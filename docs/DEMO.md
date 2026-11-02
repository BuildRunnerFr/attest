# 3-minute demo script

## Before recording

```bash
# terminal 1
python -m lab.app
# terminal 2
set -a; source .env; set +a
export ATTEST_LANG=en ATTEST_AUDITOR="<your name>" ATTEST_APPROVER="IAM owner"
python -m attest run --reset-lab --remediate --approve-all --out runs/warmup   # warm-up: caches programme + scripts
```

Arrange the screen: terminal on the left, the browser on the right with `runs/demo/report.html` ready to open.
Record the live run once at normal speed; speed up the waiting parts in editing.

## Script

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:15 | Report filling live, red rows outlined, e-mails masked | "Banks prove DORA compliance with screenshots and spreadsheets. Attest audits a system in about a minute — the way an auditor is required to." |
| 0:15–0:35 | Engagement letter + framework file | "Attest takes the regulation — DORA article 9, the technical standard on access control — and our internal policy, and Muse Spark writes the audit work programme." |
| 0:35–1:10 | `python -m attest run --reset-lab --remediate --fresh --out runs/demo`; report refreshing | "For each control, Muse Spark writes a read-only test. The verdict comes from that script, never from the model. Then it reads the screenshot to corroborate it, and SAM 3.1 outlines the proving rows and masks every e-mail and IP before the evidence leaves the system." |
| 1:10–1:50 | Change request in the terminal, type `y` | "Fixing is not the auditor's job. Attest drafts a minimal change request; the system owner approves it — here, me as IAM owner. It is applied with a separate change account, logged by the system, and re-tested with the same script." |
| 1:50–2:10 | Opinion moves Unsatisfactory → Needs improvement; F-03 action plan | "Five findings closed and verified. The shared admin account is not something you PATCH: it becomes an action plan with an owner and a deadline." |
| 2:10–2:35 | Edit a screenshot, run `python -m attest verify runs/demo` → tampering detected; optional injection banner | "Every event and file is sealed in a hash chain. Change one pixel of the evidence and verification fails. Text on the audited system that tries to instruct the AI is ignored and reported." |
| 2:35–2:55 | README table of Meta models, `ATTEST_BACKEND=local`, annex C cost | "Muse Spark plans, codes and reviews evidence. SAM 3.1 makes the evidence precise and private. And with Muse Glimmer the whole agent runs inside the bank — because sending audit evidence to an external API is itself a DORA third-party risk. This run cost a few cents." |
| 2:55–3:00 | Logo / repo URL | "Attest. Audits that test, not read." |

## Fallbacks

- API slow or rate-limited: `ATTEST_WORKERS=3`, or show the warm-up run's report and narrate.
- Tamper demo: `cp runs/demo/evidence/C1_before.png /tmp/b.png`, paint on it, run `verify`, restore the copy.
- Injection demo: restart the lab with `LAB_INJECTION=1`, run without `--remediate`, show the banner in the report.
