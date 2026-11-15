'use client';

/**
 * «دستیار» — the roaming chat on every page (owner, 2026-11-15, plan item 2; it took
 * the «مناظره» slot in the menu). It sends, with each question, the live site map
 * (lib/siteMap.ts) and the help text of the current page; the backend adds the newest
 * WORKLOG entries, the newest GitHub commits and live counts (services/assistant.py),
 * so it is current after every change without anyone updating it.
 *
 * «چند مدل» asks up to four models at once and shows each answer — the debate idea,
 * kept inside the chat. Conversations are saved and listed in «آرشیو».
 */

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { siteMapForAssistant } from '@/lib/siteMap';
import { getPageHelp } from '@/components/help/helpData';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const STORE = 'assistant.chat.v1';

interface ModelInfo { id: string; name: string; provider: string }
interface Msg { role: 'user' | 'assistant'; content: string; model_id?: string; error?: boolean }

function loadState(): { messages: Msg[]; conversationId: string | null } {
  try {
    const raw = localStorage.getItem(STORE);
    if (raw) return JSON.parse(raw);
  } catch { /* private window */ }
  return { messages: [], conversationId: null };
}

export default function AssistantChat({ pathname, pageLabel }: { pathname: string; pageLabel: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelId, setModelId] = useState('');
  const [multi, setMulti] = useState(false);
  const [multiIds, setMultiIds] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const s = loadState();
    setMessages(s.messages || []);
    setConversationId(s.conversationId || null);
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORE, JSON.stringify({ messages: messages.slice(-40), conversationId })); } catch { /* ignore */ }
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, conversationId]);

  // «ادامه در دستیار» from «آرشیو» — load a saved conversation into the chat and open it
  useEffect(() => {
    const onLoad = async (e: Event) => {
      const id = (e as CustomEvent).detail?.id;
      if (!id) return;
      try {
        const res = await fetch(`${API_BASE}/api/assistant/conversations/${id}`);
        if (!res.ok) return;
        const c = await res.json();
        setMessages((c.messages || []).map((m: any) => ({
          role: m.role === 'user' ? 'user' : 'assistant', content: m.content || m.error || '', model_id: m.model_id, error: !!m.error,
        })));
        setConversationId(c.id);
        setOpen(true);
      } catch { /* network */ }
    };
    window.addEventListener('assistant:load', onLoad);
    return () => window.removeEventListener('assistant:load', onLoad);
  }, []);

  useEffect(() => {
    if (!open || models.length) return;
    fetch(`${API_BASE}/api/assistant/models`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: ModelInfo[]) => {
        setModels(Array.isArray(list) ? list : []);
        if (list?.length) { setModelId((m) => m || list[0].id); setMultiIds(list.slice(0, 2).map((m) => m.id)); }
      })
      .catch(() => setModels([]));
  }, [open, models.length]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const history = messages.filter((m) => !m.error).map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setInput('');
    setBusy(true);
    const help = getPageHelp(pathname);
    try {
      const res = await fetch(`${API_BASE}/api/assistant/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history,
          conversation_id: conversationId,
          model_ids: multi ? multiIds : (modelId ? [modelId] : null),
          page: { path: pathname, label: pageLabel, help: help ? `${help.title}: ${help.overview}\nقابلیت‌ها: ${help.features.join('؛ ')}` : '' },
          site_map: siteMapForAssistant(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setConversationId(data.conversation_id);
      setSources(data.sources || []);
      const answers: Msg[] = (data.answers || []).map((a: any) => ({
        role: 'assistant', model_id: a.model_id,
        content: a.error ? `⚠️ ${a.error}` : a.content, error: !!a.error,
      }));
      setMessages((m) => [...m, ...answers]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: 'assistant', content: `⚠️ ${e?.message || e}`, error: true }]);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => { setMessages([]); setConversationId(null); setSources([]); };

  // bottom-left, stacked above the help circle (the right edge is the side menu in RTL)
  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        title="دستیار — هر پرسشی دربارهٔ برنامه و پروژه‌ها"
        data-report-section="assistant" data-report-section-label="دستیار سیار"
        className={`fixed bottom-24 left-6 z-[60] w-14 h-14 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg hover:scale-105 transition flex items-center justify-center text-2xl`}
      >
        {open ? '✕' : '💬'}
      </button>

      {open && (
        <div dir="rtl" className={`fixed bottom-40 left-4 right-4 sm:right-auto sm:w-[26rem] z-[60] h-[min(70vh,36rem)] flex flex-col rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-2xl`}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <span className="font-bold dark:text-white">💬 دستیار</span>
            <span className="text-xs text-gray-400 truncate flex-1">در «{pageLabel}»</span>
            <Link href="/archive?tab=assistant" className="text-xs text-blue-600 hover:underline" onClick={() => setOpen(false)}>گفت‌وگوها</Link>
            <button onClick={reset} className="text-xs text-gray-500 hover:text-red-600" title="گفت‌وگوی تازه">تازه</button>
          </div>

          <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700 text-xs flex flex-wrap items-center gap-2">
            {!multi ? (
              <select value={modelId} onChange={(e) => setModelId(e.target.value)} className="flex-1 min-w-0 rounded border px-2 py-1 dark:bg-gray-700 dark:text-white dark:border-gray-600">
                {models.length === 0 && <option value="">مدلی فعال نیست</option>}
                {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            ) : (
              <div className="flex-1 flex flex-wrap gap-1 max-h-16 overflow-auto">
                {models.map((m) => (
                  <label key={m.id} className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 dark:text-gray-200">
                    <input type="checkbox" checked={multiIds.includes(m.id)}
                      onChange={(e) => setMultiIds((ids) => e.target.checked ? [...ids, m.id].slice(0, 4) : ids.filter((x) => x !== m.id))} />
                    {m.name}
                  </label>
                ))}
              </div>
            )}
            <label className="flex items-center gap-1 dark:text-gray-300" title="یک پرسش، پاسخِ چند مدل کنارِ هم (جایگزینِ مناظره)">
              <input type="checkbox" checked={multi} onChange={(e) => setMulti(e.target.checked)} /> چند مدل
            </label>
          </div>

          <div className="flex-1 overflow-auto px-4 py-3 space-y-3 text-sm">
            {messages.length === 0 && (
              <div className="text-gray-500 dark:text-gray-400 space-y-2">
                <p>سلام! هر چیزی دربارهٔ برنامه، پروژه‌ها یا همین صفحه بپرس. من هر بار دفترِ کار، آخرین کامیت‌ها و وضعیتِ زندهٔ پروژه‌ها را می‌خوانم.</p>
                {['این صفحه چه کار می‌کند؟', 'آخرین تغییراتِ پروژه چه بوده؟', 'برای گزارشِ یک ایراد کجا بروم؟'].map((q) => (
                  <button key={q} onClick={() => setInput(q)} className="block text-right text-blue-600 hover:underline">• {q}</button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-start' : 'flex justify-end'}>
                <div className={`max-w-[90%] rounded-xl px-3 py-2 ${m.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : m.error ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300' : 'bg-gray-100 dark:bg-gray-700 dark:text-gray-100'}`}>
                  {m.model_id && <div className="text-[10px] opacity-60 mb-1" dir="ltr">{m.model_id}</div>}
                  {m.role === 'assistant' ? (
                    <div className="leading-relaxed [&_a]:text-blue-600 [&_a]:underline [&_ul]:list-disc [&_ul]:pr-5 [&_ol]:list-decimal [&_ol]:pr-5 [&_p]:my-1 [&_code]:text-xs [&_pre]:overflow-auto [&_h1]:font-bold [&_h2]:font-bold [&_h3]:font-bold">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}
                        components={{ a: ({ href, children }) => href?.startsWith('/')
                          ? <Link href={href} onClick={() => setOpen(false)}>{children}</Link>
                          : <a href={href} target="_blank" rel="noreferrer">{children}</a> }}>
                        {m.content}
                      </ReactMarkdown>
                    </div>
                  ) : <div className="whitespace-pre-wrap">{m.content}</div>}
                </div>
              </div>
            ))}
            {busy && <div className="text-xs text-gray-400">⏳ در حالِ خواندنِ بافتِ زنده و پاسخ…</div>}
            <div ref={endRef} />
          </div>

          {sources.length > 0 && (
            <div className="px-4 py-1 text-[10px] text-gray-400 border-t border-gray-100 dark:border-gray-700 truncate" title={sources.join(' · ')}>
              منابع: {sources.join(' · ')}
            </div>
          )}
          <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              rows={2}
              placeholder="پرسش… (Enter ارسال، Shift+Enter خطِ تازه)"
              className="flex-1 resize-none rounded-lg border px-3 py-2 text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
            />
            <button onClick={send} disabled={busy || !input.trim()} className="px-4 rounded-lg bg-emerald-600 text-white disabled:opacity-50">ارسال</button>
          </div>
        </div>
      )}
    </>
  );
}
