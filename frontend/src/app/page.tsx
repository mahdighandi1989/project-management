'use client';

/**
 * خانه — owner, 2026-11-15 (plan item 9): «مرتب، و جوری که هر تغییری در صفحه‌ها خودکار سینک شود».
 *
 * Nothing here is a hand-kept list:
 *   - the page cards (and their quick links to tabs) come from `lib/siteMap.ts` — the registry the menu, the help
 *     circle and «دستیار» also read; the docs gate refuses a page that is not registered;
 *   - the status row is live: AI providers, «اتاق فرمان», «نظارت و سرکشی»;
 *   - «تازه‌ها» is the newest WORKLOG entries and commits, read live from GitHub (`/api/handbook/recent`).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { SITE, GROUP_LABELS, APP_NAME, APP_NAME_FA, APP_TAGLINE, type SiteEntry } from '@/lib/siteMap';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Provider { name: string; available: boolean }
interface Recent {
  worklog: { title: string; signed: string; tags: string[] }[];
  commits: { sha: string; date: string; message: string; url: string }[];
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API_BASE}${path}`);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

function faDate(iso?: string) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso.slice(0, 16);
  }
}

function Stat({ href, label, value, hint, tone = 'gray' }: { href: string; label: string; value: React.ReactNode; hint?: string; tone?: 'gray' | 'green' | 'amber' | 'red' | 'blue' }) {
  const tones: Record<string, string> = {
    gray: 'border-gray-200 dark:border-gray-700',
    green: 'border-green-300 dark:border-green-700',
    amber: 'border-amber-300 dark:border-amber-700',
    red: 'border-red-300 dark:border-red-700',
    blue: 'border-blue-300 dark:border-blue-700',
  };
  return (
    <Link href={href} className={`block rounded-xl border bg-white dark:bg-gray-800 p-4 hover:shadow-md transition ${tones[tone]}`}>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      <div className="text-2xl font-bold dark:text-white mt-1">{value}</div>
      {hint && <div className="text-xs text-gray-400 mt-1 truncate">{hint}</div>}
    </Link>
  );
}

function PageCard({ e }: { e: SiteEntry }) {
  const tabs = e.tabs ? Object.entries(e.tabs) : [];
  const key = e.tabParam || 'tab';
  return (
    <div className="group rounded-xl bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition border border-gray-100 dark:border-gray-700 flex flex-col">
      <Link href={e.href} className="p-5 flex-1">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">{e.emoji}</span>
          <h3 className="text-lg font-bold dark:text-white group-hover:text-blue-600 transition">{e.label}</h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{e.desc}</p>
      </Link>
      {tabs.length > 0 && (
        <div className="px-5 pb-4 flex flex-wrap gap-1.5">
          {tabs.map(([id, label]) => (
            <Link key={id} href={`${e.href}?${key}=${id}`}
              className="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-blue-100 hover:text-blue-700 dark:hover:bg-blue-900/40">
              {label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function HomePage() {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [oversight, setOversight] = useState<any>(null);
  const [inspection, setInspection] = useState<any>(null);
  const [recent, setRecent] = useState<Recent | null>(null);
  const [disk, setDisk] = useState<any>(null);

  useEffect(() => {
    getJson<Provider[]>('/api/settings/providers').then((d) => setProviders(Array.isArray(d) ? d : []));
    getJson<any>('/api/oversight/status').then(setOversight);
    getJson<any>('/api/inspection?limit=1').then(setInspection);
    getJson<Recent>('/api/handbook/recent?limit=6').then(setRecent);
    getJson<any>('/api/oversight/disk').then(setDisk);
  }, []);

  const activeProviders = (providers || []).filter((p) => p.available);
  const groups = (['main', 'tools', 'system'] as const).map((g) => ({
    id: g, label: GROUP_LABELS[g], items: SITE.filter((s) => s.group === g && s.home),
  }));
  const extra = SITE.filter((s) => s.group === 'hidden' && s.home);
  const insOpen = inspection?.counts ? (inspection.counts.open || 0) + (inspection.counts.answered || 0) : null;

  return (
    <div className="max-w-6xl mx-auto" dir="rtl">
      {/* سرِ صفحه */}
      <div className="rounded-2xl bg-gradient-to-l from-primary-600 to-purple-600 text-white p-6 md:p-8 mb-6 shadow">
        <h1 className="text-2xl md:text-3xl font-bold" dir="ltr">{APP_NAME}</h1>
        <p className="mt-1 text-lg opacity-95">{APP_NAME_FA}</p>
        <p className="mt-2 text-sm opacity-80">{APP_TAGLINE}</p>
        <button
          onClick={() => window.dispatchEvent(new CustomEvent('assistant:open'))}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-white/15 hover:bg-white/25 px-4 py-2 text-sm">
          💬 از «دستیار» بپرس — همهٔ پروژه را زنده می‌خواند
        </button>
      </div>

      {/* وضعیتِ زنده */}
      {disk?.alert && (
        <div className="mb-4 rounded-xl border border-red-300 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 px-4 py-3 text-sm">
          💾 {disk.alert}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8" data-report-section="home-status" data-report-section-label="وضعیتِ زنده">
        <Stat href="/settings?view=models" label="مدل‌های فعال"
          value={providers === null ? '…' : activeProviders.length}
          hint={providers === null ? '' : activeProviders.length ? activeProviders.map((p) => p.name).join('، ') : 'کلیدی تنظیم نشده — مدل‌ها و تنظیمات'}
          tone={providers && activeProviders.length === 0 ? 'amber' : 'green'} />
        <Stat href="/oversight?tab=watched" label="مخازنِ تحتِ پایش (اتاق فرمان)"
          value={oversight ? oversight.watched_count : '…'}
          hint={oversight ? `GitHub ${oversight.github_token ? 'متصل' : 'بی‌توکن'} · Render ${oversight.render_token ? 'متصل' : 'بی‌توکن'}` : ''}
          tone={oversight && !oversight.github_token ? 'red' : 'blue'} />
        <Stat href="/oversight?tab=tasks" label="تسک‌های فعال"
          value={oversight ? (oversight.tasks_active_count ?? oversight.tasks_count) : '…'}
          hint={oversight?.tasks_by_status ? `در انتظارِ بازبینی ${oversight.tasks_by_status.awaiting_review || 0} · در حالِ اجرا ${oversight.tasks_by_status.running || 0}` : ''} />
        <Stat href="/inspection" label="برگه‌های بازِ نظارت و سرکشی"
          value={insOpen === null ? '…' : insOpen}
          hint={inspection?.counts ? `باز ${inspection.counts.open} · پاسخ‌داده ${inspection.counts.answered}` : ''}
          tone={insOpen ? 'amber' : 'gray'} />
        <Stat href="/handbook?doc=ACTIVITY" label="دیسکِ سرور (۱ گیگ)"
          value={disk?.percent != null ? `${disk.percent}%` : '…'}
          hint={disk ? (disk.last_run ? `آخرین پاک‌سازی: ${Math.round((disk.last_run.freed || 0) / 1048576)}MB آزاد${disk.last_run.drive ? '' : ' — درایو وصل نیست'}` : 'بایگانی به درایو هر ۶ ساعت') : ''}
          tone={disk?.percent >= 80 ? 'red' : disk?.percent >= 60 ? 'amber' : 'green'} />
      </div>

      {/* صفحه‌ها — از رجیستری */}
      {groups.map((g) => g.items.length > 0 && (
        <section key={g.id} className="mb-8">
          <h2 className="text-sm font-bold text-gray-500 dark:text-gray-400 mb-3">{g.label}</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {g.items.map((e) => <PageCard key={e.href} e={e} />)}
          </div>
        </section>
      ))}

      {/* تازه‌ها — زنده از GitHub */}
      <section className="mb-8 grid lg:grid-cols-2 gap-4" data-report-section="home-recent" data-report-section-label="تازه‌ها">
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold dark:text-white">📒 آخرین کارهای ثبت‌شده</h2>
            <Link href="/handbook?doc=WORKLOG" className="text-xs text-blue-600 hover:underline">دفتر کار ←</Link>
          </div>
          {!recent ? <p className="text-sm text-gray-400">در حال خواندن از GitHub…</p>
            : recent.worklog.length === 0 ? <p className="text-sm text-gray-400">ورودی‌ای خوانده نشد</p>
            : (
              <ul className="space-y-2 text-sm">
                {recent.worklog.map((w, i) => (
                  <li key={i} className="border-r-2 border-blue-300 pr-3">
                    <div className="dark:text-gray-200">{w.title}</div>
                    {w.signed && <div className="text-xs text-gray-400">✍️ {w.signed}</div>}
                  </li>
                ))}
              </ul>
            )}
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5">
          <h2 className="font-bold dark:text-white mb-3">🔀 آخرین تغییرات روی GitHub</h2>
          {!recent ? <p className="text-sm text-gray-400">در حال خواندن از GitHub…</p>
            : recent.commits.length === 0 ? <p className="text-sm text-gray-400">کامیتی خوانده نشد</p>
            : (
              <ul className="space-y-2 text-sm">
                {recent.commits.slice(0, 8).map((c) => (
                  <li key={c.sha} className="flex gap-2">
                    <a href={c.url} target="_blank" rel="noreferrer" className="font-mono text-xs text-blue-600 shrink-0" dir="ltr">{c.sha}</a>
                    <span className="flex-1 min-w-0 truncate dark:text-gray-200" title={c.message}>{c.message}</span>
                    <span className="text-xs text-gray-400 shrink-0">{faDate(c.date)}</span>
                  </li>
                ))}
              </ul>
            )}
        </div>
      </section>

      {extra.length > 0 && (
        <section className="mb-4">
          <h2 className="text-sm font-bold text-gray-500 dark:text-gray-400 mb-2">صفحه‌های دیگر</h2>
          <div className="flex flex-wrap gap-2">
            {extra.map((e) => (
              <Link key={e.href} href={e.href} title={e.desc}
                className="text-sm px-3 py-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:text-gray-200">
                {e.emoji} {e.label}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
