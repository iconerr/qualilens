<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# 1. Getting Started

## What you need before the first launch

What you need on your computer depends on how you received it.

**If you received QualiLens as a zip bundle** (the file a colleague sends, or a release download), the interface is already built inside the bundle. You need only Python.

| Requirement | Why it is needed | How to check | How to install |
|---|---|---|---|
| Python 3.11 or later | Runs the backend, the analysis pipelines, and the local database | `python3 --version` | `brew install python@3.12` on macOS, or download from python.org |
| ffmpeg (optional) | Extracts audio from video files and splits long recordings for transcription | `ffmpeg -version` | `brew install ffmpeg` on macOS |

**If you cloned the GitHub repository**, the interface must be built once on your machine. You need Node in addition to Python.

| Requirement | Why it is needed | How to check | How to install |
|---|---|---|---|
| Python 3.11 or later | Runs the backend, the analysis pipelines, and the local database | `python3 --version` | `brew install python@3.12` on macOS, or download from python.org |
| Node 18 or later and npm | Builds the browser interface once, on the first launch only | `node -v` | Download from nodejs.org |
| ffmpeg (optional) | Extracts audio from video files and splits long recordings for transcription | `ffmpeg -version` | `brew install ffmpeg` on macOS |

The launcher detects which situation you are in and tells you what is missing. If Node is absent and the interface has not been built, the error message names what to install and where.

You can skip ffmpeg if you will only ever upload documents and audio files under roughly 24 MB. You will need ffmpeg once you upload a video, or an audio file too large for the transcription service to accept in one piece. The Settings screen tells you at any time whether QualiLens can see ffmpeg on your computer.

You also need an API key from at least one AI model provider. Keys are covered below.

## Starting the app

Open a terminal in the QualiLens folder and run the launcher.

```bash
./run.sh
```

The first run creates a Python environment, installs the backend dependencies, and builds the interface. Expect that to take a minute or two. Every launch after the first is much faster, because the launcher checks for the built artifacts and skips the steps already done. Once the server is up, the launcher prints the address and opens your browser at it.

```
QualiLens running at http://127.0.0.1:8765  (Ctrl-C to stop)
```

Stop the app with Ctrl-C in the terminal where it is running. Closing the browser tab does not stop it, and neither does minimising or forgetting the terminal window: the server keeps running until you stop it or the computer restarts. Closing the browser during a long analysis stage is also safe, because the run continues in the background and its state is saved as the run proceeds.

