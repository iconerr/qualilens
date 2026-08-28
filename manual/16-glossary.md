<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 16. Glossary and Status Reference

## The application's vocabulary

**Project.** One analysis, consisting of a method, a set of setup answers, a provider and model, and a set of data sources. The method is fixed once any run exists. Projects are listed on the home screen and deleted from there.

**Source.** One uploaded file and the text extracted or transcribed from it. Sources belong to a project and are shared by every run in it.

**Group.** An optional label attached to a source at upload, available only in content analysis with group comparison switched on. Sources without a label are counted together as `Ungrouped`.

**Paper.** A source in a literature synthesis project — one uploaded article, chapter, or report. The word marks nothing special in the database; the method treats every source as a paper.

**Label.** The short name a literature synthesis cites a paper by, of the form `Okafor, 2021`, read off the paper's own text during extraction and editable at the extraction review. A paper whose text shows no citation is labeled by its filename, and two papers arriving at the same label are disambiguated with their filenames.

**Run.** One execution of the method's pipeline over the project's sources. A project may hold several runs, and each holds its own codes, excerpts, checkpoints, and report.

**Stage.** One step in the pipeline. A work stage calls the AI model and writes to the database. A checkpoint stage stops and waits for you. The Run screen labels each stage as automated or as your review.

**Segment.** A slice of a source, up to twenty-four thousand characters, cut at paragraph boundaries. Coding proceeds one segment at a time. The segment is also the unit a resumed run skips when it has already been coded.

**Code.** A named label with a definition, attached to passages of data. Codes carry a stage that says what kind of code they are.

| Code stage | Meaning | Methods |
|---|---|---|
| `open_code` | A first-pass code produced by open or initial coding | Grounded theory, thematic analysis |
| `category` | A grouping of open codes produced by axial coding | Grounded theory |
| `theme` | A grouping of initial codes produced by theme construction | Thematic analysis |
| `core` | The core category produced by selective coding | Grounded theory |
| `codebook` | A code in a fixed codebook or framework | Content analysis, framework |
| `emergent` | A code the AI model proposed outside the framework, awaiting your decision | Framework |
| `extract_field` | One of the five extraction fields — Aims, Method, Sample, Findings, Limitations — carrying a paper's extraction quotes | Literature synthesis |
| `concept` | A cross-paper grouping produced by the synthesis stage | Literature synthesis |

**Excerpt.** One passage of data assigned to one code, stored with its verbatim quote and the character positions of that quote in the source. The excerpt is the unit of evidence, and the character positions are what let the reader draw it over the document.

**Coded span.** An excerpt drawn in place over the text of its source, in [the coded-source reader](10-coded-source-reader.md). The text is split at the boundary where two excerpts overlap, so that each stretch is shaded by how many codes cover it.

**Located and unlocated.** An excerpt is located when its quote was found at an exact position in the source, and unlocated when it was not. An excerpt goes unlocated when the AI model paraphrased rather than copying verbatim. Unlocated excerpts count as evidence in your report. They appear in the reader's **Not located in the text** panel rather than over the text. In literature synthesis, an unlocated extraction quote is additionally barred from grounding the synthesis, and the extraction review shows how many quotes went unlocated per paper.

**Coverage.** The share of a document's characters lying inside at least one coded span, shown in the reader. It describes how much of the document the coding touched. It is not a quality score.

**Minimap.** The strip down the left of the reader representing the whole document, with one mark per coded span at its position in the text. It shows where coding falls and where it thins out.

**Isolate.** To click a code in the reader so that only its passages stay highlighted. Isolating a code also lets you step from one of its passages to the next.

**Memo.** A one-sentence justification attached to an excerpt by the AI coder, recorded in grounded theory, thematic analysis, and framework analysis. In familiarization, a memo is instead a longer analytic note about a whole source. In literature synthesis, a concept excerpt's memo is the point the synthesis recorded for that quote.

**Confidence.** A score between zero and one that the AI coder attaches to an assignment, recorded in content analysis and framework analysis. Framework analysis uses the score to select the assignments you review, flagging those below sixty percent. Emergent codes carry no confidence, because the model proposed the code rather than rating a fit.

**Checkpoint.** A stage where the pipeline stops and presents its output for your decisions. See [Checkpoints](09-checkpoints.md).

**Via.** The label the checkpoint's evidence panel puts on an excerpt that a grouping code carries through one of its child codes, naming that child. All of a theme's evidence is held this way, because themes carry no excerpts of their own.

**Resolution.** The set of decisions you submit at a checkpoint. It is stored with the checkpoint, so your audit trail records what you decided and not merely that you decided something.

