# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Run manager: executes a method's stages in a background thread, pauses at
checkpoints, resumes on resolution, and survives failures resumably. Long
stages record each completed unit (source segment, matrix row) in run state,
so resuming a failed run skips work already done rather than re-billing it;
single-call grouping stages reset their own output and rebuild cleanly."""

import json
import threading
import traceback

from . import db, llm
from .methods import METHODS
from .methods.base import Cancelled, RunContext

_threads: dict = {}
_lock = threading.Lock()


def reconcile_on_startup() -> None:
    """The process just started, so no background thread can exist. Any run
    still marked 'running' was interrupted (crash, restart, machine sleep);
    mark it failed so the UI offers Resume instead of spinning forever.
    Sources stuck 'transcribing' likewise get an error with a Retry path."""
    conn = db.get_conn()
    for r in conn.execute("SELECT id FROM runs WHERE status='running'").fetchall():
        conn.execute("UPDATE runs SET status='failed', error=?, updated_at=? WHERE id=?",
                     ("Interrupted by an app restart. Click Resume — completed work "
                      "is preserved and will not be re-billed.", db.now(), r["id"]))
        db.log_event(r["id"], "info", "Run marked interrupted at app startup")
    # repair the (rare) crash window between a checkpoint being claimed and
    # the run advancing: an awaiting_review run with no pending checkpoint has
    # nothing to review — mark it failed so Resume rebuilds the checkpoint
    for r in conn.execute("SELECT id FROM runs WHERE status='awaiting_review'").fetchall():
        pending = conn.execute(
            "SELECT 1 FROM checkpoints WHERE run_id=? AND status='pending'",
            (r["id"],)).fetchone()
        if not pending:
            conn.execute("UPDATE runs SET status='failed', error=?, updated_at=? WHERE id=?",
                         ("Interrupted while resolving a review. Click Resume — the "
                          "review will be rebuilt.", db.now(), r["id"]))
            db.log_event(r["id"], "info",
                         "Run marked interrupted at startup (orphaned review state)")
    for s in conn.execute("SELECT id, meta FROM sources WHERE status='transcribing'").fetchall():
        meta = json.loads(s["meta"] or "{}")
        meta["error"] = "Transcription was interrupted by an app restart. Retry it."
        conn.execute("UPDATE sources SET status='error', meta=? WHERE id=?",
                     (json.dumps(meta), s["id"]))
    conn.commit()


def _load_ctx(run_id: str) -> RunContext:
    conn = db.get_conn()
    run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not run:
        raise ValueError(f"Run {run_id} not found")
    project = db.row_to_dict(
        conn.execute("SELECT * FROM projects WHERE id=?", (run["project_id"],)).fetchone(),
        ("config",))
    sources = [db.row_to_dict(r, ("meta",)) for r in conn.execute(
        "SELECT * FROM sources WHERE project_id=? AND status='ready' ORDER BY filename",
        (run["project_id"],)).fetchall()]
    state = json.loads(run["state"] or "{}")
    # runs since the corpus freeze carry the participating source ids; a run
    # from an older database has no snapshot and keeps the old behavior
    frozen = state.get("source_ids")
    if isinstance(frozen, list) and frozen:
        keep = set(frozen)
        sources = [s for s in sources if s["id"] in keep]
    # runs since the config freeze carry their own copy of the setup answers,
    # provider, and model: a project edited after the run started (or after
    # it failed) must not change what a resumed or branched run does, and the
    # report must name the model that actually ran. Older runs fall back to
    # the project row, as before.
    snap = state.get("config")
    config = dict(snap) if isinstance(snap, dict) and snap else project["config"]
    provider = config.get("provider", "anthropic")
    model = (config.get("model") or "").strip() or llm.catalog()[provider]["default_model"]
    api_key = db.get_setting(f"api_key_{provider}", "")
    ctx = RunContext(run_id, project, sources, config, provider, model, api_key)
    ctx.state = state
    return ctx


def _save_state(ctx: RunContext) -> None:
    conn = db.get_conn()
    conn.execute("UPDATE runs SET state=?, updated_at=? WHERE id=?",
                 (json.dumps(ctx.state), db.now(), ctx.run_id))
    conn.commit()


def _set_run(run_id: str, **fields) -> None:
    conn = db.get_conn()
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE runs SET {sets}, updated_at=? WHERE id=?",
                 (*fields.values(), db.now(), run_id))
    conn.commit()


def start_run(project_id: str) -> str:
    """Create a run for the project and launch it."""
    conn = db.get_conn()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        raise ValueError("Project not found")
    if project["method"] not in METHODS:
        raise ValueError(f"Unknown method {project['method']}")
    n_ready = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE project_id=? AND status='ready'",
        (project_id,)).fetchone()["c"]
    if n_ready == 0:
        raise ValueError("No ready sources — upload data (and wait for transcription) first.")
    n_pending = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE project_id=? AND status='transcribing'",
        (project_id,)).fetchone()["c"]
    if n_pending:
        raise ValueError(
            f"{n_pending} source(s) are still transcribing. Wait for them to finish "
            "(or remove them) — starting now would silently exclude them from the analysis.")
    run_id = db.new_id()
    # freeze the participating corpus: a source added later (e.g. while this
    # run waits at a checkpoint, or before a resume) must not slip into the
    # analysis without passing through the stages that already ran
    ready_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM sources WHERE project_id=? AND status='ready' ORDER BY filename",
        (project_id,)).fetchall()]
    # freeze the configuration the same way (see _load_ctx)
    config = json.loads(project["config"] or "{}")
    provider = config.get("provider", "anthropic")
    config["model"] = ((config.get("model") or "").strip()
                       or llm.catalog().get(provider, {}).get("default_model", ""))
    conn.execute(
        "INSERT INTO runs(id,project_id,status,stage_index,state,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (run_id, project_id, "running", 0,
         json.dumps({"source_ids": ready_ids, "config": config}),
         db.now(), db.now()))
    conn.commit()
    db.log_event(run_id, "info", f"Run started with {n_ready} sources",
                 {"provider": provider, "model": config["model"],
                  "config": {k: v for k, v in config.items() if k != "model"}})
    _launch(run_id)
    return run_id


def resume_run(run_id: str) -> None:
    """Re-launch a failed or interrupted run at its current stage."""
    conn = db.get_conn()
    run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not run:
        raise ValueError("Run not found")
    if run["status"] not in ("failed", "running"):
        raise ValueError(f"Run is {run['status']}; only failed/interrupted runs resume.")
    with _lock:
        t = _threads.get(run_id)
        if t and t.is_alive():
            raise ValueError("Run is already executing.")
    _set_run(run_id, status="running", error=None)
    db.log_event(run_id, "info", "Run resumed")
    _launch(run_id)


def resolve_checkpoint(run_id: str, checkpoint_id: str, resolution: dict) -> None:
    conn = db.get_conn()
    cp = conn.execute("SELECT * FROM checkpoints WHERE id=? AND run_id=?",
                      (checkpoint_id, run_id)).fetchone()
    if not cp:
        raise ValueError("Checkpoint not found")
    run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if run["status"] != "awaiting_review":
        raise ValueError(f"Run is {run['status']}; nothing awaits review.")
    project = conn.execute("SELECT method FROM projects WHERE id=?",
                           (run["project_id"],)).fetchone()
    method = METHODS[project["method"]]
    stage = method.stages[run["stage_index"]]
    if stage.kind != "checkpoint" or stage.name != cp["stage"]:
        raise ValueError("Run is not waiting at this checkpoint")

    # Atomic claim: only one caller may resolve this checkpoint. A concurrent
    # double-submit (double-click, two tabs) fails here instead of applying
    # the decisions twice and launching two executor threads.
    cur = conn.execute(
        "UPDATE checkpoints SET status='resolved', resolution=?, resolved_at=? "
        "WHERE id=? AND status='pending'",
        (json.dumps(resolution), db.now(), checkpoint_id))
    conn.commit()
    if cur.rowcount == 0:
        raise ValueError("Checkpoint already resolved")

    try:
        ctx = _load_ctx(run_id)
        resolution.setdefault("stage", json.loads(cp["payload"]).get("stage"))
        stage.apply_resolution(ctx, resolution)
    except Exception:
        # a failure after the claim must not wedge the run: reopen the
        # checkpoint so the researcher can resubmit (already-applied
        # sub-decisions re-apply as no-ops)
        conn.execute("UPDATE checkpoints SET status='pending', resolution=NULL, "
                     "resolved_at=NULL WHERE id=?", (checkpoint_id,))
        conn.commit()
        db.log_event(run_id, "error",
                     f"Applying checkpoint '{cp['title']}' failed; checkpoint reopened")
        raise
    db.log_event(run_id, "user_decision", f"Checkpoint '{cp['title']}' resolved")
    _set_run(run_id, status="running", stage_index=run["stage_index"] + 1)
    db.checkpoint_wal("PASSIVE")   # the researcher's decisions reach the main file now
    _launch(run_id)


def _remap_ids(obj, id_map: dict):
    """Deep-copy obj with every string VALUE that is a copied code's id
    replaced by its branch id. Meta blobs may carry code ids anywhere (the
    GT core's relationships, is_existing_category_id); keys are never code
    ids today, so only values are rewritten."""
    if isinstance(obj, str):
        return id_map.get(obj, obj)
    if isinstance(obj, list):
        return [_remap_ids(x, id_map) for x in obj]
    if isinstance(obj, dict):
        return {k: _remap_ids(v, id_map) for k, v in obj.items()}
    return obj


def branch_run(source_run_id: str, stage_name: str) -> str:
    """Create a NEW run that carries everything the source run had produced
    up to the named checkpoint — codes, evidence, state, and the earlier
    resolved reviews — and reopens that checkpoint for different decisions.
    The source run and its report are untouched; stages after the review run
    again on the branch (and bill again), while the spend already made stays
    recorded on the source run."""
    conn = db.get_conn()
    run = conn.execute("SELECT * FROM runs WHERE id=?", (source_run_id,)).fetchone()
    if not run:
        raise ValueError("Run not found")
    if run["status"] == "running":
        raise ValueError("The run is still executing — wait for it or cancel it "
                         "before revisiting a review.")
    project = conn.execute("SELECT method FROM projects WHERE id=?",
                           (run["project_id"],)).fetchone()
    method = METHODS[project["method"]]
    idx = next((i for i, s in enumerate(method.stages) if s.name == stage_name), None)
    if idx is None:
        raise ValueError(f"Unknown stage '{stage_name}'")
    stage = method.stages[idx]
    if stage.kind != "checkpoint":
        raise ValueError("Only review checkpoints can be revisited.")
    if run["stage_index"] < idx:
        raise ValueError("The run never reached this review.")
    if run["stage_index"] == idx and run["status"] == "awaiting_review":
        raise ValueError("The run is waiting at this review right now — open it "
                         "instead of branching.")

    new_id = db.new_id()
    code_rows = conn.execute("SELECT * FROM codes WHERE run_id=? ORDER BY created_at",
                             (source_run_id,)).fetchall()
    # codes get fresh ids (they are global primary keys); links are remapped
    id_map = {r["id"]: db.new_id() for r in code_rows}
    stage_of = {r["id"]: r["stage"] for r in code_rows}

    # everything OWNED by stages after the branch point is left behind, so
    # those stages run again on the branch instead of skipping on stale
    # artifacts: their state keys, their unit markers, and the excerpts they
    # wrote (e.g. a branch back to the codebook review must re-code — the
    # copied coding would belong to the OLD codebook)
    drop_state, drop_units, drop_excerpt_stages = set(), set(), set()
    for later in method.stages[idx + 1:]:
        drop_state.update(later.resets)
        drop_units.update(later.reset_units)
        drop_excerpt_stages.update(later.reset_excerpt_stages)

    excerpt_rows = conn.execute(
        "SELECT * FROM excerpts WHERE run_id=? ORDER BY created_at",
        (source_run_id,)).fetchall()

    state = json.loads(run["state"] or "{}")
    if state.get("core_id") in id_map:       # grounded theory carries a code id
        state["core_id"] = id_map[state["core_id"]]
    for key in drop_state:
        state.pop(key, None)
    if drop_units:
        state["done_units"] = [
            u for u in state.get("done_units", [])
            if not any(u.startswith(p + ":") for p in drop_units)]
    # a source run from before the corpus freeze carries no snapshot; the
    # branch must not inherit that openness — reconstruct its corpus from
    # what the copied artifacts reference, else from what is ready now
    if not (isinstance(state.get("source_ids"), list) and state["source_ids"]):
        refs = {e["source_id"] for e in excerpt_rows}
        refs |= set(state.get("summaries") or {})
        refs |= set(state.get("extractions") or {})
        state["source_ids"] = sorted(refs) if refs else [
            r["id"] for r in conn.execute(
                "SELECT id FROM sources WHERE project_id=? AND status='ready' "
                "ORDER BY filename", (run["project_id"],)).fetchall()]
    # a source run from before the config freeze has no snapshot either;
    # freeze the project's configuration as it stands for the branch
    if not (isinstance(state.get("config"), dict) and state["config"]):
        prow = conn.execute("SELECT config FROM projects WHERE id=?",
                            (run["project_id"],)).fetchone()
        cfg = json.loads(prow["config"] or "{}") if prow else {}
        prov = cfg.get("provider", "anthropic")
        cfg["model"] = ((cfg.get("model") or "").strip()
                        or llm.catalog().get(prov, {}).get("default_model", ""))
        state["config"] = cfg
    # the reopened review's panel says plainly that its earlier decisions
    # are already applied (see _execute)
    state["branched_from"] = source_run_id
    state["branched_at"] = stage_name

    try:
        # the run row first — codes/excerpts/checkpoints reference it
        conn.execute(
            "INSERT INTO runs(id,project_id,status,stage_index,state,created_at,"
            "updated_at) VALUES(?,?,?,?,?,?,?)",
            (new_id, run["project_id"], "running", idx, json.dumps(state),
             db.now(), db.now()))
        for r in code_rows:
            # meta may embed code ids (the GT core's relationships and
            # is_existing_category_id) — remap them like the columns, or the
            # branch's figure would silently match nothing
            meta = r["meta"]
            try:
                meta = json.dumps(_remap_ids(json.loads(meta or "{}"), id_map))
            except (ValueError, TypeError):
                pass                       # unreadable meta is copied verbatim
            conn.execute(
                "INSERT INTO codes(id,run_id,name,definition,stage,parent_id,status,"
                "merged_into,meta,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (id_map[r["id"]], new_id, r["name"], r["definition"], r["stage"],
                 id_map.get(r["parent_id"]), r["status"], id_map.get(r["merged_into"]),
                 meta, r["created_at"]))
        for e in excerpt_rows:
            if e["code_id"] not in id_map:
                continue
            if stage_of.get(e["code_id"]) in drop_excerpt_stages:
                continue
            conn.execute(
                "INSERT INTO excerpts(id,run_id,code_id,source_id,quote,start_char,"
                "end_char,memo,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (db.new_id(), new_id, id_map[e["code_id"]], e["source_id"],
                 e["quote"], e["start_char"], e["end_char"], e["memo"],
                 e["confidence"], e["created_at"]))
        # reviews resolved BEFORE the branch point stay in the audit record
        for cp in conn.execute(
                "SELECT * FROM checkpoints WHERE run_id=? AND status='resolved'",
                (source_run_id,)).fetchall():
            cp_idx = next((i for i, s in enumerate(method.stages)
                           if s.name == cp["stage"]), None)
            if cp_idx is not None and cp_idx < idx:
                conn.execute(
                    "INSERT INTO checkpoints(id,run_id,stage,title,instructions,"
                    "payload,status,resolution,created_at,resolved_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (db.new_id(), new_id, cp["stage"], cp["title"],
                     cp["instructions"], cp["payload"], cp["status"],
                     cp["resolution"], cp["created_at"], cp["resolved_at"]))
        conn.commit()
    except Exception:
        # never leave a half-copied run or an open write transaction behind
        conn.rollback()
        raise
    db.log_event(new_id, "info",
                 f"Branched from run {source_run_id} at '{stage.label}' — the "
                 "analysis up to this review was carried over; its cost remains "
                 "recorded on the source run")
    db.log_event(source_run_id, "info",
                 f"Run {new_id} branched from this run to revisit '{stage.label}'")
    _launch(new_id)
    return new_id


def cancel_run(run_id: str) -> None:
    conn = db.get_conn()
    run = conn.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
    if not run:
        raise ValueError("Run not found")
    if run["status"] not in ("running", "awaiting_review", "failed"):
        raise ValueError(f"Run is already {run['status']}.")
    _set_run(run_id, status="cancelled")
    db.log_event(run_id, "info", "Run cancelled by user")


def _launch(run_id: str) -> None:
    with _lock:
        t = _threads.get(run_id)
        if t and t.is_alive():
            return  # an executor for this run is already working
        # shed finished executors so the registry does not grow for the life
        # of the process
        for rid in [rid for rid, th in _threads.items() if not th.is_alive()]:
            del _threads[rid]
        t = threading.Thread(target=_execute, args=(run_id,), daemon=True)
        _threads[run_id] = t
        # start INSIDE the lock: a not-yet-started thread reports is_alive()
        # False, so starting outside would let a concurrent caller race past
        # the guard and spawn a second executor
        t.start()


def _execute(run_id: str) -> None:
    try:
        ctx = _load_ctx(run_id)
        method = METHODS[ctx.project["method"]]
        conn = db.get_conn()
        while True:
            run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if run["status"] == "cancelled":
                return
            idx = run["stage_index"]
            if idx >= len(method.stages):
                _set_run(run_id, status="completed", stage_name=None)
                db.log_event(run_id, "info", "Run completed")
                db.checkpoint_wal("PASSIVE")
                return
            stage = method.stages[idx]
            _set_run(run_id, stage_name=stage.name)
            if stage.kind == "checkpoint":
                # if a pending checkpoint already exists for this stage, keep waiting
                existing = conn.execute(
                    "SELECT id FROM checkpoints WHERE run_id=? AND stage=? AND status='pending'",
                    (run_id, stage.name)).fetchone()
                if not existing:
                    title, instructions, payload = stage.build_payload(ctx)
                    if ctx.state.get("branched_at") == stage.name:
                        instructions += (
                            " This review was reopened from an earlier run: the "
                            "decisions you made there are already applied, and "
                            "further decisions build on them — codes merged or "
                            "deleted there do not reappear.")
                    conn.execute(
                        "INSERT INTO checkpoints(id,run_id,stage,title,instructions,"
                        "payload,created_at) VALUES(?,?,?,?,?,?,?)",
                        (db.new_id(), run_id, stage.name, title, instructions,
                         json.dumps(payload), db.now()))
                    conn.commit()
                _set_run(run_id, status="awaiting_review")
                db.log_event(run_id, "stage", f"Awaiting review: {stage.label}")
                db.checkpoint_wal("PASSIVE")   # a run may wait here for days
                return  # resolution re-launches the thread
            db.log_event(run_id, "stage", f"Stage started: {stage.label}")
            stage.run(ctx)
            _save_state(ctx)
            _set_run(run_id, stage_index=idx + 1)
            db.log_event(run_id, "stage", f"Stage finished: {stage.label}")
            db.checkpoint_wal("PASSIVE")
    except Cancelled:
        db.log_event(run_id, "info", "Stage stopped mid-flight after cancellation")
        # status is already 'cancelled'; partial work stays recorded
    except Exception as e:  # noqa: BLE001 — a run must never die silently
        err = f"{type(e).__name__}: {e}"
        _set_run(run_id, status="failed", error=err)
        db.log_event(run_id, "error", err, {"traceback": traceback.format_exc()[-2000:]})