Stop the app before updating it, and after an update stop any older copy that is still running: a server keeps the code it loaded when it started, so an old one left running keeps serving the old app while the folder holds the new one. The launcher notices this and says which build holds the port, when it started, and how to stop it; see [Troubleshooting](13-troubleshooting.md#starting-the-app).

### Changing the port

The app listens on port 8765. The launcher checks the port first, before any other work, and refuses to start if something else on your computer already holds it — naming the process, and, when it is a QualiLens server, the build it is running. Either stop that process, or start QualiLens on a different port.

```bash
QUALILENS_PORT=8790 ./run.sh
```

The address is bound to 127.0.0.1. QualiLens is therefore reachable only from the computer it runs on, and nothing on your network can open it.

Your browser is the one thing on that computer that could. A web page you have open in another tab can send requests to any local port, and a page that has been made to resolve to 127.0.0.1 could try to read from it. QualiLens closes both routes. The server answers only when the request names `127.0.0.1` or `localhost` as its host, refuses any request a browser marks as coming from another site, and requires a session token on every API call. The token is minted fresh each time the app starts and written into the page the app serves, so only pages QualiLens itself served carry it. You will notice the token in one situation only: if the app is restarted while a tab stays open, the tab's next action is refused and the page reloads itself once to fetch the new token. You see a brief reload, and carry on.

The app runs on macOS and Linux; on Windows, use WSL.

## API keys

QualiLens calls AI model providers directly with your key. Open **Settings** from the top bar to manage your keys.

Each provider gets its own card with four controls.

| Control | What it does |
|---|---|
| Key field | Accepts a pasted key. The field is masked, and an already-saved key shows as a placeholder rather than being displayed back to you. |
| Save | Writes the key to the local database. The card then shows a check beside the provider's name and Ready to analyze, with a hint of the form `sk-ant…4f2a` — the first six and last four characters. |
| Test | Sends one very short request to the provider and reports whether it answered. If you have typed a new key into the field but not saved it, Test uses the typed key, so a failing candidate never overwrites a working saved key. |
| Remove | Clears the stored key for that provider. |

The four providers, and the models QualiLens offers for each, are listed in [Choosing a Method](03-choosing-a-method.md#provider-and-model).

### The OpenAI key is special

Transcription of audio and video always runs through OpenAI's speech-to-text service, whichever provider performs your analysis. You will still need an OpenAI key saved in Settings if you plan to upload recordings and you have chosen Anthropic, Google, or Mistral as your analysis provider. Transcription fails without one.

### Checking that the models are still current

Providers retire models. **Check models**, on each provider's card in
Settings, compares the models this app offers against the provider's own
live model list, using your key and the provider's free listing endpoint. No
tokens are spent and nothing is sent anywhere except that provider. A model
marked ✗ is no longer served: pick a different one in the wizard, or type
any current model id under **Custom model id…** there. Run the check when a
model choice starts failing, and before you pass the app to a colleague.

### Where keys are stored

Your keys live in the `settings` table of the local SQLite database, stored as plain text. They are not encrypted, and they are not held in your system keychain. Anyone with read access to `qualilens.db` can read them.

Two practical consequences follow. Your keys are synced along with everything else if the data folder sits inside a cloud-synced directory — the app says so at startup and on the Settings screen when it detects one, and the next section says how to move the folder out. And you should use Remove before you share the folder or hand the computer to someone else, then re-enter the keys afterward.

## What happens on the first launch

The app opens on the **Projects** screen, which is empty. The top bar carries three links. The QualiLens wordmark returns you to Projects, **New analysis** opens the five-step wizard, and **Settings** opens the key management screen.

A sensible first session goes in this order. Save an API key in Settings and press Test until it reports that the key works. Return to Projects and start a new analysis with one short document. A first run on one document costs cents rather than dollars, and it lets you see all the checkpoints before you commit a real dataset. Then read [The Walkthrough](15-walkthrough.md), which follows exactly that path.

## Updating the app

Open **Settings** and find the **Application** card — it names the version
you are running. **Check for updates** asks GitHub for the latest published
QualiLens release and compares it with your installation. The check is
pull-only and happens only when you press the button: one request goes to
GitHub, nothing of yours goes with it, and nothing ever runs in the
background. When a newer release exists, **Download and install** fetches
its bundle and applies it through the same validated updater described
next; when you are current, the card says so.

When you receive a newer `QualiLens.zip` directly, do not replace the folder
by hand. On the same card, press **Update from a downloaded zip**. Either
path verifies that the bundle carries a valid signature from the QualiLens
release key — a bundle that is unsigned, signed by someone else, or altered
after signing is refused before a byte is written — then replaces only the
app's own application files and keeps the outgoing version in
`.update-backup`. Your projects, API keys, and uploaded data are never part
of an update; the updater works from a fixed list of application paths and
refuses everything else, so your data survive by construction rather than
by care. An update is also refused while any run is executing or waiting at
a checkpoint, because applying it stops the server.

If you had edited `backend/app/models.json` by hand, the update replaces it;
your copy is saved beside your data as `models.json.previous` so you can
reapply the edits.

When the update is applied the app stops itself and the page changes to
**Update installed**, which asks you to start the app again — in the Terminal
window where it was running, press ↑ then Return, or run `./run.sh` in the
QualiLens folder; the launcher also installs any new dependencies the update
brought. The page then reconnects on its own: it checks every two seconds
for the new build and, when it answers, reloads itself onto it. There is
nothing to close or reopen. If a minute passes without a reconnection, the
page says what to check, and the most common cause is an older copy of the
app still holding the port, which the launcher reports by name with the
command to stop it.

A related courtesy applies at any restart, not only after an update. A tab
left open across a restart holds a session token the new server does not
know; the first thing it asks of the server is refused, and the page reloads
itself once to fetch the new token rather than showing you the refusal.
Browsers that restore tabs from days ago behave the same way. Only when a
reload does not help — because the app is not running — does the message
`Missing or stale session token` appear, and then the remedy is to start
the app.

Replacing the folder by hand remains possible but is the dangerous path:
`backend/data/` inside the old folder holds everything you have made. If you
must do it, move `backend/data/` into the new folder before deleting the
old one.

## Where things live on disk

| Path | Contents |
|---|---|
| `backend/data/qualilens.db` | Every project, source text, code, excerpt, checkpoint decision, event, and report. This one file is your analysis. |
| `backend/data/uploads/` | The original files you uploaded, each stored under its source identifier plus the original filename. |
| `backend/data/uploads/checkpoints/` | Spreadsheets uploaded at checkpoints, kept so the audit trail can name the worksheet a resolution came from. |
| `backend/.venv/` | The Python environment the launcher builds. Safe to delete, and it will be rebuilt on the next launch. |
| `frontend/dist/` | The built interface. Safe to delete, and it will be rebuilt on the next launch. |

Back up `backend/data/`. Everything else in the folder can be regenerated from the code. Nothing else can regenerate your analyses.

### Moving the data folder

The data folder need not sit inside the app folder. Start the app with the `QUALILENS_DATA_DIR` variable and it keeps the database and the uploads there instead.

```bash
QUALILENS_DATA_DIR="$HOME/QualiLensData" ./run.sh
```

Move the existing `backend/data` folder to the new location first, or you will start with an empty database. The Settings screen names the folder in use. Do this whenever the app folder lives inside Dropbox, iCloud Drive, OneDrive, or another synced directory and your data must not: the database holds raw participant data and API keys in plain text, and a synced folder hands both to the sync service.

## A warning about cloud-synced folders

Your QualiLens folder may sit inside a directory that Dropbox, iCloud Drive, OneDrive, or a similar service keeps in sync. That arrangement is convenient as a backup. It also introduces one failure mode you must avoid.

Never run QualiLens on two computers against the same synced database. SQLite assumes it is the only writer. Sync services resolve conflicts by keeping one copy and renaming the other, so two simultaneous sessions can silently lose an analysis. Let the sync finish completely on the first computer before you start the app on a second.

There is a protection built in, and you should know what it depends on. SQLite writes through a write-ahead log, which leaves a sidecar file alongside the database, and a sync service that copies the main file without the sidecar copies an incoherent state. QualiLens folds the write-ahead log back into the main database file at startup, at shutdown, at the end of every stage, and whenever you approve a checkpoint, so the at-rest state on disk is a single coherent file at every point where it matters. Stopping the app with Ctrl-C rather than killing the terminal still helps, and you must still let the sync complete before you open the folder elsewhere.

The better arrangement is the one described above: keep the data folder outside the synced tree with `QUALILENS_DATA_DIR`, and back it up on your own terms.

## License, and how to cite QualiLens

QualiLens is copyright 2026 Ashita Aggarwal and Suraj Commuri. It is released under the Apache License 2.0. You may use it, modify it, and share it, including commercially, provided the copyright notice and the `NOTICE` file travel with any redistribution. Every source file carries an SPDX header, so attribution survives even when a single file is copied out of the project.

The analyses, codebooks, and reports you produce with QualiLens are yours alone. The authors claim no rights over any output of the tool. The `NOTICE` file says so explicitly. Point a sponsor or a publisher at that file if you are ever asked who owns your findings.

Please cite QualiLens if it contributes to published research. The machine-readable form is in `CITATION.cff` at the top of the project. The human-readable form is this.

> Aggarwal, A., & Commuri, S. (2026). *QualiLens: A local application for LLM-assisted qualitative data analysis* [Computer software].

Name the version of the software alongside the citation in your methods section, together with the provider and model that performed the coding. Those determine your analysis far more than the application does. [Reports](12-reports.md#reporting-a-qualilens-analysis) lists everything else worth recording.

## Running the tests

The test suite runs against scratch databases with a mocked AI model. It involves no API keys and no spend, and it never touches your real project database.

```bash
cd backend && .venv/bin/python -m pytest tests/test_fixes.py tests/test_hardening.py tests/test_sheets.py -q \
  && .venv/bin/python tests/e2e_grounded_theory.py \
  && .venv/bin/python tests/e2e_methods.py
```

Run these after upgrading Python, or after any change to the code. A green suite tells you the five pipelines still complete end to end.
