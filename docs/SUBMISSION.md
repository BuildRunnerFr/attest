# Submission — text, video script, bonus prizes

Every number below comes from the real-run ledger (`ledger.jsonl`, run id given) or from `examples/`.
Do not add a number that is not sourced there.

## Submission text (≈ 180 words)

> **Attest — the DORA compliance auditor that tests instead of reading.**
>
> Under DORA, EU banks must prove that their ICT security controls work. Today that proof is screenshots pasted into
> spreadsheets. Attest is an AI agent that runs the audit the way a bank's second line of defence must: Muse Spark 1.3
> turns the regulation and the internal policy into a work programme whose every requirement quotes the text word for
> word (checked by code), writes one read-only test script per control, and reviews the screenshot evidence. The
> verdict comes from the script, never from the model. SAM 3.1 outlines the proving rows and masks personal data, with
> a deterministic safety net. Fixes become change requests that the system owner approves; Attest applies them with a
> separate account, logs them and re-tests. Everything is sealed in a hash-chained audit trail.
>
> Measured on real runs: 56/56 checks correct on 8 fictitious banks in each of 5 runs, 0 false finding, 0 missed,
> prompt injection flagged every time ($0.50–0.53 per run); an IAM audit with 6 non-compliances and 5 fixes re-tested
> compliant on each of 3 runs ($0.12–0.13 per run); 7/7 planted flaws found in a code repository on 4 of 5 runs ($0.48 on
> the run shown). The test set is small and self-built: encouraging, not proof of general accuracy.

Sources: bench `20261103-232326`, `20261103-235819`, `20261104-020142`, `20261104-064005`, `20261104-080238`
`-bench-meta`; IAM `20261103-234915`, `20261104-001606`, `20261104-063210` `-iam-meta` (Muse Spark `priced_usd` 0.1209,
0.1255, 0.1266); code runs `20261103-230340`, `20261103-234658`, `20261104-002236`, `20261104-060119`,
`20261104-062938` `-code-meta` ($0.48 = `20261103-234658-code-meta`, `priced_usd` 0.479).

## Final video script (3:00, English)

Aligned with [DEMO.md](DEMO.md) (same scenes, reordered to open on the most visual moment). Recording setup and
fallbacks are in DEMO.md. On-screen captions in *italics*. Paced at about 140–150 spoken words per minute (≈ 400
words); the last seconds are a silent end card.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:12 | Close-up of an evidence screenshot: SAM 3.1 outlines appear on the failing rows, then the e-mails and IPs are blacked out | "This is audit evidence. SAM 3.1 draws a red box on the row that fails the control — and every e-mail and IP is masked before anyone reads the report." |
| 0:12–0:25 | Report filling live; caption *Attest — audits that test, not read* | "Under DORA, EU banks must prove that their ICT controls work. Today that proof is screenshots pasted into spreadsheets. Attest tests the system itself — read-only — and writes the report a CISO signs." |
| 0:25–0:52 | Attest Studio: tick DORA 9(4), RTS 21 and the internal policy, pick the IAM console, *Draft the work programme*; review page with verified quotes and "document review / interview" badges; type a name, approve | "Pick the regulation, pick the system: here DORA article nine, the access-control standard and the bank's own policy. Muse Spark drafts the audit programme, and every requirement must quote the text word for word — checked by code. Each threshold says where it comes from; what cannot be tested is listed as not covered. Nothing runs until an auditor reviews it, types a name and approves." |
| 0:52–1:23 | Live report: tests running, screenshots, SAM outlines, masked data | "Each control becomes a small, read-only test script. The verdict comes from the script, never from the model. Muse Spark reads the screenshot to corroborate it; if they disagree, a human decides. Before the model sees anything, a deterministic net blacks out the personal data, and SAM 3.1 snaps the outline onto the exact row. Privacy cannot depend on a model's recall. And the scripts are kept, so next month the same tests replay." |
| 1:23–1:43 | CLI remediation: change request, owner types `y`; re-test green; shared admin account → action plan; caption *6 non-compliances · 5 fixes re-tested compliant · same result on 3 real runs* | "Fixing is not the auditor's job. Attest drafts the change; the system owner approves it — here, by typing yes. It is applied with a separate account, logged by the system and re-tested: green. A shared admin account is an ownership decision, so it becomes an action plan." |
| 1:43–2:08 | Studio: RTS 16 + secure-development policy, target = code repository; findings with outlined lines and masked secrets; caption *7/7 planted flaws on 4 of 5 runs · e.g. run 20261103-234658-code-meta* | "Same agent, another target: a payment microservice. Hard-coded secrets, TLS checks off, MD5 passwords, a production export in the test data — each finding points at the exact lines, secrets masked. Seven of seven planted flaws on four of our five runs; on the other, one screenshot didn't back the script, so Attest asked a human instead of guessing." |
| 2:08–2:26 | Evaluation scorecard; caption *56/56 on 5 of 5 runs · 0 false finding · 0 missed · injection flagged* | "We don't train the model, we measure the agent: 56 checks on eight fictitious banks with known answers, all correct on five separate runs, and the injection flagged every time. Our own small test set — a start, not a proof." |
| 2:26–2:33 | `attest verify` failing on an edited screenshot | "Every screenshot, script and report is hash-chained: change one pixel and verification fails." |
| 2:33–2:53 | README table of Meta models, `ATTEST_BACKEND=local`, report annex C cost; caption *$0.12–0.13 of Muse Spark calls per IAM audit · 3 real runs* | "Muse Spark plans, codes and reviews; SAM 3.1 makes the evidence precise; and the agent is designed to run on open-weights Muse Glimmer inside the bank. Less than thirteen cents of model calls for the IAM audit you just saw. Attest: audits that test, not read." |
| 2:53–3:00 | End card: *Attest — audits that test, not read* · repository URL | (silence) |

