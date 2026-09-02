<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 5. Thematic Analysis

Thematic analysis in QualiLens follows the six phases of thematic analysis as Braun and Clarke set them out, in the reflexive tradition. The pipeline familiarizes itself with each source, codes systematically across the corpus, and constructs candidate themes from the codes. It then reviews those candidates against sample extracts, defines and names what survives, and stops. You review twice, once after initial coding and once after the themes have been criticized, defined, and named — so the names and definitions you approve are the ones the report carries.

A word on the name. Braun and Clarke's *reflexive* thematic analysis treats themes as the analyst's construction, made through their engagement with the data, and sets itself against approaches that treat themes as things a procedure finds. A pipeline in which a language model proposes the candidate themes is in tension with that, and a reviewer versed in the tradition may say so. QualiLens does not claim to perform the reflexive part. It performs the procedural moves of the six phases and hands you every structural decision at the checkpoints; the reflexivity — your position, your reading, your reasons for what you kept and cut — remains yours to supply and to write up. Describe the method in a paper as thematic analysis following Braun and Clarke's six phases with LLM-generated candidate codes and themes, reviewed and revised by the researcher at recorded checkpoints, rather than as reflexive thematic analysis without qualification.

## Setup options

### Research question

This field is required and accepts multiple lines. QualiLens passes it into every stage, and it does more work in this method than in any other, because the AI coder is instructed to code every segment relevant to your research question. A vague question therefore produces a diffuse code set, and a sharp question produces a focused one.

`What matters to patients about being kept informed during a long admission` will produce codes about information and its absence. `Patient experience of hospitalization` will produce codes about everything, and your first checkpoint will be long.

### Coding orientation

| Option | What the coder is told |
|---|---|
| `Inductive (data-driven)` | Work inductively, deriving codes from the data rather than from prior theory. |
| `Deductive (theory-driven)` | Work deductively through the theoretical lens supplied in the next field, with the lens text inserted verbatim into the instruction. |

The default is inductive.

**How to choose.** Inductive coding treats the data as the source of the analytic vocabulary. Choose it when you are describing a phenomenon whose relevant dimensions you do not yet want to fix. Deductive coding reads the data through a stated theoretical structure. Choose it when you are asking whether and how a known set of constructs appears in this corpus, or when your contribution is an extension of an existing framework into a new setting.

The distinction is about where the codes come from, not about rigor. Neither orientation is the safer option, and both are routinely published. What a reviewer will look for is that the orientation you declare matches the analysis you present. A paper that claims inductive coding and then reports the constructs of a named theory invites the objection that the theory was imposed rather than found.

**One trap.** Select deductive and leave the theoretical lens blank, and the instruction sent to the coder reads `Work deductively through this theoretical lens: (none provided)`. That is a deductive framing with nothing to be deductive about. The run will complete, the codes will look plausible, and you will have neither a clean inductive pass nor a genuine deductive one. Fill the lens, or set the orientation back to inductive.

### Level of meaning

| Option | What the coder is told |
|---|---|
| `Semantic (explicit, surface meanings)` | Code at the semantic level, capturing the explicit surface meanings of what is said. |
| `Latent (underlying ideas and assumptions)` | Code at the latent level, capturing the underlying ideas, assumptions, and conceptualizations beneath the surface of what is said. |

The default is semantic.

**How to choose.** Semantic coding stays with what your participants said, and anyone can check its codes against the transcript. Latent coding interprets what the saying presupposes. Its codes cannot be checked in that way, because two careful readers may reasonably differ about what an utterance assumes.

Choose semantic when your argument rests on the content of accounts, when your audience will want to verify the coding against the data, or when this is a first analysis of an unfamiliar corpus. Choose latent when your argument is about what the accounts take for granted, about the ideological or discursive work the accounts perform, or about a pattern that no participant would name in those terms.

You bear the cost of latent coding at the checkpoints. Interpretive codes vary more between runs, and they require more of your own judgment to accept or reject. Budget more time for the first review, and expect to rewrite more definitions by hand.

QualiLens applies one level to the whole run. Reflexive thematic analysis as practiced allows a corpus to be read at both levels, and this software does not. Run two projects and integrate them yourself if your analysis needs both.

### Theoretical lens

This multi-line field carries the theory or framework and its key constructs. QualiLens inserts it into the coding instruction when the orientation is deductive.

The field is **ignored entirely when the orientation is inductive**. The text you type is still stored in your project configuration and still appears in the configuration table on the project page, but it never reaches the AI model. Nothing warns you about this at the time, so check the orientation before you assume your lens is in play.

Write the lens as constructs rather than as a citation. `Self-determination theory, specifically autonomy as volitional endorsement of one's actions, competence as the felt capacity to produce desired outcomes, and relatedness as a sense of connection with others` gives the coder something to work with. `Self-determination theory (Deci and Ryan)` does not. The AI model must then supply the constructs from its own knowledge, and you have lost control of the very thing that makes your analysis deductive.

### Where these options land

Orientation and level shape the initial coding call and nothing else. Theme construction, the phase-four review, and the phase-five naming all run under the same instructions regardless of what you chose. The commitment you make here is therefore a commitment about how your data are coded, rather than about how the themes are built from the codes.

## What each stage does

### Familiarization

