'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CreatorPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // فرم ساخت پروژه
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');

  // بارگذاری پروژه‌ها
  useEffect(() => {
    loadProjects();
  }, []);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const loadProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const createProject = async () => {
    if (!projectName.trim()) {
      showError('نام پروژه را وارد کنید');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName,
          description: projectDesc || projectName,
        }),
      });

      if (res.ok) {
        showSuccess('پروژه ساخته شد ✓');
        setProjectName('');
        setProjectDesc('');
        loadProjects();
      } else {
        showError('خطا در ساخت پروژه');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm('حذف شود؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('حذف شد ✓');
        loadProjects();
      }
    } catch (e) {
      showError('خطا');
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

      <div className="max-w-4xl mx-auto p-6">
        {/* عنوان */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">موتور خالق</h1>
          <p className="text-gray-500">پروژه‌هاتو اینجا مدیریت کن</p>
        </div>

        {/* ساخت پروژه */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 mb-6 shadow">
          <h2 className="text-lg font-bold mb-4">پروژه جدید</h2>

          <input
            type="text"
            placeholder="نام پروژه"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full p-3 border rounded-lg mb-3 dark:bg-gray-700 dark:border-gray-600"
          />

          <textarea
            placeholder="توضیحات (اختیاری)"
            value={projectDesc}
            onChange={(e) => setProjectDesc(e.target.value)}
            rows={2}
            className="w-full p-3 border rounded-lg mb-3 dark:bg-gray-700 dark:border-gray-600"
          />

          <button
            onClick={createProject}
            disabled={loading}
            className="w-full py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'صبر کنید...' : 'ساخت پروژه'}
          </button>
        </div>

        {/* لیست پروژه‌ها */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold">پروژه‌ها ({projects.length})</h2>
            <button
              onClick={loadProjects}
              className="text-blue-500 hover:underline text-sm"
            >
              بروزرسانی
            </button>
          </div>

          {projects.length === 0 ? (
            <p className="text-center text-gray-400 py-8">پروژه‌ای نیست</p>
          ) : (
            <div className="space-y-3">
              {projects.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div>
                    <div className="font-bold">{p.name}</div>
                    {p.description && (
                      <div className="text-sm text-gray-500">{p.description}</div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <a
                      href={`/projects?id=${p.id}`}
                      className="px-3 py-1 bg-gray-200 dark:bg-gray-600 rounded text-sm hover:bg-gray-300"
                    >
                      مشاهده
                    </a>
                    <button
                      onClick={() => deleteProject(p.id)}
                      className="px-3 py-1 bg-red-100 text-red-600 rounded text-sm hover:bg-red-200"
                    >
                      حذف
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* لینک‌های مفید */}
        <div className="mt-6 flex justify-center gap-4 text-sm">
          <a href="/projects" className="text-blue-500 hover:underline">
            صفحه پروژه‌ها
          </a>
          <a href="/settings" className="text-blue-500 hover:underline">
            تنظیمات
          </a>
        </div>
      </div>
    </div>
  );
}
