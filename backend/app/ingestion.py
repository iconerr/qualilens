# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""File intake: text extraction for documents, audio handling for media.

Text sources (.txt, .md, .docx, .pdf) are parsed locally — they never leave
the machine except inside analysis prompts sent to the chosen LLM.
Audio/video is transcribed via OpenAI's speech-to-text API (see
transcription.py); video has its audio track extracted with ffmpeg first.
"""

from pathlib import Path

# .rtf is deliberately absent: an RTF file is markup, and reading it as
# plain text would feed control codes to the analysis. Convert it first.
TEXT_EXTS = {".txt", ".md", ".text", ".markdown"}
REFUSED_EXTS = {".rtf": "RTF is not supported — save the document as .docx or .txt first."}
DOCX_EXTS = {".docx"}
PDF_EXTS = {".pdf"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".webm", ".aac", ".mpga"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".mpeg", ".wmv"}


def classify(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in REFUSED_EXTS:
        raise ValueError(REFUSED_EXTS[ext])
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
    return decode_text(path.read_bytes()), None


def decode_text(raw: bytes) -> str:
    """Decode a plain-text upload. A byte-order mark decides UTF-8/UTF-16/
    UTF-32 outright; otherwise strict UTF-8, then Windows-1252 (which also
    covers Latin-1's printable range and is what most non-UTF-8 files
    actually are). UTF-16 is never guessed without its BOM: a Windows-1252
    file of even length decodes "successfully" as UTF-16 into CJK garbage."""
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8-sig"),
                     (b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
                     (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if raw.startswith(bom):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                break
    for enc in ("utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("latin-1")


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
    """Body text in DOCUMENT ORDER: paragraphs and tables interleaved as they
    appear (a transcript laid out as a speaker/utterance table stays where
    it was), table rows flattened to pipe-separated lines, and text boxes
    included with the paragraph that anchors them. Headers, footers, and
    footnotes are not read; the manual says so."""
    import docx  # python-docx
    from docx.oxml.ns import qn
    d = docx.Document(str(path))
    parts = []

    def para_text(p_el) -> str:
        # every w:t beneath the paragraph, including runs inside text boxes
        return "".join(t.text or "" for t in p_el.iter(qn("w:t")))

    def walk(container) -> None:
        for el in container.iterchildren():
            tag = el.tag
            if tag == qn("w:p"):
                t = para_text(el)
                if t.strip():
                    parts.append(t)
            elif tag == qn("w:tbl"):
                for tr in el.iter(qn("w:tr")):
                    cells = []
                    for tc in tr.iter(qn("w:tc")):
                        ct = "\n".join(para_text(p) for p in tc.iter(qn("w:p")))
                        ct = " ".join(ct.split())
                        if ct:
                            cells.append(ct)
                    if cells:
                        parts.append(" | ".join(cells))
            elif tag == qn("w:sdt"):
                content = el.find(qn("w:sdtContent"))
                if content is not None:
                    walk(content)
    walk(d.element.body)
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
