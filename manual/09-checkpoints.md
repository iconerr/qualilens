<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 9. Checkpoints

A checkpoint is where the pipeline stops and hands your analysis to you. The run status changes to `awaiting review`, and a panel marked by an amber rule down its left edge appears at the top of the Run screen carrying the checkpoint's title and instructions. Nothing further happens, and nothing further is spent, until you press the panel's approve button.

A run waits indefinitely. Close the browser, come back tomorrow, and the panel is still there. You can also cancel from a checkpoint, which ends the run permanently.

A resolved review is final for its own run, but it is not the end of the road. From the Run screen's pipeline you can revisit any review the run has passed, which branches a new run from that point with everything up to it carried over, including the decisions already made at that review, which further decisions build on rather than undo. [Runs, Cancellation, and Recovery](11-runs-and-recovery.md) explains what carries, what re-runs, and when to branch earlier instead.

Four kinds of panel exist. Which one you see depends on the method and the stage.

| Panel | Appears at |
|---|---|
| Code review | Review of open codes and of categories in grounded theory, review of initial codes and of themes in thematic analysis, review of the codebook in content analysis, review of concepts in literature synthesis |
| Core category review | Review of the core category in grounded theory |
| Charting review | Review of the charting in framework analysis |
| Extraction review | Review of the extraction table in literature synthesis |

---

## What every panel shares

Each panel opens with its title, its instructions, and a sentence beginning *After you approve* that states what the next stage will do with what you approve. Beneath that, the panel has two columns. The left column holds the items under review, and the right column, headed **Your review**, records where the review stands.

The right column opens with one sentence on what the evidence holds, such as `21 codes hold 21 excerpts from 1 source. Every code rests on a single excerpt.` A small table beneath it tallies your decisions by kind, and the approve button follows. Below the button, **Working method** lists two or three habits suited to that checkpoint, and some of them carry a button that applies the habit, such as **Thinnest first**, which reorders the list. In a window narrower than about 1,100 pixels, the right column moves below the list, and a bar docked at the foot of the window keeps the count of staged decisions and the approve button in view.

### Every decision is written where you make it

A decision you stage changes the item in place and states its consequence in a full sentence. A merged code reads `It will merge into seeking reassurance, and its excerpts will move there.` A deleted category reads `It will be deleted, and its 3 codes will stay, listed under Uncategorized in the report.` An edited name or field shows what it was. Every staged decision can be undone, and nothing is applied until you approve.

### Notes

Every item under review can carry a note. Press **Add a note**, write why you decided as you did, and press **Save note**. The note travels with the decision into the audit trail, where it is recorded as an event beside the decision it explains. A note on an item you leave unchanged is recorded as well, as a considered keep, so the record shows that you looked at the item and why you left it as it was.

### The approve button

The button reads **Approve as proposed and continue** until you stage a decision, and from then on it counts what you staged, as in **Approve 6 decisions and continue**. The core category panel counts changes rather than decisions. **See what will be recorded** beneath the button lists each staged decision on a line of its own, so you can read the whole review before you commit to it.

Pressing the button submits every decision at once, applies them, and restarts the pipeline at the next stage. Approval is atomic and single-use. A double click, or a second browser tab submitting the same checkpoint, is refused with a message stating that the checkpoint has already been resolved, rather than applying your decisions twice. If applying the decisions fails for any reason, the checkpoint reopens so you can submit again, and the decisions that had already been applied re-apply harmlessly.

### Your decisions survive leaving the page

Everything you stage at a checkpoint is held in the browser for that checkpoint, including every edit, merge, deletion, addition, exclusion, and note, and the current selection. Reloading the page, following a link into a coded document, or navigating away and coming back all restore the review exactly as you left it.

This is what makes the document links usable. You can open four transcripts to check a doubtful code, and the twenty decisions you had already staged are still there when you return.

The held state is cleared once you approve the checkpoint. It lives in the browser rather than in the database, so it does not survive a different browser or a private window, and it enters the audit trail only when you approve.

