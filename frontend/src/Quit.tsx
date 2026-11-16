// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

/* The page after Quit QualiLens (2026-11-15). The link itself is in App.tsx: it sits at the end of the top bar, on
   every screen, where an app's way out is looked for. It was in Settings for
   an evening, and Suraj asked for a more intuitive place. */

import { useEffect, useState } from 'react'
import { workingToken } from './api'

// After Quit QualiLens. The server has stopped, so nothing here can reach
// it. The page says so, and how to start the app again. Starting it again
// opens a new tab, signed in with a new token, and this tab cannot sign in
// before that one has.
//
// This tab does not become the app again. At first it reloaded as soon as a
// server answered, and showed the sign-in notice in place of what it had
// promised; then it joined once the new tab had signed in, which left two
// tabs of the app. Now, when this browser holds a token the new server
// accepts, the page says that QualiLens is running in another tab, and that
// this one can be closed. A page cannot close its own tab. If the app stops
// again, the page says so again.
export function Stopped() {
  const [elsewhere, setElsewhere] = useState(false)
  useEffect(() => {
    let alive = true
    let wentDown = false
    const tick = async () => {
      if (!alive) return
      try {
        const res = await fetch('/', { cache: 'no-store', credentials: 'omit' })
        if (!res.ok || !wentDown) return
        const token = await workingToken()
        if (alive) setElsewhere(!!token)
      } catch { wentDown = true; if (alive) setElsewhere(false) }
    }
    const id = window.setInterval(tick, 3000)
    return () => { alive = false; window.clearInterval(id) }
  }, [])
  return (
    <div className="page" style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '60vh', textAlign: 'center', gap: 16
    }}>
      {elsewhere ? (<>
        <h1 style={{ margin: 0 }}>QualiLens is running in another tab</h1>
        <p style={{ maxWidth: 480, lineHeight: 1.6, margin: 0 }}>
          Use that tab. You can close this one.
        </p>
      </>) : (<>
        <h1 style={{ margin: 0 }}>QualiLens has stopped</h1>
        <p style={{ maxWidth: 480, lineHeight: 1.6, margin: 0 }}>
          Your projects are saved. You can close this tab.
        </p>
        <p style={{ maxWidth: 480, lineHeight: 1.6, margin: 0 }}>
          To start QualiLens again, run <code>./run.sh</code> in Terminal. It opens in a
          new tab.
        </p>
      </>)}
    </div>
  )
}
