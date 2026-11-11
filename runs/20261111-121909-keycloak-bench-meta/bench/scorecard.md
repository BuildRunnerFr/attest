**21 checks** on 3 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-11 12:31

- Accuracy: **90%** · precision 91% · recall 100%
- False findings: **1** · missed non-compliances: **0** · inconclusive: 1
- Personal data: 301/318 spotted by the AI, 318/318 masked in the end
- Injections flagged: 0/0
- Measured cost: $0.72 · duration: 700 s

| Scenario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|---|
| kc-01-kerlann | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | 103/114 | $0.50 |
| kc-02-oceane | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ? | 112/116 | $0.13 |
| kc-03-menhir | ✔ NC found | ✘ FP | ✔ NC found | ✔ compliant | ✔ NC found | ✔ compliant | ✔ compliant | 86/88 | $0.08 |

✔ NC found = non-compliance correctly detected · ✔ compliant = compliance confirmed · ✘ FP = false finding · ✘ FN = missed non-compliance · ? = inconclusive

**Per rule**

| Rule | expected NC | TP | FP | FN | TN | ?/— | precision | recall | recall (concluded) |
|---|---|---|---|---|---|---|---|---|---|
| PSI-4.1 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.2 | 1 | 1 | 1 | 0 | 1 | 0/0 (0/0) | 50% | 100% | 100% |
| PSI-4.3 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.4 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.5 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.6 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-4.7 | 1 | 1 | 0 | 0 | 1 | 1/0 (0/0) | 100% | 100% | 100% |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- PSI-4.7 per admin account: 19 admin accounts · TP 1 · FP 0 · FN 0 · TN 10 · undetermined 8 · precision 100% · recall 100% (evidence, inconclusive, verdict)
