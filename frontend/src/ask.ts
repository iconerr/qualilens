// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

/* The app's own confirmation dialog, in place of the browser's confirm()
   (added 2026-11-15). It is set in the app's type and colors, its buttons
   are named for what they do, and for anything that cannot be undone the
   safe choice holds the focus and the other button is red. Esc, the cancel
   button, or a click outside the dialog all answer no. */

import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import { AskDialog } from './AskDialog'

export type Ask = { title: string; body?: string[]; confirm: string; cancel?: string; danger?: boolean }

/** Ask a yes-or-no question in the app's own dialog; resolves true for yes. */
export function ask(opts: Ask): Promise<boolean> {
  return new Promise(resolve => {
    const host = document.createElement('div')
    document.body.appendChild(host)
    const root = createRoot(host)
    const before = document.activeElement as HTMLElement | null
    let answered = false
    const done = (yes: boolean) => {
      if (answered) return
      answered = true
      before?.focus?.()
      resolve(yes)
      // unmount after the click that answered has finished
      setTimeout(() => { root.unmount(); host.remove() })
    }
    root.render(createElement(AskDialog, { ...opts, done }))
  })
}
