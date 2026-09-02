<!--
Copyright 2026 Ashita Aggarwal and Suraj Commuri
SPDX-License-Identifier: Apache-2.0
-->

# Contributing to QualiLens

Thank you for taking an interest. QualiLens is maintained by two researchers
in the time research allows, so this document is short and honest about what
we can take on.

## Reporting a bug

Open a GitHub issue. Include the version from **Settings → Application**,
what you did, what you expected, and what happened instead. The **Audit log**
on the Run screen usually contains the line that explains a failed run —
paste the relevant lines. **Never paste an API key, and check quoted material
before you post it: excerpts from your own data belong to your participants,
not in a public issue.**

## Proposing a change

Open an issue first for anything larger than a typo, so we can agree on the
shape before you write code. For pull requests:

- Keep the test suite green with no API spend:
  `cd backend && .venv/bin/python -m pytest tests/test_fixes.py tests/test_hardening.py -q`, then
  `.venv/bin/python tests/e2e_grounded_theory.py` and
  `.venv/bin/python tests/e2e_methods.py`. New behavior needs new mocked
  tests; nothing in `backend/tests/` may call a real provider.
- The manual is part of the product. If your change alters what the app does,
  edit the matching `manual/*.md` chapter and run
  `python3 manual/build_manual.py` — never edit `manual.html` by hand.
- Every new source file carries the SPDX header used throughout.
- By submitting a contribution you agree to license it under Apache-2.0.

## Support statement

We maintain: defect fixes, the model catalog (`backend/app/models.json`), and
the documented behavior of the five methods. We review feature requests but
decline most of them — the tool stays small and auditable by design, and a
method whose epistemics do not fit (see the project README) will not be
added. Response times are academic, not commercial.

## Security

If you believe you have found a vulnerability that affects researchers' data,
please report it privately through GitHub's "Report a vulnerability" form on
the repository's Security tab rather than opening a public issue. If that is
unavailable, open an issue that says only "security — please contact me" and
a maintainer will reply with a private channel.

For development against the Vite dev server, start the backend with a pinned
session token — `QUALILENS_TOKEN=dev ./run.sh` — and export the same value
before `npm run dev`; the proxy in `vite.config.ts` forwards it.
