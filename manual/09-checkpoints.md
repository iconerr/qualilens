<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 9. Checkpoints

A checkpoint is where the pipeline stops and hands your analysis to you. The run status changes to `awaiting review`, and an amber-bordered panel appears at the top of the Run screen carrying the checkpoint's title and instructions. Nothing further happens, and nothing further is spent, until you press **Approve and continue**.

A run waits indefinitely. Close the browser, come back tomorrow, and the panel is still there. You can also cancel from a checkpoint, which ends the run permanently.

A resolved review is final for its own run, but it is not the end of the road: from the Run screen's pipeline you can revisit any review the run has passed, which branches a new run from that point with everything up to it carried over — including the decisions already made at that review, which further decisions build on rather than undo. [Runs, Cancellation, and Recovery](11-runs-and-recovery.md) explains what carries, what re-runs, and when to branch earlier instead.

Four kinds of panel exist. Which one you see depends on the method and the stage.

| Panel | Appears at |
|---|---|
| Code review | Review of open codes and of categories in grounded theory, review of initial codes and of themes in thematic analysis, review of the codebook in content analysis, review of concepts in literature synthesis |
| Core category review | Review of the core category in grounded theory |
| Charting review | Review of the charting in framework analysis |
| Extraction review | Review of the extraction table in literature synthesis |

---

## The code review panel

A first coding pass over twenty transcripts routinely returns well over a hundred codes. The code review panel gives you four tools for working through that many, which are a search box, four sort orders, multi-select with bulk actions, and an evidence panel that shows a code's entire evidence rather than a sample.

The layout has three parts. A toolbar runs across the top, the code list fills the left, and the evidence panel occupies the right.

### The toolbar

| Control | What it does |
|---|---|
| Search box | Filters the list to codes whose name or definition contains what you type |
| Sort drop-down | Reorders the list. The four orders are described below |
| Counter | Reads `N codes · M shown`, and adds `X to merge` and `Y to delete` once you have staged actions |
| **+ Add a code** | Appends a blank row for a code of your own |

Know the sort orders individually. One of them is a working method rather than a preference.

| Order | Use it to |
|---|---|
| `Most excerpts first` | See the codes carrying the analysis. This is the default |
| `Fewest excerpts first (merge candidates)` | Surface the long tail of one-excerpt and two-excerpt codes, which is where near-duplicates and coding noise collect |
| `Alphabetical` | Bring near-synonyms next to each other when they share a first word |
| `Original order` | Restore the order the coder produced them in |

Sort by fewest excerpts first to clean a code list. The codes at that end are mostly one of two things. They are either duplicates of something already in the list under another name, or single observations that never recurred. Deciding between those two readings is exactly the judgment a checkpoint exists to capture.

### The code list

Each code appears as a row carrying a checkbox, an editable name, an editable definition, an excerpt-count button, and a Delete button.

**The name and the definition** are text boxes, and typing in them edits the code directly. There is no separate edit mode and no save button on the row. Everything is submitted together when you approve the checkpoint.

An edit you make by hand is permanent in a specific sense. The code is flagged as researcher-edited, and later automated stages will not overwrite it. This matters most in thematic analysis. The phase-five naming stage there rewrites the name and definition of every theme you did not touch, and leaves untouched every theme you did. Editing a theme's name at the checkpoint is therefore how you keep your wording in the final report.

Two details govern what counts as an edit. A value you type and then change back to what it was is not a rename, and it does not flag the code. A name you blank out is refused and the previous name is kept, because a code with no name cannot appear in a report. A definition you blank out is honored, because clearing a definition is a decision you might reasonably make.

**The excerpt-count button** reports how many excerpts the code carries. Pressing it opens that code's evidence in the panel on the right. For a grouping code such as a theme or a category, the count includes the excerpts held by its child codes. A theme showing forty-two excerpts is therefore a theme whose codes between them evidence forty-two passages.

Every code shows zero at the content analysis codebook checkpoint, because no coding has happened yet. You are reviewing definitions in the abstract at that checkpoint, against your own knowledge of the material.

### The evidence panel

Clicking a code fills the right-hand panel with the code's name, its definition, and **every one of its excerpts**, not a sample. Each excerpt shows the verbatim quote. Beneath the quote you get the source filename, the AI model's confidence where the method records one, the memo where the method records one, and a link reading **open in document ↗**.

Two of those deserve comment.

