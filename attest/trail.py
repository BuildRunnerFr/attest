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

from .redact import scrub

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
        data = scrub(json.loads(json.dumps(data, default=str, ensure_ascii=False)))   # JSON pur, hachable, sans secret
        with self._lock:
            self.seq += 1
            body = {"seq": self.seq, "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    "event": event, "data": data, "prev": self.head}
            body["hash"] = _digest(self.head, body)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(body, ensure_ascii=False, default=str) + "\n")
            self.head = body["hash"]
            return self.head


def verify(run_dir: Path, lang: str = "fr") -> tuple[bool, list[str]]:
    """Revérifie la chaîne d'événements et l'empreinte de chaque fichier cité.

    Une ligne illisible (JSON invalide, champs manquants) est signalée comme altération,
    jamais propagée en exception. `lang` (fr|en) : langue des messages ; français par défaut
    (API historique), la ligne de commande passe la langue courante (config.lang())."""
    from .i18n import L

    def t(key: str) -> str:
        return L.get(lang, L["fr"]).get(key, L["fr"][key])
    problems, prev = [], GENESIS
    trail = run_dir / "trail.jsonl"
    if not trail.exists():
        return False, [t("verify.no_trail")]
    try:
        lines = trail.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False, [t("verify.trail_unreadable")]
    for n, line in enumerate(lines, 1):
        try:
            body = json.loads(line)
            claimed = body.pop("hash")
            body_prev = body["prev"]
            data = body.get("data") or {}
            if not isinstance(claimed, str) or not isinstance(body_prev, str) or not isinstance(data, dict):
                raise TypeError
            digest = _digest(body_prev, body)
        except (ValueError, TypeError, KeyError, AttributeError):
            problems.append(t("verify.line_unreadable").format(n=n))
            continue                             # la ligne suivante signalera le chaînage rompu
        if body_prev != prev:
            problems.append(t("verify.chain_broken").format(n=n))
        if digest != claimed:
            problems.append(t("verify.line_modified").format(n=n))
        prev = claimed
        f = data.get("file")
        if f and data.get("sha256"):
            p = run_dir / str(f)
            if not p.exists():
                problems.append(t("verify.file_missing").format(f=f))
            elif sha256_file(p) != data["sha256"]:
                problems.append(t("verify.file_modified").format(f=f))
    manifest = run_dir / "manifest.json"
    if manifest.exists():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            files = m.get("files", [])
            if not isinstance(files, list):
                raise TypeError
        except (OSError, ValueError, TypeError, AttributeError):
            problems.append(t("verify.manifest_unreadable"))
            return not problems, problems
        if m.get("trail_head") != prev:
            problems.append(t("verify.manifest_head"))
        for f in files:
            try:
                path, digest = str(f["path"]), f["sha256"]
            except (TypeError, KeyError):
                problems.append(t("verify.manifest_unreadable"))
                continue
            p = run_dir / path
            if not p.exists():
                problems.append(t("verify.file_missing").format(f=path))
            elif sha256_file(p) != digest:
                problems.append(t("verify.file_issued_modified").format(f=path))
    else:
        problems.append(t("verify.no_manifest"))
    return not problems, problems
