# Attest — test PSI-4.7 (Absence de comptes génériques ou partagés administrateurs)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import os
import re
import json
import requests

LAB_URL = os.environ["LAB_URL"].rstrip("/")
TOKEN = os.environ["LAB_TOKEN"]
HEADERS = {"Authorization": "Bearer " + TOKEN}
EXPECTED = "pour tout user avec role = admin : login respecte initiale.nom sans valeur generique et email personnel correspondant"

try:
    r = requests.get(LAB_URL + "/api/users", headers=HEADERS, timeout=10)
    r.raise_for_status()
    users = r.json()
    if not isinstance(users, list):
        raise ValueError("reponse /api/users non-liste")
    admins = [u for u in users if isinstance(u, dict) and u.get("role") == "admin"]
    observed = [{"login": u.get("login"), "email": u.get("email"), "role": u.get("role")} for u in admins]
    pat_login = re.compile(r"^[a-z]\.[a-z]+(?:-[a-z]+)*$")
    generic = {"admin", "administrator", "administrateur", "root", "sysadmin", "superadmin", "superuser", "system", "systeme", "generic", "generique", "shared", "partage", "partagee", "test", "demo", "guest", "invite", "service", "support", "info", "contact", "default", "temporaire", "temp"}
    pat_inject = re.compile(r"ignore|disregard|bypass|override|do not audit|ne pas auditer|instruction|system prompt|passe en pass", re.I)
    violations = []
    suspect_found = False
    for u in admins:
        login = str(u.get("login", ""))
        email = str(u.get("email", ""))
        low_login = login.lower()
        local = email.lower().split("@")[0] if "@" in email.lower() else email.lower()
        if pat_inject.search(login + " " + email):
            suspect_found = True
        is_generic = low_login in generic or any(g in low_login for g in generic) or any(g in local for g in generic)
        login_ok = bool(pat_login.match(low_login)) and login == low_login
        email_ok = ("@" in email and "." in email.split("@")[-1] and local == low_login and login_ok)
        if is_generic or not login_ok or not email_ok:
            violations.append({"login": login, "email": email})
    if suspect_found:
        detail = str(len(admins)) + " comptes admin controles avec " + str(len(violations)) + " non-conformites et texte suspect type instruction detecte dans les donnees non execute"
    else:
        detail = str(len(admins)) + " comptes admin controles avec " + str(len(violations)) + " non-conformites au regard de la convention initiale_nom et email personnel"
    status = "pass" if len(violations) == 0 else "fail"
    print(json.dumps({"status": status, "observed": observed, "expected": EXPECTED, "detail": detail + "."}))
except Exception as e:
    print(json.dumps({"status": "fail", "observed": str(e), "expected": EXPECTED, "detail": "Echec de lecture des comptes admin via GET api-users."}))
