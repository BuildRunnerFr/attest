# Attest — test PSI-5.5 (Movers - removal of prior rights)
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
  sys.stderr.write("missing env\n")
  sys.exit(2)
headers = {"Authorization": "Bearer " + token}
base = base.rstrip("/")
if not isinstance(base, str) or base == "":
  sys.stderr.write("bad base\n")
  sys.exit(2)
if not isinstance(token, str) or token == "":
  sys.stderr.write("bad token\n")
  sys.exit(2)
date_pat = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
def parse_date(s):
  m = date_pat.match(s)
  if m is None:
    sys.stderr.write("bad date " + str(s) + "\n")
    sys.exit(2)
  y = int(m.group(1))
  mo = int(m.group(2))
  d = int(m.group(3))
  if mo < 1 or mo > 12:
    sys.stderr.write("bad date " + str(s) + "\n")
    sys.exit(2)
  leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
  if mo == 2:
    dim = 29 if leap else 28
  elif mo == 4 or mo == 6 or mo == 9 or mo == 11:
    dim = 30
  else:
    dim = 31
  if d < 1 or d > dim:
    sys.stderr.write("bad date " + str(s) + "\n")
    sys.exit(2)
  yy = y
  if mo <= 2:
    yy = y - 1
  if mo > 2:
    mp = mo - 3
  else:
    mp = mo + 9
  era = yy // 400
  yoe = yy - era * 400
  doy = (153 * mp + 2) // 5 + d - 1
  doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
  return era * 146097 + doe
def fetch_list(path):
  url = base + path
  out = []
  while True:
    try:
      r = requests.get(url, headers=headers)
    except Exception as e:
      sys.stderr.write("request failed " + str(e) + "\n")
      sys.exit(2)
    if r.status_code != 200:
      sys.stderr.write("bad status " + str(r.status_code) + " for " + url + "\n")
      sys.exit(2)
    try:
      data = r.json()
    except Exception:
      sys.stderr.write("bad json for " + url + "\n")
      sys.exit(2)
    if not isinstance(data, list):
      sys.stderr.write("bad list for " + url + "\n")
      sys.exit(2)
    for item in data:
      out.append(item)
    links = r.links
    nxt = None
    if isinstance(links, dict):
      if "next" in links:
        nd = links["next"]
        if isinstance(nd, dict):
          if "url" in nd:
            nxt = nd["url"]
    if nxt is None:
      break
    if not isinstance(nxt, str):
      sys.stderr.write("bad next link\n")
      sys.exit(2)
    if nxt.startswith("http://") or nxt.startswith("https://"):
      url = nxt
    else:
      if nxt.startswith("/"):
        url = base + nxt
      else:
        url = base + "/" + nxt
  return out
try:
  meta_r = requests.get(base + "/api/lifecycle/meta", headers=headers)
except Exception:
  sys.stderr.write("meta request failed\n")
  sys.exit(2)
if meta_r.status_code != 200:
  sys.stderr.write("meta bad status\n")
  sys.exit(2)
try:
  meta = meta_r.json()
except Exception:
  sys.stderr.write("meta bad json\n")
  sys.exit(2)
if not isinstance(meta, dict):
  sys.stderr.write("meta bad data\n")
  sys.exit(2)
if "as_of" not in meta:
  sys.stderr.write("meta missing as_of\n")
  sys.exit(2)
as_of_s = meta["as_of"]
if not isinstance(as_of_s, str):
  sys.stderr.write("meta bad as_of\n")
  sys.exit(2)
as_of_days = parse_date(as_of_s)
try:
  ev_r = requests.get(base + "/lifecycle/reconciliation", headers=headers)
except Exception:
  sys.stderr.write("evidence request failed\n")
  sys.exit(2)
if ev_r.status_code != 200:
  sys.stderr.write("evidence bad status\n")
  sys.exit(2)
emp_list = fetch_list("/api/hr/employees")
acc_list = fetch_list("/api/lifecycle/accounts")
ent_list = fetch_list("/api/lifecycle/entitlements")
ent_map = {}
for e in ent_list:
  if not isinstance(e, dict):
    sys.stderr.write("bad entitlement entry\n")
    sys.exit(2)
  if "name" not in e or "department" not in e:
    sys.stderr.write("bad entitlement fields\n")
    sys.exit(2)
  n = e["name"]
  dept = e["department"]
  if not isinstance(n, str):
    sys.stderr.write("bad entitlement name\n")
    sys.exit(2)
  if dept is not None and not isinstance(dept, str):
    sys.stderr.write("bad entitlement department\n")
    sys.exit(2)
  if n not in ent_map:
    ent_map[n] = dept
