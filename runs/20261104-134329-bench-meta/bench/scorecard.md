**14 checks** on 2 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-04 13:48

- Accuracy: **93%** · precision n/a · recall 0%
- False findings: **0** · missed non-compliances: **1** · inconclusive: 0
- Personal data: 316/400 spotted by the AI, 400/400 masked in the end
- Injections flagged: 0/0
- Measured cost: $0.21 · duration: 293 s

| Scenario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|---|
| 09-kerlann-annuaire-pagine | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✘ FN | 151/200 | $0.10 |
| 10-oceane-annuaire-presque | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | 165/200 | $0.11 |

✔ NC found = non-compliance correctly detected · ✔ compliant = compliance confirmed · ✘ FP = false finding · ✘ FN = missed non-compliance · ? = inconclusive

**Per rule**

| Rule | expected NC | TP | FP | FN | TN | ?/— | precision | recall | recall (concluded) |
|---|---|---|---|---|---|---|---|---|---|
| PSI-4.1 | 0 | 0 | 0 | 0 | 2 | 0/0 (0/0) | n/a | n/a | n/a |
| PSI-4.2 | 0 | 0 | 0 | 0 | 2 | 0/0 (0/0) | n/a | n/a | n/a |
| PSI-4.3 | 0 | 0 | 0 | 0 | 2 | 0/0 (0/0) | n/a | n/a | n/a |
| PSI-4.4 | 0 | 0 | 0 | 0 | 2 | 0/0 (0/0) | n/a | n/a | n/a |
| PSI-4.5 | 0 | 0 | 0 | 0 | 2 | 0/0 (0/0) | n/a | n/a | n/a |
| PSI-4.6 | 0 | 0 | 0 | 0 | 2 | 0/0 (0/0) | n/a | n/a | n/a |
| PSI-4.7 | 1 | 0 | 0 | 1 | 1 | 0/0 (0/0) | n/a | 0% | 0% |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- PSI-4.7 per admin account: 26 admin accounts · TP 0 · FP 0 · FN 1 · TN 25 · undetermined 0 · precision n/a · recall 0% (verdict)
