#!/bin/bash
# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0
#
# QualiLens launcher — builds the frontend if needed, starts the local server,
# and opens the app in your browser.
set -e
cd "$(dirname "$0")"

fail() { echo ""; echo "ERROR: $1" >&2; exit 1; }

# ---- Pre-flight: Python 3.11+ ----

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

# ---- Pre-flight: disk space ----

check_disk_space() {
  local avail_kb
  if command -v df >/dev/null 2>&1; then
    avail_kb="$(df -k "$(pwd)" | awk 'NR==2 {print $4}')"
    if [ -n "$avail_kb" ] && [ "$avail_kb" -lt 512000 ] 2>/dev/null; then
      fail "Less than 500 MB of disk space available. Free some space and try again."
    fi
  fi
}

check_disk_space

# ---- Python environment ----

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
    PY="$(find_python)" || fail "QualiLens needs Python 3.11 or newer (none found).
  Install it from https://www.python.org/downloads/
  macOS Homebrew: brew install python@3.12"
    echo "Creating Python environment with $PY (first run only)…"
    "$PY" -m venv backend/.venv || fail "Could not create the Python environment. Check that Python is installed correctly."
  fi
  echo "Installing Python dependencies…"
  backend/.venv/bin/python -m pip -q install -r backend/requirements.txt \
    || fail "Python dependency installation failed. Check your internet connection and try again."
fi

# an app update can change requirements.txt — reinstall when it differs from
# what this environment was built against
REQ_SHA="$(shasum backend/requirements.txt | cut -d' ' -f1)"
if [ "$REQ_SHA" != "$(cat backend/.venv/req.sha 2>/dev/null)" ]; then
  echo "Dependencies changed — updating the Python environment…"
  backend/.venv/bin/python -m pip -q install -r backend/requirements.txt \
    || fail "Python dependency update failed."
  printf '%s' "$REQ_SHA" > backend/.venv/req.sha
fi

# ---- Frontend build (GitHub clones only; bundles ship with dist/) ----

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null 2>&1 \
    || fail "The pre-built interface is not included (this is normal for a GitHub clone).
  QualiLens needs Node.js to build it once. Install Node 18+ from https://nodejs.org
  then run ./run.sh again."

  # Check Node version (18+ required for TypeScript 6 and React 19)
  NODE_MAJOR="$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)"
  if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 18 ] 2>/dev/null; then
    fail "Node.js 18 or newer is required (found $(node -v 2>/dev/null || echo 'none')).
  Install from https://nodejs.org"
  fi

  echo "Building the interface (first run only — this takes about a minute)…"

  echo "  Installing JavaScript dependencies…"
  (cd frontend && npm install --loglevel=warn) \
    || fail "JavaScript dependency installation failed.
  Check your internet connection and available disk space, then try:
    cd frontend && rm -rf node_modules && npm install"

  echo "  Compiling…"
  (cd frontend && npm run build) \
    || fail "Frontend build failed.
  Try: cd frontend && rm -rf node_modules && npm install && npm run build
  If the problem persists, open an issue at https://github.com/iconerr/qualilens/issues"

  echo "  Done."
fi

# ---- Launch ----

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

echo ""
echo "QualiLens running at http://127.0.0.1:$PORT  (Ctrl-C to stop)"
(sleep 1.5 && open_browser "http://127.0.0.1:$PORT") &
cd backend && exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
