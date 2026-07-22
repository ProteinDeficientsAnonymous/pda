#!/usr/bin/env bash

cleanup() {
  echo "🧹 Shutting down..."
  kill 0
}
trap cleanup EXIT

# bind (not connect) so an occupied port fails instantly, no timeout
port="${BACKEND_PORT:-8000}"
port_free() {
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('127.0.0.1', int(sys.argv[1])))
except OSError:
    sys.exit(1)
" "$1"
}
while ! port_free "$port"; do
  port=$((port + 1))
done
export BACKEND_PORT="$port"

echo "🚀 Starting backend on port $BACKEND_PORT..."
make "${RUN_TARGET:-run}" &

sleep 2

echo "⚛️  Starting Vite..."
cd frontend
pnpm dev