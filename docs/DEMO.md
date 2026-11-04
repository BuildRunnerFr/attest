# 3-minute demo script

## Before recording

```bash
# terminal 1: audited console + Studio (http://127.0.0.1:8000)
bash scripts/start.sh
# terminal 2: environment for every command below
source .venv/bin/activate; set -a; source .env; set +a
export ATTEST_LANG=en ATTEST_AUDITOR="<your name>" ATTEST_APPROVER="IAM owner"
```

Three warm-ups, all before the recording session:

1. **IAM (CLI)** — caches the work programme and the test scripts, and gives a finished report to fall back on:
   ```bash
   python -m attest run --reset-lab --remediate --approve-all --out runs/warmup
   ```
2. **Code repository (Studio)** — in the browser: tick RTS 16 and the secure-development policy (PDS-2), pick the
   code repository target, *Draft the work programme*, approve, run the audit. The finished report lands in
   `runs/studio/<session>/audit/report.html`; note the session id, it is the fallback for the code scene. The Studio
   re-plans on each new session, so the live take may list a different number of controls (7 to 10 on our real runs).
3. **Benchmark scorecard (pre-recorded)** — a full bench is far too long to run on camera (300–417 s on the five ledger
   runs), so record the scorecard from a finished one:
   ```bash
   python -m attest bench --lang en --out runs/bench-demo      # then open runs/bench-demo/scorecard.html
   ```
   Without a key or time, show [`examples/evaluation-en/scorecard.html`](../examples/evaluation-en/scorecard.html)
   or the `scorecard.md` kept with a ledger bench run on the `real-results` branch.

The live IAM take writes to its own folder, so the warm-up stays intact as a fallback:

```bash
python -m attest run --reset-lab --remediate --out runs/demo        # owner types y on camera
```

Arrange the screen: terminal on the left, the browser on the right.
Record the live run once at normal speed; speed up the waiting parts in editing.

## Script

The final 3-minute script, with timings, captions and the source of every spoken number, is in
[SUBMISSION.md](SUBMISSION.md#final-video-script-300-english). This file covers recording setup and fallbacks only,
so that there is a single script to record from.

## Fallbacks

- API slow or rate-limited: `ATTEST_WORKERS=3`, or show `runs/warmup/report.html` (IAM) or the Studio warm-up report
  (code) and narrate.
- Tamper demo: `cp runs/demo/evidence/C1_before.png /tmp/b.png`, paint on `runs/demo/evidence/C1_before.png`, run
  `python -m attest verify runs/demo`, then restore the copy (if the live take failed, do the same on `runs/warmup`).
- Bench scene: never run the bench live; use `runs/bench-demo/scorecard.html` from warm-up 3.
- Injection demo: restart the lab with `LAB_INJECTION=1`, run without `--remediate` (`--out runs/demo-injection`),
  show the banner in the report.
