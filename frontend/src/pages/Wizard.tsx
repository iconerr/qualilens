// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, statusLabel, testKey, type Meta, type MethodMeta, type Question, type Source } from '../api'

const STEPS = ['Method', 'Method setup', 'Model & keys', 'Data', 'Review & run']

export default function Wizard() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')

  // selections
  const [methodId, setMethodId] = useState('')
  const [name, setName] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [answersByMethod, setAnswersByMethod] = useState<Record<string, Record<string, string>>>({})
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [customModel, setCustomModel] = useState(false)
  const [modelTouched, setModelTouched] = useState(false)
  const [liveCheck, setLiveCheck] = useState<{ missing: string[]; live: string[] } | null>(null)
  const [keyDraft, setKeyDraft] = useState('')
  const [keyStatus, setKeyStatus] = useState<{ ok: boolean; msg: string } | null>(null)
  const [testing, setTesting] = useState(false)

  // data step (project is created on entering it)
  const [projectId, setProjectId] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [grpDraft, setGrpDraft] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const [estimate, setEstimate] = useState<Awaited<ReturnType<typeof api.estimate>> | null>(null)
  const [starting, setStarting] = useState(false)
  const nav = useNavigate()

  useEffect(() => { api.meta().then(setMeta).catch(e => setError(String(e.message ?? e))) }, [])

  const method: MethodMeta | undefined = useMemo(
    () => meta?.methods.find(m => m.id === methodId), [meta, methodId])
  const providerMeta = meta?.providers.find(p => p.id === provider)
  const wantsGroups = methodId === 'content_analysis' &&
    (answers['ca_compare_groups'] ?? 'false') === 'true'
  const hasMedia = sources.some(s => s.kind !== 'text')
  const transcribing = sources.some(s => s.status === 'transcribing')
  const readyCount = sources.filter(s => s.status === 'ready').length

  // With a saved key, verify the catalog against the provider's live model
  // list (free) so the dropdown can flag retired entries and the custom
  // field can autocomplete live ids.
  useEffect(() => {
    setLiveCheck(null)
    if (!provider || !providerMeta?.has_key) return
    let alive = true
    api.checkModels(provider).then(r => {
      const res = r[provider]
      if (alive && res?.ok) setLiveCheck({ missing: res.missing ?? [], live: res.live ?? [] })
    }).catch(() => { /* advisory only — the wizard works without it */ })
    return () => { alive = false }
  }, [provider, providerMeta?.has_key])

  // If the preselected default is absent from the live list and the user has
  // not chosen anything yet, move the selection to the first live catalog
  // model rather than letting the run fail later.
  useEffect(() => {
    if (!liveCheck || modelTouched || customModel || !providerMeta) return
    const current = model || providerMeta.default_model
    if (liveCheck.missing.includes(current)) {
      const alt = providerMeta.models.find(m => !liveCheck.missing.includes(m))
      if (alt) setModel(alt)
    }
  }, [liveCheck, modelTouched, customModel, providerMeta, model])

  // poll while transcription is running
  useEffect(() => {
    if (!projectId || !transcribing) return
    const t = setInterval(async () => {
      const p = await api.project(projectId)
      setSources(p.sources)
    }, 2500)
    return () => clearInterval(t)
  }, [projectId, transcribing])

  const initAnswers = (m: MethodMeta) => {
    const a: Record<string, string> = {}
    m.questions.forEach(q => { a[q.key] = q.default ?? '' })
    setAnswers(a)
  }

  const validateStep = (): string => {
    if (step === 0 && !methodId) return 'Choose a method.'
    if (step === 1) {
      if (!name.trim()) return 'Name the project.'
      for (const q of method?.questions ?? [])
        if (q.required && !String(answers[q.key] ?? '').trim())
          return `"${q.label}" is required.`
    }
    if (step === 2) {
      if (!provider) return 'Choose a provider.'
      if (customModel && !model.trim())
        return 'Enter the custom model id (or pick one from the list).'
      if (!providerMeta?.has_key && !keyDraft.trim())
        return 'Enter an API key for the selected provider.'
    }
    if (step === 3) {
      if (readyCount === 0)
        return 'Add at least one data source (and wait for transcription to finish).'
      if (transcribing)
        return 'Some files are still transcribing — continuing now would silently ' +
               'exclude them. Wait for them to finish or remove them.'
    }
    return ''
  }

  const next = async () => {
    const v = validateStep()
    if (v) { setError(v); return }
    setError('')
    try {
      if (step === 2) {
        if (keyDraft.trim()) {
          await api.saveKeys({ [provider]: keyDraft.trim() })
          setKeyDraft('')
          setMeta(await api.meta())
        }
        const cfg = { ...answers, provider, model: model.trim() || providerMeta?.default_model || '' }
        if (!projectId) {
          const p = await api.createProject(name.trim(), methodId, cfg)
          setProjectId(p.id)
        } else {
          // the user may have gone Back and edited method/answers/provider —
          // the run must use what they last saw, not the original snapshot
          await api.updateProject(projectId, name.trim(), methodId, cfg)
        }
      }
      if (step === 3) setEstimate(await api.estimate(projectId))
      setStep(s => s + 1)
    } catch (e: any) { setError(String(e.message ?? e)) }
  }

  const doTestKey = async () => {
    setTesting(true); setKeyStatus(null)
    try {
      // a pasted key is tested as-is, unsaved — a failing candidate never
      // clobbers a saved working key; Continue is what saves it
      const r = await testKey(provider, model.trim() || providerMeta?.default_model,
        keyDraft.trim() || undefined)
      setKeyStatus(r.ok ? { ok: true, msg: `Key works (model replied: "${r.reply}")` }
                        : { ok: false, msg: r.error ?? 'Failed' })
    } finally { setTesting(false) }
  }

  const upload = async (files: FileList | null) => {
    if (!files || !projectId) return
    setUploading(true); setError('')
    try {
      for (const f of Array.from(files)) {
        const s = await api.uploadSource(projectId, f, wantsGroups ? grpDraft.trim() : '')
        setSources(prev => [...prev, s])
      }
    } catch (e: any) { setError(String(e.message ?? e)) } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const start = async () => {
    setStarting(true); setError('')
    try {
      const { run_id } = await api.startRun(projectId)
      nav(`/runs/${run_id}`)
    } catch (e: any) { setError(String(e.message ?? e)); setStarting(false) }
  }

  if (!meta) return <div className="page">{error ? <div className="error-box">{error}</div> : 'Loading…'}</div>

  return (
    <div className="page">
      <h1>New analysis</h1>
      <p className="sub">Five steps: method, setup, model, data, run.</p>
      <div className="steps">
        {STEPS.map((s, i) => (
          <div key={s} className={`step ${i === step ? 'active' : i < step ? 'done' : ''}`}>
            <span className="step-n">{i < step ? '✓' : i + 1}</span>
            <span className="step-label">{s}</span>
          </div>
        ))}
      </div>
      {error && <div className="error-box">{error}</div>}

      {step === 0 && meta.methods.map(m => (
        <div key={m.id}
          className="card clickable"
          style={methodId === m.id ? { borderColor: 'var(--accent)', background: 'var(--accent-soft)' } : {}}
          onClick={() => {
            if (methodId === m.id) return
            // stash the current method's answers so switching back restores them
            if (methodId) setAnswersByMethod(x => ({ ...x, [methodId]: answers }))
            setMethodId(m.id)
            const stashed = answersByMethod[m.id]
            if (stashed) setAnswers(stashed)
            else initAnswers(m)
          }}>
          <h3>{m.label}</h3>
          <p className="desc">{m.description}</p>
          <p className="desc small">
            Pipeline: {m.stages.map(s => s.label).join(' → ')}
          </p>
        </div>
      ))}

      {step === 1 && method && (
        <div className="card">
          <label className="field">
            <span className="lbl">Project name</span>
            <input type="text" value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g., Clinician interviews, Spring 2026" />
          </label>
          {method.questions.map(q => (
            <QuestionField key={q.key} q={q} value={answers[q.key] ?? ''}
              onChange={v => setAnswers(a => ({ ...a, [q.key]: v }))} />
          ))}
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <label className="field">
            <span className="lbl">Analysis provider</span>
            <select value={provider} onChange={e => { setProvider(e.target.value); setModel(''); setCustomModel(false); setKeyStatus(null) }}>
              <option value="">Choose…</option>
              {meta.providers.map(p => (
                <option key={p.id} value={p.id}>{p.label}{p.has_key ? ' — Ready' : ''}</option>
              ))}
            </select>
          </label>
          {providerMeta && (
            <>
              <label className="field">
                <span className="lbl">Model</span>
                <select value={customModel ? '__custom__' : (model || providerMeta.default_model)}
                  onChange={e => {
                    setModelTouched(true)
                    if (e.target.value === '__custom__') { setCustomModel(true); setModel('') }
                    else { setCustomModel(false); setModel(e.target.value) }
                  }}>
                  {providerMeta.models.map(m => {
                    const retired = liveCheck?.missing.includes(m)
                    return (
                      <option key={m} value={m} disabled={retired}>
                        {m}{retired ? ' — not offered by the provider (retired?)' : ''}
                      </option>
                    )
                  })}
                  <option value="__custom__">Custom model id…</option>
                </select>
                {customModel && (
                  <>
                    <input type="text" value={model} style={{ marginTop: 6 }}
                      list="ql-live-models"
                      onChange={e => { setModelTouched(true); setModel(e.target.value) }}
                      placeholder={liveCheck
                        ? `exact model id — autocompletes across ${liveCheck.live.length} live models`
                        : 'exact model id as the provider names it'} />
                    <datalist id="ql-live-models">
                      {(liveCheck?.live ?? []).map(m => <option key={m} value={m} />)}
                    </datalist>
                  </>
                )}
                {liveCheck && liveCheck.missing.length > 0 && (
                  <span className="hint" style={{ color: 'var(--amber)' }}>
                    Verified against the provider just now: {liveCheck.missing.join(', ')}{' '}
                    {liveCheck.missing.length === 1 ? 'is' : 'are'} no longer offered and
                    {' '}{liveCheck.missing.length === 1 ? 'has' : 'have'} been disabled above.
                  </span>
                )}
                {liveCheck && liveCheck.missing.length === 0 && (
                  <span className="hint" style={{ color: 'var(--green)' }}>
                    ✓ All listed models verified against the provider just now.
                  </span>
                )}
                <span className="hint">The model that will perform coding and synthesis.
                  {' '}If a listed model has been retired by the provider, Settings → Check
                  models will say so; a custom id works immediately.</span>
              </label>
              <label className="field">
                <span className="lbl">API key {providerMeta.has_key && <span className="muted">(saved — leave blank to keep)</span>}</span>
                <input type="password" value={keyDraft} onChange={e => setKeyDraft(e.target.value)}
                  placeholder={providerMeta.has_key ? '••••••••  (already saved)' : 'Paste your API key'} />
                <span className="hint">Stored in plain text in this app's local database and sent only to {providerMeta.label}.
                  {' '}If the data folder is inside a cloud-synced directory, the sync service holds it too — Settings says where it lives.</span>
              </label>
              <div className="row">
                <button onClick={doTestKey} disabled={testing}>{testing ? 'Testing…' : 'Test key'}</button>
                {keyStatus && (
                  <span className={keyStatus.ok ? 'badge completed' : 'badge failed'}>{keyStatus.msg}</span>
                )}
              </div>
            </>
          )}
          <div className="info-box mt">
            Audio or video files are transcribed with OpenAI Whisper, which requires an OpenAI key
            even if a different provider does the analysis. Manage keys any time in Settings.
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="card">
          <p className="desc">Audio and video are transcribed
            automatically{meta.ffmpeg ? '' : ' — but ffmpeg was not found, so video cannot be processed'}.
            Transcription does not label speakers; if speaker identity matters, upload
            formatted transcripts instead.</p>
          {wantsGroups && (
            <label className="field">
              <span className="lbl">Group label for the next upload(s)</span>
              <input type="text" value={grpDraft} onChange={e => setGrpDraft(e.target.value)}
                placeholder="e.g., Site A" />
              <span className="hint">You chose to compare groups: set this before each upload batch.</span>
            </label>
          )}
          <Dropzone busy={uploading} onFiles={upload} inputRef={fileRef} />
          <div className="mt">
            {sources.map(s => (
              <div key={s.id} className="src-row">
                <span className="src-icon"><KindIcon kind={s.kind} /></span>
                <span>
                  <div className="src-name">{s.filename} {s.grp ? <span className="count-pill">{s.grp}</span> : null}</div>
                  <div className="src-meta">
                    {s.kind}{s.status === 'ready' && s.chars > 0 ? ` · ${(s.chars / 1000).toFixed(s.chars < 10000 ? 1 : 0)}k characters` : ''}
                  </div>
                </span>
                <span className="src-actions">
                  <span className={`badge ${s.status}`}>{statusLabel(s.status)}</span>
                  {s.status === 'error' && <button className="small" onClick={async () => {
                    await api.retrySource(s.id); setSources(await (await api.project(projectId)).sources)
                  }}>Retry</button>}
                  <button className="small danger" onClick={async () => {
                    await api.deleteSource(s.id); setSources(prev => prev.filter(x => x.id !== s.id))
                  }}>Remove</button>
                </span>
              </div>
            ))}
            {sources.some(s => s.status === 'error') && (
              <div className="warn-box">Some files failed. Hover the badge or retry; transcription errors
                usually mean the OpenAI key is missing (Settings) or the file is unreadable.</div>
            )}
            {transcribing && <div className="info-box">Transcribing… this can take a few minutes for long recordings.</div>}
          </div>
        </div>
      )}

      {step === 4 && estimate && method && (
        <div className="card">
          <h3>Ready to run: {name}</h3>
          <p className="desc">{method.label} · {provider}/{model || providerMeta?.default_model} · {estimate.n_sources} sources
            ({Math.round(estimate.total_chars / 1000)}k characters)</p>
          <div className="info-box">
            Estimated cost: <b>${estimate.est_cost_usd}</b> (~{Math.round(estimate.est_input_tokens / 1000)}k input /
            {' '}~{Math.round(estimate.est_output_tokens / 1000)}k output tokens). {estimate.note}
          </div>
          <p className="desc">The pipeline pauses at review checkpoints:
            {' '}{method.stages.filter(s => s.kind === 'checkpoint').map(s => s.label).join(', ') || 'none'}.
            You can close the browser during long stages — the run continues and its state is saved.</p>
          {hasMedia && <p className="desc">Transcripts generated from audio/video are kept with the project.</p>}
          <button className="primary" onClick={start} disabled={starting}>
            {starting ? 'Starting…' : 'Run analysis'}
          </button>
        </div>
      )}

      <div className="row spread mt">
        <button onClick={() => { setError(''); setStep(s => Math.max(0, s - 1)) }} disabled={step === 0}>Back</button>
        {step < 4 && <button className="primary" onClick={next}>Continue</button>}
      </div>
    </div>
  )
}

