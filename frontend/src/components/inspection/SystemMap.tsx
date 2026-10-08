'use client'
// «نقشهٔ سامانه» — every screen and sub-screen (tab) of the app, with the
// measured coordinates of everything on it. Rows come from two observers (the
// owner's browser, the supervisor's headless scan) plus the code inventory, so
// a page that exists in the source but was never opened is listed too.
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { errorText, inspectionApi, type SurfaceElement, type SurfaceSummary } from '@/lib/inspection/api'
import { toast } from '@/lib/inspection/toast'
import { fa } from './Board'

const KIND_LABEL: Record<string, string> = {
  heading: 'عنوان', tab: 'زبانه', section: 'بخش', button: 'دکمه', input: 'ورودی', link: 'پیوند',
}

export default function SystemMap() {
  const [rows, setRows] = useState<SurfaceSummary[]>([])
  const [inv, setInv] = useState<Record<string, unknown> | null>(null)
  const [q, setQ] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const [detail, setDetail] = useState<(SurfaceSummary & { elements: SurfaceElement[]; new_keys: string[] }) | null>(null)
  const [kind, setKind] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await inspectionApi.surfaces()
      setRows(d.surfaces)
      setInv(d.inventory)
    } catch (e) { toast.error(errorText(e)) }
  }, [])
  useEffect(() => { void load() }, [load])

  const show = async (id: string) => {
    if (open === id) { setOpen(null); setDetail(null); return }
    setOpen(id)
    setDetail(null)
    try { setDetail((await inspectionApi.surface(id)).surface) } catch (e) { toast.error(errorText(e)) }
  }

  const filtered = useMemo(() => rows.filter((r) => !q
    || `${r.route} ${r.tab} ${r.label} ${r.title}`.toLowerCase().includes(q.toLowerCase())), [rows, q])
  const pages = new Set(rows.map((r) => r.route)).size
  const unseen = rows.filter((r) => r.declared && !r.visits).length
  const fresh = rows.filter((r) => r.new_count > 0).length
  const elements = rows.reduce((n, r) => n + Object.values(r.counts || {}).reduce((a, b) => a + b, 0), 0)
  const newKeys = new Set(detail?.new_keys || [])

  return (
    <div dir="rtl" className="space-y-3">
      <p className="text-xs text-gray-500 dark:text-gray-400">
        هر صفحه و زیرصفحه (زبانه) با مختصاتِ دقیقِ عنوان‌ها، زبانه‌ها، بخش‌ها، دکمه‌ها، ورودی‌ها و پیوندها — خودکار ثبت
        می‌شود: هر بار که صفحه‌ای باز شود (چه الان، چه صفحه‌هایی که بعداً اضافه می‌شوند) و هر دورِ کاملِ ناظر.
        صفحه‌ای که در کد هست ولی هنوز کسی بازش نکرده با «دیده نشده» مشخص است.
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[[pages, 'صفحه'], [rows.length, 'صفحه + زیرصفحه'], [elements, 'عنصرِ ثبت‌شده'], [unseen, 'در کد، دیده‌نشده']].map(([n, l]) => (
          <div key={String(l)} className="rounded-xl border border-gray-200 bg-white p-3 text-center dark:border-gray-700 dark:bg-gray-800">
            <div className="text-2xl font-bold">{fa(Number(n))}</div><div className="text-[11px] text-gray-500">{l}</div>
          </div>
        ))}
      </div>
      {inv && (
        <div className="text-[11px] text-gray-500">
          آخرین فهرستِ کد: {String(inv.generated_at || '—')} {inv.commit ? <span dir="ltr">({String(inv.commit).slice(0, 8)})</span> : null}
          {fresh ? ` · ${fa(fresh)} صفحه عنصرِ تازه دارد` : ''}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="جستجو در مسیر/عنوان…"
          className="min-w-[14rem] flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700" />
        <button onClick={() => void load()} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs dark:border-gray-600">↻ تازه‌سازی</button>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
        <table className="w-full text-[12px]">
          <thead className="bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            <tr>
              <th className="p-2 text-right">صفحه</th><th className="p-2 text-right">زیرصفحه/زبانه</th>
              <th className="p-2 text-right">عنصرها</th><th className="p-2 text-right">آخرین مشاهده</th>
              <th className="p-2 text-right">وضعیت</th><th className="p-2" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <React.Fragment key={r.id}>
                <tr className="border-t border-gray-100 dark:border-gray-700">
                  <td className="p-2">
                    <div className="font-semibold">{r.label || r.route}</div>
                    <div className="text-[10px] text-gray-400" dir="ltr">{r.route}</div>
                  </td>
                  <td className="p-2">{r.tab || '—'}</td>
                  <td className="p-2 text-[11px]">
                    {Object.entries(r.counts || {}).map(([k, n]) => `${KIND_LABEL[k] || k}: ${fa(n)}`).join(' · ') || '—'}
                  </td>
                  <td className="p-2 text-[11px]">
                    {r.last_seen ? new Date(r.last_seen).toLocaleString('fa-IR') : '—'}
                    {r.seen_by && <div className="text-[10px] text-gray-400">{r.seen_by === 'supervisor-scan' ? 'اسکنِ ناظر' : 'مرورگرِ مالک'} · {fa(r.visits)} بار</div>}
                  </td>
                  <td className="p-2 text-[11px]">
                    {r.declared && !r.visits && <span className="rounded bg-gray-200 px-1.5 py-0.5 dark:bg-gray-700">دیده نشده</span>}
                    {r.new_count > 0 && <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800">{fa(r.new_count)} تازه</span>}
                    {r.removed_count > 0 && <span className="mr-1 rounded bg-red-100 px-1.5 py-0.5 text-red-800">{fa(r.removed_count)} حذف‌شده</span>}
                    {!!r.open_reports && <span className="mr-1 rounded bg-amber-100 px-1.5 py-0.5 text-amber-800">{fa(r.open_reports)} گزارشِ باز</span>}
                  </td>
                  <td className="p-2 text-left">
                    {!!r.visits && <button onClick={() => void show(r.id)} className="text-blue-600 hover:underline">{open === r.id ? 'بستن' : 'مختصات'}</button>}
                    {!!r.sample_path && <a href={r.sample_path} className="mr-2 text-blue-600 hover:underline">رفتن ↗</a>}
                  </td>
                </tr>
                {open === r.id && (
                  <tr className="bg-gray-50/60 dark:bg-gray-900/40">
                    <td colSpan={6} className="p-2">
                      {!detail ? <div className="text-gray-500">…</div> : (
                        <div className="space-y-2">
                          <div className="text-[11px] text-gray-500">
                            پنجره {detail.viewport ? `${fa(detail.viewport.w)}×${fa(detail.viewport.h)}` : '—'} · سند {detail.doc_size ? `${fa(detail.doc_size.w)}×${fa(detail.doc_size.h)}` : '—'}
                            {detail.source_file && <> · فایل: <span dir="ltr">{detail.source_file}</span></>}
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {['', ...Object.keys(KIND_LABEL)].map((k) => (
                              <button key={k || 'all'} onClick={() => setKind(k)}
                                className={`rounded px-2 py-0.5 text-[11px] ${kind === k ? 'bg-gray-900 text-white' : 'border border-gray-300 dark:border-gray-600'}`}>
                                {k ? KIND_LABEL[k] : 'همه'}
                              </button>
                            ))}
                          </div>
                          <div className="max-h-80 overflow-auto">
                            <table className="w-full text-[11px]">
                              <thead><tr className="text-gray-500"><th className="p-1 text-right">نوع</th><th className="p-1 text-right">برچسب</th><th className="p-1 text-right">بخش</th><th className="p-1 text-right">x,y · w×h</th><th className="p-1 text-right">سلکتور</th></tr></thead>
                              <tbody>
                                {detail.elements.filter((e) => !kind || e.kind === kind).map((e, i) => (
                                  <tr key={i} className={`border-t border-gray-100 dark:border-gray-800 ${newKeys.has(`${e.kind}|${e.label.slice(0, 80)}|${e.selector}`) ? 'bg-emerald-50 dark:bg-emerald-900/20' : ''}`}>
                                    <td className="p-1">{KIND_LABEL[e.kind] || e.kind}</td>
                                    <td className="p-1" dir="auto">{e.label || '—'}</td>
                                    <td className="p-1" dir="auto">{e.section || '—'}</td>
                                    <td className="p-1 whitespace-nowrap" dir="ltr">{e.rect.x},{e.rect.y} · {e.rect.w}×{e.rect.h}</td>
                                    <td className="p-1 text-gray-500" dir="ltr">{e.selector}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {!filtered.length && (
              <tr><td colSpan={6} className="p-6 text-center text-gray-500">هنوز صفحه‌ای ثبت نشده — کافی است صفحه‌ها باز شوند.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
