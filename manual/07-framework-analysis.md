<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 7. Framework and Deductive Coding

Framework analysis in QualiLens charts your data against a framework you already hold. The pipeline loads your codebook and works through every source, assigning the single best-fitting code to each relevant passage. It then stops so you can inspect what the AI coder was least sure about, charts any emergent code you promoted across every source, and builds a matrix whose rows are sources and whose columns are codes. The matrix is the output that distinguishes this method. It lets you read one case across every code, or one code across every case.

There is no familiarization stage, and the codebook is never derived. This method assumes you brought the framework with you.

## Setup options

### Research question

This field is required and accepts multiple lines. It reaches the emergent-code instruction, where the AI coder is told to propose a code only when a passage is clearly important to your research question and fits nothing in the framework. It also reaches the report narrative. The charting instruction itself works from the framework and the text.

### Framework or codebook

This field is required and accepts multiple lines. Enter one code per line in the form `Code name: definition`.

```
Referral pathway: Descriptions of how a case moves from first contact to specialist review.
Waiting: Any account of elapsed time between steps, including its effects.
Information handover: What is communicated between services about a case, and what is lost.
Family involvement: The role families are given or take in decisions.
```

The parser strips leading bullets and dashes, splits on the first colon, and treats a line with no colon as a code with a blank definition. The run fails at the first stage if nothing parseable is found, with a message naming the expected format. No model calls are made, so nothing is billed.

Two properties of your framework matter more here than in content analysis. The AI coder is instructed to assign the single best-fitting code to each passage rather than every code that applies. Overlapping definitions therefore force an arbitrary choice rather than a double count, and a passage assigned to the wrong one of two near-identical codes is simply missing from the other. And your framework's codes become the columns of the matrix, so a framework of thirty codes produces a matrix too wide to read. Between eight and fifteen codes usually gives a matrix your reader can use.

### Allow emergent codes?

A Yes or No toggle, defaulting to Yes.

| Option | What the coder is told |
|---|---|
| `Yes` | If a passage is clearly important to the research question but fits no framework code, return it as an emergent candidate with a proposed name and definition, sparingly, and only when the fit failure is genuine. |
| `No` | Do not propose codes outside the framework. |

**How to choose.** Turn the toggle off in three situations. Turn it off when your analysis is a test of the framework rather than a development of it, when your claim is that the data were read strictly through a prior structure, or when you are charting against an instrument whose categories are fixed by someone else. A closed framework produces a cleaner methodological statement and a shorter review.

Turn the toggle on in three other situations. Turn it on when the framework is yours to revise, when you are extending an established framework into a new setting where you expect it to be incomplete, or when the absence of a category would itself be a finding. The emergent candidates then serve as evidence about where your framework fails. That is often the most interesting result a deductive analysis can produce.

**What happens to candidates.** Every candidate is presented to you at the review checkpoint with its proposed name, definition, and sample quotes. Each one carries two buttons. Promoting a candidate moves the code into your framework, where it joins the codebook and keeps its excerpts; a stage that runs after the checkpoint then charts the promoted codes across every segment of every source, so the promoted column in the matrix holds everything that fits the code, not only the passages the model happened to flag while it was still a candidate. Discarding a candidate removes it along with its evidence.

The default is discard. A candidate you neither promote nor discard is discarded when you approve the checkpoint. Nothing is promoted by inattention, and nothing survives inattention either. Promote a candidate at the checkpoint if it looks interesting, because you cannot recover it afterward.

Emergent excerpts carry no confidence score. The AI model proposed the code rather than rating a fit against a given definition. Presenting a number there would be fabrication, so the field is left empty rather than filled with a default. The same rule applies to a framework assignment the model returns without a confidence: it is stored as missing, shown as "no confidence given", and listed for review.

## What each stage does

### Load framework

Your codebook is parsed and stored. This stage makes no model calls.

### Chart sources against framework

Each source is split into segments of twenty-four thousand characters at paragraph boundaries, and each segment is charted in one call against the full framework. For every relevant passage the AI coder returns the single best-fitting framework code, a verbatim quote, a confidence between zero and one, and a one-sentence memo justifying the assignment. Out-of-framework passages come back separately when emergent codes are allowed, with a proposed code name, a definition, and a quote.