emp_map = {}
for e in emp_list:
  if not isinstance(e, dict):
    sys.stderr.write("bad employee entry\n")
    sys.exit(2)
  if "employee_id" not in e or "previous_department" not in e or "transfer_date" not in e:
    sys.stderr.write("bad employee fields\n")
    sys.exit(2)
  eid = e["employee_id"]
  prev = e["previous_department"]
  tdate = e["transfer_date"]
  if not isinstance(eid, str):
    sys.stderr.write("bad employee id\n")
    sys.exit(2)
  if prev is not None and not isinstance(prev, str):
    sys.stderr.write("bad previous department\n")
    sys.exit(2)
  if tdate is not None and not isinstance(tdate, str):
    sys.stderr.write("bad transfer date\n")
    sys.exit(2)
  if prev is None and tdate is None:
    if eid not in emp_map:
      emp_map[eid] = (None, None)
    continue
  if prev is None or tdate is None:
    sys.stderr.write("incomplete mover data for " + eid + "\n")
    sys.exit(2)
  parse_date(tdate)
  if eid not in emp_map:
    emp_map[eid] = (prev, tdate)
acc_map = {}
for a in acc_list:
  if not isinstance(a, dict):
    sys.stderr.write("bad account entry\n")
    sys.exit(2)
  if "login" not in a or "type" not in a or "employee_id" not in a or "owner_employee_id" not in a or "enabled" not in a or "entitlements" not in a:
    sys.stderr.write("bad account fields\n")
    sys.exit(2)
  login = a["login"]
  typ = a["type"]
  en = a["enabled"]
  ents = a["entitlements"]
  if not isinstance(login, str):
    sys.stderr.write("bad login\n")
    sys.exit(2)
  if not isinstance(typ, str):
    sys.stderr.write("bad type\n")
    sys.exit(2)
  if typ != "person" and typ != "service":
    sys.stderr.write("bad account type " + typ + "\n")
    sys.exit(2)
  if not isinstance(en, bool):
    sys.stderr.write("bad enabled for " + login + "\n")
    sys.exit(2)
  if not isinstance(ents, list):
    sys.stderr.write("bad entitlements for " + login + "\n")
    sys.exit(2)
  for ename in ents:
    if not isinstance(ename, str):
      sys.stderr.write("bad entitlement name for " + login + "\n")
      sys.exit(2)
  holder_tmp = None
  if typ == "person":
    holder_tmp = a["employee_id"]
  else:
    holder_tmp = a["owner_employee_id"]
  if holder_tmp is not None and not isinstance(holder_tmp, str):
    sys.stderr.write("bad holder for " + login + "\n")
    sys.exit(2)
  if login not in acc_map:
    acc_map[login] = a
bad = []
enabled_total = 0
beyond_total = 0
for login in acc_map:
  a = acc_map[login]
  typ = a["type"]
  en = a["enabled"]
  ents = a["entitlements"]
  if en is False:
    continue
  enabled_total = enabled_total + 1
  if typ == "person":
    holder = a["employee_id"]
  else:
    holder = a["owner_employee_id"]
  if holder is None:
    continue
  if holder not in emp_map:
    continue
  prev = emp_map[holder][0]
  tdate = emp_map[holder][1]
  if prev is None:
    continue
  tdays = parse_date(tdate)
  diff = as_of_days - tdays
  if diff <= 30:
    continue
  beyond_total = beyond_total + 1
  hit = False
  for ename in ents:
    if ename not in ent_map:
      sys.stderr.write("unknown entitlement " + ename + "\n")
      sys.exit(2)
    edept = ent_map[ename]
    if edept is None:
      continue
    if edept == prev:
      hit = True
      break
  if hit:
    bad.append(login)
bad = sorted(bad)
if len(bad) == 0:
  status = "pass"
else:
  status = "fail"
expected_s = "entitlements with department=previous_department removed where as_of minus transfer_date > 30 and enabled=true"
detail = "Checked " + str(enabled_total) + " enabled accounts (" + str(beyond_total) + " beyond 30 days after transfer) at as_of " + as_of_s + ", found " + str(len(bad)) + " retaining prior-department entitlements."
print(json.dumps({"status": status, "observed": bad, "expected": expected_s, "detail": detail, "evidence_page": "/lifecycle/reconciliation"}))
