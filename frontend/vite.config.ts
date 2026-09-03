// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

import { createHash } from 'node:crypto'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// Fingerprint of the interface sources, stamped into index.html so the
// backend (and the packaging test) can tell a stale dist from a fresh one.
// Must stay byte-for-byte identical to backend/app/buildinfo.py.
const FINGERPRINT_FILES = ['index.html', 'package.json', 'package-lock.json',
  'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json']
const FINGERPRINT_TREES = ['src', 'public']
const FINGERPRINT_EXCLUDE = new Set(['public/manual.html'])

function walk(dir: string, out: string[]) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else out.push(p)
  }
}

function sourceFingerprint(root: string): string {
  const files: string[] = []
  for (const f of FINGERPRINT_FILES) {
    const p = join(root, f)
    try { if (statSync(p).isFile()) files.push(p) } catch { /* absent is fine */ }
  }
  for (const t of FINGERPRINT_TREES) {
    try { if (statSync(join(root, t)).isDirectory()) walk(join(root, t), files) } catch { /* absent */ }
  }
  const rels = files
    .map(p => [relative(root, p).split('\\').join('/'), p] as const)
    .filter(([rel]) => !FINGERPRINT_EXCLUDE.has(rel))
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  const h = createHash('sha256')
  for (const [rel, p] of rels) {
    h.update(Buffer.from(rel + '\n', 'utf8'))
    h.update(readFileSync(p))
    h.update(Buffer.from('\n', 'utf8'))
  }
  return h.digest('hex').slice(0, 16)
}

function stampSourceFingerprint(root: string): Plugin {
  return {
    name: 'qualilens-source-fingerprint',
    transformIndexHtml(html) {
      const fp = sourceFingerprint(root)
      return html.replace('</head>', `<meta name="ql-src" content="${fp}"></head>`)
    },
  }
}

export default defineConfig({
  plugins: [react(), stampSourceFingerprint(process.cwd())],
  server: {
    // development only: the backend must be started with QUALILENS_TOKEN=<value>
    // and the same value exported here, e.g. QUALILENS_TOKEN=dev in both shells
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
        headers: { 'X-QualiLens-Token': process.env.QUALILENS_TOKEN ?? 'dev' },
        // the browser's Origin here is the dev server's own (localhost:5173);
        // the backend accepts only its exact origin, so the proxy drops the
        // header — the token above still gates every call
        configure: proxy => { proxy.on('proxyReq', req => { req.removeHeader('origin') }) },
      },
    },
  },
})
