# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Reflexive thematic analysis after Braun & Clarke's six phases:
familiarization -> initial coding -> (review) -> theme construction ->
theme review against the dataset -> (review) -> define & name -> report."""

import functools
import json

from .. import db
from .base import (Method, Question, Stage, apply_code_review_resolution,
                   build_code_review_payload)
from . import common

QUESTIONS = [
    Question("research_question", "Research question", type="textarea", required=True,
             help="The question the thematic analysis should answer."),
    Question("ta_orientation", "Coding orientation", type="select",
             options=["Inductive (data-driven)", "Deductive (theory-driven)"],
             default="Inductive (data-driven)",
             help="Inductive coding stays open to whatever the data offer; deductive "
                  "coding reads the data through a stated theoretical lens."),
    Question("ta_level", "Level of meaning", type="select",
             options=["Semantic (explicit, surface meanings)",
                      "Latent (underlying ideas and assumptions)"],
             default="Semantic (explicit, surface meanings)"),
    Question("theory_lens", "Theoretical lens (if deductive)", type="textarea",
             help="Name the theory/framework and its key constructs. Ignored for "
                  "inductive coding."),
]

CODING_SYSTEM = """You are generating INITIAL CODES in a reflexive thematic analysis
(Braun & Clarke). Code systematically across the entire extract: every segment
relevant to the research question gets a code. Codes are concise labels
capturing one analytically interesting feature of the data.
{orientation}
{level}"""


def stage_initial_coding(ctx):
    inductive = "Inductive" in ctx.config.get("ta_orientation", "Inductive")
    latent = "Latent" in ctx.config.get("ta_level", "Semantic")
    orientation = ("Work inductively: derive codes from the data, not from prior theory."
                   if inductive else
                   "Work deductively through this theoretical lens: "
                   + ctx.config.get("theory_lens", "(none provided)"))
    level = ("Code at the LATENT level: underlying ideas, assumptions, and "
             "conceptualizations beneath the surface of what is said."
             if latent else
             "Code at the SEMANTIC level: explicit, surface meanings of what is said.")
    common.run_coding_pass(ctx, "open_code",
                           CODING_SYSTEM.format(orientation=orientation, level=level))


THEME_SYSTEM = """You are constructing CANDIDATE THEMES in a reflexive thematic
analysis. A theme is a pattern of shared meaning organized around a central
concept — not a topic summary, not a data domain, not an interview question.
Prefer fewer, richer themes over many thin ones. A theme must be supported by
codes from more than one part of the dataset where possible."""


def stage_theme_construction(ctx):
    common.group_codes(ctx, "open_code", "theme", THEME_SYSTEM, "theme", "themes")


def stage_theme_review(ctx):
    """Phase 4: check candidate themes against the coded extracts — coherence,
    distinctness, coverage — and record the model's own critique for the
    researcher's checkpoint."""
    themes = ctx.codes(stage="theme")
    lines = []
    for t in themes:
        kids = [k for k in ctx.codes(stage="open_code") if k.get("parent_id") == t["id"]]
        quotes = []
        for k in kids[:8]:
            for e in ctx.excerpts_for(k["id"])[:2]:
                quotes.append(f'"{e["quote"][:160]}"')
        lines.append(f"[{t['id']}] {t['name']} — {t['definition']}\n  extracts: "
                     + " | ".join(quotes[:8]))
    ctx.progress(0, 1, "Reviewing themes against the data")
    out = ctx.llm_json(
        "You are performing Phase 4 of reflexive thematic analysis: reviewing candidate "
        "themes against the coded data. For each theme judge internal coherence (do the "
        "extracts form a meaningful pattern around one central concept?) and external "
        "distinctness (is it clearly separate from other themes?). Recommend keep, revise, "
        "merge, split, or discard — with reasons. Be willing to be critical.",
        f"Research question: {ctx.config.get('research_question', '')}\n\n"
        "Candidate themes with sample extracts:\n" + "\n".join(lines) +
        '\n\nReturn JSON: {"reviews": [{"theme_id": "...", "coherence": "strong|adequate|weak", '
        '"distinctness": "strong|adequate|weak", "recommendation": "keep|revise|merge|split|discard", '
        '"notes": "specific, actionable critique"}]}',
        purpose="theme_review", max_tokens=6000)
    reviews = {r.get("theme_id"): r for r in out.get("reviews", [])} if isinstance(out, dict) else {}
    conn = db.get_conn()
    for t in themes:
        r = reviews.get(t["id"])
        if r:
            meta = t.get("meta", {})
            meta["phase4_review"] = r
            conn.execute("UPDATE codes SET meta=? WHERE id=?", (json.dumps(meta), t["id"]))
    conn.commit()
    ctx.progress(1, 1, "Theme review complete")


