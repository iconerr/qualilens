# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Framework shared by all analysis methods.

A Method is a sequence of Stages. Work stages call the LLM and write
codes/excerpts to the database; checkpoint stages pause the run, present
their payload to the researcher, and apply the researcher's decisions
before the pipeline continues. Every code assignment stores the exact
quote and its character offsets in the source — the provenance chain the
final report exposes.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .. import db, llm


@dataclass
class Stage:
    name: str
    label: str
    kind: str = "work"                       # work | checkpoint
    run: Optional[Callable] = None           # work: fn(ctx) -> None
    build_payload: Optional[Callable] = None  # checkpoint: fn(ctx) -> (title, instructions, payload)
    apply_resolution: Optional[Callable] = None  # checkpoint: fn(ctx, resolution) -> None
    # What this stage owns, for branching: when a branch re-enters the
    # pipeline BEFORE this stage, these are dropped from the copy so the
    # stage runs again instead of skipping on the source run's artifacts.
    resets: tuple = ()           # run-state keys (e.g. "matrix_rows")
    reset_units: tuple = ()      # done_units prefixes (e.g. "apply")
    reset_excerpt_stages: tuple = ()  # code stages whose excerpts this stage wrote


@dataclass
class Question:
    """A method-specific setup question rendered by the wizard."""
    key: str
    label: str
    help: str = ""
    type: str = "text"                       # text | textarea | select | toggle
    options: list = field(default_factory=list)
    default: str = ""
    required: bool = False


@dataclass
class Method:
    id: str
    label: str
    description: str
    questions: list
    stages: list

    def stage_names(self):
        return [{"name": s.name, "label": s.label, "kind": s.kind} for s in self.stages]


class Cancelled(Exception):
    """Raised inside a stage when the researcher cancels the run; stops
    further LLM spending immediately rather than at the next stage boundary."""


