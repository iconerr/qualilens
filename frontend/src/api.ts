// Copyright 2026 Ashita Aggarwal and Suraj Commuri
// SPDX-License-Identifier: Apache-2.0

// Thin typed client over the local FastAPI backend.

export interface Question {
  key: string; label: string; help: string;
  type: 'text' | 'textarea' | 'select' | 'toggle';
  options: string[]; default: string; required: boolean;
}
export interface MethodMeta {
  id: string; label: string; description: string;
  questions: Question[];
  stages: { name: string; label: string; kind: string }[];
}
export interface ProviderMeta {
  id: string; label: string; default_model: string; models: string[]; has_key: boolean;
}
export interface Meta {
  methods: MethodMeta[]; providers: ProviderMeta[]; ffmpeg: boolean; version?: string;
  release?: string; running_build?: string; running_release?: string;
  data_dir?: string; synced_folder?: string;
  update_hint?: UpdateHint;
}
export interface UpdateHint {
  remind: boolean; dismissed: boolean;
  build_age_days: number | null; days_since_check: number | null; last_checked: number | null;
}

// "3 days", "6 weeks", "4 months" — for the age of a build or of the last check
export function ageLabel(days: number | null | undefined): string {
  if (days == null) return ''
  if (days === 0) return 'today'
  if (days < 14) return `${days} day${days === 1 ? '' : 's'}`
  if (days < 70) { const w = Math.round(days / 7); return `${w} week${w === 1 ? '' : 's'}` }
  const m = Math.round(days / 30); return `${m} month${m === 1 ? '' : 's'}`
}

// "1.6.3 (build 2026.09.03-0711)" — the release version package.sh writes
// beside the build stamp, when there is one; the build alone otherwise; a
// checkout that was never packaged is a development build.
export function versionLabel(release?: string | null, build?: string | null): string {
  const r = release && release !== 'unknown' && release !== 'unreleased' ? release : ''
  const b = build && build !== 'unknown' ? `build ${build}` : ''
  if (r && b) return `${r} (${b})`
  if (r) return r
  if (b) return release === 'unreleased' ? `${b}, unreleased` : b
  return 'development build'
}

export interface Source {
  id: string; filename: string; kind: string; status: string;
  grp: string | null; chars: number; meta: Record<string, unknown>;
}
export interface RunSummary {
  id: string; status: string; stage_index: number; stage_name: string | null;
  progress: { done?: number; total?: number; detail?: string };
  usage: { input_tokens?: number; output_tokens?: number; calls?: number };
  error: string | null; created_at: number; updated_at: number;
}
export interface Project {
  id: string; name: string; method: string; config: Record<string, string>;
  created_at: number; sources: Source[]; runs: RunSummary[];
  stages: { name: string; label: string; kind: string }[];
  n_sources?: number; latest_run?: { id: string; status: string } | null;
}
export interface Checkpoint {
  id: string; stage: string; title: string; instructions: string;
  payload: Record<string, any>; status: string;
}
export interface CodedSpan {
  excerpt_id: string; code_id: string; code_name: string; code_stage: string;
  parent_name: string | null; quote: string; memo: string;
  confidence: number | null; start: number; end: number;
  page?: number | null;
}
export interface CodedSource {
  filename: string; text: string; run_id: string;
  pages?: { page: number; start: number; end: number }[];
  spans: CodedSpan[]; unlocated: CodedSpan[];
  codes: { id: string; name: string; stage: string; parent_name: string | null; count: number; unlocated_count: number }[];
}
export interface SheetImport {
  kind: 'code_review' | 'extraction_review'
  decisions?: { id: string; action: string; name?: string; definition?: string; merge_into?: string; notes?: string }[]
  additions?: { name: string; definition: string; notes?: string }[]
  rows?: ({ source_id: string; exclude?: boolean; notes?: string } & Record<string, unknown>)[]
  ignored: { row: number; id?: string; reason: string }[]
  summary: Record<string, number>
  imported_from: { filename: string; sha256: string; stored: string }
}
export interface Run extends RunSummary {
  project_id: string; project_name: string;
  stages: { name: string; label: string; kind: string }[];
  pending_checkpoint: Checkpoint | null; has_report: boolean;
}

// The per-launch session token the server injects into index.html. Every
// API request carries it; the server refuses /api calls without it, which is
// what keeps other web pages (and DNS-rebinding hosts) out of this app.
const TOKEN =
  (typeof document !== 'undefined'
    ? document.querySelector('meta[name="ql-token"]')?.getAttribute('content')
    : null) ?? ''

