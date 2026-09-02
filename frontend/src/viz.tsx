// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

// Method-appropriate report visualizations, hand-rolled SVG (no dependencies):
// the grounded theory model, the thematic map, a code-frequency chart, and a
// framework-matrix heatmap. Each renders nothing when its data is absent.

// Mirrors the tokens in styles.css (SVG cannot read CSS variables when the
// figure is exported). Ink carries the structure; the categorical palette is
// for group comparisons only, and is kept quiet.
const INK = '#16171a'
const MUTED = '#5c5f66'
const ACCENT = '#2a2c32'
const LINE = '#c4c6cd'
const PALETTE = [ACCENT, '#c9971c', '#4f8a6a', '#9a6079', '#6f68a8', '#a3823f']

function wrap(s: string, width: number, maxLines = 3): string[] {
  // hard-break tokens longer than the width (e.g. long filenames)
  const words = (s ?? '').split(/\s+/).flatMap(w => {
    const parts: string[] = []
    while (w.length > width) { parts.push(w.slice(0, width - 1) + '\u2010'); w = w.slice(width - 1) }
    parts.push(w)
    return parts
  })
  const lines: string[] = []
  let cur = ''
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > width && cur) { lines.push(cur); cur = w }
    else cur = (cur + ' ' + w).trim()
  }
  if (cur) lines.push(cur)
  if (lines.length > maxLines) {
    const kept = lines.slice(0, maxLines)
    kept[maxLines - 1] += '…'
    return kept
  }
  return lines
}

function Lines({ x, y, lines, size, fill, weight, anchor = 'middle' }:
  { x: number; y: number; lines: string[]; size: number; fill: string;
    weight?: number; anchor?: 'start' | 'middle' | 'end' }) {
  const startY = y - ((lines.length - 1) * size * 1.15) / 2
  return (
    <text x={x} textAnchor={anchor} fontSize={size} fill={fill}
      fontWeight={weight} fontFamily="inherit">
      {lines.map((l, i) => (
        <tspan key={i} x={x} y={startY + i * size * 1.15}>{l}</tspan>
      ))}
    </text>
  )
}

// ---------- grounded theory model ----------

const MAX_GT_CATS = 10

function evidenceWeight(t: any): number {
  return (t.excerpts ?? []).length
    + (t.children ?? []).reduce((n: number, c: any) => n + (c.excerpts ?? []).length, 0)
}

