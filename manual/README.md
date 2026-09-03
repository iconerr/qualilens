<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# QualiLens User Manual

Ashita Aggarwal and Suraj Commuri

QualiLens runs analysis of qualitative data locally on your computer. Your transcripts, your API keys, and the database of everything the analysis produces stay on your computer. The only traffic that leaves your computer goes directly to the AI model provider you select. There is no intermediary server, no account, and no upload of your data to anywhere except the AI provider you have selected and whose key you have supplied.

This manual documents the screens, controls, and the drop-down options, and for each option it explains what the option changes inside the analysis and the underlying principles across each choice.

Make sure you are comfortable with the choices you select because qualitative method is a set of commitments about how meaning is made from data, so your selections are consequential. For example, a drop-down that switches between Straussian and Glaserian axial coding is switching between two commitments. The manual covers these alternatives to orient you to the choices.

## A key principle

QualiLens does not run an analysis end to end without stopping. Every method pauses at review checkpoints where you, the researcher, can rename, merge, delete, or add codes before the pipeline continues. Your decisions at those checkpoints will be written to an audit trail that the final report reproduces. A name or definition you set by hand is final, and later automated stages will not overwrite it.

The software's checkpoints will help your project become researcher-led if you exercise these options. A run approved without reading is an unreviewed machine coding wearing the costume of a reviewed one, and the audit trail will faithfully record that you approved it.

## How to read this manual

If you are setting the app up for the first time, read [Getting Started](01-getting-started.md), then follow [The Walkthrough](15-walkthrough.md), which takes one dataset end to end through thematic analysis.

If the app is already running and you want to start an analysis, read [Choosing a Method](03-choosing-a-method.md), then the file for the method you chose, then [The Wizard](02-the-wizard.md) as you work through the five steps.

If a run has finished and you want to know whether to trust it, read [The Coded-Source Reader](10-coded-source-reader.md), which is where the coding is checked against the documents it came from.

If a run has stopped and you need to know what to do, go to [Runs, Cancellation, and Recovery](11-runs-and-recovery.md) or [Troubleshooting](13-troubleshooting.md).

If you are writing the methods section of a paper based on a QualiLens analysis, read the final section of [Reports](12-reports.md) together with [Data, Privacy, and Governance](14-data-and-privacy.md).

## Contents

| Chapter | What it covers |
|---|---|
| [1. Getting Started](01-getting-started.md) | Prerequisites, first launch, API keys, ffmpeg, where files live on disk |
| [2. The Wizard, Step by Step](02-the-wizard.md) | The five wizard steps, every control, what each Continue button actually does |
| [3. Choosing a Method](03-choosing-a-method.md) | The five methods compared, what each one produces, how to choose |
| [4. Grounded Theory](04-grounded-theory.md) | Grounded theory setup options, stages, checkpoints, output |
| [5. Thematic Analysis](05-thematic-analysis.md) | Thematic analysis setup options, stages, checkpoints, output |
| [6. Content Analysis](06-content-analysis.md) | Content analysis setup options, codebook handling, group comparison |
| [7. Framework and Deductive Coding](07-framework-analysis.md) | Framework and deductive coding, emergent candidates, the matrix |
| [8. Literature Synthesis](08-literature-synthesis.md) | Literature synthesis over uploaded papers, the extraction table, corpus-only citation |
| [9. Checkpoints](09-checkpoints.md) | The review panels, searching and sorting a long code list, bulk merges |
| [10. The Coded-Source Reader](10-coded-source-reader.md) | Reading a transcript with its coding drawn over it, and auditing what was missed |
| [11. Runs, Cancellation, and Recovery](11-runs-and-recovery.md) | Run states, progress, the audit log, resume against cancel, cost of each |
| [12. Reports](12-reports.md) | The interactive report, frequency tables, the matrices, Word export, reporting |
| [13. Troubleshooting](13-troubleshooting.md) | Every failure the app can show you and what to do about it |
| [14. Data, Privacy, and Governance](14-data-and-privacy.md) | What leaves the machine, what Delete deletes, what to tell an IRB |
| [15. A Worked Analysis, End to End](15-walkthrough.md) | One dataset taken end to end, with the decisions made at each checkpoint |
| [16. Glossary and Status Reference](16-glossary.md) | The app's vocabulary, and the status badges you will see |

## What QualiLens will not do for you

The model produces a first pass over your data and a set of proposals about how that pass hangs together. It does not produce a finished analysis, and the manual says so in several places because the point is easy to lose once a plausible report appears on screen. Three limits are worth carrying with you from the start.

The coding is one coder's work, and that coder is a language model whose judgments vary between runs. QualiLens models no intercoder reliability, so a claim about agreement between coders is a claim this tool cannot support.

Audio and video transcripts carry no speaker labels, because the transcription service does not diarize. If who said something matters to your analysis, prepare formatted transcripts yourself and upload those as text.

Every located quote in the report is checkable against its position in the source, and you should check a sample of them; a quote that could not be located is marked unverified rather than quoted. The provenance chain exists so that verification is cheap, and cheap verification is worth performing rather than assuming. [The Coded-Source Reader](10-coded-source-reader.md) is where that check happens, and it shows you something no other screen does, which is the stretches of each transcript the coder passed over in silence.

## License and citation

QualiLens and this manual are copyright 2026 [Ashita Aggarwal](https://in.linkedin.com/in/drashita) and Suraj Commuri, released under the Apache License 2.0. The analyses you produce with the application are yours alone, and the authors claim no rights over any output of the tool. [Getting Started](01-getting-started.md#license-and-how-to-cite-qualilens) carries the terms and the citation.
