# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Grounded theory: open coding -> (review) -> axial coding -> (review) ->
selective coding -> (review) -> theory narrative."""

import functools

from .. import db
from .base import (Method, Question, Stage, apply_code_review_resolution,
                   build_code_review_payload)
from . import common

QUESTIONS = [
    Question("research_question", "Research question or phenomenon of interest",
             help="What are you trying to build theory about? Grounded theory can start "
                  "from a broad area rather than a fixed question.",
             type="textarea", required=True),
    Question("gt_variant", "Coding paradigm", type="select",
             options=["Straussian (axial coding with paradigm model)",
                      "Glaserian (emergent, no forced paradigm)"],
             default="Straussian (axial coding with paradigm model)",
             help="Straussian axial coding organizes categories around conditions, "
                  "actions/interactions, and consequences; Glaserian lets the "
                  "organizing logic emerge."),
    Question("sensitizing_concepts", "Sensitizing concepts (optional)",
             help="Concepts from prior literature you want the coder to stay alert to, "
                  "comma-separated. Leave blank for a fully emergent pass.",
             type="text"),
]

OPEN_CODING_SYSTEM = """You are performing OPEN CODING in a grounded theory study.
Work line-by-line in spirit: fracture the data into discrete incidents and label
each with a conceptual code. Prefer gerunds ('managing uncertainty', 'seeking
validation'). Use in-vivo codes (participants' own words) when a phrase is
analytically striking. Code actions, processes, and meanings — not topics.
Stay close to the data; this is not the stage for theoretical abstraction."""

AXIAL_SYSTEM_STRAUSS = """You are performing AXIAL CODING in a Straussian grounded
theory study. Group the open codes into conceptual categories, and for each
category identify (in the rationale) its place in the paradigm model where
evident: causal conditions, context, intervening conditions,
action/interaction strategies, and consequences. Categories must be grounded
in the codes given — do not import concepts absent from the data."""

AXIAL_SYSTEM_GLASER = """You are grouping open codes into emergent conceptual
categories in a Glaserian grounded theory study. Let the organizing logic
emerge from the codes themselves; do not force a coding paradigm or any
preconceived framework. Categories must earn their way in from the data."""


def stage_open_coding(ctx):
    sens = ctx.config.get("sensitizing_concepts", "").strip()
    system = OPEN_CODING_SYSTEM
    if sens:
        system += f"\nSensitizing concepts to stay alert to (do not force them): {sens}"
    common.run_coding_pass(ctx, "open_code", system)


def stage_axial(ctx):
    strauss = "Straussian" in ctx.config.get("gt_variant", "Straussian")
    common.group_codes(ctx, "open_code", "category",
                       AXIAL_SYSTEM_STRAUSS if strauss else AXIAL_SYSTEM_GLASER,
                       "category", "categories")


def stage_selective(ctx):
    """Identify the core category and relate all categories to it."""
    ctx.reset_stage_codes("core")   # idempotent on resume after failure
    cats = ctx.codes(stage="category")
    lines = []
    for c in cats:
        kids = [k for k in ctx.codes(stage="open_code") if k.get("parent_id") == c["id"]]
        n = sum(ctx.excerpt_count(k["id"]) for k in kids)
        lines.append(f"[{c['id']}] {c['name']} — {c['definition']} "
                     f"({len(kids)} codes, {n} excerpts) "
                     f"rationale: {c.get('meta', {}).get('rationale', '')}")
    ctx.progress(0, 1, "Selective coding: identifying core category")
    out = ctx.llm_json(
        "You are performing SELECTIVE CODING in a grounded theory study. Identify the core "
        "category — the central phenomenon with the greatest explanatory power, to which all "
        "other categories relate — and articulate the storyline that integrates them. The core "
        "category may be one of the existing categories or a higher-order concept that subsumes "
        "them, but it must be grounded in the categories given.",
        f"Research question: {ctx.config.get('research_question', '')}\n\n"
        "Categories:\n" + "\n".join(lines) +
        '\n\nReturn JSON: {"core_category": {"name": "...", "definition": "...", '
        '"is_existing_category_id": "id or null"}, '
        '"storyline": "1-2 paragraph integrative storyline", '
        '"relationships": [{"from_category_id": "...", "relation": "e.g. condition for / '
        'strategy for / consequence of", "to": "core or category id", "explanation": "..."}], '
        '"theoretical_gaps": ["places where the data are thin and theoretical sampling '
        'would be needed"]}',
        purpose="selective_coding", max_tokens=6000)
    core = out.get("core_category", {}) if isinstance(out, dict) else {}
    core_id = ctx.add_code(str(core.get("name", "Core category")),
                           str(core.get("definition", "")), "core",
                           meta={"storyline": out.get("storyline", ""),
                                 "relationships": out.get("relationships", []),
                                 "theoretical_gaps": out.get("theoretical_gaps", []),
                                 "is_existing_category_id": core.get("is_existing_category_id")})
    ctx.state["core_id"] = core_id
    ctx.progress(1, 1, "Core category identified")


def cp_core_payload(ctx):
    core = ctx.codes(stage="core")
    items = [{"id": c["id"], "name": c["name"], "definition": c["definition"],
              "storyline": c.get("meta", {}).get("storyline", ""),
              "relationships": c.get("meta", {}).get("relationships", []),
              "theoretical_gaps": c.get("meta", {}).get("theoretical_gaps", []),
              "existing_category_id": c.get("meta", {}).get("is_existing_category_id")}
             for c in core]
    # the categories the core integrates, named and weighed, so the review can
    # show each relationship by its category and draw the report's figure
    all_codes = ctx.codes()
    categories = []
    for cat in ctx.codes(stage="category"):
        kids = [k for k in all_codes if k.get("parent_id") == cat["id"]]
        categories.append({
            "id": cat["id"], "name": cat["name"], "codes": len(kids),
            "excerpts": ctx.excerpt_count(cat["id"]) + sum(ctx.excerpt_count(k["id"]) for k in kids)})
    return ("Review the core category",
            "Edit the core category's name, definition, and storyline, and check the "
            "places where the data are thin. The storyline is the spine of the final "
            "report.",
            {"kind": "core_review", "items": items, "categories": categories})


def cp_core_apply(ctx, resolution):
    """Apply the researcher's edits to the core category. Only a real change
    is written and logged — the panel submits every field whether or not it
    was touched, and an audit trail must not record edits that never
    happened. Decisions are scoped to this run's codes."""
    import json as _json
    conn = db.get_conn()
    for d in resolution.get("decisions", []):
        if not isinstance(d, dict):
            continue
        row = conn.execute("SELECT * FROM codes WHERE id=? AND run_id=? AND stage='core'",
                           (d.get("id"), ctx.run_id)).fetchone()
        if not row:
            db.log_event(ctx.run_id, "info",
                         f"Skipped core-category decision for unknown code {d.get('id')}")
            continue
        meta = db.row_to_dict(row, ("meta",))["meta"]
        new_name = (str(d["name"]).strip() if isinstance(d.get("name"), str)
                    and str(d["name"]).strip() else row["name"])
        new_def = (str(d["definition"]).strip() if isinstance(d.get("definition"), str)
                   else row["definition"])
        new_story = (str(d["storyline"]).strip() if isinstance(d.get("storyline"), str)
                     else str(meta.get("storyline", "")))
        # the places where the data are thin become the report's Theoretical
        # Sampling Recommendations word for word, so the review may edit them
        old_gaps = [str(g) for g in meta.get("theoretical_gaps", []) or []]
        new_gaps = ([str(g).strip() for g in d["theoretical_gaps"] if isinstance(g, str) and str(g).strip()]
                    if isinstance(d.get("theoretical_gaps"), list) else old_gaps)
        note = d.get("notes")
        if isinstance(note, str) and note.strip():
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher note on the core category: {note.strip()}",
                         {"id": d.get("id"), "notes": note.strip()})
        changed = []
        if new_name != row["name"]:
            changed.append("name")
        if new_def != row["definition"]:
            changed.append("definition")
        if new_story != str(meta.get("storyline", "")):
            changed.append("storyline")
        if new_gaps != old_gaps:
            changed.append("sampling recommendations")
        if not changed:
            db.log_event(ctx.run_id, "user_decision",
                         "Researcher approved the core category unchanged", {"id": d.get("id")})
            continue
        meta["storyline"] = new_story
        meta["theoretical_gaps"] = new_gaps
        meta["user_edited"] = True
        conn.execute("UPDATE codes SET name=?, definition=?, meta=? WHERE id=? AND run_id=?",
                     (new_name, new_def, _json.dumps(meta), d["id"], ctx.run_id))
        db.log_event(ctx.run_id, "user_decision",
                     f"Researcher edited the core category ({', '.join(changed)})",
                     {"id": d.get("id"), "changed": changed,
                      "name": new_name if "name" in changed else None})
    conn.commit()


