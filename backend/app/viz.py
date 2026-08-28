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
import textwrap
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

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


def gt_bucket(relation: str) -> str:
    """Place a category in the paradigm-model flow by its core-directed
    relation text. Antecedent-side buckets (conditions, context, dimensions,
    related) draw LEFT of the core; response-side buckets (strategies,
    consequences) draw RIGHT. The classification only positions the box —
    the relation text itself is printed verbatim inside it, so a heuristic
    misplacement can never misstate the analysis."""
    r = (relation or "").casefold()
    if not r:
        return "related"
    if any(k in r for k in ("consequence", "outcome", "result")):
        return "consequences"
    if any(k in r for k in ("strateg", "action", "response", "coping",
                            "manag", "practice")):
        return "strategies"
    if any(k in r for k in ("condition", "cause", "antecedent", "trigger",
                            "driver", "basis", "prerequisite", "foundation")):
        return "conditions"
    if any(k in r for k in ("context", "intervening", "amplif", "setting",
                            "environment", "fram", "moderat", "backdrop")):
        return "context"
    if any(k in r for k in ("dimension", "aspect", "component", "facet",
                            "element", "part of", "constitut", "embod",
                            "manifest", "form of")):
        return "dimensions"
    return "related"


# antecedent-side buckets, in stacking order; everything else goes right
_GT_LEFT = ("conditions", "context", "dimensions", "related")
_GT_RIGHT = ("strategies", "consequences")


def _gt_columns(themes: list, rel_by_id: dict) -> tuple:
    """Split categories into the left (antecedent) and right (response)
    columns of the paradigm-model flow, preserving bucket order."""
    buckets: dict = {b: [] for b in _GT_LEFT + _GT_RIGHT}
    for t in themes:
        buckets[gt_bucket(rel_by_id.get(t["id"], ""))].append(t)
    left = [t for b in _GT_LEFT for t in buckets[b]]
    right = [t for b in _GT_RIGHT for t in buckets[b]]
    return left, right


def gt_model_png(payload: dict):
    """The paradigm-model flow, read left to right: antecedent categories
    (conditions, context, dimensions) → the core phenomenon → strategies and
    consequences. Each category box prints its own core-directed relation
    verbatim; arrows carry no floating labels, so nothing can collide."""
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
    left, right = _gt_columns(themes, rel_by_id)

    box_h, gap = 1.35, 0.4
    rows = max(len(left), len(right), 1)
    height_units = rows * (box_h + gap) + 1.2
    fig = _fig(11, max(4.6, height_units * 0.95))
    ax = fig.add_subplot()
    ax.set_xlim(0, 12)
    ax.set_ylim(0, height_units)
    ax.axis("off")
    mid_y = height_units / 2
    core_w, core_h = 3.2, 2.1
    cx = 6.0

    def draw_box(x, y, t):
        # boxes sit ABOVE the arrows (zorder), so an arrow from an outer box
        # passes cleanly beneath its neighbors instead of grazing their edges
        ax.add_patch(FancyBboxPatch((x - 1.8, y - box_h / 2), 3.6, box_h,
                                    boxstyle="round,pad=0.07",
                                    facecolor="white", edgecolor=LINE,
                                    lw=1.2, zorder=2))
        rel = rel_by_id.get(t["id"], "")
        if rel:
            ax.text(x, y + 0.27, _wrap(t["name"], 30, 3), ha="center",
                    va="center", fontsize=8.5, color=INK,
                    fontweight="bold", zorder=3)
            # a hairline rule separates the name from its relation, the way
            # the app's cards separate a title from its metadata line
            ax.plot([x - 1.45, x + 1.45], [y - 0.13, y - 0.13],
                    color=LINE, lw=0.8, zorder=3)
            ax.text(x, y - 0.45, _wrap(rel, 36, 2), ha="center", va="center",
                    fontsize=7, color=MUTED, style="italic", zorder=3)
        else:
            ax.text(x, y, _wrap(t["name"], 30, 3), ha="center", va="center",
                    fontsize=8.5, color=INK, fontweight="bold", zorder=3)

    def col_ys(n):
        span = n * box_h + (n - 1) * gap
        top = mid_y + span / 2 - box_h / 2
        return [top - i * (box_h + gap) for i in range(n)]

    def core_edge_y(y):
        # the arrowhead must land ON the core's edge, never beside it
        lean = (y - mid_y) * 0.45
        limit = core_h / 2 - 0.25
        return mid_y + max(-limit, min(limit, lean))

    for y, t in zip(col_ys(len(left)), left):
        draw_box(2.1, y, t)
        ax.add_patch(FancyArrowPatch(
            (3.95, y), (cx - core_w / 2 - 0.12, core_edge_y(y)),
            arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1.0,
            zorder=1))
    for y, t in zip(col_ys(len(right)), right):
        draw_box(9.9, y, t)
        ax.add_patch(FancyArrowPatch(
            (cx + core_w / 2 + 0.12, core_edge_y(y)), (8.05, y),
            arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1.0,
            zorder=1))

    ax.add_patch(FancyBboxPatch((cx - core_w / 2, mid_y - core_h / 2),
                                core_w, core_h, boxstyle="round,pad=0.10",
                                facecolor=ACCENT, edgecolor=ACCENT, lw=1.4,
                                zorder=2))
    ax.text(cx, mid_y + core_h / 2 - 0.32, "Core category", ha="center",
            va="center", fontsize=6.5, color="white", alpha=0.75, zorder=3)
    ax.text(cx, mid_y - 0.12, _wrap(core, 24, 4), ha="center", va="center",
            fontsize=10, color="white", fontweight="bold", zorder=3)
    if overflow:
        ax.text(11.9, 0.12, f"+{overflow} further categor"
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
