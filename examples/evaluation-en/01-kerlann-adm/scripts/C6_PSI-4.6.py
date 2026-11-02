import os
import sys
import json
import requests

try:
    base_url = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except KeyError as e:
    print(f"missing environment variable: {e}", file=sys.stderr)
    sys.exit(2)

url = base_url.rstrip("/") + "/api/security"
headers = {"Authorization": "Bearer " + token}

try:
    r = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    print(f"request failed: {e}", file=sys.stderr)
    sys.exit(2)

if r.status_code != 200:
    print(f"unexpected status code: {r.status_code}", file=sys.stderr)
    sys.exit(2)

try:
    data = r.json()
except Exception as e:
    print(f"invalid JSON: {e}", file=sys.stderr)
    sys.exit(2)

if not isinstance(data, dict) or "admin_audit_log" not in data:
    print("missing field: admin_audit_log", file=sys.stderr)
    sys.exit(2)

val = data["admin_audit_log"]
if type(val) is not bool:
    print(f"unexpected type for admin_audit_log: {type(val).__name__}", file=sys.stderr)
    sys.exit(2)

if val is True:
    print(json.dumps({"status": "pass", "observed": val, "expected": True, "detail": "admin_audit_log is true."}))
else:
    print(json.dumps({"status": "fail", "observed": val, "expected": True, "detail": "admin_audit_log is false."}))
