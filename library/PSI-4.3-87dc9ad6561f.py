# Attest — test PSI-4.3 (Complexité et longueur minimale des mots de passe)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import requests
import json
import os
import sys
import re
base = os.environ["LAB_URL"].rstrip("/")
hdr = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
try:
    r = requests.get(base + "/api/security", headers=hdr, timeout=10)
    data = r.json()
    ml = data.get("password_min_length")
    cx = data.get("password_require_complexity")
    observed = {"password_min_length": ml, "password_require_complexity": cx}
    ok = isinstance(ml, int) and ml >= 12 and cx is True
    status = "pass" if ok else "fail"
    detail = f"GET /api/security returned password_min_length={ml!r} and password_require_complexity={cx!r}."
except Exception as e:
    observed = {"error": str(e)}
    status = "fail"
    detail = f"GET /api/security request failed with error {e!r}."
print(json.dumps({"status": status, "observed": observed, "expected": "password_min_length >= 12 et password_require_complexity = true", "detail": detail}))
