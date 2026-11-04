"""Jeton substitut : le script du bac à sable ne voit jamais le vrai jeton d'audit, même transformé."""
import base64
import http.server
import json
import threading

import pytest

from attest import sandbox

REAL = "tok-REAL-0123456789abcdef"


def _forms(tok: str) -> list[str]:
    """Le jeton et des transformations qu'un script pourrait imprimer pour contourner scrub."""
    return [tok, tok[::-1], " ".join(tok), base64.b64encode(tok.encode()).decode(),
            base64.b64encode(tok[::-1].encode()).decode(), tok.encode().hex()]


def _assert_no_leak(text: str):
    for f in _forms(REAL):
        assert f not in text, f"forme du vrai jeton divulguée : {f!r}"


class _Echo(http.server.BaseHTTPRequestHandler):
    """200 si le bon jeton est présenté (et le renvoie en écho, corps et en-tête), 401 sinon ; /r redirige."""
    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        self.server.seen.append(auth)
        if self.path == "/r":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        ok = auth == "Bearer " + REAL
        body = json.dumps({"ok": ok, "echo": auth}).encode()
        self.send_response(200 if ok else 401)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Echo", auth)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def echo():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Echo)
    srv.seen = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", srv
    srv.shutdown()


LEAK = '''
import os, sys, json, base64
t = os.environ.get("LAB_TOKEN", "")
blob = " ".join([t, t[::-1], " ".join(t), base64.b64encode(t.encode()).decode(),
                 repr(dict(os.environ)), repr(dict(os.environb)), repr(os.getenv("SB_TOKEN"))])
sys.stderr.write("leak:" + blob[::-1] + "\\n")
print("leak:" + blob)
print(json.dumps({"status": "pass", "observed": t[::-1], "expected": " ".join(t), "detail": blob}))
'''


def test_script_ne_voit_que_le_substitut(echo):
    url, _ = echo
    # _run : sans garde statique ni scrub, pour prouver que rien n'atteint même la sortie brute
    res = sandbox._run(LEAK, url, REAL, 30)
    _assert_no_leak(json.dumps(res))
    assert sandbox.TOKEN_PLACEHOLDER[::-1] in json.dumps(res)      # le script a bien tourné


def test_scripts_existants_inchanges_et_garde_statique(echo):
    """Le motif des scripts de la bibliothèque (Bearer + LAB_TOKEN) fonctionne : le vrai jeton part à l'envoi."""
    url, srv = echo
    code = '''
import requests, os, json
r = requests.get(os.environ["LAB_URL"] + "/ok", headers={"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}, timeout=10)
d = r.json()
print(json.dumps({"status": "pass" if d["ok"] else "fail", "observed": [r.status_code, d["echo"][::-1],
                  r.headers.get("X-Echo", "")[::-1]], "expected": 200, "detail": "ok"}))
'''
    res = sandbox.run(code, url, REAL)
    assert res["status"] == "pass", res
    assert srv.seen == ["Bearer " + REAL]                               # la cible a reçu le vrai jeton
    assert res["requests"]["count"] == 1 and res["requests"]["log"][0]["status"] == 200
    _assert_no_leak(json.dumps(res))


def test_redirection_ne_divulgue_pas(echo):
    url, srv = echo
    code = '''
import requests, os, json
r = requests.get(os.environ["LAB_URL"] + "/r", headers={"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}, timeout=10)
h = [dict(x.request.headers) for x in r.history] + [dict(r.request.headers)]
print(json.dumps({"status": "pass", "observed": [r.status_code, str(h)[::-1], r.text[::-1]], "expected": 200, "detail": "r"}))
'''
    res = sandbox._run(code, url, REAL, 30)
    assert res["status"] == "pass", res
    assert srv.seen == ["Bearer " + REAL] * 2
    _assert_no_leak(json.dumps(res))


def test_exception_ne_divulgue_pas():
    """Erreur de connexion : ni e.request, ni le message, ni la trace non rattrapée ne portent le vrai jeton."""
    code = '''
import requests, os, sys
H = {"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}
try:
    requests.get(os.environ["LAB_URL"] + "/x", headers=H, timeout=3)
except Exception as e:
    sys.stderr.write(repr(e.args)[::-1] + str(dict(e.request.headers))[::-1] + "\\n")
requests.get(os.environ["LAB_URL"] + "/x", headers=H, timeout=3)
'''
    res = sandbox._run(code, "http://127.0.0.1:9", REAL, 30)
    assert res["status"] == "error"
    assert "ConnectionError" in res["detail"]
    _assert_no_leak(json.dumps(res))


def test_jeton_invalide_reste_un_401(echo):
    url, srv = echo
    code = '''
import requests, os, json
r = requests.get(os.environ["LAB_URL"] + "/ok", headers={"Authorization": "Bearer " + os.environ["LAB_TOKEN"]}, timeout=10)
print(json.dumps({"status": "pass", "observed": r.status_code, "expected": 200, "detail": "x"}))
'''
    res = sandbox.run(code, url, "jeton-invalide")
    assert srv.seen == ["Bearer jeton-invalide"]
    assert res["status"] == "error" and res["requests"]["log"][0]["status"] == 401