class RunContext:
    """Everything a stage needs: project data, config, LLM access, DB writes.

    All LLM calls flow through ctx.llm()/ctx.llm_json() so token usage is
    accumulated on the run row, each call is logged to the audit trail, and
    cancellation is honored before any money is spent.
    """

    SEGMENT_CHARS = 24000  # ~6k tokens per coding call

    def __init__(self, run_id: str, project: dict, sources: list, config: dict,
                 provider: str, model: str, api_key: str):
        self.run_id = run_id
        self.project = project
        self.sources = sources          # list of dicts: id, filename, text, grp
        self.config = config
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.state = {}                 # persisted between stages via runs.state

    # ---------- cancellation ----------

    def check_cancelled(self) -> None:
        row = db.get_conn().execute("SELECT status FROM runs WHERE id=?",
                                    (self.run_id,)).fetchone()
        if row and row["status"] == "cancelled":
            raise Cancelled()

    # ---------- resumable work units ----------
    # Long stages record each completed unit (a source segment, a matrix cell)
    # so a resume after failure skips finished work instead of re-billing it.

    def unit_done(self, key: str) -> bool:
        return key in self.state.get("done_units", [])

    def mark_unit(self, key: str) -> None:
        self.state.setdefault("done_units", []).append(key)
        self.persist_state()

    def clear_units(self, prefix: str) -> None:
        self.state["done_units"] = [
            k for k in self.state.get("done_units", []) if not k.startswith(prefix)]
        self.persist_state()

    def persist_state(self) -> None:
        conn = db.get_conn()
        conn.execute("UPDATE runs SET state=?, updated_at=? WHERE id=?",
                     (json.dumps(self.state), db.now(), self.run_id))
        conn.commit()

    # ---------- LLM ----------

    def llm(self, system: str, user: str, purpose: str, max_tokens: int = 8000) -> str:
        self.check_cancelled()
        try:
            text, usage = llm.chat(self.provider, self.model, self.api_key, system, user,
                                   max_tokens=max_tokens)
        except llm.LLMError as e:
            self._record_failed_usage(e, purpose)
            raise
        self._record_usage(usage, purpose)
        return text

    def llm_json(self, system: str, user: str, purpose: str, max_tokens: int = 8000):
        self.check_cancelled()
        try:
            data, usage = llm.chat_json(self.provider, self.model, self.api_key, system, user,
                                        max_tokens=max_tokens)
        except llm.LLMError as e:
            self._record_failed_usage(e, purpose)
            raise
        self._record_usage(usage, purpose)
        return data

    def _record_failed_usage(self, e: Exception, purpose: str) -> None:
        # a refused (truncated/empty) response was still billed — keep it in
        # the audit trail rather than losing the spend
        u = getattr(e, "usage", None)
        if isinstance(u, dict) and (u.get("input_tokens") or u.get("output_tokens")):
            self._record_usage(u, purpose + ":failed")

    def _record_usage(self, usage: dict, purpose: str) -> None:
        conn = db.get_conn()
        row = conn.execute("SELECT usage FROM runs WHERE id=?", (self.run_id,)).fetchone()
        acc = json.loads(row["usage"]) if row and row["usage"] else {}
        acc["input_tokens"] = acc.get("input_tokens", 0) + usage.get("input_tokens", 0)
        acc["output_tokens"] = acc.get("output_tokens", 0) + usage.get("output_tokens", 0)
        acc["calls"] = acc.get("calls", 0) + 1
        conn.execute("UPDATE runs SET usage=?, updated_at=? WHERE id=?",
                     (json.dumps(acc), db.now(), self.run_id))
        conn.commit()
        db.log_event(self.run_id, "llm", f"LLM call: {purpose}",
                     {"provider": self.provider, "model": self.model, **usage})

    # ---------- progress ----------

    def progress(self, done: int, total: int, detail: str = "") -> None:
        conn = db.get_conn()
        conn.execute("UPDATE runs SET progress=?, updated_at=? WHERE id=?",
                     (json.dumps({"done": done, "total": total, "detail": detail}),
                      db.now(), self.run_id))
        conn.commit()

    # ---------- DB writes ----------

    def reset_stage_codes(self, stage: str) -> None:
        """Idempotency for single-call grouping stages: wipe this stage's codes
        (and their excerpts / child links) so a re-run after failure rebuilds
        cleanly instead of duplicating."""
        conn = db.get_conn()
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM codes WHERE run_id=? AND stage=?",
            (self.run_id, stage)).fetchall()]
        for cid in ids:
            conn.execute("UPDATE codes SET parent_id=NULL WHERE parent_id=?", (cid,))
            conn.execute("DELETE FROM excerpts WHERE code_id=? AND run_id=?",
                         (cid, self.run_id))
            conn.execute("DELETE FROM codes WHERE id=?", (cid,))
        conn.commit()

    def add_code(self, name: str, definition: str, stage: str,
                 parent_id: str | None = None, meta: dict | None = None) -> str:
        cid = db.new_id()
        conn = db.get_conn()
        conn.execute(
            "INSERT INTO codes(id,run_id,name,definition,stage,parent_id,meta,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cid, self.run_id, name.strip(), definition.strip(), stage, parent_id,
             json.dumps(meta or {}), db.now()))
        conn.commit()
        return cid

    def add_excerpt(self, code_id: str, source_id: str, quote: str,
                    memo: str = "", confidence: float | None = None) -> str:
        src = next((s for s in self.sources if s["id"] == source_id), None)
        start, end = locate_quote(src["text"] if src else "", quote)
        eid = db.new_id()
        conn = db.get_conn()
        conn.execute(
            "INSERT INTO excerpts(id,run_id,code_id,source_id,quote,start_char,end_char,"
            "memo,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (eid, self.run_id, code_id, source_id, quote.strip(), start, end,
             memo.strip(), confidence, db.now()))
        conn.commit()
        return eid

    def codes(self, stage: str | None = None, active_only: bool = True) -> list:
        q = "SELECT * FROM codes WHERE run_id=?"
        args = [self.run_id]
        if stage:
            q += " AND stage=?"
            args.append(stage)
        if active_only:
            q += " AND status='active'"
        q += " ORDER BY created_at"
        rows = db.get_conn().execute(q, args).fetchall()
        return [db.row_to_dict(r, ("meta",)) for r in rows]

    def excerpts_for(self, code_id: str) -> list:
        rows = db.get_conn().execute(
            "SELECT * FROM excerpts WHERE run_id=? AND code_id=? ORDER BY created_at",
            (self.run_id, code_id)).fetchall()
        return [dict(r) for r in rows]

    def excerpt_count(self, code_id: str) -> int:
        row = db.get_conn().execute(
            "SELECT COUNT(*) c FROM excerpts WHERE run_id=? AND code_id=?",
            (self.run_id, code_id)).fetchone()
        return row["c"]

    # ---------- segmentation ----------

    def segments(self, source: dict) -> list:
        """Split source text at paragraph boundaries into LLM-sized segments.
        Returns [(seg_index, text), ...]."""
        return segment_text(source["text"], self.SEGMENT_CHARS)


