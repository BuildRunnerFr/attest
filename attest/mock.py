"""Réponses préenregistrées (ATTEST_BACKEND=mock) : même format que les vrais modèles.

Sert au développement, aux tests automatisés et à la CI. Les positions viennent du DOM avec un
léger bruit, pour que la mesure de masquage ne soit pas triviale.
"""
import json
import os
import random

import numpy as np

REFS = {
    "PSI-4.1": ["DORA 9(4)(d)", "RTS 21(1)(f)(ii)"], "PSI-4.2": ["DORA 9(4)(d)", "RTS 21(1)(f)(ii)"],
    "PSI-4.3": ["DORA 9(4)(d)"], "PSI-4.4": ["DORA 9(4)(c)"], "PSI-4.5": ["DORA 9(4)(c)"],
    "PSI-4.6": ["RTS 12(2)(c)(i)"], "PSI-4.7": ["DORA 9(4)(c)", "RTS 21(1)(c)", "RTS 21(3)"],
}

# id, règle, titre, objectif, attendu, criticité, page, champ (mock), remédiation, risque, recommandation
CONTROLS = [
    ("C1", "PSI-4.1", "MFA des comptes à privilèges", "Tout compte administrateur s'authentifie avec un second facteur.",
     "mfa_admin == true", "critique", "/admin/users", "mfa_admin", "config",
     "Un mot de passe administrateur volé suffit à prendre le contrôle de la console.",
     "Activer le MFA pour tous les comptes administrateurs."),
    ("C2", "PSI-4.2", "MFA des utilisateurs", "Les utilisateurs d'un système critique s'authentifient avec un second facteur.",
     "mfa_users == true", "elevee", "/admin/security", "mfa_users", "config",
     "Compromission de comptes conseillers par hameçonnage ou réutilisation de mots de passe.",
     "Activer le MFA pour les utilisateurs standards."),
    ("C3", "PSI-4.3", "Robustesse des mots de passe", "Mot de passe d'au moins 12 caractères, avec complexité.",
     "password_min_length >= 12 and password_require_complexity == true", "moyenne", "/admin/security",
     "password_min_length", "config", "Mots de passe devinables par force brute ou dictionnaire.",
     "Porter la longueur minimale à 12 et exiger la complexité."),
    ("C4", "PSI-4.4", "Verrouillage des comptes", "Verrouillage après 5 échecs au plus, jamais désactivé.",
     "1 <= lockout_threshold <= 5", "moyenne", "/admin/security", "lockout_threshold", "config",
     "Attaques par force brute en ligne sans limitation.", "Fixer le verrouillage à 5 échecs."),
    ("C5", "PSI-4.5", "Expiration des sessions", "Sessions inactives expirées après 15 minutes au plus.",
     "1 <= session_timeout_minutes <= 15", "moyenne", "/admin/security", "session_timeout_minutes", "config",
     "Session administrateur laissée ouverte réutilisable par un tiers.", "Fixer l'expiration à 15 minutes."),
    ("C6", "PSI-4.6", "Journalisation de l'administration", "Toutes les actions d'administration sont journalisées.",
     "admin_audit_log == true", "elevee", "/admin/security", "admin_audit_log", "config",
     "Actions d'administration non traçables en cas d'incident.", "Maintenir la journalisation activée."),
    ("C7", "PSI-4.7", "Comptes à privilèges nominatifs", "Aucun compte générique ou partagé n'a de droits d'administration.",
     "admins: login initiale.nom, e-mail personnel", "elevee", "/admin/users", "users", "manual",
     "Actions d'administration non imputables à une personne ; mot de passe partagé.",
     "Désactiver le compte partagé et créer des comptes nominatifs dédiés."),
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
    "C1": {"mfa_admin": True}, "C2": {"mfa_users": True},
    "C3": {"password_min_length": 12, "password_require_complexity": True},
    "C4": {"lockout_threshold": 5}, "C5": {"session_timeout_minutes": 15}, "C6": {"admin_audit_log": True},
}

_rng = random.Random(7)


def _jitter(box, px=6):
    return [int(v + _rng.randint(-px, px)) for v in box]


def _shift_ip(p: dict) -> list:
    box = _jitter(p["box"], 3)
    if p.get("kind") == "ipv4":
        box[0] += 40
    return box


