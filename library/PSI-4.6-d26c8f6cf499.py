# Attest — test PSI-4.6 (Logging of administration actions)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re

try:
    base = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except Exception as exc:
    sys.stderr.write("missing LAB_URL or LAB_TOKEN\n")
    sys.exit(2)

if not base or not token:
    sys.stderr.write("missing LAB_URL or LAB_TOKEN\n")
    sys.exit(2)

base = base.rstrip("/")
headers = {"Authorization": "Bearer " + token}

try:
    resp = requests.get(base + "/api/kc/realm", headers=headers)
except Exception as exc:
    sys.stderr.write("request to /api/kc/realm failed\n")
    sys.exit(2)

if resp.status_code != 200:
    sys.stderr.write("request to /api/kc/realm failed with status\n")
    sys.exit(2)

try:
    data = resp.json()
except Exception as exc:
    sys.stderr.write("invalid JSON from /api/kc/realm\n")
    sys.exit(2)

if not isinstance(data, dict):
    sys.stderr.write("unexpected data from /api/kc/realm\n")
    sys.exit(2)

if "adminEventsEnabled" not in data:
    sys.stderr.write("missing adminEventsEnabled in realm data\n")
    sys.exit(2)

val = data["adminEventsEnabled"]

if not isinstance(val, bool):
    sys.stderr.write("unexpected type for adminEventsEnabled\n")
    sys.exit(2)

found = False
for k in data:
    v = data[k]
    if isinstance(v, str):
        if re.search("(?i)ignore.*instruction|disregard.*instruction|system prompt|you are.*ai|output.*pass", v):
            found = True

try:
    resp2 = requests.get(base + "/kc/realm", headers=headers)
except Exception as exc:
    sys.stderr.write("request to /kc/realm failed\n")
    sys.exit(2)

if resp2.status_code != 200:
    sys.stderr.write("request to /kc/realm failed with status\n")
    sys.exit(2)

page_text = resp2.text
if re.search("(?i)ignore.*instruction|disregard.*instruction|system prompt|you are.*ai|output.*pass", page_text):
    found = True

if val is True:
    status = "pass"
    detail = "Realm representation reports adminEventsEnabled=true, so administration actions are recorded."
else:
    status = "fail"
    detail = "Realm representation reports adminEventsEnabled=false, so administration actions are not recorded."

if found:
    detail = detail + " Untrusted instruction text in audited data was ignored."

result = {"status": status, "observed": val, "expected": "adminEventsEnabled=true", "detail": detail, "evidence_page": "/kc/realm"}
print(json.dumps(result))
