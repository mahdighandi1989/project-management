'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Entry {
  id: string;
  project_id?: string | null;
  project_full_name: string;
  path: string;
  title: string;
  topic_canonical?: string;
  tags: string[];
  source_type: string;
  source_origin: string;
  summary: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
  imported_at?: string;
  merged_from?: string[];
  generated_by?: string;
  resolution_status?: string;
  recurrence_count?: number;
  user_confirmed?: boolean;
}

interface Facets {
  tags: [string, number][];
  sources: [string, number][];
  projects: [string, number][];
  resolutions?: [string, number][];
}

interface ListResponse {
  items: Entry[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  facets: Facets;
}

interface Model {
  id: string;
  name: string;
}

export default function KnowledgeCenterPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [resolutionFilter, setResolutionFilter] = useState('');
  const [sort, setSort] = useState('updated_desc');
  const [selectedEntry, setSelectedEntry] = useState<Entry | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  // 🆕 KC settings panel — auto-sync interval, processing models,
  // skip_unchanged, etc. Persisted via PATCH /knowledge-center/settings.
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [kcSettings, setKcSettings] = useState<any>({
    auto_sync_enabled: true,
    auto_sync_interval_minutes: 60,
    processing_model_ids: [],
    skip_unchanged: true,
    max_indexed_entries: 5000,
  });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState('');

