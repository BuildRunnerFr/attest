"""python -m attest exigences/dora_authentification.md [--lab http://127.0.0.1:5050] [--no-fix]"""
import argparse
import time
from pathlib import Path

from . import pipeline


def main():
    ap = argparse.ArgumentParser(prog="attest")
    ap.add_argument("requirement", type=Path)
    ap.add_argument("--lab", default="http://127.0.0.1:5050")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-fix", action="store_true", help="constater sans corriger")
    ap.add_argument("--no-reset", action="store_true", help="ne pas remettre la console dans l'état initial")
    a = ap.parse_args()
    out = a.out or Path("runs") / time.strftime("%Y%m%d-%H%M%S")
    pipeline.run(a.requirement, a.lab.rstrip("/"), out, auto_fix=not a.no_fix, reset=not a.no_reset)


if __name__ == "__main__":
    main()
