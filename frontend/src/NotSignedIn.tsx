// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from 'react'
import { adoptToken, tokenFromServer } from './api'

// What a tab without the session token shows: one opened by address or
// bookmark in a browser no launch page has signed in, or one that outlived a
// restart before the new launch page opened. The server gives the token only
// to a browser the launch page signed in, so other accounts on this computer
// cannot reach the data through it. This tab asks the server every two
// seconds, and when this window regains focus, and signs itself in as soon
// as another tab of the same browser has been.
export default function NotSignedIn() {
  useEffect(() => {
    let done = false
    const look = async () => {
      if (done) return
      try {
        const token = await tokenFromServer()
        if (token && !done) { done = true; adoptToken(token) }
      } catch { /* the server is down; ask again */ }
    }
    const t = window.setInterval(look, 2000)
    window.addEventListener('focus', look)
    return () => { done = true; window.clearInterval(t); window.removeEventListener('focus', look) }
  }, [])

  return (
    <div className="page" style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '60vh', textAlign: 'center', gap: 16
    }}>
      <h1 style={{ margin: 0 }}>Open QualiLens from the tab it opened</h1>
      <p style={{ maxWidth: 500, lineHeight: 1.6, margin: 0 }}>
        This tab is not signed in, so it cannot reach your projects. QualiLens signs in only
        the browser that <code>./run.sh</code> opens, so other accounts on this computer
        cannot read your data through it.
      </p>
      <p style={{ maxWidth: 500, lineHeight: 1.6, margin: 0 }}>
        Switch to the tab <code>./run.sh</code> opened, or open the launch page its Terminal
        window names. If you have neither, stop QualiLens with <kbd>Ctrl</kbd>-<kbd>C</kbd> in
        that window and run <code>./run.sh</code> again.
      </p>
      <p className="small muted" style={{ margin: 0 }}>
        This tab signs itself in as soon as another tab of this browser has been signed in.
      </p>
    </div>
  )
}
