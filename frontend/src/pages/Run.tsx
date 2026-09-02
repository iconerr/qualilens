// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, statusLabel, type Checkpoint, type Run, type SheetImport } from '../api'

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
          <p className="desc">The report is ready — browse it interactively, export Word, or export
            the complete audit trail (every call, decision, and checkpoint) as JSON.</p>
          <div className="row">
            <Link to={`/runs/${id}/report`}><button className="primary">Open report</button></Link>
            <a href={`/api/runs/${id}/report.docx`}><button>Download .docx</button></a>
            <a href={`/api/runs/${id}/audit.json`}><button>Export audit log</button></a>
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
          <div className="row spread mt"><h3 style={{ margin: 0 }}>Audit log</h3>
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
      </div>
    </div>
  )
}

// ---------------- checkpoint review ----------------

type Edits = { name?: string; definition?: string; notes?: string }
type Action = { kind: 'keep' | 'merge' | 'delete'; merge_into?: string }

// What an uploaded spreadsheet left behind: shown above the list until the
// checkpoint is approved, and sent with the resolution so the audit trail
// names the worksheet the decisions came from.
type Imported = { imported_from: SheetImport['imported_from']; summary: Record<string, number>;
                  ignored: SheetImport['ignored'] }

const SUMMARY_WORDS: Record<string, string> = {
  renamed: 'renamed', redefined: 'redefined', merged: 'merged', deleted: 'deleted', added: 'added',
  edited: 'papers edited', fields_edited: 'fields edited', excluded: 'excluded', reincluded: 're-included',
  with_notes: 'with notes',
}

// A definition box that grows with its text: a single line for a short
// definition, as many as it needs for a long one, never a scrollbar.
function GrowingText({ value, onChange, placeholder, disabled }:
  { value: string; onChange: (v: string) => void; placeholder?: string; disabled?: boolean }) {
  const ref = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])
  return (
    <textarea ref={ref} value={value} disabled={disabled} placeholder={placeholder}
      className="small growing" rows={1} onChange={ev => onChange(ev.target.value)} />
  )
}

function summaryLine(s: Record<string, number>): string {
  const parts = Object.entries(SUMMARY_WORDS)
    .filter(([k]) => (s[k] ?? 0) > 0)
    .map(([k, w]) => `${s[k]} ${w}`)
  return parts.length ? parts.join(', ') : 'no changes'
}

/* The spreadsheet round trip: download the checkpoint as a workbook, edit it
   anywhere that opens one, upload it. The upload only STAGES decisions into
   this screen — the researcher reads them and presses Approve & continue as
   always, so there is one apply path and one audit trail. */
