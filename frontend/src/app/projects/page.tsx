'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function ProjectsContent() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('id');

  const [projects, setProjects] = useState<any[]>([]);
  const [githubProjects, setGithubProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'github'>('all');

  // پروژه انتخابی
  const [selected, setSelected] = useState<any>(null);

  // فرم ساخت
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  // GitHub Import
  const [showGitHubImport, setShowGitHubImport] = useState(false);
  const [githubUrl, setGithubUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState('');
  const [repoInfo, setRepoInfo] = useState<any>(null);
  const [checkingRepo, setCheckingRepo] = useState(false);

  useEffect(() => {
    loadProjects();
    loadGitHubProjects();
  }, []);

  // وقتی پروژه‌ها لود شدن و id داریم، پروژه رو انتخاب کن
  useEffect(() => {
    if (projectId && projects.length > 0 && !selected) {
      const found = projects.find((p) => p.id === projectId);
      if (found) {
        setSelected(found);
      }
    }
  }, [projectId, projects]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const loadProjects = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch (e) {
      showError('خطا در بارگذاری');
    } finally {
      setLoading(false);
    }
  };

  const loadGitHubProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/github/imported`);
      if (res.ok) {
        const data = await res.json();
        setGithubProjects(data.projects || []);
      }
    } catch (e) {
      console.error('Error loading GitHub projects:', e);
    }
  };

  const createProject = async () => {
    if (!newName.trim()) {
      showError('نام پروژه را وارد کنید');
      return;
    }

    setCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName, description: newDesc }),
      });

      if (res.ok) {
        showSuccess('پروژه ساخته شد');
        setNewName('');
        setNewDesc('');
        setShowCreate(false);
        loadProjects();
      } else {
        showError('خطا در ساخت');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setCreating(false);
    }
  };

  const deleteProject = async (id: string, isGithub = false) => {
    if (!confirm('حذف شود؟')) return;

    try {
      const endpoint = isGithub
        ? `${API_BASE}/api/github/imported/${id}`
        : `${API_BASE}/api/projects/${id}`;

      const res = await fetch(endpoint, { method: 'DELETE' });
      if (res.ok) {
        showSuccess('حذف شد');
        if (selected?.id === id) setSelected(null);
        if (isGithub) {
          loadGitHubProjects();
        } else {
          loadProjects();
        }
      }
    } catch (e) {
      showError('خطا');
    }
  };

  // بررسی دسترسی به repo
  const checkRepository = async () => {
    if (!githubUrl.trim()) {
      showError('آدرس GitHub را وارد کنید');
      return;
    }

    setCheckingRepo(true);
    setRepoInfo(null);

    try {
      const res = await fetch(`${API_BASE}/api/github/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: githubUrl,
          token: githubToken || undefined,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setRepoInfo(data);
        showSuccess('دسترسی تایید شد');
      } else {
        showError(data.error || 'خطا در بررسی');
        if (data.hint) {
          setImportProgress(data.hint);
        }
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setCheckingRepo(false);
    }
  };

  // Import کردن repository
  const importRepository = async () => {
    if (!githubUrl.trim()) {
      showError('آدرس GitHub را وارد کنید');
      return;
    }

    setImporting(true);
    setImportProgress('در حال دریافت اطلاعات...');

    try {
      const res = await fetch(`${API_BASE}/api/github/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: githubUrl,
          token: githubToken || undefined,
          include_files: true,
        }),
      });

      const data = await res.json();

      if (data.success) {
        showSuccess(`پروژه "${data.name}" با موفقیت import شد`);
        setShowGitHubImport(false);
        setGithubUrl('');
        setGithubToken('');
        setRepoInfo(null);
        loadGitHubProjects();
        setActiveTab('github');
      } else {
        showError(data.error || 'خطا در import');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setImporting(false);
      setImportProgress('');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-700';
      case 'in_progress': return 'bg-blue-100 text-blue-700';
      case 'pending': return 'bg-yellow-100 text-yellow-700';
      case 'imported': return 'bg-purple-100 text-purple-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'تکمیل شده';
      case 'in_progress': return 'در حال انجام';
      case 'pending': return 'در انتظار';
      case 'imported': return 'از GitHub';
      default: return status || 'نامشخص';
    }
  };

  // ترکیب پروژه‌ها بر اساس تب
  const displayProjects = activeTab === 'github' ? githubProjects : [...projects, ...githubProjects];

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900" dir="rtl">
      {/* پیام‌ها */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {success}
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">پروژه‌ها</h1>
            <p className="text-gray-500 text-sm">مدیریت پروژه‌های شما</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowGitHubImport(true)}
              className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              Import از GitHub
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              + پروژه جدید
            </button>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
            >
              خانه
            </Link>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* لیست پروژه‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              {/* تب‌ها */}
              <div className="flex border-b mb-4">
                <button
                  onClick={() => setActiveTab('all')}
                  className={`flex-1 py-2 text-sm font-medium ${
                    activeTab === 'all'
                      ? 'border-b-2 border-blue-500 text-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  همه ({projects.length + githubProjects.length})
                </button>
                <button
                  onClick={() => setActiveTab('github')}
                  className={`flex-1 py-2 text-sm font-medium flex items-center justify-center gap-1 ${
                    activeTab === 'github'
                      ? 'border-b-2 border-purple-500 text-purple-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                  </svg>
                  GitHub ({githubProjects.length})
                </button>
              </div>

              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">لیست</h2>
                <button
                  onClick={() => { loadProjects(); loadGitHubProjects(); }}
                  className="text-blue-500 text-sm"
                >
                  بروزرسانی
                </button>
              </div>

              {loading ? (
                <p className="text-gray-400 text-center py-4">در حال بارگذاری...</p>
              ) : displayProjects.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-4xl mb-2">📭</div>
                  <p className="text-gray-400">پروژه‌ای نیست</p>
                  {activeTab === 'github' && (
                    <button
                      onClick={() => setShowGitHubImport(true)}
                      className="mt-4 text-sm text-purple-500 hover:underline"
                    >
                      Import از GitHub
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-2 max-h-[60vh] overflow-auto">
                  {displayProjects.map((p) => {
                    const isGithubProject = p.project_type === 'github_import' || p.metadata?.source === 'github';
                    return (
                      <div
                        key={p.id}
                        onClick={() => setSelected({ ...p, isGithub: isGithubProject })}
                        className={`p-3 rounded-lg cursor-pointer transition ${
                          selected?.id === p.id
                            ? 'bg-blue-50 dark:bg-blue-900/30 border-2 border-blue-500'
                            : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {isGithubProject && (
                            <svg className="w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                            </svg>
                          )}
                          <span className="font-medium truncate">{p.name}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(p.status)}`}>
                            {getStatusText(p.status)}
                          </span>
                          {p.metadata?.private && (
                            <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">
                              🔒 Private
                            </span>
                          )}
                          {p.progress !== undefined && (
                            <span className="text-xs text-gray-500">{p.progress}%</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* جزئیات پروژه */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              {!selected ? (
                <div className="text-center text-gray-400 py-12">
                  <div className="text-5xl mb-4">📁</div>
                  <p>یک پروژه انتخاب کنید</p>
                </div>
              ) : (
                <div>
                  <div className="flex items-start justify-between mb-6">
                    <div>
                      <div className="flex items-center gap-2">
                        {selected.isGithub && (
                          <svg className="w-6 h-6 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                          </svg>
                        )}
                        <h2 className="text-xl font-bold">{selected.name}</h2>
                      </div>
                      {selected.description && (
                        <p className="text-gray-500 mt-1">{selected.description}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {selected.isGithub && selected.metadata?.source_url && (
                        <a
                          href={selected.metadata.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900"
                        >
                          مشاهده در GitHub
                        </a>
                      )}
                      <Link
                        href={`/projects/${selected.id}`}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                      >
                        📂 باز کردن
                      </Link>
                      <button
                        onClick={() => deleteProject(selected.id, selected.isGithub)}
                        className="px-3 py-1 bg-red-100 text-red-600 rounded text-sm hover:bg-red-200"
                      >
                        حذف
                      </button>
                    </div>
                  </div>

                  {/* اطلاعات */}
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">وضعیت</div>
                      <div className={`inline-block px-3 py-1 rounded text-sm ${getStatusColor(selected.status)}`}>
                        {getStatusText(selected.status)}
                      </div>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">
                        {selected.isGithub ? 'ستاره‌ها' : 'پیشرفت'}
                      </div>
                      <div className="text-2xl font-bold">
                        {selected.isGithub
                          ? `⭐ ${selected.metadata?.stats?.stars || 0}`
                          : `${selected.progress || 0}%`
                        }
                      </div>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">
                        {selected.isGithub ? 'زبان اصلی' : 'نوع'}
                      </div>
                      <div>
                        {selected.isGithub
                          ? selected.metadata?.primary_language || 'نامشخص'
                          : selected.type || 'نامشخص'
                        }
                      </div>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">شناسه</div>
                      <div className="text-xs font-mono truncate">{selected.id}</div>
                    </div>
                  </div>

                  {/* GitHub Info */}
                  {selected.isGithub && selected.metadata && (
                    <div className="mb-6">
                      <h3 className="font-bold mb-3">اطلاعات GitHub</h3>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                          <div className="text-xl">⭐</div>
                          <div className="font-bold">{selected.metadata.stats?.stars || 0}</div>
                          <div className="text-gray-500 text-xs">Stars</div>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                          <div className="text-xl">🍴</div>
                          <div className="font-bold">{selected.metadata.stats?.forks || 0}</div>
                          <div className="text-gray-500 text-xs">Forks</div>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                          <div className="text-xl">📁</div>
                          <div className="font-bold">{selected.metadata.stats?.file_count || 0}</div>
                          <div className="text-gray-500 text-xs">Files</div>
                        </div>
                      </div>

                      {/* زبان‌ها */}
                      {selected.technologies && selected.technologies.length > 0 && (
                        <div className="mt-4">
                          <div className="text-sm text-gray-500 mb-2">زبان‌ها:</div>
                          <div className="flex flex-wrap gap-2">
                            {selected.technologies.map((lang: string) => (
                              <span
                                key={lang}
                                className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs"
                              >
                                {lang}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* پیشرفت بصری (برای پروژه‌های عادی) */}
                  {!selected.isGithub && selected.progress !== undefined && (
                    <div className="mb-6">
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all"
                          style={{ width: `${selected.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* مودال ساخت پروژه */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-4">پروژه جدید</h2>

            <input
              type="text"
              placeholder="نام پروژه"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full p-3 border rounded-lg mb-3 dark:bg-gray-700 dark:border-gray-600"
            />

            <textarea
              placeholder="توضیحات"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              rows={3}
              className="w-full p-3 border rounded-lg mb-4 dark:bg-gray-700 dark:border-gray-600"
            />

            <div className="flex gap-2">
              <button
                onClick={createProject}
                disabled={creating}
                className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {creating ? 'صبر کنید...' : 'ساخت'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg"
              >
                لغو
              </button>
            </div>
          </div>
        </div>
      )}

      {/* مودال Import از GitHub */}
      {showGitHubImport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-lg">
            <div className="flex items-center gap-3 mb-6">
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              <div>
                <h2 className="text-lg font-bold">Import از GitHub</h2>
                <p className="text-sm text-gray-500">پروژه‌های public و private</p>
              </div>
            </div>

            {/* URL Input */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">آدرس Repository</label>
              <input
                type="text"
                placeholder="https://github.com/owner/repo یا owner/repo"
                value={githubUrl}
                onChange={(e) => { setGithubUrl(e.target.value); setRepoInfo(null); }}
                className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                dir="ltr"
              />
            </div>

            {/* Token Input */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">
                توکن GitHub
                <span className="text-gray-400 font-normal mr-2">(برای repo های private)</span>
              </label>
              <input
                type="password"
                placeholder="ghp_xxxxxxxxxxxx"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                dir="ltr"
              />
              <p className="text-xs text-gray-400 mt-1">
                از Settings → Developer settings → Personal access tokens بسازید
              </p>
            </div>

            {/* نتیجه بررسی */}
            {repoInfo && repoInfo.success && (
              <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-3">
                  <div className="text-2xl">✅</div>
                  <div>
                    <div className="font-bold">{repoInfo.repo_info?.name}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {repoInfo.repo_info?.description || 'بدون توضیحات'}
                    </div>
                    <div className="flex gap-4 mt-2 text-xs">
                      <span>⭐ {repoInfo.repo_info?.stargazers_count || 0}</span>
                      <span>🍴 {repoInfo.repo_info?.forks_count || 0}</span>
                      <span>📝 {repoInfo.repo_info?.language || 'Unknown'}</span>
                      {repoInfo.repo_info?.private && (
                        <span className="text-yellow-600">🔒 Private</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* پیام خطا یا راهنما */}
            {importProgress && (
              <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-700 dark:text-blue-300">
                {importProgress}
              </div>
            )}

            {/* دکمه‌ها */}
            <div className="flex gap-2">
              {!repoInfo?.success ? (
                <button
                  onClick={checkRepository}
                  disabled={checkingRepo || !githubUrl.trim()}
                  className="flex-1 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-50"
                >
                  {checkingRepo ? 'در حال بررسی...' : 'بررسی دسترسی'}
                </button>
              ) : (
                <button
                  onClick={importRepository}
                  disabled={importing}
                  className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                >
                  {importing ? 'در حال Import...' : 'Import پروژه'}
                </button>
              )}
              <button
                onClick={() => {
                  setShowGitHubImport(false);
                  setGithubUrl('');
                  setGithubToken('');
                  setRepoInfo(null);
                  setImportProgress('');
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg"
              >
                لغو
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Wrapper با Suspense برای useSearchParams
export default function ProjectsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center" dir="rtl"><p>در حال بارگذاری...</p></div>}>
      <ProjectsContent />
    </Suspense>
  );
}
