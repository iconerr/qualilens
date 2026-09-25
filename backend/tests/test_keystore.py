# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""API keys at rest: encrypted in the database with a secret held outside
the data folder; the folder and the database private to this account;
removed values scrubbed from the file rather than left in freed space."""

import stat

from cryptography.fernet import Fernet
from starlette.testclient import TestClient

import app.db as db
import app.keystore as keystore
from app.main import app, SESSION_TOKEN

AUTH = {"X-QualiLens-Token": SESSION_TOKEN}
client = TestClient(app, base_url="http://127.0.0.1", headers=AUTH)

KEY = "test-key-anthropic-0123456789abcdefghijklmnopqrstuvwxyz-ZZZZ"   # not credential-shaped: the commit gate refuses sk- prefixes


def _raw(provider: str) -> str:
    return db.get_setting(f"api_key_{provider}")


def _file_bytes() -> bytes:
    """Everything on disk for the database: the main file and its sidecars."""
    out = b""
    for suffix in ("", "-wal", "-shm"):
        f = db.DB_PATH.with_name(db.DB_PATH.name + suffix)
        if f.exists():
            out += f.read_bytes()
    return out


def _mode(path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_key_is_encrypted_at_rest_and_round_trips():
    r = client.put("/api/settings/keys", json={"anthropic": KEY})
    assert r.status_code == 200
    st = r.json()["anthropic"]
    assert st["has_key"] is True and st["problem"] == ""
    assert st["key_hint"] == KEY[:6] + "…" + KEY[-4:]
    # the row holds ciphertext, the API hands back the plaintext to callers
    # inside the process, and the plaintext is nowhere in the files on disk
    assert _raw("anthropic").startswith(keystore.PREFIX)
    assert keystore.get_api_key("anthropic") == KEY
    assert KEY.encode() not in _file_bytes()
    # the interface never receives the key itself
    body = client.get("/api/settings").json()
    assert KEY not in str(body)
    assert client.get("/api/meta").json()["providers"][0]["has_key"] in (True, False)


def test_plaintext_rows_from_older_builds_are_encrypted_and_scrubbed():
    legacy = "test-key-legacy-plaintext-row-1234567890abcdefghijklmnop"
    db.set_setting("api_key_mistral", legacy)      # what a build before 1.8 wrote
    assert legacy.encode() in _file_bytes()
    assert keystore.migrate_plaintext() == 1
    assert _raw("mistral").startswith(keystore.PREFIX)
    assert keystore.get_api_key("mistral") == legacy
    assert legacy.encode() not in _file_bytes(), "plaintext lingered after migration"
    assert keystore.migrate_plaintext() == 0        # idempotent


def test_a_plaintext_row_read_later_is_encrypted_in_place():
    legacy = "test-key-legacy-read-path-1234567890abcdefghijklmnopqrstuv"
    db.set_setting("api_key_google", legacy)
    assert keystore.get_api_key("google") == legacy
    assert _raw("google").startswith(keystore.PREFIX)
    assert legacy.encode() not in _file_bytes()


def test_remove_empties_the_row_and_scrubs_the_ciphertext():
    client.put("/api/settings/keys", json={"openai": KEY})
    token = _raw("openai")
    assert token.startswith(keystore.PREFIX)
    r = client.put("/api/settings/keys", json={"openai": "__clear__"})
    st = r.json()["openai"]
    assert st == {"has_key": False, "key_hint": "", "problem": ""}
    assert _raw("openai") == ""
    assert token.encode() not in _file_bytes(), "removed value lingered in the file"


def test_a_database_from_another_computer_reports_its_keys_unreadable():
    client.put("/api/settings/keys", json={"anthropic": KEY})
    original = keystore.SECRET_FILE.read_bytes()
    try:
        keystore.SECRET_FILE.write_bytes(Fernet.generate_key() + b"\n")   # a different secret
        keystore.reload()
        st = client.get("/api/settings").json()["anthropic"]
        assert st["has_key"] is False and st["key_hint"] == ""
        assert "another computer" in st["problem"]
        assert keystore.get_api_key("anthropic") == ""
        assert client.get("/api/meta").json()["providers"]      # still serves
        r = client.post("/api/settings/check_models", json={"provider": "anthropic"})
        assert "another computer" in r.json()["anthropic"]["error"]
        # pasting the key again makes it readable with the new secret
        st = client.put("/api/settings/keys", json={"anthropic": KEY}).json()["anthropic"]
        assert st["has_key"] is True and st["problem"] == ""
    finally:
        keystore.SECRET_FILE.write_bytes(original)
        keystore.reload()
    # the row now carries the other secret's ciphertext: unreadable again
    # with the original secret, and Remove clears it
    assert client.get("/api/settings").json()["anthropic"]["has_key"] is False
    client.put("/api/settings/keys", json={"anthropic": "__clear__"})
    assert client.get("/api/settings").json()["anthropic"]["problem"] == ""


def test_secret_that_cannot_be_created_is_reported_not_fatal(tmp_path, monkeypatch):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("a file where the secret's folder should be")
    monkeypatch.setattr(keystore, "SECRET_FILE", blocker / "secret.key")
    keystore.reload()
    try:
        assert "could not be created" in keystore.secret_problem()
        meta = client.get("/api/meta").json()
        assert meta["secret_problem"] and meta["secret_file"] == str(blocker / "secret.key")
        r = client.put("/api/settings/keys", json={"mistral": KEY})
        assert r.status_code == 500 and "could not be created" in r.json()["detail"]
    finally:
        keystore.reload()


def test_meta_names_the_secret_and_the_secret_is_private():
    meta = client.get("/api/meta").json()
    assert meta["secret_file"] == str(keystore.SECRET_FILE)
    assert meta["secret_problem"] == ""
    assert keystore.SECRET_FILE.exists()
    assert _mode(keystore.SECRET_FILE) == 0o600
    assert _mode(keystore.SECRET_FILE.parent) == 0o700
    key = keystore.SECRET_FILE.read_bytes().strip()
    assert len(key) == 44                            # one Fernet key, and nothing else
    Fernet(key)


def test_data_folder_and_database_are_private_and_secure_delete_is_on():
    db.tighten_files()
    assert _mode(db.DB_PATH) == 0o600
    assert _mode(db.DB_PATH.parent) == 0o700
    wal = db.DB_PATH.with_name(db.DB_PATH.name + "-wal")
    if wal.exists():
        assert _mode(wal) == 0o600
    assert db.get_conn().execute("PRAGMA secure_delete").fetchone()[0] == 1
