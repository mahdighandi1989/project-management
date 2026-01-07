'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DebatePage() {
  const [debates, setDebates] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [workModes, setWorkModes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // فرم مناظره جدید
  const [prompt, setPrompt] = useState('');
  const [selectedMode, setSelectedMode] = useState('auto');
  const [running, setRunning] = useState(false);

  // مناظره فعال
  const [activeDebate, setActiveDebate] = useState<any>(null);

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
      // مدل‌ها
      const modelsRes = await fetch(`${API_BASE}/api/models/available`);
      if (modelsRes.ok) {
        const data = await modelsRes.json();
        setModels(data || []);
      }

      // حالت‌های کار
      const modesRes = await fetch(`${API_BASE}/api/settings/work-modes`);
      if (modesRes.ok) {
        const data = await modesRes.json();
        setWorkModes(data || []);
      }

      // مناظرات اخیر
      const debatesRes = await fetch(`${API_BASE}/api/debate/`);
      if (debatesRes.ok) {
        const data = await debatesRes.json();
        setDebates(Array.isArray(data) ? data.slice(0, 5) : []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const startDebate = async () => {
    if (!prompt.trim()) {
      showError('سوال را وارد کنید');
      return;
    }

    if (models.length === 0) {
      showError('مدلی فعال نیست');
      return;
    }

    setRunning(true);
    setActiveDebate(null);

    try {
      // ساخت مناظره
      const createRes = await fetch(`${API_BASE}/api/debate/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          mode: selectedMode,
        }),
      });

      if (!createRes.ok) {
        showError('خطا در ساخت مناظره');
        setRunning(false);
        return;
      }

      const createData = await createRes.json();
      const debateId = createData.debate?.id || createData.id;

      if (!debateId) {
        showError('شناسه مناظره یافت نشد');
        setRunning(false);
        return;
      }

      showSuccess('مناظره شروع شد...');

      // اجرای کامل
      const runRes = await fetch(`${API_BASE}/api/debate/${debateId}/run-full`, {
        method: 'POST',
      });

      if (runRes.ok) {
        const result = await runRes.json();
        setActiveDebate(result.debate || result);
        showSuccess('مناظره تمام شد');
        setPrompt('');
      } else {
        showError('خطا در اجرای مناظره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setRunning(false);
    }
  };

  const getModeLabel = (mode: string) => {
    const labels: Record<string, string> = {
      auto: 'خودکار',
      debate: 'مناظره',
      collaboration: 'همکاری',
      deep_research: 'تحقیق عمیق',
      quick: 'سریع',
      creative: 'خلاقانه',
    };
    return labels[mode] || mode;
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
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">مناظره AI</h1>
            <p className="text-gray-500 text-sm">سوال بپرسید و مدل‌ها پاسخ می‌دهند</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
          >
            خانه
          </Link>
        </div>

        {/* فرم مناظره */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-6">
          <h2 className="font-bold mb-4">مناظره جدید</h2>

          {/* وضعیت مدل‌ها */}
          {loading ? (
            <p className="text-gray-400 mb-4">در حال بارگذاری...</p>
          ) : models.length === 0 ? (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 p-3 rounded-lg mb-4">
              مدلی فعال نیست. به <Link href="/settings" className="underline">تنظیمات</Link> بروید.
            </div>
          ) : (
            <div className="flex flex-wrap gap-2 mb-4">
              {models.slice(0, 4).map((m) => (
                <span
                  key={m.id}
                  className="px-3 py-1 bg-green-100 text-green-700 rounded text-sm"
                >
                  {m.name}
                </span>
              ))}
              {models.length > 4 && (
                <span className="px-3 py-1 bg-gray-100 text-gray-500 rounded text-sm">
                  +{models.length - 4} دیگر
                </span>
              )}
            </div>
          )}

          {/* انتخاب حالت */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">حالت کار</label>
            <select
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
            >
              {workModes.length > 0 ? (
                workModes.map((mode: any) => (
                  <option key={mode.id} value={mode.id}>
                    {mode.name || getModeLabel(mode.id)}
                  </option>
                ))
              ) : (
                <>
                  <option value="auto">خودکار</option>
                  <option value="debate">مناظره</option>
                  <option value="collaboration">همکاری</option>
                  <option value="quick">سریع</option>
                </>
              )}
            </select>
          </div>

          {/* سوال */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">سوال شما</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="سوال یا موضوع مناظره را بنویسید..."
              rows={4}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
            />
          </div>

          <button
            onClick={startDebate}
            disabled={running || models.length === 0}
            className="w-full py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 disabled:opacity-50"
          >
            {running ? 'در حال اجرا...' : 'شروع مناظره'}
          </button>
        </div>

        {/* نتیجه مناظره */}
        {activeDebate && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-6">
            <h2 className="font-bold mb-4">نتیجه مناظره</h2>

            {/* خلاصه */}
            {activeDebate.summary && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">خلاصه</h3>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  {activeDebate.summary}
                </div>
              </div>
            )}

            {/* پاسخ‌های راند‌ها */}
            {activeDebate.rounds?.map((round: any, i: number) => (
              <div key={i} className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">راند {round.round_number || i + 1}</h3>
                <div className="space-y-3">
                  {round.responses?.map((resp: any, j: number) => (
                    <div key={j} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium">{resp.model}</span>
                        <span className="text-xs text-gray-500">{resp.role}</span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{resp.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* نتیجه داور */}
            {activeDebate.judge_result && (
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <h3 className="font-medium mb-2">نتیجه داوری</h3>
                <p><strong>برنده:</strong> {activeDebate.judge_result.winner}</p>
                {activeDebate.judge_result.reasoning && (
                  <p className="text-sm mt-2">{activeDebate.judge_result.reasoning}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* مناظرات اخیر */}
        {debates.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold">مناظرات اخیر</h2>
              <Link href="/archive" className="text-blue-500 text-sm">
                مشاهده همه
              </Link>
            </div>

            <div className="space-y-2">
              {debates.map((d) => (
                <div
                  key={d.id}
                  className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="font-medium truncate">{d.prompt}</div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                    <span>{getModeLabel(d.mode)}</span>
                    <span>•</span>
                    <span>{d.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
