"""Adopte le programme de travail et les scripts d'une exécution réelle : écrit controls/<mission>.<langue>.json
et library/<règle>-<clé>.py à partir d'un result.json (branche real-results), pour qu'ils soient relus puis rejoués.

  ATTEST_LANG=en python ops/adopt_run.py <result.json> mission/keycloak.toml "<id de l'exécution>"

Rien n'est validé : le catalogue reste "reviewed": false tant qu'un auditeur ne l'a pas relu."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ATTEST_BACKEND", "meta")            # écrit dans controls/ et library/, pas dans runs/_mock_*


def main():
    from attest import catalog, config, targets
    from attest.trail import sha256_text
    result, mission_path, run_id = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    mission = config.load_mission(mission_path)
    doc = targets.api_doc(mission.target)
    res = json.loads(result.read_text(encoding="utf-8"))
    entries = res["entries"]
    keys = ("id", "rule", "title", "objective", "test_procedure", "expected", "severity", "references", "risk",
            "recommendation", "cause", "evidence_page", "remediation")
    controls = [{k: e["control"][k] for k in keys if k in e["control"]} for e in entries]
    data = {"mission": mission.id, "framework_sha256": sha256_text(mission.requirement + doc + config.lang()),
            "generated_by": (res.get("usage", {}).get("rows") or [{}])[0].get("model", "muse-spark-1.3"),
            "generated_at": run_id, "reviewed": False,
            "review_note": "Passer 'reviewed' à true après relecture par un auditeur.", "controls": controls}
    path = config.ROOT / "controls" / f"{mission.id}.{config.lang()}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("catalogue :", path.relative_to(config.ROOT), len(controls), "contrôles")
    for e, c in zip(entries, controls):
        code = e["test"]["code"]
        p = config.ROOT / "library" / f"{catalog._safe(c['rule'])}-{catalog.script_key(c, doc)}.py"
        head = "" if code.startswith("# Attest") else (
            f"# Attest — test {c['rule']} ({c['title']})\n# Écrit par muse-spark-1.3, exécution {run_id} — à relire avant validation.\n")
        p.write_text(head + code, encoding="utf-8")
        print("script    :", p.relative_to(config.ROOT), e["test"]["origin"])


if __name__ == "__main__":
    main()