---

## The code review panel

A first coding pass over twenty transcripts routinely returns well over a hundred codes. The code review panel sets each code beside the evidence it rests on, so that you judge a code by its quotes rather than by its name, and it gives you the tools to work through that many, namely a search box, four orders, a compact view, multi-select, and a key for every action.

The same panel reviews open codes, categories, initial codes, themes, a content analysis codebook, and literature synthesis concepts. Its wording follows the stage, so a category review refers to categories and a concept review to concepts. This section writes *code* for all of them.

### The toolbar

| Control | What it does |
|---|---|
| Search box | Filters the list to codes whose name or definition contains what you type |
| **Most evidence**, **Thinnest first**, **A–Z**, **Original** | Reorder the list. The four orders are described below |
| Count | Shows how many codes the list holds, or how many of them match your search |
| **Names only** or **Show evidence** | Switches between full rows and a compact list of names, counts, and the codes a grouping holds |

Know the orders individually. One of them is a working method rather than a preference.

| Order | Use it to |
|---|---|
| **Most evidence** | See the codes carrying the analysis. This is the default |
| **Thinnest first** | Surface the long tail of one-excerpt and two-excerpt codes, which is where near-duplicates and coding noise collect |
| **A–Z** | Bring near-synonyms next to each other when they share a first word |
| **Original** | Restore the order the coder produced them in |

Use **Thinnest first** to clean a code list. The codes at that end are mostly one of two things. They are either duplicates of something already in the list under another name, or single observations that never recurred. Deciding between those two readings is exactly the judgment a checkpoint exists to capture.

A review of more than forty codes opens in **Names only**, because a long list is easier to survey by name before you read its evidence. The compact rows still show each code's actions when you point at the row or move to it. Once you choose a view, the panel keeps it in this browser for later reviews.

### Each code

Each code appears as a row carrying a checkbox, the code's name, its count of excerpts and sources, its definition, and its first excerpt. The excerpt is set as a quotation, with the name of its source beneath it and a link reading **Open in document ↗**. Where the coder wrote a memo for the excerpt, a **Coder's memo** button beside the source opens it. **Show all 12 excerpts** loads every excerpt the code carries, in place and in full rather than as a sample, and **Show only the first excerpt** folds them away again. With every excerpt open, the row also shows why the coder formed the code, where the method records a reason.

For a grouping code such as a theme or a category, the count includes the excerpts held by its child codes, and a line beneath the definition lists the codes it holds, as in `It holds 4 codes (a · b · c · d).` A theme showing forty-two excerpts is therefore a theme whose codes between them evidence forty-two passages. Each quote under a grouping code is labeled `via` with the name of the child code that carries it, so you can see which of a theme's codes each piece of evidence came from.

At the theme review in thematic analysis, a theme that phase five renamed shows the candidate name it started from, and the model's own critique of the theme appears beneath the definition. At the concept review in literature synthesis, each concept lists the papers that support it.

At the content analysis codebook checkpoint, no coding has happened yet, so each code reads `not yet applied` and carries no quotes. You are reviewing definitions in the abstract at that checkpoint, against your own knowledge of the material.

The **Open in document ↗** link opens [the coded-source reader](10-coded-source-reader.md) in a new tab, at that excerpt in its transcript, briefly highlighted. Follow it to verify a code that only looks plausible. Your decisions are held while you are away.

Each row ends with four actions, namely **Rename**, **Merge into…**, **Delete**, and **Add a note**. For a grouping code the first reads **Rename or redefine**.

### Rename

**Rename** opens the code's name and definition for editing. Press Enter in the name, or press **Done**, to keep your wording, and press Esc or **Cancel** to leave the code as it was. In the definition, Enter starts a new line and Command-Enter saves. A renamed code shows its old name beneath the new one.

