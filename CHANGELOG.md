<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to QualiLens. Release tags are semantic versions; each
release also carries a build stamp (`build YYYY.MM.DD-HHMM`) that the in-app
update check compares against your installation.

## 1.13.0 — 2026-11-16

- QualiLens has a Quit link. It is at the right end of the bar at the top,
  on every screen. Until now the only way to stop the app was Ctrl-C in its
  Terminal window, and an app forgotten there kept running. Quit asks
  first. If a run is in progress or a recording is being transcribed, it
  says that quitting interrupts them. You can resume the run, or retry the
  recording, when you start the app again. The page then says the app has
  stopped and how to start it again. Starting it again opens a new tab,
  and the old one says so.
- The page a tab shows when it is not signed in is easier to read. It is
  headed "This tab is not signed in" and says what to do in short steps.
- Stopping the launcher stops QualiLens. Since 1.12.0, a stop sent to the
  launcher alone, such as `kill`, ended the launcher and left the app
  running in the background. Ctrl-C and closing the Terminal window were
  not affected. The launcher now passes the stop on and waits until the app
  has stopped.

## 1.12.1 — 2026-11-15

- Other accounts on a shared computer can no longer reach your projects
  through another program your browser visits. Signing a browser in also
  left the session token in a cookie, and a browser sends a cookie to any
  program on the computer that serves pages, on whatever port. On a shared
  Mac or a lab server, another account running such a program could collect
  the token when your browser opened its page, and then read your projects
  and use your keys. The app no longer sets the cookie. The browser keeps
  the token where only QualiLens's own pages can read it, and the tabs of a
  signed-in browser can use the app as before. The Word report, the audit
  log, and the checkpoint spreadsheet download as before.
- Deleting a source removes only that source's uploaded file. A delete
  request typed by hand, outside the app, could name a pattern in place of
  a source and remove the original documents and recordings of all
  projects. The interface never sent such a request, and the text QualiLens
  had read from the files stayed in the database.
- A page served by another site, or by another program on this computer,
  can no longer show QualiLens inside itself, where a click meant for that
  page could land on the app. The app's own page also loads nothing but
  what ships with QualiLens. Both are precautions; no fault was found in
  either place.
- The launcher removes its temporary folder when the app stops only if the
  folder is one it made.

## 1.12.0 — 2026-11-15

- QualiLens starts again by itself after an update. Download and install,
  or an update from a downloaded zip, now ends with the app restarting on
  the new build in the same tab, still signed in, with nothing to do in
  Terminal. Before, the app stopped, and you started it again yourself,
  which opened a second tab. The first update into this release still works
  the old way, because the launcher that runs it is the one already
  installed.
- The page shown while an update installs no longer offers a Reload button.
  Reloading before the new build was up signed the tab out, and the page
  already reloads by itself.

## 1.11.1 — 2026-11-15

- The review screens say things more plainly. Their notes, the
  instructions at the top of each review, and the confirmation dialogs
  use shorter sentences, one point at a time, like the rest of the app.
- The manual's chapter on checkpoints is rewritten the same way, with the
  walkthrough and the other passages that describe the review screens.

## 1.11.0 — 2026-11-15

- The review screens put the evidence beside the decision. Each code shows
  its first quote, with its source and a link to the passage in the
  document, and Show all brings up the rest in place. A category or theme
  lists the codes it holds. You no longer open codes one at a time in a
  side panel to see what they rest on.
- You can record why you decided. A note on any code, category, weak
  assignment, or paper goes into the audit trail beside the decision, and
  a note on something you kept unchanged is recorded as well.
- Each review shows what approving will do. A staged decision is written
  on the item it changes, a tally beside the list counts the decisions,
  and the Approve button gives their number.
- A review of codes, categories, or themes shows how much of the
  least-coded transcript carries no code, with a link to that text in the
  coded-source reader.
- Long code lists are quicker to work through. A review of more than 40
  codes opens with one line per code, any code can be merged from its own
  row, and single keys move through the list and rename, merge, delete, or
  add a note to the code you are on.
- The core category review shows the model's theoretical gaps, which the
  report reproduces as its Theoretical Sampling Recommendations. You can
  now edit them, leave them out, or add to them before they reach the
  report. The review also shows the figure the report will draw.
- The charting review shows each weak assignment beside its framework
  code's definition, so the passage is judged against what the code means.
  A candidate code left undecided is discarded, and the review now says so
  before you approve.
