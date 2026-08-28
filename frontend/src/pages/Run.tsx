// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, statusLabel, type Checkpoint, type Run } from '../api'

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
    if (!confirm(`Revisit “${label}”?\n\n`
      + 'This creates a NEW run — not from scratch: it carries everything this '
      + 'run had at that review (the coding, the evidence, and your earlier '
      + 'decisions) and reopens the review for you to decide differently. '
      + 'This run and its report stay exactly as they are.\n\n'
      + 'Stages after the review will run again on the new run, and bill again.')) return
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
      <h1>{run.project_name}</h1>
      <p className="sub">
        <Link to={`/projects/${run.project_id}`}>← project</Link>
        {' · '}run of {new Date(run.created_at * 1000).toLocaleString()}
        {' · '}<span className={`badge ${run.status}`}>{statusLabel(run.status)}</span>
      </p>
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
        <div className="card" style={{ borderColor: 'var(--green)' }}>
          <h3>Analysis complete</h3>
          <p className="desc">The report is ready — browse it interactively or export Word.</p>
          <div className="row">
            <Link to={`/runs/${id}/report`}><button className="primary">Open report</button></Link>
            <a href={`/api/runs/${id}/report.docx`}><button>Download .docx</button></a>
          </div>
        </div>
      )}

      {run.pending_checkpoint && run.status === 'awaiting_review'
        && run.pending_checkpoint.id !== resolvedCp && (
        <CheckpointPanel runId={id!} cp={run.pending_checkpoint} onError={setError}
          onResolved={() => { setResolvedCp(run.pending_checkpoint!.id); setError('') }} />
      )}

      <div className="grid2">
        <div className="card">
          <h3>Pipeline</h3>
          <div className="stagelist">
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
        </div>
        <div className="card">
          <h3>Progress</h3>
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
            <button className="small danger" onClick={() => {
              if (confirm('Cancel this run? Cancellation is final for this run — it '
                + 'cannot be resumed. Reviews it has already passed stay available: '
                + '“↩ Revisit this review…” starts a new run carrying the work up '
                + 'to that point.'))
                api.cancelRun(id!).catch((e: any) => setError(String(e.message ?? e)))
            }}>Cancel run</button>
          )}
          <h3 className="mt">Audit log</h3>
          <div className="eventlog" ref={logRef}>
            {events.map((e, i) => (
              <div key={i} className={`ev-${e.kind}`}>
                {new Date(e.ts * 1000).toLocaleTimeString()} · {e.message}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------- checkpoint review ----------------

type Edits = { name?: string; definition?: string }
type Action = { kind: 'keep' | 'merge' | 'delete'; merge_into?: string }

function CheckpointPanel({ runId, cp, onError, onResolved }:
  { runId: string; cp: Checkpoint; onError: (m: string) => void; onResolved: () => void }) {
  const kind = cp.payload?.kind
  return (
    <div className="card" style={{ borderColor: 'var(--amber)' }}>
      <h3>⏸ {cp.title}</h3>
      <p className="desc">{cp.instructions}</p>
      {kind === 'core_review'
        ? <CoreReview key={cp.id} runId={runId} cp={cp} onError={onError} onResolved={onResolved} />
        : kind === 'framework_review'
          ? <FrameworkReview key={cp.id} runId={runId} cp={cp} onError={onError} onResolved={onResolved} />
          : kind === 'extraction_review'
            ? <ExtractionReview key={cp.id} runId={runId} cp={cp} onError={onError} onResolved={onResolved} />
            : <CodeReview key={cp.id} runId={runId} cp={cp} onError={onError} onResolved={onResolved} />}
    </div>
  )
}

type PanelProps = { runId: string; cp: Checkpoint; onError: (m: string) => void; onResolved: () => void }

function useSubmit(runId: string, cp: Checkpoint, onError: (m: string) => void, onResolved: () => void) {
  const [busy, setBusy] = useState(false)
  const submit = async (resolution: Record<string, unknown>) => {
    setBusy(true)
    try {
      await api.resolveCheckpoint(runId, cp.id, resolution)
      onResolved()
    } catch (e: any) { onError(String(e.message ?? e)) }
    finally { setBusy(false) }
  }
  return { busy, submit }
}

function CodeReview({ runId, cp, onError, onResolved }: PanelProps) {
  const items: any[] = cp.payload.items ?? []
  // In-progress decisions survive reloads and accidental navigation (e.g.
  // opening a coded document): persisted to sessionStorage per checkpoint.
  const storeKey = `qualilens-review-${cp.id}`
  const stored = useMemo(() => {
    try { return JSON.parse(sessionStorage.getItem(storeKey) ?? '{}') } catch { return {} }
  }, [storeKey])
  // edits (rename/redefine) and actions (merge/delete) are independent, so
  // undoing a merge never discards a rename made before it
  const [edits, setEdits] = useState<Record<string, Edits>>(stored.edits ?? {})
  const [actions, setActions] = useState<Record<string, Action>>(stored.actions ?? {})
  const [additions, setAdditions] = useState<{ name: string; definition: string }[]>(stored.additions ?? [])
  const [checked, setChecked] = useState<Set<string>>(new Set(stored.checked ?? []))
  const [focusId, setFocusId] = useState('')
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<'count-desc' | 'count-asc' | 'name' | 'orig'>('count-desc')
  const [mergeTarget, setMergeTarget] = useState('')
  const { busy, submit } = useSubmit(runId, cp, onError, () => {
    sessionStorage.removeItem(storeKey)
    onResolved()
  })

  useEffect(() => {
    sessionStorage.setItem(storeKey, JSON.stringify(
      { edits, actions, additions, checked: [...checked] }))
  }, [storeKey, edits, actions, additions, checked])

  const act = (id: string): Action => actions[id] ?? { kind: 'keep' }
  const setEdit = (id: string, patch: Edits) =>
    setEdits(e => ({ ...e, [id]: { ...e[id], ...patch } }))
  const displayName = (it: any) => edits[it.id]?.name ?? it.name

  // Marking codes deleted also drops them from the selection, clears them as
  // merge target, and un-stages any merges pointing INTO them — a delete must
  // never silently expand into deleting other codes' merged evidence.
  const markDelete = (ids: string[]) => {
    setActions(x => {
      const n = { ...x }
      ids.forEach(id => { n[id] = { kind: 'delete' } })
      for (const [k, v] of Object.entries(n))
        if (v.kind === 'merge' && v.merge_into && ids.includes(v.merge_into)) delete n[k]
      return n
    })
    setChecked(s => { const c = new Set(s); ids.forEach(id => c.delete(id)); return c })
    setMergeTarget(t => ids.includes(t) ? '' : t)
  }

  const activeItems = items.filter(i => act(i.id).kind === 'keep')
  const q = search.trim().toLowerCase()
  const visible = items
    .filter(it => !q || displayName(it).toLowerCase().includes(q)
      || (edits[it.id]?.definition ?? it.definition ?? '').toLowerCase().includes(q))
    .sort((a, b) => {
      if (sortKey === 'count-desc') return b.excerpt_count - a.excerpt_count
      if (sortKey === 'count-asc') return a.excerpt_count - b.excerpt_count
      if (sortKey === 'name') return displayName(a).localeCompare(displayName(b))
      return 0
    })

  const nMerged = items.filter(i => act(i.id).kind === 'merge').length
  const nDeleted = items.filter(i => act(i.id).kind === 'delete').length

  const toggleCheck = (id: string) => setChecked(s => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n
  })
  const bulkDelete = () => {
    markDelete([...checked].filter(id => act(id).kind === 'keep'))
    setChecked(new Set())
  }
  const bulkMerge = () => {
    // the target must still be a kept code (it may have been deleted since
    // it was picked, leaving the dropdown blank but the state stale)
    if (!mergeTarget || act(mergeTarget).kind !== 'keep') { setMergeTarget(''); return }
    setActions(x => {
      const n = { ...x }
      checked.forEach(id => {
        if (id !== mergeTarget && (x[id]?.kind ?? 'keep') === 'keep')
          n[id] = { kind: 'merge', merge_into: mergeTarget }
      })
      return n
    })
    setChecked(new Set()); setMergeTarget('')
  }

  const done = () => {
    const list: any[] = []
    for (const it of items) {
      const a = act(it.id)
      const e = edits[it.id] ?? {}
      if (a.kind === 'merge') list.push({ id: it.id, action: 'merge', merge_into: a.merge_into })
      else if (a.kind === 'delete') list.push({ id: it.id, action: 'delete' })
      else {
        // only submit REAL edits: a typed-then-reverted value is not a rename,
        // and must not mark the code researcher-edited
        const nameChanged = e.name !== undefined && e.name.trim() !== '' && e.name !== it.name
        const defChanged = e.definition !== undefined && e.definition !== (it.definition ?? '')
        if (nameChanged || defChanged)
          list.push({ id: it.id, action: 'rename',
                      name: nameChanged ? e.name : undefined,
                      definition: defChanged ? e.definition : undefined })
      }
    }
    submit({
      decisions: list,
      additions: additions.filter(a => a.name.trim()),
      stage: cp.payload.stage,
    })
  }

  const focused = items.find(i => i.id === focusId)

  return (
    <>
      <div className="review-toolbar">
        <input type="text" placeholder={`Search ${items.length} codes…`}
          value={search} onChange={e => setSearch(e.target.value)} />
        <select value={sortKey} onChange={e => setSortKey(e.target.value as any)}>
          <option value="count-desc">Most excerpts first</option>
          <option value="count-asc">Fewest excerpts first (merge candidates)</option>
          <option value="name">Alphabetical</option>
          <option value="orig">Original order</option>
        </select>
        <span className="small muted">
          {items.length} codes · {visible.length} shown
          {nMerged > 0 && <> · {nMerged} to merge</>}
          {nDeleted > 0 && <> · {nDeleted} to delete</>}
        </span>
        <span style={{ marginLeft: 'auto' }}>
          <button className="small" onClick={() => setAdditions(x => [...x, { name: '', definition: '' }])}>
            + Add a code
          </button>
        </span>
      </div>

      {checked.size > 0 && (
        <div className="bulkbar">
          <b>{checked.size} selected</b>
          <select value={mergeTarget} onChange={e => setMergeTarget(e.target.value)}>
            <option value="">merge all into…</option>
            {activeItems.map(o => <option key={o.id} value={o.id}>{displayName(o)}</option>)}
          </select>
          <button className="small primary" onClick={bulkMerge} disabled={!mergeTarget}>Merge</button>
          <button className="small danger" onClick={bulkDelete}>Delete selected</button>
          <button className="small" onClick={() => setChecked(new Set())}>Clear selection</button>
        </div>
      )}

      <div className="review-layout">
        <div>
          {visible.map(it => {
            const a = act(it.id)
            const e = edits[it.id] ?? {}
            const inactive = a.kind !== 'keep'
            const cls = a.kind === 'merge' ? 'merged' : a.kind === 'delete' ? 'deleted' : ''
            return (
              <div key={it.id}
                className={`code-item ${cls} ${focusId === it.id ? 'selected' : ''}`}>
                <div className="row-main" onClick={() => setFocusId(it.id)}>
                  <input type="checkbox" checked={checked.has(it.id)} disabled={inactive}
                    onClick={ev => ev.stopPropagation()}
                    onChange={() => toggleCheck(it.id)} style={{ marginTop: 8 }} />
                  <div style={{ flex: 1, minWidth: 220 }} onClick={ev => ev.stopPropagation()}>
                    <input type="text" value={e.name ?? it.name}
                      disabled={inactive}
                      onChange={ev => setEdit(it.id, { name: ev.target.value })}
                      style={{ fontWeight: 600, marginBottom: 4 }} />
                    <input type="text" value={e.definition ?? it.definition}
                      disabled={inactive}
                      onChange={ev => setEdit(it.id, { definition: ev.target.value })}
                      placeholder="definition" className="small" />
                  </div>
                  <div className="row" style={{ alignItems: 'flex-start', flexShrink: 0 }}
                    onClick={ev => ev.stopPropagation()}>
                    <button className={`small ${focusId === it.id ? 'primary' : ''}`}
                      title="Show all evidence for this code"
                      onClick={() => setFocusId(it.id)}>
                      {it.excerpt_count} excerpt{it.excerpt_count === 1 ? '' : 's'}
                    </button>
                    {!inactive ? (
                      <button className="small danger"
                        onClick={() => markDelete([it.id])}>Delete</button>
                    ) : (
                      <button className="small" onClick={() =>
                        setActions(x => { const { [it.id]: _, ...rest } = x; return rest })}>
                        Undo {a.kind}
                      </button>
                    )}
                  </div>
                </div>
                {a.kind === 'merge' && (
                  <p className="small muted" style={{ margin: '4px 0 0 26px' }}>
                    → merging into “{displayName(items.find(o => o.id === a.merge_into) ?? { name: '?' })}”
                  </p>
                )}
                {it.review && (
                  <p className="small" style={{ margin: '6px 0 0 26px' }}>
                    <b>Model’s own critique:</b> coherence {it.review.coherence},
                    distinctness {it.review.distinctness} — recommends <b>{it.review.recommendation}</b>. {it.review.notes}
                  </p>
                )}
                {(it.papers ?? []).length > 0 && (
                  <p className="small muted" style={{ margin: '4px 0 0 26px' }}>
                    Supported by {it.papers.length} paper{it.papers.length === 1 ? '' : 's'}: {it.papers.join(' · ')}
                  </p>
                )}
              </div>
            )
          })}
          {visible.length === 0 && <p className="desc">No codes match “{search}”.</p>}

          {additions.map((a, i) => (
            <div key={`add-${i}`} className="code-item" style={{ borderStyle: 'dashed' }}>
              <div className="row spread">
                <div style={{ flex: 1, minWidth: 220 }}>
                  <input type="text" value={a.name} placeholder="new code name"
                    onChange={ev => setAdditions(x => x.map((y, j) => j === i ? { ...y, name: ev.target.value } : y))}
                    style={{ fontWeight: 600, marginBottom: 4 }} />
                  <input type="text" value={a.definition} placeholder="definition" className="small"
                    onChange={ev => setAdditions(x => x.map((y, j) => j === i ? { ...y, definition: ev.target.value } : y))} />
                </div>
                <button className="small danger"
                  onClick={() => setAdditions(x => x.filter((_, j) => j !== i))}>Remove</button>
              </div>
            </div>
          ))}
        </div>

        <EvidencePanel runId={runId} code={focused}
          name={focused ? displayName(focused) : ''} />
      </div>

      <div className="right mt">
        <button className="primary" onClick={done} disabled={busy}>
          {busy ? 'Applying…' : 'Approve & continue'}
        </button>
      </div>
    </>
  )
}

function EvidencePanel({ runId, code, name }: { runId: string; code: any; name: string }) {
  const [excerpts, setExcerpts] = useState<any[] | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!code) return
    setExcerpts(null); setErr('')
    let alive = true
    api.codeExcerpts(runId, code.id)
      .then(x => { if (alive) setExcerpts(x) })
      .catch(e => { if (alive) setErr(String(e.message ?? e)) })
    return () => { alive = false }
  }, [runId, code?.id])

  if (!code) return (
    <div className="evidence-panel">
      <p className="desc">Click a code to see all of its evidence here —
        every excerpt, its source, and a link to the coded document.</p>
    </div>
  )
  return (
    <div className="evidence-panel">
      <h4>{name}</h4>
      <p className="desc small">{code.definition}</p>
      {err && <div className="error-box">{err}</div>}
      {!excerpts && !err && <p className="desc">Loading evidence…</p>}
      {excerpts && excerpts.length === 0 && <p className="desc">No excerpts.</p>}
      {excerpts?.map(e => (
        <div key={e.id} className="quote">
          “{e.quote}”
          <div className="src">
            {e.source}
            {typeof e.confidence === 'number' && <> · conf {Math.round(e.confidence * 100)}%</>}
            {e.via && <> · via “{e.via}”</>}
            {e.memo && <> · {e.memo}</>}
            {' · '}
            <Link to={`/runs/${runId}/sources/${e.source_id}?ex=${e.id}`}
              target="_blank" rel="noopener">open in document ↗</Link>
          </div>
        </div>
      ))}
    </div>
  )
}

