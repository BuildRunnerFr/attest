"""Masquage des secrets dans tout ce qui sort d'Attest (résultats de scripts, piste d'audit).

Règle (simple, assumée) :
- toute variable d'environnement dont le nom contient KEY, TOKEN, SECRET ou PASSWORD (ex. MODEL_API_KEY,
  LAB_AUDIT_TOKEN, LAB_CHANGE_TOKEN) et dont la valeur fait au moins 8 caractères est masquée là où sa
  valeur exacte apparaît — SAUF les valeurs de démonstration publiques (DEMO_VALUES, défauts de
  config.py) : elles ne sont pas secrètes et restent lisibles dans la piste ;
- les motifs de clés usuels sont masqués quelle que soit leur origine : sk-…, ghp_…/github_pat_…,
  « Bearer <jeton> », « api_key=<valeur> ».
"""
import os
import re

MASK = "[secret masqué]"
DEMO_VALUES = {"audit-ro-demo", "change-rw-demo"}          # défauts publics de config.py
_SENSITIVE = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD", re.I)
_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(?<=\bbearer )[A-Za-z0-9_\-.=+/]{8,}"),
    re.compile(r"(?i)(?<=api_key=)[^\s&\"',;]{8,}|(?<=api-key=)[^\s&\"',;]{8,}"),
]


def _secrets() -> list[str]:
    vals = {v for k, v in os.environ.items() if _SENSITIVE.search(k) and len(v) >= 8 and v not in DEMO_VALUES}
    return sorted(vals, key=len, reverse=True)                # le plus long d'abord


def _text(s: str, secrets: list[str]) -> str:
    for v in secrets:
        s = s.replace(v, MASK)
    for p in _PATTERNS:
        s = p.sub(lambda m: m.group(0) if m.group(0) in DEMO_VALUES else MASK, s)
    return s


def scrub(obj, _secrets_cache=None):
    """Copie de obj (str/dict/list/tuple, récursif) où les secrets sont remplacés par MASK."""
    sec = _secrets() if _secrets_cache is None else _secrets_cache
    if isinstance(obj, str):
        return _text(obj, sec)
    if isinstance(obj, dict):
        return {(_text(k, sec) if isinstance(k, str) else k): scrub(v, sec) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(scrub(v, sec) for v in obj)
    return obj
