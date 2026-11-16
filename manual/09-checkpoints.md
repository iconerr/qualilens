<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 9. Checkpoints

A checkpoint is where the pipeline stops and hands your analysis to you. The run status changes to `awaiting review`, and a panel with an amber edge appears at the top of the Run screen. It carries the checkpoint's title and instructions. Nothing further happens, and nothing further is spent, until you approve.

A run waits indefinitely. Close the browser, come back tomorrow, and the panel is still there. You can also cancel from a checkpoint, which ends the run permanently.

A resolved review is final for its own run. It is not the end of the road. From the Run screen's pipeline you can revisit any review the run has passed. That starts a new run with everything up to that point, including the decisions you made at that review, and new decisions build on them. [Runs, Cancellation, and Recovery](11-runs-and-recovery.md) explains what carries, what re-runs, and when to branch earlier instead.

Four kinds of panel exist. Which one you see depends on the method and the stage.

| Panel | Appears at |
|---|---|
| Code review | Review of open codes and of categories in grounded theory, review of initial codes and of themes in thematic analysis, review of the codebook in content analysis, review of concepts in literature synthesis |
| Core category review | Review of the core category in grounded theory |
| Charting review | Review of the charting in framework analysis |
| Extraction review | Review of the extraction table in literature synthesis |

---

## What every panel shares

Each panel opens with its title and instructions. A line beginning *After you approve* says what the next stage will do.

Below that are two columns. The items under review fill the left. The right column, headed **Your review**, shows where the review stands.

The right column starts with one sentence about the evidence, such as `21 codes hold 21 excerpts from 1 source. Every code rests on a single excerpt.` A small table counts your decisions by kind. The approve button comes next. Below it, **Working method** lists two or three habits for that checkpoint. Some carry a button that applies the habit. **Thinnest first**, for example, reorders the list.

In a window narrower than about 1,100 pixels, the right column moves below the list. A bar at the foot of the window keeps the count of staged decisions and the approve button in view.

### Every decision is written where you make it

A decision you stage changes the item in place and says what will happen. A merged code reads `It will merge into seeking reassurance. Its excerpts move with it.` A deleted category reads `It will be deleted. Its 3 codes stay, listed under Uncategorized in the report.` An edited name or field shows what it was.

Every staged decision can be undone. Nothing is applied until you approve.

### Notes

Any item under review can carry a note. Press **Add a note**, write why you decided as you did, and press **Save note**.

The note goes into the audit trail beside the decision it explains. A note on an item you leave unchanged is recorded too, as a considered keep. The record then shows that you looked at the item and why you left it.

### The approve button

The button reads **Approve as proposed and continue** until you stage a decision. From then on it counts them, as in **Approve 6 decisions and continue**. The core category panel counts changes instead. **See what will be recorded**, under the button, lists every staged decision on its own line. Read it before you commit.

Pressing the button submits every decision at once, applies them, and restarts the pipeline at the next stage. Approval is atomic and single-use. A double click, or a second browser tab submitting the same checkpoint, is refused with a message that the checkpoint has already been resolved. Your decisions are never applied twice. If applying them fails for any reason, the checkpoint reopens so you can submit again. Decisions that were already applied re-apply harmlessly.

### Your decisions survive leaving the page

Everything you stage at a checkpoint is held in the browser for that checkpoint. That includes every edit, merge, deletion, addition, exclusion, and note, and the current selection. Reloading the page, following a link into a coded document, or navigating away and coming back all restore the review exactly as you left it.

This is what makes the document links usable. You can open four transcripts to check a doubtful code, and the twenty decisions you had already staged are still there when you return.

The held state is cleared once you approve. It lives in the browser, not the database. It does not survive a different browser or a private window, and it enters the audit trail only when you approve.

---

## The code review panel

A first coding pass over twenty transcripts routinely returns well over a hundred codes. The code review panel puts each code beside the evidence it rests on, so you judge a code by its quotes rather than its name. It also gives you the tools to work through that many: a search box, four orders, a compact view, multi-select, and a key for every action.

The same panel reviews open codes, categories, initial codes, themes, a content analysis codebook, and literature synthesis concepts. Its wording follows the stage. This section says *code* for all of them.

### The toolbar

| Control | What it does |
|---|---|
| Search box | Filters the list to codes whose name or definition contains what you type |
| **Most evidence**, **Thinnest first**, **A–Z**, **Original** | Reorder the list. The four orders are described below |
| Count | Shows how many codes the list holds, or how many match your search |
| **Names only** or **Show evidence** | Switches between full rows and a compact list of names and counts |

