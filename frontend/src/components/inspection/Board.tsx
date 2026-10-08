'use client'
// «نظارت و سرکشی» — the board. Ported from ALLIN1 (`frontend/src/app/inspection/
// page.tsx`, read-only reference).
//
// Every sheet the owner filed, what the supervisor answered, the dependency walk
// behind that answer, and the tick. The CARD colour is whose turn it is
// (amber = waiting for the supervisor or asked again · green = answered ·
// blue = ticked by the owner, filed next round · grey = archived); the BADGE is
// what actually happened (fixed / partial / not-done / needs-owner) — derived
// from the outcome, never from the mere fact that somebody replied.
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  errorText, inspectionApi, uploadFile,
  type InspectionFile, type InspectionReport,
} from '@/lib/inspection/api'
import { geometryLabel } from '@/lib/inspection/spot'
import { notifySheetsChanged } from '@/lib/inspection/highlights'
import { everyText, humanGap, localClock, rushMessage, type NextRound } from '@/lib/inspection/nextRound'
import { shrinkShot } from '@/lib/inspection/shrinkShot'
import { toast } from '@/lib/inspection/toast'
import { TONE } from '@/lib/inspection/provider'

const FA = '۰۱۲۳۴۵۶۷۸۹'
export const fa = (n: number | string) => String(n).replace(/[0-9]/g, (d) => FA[+d])

const FILTERS: { key: string; label: string }[] = [
  { key: 'open', label: 'در انتظارِ ناظر' },
  { key: 'answered', label: 'ناظر پاسخ داد' },
  { key: 'approved', label: 'تأییدشده' },
  { key: 'filed', label: 'بایگانی' },
  { key: '', label: 'همه' },
]

/** The card's frame — whose turn it is. */
export const STATUS_FRAME: Record<string, string> = {
  open: 'border-amber-300 bg-amber-50/40 dark:border-amber-700 dark:bg-amber-900/10',
  answered: 'border-emerald-300 bg-emerald-50/40 dark:border-emerald-700 dark:bg-emerald-900/10',
  approved: 'border-blue-300 bg-blue-50/40 dark:border-blue-700 dark:bg-blue-900/10',
  filed: 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/60',
}
const STATUS_BAR: Record<string, string> = {
  open: 'bg-amber-500', answered: 'bg-emerald-500', approved: 'bg-blue-600', filed: 'bg-gray-400',
}

type FileRow = { kind: 'head'; key: string; label: string } | { kind: 'file'; f: InspectionFile }

function groupFiles(r: InspectionReport): FileRow[] {
  const files = r.files || []
  const own = files.filter((f) => !f.note_id)
  const byNote = new Map<string, InspectionFile[]>()
  for (const f of files) if (f.note_id) byNote.set(f.note_id, [...(byNote.get(f.note_id) || []), f])
  const rows: FileRow[] = []
  const labelled = byNote.size > 0
  if (own.length) {
    if (labelled) rows.push({ kind: 'head', key: 'own', label: 'همراهِ خودِ گزارش' })
    for (const f of own) rows.push({ kind: 'file', f })
  }
  for (const [nid, items] of Array.from(byNote.entries())) {
    const i = (r.notes || []).findIndex((n) => n.id === nid)
    rows.push({ kind: 'head', key: nid, label: i >= 0 ? `همراهِ یادداشتِ ${fa(i + 1)}` : 'همراهِ یک یادداشت' })
    for (const f of items) rows.push({ kind: 'file', f })
  }
  return rows
}

const PAGE_SIZES = [5, 10, 20, 50, 100]

