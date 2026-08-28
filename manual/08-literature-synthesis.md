<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 8. Literature Synthesis

Literature synthesis in QualiLens reviews a corpus you supply. You upload the papers, the pipeline extracts a structured summary from each one — aims, method, sample, findings, limitations — and stops so you can correct that table. It then synthesizes concepts across the papers, stops again so you can review them, and builds a matrix whose rows are papers and whose columns are concepts. The matrix is the output that distinguishes this method. It lets you read one paper across every concept, or one concept across every paper.

One principle governs this method, and it is not negotiable: **the AI model never cites from memory — only from the uploaded corpus.** This is enforced in the machinery, not requested in a prompt. The synthesis stage may support a concept only by pointing at extraction quotes by their internal identifiers, and only quotes that were located verbatim in their papers qualify: a quote the extractor paraphrased cannot ground a concept, a reference to an identifier that does not exist is dropped and logged, and a concept left with no surviving support is refused outright. The narrative is instructed to cite papers only by the labels read off the papers themselves, and the finished narrative — together with the concept definitions, the matrix summaries, and the excerpt memos — is scanned for citation-shaped text that matches no uploaded paper; anything found is flagged in the report's limitations section and in the audit trail. Verbatim quoting itself is instructed rather than provable, which is why the location check exists: a quote that cannot be found in its paper is listed as unlocated, shown to you at the extraction review, and barred from the synthesis. A hallucinated reference is therefore not a risk you manage by vigilance. It is a shape the pipeline cannot output silently.

What this method is not: it does not search for papers, it does not judge whether your corpus covers the field, and it does not know any literature beyond what you gave it. The corpus is the world. A synthesis over six papers is a synthesis of those six papers, and the quality of the review is bounded by the quality of your selection — which remains, deliberately, your work.

## Setup options

### Review question

This field is required and accepts multiple lines. It reaches the extraction stage, where it tells the AI extractor what the summaries are for, and the synthesis stage, where it directs which patterns matter. It also reaches the report narrative. A synthesis question ("What does this literature say about X, and where does it disagree?") serves better than a topic label.

### Synthesis focus

| Option | What the synthesis emphasizes |
|---|---|
| `Findings — what the papers found` | What the papers report, where they converge, and where they contradict each other. |
| `Methods — how the studies were designed` | How the studies were designed and sampled, which approaches dominate, and what remains untried. |

**How to choose.** Choose Findings when you are writing the substantive review section of a paper or proposal. Choose Methods when your review's contribution is a map of how the field studies the phenomenon — before a methods chapter, or when arguing that an approach is missing. All five fields are extracted either way; the focus changes which extraction material leads the synthesis prompt, not what is collected.

### Scope note

Optional, multiple lines. State what the corpus is meant to cover — inclusion criteria, period, setting. It reaches the extraction and synthesis prompts as context. Leave it blank if the review question says it all.

## What each stage does

### Extract from each paper

Each paper is split into segments of twenty-four thousand characters at paragraph boundaries, and each segment is read in one call. The AI extractor returns, for each of the five fields, brief notes plus verbatim quotes supporting them, and the paper's own bibliographic line when the segment shows one. The quotes become the evidence you will see everywhere else: they are located in the paper by exact position, so the coded-source reader can highlight them in place, with the page number when the source is a PDF.

After the last segment of a paper, one consolidation call turns the per-segment notes into that paper's row of the extraction table: two to four sentences per field, "Not reported." where the paper is silent, plus a citation line and a short label of the form `Okafor, 2021`. The label and citation come from the citation notes alone — they are read off the paper, not recalled from anywhere. A paper whose text shows no citation is labeled by its filename. Two papers that arrive at the same label are disambiguated with their filenames, so no two rows of the matrix can collapse into one.

Papers upload like any other source, and the method accepts any text format QualiLens ingests. PDFs are the natural case, and they carry one advantage: at upload, QualiLens records where each PDF page begins and ends in the extracted text, so every quote can be anchored to its page. Word documents and plain text have no pages, and their quotes anchor by position only.

### Review the extraction table

The pipeline stops and shows you one row per paper: the label, the citation line, and the five field summaries, with a count of the located verbatim quotes behind each field. Quotes the extractor paraphrased — ones that cannot be located in the paper — are counted separately on the row, because they never ground the synthesis. This checkpoint is where the synthesis is won or lost, because everything downstream builds on this table.

Open a row to edit any field. A label that would duplicate another paper's label is refused at approval, because the matrix and the narrative cite papers by label. Your edits are final — the synthesis and the narrative build on the table as you approved it, and no later stage overwrites a researcher's words. The **open coded paper** button opens the paper in [the coded-source reader](10-coded-source-reader.md) with every extraction quote highlighted, which is the fastest way to check a summary against its source.

A paper that turns out not to belong — off topic, wrong study type, a duplicate — can be **excluded** here. An excluded paper takes no part in the synthesis, the matrix, or the narrative, but its extraction row is kept in the report's appendix, marked as excluded, so your record shows what you removed and that you removed it deliberately.

**What this checkpoint does not show you.** It shows the consolidated summaries, not the underlying quotes; the quote counts tell you how much evidence stands behind each cell, and the coded paper shows you the quotes themselves. A field reading "Not reported." with a quote count of zero means the extractor found nothing — which is either a paper that genuinely does not report it, or an extraction failure on a poorly rendered PDF. The reader distinguishes the two.