Quotes are located in the source, exactly or with tolerance for typography, case, and line-break hyphenation, so your report can highlight them in place. Code names are matched to the framework after normalizing case and surrounding punctuation, and an assignment whose code name matches nothing in the framework is dropped; each drop is written to the audit log with the offending name and the quote, and a summary at the end of the stage says how many. Consider whether a code's name is long or unusual enough to have been paraphrased back by the AI model if that code is empty across every source, and shorten the name.

### Review charting

The pipeline stops and shows you two lists. Either list may be empty.

The **emergent code candidates** list carries each proposed code with its definition, its excerpt count, and its sample quotes, with buttons to promote or discard.

The **low-confidence assignments** list carries the assignments the AI model was least sure of, specifically those with a confidence below sixty percent, and any assignment that came back with no confidence at all, which are listed first as "no confidence given". They are ordered from least confident upward and capped at the sixty weakest; the panel says how many are below the threshold in total when it shows fewer. Each row shows the code, the confidence, the source, the quote, and the memo, with a checkbox. Ticking a row deletes that assignment.

The panel tells you when neither list has anything in it. That means every assignment was confident and within your framework.

Deleted assignments are written to the audit trail with their quote before they are removed, so your record shows what you rejected as well as what you kept.

**What this checkpoint does not show you.** It shows the weakest sixty assignments and the out-of-framework proposals. It does not show the confident assignments, which are the overwhelming majority of the coding, and it offers no way to browse them. Approving this checkpoint means you accept the confident assignments unread. Know that now rather than discovering it later.

### Chart promoted codes

This stage runs only when you promoted at least one emergent candidate. Each promoted code is applied to every segment of every source in one call per segment, with the same coding rules as the charting stage. Passages the emergent pass had already attached are not duplicated. The stage is resumable per segment, and the audit log records how many codes were charted.

Check those assignments after the run in [the coded-source reader](10-coded-source-reader.md), which is reachable from every source listed at the head of your report. Charting is the method where the reader matters most, because a framework applied to a transcript leaves visible gaps. Those gaps are either passages your framework has no language for, or passages the coder skipped. The reader is the only screen that distinguishes the two.

### Framework matrix and report

The matrix is built one source at a time. For each source, the passages assigned to each code are gathered and sent in a single call. The AI model returns a summary of one to two sentences per code, stating what that source said under that code, strictly from the passages supplied and with no interpretation beyond them. Cells with no passages are left empty rather than summarized.

Each cell sends up to ten quotes per code, each truncated to three hundred characters. A source that returned twenty passages under one code is therefore summarized from the first ten. The cell's count shows the true number, so a cell reading `(17)` was summarized from ten of those seventeen.

Batching by source rather than by cell has two effects. Your cost scales with the number of sources rather than with sources multiplied by codes. And the matrix row for a long interview is one call, however wide your framework is.

## Reading the matrix

The matrix appears in your report as a scrollable table whose rows are sources and whose columns are codes. Each cell holds the summary and, in parentheses, the number of passages behind it.

Read down a column to see how a single construct was spoken about across cases. Read across a row to see one case in your framework's terms. An empty cell means the source said nothing that the coder assigned to that code. That is a finding when a code is empty across most sources. It is a warning when a code is empty across all of them, because the second usually means your definition failed rather than that the phenomenon was absent.

The exported Word document renders the matrix source by source rather than as a grid, listing each source as a heading with its non-empty cells beneath. A wide table does not survive a page break.

A column for a promoted code was filled by the stage described above, so it is comparable with the others.

## What the report contains

The evidence tree is flat. It lists each framework code with its excerpts directly beneath it, including any codes you promoted from the emergent candidates. Each excerpt carries its memo, its confidence percentage where the model gave one, and a link that opens the source with the quoted span highlighted; an excerpt whose quote could not be located is marked unverified rather than quoted.

There is no source summaries appendix and no frequency table, because this method has no familiarization stage and does not count.

## Limits to state plainly in a methods section

Each passage received one code, so this analysis produces no evidence about co-occurrence between framework codes.

The matrix cells are summaries produced from up to ten passages per cell. All the underlying passages are preserved in the evidence tree, and that is where you should send a reader who wants to check a cell.

The review checkpoint examined out-of-framework proposals and the sixty least confident assignments. Assignments above the confidence threshold were accepted without individual review, unless you checked them in the reader afterward. Say which of those two you did.

The coder is one AI model. No intercoder reliability is modeled, and a second run over the same data with the same settings will not reproduce the first exactly.
