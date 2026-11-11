"""Royaumes Keycloak FICTIFS à auditer + vérité terrain de la politique PSI-4 pour Keycloak.

Chaque scénario décrit un royaume (réglages de sécurité, comptes, rôle `admin`, MFA par compte) chargé dans un
vrai Keycloak par `connectors.keycloak.seed`. Tout est synthétique et généré par graine : banques, personnes,
adresses en `.example`. « expected » est calculé par l'oracle ci-dessous ; l'agent ne voit jamais ces étiquettes.

Régénérer les fichiers :  python -m connectors.keycloak.scenarios
"""
import json
import random
import re
from pathlib import Path

from lab.scenarios import (FIRST_XL, FUNCTION_NON_ADMINS, LAST_XL, NEAR_GENERIC_ADMINS, generic_admins)

DIR = Path(__file__).with_name("scenarios")
ADMIN_ROLE = "admin"
COMPLEX = "length({n}) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)"


# ---------- oracle : PSI-4 appliquée aux champs de Keycloak (référence de notation) ----------

def password_policy(policy: str | None) -> dict:
    """« length(12) and digits(1) » → {"length": 12, "digits": 1}."""
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"(\w+)\((\d+)\)", policy or "")}


def expected(settings: dict, users: list) -> dict:
    s, pol = settings, password_policy(settings.get("passwordPolicy"))
    ok = lambda b: "pass" if b else "fail"
    admins = [u for u in users if u["role"] == "admin"]
    others = [u for u in users if u["role"] != "admin"]
    complexity = all(pol.get(k, 0) >= 1 for k in ("upperCase", "lowerCase", "digits", "specialChars"))
    return {
        "PSI-4.1": ok(all(u["totp"] for u in admins)),
        "PSI-4.2": ok(all(u["totp"] for u in others)),
        "PSI-4.3": ok(pol.get("length", 0) >= 12 and complexity),
        "PSI-4.4": ok(s["bruteForceProtected"] is True and 1 <= s["failureFactor"] <= 5),
        "PSI-4.5": ok(1 <= s["ssoSessionIdleTimeout"] <= 900),
        "PSI-4.6": ok(s["adminEventsEnabled"] is True),
        "PSI-4.7": ok(not generic_admins(users)),
    }


# ---------- génération ----------

def _directory(rng, domain, n, admin_logins=(), totp=True):
    """n comptes nominatifs uniques ; `admin_logins` : (login, partie locale) imposés comme administrateurs."""
    used, out = set(), []
    for login, local in admin_logins:
        used.add(login)
        first, last = local.split(".", 1) if "." in local else (local, local)
        out.append({"login": login, "email": f"{local}@{domain}", "first": first.title(), "last": last.title(),
                    "role": "admin", "totp": totp})
    while len(out) < n:
        f, last = rng.choice(FIRST_XL), rng.choice(LAST_XL)
        login, local, k = f"{f[0]}.{last}", f"{f}.{last}", 2
        while login in used:
            login, local, k = f"{f[0]}.{last}{k}", f"{f}.{last}{k}", k + 1
        used.add(login)
        out.append({"login": login, "email": f"{local}@{domain}", "first": f.title(), "last": last.title(),
                    "role": "conseiller", "totp": totp})
    return out


def _function_account(login, domain, role, totp):
    return {"login": login, "email": f"{login}@{domain}", "first": "Compte", "last": login, "role": role, "totp": totp}


def build() -> list:
    out = []

    def add(sid, realm, label, entity, settings, users, tests):
        users = sorted(users, key=lambda u: u["login"])           # ordre de l'annuaire Keycloak
        out.append({"id": sid, "realm": realm, "label": label, "entity": entity,
                    "system": f"Keycloak — royaume {realm} (fournisseur d'identité)", "tests": tests,
                    "settings": settings, "users": users, "notes": [],
                    "expected": expected(settings, users), "expected_generic_admins": sorted(generic_admins(users)),
                    "expected_offenders": {
                        "PSI-4.1": sorted(u["login"] for u in users if u["role"] == "admin" and not u["totp"]),
                        "PSI-4.7": sorted(generic_admins(users))}})

    # 1. Tout est non conforme ; le seul administrateur générique est servi après la 2e page de 100 comptes.
    rng = random.Random(4101)
    d = "kerlann-banque.example"
    admins = [("a.abgrall", "adele.abgrall"), ("b.cariou", "bleuenn.cariou"), ("c.denis", "corentin.denis"),
              ("e.floch", "erwan.floch"), ("g.herve", "gwenael.herve"), ("j.kermarrec", "jeanne.kermarrec")]
    users = _directory(rng, d, 259, admins, totp=False) + [_function_account("support-n2", d, "admin", False)]
    add("kc-01-kerlann", "kerlann", "Royaume Keycloak non conforme, 260 comptes", "Banque Kerlann (fictive)",
        {"passwordPolicy": "length(8)", "bruteForceProtected": False, "failureFactor": 30,
         "ssoSessionIdleTimeout": 28800, "adminEventsEnabled": False},
        users, "7 non-conformités sur un vrai Keycloak ; l'administrateur générique « support-n2 » n'est pas dans "
               "les 100 premiers comptes (taille de page par défaut de Keycloak).")

    # 2. Jumeau conforme « presque fautif » : valeurs aux seuils, noms contenant un mot de fonction.
    rng = random.Random(4102)
    d = "credit-oceane.example"
    users = _directory(rng, d, 240, NEAR_GENERIC_ADMINS, totp=True) + \
        [_function_account(login, d, "conseiller", True) for login, _ in FUNCTION_NON_ADMINS]
    add("kc-02-oceane", "oceane", "Royaume Keycloak conforme, valeurs aux seuils", "Crédit Océane (fictif)",
        {"passwordPolicy": COMPLEX.format(n=12), "bruteForceProtected": True, "failureFactor": 5,
         "ssoSessionIdleTimeout": 900, "adminEventsEnabled": True},
        users, "Aucun constat attendu : seuils exacts (12, 5, 900 s), administrateurs nommés opsomer, teamson, "
               "rootsaert, comptes de fonction sans droits d'administration.")

    # 3. Cas mixte : un seul administrateur sans MFA (loin dans l'annuaire), longueur sans complexité, session longue.
    rng = random.Random(4103)
    d = "menhir-finance.example"
    admins = [("a.bihan", "armelle.bihan"), ("l.guivarch", "loic.guivarch"), ("m.pichon", "maiwenn.pichon"),
              ("y.tanguy", "yannick.tanguy")]
    users = _directory(rng, d, 180, admins, totp=True)
    next(u for u in users if u["login"] == "y.tanguy")["totp"] = False
    add("kc-03-menhir", "menhir", "Royaume Keycloak mixte, un administrateur sans MFA", "Menhir Finance (fictive)",
        {"passwordPolicy": "length(14)", "bruteForceProtected": True, "failureFactor": 3,
         "ssoSessionIdleTimeout": 1800, "adminEventsEnabled": True},
        users, "3 non-conformités : un administrateur sur quatre sans MFA (y.tanguy), mot de passe long mais sans "
               "complexité, session inactive de 30 minutes. Le reste est conforme.")
    return out


def load() -> list:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("*.json"))]


if __name__ == "__main__":
    DIR.mkdir(exist_ok=True)
    for sc in build():
        (DIR / f"{sc['id']}.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(sc["id"], len(sc["users"]), sc["expected"], sc["expected_generic_admins"])
