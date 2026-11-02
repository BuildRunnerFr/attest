"""Infra jouet : la console d'administration d'une banque FICTIVE (Banque Kerlann).

Elle démarre volontairement non conforme, pour que l'agent ait quelque chose à trouver.
Lancer :  python -m lab.app   (port 5050)
"""
import copy
import json
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
STATE_FILE = Path(__file__).with_name("state.json")

DEFAULT_STATE = {
    "security": {
        "mfa_admin": False,             # MFA pour les comptes administrateurs
        "mfa_users": False,             # MFA pour les utilisateurs standards
        "password_min_length": 6,
        "password_require_complexity": False,
        "lockout_threshold": 0,         # 0 = jamais de verrouillage
        "session_timeout_minutes": 0,   # 0 = la session n'expire jamais
        "admin_audit_log": True,
    },
    "users": [
        {"login": "a.lefloch", "email": "anne.lefloch@kerlann-banque.example", "role": "admin",
         "last_ip": "10.12.4.31", "mfa": False},
        {"login": "ops", "email": "ops-partage@kerlann-banque.example", "role": "admin",
         "last_ip": "10.12.4.77", "mfa": False},
        {"login": "y.morvan", "email": "yann.morvan@kerlann-banque.example", "role": "conseiller",
         "last_ip": "10.12.9.5", "mfa": False},
        {"login": "m.quere", "email": "maela.quere@kerlann-banque.example", "role": "conseiller",
         "last_ip": "10.12.9.18", "mfa": False},
    ],
}

LABELS = {
    "mfa_admin": "Authentification multifacteur (administrateurs)",
    "mfa_users": "Authentification multifacteur (utilisateurs)",
    "password_min_length": "Longueur minimale du mot de passe",
    "password_require_complexity": "Complexité du mot de passe exigée",
    "lockout_threshold": "Verrouillage après N échecs de connexion",
    "session_timeout_minutes": "Expiration de session inactive (minutes)",
    "admin_audit_log": "Journalisation des actions d'administration",
}


def load():
    if not STATE_FILE.exists():
        save(copy.deepcopy(DEFAULT_STATE))
    return json.loads(STATE_FILE.read_text())


def save(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def fmt(key, value):
    if isinstance(value, bool):
        return ("Activée" if value else "Désactivée"), value
    if key in ("lockout_threshold", "session_timeout_minutes") and value == 0:
        return ("Jamais" if key == "session_timeout_minutes" else "Aucun"), False
    return str(value), None


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>{{title}} · Banque Kerlann</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f4f5f7;color:#1d2330}
 header{background:#0f2747;color:#fff;padding:14px 28px;display:flex;gap:28px;align-items:center}
 header b{font-size:18px} header a{color:#c9d6ea;text-decoration:none;font-size:14px}
 main{padding:28px;max-width:980px}
 h1{font-size:22px;margin:0 0 4px} p.sub{color:#5b6475;margin:0 0 22px;font-size:14px}
 table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px #0002}
 td,th{padding:14px 18px;border-bottom:1px solid #e6e8ec;font-size:15px;text-align:left}
 th{background:#eef1f5;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#5b6475}
 .v{font-weight:600} .ok{color:#137333} .ko{color:#b3261e}
 .note{margin-top:18px;font-size:12px;color:#8a92a3}
</style></head><body>
<header><b>Banque Kerlann · Console d'administration</b>
<a href="/admin/security">Sécurité</a><a href="/admin/users">Utilisateurs</a></header>
<main><h1>{{title}}</h1><p class="sub">{{sub}}</p>{{body|safe}}
<p class="note">Environnement de démonstration — entreprise et données fictives.</p></main></body></html>"""


@app.get("/admin/security")
def security_page():
    s = load()["security"]
    rows = []
    for key, label in LABELS.items():
        text, good = fmt(key, s[key])
        cls = "ok" if good is True else "ko" if good is False else ""
        rows.append(f'<tr id="row-{key}"><td>{label}</td><td class="v {cls}">{text}</td></tr>')
    body = "<table><tr><th>Paramètre</th><th>Valeur</th></tr>" + "".join(rows) + "</table>"
    return render_template_string(PAGE, title="Politique de sécurité",
                                  sub="Paramètres d'authentification et de session", body=body)


@app.get("/admin/users")
def users_page():
    users = load()["users"]
    rows = "".join(
        f"<tr id=\"user-{u['login']}\" data-role=\"{u['role']}\"><td>{u['login']}</td><td>{u['email']}</td><td>{u['role']}</td>"
        f"<td>{u['last_ip']}</td><td class='v {'ok' if u['mfa'] else 'ko'}'>{'Oui' if u['mfa'] else 'Non'}</td></tr>"
        for u in users)
    body = ("<table><tr><th>Identifiant</th><th>E-mail</th><th>Rôle</th><th>Dernière IP</th><th>MFA</th></tr>"
            + rows + "</table>")
    return render_template_string(PAGE, title="Comptes utilisateurs",
                                  sub="Comptes ayant accès à la console", body=body)


@app.get("/api/security")
def get_security():
    return jsonify(load()["security"])


@app.patch("/api/security")
def patch_security():
    state = load()
    patch = request.get_json(force=True) or {}
    unknown = set(patch) - set(state["security"])
    if unknown:
        return jsonify(error=f"champs inconnus : {sorted(unknown)}"), 400
    state["security"].update(patch)
    if "mfa_admin" in patch or "mfa_users" in patch:
        for u in state["users"]:
            u["mfa"] = state["security"]["mfa_admin"] if u["role"] == "admin" else state["security"]["mfa_users"]
    save(state)
    return jsonify(state["security"])


@app.get("/api/users")
def get_users():
    return jsonify(load()["users"])


@app.post("/api/reset")
def reset():
    save(copy.deepcopy(DEFAULT_STATE))
    return jsonify(ok=True)


if __name__ == "__main__":
    load()
    app.run(port=5050, debug=False)
