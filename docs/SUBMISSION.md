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
> Measured on real runs: 56/56 checks correct on 8 fictitious banks, 0 false finding, 0 missed, prompt injection
> flagged ($0.53); an IAM audit with 6 non-compliances, 5 fixes re-tested compliant ($0.12); 7/7 planted flaws found in
> a code repository ($0.48). The test set is small and self-built: encouraging, not proof of general accuracy.

Sources: `20261103-232326-bench-meta`, `20261103-234915-iam-meta`, `20261103-234658-code-meta`.

## Final video script (3:00, English)

Aligned with [DEMO.md](DEMO.md) (same scenes, reordered to open on the most visual moment). Recording setup and
fallbacks are in DEMO.md. On-screen captions in *italics*.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:12 | Close-up of an evidence screenshot: SAM 3.1 outlines appear on the failing rows, then the e-mails and IPs are blacked out | "This is audit evidence. A red box on the row that fails the control — and every e-mail and IP masked before it leaves the system. That is SAM 3.1, inside a compliance auditor." |
| 0:12–0:25 | Report filling live; caption *Attest — audits that test, not read* | "Banks prove DORA compliance with screenshots and spreadsheets. Attest tests the system itself, read-only, and writes the report a CISO signs." |
| 0:25–0:55 | Attest Studio: tick DORA 9(4), RTS 21 and the internal policy, pick the IAM console, *Draft the work programme*; review page with verified quotes and "document review / interview" badges; type a name, approve | "Pick the regulation, pick the system. Muse Spark drafts the audit programme, and every requirement must quote the text word for word — checked by code. Thresholds say where they come from; what cannot be tested is listed as not covered. Nothing runs until an auditor approves." |
| 0:55–1:30 | Live report: tests running, screenshots, SAM outlines, masked data | "Each control becomes a read-only test script. The verdict comes from the script, never from the model. Muse Spark reads the screenshot to corroborate it; SAM 3.1 makes the evidence precise and private, with a deterministic safety net — privacy cannot depend on a model's recall." |
| 1:30–1:55 | CLI remediation: change request, owner types `y`; re-test green; shared admin account → action plan; caption *6 non-compliances · 5 fixes re-tested compliant · run 20261103-234915-iam-meta* | "Fixing is not the auditor's job. Attest drafts the change, the system owner approves it, it is applied with a separate account, logged and re-tested. A shared admin account is an ownership decision, so it becomes an action plan." |
| 1:55–2:20 | Studio: RTS 16 + secure-development policy, target = code repository; findings with outlined lines and masked secrets; caption *7/7 planted flaws · run 20261103-234658-code-meta* | "Same agent, another target: a payment microservice. Hard-coded secrets, TLS checks off, MD5 passwords, a production export in the test data — all seven planted flaws found, each pointing at the exact lines, secrets masked." |
| 2:20–2:40 | Evaluation scorecard; caption *56/56 · 0 false finding · 0 missed · injection flagged · run 20261103-232326-bench-meta*; then `attest verify` failing on an edited screenshot | "We don't train the model, we measure the agent: 56 checks on eight fictitious banks with known answers, all correct, and the prompt-injection attempt flagged. It's our own small test set — a start, not a proof. And every piece of evidence is hash-chained: edit one pixel and verification fails." |
| 2:40–3:00 | README table of Meta models, `ATTEST_BACKEND=local`, report annex C cost; caption *$0.12 of Muse Spark calls for the IAM audit* | "Muse Spark plans, codes and reviews the evidence; SAM 3.1 makes it precise and private; and the agent is designed to run on open-weights Muse Glimmer inside the bank. Twelve cents of model calls for a full audit. Attest: audits that test, not read." |

Spoken numbers and their sources: 6 / 5 / $0.12 → `20261103-234915-iam-meta` (Muse Spark `priced_usd` 0.1209; SAM 3.1
has no public price and is excluded); 7/7 → `20261103-234658-code-meta`; 56/56, 0 FP, 0 FN, injection 1/1 →
`20261103-232326-bench-meta`. Do not say "closed" for the fixes: they ran under demo pre-approvals, so they are
"re-tested compliant", closure pending the owner's approval.

## Bonus prizes targeted

- **Agentic** — the strongest fit. Attest plans (work programme), writes and runs its own tools (sandboxed read-only
  test scripts), reviews multimodal evidence, proposes changes, waits for a human owner's approval, applies them and
  verifies the result by re-testing. Guardrails are part of the agent: static and runtime sandbox, segregation of
  duties, deterministic verdicts, injection detection.
- **Open Weights** — only as *designed for*: Attest has a local backend for Muse Glimmer (`ATTEST_BACKEND=local`,
  llama.cpp / vLLM / SGLang) because DORA third-party risk makes on-premise models the realistic target for banks.
  It has **not yet been benchmarked on real hardware**; say so in the submission if this prize is entered.

## Before submitting (for the author)

- **Choose a LICENSE** for the repository and add it yourself (none is included on purpose).
- Check the regulation excerpts in `exigences/library/` on EUR-Lex (in particular RTS 2024/1774 article 21(1)(e)(ii),
  now cited for dedicated administrator access).
- Refresh the README images from run `20261103-234915-iam-meta` (English) if not done yet.
