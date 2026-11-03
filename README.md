# Attest: real runs with the Meta models

This branch is written by the [`real-audit`](../../blob/main/.github/workflows/real-audit.yml) workflow.
Each run audits the fictitious systems of the repository with Muse Spark 1.3 and SAM 3.1 on a GitHub-hosted
runner, then stores its outputs here:

- `ledger.jsonl`: one line per run (date, commit tested, type, outcome, measured cost, key indicators).
- `runs/<date>-<type>-<backend>/`: `summary.json`, `report.pdf`, `result.json`, the hash-chained `trail.jsonl`
  and `manifest.json` (check with `python -m attest verify`), logs. Bench runs keep the scorecard.

Spending is capped: the workflow adds up `budget_spent_usd` over the ledger (published prices plus a cautious
estimate for SAM, whose price is not published) and sends no call once the cap
(`ATTEST_BUDGET_TOTAL_USD`, 130 USD by default) is reached.

All data is synthetic: fictitious bank, fictitious people, `.example` addresses, test IBANs.
