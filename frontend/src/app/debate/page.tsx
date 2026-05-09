'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ModelInfo {
  id: string;
  name: string;
  provider?: string;
}

interface WorkModeInfo {
  id: string;
  name?: string;
  name_fa?: string;
  icon?: string;
  rounds?: number;
  scoring?: boolean;
  judge?: boolean;
  summary?: boolean;
}

interface DebateSummary {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models?: string[];
  rounds_count?: number;
  has_judge?: boolean;
  has_summary?: boolean;
  created_at?: string;
}

interface RoundResp {
  model: string;
  role?: string;
  content: string;
  duration?: number;
}

interface DebateDetail {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models: string[];
  role_assignments?: Record<string, string>;
  rounds: RoundResp[][];
  scores?: any[];
  judge_result?: { winner?: string; reasoning?: string; ranking?: any[] } | null;
  summary?: string;
}

const FALLBACK_MODES: WorkModeInfo[] = [
  { id: 'auto', name_fa: 'تشخیص خودکار', icon: '🤖' },
  { id: 'debate', name_fa: 'مناظره', icon: '🥊' },
  { id: 'collaboration', name_fa: 'همکاری', icon: '🤝' },
  { id: 'deep_research', name_fa: 'تحقیق عمیق', icon: '🔬' },
  { id: 'quick', name_fa: 'سریع', icon: '⚡' },
  { id: 'creative', name_fa: 'خلاقانه', icon: '🎨' },
];

