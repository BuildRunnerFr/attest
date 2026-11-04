# 3-minute demo script

## Before recording

```bash
# terminal 1: audited console + Studio (http://127.0.0.1:8000)
bash scripts/start.sh
# terminal 2: warm-up run, caches the work programme and the test scripts
source .venv/bin/activate; set -a; source .env; set +a
export ATTEST_LANG=en ATTEST_AUDITOR="<your name>" ATTEST_APPROVER="IAM owner"
python -m attest run --reset-lab --remediate --approve-all --out runs/warmup
```

Arrange the screen: terminal on the left, the browser on the right.
Record the live run once at normal speed; speed up the waiting parts in editing.

## Script

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:15 | Report filling live: red rows outlined, e-mails masked | "Banks prove DORA compliance with screenshots and spreadsheets. Attest tested this console, fixed it with the owner's approval and re-tested it in 77 seconds — the way an auditor is required to." ¹ |
| 0:15–0:45 | Attest Studio: tick DORA 9(4), RTS 21 and the internal policy, pick the IAM console, *Draft the work programme* | "Pick the regulation, pick the system. Muse Spark reads the text and drafts the audit programme — and every control must quote the article word for word. The quote is checked by code; if it is not in the text, the control is rejected." |
| 0:45–1:00 | Review page: verified quotes, threshold sources, "document review / interview" badges; type your name, approve | "DORA is principle-based, so every threshold says where it comes from: our policy, or a public standard flagged as a proposal. What cannot be tested automatically is listed as not covered. Nothing runs until an auditor approves." |
| 1:00–1:35 | Live report: tests, screenshots, SAM outlines, masked personal data | "Each control becomes a read-only test; the verdict comes from that script, never from the model. Muse Spark reads the screenshot to corroborate, and SAM 3.1 outlines the proving rows and masks personal data — with a deterministic safety net, because privacy cannot depend on a model's recall." |
| 1:35–2:05 | Studio again: RTS 16 + secure-development policy, target = code repository; findings with outlined lines and masked secrets | "Same agent, another target: a payment microservice. Hard-coded secrets, TLS verification off, MD5 passwords, a production export in the test data — each finding points at the exact lines, and the secrets themselves are masked in the evidence." |
| 2:05–2:25 | CLI remediation: change request, type `y`; re-test green; shared account → action plan | "Fixing is not the auditor's job. Attest drafts the change, the system owner approves it, it is logged and re-tested. A shared admin account is an ownership decision, so it becomes an action plan." |
| 2:25–2:45 | Evaluation scorecard (8 fictitious banks) + `attest verify` on an edited screenshot | "We do not train the model, we measure the agent: 56 checks on eight fictitious banks with known answers. And every piece of evidence is sealed in a hash chain — edit one pixel and verification fails." |
| 2:45–3:00 | README table of Meta models, `ATTEST_BACKEND=local`, annex C cost | "Muse Spark plans, codes and reviews evidence; SAM 3.1 makes it precise and private; and the agent is designed to run on Muse Glimmer inside the bank. Twelve cents of model calls for that whole audit. Attest: audits that test, not read." ² |

Sources for the numbers spoken above (do not say a number that is not in the run ledger):

1. 77 s end to end, 7 controls tested, 6 non-compliances, 5 fixes re-tested compliant: ledger run
   `20261103-234915-iam-meta` (`duration_s` = 77 in its `result.json`; changes were demo pre-approvals, so the
   recorded run has no human wait — a live take with interactive approval will be longer).
2. $0.121 of Muse Spark 1.3 calls for that run (`priced_usd` 0.1209); SAM 3.1 has no public price and is not included.
   56 checks on eight fictitious banks, 0 false finding, 0 missed: ledger run `20261103-232326-bench-meta`.
   Muse Glimmer: supported backend, not yet benchmarked on real hardware — say "designed to run", never "runs".

## Fallbacks

- API slow or rate-limited: `ATTEST_WORKERS=3`, or show the warm-up run's report and narrate.
- Tamper demo: `cp runs/demo/evidence/C1_before.png /tmp/b.png`, paint on it, run `verify`, restore the copy.
- Injection demo: restart the lab with `LAB_INJECTION=1`, run without `--remediate`, show the banner in the report.
