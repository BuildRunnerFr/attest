# Attest — test PSI-5.6 (Privileged access review)
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
    sys.stderr.write("missing env\n")
    sys.exit(2)

if base.endswith("/"):
    base = base[:-1]

headers = {"Authorization": "Bearer " + token}

def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(2)

pat = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

def parse_ymd(s):
    mt = pat.match(s)
    if mt is None:
        fail("bad date: " + s)
    y = int(mt.group(1))
    m = int(mt.group(2))
    d = int(mt.group(3))
    if m < 1 or m > 12:
        fail("bad date: " + s)
    leap = 0
    if y % 400 == 0:
        leap = 1
    elif y % 100 == 0:
        leap = 0
    elif y % 4 == 0:
        leap = 1
    else:
        leap = 0
    ml = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    div = ml[m - 1]
    if d < 1 or d > div:
        fail("bad date: " + s)
    return y, m, d

def to_days(y, m, d):
    leap = 0
    if y % 400 == 0:
        leap = 1
    elif y % 100 == 0:
        leap = 0
    elif y % 4 == 0:
        leap = 1
    else:
        leap = 0
    ml = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    before_year = (y - 1) * 365 + (y - 1) // 4 - (y - 1) // 100 + (y - 1) // 400
    before_month = 0
    idx = 0
    while idx < m - 1:
        before_month = before_month + ml[idx]
        idx = idx + 1
    return before_year + before_month + (d - 1)

def fetch_list(start_url, idkey):
    out = []
    seen = {}
    url = start_url
    while url is not None:
        try:
            resp = requests.get(url, headers=headers)
        except Exception as ex:
            fail("request failed: " + str(ex))
        if resp.status_code != 200:
            fail("request failed status: " + str(resp.status_code))
        try:
            payload = resp.json()
        except Exception as ex:
            fail("json failed: " + str(ex))
        if not isinstance(payload, list):
            fail("unexpected payload")
        for item in payload:
            if not isinstance(item, dict):
                fail("unexpected item")
            if idkey not in item:
                fail("missing id")
            ident = item[idkey]
            if not isinstance(ident, str):
                fail("bad id")
            if ident not in seen:
                seen[ident] = True
                out.append(item)
        links = resp.links
        if isinstance(links, dict) and "next" in links:
            nxt = links["next"]
            if not isinstance(nxt, dict) or "url" not in nxt:
                fail("bad link")
            nxturl = nxt["url"]
            if not isinstance(nxturl, str) or len(nxturl) == 0:
                fail("bad link url")
            if nxturl.startswith("http://") or nxturl.startswith("https://"):
                url = nxturl
            else:
                if nxturl.startswith("/"):
                    url = base + nxturl
                else:
                    url = base + "/" + nxturl
        else:
            url = None
    return out

meta_url = base + "/api/lifecycle/meta"
try:
    meta_resp = requests.get(meta_url, headers=headers)
except Exception as ex:
    fail("meta request failed: " + str(ex))
if meta_resp.status_code != 200:
    fail("meta status: " + str(meta_resp.status_code))
try:
    meta_data = meta_resp.json()
except Exception as ex:
    fail("meta json failed")
if not isinstance(meta_data, dict):
    fail("bad meta")
if "as_of" not in meta_data:
    fail("missing as_of")
as_of_s = meta_data["as_of"]
if not isinstance(as_of_s, str):
    fail("bad as_of")
ay, am, ad = parse_ymd(as_of_s)
as_of_days = to_days(ay, am, ad)

accounts = fetch_list(base + "/api/lifecycle/accounts", "login")
ents = fetch_list(base + "/api/lifecycle/entitlements", "name")

priv = {}
for e in ents:
    if "name" not in e or "privileged" not in e:
        fail("bad entitlement")
    n = e["name"]
    p = e["privileged"]
    if not isinstance(n, str) or not isinstance(p, bool):
        fail("bad entitlement types")
    if p:
        priv[n] = True

ev_url = base + "/lifecycle/accounts"
try:
    ev_resp = requests.get(ev_url, headers=headers)
except Exception as ex:
    fail("evidence request failed: " + str(ex))
if ev_resp.status_code != 200:
    fail("evidence status: " + str(ev_resp.status_code))

bad = []
scoped = 0
for a in accounts:
    if "login" not in a or "enabled" not in a or "entitlements" not in a or "last_access_review" not in a:
        fail("bad account")
    login = a["login"]
    enabled = a["enabled"]
    elist = a["entitlements"]
    rev = a["last_access_review"]
    if not isinstance(login, str) or not isinstance(enabled, bool) or not isinstance(elist, list):
        fail("bad account types")
    for en in elist:
        if not isinstance(en, str):
            fail("bad entitlement entry")
    if rev is not None and not isinstance(rev, str):
        fail("bad review type")
    holds = False
    for en in elist:
        if en in priv:
            holds = True
    if enabled and holds:
        scoped = scoped + 1
        if rev is None:
            bad.append(login)
        else:
            ry, rm, rd = parse_ymd(rev)
            rdays = to_days(ry, rm, rd)
            diff = as_of_days - rdays
            if diff > 365:
                bad.append(login)

bad = sorted(bad)
expected = "last_access_review within 365 days before as_of where enabled=true and entitlements includes privileged=true"
if len(bad) == 0:
    detail = "Checked " + str(scoped) + " enabled accounts holding privileged entitlements at as_of " + as_of_s + ", all with last_access_review within 365 days."
    print(json.dumps({"status": "pass", "observed": [], "expected": expected, "detail": detail, "evidence_page": "/lifecycle/accounts"}))
else:
    detail = "Checked " + str(scoped) + " enabled accounts holding privileged entitlements at as_of " + as_of_s + ", found " + str(len(bad)) + " with null or stale review over 365 days."
    print(json.dumps({"status": "fail", "observed": bad, "expected": expected, "detail": detail, "evidence_page": "/lifecycle/accounts"}))
