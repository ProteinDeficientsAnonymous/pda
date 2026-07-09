#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME_FILE="$ROOT/.dev-pg-db-name"
LOCK_DIR="$ROOT/.dev-pg-db.lock.d"

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

docker_psql() {
  docker compose -f "$ROOT/docker-compose.yml" exec -T db psql -U pda -d postgres -v ON_ERROR_STOP=1 "$@"
}

with_lock() {
  while ! mkdir "$LOCK_DIR" 2>/dev/null; do sleep 0.2; done
  trap 'rmdir "$LOCK_DIR"' EXIT
  "$@"
}

cmd_create() {
  local name
  name=$(ensure_name)
  if docker_psql -tAc "SELECT 1 FROM pg_database WHERE datname='${name}'" | grep -q 1; then
    return 0
  fi
  docker_psql -c "CREATE DATABASE \"${name}\""
}

cmd_drop() {
  local name
  if [[ ! -f "$NAME_FILE" ]]; then
    return 0
  fi
  name=$(ensure_name)
  docker_psql -c "DROP DATABASE IF EXISTS \"${name}\"" || true
  rm -f "$NAME_FILE"
}

case "${1:-}" in
  name) ensure_name ;;
  url) worktree_url ;;
  create) with_lock cmd_create ;;
  drop) with_lock cmd_drop ;;
  *)
    echo "usage: $0 {name|url|create|drop}" >&2
    exit 1
    ;;
esac
