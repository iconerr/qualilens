#!/bin/bash
# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0
#
# Build a clean, shareable, SIGNED QualiLens bundle.
#
# The bundle is built from an EXPLICIT manifest of application files — never
# from "everything except…". Anything you add to this folder later (drafts,
# memos, transcripts, data) is excluded by construction, not by remembering
# to list it. The zip contains everything a recipient needs, including the
# pre-built interface (no Node required), and nothing personal.
#
# Freshness: the interface is rebuilt whenever its sources differ from what
# dist/ was built from (a fingerprint stamped into dist/index.html at build
# time), and the manual is rebuilt every time. A bundle can no longer ship an
# interface older than its own source.
#
# Signing: every file in the bundle is hashed into MANIFEST.sha256, which is
# signed (Ed25519) with the release key into MANIFEST.sig. The in-app updater
# refuses bundles that are unsigned, signed by another key, or altered. The
# key is read from $QUALILENS_SIGNING_KEY, defaulting to the authors' private
# key store outside this folder, and never ships. Without it the bundle is
# still produced — for tests and for colleagues who will unzip and run it
# directly — but it is UNSIGNED and the updater will refuse it, which this
# script says out loud.
set -e
CALLER_PWD="$PWD"
cd "$(dirname "$0")"

# ---- Python for the build helpers (fingerprint, manual, signing) ----
PY="${QUALILENS_PYTHON:-}"
if [ -z "$PY" ] && [ -x backend/.venv/bin/python ]; then PY="backend/.venv/bin/python"; fi
if [ -z "$PY" ]; then PY="$(command -v python3 || true)"; fi
[ -n "$PY" ] || { echo "python3 is needed to build a bundle." >&2; exit 1; }

# ---- interface: rebuild when its sources differ from what dist was built from ----
need_build=0
if [ ! -f frontend/dist/index.html ]; then
  need_build=1
else
  CURRENT_FP="$("$PY" -c 'import sys; sys.path.insert(0,"backend"); from app.buildinfo import frontend_source_fingerprint as f; print(f("frontend"))')"
  BUILT_FP="$(sed -n 's/.*<meta name="ql-src" content="\([0-9a-f]*\)".*/\1/p' frontend/dist/index.html | head -1)"
  if [ -z "$BUILT_FP" ] || [ "$BUILT_FP" != "$CURRENT_FP" ]; then need_build=1; fi
fi
if [ "$need_build" = 1 ]; then
  command -v npm >/dev/null 2>&1 || { echo "npm is needed to build the interface before packaging (the built interface is missing or older than its sources)." >&2; exit 1; }
  NODE_MAJOR="$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)"
  if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 18 ] 2>/dev/null; then
    echo "Node.js 18 or newer is required (found $(node -v 2>/dev/null || echo 'none'))." >&2; exit 1
  fi
  echo "Building the interface (sources changed since the last build)…"
  # npm install is a no-op in a second when nothing changed, and the only
  # correct move when package.json gained a dependency (the bundled fonts did)
  (cd frontend && npm install --loglevel=warn --no-fund --no-audit) || { echo "JavaScript dependency installation failed." >&2; exit 1; }
  (cd frontend && npm run build) || { echo "Frontend build failed." >&2; exit 1; }
fi

# ---- manual: always rebuilt from its sources (cheap, deterministic) ----
"$PY" manual/build_manual.py >/dev/null || { echo "Manual build failed." >&2; exit 1; }

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
  RELEASE
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
# and name the release: the first versioned heading in CHANGELOG.md ("## 1.6.3 — date").
# "unreleased" when the top entry is still "## Unreleased" (a test or interim bundle),
# so the app never claims a version that was not cut. A recipient's folder has no
# CHANGELOG; its RELEASE came with the bundle and is kept.
if [ -f CHANGELOG.md ]; then
  RELEASE="$(sed -n -E '/^## Unreleased/q; s/^## ([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' CHANGELOG.md | head -1)"
  printf '%s' "${RELEASE:-unreleased}" > RELEASE
elif [ ! -f RELEASE ]; then
  printf 'unknown' > RELEASE
fi

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
find "$STAGE" \( -name '*.bak' -o -name '*.orig' -o -name '*~' \) -type f -delete 2>/dev/null || true
# the shipped .gitignore must not name private files that never ship
if grep -q '^# Private files' "$STAGE/.gitignore" 2>/dev/null; then
  sed -i.bak '/^# Private files/,$d' "$STAGE/.gitignore" && rm -f "$STAGE/.gitignore.bak"
fi

# refuse to package if anything sensitive slipped into an included tree
if find "$STAGE" -name 'qualilens.db*' -o -name '*.venv*' -o -name 'release-signing*' | grep -q .; then
  echo "Refusing to package: a database, environment, or key file is inside an included tree." >&2
  rm -rf "$STAGE_PARENT"; exit 1
fi

# ---- sign ----
KEY="${QUALILENS_SIGNING_KEY:-$HOME/.qualilens/release-signing.key}"
SIGNED=0
if [ -f "$KEY" ]; then
  if "$PY" -c 'import cryptography' >/dev/null 2>&1; then
    "$PY" "$STAGE/backend/app/signing.py" sign "$STAGE" "$KEY" >/dev/null \
      || { echo "Signing failed." >&2; rm -rf "$STAGE_PARENT"; exit 1; }
    SIGNED=1
  else
    echo "WARNING: the 'cryptography' package is not available to $PY — bundle NOT signed." >&2
  fi
else
  echo "WARNING: no signing key at $KEY — bundle NOT signed; the in-app updater will refuse it." >&2
fi

( cd "$STAGE_PARENT" && rm -f "$OUT" && zip -qry "$OUT" "QualiLens" )
rm -rf "$STAGE_PARENT"

[ -f "$OUT" ] || { echo "Packaging failed: $OUT was not created." >&2; exit 1; }
echo "Shareable bundle written to: $OUT"
if [ "$SIGNED" = 1 ]; then
  echo "Signed (verify: $PY backend/app/signing.py verify \"$OUT\")"
else
  echo "UNSIGNED bundle: fine to unzip and run, but Settings → Update will refuse it."
fi
echo "Recipients need only Python 3.11+ — they unzip and run ./run.sh"
echo "Included: the application files listed in package.sh's manifest, nothing else."
