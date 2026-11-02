# Attest — test PSI-4.2 (MFA obligatoire pour les utilisateurs du système critique)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import os
import sys
import requests
import json
import re
url = os.environ["LAB_URL"].rstrip("/") + "/api/security"
headers = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
try:
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    observed = data.get("mfa_users")
except Exception as e:
    observed = None
    data = {}
status = "pass" if observed is True else "fail"
expected = "mfa_users = true"
detail = "GET /api/security returned mfa_users=%r." % (observed,)
print(json.dumps({"status": status, "observed": observed, "expected": expected, "detail": detail}))
