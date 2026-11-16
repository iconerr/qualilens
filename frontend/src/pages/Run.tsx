// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { dateLabel, api, statusLabel, type Run } from '../api'
import { ask } from '../ask'
import { CheckpointPanel } from './Checkpoint'

const TERMINAL = new Set(['completed', 'cancelled', 'failed'])

export default function RunPage() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [run, setRun] = useState<Run | null>(null)
  const [events, setEvents] = useState<{ ts: number; kind: string; message: string }[]>([])
  const [error, setError] = useState('')
  const [pollEpoch, setPollEpoch] = useState(0)  // bump to restart polling (resume)
  const [resolvedCp, setResolvedCp] = useState('')  // hide a checkpoint just resolved
  const lastTs = useRef(0)
  const logRef = useRef<HTMLDivElement>(null)

  // navigating to another run (e.g. a branch) must not carry this run's
  // event log or dismissed-checkpoint state along
  useEffect(() => { setEvents([]); lastTs.current = 0; setResolvedCp('') }, [id])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setInterval> | undefined
    const tick = async () => {
      try {
        const r = await api.run(id!)
        if (!alive) return
        setRun(r)
        const evs = await api.events(id!, lastTs.current)
        if (!alive) return
        if (evs.length) {
          lastTs.current = evs[evs.length - 1].ts
          setEvents(prev => [...prev.slice(-300), ...evs])
        }
        // a finished run does not change any more — stop hammering the API
        if (TERMINAL.has(r.status) && timer) clearInterval(timer)
      } catch (e: any) { if (alive) setError(String(e.message ?? e)) }
    }
    tick()
    timer = setInterval(tick, 1500)
    return () => { alive = false; if (timer) clearInterval(timer) }
  }, [id, pollEpoch])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [events])

  const revisit = async (stage: string, label: string) => {
    if (!(await ask({
      title: `Revisit “${label}”?`,
      body: ['This starts a new run with everything this run had at that review, including '
        + 'the coding, the evidence, and your earlier decisions. The review reopens there for '
        + 'you to decide differently. This run and its report stay as they are.',
        'The stages after the review run again on the new run and are billed again.'],
      confirm: 'Start the new run',
    }))) return
    try {
      const { run_id } = await api.branchRun(id!, stage)
      nav(`/runs/${run_id}`)
    } catch (e: any) { setError(String(e.message ?? e)) }
  }

  if (!run) return <div className="page">{error ? <div className="error-box">{error}</div> : 'Loading…'}</div>

  const prog = run.progress ?? {}
  const pct = prog.total ? Math.round(100 * (prog.done ?? 0) / prog.total) : null
  const usage = run.usage ?? {}

  return (
    <div className="page">
      <div className="page-head">
        <h1>{run.project_name}</h1>
        <p className="sub">
          <Link to={`/projects/${run.project_id}`}>← project</Link>
          {' · '}run of {dateLabel(run.created_at)}
          {' · '}<span className={`badge ${run.status}`}>{statusLabel(run.status)}</span>
        </p>
      </div>
      {error && <div className="error-box">{error}</div>}

      {run.status === 'failed' && (
        <div className="error-box">
          The run failed at stage “{run.stage_name}”: {run.error}
          <div className="mt">
            <button onClick={async () => {
              try {
                await api.resumeRun(id!)
                setError('')
                setPollEpoch(n => n + 1)  // restart polling
              } catch (e: any) { setError(String(e.message ?? e)) }
            }}>
              Resume from this stage
            </button>
            <span className="small" style={{ marginLeft: 10 }}>
              Completed work is preserved — resuming does not re-bill finished segments.
            </span>
          </div>
        </div>
      )}

      {run.status === 'completed' && run.has_report && (
        <div className="card done-card">
          <h3>Analysis complete</h3>
          <p className="desc">The report is ready: browse it, export Word, or export the complete
            audit trail (every call, decision, and checkpoint) as JSON.</p>
          <div className="row mt">
            <Link to={`/runs/${id}/report`}><button className="primary">Open report</button></Link>
            <a href={`/api/runs/${id}/report.docx`}><button>Download .docx</button></a>
            <a href={`/api/runs/${id}/audit.json`}><button>Export audit log</button></a>
          </div>
        </div>
      )}

      {run.pending_checkpoint && run.status === 'awaiting_review'
        && run.pending_checkpoint.id !== resolvedCp && (
        <CheckpointPanel run={run} runId={id!} cp={run.pending_checkpoint} onError={setError}
          onResolved={() => { setResolvedCp(run.pending_checkpoint!.id); setError('') }} />
      )}

      <div className="grid2">
        <section className="panel">
          <div className="panel-head"><span className="eyebrow">Pipeline</span></div>
          <div className="panel-body stagelist">
            {run.stages.map((s, i) => {
              const cls = i < run.stage_index ? 'done' : i === run.stage_index ? 'current' : 'pending'
              const revisitable = s.kind === 'checkpoint' && i < run.stage_index
                && run.status !== 'running'
              return (
                <div key={s.name} className={`stage-item ${cls}`}>
                  <div className="dot" />
                  <div>
                    <div className="s-label">{s.label}</div>
                    <div className="s-kind">{s.kind === 'checkpoint' ? 'your review' : 'automated'}</div>
                    {revisitable && (
                      <button className="small" style={{ marginTop: 4 }}
                        title="Start a new run from this review, carrying everything up to it"
                        onClick={() => revisit(s.name, s.label)}>
                        ↩ Revisit this review…
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>
        <section className="panel">
          <div className="panel-head"><span className="eyebrow">Progress</span></div>
          <div className="panel-body">
          {run.status === 'running' && (
            <>
              {pct !== null && <><div className="progressbar"><div style={{ width: `${pct}%` }} /></div>
                <p className="desc">{prog.detail} ({prog.done}/{prog.total})</p></>}
              {pct === null && <p className="desc">{prog.detail ?? 'Working…'}</p>}
            </>
          )}
          <p className="desc">
            Model usage so far: {usage.calls ?? 0} calls ·{' '}
            {((usage.input_tokens ?? 0) / 1000).toFixed(0)}k in / {((usage.output_tokens ?? 0) / 1000).toFixed(0)}k out
          </p>
          {(run.status === 'running' || run.status === 'awaiting_review') && (
            <button className="small danger" onClick={async () => {
              if (await ask({
                title: 'Cancel this run?',
                body: ['Cancelling is final. This run cannot be resumed. The reviews it has '
                  + 'passed stay available. “Revisit this review…” starts a new run with the '
                  + 'work up to that point.'],
                confirm: 'Cancel the run', cancel: 'Keep the run', danger: true,
              }))
                api.cancelRun(id!).catch((e: any) => setError(String(e.message ?? e)))
            }}>Cancel run</button>
          )}
          <div className="row spread mt"><span className="eyebrow">Audit log</span>
            <a className="small" href={`/api/runs/${id}/audit.json`}
              title="Every event with its payload, every checkpoint with its resolution, the frozen configuration">export as JSON ↗</a></div>
          <p className="desc small">The screen keeps recent entries; the export carries the complete record.</p>
          <div className="eventlog" ref={logRef}>
            {events.map((e, i) => (
              <div key={i} className={`ev-${e.kind}`}>
                {new Date(e.ts * 1000).toLocaleTimeString()} · {e.message}
              </div>
            ))}
          </div>
          </div>
        </section>
      </div>
    </div>
  )
}
