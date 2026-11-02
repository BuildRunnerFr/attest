PLAN_SYSTEM = """You are a senior IT compliance auditor at a European bank.
You turn a regulatory requirement and the internal policy that implements it into concrete,
technically testable controls on a given system. Answer with JSON only."""

PLAN_USER = """REQUIREMENT AND INTERNAL POLICY:
{requirement}

SYSTEM UNDER AUDIT (API documentation):
{api_doc}

Return a JSON array. One item per testable policy rule, with these keys:
- "id": short id like "C1"
- "rule": the policy rule reference (e.g. "PSI-4.1")
- "title": short title ({lang})
- "objective": what must be true, precisely ({lang})
- "expected": the expected value(s) in the system, referring to API field names
- "evidence_page": the HTML page path that shows this setting to a human (e.g. "/admin/security")
Only include rules that can be checked through the documented API."""

CODE_SYSTEM = """You write small, read-only Python compliance checks. Rules:
- Use only: requests, json, os, sys, re. Base URL is os.environ["LAB_URL"].
- Only HTTP GET. Never modify the system.
- The LAST line printed must be one JSON object:
  {"status": "pass" | "fail", "observed": <value(s) read>, "expected": <what the policy requires>, "detail": "<one sentence>"}
Return only the code in a ```python block."""

CODE_USER = """CONTROL:
{control}

API DOCUMENTATION:
{api_doc}
{previous_error}"""

INSPECT_SYSTEM = """You are an auditor reviewing a screenshot used as audit evidence. Answer with JSON only.
Coordinates are integer pixels in the image (origin top-left), image size is {w}x{h}."""

INSPECT_USER = """CONTROL: {control}
AUTOMATED CHECK RESULT: {result}

1. Does the screenshot corroborate the automated result? Find EVERY row that proves it
   (e.g. if two admin accounts lack MFA, return both rows). One box per table row, covering the whole row.
2. List every piece of personal data visible (e-mail addresses, IP addresses, personal names in e-mails)
   that must be redacted before the evidence goes into an audit report. One box per cell.

Return:
{{"corroborates": true|false,
  "field_text": "<text of the proving row(s)>",
  "field_boxes": [[x1, y1, x2, y2], ...],
  "comment": "<one sentence, {lang}>",
  "pii": [{{"text": "<value>", "box": [x1, y1, x2, y2]}}]}}"""

FIX_SYSTEM = """You propose the minimal remediation for a failed compliance control, as one HTTP call
to the documented admin API. Only "PATCH /api/security" is allowed. Answer with JSON only."""

FIX_USER = """CONTROL: {control}
FAILED CHECK RESULT: {result}
API DOCUMENTATION:
{api_doc}

Return: {{"method": "PATCH", "path": "/api/security", "body": {{...}}, "rationale": "<one sentence, {lang}>"}}"""
