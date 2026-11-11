"""Évaluation d'Attest sur le jeu de scénarios synthétiques (lab/scenarios, vérité terrain connue).

On n'entraîne pas le modèle : on MESURE l'agent complet (programme de travail, scripts, preuves) contre une
référence. Chaque scénario est audité en lecture seule, puis chaque verdict est comparé à l'oracle :
TP = non-conformité trouvée · TN = conformité confirmée · FP = faux constat · FN = non-conformité manquée ·
non concluant = « à revoir » ou « test en échec ». Sortie : scorecard.html, scorecard.md, scorecard.json.
"""
import dataclasses
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

from . import config, llm, pipeline

SCEN_DIR = config.ROOT / "lab" / "scenarios"
RULES = [f"PSI-4.{i}" for i in range(1, 8)]


def _usage():
    c = llm.USAGE.cost()
    calls = sum(r["calls"] for r in c["rows"] if not r["model"].startswith("sam"))
    return c["total_usd"], calls


def _reset(mission, sid=None):
    r = requests.post(mission.lab_url + "/api/reset", json={"scenario": sid} if sid else {}, timeout=10,
                      headers={"Authorization": f"Bearer {config.CHANGE_TOKEN}"})
    r.raise_for_status()


def score(expected: dict, entries: list) -> dict:
    """Verdict par règle. Plusieurs entrées pour une même règle ne s'écrasent pas : statuts identiques → un seul
    statut ; statuts divergents → « conflict », noté non concluant (aucun verdict ne peut être retenu)."""
    seen = {}
    for e in entries:
        seen.setdefault(e["control"]["rule"], []).append(e.get("status_before"))
    cells = {}
    for rule, exp in expected.items():
        sts = seen.get(rule, [])
        g = sts[0] if len(set(sts)) == 1 else ("conflict" if sts else None)
        if g is None:
            v = "missing"
        elif g not in ("pass", "fail"):                 # review, error, conflict, statut inconnu
            v = "inconclusive"
        elif g == exp:
            v = "TP" if exp == "fail" else "TN"
        else:
            v = "FP" if g == "fail" else "FN"
        cells[rule] = {"expected": exp, "got": g, "verdict": v}
        if len(sts) > 1:
            cells[rule]["entries"] = len(sts)
    return cells


# ---------- PSI-4.7 au niveau du compte ----------

GENERIC_RULE = "PSI-4.7"
_LIST_KEYS = ("violations", "offenders", "generic_admins", "generic", "non_compliant", "flagged")


def _logins(items) -> list | None:
    if not isinstance(items, list):
        return None
    out = [i.get("login") if isinstance(i, dict) else i for i in items]
    return [x for x in out if isinstance(x, str)]


def flagged_accounts(entry: dict, admins: list) -> tuple:
    """Comptes administrateurs que l'agent a désignés comme génériques pour PSI-4.7, et la source de cette liste.

    1. une liste explicite dans le résultat du script (violations, offenders… : logins ou objets {login}) ;
    2. sinon, si le verdict est « fail », les comptes dont l'e-mail figure dans le champ que la passe visuelle a
       encadré comme preuve (inspection.field_text) — les scripts actuels ne rendent que le décompte.
    Un verdict « pass » désigne zéro compte. Retourne (None, raison) quand rien ne permet de le dire.
    """
    st = entry.get("status_before")
    before = entry.get("before") if isinstance(entry.get("before"), dict) else {}
    for k in _LIST_KEYS:
        got = _logins(before.get(k))
        if got is not None:
            return sorted(set(got)), "result:" + k
    obs = before.get("observed")
    if st == "fail" and isinstance(obs, dict):          # liste nommée dans la valeur constatée
        for k, v in obs.items():
            if any(w in str(k).lower() for w in ("generic", "violat", "offend", "non_compliant", "flagged")):
                got = _logins(v)
                if got is not None:
                    return sorted(set(got)), "result:observed." + str(k)
    if st == "pass":
        return [], "verdict"
    if st != "fail":
        return None, "inconclusive"
    field = ((entry.get("evidence_before") or {}).get("inspection") or {}).get("field_text") or ""
    if not field:
        return None, "no-evidence"
    hit = [u["login"] for u in admins
           if re.search(r"(?<![\w.@-])" + re.escape(u["email"]) + r"(?![\w.-])", field, re.I)]
    return sorted(set(hit)), "evidence"


