"""Chargement de la lettre de mission (TOML) et des réglages."""
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEVERITIES = ["critique", "elevee", "moyenne", "faible"]          # ordre décroissant
DEFAULT_SLA = {"critique": 30, "elevee": 90, "moyenne": 180, "faible": 365}


@dataclass
class Mission:
    id: str
    title: str
    entity: str
    system: str
    system_criticality: str
    environment: str
    owner: str
    lead_auditor: str
    classification: str
    requirement_path: Path
    lab_url: str
    scope_in: list = field(default_factory=list)
    scope_out: list = field(default_factory=list)
    sla_days: dict = field(default_factory=lambda: dict(DEFAULT_SLA))
    target: str = "iam-console"
    framework_label: str = ""
    requirement_text: str | None = None          # texte déposé dans Attest Studio (sans fichier)

    @property
    def requirement(self) -> str:
        return self.requirement_text if self.requirement_text is not None else self.requirement_path.read_text()


def lang() -> str:
    return "en" if os.getenv("ATTEST_LANG", "fr").lower().startswith("en") else "fr"


def lang_name() -> str:
    return "English" if lang() == "en" else "French"


def load_mission(path: Path, requirement_override: Path | None = None) -> Mission:
    data = tomllib.loads(Path(path).read_text())
    m, scope = data["mission"], data.get("scope", {})
    req = requirement_override or (ROOT / m["requirement"])
    return Mission(
        id=m["id"],
        title=m.get(f"title_{lang()}", m.get("title_fr", m["id"])),
        entity=m["entity"], system=m["system"], system_criticality=m.get("system_criticality", ""),
        environment=m.get("environment", ""), owner=m.get("owner", ""),
        lead_auditor=os.getenv("ATTEST_AUDITOR", m.get("lead_auditor", "")),
        classification=m.get("classification", ""),
        requirement_path=Path(req),
        lab_url=os.getenv("LAB_URL", m.get("lab_url", "http://127.0.0.1:5050")).rstrip("/"),
        scope_in=scope.get("in", []), scope_out=scope.get("out", []),
        sla_days={**DEFAULT_SLA, **data.get("sla_days", {})},
        target=m.get("target", "iam-console"),
        framework_label=m.get("framework_label", "DORA art. 9(4) · RTS (UE) 2024/1774 art. 12, 21 · PSI-4"),
    )


def pricing() -> dict:
    p = ROOT / "pricing.toml"
    return tomllib.loads(p.read_text()) if p.exists() else {}


# Comptes de service de la console auditée
AUDIT_TOKEN = os.getenv("LAB_AUDIT_TOKEN", "audit-ro-demo")     # lecture seule : tests et captures
CHANGE_TOKEN = os.getenv("LAB_CHANGE_TOKEN", "change-rw-demo")  # changements approuvés uniquement
