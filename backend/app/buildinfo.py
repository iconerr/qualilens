# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Fingerprint of the frontend sources.

frontend/vite.config.ts computes the same value at build time (same file
set, same order, same byte stream) and stamps it into dist/index.html as
<meta name="ql-src">. The server compares the two at startup and the
packaging test compares them inside a bundle, so a dist built from older
sources than the ones beside it can no longer ship unnoticed.
"""

import hashlib
from pathlib import Path

# files and trees that make up the interface, relative to frontend/
FINGERPRINT_FILES = ("index.html", "package.json", "package-lock.json",
                     "vite.config.ts", "tsconfig.json", "tsconfig.app.json",
                     "tsconfig.node.json")
FINGERPRINT_TREES = ("src", "public")
# written by manual/build_manual.py, not part of the compiled interface
FINGERPRINT_EXCLUDE = ("public/manual.html",)


def frontend_source_fingerprint(frontend_dir: Path) -> str:
    """sha256 over (relative POSIX path, contents) of every interface source
    file in sorted path order; '' when the folder is not a frontend."""
    root = Path(frontend_dir)
    if not (root / "index.html").exists():
        return ""
    files = []
    for name in FINGERPRINT_FILES:
        p = root / name
        if p.is_file():
            files.append(p)
    for tree in FINGERPRINT_TREES:
        d = root / tree
        if d.is_dir():
            files.extend(p for p in d.rglob("*") if p.is_file())
    rels = sorted(
        (p.relative_to(root).as_posix(), p) for p in files
        if p.relative_to(root).as_posix() not in FINGERPRINT_EXCLUDE)
    h = hashlib.sha256()
    for rel, p in rels:
        h.update(rel.encode("utf-8") + b"\n")
        h.update(p.read_bytes())
        h.update(b"\n")
    return h.hexdigest()[:16]
