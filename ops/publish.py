"""Range les sorties d'une exécution du workflow real-audit dans la branche real-results
et ajoute une ligne au registre (ledger.jsonl) : dépense, résultat, commit testé.

  python ops/publish.py <sorties> <branche real-results extraite> <type> <backend> [note]
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

KEEP = {"result.json", "report.pdf", "manifest.json", "trail.jsonl", "scorecard.json", "scorecard.md",
        "interpretation.json", "catalogue.json", "run.log", "lab.log"}


def summarize(src: Path) -> dict:
    """Quelques indicateurs lisibles sans ouvrir le rapport."""
    s = {}
    for sc in src.rglob("scorecard.json"):
        d = json.loads(sc.read_text())
        d = d.get("summary", d)
        s["bench"] = {k: d.get(k) for k in ("checks", "TP", "TN", "FP", "FN", "inconclusive", "accuracy",
                                             "pii_total", "pii_model", "pii_masked", "injection_cases",
                                             "injection_flagged", "cost_usd", "seconds")}
    audits = []
    for res in sorted(src.rglob("result.json")):
        if "bench" in s and res.parent.parent.name == "bench":
            continue                                  # le banc est déjà résumé
        try:
            d = json.loads(res.read_text())
        except Exception:
            continue
        entries = d.get("entries", [])
        audits.append({
            "folder": str(res.parent.relative_to(src)),
            "controls": len(entries),
            "status_before": [e.get("status_before") for e in entries],
            "status_after": [e.get("status_after") for e in entries if e.get("status_after")],
            "evidence_errors": sum(bool(e.get("evidence_error")) for e in entries),
            "opinion_initial": d.get("opinion_initial"), "opinion_final": d.get("opinion_final"),
            "injection_detected": d.get("injection_detected"),
            "cost_usd": (d.get("usage") or {}).get("total_usd"),
        })
    if audits:
        s["audits"] = audits
    return s


def main():
    src, root, kind, backend = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    note = sys.argv[5] if len(sys.argv) > 5 else ""
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    dest = root / "runs" / f"{stamp}-{kind}-{backend}"
    dest.mkdir(parents=True, exist_ok=True)
    if src.exists():
        for p in src.rglob("*"):
            if p.is_file() and p.name in KEEP and not (kind == "bench" and p.name == "report.pdf"):
                q = dest / p.relative_to(src)
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, q)
    uf = Path(os.getenv("ATTEST_USAGE_FILE", "/nonexistent"))
    usage = json.loads(uf.read_text()) if uf.exists() else {}
    entry = {
        "id": dest.name, "utc": stamp, "kind": kind, "backend": backend, "note": note,
        "commit": os.getenv("GITHUB_SHA", "")[:7], "workflow_run": os.getenv("GITHUB_RUN_ID", ""),
        "status": os.getenv("RUN_STATUS", "unknown"),
        "budget_spent_usd": usage.get("budget_spent_usd", 0.0), "priced_usd": round(usage.get("total_usd", 0.0), 4),
        "unpriced": usage.get("unpriced", []), **summarize(src),
    }
    (dest / "summary.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2))
    with open(root / "ledger.jsonl", "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
