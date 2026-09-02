// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, type CodedSource, type CodedSpan } from '../api'

/**
 * The coded-source reader: a transcript with every coded span highlighted
 * inline, a code legend for filtering and span-to-span navigation, and a
 * minimap showing where coding falls (and thins out) across the document.
 */

interface Segment { start: number; end: number; spans: CodedSpan[] }

function segment(textLen: number, spans: CodedSpan[]): Segment[] {
  const bounds = new Set<number>([0, textLen])
  for (const s of spans) { bounds.add(s.start); bounds.add(s.end) }
  const pts = [...bounds].sort((a, b) => a - b)
  const segs: Segment[] = []
  for (let i = 0; i < pts.length - 1; i++) {
    const [a, b] = [pts[i], pts[i + 1]]
    segs.push({ start: a, end: b, spans: spans.filter(s => s.start <= a && s.end >= b) })
  }
  return segs
}

export default function SourceReader() {
  const { runId, sourceId } = useParams<{ runId: string; sourceId: string }>()
  const [params] = useSearchParams()
  const focusExcerpt = params.get('ex')
  const [data, setData] = useState<CodedSource | null>(null)
  const [error, setError] = useState('')
  const [codeFilter, setCodeFilter] = useState('')     // code id or ''
  const [navIndex, setNavIndex] = useState(0)          // span index within filter
  const [inspect, setInspect] = useState<CodedSpan[] | null>(null)
  const textRef = useRef<HTMLDivElement>(null)
  const didFocus = useRef(false)

  useEffect(() => {
    api.codedSource(runId!, sourceId!).then(setData)
      .catch(e => setError(String(e.message ?? e)))
  }, [runId, sourceId])

  const filteredSpans = useMemo(() => {
    if (!data) return []
    const all = codeFilter ? data.spans.filter(s => s.code_id === codeFilter) : data.spans
    return [...all].sort((a, b) => a.start - b.start)
  }, [data, codeFilter])

  const segs = useMemo(
    () => data ? segment(data.text.length, data.spans) : [],
    [data])

  const coveredChars = useMemo(() => {
    let n = 0
    for (const s of segs) if (s.spans.length) n += s.end - s.start
    return n
  }, [segs])

  // one-time scroll to the excerpt named in ?ex=
  const [notice, setNotice] = useState('')
  useEffect(() => {
    if (!data || !focusExcerpt || didFocus.current) return
    didFocus.current = true
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-ex~="${CSS.escape(focusExcerpt)}"]`)
      if (el) {
        el.scrollIntoView({ block: 'center' })
        el.classList.add('flash')
        setTimeout(() => el.classList.remove('flash'), 3200)
      } else if (data.unlocated.some(u => u.excerpt_id === focusExcerpt)) {
        setNotice('The linked excerpt could not be located at an exact position in '
          + 'this text (the model likely paraphrased its quote) — it is listed under '
          + '“Not located” in the side panel.')
      }
    })
  }, [data, focusExcerpt])

  const scrollToSpan = (span: CodedSpan) => {
    const el = document.querySelector(`[data-ex~="${CSS.escape(span.excerpt_id)}"]`)
    el?.scrollIntoView({ block: 'center' })
    el?.classList.add('flash')
    setTimeout(() => el?.classList.remove('flash'), 3200)
  }

  const nav = (dir: 1 | -1) => {
    if (!filteredSpans.length) return
    const next = (navIndex + dir + filteredSpans.length) % filteredSpans.length
    setNavIndex(next)
    scrollToSpan(filteredSpans[next])
  }

  const pickCode = (id: string) => {
    const meta = data?.codes.find(c => c.id === id)
    if (meta && meta.count === 0) {
      setNotice(`“${meta.name}” has ${meta.unlocated_count} excerpt(s), but none could `
        + 'be located at an exact position in this text — see the “Not located” list.')
      return
    }
    setNotice('')
    const nextFilter = codeFilter === id ? '' : id
    setCodeFilter(nextFilter)
    setNavIndex(0)
    if (nextFilter && data) {
      const first = data.spans.filter(s => s.code_id === nextFilter)
        .sort((a, b) => a.start - b.start)[0]
      if (first) scrollToSpan(first)
    }
  }

  if (error) return (
    <div className="page">
      <div className="error-box">{error}</div>
      <button onClick={() => history.back()}>← Back</button>
    </div>
  )
  if (!data) return <div className="page">Loading coded document…</div>

  const pct = data.text.length ? Math.round(100 * coveredChars / data.text.length) : 0

  return (
    <div className="page page-wide">
      <div className="row spread" style={{ marginBottom: 14 }}>
        <div>
          <h1 style={{ fontSize: 20 }}>{data.filename}</h1>
          <p className="sub" style={{ marginBottom: 0 }}>
            <Link to={`/runs/${runId}`}>← run</Link>
            {' · '}{data.spans.length} coded span{data.spans.length === 1 ? '' : 's'}
            {' · '}{data.codes.length} code{data.codes.length === 1 ? '' : 's'}
            {' · '}{pct}% of text coded
            {(data.pages ?? []).length > 0 && (() => {
              // the page map holds text-bearing pages; the last entry's
              // original page number is the closest honest page count
              const last = data.pages![data.pages!.length - 1].page
              return <>{' · '}PDF, {last} page{last === 1 ? '' : 's'}</>
            })()}
          </p>
        </div>
      </div>

      {notice && <div className="warn-box">{notice}</div>}

      <div className="reader-layout">
        <Minimap textLen={data.text.length} spans={data.spans}
          selected={codeFilter} onJump={scrollToSpan} />

        <div className="reader-text" ref={textRef}>
          {segs.map((s, i) => {
            const piece = data.text.slice(s.start, s.end)
            if (!s.spans.length) return <span key={i}>{piece}</span>
            const depth = s.spans.length > 1 ? 'd2' : 'd1'
            const cls = codeFilter
              ? (s.spans.some(x => x.code_id === codeFilter) ? 'sel' : 'dim')
              : depth
            return (
              <mark key={i} className={`${cls} clickable`}
                data-ex={s.spans.map(x => x.excerpt_id).join(' ')}
                title={s.spans.map(x => x.code_name).join(' · ')}
                onClick={() => setInspect(s.spans)}>
                {piece}
              </mark>
            )
          })}
        </div>

        <div className="reader-side">
          <div className="card" style={{ padding: '14px 16px' }}>
            <h3 style={{ fontSize: 14 }}>Codes in this document</h3>
            <div className="coverage-bar"><div style={{ width: `${pct}%` }} /></div>
            <p className="desc small" style={{ marginBottom: 8 }}>
              Click a code to isolate its spans; use ‹ › to step through them.
              Uncoded stretches are as informative as coded ones.
            </p>
            {codeFilter && (
              <div className="row" style={{ marginBottom: 8 }}>
                <button className="small" onClick={() => nav(-1)}>‹ prev</button>
                <span className="small muted">
                  {filteredSpans.length ? navIndex + 1 : 0}/{filteredSpans.length}
                </span>
                <button className="small" onClick={() => nav(1)}>next ›</button>
                <button className="small" onClick={() => pickCode(codeFilter)}>Show all</button>
              </div>
            )}
            {data.codes.map(c => (
              <div key={c.id}
                className={`legend-item ${codeFilter === c.id ? 'active' : ''}`}
                onClick={() => pickCode(c.id)}>
                <span>
                  {c.name}
                  {c.parent_name && <div className="parent">{c.parent_name}</div>}
                </span>
                <span className="count-pill">
                  {c.count}{c.unlocated_count > 0 && ` +${c.unlocated_count}?`}
                </span>
              </div>
            ))}
            {data.codes.length === 0 && <p className="desc">No coded spans in this document.</p>}
          </div>

          {inspect && (
            <div className="card inspect-box" style={{ padding: '12px 16px' }}>
              <div className="row spread">
                <h3 style={{ fontSize: 14, margin: 0 }}>This passage</h3>
                <button className="small" onClick={() => setInspect(null)}>Close</button>
              </div>
              {inspect.map(s => (
                <div key={s.excerpt_id} style={{ marginTop: 8 }}>
                  <b className="small">{s.code_name}</b>
                  {s.parent_name && <span className="muted small"> · {s.parent_name}</span>}
                  {typeof s.page === 'number' &&
                    <span className="muted small"> · p. {s.page}</span>}
                  {typeof s.confidence === 'number' &&
                    <span className="muted small"> · conf {Math.round(s.confidence * 100)}%</span>}
                  {s.memo && <p className="desc small" style={{ margin: '2px 0 0' }}>{s.memo}</p>}
                </div>
              ))}
            </div>
          )}

          {data.unlocated.length > 0 && (
            <div className="card" style={{ padding: '12px 16px' }}>
              <h3 style={{ fontSize: 14 }}>Not located in the text ({data.unlocated.length})</h3>
              <p className="desc small">These excerpts' quotes could not be matched to an
                exact position (usually the model paraphrased). The report and the Word export
                list them as unverified — never inside quotation marks — and the synthesis
                stage never builds on them. Quote the transcript, not the paraphrase.</p>
              {data.unlocated.map(s => (
                <div key={s.excerpt_id} className="quote">
                  “{s.quote.slice(0, 200)}{s.quote.length > 200 ? '…' : ''}”
                  <div className="src">{s.code_name}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Minimap({ textLen, spans, selected, onJump }:
  { textLen: number; spans: CodedSpan[]; selected: string; onJump: (s: CodedSpan) => void }) {
  if (!textLen) return <div className="minimap" />
  return (
    <div className="minimap" title="Coding coverage — click a mark to jump">
      {spans.map(s => (
        <div key={s.excerpt_id}
          className={`mm-mark ${selected && s.code_id === selected ? 'sel' : ''}`}
          style={{
            top: `${(100 * s.start) / textLen}%`,
            height: `${Math.max(0.4, (100 * (s.end - s.start)) / textLen)}%`,
            opacity: selected && s.code_id !== selected ? 0.25 : undefined,
          }}
          onClick={() => onJump(s)} />
      ))}
    </div>
  )
}
