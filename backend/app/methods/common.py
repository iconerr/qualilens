# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Shared stage implementations: familiarization, per-source coding loops,
and report assembly used across methods."""

import json

from .. import db, ingestion
from .base import RunContext

CODER_RULES = """Rules for every excerpt you return:
- "quote" must be copied VERBATIM from the source text — exact characters,
  no paraphrase, no ellipses, no corrections of typos. Quotes that do not
  appear verbatim in the source will be rejected.
- Keep quotes focused: typically 1-4 sentences, the minimal span that
  evidences the code.
- Do not invent content. If nothing in the text fits, return fewer items."""


def stage_familiarize(ctx: RunContext) -> None:
    """Per-source structured summary + analytic memo. The memo feeds the
    coding prompts as context, and summaries appear in the report appendix."""
    rq = ctx.config.get("research_question", "").strip()
    summaries = ctx.state.get("summaries", {})
    total = len(ctx.sources)
    for i, src in enumerate(ctx.sources):
        if src["id"] in summaries:      # resumable: skip sources already read
            continue
        ctx.progress(i, total, f"Familiarization: {src['filename']}")
        text = src["text"][:60000]
        out = ctx.llm_json(
            "You are a qualitative researcher reading data closely for the first time. "
            "Produce a faithful summary and an analytic memo. Do not code yet.",
            f"Research question (if any): {rq or 'not specified'}\n\n"
            f"Source: {src['filename']}\n---\n{text}\n---\n"
            'Return JSON: {"summary": "150-250 word faithful summary", '
            '"memo": "100-200 word analytic memo: tensions, surprises, context worth remembering", '
            '"notable_features": ["3-6 short bullets"]}',
            purpose=f"familiarize:{src['filename']}", max_tokens=2000)
        # validate BEFORE persisting: a malformed response must fail the stage
        # (resume retries the call) rather than poison resumable state forever
        if isinstance(out, list) and out and isinstance(out[0], dict):
            out = out[0]
        if not isinstance(out, dict):
            raise RuntimeError(
                f"Familiarization of {src['filename']} returned "
                f"{type(out).__name__} instead of an object; resume the run to retry.")
        summaries[src["id"]] = out
        ctx.state["summaries"] = summaries
        ctx.persist_state()             # survive a failure mid-familiarization
    ctx.progress(total, total, "Familiarization complete")


def run_coding_pass(ctx: RunContext, stage: str, system_prompt: str,
                    existing_codes_note: bool = True) -> None:
    """Per-source, per-segment coding loop. The system prompt defines the
    method-specific coding stance; this handles segmentation, code reuse
    across sources, and provenance capture."""
    rq = ctx.config.get("research_question", "").strip()
    total_units = sum(len(ctx.segments(s)) for s in ctx.sources)
    done = 0
    code_index = {}  # lowercase name -> code_id, for reuse across sources

    for c in ctx.codes(stage=stage):
        code_index[c["name"].lower()] = c["id"]

    summaries = ctx.state.get("summaries", {})
    for src in ctx.sources:
        s = summaries.get(src["id"])
        memo = s.get("memo", "") if isinstance(s, dict) else ""
        for seg_i, seg_text in ctx.segments(src):
            unit = f"{stage}:{src['id']}:{seg_i}"
            if ctx.unit_done(unit):     # resumable: this segment already coded
                done += 1
                continue
            ctx.progress(done, total_units,
                         f"Coding {src['filename']}" +
                         (f" (part {seg_i + 1})" if seg_i else ""))
            existing = ""
            if existing_codes_note and code_index:
                listing = "\n".join(f"- {c['name']}: {c['definition'][:120]}"
                                    for c in ctx.codes(stage=stage)[:120])
                existing = ("\nCodes already in use (REUSE these names verbatim when the "
                            f"same idea recurs; create new codes only for new ideas):\n{listing}\n")
            memo_note = f"\nAnalytic memo from first reading of this source: {memo}\n" if memo else ""
            out = ctx.llm_json(
                system_prompt + "\n\n" + CODER_RULES,
                f"Research question (if any): {rq or 'not specified'}\n"
                f"{existing}{memo_note}\n"
                f"Source: {src['filename']}\n---\n{seg_text}\n---\n"
                'Return JSON: {"codes": [{"name": "short gerund-style label", '
                '"definition": "one-sentence definition", '
                '"excerpts": [{"quote": "verbatim span", "memo": "why this fits (1 sentence)"}]}]}',
                purpose=f"{stage}:{src['filename']}:{seg_i}", max_tokens=8000)
            for c in out.get("codes", []) if isinstance(out, dict) else []:
                name = str(c.get("name", "")).strip()
                if not name:
                    continue
                cid = code_index.get(name.lower())
                if not cid:
                    cid = ctx.add_code(name, str(c.get("definition", "")), stage)
                    code_index[name.lower()] = cid
                for e in c.get("excerpts", []):
                    q = str(e.get("quote", "")).strip()
                    if q:
                        ctx.add_excerpt(cid, src["id"], q, memo=str(e.get("memo", "")))
            ctx.mark_unit(unit)
            done += 1
    ctx.progress(total_units, total_units, "Coding complete")
    db.log_event(ctx.run_id, "stage",
                 f"Coding pass produced {len(ctx.codes(stage=stage))} codes")


def group_codes(ctx: RunContext, child_stage: str, parent_stage: str,
                system_prompt: str, item_label: str, item_plural: str) -> None:
    """Cluster active child-stage codes into parent-stage groupings
    (categories/themes) in a single LLM call over the full code list."""
    # idempotent on re-run after failure: rebuild this stage's output cleanly
    ctx.reset_stage_codes(parent_stage)
    codes = ctx.codes(stage=child_stage)
    if not codes:
        raise RuntimeError(f"No {child_stage} codes to group — nothing was coded.")
    lines = []
    for c in codes:
        n = ctx.excerpt_count(c["id"])
        sample = ctx.excerpts_for(c["id"])[:2]
        quotes = " | ".join(e["quote"][:150] for e in sample)
        lines.append(f"[{c['id']}] {c['name']} ({n} excerpts) — {c['definition']}"
                     + (f" e.g. \"{quotes}\"" if quotes else ""))
    rq = ctx.config.get("research_question", "").strip()
    ctx.progress(0, 1, f"Constructing {item_plural} from {len(codes)} codes")
    out = ctx.llm_json(
        system_prompt,
        f"Research question (if any): {rq or 'not specified'}\n\n"
        f"Codes (id, name, excerpt count, definition, sample quotes):\n" + "\n".join(lines) +
        f"\n\nReturn JSON: {{\"{item_plural}\": [{{\"name\": \"...\", "
        f"\"definition\": \"2-3 sentence definition\", "
        f"\"rationale\": \"why these codes cohere\", "
        f"\"code_ids\": [\"id\", ...]}}]}}\n"
        f"Every code id must appear in exactly one {item_label}. If a code fits nowhere, "
        f"place it in a {item_label} named 'Uncategorized' with a rationale.",
        purpose=f"group:{parent_stage}", max_tokens=8000)
    conn = db.get_conn()
    assigned = set()
    groups = []
    if isinstance(out, dict):
        # accept the requested key plus common variants the model might use
        for key in (item_plural, f"{item_label}s", "groups", "items"):
            if isinstance(out.get(key), list):
                groups = out[key]
                break
    if not groups:
        # refuse to degrade the whole analysis into one "Uncategorized" bucket
        raise RuntimeError(
            f"The model returned no {item_plural} (response did not follow the requested "
            "structure). Resume the run to retry this stage — nothing was lost.")
    for g in groups:
        pid = ctx.add_code(str(g.get("name", "Unnamed")), str(g.get("definition", "")),
                           parent_stage, meta={"rationale": g.get("rationale", "")})
        for cid in g.get("code_ids", []):
            if any(c["id"] == cid for c in codes):
                conn.execute("UPDATE codes SET parent_id=? WHERE id=?", (pid, cid))
                assigned.add(cid)
    # orphans -> Uncategorized
    orphans = [c for c in codes if c["id"] not in assigned]
    if orphans:
        pid = ctx.add_code("Uncategorized", "Codes not grouped by the model.", parent_stage)
        for c in orphans:
            conn.execute("UPDATE codes SET parent_id=? WHERE id=?", (pid, c["id"]))
    conn.commit()
    ctx.progress(1, 1, f"{item_plural.capitalize()} constructed")


def assemble_report(ctx: RunContext, title: str, narrative_sections: list,
                    top_stage: str, child_stage: str | None,
                    stats: dict | None = None) -> None:
    """Build the report payload: narrative sections + full provenance tree."""
    themes = []
    parents = ctx.codes(stage=top_stage)
    parent_ids = {p["id"] for p in parents}
    claimed_children = set()
    for parent in parents:
        node = {
            "id": parent["id"], "name": parent["name"],
            "definition": parent["definition"],
            "meta": parent.get("meta", {}),
            "children": [], "excerpts": [],
        }
        direct = ctx.excerpts_for(parent["id"])
        node["excerpts"] = [_excerpt_view(ctx, e) for e in direct]
        if child_stage:
            kids = [c for c in ctx.codes(stage=child_stage) if c.get("parent_id") == parent["id"]]
            for k in kids:
                claimed_children.add(k["id"])
                exs = ctx.excerpts_for(k["id"])
                node["children"].append({
                    "id": k["id"], "name": k["name"], "definition": k["definition"],
                    "excerpts": [_excerpt_view(ctx, e) for e in exs],
                })
        themes.append(node)

    # Safety net: child codes whose parent was deleted or is inactive must not
    # silently vanish from the report — sweep them into an explicit bucket.
    if child_stage:
        orphans = [c for c in ctx.codes(stage=child_stage)
                   if c["id"] not in claimed_children
                   and c.get("parent_id") not in parent_ids]
        orphans = [c for c in orphans if ctx.excerpt_count(c["id"])]
        if orphans:
            themes.append({
                "id": "_uncategorized", "name": "Uncategorized",
                "definition": "Codes whose grouping was removed during review; their "
                              "evidence is preserved here.",
                "meta": {}, "excerpts": [],
                "children": [{
                    "id": c["id"], "name": c["name"], "definition": c["definition"],
                    "excerpts": [_excerpt_view(ctx, e) for e in ctx.excerpts_for(c["id"])],
                } for c in orphans],
            })

    conn = db.get_conn()
    n_events = conn.execute("SELECT COUNT(*) c FROM events WHERE run_id=?",
                            (ctx.run_id,)).fetchone()["c"]
    cps = conn.execute(
        "SELECT stage,title,status,resolved_at FROM checkpoints WHERE run_id=? ORDER BY created_at",
        (ctx.run_id,)).fetchall()
    usage_row = conn.execute("SELECT usage FROM runs WHERE id=?", (ctx.run_id,)).fetchone()

    payload = {
        "title": title,
        "method": ctx.project["method"],
        "project_name": ctx.project["name"],
        "generated_at": db.now(),
        "provider": ctx.provider, "model": ctx.model,
        "sources": [{"id": s["id"], "filename": s["filename"], "grp": s.get("grp")}
                    for s in ctx.sources],
        "sections": narrative_sections,
        "themes": themes,
        "source_summaries": [
            {"source_id": sid,
             "source": next(src["filename"] for src in ctx.sources if src["id"] == sid),
             "summary": s.get("summary", ""),
             "memo": s.get("memo", "")}
            for sid, s in ctx.state.get("summaries", {}).items()
            if isinstance(s, dict) and any(src["id"] == sid for src in ctx.sources)
        ],
        "stats": stats or {},
        "audit": {
            "events": n_events,
            "checkpoints": [dict(c) for c in cps],
            "usage": json.loads(usage_row["usage"]) if usage_row else {},
        },
    }
    conn.execute("INSERT OR REPLACE INTO reports(run_id,payload,created_at) VALUES(?,?,?)",
                 (ctx.run_id, json.dumps(payload), db.now()))
    conn.commit()


def _excerpt_view(ctx: RunContext, e: dict) -> dict:
    src = next((s for s in ctx.sources if s["id"] == e["source_id"]), None)
    meta = src.get("meta") if src else None
    pages = meta.get("pages") if isinstance(meta, dict) else None
    return {
        "id": e["id"],
        "quote": e["quote"], "memo": e["memo"],
        "source_id": e["source_id"],
        "source": src["filename"] if src else e["source_id"],
        "start_char": e["start_char"], "end_char": e["end_char"],
        "confidence": e["confidence"],
        "page": ingestion.page_for_offset(pages or [], e["start_char"]),
    }


def narrate(ctx: RunContext, method_desc: str, structure_summary: str,
            extra_sections: list | None = None) -> list:
    """Generate the report's narrative sections from the final structure."""
    rq = ctx.config.get("research_question", "").strip()
    out = ctx.llm_json(
        "You write the findings section of a qualitative research report. Ground every claim "
        "in the coded structure provided; never invent quotes or findings. Academic register, "
        "past tense for what was done, present tense for interpretation. Refer to themes and "
        "codes by their exact names.",
        f"Method: {method_desc}\nResearch question: {rq or 'not specified'}\n\n"
        f"Final analytic structure (with excerpt counts and sample quotes):\n{structure_summary}\n\n"
        'Return JSON: {"sections": [{"heading": "Overview of Findings", "body": "2-3 paragraphs"}, '
        '{"heading": "Findings by Theme", "body": "one substantive paragraph per top-level '
        'theme/category, in order"}, '
        '{"heading": "Integration", "body": "how the themes relate; 1-2 paragraphs"}, '
        '{"heading": "Limitations of This Analysis", "body": "honest limitations of '
        'LLM-assisted coding for this dataset; 1 paragraph"}]}',
        purpose="report:narrative", max_tokens=8000)
    sections = out.get("sections", []) if isinstance(out, dict) else []
    if extra_sections:
        sections = extra_sections + sections
    return sections


def structure_summary_text(ctx: RunContext, top_stage: str, child_stage: str | None) -> str:
    lines = []
    for parent in ctx.codes(stage=top_stage):
        n = ctx.excerpt_count(parent["id"])
        lines.append(f"THEME: {parent['name']} — {parent['definition']} ({n} direct excerpts)")
        if child_stage:
            for k in [c for c in ctx.codes(stage=child_stage)
                      if c.get("parent_id") == parent["id"]]:
                kn = ctx.excerpt_count(k["id"])
                sample = ctx.excerpts_for(k["id"])[:2]
                qs = " | ".join(f'"{e["quote"][:120]}"' for e in sample)
                lines.append(f"  code: {k['name']} ({kn} excerpts) {qs}")
    return "\n".join(lines)
