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
                    memo: str = "", confidence: float | None = None,
                    window: tuple | None = None) -> str:
        """Store one excerpt with its located span. `window` is the (start,
        end) of the segment the model was reading, so a phrase that recurs
        in the document is located where it was actually coded rather than
        at its first occurrence."""
        src = next((s for s in self.sources if s["id"] == source_id), None)
        start, end = locate_quote(src["text"] if src else "", quote, window=window)
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
        Returns [(seg_index, text, start_offset), ...]; the segments are
        contiguous slices, so text[start:start+len(seg)] == seg."""
        return segment_text(source["text"], self.SEGMENT_CHARS)


def segment_text(text: str, max_chars: int) -> list:
    if len(text) <= max_chars:
        return [(0, text, 0)]
    paras = re.split(r"(\n\s*\n)", text)  # keep separators: pieces concatenate to text
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
    # offsets: the pieces are contiguous prefixes of the original text
    result, pos = [], 0
    for i, s in enumerate(out):
        result.append((i, s, pos))
        pos += len(s)
    return result


# Models routinely normalize typographic characters when echoing quotes;
# fold both sides to the same plain form before matching.
_CHAR_FOLD = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "…": "...",
})


def _normalize_for_match(s: str) -> tuple:
    """Canonical form of a text for tolerant matching, with a map from every
    canonical index back to the original index. The canonical form folds
    typographic characters, case (casefold), NFKC compatibility forms
    (ligatures), drops soft hyphens, joins words hyphenated across a line
    break ("counter-\\nintuitive" -> "counterintuitive"), and collapses any
    whitespace run to one space. Offsets are code points of the original."""
    import unicodedata
    from array import array
    out, idx = [], array("i")
    n = len(s)
    i = 0
    prev_space = False
    while i < n:
        ch = s[i]
        if ch == "\u00ad":                 # soft hyphen: never visible
            i += 1
            continue
        if ch == "-" and i + 1 < n and s[i + 1] in "\r\n":
            # a hyphen at a line end joins the word across the break
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            i = j
            continue
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                idx.append(i)
                prev_space = True
            i += 1
            continue
        prev_space = False
        folded = unicodedata.normalize("NFKC", ch.translate(_CHAR_FOLD)).casefold()
        for c in folded or ch:
            out.append(c)
            idx.append(i)
        i += 1
    return "".join(out), idx


_NORM_CACHE: dict = {}
_NORM_CACHE_MAX = 32


def _normalized_text(text: str) -> tuple:
    """Cached _normalize_for_match for source texts (the same document is
    matched thousands of times per run)."""
    key = (len(text), hash(text))
    hit = _NORM_CACHE.get(key)
    if hit is not None and (hit[0] is text or hit[0] == text):
        return hit[1], hit[2]
    norm, idx = _normalize_for_match(text)
    if len(_NORM_CACHE) >= _NORM_CACHE_MAX:
        _NORM_CACHE.pop(next(iter(_NORM_CACHE)))
    _NORM_CACHE[key] = (text, norm, idx)
    return norm, idx


def _find_in_window(text: str, needle: str, window: tuple | None) -> int:
    """text.find that prefers a hit inside the window, then anywhere."""
    if window:
        lo, hi = max(0, int(window[0])), min(len(text), int(window[1]))
        # a quote may straddle the segment edge by a little; widen the search
        # end so a match starting inside the window is still found
        i = text.find(needle, lo, min(len(text), hi + len(needle)))
        if i != -1:
            return i
    return text.find(needle)


def locate_quote(text: str, quote: str, window: tuple | None = None) -> tuple:
    """Find quote offsets in source text. In order: exact match; a match that
    folds typography, case, ligatures, soft hyphens, line-end hyphenation,
    and whitespace; then a partial head match (which may span less than the
    full quote). `window` is the segment the model was reading, searched
    first so a recurring phrase is located where it was coded. Returns
    (start, end) code-point offsets or (None, None)."""
    if not text or not quote:
        return None, None
    q = quote.strip()
    if not q:
        return None, None
    idx = _find_in_window(text, q, window)
    if idx != -1:
        return idx, idx + len(q)
    # tolerant: canonical forms on both sides, offsets mapped back
    nq, _ = _normalize_for_match(q)
    nq = nq.strip()
    if nq:
        nt, imap = _normalized_text(text)
        hit = -1
        if window:
            import bisect
            lo = max(0, int(window[0]))
            hi = min(len(text), int(window[1]))
            clo = bisect.bisect_left(imap, lo)
            chi = bisect.bisect_left(imap, hi)
            hit = nt.find(nq, clo, min(len(nt), chi + len(nq)))
        if hit == -1:
            hit = nt.find(nq)
        if hit != -1:
            return imap[hit], imap[hit + len(nq) - 1] + 1
    # last resort: locate the head of the quote (partial span — better than
    # nothing for "view in source", though shorter than the full quote)
    head = q[:80]
    idx = _find_in_window(text, head, window)
    if idx != -1:
        return idx, idx + len(head)
    nh, _ = _normalize_for_match(head)
    nh = nh.strip()
    if len(nh) >= 20:
        nt, imap = _normalized_text(text)
        hit = nt.find(nh)
        if hit != -1:
            return imap[hit], imap[hit + len(nh) - 1] + 1
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
    decisions = [d for d in resolution.get("decisions", []) if isinstance(d, dict)]
    action_of = {d.get("id"): d for d in decisions if d.get("id")}

    # Every id in a resolution must belong to THIS run: a decision that names
    # another run's code (a stale tab, a hand-built request) must not edit
    # that run. Merge targets must also be active codes of this run at the
    # stage under review, else evidence would be stranded on an inactive or
    # foreign code. Validation runs before any mutation, so a refusal reopens
    # the checkpoint cleanly.
    own = {r["id"]: dict(r) for r in conn.execute(
        "SELECT id, name, definition, stage, status FROM codes WHERE run_id=?",
        (ctx.run_id,)).fetchall()}
    stage_under_review = resolution.get("stage")
    for d in decisions:
        cid = d.get("id")
        if cid and cid not in own:
            raise ValueError(f"Decision refers to code {cid}, which is not part of this run.")
        if d.get("action") == "merge" and d.get("merge_into"):
            tgt = own.get(d["merge_into"])
            if tgt is None:
                raise ValueError(f"Merge target {d['merge_into']} is not a code of this run.")
            if tgt["status"] != "active" and d["merge_into"] not in action_of:
                raise ValueError(f"Merge target '{tgt['name']}' is no longer active; "
                                 "choose a kept code.")
            src_stage = own.get(cid, {}).get("stage")
            if src_stage and tgt["stage"] != src_stage:
                raise ValueError(f"Cannot merge '{own[cid]['name']}' ({src_stage}) into "
                                 f"'{tgt['name']}' ({tgt['stage']}): different kinds of code.")
        if stage_under_review and cid in own and own[cid]["stage"] != stage_under_review:
            raise ValueError(f"Decision on '{own[cid]['name']}' ({own[cid]['stage']}) does "
                             f"not belong to the {stage_under_review} review.")

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
        row = conn.execute("SELECT name, definition, stage FROM codes WHERE id=? AND run_id=?",
                           (cid, ctx.run_id)).fetchone()
        if not row:
            db.log_event(ctx.run_id, "info",
                         f"Skipped decision for unknown code {cid}", d)
            continue
        # a note is the researcher's reasoning; it belongs in the trail even
        # when the decision itself changes nothing (a considered "keep")
        note = d.get("notes")
        if isinstance(note, str) and note.strip():
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher note on code '{row['name']}': {note.strip()}",
                         {"id": cid, "action": action, "notes": note.strip()})
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
            meta_row = conn.execute("SELECT meta FROM codes WHERE id=? AND run_id=?",
                                    (cid, ctx.run_id)).fetchone()
            meta = json.loads(meta_row["meta"]) if meta_row and meta_row["meta"] else {}
            meta["user_edited"] = True   # later automated stages must not overwrite
            conn.execute("UPDATE codes SET name=?, definition=?, meta=? WHERE id=? AND run_id=?",
                         (new_name.strip(), new_def.strip(), json.dumps(meta), cid, ctx.run_id))
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
                conn.execute("UPDATE codes SET status='deleted' WHERE id=? AND run_id=?",
                             (cid, ctx.run_id))
                conn.execute("UPDATE codes SET parent_id=NULL WHERE parent_id=? AND run_id=?",
                             (cid, ctx.run_id))
                db.log_event(ctx.run_id, "user_decision",
                             f"Researcher merged code {cid} into a deleted code; "
                             "treated as delete", d)
                continue
            conn.execute("UPDATE excerpts SET code_id=? WHERE code_id=? AND run_id=?",
                         (target, cid, ctx.run_id))
            # grouping codes: hand children to the merge target so their
            # evidence stays in the report
            conn.execute("UPDATE codes SET parent_id=? WHERE parent_id=? AND run_id=?",
                         (target, cid, ctx.run_id))
            conn.execute("UPDATE codes SET status='merged', merged_into=? WHERE id=? AND run_id=?",
                         (target, cid, ctx.run_id))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher merged code '{row['name']}' ({cid}) into {target}", d)
        elif action == "delete":
            conn.execute("UPDATE codes SET status='deleted' WHERE id=? AND run_id=?",
                         (cid, ctx.run_id))
            # orphan children explicitly; the report sweeps them into an
            # "Uncategorized" bucket rather than losing their evidence
            conn.execute("UPDATE codes SET parent_id=NULL WHERE parent_id=? AND run_id=?",
                         (cid, ctx.run_id))
            db.log_event(ctx.run_id, "user_decision",
                         f"Researcher deleted code '{row['name']}' ({cid})", d)
    for a in resolution.get("additions", []):
        name = str(a.get("name", "")).strip()
        if not name:
            continue
        cid = ctx.add_code(name, str(a.get("definition", "")),
                           resolution.get("stage") or a.get("stage", "open_code"),
                           meta={"user_edited": True, "origin": "researcher_added"})
        note = a.get("notes")
        db.log_event(ctx.run_id, "user_decision", f"Researcher added code '{name}'"
                     + (f" — note: {note.strip()}" if isinstance(note, str) and note.strip() else ""),
                     {"id": cid, **({"notes": note.strip()} if isinstance(note, str) and note.strip() else {})})
    conn.commit()
