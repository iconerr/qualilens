<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 14. Data, Privacy, and Governance

QualiLens runs entirely on your computer. It sends your data to exactly one place, which is the AI model provider you selected. This chapter states precisely what leaves your computer, what stays, what deletion removes, and what an ethics committee will want to know.

## What leaves your computer

Analysis calls carry your data to the provider whose key you supplied, over a direct connection to that provider's API. There is no QualiLens server, no intermediary, no queue, and no relay.

| Stage | What is transmitted |
|---|---|
| Familiarization | The first sixty thousand characters of each source, verbatim (the audit log names each source this cap shortens) |
| Coding, initial coding, applying a codebook, charting, charting promoted codes | Every source in full, verbatim, in segments of twenty-four thousand characters |
| Codebook derivation, in inductive content analysis | A sample of each source — its opening, middle, and end — verbatim |
| Grouping into categories or themes | Code names, definitions, excerpt counts, and up to two sample quotes per code |
| Theme review, selective coding | Names, definitions, and sample quotes |
| Framework matrix | Up to ten quotes per code per source, each truncated to three hundred characters |
| Structured extraction, in literature synthesis | Every paper up to its reference list, verbatim, in segments of twenty-four thousand characters, then the per-part notes for consolidation |
| Cross-paper synthesis | Extraction summaries and up to fourteen located quotes per paper, each truncated to two hundred forty characters |
| Concept matrix | Up to ten quotes per concept per paper, each truncated to three hundred characters |
| Report narrative | The final structure with names, definitions, counts, and sample quotes |
| Transcription | The recording itself, uploaded to OpenAI's speech-to-text service, as extracted audio for video and in ten-minute chunks for large files |
| Test key | A single trivial message carrying no data of yours |
| Check models | Your API key to its own provider's free list-models endpoint, and nothing else |
| Check for updates | Nothing of yours — one request to GitHub asking for the latest QualiLens release, made only when you press the button |

Your research question and every setup answer travel with most calls. Anything identifying that you typed into those fields therefore travels too.

Your API key is sent to its own provider as an authorization header, and to nobody else.

The sampling settings each call ran with — the temperature where QualiLens sets one, and the token budget — are recorded on the call's audit entry, because they differ by provider: Anthropic's models and OpenAI's reasoning models run at the provider's default temperature, the others at the value recorded.

One thing you should know about what travels: the text of your sources is placed inside the prompt as data. Every prompt tells the model that the text between the fences is data and never an instruction, and no stage acts on anything the model says outside the JSON it is asked for. A document that contains instruction-like text — most plausibly a paper downloaded from the web in a literature synthesis — could still influence how the model reads it. Nothing in QualiLens can be made to act by such text; what it can do is colour an extraction, which the extraction review exists to catch.

## What never leaves your computer

The database, the uploaded files, and the analysis itself stay on disk. No usage data, no telemetry, and no analytics are collected, and nothing runs in the background: every row in the table above is a call you initiated. Updates are pull-only — QualiLens never contacts anyone unprompted, and the update check happens only when you press its button.

The server binds to 127.0.0.1, so QualiLens is reachable only from the computer it runs on, and not from your network. The browser on that computer is the remaining route, and it is closed: the server answers only when the request names `127.0.0.1` or `localhost`, refuses any request a browser marks as coming from another site, and requires a per-launch session token on every API call, which only pages QualiLens itself served carry. A web page you have open in another tab cannot read your projects, start a run, or install anything through the app, and neither can a page that has been made to resolve to your own machine. Update bundles must carry a valid signature from the release key before a file is written.

## What the provider does with it

Your agreement with the provider governs that, rather than this software, and the terms differ between providers and between account tiers. Three questions matter. How long does the provider retain your inputs? May it use them to improve its models? Is an enterprise or zero-retention arrangement available to you? Settle all three with the provider before you upload human subjects data. QualiLens cannot answer them for you. Get a data processing agreement from the provider you intend to name if your protocol requires one.

The one thing QualiLens guarantees is that your data go to that provider and to nobody else.

## Where things sit on disk

| Path | Contents | Sensitivity |
|---|---|---|
| `backend/data/qualilens.db` | Every project, the full text of every source, every code, every excerpt with its quote, every checkpoint decision, every logged event, and every report | Holds your raw data in full |
| `backend/data/uploads/` | The original documents and recordings you uploaded | Holds your raw data in full |

`backend/data` is the default; `QUALILENS_DATA_DIR` moves both to a folder of your choosing, and the Settings screen names the folder in use.

