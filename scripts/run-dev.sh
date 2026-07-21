#!/usr/bin/env bash
# Start the FastAPI app for local development (macOS / Linux).
set -euo pipefail

HOST_ADDRESS="${HOST_ADDRESS:-127.0.0.1}"
PORT="${PORT:-8080}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOST_ADDRESS="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    echo "Virtual environment not found at $PYTHON" >&2
    echo "Create it with: python3 -m venv .venv && .venv/bin/python -m pip install -r backend/requirements.txt" >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo ".env not found. Copy .env.example to .env and set SECRET_KEY and DATABASE_URL." >&2
    exit 1
fi

"$PYTHON" -m alembic upgrade head

echo "Tan Thuan Port declaration app (FastAPI)"
echo "Open: http://${HOST_ADDRESS}:${PORT}"
echo "Press Ctrl+C to stop."

exec "$PYTHON" -m uvicorn backend.app:app --host "$HOST_ADDRESS" --port "$PORT" --reload
