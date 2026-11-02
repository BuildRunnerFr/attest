"""Mission complète en mode mock contre la vraie console (Flask) : constat, remédiation, contre-vérification."""
import importlib
import json
import os
import threading

import pytest
from werkzeug.serving import make_server


@pytest.fixture()
def lab(tmp_path):
    os.environ["LAB_STATE_FILE"] = str(tmp_path / "state.json")
    import lab.app as labapp
    importlib.reload(labapp)
    srv = make_server("127.0.0.1", 0, labapp.app, threaded=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    os.environ["LAB_URL"] = f"http://127.0.0.1:{srv.server_port}"
    yield os.environ["LAB_URL"]
    srv.shutdown()


def test_full_engagement(lab, tmp_path):
    from attest import config, pipeline
    from attest.trail import verify
    mission = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")
    out = tmp_path / "run"
    state = pipeline.run(mission, out, remediate=True, approve_all=True, approver="Responsable IAM", fresh=True)

    entries = {e["control"]["rule"]: e for e in state["entries"]}
    assert len(entries) == 7
    assert entries["PSI-4.6"]["status_before"] == "pass"                 # journalisation déjà conforme
    assert entries["PSI-4.1"]["finding"]["severity"] == "critique"
    assert entries["PSI-4.1"]["finding"]["status"] == "closed"           # corrigé puis revérifié
    assert entries["PSI-4.7"]["finding"]["status"] == "action_plan"      # compte partagé : remédiation manuelle
    assert state["opinion_initial"] == "insuffisant" and state["opinion_final"] == "ameliorer"
    assert entries["PSI-4.1"]["change"]["journal"]["approved_by"] == "Responsable IAM"
    assert (out / "report.pdf").exists() and (out / "manifest.json").exists()
    assert verify(out)[0]

    # séparation des tâches : l'auditeur ne peut pas approuver ses propres changements
    with pytest.raises(SystemExit):
        pipeline.run(mission, tmp_path / "run2", remediate=True, approve_all=True,
                     approver=mission.lead_auditor, reset_lab=True)

    # un compte d'audit ne peut rien modifier sur le système audité
    import requests
    r = requests.patch(lab + "/api/security", json={"mfa_admin": False},
                       headers={"Authorization": f"Bearer {config.AUDIT_TOKEN}"})
    assert r.status_code == 403
    assert json.loads((out / "manifest.json").read_text())["trail_head"]
