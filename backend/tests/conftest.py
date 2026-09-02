# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Test setup: point the app at a scratch database BEFORE app.main is
imported, so tests never touch the researcher's real qualilens.db."""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import app.db as db  # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="qualilens_test_")
db.DB_PATH = pathlib.Path(_tmpdir) / "test.db"
db.UPLOADS_DIR = pathlib.Path(_tmpdir) / "uploads"
db.UPLOADS_DIR.mkdir(exist_ok=True)
os.environ["QUALILENS_TEST"] = "1"

import pytest  # noqa: E402

_VERSION_FILE = pathlib.Path(__file__).resolve().parent.parent.parent / "VERSION"


@pytest.fixture(autouse=True)
def _keep_the_trees_build_stamp():
    """Tests that run package.sh re-stamp VERSION in the working tree, and a
    test build is not a release: the tree must keep the stamp of the build it
    actually is (the one the updater and the launcher compare against)."""
    before = _VERSION_FILE.read_text() if _VERSION_FILE.exists() else None
    yield
    if before is not None and _VERSION_FILE.read_text() != before:
        _VERSION_FILE.write_text(before)