  // Load active models + persisted KC settings (so processing_model_ids
  // shows the user's saved selection, not hardcoded defaults)
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/simple/status`);
        const j = await res.json();
        setModels(j?.models || []);
      } catch { /* */ }
      try {
        const res = await fetch(`${API_BASE}/api/knowledge-center/settings`);
        const j = await res.json();
        if (j && typeof j === 'object') setKcSettings(j);
      } catch { /* */ }
    })();
    try {
      const saved = localStorage.getItem('creator_selected_models');
      if (saved) setSelectedModelIds(JSON.parse(saved));
    } catch { /* */ }
  }, []);

  const saveSettings = async (patch: any) => {
    setSettingsLoading(true);
    setSettingsSaved('');
    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/settings`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      );
      const j = await res.json();
      if (res.ok) {
        setKcSettings(j);
        setSettingsSaved('✅ ذخیره شد');
        setTimeout(() => setSettingsSaved(''), 2000);
      } else {
        setSettingsSaved('❌ خطا: ' + (j?.detail || res.status));
      }
    } catch (e: any) {
      setSettingsSaved('❌ خطا: ' + (e?.message || 'unknown'));
    } finally {
      setSettingsLoading(false);
    }
  };

  const triggerManualProcess = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/process`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model_ids: kcSettings.processing_model_ids || [],
            force: false,
          }),
        },
      );
      const j = await res.json();
      if (j?.ok) {
        alert(
          `✅ پردازش انجام شد — ${j.processed || 0} پردازش، ${j.skipped || 0} skip ` +
          `(تغییری نداشتند). از ${j.total || 0} entry کل.`,
        );
        loadEntries();
      } else {
        alert('❌ خطا: ' + (j?.detail || 'unknown'));
      }
    } catch (e: any) {
      alert('خطا: ' + e?.message);
    } finally {
      setLoading(false);
    }
  };

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: String(perPage),
        sort,
      });
      if (search) params.set('search', search);
      if (tagFilter) params.set('tag', tagFilter);
      if (projectFilter) params.set('project_id', projectFilter);
      if (sourceFilter) params.set('source_type', sourceFilter);
      if (resolutionFilter) params.set('resolution_status', resolutionFilter);
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/entries?${params.toString()}`,
      );
      const j = await res.json();
      if (!res.ok) {
        setError(j?.detail || `HTTP ${res.status}`);
        return;
      }
      setData(j as ListResponse);
    } catch (e: any) {
      setError(e?.message || 'خطا در ارتباط');
    } finally {
      setLoading(false);
    }
  }, [page, perPage, search, tagFilter, projectFilter, sourceFilter, resolutionFilter, sort]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  // Debounced search — reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [search, tagFilter, projectFilter, sourceFilter, resolutionFilter, sort]);

  const syncFromRepos = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/sync`,
        { method: 'POST' },
      );
      const j = await res.json();
      if (j?.ok) {
        alert(
          `✅ سینک تمام شد — ${j.added || 0} اضافه، ${j.updated || 0} به‌روز، ` +
          `${j.total || 0} کل`,
        );
        loadEntries();
      } else {
        alert('❌ سینک ناموفق: ' + (j?.error || 'unknown'));
      }
    } catch (e: any) {
      alert('خطا: ' + e?.message);
    } finally {
      setLoading(false);
    }
  };

  const bootstrapFolders = async () => {
    if (!confirm(
      'این عملیات در همهٔ پروژه‌های تحت نظارت پوشهٔ experiences/ + README ' +
      'فرمت می‌سازد (idempotent — پوشه‌های موجود دست نمی‌خورند). ادامه؟',
    )) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/bootstrap`,
        { method: 'POST' },
      );
      const j = await res.json();
      alert(
        `✅ ${j.created || 0} پوشه ساخته شد، ${j.skipped || 0} skip ` +
        `(از قبل بود یا توکن نبود).`,
      );
    } catch (e: any) {
      alert('خطا: ' + e?.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteEntry = async (entry: Entry) => {
    if (!confirm(
      `حذف "${entry.title}"؟\n\n` +
      `این کار از index حذف می‌کند و در صورت اتصال GitHub، فایل را از repo ` +
      `هم پاک می‌کند (قابل بازگشت نیست).`,
    )) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/entries/${entry.id}`,
        {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ delete_from_repo: true }),
        },
      );
      const j = await res.json();
      if (j?.ok) {
        if (selectedEntry?.id === entry.id) setSelectedEntry(null);
        loadEntries();
      } else {
        alert('❌ ' + (j?.error || 'unknown'));
      }
    } catch (e: any) {
      alert('خطا: ' + e?.message);
    }
  };

  // Tag chip styling helper
  const fmtBytes = (n: number) => {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1024 / 1024).toFixed(2)} MB`;
  };

  const fmtDate = (s: string) => {
    if (!s) return '—';
    try { return new Date(s).toLocaleString('fa-IR'); }
    catch { return s; }
  };

  const headerStats = useMemo(() => {
    if (!data) return null;
    return {
      total: data.total,
      tags: data.facets?.tags?.length || 0,
      projects: data.facets?.projects?.length || 0,
    };
  }, [data]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6" dir="rtl">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              📚 مرکز دانش
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              کاتالوگ تجربیات قابل‌استفاده‌مجدد از همهٔ پروژه‌های تحت نظارت.
              هر تجربه به‌صورت project-agnostic ثبت می‌شود تا بشود در پروژه‌های
              دیگر اعمال کرد.
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setUploadOpen(true)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium"
            >
              📤 آپلود چت برای استخراج
            </button>
            <button
              onClick={syncFromRepos}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
            >
              🔄 سینک از repo
            </button>
            <button
              onClick={bootstrapFolders}
              disabled={loading}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg disabled:opacity-50"
              title="در همهٔ پروژه‌های تحت نظارت پوشهٔ experiences + README می‌سازد"
            >
              🛠 ساخت پوشهٔ تجربیات (همه پروژه‌ها)
            </button>
            <button
              onClick={triggerManualProcess}
              disabled={loading}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50"
              title="با مدل‌های تنظیم‌شده در ⚙️ پردازش AI رو دستی اجرا کن (تغییرنکرده‌ها skip می‌شوند)"
            >
              🧠 پردازش با AI
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg"
              title="تنظیمات: مدل‌های پردازش، interval auto-sync، skip-if-unchanged"
            >
              ⚙️ تنظیمات
            </button>
          </div>
        </div>

        {/* Stats cards */}
        {headerStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-xs text-gray-400">کل تجربیات</div>
              <div className="text-2xl font-bold">{headerStats.total}</div>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-xs text-gray-400">تگ‌ها</div>
              <div className="text-2xl font-bold">{headerStats.tags}</div>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-xs text-gray-400">پروژه‌های مشارکت‌کننده</div>
              <div className="text-2xl font-bold">{headerStats.projects}</div>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-xs text-gray-400">صفحه</div>
              <div className="text-2xl font-bold">{page}/{data?.pages || 1}</div>
            </div>
          </div>
        )}

        {/* Filters / search bar */}
        <div className="bg-white/5 rounded-lg p-4 mb-4 flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔎 جستجو در عنوان، خلاصه، تگ، پروژه..."
            className="flex-1 min-w-[200px] px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
          />
          <select
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            className="px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
          >
            <option value="">همهٔ تگ‌ها</option>
            {(data?.facets?.tags || []).map(([t, n]) => (
              <option key={t} value={t}>{t} ({n})</option>
            ))}
          </select>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
          >
            <option value="">همهٔ پروژه‌ها</option>
            {(data?.facets?.projects || []).map(([p, n]) => (
              <option key={p} value={p}>{p} ({n})</option>
            ))}
          </select>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
          >
            <option value="">همهٔ منابع</option>
            {(data?.facets?.sources || []).map(([s, n]) => (
              <option key={s} value={s}>{s} ({n})</option>
            ))}
          </select>
          <select
            value={resolutionFilter}
            onChange={(e) => setResolutionFilter(e.target.value)}
            className="px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
            title="فیلتر بر اساس وضعیت حل‌شدگی موضوع"
          >
            <option value="">همهٔ وضعیت‌ها</option>
            {(data?.facets?.resolutions || []).map(([r, n]) => (
              <option key={r} value={r}>{r} ({n})</option>
            ))}
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
          >
            <option value="updated_desc">جدیدترین به‌روزرسانی</option>
            <option value="updated_asc">قدیمی‌ترین به‌روزرسانی</option>
            <option value="created_desc">جدیدترین ساخت</option>
            <option value="title_asc">عنوان (الفبایی)</option>
            <option value="title_desc">عنوان (معکوس)</option>
            <option value="size_desc">حجیم‌ترین</option>
          </select>
          <select
            value={perPage}
            onChange={(e) => setPerPage(parseInt(e.target.value))}
            className="px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
          >
            {[10, 20, 50, 100].map((n) => (
              <option key={n} value={n}>{n} در صفحه</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500/50 rounded p-3 mb-4 text-red-200">
            ❌ {error}
          </div>
        )}

        {/* Entries grid */}
        {loading && !data ? (
          <div className="text-center py-12 text-gray-400">در حال بارگذاری…</div>
        ) : data?.items?.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg mb-2">هیچ تجربه‌ای یافت نشد.</p>
            <p className="text-sm">
              برای شروع، روی «🛠 ساخت پوشهٔ تجربیات» بزن تا پوشه در همه repo‌ها
              ساخته شود، سپس از کلاد کد بخواه تجربیاتت را ثبت کند یا فایل چت
              آپلود کن.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
            {data?.items?.map((entry) => (
              <div
                key={entry.id}
                className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg p-4 cursor-pointer transition-all"
                onClick={() => setSelectedEntry(entry)}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-bold text-sm flex-1">{entry.title}</h3>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteEntry(entry);
                    }}
                    className="text-red-400 hover:text-red-300 text-xs"
                    title="حذف"
                  >
                    🗑
                  </button>
                </div>
                <p className="text-xs text-gray-400 mb-2 line-clamp-2" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {entry.summary || '—'}
                </p>
                <div className="flex flex-wrap gap-1 mb-2 items-center">
                  {entry.resolution_status && entry.resolution_status !== 'unknown' && (
                    <ResolutionBadge
                      status={entry.resolution_status}
                      recurrence={entry.recurrence_count}
                      confirmed={entry.user_confirmed}
                    />
                  )}
                  {(entry.tags || []).slice(0, 4).map((t) => (
                    <span
                      key={t}
                      className="px-1.5 py-0.5 bg-blue-500/20 text-blue-300 rounded text-[10px]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
                <div className="text-[10px] text-gray-500 flex items-center justify-between">
                  <span className="font-mono truncate">{entry.project_full_name || '—'}</span>
                  <span>{fmtBytes(entry.size_bytes || 0)}</span>
                </div>
                <div className="text-[10px] text-gray-500 flex items-center justify-between mt-1">
                  <span>{entry.source_type}</span>
                  {entry.generated_by && (
                    <span className="text-blue-300">{entry.generated_by.slice(0, 16)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex justify-center gap-2 flex-wrap">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="px-3 py-1 bg-white/10 rounded disabled:opacity-30 text-sm"
            >
              قبلی
            </button>
            {Array.from({ length: Math.min(7, data.pages) }, (_, i) => {
              let p = i + 1;
              if (data.pages > 7) {
                if (page > 4 && page < data.pages - 3) {
                  p = page - 3 + i;
                } else if (page >= data.pages - 3) {
                  p = data.pages - 6 + i;
                }
              }
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-3 py-1 rounded text-sm ${
                    p === page ? 'bg-blue-500' : 'bg-white/10 hover:bg-white/20'
                  }`}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage(Math.min(data.pages, page + 1))}
              disabled={page >= data.pages}
              className="px-3 py-1 bg-white/10 rounded disabled:opacity-30 text-sm"
            >
              بعدی
            </button>
          </div>
        )}
      </div>

      {/* Detail modal */}
      {selectedEntry && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setSelectedEntry(null)}
        >
          <div
            className="bg-gray-900 border border-white/10 rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-gray-900 p-4 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-bold">{selectedEntry.title}</h3>
              <button
                onClick={() => setSelectedEntry(null)}
                className="px-3 py-1 bg-white/10 rounded hover:bg-white/20"
              >
                بستن
              </button>
            </div>
            <div className="p-6 space-y-3 text-sm">
              <div><span className="text-gray-400">پروژه:</span> <span className="font-mono">{selectedEntry.project_full_name || '—'}</span></div>
              <div><span className="text-gray-400">مسیر:</span> <span className="font-mono">{selectedEntry.path}</span></div>
              <div><span className="text-gray-400">topic_canonical:</span> <span className="font-mono">{selectedEntry.topic_canonical || '—'}</span></div>
              <div><span className="text-gray-400">منبع:</span> {selectedEntry.source_type} {selectedEntry.source_origin && `(${selectedEntry.source_origin})`}</div>
              {selectedEntry.generated_by && (
                <div><span className="text-gray-400">تولیدشده توسط:</span> <span className="font-mono text-blue-300">{selectedEntry.generated_by}</span></div>
              )}
              <div><span className="text-gray-400">ساخت:</span> {fmtDate(selectedEntry.created_at)}</div>
              <div><span className="text-gray-400">آخرین آپدیت:</span> {fmtDate(selectedEntry.updated_at)}</div>
              <div><span className="text-gray-400">حجم:</span> {fmtBytes(selectedEntry.size_bytes)}</div>
              <div>
                <span className="text-gray-400">تگ‌ها:</span>{' '}
                {(selectedEntry.tags || []).map((t) => (
                  <span key={t} className="ml-1 px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded text-xs">{t}</span>
                ))}
              </div>
              {selectedEntry.resolution_status && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">وضعیت حل:</span>
                  <ResolutionBadge
                    status={selectedEntry.resolution_status}
                    recurrence={selectedEntry.recurrence_count}
                    confirmed={selectedEntry.user_confirmed}
                  />
                </div>
              )}
              {selectedEntry.merged_from && selectedEntry.merged_from.length > 0 && (
                <div>
                  <span className="text-gray-400">merged_from:</span>
                  <ul className="list-disc pr-5 text-xs text-gray-300 mt-1">
                    {selectedEntry.merged_from.map((m, i) => (
                      <li key={i} className="font-mono">{m}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="border-t border-white/10 pt-3">
                <div className="text-gray-400 mb-1">خلاصه:</div>
                <pre className="whitespace-pre-wrap text-gray-200 text-xs font-sans">{selectedEntry.summary}</pre>
              </div>
              <div className="text-xs text-gray-500 pt-2 border-t border-white/10">
                💡 برای ویرایش محتوای کامل، فایل را مستقیماً در repo باز کن:
                <span className="font-mono"> {selectedEntry.project_full_name}/{selectedEntry.path}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload chat modal */}
      {uploadOpen && (
        <UploadChatModal
          models={models}
          selectedModelIds={selectedModelIds}
          onClose={() => setUploadOpen(false)}
          onDone={() => { setUploadOpen(false); loadEntries(); }}
        />
      )}

      {/* Settings modal */}
      {settingsOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => !settingsLoading && setSettingsOpen(false)}
        >
          <div
            className="bg-gray-900 border border-white/10 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-gray-900 p-4 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-bold text-lg">⚙️ تنظیمات مرکز دانش</h3>
              <button
                onClick={() => setSettingsOpen(false)}
                disabled={settingsLoading}
                className="px-3 py-1 bg-white/10 rounded hover:bg-white/20 disabled:opacity-50"
              >
                بستن
              </button>
            </div>
            <div className="p-6 space-y-6">
              {/* Auto-sync section */}
              <div className="space-y-3">
                <h4 className="font-bold text-blue-300">🔁 سینک خودکار</h4>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={kcSettings.auto_sync_enabled !== false}
                    onChange={(e) => saveSettings({ auto_sync_enabled: e.target.checked })}
                    disabled={settingsLoading}
                  />
                  <span className="text-sm">
                    فعال‌سازی سینک خودکار از repo‌ها + پردازش AI
                  </span>
                </label>
                <div className="flex items-center gap-2">
                  <label className="text-sm">Interval (دقیقه):</label>
                  <input
                    type="number"
                    min={5}
                    max={1440}
                    value={kcSettings.auto_sync_interval_minutes || 60}
                    onChange={(e) => {
                      const v = parseInt(e.target.value);
                      if (v >= 5) {
                        setKcSettings({ ...kcSettings, auto_sync_interval_minutes: v });
                      }
                    }}
                    onBlur={(e) => {
                      const v = parseInt(e.target.value);
                      if (v >= 5 && v !== kcSettings.auto_sync_interval_minutes) {
                        saveSettings({ auto_sync_interval_minutes: v });
                      }
                    }}
                    disabled={settingsLoading}
                    className="px-3 py-1 bg-black/40 border border-white/10 rounded text-sm w-24"
                  />
                  <span className="text-xs text-gray-400">
                    حداقل ۵ دقیقه (محافظت از rate-limit GitHub)
                  </span>
                </div>
              </div>

              {/* Processing model picker — THE thing the user asked for */}
              <div className="space-y-3">
                <h4 className="font-bold text-purple-300">
                  🤖 مدل‌های پردازش AI
                </h4>
                <p className="text-xs text-gray-400">
                  هر مدل فعالی از صفحهٔ "مدل‌ها" می‌توانی انتخاب کنی. این
                  انتخاب در هر سیکل auto-sync و دکمهٔ "پردازش با AI" استفاده
                  می‌شود. اگر هیچ‌کدام تیک نخورد، پیش‌فرض ai_manager (همه
                  مدل‌های available) به‌کار می‌رود.
                </p>
                {models.length === 0 ? (
                  <p className="text-sm text-amber-300">
                    ⚠️ هیچ مدل فعالی پیدا نشد. ابتدا در صفحهٔ مدل‌ها API key یا
                    OAuth token را فعال کن.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {models.map((m) => {
                      const checked = (kcSettings.processing_model_ids || [])
                        .includes(m.id);
                      return (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => {
                            const cur = kcSettings.processing_model_ids || [];
                            const next = checked
                              ? cur.filter((x: string) => x !== m.id)
                              : [...cur, m.id];
                            saveSettings({ processing_model_ids: next });
                          }}
                          disabled={settingsLoading}
                          className={`px-3 py-1.5 rounded text-xs ${
                            checked
                              ? 'bg-purple-600 text-white'
                              : 'bg-white/10 hover:bg-white/20'
                          }`}
                        >
                          {checked ? '✓ ' : ''}{m.name || m.id}
                        </button>
                      );
                    })}
                  </div>
                )}
                <div className="text-xs text-gray-400">
                  انتخاب فعلی:{' '}
                  {(kcSettings.processing_model_ids || []).length === 0
                    ? '(هیچ — auto)'
                    : (kcSettings.processing_model_ids || []).join(', ')}
                </div>
              </div>

              {/* Optimization toggles */}
              <div className="space-y-3">
                <h4 className="font-bold text-green-300">⚡ بهینه‌سازی</h4>
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={kcSettings.skip_unchanged !== false}
                    onChange={(e) => saveSettings({ skip_unchanged: e.target.checked })}
                    disabled={settingsLoading}
                    className="mt-1"
                  />
                  <div>
                    <div className="text-sm">skip-if-unchanged</div>
                    <div className="text-xs text-gray-400">
                      فایل‌هایی که content_hash تغییر نکرده دوباره پردازش
                      نمی‌شوند. صرفه‌جویی در token + جلوگیری از کار تکراری.
                    </div>
                  </div>
                </label>
                <div className="flex items-center gap-2">
                  <label className="text-sm">سقف entry‌های ایندکس:</label>
                  <input
                    type="number"
                    min={0}
                    max={50000}
                    value={kcSettings.max_indexed_entries || 0}
                    onChange={(e) => {
                      setKcSettings({
                        ...kcSettings,
                        max_indexed_entries: parseInt(e.target.value) || 0,
                      });
                    }}
                    onBlur={(e) => {
                      const v = parseInt(e.target.value) || 0;
                      if (v !== kcSettings.max_indexed_entries) {
                        saveSettings({ max_indexed_entries: v });
                      }
                    }}
                    disabled={settingsLoading}
                    className="px-3 py-1 bg-black/40 border border-white/10 rounded text-sm w-28"
                  />
                  <span className="text-xs text-gray-400">
                    ۰ = نامحدود. مازاد، قدیمی‌ترها de-index می‌شوند (فایل در
                    repo می‌ماند).
                  </span>
                </div>
              </div>

              {settingsSaved && (
                <div className="text-sm text-green-300">{settingsSaved}</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// Upload modal — chat import with model selection
// ─────────────────────────────────────────────────────────────────────────────


interface UploadProps {
  models: Model[];
  selectedModelIds: string[];
  onClose: () => void;
  onDone: () => void;
}

function UploadChatModal({ models, selectedModelIds: initialSelected, onClose, onDone }: UploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [targetProjectId, setTargetProjectId] = useState('');
  const [projects, setProjects] = useState<{ id: string; repo_full_name: string }[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>(initialSelected);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/oversight/watched`);
        const j = await res.json();
        const items = j?.items || j?.watched || [];
        setProjects(items.map((w: any) => ({ id: w.id, repo_full_name: w.repo_full_name })));
      } catch { /* */ }
    })();
  }, []);

  const submit = async () => {
    if (!file) {
      setError('فایل را انتخاب کن.');
      return;
    }
    setUploading(true);
    setError('');
    setResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('target_project_id', targetProjectId);
      form.append('model_ids', selectedModels.join(','));
      const res = await fetch(
        `${API_BASE}/api/knowledge-center/import`,
        { method: 'POST', body: form },
      );
      const j = await res.json();
      if (!res.ok || !j?.ok) {
        setError(j?.detail || j?.error || `HTTP ${res.status}`);
        return;
      }
      setResult(j);
    } catch (e: any) {
      setError(e?.message || 'خطا در ارتباط');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={() => !uploading && onClose()}
    >
      <div
        className="bg-gray-900 border border-white/10 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-gray-900 p-4 border-b border-white/10 flex items-center justify-between">
          <h3 className="font-bold text-lg">📤 آپلود چت برای استخراج تجربه</h3>
          <button onClick={onClose} disabled={uploading} className="px-3 py-1 bg-white/10 rounded">بستن</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm mb-1">فایل چت (txt / md / html / pdf):</label>
            <input
              type="file"
              accept=".txt,.md,.html,.htm,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={uploading}
              className="w-full text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              متن فایل با مدل‌های انتخابی تحلیل می‌شود تا چالش‌ها/راه‌حل‌ها به‌صورت
              project-agnostic استخراج شوند. حجم بالا خودکار chunk می‌شود.
            </p>
          </div>

          <div>
            <label className="block text-sm mb-1">پروژهٔ مقصد (اختیاری):</label>
            <select
              value={targetProjectId}
              onChange={(e) => setTargetProjectId(e.target.value)}
              disabled={uploading}
              className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded text-sm"
            >
              <option value="">— بدون پروژهٔ مشخص (فقط index)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.repo_full_name}</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              اگر پروژه انتخاب شود، فایل تجربه در experiences/ آن پروژه نوشته می‌شود.
            </p>
          </div>

          <div>
            <label className="block text-sm mb-1">مدل‌های AI برای استخراج:</label>
            <div className="flex flex-wrap gap-2">
              {models.map((m) => {
                const checked = selectedModels.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setSelectedModels(
                        checked
                          ? selectedModels.filter((x) => x !== m.id)
                          : [...selectedModels, m.id],
                      );
                    }}
                    disabled={uploading}
                    className={`px-3 py-1 rounded text-xs ${
                      checked ? 'bg-blue-500 text-white' : 'bg-white/10 hover:bg-white/20'
                    }`}
                  >
                    {m.name || m.id}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              اگر هیچ مدلی انتخاب نشود، مدل پیش‌فرض استفاده می‌شود.
            </p>
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded p-3 text-red-200 text-sm">
              ❌ {error}
            </div>
          )}

          {result && (
            <div className="bg-green-500/10 border border-green-500/30 rounded p-3 text-sm space-y-1">
              <div className="font-bold text-green-300">✅ نتیجه:</div>
              {result.pass_mode === 'two_pass' ? (
                <>
                  <div>🧠 حالت: دومرحله‌ای (outline → deep)</div>
                  <div>🎯 موضوعات شناسایی‌شده: {result.topics_identified}</div>
                </>
              ) : (
                <>
                  <div>📄 حالت: تک‌مرحله‌ای (fallback chunking)</div>
                  <div>📦 chunks پردازش‌شده: {result.chunks_processed}</div>
                </>
              )}
              <div>➕ تجربیات جدید: {result.created}</div>
              <div>🔀 ادغام با موجود: {result.merged}</div>
              {result.errors?.length > 0 && (
                <div className="text-amber-300">⚠️ خطاها: {result.errors.length}</div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
            <button
              onClick={onClose}
              disabled={uploading}
              className="px-4 py-2 bg-white/10 rounded"
            >
              بستن
            </button>
            {result ? (
              <button onClick={onDone} className="px-4 py-2 bg-green-500 text-white rounded">
                مشاهدهٔ نتایج
              </button>
            ) : (
              <button
                onClick={submit}
                disabled={uploading || !file}
                className="px-4 py-2 bg-purple-600 text-white rounded disabled:opacity-50"
              >
                {uploading ? '... در حال استخراج' : '🚀 شروع استخراج'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


function ResolutionBadge({
  status,
  recurrence,
  confirmed,
}: {
  status: string;
  recurrence?: number;
  confirmed?: boolean;
}) {
  const cls: Record<string, string> = {
    solved: 'bg-green-500/20 text-green-300',
    partial: 'bg-yellow-500/20 text-yellow-300',
    open: 'bg-gray-500/20 text-gray-300',
    regressed: 'bg-red-500/20 text-red-300',
    unknown: 'bg-white/10 text-gray-400',
  };
  const icon: Record<string, string> = {
    solved: '✅',
    partial: '🟡',
    open: '⏳',
    regressed: '🔁',
    unknown: '❓',
  };
  const c = cls[status] || cls.unknown;
  const i = icon[status] || icon.unknown;
  return (
    <span
      className={`px-1.5 py-0.5 rounded text-[10px] ${c}`}
      title={
        `وضعیت: ${status}` +
        (recurrence && recurrence > 1 ? ` • تکرار: ${recurrence}×` : '') +
        (confirmed ? ' • تأیید کاربر' : '')
      }
    >
      {i} {status}
      {recurrence && recurrence > 1 ? ` ×${recurrence}` : ''}
      {confirmed ? ' ✓' : ''}
    </span>
  );
}
