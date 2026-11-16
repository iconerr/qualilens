// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Wizard from './pages/Wizard'
import ProjectPage from './pages/Project'
import RunPage from './pages/Run'
import ReportPage from './pages/Report'
import SourceReader from './pages/SourceReader'
import Settings from './pages/Settings'
import NotSignedIn from './NotSignedIn'
import { Stopped } from './Quit'
import { ask } from './ask'
import { api, signedIn, versionLabel } from './api'

const QL_LINEAGE = 'ql-a2f4467befc3477b9caea1866a2af37e'

// what this page was served by: the server stamps both into index.html, so
// the footer can say which version is running without a request
const metaTag = (name: string) =>
  document.querySelector(`meta[name="${name}"]`)?.getAttribute('content') ?? ''
const RUNNING = versionLabel(metaTag('ql-release'), metaTag('ql-build'))

const KONAMI = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
  'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a']

const EGG_WORDS = ['open coding', 'in-vivo', 'memo', 'axial', 'saturation',
  'reflexivity', 'core category', 'verbatim', 'audit trail', 'themes',
  'constant comparison', 'thick description', 'member check', 'bracketing']

function useKonami(onUnlock: () => void) {
  useEffect(() => {
    let progress = 0
    const onKey = (e: KeyboardEvent) => {
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key
      progress = key === KONAMI[progress] ? progress + 1 : (key === KONAMI[0] ? 1 : 0)
      if (progress === KONAMI.length) { progress = 0; onUnlock() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onUnlock])
}

function CoreCategoryEgg({ onDone }: { onDone: () => void }) {
  const pills = useMemo(() =>
    Array.from({ length: 26 }, (_, i) => ({
      word: EGG_WORDS[i % EGG_WORDS.length],
      left: (i * 37 + 11) % 100,
      delay: ((i * 13) % 20) / 10,
      dur: 3.5 + ((i * 7) % 25) / 10,
    })), [])
  useEffect(() => {
    const t = setTimeout(onDone, 7000)
    return () => clearTimeout(t)
  }, [onDone])
  return (
    <div className="egg-layer" onClick={onDone} role="presentation">
      {pills.map((p, i) => (
        <span key={i} className="egg-pill"
          style={{ left: `${p.left}%`, animationDelay: `${p.delay}s`,
                   animationDuration: `${p.dur}s` }}>
          {p.word}
        </span>
      ))}
      <div className="egg-toast">
        <b>You found the core category.</b>
        <div>Everything else in the data relates to you, the careful reader.</div>
        <div className="egg-sig">— Ashita &amp; Suraj</div>
      </div>
    </div>
  )
}

/** Ask, then quit. The server first says what stopping now would interrupt,
    the dialog says it, and only a yes stops the app. Resolves true when the
    app is stopping. */
async function quitApp(): Promise<boolean> {
  try {
    const now = await api.quit(false)
    const body = ['QualiLens stops. Your projects are saved.']
    if (now.running > 0) body.push(
      `${now.running === 1 ? 'A run is' : `${now.running} runs are`} in progress. Quitting `
      + `interrupts ${now.running === 1 ? 'it' : 'them'}. You can resume `
      + `${now.running === 1 ? 'it' : 'them'} when you start QualiLens again. Finished work is `
      + 'kept and is not billed again.')
    if (now.transcribing > 0) body.push(
      `${now.transcribing === 1 ? 'A recording is' : `${now.transcribing} recordings are`} being `
      + `transcribed. Quitting interrupts ${now.transcribing === 1 ? 'it' : 'them'}. You can retry `
      + `${now.transcribing === 1 ? 'it' : 'them'} when you start QualiLens again.`)
    body.push('To start QualiLens again, run ./run.sh in Terminal.')
    const busy = now.running > 0 || now.transcribing > 0
    if (!(await ask({ title: 'Quit QualiLens?', body, confirm: 'Quit QualiLens',
                      cancel: 'Keep it running', danger: busy }))) return false
    await api.quit(true)
    return true
  } catch (e: any) {
    void ask({ title: 'QualiLens did not quit', body: [String(e?.message ?? e)], confirm: 'OK', cancel: '' })
    return false
  }
}

export default function App() {
  const [egg, setEgg] = useState(false)
  // after Quit: the server is gone, so the bar offers nothing and the page says so
  const [stopped, setStopped] = useState(false)
  useKonami(() => setEgg(true))
  // a tab without the session token can reach nothing but the manual
  const ok = signedIn()
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          <svg className="mark" viewBox="0 0 48 48" aria-hidden="true">
            <line x1="2" y1="4" x2="22" y2="19" stroke="#863bff" strokeWidth="2.8" strokeLinecap="round" opacity="0.35"/>
            <line x1="2" y1="14" x2="22" y2="21" stroke="#863bff" strokeWidth="2.8" strokeLinecap="round" opacity="0.55"/>
            <line x1="2" y1="24" x2="22" y2="24" stroke="#863bff" strokeWidth="2.8" strokeLinecap="round" opacity="0.75"/>
            <line x1="2" y1="34" x2="22" y2="27" stroke="#863bff" strokeWidth="2.8" strokeLinecap="round" opacity="0.55"/>
            <line x1="2" y1="44" x2="22" y2="29" stroke="#863bff" strokeWidth="2.8" strokeLinecap="round" opacity="0.35"/>
            <polyline points="31,12 44,24 31,36" stroke="#863bff" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="word">QualiLens</span><small>You. AI. Done.</small>
        </Link>
        {!stopped && <nav>
          {/* the one link that leaves this tab says so, with the same mark
              the rest of the app uses for links that open elsewhere */}
          <a href="/manual.html" target="_blank" rel="noopener"
            title="Opens the manual in a new tab; your work here stays where it is">
            Manual<span className="ext" aria-hidden="true">↗</span></a>
          {ok && <>
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>Settings</NavLink>
            <NavLink to="/new" className="nav-primary">New analysis</NavLink>
            {/* last and quiet: used once a session, and it asks before anything stops */}
            <button type="button" className="nav-quit" title="Stop QualiLens on this computer"
              onClick={async () => { if (await quitApp()) setStopped(true) }}>Quit</button>
          </>}
        </nav>}
      </header>
      {stopped ? <Stopped /> : ok ? (
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/new" element={<Wizard />} />
          <Route path="/projects/:id" element={<ProjectPage />} />
          <Route path="/runs/:id" element={<RunPage />} />
          <Route path="/runs/:id/report" element={<ReportPage />} />
          <Route path="/runs/:runId/sources/:sourceId" element={<SourceReader />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      ) : <NotSignedIn />}
      <footer className="footer" data-ql={QL_LINEAGE}>
        QualiLens <span className="mono" title="The version you are running; Settings has the update check">{RUNNING}</span> ·
        © 2026 <a href="https://in.linkedin.com/in/drashita" target="_blank" rel="noopener">Ashita Aggarwal</a> &amp; Suraj Commuri ·
        released under the <a href="https://www.apache.org/licenses/LICENSE-2.0"
          target="_blank" rel="noopener">Apache-2.0 license</a> — free to use,
        modify, and share with attribution. Your data and analyses remain
        entirely yours.
      </footer>
      {egg && <CoreCategoryEgg onDone={() => setEgg(false)} />}
    </>
  )
}
