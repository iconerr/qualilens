<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 10. The Coded-Source Reader

The reader displays one of your documents with every coded passage highlighted in the place where it sits in the text. This is the screen you use to audit the coding. It answers a question the report cannot answer, which is what the coding caught, what the coding missed, and where in the document each of those happened.

The report tells you what the AI coder found. The reader shows you the document the AI coder was reading. The difference should be important to you because the reader makes the blank stretches between the highlights visible. No other screen in QualiLens shows you those blank stretches, and they are often the most informative thing in front of you.

## How to open it

There are three routes into the reader. Two of them take you to a particular passage.

| From | How | Where it lands |
|---|---|---|
| The report's **Sources** section | A button per source, carrying that source's excerpt count | The top of the document |
| Any excerpt in the report | The **view in coded document** link | At that excerpt, briefly highlighted |
| The evidence panel at a checkpoint | The **open in document ↗** link | At that excerpt, in a new browser tab |

The link from a checkpoint opens a new tab, so that a review in progress is not lost when you navigate away. Your checkpoint decisions are held either way.

## What is on the screen

The line under the filename reports four things, and a fifth for a PDF. It gives you a link back to the run, the number of coded spans in this document, the number of codes appearing in this document, the percentage of the text that falls inside at least one coded span, and — when the source is a PDF with a page map — the page count, taken from the last page that carries text.

Below that line sit three panes. A narrow minimap runs down the left. The document fills the center. A panel on the right lists the codes. The minimap and the panel stay in place while you scroll the document.

## The document

Every located excerpt is drawn as a highlight over the exact characters it quotes. The text is split at the boundary where two excerpts overlap. Each stretch is then shaded according to how many codes cover it.

| Shading | Meaning |
|---|---|
| Pale yellow | One code covers this passage |
| Deeper amber | Two or more codes cover this passage |
| Blue with an outline | This passage carries the code you have isolated |
| Grey | A coded passage that does not carry the isolated code |

Hovering over a highlight names the codes on it. Clicking a highlight opens the passage inspector described below.

Pay attention to the deeper amber. Two or more codes on one passage means one of two things. It may mean genuine analytic overlap, which is legitimate and often interesting. Or, it may instead reveal to you that two codes name the same thing and should be merged. The reader cannot tell you which of these you are looking at, but it can show you every instance.

## The code panel

**Codes in this document** lists every code with evidence in this source, ordered by how much evidence each one has here. Each entry carries the code's name, the theme or category it belongs to underneath the name where the method has one, and a count.

The coverage bar and its percentage sit at the head of the panel. Coverage is the share of characters lying inside at least one coded span. Treat coverage as a description and not as a score. A very high figure usually means the AI coder labeled nearly everything, which makes the codes less discriminating rather than more thorough. A very low figure means either that the document has little bearing on your research question, or that your question is narrow enough to exclude most of what the participant said. Both are findings about your analysis. Neither is a number to move up or down.

### Isolating a code

Click any code to isolate it. The passages carrying that code turn blue, every other coded passage fades to grey, and the view jumps to the first instance.

Three controls appear while a code is isolated.

| Control | What it does |
|---|---|
| **‹ prev** and **next ›** | Step to the previous or next passage carrying this code, in document order, wrapping around at the ends |
| The counter | Your position in that code's passages, for instance `4/11` |
| **Show all** | Clears the isolation and restores every highlight |

Clicking the isolated code a second time also clears it.

Step through a code from its first passage to its last. This check puts every piece of evidence for one code in front of you, in the order the participant said it. A code that holds together across eleven passages is a code you can defend. A code whose eleven passages turn out to be four different things is a code to split in your writing, or a code you should have caught at the checkpoint.

### The count, and the question mark

The number beside each code is the number of that code's excerpts located in this text. Some excerpts cannot be located. The count is then followed by the number that could not be located, marked with a question mark, as in `7 +2?`.

