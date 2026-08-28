<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 11. Runs, Cancellation, and Recovery

A run is one execution of a method's pipeline over a project's sources. Starting the wizard's final step creates a run. **New run** on a project page creates another over the same configuration and the same data.

## The Run screen

The heading carries your project name. Beneath it, a line links back to the project, gives the time the run was created, and shows a status badge. Two cards sit below that line.

The **Pipeline** card lists every stage in order, with a marker showing which stages are done, which one is current, and which are still to come. Each stage is labeled either automated or your review, so you can see how many pauses remain.

The **Progress** card shows a bar and a detail line while a stage is running, for example `Coding interview_04.docx (7/23)`. It also shows the running total of model usage in calls and tokens, a **Cancel run** button, and the audit log.

The **audit log** streams the run's events as they happen, each with a timestamp. Stage boundaries, individual model calls with their purpose, your checkpoint decisions, dropped assignments, and errors all appear there. The screen keeps the recent history rather than the whole log. The complete record is kept in the database and summarized in your report's audit appendix.

The screen refreshes itself while the run is live, and it stops refreshing once the run reaches a final state. A completed run does not keep polling in the background.

## Run states

| Status | Meaning | What you can do |
|---|---|---|
| `running` | A stage is executing | Watch, or cancel. You may close the browser |
| `awaiting review` | A checkpoint is waiting for you | Approve and continue, or cancel |
| `completed` | Every stage finished and the report exists | Open the report, or export it |
| `failed` | A stage raised an error, or the app restarted mid-run | Resume, or leave it |
| `cancelled` | You cancelled | Start a new run, or branch from a review it passed |

## Closing the browser

Closing the browser or the tab does not affect a run. The pipeline executes inside the server process, and its state is written to the database as the run proceeds. The screen simply reads that state. Come back later and open the run from the project page.

Stopping the server with Ctrl-C does interrupt a run. The next launch handles that, as described below.

## Cancelling

**Cancel run** is available while a run is executing or waiting at a checkpoint. It asks you for confirmation, because cancellation is final.

Cancellation stops the run before the next model call, rather than at the next stage boundary. A stage in the middle of coding twenty sources therefore halts within one call rather than finishing all twenty. That is what makes cancellation useful for stopping your spend.