**Event.** One entry in the audit log. An event records a stage boundary, a model call, a decision of yours, a dropped assignment, or an error.

**Usage.** The running total of calls and tokens for a run, accumulated from the providers' own responses. Tokens billed for a call that then failed are included. The total therefore reflects money you spent rather than work completed.

**Report.** The stored output of a completed run, holding the narrative sections, the method's figure, the full evidence tree, any statistics, and the audit summary. It is generated once at the end of the run, and it does not change afterward.

**Figure.** The one diagram each method's report carries: the grounded theory model, the thematic map, the code frequency chart, the framework heatmap, or the concept-by-paper heatmap. Figures render the structure you approved, disclose on their face when they truncate, and are described in [the reports chapter](12-reports.md).

**Familiarization.** The opening stage of grounded theory and thematic analysis. It produces a summary and an analytic memo for each source. The memo is injected into that source's coding prompt, and the summaries appear in your report appendix.

**Framework matrix.** The output of framework analysis, a table whose rows are sources and whose columns are framework codes, each populated cell holding a summary of what that source said under that code.

**Extraction table.** The output of literature synthesis's first stage and the subject of its first checkpoint: one row per paper carrying its label, its citation line, and consolidated summaries of aims, method, sample, findings, and limitations, each backed by verbatim quotes. The approved table is preserved in the report's appendix.

**Concept-by-paper matrix.** The output of literature synthesis, a table whose rows are papers and whose columns are concepts, each populated cell holding a summary of what that paper contributes to that concept, drawn strictly from that paper's extraction quotes.

**Citation guard.** The scan literature synthesis runs over its finished narrative, checking every parenthetical that carries a year against the corpus labels. Citation-shaped text matching no uploaded paper is listed in the report's limitations section and logged. It is a tripwire against fabricated references, not a validation of real ones.

**Page anchor.** The page number attached to an excerpt from a PDF, derived from a page map recorded at upload. Page anchors appear beside quotes in reports, exports, and the coded-source reader. Sources ingested before page mapping existed, and formats without pages, carry none.

---

## Status badges

### Source status

| Badge | Meaning |
|---|---|
| `ready` | Text is extracted or transcribed, and the source will be included in runs |
| `transcribing` | A recording is being transcribed in the background |
| `error` | Extraction or transcription failed. Audio and video can be retried |

### Run status

| Badge | Meaning | Next step |
|---|---|---|
| `running` | A stage is executing | Watch, or cancel |
| `awaiting review` | A checkpoint is waiting | Approve and continue, or cancel |
| `completed` | Every stage finished and the report exists | Open or export the report |
| `failed` | A stage errored, or the app restarted mid-run | Resume |
| `cancelled` | You cancelled, and this is final | Start a new run |

### Checkpoint status

| Badge | Meaning |
|---|---|
| `pending` | Waiting for your decisions |
| `resolved` | Your decisions were submitted and applied |

### Code status, held in the database rather than shown on screen

| Status | Meaning |
|---|---|
| `active` | In the analysis |
| `merged` | Merged into another code at a checkpoint, with a record of the target |
| `deleted` | Deleted at a checkpoint, and retained in the database as history |

---

## Numbers worth knowing

| Quantity | Value | Where it matters |
|---|---|---|
| Segment size | 24,000 characters | Coding proceeds one segment at a time |
| Familiarization read | First 60,000 characters of each source | The memo reflects the opening of a long transcript |
| Inductive codebook sample | About 45,000 characters divided across sources, at least 2,000 each | Content analysis codebook derivation |
| Existing codes shown to the coder | 120 | Above this, near-duplicate codes appear |
| Evidence shown at a code checkpoint | All of it, on demand | Clicking a code opens every excerpt, not a sample |
| Sample quotes on an emergent candidate | 4, 400 characters each | The framework charting checkpoint |
| Quote preview in the Not located panel | 200 characters | The coded-source reader |
| Low-confidence threshold | Below 0.6 | Which assignments the framework checkpoint shows |
| Low-confidence list length | 60 | The weakest sixty assignments |
| Quotes per matrix cell | 10, each 300 characters | The evidence a matrix summary is drawn from |
| Extraction quotes offered to the synthesis | 14 per paper, each 240 characters | The cross-paper synthesis call; the full set stays in the evidence |
| Excerpts shown per code in the report | 6, then all on request | The interactive report |
| Excerpts written per code in the Word export | 12, then a count of the remainder | The exported document |
| Transcription chunk length | 10 minutes | Where a seam may garble a word |
| Transcription size threshold | About 24 MB | Above this, ffmpeg splits the file |
| Token estimate | 4 characters per token | The pre-run cost estimate |
| Default port | 8765 | Override with `QUALILENS_PORT` |
