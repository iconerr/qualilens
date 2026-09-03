<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 13. Troubleshooting

Every failure QualiLens can show you is listed here, with its cause and its remedy. The messages are quoted as they appear on your screen.

## Starting the app

| Message | Cause | Remedy |
|---|---|---|
| `QualiLens needs Python 3.11 or newer (none found)` | No Python of version 3.11 or later is on the path | Install one, for example with `brew install python@3.12`, then run the launcher again |
| `The bundled Python environment does not work on this machine/path — rebuilding it…` | The folder was copied from another computer, or renamed or moved on this one. Environments are tied to the path that created them | Nothing. The rebuild is automatic, takes about a minute, and the message is information rather than an error |
| `The pre-built interface is not included (this is normal for a GitHub clone). QualiLens needs Node.js to build it once.` | You cloned the repo from GitHub, which does not include the built interface, and Node is not installed | Install Node 18 or later from nodejs.org, then run the launcher again. This is needed once, not on every launch. If you received the app as a zip bundle, this message should not appear — report it as a bug |
| `Node.js 18 or newer is required` | Node is installed but too old for the dependencies | Upgrade Node from nodejs.org |
| `JavaScript dependency installation failed` | npm install failed, usually because of a network problem or insufficient disk space | Check your internet connection and free disk space, then try the recovery command printed below the error |
| `Frontend build failed` | The interface code did not compile. On a fresh installation this should not happen | Try the recovery command printed below the error. If it persists, open an issue on the GitHub repository |
| `Less than 500 MB of disk space available` | The launcher checks available space before starting | Free some space and try again |
| `Port 8765 is already in use.` | Another process holds the port. The lines that follow say which: a QualiLens server (with the build it is running, when it started, and its process number) or another program | Read the lines below the message. If the running QualiLens is this folder's build, open the address it prints. If it is an older build, or predates build stamps, stop it with the `kill` command printed and run the launcher again. For another program, stop it or start QualiLens on another port with `QUALILENS_PORT=8790 ./run.sh` |

A running server keeps the code it loaded when it started, however the folder changes afterwards. A QualiLens left running in a forgotten Terminal tab therefore keeps serving an old build after an update has landed in the folder, and the browser shows the old app while the folder holds the new one. The port check is the first thing the launcher does, before any environment work, so the report appears at once.

The launcher checks for the built artifacts rather than the folders. A first run that failed part way therefore retries cleanly on the next launch, rather than skipping the step that failed.

