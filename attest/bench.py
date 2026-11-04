"""Évaluation d'Attest sur le jeu de scénarios synthétiques (lab/scenarios, vérité terrain connue).

On n'entraîne pas le modèle : on MESURE l'agent complet (programme de travail, scripts, preuves) contre une
référence. Chaque scénario est audité en lecture seule, puis chaque verdict est comparé à l'oracle :
TP = non-conformité trouvée · TN = conformité confirmée · FP = faux constat · FN = non-conformité manquée ·
non concluant = « à revoir » ou « test en échec ». Sortie : scorecard.html, scorecard.md, scorecard.json.
"""
import dataclasses
import html
import json
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
    got = {e["control"]["rule"]: e.get("status_before") for e in entries}
    cells = {}
    for rule, exp in expected.items():
        g = got.get(rule)
        if g is None:
            v = "missing"
        elif g in ("review", "error"):
            v = "inconclusive"
        elif g == exp:
            v = "TP" if exp == "fail" else "TN"
        else:
            v = "FP" if g == "fail" else "FN"
        cells[rule] = {"expected": exp, "got": g, "verdict": v}
    return cells


def run_bench(mission, out_root: Path, only: list | None = None) -> dict:
    paths = sorted(SCEN_DIR.glob("*.json"))
    if only:
        paths = [p for p in paths if any(p.stem.startswith(o) for o in only)]
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
            "id": sc["id"], "label": sc["label"], "tests": sc.get("tests", ""), "accounts": len(sc["users"]),
            "cells": score(sc["expected"], state["entries"]),
            "pii_total": sum(v["metrics"].get("pii_total", 0) for v in evs),
            "pii_model": sum(v["metrics"].get("pii_found_by_model", 0) for v in evs),
            "pii_masked": sum(v["metrics"].get("pii_masked", 0) for v in evs),
            "injection_expected": bool(sc.get("notes")), "injection_flagged": bool(state.get("injection_detected")),
            "cost_usd": round(c1 - c0, 4), "calls": n1 - n0, "seconds": round(time.time() - t0),
            "report": f"{sc['id']}/report.html",
        })
    _reset(mission)                                   # la console revient au scénario de démonstration
    summary = summarize(results)
    data = {"backend": llm.BACKEND, "model": llm.model_for(False), "lang": config.lang(),
            "date": time.strftime("%Y-%m-%d %H:%M"), "premask": False, "summary": summary, "scenarios": results}
    (out_root / "scorecard.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (out_root / "scorecard.md").write_text(to_markdown(data))
    (out_root / "scorecard.html").write_text(to_html(data))
    print("\n" + to_markdown(data))
    return data


def summarize(results: list) -> dict:
    v = [c["verdict"] for r in results for c in r["cells"].values()]
    n = lambda k: v.count(k)
    tp, tn, fp, fn = n("TP"), n("TN"), n("FP"), n("FN")
    return {
        "checks": len(v), "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "inconclusive": n("inconclusive"), "missing": n("missing"),
        "accuracy": round((tp + tn) / len(v), 3) if v else None,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "pii_total": sum(r["pii_total"] for r in results),
        "pii_model": sum(r["pii_model"] for r in results),
        "pii_masked": sum(r["pii_masked"] for r in results),
        "injection_cases": sum(r["injection_expected"] for r in results),
        "injection_flagged": sum(r["injection_expected"] and r["injection_flagged"] for r in results),
        "cost_usd": round(sum(r["cost_usd"] for r in results), 4),
        "seconds": sum(r["seconds"] for r in results),
    }


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
    lines = [f"**{s['checks']} {b['checks']}** {b['on']} {len(d['scenarios'])} {b['fict']} · {b['model']} `{d['model']}` "
             f"({d['backend']}) · {d['date']}", "",
             f"- {b['acc']}{c}**{pct(s['accuracy'])}** · {b['prec']} {pct(s['precision'])} · {b['rec']} {pct(s['recall'])}",
             f"- {b['fp']}{c}**{s['FP']}** · {b['fn']}{c}**{s['FN']}** · {b['inc']}{c}{s['inconclusive']}",
             f"- {b['pii']}{c}{s['pii_model']}/{s['pii_total']} {b['pii_ai']}, "
             f"{s['pii_masked']}/{s['pii_total']} {b['pii_mask']}",
             f"- {b['inj']}{c}{s['injection_flagged']}/{s['injection_cases']}",
             f"- {b['cost']}{c}{b['money'](s['cost_usd'])} · {b['dur']}{c}{s['seconds']} s", "",
             f"| {b['scen']} | " + " | ".join(RULES) + f" | {b['pii_col']} | {b['cost_col']} |",
             "|---|" + "---|" * len(RULES) + "---|---|"]
    for r in d["scenarios"]:
        lines.append(f"| {r['id']} | " + " | ".join(sym[r["cells"].get(x, {"verdict": "missing"})["verdict"]] for x in RULES)
                     + f" | {r['pii_model']}/{r['pii_total']} | {b['money'](r['cost_usd'])} |")
    lines += ["", b["legend"]]
    return "\n".join(lines) + "\n"


def to_html(d: dict) -> str:
    s = d["summary"]
    lang, b, sym, pct = _labels(d)
    color = {"TP": "#166534", "TN": "#166534", "FP": "#b91c1c", "FN": "#b91c1c", "inconclusive": "#a16207",
             "missing": "#6b7280"}
    rows = []
    for r in d["scenarios"]:
        cells = "".join(
            f'<td style="color:{color[c["verdict"]]};font-weight:600;white-space:nowrap" '
            f'title="{b["expected"]} {c["expected"]}, {b["got"]} {c["got"]}">'
            f'{sym[c["verdict"]]}</td>' for c in (r["cells"].get(x, {"verdict": "missing", "expected": "", "got": ""})
                                                for x in RULES))
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
<div class="ks">{tiles}</div><div class="t"><table><tr><th>{b["scen"]}</th>{"".join(f"<th>{x}</th>" for x in RULES)}
<th>{b["pii_th"]}</th><th>{b["inj_th"]}</th><th>{b["cost_col"]}</th><th>{b["dur_th"]}</th></tr>{"".join(rows)}</table></div>
<p class="sub" style="margin-top:14px">{html.escape(b["legend"])}</p>
</main></body></html>"""
