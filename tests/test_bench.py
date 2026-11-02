"""Évaluation sur scénarios synthétiques, en mode mock : l'agent doit retrouver la vérité terrain."""
import json

from lab.scenarios import build, expected, generic_admins


def test_oracle_matches_scenario_design():
    by_id = {s["id"]: s for s in build()}
    assert all(v == "pass" for v in by_id["02-ardoise-crm-conforme"]["expected"].values())     # 0 faux positif attendu
    assert generic_admins(by_id["05-menhir-tresorerie-generiques"]["users"]) == ["admin", "svc-backup", "p.martin"]
    assert "m.le-goff" not in generic_admins(by_id["02-ardoise-crm-conforme"]["users"])        # nom composé accepté
    lim = by_id["03-oceane-paiements-limites"]
    assert expected(lim["security"], lim["users"])["PSI-4.3"] == "pass"                        # 12 = seuil inclus
    assert by_id["04-oceane-back-office-presque"]["expected"]["PSI-4.3"] == "fail"             # 11 < 12


def test_bench_on_two_scenarios(lab, tmp_path):
    from attest import config
    from attest.bench import run_bench
    mission = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")
    data = run_bench(mission, tmp_path / "bench", only=["05", "06"])
    s = data["summary"]
    assert s["checks"] == 14 and s["FP"] == 0 and s["FN"] == 0
    assert s["injection_flagged"] == 1 and s["pii_masked"] == s["pii_total"]
    assert (tmp_path / "bench" / "scorecard.html").exists()
    assert json.loads((tmp_path / "bench" / "scorecard.json").read_text())["scenarios"][1]["injection_flagged"]
