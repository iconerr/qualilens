// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from 'react'
import { useRef } from 'react'
import { ageLabel, api, testKey, versionLabel, type Meta } from '../api'

// After an update the server stops itself so ./run.sh can relaunch the new
// build. This page has nothing to talk to until then, and when the new server
// comes up it mints a new session token that this page does not hold. So the
// page waits, polls the root URL (which needs no token), and the moment a
// server answers with a different build stamp than the one this page was
// served by, reloads itself — which is exactly what the human would otherwise
// be told to do, and the step that used to strand people on a token error.
const THIS_BUILD = document.querySelector('meta[name="ql-build"]')?.getAttribute('content') ?? ''

function UpdateWaiting({ detail }: { detail: string }) {
  const [secs, setSecs] = useState(0)
  const [sameBuildFor, setSameBuildFor] = useState(0)
  useEffect(() => {
    let alive = true
    const tick = async () => {
      if (!alive) return
      setSecs(s => s + 2)
      try {
        const res = await fetch('/', { cache: 'no-store', credentials: 'same-origin' })
        if (res.ok) {
          const html = await res.text()
          const build = /<meta name="ql-build" content="([^"]*)"/.exec(html)?.[1] ?? ''
          if (build && build !== THIS_BUILD) { window.location.reload(); return }
          setSameBuildFor(t => t + 2)      // a server answered, but not a new build (yet)
        }
      } catch { /* connection refused: the app is between stop and relaunch */ }
    }
    const id = window.setInterval(tick, 2000)
    return () => { alive = false; window.clearInterval(id) }
  }, [])
  const origin = window.location.origin
  return (
    <div className="page" style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '60vh', textAlign: 'center', gap: 16
    }}>
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
        stroke="var(--green)" strokeWidth="1.8" strokeLinecap="round"
        strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" opacity="0.25" />
        <path d="M8 12l3 3 5-6" />
      </svg>
      <h1 style={{ margin: 0 }}>Update installed</h1>
      <p style={{ maxWidth: 460, lineHeight: 1.6, margin: 0 }}>
        QualiLens has stopped so the new build can start. Start it again: in the Terminal
        window where it was running, press <kbd>↑</kbd> then <kbd>Return</kbd> — or open a
        Terminal in the QualiLens folder and run <code>./run.sh</code>.
      </p>
      <p style={{ maxWidth: 460, lineHeight: 1.6, margin: 0 }}>
        <b>This page reconnects on its own</b> once the new build is up; nothing else to do.
      </p>
      <p className="small muted" style={{ margin: 0 }}>
        Waiting for the new build… {secs > 0 && <span className="mono">{secs}s</span>}
      </p>
      {(secs >= 60 || sameBuildFor >= 20) && (
        <div className="warn-box" style={{ maxWidth: 520, textAlign: 'left' }}>
          {sameBuildFor >= 20
            ? <>A server is answering, but it runs the same build as before. If you relaunched
                from a different folder, or the launcher printed that the port is in use,
                stop that server (the launcher prints the command) and run <code>./run.sh</code>
                again in the updated folder.</>
            : <>Not reconnecting yet. If the launcher says the port is already in use, an older
                server is still running — stop it with the command it prints, then run{' '}
                <code>./run.sh</code> again. Once the app says it is running, this page
                reloads; if it does not, open <a href={origin}>{origin}</a> in a new tab.</>}
        </div>
      )}
      <div className="row" style={{ gap: 10 }}>
        <button onClick={() => window.location.reload()}>Reload now</button>
      </div>
      <p className="small muted" style={{ maxWidth: 520, marginTop: 8 }}>{detail}</p>
    </div>
  )
}

