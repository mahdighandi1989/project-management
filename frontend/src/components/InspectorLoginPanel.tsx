'use client';

/**
 * PM-INS-0031 — «🔐 ورودِ یک‌باره». The preview iframe is sandboxed (no cookies/storage, Google sign-in refuses the
 * proxy domain), so the owner signs in ONCE inside a live browser on the server, on the project's real site. Frames
 * are shown here; clicks and typing are forwarded. «ذخیره» keeps the session encrypted on the server (per site) and
 * 📸 عکس / 🖱 عامل / the snapshot then open the site already signed in. Typed text never leaves the request.
 * Backend: backend/app/services/manual_login.py, /api/inspector-agent/login/*.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BASE = `${API_BASE}/api/inspector-agent`;

interface Saved { host: string; saved_at: string; expires_at: string; cookies: number; origins: number; final_url: string; title: string; expired?: boolean }
interface Frame { ok: boolean; image?: string; url?: string; title?: string; tabs?: number; viewport?: { width: number; height: number }; error?: string }

const KEYS: [string, string][] = [['Enter', '⏎ Enter'], ['Tab', '⇥ Tab'], ['Backspace', '⌫ پاک'], ['Escape', 'Esc']];

export default function InspectorLoginPanel({ projectId, onStatus }: { projectId: string; onStatus?: (msg: string) => void }) {
  const [saved, setSaved] = useState<Saved | null>(null);
  const [site, setSite] = useState('');
  const [sid, setSid] = useState<string | null>(null);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [text, setText] = useState('');
  const imgRef = useRef<HTMLImageElement>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadStatus = useCallback(async () => {
    if (!projectId) return;
    try {
      const r = await fetch(`${BASE}/login/status?project_id=${encodeURIComponent(projectId)}`);
      const d = await r.json();
      setSite(d.url || '');
      setSaved(d.saved || null);
    } catch { /* offline — keep last */ }
  }, [projectId]);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const poll = useCallback(async (id: string) => {
    try {
      const r = await fetch(`${BASE}/login/${id}/frame`);
      if (r.status === 404) { setSid(null); setErr('پنجرهٔ ورود بسته شد (بی‌کاری) — دوباره بزنید'); return; }
      const d: Frame = await r.json();
      if (d.ok) setFrame(d); else setErr(d.error || 'تصویر نیامد');
    } catch { /* transient */ }
    pollRef.current = setTimeout(() => poll(id), 900);
  }, []);

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current); }, []);

  const start = async () => {
    setBusy(true); setErr(''); setFrame(null);
    try {
      const r = await fetch(`${BASE}/login/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: projectId }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      setSid(d.session_id); setSite(d.url);
      poll(d.session_id);
    } catch (e: any) { setErr(e?.message || String(e)); } finally { setBusy(false); }
  };

  const act = async (body: Record<string, any>) => {
    if (!sid) return;
    try {
      const r = await fetch(`${BASE}/login/${sid}/act`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const d = await r.json();
      setErr(d.ok ? '' : (d.error || d.detail || 'انجام نشد'));
    } catch (e: any) { setErr(e?.message || String(e)); }
  };

  const stopPolling = () => { if (pollRef.current) clearTimeout(pollRef.current); pollRef.current = null; };

  const save = async () => {
    if (!sid) return;
    setBusy(true);
    try {
      const r = await fetch(`${BASE}/login/${sid}/save`, { method: 'POST' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      stopPolling(); setSid(null); setFrame(null); setSaved(d.saved);
      onStatus?.(`🔐 ورودِ «${d.saved?.host}» ذخیره شد (رمزنگاری‌شده روی سرور، ${d.saved?.cookies} کوکی، ${d.saved?.origins} origin). از این به بعد 📸 عکس و 🖱 عامل با همین حساب وارد می‌شوند. صفحهٔ آخر: ${d.saved?.title || d.saved?.final_url || '—'}`);
    } catch (e: any) { setErr(e?.message || String(e)); } finally { setBusy(false); }
  };

  const cancel = async () => {
    stopPolling();
    if (sid) { try { await fetch(`${BASE}/login/${sid}/cancel`, { method: 'POST' }); } catch { /* ignore */ } }
    setSid(null); setFrame(null);
  };

  const forget = async () => {
    if (!window.confirm('ورودِ ذخیره‌شدهٔ این سایت پاک شود؟')) return;
    await fetch(`${BASE}/login/forget`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: projectId }) });
    loadStatus();
  };

  const onImgClick = (e: React.MouseEvent<HTMLImageElement>) => {
    const img = imgRef.current; const vp = frame?.viewport;
    if (!img || !vp) return;
    const rc = img.getBoundingClientRect();
    act({ kind: 'click', x: ((e.clientX - rc.left) / rc.width) * vp.width, y: ((e.clientY - rc.top) / rc.height) * vp.height });
  };

  const okSaved = saved && !saved.expired;
  return (
    <>
      <div className="flex flex-col items-center">
        <button
          onClick={start}
          disabled={busy || !projectId}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all disabled:opacity-50 ${okSaved ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-amber-600 hover:bg-amber-700'}`}
          title="یک مرورگرِ زنده روی سرور، روی سایتِ واقعیِ پروژه، باز می‌شود؛ خودتان وارد شوید و «ذخیره» بزنید"
        >
          {busy && !sid ? '⏳ باز کردن…' : okSaved ? '🔐 ورود ذخیره است — دوباره' : '🔐 ورودِ یک‌باره'}
        </button>
        <span className="text-[10px] text-gray-500 mt-1 text-center max-w-[170px] leading-4">
          {okSaved
            ? `واردشده تا ${new Date(saved!.expires_at).toLocaleDateString('fa-IR')} — 📸 و عامل با حسابِ شما کار می‌کنند`
            : saved?.expired ? 'ورودِ قبلی منقضی شد — دوباره وارد شوید'
            : 'یک بار با حسابِ خودتان وارد شوید تا 📸 و عامل صفحه‌های داخلی را ببینند'}
        </span>
        {saved && <button onClick={forget} className="text-[10px] text-red-500 hover:underline mt-0.5">🗑 فراموش کن</button>}
        {err && !sid && <span className="text-[10px] text-red-500 mt-0.5 max-w-[170px] text-center">{err}</span>}
      </div>

      {sid && (
        <div className="fixed inset-0 z-[80] bg-black/85 flex flex-col p-2 sm:p-4" dir="rtl">
          <div className="flex flex-wrap items-center gap-2 text-white text-xs mb-2">
            <b className="text-sm">🔐 ورودِ یک‌باره</b>
            <span className="text-gray-300">روی تصویر کلیک کنید مثلِ صفحهٔ واقعی؛ برای تایپ، متن را در کادرِ پایین بنویسید و «بفرست». وقتی وارد شدید «✅ وارد شدم — ذخیره».</span>
          </div>
          <div className="text-[11px] text-gray-300 mb-1 truncate" dir="ltr">{frame?.url || site} {frame?.tabs && frame.tabs > 1 ? ` · ${frame.tabs} tabs (showing newest — e.g. Google sign-in popup)` : ''}</div>
          <div className="flex-1 min-h-0 flex items-center justify-center bg-gray-900 rounded-lg overflow-auto">
            {frame?.image
              ? <img ref={imgRef} src={`data:image/jpeg;base64,${frame.image}`} alt="مرورگرِ زندهٔ سرور" onClick={onImgClick}
                  onWheel={(e) => act({ kind: 'scroll', dy: e.deltaY })}
                  className="max-w-full max-h-full object-contain cursor-pointer select-none" draggable={false} />
              : <span className="text-gray-400 text-sm">⏳ در حالِ باز کردنِ سایت روی سرور…</span>}
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <input
              value={text} onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && text) { act({ kind: 'type', text }); setText(''); } }}
              type="text" autoComplete="off" placeholder="متنی که باید در فیلدِ انتخاب‌شده تایپ شود (ایمیل، رمز…)"
              className="flex-1 min-w-[200px] px-2 py-1.5 rounded bg-gray-800 text-white text-sm border border-gray-600" dir="auto"
            />
            <button onClick={() => { if (text) { act({ kind: 'type', text }); setText(''); } }} className="px-3 py-1.5 rounded bg-blue-600 text-white text-xs">⌨️ بفرست</button>
            {KEYS.map(([k, l]) => <button key={k} onClick={() => act({ kind: 'key', key: k })} className="px-2 py-1.5 rounded bg-gray-700 text-white text-xs">{l}</button>)}
            <button onClick={() => act({ kind: 'scroll', dy: -500 })} className="px-2 py-1.5 rounded bg-gray-700 text-white text-xs">⬆</button>
            <button onClick={() => act({ kind: 'scroll', dy: 500 })} className="px-2 py-1.5 rounded bg-gray-700 text-white text-xs">⬇</button>
            <button onClick={() => act({ kind: 'back' })} className="px-2 py-1.5 rounded bg-gray-700 text-white text-xs">↩ برگشت</button>
            <button onClick={save} disabled={busy} className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold disabled:opacity-50">✅ وارد شدم — ذخیره</button>
            <button onClick={cancel} className="px-3 py-1.5 rounded bg-gray-600 text-white text-xs">انصراف</button>
          </div>
          {err && <div className="text-red-400 text-xs mt-1">{err}</div>}
          <div className="text-[10px] text-gray-400 mt-1">رمز فقط به همان صفحه تایپ می‌شود و جایی ثبت نمی‌شود؛ آنچه ذخیره می‌شود نشستِ واردشده (کوکی/حافظهٔ سایت) است، رمزنگاری‌شده روی سرور، تا ۱۴ روز.</div>
        </div>
      )}
    </>
  );
}
