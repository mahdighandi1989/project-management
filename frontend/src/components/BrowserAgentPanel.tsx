'use client';

/**
 * «عاملِ مرورگر» — the inspector takes the mouse (owner, 2026-11-15, plan item 12; backend: services/browser_agent.py).
 *
 * A server-side Chromium does the task step by step; every step (what the model saw and thought, the action, the
 * result, a screenshot) is shown live here and kept as a run log. Clicks that may submit/pay/delete and typing into
 * password fields wait for «اجازه»; other sites than the allowed ones are blocked on the server.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { withToken } from '@/lib/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BASE = `${API_BASE}/api/inspector-agent`;

interface ModelInfo { id: string; name: string; vision: boolean }
interface Step { n: number; url: string; title: string; elements: number; thought: string; action: Record<string, any>; result: string; ok: boolean; shot?: string | null }
interface Run {
  id: string; task: string; start_url: string; status: string; summary: string; model_id: string;
  allowed_hosts: string[]; steps: Step[]; pending?: { kind: 'confirm' | 'answer'; text: string } | null;
}

const LIVE = new Set(['starting', 'running', 'waiting_confirm', 'waiting_answer']);
const STATUS_FA: Record<string, string> = {
  starting: 'در حالِ شروع', running: 'در حالِ کار', waiting_confirm: 'منتظرِ اجازهٔ شما', waiting_answer: 'منتظرِ پاسخِ شما',
  done: 'انجام شد', failed: 'ناموفق', stopped: 'متوقف شد', stuck: 'گیر کرد',
};

function actionText(a: Record<string, any>): string {
  switch (a.type) {
    case 'click': return `کلیک روی [${a.id}]`;
    case 'type': return `تایپ در [${a.id}]${a.secret_ref ? ` (${a.secret_ref})` : ''}${a.submit ? ' + Enter' : ''}`;
    case 'select': return `انتخابِ «${a.option}» در [${a.id}]`;
    case 'check': return `${a.on ? 'تیک' : 'برداشتنِ تیکِ'} [${a.id}]`;
    case 'goto': return `رفتن به ${a.url}`;
    case 'scroll': return `اسکرول ${a.dir === 'up' ? 'بالا' : 'پایین'}`;
    case 'press': return `کلیدِ ${a.key}`;
    case 'wait': return `صبر ${a.ms}ms`;
    case 'back': return 'برگشت';
    case 'ask_user': return `پرسش: ${a.summary}`;
    case 'done': return `پایان: ${a.summary}`;
    default: return a.type || '';
  }
}

function toMarkdown(run: Run): string {
  const lines = [`# اجرای عاملِ مرورگر ${run.id}`, '', `- کار: ${run.task}`, `- شروع: ${run.start_url}`, `- مدل: ${run.model_id}`,
    `- وضعیت: ${STATUS_FA[run.status] || run.status}`, `- نتیجه: ${run.summary}`, '', '## گام‌ها', ''];
  run.steps.forEach((s) => lines.push(`${s.n}. ${s.ok ? '✅' : '❌'} ${actionText(s.action)} — ${s.result}${s.thought ? `  \n   _${s.thought}_` : ''}  \n   ${s.url}`));
  return lines.join('\n');
}

export default function BrowserAgentPanel({ projectId, defaultUrl, onSendToChat }: {
  projectId?: string; defaultUrl?: string | null; onSendToChat?: (text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [task, setTask] = useState('');
  const [url, setUrl] = useState(defaultUrl || '');
  const [hosts, setHosts] = useState('');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelId, setModelId] = useState('');
  const [maxSteps, setMaxSteps] = useState(25);
  const [useLogin, setUseLogin] = useState(true);
  const [run, setRun] = useState<Run | null>(null);
  const [answer, setAnswer] = useState('');
  const [err, setErr] = useState('');
  const [selected, setSelected] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { if (defaultUrl && !url) setUrl(defaultUrl); }, [defaultUrl, url]);
  useEffect(() => {
    if (!open || models.length) return;
    fetch(`${BASE}/models`).then((r) => (r.ok ? r.json() : [])).then((m: ModelInfo[]) => {
      setModels(m || []);
      if (m?.length) setModelId((x) => x || m[0].id);
    }).catch(() => setModels([]));
  }, [open, models.length]);

  const poll = useCallback((id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${BASE}/runs/${id}`);
        if (!r.ok) return;
        const d: Run = await r.json();
        setRun(d);
        if (!LIVE.has(d.status) && pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      } catch { /* keep polling */ }
    }, 1200);
  }, []);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const start = async () => {
    setErr('');
    try {
      const r = await fetch(`${BASE}/runs`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify((() => {
          // (2026-11-15, PM-INS-0012) the agent on THIS app: sign in with the current session (no Auth Recipe needed)
          // and let it reach this app's API host, or every data call is blocked and the page looks logged out
          let _same = false;
          let _apiHost = '';
          try { _same = new URL(url).host === window.location.host; _apiHost = new URL(API_BASE).host; } catch { /* bad url */ }
          const _hosts = hosts.split(/[\s,،]+/).filter(Boolean);
          if (_same && _apiHost && !_hosts.includes(_apiHost)) _hosts.push(_apiHost);
          return { task, start_url: url, allowed_hosts: _hosts, model_id: modelId || null, project_id: projectId,
                   max_steps: maxSteps, use_login: useLogin, use_session: useLogin && _same };
        })()),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d?.detail || `HTTP ${r.status}`);
      setRun({ id: d.run_id, task, start_url: url, status: 'starting', summary: d.login || '', model_id: d.model_id, allowed_hosts: d.allowed_hosts, steps: [] });
      setSelected(null);
      poll(d.run_id);
    } catch (e: any) { setErr(e?.message || String(e)); }
  };

  const send = async (path: string, body?: any) => {
    if (!run) return;
    await fetch(`${BASE}/runs/${run.id}/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }).catch(() => {});
  };

  const download = () => {
    if (!run) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([toMarkdown(run)], { type: 'text/markdown;charset=utf-8' }));
    a.download = `browser-agent-${run.id}.md`; a.click();
  };

  const shown = run?.steps.find((s) => s.n === selected) || run?.steps[run.steps.length - 1];
  const shotUrl = (s?: Step) => (run && s?.shot ? withToken(`${BASE}/runs/${run.id}/shots/${s.shot}`) : '');
  const live = run && LIVE.has(run.status);
  const selModel = models.find((m) => m.id === modelId);

  return (
    <>
      <button onClick={() => setOpen(true)} title="عاملِ مرورگر — کار روی سایت مثلِ کاربر (کلیک، فرم، ناوبری)"
        className="px-2 py-1 bg-teal-600/90 hover:bg-teal-700 text-white text-[10px] rounded-md shadow-lg flex items-center gap-1">
        🖱 عامل
      </button>
      {open && (
        <div className="fixed inset-0 z-[9998] bg-black/50 flex items-center justify-center p-3" dir="rtl" onClick={() => !live && setOpen(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[92vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b dark:border-gray-700">
              <div>
                <h2 className="font-bold dark:text-white">🖱 عاملِ مرورگر — کار روی سایت مثلِ کاربر</h2>
                <p className="text-xs text-gray-500">هر گام ثبت می‌شود (دید، فکر، کار، نتیجه، عکس). ثبت/ارسال/حذف/پرداخت و رمز منتظرِ اجازهٔ شماست؛ سایت‌های غیرمجاز روی سرور مسدودند.</p>
              </div>
              <button onClick={() => setOpen(false)} className="text-xl px-2 dark:text-white">✕</button>
            </div>

            {!run || !live ? (
              <div className="p-5 grid md:grid-cols-2 gap-3 border-b dark:border-gray-700">
                <label className="md:col-span-2 text-sm dark:text-gray-200">چه کاری انجام شود؟
                  <textarea value={task} onChange={(e) => setTask(e.target.value)} rows={3}
                    placeholder="مثلاً: وارد صفحهٔ ثبت‌نام شو، فرم را با ایمیلِ test@example.com پر کن و پیامِ نتیجه را بگو"
                    className="mt-1 w-full rounded-lg border px-3 py-2 dark:bg-gray-800 dark:border-gray-700" />
                </label>
                <label className="text-sm dark:text-gray-200">نشانیِ شروع
                  <input value={url} onChange={(e) => setUrl(e.target.value)} dir="ltr" className="mt-1 w-full rounded-lg border px-3 py-2 dark:bg-gray-800 dark:border-gray-700" />
                </label>
                <label className="text-sm dark:text-gray-200">سایت‌های مجازِ دیگر (اختیاری، با فاصله)
                  <input value={hosts} onChange={(e) => setHosts(e.target.value)} dir="ltr" placeholder="api.example.com"
                    className="mt-1 w-full rounded-lg border px-3 py-2 dark:bg-gray-800 dark:border-gray-700" />
                </label>
                <label className="text-sm dark:text-gray-200">مدل
                  <select value={modelId} onChange={(e) => setModelId(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2 dark:bg-gray-800 dark:border-gray-700">
                    {models.length === 0 && <option value="">مدلی فعال نیست</option>}
                    {models.map((m) => <option key={m.id} value={m.id}>{m.name} {m.vision ? '👁 تصویری' : '📝 متنی'}</option>)}
                  </select>
                  <span className="text-[11px] text-gray-500">{selModel?.vision ? 'این مدل عکسِ هر گام را هم می‌بیند' : 'مدل‌های متنی فهرستِ شماره‌دارِ عناصرِ صفحه را می‌بینند — برای مدل‌های ضعیف هم کار می‌کند'}</span>
                </label>
                <label className="text-sm dark:text-gray-200">حداکثرِ گام
                  <input type="number" min={1} max={40} value={maxSteps} onChange={(e) => setMaxSteps(Math.max(1, Math.min(40, +e.target.value || 25)))}
                    className="mt-1 w-full rounded-lg border px-3 py-2 dark:bg-gray-800 dark:border-gray-700" />
                </label>
                <label className="md:col-span-2 text-xs flex items-center gap-2 dark:text-gray-300">
                  <input type="checkbox" checked={useLogin} onChange={(e) => setUseLogin(e.target.checked)} />
                  اول با «Auth Recipe» ِ همان پروژه (کارتِ اتاق فرمان) وارد شو — رمزها فقط از متغیرهای سرور، مدل هرگز نمی‌بیندشان
                </label>
                <div className="md:col-span-2 flex items-center gap-3">
                  <button onClick={start} disabled={task.trim().length < 3 || !/^https?:\/\//.test(url)}
                    className="px-5 py-2 rounded-lg bg-teal-600 text-white disabled:opacity-50">▶️ شروع</button>
                  {err && <span className="text-sm text-red-600">{err}</span>}
                </div>
              </div>
            ) : null}

            {run && (
              <div className="flex-1 min-h-0 grid md:grid-cols-5 gap-0">
                <div className="md:col-span-3 p-4 border-l dark:border-gray-700 flex flex-col min-h-0">
                  <div className="flex items-center gap-2 mb-2 text-sm flex-wrap">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${live ? 'bg-blue-100 text-blue-700' : run.status === 'done' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                      {live && '⏳ '}{STATUS_FA[run.status] || run.status}
                    </span>
                    <span className="text-xs text-gray-500 truncate flex-1" dir="ltr">{shown?.url || run.start_url}</span>
                    {live && <button onClick={() => send('cancel')} className="px-3 py-1 rounded bg-red-600 text-white text-xs">⏹ توقف</button>}
                  </div>
                  <div className="flex-1 min-h-[240px] bg-gray-100 dark:bg-gray-800 rounded-lg overflow-auto flex items-start justify-center">
                    {shotUrl(shown)
                      // eslint-disable-next-line @next/next/no-img-element
                      ? <img src={shotUrl(shown)} alt={`گام ${shown?.n}`} className="max-w-full" />
                      : <p className="text-gray-400 text-sm p-6">{live ? 'در حالِ باز کردنِ صفحه…' : 'عکسی نیست'}</p>}
                  </div>
                  {run.pending && (
                    <div className="mt-3 rounded-lg border-2 border-amber-400 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm">
                      {run.pending.kind === 'confirm' ? (
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="flex-1">⚠️ {run.pending.text} — اجازه می‌دهید؟</span>
                          <button onClick={() => send('reply', { approve: true })} className="px-3 py-1 rounded bg-green-600 text-white">اجازه</button>
                          <button onClick={() => send('reply', { approve: false })} className="px-3 py-1 rounded bg-gray-500 text-white">رد</button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span>❓ {run.pending.text}</span>
                          <input value={answer} onChange={(e) => setAnswer(e.target.value)} className="flex-1 rounded border px-2 py-1 dark:bg-gray-800" />
                          <button onClick={() => { send('reply', { text: answer }); setAnswer(''); }} className="px-3 py-1 rounded bg-blue-600 text-white">ارسال</button>
                        </div>
                      )}
                    </div>
                  )}
                  {!live && (
                    <div className="mt-3 text-sm">
                      <div className="font-bold dark:text-white">نتیجه: <span className="font-normal">{run.summary || '—'}</span></div>
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {onSendToChat && <button onClick={() => { onSendToChat(toMarkdown(run)); setOpen(false); }} className="px-3 py-1 rounded bg-blue-600 text-white text-xs">💬 گزارش به چتِ بازرس</button>}
                        <button onClick={download} className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 dark:text-white text-xs">⬇️ گزارش (.md)</button>
                        <button onClick={() => setRun(null)} className="px-3 py-1 rounded bg-teal-600 text-white text-xs">کارِ تازه</button>
                      </div>
                    </div>
                  )}
                </div>
                <div className="md:col-span-2 p-4 overflow-auto max-h-[60vh] md:max-h-none">
                  <div className="text-xs text-gray-500 mb-2 truncate">کار: {run.task}</div>
                  <ol className="space-y-2">
                    {run.steps.map((s) => (
                      <li key={s.n}>
                        <button onClick={() => setSelected(s.n)}
                          className={`w-full text-right rounded-lg p-2 text-xs border ${selected === s.n ? 'border-teal-500' : 'border-transparent'} ${s.ok ? 'bg-gray-50 dark:bg-gray-800' : 'bg-red-50 dark:bg-red-900/20'}`}>
                          <div className="font-bold dark:text-white">{s.n}. {s.ok ? '✅' : '❌'} {actionText(s.action)}</div>
                          {s.thought && <div className="text-gray-500 mt-0.5">💭 {s.thought}</div>}
                          <div className="text-gray-600 dark:text-gray-300 mt-0.5">{s.result}</div>
                        </button>
                      </li>
                    ))}
                    {live && <li className="text-xs text-gray-400">⏳ …</li>}
                  </ol>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