You cannot resume a cancelled run. The work already completed stays in the database, and the audit trail records the cancellation. To continue you have two paths. A new run begins at the first stage and pays again for everything. A branch from any review the cancelled run had passed carries the work before that review at no cost and reopens it — see [Revisiting a review you have already passed](11-runs-and-recovery.md#revisiting-a-review-you-have-already-passed) below.

Cancel when you have seen enough of the coding to know your setup is wrong. The money you save is the money that would have been spent on the rest of the corpus. Do not cancel a run that has merely failed. You can resume a failed run, and you cannot resume a cancelled one.

## Resuming a failed run

A failed run shows a red box naming the stage that failed and the error, with a **Resume from this stage** button.

Resuming restarts the pipeline at the stage that failed. Work already completed is preserved, and the resume skips it rather than paying for it again.

### What is preserved and what repeats

Resumption is fine-grained in the long stages and coarse in the short ones. That follows from how each stage is built.

| Stage type | On resume |
|---|---|
| Familiarization | Sources already summarized are skipped |
| Coding, initial coding, applying a codebook, charting | Each source segment already coded is skipped |
| Framework matrix | Each source row already summarized is skipped |
| Axial coding, theme construction, selective coding, codebook derivation | The stage's output is cleared and the single call is made again |

The pattern is that anything built from many calls resumes call by call, and anything built from one call is rebuilt. The second group repeats one call rather than a whole corpus. The cost of a resume is therefore bounded by the cost of the stage that failed, rather than by the cost of the run.

One consequence is worth naming. Rebuilding a single-call stage produces a genuinely new grouping rather than the previous one. Resume after axial coding fails, and the categories you get are not the categories the failed attempt would have produced. That is why the rebuild is clean rather than incremental, and it is why the pipeline pauses for your review immediately afterward.

## When the app restarts mid-run

No background thread survives if the server stops while a run is executing, whether by Ctrl-C, a crash, or your computer sleeping deeply enough to break the process. QualiLens detects this at the next startup and repairs the record, rather than leaving a run spinning forever.

A run still marked as running is marked failed, with the message that it was interrupted by an app restart, and the Resume button appears. A run marked as awaiting review whose checkpoint has gone missing is likewise marked failed, and resuming rebuilds the checkpoint from the current state. That case is rare, and it follows from stopping the app in the moment a checkpoint was being resolved. A source still marked as transcribing is marked as errored, with a message saying the transcription was interrupted, and the Retry button appears on it.

The instruction is the same in all three cases. Open the run or the source, and press Resume or Retry.

## Starting another run over the same project

The project page lists every run as a clickable row — click anywhere on it to open that run's screen. Each row carries the run's date, a line saying what it is doing or waiting for, and its status badge, and completed runs carry **Open report** and **Word** buttons right on the row, so a finished analysis is one click from its findings. **New run** starts a fresh one from the first stage.

A new run reuses your project's method, setup answers, provider, model, and sources. It starts from the first stage, with nothing carried over from previous runs. Codes, excerpts, checkpoints, and reports belong to the run that produced them. A project with three runs therefore holds three independent analyses of the same data, and you can compare them.

That comparison is the most useful thing a second run offers you. Run the same configuration twice and read the two theme sets against each other. This is the closest QualiLens comes to a stability check, and it costs a second full run to obtain.

## Revisiting a review you have already passed

Reviews are where your judgment enters the analysis, and judgment sometimes ripens late. You approve the open codes, see the categories they produced, and only then realize two codes should have been merged. The pipeline never reopens a resolved review in place — that would rewrite the record of what you decided — but it lets you branch.

On the Run screen, once the run is not actively executing, every review it has passed shows **↩ Revisit this review…** in the pipeline column (wait for a running run, or cancel it, to branch). Pressing it explains what will happen and asks you to confirm: a NEW run is created — not from scratch — carrying everything the run had at that point, including the coding, the evidence, and the earlier reviews you resolved, and it reopens that review for further decisions. The original run, its report, and its audit trail stay exactly as they are, so you can compare the two afterward.

Be precise about what "reopens" means, and the reopened panel says the same. The branch carries the run's state as it stood, **including the decisions you already made at that review**: you can rename further, merge further, delete further, and add — but a code you merged or deleted the first time, an excerpt you removed, or an emergent candidate you discarded does not come back, because the pipeline never invents a state that no run was actually in. When the decision you regret was destructive, branch at an EARLIER review where the material still existed, and let the stages between them run again.

Three more things to know before you branch. Stages after the revisited review run again on the new run, and bill again; work before it is carried over and costs nothing. Where the method codes *after* the review — content analysis applies its codebook after the codebook review — the branch re-codes from your revised decisions rather than keeping coding produced under the old ones, which is the point of branching. And the audit trails stay honest on both sides: each run records the branch, the carried-over reviews appear in the new run's record, and the money spent before the branch remains recorded on the source run.

Branching is how you explore an alternative reading without destroying the one you have. A cancelled run can be branched too — cancellation ends a run for good, but what it had produced up to any review it passed remains usable ground for a new one.

## What you cannot change once a run exists

Your method is fixed once any run exists for the project. QualiLens refuses to change it, because the change would leave you with a project whose history no longer matches its configuration.

You cannot delete sources while a run is executing or waiting at a checkpoint. QualiLens says so rather than removing evidence from underneath a live analysis. Cancel or finish the run first.

The setup answers, provider, and model have no edit screen after the wizard. The project page shows them as a read-only table. Create a new project and upload the sources again to analyze the same data under different settings.

## Reading the cost of a run

The Progress card shows the running total of calls and tokens, and your report's audit appendix records the final totals. Those numbers are what the providers billed, taken from their own responses. Trust them rather than the pre-run estimate.

Tokens spent on a call that failed are recorded too. A response refused for being truncated or empty was still billed, and QualiLens keeps it in the usage total rather than dropping it. Your audit trail therefore accounts for money actually spent, rather than for successful work only.
