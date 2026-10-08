'use client'
// «نظارت و سرکشی» — the smaller tabs: archive binders, Google Drive storage,
// and the Routines that do the supervising.
import React, { useCallback, useEffect, useState } from 'react'
import { errorText, inspectionApi, type Schedule, type StorageStatus } from '@/lib/inspection/api'
import { everyText, humanGap, localClock } from '@/lib/inspection/nextRound'
import { toast } from '@/lib/inspection/toast'
import { fa } from './Board'

// ---------------------------------------------------------------------------
// archive
// ---------------------------------------------------------------------------
type Binder = Awaited<ReturnType<typeof inspectionApi.binders>>['binders'][number]

export function Binders() {
  const [rows, setRows] = useState<Binder[]>([])
  useEffect(() => {
    inspectionApi.binders().then((d) => setRows(d.binders)).catch((e) => toast.error(errorText(e)))
  }, [])
  return (
    <div dir="rtl" className="space-y-3">
      <p className="text-xs text-gray-500 dark:text-gray-400">
        برگه‌هایی که تو تأیید (آبی) کرده‌ای، در دورِ بعدیِ ناظر — دوره‌ای یا فوری — اینجا بایگانی می‌شوند و هایلایتشان
        از صفحه‌ها برداشته می‌شود. هر زونکن {fa(40)} برگه دارد. متنِ کاملِ هر برگه در زبانهٔ «برگه‌ها» با فیلترِ «بایگانی» هست.
      </p>
      {!rows.length && <div className="rounded-xl border border-dashed p-8 text-center text-sm text-gray-500">هنوز چیزی بایگانی نشده.</div>}
      {rows.map((b) => (
        <div key={b.id} className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">🗂 {b.label}</span>
            <span className="text-[11px] text-gray-500">{fa(b.count)} از {fa(b.capacity)} برگه</span>
            <span className={`rounded px-1.5 text-[10px] ${b.closed_at ? 'bg-gray-200 dark:bg-gray-700' : 'bg-emerald-100 text-emerald-800'}`}>
              {b.closed_at ? 'بسته' : 'باز'}</span>
          </div>
          <ol className="mt-2 grid gap-1 text-[12px] md:grid-cols-2">
            {b.pages.map((p) => (
              <li key={p.report_id} className="rounded bg-gray-50 px-2 py-1 dark:bg-gray-900/50">
                برگهٔ {fa(p.page)} — گزارشِ {fa(p.number)}: {p.title}
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Google Drive
// ---------------------------------------------------------------------------
type CodeClient = { requestCode: () => void }
type Oauth2 = { initCodeClient: (o: Record<string, unknown>) => CodeClient }
const oauth2 = (): Oauth2 | undefined =>
  (window as unknown as { google?: { accounts?: { oauth2?: Oauth2 } } }).google?.accounts?.oauth2

function loadGis(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (oauth2()) return resolve()
    const s = document.createElement('script')
    s.src = 'https://accounts.google.com/gsi/client'
    s.async = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('بارگذاریِ گوگل ناموفق بود'))
    document.head.appendChild(s)
  })
}

export function StoragePanel() {
  const [st, setSt] = useState<StorageStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [rt, setRt] = useState('')

  const load = useCallback(async () => {
    try { setSt(await inspectionApi.storage()) } catch (e) { toast.error(errorText(e)) }
  }, [])
  useEffect(() => { void load() }, [load])

  const connect = async () => {
    if (!st?.drive.client_id) { toast.error('GOOGLE_CLIENT_ID روی سرور تنظیم نیست'); return }
    setBusy(true)
    try {
      await loadGis()
      const o = oauth2()
      if (!o) throw new Error('گوگل در دسترس نیست')
      o.initCodeClient({
        client_id: st.drive.client_id,
        scope: st.drive.scope,
        ux_mode: 'popup',
        prompt: 'consent',                      // a refresh token is only issued on full consent
        // Ask for EXACTLY drive.file. By default Google merges every scope this OAuth
        // client was granted before (incremental auth) — this client also serves a
        // YouTube app, and Google refuses drive.file + youtube.* in one request
        // («scopes that cannot be requested together», Error 400: invalid_request).
        include_granted_scopes: false,
        callback: async (resp: { code?: string; error?: string }) => {
          if (!resp.code) { toast.error(`اتصال انجام نشد${resp.error ? ` (${resp.error})` : ''}`); setBusy(false); return }
          try {
            setSt(await inspectionApi.connectDrive({ code: resp.code }))
            toast.success('گوگل درایو وصل شد — پوشهٔ پروژه ساخته شد و فایل‌های منتظر منتقل می‌شوند')
          } catch (e) { toast.error(errorText(e)) } finally { setBusy(false) }
        },
        error_callback: () => { toast.error('پنجرهٔ گوگل بسته شد یا مسدود بود'); setBusy(false) },
      }).requestCode()
    } catch (e) { toast.error(errorText(e)); setBusy(false) }
  }

  const useToken = async () => {
    if (!rt.trim()) return
    setBusy(true)
    try { setSt(await inspectionApi.connectDrive({ refresh_token: rt.trim() })); setRt(''); toast.success('وصل شد') }
    catch (e) { toast.error(errorText(e)) } finally { setBusy(false) }
  }

  const sync = async () => {
    setBusy(true)
    try {
      const d = await inspectionApi.syncDrive()
      setSt(d)
      const r = d.result as Record<string, number>
      toast.success(`منتقل شد: ${fa(r.files || 0)} فایل، ${fa(r.shots || 0)} تصویر${r.failed ? ` · ناموفق: ${fa(r.failed)}` : ''}`)
    } catch (e) { toast.error(errorText(e)) } finally { setBusy(false) }
  }

  const disconnect = async () => {
    if (!window.confirm('اتصالِ درایو قطع شود؟ فایل‌های قبلی در درایو می‌مانند؛ فقط فایل‌های تازه منتظر می‌مانند.')) return
    try { setSt(await inspectionApi.disconnectDrive()) } catch (e) { toast.error(errorText(e)) }
  }

  if (!st) return <div className="text-sm text-gray-500">…</div>
  const d = st.drive
  const tally = (m: Record<string, { count: number; label: string }>) =>
    Object.entries(m).map(([k, v]) => `${k === 'drive' ? 'در درایو' : k === 'pending' ? 'منتظر' : k === 'failed' ? 'ناموفق' : k}: ${fa(v.count)} (${v.label})`).join(' · ') || '—'

  return (
    <div dir="rtl" className="space-y-3">
      <p className="text-xs text-gray-500 dark:text-gray-400">
        فایل‌ها و اسکرین‌شات‌های «نظارت و سرکشی» روی سرور نگه داشته نمی‌شوند: فقط تا وقتی در راه‌اند موقتاً روی دیسک‌اند،
        بعد با رفرنسِ مشخص (مثلِ <span dir="ltr">PM-INS-0007-F01</span>) به پوشهٔ همین پروژه در گوگل درایو منتقل و لینک
        می‌شوند و نسخهٔ سرور — پس از تطبیقِ MD5 — پاک می‌شود. متنِ استخراج‌شده هم کنارِ فایل در درایو است.
      </p>
      <div className={`rounded-xl border p-4 ${d.connected ? 'border-emerald-300 bg-emerald-50/60 dark:bg-emerald-900/20' : 'border-amber-300 bg-amber-50/60 dark:bg-amber-900/20'}`}>
        <div className="text-sm font-semibold">{d.connected ? '☁ گوگل درایو وصل است' : '⚠ گوگل درایو هنوز وصل نیست'}</div>
        <div className="mt-1 space-y-0.5 text-[12px]">
          <div>پوشهٔ پروژه: <b>{d.root_folder}</b> / نظارت و سرکشی / گزارش-NNNN /
            {d.root_folder_link && <> · <a className="text-blue-600 hover:underline" href={d.root_folder_link} target="_blank" rel="noreferrer">باز کردنِ پوشه ↗</a></>}
            {d.inspection_folder_link && <> · <a className="text-blue-600 hover:underline" href={d.inspection_folder_link} target="_blank" rel="noreferrer">نظارت و سرکشی ↗</a></>}
          </div>
          {d.connected && <div>روش: {d.source === 'env' ? 'متغیرِ محیطیِ Render (GOOGLE_DRIVE_REFRESH_TOKEN)' : 'اتصال از همین صفحه'}{d.account ? ` · ${d.account}` : ''}</div>}
          {!d.connected && !!d.missing.length && (
            <div className="text-amber-800 dark:text-amber-200">لازم است: <span dir="ltr">{d.missing.join(' · ')}</span></div>
          )}
          {d.broken && <div className="text-red-700">اعتبارنامهٔ ذخیره‌شده خوانده نشد — دوباره وصل کن.</div>}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {!d.connected && d.client_configured && (
            <button onClick={() => void connect()} disabled={busy}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm text-white disabled:opacity-50">اتصال به گوگل درایو</button>
          )}
          <button onClick={() => void sync()} disabled={busy || !d.connected}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs disabled:opacity-50 dark:border-gray-600">انتقالِ فوریِ منتظرها به درایو</button>
          {d.connected && d.source === 'app' && (
            <button onClick={() => void disconnect()} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600">قطعِ اتصال</button>
          )}
        </div>
        {!d.connected && d.client_configured && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px]">
            <span>یا refresh token (scope ‎drive.file‎ برای همین کلاینت):</span>
            <input value={rt} onChange={(e) => setRt(e.target.value)} dir="ltr" type="password"
              className="min-w-[16rem] flex-1 rounded border border-gray-300 bg-white px-2 py-1 dark:border-gray-600 dark:bg-gray-700" />
            <button onClick={() => void useToken()} disabled={busy || !rt.trim()} className="rounded border px-2 py-1 disabled:opacity-50">ثبت</button>
          </div>
        )}
        {!d.client_configured && (
          <div className="mt-3 rounded-lg bg-white/70 p-2 text-[12px] text-gray-700 dark:bg-gray-900/40 dark:text-gray-200">
            برای اتصال، روی سرویسِ بک‌اند در Render این متغیرها را بگذار (هیچ‌کدام در کد نوشته نمی‌شود):
            <ul className="mt-1 list-disc pr-5" dir="ltr">
              <li>GOOGLE_CLIENT_ID · GOOGLE_CLIENT_SECRET (OAuth client از Google Cloud Console)</li>
              <li>GOOGLE_DRIVE_REFRESH_TOKEN (اختیاری — یا بعد از دو متغیرِ بالا، دکمهٔ «اتصال» همین‌جا)</li>
              <li>GOOGLE_DRIVE_ROOT_FOLDER (اختیاری، پیش‌فرض project-management)</li>
            </ul>
            <div className="mt-1">برای دکمهٔ اتصال، نشانیِ همین سایت باید در «Authorized JavaScript origins» همان کلاینت باشد.</div>
          </div>
        )}
      </div>
      <div className="rounded-xl border border-gray-200 bg-white p-3 text-[12px] dark:border-gray-700 dark:bg-gray-800">
        <div>فایل‌ها: {tally(st.usage.files)}</div>
        <div>تصویرها: {tally(st.usage.shots)}</div>
        <div>فضای موقتِ سرور (فقط در راه): {fa(st.usage.spool.files)} فایل · {st.usage.spool.label} از سقفِ {fa(st.usage.spool.limit_mb)} مگابایت</div>
        <div>سقفِ هر فایل: {fa(st.usage.max_file_mb)} مگابایت</div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// the Routines
// ---------------------------------------------------------------------------
const CRON_FA: Record<string, string> = {
  '11 */3 * * *': 'هر ۳ ساعت، دقیقهٔ ۱۱ (UTC)',
  '37 0 * * 2,5': 'سه‌شنبه و جمعه، ۰۰:۳۷ UTC',
}

export function Routines() {
  const [s, setS] = useState<Schedule | null>(null)
  useEffect(() => { inspectionApi.schedule().then(setS).catch((e) => toast.error(errorText(e))) }, [])
  if (!s) return <div className="text-sm text-gray-500">…</div>
  const nr = s.urgent.next_round
  const left = Math.round((new Date(nr.at).getTime() - Date.now()) / 60000)
  return (
    <div dir="rtl" className="space-y-3 text-[13px]">
      <p className="text-xs text-gray-500 dark:text-gray-400">
        دو روتینِ Claude Code (هر اجرا یک نشستِ مستقل) این سامانه را می‌گردانند. پرامپتِ داخلِ هر روتین عمداً کوتاه و ثابت
        است و فقط به فایلِ دستورش در ریپو اشاره می‌کند؛ همهٔ رفتار در گیت نسخه‌بندی می‌شود و نسخه‌های قبلی در
        <span dir="ltr"> {s.archive} </span>بایگانی می‌شوند.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-orange-200 bg-orange-50/50 p-4 dark:border-orange-800 dark:bg-orange-900/20">
          <div className="font-semibold">⚡ صفِ فوری</div>
          <div className="mt-1">زمان‌بندی: {CRON_FA[s.urgent.cron_utc] || s.urgent.cron_utc} <span className="text-gray-400" dir="ltr">({s.urgent.cron_utc})</span></div>
          <div>دستور: <span dir="ltr">{s.urgent.prompt}</span></div>
          <div>دورِ بعدی: {localClock(nr.at)} ({humanGap(left)}){nr.basis === 'assumed' ? ' — تخمینی' : ''}
            {nr.basis === 'stale' && <span className="text-red-700"> — مدتی است سر نزده!</span>}</div>
          {nr.last_seen && <div>آخرین دور: {new Date(nr.last_seen).toLocaleString('fa-IR')} · {everyText(nr.every_minutes)}</div>}
          <div className="mt-2 text-[12px] text-gray-600 dark:text-gray-300">
            هر دور: اول تأییدشده‌های تو (آبی) را بایگانی می‌کند، بعد برگه‌هایی را که «⚡ فوری» زده‌ای یکی‌یکی به ترتیبِ فشردنِ
            دکمه برمی‌دارد، کامل می‌خواند، انجام می‌دهد و زیرِ برگه جواب می‌نویسد. صفِ خالی = بی‌صدا.
          </div>
        </div>
        <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
          <div className="font-semibold">🛡 ناظرِ خودکارِ کامل</div>
          <div className="mt-1">زمان‌بندی: {CRON_FA[s.full.cron_utc] || s.full.cron_utc} <span className="text-gray-400" dir="ltr">({s.full.cron_utc})</span></div>
          <div>دستور: <span dir="ltr">{s.full.prompt}</span></div>
          {s.full.next_at && <div>دورِ بعدی: {new Date(s.full.next_at).toLocaleString('fa-IR')}</div>}
          <div>آخرین دورِ دیده‌شده: {s.full.last_seen ? new Date(s.full.last_seen).toLocaleString('fa-IR') : 'هنوز ثبت نشده'}</div>
          <div className="mt-2 text-[12px] text-gray-600 dark:text-gray-300">
            هر دور: بایگانیِ آبی‌ها، جوابِ همهٔ برگه‌های باز و نیمه‌کاره، به‌روزکردنِ نقشهٔ سامانه از روی کد و اسکنِ همهٔ صفحه‌ها،
            اجرای تست‌ها و بیلد، بازرسیِ بدبینانه، اصلاح و کامیت، و گزارشِ کوتاه به تو.
          </div>
        </div>
      </div>
    </div>
  )
}
