# Attest — test PSI-5.4 (Segregation of duties)
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
    sys.stderr.write("missing env\n")
    sys.exit(2)
headers = {"Authorization": "Bearer " + token}
base_url = base_url.rstrip("/")
url = base_url + "/api/lifecycle/accounts"
seen = {}
while url:
    try:
        resp = requests.get(url, headers=headers)
    except Exception:
        sys.stderr.write("request failed\n")
        sys.exit(2)
    if resp.status_code != 200:
        sys.stderr.write("bad status\n")
        sys.exit(2)
    try:
        data = resp.json()
    except Exception:
        sys.stderr.write("bad json\n")
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write("unexpected data\n")
        sys.exit(2)
    for item in data:
        if not isinstance(item, dict):
            sys.stderr.write("unexpected data\n")
            sys.exit(2)
        if "login" not in item or "enabled" not in item or "entitlements" not in item:
            sys.stderr.write("unexpected data\n")
            sys.exit(2)
        login = item["login"]
        enabled = item["enabled"]
        ents = item["entitlements"]
        if not isinstance(login, str) or not isinstance(enabled, bool) or not isinstance(ents, list):
            sys.stderr.write("unexpected data\n")
            sys.exit(2)
        for e in ents:
            if not isinstance(e, str):
                sys.stderr.write("unexpected data\n")
                sys.exit(2)
        if login not in seen:
            seen[login] = item
    try:
        links = resp.links
    except Exception:
        sys.stderr.write("bad links\n")
        sys.exit(2)
    if "next" in links:
        nxt = links["next"]
        if "url" in nxt:
            raw_next = nxt["url"]
            if not isinstance(raw_next, str):
                sys.stderr.write("bad next url\n")
                sys.exit(2)
            if raw_next.startswith("http://") or raw_next.startswith("https://"):
                url = raw_next
            else:
                if raw_next.startswith("/"):
                    url = base_url + raw_next
                else:
                    url = base_url + "/" + raw_next
        else:
            url = None
    else:
        url = None
try:
    ev_resp = requests.get(base_url + "/lifecycle/accounts", headers=headers)
except Exception:
    sys.stderr.write("evidence request failed\n")
    sys.exit(2)
if ev_resp.status_code != 200:
    sys.stderr.write("evidence bad status\n")
    sys.exit(2)
off = []
enabled_count = 0
for login in seen:
    item = seen[login]
    if item["enabled"] is True:
        enabled_count = enabled_count + 1
        ents = item["entitlements"]
        has_p = "paiements.saisie" in ents and "paiements.validation" in ents
        has_c = "credit.instruction" in ents and "credit.decision" in ents
        if has_p or has_c:
            off.append(login)
off = sorted(off)
total = len(seen)
if off:
    status = "fail"
else:
    status = "pass"
expected = "entitlements does not contain paiements.saisie + paiements.validation nor credit.instruction + credit.decision where enabled=true"
detail = "Checked " + str(enabled_count) + " enabled accounts among " + str(total) + " total accounts; " + str(len(off)) + " enabled accounts hold both entitlements of an incompatible pair."
print(json.dumps({"status": status, "observed": off, "expected": expected, "detail": detail, "evidence_page": "/lifecycle/accounts"}))
