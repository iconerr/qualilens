#!/bin/bash
# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0
#
# QualiLens launcher — builds the frontend if needed, starts the local server,
# and opens the app in your browser.
set -e
cd "$(dirname "$0")"

# Find a suitable Python (3.11+): prefer explicit versions, fall back to python3
find_python() {
  for cand in python3.13 python3.12 python3.11 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
      if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
        command -v "$cand"
        return 0
      fi
    fi
  done
  return 1
}

# A venv is tied to the machine AND path that created it. Probe it by actually
# importing the app's server package through the venv's own interpreter — a
# venv copied from another machine (or a renamed folder) fails this and is
# rebuilt. Never invoke the venv's console scripts (their shebangs hardcode
# the original absolute path); always go through `python -m`.
if [ -d backend/.venv ] && ! backend/.venv/bin/python -c 'import uvicorn' >/dev/null 2>&1; then
  echo "The bundled Python environment does not work on this machine/path — rebuilding it…"
  rm -rf backend/.venv
fi

if [ ! -d backend/.venv ] || ! backend/.venv/bin/python -c 'import uvicorn' >/dev/null 2>&1; then
  if [ ! -d backend/.venv ]; then
    PY="$(find_python)" || { echo "QualiLens needs Python 3.11 or newer (none found). Install it from https://www.python.org/downloads/ (macOS Homebrew: brew install python@3.12)." >&2; exit 1; }
    echo "Creating Python environment with $PY (first run only)…"
    "$PY" -m venv backend/.venv
  fi
  backend/.venv/bin/python -m pip -q install -r backend/requirements.txt
fi

# an app update can change requirements.txt — reinstall when it differs from
# what this environment was built against
REQ_SHA="$(shasum backend/requirements.txt | cut -d' ' -f1)"
if [ "$REQ_SHA" != "$(cat backend/.venv/req.sha 2>/dev/null)" ]; then
  echo "Dependencies changed — updating the Python environment…"
  backend/.venv/bin/python -m pip -q install -r backend/requirements.txt
  printf '%s' "$REQ_SHA" > backend/.venv/req.sha
fi

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null 2>&1 || { echo "QualiLens needs Node/npm to build its interface once. Install from https://nodejs.org" >&2; exit 1; }
  echo "Building frontend (first run only)…"
  (cd frontend && npm install --silent && npm run build)
fi

PORT="${QUALILENS_PORT:-8765}"
if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use (is QualiLens already running?)." >&2
  echo "Open http://127.0.0.1:$PORT — or set QUALILENS_PORT to another port." >&2
  exit 1
fi

open_browser() {
  if command -v open >/dev/null 2>&1; then open "$1"        # macOS
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1"  # Linux
  else echo "Open $1 in your browser."
  fi
}

echo "QualiLens running at http://127.0.0.1:$PORT  (Ctrl-C to stop)"
(sleep 1.5 && open_browser "http://127.0.0.1:$PORT") &
cd backend && exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
