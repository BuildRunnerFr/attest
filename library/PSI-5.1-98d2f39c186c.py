# Attest — test PSI-5.1 (Leavers - timely deactivation)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re
try:
    base = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except KeyError:
    sys.stderr.write("missing LAB_URL or LAB_TOKEN\n")
    sys.exit(2)
if not isinstance(base, str) or not isinstance(token, str):
    sys.stderr.write("env invalid\n")
    sys.exit(2)
headers = {"Authorization": "Bearer " + token}
clean = base.rstrip("/")
pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")
meta_resp = requests.get(clean + "/api/lifecycle/meta", headers=headers)
if meta_resp.status_code != 200:
    sys.stderr.write("meta request failed\n")
    sys.exit(2)
try:
    meta_data = meta_resp.json()
except Exception:
    sys.stderr.write("meta json failed\n")
    sys.exit(2)
if not isinstance(meta_data, dict):
    sys.stderr.write("meta format invalid\n")
    sys.exit(2)
if "as_of" not in meta_data:
    sys.stderr.write("meta as_of missing\n")
    sys.exit(2)
as_of = meta_data["as_of"]
if not isinstance(as_of, str):
    sys.stderr.write("as_of invalid\n")
    sys.exit(2)
if not pat.match(as_of):
    sys.stderr.write("as_of date invalid\n")
    sys.exit(2)
employees = {}
url = clean + "/api/hr/employees"
while True:
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        sys.stderr.write("employees request failed\n")
        sys.exit(2)
    try:
        batch = r.json()
    except Exception:
        sys.stderr.write("employees json failed\n")
        sys.exit(2)
    if not isinstance(batch, list):
        sys.stderr.write("employees format invalid\n")
        sys.exit(2)
    for entry in batch:
        if not isinstance(entry, dict):
            sys.stderr.write("employee entry invalid\n")
            sys.exit(2)
        if "employee_id" not in entry:
            sys.stderr.write("employee_id missing\n")
            sys.exit(2)
        eid = entry["employee_id"]
        if not isinstance(eid, str):
            sys.stderr.write("employee_id invalid\n")
            sys.exit(2)
        if eid not in employees:
            employees[eid] = entry
    if "next" in r.links:
        nxt = r.links["next"]["url"]
        if not isinstance(nxt, str):
            sys.stderr.write("next link invalid\n")
            sys.exit(2)
        if nxt.startswith("http"):
            url = nxt
        elif nxt.startswith("/"):
            url = clean + nxt
        else:
            url = clean + "/" + nxt
    else:
        break
accounts = {}
url2 = clean + "/api/lifecycle/accounts"
while True:
    r2 = requests.get(url2, headers=headers)
    if r2.status_code != 200:
        sys.stderr.write("accounts request failed\n")
        sys.exit(2)
    try:
        batch2 = r2.json()
    except Exception:
        sys.stderr.write("accounts json failed\n")
        sys.exit(2)
    if not isinstance(batch2, list):
        sys.stderr.write("accounts format invalid\n")
        sys.exit(2)
    for entry2 in batch2:
        if not isinstance(entry2, dict):
            sys.stderr.write("account entry invalid\n")
            sys.exit(2)
        if "login" not in entry2:
            sys.stderr.write("login missing\n")
            sys.exit(2)
        lg = entry2["login"]
        if not isinstance(lg, str):
            sys.stderr.write("login invalid\n")
            sys.exit(2)
        if lg not in accounts:
            accounts[lg] = entry2
    if "next" in r2.links:
        nxt2 = r2.links["next"]["url"]
        if not isinstance(nxt2, str):
            sys.stderr.write("next link invalid\n")
            sys.exit(2)
        if nxt2.startswith("http"):
            url2 = nxt2
        elif nxt2.startswith("/"):
            url2 = clean + nxt2
        else:
            url2 = clean + "/" + nxt2
    else:
        break
ev = requests.get(clean + "/lifecycle/reconciliation", headers=headers)
if ev.status_code != 200:
    sys.stderr.write("evidence request failed\n")
    sys.exit(2)
bad = []
enabled_person = 0
for lg, acc in accounts.items():
    if "type" not in acc or "enabled" not in acc or "employee_id" not in acc:
        sys.stderr.write("account fields missing\n")
        sys.exit(2)
    typ = acc["type"]
    en = acc["enabled"]
    if typ not in ("person", "service"):
        sys.stderr.write("account type invalid\n")
        sys.exit(2)
    if not isinstance(en, bool):
        sys.stderr.write("enabled invalid\n")
        sys.exit(2)
    if typ != "person":
        continue
    if not en:
        continue
    enabled_person = enabled_person + 1
    eid2 = acc["employee_id"]
    if eid2 is None:
        continue
    if not isinstance(eid2, str):
        sys.stderr.write("employee_id invalid\n")
        sys.exit(2)
    if eid2 not in employees:
        continue
    emp = employees[eid2]
    if "end_date" not in emp:
        sys.stderr.write("end_date missing\n")
        sys.exit(2)
    ed = emp["end_date"]
    if ed is None:
        continue
    if not isinstance(ed, str):
        sys.stderr.write("end_date invalid\n")
        sys.exit(2)
    if not pat.match(ed):
        sys.stderr.write("end_date date invalid\n")
        sys.exit(2)
    if ed < as_of:
        bad.append(lg)
bad_sorted = sorted(bad)
total_accounts = len(accounts)
total_employees = len(employees)
if bad_sorted:
    status = "fail"
    observed = bad_sorted
else:
    status = "pass"
    observed = []
detail = "Checked " + str(enabled_person) + " enabled person accounts among " + str(total_accounts) + " accounts against " + str(total_employees) + " employees at as_of " + as_of + ": " + str(len(bad_sorted)) + " with end_date before as_of"
print(json.dumps({"status": status, "observed": observed, "expected": "enabled=false where type=person and end_date < as_of", "detail": detail, "evidence_page": "/lifecycle/reconciliation"}))
