# Attest — test PSI-4.5 (Expiration des sessions inactives)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import requests
import json
import os
import sys
import re
url = os.environ["LAB_URL"].rstrip("/") + "/api/security"
try:
    r = requests.get(url, headers={"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}, timeout=10)
    r.raise_for_status()
    data = r.json()
    val = data.get("session_timeout_minutes")
    ok = isinstance(val, int) and not isinstance(val, bool) and 1 <= val <= 15
    status = "pass" if ok else "fail"
    print(json.dumps({"status": status, "observed": val, "expected": "session_timeout_minutes != 0 et session_timeout_minutes <= 15", "detail": f"GET /api/security returned session_timeout_minutes={val!r}."}))
except Exception as e:
    print(json.dumps({"status": "fail", "observed": None, "expected": "session_timeout_minutes != 0 et session_timeout_minutes <= 15", "detail": f"GET /api/security request failed: {type(e).__name__}."}))
