'use client';

// (PM-INS-0013) «فیدِ رویدادِ همهٔ پروژه‌ها» — هر کامیت در هر مخزنِ تحتِ نظارت، با فایل‌هایی که افزوده/تغییر/حذف کرد.
// زنده از GitHub (کشِ ۵ دقیقه‌ای سمتِ سرور). با `repo` فقط همان مخزن.

import { useCallback, useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const STATUS_FA: Record<string, { label: string; cls: string }> = {
  added: { label: 'افزوده', cls: 'text-green-700' },
  modified: { label: 'تغییر', cls: 'text-blue-700' },
  removed: { label: 'حذف', cls: 'text-red-700' },
  renamed: { label: 'تغییرِ نام', cls: 'text-purple-700' },
};

function fmt(iso?: string) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleString('fa-IR', { dateStyle: 'short', timeStyle: 'short' }); } catch { return iso; }
}

export default function ProjectsEventFeed({ repo, limit = 60, title }: { repo?: string; limit?: number; title?: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [filter, setFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setErr('');
    try {
      const q = new URLSearchParams({ limit: String(limit) });
      if (repo) q.set('repo', repo);
      const r = await fetch(`${API_BASE}/api/project-supervision/feed?${q}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      setData(d);
    } catch (e: any) { setErr(e?.message || 'خوانده نشد'); } finally { setLoading(false); }
  }, [repo, limit]);

  useEffect(() => { load(); const t = setInterval(load, 5 * 60000); return () => clearInterval(t); }, [load]);

  const events: any[] = (data?.events || []).filter((e: any) => !filter || e.repo === filter);
  return (
    <div className="rounded-lg border p-3 dark:border-gray-700 bg-white dark:bg-gray-800" dir="rtl">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <div className="font-semibold">📡 {title || 'فیدِ رویدادِ همهٔ پروژه‌ها'}</div>
        {data && <span className="text-xs text-gray-500">
          فایل‌ها: {data.file_counts?.added ?? 0} افزوده · {data.file_counts?.modified ?? 0} تغییر · {data.file_counts?.removed ?? 0} حذف
        </span>}
        {!repo && data?.repos?.length > 1 && (
          <select value={filter} onChange={(e) => setFilter(e.target.value)} dir="ltr"
            className="mr-auto border rounded px-2 py-0.5 text-xs bg-white dark:bg-gray-900 dark:border-gray-600 max-w-full">
            <option value="">همهٔ {data.repos.length} مخزن</option>
            {data.repos.map((r: string) => <option key={r} value={r}>{r}</option>)}
          </select>
        )}
        <button onClick={load} className={`text-xs text-blue-600 hover:underline ${repo || !(data?.repos?.length > 1) ? 'mr-auto' : ''}`}>{loading ? '…' : 'بروزرسانی'}</button>
      </div>
      {err && <div className="text-sm text-red-600">⚠️ {err}</div>}
      {data?.unreachable?.length > 0 && <div className="text-xs text-amber-700 mb-1">خوانده نشد: <span dir="ltr">{data.unreachable.join(', ')}</span></div>}
      {data && events.length === 0 && !err && <div className="text-xs text-gray-500">رویدادی نیست{data.offline ? ' (حالتِ آفلاین)' : ''}.</div>}
      <ul className="space-y-2 max-h-[480px] overflow-auto text-sm">
        {events.map((e) => (
          <li key={`${e.repo}-${e.sha}`} className="border-b last:border-0 pb-2 dark:border-gray-700">
            <div className="flex flex-wrap gap-x-2 text-xs text-gray-500">
              {!repo && <span className="font-mono" dir="ltr">{e.repo.split('/')[1] || e.repo}</span>}
              <a href={e.url} target="_blank" rel="noopener noreferrer" className="font-mono text-blue-600" dir="ltr">{e.sha}</a>
              <span>{fmt(e.date)}</span><span>{e.author}</span>
            </div>
            <div className="break-words" dir="auto">{e.message}</div>
            {Array.isArray(e.files) && e.files.length > 0 && (
              <details className="text-xs mt-1">
                <summary className="cursor-pointer text-gray-600">{e.files.length} فایل</summary>
                <ul className="mt-1 space-y-0.5">
                  {e.files.map((f: any) => (
                    <li key={f.path} className="flex gap-2"><span className={`shrink-0 ${STATUS_FA[f.status]?.cls || ''}`}>{STATUS_FA[f.status]?.label || f.status}</span>
                      <span className="font-mono break-all" dir="ltr">{f.path}</span></li>
                  ))}
                </ul>
              </details>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
