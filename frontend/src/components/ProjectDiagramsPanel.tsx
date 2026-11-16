'use client';

// (PM-INS-0004) نمودارهای هر پروژه ذیلِ صفحهٔ خودِ پروژه — نمودارهای ذخیره‌شده + «رسم خودکار».
// تبِ «📊 نمودارها» در /projects?view=diagrams بی‌تغییر می‌ماند؛ هر دو در یک مخزن (/api/diagrams/saved) می‌نویسند.

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AUTO_DIAGRAM_TYPES } from './views/DiagramsView';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type SavedDiagram = { id: string; title: string; diagram_type: string; mermaid: string; created_at: string };

function MermaidBox({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', fontFamily: 'inherit',
          flowchart: { useMaxWidth: true, htmlLabels: true } });
        const { svg } = await mermaid.render(`pd-${Math.random().toString(36).slice(2)}`, code);
        if (!cancelled && ref.current) { ref.current.innerHTML = svg; setErr(''); }
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || 'نمودار رندر نشد');
      }
    })();
    return () => { cancelled = true; };
  }, [code]);
  return (
    <div dir="ltr" className="overflow-auto max-h-[480px] bg-white dark:bg-gray-900 rounded border dark:border-gray-700 p-2">
      {err ? <pre className="text-xs text-red-600 whitespace-pre-wrap" dir="rtl">⚠️ {err}</pre> : <div ref={ref} />}
    </div>
  );
}

export default function ProjectDiagramsPanel({ source, id, projectName }: { source: 'local' | 'github'; id: string; projectName?: string }) {
  const [items, setItems] = useState<SavedDiagram[]>([]);
  const [loading, setLoading] = useState(true);
  const [type, setType] = useState('tree');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/diagrams/saved?source=${encodeURIComponent(source)}&id=${encodeURIComponent(id)}`);
      const data = res.ok ? await res.json() : { items: [] };
      const list: SavedDiagram[] = data.items || [];
      setItems(list);
      setOpenId((cur) => cur ?? list[0]?.id ?? null);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [source, id]);

  useEffect(() => { void load(); }, [load]);

  const autoDraw = async () => {
    setBusy(true);
    setMsg('');
    try {
      const res = await fetch(`${API_BASE}/api/diagrams/auto-from-project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, id, diagram_type: type, max_files: 80 }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.mermaid) {
        setMsg(`❌ ${data.detail || 'رسم خودکار ناموفق بود'}`);
        return;
      }
      const label = AUTO_DIAGRAM_TYPES.find((t) => t.id === type)?.label || type;
      const save = await fetch(`${API_BASE}/api/diagrams/saved`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, id, mermaid: data.mermaid, diagram_type: type, title: label }),
      });
      const saved = await save.json().catch(() => ({}));
      if (!save.ok) {
        setMsg(`⚠️ نمودار رسم شد ولی ذخیره نشد: ${saved.detail || save.status}`);
        return;
      }
      setMsg(saved.duplicate ? 'ℹ️ همین نمودار قبلاً ذخیره شده بود' : '✅ رسم و ذخیره شد');
      setOpenId(saved.item?.id || null);
      await load();
    } catch (e: any) {
      setMsg(`❌ ${e?.message || 'خطای شبکه'}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div dir="rtl" className="space-y-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h2 className="font-bold dark:text-white">📊 نمودارهای {projectName || 'این پروژه'}</h2>
          <Link href="/projects?view=diagrams" className="text-xs text-blue-600 hover:underline">
            ویرایشگرِ کاملِ نمودارها ←
          </Link>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          {AUTO_DIAGRAM_TYPES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setType(t.id)}
              title={t.desc}
              className={`px-3 py-1.5 rounded border text-sm transition ${
                type === t.id
                  ? 'bg-purple-500 text-white border-purple-500'
                  : 'bg-gray-50 dark:bg-gray-700 dark:text-gray-200 border-gray-200 dark:border-gray-600 hover:bg-gray-100'
              }`}
            >
              {t.label}
            </button>
          ))}
          <button
            onClick={autoDraw}
            disabled={busy}
            className="px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {busy ? '⏳ در حالِ رسم…' : '🪄 رسم خودکار'}
          </button>
        </div>
        {msg && <p className="text-sm mt-2 dark:text-gray-200">{msg}</p>}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
        <h3 className="font-semibold mb-3 dark:text-white">نمودارهای ذخیره‌شده ({items.length})</h3>
        {loading ? (
          <p className="text-sm text-gray-500">در حالِ بارگذاری…</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-gray-500">هنوز نموداری برای این پروژه ذخیره نشده — یک نوع را انتخاب و «🪄 رسم خودکار» را بزنید.</p>
        ) : (
          <div className="space-y-2">
            {items.map((d) => (
              <div key={d.id} className="border dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => setOpenId(openId === d.id ? null : d.id)}
                  className="w-full flex items-center justify-between p-3 text-right hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <span className="font-medium text-sm dark:text-white">{d.title}</span>
                  <span className="text-xs text-gray-500">
                    {d.created_at ? new Date(d.created_at).toLocaleString('fa-IR') : ''} {openId === d.id ? '▲' : '▼'}
                  </span>
                </button>
                {openId === d.id && (
                  <div className="p-3 pt-0">
                    <MermaidBox code={d.mermaid} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