- The extraction review opens as a table of papers by field, with the
  number of quotes behind each summary, so a summary with no quote behind
  it stands out. An opened paper shows each summary beside its quotes.
  Excluding a paper asks for a reason, which is recorded with the
  exclusion.
- A review that was already waiting when you update opens in the new
  screens. A few details, such as the codes a category holds, appear only
  in reviews opened after the update.
- Quotes in the review screens read whole. A word that a PDF broke across
  a line showed as "decom- poses" and now reads "decomposes", and a word
  the paper hyphenates, such as "worst-case", keeps its hyphen. The stored
  quote, the spreadsheet, and the audit export are unchanged.
- Confirmations use the app's own dialog instead of the browser's, with
  buttons named for what they do. When an action cannot be undone, such as
  deleting a project, the safe button is the one selected.
- In the extraction review, the column names stay with the table and
  appear again below an opened paper, so the papers after it are labeled.
- The top bar fits a narrow window. At 390 pixels wide it ran past the
  edge of the screen and cut off New analysis.
- Word reports list QualiLens as their author. Word's document properties
  showed python-docx, the library that writes them.
- The manual and the instructions at the top of each review describe the
  new screens.

## 1.10.2 — 2026-11-04

- The Mistral list offers `mistral-large-4` as the default, with
  `mistral-small-latest`. Mistral deprecated Large 3 and Medium 3.5 on
  31 October 2026 and retires them on 30 April 2027, naming Large 4 as the
  replacement for both; `mistral-large-latest` and `mistral-medium-latest`
  still answer with the deprecated models, so they leave the list. A project
  that uses either keeps running until the retirement, priced as before.
- Mistral Large 4 reasons before it answers and returns that reasoning
  beside the answer, in a shape QualiLens could not read: a run on it
  failed before it began. QualiLens now reads the answer, leaves room in
  the token budget for the reasoning, and records the reasoning tokens in
  the audit trail as it does for Gemini. The same failure would have
  reached the projects on `mistral-large-latest` the day Mistral pointed
  that alias at Large 4.
- `gemini-4-argon`, Google's current flagship, joins the Google list,
  marked paid tier only. The cost estimate prices it at Google's rate from
  1 December 2026 ($4.00 and $20.00 per million tokens; Google charges half
  until 30 November).
- From 1 December 2026 Google answers `gemini-2.5-pro` with
  `gemini-3.8-flash` and `gemini-2.5-flash` with `gemini-3.5-flash-lite`,
  billed at their rates. QualiLens no longer sets a temperature on calls to
  those two ids, which the Gemini 3 models do not take, so a project on
  either keeps running after the change, and its report names the model
  that answered.
- Updated pypdf to 6.21.4, which fixes seven flaws published since the
  last release; pypdf reads the PDFs you upload.
- Internal: the interface is built with vite 8.3.5, and the test workflow
  runs on Node 24 with current GitHub actions.

## 1.10.1 — 2026-10-24

- The Anthropic list offers the 5.5 generation: `claude-sonnet-5-5` is the
  default, with `claude-opus-5-5` and `claude-haiku-5-5`. `claude-sonnet-5`,
  `claude-opus-5` and `claude-haiku-4-5-20251001` stay available under
  Custom model id and keep running in the projects that use them. The cost
  estimate now prices each Anthropic model at its own rate; it had used one
  rate for all three, which overstated Sonnet 5 and Haiku 4.5 and
  understated Opus 5.
- `gpt-4.1` and `gpt-4o` have been removed from the OpenAI list. OpenAI
  deprecated them on 14 October 2026 and shuts them down on 14 January
  2027; a project that uses either keeps running until then. `gpt-6-luna`,
  the replacement OpenAI names, joins `gpt-6.1-sol`.
- The estimate's Mistral prices follow Mistral's current list: Large at
  $0.50 and $1.50 per million tokens, with Medium and Small priced
  separately.
- QualiLens installs on Python 3.15, which Homebrew and python.org now
  install by default. The pinned chart library had no build for 3.15, so a
  first launch on such a computer stopped while installing dependencies and
  blamed the internet connection. The test suite now also runs on 3.15.
- Updated pypdf to 6.21.2, Pillow to 13.0.0 and certifi to 2026.10.23, which
  fix flaws published since the last release; pypdf reads the PDFs you
  upload.
- Audio and video are transcribed with OpenAI's `gpt-transcribe` model.
  OpenAI has deprecated `whisper-1` and shuts it down on 26 February 2027.
  The new model costs less per minute and, like Whisper, does not label
  speakers.
