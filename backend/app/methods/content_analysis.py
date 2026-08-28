# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Qualitative content analysis: derive or load a codebook -> (review) ->
apply codes across all sources -> quantify frequencies (overall and by
group) -> report."""

import json
from collections import defaultdict

from .. import db
from .base import (Method, Question, Stage, apply_code_review_resolution,
                   build_code_review_payload)
from . import common

QUESTIONS = [
    Question("research_question", "Research question", type="textarea", required=True),
    Question("ca_mode", "Codebook", type="select",
             options=["Inductive — derive the codebook from the data",
                      "Deductive — I will supply the codebook"],
             default="Inductive — derive the codebook from the data"),
    Question("codebook_text", "Codebook (if deductive)", type="textarea",
             help="One code per line as 'Code name: definition'. Ignored in "
                  "inductive mode."),
    Question("ca_level", "Content level", type="select",
             options=["Manifest (what is explicitly said)",
                      "Latent (interpreted underlying meaning)"],
             default="Manifest (what is explicitly said)"),
    Question("ca_compare_groups", "Compare groups?", type="toggle", default="false",
             help="If your sources belong to groups (e.g., sites, cohorts, time points), "
                  "assign each source a group label at upload and the report will "
                  "cross-tabulate code frequencies by group."),
]

DERIVE_SYSTEM = """You are deriving a CODEBOOK for qualitative content analysis.
From the sampled material, propose a set of mutually exclusive, exhaustive
categories at a consistent level of abstraction. Each code needs a name, a
clear definition, inclusion criteria, and one example from the data.
Aim for 8-20 codes: few enough to count meaningfully, many enough to
discriminate."""


def parse_codebook(text: str) -> list:
    codes = []
    for line in text.splitlines():
        line = line.strip().lstrip("-•* ")
        if not line:
            continue
        if ":" in line:
            name, definition = line.split(":", 1)
        else:
            name, definition = line, ""
        if name.strip():
            codes.append({"name": name.strip(), "definition": definition.strip()})
    return codes


def _match_key(name: str) -> str:
    """Normalize a code name for matching model echoes back to the codebook:
    casefold and strip surrounding punctuation/whitespace."""
    import string
    return name.strip().strip(string.punctuation + " ‘’“”").casefold()


def stage_codebook(ctx):
    ctx.reset_stage_codes("codebook")   # idempotent on resume after failure
    deductive = "Deductive" in ctx.config.get("ca_mode", "Inductive")
    if deductive:
        entries = parse_codebook(ctx.config.get("codebook_text", ""))
        if not entries:
            raise RuntimeError("Deductive mode selected but no parseable codebook was "
                               "supplied. Use one 'Code name: definition' per line.")
        for e in entries:
            ctx.add_code(e["name"], e["definition"], "codebook",
                         meta={"origin": "user_supplied"})
        ctx.progress(1, 1, f"Loaded {len(entries)} codebook entries")
        return
    # inductive: sample material across sources, one derivation call
    latent = "Latent" in ctx.config.get("ca_level", "Manifest")
    per_source = max(2000, 45000 // max(1, len(ctx.sources)))
    sample = "\n\n".join(
        f"--- {s['filename']} ---\n{s['text'][:per_source]}" for s in ctx.sources)
    ctx.progress(0, 1, "Deriving codebook from sampled material")
    out = ctx.llm_json(
        DERIVE_SYSTEM + ("\nCode at the LATENT level (interpreted underlying meaning)."
                         if latent else "\nCode at the MANIFEST level (explicit content)."),
        f"Research question: {ctx.config.get('research_question', '')}\n\n"
        f"Sampled material:\n{sample}\n\n"
        'Return JSON: {"codes": [{"name": "...", "definition": "...", '
        '"inclusion_criteria": "...", "example": "verbatim example from the material"}]}',
        purpose="derive_codebook", max_tokens=6000)
    for c in out.get("codes", []) if isinstance(out, dict) else []:
        if str(c.get("name", "")).strip():
            ctx.add_code(str(c["name"]), str(c.get("definition", "")), "codebook",
                         meta={"inclusion_criteria": c.get("inclusion_criteria", ""),
                               "example": c.get("example", ""), "origin": "derived"})
    ctx.progress(1, 1, "Codebook derived")


APPLY_SYSTEM = """You are APPLYING a fixed codebook in qualitative content analysis.
Code ONLY with the codes provided — never invent new codes. Identify every
passage that satisfies a code's definition; one passage may carry multiple
codes only if their definitions genuinely overlap on it. For each assignment
give a confidence from 0 to 1."""


def stage_apply(ctx):
    codebook = ctx.codes(stage="codebook")
    listing = "\n".join(
        f"- {c['name']}: {c['definition']}"
        + (f" (include when: {c['meta'].get('inclusion_criteria')})"
           if c.get("meta", {}).get("inclusion_criteria") else "")
        for c in codebook)
    by_name = {_match_key(c["name"]): c["id"] for c in codebook}
    total_units = sum(len(ctx.segments(s)) for s in ctx.sources)
    done = 0
    dropped = 0
    for src in ctx.sources:
        for seg_i, seg_text in ctx.segments(src):
            unit = f"apply:{src['id']}:{seg_i}"
            if ctx.unit_done(unit):     # resumable: segment already coded
                done += 1
                continue
            ctx.progress(done, total_units, f"Coding {src['filename']}"
                         + (f" (part {seg_i + 1})" if seg_i else ""))
            out = ctx.llm_json(
                APPLY_SYSTEM + "\n\n" + common.CODER_RULES,
                f"CODEBOOK:\n{listing}\n\nSource: {src['filename']}\n---\n{seg_text}\n---\n"
                'Return JSON: {"assignments": [{"code": "exact code name from the codebook", '
                '"quote": "verbatim passage", "confidence": 0.0}]}',
                purpose=f"apply:{src['filename']}:{seg_i}", max_tokens=8000)
            for a in out.get("assignments", []) if isinstance(out, dict) else []:
                cid = by_name.get(_match_key(str(a.get("code", ""))))
                q = str(a.get("quote", "")).strip()
                if cid and q:
                    try:
                        conf = float(a.get("confidence", 0.8))
                    except (TypeError, ValueError):
                        conf = 0.8
                    ctx.add_excerpt(cid, src["id"], q, confidence=conf)
                elif q:
                    dropped += 1
                    db.log_event(ctx.run_id, "info",
                                 f"Dropped assignment: model used code name "
                                 f"'{a.get('code')}' not in the codebook",
                                 {"source": src["filename"], "quote": q[:200]})
            ctx.mark_unit(unit)
            done += 1
    ctx.progress(total_units, total_units, "Coding complete")
    if dropped:
        db.log_event(ctx.run_id, "info",
                     f"{dropped} assignment(s) dropped for unmatched code names — "
                     "counts may undercount; see earlier events for details")


def compute_stats(ctx) -> dict:
    codebook = ctx.codes(stage="codebook")
    compare = str(ctx.config.get("ca_compare_groups", "false")).lower() == "true"
    groups = sorted({s.get("grp") or "Ungrouped" for s in ctx.sources}) if compare else []
    src_group = {s["id"]: (s.get("grp") or "Ungrouped") for s in ctx.sources}
    src_name = {s["id"]: s["filename"] for s in ctx.sources}

    rows = []
    total_all = 0
    by_group_totals = defaultdict(int)
    for c in codebook:
        exs = ctx.excerpts_for(c["id"])
        n = len(exs)
        total_all += n
        srcs = sorted({src_name.get(e["source_id"], "?") for e in exs})
        row = {"code": c["name"], "count": n,
               "sources": len(srcs), "source_names": srcs}
        if compare:
            gcounts = defaultdict(int)
            for e in exs:
                g = src_group.get(e["source_id"], "Ungrouped")
                gcounts[g] += 1
                by_group_totals[g] += 1
            row["by_group"] = {g: gcounts.get(g, 0) for g in groups}
        rows.append(row)
    rows.sort(key=lambda r: -r["count"])
    for r in rows:
        r["pct"] = round(100 * r["count"] / total_all, 1) if total_all else 0.0
    return {"kind": "content_frequencies", "total_assignments": total_all,
            "n_sources": len(ctx.sources), "groups": groups,
            "group_totals": dict(by_group_totals), "rows": rows}


def stage_quantify_report(ctx):
    stats = compute_stats(ctx)
    table_text = "\n".join(
        f"- {r['code']}: {r['count']} ({r['pct']}%) across {r['sources']} sources"
        + (f"; by group: {r['by_group']}" if "by_group" in r else "")
        for r in stats["rows"])
    level = ctx.config.get("ca_level", "Manifest")
    extra = [{"heading": "Code Frequencies",
              "body": f"Total coded passages: {stats['total_assignments']} across "
                      f"{stats['n_sources']} sources.\n{table_text}"}]
    sections = common.narrate(
        ctx, f"Qualitative content analysis ({level.split(' ')[0].lower()} level)",
        "Codebook with frequencies:\n" + table_text + "\n\nCodes and definitions:\n"
        + "\n".join(f"- {c['name']}: {c['definition']}" for c in ctx.codes(stage="codebook")),
        extra_sections=extra)
    common.assemble_report(ctx, f"Content Analysis: {ctx.project['name']}",
                           sections, "codebook", None, stats=stats)


def cp_codebook_payload(ctx):
    return build_code_review_payload(
        ctx, stage="codebook", title="Review the codebook",
        instructions="This codebook will be applied verbatim to every source. Tighten "
                     "definitions, merge overlapping codes, add missing ones — coding "
                     "quality is bounded by codebook quality.")


METHOD = Method(
    id="content_analysis",
    label="Content Analysis",
    description="Derives or applies a fixed codebook, codes every source against it, "
                "and reports code frequencies overall and by group.",
    questions=QUESTIONS,
    stages=[
        Stage("codebook", "Build codebook", run=stage_codebook),
        Stage("review_codebook", "Review codebook", kind="checkpoint",
              build_payload=cp_codebook_payload,
              apply_resolution=apply_code_review_resolution),
        Stage("apply", "Apply codes", run=stage_apply,
              # a branch back to the codebook review must re-code: the copied
              # coding belongs to the OLD codebook
              reset_units=("apply",), reset_excerpt_stages=("codebook",)),
        Stage("quantify_report", "Quantify & report", run=stage_quantify_report),
    ],
)
