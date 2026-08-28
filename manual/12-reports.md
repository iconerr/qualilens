<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 12. Reports

The Run screen shows a green card offering **Open report** and **Download .docx** when a run completes. Your report is generated once, at the end of the run, and stored with that run. Opening it later shows you exactly what was produced then.

## The interactive report

The report opens with the title, a line linking back to the run and naming the provider, the AI model, and the time of generation, and a Download button.

### Sources

The first section lists every source as a button carrying its filename and the number of excerpts drawn from it. Press one to open that document in [the coded-source reader](10-coded-source-reader.md), where the coding is drawn over the text in place.

Glance at those counts before you read a word of the narrative. A source contributing three excerpts where its neighbors contributed forty is one of three things. It is a short document, a document about something else, or a document the AI coder failed on. The reader will tell you which.

### Narrative sections

Four of the methods produce the same four narrative sections. They are written from your final analytic structure by a call instructed to ground every claim in the coded structure, and never to invent quotes or findings.

| Section | Contents |
|---|---|
| Overview of Findings | Two to three paragraphs across the whole analysis |
| Findings by Theme | One substantive paragraph per top-level theme or category, in order |
| Integration | How the themes relate, in one or two paragraphs |
| Limitations of This Analysis | One paragraph on the limitations of this coding for this dataset |

