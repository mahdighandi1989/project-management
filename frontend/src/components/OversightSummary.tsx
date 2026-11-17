'use client';

/**
 * PM-INS-0020 (بندِ ۱۳) — «اتاق فرمان» on one page, at the top of /oversight: what runs automatically right now and what
 * is off and why, the 10 most important open tasks, and a SAFE cleanup of duplicate/stale tasks (preview → tick → confirm;
 * archived with a reason, never deleted). Backend: services/oversight_summary.py, GET /api/oversight/summary.
 */
import { useEffect, useState } from 'react';
import DiskPanel from './DiskPanel';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Summary = {
  generated_at: string;
  models_on: number;
  totals: { watched: number; tasks_open: number; tasks_archived: number; reports: number; open_by_status: Record<string, number> };
  automation: { watched_id: string; repo: string; on: string[]; off: string[] }[];
  top_tasks: { id: string; title: string; repo: string; priority: string; status: string; verification_status: string }[];
  cleanup: { duplicates: number; duplicate_tasks: number; stale: number };
  // (PM-INS-0026 «ب») when did a task REALLY run, and can anything change code right now
  last_real_run?: { line: string; safe_path: string; runner_on: string[]; allow_push_on: string[]; auto_but_verify_only: string[];
    task_days_ago: number | null };
};
type Preview = {
  stale_days: number;
  duplicate_groups: { repo: string; keep: { id: string; title: string; status: string }; archive: { id: string; title: string; status: string }[] }[];
  stale: { id: string; title: string; repo: string; status: string; days: number }[];
};

const fa = (n: number) => (n ?? 0).toLocaleString('fa-IR');
const PRIO: Record<string, string> = { critical: '🔴 بحرانی', high: '🟠 بالا', medium: '🟡 متوسط', low: '⚪ کم' };
const STATUS: Record<string, string> = {
  suggested: 'پیشنهادِ اسکن', pending: 'در انتظار', awaiting_review: 'منتظرِ بازبینی', running: 'در حال اجرا', failed: 'ناموفق',
};

