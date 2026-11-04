"""Grands annuaires paginés (scénarios 09 et 10) : vérité terrain, pagination de la console, non-régression 01-08."""
import json
import os

import pytest
import requests

from attest import bench
from lab.scenarios import PAGE_SIZE, build, expected, generic_admins, page_of

BY_ID = {s["id"]: s for s in build()}
P09, P10 = "09-kerlann-annuaire-pagine", "10-oceane-annuaire-presque"
H = {"Authorization": "Bearer audit-ro-demo"}


def _reset(base, sid):
    requests.post(base + "/api/reset", json={"scenario": sid} if sid else {}, timeout=10,
                  headers={"Authorization": "Bearer change-rw-demo"}).raise_for_status()


def _all_pages(base):
    url, out, pages = base + "/api/users", [], 0
    while url:
        r = requests.get(url, headers=H, timeout=10)
        r.raise_for_status()
        out += r.json()
        pages += 1
        url = base + r.links["next"]["url"] if "next" in r.links else None
    return out, pages, r


def test_09_one_generic_admin_not_on_page_one():
    sc = BY_ID[P09]
    assert sc["pagination"] == {"page_size": PAGE_SIZE} and 600 <= len(sc["users"]) <= 900
    assert [r for r, v in sc["expected"].items() if v == "fail"] == ["PSI-4.7"]
    assert sc["expected_generic_admins"] == generic_admins(sc["users"]) == ["support-n2"]
    assert page_of(sc["users"], "support-n2") > 1
    first = sc["users"][:PAGE_SIZE]
    assert any(u["role"] == "admin" for u in first) and not generic_admins(first)   # page 1 seule : « conforme »


def test_10_near_faulty_twin_all_pass():
    sc = BY_ID[P10]
    assert sc["pagination"] and 600 <= len(sc["users"]) <= 900
    assert set(sc["expected"].values()) == {"pass"} and sc["expected_generic_admins"] == []
    admins = {u["login"] for u in sc["users"] if u["role"] == "admin"}
    assert {"j.opsomer", "t.teamson", "r.rootsaert", "k.morvan"} <= admins          # sous-chaînes, pas des mots
    roles = {u["login"]: u["role"] for u in sc["users"]}
    assert roles["support-agence"] == roles["svc-batch"] == roles["helpdesk"] == "conseiller"
    s = sc["security"]
    assert (s["password_min_length"], s["lockout_threshold"], s["session_timeout_minutes"]) == (12, 5, 15)
    assert max(page_of(sc["users"], x) for x in ("t.teamson", "svc-batch")) > 1      # pièges aussi en page tardive


def test_files_match_oracle_and_logins_unique():
    for sid, sc in BY_ID.items():
        on_disk = json.loads((bench.SCEN_DIR / f"{sid}.json").read_text())
        assert on_disk == sc, sid
        assert on_disk["expected"] == expected(on_disk["security"], on_disk["users"])
        assert len({u["login"] for u in sc["users"]}) == len(sc["users"])
    assert [k for k, s in BY_ID.items() if s.get("pagination")] == [P09, P10]


@pytest.mark.parametrize("sid", [P09, P10])
def test_pagination_returns_every_account_once(lab, sid):
    _reset(lab, sid)
    users, pages, last = _all_pages(lab)
    truth = BY_ID[sid]["users"]
    assert [u["login"] for u in users] == [u["login"] for u in truth]                # chacun une fois, dans l'ordre
    assert pages == -(-len(truth) // PAGE_SIZE) and "next" not in last.links
    r = requests.get(lab + "/api/users", headers=H, timeout=10)
    assert len(r.json()) == PAGE_SIZE and r.headers["X-Total-Count"] == str(len(truth))
    assert r.headers["X-Total-Pages"] == str(pages) and r.links["next"]["url"] == "/api/users?page=2&per_page=100"
    assert requests.get(lab + "/api/users?per_page=5000", headers=H, timeout=10).headers["X-Page"] == "1"
    assert len(requests.get(lab + "/api/users?per_page=5000", headers=H, timeout=10).json()) == PAGE_SIZE
    assert requests.get(lab + f"/api/users?page={pages + 1}", headers=H, timeout=10).json() == []
    assert requests.get(lab + "/api/users?page=x", headers=H, timeout=10).status_code == 400


def test_html_page_follows_api_pages(lab):
    _reset(lab, P09)
    p = page_of(BY_ID[P09]["users"], "support-n2")
    first = requests.get(lab + "/admin/users", headers=H, timeout=10).text
    assert "user-support-n2" not in first and "721 comptes" in first and first.count('id="user-') == PAGE_SIZE
    late = requests.get(lab + f"/admin/users?page={p}", headers=H, timeout=10).text
    assert 'id="user-support-n2"' in late and f"Page {p} / 8" in late


@pytest.mark.parametrize("sid", [None, "01-kerlann-adm", "07-ardoise-grand-annuaire"])
def test_scenarios_without_flag_not_paginated(lab, sid):
    _reset(lab, sid)
    import lab.app as labapp
    want = BY_ID[sid]["users"] if sid else labapp.DEFAULT_STATE["users"]
    for q in ("", "?page=2", "?per_page=1"):
        r = requests.get(lab + "/api/users" + q, headers=H, timeout=10)
        assert r.json() == want
        assert not {"Link", "X-Total-Count", "X-Page", "X-Total-Pages"} & set(r.headers)
    page = requests.get(lab + "/admin/users", headers=H, timeout=10).text
    assert 'id="pagination"' not in page and page.count('id="user-') == len(want)
    assert "pagination" not in json.loads(open(os.environ["LAB_STATE_FILE"]).read())


def test_demo_state_has_no_pagination():
    import lab.app as labapp
    assert "pagination" not in labapp.DEFAULT_STATE


def test_default_bench_excludes_stress_set():
    default = [p.stem for p in bench.select()]
    assert default == sorted(k for k in BY_ID if k < "09") and len(default) == 8
    assert sum(len(BY_ID[k]["expected"]) for k in default) == 56
    assert sum(v == "fail" for k in default for v in BY_ID[k]["expected"].values()) == 15
    assert [k for k, s in BY_ID.items() if s.get("stress")] == [P09, P10]


def test_stress_set_only_when_named():
    assert [p.stem for p in bench.select(["09", "10"])] == [P09, P10]
    assert [p.stem for p in bench.select(["05", " 10"])] == ["05-menhir-tresorerie-generiques", P10]
    assert [p.stem for p in bench.select([""])] == []