### Cross-paper synthesis

One call over the whole corpus. The prompt lists, per paper, its label, its focus-field summary and limitations, and its located extraction quotes tagged with their internal identifiers — up to fourteen quotes per paper, ordered so the focus field leads; when a paper has more, the audit log records how many were offered, and unlocated quotes are never offered at all. A corpus whose included papers carry no located quotes is refused before the call is spent, because nothing could ground its concepts. The AI model returns concepts — patterns that recur or clash across papers — each with a name, a definition, a rationale, and the list of quote identifiers that support it.

This is where the corpus-grounding principle bites. A supporting identifier that matches no extraction quote is dropped, and the drop is written to the audit log naming the concept that tried it. A concept whose support does not survive this filter is refused entirely. If nothing survives, the stage fails with a message rather than producing an empty or invented synthesis, and Resume retries at no loss.

### Review concepts

The pipeline stops and shows each concept with its definition, its evidence, and the papers that support it. This is the same review surface you know from the other methods: rename, merge, or delete concepts, add your own, and open any excerpt in the coded paper. A concept supported by a single paper deserves your particular attention — the synthesis prompt allows it only when clearly important, and you are the check on whether it earned its place.

### Concept matrix and report

The matrix is built one paper at a time. For each paper, the quotes supporting each concept are gathered and sent in a single call, and the AI model returns one to two sentences per concept stating what that paper contributes, strictly from the passages given. Each cell sends up to ten quotes, each truncated to three hundred characters; the cell's count shows the true number. Cost scales with the number of papers, not papers multiplied by concepts.

The narrative is then written from the corpus listing, the concepts, and the matrix — under instruction to cite only the corpus labels — in four sections: Overview of the Corpus, Synthesis by Concept, Convergence and Divergence, and Limitations of This Synthesis. The report opens with **The Corpus**, listing every synthesized paper with its citation line, and naming any papers you excluded.

The narrative is generated text, and one further guard runs after it is written. Every citation inside every parenthetical carrying a year is checked against the corpus labels — each citation on its own, so a real citation cannot shield a phantom packed beside it in the same parentheses. Anything in the narrative that matches no uploaded paper is listed in the limitations section with an instruction to treat its sentences as ungrounded, and logged in the audit trail. The concept definitions, matrix summaries, and excerpt memos are scanned too, and their hits are reported separately, because a flag there may be a paper's own reference echoed from a quoted passage rather than a memory citation — verify those in the coded paper. The guard catches the classic hallucinated `(Author, 1998)` shape. It is a tripwire, not a proof — read the narrative as a draft, as you would any QualiLens narrative.

## Reading the concept-by-paper matrix

The matrix appears in your report as a heatmap and a scrollable table whose rows are papers and whose columns are concepts. Each populated cell holds the summary and, in parentheses, the number of supporting passages behind it.

Read down a column to see how a concept runs across the corpus — which papers carry it, which are silent. Read across a row to see one paper in the review's terms. An empty cell means no extraction quote from that paper supported that concept. That is a finding when a concept is absent from most of the corpus. It is a prompt to check the extraction when a paper is empty across every concept, because a paper contributing nothing to any concept either does not belong in this review or was poorly extracted, and the coded paper will tell you which.

The heatmap shows at most twenty papers by twelve concepts and says so on its face when it truncates; the table beneath is complete.

## What the report contains

The evidence tree is flat: each concept with its excerpts directly beneath it. Each excerpt carries the verbatim quote, the point the synthesis recorded for it, the paper's filename with the page number when the source is a PDF, and a link that opens the paper with the quoted span highlighted. The extraction quotes themselves remain visible in the coded-source reader, where each paper is painted by field — Aims, Method, Sample, Findings, Limitations — alongside the concept highlights.

The report carries two appendices of its own. **Appendix: Extraction Table** preserves the per-paper extraction exactly as you approved it, including excluded papers, marked. There is no familiarization appendix, because this method's first reading of each source is the extraction itself.

The Word export renders the matrix paper by paper rather than as a grid, and includes the extraction table appendix. Page numbers accompany quotes there too.

## Limits to state plainly in a methods section

The corpus was selected by the researcher, not by the tool. This synthesis makes no claim of systematic coverage; it is a synthesis of the papers supplied, and the search and inclusion decisions that produced them must be reported separately.

Extraction is bounded by what the PDF yields as text. A scanned paper without a text layer is refused at upload, because nothing can be extracted from it; a poorly rendered one extracts little, and its row will say so. The extraction table records what the AI extractor read, as reviewed and corrected by the researcher.

The synthesis call saw up to fourteen extraction quotes per paper, with the full set preserved in the evidence tree and the coded papers. Matrix cells are summaries produced from up to ten passages per cell; the underlying passages are all in the evidence tree.

Every citation in this report traces to an uploaded paper by construction: synthesis support referencing anything outside the located extraction was dropped and logged, and the narrative, concept definitions, matrix summaries, and memos were scanned for citation-shaped text matching no uploaded paper. The scan is a guard against fabricated references, not a validation of the claims made about real ones — checking that a cited passage supports the sentence citing it remains the researcher's verification, performed in the coded-source reader.

The synthesizer is one AI model. A second run over the same corpus with the same settings will not reproduce the first exactly.