function withToken(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers ?? {})
  if (TOKEN) headers.set('X-QualiLens-Token', TOKEN)
  return { ...init, headers, credentials: 'same-origin' }
}

// A 401 from our own server means this page holds a token the server no
// longer knows: the app was restarted (an update, a relaunch) and the page
// survived it — Safari restores tabs with their old script state for days.
// The only remedy is the one the old error message asked the human for, so
// do it for them: reload once, which fetches index.html and the new token.
// The guard stops a loop if reloading did not help (then the error shows).
const STALE_KEY = 'ql-stale-reload'
function reloadIfStaleToken(res: Response): boolean {
  if (res.status !== 401 || typeof window === 'undefined') return false
  try {
    const last = Number(sessionStorage.getItem(STALE_KEY) ?? 0)
    if (Date.now() - last < 15000) return false
    sessionStorage.setItem(STALE_KEY, String(Date.now()))
  } catch { /* storage unavailable: still reload once per page life */ }
  window.location.reload()
  return true
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, withToken(init))
  if (!res.ok) {
    if (reloadIfStaleToken(res)) return new Promise<T>(() => { /* the page is reloading */ })
    throw new Error(await errText(res))
  }
  return res.json()
}

async function errText(res: Response): Promise<string> {
  try {
    const body = await res.json()
    const d = body?.detail ?? body
    return typeof d === 'string' ? d : JSON.stringify(d)
  } catch {
    return `Request failed (HTTP ${res.status})`
  }
}
const post = (body?: unknown) =>
  ({ method: 'POST', headers: { 'Content-Type': 'application/json' },
     body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  meta: () => j<Meta>('/api/meta'),
  settings: () => j<Record<string, { has_key: boolean; key_hint: string }>>('/api/settings'),
  saveKeys: (keys: Record<string, string>) =>
    j('/api/settings/keys', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(keys) }),
  projects: () => j<Project[]>('/api/projects'),
  project: (id: string) => j<Project>(`/api/projects/${id}`),
  createProject: (name: string, method: string, config: Record<string, string>) =>
    j<Project>('/api/projects', post({ name, method, config })),
  updateProject: (id: string, name: string, method: string, config: Record<string, string>) =>
    j<Project>(`/api/projects/${id}`, { method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, method, config }) }),
  deleteProject: (id: string) => j(`/api/projects/${id}`, { method: 'DELETE' }),
  uploadSource: async (projectId: string, file: File, grp: string) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('grp', grp)
    const res = await fetch(`/api/projects/${projectId}/sources`, withToken({ method: 'POST', body: fd }))
    if (!res.ok) {
      if (reloadIfStaleToken(res)) return new Promise<Source>(() => { /* reloading */ })
      throw new Error(await errText(res))
    }
    return res.json() as Promise<Source>
  },
  deleteSource: (id: string) => j(`/api/sources/${id}`, { method: 'DELETE' }),
  retrySource: (id: string) => j(`/api/sources/${id}/retry`, post()),
  sourceText: (id: string) => j<{ filename: string; text: string }>(`/api/sources/${id}/text`),
  estimate: (projectId: string) =>
    j<{ n_sources: number; total_chars: number; est_input_tokens: number;
        est_output_tokens: number; est_cost_usd: number; note: string;
        priced_model?: string | null; price_per_mtok?: number[] }>(`/api/projects/${projectId}/estimate`),
  startRun: (projectId: string) => j<{ run_id: string }>(`/api/projects/${projectId}/runs`, post()),
  run: (id: string) => j<Run>(`/api/runs/${id}`),
  events: (id: string, after: number) =>
    j<{ ts: number; kind: string; message: string }[]>(`/api/runs/${id}/events?after=${after}`),
  resolveCheckpoint: (runId: string, cpId: string, resolution: unknown) =>
    j(`/api/runs/${runId}/checkpoints/${cpId}/resolve`, post(resolution)),
  branchRun: (runId: string, stage: string) =>
    j<{ run_id: string }>(`/api/runs/${runId}/branch`, post({ stage })),
  resumeRun: (id: string) => j(`/api/runs/${id}/resume`, post()),
  cancelRun: (id: string) => j(`/api/runs/${id}/cancel`, post()),
  report: (runId: string) => j<any>(`/api/runs/${runId}/report`),
  codeExcerpts: (runId: string, codeId: string) =>
    j<{ id: string; quote: string; memo: string; confidence: number | null;
        start_char: number | null; end_char: number | null;
        source_id: string; source: string; via: string | null }[]>(
      `/api/runs/${runId}/codes/${codeId}/excerpts`),
  checkModels: (provider?: string) =>
    j<Record<string, { ok: boolean; error?: string; missing?: string[];
      catalog?: { id: string; available: boolean }[];
      live_count?: number; live?: string[] }>>(
      '/api/settings/check_models', post({ provider })),
  // A bundle older than the installed build answers 409: the error carries
  // rollback=true so the screen can ask, then retry with allowDowngrade.
  applyUpdate: async (file: File, opts?: { allowDowngrade?: boolean }) => {
    const fd = new FormData()
    fd.append('file', file)
    if (opts?.allowDowngrade) fd.append('allow_downgrade', 'true')
    const res = await fetch('/api/settings/update', withToken({ method: 'POST', body: fd }))
    if (!res.ok) {
      if (reloadIfStaleToken(res)) return new Promise<never>(() => { /* reloading */ })
      const err = new Error(await errText(res)) as Error & { rollback?: boolean }
      if (res.status === 409) err.rollback = true
      throw err
    }
    return res.json() as Promise<{ ok: boolean; from_version: string; to_version: string;
      files_installed: number; backup: string; restart_required?: boolean; note?: string }>
  },
  codedSource: (runId: string, sourceId: string) =>
    j<CodedSource>(`/api/runs/${runId}/sources/${sourceId}/coded`),
  // a checkpoint as a spreadsheet: the download is a plain link (see
  // sheetUrl); the upload returns the decisions the screen then stages
  sheetUrl: (runId: string, cpId: string) => `/api/runs/${runId}/checkpoints/${cpId}/sheet.xlsx`,
  importSheet: async (runId: string, cpId: string, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`/api/runs/${runId}/checkpoints/${cpId}/sheet`, withToken({ method: 'POST', body: fd }))
    if (!res.ok) {
      if (reloadIfStaleToken(res)) return new Promise<SheetImport>(() => { /* reloading */ })
      throw new Error(await errText(res))
    }
    return res.json() as Promise<SheetImport>
  },
  checkUpdates: () =>
    j<{ ok: boolean; error?: string; current?: string; release?: string; tag?: string; build?: string;
        newer?: boolean; has_bundle?: boolean; release_url?: string; note?: string }>(
      '/api/settings/check_updates', post()),
  dismissUpdateHint: () => j<{ ok: boolean }>('/api/settings/dismiss_update_hint', post()),
  installUpdate: () =>
    j<{ ok: boolean; from_version: string; to_version: string; files_installed: number;
        backup: string; restart_required?: boolean; note?: string }>('/api/settings/install_update', post()),
}

