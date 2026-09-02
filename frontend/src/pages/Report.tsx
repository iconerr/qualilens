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
        <div className="row">
          <a href={`/api/runs/${id}/audit.json`} title="The complete audit trail: every event, decision, and checkpoint payload, as JSON">
            <button>Export audit log</button></a>
          <a href={`/api/runs/${id}/report.docx`}><button className="primary">Download .docx</button></a>
        </div>
      </div>

      {rep.config && Object.keys(rep.config).length > 0 && (
        <section>
          <h2>Method configuration</h2>
          <p className="desc">Every setup answer exactly as recorded for this run, frozen when the run
            started. Reproduce these verbatim in a methods section — the option text carries the
            methodological commitment.</p>
          <table className="freq"><tbody>
            {Object.entries(rep.config).map(([k, v]: [string, any]) => (
              <tr key={k}><td className="muted" style={{ width: 240 }}>{rep.config_labels?.[k] ?? k}</td>
                <td style={{ whiteSpace: 'pre-wrap' }}>{String(v ?? '').trim() || <span className="muted">(blank)</span>}</td></tr>
            ))}
            <tr><td className="muted">Provider and model</td><td>{rep.provider}/{rep.model}</td></tr>
          </tbody></table>
        </section>
      )}

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
          {stats.unit && <p className="desc">Unit counted: {stats.unit}. Rates are per 10,000 characters
            of source text and correct for unequal source and group sizes; compare groups on rates, not counts.</p>}
          <table className="freq">
            <thead><tr>
              <th>Code</th><th>Count</th><th>%</th><th>Sources</th>
              {'per_10k_chars' in (stats.rows[0] ?? {}) && <th>per 10k chars</th>}
              {(stats.groups ?? []).map((g: string) => <th key={g}>{g}</th>)}
              {(stats.groups ?? []).map((g: string) => <th key={`${g}-rate`}>{g} per 10k</th>)}
            </tr></thead>
            <tbody>
              {stats.rows.map((r: any) => (
                <tr key={r.code}>
                  <td>{r.code}</td><td>{r.count}</td><td>{r.pct}%</td><td>{r.sources}</td>
                  {'per_10k_chars' in r && <td>{r.per_10k_chars}</td>}
                  {(stats.groups ?? []).map((g: string) => <td key={g}>{r.by_group?.[g] ?? 0}</td>)}
                  {(stats.groups ?? []).map((g: string) => <td key={`${g}-rate`}>{r.by_group_per_10k?.[g] ?? '—'}</td>)}
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
              {r.cited_work && (
                <p className="desc" style={{ margin: '6px 0' }}>
                  <b>Findings the paper attributes to other work</b> (not used in the synthesis): {r.cited_work}
                </p>
              )}
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
          {rep.audit?.events} logged events. Model usage: {usage.calls ?? 0} calls,{' '}
          {((usage.input_tokens ?? 0) / 1000).toFixed(0)}k input /
          {' '}{((usage.output_tokens ?? 0) / 1000).toFixed(0)}k output tokens.
          {rep.audit?.models_used && Object.keys(rep.audit.models_used).length > 0 && (
            <> Models that answered: {Object.entries(rep.audit.models_used)
              .map(([m, n]: [string, any]) => `${m} (${n})`).join(', ')}.</>)}
          {typeof rep.audit?.excerpts_unlocated === 'number' && (
            <> Evidence: {rep.audit.excerpts_located} excerpts located verbatim,{' '}
              {rep.audit.excerpts_unlocated} unverified.</>)}
          {rep.audit?.branched_from && (
            <> Branched from run {rep.audit.branched_from} at “{rep.audit.branched_at}”.</>)}
        </p>
        <p className="desc">Researcher checkpoints:</p>
        <table className="freq"><tbody>
          {(rep.audit?.checkpoints ?? []).map((c: any, i: number) => (
            <tr key={i}>
              <td style={{ width: 260 }}><b>{c.title}</b> <span className="muted small">({c.status})</span></td>
              <td className="small">{summaryLine(c.summary)}</td>
            </tr>
          ))}
        </tbody></table>
        <p className="desc">The complete log — every model call, every decision with its parameters,
          every checkpoint payload — is in <b>Export audit log</b> at the top of this page.</p>
      </section>
    </div>
  )
}

function summaryLine(summ: any): string {
  if (!summ || Object.keys(summ).length === 0) return 'approved without changes'
  const bits: string[] = []
  if (summ.decisions) bits.push('decisions: ' + Object.entries(summ.decisions).map(([k, v]) => `${k} ${v}`).join(', '))
  if (summ.renamed_to?.length) bits.push('renamed to: ' + summ.renamed_to.slice(0, 8).join('; ') + (summ.renamed_to.length > 8 ? '…' : ''))
  if (summ.added?.length) bits.push('added: ' + summ.added.slice(0, 8).join('; '))
  if (summ.excerpts_removed) bits.push(`excerpts removed: ${summ.excerpts_removed}`)
  if (summ.extraction_rows_edited) bits.push(`extraction rows edited: ${summ.extraction_rows_edited}`)
  if (summ.papers_excluded) bits.push(`papers excluded: ${summ.papers_excluded}`)
  return bits.join(' · ') || 'approved without changes'
}

// an excerpt is located when its quote was found verbatim in the source;
// older reports carry no flag and are shown as they were
const isLocated = (e: any) =>
  'located' in e ? !!e.located : (!('start_char' in e) || e.start_char !== null)

function Excerpts({ list, onView }: { list: any[]; onView: (e: any) => void }) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? list : list.slice(0, 6)
  return (
    <>
      {visible.map((e: any, i: number) => (
        <div key={i} className={`excerpt ${isLocated(e) ? '' : 'unverified'}`}>
          {isLocated(e)
            ? <>“{e.quote}”</>
            : <><span className="unverified-tag" title="The model returned this text under the code, but it could not be found verbatim in the source — likely paraphrase. Not a quotation.">not located verbatim</span> {e.quote}</>}
          {e.memo && <div className="memo">{e.memo}</div>}
          <div className="meta">
            {e.source}
            {typeof e.page === 'number' && <>, p. {e.page}</>}
            {typeof e.confidence === 'number' && <> · conf {Math.round(e.confidence * 100)}%</>}
            {' · '}
            <a href="#" onClick={ev => { ev.preventDefault(); onView(e) }}>
              {isLocated(e) ? 'view in coded document' : 'open document (listed under Not located)'}
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
