'use client';

/**
 * «خودسنجی، پیش‌نمایشِ زنده و دانلود» on a Creator Engine project (PM-INS-0025, 2026-11-17).
 *
 * After building, the engine RUNS the project (its own tests via `node --test` + a real Chromium that clicks through a
 * scenario such as «2 + 3 =» ⇒ «5») and fixes it until green. This panel shows that record, the last screenshot, the
 * live app in a sandboxed iframe (a 30-minute, project-scoped ticket in the path — an iframe cannot send the login
 * header), a zip download, and «اجرای دوباره» / «اجرا و اصلاح تا سبز» with the models selected on the page.
 */

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Round = {
  round: number;
  green?: boolean;
  auto_fixes?: string[];
  rewritten?: string[];
  problems?: string[];
  blocked?: string[];
  error?: string;
  strategy?: 'fix' | 'root_cause';
  stuck?: string[] | null;
  diagnosis?: string | null;
  tests?: { ran?: boolean; ok?: boolean; tests?: number; passed?: number; failed?: number; reason?: string };
  browser?: { ran?: boolean; ok?: boolean; errors?: number; failed_requests?: number; steps?: string; reason?: string };
};

export type Selfcheck = {
  green?: boolean;
  skipped?: string;
  error?: string;
  at?: string;
  not_converged?: { tests?: string[]; fix_rounds?: number; stopped_early?: boolean; model_diagnosis?: string | null;
    likely_cause?: string } | null;
  rounds?: Round[];
  steps?: Array<Record<string, string>>;
  final?: {
    problems?: string[];
    blocked?: string[];
    tests?: Round['tests'] & { command?: string };
    tests_output?: string;
    browser?: { ran?: boolean; ok?: boolean; steps?: Array<{ i: number; step: any; ok?: boolean; got?: string; want?: string; why?: string }>;
      steps_passed?: number; steps_total?: number; errors?: string[]; failed_requests?: string[]; reason?: string };
  };
};

function stepText(s: Record<string, any>): string {
  if (s.click !== undefined) return `کلیک «${s.click}»`;
  if (s.type !== undefined) return `تایپ «${s.type}» در ${s.into || 'ورودی'}`;
  if (s.expect !== undefined) return `انتظار «${s.expect}»${s.in ? ` در ${s.in}` : ''}`;
  return JSON.stringify(s);
}

