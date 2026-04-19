#!/usr/bin/env bash

cleanup() {
  echo "🧹 Shutting down..."
  kill 0
}
trap cleanup EXIT

echo "🚀 Starting backend..."
make run &

sleep 2

echo "⚛️  Starting Vite..."
cd frontend
pnpm dev