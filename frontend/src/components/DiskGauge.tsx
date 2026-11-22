'use client';

/**
 * PM-INS-0032 (2026-11-22) — «نشانگرِ دائمیِ دیسک: ٪ + آزاد + بزرگ‌ترین مصرف‌کننده‌ها» با هشدارِ بالای ۸۰٪.
 * Shown in «نظارت و سرکشی › فضای ذخیره‌سازی» and at the top of the disk panel in «اتاق فرمان» (/oversight#disk).
 * Backend: GET /api/oversight/disk/status (services/disk_janitor.status) — the same GET the coordinator reads.
 */
import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const mb = (b: number) => `${((b || 0) / 1048576).toLocaleString('fa-IR', { maximumFractionDigits: 1 })}MB`;

export default function DiskGauge({ link = true }: { link?: boolean }) {
  const [st, setSt] = useState<any>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    let live = true;
    const load = () => fetch(`${API_BASE}/api/oversight/disk/status`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((j) => { if (live) { setSt(j); setErr(''); } })
      .catch((e) => { if (live) setErr(String(e?.message || e)); });
    load();
    const t = setInterval(load, 5 * 60 * 1000);
    return () => { live = false; clearInterval(t); };
  }, []);

  if (err) return <div className="text-xs text-red-600" data-testid="disk-gauge">💾 وضعیتِ دیسک خوانده نشد: {err}</div>;
  if (!st) return <div className="text-xs text-gray-500" data-testid="disk-gauge">💾 …</div>;
  const pct = Number(st.percent || 0);
  const color = st.level === 'critical' ? 'bg-red-600' : st.level === 'warn' ? 'bg-amber-500' : 'bg-emerald-600';
  const box = st.level === 'ok' ? 'border-gray-200 dark:border-gray-700'
    : st.level === 'critical' ? 'border-red-400 bg-red-50 dark:bg-red-900/20' : 'border-amber-400 bg-amber-50 dark:bg-amber-900/20';
  return (
    <div className={`rounded-lg border p-2 text-xs ${box}`} data-testid="disk-gauge" data-report-section="disk-gauge" data-report-section-label="نشانگرِ دیسک">
      <div className="flex flex-wrap items-center gap-2">
        <b>💾 دیسکِ سرور: {pct.toLocaleString('fa-IR')}%</b>
        <span>آزاد {mb(st.free)} از {mb(st.total)}</span>
        {st.db_reclaimable > 32 * 1048576 && <span className="text-gray-600 dark:text-gray-300">· فضای خالیِ داخلِ پایگاه‌داده {mb(st.db_reclaimable)}</span>}
        {link && <a href="/oversight#disk" className="text-blue-600 underline mr-auto">ریزِ مصرف و پاک‌سازی ←</a>}
      </div>
      <div className="mt-1 h-2 w-full rounded bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div className={`h-2 ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      {st.level !== 'ok' && (
        <div className="mt-1 font-semibold text-red-700 dark:text-red-300">
          ⚠️ {st.alert || `دیسک از ${Number(st.alert_percent).toLocaleString('fa-IR')}٪ گذشته`}
        </div>
      )}
      {Array.isArray(st.top) && st.top.length > 0 && (
        <div className="mt-1 text-gray-700 dark:text-gray-300">
          بزرگ‌ترین‌ها: {st.top.slice(0, 5).map((t: any) => `${t.label} ${mb(t.bytes)}`).join(' · ')}
        </div>
      )}
    </div>
  );
}
