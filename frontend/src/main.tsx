// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
// The interface's three faces ship inside the app, as on qualilens.org (the
// 2026-11-15 register): IBM Plex Sans (weight axis, with a true italic) for
// the interface, IBM Plex Serif for display headings and for what is read
// (report, reader, quotes), IBM Plex Mono for identifiers. Nothing is fetched
// at run time.
import '@fontsource-variable/ibm-plex-sans'
import '@fontsource-variable/ibm-plex-sans/wght-italic.css'
import '@fontsource/ibm-plex-serif/400.css'
import '@fontsource/ibm-plex-serif/400-italic.css'
import '@fontsource/ibm-plex-serif/500.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './styles.css'

try {
  console.log(
    '%cQualiLens%c — handcrafted for researchers by Ashita Aggarwal & Suraj Commuri.\n' +
    'Reading the console is sound qualitative practice: the interface is only ' +
    'what the system says in public.\n' +
    'For the full interview, try:  \u2191 \u2191 \u2193 \u2193 \u2190 \u2192 \u2190 \u2192 b a',
    'font-weight:600;font-size:15px;color:#1c1917', '')
} catch { /* consoles are optional */ }

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
