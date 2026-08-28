<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 6. Content Analysis

Content analysis in QualiLens fixes a codebook, applies it to every source, and counts. The pipeline either derives the codebook from your data or loads the one you supply. It then stops once so you can tighten the codebook, codes the whole corpus against it, and produces a frequency table you can cross-tabulate by group. This is the shortest and cheapest of the five pipelines. It is also the only one whose output is numeric.

There is no familiarization stage. The AI model never reads a source whole before coding it.

## Setup options

### Research question

This field is required and accepts multiple lines. QualiLens passes it into the codebook derivation and the report narrative. It does not reach the coding calls in deductive mode, where the AI coder sees only the codebook and the text. In that mode your question shapes the write-up rather than the coding.

### Codebook

| Option | What happens |
|---|---|
| `Inductive — derive the codebook from the data` | One call reads a sample of each source and proposes a codebook of eight to twenty codes, each with a name, a definition, inclusion criteria, and one verbatim example from the data. |
| `Deductive — I will supply the codebook` | The codebook you type in the next field is parsed and used exactly as written. |

The default is inductive.

**How to choose.** Deductive is the stronger position whenever you have a codebook you can defend. A codebook drawn from prior literature, from a pilot, or from a published instrument carries an argument for its categories that a derived codebook does not. Choose inductive when no such codebook exists for your setting, or when the point of your study is to establish what categories the material contains.

**What inductive derivation actually reads.** The derivation call does not read your corpus. It reads a sample taken from the beginning of each source. The size of that sample shrinks as your corpus grows, because a fixed budget of roughly forty-five thousand characters is divided across the sources, with a floor of two thousand characters each.

| Number of sources | Characters sampled from each | Total sampled |
|---|---|---|
| 1 | 45,000 | 45,000 |
| 5 | 9,000 | 45,000 |
| 10 | 4,500 | 45,000 |
| 20 | 2,250 | 45,000 |
| 30 | 2,000 | 60,000 |

Two consequences follow. A category that appears only in the later part of long interviews may never be sampled, and so may never enter your codebook. Coding is instructed to use only the codes provided, so that category will then be invisible in your counts. And the sample is taken from the opening of each file, so an interview that begins with demographic questions spends its sample on them.

Read the derived codebook at the checkpoint against your own reading of the material if you run inductively over long sources, and add what is missing. That is exactly what the checkpoint is for.

### Codebook text

This multi-line field takes one code per line in the form `Code name: definition`.

```
Access barriers: Statements describing difficulty reaching, entering, or using a service.
Cost concerns: References to price, affordability, insurance, or out-of-pocket burden.
Trust in providers: Expressions of confidence or doubt about clinicians' competence or motives.
```

The parser is forgiving in specific ways. It strips leading bullets and dashes, so a list pasted from a document works. It splits on the first colon, so a definition may itself contain colons. A line with no colon becomes a code with a blank definition. The AI coder will then apply that code on the strength of its name alone, so supply definitions.

The field is **ignored entirely in inductive mode**. The text is still stored and still shows in your configuration table, and it never reaches the AI model. Select deductive mode with nothing parseable in the field, and the run fails at the first stage with a message telling you the expected format. No model calls are made, so nothing is billed.

### Content level

| Option | What it does |
|---|---|
| `Manifest (what is explicitly said)` | The derivation call is told to code at the manifest level, capturing explicit content. |
| `Latent (interpreted underlying meaning)` | The derivation call is told to code at the latent level, capturing interpreted underlying meaning. |

The default is manifest.

**How to choose.** Manifest content analysis counts what is on the page. It produces categories a second reader can apply without interpretation, which is what makes counting meaningful in the first place. Latent content analysis counts interpretations. That is defensible when the construct of interest has no surface marker, and it weakens your claim that the counts are reproducible.

Counting is the point of this method, and your counts are only as sound as the reproducibility of the coding that produced them. Choose manifest unless you have a specific reason to do otherwise.

**Where this option lands, precisely.** In inductive mode it shapes the codebook derivation, and the codebook then carries the level into the coding through its definitions and inclusion criteria. The coding calls themselves are never told which level to work at. In deductive mode the option therefore does no analytic work at all, and its only effect is on the wording of the method description in your report. Your definitions carry the level when you supply your own codebook, and this drop-down is documentation rather than instruction.

### Compare groups?

