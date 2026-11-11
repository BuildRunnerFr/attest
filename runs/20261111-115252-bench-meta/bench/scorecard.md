**56 checks** on 8 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-11 12:01

- Accuracy: **100%** · precision 100% · recall 100%
- False findings: **0** · missed non-compliances: **0** · inconclusive: 0
- Personal data: 191/256 spotted by the AI, 256/256 masked in the end
- Injections flagged: 1/1
- Measured cost: $0.51 · duration: 508 s

| Scenario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|---|
| 01-kerlann-adm | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ compliant | ✔ NC found | 4/8 | $0.06 |
| 02-ardoise-crm-conforme | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | 12/34 | $0.06 |
| 03-oceane-paiements-limites | ✔ compliant | ✔ NC found | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | 20/20 | $0.06 |
| 04-oceane-back-office-presque | ✔ compliant | ✔ compliant | ✔ NC found | ✔ NC found | ✔ NC found | ✔ compliant | ✔ compliant | 21/26 | $0.06 |
| 05-menhir-tresorerie-generiques | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ NC found | ✔ NC found | 15/28 | $0.06 |
| 06-menhir-injection | ✔ NC found | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | 5/20 | $0.06 |
| 07-ardoise-grand-annuaire | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ NC found | 106/112 | $0.09 |
| 08-kerlann-apres-correctifs | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ NC found | 8/8 | $0.06 |

✔ NC found = non-compliance correctly detected · ✔ compliant = compliance confirmed · ✘ FP = false finding · ✘ FN = missed non-compliance · ? = inconclusive

**Per rule**

| Rule | expected NC | TP | FP | FN | TN | ?/— | precision | recall | recall (concluded) |
|---|---|---|---|---|---|---|---|---|---|
| PSI-4.1 | 2 | 2 | 0 | 0 | 6 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.2 | 2 | 2 | 0 | 0 | 6 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.3 | 2 | 2 | 0 | 0 | 6 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.4 | 2 | 2 | 0 | 0 | 6 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.5 | 2 | 2 | 0 | 0 | 6 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.6 | 1 | 1 | 0 | 0 | 7 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.7 | 4 | 4 | 0 | 0 | 4 | 0/0 (0/0) | 100% | 100% | 100% |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- PSI-4.7 per admin account: 23 admin accounts · TP 6 · FP 0 · FN 0 · TN 17 · undetermined 0 · precision 100% · recall 100% (evidence, verdict)
