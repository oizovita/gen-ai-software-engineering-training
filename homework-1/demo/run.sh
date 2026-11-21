#!/usr/bin/env bash
# Start the Banking Transactions API on http://localhost:3000
#
# Usage:
#   ./demo/run.sh                 # start with an empty store
#   SEED=1 ./demo/run.sh          # start pre-loaded with demo/sample-data.json
#   PORT=8080 ./demo/run.sh       # use a different port
#
# The script creates a .venv (if missing), installs requirements and runs uvicorn.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-3000}"
VENV="$ROOT/.venv"

pick_python() {
  for candidate in python3.13 python3.12 python3.14 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done
  echo "python3 not found in PATH" >&2
  exit 1
}

if [ ! -x "$VENV/bin/python" ]; then
  PY="$(pick_python)"
  echo "➜ Creating virtualenv with $PY ..."
  "$PY" -m venv "$VENV"
fi

echo "➜ Installing dependencies ..."
if ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi
if "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r requirements.txt
elif command -v uv >/dev/null 2>&1; then
  uv pip install --quiet --python "$VENV/bin/python" -r requirements.txt
else
  echo "pip is not available in $VENV and uv is not installed" >&2
  exit 1
fi

if [ "${SEED:-0}" = "1" ]; then
  export SEED_FILE="$ROOT/demo/sample-data.json"
  echo "➜ Seeding from $SEED_FILE"
fi

echo "➜ Starting API on http://localhost:$PORT  (Swagger UI: http://localhost:$PORT/docs)"
exec "$VENV/bin/uvicorn" src.app:app --host 0.0.0.0 --port "$PORT"