export default function Settings() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [saved, setSaved] = useState<Record<string, { has_key: boolean; key_hint: string }>>({})
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [status, setStatus] = useState<Record<string, string>>({})
  const [modelCheck, setModelCheck] = useState<Record<string, any>>({})
  const [error, setError] = useState('')
  const [updState, setUpdState] = useState<{ phase: string; msg: string }>({ phase: 'idle', msg: '' })
  const [check, setCheck] = useState<{ phase: string; msg: string; newer?: boolean;
    releaseUrl?: string }>({ phase: 'idle', msg: '' })
  const updRef = useRef<HTMLInputElement>(null)
  const [editing, setEditing] = useState<string | null>(null)   // the provider row whose key editor is open

  const checkForUpdates = async () => {
    setCheck({ phase: 'busy', msg: 'Asking GitHub for the latest release…' })
    try {
      const r = await api.checkUpdates()
      if (!r.ok) { setCheck({ phase: 'error', msg: r.error ?? 'The check failed.' }); return }
      api.meta().then(setMeta).catch(() => { /* the 'last checked' line refreshes next visit */ })
      if (r.note) { setCheck({ phase: 'done', msg: r.note, releaseUrl: r.release_url }); return }
      if (r.newer && r.has_bundle) {
        setCheck({ phase: 'done', newer: true, releaseUrl: r.release_url,
          msg: `Update available: ${r.tag} (build ${r.build}); you are running ${versionLabel(r.release, r.current)}.` })
      } else if (r.newer) {
        setCheck({ phase: 'done', releaseUrl: r.release_url,
          msg: `A newer release exists (${r.tag}) but carries no installable bundle — see the release page.` })
      } else {
        setCheck({ phase: 'done', msg: `You are up to date: QualiLens ${versionLabel(r.release, r.current)}.` })
      }
    } catch (e: any) { setCheck({ phase: 'error', msg: String(e.message ?? e) }) }
  }

  const installUpdate = async () => {
    if (!confirm('Download and install the latest release from GitHub?\n\n'
      + 'Your projects, keys, and uploads are never touched by an update. The '
      + 'app will stop itself when done; you start it again with ./run.sh and '
      + 'this page reconnects on its own.')) return
    setUpdState({ phase: 'busy', msg: 'Downloading the release and applying it…' })
    try {
      const r = await api.installUpdate()
      setUpdState({ phase: 'done',
        msg: `Updated ${r.from_version} → ${r.to_version} (${r.files_installed} files; `
          + `previous version kept in ${r.backup}).` + (r.note ? ` ${r.note}` : '') })
    } catch (e: any) {
      setUpdState({ phase: 'error', msg: String(e.message ?? e) })
    }
  }

  const applyUpdate = async (f: File | undefined) => {
    if (!f) return
    if (!confirm(`Update QualiLens from “${f.name}”?\n\nYour projects, keys, and uploads are `
      + 'never touched by an update. The app will stop itself when done; you start '
      + 'it again with ./run.sh and this page reconnects on its own.')) return
    setUpdState({ phase: 'busy', msg: 'Validating and applying the bundle…' })
    try {
      let r
      try {
        r = await api.applyUpdate(f)
      } catch (e: any) {
        // an older build than the one installed: a rollback only on request
        if (!e?.rollback) throw e
        if (!confirm(`${e.message}\n\nInstall this older build anyway?`)) {
          setUpdState({ phase: 'idle', msg: '' }); return
        }
        setUpdState({ phase: 'busy', msg: 'Installing the older build as requested…' })
        r = await api.applyUpdate(f, { allowDowngrade: true })
      }
      setUpdState({ phase: 'done',
        msg: `Updated ${r.from_version} → ${r.to_version} (${r.files_installed} files; `
          + `previous version kept in ${r.backup}).` + (r.note ? ` ${r.note}` : '') })
    } catch (e: any) {
      setUpdState({ phase: 'error', msg: String(e.message ?? e) })
    } finally {
      if (updRef.current) updRef.current.value = ''
    }
  }

  const load = async () => {
    try {
      setMeta(await api.meta())
      setSaved(await api.settings())
    } catch (e: any) { setError(String(e.message ?? e)) }
  }
  useEffect(() => { load() }, [])

  const save = async (pid: string) => {
    const v = (drafts[pid] ?? '').trim()
    if (!v) return
    try {
      await api.saveKeys({ [pid]: v })
      setDrafts(d => ({ ...d, [pid]: '' }))
      setStatus(s => ({ ...s, [pid]: 'Saved.' }))
      load()
    } catch (e: any) { setStatus(s => ({ ...s, [pid]: `Save failed: ${String(e.message ?? e)}` })) }
  }

  const clear = async (pid: string) => {
    try {
      await api.saveKeys({ [pid]: '__clear__' })
      setStatus(s => ({ ...s, [pid]: 'Cleared.' }))
      load()
    } catch (e: any) { setStatus(s => ({ ...s, [pid]: `Remove failed: ${String(e.message ?? e)}` })) }
  }

  const checkModels = async (pid: string) => {
    setStatus(s => ({ ...s, [pid]: 'Checking the provider’s live model list…' }))
    try {
      const r = await api.checkModels(pid)
      setModelCheck(m => ({ ...m, [pid]: r[pid] }))
      const res = r[pid]
      setStatus(s => ({ ...s, [pid]: res.ok
        ? (res.missing!.length
            ? `${res.missing!.length} catalog model(s) NOT in the provider's live list — likely retired.`
            : 'All catalog models are live at the provider.')
        : `Check failed: ${res.error}` }))
    } catch (e: any) { setStatus(s => ({ ...s, [pid]: `Check failed: ${String(e.message ?? e)}` })) }
  }

  const test = async (pid: string) => {
    const draft = (drafts[pid] ?? '').trim()
    setStatus(s => ({ ...s, [pid]: draft ? 'Testing the typed key (not saved yet)…' : 'Testing…' }))
    const r = await testKey(pid, undefined, draft || undefined)
    setStatus(s => ({ ...s, [pid]: r.ok ? `Key works (reply: "${r.reply}")` : `Failed: ${r.error}` }))
  }

  if (updState.phase === 'done') return <UpdateWaiting detail={updState.msg} />

  if (!meta) return <div className="page">{error ? <div className="error-box">{error}</div> : 'Loading…'}</div>

  return (
    <div className="page">
      <div className="page-head">
        <h1>Settings</h1>
        <p className="sub">Keys, data, and the application. All of it stays on this computer.</p>
      </div>
      {error && <div className="error-box">{error}</div>}

      <section className="panel">
        <div className="panel-head">
          <span className="eyebrow">Providers</span>
          <span className="panel-note">A key goes only to the provider it belongs to. Recordings are
            transcribed with the OpenAI key, whichever provider analyzes.</span>
        </div>
        {meta.providers.map(p => {
          const has = !!saved[p.id]?.has_key
          const draft = (drafts[p.id] ?? '').trim()
          const open = editing === p.id
          return (
            <div key={p.id} className={`prow ${open ? 'open' : ''}`}>
              <div className="prow-main">
                <span className={`dot ${has ? 'ok' : ''}`} aria-hidden="true" />
                <span className="prow-name">{p.label}</span>
                <span className="prow-hint mono">{has ? (saved[p.id].key_hint || 'key saved') : 'no key'}</span>
                <span className="prow-actions">
                  {has ? <>
                    <button className="small quiet" onClick={() => test(p.id)}>Test</button>
                    <button className="small quiet" onClick={() => checkModels(p.id)}
                      title="Compare this app's model catalog with the provider's live model list (free)">
                      Check models</button>
                    <button className="small quiet" onClick={() => clear(p.id)}>Remove</button>
                    <button className="small" onClick={() => setEditing(open ? null : p.id)}>
                      {open ? 'Cancel' : 'Replace key'}</button>
                  </> : (
                    <button className="small" onClick={() => setEditing(open ? null : p.id)}>
                      {open ? 'Cancel' : 'Add key'}</button>
                  )}
                </span>
              </div>
              {open && (
                <div className="prow-editor">
                  <input type="password" autoFocus
                    placeholder={has ? 'Paste the new key…' : 'Paste API key…'}
                    value={drafts[p.id] ?? ''}
                    onChange={e => setDrafts(d => ({ ...d, [p.id]: e.target.value }))}
                    onKeyDown={e => { if (e.key === 'Enter' && draft) { save(p.id).then(() => setEditing(null)) } }} />
                  <button className="primary" disabled={!draft}
                    onClick={() => save(p.id).then(() => setEditing(null))}>Save</button>
                  <button disabled={!draft} onClick={() => test(p.id)}
                    title="Tests the typed key without saving it">Test first</button>
                </div>
              )}
              {status[p.id] && <p className="prow-status small muted">{status[p.id]}</p>}
              {modelCheck[p.id]?.ok && (
                <div className="prow-extra">
                  <div className="row" style={{ gap: 8 }}>
                    {modelCheck[p.id].catalog.map((m: any) => (
                      <span key={m.id} className={`badge ${m.available ? 'completed' : 'failed'}`}>
                        {m.available ? '✓' : '✗'} {m.id}
                      </span>
                    ))}
                  </div>
                  {modelCheck[p.id].missing.length > 0 && (
                    <p className="small" style={{ marginTop: 6 }}>
                      Models marked ✗ are absent from the provider’s live list. Update
                      <code> backend/app/models.json</code> — instructions are in that file’s
                      own <code>_readme</code> — or use a custom model id in the wizard meanwhile.
                    </p>
                  )}
                  <details className="small muted" style={{ marginTop: 6 }}>
                    <summary>
                      {modelCheck[p.id].live_count} models live at the provider — show ids
                      {modelCheck[p.id].live.length < modelCheck[p.id].live_count &&
                        ` (first ${modelCheck[p.id].live.length} shown)`}
                    </summary>
                    <p className="mono" style={{ maxHeight: 140, overflowY: 'auto' }}>
                      {modelCheck[p.id].live.join(' · ')}
                    </p>
                  </details>
                </div>
              )}
            </div>
          )
        })}
      </section>

      <div className="grid2">
      <section className="panel">
        <div className="panel-head"><span className="eyebrow">Data</span></div>
        <div className="panel-body">
          <table className="facts"><tbody>
            <tr><td className="muted">Folder</td>
              <td><code style={{ wordBreak: 'break-all' }}>{meta.data_dir}</code></td></tr>
            <tr><td className="muted">Cloud sync</td>
              <td>{meta.synced_folder
                ? <b>inside {meta.synced_folder}, so the sync service holds your participant data and keys</b>
                : 'not inside a synced folder'}</td></tr>
            <tr><td className="muted">ffmpeg</td>
              <td>{meta.ffmpeg ? 'installed, so video files can be processed'
                : <>not found: install it (<code>brew install ffmpeg</code>) to analyze video</>}</td></tr>
          </tbody></table>
          <details className="small muted" style={{ marginTop: 10 }}>
            <summary>Moving the folder</summary>
            <p style={{ margin: '6px 0 0' }}>
              The files are unencrypted, protected only by your computer's file permissions. To keep
              them on this computer only, stop the app and start it with
              <code> QUALILENS_DATA_DIR=/path/outside/the/synced/tree ./run.sh</code>, after moving the
              existing <code>data</code> folder there. The manual's Data, Privacy, and Governance
              chapter has the details.
            </p>
          </details>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head"><span className="eyebrow">Application</span></div>
        <div className="panel-body">
        <table className="facts"><tbody>
          <tr><td className="muted">Version</td>
            <td>{versionLabel(meta.release, meta.version)}</td></tr>
          <tr><td className="muted">Updates checked</td>
            <td>{meta.update_hint?.last_checked
              ? `${ageLabel(meta.update_hint.days_since_check)} ago`
              : 'never from this installation'}
              {meta.update_hint?.remind && meta.update_hint.build_age_days != null &&
                <span className="muted"> · this build is {ageLabel(meta.update_hint.build_age_days)} old, worth a check</span>}
            </td></tr>
        </tbody></table>
        <details className="small muted" style={{ margin: '10px 0 12px' }}>
          <summary>How updates work</summary>
          <p style={{ margin: '6px 0 0' }}>
            Updates are pull-only. <b>Check for updates</b> makes one request to GitHub, only when
            you press it; nothing runs in the background, and nothing is sent beyond the request
            itself. A bundle installs only if it carries a valid signature from the QualiLens
            release key; an unsigned, foreign, or altered bundle is refused, and so is a build
            older than this one unless you ask for it. Your projects, API keys, and uploaded data
            are never touched: only the application's own files are replaced, the previous version
            is kept as a backup, and an update is refused while any run is executing or awaiting
            review. The build stamp is the date and time the release was packaged.
          </p>
        </details>
        <div className="row">
          <button onClick={checkForUpdates}
            disabled={check.phase === 'busy' || updState.phase === 'busy' || updState.phase === 'done'}>
            {check.phase === 'busy' ? 'Checking…' : 'Check for updates'}
          </button>
          {check.newer && (
            <button className="primary" onClick={installUpdate}
              disabled={updState.phase === 'busy' || updState.phase === 'done'}>
              {updState.phase === 'busy' ? 'Updating…' : 'Download and install'}
            </button>
          )}
          <button className="quiet" onClick={() => updRef.current?.click()}
            disabled={updState.phase === 'busy' || updState.phase === 'done'}>
            From a downloaded zip…
          </button>
          <input ref={updRef} type="file" accept=".zip" style={{ display: 'none' }}
            onChange={e => applyUpdate(e.target.files?.[0])} />
        </div>
        {check.phase === 'done' && (
          <p className="small muted" style={{ marginBottom: 0 }}>
            {check.msg}
            {check.releaseUrl && <>{' '}
              <a href={check.releaseUrl} target="_blank" rel="noopener">release page ↗</a></>}
          </p>
        )}
        {check.phase === 'error' && <p className="small muted" style={{ marginBottom: 0 }}>{check.msg}</p>}
        {updState.phase === 'done' && <div className="info-box mt">{updState.msg}</div>}
        {updState.phase === 'error' && <div className="error-box mt">{updState.msg}</div>}
        </div>
      </section>
      </div>
    </div>
  )
}
