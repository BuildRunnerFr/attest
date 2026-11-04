import os
import sys
from pathlib import Path

os.environ["ATTEST_BACKEND"] = "mock"
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import importlib
import threading

import pytest
from werkzeug.serving import make_server


@pytest.fixture()
def lab(tmp_path):
    """Console auditée réelle (Flask) sur un port libre, état isolé."""
    os.environ["LAB_STATE_FILE"] = str(tmp_path / "state.json")
    import lab.app as labapp
    importlib.reload(labapp)
    srv = make_server("127.0.0.1", 0, labapp.app, threaded=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    os.environ["LAB_URL"] = f"http://127.0.0.1:{srv.server_port}"
    yield os.environ["LAB_URL"]
    srv.shutdown()




@pytest.fixture(autouse=True)
def _langue_isolee():
    """Le Studio fixe ATTEST_LANG dans os.environ : chaque test retrouve la langue d'avant."""
    before = os.environ.get("ATTEST_LANG")
    yield
    if before is None:
        os.environ.pop("ATTEST_LANG", None)
    else:
        os.environ["ATTEST_LANG"] = before