An edit you make by hand is permanent in a specific sense. The code is flagged as researcher-edited, and later automated stages will not overwrite it. In thematic analysis the phase-five naming stage runs before the theme review, so what you see at that checkpoint is already the final wording, and what you approve is what the report carries. A branch that reopens the review still leaves every theme you edited exactly as you wrote it.

Two details govern what counts as an edit. A value you type and then change back to what it was is not a rename, and it does not flag the code. A name you blank out is refused and the previous name is kept, because a code with no name cannot appear in a report. A definition you blank out is honored, because clearing a definition is a decision you might reasonably make.

### Merge

**Merge into…** opens a list of the codes you are keeping, in alphabetical order, each with its excerpt count. Type to narrow the list, and press Enter to take the first match, or choose any code in the list. Esc closes the list without merging. The merged row then states which code it will merge into and that its excerpts, or for a grouping its codes and their evidence, will move there, and the target lists the codes it absorbs beneath its definition, so the list shows you what you have decided before you commit to it.

The target must be a code you are keeping. Merge into the code whose name you want to keep, because the merged code's name leaves your analysis with the merge.

### Delete

**Delete** marks a code for removal, and the row states what deleting it will do. Deleting does more than it appears to. A code you delete is dropped from the current selection, and any merges you had staged into it are un-staged, because a delete must never quietly expand into deleting the evidence that other codes were about to be merged into. Those codes return to being kept, and you can merge them elsewhere.

For a plain code, deleting removes the code and its evidence from your analysis. For a grouping code, deleting removes the grouping and orphans its child codes. The report then sweeps those orphaned codes into an `Uncategorized` block with their evidence intact rather than losing them. Deleting a theme therefore removes the theme, not the data underneath it.

Delete when a code is an artifact of the coder rather than a feature of your data. Merge when two codes name the same thing. Rename when the code is right and its label is not.

### Undo

A code staged for merge or deletion shows **Undo merge** or **Undo delete**, which returns it to the kept state. Edits and actions are held separately. Undoing a merge therefore restores any rename you made before you merged it, and you lose nothing by changing your mind about the action.

### Selecting codes and acting in bulk

The checkbox on each row adds that code to a selection. A bar appears in the toolbar as soon as one code is selected, carrying the count and three actions.

| Action | What it does |
|---|---|
| **Merge into…** | Stages every selected code to merge into the one you choose. The list leaves out the selected codes themselves |
| **Delete** | Stages every selected code for deletion |
| **Clear selection** | Empties the selection without staging anything |

Bulk merging is the fastest way to clean a code list. Tick the four codes that all name the same idea, press **Merge into…** in the bar, and choose the code whose name you prefer. A code already staged for merge or deletion cannot be selected until you undo it.

### Keys

The list answers to the keyboard, which makes a long review much faster. Click a row, and the keys act on that row, while the arrow keys move from row to row. They do nothing while you are typing in a box, and the right-hand column lists them as a reminder.

| Key | Action |
|---|---|
| ↓ or J, ↑ or K | Move to the next or the previous code |
| R | Rename |
| M | Merge into… |
| D | Delete |
| N | Add a note |
| U | Undo a merge or a deletion |
| X | Select the code, or clear it from the selection |

Every key stages a decision you can undo, and nothing is applied until you approve.

### Add a code

**+ Add a code the coder missed** at the foot of the list appends a row with an empty name and definition. Fill in the name, because a row left nameless is ignored on submission. Press **Remove** to discard a row you no longer want. A line on the new row states what an added code does at this stage.

An added code carries no excerpts, and you cannot attach any to it. What the code does depends on where you add it. At the codebook checkpoint in content analysis, an added code enters the codebook and is applied to every source in the coding stage that follows. That is the case where adding is most useful. At an open-code or initial-code checkpoint, the added code is passed to the grouping stage and can be claimed by a category or theme, but it will appear in your report with no evidence beneath it. At a theme or category checkpoint, an added item will hold nothing at all, because no later stage assigns codes to it. At the concept checkpoint in literature synthesis, an added concept carries no quotes, and the matrix will show it empty.