function ExtractionReview({ runId, cp, onError, onResolved }: PanelProps) {
  const rows: any[] = cp.payload.rows ?? []
  const fieldKeys: string[] = cp.payload.fields ?? []
  const fieldLabels: Record<string, string> = cp.payload.field_labels ?? {}
  // In-progress edits survive reloads and side trips into coded documents,
  // exactly like the code review: persisted to sessionStorage per checkpoint.
  const storeKey = `qualilens-review-${cp.id}`
  const stored = useMemo(() => {
    try { return JSON.parse(sessionStorage.getItem(storeKey) ?? '{}') } catch { return {} }
  }, [storeKey])
  const [edits, setEdits] = useState<Record<string, Record<string, string>>>(stored.edits ?? {})
  const [excluded, setExcluded] = useState<Record<string, boolean>>(stored.excluded ?? {})
  const [open, setOpen] = useState<string>(rows.length === 1 ? rows[0].source_id : '')
  const { busy, submit } = useSubmit(runId, cp, onError, () => {
    sessionStorage.removeItem(storeKey)
    onResolved()
  })

  useEffect(() => {
    sessionStorage.setItem(storeKey, JSON.stringify({ edits, excluded }))
  }, [storeKey, edits, excluded])

  const setEdit = (sid: string, key: string, value: string) =>
    setEdits(e => ({ ...e, [sid]: { ...e[sid], [key]: value } }))
  const original = (row: any, key: string): string =>
    key === 'label' ? (row.label ?? '') :
    key === 'citation' ? (row.citation ?? '') : (row.fields?.[key] ?? '')
  const current = (row: any, key: string): string =>
    edits[row.source_id]?.[key] ?? original(row, key)
  const isExcluded = (row: any): boolean =>
    excluded[row.source_id] ?? !!row.excluded

  // a blanked label is not an edit — the backend refuses blank labels and
  // keeps the old one, so counting it would claim a change that won't apply
  const isEdit = (r: any, k: string) => {
    const v = current(r, k)
    if (k === 'label' && !v.trim()) return false
    return v !== original(r, k)
  }
  const nEdited = rows.filter(r => fieldKeys.concat(['label', 'citation'])
    .some(k => isEdit(r, k))).length
  const nExcluded = rows.filter(isExcluded).length

  const done = () => {
    if (rows.length && rows.every(isExcluded)) {
      onError('Every paper is excluded — re-include at least one paper before '
        + 'approving, or cancel the run.')
      return
    }
    const out: any[] = []
    for (const r of rows) {
      const patch: Record<string, unknown> = {}
      // only submit REAL edits: a typed-then-reverted value is not an edit,
      // and must not mark the row researcher-edited
      for (const k of ['label', 'citation', ...fieldKeys])
        if (isEdit(r, k)) patch[k] = current(r, k)
      if (isExcluded(r) !== !!r.excluded) patch.exclude = isExcluded(r)
      if (Object.keys(patch).length) out.push({ source_id: r.source_id, ...patch })
    }
    submit({ rows: out, stage: cp.payload.stage })
  }

  return (
    <>
      <div className="review-toolbar">
        <span className="small muted">
          {rows.length} paper{rows.length === 1 ? '' : 's'}
          {nEdited > 0 && <> · {nEdited} edited</>}
          {nExcluded > 0 && <> · {nExcluded} excluded from synthesis</>}
        </span>
      </div>
      {rows.map(r => {
        const off = isExcluded(r)
        const isOpen = open === r.source_id
        const quotes: Record<string, number> = r.quote_counts ?? {}
        const totalQuotes = fieldKeys.reduce((n, k) => n + (quotes[k] ?? 0), 0)
        return (
          <div key={r.source_id} className="code-item" style={off ? { opacity: .55 } : {}}>
            <div className="row spread" style={{ cursor: 'pointer' }}
              onClick={() => setOpen(isOpen ? '' : r.source_id)}>
              <div>
                <b>{current(r, 'label') || r.filename}</b>
                <span className="muted small"> · {r.filename}</span>
                {' '}<span className="count-pill">{totalQuotes} quote{totalQuotes === 1 ? '' : 's'}</span>
                {(r.unlocated_quotes ?? 0) > 0 && (
                  <span className="muted small"> · {r.unlocated_quotes} not located
                    — those cannot ground the synthesis</span>
                )}
                {off && <span className="muted small"> · excluded from synthesis</span>}
              </div>
              <div className="row" onClick={ev => ev.stopPropagation()}>
                <Link to={`/runs/${runId}/sources/${r.source_id}`} target="_blank" rel="noopener">
                  <button className="small" title="Open the paper with every extraction quote highlighted">
                    open coded paper ↗</button>
                </Link>
                <button className={`small ${off ? '' : 'danger'}`}
                  onClick={() => setExcluded(x => ({ ...x, [r.source_id]: !off }))}>
                  {off ? 'Re-include' : 'Exclude'}
                </button>
                <button className="small" onClick={() => setOpen(isOpen ? '' : r.source_id)}>
                  {isOpen ? 'Collapse' : 'Review'}
                </button>
              </div>
            </div>
            {isOpen && (
              <div className="mt" onClick={ev => ev.stopPropagation()}>
                <label className="field"><span className="lbl">Label (how the narrative cites this paper)</span>
                  <input type="text" value={current(r, 'label')} disabled={off}
                    onChange={ev => setEdit(r.source_id, 'label', ev.target.value)} /></label>
                <label className="field"><span className="lbl">Citation (as read off the paper)</span>
                  <input type="text" value={current(r, 'citation')} disabled={off}
                    onChange={ev => setEdit(r.source_id, 'citation', ev.target.value)} /></label>
                {fieldKeys.map(k => (
                  <label key={k} className="field">
                    <span className="lbl">
                      {fieldLabels[k] ?? k}
                      <span className="muted"> · {quotes[k] ?? 0} quote{(quotes[k] ?? 0) === 1 ? '' : 's'}</span>
                    </span>
                    <textarea value={current(r, k)} disabled={off}
                      onChange={ev => setEdit(r.source_id, k, ev.target.value)} />
                  </label>
                ))}
              </div>
            )}
          </div>
        )
      })}
      <div className="right mt">
        <button className="primary" onClick={done} disabled={busy}>
          {busy ? 'Applying…' : 'Approve & continue'}
        </button>
      </div>
    </>
  )
}

