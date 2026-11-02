# Business case — feasibility, cost, deployment

Written from the point of view of a CISO office / head of cyber strategy at a large EU bank.
Figures marked **(assumption)** are illustrative and must be replaced with internal data.

## 1. Problem and users

- **Who**: second line of defence (IT risk, cyber compliance), internal audit (third line), CISO office.
- **Pain**: DORA (applicable since 17 January 2025) turns ICT controls into a recurring, evidenced obligation.
  For each system, someone gathers screenshots and exports, maps them to requirements, writes findings, chases fixes and
  re-tests. The work is repetitive, slow, hard to reproduce and the evidence is easy to dispute.
- **What Attest changes**: configuration-level controls are tested automatically, read-only, with sealed and masked
  evidence, a reviewable test library, change requests routed to the system owner and verified closure. Auditors spend
  their time on judgment, not on screenshots.

## 2. What is realistic — and what is not

| Realistic now | Not in scope (yet) |
|---|---|
| Controls readable through an API or an admin page: MFA enforcement, password and lockout policy, session timeout, logging flags, privileged-account inventory, generic accounts | Judgment on the adequacy of a policy or a process |
| Continuous monitoring by replaying validated scripts | Effectiveness testing of the MFA factors themselves |
| Evidence packs, findings, action plans, re-tests | Interviews and walkthroughs (roadmap: Muse Voice Transcribe for interview notes, "declared vs observed") |

## 3. Cost

Every run measures its own tokens and prices them from `pricing.toml` (report, annex C). List prices used:
Muse Spark 1.3 **$1.25 / $4.25 per million input / output tokens** (source cited in `pricing.toml`).
SAM 3.1 price was not found in public sources: fill it in from the Meta console.

**Measured on the first real run** (2 November 2026, Meta Model API, 7 controls, cached work programme and scripts,
remediation with interactive approval — see [`examples/README.md`](../examples/README.md)):

| Item | Measured |
|---|---|
| Muse Spark 1.3 calls | 18 (12 evidence reviews + 6 change requests) |
| Tokens | 22,663 input · 25,181 output (reasoning makes output larger than input) |
| Muse Spark cost | **$0.135** for the whole engagement, ≈ $0.0075 per call |
| SAM 3.1 | 12 images, 15 s in total; price not public |
| Wall-clock | 29 s to test and evidence 7 controls · 8 s to re-test 5 fixes · 108 s end to end including about a minute of human approvals |

Estimates for other runs, scaled from those measurements:

| Scenario | Model calls | Muse Spark cost |
|---|---|---|
| First engagement, nothing cached: work programme + 7 test scripts + the run above | ≈ 26 | ≈ $0.20 |
| Monitoring run: cached programme and scripts, evidence review only, no remediation | ≈ 7 | ≈ $0.05 |

**At scale (assumption)**: 150 critical systems × 10 configuration controls, tested monthly = 1,500 control tests a month.
At ≈ $0.0075 per monitoring control test, that is **≈ $11 a month** of model cost on the API. With **Muse Glimmer**
served internally (30B dense, under 20 GB quantised, runs on a single GPU according to Meta and Nvidia's launch
communication) the marginal model cost is the GPU time the bank already operates.

**People time (assumption, replace with your baseline)**: if a manual control test takes 45 minutes (access, screenshots,
write-up, review) and reviewing an Attest result takes 10, the 1,500 monthly tests above free ≈ 875 hours a month.
The pilot must measure both numbers.

## 4. Deployment path

| Phase | Content | Exit criteria |
|---|---|---|
| Hackathon (now) | Demo console, 7 controls, full loop | Working demo, tests green |
| Pilot — 3 months | 1–3 real IAM systems through read-only APIs (e.g. Entra ID, Okta), local Glimmer backend, auditors review the library | Agreement with manual testing on a sample; zero unapproved change; time per control measured |
| Scale | Connector catalogue; findings exported to the GRC tool; change requests sent to the ITSM tool; trail shipped to the SIEM; scheduled monitoring | Coverage of in-scope configuration controls; remediation lead time |

Team for the pilot **(assumption)**: one product owner from the second line, one or two engineers, auditor reviewers part-time.

## 5. Governance of the tool itself

- **DORA third-party risk**: using an external model API for audit evidence makes the provider an ICT third-party service
  provider (contract provisions, register of information — DORA articles 28 and 30). Confidential evidence therefore goes
  through the **local open-weights backend**; the API is acceptable for non-confidential tests. To be confirmed with
  Legal and Compliance.
- **Model risk management**: the agent is validated like any model: test suite (in `tests/`), benchmark against manual
  testing, monitoring of disagreement and *needs review* rates.
- **EU AI Act**: not obviously in a high-risk category; to be confirmed by Legal. Human oversight, logging and
  transparency are built in regardless (report annex C lists models, calls and human decisions).
- **Data protection**: personal data masked before distribution, raw captures not kept, data minimisation in prompts.
- **Security of the agent**: see the threat model in [ARCHITECTURE.md](ARCHITECTURE.md).

## 6. Risks

| Risk | Mitigation |
|---|---|
| Wrong verdict | Deterministic scripts, reviewed library, screenshot corroboration, *needs review* status |
| Agent changes production on its own | No write access during tests; human approval, allow-list, separate change account, ticket |
| Misreading the regulation | Work programme reviewed by an auditor; references shown on every finding |
| Model or vendor change | Backend abstraction; validated scripts no longer depend on the model |
| Auditor adoption | Output in the audit profession's own format (opinion, Criteria/Condition/Risk/Recommendation, traceability, PDF) |

## 7. KPIs for the pilot

Automation coverage · agreement rate with manual testing · evidence time per control · finding-to-verified-closure lead
time · cost per control test · number of *needs review* and injection alerts.