def stage_theory_report(ctx):
    core = ctx.codes(stage="core")
    core_c = core[0] if core else {"name": "?", "definition": "", "meta": {}}
    structure = common.structure_summary_text(ctx, "category", "open_code")
    rel = core_c.get("meta", {}).get("relationships", [])
    rel_text = "\n".join(f"- {r.get('from_category_id')} --{r.get('relation')}--> {r.get('to')}: "
                         f"{r.get('explanation', '')}" for r in rel)
    extra = [{"heading": "The Grounded Theory",
              "body": f"Core category: {core_c['name']} — {core_c['definition']}\n\n"
                      f"{core_c.get('meta', {}).get('storyline', '')}"}]
    if core_c.get("meta", {}).get("theoretical_gaps"):
        extra.append({"heading": "Theoretical Sampling Recommendations",
                      "body": "\n".join("- " + g for g in core_c["meta"]["theoretical_gaps"])})
    sections = common.narrate(
        ctx, "Grounded theory (open, axial, and selective coding)",
        f"CORE CATEGORY: {core_c['name']} — {core_c['definition']}\n"
        f"Relationships to core:\n{rel_text}\n\n{structure}",
        extra_sections=extra)
    # structured model for the diagram: core + labeled category relationships;
    # existing_category_id lets renderers avoid drawing the core twice and
    # recognize relationships targeting the core under its category id
    stats = {"kind": "gt_model",
             "core": {"name": core_c["name"], "definition": core_c["definition"],
                      "existing_category_id":
                          core_c.get("meta", {}).get("is_existing_category_id")},
             "relationships": rel}
    common.assemble_report(ctx, f"Grounded Theory Analysis: {ctx.project['name']}",
                           sections, "category", "open_code", stats=stats)


