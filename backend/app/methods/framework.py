# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Framework (deductive) analysis: load the researcher's codebook -> apply it
across sources (optionally flagging emergent candidates) -> (review, focused
on low-confidence and emergent assignments) -> framework matrix -> report."""

import json
from collections import defaultdict

from .. import db
from .base import Method, Question, Stage, apply_code_review_resolution
from . import common
from .content_analysis import parse_codebook

QUESTIONS = [
    Question("research_question", "Research question", type="textarea", required=True),
    Question("codebook_text", "Framework / codebook", type="textarea", required=True,
             help="One code per line as 'Code name: definition'. This is the a priori "
                  "framework the data will be charted against."),
    Question("allow_emergent", "Allow emergent codes?", type="toggle", default="true",
             help="If on, passages that fit no framework code but seem analytically "
                  "important are flagged as emergent candidates for your review."),
]

APPLY_SYSTEM = """You are performing FRAMEWORK ANALYSIS (deductive charting). Apply
the a priori framework codes to the source. For each relevant passage, assign
the single best-fitting framework code with a confidence from 0 to 1.
{emergent}"""

EMERGENT_ON = """If a passage is clearly important to the research question but fits
no framework code, return it under "emergent" with a proposed code name and
definition — sparingly, only when the fit failure is genuine."""
EMERGENT_OFF = "Do not propose codes outside the framework."


def stage_load_framework(ctx):
    ctx.reset_stage_codes("codebook")   # idempotent on resume after failure
    entries = parse_codebook(ctx.config.get("codebook_text", ""))
    if not entries:
        raise RuntimeError("No parseable framework codebook. Use one "
                           "'Code name: definition' per line.")
    for e in entries:
        ctx.add_code(e["name"], e["definition"], "codebook",
                     meta={"origin": "framework"})
    ctx.progress(1, 1, f"Loaded framework with {len(entries)} codes")


def stage_apply(ctx):
    allow_emergent = str(ctx.config.get("allow_emergent", "true")).lower() == "true"
    from .content_analysis import _match_key
    codebook = ctx.codes(stage="codebook")
    listing = "\n".join(f"- {c['name']}: {c['definition']}" for c in codebook)
    by_name = {_match_key(c["name"]): c["id"] for c in codebook}
    emergent_index = {_match_key(c["name"]): c["id"]
                      for c in ctx.codes(stage="emergent")}
    system = APPLY_SYSTEM.format(emergent=EMERGENT_ON if allow_emergent else EMERGENT_OFF)
    total_units = sum(len(ctx.segments(s)) for s in ctx.sources)
    done = 0
    for src in ctx.sources:
        for seg_i, seg_text in ctx.segments(src):
            unit = f"chart:{src['id']}:{seg_i}"
            if ctx.unit_done(unit):     # resumable: segment already charted
                done += 1
                continue
            ctx.progress(done, total_units, f"Charting {src['filename']}"
                         + (f" (part {seg_i + 1})" if seg_i else ""))
            schema = ('{"assignments": [{"code": "exact framework code name", '
                      '"quote": "verbatim passage", "confidence": 0.0, '
                      '"memo": "1-sentence justification"}]')
            if allow_emergent:
                schema += (', "emergent": [{"proposed_code": "...", "definition": "...", '
                           '"quote": "verbatim passage"}]')
            schema += "}"
            out = ctx.llm_json(
                system + "\n\n" + common.CODER_RULES,
                f"FRAMEWORK:\n{listing}\n\nSource: {src['filename']}\n---\n{seg_text}\n---\n"
                f"Return JSON: {schema}",
                purpose=f"chart:{src['filename']}:{seg_i}", max_tokens=8000)
            if isinstance(out, dict):
                for a in out.get("assignments", []):
                    cid = by_name.get(_match_key(str(a.get("code", ""))))
                    q = str(a.get("quote", "")).strip()
                    if cid and q:
                        try:
                            conf = float(a.get("confidence", 0.8))
                        except (TypeError, ValueError):
                            conf = 0.8
                        ctx.add_excerpt(cid, src["id"], q,
                                        memo=str(a.get("memo", "")), confidence=conf)
                for em in out.get("emergent", []) if allow_emergent else []:
                    name = str(em.get("proposed_code", "")).strip()
                    q = str(em.get("quote", "")).strip()
                    if not name or not q:
                        continue
                    cid = emergent_index.get(_match_key(name))
                    if not cid:
                        cid = ctx.add_code(name, str(em.get("definition", "")), "emergent",
                                           meta={"origin": "emergent"})
                        emergent_index[_match_key(name)] = cid
                    # no confidence: the model proposed this code, it did not
                    # rate the fit — presenting a number would be fabrication
                    ctx.add_excerpt(cid, src["id"], q)
            ctx.mark_unit(unit)
            done += 1
    ctx.progress(total_units, total_units, "Charting complete")


def cp_review_payload(ctx):
    """Focus the researcher on what needs judgment: low-confidence assignments
    and emergent code candidates."""
    low_conf = []
    rows = db.get_conn().execute(
        "SELECT e.*, c.name AS code_name FROM excerpts e JOIN codes c ON c.id=e.code_id "
        "WHERE e.run_id=? AND c.stage='codebook' AND e.confidence < 0.6 "
        "ORDER BY e.confidence ASC LIMIT 60", (ctx.run_id,)).fetchall()
    src_name = {s["id"]: s["filename"] for s in ctx.sources}
    for r in rows:
        low_conf.append({"excerpt_id": r["id"], "code": r["code_name"],
                         "quote": r["quote"][:400], "confidence": r["confidence"],
                         "source": src_name.get(r["source_id"], "?"), "memo": r["memo"]})
    emergent = []
    for c in ctx.codes(stage="emergent"):
        exs = ctx.excerpts_for(c["id"])
        emergent.append({"id": c["id"], "name": c["name"], "definition": c["definition"],
                         "excerpt_count": len(exs),
                         "sample_excerpts": [{"quote": e["quote"][:400],
                                              "source_id": e["source_id"], "memo": ""}
                                             for e in exs[:4]]})
    return ("Review charting",
            "Low-confidence assignments are listed for spot-checking (delete any that are "
            "wrong). Emergent code candidates can be promoted into the framework or "
            "discarded.",
            {"kind": "framework_review", "low_confidence": low_conf,
             "items": emergent, "stage": "emergent"})


def cp_review_apply(ctx, resolution):
    conn = db.get_conn()
    for ex in resolution.get("excerpt_deletions", []):
        row = conn.execute("SELECT quote, source_id, code_id FROM excerpts "
                           "WHERE id=? AND run_id=?", (ex, ctx.run_id)).fetchone()
        if not row:
            continue
        # preserve the removed evidence in the audit trail before deleting it
        db.log_event(ctx.run_id, "user_decision",
                     f"Researcher rejected excerpt {ex}",
                     {"quote": row["quote"], "source_id": row["source_id"],
                      "code_id": row["code_id"]})
        conn.execute("DELETE FROM excerpts WHERE id=? AND run_id=?", (ex, ctx.run_id))
    conn.commit()
    # decisions on emergent codes: keep => promote to codebook; delete => drop
    for d in resolution.get("decisions", []):
        row = conn.execute("SELECT name, definition FROM codes WHERE id=?",
                           (d.get("id"),)).fetchone()
        if not row:
            db.log_event(ctx.run_id, "info",
                         f"Skipped decision for unknown emergent code {d.get('id')}", d)
            continue
        if d.get("action") in ("keep", "rename"):
            conn.execute("UPDATE codes SET stage='codebook', name=?, definition=? WHERE id=?",
                         (d.get("name") or row["name"],
                          d.get("definition") or row["definition"], d["id"]))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher promoted emergent code '{row['name']}' into framework", d)
        elif d.get("action") == "delete":
            conn.execute("UPDATE codes SET status='deleted' WHERE id=?", (d["id"],))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher discarded emergent code '{row['name']}'", d)
        elif d.get("action") == "merge" and d.get("merge_into"):
            conn.execute("UPDATE excerpts SET code_id=? WHERE code_id=? AND run_id=?",
                         (d["merge_into"], d["id"], ctx.run_id))
            conn.execute("UPDATE codes SET status='merged', merged_into=? WHERE id=?",
                         (d["merge_into"], d["id"]))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher merged emergent code '{row['name']}' into {d['merge_into']}", d)
    conn.commit()


def stage_matrix_report(ctx):
    """Framework matrix: source x code, each cell a summary of that source's
    material under that code. One batched LLM call per source (not per cell),
    so cost scales with the number of sources, not sources x codes."""
    codebook = ctx.codes(stage="codebook")
    src_name = {s["id"]: s["filename"] for s in ctx.sources}
    cells = defaultdict(lambda: defaultdict(list))
    for c in codebook:
        for e in ctx.excerpts_for(c["id"]):
            cells[e["source_id"]][c["id"]].append(e["quote"])

    matrix_rows = ctx.state.get("matrix_rows", {})
    total = len(ctx.sources)
    for i, src in enumerate(ctx.sources):
        if src["id"] in matrix_rows:    # resumable: row already summarized
            continue
        row = {}
        nonempty = [(c, cells.get(src["id"], {}).get(c["id"], [])) for c in codebook]
        nonempty = [(c, qs) for c, qs in nonempty if qs]
        for c in codebook:
            row[c["name"]] = {"summary": "", "n": len(cells.get(src["id"], {}).get(c["id"], []))}
        if nonempty:
            ctx.progress(i, total, f"Charting matrix: {src['filename']}")
            blocks = []
            for c, qs in nonempty:
                joined = "\n".join(f"  - {q[:300]}" for q in qs[:10])
                blocks.append(f"CODE: {c['name']} — {c['definition']}\n{joined}")
            out = ctx.llm_json(
                "You are charting a framework-analysis matrix. For EACH code below, summarize "
                "in 1-2 sentences, strictly from the passages given, what this source says "
                "under that code. No interpretation beyond the passages.",
                f"Source: {src['filename']}\n\n" + "\n\n".join(blocks) +
                '\n\nReturn JSON: {"summaries": [{"code": "exact code name", '
                '"summary": "1-2 sentences"}]}',
                purpose=f"matrix:{src['filename']}", max_tokens=4000)
            for s in out.get("summaries", []) if isinstance(out, dict) else []:
                cname = str(s.get("code", "")).strip()
                if cname in row:
                    row[cname]["summary"] = str(s.get("summary", "")).strip()
        matrix_rows[src["id"]] = row
        ctx.state["matrix_rows"] = matrix_rows
        ctx.persist_state()
    ctx.progress(total, total, "Matrix complete")

    matrix = {"kind": "framework_matrix",
              "codes": [c["name"] for c in codebook],
              "rows": [{"source": src_name.get(sid, sid), "cells": row}
                       for sid, row in matrix_rows.items()]}

    matrix_text = ""
    for row in matrix["rows"]:
        matrix_text += f"\nSOURCE: {row['source']}\n"
        for cname, cell in row["cells"].items():
            if cell["n"]:
                matrix_text += f"  {cname} ({cell['n']}): {cell['summary']}\n"
    sections = common.narrate(
        ctx, "Framework analysis (deductive charting against an a priori framework)",
        "Framework matrix (source x code summaries):\n" + matrix_text)
    common.assemble_report(ctx, f"Framework Analysis: {ctx.project['name']}",
                           sections, "codebook", None, stats=matrix)


METHOD = Method(
    id="framework",
    label="Framework / Deductive Coding",
    description="Applies your a priori codebook to every source, flags emergent "
                "candidates and low-confidence assignments for review, and charts "
                "a framework matrix.",
    questions=QUESTIONS,
    stages=[
        Stage("load_framework", "Load framework", run=stage_load_framework),
        Stage("apply", "Chart sources against framework", run=stage_apply),
        Stage("review_charting", "Review charting", kind="checkpoint",
              build_payload=cp_review_payload, apply_resolution=cp_review_apply),
        Stage("matrix_report", "Framework matrix & report", run=stage_matrix_report),
    ],
)
