"""Règles de preuve : page réellement lue, opinion avec réserve, pré-masquage avant envoi au modèle."""
import json
from types import SimpleNamespace

from PIL import Image

from attest import config, pipeline, report
from attest.i18n import t
from attest.trail import Trail

CTRL = {"id": "C9", "rule": "PSI-4.9", "evidence_page": "/repo/demo/view?path=README.md"}


def test_page_404_falls_back_to_programme():
    res = {"status": "fail", "evidence_page": "/repo/demo/view?path=app/missing.py", "observed": {}}
    log = [{"method": "GET", "path": "/api/repo/demo/search?q=x", "status": 200},
           {"method": "GET", "path": "/api/repo/demo/file?path=app%2Fmissing.py", "status": 404}]
    assert pipeline.evidence_page(CTRL, res, log) == CTRL["evidence_page"]


def test_page_read_2xx_kept_and_no_log_unchanged():
    res = {"status": "fail", "evidence_page": "/repo/demo/view?path=app/db.py"}
    log = [{"method": "GET", "path": "/api/repo/demo/file?path=app%2Fdb.py", "status": 200}]
    assert pipeline.evidence_page(CTRL, res, log) == "/repo/demo/view?path=app/db.py"
    assert pipeline.evidence_page(CTRL, res, []) == "/repo/demo/view?path=app/db.py"
    # page hors dépôt : acceptée comme avant
    assert pipeline.evidence_page(CTRL, {"evidence_page": "/admin/users"}, log) == "/admin/users"
    assert pipeline.evidence_page(CTRL, {"evidence_page": "https://x/y"}, log) == CTRL["evidence_page"]


def test_observed_path_read_2xx_is_chosen():
    res = {"status": "fail", "evidence_page": "/repo/demo/view?path=app/gone.py",
           "observed": {"matches": [{"path": "app/gone.py", "line": 3}, {"path": "app/client.py", "line": 7},
                                    {"path": "app/other.py", "line": 1}]}}
    log = [{"method": "GET", "path": "/api/repo/demo/file?path=app%2Fgone.py", "status": 404},
           {"method": "GET", "path": "/api/repo/demo/file?path=app%2Fother.py", "status": 200},
           {"method": "GET", "path": "/api/repo/demo/file?path=app%2Fclient.py", "status": 200}]
    # ordre de « observed » : déterministe
    assert pipeline.evidence_page(CTRL, res, log) == "/repo/demo/view?path=app/client.py"


def test_review_counts_as_inconclusive_and_basis_says_so(monkeypatch):
    monkeypatch.setenv("ATTEST_LANG", "en")
    entries = [{"status_before": "fail"}, {"status_before": "review"}, {"status_before": "pass"}]
    n = pipeline.inconclusive_count(entries)
    assert n == 1
    assert pipeline.opinion(["moyenne"], n) == "reserve"
    assert pipeline.opinion(["elevee"], n) == "ameliorer"          # l'opinion vient des constats…
    state = {"mission": {"environment": "lab"}, "entries": entries, "started": "2026-11-04",
             "catalogue": {"reviewed": True}}
    html = report.basis(state)
    assert t("basis.qualified").format(n=1) in html.replace("&#x27;", "'")   # …et la réserve est dite
    assert "basis.qualified" not in report.basis({**state, "entries": entries[:1]})
    monkeypatch.setenv("ATTEST_LANG", "fr")
    assert "1 contrôle(s)" in t("basis.qualified").format(n=1)


def _ctx(tmp_path):
    (tmp_path / "evidence").mkdir()
    return SimpleNamespace(out=tmp_path, mission=SimpleNamespace(lab_url="http://lab"),
                           trail=Trail(tmp_path / "trail.jsonl"), rel=lambda p: str(p.relative_to(tmp_path)))


def _run(tmp_path, monkeypatch, premask):
    box = [20, 20, 60, 40]

    def capture(url, out, token):
        Image.new("RGB", (100, 80), (255, 255, 255)).save(out)
        return {"pii": [{"kind": "email", "text": "x@example.test", "box": box}], "lines": {}}

    seen = {}

    def inspect(c, result, shot, dom):
        img = Image.open(shot).convert("RGB")
        seen["path"], seen["px"], seen["out"] = shot, img.getpixel((40, 30)), img.getpixel((90, 70))
        return {"corroborates": True, "pii": []}

    monkeypatch.setattr(pipeline.evidence, "capture", capture)
    monkeypatch.setattr(pipeline, "inspect", inspect)
    monkeypatch.setattr(pipeline.sam, "segment_boxes", lambda shot, boxes: [])
    monkeypatch.setattr(config, "PREMASK", premask)
    ctx = _ctx(tmp_path)
    ev = pipeline.collect_evidence({"control": {**CTRL, "evidence_page": "/admin/users"}},
                                   {"status": "pass"}, "before", ctx)
    return seen, ev, ctx


def test_model_receives_premasked_image(tmp_path, monkeypatch):
    seen, ev, ctx = _run(tmp_path, monkeypatch, True)
    assert seen["px"] == (0, 0, 0) and seen["out"] == (255, 255, 255)
    assert not seen["path"].exists()                                # copie supprimée
    assert not list((tmp_path / "evidence").glob("*_raw.png"))
    assert ev["metrics"] == {"pii_total": 1, "pii_masked": 1, "pii_found_by_model": 0}
    sealed = [json.loads(l) for l in (tmp_path / "trail.jsonl").read_text().splitlines()]
    assert sealed[-1]["event"] == "evidence_sealed" and sealed[-1]["data"]["premask"] is True


def test_premask_off_sends_raw(tmp_path, monkeypatch):
    seen, ev, ctx = _run(tmp_path, monkeypatch, False)
    assert seen["px"] == (255, 255, 255)
    sealed = json.loads((tmp_path / "trail.jsonl").read_text().splitlines()[-1])
    assert sealed["data"]["premask"] is False