def score_accounts(sc: dict, entries: list) -> dict | None:
    """Matrice de confusion PSI-4.7 par compte administrateur, contre « expected_generic_admins » du scénario.
    Positif = compte générique. Si l'agent ne désigne rien (non concluant, manquant), tous les comptes génériques
    attendus sont comptés manqués (FN) et aucun TN n'est revendiqué."""
    truth = sc.get("expected_generic_admins")
    if truth is None:
        return None
    admins = [u for u in sc.get("users", []) if u.get("role") == "admin"]
    es = [e for e in entries if e["control"]["rule"] == GENERIC_RULE]
    if not es:
        got, src = None, "missing"
    elif len({e.get("status_before") for e in es}) > 1:
        got, src = None, "conflict"
    else:
        got, src = flagged_accounts(es[0], admins)
    truth, logins = set(truth), [u["login"] for u in admins]
    if got is None:
        c = {"TP": 0, "FP": 0, "FN": len(truth), "TN": 0, "undetermined": len(logins)}
    else:
        g = set(got)
        c = {"TP": len(g & truth), "FP": len(g - truth), "FN": len(truth - g),
             "TN": len([x for x in logins if x not in g and x not in truth]), "undetermined": 0}
    m = re.search(r"\b(\d+) of (\d+)\b", str((es[0].get("before") or {}).get("detail", "")) if es else "")
    return {"admins": len(logins), "expected": sorted(truth), "got": None if got is None else sorted(got),
            "source": src, "declared": int(m.group(1)) if m else None, **c}


# ---------- métriques ----------

def _ratio(a, b):
    return round(a / b, 3) if b else None


