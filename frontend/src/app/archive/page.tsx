'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DebateItem {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models?: string[];
  rounds_count?: number;
  has_judge?: boolean;
  has_summary?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface FileItem {
  id: string;
  original_name: string;
  stored_name?: string;
  mime_type?: string;
  size: number;
  category?: string;
  subcategory?: string;
  created_at?: string;
  tags?: string[];
}

interface ProjectItem {
  id: string;
  name: string;
  description: string;
  project_type: string;
  status?: string;
  files?: any[];
  created_at?: string;
}

interface DebateDetail {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models: string[];
  rounds: any[][];
  judge_result?: any;
  summary?: string;
  created_at?: string;
}

type TabType = 'debates' | 'files' | 'projects';

export default function ArchivePage() {
  const [tab, setTab] = useState<TabType>('debates');
  const [debates, setDebates] = useState<DebateItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'name'>('newest');

  const [selectedDebateId, setSelectedDebateId] = useState<string | null>(null);
  const [selectedDebate, setSelectedDebate] = useState<DebateDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedDebateId) loadDebateDetail(selectedDebateId);
  }, [selectedDebateId]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };
  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 3000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [debatesRes, filesRes, projectsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/debate/`),
        fetch(`${API_BASE}/api/upload/files`),
        fetch(`${API_BASE}/api/simple/projects`),
      ]);

      if (debatesRes.status === 'fulfilled' && debatesRes.value.ok) {
        const data = await debatesRes.value.json();
        setDebates(Array.isArray(data) ? data : []);
      }

      if (filesRes.status === 'fulfilled' && filesRes.value.ok) {
        const data = await filesRes.value.json();
        // upload/files returns array directly
        setFiles(Array.isArray(data) ? data : data?.files || []);
      }

      if (projectsRes.status === 'fulfilled' && projectsRes.value.ok) {
        const data = await projectsRes.value.json();
        setProjects(data?.projects || []);
      }
    } catch (e) {
      console.error('Error loading archive:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadDebateDetail = async (id: string) => {
    setLoadingDetail(true);
    setSelectedDebate(null);
    try {
      const res = await fetch(`${API_BASE}/api/debate/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedDebate(data);
      } else {
        showError('بارگذاری جزئیات ناموفق بود');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setLoadingDetail(false);
    }
  };

  const deleteFile = async (id: string, name: string) => {
    if (!confirm(`فایل «${name}» حذف شود؟`)) return;

    try {
      const res = await fetch(`${API_BASE}/api/upload/file/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('فایل حذف شد');
        setFiles((prev) => prev.filter((f) => f.id !== id));
      } else {
        showError('خطا در حذف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const deleteProject = async (id: string, name: string) => {
    if (!confirm(`پروژه «${name}» حذف شود؟ این عمل قابل بازگشت نیست.`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('پروژه حذف شد');
        setProjects((prev) => prev.filter((p) => p.id !== id));
      } else {
        showError('خطا در حذف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const exportDebate = (d: DebateDetail) => {
    const data = JSON.stringify(d, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debate-${d.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showSuccess('فایل دانلود شد');
  };

  const formatSize = (bytes: number) => {
    if (!bytes) return '۰ B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (date?: string) => {
    if (!date) return '';
    try {
      return new Date(date).toLocaleString('fa-IR');
    } catch (e) {
      return date;
    }
  };

  const fileIcon = (mime?: string, name?: string) => {
    if (!mime && name) {
      const ext = name.split('.').pop()?.toLowerCase();
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext || '')) return '🖼️';
      if (['pdf'].includes(ext || '')) return '📕';
      if (['doc', 'docx'].includes(ext || '')) return '📘';
      if (['xls', 'xlsx', 'csv'].includes(ext || '')) return '📊';
      if (['mp3', 'wav', 'ogg'].includes(ext || '')) return '🎵';
      if (['mp4', 'avi', 'mkv'].includes(ext || '')) return '🎬';
      if (['zip', 'tar', 'gz', 'rar'].includes(ext || '')) return '🗜️';
      if (['js', 'ts', 'py', 'json', 'md', 'html', 'css'].includes(ext || ''))
        return '📜';
    }
    if (mime?.startsWith('image/')) return '🖼️';
    if (mime?.startsWith('video/')) return '🎬';
    if (mime?.startsWith('audio/')) return '🎵';
    if (mime?.startsWith('text/')) return '📜';
    if (mime?.includes('pdf')) return '📕';
    if (mime?.includes('zip') || mime?.includes('compress')) return '🗜️';
    return '📄';
  };

  // فیلترها
  const filteredDebates = useMemo(() => {
    let list = debates.filter((d) => {
      if (search && !d.prompt?.toLowerCase().includes(search.toLowerCase())) return false;
      if (statusFilter !== 'all' && d.status !== statusFilter) return false;
      return true;
    });

    list.sort((a, b) => {
      if (sortBy === 'newest')
        return (b.created_at || '').localeCompare(a.created_at || '');
      if (sortBy === 'oldest')
        return (a.created_at || '').localeCompare(b.created_at || '');
      return (a.prompt || '').localeCompare(b.prompt || '');
    });

    return list;
  }, [debates, search, statusFilter, sortBy]);

  const filteredFiles = useMemo(() => {
    let list = files.filter((f) => {
      if (search && !f.original_name?.toLowerCase().includes(search.toLowerCase()))
        return false;
      if (categoryFilter !== 'all' && f.category !== categoryFilter) return false;
      return true;
    });

    list.sort((a, b) => {
      if (sortBy === 'newest')
        return (b.created_at || '').localeCompare(a.created_at || '');
      if (sortBy === 'oldest')
        return (a.created_at || '').localeCompare(b.created_at || '');
      return (a.original_name || '').localeCompare(b.original_name || '');
    });

    return list;
  }, [files, search, categoryFilter, sortBy]);

  const filteredProjects = useMemo(() => {
    let list = projects.filter(
      (p) =>
        !search ||
        p.name?.toLowerCase().includes(search.toLowerCase()) ||
        p.description?.toLowerCase().includes(search.toLowerCase()),
    );

    list.sort((a, b) => {
      if (sortBy === 'newest')
        return (b.created_at || '').localeCompare(a.created_at || '');
      if (sortBy === 'oldest')
        return (a.created_at || '').localeCompare(b.created_at || '');
      return (a.name || '').localeCompare(b.name || '');
    });

    return list;
  }, [projects, search, sortBy]);

  const debateStatuses = useMemo(() => {
    const set = new Set<string>();
    debates.forEach((d) => d.status && set.add(d.status));
    return Array.from(set);
  }, [debates]);

  const fileCategories = useMemo(() => {
    const set = new Set<string>();
    files.forEach((f) => f.category && set.add(f.category));
    return Array.from(set);
  }, [files]);

  const totalFileSize = useMemo(
    () => files.reduce((sum, f) => sum + (f.size || 0), 0),
    [files],
  );

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900" dir="rtl">
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-md">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-md">
          {success}
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
              📚 آرشیو
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              تاریخچه مناظرات، فایل‌ها و پروژه‌ها
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadData}
              className="px-4 py-2 bg-white dark:bg-gray-800 dark:text-white border dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              🔄 بروزرسانی
            </button>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              🏠 خانه
            </Link>
          </div>
        </div>

        {/* آمار */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 text-center">
            <div className="text-2xl mb-1">🥊</div>
            <div className="text-2xl font-bold dark:text-white">{debates.length}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">مناظره</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 text-center">
            <div className="text-2xl mb-1">📁</div>
            <div className="text-2xl font-bold dark:text-white">{files.length}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              فایل ({formatSize(totalFileSize)})
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 text-center">
            <div className="text-2xl mb-1">🛠️</div>
            <div className="text-2xl font-bold dark:text-white">{projects.length}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">پروژه</div>
          </div>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {(
            [
              { id: 'debates', label: 'مناظرات', icon: '🥊', count: debates.length },
              { id: 'files', label: 'فایل‌ها', icon: '📁', count: files.length },
              { id: 'projects', label: 'پروژه‌ها', icon: '🛠️', count: projects.length },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
                tab === t.id
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'bg-white dark:bg-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  tab === t.id ? 'bg-white/20' : 'bg-gray-200 dark:bg-gray-700'
                }`}
              >
                {t.count}
              </span>
            </button>
          ))}
        </div>

        {/* فیلترها */}
        <div className="flex gap-2 mb-4 flex-wrap">
          <input
            type="text"
            placeholder="🔍 جستجو..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 min-w-[200px] p-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700 dark:text-white"
          />

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="p-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700 dark:text-white"
          >
            <option value="newest">📅 جدیدترین</option>
            <option value="oldest">📅 قدیمی‌ترین</option>
            <option value="name">🔤 الفبایی</option>
          </select>

          {tab === 'debates' && debateStatuses.length > 0 && (
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="p-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">همه وضعیت‌ها</option>
              {debateStatuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          )}

          {tab === 'files' && fileCategories.length > 0 && (
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="p-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            >
              <option value="all">همه دسته‌ها</option>
              {fileCategories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* محتوا */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div>
              <p className="text-gray-400">در حال بارگذاری...</p>
            </div>
          ) : tab === 'debates' ? (
            filteredDebates.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-3">📭</div>
                <p>{debates.length === 0 ? 'هنوز مناظره‌ای وجود ندارد' : 'نتیجه‌ای پیدا نشد'}</p>
                {debates.length === 0 && (
                  <Link
                    href="/debate"
                    className="inline-block mt-3 text-blue-500 hover:underline"
                  >
                    شروع مناظره جدید ←
                  </Link>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredDebates.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setSelectedDebateId(d.id)}
                    className="w-full text-right p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition border border-transparent hover:border-blue-300 dark:hover:border-blue-700"
                  >
                    <div className="font-medium text-sm dark:text-white line-clamp-2">
                      {d.prompt}
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                      <span
                        className={`px-2 py-0.5 rounded ${
                          d.status === 'completed' || d.status === 'finished'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                            : d.status === 'failed' || d.status === 'error'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                            : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                        }`}
                      >
                        {d.status}
                      </span>
                      <span>📌 {d.mode}</span>
                      {d.rounds_count !== undefined && d.rounds_count > 0 && (
                        <span>🔁 {d.rounds_count} راند</span>
                      )}
                      {d.has_judge && <span>⚖️ داوری</span>}
                      {d.has_summary && <span>📝 خلاصه</span>}
                      {d.created_at && <span className="mr-auto">{formatDate(d.created_at)}</span>}
                    </div>
                  </button>
                ))}
              </div>
            )
          ) : tab === 'files' ? (
            filteredFiles.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-3">📭</div>
                <p>{files.length === 0 ? 'فایلی آپلود نشده' : 'نتیجه‌ای پیدا نشد'}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredFiles.map((f) => (
                  <div
                    key={f.id}
                    className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg flex items-center gap-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                  >
                    <div className="text-3xl">{fileIcon(f.mime_type, f.original_name)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm dark:text-white truncate">
                        {f.original_name}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                        <span>{formatSize(f.size)}</span>
                        {f.mime_type && <span>• {f.mime_type}</span>}
                        {f.category && (
                          <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded">
                            {f.category}
                          </span>
                        )}
                        {f.created_at && <span>• {formatDate(f.created_at)}</span>}
                      </div>
                      {f.tags && f.tags.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {f.tags.map((t) => (
                            <span
                              key={t}
                              className="text-xs px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded"
                            >
                              #{t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <a
                        href={`${API_BASE}/api/upload/file/${f.id}`}
                        download={f.original_name}
                        className="px-3 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded text-sm hover:bg-blue-200 dark:hover:bg-blue-900/60"
                      >
                        ↓ دانلود
                      </a>
                      <button
                        onClick={() => deleteFile(f.id, f.original_name)}
                        className="px-3 py-1 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300 rounded text-sm hover:bg-red-200 dark:hover:bg-red-900/60"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            // پروژه‌ها
            filteredProjects.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-3">📭</div>
                <p>{projects.length === 0 ? 'پروژه‌ای ساخته نشده' : 'نتیجه‌ای پیدا نشد'}</p>
                {projects.length === 0 && (
                  <Link
                    href="/creator"
                    className="inline-block mt-3 text-blue-500 hover:underline"
                  >
                    ساخت پروژه جدید ←
                  </Link>
                )}
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {filteredProjects.map((p) => (
                  <div
                    key={p.id}
                    className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition border border-transparent hover:border-blue-300 dark:hover:border-blue-700 group"
                  >
                    <Link href={`/project/${p.id}`} className="block">
                      <div className="font-medium dark:text-white truncate">{p.name}</div>
                      {p.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">
                          {p.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                        <span className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded">
                          {p.project_type}
                        </span>
                        {p.status && <span>📌 {p.status}</span>}
                        {p.files && p.files.length > 0 && (
                          <span className="text-green-600 dark:text-green-400">
                            📄 {p.files.length} فایل
                          </span>
                        )}
                      </div>
                    </Link>
                    <button
                      onClick={() => deleteProject(p.id, p.name)}
                      className="opacity-0 group-hover:opacity-100 mt-2 text-xs text-red-500 hover:text-red-600 transition"
                    >
                      🗑️ حذف پروژه
                    </button>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>

      {/* مودال جزئیات مناظره */}
      {selectedDebateId && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
          onClick={() => {
            setSelectedDebateId(null);
            setSelectedDebate(null);
          }}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
              <h2 className="text-lg font-bold dark:text-white">📋 جزئیات مناظره</h2>
              <div className="flex gap-2">
                {selectedDebate && (
                  <button
                    onClick={() => exportDebate(selectedDebate)}
                    className="px-3 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded text-sm hover:bg-blue-200"
                  >
                    ↓ JSON
                  </button>
                )}
                <button
                  onClick={() => {
                    setSelectedDebateId(null);
                    setSelectedDebate(null);
                  }}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none px-2"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="overflow-auto p-4 flex-1">
              {loadingDetail ? (
                <div className="text-center py-12">
                  <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                  <p className="text-gray-400">در حال بارگذاری...</p>
                </div>
              ) : !selectedDebate ? (
                <p className="text-center text-gray-400 py-8">جزئیات یافت نشد</p>
              ) : (
                <>
                  {/* سوال */}
                  <div className="mb-4">
                    <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                      سوال
                    </h3>
                    <p className="dark:text-gray-200 whitespace-pre-wrap p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      {selectedDebate.prompt}
                    </p>
                  </div>

                  {/* اطلاعات کلی */}
                  <div className="flex flex-wrap gap-2 mb-4 text-xs">
                    <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded">
                      حالت: {selectedDebate.mode}
                    </span>
                    <span className="px-2 py-1 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded">
                      وضعیت: {selectedDebate.status}
                    </span>
                    {selectedDebate.models && selectedDebate.models.length > 0 && (
                      <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded">
                        🤖 {selectedDebate.models.length} مدل
                      </span>
                    )}
                  </div>

                  {/* خلاصه */}
                  {selectedDebate.summary && (
                    <div className="mb-4">
                      <h3 className="text-sm font-medium mb-2 dark:text-gray-200">📝 خلاصه</h3>
                      <p className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg whitespace-pre-wrap text-sm dark:text-blue-100 border border-blue-200 dark:border-blue-800">
                        {selectedDebate.summary}
                      </p>
                    </div>
                  )}

                  {/* داوری */}
                  {selectedDebate.judge_result && selectedDebate.judge_result.winner && (
                    <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                      <h3 className="font-medium mb-1 dark:text-yellow-200">⚖️ نتیجه داوری</h3>
                      <p className="text-sm dark:text-yellow-100">
                        <strong>برنده:</strong> {selectedDebate.judge_result.winner}
                      </p>
                      {selectedDebate.judge_result.reasoning && (
                        <p className="text-xs mt-2 dark:text-yellow-200/80 whitespace-pre-wrap">
                          {selectedDebate.judge_result.reasoning}
                        </p>
                      )}
                    </div>
                  )}

                  {/* راندها */}
                  {selectedDebate.rounds && selectedDebate.rounds.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium dark:text-gray-200">💬 پاسخ‌ها</h3>
                      {selectedDebate.rounds.map((round, i) => (
                        <div key={i} className="border-r-4 border-blue-500 pr-3">
                          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                            راند {i + 1}
                          </h4>
                          <div className="space-y-2">
                            {round?.map((resp: any, j: number) => (
                              <div
                                key={j}
                                className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                              >
                                <div className="flex items-center gap-2 mb-2 flex-wrap">
                                  <span className="font-medium text-sm dark:text-white">
                                    🤖 {resp.model}
                                  </span>
                                  {resp.role && (
                                    <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded">
                                      {resp.role}
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm whitespace-pre-wrap dark:text-gray-200 leading-relaxed">
                                  {resp.content}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
