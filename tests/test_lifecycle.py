"""Cycle de vie des accès (RH ↔ comptes) : vérité terrain, cas presque fautifs, API paginée, banc."""
import json
from datetime import date, timedelta
from pathlib import Path

import requests

from lab import lifecycle

ROOT = Path(__file__).resolve().parent.parent
AUDIT = {"Authorization": "Bearer audit-ro-demo"}
CHANGE = {"Authorization": "Bearer change-rw-demo"}
AS_OF = date(2026, 11, 2)


def _sc(account=None, employee=None):
    e = {"employee_id": "E1", "first_name": "A", "last_name": "B", "department": "paiements", "status": "active",
         "start_date": "2020-01-01", "end_date": None, "previous_department": None, "transfer_date": None,
         **(employee or {})}
    a = {"login": "a.b", "email": "a.b@x.example", "type": "person", "employee_id": "E1", "owner_employee_id": None,
         "enabled": True, "created": "2020-01-01", "last_login": AS_OF.isoformat(),
         "entitlements": ["commun.messagerie", "paiements.saisie"], "last_access_review": None, **(account or {})}
    return {"as_of": AS_OF.isoformat(), "employees": [e], "accounts": [a]}


def _hit(rule, **k):
    return lifecycle.offenders(_sc(**k))[rule] == ["a.b"]


def _day(n):
    return (AS_OF - timedelta(days=n)).isoformat()


def test_oracle_boundaries():
    assert not any(lifecycle.offenders(_sc()).values())
    # départ : la veille = fautif ; le jour même, à venir, ou compte désactivé = conforme
    assert _hit("PSI-5.1", employee={"status": "left", "end_date": _day(1)})
    assert not _hit("PSI-5.1", employee={"end_date": _day(0)}) and not _hit("PSI-5.1", employee={"end_date": _day(-10)})
    assert not _hit("PSI-5.1", employee={"status": "left", "end_date": _day(30)}, account={"enabled": False})
    # rattachement : matricule inconnu ; compte de service dont le responsable est parti
    assert _hit("PSI-5.2", account={"employee_id": "E404"})
    svc = {"type": "service", "employee_id": None, "owner_employee_id": "E1", "last_login": None}
    assert not _hit("PSI-5.2", account=svc) and _hit("PSI-5.2", account=svc, employee={"status": "left", "end_date": _day(5)})
    # dormant : 91 jours ; 90 pile conforme ; jamais connecté = depuis la création ; service hors champ
    assert _hit("PSI-5.3", account={"last_login": _day(91)}) and not _hit("PSI-5.3", account={"last_login": _day(90)})
    assert _hit("PSI-5.3", account={"last_login": None}) and not _hit("PSI-5.3", account={**svc, "created": _day(900)})
    # séparation des tâches : les deux paires, pas un croisement
    assert _hit("PSI-5.4", account={"entitlements": ["paiements.saisie", "paiements.validation"]})
    assert _hit("PSI-5.4", account={"entitlements": ["credit.instruction", "credit.decision"]})
    assert not _hit("PSI-5.4", account={"entitlements": ["paiements.saisie", "credit.decision"]})
    # mutation : 31 jours avec un droit de l'ancien service ; 30 pile conforme ; droit commun ignoré
    moved = {"department": "credit", "previous_department": "paiements"}
    assert _hit("PSI-5.5", employee={**moved, "transfer_date": _day(31)})
    assert not _hit("PSI-5.5", employee={**moved, "transfer_date": _day(30)})
    assert not _hit("PSI-5.5", employee={**moved, "transfer_date": _day(200)}, account={"entitlements": ["commun.messagerie", "credit.instruction"]})
    # revue des privilèges : absente ou 366 jours ; 365 pile conforme ; sans privilège hors champ
    priv = ["paiements.admin"]
    assert _hit("PSI-5.6", account={"entitlements": priv}) and _hit("PSI-5.6", account={"entitlements": priv, "last_access_review": _day(366)})
    assert not _hit("PSI-5.6", account={"entitlements": priv, "last_access_review": _day(365)}) and not _hit("PSI-5.6")


def test_scenarios_match_generator_and_are_synthetic():
    built = {s["id"]: s for s in lifecycle.build()}
    assert lifecycle.load() == built and list(built) == ["lc-01-kerlann", "lc-02-oceane", "lc-03-menhir"]
    for sc in built.values():
        assert all(a["email"].endswith(".example") for a in sc["accounts"])
        assert sc["expected_offenders"] == lifecycle.offenders(sc) and sc["expected"] == lifecycle.expected(sc)
        assert len(sc["accounts"]) > 2 * lifecycle.PAGE_SIZE
    assert set(built["lc-01-kerlann"]["expected"].values()) == {"fail"}
    assert set(built["lc-02-oceane"]["expected"].values()) == {"pass"}
    m = built["lc-03-menhir"]
    assert [r for r, v in m["expected"].items() if v == "fail"] == ["PSI-5.1", "PSI-5.4"]
    order = [a["login"] for a in m["accounts"]]
    assert all(order.index(x) >= lifecycle.PAGE_SIZE for v in m["expected_offenders"].values() for x in v)


