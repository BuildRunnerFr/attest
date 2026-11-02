"""Authentification des opérateurs back-office."""
import hashlib

from .db import get_operator


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def login(username: str, password: str) -> bool:
    operator = get_operator(username)
    if operator is None:
        return False
    return operator["password_hash"] == hash_password(password)