export function GTModel({ themes, stats }: { themes: any[]; stats: any }) {
  const existingId = stats?.core?.existing_category_id
  // the core may itself be one of the categories — never draw it twice
  let cats = (themes ?? []).filter(t => t.name !== 'Uncategorized' && t.id !== existingId)
  if (!cats.length) return null
  let overflow = 0
  if (cats.length > MAX_GT_CATS) {
    cats = [...cats].sort((a, b) => evidenceWeight(b) - evidenceWeight(a))
    overflow = cats.length - MAX_GT_CATS
    cats = cats.slice(0, MAX_GT_CATS)
  }
  const core = stats?.core?.name || 'Core category'
  // label ONLY relationships whose target is the core (labeling a
  // category-to-category relation on an arrow into the core would assert a
  // relationship the analysis never made); join multiples
  const aliases = new Set(['core', ''])
  if (existingId) aliases.add(String(existingId))
  const relBy: Record<string, string[]> = {}
  for (const r of stats?.relationships ?? []) {
    const rel = String(r.relation ?? '').trim()
    const to = String(r.to ?? '').trim().toLowerCase()
    if (r.from_category_id && rel && aliases.has(to)) {
      relBy[r.from_category_id] = relBy[r.from_category_id] ?? []
      if (!relBy[r.from_category_id].includes(rel)) relBy[r.from_category_id].push(rel)
    }
  }

  // The paradigm-model flow, read left to right: antecedent categories
  // (conditions, context, dimensions) → the core phenomenon → strategies and
  // consequences. The bucket only positions a box; its own core-directed
  // relation is printed verbatim inside it, and arrows carry no floating
  // labels, so nothing can collide or mislead.
  const bucket = (rel: string): string => {
    const r = (rel ?? '').toLowerCase()
    if (!r) return 'related'
    if (['consequence', 'outcome', 'result'].some(k => r.includes(k))) return 'consequences'
    if (['strateg', 'action', 'response', 'coping', 'manag', 'practice']
      .some(k => r.includes(k))) return 'strategies'
    if (['condition', 'cause', 'antecedent', 'trigger', 'driver', 'basis',
      'prerequisite', 'foundation'].some(k => r.includes(k))) return 'conditions'
    if (['context', 'intervening', 'amplif', 'setting', 'environment', 'fram',
      'moderat', 'backdrop'].some(k => r.includes(k))) return 'context'
    if (['dimension', 'aspect', 'component', 'facet', 'element', 'part of',
      'constitut', 'embod', 'manifest', 'form of'].some(k => r.includes(k))) return 'dimensions'
    return 'related'
  }
  const relOf = (t: any) => relBy[t.id]?.slice(0, 2).join(' / ') ?? ''
  const side = (t: any) =>
    ['strategies', 'consequences'].includes(bucket(relOf(t))) ? 'right' : 'left'
  const order = ['conditions', 'context', 'dimensions', 'related', 'strategies', 'consequences']
  const sorted = [...cats].sort((a, b) =>
    order.indexOf(bucket(relOf(a))) - order.indexOf(bucket(relOf(b))))
  const left = sorted.filter(t => side(t) === 'left')
  const right = sorted.filter(t => side(t) === 'right')

  const BOX_W = 320, BOX_H = 128, GAP = 36
  const CORE_W = 300, CORE_H = 210
  const rows = Math.max(left.length, right.length, 1)
  const W = 1150
  const H = rows * (BOX_H + GAP) + 100
  const midY = H / 2
  const colYs = (n: number) => {
    const span = n * BOX_H + (n - 1) * GAP
    const top = midY - span / 2 + BOX_H / 2
    return Array.from({ length: n }, (_, i) => top + i * (BOX_H + GAP))
  }
  const coreEdgeY = (y: number) => {
    // the arrowhead must land ON the core's edge, never beside it
    const lean = (y - midY) * 0.45
    const limit = CORE_H / 2 - 22
    return midY + Math.max(-limit, Math.min(limit, lean))
  }
  const coreL = W / 2 - CORE_W / 2, coreR = W / 2 + CORE_W / 2
  const leftX = () => 30 + BOX_W / 2
  const rightX = () => W - 30 - BOX_W / 2

  const Box = ({ x, y, t }: { x: number; y: number; t: any }) => {
    const rel = relOf(t)
    return (
      <g>
        <rect x={x - BOX_W / 2} y={y - BOX_H / 2} width={BOX_W} height={BOX_H}
          rx={6} fill="white" stroke={LINE} strokeWidth={1.3} />
        {rel ? (
          <>
            <Lines x={x} y={y - 26} lines={wrap(t.name, 30, 3)} size={13}
              fill={INK} weight={600} />
            <line x1={x - 130} y1={y + 12} x2={x + 130} y2={y + 12}
              stroke={LINE} strokeWidth={1} />
            <g fontStyle="italic">
              <Lines x={x} y={y + 42} lines={wrap(rel, 38, 2)} size={11} fill={MUTED} />
            </g>
          </>
        ) : (
          <Lines x={x} y={y} lines={wrap(t.name, 30, 3)} size={13}
            fill={INK} weight={600} />
        )}
      </g>
    )
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: 1080 }}
      role="img" aria-label="Grounded theory model, read left to right">
      <defs>
        <marker id="gt-arrow" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill={MUTED} />
        </marker>
      </defs>
      {/* arrows first, boxes after: a spoke from an outer box passes cleanly
          beneath its neighbors instead of grazing their edges */}
      {left.map((t, i) => {
        const y = colYs(left.length)[i]
        return (
          <line key={`la-${t.id}`} x1={leftX() + BOX_W / 2 + 4} y1={y}
            x2={coreL - 10} y2={coreEdgeY(y)}
            stroke={MUTED} strokeWidth={1.4} markerEnd="url(#gt-arrow)" />
        )
      })}
      {right.map((t, i) => {
        const y = colYs(right.length)[i]
        return (
          <line key={`ra-${t.id}`} x1={coreR + 10} y1={coreEdgeY(y)}
            x2={rightX() - BOX_W / 2 - 4} y2={y}
            stroke={MUTED} strokeWidth={1.4} markerEnd="url(#gt-arrow)" />
        )
      })}
      {left.map((t, i) => (
        <Box key={`lb-${t.id}`} x={leftX()} y={colYs(left.length)[i]} t={t} />
      ))}
      {right.map((t, i) => (
        <Box key={`rb-${t.id}`} x={rightX()} y={colYs(right.length)[i]} t={t} />
      ))}
      <rect x={coreL} y={midY - CORE_H / 2} width={CORE_W} height={CORE_H}
        rx={6} fill={ACCENT} />
      <text x={W / 2} y={midY - CORE_H / 2 + 30} textAnchor="middle"
        fontSize={11} fill="white" opacity={0.75}>Core category</text>
      <Lines x={W / 2} y={midY + 10} lines={wrap(core, 24, 4)} size={15}
        fill="white" weight={600} />
      {overflow > 0 && (
        <text x={W - 8} y={H - 8} textAnchor="end" fontSize={11} fill={MUTED}
          fontStyle="italic">+{overflow} further categor{overflow === 1 ? 'y' : 'ies'} not shown</text>
      )}
    </svg>
  )
}

