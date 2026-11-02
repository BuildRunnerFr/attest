"""Initiation de virements SEPA via le prestataire de paiement (PSP)."""
import logging

import requests

from .config import PSP_URL, TIMEOUT_S

log = logging.getLogger("paiement")


def initiate_transfer(debtor_iban: str, creditor_iban: str, amount_cents: int, reference: str) -> dict:
    payload = {
        "debtor": {"iban": debtor_iban},
        "creditor": {"iban": creditor_iban},
        "amount": {"value": amount_cents, "currency": "EUR"},
        "reference": reference,
    }
    response = requests.post(PSP_URL, json=payload, timeout=TIMEOUT_S, verify=False)
    response.raise_for_status()
    log.info("virement initié ref=%s", reference)
    return response.json()
