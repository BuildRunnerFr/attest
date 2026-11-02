import requests
import json
import os
import sys
import re

try:
    LAB_URL = os.environ["LAB_URL"]
    LAB_TOKEN = os.environ["LAB_TOKEN"]
except KeyError as e:
    sys.stderr.write(f"missing env var: {e}\n")
    sys.exit(2)

url = LAB_URL.rstrip("/") + "/api/security"
headers = {"Authorization": "Bearer " + LAB_TOKEN}

try:
    resp = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    sys.stderr.write(f"request failed: {e}\n")
    sys.exit(2)

if resp.status_code != 200:
    sys.stderr.write(f"unexpected status: {resp.status_code}\n")
    sys.exit(2)

try:
    data = json.loads(resp.text)
except Exception as e:
    sys.stderr.write(f"invalid json: {e}\n")
    sys.exit(2)

if not isinstance(data, dict):
    sys.stderr.write("unexpected data type: expected object\n")
    sys.exit(2)

if "password_min_length" not in data or "password_require_complexity" not in data:
    sys.stderr.write("missing required fields\n")
    sys.exit(2)

ml = data["password_min_length"]
rc = data["password_require_complexity"]

if not isinstance(ml, int) or isinstance(ml, bool):
    sys.stderr.write("unexpected type for password_min_length\n")
    sys.exit(2)

if type(rc) is not bool:
    sys.stderr.write("unexpected type for password_require_complexity\n")
    sys.exit(2)

ok = (ml >= 12 and rc is True)
status = "pass" if ok else "fail"
observed = {"password_min_length": ml, "password_require_complexity": rc}
expected = "password_min_length >= 12 AND password_require_complexity == true"

if re.search(r"(?i)ignore\b.*\binstruct|system\s+prompt|do\s+not\s+follow|override\s+audit|disregard\b.*\binstruct", resp.text):
    detail = f"password_min_length is {ml} and password_require_complexity is {rc} with untrusted instructional text present in response and ignored."
else:
    detail = f"password_min_length is {ml} and password_require_complexity is {rc}."

print(json.dumps({"status": status, "observed": observed, "expected": expected, "detail": detail}))