The useful case is content analysis. Elsewhere, adding a code records a concept you believe is present and the coder missed, and it does not put evidence in your report.

### What the right-hand column measures

The tally counts the codes renamed, merging, deleting, added, and carrying a note, and the codes left unchanged. The sentence above it counts the codes, their excerpts, and the sources the excerpts come from, and it flags the codes that rest on a single excerpt, or at a category or theme review, the groupings that rest on a single code.

At the open-code, initial-code, category, and theme checkpoints, **Working method** also measures what the coder left out. It finds the source with the largest share of text that carries no code and states that share, as in `Ask what the coder missed, because 50% of the transcript has no code.`, with a link that opens that source in [the coded-source reader](10-coded-source-reader.md), where the uncoded stretches are visible. The measure is absent at the codebook checkpoint, because nothing has been coded yet, and at the concept checkpoint, because papers are quoted rather than coded in full.

### How merges are resolved

The resolution handles chains and cycles rather than failing on them. Merge A into B and B into C in the same submission, and A's evidence lands on C. Merge A into B and delete B, and A is treated as deleted. Declare a cycle, and QualiLens keeps one member of it and lands the evidence there rather than losing it.

Merging moves the merged code's excerpts to the target. For a grouping code it also moves the child codes, so evidence follows the merge rather than being stranded. The merged code is retained in the database with a record of where it went, and it disappears from your analysis.

You do not need to plan for any of this. It means an inconsistent set of merges produces a coherent result rather than an error.

Approval checks every decision before it applies any. A decision that names a code from another run, a merge into a code that is no longer active, or a merge across kinds of code (an open code into a theme) is refused with a message, and the checkpoint stays open for you to correct it. Nothing is half-applied.

### Working in a spreadsheet

A checkpoint with a hundred codes is a codebook, and a codebook is easier to read, share with a co-coder, and revise in a spreadsheet than on a screen. Two links in the right-hand column, **Download as spreadsheet** and **Upload spreadsheet**, make that possible without leaving the record.

**Download as spreadsheet** saves an `.xlsx` workbook with three sheets. The *Codes* sheet has one row per code, with its id, name, definition, excerpt count, and first excerpt for orientation, and three columns for you, namely *action*, *merge into*, and *notes*. The *Excerpts* sheet lists every excerpt behind every code, for reference. The *About* sheet identifies the project, run, and checkpoint the file belongs to and repeats the rules below. Numbers, Excel, and Google Sheets all open and save it.

Edit the workbook as you would any codebook. Changing a name or a definition in place is a rename or a redefinition, and it needs no action word. To merge, choose *merge* in the action column and put the target's id or its exact name in *merge into*. Choose *delete* to delete, and leave the action blank to keep. Add a code by adding a row with an empty id and a name, and write your reasoning in *notes*. Leave the id column as it is, because it is how each row finds its code.

**Upload spreadsheet** reads the file back and loads its decisions into the panel as staged decisions. A line above the list then shows the file's name and what it found, such as how many codes it renamed, merged, deleted, or added and how many carry notes, together with how many rows it ignored, and **(show)** lists the reason for each. Nothing is applied by the upload. You read the panel, change anything you like, and approve as always. If decisions were already staged on the screen, the upload replaces them, and it asks first.

The upload refuses or reports rather than guessing. A workbook from a different checkpoint is refused, and the message identifies the checkpoint it belongs to. A row whose id is not in this checkpoint is ignored and listed. A code with no row in the file is unchanged, so deleting a row in the spreadsheet does not delete a code, and only the *delete* action does. A blank name keeps the old name. A merge target that matches no code, or more than one, is reported. A file that is not an `.xlsx`, or is larger than 10 MB, is refused.

Notes in the workbook travel into the audit trail exactly as notes typed on the screen do. When you approve, the workbook itself is kept with the run's uploads and listed in the audit trail and the audit export, so the worksheet you actually worked in becomes part of the record.

