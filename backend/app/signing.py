# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Release-bundle signing and verification (Ed25519).

A bundle carries two extra members at its root: MANIFEST.sha256, one line per
file of the form "<sha256 hex>  <relative path>", and MANIFEST.sig, the
base64 Ed25519 signature over the manifest's exact bytes. The updater
verifies the signature against the public key compiled into update.py and
then checks every member of the archive against the manifest, so a bundle
that was not produced by the authors' key — or was altered afterwards — is
refused before a byte is written.

This file is deliberately import-free of the rest of the app so package.sh
can run it as a plain script from the staging directory:

    python signing.py keygen <keyfile>            # writes seed; prints public hex
    python signing.py sign <stage_dir> <keyfile>  # writes MANIFEST.sha256 + .sig
    python signing.py verify <bundle.zip> [pubhex]

The private key file holds the 32-byte seed as hex. It is held by the
authors outside the application folder and never ships: the packaging
manifest cannot reach it, and the sync script's refusal gate rejects any
key-shaped file before a commit.
"""

import base64
import hashlib
import sys
import zipfile
from pathlib import Path

MANIFEST_NAME = "MANIFEST.sha256"
SIGNATURE_NAME = "MANIFEST.sig"


class SignatureError(Exception):
    pass


def _ed25519():
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
    except ImportError as e:  # pragma: no cover — requirements.txt pins it
        raise SignatureError("The 'cryptography' package is required for bundle "
                             "signing and verification.") from e
    return ed25519, serialization


def read_seed(keyfile: Path) -> bytes:
    seed = bytes.fromhex(Path(keyfile).read_text().strip())
    if len(seed) != 32:
        raise SignatureError("The signing key file must hold a 32-byte seed as hex.")
    return seed


def public_hex_from_seed(seed: bytes) -> str:
    ed25519, ser = _ed25519()
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    return priv.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw).hex()


def keygen(keyfile: Path) -> str:
    ed25519, ser = _ed25519()
    priv = ed25519.Ed25519PrivateKey.generate()
    seed = priv.private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption())
    keyfile = Path(keyfile)
    keyfile.write_text(seed.hex() + "\n")
    try:
        keyfile.chmod(0o600)
    except OSError:
        pass
    return public_hex_from_seed(seed)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_for_dir(stage: Path) -> str:
    """Manifest text for every regular file under stage (sorted, POSIX paths),
    excluding the manifest and signature themselves."""
    stage = Path(stage)
    lines = []
    for p in sorted(stage.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(stage).as_posix()
        if rel in (MANIFEST_NAME, SIGNATURE_NAME):
            continue
        lines.append(f"{sha256_file(p)}  {rel}")
    return "\n".join(lines) + "\n"


def sign_bytes(data: bytes, seed: bytes) -> str:
    ed25519, _ = _ed25519()
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    return base64.b64encode(priv.sign(data)).decode("ascii")


def verify_bytes(data: bytes, sig_b64: str, public_hex: str) -> bool:
    ed25519, _ = _ed25519()
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
        pub.verify(base64.b64decode(sig_b64.strip()), data)
        return True
    except Exception:  # noqa: BLE001 — any failure is "not verified"
        return False


def sign_stage(stage: Path, keyfile: Path) -> None:
    """Write MANIFEST.sha256 and MANIFEST.sig into a staged bundle folder."""
    stage = Path(stage)
    seed = read_seed(keyfile)
    manifest = manifest_for_dir(stage)
    (stage / MANIFEST_NAME).write_text(manifest, encoding="utf-8")
    (stage / SIGNATURE_NAME).write_text(sign_bytes(manifest.encode("utf-8"), seed) + "\n",
                                        encoding="utf-8")


def parse_manifest(text: str) -> dict:
    out = {}
    for n, line in enumerate(text.splitlines(), 1):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise SignatureError(f"Malformed manifest line {n}.")
        digest, rel = parts[0].lower(), parts[1].strip()
        if rel in out:
            raise SignatureError(f"Duplicate manifest entry: {rel!r}.")
        out[rel] = digest
    if not out:
        raise SignatureError("The manifest is empty.")
    return out


def verify_zip_members(zf: zipfile.ZipFile, members: list, public_hex: str) -> dict:
    """members: [(ZipInfo, relative_path)] as the updater computed them (root
    folder stripped). Verifies the signature over the manifest and every
    member's hash; refuses extra or missing files. Returns the manifest."""
    by_rel = {rel: m for m, rel in members}
    if MANIFEST_NAME not in by_rel or SIGNATURE_NAME not in by_rel:
        raise SignatureError("This bundle is not signed (no MANIFEST.sha256 / MANIFEST.sig). "
                             "Only bundles signed by the QualiLens release key can be installed.")
    manifest_bytes = zf.read(by_rel[MANIFEST_NAME])
    sig = zf.read(by_rel[SIGNATURE_NAME]).decode("ascii", "replace")
    if not verify_bytes(manifest_bytes, sig, public_hex):
        raise SignatureError("The bundle's signature does not verify against the QualiLens "
                             "release key. It was not produced by the authors, or it was "
                             "altered after signing. Refusing to install it.")
    manifest = parse_manifest(manifest_bytes.decode("utf-8", "replace"))
    listed = set(manifest)
    present = {rel for rel in by_rel if rel not in (MANIFEST_NAME, SIGNATURE_NAME)}
    extra = sorted(present - listed)
    missing = sorted(listed - present)
    if extra:
        raise SignatureError(f"The bundle contains files not covered by its signature: "
                             f"{', '.join(extra[:5])}{'…' if len(extra) > 5 else ''}. Refusing.")
    if missing:
        raise SignatureError(f"The bundle is missing signed files: "
                             f"{', '.join(missing[:5])}{'…' if len(missing) > 5 else ''}. Refusing.")
    for rel, digest in manifest.items():
        h = hashlib.sha256()
        with zf.open(by_rel[rel]) as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != digest:
            raise SignatureError(f"{rel} does not match its signed hash. Refusing.")
    return manifest


def verify_bundle_file(path: Path, public_hex: str) -> int:
    """Verify a bundle zip on disk (used before publishing a release).
    Returns the number of signed files."""
    with zipfile.ZipFile(path) as zf:
        names = [m.filename for m in zf.infolist() if not m.is_dir()]
        prefix = ""
        first = names[0].split("/", 1)[0] if names else ""
        if first and all(n.startswith(first + "/") for n in names):
            prefix = first + "/"
        members = [(m, m.filename[len(prefix):]) for m in zf.infolist() if not m.is_dir()]
        return len(verify_zip_members(zf, members, public_hex))


def _main(argv: list) -> int:
    if len(argv) >= 3 and argv[1] == "keygen":
        print(keygen(Path(argv[2])))
        return 0
    if len(argv) >= 4 and argv[1] == "sign":
        sign_stage(Path(argv[2]), Path(argv[3]))
        print(f"signed {argv[2]}")
        return 0
    if len(argv) >= 3 and argv[1] == "verify":
        pub = argv[3] if len(argv) >= 4 else None
        if pub is None:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from app.update import PUBLIC_KEY_HEX as pub  # noqa: WPS433
        try:
            n = verify_bundle_file(Path(argv[2]), pub)
        except SignatureError as e:
            print(f"NOT VERIFIED: {e}")
            return 1
        print(f"verified: {n} signed files")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
