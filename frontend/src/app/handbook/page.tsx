'use client';

/**
 * «جزوه و دفتر کار» — owner, 2026-11-15 (plan item 11). Pattern: Detective-1's /handbook (read-only reference).
 *
 * Every document is read LIVE from GitHub `main` by the backend (`/api/handbook/*`, services/repo_docs.py), so this
 * page is always what GitHub has — a commit that adds or edits a Markdown file in docs/handbook, docs/supervisor or
 * experiences shows up here with no deploy. Two documents are generated live: CHANGELOG (every commit, from any
 * session/model/human) and ACTIVITY (what the app's own models did).
 *
 * Index: date-ordered documents (WORKLOG, PROGRESS, CHANGELOG, …) list newest first; content documents keep their
 * order. Heading anchors use GitHub's slug rule — the same one scripts/docs_gate.py checks the handbook's links with.
 * Export: this document (.md), all documents (.md), print / save as PDF.
 */

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DocMeta { slug: string; title: string; group: string; order: 'date' | 'content'; path: string | null; github_url: string | null }
interface Doc extends DocMeta { content: string; source: string }
interface Hit { slug: string; heading: string; line: string }

/** GitHub's heading anchor — keep letters, marks, numbers, _ - and space; spaces ⇒ '-'. Same as docs_gate.gh_slug. */
const SLUG_KEEP = new RegExp('[\\p{L}\\p{M}\\p{N}_\\- ]', 'u');  // constructor form: the build targets ES5

function ghSlug(text: string): string {
  return text.replace(/[*`]/g, '').trim().toLowerCase()
    .split('').filter((ch) => SLUG_KEEP.test(ch)).join('')
    .replace(/ /g, '-');
}

function allMatches(re: RegExp, text: string): RegExpExecArray[] {
  const out: RegExpExecArray[] = [];
  const g = new RegExp(re.source, re.flags.includes('g') ? re.flags : re.flags + 'g');
  let m: RegExpExecArray | null;
  while ((m = g.exec(text)) !== null) out.push(m);
  return out;
}

function textOf(node: any): string {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  return textOf(node.props?.children);
}

function extractToc(md: string): { depth: number; text: string; id: string }[] {
  const body = md.replace(/```[\s\S]*?```/g, '');
  const out: { depth: number; text: string; id: string }[] = [];
  allMatches(/^(#{1,4})\s+(.+?)\s*$/gm, body).forEach((m) => {
    const text = m[2].replace(/[*`]/g, '');
    out.push({ depth: m[1].length, text, id: ghSlug(m[2]) });
  });
  return out;
}

/** Repo-relative Markdown link ⇒ the reader's slug (null = leave it as an external/GitHub link). */
function slugForLink(href: string, current: DocMeta | undefined, docs: DocMeta[]): { slug: string; hash: string } | null {
  const m = /^([^#]*?)([A-Za-z0-9_\-]+)\.md(#.*)?$/.exec(href);
  if (!m || /^https?:/.test(href)) return null;
  const stem = m[2];
  const hash = m[3] || '';
  const dir = m[1];
  const candidates = [stem, `supervisor-${stem}`, `lesson-${stem}`];
  if (dir.includes('supervisor')) candidates.unshift(`supervisor-${stem}`);
  if (dir.includes('experiences')) candidates.unshift(`lesson-${stem}`);
  if (!dir && current?.slug.startsWith('supervisor-')) candidates.unshift(`supervisor-${stem}`);
  const hit = candidates.find((c) => docs.some((d) => d.slug === c));
  return hit ? { slug: hit, hash } : null;
}

function Mermaid({ chart }: { chart: string }) {
  const [svg, setSvg] = useState('');
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, theme: 'base' });
        const { svg } = await mermaid.render(`hb-${Math.random().toString(36).slice(2)}`, chart);
        if (alive) setSvg(svg);
      } catch {
        if (alive) setSvg('');
      }
    })();
    return () => { alive = false; };
  }, [chart]);
  return svg ? <div className="my-4 overflow-auto" dangerouslySetInnerHTML={{ __html: svg }} />
    : <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-3 rounded overflow-auto" dir="ltr">{chart}</pre>;
}

