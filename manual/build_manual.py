#!/usr/bin/env python3
# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Build a single self-contained manual.html from the markdown sources.

The markdown files in this folder are the source of truth. This script
concatenates them into one offline HTML page with a sticky sidebar and a
client-side search index, then writes identical copies to the three places
the page is wanted.

    python3 manual/build_manual.py

Outputs:
    manual/manual.html            sits beside its own sources, opens by itself
    frontend/public/manual.html   survives `npm run build`
    frontend/dist/manual.html     served at /manual.html, no rebuild needed

Standard library only. No dependencies to install, on any machine.
"""

import hashlib
import html
import re
import sys
from datetime import date
from pathlib import Path

MANUAL_DIR = Path(__file__).resolve().parent
ROOT = MANUAL_DIR.parent
TARGETS = [MANUAL_DIR / "manual.html",
           ROOT / "frontend" / "public" / "manual.html",
           ROOT / "frontend" / "dist" / "manual.html"]

# README first, then the numbered chapters in order.
def source_files():
    readme = MANUAL_DIR / "README.md"
    chapters = sorted(p for p in MANUAL_DIR.glob("*.md") if p.name != "README.md")
    if not readme.exists():
        sys.exit("manual/README.md is missing.")
    return [readme] + chapters


def file_id(path: Path) -> str:
    """A stable in-page id for a chapter.

    The leading chapter number is dropped, because a CSS identifier may not
    begin with a digit and `#11-troubleshooting` is therefore unselectable
    even though it navigates. Dropping it also keeps anchors stable if the
    chapters are ever renumbered.
    """
    if path.name == "README.md":
        return "index"
    return re.sub(r"^\d+[-_]", "", path.stem).lower()


def slug(text: str) -> str:
    s = re.sub(r"`|\*\*|\*", "", text).strip().lower()
    s = re.sub(r"[^a-z0-9 \-]", "", s)
    return re.sub(r"[ ]+", "-", s).strip("-")


# ---------- inline markup ----------

CODE_TOKEN = "\x00CODE%d\x00"


def inline(text: str, link_map: dict) -> str:
    """Escape, then apply code spans, links, bold, and italics in that order."""
    text = html.escape(text, quote=False)

    spans = []

    def stash(m):
        spans.append(m.group(1))
        return CODE_TOKEN % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)

    def link(m):
        label, target = m.group(1), m.group(2)
        return f'<a href="{rewrite_target(target, link_map)}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    for i, code in enumerate(spans):
        text = text.replace(CODE_TOKEN % i, f"<code>{code}</code>")
    return text


def rewrite_target(target: str, link_map: dict) -> str:
    """Turn a cross-file markdown link into an in-page anchor."""
    if target.startswith(("http://", "https://", "#", "mailto:")):
        return target
    name, _, frag = target.partition("#")
    fid = link_map.get(name)
    if fid is None:
        return target
    return f"#{fid}--{frag}" if frag else f"#{fid}"


# ---------- block parsing ----------

def parse_blocks(lines, fid, link_map, headings):
    out = []
    i = 0
    n = len(lines)
    # convention: in README.md, the paragraph directly beneath the title
    # is the byline, and is rendered as one rather than as body prose
    byline_next = False
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # HTML comment (the per-file SPDX header); consumed, never rendered
        if stripped.startswith("<!--"):
            while i < n and "-->" not in lines[i]:
                i += 1
            i += 1
            continue

        # fenced code
        if stripped.startswith("```"):
            i += 1
            body = []
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>"
                       + html.escape("\n".join(body), quote=False)
                       + "</code></pre>")
            continue

        # blockquote: consecutive '>' lines become one quoted block
        if stripped.startswith(">"):
            quoted = []
            while i < n and lines[i].strip().startswith(">"):
                quoted.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>"
                       + inline(" ".join(q.strip() for q in quoted), link_map)
                       + "</blockquote>")
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}", stripped):
            out.append('<hr class="rule">')
            i += 1
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1:
                hid = fid
            else:
                hid = f"{fid}--{slug(text)}"
            headings.append({"level": level, "text": re.sub(r"`|\*\*", "", text),
                             "id": hid, "file": fid})
            out.append(f'<h{level} id="{hid}">{inline(text, link_map)}'
                       f'<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a>'
                       f'</h{level}>')
            byline_next = (level == 1 and fid == "index")
            i += 1
            continue

        # table
        if stripped.startswith("|") and i + 1 < n and re.match(
                r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = split_row(lines[i])
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append(render_table(header, rows, link_map))
            continue

        # paragraph
        para = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith(
                ("#", "```", "|", "<!--", ">")) and not re.fullmatch(r"-{3,}", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        cls = ' class="byline"' if byline_next else ""
        byline_next = False
        out.append(f"<p{cls}>" + inline(" ".join(para), link_map) + "</p>")
    return out


def split_row(line: str):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def render_table(header, rows, link_map) -> str:
    # A table whose first column is Message is a message catalog. Rendered as
    # a genuine table, the short code chip hoards the width while Cause and
    # Remedy wrap two words to a line; rendered as cards, every row breathes.
    if header and header[0].strip().lower() == "message":
        return render_message_list(header, rows, link_map)
    head = "".join(f"<th>{inline(c, link_map)}</th>" for c in header)
    body = ""
    for r in rows:
        cells = "".join(f"<td>{inline(c, link_map)}</td>" for c in r)
        body += f"<tr>{cells}</tr>"
    return ('<div class="table-wrap"><table><thead><tr>'
            + head + "</tr></thead><tbody>" + body + "</tbody></table></div>")


def render_message_list(header, rows, link_map) -> str:
    labels = [h.strip() for h in header[1:]]
    items = ""
    for r in rows:
        msg = inline(r[0], link_map) if r else ""
        facts = ""
        for label, cell in zip(labels, r[1:]):
            if cell.strip():
                facts += ('<div class="msg-fact">'
                          f'<span class="msg-k">{label}</span>'
                          f'<span class="msg-v">{inline(cell, link_map)}</span></div>')
        items += f'<div class="msg-item"><div class="msg-line">{msg}</div>{facts}</div>'
    return f'<div class="msg-list">{items}</div>'



# ---------- navigation ----------

def render_nav(headings) -> str:
    parts = ['<nav id="nav">']
    current_open = False
    for h in headings:
        if h["level"] == 1:
            if current_open:
                parts.append("</div></div>")
            parts.append(f'<div class="nav-sec" data-sec="{h["id"]}">')
            parts.append(f'<a class="nav-h1" href="#{h["id"]}" '
                         f'data-target="{h["id"]}">{html.escape(h["text"])}</a>')
            parts.append('<div class="nav-kids">')
            current_open = True
        elif h["level"] == 2 and current_open:
            parts.append(f'<a class="nav-h2" href="#{h["id"]}" '
                         f'data-target="{h["id"]}">{html.escape(h["text"])}</a>')
    if current_open:
        parts.append("</div></div>")
    parts.append("</nav>")
    return "\n".join(parts)


# ---------- page ----------

CSS = """
:root{
  --bg:#f4f4f6; --panel:#ffffff; --ink:#16171a; --muted:#5c5f66;
  --line:#dcdde2; --line-strong:#c4c6cd; --accent:#1a1b1f; --accent-soft:#ececef;
  --focus:#863bff; --focus-soft:#ede3ff;
  --amber-soft:#fbf1dc; --amber:#8a5a0c;
  --font:"Inter Variable",Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
  --serif:Charter,"Iowan Old Style","Source Serif Pro","Palatino Linotype",Georgia,serif;
  --mono:"JetBrains Mono Variable","JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --rail:300px;
}
/* The same faces the app bundles, at stable paths under /fonts/ when the
   manual is served by the app; opened as a plain file, the stacks above fall
   back to what the machine has. */
