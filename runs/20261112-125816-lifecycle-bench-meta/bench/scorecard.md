**18 checks** on 3 fictitious systems · model `muse-spark-1.3` (meta) · 2026-11-12 13:06

- Accuracy: **94%** · precision 100% · recall 100%
- False findings: **0** · missed non-compliances: **0** · inconclusive: 1
- Personal data: 0/0 spotted by the AI, 0/0 masked in the end
- Injections flagged: 0/0
- Measured cost: $0.77 · duration: 468 s

| Scenario | PSI-5.1 | PSI-5.2 | PSI-5.3 | PSI-5.4 | PSI-5.5 | PSI-5.6 | AI PII / total | Cost |
|---|---|---|---|---|---|---|---|---|
| lc-01-kerlann | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | ✔ NC found | 0/0 | $0.49 |
| lc-02-oceane | ✔ compliant | ✔ compliant | ✔ compliant | ✔ compliant | ? | ✔ compliant | 0/0 | $0.14 |
| lc-03-menhir | ✔ NC found | ✔ compliant | ✔ compliant | ✔ NC found | ✔ compliant | ✔ compliant | 0/0 | $0.14 |

✔ NC found = non-compliance correctly detected · ✔ compliant = compliance confirmed · ✘ FP = false finding · ✘ FN = missed non-compliance · ? = inconclusive

**Per rule**

| Rule | expected NC | TP | FP | FN | TN | ?/— | precision | recall | recall (concluded) |
|---|---|---|---|---|---|---|---|---|---|
| PSI-5.1 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-5.2 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-5.3 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-5.4 | 2 | 2 | 0 | 0 | 1 | 0/0 (0/0) | 100% | 100% | 100% |
| PSI-5.5 | 1 | 1 | 0 | 0 | 1 | 1/0 (0/0) | 100% | 100% | 100% |
| PSI-5.6 | 1 | 1 | 0 | 0 | 2 | 0/0 (0/0) | 100% | 100% | 100% |

Strict recall: an expected non-compliance judged inconclusive (?) or missing counts as missed; “recall (concluded)” ignores it. ?/— = inconclusive / missing (of which on expected NC).

- Offending items named by the tests : 17 expected · TP 17 · FP 0 · FN 0 · precision 100% · recall 100%