export default function CreatorSelfcheckPanel({
  projectId, selfcheck, constraints, modelIds, onUpdated,
}: {
  projectId: string;
  selfcheck?: Selfcheck | null;
  constraints?: { phrases?: string[]; no_backend?: boolean; static_web?: boolean } | null;
  modelIds: string[];
  onUpdated?: () => void;
}) {
  const [sc, setSc] = useState<Selfcheck | null>(selfcheck || null);
  const [busy, setBusy] = useState<'' | 'check' | 'fix' | 'zip'>('');
  const [err, setErr] = useState('');
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewNote, setPreviewNote] = useState('');
  const [shot, setShot] = useState('');
  const [showLog, setShowLog] = useState(false);

  useEffect(() => { setSc(selfcheck || null); }, [selfcheck]);

  const loadShot = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/simple/projects/${projectId}/selfcheck/screenshot`);
      if (!r.ok) { setShot(''); return; }
      const b = await r.blob();
      setShot((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(b); });
    } catch { /* no screenshot yet */ }
  };

  const openPreview = async () => {
    setPreviewNote('');
    try {
      const r = await fetch(`${API_BASE}/api/simple/projects/${projectId}/preview-url`, { method: 'POST' });
      const d = await r.json();
      if (d.success && d.url) setPreviewUrl(`${API_BASE}${d.url}`);
      else { setPreviewUrl(''); setPreviewNote(d.reason || 'پیش‌نمایش در دسترس نیست'); }
    } catch (e: any) {
      setPreviewNote(e?.message || 'خطا در گرفتنِ نشانیِ پیش‌نمایش');
    }
  };

  useEffect(() => {
    loadShot();
    openPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const run = async (fix: boolean) => {
    setBusy(fix ? 'fix' : 'check');
    setErr('');
    try {
      const r = await fetch(`${API_BASE}/api/simple/projects/${projectId}/selfcheck`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // with a model the scenario is rewritten from the current HTML/JS + every requested feature
        body: JSON.stringify({ model_ids: fix ? modelIds : [], fix, max_rounds: 3, replan: fix }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      setSc(d.selfcheck);
      await loadShot();
      await openPreview();
      onUpdated?.();
    } catch (e: any) {
      setErr(e?.message || 'خطا');
    } finally {
      setBusy('');
    }
  };

  const undo = async () => {
    if (!window.confirm('فایل‌ها به پیش از آخرین «اجرا و اصلاح» برگردند؟')) return;
    setBusy('check');
    setErr('');
    try {
      const r = await fetch(`${API_BASE}/api/simple/projects/${projectId}/selfcheck/undo`, { method: 'POST' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      setSc(d.project?.selfcheck || null);
      await openPreview();
      onUpdated?.();
    } catch (e: any) {
      setErr(e?.message || 'خطا');
    } finally {
      setBusy('');
    }
  };

  const downloadZip = async () => {
    setBusy('zip');
    setErr('');
    try {
      const r = await fetch(`${API_BASE}/api/simple/projects/${projectId}/zip`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const b = await r.blob();
      const cd = r.headers.get('content-disposition') || '';
      const m = cd.match(/filename="([^"]+)"/);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(b);
      a.download = m ? m[1] : `${projectId}.zip`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    } catch (e: any) {
      setErr(e?.message || 'خطا در دانلود');
    } finally {
      setBusy('');
    }
  };

  const fin = sc?.final;
  const t = fin?.tests;
  const b = fin?.browser;
  const status = !sc || (!sc.rounds && !sc.skipped && !sc.error)
    ? { cls: 'bg-white/5 border-white/10 text-gray-300', txt: 'هنوز خودسنجی اجرا نشده' }
    : sc.skipped
      ? { cls: 'bg-white/5 border-white/10 text-gray-300', txt: `⏭ ${sc.skipped}` }
      : sc.green
        ? { cls: 'bg-green-500/15 border-green-500/40 text-green-200', txt: '✅ سبز — تست‌ها و سناریوی مرورگر درست‌اند' }
        : (sc as any).verdict === 'works_tests_rewritten'
          ? { cls: 'bg-yellow-500/15 border-yellow-500/40 text-yellow-100',
              txt: `🟡 کار می‌کند — همهٔ تست‌های فعلی و سناریوی مرورگر قبول؛ ولی مدل ${(sc as any).lost_passing ?? '?'} تا از ${(sc as any).base_passing ?? '?'} تستی را که قبول بود حذف/بازنویسی کرد (نمی‌شود فهمید تستِ غلط بود یا ضعیف شد — نگاه کنید)` }
        : sc.not_converged
          ? { cls: 'bg-red-500/15 border-red-500/40 text-red-100',
              txt: `🛑 همگرا نشد — پس از ${sc.not_converged.fix_rounds ?? 0} دورِ اصلاح همان ایرادها ماند${sc.not_converged.stopped_early ? ' (حلقه زودتر ایستاد تا همان کار را تکرار نکند)' : ''}` }
        : { cls: 'bg-amber-500/15 border-amber-500/40 text-amber-100', txt: '⚠️ هنوز ایراد دارد — جزئیات پایین' };

  return (
    <div className="bg-white/10 backdrop-blur rounded-2xl p-4 mb-6" dir="rtl">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h2 className="font-bold">🧪 خودسنجی، پیش‌نمایشِ زنده و دانلود</h2>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => run(false)} disabled={!!busy}
            className="px-3 py-1.5 rounded-lg text-sm bg-white/10 hover:bg-white/20 disabled:opacity-50">
            {busy === 'check' ? '⏳ در حال اجرا…' : '▶️ اجرای دوبارهٔ خودسنجی'}
          </button>
          <button onClick={() => run(true)} disabled={!!busy || modelIds.length === 0}
            title={modelIds.length === 0 ? 'اول یک مدل انتخاب کنید' : `با ${modelIds.join('، ')}`}
            className="px-3 py-1.5 rounded-lg text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50">
            {busy === 'fix' ? '⏳ اجرا و اصلاح… (۱ تا ۳ دقیقه)' : '🔧 اجرا و اصلاح تا سبز'}
          </button>
          <button onClick={undo} disabled={!!busy} title="۵ نسخهٔ پشتیبان پیش از هر «اجرا و اصلاح» نگه داشته می‌شود"
            className="px-3 py-1.5 rounded-lg text-sm bg-white/10 hover:bg-white/20 disabled:opacity-50">
            ↩ برگرداندن به پیش از آخرین اصلاح
          </button>
          <button onClick={downloadZip} disabled={!!busy}
            className="px-3 py-1.5 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50">
            {busy === 'zip' ? '⏳…' : '⬇️ دانلودِ zip'}
          </button>
        </div>
      </div>

      {constraints?.phrases && constraints.phrases.length > 0 && (
        <p className="text-xs text-gray-300 mb-2">
          ⛔ قیدهای صریحِ شما (رعایت شد): {constraints.phrases.map((p) => `«${p}»`).join('، ')}
        </p>
      )}
      {err && <p className="text-sm text-red-300 mb-2">❌ {err}</p>}

      <div className={`rounded-xl border p-3 text-sm mb-3 ${status.cls}`}>
        <div className="font-bold">{status.txt}</div>
        {sc?.error && <div className="text-xs mt-1">خطا: {sc.error}</div>}
        {(sc as any)?.note && <div className="text-xs mt-1">{(sc as any).note}</div>}
        {sc?.not_converged && !sc.green && (
          <div className="text-xs mt-1 space-y-0.5" data-testid="selfcheck-not-converged">
            <div>🔎 علتِ احتمالی: {sc.not_converged.likely_cause}</div>
            {sc.not_converged.model_diagnosis && <div>🤖 تشخیصِ مدل در دورِ ریشه‌یابی: {sc.not_converged.model_diagnosis}</div>}
            {sc.not_converged.tests && sc.not_converged.tests.length > 0 && (
              <div>📌 تست‌های گیرکرده ({sc.not_converged.tests.length}): {sc.not_converged.tests.map((x) => `«${x}»`).join('، ')}</div>
            )}
          </div>
        )}
        {(sc as any)?.restored_round !== undefined && (sc as any)?.restored_round !== null && (
          <div className="text-xs mt-1">↩ دورهای بعدی بدتر کردند؛ بهترین نسخه (دورِ {(sc as any).restored_round}) نگه داشته شد.</div>
        )}
        {fin && (fin as any).scenario_unresolved?.length > 0 && (
          <div className="text-xs mt-1">🧭 قدم‌هایی از سناریو که در صفحه پیدا نشد (ایرادِ سناریو، نه لزوماً برنامه): {(fin as any).scenario_unresolved.join(' · ')}</div>
        )}
        {sc?.rounds && (
          <div className="grid sm:grid-cols-3 gap-2 mt-2 text-xs">
            <div>📦 تست‌ها ({t?.command || 'npm test'}): {t?.ran
              ? `${t.passed ?? 0}/${t.tests ?? 0} قبول${t.failed ? ` · ${t.failed} رد` : ''}`
              : (t?.reason || 'اجرا نشد')}</div>
            <div>🌐 مرورگر: {b?.ran
              ? `سناریو ${b.steps_passed ?? 0}/${b.steps_total ?? 0} · خطای صفحه ${b.errors?.length ?? 0} · درخواستِ ناموفق ${b.failed_requests?.length ?? 0}`
              : (b?.reason ? `اجرا نشد: ${b.reason.slice(0, 120)}` : 'اجرا نشد')}</div>
            <div>🔁 دورها: {sc.rounds.length - 1} دورِ اصلاح{sc.at ? ` · ${new Date(sc.at).toLocaleString('fa-IR')}` : ''}</div>
          </div>
        )}
        {fin?.blocked && fin.blocked.length > 0 && (
          <ul className="text-xs mt-2 list-disc pr-5">{fin.blocked.map((x, i) => <li key={i}>🚧 {x}</li>)}</ul>
        )}
        {fin?.problems && fin.problems.length > 0 && (
          <ul className="text-xs mt-2 list-disc pr-5 max-h-40 overflow-auto">
            {fin.problems.map((x, i) => <li key={i} className="whitespace-pre-wrap">{x.slice(0, 400)}</li>)}
          </ul>
        )}
      </div>

      {b?.steps && b.steps.length > 0 && (
        <div className="text-xs mb-3">
          <div className="font-bold mb-1">سناریوی مرورگر (همان که اجرا شد)</div>
          <ol className="list-decimal pr-5 space-y-0.5">
            {b.steps.map((s) => (
              <li key={s.i} className={s.ok ? 'text-green-300' : 'text-red-300'}>
                {s.ok ? '✓' : '✗'} {stepText(s.step)}{s.got !== undefined ? ` — صفحه: «${s.got}»` : ''}{s.why && !s.ok ? ` — ${s.why}` : ''}
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-3">
        <div>
          <div className="text-xs text-gray-300 mb-1 flex items-center justify-between">
            <span>🖥 پیش‌نمایشِ زنده (sandbox؛ کدِ ساخته‌شده به حساب و API دسترسی ندارد)</span>
            {previewUrl && <button onClick={openPreview} className="underline">↻ تازه</button>}
          </div>
          {previewUrl ? (
            <iframe key={previewUrl} src={previewUrl} title="پیش‌نمایشِ پروژه"
              sandbox="allow-scripts allow-forms allow-modals allow-popups"
              className="w-full h-[420px] rounded-lg bg-white border border-white/10" />
          ) : (
            <div className="h-[120px] flex items-center justify-center rounded-lg bg-black/20 text-xs text-gray-400">
              {previewNote || '…'}
            </div>
          )}
        </div>
        <div>
          <div className="text-xs text-gray-300 mb-1">📸 آخرین عکسِ خودسنجی (پس از اجرای سناریو)</div>
          {shot ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={shot} alt="عکسِ خودسنجی" className="w-full rounded-lg border border-white/10 bg-white" />
          ) : (
            <div className="h-[120px] flex items-center justify-center rounded-lg bg-black/20 text-xs text-gray-400">عکسی نیست</div>
          )}
        </div>
      </div>

      {sc?.rounds && (
        <div className="mt-3 text-xs">
          <button onClick={() => setShowLog((v) => !v)} className="underline text-gray-300">
            {showLog ? '▲ بستنِ' : '▼ دیدنِ'} گزارشِ دور به دور{fin?.tests_output ? ' و خروجیِ تست' : ''}
          </button>
          {showLog && (
            <div className="mt-2 space-y-2">
              {sc.rounds.map((r) => (
                <div key={r.round} className="rounded-lg bg-black/20 p-2">
                  <div className="font-bold">{r.round === 0 ? 'اجرای اول' : `دورِ اصلاحِ ${r.round}`} — {r.green ? '✅ سبز' : '⚠️'}</div>
                  {r.strategy === 'root_cause' && (
                    <div>🔎 تغییرِ راهبرد: {r.stuck?.length ?? 0} تست دو دور پشتِ هم رد شد ⇒ ریشه‌یابی (تست غلط است یا کد؟){r.diagnosis ? ` — تشخیص: ${r.diagnosis}` : ''}</div>
                  )}
                  {r.auto_fixes && r.auto_fixes.length > 0 && <div>🔩 اصلاحِ خودکار: {r.auto_fixes.join(' · ')}</div>}
                  {r.rewritten && r.rewritten.length > 0 && <div>✍️ بازنویسیِ مدل: {r.rewritten.join('، ')}</div>}
                  {r.tests && <div>📦 تست: {r.tests.ran ? `${r.tests.passed ?? 0}/${r.tests.tests ?? 0}` : (r.tests.reason || '—')}</div>}
                  {r.browser && <div>🌐 مرورگر: {r.browser.ran ? `سناریو ${r.browser.steps} · خطا ${r.browser.errors}` : (r.browser.reason || '—')}</div>}
                  {r.error && <div className="text-red-300">خطا: {r.error}</div>}
                </div>
              ))}
              {fin?.tests_output && (
                <pre className="rounded-lg bg-black/40 p-2 overflow-auto max-h-60 text-[11px] whitespace-pre-wrap" dir="ltr">
                  {fin.tests_output}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
