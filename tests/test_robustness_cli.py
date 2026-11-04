"""Robustesse : catalogue renvoyé par le LLM, `python -m attest verify`, encodage UTF-8 hors locale."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from attest import catalog, llm
from attest.trail import Trail, sha256_file, verify

ROOT = Path(__file__).resolve().parent.parent


# ---------- catalog.normalize ----------

def test_normalize_accepts_wrapped_form():
    out = catalog.normalize(llm.extract_json('{"controls":[{}]}'))
    assert len(out) == 1 and out[0]["id"] == "C1" and out[0]["severity"] == "moyenne"


def test_normalize_plain_list_unchanged():
    ctl = [{"id": "AC-1", "title": " Comptes ", "severity": "High", "references": "DORA 9(4)"}]
    out = catalog.normalize(ctl)
    assert out[0]["id"] == "AC-1" and out[0]["title"] == "Comptes"
    assert out[0]["severity"] == "elevee" and out[0]["references"] == ["DORA 9(4)"]
    assert catalog.normalize({"controls": ctl}) == out


@pytest.mark.parametrize("bad", [[1], ["texte"], [{"id": "C1"}, None], [[("id", "C1")]]])
def test_normalize_rejects_non_object(bad):
    with pytest.raises(ValueError, match="n'est pas un objet"):
        catalog.normalize(bad)


@pytest.mark.parametrize("bad", [{"items": []}, "texte", 42])
def test_normalize_rejects_non_list(bad):
    with pytest.raises(ValueError, match="catalogue invalide"):
        catalog.normalize(bad)


def test_normalize_unique_ids_deterministic(caplog):
    ctl = [{"id": "C1"}, {"id": "C1"}, {}, {"id": "C1"}, {"id": ""}]
    with caplog.at_level("WARNING", logger="attest.catalog"):
        ids = [c["id"] for c in catalog.normalize(ctl)]
    assert ids == ["C1", "C1-2", "C3", "C1-3", "C5"]
    assert len(set(ids)) == len(ids)
    assert ids == [c["id"] for c in catalog.normalize(ctl)]          # même entrée, mêmes identifiants
    assert "en double" in caplog.text


def test_normalize_generated_id_collision():
    ids = [c["id"] for c in catalog.normalize([{"id": "C2"}, {}])]
    assert ids == ["C2", "C2-2"]


# ---------- verify ----------

def _run(tmp_path: Path) -> Path:
    (tmp_path / "preuve.png").write_bytes(b"preuve")
    tr = Trail(tmp_path / "trail.jsonl")
    tr.log("evidence_sealed", file="preuve.png", sha256=sha256_file(tmp_path / "preuve.png"), note="écrit")
    tr.log("report_issued")
    (tmp_path / "manifest.json").write_text(json.dumps({"trail_head": tr.head, "files": []}), encoding="utf-8")
    return tmp_path


def _cli(run_dir, lang=None, locale_c=False):
    env = {**os.environ}
    env.pop("ATTEST_LANG", None)
    if lang:
        env["ATTEST_LANG"] = lang
    if locale_c:
        env.update(LC_ALL="C", LANG="C")
        env.pop("PYTHONUTF8", None)
    return subprocess.run([sys.executable, "-m", "attest", "verify", str(run_dir)], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=60)


def test_verify_garbage_line_is_tampering(tmp_path):
    run = _run(tmp_path)
    with open(run / "trail.jsonl", "a", encoding="utf-8") as f:
        f.write("x{\n")
    ok, problems = verify(run)
    assert not ok and "ligne 3 : illisible" in problems


@pytest.mark.parametrize("line", ["[]", "{}", '{"hash": "x"}', '{"hash": 1, "prev": "0"}', "null"])
def test_verify_malformed_json_line(tmp_path, line):
    run = _run(tmp_path)
    lines = (run / "trail.jsonl").read_text(encoding="utf-8").splitlines()
    lines.insert(1, line)
    (run / "trail.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, problems = verify(run)
    assert not ok and problems == ["ligne 2 : illisible"]              # ligne insérée : signalée, sans trace


def test_verify_messages_language(tmp_path, monkeypatch):
    run = _run(tmp_path)
    (run / "preuve.png").write_bytes(b"falsifiee")
    monkeypatch.setenv("ATTEST_LANG", "en")                # l'API reste en français par défaut
    assert verify(run)[1] == ["preuve.png : fichier modifié après coup"]
    assert verify(run, lang="en")[1] == ["preuve.png: file modified afterwards"]


def test_verify_unreadable_manifest(tmp_path):
    run = _run(tmp_path)
    (run / "manifest.json").write_text("{pas du json", encoding="utf-8")
    ok, problems = verify(run)
    assert not ok and problems == ["manifest.json illisible"]


def test_cli_verify_ok_fr_en(tmp_path):
    run = _run(tmp_path)
    r = _cli(run)
    assert r.returncode == 0 and "Intégrité vérifiée" in r.stdout
    r = _cli(run, lang="en")
    assert r.returncode == 0 and "Integrity verified" in r.stdout


def test_cli_verify_garbage_fr_en(tmp_path):
    run = _run(tmp_path)
    with open(run / "trail.jsonl", "a", encoding="utf-8") as f:
        f.write("x{\n")
    r = _cli(run)
    assert r.returncode == 1 and "ALTÉRATION DÉTECTÉE" in r.stdout and "ligne 3 : illisible" in r.stdout
    assert "Traceback" not in r.stderr and "JSONDecodeError" not in r.stderr
    r = _cli(run, lang="en")
    assert r.returncode == 1 and "TAMPERING DETECTED" in r.stdout and "line 3: unreadable" in r.stdout
    assert "Traceback" not in r.stderr


def test_cli_verify_missing_dir(tmp_path):
    r = _cli(tmp_path / "absent")
    assert r.returncode == 1 and "ALTÉRATION DÉTECTÉE" in r.stdout and "Traceback" not in r.stderr


def test_cli_verify_c_locale(tmp_path):
    run = _run(tmp_path)
    r = _cli(run, locale_c=True)
    assert r.returncode == 0 and "Intégrité vérifiée" in r.stdout, r.stderr
    (run / "preuve.png").write_bytes(b"falsifiee")
    r = _cli(run, locale_c=True)
    assert r.returncode == 1 and "preuve.png : fichier modifié après coup" in r.stdout, r.stderr
