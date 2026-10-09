# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""The update path through a real browser — optional, not part of CI.

Installs a newer signed bundle from the Settings page, lets the server stop
itself, relaunches it, and requires the page to follow the new build on its
own. Since 2026-10-08 the server gives its session token only to a browser a
launch page has signed in, so every start here does what ./run.sh does: the
server writes the launch page (QUALILENS_LAUNCH_FILE) and a tab of its own
opens it. Then the stale-token path: a tab that survives a plain restart
shows how to open QualiLens instead of a token error, and signs itself in
once the new launch tab has loaded. A browser never signed in sees no token.

The tree to update from is best the previous release as users have it, so
that the run covers the old interface meeting the new server. Needs
Playwright with Chromium (`pip install playwright && playwright install
chromium`), that tree with its update.py trusting a test key, and a bundle
signed with that key carrying a newer VERSION. Nothing here touches the real
data folder or the release key.

    # one-time setup, from the app folder
    python backend/app/signing.py keygen /tmp/testkey.key      # prints PUB
    unzip -q ../release-packages/QualiLens-<previous stamp>.zip -d /tmp/ql_upd
    #   set PUBLIC_KEY_HEX in /tmp/ql_upd/QualiLens/backend/app/update.py to PUB
    cp VERSION /tmp/VERSION.keep && cp RELEASE /tmp/RELEASE.keep   # package.sh re-stamps both
    QUALILENS_SIGNING_KEY=/tmp/testkey.key ./package.sh /tmp/newbuild.zip
    cp /tmp/VERSION.keep VERSION && cp /tmp/RELEASE.keep RELEASE
    QL_TREE=/tmp/ql_upd/QualiLens QL_BUNDLE=/tmp/newbuild.zip \
        QL_PYTHON="$PWD/backend/.venv/bin/python" python backend/tests/e2e_update_browser.py

