'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ArchivePage() {
  const [tab, setTab] = useState<'debates' | 'files'>('debates');
  const [debates, setDebates] = useState<any[]>([]);
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // جستجو
  const [search, setSearch] = useState('');

  // مناظره انتخابی
  const [selectedDebate, setSelectedDebate] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // مناظرات
      const debatesRes = await fetch(`${API_BASE}/api/debate/`);
      if (debatesRes.ok) {
        const data = await debatesRes.json();
        setDebates(Array.isArray(data) ? data : []);
      }

      // فایل‌ها
      const filesRes = await fetch(`${API_BASE}/api/upload/files`);
      if (filesRes.ok) {
        const data = await filesRes.json();
        setFiles(data.files || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (id: string) => {
    if (!confirm('حذف شود؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/upload/file/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('حذف شد');
        loadData();
      }
    } catch (e) {
      showError('خطا');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const filteredDebates = debates.filter(
    (d) => !search || d.prompt?.toLowerCase().includes(search.toLowerCase())
  );

  const filteredFiles = files.filter(
    (f) => !search || f.name?.toLowerCase().includes(search.toLowerCase())
  );

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

      <div className="max-w-5xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">آرشیو</h1>
            <p className="text-gray-500 text-sm">تاریخچه مناظرات و فایل‌ها</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
          >
            خانه
          </Link>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setTab('debates')}
            className={`px-4 py-2 rounded-lg ${
              tab === 'debates'
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            مناظرات ({debates.length})
          </button>
          <button
            onClick={() => setTab('files')}
            className={`px-4 py-2 rounded-lg ${
              tab === 'files'
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            فایل‌ها ({files.length})
          </button>
        </div>

        {/* جستجو */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="جستجو..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full p-3 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
          />
        </div>

        {/* محتوا */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
          {loading ? (
            <p className="text-gray-400 text-center py-8">در حال بارگذاری...</p>
          ) : tab === 'debates' ? (
            // لیست مناظرات
            filteredDebates.length === 0 ? (
              <p className="text-gray-400 text-center py-8">مناظره‌ای نیست</p>
            ) : (
              <div className="space-y-3">
                {filteredDebates.map((d) => (
                  <div
                    key={d.id}
                    onClick={() => setSelectedDebate(d)}
                    className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-100"
                  >
                    <div className="font-medium truncate">{d.prompt}</div>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <span className={`px-2 py-0.5 rounded ${
                        d.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {d.status}
                      </span>
                      <span>{d.mode}</span>
                      {d.models?.length > 0 && (
                        <span>{d.models.length} مدل</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            // لیست فایل‌ها
            filteredFiles.length === 0 ? (
              <p className="text-gray-400 text-center py-8">فایلی نیست</p>
            ) : (
              <div className="space-y-3">
                {filteredFiles.map((f) => (
                  <div
                    key={f.id}
                    className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium">{f.name}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {formatSize(f.size)} • {f.type || 'نامشخص'}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <a
                        href={`${API_BASE}/api/upload/file/${f.id}`}
                        download
                        className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200"
                      >
                        دانلود
                      </a>
                      <button
                        onClick={() => deleteFile(f.id)}
                        className="px-3 py-1 bg-red-100 text-red-600 rounded text-sm hover:bg-red-200"
                      >
                        حذف
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>

      {/* مودال جزئیات مناظره */}
      {selectedDebate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">جزئیات مناظره</h2>
              <button
                onClick={() => setSelectedDebate(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>

            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-500 mb-1">سوال</h3>
              <p>{selectedDebate.prompt}</p>
            </div>

            {selectedDebate.summary && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-1">خلاصه</h3>
                <p className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  {selectedDebate.summary}
                </p>
              </div>
            )}

            {selectedDebate.rounds?.map((round: any, i: number) => (
              <div key={i} className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  راند {round.round_number || i + 1}
                </h3>
                <div className="space-y-2">
                  {round.responses?.map((resp: any, j: number) => (
                    <div key={j} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="font-medium text-sm mb-1">{resp.model}</div>
                      <p className="text-sm whitespace-pre-wrap">{resp.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {selectedDebate.judge_result && (
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <h3 className="font-medium text-sm mb-1">نتیجه داوری</h3>
                <p>برنده: {selectedDebate.judge_result.winner}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
