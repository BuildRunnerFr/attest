#!/usr/bin/env bash
# Attest : démarre la console auditée (système fictif) et Attest Studio, puis ouvre le Studio.
# Usage : bash scripts/start.sh            Ctrl-C arrête les deux.
# Compatible bash 3.2 (macOS) et Linux.
set -u
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Fichier .env absent : cp .env.example .env, puis renseigne MODEL_API_KEY (ou ATTEST_BACKEND=mock)."
  exit 1
fi
set -a; source .env; set +a
if [ "${ATTEST_BACKEND:-meta}" = "meta" ] && [ -z "${MODEL_API_KEY:-}" ]; then
  echo "MODEL_API_KEY est vide dans .env (ou ATTEST_BACKEND=mock pour une démo sans clé)."
  exit 1
fi

if [ -z "${VIRTUAL_ENV:-}" ]; then
  [ -d .venv ] || python3 -m venv .venv || exit 1
  source .venv/bin/activate
fi
pip install -q -r requirements.txt || exit 1
if ! python -c "from playwright.sync_api import sync_playwright as s; p = s().start(); p.chromium.launch().close(); p.stop()" > /dev/null 2>&1; then
  echo "Installation de Chromium pour les captures d'écran (une seule fois)…"
  python -m playwright install chromium > /dev/null 2>&1 \
    || echo "Avertissement : Chromium (Playwright) non installé ; les captures d'écran échoueront."
fi

# Une instance encore en mémoire (ancienne version du code) fausserait l'audit : on l'arrête.
pkill -i -f 'python.*-m lab[.]app' 2>/dev/null
pkill -i -f 'python.*-m attest[.]studio' 2>/dev/null
sleep 1

LAB_URL="http://127.0.0.1:${LAB_PORT:-5050}"
STUDIO_URL="http://127.0.0.1:${STUDIO_PORT:-8000}"
mkdir -p runs/_logs
python -m lab.app > runs/_logs/lab.log 2>&1 &
LAB=$!
python -m attest.studio > runs/_logs/studio.log 2>&1 &
STUDIO=$!
trap 'kill $LAB $STUDIO 2>/dev/null; echo; echo "Console et Studio arrêtés."' EXIT

up=""
for _ in $(seq 60); do
  for pid in $LAB $STUDIO; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Échec au démarrage (journaux ci-dessous) :"
      tail -n 15 runs/_logs/lab.log runs/_logs/studio.log
      exit 1
    fi
  done
  if curl -s -o /dev/null "$LAB_URL/" && curl -s -o /dev/null "$STUDIO_URL/"; then up=1; break; fi
  sleep 0.5
done
[ -n "$up" ] || { echo "La console ou le Studio ne répond pas ; voir runs/_logs/."; exit 1; }

echo
echo "  Attest Studio    $STUDIO_URL"
echo "  Console auditée  $LAB_URL/admin/security?token=${LAB_AUDIT_TOKEN:-audit-ro-demo}   (système fictif)"
case "${ATTEST_BACKEND:-meta}" in
  meta)  models="Meta Model API : ${ATTEST_MODEL_REASON:-muse-spark-1.3} + SAM 3.1" ;;
  local) models="local : ${LOCAL_MODEL:-muse-glimmer} (${LOCAL_BASE_URL:-})" ;;
  *)     models="mock (réponses simulées, sans clé)" ;;
esac
echo "  Modèles          $models"
echo "  Journaux         runs/_logs/        Ctrl-C pour tout arrêter"
echo
case "${OSTYPE:-}" in darwin*) open "$STUDIO_URL" ;; esac
wait
