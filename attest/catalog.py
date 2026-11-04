"""Catalogue de contrôles (programme de travail) et bibliothèque de scripts de test.

- Le catalogue est rédigé par Muse Spark à partir du référentiel, puis ENREGISTRÉ (controls/<mission>.json)
  pour être relu et validé par un auditeur. Les audits suivants le réutilisent tant que le référentiel
  n'a pas changé : le résultat devient reproductible et le coût LLM tombe quasiment à zéro.
- Chaque script de test validé est conservé dans library/ (versionné dans git = revue de code par
  l'auditeur). Un script de la bibliothèque est rejoué tel quel ; il n'est régénéré que s'il échoue.
"""
import json
import logging
import time
import unicodedata
from pathlib import Path

from . import config, llm, prompts
from .trail import sha256_text

log = logging.getLogger(__name__)

API_DOC = (config.ROOT / "lab" / "API.md").read_text(encoding="utf-8")      # cible par défaut (console IAM)

_SEV_ALIASES = {
    "critique": "critique", "critical": "critique",
    "elevee": "elevee", "eleve": "elevee", "high": "elevee",
    "moyenne": "moyenne", "moyen": "moyenne", "medium": "moyenne",
    "faible": "faible", "low": "faible",
}


def _dir(name: str) -> Path:
    # en mode mock, on n'écrit jamais dans le catalogue ni la bibliothèque « réels »
    d = config.ROOT / ("runs/_mock_" + name if llm.BACKEND == "mock" else name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def _unwrap(controls) -> list:
    """Liste de contrôles, y compris sous la forme enveloppée {"controls": [...]} que renvoient certains LLM."""
    if isinstance(controls, dict):
        if isinstance(controls.get("controls"), list):
            return controls["controls"]
        raise ValueError("catalogue invalide : objet JSON sans liste « controls » "
                         f"(clés reçues : {', '.join(map(str, controls)) or 'aucune'})")
    if not isinstance(controls, (list, tuple)):
        raise ValueError(f"catalogue invalide : liste de contrôles attendue, reçu {type(controls).__name__}")
    return list(controls)


def normalize(controls: list, default_page: str = "/admin/security") -> list:
    out, seen = [], set()
    for i, c in enumerate(_unwrap(controls), 1):
        if not isinstance(c, dict):
            raise ValueError(f"catalogue invalide : le contrôle n° {i} n'est pas un objet JSON "
                             f"(reçu {type(c).__name__} : {str(c)[:60]!r})")
        c = dict(c)
        cid = str(c.get("id") or "").strip() or f"C{i}"
        if cid in seen:                          # doublon : suffixe déterministe -2, -3…
            k = 2
            while f"{cid}-{k}" in seen:
                k += 1
            log.warning("catalogue : identifiant %s en double (contrôle n° %d), renommé %s-%d", cid, i, cid, k)
            cid = f"{cid}-{k}"
        seen.add(cid)
        c["id"] = cid
        c["severity"] = _SEV_ALIASES.get(_ascii(c.get("severity", "moyenne")), "moyenne")
        refs = c.get("references") or []
        c["references"] = list(refs) if isinstance(refs, (list, tuple)) else [str(refs)]
        c["remediation"] = "manual" if _ascii(c.get("remediation", "config")).startswith("man") else "config"
        page = str(c.get("evidence_page") or default_page)
        c["evidence_page"] = page if page.startswith("/") else "/" + page
        for k in ("title", "objective", "test_procedure", "expected", "risk", "recommendation", "rule"):
            c[k] = str(c.get(k, "")).strip()
        c["cause"] = str(c.get("cause") or "").strip()
        out.append(c)
    return out


def load_or_plan(mission, trail, replan: bool = False) -> tuple[list, dict]:
    from . import targets
    doc = targets.api_doc(mission.target)
    framework_sha = sha256_text(mission.requirement + doc + config.lang())
    path = _dir("controls") / f"{mission.id}.{config.lang()}.json"
    if path.exists() and not replan:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("framework_sha256") == framework_sha:
            trail.log("catalogue_reused", file=str(path.relative_to(config.ROOT)),
                      reviewed=data.get("reviewed", False))
            return data["controls"], {"source": "catalogue", "reviewed": data.get("reviewed", False),
                                      "path": str(path.relative_to(config.ROOT))}

    txt = llm.ask("plan", prompts.PLAN_SYSTEM,
                  prompts.PLAN_USER.format(requirement=mission.requirement, api_doc=doc,
                                           lang=config.lang_name()))
    controls = normalize(llm.extract_json(txt), targets.get(mission.target)["default_page"])
    data = {"mission": mission.id, "framework_sha256": framework_sha,
            "generated_by": llm.model_for(False), "generated_at": time.strftime("%Y-%m-%d %H:%M"),
            "reviewed": False,
            "review_note": "Passer 'reviewed' à true après relecture par un auditeur.",
            "controls": controls}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    trail.log("catalogue_planned", model=llm.model_for(False), controls=len(controls),
              framework_sha256=framework_sha)
    return controls, {"source": "planned", "reviewed": False, "path": str(path.relative_to(config.ROOT))}


# ---------- bibliothèque de scripts ----------

def _safe(rule: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ".-" else "_" for ch in rule)[:40]


def script_key(control: dict, doc: str = API_DOC) -> str:
    spec = {k: control.get(k) for k in ("rule", "objective", "expected", "test_procedure", "evidence_page")}
    return sha256_text(json.dumps(spec, sort_keys=True, ensure_ascii=False) + doc)[:12]


def library_get(control: dict, doc: str = API_DOC) -> str | None:
    p = _dir("library") / f"{_safe(control['rule'])}-{script_key(control, doc)}.py"
    return p.read_text(encoding="utf-8") if p.exists() else None


def library_put(control: dict, code: str, doc: str = API_DOC):
    p = _dir("library") / f"{_safe(control['rule'])}-{script_key(control, doc)}.py"
    header = (f"# Attest — test {control['rule']} ({control['title']})\n"
              f"# Écrit par {llm.model_for(True)} le {time.strftime('%Y-%m-%d')} — à relire avant validation.\n")
    p.write_text(code if code.startswith("# Attest") else header + code, encoding="utf-8")
