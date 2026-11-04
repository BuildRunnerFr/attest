"""Interfaces bilingues : tableau de bord d'évaluation, Studio et rapport en anglais sans résidu français."""
import json

from attest import bench, config

EN = config.ROOT / "examples" / "evaluation-en" / "scorecard.json"


def test_scorecard_english():
    d = json.loads(EN.read_text())
    assert d["lang"] == "en"
    page, md = bench.to_html(d), bench.to_markdown(d)
    assert '<html lang="en">' in page
    for fr in ("Évaluation", "justesse", "faux constats", "Scénario", "Coût", "Cas de la démo"):
        assert fr not in page and fr not in md
    assert "✔ NC found" in page and "✔ compliant" in page and "$0.65" in page
    assert "Measured cost: $0.65" in md


def test_scorecard_french_default():
    d = json.loads(EN.read_text())
    d.pop("lang")
    page, md = bench.to_html(d), bench.to_markdown(d)
    assert '<html lang="fr">' in page and "Évaluation d" in page and "0.6489 $" in page
    assert "✔ NC détectée" in page and "Justesse : **100 %**" in md


def test_studio_index_english_titles():
    from attest import studio
    c = studio.app.test_client()
    en = c.get("/?lang=en").get_data(as_text=True)
    assert "DORA — Article 9(4): access, strong authentication, change management" in en
    assert "sécurité des données" not in en and "contrôle d'accès" not in en
    fr = c.get("/?lang=fr").get_data(as_text=True)
    assert "DORA — article 9(4) : accès, authentification forte, gestion des changements" in fr
    assert set(studio.LIB_EN) == {p.stem for p in studio.LIB.glob("*.md")}


def test_report_framework_english(monkeypatch):
    from attest import report
    monkeypatch.setenv("ATTEST_LANG", "en")
    assert "(EU)" in report.framework({}) and "(UE)" not in report.framework({})
    assert "(EU)" in report.framework({"framework_label": report.FRAMEWORK_DEFAULT})
    monkeypatch.setenv("ATTEST_LANG", "fr")
    assert report.framework({}) == report.FRAMEWORK_DEFAULT
