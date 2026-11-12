# Attest — test PSI-4.2 (MFA enforced for users of critical system)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re

try:
    base_url = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except KeyError:
    print("missing LAB_URL or LAB_TOKEN", file=sys.stderr)
    sys.exit(2)

if not base_url or not token:
    print("empty LAB_URL or LAB_TOKEN", file=sys.stderr)
    sys.exit(2)

base_url = base_url.rstrip("/")
headers = {"Authorization": "Bearer " + token}

users_by_id = {}
url = base_url + "/api/kc/users"
visited = set()

while url:
    if url in visited:
        break
    visited.add(url)
    try:
        resp = requests.get(url, headers=headers)
    except Exception:
        print("request failed for users list", file=sys.stderr)
        sys.exit(2)
    if resp.status_code != 200:
        print("users list status not 200", file=sys.stderr)
        sys.exit(2)
    try:
        data = resp.json()
    except Exception:
        print("users list invalid json", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, list):
        print("users list not a list", file=sys.stderr)
        sys.exit(2)
    for item in data:
        if not isinstance(item, dict):
            print("user entry not an object", file=sys.stderr)
            sys.exit(2)
        if "id" not in item or "username" not in item or "totp" not in item:
            print("user entry missing field", file=sys.stderr)
            sys.exit(2)
        uid = item["id"]
        uname = item["username"]
        totp = item["totp"]
        if not isinstance(uid, str) or not isinstance(uname, str) or not isinstance(totp, bool):
            print("user entry invalid field type", file=sys.stderr)
            sys.exit(2)
        if uid not in users_by_id:
            users_by_id[uid] = item
    nxt = None
    try:
        links = resp.links
    except Exception:
        links = {}
    if isinstance(links, dict) and "next" in links:
        nxt_info = links["next"]
        if isinstance(nxt_info, dict) and "url" in nxt_info:
            nxt = nxt_info["url"]
    if nxt:
        if not isinstance(nxt, str):
            print("invalid next link", file=sys.stderr)
            sys.exit(2)
        if nxt.startswith("http"):
            url = nxt
        else:
            if nxt.startswith("/"):
                url = base_url + nxt
            else:
                url = base_url + "/" + nxt
    else:
        url = None

try:
    ev_resp = requests.get(base_url + "/kc/users", headers=headers)
except Exception:
    print("request failed for evidence page", file=sys.stderr)
    sys.exit(2)
if ev_resp.status_code != 200:
    print("evidence page status not 200", file=sys.stderr)
    sys.exit(2)

total = len(users_by_id)
offenders = sorted([v["username"] for v in users_by_id.values() if v["totp"] is not True])
expected = "totp=true for every object from GET /api/kc/users"

if offenders:
    result = {"status": "fail", "observed": offenders, "expected": expected, "detail": str(len(offenders)) + " of " + str(total) + " users have totp=false.", "evidence_page": "/kc/users"}
else:
    result = {"status": "pass", "observed": [], "expected": expected, "detail": "All " + str(total) + " users have totp=true.", "evidence_page": "/kc/users"}

print(json.dumps(result))
