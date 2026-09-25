# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""API keys at rest: encrypted in the database, with the secret kept elsewhere.

A provider key is stored in the settings table as Fernet ciphertext (AES-128
in CBC mode with an HMAC-SHA256 tag, from the cryptography package the
updater already depends on), marked with the prefix 'enc1:'. The secret that
encrypts every key lives OUTSIDE the data folder, in a per-user location that
no sync service follows:

    macOS            ~/Library/Application Support/QualiLens/secret.key
    Linux and WSL    $XDG_CONFIG_HOME/qualilens/secret.key  (~/.config/qualilens/)
    anywhere         $QUALILENS_SECRET_FILE, when it is set

so a copy of the database — synced, backed up, or handed over — carries no
usable key. The file is created on first use, mode 0600 in a 0700 directory,
and holds one Fernet key (44 urlsafe-base64 characters).

What this protects against: the sync service, and anyone who obtains the
database file without the secret. What it does not protect against: anyone
who runs as this user on this computer, who can read both files. The manual
says so in the same words.

A database opened where the secret differs (another computer, or the file was
replaced) reports its keys as unreadable rather than absent, so the Settings
screen can say why; pasting the key again overwrites it. Plaintext rows saved
by builds before this module are encrypted in place at startup by
migrate_plaintext(), and on read should one appear later.
"""

import os
import sys
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from . import db

PREFIX = "enc1:"


def _default_secret_file() -> Path:
    env = (os.environ.get("QUALILENS_SECRET_FILE") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support" / "QualiLens"
    else:
        xdg = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
        base = (Path(xdg).expanduser() if xdg else home / ".config") / "qualilens"
    return base / "secret.key"


# Tests point this at a scratch path before the app is imported, as they do
# with db.DB_PATH; the file is read lazily, on first use.
SECRET_FILE = _default_secret_file()


class KeyStoreError(Exception):
    """The secret cannot be read or created, so no key can be saved."""


_lock = threading.Lock()
_fernet: Fernet | None = None
_problem = ""                  # why the secret is unusable; '' when it is fine
_loaded_from: Path | None = None


def _setting(provider: str) -> str:
    return f"api_key_{provider}"


def _read_or_create(path: Path) -> bytes:
    if path.exists():
        db.private(path, 0o600)          # tighten a file created by hand or copied
        return path.read_bytes().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    db.private(path.parent, 0o700)
    key = Fernet.generate_key()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:              # another QualiLens process won the race
        return path.read_bytes().strip()
    with os.fdopen(fd, "wb") as f:
        f.write(key + b"\n")
    return key


def _load() -> Fernet | None:
    """The Fernet for SECRET_FILE, created on first use; None when the secret
    cannot be read or created, with the reason in _problem. Cached until
    SECRET_FILE changes or reload() is called."""
    global _fernet, _problem, _loaded_from
    with _lock:
        if _loaded_from == SECRET_FILE and (_fernet is not None or _problem):
            return _fernet
        path = SECRET_FILE
        _fernet, _problem, _loaded_from = None, "", path
        try:
            _fernet = Fernet(_read_or_create(path))
        except (OSError, ValueError, TypeError) as e:
            verb = "read" if path.exists() else "created"
            _problem = (f"The secret that encrypts your API keys could not be {verb} "
                        f"at {path} ({e}). Keys cannot be saved until it can. Set "
                        "QUALILENS_SECRET_FILE to a writable path outside any synced "
                        "folder and start the app again.")
        return _fernet


def reload() -> None:
    """Forget the cached secret so the next use reads SECRET_FILE afresh."""
    global _fernet, _problem, _loaded_from
    with _lock:
        _fernet, _problem, _loaded_from = None, "", None


def secret_problem() -> str:
    """'' when the secret is usable; otherwise why it is not."""
    _load()
    return _problem


def _encrypt(text: str) -> str:
    f = _load()
    if f is None:
        raise KeyStoreError(_problem)
    return PREFIX + f.encrypt(text.encode("utf-8")).decode("ascii")


def _decrypt(value: str) -> tuple[str, str]:
    """(plaintext, problem). Empty plaintext with an empty problem means no
    key is saved; empty plaintext with a problem means one is saved that
    this computer cannot read."""
    if not value:
        return "", ""
    if not value.startswith(PREFIX):
        return value, ""                 # a plaintext row from a build before 1.8
    f = _load()
    if f is None:
        return "", _problem
    try:
        return f.decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8"), ""
    except (InvalidToken, UnicodeDecodeError, ValueError):
        return "", (f"A key is saved but cannot be read with this computer's secret "
                    f"({SECRET_FILE}): the database came from another computer, or the "
                    "secret file was replaced. Paste the key again, or Remove it.")


def _hint(text: str) -> str:
    return (text[:6] + "…" + text[-4:]) if len(text) > 12 else ""


def status(provider: str) -> dict:
    """What Settings shows: whether a usable key is saved, its hint, and the
    reason when one is saved but unreadable."""
    text, problem = _decrypt(db.get_setting(_setting(provider)))
    return {"has_key": bool(text), "key_hint": _hint(text), "problem": problem}


def get_api_key(provider: str) -> str:
    """The plaintext key for a provider, or '' when none is saved or the
    saved one cannot be read here. A plaintext row is encrypted in place the
    first time it is read, so one never lingers."""
    raw = db.get_setting(_setting(provider))
    text, _ = _decrypt(raw)
    if text and not raw.startswith(PREFIX) and _load() is not None:
        db.set_setting(_setting(provider), _encrypt(text))
        db.scrub()
    return text


def set_api_key(provider: str, key: str) -> None:
    key = (key or "").strip()
    if not key:
        clear_api_key(provider)
        return
    db.set_setting(_setting(provider), _encrypt(key))   # KeyStoreError when no secret


def clear_api_key(provider: str) -> None:
    """Remove: the row is emptied and the file compacted so the old value
    leaves the file rather than lingering in freed space."""
    db.set_setting(_setting(provider), "")
    db.scrub()


def migrate_plaintext() -> int:
    """Encrypt every plaintext key row in place (a database written by a
    build before 1.8), then compact the file so the plaintext leaves it.
    Returns how many rows were encrypted. Does nothing when the secret is
    unusable — the rows stay readable and Settings reports the problem."""
    if _load() is None:
        return 0
    conn = db.get_conn()
    rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'api_key_%'").fetchall()
    n = 0
    for r in rows:
        value = r["value"] or ""
        if value and not value.startswith(PREFIX):
            db.set_setting(r["key"], _encrypt(value))
            n += 1
    if n:
        db.scrub()
    return n
