# Attest — test PSI-4.1 (MFA enforced for privileged administrator accounts)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re

try:
    base_url = os.environ["LAB_URL"]
except Exception:
    sys.stderr.write("missing LAB_URL\n")
    sys.exit(2)

try:
    token = os.environ["LAB_TOKEN"]
except Exception:
    sys.stderr.write("missing LAB_TOKEN\n")
    sys.exit(2)

if not isinstance(base_url, str) or base_url == "":
    sys.stderr.write("bad LAB_URL\n")
    sys.exit(2)

if not isinstance(token, str) or token == "":
    sys.stderr.write("bad LAB_TOKEN\n")
    sys.exit(2)

headers = {"Authorization": "Bearer " + token}
base = base_url.rstrip("/")
url = base + "/api/kc/roles/admin/users"
seen = {}

while True:
    try:
        resp = requests.get(url, headers=headers)
    except Exception as e:
        sys.stderr.write("request failed: " + str(e) + "\n")
        sys.exit(2)
    if resp.status_code != 200:
        sys.stderr.write("bad status for list request\n")
        sys.exit(2)
    try:
        data = resp.json()
    except Exception as e:
        sys.stderr.write("bad json: " + str(e) + "\n")
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write("unexpected data not list\n")
        sys.exit(2)
    for item in data:
        if not isinstance(item, dict):
            sys.stderr.write("unexpected item not object\n")
            sys.exit(2)
        if "id" not in item or "username" not in item or "totp" not in item:
            sys.stderr.write("missing fields in admin user object\n")
            sys.exit(2)
        totp_val = item["totp"]
        if not isinstance(totp_val, bool):
            sys.stderr.write("unexpected totp type\n")
            sys.exit(2)
        uid = item["id"]
        if uid not in seen:
            seen[uid] = item
    links = resp.links
    if not isinstance(links, dict):
        sys.stderr.write("bad links\n")
        sys.exit(2)
    if "next" not in links:
        break
    nxt = links["next"]
    if not isinstance(nxt, dict) or "url" not in nxt:
        break
    raw_next = nxt["url"]
    if not isinstance(raw_next, str) or raw_next == "":
        break
    if raw_next.startswith("http://") or raw_next.startswith("https://"):
        url = raw_next
    else:
        url = base + "/" + raw_next.lstrip("/")

ev_path = "/kc/roles/admin/users"
ev_url = base + ev_path
try:
    ev_resp = requests.get(ev_url, headers=headers)
except Exception as e:
    sys.stderr.write("evidence request failed: " + str(e) + "\n")
    sys.exit(2)
if ev_resp.status_code != 200:
    sys.stderr.write("bad status for evidence page\n")
    sys.exit(2)

total = len(seen)
bad = []
for uid in seen:
    obj = seen[uid]
    if not obj["totp"]:
        bad.append(obj["username"])
bad.sort()

expected = "totp=true for every object from GET /api/kc/roles/admin/users"
if len(bad) == 0:
    status = "pass"
    observed = []
    detail = "Checked " + str(total) + " admin accounts, all have totp=true."
else:
    status = "fail"
    observed = bad
    detail = "Checked " + str(total) + " admin accounts, " + str(len(bad)) + " lack MFA."

print(json.dumps({"status": status, "observed": observed, "expected": expected, "detail": detail, "evidence_page": ev_path}))
