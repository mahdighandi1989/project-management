'use client';

/**
 * PM-INS-0024 (2026-11-17) — «دیسکِ سرور ۷۸٪ — بگو چه چیزی جا گرفته و پاک‌سازیِ امن پیشنهاد بده».
 * Inside «خلاصهٔ یک‌صفحه‌ایِ اتاق فرمان» (/oversight#disk). Backend: services/disk_janitor.py —
 *   GET  /api/oversight/disk                  → percent + breakdown (10 biggest folders/files, biggest DB tables)
 *   GET  /api/oversight/disk/cleanup-preview  → re-creatable caches, old logs, old artifacts (nothing changes)
 *   POST /api/oversight/disk/cleanup          → only the ticked paths, with confirm; logs/artifacts go to Drive first
 * The database and the JSON stores are never cleanup candidates. Telegram alert past 85%.
 */
import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const mb = (b: number) => `${((b || 0) / 1048576).toLocaleString('fa-IR', { maximumFractionDigits: 1 })}MB`;
const KIND: Record<string, string> = { cache: 'کش/موقت (حذف — دوباره ساخته می‌شود)', log: 'لاگِ قدیمی (اول درایو، بعد حذف)', old_artifact: 'فایلِ کهنهٔ اسکن/آپلود (اول درایو، بعد حذف)' };

type Item = { path: string; kind: string; action: string; bytes: number; age_days: number };

