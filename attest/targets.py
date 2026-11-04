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


def text(target_id: str, key: str, lang: str | None = None) -> str:
    """Champ d'une cible dans la langue du rapport (`key_en`), sinon le champ de base."""
    t = get(target_id)
    return t.get(f"{key}_{lang or config.lang()}", t[key])
