<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 15. A Worked Analysis, End to End

This chapter follows one dataset through the whole application. The dataset is eight interviews with community pharmacists about conversations with patients on reducing long-term medication, and the method is thematic analysis. The figures quoted are illustrative. They are chosen so that you can check your own run against the same arithmetic.

The eight transcripts are Word documents averaging thirty-eight thousand characters each, three hundred and four thousand characters in total. They have already been de-identified.

---

## Before starting

Open **Settings** and save an Anthropic key. Press **Test**, and wait for the badge to report that the key works.

The transcripts are documents rather than recordings, so you need no OpenAI key and ffmpeg is irrelevant. You would need both if these were audio files.

---

## Step 1. Method

Press **New analysis**. Five cards appear.

The question here is what your study claims. This study reports what pharmacists find difficult about a particular kind of conversation. That is a claim about patterns of meaning rather than about a process, so thematic analysis is the honest choice. Grounded theory would promise a theory the study is not trying to build.

Read the pipeline printed on the card before you click. It tells you the run will stop twice.

```
Pipeline: Familiarization → Initial coding → Review initial codes → Constructing
themes → Reviewing themes against data → Review themes → Defining & naming
themes → Report
```

Select the Thematic Analysis card and press **Continue**.

---

## Step 2. Method setup

Name the project `Deprescribing conversations, pharmacists, 2026`.

Your research question needs to be sharp enough to focus the coding, because the AI coder is instructed to code every segment relevant to it. `What makes deprescribing conversations difficult for community pharmacists, and what do they do about it` is specific about the phenomenon and open about the answer.

Set the coding orientation to **Inductive (data-driven)**. This study describes a practice that has not been well characterized in this setting, so fixing the analytic vocabulary in advance would defeat the purpose.

Set the level of meaning to **Semantic (explicit, surface meanings)**. Your argument will rest on what the pharmacists said about their own practice, and your reader should be able to check the coding against the transcripts.

Leave the theoretical lens blank. It does nothing under inductive coding, and typing into it would create a false impression on your configuration table later.

Press **Continue**.

---

## Step 3. Model and keys

Select **Anthropic (Claude)**, which now shows `— Ready`. Leave the model at its default of `claude-sonnet-5`. Leave the key field blank, because you are keeping the saved key.

Press **Test key** once more with this model selected. The earlier test in Settings used the provider's default, and this one confirms the exact model.

Press **Continue**. Your project is now created and appears on the Projects list.

---

## Step 4. Data

Select all eight transcripts at once in the file chooser. They upload one after another. They are documents rather than recordings, so the text is extracted immediately and each row reaches `ready` without a transcription wait.

The rows read like this.

```
pharmacist_01.docx  · text · 38k chars     [ready]  Remove
pharmacist_02.docx  · text · 41k chars     [ready]  Remove
...
```

No group label field appears, because group labels belong to content analysis.

Check the character counts before you continue. A transcript showing far fewer characters than its neighbors usually means the document held its content in a text box or a header, which the extractor does not read. Find that now rather than at the first checkpoint.

Press **Continue**.

---

## Step 5. Review and run

The summary line reads `Thematic Analysis · anthropic/claude-sonnet-5 · 8 sources (304k characters)`.

