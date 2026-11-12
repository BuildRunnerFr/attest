"""Cible Keycloak : scénarios et vérité terrain, passerelle en lecture seule (devant un faux Keycloak de test),
preuves paginées. Les mesures réelles viennent d'un Keycloak 26 (workflow real-audit, kind=keycloak-bench)."""
import importlib
import json
import os
import threading
from pathlib import Path

import pytest
import requests
from werkzeug.serving import make_server

from connectors.keycloak import scenarios, stub

ROOT = Path(__file__).resolve().parent.parent
AUDIT = {"Authorization": "Bearer audit-ro-demo"}
CHANGE = {"Authorization": "Bearer change-rw-demo"}


def _serve(app):
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


@pytest.fixture()
def gw(monkeypatch):
    """Passerelle réelle devant le faux Keycloak, royaume kerlann."""
    kc, kc_url = _serve(stub.make_app("stub-secret"))
    monkeypatch.setenv("KC_URL", kc_url)
    monkeypatch.setenv("KC_AUDIT_SECRET", "stub-secret")
    monkeypatch.setenv("KC_REALM", "kerlann")
    from connectors.keycloak import gateway
    importlib.reload(gateway)
    srv, url = _serve(gateway.app)
    monkeypatch.setenv("LAB_URL", url)
    yield url
    srv.shutdown()
    kc.shutdown()


def test_scenario_files_match_generator_and_ground_truth():
    built = scenarios.build()
    assert [s["id"] for s in built] == ["kc-01-kerlann", "kc-02-oceane", "kc-03-menhir"]
    for sc in built:
        assert json.loads((scenarios.DIR / f"{sc['id']}.json").read_text(encoding="utf-8")) == sc
        assert all(u["email"].endswith(".example") for u in sc["users"])
        assert len({u["login"] for u in sc["users"]}) == len(sc["users"]) > 100      # plus d'une page Keycloak
    k1, k2, k3 = built
    assert set(k1["expected"].values()) == {"fail"} and k1["expected_generic_admins"] == ["support-n2"]
    assert [u["login"] for u in k1["users"]].index("support-n2") >= 200
    assert set(k2["expected"].values()) == {"pass"} and not k2["expected_generic_admins"]
    assert [r for r, v in k3["expected"].items() if v == "fail"] == ["PSI-4.1", "PSI-4.2", "PSI-4.3", "PSI-4.5"]


def test_oracle_thresholds():
    users = [{"login": "a.b", "email": "a.b@x.example", "role": "admin", "totp": True}]
    ok = {"passwordPolicy": scenarios.COMPLEX.format(n=12), "bruteForceProtected": True, "failureFactor": 5,
          "ssoSessionIdleTimeout": 900, "adminEventsEnabled": True}
    assert set(scenarios.expected(ok, users).values()) == {"pass"}
    exp = lambda **k: scenarios.expected({**ok, **k}, users)
    assert exp(passwordPolicy="length(11) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)")["PSI-4.3"] == "fail"
    assert exp(passwordPolicy="length(16)")["PSI-4.3"] == "fail" and exp(passwordPolicy=None)["PSI-4.3"] == "fail"
    assert exp(failureFactor=6)["PSI-4.4"] == "fail" and exp(bruteForceProtected=False)["PSI-4.4"] == "fail"
    assert exp(ssoSessionIdleTimeout=901)["PSI-4.5"] == "fail" and exp(ssoSessionIdleTimeout=0)["PSI-4.5"] == "fail"


