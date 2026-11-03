"""Robustesse (mode mock) : une panne du modèle ne fait pas tomber l'audit, et un échec fatal laisse un dossier vérifiable."""
import json

import pytest


def _mission():
    from attest import config
    return config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")


def _flaky(monkeypatch, task_name, cid, behaviour):
    """llm.ask perturbé pour un seul contrôle (cid) et une seule tâche."""
    from attest import llm
    real = llm.ask

    def ask(task, system, user, **kw):
        c = (kw.get("mock_ctx") or {}).get("control") or {}
        if task == task_name and c.get("id") == cid:
            return behaviour()
        return real(task, system, user, **kw)
    monkeypatch.setattr(llm, "ask", ask)


def test_model_failure_on_one_control_is_inconclusive(lab, tmp_path, monkeypatch):
    from attest import pipeline
    from attest.trail import verify

    def boom():
        raise TimeoutError("simulé : délai de lecture de l'API dépassé")
    _flaky(monkeypatch, "code", "C3", boom)
    out = tmp_path / "run"
    state = pipeline.run(_mission(), out, fresh=True, reset_lab=True)
    entries = {e["control"]["id"]: e for e in state["entries"]}
    assert entries["C3"]["status_before"] == "error" and "TimeoutError" in entries["C3"]["before"]["detail"]
    assert not entries["C3"].get("finding")
    assert all(e.get("status_before") for e in state["entries"])          # les autres contrôles ont abouti
    assert not state.get("aborted") and not state["running"]
    assert (out / "manifest.json").exists() and (out / "result.json").exists()
    assert verify(out)[0]
    assert "Audit en cours" not in (out / "report.html").read_text()


def test_inconclusive_never_counts_as_compliant():
    from attest.pipeline import opinion
    assert opinion([], inconclusive=1) == "reserve"
    assert opinion(["moyenne"], inconclusive=2) == "reserve"
    assert opinion(["critique"], inconclusive=1) == "insuffisant"


def test_malformed_fix_json_falls_back_to_action_plan(lab, tmp_path, monkeypatch):
    from attest import pipeline
    from attest.trail import verify
    _flaky(monkeypatch, "fix", "C1", lambda: "Sure! Here is the fix: {method: PATCH, path: /api/security")
    out = tmp_path / "run"
    state = pipeline.run(_mission(), out, remediate=True, approve_all=True, approver="Responsable IAM",
                         fresh=True, reset_lab=True)
    c1 = next(e for e in state["entries"] if e["control"]["id"] == "C1")
    assert c1["change"]["type"] == "manual" and c1["finding"]["status"] == "action_plan"
    assert verify(out)[0]


def test_fatal_error_writes_aborted_outputs(lab, tmp_path, monkeypatch):
    from attest import llm, pipeline
    from attest.trail import verify

    def broke(*a, **k):
        raise llm.BudgetExceeded("plafond de dépense atteint (simulé)")
    monkeypatch.setattr(pipeline, "raise_findings", broke)
    out = tmp_path / "run"
    with pytest.raises(llm.BudgetExceeded):
        pipeline.run(_mission(), out, fresh=True, reset_lab=True)
    res = json.loads((out / "result.json").read_text())
    assert "BudgetExceeded" in res["aborted"] and res["running"] is False
    assert "BudgetExceeded" in json.loads((out / "manifest.json").read_text())["aborted"]
    assert any(json.loads(line)["event"] == "engagement_aborted" for line in (out / "trail.jsonl").open())
    page = (out / "report.html").read_text()
    assert "Audit interrompu" in page and 'http-equiv="refresh"' not in page
    assert verify(out)[0]


def test_preapproved_is_not_a_human_approval(lab, tmp_path):
    from attest import pipeline
    out = tmp_path / "run"
    state = pipeline.run(_mission(), out, remediate=True, approve_all=True, approver="Responsable IAM",
                         fresh=True, reset_lab=True)
    pre = sum(1 for d in state["decisions"] if d["mode"] == "pre-approved")
    assert pre and not any(d["mode"] == "interactive" for d in state["decisions"])
    page = (out / "report.html").read_text()
    assert f'<b>0</b><span>approbations humaines · {pre} pré-approuvées (démo)</span>' in page
    assert "pré-approuvé (démo, non valable comme approbation)" in page