A Yes or No toggle, defaulting to No.

Setting it to Yes does two things. It reveals a group label field on the Data step, which is the only way to attach labels to your sources. And it makes the report cross-tabulate every code's frequency across those labels, both on screen and in the exported Word document.

**Set this before you upload.** The label field is hidden while the toggle is No, and you cannot add labels to sources afterward. Go back to the setup step and switch the toggle if you have already uploaded. Then return to the Data step, remove the sources, and upload them again in labeled batches.

Sources uploaded without a label are grouped together under `Ungrouped`, which appears as its own column.

## What each stage does

### Build codebook

This stage runs either the derivation call described above, or the parsing of the codebook you supplied. Derived codes carry inclusion criteria and an example drawn from your data. Supplied codes carry whatever definitions you wrote.

### Review codebook

The pipeline stops and shows you every code with its name and definition. You can rename, redefine, merge, delete, or add.

This checkpoint differs from the coding checkpoints in one visible way. No coding has happened yet, so every code shows zero excerpts and the evidence panel has nothing to show. You are reviewing definitions in the abstract, against your own knowledge of the material. This is the one checkpoint where the software can give you no help beyond the definitions themselves.

It is also the most consequential checkpoint in QualiLens, because this codebook is applied verbatim to every source and the AI coder is forbidden to invent anything outside it. Overlapping definitions produce arbitrary assignment. A missing category produces silence rather than an error. A vague definition produces counts that mean nothing. Your coding quality is bounded here.

Three checks are worth making every time. Read each pair of definitions that sound close, ask whether a passage could satisfy both, and then tighten or merge them. Ask what a participant might say that no code would capture, and add a code for it. Ask whether each definition tells a stranger what to include and what to exclude, and rewrite the ones that do not.

### Apply codes

Each source is split into segments of twenty-four thousand characters at paragraph boundaries, and each segment is coded in one call against the full codebook. The AI coder is instructed to use only the codes provided and never to invent new ones. It is told to find every passage that satisfies a code's definition, to assign more than one code to a passage only where the definitions genuinely overlap on it, and to give every assignment a confidence between zero and one.

Every quote is copied verbatim and located in the source. Assignments carry a confidence score and no memo, so your report shows a confidence percentage on each excerpt and no justification.

**Sometimes the AI model names a code that is not in your codebook.** The assignment is then discarded rather than guessed at, and the discard is written to the audit log with the offending name and the quote. A summary event at the end of the stage records how many assignments were dropped, and warns you that the counts may undercount. Check the audit log after a run if your totals look low. A codebook whose names are long or unusual attracts more of these.

### Quantify and report

Counts are assembled per code, sorted from most to least frequent, and expressed as a percentage of all assignments. The number of distinct sources in which each code appears is recorded alongside. Each code's count is broken out by group when group comparison is on.

## Reading the frequency table

The table has one column you must read carefully, and one you must not over-read.

The **Count** column counts coded passages. It does not count participants, and it does not count sources. A single participant who returns to the same concern six times contributes six to that code.

The **%** column is each code's share of all assignments across the whole corpus. It is not prevalence, and it does not tell you what proportion of your participants raised the theme. The **Sources** column is closer to a prevalence measure, because it counts how many distinct sources contain the code at least once. That is usually the figure to report alongside the count.

The group columns carry raw counts rather than proportions when group comparison is on. You cannot compare groups of unequal size by reading across the row. Normalize by group size yourself before you draw any conclusion.

## What the report contains

Your report opens with a **Code Frequencies** section carrying the totals in prose, followed by the narrative sections and then the frequency table. The evidence tree is flat. It lists each codebook code with its excerpts directly beneath it, rather than nesting codes inside themes, because content analysis has no grouping level.

There is no source summaries appendix, because this method has no familiarization stage.

## Limits to state plainly in a methods section

A derived codebook was derived from a sample of each source rather than from the whole corpus. The sampling rule is the one tabulated above.

Counting is of coded passages, and the denominator of the percentage column is the total number of assignments.

The coder is one AI model. No intercoder reliability is modeled, and reproducibility across runs has not been established for your corpus. Run the analysis twice and report the agreement you observe if your argument depends on the counts. That is the closest QualiLens comes to a reliability check.

Passages whose code names failed to match the codebook were dropped. The number dropped is in the audit log. Report it if it is not zero.
