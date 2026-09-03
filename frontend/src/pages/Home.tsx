// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, dayLabel, methodLabel, statusLabel, type Project } from '../api'
import UpdateHint from '../UpdateHint'
import MethodGlyph from '../Glyphs'

export default function Home() {
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [error, setError] = useState('')
  const nav = useNavigate()

  const load = () => api.projects().then(setProjects).catch(e => setError(String(e.message ?? e)))
  useEffect(() => { load() }, [])

  const del = async (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation()
    if (!confirm(`Delete project "${name}" and all its runs, codes, and reports? This cannot be undone.`)) return
    try {
      await api.deleteProject(id)
      load()
    } catch (err: any) { setError(String(err.message ?? err)) }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Projects</h1>
        <p className="sub">One analysis each: a method, a dataset, and its runs. All of it on this computer.</p>
      </div>
      <UpdateHint />
      {error && <div className="error-box">{error}</div>}
      {projects && projects.length === 0 && (
        <div className="card empty-state">
          <svg className="es-mark" width="56" height="56" viewBox="0 0 56 56" aria-hidden="true">
            <rect x="8" y="6" width="40" height="44" rx="6" fill="none"
              stroke="currentColor" strokeWidth="2" />
            <line x1="16" y1="17" x2="40" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <line x1="16" y1="25" x2="34" y2="25" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".55" />
            <rect x="14" y="31" width="16" height="6" rx="3" fill="#d9a520" opacity=".85" />
            <line x1="34" y1="34" x2="40" y2="34" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".55" />
            <line x1="16" y1="43" x2="38" y2="43" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".75" />
          </svg>
          <h3>Begin your first analysis</h3>
          <p>Choose a method, answer its setup questions, add your transcripts or
            documents, and run — pausing at checkpoints where your judgment shapes
            the coding.</p>
          <Link to="/new"><button className="primary">New analysis</button></Link>
        </div>
      )}
      {projects && projects.length > 0 && (
        <section className="panel">
          {projects.map(p => (
            <div key={p.id} className="lrow clickable" role="link" tabIndex={0}
              onClick={() => nav(`/projects/${p.id}`)}
              onKeyDown={e => { if (e.key === 'Enter' && e.target === e.currentTarget) nav(`/projects/${p.id}`) }}>
              <MethodGlyph method={p.method} className="lrow-glyph" />
              <div className="lrow-main">
                <div className="lrow-title">{p.name}</div>
                <div className="lrow-meta">
                  {methodLabel(p.method)} · {p.n_sources} source{p.n_sources === 1 ? '' : 's'} · {dayLabel(p.created_at)}
                </div>
              </div>
              <div className="lrow-actions">
                {p.latest_run && (
                  <span className={`badge ${p.latest_run.status}`} role="link"
                    tabIndex={0} style={{ cursor: 'pointer' }} title="Open the latest run"
                    onClick={e => { e.stopPropagation(); nav(`/runs/${p.latest_run!.id}`) }}
                    onKeyDown={e => {
                      if (e.key === 'Enter') { e.stopPropagation(); nav(`/runs/${p.latest_run!.id}`) }
                    }}>
                    {statusLabel(p.latest_run.status)}
                  </span>
                )}
                <button className="small quiet" onClick={e => del(e, p.id, p.name)}>Delete</button>
                <span className="chev" aria-hidden="true">›</span>
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