The extraction table in literature synthesis has the same two links. Its workbook has a *Papers* sheet, with one row per paper holding the label, the citation, the five fields, the findings the paper attributes to other work, an *exclude* column that takes *yes* or *no*, and *notes*, and a *Quotes* sheet that lists the extraction quotes by paper and field. A changed field becomes an edit to that field alone, and a blank label keeps the old one.

---

## The core category review panel

This panel appears once, in grounded theory, after selective coding. It is the checkpoint where your own analytic voice enters the report most directly, and it has four parts.

**The core category** shows the core's name and definition. **Edit the name or definition** opens both for editing. A name you blank out is refused and the previous name is kept.

**Storyline** shows the one-to-two-paragraph integrative account the AI model produced. The storyline is the spine of your final report, and the report's opening section reproduces it, so rewriting it is expected rather than exceptional. **Rewrite the storyline** opens the whole text for editing, and your wording is final.

**How each category relates to the core** draws the grounded theory model as the report will draw it, and lists each category with its counts of codes and excerpts, the relation the model proposed, and the model's explanation. A category for which the model proposed no relationship is listed as well, with a line stating that none was proposed, because a core category should account for every category. You cannot edit the relationships here, but a note can record where you disagree with them.

**Where the data are thin** lists the places where the model judged the data insufficient. These go into the report, word for word, as its *Theoretical Sampling Recommendations*. Each one can be edited or left out of the report, and **+ Add a place where the data are thin** adds one of your own. A recommendation you left out shows **Keep it**, which restores it.

Once you change the core category or the storyline, it shows that you changed it, with a button that shows the model's version beside yours and a button that undoes your change. A recommendation you edited is marked `edited`, and one you added is marked `added by you`. A single note, at the foot of the panel, can record why you changed what you changed or why you approve the core as it stands, and it is recorded with your approval.

The audit trail records which parts you changed. Approving without changing anything is recorded as an unchanged approval, not as an edit. The right-hand column tallies the core category and the storyline as edited or unchanged, the number of sampling recommendations the report will carry, and whether you added a note.

The panel states when selective coding produced no core category. There is then nothing to approve.

---

## The charting review panel

This panel appears once, in framework analysis, and it carries two lists.

**Candidate codes outside the framework** appear only when you allowed emergent codes. These are passages the coder found important that fit no framework code, gathered under a proposed code. Each candidate shows its proposed name, its number of passages, its definition, and sample quotes, each with its source and an **Open in document ↗** link, followed by two buttons, **Promote to the framework** and **Discard**. Promoting moves the code into your framework, where it keeps its passages, is charted across every source by the stage that follows, and becomes a column in the matrix. Discarding removes the code and its passages' coding. Pressing the chosen button a second time withdraws the decision.

The default is discard. A candidate you leave undecided reads `It is not decided, so it will be discarded if you leave it.`, the right-hand column repeats the count of undecided candidates beneath the approve button, and a discarded candidate cannot be recovered afterward.

**Assignments below 60% confidence** lists the sixty assignments the AI coder was least sure about. The line above the list states how many assignments fell below the threshold and how many the framework holds in all, so you can see what share you are reviewing. By default the list is grouped **By framework code**, and each group opens with the code's name, how many of its assignments fall below sixty percent, and the code's definition, so that each passage is judged against the definition rather than the name. **Weakest first** lists the assignments in order of confidence instead, each with its code's name and definition beside it. An assignment that came back with no confidence at all is marked `No confidence given` and comes first, within its code's group when the list is grouped.

Each assignment shows its quote, its confidence, its source, and an **Open in document ↗** link, with **Coder's reason** where the coder gave one, followed by two buttons, **Keep** and **Remove**. A removed assignment reads `It will be removed from this code, and the audit trail keeps the quote.` Removed assignments are written to the audit trail with their quote before removal, and a note you add to an assignment, kept or removed, is recorded beside it.

The panel states when both lists are empty. That means every assignment was confident and inside your framework.

