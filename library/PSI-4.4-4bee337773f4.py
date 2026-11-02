# Attest — test PSI-4.4 (Verrouillage des comptes après échecs de connexion)
# Écrit par muse-spark-1.3 le 2026-11-02 — à relire avant validation.
import os
import requests
import json
import sys
import re
try:
    base = os.environ["LAB_URL"].rstrip("/")
    headers = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
    r = requests.get(base + "/api/security", headers=headers, timeout=10)
    data = r.json()
    threshold = data.get("lockout_threshold")
    raw = json.dumps(data, ensure_ascii=False)
    has_instr = bool(re.search(r"(?i)ignore\s+(previous|.*instruction)|disregard\s+.*instruction|override\s+.*(rule|control|policy)|system\s+prompt|do\s+not\s+report", raw))
    ok = type(threshold) is int and 1 <= threshold <= 5
    status = "pass" if ok else "fail"
    if has_instr:
        detail = f"GET /api/security returned lockout_threshold={threshold!r} with untrusted instructional text detected and not followed."
    else:
        detail = f"GET /api/security returned lockout_threshold={threshold!r}."
    print(json.dumps({"status": status, "observed": threshold, "expected": "lockout_threshold != 0 et lockout_threshold <= 5", "detail": detail}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"status": "fail", "observed": None, "expected": "lockout_threshold != 0 et lockout_threshold <= 5", "detail": "GET /api/security did not return a verifiable lockout_threshold."}, ensure_ascii=False))
