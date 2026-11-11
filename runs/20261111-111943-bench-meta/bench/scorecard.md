**14 checks** on 2 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-11 11:30

- Accuracy: **86%** · precision n/a · recall 0%
- False findings: **0** · missed non-compliances: **0** · inconclusive: 2
- Personal data: 357/400 spotted by the AI, 400/400 masked in the end
- Injections flagged: 0/0
- Measured cost: $0.27 · duration: 623 s

| Scenario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|---|
| 09-kerlann-annuaire-pagine | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ? | 165/200 | $0.18 |
| 10-oceane-annuaire-presque | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ? | 192/200 | $0.10 |

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
| PSI-4.7 | 1 | 0 | 0 | 0 | 0 | 2/0 (1/0) | n/a | 0% | n/a |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- PSI-4.7 per admin account: 26 admin accounts · TP 0 · FP 0 · FN 1 · TN 0 · undetermined 26 · precision n/a · recall 0% (inconclusive)
