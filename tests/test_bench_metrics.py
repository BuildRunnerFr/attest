"""Oracle PSI-4.7 (mots entiers) et métriques du banc : par règle, rappel strict, doublons, score par compte."""
import json

from attest import bench
from lab.scenarios import FIRST, LAST, build, functional_local, generic_admins


def _admin(login, local):
    return {"login": login, "email": f"{local}@x.example", "role": "admin"}


def test_oracle_whole_words_not_substrings():
    users = [_admin("j.opsomer", "jean.opsomer"), _admin("r.rootsaert", "rose.rootsaert"),
             _admin("t.teamson", "tom.teamson"), _admin("a.madmin", "anne.madmin"),
             _admin("p.martin", "it-support"), _admin("o.ops", "ops-partage"), _admin("s.svc", "svc_backup"),
             _admin("e.exp", "exploitation"), _admin("a.adm", "admin2")]
    assert generic_admins(users) == ["p.martin", "o.ops", "s.svc", "e.exp", "a.adm"]
    assert not functional_local("jean.opsomer") and functional_local("Helpdesk.Team")


def test_generator_names_never_functional():
    assert not [f"{f}.{l}" for f in FIRST for l in LAST if functional_local(f"{f}.{l}")]


def test_ground_truth_unchanged_by_oracle_fix():
    for sc in build():
        on_disk = json.loads((bench.SCEN_DIR / f"{sc['id']}.json").read_text())
        assert sc["expected"] == on_disk["expected"]
        assert sc["expected_generic_admins"] == on_disk["expected_generic_admins"]


def _e(rule, status, **kw):
    return {"control": {"rule": rule}, "status_before": status, **kw}


def test_score_duplicates_not_overwritten():
    exp = {"PSI-4.1": "fail", "PSI-4.2": "fail", "PSI-4.3": "pass"}
    cells = bench.score(exp, [_e("PSI-4.1", "pass"), _e("PSI-4.1", "fail"), _e("PSI-4.2", "fail"),
                              _e("PSI-4.2", "fail"), _e("PSI-4.3", "pass")])
    assert cells["PSI-4.1"]["verdict"] == "inconclusive" and cells["PSI-4.1"]["got"] == "conflict"
    assert cells["PSI-4.2"]["verdict"] == "TP" and cells["PSI-4.2"]["entries"] == 2
    assert cells["PSI-4.3"]["verdict"] == "TN" and "entries" not in cells["PSI-4.3"]


def _res(cells, acc=None):
    return {"id": "x", "cells": cells, "accounts_generic": acc, "pii_total": 0, "pii_model": 0, "pii_masked": 0,
            "injection_expected": False, "injection_flagged": False, "cost_usd": 0, "seconds": 0}


def test_per_rule_metrics_and_strict_recall():
    c = lambda exp, v: {"expected": exp, "got": None, "verdict": v}
    results = [_res({"PSI-4.1": c("fail", "TP"), "PSI-4.2": c("fail", "inconclusive")}),
               _res({"PSI-4.1": c("pass", "FP"), "PSI-4.2": c("fail", "TP")}),
               _res({"PSI-4.1": c("fail", "missing"), "PSI-4.2": c("pass", "inconclusive")}),
               _res({"PSI-4.1": c("fail", "FN"), "PSI-4.2": c("pass", "TN")})]
    s = bench.summarize(results)
    m1, m2 = s["per_rule"]["PSI-4.1"], s["per_rule"]["PSI-4.2"]
    assert (m1["TP"], m1["FP"], m1["FN"], m1["TN"], m1["missing_on_fail"]) == (1, 1, 1, 0, 1)
    assert m1["precision"] == 0.5 and m1["recall"] == 0.333 and m1["recall_concluded"] == 0.5
    assert (m2["inconclusive"], m2["inconclusive_on_fail"], m2["recall"], m2["recall_concluded"]) == (2, 1, 0.5, 1.0)
    assert m2["precision"] == 1.0 and s["per_rule"]["PSI-4.7"]["checks"] == 0
    # global : 2 TP, 1 FN, 1 manquant + 1 non concluant sur NC attendue → rappel strict 2/5
    assert s["recall"] == 0.4 and s["recall_concluded"] == 0.667 and s["undetected_inconclusive"] == 2
    md = bench.to_markdown({"model": "m", "backend": "mock", "date": "d", "summary": s, "scenarios": results})
    assert "| PSI-4.1 | 3 | 1 | 1 | 1 | 0 | 0/1 (0/1) | 50 % | 33 % | 50 % |" in md


def test_accounts_psi47():
    sc = {"expected_generic_admins": ["ops"],
          "users": [_admin("a.lefloch", "anne.lefloch"), _admin("ops", "ops-partage"),
                    {"login": "c.x", "email": "c@x.example", "role": "conseiller"}]}
    field = "ops ops-partage@x.example admin 10.0.0.1 Oui"
    ev = {"inspection": {"field_text": field}}
    a = bench.score_accounts(sc, [_e("PSI-4.7", "fail", before={"detail": "1 of 2 admin"}, evidence_before=ev)])
    assert (a["TP"], a["FP"], a["FN"], a["TN"], a["source"], a["declared"]) == (1, 0, 0, 1, "evidence", 1)
    # liste explicite du script prioritaire ; faux positif compté
    a = bench.score_accounts(sc, [_e("PSI-4.7", "fail", before={"violations": [{"login": "a.lefloch"}]})])
    assert (a["TP"], a["FP"], a["FN"], a["TN"], a["source"]) == (0, 1, 1, 0, "result:violations")
    # « pass » : aucun compte désigné → le générique est manqué
    a = bench.score_accounts(sc, [_e("PSI-4.7", "pass")])
    assert (a["TP"], a["FN"], a["TN"]) == (0, 1, 1)
    # non concluant ou absent : génériques manqués, aucun TN revendiqué
    for entries in ([_e("PSI-4.7", "review")], []):
        a = bench.score_accounts(sc, entries)
        assert (a["TP"], a["FN"], a["TN"], a["undetermined"], a["got"]) == (0, 1, 0, 2, None)
    assert bench.score_accounts({"users": []}, []) is None
    s = bench.summarize([_res({}, bench.score_accounts(sc, [_e("PSI-4.7", "fail", evidence_before=ev)]))])
    assert s["accounts_generic"]["TP"] == 1 and s["accounts_generic"]["recall"] == 1.0


def test_rescore_without_model(tmp_path):
    sc = json.loads((bench.SCEN_DIR / "08-kerlann-apres-correctifs.json").read_text())
    d = tmp_path / "bench" / sc["id"]
    d.mkdir(parents=True)
    entries = [_e(r, v) for r, v in sc["expected"].items()]
    (d / "result.json").write_text(json.dumps({"entries": entries}))
    data = bench.rescore(tmp_path / "bench", tmp_path / "out")
    s = data["summary"]
    assert s["checks"] == 7 and s["accuracy"] == 1.0 and s["per_rule"]["PSI-4.7"]["TP"] == 1
    assert s["accounts_generic"]["undetermined"] == 2 and s["accounts_generic"]["FN"] == 1   # « fail » sans preuve
    assert (tmp_path / "out" / "scorecard.md").exists()
