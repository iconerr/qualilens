# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Render a run's report payload to a formatted .docx."""

import time
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x66, 0x66, 0x66)


def build_docx(payload: dict) -> bytes:
    doc = Document()
    # generator identification in the document properties (the visible
    # counterpart is the colophon at the end of the report)
    doc.core_properties.comments = "Generated with QualiLens (ql-a2f4467b)"
    style = doc.styles["Normal"]
    style.font.name = "Georgia"
    style.font.size = Pt(11)

    # Title block
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run(payload.get("title", "Qualitative Analysis Report"))
    r.font.size = Pt(20)
    r.font.bold = True
    r.font.color.rgb = ACCENT

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    when = time.strftime("%B %d, %Y", time.localtime(payload.get("generated_at", time.time())))
    r = meta.add_run(
        f"Method: {payload.get('method', '')}  ·  Generated {when} with QualiLens  ·  "
        f"Model: {payload.get('provider', '')}/{payload.get('model', '')}")
    r.font.size = Pt(9)
    r.font.color.rgb = MUTED

    # Sources
    doc.add_heading("Data Sources", level=1)
    for s in payload.get("sources", []):
        line = s["filename"] + (f"  (group: {s['grp']})" if s.get("grp") else "")
        doc.add_paragraph(line, style="List Bullet")

    # Narrative sections
    for sec in payload.get("sections", []):
        doc.add_heading(sec.get("heading", ""), level=1)
        for para in str(sec.get("body", "")).split("\n\n"):
            if para.strip():
                doc.add_paragraph(para.strip())

    # Method-appropriate figure(s): grounded theory model, thematic map,
    # frequency chart, or framework heatmap
    try:
        from . import viz
        figures = viz.render_for_payload(payload)
    except Exception:  # noqa: BLE001 — figures are additive, never blocking
        import logging
        logging.getLogger("qualilens.viz").exception(
            "Figure generation failed; exporting report without figures")
        figures = []
    for caption, png in figures:
        doc.add_picture(BytesIO(png), width=Inches(6.3))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(caption)
        r.font.size = Pt(9)
        r.font.color.rgb = MUTED

    # Frequency table (content analysis)
    stats = payload.get("stats") or {}
    if stats.get("kind") == "content_frequencies" and stats.get("rows"):
        doc.add_heading("Code Frequency Table", level=1)
        groups = stats.get("groups", [])
        cols = 3 + len(groups)
        table = doc.add_table(rows=1, cols=cols)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Code"
        hdr[1].text = "Count"
        hdr[2].text = "%"
        for i, g in enumerate(groups):
            hdr[3 + i].text = g
        for row in stats["rows"]:
            cells = table.add_row().cells
            cells[0].text = row["code"]
            cells[1].text = str(row["count"])
            cells[2].text = f"{row['pct']}%"
            for i, g in enumerate(groups):
                cells[3 + i].text = str(row.get("by_group", {}).get(g, 0))

    # Framework matrix
    if stats.get("kind") == "framework_matrix" and stats.get("rows"):
        doc.add_heading("Framework Matrix", level=1)
        for row in stats["rows"]:
            doc.add_heading(row["source"], level=2)
            for cname, cell in row["cells"].items():
                if cell.get("n"):
                    p = doc.add_paragraph()
                    r = p.add_run(f"{cname} ({cell['n']}): ")
                    r.bold = True
                    p.add_run(cell.get("summary", ""))

    # Concept-by-paper matrix (literature synthesis) — rendered paper by
    # paper like the framework matrix; a grid wide enough for a full corpus
    # does not survive a page break
    if stats.get("kind") == "concept_matrix" and stats.get("rows"):
        doc.add_heading("Concept-by-Paper Matrix", level=1)
        for row in stats["rows"]:
            doc.add_heading(row["source"], level=2)
            for cname, cell in row["cells"].items():
                if cell.get("n"):
                    p = doc.add_paragraph()
                    r = p.add_run(f"{cname} ({cell['n']}): ")
                    r.bold = True
                    p.add_run(cell.get("summary", ""))

    # Themes with evidence (concepts, for a literature synthesis)
    doc.add_heading("Evidence: Concepts and Excerpts"
                    if payload.get("method") == "literature_synthesis"
                    else "Themes, Codes, and Evidence", level=1)
    for theme in payload.get("themes", []):
        doc.add_heading(theme["name"], level=2)
        if theme.get("definition"):
            p = doc.add_paragraph()
            r = p.add_run(theme["definition"])
            r.italic = True
        _write_excerpts(doc, theme.get("excerpts", []))
        for child in theme.get("children", []):
            doc.add_heading(child["name"], level=3)
            if child.get("definition"):
                p = doc.add_paragraph()
                r = p.add_run(child["definition"])
                r.italic = True
            _write_excerpts(doc, child.get("excerpts", []))

    # Extraction table appendix (literature synthesis)
    if stats.get("kind") == "concept_matrix" and stats.get("extraction_rows"):
        doc.add_heading("Appendix: Extraction Table", level=1)
        field_labels = stats.get("field_labels") or {}
        for row in stats["extraction_rows"]:
            head = row.get("label") or row.get("filename", "")
            if row.get("excluded"):
                head += "  (excluded from the synthesis)"
            doc.add_heading(head, level=2)
            if row.get("citation"):
                p = doc.add_paragraph()
                r = p.add_run(row["citation"])
                r.italic = True
                r.font.size = Pt(10)
            for key, text in (row.get("fields") or {}).items():
                if text:
                    p = doc.add_paragraph()
                    r = p.add_run(f"{field_labels.get(key, key)}: ")
                    r.bold = True
                    p.add_run(text)

    # Familiarization appendix
    summaries = [s for s in payload.get("source_summaries", []) if s.get("summary")]
    if summaries:
        doc.add_heading("Appendix: Source Summaries (Familiarization)", level=1)
        for s in summaries:
            doc.add_heading(s.get("source", ""), level=2)
            doc.add_paragraph(s["summary"])
            if s.get("memo"):
                p = doc.add_paragraph()
                r = p.add_run(f"Analytic memo: {s['memo']}")
                r.italic = True
                r.font.size = Pt(10)

    # Audit appendix
    doc.add_heading("Appendix: Audit Trail", level=1)
    audit = payload.get("audit", {})
    doc.add_paragraph(
        f"This analysis logged {audit.get('events', 0)} events. Researcher checkpoints:")
    for cp in audit.get("checkpoints", []):
        when_cp = ""
        if cp.get("resolved_at"):
            when_cp = " — resolved " + time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(cp["resolved_at"]))
        doc.add_paragraph(f"{cp.get('title', cp.get('stage'))} ({cp.get('status')}){when_cp}",
                          style="List Bullet")
    usage = audit.get("usage", {})
    if usage:
        doc.add_paragraph(
            f"Model usage: {usage.get('calls', 0)} calls, "
            f"{usage.get('input_tokens', 0):,} input tokens, "
            f"{usage.get('output_tokens', 0):,} output tokens.")

    # Colophon: provenance and a suggested software citation — deliberately
    # NOT a copyright notice, since the report's content belongs entirely to
    # the researchers who produced it (see the project NOTICE file).
    colophon = doc.add_paragraph()
    r = colophon.add_run(
        "This report was generated with QualiLens, free software by Ashita Aggarwal "
        "and Suraj Commuri (Apache-2.0). Suggested software citation: Aggarwal, A., & "
        "Commuri, S. (2026). QualiLens: A local application for LLM-assisted "
        "qualitative data analysis [Computer software]. The content of this report "
        "belongs to its authors.")
    r.font.size = Pt(8)
    r.font.color.rgb = MUTED

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _write_excerpts(doc, excerpts: list, limit: int = 12) -> None:
    for e in excerpts[:limit]:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.4)
        r = p.add_run(f"“{e['quote']}”")
        r.font.size = Pt(10)
        where = f"  — {e.get('source', '')}"
        if e.get("page"):
            where += f", p. {e['page']}"   # PDF page anchor, when known
        src = p.add_run(where)
        src.font.size = Pt(9)
        src.font.color.rgb = MUTED
        if e.get("memo"):
            m = doc.add_paragraph()
            m.paragraph_format.left_indent = Inches(0.6)
            mr = m.add_run(f"Memo: {e['memo']}")
            mr.font.size = Pt(9)
            mr.font.color.rgb = MUTED
    if len(excerpts) > limit:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.4)
        r = p.add_run(f"(+{len(excerpts) - limit} further excerpts in the project database)")
        r.font.size = Pt(9)
        r.font.color.rgb = MUTED
