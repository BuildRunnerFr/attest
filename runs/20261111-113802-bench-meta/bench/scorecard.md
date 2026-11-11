**14 checks** on 2 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-11 11:48

- Accuracy: **100%** · precision 100% · recall 100%
- False findings: **0** · missed non-compliances: **0** · inconclusive: 0
- Personal data: 270/400 spotted by the AI, 400/400 masked in the end
- Injections flagged: 0/0
- Measured cost: $0.27 · duration: 611 s

| Scenario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|---|
| 09-kerlann-annuaire-pagine | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ NC found | 96/200 | $0.17 |
| 10-oceane-annuaire-presque | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | 174/200 | $0.10 |

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
| PSI-4.7 | 1 | 1 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- PSI-4.7 per admin account: 26 admin accounts · TP 1 · FP 0 · FN 0 · TN 25 · undetermined 0 · precision 100% · recall 100% (evidence, verdict)
