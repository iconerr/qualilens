// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

/* The checkpoint panels: where the pipeline stops and the analysis becomes
   the researcher's. Redesigned 2026-11-15 from what a reviewer needs (mock,
   reasoning and measurements: devnotes/design/2026-11-15-app/review/):
   - what you judge sits beside what it rests on (a code beside its quote, a
     summary beside its quotes, a weak assignment beside its code's definition);
   - every decision is written in words where it was made, and tallied beside
     the list with the one way out, Approve, which names the count;
   - a note can go on anything, and travels into the audit trail;
   - nothing applies until Approve; staged decisions survive leaving the page. */

import { Fragment, useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, saveFile, type Checkpoint, type Run, type SheetImport } from '../api'
import { ask } from '../ask'
import { GTModel } from '../viz'

type PanelProps = { runId: string; cp: Checkpoint; onError: (m: string) => void; onResolved: () => void }

const plural = (n: number, one: string, many = one + 's') =>
  `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`

// what approving starts, said where the decision is made
const NEXT: Record<string, string> = {
  review_open_codes: 'After you approve, axial coding groups the codes you keep into categories.',
  review_categories: 'After you approve, selective coding looks for the core category among the categories you keep.',
  review_core: 'After you approve, the theory and the report are written.',
  review_codes: 'After you approve, the codes you keep are grouped into candidate themes. Those are reviewed against the data and named.',
  review_themes: 'After you approve, the report is written from the themes you keep, as you named them.',
  review_codebook: 'After you approve, the codebook is applied to every source and the results are counted.',
  review_charting: 'After you approve, the promoted codes are charted across every source. Then the matrix and the report are built.',
  review_extraction: 'After you approve, the synthesis is built on this table. You review its concepts next.',
  review_synthesis: 'After you approve, the concept matrix and the report are built from the concepts you keep.',
}

const PauseMark = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" aria-label="waiting for your review" style={{ flexShrink: 0 }}>
    <rect x="2" y="1.5" width="3.5" height="11" rx="1" fill="var(--amber)" />
    <rect x="8.5" y="1.5" width="3.5" height="11" rx="1" fill="var(--amber)" />
  </svg>
)

export function CheckpointPanel({ run, runId, cp, onError, onResolved }: PanelProps & { run: Run }) {
  const kind = cp.payload?.kind
  const nextStage = run.stages[run.stage_index + 1]
  const next = NEXT[cp.stage] ?? (nextStage ? `After you approve, the run continues with ${nextStage.label.toLowerCase()}.` : '')
  const props = { runId, cp, onError, onResolved }
  return (
    <section className="card checkpoint-card rv-card" aria-label={cp.title}>
      <div className="rv-intro">
        <h2><PauseMark />{cp.title}</h2>
        <p>{cp.instructions}</p>
        {next && <p className="rv-next">{next}</p>}
      </div>
      {kind === 'core_review' ? <CoreReview key={cp.id} {...props} />
        : kind === 'framework_review' ? <FrameworkReview key={cp.id} {...props} />
        : kind === 'extraction_review' ? <ExtractionReview key={cp.id} {...props} />
        : <CodeReview key={cp.id} {...props} />}
    </section>
  )
}

// ---------------------------------------------------------------- shared pieces

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

// staged decisions survive reloads and side trips into coded documents: held
// in sessionStorage per checkpoint, cleared on approval
function useStored(cp: Checkpoint) {
  const key = `qualilens-review-${cp.id}`
  const stored = useMemo(() => {
    try { return JSON.parse(sessionStorage.getItem(key) ?? '{}') } catch { return {} }
  }, [key])
  const save = (v: unknown) => { try { sessionStorage.setItem(key, JSON.stringify(v)) } catch { /* private window */ } }
  const clear = () => { try { sessionStorage.removeItem(key) } catch { /* fine */ } }
  return { stored, save, clear }
}

