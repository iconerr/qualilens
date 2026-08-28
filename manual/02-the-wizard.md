<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 2. The Wizard, Step by Step

Every analysis begins at **New analysis** in the top bar, which opens a five-step wizard. The step strip across the top shows you where you are. The **Back** and **Continue** buttons at the foot of the page move you between steps. Continue validates the current step before it advances, and it prints the reason in a red box when it refuses.

The five steps are Method, Method setup, Model and keys, Data, and Review and run.

---

## Step 1. Method

Five cards appear, one per method. Click a card to select it, and the selected card is outlined and tinted. Each card carries the method's name, a one-sentence description, and the full pipeline the method will run, written as a chain of stage labels.

```
Pipeline: Familiarization → Initial coding → Review initial codes → Constructing
themes → Reviewing themes against data → Review themes → Defining & naming
themes → Report
```

Read that chain before you choose. It tells you how many AI model passes the method makes over your data, and where the method will stop for you.

Switching methods is safe. The answers you already typed for the previous method are held aside when you select a different card, and returning to that method restores them. You lose nothing by exploring.

Continue refuses until you select a method. [Choosing a Method](03-choosing-a-method.md) compares the five.

---

## Step 2. Method setup

This screen carries the project name and the questions specific to the method you chose.

**Project name** is required. It appears throughout the app, on the Projects list, at the head of every run, in the report title, and in the filename of the exported Word document. Name your project so that you can tell two runs apart six months from now, for example `Clinician interviews, Spring 2026`.

Below the name are the method's own questions. A question marked with an asterisk is required, and Continue names the first one you left blank. Every question carries a help line beneath it explaining what the question does. The method chapters in this manual explain what each option commits you to.

Four kinds of field appear.

| Field type | Appearance | Notes |
|---|---|---|
| Text | Single-line box | Used for short lists, such as sensitizing concepts |
| Textarea | Multi-line box | Used for research questions and codebooks |
| Select | Drop-down with named options | The option text itself is stored and passed into the analysis, so the wording matters |
| Toggle | Drop-down offering Yes and No | Stored as `true` or `false` |

One consequence of how the drop-downs work is worth knowing. The full option text, for instance `Straussian (axial coding with paradigm model)`, is what gets recorded in your project configuration and what the pipeline reads. The Configuration table on the project page therefore shows you the exact choice you made rather than a code.

Some fields are ignored depending on your other answers. The Theoretical lens field does nothing in inductive thematic analysis, and the Codebook field does nothing in inductive content analysis. The manual flags each of these in the method chapters. The field stays visible in both cases, so switching the other option back restores your text.

---

## Step 3. Model and keys

Three controls sit on this screen. Continue does more work here than on any other step.

**Analysis provider** lists the four providers. A provider with a key already saved is marked `— Ready` in the list.

**Model** lists the models QualiLens offers for that provider, and it defaults to the provider's default model. Choosing a provider resets the model to that default. The model you pick performs every coding, grouping, and narrative call in the run.

**API key** accepts a pasted key. The label tells you when a key is already saved, and you can leave the field blank to keep that key. Anything you type replaces the saved key when you press Continue.

**Test key** sends one short request to the provider using the model you selected. It reports either the model's reply or the provider's error. The test uses whatever is in the key field, and it does not save that key, so trying a doubtful key never damages a working one. A test call costs a fraction of a cent. Run it before a large analysis, because it catches an expired key, an unfunded account, or a model your account cannot reach, before you have spent anything on coding.

### What Continue does here

Pressing Continue on this step performs four actions in order. It saves the API key if you typed one. It assembles your configuration from the setup answers plus the provider and model. It creates the project in the database. It advances you to the Data step.

Two consequences follow. Your project now exists and appears on the Projects list even if you abandon the wizard at the next step, and you can delete it from there. And the project is updated rather than duplicated if you press Back from a later step, change your answers, and press Continue through this step again. The run therefore uses what you last saw rather than the first snapshot.

A note about transcription appears at the foot of this screen. It repeats that audio and video need an OpenAI key regardless of which provider you selected here.

---

## Step 4. Data

Upload your sources here. Drop files onto the upload area, or press it to browse. It accepts multiple files at once, and each file is uploaded and processed as it arrives.

### What you can upload

| Category | Extensions | How QualiLens reads it |
|---|---|---|
| Plain text | `.txt`, `.md`, `.text` | Decoded directly, trying UTF-8, then UTF-16, then Latin-1 |
| Word | `.docx` | Paragraph text is extracted in order, and table rows are flattened into pipe-separated lines |
| PDF | `.pdf` | Text layer is extracted page by page |
| Audio | `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`, `.webm`, `.aac`, `.mpga` | Sent for transcription |
| Video | `.mp4`, `.mov`, `.avi`, `.mkv`, `.mpeg`, `.wmv` | Audio track extracted with ffmpeg, then transcribed |

Three limits on this table are worth knowing before you upload.