def test_policy_and_framework_share_the_rules():
    lib = (ROOT / "exigences/library/politique-psi-5-cycle-de-vie.md").read_text(encoding="utf-8")
    fw = (ROOT / "exigences/cycle_de_vie_acces.md").read_text(encoding="utf-8")
    rows = [l for l in lib.splitlines() if l.startswith("| PSI-5.")]
    assert len(rows) == 6 and all(r in fw for r in rows)


def _reset(lab, sid):
    assert requests.post(lab + "/api/reset", json={"scenario": sid}, headers=CHANGE, timeout=10).status_code == 200


def test_api_is_paginated_read_only_and_switchable(lab):
    _reset(lab, "lc-03-menhir")
    assert requests.get(lab + "/api/lifecycle/meta").status_code == 401
    meta = requests.get(lab + "/api/lifecycle/meta", headers=AUDIT).json()
    assert meta["as_of"] == "2026-11-02" and meta["accounts"] == 253
    got, url = [], "/api/lifecycle/accounts"
    while url:
        r = requests.get(lab + url, headers=AUDIT)
        got += r.json()
        url = r.links.get("next", {}).get("url")
    assert len(got) == 253 and r.headers["X-Total-Pages"] == "3" and r.headers["X-Page"] == "3"
    emp = requests.get(lab + "/api/hr/employees?page=3", headers=AUDIT)
    assert len(emp.json()) == 50 and "next" not in emp.links
    assert requests.post(lab + "/api/lifecycle/accounts", headers=CHANGE, json={}).status_code == 405
    assert requests.post(lab + "/api/reset", json={"scenario": "lc-99"}, headers=CHANGE).status_code == 404
    _reset(lab, "01-kerlann-adm")                                   # un scénario de la console rétablit le défaut
    assert requests.get(lab + "/api/lifecycle/meta", headers=AUDIT).json()["accounts"] == 434
    assert requests.get(lab + "/api/security", headers=AUDIT).status_code == 200


def test_evidence_page_shows_the_offender(lab):
    from attest import evidence
    _reset(lab, "lc-03-menhir")
    who = lifecycle.load()["lc-03-menhir"]["expected_offenders"]["PSI-5.1"][0]
    url = evidence.locate(lab + "/lifecycle/reconciliation", "audit-ro-demo", {who})
    assert "page=" in url and f'id="user-{who}"' in requests.get(url, headers=AUDIT).text


def test_bench_scores_named_offenders_and_any_rule_set():
    from attest import bench
    sc = {"accounts": [{"login": x} for x in ("a.b", "c.d", "e.f")],
          "expected_offenders": {"PSI-5.1": ["a.b"], "PSI-5.4": ["c.d"], "PSI-5.6": []}}
    e = lambda rule, st, obs=None: {"control": {"rule": rule}, "status_before": st, "before": {"observed": obs}}
    o = bench.score_offenders(sc, [e("PSI-5.1", "fail", [{"login": "a.b"}, {"login": "e.f"}]), e("PSI-5.4", "review"),
                                   e("PSI-5.6", "pass")])
    assert (o["PSI-5.1"]["TP"], o["PSI-5.1"]["FP"], o["PSI-5.1"]["FN"]) == (1, 1, 0) and o["PSI-5.1"]["extra"] == ["e.f"]
    assert o["PSI-5.4"]["FN"] == 1 and not o["PSI-5.4"]["determined"] and o["PSI-5.6"]["TP"] == 0
    m = bench.offender_metrics([{"offenders": o}])
    assert (m["TP"], m["FP"], m["FN"]) == (1, 1, 1) and m["precision"] == 0.5 and m["recall"] == 0.5
    cells = bench.score({"PSI-5.1": "fail", "PSI-5.10": "pass", "PSI-5.2": "pass"}, [e("PSI-5.1", "fail")])
    assert bench._rules([{"cells": cells}]) == ["PSI-5.1", "PSI-5.2", "PSI-5.10"]
    assert len(bench.select(None, bench.SUITES["iam-lifecycle"][0])) == 3


def test_library_scripts_match_ground_truth_on_every_scenario(lab):
    """Les 6 scripts PSI-5 écrits par Muse Spark (exécution 20261112-125816-lifecycle-bench-meta), rejoués sans
    modèle : même verdict que la vérité terrain et exactement les comptes fautifs attendus, sur les 3 scénarios."""
    from attest import catalog, config, pipeline, sandbox, targets
    doc = targets.api_doc("iam-lifecycle")
    controls = json.loads((ROOT / "controls" / "AUD-2026-JML-01.en.json").read_text(encoding="utf-8"))["controls"]
    assert sorted(c["rule"] for c in controls) == lifecycle.RULES
    for sid, sc in lifecycle.load().items():
        _reset(lab, sid)
        logins = {a["login"] for a in sc["accounts"]}
        for c in controls:
            code = (ROOT / "library" / f"{catalog._safe(c['rule'])}-{catalog.script_key(c, doc)}.py").read_text(encoding="utf-8")
            res = sandbox.run(code, lab, config.AUDIT_TOKEN)
            assert res["status"] == sc["expected"][c["rule"]], (sid, c["rule"], res.get("detail"))
            assert "partial_population" not in res["requests"]
            if res["status"] == "fail":
                assert sorted(pipeline._strings(res["observed"]) & logins) == sc["expected_offenders"][c["rule"]], (sid, c["rule"])
