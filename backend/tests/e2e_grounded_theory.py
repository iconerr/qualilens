# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""End-to-end pipeline test with a mocked LLM. Exercises: project creation,
source upload, run start, all GT stages, all 3 checkpoints (with edits),
report payload, and docx export."""
import io, json, time, sys


# Safety: always run against a scratch database, never the researcher's real
# one — even when this script is executed directly.
import pathlib as _pl, sys as _sys, tempfile as _tf
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
import app.db as _db
import app.keystore as _keystore
_td = _tf.mkdtemp(prefix="qualilens_e2e_")
_db.DB_PATH = _pl.Path(_td) / "e2e.db"
_db.UPLOADS_DIR = _pl.Path(_td) / "uploads"
_db.UPLOADS_DIR.mkdir(exist_ok=True)
_keystore.SECRET_FILE = _pl.Path(_td) / "secret.key"

import app.llm as llm_mod

INTERVIEW_1 = """Interviewer: How did you decide to leave your job?

Participant: Honestly it was the uncertainty that wore me down. Every quarter there were new rumors about layoffs. I kept telling myself it would settle, but it never did.

I started looking for validation elsewhere, asking friends whether I was crazy to leave a stable paycheck.

Eventually I realized I was managing my anxiety instead of managing my career."""

INTERVIEW_2 = """Interviewer: What was the hardest part of the transition?

Participant: The identity piece. For fifteen years I introduced myself by my employer's name. Who was I without it?

My spouse kept reassuring me, and that support mattered more than any severance package.