A line reading `NOTICE: the data folder … appears to sit inside a cloud-synced directory` is information, not an error: it says the sync service holds your database and keys as well, and points to `QUALILENS_DATA_DIR` in [Getting Started](01-getting-started.md#moving-the-data-folder). A line reading `WARNING: frontend/dist was built from different sources than frontend/src` means the interface on disk is older than its source; run `cd frontend && npm run build` or `./package.sh`.

## The page refuses to talk to the app

| Message | Cause | Remedy |
|---|---|---|
| `Missing or stale session token — reload the QualiLens page` | The app was restarted while this tab stayed open, so the tab carries the previous launch's token; or the request did not come from a page QualiLens served | Normally you never see this: the page reloads itself once to fetch the new token. If the message shows, the reload did not help, which means the app is not running — start it with `./run.sh`, then reload. Staged checkpoint decisions survive a reload |
| The **Update installed** page keeps waiting | The new build has not started yet, or an older copy of the app still holds the port | Start the app with `./run.sh`. If the launcher reports the port in use, stop the server it names and run the launcher again. The page reloads by itself once the new build answers; **Reload now** forces it |
| `QualiLens answers only to 127.0.0.1 or localhost` | The address bar names the machine some other way (its LAN address, a hostname), or something on the machine forwarded the request | Open `http://127.0.0.1:8765` |
| `Cross-site request refused` | A page from another site tried to use the app; or a page served by another program on this computer (a notebook server, a development server, on another port); or a browser extension rewrote the request's origin | Use the app from its own tab at `http://127.0.0.1:8765`; the refusal is the protection working |
| `That bundle is build …, older than the installed build …` | The bundle you chose is a signed QualiLens build, but an earlier one than the build you are running | If you mean to roll back, answer the dialog that asks; the app then installs it. The **Download and install** path never installs an older build |

## Uploading documents

| Message | Cause | Remedy |
|---|---|---|
| `… is larger than the … bound for text/audio/video files; refusing.` | The file exceeds the upload bound for its kind: 200 MB for documents, 2 GB for audio, 8 GB for video | Split the document, or compress or trim the recording, and upload again. Nothing of the refused file is kept |
| `Unsupported file type: .xyz` | The extension is not one of the accepted types | Convert the file. The accepted list is in [The Wizard](02-the-wizard.md#what-you-can-upload) |
| `Could not extract text from <file>` | The file is corrupt, password-protected, or not the format its extension claims | Open it in its own application, save a clean copy, and upload that |
| `<file> contains no extractable text` | Most often a scanned PDF that holds page images and no text layer | Run the file through optical character recognition, or supply the transcript as text |

`RTF is not supported — save the document as .docx or .txt first.` is the refusal for an `.rtf` upload; RTF is markup, and reading it as text would feed control codes to the analysis.

`The upload carries no filename.` means the browser sent the file without a name; save it with a name and upload again.

## Transcribing audio and video

| Message | Cause | Remedy |
|---|---|---|
| `Audio/video transcription requires an OpenAI API key (used for Whisper). Add one in Settings.` | No OpenAI key is saved, whichever provider runs the analysis | Save an OpenAI key in Settings, then press Retry on the source |
| `ffmpeg is required to extract audio from video files.` | A video was uploaded and ffmpeg is not installed | Install ffmpeg, then Retry. Settings shows whether the app can see it |
| `This audio file exceeds the transcription API's size limit and ffmpeg is not available to split it.` | The recording is over roughly 24 MB and cannot be chunked | Install ffmpeg and Retry, or compress the audio yourself before uploading |
| `The transcription service does not accept .aac files and ffmpeg is not available to convert it.` | An `.aac` recording needs re-encoding first | Install ffmpeg and Retry, or convert the recording to `.mp3` or `.m4a` and upload that |
| `ffmpeg failed` | ffmpeg rejected the file, usually a corrupt or unusual container | Re-export the recording to `.mp3` or `.mp4` and upload again |
| `Transcription failed for <file>: API error 401` | The OpenAI key is invalid or the account cannot reach the transcription service | Test the key in Settings, replace it, then Retry |
| `Transcription failed for <file>: API error 429` | Rate limited, after the app had already retried several times with increasing delays | Wait, then Retry. If it persists, transcribe fewer files at once |
| `Transcription returned no text.` | The recording is silent, or the audio track is empty | Check the file plays. If it does, re-export the audio and upload again |
| `Transcription was interrupted by an app restart. Retry it.` | The server stopped while the recording was being transcribed | Press Retry |

Retry appears only on failed audio and video sources. A document that failed extraction was rejected at upload and never became a row. There is therefore nothing to retry, and you upload a corrected file instead.

Two messages may meet you if you press Retry at the wrong moment. `Transcription is already in progress for this source` means the transcription is running, and you should wait. `Only failed audio/video transcriptions can be retried` means the underlying file is gone, or the source is a document.

## Configuring a project

| Message | Cause | Remedy |
|---|---|---|
| `Project name is required` | The name field is empty | Name the project |
| `Missing required setting: <label>` | A required setup question was left blank | Fill the named field |
| `Choose an analysis provider` | No provider was selected | Select one on the Model and keys step |
| `Method cannot be changed once runs exist — create a new project.` | You went back and changed the method after a run had been created | Create a new project for the other method |
| `A run is in progress — wait for it or cancel it before editing the project configuration.` | A run is executing or waiting at a checkpoint | Finish or cancel the run first |
| `A run is in progress for this project — cancel it or wait before deleting sources.` | You tried to remove a source under a live run | Finish or cancel the run first |
| `A run is in progress for this project — wait for it or cancel it before adding sources.` | You tried to upload under a live run; a source added now would skip the stages that already ran | Finish or cancel the run first |
| `N completed run(s) cite this source. Deleting it would strip their evidence…` | The source is evidence in a finished analysis | Delete the project to remove everything; or, if you accept losing that evidence, repeat the request with `?force=true` |

## Starting a run

| Message | Cause | Remedy |
|---|---|---|
| `No ready sources — upload data (and wait for transcription) first.` | Every source is missing, still transcribing, or errored | Upload data, or fix the errored sources |
| `N source(s) are still transcribing.` | Recordings are still being processed | Wait, or remove them deliberately. Starting now would exclude them silently, which is why the app refuses |
| `Run is already executing.` | Resume was pressed on a run whose thread is alive | Wait |
| `Run is <status>; only failed/interrupted runs resume.` | Resume was pressed on a completed or cancelled run | A cancelled run cannot be resumed. Start a new run |

## Checkpoints

| Message | Cause | Remedy |
|---|---|---|
| `Checkpoint already resolved` | The same checkpoint was submitted twice, from a double click or a second tab | Nothing. The first submission was applied, and the run has moved on. Reload the page |
| `Run is <status>; nothing awaits review.` | The run is no longer waiting, usually because it was resolved elsewhere or cancelled | Reload the page |
| `Applying checkpoint '<title>' failed; checkpoint reopened` | Something went wrong while applying your decisions | Submit again. Decisions already applied re-apply harmlessly |
| `Decision refers to code <id>, which is not part of this run.` | A stale tab or a hand-built request named a code from another run | Reload the checkpoint and submit again |
| `Merge target '<name>' is no longer active; choose a kept code.` | The code you chose to merge into was merged or deleted at an earlier review | Pick a code that is still kept |
| `Cannot merge '<a>' (<kind>) into '<b>' (<kind>): different kinds of code.` | An open code was aimed at a theme or category, or the reverse | Merge like into like |
| `Two papers would share the label '<label>' — give each paper its own label.` | Two extraction rows would cite by the same label | Edit one of the labels |
| `Every paper is excluded — re-include at least one paper before approving, or cancel the run.` | The extraction review excluded every paper | Re-include one, or cancel |
| `Only review checkpoints can be revisited.` / `The run never reached this review.` / `The run is waiting at this review right now — open it instead of branching.` | Revisit was asked for a stage that is not a passed review | Choose a review the run has passed |

## Model and provider errors

These appear as a failed run, with the error printed on the Run screen. You can resume all of them, and resuming skips the work already completed.

| Message | Cause | Remedy |
|---|---|---|
| `No API key configured for provider '<x>'.` | The key was removed after the project was created | Save a key in Settings, then Resume |
| `HTTP 401` | The key is invalid, revoked, or belongs to a different provider | Test the key in Settings, replace it, then Resume |
| `HTTP 403` or a message about model access | Your account cannot reach the selected model | Choose a different model. The model is fixed for the project, so this means a new project |
| `<provider> did not accept the model id '<m>' — the provider may have retired or renamed it` | The provider no longer serves that model id | Press **Check models** in Settings to see which catalog models are still live, then start a new project with a current model, or type a custom model id in the wizard |
| `HTTP 429` | Rate limited, after the app had already retried up to five times with increasing delays and honored the provider's own retry hint | Wait and Resume. On a large corpus, a cheaper or less contended model finishes more reliably |
| `HTTP 402` or a message about credit | The account has no funds | Add credit, then Resume |
| `Network error` or `Exhausted retries` | The connection dropped, or the provider was unreachable throughout the retries | Check connectivity and Resume |

### Errors about the shape of the response

These are QualiLens refusing output it cannot trust, rather than the provider failing.

`<provider>/<model> returned no text (stop reason: ...)` means the AI model produced nothing visible. On a model that reasons internally before answering, this usually means the token budget was consumed by that reasoning. Resume once. The model is a poor fit for this corpus if the error recurs, and a new project with a different model is the remedy.

`<provider>/<model> output was truncated at the token limit; refusing to parse a partial JSON response` means the response was cut off mid-structure. QualiLens refuses to repair it, because repairing a truncated analysis response would invent codes and quotes the model never produced. Resume, because the failure is often transient. The stage is producing more output than the budget allows if the error recurs at the same stage. That happens on unusually dense sources and on very large code sets, and the practical fix is to reduce the corpus or split it across projects.

`<provider>/<model> returned N chars of malformed JSON — too large to repair` means the response was complete but not valid JSON, and too long to repair safely. Resume the run.

`JSON repair was itself truncated; giving up` means the repair call also failed. Resume the run.

`Gemini returned no candidates (block reason: ...)` means a safety filter blocked the response. Qualitative data about health, violence, or abuse can trigger this. Resume once. A different provider is the practical remedy if the same segment blocks repeatedly.

### Errors from the analysis stages

| Message | Cause | Remedy |
|---|---|---|
| `No <stage> codes to group — nothing was coded.` | The coding stage produced nothing, usually because the sources hold no text relevant to the research question, or the research question is mismatched to the data | Open a source in the coded-source reader from any earlier run to see what the coder was reading, and check the research question |
| `The model returned no <themes/categories> (response did not follow the requested structure).` | The grouping call answered in an unexpected shape. QualiLens refuses to degrade the analysis into a single uncategorized bucket | Resume. Nothing was lost, and the stage rebuilds |
| `Deductive mode selected but no parseable codebook was supplied.` | Content analysis in deductive mode with an empty or unparseable codebook | The format is one `Code name: definition` per line. This fails before any model call, so nothing was billed |
| `No parseable framework codebook.` | Framework analysis with an empty or unparseable codebook | Same format, and again nothing was billed |
| `Familiarization of <file> returned <type> instead of an object` | The model answered familiarization in the wrong shape | Resume. The stage retries that source and keeps the ones already done |

## Reports

`No report for this run yet` means the run has not reached its final stage. Check the run's status.

## Updating the app

| Message | Cause | Remedy |
|---|---|---|
| `This bundle is not signed (no MANIFEST.sha256 / MANIFEST.sig)…` | The zip was built without the release key, or is a repository download rather than a release | Download the release's `QualiLens.zip`, or ask the sender for a signed bundle |
| `The bundle's signature does not verify against the QualiLens release key…` | The zip was signed with another key, or changed after signing | Do not install it. Download the release again |
| `The bundle contains files not covered by its signature` / `is missing signed files` / `does not match its signed hash` | The zip was altered after signing | Do not install it. Download the release again |
| `N run(s) are executing or awaiting review. Finish or cancel them before you update…` | An update stops the server, and would interrupt the run | Finish or cancel the runs, then update |
| `That file is larger than any QualiLens bundle; refusing.` | The chosen file is not a QualiLens bundle | Choose the release's `QualiLens.zip` |
| `The download was redirected away from GitHub; refusing.` | The release asset resolved to a host that is not GitHub's | Do not install it; check the repository's releases page |

After an update, `Your edited models.json differed from the update's; the outgoing copy was saved to …` tells you where your model-catalog edits went so you can reapply them.

## The coded-source reader

`Source not found in this run's project` means the source was deleted after the run completed. The excerpt and its quoted text remain in your stored report, and the document they came from is gone, so there is nothing to highlight.

`Run not found` means the run was deleted, usually because its whole project was.

A reader may open and show no highlights at all, with the code panel reading that there are no coded spans in this document. That means one of three things. The source may have contributed nothing to this run, which the excerpt count beside it in the report's Sources section will confirm. Every code that touched the source may have been deleted at a checkpoint, because evidence on a deleted code is not shown. Or every quote from the source may have failed to locate, in which case the **Not located in the text** panel carries them, and its heading gives you the count.

## Things that go wrong quietly

Five failures produce no error message. Check for them yourself.

**Near-duplicate codes.** The AI coder is shown the codes already in use so that it can reuse them, and that listing is capped at three hundred codes. The cap is passed only on a very large corpus; when it is, later segments stop seeing the earliest codes, synonyms appear, and the audit log records that the cap was reached. Merge them at your first checkpoint.

**Dropped assignments in content analysis.** The assignment is discarded rather than guessed at when the AI model names a code that does not match your codebook. The audit log records each drop, along with a summary at the end of the stage warning that your counts may undercount. Read the audit log if your totals look low. Short, distinctive code names attract fewer drops than long ones.

**Dropped assignments in framework analysis.** The same mismatch occurs in framework charting, and each drop is now logged with the name the model used and the quote, with a summary at the end of the stage. A framework code that is empty across every source is the symptom, and a shorter code name is usually the cure.

**Short highlights in the coded document.** The opening of a quote is located instead when the quote cannot be matched exactly or after normalizing typography, and the highlight then covers less than the quote. The passage is present, and the highlight is partial.

**Excerpts that never reach the document.** A quote that cannot be located at all is a different matter. It means the AI model did not copy the passage verbatim, which the coding instructions forbid. Those excerpts are gathered under **Not located in the text** in the reader, its heading gives you the count for that document, and the report marks each of them *not located verbatim* instead of quoting it. A handful is ordinary. A long list means the coder is paraphrasing. Check any quotation you intend to publish from that document against the transcript by hand before you print it.

**Familiarization that read the opening only.** A source longer than sixty thousand characters is summarized from its first sixty thousand, and the audit log says so for each such source. Coding covers the whole source; the memo that primes it does not.

**Guard notes in the narrative.** A Limitations section that ends with `Citation guard:` or `Quote guard:` is the report telling you that generated prose contained a citation or a quotation matching nothing in the corpus. Treat the sentences named as unverified.

## When nothing here fits

The audit log on the Run screen records every stage boundary, every model call with its purpose, and every error with the tail of its traceback. Read it from the bottom up. The last entries before a failure usually name the source and the segment that caused it. The complete event history is in the database, and it outlives your browser session.
