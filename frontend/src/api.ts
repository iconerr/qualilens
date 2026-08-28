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
export interface Meta { methods: MethodMeta[]; providers: ProviderMeta[]; ffmpeg: boolean; version?: string }

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
export interface Run extends RunSummary {
  project_id: string; project_name: string;
  stages: { name: string; label: string; kind: string }[];
  pending_checkpoint: Checkpoint | null; has_report: boolean;
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) throw new Error(await errText(res))
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
    const res = await fetch(`/api/projects/${projectId}/sources`, { method: 'POST', body: fd })
    if (!res.ok) throw new Error(await errText(res))
    return res.json() as Promise<Source>
  },
  deleteSource: (id: string) => j(`/api/sources/${id}`, { method: 'DELETE' }),
  retrySource: (id: string) => j(`/api/sources/${id}/retry`, post()),
  sourceText: (id: string) => j<{ filename: string; text: string }>(`/api/sources/${id}/text`),
  estimate: (projectId: string) =>
    j<{ n_sources: number; total_chars: number; est_input_tokens: number;
        est_output_tokens: number; est_cost_usd: number; note: string }>(`/api/projects/${projectId}/estimate`),
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
  applyUpdate: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/settings/update', { method: 'POST', body: fd })
    if (!res.ok) throw new Error(await errText(res))
    return res.json() as Promise<{ ok: boolean; from_version: string; to_version: string;
      files_installed: number; backup: string; restart_required?: boolean }>
  },
  codedSource: (runId: string, sourceId: string) =>
    j<CodedSource>(`/api/runs/${runId}/sources/${sourceId}/coded`),
  checkUpdates: () =>
    j<{ ok: boolean; error?: string; current?: string; tag?: string; build?: string;
        newer?: boolean; has_bundle?: boolean; release_url?: string; note?: string }>(
      '/api/settings/check_updates', post()),
  installUpdate: () =>
    j<{ ok: boolean; from_version: string; to_version: string; files_installed: number;
        backup: string; restart_required?: boolean }>('/api/settings/install_update', post()),
}

export const statusLabel = (s: string) =>
  s ? s.charAt(0).toUpperCase() + s.slice(1).replaceAll('_', ' ') : s

export async function testKey(provider: string, model?: string, key?: string) {
  try {
    return await j<{ ok: boolean; reply?: string; error?: string }>(
      '/api/settings/test_key', post({ provider, model, key }))
  } catch (e: any) {
    return { ok: false, error: String(e.message ?? e) }
  }
}
