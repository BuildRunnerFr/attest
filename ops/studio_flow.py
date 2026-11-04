"""Parcours complet d'Attest Studio sans navigateur, avec les vrais modèles (workflow real-audit) :
extraits choisis → interprétation ancrée → validation de tous les contrôles proposés → audit → rapport.

  python ops/studio_flow.py --lib rts-16-developpement,politique-pds-2-developpement \\
                            --target repo:paiement-api --out out/code [--remediate]

La validation humaine du Studio est ici donnée par « Attest CI » : ces exécutions vérifient le
système, elles ne valent pas opinion d'audit.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True, help="extraits de exigences/library, séparés par des virgules")
    ap.add_argument("--target", required=True, help="iam-console | repo:paiement-api")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--remediate", action="store_true")
    ap.add_argument("--reviewer", default="Attest CI")
    ap.add_argument("--approver", default="System owner (CI)")
    a = ap.parse_args()

    from attest import config, studio
    lang = config.lang()
    studio.WORK = a.out / "studio"
    c = studio.app.test_client()

    r = c.post("/interpret", data={"lang": lang, "lib": a.lib.split(","), "target": a.target})
    if r.status_code != 302:
        print(r.get_data(as_text=True)[-3000:])
        sys.exit("interprétation refusée ou en erreur")
    sid = r.location.split("/review/")[1].split("?")[0]
    it = json.loads((studio.WORK / sid / "interpretation.json").read_text())
    print("interprétation :", json.dumps(it["counts"], ensure_ascii=False))
    ctrl = [k["id"] for q in it["requirements"] if q["quote_verified"] for k in q["controls"]]
    if not ctrl:
        sys.exit("aucun contrôle automatisable proposé")

    form = {"reviewer": a.reviewer, "approver": a.approver, "ctrl": ctrl, "unattended": "1"}
    if a.remediate:
        form["remediate"] = "on"
    r = c.post(f"/run/{sid}", data=form)
    if r.status_code != 302:
        print(r.get_data(as_text=True)[-3000:])
        sys.exit("lancement de l'audit refusé")

    t0 = time.time()
    while True:
        st = c.get(f"/status/{sid}").get_json()
        if st["state"] in ("done", "error"):
            break
        if time.time() - t0 > 40 * 60:
            sys.exit("audit trop long (40 min)")
        time.sleep(2)
    audit = studio.WORK / sid / "audit"
    for name in ("interpretation.json", "catalogue.json"):
        if (studio.WORK / sid / name).exists():
            shutil.copy2(studio.WORK / sid / name, audit / name)
    print("audit :", st)
    if st["state"] != "done":
        sys.exit(st.get("message", "audit en erreur"))


if __name__ == "__main__":
    main()