def test_gateway_requires_the_audit_token(gw):
    assert requests.get(gw + "/api/kc/realm").status_code == 401
    assert requests.get(gw + "/kc/users").status_code == 401
    assert requests.get(gw + "/api/kc/realm", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_gateway_returns_only_security_fields(gw):
    realm = requests.get(gw + "/api/kc/realm", headers=AUDIT).json()
    assert realm["passwordPolicy"] == "length(8)" and realm["bruteForceProtected"] is False
    assert "smtpServer" not in realm and "**" not in json.dumps(realm)
    u = requests.get(gw + "/api/kc/users?max=1", headers=AUDIT).json()[0]
    assert set(u) <= {"id", "username", "email", "firstName", "lastName", "enabled", "totp", "emailVerified",
                      "createdTimestamp", "requiredActions"} and "access" not in u


def test_gateway_declares_keycloak_pagination(gw):
    r = requests.get(gw + "/api/kc/users", headers=AUDIT)
    assert len(r.json()) == 100 and r.headers["X-Total-Count"] == "260"       # page par défaut de Keycloak
    seen, url = [], "/api/kc/users"
    while url:
        r = requests.get(gw + url, headers=AUDIT)
        seen += [u["username"] for u in r.json()]
        url = r.links.get("next", {}).get("url")
    assert len(seen) == len(set(seen)) == 260 and "support-n2" in seen[200:]
    assert requests.get(gw + "/api/kc/users?max=5000", headers=AUDIT).json().__len__() == 100   # plafonné
    admins = requests.get(gw + "/api/kc/roles/admin/users", headers=AUDIT)
    assert len(admins.json()) == 7 and "next" not in admins.links


def test_gateway_has_no_write_route(gw):
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        for path in ("/api/kc/realm", "/api/kc/users", "/api/kc/roles/admin/users"):
            assert requests.request(method, gw + path, headers=CHANGE, json={}).status_code == 405
    assert requests.get(gw + "/api/kc/roles/..%2F..%2Fusers/users", headers=AUDIT).status_code in (400, 404)


def test_reset_only_selects_a_scenario_realm(gw):
    assert requests.post(gw + "/api/reset", json={"scenario": "kc-02-oceane"}, headers=AUDIT).status_code == 403
    assert requests.post(gw + "/api/reset", json={"scenario": "master"}, headers=CHANGE).status_code == 400
    assert requests.post(gw + "/api/reset", json={"scenario": "kc-02-oceane"}, headers=CHANGE).json() == {"realm": "oceane"}
    assert requests.get(gw + "/api/kc/realm", headers=AUDIT).json()["failureFactor"] == 5
    assert requests.post(gw + "/api/reset", json={}, headers=CHANGE).json() == {"realm": "kerlann"}


def test_evidence_pages_and_located_account(gw):
    from attest import evidence
    dom = evidence.capture(gw + "/kc/realm", Path(os.environ.get("TMPDIR", "/tmp")) / "kc-realm-test.png", "audit-ro-demo")
    assert {"passwordPolicy", "failureFactor", "ssoSessionIdleTimeout", "adminEventsEnabled"} <= set(dom["rows"])
    url = evidence.locate(gw + "/kc/users", "audit-ro-demo", {"support-n2"})
    assert "first=200" in url
    page = requests.get(url, headers=AUDIT).text
    assert 'id="user-support-n2" data-role="admin"' in page


def test_keycloak_framework_is_the_same_text_as_the_reference():
    base = (ROOT / "exigences" / "dora_authentification.md").read_text(encoding="utf-8")
    kc = (ROOT / "exigences" / "keycloak_authentification.md").read_text(encoding="utf-8")
    assert kc == base.replace("Le système KRL-ADM supporte", "Le fournisseur d'identité Keycloak supporte")


def test_target_declared_and_probed(gw):
    from attest import targets
    assert targets.get("keycloak")["remediable"] is False and "keycloak" in targets.api_doc("keycloak").lower()
    assert list(targets.available(gw, "audit-ro-demo")) == ["keycloak"]
    assert set(targets.available("http://127.0.0.1:9", "x")) == set(targets.TARGETS)     # rien ne répond : toutes


def test_library_scripts_match_ground_truth_on_every_realm(gw):
    """Les 7 scripts écrits par Muse Spark sur un vrai Keycloak (exécution 20261112-130651-keycloak-bench-meta),
    rejoués sans modèle : même verdict que la vérité terrain sur les 3 royaumes, mêmes comptes désignés, et toute
    la population lue (260 comptes = 3 pages de Keycloak)."""
    from attest import catalog, config, pipeline, sandbox, targets
    doc = targets.api_doc("keycloak")
    controls = json.loads((ROOT / "controls" / "AUD-2026-KC-01.en.json").read_text(encoding="utf-8"))["controls"]
    assert sorted(c["rule"] for c in controls) == [f"PSI-4.{i}" for i in range(1, 8)]
    for sc in scenarios.build():
        assert requests.post(gw + "/api/reset", json={"scenario": sc["id"]}, headers=CHANGE).status_code == 200
        logins = {u["login"] for u in sc["users"]}
        for c in controls:
            code = (ROOT / "library" / f"{catalog._safe(c['rule'])}-{catalog.script_key(c, doc)}.py").read_text(encoding="utf-8")
            res = sandbox.run(code, gw, config.AUDIT_TOKEN)
            assert res["status"] == sc["expected"][c["rule"]], (sc["id"], c["rule"], res.get("detail"))
            assert "partial_population" not in res["requests"]
            want = sc["expected_offenders"].get(c["rule"])
            if want is not None and res["status"] == "fail":
                assert sorted(pipeline._strings(res["observed"]) & logins) == want, (sc["id"], c["rule"])
