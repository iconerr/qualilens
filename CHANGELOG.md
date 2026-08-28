<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to QualiLens. Release tags are semantic versions; each
release also carries a build stamp (`build YYYY.MM.DD-HHMM`) that the in-app
update check compares against your installation.

## 1.0.0 — 2026-08-27

Initial public release.

- Five analysis methods, each a staged pipeline with researcher checkpoints:
  grounded theory, reflexive thematic analysis, qualitative content analysis,
  framework/deductive coding, and corpus-grounded literature synthesis.
- Researcher-led by construction: runs pause at review checkpoints; your
  edits are final and are never overwritten by later automated stages; every
  decision is written to an audit trail the report reproduces.
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
  video, cost estimation before a run, resumable runs that never re-bill
  finished work, and honored cancellation.
- Everything runs locally; data goes only to the provider you chose. In-place
  updates from a downloaded bundle or, pull-only and on demand, from this
  repository's releases — your projects, keys, and uploads are untouchable
  by the updater's allowlist.
- A fifteen-plus-chapter user manual, shipped in the app.
