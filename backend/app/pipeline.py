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
    config = project["config"]
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
    conn.execute(
        "INSERT INTO runs(id,project_id,status,stage_index,state,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (run_id, project_id, "running", 0, json.dumps({"source_ids": ready_ids}),
         db.now(), db.now()))
    conn.commit()
    db.log_event(run_id, "info", f"Run started with {n_ready} sources")
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
    _launch(run_id)


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
                    conn.execute(
                        "INSERT INTO checkpoints(id,run_id,stage,title,instructions,"
                        "payload,created_at) VALUES(?,?,?,?,?,?,?)",
                        (db.new_id(), run_id, stage.name, title, instructions,
                         json.dumps(payload), db.now()))
                    conn.commit()
                _set_run(run_id, status="awaiting_review")
                db.log_event(run_id, "stage", f"Awaiting review: {stage.label}")
                return  # resolution re-launches the thread
            db.log_event(run_id, "stage", f"Stage started: {stage.label}")
            stage.run(ctx)
            _save_state(ctx)
            _set_run(run_id, stage_index=idx + 1)
            db.log_event(run_id, "stage", f"Stage finished: {stage.label}")
    except Cancelled:
        db.log_event(run_id, "info", "Stage stopped mid-flight after cancellation")
        # status is already 'cancelled'; partial work stays recorded
    except Exception as e:  # noqa: BLE001 — a run must never die silently
        err = f"{type(e).__name__}: {e}"
        _set_run(run_id, status="failed", error=err)
        db.log_event(run_id, "error", err, {"traceback": traceback.format_exc()[-2000:]})