- When a provider's safety system declines to answer a segment, the run
  stops with a message that says so, carries the provider's explanation when
  it gives one, and suggests resuming once or using another provider. Such
  an answer used to be reported as an empty reply with advice about token
  limits, and a reply cut short by OpenAI's content filter could reach the
  JSON reader as a partial answer.
- The first launch no longer reports that the dependencies changed right
  after installing them.
- README names all five methods, CITATION.cff carries the Zenodo DOI, and
  two sentences describe what the coded-source reader shows instead of
  calling it the fastest way.

## 1.10.0 — 2026-10-09

- Reports now list the model that actually answered each call, and
  indicate when a provider answered with a different model from the one
  the project chose. Each call records the model the provider reports, and
  the report header, the configuration section, and the audit appendix
  indicate any difference, in the app and in the Word report, with an
  amber notice in the app. A dated snapshot, such as OpenAI's
  `gpt-5.1-2025-11-13` for `gpt-5.1`, counts as the model itself. Calls
  logged before this release recorded no answering model, and the audit
  appendix counts them separately under the model requested.
- `gemini-3.7-flash` has been removed from the wizard's list of Google
  models. Google has deprecated it and now answers requests for it with
  `gemini-3.8-flash` at the same price, so the two choices had become one
  model. A project that already uses 3.7 keeps running on 3.8, and its
  report lists 3.8 for calls made after this update. For calls made
  earlier the report lists only 3.7, so a methods section should indicate
  that calls made since Google's change ran on 3.8.
- OpenAI's default is now `gpt-6.1-sol`, and `gpt-5.1` and `gpt-5` have
  been removed from the list. OpenAI has deprecated both, and it shuts down `gpt-5` on
  11 December 2026 and `gpt-5.1` on 1 April 2027. A project that already
  uses either keeps running until that date. The cost estimate prices
  `gpt-6.1-sol` at $2.00 and $10.00 per million tokens, `gpt-4.1` and
  `gpt-4o` at their own prices, and `gpt-5.1` and `gpt-5` at $1.25 and
  $10.00 for projects that still use them.

## 1.9.0 — 2026-10-08

- Other accounts on a shared computer can no longer reach your projects
  through the app. The page the app served handed its session token to
  whoever asked for it, and a connection to the app does not say which
  account on the computer made it, so on a shared Mac or a lab server
  another account could read your projects and use your keys. The launcher
  now opens a launch page readable by your account only, which signs your
  browser in, and the app gives the token to no one else. A tab opened by
  address in a browser that has not been signed in shows how to open
  QualiLens, and the launcher's Terminal window names the launch page.
- Word reports and checkpoint spreadsheets no longer fail on control
  characters. A form feed in a source, which PDF-to-text tools write at
  every page break, made the Word export and the checkpoint spreadsheet
  fail for the whole run. Such characters are now cleaned when a source is
  added and again when either file is written, which covers sources added
  before this release.
- QualiLens handles untrusted files more cautiously. A .docx or a
  checkpoint workbook that would unpack to an implausible size is refused
  before it is opened, and ffmpeg may read a recording only from disk,
  never from the network.
- QualiLens now uses pypdf 6.19.0, which fixes eight published flaws that
  let a crafted PDF make text extraction run for a very long time or
  exhaust memory.
- Dependencies are pinned with hashes. Python packages, including the ones
  QualiLens uses indirectly, are installed at fixed versions and checked
  against the hash of the published file, and the launcher builds the
  interface of a GitHub clone with `npm ci`.
- Intel Macs are not supported. A library QualiLens needs for encryption
  and for checking update signatures stopped publishing builds for Intel
  Macs, so installation there has failed since 1.5.0 with a misleading
  message. The launcher now says so plainly, and it tells someone running
  an Intel Python on an Apple-silicon Mac how to fix that.
- Settings links to What's New. Beside the version in the Application card,
  **What's new** opens the website's page of what each release changed, so
  the record is one click from the app.

## 1.8.2 — 2026-09-30

- Gemini works again for new Google projects. Google now offers the
  Gemini 2.5 models only to projects that used them before and refuses them
  to others as "no longer available to new users"; the catalog offered only
  those models, so a new Google key failed at Test and at the first call of
  a run. The catalog now offers `gemini-3.6-flash` (the default),
  `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.5-flash-lite`, and
  `gemini-3.1-pro-preview`, with per-model prices; the wizard marks the
  last `— paid tier only`, since a free key has no quota for it. A project
  already set to a 2.5 model keeps it, and its estimate keeps 2.5 prices.
