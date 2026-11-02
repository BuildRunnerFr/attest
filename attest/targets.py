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
        "doc": "lab/API.md",
        "default_page": "/admin/security",
        "remediable": True,                  # correctifs de paramètres via le compte de changement
    },
    "repo:paiement-api": {
        "kind": "code",
        "label": {"fr": "Dépôt de code paiement-api (microservice de virements SEPA)",
                  "en": "paiement-api code repository (SEPA transfer microservice)"},
        "system": "paiement-api — microservice de virements SEPA",
        "owner": "DSI — équipe de développement Paiements",
        "doc": "lab/REPO_API.md",
        "repo": "paiement-api",
        "default_page": "/repo/paiement-api/view?path=README.md",
        "remediable": False,                 # le code est corrigé par l'équipe de développement
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
