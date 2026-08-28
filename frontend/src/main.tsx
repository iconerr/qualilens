// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './styles.css'

try {
  console.log(
    '%cQualiLens%c — handcrafted for researchers by Ashita Aggarwal & Suraj Commuri.\n' +
    'Reading the console is sound qualitative practice: the interface is only ' +
    'what the system says in public.\n' +
    'For the full interview, try:  \u2191 \u2191 \u2193 \u2193 \u2190 \u2192 \u2190 \u2192 b a',
    'font-weight:700;font-size:15px;color:#1f3a5f', '')
} catch { /* consoles are optional */ }

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
