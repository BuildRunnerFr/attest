"""Population complète : un « conforme » rendu sur une liste paginée lue en partie n'est pas un verdict."""
import json

import requests

from attest import mock, sandbox
from attest.sandbox import _partial_population as partial
from lab.scenarios import PAGE_SIZE

P09, P10 = "09-kerlann-annuaire-pagine", "10-oceane-annuaire-presque"
AUDIT, CHANGE = "audit-ro-demo", "change-rw-demo"

FIRST_PAGE_ONLY = '''
import json, os, requests
H = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
users = requests.get(os.environ["LAB_URL"] + "/api/users", headers=H, timeout=10).json()
bad = [u["login"] for u in users if u["role"] == "admin" and u["login"].startswith("%s")]
print(json.dumps({"status": "fail" if bad else "pass", "observed": {"n": len(users), "bad": bad},
                  "expected": "none", "detail": "%%d accounts read" %% len(users)}))
'''


def _reset(lab, sid):
    r = requests.post(lab + "/api/reset", json={"scenario": sid},
                      headers={"Authorization": "Bearer " + CHANGE}, timeout=10)
    assert r.status_code == 200


def _req(path, page=None, pages=None, nxt=None, status=200):
    pg = {k: v for k, v in (("page", page), ("pages", pages), ("next", nxt)) if v is not None}
    return {"method": "GET", "path": path, "status": status, **({"pagination": pg} if pg else {})}


def test_partial_population_rules():
    assert partial([_req("/api/security")]) is None                                   # point d'accès non paginé
    assert partial([_req("/api/users", 1, 1)]) is None                                # une seule page
    assert partial([_req(f"/api/users?page={i}", i, 3) for i in (1, 2, 3)]) is None   # tout lu
    assert partial([_req("/api/users", 1, 8, "/api/users?page=2")]) == {"path": "/api/users", "read": 1, "pages": 8}
    # une page en erreur ne compte pas comme lue
    assert partial([_req("/api/users", 1, 2), _req("/api/users?page=2", 2, 2, status=500)])["read"] == 1
    # sans numérotation : chaque lien « next » annoncé doit avoir été suivi (ordre des paramètres indifférent)
    assert partial([_req("/items", nxt="/items?cursor=b&n=5"), _req("/items?n=5&cursor=b")]) is None
    assert partial([_req("/items", nxt="/items?cursor=b")])["path"] == "/items"


def test_pass_on_first_page_only_is_inconclusive(lab):
    _reset(lab, P09)
    res = sandbox.run(FIRST_PAGE_ONLY % "support", lab, AUDIT)
    assert res["status"] == "error" and "/api/users" in res["detail"] and "Link" in res["detail"]
    assert res["requests"]["partial_population"] == {"path": "/api/users", "read": 1, "pages": 8}


def test_fail_on_partial_population_stays_a_finding(lab):
    _reset(lab, P09)
    res = sandbox.run(FIRST_PAGE_ONLY % "a.", lab, AUDIT)        # une exception vue en page 1 reste un constat
    assert res["status"] == "fail" and "/api/users" in res["detail"]


def test_unpaginated_directory_unaffected(lab):
    _reset(lab, "01-kerlann-adm")
    res = sandbox.run(FIRST_PAGE_ONLY % "zzz", lab, AUDIT)
    assert res["status"] == "pass" and "partial_population" not in res["requests"]


def test_full_pagination_finds_the_late_generic_account(lab):
    _reset(lab, P09)
    code = mock._code("C7").split("```python")[1].split("```")[0]
    res = sandbox.run(code, lab, AUDIT)
    assert res["status"] == "fail" and res["requests"]["count"] == 8 and PAGE_SIZE == 100
    assert res["observed"]["generic_admin_accounts"] == ["support-n2"]
    assert "partial_population" not in res["requests"]


def test_library_failure_guides_the_rewrite(monkeypatch, tmp_path):
    """Le motif d'échec du script de bibliothèque est transmis au modèle pour la réécriture."""
    from attest import catalog, pipeline
    seen = []
    monkeypatch.setattr(catalog, "library_get", lambda c, doc=None: "print('old')")
    monkeypatch.setattr(catalog, "library_put", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "_safe_run", lambda code, ctx: (
        {"status": "error", "detail": "incomplete population: /api/users"} if "old" in code
        else {"status": "pass", "observed": 1, "requests": {"count": 1, "log": []}}))
    monkeypatch.setattr(pipeline, "_write_test", lambda c, error, doc: seen.append(error) or "print('new')")

    class T:
        def log(self, *a, **k): pass
    (tmp_path / "scripts").mkdir()
    ctx = type("C", (), {"fresh": False, "doc": "d", "out": tmp_path, "trail": T(), "rel": staticmethod(str)})()
    e = {"control": {"id": "C7", "rule": "PSI-4.7", "title": "t"}}
    pipeline.run_test(e, ctx)
    assert seen == ["incomplete population: /api/users"] and e["test"]["origin"] == "generated"