Literature synthesis writes its own four instead — Overview of the Corpus, Synthesis by Concept, Convergence and Divergence, and Limitations of This Synthesis — under the further instruction to cite papers only by their corpus labels, with the citation guard described in [that method's chapter](08-literature-synthesis.md) run over the result.

Three methods prepend sections of their own. Grounded theory opens with **The Grounded Theory**, carrying the core category, its definition, and the storyline as you approved it. **Theoretical Sampling Recommendations** follows when the selective coding stage named places where your data are thin. Content analysis opens with **Code Frequencies**, carrying the totals in prose. Literature synthesis opens with **The Corpus**, listing every synthesized paper with its citation line and naming any papers you excluded.

The narrative is generated text. Read it as a draft. It is grounded in the structure you approved, and it is not a findings section you can publish unedited.

### The figure

Each method draws the one figure its tradition expects. It appears in the interactive report and again in the Word export, where it is captioned as Figure 1.

| Method | Figure | What it shows |
|---|---|---|
| Grounded theory | The grounded theory model | A left-to-right paradigm flow: antecedent categories, then the core category, then strategies and consequences |
| Thematic analysis | Thematic map | Each theme with its constituent codes beneath it, excerpt counts in parentheses |
| Content analysis | Code frequency chart | A horizontal bar per code, above the frequency table; segments stacked by group when group comparison is on |
| Framework | Matrix heatmap | Sources by codes above the matrix, each populated cell carrying its count, shaded by intensity |
| Literature synthesis | Concept-by-paper heatmap | Papers by concepts above the matrix, each populated cell carrying its count of supporting passages |

The figure is drawn from the structure you approved at the checkpoints, so it changes when your decisions change. Rename a category and the box is renamed. Merge two themes and the map has one hub fewer.

The grounded theory model reads left to right, the way theory models are conventionally drawn: categories whose relationship to the core names a condition, a context, or a constitutive dimension sit on the left with arrows into the core; categories whose relationship names a strategy or a consequence sit on the right, with arrows leading out of it. The placement is decided by the wording of each relationship, and the wording itself is printed inside the category's box, verbatim — so even if a relationship's phrasing lands a box on an arguable side, the figure never says more than selective coding said. Three rules protect you further. First, a relationship is printed only when selective coding related that category **to the core itself**; a relationship between two categories is real analysis, but attaching it to the core would assert a claim you never approved, so it stays in the narrative. Second, a category with no core-directed relationship is drawn on the left with an unlabeled arrow and no relation line. Third, when you accepted an existing category as the core rather than a higher-order concept, it is drawn once, at the center, and not again among the categories.

Figures are views, not inventories. The model shows at most ten categories, chosen by the weight of their evidence. The thematic map shows at most six themes and eight codes per theme. The chart shows the fifteen most frequent codes, and either heatmap at most twenty sources or papers by twelve codes or concepts. Every figure that truncates says so on its face, and the tables and evidence section beneath remain complete. Read the figure for shape, and the tables for the record.

A figure that cannot be drawn is dropped rather than guessed at, and everything else in the report is unaffected. A report without its figure is a report whose figure failed, not a report missing findings.

Treat the figure as you treat the narrative. It is a faithful rendering of the approved structure, and it is publishable only after the verification described at the end of this chapter, because a clean diagram of an unreviewed coding is still an unreviewed coding.

### The frequency table

Content analysis reports carry a table sorted from the most to the least frequent code.

| Column | What it counts |
|---|---|
| Code | The codebook entry |
| Count | Coded passages, across the whole corpus |
| % | That code's share of all assignments |
| Sources | The number of distinct sources containing the code at least once |
| One column per group | Raw counts within each group, when group comparison is on |

Read the Sources column when you want prevalence, and the Count column when you want intensity. The percentage is a share of assignments rather than a share of participants. The group columns are raw counts, and you must normalize them by group size before you compare them.

### The framework matrix

Framework reports carry a scrollable table whose rows are sources and whose columns are framework codes, including any emergent codes you promoted. Each populated cell holds a one-to-two-sentence summary of what that source said under that code, with the number of underlying passages in parentheses. An empty cell shows a dash.

### The concept-by-paper matrix

Literature synthesis reports carry the same construction with papers for rows and concepts for columns. Each populated cell states what that paper contributes to that concept, summarized strictly from that paper's extraction quotes, with the count of supporting passages in parentheses. A note beneath names any papers excluded from the synthesis. [Reading the matrix](08-literature-synthesis.md#reading-the-concept-by-paper-matrix) is covered in the method's own chapter.

### Evidence

The evidence section is your provenance chain. It is the part of the report that carries the analysis rather than describing it.

Each top-level item appears as a collapsible card showing its name, its definition, and a count of every excerpt beneath it, including those on its child codes. Expanding the card reveals the excerpts attached directly to the item, then each child code with its own name, definition, and excerpts. Grounded theory shows categories with their open codes. Thematic analysis shows themes with their initial codes. Content analysis and framework analysis show a flat list of codebook codes, because neither method has a grouping level, and literature synthesis shows a flat list of concepts with their supporting quotes for the same reason.

Each excerpt shows the verbatim quote, the memo where the method records one, the source filename — with the page number, for a PDF ingested since page anchoring was added — the confidence percentage where the method records one, and a **view in coded document** link.

Six excerpts show at first. **Show all** reveals the rest.

| Method | Memo on excerpts | Confidence on excerpts |
|---|---|---|
| Grounded theory | Yes | No |
| Thematic analysis | Yes | No |
| Content analysis | No | Yes |
| Framework | Yes | Yes, except on promoted emergent codes |
| Literature synthesis | Yes — the point the synthesis recorded for the quote | No |

### View in coded document

The **view in coded document** link opens that source in [the coded-source reader](10-coded-source-reader.md), at the excerpt, briefly highlighted, with every other coded passage in the document shaded around it. Reading a quote inside its own paragraph, with its neighbors visible, is the check that makes your analysis auditable. Perform it on a sample of excerpts under every theme before you write anything from the report.

The highlight is placed by locating the quote in the source. QualiLens tries an exact match first. It then tries a match that treats typographic quotation marks, dashes, and whitespace as equivalent, because AI models routinely normalize those characters when echoing a passage. The opening of the quote is located instead when neither match succeeds, and the highlight then covers less than the full quote. A highlight noticeably shorter than the quote you are reading is therefore a partial match rather than a truncated source, and the passage is still there.

The reader says so when a quote cannot be located at all, and lists that excerpt under **Not located in the text** instead. Such excerpts still count as evidence in your report. Give them your attention, because a quote absent from its source is a quote the AI model did not copy verbatim, which the coding instructions forbid.

### Appendices

**Source Summaries** appears in grounded theory and thematic analysis reports only. It carries the familiarization summary and analytic memo for each source.

**Extraction Table** appears in literature synthesis reports only. It preserves the per-paper extraction exactly as you approved it, excluded papers included and marked.

**Audit Trail** appears in every report. It records the number of logged events, every checkpoint with its resolved status, and the total model usage in calls and tokens. The sources analyzed are listed at the head of the report rather than here.

## The Word export

**Download .docx** builds a formatted document from the same payload. The document is set in Georgia at eleven points. It carries a title block, the data sources with their group labels, the narrative sections, the method's figure with its caption, the frequency table or the matrix where applicable, the full evidence listing, the familiarization appendix, and the audit appendix.

Three differences from the on-screen report are worth knowing before you send the file to a coauthor.

Excerpts are capped at twelve per code, with a note recording how many further excerpts remain in the project database. The on-screen report shows all of them.

The framework matrix is rendered source by source rather than as a grid, listing each source as a heading with its populated cells beneath, and the concept-by-paper matrix is rendered paper by paper in the same way. A table wide enough to hold a full framework does not survive a page break.

The frequency table carries the code, the count, the percentage, and the group columns. It omits the Sources column that appears on screen.

The file is named after your project.

## Reporting a QualiLens analysis

Your analysis may be going into a paper, a thesis, or a report to a sponsor. These are the facts your reader needs, and the places to find them.

**From the wizard and the project page.** The method, which is on the project page. Every setup answer exactly as recorded, which is the Configuration table on the project page. Reproduce those answers verbatim, because the option text carries the methodological commitment. The provider and AI model, which are in the report header.

**From the report's audit appendix.** The number of sources. The number of checkpoints, and the fact that a researcher resolved each one. The total model usage, if you are reporting cost or compute.

**From your own record.** What you actually did at each checkpoint. The audit appendix records that checkpoints were resolved, and the underlying event log records each individual edit. Neither records why you made the decisions, and that is yours to supply. Keep a short note as you work through each checkpoint. It costs little, and it is the difference between an auditable analysis and one that merely logs.

**From the verification you performed.** How many excerpts you checked against their sources, and in how many documents, and what you found. Whether you also read the uncoded stretches, which [the coded-source reader](10-coded-source-reader.md) makes visible, and what that showed. How many excerpts the reader could not locate in their sources. These are the claims that distinguish a reviewed machine coding from an unreviewed one, and QualiLens cannot make them for you, because the reader records nothing.

**The limitations that apply to every QualiLens analysis.** A single AI model performed the coding, rather than multiple human coders, and no intercoder reliability was computed. Coding is not deterministic, so a second run over the same data with the same settings will differ. Transcripts produced automatically carry no speaker labels. Recordings above the transcription service's size limit were split on a fixed time boundary, which can garble a word at each seam. The method-specific limits are listed at the foot of each method chapter in this manual.
