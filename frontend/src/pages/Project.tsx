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
          <div key={r.id} className="row spread" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
            <span>
              <Link to={`/runs/${r.id}`}>{new Date(r.created_at * 1000).toLocaleString()}</Link>
              <span className="muted small"> · {r.stage_name ?? 'finished'}</span>
            </span>
            <span className={`badge ${r.status}`}>{statusLabel(r.status)}</span>
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
