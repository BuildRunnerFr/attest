#!/usr/bin/env bash
# Verrou des cycles planifiés : un seul cycle d'amélioration à la fois.
# L'état est dans la branche cycle-lock (commits vides « held <date> » / « free <date> ») ; chaque prise de
# verrou est un push en avance rapide, donc deux cycles simultanés ne peuvent pas le prendre tous les deux.
#   bash ops/cycle_lock.sh acquire   → 0 : verrou pris · 3 : un autre cycle travaille (verrou de moins de 3 h)
#   bash ops/cycle_lock.sh release   → libère le verrou
set -u
cmd="${1:-}"
MAX_AGE="${CYCLE_LOCK_MAX_AGE:-10800}"
export GIT_AUTHOR_NAME="Ethan Blombou" GIT_AUTHOR_EMAIL="289934308+BuildRunnerFr@users.noreply.github.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
tree=$(git hash-object -w -t tree /dev/null)
now=$(date -u +%FT%TZ)

tip=""; state="free"; age=0
if git fetch -q origin cycle-lock 2>/dev/null; then
  tip=$(git rev-parse FETCH_HEAD)
  state=$(git log -1 --format=%s "$tip")
  age=$(( $(date +%s) - $(git log -1 --format=%ct "$tip") ))
fi

case "$cmd" in
  acquire)
    if [ "${state%% *}" = "held" ] && [ "$age" -lt "$MAX_AGE" ]; then
      echo "Un autre cycle travaille (verrou pris il y a $((age / 60)) min)."; exit 3
    fi
    c=$(git commit-tree "$tree" ${tip:+-p "$tip"} -m "held $now")
    if git push -q origin "$c:refs/heads/cycle-lock" 2>/dev/null; then
      echo "Verrou pris ($now)."; exit 0
    fi
    echo "Un autre cycle vient de prendre le verrou."; exit 3 ;;
  release)
    [ -n "$tip" ] || { echo "Aucun verrou."; exit 0; }
    c=$(git commit-tree "$tree" -p "$tip" -m "free $now")
    git push -q origin "$c:refs/heads/cycle-lock" && echo "Verrou libéré." ;;
  *)
    echo "usage : bash ops/cycle_lock.sh acquire|release"; exit 2 ;;
esac
