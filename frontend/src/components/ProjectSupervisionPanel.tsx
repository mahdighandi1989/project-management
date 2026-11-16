'use client';

// (PM-INS-0013) «نظارت و سرکشیِ همین پروژه» — فقط‌خواندنی و زنده: برگه‌های باز/فوری/پاسخ‌داده و زمانِ دورِ بعدیِ ناظر،
// به‌اضافهٔ آنچه در خودِ مخزن از ناظر هست (نسخهٔ دستورها، شاخه‌های supervisor-pending، کامیت‌های برگه‌ها).
// هر پروژه برگه‌های خودش را روی سرورِ خودش دارد؛ تا نشانیِ آن سرور در Render تنظیم نشده، همین را صریح می‌گوید.

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import ProjectsEventFeed from './ProjectsEventFeed';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Sheet = { number: number; ref: string; title: string; status: string; urgent: boolean; page_label: string; outcome: string; updated: string };

function fmt(iso?: string | null) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('fa-IR', { dateStyle: 'short', timeStyle: 'short' }); } catch { return iso; }
}

function nextRoundText(nr: any): string {
  if (!nr) return '—';
  if (typeof nr === 'string') return fmt(nr);
  const basis: Record<string, string> = { assumed: 'برآورد', observed: 'سنجیده', due: 'عقب‌افتاده', stale: 'مدتی خبری نیست' };
  return fmt(nr.at) + (nr.basis ? ` (${basis[nr.basis] || nr.basis})` : '');
}

