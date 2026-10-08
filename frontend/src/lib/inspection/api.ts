// «نظارت و سرکشی» — the browser's client for /api/inspection.
//
// This app has no login: the owner is whoever uses the UI, and the supervisor
// is a Claude Code Routine that sends its own token from a script — never from
// a browser. So nothing here carries credentials.
//
// Uploads follow the house pattern that survives Cloudflare
// (experiences/cloudflare-403-on-chunked-cross-origin-post.md and
// components/TaskFilePicker.tsx): open a session, append octet-stream pieces
// by offset (resumable), finish.
import type { SpotGeometry, UiSpot } from './spot'
import type { NextRound } from './nextRound'

export function apiBase(): string {
  const w = typeof window !== 'undefined'
    ? (window as unknown as { __NEXT_PUBLIC_API_URL__?: string }).__NEXT_PUBLIC_API_URL__
    : undefined
  return (process.env.NEXT_PUBLIC_API_URL || w || 'http://localhost:8000').replace(/\/+$/, '')
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function detailOf(body: unknown, status: number): string {
  const d = (body as { detail?: unknown })?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => (x as { msg?: string })?.msg || JSON.stringify(x)).join(' · ')
  if (d && typeof d === 'object') return (d as { message?: string }).message || JSON.stringify(d)
  return `خطای سرور (${status})`
}

