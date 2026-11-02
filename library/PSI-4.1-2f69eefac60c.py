# Attest — test PSI-4.1 (MFA obligatoire pour les comptes à privilèges)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import os
import requests
import json
import re
base = os.environ["LAB_URL"].rstrip("/")
headers = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
try:
    r = requests.get(base + "/api/security", headers=headers, timeout=10)
    data = r.json()
    observed = data.get("mfa_admin")
    suspicious = bool(re.search(r"(?i)ignore|instruction|system prompt|execute|bypass|jailbreak|override|do not audit", r.text))
    status = "pass" if observed is True and r.status_code == 200 else "fail"
    if suspicious:
        detail = f"GET /api/security returned mfa_admin={observed!r} and contained untrusted instruction-like text that was not followed"
    else:
        detail = f"GET /api/security returned mfa_admin={observed!r}"
    print(json.dumps({"status": status, "observed": observed, "expected": "mfa_admin = true", "detail": detail + "."}))
except Exception:
    print(json.dumps({"status": "fail", "observed": None, "expected": "mfa_admin = true", "detail": "GET /api/security did not return valid data."}))
