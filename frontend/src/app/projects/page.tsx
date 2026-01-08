'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function ProjectsContent() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('id');

  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // پروژه انتخابی
  const [selected, setSelected] = useState<any>(null);

  // فرم ساخت
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProjects();
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

  const deleteProject = async (id: string) => {
    if (!confirm('حذف شود؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('حذف شد');
        if (selected?.id === id) setSelected(null);
        loadProjects();
      }
    } catch (e) {
      showError('خطا');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-700';
      case 'in_progress': return 'bg-blue-100 text-blue-700';
      case 'pending': return 'bg-yellow-100 text-yellow-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'تکمیل شده';
      case 'in_progress': return 'در حال انجام';
      case 'pending': return 'در انتظار';
      default: return status || 'نامشخص';
    }
  };

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
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">لیست ({projects.length})</h2>
                <button onClick={loadProjects} className="text-blue-500 text-sm">
                  بروزرسانی
                </button>
              </div>

              {loading ? (
                <p className="text-gray-400 text-center py-4">در حال بارگذاری...</p>
              ) : projects.length === 0 ? (
                <p className="text-gray-400 text-center py-4">پروژه‌ای نیست</p>
              ) : (
                <div className="space-y-2 max-h-[60vh] overflow-auto">
                  {projects.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => setSelected(p)}
                      className={`p-3 rounded-lg cursor-pointer transition ${
                        selected?.id === p.id
                          ? 'bg-blue-50 dark:bg-blue-900/30 border-2 border-blue-500'
                          : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="font-medium truncate">{p.name}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(p.status)}`}>
                          {getStatusText(p.status)}
                        </span>
                        {p.progress !== undefined && (
                          <span className="text-xs text-gray-500">{p.progress}%</span>
                        )}
                      </div>
                    </div>
                  ))}
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
                      <h2 className="text-xl font-bold">{selected.name}</h2>
                      {selected.description && (
                        <p className="text-gray-500 mt-1">{selected.description}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Link
                        href={`/projects/${selected.id}`}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                      >
                        📂 باز کردن
                      </Link>
                      <button
                        onClick={() => deleteProject(selected.id)}
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
                      <div className="text-sm text-gray-500 mb-1">پیشرفت</div>
                      <div className="text-2xl font-bold">{selected.progress || 0}%</div>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">نوع</div>
                      <div>{selected.type || 'نامشخص'}</div>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">شناسه</div>
                      <div className="text-xs font-mono truncate">{selected.id}</div>
                    </div>
                  </div>

                  {/* پیشرفت بصری */}
                  {selected.progress !== undefined && (
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

      {/* مودال ساخت */}
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
