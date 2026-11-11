"""Cibles d'audit : ce que l'agent peut tester, et par quelle interface en lecture seule.

Chaque cible est exposée par une passerelle HTTP en lecture seule (la console de démo `lab/`) : l'agent n'a
jamais d'accès direct au système ni au système de fichiers. Ajouter une cible = décrire son interface.
"""
from . import config

TARGETS = {
    "iam-console": {
        "kind": "app",
        "label": {"fr": "Console d'administration IAM KRL-ADM (Banque Kerlann)",
                  "en": "KRL-ADM IAM admin console (Banque Kerlann)"},
        "system": "KRL-ADM — console d'administration IAM",
        "owner": "DSI — équipe IAM",
        "system_en": "KRL-ADM — IAM administration console",
        "owner_en": "IT department — IAM team",
        "doc": "lab/API.md",
        "default_page": "/admin/security",
        "probe": "/api/security",
        "remediable": True,                  # correctifs de paramètres via le compte de changement
    },
    "repo:paiement-api": {
        "kind": "code",
        "label": {"fr": "Dépôt de code paiement-api (microservice de virements SEPA)",
                  "en": "paiement-api code repository (SEPA transfer microservice)"},
        "system": "paiement-api — microservice de virements SEPA",
        "owner": "DSI — équipe de développement Paiements",
        "system_en": "paiement-api — SEPA transfer microservice",
        "owner_en": "IT department — Payments development team",
        "doc": "lab/REPO_API.md",
        "repo": "paiement-api",
        "default_page": "/repo/paiement-api/view?path=README.md",
        "probe": "/api/repos",
        "remediable": False,                 # le code est corrigé par l'équipe de développement
    },
    "iam-lifecycle": {
        "kind": "app",
        "label": {"fr": "Registre RH ↔ habilitations (départs, mutations, droits incompatibles)",
                  "en": "HR register ↔ entitlements (leavers, movers, conflicting rights)"},
        "system": "Registre RH et habilitations applicatives",
        "owner": "DSI — équipe IAM ; DRH pour le registre",
        "system_en": "HR register and application entitlements",
        "owner_en": "IT department — IAM team; HR for the register",
        "doc": "lab/LIFECYCLE_API.md",
        "default_page": "/lifecycle/accounts",
        "probe": "/api/lifecycle/meta",
        "remediable": False,                 # retraits de droits et désactivations : décision des propriétaires
    },
    "keycloak": {
        "kind": "app",
        "label": {"fr": "Keycloak (fournisseur d'identité open source), via la passerelle en lecture seule",
                  "en": "Keycloak (open-source identity provider), through the read-only gateway"},
        "system": "Keycloak — fournisseur d'identité",
        "owner": "DSI — équipe IAM",
        "system_en": "Keycloak — identity provider",
        "owner_en": "IT department — IAM team",
        "doc": "connectors/keycloak/API.md",
        "default_page": "/kc/realm",
        "probe": "/api/kc/realm",            # route qui prouve que cette cible est servie à LAB_URL
        "remediable": False,                 # la passerelle n'a aucune route d'écriture
    },
}


def get(target_id: str) -> dict:
    if target_id not in TARGETS:
        raise SystemExit(f"Cible inconnue : {target_id}. Cibles : {', '.join(TARGETS)}")
    return TARGETS[target_id]


def api_doc(target_id: str) -> str:
    t = get(target_id)
    text = (config.ROOT / t["doc"]).read_text()
    return text.replace("{repo}", t.get("repo", ""))


def label(target_id: str) -> str:
    return get(target_id)["label"][config.lang()]


def text(target_id: str, key: str, lang: str | None = None) -> str:
    """Champ d'une cible dans la langue du rapport (`key_en`), sinon le champ de base."""
    t = get(target_id)
    return t.get(f"{key}_{lang or config.lang()}", t[key])


def available(lab_url: str, token: str) -> dict:
    """Cibles réellement servies à cette adresse (leur route témoin répond au compte d'audit).
    Si rien ne répond (console arrêtée), toutes les cibles sont rendues : l'erreur viendra du contrôle préalable."""
    import requests
    ok = {}
    for tid, t in TARGETS.items():
        try:
            r = requests.get(lab_url + t["probe"], timeout=3, headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 200:
                ok[tid] = t
        except requests.RequestException:
            pass
    return ok or dict(TARGETS)
