'use client';

/**
 * 📚 صفحهٔ مرکز دانش (Knowledge Center / دانشنامهٔ تجربیات)
 *
 * - فهرست (TOC) + لیست دسته‌بندی‌شدهٔ تجربیات (سینک‌شده از پوشه‌های
 *   experiences پروژه‌ها + استخراج‌شده از چت‌ها)
 * - نمایش جزئیات هر تجربه به‌صورت دانشنامه‌ای
 * - آپلود فایل چت (txt/md/html/pdf) برای استخراج تجربه با AI
 * - دکمهٔ سینک پوشه‌های experiences و ساخت پوشه‌ها
 */

import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Reference {
  source: string;
  added_at: string;
}

interface Entry {
  id: string;
  title: string;
  category: string;
  summary: string;
  content: string;
  source: string;
  project?: string | null;
  references: Reference[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface TocItem {
  id: string;
  title: string;
}

interface TocGroup {
  category: string;
  count: number;
  items: TocItem[];
}

interface EntriesResponse {
  total: number;
  entries: Entry[];
  categories: string[];
  toc: TocGroup[];
}

export default function KnowledgeCenterPage() {
  const [data, setData] = useState<EntriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('all');

  // upload state
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/knowledge-center/entries`);
      if (res.ok) {
        const json: EntriesResponse = await res.json();
        setData(json);
      } else {
        setError(`خطا در بارگذاری: ${res.status}`);
      }
    } catch (e) {
      setError('خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadMsg('');
    let ok = 0;
    let failed = 0;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadMsg(`در حال پردازش ${file.name} (${i + 1}/${files.length})...`);
      try {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch(`${API_BASE}/api/knowledge-center/import`, {
          method: 'POST',
          body: form,
        });
        if (res.ok) {
          ok += 1;
        } else {
          failed += 1;
        }
      } catch {
        failed += 1;
      }
    }
    setUploadMsg(`آپلود کامل شد — موفق: ${ok}، ناموفق: ${failed}`);
    setUploading(false);
    await loadEntries();
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg('در حال سینک پوشه‌های تجربیات...');
    try {
      const res = await fetch(`${API_BASE}/api/knowledge-center/sync`, {
        method: 'POST',
      });
      if (res.ok) {
        const json = await res.json();
        setSyncMsg(`سینک شد — ${json.files_synced ?? 0} فایل تجربه پردازش شد`);
        await loadEntries();
      } else {
        setSyncMsg(`خطا در سینک: ${res.status}`);
      }
    } catch {
      setSyncMsg('خطا در ارتباط با سرور');
    } finally {
      setSyncing(false);
    }
  };

  const selectedEntry = data?.entries.find((e) => e.id === selectedId) || null;

  const visibleToc =
    activeCategory === 'all'
      ? data?.toc || []
      : (data?.toc || []).filter((g) => g.category === activeCategory);

  return (
    <div className="max-w-6xl mx-auto" dir="rtl">
      {/* هدر */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <span>📚</span> مرکز دانش
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            دانشنامهٔ تجربیات — سینک‌شده از پروژه‌ها و استخراج‌شده از چت‌ها
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 transition"
          >
            {syncing ? 'در حال سینک...' : '🔄 سینک تجربیات'}
          </button>
          <button
            onClick={loadEntries}
            className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
          >
            تازه‌سازی
          </button>
        </div>
      </div>

      {syncMsg && (
        <div className="mb-4 text-sm text-gray-600 dark:text-gray-300">{syncMsg}</div>
      )}

      {/* بخش آپلود چت */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 mb-6 shadow border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-bold mb-2">📥 ایمپورت چت</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
          فایل‌های چت (txt / md / html / pdf) را آپلود کنید تا تجربیات با هوش
          مصنوعی استخراج و به دانشنامه اضافه شوند. فایل‌های حجیم به‌صورت خودکار
          قطعه‌بندی (chunk) می‌شوند.
        </p>
        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white cursor-pointer hover:bg-green-700 transition">
          <span>{uploading ? 'در حال آپلود...' : '➕ انتخاب فایل‌ها'}</span>
          <input
            type="file"
            multiple
            accept=".txt,.md,.markdown,.html,.htm,.pdf,text/plain,text/markdown,text/html,application/pdf"
            className="hidden"
            disabled={uploading}
            onChange={(e) => handleUpload(e.target.files)}
          />
        </label>
        {uploadMsg && (
          <span className="mr-3 text-sm text-gray-600 dark:text-gray-300">{uploadMsg}</span>
        )}
      </div>

      {/* فیلتر دسته‌بندی */}
      {data && data.categories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5">
          <button
            onClick={() => setActiveCategory('all')}
            className={`px-3 py-1.5 rounded-full text-sm transition ${
              activeCategory === 'all'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            همه ({data.total})
          </button>
          {data.categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-sm transition ${
                activeCategory === cat
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <p className="text-gray-400">در حال بارگذاری...</p>
      ) : error ? (
        <p className="text-red-500">{error}</p>
      ) : !data || data.total === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-10 text-center shadow">
          <div className="text-5xl mb-3">📭</div>
          <p className="text-gray-500 dark:text-gray-400">
            هنوز تجربه‌ای ثبت نشده. از دکمهٔ «سینک تجربیات» یا «ایمپورت چت»
            استفاده کنید.
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {/* فهرست (TOC) */}
          <aside className="md:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow sticky top-4">
              <h2 className="font-bold mb-3 text-gray-700 dark:text-gray-200">
                📑 فهرست
              </h2>
              <div className="space-y-4 max-h-[70vh] overflow-auto">
                {visibleToc.map((group) => (
                  <div key={group.category}>
                    <h3 className="text-xs font-semibold uppercase text-gray-400 mb-1">
                      {group.category} ({group.count})
                    </h3>
                    <ul className="space-y-1">
                      {group.items.map((item) => (
                        <li key={item.id}>
                          <button
                            onClick={() => setSelectedId(item.id)}
                            className={`text-right w-full text-sm px-2 py-1 rounded transition ${
                              selectedId === item.id
                                ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                          >
                            {item.title}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          </aside>

          {/* محتوای انتخاب‌شده یا لیست */}
          <section className="md:col-span-2">
            {selectedEntry ? (
              <article className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <h2 className="text-2xl font-bold">{selectedEntry.title}</h2>
                  <button
                    onClick={() => setSelectedId(null)}
                    className="text-sm text-gray-400 hover:text-gray-600"
                  >
                    ✕ بستن
                  </button>
                </div>
                <div className="flex flex-wrap gap-2 mb-4 text-xs">
                  <span className="px-2 py-1 rounded bg-primary-50 dark:bg-primary-900/30 text-primary-600">
                    {selectedEntry.category}
                  </span>
                  <span className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
                    منبع: {selectedEntry.source === 'chat_import' ? 'ایمپورت چت' : 'پوشهٔ تجربیات'}
                  </span>
                  {selectedEntry.tags.map((t) => (
                    <span key={t} className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
                      #{t}
                    </span>
                  ))}
                </div>
                <pre className="whitespace-pre-wrap break-words text-sm leading-7 text-gray-700 dark:text-gray-200 font-sans">
                  {selectedEntry.content}
                </pre>
                {selectedEntry.references.length > 0 && (
                  <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700">
                    <h3 className="text-sm font-semibold mb-2 text-gray-500">
                      🔗 منابع (References)
                    </h3>
                    <ul className="text-xs text-gray-500 space-y-1">
                      {selectedEntry.references.map((r, i) => (
                        <li key={i}>
                          {r.source} — {r.added_at?.slice(0, 10)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            ) : (
              <div className="space-y-3">
                {data.entries.map((entry) => (
                  <button
                    key={entry.id}
                    onClick={() => setSelectedId(entry.id)}
                    className="block text-right w-full bg-white dark:bg-gray-800 rounded-xl p-4 shadow hover:shadow-lg transition"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-bold text-gray-800 dark:text-gray-100">
                        {entry.title}
                      </h3>
                      <span className="text-xs px-2 py-1 rounded bg-primary-50 dark:bg-primary-900/30 text-primary-600 whitespace-nowrap">
                        {entry.category}
                      </span>
                    </div>
                    {entry.summary && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                        {entry.summary}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
