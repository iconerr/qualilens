// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from 'react'
import { adoptToken, workingToken } from './api'

// What a tab without the session token shows: one opened by address or
// bookmark in a browser no launch page has signed in, or one that outlived a
// restart before the new launch page opened. The server gives the token only
// to a browser the launch page signed in, so other accounts on this computer
// cannot reach the data through it. A tab the launch page signs in stores
// the token where this browser's other tabs can read it, so this tab looks
// every two seconds, when another tab stores something, and when this window
// regains focus, and signs itself in as soon as it finds a token the server
// accepts.
export default function NotSignedIn() {
  useEffect(() => {
    let done = false
    const look = async () => {
      if (done) return
      try {
        const token = await workingToken()
        if (token && !done) { done = true; adoptToken(token) }
      } catch { /* the server is down; ask again */ }
    }
    const t = window.setInterval(look, 2000)
    window.addEventListener('focus', look)
    window.addEventListener('storage', look)
    return () => {
      done = true; window.clearInterval(t)
      window.removeEventListener('focus', look); window.removeEventListener('storage', look)
    }
  }, [])

  return (
    <div className="page" style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '60vh', textAlign: 'center', gap: 16
    }}>
      <h1 style={{ margin: 0 }}>This tab is not signed in</h1>
      <p style={{ maxWidth: 500, lineHeight: 1.6, margin: 0 }}>
        QualiLens is running, but this tab cannot open your projects. Use the tab that
        opened when you started QualiLens.
      </p>
      <p style={{ maxWidth: 500, lineHeight: 1.6, margin: 0 }}>
        If you cannot find that tab, go to the Terminal window where QualiLens is running.
        Press <kbd>Ctrl</kbd>-<kbd>C</kbd> to stop it. Then run <code>./run.sh</code> again.
      </p>
      <p className="small muted" style={{ maxWidth: 500, margin: 0 }}>
        QualiLens signs in only the browser it opens. This keeps other accounts on this
        computer out of your projects. Once one tab in this browser is signed in, this
        tab signs in by itself.
      </p>
    </div>
  )
}
