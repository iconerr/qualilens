# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""The update path through a real browser — optional, not part of CI.

Installs a newer signed bundle from the Settings page, lets the server stop
itself, relaunches it, and requires the page to reconnect on its own with the
new token. Then the stale-token path: a tab that survives a plain restart must
reload itself on its next API call instead of showing a token error.

Needs: Playwright with Chromium (`pip install playwright && playwright
install chromium`), a tree to run from whose update.py trusts a test key,
and a bundle signed with that key carrying a newer VERSION. Nothing here
touches the real data folder or the release key.

    # one-time setup, from the app folder
    python backend/app/signing.py keygen /tmp/testkey.key      # prints PUB
    rsync -a --exclude node_modules . /tmp/ql_upd/ && printf '2026.01.01-0000' > /tmp/ql_upd/VERSION
    #   set PUBLIC_KEY_HEX in /tmp/ql_upd/backend/app/update.py to PUB
    QUALILENS_SIGNING_KEY=/tmp/testkey.key ./package.sh /tmp/newbuild.zip
    QL_TREE=/tmp/ql_upd QL_BUNDLE=/tmp/newbuild.zip python backend/tests/e2e_update_browser.py

A successful run leaves the tree updated: its update.py is now the bundle's,
which trusts the real release key, and its VERSION is the bundle's. Before
running again, reset VERSION and set PUBLIC_KEY_HEX to the test key again.
"""
import os, re, subprocess, sys, tempfile, time, urllib.request, zipfile

from playwright.sync_api import sync_playwright

TREE = os.environ.get("QL_TREE") or sys.exit("set QL_TREE to the tree to run (see docstring)")
BUNDLE = os.environ.get("QL_BUNDLE") or sys.exit("set QL_BUNDLE to the signed newer bundle")
PORT = int(os.environ.get("QL_PORT", "8831"))
ORIGIN = f"http://127.0.0.1:{PORT}"
PY = os.environ.get("QL_PYTHON", sys.executable)
ENV = dict(os.environ, QUALILENS_DATA_DIR=tempfile.mkdtemp(prefix="ql_update_e2e_"))
with zipfile.ZipFile(BUNDLE) as z:
    NEW = z.read("QualiLens/VERSION").decode().strip()
OLD = open(f"{TREE}/VERSION").read().strip()
assert NEW != OLD, "the bundle must carry a different VERSION from the tree"


def start():
    p = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                         cwd=f"{TREE}/backend", env=ENV,
                         stdout=open(os.path.join(ENV["QUALILENS_DATA_DIR"], "server.log"), "ab"),
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


fails = []


def check(cond, msg):
    print(("  ok  " if cond else "  FAIL") + " " + msg)
    if not cond:
        fails.append(msg)


srv = start()
check(served_build() == OLD, f"server A serves build {OLD}")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    page = b.new_context(viewport={"width": 1400, "height": 900}).new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(ORIGIN + "/#/settings", wait_until="networkidle")
    token_before = page.evaluate("document.querySelector('meta[name=ql-token]').content")
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
    page.wait_for_function(f"document.querySelector('meta[name=ql-build]')?.content === '{NEW}'", timeout=15000)
    check(True, "page reloaded itself onto the new build without a click")
    page.wait_for_selector("text=API keys are stored", timeout=10000)
    check("Missing or stale session token" not in page.content(), "no token error after the reconnect")
    check(page.evaluate("document.querySelector('meta[name=ql-token]').content") != token_before,
          "page holds the new server's token")
    # a surviving tab across a plain restart
    page.goto(ORIGIN + "/#/", wait_until="networkidle")
    stale = page.evaluate("document.querySelector('meta[name=ql-token]').content")
    srv.terminate(); srv.wait(); srv = start()
    page.click("text=Settings")
    page.wait_for_function(f"document.querySelector('meta[name=ql-token]')?.content !== '{stale}'", timeout=15000)
    page.wait_for_selector("text=API keys are stored", timeout=10000)
    check("Missing or stale session token" not in page.content(), "stale tab reloaded itself; no token error")
    b.close()
srv.terminate(); srv.wait()
print("ALL UPDATE E2E CHECKS PASSED" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