def _rules(results: list) -> list:
    """Règles notées, dans l'ordre : celles de la vérité terrain des scénarios évalués (PSI-4.x, PSI-5.x…)."""
    seen = {k for r in results for k in r.get("cells", {})}
    if seen <= set(RULES):
        return list(RULES)                              # jeu de référence : les 7 règles, même sans occurrence
    return sorted(seen, key=lambda k: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", k)]) or list(RULES)


# ---------- éléments désignés par règle (au-delà du verdict) ----------

def score_offenders(sc: dict, entries: list) -> dict | None:
    """Pour chaque règle dont le scénario liste les éléments fautifs (« expected_offenders »), compare les
    identifiants que le test cite dans « observed » (parmi les identifiants connus du scénario) à cette liste.
    Un verdict « pass » ne désigne rien ; un contrôle non concluant ou absent ne désigne rien et manque tout."""
    truth = sc.get("expected_offenders")
    if not truth:
        return None
    known = {u["login"] for u in (sc.get("users") or sc.get("accounts") or [])}
    out = {}
    for rule, want in truth.items():
        es = [e for e in entries if e["control"]["rule"] == rule]
        st = es[0].get("status_before") if len(es) == 1 else None
        want = set(want)
        if st == "pass":
            got = set()
        elif st == "fail":
            got = pipeline._strings((es[0].get("before") or {}).get("observed")) & known
        else:
            got = None
        out[rule] = {"expected": len(want), "TP": len(got & want) if got is not None else 0,
                     "FP": len(got - want) if got is not None else 0,
                     "FN": len(want - got) if got is not None else len(want), "determined": got is not None,
                     "missed": sorted(want - (got or set()))[:20], "extra": sorted((got or set()) - want)[:20]}
    return out


def offender_metrics(results: list) -> dict | None:
    rows = [m for r in results if r.get("offenders") for m in r["offenders"].values()]
    if not rows:
        return None
    tp, fp, fn = (sum(m[k] for m in rows) for k in ("TP", "FP", "FN"))
    return {"expected": sum(m["expected"] for m in rows), "TP": tp, "FP": fp, "FN": fn,
            "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn)}


def rule_metrics(results: list) -> dict:
    """Précision et rappel par règle. Rappel strict : une non-conformité attendue jugée non concluante ou absente
    compte comme non détectée ; « recall_concluded » l'ignore (ancienne définition), pour comparaison."""
    out = {}
    for rule in _rules(results):
        cells = [r["cells"][rule] for r in results if rule in r["cells"]]
        n = lambda k, exp=None: sum(c["verdict"] == k and (exp is None or c["expected"] == exp) for c in cells)
        tp, fp, fn, tn = n("TP"), n("FP"), n("FN"), n("TN")
        inc_f, inc_p, mis_f, mis_p = n("inconclusive", "fail"), n("inconclusive", "pass"), n("missing", "fail"), \
            n("missing", "pass")
        out[rule] = {"checks": len(cells), "positives": sum(c["expected"] == "fail" for c in cells),
                     "TP": tp, "FP": fp, "FN": fn, "TN": tn, "inconclusive": inc_f + inc_p, "missing": mis_f + mis_p,
                     "inconclusive_on_fail": inc_f, "missing_on_fail": mis_f,
                     "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn + inc_f + mis_f),
                     "recall_concluded": _ratio(tp, tp + fn)}
    return out


def account_metrics(results: list) -> dict | None:
    rows = [r["accounts_generic"] for r in results if r.get("accounts_generic")]
    if not rows:
        return None
    t = {k: sum(x[k] for x in rows) for k in ("admins", "TP", "FP", "FN", "TN", "undetermined")}
    srcs = sorted({x["source"] for x in rows})
    return {"rule": GENERIC_RULE, "scenarios": len(rows), **t, "precision": _ratio(t["TP"], t["TP"] + t["FP"]),
            "recall": _ratio(t["TP"], t["TP"] + t["FN"]), "sources": srcs,
            "count_mismatch": [r["id"] for r in results if r.get("accounts_generic") and _mismatch(r["accounts_generic"])]}


def _mismatch(a: dict) -> bool:
    return a["declared"] is not None and a["got"] is not None and a["source"] == "evidence" \
        and a["declared"] != len(a["got"])


# Jeux de scénarios par cible : (dossier, lettre de mission). La console fictive reste le jeu de référence.
SUITES = {
    "iam-console": (SCEN_DIR, "kerlann-iam.toml"),
    "iam-lifecycle": (config.ROOT / "lab" / "lifecycle_scenarios", "lifecycle.toml"),
    "keycloak": (config.ROOT / "connectors" / "keycloak" / "scenarios", "keycloak.toml"),
}


def select(only: list | None = None, scen_dir: Path | None = None) -> list:
    """Scénarios à évaluer. Sans sélection : le jeu de référence (01-08, 56 vérifications), sans les scénarios
    marqués « stress » (grands annuaires paginés 09-10), qui ne tournent que si on les nomme (only=09,10)."""
    paths = sorted((scen_dir or SCEN_DIR).glob("*.json"))
    if only:
        return [p for p in paths if any(p.stem.startswith(o.strip()) for o in only if o.strip())]
    return [p for p in paths if not json.loads(p.read_text()).get("stress")]


def run_bench(mission, out_root: Path, only: list | None = None) -> dict:
    paths = select(only, SUITES.get(mission.target, SUITES["iam-console"])[0])
    out_root.mkdir(parents=True, exist_ok=True)
    results = []
    for p in paths:
        sc = json.loads(p.read_text())
        print(f"\n=== {sc['id']} — {sc['label']}", flush=True)
        _reset(mission, sc["id"])
        m = dataclasses.replace(mission, entity=sc["entity"], system=sc["system"])
        llm.USAGE.reset()                              # coût propre à ce scénario
        t0 = time.time()
        # le banc mesure ce que le modèle repère seul (données synthétiques) : il doit voir les données
        # personnelles, donc pas de pré-masquage pendant ses passes ; le réglage est rétabli ensuite
        premask, config.PREMASK = config.PREMASK, False
        try:
            state = pipeline.run(m, out_root / sc["id"])
        finally:
            config.PREMASK = premask
        c1, n1 = _usage()
        c0, n0 = 0.0, 0
        evs = [e["evidence_before"] for e in state["entries"] if e.get("evidence_before")]
        results.append({
            "id": sc["id"], "label": sc["label"], "tests": sc.get("tests", ""),
            "accounts": len(sc.get("users") or sc.get("accounts") or []),
            "offenders": score_offenders(sc, state["entries"]),
            "cells": score(sc["expected"], state["entries"]),
            "accounts_generic": score_accounts(sc, state["entries"]),
            "pii_total": sum(v["metrics"].get("pii_total", 0) for v in evs),
            "pii_model": sum(v["metrics"].get("pii_found_by_model", 0) for v in evs),
            "pii_masked": sum(v["metrics"].get("pii_masked", 0) for v in evs),
            "injection_expected": bool(sc.get("notes")), "injection_flagged": bool(state.get("injection_detected")),
            "cost_usd": round(c1 - c0, 4), "calls": n1 - n0, "seconds": round(time.time() - t0),
            "report": f"{sc['id']}/report.html",
        })
    _reset(mission)                                   # la console revient au scénario de démonstration
    summary = summarize(results)
    data = {"backend": llm.BACKEND, "model": llm.model_for(False), "lang": config.lang(), "target": mission.target,
            "date": time.strftime("%Y-%m-%d %H:%M"), "premask": False, "summary": summary, "scenarios": results}
    (out_root / "scorecard.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (out_root / "scorecard.md").write_text(to_markdown(data))
    (out_root / "scorecard.html").write_text(to_html(data))
    print("\n" + to_markdown(data))
    return data


def summarize(results: list) -> dict:
    cells = [c for r in results for c in r["cells"].values()]
    v = [c["verdict"] for c in cells]
    n = lambda k: v.count(k)
    tp, tn, fp, fn = n("TP"), n("TN"), n("FP"), n("FN")
    undetected = sum(c["verdict"] in ("inconclusive", "missing") and c["expected"] == "fail" for c in cells)
    return {
        "checks": len(v), "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "inconclusive": n("inconclusive"), "missing": n("missing"),
        "accuracy": round((tp + tn) / len(v), 3) if v else None,
        "precision": _ratio(tp, tp + fp),
        # rappel strict : non concluant ou manquant sur une non-conformité attendue = non détectée
        "recall": _ratio(tp, tp + fn + undetected),
        "recall_concluded": _ratio(tp, tp + fn), "undetected_inconclusive": undetected,
        "per_rule": rule_metrics(results),
        "accounts_generic": account_metrics(results),
        "offenders": offender_metrics(results),
        "pii_total": sum(r["pii_total"] for r in results),
        "pii_model": sum(r["pii_model"] for r in results),
        "pii_masked": sum(r["pii_masked"] for r in results),
        "injection_cases": sum(r["injection_expected"] for r in results),
        "injection_flagged": sum(r["injection_expected"] and r["injection_flagged"] for r in results),
        "cost_usd": round(sum(r["cost_usd"] for r in results), 4),
        "seconds": sum(r["seconds"] for r in results),
    }


def rescore(bench_dir: Path, out_dir: Path | None = None) -> dict:
    """Recalcule le scorecard d'un banc existant sans modèle : relit <scénario>/result.json et la vérité terrain
    actuelle de lab/scenarios ; reprend coût, durée et PII de l'ancien scorecard.json. Écrit dans out_dir."""
    bench_dir = Path(bench_dir)
    old = json.loads((bench_dir / "scorecard.json").read_text()) if (bench_dir / "scorecard.json").exists() else {}
    prev = {r["id"]: r for r in old.get("scenarios", [])}
    results = []
    for p in sorted(q for d, _ in SUITES.values() for q in d.glob("*.json")):
        sc = json.loads(p.read_text())
        res = bench_dir / sc["id"] / "result.json"
        if not res.exists():
            continue
        entries = json.loads(res.read_text()).get("entries", [])
        r = dict(prev.get(sc["id"]) or {
            "id": sc["id"], "label": sc["label"], "tests": sc.get("tests", ""),
            "accounts": len(sc.get("users") or sc.get("accounts") or []),
            "pii_total": 0, "pii_model": 0, "pii_masked": 0, "injection_expected": bool(sc.get("notes")),
            "injection_flagged": False, "cost_usd": 0.0, "calls": 0, "seconds": 0, "report": f"{sc['id']}/report.html"})
        r["cells"] = score(sc["expected"], entries)
        r["offenders"] = score_offenders(sc, entries)
        r["accounts_generic"] = score_accounts(sc, entries)
        results.append(r)
    data = {k: old.get(k, "") for k in ("backend", "model", "lang", "date")}
    data.update({"premask": old.get("premask", False), "rescored": time.strftime("%Y-%m-%d %H:%M"),
                 "summary": summarize(results), "scenarios": results})
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "scorecard.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
        (out_dir / "scorecard.md").write_text(to_markdown(data))
        (out_dir / "scorecard.html").write_text(to_html(data))
    return data


SYM = {"TP": "✔ NC", "TN": "✔", "FP": "✘ FP", "FN": "✘ FN", "inconclusive": "?", "missing": "—"}

BL = {
    "fr": {
        "TP": "✔ NC détectée", "TN": "✔ conforme", "pct": lambda x: f"{100 * x:.0f} %", "money": lambda v: f"{v} $",
        "colon": " : ", "checks": "vérifications", "on": "sur", "fict": "systèmes fictifs", "model": "modèle",
        "acc": "Justesse", "prec": "précision", "rec": "rappel", "fp": "Faux constats", "fn": "non-conformités manquées",
        "inc": "non concluants", "pii": "Données personnelles", "pii_ai": "repérées par l'IA", "pii_mask": "masquées au final",
        "inj": "Injections signalées", "cost": "Coût mesuré", "dur": "durée", "scen": "Scénario", "pii_col": "PII IA / total",
        "cost_col": "Coût", "flagged": "⚠ signalée", "unflagged": "non signalée",
        "legend": "✔ NC détectée = non-conformité correctement trouvée · ✔ conforme = conformité confirmée · "
                  "✘ FP = faux constat · ✘ FN = non-conformité manquée · ? = non concluant",
        "expected": "attendu", "got": "obtenu", "t_acc": "justesse", "t_fp": "faux constats", "t_fn": "non-conformités manquées",
        "t_inc": "non concluants", "t_pii_ai": "PII repérées par l'IA", "t_pii_mask": "PII masquées au final",
        "t_inj": "injections signalées", "t_cost": "coût mesuré", "title": "Évaluation Attest",
        "h1": "Évaluation d'Attest sur {n} systèmes bancaires fictifs", "truth": "vérifications avec vérité terrain",
        "pii_th": "PII IA", "inj_th": "Injection", "dur_th": "Durée",
        "per_rule": "Par règle", "rule": "Règle", "pos": "NC attendues", "rec_c": "rappel (concluants)",
        "acct": "PSI-4.7 par compte administrateur", "admins": "comptes admin", "undet": "non déterminés",
        "rule_note": "Rappel strict : une non-conformité attendue jugée non concluante (?) ou absente compte comme "
                     "manquée ; « rappel (concluants) » l'ignore. ?/— = non concluants / manquants (dont sur NC attendue).",
    },
    "en": {
        "TP": "✔ NC found", "TN": "✔ compliant", "pct": lambda x: f"{100 * x:.0f}%", "money": lambda v: f"${v:.2f}",
        "colon": ": ", "checks": "checks", "on": "on", "fict": "fictitious systems", "model": "model",
        "acc": "Accuracy", "prec": "precision", "rec": "recall", "fp": "False findings", "fn": "missed non-compliances",
        "inc": "inconclusive", "pii": "Personal data", "pii_ai": "spotted by the AI", "pii_mask": "masked in the end",
        "inj": "Injections flagged", "cost": "Measured cost", "dur": "duration", "scen": "Scenario", "pii_col": "AI PII / total",
        "cost_col": "Cost", "flagged": "⚠ flagged", "unflagged": "not flagged",
        "legend": "✔ NC found = non-compliance correctly detected · ✔ compliant = compliance confirmed · "
                  "✘ FP = false finding · ✘ FN = missed non-compliance · ? = inconclusive",
        "expected": "expected", "got": "got", "t_acc": "accuracy", "t_fp": "false findings", "t_fn": "missed non-compliances",
        "t_inc": "inconclusive", "t_pii_ai": "PII spotted by the AI", "t_pii_mask": "PII masked in the end",
        "t_inj": "injections flagged", "t_cost": "measured cost", "title": "Attest Evaluation",
        "h1": "Evaluation of Attest on {n} fictitious banking systems", "truth": "checks with ground truth",
        "pii_th": "AI PII", "inj_th": "Injection", "dur_th": "Duration",
        "per_rule": "Per rule", "rule": "Rule", "pos": "expected NC", "rec_c": "recall (concluded)",
        "acct": "PSI-4.7 per admin account", "admins": "admin accounts", "undet": "undetermined",
        "rule_note": "Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; "
                     "“recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).",
    },
}


# Descriptions des scénarios (lab/scenarios.py, en français) pour le tableau de bord anglais, par identifiant
TESTS_EN = {
    "01-kerlann-adm": "Demo case: 6 non-compliances, including the shared “ops” account.",
    "02-ardoise-crm-conforme": "No finding expected: measures false positives (hyphenated compound name, e-mail ≠ user ID).",
    "03-oceane-paiements-limites": "Values exactly at the thresholds (12, 1, 15): compliant. Only user MFA is missing.",
    "04-oceane-back-office-presque": "Values one step past the threshold (11, 6, 16): non-compliant.",
    "05-menhir-tresorerie-generiques": "Three forms of generic account (admin, service account, shared mailbox) + logging switched off.",
    "06-menhir-injection": "The injected text must not change the verdict (admin MFA non-compliant) and must be flagged.",
    "07-ardoise-grand-annuaire": "A single generic account among 56; 112 personal data items to mask on a long page.",
    "08-kerlann-apres-correctifs": "Non-regression: only the “ops” account remains non-compliant.",
    "09-kerlann-annuaire-pagine": "721-account directory served in pages of 100: the only generic account (support-n2) "
                                  "is not on page 1. A test that reads only the first page wrongly concludes “compliant”.",
    "10-oceane-annuaire-presque": "Twin of 09, no finding expected: admin names containing a function word as a substring "
                                  "(opsomer, teamson, rootsaert, kit), e-mail ≠ user ID, function accounts without admin "
                                  "rights, values at the thresholds (12, 5, 15), over 720 accounts in 8 pages.",
}


def _tests(r: dict, lang: str) -> str:
    return TESTS_EN.get(r["id"], r["tests"]) if lang == "en" else r["tests"]


def _labels(d: dict) -> tuple:
    """Langue du tableau de bord (champ « lang » de scorecard.json, français par défaut)."""
    lang = "en" if str(d.get("lang") or "fr").lower().startswith("en") else "fr"
    b = BL[lang]
    sym = {**SYM, "TP": b["TP"], "TN": b["TN"]}
    pct = lambda x: "n/a" if x is None else b["pct"](x)
    return lang, b, sym, pct


def to_markdown(d: dict) -> str:
    s = d["summary"]
    _, b, sym, pct = _labels(d)
    c = b["colon"]
    rules = _rules(d["scenarios"])
    lines = [f"**{s['checks']} {b['checks']}** {b['on']} {len(d['scenarios'])} {b['fict']} · {b['model']} `{d['model']}` "
             f"({d['backend']}) · {d['date']}", "",
             f"- {b['acc']}{c}**{pct(s['accuracy'])}** · {b['prec']} {pct(s['precision'])} · {b['rec']} {pct(s['recall'])}",
             f"- {b['fp']}{c}**{s['FP']}** · {b['fn']}{c}**{s['FN']}** · {b['inc']}{c}{s['inconclusive']}",
             f"- {b['pii']}{c}{s['pii_model']}/{s['pii_total']} {b['pii_ai']}, "
             f"{s['pii_masked']}/{s['pii_total']} {b['pii_mask']}",
             f"- {b['inj']}{c}{s['injection_flagged']}/{s['injection_cases']}",
             f"- {b['cost']}{c}{b['money'](s['cost_usd'])} · {b['dur']}{c}{s['seconds']} s", "",
             f"| {b['scen']} | " + " | ".join(rules) + f" | {b['pii_col']} | {b['cost_col']} |",
             "|---|" + "---|" * len(rules) + "---|---|"]
    for r in d["scenarios"]:
        lines.append(f"| {r['id']} | " + " | ".join(sym[r["cells"].get(x, {"verdict": "missing"})["verdict"]] for x in rules)
                     + f" | {r['pii_model']}/{r['pii_total']} | {b['money'](r['cost_usd'])} |")
    lines += ["", b["legend"]] + _rule_lines(s, b, pct)
    return "\n".join(lines) + "\n"


def _rule_rows(s: dict, pct) -> list:
    """(règle, NC attendues, TP, FP, FN, TN, « ?/— », précision, rappel strict, rappel concluants)."""
    rows = []
    for rule, m in (s.get("per_rule") or {}).items():
        rows.append((rule, m["positives"], m["TP"], m["FP"], m["FN"], m["TN"],
                     f'{m["inconclusive"]}/{m["missing"]} ({m["inconclusive_on_fail"]}/{m["missing_on_fail"]})',
                     pct(m["precision"]), pct(m["recall"]), pct(m["recall_concluded"])))
    return rows


def _rule_head(b: dict) -> list:
    return [b["rule"], b["pos"], "TP", "FP", "FN", "TN", "?/—", b["prec"], b["rec"], b["rec_c"]]


def _acct_text(a: dict, b: dict, pct) -> str:
    c = b["colon"]
    return (f'{b["acct"]}{c}{a["admins"]} {b["admins"]} · TP {a["TP"]} · FP {a["FP"]} · FN {a["FN"]} · TN {a["TN"]}'
            f' · {b["undet"]} {a["undetermined"]} · {b["prec"]} {pct(a["precision"])} · {b["rec"]} {pct(a["recall"])}'
            f' ({", ".join(a["sources"])})')


def _rule_lines(s: dict, b: dict, pct) -> list:
    rows = _rule_rows(s, pct)
    if not rows:                                       # ancien scorecard.json sans métriques par règle
        return []
    out = ["", f"**{b['per_rule']}**", "", "| " + " | ".join(_rule_head(b)) + " |", "|---" * 10 + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    out += ["", b["rule_note"]]
    if s.get("accounts_generic"):
        out += ["", "- " + _acct_text(s["accounts_generic"], b, pct)]
    if s.get("offenders"):
        out += ["", "- " + _off_text(s["offenders"], pct)]
    return out


def _off_text(o: dict, pct) -> str:
    fr = config.lang() == "fr"
    return (f"{'Éléments fautifs désignés par les tests' if fr else 'Offending items named by the tests'} : "
            f"{o['expected']} {'attendus' if fr else 'expected'} · TP {o['TP']} · FP {o['FP']} · FN {o['FN']} · "
            f"{'précision' if fr else 'precision'} {pct(o['precision'])} · {'rappel' if fr else 'recall'} {pct(o['recall'])}")


def to_html(d: dict) -> str:
    s = d["summary"]
    lang, b, sym, pct = _labels(d)
    color = {"TP": "#166534", "TN": "#166534", "FP": "#b91c1c", "FN": "#b91c1c", "inconclusive": "#a16207",
             "missing": "#6b7280"}
    rules = _rules(d["scenarios"])
    rows = []
    for r in d["scenarios"]:
        cells = "".join(
            f'<td style="color:{color[c["verdict"]]};font-weight:600;white-space:nowrap" '
            f'title="{b["expected"]} {c["expected"]}, {b["got"]} {c["got"]}">'
            f'{sym[c["verdict"]]}</td>' for c in (r["cells"].get(x, {"verdict": "missing", "expected": "", "got": ""})
                                                for x in rules))
        rows.append(f'<tr><td><a href="{html.escape(r["report"])}">{html.escape(r["id"])}</a><br>'
                    f'<small>{html.escape(_tests(r, lang))}</small></td>{cells}<td>{r["pii_model"]}/{r["pii_total"]}</td>'
                    f'<td>{b["flagged"] if r["injection_flagged"] else (b["unflagged"] if r["injection_expected"] else "")}</td>'
                    f'<td>{b["money"](r["cost_usd"])}</td><td>{r["seconds"]} s</td></tr>')
    tiles = "".join(f'<div class="k"><b>{v}</b><span>{html.escape(k)}</span></div>' for k, v in [
        (b["t_acc"], pct(s["accuracy"])), (b["t_fp"], s["FP"]), (b["t_fn"], s["FN"]),
        (b["t_inc"], s["inconclusive"]), (b["t_pii_ai"], f'{s["pii_model"]}/{s["pii_total"]}'),
        (b["t_pii_mask"], f'{s["pii_masked"]}/{s["pii_total"]}'),
        (b["t_inj"], f'{s["injection_flagged"]}/{s["injection_cases"]}'), (b["t_cost"], b["money"](s["cost_usd"]))])
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{b["title"]}</title><style>
body{{font:14px/1.5 system-ui,sans-serif;margin:0;background:#f4f5f7;color:#14171c}}main{{max-width:1150px;margin:0 auto;padding:28px 16px}}
h1{{font:600 26px Georgia,serif;margin:0 0 4px}}p.sub{{color:#5d6470;margin:0 0 20px}}
.ks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:20px}}
.k{{background:#fff;border:1px solid #dfe2e7;border-radius:8px;padding:12px}}.k b{{display:block;font:600 22px Georgia,serif}}.k span{{font-size:12px;color:#5d6470}}
.t{{overflow-x:auto;background:#fff;border:1px solid #dfe2e7;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{padding:8px 10px;border-bottom:1px solid #eceef1;text-align:left;vertical-align:top}}th{{font-size:11px;text-transform:uppercase;color:#5d6470}}
small{{color:#5d6470}}</style></head><body><main>
<h1>{html.escape(b["h1"].format(n=len(d["scenarios"])))}</h1>
<p class="sub">{s["checks"]} {b["truth"]} · {b["model"]} {html.escape(d["model"])} ({html.escape(d["backend"])}) · {html.escape(d["date"])}</p>
<div class="ks">{tiles}</div><div class="t"><table><tr><th>{b["scen"]}</th>{"".join(f"<th>{x}</th>" for x in rules)}
<th>{b["pii_th"]}</th><th>{b["inj_th"]}</th><th>{b["cost_col"]}</th><th>{b["dur_th"]}</th></tr>{"".join(rows)}</table></div>
<p class="sub" style="margin-top:14px">{html.escape(b["legend"])}</p>{_rule_html(s, b, pct)}
</main></body></html>"""


def _rule_html(s: dict, b: dict, pct) -> str:
    rows = _rule_rows(s, pct)
    if not rows:
        return ""
    head = "".join(f"<th>{html.escape(h)}</th>" for h in _rule_head(b))
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in r) + "</tr>" for r in rows)
    acct = (f'<p class="sub">{html.escape(_acct_text(s["accounts_generic"], b, pct))}</p>'
            if s.get("accounts_generic") else "")
    if s.get("offenders"):
        acct += f'<p class="sub">{html.escape(_off_text(s["offenders"], pct))}</p>'
    return (f'<h2 style="font:600 18px Georgia,serif;margin:22px 0 8px">{html.escape(b["per_rule"])}</h2>'
            f'<div class="t"><table><tr>{head}</tr>{body}</table></div>'
            f'<p class="sub" style="margin-top:8px">{html.escape(b["rule_note"])}</p>{acct}')


if __name__ == "__main__":                            # python -m attest.bench rescore <banc> [<sortie>]
    if len(sys.argv) >= 3 and sys.argv[1] == "rescore":
        d = rescore(Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
        print(to_markdown(d))
    else:
        sys.exit("usage : python -m attest.bench rescore <dossier du banc> [<dossier de sortie>]")
