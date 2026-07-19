#!/usr/bin/env bash
# Per-worktree SQLite dev.db: fingerprint migrations+seed, cache in dev.db.stamp.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

abs_path() {
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

fingerprint() {
  {
    find "$ROOT/backend" -path '*/migrations/*.py' | sort
    printf '%s\n' \
      "$ROOT/backend/community/management/commands/seed.py" \
      "$ROOT/backend/community/management/commands/_seed_data.py" \
      "$ROOT/backend/community/management/commands/_seed_shared.py"
  } | xargs shasum -a 256 | shasum -a 256 | awk '{print $1}'
}

is_current() {
  local db=$1 stamp="${db}.stamp"
  [[ -f "$db" && -f "$stamp" ]] || return 1
  [[ "$(tr -d '[:space:]' < "$stamp")" == "$(fingerprint)" ]]
}

write_stamp() {
  fingerprint > "${1}.stamp"
}

ensure() {
  local db
  db=$(abs_path "$1")
  is_current "$db" && return 0

  local lock="${db}.lock.d"
  while ! mkdir "$lock" 2>/dev/null; do sleep 0.2; done
  trap "rmdir '$lock'" EXIT

  if is_current "$db"; then
    rmdir "$lock"
    trap - EXIT
    return 0
  fi
  (
    cd "$ROOT/backend"
    DATABASE_URL="sqlite:///$db" uv run python manage.py migrate
    DATABASE_URL="sqlite:///$db" uv run python manage.py seed
  )
  write_stamp "$db"
  rmdir "$lock"
  trap - EXIT
}

cmd=${1:-}
db=${2:-}
case "$cmd" in
  fingerprint) fingerprint ;;
  check) is_current "$(abs_path "$db")" ;;
  write) write_stamp "$(abs_path "$db")" ;;
  ensure) ensure "$db" ;;
  *)
    echo "usage: $0 {fingerprint|check|write|ensure} <dev.db>" >&2
    exit 2
    ;;
esac
