import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_has_clients():
    data = json.loads((FIXTURES / "clients_export_prod.json").read_text())
    assert len(data["clients"]) > 0
