// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

// One quiet line on the Projects page when the running build is a month or
// more old and updates have not been checked in two weeks: the fact and the
// path, no urgency. Computed by the server from the build's date — no
// request leaves the machine. Dismiss hides it until the app is next launched.

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ageLabel, api, type UpdateHint as Hint } from './api'

export default function UpdateHint() {
  const [hint, setHint] = useState<Hint | null>(null)
  useEffect(() => {
    api.meta().then(m => setHint(m.update_hint ?? null)).catch(() => { /* the page still works */ })
  }, [])
  if (!hint || !hint.remind || hint.dismissed) return null
  const dismiss = async () => {
    setHint({ ...hint, dismissed: true })
    try { await api.dismissUpdateHint() } catch { /* already hidden here */ }
  }
  return (
    <div className="info-box row spread" role="status">
      <span>
        This build is {ageLabel(hint.build_age_days)} old
        {hint.days_since_check == null
          ? ', and updates have not been checked from this installation'
          : `; updates were last checked ${ageLabel(hint.days_since_check)} ago`}.
        {' '}<Link to="/settings">Settings → Check for updates</Link>.
      </span>
      <button className="small" onClick={dismiss} title="Hide this until the app is next started">Dismiss</button>
    </div>
  )
}
