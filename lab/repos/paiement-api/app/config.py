"""Configuration du service."""
import os

PSP_URL = os.getenv("PSP_URL", "https://psp.kerlann-banque.example/v1/transfers")
DB_URL = "postgresql://paiement@db.kerlann-banque.example:5432/paiement"
DB_PASSWORD = "Azerty123!"  # TODO : déplacer dans le coffre-fort
JWT_SECRET = "kerlann-dev-secret-2026"
TIMEOUT_S = 10
