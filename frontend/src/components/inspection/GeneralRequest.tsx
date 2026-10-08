'use client'
// «درخواستِ عمومی» — for a request that points at no place on screen, or at a
// place that does not exist yet (a new feature, a general change, a question).
// Same as ALLIN1's general request: it becomes an ordinary sheet in the
// supervisor's queue and is followed up on the same board. Added here: files of
// any type and «⚡ فوری» on the form itself.
import React, { useState } from 'react'
import { errorText, inspectionApi, uploadFile } from '@/lib/inspection/api'
import { rushMessage } from '@/lib/inspection/nextRound'
import { shrinkShot } from '@/lib/inspection/shrinkShot'
import { toast } from '@/lib/inspection/toast'

export default function GeneralRequest({ onFiled, compact = false }: { onFiled?: () => void; compact?: boolean }) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [shot, setShot] = useState<string | null>(null)
  const [urgent, setUrgent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [pct, setPct] = useState<{ name: string; pct: number } | null>(null)

  const onPaste = (e: React.ClipboardEvent) => {
    const item = Array.from(e.clipboardData?.items || []).find((i) => i.type.startsWith('image/'))
    const file = item?.getAsFile()
    if (!file) return
    e.preventDefault()
    const fr = new FileReader()
    fr.onload = () => { void shrinkShot(String(fr.result || '')).then(setShot) }
    fr.readAsDataURL(file)
  }

  const file = async () => {
    const t = text.trim()
    if (!t || busy) return
    setBusy(true)
    try {
      const { report } = await inspectionApi.create({ text: t, kind: 'general', shot, urgent: false })
      const failed: string[] = []
      for (const f of files) {
        try {
          setPct({ name: f.name, pct: 0 })
          await uploadFile(report.id, f, { onProgress: (p) => setPct({ name: f.name, pct: p }) })
        } catch (e) { failed.push(`${f.name} (${errorText(e)})`) }
      }
      setPct(null)
      let extra = ''
      if (urgent) {
        try {
          const rr = await inspectionApi.rush(report.id)
          extra = ` · ${rushMessage(rr.position, rr.next_round)}`
        } catch { /* filed; ⚡ can be pressed on the board */ }
      }
      if (failed.length) toast.error(`درخواست ثبت شد ولی این فایل‌ها بالا نرفتند: ${failed.join(' · ')}`)
      else toast.success(<span dir="rtl">درخواستِ {report.number} ثبت شد و در صفِ ناظر است{extra}</span>, { duration: 7000 })
      setText(''); setFiles([]); setShot(null); setUrgent(false)
      onFiled?.()
      try { window.dispatchEvent(new CustomEvent('pm:inspection-filed')) } catch { /* SSR */ }
    } catch (e) { toast.error(errorText(e)) } finally { setBusy(false); setPct(null) }
  }

  return (
    <div dir="rtl" className="space-y-2 rounded-xl border border-gray-300 bg-white p-4 dark:border-gray-600 dark:bg-gray-800">
      <div className="text-sm font-semibold">درخواستِ عمومی</div>
      {!compact && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          برای چیزی که به جای مشخصی از صفحه‌ها اشاره نمی‌کند، یا جایی برایش هنوز ساخته نشده (قابلیتِ تازه، تغییرِ کلی،
          سؤال). مثلِ بقیهٔ برگه‌ها در صفِ ناظر می‌رود، رنگش با وضعیت عوض می‌شود و همین‌جا پیگیری می‌شود.
        </p>
      )}
      <textarea value={text} dir="auto" rows={4} onPaste={onPaste}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void file() }}
        placeholder="درخواستت را بنویس… (Ctrl+Enter برای ثبت · اسکرین‌شات را Ctrl+V کن)"
        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700" />
      <div className="flex flex-wrap items-center gap-2">
        <label className="cursor-pointer rounded-lg border border-dashed border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">
          📎 فایل (هر نوعی)
          <input type="file" multiple className="hidden" onChange={(e) => {
            const list = Array.from(e.target.files || [])
            if (list.length) setFiles((p) => [...p, ...list])
            e.target.value = ''
          }} />
        </label>
        <label className="flex items-center gap-1 text-xs text-orange-700 dark:text-orange-300">
          <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} /> ⚡ فوری
        </label>
        {shot && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={shot} alt="اسکرین‌شات" className="h-10 rounded border border-gray-300" />
        )}
        {shot && <button className="text-xs text-red-600" onClick={() => setShot(null)}>× تصویر</button>}
        <span className="flex-1" />
        <button type="button" onClick={() => void file()} disabled={busy || !text.trim()}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
          {busy ? 'در حالِ ثبت…' : 'ثبت درخواست'}
        </button>
      </div>
      {!!files.length && (
        <div className="flex flex-wrap gap-1.5 text-[11px]">
          {files.map((f, i) => (
            <span key={`${f.name}-${i}`} className="rounded bg-gray-100 px-2 py-0.5 dark:bg-gray-700">
              {f.name} · {(f.size / (1024 * 1024)).toFixed(1)}MB{' '}
              <button className="text-red-600" onClick={() => setFiles((p) => p.filter((_, j) => j !== i))}>×</button>
            </span>
          ))}
        </div>
      )}
      {pct && <div className="text-[11px] text-amber-800">در حالِ بالا رفتن: {pct.name} — {pct.pct}٪</div>}
    </div>
  )
}
