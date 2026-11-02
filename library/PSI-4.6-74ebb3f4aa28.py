# Attest — test PSI-4.6 (Journalisation des actions d'administration)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import requests
import json
import os
import sys
import re

try:
    url = os.environ["LAB_URL"].rstrip("/") + "/api/security"
    headers = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    observed = data.get("admin_audit_log")
    status = "pass" if observed is True else "fail"
    detail = f"GET /api/security returned admin_audit_log={observed!r}."
    print(json.dumps({"status": status, "observed": observed, "expected": True, "detail": detail}))
except Exception as e:
    print(json.dumps({"status": "fail", "observed": None, "expected": True, "detail": f"GET /api/security request failed: {e!r}."}))