Clicking a code whose located count is zero will not isolate anything, because there is nothing to show. The reader tells you so and points you to the list described next.

## The passage inspector

Clicking a highlighted passage opens **This passage** in the right-hand column. It lists every code covering that exact stretch of text. For each code it gives you the code name, the parent theme or category, the page number when the source is a PDF with a page map, the AI model's confidence where the method records one, and the coder's one-sentence memo where the method records one.

Which of these appear depends on the method you chose. Grounded theory and thematic analysis record memos and no confidence. Content analysis records confidence and no memo. Framework analysis records both, except on codes promoted from emergent candidates, which carry no confidence. Literature synthesis records memos and no confidence, and paints each paper twice over — once by extraction field, once by concept. The table in [Reports](12-reports.md#evidence) sets this out.

Close the inspector with its Close button, or click another passage to replace it.

## Excerpts that could not be located

Sometimes the AI model returns a quote that does not appear verbatim in the source. That quote cannot be drawn over the text. Those excerpts are collected in a panel headed **Not located in the text**.

Each entry shows the beginning of the quote and the code it belongs to. These excerpts still count as evidence in the report. They appear in the evidence tree and in the Word export exactly like any other excerpt. What they lack is a position in the document, so you cannot check them in place.

The coding instructions require quotes to be copied verbatim. This list therefore measures how far the AI model departed from that instruction on this document. A handful of entries is ordinary, because a model will occasionally normalize a dash or drop a stray character. A long list is a warning, because it means the coder is paraphrasing. Do not print a paraphrased quote as a quotation. Find the sentence in the transcript first and quote what the participant actually said.

## What the reader does not show

The reader shows one run's coding of one document. Three exclusions follow from that.

Evidence attached to a code you deleted at a checkpoint does not appear, because that code is no longer part of the analysis. Evidence from a code you merged does appear, under the code it was merged into, because a merge moves the evidence rather than discarding it.

Coding from other runs does not appear. A project with three runs over the same source holds three different sets of coded spans. The reader shows you the run you opened it from.

Passages the AI coder never returned do not appear at all. Those passages are the uncoded stretches.

## Using the reader as an audit

Five passes are worth making on any document your argument will rest on. Together they take a few minutes.

Read the uncoded stretches first, before you read any highlight. Scroll the document looking only at what is unmarked, and ask yourself whether anything there should have been coded. No other screen in QualiLens supports this check, and it is the check that finds what the coder missed.

Look at the minimap for blank bands. A long unmarked stretch in the middle of an interview usually means one of three things. The passage may genuinely bear on nothing. The segment boundary may have fallen awkwardly. The coder may have lost the thread. Jump to the band and see which of the three you are dealing with.

Open a few deep-amber passages and read what the inspector tells you. Two codes on one sentence should be two ideas. When it is one idea wearing two names, you have found a merge.

Isolate your two or three most important codes and step through every passage with the arrows. These are the codes your argument will rest on, so these are the codes to see whole.

Check the length of the Not located list, and read a few of its quotes against the document. If a quote you intend to publish is on that list, find the real sentence in the transcript and quote that instead.

## Reading the minimap

The strip on the left represents the whole document from top to bottom. It carries one mark for every coded span, placed at that span's position in the text and sized by its length. Click a mark to jump to that passage. When a code is isolated, its marks stand out and the rest fade.

The minimap answers a question the scrolling text cannot, which is how the coding is distributed across the document as a whole. Coding often clusters in the opening third of an interview and thins toward the end. Understand that distribution before you treat code frequencies as evidence about what your participants emphasized.

## Recording what you found

The reader logs nothing. Isolating codes, stepping through passages, and reading the Not located list leave no trace in the audit trail, because none of these actions changes the analysis.

The record is therefore yours to keep. When you verify a sample of excerpts, note how many you checked, which documents you checked them in, and what you found. That note is the sentence your methods section needs, and the software cannot write it for you. [Reports](12-reports.md#reporting-a-qualilens-analysis) sets out what else to record.
