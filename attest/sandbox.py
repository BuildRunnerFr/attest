"""Exécution des scripts de contrôle écrits par le modèle.

Garde-fous (vérifiés statiquement AVANT exécution) :
- imports limités à une liste blanche ;
- aucune requête qui modifie l'environnement (POST/PUT/PATCH/DELETE) : un contrôle est en lecture seule ;
- pas d'exec/eval/compile/__import__, pas d'écriture de fichier.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

ALLOWED_IMPORTS = {"requests", "json", "os", "sys", "re"}
FORBIDDEN_CALLS = {"exec", "eval", "compile", "__import__", "open", "input"}
WRITE_METHODS = {"post", "put", "patch", "delete", "request"}


class UnsafeCode(Exception):
    pass


def check(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for n in names:
                if n.split(".")[0] not in ALLOWED_IMPORTS:
                    raise UnsafeCode(f"import interdit : {n}")
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in FORBIDDEN_CALLS:
                raise UnsafeCode(f"appel interdit : {f.id}()")
            if isinstance(f, ast.Attribute) and f.attr in WRITE_METHODS:
                raise UnsafeCode(f"méthode HTTP en écriture interdite : .{f.attr}()")
            if isinstance(f, ast.Attribute) and f.attr in {"system", "popen", "remove", "unlink", "rmtree"}:
                raise UnsafeCode(f"appel interdit : .{f.attr}()")


def run(code: str, lab_url: str, token: str, timeout: int = 30) -> dict:
    """Exécute le script ; il doit imprimer en dernière ligne un JSON {status, observed, expected, detail}."""
    check(code)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "check.py")
        with open(path, "w") as f:
            f.write(code)
        env = {"LAB_URL": lab_url, "LAB_TOKEN": token, "PATH": os.environ.get("PATH", ""),
               "NO_PROXY": "127.0.0.1,localhost"}
        p = subprocess.run([sys.executable, "-I", path], capture_output=True, text=True,
                           timeout=timeout, cwd=d, env=env)
    lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
    if p.returncode != 0 or not lines:
        return {"status": "error", "detail": (p.stderr or p.stdout)[-800:]}
    try:
        res = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"status": "error", "detail": f"sortie non JSON : {lines[-1][:300]}"}
    if res.get("status") not in ("pass", "fail"):
        return {"status": "error", "detail": f"statut invalide : {res}"}
    return res