def _code(cid: str) -> str:
    if cid == "C7":
        return """```python
import json, os, re, requests

H = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
users = requests.get(os.environ["LAB_URL"] + "/api/users", headers=H, timeout=10).json()
generic = [u["login"] for u in users if u["role"] == "admin" and (
    not re.fullmatch(r"[a-z]\\.[a-z]+", u["login"]) or re.search(r"partage|shared|ops|admin", u["email"].split("@")[0]))]
print(json.dumps({"status": "fail" if generic else "pass", "observed": {"generic_admin_accounts": generic},
                  "expected": "aucun compte administrateur générique ou partagé",
                  "detail": f"{len(generic)} compte(s) administrateur non nominatif(s)."}, ensure_ascii=False))
```"""
    cond, observed, expected = CHECKS[cid]
    return f"""```python
import json, os, requests

H = {{"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}}
s = requests.get(os.environ["LAB_URL"] + "/api/security", headers=H, timeout=10).json()
ok = {cond}
print(json.dumps({{"status": "pass" if ok else "fail", "observed": {observed},
                  "expected": {expected},
                  "detail": "Valeur lue via l'API d'administration (compte d'audit en lecture seule)."}},
                 ensure_ascii=False))
```"""


def answer(task: str, user: str, ctx: dict) -> str:
    if task == "plan":
        return json.dumps([
            {"id": i, "rule": r, "title": t, "objective": o, "expected": e, "severity": sev,
             "test_procedure": f"Lecture de la configuration via l'API en lecture seule et comparaison à {r}.",
             "references": REFS[r], "risk": risk, "recommendation": reco, "evidence_page": p,
             "remediation": rem, "_field": f}
            for i, r, t, o, e, sev, p, f, rem, risk, reco in CONTROLS], ensure_ascii=False)

    if task == "code":
        return _code(ctx["control"]["id"])

    if task == "inspect":
        dom, c, res = ctx["dom"], ctx["control"], ctx["result"]
        if c["id"] == "C7":
            boxes = [u["box"] for login, u in dom["users"].items() if login == "ops"]
            text = "Compte « ops » : rôle admin, adresse partagée"
        elif c["evidence_page"] == "/admin/users":
            boxes = [u["box"] for u in dom["users"].values() if u["role"] == "admin"]
            text = "Comptes admin a.lefloch et ops : MFA " + ("Oui" if res["status"] == "pass" else "Non")
        else:
            boxes = [dom["rows"][c.get("_field", "mfa_users")]]
            text = c["title"]
        return json.dumps({
            "corroborates": True, "field_text": text, "field_boxes": [_jitter(b) for b in boxes],
            "comment": f"Ligne « {text} » : valeur cohérente avec la lecture API.",
            # comme Muse Spark lors du premier audit réel : boîtes des IP décalées d'environ 40 px vers la droite
            "pii": [{"text": p["text"], "box": _shift_ip(p)} for p in dom["pii"]],
            "injection_detected": os.getenv("LAB_INJECTION") == "1" and c["evidence_page"] == "/admin/users",
        }, ensure_ascii=False)

    if task == "fix":
        c = ctx["control"]
        if c["id"] == "C7":
            return json.dumps({"type": "manual", "rationale": "Compte partagé : décision du propriétaire requise.",
                               "actions": ["Identifier les utilisateurs réels du compte « ops ».",
                                           "Créer des comptes administrateurs nominatifs avec MFA.",
                                           "Désactiver le compte « ops » et révoquer ses accès."]},
                              ensure_ascii=False)
        return json.dumps({"type": "config", "method": "PATCH", "path": "/api/security", "body": FIXES[c["id"]],
                           "rationale": f"Alignement minimal sur la règle {c['rule']}.",
                           "impact": "Les utilisateurs concernés devront s'adapter à la nouvelle règle à leur prochaine connexion."},
                          ensure_ascii=False)
    raise ValueError(task)


def sam_output(boxes, size) -> str:
    """Fabrique une sortie SAM au vrai format filaire (masques one_bit encodés en base85)."""
    from meta_sam_parser._mask_codec import _encode_raster

    W, H = size
    recs = []
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        mh, mw = max(4, (y2 - y1) // 4), max(4, (x2 - x1) // 4)
        m = np.zeros((mh, mw), dtype=np.uint8)
        m[1:mh - 1, 1:mw - 1] = 1
        payload = _encode_raster(bytes(m.flatten()), mw, mh)
        recs.append(f"{i + 1}<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={W};h={H};c=0.93|>"
                    f"<|mask;x=0;y=0;c=0.91;data={mh},{mw},{payload}|>")
    return "<0f>" + ",".join(recs)
