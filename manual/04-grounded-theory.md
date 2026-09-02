<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 4. Grounded Theory

Grounded theory in QualiLens moves from fractured incidents to a single explanatory core. The pipeline codes every source line by line in spirit. It then groups those codes into conceptual categories, identifies the category with the greatest explanatory power, and writes a storyline that integrates the rest around it. You review the output of each of those three moves before the next one begins.

## Setup options

### Research question or phenomenon of interest

This field is required. It accepts multiple lines, and QualiLens passes it into every stage of the analysis as context.

Grounded theory tolerates a broader opening than the other methods, because the tradition begins from an area of inquiry rather than a fixed hypothesis. `How do community health workers manage competing obligations to clinic protocol and to the families they serve` works. So does the narrower `What do community health workers do when a protocol conflicts with a family's wishes`. The broader statement produces a wider spread of open codes and a longer review at your first checkpoint. The narrower statement produces a tighter set, and it risks closing off the process you were trying to discover.

Write your question as a question about a process rather than about a topic. The AI coder is instructed to code actions, processes, and meanings rather than topics, so a research question phrased as a topic pulls against that instruction.

### Coding paradigm

This drop-down carries two options. It changes exactly one thing, which is the instruction given to the axial coding call. Open coding and selective coding run identically under both options.

| Option | What the axial call is told to do |
|---|---|
| `Straussian (axial coding with paradigm model)` | Group the open codes into conceptual categories, and for each category identify in its rationale where it sits in the paradigm model, specifically causal conditions, context, intervening conditions, action and interaction strategies, and consequences. Categories must be grounded in the codes supplied rather than imported. |
| `Glaserian (emergent, no forced paradigm)` | Group the open codes into emergent conceptual categories, letting the organizing logic emerge from the codes themselves without forcing a coding paradigm or any preconceived framework. |

The default is Straussian.

**How to choose.** This choice is a methodological commitment, and your reviewers will read it as one.

Choose Straussian in three situations. Choose it when you intend to report a paradigm model, when your analytic interest is in conditions and consequences rather than in the bare process, or when your journal expects the tradition of Strauss and Corbin. The practical effect in your report is that each category's rationale states its role in the paradigm. That gives your discussion section a ready-made structure, and it gives a reviewer a visible logic for why the categories were cut where they were.

Choose Glaserian in three other situations. Choose it when your commitment is to emergence and you would rather risk a looser structure than impose one, when the paradigm model's vocabulary of conditions and consequences would distort a phenomenon that is not causal in shape, or when you expect a reviewer to press you on forcing. The practical effect is that the categories are freer to organize around whatever the codes actually share. The rationale field then carries the AI model's own account of that logic rather than a paradigm slot.

State the difference plainly in your methods section. The two options differ in the instruction given at the axial stage, and in nothing else. Run both as separate projects over the same sources and compare the categories if you need the distinction to run deeper than that. Axial coding is a single call, so the comparison is affordable.

### Sensitizing concepts

This optional single-line field accepts a comma-separated list of concepts from prior literature. Anything you enter is appended to the open coding instruction, along with a directive not to force them.

Leave the field blank for a fully emergent first pass. Fill it when you are working in a literature whose constructs you must be able to speak to, and you would rather the AI coder stay alert to them than reconstruct them yourself at the axial stage.

Two cautions apply. Naming a concept raises the chance that the coder finds it, whether or not the concept is there. That is the tension the field's help text acknowledges and cannot resolve, and a blank field is the cleaner methodological position and the easier one to defend. Whatever you enter is recorded in your project configuration and reproduced in the report's configuration table, so your decision stays visible to anyone auditing the analysis.

The field affects open coding only. Axial and selective coding never see it.

## What each stage does

### Familiarization and memos

Every source is read once before any coding. Each reading produces a faithful summary of one hundred and fifty to two hundred and fifty words, an analytic memo of one hundred to two hundred words naming tensions, surprises, and context worth remembering, and a short list of notable features.

The memo is not decorative. It is injected into the coding prompt for that same source, so the AI coder approaches the transcript having already articulated what was strange about it. The summaries appear in your report as an appendix.

One limit applies. Familiarization reads the first sixty thousand characters of each source, which is roughly ten thousand words. The memo for a long transcript therefore reflects the opening rather than the whole. Coding itself has no such limit and covers the source in full.

### Open coding