function CoreReview({ runId, cp, onError, onResolved }: PanelProps) {
  const core = (cp.payload.items ?? [])[0]
  const [name, setName] = useState<string>(core?.name ?? '')
  const [definition, setDefinition] = useState<string>(core?.definition ?? '')
  const [storyline, setStoryline] = useState<string>(core?.storyline ?? '')
  const { busy, submit } = useSubmit(runId, cp, onError, onResolved)
  if (!core) return <p className="desc">No core category was produced.</p>
  return (
    <>
      <label className="field"><span className="lbl">Core category</span>
        <input type="text" value={name} onChange={e => setName(e.target.value)} /></label>
      <label className="field"><span className="lbl">Definition</span>
        <textarea value={definition} onChange={e => setDefinition(e.target.value)} /></label>
      <label className="field"><span className="lbl">Storyline</span>
        <textarea value={storyline} style={{ minHeight: 140 }} onChange={e => setStoryline(e.target.value)} /></label>
      {(core.relationships ?? []).length > 0 && (
        <p className="small muted">Relationships proposed: {core.relationships.map((r: any) =>
          `${r.relation} (${r.explanation})`).join(' · ')}</p>
      )}
      <div className="right">
        <button className="primary" disabled={busy}
          onClick={() => submit({ decisions: [{ id: core.id, name, definition, storyline }] })}>
          {busy ? 'Applying…' : 'Approve & continue'}
        </button>
      </div>
    </>
  )
}

