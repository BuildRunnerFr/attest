"""Intégrité des verdicts et de l'opinion (mode mock) : verdict sans requête à la cible, clôture sans
approbation humaine valable, fondement de l'opinion, échec immédiat sur un backend mal configuré."""
import hashlib
import html
import json
from pathlib import Path

import pytest
import requests

from attest import sandbox
from attest.i18n import L

ROOT = Path(__file__).resolve().parent.parent
GET_SECURITY = ('import json, os, requests\n'
                'H = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}\n'
                's = requests.get(os.environ["LAB_URL"] + "/api/security", headers=H, timeout=10).json()\n'
                'print(json.dumps({"status": "pass", "observed": s.get("mfa_admin"), "expected": True, "detail": "ok"}))')


def _mission():
    from attest import config
    return config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")


# ---------- 1. verdict sans requête à la cible ----------

@pytest.mark.parametrize("status", ["pass", "fail"])
def test_verdict_without_request_is_error(lab, status):
    code = f'import json\nprint(json.dumps({{"status": "{status}", "observed": 1, "expected": 1, "detail": "deviné"}}))'
    res = sandbox.run(code, lab, "audit-ro-demo")
    assert res["status"] == "error"
    assert L["fr"]["sb.norequest"] in res["detail"] and res["requests"]["count"] == 0


def test_request_log_recorded_and_not_forgeable(lab):
    forged = GET_SECURITY.replace('"detail": "ok"', '"detail": "ok", "requests": {"count": 99, "log": []}')
    res = sandbox.run(forged, lab, "audit-ro-demo")
    assert res["status"] == "pass", res
    assert res["requests"]["count"] == 1                             # le journal du runner fait foi
    entry = res["requests"]["log"][0]
    body = requests.get(lab + "/api/security", headers={"Authorization": "Bearer audit-ro-demo"}).content
    assert entry == {"method": "GET", "path": "/api/security", "status": 200,
                     "sha256": hashlib.sha256(body).hexdigest()}


def test_unreachable_target_gives_no_verdict():
    code = ('import json, requests\ntry:\n    requests.get("http://127.0.0.1:9/api", timeout=2)\nexcept Exception:\n'
            '    pass\nprint(json.dumps({"status": "fail", "observed": "KO", "expected": 1}))')
    assert sandbox.run(code, "http://127.0.0.1:9", "t")["status"] == "error"


@pytest.mark.parametrize("path", sorted((ROOT / "library").glob("*.py")), ids=lambda p: p.name)
def test_library_scripts_query_the_target(lab, path):
    res = sandbox.run(path.read_text(), lab, "audit-ro-demo")
    assert res["status"] in ("pass", "fail"), res
    assert res["requests"]["count"] >= 1


def test_request_log_in_trail(lab, tmp_path):
    from attest import pipeline
    out = tmp_path / "run"
    pipeline.run(_mission(), out, fresh=True, reset_lab=True)
    ev = [json.loads(line) for line in (out / "trail.jsonl").open()]
    tests = [x["data"] for x in ev if x["event"] == "test_executed"]
    assert tests and all(x["requests"]["count"] >= 1 for x in tests)
    assert all("requests" not in x["result"] for x in tests)        # hors du résultat montré au modèle


# ---------- 2. clôture et approbation humaine ----------

def test_preapproved_fix_is_not_closed(lab, tmp_path):
    from attest import pipeline
    out = tmp_path / "run"
    state = pipeline.run(_mission(), out, remediate=True, approve_all=True, approver="Responsable IAM",
                         fresh=True, reset_lab=True)
    fixed = [e for e in state["entries"] if e.get("status_after") == "pass"]
    assert fixed and all(e["finding"]["status"] == "retested_unapproved" for e in fixed)
    assert not any(e.get("finding", {}).get("status") == "closed" for e in state["entries"])
    assert state["opinion_final"] == state["opinion_initial"] == "insuffisant"   # toujours pris en compte
    page = (out / "report.html").read_text()
    assert html.escape(L["fr"]["fs.retested_unapproved"]) in page
    assert html.escape("risque d'autorévision") in page


def test_interactive_approval_closes(lab, tmp_path, monkeypatch):
    from attest import pipeline

    class Tty:
        def isatty(self):
            return True
    monkeypatch.setattr(pipeline.sys, "stdin", Tty())
    monkeypatch.setattr("builtins.input", lambda *a: "o")
    state = pipeline.run(_mission(), tmp_path / "run", remediate=True, approver="Responsable IAM",
                         fresh=True, reset_lab=True)
    assert all(d["mode"] == "interactive" and d["approved"] for d in state["decisions"])
    fixed = [e for e in state["entries"] if e.get("status_after") == "pass"]
    assert fixed and all(e["finding"]["status"] == "closed" for e in fixed)
    assert state["opinion_final"] == "ameliorer"


# ---------- 3. fondement de l'opinion ----------

def test_basis_for_opinion_and_signoff(lab, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTEST_LANG", "en")
    from attest import pipeline
    out = tmp_path / "run"
    state = pipeline.run(_mission(), out, fresh=True, reset_lab=True)
    page = (out / "report.html").read_text()
    assert "Basis for opinion" in page
    assert f"{len(state['entries'])} controls tested" in page and state["mission"]["environment"] in page
    assert ("Work programme and test scripts drafted by AI and not yet reviewed by an auditor; requirements "
            "needing document review or interview are not covered; the opinion applies at the test date only.") in page
    assert "Prepared by: <b>Attest (AI-assisted)</b>" in page and "Auditor sign-off: <b>pending</b>" in page


def test_i18n_keys_in_both_languages():
    for k in ("sb.norequest", "fs.retested_unapproved", "basis.title", "basis.text", "basis.scope", "basis.scope_all",
              "basis.scope_scripts", "signoff.label", "pre.nokey", "pre.backend", "msg.retested", "k.retested"):
        assert L["fr"][k] and L["en"][k] and L["fr"][k] != L["en"][k]
    assert len(L["fr"]["limits"]) == len(L["en"]["limits"])


# ---------- 4. échec immédiat ----------

def test_meta_without_key_fails_before_trail(lab, tmp_path, monkeypatch):
    from attest import llm, pipeline
    monkeypatch.setattr(llm, "BACKEND", "meta")
    for v in (None, "", "   "):
        if v is None:
            monkeypatch.delenv("MODEL_API_KEY", raising=False)
        else:
            monkeypatch.setenv("MODEL_API_KEY", v)
        with pytest.raises(SystemExit, match="MODEL_API_KEY"):
            pipeline.run(_mission(), tmp_path / "run", fresh=True)
        assert not (tmp_path / "run" / "trail.jsonl").exists()


def test_meta_with_key_passes_check_without_showing_it(monkeypatch, capsys):
    from attest import llm
    monkeypatch.setattr(llm, "BACKEND", "meta")
    monkeypatch.setenv("MODEL_API_KEY", "sk-FAKE-not-a-real-key-123")
    llm.check_backend()
    assert "sk-FAKE" not in capsys.readouterr().out


def test_unknown_backend_rejected(monkeypatch):
    from attest import llm
    monkeypatch.setattr(llm, "BACKEND", "metaa")
    with pytest.raises(SystemExit, match="metaa"):
        llm.check_backend()
