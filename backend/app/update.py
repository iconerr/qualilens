# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""In-place application update from a downloaded QualiLens bundle.

Safety model, in order of importance:
1. `backend/data/` (projects, keys, uploads) is untouchable — the updater
   works from an ALLOWLIST of application paths and refuses everything else,
   so user data survive by construction, not by care.
2. Every archive member is validated against zip-slip (absolute paths, `..`,
   symlinks) and against size bounds before a single byte is written.
3. The bundle must carry a valid Ed25519 signature from the QualiLens
   release key (PUBLIC_KEY_HEX below) over a manifest that names and hashes
   every file in it. An unsigned, foreign, or altered bundle is refused —
   this, not the marker files, is what proves a bundle is QualiLens.
4. The previous application files are backed up first; any failure during
   extraction restores them automatically.
5. A bundle whose build stamp is OLDER than the installed one is refused
   (RollbackRefused) unless the caller says allow_downgrade — a signature
   proves the authors made a bundle, not that it is the one they publish
   now, so a republished old release must not install itself as "latest".
   The GitHub path never allows a downgrade; the zip path asks first.

The optional release check is PULL-ONLY and user-initiated: pressing the
button makes one GET to GitHub's releases endpoint for UPDATE_REPO; nothing
is ever sent beyond that request, and nothing runs in the background. The
downloaded bundle goes through apply_update like any other, so the safety
model above applies unchanged.
"""

import re
import shutil
import time
import zipfile
from pathlib import Path

from . import signing

# The Ed25519 public key every installable bundle must be signed with. The
# matching private seed is held by the authors and is never part of any
# bundle or repository; package.sh signs each bundle with it. Rotating the
# key means shipping one release signed by the old key that carries the new
# key here.
PUBLIC_KEY_HEX = "3bc9834cefa5c6e86df2000816ddd814077d04163c86edc1ffe62261d3d42464"

# Where releases are published. The check compares the release's "build"
# stamp (in its title or notes, e.g. "build 2026.08.27-1950") against the
# local VERSION file; the human-facing tag may be semver (v1.0.0).
UPDATE_REPO = "iconerr/qualilens"
RELEASES_URL = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
BUNDLE_ASSET_NAME = "QualiLens.zip"
MAX_BUNDLE_BYTES = 200 * 1024 * 1024          # the zip itself, either path
MAX_UNPACKED_BYTES = 600 * 1024 * 1024        # sum of members' declared sizes
MAX_MEMBER_COUNT = 20000
_BUILD_RE = re.compile(r"build\s+(\d{4}\.\d{2}\.\d{2}-\d{4})")
# a VERSION stamp: YYYY.MM.DD, optionally -HHMM (compares lexicographically)
_STAMP_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}(-\d{4})?$")

APP_ROOT = Path(__file__).resolve().parent.parent.parent

# The only top-level paths an update may create or replace. Mirrors the
# shipping manifest in package.sh. Everything else — backend/data above all —
# is refused.
ALLOWED = (
    "VERSION", "run.sh", "package.sh", "LICENSE", "NOTICE", "CITATION.cff",
    "README.md", ".gitignore",
    "backend/requirements.txt", "backend/app/", "backend/tests/",
    "frontend/index.html", "frontend/package.json", "frontend/package-lock.json",
    "frontend/tsconfig.json", "frontend/tsconfig.app.json",
    "frontend/tsconfig.node.json", "frontend/vite.config.ts",
    "frontend/public/", "frontend/src/", "frontend/dist/",
    "manual/",
)

# Trees that are REPLACED wholesale (so files deleted upstream do not linger,
# e.g. old hashed bundles in frontend/dist).
REPLACE_TREES = ("backend/app", "backend/tests", "frontend/dist",
                 "frontend/src", "frontend/public", "manual")

BACKUP_DIR = APP_ROOT / ".update-backup"


class UpdateError(Exception):
    pass


class RollbackRefused(UpdateError):
    """The bundle is a valid, signed QualiLens build — but an older one."""


def is_older_build(candidate: str, installed: str) -> bool:
    """True when both are build stamps and candidate predates installed.
    Anything unstamped ('unknown', a test label) cannot be compared and is
    not called a rollback."""
    c, i = (candidate or "").strip(), (installed or "").strip()
    return bool(_STAMP_RE.match(c) and _STAMP_RE.match(i)) and c < i


def _github_page_url(value) -> str:
    """The release's page URL, only when it is a GitHub page of UPDATE_REPO.
    The interface renders it as a link, so anything else — another host, an
    odd scheme — is dropped rather than shown."""
    url = str(value or "")
    return url if url.startswith(f"https://github.com/{UPDATE_REPO}/") else ""


def _current_version() -> str:
    try:
        return (APP_ROOT / "VERSION").read_text().strip()
    except OSError:
        return "unknown"


def _member_paths(zf: zipfile.ZipFile) -> list:
    """Validated (member, relative_path) pairs, with the bundle's root folder
    stripped and zip-slip attempts rejected."""
    names = [m.filename for m in zf.infolist() if not m.is_dir()]
    if not names:
        raise UpdateError("The archive is empty.")
    if len(names) > MAX_MEMBER_COUNT:
        raise UpdateError("The archive holds implausibly many files; refusing.")
    declared = sum(max(0, m.file_size) for m in zf.infolist())
    if declared > MAX_UNPACKED_BYTES:
        raise UpdateError("The archive would unpack to an implausible size; refusing.")
    prefix = ""
    first = names[0].split("/", 1)[0]
    if first and all(n.startswith(first + "/") for n in names):
        prefix = first + "/"
    out = []
    for m in zf.infolist():
        if m.is_dir():
            continue
        rel = m.filename[len(prefix):] if prefix else m.filename
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or not rel:
            raise UpdateError(f"Unsafe path in archive: {m.filename!r}")
        # refuse symlinks outright (external_attr high bits carry the mode)
        if (m.external_attr >> 16) & 0o170000 == 0o120000:
            raise UpdateError(f"Symbolic link in archive: {m.filename!r}")
        out.append((m, rel))
    return out


def _is_allowed(rel: str) -> bool:
    return any(rel == a or (a.endswith("/") and rel.startswith(a))
               for a in ALLOWED)


def _validate_is_qualilens(zf: zipfile.ZipFile, members: list) -> None:
    rels = {rel for _, rel in members}
    for required in ("run.sh", "backend/app/main.py", "NOTICE",
                     "frontend/dist/index.html"):
        if required not in rels:
            raise UpdateError(
                f"This does not look like a QualiLens bundle ({required} is missing).")
    notice_member = next(m for m, rel in members if rel == "NOTICE")
    notice = zf.read(notice_member).decode("utf-8", errors="replace")
    if "Ashita Aggarwal and Suraj Commuri" not in notice:
        raise UpdateError("The bundle's NOTICE does not identify QualiLens.")
    # the marker checks above are a cheap sanity filter; authenticity is the
    # signature over the full manifest, verified here before anything else
    try:
        signing.verify_zip_members(zf, members, PUBLIC_KEY_HEX)
    except signing.SignatureError as e:
        raise UpdateError(str(e))


# ---------- pull-only release check ----------

def fetch_latest_release() -> dict:
    """One GET to GitHub's latest-release endpoint. The only network call in
    this module; tests monkeypatch it, and the UI calls it only on a click."""
    import httpx
    try:
        r = httpx.get(RELEASES_URL, timeout=20, follow_redirects=True,
                      headers={"Accept": "application/vnd.github+json",
                               "User-Agent": "QualiLens-updater"})
    except Exception as e:  # noqa: BLE001 — network failure is a user-facing fact
        raise UpdateError(f"Could not reach GitHub: {e}")
    if r.status_code == 404:
        raise UpdateError("No releases have been published yet.")
    if r.status_code != 200:
        raise UpdateError(f"GitHub answered HTTP {r.status_code}.")
    try:
        data = r.json()
    except ValueError:
        raise UpdateError("GitHub's answer was not readable.")
    if not isinstance(data, dict):
        raise UpdateError("GitHub's answer was not readable.")
    return data


def _bundle_asset(release: dict) -> dict | None:
    for a in release.get("assets") or []:
        if isinstance(a, dict) and a.get("name") == BUNDLE_ASSET_NAME:
            return a
    return None


def check_for_update() -> dict:
    """Compare the latest published release's build stamp with the installed
    VERSION. Build stamps (YYYY.MM.DD-HHMM) compare lexicographically."""
    release = fetch_latest_release()
    tag = str(release.get("tag_name") or "")
    m = _BUILD_RE.search(f"{release.get('name') or ''}\n{release.get('body') or ''}")
    build = m.group(1) if m else ""
    asset = _bundle_asset(release)
    current = _current_version()
    out = {
        "ok": True, "current": current, "tag": tag, "build": build,
        "release_url": _github_page_url(release.get("html_url")),
        "has_bundle": bool(asset),
        "asset_size": (asset or {}).get("size"),
    }
    if not build:
        out["newer"] = False
        out["note"] = ("The latest release carries no build stamp, so it cannot "
                       "be compared with this installation — see the release page.")
    else:
        out["newer"] = current == "unknown" or build > current
    return out


def download_latest_bundle(dest_dir: Path) -> Path:
    """Fetch the latest release's bundle to dest_dir and return its path.
    The release is re-resolved here — a caller-supplied URL is never
    accepted — and the asset must be GitHub-hosted and within size bounds."""
    release = fetch_latest_release()
    asset = _bundle_asset(release)
    if not asset:
        raise UpdateError(
            f"The latest release carries no {BUNDLE_ASSET_NAME} asset.")
    url = str(asset.get("browser_download_url") or "")
    if not url.startswith(f"https://github.com/{UPDATE_REPO}/"):
        raise UpdateError("The release asset is not hosted with the QualiLens "
                          "repository; refusing to download it.")
    size = asset.get("size") or 0
    if size > MAX_BUNDLE_BYTES:
        raise UpdateError("The release asset is implausibly large; refusing.")
    import httpx
    dest = Path(dest_dir) / BUNDLE_ASSET_NAME
    try:
        with httpx.stream("GET", url, timeout=120, follow_redirects=True,
                          headers={"User-Agent": "QualiLens-updater"}) as r:
            if r.status_code != 200:
                raise UpdateError(f"Downloading the bundle failed (HTTP {r.status_code}).")
            # the prefix check above covered the first hop only; the final
            # host after redirects must still be GitHub's own storage
            final_host = (r.url.host or "").lower()
            if not (final_host == "github.com" or final_host.endswith(".github.com")
                    or final_host.endswith(".githubusercontent.com")):
                raise UpdateError("The download was redirected away from GitHub; refusing.")
            written = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes():
                    written += len(chunk)
                    if written > MAX_BUNDLE_BYTES:
                        raise UpdateError("The download exceeded the size bound; refusing.")
                    f.write(chunk)
    except UpdateError:
        raise
    except Exception as e:  # noqa: BLE001
        raise UpdateError(f"Downloading the bundle failed: {e}")
    return dest


def apply_update(zip_path: Path, allow_downgrade: bool = False) -> dict:
    """Validate and apply the bundle at zip_path. Returns a summary dict.
    Raises UpdateError with a user-facing message on any refusal (a
    RollbackRefused when the only objection is that the bundle is an older
    build than the installed one); restores the previous files on any
    mid-flight failure."""
    from_version = _current_version()
    try:
        if Path(zip_path).stat().st_size > MAX_BUNDLE_BYTES:
            raise UpdateError("That file is larger than any QualiLens bundle; refusing.")
    except OSError:
        raise UpdateError("The bundle file could not be read.")
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise UpdateError("That file is not a zip archive.")
    with zf:
        members = _member_paths(zf)
        _validate_is_qualilens(zf, members)
        manifest_files = (signing.MANIFEST_NAME, signing.SIGNATURE_NAME)
        to_install = [(m, rel) for m, rel in members if _is_allowed(rel)]
        skipped = [rel for _, rel in members
                   if not _is_allowed(rel) and rel not in manifest_files]
        if not to_install:
            raise UpdateError("The bundle contains no installable application files.")
        # a maintainer's local model-catalog edits must not vanish silently
        # when backend/app is replaced wholesale: keep the outgoing copy
        # beside the data (never inside the replaced tree) when it differs
        catalog_note = None
        local_catalog = APP_ROOT / "backend" / "app" / "models.json"
        incoming = next((m for m, rel in to_install if rel == "backend/app/models.json"), None)
        if incoming is not None and local_catalog.exists():
            try:
                if local_catalog.read_bytes() != zf.read(incoming):
                    from . import db
                    keep = db.DATA_DIR / "models.json.previous"
                    keep.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_catalog, keep)
                    catalog_note = (f"Your edited models.json differed from the update's; "
                                    f"the outgoing copy was saved to {keep}.")
            except OSError:
                pass

        # read the incoming version before touching anything
        to_version = "unknown"
        for m, rel in to_install:
            if rel == "VERSION":
                to_version = zf.read(m).decode("utf-8", "replace").strip()
        if is_older_build(to_version, from_version) and not allow_downgrade:
            raise RollbackRefused(
                f"That bundle is build {to_version}, older than the installed build "
                f"{from_version}. A signed bundle proves the authors made it, not that "
                "it is current; installing an older build is a rollback and is refused "
                "unless you ask for it explicitly.")

        # back up everything we are about to replace
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / stamp
        if BACKUP_DIR.exists():
            shutil.rmtree(BACKUP_DIR)  # keep exactly one previous version
        backup.mkdir(parents=True)
        replaced_trees = []
        for tree in REPLACE_TREES:
            src = APP_ROOT / tree
            if src.exists():
                (backup / tree).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(backup / tree))
                replaced_trees.append(tree)
        for _, rel in to_install:
            if any(rel == t or rel.startswith(t + "/") for t in REPLACE_TREES):
                continue
            src = APP_ROOT / rel
            if src.exists():
                dest = backup / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        try:
            for m, rel in to_install:
                dest = APP_ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(m) as f, open(dest, "wb") as out:
                    shutil.copyfileobj(f, out)
                if rel.endswith(".sh"):
                    dest.chmod(0o755)
        except Exception as e:  # noqa: BLE001 — restore, then report
            for tree in replaced_trees:
                dest = APP_ROOT / tree
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(backup / tree), str(dest))
            # single files (run.sh, VERSION, …) may already be overwritten
            for f in backup.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(backup)
                    if not any(str(rel) == t2 or str(rel).startswith(t2 + "/")
                               for t2 in REPLACE_TREES):
                        shutil.copy2(f, APP_ROOT / rel)
            raise UpdateError(
                f"Extraction failed and the previous version was restored: {e}")

    out = {
        "ok": True,
        "from_version": from_version,
        "to_version": to_version,
        "files_installed": len(to_install),
        "files_refused": skipped,
        "backup": str(backup),
        "data_untouched": True,
        "signature": "verified",
    }
    if catalog_note:
        out["note"] = catalog_note
    return out
