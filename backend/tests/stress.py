# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Stress and adversarial pass (mocked model, scratch database). Not part of
the CI checklist — it takes a minute or two — but it is the pass to run
before a release:

    cd backend && .venv/bin/python tests/stress.py

It pushes on: a large corpus through thematic analysis (chunked grouping,
thousands of excerpts, every located span checked against its quote);
concurrent double-submits, uploads, branches, and cancel/resume storms; the
local-only guard under random Host/Origin/token combinations; the updater
under hostile archives; the quote locator, the citation guard, the
resolution applier, and text decoding under fuzzed input. Every section
prints PASS or the first failure and the script exits non-zero on any."""

import io, json, os, pathlib, random, string, sys, tempfile, threading, time, zipfile

# Safety: scratch database, never the researcher's real one.
import pathlib as _pl, tempfile as _tf
sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
import app.db as _db
_td = _tf.mkdtemp(prefix="qualilens_stress_")
_db.DB_PATH = _pl.Path(_td) / "stress.db"
_db.UPLOADS_DIR = _pl.Path(_td) / "uploads"
_db.UPLOADS_DIR.mkdir(exist_ok=True)
os.environ["QUALILENS_TEST"] = "1"

import app.llm as llm
from starlette.testclient import TestClient
from app.main import app, SESSION_TOKEN
from app import update, signing, ingestion
from app.methods import common
from app.methods.base import (RunContext, apply_code_review_resolution, locate_quote,
                              segment_text, _normalize_for_match)
from app.methods.literature_synthesis import _citation_guard

AUTH = {"X-QualiLens-Token": SESSION_TOKEN}
c = TestClient(app, base_url="http://127.0.0.1", headers=AUTH, raise_server_exceptions=False)
rng = random.Random(20260902)
FAILS = []


def section(name):
    print(f"\n== {name}")


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL:", msg)


def wait(run_id, *want, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = c.get(f"/api/runs/{run_id}").json()
        if d["status"] in want:
            return d
        if d["status"] == "failed" and "failed" not in want:
            raise SystemExit(f"run failed at {d['stage_name']}: {d['error']}")
        time.sleep(0.05)
    raise SystemExit(f"timeout waiting for {want}; last {d['status']}")


# ---------------------------------------------------------------------
# 1. Large corpus through thematic analysis
# ---------------------------------------------------------------------
WORDS = ("uncertainty identity support validation anxiety career rumours layoff journal "
         "spouse manager colleague trust pricing onboarding contract flexibility time "
         "pressure candour prescriber relationship rehearsal migration software").split()


def make_doc(i, n_words=9000):
    out = []
    for p in range(n_words // 60):
        sent = " ".join(rng.choice(WORDS) for _ in range(12)).capitalize() + "."
        # sprinkle typography, emoji, and hyphenated line breaks the way PDFs do
        if p % 7 == 0:
            sent = sent.replace(" ", " ", 1)
        if p % 11 == 0:
            sent += " 🎉"
        if p % 13 == 0:
            sent = sent[: len(sent) // 2] + "-\n" + sent[len(sent) // 2:]
        out.append(sent + " " + f"I don't know, said participant {i}." )
    return "\n\n".join(out)


def big_mock(system, user):
    """Scriptable model for the large run: 15 codes per segment, half reused
    from a global vocabulary (so reuse and the reuse cap are exercised),
    quotes taken verbatim from the segment with random perturbations."""
    if "reading data closely" in system:
        return json.dumps({"summary": "s", "memo": "m", "notable_features": []})
    if "INITIAL CODES" in system:
        body = user.split("---\n", 1)[1].rsplit("\n---", 1)[0]
        sents = [s for s in body.replace("\n\n", " ").split(". ") if len(s) > 40]
        codes = []
        for k in range(15):
            name = f"code {rng.randrange(600)}" if rng.random() < 0.5 else f"fresh {rng.randrange(10**6)}"
            exs = []
            for _ in range(3):
                q = rng.choice(sents)[:120]
                r = rng.random()
                if r < 0.2:
                    q = q.upper()
                elif r < 0.3:
                    q = q.replace("-\n", "")
                elif r < 0.35:
                    q = "a paraphrase that appears nowhere " + str(rng.random())
                exs.append({"quote": q, "memo": "why"})
            codes.append({"name": name, "definition": "d" * 300, "excerpts": exs})
        return json.dumps({"codes": codes})
    if "Provisional themes" in user:
        import re
        gids = re.findall(r"\[(g\d+)\]", user)
        k = max(1, len(gids) // 6)
        groups = [gids[i:i + k] for i in range(0, len(gids), k)]
        return json.dumps({"themes": [{"name": f"Theme {i}", "definition": "d", "rationale": "r",
                                       "group_ids": g} for i, g in enumerate(groups)]})
    if "CANDIDATE THEMES" in system:
        import re
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        k = max(1, len(ids) // 5)
        return json.dumps({"themes": [{"name": f"Chunk theme {i}", "definition": "d", "rationale": "r",
                                       "code_ids": ids[i:i + k]} for i in range(0, len(ids), k)]})
    if "Phase 4" in system:
        import re
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        return json.dumps({"reviews": [{"theme_id": i, "coherence": "strong", "distinctness": "adequate",
                                        "recommendation": "keep", "notes": "n"} for i in ids]})
    if "Phase 5" in system:
        import re
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        return json.dumps({"themes": [{"theme_id": i, "final_name": f"Final {n}", "final_definition": "fd"}
                                      for n, i in enumerate(ids)]})
    if "findings section" in system:
        return json.dumps({"sections": [
            {"heading": "Overview of Findings", "body": 'They said "I don\'t know, said participant 3" often. '
                                                        'Another claimed "this sentence was never spoken by anyone at all".'},
            {"heading": "Limitations of This Analysis", "body": "L."}]})
    return json.dumps({"ok": True})


def fake_chat(provider, model, api_key, system, user, max_tokens=8000, temperature=0.3):
    return big_mock(system, user), {"input_tokens": 10, "output_tokens": 5, "stop_reason": "end_turn"}


llm.chat = fake_chat
c.put("/api/settings/keys", json={"anthropic": "sk-stress"})


def run_large_corpus(n_sources=24):
    section(f"large corpus: {n_sources} sources through thematic analysis")
    r = c.post("/api/projects", json={"name": "Stress TA", "method": "thematic",
                                      "config": {"provider": "anthropic", "research_question": "q"}})
    pid = r.json()["id"]
    docs = {}
    for i in range(n_sources):
        text = make_doc(i)
        docs[i] = text
        r = c.post(f"/api/projects/{pid}/sources",
                   files={"file": (f"doc_{i:02}.txt", io.BytesIO(text.encode()), "text/plain")}, data={"grp": ""})
        check(r.status_code == 200, f"upload {i}: {r.text[:100]}")
    t0 = time.time()
    run_id = c.post(f"/api/projects/{pid}/runs").json()["run_id"]
    d = wait(run_id, "awaiting_review")
    cp = d["pending_checkpoint"]
    n_codes = len(cp["payload"]["items"])
    print(f"  coded in {time.time() - t0:.1f}s: {n_codes} codes")
    check(n_codes > common.GROUP_CHUNK, "the corpus must produce more codes than one grouping call takes")
    # a big, messy resolution: merge 40 random pairs, rename 20, delete 10, add 3
    items = cp["payload"]["items"]
    ids = [i["id"] for i in items]
    rng.shuffle(ids)
    decisions = []
    for a, b in zip(ids[0:40], ids[40:80]):
        decisions.append({"id": a, "action": "merge", "merge_into": b})
    for x in ids[80:100]:
        decisions.append({"id": x, "action": "rename", "name": "renamed " + x})
    for x in ids[100:110]:
        decisions.append({"id": x, "action": "delete"})
    r = c.post(f"/api/runs/{run_id}/checkpoints/{cp['id']}/resolve",
               json={"decisions": decisions, "additions": [{"name": "added one"}, {"name": "added two"}],
                     "stage": "open_code"})
    check(r.status_code == 200, f"resolve 1: {r.text[:200]}")
    d = wait(run_id, "awaiting_review")
    cp2 = d["pending_checkpoint"]
    check(cp2["stage"] == "review_themes", "second checkpoint is the theme review")
    check(all(it.get("candidate_name") for it in cp2["payload"]["items"] if it["name"].startswith("Final")),
          "phase-5 names carry their candidate names")
    r = c.post(f"/api/runs/{run_id}/checkpoints/{cp2['id']}/resolve", json={"decisions": [], "stage": "theme"})
    check(r.status_code == 200, f"resolve 2: {r.text[:200]}")
    wait(run_id, "completed")
    print(f"  completed in {time.time() - t0:.1f}s")
    rep = c.get(f"/api/runs/{run_id}/report").json()
    # --- invariants over the report ---
    conn = _db.get_conn()
    bad_span = 0; n_ex = 0; n_unloc = 0
    src_text = {s["id"]: conn.execute("SELECT text FROM sources WHERE id=?", (s["id"],)).fetchone()["text"]
                for s in rep["sources"]}
    for th in rep["themes"]:
        for e in th["excerpts"] + [e for ch in th["children"] for e in ch["excerpts"]]:
            n_ex += 1
            if not e["located"]:
                n_unloc += 1
                continue
            span = src_text[e["source_id"]][e["start_char"]:e["end_char"]]
            if _normalize_for_match(span)[0].strip() != _normalize_for_match(e["quote"])[0].strip() \
                    and not e["quote"].strip().startswith(span.strip()[:20]):
                bad_span += 1
    print(f"  excerpts {n_ex}, unlocated {n_unloc}, bad spans {bad_span}")
    check(bad_span == 0, "every located span must reproduce its quote (normalized) or be its head")
    check(n_unloc < n_ex * 0.1, "paraphrases were 5% of quotes; unlocated must stay near that")
    # orphans: every active open code has an active parent
    orphans = conn.execute(
        "SELECT COUNT(*) c FROM codes k WHERE k.run_id=? AND k.stage='open_code' AND k.status='active' "
        "AND (k.parent_id IS NULL OR k.parent_id NOT IN (SELECT id FROM codes WHERE run_id=? AND stage='theme' AND status='active'))",
        (run_id, run_id)).fetchone()["c"]
    check(orphans == 0, f"{orphans} active open codes without an active theme")
    # evidence on a DELETED code is deleted evidence (kept in the database by
    # design); evidence on a MERGED code would be stranded — the merge must
    # have moved it
    stranded = conn.execute(
        "SELECT COUNT(*) c FROM excerpts e JOIN codes k ON k.id=e.code_id WHERE e.run_id=? AND k.status='merged'",
        (run_id,)).fetchone()["c"]
    check(stranded == 0, f"{stranded} excerpts stranded on merged codes")
    deleted_ev = conn.execute(
        "SELECT COUNT(*) c FROM excerpts e JOIN codes k ON k.id=e.code_id WHERE e.run_id=? AND k.status='deleted'",
        (run_id,)).fetchone()["c"]
    check(deleted_ev == 30, f"the 10 deleted codes keep their 3 excerpts each in the record ({deleted_ev})")
    cross = conn.execute(
        "SELECT COUNT(*) c FROM excerpts e JOIN codes k ON k.id=e.code_id WHERE e.run_id=? AND k.run_id<>e.run_id",
        (run_id,)).fetchone()["c"]
    check(cross == 0, "no excerpt points at another run's code")
    lim = next(s for s in rep["sections"] if s["heading"].startswith("Limitations"))
    check("Quote guard" in lim["body"] and "never spoken" in lim["body"], "the invented narrative quotation was flagged")
    check("participant 3" not in lim["body"], "a real quotation was not flagged")
    check(rep["audit"]["excerpts_unlocated"] == n_unloc, "audit counts agree with the tree")
    check(rep["config"]["research_question"] == "q" and rep["method_label"] == "Thematic Analysis", "config in report")
    summ = rep["audit"]["checkpoints"][0]["summary"]
    check(summ.get("decisions", {}).get("merge") == 40 and summ.get("decisions", {}).get("delete") == 10,
          f"checkpoint summary reflects the decisions: {summ}")
    # docx and audit export render at this size
    t1 = time.time()
    r = c.get(f"/api/runs/{run_id}/report.docx")
    check(r.status_code == 200 and len(r.content) > 50000, "docx renders")
    r = c.get(f"/api/runs/{run_id}/audit.json")
    check(r.status_code == 200 and len(r.json()["events"]) > 100, "audit export renders")
    print(f"  docx+audit in {time.time() - t1:.1f}s")
    # coded reader for the longest source
    sid = rep["sources"][0]["id"]
    data = c.get(f"/api/runs/{run_id}/sources/{sid}/coded").json()
    utf16 = data["text"].encode("utf-16-le")
    bad = 0
    for s in data["spans"]:
        sliced = utf16[2 * s["start"]:2 * s["end"]].decode("utf-16-le")
        if _normalize_for_match(sliced)[0].strip() != _normalize_for_match(s["quote"])[0].strip() \
                and not s["quote"].strip().startswith(sliced.strip()[:20]):
            bad += 1
    check(bad == 0, f"{bad} reader spans do not reproduce their quotes in UTF-16 space")
    # branch from the first review and let it finish
    r = c.post(f"/api/runs/{run_id}/branch", json={"stage": "review_codes"})
    check(r.status_code == 200, f"branch: {r.text[:100]}")
    bid = r.json()["run_id"]
    d = wait(bid, "awaiting_review")
    c.post(f"/api/runs/{bid}/checkpoints/{d['pending_checkpoint']['id']}/resolve", json={"decisions": [], "stage": "open_code"})
    d = wait(bid, "awaiting_review")
    c.post(f"/api/runs/{bid}/checkpoints/{d['pending_checkpoint']['id']}/resolve", json={"decisions": [], "stage": "theme"})
    wait(bid, "completed")
    rep2 = c.get(f"/api/runs/{bid}/report").json()
    check(rep2["audit"]["branched_from"] == run_id, "branch records its origin")
    check(c.get(f"/api/runs/{run_id}/report").status_code == 200, "source run report intact after branch")
    return pid, run_id


# ---------------------------------------------------------------------
# 2. Concurrency
# ---------------------------------------------------------------------
def run_concurrency():
    section("concurrency: double submits, parallel uploads, cancel/resume storms")
    r = c.post("/api/projects", json={"name": "Conc", "method": "thematic",
                                      "config": {"provider": "anthropic", "research_question": "q"}})
    pid = r.json()["id"]
    # 30 parallel uploads
    results = []
    def up(i):
        rr = c.post(f"/api/projects/{pid}/sources",
                    files={"file": (f"p{i}.txt", io.BytesIO(make_doc(i, 600).encode()), "text/plain")}, data={"grp": ""})
        results.append(rr.status_code)
    ths = [threading.Thread(target=up, args=(i,)) for i in range(30)]
    [t.start() for t in ths]; [t.join() for t in ths]
    check(results.count(200) == 30, f"parallel uploads: {results}")
    n = c.get(f"/api/projects/{pid}").json()["sources"]
    check(len(n) == 30, "all 30 sources present")
    run_id = c.post(f"/api/projects/{pid}/runs").json()["run_id"]
    # uploads during the run must be refused
    rr = c.post(f"/api/projects/{pid}/sources",
                files={"file": ("late.txt", io.BytesIO(b"late"), "text/plain")}, data={"grp": ""})
    check(rr.status_code == 409, "upload mid-run refused")
    d = wait(run_id, "awaiting_review")
    cp = d["pending_checkpoint"]
    codes = []
    def resolve():
        rr = c.post(f"/api/runs/{run_id}/checkpoints/{cp['id']}/resolve", json={"decisions": [], "stage": "open_code"})
        codes.append(rr.status_code)
    ths = [threading.Thread(target=resolve) for _ in range(25)]
    [t.start() for t in ths]; [t.join() for t in ths]
    check(codes.count(200) == 1 and all(x in (200, 400) for x in codes), f"exactly one resolve wins: {codes}")
    # cancel/resume storm while it runs
    outcomes = []
    def storm(i):
        if i % 2:
            outcomes.append(("cancel", c.post(f"/api/runs/{run_id}/cancel").status_code))
        else:
            outcomes.append(("resume", c.post(f"/api/runs/{run_id}/resume").status_code))
    ths = [threading.Thread(target=storm, args=(i,)) for i in range(20)]
    [t.start() for t in ths]; [t.join() for t in ths]
    check(all(s in (200, 400) for _, s in outcomes), f"storm never 500s: {outcomes}")
    time.sleep(1.0)
    d = c.get(f"/api/runs/{run_id}").json()
    check(d["status"] in ("cancelled", "awaiting_review", "completed", "running"), f"consistent status after storm: {d['status']}")
    # a cancelled run cannot be resumed, only branched
    if d["status"] == "cancelled":
        check(c.post(f"/api/runs/{run_id}/resume").status_code == 400, "cancelled run refuses resume")
    # parallel branches from the same review
    bres = []
    def br():
        bres.append(c.post(f"/api/runs/{run_id}/branch", json={"stage": "review_codes"}).status_code)
    ths = [threading.Thread(target=br) for _ in range(6)]
    [t.start() for t in ths]; [t.join() for t in ths]
    check(all(s in (200, 400) for s in bres), f"parallel branches: {bres}")
    conn = _db.get_conn()
    # DB invariants after the chaos
    cross = conn.execute("SELECT COUNT(*) c FROM excerpts e JOIN codes k ON k.id=e.code_id WHERE k.run_id<>e.run_id").fetchone()["c"]
    check(cross == 0, "no cross-run excerpt links anywhere")
    open_tx = conn.in_transaction
    check(not open_tx, "no transaction left open on the request thread")


# ---------------------------------------------------------------------
# 3. The guard under fuzz
# ---------------------------------------------------------------------
def run_guard_fuzz():
    section("local-only guard fuzz")
    hosts = ["127.0.0.1", "127.0.0.1:8765", "localhost", "localhost:8765", "[::1]:8765", "::1",
             "192.168.0.5", "attacker.example", "127.0.0.1.attacker.example", "", "localhost.attacker.example",
             "LOCALHOST", "127.0.0.1:1", "0x7f000001", "127.1", "2130706433", "127.0.0.1@evil"]
    origins = [None, "http://127.0.0.1:8765", "http://localhost:8765", "https://evil.example", "null",
               "http://127.0.0.1.evil.example", "http://[::1]:8765", "file://", "http://localhost.evil", "",
               # another local program's page on another port arrives WITH the cookie
               "http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1", "HTTP://127.0.0.1:8765",
               "https://127.0.0.1:8765", "http://127.0.0.1:8765/path"]
    tokens = [None, SESSION_TOKEN, "", SESSION_TOKEN[:-1], SESSION_TOKEN + "x", "x" * 43, SESSION_TOKEN.upper()]
    bad = 0; tried = 0
    for h in hosts:
        for o in origins:
            for t in tokens:
                headers = {"host": h}
                if o is not None:
                    headers["origin"] = o
                if t is not None:
                    headers["x-qualilens-token"] = t
                plain = TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False)
                for method, path in (("GET", "/api/meta"), ("POST", "/api/settings/check_updates"), ("GET", "/")):
                    tried += 1
                    rr = plain.request(method, path, headers=headers)
                    def bare(v):
                        v = v.strip().lower()
                        if "://" in v:
                            v = v.split("://", 1)[1].split("/", 1)[0]
                        if v.startswith("["):
                            return v[1:].split("]", 1)[0]
                        return v.rsplit(":", 1)[0] if v.count(":") == 1 else v
                    def netloc(v):
                        v = v.strip().lower()
                        if "://" in v:
                            v = v.split("://", 1)[1].split("/", 1)[0]
                        return v
                    host_ok = bare(h) in ("127.0.0.1", "localhost", "::1")
                    # since 2026-09-03 an Origin must be the app's own origin EXACTLY:
                    # http, and the same host:port the browser addressed (the Host header)
                    origin_ok = o is None or (o.strip().lower().startswith("http://")
                                              and netloc(h) != "" and netloc(o) == netloc(h))
                    tok_ok = t == SESSION_TOKEN
                    if path.startswith("/api"):
                        should = host_ok and origin_ok and tok_ok
                    else:
                        should = host_ok and origin_ok
                    if rr.status_code >= 500:
                        bad += 1; print("  500 on", h, o, t, path)
                    elif should and rr.status_code in (401, 403, 421):
                        bad += 1; print("  wrongly refused", h, o, t, path, rr.status_code)
                    elif not should and rr.status_code not in (401, 403, 421):
                        bad += 1; print("  wrongly ALLOWED", h, o, t, path, rr.status_code)
    print(f"  {tried} requests")
    check(bad == 0, f"{bad} guard decisions wrong")


# ---------------------------------------------------------------------
# 4. Updater under hostile archives
# ---------------------------------------------------------------------
def run_updater_fuzz():
    section("updater under hostile archives")
    root = pathlib.Path(tempfile.mkdtemp(prefix="ql_upd_"))
    (root / "backend" / "app").mkdir(parents=True); (root / "backend" / "data").mkdir()
    (root / "backend" / "app" / "main.py").write_text("# old")
    (root / "backend" / "data" / "qualilens.db").write_text("PRECIOUS")
    (root / "frontend" / "dist").mkdir(parents=True)
    update.APP_ROOT = root; update.BACKUP_DIR = root / ".update-backup"
    seed = bytes(range(32)); update.PUBLIC_KEY_HEX = signing.public_hex_from_seed(seed)
    before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    def zipped(entries, sign=True, tamper=None):
        files = dict(entries)
        if sign:
            import hashlib
            lines = [f"{hashlib.sha256(v if isinstance(v, bytes) else v.encode()).hexdigest()}  {k[len('QualiLens/'):]}"
                     for k, v in sorted(files.items())]
            man = "\n".join(lines) + "\n"
            files["QualiLens/MANIFEST.sha256"] = man
            files["QualiLens/MANIFEST.sig"] = signing.sign_bytes(man.encode(), seed)
        files.update(tamper or {})
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for k, v in files.items():
                zi = zipfile.ZipInfo(k)
                if k.endswith(".lnk"):
                    zi.external_attr = 0o120777 << 16     # symlink
                z.writestr(zi, v)
        p = root / "cand.zip"; p.write_bytes(buf.getvalue()); return p
    base = {"QualiLens/run.sh": "#!/bin/bash\n", "QualiLens/backend/app/main.py": "# new",
            "QualiLens/frontend/dist/index.html": "x", "QualiLens/VERSION": "9999.01.01-0000",
            "QualiLens/NOTICE": "Copyright 2026 Ashita Aggarwal and Suraj Commuri"}
    cases = {
        "junk bytes": (None, b"not a zip at all"),
        "empty zip": ({}, None),
        "unsigned": (dict(base), "unsigned"),
        "absolute path": (dict(base, **{"/etc/evil": "x"}), None),
        "dotdot": (dict(base, **{"QualiLens/../evil": "x"}), None),
        "symlink member": (dict(base, **{"QualiLens/backend/app/x.lnk": "/etc/passwd"}), None),
        "data path": (dict(base, **{"QualiLens/backend/data/qualilens.db": "ATTACK"}), "ok-but-refused-member"),
        "extra unsigned member": (dict(base), {"QualiLens/backend/app/planted.py": "x"}),
        "tampered member": (dict(base), {"QualiLens/backend/app/main.py": "# evil"}),
        "tampered manifest": (dict(base), {"QualiLens/MANIFEST.sha256": "deadbeef  x\n"}),
        "garbage manifest": (dict(base), {"QualiLens/MANIFEST.sha256": "\x00\x01\x02"}),
        "garbage sig": (dict(base), {"QualiLens/MANIFEST.sig": "!!!not base64!!!"}),
        "unicode names": (dict(base, **{"QualiLens/backend/app/файл.py": "x"}), "ok"),
        "no NOTICE": ({k: v for k, v in base.items() if k != "QualiLens/NOTICE"}, None),
        "wrong NOTICE": (dict(base, **{"QualiLens/NOTICE": "someone else"}), None),
        "huge declared member": (dict(base, **{"QualiLens/big.bin": b"\0" * 1024}), "bomb"),
        "too many members": ({f"QualiLens/f{i}": "x" for i in range(update.MAX_MEMBER_COUNT + 5)}, None),
        "double-nested root": ({"Outer/" + k: v for k, v in base.items()}, None),
    }
    for name, (entries, mode) in cases.items():
        try:
            if entries is None:
                p = root / "cand.zip"; p.write_bytes(mode)
            elif mode == "unsigned":
                p = zipped(entries, sign=False)
            elif isinstance(mode, dict):
                p = zipped(entries, tamper=mode)
            elif mode == "bomb":
                p = zipped(entries)
                # rewrite the declared size in the central directory to an implausible number
                data = bytearray(p.read_bytes())
                idx = data.find(b"big.bin")
                p.write_bytes(bytes(data))
                update.MAX_UNPACKED_BYTES, saved = 100, update.MAX_UNPACKED_BYTES
            else:
                p = zipped(entries)
            (root / "backend" / "data" / "qualilens.db").write_text("PRECIOUS")
            try:
                res = update.apply_update(p)
                outcome = "installed"
            except update.UpdateError as e:
                outcome = f"refused: {str(e)[:60]}"
            except Exception as e:  # noqa: BLE001
                outcome = f"EXCEPTION {type(e).__name__}: {e}"
                check(False, f"{name}: non-UpdateError exception {type(e).__name__}: {e}")
            finally:
                if mode == "bomb":
                    update.MAX_UNPACKED_BYTES = saved
            expect_install = mode in ("ok", "ok-but-refused-member")
            check((outcome == "installed") == expect_install, f"{name}: {outcome}")
            check((root / "backend" / "data" / "qualilens.db").read_text() == "PRECIOUS", f"{name}: data untouched")
            # nothing written outside the root
            check(not pathlib.Path("/etc/evil").exists() and not (root.parent / "evil").exists(), f"{name}: no escape")
            print(f"  {name:24} -> {outcome}")
        except Exception as e:  # noqa: BLE001
            check(False, f"{name}: harness error {e}")


# ---------------------------------------------------------------------
# 5. Locator, guard, resolution, decoding under fuzz
# ---------------------------------------------------------------------
def run_fuzz():
    section("locate_quote fuzz")
    alphabet = string.ascii_letters + string.digits + " \n\t.,;:'\"-–—“”‘’ﬁﬂ­éüçß" + "🎉😀"
    t0 = time.time(); worst = 0; found = 0; tried = 0
    for _ in range(400):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(50, 4000)))
        for _ in range(5):
            if len(text) < 30:
                break
            a = rng.randrange(0, len(text) - 25); b = a + rng.randrange(10, min(200, len(text) - a))
            q = text[a:b]
            r = rng.random()
            if r < 0.3: q = q.upper()
            elif r < 0.5: q = q.replace("\n", " ")
            elif r < 0.6: q = q.translate({ord("“"): '"', ord("”"): '"', ord("’"): "'"})
            elif r < 0.7: q = q + "-\nx"
            elif r < 0.8: q = "".join(ch for ch in q if ch != "\xad")
            tried += 1
            t1 = time.time()
            try:
                s, e = locate_quote(text, q, window=(max(0, a - 50), min(len(text), b + 50)) if rng.random() < 0.5 else None)
            except Exception as ex:  # noqa: BLE001
                check(False, f"locate_quote raised {type(ex).__name__}: {ex}"); continue
            worst = max(worst, time.time() - t1)
            if s is not None:
                found += 1
                check(0 <= s < e <= len(text), "span inside text")
                span = text[s:e]
                ns = _normalize_for_match(span)[0].strip(); nq = _normalize_for_match(q)[0].strip()
                ok = ns == nq or nq.startswith(ns[:20]) or ns.startswith(nq[:20]) or nq[:20] in ns or ns in nq
                check(ok, f"span mismatch: {span[:40]!r} vs {q[:40]!r}")
    print(f"  {tried} lookups, {found} located, worst {worst*1000:.1f} ms, total {time.time()-t0:.1f}s")
    # a very long text
    long = ("word " * 200000)
    t1 = time.time(); locate_quote(long, "WORD word Word" * 3); locate_quote(long, "xyzzy"); dt = time.time() - t1
    print(f"  1 MB text, two lookups: {dt:.2f}s")
    check(dt < 5, "long-text lookups stay fast")

    section("segment_text fuzz")
    for _ in range(200):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 5000)))
        segs = segment_text(text, rng.randrange(20, 800))
        check("".join(s for _, s, _ in segs) == text, "segments concatenate to the text")
        check(all(text[st:st + len(s)] == s for _, s, st in segs), "segment offsets right")

    section("citation guard fuzz")
    for _ in range(300):
        labels = [f"{''.join(rng.choice(string.ascii_letters) for _ in range(rng.randrange(2, 9)))}, {rng.randrange(1900, 2027)}"
                  for _ in range(rng.randrange(1, 8))]
        body = " ".join(f"({rng.choice(labels)})" if rng.random() < 0.6 else
                        f"({''.join(rng.choice(string.ascii_letters + ' ,&;') for _ in range(rng.randrange(1, 30)))}, {rng.randrange(1900, 2027)})"
                        for _ in range(rng.randrange(0, 12)))
        try:
            flagged = _citation_guard([{"body": body}], labels)
        except Exception as ex:  # noqa: BLE001
            check(False, f"guard raised {ex}"); continue
        for f in flagged:
            check(f not in labels, f"corpus label flagged: {f}")

    section("resolution fuzz")
    conn = _db.get_conn()
    for _ in range(40):
        pid, rid, sid = _db.new_id(), _db.new_id(), _db.new_id()
        conn.execute("INSERT INTO projects(id,name,method,config,created_at) VALUES(?,?,?,?,?)", (pid, "F", "thematic", "{}", _db.now()))
        conn.execute("INSERT INTO sources(id,project_id,filename,kind,status,text,meta,created_at) VALUES(?,?,?,?,?,?,?,?)",
                     (sid, pid, "s.txt", "text", "ready", "the price was transparent. Support was responsive.", "{}", _db.now()))
        conn.execute("INSERT INTO runs(id,project_id,status,created_at,updated_at) VALUES(?,?,?,?,?)", (rid, pid, "running", _db.now(), _db.now()))
        conn.commit()
        ctx = RunContext(rid, {"id": pid, "method": "thematic", "name": "F"},
                         [{"id": sid, "filename": "s.txt", "text": "the price was transparent. Support was responsive.", "meta": {}}],
                         {}, "anthropic", "m", "k")
        ids = [ctx.add_code(f"c{i}", "", "open_code") for i in range(8)]
        for i in ids:
            ctx.add_excerpt(i, sid, rng.choice(["the price was transparent", "Support was responsive"]))
        decisions = []
        for _ in range(rng.randrange(0, 12)):
            r = rng.random()
            if r < 0.1: decisions.append("garbage")
            elif r < 0.2: decisions.append({"id": None, "action": "delete"})
            elif r < 0.3: decisions.append({"id": "ffffffffffff", "action": "rename", "name": "x"})
            elif r < 0.5: decisions.append({"id": rng.choice(ids), "action": "merge", "merge_into": rng.choice(ids)})
            elif r < 0.7: decisions.append({"id": rng.choice(ids), "action": "delete"})
            elif r < 0.85: decisions.append({"id": rng.choice(ids), "action": "rename", "name": rng.choice(["", "  ", "N"])})
            else: decisions.append({"id": rng.choice(ids), "action": "keep", "definition": ""})
        try:
            apply_code_review_resolution(ctx, {"decisions": decisions, "stage": "open_code",
                                               "additions": [{"name": ""}, {"name": "add"}]})
        except ValueError:
            pass
        except Exception as ex:  # noqa: BLE001
            check(False, f"resolution raised {type(ex).__name__}: {ex}")
        stranded = conn.execute("SELECT COUNT(*) c FROM excerpts e JOIN codes k ON k.id=e.code_id WHERE e.run_id=? AND k.status='merged'", (rid,)).fetchone()["c"]
        check(stranded == 0, f"stranded evidence after fuzzed resolution: {stranded}")
        total = conn.execute("SELECT COUNT(*) c FROM excerpts WHERE run_id=?", (rid,)).fetchone()["c"]
        check(total == 8, "no evidence lost or duplicated")

    section("decoding fuzz")
    for _ in range(500):
        raw = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 300)))
        try:
            out = ingestion.decode_text(raw)
            check(isinstance(out, str), "decode returns str")
        except Exception as ex:  # noqa: BLE001
            check(False, f"decode raised {ex}")
    for name in ["", ".", "..", "a.", ".RTF", "x.TxT", "x.tar.gz", "../../etc/passwd.txt", "𝔘𝔫𝔦.pdf", "a" * 300 + ".md"]:
        try:
            ingestion.classify(name)
        except ValueError:
            pass
        except Exception as ex:  # noqa: BLE001
            check(False, f"classify raised {type(ex).__name__} for {name!r}")

    section("API bodies fuzz (never 500)")
    paths = ["/api/projects", "/api/settings/keys", "/api/settings/test_key", "/api/settings/check_models",
             "/api/runs/zzz/branch", "/api/runs/zzz/checkpoints/yyy/resolve", "/api/projects/zzz"]
    bodies = [b"", b"{", b"[]", b"null", b'{"name": 1}', b'{"a":' + b"1" * 100000 + b"}", "🎉".encode(), b"\x00\xff"]
    n500 = 0
    for p in paths:
        for b in bodies:
            for m in ("POST", "PUT"):
                rr = c.request(m, p, content=b, headers={"content-type": "application/json"})
                if rr.status_code >= 500:
                    n500 += 1; print("  500:", m, p, b[:20])
    check(n500 == 0, f"{n500} server errors on junk bodies")


# ---------------------------------------------------------------------
# 6. The other methods end to end through the API, at size
# ---------------------------------------------------------------------
SURNAMES = ("Okafor Baker Nguyen Schmidt Rossi Tanaka Kowalski Haddad Petrov Silva Andersen Moreau "
            "Yilmaz Chen Dubois Novak Fischer Costa Ivanova Berg Larsen Weber Santos Popescu Kim Mensah "
            "Lindqvist Horvat Byrne Nakamura").split()


def make_paper(i):
    cyr = (i == 3)
    head = ("ПЕРЕСБОРКА СОЦИАЛЬНОГО\nЛатур, Б. (2005). Пересборка социального.\n\n" if cyr
            else f"A Study of Thing {i}\n{SURNAMES[i]}, A. ({1990 + i}). Journal of Things, {i}(1).\n\n")
    body = []
    for p in range(60):
        sent = " ".join(rng.choice(WORDS) for _ in range(14)).capitalize()
        if p % 9 == 0:
            sent = sent[: len(sent) // 2] + "-\n" + sent[len(sent) // 2:]
        body.append(sent + f". This paper finds thing {i} in study {p}.")
    body.append("Prior work by Smith (1998) found the opposite; Jones (2003) agreed with Smith.")
    refs = "\n\nReferences\n\n" + "\n".join(f"Ref{k}, R. ({1950 + k}). Old paper {k}. Old Journal." for k in range(40))
    return head + "\n\n".join(body) + refs


def ls_mock(system, user):
    import re
    if "STRUCTURED EXTRACTION" in system:
        seg = user.split("---\n", 1)[1].rsplit("\n---", 1)[0]
        cit = ""
        m = re.search(r"^(.*\(\d{4}\)\..*)$", seg, re.M)
        if m:
            cit = m.group(1)
        sents = [x for x in seg.split(". ") if "finds thing" in x]
        quotes = []
        for x in sents[:6]:
            q = x[:100]
            if rng.random() < 0.3:
                q = q.replace("-\n", "").upper()
            quotes.append({"quote": q + ".", "why": "w"})
        return json.dumps({"citation": cit, "cited_work": "Smith (1998) found the opposite.",
                           "fields": {"findings": {"notes": "finds things", "quotes": quotes},
                                      "aims": {"notes": "aims", "quotes": []}, "method": {"notes": "", "quotes": []},
                                      "sample": {"notes": "", "quotes": []}, "limitations": {"notes": "", "quotes": []}}})
    if "consolidating a structured extraction" in system:
        m = re.search(r"citation: (.*)", user)
        cit = m.group(1) if m else ""
        lab = ""
        mm = re.search(r"^([^,(\n]+?),? [A-ZА-Я]?\.? ?\((\d{4})\)", cit)
        if "Латур" in cit:
            lab = "Латур, 2005"
        elif mm:
            lab = f"{mm.group(1).strip()}, {mm.group(2)}"
        return json.dumps({"label": lab, "citation": cit, "aims": "a", "method": "m", "sample": "s",
                           "findings": "finds things", "limitations": "l",
                           "cited_work": "Smith (1998) found the opposite."})
    if "CROSS-PAPER SYNTHESIS" in system:
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        k = max(1, len(ids) // 4)
        return json.dumps({"concepts": [{"name": f"Concept {i}", "definition": "d", "rationale": "r",
                                         "support": [{"excerpt_id": e, "point": "p"} for e in ids[i * k:(i + 1) * k]]}
                                        for i in range(4)] + [
            {"name": "Phantom", "definition": "d", "rationale": "r",
             "support": [{"excerpt_id": "ffffffffffff", "point": "memory"}]}]})
    if "concept-by-paper matrix" in system:
        names = re.findall(r"CONCEPT: (.+?) —", user)
        return json.dumps({"summaries": [{"concept": n, "summary": "s"} for n in names]})
    if "synthesis section of a literature review" in system:
        labels = re.findall(r"^(.+?)(?: — .*)? \(.*\.txt\)$", user.split("cite ONLY these labels):\n", 1)[1].split("\n\n", 1)[0], re.M)
        cites = " ".join(f"({l})" for l in labels[:5])
        return json.dumps({"sections": [
            {"heading": "Overview of the Corpus", "body": f"Many papers {cites}."},
            {"heading": "Synthesis by Concept", "body": "Concept 0 recurs (Латур, 2005) and (Smith, 1998) and (Baker, 2003)."},
            {"heading": "Convergence and Divergence", "body": "They agree."},
            {"heading": "Limitations of This Synthesis", "body": "Small."}]})
    return None


def run_methods_end_to_end():
    section("literature synthesis: 30 papers with a Cyrillic label, references, cited work")
    global fake_chat
    def chat_ls(provider, model, api_key, system, user, max_tokens=8000, temperature=0.3):
        out = ls_mock(system, user)
        if out is None:
            out = big_mock(system, user)
        return out, {"input_tokens": 10, "output_tokens": 5, "stop_reason": "end_turn"}
    llm.chat = chat_ls
    r = c.post("/api/projects", json={"name": "Stress LS", "method": "literature_synthesis",
                                      "config": {"provider": "anthropic", "research_question": "what?"}})
    pid = r.json()["id"]
    for i in range(30):
        r = c.post(f"/api/projects/{pid}/sources",
                   files={"file": (f"paper_{i:02}.txt", io.BytesIO(make_paper(i).encode()), "text/plain")}, data={"grp": ""})
        check(r.status_code == 200, f"paper upload {i}")
    run_id = c.post(f"/api/projects/{pid}/runs").json()["run_id"]
    d = wait(run_id, "awaiting_review")
    cp = d["pending_checkpoint"]
    rows = cp["payload"]["rows"]
    check(len(rows) == 30, "30 extraction rows")
    labs = [r_["label"] for r_ in rows]
    check("Латур, 2005" in labs, f"Cyrillic label read off the paper: {labs[:5]}")
    check(all(r_["cited_work"] for r_ in rows), "cited work captured on every row")
    check(all(r_["unlocated_quotes"] == 0 for r_ in rows), f"hyphenated/upper-cased quotes all locate: {[r_['unlocated_quotes'] for r_ in rows][:8]}")
    evs = c.get(f"/api/runs/{run_id}/events").json()
    check(sum(1 for e in evs if "reference list" in e["message"]) == 30, "reference lists cut on every paper")
    # exclude two papers, edit one label to Latin script
    lat = next(r_ for r_ in rows if r_["label"] == "Латур, 2005")
    res = {"rows": [{"source_id": rows[0]["source_id"], "exclude": True},
                    {"source_id": rows[1]["source_id"], "exclude": True},
                    {"source_id": lat["source_id"], "label": "Latour, 2005"}], "stage": "extract_field"}
    r = c.post(f"/api/runs/{run_id}/checkpoints/{cp['id']}/resolve", json=res)
    check(r.status_code == 200, f"extraction resolve: {r.text[:120]}")
    d = wait(run_id, "awaiting_review")
    cp2 = d["pending_checkpoint"]
    check(cp2["stage"] == "review_synthesis", "concept review reached")
    names = [it["name"] for it in cp2["payload"]["items"]]
    check("Phantom" not in names and len(names) == 4, f"ungrounded concept refused: {names}")
    r = c.post(f"/api/runs/{run_id}/checkpoints/{cp2['id']}/resolve", json={"decisions": [], "stage": "concept"})
    wait(run_id, "completed")
    rep = c.get(f"/api/runs/{run_id}/report").json()
    lim = next(s_ for s_ in rep["sections"] if s_["heading"].startswith("Limitations"))
    check("Smith, 1998" in lim["body"], "phantom citation flagged")
    check("Латур, 2005" in lim["body"], "the narrative's Cyrillic cite of a relabelled paper is flagged (label is now Latin)")
    check("Baker, 2003" in lim["body"], "near-miss year flagged (corpus has Baker, 1991)")
    check("Latour, 2005" not in lim["body"].split("Citation guard")[-1], "the relabelled paper is not flagged")
    check(len(rep["stats"]["excluded"]) == 2 and len(rep["stats"]["rows"]) == 28, "exclusions honoured")
    check(all(r_["cited_work"] for r_ in rep["stats"]["extraction_rows"]), "cited work in the appendix rows")
    r = c.get(f"/api/runs/{run_id}/report.docx")
    check(r.status_code == 200, "LS docx renders")
    llm.chat = fake_chat

    section("framework with promotion through the API; content analysis with groups")
    def chat_fw(provider, model, api_key, system, user, max_tokens=8000, temperature=0.3):
        if "FRAMEWORK ANALYSIS" in system:
            if "only these codes" in user:
                return json.dumps({"assignments": [{"code": "Trial", "quote": "the price was transparent", "confidence": 0.7, "memo": "m"}]}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
            return json.dumps({"assignments": [{"code": "Cost", "quote": "the price was transparent", "memo": "m"}],
                               "emergent": [{"proposed_code": "Trial", "definition": "d", "quote": "Support was responsive"}]}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
        if "framework-analysis matrix" in system:
            return json.dumps({"summaries": [{"code": "Cost", "summary": "s"}, {"code": "Trial", "summary": "s"}]}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
        if "findings section" in system:
            return json.dumps({"sections": [{"heading": "Overview of Findings", "body": "b"}]}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
        if "deriving a CODEBOOK" in system:
            return json.dumps({"codes": [{"name": "Pricing", "definition": "d"}, {"name": "Support", "definition": "d"}]}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
        if "APPLYING a fixed codebook" in system:
            return json.dumps({"assignments": [{"code": "Pricing", "quote": "the price was transparent"},
                                               {"code": "Support", "quote": "Support was responsive", "confidence": 0.9}]}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
        return json.dumps({"ok": True}), {"input_tokens": 1, "output_tokens": 1, "stop_reason": "end_turn"}
    llm.chat = chat_fw
    doc = "We chose the vendor because the price was transparent. Support was responsive."
    r = c.post("/api/projects", json={"name": "FW", "method": "framework",
                                      "config": {"provider": "anthropic", "research_question": "q", "allow_emergent": "true",
                                                 "codebook_text": "Cost: cost"}})
    pid = r.json()["id"]
    for i in range(3):
        c.post(f"/api/projects/{pid}/sources", files={"file": (f"d{i}.txt", io.BytesIO(doc.encode()), "text/plain")}, data={"grp": ""})
    run_id = c.post(f"/api/projects/{pid}/runs").json()["run_id"]
    d = wait(run_id, "awaiting_review")
    cp = d["pending_checkpoint"]
    check(cp["payload"]["low_confidence_total"] == 3 and cp["payload"]["low_confidence"][0]["confidence"] is None,
          "assignments without a confidence are listed for review")
    em = cp["payload"]["items"][0]
    r = c.post(f"/api/runs/{run_id}/checkpoints/{cp['id']}/resolve",
               json={"decisions": [{"id": em["id"], "action": "keep"}], "excerpt_deletions": []})
    check(r.status_code == 200, f"fw resolve {r.text[:100]}")
    wait(run_id, "completed")
    rep = c.get(f"/api/runs/{run_id}/report").json()
    trial = next(t for t in rep["themes"] if t["name"] == "Trial")
    check(len(trial["excerpts"]) == 6, f"promoted code charted across all 3 sources: {len(trial['excerpts'])} (3 emergent + 3 re-charted)")
    check(all(row["cells"]["Trial"]["n"] == 2 for row in rep["stats"]["rows"]), "matrix column for the promoted code is complete")
    check(any("Charted 1 promoted" in e["message"] for e in c.get(f"/api/runs/{run_id}/events").json()), "promotion charting logged")

    r = c.post("/api/projects", json={"name": "CA", "method": "content_analysis",
                                      "config": {"provider": "anthropic", "research_question": "q",
                                                 "ca_mode": "Inductive — derive the codebook from the data", "ca_compare_groups": "true"}})
    pid = r.json()["id"]
    for i, g in enumerate(["A", "A", "B"]):
        c.post(f"/api/projects/{pid}/sources", files={"file": (f"c{i}.txt", io.BytesIO((doc * (i + 1)).encode()), "text/plain")}, data={"grp": g})
    run_id = c.post(f"/api/projects/{pid}/runs").json()["run_id"]
    d = wait(run_id, "awaiting_review")
    c.post(f"/api/runs/{run_id}/checkpoints/{d['pending_checkpoint']['id']}/resolve", json={"decisions": [], "stage": "codebook"})
    wait(run_id, "completed")
    rep = c.get(f"/api/runs/{run_id}/report").json()
    st = rep["stats"]
    check(st["groups"] == ["A", "B"] and all("by_group_per_10k" in r_ for r_ in st["rows"]), "group rates present")
    confs = [e["confidence"] for t in rep["themes"] for e in t["excerpts"]]
    check(None in confs and 0.9 in confs, f"missing confidence stored as null, given ones kept: {set(map(str, confs))}")
    r = c.get(f"/api/runs/{run_id}/report.docx")
    check(r.status_code == 200, "CA docx renders with rate columns")
    llm.chat = fake_chat


if __name__ == "__main__":
    t0 = time.time()
    run_large_corpus()
    run_methods_end_to_end()
    run_concurrency()
    run_guard_fuzz()
    run_updater_fuzz()
    run_fuzz()
    print(f"\n{'ALL STRESS CHECKS PASSED' if not FAILS else str(len(FAILS)) + ' FAILURES'} in {time.time() - t0:.0f}s")
    for f in FAILS:
        print(" -", f)
    sys.exit(1 if FAILS else 0)
