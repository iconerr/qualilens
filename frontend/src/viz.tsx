// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

// Method-appropriate report visualizations, hand-rolled SVG (no dependencies):
// the grounded theory model, the thematic map, a code-frequency chart, and a
// framework-matrix heatmap. Each renders nothing when its data is absent.

const INK = '#22252a'
const MUTED = '#6b7280'
const ACCENT = '#1f3a5f'
const ACCENT_SOFT = '#e8eef6'
const LINE = '#c9c7bf'
const PALETTE = [ACCENT, '#d9a520', '#5a8f6f', '#a1657c', '#7a6fb0', '#b08948']

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
  const core = stats?.core?.name ?? 'Core category'
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

  const W = 900, H = 620, cx = W / 2, cy = H / 2
  const rx = 330, ry = 225
  const coreRx = 158, coreRy = 82
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: 860 }}
      role="img" aria-label="Grounded theory model">
      <defs>
        <marker id="gt-arrow" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill={MUTED} />
        </marker>
      </defs>
      {cats.map((t, i) => {
        const ang = (2 * Math.PI * i) / cats.length - Math.PI / 2
        const x = cx + rx * Math.cos(ang), y = cy + ry * Math.sin(ang)
        const d = Math.hypot(cx - x, cy - y)
        const ux = (cx - x) / d, uy = (cy - y) / d
        const sx = x + ux * 105, sy = y + uy * 48
        // land the arrowhead on the core ELLIPSE boundary (plus margin), so
        // the ellipse never paints over it
        const tEdge = 1 / Math.sqrt((ux / coreRx) ** 2 + (uy / coreRy) ** 2)
        const ex = cx - ux * (tEdge + 8), ey = cy - uy * (tEdge + 8)
        const rel = relBy[t.id]?.slice(0, 2).join(' / ')
        return (
          <g key={t.id}>
            <line x1={sx} y1={sy} x2={ex} y2={ey} stroke={MUTED}
              strokeWidth={1.4} markerEnd="url(#gt-arrow)" />
            {rel && (
              <g>
                <rect x={(sx + ex) / 2 - 62} y={(sy + ey) / 2 - 22} width={124}
                  height={26} rx={5} fill="white" opacity={0.9} />
                <Lines x={(sx + ex) / 2} y={(sy + ey) / 2 - 8}
                  lines={wrap(rel, 22, 2)} size={11} fill={MUTED} />
              </g>
            )}
            <rect x={x - 100} y={y - 42} width={200} height={84} rx={10}
              fill={ACCENT_SOFT} stroke={ACCENT} strokeWidth={1.4} />
            <Lines x={x} y={y + 4} lines={wrap(t.name, 22, 3)} size={13} fill={INK} />
          </g>
        )
      })}
      <ellipse cx={cx} cy={cy} rx={coreRx} ry={coreRy} fill={ACCENT} />
      <Lines x={cx} y={cy + 4} lines={wrap(core, 20, 3)} size={15}
        fill="white" weight={700} />
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
            {kids.map((k: any, j: number) => {
              const y = 130 + j * 58
              return (
                <g key={k.id}>
                  <line x1={x} y1={78} x2={x} y2={y} stroke={LINE} strokeWidth={1.2} />
                  <rect x={x - 92} y={y} width={184} height={44} rx={8}
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
            <rect x={x - 96} y={16} width={192} height={62} rx={10} fill={ACCENT} />
            <Lines x={x} y={50} lines={wrap(t.name, 24, 3)} size={13}
              fill="white" weight={700} />
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
    if (!v) return '#f6f5f1'
    const t = v / vmax
    // white-to-accent ramp
    const mix = (a: number, b: number) => Math.round(a + (b - a) * t)
    return `rgb(${mix(232, 31)}, ${mix(238, 58)}, ${mix(246, 95)})`
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