def segment_text(text: str, max_chars: int) -> list:
    if len(text) <= max_chars:
        return [(0, text)]
    paras = re.split(r"(\n\s*\n)", text)  # keep separators to preserve offsets roughly
    segs, buf = [], ""
    for piece in paras:
        if len(buf) + len(piece) > max_chars and buf.strip():
            segs.append(buf)
            buf = piece
        else:
            buf += piece
    if buf.strip():
        segs.append(buf)
    # hard-split any segment that is still too large (e.g., no paragraph breaks)
    out = []
    for s in segs:
        while len(s) > max_chars:
            out.append(s[:max_chars])
            s = s[max_chars:]
        out.append(s)
    return list(enumerate(out))


# Models routinely normalize typographic characters when echoing quotes;
# fold both sides to the same plain form before matching.
_CHAR_FOLD = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "…": "...",
})


def locate_quote(text: str, quote: str) -> tuple:
    """Find quote offsets in source text: exact match, then punctuation- and
    whitespace-normalized regex search, then a partial head match (which may
    span less than the full quote). Returns (start, end) or (None, None)."""
    if not text or not quote:
        return None, None
    q = quote.strip()
    idx = text.find(q)
    if idx != -1:
        return idx, idx + len(q)
    # normalized: fold typographic characters, treat any whitespace/quote/dash
    # variant as equivalent, and search the original text positionally
    folded = q.translate(_CHAR_FOLD)
    pattern = re.escape(folded)
    pattern = re.sub(r"\\\s+|\\ ", r"\\s+", pattern)
    # re.escape (3.7+) leaves quote characters unescaped and escapes '-'
    pattern = (pattern.replace("'", "['‘’]")
                      .replace('"', '["“”]')
                      .replace("\\-", "[-–—]"))
    try:
        m = re.search(pattern, text)
        if m:
            return m.start(), m.end()
    except re.error:
        pass
    # last resort: locate the head of the quote (partial span — better than
    # nothing for "view in source", though shorter than the full quote)
    head = q[:80]
    idx = text.find(head)
    if idx != -1:
        return idx, idx + len(head)
    return None, None


# ---------- shared checkpoint machinery for code/theme review ----------

def build_code_review_payload(ctx: RunContext, stage: str, title: str,
                              instructions: str) -> tuple:
    items = []
    all_codes = ctx.codes()
    for c in ctx.codes(stage=stage):
        exs = list(ctx.excerpts_for(c["id"]))
        # a grouping code (theme/category) carries its evidence on child codes
        for child in all_codes:
            if child.get("parent_id") == c["id"]:
                exs.extend(ctx.excerpts_for(child["id"]))
        items.append({
            "id": c["id"], "name": c["name"], "definition": c["definition"],
            "excerpt_count": len(exs),
            "sample_excerpts": [
                {"quote": e["quote"][:400], "source_id": e["source_id"], "memo": e["memo"]}
                for e in exs[:4]
            ],
        })
    return title, instructions, {"kind": "code_review", "stage": stage, "items": items}


