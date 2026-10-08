'use client'
// «نظارت و سرکشی» on the client: the owner arms a box, draws it around what is
// wrong, writes a line, and the sheet is filed with the way BACK to it.
//
// Ported from ALLIN1 (`frontend/src/lib/inspection.tsx`, read-only reference),
// including the lessons recorded there:
//   • two pieces of evidence — the ADDRESS (always true) and the PICTURE (a real
//     screenshot the owner pastes with Ctrl+V, or a render of the region with the
//     box marked on it, clearly labelled as a render);
//   • the capture starts by itself the moment the box is drawn (a second button
//     press cost the owner a picture once), and filing waits for it;
//   • the dialog asks WHERE this goes: «گزارشِ جدید» or «ذیلِ» one of the sheets
//     still open — the follow-up keeps its own box, picture and files;
//   • any file type can ride along; files belong to the note they came with.
// Added here: «⚡ فوری» right in the dialog, and this app's absolute API base.
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { errorText, inspectionApi, uploadFile, type InspectionReport } from './api'
import { notifySheetsChanged } from './highlights'
import { shrinkShot } from './shrinkShot'
import { rushMessage } from './nextRound'
import { toast, Toaster } from './toast'
import {
  CAPTURE_DEADLINE_MS, CROP_MIN_PX, activeTab, bandAround, boundedCaptureTarget, captureChain, captureRatio,
  geometryLabel, measureSpot, pageElementsAt, pickCaptureTarget, pickCropSheet, resolveSpot,
  spotAddress, verifiedSelector, withDeadline,
  type Rect, type UiSpot,
} from './spot'

type Ctx = {
  active: boolean
  setActive: (v: boolean) => void
  arm: () => void
  reports: InspectionReport[]
  refresh: () => Promise<void>
  loading: boolean
}

const InspectionCtx = createContext<Ctx | null>(null)
export const useInspection = () => useContext(InspectionCtx)

const LS_KEY = 'pm.inspection.active'

export const TONE: Record<string, string> = {
  open: 'bg-amber-500',
  answered: 'bg-emerald-600',
  approved: 'bg-blue-600',
  filed: 'bg-gray-400',
  fixed: 'bg-emerald-600',
  partial: 'bg-yellow-600',
  'needs-owner': 'bg-purple-600',
  'not-done': 'bg-red-600',
  stale: 'bg-gray-500',
}

