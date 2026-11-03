import json

import numpy as np
import pytest

from attest import llm, sam, sandbox
from attest.pipeline import guard_fix, opinion, snap
from attest.trail import Trail, verify


# ---------- garde-fou des scripts ----------

@pytest.mark.parametrize("code,reason", [
    ("import subprocess", "import interdit"),
    ("import requests\nrequests.patch('x')", "écriture interdite"),
    ("import requests\nrequests.post('x')", "écriture interdite"),
    ("open('/etc/passwd')", "appel interdit"),
    ("eval('1')", "appel interdit"),
    ("import os\nos.system('id')", "appel interdit"),
])
def test_guard_refuses(code, reason):
    with pytest.raises(sandbox.UnsafeCode, match=reason):
        sandbox.check(code)


def test_guard_accepts_read_only():
    sandbox.check("import json, os, requests\nr = requests.get(os.environ['LAB_URL'])\nprint(json.dumps({}))")


# ---------- correctifs ----------

def test_fix_whitelist():
    ok = {"method": "PATCH", "path": "/api/security", "body": {"mfa_admin": True}}
    assert guard_fix(ok) is None
    assert "route" in guard_fix({**ok, "path": "/api/users"})
    assert "non autorisé" in guard_fix({**ok, "body": {"is_admin": True}})
    assert "type" in guard_fix({**ok, "body": {"mfa_admin": "yes"}})
    assert "vide" in guard_fix({**ok, "body": {}})


def test_opinion_scale():
    assert opinion(["critique", "faible"]) == "insuffisant"
    assert opinion(["elevee"]) == "ameliorer"
    assert opinion(["moyenne"]) == "globalement"
    assert opinion([]) == "satisfaisant"


# ---------- SAM ----------

def test_sam_wire_format_roundtrip():
    from attest import mock
    out = mock.sam_output([(10, 20, 110, 60), (200, 30, 260, 90)], (400, 200))
    objs = sam.parse(out)
    assert [o["id"] for o in objs] == [1, 2]
    assert objs[0]["box"] == (10, 20, 110, 60)
    full = sam.full_mask(objs[0], (400, 200))
    assert full.shape == (200, 400) and full[40, 60] and not full[5, 5]


def test_snap_ignores_glyph_noise_outside_box():
    m = np.zeros((300, 1000), bool)
    for x in range(50, 800, 60):
        m[105:120, x:x + 30] = True          # « lettres » dans la ligne
    m[110:115, 950:990] = True               # pixels parasites hors zone
    assert snap(m, (40, 95, 900, 130)) == (50, 105, 800, 120)
    assert snap(np.zeros((300, 1000), bool), (40, 95, 900, 130)) == (40, 95, 900, 130)


# ---------- piste d'audit ----------

def test_trail_detects_tampering(tmp_path):
    (tmp_path / "evidence.png").write_bytes(b"preuve")
    from attest.trail import sha256_file
    tr = Trail(tmp_path / "trail.jsonl")
    tr.log("evidence_sealed", file="evidence.png", sha256=sha256_file(tmp_path / "evidence.png"))
    tr.log("report_issued")
    (tmp_path / "manifest.json").write_text(json.dumps({"trail_head": tr.head, "files": []}))
    assert verify(tmp_path)[0]

    (tmp_path / "evidence.png").write_bytes(b"falsifiee")
    ok, problems = verify(tmp_path)
    assert not ok and any("modifié" in p for p in problems)

    (tmp_path / "evidence.png").write_bytes(b"preuve")
    lines = (tmp_path / "trail.jsonl").read_text().splitlines()
    (tmp_path / "trail.jsonl").write_text("\n".join(reversed(lines)) + "\n")
    assert not verify(tmp_path)[0]


