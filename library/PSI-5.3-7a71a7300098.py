# Attest — test PSI-5.3 (Dormant person accounts)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re

try:
    base_raw = os.environ["LAB_URL"]
    token_raw = os.environ["LAB_TOKEN"]
except Exception as e:
    sys.stderr.write("missing env: " + str(e) + "\n")
    sys.exit(2)

base = base_raw.rstrip("/")
headers = {"Authorization": "Bearer " + token_raw}

def to_ord(ds):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", ds)
    if not m:
        sys.stderr.write("bad date: " + str(ds) + "\n")
        sys.exit(2)
    y = int(m.group(1))
    mo = int(m.group(2))
    d = int(m.group(3))
    if mo < 1 or mo > 12:
        sys.stderr.write("bad month: " + str(ds) + "\n")
        sys.exit(2)
    leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    ml = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if d < 1 or d > ml[mo - 1]:
        sys.stderr.write("bad day: " + str(ds) + "\n")
        sys.exit(2)
    n = (y - 1) * 365 + (y - 1) // 4 - (y - 1) // 100 + (y - 1) // 400
    s = 0
    i = 0
    while i < mo - 1:
        s = s + ml[i]
        i = i + 1
    n = n + s + d
    return n

try:
    mr = requests.get(base + "/api/lifecycle/meta", headers=headers)
except Exception as e:
    sys.stderr.write("meta request failed: " + str(e) + "\n")
    sys.exit(2)
if mr.status_code != 200:
    sys.stderr.write("meta bad status: " + str(mr.status_code) + "\n")
    sys.exit(2)
try:
    mdata = mr.json()
except Exception as e:
    sys.stderr.write("meta bad json: " + str(e) + "\n")
    sys.exit(2)
if not isinstance(mdata, dict):
    sys.stderr.write("meta expected dict\n")
    sys.exit(2)
if "as_of" not in mdata:
    sys.stderr.write("meta missing as_of\n")
    sys.exit(2)
as_of_str = mdata["as_of"]
if not isinstance(as_of_str, str):
    sys.stderr.write("meta as_of not string\n")
    sys.exit(2)
if not re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_str):
    sys.stderr.write("meta as_of bad format\n")
    sys.exit(2)
as_of_ord = to_ord(as_of_str)

acc_by_login = {}
url = base + "/api/lifecycle/accounts"
while url is not None:
    try:
        rr = requests.get(url, headers=headers)
    except Exception as e:
        sys.stderr.write("accounts request failed: " + str(e) + "\n")
        sys.exit(2)
    if rr.status_code != 200:
        sys.stderr.write("accounts bad status: " + str(rr.status_code) + "\n")
        sys.exit(2)
    try:
        j = rr.json()
    except Exception as e:
        sys.stderr.write("accounts bad json: " + str(e) + "\n")
        sys.exit(2)
    if not isinstance(j, list):
        sys.stderr.write("accounts expected list\n")
        sys.exit(2)
    for it in j:
        if not isinstance(it, dict):
            sys.stderr.write("account expected dict\n")
            sys.exit(2)
        if "login" not in it or "type" not in it or "enabled" not in it or "created" not in it or "last_login" not in it:
            sys.stderr.write("account missing fields\n")
            sys.exit(2)
        lg = it["login"]
        if not isinstance(lg, str):
            sys.stderr.write("account login not string\n")
            sys.exit(2)
        if lg not in acc_by_login:
            acc_by_login[lg] = it
    if "next" in rr.links:
        nu = rr.links["next"]["url"]
        if not isinstance(nu, str):
            sys.stderr.write("next url not string\n")
            sys.exit(2)
        if nu.startswith("http"):
            url = nu
        elif nu.startswith("/"):
            url = base + nu
        else:
            url = base + "/" + nu
    else:
        url = None

try:
    er = requests.get(base + "/lifecycle/accounts", headers=headers)
except Exception as e:
    sys.stderr.write("evidence request failed: " + str(e) + "\n")
    sys.exit(2)
if er.status_code != 200:
    sys.stderr.write("evidence bad status: " + str(er.status_code) + "\n")
    sys.exit(2)

total = 0
dormant = []
for acc in acc_by_login.values():
    typ = acc["type"]
    en = acc["enabled"]
    if typ not in ("person", "service"):
        sys.stderr.write("bad type: " + str(typ) + "\n")
        sys.exit(2)
    if not isinstance(en, bool):
        sys.stderr.write("bad enabled flag\n")
        sys.exit(2)
    if typ == "person" and en == True:
        total = total + 1
        ll = acc["last_login"]
        cr = acc["created"]
        if ll is not None and not isinstance(ll, str):
            sys.stderr.write("bad last_login\n")
            sys.exit(2)
        if not isinstance(cr, str):
            sys.stderr.write("bad created\n")
            sys.exit(2)
        ref = ll if ll is not None else cr
        ref_ord = to_ord(ref)
        diff = as_of_ord - ref_ord
        if diff > 90:
            dormant.append(acc["login"])

dormant_sorted = sorted(dormant)
expected = "as_of minus (last_login or created if null) <= 90 where type=person and enabled=true"
if len(dormant_sorted) == 0:
    status = "pass"
    observed = []
    detail = "Checked " + str(total) + " enabled person accounts at as_of " + as_of_str + ", none exceeded 90 days inactivity."
else:
    status = "fail"
    observed = dormant_sorted
    detail = "Checked " + str(total) + " enabled person accounts at as_of " + as_of_str + ", " + str(len(dormant_sorted)) + " exceeded 90 days inactivity."

print(json.dumps({"status": status, "observed": observed, "expected": expected, "detail": detail, "evidence_page": "/lifecycle/accounts"}))
