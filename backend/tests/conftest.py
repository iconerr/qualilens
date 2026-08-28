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