This panel shows you the weakest coding and the out-of-framework proposals, and it shows you nothing else. The confident assignments are the bulk of the coding, and they are accepted on approval without individual review. Read a sample of them in [the coded-source reader](10-coded-source-reader.md), which you can reach from every source in your report.

---

## The extraction review panel

This panel appears once, in literature synthesis, after every paper has been extracted. It shows the extraction table, with one row per paper. Each row carries the label the synthesis will cite the paper by, its citation line, and one column per extraction field. A number in a field's column counts the verbatim quotes located in the paper for that field. A dash marks a field the paper does not report, and an amber `0` marks a summary with no quote behind it. The last column counts the quotes that could not be located in the paper, which never ground the synthesis.

The toolbar carries a search box over labels and citations and three orders, namely **As listed**, **Fewest quotes**, and **Most not located**. When any summary lacks a quote, **Working method** counts those summaries, and **Show those papers** narrows the table to the papers that hold them, which is where a review of the table should start.

Select a paper to open it in place. Each field shows its summary beside the quotes behind it, two at first and **Show all** for the rest, each with the extractor's reason for choosing it where it gave one. A summary with no quote behind it reads `No quote in the paper supports this summary.` **Edit** beneath any field opens it for editing, including the label, the citation, and the *cited work* note, which holds findings the paper attributes to other work and is never offered to the synthesis. An edited field shows what it was, with a button that restores it. **Open the coded paper ↗** opens the paper in [the coded-source reader](10-coded-source-reader.md) with every extraction quote highlighted, which is how you check a summary against its source without leaving your staged edits behind.

Everything you type is a researcher edit in the same sense as a rename in the code review. A value you type and then change back is not an edit. A label you blank out is refused and the previous label kept, and a label that would duplicate another paper's is refused at approval, because the label is how the matrix and the narrative cite the paper. A field summary you blank out is honored.

**Exclude from the synthesis…** removes a paper from the synthesis without removing it from the record. The panel first asks why, and your reason is recorded with the exclusion as your note on that paper, because a synthesis has to account for what it left out. The synthesis, the matrix, and the narrative proceed without the paper, and its extraction row stays in the report's appendix, marked as excluded. Use it for the paper that extraction reveals to be off topic. **Re-include** reverses a staged exclusion before you approve. The panel refuses to exclude the last paper still included, because a synthesis needs at least one.

The right-hand column tallies the papers you corrected, the papers you excluded, the papers that carry a note, and the papers left unchanged. Like every panel, this one holds your staged decisions in the browser, and the table can also be downloaded as a workbook, edited, and uploaded again, as [Working in a spreadsheet](#working-in-a-spreadsheet) describes.

The chapter on [literature synthesis](08-literature-synthesis.md) explains what to look for in the table itself.

---

## How to use a checkpoint well

The checkpoints make your analysis researcher-led, and they do that work only if you use them. Five habits are worth forming, and four of them take a few clicks each.

Start from **Thinnest first** and work up. The thin end of the list is where duplicates and noise sit. Clearing that end means the grouping stage receives a clean set rather than a set full of synonyms competing for the same theme.

Merge in batches rather than one at a time. Tick every code that names the same idea, press **Merge into…**, and choose the code whose name you want to keep.

Read all the evidence for any code whose name you find surprising, appealing, or too neat. A code that reads well and rests on two thin excerpts will carry a theme it cannot support. **Show all** loads every excerpt the code carries rather than a sample, so you can make the judgment quickly.

Follow **Open in document ↗** on at least a few excerpts per checkpoint. Reading a quote inside its paragraph is the only way to catch a passage whose meaning reverses in context, and your staged decisions are waiting when you come back.

Ask what is absent. The panel shows you what the AI coder found, and it cannot show you what the coder missed. Its right-hand column states how much of the least-coded source carries no code and links to that source, and [the coded-source reader](10-coded-source-reader.md) shows you the uncoded stretches of every transcript. That check is the one that most often changes an analysis.
