'use client';

/**
 * PM-INS-0024 «الف» — «لاگ رندر › آرشیو» › ☁️ بایگانیِ درایو: old render_logs / ai_logs rows that were moved to Google
 * Drive (gz JSON-lines) and deleted from the database — a preview with before/after numbers, the explicit-confirm move,
 * the list of archive files, and a search inside them. Backend: services/log_archive.py, /api/render/log-archive/*.
 */
import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const fa = (n: number) => (n ?? 0).toLocaleString('fa-IR');
const T: Record<string, string> = { render_logs: 'لاگ‌های رندر', ai_logs: 'لاگ‌های مصرفِ AI' };

export default function LogDriveArchive() {
  const [preview, setPreview] = useState<any>(null);
  const [job, setJob] = useState<any>(null);
  const [list, setList] = useState<any[]>([]);
  const [table, setTable] = useState('render_logs');
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const [p, l, j] = await Promise.all([
      fetch(`${API_BASE}/api/render/log-archive/preview`).then((r) => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/render/log-archive/list`).then((r) => r.json()).catch(() => ({ archives: [] })),
      fetch(`${API_BASE}/api/render/log-archive/status`).then((r) => r.json()).catch(() => null),
    ]);
    setPreview(p); setList(l?.archives || []); setJob(j);
  };
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    if (!job?.running) return;
    const t = setInterval(() => { void load(); }, 5000);
    return () => clearInterval(t);
  }, [job?.running]);

  const run = async () => {
    const n = (preview?.render_logs?.to_move || 0) + (preview?.ai_logs?.to_move || 0);
    if (!window.confirm(`${fa(n)} ردیفِ قدیمی اول به گوگل درایو می‌رود و فقط پس از تأییدِ درایو از پایگاه‌داده حذف می‌شود. ادامه؟`)) return;
    setBusy(true);
    try {
      await fetch(`${API_BASE}/api/render/log-archive/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }),
      });
      await load();
    } finally { setBusy(false); }
  };

  const search = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/render/log-archive/search?table=${table}&q=${encodeURIComponent(q)}&limit=200`);
      setHits(await r.json());
    } finally { setBusy(false); }
  };

  return (
    <div dir="rtl" className="rounded-lg border border-sky-200 dark:border-sky-800 bg-sky-50/50 dark:bg-sky-900/10 p-4 space-y-3 text-sm">
      <div className="font-bold">☁️ بایگانیِ درایو — لاگ‌های قدیمی بیرون از پایگاه‌داده</div>
      {preview && (
        <div className="grid md:grid-cols-2 gap-2 text-xs">
          {(['render_logs', 'ai_logs'] as const).map((k) => (
            <div key={k} className="rounded border border-gray-200 dark:border-gray-700 p-2 bg-white dark:bg-gray-800">
              <div className="font-semibold">{T[k]}</div>
              <div>در پایگاه‌داده: {fa(preview[k]?.total)} ردیف</div>
              <div>قدیمی‌تر از نگه‌داری ({k === 'render_logs' ? '۴۸ ساعت' : '۳۰ روز'}): <b>{fa(preview[k]?.to_move)}</b></div>
              {preview[k]?.oldest && <div className="text-gray-500">قدیمی‌ترین: {new Date(preview[k].oldest + 'Z').toLocaleString('fa-IR')}</div>}
            </div>
          ))}
        </div>
      )}
      {preview && !preview.drive_connected && <div className="text-red-600">گوگل درایو وصل نیست — هیچ ردیفی حذف نمی‌شود.</div>}
      <div className="flex gap-2 flex-wrap items-center">
        <button disabled={busy || job?.running || !preview?.drive_connected} onClick={run}
          className="rounded bg-sky-600 text-white px-3 py-1.5 disabled:opacity-50">☁️ انتقال به درایو و حذف از پایگاه‌داده</button>
        <span className="text-xs text-gray-500">هر ۶ ساعت هم خودکار با همین قاعده اجرا می‌شود.</span>
      </div>
      {job?.running && <div className="text-xs">⏳ در حالِ انتقال… (شروع: {job.started_at})</div>}
      {job?.out && (
        <div className="text-xs rounded bg-white dark:bg-gray-800 p-2">
          آخرین اجرا: render_logs {fa(job.out.before?.render_logs?.total)} ⇐ {fa(job.out.after?.render_logs?.total)} ردیف
          ({fa(job.out.result?.render_logs?.moved)} در {fa(job.out.result?.render_logs?.files)} فایل) · ai_logs {fa(job.out.before?.ai_logs?.total)} ⇐ {fa(job.out.after?.ai_logs?.total)}
          ({fa(job.out.result?.ai_logs?.moved)} در {fa(job.out.result?.ai_logs?.files)} فایل)
          {job.out.result?.ok === false && <span className="text-red-600"> — ناقص: {job.out.result?.render_logs?.error || job.out.result?.ai_logs?.error || job.out.result?.reason}</span>}
        </div>
      )}
      {job?.error && <div className="text-xs text-red-600">خطا: {job.error}</div>}

      <div className="flex gap-2 flex-wrap items-center">
        <select value={table} onChange={(e) => setTable(e.target.value)} className="border rounded p-1 text-xs dark:bg-gray-800">
          <option value="render_logs">{T.render_logs}</option>
          <option value="ai_logs">{T.ai_logs}</option>
        </select>
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void search(); }}
          placeholder="جست‌وجو در بایگانیِ درایو…" className="flex-1 min-w-[12rem] border rounded p-1 text-xs dark:bg-gray-800" />
        <button disabled={busy} onClick={search} className="rounded border px-3 py-1 text-xs">🔍 جست‌وجو</button>
      </div>
      {hits && (
        <div className="text-xs space-y-1 max-h-80 overflow-auto">
          <div className="text-gray-500">{hits.note} — {fa(hits.hits?.length)} نتیجه</div>
          {(hits.hits || []).map((h: any) => (
            <div key={h.id} className="font-mono border-b border-gray-100 dark:border-gray-700 py-0.5" dir="ltr">
              {(h.timestamp || h.created_at || '').slice(0, 19)} [{h.level || h.status}] {h.service_name || h.provider}: {(h.message || h.prompt || '').slice(0, 300)}
            </div>
          ))}
        </div>
      )}

      <div className="text-xs">
        <div className="font-semibold mb-1">فایل‌های بایگانی ({fa(list.length)})</div>
        <div className="max-h-56 overflow-auto space-y-0.5">
          {list.map((a) => (
            <div key={a.id} className="flex gap-2 flex-wrap">
              <span>{T[a.table] || a.table}</span>
              <span className="text-gray-500" dir="ltr">{a.start.slice(0, 16)} → {a.end.slice(0, 16)}</span>
              <span>{fa(a.rows)} ردیف</span>
              {a.link && <a className="text-sky-700 dark:text-sky-300 underline" href={a.link} target="_blank" rel="noreferrer">درایو</a>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
