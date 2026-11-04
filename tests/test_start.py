"""Lanceur scripts/start.sh et résolution de l'URL de la console : un juré qui clone doit pouvoir lancer la démo."""
import os
import shutil
import subprocess

from attest import config

ROOT = config.ROOT


def _check(tmp_path, env_file=None, **env):
    """Copie minimale du dépôt (sans .env) puis `start.sh --check` : rien n'est lancé."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "start.sh", tmp_path / "scripts" / "start.sh")
    shutil.copy(ROOT / ".env.example", tmp_path / ".env.example")
    if env_file is not None:
        (tmp_path / ".env").write_text(env_file)
    base = {k: v for k, v in os.environ.items()
            if k not in ("ATTEST_BACKEND", "MODEL_API_KEY", "LAB_PORT", "LAB_URL", "STUDIO_PORT")}
    r = subprocess.run(["bash", str(tmp_path / "scripts" / "start.sh"), "--check"], capture_output=True, text=True,
                       env={**base, **env}, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    out = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line and " " not in line.split("=")[0])
    return out, r.stdout


def test_start_without_env_falls_back_to_mock(tmp_path):
    out, text = _check(tmp_path)
    assert (tmp_path / ".env").exists()                          # copié depuis .env.example
    assert out["ATTEST_BACKEND"] == "mock" and "mode mock" in text   # pas de clé : mock, avec avertissement
    assert out["LAB_URL"] == "http://127.0.0.1:5050"


def test_start_shell_variables_win_over_env(tmp_path):
    out, text = _check(tmp_path, "ATTEST_BACKEND=meta\nMODEL_API_KEY=\nLAB_PORT=5050\n",
                       ATTEST_BACKEND="mock", LAB_PORT="5977", STUDIO_PORT="8977")
    assert out["ATTEST_BACKEND"] == "mock" and "Avertissement" not in text
    assert out["LAB_URL"] == "http://127.0.0.1:5977" and out["STUDIO_URL"] == "http://127.0.0.1:8977"


def test_start_never_prints_the_key(tmp_path):
    out, text = _check(tmp_path, "ATTEST_BACKEND=meta\nMODEL_API_KEY=sk-test-synthetique-123\n")
    assert out["ATTEST_BACKEND"] == "meta" and "sk-test" not in text


def test_mission_lab_url_follows_env(monkeypatch):
    path = ROOT / "mission" / "kerlann-iam.toml"
    monkeypatch.delenv("LAB_URL", raising=False)
    monkeypatch.delenv("LAB_PORT", raising=False)
    assert config.load_mission(path).lab_url == "http://127.0.0.1:5050"
    monkeypatch.setenv("LAB_PORT", "5977")
    assert config.load_mission(path).lab_url == "http://127.0.0.1:5977"
    monkeypatch.setenv("LAB_URL", "http://127.0.0.1:6001/")
    assert config.load_mission(path).lab_url == "http://127.0.0.1:6001"


def test_mission_fields_localized(monkeypatch):
    path = ROOT / "mission" / "kerlann-iam.toml"
    monkeypatch.setenv("ATTEST_LANG", "en")
    m = config.load_mission(path)
    assert m.system == "KRL-ADM — IAM administration console" and "fictitious" in m.entity
    assert m.scope_in[0].startswith("Authentication") and m.owner.startswith("IT department")
    monkeypatch.setenv("ATTEST_LANG", "fr")
    m = config.load_mission(path)
    assert m.system == "KRL-ADM — console d'administration IAM" and m.scope_out[-1] == "Contrôles physiques"
