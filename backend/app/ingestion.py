# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""File intake: text extraction for documents, audio handling for media.

Text sources (.txt, .md, .docx, .pdf) are parsed locally — they never leave
the machine except inside analysis prompts sent to the chosen LLM.
Audio/video is transcribed via OpenAI's speech-to-text API (see
transcription.py); video has its audio track extracted with ffmpeg first.
"""

from pathlib import Path

TEXT_EXTS = {".txt", ".md", ".text", ".rtf"}
DOCX_EXTS = {".docx"}
PDF_EXTS = {".pdf"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".webm", ".aac", ".mpga"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".mpeg", ".wmv"}


def classify(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in TEXT_EXTS | DOCX_EXTS | PDF_EXTS:
        return "text"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    raise ValueError(f"Unsupported file type: {ext or filename}")


def extract_text(path: Path) -> str:
    return extract_text_with_pages(path)[0]


def extract_text_with_pages(path: Path) -> tuple:
    """Extract text plus, for PDFs, the page map: [{"page", "start", "end"}]
    with original 1-based page numbers and character offsets into the
    returned text. Non-PDF sources return (text, None) — they have no pages.
    The joined text is byte-identical to what extract_text always produced,
    so nothing downstream changes for existing sources."""
    ext = path.suffix.lower()
    if ext in DOCX_EXTS:
        return _extract_docx(path), None
    if ext in PDF_EXTS:
        return _extract_pdf(path)
    # plain text; try common encodings
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc), None
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace"), None


def page_for_offset(pages: list, offset) -> int | None:
    """Original PDF page number for a character offset, from a stored page
    map. None when the map is absent/empty or the offset falls outside it
    (e.g. in the join between pages)."""
    if not pages or not isinstance(offset, int):
        return None
    for p in pages:
        try:
            if p["start"] <= offset < p["end"]:
                return p["page"]
        except (KeyError, TypeError):
            return None
    return None


def _extract_docx(path: Path) -> str:
    import docx  # python-docx
    d = docx.Document(str(path))
    parts = []
    for para in d.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def _extract_pdf(path: Path) -> tuple:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    page_texts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        page_texts.append(t)
    return join_pdf_pages(page_texts)


def join_pdf_pages(page_texts: list) -> tuple:
    """Join per-page texts the way the app always has (strip each page, skip
    empty pages, join with a blank line) while recording where each original
    page landed in the joined string. Pure, so the offset bookkeeping is
    testable without a PDF on disk."""
    parts, pages, pos = [], [], 0
    for i, t in enumerate(page_texts, start=1):
        t = (t or "").strip()
        if not t:
            continue                # an image-only page keeps its neighbors' numbers
        if parts:
            pos += 2                # the "\n\n" separator
        pages.append({"page": i, "start": pos, "end": pos + len(t)})
        parts.append(t)
        pos += len(t)
    return "\n\n".join(parts), (pages or None)
