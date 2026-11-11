#!/usr/bin/env bash
# Démarre un Keycloak de test, y charge les royaumes fictifs et lance la passerelle d'audit en lecture seule.
#   bash ops/keycloak_up.sh            puis, dans un autre terminal :
#   python -m attest run mission/keycloak.toml      ou      python -m attest bench --target keycloak
# Keycloak : conteneur Docker (défaut) ou installation locale si KC_HOME pointe vers un Keycloak décompressé.
# Les mots de passe sont tirés au hasard à chaque lancement et ne quittent pas cette machine. Ctrl-C arrête tout.
# Avec KC_DETACH=1 (CI), le script rend la main une fois la passerelle prête et écrit les PID dans $KC_RUN_DIR.
set -uo pipefail
cd "$(dirname "$0")/.."
KC_VERSION="${KC_VERSION:-26.0.5}"
KC_PORT="${KC_PORT:-8081}"
GW_PORT="${LAB_PORT:-5050}"
RUN="${KC_RUN_DIR:-runs/_keycloak}"
mkdir -p "$RUN"
rand() { python3 -c "import secrets; print(secrets.token_urlsafe(24))"; }
# Compte d'amorçage : créé par Keycloak au premier démarrage seulement. Avec un KC_HOME déjà initialisé,
# fournir KC_ADMIN_USER et KC_ADMIN_PASSWORD (compte administrateur existant).
export KC_URL="http://127.0.0.1:$KC_PORT"
export KC_ADMIN_USER="${KC_ADMIN_USER:-bootstrap-$(rand | cut -c1-6)}" KC_ADMIN_PASSWORD="${KC_ADMIN_PASSWORD:-$(rand)}"
export KC_AUDIT_SECRET="$(rand)"

stop() {
  [ -f "$RUN/gateway.pid" ] && kill "$(cat "$RUN/gateway.pid")" 2>/dev/null
  [ -f "$RUN/keycloak.pid" ] && kill "$(cat "$RUN/keycloak.pid")" 2>/dev/null
  [ -f "$RUN/container" ] && docker rm -f "$(cat "$RUN/container")" > /dev/null 2>&1
  rm -f "$RUN"/*.pid "$RUN/container"
}
[ "${1:-}" = "stop" ] && { stop; echo "Keycloak et passerelle arrêtés."; exit 0; }
stop
if curl -s -o /dev/null "http://127.0.0.1:$GW_PORT/"; then
  echo "le port $GW_PORT répond déjà : arrête la console ou la passerelle précédente"; exit 1
fi

if [ -n "${KC_HOME:-}" ]; then
  KC_BOOTSTRAP_ADMIN_USERNAME="$KC_ADMIN_USER" KC_BOOTSTRAP_ADMIN_PASSWORD="$KC_ADMIN_PASSWORD" \
    env -u JAVA_TOOL_OPTIONS "$KC_HOME/bin/kc.sh" start-dev --http-port "$KC_PORT" > "$RUN/keycloak.log" 2>&1 &
  echo $! > "$RUN/keycloak.pid"
else
  command -v docker > /dev/null || { echo "Docker absent : installe Docker, ou décompresse Keycloak et indique KC_HOME."; exit 1; }
  docker run -d --rm -p "127.0.0.1:$KC_PORT:8080" \
    -e KC_BOOTSTRAP_ADMIN_USERNAME="$KC_ADMIN_USER" -e KC_BOOTSTRAP_ADMIN_PASSWORD="$KC_ADMIN_PASSWORD" \
    "quay.io/keycloak/keycloak:$KC_VERSION" start-dev > "$RUN/container" || exit 1
fi
[ "${KC_DETACH:-}" = "1" ] || trap 'stop; echo; echo "Keycloak et passerelle arrêtés."' EXIT

echo "Démarrage de Keycloak $KC_VERSION…"
for _ in $(seq 120); do curl -s -o /dev/null "$KC_URL/realms/master" && break; sleep 2; done
curl -s -o /dev/null "$KC_URL/realms/master" || { echo "Keycloak n'a pas démarré (voir $RUN/keycloak.log ou docker logs)."; stop; exit 1; }

python3 -m connectors.keycloak.seed || { stop; exit 1; }
# la passerelle ne reçoit que le secret du compte d'audit : ni le compte d'amorçage, ni la clé du modèle
env -u KC_ADMIN_USER -u KC_ADMIN_PASSWORD -u MODEL_API_KEY LAB_PORT="$GW_PORT" KC_REALM="${KC_REALM:-kerlann}" \
  python3 -m connectors.keycloak.gateway > "$RUN/gateway.log" 2>&1 &
echo $! > "$RUN/gateway.pid"
for _ in $(seq 40); do curl -s -o /dev/null "http://127.0.0.1:$GW_PORT/" && break; sleep 0.5; done
curl -s -o /dev/null "http://127.0.0.1:$GW_PORT/" || { echo "La passerelle n'a pas démarré (voir $RUN/gateway.log)."; stop; exit 1; }

echo
echo "  Keycloak            $KC_URL   (royaumes fictifs : kerlann, oceane, menhir)"
echo "  Passerelle d'audit  http://127.0.0.1:$GW_PORT   (lecture seule)"
echo "  Preuve visuelle     http://127.0.0.1:$GW_PORT/kc/realm?token=${LAB_AUDIT_TOKEN:-audit-ro-demo}"
echo
[ "${KC_DETACH:-}" = "1" ] && exit 0
echo "Ctrl-C pour tout arrêter."
wait
