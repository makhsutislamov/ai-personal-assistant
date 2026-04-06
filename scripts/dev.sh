#!/usr/bin/env bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$FRONTEND_PID" "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start frontend
npm run dev:frontend &
FRONTEND_PID=$!
echo "[dev] Frontend started (pid $FRONTEND_PID)"

# Start backend
npm run dev:backend &
BACKEND_PID=$!
echo "[dev] Backend started (pid $BACKEND_PID)"

# Wait for backend to be ready
echo "[dev] Waiting for backend..."
for i in $(seq 1 20); do
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "[dev] Backend is ready"
    break
  fi
  sleep 0.5
done

# Start Electron (foreground — closing the window exits the script)
npm run dev:electron