Spoken numbers and their sources: 6 / 5 → each of `20261103-234915`, `20261104-001606`, `20261104-063210` `-iam-meta`
(6 failing controls out of 7, 5 re-tested compliant, 1 action plan); "less than thirteen cents" → Muse Spark
`priced_usd` 0.1209 / 0.1255 / 0.1266 on those three runs (SAM 3.1 has no public price and is excluded) — check annex C
of the run you record before keeping the sentence; 7/7 on 4 of 5 → the five `-code-meta` runs above (the work
programme, re-planned on each run, counted 7, 7, 7, 10 and 9 controls); 56/56, 0 FP, 0 FN, injection flagged, on each
of the five `-bench-meta` runs above. Do not say "closed" for the fixes: they ran under demo pre-approvals, so they are
"re-tested compliant", closure pending the owner's approval. Do not say evidence is masked "before it leaves the
system": Muse Spark only sees a pre-masked copy, but SAM 3.1 still receives the raw screenshot.

## Bonus prizes targeted

- **Agentic** — the strongest fit. Attest plans (work programme), writes and runs its own tools (sandboxed read-only
  test scripts), reviews multimodal evidence, proposes changes, waits for a human owner's approval, applies them and
  verifies the result by re-testing. Guardrails are part of the agent: static and runtime sandbox, segregation of
  duties, deterministic verdicts, injection detection.
- **Open Weights** — only as *designed for*: Attest has a local backend for Muse Glimmer (`ATTEST_BACKEND=local`,
  llama.cpp / vLLM / SGLang) because DORA third-party risk makes on-premise models the realistic target for banks.
  It has **not yet been benchmarked on real hardware**; say so in the submission if this prize is entered.

- **Creative** — segmentation used as an audit instrument: SAM 3.1 snaps the model's boxes onto the exact rows that
  prove a finding and masks personal data; masking is measured against the page DOM (256/256 on every benchmark run:
  `20261103-232326`, `20261103-235819`, `20261104-020142`, `20261104-064005`, `20261104-080238` `-bench-meta`).

## Before submitting (for the author)

- **Choose a LICENSE** for the repository and add it yourself (none is included on purpose).
- Check the regulation excerpts in `exigences/library/` on EUR-Lex (in particular RTS 2024/1774 article 21(1)(e)(ii),
  now cited for dedicated administrator access).
- README images now come from the English PDF of run `20261104-063210-iam-meta`; refresh them if a later run is shown.
- Open Weights: confirm the Muse Glimmer licence (Apache 2.0 or not) before writing it anywhere.