function Dropzone({ busy, onFiles, inputRef }: {
  busy: boolean; onFiles: (f: FileList | null) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const [drag, setDrag] = useState(false)
  return (
    <div className={`dropzone ${drag ? 'drag' : ''} ${busy ? 'busy' : ''}`}
      role="button" tabIndex={0} aria-label="Add data files"
      onClick={() => inputRef.current?.click()}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); onFiles(e.dataTransfer.files) }}>
      <div className="dz-icon">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 16V5" /><path d="m7 9 5-4.5L17 9" />
          <path d="M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15" />
        </svg>
      </div>
      <div className="dz-title">
        {busy ? 'Uploading…' : <>Drop your data here, or <u>browse</u></>}
      </div>
      <div className="dz-sub">Transcripts, documents, audio, or video — several at once is fine</div>
      <div className="fmt-chips">
        {['.txt', '.md', '.docx', '.pdf', '.mp3', '.m4a', '.wav', '.flac', '.ogg', '.webm', '.aac',
          '.mp4', '.mov', '.avi', '.mkv'].map(f =>
          <span key={f}>{f}</span>)}
      </div>
      <input ref={inputRef} type="file" multiple style={{ display: 'none' }}
        onChange={e => onFiles(e.target.files)} />
    </div>
  )
}

