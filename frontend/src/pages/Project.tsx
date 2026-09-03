// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, dateLabel, methodLabel, settingValue, sizeLabel, statusLabel, type Meta, type Project } from '../api'
import MethodGlyph from '../Glyphs'

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const [p, setP] = useState<Project | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [error, setError] = useState('')
  const nav = useNavigate()

  const load = () => api.project(id!).then(setP).catch(e => setError(String(e.message ?? e)))
  useEffect(() => { load() }, [id])
  useEffect(() => { api.meta().then(setMeta).catch(() => { /* labels fall back to keys */ }) }, [])

  // the setting's own question label, as the wizard showed it
  const labelOf = (key: string): string => {
    if (key === 'provider') return 'Provider'
    if (key === 'model') return 'Model'
    const q = meta?.methods.find(m => m.id === p?.method)?.questions.find(q => q.key === key)
    return q?.label ?? key.replaceAll('_', ' ')
  }
  const valueOf = (key: string, v: unknown): string => {
    if (key === 'provider') return meta?.providers.find(x => x.id === v)?.label ?? String(v)
    return settingValue(v)
  }

  const startRun = async () => {
    try {
      const { run_id } = await api.startRun(id!)
      nav(`/runs/${run_id}`)
    } catch (e: any) { setError(String(e.message ?? e)) }
  }

  if (!p) return <div className="page">{error ? <div className="error-box">{error}</div> : 'Loading…'}</div>

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="with-glyph"><MethodGlyph method={p.method} size={26} />{p.name}</h1>
        <p className="sub">{methodLabel(p.method)} · created {dateLabel(p.created_at)}</p>
      </div>
      {error && <div className="error-box">{error}</div>}

      <section className="panel">
        <div className="panel-head spread">
          <span className="eyebrow">Runs</span>
          <button className="primary small" onClick={startRun}>New run</button>
        </div>
        {p.runs.length === 0 && <p className="desc" style={{ padding: '0 20px 16px' }}>No runs yet.</p>}
        {p.runs.map(r => (
          <div key={r.id} className="lrow clickable" role="link" tabIndex={0}
            title="Open this run"
            onClick={() => nav(`/runs/${r.id}`)}
            onKeyDown={e => {
              // only the row itself — Enter on an inner button must not
              // also fire a navigation
              if (e.key === 'Enter' && e.target === e.currentTarget) nav(`/runs/${r.id}`)
            }}>
            <div className="lrow-main">
              <div className="lrow-title">Run of {dateLabel(r.created_at)}</div>
              <div className="lrow-meta">
                {r.status === 'completed' ? 'Completed — the report is ready'
                  : r.status === 'awaiting_review' ? `Waiting for your review: ${statusLabel(r.stage_name ?? '')}`
                    : r.status === 'running' ? `Running: ${statusLabel(r.stage_name ?? '')}`
                      : r.status === 'failed' ? 'Failed — open it to resume'
                        : 'Cancelled'}
              </div>
            </div>
            <div className="lrow-actions">
              {/* only the real controls swallow the click — the badge and
                  the chevron still open the run, as the row promises */}
              <span className={`badge ${r.status}`}>{statusLabel(r.status)}</span>
              {r.status === 'completed' && <>
                <Link to={`/runs/${r.id}/report`} onClick={e => e.stopPropagation()}>
                  <button className="small primary">Open report</button></Link>
                <a href={`/api/runs/${r.id}/report.docx`} onClick={e => e.stopPropagation()}>
                  <button className="small">Word</button></a>
              </>}
              {r.status === 'awaiting_review' &&
                <Link to={`/runs/${r.id}`} onClick={e => e.stopPropagation()}>
                  <button className="small primary">Review now</button></Link>}
              {r.status === 'failed' &&
                <Link to={`/runs/${r.id}`} onClick={e => e.stopPropagation()}>
                  <button className="small">Open to resume</button></Link>}
              <span className="chev" aria-hidden="true">›</span>
            </div>
          </div>
        ))}
      </section>

      <div className="grid2">
      <section className="panel">
        <div className="panel-head"><span className="eyebrow">Sources</span>
          <span className="panel-note">{p.sources.length} file{p.sources.length === 1 ? '' : 's'}</span></div>
        {p.sources.map(s => (
          <div key={s.id} className="lrow compact">
            <div className="lrow-main">
              <div className="lrow-title">{s.filename} {s.grp && <span className="count-pill">{s.grp}</span>}</div>
              <div className="lrow-meta">{s.kind}{s.chars > 0 ? ` · ${sizeLabel(s.chars)}` : ''}</div>
            </div>
            <span className={`badge ${s.status}`}>{statusLabel(s.status)}</span>
          </div>
        ))}
      </section>

      <section className="panel">
        <div className="panel-head"><span className="eyebrow">Configuration</span></div>
        <div className="panel-body">
          <table className="facts"><tbody>
            {Object.entries(p.config).map(([k, v]) => (
              <tr key={k}><td className="muted">{labelOf(k)}</td>
                <td style={{ whiteSpace: 'pre-wrap' }} className={k === 'model' ? 'mono' : ''}>
                  {valueOf(k, v) || <span className="muted">(blank)</span>}</td></tr>
            ))}
          </tbody></table>
        </div>
      </section>
      </div>
    </div>
  )
}