METHOD = Method(
    id="grounded_theory",
    label="Grounded Theory",
    description="Builds theory from data through open coding, axial coding into "
                "categories, and selective coding around a core category. "
                "Checkpoints after each coding phase.",
    questions=QUESTIONS,
    stages=[
        Stage("familiarize", "Familiarization & memos", run=common.stage_familiarize),
        Stage("open_coding", "Open coding", run=stage_open_coding),
        Stage("review_open_codes", "Review open codes", kind="checkpoint",
              build_payload=functools.partial(
                  build_code_review_payload, stage="open_code",
                  title="Review open codes",
                  instructions="Rename, merge, or delete the open codes, and add any the "
                               "coder missed. A merged code's excerpts move into the code "
                               "it merges into."),
              apply_resolution=apply_code_review_resolution),
        Stage("axial_coding", "Axial coding", run=stage_axial),
        Stage("review_categories", "Review categories", kind="checkpoint",
              build_payload=functools.partial(
                  build_code_review_payload, stage="category",
                  title="Review categories",
                  instructions="Refine the category names and definitions, and check that "
                               "each category's codes belong together. Merge categories that "
                               "name one idea, and delete any that do not hold together."),
              apply_resolution=apply_code_review_resolution),
        Stage("selective_coding", "Selective coding", run=stage_selective),
        Stage("review_core", "Review core category", kind="checkpoint",
              build_payload=cp_core_payload, apply_resolution=cp_core_apply),
        Stage("theory_report", "Theory & report", run=stage_theory_report),
    ],
)
