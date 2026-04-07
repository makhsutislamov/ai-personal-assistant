#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

echo "[build-backend.sh] Building Python backend with PyInstaller..."

# Activate virtual environment
source "$BACKEND_DIR/.venv/bin/activate"

# Install PyInstaller if not already present (falls back for local dev outside CI)
if ! pyinstaller --version &>/dev/null 2>&1; then
  echo "[build-backend.sh] Installing PyInstaller..."
  pip install 'pyinstaller>=6.0'
fi

cd "$BACKEND_DIR"

# Build the backend as a single directory bundle
pyinstaller \
  --onedir \
  --name backend \
  --distpath dist \
  --clean \
  --noconfirm \
  app/main.py

echo "[build-backend.sh] Backend built successfully at $BACKEND_DIR/dist/backend/"