Each source is split into segments of twenty-four thousand characters at paragraph boundaries, and each segment is coded in one call. The AI coder is instructed to fracture the data into discrete incidents and to label each with a conceptual code. It is told to prefer gerunds such as `managing uncertainty` or `seeking validation`, to use in-vivo codes when a participant's own phrase is analytically striking, and to code actions, processes, and meanings rather than topics. It is told explicitly that this is not the stage for theoretical abstraction.

Every excerpt must be copied verbatim from the source, and each one carries a one-sentence memo explaining why it fits the code. QualiLens locates each quote in the source — exact match first, then a match that tolerates typography, case, and PDF line-break hyphenation, searched first inside the segment the coder was reading so a phrase that recurs is highlighted where it was coded — so that your report can highlight the quote in place. A quote that cannot be found at all is kept but marked unverified, and the report never presents it as a quotation ([Reports](12-reports.md#evidence)).

Codes are reused across sources by exact name match. The coder is shown the codes already in use, with an instruction to reuse those names when the same idea recurs. That listing is capped at three hundred codes. The code count passes that cap only on a very large corpus; when it does, later segments stop seeing the earliest codes, near-duplicates appear, and the audit log says so. It is what the merge control at your first checkpoint exists for.

### Review open codes

The pipeline stops. Every open code appears with its excerpt count. You can search and sort the list, select codes and merge them in batches, rename or redefine any of them, delete them, or add a code of your own. Clicking a code opens all of its evidence beside the list, and each excerpt links into [the coded-source reader](10-coded-source-reader.md) at its place in the transcript. [Checkpoints](09-checkpoints.md) documents every control.

This is the checkpoint that most repays your care, because everything downstream is built from what survives it. Open coding fractures the data deliberately, so this list is long by design. Merge the near-duplicates here. Sorting by fewest excerpts first puts the duplicates in front of you.

### Axial coding

One call receives every surviving open code with its excerpt count, its definition, and up to two sample quotes, and returns a set of categories. Above one hundred and twenty codes the grouping runs in chunks of that size, and a second call consolidates the provisional categories into the final set, so a large study does not fail on the model's output limit. Each category carries a name, a definition of two to three sentences, a rationale for why those codes cohere, and the list of codes it claims. Every code must land in exactly one category, and codes that fit nowhere are placed in a category named `Uncategorized` with a rationale.

Any code the AI model fails to place is swept into `Uncategorized` as well, so no evidence is lost by omission.

### Review categories

You see each category with the total excerpt count carried by its child codes, and you get the same rename, merge, and delete controls. Merging a category moves its child codes to the target, so the evidence follows the merge rather than being stranded.

### Selective coding

One call receives every category with its definition, its child code count, its total excerpts, and its rationale. It returns four things.

It returns the core category, which may be one of the existing categories or a higher-order concept that subsumes them. The core category must be grounded in the categories given. It returns a storyline of one to two paragraphs integrating the categories. It returns a list of relationships, each naming a category, a relation such as condition for or strategy for or consequence of, and an explanation. It returns a list of theoretical gaps, which are the places where your data are thin and theoretical sampling would be needed.

### Review core category

You edit the core category's name, definition, and storyline directly. The proposed relationships are displayed for your information, and you cannot edit them at this checkpoint. The storyline is the spine of the final report, so this is the checkpoint where your own analytic voice enters the report most directly. The audit trail records which of the three fields you changed, and records an unchanged approval as exactly that.

### Theory and report

The narrative is generated from the final structure and assembled into your report. The grounded theory report opens with a section titled **The Grounded Theory**, carrying the core category and the storyline. **Theoretical Sampling Recommendations** follows if any gaps were identified, and then come the standard narrative sections.

## What the report contains

Themes in the evidence tree are the categories, and their children are the open codes. Each excerpt carries its memo and a link that opens the source document with the quoted span highlighted. The familiarization summaries appear as an appendix. The report opens with the configuration the run was frozen with, and its audit appendix summarizes each checkpoint's decisions; the complete record of every edit exports from the run screen.

## Limits to state plainly in a methods section

Theoretical sampling is not performed. QualiLens analyzes the corpus you supply, and the theoretical gaps it names are the nearest it comes to telling you what to collect next. A single pass over a fixed corpus cannot support a claim of theoretical saturation, so do not make that claim on this evidence.

Constant comparison is approximated rather than performed. Codes are compared across sources through name reuse during coding, and through the single grouping call at the axial stage. There is no iterative movement between collection and analysis.

The coder is one AI model, and its judgments vary between runs. No intercoder reliability is modeled. A second run over the same data with the same settings will not reproduce the first exactly.
