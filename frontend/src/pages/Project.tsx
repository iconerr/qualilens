// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, statusLabel, type Project } from '../api'

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const [p, setP] = useState<Project | null>(null)
  const [error, setError] = useState('')
  const nav = useNavigate()

  const load = () => api.project(id!).then(setP).catch(e => setError(String(e.message ?? e)))
  useEffect(() => { load() }, [id])

  const startRun = async () => {
    try {
      const { run_id } = await api.startRun(id!)
      nav(`/runs/${run_id}`)
    } catch (e: any) { setError(String(e.message ?? e)) }
  }

  if (!p) return <div className="page">{error ? <div className="error-box">{error}</div> : 'Loading…'}</div>

  return (
    <div className="page">
      <h1>{p.name}</h1>
      <p className="sub">{p.method.replace('_', ' ')} · created {new Date(p.created_at * 1000).toLocaleString()}</p>
      {error && <div className="error-box">{error}</div>}

      <div className="card">
        <div className="row spread">
          <h3 style={{ margin: 0 }}>Runs</h3>
          <button className="primary" onClick={startRun}>New run</button>
        </div>
        {p.runs.length === 0 && <p className="desc mt">No runs yet.</p>}
        {p.runs.map(r => (
          <div key={r.id} className="run-row" role="link" tabIndex={0}
            title="Open this run"
            onClick={() => nav(`/runs/${r.id}`)}
            onKeyDown={e => {
              // only the row itself — Enter on an inner button must not
              // also fire a navigation
              if (e.key === 'Enter' && e.target === e.currentTarget) nav(`/runs/${r.id}`)
            }}>
            <div>
              <b>Run of {new Date(r.created_at * 1000).toLocaleString()}</b>
              <div className="muted small">
                {r.status === 'completed' ? 'Completed — the report is ready'
                  : r.status === 'awaiting_review' ? `Waiting for your review: ${statusLabel(r.stage_name ?? '')}`
                    : r.status === 'running' ? `Running: ${statusLabel(r.stage_name ?? '')}`
                      : r.status === 'failed' ? 'Failed — open it to resume'
                        : 'Cancelled'}
              </div>
            </div>
            <div className="row">
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
      </div>

      <div className="card">
        <h3>Data sources</h3>
        {p.sources.map(s => (
          <div key={s.id} className="row spread" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
            <span>{s.filename} {s.grp && <span className="count-pill">{s.grp}</span>}
              <span className="muted small"> · {s.kind} · {Math.round(s.chars / 1000)}k chars</span></span>
            <span className={`badge ${s.status}`}>{statusLabel(s.status)}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Configuration</h3>
        <table className="freq"><tbody>
          {Object.entries(p.config).map(([k, v]) => (
            <tr key={k}><td className="muted" style={{ width: 220 }}>{k}</td>
              <td style={{ whiteSpace: 'pre-wrap' }}>{String(v)}</td></tr>
          ))}
        </tbody></table>
      </div>
    </div>
  )
}