export const statusLabel = (s: string) =>
  s ? s.charAt(0).toUpperCase() + s.slice(1).replaceAll('_', ' ') : s

// The human names of things the API names by id.
export const METHOD_LABELS: Record<string, string> = {
  grounded_theory: 'Grounded Theory',
  thematic: 'Thematic Analysis',
  content_analysis: 'Content Analysis',
  framework: 'Framework / Deductive',
  literature_synthesis: 'Literature Synthesis',
}
export const methodLabel = (id: string) => METHOD_LABELS[id] ?? id.replaceAll('_', ' ')

// "3 Sep 2026, 8:11 AM" — no seconds in a heading
export const dateLabel = (ts: number) =>
  new Date(ts * 1000).toLocaleString(undefined,
    { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
export const dayLabel = (ts: number) =>
  new Date(ts * 1000).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })

// The size of a source as a reader thinks of it: "about 2,100 words"
export const sizeLabel = (chars: number) =>
  chars > 0 ? `about ${Math.max(1, Math.round(chars / 6)).toLocaleString()} words` : ''

// A recorded setting, as prose: booleans as words, never "true"
export const settingValue = (v: unknown): string => {
  if (v === true || v === 'true') return 'Yes'
  if (v === false || v === 'false') return 'No'
  return String(v ?? '').trim()
}

export async function testKey(provider: string, model?: string, key?: string) {
  try {
    return await j<{ ok: boolean; reply?: string; error?: string }>(
      '/api/settings/test_key', post({ provider, model, key }))
  } catch (e: any) {
    return { ok: false, error: String(e.message ?? e) }
  }
}
