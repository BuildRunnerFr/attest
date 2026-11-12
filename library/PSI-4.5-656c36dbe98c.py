# Attest — test PSI-4.5 (Idle session timeout limited to 15 minutes)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re

try:
    base_url = os.environ["LAB_URL"]
    token_value = os.environ["LAB_TOKEN"]
except KeyError:
    sys.stderr.write("missing LAB_URL or LAB_TOKEN\n")
    sys.exit(2)

headers = {"Authorization": "Bearer " + token_value}
base_clean = base_url.rstrip("/")
api_url = base_clean + "/api/kc/realm"
evidence_url = base_clean + "/kc/realm"

try:
    resp = requests.get(api_url, headers=headers, timeout=30)
except Exception:
    sys.stderr.write("GET api/kc/realm request failed\n")
    sys.exit(2)

if resp.status_code != 200:
    sys.stderr.write("GET api/kc/realm unexpected status\n")
    sys.exit(2)

try:
    realm_data = resp.json()
except Exception:
    sys.stderr.write("api/kc/realm invalid json\n")
    sys.exit(2)

if not isinstance(realm_data, dict):
    sys.stderr.write("api/kc/realm unexpected data\n")
    sys.exit(2)

if "ssoSessionIdleTimeout" not in realm_data:
    sys.stderr.write("ssoSessionIdleTimeout missing\n")
    sys.exit(2)

timeout_value = realm_data["ssoSessionIdleTimeout"]

if isinstance(timeout_value, bool):
    sys.stderr.write("ssoSessionIdleTimeout unexpected type\n")
    sys.exit(2)

if not isinstance(timeout_value, int):
    sys.stderr.write("ssoSessionIdleTimeout unexpected type\n")
    sys.exit(2)

try:
    ev_resp = requests.get(evidence_url, headers=headers, timeout=30)
except Exception:
    sys.stderr.write("GET kc/realm request failed\n")
    sys.exit(2)

if ev_resp.status_code != 200:
    sys.stderr.write("GET kc/realm unexpected status\n")
    sys.exit(2)

expected_text = "ssoSessionIdleTimeout<=900 (seconds) and not disabled or zero"

if timeout_value <= 0:
    detail_text = "Realm ssoSessionIdleTimeout is " + str(timeout_value) + " seconds, timeout is disabled and exceeds the 900-second limit."
    print(json.dumps({"status": "fail", "observed": timeout_value, "expected": expected_text, "detail": detail_text, "evidence_page": "/kc/realm"}))
elif timeout_value <= 900:
    detail_text = "Realm ssoSessionIdleTimeout is " + str(timeout_value) + " seconds, within the 900-second limit."
    print(json.dumps({"status": "pass", "observed": timeout_value, "expected": expected_text, "detail": detail_text, "evidence_page": "/kc/realm"}))
else:
    detail_text = "Realm ssoSessionIdleTimeout is " + str(timeout_value) + " seconds, exceeding the 900-second limit."
    print(json.dumps({"status": "fail", "observed": timeout_value, "expected": expected_text, "detail": detail_text, "evidence_page": "/kc/realm"}))
