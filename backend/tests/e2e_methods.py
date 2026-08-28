# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""E2E for thematic, content analysis, framework, and literature-synthesis
methods (mocked LLM)."""
import io, json, re, time


# Safety: always run against a scratch database, never the researcher's real
# one — even when this script is executed directly.
import pathlib as _pl, sys as _sys, tempfile as _tf
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
import app.db as _db
_td = _tf.mkdtemp(prefix="qualilens_e2e_")
_db.DB_PATH = _pl.Path(_td) / "e2e.db"
_db.UPLOADS_DIR = _pl.Path(_td) / "uploads"
_db.UPLOADS_DIR.mkdir(exist_ok=True)

import app.llm as llm_mod

DOC_A = """We chose the vendor because the price was transparent. Hidden fees elsewhere made us nervous.
Our team also valued the responsive support during the trial period."""
DOC_B = """Support was slow to respond at first, which almost killed the deal.
In the end the transparent pricing convinced our finance team."""

def fake_chat(provider, model, api_key, system, user, max_tokens=8000, temperature=0.3):
    usage = {"input_tokens": 400, "output_tokens": 150}
    if "Respond ONLY with valid JSON" in system:
        return router(system, user), usage
    if "Summarize, in 1-2 sentences" in system:
        return "This source discusses the code's topic directly.", usage
    return "narrative", usage

def router(system, user):
    if "reading data closely" in system:
        return json.dumps({"summary": "s", "memo": "m", "notable_features": ["f"]})
    if "INITIAL CODES" in system:
        if "price was transparent" in user:
            return json.dumps({"codes": [
                {"name": "valuing price transparency", "definition": "d",
                 "excerpts": [{"quote": "the price was transparent", "memo": ""}]},
                {"name": "fearing hidden fees", "definition": "d",
                 "excerpts": [{"quote": "Hidden fees elsewhere made us nervous.", "memo": ""}]}]})
        return json.dumps({"codes": [
            {"name": "valuing price transparency", "definition": "d",
             "excerpts": [{"quote": "the transparent pricing convinced our finance team", "memo": ""}]},
            {"name": "experiencing slow support", "definition": "d",
             "excerpts": [{"quote": "Support was slow to respond at first", "memo": ""}]}]})
    if "CANDIDATE THEMES" in system:
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        return json.dumps({"themes": [
            {"name": "Trust through transparency", "definition": "d", "rationale": "r",
             "code_ids": ids}]})
    if "Phase 4" in system:
        return json.dumps({"reviews": [{"theme_id": re.findall(r"\[([0-9a-f]{12})\]", user)[0],
                                        "coherence": "strong", "distinctness": "adequate",
                                        "recommendation": "keep", "notes": "fine"}]})
    if "Phase 5" in system:
        m = re.findall(r"\[([0-9a-f]{12})\]", user)
        return json.dumps({"themes": [{"theme_id": m[0], "final_name": "Trust Through Transparency",
                                       "final_definition": "Final def."}]})
    if "deriving a CODEBOOK" in system:
        return json.dumps({"codes": [
            {"name": "Pricing transparency", "definition": "Mentions of clear pricing.",
             "inclusion_criteria": "explicit price talk", "example": "the price was transparent"},
            {"name": "Support quality", "definition": "Mentions of vendor support.",
             "inclusion_criteria": "support experiences", "example": "responsive support"}]})
    if "APPLYING a fixed codebook" in system:
        if "price was transparent" in user:
            return json.dumps({"assignments": [
                {"code": "Pricing transparency", "quote": "the price was transparent", "confidence": 0.95},
                {"code": "Support quality", "quote": "responsive support during the trial period", "confidence": 0.9}]})
        return json.dumps({"assignments": [
            {"code": "Pricing transparency", "quote": "the transparent pricing convinced our finance team", "confidence": 0.9},
            {"code": "Support quality", "quote": "Support was slow to respond at first", "confidence": 0.85}]})
    if "FRAMEWORK ANALYSIS" in system:
        if "price was transparent" in user:
            return json.dumps({"assignments": [
                {"code": "Cost factors", "quote": "the price was transparent", "confidence": 0.9, "memo": "m"},
                {"code": "Cost factors", "quote": "Hidden fees elsewhere made us nervous.", "confidence": 0.4, "memo": "low"}],
                "emergent": [{"proposed_code": "Trial experience", "definition": "d",
                              "quote": "responsive support during the trial period"}]})
        return json.dumps({"assignments": [
            {"code": "Service factors", "quote": "Support was slow to respond at first", "confidence": 0.8, "memo": "m"}],
            "emergent": []})
    if "findings section" in system:
        return json.dumps({"sections": [{"heading": "Overview of Findings", "body": "b"}]})
    if "STRUCTURED EXTRACTION" in system:
        if "price was transparent" in user:
            return json.dumps({
                "citation": "Alpha, A. (2021). Choosing vendors. J. Proc., 3(1).",
                "fields": {
                    "aims": {"notes": "why buyers choose vendors", "quotes": []},
                    "method": {"notes": "", "quotes": []},
                    "sample": {"notes": "", "quotes": []},
                    "findings": {"notes": "transparency decided it",
                                 "quotes": [{"quote": "the price was transparent",
                                             "why": "decisive factor"}]},
                    "limitations": {"notes": "fear of hidden fees elsewhere",
                                    "quotes": [{"quote": "Hidden fees elsewhere made us nervous.",
                                                "why": "stated worry"}]}}})
        return json.dumps({
            "citation": "Beta, B. (2022). Deals that nearly die. J. Proc., 4(2).",
            "fields": {
                "aims": {"notes": "how deals survive setbacks", "quotes": []},
                "method": {"notes": "", "quotes": []},
                "sample": {"notes": "", "quotes": []},
                "findings": {"notes": "pricing transparency rescued the deal",
                             "quotes": [{"quote": "the transparent pricing convinced our finance team",
                                         "why": "turning point"}]},
                "limitations": {"notes": "", "quotes": []}}})
    if "consolidating a structured extraction" in system:
        alpha = "Choosing vendors" in user or "doc_1" in user
        return json.dumps({
            "label": "Alpha, 2021" if alpha else "Beta, 2022",
            "citation": ("Alpha, A. (2021). Choosing vendors. J. Proc., 3(1)." if alpha
                         else "Beta, B. (2022). Deals that nearly die. J. Proc., 4(2)."),
            "aims": "Why buyers choose vendors." if alpha else "How deals survive setbacks.",
            "method": "Not reported.", "sample": "Not reported.",
            "findings": ("Transparency decided the choice." if alpha
                         else "Transparent pricing rescued the deal."),
            "limitations": "Fear of hidden fees." if alpha else "Not reported."})
    if "CROSS-PAPER SYNTHESIS" in system:
        ids = re.findall(r"\[([0-9a-f]{12})\]", user)
        support = [{"excerpt_id": i, "point": "shows transparency at work"} for i in ids]
        support.append({"excerpt_id": "deadbeef0000",
                        "point": "a memory citation that must be dropped"})
        return json.dumps({"concepts": [
            {"name": "Transparency as trust", "definition": "d", "rationale": "r",
             "support": support}]})
    if "concept-by-paper matrix" in system:
        names = re.findall(r"CONCEPT: (.+?) —", user)
        return json.dumps({"summaries": [
            {"concept": n, "summary": "This paper reports transparency as decisive."}
            for n in names]})
    if "synthesis section of a literature review" in system:
        return json.dumps({"sections": [
            {"heading": "Overview of the Corpus", "body": "Two papers (Alpha, 2021; Beta, 2022)."},
            {"heading": "Synthesis by Concept", "body": "Transparency ran through both (Alpha, 2021)."},
            {"heading": "Convergence and Divergence",
             "body": "Both agree, echoing older accounts (Smith, 1998)."},
            {"heading": "Limitations of This Synthesis", "body": "Small corpus."}]})
    return json.dumps({"ok": True})

llm_mod.chat = fake_chat

from starlette.testclient import TestClient
from app.main import app
c = TestClient(app)
c.put('/api/settings/keys', json={"anthropic": "sk-fake"})

def make_project(name, method, config, groups=(None, None)):
    r = c.post('/api/projects', json={"name": name, "method": method,
                                      "config": {"provider": "anthropic", **config}})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    for i, (txt, g) in enumerate(zip((DOC_A, DOC_B), groups), 1):
        r = c.post(f'/api/projects/{pid}/sources',
                   files={"file": (f"doc_{i}.txt", io.BytesIO(txt.encode()), "text/plain")},
                   data={"grp": g or ""})
        assert r.status_code == 200, r.text
    r = c.post(f'/api/projects/{pid}/runs'); assert r.status_code == 200, r.text
    return pid, r.json()["run_id"]

def wait(run_id, *want, timeout=30):
    for _ in range(timeout * 10):
        d = c.get(f'/api/runs/{run_id}').json()
        if d["status"] in want: return d
        if d["status"] == "failed": raise SystemExit(f"RUN FAILED at {d['stage_name']}: {d['error']}")
        time.sleep(0.1)
    raise SystemExit("timeout")

def resolve(run_id, d, body=None):
    cp = d["pending_checkpoint"]
    r = c.post(f'/api/runs/{run_id}/checkpoints/{cp["id"]}/resolve', json=body or {"decisions": []})
    assert r.status_code == 200, r.text
    return cp

# ---- thematic ----
pid, rid = make_project("TA", "thematic", {"research_question": "Why do buyers choose vendors?"})
d = wait(rid, "awaiting_review"); assert d["pending_checkpoint"]["stage"] == "review_codes"
resolve(rid, d)
d = wait(rid, "awaiting_review"); cp = d["pending_checkpoint"]
assert cp["stage"] == "review_themes"
assert cp["payload"]["items"][0].get("review"), "phase-4 critique must be in payload"
resolve(rid, d)
d = wait(rid, "completed")
rep = c.get(f'/api/runs/{rid}/report').json()
assert rep["themes"][0]["name"] == "Trust Through Transparency", rep["themes"][0]["name"]
assert rep["themes"][0]["children"], "themes must carry child codes"
print("THEMATIC OK:", rep["themes"][0]["name"])

# ---- content analysis (inductive, groups) ----
pid, rid = make_project("CA", "content_analysis",
                        {"research_question": "q", "ca_mode": "Inductive — derive the codebook from the data",
                         "ca_compare_groups": "true"}, groups=("Site A", "Site B"))
d = wait(rid, "awaiting_review"); assert d["pending_checkpoint"]["stage"] == "review_codebook"
resolve(rid, d)
d = wait(rid, "completed")
rep = c.get(f'/api/runs/{rid}/report').json()
stats = rep["stats"]
assert stats["kind"] == "content_frequencies"
assert stats["total_assignments"] == 4, stats
row = next(r for r in stats["rows"] if r["code"] == "Pricing transparency")
assert row["by_group"] == {"Site A": 1, "Site B": 1}, row
print("CONTENT OK:", [(r['code'], r['count']) for r in stats["rows"]])
r = c.get(f'/api/runs/{rid}/report.docx'); assert r.status_code == 200 and len(r.content) > 5000

# ---- framework (emergent promotion + excerpt deletion) ----
pid, rid = make_project("FW", "framework",
                        {"research_question": "q", "allow_emergent": "true",
                         "codebook_text": "Cost factors: pricing considerations\nService factors: support and service"})
d = wait(rid, "awaiting_review"); cp = d["pending_checkpoint"]
assert cp["stage"] == "review_charting"
pl = cp["payload"]
assert pl["low_confidence"], "low-confidence list must be populated"
assert pl["items"] and pl["items"][0]["name"] == "Trial experience"
emergent_id = pl["items"][0]["id"]
bad_excerpt = pl["low_confidence"][0]["excerpt_id"]
resolve(rid, d, {"decisions": [{"id": emergent_id, "action": "keep"}],
                 "excerpt_deletions": [bad_excerpt]})
d = wait(rid, "completed")
rep = c.get(f'/api/runs/{rid}/report').json()
names = [t["name"] for t in rep["themes"]]
assert "Trial experience" in names, names   # promoted emergent code in framework
assert rep["stats"]["kind"] == "framework_matrix"
assert "Trial experience" in rep["stats"]["codes"]
total_ex = sum(len(t["excerpts"]) for t in rep["themes"])
assert total_ex == 3, total_ex  # 3 fw + 1 emergent - 1 deleted = 3
print("FRAMEWORK OK:", names)

# ---- literature synthesis (extraction edit, exclusion-free, guarded citation) ----
pid, rid = make_project("LS", "literature_synthesis",
                        {"research_question": "What makes buyers trust vendors?"})
d = wait(rid, "awaiting_review"); cp = d["pending_checkpoint"]
assert cp["stage"] == "review_extraction"
pl = cp["payload"]
assert pl["kind"] == "extraction_review"
rows = {r["filename"]: r for r in pl["rows"]}
assert rows["doc_1.txt"]["label"] == "Alpha, 2021", rows["doc_1.txt"]
assert rows["doc_1.txt"]["quote_counts"]["findings"] == 1
assert rows["doc_1.txt"]["fields"]["findings"] == "Transparency decided the choice."
resolve(rid, d, {"rows": [{"source_id": rows["doc_1.txt"]["source_id"],
                           "findings": "EDITED FINDINGS."}]})
d = wait(rid, "awaiting_review"); cp = d["pending_checkpoint"]
assert cp["stage"] == "review_synthesis"
items = cp["payload"]["items"]
assert items and items[0]["name"] == "Transparency as trust"
assert sorted(items[0]["papers"]) == ["Alpha, 2021", "Beta, 2022"], items[0]
# all three extraction quotes made it in; the bogus excerpt id must not have
assert items[0]["excerpt_count"] == 3, items[0]
resolve(rid, d, {"decisions": [{"id": items[0]["id"], "action": "rename",
                                "name": "Transparency and trust"}]})
d = wait(rid, "completed")
rep = c.get(f'/api/runs/{rid}/report').json()
stats = rep["stats"]
assert stats["kind"] == "concept_matrix"
assert stats["codes"] == ["Transparency and trust"], stats["codes"]
assert {r["source"] for r in stats["rows"]} == {"Alpha, 2021", "Beta, 2022"}
for r in stats["rows"]:
    cell = r["cells"]["Transparency and trust"]
    want_n = 2 if r["source"] == "Alpha, 2021" else 1
    assert cell["n"] == want_n and "transparency" in cell["summary"].lower(), r
ex_rows = {r["filename"]: r for r in stats["extraction_rows"]}
assert ex_rows["doc_1.txt"]["fields"]["findings"] == "EDITED FINDINGS."  # researcher edit is final
theme = rep["themes"][0]
assert theme["name"] == "Transparency and trust"
assert all(e["start_char"] is not None for e in theme["excerpts"]), theme["excerpts"]
lim = next(s for s in rep["sections"] if s["heading"] == "Limitations of This Synthesis")
assert "Citation guard" in lim["body"] and "Smith, 1998" in lim["body"], lim["body"]
assert not any("Alpha" in s["body"] and "Citation guard" in s["body"] and "Alpha, 2021" in
               s["body"].split("Citation guard")[1] for s in rep["sections"]), \
    "corpus labels must not be flagged by the citation guard"
evs = c.get(f'/api/runs/{rid}/events').json()
assert any("Dropped support" in e["message"] for e in evs), \
    "the out-of-corpus excerpt id must be dropped and logged"
r = c.get(f'/api/runs/{rid}/report.docx'); assert r.status_code == 200 and len(r.content) > 5000
print("LITERATURE SYNTHESIS OK:", stats["codes"])
print("ALL METHOD E2E CHECKS PASSED")