/** The progress chart — drawn from PROGRESS.md's own table, so it can never disagree with it. */
function ProgressChart({ md }: { md: string }) {
  const rows = allMatches(/^\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*([\d—-]+)\s*\|\s*([▲▼↩]+)\s*\|/gm, md)
    .map((m) => ({ n: +m[1], date: m[2], text: m[3], tests: /^\d+$/.test(m[4]) ? +m[4] : null, dir: m[5] }));
  if (rows.length < 2) return null;
  const W = 760, H = 220, P = 36;
  const tests = rows.map((r) => r.tests).filter((t): t is number => t != null);
  const tMin = tests.length ? Math.min(...tests) - 10 : 0, tMax = tests.length ? Math.max(...tests) + 10 : 1;
  const x = (i: number) => P + (i * (W - 2 * P)) / (rows.length - 1);
  const y = (t: number) => H - P - ((t - tMin) * (H - 2 * P)) / Math.max(tMax - tMin, 1);
  const pts = rows.map((r, i) => (r.tests != null ? `${x(i)},${y(r.tests)}` : null)).filter(Boolean).join(' ');
  const color = (d: string) => (d.includes('▼') ? '#dc2626' : d.includes('↩') ? '#d97706' : '#16a34a');
  return (
    <div className="my-4 rounded-xl border border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-900">
      <div className="text-sm font-bold mb-1 dark:text-white">نمودارِ روند — از جدولِ همین سند</div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ direction: 'ltr' }} role="img" aria-label="progress chart">
        <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="#9ca3af" />
        {tests.length > 0 && <>
          <text x={4} y={y(tMax - 10) + 4} fontSize="10" fill="#6b7280">{tMax - 10}</text>
          <text x={4} y={y(tMin + 10) + 4} fontSize="10" fill="#6b7280">{tMin + 10}</text>
          <polyline points={pts} fill="none" stroke="#3b82f6" strokeWidth="2" />
        </>}
        {rows.map((r, i) => (
          <g key={r.n}>
            <circle cx={x(i)} cy={r.tests != null ? y(r.tests) : H - P - 8} r="5" fill={color(r.dir)}>
              <title>{`#${r.n} ${r.date} ${r.dir} — ${r.text}${r.tests != null ? ` (تست‌ها: ${r.tests})` : ''}`}</title>
            </circle>
            <text x={x(i)} y={H - P + 14} fontSize="9" textAnchor="middle" fill="#6b7280">#{r.n}</text>
          </g>
        ))}
      </svg>
      <div className="text-xs text-gray-500 mt-1">خط: تعدادِ تست‌های سبز · نقطه: ▲ سبز پیشرفت، ▼ قرمز پسرفت، ↩ نارنجی بازگشت/اصلاح · روی نقطه بایستید تا رویداد را ببینید</div>
    </div>
  );
}

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url; a.download = name; a.click();
  URL.revokeObjectURL(url);
}

