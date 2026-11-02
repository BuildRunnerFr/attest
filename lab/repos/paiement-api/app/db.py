"""Accès aux opérateurs back-office (bouchon de démonstration)."""

_OPERATORS = {
    "y.morvan": {"password_hash": "5f4dcc3b5aa765d61d8327deb882cf99", "role": "operateur"},
}


def get_operator(username: str):
    return _OPERATORS.get(username)
