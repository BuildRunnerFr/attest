#!/usr/bin/env bash
# Attest : démarre la console auditée (système fictif) et Attest Studio, puis ouvre le Studio.
# Usage : bash scripts/start.sh            Ctrl-C arrête les deux.
#         bash scripts/start.sh --check    affiche la configuration retenue (backend, URL) sans rien lancer.
# Les variables déjà définies dans le shell l'emportent sur .env : ATTEST_BACKEND=mock bash scripts/start.sh
# Compatible bash 3.2 (macOS) et Linux.
set -u
cd "$(dirname "$0")/.."
CHECK=""
[ "${1:-}" = "--check" ] && CHECK=1

if [ ! -f .env ]; then
  cp .env.example .env || exit 1
  echo "Fichier .env créé à partir de .env.example (renseigne MODEL_API_KEY pour les modèles Meta)."
fi
# Variables non vides déjà présentes dans le shell : on les garde après lecture de .env.
keep=""
for name in $(sed -n 's/^[[:space:]]*\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .env); do
  if eval "[ -n \"\${$name:-}\" ]"; then keep="$keep$(declare -p "$name")
"; fi
done
set -a; source .env; set +a
eval "$keep"

if [ "${ATTEST_BACKEND:-meta}" = "meta" ] && [ -z "${MODEL_API_KEY:-}" ]; then
  echo "Avertissement : MODEL_API_KEY est vide ; démarrage en mode mock (réponses simulées, sans clé)."
  echo "  Pour les modèles Meta : renseigne MODEL_API_KEY dans .env, puis relance."
  ATTEST_BACKEND=mock
fi
export ATTEST_BACKEND
export LAB_PORT="${LAB_PORT:-5050}"
export STUDIO_PORT="${STUDIO_PORT:-8000}"
export LAB_URL="http://127.0.0.1:${LAB_PORT}"     # l'auditeur teste la console lancée ici
STUDIO_URL="http://127.0.0.1:${STUDIO_PORT}"

if [ -n "$CHECK" ]; then
  echo "ATTEST_BACKEND=$ATTEST_BACKEND"
  echo "LAB_URL=$LAB_URL"
  echo "STUDIO_URL=$STUDIO_URL"
  exit 0
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

# Une instance lancée par un démarrage précédent (ancienne version du code) fausserait l'audit : on l'arrête.
# Seuls les processus de ce script (fichiers pid) sont visés, jamais ceux d'un autre dossier.
mkdir -p runs/_logs
for name in lab studio; do
  f="runs/_logs/$name.pid"
  if [ -f "$f" ]; then
    pid=$(cat "$f")
    case "$(ps -p "$pid" -o args= 2>/dev/null)" in
      *"-m lab.app"*|*"-m attest.studio"*) kill "$pid" 2>/dev/null; sleep 1 ;;
    esac
    rm -f "$f"
  fi
done

python -m lab.app > runs/_logs/lab.log 2>&1 &
LAB=$!
python -m attest.studio > runs/_logs/studio.log 2>&1 &
STUDIO=$!
echo "$LAB" > runs/_logs/lab.pid
echo "$STUDIO" > runs/_logs/studio.pid
trap 'kill $LAB $STUDIO 2>/dev/null; rm -f runs/_logs/lab.pid runs/_logs/studio.pid; echo; echo "Console et Studio arrêtés."' EXIT

up=""
for _ in $(seq 60); do
  for pid in $LAB $STUDIO; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Échec au démarrage (journaux ci-dessous ; port $LAB_PORT ou $STUDIO_PORT déjà pris ?) :"
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
