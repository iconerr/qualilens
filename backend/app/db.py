# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""SQLite persistence layer.

One database file holds all projects. Every table that participates in the
audit trail (codes, excerpts, checkpoints, events) is append-preserving:
user edits at checkpoints are recorded as events rather than silently
overwriting history.
"""

import atexit
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "qualilens.db"
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

_local = threading.local()

# Build lineage of this QualiLens distribution (see the project NOTICE).
LINEAGE = "ql-a2f4467befc3477b9caea1866a2af37e"
# SQLite application_id: the four bytes 'QLns', stamped into every database
# file this application creates (standard SQLite file-type identification).
APPLICATION_ID = 0x514C6E73

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    method TEXT NOT NULL,
    config TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    filename TEXT NOT NULL,
    kind TEXT NOT NULL,              -- text | audio | video
    status TEXT NOT NULL,            -- pending | transcribing | ready | error
    grp TEXT,                        -- optional group label (content analysis)
    text TEXT,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    status TEXT NOT NULL,            -- running | awaiting_review | completed | failed | cancelled
    stage_index INTEGER NOT NULL DEFAULT 0,
    stage_name TEXT,
    progress TEXT NOT NULL DEFAULT '{}',   -- {done, total, detail}
    state TEXT NOT NULL DEFAULT '{}',      -- intermediate artifacts between stages
    error TEXT,
    usage TEXT NOT NULL DEFAULT '{}',      -- accumulated token usage / cost
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS codes (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    name TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '',
    stage TEXT NOT NULL,             -- open_code | category | theme | codebook | core
    parent_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',   -- active | merged | deleted
    merged_into TEXT,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS excerpts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    code_id TEXT NOT NULL REFERENCES codes(id),
    source_id TEXT NOT NULL REFERENCES sources(id),
    quote TEXT NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    memo TEXT NOT NULL DEFAULT '',
    confidence REAL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    stage TEXT NOT NULL,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | resolved
    resolution TEXT,
    created_at REAL NOT NULL,
    resolved_at REAL
);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    ts REAL NOT NULL,
    kind TEXT NOT NULL,              -- stage | llm | user_decision | error | info
    message TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS reports (
    run_id TEXT PRIMARY KEY REFERENCES runs(id),
    payload TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sources_project ON sources(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
CREATE INDEX IF NOT EXISTS idx_codes_run ON codes(run_id);
CREATE INDEX IF NOT EXISTS idx_excerpts_run ON excerpts(run_id);
CREATE INDEX IF NOT EXISTS idx_excerpts_code ON excerpts(code_id);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id);
"""


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
        _local.conn = conn
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    if not get_setting("lineage"):
        set_setting("lineage", LINEAGE)
    # This database may live in a cloud-synced folder (e.g. Dropbox). Keep the
    # WAL sidecar file empty whenever we can so the at-rest state syncs as a
    # single coherent file: fold the WAL into the main DB at startup and exit.
    checkpoint_wal()
    atexit.register(checkpoint_wal)


def checkpoint_wal() -> None:
    try:
        get_conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:
        pass  # best-effort hygiene; never block startup/shutdown on it


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return time.time()


# ---------- small helpers ----------

def row_to_dict(row: sqlite3.Row, json_fields: tuple = ()) -> dict:
    d = dict(row)
    for f in json_fields:
        if f in d and isinstance(d[f], str):
            try:
                d[f] = json.loads(d[f])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def get_setting(key: str, default: str = "") -> str:
    row = get_conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def log_event(run_id: str, kind: str, message: str, payload: dict | None = None) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO events(id,run_id,ts,kind,message,payload) VALUES(?,?,?,?,?,?)",
        (new_id(), run_id, now(), kind, message, json.dumps(payload or {})),
    )
    conn.commit()
