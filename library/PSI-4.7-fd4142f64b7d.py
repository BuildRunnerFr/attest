# Attest — test PSI-4.7 (No generic or shared administrator accounts)
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

base = os.environ["LAB_URL"]
token = os.environ["LAB_TOKEN"]

if not isinstance(base, str) or base == "":
    sys.stderr.write("bad base url\n")
    sys.exit(2)
if not isinstance(token, str) or token == "":
    sys.stderr.write("bad token\n")
    sys.exit(2)

headers = {"Authorization": "Bearer " + token}
base_url = base.rstrip("/")
api_start = base_url + "/api/kc/roles/admin/users"

users = []
seen = set()
url = api_start
while True:
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        sys.stderr.write("admin list request failed\n")
        sys.exit(2)
    try:
        data = resp.json()
    except ValueError:
        sys.stderr.write("admin list bad json\n")
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write("admin list not a list\n")
        sys.exit(2)
    for entry in data:
        if not isinstance(entry, dict):
            sys.stderr.write("admin entry not an object\n")
            sys.exit(2)
        if "username" not in entry or "email" not in entry:
            sys.stderr.write("admin entry missing fields\n")
            sys.exit(2)
        username = entry["username"]
        email = entry["email"]
        if not isinstance(username, str):
            sys.stderr.write("bad username type\n")
            sys.exit(2)
        if email is not None and not isinstance(email, str):
            sys.stderr.write("bad email type\n")
            sys.exit(2)
        if "id" in entry and isinstance(entry["id"], str):
            uid = entry["id"]
        else:
            uid = username
        if uid in seen:
            continue
        seen.add(uid)
        users.append(entry)
    if "next" in resp.links and "url" in resp.links["next"]:
        nxt = resp.links["next"]["url"]
        if not isinstance(nxt, str) or nxt == "":
            sys.stderr.write("bad next link\n")
            sys.exit(2)
        if nxt.startswith("http://") or nxt.startswith("https://"):
            url = nxt
        else:
            url = base_url + "/" + nxt.lstrip("/")
    else:
        break

ev_resp = requests.get(base_url + "/kc/roles/admin/users", headers=headers)
if ev_resp.status_code != 200:
    sys.stderr.write("evidence page request failed\n")
    sys.exit(2)

generic_words = set(["admin", "administrator", "administrateur", "root", "ops", "support", "team", "service", "services", "shared", "partage", "generic", "generique", "system", "test", "info", "contact", "helpdesk", "operator", "operators", "devops", "secops", "superuser", "supervisor"])
pattern = r'^[A-Za-z]\.[A-Za-z]+(?:-[A-Za-z]+)*$'

offending = []
for u in users:
    username = u["username"]
    email = u["email"]
    ok_name = re.match(pattern, username) is not None
    uname_tokens = re.findall(r'[A-Za-z]+', username.lower())
    uname_generic = False
    for t in uname_tokens:
        if t in generic_words:
            uname_generic = True
            break
    if email is None or email == "" or "@" not in email:
        ok_mail = False
    else:
        parts = email.split("@")
        if len(parts) != 2 or parts[0] == "" or parts[1] == "":
            ok_mail = False
        else:
            local_tokens = re.findall(r'[A-Za-z]+', parts[0].lower())
            has_generic = False
            for t in local_tokens:
                if t in generic_words:
                    has_generic = True
                    break
            ok_mail = not has_generic
    if (not ok_name) or uname_generic or (not ok_mail):
        offending.append(username)

expected = "username matches initiale.nom pattern and email is personal (not ops, admin, root or ops-partage@, admin@) for every object from GET /api/kc/roles/admin/users"
evidence = "/kc/roles/admin/users"

if len(offending) == 0:
    observed = []
    for u in users:
        observed.append(u["username"])
    detail = "Checked " + str(len(users)) + " admin users, all have nominative username and personal email."
    print(json.dumps({"status": "pass", "observed": observed, "expected": expected, "detail": detail, "evidence_page": evidence}))
else:
    detail = "Checked " + str(len(users)) + " admin users, found " + str(len(offending)) + " with generic or non-nominative username or email."
    print(json.dumps({"status": "fail", "observed": offending, "expected": expected, "detail": detail, "evidence_page": evidence}))
