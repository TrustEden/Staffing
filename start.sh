#!/usr/bin/env bash
set -euo pipefail

# Backend setup
echo "Starting backend..."
if [ ! -d "backend/venv" ]; then
  python -m venv backend/venv
fi
source backend/venv/bin/activate
pip install -r backend/requirements.txt
uvicorn main:app --reload --app-dir backend
