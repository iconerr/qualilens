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
| `Port 8765 is already in use (is QualiLens already running?)` | Another process holds the port, often an earlier QualiLens you forgot to stop | Open the address the message prints, or start on another port with `QUALILENS_PORT=8790 ./run.sh` |

The launcher checks for the built artifacts rather than the folders. A first run that failed part way therefore retries cleanly on the next launch, rather than skipping the step that failed.

## Uploading documents

| Message | Cause | Remedy |
|---|---|---|
| `Unsupported file type: .xyz` | The extension is not one of the accepted types | Convert the file. The accepted list is in [The Wizard](02-the-wizard.md#what-you-can-upload) |
| `Could not extract text from <file>` | The file is corrupt, password-protected, or not the format its extension claims | Open it in its own application, save a clean copy, and upload that |
| `<file> contains no extractable text` | Most often a scanned PDF that holds page images and no text layer | Run the file through optical character recognition, or supply the transcript as text |

An `.rtf` file uploads without complaint, and it is then read as plain text rather than parsed. Your analysis would see RTF control codes alongside the words. Convert to `.docx` or `.txt` before you upload.

## Transcribing audio and video

| Message | Cause | Remedy |
|---|---|---|
| `Audio/video transcription requires an OpenAI API key (used for Whisper). Add one in Settings.` | No OpenAI key is saved, whichever provider runs the analysis | Save an OpenAI key in Settings, then press Retry on the source |
| `ffmpeg is required to extract audio from video files.` | A video was uploaded and ffmpeg is not installed | Install ffmpeg, then Retry. Settings shows whether the app can see it |
| `This audio file exceeds the transcription API's size limit and ffmpeg is not available to split it.` | The recording is over roughly 24 MB and cannot be chunked | Install ffmpeg and Retry, or compress the audio yourself before uploading |
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

## The coded-source reader

`Source not found in this run's project` means the source was deleted after the run completed. The excerpt and its quoted text remain in your stored report, and the document they came from is gone, so there is nothing to highlight.

`Run not found` means the run was deleted, usually because its whole project was.

A reader may open and show no highlights at all, with the code panel reading that there are no coded spans in this document. That means one of three things. The source may have contributed nothing to this run, which the excerpt count beside it in the report's Sources section will confirm. Every code that touched the source may have been deleted at a checkpoint, because evidence on a deleted code is not shown. Or every quote from the source may have failed to locate, in which case the **Not located in the text** panel carries them, and its heading gives you the count.

## Things that go wrong quietly

Five failures produce no error message. Check for them yourself.

**Near-duplicate codes.** The AI coder is shown the codes already in use so that it can reuse them, and that listing is capped at one hundred and twenty codes. The cap is passed on a large corpus, later segments stop seeing the earliest codes, and synonyms appear. Merge them at your first checkpoint.

**Dropped assignments in content analysis.** The assignment is discarded rather than guessed at when the AI model names a code that does not match your codebook. The audit log records each drop, along with a summary at the end of the stage warning that your counts may undercount. Read the audit log if your totals look low. Short, distinctive code names attract fewer drops than long ones.

**Silently dropped assignments in framework analysis.** The same mismatch occurs in framework charting, and there the assignment is dropped without a log entry. A framework code that is empty across every source is the symptom, and a shorter code name is usually the cure.

**Short highlights in the coded document.** The opening of a quote is located instead when the quote cannot be matched exactly or after normalizing typography, and the highlight then covers less than the quote. The passage is present, and the highlight is partial.

**Excerpts that never reach the document.** A quote that cannot be located at all is a different matter. It means the AI model did not copy the passage verbatim, which the coding instructions forbid. Those excerpts are gathered under **Not located in the text** in the reader, and its heading gives you the count for that document. A handful is ordinary. A long list means the coder is paraphrasing. Check any quotation you intend to publish from that document against the transcript by hand before you print it.

## When nothing here fits

The audit log on the Run screen records every stage boundary, every model call with its purpose, and every error with the tail of its traceback. Read it from the bottom up. The last entries before a failure usually name the source and the segment that caused it. The complete event history is in the database, and it outlives your browser session.