function SheetList({ title, items, tone }: { title: string; items: Sheet[]; tone: string }) {
  return (
    <div className={`rounded-lg border p-3 ${tone}`}>
      <div className="font-semibold mb-2">{title} ({items.length})</div>
      {items.length === 0 ? <div className="text-xs text-gray-500">موردی نیست</div> : (
        <ul className="space-y-1 text-sm max-h-64 overflow-auto">
          {items.map((s) => (
            <li key={`${s.ref}-${s.number}`} className="flex gap-2 items-start">
              <span className="font-mono text-xs shrink-0 mt-0.5" dir="ltr">{s.ref || `#${s.number}`}</span>
              <span className="flex-1 break-words">{s.title || '—'}</span>
              {s.outcome && <span className="text-xs text-gray-500 shrink-0">{s.outcome}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ProjectSupervisionPanel({ repo: initialRepo }: { repo?: string }) {
  const [repos, setRepos] = useState<{ repo: string; self: boolean }[]>([]);
  const [repo, setRepo] = useState<string>(initialRepo || '');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/project-supervision/repos`).then((r) => r.json()).then((d) => {
      const list = d.repos || [];
      setRepos(list);
      setRepo((cur) => cur || list.find((x: any) => x.self)?.repo || list[0]?.repo || '');
    }).catch(() => setRepos([]));
  }, []);

  const load = useCallback(async () => {
    if (!repo) return;
    setLoading(true); setErr('');
    try {
      const r = await fetch(`${API_BASE}/api/project-supervision/board?repo=${encodeURIComponent(repo)}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      setData(d);
    } catch (e: any) {
      setErr(e?.message || 'خوانده نشد'); setData(null);
    } finally { setLoading(false); }
  }, [repo]);

  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, [load]);

  const live = data?.live || {};
  const git = data?.git || {};
  return (
    <div className="space-y-4" dir="rtl">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-bold text-lg">🛡️ نظارت و سرکشیِ همین پروژه</h3>
        <span className="text-xs text-gray-500">فقط‌خواندنی · هر ۶۰ ثانیه تازه می‌شود</span>
        <select value={repo} onChange={(e) => setRepo(e.target.value)} dir="ltr"
          className="mr-auto border rounded px-2 py-1 text-sm bg-white dark:bg-gray-800 dark:border-gray-600 max-w-full">
          {repo && !repos.some((r) => r.repo === repo) && <option value={repo}>{repo}</option>}
          {repos.map((r) => <option key={r.repo} value={r.repo}>{r.repo}{r.self ? ' (همین برنامه)' : ''}</option>)}
        </select>
        <button onClick={load} className="text-sm text-blue-600 hover:underline">{loading ? '…' : 'بروزرسانی'}</button>
      </div>
      {!initialRepo && <div className="text-xs text-amber-700">این پروژه به مخزنِ GitHub وصل نیست؛ از فهرست یکی از مخزن‌های تحتِ نظارت را انتخاب کنید.</div>}
      {err && <div className="text-sm text-red-600">⚠️ {err}</div>}

      {data && (
        <>
          <div className="rounded-lg border p-3 bg-gray-50 dark:bg-gray-800 dark:border-gray-700 text-sm space-y-1">
            {live.configured === false || live.ok === false ? (
              <div className="text-amber-700">برگه‌های زندهٔ این پروژه روی سرورِ خودش است و خوانده نشد: {live.reason}</div>
            ) : (
              <div className="flex flex-wrap gap-x-6 gap-y-1">
                <span>باز: <b>{live.counts?.open ?? 0}</b></span>
                <span>پاسخ‌داده: <b>{live.counts?.answered ?? 0}</b></span>
                <span>تأییدشده: <b>{live.counts?.approved ?? 0}</b></span>
                <span>⚡ فوریِ در انتظار: <b>{live.urgent_waiting ?? 0}</b></span>
                <span>دورِ بعدیِ صفِ فوری: <b>{nextRoundText(live.next_round)}</b></span>
                <span>بازرسیِ کاملِ بعدی: <b>{fmt(live.next_full)}</b></span>
              </div>
            )}
            {data.self && <Link href="/inspection" className="text-blue-600 hover:underline text-xs">باز کردنِ برگه‌ها در «نظارت و سرکشی» ←</Link>}
          </div>

          {live.ok && (
            <div className="grid md:grid-cols-3 gap-3">
              <SheetList title="⚡ فوری" items={live.urgent || []} tone="border-red-200 dark:border-red-900" />
              <SheetList title="🟡 باز" items={live.open || []} tone="border-amber-200 dark:border-amber-900" />
              <SheetList title="✅ پاسخ‌داده" items={live.answered || []} tone="border-green-200 dark:border-green-900" />
            </div>
          )}

          <div className="rounded-lg border p-3 dark:border-gray-700 text-sm space-y-2">
            <div className="font-semibold">ناظرِ این پروژه در خودِ مخزن <span className="text-xs text-gray-500">({git.source})</span></div>
            {git.has_supervisor_dir === false && <div className="text-gray-500">پوشهٔ docs/supervisor در این مخزن نیست.</div>}
            {(git.prompts || []).map((p: any) => (
              <div key={p.file} className="flex flex-wrap gap-3"><span className="font-mono text-xs" dir="ltr">{p.file}</span>
                <span>نسخه: <b>{p.version || '—'}</b></span><span>به‌روز: {p.updated || '—'}</span></div>
            ))}
            <div>شاخه‌های کارِ جامانده (supervisor-pending): {(git.pending_branches || []).length
              ? <span className="font-mono text-xs" dir="ltr">{git.pending_branches.join(', ')}</span> : 'هیچ'}</div>
            {(git.supervisor_commits || []).length > 0 && (
              <details>
                <summary className="cursor-pointer">کامیت‌های ناظر/برگه‌ها ({git.supervisor_commits.length})</summary>
                <ul className="mt-1 space-y-1 text-xs max-h-60 overflow-auto">
                  {git.supervisor_commits.map((c: any) => (
                    <li key={c.sha} className="break-words"><a href={c.url} target="_blank" rel="noopener noreferrer" className="font-mono text-blue-600" dir="ltr">{c.sha}</a> · {fmt(c.date)} · {c.message}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>

          <ProjectsEventFeed repo={repo} limit={20} title="رویدادهای همین مخزن" />
        </>
      )}
    </div>
  );
}
