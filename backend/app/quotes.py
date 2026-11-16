# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Quotes as a reader sees them on screen (added 2026-11-15).

A quote is stored verbatim, as the model returned it, so a PDF's line-end
hyphenation survives in it, either with the line break ("decom-\\nposes") or
with the break flattened to a space ("decom- poses"). On screen that reads as
"decom- poses". For display, a word broken across a line is joined again, and
the source's own text decides whether it keeps its hyphen: "decomposes", but
"worst-case" when the paper writes "worst-case" on one line elsewhere. A
suspended hyphen ("pre- and post-test") is left as it is. The stored quote,
the spreadsheet export and the audit export never change.
"""

import re
from functools import lru_cache

from . import db

_WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
# a word, a hyphen, then a line break (with any spaces) or plain spaces, then a word
_BROKEN = re.compile(r"([^\W\d_]+)-([ \t]*\r?\n[ \t]*|[ \t]+)([^\W\d_]+)")
_SUSPENDED = frozenset({"and", "or", "nor", "to", "through", "versus", "vs", "than", "as"})


def display(quote: str, vocab: frozenset = frozenset()) -> str:
    """The quote with words broken across a line joined again. `vocab` is the
    set of words (lowercase, hyphenated compounds whole) in the source."""
    if not quote or "-" not in quote:
        return quote

    def join(m: re.Match) -> str:
        a, b = m.group(1), m.group(3)
        if not b[0].islower() or b.lower() in _SUSPENDED:
            return m.group(0)
        if f"{a}-{b}".lower() in vocab and (a + b).lower() not in vocab:
            return f"{a}-{b}"
        return a + b

    return _BROKEN.sub(join, quote)


@lru_cache(maxsize=128)
def _vocab(source_id: str) -> frozenset:
    # a source's text never changes after upload, so its word list is cached
    row = db.get_conn().execute("SELECT text FROM sources WHERE id=?", (source_id,)).fetchone()
    text = (row["text"] if row else "") or ""
    return frozenset(w.lower() for w in _WORD.findall(text))


def for_display(quote: str, source_id: str | None) -> str:
    """display(), with the vocabulary of the quote's own source."""
    if not quote or "-" not in quote:
        return quote
    return display(quote, _vocab(source_id) if source_id else frozenset())


def checkpoint_payload(payload: dict) -> dict:
    """A pending checkpoint's payload as the review shows it: the quotes it
    carries pass through for_display(). The stored payload is not changed."""
    if not isinstance(payload, dict):
        return payload
    def fix(ex: dict) -> None:
        if isinstance(ex, dict) and isinstance(ex.get("quote"), str):
            ex["quote"] = for_display(ex["quote"], ex.get("source_id"))
    for it in payload.get("items") or []:
        for ex in (it.get("sample_excerpts") or []) if isinstance(it, dict) else []:
            fix(ex)
    for ex in payload.get("low_confidence") or []:
        fix(ex)
    return payload
