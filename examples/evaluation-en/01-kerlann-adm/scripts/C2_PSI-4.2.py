import requests
import json
import os
import sys
import re

try:
    base = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except KeyError as e:
    print(f"missing environment variable: {e}", file=sys.stderr)
    sys.exit(2)

url = re.sub(r"/+$", "", base) + "/api/security"
headers = {"Authorization": "Bearer " + token}

try:
    r = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    print(f"request failed: {e}", file=sys.stderr)
    sys.exit(2)

if r.status_code != 200:
    print(f"unexpected status {r.status_code} for GET /api/security", file=sys.stderr)
    sys.exit(2)

try:
    data = r.json()
except Exception as e:
    print(f"invalid json: {e}", file=sys.stderr)
    sys.exit(2)

if not isinstance(data, dict) or "mfa_users" not in data or not isinstance(data["mfa_users"], bool):
    print("missing or invalid mfa_users field", file=sys.stderr)
    sys.exit(2)

observed = data["mfa_users"]
status = "pass" if observed is True else "fail"
print(json.dumps({"status": status, "observed": observed, "expected": True, "detail": f"mfa_users is {observed}."}))