// a text box that grows with its text: never a scrollbar
function GrowingText({ value, onChange, placeholder, className = '', autoFocus, onKeyDown, label }:
  { value: string; onChange: (v: string) => void; placeholder?: string; className?: string;
    autoFocus?: boolean; onKeyDown?: (e: KeyboardEvent<HTMLTextAreaElement>) => void; label?: string }) {
  const ref = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight + 2}px`
  }, [value])
  return (
    <textarea ref={ref} value={value} placeholder={placeholder} rows={1} aria-label={label}
      className={`growing ${className}`} autoFocus={autoFocus} onKeyDown={onKeyDown}
      onChange={ev => onChange(ev.target.value)} />
  )
}

// a verbatim passage: in the serif, the reader's gold as its rule
function Quote({ text, cite, children }: { text: string; cite?: ReactNode; children?: ReactNode }) {
  return (
    <figure className="rv-quote">
      <blockquote>“{text}”</blockquote>
      {cite && <figcaption>{cite}</figcaption>}
      {children}
    </figure>
  )
}

const docLink = (runId: string, sourceId: string, excerptId?: string) => (
  <Link to={`/runs/${runId}/sources/${sourceId}${excerptId ? `?ex=${excerptId}` : ''}`}
    target="_blank" rel="noopener">Open in document ↗</Link>
)

// a note on a decision: shown, edited in place, saved into the staged state
function Note({ value, editing, setEditing, onSave, hint, addLabel = 'Add a note', keyHint }:
  { value: string; editing: boolean; setEditing: (b: boolean) => void; onSave: (v: string) => void;
    hint: string; addLabel?: string; keyHint?: boolean }) {
  if (editing) return <NoteEditor value={value} setEditing={setEditing} onSave={onSave} hint={hint} />
  if (value.trim()) return (
    <p className="rv-note"><b>Your note</b> · {value}{' '}
      <button className="rv-link" onClick={() => setEditing(true)}>Edit</button></p>
  )
  return <button className="rv-act" onClick={() => setEditing(true)}>{addLabel}{keyHint && <span className="key">N</span>}</button>
}

function NoteEditor({ value, setEditing, onSave, hint }:
  { value: string; setEditing: (b: boolean) => void; onSave: (v: string) => void; hint: string }) {
  const [draft, setDraft] = useState(value)
  return (
    <div className="rv-edit">
      <label>Your note<span className="rv-hint">{hint}</span>
        <GrowingText value={draft} onChange={setDraft} autoFocus label="Your note"
          onKeyDown={e => { if (e.key === 'Escape') setEditing(false) }} /></label>
      <div className="row">
        <button className="small primary" onClick={() => { onSave(draft); setEditing(false) }}>Save note</button>
        <button className="small" onClick={() => setEditing(false)}>Cancel</button>
        {value.trim() && <button className="small quiet" onClick={() => { onSave(''); setEditing(false) }}>Remove note</button>}
      </div>
    </div>
  )
}

const toggled = (s: Set<string>, id: string) => {
  const c = new Set(s)
  if (c.has(id)) c.delete(id); else c.add(id)
  return c
}
const without = <T,>(o: Record<string, T>, key: string): Record<string, T> => {
  const c = { ...o }
  delete c[key]
  return c
}

/* The spreadsheet round trip: download the checkpoint as a workbook, edit it
   anywhere that opens one, upload it. The upload only STAGES decisions into
   this screen; the researcher reads them and approves as always, so there is
   one apply path and one audit trail. The links sit in the rail; what an
   upload loaded is said above the list. */
type Imported = { imported_from: SheetImport['imported_from']; summary: Record<string, number>;
                  ignored: SheetImport['ignored'] }
const SUMMARY_WORDS: Record<string, string> = {
  renamed: 'renamed', redefined: 'redefined', merged: 'merged', deleted: 'deleted', added: 'added',
  edited: 'papers edited', fields_edited: 'fields edited', excluded: 'excluded', reincluded: 're-included',
  with_notes: 'with notes',
}
function summaryLine(s: Record<string, number>): string {
  const parts = Object.entries(SUMMARY_WORDS).filter(([k]) => (s[k] ?? 0) > 0).map(([k, w]) => `${s[k]} ${w}`)
  return parts.length ? parts.join(', ') : 'no changes'
}
function useSheet(runId: string, cp: Checkpoint, staged: boolean, imported: Imported | null,
                  onImport: (r: SheetImport) => void, onError: (m: string) => void) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [showIgnored, setShowIgnored] = useState(false)
  const pick = async (f: File | undefined) => {
    if (!f) return
    if (staged && !(await ask({
      title: 'Replace the staged decisions?',
      body: ['The decisions loaded from the spreadsheet replace the ones staged on this screen now.'],
      confirm: 'Load the spreadsheet', cancel: 'Keep the staged decisions', danger: true,
    }))) { if (fileRef.current) fileRef.current.value = ''; return }
    setBusy(true)
    try { onImport(await api.importSheet(runId, cp.id, f)) }
    catch (e: any) { onError(String(e.message ?? e)) }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = '' }
  }
  const links = (
    <p>
      <a href={api.sheetUrl(runId, cp.id)} onClick={e => saveFile(e, api.sheetUrl(runId, cp.id))} title="Every item under review as an .xlsx workbook, with the rules on its About sheet">Download as spreadsheet</a>
      {' · '}
      <button className="rv-link" disabled={busy} onClick={() => fileRef.current?.click()}
        title="Upload the edited workbook; its decisions load here for you to check before approving">
        {busy ? 'Reading…' : 'Upload spreadsheet'}</button>
      <input ref={fileRef} type="file" accept=".xlsx" style={{ display: 'none' }}
        onChange={ev => pick(ev.target.files?.[0])} />
    </p>
  )
  const summary = imported && (
    <div className="sheetbar">
      <span className="small">Loaded from <span className="mono">{imported.imported_from.filename}</span>: {summaryLine(imported.summary)}
        {imported.ignored.length > 0 && (
          <> · {imported.ignored.length} row{imported.ignored.length === 1 ? '' : 's'} ignored{' '}
            <button className="rv-link" onClick={() => setShowIgnored(s => !s)}>({showIgnored ? 'hide' : 'show'})</button></>
        )}</span>
      {showIgnored && imported.ignored.length > 0 && (
        <ul className="small muted" style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {imported.ignored.map((g, i) => (
            <li key={i}>Row {g.row}{g.id ? <> (<span className="mono">{g.id}</span>)</> : null}: {g.reason}</li>
          ))}
        </ul>
      )}
    </div>
  )
  return { links, summary }
}

// The rail beside the list: where the review stands, and the one way out.
// Below 1100px it follows the list and Approve docks at the bottom.
function ReviewLayout({ main, evidence, tally, decisions, approveLabel, busy, onApprove, fine, habits, extra }:
  { main: ReactNode; evidence: ReactNode; tally: [string, ReactNode, boolean][]; decisions: string[];
    approveLabel: string; busy: boolean; onApprove: () => void; fine?: ReactNode; habits: ReactNode; extra?: ReactNode }) {
  const label = busy ? 'Applying…' : approveLabel
  return (
    <>
      <div className="rv">
        <div className="rv-main">{main}</div>
        <aside className="rv-rail" aria-label="Where the review stands">
          <section>
            <h3>Your review</h3>
            <p>{evidence}</p>
            <table className="rv-tally"><tbody>
              {tally.map(([l, v, zero]) => <tr key={l} className={zero ? 'zero' : ''}><td>{l}</td><td>{v}</td></tr>)}
            </tbody></table>
            <button className="primary rv-approve" disabled={busy} onClick={onApprove}>{label}</button>
            {fine && <p className="rv-fine">{fine}</p>}
            <p className="rv-fine">Nothing is applied until you approve. Your decisions stay in this browser if you leave the page.</p>
            {decisions.length > 0 && (
              <details><summary>See what will be recorded ({decisions.length})</summary>
                <ul className="rv-decisions">{decisions.map((d, i) => <li key={i}>{d}</li>)}</ul></details>
            )}
          </section>
          <section><h3>Working method</h3><ul>{habits}</ul></section>
          {extra && <section>{extra}</section>}
        </aside>
      </div>
      <div className="rv-dock">
        <span>{decisions.length ? `${plural(decisions.length, 'decision')} staged` : 'Nothing is staged yet'}</span>
        <button className="primary" disabled={busy} onClick={onApprove}>{label}</button>
      </div>
    </>
  )
}

const uncodedLine = (runId: string, coverage: any[] | undefined) => {
  if (!coverage?.length) return null
  const least = [...coverage].sort((a, b) => a.coded_pct - b.coded_pct)[0]
  const what = coverage.length === 1
    ? `${100 - least.coded_pct}% of the transcript has no code.`
    : `The least-coded source, ${least.filename}, has ${100 - least.coded_pct}% of its text uncoded.`
  return <li>Ask what the coder missed. {what}{' '}
    <Link to={`/runs/${runId}/sources/${least.source_id}`} target="_blank" rel="noopener">Read the uncoded text ↗</Link></li>
}

// ---------------------------------------------------------------- the code review

type Edits = { name?: string; definition?: string; notes?: string }
type Action = { kind: 'keep' | 'merge' | 'delete'; merge_into?: string }
type RowUI = { editing?: boolean; picking?: boolean; noting?: boolean; all?: boolean; memo?: string | null }

const NOUN: Record<string, [string, string]> = {
  open_code: ['code', 'codes'], codebook: ['code', 'codes'], category: ['category', 'categories'],
  theme: ['theme', 'themes'], concept: ['concept', 'concepts'],
}
const ADD_HINT: Record<string, string> = {
  codebook: 'An added code enters the codebook and is applied to every source.',
  open_code: 'An added code has no excerpts. A category or theme can still claim it, and the report lists it without evidence.',
  category: 'An added category stays empty. No later stage assigns codes to it.',
  theme: 'An added theme stays empty. No later stage assigns codes to it.',
  concept: 'An added concept has no quotes. The matrix shows it empty.',
}

function CodeReview({ runId, cp, onError, onResolved }: PanelProps) {
  const items: any[] = cp.payload.items ?? []
  const stage: string = cp.payload.stage ?? 'open_code'
  const [noun, nouns] = NOUN[stage] ?? ['code', 'codes']
  const codebook = stage === 'codebook'            // nothing coded yet: definitions in the abstract
  // a category or theme is a grouping even in a review opened before 2026-11-15,
  // whose payload does not list the codes each one holds
  const kidsKnown = items.some(i => Array.isArray(i.children))
  const grouping = stage === 'category' || stage === 'theme' || kidsKnown
  const kids = (it: any) => Array.isArray(it.children) ? plural(it.children.length, 'code') : 'codes'
  const { stored, save, clear } = useStored(cp)
  // edits (rename/redefine/note) and actions (merge/delete) are independent,
  // so undoing a merge never discards a rename made before it
  const [edits, setEdits] = useState<Record<string, Edits>>(stored.edits ?? {})
  const [actions, setActions] = useState<Record<string, Action>>(stored.actions ?? {})
  const [additions, setAdditions] = useState<{ name: string; definition: string; notes?: string }[]>(stored.additions ?? [])
  const [checked, setChecked] = useState<Set<string>>(new Set(stored.checked ?? []))
  const [imported, setImported] = useState<Imported | null>(stored.imported ?? null)
  const [ui, setUi] = useState<Record<string, RowUI>>({})
  const [all, setAll] = useState<Record<string, any[] | 'loading'>>({})
  const [focusId, setFocusId] = useState('')
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<'most' | 'thin' | 'az' | 'orig'>('most')
  const [bulkPick, setBulkPick] = useState(false)
  // Decided 2026-11-15: a review of more than 40 codes opens in names only;
  // after that, the view last chosen is remembered
  const [compact, setCompact] = useState<boolean>(() => {
    try { const v = localStorage.getItem('ql-review-view'); if (v) return v === 'names' } catch { /* fine */ }
    return items.length > 40
  })
  const listRef = useRef<HTMLUListElement>(null)
  const { busy, submit } = useSubmit(runId, cp, onError, () => { clear(); onResolved() })

  useEffect(() => { save({ edits, actions, additions, checked: [...checked], imported }) },
    [edits, actions, additions, checked, imported])  // eslint-disable-line react-hooks/exhaustive-deps

  const act = (id: string): Action => actions[id] ?? { kind: 'keep' }
  const byId = (id?: string) => items.find(i => i.id === id)
  const nameOf = (it: any) => edits[it.id]?.name ?? it.name
  const defOf = (it: any) => edits[it.id]?.definition ?? it.definition ?? ''
  const noteOf = (id: string) => edits[id]?.notes ?? ''
  const setEdit = (id: string, patch: Edits) => setEdits(e => ({ ...e, [id]: { ...e[id], ...patch } }))
  const setRow = (id: string, patch: RowUI) => setUi(u => ({ ...u, [id]: { ...u[id], ...patch } }))
  const renamed = (it: any) => act(it.id).kind === 'keep' && (
    (edits[it.id]?.name !== undefined && edits[it.id]!.name!.trim() !== '' && edits[it.id]!.name !== it.name)
    || (edits[it.id]?.definition !== undefined && edits[it.id]!.definition !== (it.definition ?? '')))

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
    setChecked(new Set()); setBulkPick(false)
    setImported({ imported_from: r.imported_from, summary: r.summary, ignored: r.ignored })
  }
  const staged = Object.keys(edits).length + Object.keys(actions).length + additions.length > 0
  const sheet = useSheet(runId, cp, staged, imported, loadSheet, onError)

  // Marking codes deleted also drops them from the selection and un-stages
  // any merges pointing INTO them: a delete must never silently expand into
  // deleting other codes' merged evidence.
  const markDelete = (ids: string[]) => {
    setActions(x => {
      const n = { ...x }
      ids.forEach(id => { n[id] = { kind: 'delete' } })
      for (const [k, v] of Object.entries(n))
        if (v.kind === 'merge' && v.merge_into && ids.includes(v.merge_into)) delete n[k]
      return n
    })
    setChecked(s => { const c = new Set(s); ids.forEach(id => c.delete(id)); return c })
  }
  // the target must be a kept code
  const markMerge = (ids: string[], into: string) => {
    if (act(into).kind !== 'keep') return
    setActions(x => {
      const n = { ...x }
      ids.forEach(id => { if (id !== into && (x[id]?.kind ?? 'keep') === 'keep') n[id] = { kind: 'merge', merge_into: into } })
      return n
    })
    setChecked(s => { const c = new Set(s); ids.forEach(id => c.delete(id)); return c })
  }
  const undo = (id: string) => setActions(x => without(x, id))

  const q = search.trim().toLowerCase()
  const visible = items.map((it, i) => ({ it, i }))
    .filter(({ it }) => !q || nameOf(it).toLowerCase().includes(q) || defOf(it).toLowerCase().includes(q))
    .sort((a, b) => sortKey === 'most' ? b.it.excerpt_count - a.it.excerpt_count || a.i - b.i
      : sortKey === 'thin' ? a.it.excerpt_count - b.it.excerpt_count || a.i - b.i
      : sortKey === 'az' ? nameOf(a.it).localeCompare(nameOf(b.it)) : a.i - b.i)
    .map(x => x.it)
  const kept = items.filter(i => act(i.id).kind === 'keep')

  // what Approve will submit, exactly as done() builds it
  const tally = useMemo(() => {
    const merging = items.filter(i => act(i.id).kind === 'merge')
    const t = {
      renamed: items.filter(renamed).length, merging: merging.length,
      deleting: items.filter(i => act(i.id).kind === 'delete').length,
      added: additions.filter(a => a.name.trim()).length,
      notes: items.filter(i => noteOf(i.id).trim()).length,
      considered: items.filter(i => act(i.id).kind === 'keep' && !renamed(i) && noteOf(i.id).trim()).length,
      unchanged: items.filter(i => act(i.id).kind === 'keep' && !renamed(i)).length,
    }
    return { ...t, decisions: t.renamed + t.merging + t.deleting + t.added + t.considered }
  }, [items, edits, actions, additions])  // eslint-disable-line react-hooks/exhaustive-deps
  const decisionsList = [
    ...items.flatMap(o => {
      const a = act(o.id)
      if (a.kind === 'merge') return [`Merge “${o.name}” into “${nameOf(byId(a.merge_into) ?? { name: '?' })}”`]
      if (a.kind === 'delete') return [`Delete “${o.name}”`]
      if (renamed(o)) return [nameOf(o) !== o.name ? `Rename “${o.name}” to “${nameOf(o)}”` : `Redefine “${o.name}”`]
      if (noteOf(o.id).trim()) return [`Keep “${o.name}”, with a note`]
      return []
    }),
    ...additions.filter(a => a.name.trim()).map(a => `Add “${a.name.trim()}”`),
  ]

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
          list.push({ id: it.id, action: 'rename', name: nameChanged ? e.name : undefined,
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

  const showAll = async (it: any) => {
    const open = !ui[it.id]?.all
    setRow(it.id, { all: open })
    if (open && !all[it.id]) {
      setAll(x => ({ ...x, [it.id]: 'loading' }))
      try {
        const ex = await api.codeExcerpts(runId, it.id)
        setAll(x => ({ ...x, [it.id]: ex }))
      } catch (e: any) { setAll(x => without(x, it.id)); onError(String(e.message ?? e)) }
    }
  }

  // keys act on the code the key was pressed in, never on remembered state
  const onKeys = (e: KeyboardEvent<HTMLUListElement>) => {
    const t = e.target as HTMLElement
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || e.metaKey || e.ctrlKey || e.altKey) return
    const row = t.closest<HTMLElement>('[data-id]')
    const rows = [...(listRef.current?.querySelectorAll<HTMLElement>('li[data-id]') ?? [])]
    const i = row ? rows.indexOf(row) : -1
    const go = (j: number) => { const r = rows[Math.max(0, Math.min(rows.length - 1, j))]; r?.focus(); r?.scrollIntoView({ block: 'nearest' }) }
    const k = e.key.toLowerCase()
    if (k === 'j' || e.key === 'ArrowDown') { e.preventDefault(); go(i + 1); return }
    if (k === 'k' || e.key === 'ArrowUp') { e.preventDefault(); go(i < 0 ? 0 : i - 1); return }
    if (!row || t !== row) return
    const id = row.dataset.id!, a = act(id).kind
    const hit = (fn: () => void) => { e.preventDefault(); fn() }
    if (k === 'r' && a === 'keep') hit(() => setRow(id, { editing: true, picking: false }))
    else if (k === 'm' && a === 'keep') hit(() => setRow(id, { picking: !ui[id]?.picking, editing: false }))
    else if (k === 'd' && a === 'keep') hit(() => markDelete([id]))
    else if (k === 'u' && a !== 'keep') hit(() => undo(id))
    else if (k === 'n') hit(() => setRow(id, { noting: true }))
    else if (k === 'x' && a === 'keep') hit(() => setChecked(s => toggled(s, id)))
  }

  const thin = items.filter(i => i.excerpt_count === 1).length
  // the sources the items' evidence comes from; a payload from before 2026-11-15 has no count, and the sentence leaves it out
  const nSources: number = cp.payload.source_count ?? 0
  const exTotal = items.reduce((n, i) => n + (i.excerpt_count ?? 0), 0)
  const evidence = codebook
    ? `The codebook holds ${plural(items.length, noun, nouns)}. None has been applied yet.`
    : grouping && !kidsKnown
      ? `${plural(items.length, noun, nouns)} hold ${plural(exTotal, 'excerpt')}${nSources ? ` from ${plural(nSources, 'source')}` : ''}.`
    : grouping
      ? `${plural(items.length, noun, nouns)} hold ${plural(items.reduce((n, i) => n + (i.children?.length ?? 0), 0), 'code')} and ${plural(exTotal, 'excerpt')}${nSources ? ` from ${plural(nSources, 'source')}` : ''}.`
        + (() => { const one = items.filter(i => i.children?.length === 1).length
                   return one ? ` ${one === 1 ? `One ${noun} rests` : `${one} ${nouns} rest`} on a single code.` : '' })()
      : `${plural(items.length, noun, nouns)} hold ${plural(exTotal, 'excerpt')}${nSources ? ` from ${plural(nSources, 'source')}` : ''}.`
        + (thin && thin === items.length ? ` Every ${noun} rests on a single excerpt.` : thin ? ` ${plural(thin, `${noun} rests`, `${nouns} rest`)} on a single excerpt.` : '')

  const row = (it: any) => {
    const a = act(it.id), u = ui[it.id] ?? {}, id = it.id
    const n = it.excerpt_count ?? 0
    const count = codebook ? 'not yet applied' : `${plural(n, 'excerpt')}${it.source_count !== undefined ? ` · ${plural(it.source_count, 'source')}` : ''}`
    const note = <Note value={noteOf(id)} editing={!!u.noting} setEditing={b => setRow(id, { noting: b })} keyHint
      onSave={v => setEdit(id, { notes: v })} hint="Why you decided as you did. It goes into the audit trail beside the decision." />
    const head = (
      <div className="rv-head"><h3 className="rv-name">{nameOf(it)}</h3><span className="rv-count">{count}</span></div>
    )
    const check = (
      <input type="checkbox" checked={checked.has(id)} disabled={a.kind !== 'keep'} aria-label={`Select ${nameOf(it)}`}
        onChange={() => { setBulkPick(false); setChecked(s => toggled(s, id)) }} />
    )
    if (a.kind !== 'keep') {
      const target = byId(a.merge_into)
      const what = a.kind === 'merge'
        ? <>It will merge into <b>{nameOf(target ?? { name: '?' })}</b>. {grouping ? `Its ${kids(it)} and their evidence move with it.` : n === 1 ? 'Its excerpt moves with it.' : 'Its excerpts move with it.'}</>
        : grouping ? <>It will be deleted. Its {kids(it)} stay, listed under Uncategorized in the report.</>
        : <>It will be deleted{n ? `, with ${n === 1 ? 'its excerpt' : `its ${n} excerpts`}` : ''}.</>
      return (
        <li key={id} data-id={id} tabIndex={0} className={`rv-row is-${a.kind}${focusId === id ? ' is-focus' : ''}`} onFocus={() => setFocusId(id)}>
          {check}<div>{head}<p className="rv-decision">{what}</p>
            <div className="rv-actions"><button className="rv-act" onClick={() => undo(id)}>Undo {a.kind}<span className="key">U</span></button>{!noteOf(id).trim() && !u.noting && note}</div>
            {(noteOf(id).trim() || u.noting) && note}</div>
        </li>
      )
    }
    const absorbs = items.filter(o => act(o.id).kind === 'merge' && act(o.id).merge_into === id)
    const samples: any[] = it.sample_excerpts ?? []
    const full = all[id]
    const shown = u.all ? (Array.isArray(full) ? full : samples) : samples.slice(0, 1)
    const nameChanged = edits[id]?.name !== undefined && edits[id]!.name!.trim() !== '' && edits[id]!.name !== it.name
    return (
      <li key={id} data-id={id} tabIndex={0} className={`rv-row${focusId === id ? ' is-focus' : ''}`} onFocus={() => setFocusId(id)}>
        {check}
        <div>
          {u.editing ? <RenameBox it={it} name={nameOf(it)} def={defOf(it)} noun={noun}
              onDone={(nm, df) => {
                const patch: Edits = {}
                if (nm.trim()) patch.name = nm          // a blank name keeps the old one
                patch.definition = df                    // a blank definition is a decision
                setEdit(id, patch); setRow(id, { editing: false })
                setTimeout(() => listRef.current?.querySelector<HTMLElement>(`li[data-id="${id}"]`)?.focus())
              }}
              onCancel={() => setRow(id, { editing: false })} />
            : <>
              {head}
              {nameChanged && <p className="rv-was">Renamed from “{it.name}”</p>}
              <p className="rv-def">{defOf(it) || <span className="muted">No definition</span>}</p>
              {Array.isArray(it.children) && it.children.length > 0 && (
                <p className="rv-kids">It holds {plural(it.children.length, 'code')} ({it.children.map((k: any, j: number) => (
                  <Fragment key={k.id}>{j > 0 && ' · '}<span>{k.name}</span></Fragment>))}).</p>
              )}
              {it.candidate_name && it.candidate_name !== it.name && (
                <p className="rv-was">Phase 5 named it from the candidate “{it.candidate_name}”. The report carries the name and definition above unless you edit them.</p>
              )}
              {it.review && (
                <p className="rv-memo"><b>The model’s own critique:</b> coherence {it.review.coherence}, distinctness {it.review.distinctness}; recommends {it.review.recommendation}. {it.review.notes}</p>
              )}
              {(it.papers ?? []).length > 0 && (
                <p className="rv-kids">It is supported by {plural(it.papers.length, 'paper')} ({it.papers.join(' · ')}).</p>
              )}
              {absorbs.length > 0 && <p className="rv-absorbs">Absorbs {absorbs.map(o => `“${nameOf(o)}”`).join(', ')}</p>}
              {!codebook && shown.map((x: any) => (
                <Quote key={x.id ?? x.quote} text={x.quote + (x.truncated && !u.all ? '…' : '')}
                  cite={<>
                    {x.via && <span className="via">via {x.via} · </span>}
                    {x.source}
                    {x.memo && <> · <button aria-expanded={u.memo === (x.id ?? x.quote)}
                      onClick={() => setRow(id, { memo: u.memo === (x.id ?? x.quote) ? null : (x.id ?? x.quote) })}>Coder’s memo</button></>}
                    {x.source_id && <> · {docLink(runId, x.source_id, x.id)}</>}
                  </>}>
                  {u.memo === (x.id ?? x.quote) && x.memo && <p className="rv-memo"><b>Coder’s memo:</b> {x.memo}</p>}
                </Quote>
              ))}
              {codebook && <p className="rv-def muted">It has no excerpts yet. The codebook is applied after this review.</p>}
              {!codebook && n > 1 && (
                <p className="rv-more"><button className="rv-link" aria-expanded={!!u.all} onClick={() => showAll(it)}>
                  {u.all ? 'Show only the first excerpt' : full === 'loading' ? 'Loading…' : `Show all ${n} excerpts`}</button></p>
              )}
              {it.rationale && u.all && <p className="rv-memo"><b>Why the coder formed it:</b> {it.rationale}</p>}
              <div className="rv-actions">
                <button className="rv-act" onClick={() => setRow(id, { editing: true, picking: false })}>{grouping ? 'Rename or redefine' : 'Rename'}<span className="key">R</span></button>
                <button className="rv-act" aria-expanded={!!u.picking} onClick={() => setRow(id, { picking: !u.picking, editing: false })}>Merge into…<span className="key">M</span></button>
                <button className="rv-act del" onClick={() => markDelete([id])}>Delete<span className="key">D</span></button>
                {!noteOf(id).trim() && !u.noting && note}
              </div>
              {(noteOf(id).trim() || u.noting) && note}
              {u.picking && <MergePicker noun={noun} exclude={[id]} options={kept} nameOf={nameOf}
                onPick={into => { markMerge([id], into); setRow(id, { picking: false }) }}
                onClose={() => setRow(id, { picking: false })} />}
            </>}
        </div>
      </li>
    )
  }

  const main = (
    <>
      <div className="rv-toolbar">
        <input type="search" placeholder={`Search ${plural(items.length, noun, nouns)}`} aria-label="Search"
          value={search} onChange={e => setSearch(e.target.value)} />
        <div className="rv-seg" role="group" aria-label="Order">
          {([['most', 'Most evidence'], ['thin', 'Thinnest first'], ['az', 'A–Z'], ['orig', 'Original']] as const).map(([v, l]) => (
            <button key={v} aria-pressed={sortKey === v} onClick={() => setSortKey(v)}>{l}</button>))}
        </div>
        <span className="rv-shown">
          {visible.length === items.length ? plural(items.length, noun, nouns) : `${visible.length} of ${items.length} shown`}
          {' · '}<button className="rv-link rv-view" onClick={() => {
            setCompact(c => { try { localStorage.setItem('ql-review-view', c ? 'evidence' : 'names') } catch { /* fine */ } return !c })
          }}>{compact ? 'Show evidence' : 'Names only'}</button>
        </span>
        {checked.size > 0 && (
          <div className="rv-bulk">
            <b>{checked.size} selected</b>
            <button className="rv-link" aria-expanded={bulkPick} onClick={() => setBulkPick(b => !b)}>Merge into…</button>
            <button className="rv-link" onClick={() => { markDelete([...checked]); setBulkPick(false) }}>Delete</button>
            <button className="rv-link" onClick={() => { setChecked(new Set()); setBulkPick(false) }}>Clear selection</button>
            {bulkPick && <MergePicker noun={noun} exclude={[...checked]} options={kept} nameOf={nameOf}
              onPick={into => { markMerge([...checked], into); setBulkPick(false) }} onClose={() => setBulkPick(false)} />}
          </div>
        )}
      </div>
      {sheet.summary}
      <ul className={`rv-list${compact ? ' compact' : ''}`} ref={listRef} onKeyDown={onKeys}>
        {visible.map(row)}
        {visible.length === 0 && <li className="rv-row"><span /><p className="rv-def">No {noun} matches “{search}”.</p></li>}
        {additions.map((a, i) => (
          <li key={`add-${i}`} className="rv-row"><span />
            <div className="rv-edit">
              <label>Name<input type="text" value={a.name} placeholder={`A ${noun} the coder missed`}
                onChange={ev => setAdditions(x => x.map((y, j) => j === i ? { ...y, name: ev.target.value } : y))} /></label>
              <label>Definition<GrowingText value={a.definition} label="Definition"
                onChange={v => setAdditions(x => x.map((y, j) => j === i ? { ...y, definition: v } : y))} /></label>
              {a.notes && <p className="rv-note"><b>Note</b> · {a.notes}</p>}
              <span className="rv-hint">{ADD_HINT[stage] ?? ADD_HINT.open_code}</span>
              <div className="row"><button className="small quiet" onClick={() => setAdditions(x => x.filter((_, j) => j !== i))}>Remove</button></div>
            </div>
          </li>
        ))}
      </ul>
      <p className="rv-add"><button className="rv-link" onClick={() => setAdditions(x => [...x, { name: '', definition: '' }])}>+ Add a {noun} the coder missed</button></p>
    </>
  )
  const zero = (n: number) => n === 0
  return (
    <ReviewLayout main={main} evidence={evidence}
      tally={[['Renamed', tally.renamed, zero(tally.renamed)], ['Merging', tally.merging, zero(tally.merging)],
              ['Deleting', tally.deleting, zero(tally.deleting)], ['Added', tally.added, zero(tally.added)],
              ['With a note', tally.notes, zero(tally.notes)], ['Unchanged', tally.unchanged, false]]}
      decisions={decisionsList} busy={busy} onApprove={done}
      approveLabel={tally.decisions ? `Approve ${plural(tally.decisions, 'decision')} and continue` : 'Approve as proposed and continue'}
      habits={<>
        {codebook
          ? <li>Read each definition as the coder will apply it. A vague one is coded loosely in every source.</li>
          : grouping
            ? <li>Check that each {noun}’s codes belong together. Merge {nouns} that name one idea, starting with the thin ones. <button className="rv-link" onClick={() => setSortKey('thin')}>Thinnest first</button></li>
            : <li>Start from the thinnest {nouns}. Near-duplicates and one-off observations collect there. <button className="rv-link" onClick={() => setSortKey('thin')}>Thinnest first</button></li>}
        {!codebook && <li>Before trusting a neat {noun}, open its quote in the document.</li>}
        {(stage === 'open_code' || grouping) && uncodedLine(runId, cp.payload.coverage)}
      </>}
      extra={<>{sheet.links}
        <p className="rv-fine">Keys: <kbd>↑</kbd> <kbd>↓</kbd> move · <kbd>R</kbd> rename · <kbd>M</kbd> merge · <kbd>D</kbd> delete · <kbd>N</kbd> note · <kbd>U</kbd> undo · <kbd>X</kbd> select</p></>} />
  )
}

function RenameBox({ name, def, noun, onDone, onCancel }:
  { it: any; name: string; def: string; noun: string; onDone: (n: string, d: string) => void; onCancel: () => void }) {
  const [n, setN] = useState(name)
  const [d, setD] = useState(def)
  const keys = (e: KeyboardEvent<HTMLElement>, enterSaves: boolean) => {
    if (e.key === 'Escape') { e.preventDefault(); onCancel() }
    if (e.key === 'Enter' && (enterSaves || e.metaKey || e.ctrlKey)) { e.preventDefault(); onDone(n, d) }
  }
  return (
    <div className="rv-edit">
      <label>Name<input type="text" value={n} autoFocus onChange={e => setN(e.target.value)} onKeyDown={e => keys(e, true)} /></label>
      <label>Definition<GrowingText value={d} onChange={setD} label="Definition" onKeyDown={e => keys(e, false)} /></label>
      <div className="row">
        <button className="small primary" onClick={() => onDone(n, d)}>Done</button>
        <button className="small" onClick={onCancel}>Cancel</button>
        <span className="rv-hint">Enter saves · Esc cancels. Later stages keep your wording. A {noun} left without a name keeps its old one.</span>
      </div>
    </div>
  )
}

function MergePicker({ noun, exclude, options, nameOf, onPick, onClose }:
  { noun: string; exclude: string[]; options: any[]; nameOf: (it: any) => string;
    onPick: (id: string) => void; onClose: () => void }) {
  const [q, setQ] = useState('')
  const listRef = useRef<HTMLUListElement>(null)
  const opts = options.filter(o => !exclude.includes(o.id) && (!q.trim() || nameOf(o).toLowerCase().includes(q.trim().toLowerCase())))
    .sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
  return (
    <div className="rv-picker">
      <div className="rv-pick-head">Merge into the {noun} whose name you want to keep</div>
      <input type="text" value={q} autoFocus placeholder={`Find a ${noun}…`} aria-label={`Find a ${noun}`}
        onChange={e => setQ(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Escape') { e.preventDefault(); onClose() }
          if (e.key === 'Enter' && opts[0]) { e.preventDefault(); onPick(opts[0].id) }
          if (e.key === 'ArrowDown') { e.preventDefault(); listRef.current?.querySelector<HTMLElement>('button')?.focus() }
        }} />
      <ul ref={listRef}>
        {opts.map(o => (
          <li key={o.id}><button onClick={() => onPick(o.id)} onKeyDown={e => { if (e.key === 'Escape') onClose() }}>
            <span>{nameOf(o)}</span><span className="n">{plural(o.excerpt_count ?? 0, 'excerpt')}</span></button></li>
        ))}
        {opts.length === 0 && <li className="rv-pick-head" style={{ padding: '8px 12px' }}>No {noun} matches.</li>}
      </ul>
      <div className="rv-pick-foot"><button className="rv-link" onClick={onClose}>Cancel</button></div>
    </div>
  )
}

// ---------------------------------------------------------------- the core category (grounded theory)

function CoreReview({ runId, cp, onError, onResolved }: PanelProps) {
  const core = (cp.payload.items ?? [])[0]
  const categories: any[] = cp.payload.categories ?? []
  // a review opened by a version before 2026-11-15 carries no categories, so it
  // cannot name them or draw the figure; it must not call them missing
  const legacy = !Array.isArray(cp.payload.categories)
  const { stored, save, clear } = useStored(cp)
  const [name, setName] = useState<string>(stored.name ?? core?.name ?? '')
  const [definition, setDefinition] = useState<string>(stored.definition ?? core?.definition ?? '')
  const [storyline, setStoryline] = useState<string>(stored.storyline ?? core?.storyline ?? '')
  const origGaps: string[] = core?.theoretical_gaps ?? []
  const [gaps, setGaps] = useState<{ text: string; orig: string | null; gone?: boolean }[]>(
    stored.gaps ?? origGaps.map(t => ({ text: t, orig: t })))
  const [note, setNote] = useState<string>(stored.note ?? '')
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState({ name: '', def: '', story: '', gap: '' })
  const [showWas, setShowWas] = useState<Record<string, boolean>>({})
  const [noting, setNoting] = useState(false)
  const { busy, submit } = useSubmit(runId, cp, onError, () => { clear(); onResolved() })
  useEffect(() => { save({ name, definition, storyline, gaps, note }) },
    [name, definition, storyline, gaps, note])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!core) return <p className="desc">Selective coding produced no core category. There is nothing to approve here.</p>

  const nameEd = name !== core.name, defEd = definition !== (core.definition ?? ''), storyEd = storyline !== (core.storyline ?? '')
  const finalGaps = gaps.filter(g => !g.gone && g.text.trim()).map(g => g.text.trim())
  const gapsEd = JSON.stringify(finalGaps) !== JSON.stringify(origGaps)
  const decisions = [
    nameEd && `Rename the core category to “${name}”`, defEd && 'Redefine the core category',
    storyEd && 'Rewrite the storyline', gapsEd && 'Change the sampling recommendations',
    note.trim() && 'A note with the approval',
  ].filter(Boolean) as string[]
  const catName = (id: string) => categories.find(c => c.id === id)
  const related = new Set((core.relationships ?? []).map((r: any) => r.from_category_id))
  const themes = categories.map(c => ({ id: c.id, name: c.name, excerpts: new Array(c.excerpts).fill(0), children: [] }))
  const stats = { kind: 'gt_model', core: { name, definition, existing_category_id: core.existing_category_id }, relationships: core.relationships ?? [] }

  const approve = () => submit({ decisions: [{
    id: core.id, name, definition, storyline,
    ...(gapsEd ? { theoretical_gaps: finalGaps } : {}),
    ...(note.trim() ? { notes: note.trim() } : {}),
  }] })

  const editedLine = (what: string, k: string, undoFn: () => void) => (
    <p className="pn-edited">You {what} · <button onClick={() => setShowWas(s => ({ ...s, [k]: !s[k] }))}>{showWas[k] ? 'Hide' : 'Show'} the model’s version</button>
      {' · '}<button onClick={() => { undoFn(); setShowWas(s => ({ ...s, [k]: false })) }}>Undo</button></p>
  )
  const main = (
    <>
      <div className="pn-sec"><h3>The core category</h3>
        {editing === 'core' ? (
          <div className="rv-edit">
            <label>Core category<input type="text" autoFocus value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} /></label>
            <label>Definition<GrowingText value={draft.def} label="Definition" onChange={v => setDraft(d => ({ ...d, def: v }))} /></label>
            <div className="row">
              <button className="small primary" onClick={() => { if (draft.name.trim()) setName(draft.name.trim()); setDefinition(draft.def.trim()); setEditing(null) }}>Done</button>
              <button className="small" onClick={() => setEditing(null)}>Cancel</button>
              <span className="rv-hint">A core category with no name keeps its old one.</span>
            </div>
          </div>
        ) : <>
          <p className="pn-core-name">{name}</p>
          <p className="pn-core-def">{definition}</p>
          {(nameEd || defEd) && editedLine(`edited the ${[nameEd && 'name', defEd && 'definition'].filter(Boolean).join(' and ')}`, 'core',
            () => { setName(core.name); setDefinition(core.definition ?? '') })}
          {showWas.core && <div className="pn-was"><b>{core.name}</b><br />{core.definition}</div>}
          <div className="rv-actions"><button className="rv-act" onClick={() => { setDraft(d => ({ ...d, name, def: definition })); setEditing('core') }}>Edit the name or definition</button></div>
        </>}
      </div>
      <div className="pn-sec"><h3>Storyline</h3>
        <p className="pn-lede">The report opens with this text. Rewrite it in your own words.</p>
        {editing === 'story' ? (
          <div className="rv-edit">
            <GrowingText value={draft.story} className="pn-grow" label="Storyline" autoFocus onChange={v => setDraft(d => ({ ...d, story: v }))} />
            <div className="row">
              <button className="small primary" onClick={() => { setStoryline(draft.story.trim()); setEditing(null) }}>Done</button>
              <button className="small" onClick={() => setEditing(null)}>Cancel</button>
              <span className="rv-hint">Your wording is final.</span>
            </div>
          </div>
        ) : <>
          <p className="pn-story">{storyline}</p>
          {storyEd && editedLine('rewrote the storyline', 'story', () => setStoryline(core.storyline ?? ''))}
          {showWas.story && <div className="pn-was pn-story-was">{core.storyline}</div>}
          <div className="rv-actions"><button className="rv-act" onClick={() => { setDraft(d => ({ ...d, story: storyline })); setEditing('story') }}>Rewrite the storyline</button></div>
        </>}
      </div>
      <div className="pn-sec"><h3>How each category relates to the core</h3>
        <p className="pn-lede">{legacy
          ? 'These relationships are the model’s proposal. This review was opened by an earlier version of QualiLens, which did not name the categories here. The report still draws its figure from them. You cannot edit them here, but a note can record where you disagree.'
          : 'These relationships are the model’s proposal. The report draws this figure from them. You cannot edit them here, but a note can record where you disagree.'}</p>
        {categories.length > 0 && (
          <figure className="pn-figure"><GTModel themes={themes} stats={stats} />
            <figcaption>The grounded theory model, as the report will draw it</figcaption></figure>
        )}
        <ul className="pn-rel">
          {(core.relationships ?? []).map((r: any, i: number) => {
            const c = catName(r.from_category_id)
            return (
              <li key={i}><span className="cat">{c ? c.name : legacy ? 'A category' : 'A category no longer in this run'}</span>
                <span className="n">{c ? `${plural(c.codes, 'code')} · ${plural(c.excerpts, 'excerpt')}` : ''}</span>
                <span className="how">Proposed relation: <b>{r.relation}</b>. {r.explanation}</span></li>
            )
          })}
          {categories.filter(c => !related.has(c.id) && c.id !== core.existing_category_id).map(c => (
            <li key={c.id}><span className="cat">{c.name}</span><span className="n">{plural(c.codes, 'code')} · {plural(c.excerpts, 'excerpt')}</span>
              <span className="none">No relationship to the core was proposed. A core category should account for every category.</span></li>
          ))}
        </ul>
      </div>
      <div className="pn-sec"><h3>Where the data are thin</h3>
        <p className="pn-lede">These go into the report, word for word, as its Theoretical Sampling Recommendations. Edit them, leave them out, or add to them before they do.</p>
        <ol className="pn-gaps">
          {gaps.map((g, i) => editing === `gap${i}` ? (
            <li key={i}><div className="rv-edit" style={{ margin: 0 }}>
              <GrowingText value={draft.gap} label="Where the data are thin" autoFocus onChange={v => setDraft(d => ({ ...d, gap: v }))} />
              <div className="row">
                <button className="small primary" onClick={() => {
                  const v = draft.gap.trim()
                  setGaps(x => v ? x.map((y, j) => j === i ? { ...y, text: v } : y) : x.filter((y, j) => !(j === i && y.orig === null)))
                  setEditing(null)
                }}>Done</button>
                <button className="small" onClick={() => { if (g.orig === null && !g.text) setGaps(x => x.filter((_, j) => j !== i)); setEditing(null) }}>Cancel</button>
              </div></div></li>
          ) : (
            <li key={i} className={g.gone ? 'is-gone' : ''}><div><span>{g.text}</span>
              {g.orig === null ? <span className="muted small"> · added by you</span> : g.text !== g.orig && !g.gone ? <span className="muted small"> · edited</span> : null}
              <div className="rv-actions">{g.gone
                ? <button className="rv-act" onClick={() => setGaps(x => x.map((y, j) => j === i ? { ...y, gone: false } : y))}>Keep it</button>
                : <>
                  <button className="rv-act" onClick={() => { setDraft(d => ({ ...d, gap: g.text })); setEditing(`gap${i}`) }}>Edit</button>
                  <button className="rv-act del" onClick={() => setGaps(x => g.orig === null ? x.filter((_, j) => j !== i) : x.map((y, j) => j === i ? { ...y, gone: true } : y))}>Leave out of the report</button>
                </>}</div></div></li>
          ))}
        </ol>
        <p className="rv-add"><button className="rv-link" onClick={() => { setGaps(x => [...x, { text: '', orig: null }]); setDraft(d => ({ ...d, gap: '' })); setEditing(`gap${gaps.length}`) }}>+ Add a place where the data are thin</button></p>
      </div>
      <div className="pn-sec"><h3>Your note</h3>
        <Note value={note} editing={noting} setEditing={setNoting} onSave={setNote}
          hint="Why you changed what you changed, or why you approve it as it stands. It goes into the audit trail with your approval." />
      </div>
    </>
  )
  const kept = gaps.filter(g => !g.gone && g.text.trim()).length
  return (
    <ReviewLayout main={main}
      evidence={legacy
        ? `The model proposes ${plural((core.relationships ?? []).length, 'relationship')} between the categories and the core and finds ${plural(origGaps.length, 'place')} where the data are thin.`
        : `One core category integrates ${plural(categories.length, 'category', 'categories')}. The model proposes ${plural((core.relationships ?? []).length, 'relationship')} and finds ${plural(origGaps.length, 'place')} where the data are thin.`}
      tally={[['Core category', nameEd || defEd ? 'Edited' : 'Unchanged', !(nameEd || defEd)],
              ['Storyline', storyEd ? 'Rewritten' : 'Unchanged', !storyEd],
              ['Sampling recommendations', gapsEd ? `${kept} (changed)` : String(kept), !gapsEd],
              ['Note', note.trim() ? 'Added' : 'None', !note.trim()]]}
      decisions={decisions} busy={busy} onApprove={approve}
      approveLabel={decisions.length ? `Approve ${plural(decisions.length, 'change')} and continue` : 'Approve as proposed and continue'}
      habits={<>
        <li>Read the storyline against the categories. Each should find its place in it.</li>
        <li>Rewrite it in your own words. The report opens with it.</li>
        <li>Check the thin places before they become the report’s recommendations.</li>
      </>} />
  )
}

// ---------------------------------------------------------------- charting (framework analysis)

function FrameworkReview({ runId, cp, onError, onResolved }: PanelProps) {
  const lowConf: any[] = cp.payload.low_confidence ?? []
  const emergent: any[] = cp.payload.items ?? []
  const framework: any[] = cp.payload.framework ?? []
  const { stored, save, clear } = useStored(cp)
  const [deletions, setDeletions] = useState<Set<string>>(new Set(stored.deletions ?? []))
  const [decisions, setDecisions] = useState<Record<string, 'keep' | 'delete'>>(stored.decisions ?? {})
  const [notes, setNotes] = useState<Record<string, string>>(stored.notes ?? {})
  const [noting, setNoting] = useState<Record<string, boolean>>({})
  const [memo, setMemo] = useState<Record<string, boolean>>({})
  const [byCode, setByCode] = useState(framework.length > 0)   // each definition once, when the payload has them
  const { busy, submit } = useSubmit(runId, cp, onError, () => { clear(); onResolved() })
  useEffect(() => { save({ deletions: [...deletions], decisions, notes }) },
    [deletions, decisions, notes])  // eslint-disable-line react-hooks/exhaustive-deps

  const fw = (name: string) => framework.find(f => f.name === name)
  const noteFor = (id: string) => (
    <Note value={notes[id] ?? ''} editing={!!noting[id]} setEditing={b => setNoting(x => ({ ...x, [id]: b }))}
      onSave={v => setNotes(x => ({ ...x, [id]: v }))} hint="Why you decided as you did. It goes into the audit trail beside the decision." />
  )
  const decide = (id: string, buttons: ReactNode, state: ReactNode) => (
    <>
      <div className="pn-decide">{buttons}{state && <span className="pn-state">{state}</span>}{!(notes[id] ?? '').trim() && !noting[id] && noteFor(id)}</div>
      {((notes[id] ?? '').trim() || noting[id]) && noteFor(id)}
    </>
  )
  const conf = (l: any) => typeof l.confidence === 'number'
    ? <span className="pn-conf">{Math.round(l.confidence * 100)}% confident</span>
    : <span className="pn-conf none">No confidence given</span>
  const lows = byCode ? [...lowConf].sort((a, b) => a.code.localeCompare(b.code)
    || (a.confidence ?? -1) - (b.confidence ?? -1)) : lowConf

  const promoted = emergent.filter(e => decisions[e.id] === 'keep'), discarded = emergent.filter(e => decisions[e.id] === 'delete')
  const undecided = emergent.filter(e => !decisions[e.id])
  const keptNotes = lowConf.filter(l => !deletions.has(l.excerpt_id) && (notes[l.excerpt_id] ?? '').trim())
  const list = [
    ...promoted.map(e => `Promote “${e.name}” to the framework`), ...discarded.map(e => `Discard “${e.name}”`),
    ...lowConf.filter(l => deletions.has(l.excerpt_id)).map(l => `Remove “${l.quote.slice(0, 48)}${l.quote.length > 48 ? '…' : ''}” from ${l.code}`),
    ...keptNotes.map(l => `Keep “${l.quote.slice(0, 40)}…”, with a note`),
  ]
  const approve = () => submit({
    excerpt_deletions: Array.from(deletions),
    decisions: emergent.map(e => ({ id: e.id, action: decisions[e.id] ?? 'delete',
      ...((notes[e.id] ?? '').trim() ? { notes: notes[e.id].trim() } : {}) })),
    excerpt_notes: Object.fromEntries(lowConf.filter(l => (notes[l.excerpt_id] ?? '').trim()).map(l => [l.excerpt_id, notes[l.excerpt_id].trim()])),
  })

  const total = cp.payload.assignments_total
  const main = (
    <>
      {emergent.length > 0 && (
        <div className="pn-sec"><h3>{plural(emergent.length, 'candidate code')} outside the framework</h3>
          <p className="pn-lede">The coder found these passages important, but they fit no framework code. It grouped them under a proposed code. A promoted code is charted across every source and gets a column in the matrix.</p>
          {emergent.map(e => {
            const d = decisions[e.id]
            const state = d === 'keep' ? 'It will join the framework and be charted across every source.'
              : d === 'delete' ? 'It will be discarded, with its passages’ coding.'
              : <span className="pending">It is not decided. If you leave it, it is discarded.</span>
            return (
              <div key={e.id} className="rv-row rv-row-wide"><div>
                <div className="rv-head"><h3 className="rv-name">{e.name}</h3><span className="rv-count">{plural(e.excerpt_count ?? 0, 'passage')}</span></div>
                <p className="rv-def">{e.definition}</p>
                {(e.sample_excerpts ?? []).map((x: any, i: number) => (
                  <Quote key={x.id ?? i} text={x.quote} cite={<>{x.source}{x.source_id && <> · {docLink(runId, x.source_id, x.id)}</>}</>} />
                ))}
                {decide(e.id, (
                  <span className="pn-choice" role="group" aria-label={`Decision for ${e.name}`}>
                    <button aria-pressed={d === 'keep'} onClick={() => setDecisions(x => d === 'keep' ? without(x, e.id) : { ...x, [e.id]: 'keep' })}>Promote to the framework</button>
                    <button aria-pressed={d === 'delete'} onClick={() => setDecisions(x => d === 'delete' ? without(x, e.id) : { ...x, [e.id]: 'delete' })}>Discard</button>
                  </span>), state)}
              </div></div>
            )
          })}
        </div>
      )}
      {lowConf.length > 0 && (
        <div className="pn-sec"><h3>Assignments below 60% confidence</h3>
          <p className="pn-lede">
            {cp.payload.low_confidence_total > lowConf.length
              ? `These are the ${lowConf.length} weakest of the ${cp.payload.low_confidence_total} assignments below the threshold`
              : `These are all ${plural(lowConf.length, 'assignment')} below the threshold`}
            {typeof total === 'number' ? `, out of ${plural(total, 'assignment')} in all` : ''}. Judge each passage against its code’s definition.
            {' '}Assignments that came back without a confidence rating are listed first. The rest are accepted when you approve. Read a sample of them in the coded-source reader.</p>
          {framework.length > 0 && (
            <div className="rv-seg" role="group" aria-label="Order" style={{ margin: '4px 0' }}>
              <button aria-pressed={byCode} onClick={() => setByCode(true)}>By framework code</button>
              <button aria-pressed={!byCode} onClick={() => setByCode(false)}>Weakest first</button>
            </div>
          )}
          <ul className="rv-list">
            {lows.map((l, i) => {
              const gone = deletions.has(l.excerpt_id), f = fw(l.code)
              let group: ReactNode = null
              if (byCode && (i === 0 || lows[i - 1].code !== l.code)) {
                const nLow = lowConf.filter(x => x.code === l.code).length
                group = <li className="pn-group" key={`g-${l.code}`}><h4>{l.code}</h4>
                  {f && <span className="n">{nLow} of its {plural(f.assignments, 'assignment')} fall below 60%</span>}
                  {f && <p>{f.definition}</p>}</li>
              }
              return [group, (
                <li key={l.excerpt_id} className={`rv-row rv-row-wide${gone ? ' is-removed' : ''}`}><div>
                  {!byCode && <><div className="rv-head"><h3 className="rv-name">{l.code}</h3>{conf(l)}</div>
                    {f && <p className="pn-fwdef"><b>Framework definition:</b> {f.definition}</p>}</>}
                  <Quote text={l.quote} cite={<>
                    {byCode && <>{conf(l)} · </>}{l.source}
                    {l.memo && <> · <button aria-expanded={!!memo[l.excerpt_id]} onClick={() => setMemo(m => ({ ...m, [l.excerpt_id]: !m[l.excerpt_id] }))}>Coder’s reason</button></>}
                    {l.source_id && <> · {docLink(runId, l.source_id, l.excerpt_id)}</>}
                  </>}>
                    {memo[l.excerpt_id] && l.memo && <p className="rv-memo"><b>Coder’s reason:</b> {l.memo}</p>}
                  </Quote>
                  {decide(l.excerpt_id, (
                    <span className="pn-choice" role="group" aria-label="Keep or remove this assignment">
                      <button aria-pressed={!gone} onClick={() => setDeletions(s => { const n = new Set(s); n.delete(l.excerpt_id); return n })}>Keep</button>
                      <button aria-pressed={gone} onClick={() => setDeletions(s => new Set(s).add(l.excerpt_id))}>Remove</button>
                    </span>), gone ? 'It will be removed from this code. The audit trail keeps the quote.' : null)}
                </div></li>)]
            })}
          </ul>
        </div>
      )}
      {emergent.length === 0 && lowConf.length === 0 &&
        <p className="desc">Nothing was flagged. Every assignment was confident and inside the framework.</p>}
    </>
  )
  const nNotes = Object.values(notes).filter(n => n.trim()).length
  return (
    <ReviewLayout main={main}
      evidence={`${framework.length ? `The framework has ${plural(framework.length, 'code')}${typeof total === 'number' ? ` and ${plural(total, 'assignment')}` : ''}. ` : ''}`
        + `${plural(cp.payload.low_confidence_total ?? lowConf.length, 'assignment')} fall below 60% confidence. ${plural(emergent.length, 'candidate')} ${emergent.length === 1 ? 'sits' : 'sit'} outside the framework.`}
      tally={[['Promoted', promoted.length, !promoted.length], ['Discarded', discarded.length, !discarded.length],
              ['Not decided', undecided.length, !undecided.length], ['Assignments removed', deletions.size, !deletions.size],
              ['Assignments kept', lowConf.length - deletions.size, false], ['With a note', nNotes, !nNotes]]}
      decisions={list} busy={busy} onApprove={approve}
      approveLabel={list.length ? `Approve ${plural(list.length, 'decision')} and continue` : 'Approve as proposed and continue'}
      fine={undecided.length ? `${undecided.length === 1 ? 'One candidate is' : `${undecided.length} candidates are`} not decided and will be discarded.` : undefined}
      habits={<>
        <li>Judge each weak assignment against its code’s definition, not its name.</li>
        <li>Look at every candidate. One left undecided is discarded.</li>
        <li>The confident assignments are accepted unseen. Read a sample of them in the coded-source reader.</li>
      </>} />
  )
}

// ---------------------------------------------------------------- the extraction table (literature synthesis)

function ExtractionReview({ runId, cp, onError, onResolved }: PanelProps) {
  const rows: any[] = cp.payload.rows ?? []
  const F: string[] = cp.payload.fields ?? []
  const FL: Record<string, string> = cp.payload.field_labels ?? {}
  const { stored, save, clear } = useStored(cp)
  const [edits, setEdits] = useState<Record<string, Record<string, string>>>(stored.edits ?? {})
  const [excluded, setExcluded] = useState<Record<string, boolean>>(stored.excluded ?? {})
  const [notes, setNotes] = useState<Record<string, string>>(stored.notes ?? {})
  const [imported, setImported] = useState<Imported | null>(stored.imported ?? null)
  const [open, setOpen] = useState<string>(rows.length === 1 ? rows[0].source_id : '')
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [excluding, setExcluding] = useState<string | null>(null)
  const [noting, setNoting] = useState<Record<string, boolean>>({})
  const [quotes, setQuotes] = useState<Record<string, Record<string, any[]> | 'loading'>>({})
  const [allOf, setAllOf] = useState<Record<string, boolean>>({})
  const [sort, setSort] = useState<'listed' | 'thin' | 'unloc'>('listed')
  const [onlyBare, setOnlyBare] = useState(false)
  const [search, setSearch] = useState('')
  const { busy, submit } = useSubmit(runId, cp, onError, () => { clear(); onResolved() })
  useEffect(() => { save({ edits, excluded, notes, imported }) },
    [edits, excluded, notes, imported])  // eslint-disable-line react-hooks/exhaustive-deps

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
  const staged = Object.keys(edits).length + Object.keys(excluded).length > 0
  const sheet = useSheet(runId, cp, staged, imported, loadSheet, onError)

  const original = (r: any, k: string): string =>
    k === 'label' ? (r.label ?? '') : k === 'citation' ? (r.citation ?? '') : k === 'cited_work' ? (r.cited_work ?? '') : (r.fields?.[k] ?? '')
  const current = (r: any, k: string): string => edits[r.source_id]?.[k] ?? original(r, k)
  const isOut = (r: any): boolean => excluded[r.source_id] ?? !!r.excluded
  // a blanked label is not an edit: the backend refuses blank labels and keeps the old one
  const isEdit = (r: any, k: string) => { const v = current(r, k); if (k === 'label' && !v.trim()) return false; return v !== original(r, k) }
  const KEYS = ['label', 'citation', 'cited_work', ...F]
  const edited = (r: any) => KEYS.some(k => isEdit(r, k))
  const nr = (v: string) => !v.trim() || /^not reported/i.test(v.trim())
  const count = (r: any, k: string) => r.quote_counts?.[k] ?? 0
  const bare = (r: any, k: string) => !nr(current(r, k)) && count(r, k) === 0
  const nBare = (r: any) => F.filter(k => bare(r, k)).length
  const totalBare = rows.reduce((n, r) => n + nBare(r), 0)
  const nQuotes = (r: any) => F.reduce((n, k) => n + count(r, k), 0)

  const openPaper = async (sid: string) => {
    const next = open === sid ? '' : sid
    setOpen(next); setEditing(null); setExcluding(null)
    if (next && !quotes[sid]) {
      setQuotes(q => ({ ...q, [sid]: 'loading' }))
      try { const r = await api.extractionQuotes(runId, sid); setQuotes(q => ({ ...q, [sid]: r.fields })) }
      catch (e: any) { setQuotes(q => without(q, sid)); onError(String(e.message ?? e)) }
    }
  }

  const done = () => {
    if (rows.length && rows.every(isOut)) {
      onError('Every paper is excluded, so re-include at least one paper before approving, or cancel the run.')
      return
    }
    const out: any[] = []
    for (const r of rows) {
      const patch: Record<string, unknown> = {}
      // only submit REAL edits: a typed-then-reverted value is not an edit
      for (const k of KEYS) if (isEdit(r, k)) patch[k] = current(r, k)
      if (isOut(r) !== !!r.excluded) patch.exclude = isOut(r)
      if (notes[r.source_id]?.trim()) patch.notes = notes[r.source_id].trim()
      if (Object.keys(patch).length) out.push({ source_id: r.source_id, ...patch })
    }
    submit({ rows: out, stage: cp.payload.stage, ...(imported ? { imported_from: imported.imported_from } : {}) })
  }

  const q = search.trim().toLowerCase()
  let shown = rows.map((r, i) => ({ r, i })).filter(({ r }) => !q || current(r, 'label').toLowerCase().includes(q) || current(r, 'citation').toLowerCase().includes(q))
  if (onlyBare) shown = shown.filter(({ r }) => nBare(r) > 0)
  shown.sort((a, b) => sort === 'thin' ? nQuotes(a.r) - nQuotes(b.r) || a.i - b.i
    : sort === 'unloc' ? (b.r.unlocated_quotes ?? 0) - (a.r.unlocated_quotes ?? 0) || a.i - b.i : a.i - b.i)

  const field = (r: any, k: string, label: string) => {
    const key = `${r.source_id}:${k}`, v = current(r, k)
    const qs: any[] = (quotes[r.source_id] && quotes[r.source_id] !== 'loading' ? (quotes[r.source_id] as any)[k] : null) ?? []
    const isField = F.includes(k)
    const off = isOut(r)
    if (editing === key) return (
      <><dt>{label}</dt><dd><div className="rv-edit" style={{ margin: 0 }}>
        <GrowingText value={draft} label={label} autoFocus onChange={setDraft} />
        <div className="row">
          <button className="small primary" onClick={() => {
            if (!(k === 'label' && !draft.trim()))     // a blank label keeps the old one, as the backend does
              setEdits(e => ({ ...e, [r.source_id]: { ...e[r.source_id], [k]: draft } }))
            setEditing(null)
          }}>Done</button>
          <button className="small" onClick={() => setEditing(null)}>Cancel</button>
          {k === 'label' && <span className="rv-hint">The narrative and the matrix cite the paper by this label.</span>}
        </div></div></dd></>
    )
    const n = count(r, k)
    return (
      <><dt>{label}{isField && <><br /><span className="pn-n">{n ? plural(n, 'quote') : 'no quote'}</span></>}</dt>
        <dd>
          <p className={nr(v) && (isField || k === 'cited_work') ? 'nr' : ''}>{v || '—'}</p>
          {isEdit(r, k) && <p className="pn-edited">You edited this · was “{original(r, k).slice(0, 140)}{original(r, k).length > 140 ? '…' : ''}” ·{' '}
            <button onClick={() => setEdits(e => ({ ...e, [r.source_id]: without(e[r.source_id] ?? {}, k) }))}>Undo</button></p>}
          {isField && bare(r, k) && <p className="bare-note">No quote in the paper supports this summary.</p>}
          {isField && quotes[r.source_id] === 'loading' && n > 0 && <p className="rv-def muted">Loading quotes…</p>}
          {isField && (allOf[key] ? qs : qs.slice(0, 2)).map(x => <Quote key={x.id} text={x.quote} cite={x.why ? <i>{x.why}</i> : undefined} />)}
          {isField && qs.length > 2 && <p className="rv-more"><button className="rv-link" onClick={() => setAllOf(a => ({ ...a, [key]: !a[key] }))}>
            {allOf[key] ? 'Show the first two' : `Show all ${qs.length} quotes`}</button></p>}
          {!off && <div className="rv-actions"><button className="rv-act" onClick={() => { setDraft(v); setEditing(key) }}>Edit</button></div>}
        </dd></>
    )
  }

  const detail = (r: any) => {
    const off = isOut(r), sid = r.source_id
    const note = <Note value={notes[sid] ?? ''} editing={!!noting[sid]} setEditing={b => setNoting(x => ({ ...x, [sid]: b }))}
      onSave={v => setNotes(x => ({ ...x, [sid]: v }))} hint="Why you edited or excluded this paper. It goes into the audit trail." />
    return (
      <div className="ex-detail">
        <dl>
          {field(r, 'label', 'Label')}
          {field(r, 'citation', 'Citation')}
          {F.map(k => <Fragment key={k}>{field(r, k, FL[k] ?? k)}</Fragment>)}
          {r.cited_work !== undefined && field(r, 'cited_work', 'Cited work')}
          {(r.unlocated_quotes ?? 0) > 0 && <><dt>Not located</dt><dd><p className="nr">{plural(r.unlocated_quotes, 'quote')} could not be found in the paper, and they never ground the synthesis.</p></dd></>}
        </dl>
        {excluding === sid ? (
          <div className="rv-edit">
            <label>Why exclude this paper?<span className="rv-hint">Your reason is recorded with the exclusion. A synthesis should account for what it leaves out.</span>
              <GrowingText value={draft} label="Why exclude this paper?" autoFocus onChange={setDraft} /></label>
            <div className="row">
              <button className="small primary" onClick={() => {
                if (rows.filter(x => !isOut(x)).length <= 1) { onError('A synthesis needs at least one paper. This one cannot be excluded.'); return }
                setExcluded(x => ({ ...x, [sid]: true }))
                if (draft.trim()) setNotes(x => ({ ...x, [sid]: draft.trim() }))
                setExcluding(null)
              }}>Exclude from the synthesis</button>
              <button className="small" onClick={() => setExcluding(null)}>Cancel</button>
            </div>
          </div>
        ) : off ? (
          <>
            <p className="rv-decision"><b>This paper is excluded from the synthesis.</b> Its extraction stays in the report’s appendix.</p>
            <div className="rv-actions"><button className="rv-act" onClick={() => setExcluded(x => ({ ...x, [sid]: false }))}>Re-include</button></div>
          </>
        ) : (
          <div className="rv-actions">
            <Link to={`/runs/${runId}/sources/${sid}`} target="_blank" rel="noopener" className="rv-act-link"
              title="Open the paper with every extraction quote highlighted">Open the coded paper ↗</Link>
            <button className="rv-act del" onClick={() => { setDraft(notes[sid] ?? ''); setExcluding(sid) }}>Exclude from the synthesis…</button>
          </div>
        )}
        {note}
      </div>
    )
  }

  const nEdited = rows.filter(edited).length, nOut = rows.filter(isOut).length
  const noted = rows.filter(r => (notes[r.source_id] ?? '').trim())
  const list = [
    ...rows.filter(edited).map(r => `Correct ${original(r, 'label') || r.filename} (${KEYS.filter(k => isEdit(r, k)).map(k => k === 'label' || k === 'citation' ? k : k === 'cited_work' ? 'cited work' : (FL[k] ?? k).toLowerCase()).join(', ')})`),
    ...rows.filter(r => isOut(r) !== !!r.excluded).map(r => `${isOut(r) ? 'Exclude' : 'Re-include'} ${original(r, 'label') || r.filename}`),
    ...noted.filter(r => !edited(r) && isOut(r) === !!r.excluded).map(r => `A note on ${original(r, 'label') || r.filename}`),
  ]
  const totQ = rows.reduce((n, r) => n + nQuotes(r), 0), totU = rows.reduce((n, r) => n + (r.unlocated_quotes ?? 0), 0)
  const main = (
    <>
      <div className="rv-toolbar">
        <input type="search" placeholder={`Search ${plural(rows.length, 'paper')}`} aria-label="Search papers" value={search} onChange={e => setSearch(e.target.value)} />
        <div className="rv-seg" role="group" aria-label="Order">
          {([['listed', 'As listed'], ['thin', 'Fewest quotes'], ['unloc', 'Most not located']] as const).map(([v, l]) => (
            <button key={v} aria-pressed={sort === v} onClick={() => setSort(v)}>{l}</button>))}
        </div>
        <span className="rv-shown">{shown.length === rows.length ? plural(rows.length, 'paper') : `${shown.length} of ${rows.length} papers`}
          {onlyBare && <> · <button className="rv-link rv-view" onClick={() => setOnlyBare(false)}>Show all</button></>}</span>
      </div>
      {sheet.summary}
      <div className="ex" role="table" aria-label="The extraction table">
        <div className="ex-head" role="row"><span role="columnheader">Paper</span>{F.map(k => <span key={k} role="columnheader">{FL[k] ?? k}</span>)}<span role="columnheader">Not located</span></div>
        {shown.map(({ r }, idx) => {
          const sid = r.source_id, flags = [edited(r) && 'Edited', isOut(r) && 'Excluded from synthesis'].filter(Boolean)
          return (
            <div key={sid} className={`ex-paper${open === sid ? ' is-open' : ''}${isOut(r) ? ' is-excluded' : ''}`} role="row">
              <div className="ex-line" role="button" tabIndex={0} aria-expanded={open === sid}
                onClick={() => openPaper(sid)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPaper(sid) } }}>
                <div><span className="lab">{current(r, 'label') || r.filename}</span>
                  <span className="cit" title={current(r, 'citation')}>{current(r, 'citation') || r.filename}</span>
                  {flags.length > 0 && <span className="flag">{flags.join(' · ')}</span>}
                  {(notes[sid] ?? '').trim() && <span className="flag">Note: {notes[sid]}</span>}
                </div>
                {F.map(k => nr(current(r, k))
                  ? <span key={k} className="c nr" data-f={FL[k] ?? k} title={`${FL[k] ?? k}: not reported`}>—</span>
                  : bare(r, k) ? <span key={k} className="c bare" data-f={FL[k] ?? k} title={`${FL[k] ?? k}: a summary with no quote behind it`}>0</span>
                  : <span key={k} className="c" data-f={FL[k] ?? k} title={`${FL[k] ?? k}: ${plural(count(r, k), 'quote')}`}>{count(r, k)}</span>)}
                <span className="c un uncol" data-f="Not located" title="Quotes not found in the paper">{r.unlocated_quotes || '—'}</span>
              </div>
              {open === sid && detail(r)}
              {/* an open paper can be a screen long, so the papers after it get the
                  column names again where they are read */}
              {open === sid && idx < shown.length - 1 && (
                <div className="ex-head ex-head-again" aria-hidden="true"><span>Paper</span>{F.map(k => <span key={k}>{FL[k] ?? k}</span>)}<span>Not located</span></div>
              )}
            </div>
          )
        })}
        {shown.length === 0 && <p className="rv-def" style={{ padding: '14px 0' }}>No paper matches.</p>}
      </div>
      <p className="ex-key">Each number counts the quotes located in the paper for a field. A dash (<span className="nr-key">—</span>) marks a field the paper does not report. An amber <span className="bare">0</span> marks a summary with no quote behind it. Select a paper to read and correct it.</p>
    </>
  )
  return (
    <ReviewLayout main={main}
      evidence={`The ${plural(rows.length, 'paper')} have ${plural(totQ, 'quote')} located in their text. Another ${totU.toLocaleString('en-US')} could not be located, and those never ground the synthesis.`}
      tally={[['Papers corrected', nEdited, !nEdited], ['Excluded', nOut, !nOut], ['With a note', noted.length, !noted.length],
              ['Unchanged', rows.filter(r => !edited(r) && !isOut(r) && !(notes[r.source_id] ?? '').trim()).length, false]]}
      decisions={list} busy={busy} onApprove={done}
      approveLabel={list.length ? `Approve ${plural(list.length, 'decision')} and continue` : 'Approve as proposed and continue'}
      habits={<>
        {totalBare > 0
          ? <li>{totalBare === 1 ? 'One summary has' : `${totalBare} summaries have`} no quote behind {totalBare === 1 ? 'it' : 'them'}. Start there. <button className="rv-link" onClick={() => { setOnlyBare(true); setSort('listed') }}>Show those papers</button></li>
          : <li>Every summary has at least one quote behind it. Start with the papers that have the fewest. <button className="rv-link" onClick={() => setSort('thin')}>Fewest quotes</button></li>}
        <li>Check labels and citations. The narrative and the matrix cite papers by their labels.</li>
        <li>Read a summary against its paper before trusting it.</li>
      </>}
      extra={sheet.links} />
  )
}
