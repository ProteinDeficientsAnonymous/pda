#!/usr/bin/env bash
# Per-worktree Postgres on shared Docker: unique DB name, stamp cache for migrate+seed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME_FILE="$ROOT/.dev-pg-db-name"
STAMP_FILE="$ROOT/.dev-pg-db.stamp"
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -p pda)
PSQL_ADMIN=(psql postgresql://pda:pda@localhost:5432/postgres -v ON_ERROR_STOP=1)

read_base_url() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    echo "$DATABASE_URL"
    return
  fi
  if [[ -f "$ROOT/.env" ]]; then
    local line
    line=$(grep -E '^DATABASE_URL=' "$ROOT/.env" | head -1 || true)
    if [[ -n "$line" ]]; then
      echo "${line#DATABASE_URL=}"
      return
    fi
  fi
  echo "postgresql://pda:pda@localhost:5432/pda"
}

ensure_name() {
  local name
  if [[ -f "$NAME_FILE" ]]; then
    name=$(tr -d '[:space:]' < "$NAME_FILE")
  else
    name="pda_$(openssl rand -hex 4)"
    printf '%s\n' "$name" > "$NAME_FILE"
  fi
  if [[ ! "$name" =~ ^pda_[0-9a-f]{8}$ ]]; then
    echo "invalid dev postgres database name in $NAME_FILE: $name" >&2
    exit 1
  fi
  echo "$name"
}

worktree_url() {
  BASE="$(read_base_url)" NAME="$(ensure_name)" python3 - <<'PY'
import os
from urllib.parse import urlparse, urlunparse

base = os.environ["BASE"]
name = os.environ["NAME"]
parsed = urlparse(base)
print(urlunparse(parsed._replace(path="/" + name)))
PY
}

pg_ready() {
  pg_isready -h localhost -p 5432 -U pda >/dev/null 2>&1
}

start_pg_if_needed() {
  pg_ready && return 0
  "${COMPOSE[@]}" up -d db
  for _ in $(seq 1 60); do
    pg_ready && return 0
    sleep 0.5
  done
  echo "postgres did not become ready on localhost:5432" >&2
  return 1
}

admin_psql() {
  "${PSQL_ADMIN[@]}" "$@"
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
  [[ -f "$STAMP_FILE" ]] || return 1
  admin_psql -tAc "SELECT 1 FROM pg_database WHERE datname='$(ensure_name)'" | grep -q 1 || return 1
  [[ "$(tr -d '[:space:]' < "$STAMP_FILE")" == "$(fingerprint)" ]]
}

write_stamp() {
  fingerprint > "$STAMP_FILE"
}

create_db() {
  local name
  name=$(ensure_name)
  if admin_psql -tAc "SELECT 1 FROM pg_database WHERE datname='${name}'" | grep -q 1; then
    return 0
  fi
  admin_psql -c "CREATE DATABASE \"${name}\""
}

drop_db() {
  if [[ ! -f "$NAME_FILE" ]]; then
    rm -f "$STAMP_FILE"
    return 0
  fi
  local name
  name=$(ensure_name)
  admin_psql -c "DROP DATABASE IF EXISTS \"${name}\"" || true
  rm -f "$NAME_FILE" "$STAMP_FILE"
}

ensure() {
  start_pg_if_needed
  create_db
  is_current && return 0

  local lock="$ROOT/.dev-pg-db.lock.d"
  while ! mkdir "$lock" 2>/dev/null; do sleep 0.2; done
  trap "rmdir '$lock'" EXIT

  if is_current; then
    rmdir "$lock"
    trap - EXIT
    return 0
  fi
  local url
  url=$(worktree_url)
  (
    cd "$ROOT/backend"
    DATABASE_URL="$url" uv run python manage.py migrate
    DATABASE_URL="$url" uv run python manage.py seed
  )
  write_stamp
  rmdir "$lock"
  trap - EXIT
}

case "${1:-}" in
  name) ensure_name ;;
  url) worktree_url ;;
  fingerprint) fingerprint ;;
  check) is_current ;;
  create) start_pg_if_needed && create_db ;;
  drop) drop_db ;;
  ensure) ensure ;;
  *)
    echo "usage: $0 {name|url|fingerprint|check|create|drop|ensure}" >&2
    exit 2
    ;;
esac