Know the orders individually. One of them is a working method rather than a preference.

| Order | Use it to |
|---|---|
| **Most evidence** | See the codes carrying the analysis. This is the default |
| **Thinnest first** | Surface the long tail of one-excerpt and two-excerpt codes, which is where near-duplicates and coding noise collect |
| **A–Z** | Bring near-synonyms next to each other when they share a first word |
| **Original** | Restore the order the coder produced them in |

Use **Thinnest first** to clean a code list. The codes at that end are mostly one of two things. They are either duplicates of something already in the list under another name, or single observations that never recurred. Deciding between those two readings is exactly the judgment a checkpoint exists to capture.

A review of more than forty codes opens in **Names only**. A long list is easier to survey by name first. The compact rows still show a code's actions when you point at it or move to it. The panel remembers the view you choose, in this browser.

### Each code

Each code is a row. It carries a checkbox, the code's name, its counts of excerpts and sources, its definition, and its first excerpt.

The excerpt is set as a quotation. Beneath it are the source's name and an **Open in document ↗** link. Where the coder wrote a memo, **Coder's memo** opens it. **Show all 12 excerpts** loads every excerpt in place, in full. **Show only the first excerpt** folds them away again. With every excerpt open, the row also shows why the coder formed the code, where the method records a reason.

For a grouping code, such as a theme or a category, the count includes the excerpts of its child codes. A theme showing forty-two excerpts is a theme whose codes between them evidence forty-two passages. A line under the definition lists the codes it holds, as in `It holds 4 codes (a · b · c · d).` Each quote is labeled `via` with the child code that carries it, so you can see which of a theme's codes each piece of evidence came from.

At the theme review in thematic analysis, a theme renamed in phase five shows the candidate name it started from. The model's own critique of the theme sits under the definition. At the concept review in literature synthesis, each concept lists the papers that support it.

At the content analysis codebook checkpoint, nothing has been coded yet. Each code reads `not yet applied` and has no quotes. You are reviewing definitions in the abstract, against your own knowledge of the material.

**Open in document ↗** opens [the coded-source reader](10-coded-source-reader.md) in a new tab, at that excerpt in its transcript, briefly highlighted. Follow it to verify a code that only looks plausible. Your decisions are held while you are away.

Each row ends with four actions: **Rename**, **Merge into…**, **Delete**, and **Add a note**. For a grouping code the first reads **Rename or redefine**.

### Rename

**Rename** opens the code's name and definition. Press Enter in the name, or **Done**, to keep your wording. Press Esc or **Cancel** to leave the code as it was. In the definition, Enter starts a new line and Command-Enter saves. A renamed code shows its old name under the new one.

An edit you make by hand is permanent in a specific sense. The code is flagged as researcher-edited, and later automated stages will not overwrite it. In thematic analysis the phase-five naming stage runs before the theme review, so what you see at that checkpoint is already the final wording. What you approve is what the report carries. A branch that reopens the review still leaves every theme you edited exactly as you wrote it.

Two details govern what counts as an edit. A value you type and then change back to what it was is not a rename, and it does not flag the code. A name you blank out is refused and the previous name is kept, because a code with no name cannot appear in a report. A definition you blank out is honored, because clearing a definition is a decision you might reasonably make.

### Merge

**Merge into…** opens a list of the codes you are keeping, in alphabetical order, each with its excerpt count. Type to narrow the list. Enter takes the first match, or you can choose any code in the list. Esc closes the list without merging.

The merged row then says which code it will merge into and that its excerpts move with it. For a grouping, its codes and their evidence move. The target lists the codes it absorbs under its definition. You see what you have decided before you commit to it.

The target must be a code you are keeping. Merge into the code whose name you want to keep. The merged code's name leaves your analysis.

### Delete

**Delete** marks a code for removal, and the row says what deleting it will do.

Deleting does more than it appears to. A code you delete is dropped from the current selection. Any merges you had staged into it are cancelled, because a delete must never quietly take the evidence that other codes were about to merge into it. Those codes return to being kept, and you can merge them elsewhere.

For a plain code, deleting removes the code and its evidence from your analysis. For a grouping code, deleting removes the grouping and orphans its child codes. The report then sweeps those orphaned codes into an `Uncategorized` block with their evidence intact rather than losing them. Deleting a theme therefore removes the theme, not the data underneath it.

Delete when a code is an artifact of the coder rather than a feature of your data. Merge when two codes name the same thing. Rename when the code is right and its label is not.

