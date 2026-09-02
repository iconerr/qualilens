# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Framework (deductive) analysis: load the researcher's codebook -> apply it
across sources (optionally flagging emergent candidates) -> (review, focused
on low-confidence and emergent assignments) -> chart promoted emergent codes
across the whole corpus -> framework matrix -> report."""

import json
from collections import defaultdict

from .. import db
from .base import Method, Question, Stage, apply_code_review_resolution
from .base import locate_quote as base_locate
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
    dropped = 0
    for src in ctx.sources:
        for seg_i, seg_text, seg_start in ctx.segments(src):
            unit = f"chart:{src['id']}:{seg_i}"
            if ctx.unit_done(unit):     # resumable: segment already charted
                done += 1
                continue
            window = (seg_start, seg_start + len(seg_text))
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
                    if not isinstance(a, dict):
                        continue
                    cid = by_name.get(_match_key(str(a.get("code", ""))))
                    q = str(a.get("quote", "")).strip()
                    if cid and q:
                        ctx.add_excerpt(cid, src["id"], q,
                                        memo=str(a.get("memo", "")),
                                        confidence=_confidence_or_none(a),
                                        window=window)
                    elif q:
                        # the same mismatch content analysis logs; silence here
                        # made an empty column impossible to diagnose
                        dropped += 1
                        db.log_event(ctx.run_id, "info",
                                     f"Dropped assignment: model used code name "
                                     f"'{a.get('code')}' not in the framework",
                                     {"source": src["filename"], "quote": q[:200]})
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
                    ctx.add_excerpt(cid, src["id"], q, window=window)
            ctx.mark_unit(unit)
            done += 1
    ctx.progress(total_units, total_units, "Charting complete")
    if dropped:
        db.log_event(ctx.run_id, "info",
                     f"{dropped} assignment(s) dropped for unmatched framework code names — "
                     "a code empty across every source may be the symptom; see earlier events")


def _confidence_or_none(a: dict):
    """The model's stated confidence, or None when it gave none. A missing
    number is recorded as missing — substituting a default would present a
    rating the model never made, and would also hide the assignment from
    the low-confidence review."""
    v = a.get("confidence")
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:                         # NaN
        return None
    return max(0.0, min(1.0, f))


def cp_review_payload(ctx):
    """Focus the researcher on what needs judgment: low-confidence assignments
    and emergent code candidates."""
    low_conf = []
    conn = db.get_conn()
    # assignments with no stated confidence are reviewable too — they are
    # listed first, since nothing vouches for them
    where = ("WHERE e.run_id=? AND c.stage='codebook' AND c.status='active' "
             "AND (e.confidence IS NULL OR e.confidence < 0.6)")
    total_low = conn.execute(
        "SELECT COUNT(*) c FROM excerpts e JOIN codes c ON c.id=e.code_id " + where,
        (ctx.run_id,)).fetchone()["c"]
    rows = conn.execute(
        "SELECT e.*, c.name AS code_name FROM excerpts e JOIN codes c ON c.id=e.code_id "
        + where + " ORDER BY (e.confidence IS NOT NULL), e.confidence ASC LIMIT 60",
        (ctx.run_id,)).fetchall()
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
            "discarded; a promoted code is then charted across every source before the "
            "matrix is built.",
            {"kind": "framework_review", "low_confidence": low_conf,
             "low_confidence_total": total_low, "low_confidence_shown": len(low_conf),
             "items": emergent, "stage": "emergent"})


def cp_review_apply(ctx, resolution):
    conn = db.get_conn()
    own = {r["id"]: dict(r) for r in conn.execute(
        "SELECT id, name, stage, status FROM codes WHERE run_id=?", (ctx.run_id,)).fetchall()}
    # validate before mutating, so a refusal reopens the checkpoint cleanly
    for d in resolution.get("decisions", []):
        if not isinstance(d, dict):
            continue
        if d.get("id") and d["id"] not in own:
            raise ValueError(f"Decision refers to code {d['id']}, which is not part of this run.")
        if d.get("action") == "merge" and d.get("merge_into"):
            tgt = own.get(d["merge_into"])
            if tgt is None or tgt["status"] != "active":
                raise ValueError("Merge target is not an active code of this run.")
    promoted = list(ctx.state.get("promoted_codes", []))
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
        if not isinstance(d, dict):
            continue
        row = conn.execute("SELECT name, definition FROM codes WHERE id=? AND run_id=?",
                           (d.get("id"), ctx.run_id)).fetchone()
        if not row:
            db.log_event(ctx.run_id, "info",
                         f"Skipped decision for unknown emergent code {d.get('id')}", d)
            continue
        if d.get("action") in ("keep", "rename"):
            meta_row = conn.execute("SELECT meta FROM codes WHERE id=? AND run_id=?",
                                    (d["id"], ctx.run_id)).fetchone()
            try:
                meta = json.loads(meta_row["meta"] or "{}") if meta_row else {}
            except ValueError:
                meta = {}
            meta["promoted"] = True
            conn.execute("UPDATE codes SET stage='codebook', name=?, definition=?, meta=? "
                         "WHERE id=? AND run_id=?",
                         (d.get("name") or row["name"],
                          d.get("definition") or row["definition"], json.dumps(meta),
                          d["id"], ctx.run_id))
            if d["id"] not in promoted:
                promoted.append(d["id"])
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher promoted emergent code '{row['name']}' into framework; "
                         "it will be charted across every source before the matrix", d)
        elif d.get("action") == "delete":
            conn.execute("UPDATE codes SET status='deleted' WHERE id=? AND run_id=?",
                         (d["id"], ctx.run_id))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher discarded emergent code '{row['name']}'", d)
        elif d.get("action") == "merge" and d.get("merge_into"):
            conn.execute("UPDATE excerpts SET code_id=? WHERE code_id=? AND run_id=?",
                         (d["merge_into"], d["id"], ctx.run_id))
            conn.execute("UPDATE codes SET status='merged', merged_into=? WHERE id=? AND run_id=?",
                         (d["merge_into"], d["id"], ctx.run_id))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher merged emergent code '{row['name']}' into {d['merge_into']}", d)
    conn.commit()
    ctx.state["promoted_codes"] = promoted
    ctx.persist_state()


def stage_chart_promoted(ctx):
    """A code promoted from the emergent candidates entered the framework
    with only the passages the model happened to flag. Chart the promoted
    codes across every segment of every source (one call per segment, all
    promoted codes together) so their matrix columns mean what the other
    columns mean. Resumable per segment; a no-op when nothing was promoted."""
    from .content_analysis import _match_key
    promoted_ids = [c for c in ctx.state.get("promoted_codes", [])]
    codes = [c for c in ctx.codes(stage="codebook") if c["id"] in promoted_ids]
    if not codes:
        ctx.progress(1, 1, "No promoted codes to chart")
        return
    listing = "\n".join(f"- {c['name']}: {c['definition']}" for c in codes)
    by_name = {_match_key(c["name"]): c["id"] for c in codes}
    # the passages already on these codes (from the emergent pass) must not
    # be duplicated: skip a quote that locates inside an existing span
    existing = {}
    for c in codes:
        existing[c["id"]] = [(e["source_id"], e["start_char"], e["end_char"], e["quote"])
                             for e in ctx.excerpts_for(c["id"])]
    total_units = sum(len(ctx.segments(s)) for s in ctx.sources)
    done = 0
    for src in ctx.sources:
        for seg_i, seg_text, seg_start in ctx.segments(src):
            unit = f"rechart:{src['id']}:{seg_i}"
            if ctx.unit_done(unit):
                done += 1
                continue
            ctx.progress(done, total_units, f"Charting promoted codes: {src['filename']}"
                         + (f" (part {seg_i + 1})" if seg_i else ""))
            out = ctx.llm_json(
                APPLY_SYSTEM.format(emergent=EMERGENT_OFF) + "\n\n" + common.CODER_RULES,
                f"FRAMEWORK (only these codes):\n{listing}\n\nSource: {src['filename']}\n---\n"
                f"{seg_text}\n---\nReturn JSON: {{\"assignments\": [{{\"code\": \"exact "
                f"framework code name\", \"quote\": \"verbatim passage\", \"confidence\": 0.0, "
                f"\"memo\": \"1-sentence justification\"}}]}}",
                purpose=f"rechart:{src['filename']}:{seg_i}", max_tokens=8000)
            window = (seg_start, seg_start + len(seg_text))
            for a in out.get("assignments", []) if isinstance(out, dict) else []:
                if not isinstance(a, dict):
                    continue
                cid = by_name.get(_match_key(str(a.get("code", ""))))
                q = str(a.get("quote", "")).strip()
                if not (cid and q):
                    continue
                span = base_locate(src["text"], q, window)
                dup = False
                for (sid, st, en, oq) in existing.get(cid, []):
                    if sid != src["id"]:
                        continue
                    if span[0] is not None and st is not None and en is not None \
                            and st <= span[0] < en:
                        dup = True
                        break
                    if oq.strip() == q:
                        dup = True
                        break
                if dup:
                    continue
                eid = ctx.add_excerpt(cid, src["id"], q, memo=str(a.get("memo", "")),
                                      confidence=_confidence_or_none(a), window=window)
                existing.setdefault(cid, []).append((src["id"], span[0], span[1], q))
                del eid
            ctx.mark_unit(unit)
            done += 1
    ctx.progress(total_units, total_units, "Promoted codes charted")
    db.log_event(ctx.run_id, "stage",
                 f"Charted {len(codes)} promoted code(s) across the corpus")


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
        Stage("apply", "Chart sources against framework", run=stage_apply,
              # declared for completeness: no checkpoint precedes this stage
              # today, so a branch can never land before it
              reset_units=("chart",), reset_excerpt_stages=("codebook", "emergent")),
        Stage("review_charting", "Review charting", kind="checkpoint",
              build_payload=cp_review_payload, apply_resolution=cp_review_apply),
        Stage("chart_promoted", "Chart promoted codes", run=stage_chart_promoted,
              resets=("promoted_codes",), reset_units=("rechart",)),
        Stage("matrix_report", "Framework matrix & report", run=stage_matrix_report,
              resets=("matrix_rows",)),
    ],
)
