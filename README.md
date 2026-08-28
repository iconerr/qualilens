# QualiLens

A local web application for LLM-assisted qualitative data analysis. Everything —
your data, your API keys, the coding database — stays on your computer; the only
network traffic is direct calls to the LLM provider you choose.

## Starting the app

```bash
./run.sh
```

The first run builds the environment (a minute or two); afterwards it starts
instantly. The app opens at http://127.0.0.1:8765. Stop it with Ctrl-C.

## What it does

A five-step wizard walks each analysis:

1. **Method** — choose one of four:
   - **Grounded theory** — open coding → axial coding into categories →
     selective coding around a core category → theory narrative. Straussian or
     Glaserian variant.
   - **Thematic analysis** — Braun & Clarke's six phases, inductive or
     deductive, semantic or latent.
   - **Content analysis** — derive a codebook from the data or supply one,
     code every source against it, get frequencies overall and by group.
   - **Framework / deductive coding** — apply your a priori codebook, review
     emergent candidates and low-confidence assignments, get a framework matrix.
2. **Method setup** — the questions specific to that method (research question,
   coding orientation, codebook, …).
3. **Model & keys** — pick the provider (Anthropic, OpenAI, Google, or Mistral)
   and model; paste and test the API key.
4. **Data** — upload transcripts and documents (.txt, .md, .docx, .pdf) or
   audio/video (.mp3, .m4a, .wav, .mp4, .mov, …). Audio and video are
   transcribed automatically with OpenAI Whisper (requires an OpenAI key even
   if another provider does the analysis; video also requires ffmpeg).
   Note: Whisper does not label speakers — if speaker identity matters,
   upload formatted transcripts instead.
5. **Review & run** — a cost estimate, then the run.

### Checkpoints

The pipeline pauses at review checkpoints — after initial/open coding, after
theme or category construction, at the core category, at the codebook — where
you rename, merge, delete, or add codes before the analysis continues. Every
decision you make is logged, and a name or definition you set by hand is final:
later automated stages never overwrite a researcher's edit. This is what keeps
the analysis *researcher-led*: the model proposes, you dispose.

### Provenance and the audit trail

Every code assignment stores the verbatim quote and its exact character
position in the source. In the report, any excerpt links back to its
highlighted place in the original document. The report's appendix lists every
checkpoint, every researcher edit, and total model usage — the audit trail you
would show a reviewer who asks how a theme was derived.

### Reviewing at scale

The checkpoint screens are built for real studies, not demos: search and sort
the code list (fewest-excerpts-first surfaces merge candidates), multi-select
codes and merge them in one action, and click any code's excerpt count to open
its full evidence — every excerpt, its source, and a link into the coded
document.

### The coded-source reader

Any source can be read with its coded spans highlighted inline: a legend of
codes with counts, click-to-isolate a single code and step span-to-span, a
minimap showing where coding falls (and thins out) across the document, and a
coverage figure. This is the auditing view — what did the coding catch, what
did it miss, and where.

### Reports and visualizations

Interactive in the browser (themes → codes → excerpts → coded document) and
exportable as a formatted Word document (narrative sections, frequency tables
or framework matrix where applicable, full evidence listing, audit appendix).
Each method gets its natural figure, both in the browser and embedded in the
Word export: the **grounded theory model** (categories in labeled relation to
the core category), the **thematic map** (themes with their constituent
codes), a **code-frequency chart** (stacked by group where groups are used),
and a **framework-matrix heatmap**.

### Reliability

Runs execute in the background with per-document progress; you can close the
browser during long stages. A failed run (network error, rate limit) resumes
from where it stopped: long stages record each completed segment, so resuming
skips finished work rather than re-billing it. If the app itself is restarted
mid-run, the run is marked interrupted at startup and offers the same Resume.
Cancelling a run stops it before the next model call — no further spend — and
is final. All projects persist in a local SQLite database
(`backend/data/qualilens.db`).

## Architecture

