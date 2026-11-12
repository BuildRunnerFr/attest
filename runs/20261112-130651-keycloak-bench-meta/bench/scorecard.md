**21 checks** on 3 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-12 13:17

- Accuracy: **100%** · precision 100% · recall 100%
- False findings: **0** · missed non-compliances: **0** · inconclusive: 0
- Personal data: 302/318 spotted by the AI, 318/318 masked in the end
- Injections flagged: 0/0
- Measured cost: $0.66 · duration: 594 s

| Scenario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|---|
| kc-01-kerlann | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | 108/114 | $0.46 |
| kc-02-oceane | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | 108/116 | $0.11 |
| kc-03-menhir | ✔ NC found | ✔ NC found | ✔ NC found | ✔ compliant | ✔ NC found | ✔ compliant | ✔ compliant | 86/88 | $0.10 |

✔ NC found = non-compliance correctly detected · ✔ compliant = compliance confirmed · ✘ FP = false finding · ✘ FN = missed non-compliance · ? = inconclusive

**Per rule**

| Rule | expected NC | TP | FP | FN | TN | ?/— | precision | recall | recall (concluded) |
|---|---|---|---|---|---|---|---|---|---|
| PSI-4.1 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.2 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.3 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.4 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.5 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.6 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.7 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- PSI-4.7 per admin account: 19 admin accounts · TP 1 · FP 0 · FN 0 · TN 18 · undetermined 0 · precision 100% · recall 100% (evidence, verdict)

- Offending items named by the tests : 270 expected · TP 270 · FP 0 · FN 0 · precision 100% · recall 100%