- Check models catches a model Google lists but refuses. Google's model
  list still includes the 2.5 models for projects that cannot use them, so
  the check reported them as live. For Google it now also asks about each
  catalog model through Google's free token-counting endpoint, marks a
  refused model ✗ with Google's reason, and the wizard disables it. Continue
  on the wizard's model step runs the same check before it creates the
  project, whenever a key was just typed or no check has finished.
- Gemini errors say what happened. A refused model says so and names the
  model Google suggests, instead of suggesting it was retired, and says
  when that suggestion is paid-only. A model with no free-tier quota —
  `gemini-3.1-pro-preview` on a free key — fails at once with the steps to
  Google's paid tier, instead of after a minute of retries; a spent daily
  quota says when it resets; a paid project is pointed to a higher tier
  rather than to billing; and a per-minute limit waits as long as Google
  asks. An answer Gemini stopped for safety or recitation is refused as
  incomplete rather than parsed.
- Gemini token counts include thinking. Gemini bills the tokens it spends
  thinking as output but reports them apart from the answer, and the Run
  screen, the report, and the audit log counted only the answer — a
  sixfold undercount on one call we measured. They now count both, and each
  call's audit entry records the thinking share. Reports from earlier
  Gemini runs understate output tokens for the same reason.
- Gemini 3 models run at Google's default temperature, as Google advises,
  and the audit log says so; the older Gemini models keep the temperature
  QualiLens sets.
- The wizard's custom-model field no longer suggests Google's speech,
  image, music, robotics, and agent models, which cannot do a coding pass.
- The manual and the wizard describe Google's free tier. Outside the EEA,
  Switzerland, and the UK, on a key whose project is not on Google's paid
  tier, Google may use what you send to improve its products and human
  reviewers may read it, so it is unsuitable for confidential data.

## 1.8.1 — 2026-09-24

- Check for updates now says what changed. When a newer release exists,
  the first paragraph of its release notes appears under the result in
  Settings, so the decision to install can be made there; the release page
  link carries the rest. The notes ride along with the check's own answer,
  so the privacy claim is unchanged: one request to GitHub, only when you
  press the button.
- The website has a What's New page, written from this changelog, so what
  each release changed is readable without visiting GitHub.

## 1.8.0 — 2026-09-24

- API keys are encrypted at rest. Each saved key is stored as ciphertext,
  and the secret that unlocks it is a small file outside the data folder —
  `~/Library/Application Support/QualiLens/secret.key` on macOS,
  `~/.config/qualilens/secret.key` on Linux and WSL, or wherever
  `QUALILENS_SECRET_FILE` points — created the first time it is needed and
  readable by your account only. A synced, backed-up, or copied database
  therefore carries no usable key. Keys saved by an earlier build are
  encrypted in place on the first start, and the app says so. A database
  opened on another computer, or after the secret was replaced, shows its
  keys as unreadable in Settings with the reason; paste them again or
  Remove them. Settings names the secret file beside the data folder and
  warns when either sits in a cloud-synced directory.
- The data folder is readable by your account only, and so are the
  database and its sidecar files, set at every start. Deleted and
  overwritten content is zeroed inside the database rather than left in
  freed space, and Remove compacts the file, so a removed key leaves it
  rather than lingering.
- The manual's Getting Started, Troubleshooting, and Data, Privacy, and
  Governance chapters say what the encryption protects against and what it
  does not: the participant data remain plain text, and someone using your
  own account on your own computer can read both files.

## 1.7.1 — 2026-09-03

- An installation updated to 1.7.0 by an older build showed only its build
  stamp: that build's updater refused the new `RELEASE` file. The version
  now also rides inside the interface's `index.html`, which every updater
  accepts, so the next update names its version whatever it came from.
  "Updates checked" says "today" rather than "0 days ago".

## 1.7.0 — 2026-09-03

- The version you are running shows in the footer of every page and on the
  Application card in Settings, with the build stamp beside it, and **Check
  for updates** names it as well. Bundles now carry a `RELEASE` file that
  `package.sh` writes from the changelog's top entry.
- A reminder to check for updates. When the build you are running is a
  month or more old and no check has been made in two weeks, the Projects
  page says so in one line, once per launch, with the path to the check;
  **Dismiss** hides it until the next start. It is worked out on your
  computer from the build's date and makes no request, so the privacy
  claim is unchanged. The Application card in Settings records when you
  last checked.