export default function OversightSummary({ onOpenTask }: { onOpenTask?: (id: string) => void }) {
  const [open, setOpen] = useState(true);
  const [data, setData] = useState<Summary | null>(null);
  const [err, setErr] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [pick, setPick] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState('');

  const load = () => {
    fetch(`${API_BASE}/api/oversight/summary`).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData).catch((e) => setErr(String(e?.message || e)));
  };
  useEffect(load, []);

  const openPreview = async () => {
    setBusy(true); setDone('');
    try {
      const r = await fetch(`${API_BASE}/api/oversight/summary/cleanup-preview`);
      const p: Preview = await r.json();
      const sel: Record<string, boolean> = {};
      p.duplicate_groups.forEach((g) => g.archive.forEach((a) => { sel[`d:${g.keep.id}:${a.id}`] = true; }));
      p.stale.forEach((s) => { sel[`s:${s.id}`] = false; });  // stale ones only when the owner ticks them
      setPick(sel); setPreview(p);
    } catch (e: any) { setErr(String(e?.message || e)); } finally { setBusy(false); }
  };

  const apply = async () => {
    if (!preview) return;
    const merge: { keep: string; archive: string[] }[] = [];
    preview.duplicate_groups.forEach((g) => {
      const ids = g.archive.filter((a) => pick[`d:${g.keep.id}:${a.id}`]).map((a) => a.id);
      if (ids.length) merge.push({ keep: g.keep.id, archive: ids });
    });
    const stale_ids = preview.stale.filter((s) => pick[`s:${s.id}`]).map((s) => s.id);
    const n = merge.reduce((a, g) => a + g.archive.length, 0) + stale_ids.length;
    if (!n) { setDone('چیزی انتخاب نشده'); return; }
    if (!window.confirm(`${fa(n)} تسک بایگانی می‌شود (حذف نه — از «آرشیو» قابلِ بازگردانی است). ادامه؟`)) return;
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/oversight/summary/cleanup`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merge, stale_ids, confirm: true }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.detail || `HTTP ${r.status}`);
      setDone(`✅ ${fa(j.merged)} تکراری ادغام و ${fa(j.archived_stale)} کهنه بایگانی شد — ${j.note}`);
      setPreview(null); load();
    } catch (e: any) { setDone(`❌ ${e?.message || e}`); } finally { setBusy(false); }
  };

  return (
    <section dir="rtl" className="mb-6 rounded-2xl border-2 border-indigo-200 dark:border-indigo-800 bg-white dark:bg-gray-800 shadow-sm"
      data-report-section="oversight-summary" data-report-section-label="خلاصهٔ یک‌صفحه‌ای">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-4 py-3 text-right">
        <span className="font-bold text-indigo-900 dark:text-indigo-200">📋 خلاصهٔ یک‌صفحه‌ایِ اتاق فرمان</span>
        <span className="text-xs text-gray-500">{open ? '▲ بستن' : '▼ باز کردن'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-4 text-sm">
          {err && <div className="text-red-600">خلاصه خوانده نشد: {err}</div>}
          {!data && !err && <div className="text-gray-500">…</div>}
          {data && (
            <>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-lg bg-gray-100 dark:bg-gray-700 px-2 py-1">{fa(data.totals.watched)} مخزن</span>
                <span className="rounded-lg bg-gray-100 dark:bg-gray-700 px-2 py-1">{fa(data.totals.tasks_open)} تسکِ باز</span>
                {Object.entries(data.totals.open_by_status).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <span key={k} className="rounded-lg bg-gray-50 dark:bg-gray-900 px-2 py-1">{STATUS[k] || k}: {fa(v)}</span>
                ))}
                <span className="rounded-lg bg-gray-100 dark:bg-gray-700 px-2 py-1">{fa(data.totals.tasks_archived)} بایگانی</span>
                <span className="rounded-lg bg-gray-100 dark:bg-gray-700 px-2 py-1">{fa(data.totals.reports)} گزارش</span>
                <span className={`rounded-lg px-2 py-1 ${data.models_on > 0 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200' : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'}`}>
                  {data.models_on > 0 ? `${fa(data.models_on)} مدلِ روشن` : 'هیچ مدلی روشن نیست'}
                </span>
              </div>

              {data.last_real_run && (
                <div data-testid="oversight-last-real-run"
                  className={`rounded-lg p-2 text-xs ${(data.last_real_run.task_days_ago ?? 999) > 14 || data.last_real_run.runner_on.length === 0
                    ? 'bg-amber-50 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100' : 'bg-gray-50 dark:bg-gray-700/40'}`}>
                  <div className="font-semibold">⏱ {data.last_real_run.line}</div>
                  {data.last_real_run.auto_but_verify_only.length > 0 && (
                    <div className="mt-1">ℹ️ «خودمختاری: auto» ولی «فقط verify» هم روشن است (پس فقط verify اجرا می‌شود): {data.last_real_run.auto_but_verify_only.join('، ')}</div>
                  )}
                  <div className="mt-1 opacity-80">🛡 {data.last_real_run.safe_path}</div>
                </div>
              )}

              <div>
                <div className="font-semibold mb-1">⚙️ الان چه چیزی خودکار اجرا می‌شود و چه چیزی خاموش است</div>
                <div className="grid md:grid-cols-2 gap-2">
                  {data.automation.map((a) => (
                    <div key={a.watched_id} className="rounded-lg border border-gray-200 dark:border-gray-700 p-2 text-xs">
                      <div className="font-semibold mb-1" dir="ltr">{a.repo}</div>
                      {a.on.map((x) => <div key={x} className="text-emerald-700 dark:text-emerald-300">▶️ {x}</div>)}
                      {a.off.map((x) => <div key={x} className="text-gray-500 dark:text-gray-400">⏸ {x}</div>)}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="font-semibold mb-1">🎯 ۱۰ تسکِ مهمِ باز</div>
                <ol className="space-y-1 text-xs list-decimal pr-5">
                  {data.top_tasks.map((t) => (
                    <li key={t.id}>
                      <button className="hover:underline text-right" onClick={() => onOpenTask?.(t.id)}>
                        {PRIO[t.priority] || t.priority} · {t.title}
                      </button>
                      <span className="text-gray-500"> — <span dir="ltr">{t.repo}</span> · {STATUS[t.status] || t.status}
                        {t.verification_status ? ` · verify: ${t.verification_status}` : ''}</span>
                    </li>
                  ))}
                </ol>
              </div>

              <DiskPanel />

              <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 p-3 text-xs">
                <div className="mb-2">
                  🧹 {fa(data.cleanup.duplicate_tasks)} تسکِ تکراری در {fa(data.cleanup.duplicates)} گروه و {fa(data.cleanup.stale)} تسکِ کهنه
                  (پیشنهاد/در انتظار بی‌تغییر بیش از ۴۵ روز) قابلِ پاک‌سازی‌اند. پاک‌سازی = <b>بایگانی</b> با دلیل، نه حذف؛ اول پیش‌نمایش، بعد تأییدِ شما.
                </div>
                <button disabled={busy} onClick={openPreview}
                  className="rounded-lg bg-amber-600 text-white px-3 py-1.5 disabled:opacity-60">🔍 پیش‌نمایشِ پاک‌سازی/ادغام</button>
                {done && <div className="mt-2">{done}</div>}
              </div>
            </>
          )}
        </div>
      )}

      {preview && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setPreview(null)}>
          <div dir="rtl" className="w-full max-w-3xl max-h-[85vh] overflow-auto rounded-2xl bg-white dark:bg-gray-800 p-4 text-xs"
            onClick={(e) => e.stopPropagation()}>
            <div className="font-bold text-sm mb-2">پیش‌نمایشِ پاک‌سازی — هیچ چیزی تا «تأیید» تغییر نمی‌کند</div>
            <div className="font-semibold mt-2 mb-1">🔁 تکراری‌ها ({fa(preview.duplicate_groups.length)} گروه) — نگه‌داشته‌شده ✅، تیک‌خورده‌ها در آن ادغام و بایگانی می‌شوند</div>
            {preview.duplicate_groups.map((g) => (
              <div key={g.keep.id} className="mb-2 rounded border border-gray-200 dark:border-gray-700 p-2">
                <div className="text-gray-500" dir="ltr">{g.repo}</div>
                <div>✅ نگه‌داشته: {g.keep.title} <span className="text-gray-500">({STATUS[g.keep.status] || g.keep.status})</span></div>
                {g.archive.map((a) => (
                  <label key={a.id} className="flex gap-2 items-start mr-4">
                    <input type="checkbox" checked={!!pick[`d:${g.keep.id}:${a.id}`]}
                      onChange={(e) => setPick({ ...pick, [`d:${g.keep.id}:${a.id}`]: e.target.checked })} />
                    <span>{a.title} <span className="text-gray-500">({STATUS[a.status] || a.status})</span></span>
                  </label>
                ))}
              </div>
            ))}
            <div className="font-semibold mt-3 mb-1">🕰 کهنه‌ها ({fa(preview.stale.length)}) — پیش‌فرض تیک‌نخورده؛ هر کدام را می‌خواهید بایگانی شود تیک بزنید</div>
            {preview.stale.slice(0, 300).map((s) => (
              <label key={s.id} className="flex gap-2 items-start">
                <input type="checkbox" checked={!!pick[`s:${s.id}`]} onChange={(e) => setPick({ ...pick, [`s:${s.id}`]: e.target.checked })} />
                <span>{s.title} <span className="text-gray-500">— <span dir="ltr">{s.repo}</span> · {fa(s.days)} روز بی‌تغییر</span></span>
              </label>
            ))}
            {preview.stale.length > 300 && <div className="text-gray-500">… و {fa(preview.stale.length - 300)} مورد دیگر (فقط ۳۰۰ ِ قدیمی‌ترین نشان داده شد)</div>}
            <div className="flex gap-2 mt-4 sticky bottom-0 bg-white dark:bg-gray-800 pt-2">
              <button disabled={busy} onClick={apply} className="rounded-lg bg-amber-600 text-white px-3 py-1.5 disabled:opacity-60">✅ تأیید و بایگانی</button>
              <button onClick={() => setPreview(null)} className="rounded-lg border px-3 py-1.5">انصراف</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