function SheetBar({ runId, cp, imported, onImport, onError, staged }:
  { runId: string; cp: Checkpoint; imported: Imported | null;
    onImport: (r: SheetImport) => void; onError: (m: string) => void; staged: boolean }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [showIgnored, setShowIgnored] = useState(false)
  const pick = async (f: File | undefined) => {
    if (!f) return
    if (staged && !confirm('Decisions loaded from the spreadsheet replace the edits currently '
      + 'staged on this screen. Continue?')) { if (fileRef.current) fileRef.current.value = ''; return }
    setBusy(true)
    try { onImport(await api.importSheet(runId, cp.id, f)) }
    catch (e: any) { onError(String(e.message ?? e)) }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = '' }
  }
  return (
    <div className="sheetbar">
      <div className="row" style={{ gap: 8 }}>
        <a href={api.sheetUrl(runId, cp.id)} title="Every item under review as an .xlsx workbook, with the rules on its About sheet">
          <button className="small">Download as spreadsheet</button></a>
        <button className="small" disabled={busy} onClick={() => fileRef.current?.click()}
          title="Upload the edited workbook; its decisions load here for you to check before approving">
          {busy ? 'Reading…' : 'Upload spreadsheet'}
        </button>
        <input ref={fileRef} type="file" accept=".xlsx" style={{ display: 'none' }}
          onChange={ev => pick(ev.target.files?.[0])} />
        {imported && (
          <span className="small muted">
            Loaded from <span className="mono">{imported.imported_from.filename}</span>: {summaryLine(imported.summary)}
            {imported.ignored.length > 0 && (
              <> · {imported.ignored.length} row{imported.ignored.length === 1 ? '' : 's'} ignored{' '}
                <a href="#" onClick={ev => { ev.preventDefault(); setShowIgnored(s => !s) }}>({showIgnored ? 'hide' : 'show'})</a></>
            )}
          </span>
        )}
      </div>
      {imported && showIgnored && imported.ignored.length > 0 && (
        <ul className="small muted" style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {imported.ignored.map((g, i) => (
            <li key={i}>Row {g.row}{g.id ? <> (<span className="mono">{g.id}</span>)</> : null}: {g.reason}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function CheckpointPanel({ runId, cp, onError, onResolved }:
  { runId: string; cp: Checkpoint; onError: (m: string) => void; onResolved: () => void }) {
  const kind = cp.payload?.kind
  return (
    <div className="card" style={{ borderColor: 'var(--amber)' }}>
      <h3 className="row" style={{ gap: 8 }}>
        <svg width="14" height="14" viewBox="0 0 14 14" aria-label="waiting for your review"
          style={{ flexShrink: 0 }}><rect x="2" y="1.5" width="3.5" height="11" rx="1" fill="var(--amber)" />
          <rect x="8.5" y="1.5" width="3.5" height="11" rx="1" fill="var(--amber)" /></svg>
        {cp.title}
      </h3>
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
  const [additions, setAdditions] = useState<{ name: string; definition: string; notes?: string }[]>(stored.additions ?? [])
  const [checked, setChecked] = useState<Set<string>>(new Set(stored.checked ?? []))
  const [imported, setImported] = useState<Imported | null>(stored.imported ?? null)
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
      { edits, actions, additions, checked: [...checked], imported }))
  }, [storeKey, edits, actions, additions, checked, imported])

  const act = (id: string): Action => actions[id] ?? { kind: 'keep' }
  const setEdit = (id: string, patch: Edits) =>
    setEdits(e => ({ ...e, [id]: { ...e[id], ...patch } }))
  const displayName = (it: any) => edits[it.id]?.name ?? it.name

  // A spreadsheet's decisions replace whatever is staged: the file is the
  // researcher's considered state, and mixing two sources would be a guess.
  const loadSheet = (r: SheetImport) => {
    const e: Record<string, Edits> = {}
    const a: Record<string, Action> = {}
    for (const d of r.decisions ?? []) {
      if (d.action === 'merge' && d.merge_into) a[d.id] = { kind: 'merge', merge_into: d.merge_into }
      else if (d.action === 'delete') a[d.id] = { kind: 'delete' }
      const patch: Edits = {}
      if (d.name !== undefined) patch.name = d.name
      if (d.definition !== undefined) patch.definition = d.definition
      if (d.notes) patch.notes = d.notes
      if (Object.keys(patch).length) e[d.id] = patch
    }
    setEdits(e); setActions(a)
    setAdditions((r.additions ?? []).map(x => ({ name: x.name, definition: x.definition ?? '', notes: x.notes })))
    setChecked(new Set()); setMergeTarget('')
    setImported({ imported_from: r.imported_from, summary: r.summary, ignored: r.ignored })
  }
  const anythingStaged = Object.keys(edits).length + Object.keys(actions).length + additions.length > 0

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
      const notes = e.notes?.trim() ? { notes: e.notes.trim() } : {}
      if (a.kind === 'merge') list.push({ id: it.id, action: 'merge', merge_into: a.merge_into, ...notes })
      else if (a.kind === 'delete') list.push({ id: it.id, action: 'delete', ...notes })
      else {
        // only submit REAL edits: a typed-then-reverted value is not a rename,
        // and must not mark the code researcher-edited
        const nameChanged = e.name !== undefined && e.name.trim() !== '' && e.name !== it.name
        const defChanged = e.definition !== undefined && e.definition !== (it.definition ?? '')
        if (nameChanged || defChanged)
          list.push({ id: it.id, action: 'rename',
                      name: nameChanged ? e.name : undefined,
                      definition: defChanged ? e.definition : undefined, ...notes })
        else if (e.notes?.trim())
          list.push({ id: it.id, action: 'keep', ...notes })   // a considered keep, with its reason
      }
    }
    submit({
      decisions: list,
      additions: additions.filter(a => a.name.trim()),
      stage: cp.payload.stage,
      ...(imported ? { imported_from: imported.imported_from } : {}),
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

      <SheetBar runId={runId} cp={cp} imported={imported} onImport={loadSheet} onError={onError}
        staged={anythingStaged} />

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
                    <GrowingText value={e.definition ?? it.definition ?? ''} disabled={inactive}
                      onChange={v => setEdit(it.id, { definition: v })}
                      placeholder="definition" />
                    {e.notes && (
                      <p className="small muted" style={{ margin: '4px 0 0' }}>
                        <b>Note:</b> {e.notes}
                      </p>
                    )}
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
                {it.candidate_name && it.candidate_name !== it.name && (
                  <p className="small muted" style={{ margin: '4px 0 0 26px' }}>
                    Named in Phase 5 from the candidate “{it.candidate_name}” — the name and
                    definition above are what the report will carry unless you edit them.
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
                  <GrowingText value={a.definition} placeholder="definition"
                    onChange={v => setAdditions(x => x.map((y, j) => j === i ? { ...y, definition: v } : y))} />
                  {a.notes && <p className="small muted" style={{ margin: '4px 0 0' }}><b>Note:</b> {a.notes}</p>}
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
  const [notes, setNotes] = useState<Record<string, string>>(stored.notes ?? {})
  const [imported, setImported] = useState<Imported | null>(stored.imported ?? null)
  const [open, setOpen] = useState<string>(rows.length === 1 ? rows[0].source_id : '')
  const { busy, submit } = useSubmit(runId, cp, onError, () => {
    sessionStorage.removeItem(storeKey)
    onResolved()
  })

  useEffect(() => {
    sessionStorage.setItem(storeKey, JSON.stringify({ edits, excluded, notes, imported }))
  }, [storeKey, edits, excluded, notes, imported])

  const loadSheet = (r: SheetImport) => {
    const e: Record<string, Record<string, string>> = {}
    const x: Record<string, boolean> = {}
    const n: Record<string, string> = {}
    for (const row of r.rows ?? []) {
      const { source_id, exclude, notes: note, ...fields } = row
      for (const [k, v] of Object.entries(fields)) if (typeof v === 'string') (e[source_id] ??= {})[k] = v
      if (typeof exclude === 'boolean') x[source_id] = exclude
      if (note) n[source_id] = note
    }
    setEdits(e); setExcluded(x); setNotes(n)
    setImported({ imported_from: r.imported_from, summary: r.summary, ignored: r.ignored })
  }
  const anythingStaged = Object.keys(edits).length + Object.keys(excluded).length > 0

  const setEdit = (sid: string, key: string, value: string) =>
    setEdits(e => ({ ...e, [sid]: { ...e[sid], [key]: value } }))
  const original = (row: any, key: string): string =>
    key === 'label' ? (row.label ?? '') :
    key === 'citation' ? (row.citation ?? '') :
    key === 'cited_work' ? (row.cited_work ?? '') : (row.fields?.[key] ?? '')
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
  const nEdited = rows.filter(r => fieldKeys.concat(['label', 'citation', 'cited_work'])
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
      for (const k of ['label', 'citation', 'cited_work', ...fieldKeys])
        if (isEdit(r, k)) patch[k] = current(r, k)
      if (isExcluded(r) !== !!r.excluded) patch.exclude = isExcluded(r)
      if (notes[r.source_id]?.trim()) patch.notes = notes[r.source_id].trim()
      if (Object.keys(patch).length) out.push({ source_id: r.source_id, ...patch })
    }
    submit({ rows: out, stage: cp.payload.stage,
             ...(imported ? { imported_from: imported.imported_from } : {}) })
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
      <SheetBar runId={runId} cp={cp} imported={imported} onImport={loadSheet} onError={onError}
        staged={anythingStaged} />
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
                {notes[r.source_id] && (
                  <p className="small muted" style={{ margin: '4px 0 0' }}><b>Note:</b> {notes[r.source_id]}</p>
                )}
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
                <label className="field">
                  <span className="lbl">Findings the paper attributes to other work
                    <span className="muted"> · not used in the synthesis; here so a cited result is not mistaken for this paper's own</span></span>
                  <textarea value={current(r, 'cited_work')} disabled={off}
                    onChange={ev => setEdit(r.source_id, 'cited_work', ev.target.value)} />
                </label>
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
          unpromoted candidates are discarded. A promoted code is charted across every source before
          the matrix is built, so its column means what the other columns mean.</p>
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
        <p className="desc small">Tick any assignment that is wrong; ticked excerpts are removed.
          {typeof cp.payload.low_confidence_total === 'number' && cp.payload.low_confidence_total > lowConf.length && (
            <> Showing the {lowConf.length} weakest of {cp.payload.low_confidence_total} below the threshold;
              the rest are accepted on approval — check them in the coded-source reader.</>)}
          {' '}An assignment marked “no confidence given” came back without a rating; it is listed first.</p>
        {lowConf.map(e => (
          <div key={e.excerpt_id} className="code-item" style={deletions.has(e.excerpt_id) ? { opacity: .5 } : {}}>
            <label className="row" style={{ cursor: 'pointer' }}>
              <input type="checkbox" checked={deletions.has(e.excerpt_id)} onChange={() => toggle(e.excerpt_id)} />
              <span><b>{e.code}</b> <span className="count-pill">{typeof e.confidence === 'number' ? `conf ${Math.round(e.confidence * 100)}%` : 'no confidence given'}</span>
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
