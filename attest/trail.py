"""Piste d'audit infalsifiable (tamper-evident).

Chaque événement est une ligne JSON qui contient l'empreinte SHA-256 de l'événement précédent :
modifier, supprimer ou réordonner une ligne casse la chaîne. Les fichiers de preuve sont
référencés par leur empreinte. `python -m attest verify <dossier>` revérifie tout.
(Esprit du RTS 2024/1774 art. 12(2)(d) : protéger les journaux contre l'altération.)
"""
import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _digest(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()


class Trail:
    def __init__(self, path: Path):
        self.path = path
        self.head = GENESIS
        self.seq = 0
        self._lock = threading.Lock()

    def log(self, event: str, **data) -> str:
        data = json.loads(json.dumps(data, default=str, ensure_ascii=False))   # JSON pur, hachable
        with self._lock:
            self.seq += 1
            body = {"seq": self.seq, "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    "event": event, "data": data, "prev": self.head}
            body["hash"] = _digest(self.head, body)
            with open(self.path, "a") as f:
                f.write(json.dumps(body, ensure_ascii=False, default=str) + "\n")
            self.head = body["hash"]
            return self.head


def verify(run_dir: Path) -> tuple[bool, list[str]]:
    """Revérifie la chaîne d'événements et l'empreinte de chaque fichier cité."""
    problems, prev = [], GENESIS
    trail = run_dir / "trail.jsonl"
    if not trail.exists():
        return False, ["trail.jsonl absent"]
    for n, line in enumerate(trail.read_text().splitlines(), 1):
        body = json.loads(line)
        claimed = body.pop("hash")
        if body["prev"] != prev:
            problems.append(f"ligne {n} : chaînage rompu")
        if _digest(body["prev"], body) != claimed:
            problems.append(f"ligne {n} : contenu modifié")
        prev = claimed
        f = body["data"].get("file")
        if f and body["data"].get("sha256"):
            p = run_dir / f
            if not p.exists():
                problems.append(f"{f} : fichier manquant")
            elif sha256_file(p) != body["data"]["sha256"]:
                problems.append(f"{f} : fichier modifié après coup")
    manifest = run_dir / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        if m.get("trail_head") != prev:
            problems.append("manifest.json ne correspond pas à la fin de la piste")
        for f in m.get("files", []):
            p = run_dir / f["path"]
            if not p.exists():
                problems.append(f"{f['path']} : fichier manquant")
            elif sha256_file(p) != f["sha256"]:
                problems.append(f"{f['path']} : fichier modifié après émission")
    else:
        problems.append("manifest.json absent")
    return not problems, problems
