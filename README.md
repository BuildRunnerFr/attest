# Attest — the DORA compliance auditor that tests instead of reading

**Attest is an AI agent that audits a bank's systems against DORA: it tests them read-only, seals and masks the
evidence, routes fixes to the system owner for approval, re-tests, and writes the report a CISO signs.**
Built on **Muse Spark 1.3** (work programme, test scripts, evidence review, change requests) and **SAM 3.1**
(proving rows outlined, personal data masked). Meta Global AI Developer Hackathon · track "Build for Your World".

**Why it matters:** DORA makes every EU bank prove its ICT controls work. Today that proof is screenshots pasted into
spreadsheets, re-checked by hand months later. Attest turns it into a sealed, re-playable test: in real run
`20261104-083850-iam-meta`, a full IAM console audit (7 controls tested, 6 non-compliances, 5 fixes applied after a
demo pre-approval and re-tested compliant, sealed report) took 62 s and $0.13 of Muse Spark calls.

Measured on real runs with the Meta Model API (ids from our [run ledger](https://github.com/BuildRunnerFr/attest/blob/real-results/ledger.jsonl); Muse Spark cost, SAM 3.1 has no public price).
Each ledger entry carries the GitHub Actions `workflow_run` id of the run that produced it, viewable at
`https://github.com/BuildRunnerFr/attest/actions/runs/<workflow_run>`:

| Run | Result | Cost |
|---|---|---|
| Benchmark, 8 fictitious banks, 7 runs (`20261103-232326`, `20261103-235819`, `20261104-020142`, `20261104-064005`, `20261104-080238`, `20261104-095918`, `20261104-115711` `-bench-meta`) | **56/56 checks correct on every run, 0 false finding, 0 missed, prompt injection flagged 7/7**, 256/256 personal-data items masked each time | $0.50–0.53, 300–417 s per run |
| IAM console audit with remediation, 5 runs (`20261103-234915`, `20261104-001606`, `20261104-063210`, `20261104-083850`, `20261104-102217` `-iam-meta`) | **6 non-compliances on every run; 5 fixes applied after (demo) pre-approval and re-tested compliant**, 1 action plan | $0.12–0.13, 62–87 s per run |
| Code repository audit, 7 runs (`20261103-230340`, `20261103-234658`, `20261104-002236`, `20261104-060119`, `20261104-062938`, `20261104-083648`, `20261104-102820` `-code-meta`) | **7/7 planted flaws found on 6 of 7 runs**, each with its evidence (the work programme, re-planned on each run, tested them as 7 to 10 controls); on `20261104-002236`, 6 found, 1 sent to human review because the screenshot did not back the script, 1 evidence error (fixed since: a missing file is now a technical error, never a finding) | $0.33–0.78, 190–390 s per run |

Caveat: the test set is small, fictitious and built by us. Encouraging, not a proof of general accuracy.

![Executive summary of an Attest report](docs/img/report-summary.png)
*Executive summary, from real run `20261104-063210-iam-meta` (English PDF report).*

## Why

Banks must prove to supervisors that their security controls work. Under **DORA** (EU Regulation 2022/2554,
applicable since 17 January 2025) that proof is still mostly built by hand: someone reads the policy, logs into
each system, takes screenshots, pastes them into a spreadsheet, and an auditor re-checks it all months later.
Attest runs that audit the way a bank's second line of defence must run it: independent, read-only, evidenced,
with human approval for every change.

## Attest Studio: pick an article, pick a target, approve, audit

`python -m attest.studio` opens a local web app:

1. **Framework**: tick verified excerpts of DORA (art. 9(3), 9(4)) and of the technical standard RTS 2024/1774
   (art. 6–7 cryptography, 12 logging, 16 development, 21 access control), add an internal policy, or upload your own
   text (.md, .txt, .pdf).
2. **Target**: the IAM admin console, or a **code repository** (a fictitious SEPA payment microservice with 7 planted
   flaws: hard-coded secrets, TLS verification disabled, MD5 password hashing, no SAST in CI, unpinned dependencies,
   a production export in the test fixtures, and no logging of authentication successes and failures).
3. **Grounded interpretation** (Muse Spark): every requirement must quote the text **word for word** — the quote is
   checked by code, and a requirement whose quote cannot be found is rejected. Every threshold says where it comes from
   (your policy, a named public standard marked *proposal*, or the text). Requirements are triaged into *testable
   here*, *document review* and *interview*; the report lists what Attest did **not** cover.
4. **Human approval**: the auditor ticks the controls, adjusts severities and signs. Nothing is tested before that.
5. **Audit**: the same pipeline runs and the report fills in live.

### Does it interpret DORA correctly?

Not on its own, by design. DORA and its RTS are principle-based: they require "strong authentication" or limiting
"generic and shared user accounts", never "12 characters" or "15 minutes". Banks translate them into internal policies,
and that is what Attest tests. Given a policy, Muse Spark turned 7 rules into a faithful work programme on our first real
run; given an ambiguous rule, a generated test was too strict and human review caught it (see
[`examples/README.md`](examples/README.md)). Given the regulation alone, thresholds are flagged as proposals to approve.
Quote verification, testability triage and mandatory approval are there because interpretation is where AI can be wrong.

## What happens in one run

| Step | What Attest does | Meta model |
|---|---|---|
| 1. Work programme | Reads the framework (DORA art. 9(4), RTS 2024/1774 art. 12 and 21, internal policy) and writes a catalogue of testable controls with severity, risk and recommendation. Cached for auditor review. | **Muse Spark 1.3** |
| 2. Test | Writes one read-only Python test per control, statically checked, executed with a read-only service account. The **verdict comes from the script, never from the model**. Scripts are kept in a reviewable library and replayed on later runs. | **Muse Spark 1.3** |
| 3. Evidence | Captures the admin page, asks the model whether it corroborates the test (disagreement → *needs review*), and spots prompt-injection attempts. Muse Spark only receives a copy of the screenshot on which the deterministic net has already blacked out the personal data found in the page (the benchmark alone sends synthetic data unmasked, to measure the model's own recall). | **Muse Spark 1.3** (vision) |
| 4. Annotate | Snaps the model's boxes onto what is really on screen: proving rows are outlined, e-mails and IPs are masked in every image Attest keeps or puts in a report. SAM 3.1 itself still receives the raw screenshot (through the Meta Model API in our runs) to segment it: a known limit, so in confidential mode it has to run inside the bank too. Masking coverage is measured against the page DOM. | **SAM 3.1** |
| 5. Remediate (optional) | Drafts a minimal change request per finding. A **human system owner approves it** (the auditor cannot); it is applied with a separate change account, a ticket, and logged by the audited system (DORA 9(4)(e)). Organisational fixes (a shared admin account) become an action plan with an owner and a due date. | **Muse Spark 1.3** |
| 6. Re-test and report | Replays the same script, seals new evidence, issues an HTML + PDF report with an executive opinion, findings in Criteria / Condition / Probable cause / Risk / Recommendation form (the cause is marked as an AI hypothesis to confirm with the owner), a traceability matrix, an evidence register, measured AI cost and a hash-chained audit trail. | — |

**Confidential mode:** `ATTEST_BACKEND=local` points the same agent at **Muse Glimmer** served inside the bank
(llama.cpp, vLLM, SGLang). This is a supported backend, **not yet benchmarked on real hardware**: every measured result
in this README comes from the Meta Model API. For a bank it is not a nice-to-have: sending audit evidence to an external
model API makes that API an ICT third-party provider under DORA. See [docs/BUSINESS_CASE.md](docs/BUSINESS_CASE.md).

![A finding with sealed before/after evidence and an approved change](docs/img/finding.png)
*A finding with sealed before/after evidence and a (demo) pre-approved change, from real run `20261104-063210-iam-meta`.*

## Beyond the demo console

- **A real Keycloak.** Attest audits Keycloak 26 through a read-only gateway (GET only, service account limited to
  `view-realm` and `view-users`). On three fictitious realms of 180 to 260 accounts: **21 / 21 checks correct**, 0 missed,
  0 false findings, and the 270 offending accounts named exactly (`20261112-130651-keycloak-bench-meta`). The first
  run scored 19 / 21; the one "false finding" turned out to be an error in our own ground truth.
- **HR ↔ access reconciliation.** Leavers still enabled, orphan and dormant accounts, segregation-of-duties conflicts,
  movers keeping old rights, overdue privileged reviews: six rules that each join the HR register with the accounts.
  **18 / 18 checks correct**, 0 missed, 0 false findings, 17 / 17 offending accounts named with no extra
  (`20261112-132525-lifecycle-bench-meta`; the first run scored 14 / 18 with one false finding).

Details, how to run them, and what the first runs got wrong: [docs/TARGETS.md](docs/TARGETS.md).

## Built the way a bank would have to run it

- **Independence and least privilege**: tests use a read-only token; even if a generated script tried to write, the
  audited system would refuse (403). Before that, a static guard and a runtime audit hook refuse write calls, file and process access, and any network destination other than the audited system (`tests/test_sandbox.py` replays the bypasses our own red-team review found).
- **Segregation of duties**: changes need an approver who is not the lead auditor; Attest refuses to run otherwise.
- **Change management**: every fix has a ticket, an approver, a journal entry on the audited system and a re-test (DORA 9(4)(e)).
- **Tamper-evident evidence**: every event and file is sealed in a SHA-256 hash chain. `python -m attest verify runs/<run>` detects any edited screenshot, script or report.
- **Prompt-injection resistant**: data from the audited system is treated as untrusted; the verdict is deterministic; injection attempts are flagged in the report (`LAB_INJECTION=1` to try it).
- **Privacy that does not depend on a model**: personal data is masked in two layers — what Muse Spark spots, refined by
  SAM 3.1, plus a deterministic safety net on the page text (e-mails, IPs, IBANs, phone numbers). Our first real run
  showed why: the model found all 8 items but its IP boxes were 40 px short, leaving prefixes readable. The report now
  shows both figures. Personal data in the report text is pseudonymised; unmasked screenshots are never kept, and
  Muse Spark only sees a pre-masked copy. One gap remains: SAM 3.1 receives the raw screenshot to segment it, so in
  confidential mode it must run inside the bank as well.
- **Measured cost**: tokens are counted on every call and priced from `pricing.toml` (sources cited).
- **Not everything is auto-fixed**: a shared admin account is an ownership decision, so it gets an action plan, not a PATCH.
- **No opinion without evidence**: when no control is conclusive, or more than half are inconclusive with no high or critical finding, the report issues a *Disclaimer of opinion* (ISA 705 §9; ISACA ITAF 1401) instead of a rating.
- **Per-rule bench metrics**: the benchmark now scores precision and strict recall for each PSI-4.x rule; rescoring ledger `20261104-095918-bench-meta` gives 100 % precision and 100 % strict recall on all 7 rules (15 TP, 41 TN, 0 FP, 0 FN), and PSI-4.7 per account 6 TP, 17 TN, 0 FP, 0 FN over 23 admin accounts.
- **A measured miss, fixed and re-measured**: on the stress scenario `09` (721 accounts, 100 per page, one generic admin on page 7) the PSI-4.7 library script written by Muse Spark read only page 1 and missed the planted admin (`20261104-134329-bench-meta`, `20261104-204107-bench-meta`: 13/14, 1 missed). The sandbox now records the pagination the target declares (`Link rel="next"`, `X-Total-Pages`) and refuses a "pass" on a partially read population; the rejected script is rewritten with that reason, and the evidence screenshot is the page that shows the offending account. Re-measured on `20261111-113802-bench-meta`: 14/14 on `09` and `10`, the admin on page 7 found and shown, 0 false findings on the near-miss twin.

## Quickstart

Requires Python 3.11+ (tested on 3.12 and 3.13). No API key needed to try it: the `mock` backend runs offline.
Mock mode returns canned, partly French text; real English outputs are in [`examples/`](examples/) and on the
[`real-results`](https://github.com/BuildRunnerFr/attest/tree/real-results) branch.

```bash
git clone https://github.com/BuildRunnerFr/attest.git && cd attest
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python -m playwright install chromium

cp .env.example .env                      # add MODEL_API_KEY; without a key, start.sh switches to mock
python -m pytest -q                       # optional: pip install -r requirements-dev.txt first
bash scripts/start.sh                     # one command: audited console + Studio, opens http://127.0.0.1:8000
```

Or step by step:

```bash
python -m lab.app                         # terminal 1: the audited system (fictitious bank console)
set -a; source .env; set +a               # terminal 2
export ATTEST_BACKEND=mock                # only if you have no MODEL_API_KEY
python -m attest.studio                                # web app: http://127.0.0.1:8000
python -m attest run --reset-lab                       # or the CLI: read-only audit
python -m attest run --reset-lab --remediate           # + change requests, approved interactively
python -m attest verify runs/<run-folder>              # integrity check
```

The report (`runs/<run>/report.html`) refreshes live during the audit; `report.pdf` is written at the end.
A real IAM audit with remediation cost $0.12–0.13 of Muse Spark calls and 62–87 s (ledger runs `20261103-234915`,
`20261104-001606`, `20261104-063210`, `20261104-083850`, `20261104-102217` `-iam-meta`); what the
first real runs measured and revealed is in [`examples/README.md`](examples/README.md) and
[docs/BUSINESS_CASE.md](docs/BUSINESS_CASE.md).
Useful flags: `--lang en`, `--approve-all --approver "IAM owner"` (pre-approved, demo only), `--fresh`
(rewrite tests instead of replaying the library), `--replan` (redo the work programme).

## Evaluation, not training

We do not fine-tune anything: the model is not the judge, and a bank cannot hand over labelled data. Instead,
`python -m attest bench` audits **8 fictitious banking systems** with known ground truth (compliant system, threshold
edge cases, generic accounts, prompt injection, a 56-account directory) and reports accuracy, false findings, missed
non-compliances, privacy masking and cost. See [docs/EVALUATION.md](docs/EVALUATION.md).

Eight real runs of the same benchmark (Muse Spark 1.3 + SAM 3.1; the first from `examples/`, the other seven from the run ledger):

| Run | Checks correct | False findings / missed | Injection | Personal data spotted by the model / masked | Cost, time |
|---|---|---|---|---|---|
| First run, 2 Nov 2026 ([scorecard](examples/evaluation-en/scorecard.md)) | 56/56 | 0 / 0 | flagged | 178/256 (70 %) / 256/256 | $0.65, 240 s |
| Replay in GitHub Actions, ledger `20261103-232326-bench-meta` | 56/56 | 0 / 0 | flagged | 87/256 (34 %) / 256/256 | $0.53, 300 s |
| Stability run, ledger `20261103-235819-bench-meta` | 56/56 | 0 / 0 | flagged | 183/256 (71 %) / 256/256 | $0.50, 334 s |
| Stability run, ledger `20261104-020142-bench-meta` | 56/56 | 0 / 0 | flagged | 197/256 (77 %) / 256/256 | $0.50, 370 s |
| Stability run, ledger `20261104-064005-bench-meta` | 56/56 | 0 / 0 | flagged | 221/256 (86 %) / 256/256 | $0.51, 417 s |
| Stability run, ledger `20261104-080238-bench-meta` | 56/56 | 0 / 0 | flagged | 191/256 (75 %) / 256/256 | $0.52, 387 s |
| Stability run, ledger `20261104-095918-bench-meta` | 56/56 | 0 / 0 | flagged | 181/256 (71 %) / 256/256 | $0.51, 312 s |
| Stability run, ledger `20261104-115711-bench-meta` | 56/56 | 0 / 0 | flagged | 176/256 (69 %) / 256/256 | $0.52, 384 s |

Verdicts were identical on all eight runs (56/56, 0 false finding, 0 missed, injection flagged). On the seven ledger runs,
the model's own recall of personal data averaged 69 % and ranged from 34 % to 86 %, which is why masking never depends on it: the deterministic
safety net masked 256/256 every time. Each ledger run cost $0.50–0.53 and took 300–417 s. A small, self-built test set: encouraging, not a proof of general accuracy.

## Repository

```
attest/          the agent: Studio, grounded interpretation, pipeline, prompts, sandbox, SAM client, evidence,
                 audit trail, report, evaluation bench
lab/             the audited systems behind one read-only gateway: fictitious IAM console (read-only and change
                 accounts), fictitious code repository (lab/repos), HR register and entitlements (access lifecycle),
                 and the evaluation scenarios
connectors/      real systems: read-only audit gateway for Keycloak, test realms and their ground truth
exigences/       the framework: verified excerpts of DORA and RTS 2024/1774 (library/) and fictitious internal policies
mission/         engagement letter (scope, owner, auditor, classification, remediation deadlines)
controls/        work programmes drafted by AI, kept for auditor review
library/         test scripts kept for review and replay (continuous control monitoring)
docs/            architecture and threat model, business case, demo script
tests/           unit and end-to-end tests (mock mode, also run in CI)
```

## Limitations

- Tests read configuration through an API; they do not test the strength of MFA factors themselves.
- AI-drafted work programmes and scripts must be reviewed by an auditor before they count as validated; the report says so.
- Apart from Keycloak (a real product, on test realms), the audited systems are demos behind a read-only gateway.
  Other connectors (Entra ID, Okta, CyberArk, cloud IAM, GitHub/GitLab) are the next step; adding a target means
  describing its read-only interface in `attest/targets.py`, as `connectors/keycloak` does.
- Regulation excerpts are quoted from the official English text; check EUR-Lex before external use.

## Disclosure

Built during the hackathon with an AI coding assistant (Claude). Domain framing, review and testing by the author.
All data, people and the bank are fictitious.
