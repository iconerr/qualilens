// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

/* The dialog that ask() shows; see ask.ts. */

import { useEffect, useRef, type KeyboardEvent } from 'react'
import type { Ask } from './ask'

export function AskDialog({ title, body = [], confirm, cancel = 'Cancel', danger, done }: Ask & { done: (ok: boolean) => void }) {
  const ok = useRef<HTMLButtonElement>(null)
  const no = useRef<HTMLButtonElement>(null)
  useEffect(() => { (danger ? no : ok).current?.focus() }, [danger])
  const keys = (e: KeyboardEvent) => {
    if (e.key === 'Escape') { e.preventDefault(); done(false) }
    if (e.key === 'Tab') {               // focus stays on the two buttons
      e.preventDefault()
      ;(document.activeElement === ok.current ? no : ok).current?.focus()
    }
  }
  return (
    <div className="modal-back" onMouseDown={e => { if (e.target === e.currentTarget) done(false) }}>
      <div className="modal ask" role="alertdialog" aria-modal="true"
        aria-labelledby="ql-ask-title" aria-describedby="ql-ask-body" onKeyDown={keys}>
        <h2 id="ql-ask-title">{title}</h2>
        <div id="ql-ask-body">{body.map((p, i) => <p key={i}>{p}</p>)}</div>
        <div className="ask-actions">
          <button ref={no} onClick={() => done(false)}>{cancel}</button>
          <button ref={ok} className={danger ? 'primary danger' : 'primary'} onClick={() => done(true)}>{confirm}</button>
        </div>
      </div>
    </div>
  )
}
