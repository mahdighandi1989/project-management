'use client';

/**
 * «نمای سرور» — the self-healing fallback of the «بازرس ویژه» screen (owner plan item 12, 2026-11-15).
 *
 * When the proxied iframe cannot show the project's site (framing refused, dynamic chunks, a POST-only page, an
 * error), this shows a live picture of the same URL taken by the server's Chromium every few seconds
 * (`GET /api/inspector-agent/snapshot`). Every minute it lets the parent retry the iframe; as soon as the iframe
 * loads again the parent switches back by itself.
 */

import { useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ServerScreen({ url, onRetryIframe, everyMs = 4000 }: { url: string; onRetryIframe: () => void; everyMs?: number }) {
  const [src, setSrc] = useState('');
  const [err, setErr] = useState('');
  const [at, setAt] = useState<Date | null>(null);
  const prev = useRef('');

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/inspector-agent/snapshot?url=${encodeURIComponent(url)}`);
        if (r.status === 409) return;  // server browser busy — next tick
        if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `HTTP ${r.status}`);
        const u = URL.createObjectURL(await r.blob());
        if (stop) { URL.revokeObjectURL(u); return; }
        if (prev.current) URL.revokeObjectURL(prev.current);
        prev.current = u;
        setSrc(u); setErr(''); setAt(new Date());
      } catch (e: any) {
        if (!stop) setErr(e?.message || String(e));
      }
    };
    tick();
    const iv = setInterval(tick, everyMs);
    const retry = setInterval(onRetryIframe, 60_000);  // self-healing: try the live iframe again every minute
    return () => { stop = true; clearInterval(iv); clearInterval(retry); if (prev.current) URL.revokeObjectURL(prev.current); };
  }, [url, everyMs, onRetryIframe]);

  return (
    <div className="absolute inset-0 z-40 bg-gray-900 flex flex-col" dir="rtl">
      <div className="flex items-center gap-2 px-2 py-1 text-[10px] text-amber-200 bg-amber-900/60">
        <span>🛰 نمای سرور — iframe بار نشد؛ تصویرِ زندهٔ همین صفحه از مرورگرِ سرور (هر {Math.round(everyMs / 1000)} ثانیه)</span>
        <span className="flex-1" />
        {at && <span>{at.toLocaleTimeString('fa-IR')}</span>}
        <button onClick={onRetryIframe} className="px-2 py-0.5 rounded bg-blue-600 text-white">تلاشِ دوباره با iframe</button>
      </div>
      <div className="flex-1 overflow-auto flex items-start justify-center">
        {src
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={src} alt="نمای سرور" className="max-w-full" />
          : <p className="text-gray-400 text-xs p-6">{err ? `خطا: ${err}` : 'در حالِ گرفتنِ تصویر از سرور…'}</p>}
      </div>
      {err && src && <div className="px-2 py-1 text-[10px] text-red-300 bg-red-900/40">آخرین تلاش ناموفق: {err}</div>}
    </div>
  );
}
