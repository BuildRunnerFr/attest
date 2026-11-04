"""Attest : agent d'audit de conformité qui teste au lieu de lire."""
import sys

if sys.version_info < (3, 11):  # tomllib (config) et la syntaxe utilisée exigent Python 3.11+
    raise SystemExit(f"Attest requires Python 3.11+ (found {sys.version.split()[0]}).")