### Undo

A code staged for merge or deletion shows **Undo merge** or **Undo delete**, which returns it to the kept state. Edits and actions are held separately. Undoing a merge therefore restores any rename you made before you merged it. You lose nothing by changing your mind.

### Selecting codes and acting in bulk

The checkbox on each row adds that code to a selection. As soon as one code is selected, a bar appears in the toolbar with the count and three actions.

| Action | What it does |
|---|---|
| **Merge into…** | Stages every selected code to merge into the one you choose. The list leaves out the selected codes themselves |
| **Delete** | Stages every selected code for deletion |
| **Clear selection** | Empties the selection without staging anything |

Bulk merging is the fastest way to clean a code list. Tick the four codes that name the same idea, press **Merge into…** in the bar, and choose the code whose name you prefer. A code already staged for merge or deletion cannot be selected until you undo it.

### Keys

The list answers to the keyboard, which makes a long review much faster. Click a row, and the keys act on that row. The arrow keys move from row to row. Keys do nothing while you are typing in a box. The right-hand column lists them as a reminder.

| Key | Action |
|---|---|
| ↓ or J, ↑ or K | Move to the next or the previous code |
| R | Rename |
| M | Merge into… |
| D | Delete |
| N | Add a note |
| U | Undo a merge or a deletion |
| X | Select the code, or clear it from the selection |

Every key stages a decision you can undo. Nothing is applied until you approve.

### Add a code

**+ Add a code the coder missed**, at the foot of the list, adds a row with an empty name and definition. Fill in the name. A row left nameless is ignored. **Remove** discards a row you no longer want. A line on the new row says what an added code does at this stage.

An added code carries no excerpts, and you cannot attach any to it. What it does depends on where you add it.

| Checkpoint | What an added code does |
|---|---|
| Codebook (content analysis) | Enters the codebook and is applied to every source in the coding stage that follows |
| Open codes or initial codes | Passes to the grouping stage, which can claim it, and appears in the report with no evidence |
| Categories or themes | Stays empty, because no later stage assigns codes to it |
| Concepts (literature synthesis) | Has no quotes, so the matrix shows it empty |

The useful case is content analysis. Elsewhere, adding a code records a concept you believe is present and the coder missed. It does not put evidence in your report.

### What the right-hand column measures

The tally counts the codes renamed, merging, deleting, added, and carrying a note, and the codes left unchanged. The sentence above it counts the codes, their excerpts, and the sources they come from. It flags the codes that rest on a single excerpt. At a category or theme review, it flags the groupings that rest on a single code.

At the open-code, initial-code, category, and theme checkpoints, **Working method** also measures what the coder left out. It finds the source with the largest share of uncoded text and gives that share, as in `Ask what the coder missed. 50% of the transcript has no code.` Its link opens that source in [the coded-source reader](10-coded-source-reader.md), where the uncoded stretches are visible. The measure is absent at the codebook checkpoint, where nothing is coded yet, and at the concept checkpoint, where papers are quoted rather than coded in full.

### How merges are resolved

The resolution handles chains and cycles rather than failing on them. Merge A into B and B into C in the same submission, and A's evidence lands on C. Merge A into B and delete B, and A is treated as deleted. Declare a cycle, and QualiLens keeps one member of it and lands the evidence there rather than losing it.

Merging moves the merged code's excerpts to the target. For a grouping code it also moves the child codes, so evidence follows the merge rather than being stranded. The merged code is retained in the database with a record of where it went, and it disappears from your analysis.

You do not need to plan for any of this. It means an inconsistent set of merges produces a coherent result rather than an error.

Approval checks every decision before it applies any. A decision that names a code from another run, a merge into a code that is no longer active, or a merge across kinds of code (an open code into a theme) is refused with a message. The checkpoint stays open for you to correct it. Nothing is half-applied.

### Working in a spreadsheet

A checkpoint with a hundred codes is a codebook. A codebook is easier to read, share with a co-coder, and revise in a spreadsheet than on a screen. Two links in the right-hand column, **Download as spreadsheet** and **Upload spreadsheet**, let you do that without leaving the record.

**Download as spreadsheet** saves an `.xlsx` workbook with three sheets.

| Sheet | What it holds |
|---|---|
| *Codes* | One row per code: id, name, definition, excerpt count, and first excerpt, plus three columns for you, *action*, *merge into*, and *notes* |
| *Excerpts* | Every excerpt behind every code, for reference |
| *About* | The project, run, and checkpoint the file belongs to, and the rules below |