- A polish pass over the interface. Settings offers only the controls a
  state allows and keeps its policy text behind "How updates work" and
  "Moving the folder"; the project page names settings by the wizard's
  own question labels, methods by name, dates without seconds, and sizes
  as words rather than "0k chars"; the report writes Yes and No where it
  wrote true and false; the wizard's method cards say how many stages and
  reviews a method has instead of spelling out the pipeline; Delete on a
  project card is quiet until hovered. The content-analysis report no
  longer prints raw data structures into its prose, and its frequency
  figures appear once, in the table. A contrast pass on the palette: darker
  ink, cards lifted by a soft shadow, and the mark's violet as the single
  accent for the primary action and the active step.
- Settings is one screen: the providers as a single panel of rows, each with
  its status, its key hint, and its actions, and a key editor that opens in
  the row; Data and Application side by side as two compact panels of facts.
  Page titles are larger and section labels are small tracked eyebrows.
  The same structure carries to Projects (a panel of rows, each with a
  glyph for its method), the project page (runs and sources as rows, the
  configuration as facts), the wizard's method cards (the glyphs), and the
  run page. A checkout that was never packaged reports the last released
  version with a plus sign, "1.6.3+", beside its build stamp.

## 1.6.3 — 2026-09-03

- Security review of 2026-09-03, five fixes. Checkpoint spreadsheets write
  every cell as text, so a name or quote beginning with `=` can no longer
  become a live formula when Excel opens the sheet. The local guard now
  requires the request's origin to equal the app's own origin exactly
  (scheme, host, and port), closing the route by which a page served by
  another program on this computer, on another port, could reach the API
  with the session cookie. Uploads stream to disk under a bound per kind
  (200 MB documents, 2 GB audio, 8 GB video) and document parsing runs off
  the server's event loop, so a large PDF no longer freezes the interface.
  A signed bundle older than the installed build is refused as a rollback —
  the zip path asks first, the GitHub path never installs one. The release
  page link is shown only when it is a GitHub page of the QualiLens
  repository.

## 1.6.2 — 2026-09-02

- The manual now shares the interface's register and type: the same ground,
  ink, and spacing, Inter for headings and navigation, JetBrains Mono for
  commands, a serif for the text. The typefaces ship with the app under
  `frontend/public/fonts/` with their licence (SIL OFL 1.1), noted in NOTICE.

## 1.6.1 — 2026-09-02

- Settings: "Where your data live".

## 1.6.0 — 2026-09-02

- A checkpoint can be worked in a spreadsheet. **Download as spreadsheet**
  saves the code review (or the literature-synthesis extraction table) as
  an `.xlsx` workbook with a column for your action, one for a merge
  target, and one for notes; **Upload spreadsheet** reads it back and loads
  its decisions into the review screen for you to check before approving.
  Rows are matched by id, an unknown row is listed rather than guessed at,
  a code with no row is unchanged, and a workbook from another checkpoint is
  refused. Notes enter the audit trail beside the decisions they explain,
  and the workbook itself is kept with the run and named in the audit
  export. Definition boxes on the review screen now grow with their text.
- A quieter interface: a cool near-white ground, one ink for text and the
  primary action, colour kept for done, waiting, and wrong. The app now
  ships its own type — Inter for the interface and JetBrains Mono for model
  ids, build stamps, and the audit log — so it looks the same on Mac,
  Windows, and Linux, and fetches nothing to do so. Figures follow the same
  palette; the thematic map's connectors no longer cross code boxes.
- After an update, the page waits for the new build and reconnects on its
  own once you have started the app again; nothing to close or reopen. A
  tab left open across any restart now reloads itself to pick up the new
  session, instead of showing a token error.
- The launcher checks the port before any other work and, when it is taken,
  says what holds it: for a QualiLens server, the build it is running, when
  it started, and the exact command to stop it. A server left running in a
  forgotten terminal keeps serving the build it started with, so this is how
  you learn that the app in your browser is older than the folder. The
  served page and `/api/meta` now carry the running build.
- Test runs no longer re-stamp the folder's `VERSION`.

## 1.5.0 — 2026-09-02

Security and evidence-integrity release. Updating is recommended.

- Security hardening of the local server and of the in-app updater. Update
  bundles are now signed, and only signed bundles install; an update is
  refused while a run is executing or awaiting review. A tab left open across
  an app restart now asks you to reload the page.
