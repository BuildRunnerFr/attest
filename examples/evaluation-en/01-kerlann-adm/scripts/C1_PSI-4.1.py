import os
import sys
import json
import re
import requests

try:
    base = os.environ["LAB_URL"]
except KeyError:
    sys.stderr.write("missing LAB_URL\n")
    sys.exit(2)
try:
    token = os.environ["LAB_TOKEN"]
except KeyError:
    sys.stderr.write("missing LAB_TOKEN\n")
    sys.exit(2)

url = base.rstrip("/") + "/api/security"
headers = {"Authorization": "Bearer " + token}

try:
    r = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    sys.stderr.write("request failed: %s\n" % e)
    sys.exit(2)

if r.status_code != 200:
    sys.stderr.write("unexpected status %s\n" % r.status_code)
    sys.exit(2)

try:
    data = r.json()
except Exception as e:
    sys.stderr.write("invalid json: %s\n" % e)
    sys.exit(2)

if not isinstance(data, dict) or "mfa_admin" not in data:
    sys.stderr.write("missing mfa_admin\n")
    sys.exit(2)

observed = data["mfa_admin"]

if type(observed) is not bool:
    sys.stderr.write("unexpected type for mfa_admin\n")
    sys.exit(2)

raw = json.dumps(data, default=str)
injected = bool(re.search(r"(?i)(ignore|disregard|bypass|override|follow).{0,40}(instruction|prompt|audit|control|system)|system\s*prompt|execute\s+.*code", raw))

status = "pass" if observed is True else "fail"
if injected:
    detail = "GET /api/security returned mfa_admin=%s, ignoring untrusted instructional text found in response." % observed
else:
    detail = "GET /api/security returned mfa_admin=%s." % observed

print(json.dumps({"status": status, "observed": observed, "expected": True, "detail": detail}))