export default function DebatePage() {
  const [debates, setDebates] = useState<DebateSummary[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [workModes, setWorkModes] = useState<WorkModeInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [prompt, setPrompt] = useState('');
  const [selectedMode, setSelectedMode] = useState('auto');
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState('');
  const [phasePct, setPhasePct] = useState(0);

  const [activeDebate, setActiveDebate] = useState<DebateDetail | null>(null);
  const pollRef = useRef<any>(null);

  useEffect(() => {
    loadData();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
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
      const [modelsRes, modesRes, debatesRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/models/available`),
        fetch(`${API_BASE}/api/settings/work-modes`),
        fetch(`${API_BASE}/api/debate/`),
      ]);

      if (modelsRes.status === 'fulfilled' && modelsRes.value.ok) {
        const data = await modelsRes.value.json();
        setModels(Array.isArray(data) ? data : []);
      }

      if (modesRes.status === 'fulfilled' && modesRes.value.ok) {
        const data = await modesRes.value.json();
        setWorkModes(Array.isArray(data) && data.length > 0 ? data : FALLBACK_MODES);
      } else {
        setWorkModes(FALLBACK_MODES);
      }

      if (debatesRes.status === 'fulfilled' && debatesRes.value.ok) {
        const data = await debatesRes.value.json();
        setDebates(Array.isArray(data) ? data.slice(0, 6) : []);
      }
    } catch (e) {
      console.error('Error loading debates data:', e);
      setWorkModes(FALLBACK_MODES);
    } finally {
      setLoading(false);
    }
  };

  const fetchDebateDetail = async (id: string): Promise<DebateDetail | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/debate/${id}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('Error fetching debate:', e);
    }
    return null;
  };

  const startPolling = (debateId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);

    let elapsed = 0;
    const maxSeconds = 600; // 10 دقیقه

    pollRef.current = setInterval(async () => {
      elapsed += 2;
      const detail = await fetchDebateDetail(debateId);

      if (detail) {
        setActiveDebate(detail);

        // به‌روزرسانی فاز
        const status = detail.status?.toLowerCase();
        if (status === 'running' || status === 'in_progress' || status === 'in-progress') {
          if (detail.rounds?.length > 0) {
            setPhase(`در حال راند ${detail.rounds.length}...`);
            setPhasePct(Math.min(40 + detail.rounds.length * 15, 80));
          } else {
            setPhase('شروع پاسخ‌دهی مدل‌ها...');
            setPhasePct(20);
          }
        } else if (status === 'scoring') {
          setPhase('در حال امتیازدهی...');
          setPhasePct(85);
        } else if (status === 'judging') {
          setPhase('در حال داوری...');
          setPhasePct(92);
        } else if (status === 'completed' || status === 'finished') {
          setPhase('تکمیل شد!');
          setPhasePct(100);
          clearInterval(pollRef.current);
          pollRef.current = null;
          setRunning(false);
          showSuccess('مناظره با موفقیت تمام شد');
          loadData();
        } else if (status === 'failed' || status === 'error') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setRunning(false);
          showError('مناظره با خطا متوقف شد');
        }
      }

      if (elapsed >= maxSeconds) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setRunning(false);
        showError('زمان انتظار به پایان رسید');
      }
    }, 2000);
  };

  const startDebate = async () => {
    if (!prompt.trim()) {
      showError('سوال یا موضوع را وارد کنید');
      return;
    }
    if (prompt.trim().length < 5) {
      showError('سوال خیلی کوتاه است');
      return;
    }
    if (models.length === 0) {
      showError('هیچ مدلی فعال نیست. به تنظیمات بروید.');
      return;
    }

    setRunning(true);
    setActiveDebate(null);
    setPhase('در حال ساخت مناظره...');
    setPhasePct(5);

    try {
      const createRes = await fetch(`${API_BASE}/api/debate/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          mode: selectedMode,
        }),
      });

      if (!createRes.ok) {
        const err = await createRes.json().catch(() => ({}));
        showError(err.detail || 'خطا در ساخت مناظره');
        setRunning(false);
        return;
      }

      const createData = await createRes.json();
      const debateId = createData.id || createData.debate?.id;

      if (!debateId) {
        showError('شناسه مناظره دریافت نشد');
        setRunning(false);
        return;
      }

      setPhase('شروع اجرا...');
      setPhasePct(10);

      // اجرای کامل (background task)
      const runRes = await fetch(`${API_BASE}/api/debate/${debateId}/run-full`, {
        method: 'POST',
      });

      if (!runRes.ok) {
        showError('خطا در اجرای مناظره');
        setRunning(false);
        return;
      }

      // شروع polling برای دریافت نتایج
      startPolling(debateId);
    } catch (e: any) {
      showError(e.message || 'خطا در ارتباط');
      setRunning(false);
    }
  };

  const stopDebate = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setRunning(false);
    setPhase('');
    setPhasePct(0);
  };

  const loadOldDebate = async (id: string) => {
    setActiveDebate(null);
    setPhase('در حال بارگذاری...');
    const d = await fetchDebateDetail(id);
    if (d) {
      setActiveDebate(d);
      setPhase('');
    } else {
      showError('بارگذاری ناموفق بود');
    }
  };

  const getModeLabel = (mode: string) => {
    const m = workModes.find((x) => x.id === mode);
    if (m) return `${m.icon || ''} ${m.name_fa || m.name || mode}`.trim();
    const fallback: Record<string, string> = {
      auto: '🤖 خودکار',
      debate: '🥊 مناظره',
      collaboration: '🤝 همکاری',
      deep_research: '🔬 تحقیق عمیق',
      quick: '⚡ سریع',
      creative: '🎨 خلاقانه',
    };
    return fallback[mode] || mode;
  };

  const currentMode = useMemo(
    () => workModes.find((m) => m.id === selectedMode),
    [workModes, selectedMode],
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

      <div className="max-w-5xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2 dark:text-white">
              <span>🥊</span>
              <span>مناظره AI</span>
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              سوال بپرسید و چند مدل با هم بحث کنند تا بهترین پاسخ را پیدا کنند
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/archive"
              className="px-4 py-2 bg-white dark:bg-gray-800 dark:text-white rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              📚 آرشیو
            </Link>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              🏠 خانه
            </Link>
          </div>
        </div>

        {/* فرم مناظره */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-6">
          <h2 className="font-bold mb-4 dark:text-white">مناظره جدید</h2>

          {/* وضعیت مدل‌ها */}
          {loading ? (
            <p className="text-gray-400 mb-4">در حال بارگذاری مدل‌ها...</p>
          ) : models.length === 0 ? (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 p-3 rounded-lg mb-4 border border-yellow-200 dark:border-yellow-700">
              ⚠️ مدلی فعال نیست. به{' '}
              <Link href="/settings" className="underline font-medium">
                تنظیمات
              </Link>{' '}
              بروید و کلید API وارد کنید.
            </div>
          ) : (
            <div className="mb-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                مدل‌های فعال ({models.length}):
              </p>
              <div className="flex flex-wrap gap-2">
                {models.slice(0, 6).map((m) => (
                  <span
                    key={m.id}
                    className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-xs"
                  >
                    ✓ {m.name}
                  </span>
                ))}
                {models.length > 6 && (
                  <span className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300 rounded-full text-xs">
                    +{models.length - 6} دیگر
                  </span>
                )}
              </div>
            </div>
          )}

          {/* انتخاب حالت */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2 dark:text-gray-200">حالت کار</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {workModes.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setSelectedMode(mode.id)}
                  className={`p-3 rounded-lg border text-right transition ${
                    selectedMode === mode.id
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-gray-50 dark:bg-gray-700 dark:text-gray-200 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{mode.icon || '🔵'}</span>
                    <span className="text-sm font-medium">{mode.name_fa || mode.name}</span>
                  </div>
                </button>
              ))}
            </div>
            {currentMode && (
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex flex-wrap gap-x-3 gap-y-1">
                {currentMode.rounds !== undefined && (
                  <span>🔁 {currentMode.rounds} راند</span>
                )}
                {currentMode.scoring && <span>📊 امتیازدهی</span>}
                {currentMode.judge && <span>⚖️ داوری</span>}
                {currentMode.summary && <span>📝 خلاصه</span>}
              </div>
            )}
          </div>

          {/* سوال */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2 dark:text-gray-200">
              سوال شما
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="سوال یا موضوع مناظره را بنویسید... (مثال: بهترین زبان برای backend در ۲۰۲۶ چیست؟)"
              rows={4}
              disabled={running}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
          </div>

          {/* نوار پیشرفت */}
          {running && (
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-blue-700 dark:text-blue-300 flex items-center gap-2">
                  <span className="inline-block w-3 h-3 bg-blue-500 rounded-full animate-pulse"></span>
                  {phase}
                </span>
                <span className="text-gray-500">{Math.round(phasePct)}%</span>
              </div>
              <div className="w-full h-2 bg-blue-100 dark:bg-blue-900/40 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${phasePct}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={startDebate}
              disabled={running || models.length === 0}
              className="flex-1 py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 disabled:opacity-50 transition"
            >
              {running ? '⏳ در حال اجرا...' : '🚀 شروع مناظره'}
            </button>
            {running && (
              <button
                onClick={stopDebate}
                className="px-4 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
              >
                ⏹️ توقف
              </button>
            )}
          </div>
        </div>

        {/* نتیجه مناظره */}
        {activeDebate && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold dark:text-white">📝 نتیجه مناظره</h2>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  activeDebate.status === 'completed' || activeDebate.status === 'finished'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                }`}
              >
                {activeDebate.status}
              </span>
            </div>

            {/* سوال */}
            <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">سوال:</p>
              <p className="text-sm dark:text-gray-200">{activeDebate.prompt}</p>
            </div>

            {/* خلاصه */}
            {activeDebate.summary && (
              <div className="mb-4">
                <h3 className="text-sm font-medium mb-2 dark:text-gray-200">📌 خلاصه</h3>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg whitespace-pre-wrap text-sm dark:text-blue-100 border border-blue-200 dark:border-blue-800">
                  {activeDebate.summary}
                </div>
              </div>
            )}

            {/* نتیجه داور */}
            {activeDebate.judge_result && activeDebate.judge_result.winner && (
              <div className="mb-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                <h3 className="font-medium mb-2 dark:text-yellow-200 flex items-center gap-2">
                  ⚖️ نتیجه داوری
                </h3>
                <p className="text-sm dark:text-yellow-100">
                  <strong>برنده:</strong> {activeDebate.judge_result.winner}
                </p>
                {activeDebate.judge_result.reasoning && (
                  <p className="text-xs mt-2 dark:text-yellow-200/80 whitespace-pre-wrap">
                    {activeDebate.judge_result.reasoning}
                  </p>
                )}
              </div>
            )}

            {/* راندها */}
            {activeDebate.rounds?.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium dark:text-gray-200">💬 پاسخ‌ها و راندها</h3>
                {activeDebate.rounds.map((round, i) => (
                  <div key={i} className="border-r-4 border-blue-500 pr-3">
                    <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                      راند {i + 1}
                    </h4>
                    <div className="space-y-2">
                      {round?.map((resp, j) => (
                        <div
                          key={j}
                          className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                        >
                          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
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
          </div>
        )}

        {/* مناظرات اخیر */}
        {debates.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold dark:text-white">🕐 مناظرات اخیر</h2>
              <Link href="/archive" className="text-blue-500 text-sm hover:underline">
                مشاهده همه ←
              </Link>
            </div>

            <div className="space-y-2">
              {debates.map((d) => (
                <button
                  key={d.id}
                  onClick={() => loadOldDebate(d.id)}
                  className="w-full text-right p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                >
                  <div className="font-medium truncate text-sm dark:text-white">
                    {d.prompt}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                    <span>{getModeLabel(d.mode)}</span>
                    <span>•</span>
                    <span
                      className={`px-1.5 py-0.5 rounded ${
                        d.status === 'completed'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                      }`}
                    >
                      {d.status}
                    </span>
                    {d.rounds_count !== undefined && (
                      <span>• {d.rounds_count} راند</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
