# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""QualiLens — local web app for LLM-assisted qualitative analysis.

FastAPI backend: serves the JSON API and, in production, the built frontend.
Everything runs on the researcher's machine; API keys live in the local
SQLite database and calls go straight to the chosen provider.
"""

import json
import re
import threading
from dataclasses import asdict
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import db, ingestion, llm, pipeline, report_docx, transcription, update
from .methods import METHODS

app = FastAPI(title="QualiLens")
db.init_db()
pipeline.reconcile_on_startup()


def _err(status: int, msg: str):
    raise HTTPException(status_code=status, detail=msg)


# ---------------- meta ----------------

@app.get("/api/meta")
def get_meta():
    return {
        "methods": [
            {"id": m.id, "label": m.label, "description": m.description,
             "questions": [asdict(q) for q in m.questions],
             "stages": m.stage_names()}
            for m in METHODS.values()
        ],
        # read fresh so a models.json edit is live on the next page load
        "providers": [
            {"id": pid, **info, "has_key": bool(db.get_setting(f"api_key_{pid}"))}
            for pid, info in llm.catalog().items()
        ],
        "ffmpeg": transcription.ffmpeg_available(),
        "version": update._current_version(),
    }


# ---------------- settings ----------------

@app.get("/api/settings")
def get_settings():
    out = {}
    for pid in llm.PROVIDERS:
        key = db.get_setting(f"api_key_{pid}")
        out[pid] = {"has_key": bool(key),
                    "key_hint": (key[:6] + "…" + key[-4:]) if len(key) > 12 else ""}
    return out


@app.put("/api/settings/keys")
def put_keys(body: dict):
    for pid, key in body.items():
        if pid not in llm.PROVIDERS:
            continue
        if key == "__clear__":
            db.set_setting(f"api_key_{pid}", "")
        elif key:
            db.set_setting(f"api_key_{pid}", key.strip())
    return get_settings()


@app.post("/api/settings/test_key")
def test_key(body: dict):
    pid = body.get("provider")
    if pid not in llm.PROVIDERS:
        _err(400, "Unknown provider")
    # an explicitly supplied key is tested WITHOUT being saved, so trying a
    # new key never clobbers a saved working one
    key = (body.get("key") or "").strip() or db.get_setting(f"api_key_{pid}")
    if not key:
        _err(400, "No key saved for this provider")
    model = body.get("model") or llm.PROVIDERS[pid]["default_model"]
    try:
        text, usage = llm.chat(pid, model, key, "Reply with the single word: ok",
                               "Say ok.", max_tokens=1000, temperature=0.0, retries=1)
        return {"ok": True, "reply": text.strip()[:40], "usage": usage}
    except llm.LLMError as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/settings/check_models")
def check_models(body: dict):
    """Compare this app's model catalog with each provider's LIVE model list
    (their free list-models endpoint, called with the user's own key). This is
    how a maintainer learns a catalog entry has been retired — no telemetry,
    no token spend."""
    only = body.get("provider")
    if only and only not in llm.PROVIDERS:
        _err(400, f"Unknown provider '{only}'")
    out = {}
    for pid, info in llm.catalog().items():
        if only and pid != only:
            continue
        key = db.get_setting(f"api_key_{pid}")
        if not key:
            out[pid] = {"ok": False, "error": "No API key saved."}
            continue
        try:
            live = [m for m in llm.list_models(pid, key) if m]
        except Exception as e:  # noqa: BLE001 — report, never 500
            out[pid] = {"ok": False, "error": str(e)[:300]}
            continue
        live_set = set(live)
        out[pid] = {
            "ok": True,
            "catalog": [{"id": m, "available": m in live_set}
                        for m in info["models"]],
            "missing": [m for m in info["models"] if m not in live_set],
            "live_count": len(live),
            "live": live[:200],
        }
    return out


def _finish_update(result: dict) -> dict:
    """After a successful update: stop the server (outside tests) so ./run.sh
    relaunches the new version. Shared by the zip and release paths."""
    import os
    import signal
    if not os.environ.get("QUALILENS_TEST"):
        def _stop():
            import time as _t
            _t.sleep(1.2)   # let the response reach the browser first
            db.checkpoint_wal()
            os.kill(os.getpid(), signal.SIGTERM)
        threading.Thread(target=_stop, daemon=True).start()
        result["restart_required"] = True
    return result


@app.post("/api/settings/update")
async def apply_app_update(file: UploadFile = File(...)):
    """Update the application in place from a downloaded QualiLens bundle.
    Projects, keys, and uploads are untouchable by design (allowlist). On
    success the server stops itself so ./run.sh relaunches the new version."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        result = update.apply_update(tmp_path)
    except update.UpdateError as e:
        _err(400, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)
    return _finish_update(result)


@app.post("/api/settings/check_updates")
def check_updates():
    """PULL-ONLY and user-initiated: one GET to GitHub's releases endpoint,
    made when the researcher presses the button — never in the background,
    and nothing is sent beyond the request itself."""
    try:
        return update.check_for_update()
    except update.UpdateError as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/settings/install_update")
def install_update():
    """Download the latest published release and apply it through the same
    validated updater as the zip path. The release is resolved server-side —
    no URL is accepted from the client — and user data is untouchable by the
    updater's allowlist, as ever."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        try:
            bundle = update.download_latest_bundle(Path(td))
            result = update.apply_update(bundle)
        except update.UpdateError as e:
            _err(400, str(e))
    return _finish_update(result)


# ---------------- projects ----------------

@app.get("/api/projects")
def list_projects():
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        p = db.row_to_dict(r, ("config",))
        p["n_sources"] = conn.execute(
            "SELECT COUNT(*) c FROM sources WHERE project_id=?", (r["id"],)).fetchone()["c"]
        latest = conn.execute(
            "SELECT id,status,stage_name FROM runs WHERE project_id=? "
            "ORDER BY created_at DESC LIMIT 1", (r["id"],)).fetchone()
        p["latest_run"] = dict(latest) if latest else None
        out.append(p)
    return out


@app.post("/api/projects")
def create_project(body: dict):
    name = (body.get("name") or "").strip()
    method = body.get("method")
    if not name:
        _err(400, "Project name is required")
    if method not in METHODS:
        _err(400, f"Unknown method '{method}'")
    config = body.get("config") or {}
    # validate required method questions
    for q in METHODS[method].questions:
        if q.required and not str(config.get(q.key, "")).strip():
            _err(400, f"Missing required setting: {q.label}")
    if config.get("provider") not in llm.PROVIDERS:
        _err(400, "Choose an analysis provider")
    if isinstance(config.get("model"), str):
        config["model"] = config["model"].strip()
    pid = db.new_id()
    conn = db.get_conn()
    conn.execute("INSERT INTO projects(id,name,method,config,created_at) VALUES(?,?,?,?,?)",
                 (pid, name, method, json.dumps(config), db.now()))
    conn.commit()
    return get_project(pid)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        _err(404, "Project not found")
    p = db.row_to_dict(row, ("config",))
    p["sources"] = [
        {k: v for k, v in db.row_to_dict(r, ("meta",)).items() if k != "text"}
        | {"chars": len(r["text"] or "")}
        for r in conn.execute(
            "SELECT * FROM sources WHERE project_id=? ORDER BY filename",
            (project_id,)).fetchall()
    ]
    p["runs"] = [db.row_to_dict(r, ("progress", "usage")) for r in conn.execute(
        "SELECT id,status,stage_index,stage_name,progress,usage,error,created_at,updated_at "
        "FROM runs WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()]
    p["stages"] = METHODS[p["method"]].stage_names()
    return p


def _remove_upload_file(source_id: str) -> None:
    """Deleting a source must also delete the researcher's uploaded file —
    'deleted' interview data must not quietly persist on disk."""
    for f in db.UPLOADS_DIR.glob(f"{source_id}_*"):
        try:
            f.unlink()
        except OSError:
            pass


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, body: dict):
    """The wizard may revise name/method/config after the project exists
    (Back-navigation); the run must use what the researcher last saw."""
    conn = db.get_conn()
    existing = conn.execute("SELECT method FROM projects WHERE id=?", (project_id,)).fetchone()
    if not existing:
        _err(404, "Project not found")
    name = (body.get("name") or "").strip()
    method = body.get("method")
    config = body.get("config") or {}
    has_runs = conn.execute("SELECT 1 FROM runs WHERE project_id=? LIMIT 1",
                            (project_id,)).fetchone()
    if has_runs and method != existing["method"]:
        _err(409, "Method cannot be changed once runs exist — create a new project.")
    active = conn.execute("SELECT 1 FROM runs WHERE project_id=? AND status IN "
                          "('running','awaiting_review') LIMIT 1", (project_id,)).fetchone()
    if active:
        _err(409, "A run is in progress — wait for it or cancel it before editing "
                  "the project configuration.")
    if not name:
        _err(400, "Project name is required")
    if method not in METHODS:
        _err(400, f"Unknown method '{method}'")
    for q in METHODS[method].questions:
        if q.required and not str(config.get(q.key, "")).strip():
            _err(400, f"Missing required setting: {q.label}")
    if config.get("provider") not in llm.PROVIDERS:
        _err(400, "Choose an analysis provider")
    if isinstance(config.get("model"), str):
        config["model"] = config["model"].strip()
    conn.execute("UPDATE projects SET name=?, method=?, config=? WHERE id=?",
                 (name, method, json.dumps(config), project_id))
    conn.commit()
    return get_project(project_id)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    conn = db.get_conn()
    run_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM runs WHERE project_id=?", (project_id,)).fetchall()]
    for rid in run_ids:
        for table in ("excerpts", "codes", "checkpoints", "events", "reports"):
            conn.execute(f"DELETE FROM {table} WHERE run_id=?", (rid,))
    source_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM sources WHERE project_id=?", (project_id,)).fetchall()]
    conn.execute("DELETE FROM runs WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM sources WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    for sid in source_ids:
        _remove_upload_file(sid)
    return {"ok": True}


# ---------------- sources ----------------

@app.post("/api/projects/{project_id}/sources")
async def upload_source(project_id: str, file: UploadFile = File(...),
                        grp: str = Form("")):
    conn = db.get_conn()
    if not conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
        _err(404, "Project not found")
    busy = conn.execute(
        "SELECT 1 FROM runs WHERE project_id=? AND status IN ('running','awaiting_review') "
        "LIMIT 1", (project_id,)).fetchone()
    if busy:
        # a source added mid-run would join the analysis without passing
        # through the stages and checkpoints that already ran
        _err(409, "A run is in progress for this project — wait for it or cancel "
                  "it before adding sources.")
    try:
        kind = ingestion.classify(file.filename)
    except ValueError as e:
        _err(400, str(e))
    sid = db.new_id()
    dest = db.UPLOADS_DIR / f"{sid}_{Path(file.filename).name}"
    content = await file.read()
    dest.write_bytes(content)

    if kind == "text":
        try:
            text, pages = ingestion.extract_text_with_pages(dest)
        except Exception as e:  # noqa: BLE001
            dest.unlink(missing_ok=True)
            _err(400, f"Could not extract text from {file.filename}: {e}")
        if not text.strip():
            dest.unlink(missing_ok=True)
            _err(400, f"{file.filename} contains no extractable text.")
        meta = {"bytes": len(content)}
        if pages:
            meta["pages"] = pages   # PDF page map: char offsets -> page numbers
        conn.execute(
            "INSERT INTO sources(id,project_id,filename,kind,status,grp,text,meta,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (sid, project_id, file.filename, kind, "ready", grp or None, text,
             json.dumps(meta), db.now()))
        conn.commit()
    else:
        conn.execute(
            "INSERT INTO sources(id,project_id,filename,kind,status,grp,meta,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (sid, project_id, file.filename, kind, "transcribing", grp or None,
             json.dumps({"bytes": len(content), "path": str(dest)}), db.now()))
        conn.commit()
        threading.Thread(target=_transcribe_source, args=(sid, dest, kind),
                         daemon=True).start()
    row = conn.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
    d = db.row_to_dict(row, ("meta",))
    d["chars"] = len(d.pop("text", None) or "")
    return d


def _transcribe_source(sid: str, path: Path, kind: str) -> None:
    conn = db.get_conn()

    def progress(done: int, total: int) -> None:
        row = conn.execute("SELECT meta FROM sources WHERE id=?", (sid,)).fetchone()
        meta = json.loads(row["meta"]) if row else {}
        meta["transcribe_progress"] = {"done": done, "total": total}
        conn.execute("UPDATE sources SET meta=? WHERE id=?", (json.dumps(meta), sid))
        conn.commit()

    try:
        key = db.get_setting("api_key_openai")
        text = transcription.transcribe(path, kind, key, progress_cb=progress)
        if not text.strip():
            raise transcription.TranscriptionError("Transcription returned no text.")
        conn.execute("UPDATE sources SET status='ready', text=? WHERE id=?", (text, sid))
    except Exception as e:  # noqa: BLE001
        meta_row = conn.execute("SELECT meta FROM sources WHERE id=?", (sid,)).fetchone()
        meta = json.loads(meta_row["meta"]) if meta_row else {}
        meta["error"] = str(e)
        conn.execute("UPDATE sources SET status='error', meta=? WHERE id=?",
                     (json.dumps(meta), sid))
    conn.commit()


@app.get("/api/sources/{source_id}/text")
def source_text(source_id: str):
    row = db.get_conn().execute("SELECT filename,text FROM sources WHERE id=?",
                                (source_id,)).fetchone()
    if not row:
        _err(404, "Source not found")
    return {"filename": row["filename"], "text": row["text"] or ""}


@app.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT project_id FROM sources WHERE id=?", (source_id,)).fetchone()
    if not row:
        _remove_upload_file(source_id)   # purge any stale file even without a row
        return {"ok": True}
    busy = conn.execute(
        "SELECT 1 FROM runs WHERE project_id=? AND status IN ('running','awaiting_review') "
        "LIMIT 1", (row["project_id"],)).fetchone()
    if busy:
        _err(409, "A run is in progress for this project — cancel it or wait "
                  "before deleting sources.")
    # excerpts reference sources (FK RESTRICT): remove the evidence rows first
    # or the delete 500s once any run has coded this source
    conn.execute("DELETE FROM excerpts WHERE source_id=?", (source_id,))
    conn.execute("DELETE FROM sources WHERE id=?", (source_id,))
    conn.commit()
    _remove_upload_file(source_id)
    return {"ok": True}


@app.post("/api/sources/{source_id}/retry")
def retry_source(source_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
    if not row:
        _err(404, "Source not found")
    if row["status"] == "transcribing":
        _err(400, "Transcription is already in progress for this source.")
    meta = json.loads(row["meta"])
    path = Path(meta.get("path", ""))
    if row["kind"] not in ("audio", "video") or not path.exists():
        _err(400, "Only failed audio/video transcriptions can be retried.")
    conn.execute("UPDATE sources SET status='transcribing' WHERE id=?", (source_id,))
    conn.commit()
    threading.Thread(target=_transcribe_source, args=(source_id, path, row["kind"]),
                     daemon=True).start()
    return {"ok": True}


# ---------------- estimate & runs ----------------

@app.get("/api/projects/{project_id}/estimate")
def estimate(project_id: str):
    conn = db.get_conn()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        _err(404, "Project not found")
    config = json.loads(project["config"])
    provider = config.get("provider", "anthropic")
    sources = conn.execute(
        "SELECT text FROM sources WHERE project_id=? AND status='ready'",
        (project_id,)).fetchall()
    total_chars = sum(len(r["text"] or "") for r in sources)
    data_tokens = llm.estimate_tokens_from_chars(total_chars) if total_chars else 0
    # heuristic: data passes through coding once (input), plus familiarization,
    # plus grouping/report overhead; output roughly 15% of input
    method = project["method"]
    passes = {"grounded_theory": 2.4, "thematic": 2.4,
              "content_analysis": 1.6, "framework": 1.9,
              "literature_synthesis": 1.7}.get(method, 2.0)
    est_in = int(data_tokens * passes) + 20000
    est_out = int(est_in * 0.15)
    p_in, p_out = llm.catalog().get(provider, {}).get("pricing", (3.0, 15.0))
    cost = est_in / 1e6 * p_in + est_out / 1e6 * p_out
    return {"n_sources": len(sources), "total_chars": total_chars,
            "est_input_tokens": est_in, "est_output_tokens": est_out,
            "est_cost_usd": round(cost, 2),
            "note": "Rough estimate from data volume and default prices; actual cost "
                    "depends on provider pricing and model verbosity."}


@app.post("/api/projects/{project_id}/runs")
def create_run(project_id: str):
    try:
        run_id = pipeline.start_run(project_id)
    except ValueError as e:
        _err(400, str(e))
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        _err(404, "Run not found")
    run = db.row_to_dict(row, ("progress", "usage"))
    run.pop("state", None)
    project = conn.execute("SELECT method,name FROM projects WHERE id=?",
                           (row["project_id"],)).fetchone()
    run["project_name"] = project["name"]
    run["stages"] = METHODS[project["method"]].stage_names()
    cp = conn.execute(
        "SELECT * FROM checkpoints WHERE run_id=? AND status='pending' "
        "ORDER BY created_at DESC LIMIT 1", (run_id,)).fetchone()
    run["pending_checkpoint"] = db.row_to_dict(cp, ("payload",)) if cp else None
    run["has_report"] = bool(conn.execute(
        "SELECT run_id FROM reports WHERE run_id=?", (run_id,)).fetchone())
    return run


@app.get("/api/runs/{run_id}/events")
def run_events(run_id: str, after: float = 0):
    rows = db.get_conn().execute(
        "SELECT ts,kind,message FROM events WHERE run_id=? AND ts>? ORDER BY ts LIMIT 200",
        (run_id, after)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/runs/{run_id}/checkpoints/{checkpoint_id}/resolve")
def resolve_cp(run_id: str, checkpoint_id: str, body: dict):
    try:
        pipeline.resolve_checkpoint(run_id, checkpoint_id, body or {})
    except ValueError as e:
        _err(400, str(e))
    return {"ok": True}


@app.post("/api/runs/{run_id}/resume")
def resume(run_id: str):
    try:
        pipeline.resume_run(run_id)
    except ValueError as e:
        _err(400, str(e))
    return {"ok": True}


@app.post("/api/runs/{run_id}/cancel")
def cancel(run_id: str):
    pipeline.cancel_run(run_id)
    return {"ok": True}


# ---------------- evidence exploration ----------------

@app.get("/api/runs/{run_id}/codes/{code_id}/excerpts")
def code_excerpts(run_id: str, code_id: str):
    """Every excerpt of one code, with source names — the checkpoint review
    side panel's full-evidence view. Grouping codes (themes/categories) carry
    their evidence on child codes, so those are included too, labeled 'via'."""
    conn = db.get_conn()
    if not conn.execute("SELECT id FROM runs WHERE id=?", (run_id,)).fetchone():
        _err(404, "Run not found")
    rows = conn.execute(
        "SELECT e.id, e.quote, e.memo, e.confidence, e.start_char, e.end_char, "
        "e.source_id, s.filename AS source, "
        "CASE WHEN e.code_id=? THEN NULL ELSE c.name END AS via "
        "FROM excerpts e JOIN sources s ON s.id = e.source_id "
        "JOIN codes c ON c.id = e.code_id "
        "WHERE e.run_id=? AND (e.code_id=? OR (c.parent_id=? AND c.status='active')) "
        "ORDER BY via, s.filename, COALESCE(e.start_char, 0)",
        (code_id, run_id, code_id, code_id)).fetchall()
    return [dict(r) for r in rows]


def _to_utf16_offsets(text: str, items: list, keys: tuple = ("start", "end")) -> None:
    """Convert Python code-point offsets to UTF-16 code units in place.
    JavaScript strings index by UTF-16, so a single astral character (emoji)
    would otherwise shift every later highlight in the reader."""
    if all(ord(ch) <= 0xFFFF for ch in text):
        return  # offsets already coincide
    pref = [0] * (len(text) + 1)
    acc = 0
    for i, ch in enumerate(text):
        acc += 2 if ord(ch) > 0xFFFF else 1
        pref[i + 1] = acc
    for it in items:
        for k in keys:
            if it.get(k) is not None:
                it[k] = pref[it[k]]


@app.get("/api/runs/{run_id}/sources/{source_id}/coded")
def coded_source(run_id: str, source_id: str):
    """A source document with every located coded span from this run —
    the coded-source reader's data. Only active codes' evidence appears;
    excerpts whose quote could not be located are listed separately."""
    conn = db.get_conn()
    run = conn.execute("SELECT project_id FROM runs WHERE id=?", (run_id,)).fetchone()
    if not run:
        _err(404, "Run not found")
    src = conn.execute("SELECT * FROM sources WHERE id=? AND project_id=?",
                       (source_id, run["project_id"])).fetchone()
    if not src:
        _err(404, "Source not found in this run's project")
    text = src["text"] or ""
    src_meta = json.loads(src["meta"] or "{}")
    page_map = src_meta.get("pages")         # PDFs ingested since page capture
    if not isinstance(page_map, list):
        page_map = []
    page_map = [p for p in page_map if isinstance(p, dict)]

    codes = {r["id"]: dict(r) for r in conn.execute(
        "SELECT id, name, stage, parent_id FROM codes WHERE run_id=? AND status='active'",
        (run_id,)).fetchall()}
    parent_name = {cid: codes.get(c["parent_id"], {}).get("name")
                   for cid, c in codes.items()}

    spans, unlocated = [], []
    located_n: dict = {}
    unlocated_n: dict = {}
    for e in conn.execute(
            "SELECT * FROM excerpts WHERE run_id=? AND source_id=? "
            "ORDER BY COALESCE(start_char, 0)", (run_id, source_id)).fetchall():
        c = codes.get(e["code_id"])
        if not c:
            continue  # evidence on merged/deleted codes is not shown
        item = {"excerpt_id": e["id"], "code_id": c["id"], "code_name": c["name"],
                "code_stage": c["stage"], "parent_name": parent_name.get(c["id"]),
                "quote": e["quote"], "memo": e["memo"], "confidence": e["confidence"],
                "start": e["start_char"], "end": e["end_char"],
                "page": ingestion.page_for_offset(page_map, e["start_char"])}
        ok = (e["start_char"] is not None and e["end_char"] is not None
              and 0 <= e["start_char"] < e["end_char"] <= len(text))
        if ok:
            located_n[c["id"]] = located_n.get(c["id"], 0) + 1
            spans.append(item)
        else:
            unlocated_n[c["id"]] = unlocated_n.get(c["id"], 0) + 1
            unlocated.append(item)

    # bounds were validated in Python indices; ship JS-compatible offsets
    _to_utf16_offsets(text, spans)
    pages_out = [dict(p) for p in page_map]
    _to_utf16_offsets(text, pages_out)

    all_cids = set(located_n) | set(unlocated_n)
    return {
        "filename": src["filename"], "text": text, "run_id": run_id,
        "pages": pages_out,
        "spans": spans, "unlocated": unlocated,
        "codes": sorted(
            [{"id": cid, "name": codes[cid]["name"], "stage": codes[cid]["stage"],
              "parent_name": parent_name.get(cid),
              "count": located_n.get(cid, 0),
              "unlocated_count": unlocated_n.get(cid, 0)}
             for cid in all_cids],
            key=lambda c: (-c["count"], -c["unlocated_count"])),
    }


# ---------------- report ----------------

@app.get("/api/runs/{run_id}/report")
def get_report(run_id: str):
    row = db.get_conn().execute("SELECT payload FROM reports WHERE run_id=?",
                                (run_id,)).fetchone()
    if not row:
        _err(404, "No report for this run yet")
    return json.loads(row["payload"])


@app.get("/api/runs/{run_id}/report.docx")
def get_report_docx(run_id: str):
    row = db.get_conn().execute("SELECT payload FROM reports WHERE run_id=?",
                                (run_id,)).fetchone()
    if not row:
        _err(404, "No report for this run yet")
    payload = json.loads(row["payload"])
    data = report_docx.build_docx(payload)
    # HTTP headers are latin-1: send an ASCII-safe fallback name plus the
    # RFC 5987 UTF-8 form so non-Latin project names don't 500 the download
    raw = payload.get("project_name", "report")
    ascii_name = re.sub(r'[^A-Za-z0-9._-]+', "_", raw).strip("_") or "report"
    utf8_name = quote(f"{raw} report.docx".replace('"', ""), safe="")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition":
                 f'attachment; filename="{ascii_name}_report.docx"; '
                 f"filename*=UTF-8''{utf8_name}"})


# ---------------- static frontend (production) ----------------

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    _DIST_BASE = FRONTEND_DIST.resolve()

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            _err(404, "Unknown API route")
        # confine strictly to the built frontend directory — never serve
        # anything else (the database and source code live nearby)
        target = (_DIST_BASE / full_path).resolve()
        if (full_path and target.is_file()
                and _DIST_BASE in target.parents):
            return FileResponse(target)
        return FileResponse(_DIST_BASE / "index.html")
