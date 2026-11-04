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


def to_markdown(d: dict) -> str:
    s = d["summary"]
    pct = lambda x: "n/a" if x is None else f"{100 * x:.0f} %"
    lines = [f"**{s['checks']} vérifications** sur {len(d['scenarios'])} systèmes fictifs · modèle `{d['model']}` "
             f"({d['backend']}) · {d['date']}", "",
             f"- Justesse : **{pct(s['accuracy'])}** · précision {pct(s['precision'])} · rappel {pct(s['recall'])}",
             f"- Faux constats : **{s['FP']}** · non-conformités manquées : **{s['FN']}** · non concluants : {s['inconclusive']}",
             f"- Données personnelles : {s['pii_model']}/{s['pii_total']} repérées par l'IA, "
             f"{s['pii_masked']}/{s['pii_total']} masquées au final",
             f"- Injections signalées : {s['injection_flagged']}/{s['injection_cases']}",
             f"- Coût mesuré : {s['cost_usd']} $ · durée : {s['seconds']} s", "",
             "| Scénario | " + " | ".join(RULES) + " | PII IA / total | Coût |",
             "|---|" + "---|" * len(RULES) + "---|---|"]
    for r in d["scenarios"]:
        lines.append(f"| {r['id']} | " + " | ".join(SYM[r["cells"].get(x, {"verdict": "missing"})["verdict"]] for x in RULES)
                     + f" | {r['pii_model']}/{r['pii_total']} | {r['cost_usd']} $ |")
    lines += ["", "✔ NC = non-conformité correctement trouvée · ✔ = conformité confirmée · ✘ FP = faux constat · "
              "✘ FN = non-conformité manquée · ? = non concluant"]
    return "\n".join(lines) + "\n"


def to_html(d: dict) -> str:
    s = d["summary"]
    pct = lambda x: "n/a" if x is None else f"{100 * x:.0f} %"
    color = {"TP": "#166534", "TN": "#166534", "FP": "#b91c1c", "FN": "#b91c1c", "inconclusive": "#a16207",
             "missing": "#6b7280"}
    rows = []
    for r in d["scenarios"]:
        cells = "".join(
            f'<td style="color:{color[c["verdict"]]};font-weight:600" title="attendu {c["expected"]}, obtenu {c["got"]}">'
            f'{SYM[c["verdict"]]}</td>' for c in (r["cells"].get(x, {"verdict": "missing", "expected": "", "got": ""})
                                                for x in RULES))
        rows.append(f'<tr><td><a href="{html.escape(r["report"])}">{html.escape(r["id"])}</a><br>'
                    f'<small>{html.escape(r["tests"])}</small></td>{cells}<td>{r["pii_model"]}/{r["pii_total"]}</td>'
                    f'<td>{"⚠ signalée" if r["injection_flagged"] else ("non signalée" if r["injection_expected"] else "")}</td>'
                    f'<td>{r["cost_usd"]} $</td><td>{r["seconds"]} s</td></tr>')
    tiles = "".join(f'<div class="k"><b>{v}</b><span>{k}</span></div>' for k, v in [
        ("justesse", pct(s["accuracy"])), ("faux constats", s["FP"]), ("non-conformités manquées", s["FN"]),
        ("non concluants", s["inconclusive"]), ("PII repérées par l'IA", f'{s["pii_model"]}/{s["pii_total"]}'),
        ("PII masquées au final", f'{s["pii_masked"]}/{s["pii_total"]}'),
        ("injections signalées", f'{s["injection_flagged"]}/{s["injection_cases"]}'), ("coût mesuré", f'{s["cost_usd"]} $')])
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Évaluation Attest</title><style>
body{{font:14px/1.5 system-ui,sans-serif;margin:0;background:#f4f5f7;color:#14171c}}main{{max-width:1150px;margin:0 auto;padding:28px 16px}}
h1{{font:600 26px Georgia,serif;margin:0 0 4px}}p.sub{{color:#5d6470;margin:0 0 20px}}
.ks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:20px}}
.k{{background:#fff;border:1px solid #dfe2e7;border-radius:8px;padding:12px}}.k b{{display:block;font:600 22px Georgia,serif}}.k span{{font-size:12px;color:#5d6470}}
.t{{overflow-x:auto;background:#fff;border:1px solid #dfe2e7;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{padding:8px 10px;border-bottom:1px solid #eceef1;text-align:left;vertical-align:top}}th{{font-size:11px;text-transform:uppercase;color:#5d6470}}
small{{color:#5d6470}}</style></head><body><main>
<h1>Évaluation d'Attest sur {len(d["scenarios"])} systèmes bancaires fictifs</h1>
<p class="sub">{s["checks"]} vérifications avec vérité terrain · modèle {html.escape(d["model"])} ({html.escape(d["backend"])}) · {html.escape(d["date"])}</p>
<div class="ks">{tiles}</div><div class="t"><table><tr><th>Scénario</th>{"".join(f"<th>{x}</th>" for x in RULES)}
<th>PII IA</th><th>Injection</th><th>Coût</th><th>Durée</th></tr>{"".join(rows)}</table></div>
<p class="sub" style="margin-top:14px">✔ NC non-conformité trouvée · ✔ conformité confirmée · ✘ FP faux constat · ✘ FN non-conformité manquée · ? non concluant</p>
</main></body></html>"""