For a grouping code, excerpts carried by a child code are labeled `via` with the child code's name. You can therefore see which of a theme's codes each piece of evidence actually came from. The excerpts are ordered by that label first, then by source, then by position in the document.

The **open in document ↗** link opens [the coded-source reader](10-coded-source-reader.md) in a new tab, at that excerpt in its transcript, briefly highlighted. Follow that link to verify a code that only looks plausible. Your decisions are held while you are away, as described below.

### Selecting codes and acting in bulk

The checkbox on each row adds that code to a selection. A bar appears above the list as soon as one code is selected, carrying the count and three actions.

| Action | What it does |
|---|---|
| `merge all into…` plus **Merge** | Stages every selected code to merge into the one you pick from the drop-down |
| **Delete selected** | Stages every selected code for deletion |
| **Clear selection** | Empties the selection without staging anything |

Bulk merging is how you clean a code list. Tick the four codes that all name the same idea, choose the one whose name you prefer as the target, and press Merge. The target must be a code you are keeping. A target you subsequently delete is dropped rather than left stale.

Merging is available only through this bar. There is no per-row merge control, so merging two codes means ticking the one to absorb and choosing the other as the target.

### Delete

**Delete** on a row, or **Delete selected** in the bulk bar, marks a code for removal. The row dims, and its Delete button becomes **Undo delete**.

Deleting does more than it appears to. A code you delete is dropped from the current selection, and it is cleared if it was the chosen merge target. Any merges you had staged *into* it are un-staged, because a delete must never quietly expand into deleting the evidence that other codes were about to be merged into. Those codes return to being kept, and you can re-merge them elsewhere.

For a plain code, deleting removes the code and its evidence from your analysis. For a grouping code, deleting removes the grouping and orphans its child codes. The report then sweeps those orphaned codes into an `Uncategorized` block with their evidence intact rather than losing them. Deleting a theme therefore removes the theme, not the data underneath it.

Delete when a code is an artifact of the coder rather than a feature of your data. Merge when two codes name the same thing. Rename when the code is right and its label is not.

### Undo

A code staged for merge or deletion shows **Undo merge** or **Undo delete**, which returns it to the kept state. A staged merge also prints its target beneath the row, reading `→ merging into "X"`, so the list shows you what you have decided before you commit to it.

Edits and actions are held separately. Undoing a merge therefore restores any rename you made before you merged it, and you lose nothing by changing your mind about the action.

### How merges are resolved

The resolution handles chains and cycles rather than failing on them. Merge A into B and B into C in the same submission, and A's evidence lands on C. Merge A into B and delete B, and A is treated as deleted. Declare a cycle, and QualiLens keeps one member of it and lands the evidence there rather than losing it.

Merging moves the merged code's excerpts to the target. For a grouping code it also moves the child codes, so evidence follows the merge rather than being stranded. The merged code is retained in the database with a record of where it went, and it disappears from your analysis.

You do not need to plan for any of this. It means an inconsistent set of merges produces a coherent result rather than an error.

### Add a code

**+ Add a code** in the toolbar appends a dashed row with an empty name and definition. Fill in the name, because a row left nameless is ignored on submission. Press **Remove** to discard a row you no longer want.

An added code carries no excerpts, and you cannot attach any to it. What the code does depends on where you add it. At the codebook checkpoint in content analysis, an added code enters the codebook and is applied to every source in the coding stage that follows. That is the case where adding is most useful. At an open-code or initial-code checkpoint, the added code is passed to the grouping stage and can be claimed by a category or theme, but it will appear in your report with no evidence beneath it. At a theme or category checkpoint, an added item will hold nothing at all, because no later stage assigns codes to it.

The useful case is content analysis. Elsewhere, adding a code records a concept you believe is present and the coder missed, and it does not put evidence in your report.

### Your decisions survive leaving the page

Everything you stage at a checkpoint is held in the browser for that checkpoint. That includes every rename, every merge, every deletion, every added code, and the current selection. Reloading the page, following a link to a coded document, or navigating away and coming back all restore the review exactly as you left it.

This is what makes the evidence links usable. You can open four transcripts to check a doubtful code, and the twenty decisions you had already staged are still there when you return.

The held state is cleared once you approve the checkpoint. It lives in the browser rather than in the database, so it does not survive a different browser or a private window, and it is not part of the audit trail.

### Approve and continue

This button submits every edit, action, and addition at once, applies them, and restarts the pipeline at the next stage.

