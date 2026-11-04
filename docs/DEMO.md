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

The final 3-minute script, with timings, captions and the source of every spoken number, is in
[SUBMISSION.md](SUBMISSION.md#final-video-script-300-english). This file covers recording setup and fallbacks only,
so that there is a single script to record from.

## Fallbacks

- API slow or rate-limited: `ATTEST_WORKERS=3`, or show the warm-up run's report and narrate.
- Tamper demo: `cp runs/demo/evidence/C1_before.png /tmp/b.png`, paint on it, run `verify`, restore the copy.
- Injection demo: restart the lab with `LAB_INJECTION=1`, run without `--remediate`, show the banner in the report.
