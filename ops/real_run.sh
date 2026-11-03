#!/usr/bin/env bash
# Une exécution d'Attest pour le workflow real-audit : démarre la console auditée, lance l'audit demandé.
# Usage : bash ops/real_run.sh <bench|iam|code|studio-iam|injection> <dossier de sortie>
set -uo pipefail
kind="$1"; out="$2"
mkdir -p "$out"

case "$kind" in bench|iam|code|studio-iam|injection) ;; *) echo "type inconnu : $kind"; exit 2 ;; esac
[ "$kind" = "injection" ] && export LAB_INJECTION=1
python -m lab.app > "$out/lab.log" 2>&1 &
for _ in $(seq 60); do curl -s -o /dev/null http://127.0.0.1:5050/ && break; sleep 0.5; done

case "$kind" in
  bench)      python -m attest bench ${BENCH_ONLY:+--only "$BENCH_ONLY"} --out "$out/bench" ;;
  iam)        python -m attest run --reset-lab --remediate --approve-all --approver "IAM owner (CI)" --out "$out/iam" ;;
  injection)  python -m attest run --reset-lab --out "$out/injection" ;;
  code)       python ops/studio_flow.py --lib rts-16-developpement,politique-pds-2-developpement \
                --target repo:paiement-api --out "$out/code" ;;
  studio-iam) python ops/studio_flow.py --lib dora-9-4-acces-changements,rts-21-controle-acces,politique-psi-4-acces \
                --target iam-console --remediate --out "$out/studio-iam" ;;
esac 2>&1 | tee "$out/run.log"
exit "${PIPESTATUS[0]}"
