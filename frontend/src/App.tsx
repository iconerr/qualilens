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

const QL_LINEAGE = 'ql-a2f4467befc3477b9caea1866a2af37e'

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

export default function App() {
  const [egg, setEgg] = useState(false)
  useKonami(() => setEgg(true))
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
          QualiLens<small>You. AI. Done.</small>
        </Link>
        <nav>
          {/* the one link that leaves this tab says so, with the same mark
              the rest of the app uses for links that open elsewhere */}
          <a href="/manual.html" target="_blank" rel="noopener"
            title="Opens the manual in a new tab; your work here stays where it is">
            Manual<span className="ext" aria-hidden="true">↗</span></a>
          <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>Settings</NavLink>
          <NavLink to="/new" className="nav-primary">New analysis</NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/new" element={<Wizard />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="/runs/:id" element={<RunPage />} />
        <Route path="/runs/:id/report" element={<ReportPage />} />
        <Route path="/runs/:runId/sources/:sourceId" element={<SourceReader />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
      <footer className="footer" data-ql={QL_LINEAGE}>
        QualiLens · © 2026 Ashita Aggarwal &amp; Suraj Commuri ·
        released under the <a href="https://www.apache.org/licenses/LICENSE-2.0"
          target="_blank" rel="noopener">Apache-2.0 license</a> — free to use,
        modify, and share with attribution. Your data and analyses remain
        entirely yours.
      </footer>
      {egg && <CoreCategoryEgg onDone={() => setEgg(false)} />}
    </>
  )
}
