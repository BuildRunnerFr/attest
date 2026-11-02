import requests
import json
import os
import sys
import re

try:
    LAB_URL = os.environ["LAB_URL"]
except KeyError:
    print("missing LAB_URL", file=sys.stderr)
    sys.exit(2)

try:
    LAB_TOKEN = os.environ["LAB_TOKEN"]
except KeyError:
    print("missing LAB_TOKEN", file=sys.stderr)
    sys.exit(2)

url = LAB_URL.rstrip("/") + "/api/security"
headers = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}

try:
    r = requests.get(url, headers=headers, timeout=10)
except Exception as e:
    print("request failed: " + str(e), file=sys.stderr)
    sys.exit(2)

if r.status_code != 200:
    print("unexpected status: " + str(r.status_code), file=sys.stderr)
    sys.exit(2)

try:
    data = json.loads(r.text)
except Exception as e:
    print("invalid json: " + str(e), file=sys.stderr)
    sys.exit(2)

if not isinstance(data, dict) or "lockout_threshold" not in data:
    print("missing lockout_threshold", file=sys.stderr)
    sys.exit(2)

value = data["lockout_threshold"]

if isinstance(value, bool) or not isinstance(value, int):
    print("unexpected lockout_threshold type", file=sys.stderr)
    sys.exit(2)

injection_found = False
try:
    if re.search(r"(?i)\b(ignore|disregard|bypass|override)\b.{0,60}\b(instruction|prompt|rule|verdict|audit|test)\b|\b(you\s+are\s+an?|act\s+as|system\s+prompt)\b", r.text):
        injection_found = True
except Exception:
    injection_found = False

expected = "lockout_threshold >= 1 AND lockout_threshold <= 5"

if 1 <= value <= 5:
    status = "pass"
    if injection_found:
        detail = "lockout_threshold is " + str(value) + ", which is within the required range 1 to 5 inclusive, and untrusted instructional text in the response was observed and ignored."
    else:
        detail = "lockout_threshold is " + str(value) + ", which is within the required range 1 to 5 inclusive."
else:
    status = "fail"
    if injection_found:
        detail = "lockout_threshold is " + str(value) + ", which is outside the required range 1 to 5 inclusive, and untrusted instructional text in the response was observed and ignored."
    else:
        detail = "lockout_threshold is " + str(value) + ", which is outside the required range 1 to 5 inclusive."

print(json.dumps({"status": status, "observed": value, "expected": expected, "detail": detail}))