export function InspectionProvider({ children, pathname, pageLabel }: {
  children: React.ReactNode
  pathname: string
  pageLabel: string
}) {
  const [active, setActiveRaw] = useState(false)
  const [armed, setArmed] = useState(false)
  const [rect, setRect] = useState<Rect | null>(null)
  const [spot, setSpot] = useState<UiSpot | null>(null)
  const [shot, setShot] = useState<{ data: string; kind: 'pasted' | 'rendered' } | null>(null)
  const [shooting, setShooting] = useState(false)
  const [text, setText] = useState('')
  const [picked, setPicked] = useState<File[]>([])
  const [target, setTarget] = useState('')   // '' = a new sheet; otherwise the sheet this goes under
  const [urgent, setUrgent] = useState(false)
  const [upPct, setUpPct] = useState<{ name: string; pct: number } | null>(null)
  const [busy, setBusy] = useState(false)
  const [reports, setReports] = useState<InspectionReport[]>([])
  const [loading, setLoading] = useState(false)
  const start = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    try { setActiveRaw(localStorage.getItem(LS_KEY) === '1') } catch { /* private mode */ }
  }, [])
  const setActive = useCallback((v: boolean) => {
    setActiveRaw(v)
    try { localStorage.setItem(LS_KEY, v ? '1' : '0') } catch { /* private mode */ }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      setReports((await inspectionApi.list({})).reports)
      notifySheetsChanged()
    } catch { /* backend asleep — the next action tries again */ }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { if (active) void refresh() }, [active, refresh])

  const arm = useCallback(() => { setArmed(true); void refresh() }, [refresh])

  // Alt is the other way in; Escape always gets out.
  useEffect(() => {
    if (!active) return
    const down = (e: KeyboardEvent) => {
      if (e.key === 'Alt' && !spot) setArmed(true)
      if (e.key === 'Escape' && (armed || spot)) { setArmed(false); setRect(null); setSpot(null) }
    }
    const up = (e: KeyboardEvent) => { if (e.key === 'Alt' && !start.current) setArmed(false) }
    window.addEventListener('keydown', down, true)
    window.addEventListener('keyup', up, true)
    return () => {
      window.removeEventListener('keydown', down, true)
      window.removeEventListener('keyup', up, true)
    }
  }, [active, armed, spot])

  const onDown = (e: React.PointerEvent) => {
    start.current = { x: e.clientX, y: e.clientY }
    setRect({ x: e.clientX, y: e.clientY, w: 0, h: 0 })
  }
  const onMove = (e: React.PointerEvent) => {
    const s = start.current
    if (!s) return
    setRect({
      x: Math.min(s.x, e.clientX), y: Math.min(s.y, e.clientY),
      w: Math.abs(e.clientX - s.x), h: Math.abs(e.clientY - s.y),
    })
  }
  const onUp = async () => {
    const s = start.current
    start.current = null
    const r = rect
    setRect(null)
    setArmed(false)
    if (!s || !r || r.w < CROP_MIN_PX || r.h < CROP_MIN_PX) return
    const stack = pageElementsAt(r.x + r.w / 2, r.y + r.h / 2)
    const anchor = stack[0] ?? null
    const anchorPath = verifiedSelector(anchor)
    const ab = anchor?.getBoundingClientRect()
    const sx = window.scrollX || 0
    const sy = window.scrollY || 0
    const geometry = measureSpot({
      rect: r,
      viewport: { w: window.innerWidth, h: window.innerHeight },
      scroll: { x: sx, y: sy },
      doc_size: {
        w: Math.max(document.documentElement.scrollWidth, window.innerWidth),
        h: Math.max(document.documentElement.scrollHeight, window.innerHeight),
      },
      dpr: window.devicePixelRatio || 1,
      anchor,
      anchorRect: ab ? { x: ab.left + sx, y: ab.top + sy, w: ab.width, h: ab.height } : null,
      anchorPath,
    })
    const tab = activeTab(document, window.location.search)
    if (tab) geometry.tab = tab
    const resolved = resolveSpot({
      rect: r, viewport: { w: window.innerWidth, h: window.innerHeight }, stack, geometry,
      fallbackPage: pathname, fallbackLabel: pageLabel, search: window.location.search,
    })
    if (tab && !resolved.section_label) resolved.section_label = `زبانهٔ «${tab}»`
    setSpot(resolved)
    setText('')
    setShot(null)
    setUrgent(false)
    void renderRegion(resolved)
  }

  /** Render the covered region — clearly labelled as a render, never as a photo. */
  const renderRegion = useCallback(async (spotArg?: UiSpot) => {
    const sp = spotArg ?? spot
    if (!sp) return
    setShooting(true)
    try {
      const { toJpeg } = await import('html-to-image')
      const el = pageElementsAt(sp.rect.x + sp.rect.w / 2, sp.rect.y + sp.rect.h / 2)[0] as HTMLElement | undefined
      // a box outside the content area (the sidebar, the header) is photographed
      // from the page itself — the content area would not contain it at all
      const surface = el?.closest?.('[data-report-surface]') ? pickCaptureTarget(el) : (document.body as HTMLElement)
      if (!surface) return
      const tgt = boundedCaptureTarget(
        captureChain(el, surface),
        (n) => ({ w: (n as HTMLElement).offsetWidth, h: (n as HTMLElement).offsetHeight,
                  nodes: n.querySelectorAll('*').length }),
      ) as HTMLElement | null
      if (!tgt) {
        setShot(null)
        toast.info('این صفحه برای تصویربرداریِ خودکار سنگین است — اسکرین‌شاتِ خودت را Ctrl+V کن', { duration: 6000 })
        return
      }
      const sheet = pickCropSheet(el, tgt)
      const ratio = captureRatio({ w: tgt.offsetWidth, h: tgt.offsetHeight })
      const dark = document.documentElement.classList.contains('dark')
      const data = await withDeadline(toJpeg(tgt, {
        quality: 0.82, pixelRatio: ratio, cacheBust: true,
        backgroundColor: dark ? '#111827' : '#ffffff',
        style: { margin: '0' },
      }), CAPTURE_DEADLINE_MS)
      if (!data) {
        setShot(null)
        toast.info('تصویرِ خودکار برای این صفحه گرفته نشد — اسکرین‌شاتِ خودت را Ctrl+V کن', { duration: 6000 })
        return
      }
      const tr = tgt.getBoundingClientRect()
      let out = data
      try {
        const { annotate, boxInImage } = await import('./annotateShot')
        const probe = new Image()
        await new Promise<void>((res, rej) => {
          probe.onload = () => res(); probe.onerror = () => rej(new Error('x')); probe.src = data
        })
        const geom = {
          left: tr.left, top: tr.top, width: tr.width, height: tr.height,
          layoutWidth: tgt.offsetWidth, layoutHeight: tgt.offsetHeight,
        }
        const image = { width: probe.naturalWidth, height: probe.naturalHeight }
        const box = boxInImage(sp.rect, geom, image)
        const sr = sheet?.getBoundingClientRect()
        const crop = sr
          ? boxInImage({ x: sr.left, y: sr.top, w: sr.width, h: sr.height }, geom, image)
          : (box ? bandAround(box, image, window.innerHeight) : null)
        if (box) out = await annotate(data, box, crop)
      } catch { /* marking failed — keep the plain capture */ }
      out = await shrinkShot(out)
      setShot((prev) => (prev?.kind === 'pasted' ? prev : { data: out, kind: 'rendered' }))
    } catch {
      toast.error('تصویربرداری از این بخش ممکن نشد — می‌توانی اسکرین‌شاتِ خودت را بچسبانی')
    } finally { setShooting(false) }
  }, [spot])

  /** A real screenshot from the owner's own OS, pasted in. The best evidence. */
  const onPaste = useCallback((e: React.ClipboardEvent) => {
    const item = Array.from(e.clipboardData?.items || []).find((i) => i.type.startsWith('image/'))
    if (!item) return
    const file = item.getAsFile()
    if (!file) return
    e.preventDefault()
    const fr = new FileReader()
    fr.onload = () => {
      const raw = String(fr.result || '')
      setShot({ data: raw, kind: 'pasted' })
      void shrinkShot(raw).then((small) => {
        if (small !== raw) setShot((prev) => (prev?.data === raw ? { data: small, kind: 'pasted' } : prev))
      })
    }
    fr.readAsDataURL(file)
  }, [])

  // Only sheets still in play can take a follow-up: once ticked or archived,
  // that conversation is over and a new observation deserves its own sheet.
  const openSheets = useMemo(
    () => reports.filter((r) => r.status === 'open' || r.status === 'answered'),
    [reports])

  const submit = async () => {
    if (!spot || !text.trim()) return
    setBusy(true)
    try {
      const under = target && openSheets.some((r) => r.id === target) ? target : ''
      const rep = under
        ? { id: under, number: openSheets.find((r) => r.id === under)?.number }
        : (await inspectionApi.create({ text: text.trim(), spot, shot: shot?.data, urgent })).report
      const failed: string[] = []
      const uploaded: string[] = []
      for (const f of picked) {
        try {
          setUpPct({ name: f.name, pct: 0 })
          const got = await uploadFile(rep.id, f, { onProgress: (pct) => setUpPct({ name: f.name, pct }) })
          uploaded.push(got.id)
        } catch (e) { failed.push(`${f.name} (${errorText(e)})`) }
      }
      setUpPct(null)
      if (under) {
        await inspectionApi.note(under, { text: text.trim(), shot: shot?.data, spot, file_ids: uploaded })
      }
      let rushText = ''
      if (urgent && under) {
        try {
          const rr = await inspectionApi.rush(under)
          rushText = ' · ' + rushMessage(rr.position, rr.next_round)
        } catch { /* the note is in; the rush can be pressed on the board */ }
      } else if (urgent) {
        rushText = ' · در صفِ فوری'
      }
      if (failed.length) {
        toast.error(`${under ? 'یادداشت' : 'گزارش'} ثبت شد ولی این فایل‌ها بالا نرفتند: ${failed.join(' · ')}`)
      } else if (under) {
        toast.success(<span dir="rtl">ذیلِ گزارشِ {rep.number} ثبت شد — آن برگه دوباره بازِ رسیدگی شد{rushText}</span>)
      } else {
        toast.success(<span dir="rtl">{picked.length
          ? `گزارش با ${picked.length} فایل ثبت شد — ناظر باید کاملشان را بخواند`
          : 'گزارش ثبت شد — ناظر در دورِ بعد جواب می‌دهد'}{rushText}</span>)
      }
      setSpot(null); setText(''); setShot(null); setPicked([]); setTarget(''); setUrgent(false)
      await refresh()
      // tell an open board (the /inspection page) that a sheet was filed or grew
      try { window.dispatchEvent(new CustomEvent('pm:inspection-filed')) } catch { /* SSR */ }
    } catch (e) { toast.error(errorText(e)) } finally { setBusy(false); setUpPct(null) }
  }

  const value = useMemo<Ctx>(() => ({ active, setActive, arm, reports, refresh, loading }),
    [active, setActive, arm, reports, refresh, loading])

  return (
    <InspectionCtx.Provider value={value}>
      {children}
      <Toaster />
      {active && !spot && !armed && (
        <button
          onClick={arm}
          data-inspection-layer="1"
          className="fixed bottom-6 left-24 z-[80] rounded-full bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-amber-700"
          title="یک کادر دورِ همان چیزی بکش که ایراد دارد (یا کلید Alt را نگه دار)"
        >📝 ثبت گزارش</button>
      )}
      {armed && (
        <div
          dir="rtl" data-inspection-layer="1"
          className="fixed inset-0 z-[90]"
          style={{ cursor: 'crosshair', background: 'rgba(15,12,8,0.18)' }}
          onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp}
        >
          {rect && rect.w > 2 && (
            <div className="pointer-events-none absolute border-2 border-amber-400 bg-amber-200/10"
              style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }} />
          )}
          <div className="pointer-events-none absolute left-1/2 top-6 -translate-x-1/2 rounded-lg bg-black/85 px-4 py-2 text-sm text-amber-100">
            کادر بکش دورِ همان چیزی که منظورت است · Esc انصراف
          </div>
        </div>
      )}
      {spot && (
        <div dir="rtl" data-inspection-layer="1"
          className="fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) { setSpot(null); setPicked([]) } }}>
          <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-4 shadow-2xl dark:bg-gray-800 dark:text-gray-100">
            <div className="mb-2 text-sm font-bold">گزارشِ نظارت و سرکشی</div>
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-100">
              <div className="font-semibold">{spotAddress(spot)}</div>
              <div className="mt-1 opacity-80" dir="ltr">{spot.reopen}</div>
              {!!spot.covered_text && (
                <div className="mt-1 line-clamp-3 opacity-80">آنچه در کادر بود: {spot.covered_text}</div>
              )}
              {!!spot.geometry && (
                <div dir="rtl" className="mt-1 opacity-90">
                  مختصات: {geometryLabel(spot.geometry)}
                  {spot.geometry.anchor.path
                    ? ' · به عنصرِ زیرش گره خورد (با تغییرِ چیدمان هم سرِ جایش می‌ماند)'
                    : ' · گره به عنصر ممکن نشد — فقط مختصاتِ سند ذخیره می‌شود'}
                </div>
              )}
            </div>
            {openSheets.length > 0 && (
              <div className="mb-2">
                <label className="mb-1 block text-[11px] font-semibold">این را کجا ثبت کنم؟</label>
                <select value={target} onChange={(e) => setTarget(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white p-2 text-xs dark:border-gray-600 dark:bg-gray-700">
                  <option value="">گزارشِ جدید</option>
                  {openSheets.map((r) => (
                    <option key={r.id} value={r.id}>
                      ذیلِ گزارشِ {r.number} — {(r.title || '').slice(0, 48)}
                      {r.status === 'answered' ? ' (پاسخ گرفته)' : ''}
                    </option>
                  ))}
                </select>
                {!!target && (
                  <div className="mt-1 text-[11px] text-amber-800 dark:text-amber-300">
                    ذیلِ آن برگه ثبت می‌شود، با کادر و تصویرِ خودش؛ فایل‌هایی که اینجا پیوست کنی فقط مالِ همین
                    یادداشت‌اند و با پیوست‌های قبلی قاتی نمی‌شوند. آن برگه دوباره «بازِ رسیدگی» (نارنجی) می‌شود.
                  </div>
                )}
              </div>
            )}
            <textarea
              value={text} onChange={(e) => setText(e.target.value)} onPaste={onPaste}
              rows={4} autoFocus dir="auto"
              placeholder="چه ایرادی دارد، یا چه می‌خواهی؟ (اسکرین‌شاتِ خودت را می‌توانی همین‌جا Ctrl+V کنی)"
              className="w-full rounded-lg border border-gray-300 bg-white p-2 text-sm dark:border-gray-600 dark:bg-gray-700"
            />
            <label className="mt-2 flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-gray-300 px-3 py-2 text-xs text-gray-600 hover:border-amber-400 hover:bg-amber-50/40 dark:border-gray-600 dark:text-gray-300">
              <span>📎 فایل پیوست کن (هر نوعی — ورد، PDF، عکس، اکسل، صوت، ویدئو، زیپ…)</span>
              <input type="file" multiple className="hidden"
                onChange={(e) => {
                  const list = Array.from(e.target.files || [])
                  if (list.length) setPicked((prev) => [...prev, ...list])
                  e.target.value = ''
                }} />
            </label>
            {!!picked.length && (
              <div className="mt-1.5 space-y-1">
                {picked.map((f, i) => (
                  <div key={`${f.name}-${i}`} dir="rtl"
                    className="flex items-center gap-2 rounded-md bg-gray-50 px-2 py-1 text-[11px] dark:bg-gray-700">
                    <span className="truncate">{f.name}</span>
                    <span className="text-gray-400">{(f.size / (1024 * 1024)).toFixed(1)} مگابایت</span>
                    <span className="flex-1" />
                    <button type="button" title="برداشتن"
                      onClick={() => setPicked((prev) => prev.filter((_, j) => j !== i))}
                      className="text-red-600 hover:underline">×</button>
                  </div>
                ))}
                <div className="text-[11px] text-emerald-700 dark:text-emerald-400">
                  فایل‌ها پس از بالا رفتن به پوشهٔ همین پروژه در گوگل درایو منتقل می‌شوند و ناظر موظف است کاملشان را بخواند.
                </div>
              </div>
            )}
            {upPct && (
              <div dir="rtl" className="mt-1.5 text-[11px] text-amber-800 dark:text-amber-300">
                در حالِ بالا رفتن: {upPct.name} — {upPct.pct}٪
              </div>
            )}
            <label className="mt-2 flex items-center gap-2 text-xs text-orange-700 dark:text-orange-300">
              <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} />
              ⚡ فوری — ناظر خارج از نوبتِ دوره‌ای (در دورِ فوریِ بعدی) سراغش برود
            </label>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <button onClick={() => void renderRegion()} type="button" disabled={shooting}
                className="rounded-lg border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700">
                {shooting ? '… در حالِ گرفتنِ تصویر' : '📷 گرفتنِ دوبارهٔ تصویر'}
              </button>
              {shot && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={shot.data} alt="پیش‌نمایشِ تصویر" className="h-12 w-auto rounded border border-gray-300" />
              )}
              {shot && (
                <span className={`text-[11px] ${shot.kind === 'pasted' ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {shot.kind === 'pasted'
                    ? '✓ اسکرین‌شاتِ واقعیِ خودت پیوست شد'
                    : '⚠ تصویرِ بازسازی‌شده با کادرِ تو علامت‌خورده (عکسِ واقعی نیست) — اگر دقیق نبود، اسکرین‌شاتِ خودت را Ctrl+V کن'}
                </span>
              )}
              <span className="flex-1" />
              <button onClick={() => { setSpot(null); setPicked([]) }} type="button"
                className="rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">انصراف</button>
              <button onClick={() => void submit()} disabled={busy || shooting || !text.trim()}
                title={shooting ? 'تا آماده‌شدنِ تصویر صبر کن' : ''}
                className="rounded-lg bg-amber-600 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
                {busy ? '...' : shooting ? 'تصویر…' : target ? 'ثبت ذیلِ گزارش' : 'ثبت گزارش'}
              </button>
            </div>
          </div>
        </div>
      )}
    </InspectionCtx.Provider>
  )
}

/** The switch that turns the inspection round on — in the sidebar. */
export function InspectionToggle({ compact = false }: { compact?: boolean }) {
  const ins = useInspection()
  if (!ins) return null
  return (
    <button
      type="button"
      onClick={() => ins.setActive(!ins.active)}
      title={ins.active ? 'حالتِ ثبتِ گزارش روشن است — برای خاموش‌کردن بزن' : 'روشن‌کردنِ حالتِ ثبتِ گزارش روی صفحه‌ها'}
      className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 transition-all ${ins.active
        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'}`}
    >
      <span>📝</span>
      {!compact && <span className="font-medium">{ins.active ? 'ثبتِ گزارش: روشن' : 'ثبتِ گزارش: خاموش'}</span>}
    </button>
  )
}
