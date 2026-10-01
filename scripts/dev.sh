#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
(cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID' EXIT
cd frontend && npm run dev
