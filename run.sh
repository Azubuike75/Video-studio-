#!/usr/bin/env bash
# Video Studio launcher (macOS/Linux)
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Setting up virtual environment (first run only)..."
  python3 -m venv venv
  ./venv/bin/pip install --upgrade pip >/dev/null
  ./venv/bin/pip install -r requirements.txt
fi

./venv/bin/python3 app.py
