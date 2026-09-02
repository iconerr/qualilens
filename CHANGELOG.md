<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to QualiLens. Release tags are semantic versions; each
release also carries a build stamp (`build YYYY.MM.DD-HHMM`) that the in-app
update check compares against your installation.

## 1.6.1 — 2026-09-02

- Settings: "Where your data live".

## 1.6.0 — 2026-09-02

- A checkpoint can be worked in a spreadsheet. **Download as spreadsheet**
  saves the code review (or the literature-synthesis extraction table) as
  an `.xlsx` workbook with a column for your action, one for a merge
  target, and one for notes; **Upload spreadsheet** reads it back and loads
  its decisions into the review screen for you to check before approving.
  Rows are matched by id, an unknown row is listed rather than guessed at,
  a code with no row is unchanged, and a workbook from another checkpoint is
  refused. Notes enter the audit trail beside the decisions they explain,
  and the workbook itself is kept with the run and named in the audit
  export. Definition boxes on the review screen now grow with their text.
- A quieter interface: a cool near-white ground, one ink for text and the
  primary action, colour kept for done, waiting, and wrong. The app now
  ships its own type — Inter for the interface and JetBrains Mono for model
  ids, build stamps, and the audit log — so it looks the same on Mac,
  Windows, and Linux, and fetches nothing to do so. Figures follow the same
  palette; the thematic map's connectors no longer cross code boxes.
- After an update, the page waits for the new build and reconnects on its
  own once you have started the app again; nothing to close or reopen. A
  tab left open across any restart now reloads itself to pick up the new
  session, instead of showing a token error.
- The launcher checks the port before any other work and, when it is taken,
  says what holds it: for a QualiLens server, the build it is running, when
  it started, and the exact command to stop it. A server left running in a
  forgotten terminal keeps serving the build it started with, so this is how
  you learn that the app in your browser is older than the folder. The
  served page and `/api/meta` now carry the running build.
- Test runs no longer re-stamp the folder's `VERSION`.

## 1.5.0 — 2026-09-02

Security and evidence-integrity release. Updating is recommended.

- Security hardening of the local server and of the in-app updater. Update
  bundles are now signed, and only signed bundles install; an update is
  refused while a run is executing or awaiting review. A tab left open across
  an app restart now asks you to reload the page.
- Excerpts state their own status: an excerpt whose quote cannot be found
  verbatim in its source is marked *unverified* in the report and listed
  outside quotation marks in the Word export; the audit appendix counts
  located and unverified excerpts. Quote location tolerates case, ligatures,
  soft hyphens, and PDF line-break hyphenation, and searches the segment the
  model was reading first, so a recurring phrase is highlighted where it was
  coded — on a 26-paper corpus this recovered about a quarter of the quotes
  that were previously discarded.
- Literature synthesis: the extractor now separates a paper's own findings
  from findings it attributes to other work (shown on the extraction review,
  not offered to the synthesis) and skips reference lists; the citation
  guard recognises names in any script, ignores stopwords from filename
  labels, and requires the year to match.
- Reports now carry the configuration the run was frozen with, the models
  that answered, and a per-checkpoint summary of decisions; the audit trail
  exports as JSON from the run screen. A run freezes its provider, model,
  and setup answers at start, so a resumed or branched run keeps its model.
- Thematic analysis defines and names themes before the theme review, so the
  names in the report are the ones you approved. Framework analysis charts a
  promoted emergent code across the sources before the matrix. Content
  analysis samples the opening, middle, and end of each source for the
  codebook, reports rates per 10,000 characters beside counts, and names the
  unit it counts. A confidence the model did not give is recorded as missing,
  not as 0.8. Findings narratives pass a quote guard.
- Grouping of very large code sets runs in chunks and consolidates, instead
  of failing on the output limit. The coder is shown up to 300 codes for
  reuse (was 120).
- `QUALILENS_DATA_DIR` moves projects, uploads, and keys out of the app
  folder; the app warns at startup and in Settings when the data folder sits
  inside a cloud-synced directory. The write-ahead log is folded into the
  database at stage boundaries and checkpoints.
- Text ingestion no longer guesses UTF-16 without a byte-order mark, reads
  Word tables in document order with text boxes, refuses `.rtf`, and
  converts `.aac` for transcription when ffmpeg is present.
- `package.sh` rebuilds the interface when its sources have changed (a
  fingerprint is stamped into the build and checked at startup and in the
  packaging test) and rebuilds the manual as part of packaging. Release
  1.4.0 had shipped an interface built before its latest sources.

## 1.4.0 — 2026-08-31

- After a successful update, Settings shows a full-screen confirmation page
  instead of a small notice that was easy to miss.
- The launcher (`run.sh`) now checks disk space, verifies Node 18+, shows
  npm output during first-time setup, and detects a port already in use.
- The QualiLens chevron logo now appears in the app's navigation bar.
- Bug fixes and internal improvements.

## 1.3.0 — 2026-08-30

- The launcher checks disk space and Node 18+, shows npm output on first run,
  and detects a port already in use. Chevron logo. Manual updates; the
  release ZIP needs only Python. (Entry reconstructed from the working log;
  1.1 and 1.2 were never published.)

## 1.0.0 — 2026-08-27

Initial public release.

- Five analysis methods, each a staged pipeline with researcher checkpoints:
  grounded theory, reflexive thematic analysis, qualitative content analysis,
  framework/deductive coding, and corpus-grounded literature synthesis.
- Researcher-led by construction: runs pause at review checkpoints; your
  edits are final and are not overwritten by later automated stages;
  decisions are written to an audit trail the report reproduces.
- Provenance-first evidence: verbatim quotes with character offsets, a
  coded-source reader that draws the coding over each document in place, and
  page anchors for PDF sources.
- Literature synthesis cites only from the uploaded corpus — never from
  memory. Synthesis support must reference located extraction quotes by id;
  ungrounded support is dropped and logged, and a citation guard scans the
  generated text for citation-shaped strings matching no uploaded paper.
- Interactive report plus a formatted Word export, with method-appropriate
  figures that disclose truncation on their face — the grounded theory model
  drawn as a left-to-right paradigm flow.
- Any review a run has passed can be revisited: a branch carries everything
  up to that review into a new run and reopens it, leaving the original run
  and its report untouched.
- Four providers (Anthropic, OpenAI, Google, Mistral), an editable model
  catalog with a live model check, Whisper transcription for audio and
  video, cost estimation before a run, resumable runs that do not re-bill
  finished work, and honored cancellation.
- The app runs locally; data go only to the provider you chose. In-place
  updates from a downloaded bundle or, pull-only and on demand, from this
  repository's releases — the updater's allowlist leaves your projects,
  keys, and uploads untouched.
- A fifteen-plus-chapter user manual, shipped in the app.
