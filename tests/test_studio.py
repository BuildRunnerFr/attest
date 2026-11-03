"""Interprétation ancrée et Attest Studio (mode mock) : du texte choisi au rapport d'audit."""
import time

from attest import config, interpret

LIB = config.ROOT / "exigences" / "library"


def _texts(*stems):
    return [((LIB / f"{s}.md").read_text().splitlines()[0], (LIB / f"{s}.md").read_text()) for s in stems]


def test_quote_verification():
    t = "(c) a provision on user accountability, by limiting to the extent possible the use of generic and shared user accounts;"
    assert interpret.verify_quote("limiting to the extent possible the use of generic and shared user accounts", t)
    assert interpret.verify_quote("a provision on user accountability […] generic and shared user accounts", t)
    assert not interpret.verify_quote("limit generic accounts as much as possible", t)          # paraphrase refusée
    assert not interpret.verify_quote("user accounts", t)                                        # trop court


def test_policy_gives_thresholds_regulation_alone_gives_proposals():
    with_policy = interpret.interpret(_texts("rts-16-developpement", "politique-pds-2-developpement"), "repo:paiement-api")
    assert with_policy["counts"]["controls"] == 7 and with_policy["counts"]["rejected"] == 1
    assert with_policy["counts"]["automated"] == 10                    # 7 règles + 3 clauses rattachées
    sources = {c["threshold_source"] for r in with_policy["requirements"] for c in r["controls"]}
    assert all(s.startswith("PDS-2.") for s in sources)
    alone = interpret.interpret(_texts("dora-9-4-acces-changements", "rts-21-controle-acces"), "iam-console")
    sources = [c["threshold_source"] for r in alone["requirements"] for c in r["controls"]]
    assert any("proposal" in s for s in sources)                       # seuil absent du texte : proposition
    assert alone["counts"]["interview"] >= 1 and alone["counts"]["document"] >= 1


def test_studio_end_to_end(lab, tmp_path, monkeypatch):
    from attest import studio
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    c = studio.app.test_client()
    assert c.get("/?lang=en").status_code == 200
    r = c.post("/interpret", data={"lang": "fr", "lib": ["rts-16-developpement", "politique-pds-2-developpement"],
                                    "target": "repo:paiement-api"})
    assert r.status_code == 302 and "/review/" in r.location
    sid = r.location.split("/review/")[1].split("?")[0]
    page = c.get(f"/review/{sid}").get_data(as_text=True)
    assert "citation vérifiée" in page and "citation introuvable" in page
    r = c.post(f"/run/{sid}", data={"reviewer": "A. Auditeur", "ctrl": ["C1", "C2", "C3"]})
    assert r.status_code == 302
    for _ in range(120):
        st = c.get(f"/status/{sid}").get_json()
        if st["state"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert st["state"] == "done", st
    report = (tmp_path / "studio" / sid / "audit" / "report.html").read_text()
    assert "Couverture du référentiel" in report and "PDS-2.1" in report and "A. Auditeur" in report


def test_studio_refuses_self_approval(lab, tmp_path, monkeypatch):
    from attest import studio
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    c = studio.app.test_client()
    r = c.post("/interpret", data={"lang": "fr", "lib": ["politique-psi-4-acces"], "target": "iam-console"})
    sid = r.location.split("/review/")[1].split("?")[0]
    page = c.post(f"/run/{sid}", data={"reviewer": "Alex", "approver": "alex", "remediate": "on", "ctrl": ["C1"]})
    assert "doit être différent" in page.get_data(as_text=True)


def test_regulation_clauses_covered_by_policy_controls():
    r = interpret.interpret(_texts("rts-16-developpement", "politique-pds-2-developpement"), "repo:paiement-api")
    cov = {x["quote"][:40]: x["covered_by"] for x in r["requirements"] if x["covered_by"]}
    assert r["counts"]["covered"] == 3 and ["PDS-2.4"] in cov.values()
    assert all(x["covered_by"] == [] for x in r["requirements"] if x["controls"])      # pas de doublon


def test_missing_evidence_is_reported_not_hidden(lab, tmp_path, monkeypatch):
    """Une capture qui échoue ne disparaît pas : le rapport le dit et la piste d'audit le trace."""
    from attest import evidence, pipeline
    real = evidence.capture

    def flaky(url, out, token):
        if "users" in url:
            raise RuntimeError("navigateur indisponible")
        return real(url, out, token)
    monkeypatch.setattr(evidence, "capture", flaky)
    mission = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")
    state = pipeline.run(mission, tmp_path / "run", reset_lab=True)
    broken = [e for e in state["entries"] if e.get("evidence_error")]
    assert broken and all(e["status_before"] in ("pass", "fail") for e in broken)
    html = (tmp_path / "run" / "report.html").read_text()
    assert "Preuve visuelle indisponible" in html and "sans preuve visuelle" in html
    assert "evidence_failed" in (tmp_path / "run" / "trail.jsonl").read_text()
