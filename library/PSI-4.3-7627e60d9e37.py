# Attest — test PSI-4.3 (Strong password policy with length and complexity)
# Écrit par muse-spark-1.3 le 2026-11-12 — à relire avant validation.
import requests
import json
import os
import sys
import re
if "LAB_URL" not in os.environ:
    sys.stderr.write("missing LAB_URL\n")
    sys.exit(2)
if "LAB_TOKEN" not in os.environ:
    sys.stderr.write("missing LAB_TOKEN\n")
    sys.exit(2)
baseUrl = os.environ["LAB_URL"]
tokenVal = os.environ["LAB_TOKEN"]
baseUrl = baseUrl.rstrip("/")
headers = {"Authorization": "Bearer " + tokenVal}
try:
    respRealm = requests.get(baseUrl + "/api/kc/realm", headers=headers)
except Exception as ex:
    sys.stderr.write("request failed for realm api: " + str(ex) + "\n")
    sys.exit(2)
if respRealm.status_code != 200:
    sys.stderr.write("realm api returned status " + str(respRealm.status_code) + "\n")
    sys.exit(2)
try:
    respEvidence = requests.get(baseUrl + "/kc/realm", headers=headers)
except Exception as ex:
    sys.stderr.write("request failed for evidence page: " + str(ex) + "\n")
    sys.exit(2)
if respEvidence.status_code != 200:
    sys.stderr.write("evidence page returned status " + str(respEvidence.status_code) + "\n")
    sys.exit(2)
try:
    dataRealm = respRealm.json()
except Exception as ex:
    sys.stderr.write("invalid json for realm: " + str(ex) + "\n")
    sys.exit(2)
if not isinstance(dataRealm, dict):
    sys.stderr.write("unexpected realm data type\n")
    sys.exit(2)
policyVal = dataRealm.get("passwordPolicy")
if policyVal is not None and not isinstance(policyVal, str):
    sys.stderr.write("unexpected passwordPolicy type\n")
    sys.exit(2)
expectedReq = "passwordPolicy contains length(12) or greater and upperCase(1), lowerCase(1), digits(1) and specialChars(1)"
if policyVal is None:
    statusVal = "fail"
    observedVal = None
    detailVal = "Realm password policy is missing and does not satisfy length 12 or greater with upper-case, lower-case, digit and special-character requirements."
else:
    foundPairs = re.findall(r"([A-Za-z]+)\s*\(\s*(\d+)\s*\)", policyVal)
    parsedVals = {}
    for pairName, pairNum in foundPairs:
        parsedVals[pairName] = int(pairNum)
    hasLength = "length" in parsedVals and parsedVals["length"] >= 12
    hasUpper = "upperCase" in parsedVals and parsedVals["upperCase"] >= 1
    hasLower = "lowerCase" in parsedVals and parsedVals["lowerCase"] >= 1
    hasDigits = "digits" in parsedVals and parsedVals["digits"] >= 1
    hasSpecial = "specialChars" in parsedVals and parsedVals["specialChars"] >= 1
    if hasLength and hasUpper and hasLower and hasDigits and hasSpecial:
        statusVal = "pass"
        observedVal = policyVal
        detailVal = "Realm password policy satisfies length 12 or greater with upper-case, lower-case, digit and special-character requirements."
    else:
        statusVal = "fail"
        observedVal = policyVal
        detailVal = "Realm password policy does not satisfy length 12 or greater with upper-case, lower-case, digit and special-character requirements."
print(json.dumps({"status": statusVal, "observed": observedVal, "expected": expectedReq, "detail": detailVal, "evidence_page": "/kc/realm"}))