@font-face{font-family:"Inter Variable";font-style:normal;font-weight:100 900;font-display:swap;
  src:url(/fonts/inter-latin-wght-normal.woff2) format("woff2");
  unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:"Inter Variable";font-style:normal;font-weight:100 900;font-display:swap;
  src:url(/fonts/inter-latin-ext-wght-normal.woff2) format("woff2");
  unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:"Inter Variable";font-style:italic;font-weight:100 900;font-display:swap;
  src:url(/fonts/inter-latin-wght-italic.woff2) format("woff2");
  unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:"Inter Variable";font-style:italic;font-weight:100 900;font-display:swap;
  src:url(/fonts/inter-latin-ext-wght-italic.woff2) format("woff2");
  unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:"JetBrains Mono Variable";font-style:normal;font-weight:100 800;font-display:swap;
  src:url(/fonts/jetbrains-mono-latin-wght-normal.woff2) format("woff2")}
*{box-sizing:border-box}
html{scroll-behavior:smooth; scroll-padding-top:24px}
html{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);
  font-size:14.5px;line-height:1.5;font-feature-settings:"cv11","ss01"}
a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--line-strong);text-underline-offset:2px}
a:hover{text-decoration-color:var(--ink)}

/* ---------- layout ---------- */
.shell{display:flex;align-items:flex-start;min-height:100vh}
.rail{width:var(--rail);flex:0 0 var(--rail);position:sticky;top:0;height:100vh;
  display:flex;flex-direction:column;background:var(--panel);
  border-right:1px solid var(--line)}
