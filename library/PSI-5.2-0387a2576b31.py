# Attest — test PSI-5.2 (Account ownership)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re
try:
    base = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except Exception:
    sys.stderr.write("missing LAB_URL or LAB_TOKEN\n")
    sys.exit(2)
if not isinstance(base, str) or base == "":
    sys.stderr.write("invalid LAB_URL value\n")
    sys.exit(2)
if not isinstance(token, str) or token == "":
    sys.stderr.write("invalid LAB_TOKEN value\n")
    sys.exit(2)
base = base.rstrip("/")
headers = {"Authorization": "Bearer " + token}
emp_status = {}
url = base + "/api/hr/employees"
while url:
    try:
        resp = requests.get(url, headers=headers)
    except Exception:
        sys.stderr.write("employees request failed\n")
        sys.exit(2)
    if resp.status_code != 200:
        sys.stderr.write("employees request error " + str(resp.status_code) + "\n")
        sys.exit(2)
    try:
        data = resp.json()
    except Exception:
        sys.stderr.write("employees invalid json\n")
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write("employees unexpected payload\n")
        sys.exit(2)
    for item in data:
        if not isinstance(item, dict):
            sys.stderr.write("employee unexpected record\n")
            sys.exit(2)
        if "employee_id" not in item or "status" not in item:
            sys.stderr.write("employee missing fields\n")
            sys.exit(2)
        eid = item["employee_id"]
        st = item["status"]
        if not isinstance(eid, str) or eid == "":
            sys.stderr.write("employee invalid id\n")
            sys.exit(2)
        if not isinstance(st, str):
            sys.stderr.write("employee invalid status\n")
            sys.exit(2)
        if eid not in emp_status:
            emp_status[eid] = st
    nxt = None
    links = resp.links
    if "next" in links:
        info = links["next"]
        if "url" not in info:
            sys.stderr.write("employees invalid next link\n")
            sys.exit(2)
        nxt = info["url"]
        if not isinstance(nxt, str):
            sys.stderr.write("employees invalid next url\n")
            sys.exit(2)
    if nxt:
        if re.match("https?://", nxt):
            url = nxt
        elif nxt.startswith("/"):
            url = base + nxt
        else:
            url = base + "/" + nxt
    else:
        url = None
acc_map = {}
url = base + "/api/lifecycle/accounts"
while url:
    try:
        resp = requests.get(url, headers=headers)
    except Exception:
        sys.stderr.write("accounts request failed\n")
        sys.exit(2)
    if resp.status_code != 200:
        sys.stderr.write("accounts request error " + str(resp.status_code) + "\n")
        sys.exit(2)
    try:
        data = resp.json()
    except Exception:
        sys.stderr.write("accounts invalid json\n")
        sys.exit(2)
    if not isinstance(data, list):
        sys.stderr.write("accounts unexpected payload\n")
        sys.exit(2)
    for item in data:
        if not isinstance(item, dict):
            sys.stderr.write("account unexpected record\n")
            sys.exit(2)
        if "login" not in item or "type" not in item or "enabled" not in item:
            sys.stderr.write("account missing fields\n")
            sys.exit(2)
        login = item["login"]
        typ = item["type"]
        ena = item["enabled"]
        if not isinstance(login, str) or login == "":
            sys.stderr.write("account invalid login\n")
            sys.exit(2)
        if typ != "person" and typ != "service":
            sys.stderr.write("account invalid type\n")
            sys.exit(2)
        if not isinstance(ena, bool):
            sys.stderr.write("account invalid enabled flag\n")
            sys.exit(2)
        if "employee_id" not in item or "owner_employee_id" not in item:
            sys.stderr.write("account missing ownership fields\n")
            sys.exit(2)
        if login not in acc_map:
            acc_map[login] = item
    nxt = None
    links = resp.links
    if "next" in links:
        info = links["next"]
        if "url" not in info:
            sys.stderr.write("accounts invalid next link\n")
            sys.exit(2)
        nxt = info["url"]
        if not isinstance(nxt, str):
            sys.stderr.write("accounts invalid next url\n")
            sys.exit(2)
    if nxt:
        if re.match("https?://", nxt):
            url = nxt
        elif nxt.startswith("/"):
            url = base + nxt
        else:
            url = base + "/" + nxt
    else:
        url = None
try:
    ev = requests.get(base + "/lifecycle/reconciliation", headers=headers)
except Exception:
    sys.stderr.write("evidence request failed\n")
    sys.exit(2)
if ev.status_code != 200:
    sys.stderr.write("evidence request error " + str(ev.status_code) + "\n")
    sys.exit(2)
offenders = []
person_total = 0
service_total = 0
for login, acc in acc_map.items():
    if acc["enabled"] is not True:
        continue
    typ = acc["type"]
    if typ == "person":
        person_total = person_total + 1
        eid = acc["employee_id"]
        if not isinstance(eid, str) or eid == "":
            offenders.append(login)
        elif eid not in emp_status:
            offenders.append(login)
    else:
        service_total = service_total + 1
        owner = acc["owner_employee_id"]
        if not isinstance(owner, str) or owner == "":
            offenders.append(login)
        elif owner not in emp_status:
            offenders.append(login)
        elif emp_status[owner] != "active":
            offenders.append(login)
offenders = sorted(offenders)
enabled_total = person_total + service_total
emp_total = len(emp_status)
expected = "employee_id in employees.employee_id for enabled person accounts; owner_employee_id in employees.employee_id with status=active for enabled service accounts"
if len(offenders) == 0:
    status = "pass"
else:
    status = "fail"
detail = "Checked " + str(enabled_total) + " enabled accounts (" + str(person_total) + " person, " + str(service_total) + " service) against " + str(emp_total) + " HR employees: " + str(len(offenders)) + " orphan or ownerless accounts found"
print(json.dumps({"status": status, "observed": offenders, "expected": expected, "detail": detail, "evidence_page": "/lifecycle/reconciliation"}))
