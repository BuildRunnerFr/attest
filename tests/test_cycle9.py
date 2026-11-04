"""Cycle 9 : id du registre dans l'étape Audit, intitulés du mock en EN, méthode sans correctif, test ponctuel."""
import importlib.util
import json
import re
import time

import yaml

from attest import config, mock, report

WF = config.ROOT / ".github" / "workflows" / "real-audit.yml"


def _publish():
    spec = importlib.util.spec_from_file_location("publish", config.ROOT / "ops" / "publish.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _steps():
    wf = yaml.safe_load(WF.read_text())
    return [s for job in wf["jobs"].values() for s in job["steps"]]


# ---------- 1. ATTEST_RUN_ID = id du registre ----------

def test_audit_step_sets_run_id_from_ledger_computation():
    steps = _steps()
    names = [s.get("name") for s in steps]
    rid = next(s for s in steps if s.get("id") == "runid")
    # l'id est calculé par ops/publish.py (même fonction que le registre), avec le type et le backend du run
    assert 'python ops/publish.py --run-id "$KIND" "$BACKEND"' in rid["run"] and "GITHUB_OUTPUT" in rid["run"]
    audit = next(s for s in steps if s.get("name") == "Audit")
    pub = next(s for s in steps if str(s.get("name", "")).startswith("Publication"))
    assert names.index(rid["name"]) < names.index("Audit")
    assert audit["env"]["ATTEST_RUN_ID"] == "${{ steps.runid.outputs.id }}"
    assert pub["env"]["ATTEST_RUN_ID"] == "${{ steps.runid.outputs.id }}"   # la publication reprend le même id


def test_ledger_id_format_and_reuse(tmp_path, monkeypatch, capsys):
    pub = _publish()
    assert pub.run_id("studio-iam", "meta", "20261104-123009") == "20261104-123009-studio-iam-meta"
    assert re.fullmatch(r"\d{8}-\d{6}-code-mock", pub.run_id("code", "mock"))
    # publish.py reprend l'id posé avant l'audit : le rapport et le registre portent le même
    monkeypatch.setenv("ATTEST_RUN_ID", "20261104-101500-iam-mock")
    monkeypatch.setenv("ATTEST_USAGE_FILE", str(tmp_path / "none.json"))
    monkeypatch.setattr("sys.argv", ["publish.py", str(tmp_path / "out"), str(tmp_path / "res"), "iam", "mock"])
    pub.main()
    line = json.loads((tmp_path / "res" / "ledger.jsonl").read_text().splitlines()[0])
    assert line["id"] == "20261104-101500-iam-mock" and line["utc"] == "20261104-101500"
    assert (tmp_path / "res" / "runs" / "20261104-101500-iam-mock").is_dir()
    # id d'un autre format (ou d'un autre type) : ignoré, l'horodatage est recalculé
    monkeypatch.setenv("ATTEST_RUN_ID", "gh-123")
    pub.main()
    line = json.loads((tmp_path / "res" / "ledger.jsonl").read_text().splitlines()[1])
    assert re.fullmatch(r"\d{8}-\d{6}-iam-mock", line["id"]) and line["id"] != "gh-123"


# ---------- 2. intitulés du mock ----------

def test_mock_titles_follow_language(monkeypatch):
    monkeypatch.setenv("ATTEST_LANG", "en")
    plan = {c["id"]: c["title"] for c in json.loads(mock.answer("plan", "", {}))}
    assert plan["C1"] == "MFA for privileged accounts" and plan["C7"] == "Named privileged accounts"
    assert mock._code_control("tls", "paiement-api", "text")["title"] == "TLS verification of outbound calls"
    assert set(mock.TITLES_EN) == {c[0] for c in mock.CONTROLS} | set(mock.CODE)
    monkeypatch.setenv("ATTEST_LANG", "fr")
    plan = {c["id"]: c["title"] for c in json.loads(mock.answer("plan", "", {}))}
    assert plan["C1"] == "MFA des comptes à privilèges" and plan["C7"] == "Comptes à privilèges nominatifs"
    assert mock._code_control("tls", "paiement-api", "text")["title"] == "Vérification TLS des appels sortants"


# ---------- 3 et 4. méthode et limites du rapport ----------

def test_method_step5_without_remediation(monkeypatch):
    code = {"target": "repo:paiement-api", "remediation_requested": False, "started": "2026-11-04 12:30"}
    for lang, words in (("en", ("fix",)), ("fr", ("correctif", "correction"))):
        monkeypatch.setenv("ATTEST_LANG", lang)
        steps = report.method(code)
        assert len(steps) == 6 and steps[4] == report.t("method.noremediation")
        assert not any(w in steps[4].lower() for w in words)
        # avec remédiation : étape d'origine conservée
        assert report.method({**code, "remediation_requested": True}) == list(report.t("method"))


def test_point_in_time_limitation(monkeypatch):
    iam = {"target": "iam-console", "remediation_requested": True, "started": "2026-11-04 12:30"}
    code = {"target": "repo:paiement-api", "remediation_requested": False, "started": "2026-11-04 12:30"}
    monkeypatch.setenv("ATTEST_LANG", "en")
    lim = report.limits(iam)
    assert lim[1] == ("Point-in-time test: the configuration was observed on 2026-11-04; the tests assess the design "
                      "and implementation of the controls at that date, not their operating effectiveness over a period.")
    assert len(lim) == 5 and "self-review threat" in lim[3]
    assert "repository was examined on 2026-11-04" in report.limits(code)[1]
    monkeypatch.setenv("ATTEST_LANG", "fr")
    lim = report.limits(iam)
    assert lim[1].startswith("Test ponctuel : la configuration a été observée le 2026-11-04")
    assert "pas leur efficacité opérationnelle sur une période" in lim[1]
    assert "le dépôt a été examiné le 2026-11-04" in report.limits(code)[1]


def test_code_report_method_and_limits_end_to_end(lab, tmp_path, monkeypatch):
    from attest import studio
    monkeypatch.setenv("ATTEST_LANG", "en")
    monkeypatch.setattr(studio, "WORK", tmp_path / "studio")
    c = studio.app.test_client()
    r = c.post("/interpret", data={"lang": "en", "lib": ["rts-16-developpement", "politique-pds-2-developpement"],
                                    "target": "repo:paiement-api"})
    sid = r.location.split("/review/")[1].split("?")[0]
    c.post(f"/run/{sid}", data={"reviewer": "A. Auditor", "ctrl": ["C1", "C2"]})
    for _ in range(120):
        st = c.get(f"/status/{sid}").get_json()
        if st["state"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert st["state"] == "done", st
    html = (tmp_path / "studio" / sid / "audit" / "report.html").read_text()
    s2 = html.split('<section id="s2">')[1].split("</section>")[0]
    method = s2.split("<ol>")[1].split("</ol>")[0]
    assert "No remediation was applied" in method and "fix" not in method.lower()
    assert "Point-in-time test: the repository was examined on" in s2
    assert "operating effectiveness over a period" in s2