A copy of this folder (`rsync -a --exclude node_modules . /tmp/ql_upd/`, with
an older VERSION) also serves as the tree, and then the run covers the
current interface's reconnect instead. A successful run leaves the tree
updated: its update.py is now the bundle's, which trusts the real release
key, and its VERSION is the bundle's. Unzip it afresh before running again.
"""
import atexit, os, re, subprocess, sys, tempfile, time, urllib.request, zipfile

from playwright.sync_api import sync_playwright

TREE = os.environ.get("QL_TREE") or sys.exit("set QL_TREE to the tree to run (see docstring)")
BUNDLE = os.environ.get("QL_BUNDLE") or sys.exit("set QL_BUNDLE to the signed newer bundle")
PORT = int(os.environ.get("QL_PORT", "8831"))
ORIGIN = f"http://127.0.0.1:{PORT}"
PY = os.environ.get("QL_PYTHON", sys.executable)
DATA = tempfile.mkdtemp(prefix="ql_update_e2e_")
# where ./run.sh has the server write the launch page: a folder only this account can enter
LAUNCH = os.path.join(DATA, "launch", "open.html")
os.makedirs(os.path.dirname(LAUNCH), mode=0o700)
ENV = dict(os.environ, QUALILENS_DATA_DIR=DATA, QUALILENS_SECRET_FILE=os.path.join(DATA, "secret.key"),
           QUALILENS_LAUNCH_FILE=LAUNCH, QUALILENS_PORT=str(PORT))
ENV.pop("QUALILENS_TOKEN", None)
with zipfile.ZipFile(BUNDLE) as z:
    NEW = z.read("QualiLens/VERSION").decode().strip()
OLD = open(f"{TREE}/VERSION").read().strip()
assert NEW != OLD, "the bundle must carry a different VERSION from the tree"
# the token this tab holds: the one served in the page, else the one it kept
TOKEN_JS = "document.querySelector('meta[name=ql-token]')?.content || sessionStorage.getItem('ql-token') || ''"
# text only the signed-in Settings screen shows (its subtitle; the earlier
# marker, "API keys are stored", left the screen in a redesign)
SETTINGS = "text=Keys, data, and the application"


def start():
    if os.path.exists(LAUNCH):
        os.unlink(LAUNCH)   # a server killed outright leaves its page behind
    p = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                         cwd=f"{TREE}/backend", env=ENV,
                         stdout=open(os.path.join(DATA, "server.log"), "ab"),
                         stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen(ORIGIN + "/", timeout=1)
            return p
        except Exception:  # noqa: BLE001
            time.sleep(0.25)
    raise SystemExit("server did not start")


def served_build():
    html = urllib.request.urlopen(ORIGIN + "/", timeout=2).read().decode()
    return re.search(r'ql-build" content="([^"]*)"', html).group(1)


def launch_url():
    """The address the launch page sends a browser to; None for a build from
    before 2026-10-08, which writes no launch page and gives its token to any
    page load."""
    if not os.path.exists(LAUNCH):
        return None
    return re.search(r'content="0;url=([^"]+)"', open(LAUNCH, encoding="utf-8").read()).group(1)


fails = []


def check(cond, msg):
    print(("  ok  " if cond else "  FAIL") + " " + msg)
    if not cond:
        fails.append(msg)


srv = start()
# a failed wait raises out of the browser block; never leave a server behind
atexit.register(lambda: srv.poll() is None and srv.terminate())
check(served_build() == OLD, f"server A serves build {OLD}")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})

    def run_sh_opens_launch_page():
        """What ./run.sh does once the server answers: open the launch page in
        this browser, in a tab of its own. None for a build that writes none."""
        url = launch_url()
        if not url:
            return None
        tab = ctx.new_page()
        tab.goto(url, wait_until="networkidle")
        return tab

    run_sh_opens_launch_page()
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(ORIGIN + "/#/settings", wait_until="networkidle")
    token_before = page.evaluate(TOKEN_JS)
    check(bool(token_before), "page holds server A's token")
    page.set_input_files("input[type=file]", BUNDLE)
    page.wait_for_selector("text=Update installed", timeout=60000)
    check(True, "page shows 'Update installed'")
    for _ in range(40):
        if srv.poll() is not None:
            break
        time.sleep(0.25)
    check(srv.poll() is not None, "server A stopped itself")
    check(open(f"{TREE}/VERSION").read().strip() == NEW, "tree carries the new stamp")
    time.sleep(4)
    check("Update installed" in page.content(), "page still waiting, not errored, while the server is down")
    srv = start()
    check(served_build() == NEW, f"server B serves build {NEW}")
    check(launch_url() is not None and os.stat(LAUNCH).st_mode & 0o777 == 0o600,
          "server B wrote its launch page, readable by this account only")
    # the old page can reach server B before ./run.sh's tab has signed the
    # browser in: it must wait, not error
    time.sleep(5)
    check("Missing or stale session token" not in page.content(),
          "no token error while the browser is not yet signed in to server B")
    launch_tab = run_sh_opens_launch_page()
    page.wait_for_function(f"document.querySelector('meta[name=ql-build]')?.content === '{NEW}'", timeout=20000)
    check(True, "page followed the new build without a click once the launch tab loaded")
    page.wait_for_selector(SETTINGS, timeout=15000)
    check("Missing or stale session token" not in page.content(), "no token error after the reconnect")
    check(page.evaluate(TOKEN_JS) not in ("", token_before), "page holds the new server's token")
    # another browser, never signed in, gets the page without a token
    stranger = b.new_context().new_page()
    stranger.goto(ORIGIN + "/", wait_until="networkidle")
    check(stranger.evaluate(TOKEN_JS) == "" and "Open QualiLens from the tab it opened" in stranger.content(),
          "a browser never signed in gets no token, only how to open QualiLens")
    # a surviving tab across a plain restart
    page.goto(ORIGIN + "/#/", wait_until="networkidle")
    stale = page.evaluate(TOKEN_JS)
    launch_tab.close()
    srv.terminate(); srv.wait()
    check(not os.path.exists(LAUNCH), "the launch page is removed when the server stops")
    srv = start()
    page.click("text=Settings")
    page.wait_for_selector("text=Open QualiLens from the tab it opened", timeout=15000)
    check("Missing or stale session token" not in page.content(),
          "stale tab shows how to open QualiLens; no token error")
    run_sh_opens_launch_page()
    page.wait_for_selector(SETTINGS, timeout=15000)
    check(page.evaluate(TOKEN_JS) not in ("", stale), "stale tab signed itself in once the new launch tab loaded")
    b.close()
srv.terminate(); srv.wait()
print("ALL UPDATE E2E CHECKS PASSED" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
