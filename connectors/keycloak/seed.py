"""Charge les royaumes fictifs dans un Keycloak de test et crée le compte d'audit en lecture seule.

  KC_URL=http://127.0.0.1:8081 KC_ADMIN_USER=… KC_ADMIN_PASSWORD=… KC_AUDIT_SECRET=… python -m connectors.keycloak.seed

- Chaque scénario de `scenarios/` devient un royaume (supprimé puis recréé : ne jamais viser un Keycloak réel).
- Le compte d'audit est le client `attest-audit` du royaume `master` (compte de service). Il ne reçoit, pour
  chaque royaume audité, que les rôles `view-realm` et `view-users` : il ne peut rien modifier (HTTP 403).
- Les « MFA » des comptes sont des secrets TOTP synthétiques, sans valeur : personne ne se connecte avec.
"""
import json
import os
import sys

import requests

from . import scenarios

AUDIT_CLIENT = "attest-audit"
READ_ROLES = ("view-realm", "view-users")


def _otp(i: int) -> dict:
    return {"type": "otp", "userLabel": "synthetic",
            "secretData": json.dumps({"value": f"SYNTHETIC{i:08d}"}),
            "credentialData": json.dumps({"subType": "totp", "digits": 6, "counter": 0, "period": 30,
                                          "algorithm": "HmacSHA1"})}


def realm_representation(sc: dict) -> dict:
    users = [{"username": u["login"], "email": u["email"], "firstName": u["first"], "lastName": u["last"],
              "enabled": True, "realmRoles": [scenarios.ADMIN_ROLE] if u["role"] == "admin" else [],
              "credentials": [_otp(i)] if u["totp"] else []} for i, u in enumerate(sc["users"])]
    return {"realm": sc["realm"], "enabled": True, "displayName": sc["entity"], **sc["settings"],
            "roles": {"realm": [{"name": scenarios.ADMIN_ROLE, "description": "Administrateurs du système"}]},
            "users": users}


class Admin:
    def __init__(self, url: str, user: str, password: str):
        self.url = url.rstrip("/")
        r = requests.post(f"{self.url}/realms/master/protocol/openid-connect/token", timeout=30,
                          data={"grant_type": "password", "client_id": "admin-cli", "username": user,
                                "password": password})
        if r.status_code != 200:
            sys.exit(f"Keycloak refuse le compte d'administration (HTTP {r.status_code}) : vérifier KC_ADMIN_USER "
                     "et KC_ADMIN_PASSWORD (le compte d'amorçage n'est créé qu'au premier démarrage)")
        self.h = {"Authorization": "Bearer " + r.json()["access_token"]}

    def call(self, method: str, path: str, **k):
        r = requests.request(method, f"{self.url}/admin/realms{path}", headers=self.h, timeout=120, **k)
        if r.status_code >= 400 and not (method == "DELETE" and r.status_code == 404):
            sys.exit(f"Keycloak {method} {path} → HTTP {r.status_code} {r.text[:200]}")
        return r


def seed(url: str, user: str, password: str, audit_secret: str, only: list | None = None) -> list:
    kc = Admin(url, user, password)
    done = []
    for sc in scenarios.load():
        if only and sc["id"] not in only:
            continue
        kc.call("DELETE", f"/{sc['realm']}")
        kc.call("POST", "", json=realm_representation(sc))
        done.append(sc["realm"])
    # compte d'audit : client confidentiel du royaume master, sans autre flux que client_credentials
    for c in kc.call("GET", "/master/clients", params={"clientId": AUDIT_CLIENT}).json():
        kc.call("DELETE", f"/master/clients/{c['id']}")
    kc.call("POST", "/master/clients", json={
        "clientId": AUDIT_CLIENT, "secret": audit_secret, "publicClient": False, "serviceAccountsEnabled": True,
        "standardFlowEnabled": False, "directAccessGrantsEnabled": False, "implicitFlowEnabled": False})
    sa = kc.call("GET", "/master/users", params={"username": f"service-account-{AUDIT_CLIENT}", "exact": "true"}).json()[0]
    for realm in done:
        c = kc.call("GET", "/master/clients", params={"clientId": f"{realm}-realm"}).json()[0]
        roles = [r for r in kc.call("GET", f"/master/clients/{c['id']}/roles").json() if r["name"] in READ_ROLES]
        kc.call("POST", f"/master/users/{sa['id']}/role-mappings/clients/{c['id']}", json=roles)
    return done


if __name__ == "__main__":
    env = os.environ
    missing = [k for k in ("KC_ADMIN_USER", "KC_ADMIN_PASSWORD", "KC_AUDIT_SECRET") if not env.get(k)]
    if missing:
        sys.exit("variables manquantes : " + ", ".join(missing))
    realms = seed(env.get("KC_URL", "http://127.0.0.1:8081"), env["KC_ADMIN_USER"], env["KC_ADMIN_PASSWORD"],
                  env["KC_AUDIT_SECRET"])
    print("royaumes chargés :", ", ".join(realms))
