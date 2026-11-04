"""Attest — ligne de commande.

  python -m attest run mission/kerlann-iam.toml                       # constat en lecture seule
  python -m attest run mission/kerlann-iam.toml --remediate           # + changements sur approbation
  python -m attest run mission/kerlann-iam.toml --remediate --approve-all --approver "Responsable IAM"
  python -m attest verify runs/<dossier>                              # intégrité des preuves et de la piste
  python -m attest bench                                              # évaluation sur 8 systèmes fictifs
"""
import argparse
import os
import sys
import time
from pathlib import Path

from . import config


def main():
    argv = sys.argv[1:]
    if argv and argv[0] not in ("run", "verify", "bench", "-h", "--help"):
        argv = ["run"] + argv                    # « python -m attest <fichier> » = run
    ap = argparse.ArgumentParser(prog="attest", description="Agent d'audit de conformité (DORA).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="exécuter une mission d'audit")
    r.add_argument("mission", type=Path, nargs="?", default=config.ROOT / "mission" / "kerlann-iam.toml",
                   help="lettre de mission .toml (ou un référentiel .md avec la mission par défaut)")
    r.add_argument("--remediate", action="store_true", help="proposer des changements, soumis à approbation")
    r.add_argument("--approve-all", action="store_true", help="approbation donnée d'avance (démo uniquement)")
    r.add_argument("--approver", default=os.getenv("ATTEST_APPROVER", "Responsable IAM (démo)"),
                   help="nom de l'approbateur des changements (propriétaire du système)")
    r.add_argument("--fresh", action="store_true", help="réécrire les scripts au lieu de la bibliothèque")
    r.add_argument("--replan", action="store_true", help="refaire le programme de travail")
    r.add_argument("--reset-lab", action="store_true", help="remettre la console de démo dans son état initial")
    r.add_argument("--lang", choices=["fr", "en"], help="langue du rapport (sinon ATTEST_LANG)")
    r.add_argument("--out", type=Path)

    b = sub.add_parser("bench", help="évaluer Attest sur les scénarios synthétiques (vérité terrain)")
    b.add_argument("--only", help="préfixes de scénarios, séparés par des virgules (ex. 02,05)")
    b.add_argument("--lang", choices=["fr", "en"])
    b.add_argument("--out", type=Path)

    v = sub.add_parser("verify", help="vérifier l'intégrité d'un dossier d'audit")
    v.add_argument("run_dir", type=Path)
    v.add_argument("--lang", choices=["fr", "en"], help="langue des messages (sinon ATTEST_LANG)")
    a = ap.parse_args(argv)

    if a.lang:
        os.environ["ATTEST_LANG"] = a.lang

    if a.cmd == "verify":
        from .i18n import t
        from .trail import verify
        if not a.run_dir.is_dir():
            ok, problems = False, [t("verify.no_dir").format(d=a.run_dir)]
        else:
            ok, problems = verify(a.run_dir, lang=config.lang())
        print(t("verify.ok") if ok else t("verify.tampered"))
        for p in problems:
            print("  -", p)
        sys.exit(0 if ok else 1)

    from . import llm, pipeline                  # après le choix de la langue
    llm.check_backend()                          # échec immédiat : backend inconnu ou clé absente

    if a.cmd == "bench":
        from .bench import run_bench
        mission = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml")
        run_bench(mission, a.out or Path("runs") / time.strftime("bench-%Y%m%d-%H%M%S"),
                  only=a.only.split(",") if a.only else None)
        return

    if a.mission.suffix == ".md":
        mission = config.load_mission(config.ROOT / "mission" / "kerlann-iam.toml", requirement_override=a.mission)
    else:
        mission = config.load_mission(a.mission)
    out = a.out or Path("runs") / time.strftime("%Y%m%d-%H%M%S")
    pipeline.run(mission, out, remediate=a.remediate, approve_all=a.approve_all, approver=a.approver,
                 fresh=a.fresh, replan=a.replan, reset_lab=a.reset_lab)


if __name__ == "__main__":
    main()
