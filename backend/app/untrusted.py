# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Content QualiLens did not write: text that must fit in XML, and zip
containers that must not unpack to an implausible size.

Text. Word documents and spreadsheets are XML, and XML 1.0 forbids most
control characters. Source text can carry them anyway: pdftotext puts a form
feed at every page break, and an older export may hold stray control bytes.
One such character in a coded quote made the Word report and the checkpoint
spreadsheet fail for the whole run (2026-10-08). xml_safe() turns a form feed
or vertical tab into a line break and drops the rest. Intake applies it before
offsets are computed, so stored text and offsets agree, and both exports
apply it to what they write, which covers sources stored before intake did.

Zip containers. A .docx or an .xlsx is a zip, and a small one can declare
members that unpack to gigabytes. Python's zipfile stops each member at its
declared size and then fails its CRC, so the declared sizes bound what a
parser can be made to read. zip_within_bounds() refuses a container before
any parser opens it. The updater keeps its own bounds (update.py).
"""

import re
import zipfile

# The C0 controls other than tab, line feed, and carriage return; the two
# noncharacters U+FFFE and U+FFFF; and lone surrogates, which no well-formed
# text holds but a careless decode can produce.
_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")
_LINE_BREAKS = "\x0b\x0c"


def xml_safe(text: str) -> str:
    """text with every character XML 1.0 forbids removed; a form feed or a
    vertical tab becomes a line feed, so a page break stays a break."""
    if not text or not _XML_ILLEGAL.search(text):
        return text
    return _XML_ILLEGAL.sub(lambda m: "\n" if m.group() in _LINE_BREAKS else "", text)


def xml_safe_deep(obj):
    """xml_safe applied to every string in a JSON-shaped value, keys included
    (a frequency table is keyed by code names, which become table headers)."""
    if isinstance(obj, str):
        return xml_safe(obj)
    if isinstance(obj, list):
        return [xml_safe_deep(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(xml_safe_deep(x) for x in obj)
    if isinstance(obj, dict):
        return {(xml_safe(k) if isinstance(k, str) else k): xml_safe_deep(v)
                for k, v in obj.items()}
    return obj


class ContainerRefused(ValueError):
    """A zip container that is not one (not_a_zip), or that would unpack
    implausibly."""

    def __init__(self, message: str, not_a_zip: bool = False):
        super().__init__(message)
        self.not_a_zip = not_a_zip


def zip_within_bounds(source, what: str, max_unpacked: int, max_members: int = 10_000) -> None:
    """Refuse a zip container (a path or a binary file object) that is not a
    zip, holds more than max_members members, or declares more than
    max_unpacked bytes in all. `what` names the file for the message."""
    try:
        with zipfile.ZipFile(source) as zf:
            infos = zf.infolist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError) as e:
        raise ContainerRefused(f"That {what} is damaged or is not a {what} file.",
                               not_a_zip=True) from e
    if len(infos) > max_members:
        raise ContainerRefused(f"That {what} holds implausibly many parts ({len(infos):,}); "
                               "refusing. Save it again from the program that made it.")
    declared = sum(max(0, i.file_size) for i in infos)
    if declared > max_unpacked:
        raise ContainerRefused(
            f"That {what} would unpack to {declared / (1 << 20):,.0f} MB, more than any "
            f"{what} QualiLens reads ({max_unpacked >> 20:,} MB); it is damaged or built "
            "to exhaust memory. Refusing. Save it again from the program that made it.")
