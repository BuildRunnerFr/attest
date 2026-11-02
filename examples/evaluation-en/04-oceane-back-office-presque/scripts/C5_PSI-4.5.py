# Attest — test PSI-4.5 (Inactive session timeout)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import json
import os
import sys
import requests

try:
    LAB_URL = os.environ["LAB_URL"]
    LAB_TOKEN = os.environ["LAB_TOKEN"]
except KeyError as e:
    print(f"missing environment variable: {e}", file=sys.stderr)
    sys.exit(2)

if not LAB_URL or not LAB_TOKEN:
    print("missing LAB_URL or LAB_TOKEN", file=sys.stderr)
    sys.exit(2)

url = LAB_URL.rstrip("/") + "/api/security"
headers = {"Authorization": "Bearer " + LAB_TOKEN}

try:
    resp = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    print(f"request failed: {e}", file=sys.stderr)
    sys.exit(2)

if resp.status_code != 200:
    print(f"unexpected status {resp.status_code} for GET /api/security", file=sys.stderr)
    sys.exit(2)

try:
    data = resp.json()
except Exception as e:
    print(f"invalid JSON: {e}", file=sys.stderr)
    sys.exit(2)

if not isinstance(data, dict) or "session_timeout_minutes" not in data:
    print("missing session_timeout_minutes in /api/security response", file=sys.stderr)
    sys.exit(2)

val = data["session_timeout_minutes"]

if type(val) is not int:
    print(f"unexpected type for session_timeout_minutes: {type(val).__name__}", file=sys.stderr)
    sys.exit(2)

expected = "session_timeout_minutes >= 1 AND session_timeout_minutes <= 15"
if 1 <= val <= 15:
    status = "pass"
    detail = f"Observed session_timeout_minutes is {val}, within the required 1 to 15 inclusive."
else:
    status = "fail"
    detail = f"Observed session_timeout_minutes is {val}, outside the required 1 to 15 inclusive."

print(json.dumps({"status": status, "observed": val, "expected": expected, "detail": detail}))