export default function DiskPanel() {
  const [rep, setRep] = useState<any>(null);
  const [err, setErr] = useState('');
  const [prev, setPrev] = useState<{ items: Item[]; bytes: number } | null>(null);
  const [pick, setPick] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState('');

  const load = () => {
    fetch(`${API_BASE}/api/oversight/disk`).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setRep).catch((e) => setErr(String(e?.message || e)));
  };
  useEffect(load, []);

  const preview = async () => {
    setBusy(true); setDone('');
    try {
      const r = await fetch(`${API_BASE}/api/oversight/disk/cleanup-preview`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const p = await r.json();
      const sel: Record<string, boolean> = {};
      (p.items as Item[]).forEach((i) => { sel[i.path] = i.kind === 'cache'; });  // only re-creatable ones pre-ticked
      setPick(sel); setPrev(p);
    } catch (e: any) { setErr(String(e?.message || e)); } finally { setBusy(false); }
  };

  const apply = async () => {
    if (!prev) return;
    const paths = prev.items.filter((i) => pick[i.path]).map((i) => i.path);
    if (!paths.length) { setDone('چیزی انتخاب نشده'); return; }
    const bytes = prev.items.filter((i) => pick[i.path]).reduce((a, i) => a + i.bytes, 0);
    if (!window.confirm(`${paths.length.toLocaleString('fa-IR')} مورد (${mb(bytes)}) پاک‌سازی شود؟ لاگ‌ها و فایل‌های کهنه اول به گوگل درایو می‌روند.`)) return;
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/oversight/disk/cleanup`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paths, confirm: true }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.detail || `HTTP ${r.status}`);
      setDone(`✅ ${j.removed.toLocaleString('fa-IR')} مورد، ${mb(j.freed)} آزاد شد`
        + (j.kept?.length ? ` · ${j.kept.length.toLocaleString('fa-IR')} مورد ماند (${j.drive ? 'آپلود به درایو تأیید نشد' : 'درایو وصل نیست'})` : '')
        + (j.errors?.length ? ` · خطا: ${j.errors.slice(0, 2).join('، ')}` : ''));
      setPrev(null); load();
    } catch (e: any) { setDone(`❌ ${e?.message || e}`); } finally { setBusy(false); }
  };

  const b = rep?.breakdown || {};
  return (
    <div id="disk" className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-xs" data-report-section="oversight-disk" data-report-section-label="دیسکِ سرور">
      <div className="font-semibold mb-2 text-sm">💾 دیسکِ سرور (۱ گیگ) — چه چیزی جا گرفته</div>
      {err && <div className="text-red-600">گزارشِ دیسک خوانده نشد: {err}</div>}
      {!rep && !err && <div className="text-gray-500">…</div>}
      {rep && (
        <>
          <div className="mb-2">
            <b>{rep.percent?.toLocaleString('fa-IR')}%</b> پر — {mb(rep.used)} از {mb(rep.total)} · آزاد {mb(rep.free)}
            {rep.last_run && <> · آخرین پاک‌سازیِ خودکار: {mb(rep.last_run.freed)} آزاد{rep.last_run.drive ? '' : ' (درایو وصل نیست)'}</>}
            {b.root_bytes != null && rep.used != null && <> · پوشهٔ دادهٔ برنامه {mb(b.root_bytes)}</>}
          </div>
          {b.error && <div className="text-red-600">ریزِ مصرف خوانده نشد: {b.error}</div>}
          <div className="grid md:grid-cols-3 gap-3">
            {[['۱۰ پوشهٔ بزرگ', b.top_dirs], ['۱۰ فایلِ بزرگ', b.top_files]].map(([title, rows]: any) => (
              <div key={title}>
                <div className="font-semibold mb-1">{title}</div>
                <ol className="list-decimal pr-5 space-y-0.5">
                  {(rows || []).map((r: any) => <li key={r.path}><span dir="ltr">{r.path}</span> — {mb(r.bytes)}</li>)}
                </ol>
              </div>
            ))}
            <div>
              <div className="font-semibold mb-1">جدول‌های بزرگِ پایگاه‌داده</div>
              <ol className="list-decimal pr-5 space-y-0.5">
                {(b.db_tables || []).map((t: any) => (
                  <li key={t.table || t.error}><span dir="ltr">{t.table || t.error}</span>{t.bytes != null ? ` — ${mb(t.bytes)}` : t.rows != null ? ` — ${t.rows.toLocaleString('fa-IR')} سطر` : ''}</li>
                ))}
              </ol>
            </div>
          </div>
          <div className="mt-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 p-2">
            🧹 پاک‌سازیِ امن: فقط کش‌ها و فایل‌های موقت حذف می‌شوند؛ لاگ‌های قدیمی و فایل‌های کهنهٔ اسکن/آپلود اول به گوگل درایو می‌روند
            و فقط وقتی درایو نسخه را تأیید کرد از سرور برداشته می‌شوند. پایگاه‌داده و فایل‌های دادهٔ اتاق فرمان هرگز در فهرست نیستند.
            هشدارِ تلگرام وقتی دیسک از ۸۵٪ گذشت.
            <div className="mt-2 flex gap-2">
              <button disabled={busy} onClick={preview} className="rounded bg-amber-600 text-white px-3 py-1 disabled:opacity-50">پیش‌نمایشِ پاک‌سازی</button>
              {prev && <button disabled={busy} onClick={apply} className="rounded bg-red-600 text-white px-3 py-1 disabled:opacity-50">پاک‌سازیِ انتخاب‌شده‌ها</button>}
            </div>
            {done && <div className="mt-2">{done}</div>}
            {prev && (
              <div className="mt-2">
                {prev.items.length === 0 ? <div>چیزی برای پاک‌سازیِ امن پیدا نشد.</div> : (
                  <>
                    <div className="mb-1">{prev.items.length.toLocaleString('fa-IR')} مورد، روی‌هم {mb(prev.bytes)}:</div>
                    <ul className="space-y-0.5 max-h-64 overflow-auto">
                      {prev.items.map((i) => (
                        <li key={i.path}>
                          <label className="flex gap-2 items-start">
                            <input type="checkbox" checked={!!pick[i.path]} onChange={(e) => setPick({ ...pick, [i.path]: e.target.checked })} />
                            <span><span dir="ltr">{i.path}</span> — {mb(i.bytes)} · {i.age_days.toLocaleString('fa-IR')} روز · {KIND[i.kind] || i.kind}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