def apply_code_review_resolution(ctx: RunContext, resolution: dict) -> None:
    """Resolution format:
    {"decisions": [{"id": ..., "action": "keep|rename|merge|delete",
                    "name"?: ..., "definition"?: ..., "merge_into"?: id}]}

    Merges move the merged code's excerpts (and, for grouping codes, its child
    codes) to the target. Merge targets are resolved transitively across the
    whole batch first, so "A -> B" combined with "B -> C" or "delete B" in the
    same submission can never strand evidence on an inactive code.
    """
    conn = db.get_conn()
    decisions = resolution.get("decisions", [])
    action_of = {d.get("id"): d for d in decisions if d.get("id")}

    # Cycles in the declared merges (A->B, B->A; or A->A) canonicalize on the
    # first revisited node, which is then forced to stay kept — its own merge
    # decision is ignored so evidence always lands on an active code.
    forced_keep: set = set()

    def final_target(start_id: str) -> str | None:
        """Terminus of the merge chain declared in this batch, following from
        start_id's target. None = the chain ends in a deletion."""
        path = {start_id}
        cur = (action_of.get(start_id) or {}).get("merge_into")
        while cur:
            if cur in path:               # cycle: canonicalize here
                forced_keep.add(cur)
                return cur
            path.add(cur)
            if cur in forced_keep:
                return cur
            d2 = action_of.get(cur)
            act = (d2 or {}).get("action", "keep")
            if act == "delete":
                return None
            if act == "merge" and (d2 or {}).get("merge_into"):
                cur = d2["merge_into"]
                continue
            return cur
        return None

    for d in decisions:
        cid = d.get("id")
        action = d.get("action", "keep")
        row = conn.execute("SELECT name, definition, stage FROM codes WHERE id=?",
                           (cid,)).fetchone()
        if not row:
            db.log_event(ctx.run_id, "info",
                         f"Skipped decision for unknown code {cid}", d)
            continue
        if action == "rename" or (action == "keep" and
                                  (d.get("name") is not None or d.get("definition") is not None)):
            raw_name = d.get("name")
            raw_def = d.get("definition")
            # a blank name is invalid (keep the old); a blank definition is a
            # deliberate clearing (honor it)
            new_name = (str(raw_name).strip()
                        if isinstance(raw_name, str) and str(raw_name).strip()
                        else row["name"])
            new_def = str(raw_def) if isinstance(raw_def, str) else row["definition"]
            meta_row = conn.execute("SELECT meta FROM codes WHERE id=?", (cid,)).fetchone()
            meta = json.loads(meta_row["meta"]) if meta_row and meta_row["meta"] else {}
            meta["user_edited"] = True   # later automated stages must not overwrite
            conn.execute("UPDATE codes SET name=?, definition=?, meta=? WHERE id=?",
                         (new_name.strip(), new_def.strip(), json.dumps(meta), cid))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher edited code '{row['name']}' -> '{new_name}'", d)
        elif action == "merge" and d.get("merge_into"):
            if cid in forced_keep:
                db.log_event(ctx.run_id, "info",
                             f"Merge of {cid} skipped: it is the canonical member of a "
                             "circular merge and stays kept", d)
                continue
            target = final_target(cid)
            if target == cid:
                # self-merge or degenerate chain: keep the code as-is
                db.log_event(ctx.run_id, "info",
                             f"Merge of {cid} into itself ignored; code kept", d)
                continue
            if target is None:
                # chain ends in a deletion: treat as delete
                conn.execute("UPDATE codes SET status='deleted' WHERE id=?", (cid,))
                conn.execute("UPDATE codes SET parent_id=NULL WHERE parent_id=?", (cid,))
                db.log_event(ctx.run_id, "user_decision",
                             f"Researcher merged code {cid} into a deleted code; "
                             "treated as delete", d)
                continue
            conn.execute("UPDATE excerpts SET code_id=? WHERE code_id=? AND run_id=?",
                         (target, cid, ctx.run_id))
            # grouping codes: hand children to the merge target so their
            # evidence stays in the report
            conn.execute("UPDATE codes SET parent_id=? WHERE parent_id=?", (target, cid))
            conn.execute("UPDATE codes SET status='merged', merged_into=? WHERE id=?",
                         (target, cid))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher merged code '{row['name']}' ({cid}) into {target}", d)
        elif action == "delete":
            conn.execute("UPDATE codes SET status='deleted' WHERE id=?", (cid,))
            # orphan children explicitly; the report sweeps them into an
            # "Uncategorized" bucket rather than losing their evidence
            conn.execute("UPDATE codes SET parent_id=NULL WHERE parent_id=?", (cid,))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher deleted code '{row['name']}' ({cid})", d)
    for a in resolution.get("additions", []):
        name = str(a.get("name", "")).strip()
        if not name:
            continue
        cid = ctx.add_code(name, str(a.get("definition", "")),
                           resolution.get("stage") or a.get("stage", "open_code"),
                           meta={"user_edited": True, "origin": "researcher_added"})
        db.log_event(ctx.run_id, "user_decision", f"Researcher added code '{name}'",
                     {"id": cid})
    conn.commit()