PDF extraction reads the text layer and performs no optical character recognition. A scanned PDF that holds page images rather than text therefore yields nothing, and the upload is rejected with a message saying the file contains no extractable text. Run such files through an OCR tool first, or supply the transcript as text.

RTF files are accepted by the uploader, but they are decoded as plain text rather than parsed. Your analysis would then see the RTF control codes along with the words. Convert `.rtf` to `.docx` or `.txt` before you upload.

Any other extension is refused at upload with a message naming the unsupported type.

### The group label field

This field appears only when you are running content analysis and answered Yes to **Compare groups?** in the setup step. It sets the group label applied to the next files you upload. The working pattern is to type `Site A`, upload that site's transcripts, change the field to `Site B`, upload those, and so on. The label appears as a pill next to each filename, and the report cross-tabulates code frequencies by these labels. Sources left without a label are counted together under `Ungrouped`.

Return to the setup step and switch the toggle before you upload if you intend to compare groups. The field is the only way to attach labels, and it is hidden while the toggle is No.

### The source list

Each uploaded file appears as a row carrying its filename, its group label if it has one, its kind, its size in thousands of characters once it is ready, and a status badge.

| Status | Meaning | What to do |
|---|---|---|
| `ready` | The text is extracted or transcribed and the source will be included in the run | Nothing |
| `transcribing` | A recording is being transcribed in the background | Wait. The list refreshes itself every few seconds |
| `error` | Extraction or transcription failed | Press Retry, or Remove the file and investigate |

**Retry** appears only on failed rows, and it works only for audio and video. A document that failed to extract was rejected at upload and never became a row. The commonest cause of a transcription error is a missing OpenAI key. Fix that in Settings and then retry.

**Remove** deletes the source and the uploaded file from disk.

Long recordings take minutes to transcribe. An information box says so while any transcription is running.

### What Continue does here

Continue refuses to advance unless at least one source is ready. It also refuses while any source is still transcribing, because continuing at that moment would silently exclude the unfinished recordings from your analysis. Wait for them, or remove them deliberately.

Continue asks the backend for a cost estimate over the ready sources when it does advance.

---

## Step 5. Review and run

The final screen restates what is about to happen and gives you one button.

The summary line names the project, the method, the provider and model, the number of sources, and the total character count. Below it the estimate box shows an approximate cost, together with the input and output token counts the cost was derived from. Below that, the checkpoints this method will pause at are listed by name, so you know how many times the run will stop for you.

### How the estimate is calculated

The estimate is a heuristic over data volume and default prices. Understand it rather than trusting it.

The character count of all ready sources is converted to tokens at four characters per token. That figure is multiplied by a per-method factor reflecting how many times the method passes over your data. A fixed twenty thousand tokens are added for prompts and grouping calls. Output is assumed to be fifteen percent of input. The result is priced against a built-in table of default rates per million tokens.

| Method | Pass factor |
|---|---|
| Grounded theory | 2.4 |
| Thematic analysis | 2.4 |
| Framework | 1.9 |
| Literature synthesis | 1.7 |
| Content analysis | 1.6 |

| Provider | Input, per million tokens | Output, per million tokens |
|---|---|---|
| Anthropic | $3.00 | $15.00 |
| OpenAI | $2.50 | $10.00 |
| Google | $1.25 | $10.00 |
| Mistral | $2.00 | $6.00 |

Four things the estimate does not know are worth holding in mind. It uses the built-in price table rather than the price your account actually pays, so a discounted or a premium rate will move the real figure. It assumes one pass through the pipeline, so a run you resume after a failure, or a second run over the same project, costs again for the stages that repeat. It does not model reasoning tokens, which several current AI models spend internally and bill as output. And it cannot know how verbose your chosen model will be.

Treat the estimate as an order of magnitude. The Run screen shows you actual token usage as the analysis proceeds, and the report's audit appendix records the final totals, so you can always recover the true cost afterward.

### Run analysis

Pressing **Run analysis** creates the run and takes you to the Run screen, where the pipeline begins immediately. The wizard is finished at that point. Everything that follows is documented in [Runs, Cancellation, and Recovery](11-runs-and-recovery.md) and [Checkpoints](09-checkpoints.md).

---

## Moving backward through the wizard

**Back** returns you one step and clears any error message. Your answers survive, including uploaded files, which stay attached to the project.

One asymmetry deserves your attention. Uploaded sources belong to the project, so the files remain if you go back and change the method after uploading. That is usually what you want. It is not what you want if you switch away from content analysis with group comparison, because the group labels stay stored on the sources while the new method ignores them entirely.

## Editing a project after the wizard

Your project's configuration is fixed once the wizard is finished. The project page shows the configuration as a read-only table, and there is no edit screen. Starting a **New run** from the project page reuses the same method, the same setup answers, the same provider and model, and the same sources, and it begins again from the first stage.

Create a new project to analyze the same data under different settings. The method in particular cannot change once any run exists. QualiLens refuses that change, because it would leave you with a project whose history no longer matches its configuration.
