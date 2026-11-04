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
    assert interpret.verify_quote("a provision on user accountability, by limiting [...] generic and shared user accounts;", t)
    # plusieurs coupures : on recompose une phrase qui n'existe pas
    assert not interpret.verify_quote("a provision on user accountability […] limiting to the extent possible […] "
                                      "generic and shared user accounts", t)
    # fragments trop courts (moins de 4 mots)
    assert not interpret.verify_quote("a provision on user accountability […] user accounts", t)
    # coupé en plein mot
    assert not interpret.verify_quote("imiting to the extent possible the use", t)
    assert not interpret.verify_quote("limiting to the extent possible the use of gen", t)


def test_quote_cut_cannot_drop_a_negation():
    t = "To that end, financial entities shall not store passwords in clear text."
    assert not interpret.verify_quote("Financial entities shall […] store passwords in clear text", t)
    assert not interpret.verify_quote("to that end, financial entities shall […] store passwords in clear text", t)
    assert interpret.verify_quote("to that end, financial entities shall not store passwords in clear text", t)
    fr = "Le mot de passe n'est en aucun cas transmis en clair sur le réseau, sauf exception documentée."
    assert not interpret.verify_quote("le mot de passe […] en aucun cas transmis en clair sur le réseau", fr)
    assert interpret.verify_quote("le mot de passe n'est en aucun cas […] en clair sur le réseau", fr)


def test_quote_verified_document_by_document():
    texts = [("A", "Article 1: the management body shall approve the ICT risk framework."),
             ("B", "Article 2: financial entities shall test the plan at least yearly.")]
    assert interpret.verify_quote_in("the management body shall approve […] financial entities shall test the plan", texts) is False
    assert interpret.verify_quote_in("approve the ICT risk framework. Article 2: financial entities", texts) is False
    assert interpret.verify_quote_in("=== B === Article 2: financial entities shall test", texts) is False   # en-tête
    assert interpret.verify_quote_in("financial entities shall test […] plan at least yearly", texts) is True


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


def _prepared(c, lang="fr"):
    r = c.post("/interpret", data={"lang": lang, "lib": ["politique-psi-4-acces"], "target": "iam-console"})
    return r.location.split("/review/")[1].split("?")[0]


def test_studio_single_pipeline_per_folder(tmp_path, monkeypatch):
    """Double clic sur « Lancer l'audit » : un seul pipeline, la piste scellée n'a qu'un auteur."""
    import threading
    from attest import studio
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    monkeypatch.setattr(studio, "JOBS", {})
    started, gate = [], threading.Event()

    def fake_job(sid, *a):
        started.append(sid)
        gate.wait(10)
        studio.JOBS[sid] = {"state": "done"}
    monkeypatch.setattr(studio, "job", fake_job)
    c = studio.app.test_client()
    sid = _prepared(c)
    form = {"reviewer": "A. Auditeur", "ctrl": ["C1"]}
    r1, r2 = c.post(f"/run/{sid}", data=form), c.post(f"/run/{sid}", data=form)
    assert r1.status_code == r2.status_code == 302 and r2.location.endswith(f"/audit/{sid}")
    # Pendant l'audit, pas de nouvelle interprétation (elle remettrait le compteur de coût à zéro)
    busy = c.post("/interpret", data={"lang": "en", "lib": ["politique-psi-4-acces"], "target": "iam-console"})
    assert busy.status_code == 409 and "An audit is running" in busy.get_data(as_text=True)
    gate.set()
    for _ in range(50):
        if studio.JOBS[sid]["state"] == "done":
            break
        time.sleep(0.05)
    (tmp_path / "studio" / sid / "audit").mkdir()
    studio.JOBS.clear()                                  # redémarrage du Studio : le dossier audit/ suffit
    c.post(f"/run/{sid}", data=form)
    assert started == [sid]


def test_studio_requires_reviewer_and_known_target(tmp_path, monkeypatch):
    from attest import studio
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    monkeypatch.setattr(studio, "JOBS", {})
    c = studio.app.test_client()
    sid = _prepared(c, "en")
    page = c.post(f"/run/{sid}", data={"reviewer": "  ", "ctrl": ["C1"]})
    assert page.status_code == 200 and "Enter your name" in page.get_data(as_text=True)
    assert sid not in studio.JOBS
    r = c.post("/interpret", data={"lang": "fr", "lib": ["politique-psi-4-acces"], "target": "../../etc"})
    assert r.status_code == 400 and "Cible inconnue" in r.get_data(as_text=True)


def test_studio_sans_operateur_n_est_pas_une_relecture(lab, tmp_path, monkeypatch):
    """ops/studio_flow.py (CI) n'est pas un auditeur : le programme reste « non relu » dans le catalogue."""
    import json
    from attest import studio
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    monkeypatch.setattr(studio, "job", lambda *a: None)
    c = studio.app.test_client()
    r = c.post("/interpret", data={"lang": "en", "lib": ["politique-psi-4-acces"], "target": "iam-console"})
    sid = r.location.split("/review/")[1].split("?")[0]
    it = json.loads((tmp_path / "studio" / sid / "interpretation.json").read_text())
    ctrl = [k["id"] for q in it["requirements"] if q["quote_verified"] for k in q["controls"]][:1]
    c.post(f"/run/{sid}", data={"reviewer": "Attest CI", "ctrl": ctrl, "unattended": "1"})
    cat = json.loads((tmp_path / "studio" / sid / "catalogue.json").read_text())
    assert cat["reviewed"] is False and cat["reviewer"] is None
    studio.JOBS.clear()