def cp_theme_payload(ctx):
    title, instructions, payload = build_code_review_payload(
        ctx, stage="theme", title="Review themes",
        instructions="The model's Phase-4 critique of each candidate theme is shown. "
                     "Rename, merge, or discard themes; edits here define the final "
                     "structure of the report.")
    for item in payload["items"]:
        row = db.get_conn().execute("SELECT meta FROM codes WHERE id=?",
                                    (item["id"],)).fetchone()
        meta = json.loads(row["meta"]) if row else {}
        item["review"] = meta.get("phase4_review")
        item["rationale"] = meta.get("rationale", "")
    return title, instructions, payload


def stage_define_name(ctx):
    """Phase 5: definitive names and definitions — but ONLY for themes the
    researcher did not rename at the review checkpoint. A researcher's manual
    edit is final; the model never overwrites it."""
    themes = ctx.codes(stage="theme")
    untouched = [t for t in themes if not t.get("meta", {}).get("user_edited")]
    if not untouched:
        ctx.progress(1, 1, "All themes were researcher-named; nothing to define")
        return
    lines = []
    for t in untouched:
        kids = [k for k in ctx.codes(stage="open_code") if k.get("parent_id") == t["id"]]
        n = sum(ctx.excerpt_count(k["id"]) for k in kids)
        lines.append(f"[{t['id']}] {t['name']} — {t['definition']} "
                     f"({len(kids)} codes, {n} extracts)")
    ctx.progress(0, 1, "Defining and naming themes")
    out = ctx.llm_json(
        "You are performing Phase 5 of reflexive thematic analysis: defining and naming "
        "themes. For each theme write a crisp, evocative name (a short phrase, not a topic "
        "word) and a definition stating its central organizing concept, its scope, and its "
        "boundaries.",
        "Themes:\n" + "\n".join(lines) +
        '\n\nReturn JSON: {"themes": [{"theme_id": "...", "final_name": "...", '
        '"final_definition": "3-4 sentences: central concept, scope, boundary"}]}',
        purpose="define_name", max_tokens=4000)
    conn = db.get_conn()
    allowed = {t["id"] for t in untouched}
    for t in out.get("themes", []) if isinstance(out, dict) else []:
        if t.get("theme_id") in allowed:
            conn.execute("UPDATE codes SET name=?, definition=? WHERE id=?",
                         (str(t.get("final_name", "")).strip() or "Unnamed",
                          str(t.get("final_definition", "")).strip(), t["theme_id"]))
    conn.commit()
    ctx.progress(1, 1, "Themes defined")


def stage_report(ctx):
    structure = common.structure_summary_text(ctx, "theme", "open_code")
    sections = common.narrate(
        ctx, "Reflexive thematic analysis (Braun & Clarke, six phases)", structure)
    common.assemble_report(ctx, f"Thematic Analysis: {ctx.project['name']}",
                           sections, "theme", "open_code")


METHOD = Method(
    id="thematic",
    label="Thematic Analysis",
    description="Reflexive thematic analysis following Braun & Clarke's six phases, "
                "with checkpoints after initial coding and after theme review.",
    questions=QUESTIONS,
    stages=[
        Stage("familiarize", "Familiarization", run=common.stage_familiarize),
        Stage("initial_coding", "Initial coding", run=stage_initial_coding),
        Stage("review_codes", "Review initial codes", kind="checkpoint",
              build_payload=functools.partial(
                  build_code_review_payload, stage="open_code",
                  title="Review initial codes",
                  instructions="Rename, merge, or delete codes before themes are "
                               "constructed from them."),
              apply_resolution=apply_code_review_resolution),
        Stage("theme_construction", "Constructing themes", run=stage_theme_construction),
        Stage("theme_review", "Reviewing themes against data", run=stage_theme_review),
        Stage("review_themes", "Review themes", kind="checkpoint",
              build_payload=cp_theme_payload,
              apply_resolution=apply_code_review_resolution),
        Stage("define_name", "Defining & naming themes", run=stage_define_name),
        Stage("report", "Report", run=stage_report),
    ],
)
