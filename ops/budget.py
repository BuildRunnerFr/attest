"""Plafond de dépense des audits réels lancés par le workflow real-audit.

  python ops/budget.py <ledger.jsonl> <plafond_usd>

Affiche la dépense cumulée des exécutions sur les modèles Meta (estimation prudente : prix publiés,
plus une majoration pour SAM dont le prix n'est pas publié). Dans GitHub Actions, écrit aussi
spent=…, remaining=… et ok=true|false dans $GITHUB_OUTPUT.
"""
import json
import os
import sys
from pathlib import Path

RESERVE_USD = 1.0          # une exécution n'est lancée que s'il reste au moins ce montant


def spent(ledger: Path) -> float:
    if not ledger.exists():
        return 0.0
    total = 0.0
    for line in ledger.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("backend") == "meta":
                total += float(row.get("budget_spent_usd") or 0)
    return total


def main():
    ledger, cap = Path(sys.argv[1]), float(sys.argv[2])
    s = spent(ledger)
    remaining = max(0.0, cap - s)
    ok = remaining >= RESERVE_USD
    print(f"Dépense cumulée (estimation prudente) : {s:.2f} $ / plafond {cap:.2f} $ — reste {remaining:.2f} $"
          + ("" if ok else " — PLAFOND ATTEINT, aucun appel ne sera envoyé"))
    out = os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"spent={s:.4f}\nremaining={remaining:.4f}\nok={'true' if ok else 'false'}\n")


if __name__ == "__main__":
    main()