Each source is read once. The reading produces a faithful summary, an analytic memo naming tensions and surprises, and a short list of notable features. The memo is injected into the coding prompt for that source, and the summaries appear as an appendix in your report.

Familiarization reads the first sixty thousand characters of each source. The memo for a long transcript therefore reflects the opening rather than the whole. Coding itself covers the source in full.

### Initial coding

Each source is split into segments of twenty-four thousand characters at paragraph boundaries, and each segment is coded in one call. The AI coder is instructed to code systematically across the entire extract, giving a code to every segment relevant to your research question. Each code is a concise label capturing one analytically interesting feature of the data. The orientation and level instructions are appended.

Every excerpt is copied verbatim and carries a one-sentence memo explaining the fit. Codes are reused across sources by exact name match, and the coder is shown the codes already in use, capped at three hundred. Above that cap, later segments no longer see the earliest codes, near-duplicates appear, and the audit log says so. That is what the merge control at your first checkpoint is for.

### Review initial codes

The pipeline stops. Every code appears with its excerpt count. You can search and sort the list, select codes and merge them in batches, rename, redefine, delete, or add. Clicking a code opens all of its evidence beside the list, and each excerpt links into [the coded-source reader](10-coded-source-reader.md) at its place in the transcript. See [Checkpoints](09-checkpoints.md).

### Constructing themes

One call receives every surviving code with its definition, its excerpt count, and up to two sample quotes, and returns candidate themes (above one hundred and twenty codes, the grouping runs in chunks and a second call consolidates the result). The instruction is explicit about what a theme is, which is a pattern of shared meaning organized around a central concept. It is equally explicit about what a theme is not, which is a topic summary, a data domain, or an interview question. The AI model is told to prefer fewer and richer themes over many thin ones, and to build each theme from codes drawn from more than one part of your dataset where possible.

Every code must land in exactly one theme, and codes that fit nowhere are placed in a theme named `Uncategorized`.

### Reviewing themes against data

This stage is phase four. It is the AI model criticizing its own themes, and it is a much smaller thing than Braun and Clarke's phase four, which re-reads the whole dataset against the candidate themes. Here the model receives, for each candidate theme, up to sixteen sample extracts drawn from that theme's codes, each cut to one hundred and sixty characters. It judges internal coherence, asking whether the extracts form a meaningful pattern around one central concept. It judges external distinctness, asking whether the theme is clearly separate from the others. It returns a rating of strong, adequate, or weak on each, a recommendation of keep, revise, merge, split, or discard, and a specific critique. It is instructed to be willing to be critical.

Nothing is acted on automatically. The critique is stored and shown to you at the next checkpoint.

### Defining and naming themes

This stage is phase five, and it runs before your review. The AI model writes a definitive name and a definition of three to four sentences for each theme, stating its central organizing concept, its scope, and its boundaries. The candidate name it replaced is kept, and the review panel shows it beneath the final name so you can see what phase five changed. A theme that already carries a researcher edit — possible when a branch reopens this review — is left exactly as you wrote it.

### Review themes

You see every theme with its final name and definition, its excerpt count, the candidate name phase five started from, and the phase-four critique rendered beneath it, in the form `coherence adequate, distinctness weak — recommends merge`, followed by the model's notes. Clicking a theme opens all of its evidence beside the list, with each excerpt labeled by the initial code it came from, so you can see which of a theme's codes is actually carrying it. What you approve here is what the report carries; nothing renames a theme after this point.

Treat the critique as a second opinion rather than an instruction. The same AI model that built the themes produced it, from a sample of extracts rather than the full evidence. Use it to find the themes worth looking at closely. Do not let it substitute for looking.

**One recommendation you cannot execute.** The checkpoint offers rename, merge, delete, and add. It does not offer split. When the critique recommends splitting a theme, you have two options. You can leave the theme whole and split it in your own writing. Or you can delete it, which orphans its codes and sweeps them with their evidence into an `Uncategorized` block in the report. A code you add by hand carries no excerpts and cannot be given any, so you cannot build the two halves manually. Deleting a theme in order to split it usually costs more than it gains.

### Report

The narrative is generated from the final structure and assembled into your report. Quotations in the narrative are checked against the coded excerpts and the sources; any that match neither are named in the Limitations section as unverified.

## What the report contains

Themes in the evidence tree are the themes, and their children are the initial codes. Each excerpt carries its memo and a link that opens the source with the quoted span highlighted; an excerpt whose quote could not be located is marked unverified rather than quoted. Excerpts carry no confidence score in this method, because the coder was not asked to rate its own fit. The report opens with the configuration the run was frozen with, the familiarization summaries appear as an appendix, and the audit appendix summarizes each checkpoint's decisions; the complete record exports from the run screen.

## Limits to state plainly in a methods section

Reflexivity is yours to supply. The pipeline performs the procedural moves of the six phases with a language model generating the candidates. Reflexive thematic analysis also asks for an account of the analyst's position and its bearing on the reading, and no automated stage produces that. Say plainly that candidate codes and themes were model-generated and researcher-reviewed.

The coder is one AI model. No intercoder reliability is modeled, and a second run over the same data with the same settings will not reproduce the first exactly.

The phase-four critique comes from the same AI model that produced the themes, and from a sample of the extracts. Treat it as an internal consistency check rather than an independent review.
