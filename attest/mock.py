"""Réponses préenregistrées pour faire tourner le pipeline sans clé d'API (ATTEST_BACKEND=mock).

Elles imitent ce que les vrais modèles doivent renvoyer. Les positions viennent du DOM, avec un
léger bruit pour que la mesure de précision ne soit pas triviale.
"""
import json
import random

import numpy as np

CONTROLS = [
    ("C1", "PSI-4.1", "MFA pour les administrateurs", "Tout compte administrateur doit utiliser le MFA.",
     "mfa_admin == true", "/admin/users", "mfa_admin", lambda v: v["mfa_admin"] is True),
    ("C2", "PSI-4.2", "MFA pour les utilisateurs", "Les utilisateurs accédant aux données clients utilisent le MFA.",
     "mfa_users == true", "/admin/security", "mfa_users", lambda v: v["mfa_users"] is True),
    ("C3", "PSI-4.3", "Robustesse des mots de passe", "Mot de passe d'au moins 12 caractères, avec complexité.",
     "password_min_length >= 12 and password_require_complexity == true", "/admin/security",
     "password_min_length", None),
    ("C4", "PSI-4.4", "Verrouillage des comptes", "Verrouillage après 5 échecs au plus.",
     "1 <= lockout_threshold <= 5", "/admin/security", "lockout_threshold", None),
    ("C5", "PSI-4.5", "Expiration des sessions", "Sessions inactives expirées après 15 minutes au plus.",
     "1 <= session_timeout_minutes <= 15", "/admin/security", "session_timeout_minutes", None),
    ("C6", "PSI-4.6", "Journalisation administrateur", "Toutes les actions d'administration sont journalisées.",
     "admin_audit_log == true", "/admin/security", "admin_audit_log", None),
]

CHECKS = {
    "C1": ("s['mfa_admin'] is True", "{'mfa_admin': s['mfa_admin']}", "'mfa_admin = true'"),
    "C2": ("s['mfa_users'] is True", "{'mfa_users': s['mfa_users']}", "'mfa_users = true'"),
    "C3": ("s['password_min_length'] >= 12 and s['password_require_complexity'] is True",
           "{'password_min_length': s['password_min_length'], 'password_require_complexity': s['password_require_complexity']}",
           "'longueur >= 12 et complexité exigée'"),
    "C4": ("1 <= s['lockout_threshold'] <= 5", "{'lockout_threshold': s['lockout_threshold']}", "'entre 1 et 5'"),
    "C5": ("1 <= s['session_timeout_minutes'] <= 15", "{'session_timeout_minutes': s['session_timeout_minutes']}",
           "'entre 1 et 15 minutes'"),
    "C6": ("s['admin_audit_log'] is True", "{'admin_audit_log': s['admin_audit_log']}", "'admin_audit_log = true'"),
}

FIXES = {
    "C1": {"mfa_admin": True},
    "C2": {"mfa_users": True},
    "C3": {"password_min_length": 12, "password_require_complexity": True},
    "C4": {"lockout_threshold": 5},
    "C5": {"session_timeout_minutes": 15},
    "C6": {"admin_audit_log": True},
}

_rng = random.Random(7)


def _jitter(box, px=6):
    return [int(v + _rng.randint(-px, px)) for v in box]


def answer(task: str, user: str, ctx: dict) -> str:
    if task == "plan":
        return json.dumps([
            {"id": i, "rule": r, "title": t, "objective": o, "expected": e, "evidence_page": p, "_field": f}
            for i, r, t, o, e, p, f, _ in CONTROLS], ensure_ascii=False)

    if task == "code":
        cid = ctx["control"]["id"]
        cond, observed, expected = CHECKS[cid]
        return f"""```python
import json, os, requests

s = requests.get(os.environ["LAB_URL"] + "/api/security", timeout=10).json()
ok = {cond}
print(json.dumps({{"status": "pass" if ok else "fail", "observed": {observed},
                  "expected": {expected},
                  "detail": "Valeur lue via l'API de la console."}}, ensure_ascii=False))
```"""

    if task == "inspect":
        dom, c, res = ctx["dom"], ctx["control"], ctx["result"]
        if c["evidence_page"] == "/admin/users":
            boxes = [u["box"] for u in dom["users"].values() if u["role"] == "admin"]
            text = "Comptes admin a.lefloch et ops : MFA " + ("Oui" if res["status"] == "pass" else "Non")
        else:
            boxes = [dom["rows"][c.get("_field", "mfa_users")]]
            text = c["title"]
        return json.dumps({
            "corroborates": True, "field_text": text, "field_boxes": [_jitter(b) for b in boxes],
            "comment": f"Ligne « {text} » : valeur cohérente avec la lecture API.",
            "pii": [{"text": p["text"], "box": _jitter(p["box"], 3)} for p in dom["pii"]],
        }, ensure_ascii=False)

    if task == "fix":
        cid = ctx["control"]["id"]
        return json.dumps({"method": "PATCH", "path": "/api/security", "body": FIXES[cid],
                           "rationale": f"Alignement minimal sur la règle {ctx['control']['rule']}."},
                          ensure_ascii=False)
    raise ValueError(task)


def sam_output(boxes, size) -> str:
    """Fabrique une sortie SAM au vrai format filaire (masques one_bit encodés en base85)."""
    from meta_sam_parser._mask_codec import _encode_raster

    W, H = size
    recs = []
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        # SAM « resserre » la boîte : masque local à résolution réduite, bords rognés
        mh, mw = max(4, (y2 - y1) // 4), max(4, (x2 - x1) // 4)
        m = np.zeros((mh, mw), dtype=np.uint8)
        m[1:mh - 1, 1:mw - 1] = 1
        payload = _encode_raster(bytes(m.flatten()), mw, mh)
        recs.append(f"{i + 1}<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={W};h={H};c=0.93|>"
                    f"<|mask;x=0;y=0;c=0.91;data={mh},{mw},{payload}|>")
    return "<0f>" + ",".join(recs)
