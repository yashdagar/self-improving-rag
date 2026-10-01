#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
python3.11 -m venv .venv 2>/dev/null || uv venv --python 3.11 .venv
.venv/bin/python -m pip install -q -r backend/requirements-dev.txt 2>/dev/null \
  || VIRTUAL_ENV=.venv uv pip install -q -r backend/requirements-dev.txt
(cd frontend && npm install)
git config core.hooksPath .githooks
