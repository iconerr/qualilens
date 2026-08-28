// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useMemo, useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { FreqChart, GTModel, MatrixHeatmap, ThematicMap } from '../viz'

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const [rep, setRep] = useState<any | null>(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const nav = useNavigate()

  useEffect(() => { api.report(id!).then(setRep).catch(e => setError(String(e.message ?? e))) }, [id])

  // per-source excerpt counts for the Sources overview, from the report itself
  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    const walk = (list: any[]) => list?.forEach((e: any) => {
      counts[e.source_id] = (counts[e.source_id] ?? 0) + 1
    })
    rep?.themes?.forEach((t: any) => {
      walk(t.excerpts)
      t.children?.forEach((c: any) => walk(c.excerpts))
    })
    return counts
  }, [rep])

  const openInReader = (e: any) => {
    const q = e.id ? `?ex=${e.id}` : ''
    nav(`/runs/${id}/sources/${e.source_id}${q}`)
  }

  if (!rep) return <div className="page">{error ? <div className="error-box">{error}</div> : 'Loading…'}</div>

  const stats = rep.stats ?? {}
  const usage = rep.audit?.usage ?? {}

  return (
    <div className="page page-wide report">
      {error && <div className="error-box">{error}</div>}
      <div className="row spread">
        <div>
          <h1>{rep.title}</h1>
          <p className="sub">
            <Link to={`/runs/${id}`}>← run</Link>
            {' · '}{rep.provider}/{rep.model}
            {' · '}{new Date(rep.generated_at * 1000).toLocaleString()}
          </p>
        </div>
        <a href={`/api/runs/${id}/report.docx`}><button className="primary">Download .docx</button></a>
      </div>

      <section>
        <h2>Sources</h2>
        <p className="desc">Open any source to read it with its coded spans highlighted —
          the fastest way to audit what the coding caught and what it missed.</p>
        <div className="row">
          {rep.sources?.map((s: any) => (
            <button key={s.id} className="small"
              onClick={() => nav(`/runs/${id}/sources/${s.id}`)}>
              {s.filename} <span className="count-pill">{sourceCounts[s.id] ?? 0}</span>
            </button>
          ))}
        </div>
      </section>

      {rep.sections?.map((s: any, i: number) => (
        <section key={i}>
          <h2>{s.heading}</h2>
          <div className="narrative">
            {String(s.body).split('\n').map((p: string, j: number) => p.trim() && <p key={j}>{p}</p>)}
          </div>
        </section>
      ))}

      {stats.kind === 'gt_model' && (
        <section>
          <h2>The Grounded Theory Model</h2>
          <p className="desc">A left-to-right paradigm flow: each category prints its
            core-directed relationship verbatim — conditions, context, and dimensions
            to the left of the core, strategies and consequences to its right.</p>
          <div className="viz-card"><GTModel themes={rep.themes} stats={stats} /></div>
        </section>
      )}

      {rep.method === 'thematic' && (
        <section>
          <h2>Thematic Map</h2>
          <p className="desc">Themes and their constituent codes (excerpt counts in
            parentheses).</p>
          <div className="viz-card"><ThematicMap themes={rep.themes} /></div>
        </section>
      )}

      {stats.kind === 'content_frequencies' && (
        <section>
          <h2>Code Frequencies</h2>
          <div className="viz-card"><FreqChart stats={stats} /></div>
          <table className="freq">
            <thead><tr>
              <th>Code</th><th>Count</th><th>%</th><th>Sources</th>
              {(stats.groups ?? []).map((g: string) => <th key={g}>{g}</th>)}
            </tr></thead>
            <tbody>
              {stats.rows.map((r: any) => (
                <tr key={r.code}>
                  <td>{r.code}</td><td>{r.count}</td><td>{r.pct}%</td><td>{r.sources}</td>
                  {(stats.groups ?? []).map((g: string) => <td key={g}>{r.by_group?.[g] ?? 0}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {stats.kind === 'framework_matrix' && (
        <section>
          <h2>Framework Matrix</h2>
          <div className="viz-card"><MatrixHeatmap stats={stats} /></div>
          <div style={{ overflowX: 'auto' }}>
            <table className="freq">
              <thead><tr><th>Source</th>{stats.codes.map((c: string) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>
                {stats.rows.map((row: any) => (
                  <tr key={row.source}>
                    <td><b>{row.source}</b></td>
                    {stats.codes.map((c: string) => {
                      const cell = row.cells?.[c]
                      return <td key={c} className="small">{cell?.n ? `${cell.summary} (${cell.n})` : '—'}</td>
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {stats.kind === 'concept_matrix' && (
        <section>
          <h2>Concept-by-Paper Matrix</h2>
          <p className="desc">Each cell states what one paper contributes to one concept,
            summarized strictly from that paper's extraction quotes; the count is the
            number of supporting passages.</p>
          <div className="viz-card"><MatrixHeatmap stats={stats} rowNoun="paper" colNoun="concept" /></div>
          <div style={{ overflowX: 'auto' }}>
            <table className="freq">
              <thead><tr><th>Paper</th>{stats.codes.map((c: string) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>
                {stats.rows.map((row: any) => (
                  <tr key={row.source}>
                    <td><b>{row.source}</b></td>
                    {stats.codes.map((c: string) => {
                      const cell = row.cells?.[c]
                      return <td key={c} className="small">{cell?.n ? `${cell.summary} (${cell.n})` : '—'}</td>
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(stats.excluded ?? []).length > 0 && (
            <p className="desc">Excluded from the synthesis at the extraction review:{' '}
              {stats.excluded.map((x: any) => x.label).join(' · ')}.</p>
          )}
        </section>
      )}

      <section>
        <h2>{rep.method === 'literature_synthesis'
          ? 'Evidence: Concepts → Excerpts'
          : 'Evidence: Themes → Codes → Excerpts'}</h2>
        <p className="desc">Every excerpt links to its exact highlighted place in the coded document.</p>
        {rep.themes?.map((t: any) => (
          <div key={t.id} className="theme-block card">
            <div className="theme-head" onClick={() => setOpen(o => ({ ...o, [t.id]: !o[t.id] }))}>
              <h3>{open[t.id] ? '▾' : '▸'} {t.name}</h3>
              <span className="count-pill">
                {(t.excerpts ?? []).length + (t.children ?? []).reduce(
                  (n: number, c: any) => n + (c.excerpts ?? []).length, 0)} excerpts
              </span>
            </div>
            <p className="desc" style={{ marginTop: 4 }}>{t.definition}</p>
            {open[t.id] && (
              <>
                <Excerpts list={t.excerpts ?? []} onView={openInReader} />
                {(t.children ?? []).map((c: any) => (
                  <div key={c.id} style={{ marginLeft: 16, marginTop: 10 }}>
                    <b>{c.name}</b> <span className="muted small">{c.definition}</span>
                    <Excerpts list={c.excerpts ?? []} onView={openInReader} />
                  </div>
                ))}
              </>
            )}
          </div>
        ))}
      </section>

      {stats.kind === 'concept_matrix' && (stats.extraction_rows ?? []).length > 0 && (
        <section>
          <h2>Appendix: Extraction Table</h2>
          <p className="desc">The per-paper structured extraction as you approved it —
            the ground the synthesis was built on.</p>
          {stats.extraction_rows.map((r: any) => (
            <div key={r.source_id} className="card">
              <div className="row spread">
                <b>{r.label || r.filename}
                  {r.excluded && <span className="muted"> (excluded from the synthesis)</span>}</b>
                <button className="small" onClick={() => nav(`/runs/${id}/sources/${r.source_id}`)}>
                  open coded paper</button>
              </div>
              {r.citation && <p className="desc" style={{ margin: '4px 0' }}><i>{r.citation}</i></p>}
              {Object.entries(r.fields ?? {}).map(([k, v]: [string, any]) => v && (
                <p key={k} className="narrative" style={{ margin: '6px 0' }}>
                  <b>{stats.field_labels?.[k] ?? k}:</b> {v}
                </p>
              ))}
            </div>
          ))}
        </section>
      )}

      {(rep.source_summaries ?? []).some((s: any) => s.summary) && (
        <section>
          <h2>Appendix: Source Summaries (Familiarization)</h2>
          {rep.source_summaries.filter((s: any) => s.summary).map((s: any) => (
            <div key={s.source_id} className="card">
              <b>{s.source}</b>
              <p className="narrative" style={{ margin: '6px 0' }}>{s.summary}</p>
              {s.memo && <p className="desc"><i>Analytic memo:</i> {s.memo}</p>}
            </div>
          ))}
        </section>
      )}

      <section>
        <h2>Audit Trail</h2>
        <p className="desc">
          {rep.audit?.events} logged events · researcher checkpoints:{' '}
          {(rep.audit?.checkpoints ?? []).map((c: any) =>
            `${c.title} (${c.status})`).join('; ') || 'none'}.
          {' '}Model usage: {usage.calls ?? 0} calls, {((usage.input_tokens ?? 0) / 1000).toFixed(0)}k input /
          {' '}{((usage.output_tokens ?? 0) / 1000).toFixed(0)}k output tokens.
        </p>
      </section>
    </div>
  )
}

function Excerpts({ list, onView }: { list: any[]; onView: (e: any) => void }) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? list : list.slice(0, 6)
  return (
    <>
      {visible.map((e: any, i: number) => (
        <div key={i} className="excerpt">
          “{e.quote}”
          {e.memo && <div className="memo">{e.memo}</div>}
          <div className="meta">
            {e.source}
            {typeof e.page === 'number' && <>, p. {e.page}</>}
            {typeof e.confidence === 'number' && <> · conf {Math.round(e.confidence * 100)}%</>}
            {' · '}
            <a href="#" onClick={ev => { ev.preventDefault(); onView(e) }}>
              view in coded document
            </a>
          </div>
        </div>
      ))}
      {list.length > 6 && (
        <button className="small" onClick={() => setShowAll(s => !s)}>
          {showAll ? 'Show fewer' : `Show all ${list.length}`}
        </button>
      )}
    </>
  )
}
