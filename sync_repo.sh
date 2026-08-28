#!/bin/bash
# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0
#
# Publish the application to the public git repository.
#
# The repository tree is produced from package.sh's staging — the SAME
# explicit manifest that builds the shareable bundle — so what is public is
# exactly what recipients get, curated by one authority. Private material
# (backend/data with your keys, FINGERPRINT.md, devnotes/, transcripts,
# memos) is excluded by construction: it is not on the manifest, so it never
# enters the staging, the repo directory, or the history.
#
# Two departures from the bundle:
#   - frontend/dist is omitted (the repo tracks source; the runnable build
#     travels in each release's QualiLens.zip asset instead), per .gitignore.
#   - repo-facing files ride along: CHANGELOG.md, CONTRIBUTING.md, the CI
#     workflow, and this script.
#
# Before every commit, the tree is scanned for anything credential-shaped
# and for data paths; a hit refuses the commit outright. No exceptions.
#
# Usage: ./sync_repo.sh "commit message" [existing-bundle.zip]
# Pass an existing bundle when cutting a release, so the repo, the release
# asset, and the VERSION stamp inside it are one and the same build —
# otherwise a fresh staging is packaged (which re-stamps VERSION).
# The repo working copy lives OUTSIDE Dropbox (git and sync clients corrupt
# each other): $QUALILENS_REPO_DIR, default ~/Code/qualilens.
set -e
cd "$(dirname "$0")"
REPO_DIR="${QUALILENS_REPO_DIR:-$HOME/Code/qualilens}"
MSG="${1:?usage: ./sync_repo.sh \"commit message\" [bundle.zip]}"
BUNDLE="${2:-}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if [ -n "$BUNDLE" ]; then
  [ -f "$BUNDLE" ] || { echo "No such bundle: $BUNDLE" >&2; exit 1; }
  cp "$BUNDLE" "$TMP/bundle.zip"
else
  ./package.sh "$TMP/bundle.zip" >/dev/null
fi
unzip -q "$TMP/bundle.zip" -d "$TMP"
STAGE="$TMP/QualiLens"

rm -rf "$STAGE/frontend/dist"
for extra in CHANGELOG.md CONTRIBUTING.md sync_repo.sh; do
  cp "$extra" "$STAGE/$extra"
done
mkdir -p "$STAGE/.github/workflows"
cp .github/workflows/tests.yml "$STAGE/.github/workflows/tests.yml"

mkdir -p "$REPO_DIR"
if [ ! -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" init -b main >/dev/null
fi
rsync -a --delete --exclude '.git' "$STAGE/" "$REPO_DIR/"

# ---- refusal gate: nothing key-shaped, no data paths. No exceptions. ----
if grep -RInE --binary-files=without-match --exclude-dir=.git \
    'sk-(ant|proj)-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY' \
    "$REPO_DIR"; then
  echo "REFUSING to commit: the text above looks like a credential." >&2
  exit 1
fi
if find "$REPO_DIR" \( -name 'qualilens.db*' -o -name '*.venv*' \
    -o -path '*backend/data*' -o -name 'FINGERPRINT.md' -o -path '*devnotes*' \) \
    | grep -q .; then
  echo "REFUSING to commit: a database, data path, or private file is in the repo tree." >&2
  exit 1
fi

cd "$REPO_DIR"
git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit — the repo already matches the manifest."
else
  git commit -q -m "$MSG"
  echo "Committed: $MSG"
fi
if git remote get-url origin >/dev/null 2>&1; then
  git push -q -u origin main
  echo "Pushed to $(git remote get-url origin)"
else
  echo "No remote yet — create one with:"
  echo "  cd $REPO_DIR && gh repo create qualilens --private --source=. --remote=origin --push"
fi