.rail-head{padding:18px 20px 12px;border-bottom:1px solid var(--line)}
.brand{display:block;font-weight:600;font-size:16px;color:var(--ink);letter-spacing:-.2px;text-decoration:none}
.brand:hover{text-decoration:none}
.brand small{display:block;font-weight:400;font-size:11.5px;color:var(--muted);
  margin-top:3px;letter-spacing:.08em;text-transform:uppercase}
.search-wrap{position:relative;margin-top:12px}
#search{width:100%;padding:8px 30px 8px 11px;border:1px solid var(--line);
  border-radius:4px;font-family:inherit;font-size:13.5px;background:#fff;color:var(--ink)}
#search:focus{outline:none;border-color:var(--focus);
  box-shadow:0 0 0 3px var(--focus-soft)}
.search-hint{position:absolute;right:9px;top:50%;transform:translateY(-50%);
  font-family:var(--mono);font-size:11px;color:var(--muted);pointer-events:none}
#search:focus + .search-hint{display:none}

.rail-body{flex:1;overflow-y:auto;padding:10px 0 40px}
.nav-sec{padding:0 8px}
.nav-h1{display:block;padding:6px 12px;border-radius:4px;font-size:13.5px;
  font-weight:500;color:var(--ink);line-height:1.35;text-decoration:none}
.nav-h1:hover{background:var(--bg);text-decoration:none}
.nav-kids{display:none;margin:1px 0 6px 0;padding-left:12px;
  border-left:1px solid var(--line)}
.nav-sec.open .nav-kids{display:block}
.nav-h2{display:block;padding:4px 10px;border-radius:4px;font-size:12.5px;
  color:var(--muted);line-height:1.35;text-decoration:none}
.nav-h2:hover{background:var(--bg);color:var(--ink);text-decoration:none}
.nav-h1.active{background:var(--accent-soft);color:var(--ink);font-weight:600}
.nav-h2.active{color:var(--ink);font-weight:500}