Approval is atomic and single-use. A double click, or a second browser tab submitting the same checkpoint, is refused with a message saying the checkpoint has already been resolved, rather than applying your decisions twice. The checkpoint reopens so you can submit again if applying the decisions fails for any reason, and the sub-decisions that had already been applied re-apply harmlessly.

---

## The core category review panel

This panel appears once, in grounded theory, after selective coding.

Three fields are editable. They are the **core category** name, its **definition**, and the **storyline**, which is the one-to-two-paragraph integrative account the AI model produced. Beneath them, the relationships the model proposed between each category and the core are listed for your information. You cannot edit those here.

The storyline is the spine of your final report, and the report's opening section reproduces it. This is therefore the checkpoint where your own analytic voice enters the report most directly. Rewriting the storyline is expected rather than exceptional.

The panel tells you when selective coding produced no core category. There is then nothing to approve.

---

## The charting review panel

This panel appears once, in framework analysis, and it carries two lists.

**Emergent code candidates** appear only when you allowed emergent codes. Each candidate shows its proposed name, definition, excerpt count, and sample quotes, with **Promote to framework** and **Discard**. Promoting moves the code into your framework, where it keeps its excerpts and becomes a column in the matrix. Discarding removes the code and its evidence.

The default is discard. A candidate you leave untouched is discarded on approval, and you cannot recover it afterward.

**Low-confidence assignments** lists the sixty assignments the AI coder was least sure about, meaning those below sixty percent confidence, ordered from least confident upward. Each row carries a checkbox, and ticking it deletes that assignment. Deleted assignments are written to the audit trail with their quote before removal.

The panel tells you when both lists are empty. That means every assignment was confident and inside your framework.

This panel shows you the weakest coding and the out-of-framework proposals, and it shows you nothing else. The confident assignments are the bulk of the coding, and they are accepted on approval without individual review. Read a sample of them in [the coded-source reader](10-coded-source-reader.md), which you can reach from every source in your report.

---

## The extraction review panel

This panel appears once, in literature synthesis, after every paper has been extracted. It shows one collapsible row per paper: the label the synthesis will cite it by, its citation line, and a count of the located verbatim quotes behind its extraction — quotes that could not be located in the paper are counted separately, and those never ground the synthesis. **Review** opens the row's editable fields — the label, the citation, and the five extraction summaries, each with its own quote count. **Open coded paper** opens the paper in [the coded-source reader](10-coded-source-reader.md) with every extraction quote highlighted, which is how you check a summary against its source without leaving your staged edits behind.

Everything you type is a researcher edit in the same sense as a rename in the code review. A value you type and then change back is not an edit. A label you blank out is refused and the previous label kept, and a label that would duplicate another paper's is refused at approval, because the label is how the matrix and the narrative cite the paper. A field summary you blank out is honored.

**Exclude** removes a paper from the synthesis without removing it from the record. The synthesis, the matrix, and the narrative proceed without it; its extraction row stays in the report's appendix, marked as excluded, and the exclusion is logged. Use it for the paper that extraction reveals to be off topic. **Re-include** reverses a staged exclusion before you approve. Excluding every paper is refused at approval, because a synthesis needs at least one paper — re-include one, or cancel the run.

Like the code review, your staged edits are held in the browser for this checkpoint and survive reloads and side trips into coded papers, and approval is atomic and single-use.

The chapter on [literature synthesis](08-literature-synthesis.md) explains what to look for in the table itself.

---

## How to use a checkpoint well

The checkpoints make your analysis researcher-led, and they do that work only if you use them. Five habits are worth forming. Four of them take a few clicks each.

Sort by fewest excerpts first and work up. The thin end of the list is where duplicates and noise sit. Clearing that end means the grouping stage receives a clean set rather than a set full of synonyms competing for the same theme.

Merge in batches rather than one at a time. Tick every code that names the same idea, pick the best name as the target, and merge them in one action.

Open the evidence for any code whose name you find surprising, appealing, or too neat. A code that reads well and rests on two thin excerpts will carry a theme it cannot support. The panel shows you all of that code's evidence rather than a sample, so you can make the judgment quickly.

Follow **open in document ↗** on at least a few excerpts per checkpoint. Reading a quote inside its paragraph is the only way to catch a passage whose meaning reverses in context, and your staged decisions are waiting when you come back.

Ask what is absent. The panel shows you what the AI coder found, and it cannot show you what the coder missed. [The coded-source reader](10-coded-source-reader.md) can, because it shows you the uncoded stretches of the transcript. That check is the one that most often changes an analysis.