Anyone with read access to those two paths has your data. Everything in that table is synced as well if the data folder sits inside a cloud-synced directory — the app says so at startup and in Settings when it detects one. Keep the data folder outside the synced tree if your protocol requires the data to stay on one machine ([Getting Started](01-getting-started.md#moving-the-data-folder)).

## API keys

Your keys are stored as plain text in the `settings` table of the database. They are not encrypted, and they are not held in a system keychain. Anyone who can read the database file can read your keys, and a synced folder syncs them.

Two habits follow. Use **Remove** in Settings before you hand the computer or the folder to anyone. And prefer a key scoped to this work, with its own spending limit, over a key that reaches your whole account.

## What deletion actually deletes

### Removing a source

Removing a source from the Data step or the project page deletes three things. It deletes the source record with its extracted text, every excerpt in every run that pointed at that source, and the original uploaded file on disk.

For that reason a source that a completed run cites is refused unless you insist: deleting it would leave that run's report quoting a document that no longer exists. When you do insist, two things stay behind, and both can hold quoted material from that source. Reports you already generated hold their own stored copy of the analysis, including the quotes. An excerpt from a removed source therefore still appears in an existing report, and its **view in coded document** link then fails, because the document is gone. The event log likewise retains quoted fragments in entries recording dropped or rejected assignments.

### Deleting a project

Deleting a project from the Projects list removes everything. That means every run, every code, every excerpt, every checkpoint and its recorded resolution, every logged event, every stored report, every source with its text, and every uploaded file. The confirmation dialog says the deletion cannot be undone, and it means it.

Use this operation when a participant withdraws and you must remove their data completely. It is the only operation that clears the stored reports and the event log.

### Removing a key

**Remove** in Settings clears the stored value for that provider. It does not touch any project.

### What is retained by design

Codes you delete or merge at a checkpoint are marked as deleted or merged rather than removed. The database therefore retains the analytic history that produced your final structure. Excerpts you reject at the framework checkpoint are written to the audit trail with their quote before they are removed.

This is deliberate. An audit trail that silently loses the evidence you rejected is not an audit trail. It also means the database holds more of your data than your report displays.

## Notes for an ethics application

These are the facts a committee will ask for, stated in the terms committees use.

**Processing location.** Analysis runs locally on the researcher's own computer. No study data are stored on any QualiLens server, because there is none.

**Third-party transfer.** Source text is transmitted to a named commercial AI model provider for analysis, over an encrypted connection, using the researcher's own account. Name the provider you will use. The recording itself is transmitted to OpenAI where audio or video is transcribed. Disclose that as a separate transfer, even when a different provider performs the analysis.

**De-identification.** The software performs none. Whatever is in the transcript is what is transmitted, including names, places, and any other identifier a participant spoke aloud. De-identify before upload if your protocol requires it. Note that upload is the only point at which de-identification can happen.

**Storage and access.** Study data are held in a single database file and an uploads folder in the project directory, unencrypted, protected by the operating system's file permissions. State whether that directory is synced to a cloud service. The study data are held by that service as well if it is.

**Retention and destruction.** Data persist until deleted. Deleting a project removes all of it, including derived analyses, logs, and reports. Removing an individual source leaves quotes in previously generated reports and in the event log. Honor a withdrawal request by deleting the project.

**Automated decision-making.** An AI model produces the coding proposals. The researcher reviews and approves every analytic structure at explicit checkpoints, and each checkpoint is logged. No finding is produced without researcher approval.

**Reproducibility.** AI model coding is not deterministic, and a second run over the same data with the same settings will differ. The audit trail records the model, the provider, the settings frozen at the run's start, the sampling settings of every call, and every researcher decision, and it exports as one JSON file from the run screen. That supports auditability rather than exact reproducibility. State the distinction rather than eliding it.

**Software integrity.** The application updates only from bundles signed by its authors' release key, verified before installation; a local page cannot be reached by other web pages. State this if the committee asks how the analysis software is protected on the researcher's machine.

## A working checklist before you upload human subjects data

Confirm that the provider's data handling terms cover what your protocol promised your participants.

De-identify the transcripts. Upload is the last moment at which you can.

Decide where the data folder lives before the first upload. If the app folder is synced, point `QUALILENS_DATA_DIR` at a folder that is not, or exclude the data folder from sync — before the first upload rather than after.

Use a dedicated API key with a spending limit.

Run one short source end to end first, so that you see what is sent and what comes back before you commit the corpus.