/* ---------- search results ---------- */
#results{display:none;padding:6px 8px 40px}
#results.on{display:block}
body.searching #nav{display:none}
.res-count{padding:6px 12px 8px;font-size:11.5px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.4px}
.res{display:block;padding:8px 12px;border-radius:4px;margin-bottom:2px;color:var(--ink);text-decoration:none}
.res:hover{background:var(--bg);text-decoration:none}
.res .where{display:block;font-size:11px;color:var(--muted);margin-bottom:2px}
.res .snip{display:block;font-size:12.5px;line-height:1.45;color:#3b3f46}
.res mark,mark.hit{background:#fdf0bd;color:inherit;padding:0 1px;border-radius:2px}
.res-empty{padding:14px 12px;font-size:13px;color:var(--muted)}

/* ---------- content ---------- */
.main{flex:1;min-width:0;display:flex;justify-content:center;padding:0 48px 140px}
.doc{width:100%;max-width:820px}
.doc h1{font-size:28px;font-weight:600;line-height:1.2;margin:64px 0 8px;letter-spacing:-.02em}
.doc p.byline{font-family:var(--font);font-size:13px;color:var(--muted);
  letter-spacing:.08em;text-transform:uppercase;margin:0 0 26px}
.doc section:first-child h1{margin-top:44px}
.doc h2{font-size:19px;font-weight:600;margin:38px 0 6px;line-height:1.3;letter-spacing:-.01em}
.doc h3{font-size:15.5px;font-weight:600;margin:26px 0 4px}
.doc p{font-family:var(--serif);font-size:16px;line-height:1.62;margin:12px 0;
  color:#26282e}
.doc code{font-family:var(--mono);font-size:.85em;font-weight:450;background:var(--accent-soft);
  padding:1px 5px;border-radius:3px;color:#2a2c32}
.doc pre{background:#16171a;color:#e6e6ea;padding:14px 16px;border-radius:6px;
  overflow-x:auto;margin:16px 0}
.doc pre code{background:none;padding:0;color:inherit;font-size:12.5px;line-height:1.6}
.doc hr.rule{border:0;border-top:1px solid var(--line);margin:34px 0}
.doc blockquote{margin:16px 0;padding:2px 0 2px 18px;
  border-left:3px solid var(--line);font-family:var(--serif);font-size:15.5px;
  line-height:1.6;color:#3a3c42}
.doc strong{font-weight:600;color:var(--ink)}

.table-wrap{overflow-x:auto;margin:16px 0;border:1px solid var(--line);
  border-radius:6px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:9px 13px;border-bottom:1px solid var(--line);
  vertical-align:top;line-height:1.45}
th{background:var(--bg);font-weight:500;font-size:12.5px;white-space:nowrap}
tr:last-child td{border-bottom:none}
td code{white-space:nowrap}

.msg-list{margin:16px 0;border:1px solid var(--line);border-radius:6px;
  background:var(--panel);overflow:hidden}
.msg-item{padding:13px 16px 11px;border-bottom:1px solid var(--line)}
.msg-item:last-child{border-bottom:none}
.msg-item:nth-child(even){background:#f8f8fa}
.msg-line{margin-bottom:7px}
.msg-line code{white-space:normal;word-break:break-word}
.msg-fact{display:flex;gap:12px;font-size:13.5px;line-height:1.5;margin-top:4px}
.msg-k{flex:0 0 62px;font-weight:500;color:var(--muted);font-size:10.5px;
  text-transform:uppercase;letter-spacing:.06em;padding-top:2.5px}
.msg-v{flex:1;color:var(--ink)}

.anchor{opacity:0;margin-left:8px;color:var(--muted);font-weight:400;
  text-decoration:none;font-size:.7em}
.doc a:not(.anchor){color:var(--ink)}
h1:hover .anchor,h2:hover .anchor,h3:hover .anchor{opacity:1}

section{scroll-margin-top:20px}
.flash{animation:flash 1.6s ease-out}
tr.flash td,tr.flash th{animation:flash 1.6s ease-out}
@keyframes flash{0%{background:#fdf0bd}100%{background:transparent}}

.colophon{margin:80px 0 0;padding:22px 0 0;border-top:1px solid var(--line);
  font-size:12.5px;line-height:1.6;color:var(--muted)}
.colophon p{font-family:var(--font);font-size:12.5px;color:var(--muted);margin:0 0 8px}
.colophon b{color:var(--ink)}
.colophon .buildstamp{margin-top:14px;font-size:11.5px;color:#8b8e97}
.colophon code{font-family:var(--mono);font-size:11px;background:var(--accent-soft);
  padding:1px 5px;border-radius:3px;color:var(--muted)}

.totop{position:fixed;right:22px;bottom:22px;padding:8px 13px;border-radius:20px;
  background:var(--panel);border:1px solid var(--line-strong);font-size:12.5px;
  color:var(--muted);box-shadow:0 2px 10px rgba(22,23,26,.06);opacity:0;text-decoration:none;
  pointer-events:none;transition:opacity .2s}
.totop.on{opacity:1;pointer-events:auto}
.totop:hover{color:var(--ink);text-decoration:none}

/* ---------- narrow screens ---------- */
@media (max-width:900px){
  :root{--rail:100%}
  /* the base rule pins align-items to flex-start, which in a column flex
     container makes each item size to its content and overflows the viewport */
  .shell{flex-direction:column;align-items:stretch}
  .rail{position:static;height:auto;max-height:58vh;width:100%;flex:0 0 auto;
    border-right:none;border-bottom:1px solid var(--line)}
  .main{padding:0 20px 80px;width:100%}
  .doc{max-width:100%}
  .doc h1{margin-top:40px;font-size:25px}
  .doc p{font-size:15.5px}
}

@media print{
  .rail,.totop,.anchor{display:none!important}
  .main{padding:0}
  body{background:#fff}
  .doc section{break-before:page}
  .doc section:first-child{break-before:auto}
}
"""

JS = r"""
(function () {
  var content = document.getElementById('content');
  var search  = document.getElementById('search');
  var results = document.getElementById('results');
  var nav     = document.getElementById('nav');
  var totop   = document.getElementById('totop');

  /* ---- build the search index from the rendered page ---- */
  var index = [];
  var sections = content.querySelectorAll('section');
  for (var s = 0; s < sections.length; s++) {
    var sec = sections[s];
    var secTitle = sec.querySelector('h1') ? sec.querySelector('h1').textContent.replace(/#$/, '') : '';
    var heading = secTitle;
    var kids = sec.children;
    for (var k = 0; k < kids.length; k++) {
      var el = kids[k];
      var tag = el.tagName;
      if (tag === 'H1') continue;
      if (tag === 'H2' || tag === 'H3') {
        heading = el.textContent.replace(/#$/, '');
      }
      /* index a table one row at a time; taking textContent of the whole
         table would concatenate every cell into one unreadable snippet */
      if (el.classList && el.classList.contains('msg-list')) {
        var mItems = el.querySelectorAll('.msg-item');
        for (var m = 0; m < mItems.length; m++) {
          var mText = mItems[m].textContent.replace(/\s+/g, ' ').trim();
          if (!mText) continue;
          if (!mItems[m].id) mItems[m].id = 'b' + index.length;
          index.push({ el: mItems[m], id: mItems[m].id, text: mText,
                       low: mText.toLowerCase(), section: secTitle,
                       heading: heading, isHead: false });
        }
        continue;
      }
      if (el.classList && el.classList.contains('table-wrap')) {
        var rows = el.querySelectorAll('tr');
        for (var r = 0; r < rows.length; r++) {
          var cells = rows[r].querySelectorAll('th, td');
          var parts = [];
          for (var c = 0; c < cells.length; c++) {
            var ct = cells[c].textContent.trim();
            if (ct) parts.push(ct);
          }
          var rowText = parts.join('  ·  ');
          if (!rowText) continue;
          if (!rows[r].id) rows[r].id = 'b' + index.length;
          index.push({ el: rows[r], id: rows[r].id, text: rowText,
                       low: rowText.toLowerCase(), section: secTitle,
                       heading: heading, isHead: false });
        }
        continue;
      }
      var text = el.textContent.replace(/#$/, '').trim();
      if (!text) continue;
      if (!el.id) el.id = 'b' + index.length;
      index.push({ el: el, id: el.id, text: text, low: text.toLowerCase(),
                   section: secTitle, heading: heading, isHead: tag[0] === 'H' });
    }
  }

  function esc(s) {
    return s.replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }

  function snippet(text, low, q) {
    var i = low.indexOf(q);
    var start = Math.max(0, i - 60);
    var end = Math.min(text.length, i + q.length + 110);
    var pre  = (start > 0 ? '…' : '') + text.slice(start, i);
    var hit  = text.slice(i, i + q.length);
    var post = text.slice(i + q.length, end) + (end < text.length ? '…' : '');
    return esc(pre) + '<mark>' + esc(hit) + '</mark>' + esc(post);
  }

  var flashed = null;
  function goTo(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    if (flashed) flashed.classList.remove('flash');
    el.classList.add('flash');
    flashed = el;
  }

  function runSearch() {
    var q = search.value.trim().toLowerCase();
    if (q.length < 2) {
      document.body.classList.remove('searching');
      results.classList.remove('on');
      results.innerHTML = '';
      return;
    }
    document.body.classList.add('searching');
    results.classList.add('on');

    var hits = [];
    for (var i = 0; i < index.length && hits.length < 60; i++) {
      if (index[i].low.indexOf(q) !== -1) hits.push(index[i]);
    }
    hits.sort(function (a, b) { return (b.isHead ? 1 : 0) - (a.isHead ? 1 : 0); });

    if (!hits.length) {
      results.innerHTML = '<div class="res-empty">No matches for “' + esc(search.value) + '”.</div>';
      return;
    }
    var html = '<div class="res-count">' + hits.length +
               (hits.length === 60 ? '+ matches' : ' match' + (hits.length === 1 ? '' : 'es')) + '</div>';
    for (var j = 0; j < hits.length; j++) {
      var h = hits[j];
      var where = h.heading && h.heading !== h.section
        ? esc(h.section) + ' › ' + esc(h.heading) : esc(h.section);
      html += '<a class="res" href="#' + h.id + '" data-go="' + h.id + '">' +
              '<span class="where">' + where + '</span>' +
              '<span class="snip">' + snippet(h.text, h.low, q) + '</span></a>';
    }
    results.innerHTML = html;
  }

  search.addEventListener('input', runSearch);
  search.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { search.value = ''; runSearch(); search.blur(); }
    if (e.key === 'Enter') {
      var first = results.querySelector('.res');
      if (first) { goTo(first.getAttribute('data-go')); search.blur(); }
      e.preventDefault();
    }
  });
  results.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('.res') : null;
    if (!a) return;
    e.preventDefault();
    goTo(a.getAttribute('data-go'));
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== search) {
      e.preventDefault(); search.focus(); search.select();
    }
  });

  /* ---- scroll spy ---- */
  var links = {};
  var navLinks = nav.querySelectorAll('[data-target]');
  for (var n = 0; n < navLinks.length; n++) {
    links[navLinks[n].getAttribute('data-target')] = navLinks[n];
  }
  var marks = content.querySelectorAll('h1[id], h2[id]');
  var order = [];
  for (var m = 0; m < marks.length; m++) order.push(marks[m]);

  var currentId = null;
  function spy() {
    var found = null;
    for (var i = 0; i < order.length; i++) {
      if (order[i].getBoundingClientRect().top <= 90) found = order[i]; else break;
    }
    totop.classList.toggle('on', window.scrollY > 700);
    var id = found ? found.id : (order[0] && order[0].id);
    if (id === currentId) return;
    currentId = id;
    for (var key in links) links[key].classList.remove('active');
    var secs = nav.querySelectorAll('.nav-sec');
    for (var s2 = 0; s2 < secs.length; s2++) secs[s2].classList.remove('open');
    var link = links[id];
    if (!link) return;
    link.classList.add('active');
    var sec = link.closest('.nav-sec');
    if (sec) {
      sec.classList.add('open');
      var h1 = sec.querySelector('.nav-h1');
      if (h1 !== link) h1.classList.add('active');
      if (sec.getBoundingClientRect().top < 0 ||
          sec.getBoundingClientRect().bottom > window.innerHeight) {
        link.scrollIntoView({ block: 'nearest' });
      }
    }
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () { spy(); ticking = false; });
  });
  window.addEventListener('load', spy);
  spy();

  totop.addEventListener('click', function (e) {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();
"""


def build() -> tuple[str, str]:
    """Return the finished page and the build stamp printed alongside it."""
    files = source_files()
    link_map = {p.name: file_id(p) for p in files}
    headings = []
    body = []
    digest = hashlib.sha256()
    for p in files:
        fid = file_id(p)
        raw = p.read_text(encoding="utf-8")
        # fingerprint the sources, not the rendered page, so the same markdown
        # always yields the same identifier however often it is rebuilt
        digest.update(p.name.encode("utf-8"))
        digest.update(raw.encode("utf-8"))
        blocks = parse_blocks(raw.split("\n"), fid, link_map, headings)
        body.append(f'<section id="sec-{fid}">\n' + "\n".join(blocks) + "\n</section>")

    n_chapters = len(files) - 1          # the index is not a chapter
    src_hash = digest.hexdigest()[:8]
    built = date.today().strftime("%-d %B %Y") if sys.platform != "win32" \
        else date.today().strftime("%d %B %Y")
    stamp = (f"Built {built} from {n_chapters} chapters in <code>manual/</code>. "
             f"Source fingerprint <code>{src_hash}</code>.")
    stamp_plain = f"built {built} · {n_chapters} chapters · sources {src_hash}"

    nav = render_nav(headings)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QualiLens User Manual</title>
<meta name="author" content="Ashita Aggarwal and Suraj Commuri">
<meta name="copyright" content="Copyright 2026 Ashita Aggarwal and Suraj Commuri. Licensed under Apache-2.0.">
<meta name="date" content="{date.today().isoformat()}">
<!-- QualiLens User Manual: {stamp_plain} -->
<style>{CSS}</style>
</head>
<body>
<div class="shell">
  <aside class="rail">
    <div class="rail-head">
      <a class="brand" href="#index">QualiLens<small>User Manual</small></a>
      <div class="search-wrap">
        <input id="search" type="search" placeholder="Search the manual"
               autocomplete="off" spellcheck="false" aria-label="Search the manual">
        <span class="search-hint">/</span>
      </div>
    </div>
    <div class="rail-body">
      {nav}
      <div id="results"></div>
    </div>
  </aside>
  <main class="main">
    <article class="doc" id="content">
{chr(10).join(body)}
      <footer class="colophon">
        <p><b>QualiLens User Manual.</b> Copyright 2026
        <a href="https://in.linkedin.com/in/drashita" target="_blank" rel="noopener">Ashita Aggarwal</a> and Suraj
        Commuri, released under the
        <a href="https://www.apache.org/licenses/LICENSE-2.0" target="_blank"
           rel="noopener">Apache License 2.0</a>. Free to use, modify, and share,
        including commercially, provided the copyright notice travels with it.</p>
        <p>The analyses, codebooks, and reports you produce with QualiLens are
        yours alone. The authors claim no rights over any output of the tool.</p>
        <p>If QualiLens contributes to published research, cite it as Aggarwal, A.,
        &amp; Commuri, S. (2026). <i>QualiLens: A local application for LLM-assisted
        qualitative data analysis</i> [Computer software].</p>
        <p class="buildstamp">{stamp}</p>
      </footer>
    </article>
  </main>
</div>
<a class="totop" id="totop" href="#">Back to top</a>
<script>{JS}</script>
</body>
</html>
"""
    return page, stamp_plain


def main() -> None:
    page, stamp = build()
    written = []
    for target in TARGETS:
        if not target.parent.exists():
            print(f"skipped {target} (folder does not exist)")
            continue
        target.write_text(page, encoding="utf-8")
        written.append(target)
    size = len(page.encode("utf-8")) / 1024
    for w in written:
        print(f"wrote {w.relative_to(ROOT)}  ({size:.0f} KB)")
    print(stamp)
    if not written:
        sys.exit("Nothing written. Run this from inside the QualiLens project.")


if __name__ == "__main__":
    main()