- `backend/` — Python 3.12 + FastAPI. `app/methods/` holds the four method
  pipelines built on a shared stage/checkpoint framework (`base.py`,
  `common.py`); `app/pipeline.py` is the run manager; `app/llm.py` the
  provider-agnostic LLM client; `app/transcription.py` Whisper + ffmpeg;
  `app/report_docx.py` the Word exporter.
- `frontend/` — React + TypeScript (Vite). Built once; served by the backend.
- `backend/data/` — SQLite database and uploaded files. **This is where your
  analyses live; back it up if the project matters.** Note this folder sits
  inside a Dropbox-synced directory — convenient for backup, but never run
  the app from two machines against the same synced database, and let Dropbox
  finish syncing before starting the app on another machine. The app folds the
  database's write-ahead log at startup and shutdown to keep the at-rest file
  coherent for syncing.

## Honest limitations

- LLM coding is a *first pass with review*, not a replacement for researcher
  judgment; the checkpoints exist to make that review real.
- Whisper transcripts have no speaker diarization, and recordings above the
  API's size limit are split on a hard time boundary (a word can be garbled at
  each ~10-minute seam).
- Intercoder reliability (multiple human coders) is not modeled in v1.
- Cost estimates are heuristics; actual spend depends on provider pricing.
- Quotes the model fails to echo verbatim are located by a normalized search
  (typographic quotes/dashes folded); when only a partial match is found, the
  "view in source" highlight may span less than the full quote.

## Keeping the model list current

Providers retire models. The catalog the wizard offers lives in
`backend/app/models.json` — a data file, edited without touching code — and
**Settings → Check models** verifies it against each provider's live model
list using your key (free). The wizard also accepts any custom model id, so
a stale catalog never blocks an analysis. Maintenance procedure: `devnotes/MAINTENANCE.md` (authors' working notes —
present in the development folder, deliberately not in shared bundles; the
essentials are in `models.json`'s own `_readme`).

## The manual

A full user manual lives in `manual/` (fifteen chapters, built into a single
`manual.html` by `manual/build_manual.py`). It is available from inside the
running app — the **Manual** link in the top bar, or http://127.0.0.1:8765/manual.html —
and ships in the shareable bundle, both as the served page and as source.

## Sharing QualiLens with colleagues

```bash
./package.sh
```

This writes a clean `QualiLens.zip` to your Desktop containing everything a
recipient needs — including the pre-built interface, so they need neither
Node nor npm — and **nothing personal**. The bundle is built from an explicit
manifest of application files, so your Python environment, database, API
keys, uploaded data, and anything else you keep in this folder (manuals,
memos, transcripts) are excluded by construction. Recipients need only Python
3.11+; they unzip and run `./run.sh`.

Never share the project folder directly: `backend/data/` holds your API keys
and participant data. If a folder is copied anyway, `run.sh` detects a Python
environment built on another machine and rebuilds it automatically.

## Running the tests

```bash
cd backend && .venv/bin/python -m pytest tests/test_fixes.py -q && .venv/bin/python tests/e2e_grounded_theory.py && .venv/bin/python tests/e2e_methods.py
```

All tests run against scratch databases with a mocked model — no API keys or
spend involved, and your real project database is never touched.

## License, copyright, and citation

Copyright © 2026 **Ashita Aggarwal and Suraj Commuri**.

QualiLens is free software, released under the [Apache License 2.0](LICENSE):
use it, modify it, and share it — including commercially — provided the
copyright notice and [NOTICE](NOTICE) file travel with any redistribution.
Every source file carries an SPDX copyright header, so attribution survives
even when a single file is copied out of the project.

The analyses, codebooks, and reports you produce *with* QualiLens are yours
alone; the authors claim no rights over any output of the tool.

If QualiLens contributes to published research, please cite it (see
[CITATION.cff](CITATION.cff)):

> Aggarwal, A., & Commuri, S. (2026). *QualiLens: A local application for
> LLM-assisted qualitative data analysis* [Computer software].
