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
import DiskGauge from './DiskGauge';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const mb = (b: number) => `${((b || 0) / 1048576).toLocaleString('fa-IR', { maximumFractionDigits: 1 })}MB`;
const KIND: Record<string, string> = { cache: 'کش/موقت (حذف — دوباره ساخته می‌شود)', log: 'لاگِ قدیمی (اول درایو، بعد حذف)', old_artifact: 'فایلِ کهنهٔ اسکن/آپلود/شواهد (اول درایو، بعد حذف)' };

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

  // PM-INS-0032 — guarded VACUUM (backup to Drive first) and search of what went to Drive
  const [vac, setVac] = useState('');
  const vacuum = async () => {
    const p = rep?.db_space;
    if (!window.confirm(`پشتیبانِ کاملِ پایگاه‌داده اول به گوگل درایو می‌رود، بعد VACUUM ${p ? mb(p.free_bytes) : ''} فضای خالیِ داخلِ آن را به دیسک برمی‌گرداند. ادامه؟`)) return;
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/oversight/disk/vacuum`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }) });
      const j = await r.json();
      setVac(j.started ? '⏳ شروع شد — پشتیبان به درایو، بعد VACUUM. چند دقیقه بعد صفحه را تازه کن.' : `❌ ${j.reason || 'شروع نشد'}`);
    } catch (e: any) { setVac(`❌ ${e?.message || e}`); } finally { setBusy(false); }
  };
  const [aq, setAq] = useState('');
  const [arch, setArch] = useState<any>(null);
  const searchArchives = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/oversight/disk/archives?q=${encodeURIComponent(aq)}`);
      setArch(r.ok ? await r.json() : { error: `HTTP ${r.status}` });
    } catch (e: any) { setArch({ error: String(e?.message || e) }); } finally { setBusy(false); }
  };

  const b = rep?.breakdown || {};
  return (
    <div id="disk" className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-xs" data-report-section="oversight-disk" data-report-section-label="دیسکِ سرور">
      <div className="font-semibold mb-2 text-sm">💾 دیسکِ سرور (۱ گیگ) — چه چیزی جا گرفته</div>
      <div className="mb-2"><DiskGauge link={false} /></div>
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
          {Array.isArray(rep.consumers) && rep.consumers.length > 0 && (
            <div className="mb-3" data-testid="disk-consumers">
              <div className="font-semibold mb-1">سهمِ هر بخش</div>
              <table className="w-full">
                <tbody>
                  {rep.consumers.map((c: any) => {
                    const g = (rep.growth?.groups || []).find((x: any) => x.label === c.label);
                    return (
                      <tr key={c.label} className="border-t border-gray-100 dark:border-gray-800">
                        <td className="py-0.5">{c.label}</td>
                        <td className="py-0.5 whitespace-nowrap">{mb(c.bytes)}{c.free_inside ? ` (خالیِ داخلِ آن ${mb(c.free_inside)})` : ''}</td>
                        <td className="py-0.5 whitespace-nowrap text-gray-500">{g && g.delta ? `${g.delta > 0 ? '+' : '−'}${mb(Math.abs(g.delta))}` : ''}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="text-gray-500 mt-1">
                {rep.growth?.since ? `ستونِ آخر: تغییر از ${new Date(rep.growth.since).toLocaleString('fa-IR')} (عکس‌برداری هر ۶ ساعت)` : 'تاریخچهٔ رشد تازه شروع شده — هر ۶ ساعت یک عکس'}
              </div>
            </div>
          )}
          {rep.db_space?.free_bytes != null && (
            <div className="mb-3 rounded-lg bg-sky-50 dark:bg-sky-900/20 p-2" data-testid="disk-vacuum">
              🗜️ پایگاه‌داده {mb(rep.db_space.file_bytes)} است ولی فقط {mb(rep.db_space.used_bytes)} داده دارد — {mb(rep.db_space.free_bytes)} جای خالیِ ردیف‌های حذف‌شده
              (WAL {mb(rep.db_space.wal_bytes)}). VACUUM آن را به دیسک برمی‌گرداند؛ اول پشتیبانِ کامل به گوگل درایو می‌رود.
              {rep.vacuum_plan && !rep.vacuum_plan.possible && rep.vacuum_plan.reason && <div className="mt-1">⛔ {rep.vacuum_plan.reason}</div>}
              {rep.vacuum_plan?.state?.state && rep.vacuum_plan.state.state !== 'idle' && (
                <div className="mt-1">وضعیتِ آخرین VACUUM: {rep.vacuum_plan.state.state}{rep.vacuum_plan.state.error ? ` — ${rep.vacuum_plan.state.error}` : ''}
                  {rep.vacuum_plan.state.after ? ` — ${mb(rep.vacuum_plan.state.before)} ⇐ ${mb(rep.vacuum_plan.state.after)}` : ''}</div>
              )}
              <div className="mt-1">
                <button disabled={busy || !rep.vacuum_plan?.possible} onClick={vacuum} className="rounded bg-sky-700 text-white px-3 py-1 disabled:opacity-50">پشتیبان به درایو + VACUUM</button>
              </div>
              {vac && <div className="mt-1">{vac}</div>}
            </div>
          )}
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
            <div className="mt-3 border-t border-amber-200 dark:border-amber-800 pt-2" data-testid="disk-archives">
              🔎 جست‌وجو در آنچه به درایو رفته (شواهد، اسکن‌ها، لاگ‌ها، گزارش‌ها، پشتیبان‌های پایگاه‌داده):
              <div className="mt-1 flex gap-2">
                <input value={aq} onChange={(e) => setAq(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') searchArchives(); }}
                  placeholder="نامِ تسک، شمارهٔ گزارش، تاریخ…" className="flex-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1" />
                <button disabled={busy} onClick={searchArchives} className="rounded bg-gray-700 text-white px-3 py-1 disabled:opacity-50">جست‌وجو</button>
              </div>
              {arch?.error && <div className="mt-1 text-red-600">{arch.error}</div>}
              {arch && !arch.error && (arch.drive === false ? <div className="mt-1">گوگل درایو وصل نیست.</div> : (
                <ul className="mt-1 space-y-0.5 max-h-64 overflow-auto">
                  {(arch.files || []).length === 0 && <li>چیزی پیدا نشد.</li>}
                  {(arch.files || []).map((f: any) => (
                    <li key={f.id}><a href={f.link} target="_blank" rel="noreferrer" className="text-blue-600 underline" dir="ltr">{f.name}</a> — {f.kind} · {mb(f.bytes)} · {f.created ? new Date(f.created).toLocaleDateString('fa-IR') : ''}</li>
                  ))}
                </ul>
              ))}
            </div>
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