export default function Board({ kind, onCounts }: {
  kind?: 'general'
  onCounts?: (c: { open: number; general: number; urgent: number }) => void
}) {
  const [reports, setReports] = useState<InspectionReport[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [filter, setFilter] = useState('')
  const [busy, setBusy] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)
  const [reply, setReply] = useState('')
  const [replyFiles, setReplyFiles] = useState<File[]>([])
  const [replyShot, setReplyShot] = useState<string | null>(null)
  const [replyUrgent, setReplyUrgent] = useState(false)
  const [sending, setSending] = useState(false)
  const [upPct, setUpPct] = useState<{ id: string; name: string; pct: number } | null>(null)
  const [peek, setPeek] = useState<{ file: InspectionFile; text: string; loading: boolean } | null>(null)
  const [editing, setEditing] = useState<{ noteId: string; text: string } | null>(null)
  const [nextRound, setNextRound] = useState<NextRound | null>(null)
  const [tick, setTick] = useState(0)
  const [pageSize, setPageSize] = useState(10)
  const [page, setPage] = useState(1)
  const [zoom, setZoom] = useState<string | null>(null)
  // kept in a ref: a parent passing an inline callback must not re-trigger loading
  const countsCb = useRef(onCounts)
  countsCb.current = onCounts

  useEffect(() => {
    try {
      const v = Number(localStorage.getItem('pm.inspection.pageSize'))
      if (PAGE_SIZES.includes(v)) setPageSize(v)
    } catch { /* storage unavailable */ }
  }, [])
  useEffect(() => { setPage(1) }, [filter, pageSize])
  const pageCount = Math.max(1, Math.ceil(reports.length / pageSize))
  const curPage = Math.min(page, pageCount)
  const pageReports = useMemo(() => reports.slice((curPage - 1) * pageSize, curPage * pageSize),
    [reports, curPage, pageSize])

  const load = useCallback(async () => {
    setBusy(true)
    try {
      const d = await inspectionApi.list({ include_filed: true, status: filter || undefined, kind })
      setReports(d.reports)
      setCounts(d.counts || {})
      countsCb.current?.({ open: d.counts?.open || 0, general: d.general_open || 0, urgent: d.urgent_waiting || 0 })
      notifySheetsChanged()
      try { setNextRound((await inspectionApi.urgentQueue()).next_round ?? null) } catch { /* courtesy */ }
    } catch (e) { toast.error(errorText(e)) } finally { setBusy(false) }
  }, [filter, kind])
  useEffect(() => { void load() }, [load])
  useEffect(() => {
    const t = window.setInterval(() => setTick((n) => n + 1), 30_000)
    return () => window.clearInterval(t)
  }, [])
  // a sheet filed from the capture dialog on another page shows up here at once
  useEffect(() => {
    const again = () => void load()
    window.addEventListener('pm:inspection-filed', again)
    return () => window.removeEventListener('pm:inspection-filed', again)
  }, [load])

  const approve = async (r: InspectionReport) => {
    try {
      await inspectionApi.setStatus(r.id, r.status === 'approved' ? 'open' : 'approved')
      toast.success(r.status === 'approved' ? 'تأیید برداشته شد' : 'تأیید ثبت شد (آبی) — دورِ بعدِ ناظر بایگانی‌اش می‌کند')
      await load()
    } catch (e) { toast.error(errorText(e)) }
  }
  const remove = async (r: InspectionReport) => {
    if (!window.confirm(`گزارشِ ${fa(r.number)} حذف شود؟ (فایل‌هایش در درایو به «سطلِ حذف‌شده» می‌روند، پاک نمی‌شوند)`)) return
    try { await inspectionApi.remove(r.id); await load() } catch (e) { toast.error(errorText(e)) }
  }

  const resetReply = () => { setReply(''); setReplyFiles([]); setReplyShot(null); setReplyUrgent(false) }

  /** A follow-up UNDER this sheet — its own text, its own pasted picture, its own
   *  files (claimed by this note, never mixed with the earlier ones). */
  const addNote = async (r: InspectionReport) => {
    if (!reply.trim() || sending) return
    setSending(true)
    try {
      const ids: string[] = []
      const failed: string[] = []
      for (const f of replyFiles) {
        try {
          setUpPct({ id: r.id, name: f.name, pct: 0 })
          ids.push((await uploadFile(r.id, f, { onProgress: (pct) => setUpPct({ id: r.id, name: f.name, pct }) })).id)
        } catch (e) { failed.push(`${f.name} (${errorText(e)})`) }
      }
      setUpPct(null)
      await inspectionApi.note(r.id, { text: reply.trim(), shot: replyShot, file_ids: ids })
      let extra = ''
      if (replyUrgent && !r.urgent) {
        try {
          const rr = await inspectionApi.rush(r.id)
          extra = ' · ' + rushMessage(rr.position, rr.next_round)
        } catch { /* the note is in */ }
      }
      if (failed.length) toast.error(`یادداشت ثبت شد ولی این فایل‌ها بالا نرفتند: ${failed.join(' · ')}`)
      else toast.success(<span dir="rtl">نوشته شد — این برگه دوباره در صفِ ناظر است (نارنجی){extra}</span>)
      resetReply()
      await load()
    } catch (e) { toast.error(errorText(e)) } finally { setSending(false); setUpPct(null) }
  }

  const attach = useCallback(async (r: InspectionReport, files: File[]) => {
    for (const f of files) {
      try {
        setUpPct({ id: r.id, name: f.name, pct: 0 })
        await uploadFile(r.id, f, { onProgress: (pct) => setUpPct({ id: r.id, name: f.name, pct }) })
        toast.success(`«${f.name}» پیوست شد — ناظر باید کاملش را بخواند`)
      } catch (e) { toast.error(`${f.name}: ${errorText(e)}`) }
    }
    setUpPct(null)
    await load()
  }, [load])

  const rush = useCallback(async (r: InspectionReport) => {
    try {
      if (r.urgent) {
        await inspectionApi.unrush(r.id)
        toast.success('از صفِ فوری بیرون آمد')
      } else {
        const { position, next_round } = await inspectionApi.rush(r.id)
        toast.success(<span dir="rtl">{rushMessage(position, next_round)}</span>, { duration: 8000 })
      }
      await load()
    } catch (e) { toast.error(errorText(e)) }
  }, [load])

  const saveEdit = useCallback(async (r: InspectionReport, noteId: string) => {
    const text = (editing?.text || '').trim()
    if (!text) return
    try {
      await inspectionApi.editNote(r.id, noteId, text)
      toast.success('ویرایش ذخیره شد — متنِ اولیه هم نگه داشته شد')
      setEditing(null)
      await load()
    } catch (e) { toast.error(errorText(e)) }
  }, [editing, load])

  const dropFile = useCallback(async (f: InspectionFile) => {
    if (!window.confirm(`«${f.filename}» از این برگه برداشته شود؟ (نسخهٔ درایو به «سطلِ حذف‌شده» می‌رود)`)) return
    try { await inspectionApi.removeFile(f.id); toast.success('برداشته شد'); await load() }
    catch (e) { toast.error(errorText(e)) }
  }, [load])

  const openPeek = useCallback(async (f: InspectionFile) => {
    setPeek({ file: f, text: '', loading: true })
    try {
      let out = ''
      let offset = 0
      for (let guard = 0; guard < 400; guard++) {
        const got = await inspectionApi.fileText(f.id, offset)
        out += got.text
        if (!got.has_more || got.next_offset === null) break
        offset = got.next_offset
      }
      setPeek({ file: f, text: out, loading: false })
    } catch (e) { toast.error(errorText(e)); setPeek(null) }
  }, [])

  const onReplyPaste = useCallback((e: React.ClipboardEvent) => {
    const item = Array.from(e.clipboardData?.items || []).find((i) => i.type.startsWith('image/'))
    const file = item?.getAsFile()
    if (!file) return
    e.preventDefault()
    const fr = new FileReader()
    fr.onload = () => { void shrinkShot(String(fr.result || '')).then(setReplyShot) }
    fr.readAsDataURL(file)
  }, [])

  // WATCH THE FAST QUEUE, and say what happened (only while something is rushed).
  const watching = useMemo(() => reports.filter((r) => r.urgent).map((r) => r.id).join(','), [reports])
  const seen = useRef<Record<string, string>>({})
  const [done, setDone] = useState<{ number: number; title: string; label: string }[]>([])
  useEffect(() => {
    for (const r of reports) if (r.urgent || r.urgent_done_at) seen.current[r.id] = `${r.status}|${r.notes?.length || 0}`
  }, [reports])
  useEffect(() => {
    if (!watching) return
    let alive = true
    const poll = async () => {
      try {
        const d = await inspectionApi.list({ include_filed: true, status: filter || undefined, kind })
        if (!alive) return
        const changed: { number: number; title: string; label: string }[] = []
        for (const r of d.reports) {
          const before = seen.current[r.id]
          const now = `${r.status}|${r.notes?.length || 0}`
          if (before && before !== now && (r.urgent_done_at || r.status === 'answered')) {
            changed.push({ number: r.number, title: r.title || '', label: r.glow?.label || r.status })
          }
          seen.current[r.id] = now
        }
        setReports(d.reports)
        setCounts(d.counts || {})
        if (changed.length) { setDone((prev) => [...changed, ...prev].slice(0, 5)); notifySheetsChanged() }
      } catch { /* offline — the next tick tries again */ }
    }
    const t = window.setInterval(poll, 20_000)
    const onFocus = () => void poll()
    window.addEventListener('focus', onFocus)
    return () => { alive = false; window.clearInterval(t); window.removeEventListener('focus', onFocus) }
  }, [watching, filter, kind])

  const summary = { open: counts.open || 0, answered: counts.answered || 0,
                    approved: counts.approved || 0, filed: counts.filed || 0 }

  return (
    <div dir="rtl" className="space-y-4">
      {!!done.length && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 dark:bg-emerald-900/30">
          <div className="flex items-start gap-2">
            <span className="text-lg leading-none">⚡</span>
            <div className="flex-1 text-[13px] text-emerald-900 dark:text-emerald-100">
              <div className="font-semibold">ناظر روی موردهای فوری کار کرد:</div>
              <ul className="mt-1 space-y-0.5">
                {done.map((d) => (
                  <li key={d.number}>گزارشِ {fa(d.number)}{d.title ? ` — ${d.title}` : ''}
                    <span className="opacity-75"> · {d.label}</span></li>
                ))}
              </ul>
              <div className="mt-1 text-[11px] opacity-75">صفحه خودش به‌روز شد — بازش کن و ببین.</div>
            </div>
            <button onClick={() => setDone([])} title="بستن" className="rounded p-1 hover:bg-emerald-100">✕</button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`rounded-lg px-3 py-1 text-xs ${filter === f.key
                ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                : 'border border-gray-300 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700'}`}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {nextRound && <NextRoundChip nr={nextRound} tick={tick} />}
          <button onClick={() => void load()} disabled={busy}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-60 dark:border-gray-600 dark:hover:bg-gray-700">
            {busy ? '…' : '↻ تازه‌سازی'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {([['open', 'در انتظارِ ناظر', 'border-amber-200 bg-amber-50 text-amber-800'],
           ['answered', 'ناظر پاسخ داد', 'border-emerald-200 bg-emerald-50 text-emerald-800'],
           ['approved', 'تأییدِ تو (آبی)', 'border-blue-200 bg-blue-50 text-blue-800'],
           ['filed', 'بایگانی', 'border-gray-200 bg-gray-50 text-gray-700']] as const).map(([k, label, cls]) => (
          <button key={k} onClick={() => setFilter(k)} className={`rounded-xl border p-3 text-center ${cls}`}>
            <div className="text-2xl font-bold">{fa(summary[k])}</div>
            <div className="text-[11px]">{label}</div>
          </button>
        ))}
      </div>

      {!reports.length && !busy && (
        <div className="rounded-xl border border-dashed border-gray-300 p-10 text-center text-sm text-gray-500 dark:border-gray-600">
          {kind === 'general'
            ? 'هنوز درخواستِ عمومی‌ای ثبت نشده. از فرمِ بالا بنویس.'
            : 'هنوز گزارشی اینجا نیست. «📝 ثبتِ گزارش» را در منو روشن کن، برو هر جای برنامه که ایراد دیدی، و دورش کادر بکش.'}
        </div>
      )}

      {reports.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
          <label className="flex items-center gap-1">تعداد در هر صفحه
            <select value={pageSize} className="rounded border border-gray-300 bg-transparent px-1 py-[2px] dark:border-gray-600"
              onChange={(e) => {
                const v = Number(e.target.value)
                setPageSize(v)
                try { localStorage.setItem('pm.inspection.pageSize', String(v)) } catch { /* ignore */ }
              }}>
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <span>· {fa(reports.length)} گزارش · صفحهٔ {fa(curPage)} از {fa(pageCount)}</span>
          <button disabled={curPage <= 1} onClick={() => setPage(curPage - 1)}
            className="rounded border border-gray-300 px-2 py-[2px] disabled:opacity-40 dark:border-gray-600">قبلی</button>
          <button disabled={curPage >= pageCount} onClick={() => setPage(curPage + 1)}
            className="rounded border border-gray-300 px-2 py-[2px] disabled:opacity-40 dark:border-gray-600">بعدی</button>
        </div>
      )}

      <div className="space-y-3">
        {pageReports.map((r) => {
          const expanded = openId === r.id
          const lastReviewer = [...(r.notes || [])].reverse().find((n) => n.by === 'reviewer')
          return (
            <div key={r.id} id={`sheet-${r.number}`}
              className={`relative overflow-hidden rounded-xl border p-4 pr-5 ${STATUS_FRAME[r.status] || ''}`}>
              <span className={`absolute inset-y-0 right-0 w-1.5 ${STATUS_BAR[r.status] || 'bg-gray-300'}`} />
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded px-2 py-[2px] text-[11px] text-white ${TONE[r.glow?.tone] || 'bg-gray-500'}`}>
                      {r.glow?.label}
                    </span>
                    {r.kind === 'general' && (
                      <span className="rounded bg-gray-800 px-2 py-[2px] text-[11px] text-white">درخواستِ عمومی</span>
                    )}
                    <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      گزارشِ {fa(r.number)} — {r.title}
                    </span>
                    <span className="text-[10px] text-gray-400" dir="ltr">{r.ref}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                    {r.page_label}{r.section_label ? ` ← ${r.section_label}` : ''}
                    {r.kind !== 'general' && (<>{' · '}
                      <a href={r.url || r.page} className="text-blue-600 hover:underline">رفتن به همان‌جا ↗</a></>)}
                    {r.binder && <> · زونکنِ {fa(r.binder.number)}، برگهٔ {fa(r.binder.page)}</>}
                    {r.created_at && <> · {new Date(r.created_at).toLocaleString('fa-IR')}</>}
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {r.status !== 'filed' && r.status !== 'approved' && (
                    <button onClick={() => void rush(r)}
                      title={r.urgent ? 'در صفِ فوری است — برای بیرون‌آوردن بزن' : 'ناظر خارج از نوبت سراغش برود'}
                      className={`rounded-lg px-2.5 py-1 text-xs ${r.urgent
                        ? 'bg-orange-600 text-white hover:bg-orange-700'
                        : 'border border-orange-300 text-orange-700 hover:bg-orange-50 dark:text-orange-300'}`}>
                      {r.urgent ? (r.urgent_in_progress ? '⚡ در دستِ ناظر' : '⚡ در صفِ فوری') : '⚡ فوری'}
                    </button>
                  )}
                  {!!r.urgent_done_at && !r.urgent && (
                    <span className="rounded-lg bg-emerald-50 px-2 py-1 text-[11px] text-emerald-700">⚡ جواب گرفت</span>
                  )}
                  <button onClick={() => { setOpenId(expanded ? null : r.id); resetReply(); setEditing(null) }}
                    className="rounded-lg border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700">
                    {expanded ? 'بستن' : 'جزئیات'}
                  </button>
                  {r.status !== 'filed' && (
                    <button onClick={() => void approve(r)} title="تأیید — فقط دستِ توست"
                      className={`rounded-lg px-2.5 py-1 text-xs ${r.status === 'approved'
                        ? 'bg-blue-600 text-white' : 'border border-blue-300 text-blue-700 hover:bg-blue-50 dark:text-blue-300'}`}>
                      ✓ {r.status === 'approved' ? 'تأییدشده' : 'تأیید'}
                    </button>
                  )}
                  <button onClick={() => void remove(r)} title="حذف"
                    className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50">🗑</button>
                </div>
              </div>

              {!expanded && lastReviewer && (
                <div className="mt-2 line-clamp-2 rounded-lg bg-white/70 p-2 text-[12px] text-gray-700 dark:bg-gray-900/40 dark:text-gray-300">
                  🤖 {lastReviewer.text}
                </div>
              )}

              {expanded && (
                <div className="mt-3 space-y-3 border-t border-gray-200 pt-3 dark:border-gray-700">
                  {r.kind !== 'general' && (
                    <div className="rounded-lg bg-white/80 p-2 text-[11px] text-gray-600 dark:bg-gray-900/40 dark:text-gray-300">
                      <div><b>نشانیِ دقیق:</b> <span dir="ltr">{r.reopen}</span></div>
                      {!!r.geometry && (
                        <>
                          <div><b>مختصات و ابعاد:</b> {geometryLabel(r.geometry)}{r.geometry.tab ? ` · زبانه: ${r.geometry.tab}` : ''}</div>
                          <div><b>گره:</b>{' '}
                            {r.geometry.anchor.path
                              ? <span dir="ltr" className="text-[11px]">{r.geometry.anchor.path}</span>
                              : 'به عنصری گره نخورد — فقط مختصاتِ سند'}
                          </div>
                        </>
                      )}
                      {!!r.covered_text && <div className="mt-1">آنچه در کادر بود: {r.covered_text}</div>}
                    </div>
                  )}

                  {r.notes?.map((n, i) => (
                    <div key={n.id} className={`rounded-lg border p-2.5 ${n.by === 'reviewer'
                      ? 'border-emerald-200 bg-emerald-50/60 dark:border-emerald-800 dark:bg-emerald-900/20'
                      : 'border-amber-200 bg-amber-50/60 dark:border-amber-800 dark:bg-amber-900/20'}`}>
                      <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px]">
                        <b>{n.by === 'reviewer' ? '🤖 ناظر' : '👤 تو'}</b>
                        <span className="text-gray-400">{fa(i + 1)} · {new Date(n.at).toLocaleString('fa-IR')}</span>
                        {n.outcome && (
                          <span className={`rounded px-1.5 text-[10px] text-white ${TONE[n.outcome] || 'bg-gray-500'}`}>{n.outcome}</span>
                        )}
                        {n.by === 'owner' && r.status !== 'filed' && editing?.noteId !== n.id && (
                          <button type="button" title="ویرایشِ همین متن"
                            onClick={() => setEditing({ noteId: n.id, text: n.text })}
                            className="text-gray-500 hover:text-gray-800">✏️</button>
                        )}
                        {!!n.edited_at && (
                          <span className="text-[10px] text-gray-400" title={n.original_text ? `متنِ اول: ${n.original_text}` : ''}>ویرایش شد</span>
                        )}
                        {!!n.spot?.page && n.spot.page !== r.page && (
                          <a href={n.spot.url || n.spot.page} className="text-[10px] text-blue-600 hover:underline">
                            کادرِ این یادداشت: {n.spot.page_label || n.spot.page} ↗</a>
                        )}
                      </div>
                      {editing?.noteId === n.id ? (
                        <div>
                          <textarea value={editing.text} rows={4} autoFocus dir="auto"
                            onChange={(e) => setEditing({ noteId: n.id, text: e.target.value })}
                            className="w-full rounded-lg border border-gray-300 bg-white p-2 text-[12.5px] dark:border-gray-600 dark:bg-gray-700" />
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <button type="button" disabled={!editing.text.trim()} onClick={() => void saveEdit(r, n.id)}
                              className="rounded-lg bg-gray-900 px-3 py-1 text-xs text-white disabled:opacity-50">ذخیرهٔ ویرایش</button>
                            <label className="cursor-pointer rounded-lg border border-dashed border-sky-300 px-2.5 py-1 text-xs text-sky-800 hover:bg-sky-50 dark:text-sky-300">
                              📎 پیوستِ فایل به همین گزارش
                              <input type="file" multiple className="hidden" onChange={(e) => {
                                const list = Array.from(e.target.files || [])
                                if (list.length) void attach(r, list)
                                e.target.value = ''
                              }} />
                            </label>
                            <button type="button" onClick={() => setEditing(null)} className="px-2 py-1 text-xs text-gray-600 hover:underline">انصراف</button>
                            <span className="text-[10px] text-gray-400">متنِ اولیه نگه داشته می‌شود</span>
                          </div>
                        </div>
                      ) : (
                        <div className="whitespace-pre-wrap text-[12.5px] text-gray-800 dark:text-gray-200" dir="auto">{n.text}</div>
                      )}
                      {!!n.commits?.length && (
                        <div dir="ltr" className="mt-1 text-[10px] text-gray-500">{n.commits.join(' · ')}</div>
                      )}
                      <div className="mt-2 flex flex-wrap gap-2">
                        {n.shot_id && <Shot r={r} id={n.shot_id} caption="چیزی که دیدی" onZoom={setZoom} />}
                        {n.after_shot_id && <Shot r={r} id={n.after_shot_id} caption="بعد از کارِ ناظر" after onZoom={setZoom} />}
                      </div>
                    </div>
                  ))}

                  <div className="rounded-lg border border-sky-200 bg-sky-50/50 p-2.5 dark:border-sky-800 dark:bg-sky-900/20">
                    <div className="mb-1.5 flex items-center gap-2 text-[11px] font-semibold text-sky-900 dark:text-sky-200">
                      📎 فایل‌ها {r.files?.length ? `(${fa(r.files.length)})` : ''}
                    </div>
                    {!r.files?.length && (
                      <div className="mb-1.5 text-[11px] text-gray-500">فایلی پیوست نشده. هر نوع فایلی می‌شود — ورد، PDF، عکس، اکسل، صوت، ویدئو…</div>
                    )}
                    <div className="space-y-1.5">
                      {groupFiles(r).map((row) => {
                        if (row.kind === 'head') return (
                          <div key={`h-${row.key}`} className="pt-1 text-[10px] font-semibold text-sky-800 dark:text-sky-300">{row.label}</div>
                        )
                        const f = row.f
                        return (
                          <div key={f.id} className="rounded-md border border-sky-100 bg-white px-2 py-1.5 text-[11px] dark:border-sky-900 dark:bg-gray-800">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="max-w-[16rem] truncate font-semibold text-gray-800 dark:text-gray-100">{f.filename}</span>
                              <span className="text-gray-400" dir="ltr">{f.ref}</span>
                              <span className="text-gray-400">{f.size_label}</span>
                              {f.extract_status === 'ok' ? (
                                <span className={f.fully_read ? 'text-emerald-700' : 'text-amber-700'}>
                                  {f.fully_read ? '✓ ناظر کاملش را خواند' : `ناظر ${fa(f.read_percent ?? 0)}٪ خوانده`}
                                </span>
                              ) : (
                                <span className={f.viewed_at ? 'text-emerald-700' : 'text-amber-700'}>
                                  {f.viewed_at ? '✓ باز شد' : 'ناظر هنوز بازش نکرده'}
                                </span>
                              )}
                              {f.durable
                                ? <span className="text-emerald-700" title={f.drive_path}>☁ در گوگل درایو</span>
                                : <span className="text-red-700" title={f.store_note}>⏳ هنوز در درایو نیست</span>}
                              <span className="flex-1" />
                              {f.extract_status === 'ok' && (
                                <button type="button" onClick={() => void openPeek(f)} className="text-sky-700 hover:underline">متن</button>
                              )}
                              <a href={inspectionApi.rawUrl(f.id)} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">باز کردن</a>
                              {!!f.drive_link && <a href={f.drive_link} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">درایو</a>}
                              {!!f.drive_folder_link && <a href={f.drive_folder_link} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">پوشه</a>}
                              {r.status !== 'filed' && (
                                <button type="button" onClick={() => void dropFile(f)} title="برداشتن" className="text-red-600 hover:underline">×</button>
                              )}
                            </div>
                            <div className="mt-0.5 text-gray-500">{f.extract_label}</div>
                            {!!f.extract_note && <div className="mt-0.5 text-gray-500">{f.extract_note}</div>}
                            {!f.durable && !!f.store_note && <div className="mt-0.5 text-red-700">{f.store_note}</div>}
                            {!!f.caption && <div className="mt-0.5 text-gray-700 dark:text-gray-300" dir="auto">توضیح: {f.caption}</div>}
                          </div>
                        )
                      })}
                    </div>
                    {r.status !== 'filed' && (
                      <label className="mt-1.5 flex cursor-pointer items-center gap-1.5 text-[11px] text-sky-800 hover:underline dark:text-sky-300">
                        📎 <span>پیوست کردنِ فایل به خودِ گزارش (هر نوعی)</span>
                        <input type="file" multiple className="hidden" onChange={(e) => {
                          const list = Array.from(e.target.files || [])
                          if (list.length) void attach(r, list)
                          e.target.value = ''
                        }} />
                      </label>
                    )}
                    {upPct?.id === r.id && <div className="mt-1 text-[11px] text-amber-800">{upPct.name} — {fa(upPct.pct)}٪</div>}
                    {!!r.read_debt?.length && (
                      <div className="mt-1.5 rounded-md bg-amber-100/70 px-2 py-1 text-[11px] text-amber-900">
                        ناظر تا این فایل‌ها را کامل نخواند نمی‌تواند برگه را جواب بدهد: {r.read_debt.map((d) => d.filename).join(' · ')}
                      </div>
                    )}
                  </div>

                  {!!r.dependencies?.length && (
                    <div className="rounded-lg border border-purple-200 bg-purple-50/50 p-2.5 dark:border-purple-800 dark:bg-purple-900/20">
                      <div className="mb-1 text-[11px] font-semibold text-purple-900 dark:text-purple-200">وابستگی‌هایی که ناظر بررسی کرد</div>
                      <ul className="space-y-0.5 text-[11.5px]">
                        {r.dependencies.map((d, i) => (
                          <li key={i} className="flex gap-1.5">
                            <span>{d.status === 'ok' ? '✅' : d.status === 'missing' ? '❌' : '⚠️'}</span>
                            <span dir="auto">{d.name}</span>
                            {!!d.note && <span className="text-gray-500">— {d.note}</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {r.status !== 'filed' && (
                    <div className="rounded-lg border border-gray-200 bg-white/80 p-2.5 dark:border-gray-700 dark:bg-gray-900/40">
                      <div className="mb-1 text-[11px] font-semibold">ثبتِ تازه ذیلِ همین گزارش</div>
                      <textarea value={reply} onChange={(e) => setReply(e.target.value)} onPaste={onReplyPaste} rows={3} dir="auto"
                        placeholder="یادداشتِ تازه (اسکرین‌شات را همین‌جا Ctrl+V کن). برای اصلاحِ خودِ متنِ گزارش، ✏️ کنارِ آن را بزن."
                        className="w-full rounded-lg border border-gray-300 bg-white p-2 text-sm dark:border-gray-600 dark:bg-gray-700" />
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <label className="cursor-pointer rounded-lg border border-dashed border-sky-300 px-2.5 py-1 text-xs text-sky-800 hover:bg-sky-50 dark:text-sky-300">
                          📎 فایلِ همین یادداشت
                          <input type="file" multiple className="hidden" onChange={(e) => {
                            const list = Array.from(e.target.files || [])
                            if (list.length) setReplyFiles((p) => [...p, ...list])
                            e.target.value = ''
                          }} />
                        </label>
                        {r.status !== 'approved' && !r.urgent && (
                          <label className="flex items-center gap-1 text-xs text-orange-700 dark:text-orange-300">
                            <input type="checkbox" checked={replyUrgent} onChange={(e) => setReplyUrgent(e.target.checked)} /> ⚡ فوری
                          </label>
                        )}
                        {replyShot && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={replyShot} alt="اسکرین‌شات" className="h-10 rounded border border-gray-300" />
                        )}
                        {replyShot && <button className="text-xs text-red-600" onClick={() => setReplyShot(null)}>× تصویر</button>}
                        <span className="flex-1" />
                        <button onClick={() => void addNote(r)} disabled={!reply.trim() || sending}
                          className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs text-white disabled:opacity-50 dark:bg-gray-100 dark:text-gray-900">
                          {sending ? '…' : 'افزودن به همین برگه'}
                        </button>
                      </div>
                      {!!replyFiles.length && (
                        <div className="mt-1 flex flex-wrap gap-1.5 text-[11px]">
                          {replyFiles.map((f, i) => (
                            <span key={`${f.name}-${i}`} className="rounded bg-gray-100 px-2 py-0.5 dark:bg-gray-700">
                              {f.name} <button className="text-red-600" onClick={() => setReplyFiles((p) => p.filter((_, j) => j !== i))}>×</button>
                            </span>
                          ))}
                          <span className="text-gray-500">— فقط مالِ همین یادداشت‌اند، با پیوست‌های قبلی قاتی نمی‌شوند</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {peek && (
        <div dir="rtl" className="fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setPeek(null) }}>
          <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-2xl dark:bg-gray-800">
            <div className="flex items-center gap-2 border-b border-gray-200 p-3 dark:border-gray-700">
              <span className="truncate text-sm font-bold">{peek.file.filename}</span>
              <span className="text-[11px] text-gray-500">{peek.file.size_label}</span>
              <span className="flex-1" />
              <button onClick={() => setPeek(null)} className="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-700">✕</button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-3">
              {peek.loading ? <div className="text-sm text-gray-500">در حالِ خواندن…</div> : (
                <pre dir="auto" className="whitespace-pre-wrap break-words text-[12.5px] leading-6">{peek.text || '(متنی استخراج نشد)'}</pre>
              )}
            </div>
            <div className="border-t border-gray-200 p-2 text-[11px] text-gray-500 dark:border-gray-700">این همان متنی است که ناظر می‌خواند — تکه‌تکه، تا آخر.</div>
          </div>
        </div>
      )}
      {zoom && (
        <div className="fixed inset-0 z-[96] flex items-center justify-center bg-black/80 p-4" onClick={() => setZoom(null)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={zoom} alt="تصویر" className="max-h-full max-w-full rounded" />
        </div>
      )}
    </div>
  )
}

function Shot({ r, id, caption, after, onZoom }: {
  r: InspectionReport; id: string; caption: string; after?: boolean; onZoom: (u: string) => void
}) {
  const info = r.shots?.[id]
  const url = inspectionApi.shotUrl(id)
  return (
    <figure className="max-w-xs">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={caption} onClick={() => onZoom(url)}
        className={`max-w-full cursor-zoom-in rounded border ${after ? 'border-emerald-300' : 'border-gray-300'}`} />
      <figcaption className={`text-[10px] ${after ? 'text-emerald-700' : 'text-gray-500'}`}>
        {caption}{info?.ref ? ` · ${info.ref}` : ''}
        {info && (info.store === 'drive'
          ? <> · {info.drive_link ? <a href={info.drive_link} target="_blank" rel="noreferrer" className="text-sky-700">☁ درایو</a> : '☁ درایو'}</>
          : <span className="text-red-700" title={info.store_note}> · ⏳ هنوز در درایو نیست</span>)}
      </figcaption>
    </figure>
  )
}

export function NextRoundChip({ nr, tick }: { nr: NextRound; tick: number }) {
  const left = Math.round((new Date(nr.at).getTime() - Date.now()) / 60000)
  void tick
  if (nr.basis === 'stale') {
    return <span dir="rtl" title={`آخرین دورِ ناظر: ${localClock(nr.last_seen || nr.at)}`}
      className="rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs text-red-800">
      ⚡ ناظرِ فوری مدتی است سر نزده — روتینش را بررسی کن</span>
  }
  if (nr.basis === 'due' || left <= 0) {
    return <span dir="rtl" className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
      ⚡ دورِ ناظر ({localClock(nr.at)}) در راه است — هر لحظه می‌رسد</span>
  }
  return (
    <span dir="rtl"
      title={nr.basis === 'assumed' ? 'تخمینی — هنوز دوری از ناظر ثبت نشده است'
        : `${everyText(nr.every_minutes)} · آخرین دور: ${localClock(nr.last_seen || nr.at)}`}
      className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
      ⚡ دورِ فوریِ بعدیِ ناظر: {localClock(nr.at)} ({humanGap(left)}){nr.basis === 'assumed' && ' — تخمینی'}
    </span>
  )
}

