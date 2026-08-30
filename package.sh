#!/bin/bash
# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0
#
# Build a clean, shareable QualiLens bundle.
#
# The bundle is built from an EXPLICIT manifest of application files — never
# from "everything except…". Anything you add to this folder later (drafts,
# memos, transcripts, data) is excluded by construction, not by remembering
# to list it. The zip contains everything a recipient needs, including the
# pre-built interface (no Node required), and nothing personal.
set -e
CALLER_PWD="$PWD"
cd "$(dirname "$0")"

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null 2>&1 || { echo "npm is needed to build the interface before packaging." >&2; exit 1; }
  NODE_MAJOR="$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)"
  if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 18 ] 2>/dev/null; then
    echo "Node.js 18 or newer is required (found $(node -v 2>/dev/null || echo 'none'))." >&2; exit 1
  fi
  echo "Building the interface…"
  (cd frontend && npm install --loglevel=warn && npm run build) \
    || { echo "Frontend build failed." >&2; exit 1; }
fi

RELEASE_DIR="$(dirname "$0")/../release-packages"
mkdir -p "$RELEASE_DIR"
BUILD_STAMP="$(date '+%Y.%m.%d-%H%M')"
OUT="${1:-$RELEASE_DIR/QualiLens-${BUILD_STAMP}.zip}"
case "$OUT" in
  /*) ;;                       # already absolute
  *) OUT="$CALLER_PWD/$OUT" ;; # resolve relative to where the user ran us
esac

STAGE_PARENT="$(mktemp -d)"
STAGE="$STAGE_PARENT/QualiLens"
mkdir -p "$STAGE"

# ---- the manifest: application files only ----
MANIFEST=(
  VERSION
  run.sh
  package.sh
  LICENSE
  NOTICE
  CITATION.cff
  README.md
  .gitignore
  backend/requirements.txt
  backend/app
  backend/tests
  frontend/index.html
  frontend/package.json
  frontend/package-lock.json
  frontend/tsconfig.json
  frontend/tsconfig.app.json
  frontend/tsconfig.node.json
  frontend/vite.config.ts
  frontend/public
  frontend/src
  frontend/dist
  manual
)

# stamp this build so recipients (and the in-app updater) can tell versions apart
printf '%s' "$BUILD_STAMP" > VERSION

for item in "${MANIFEST[@]}"; do
  if [ -e "$item" ]; then
    mkdir -p "$STAGE/$(dirname "$item")"
    cp -R "$item" "$STAGE/$item"
  fi
done

# strip caches that live inside the included trees
find "$STAGE" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.DS_Store' -delete 2>/dev/null || true

# refuse to package if anything sensitive slipped into an included tree
if find "$STAGE" -name 'qualilens.db*' -o -name '*.venv*' | grep -q .; then
  echo "Refusing to package: a database or environment file is inside an included tree." >&2
  rm -rf "$STAGE_PARENT"; exit 1
fi

( cd "$STAGE_PARENT" && rm -f "$OUT" && zip -qry "$OUT" "QualiLens" )
rm -rf "$STAGE_PARENT"

[ -f "$OUT" ] || { echo "Packaging failed: $OUT was not created." >&2; exit 1; }
echo "Shareable bundle written to: $OUT"
echo "Recipients need only Python 3.11+ — they unzip and run ./run.sh"
echo "Included: the application files listed in package.sh's manifest, nothing else."
