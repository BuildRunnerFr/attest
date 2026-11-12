# Attest — test PSI-4.4 (Account lockout after repeated login failures)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re

if "LAB_URL" not in os.environ:
    sys.stderr.write("missing LAB_URL\n")
    sys.exit(2)
if "LAB_TOKEN" not in os.environ:
    sys.stderr.write("missing LAB_TOKEN\n")
    sys.exit(2)
base_url = os.environ["LAB_URL"]
token = os.environ["LAB_TOKEN"]
base_url = base_url.rstrip("/")
headers = {"Authorization": "Bearer " + token}
r = requests.get(base_url + "/api/kc/realm", headers=headers, timeout=20)
if r.status_code != 200:
    sys.stderr.write("GET /api/kc/realm failed with status " + str(r.status_code) + "\n")
    sys.exit(2)
try:
    data = r.json()
except Exception:
    sys.stderr.write("invalid json for /api/kc/realm\n")
    sys.exit(2)
if type(data) is not dict:
    sys.stderr.write("unexpected data type for realm\n")
    sys.exit(2)
if "bruteForceProtected" not in data:
    sys.stderr.write("missing bruteForceProtected\n")
    sys.exit(2)
if "failureFactor" not in data:
    sys.stderr.write("missing failureFactor\n")
    sys.exit(2)
brute = data["bruteForceProtected"]
factor = data["failureFactor"]
if type(brute) is not bool:
    sys.stderr.write("unexpected type for bruteForceProtected\n")
    sys.exit(2)
if type(factor) is not int:
    sys.stderr.write("unexpected type for failureFactor\n")
    sys.exit(2)
e = requests.get(base_url + "/kc/realm", headers=headers, timeout=20)
if e.status_code != 200:
    sys.stderr.write("GET /kc/realm failed with status " + str(e.status_code) + "\n")
    sys.exit(2)
page_text = e.text
if type(page_text) is not str:
    sys.stderr.write("unexpected page type for /kc/realm\n")
    sys.exit(2)
observed = {"bruteForceProtected": brute, "failureFactor": factor}
expected = "bruteForceProtected=true and failureFactor<=5"
detail = "Checked 1 realm; bruteForceProtected is " + str(brute).lower() + " and failureFactor is " + str(factor) + "."
if brute and factor <= 5:
    result = {"status": "pass", "observed": observed, "expected": expected, "detail": detail, "evidence_page": "/kc/realm"}
else:
    result = {"status": "fail", "observed": observed, "expected": expected, "detail": detail, "evidence_page": "/kc/realm"}
print(json.dumps(result))