// ---------- thematic map ----------

export function ThematicMap({ themes }: { themes: any[] }) {
  const withKids = (themes ?? []).filter(t => (t.children ?? []).length)
  const shown = withKids.slice(0, 6)
  const hiddenThemes = withKids.length - shown.length
  if (!shown.length) return null
  const MAX_CODES = 8
  const COL = 215
  const W = Math.max(640, COL * shown.length)
  const maxRows = Math.min(MAX_CODES,
    Math.max(...shown.map(t => t.children.length)))
  const H = 120 + maxRows * 58 + 30
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: W }}
      role="img" aria-label="Thematic map">
      {shown.map((t, i) => {
        const x = i * COL + COL / 2
        const kids = t.children.slice(0, MAX_CODES)
        return (
          <g key={t.id}>
            {/* one spine, drawn before the boxes so no connector crosses a box */}
            {kids.length > 0 && (
              <line x1={x} y1={78} x2={x} y2={130 + (kids.length - 1) * 58}
                stroke={LINE} strokeWidth={1.2} />
            )}
            {kids.map((k: any, j: number) => {
              const y = 130 + j * 58
              return (
                <g key={k.id}>
                  <rect x={x - 92} y={y} width={184} height={44} rx={6}
                    fill="white" stroke={LINE} strokeWidth={1.1} />
                  <Lines x={x} y={y + 25}
                    lines={wrap(`${k.name} (${(k.excerpts ?? []).length})`, 26, 2)}
                    size={11.5} fill={INK} />
                </g>
              )
            })}
            {t.children.length > MAX_CODES && (
              <Lines x={x} y={130 + MAX_CODES * 58 + 8}
                lines={[`+${t.children.length - MAX_CODES} more codes`]}
                size={11} fill={MUTED} />
            )}
            <rect x={x - 96} y={16} width={192} height={62} rx={6} fill={ACCENT} />
            <Lines x={x} y={50} lines={wrap(t.name, 24, 3)} size={13}
              fill="white" weight={600} />
          </g>
        )
      })}
      {hiddenThemes > 0 && (
        <text x={W - 8} y={H - 6} textAnchor="end" fontSize={11} fill={MUTED}
          fontStyle="italic">+{hiddenThemes} further theme{hiddenThemes === 1 ? '' : 's'} not shown</text>
      )}
    </svg>
  )
}

// ---------- content-analysis frequencies ----------

export function FreqChart({ stats }: { stats: any }) {
  const allRows = stats?.rows ?? []
  const rows = allRows.slice(0, 15)
  const hiddenRows = allRows.length - rows.length
  if (!rows.length) return null
  const groups: string[] = stats.groups ?? []
  const max = Math.max(...rows.map((r: any) => r.count), 1)
  const W = 860, LABEL = 235, CHART = W - LABEL - 60
  const ROW = 32
  const H = rows.length * ROW + (groups.length ? 26 + Math.ceil(groups.length / 4) * 20 : 16)
    + (hiddenRows > 0 ? 20 : 0)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: W }}
      role="img" aria-label="Code frequencies">
      {rows.map((r: any, i: number) => {
        const y = i * ROW
        let xAcc = LABEL
        const byGroup = groups.map((g, gi) => ({ v: r.by_group?.[g] ?? 0, color: PALETTE[gi % PALETTE.length] }))
        // an old report may lack by_group breakdowns: fall back to one bar
        const segs = groups.length && byGroup.some(s => s.v > 0)
          ? byGroup
          : [{ v: r.count, color: ACCENT }]
        return (
          <g key={i}>
            <Lines x={LABEL - 10} y={y + ROW / 2 + 4}
              lines={wrap(r.code, 34, 1)} size={12} fill={INK} anchor="end" />
            {segs.map((s, si) => {
              const w = (s.v / max) * CHART
              const rect = (
                <rect key={si} x={xAcc} y={y + 7} width={Math.max(w, s.v ? 1.5 : 0)}
                  height={ROW - 14} fill={s.color} rx={2}>
                  <title>{groups.length ? `${groups[si]}: ${s.v}` : `${s.v}`}</title>
                </rect>
              )
              xAcc += w
              return rect
            })}
            <text x={xAcc + 6} y={y + ROW / 2 + 4} fontSize={11.5} fill={MUTED}>
              {r.count}
            </text>
          </g>
        )
      })}
      {hiddenRows > 0 && (
        <text x={LABEL} y={H - 6} fontSize={11} fill={MUTED} fontStyle="italic">
          Top 15 of {allRows.length} codes — the table below is complete
        </text>
      )}
      {groups.map((g, gi) => {
        const col = gi % 4, rowN = Math.floor(gi / 4)
        const ly = rows.length * ROW + 14 + rowN * 20
        return (
          <g key={g}>
            <rect x={LABEL + col * 150} y={ly} width={12} height={12}
              fill={PALETTE[gi % PALETTE.length]} rx={2} />
            <text x={LABEL + col * 150 + 18} y={ly + 10.5}
              fontSize={11.5} fill={INK}>{g.length > 16 ? g.slice(0, 15) + '…' : g}</text>
          </g>
        )
      })}
    </svg>
  )
}

