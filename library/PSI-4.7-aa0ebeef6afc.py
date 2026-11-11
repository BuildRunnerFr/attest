# Attest — test PSI-4.7 (No generic or shared admin accounts)
# Écrit par muse-spark-1.3 le 2026-11-11 — à relire avant validation.
import requests
import json
import os
import sys
import re
try:
    base_url = os.environ["LAB_URL"]
    lab_token = os.environ["LAB_TOKEN"]
except KeyError:
    sys.stderr.write("missing env\n")
    sys.exit(2)
if not isinstance(base_url, str) or not isinstance(lab_token, str) or not base_url or not lab_token:
    sys.stderr.write("missing env\n")
    sys.exit(2)
base_url = base_url.rstrip("/")
headers = {"Authorization": "Bearer " + lab_token}
try:
    ev = requests.get(base_url + "/admin/users", headers=headers)
except Exception:
    sys.stderr.write("evidence request failed\n")
    sys.exit(2)
if ev.status_code != 200:
    sys.stderr.write("evidence request failed\n")
    sys.exit(2)
all_users = []
next_url = base_url + "/api/users"
visited = []
page_count = 0
while next_url:
    if next_url in visited:
        sys.stderr.write("pagination loop\n")
        sys.exit(2)
    visited.append(next_url)
    current_url = next_url
    try:
        resp = requests.get(next_url, headers=headers)
    except Exception:
        sys.stderr.write("users request failed\n")
        sys.exit(2)
    if resp.status_code != 200:
        sys.stderr.write("users request failed\n")
        sys.exit(2)
    page_count = page_count + 1
    try:
        payload = resp.json()
    except Exception:
        sys.stderr.write("bad json\n")
        sys.exit(2)
    if isinstance(payload, list):
        batch = payload
    elif isinstance(payload, dict):
        batch = None
        for key in ("users", "data", "items", "results"):
            if key in payload and isinstance(payload[key], list):
                batch = payload[key]
                break
        if batch is None:
            sys.stderr.write("unexpected users format\n")
            sys.exit(2)
    else:
        sys.stderr.write("unexpected users format\n")
        sys.exit(2)
    for entry in batch:
        all_users.append(entry)
    candidate = None
    try:
        linkmap = resp.links
        if "next" in linkmap:
            info = linkmap["next"]
            if "url" in info:
                candidate = info["url"]
    except Exception:
        candidate = None
    if not candidate:
        if "Link" in resp.headers:
            lh = resp.headers["Link"]
            if isinstance(lh, str):
                m2 = re.search(r'<([^>]+)>\s*;\s*rel="next"', lh)
                if m2:
                    candidate = m2.group(1)
    if candidate:
        if candidate.startswith("http://") or candidate.startswith("https://"):
            next_url = candidate
        elif candidate.startswith("/"):
            next_url = base_url + candidate
        else:
            next_url = base_url + "/" + candidate
    else:
        total_pages = None
        if "X-Total-Pages" in resp.headers:
            try:
                total_pages = int(resp.headers["X-Total-Pages"])
            except Exception:
                sys.stderr.write("bad total pages\n")
                sys.exit(2)
        if total_pages is not None:
            cur_page = None
            for hkey in ("X-Current-Page", "X-Page"):
                if hkey in resp.headers:
                    try:
                        cur_page = int(resp.headers[hkey])
                    except Exception:
                        cur_page = None
                    if cur_page is not None:
                        break
            if cur_page is None:
                m = re.search(r"[?&]page=(\d+)", current_url)
                if m:
                    cur_page = int(m.group(1))
                else:
                    cur_page = page_count
            if cur_page < total_pages:
                want = cur_page + 1
                if re.search(r"[?&]page=\d+", current_url):
                    next_url = re.sub(r"([?&]page=)\d+", r"\g<1>" + str(want), current_url)
                else:
                    if "?" in current_url:
                        next_url = current_url + "&page=" + str(want)
                    else:
                        next_url = current_url + "?page=" + str(want)
            else:
                next_url = None
        else:
            next_url = None
def tokens_of(value):
    parts = re.split(r"[^A-Za-z]+", value.lower())
    out = []
    for p in parts:
        if p:
            out.append(p)
    return out
generic = ["admin", "administrator", "administrateur", "root", "superuser", "sysadmin", "system", "support", "helpdesk", "help", "team", "equipe", "service", "services", "contact", "info", "infos", "generic", "generique", "shared", "partage", "test", "demo", "guest", "operator", "security"]
admins = []
for u in all_users:
    if not isinstance(u, dict):
        sys.stderr.write("unexpected user entry\n")
        sys.exit(2)
    if "login" not in u or "email" not in u or "role" not in u:
        sys.stderr.write("missing user field\n")
        sys.exit(2)
    login = u["login"]
    email = u["email"]
    role = u["role"]
    if not isinstance(login, str) or not isinstance(email, str) or not isinstance(role, str):
        sys.stderr.write("bad user field type\n")
        sys.exit(2)
    if role == "admin":
        admins.append(u)
admin_logins = []
for a in admins:
    admin_logins.append(a["login"])
offending = []
for a in admins:
    login = a["login"]
    email = a["email"]
    bad = False
    if not re.match(r"^[A-Za-z]\.[A-Za-z]+(?:-[A-Za-z]+)*$", login):
        bad = True
    else:
        lt = tokens_of(login)
        for t in lt:
            if t in generic:
                bad = True
                break
    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        bad = True
    else:
        local = parts[0]
        if "." not in local:
            bad = True
        elif not re.match(r"^[A-Za-z]+(?:[.\-][A-Za-z]+)+$", local):
            bad = True
        else:
            et = tokens_of(local)
            for t in et:
                if t in generic:
                    bad = True
                    break
    if bad:
        offending.append(login)
expected = "for all users where role == admin: login matches initiale.nom pattern and email is personal, with no function login and no shared mailbox"
total_count = len(all_users)
admin_count = len(admins)
off_count = len(offending)
if off_count == 0:
    detail = "Checked " + str(admin_count) + " admin accounts among " + str(total_count) + " users across " + str(page_count) + " pages with no generic or shared admin account"
    print(json.dumps({"status": "pass", "observed": admin_logins, "expected": expected, "detail": detail, "evidence_page": "/admin/users"}))
else:
    detail = "Checked " + str(admin_count) + " admin accounts among " + str(total_count) + " users across " + str(page_count) + " pages with " + str(off_count) + " generic or shared admin accounts"
    print(json.dumps({"status": "fail", "observed": offending, "expected": expected, "detail": detail, "evidence_page": "/admin/users"}))
