import requests
import json
import os
import sys
import re

try:
    base = os.environ["LAB_URL"]
    token = os.environ["LAB_TOKEN"]
except KeyError as e:
    print(f"missing env var: {e}", file=sys.stderr)
    sys.exit(2)

url = base.rstrip("/") + "/api/users"
try:
    r = requests.get(url, headers={"Authorization": "Bearer " + token}, timeout=10)
except Exception as e:
    print(f"GET /api/users failed: {e}", file=sys.stderr)
    sys.exit(2)

if r.status_code != 200:
    print(f"GET /api/users unexpected status: {r.status_code}", file=sys.stderr)
    sys.exit(2)

try:
    data = r.json()
except Exception as e:
    print(f"invalid JSON for /api/users: {e}", file=sys.stderr)
    sys.exit(2)

if not isinstance(data, list):
    print("unexpected data: /api/users is not a list", file=sys.stderr)
    sys.exit(2)

for u in data:
    if not isinstance(u, dict):
        print("unexpected data: user entry is not an object", file=sys.stderr)
        sys.exit(2)
    for k in ("login", "email", "role"):
        if k not in u:
            print(f"unexpected data: missing key {k}", file=sys.stderr)
            sys.exit(2)
    if not isinstance(u["login"], str) or not isinstance(u["email"], str) or not isinstance(u["role"], str):
        print("unexpected data: login/email/role wrong type", file=sys.stderr)
        sys.exit(2)
    if u["role"] not in ("admin", "conseiller"):
        print(f"unexpected data: unknown role {u['role']}", file=sys.stderr)
        sys.exit(2)

admins = [u for u in data if u["role"] == "admin"]
login_re = re.compile(r"^[A-Za-z]\.[A-Za-z][A-Za-z\-]*$")
generic = {"admin", "administrator", "administrateur", "root", "superuser", "superadmin", "sysadmin", "support", "helpdesk", "service", "services", "contact", "info", "infos", "accueil", "generic", "generique", "team", "equipe", "shared", "partage", "fonction", "function", "fonctionnel", "bureau", "office", "test", "demo", "backup", "system", "systeme", "securite", "security", "compta", "direction", "caisse", "guichet", "agence", "standard", "commun", "gen"}

def is_generic(s):
    parts = re.split(r"[._\-+]+", s.lower())
    for p in parts:
        if p in generic:
            return True
        for g in generic:
            if p == g:
                return True
            if len(p) > len(g) and p.startswith(g) and p[len(g):].isdigit():
                return True
    return False

violations = []
observed = []
for u in admins:
    login = u["login"]
    email = u["email"]
    observed.append({"login": login, "email": email, "role": "admin"})
    local = email.split("@")[0] if "@" in email else email
    login_ok = bool(login_re.match(login))
    login_gen = is_generic(login)
    email_gen = is_generic(local) if local else True
    email_valid = "@" in email and "." in email.split("@")[-1]
    if (not login_ok) or login_gen or email_gen or (not email_valid):
        violations.append({"login": login, "email": email, "login_ok": login_ok, "login_generic": login_gen, "email_generic": email_gen})

expected = "for all users where role == admin: login matches initiale.nom pattern and email is personal, with no function login and no shared mailbox"

if not violations:
    status = "pass"
    detail = f"All {len(admins)} admin account(s) have nominative initiale.nom logins and personal emails with no shared mailbox."
else:
    status = "fail"
    detail = f"{len(violations)} of {len(admins)} admin account(s) violate nominative login or personal email requirements."

print(json.dumps({"status": status, "observed": observed, "expected": expected, "detail": detail}))
