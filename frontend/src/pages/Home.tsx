// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, statusLabel, type Project } from '../api'

const METHOD_LABELS: Record<string, string> = {
  grounded_theory: 'Grounded Theory',
  thematic: 'Thematic Analysis',
  content_analysis: 'Content Analysis',
  framework: 'Framework / Deductive',
  literature_synthesis: 'Literature Synthesis',
}

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
      <h1>Projects</h1>
      <p className="sub">Each project is one analysis: a method, a dataset, and its runs. Everything is stored locally.</p>
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
      {projects?.map(p => (
        <div key={p.id} className="card clickable" onClick={() => nav(`/projects/${p.id}`)}>
          <div className="row spread">
            <div>
              <div className="proj-title-row">
                <h3>{p.name}</h3>
                <span className="method-pill">{METHOD_LABELS[p.method] ?? p.method}</span>
              </div>
              <p className="desc">
                {p.n_sources} source{p.n_sources === 1 ? '' : 's'}
                {' · created '}{new Date(p.created_at * 1000).toLocaleDateString()}
              </p>
            </div>
            <div className="row">
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
              <button className="small danger" onClick={e => del(e, p.id, p.name)}>Delete</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