Numbers, Excel, and Google Sheets all open and save it.

Edit the workbook as you would any codebook. Changing a name or a definition in place is a rename or a redefinition. It needs no action word. To merge, choose *merge* in the action column and put the target's id or exact name in *merge into*. Choose *delete* to delete. Leave the action blank to keep. Add a code by adding a row with an empty id and a name. Write your reasoning in *notes*. Leave the id column alone, because it is how each row finds its code.

**Upload spreadsheet** reads the file back and loads its decisions into the panel as staged decisions. A line above the list shows the file's name and what it found: how many codes it renamed, merged, deleted, or added, how many carry notes, and how many rows it ignored. **(show)** lists the reason for each ignored row. Nothing is applied by the upload. You read the panel, change anything you like, and approve as always. If decisions were already staged, the upload asks first, then replaces them.

The upload refuses or reports rather than guessing.

- A workbook from a different checkpoint is refused, and the message names the checkpoint it belongs to.
- A row whose id is not in this checkpoint is ignored and listed.
- A code with no row in the file is unchanged. Deleting a row in the spreadsheet does not delete a code; only the *delete* action does.
- A blank name keeps the old name.
- A merge target that matches no code, or more than one, is reported.
- A file that is not an `.xlsx`, or is larger than 10 MB, is refused.

Notes in the workbook reach the audit trail just as notes typed on the screen do. When you approve, the workbook itself is kept with the run's uploads and listed in the audit trail and the audit export. The worksheet you actually worked in becomes part of the record.

The extraction table in literature synthesis has the same two links. Its workbook has a *Papers* sheet and a *Quotes* sheet. *Papers* has one row per paper with the label, the citation, the five fields, the findings the paper attributes to other work, an *exclude* column that takes *yes* or *no*, and *notes*. *Quotes* lists the extraction quotes by paper and field. A changed field becomes an edit to that field alone. A blank label keeps the old one.

---

## The core category review panel

This panel appears once, in grounded theory, after selective coding. It is where your own analytic voice enters the report most directly. It has four parts.

**The core category** shows the core's name and definition. **Edit the name or definition** opens both. A name you blank out is refused and the previous name is kept.

**Storyline** shows the one-to-two-paragraph account the AI model wrote to integrate the categories. The report opens with it. Rewriting it is expected, not exceptional. **Rewrite the storyline** opens the whole text, and your wording is final.

**How each category relates to the core** shows the grounded theory model as the report will draw it. Each category is listed with its counts of codes and excerpts, the relation the model proposed, and the model's explanation. A category with no proposed relationship is listed too, because a core category should account for every category. You cannot edit the relationships here. A note can record where you disagree.

**Where the data are thin** lists the places where the model judged the data insufficient. These go into the report, word for word, as its *Theoretical Sampling Recommendations*. You can edit each one or leave it out of the report. **+ Add a place where the data are thin** adds one of your own. A recommendation you left out shows **Keep it**, which restores it.

When you change the core category or the storyline, the panel marks the change. One button shows the model's version beside yours, and another undoes your change. A recommendation you edited is marked `edited`, and one you added is marked `added by you`.

A single note at the foot of the panel can say why you changed what you changed, or why you approve the core as it stands. It is recorded with your approval.

The audit trail records which parts you changed. Approving without changing anything is recorded as an unchanged approval, not as an edit. The right-hand column shows whether the core category and the storyline were edited, how many sampling recommendations the report will carry, and whether you added a note.

The panel says so when selective coding produced no core category. There is then nothing to approve.

---

## The charting review panel

This panel appears once, in framework analysis. It carries two lists.

**Candidate codes outside the framework** appear only when you allowed emergent codes. These are passages the coder found important that fit no framework code, grouped under a proposed code. Each candidate shows its proposed name, its number of passages, its definition, and sample quotes with their sources and **Open in document ↗** links.

Two buttons follow: **Promote to the framework** and **Discard**. A promoted code joins your framework with its passages, is charted across every source by the next stage, and becomes a column in the matrix. A discarded code is removed with its passages' coding. Press the chosen button again to withdraw the decision.

The default is discard. A candidate you leave undecided reads `It is not decided. If you leave it, it is discarded.` The right-hand column repeats the count of undecided candidates under the approve button. A discarded candidate cannot be recovered afterward.

**Assignments below 60% confidence** lists the sixty assignments the AI coder was least sure about. The line above the list says how many fell below the threshold and how many the framework holds in all.