I kept a journal, and re-reading it now I see how much I was seeking validation from everyone around me."""

# ---- mock LLM ----
def fake_chat(provider, model, api_key, system, user, max_tokens=8000, temperature=0.3):
    usage = {"input_tokens": 500, "output_tokens": 200}
    if "Respond ONLY with valid JSON" in system:
        return fake_json_router(system, user), usage
    return "Plain narrative text response.", usage

def fake_json_router(system, user):
    if "reading data closely" in system:
        return json.dumps({"summary": "A participant describes leaving a job.",
                           "memo": "Uncertainty and identity loss recur.",
                           "notable_features": ["uncertainty", "identity", "support"]})
    if "OPEN CODING" in system:
        if "uncertainty that wore me down" in user:
            return json.dumps({"codes": [
                {"name": "enduring chronic uncertainty", "definition": "Living with sustained ambiguity about job security.",
                 "excerpts": [{"quote": "it was the uncertainty that wore me down", "memo": "explicit exhaustion from ambiguity"}]},
                {"name": "seeking validation", "definition": "Asking others to confirm one's decisions.",
                 "excerpts": [{"quote": "asking friends whether I was crazy to leave a stable paycheck", "memo": "external confirmation"}]},
                {"name": "managing anxiety", "definition": "Coping with emotional strain.",
                 "excerpts": [{"quote": "I was managing my anxiety instead of managing my career", "memo": "self-diagnosis"}]}]})
        return json.dumps({"codes": [
            {"name": "losing occupational identity", "definition": "Losing self-definition tied to employer.",
             "excerpts": [{"quote": "For fifteen years I introduced myself by my employer's name.", "memo": "identity fused with employer"}]},
            {"name": "seeking validation", "definition": "Asking others to confirm one's decisions.",
             "excerpts": [{"quote": "seeking validation from everyone around me", "memo": "recurring pattern"}]},
            {"name": "drawing on spousal support", "definition": "Relying on partner reassurance.",
             "excerpts": [{"quote": "My spouse kept reassuring me", "memo": "support as resource"}]}]})
    if "AXIAL CODING" in system or "grouping open codes" in system:
        # ids appear in user text as [id] — parse them
        import re
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        half = max(1, len(ids)//2)
        return json.dumps({"categorys": [
            {"name": "Navigating destabilization", "definition": "Conditions destabilizing the participant.",
             "rationale": "These codes describe destabilizing conditions.", "code_ids": ids[:half]},
            {"name": "Rebuilding the self", "definition": "Strategies to rebuild identity and confidence.",
             "rationale": "These codes describe rebuilding strategies.", "code_ids": ids[half:]}]})
    if "SELECTIVE CODING" in system:
        return json.dumps({"core_category": {"name": "Reconstructing identity under uncertainty",
                                             "definition": "The central process of rebuilding a self.",
                                             "is_existing_category_id": None},
                           "storyline": "Participants moved from destabilization to reconstruction.",
                           "relationships": [{"from_category_id": "x", "relation": "condition for", "to": "core",
                                              "explanation": "Destabilization triggers reconstruction."}],
                           "theoretical_gaps": ["No negative cases sampled."]})
    if "findings section" in system:
        return json.dumps({"sections": [
            {"heading": "Overview of Findings", "body": "Two categories emerged.\n\nThey cohere around a core."},
            {"heading": "Findings by Theme", "body": "Navigating destabilization... Rebuilding the self..."},
            {"heading": "Integration", "body": "The categories relate through the core."},
            {"heading": "Limitations of This Analysis", "body": "LLM-assisted coding has limits."}]})
    return json.dumps({"ok": True})

llm_mod.chat = fake_chat

from starlette.testclient import TestClient
from app.main import app, SESSION_TOKEN
import app.pipeline as pipeline

c = TestClient(app, base_url="http://127.0.0.1", headers={"X-QualiLens-Token": SESSION_TOKEN})

# providers key
c.put('/api/settings/keys', json={"anthropic": "sk-fake"})

# create project
r = c.post('/api/projects', json={
    "name": "E2E Test GT", "method": "grounded_theory",
    "config": {"provider": "anthropic", "model": "claude-sonnet-5",
               "research_question": "How do professionals experience voluntary job exit?",
               "gt_variant": "Straussian (axial coding with paradigm model)"}})
assert r.status_code == 200, r.text
proj = r.json(); pid = proj["id"]
print("project:", pid)

# upload two sources
for i, txt in enumerate((INTERVIEW_1, INTERVIEW_2), 1):
    r = c.post(f'/api/projects/{pid}/sources',
               files={"file": (f"interview_{i}.txt", io.BytesIO(txt.encode()), "text/plain")},
               data={"grp": ""})
    assert r.status_code == 200, r.text
print("sources uploaded")

# estimate
r = c.get(f'/api/projects/{pid}/estimate'); print("estimate:", r.json()["est_cost_usd"], "USD")

# start run
r = c.post(f'/api/projects/{pid}/runs'); assert r.status_code == 200, r.text
run_id = r.json()["run_id"]; print("run:", run_id)

def wait_status(*want, timeout=30):
    for _ in range(timeout * 10):
        r = c.get(f'/api/runs/{run_id}'); d = r.json()
        if d["status"] in want: return d
        if d["status"] == "failed": raise SystemExit("RUN FAILED: " + str(d["error"]))
        time.sleep(0.1)
    raise SystemExit("timeout waiting for " + str(want))

# checkpoint 1: open codes — rename one, merge nothing, delete nothing
d = wait_status("awaiting_review")
cp = d["pending_checkpoint"]; assert cp["stage"] == "review_open_codes", cp["stage"]
items = cp["payload"]["items"]
print("open codes:", [i["name"] for i in items])
assert any(i["name"] == "seeking validation" for i in items)
# 'seeking validation' should have excerpts from BOTH sources (code reuse across sources)
sv = next(i for i in items if i["name"] == "seeking validation")
assert sv["excerpt_count"] == 2, sv
# the review shows a code's first quote beside it: id, source name, no 'via' on an open code
s0 = sv["sample_excerpts"][0]
assert s0["id"] and s0["source"] and s0["via"] is None and "truncated" in s0, s0
assert sv["source_count"] == 2, sv
assert "children" not in sv, "an open code is not a grouping code"
assert cp["payload"]["source_count"] == 2, cp["payload"].get("source_count")
cov = cp["payload"]["coverage"]
assert len(cov) == 2 and all(isinstance(x["coded_pct"], int) and 0 < x["coded_pct"] <= 100 for x in cov), cov
decisions = [{"id": items[0]["id"], "action": "rename", "name": items[0]["name"] + " (edited)"}]
r = c.post(f'/api/runs/{run_id}/checkpoints/{cp["id"]}/resolve', json={"decisions": decisions})
assert r.status_code == 200, r.text

# checkpoint 2: categories
d = wait_status("awaiting_review")
cp = d["pending_checkpoint"]; assert cp["stage"] == "review_categories", cp["stage"]
print("categories:", [i["name"] for i in cp["payload"]["items"]])
# a category names the codes it holds, and its quotes say which code they came through
cat = next(i for i in cp["payload"]["items"] if i["children"])
assert all(k["name"] and isinstance(k["excerpt_count"], int) for k in cat["children"]), cat
assert cat["sample_excerpts"] and all(x["via"] in {k["name"] for k in cat["children"]}
                                      for x in cat["sample_excerpts"]), cat
r = c.post(f'/api/runs/{run_id}/checkpoints/{cp["id"]}/resolve', json={"decisions": []})
assert r.status_code == 200, r.text

# checkpoint 3: core category — edit the storyline
d = wait_status("awaiting_review")
cp = d["pending_checkpoint"]; assert cp["stage"] == "review_core", cp["stage"]
core = cp["payload"]["items"][0]
print("core:", core["name"])
# the core review names each category with its weight, and shows the sampling gaps
cats = cp["payload"]["categories"]
assert cats and all(c_["name"] and isinstance(c_["codes"], int) and isinstance(c_["excerpts"], int) for c_ in cats), cats
assert core["theoretical_gaps"] == ["No negative cases sampled."], core["theoretical_gaps"]
r = c.post(f'/api/runs/{run_id}/checkpoints/{cp["id"]}/resolve',
           json={"decisions": [{"id": core["id"], "storyline": "EDITED STORYLINE.",
                                "theoretical_gaps": ["Sample people who stopped, too.", "  "],
                                "notes": "Storyline rewritten in the participants' terms."}]})
assert r.status_code == 200, r.text
evs = [e["message"] for e in c.get(f'/api/runs/{run_id}/events?after=0').json()]
assert any("Researcher note on the core category" in m and "participants' terms" in m for m in evs), evs[-5:]
assert any("edited the core category" in m and "sampling recommendations" in m for m in evs), evs[-5:]

# completion
d = wait_status("completed")
print("run completed; usage:", d["usage"])

# report
r = c.get(f'/api/runs/{run_id}/report'); assert r.status_code == 200, r.text
rep = r.json()
print("report title:", rep["title"])
print("themes:", [t["name"] for t in rep["themes"]])
assert "EDITED STORYLINE." in json.dumps(rep), "edited storyline must reach the report"
assert "Sample people who stopped, too." in json.dumps(rep), "edited sampling gaps must reach the report"
assert "No negative cases sampled." not in json.dumps(rep), "a gap left out must not reach the report"
assert any("(edited)" in json.dumps(t) for t in rep["themes"]), "renamed code must persist"
# provenance: offsets located
ex = rep["themes"][0]["children"][0]["excerpts"][0]
assert ex["start_char"] is not None, "offsets must be located"
print("provenance sample:", ex["source"], ex["start_char"], ex["end_char"])

# docx
r = c.get(f'/api/runs/{run_id}/report.docx')
assert r.status_code == 200 and len(r.content) > 5000
print("docx bytes:", len(r.content))
# every checkpoint's instructions follow the house style: full sentences, no em dashes
_cps = _db.get_conn().execute("SELECT stage, instructions FROM checkpoints").fetchall()
assert _cps and all("\u2014" not in r["instructions"] for r in _cps), \
    [r["stage"] for r in _cps if "\u2014" in r["instructions"]]
print("ALL E2E CHECKS PASSED")