function FrameworkReview({ runId, cp, onError, onResolved }: PanelProps) {
  const lowConf: any[] = cp.payload.low_confidence ?? []
  const emergent: any[] = cp.payload.items ?? []
  const [deletions, setDeletions] = useState<Set<string>>(new Set())
  const [decisions, setDecisions] = useState<Record<string, { id: string; action: string }>>({})
  const { busy, submit } = useSubmit(runId, cp, onError, onResolved)

  const toggle = (id: string) => setDeletions(s => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n
  })

  const done = () => submit({
    excerpt_deletions: Array.from(deletions),
    decisions: emergent.map(e => decisions[e.id] ?? { id: e.id, action: 'delete' }),
  })

  return (
    <>
      {emergent.length > 0 && <>
        <h3>Emergent code candidates</h3>
        <p className="desc small">Passages that fit no framework code. Promote the ones worth keeping —
          unpromoted candidates are discarded.</p>
        {emergent.map(e => {
          const d = decisions[e.id]
          return (
            <div key={e.id} className="code-item">
              <div className="row spread">
                <div><b>{e.name}</b> <span className="muted small">{e.definition}</span>
                  {' '}<span className="count-pill">{e.excerpt_count}</span></div>
                <div className="row">
                  <button className={`small ${d?.action === 'keep' ? 'primary' : ''}`}
                    onClick={() => setDecisions(x => ({ ...x, [e.id]: { id: e.id, action: 'keep' } }))}>
                    Promote to framework
                  </button>
                  <button className={`small ${!d || d.action === 'delete' ? 'danger' : ''}`}
                    onClick={() => setDecisions(x => ({ ...x, [e.id]: { id: e.id, action: 'delete' } }))}>
                    Discard
                  </button>
                </div>
              </div>
              {(e.sample_excerpts ?? []).map((x: any, i: number) => (
                <div key={i} className="quote">“{x.quote}”</div>
              ))}
            </div>
          )
        })}
      </>}
      {lowConf.length > 0 && <>
        <h3>Low-confidence assignments</h3>
        <p className="desc small">Tick any assignment that is wrong; ticked excerpts are removed.</p>
        {lowConf.map(e => (
          <div key={e.excerpt_id} className="code-item" style={deletions.has(e.excerpt_id) ? { opacity: .5 } : {}}>
            <label className="row" style={{ cursor: 'pointer' }}>
              <input type="checkbox" checked={deletions.has(e.excerpt_id)} onChange={() => toggle(e.excerpt_id)} />
              <span><b>{e.code}</b> <span className="count-pill">conf {Math.round((e.confidence ?? 0) * 100)}%</span>
                <span className="muted small"> · {e.source}</span></span>
            </label>
            <div className="quote">“{e.quote}” {e.memo && <span className="src">— {e.memo}</span>}</div>
          </div>
        ))}
      </>}
      {emergent.length === 0 && lowConf.length === 0 &&
        <p className="desc">Nothing was flagged — all assignments were confident and within the framework.</p>}
      <div className="right mt">
        <button className="primary" onClick={done} disabled={busy}>
          {busy ? 'Applying…' : 'Approve & continue'}
        </button>
      </div>
    </>
  )
}
