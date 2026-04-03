#!/usr/bin/env bash

cleanup() {
  echo "🧹 Shutting down..."
  kill 0
}
trap cleanup EXIT

echo "🚀 Starting backend..."
make run &

sleep 2

echo "🎨 Starting Flutter..."
cd frontend

# Choose device: chrome if available, otherwise fallback
if flutter devices | grep -q "Chrome"; then
  DEVICE="chrome"
  echo "Using Chrome for Flutter web"
else
  DEVICE="web-server"
  echo "⚠️ Chrome not found, falling back to web-server (limited hot reload)"
fi

flutter run -d $DEVICE \
  --web-port 3000 \
  ${CHROME_EXECUTABLE:+--web-browser-executable="$CHROME_EXECUTABLE"} \
  --dart-define=ENABLE_FEEDBACK=${ENABLE_FEEDBACK:-true} \
  --dart-define=GIT_SHA=$(git rev-parse --short HEAD)