function HandbookInner() {
  const params = useSearchParams();
  const router = useRouter();
  const slug = params.get('doc') || 'HANDBOOK';
  const [docs, setDocs] = useState<DocMeta[]>([]);
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [newestFirst, setNewestFirst] = useState(true);
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Hit[] | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/handbook/docs`).then((r) => (r.ok ? r.json() : [])).then(setDocs).catch(() => setDocs([]));
  }, []);

  useEffect(() => {
    setLoading(true); setError('');
    fetch(`${API_BASE}/api/handbook/doc/${encodeURIComponent(slug)}`)
      .then(async (r) => { if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `HTTP ${r.status}`); return r.json(); })
      .then((d: Doc) => setDoc(d))
      .catch((e) => { setDoc(null); setError(String(e.message || e)); })
      .finally(() => setLoading(false));
  }, [slug]);

  // deep links into sections (?doc=X#heading)
  useEffect(() => {
    if (!doc || typeof window === 'undefined' || !window.location.hash) return;
    const id = decodeURIComponent(window.location.hash.slice(1));
    setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 250);
  }, [doc]);

  const toc = useMemo(() => (doc ? extractToc(doc.content) : []), [doc]);
  const isDateDoc = doc?.order === 'date';
  const visibleToc = useMemo(() => {
    let list = toc.filter((t) => t.depth >= 2 && t.depth <= 3 && (!filter || t.text.includes(filter)));
    if (isDateDoc && newestFirst) list = [...list].reverse();
    return list;
  }, [toc, filter, isDateDoc, newestFirst]);
  const meta = docs.find((d) => d.slug === slug);
  const groups = useMemo(() => {
    const g: Record<string, DocMeta[]> = {};
    docs.forEach((d) => { (g[d.group] = g[d.group] || []).push(d); });
    return Object.entries(g);
  }, [docs]);

  const open = useCallback((s: string, hash = '') => router.push(`/handbook?doc=${s}${hash}`), [router]);

  const runSearch = async () => {
    if (q.trim().length < 2) { setHits(null); return; }
    const r = await fetch(`${API_BASE}/api/handbook/search?q=${encodeURIComponent(q.trim())}`).catch(() => null);
    setHits(r && r.ok ? (await r.json()).hits : []);
  };

  const exportAll = async () => {
    const r = await fetch(`${API_BASE}/api/handbook/export`).catch(() => null);
    if (r && r.ok) download('handbook-all.md', await r.text());
  };

  const H = (level: 1 | 2 | 3 | 4) => function Heading({ children }: { children?: React.ReactNode }) {
    const Tag = `h${level}` as 'h1';
    const sizes = { 1: 'text-2xl mt-2 mb-4', 2: 'text-xl mt-8 mb-3 border-b border-gray-200 dark:border-gray-700 pb-1', 3: 'text-lg mt-6 mb-2', 4: 'text-base mt-4 mb-2' };
    return <Tag id={ghSlug(textOf(children))} className={`font-bold scroll-mt-20 dark:text-white ${sizes[level]}`}>{children}</Tag>;
  };

  return (
    <div dir="rtl" className="max-w-7xl mx-auto">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold dark:text-white">📘 جزوه و دفتر کار</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">جزوهٔ دانشِ پروژه، دفتر پیشرفت با نمودار، دفترِ ثبتِ جزئیِ همهٔ کارها، تاریخچهٔ همهٔ تغییرات و فعالیتِ مدل‌ها — زنده از GitHub</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {doc && <button onClick={() => download(`${slug}.md`, doc.content)} className="px-3 py-1.5 text-sm rounded-lg bg-white dark:bg-gray-800 border dark:border-gray-700 dark:text-white">⬇️ این سند (.md)</button>}
          <button onClick={exportAll} className="px-3 py-1.5 text-sm rounded-lg bg-white dark:bg-gray-800 border dark:border-gray-700 dark:text-white">⬇️ همهٔ اسناد (.md)</button>
          <button onClick={() => window.print()} className="px-3 py-1.5 text-sm rounded-lg bg-white dark:bg-gray-800 border dark:border-gray-700 dark:text-white">🖨 چاپ / PDF</button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <aside className="space-y-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto print:hidden">
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
            <div className="flex gap-1">
              <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && runSearch()}
                placeholder="جست‌وجو در همهٔ اسناد…" className="flex-1 min-w-0 rounded border px-2 py-1 text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600" />
              <button onClick={runSearch} className="px-2 text-sm">🔍</button>
            </div>
            {hits && (
              <div className="mt-2 max-h-64 overflow-auto space-y-1 text-xs">
                {hits.length === 0 ? <p className="text-gray-400">چیزی پیدا نشد</p> : hits.map((h, i) => (
                  <button key={i} onClick={() => open(h.slug, h.heading ? `#${ghSlug(h.heading)}` : '')}
                    className="block w-full text-right p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                    <div className="text-blue-600">{docs.find((d) => d.slug === h.slug)?.title || h.slug} › {h.heading}</div>
                    <div className="text-gray-500 dark:text-gray-400 truncate">{h.line}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <nav className="space-y-3">
            {groups.map(([group, items]) => (
              <div key={group}>
                <div className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 px-1">{group}</div>
                {items.map((d) => (
                  <button key={d.slug} onClick={() => open(d.slug)}
                    className={`block w-full text-right rounded-lg px-3 py-2 text-sm ${d.slug === slug ? 'bg-primary-600 text-white' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}`}>
                    {d.title}
                    {d.order === 'date' && <span className={`mr-1 text-[10px] ${d.slug === slug ? 'opacity-80' : 'text-gray-400'}`}>· تاریخی</span>}
                  </button>
                ))}
              </div>
            ))}
          </nav>

          {toc.length > 0 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-500">فهرستِ این سند ({visibleToc.length})</span>
                {isDateDoc && (
                  <button onClick={() => setNewestFirst((v) => !v)} className="text-[11px] text-blue-600">
                    {newestFirst ? 'جدیدترین اول' : 'قدیمی‌ترین اول'} ⇅
                  </button>
                )}
              </div>
              <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="جست‌وجو در فهرست…"
                className="mb-2 w-full rounded border px-2 py-1 text-xs dark:bg-gray-700 dark:text-white dark:border-gray-600" />
              <ul className="space-y-1 text-sm max-h-[50vh] overflow-auto">
                {visibleToc.map((t, i) => (
                  <li key={`${t.id}-${i}`} style={{ paddingRight: (t.depth - 2) * 12 }}>
                    <a href={`#${t.id}`} className="block truncate text-gray-600 dark:text-gray-300 hover:text-blue-600" title={t.text}
                      onClick={(e) => {
                        e.preventDefault();
                        document.getElementById(t.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        history.replaceState(null, '', `?doc=${slug}#${t.id}`);
                      }}>{t.text}</a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <article className="min-w-0 lg:col-span-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 print:border-0 print:p-0">
          {meta?.github_url && (
            <div className="mb-3 text-xs text-gray-400 flex gap-3 print:hidden">
              <a href={meta.github_url} target="_blank" rel="noreferrer" className="hover:text-blue-600">↗ روی GitHub</a>
              <span dir="ltr">{meta.path}</span>
              {doc?.source && <span>منبع: {doc.source === 'local' ? 'نسخهٔ محلی' : 'GitHub (زنده)'}</span>}
            </div>
          )}
          {error && <p className="text-red-600">خطا: {error}</p>}
          {loading && !doc && <p className="text-gray-400">در حال خواندن از GitHub…</p>}
          {doc && (
            <div className="leading-8 text-gray-800 dark:text-gray-200 [&_a]:text-blue-600 [&_a]:underline [&_ul]:list-disc [&_ul]:pr-6 [&_ol]:list-decimal [&_ol]:pr-6 [&_p]:my-2 [&_blockquote]:border-r-4 [&_blockquote]:border-blue-300 [&_blockquote]:pr-3 [&_blockquote]:text-gray-600 dark:[&_blockquote]:text-gray-400 [&_table]:my-3 [&_table]:w-full [&_table]:text-sm [&_th]:bg-gray-100 dark:[&_th]:bg-gray-700 [&_th]:p-2 [&_td]:p-2 [&_td]:border-t [&_td]:border-gray-200 dark:[&_td]:border-gray-700 [&_td]:align-top [&_code]:text-[0.85em] [&_code]:bg-gray-100 dark:[&_code]:bg-gray-900 [&_code]:px-1 [&_code]:rounded">
              {slug === 'PROGRESS' && <ProgressChart md={doc.content} />}
              <div className="overflow-x-auto">
                <ReactMarkdown remarkPlugins={[remarkGfm]}
                  components={{
                    h1: H(1), h2: H(2), h3: H(3), h4: H(4),
                    code({ className, children }) {
                      const lang = /language-(\w+)/.exec(className || '')?.[1];
                      if (lang === 'mermaid') return <Mermaid chart={textOf(children).trim()} />;
                      return <code className={className}>{children}</code>;
                    },
                    a({ href = '', children }) {
                      if (href.startsWith('#')) return <a href={href}>{children}</a>;
                      const target = slugForLink(href, meta, docs);
                      if (target) {
                        return <a href={`/handbook?doc=${target.slug}${target.hash}`} onClick={(e) => { e.preventDefault(); open(target.slug, target.hash); }}>{children}</a>;
                      }
                      if (href.startsWith('/') && !href.startsWith('//')) return <a href={href}>{children}</a>;
                      if (!/^https?:/.test(href) && meta?.path) {
                        // other repo files ⇒ GitHub
                        const base = meta.github_url?.replace(/\/[^/]*$/, '') || '';
                        return <a href={`${base}/${href}`} target="_blank" rel="noreferrer">{children}</a>;
                      }
                      return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
                    },
                  }}>
                  {doc.content}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </article>
      </div>
    </div>
  );
}

export default function HandbookPage() {
  return (
    <Suspense fallback={<p className="p-6 text-gray-500" dir="rtl">در حال بارگذاری...</p>}>
      <HandbookInner />
    </Suspense>
  );
}