By default the list is grouped **By framework code**. Each group opens with the code's name, how many of its assignments fall below sixty percent, and the code's definition. You judge each passage against the definition, not the name. **Weakest first** lists the assignments by confidence instead, each with its code's name and definition. An assignment that came back with no confidence is marked `No confidence given` and comes first, within its code's group when the list is grouped.

Each assignment shows its quote, its confidence, its source, an **Open in document ↗** link, and **Coder's reason** where the coder gave one. Two buttons follow: **Keep** and **Remove**. A removed assignment reads `It will be removed from this code. The audit trail keeps the quote.` Removed assignments are written to the audit trail with their quote before removal. A note on any assignment, kept or removed, is recorded beside it.

The panel says so when both lists are empty. That means every assignment was confident and inside your framework.

This panel shows you the weakest coding and the out-of-framework proposals, and nothing else. The confident assignments are the bulk of the coding, and they are accepted on approval without individual review. Read a sample of them in [the coded-source reader](10-coded-source-reader.md), which you can reach from every source in your report.

---

## The extraction review panel

This panel appears once, in literature synthesis, after every paper has been extracted. It shows the extraction table, one row per paper.

Each row carries the label the synthesis will cite the paper by, its citation line, and one column per extraction field. A number counts the verbatim quotes located in the paper for that field. A dash marks a field the paper does not report. An amber `0` marks a summary with no quote behind it. The last column counts the quotes that could not be located in the paper. Those never ground the synthesis.

The toolbar has a search box for labels and citations and three orders: **As listed**, **Fewest quotes**, and **Most not located**. When any summary has no quote behind it, **Working method** counts those summaries. **Show those papers** narrows the table to them. Start your review there.

Select a paper to open it in place. Each field shows its summary beside the quotes behind it, two at first, with **Show all** for the rest. Each quote carries the extractor's reason for choosing it, where it gave one. A summary with no quote reads `No quote in the paper supports this summary.`

**Edit**, under any field, opens it, including the label, the citation, and the *cited work* note. That note holds findings the paper attributes to other work, and it is never offered to the synthesis. An edited field shows what it was, with a button that restores it. **Open the coded paper ↗** opens the paper in [the coded-source reader](10-coded-source-reader.md) with every extraction quote highlighted. That is how you check a summary against its source without losing your staged edits.

Everything you type is a researcher edit, in the same sense as a rename in the code review. A value you type and then change back is not an edit. A label you blank out is refused and the previous label kept. A label that would duplicate another paper's is refused at approval, because the matrix and the narrative cite papers by label. A field summary you blank out is honored.

**Exclude from the synthesis…** removes a paper from the synthesis without removing it from the record. The panel asks why first. Your reason is recorded with the exclusion, because a synthesis should account for what it leaves out. The synthesis, the matrix, and the narrative proceed without the paper. Its extraction row stays in the report's appendix, marked as excluded. Use it for the paper that extraction reveals to be off topic. **Re-include** reverses a staged exclusion before you approve. The panel will not exclude the last paper still included, because a synthesis needs at least one.

The right-hand column counts the papers you corrected, the papers you excluded, the papers with a note, and the papers left unchanged. As in every panel, your staged decisions are held in the browser. The table can also be downloaded as a workbook, edited, and uploaded again, as [Working in a spreadsheet](#working-in-a-spreadsheet) describes.

The chapter on [literature synthesis](08-literature-synthesis.md) explains what to look for in the table itself.

---

## How to use a checkpoint well

The checkpoints make your analysis researcher-led, but only if you use them. Five habits are worth forming. Four of them take a few clicks each.

Start from **Thinnest first** and work up. The thin end of the list is where duplicates and noise sit. Clearing that end means the grouping stage receives a clean set rather than a set full of synonyms competing for the same theme.

Merge in batches rather than one at a time. Tick every code that names the same idea, press **Merge into…**, and choose the code whose name you want to keep.

Read all the evidence for any code whose name you find surprising, appealing, or too neat. A code that reads well and rests on two thin excerpts will carry a theme it cannot support. **Show all** loads every excerpt the code carries, not a sample, so the judgment is quick.

Follow **Open in document ↗** on at least a few excerpts per checkpoint. Reading a quote inside its paragraph is the only way to catch a passage whose meaning reverses in context. Your staged decisions are waiting when you come back.

Ask what is absent. The panel shows you what the AI coder found. It cannot show you what the coder missed. Its right-hand column gives the share of the least-coded source that carries no code and links to that source. [The coded-source reader](10-coded-source-reader.md) shows the uncoded stretches of every transcript. That check is the one that most often changes an analysis.