// ---------- framework-matrix heatmap ----------
// also draws the literature-synthesis concept-by-paper matrix — the same
// grid with honest nouns (rowNoun="paper", colNoun="concept")

export function MatrixHeatmap({ stats, rowNoun = 'source', colNoun = 'code' }:
  { stats: any; rowNoun?: string; colNoun?: string }) {
  const allRows = stats?.rows ?? []
  const allCodes = stats?.codes ?? []
  const rows = allRows.slice(0, 20)
  const codes = allCodes.slice(0, 12)
  const hiddenNote = [
    allRows.length > rows.length ? `${allRows.length - rows.length} further ${rowNoun}s` : '',
    allCodes.length > codes.length ? `${allCodes.length - codes.length} further ${colNoun}s` : '',
  ].filter(Boolean).join(' and ')
  if (!rows.length || !codes.length) return null
  const grid = rows.map((r: any) =>
    codes.map((c: string) => (r.cells?.[c]?.n ?? 0)))
  const vmax = Math.max(...grid.flat(), 1)
  if (!grid.flat().some((v: number) => v)) return null
  const LABEL = 190, CELL = 58, HEAD = 64
  const W = LABEL + codes.length * CELL + 16
  const H = HEAD + rows.length * 34 + 8 + (hiddenNote ? 20 : 0)
  const shade = (v: number) => {
    if (!v) return '#f4f4f6'
    const t = v / vmax
    // light-grey-to-ink ramp
    const mix = (a: number, b: number) => Math.round(a + (b - a) * t)
    return `rgb(${mix(228, 42)}, ${mix(229, 44)}, ${mix(233, 50)})`
  }
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: W }}
      role="img" aria-label={`Matrix heatmap of ${colNoun}s by ${rowNoun}`}>
      {codes.map((c: string, x: number) => (
        <Lines key={c} x={LABEL + x * CELL + CELL / 2} y={30}
          lines={wrap(c, 12, 3)} size={10} fill={INK} />
      ))}
      {hiddenNote && (
        <text x={LABEL} y={H - 6} fontSize={11} fill={MUTED} fontStyle="italic">
          +{hiddenNote} not shown — the matrix table is complete
        </text>
      )}
      {rows.map((r: any, y: number) => (
        <g key={r.source}>
          <Lines x={LABEL - 8} y={HEAD + y * 34 + 21}
            lines={wrap(r.source, 28, 1)} size={11} fill={INK} anchor="end" />
          {codes.map((c: string, x: number) => {
            const v = grid[y][x]
            return (
              <g key={c}>
                <rect x={LABEL + x * CELL} y={HEAD + y * 34} width={CELL - 3}
                  height={30} rx={4} fill={shade(v)}>
                  <title>{`${r.source} × ${c}: ${v}`}</title>
                </rect>
                {v > 0 && (
                  <text x={LABEL + x * CELL + (CELL - 3) / 2} y={HEAD + y * 34 + 20}
                    textAnchor="middle" fontSize={11}
                    fill={v > 0.6 * vmax ? 'white' : INK}>{v}</text>
                )}
              </g>
            )
          })}
        </g>
      ))}
    </svg>
  )
}