def test_extract_json_tolerates_prose():
    assert llm.extract_json('Voici :\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}
    assert llm.extract_json('texte [ {"b": 1} ] fin') == [{"b": 1}]


# ---------- confidentialité ----------

def test_safety_net_masks_what_the_model_missed(tmp_path):
    from PIL import Image
    from attest.pipeline import annotate, measure
    shot = tmp_path / "shot.png"
    Image.new("RGB", (400, 200), "white").save(shot)
    ip_box = (300, 50, 360, 70)
    insp = {"field_boxes": [], "pii": [{"text": "10.12.4.31", "box": [340, 50, 360, 70]}]}   # boîte trop courte
    dom = {"pii": [{"kind": "ipv4", "text": "10.12.4.31", "box": list(ip_box)}]}
    masks = annotate(shot, insp, "fail", tmp_path / "out.png", net_boxes=[ip_box])
    m = measure(masks, dom)
    assert m == {"pii_total": 1, "pii_masked": 1, "pii_found_by_model": 0}


def test_report_text_is_pseudonymised():
    from attest.report import redact
    out = redact('{"email": "anne.lefloch@kerlann-banque.example", "ip": "10.12.4.31", "iban": "FR76 3000 6000 0112 3456 7890 189"}')
    assert "anne.lefloch" not in out and "a•••@kerlann-banque.example" in out
    assert "10.12.•.•" in out and "4.31" not in out
    assert "FR76 •••• ••••" in out and "7890" not in out
    import json
    out = redact(json.dumps({"text": 'DB_PASSWORD = "Azerty123!"  # TODO'}))     # guillemets échappés (JSON)
    assert "Azerty123" not in out and "Az••••" in out


def test_no_finding_without_observed_value():
    """Un script qui conclut « fail » sans valeur constatée (ex. API injoignable) donne « test en échec »."""
    code = 'import json\nprint(json.dumps({"status": "fail", "observed": None, "expected": "x", "detail": "API KO"}))'
    assert sandbox.run(code, "http://127.0.0.1:9", "t")["status"] == "error"
    code = 'import sys\nsys.exit(2)'
    assert sandbox.run(code, "http://127.0.0.1:9", "t")["status"] == "error"


def test_model_boxes_are_read_tolerantly():
    from attest.pipeline import as_box, to_rows
    assert as_box([218.4, 201, 520, "224"]) == (218, 201, 520, 224)
    assert as_box({"x1": 1, "y1": 2, "x2": 50, "y2": 30}) == (1, 2, 50, 30)
    assert as_box({"x": 10, "y": 10, "w": 40, "h": 12}) == (10, 10, 50, 22)
    assert as_box("[5, 6, 90, 40]") == (5, 6, 90, 40)
    assert as_box({"a": 1}) is None and as_box([1, 2, 3]) is None and as_box(None) is None
    rows = [(28, 100, 1068, 124), (28, 124, 1068, 148), (28, 148, 1068, 172)]
    assert to_rows((100, 118, 300, 150), rows) == (28, 124, 1068, 148)     # ligne entière
    assert to_rows((100, 400, 300, 420), rows) is None                       # hors du code : ignoré


# ---------- plafond de dépense ----------

def test_budget_cap_stops_paid_calls(monkeypatch):
    monkeypatch.setattr(llm, "BACKEND", "meta")
    monkeypatch.setenv("ATTEST_BUDGET_USD", "1.0")
    total = llm.Usage()
    monkeypatch.setattr(llm, "TOTAL", total)
    total.add("muse-spark-1.3", "plan", inp=400_000)              # 0,50 $ au prix publié
    llm.check_budget()                                            # sous le plafond : l'appel part
    total.add("sam-3.1", "segment", images=30)                    # prix non publié : 30 × 0,02 $ comptés
    assert llm.spent_usd() == pytest.approx(1.10)
    with pytest.raises(llm.BudgetExceeded):
        llm.check_budget()


def test_ledger_counts_only_real_runs(tmp_path):
    import importlib.util
    from attest import config
    spec = importlib.util.spec_from_file_location("budget", config.ROOT / "ops" / "budget.py")
    budget = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(budget)
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"backend": "meta", "budget_spent_usd": 0.65}\n{"backend": "mock", "budget_spent_usd": 9}\n'
                      '{"backend": "meta", "budget_spent_usd": 0.30}\n')
    assert budget.spent(ledger) == pytest.approx(0.95)
    assert budget.spent(tmp_path / "absent.jsonl") == 0.0
