#!/usr/bin/env bash
# Helper script to kill any process on the chosen port and start the FastAPI backend.
# Usage: ./start_backend.sh [port]
# Defaults to port 8000 if none is provided.

PORT=${1:-8000}

# ensure we're in the backend directory
cd "$(dirname "$0")"

echo "🔄 clearing port $PORT if occupied..."
lsof -ti :$PORT | xargs kill -9 2>/dev/null || true

export BACKEND_PORT=$PORT

# run through python entrypoint which also kills the port as a safety net
python3 main.py
