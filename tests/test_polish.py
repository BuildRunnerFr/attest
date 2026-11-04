"""Finitions bilingues : ponctuation du terminal, identifiant d'exécution, rapport « code » sans remédiation, Studio."""
import re
import time

from attest import config, pipeline, report


def _iam_run(tmp_path, monkeypatch, lang="en", **kw):
    monkeypatch.setenv("ATTEST_LANG", lang)
    mission = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")
    out = tmp_path / "run"
    state = pipeline.run(mission, out, remediate=True, approve_all=True, approver="IAM owner", fresh=True, **kw)
    return state, out


def test_colon_follows_language(monkeypatch):
    monkeypatch.setenv("ATTEST_LANG", "en")
    assert report.colon() == ": "
    monkeypatch.setenv("ATTEST_LANG", "fr")
    assert report.colon() == " : "


def test_terminal_english_colon_and_run_id_from_env(lab, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATTEST_RUN_ID", "gh-123456")
    state, out = _iam_run(tmp_path, monkeypatch)
    logs = capsys.readouterr().out
    assert "Work programme: " in logs and "Report: " in logs
    assert "Work programme :" not in logs and "Report :" not in logs
    assert state["run_id"] == "gh-123456"
    html = (out / "report.html").read_text()
    assert "gh-123456" in html
    # IAM avec remédiation : colonne « After » et limite sur les correctifs conservées
    assert "<th>After</th>" in html and "self-review threat" in html
    assert "strength of authentication factors" in html


def test_run_id_falls_back_to_out_dir(lab, tmp_path, monkeypatch):
    monkeypatch.delenv("ATTEST_RUN_ID", raising=False)
    state, _ = _iam_run(tmp_path, monkeypatch)
    assert state["run_id"] == "run"
    state2, _ = _iam_run(tmp_path, monkeypatch, run_id="explicit")
    assert state2["run_id"] == "explicit"                  # l'argument explicite reste prioritaire


def test_code_report_hides_after_column_and_iam_limits(lab, tmp_path, monkeypatch):
    from attest import studio
    monkeypatch.setenv("ATTEST_LANG", "fr")                  # le Studio écrit ATTEST_LANG : restauré après le test
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    c = studio.app.test_client()
    r = c.post("/interpret", data={"lang": "en", "lib": ["rts-16-developpement", "politique-pds-2-developpement"],
                                    "target": "repo:paiement-api"})
    sid = r.location.split("/review/")[1].split("?")[0]
    page = c.get(f"/review/{sid}").get_data(as_text=True)
    assert "“" in page and "«" not in page              # guillemets anglais
    assert "Rule unrelated to this target." in page or "Covered by the internal policy controls." in page
    c.post(f"/run/{sid}", data={"reviewer": "A. Auditor", "ctrl": ["C1", "C2", "C3"]})
    for _ in range(120):
        st = c.get(f"/status/{sid}").get_json()
        if st["state"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert st["state"] == "done", st
    html = (tmp_path / "studio" / sid / "audit" / "report.html").read_text()
    s3 = html.split('<section id="s3">')[1].split("</section>")[0]
    assert "<th>After</th>" not in s3
    assert len(re.findall("<th>", s3.split("</tr>")[0])) == 7
    assert "strength of authentication factors" not in html and "self-review threat" not in html
    assert "repository content at the audited revision" in html


def test_studio_language_marked_and_run_button_disabled(tmp_path, monkeypatch):
    from attest import studio
    monkeypatch.setenv("ATTEST_LANG", "fr")                  # le Studio écrit ATTEST_LANG : restauré après le test
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    c = studio.app.test_client()
    page = c.get("/?lang=en").get_data(as_text=True)
    assert re.search(r'<a href="/\?lang=en"[^>]*class="on" aria-current="true"', page)
    assert not re.search(r'<a href="/\?lang=fr"[^>]*aria-current', page)
    r = c.post("/interpret", data={"lang": "fr", "lib": ["politique-psi-4-acces"], "target": "iam-console"})
    sid = r.location.split("/review/")[1].split("?")[0]
    page = c.get(f"/review/{sid}").get_data(as_text=True)
    assert '<button id="go"' in page
    assert "b.disabled=!f.querySelector('input[name=ctrl]:checked')" in page
    assert "« " in page and "“" not in page                 # guillemets français en FR