The estimate box shows roughly `$1.06`, from about `202k` input tokens and `30k` output tokens. Follow the arithmetic in [The Wizard](02-the-wizard.md#how-the-estimate-is-calculated). Three hundred and four thousand characters becomes seventy-six thousand tokens. That figure is multiplied by the thematic factor of 2.4 and increased by twenty thousand for prompt overhead, with output assumed at fifteen percent.

Beneath the estimate the checkpoints are named. They are the review of initial codes and the review of themes.

Press **Run analysis**.

---

## The run begins

The Run screen opens. The Pipeline card marks Familiarization as current, and the Progress card shows `Familiarization: pharmacist_01.docx (0/8)`.

Familiarization takes eight calls, one per source. Initial coding follows and takes sixteen, because each thirty-eight-thousand-character transcript splits into two segments of twenty-four thousand characters at paragraph boundaries. The progress detail reads `Coding pharmacist_03.docx (part 2)` as the stage works.

You can close the browser here. The run continues in the server process, and reopening the run from the project page shows you where it reached.

---

## Checkpoint one: review initial codes

The run status changes to `awaiting review`, and an amber panel appears carrying sixty-one initial codes.

Work through them in four passes.

**The merge pass comes first.** Sixty-one codes on eight transcripts is more than your data hold. The surplus is duplication rather than richness, because the AI coder sees at most one hundred and twenty existing codes when coding each segment, and near-synonyms accumulate.

Set the sort to **Fewest excerpts first (merge candidates)**. The thin end of the list rises to the top, and the duplicates are mostly there. Pairs such as `worrying about overstepping` and `fearing overreach into prescribing` name the same thing, and so do three separate codes about the prescriber's authority. Tick all three, choose the best-named of them from **merge all into…**, and press **Merge**. Each merged row dims and prints where it is going, and its excerpts will move to the target.

Nine merges in four batches bring the list from sixty-one to fifty-two. The counter in the toolbar reads `61 codes · 61 shown · 9 to merge` while you work.

**The evidence pass comes second.** Click any code whose name is surprising, appealing, or suspiciously neat, and its full evidence opens beside the list. `Rationing candor` sounds like a finding, and it rests on two excerpts. Reading both shows that one is a pharmacist describing time pressure rather than any decision about candor. Rename the code to `Shortening the conversation under time pressure` and rewrite the definition to match. That rename flags the code as researcher-edited, and nothing downstream will overwrite it.

**The document pass comes third.** Follow **open in document ↗** on an excerpt, for two or three of the codes your argument will lean on. The transcript opens in a new tab with that passage highlighted and the rest of the document's coding shaded around it, so you can read the quote in its own paragraph. One excerpt under `Guarding the relationship with the prescriber` turns out to be a pharmacist describing a good working relationship rather than guarding anything. Note that code for a definition rewrite when you return.

Your merges and renames are all still staged when you come back to the tab. You lose nothing by leaving the page.

**The absence pass comes fourth.** Ask what your own reading of these transcripts found that the list does not show. Two pharmacists described consulting a colleague before raising the subject, and no code names it. Press **+ Add a code**, name it `Seeking a second opinion before raising it`, and write a definition.

Be clear-eyed about what that addition does at this checkpoint. It carries no excerpts and cannot be given any. It will be passed to theme construction and may be claimed by a theme, and it will appear in your report with no evidence beneath it. It records that you saw something the AI coder missed. You will have to evidence the concept yourself from the transcripts if it matters to your paper.

Press **Approve and continue**. The run resumes.

---

## Between the checkpoints

Theme construction runs as a single call over the fifty-three surviving codes, and returns six candidate themes. The theme review stage then runs a second call in which the AI model criticizes its own themes against sample extracts, rating coherence and distinctness and recommending an action for each.

Two calls, a minute or two, and the panel reappears.

---

## Checkpoint two: review themes

Six candidate themes appear, each with its definition, its excerpt count, and the phase-four critique beneath it. Clicking a theme opens all of its evidence beside the list, with each excerpt labeled by the initial code it came from.

```
Guarding the relationship with the prescriber            [ 47 excerpts ]
Model's own critique: coherence strong, distinctness strong —
recommends keep.

Time as the limiting condition                           [ 31 excerpts ]
Model's own critique: coherence adequate, distinctness weak —
recommends merge. Overlaps substantially with "Working inside
the appointment structure".
```

Read the critique as a second opinion rather than an instruction. It came from the same AI model that built the themes, and from a sample of extracts rather than the full evidence. Open the theme and read the evidence yourself wherever the critique flags a weakness.

The critique is right about the overlap here. Opening both themes shows the same four initial codes doing the work in each. Tick `Time as the limiting condition`, choose `Working inside the appointment structure` as the target, and merge. The child codes move across, so the evidence follows.

A fourth theme carries a recommendation to split, and the panel offers no split control. Leave the theme whole. Deleting it in order to split it would orphan its codes into an `Uncategorized` block. You can draw the two halves out in your own writing, where the evidence is all still visible under one heading.

Now decide about naming, because this checkpoint governs the next stage. The phase-five stage rewrites the name and definition of every theme you leave untouched, and leaves untouched every theme you edit. Two of the five remaining themes carry names that already say what you want. Edit those two now to lock them, and leave the other three for the AI model to name.

Press **Approve and continue**.

---

## The report

Defining and naming runs, the narrative is written, and the run reaches `completed`. A green card offers **Open report** and **Download .docx**.

Your report opens with a **Sources** section listing all eight transcripts as buttons, each carrying the number of excerpts drawn from it. Read those counts before anything else. Seven transcripts contributed between thirty and fifty excerpts. `pharmacist_06.docx` contributed nine, which is worth a look.

Below that come the four narrative sections. Read them as a draft grounded in the structure you approved, rather than as a findings section. The writing is generated, and the analysis is yours.

Scroll to **Evidence: Themes → Codes → Excerpts** and open the first theme. The initial codes appear beneath it, each with its excerpts. Each excerpt carries the AI coder's one-sentence memo, the source filename, and a **view in coded document** link.

---

## The verification that makes this an analysis rather than an output

Press the `pharmacist_06.docx` button in the Sources section. The transcript opens in the coded-source reader, with its nine coded passages highlighted and everything else plain.

The reason for the low count becomes visible quickly. The header reads `9 coded spans · 7 codes · 6% of text coded`. The minimap shows marks clustered in the first fifth of the document and nothing after. Scrolling confirms that the interview turns after twenty minutes to a long account of a dispensing-software migration, which bears on nothing in your research question. That is a finding about the interview rather than a fault in the coding, and it belongs in your notes.

Now do the same for a transcript that coded heavily. Open `pharmacist_02.docx` and make three passes.

Read the unmarked stretches first, ignoring the highlights. This is the check nothing else in QualiLens supports. One unmarked paragraph describes a pharmacist rehearsing the conversation on the way to work. That is exactly the sort of anticipatory work your study is about, and no code caught it. Note it, because this is the kind of absence that changes a paper.

Open two or three of the deeper amber passages, where more than one code overlaps. The inspector names each code on the passage. One sentence carries both `Guarding the relationship with the prescriber` and `Deferring to the prescriber`. Reading it shows these are two names for one idea. That is a merge you missed at the checkpoint, and you can still report it honestly as a limitation.

Isolate the theme's most important code in the panel, and step through every one of its passages with **next ›**. Eleven passages, read in the order the pharmacist said them, will tell you whether the code holds together.

Finally, check the **Not located in the text** panel. Two excerpts sit there for this document, which is ordinary. Read both. Find the real sentence in the transcript and quote that instead, if either excerpt is a quotation you intend to publish.

Fifteen minutes across two transcripts is the difference between a reviewed coding and an unreviewed one. The reader logs none of it, so write down what you did.

---

## The audit trail

The **Audit Trail** section at the foot of your report records the number of logged events, the two checkpoints and their resolution, and the model usage. That usage figure is what was actually billed. Compare it against the estimate of a dollar and six cents to calibrate your expectations for the next study.

---

## What to write down while it is fresh

Your report records that checkpoints were resolved, and the event log records each individual edit. Neither records why. The reader records nothing at all.

Note six things before you close the browser. Note the nine merges you made at the first checkpoint and why you made them. Note the code you added and what you saw that prompted it. Note the theme merge you made at the second checkpoint, and the split recommendation you declined. Note which documents you read in the reader and what the uncoded stretches showed. Note the overlapping codes you found there. And note how many excerpts you checked in place, along with the two that could not be located.

Those notes, plus the configuration table on your project page, plus the audit appendix, are your methods section.

---

## If something had gone wrong

The red box would have named the stage and the error, had the run failed at initial coding on the sixth transcript, and **Resume from this stage** would have restarted it. Familiarization would not repeat. The five transcripts already coded would not repeat. The run would pick up at the segment that failed.

The next launch would have marked the run as interrupted and offered the same Resume, had the app been stopped mid-run.

**Cancel run** would have stopped the run before the next call, had the analysis been visibly wrong at the first checkpoint because your research question was pulling the AI coder toward the wrong material. Cancellation is final. The remedy is a new project with a better question, and that costs the coding again. This is the argument for piloting on one transcript before you commit eight.
