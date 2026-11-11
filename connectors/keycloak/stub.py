"""Faux Keycloak minimal pour les tests sans Java ni Docker : les quelques routes de l'API d'administration que la
passerelle appelle, servies depuis les scénarios, avec les mêmes formes de réponse et la même taille de page
par défaut (100) qu'un vrai Keycloak 26. Il ne sert qu'aux tests : les mesures viennent d'un Keycloak réel."""
from flask import Flask, abort, jsonify, request

from . import scenarios


def make_app(audit_secret: str = "stub-secret") -> Flask:
    app = Flask("keycloak-stub")
    realms = {s["realm"]: s for s in scenarios.load()}
    token = "stub-access-token"

    def realm(name):
        if request.headers.get("Authorization") != f"Bearer {token}":
            abort(401)
        if name not in realms:
            abort(404)
        return realms[name]

    def user(i, u):
        return {"id": f"00000000-0000-4000-8000-{i:012d}", "username": u["login"], "email": u["email"],
                "firstName": u["first"], "lastName": u["last"], "enabled": True, "emailVerified": False,
                "totp": u["totp"], "requiredActions": [], "notBefore": 0, "disableableCredentialTypes": [],
                "access": {"manage": False, "view": True}}

    def page(rows):
        first, size = int(request.args.get("first", 0)), int(request.args.get("max", 100))
        return jsonify(rows[first:first + size])

    @app.post("/realms/master/protocol/openid-connect/token")
    def issue():
        if request.form.get("client_secret") != audit_secret or request.form.get("grant_type") != "client_credentials":
            abort(401)
        return jsonify(access_token=token, expires_in=60)

    @app.get("/admin/realms/<name>")
    def get_realm(name):
        sc = realm(name)
        return jsonify({"realm": name, "enabled": True, "smtpServer": {"password": "**********"},
                        "permanentLockout": False, "eventsEnabled": False, **sc["settings"]})

    @app.get("/admin/realms/<name>/users")
    def users(name):
        return page([user(i, u) for i, u in enumerate(realm(name)["users"])])

    @app.get("/admin/realms/<name>/users/count")
    def count(name):
        return jsonify(len(realm(name)["users"]))

    @app.get("/admin/realms/<name>/roles")
    def roles(name):
        realm(name)
        return jsonify([{"name": n} for n in (scenarios.ADMIN_ROLE, "offline_access", "uma_authorization")])

    @app.get("/admin/realms/<name>/roles/<role>/users")
    def role_users(name, role):
        sc = realm(name)
        if role != scenarios.ADMIN_ROLE:
            return jsonify([])
        return page([user(i, u) for i, u in enumerate(sc["users"]) if u["role"] == "admin"])

    @app.route("/admin/realms/<path:rest>", methods=["POST", "PUT", "PATCH", "DELETE"])
    def write(rest):
        abort(403)

    return app