- Excerpts state their own status: an excerpt whose quote cannot be found
  verbatim in its source is marked *unverified* in the report and listed
  outside quotation marks in the Word export; the audit appendix counts
  located and unverified excerpts. Quote location tolerates case, ligatures,
  soft hyphens, and PDF line-break hyphenation, and searches the segment the
  model was reading first, so a recurring phrase is highlighted where it was
  coded — on a 26-paper corpus this recovered about a quarter of the quotes
  that were previously discarded.
- Literature synthesis: the extractor now separates a paper's own findings
  from findings it attributes to other work (shown on the extraction review,
  not offered to the synthesis) and skips reference lists; the citation
  guard recognises names in any script, ignores stopwords from filename
  labels, and requires the year to match.
- Reports now carry the configuration the run was frozen with, the models
  that answered, and a per-checkpoint summary of decisions; the audit trail
  exports as JSON from the run screen. A run freezes its provider, model,
  and setup answers at start, so a resumed or branched run keeps its model.
- Thematic analysis defines and names themes before the theme review, so the
  names in the report are the ones you approved. Framework analysis charts a
  promoted emergent code across the sources before the matrix. Content
  analysis samples the opening, middle, and end of each source for the
  codebook, reports rates per 10,000 characters beside counts, and names the
  unit it counts. A confidence the model did not give is recorded as missing,
  not as 0.8. Findings narratives pass a quote guard.
- Grouping of very large code sets runs in chunks and consolidates, instead
  of failing on the output limit. The coder is shown up to 300 codes for
  reuse (was 120).
- `QUALILENS_DATA_DIR` moves projects, uploads, and keys out of the app
  folder; the app warns at startup and in Settings when the data folder sits
  inside a cloud-synced directory. The write-ahead log is folded into the
  database at stage boundaries and checkpoints.
- Text ingestion no longer guesses UTF-16 without a byte-order mark, reads
  Word tables in document order with text boxes, refuses `.rtf`, and
  converts `.aac` for transcription when ffmpeg is present.
- `package.sh` rebuilds the interface when its sources have changed (a
  fingerprint is stamped into the build and checked at startup and in the
  packaging test) and rebuilds the manual as part of packaging. Release
  1.4.0 had shipped an interface built before its latest sources.

## 1.4.0 — 2026-08-31

- After a successful update, Settings shows a full-screen confirmation page
  instead of a small notice that was easy to miss.
- The launcher (`run.sh`) now checks disk space, verifies Node 18+, shows
  npm output during first-time setup, and detects a port already in use.
- The QualiLens chevron logo now appears in the app's navigation bar.
- Bug fixes and internal improvements.

## 1.3.0 — 2026-08-30

- The launcher checks disk space and Node 18+, shows npm output on first run,
  and detects a port already in use. Chevron logo. Manual updates; the
  release ZIP needs only Python. (Entry reconstructed from the working log;
  1.1 and 1.2 were never published.)

## 1.0.0 — 2026-08-27

Initial public release.

- Five analysis methods, each a staged pipeline with researcher checkpoints:
  grounded theory, reflexive thematic analysis, qualitative content analysis,
  framework/deductive coding, and corpus-grounded literature synthesis.
- Researcher-led by construction: runs pause at review checkpoints; your
  edits are final and are not overwritten by later automated stages;
  decisions are written to an audit trail the report reproduces.
- Provenance-first evidence: verbatim quotes with character offsets, a
  coded-source reader that draws the coding over each document in place, and
  page anchors for PDF sources.
- Literature synthesis cites only from the uploaded corpus — never from
  memory. Synthesis support must reference located extraction quotes by id;
  ungrounded support is dropped and logged, and a citation guard scans the
  generated text for citation-shaped strings matching no uploaded paper.
- Interactive report plus a formatted Word export, with method-appropriate
  figures that disclose truncation on their face — the grounded theory model
  drawn as a left-to-right paradigm flow.
- Any review a run has passed can be revisited: a branch carries everything
  up to that review into a new run and reopens it, leaving the original run
  and its report untouched.
- Four providers (Anthropic, OpenAI, Google, Mistral), an editable model
  catalog with a live model check, Whisper transcription for audio and
  video, cost estimation before a run, resumable runs that do not re-bill
  finished work, and honored cancellation.
- The app runs locally; data go only to the provider you chose. In-place
  updates from a downloaded bundle or, pull-only and on demand, from this
  repository's releases — the updater's allowlist leaves your projects,
  keys, and uploads untouched.
- A fifteen-plus-chapter user manual, shipped in the app.
