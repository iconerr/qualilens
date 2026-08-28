# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Method-appropriate figures for the Word export, rendered with matplotlib.

Uses the object-oriented Figure API (never pyplot), so rendering holds no
global state and is safe under FastAPI's concurrent request threads.

Every function takes the report payload (or its stats block) and returns PNG
bytes, or None when there is nothing meaningful to draw. All rendering is
guarded and logged: a figure that fails must never break report generation.
"""

import logging
import math
import textwrap
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch

log = logging.getLogger("qualilens.viz")

INK = "#22252a"
MUTED = "#6b7280"
ACCENT = "#1f3a5f"
ACCENT_SOFT = "#e8eef6"
AMBER = "#d9a520"
LINE = "#c9c7bf"

MAX_GT_CATEGORIES = 10


def _fig(w: float, h: float) -> Figure:
    fig = Figure(figsize=(w, h))
    FigureCanvasAgg(fig)
    return fig


def _png(fig: Figure) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    return buf.getvalue()


def _wrap(s, width: int, max_lines: int = 3) -> str:
    lines = textwrap.wrap(str(s or ""), width) or [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] += "…"
    return "\n".join(lines)


def gt_relation_labels(stats: dict) -> dict:
    """Map category id -> label for relationships whose target IS the core.

    Selective coding may relate a category to another category ("to": some
    category id); labeling such a relationship on that category's arrow into
    the core would assert a relationship the analysis never made — so only
    relationships aimed at the core (the literal "core", or the core's own
    category id when the core is an existing category) are labeled. Multiple
    core-directed relationships from one category are joined.
    """
    core = (stats or {}).get("core") or {}
    aliases = {"core", ""}
    if core.get("existing_category_id"):
        aliases.add(str(core["existing_category_id"]))
    labels: dict = {}
    for r in (stats or {}).get("relationships") or []:
        fid = r.get("from_category_id")
        rel = str(r.get("relation") or "").strip()
        to = str(r.get("to") or "").strip()
        if fid and rel and (to.lower() in aliases):
            labels.setdefault(fid, [])
            if rel not in labels[fid]:
                labels[fid].append(rel)
    return {fid: " / ".join(rels[:2]) for fid, rels in labels.items()}


def render_for_payload(payload: dict):
    """Return [(caption, png_bytes), ...] appropriate to this report."""
    out = []
    stats = payload.get("stats") or {}
    kind = stats.get("kind")
    try:
        if kind == "gt_model":
            png = gt_model_png(payload)
            if png:
                out.append(("Figure 1. The grounded theory model: categories in "
                            "relation to the core category.", png))
        elif payload.get("method") == "thematic":
            png = thematic_map_png(payload)
            if png:
                out.append(("Figure 1. Thematic map: themes and their "
                            "constituent codes.", png))
        elif kind == "content_frequencies":
            png = content_freq_png(stats)
            if png:
                out.append(("Figure 1. Code frequencies"
                            + (" by group." if stats.get("groups") else "."), png))
        elif kind == "framework_matrix":
            png = framework_heatmap_png(stats)
            if png:
                out.append(("Figure 1. Framework matrix: coded passages per "
                            "source and code.", png))
        elif kind == "concept_matrix":
            png = framework_heatmap_png(stats, row_noun="paper",
                                        col_noun="concept",
                                        value_label="Supporting passages")
            if png:
                out.append(("Figure 1. Concept-by-paper matrix: supporting "
                            "passages per paper and concept.", png))
    except Exception:  # noqa: BLE001 — a figure must never break the report
        log.exception("Report figure rendering failed; continuing without it")
        return []
    return out


# ---------- grounded theory model ----------

def _evidence_weight(theme: dict) -> int:
    return (len(theme.get("excerpts") or [])
            + sum(len(c.get("excerpts") or []) for c in theme.get("children") or []))


def gt_model_png(payload: dict):
    stats = payload.get("stats") or {}
    core_meta = stats.get("core") or {}
    core = core_meta.get("name") or "Core category"
    existing_id = core_meta.get("existing_category_id")
    # the core may itself be one of the categories — never draw it twice
    themes = [t for t in payload.get("themes", [])
              if t.get("name") != "Uncategorized" and t.get("id") != existing_id]
    if not themes:
        return None
    overflow = 0
    if len(themes) > MAX_GT_CATEGORIES:
        themes = sorted(themes, key=_evidence_weight, reverse=True)
        overflow = len(themes) - MAX_GT_CATEGORIES
        themes = themes[:MAX_GT_CATEGORIES]
    rel_by_id = gt_relation_labels(stats)

    fig = _fig(9, 6.4)
    ax = fig.add_subplot()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    cx, cy = 5, 3.5
    core_rx, core_ry = 1.65, 0.85

    n = len(themes)
    rx, ry = 3.6, 2.5
    for i, t in enumerate(themes):
        ang = 2 * math.pi * i / n - math.pi / 2
        x, y = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
        box = FancyBboxPatch((x - 1.05, y - 0.45), 2.1, 0.9,
                             boxstyle="round,pad=0.08",
                             facecolor=ACCENT_SOFT, edgecolor=ACCENT, lw=1.1)
        ax.add_patch(box)
        ax.text(x, y, _wrap(t["name"], 18, 3), ha="center", va="center",
                fontsize=8.5, color=INK)
        # arrow from box edge to the core ELLIPSE BOUNDARY (plus margin), so
        # the arrowhead is never painted over by the ellipse
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        sx, sy = x + ux * 1.15, y + uy * 0.55
        t_edge = 1.0 / math.sqrt((ux / core_rx) ** 2 + (uy / core_ry) ** 2)
        ex, ey = cx - ux * (t_edge + 0.10), cy - uy * (t_edge + 0.10)
        ax.add_patch(FancyArrowPatch((sx, sy), (ex, ey),
                                     arrowstyle="-|>", mutation_scale=13,
                                     color=MUTED, lw=1.0))
        rel = rel_by_id.get(t["id"], "")
        if rel:
            mx, my = (sx + ex) / 2, (sy + ey) / 2
            ax.text(mx, my + 0.14, _wrap(rel, 20, 2), ha="center", va="center",
                    fontsize=7, color=MUTED, style="italic",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="none", alpha=0.85))

    ax.add_patch(Ellipse((cx, cy), core_rx * 2, core_ry * 2,
                         facecolor=ACCENT, edgecolor=ACCENT, lw=1.4))
    ax.text(cx, cy, _wrap(core, 20, 3), ha="center", va="center",
            fontsize=10, color="white", fontweight="bold")
    if overflow:
        ax.text(9.9, 0.15, f"+{overflow} further categor"
                + ("y" if overflow == 1 else "ies") + " not shown",
                ha="right", fontsize=7.5, color=MUTED, style="italic")
    return _png(fig)


# ---------- thematic map ----------

def thematic_map_png(payload: dict, max_codes: int = 8, max_themes: int = 6):
    all_themes = [t for t in payload.get("themes", []) if t.get("children")]
    if not all_themes:
        return None
    themes = all_themes[:max_themes]
    hidden = len(all_themes) - len(themes)
    n = len(themes)
    fig = _fig(max(7.5, 3.1 * n), 6)
    ax = fig.add_subplot()
    ax.set_xlim(0, n)
    ax.set_ylim(0, 10)
    ax.axis("off")

    for i, t in enumerate(themes):
        x = i + 0.5
        ax.add_patch(FancyBboxPatch((x - 0.42, 8.5), 0.84, 1.1,
                                    boxstyle="round,pad=0.03",
                                    facecolor=ACCENT, edgecolor=ACCENT,
                                    mutation_aspect=6))
        ax.text(x, 9.05, _wrap(t["name"], 16, 3), ha="center", va="center",
                fontsize=8.5, color="white", fontweight="bold")
        kids = t.get("children", [])
        for j, k in enumerate(kids[:max_codes]):
            y = 7.6 - j * 0.9
            ax.plot([x, x], [8.45, y + 0.32], color=LINE, lw=0.9, zorder=0)
            n_ex = len(k.get("excerpts") or [])
            ax.add_patch(FancyBboxPatch((x - 0.4, y), 0.8, 0.62,
                                        boxstyle="round,pad=0.02",
                                        facecolor="white", edgecolor=LINE,
                                        mutation_aspect=6))
            ax.text(x, y + 0.31, _wrap(f"{k['name']} ({n_ex})", 18, 2),
                    ha="center", va="center", fontsize=7.3, color=INK)
        if len(kids) > max_codes:
            ax.text(x, 7.6 - max_codes * 0.9 + 0.15,
                    f"+{len(kids) - max_codes} more codes",
                    ha="center", va="center", fontsize=7, color=MUTED,
                    style="italic")
    if hidden:
        ax.text(n - 0.05, 0.15, f"+{hidden} further theme"
                + ("" if hidden == 1 else "s") + " not shown",
                ha="right", fontsize=7.5, color=MUTED, style="italic")
    return _png(fig)


# ---------- content-analysis frequencies ----------

def content_freq_png(stats: dict, top: int = 15):
    rows = (stats.get("rows") or [])[:top]
    if not rows:
        return None
    rows = rows[::-1]  # largest at the top of a horizontal chart
    # numeric y positions: two codes whose wrapped labels coincide must NOT
    # be merged into one categorical bar
    ys = list(range(len(rows)))
    labels = [_wrap(r["code"], 28, 2) for r in rows]
    groups = stats.get("groups") or []
    fig = _fig(8, max(2.8, 0.42 * len(rows) + 1.2 + 0.3 * (len(groups) // 5)))
    ax = fig.add_subplot()

    # an old report may lack by_group breakdowns entirely — fall back to
    # plain bars rather than drawing invisible zero-width segments
    has_breakdown = any((r.get("by_group") or {}).get(g, 0)
                        for r in rows for g in groups)
    if groups and has_breakdown:
        palette = [ACCENT, AMBER, "#5a8f6f", "#a1657c", "#7a6fb0", "#b08948"]
        left = [0.0] * len(rows)
        for gi, g in enumerate(groups):
            vals = [(r.get("by_group") or {}).get(g, 0) for r in rows]
            ax.barh(ys, vals, left=left, height=0.62,
                    color=palette[gi % len(palette)], label=_wrap(g, 18, 1))
            left = [a + b for a, b in zip(left, vals)]
        ax.legend(fontsize=8, frameon=False, loc="upper center",
                  bbox_to_anchor=(0.5, -0.08), ncols=min(len(groups), 4))
        totals = [max(a, r["count"]) for a, r in zip(left, rows)]
    else:
        totals = [r["count"] for r in rows]
        ax.barh(ys, totals, height=0.62, color=ACCENT)

    ax.set_yticks(ys, labels)
    vmax = max(totals) or 1
    for y in ys:
        ax.text(totals[y] + vmax * 0.015, y, str(int(rows[y]["count"])),
                va="center", fontsize=8, color=MUTED)
    ax.set_xlabel("Coded passages", fontsize=9, color=MUTED)
    ax.tick_params(labelsize=8.5, colors=INK)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    n_total = len(stats.get("rows") or [])
    if n_total > top:
        ax.set_title(f"Top {top} of {n_total} codes", fontsize=9,
                     color=MUTED, loc="left")
    return _png(fig)


# ---------- framework matrix heatmap ----------

def framework_heatmap_png(stats: dict, max_codes: int = 12, max_sources: int = 20,
                          row_noun: str = "source", col_noun: str = "code",
                          value_label: str = "Coded passages"):
    """Also draws the literature-synthesis concept-by-paper matrix — the same
    grid with honest nouns (papers x concepts, "supporting passages")."""
    all_rows = stats.get("rows") or []
    all_codes = stats.get("codes") or []
    rows = all_rows[:max_sources]
    codes = all_codes[:max_codes]
    if not rows or not codes:
        return None
    grid = [[((r.get("cells") or {}).get(c) or {}).get("n", 0) for c in codes]
            for r in rows]
    if not any(any(line) for line in grid):
        return None
    fig = _fig(max(6, 0.85 * len(codes) + 2.6), max(2.6, 0.5 * len(rows) + 1.6))
    ax = fig.add_subplot()
    im = ax.imshow(grid, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(codes)),
                  [_wrap(c, 14, 2) for c in codes], fontsize=7.5,
                  rotation=35, ha="right")
    ax.set_yticks(range(len(rows)),
                  [_wrap(r["source"], 24, 1) for r in rows], fontsize=8)
    vmax = max(max(line) for line in grid) or 1
    for y, line in enumerate(grid):
        for x, v in enumerate(line):
            if v:
                ax.text(x, y, str(v), ha="center", va="center", fontsize=7.5,
                        color="white" if v > 0.6 * vmax else INK)
    ax.tick_params(colors=INK)
    hidden = []
    if len(all_rows) > len(rows):
        hidden.append(f"{len(all_rows) - len(rows)} further {row_noun}s")
    if len(all_codes) > len(codes):
        hidden.append(f"{len(all_codes) - len(codes)} further {col_noun}s")
    if hidden:
        ax.set_title("+" + " and ".join(hidden) + " not shown — the matrix "
                     "listing is complete", fontsize=8, color=MUTED, loc="left",
                     style="italic")
    fig.colorbar(im, ax=ax, shrink=0.75).set_label(value_label,
                                                   fontsize=8, color=MUTED)
    return _png(fig)