function KindIcon({ kind }: { kind: string }) {
  const common = { width: 17, height: 17, viewBox: '0 0 24 24', fill: 'none' as const,
    stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const }
  if (kind === 'audio') return (
    <svg {...common} aria-hidden="true">
      <path d="M4 12v2M8 9v8M12 5v14M16 8v9M20 11v4" />
    </svg>
  )
  if (kind === 'video') return (
    <svg {...common} aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2.5" />
      <path d="m10 9.5 5 2.5-5 2.5z" fill="currentColor" stroke="none" />
    </svg>
  )
  return (
    <svg {...common} aria-hidden="true">
      <path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4" />
      <path d="M9 12h6M9 16h6" />
    </svg>
  )
}

function QuestionField({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  return (
    <label className="field">
      <span className="lbl">{q.label}{q.required ? ' *' : ''}</span>
      {q.type === 'textarea' && <textarea value={value} onChange={e => onChange(e.target.value)} />}
      {q.type === 'text' && <input type="text" value={value} onChange={e => onChange(e.target.value)} />}
      {q.type === 'select' && (
        <select value={value} onChange={e => onChange(e.target.value)}>
          {q.options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      )}
      {q.type === 'toggle' && (
        <select value={value} onChange={e => onChange(e.target.value)}>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      )}
      {q.help && <span className="hint">{q.help}</span>}
    </label>
  )
}