async function call<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${apiBase()}/api/inspection${path}`, {
      method: opts.method || (opts.body !== undefined ? 'POST' : 'GET'),
      headers: opts.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    })
  } catch {
    throw new ApiError('ارتباط با سرور برقرار نشد — اتصال یا بیدار شدنِ سرور را بررسی کن', 0)
  }
  const text = await res.text()
  let data: unknown = null
  try { data = text ? JSON.parse(text) : null } catch { data = { detail: text.slice(0, 200) } }
  if (!res.ok) throw new ApiError(detailOf(data, res.status), res.status)
  return data as T
}

export const errorText = (e: unknown): string =>
  e instanceof Error ? e.message : String(e)

// ---------------------------------------------------------------------------
// types
// ---------------------------------------------------------------------------
export type Dependency = { name: string; status: string; note?: string }

export type InspectionNote = {
  id: string
  by: 'owner' | 'reviewer'
  at: string
  text: string
  author?: string
  shot_id?: string | null
  after_shot_id?: string | null
  outcome?: string | null
  commits?: string[]
  edited_at?: string
  original_text?: string
  spot?: Partial<UiSpot> & { geometry?: SpotGeometry | null }
}

export type InspectionFile = {
  id: string
  report_id: string
  note_id: string
  ref: string
  filename: string
  mime: string
  byte_size: number
  size_label: string
  caption: string
  created_at: string | null
  store: string
  store_note: string
  durable: boolean
  drive_link: string
  drive_path: string
  drive_folder_link: string
  text_drive_link: string
  extract_status: string
  extract_label: string
  extract_note: string
  text_chars: number
  page_count: number
  text_truncated: boolean
  read_chars: number
  read_percent: number | null
  fully_read: boolean
  read_at: string | null
  read_by: string
  viewed_at: string | null
}

export type ShotInfo = { ref: string; kind: string; store: string; store_note: string; drive_link: string; byte_size: number }

export type InspectionReport = {
  id: string
  number: number
  ref: string
  kind: 'spot' | 'general'
  created_at: string | null
  updated_at: string | null
  status: 'open' | 'answered' | 'approved' | 'filed'
  title: string
  page: string
  page_label: string
  section_id: string
  section_label: string
  reopen: string
  url: string
  dom_path: string
  covered_text: string
  geometry: SpotGeometry | null
  notes: InspectionNote[]
  dependencies: Dependency[]
  glow: { key: string; label: string; tone: string; outcome?: string }
  urgent: boolean
  urgent_at: string | null
  urgent_done_at: string | null
  urgent_in_progress: boolean
  urgent_claim_expires_at: string | null
  files: InspectionFile[]
  read_debt: { file_id: string; filename: string; reason: string; remaining: number }[]
  shots: Record<string, ShotInfo>
  binder: { id: string; number: number; page: number } | null
  filed_at: string | null
}

export type ListResult = {
  reports: InspectionReport[]
  counts: Record<string, number>
  general_open: number
  urgent_waiting: number
}

export type DriveStatus = {
  client_configured: boolean
  client_id: string | null
  connected: boolean
  source: 'env' | 'app' | null
  broken: boolean
  account: string | null
  connected_at: string | null
  root_folder: string
  root_folder_link: string | null
  inspection_folder_link: string | null
  scope: string
  missing: string[]
}

export type Usage = { count: number; bytes: number; label: string }
export type StorageStatus = {
  drive: DriveStatus
  usage: {
    files: Record<string, Usage>
    shots: Record<string, Usage>
    spool: { bytes: number; files: number; label: string; limit_mb: number }
    max_file_mb: number
  }
}

export type SurfaceSummary = {
  id: string
  route: string
  tab: string
  label: string
  title: string
  sample_path: string
  source_file: string
  declared: boolean
  first_seen: string | null
  last_seen: string | null
  seen_by: string
  visits: number
  counts: Record<string, number>
  new_count: number
  removed_count: number
  open_reports?: number
  viewport: { w: number; h: number } | null
  doc_size: { w: number; h: number } | null
}

export type SurfaceElement = {
  kind: string
  label: string
  selector: string
  section: string
  rect: { x: number; y: number; w: number; h: number }
  href?: string
}

export type Schedule = {
  urgent: { cron_utc: string; next_round: NextRound; prompt: string }
  full: { cron_utc: string; last_seen: string | null; prompt: string; next_at: string | null }
  archive: string
}

// ---------------------------------------------------------------------------
// calls
// ---------------------------------------------------------------------------
export const inspectionApi = {
  list: (q: { status?: string; include_filed?: boolean; kind?: string; page?: string } = {}) => {
    const p = new URLSearchParams()
    if (q.status) p.set('status', q.status)
    if (q.include_filed) p.set('include_filed', 'true')
    if (q.kind) p.set('kind', q.kind)
    if (q.page) p.set('page', q.page)
    const s = p.toString()
    return call<ListResult>(s ? `?${s}` : '')
  },
  get: (id: string) => call<{ report: InspectionReport }>(`/${id}`),
  create: (body: { text: string; kind?: 'spot' | 'general'; spot?: Partial<UiSpot>; shot?: string | null; urgent?: boolean }) =>
    call<{ report: InspectionReport }>('', { body }),
  note: (id: string, body: { text: string; shot?: string | null; spot?: Partial<UiSpot> | null; file_ids?: string[] }) =>
    call<{ report: InspectionReport }>(`/${id}/notes`, { body }),
  editNote: (id: string, noteId: string, text: string) =>
    call<{ report: InspectionReport }>(`/${id}/notes/${noteId}`, { method: 'PATCH', body: { text } }),
  setStatus: (id: string, status: 'open' | 'approved') =>
    call<{ report: InspectionReport }>(`/${id}/status`, { body: { status } }),
  remove: (id: string) => call<{ ok: boolean }>(`/${id}`, { method: 'DELETE' }),
  rush: (id: string) => call<{ position: number; next_round: NextRound }>(`/${id}/urgent`, { method: 'POST' }),
  unrush: (id: string) => call<{ ok: boolean }>(`/${id}/urgent`, { method: 'DELETE' }),
  urgentQueue: () => call<{ waiting: number; next_round: NextRound }>('/urgent'),
  schedule: () => call<Schedule>('/schedule'),
  binders: () => call<{ binders: { id: string; number: number; label: string; subtitle: string; opened_at: string | null;
    closed_at: string | null; capacity: number; count: number;
    pages: { page: number; report_id: string; number: number; title: string }[] }[] }>('/binders'),
  fileText: (fileId: string, offset = 0) =>
    call<{ text: string; has_more: boolean; next_offset: number | null; text_chars: number }>(
      `/files/${fileId}/text?offset=${offset}`),
  removeFile: (fileId: string) => call<{ ok: boolean }>(`/files/${fileId}`, { method: 'DELETE' }),
  storage: () => call<StorageStatus>('/storage'),
  connectDrive: (body: { code?: string; refresh_token?: string }) =>
    call<StorageStatus>('/storage/drive/connect', { body }),
  disconnectDrive: () => call<StorageStatus>('/storage/drive/disconnect', { method: 'POST' }),
  syncDrive: () => call<StorageStatus & { result: Record<string, number | boolean> }>('/storage/sync', { method: 'POST' }),
  surfaces: () => call<{ surfaces: SurfaceSummary[]; inventory: Record<string, unknown> | null }>('/surfaces'),
  surface: (id: string) => call<{ surface: SurfaceSummary & { elements: SurfaceElement[]; new_keys: string[]; removed_keys: string[] } }>(`/surfaces/${id}`),
  registerSurface: (body: unknown) => call<{ ok: boolean; new: number }>('/surfaces', { body }),
  shotUrl: (id: string) => `${apiBase()}/api/inspection/shots/${id}`,
  rawUrl: (fileId: string) => `${apiBase()}/api/inspection/files/${fileId}/raw`,
}

// ---------------------------------------------------------------------------
// chunked upload — any type, resumable, octet-stream pieces
// ---------------------------------------------------------------------------
export async function uploadFile(
  reportId: string,
  file: File,
  opts: { caption?: string; noteId?: string; onProgress?: (pct: number) => void } = {},
): Promise<InspectionFile> {
  const start = await call<{ upload_id: string; chunk_size: number }>(`/${reportId}/intake/start`, {
    body: { filename: file.name, mime: file.type || 'application/octet-stream', size: file.size,
            caption: opts.caption || '', note_id: opts.noteId || '' },
  })
  const id = start.upload_id
  const step = start.chunk_size || 4 * 1024 * 1024
  let offset = 0
  let attempts = 0
  while (offset < file.size) {
    const piece = file.slice(offset, Math.min(offset + step, file.size))
    let res: Response | null = null
    try {
      res = await fetch(`${apiBase()}/api/inspection/intake/${id}/append?offset=${offset}`, {
        method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: piece,
      })
    } catch { res = null }
    if (res && res.ok) {
      const j = await res.json()
      offset = Number(j.next_offset)
      attempts = 0
      opts.onProgress?.(Math.round((100 * offset) / file.size))
      continue
    }
    // resync on an offset mismatch, otherwise back off and retry a few times
    if (res && res.status === 409) {
      const j = await res.json().catch(() => ({}))
      const exp = (j as { detail?: { expected_offset?: number } })?.detail?.expected_offset
      if (typeof exp === 'number') { offset = exp; continue }
    }
    attempts += 1
    if (attempts >= 4) {
      await call(`/intake/${id}`, { method: 'DELETE' }).catch(() => undefined)
      throw new ApiError(`آپلودِ «${file.name}» قطع شد${res ? ` (HTTP ${res.status})` : ''}`, res?.status || 0)
    }
    await new Promise((r) => setTimeout(r, 1500 * attempts))
  }
  const fin = await call<{ file: InspectionFile }>(`/intake/${id}/finish`, { method: 'POST' })
  return fin.file
}
