'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ModelInfo {
  id: string;
  name: string;
  provider?: string;
}

interface Repo {
  id: number;
  full_name: string;
  name: string;
  owner: string;
  description: string;
  private: boolean;
  default_branch: string;
  language: string;
  html_url: string;
  pushed_at?: string;
  updated_at?: string;
  stargazers_count?: number;
  open_issues_count?: number;
  topics?: string[];
  archived?: boolean;
}

interface Watched {
  id: string;
  repo_full_name: string;
  repo_url: string;
  private: boolean;
  default_branch: string;
  language: string;
  user_notes: string;
  tags: string[];
  schedule_enabled: boolean;
  interval_hours: number;
  autonomy_level: 'manual' | 'assist' | 'auto';
  allow_push: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
}

interface Task {
  id: string;
  watched_id?: string | null;
  project_full_name: string;
  title: string;
  prompt: string;
  raw_idea?: string;
  type: string;
  priority: string;
  status: string;
  models_used?: string[];
  last_run_at?: string | null;
  runs_count?: number;
  last_summary?: string;
  deadline?: string | null;
  source: string;
  created_at?: string;
}

interface Report {
  id: string;
  task_id: string;
  watched_id?: string | null;
  project_full_name: string;
  run_at: string;
  status: 'done' | 'partial' | 'not_done' | 'error';
  done_parts: string[];
  remaining_parts: string[];
  evidence: Record<string, any>;
  next_actions: string[];
  confidence_score: number;
  raw_response?: string;
  model_id?: string;
  read?: boolean;
  flagged?: boolean;
}

interface Status {
  github_token: boolean;
  render_token: boolean;
  watched_count: number;
  tasks_count: number;
  reports_count: number;
  tasks_by_status: Record<string, number>;
  settings: any;
}

const TASK_STATUSES = [
  { id: 'pending', label: 'در صف', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300' },
  { id: 'running', label: 'در حال اجرا', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' },
  { id: 'awaiting_review', label: 'بازبینی', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300' },
  { id: 'done', label: 'انجام شده', color: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300' },
  { id: 'failed', label: 'خطا', color: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300' },
  { id: 'cancelled', label: 'لغو', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' },
  { id: 'suggested', label: 'پیشنهاد AI', color: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300' },
];

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  medium: 'bg-blue-200 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  high: 'bg-orange-200 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
  critical: 'bg-red-200 text-red-800 dark:bg-red-900/40 dark:text-red-200',
};

const TYPE_ICONS: Record<string, string> = {
  idea: '💡',
  bug: '🐛',
  feature_request: '✨',
  refactor: '🔧',
  docs: '📝',
  other: '📌',
};

export default function OversightPage() {
  const [tab, setTab] = useState<'repos' | 'watched' | 'ideas' | 'tasks' | 'reports'>('watched');

  const [status, setStatus] = useState<Status | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('');

  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposSyncedAt, setReposSyncedAt] = useState<string | null>(null);
  const [reposLoading, setReposLoading] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');
  const [repoLangFilter, setRepoLangFilter] = useState('');
  const [repoVisibility, setRepoVisibility] = useState<'all' | 'public' | 'private'>('all');

  const [watched, setWatched] = useState<Watched[]>([]);
  const [editingWatched, setEditingWatched] = useState<Watched | null>(null);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskFilterStatus, setTaskFilterStatus] = useState<string>('all');
  const [taskFilterWatched, setTaskFilterWatched] = useState<string>('all');
  const [viewingTask, setViewingTask] = useState<Task | null>(null);

  const [reports, setReports] = useState<Report[]>([]);
  const [viewingReport, setViewingReport] = useState<Report | null>(null);

  // Idea inbox
  const [idea, setIdea] = useState('');
  const [ideaWatchedId, setIdeaWatchedId] = useState<string>('');
  const [ideaType, setIdeaType] = useState('idea');
  const [ideaPriority, setIdeaPriority] = useState('medium');
  const [generating, setGenerating] = useState(false);
  const [previewPrompt, setPreviewPrompt] = useState<{ title: string; prompt: string } | null>(null);

  // Settings
  const [settings, setSettings] = useState<any>({});

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };
  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 3500);
  };

  useEffect(() => {
    init();
  }, []);

  useEffect(() => {
    // load saved model from localStorage
    if (typeof window === 'undefined') return;
    try {
      const saved = localStorage.getItem('oversight_model');
      if (saved) setSelectedModelId(saved);
    } catch {}
  }, []);

  const saveModelChoice = (id: string) => {
    setSelectedModelId(id);
    try {
      localStorage.setItem('oversight_model', id);
    } catch {}
  };

  const init = async () => {
    setLoading(true);
    try {
      const [statusRes, modelsRes, watchedRes, tasksRes, reportsRes, settingsRes] =
        await Promise.allSettled([
          fetch(`${API_BASE}/api/oversight/status`),
          fetch(`${API_BASE}/api/models/available`),
          fetch(`${API_BASE}/api/oversight/watched`),
          fetch(`${API_BASE}/api/oversight/tasks`),
          fetch(`${API_BASE}/api/oversight/reports?limit=200`),
          fetch(`${API_BASE}/api/oversight/settings`),
        ]);

      if (statusRes.status === 'fulfilled' && statusRes.value.ok)
        setStatus(await statusRes.value.json());
      if (modelsRes.status === 'fulfilled' && modelsRes.value.ok) {
        const data = await modelsRes.value.json();
        setModels(Array.isArray(data) ? data : []);
      }
      if (watchedRes.status === 'fulfilled' && watchedRes.value.ok) {
        const data = await watchedRes.value.json();
        setWatched(data.items || []);
      }
      if (tasksRes.status === 'fulfilled' && tasksRes.value.ok) {
        const data = await tasksRes.value.json();
        setTasks(data.items || []);
      }
      if (reportsRes.status === 'fulfilled' && reportsRes.value.ok) {
        const data = await reportsRes.value.json();
        setReports(data.items || []);
      }
      if (settingsRes.status === 'fulfilled' && settingsRes.value.ok)
        setSettings(await settingsRes.value.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const reloadStatus = async () => {
    const r = await fetch(`${API_BASE}/api/oversight/status`);
    if (r.ok) setStatus(await r.json());
  };

  // ============================ Repos ============================

  const loadRepos = async () => {
    setReposLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/oversight/repos`);
      const data = await res.json();
      if (data.success) {
        setRepos(data.repos || []);
        setReposSyncedAt(data.synced_at || new Date().toISOString());
        showSuccess(`${data.count} مخزن بارگذاری شد`);
      } else {
        showError(data.error || 'خطا در دریافت مخازن');
        setRepos(data.repos || []);
      }
    } catch (e: any) {
      showError(e.message || 'خطای ارتباط');
    } finally {
      setReposLoading(false);
    }
  };

  const addToWatch = async (repo: Repo) => {
    try {
      const res = await fetch(`${API_BASE}/api/oversight/watched`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_full_name: repo.full_name,
          repo_url: repo.html_url,
          private: repo.private,
          default_branch: repo.default_branch,
          language: repo.language,
          tags: repo.topics || [],
        }),
      });
      if (res.ok) {
        const w = await res.json();
        setWatched((prev) => {
          if (prev.some((x) => x.id === w.id)) return prev;
          return [...prev, w];
        });
        showSuccess('به لیست نظارت اضافه شد');
        reloadStatus();
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در اضافه کردن');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const filteredRepos = useMemo(() => {
    return repos.filter((r) => {
      if (
        repoSearch &&
        !r.full_name.toLowerCase().includes(repoSearch.toLowerCase()) &&
        !r.description?.toLowerCase().includes(repoSearch.toLowerCase())
      )
        return false;
      if (repoLangFilter && r.language !== repoLangFilter) return false;
      if (repoVisibility === 'private' && !r.private) return false;
      if (repoVisibility === 'public' && r.private) return false;
      return true;
    });
  }, [repos, repoSearch, repoLangFilter, repoVisibility]);

  const repoLanguages = useMemo(() => {
    const set = new Set<string>();
    repos.forEach((r) => r.language && set.add(r.language));
    return Array.from(set).sort();
  }, [repos]);

  // ============================ Watched ============================

  const updateWatched = async (id: string, updates: Partial<Watched>) => {
    try {
      const res = await fetch(`${API_BASE}/api/oversight/watched/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const w = await res.json();
        setWatched((prev) => prev.map((x) => (x.id === id ? w : x)));
        showSuccess('بروزرسانی شد');
      } else {
        showError('خطا در بروزرسانی');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const removeWatched = async (id: string, name: string) => {
    if (!confirm(`«${name}» از لیست نظارت حذف شود؟`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/oversight/watched/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setWatched((prev) => prev.filter((x) => x.id !== id));
        showSuccess('حذف شد');
        reloadStatus();
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const scanProject = async (id: string) => {
    showSuccess('اسکن شروع شد... ممکن است کمی طول بکشد');
    try {
      const res = await fetch(`${API_BASE}/api/oversight/scan/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModelId || undefined }),
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(`${data.created_count} نیاز/پیشنهاد جدید شناسایی شد`);
        // refresh tasks
        const tasksRes = await fetch(`${API_BASE}/api/oversight/tasks`);
        if (tasksRes.ok) {
          const t = await tasksRes.json();
          setTasks(t.items || []);
        }
        setTab('tasks');
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در اسکن');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  // ============================ Idea / Tasks ============================

  const generatePrompt = async () => {
    if (!idea.trim()) {
      showError('متن ایده را وارد کنید');
      return;
    }
    setGenerating(true);
    setPreviewPrompt(null);
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/from-idea`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea,
          watched_id: ideaWatchedId || null,
          type: ideaType,
          priority: ideaPriority,
          model_id: selectedModelId || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewPrompt({ title: data.title, prompt: data.prompt });
        showSuccess('پرامپت تولید شد - بررسی و تأیید کنید');
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در تولید پرامپت');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const savePromptAsTask = async () => {
    if (!previewPrompt) return;
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          watched_id: ideaWatchedId || null,
          project_full_name: watched.find((w) => w.id === ideaWatchedId)?.repo_full_name || '',
          title: previewPrompt.title,
          prompt: previewPrompt.prompt,
          raw_idea: idea,
          type: ideaType,
          priority: ideaPriority,
          status: 'pending',
        }),
      });
      if (res.ok) {
        const t = await res.json();
        setTasks((prev) => [t, ...prev]);
        setIdea('');
        setPreviewPrompt(null);
        showSuccess('تسک ساخته شد');
        reloadStatus();
        setTab('tasks');
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const runTask = async (id: string) => {
    showSuccess('در حال اجرا...');
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: 'running' } : t))
    );
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModelId || undefined }),
      });
      if (res.ok) {
        const data = await res.json();
        setTasks((prev) => prev.map((t) => (t.id === id ? data.task : t)));
        if (data.report) setReports((prev) => [data.report, ...prev]);
        showSuccess('اجرا کامل شد');
        reloadStatus();
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در اجرا');
        // refetch task
        init();
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const updateTask = async (id: string, updates: Partial<Task>) => {
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const t = await res.json();
        setTasks((prev) => prev.map((x) => (x.id === id ? t : x)));
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  const deleteTask = async (id: string) => {
    if (!confirm('تسک حذف شود؟')) return;
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setTasks((prev) => prev.filter((x) => x.id !== id));
        showSuccess('حذف شد');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      if (taskFilterStatus !== 'all' && t.status !== taskFilterStatus) return false;
      if (taskFilterWatched !== 'all' && t.watched_id !== taskFilterWatched) return false;
      return true;
    });
  }, [tasks, taskFilterStatus, taskFilterWatched]);

  // ============================ Settings ============================

  const updateSettings = async (updates: any) => {
    try {
      const res = await fetch(`${API_BASE}/api/oversight/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const s = await res.json();
        setSettings(s);
        showSuccess('تنظیمات ذخیره شد');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  // ============================ UI ============================

  const watchedFullNames = useMemo(
    () => new Set(watched.map((w) => w.repo_full_name)),
    [watched],
  );

  const fmtDate = (d?: string | null) => {
    if (!d) return '-';
    try {
      return new Date(d).toLocaleString('fa-IR');
    } catch {
      return d;
    }
  };

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

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
              🛰️ مرکز نظارت پروژه‌ها
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              مدیریت یکپارچه مخازن گیت‌هاب با AI - ایده، پرامپت، اجرا، گزارش
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={init}
              className="px-4 py-2 bg-white dark:bg-gray-800 dark:text-white border dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              🔄 بروزرسانی
            </button>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-300"
            >
              🏠 خانه
            </Link>
          </div>
        </div>

        {/* وضعیت توکن‌ها */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
          <StatusCard
            label="GitHub"
            ok={status?.github_token}
            okLabel="متصل"
            failLabel="توکن ندارد"
          />
          <StatusCard
            label="Render"
            ok={status?.render_token}
            okLabel="متصل"
            failLabel="توکن ندارد"
          />
          <StatusCard
            label="پروژه‌های تحت نظارت"
            ok={true}
            okLabel={`${status?.watched_count ?? 0} پروژه`}
            isCount
          />
          <StatusCard
            label="تسک‌ها"
            ok={true}
            okLabel={`${status?.tasks_count ?? 0} تسک`}
            isCount
          />
          <StatusCard
            label="گزارش‌ها"
            ok={true}
            okLabel={`${status?.reports_count ?? 0} گزارش`}
            isCount
          />
        </div>

        {!status?.github_token && (
          <div className="mb-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg flex items-center justify-between flex-wrap gap-2">
            <span className="text-yellow-800 dark:text-yellow-200 text-sm">
              ⚠️ توکن گیت‌هاب تنظیم نشده — بدون آن نمی‌توانید مخازن خود را ببینید.
            </span>
            <Link
              href="/settings"
              className="px-3 py-1 bg-yellow-500 text-black rounded text-sm font-medium hover:bg-yellow-400"
            >
              تنظیم در /settings
            </Link>
          </div>
        )}

        {/* انتخاب مدل */}
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl shadow">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="font-bold dark:text-white">🤖 مدل پیش‌فرض نظارت</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {models.length} مدل فعال
              </p>
            </div>
            <select
              value={selectedModelId}
              onChange={(e) => saveModelChoice(e.target.value)}
              className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 min-w-[260px]"
            >
              <option value="">— اولین مدل موجود —</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} {m.provider ? `(${m.provider})` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {(
            [
              { id: 'watched', label: 'تحت نظارت', icon: '👁️', count: watched.length },
              { id: 'repos', label: 'مخازن GitHub', icon: '📦', count: repos.length },
              { id: 'ideas', label: 'ایده/مشکل', icon: '💡', count: 0 },
              { id: 'tasks', label: 'تسک‌ها', icon: '📋', count: tasks.length },
              { id: 'reports', label: 'گزارش‌ها', icon: '📊', count: reports.length },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                tab === t.id
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'bg-white dark:bg-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
              {t.count > 0 && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    tab === t.id ? 'bg-white/20' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                >
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* محتوا */}
        {loading ? (
          <div className="text-center py-12 dark:text-gray-300">در حال بارگذاری...</div>
        ) : tab === 'watched' ? (
          // ============================ Watched ============================
          <div className="space-y-3">
            {watched.length === 0 ? (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-12 text-center text-gray-400">
                <div className="text-5xl mb-3">📭</div>
                <p className="mb-3">پروژه‌ای تحت نظارت نیست</p>
                <button
                  onClick={() => setTab('repos')}
                  className="text-blue-500 hover:underline"
                >
                  از تب «مخازن» انتخاب کنید ←
                </button>
              </div>
            ) : (
              watched.map((w) => (
                <WatchedCard
                  key={w.id}
                  w={w}
                  onChange={(u) => updateWatched(w.id, u)}
                  onRemove={() => removeWatched(w.id, w.repo_full_name)}
                  onScan={() => scanProject(w.id)}
                  onWriteIdea={() => {
                    setIdeaWatchedId(w.id);
                    setTab('ideas');
                  }}
                  onViewTasks={() => {
                    setTaskFilterWatched(w.id);
                    setTab('tasks');
                  }}
                />
              ))
            )}
          </div>
        ) : tab === 'repos' ? (
          // ============================ Repos ============================
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <div>
                <h2 className="font-bold dark:text-white">📦 مخازن گیت‌هاب من</h2>
                {reposSyncedAt && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    آخرین sync: {fmtDate(reposSyncedAt)}
                  </p>
                )}
              </div>
              <button
                onClick={loadRepos}
                disabled={reposLoading || !status?.github_token}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {reposLoading ? '⏳ در حال بارگذاری...' : '🔄 بارگذاری از GitHub'}
              </button>
            </div>

            {repos.length > 0 && (
              <div className="flex gap-2 mb-4 flex-wrap">
                <input
                  type="text"
                  placeholder="🔍 جستجو..."
                  value={repoSearch}
                  onChange={(e) => setRepoSearch(e.target.value)}
                  className="flex-1 min-w-[200px] p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                />
                <select
                  value={repoLangFilter}
                  onChange={(e) => setRepoLangFilter(e.target.value)}
                  className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="">همه زبان‌ها</option>
                  {repoLanguages.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
                <select
                  value={repoVisibility}
                  onChange={(e) => setRepoVisibility(e.target.value as any)}
                  className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="all">همه</option>
                  <option value="public">عمومی</option>
                  <option value="private">خصوصی</option>
                </select>
              </div>
            )}

            {repos.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-3">📦</div>
                <p>روی «بارگذاری از GitHub» کلیک کنید</p>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {filteredRepos.map((r) => {
                  const watching = watchedFullNames.has(r.full_name);
                  return (
                    <div
                      key={r.id}
                      className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-transparent hover:border-blue-300 dark:hover:border-blue-700 transition"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <a
                              href={r.html_url}
                              target="_blank"
                              rel="noreferrer"
                              className="font-medium text-sm dark:text-white hover:underline truncate"
                              dir="ltr"
                            >
                              {r.full_name}
                            </a>
                            {r.private && (
                              <span className="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 dark:text-gray-200 rounded">
                                🔒 خصوصی
                              </span>
                            )}
                            {r.archived && (
                              <span className="text-xs px-1.5 py-0.5 bg-yellow-200 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-300 rounded">
                                آرشیو
                              </span>
                            )}
                          </div>
                          {r.description && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">
                              {r.description}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                            {r.language && <span>💻 {r.language}</span>}
                            {(r.stargazers_count ?? 0) > 0 && (
                              <span>⭐ {r.stargazers_count}</span>
                            )}
                            {(r.open_issues_count ?? 0) > 0 && (
                              <span>🔧 {r.open_issues_count} issue</span>
                            )}
                            {r.pushed_at && <span>📅 {fmtDate(r.pushed_at)}</span>}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => addToWatch(r)}
                        disabled={watching}
                        className={`w-full mt-2 px-3 py-1.5 rounded text-sm font-medium ${
                          watching
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 cursor-default'
                            : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 hover:bg-blue-200'
                        }`}
                      >
                        {watching ? '✓ تحت نظارت' : '+ افزودن به نظارت'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : tab === 'ideas' ? (
          // ============================ Ideas ============================
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold mb-4 dark:text-white">💡 ایده / مشکل / درخواست</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              هر چه به ذهنت می‌رسد بنویس - AI آن را به یک پرامپت قدرتمند با ساختار «هدف /
              context / مراحل / معیار پذیرش / خروجی» تبدیل می‌کند.
            </p>

            <div className="grid sm:grid-cols-3 gap-3 mb-4">
              <div>
                <label className="block text-xs mb-1 dark:text-gray-300">پروژه</label>
                <select
                  value={ideaWatchedId}
                  onChange={(e) => setIdeaWatchedId(e.target.value)}
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="">— هیچ پروژه‌ای —</option>
                  {watched.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.repo_full_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1 dark:text-gray-300">نوع</label>
                <select
                  value={ideaType}
                  onChange={(e) => setIdeaType(e.target.value)}
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="idea">💡 ایده</option>
                  <option value="bug">🐛 باگ</option>
                  <option value="feature_request">✨ قابلیت جدید</option>
                  <option value="refactor">🔧 بازنویسی</option>
                  <option value="docs">📝 مستند</option>
                  <option value="other">📌 دیگر</option>
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1 dark:text-gray-300">اولویت</label>
                <select
                  value={ideaPriority}
                  onChange={(e) => setIdeaPriority(e.target.value)}
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="low">پایین</option>
                  <option value="medium">متوسط</option>
                  <option value="high">بالا</option>
                  <option value="critical">بحرانی</option>
                </select>
              </div>
            </div>

            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              rows={6}
              placeholder="مثلاً: «authentication این پروژه ضعیفه. JWT اضافه کن، rate limit بذار، endpoint های login/register رو امن کن، اگه کاربر سه بار اشتباه پسورد بزنه قفل بشه...»"
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 mb-3"
            />

            <button
              onClick={generatePrompt}
              disabled={generating || !idea.trim()}
              className="w-full py-3 bg-purple-500 text-white rounded-lg font-bold hover:bg-purple-600 disabled:opacity-50"
            >
              {generating ? '⏳ AI در حال تبدیل به پرامپت قدرتمند...' : '🪄 تبدیل به پرامپت با AI'}
            </button>

            {previewPrompt && (
              <div className="mt-6 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                <h3 className="font-bold mb-2 dark:text-purple-200">
                  ✨ پیش‌نمایش پرامپت — قبل از ذخیره ویرایش کنید
                </h3>
                <input
                  type="text"
                  value={previewPrompt.title}
                  onChange={(e) =>
                    setPreviewPrompt({ ...previewPrompt, title: e.target.value })
                  }
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 mb-2 font-medium"
                />
                <textarea
                  value={previewPrompt.prompt}
                  onChange={(e) =>
                    setPreviewPrompt({ ...previewPrompt, prompt: e.target.value })
                  }
                  rows={12}
                  className="w-full p-3 border rounded-lg dark:bg-gray-900 dark:text-white dark:border-gray-700 font-mono text-sm whitespace-pre-wrap"
                />
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={savePromptAsTask}
                    className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    ✓ ذخیره به‌عنوان تسک
                  </button>
                  <button
                    onClick={() => setPreviewPrompt(null)}
                    className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded-lg hover:bg-gray-400"
                  >
                    لغو
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : tab === 'tasks' ? (
          // ============================ Tasks ============================
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <h2 className="font-bold dark:text-white">📋 صف تسک‌ها</h2>
              <div className="flex gap-2 flex-wrap">
                <select
                  value={taskFilterStatus}
                  onChange={(e) => setTaskFilterStatus(e.target.value)}
                  className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 text-sm"
                >
                  <option value="all">همه وضعیت‌ها</option>
                  {TASK_STATUSES.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <select
                  value={taskFilterWatched}
                  onChange={(e) => setTaskFilterWatched(e.target.value)}
                  className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 text-sm"
                >
                  <option value="all">همه پروژه‌ها</option>
                  {watched.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.repo_full_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {filteredTasks.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-3">📋</div>
                <p>تسکی نیست</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredTasks.map((t) => {
                  const statusInfo = TASK_STATUSES.find((s) => s.id === t.status);
                  return (
                    <div
                      key={t.id}
                      className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-transparent hover:border-blue-300 dark:hover:border-blue-700"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2 flex-wrap">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span className="text-lg">{TYPE_ICONS[t.type] || '📌'}</span>
                            <button
                              onClick={() => setViewingTask(t)}
                              className="font-medium dark:text-white text-right hover:underline"
                            >
                              {t.title}
                            </button>
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${statusInfo?.color || ''}`}
                            >
                              {statusInfo?.label || t.status}
                            </span>
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${PRIORITY_COLORS[t.priority] || ''}`}
                            >
                              {t.priority}
                            </span>
                            {t.source === 'auto_scan' && (
                              <span className="text-xs px-2 py-0.5 bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300 rounded">
                                🤖 AI
                              </span>
                            )}
                          </div>
                          {t.project_full_name && (
                            <div className="text-xs text-gray-500 dark:text-gray-400" dir="ltr">
                              {t.project_full_name}
                            </div>
                          )}
                          {t.last_summary && (
                            <p className="text-xs text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
                              {t.last_summary}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                            {t.runs_count !== undefined && t.runs_count > 0 && (
                              <span>🔁 {t.runs_count} اجرا</span>
                            )}
                            {t.last_run_at && <span>⏱ {fmtDate(t.last_run_at)}</span>}
                          </div>
                        </div>
                        <div className="flex gap-1 flex-wrap">
                          <button
                            onClick={() => runTask(t.id)}
                            disabled={t.status === 'running'}
                            className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600 disabled:opacity-50"
                          >
                            ▶ اجرا
                          </button>
                          {t.status === 'suggested' && (
                            <button
                              onClick={() => updateTask(t.id, { status: 'pending' })}
                              className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
                            >
                              ✓ تأیید
                            </button>
                          )}
                          <button
                            onClick={() => setViewingTask(t)}
                            className="px-3 py-1 bg-gray-200 dark:bg-gray-600 dark:text-white rounded text-xs hover:bg-gray-300"
                          >
                            👁 مشاهده
                          </button>
                          <button
                            onClick={() => deleteTask(t.id)}
                            className="px-3 py-1 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300 rounded text-xs hover:bg-red-200"
                          >
                            🗑
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          // ============================ Reports ============================
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold mb-4 dark:text-white">📊 گزارش‌ها</h2>
            {reports.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-3">📊</div>
                <p>هنوز گزارشی ثبت نشده</p>
              </div>
            ) : (
              <div className="space-y-2">
                {reports.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setViewingReport(r)}
                    className="w-full text-right p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          r.status === 'done'
                            ? 'bg-green-100 text-green-700'
                            : r.status === 'partial'
                            ? 'bg-yellow-100 text-yellow-700'
                            : r.status === 'not_done'
                            ? 'bg-orange-100 text-orange-700'
                            : 'bg-red-100 text-red-700'
                        }`}
                      >
                        {r.status}
                      </span>
                      <span className="dark:text-gray-200" dir="ltr">
                        {r.project_full_name}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ⏱ {fmtDate(r.run_at)}
                      </span>
                      <span className="text-xs text-gray-500 mr-auto">
                        اعتماد: {Math.round((r.confidence_score || 0) * 100)}%
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* مودال تسک */}
        {viewingTask && (
          <Modal onClose={() => setViewingTask(null)} title="📋 جزئیات تسک">
            <div className="space-y-3">
              <div>
                <h4 className="text-xs text-gray-500 mb-1">عنوان</h4>
                <p className="font-medium dark:text-white">{viewingTask.title}</p>
              </div>
              {viewingTask.raw_idea && (
                <div>
                  <h4 className="text-xs text-gray-500 mb-1">ایدهٔ خام</h4>
                  <p className="text-sm dark:text-gray-300 whitespace-pre-wrap">
                    {viewingTask.raw_idea}
                  </p>
                </div>
              )}
              <div>
                <h4 className="text-xs text-gray-500 mb-1">پرامپت</h4>
                <pre className="text-sm dark:text-gray-200 whitespace-pre-wrap p-3 bg-gray-50 dark:bg-gray-900 rounded-lg max-h-80 overflow-auto">
                  {viewingTask.prompt}
                </pre>
              </div>
              {viewingTask.last_summary && (
                <div>
                  <h4 className="text-xs text-gray-500 mb-1">خلاصه آخرین اجرا</h4>
                  <p className="text-sm dark:text-gray-200 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    {viewingTask.last_summary}
                  </p>
                </div>
              )}
              <div className="flex gap-2 pt-3">
                <button
                  onClick={() => {
                    runTask(viewingTask.id);
                    setViewingTask(null);
                  }}
                  className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  ▶ اجرای فوری
                </button>
              </div>
            </div>
          </Modal>
        )}

        {/* مودال گزارش */}
        {viewingReport && (
          <Modal onClose={() => setViewingReport(null)} title="📊 جزئیات گزارش">
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={`px-2 py-1 rounded text-sm ${
                    viewingReport.status === 'done'
                      ? 'bg-green-100 text-green-700'
                      : viewingReport.status === 'partial'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {viewingReport.status}
                </span>
                <span className="text-sm dark:text-gray-300">
                  اعتماد: {Math.round((viewingReport.confidence_score || 0) * 100)}%
                </span>
                <span className="text-xs text-gray-500 mr-auto">
                  {fmtDate(viewingReport.run_at)}
                </span>
              </div>

              {viewingReport.done_parts.length > 0 && (
                <Section title="✅ انجام شده" items={viewingReport.done_parts} />
              )}
              {viewingReport.remaining_parts.length > 0 && (
                <Section title="⏳ باقی‌مانده" items={viewingReport.remaining_parts} />
              )}
              {viewingReport.next_actions.length > 0 && (
                <Section title="🎯 اقدامات بعدی" items={viewingReport.next_actions} />
              )}
              {Object.keys(viewingReport.evidence || {}).length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2 dark:text-gray-200">🔗 شواهد</h4>
                  <pre className="text-xs p-3 bg-gray-50 dark:bg-gray-900 dark:text-gray-200 rounded-lg overflow-auto" dir="ltr">
                    {JSON.stringify(viewingReport.evidence, null, 2)}
                  </pre>
                </div>
              )}
              {viewingReport.raw_response && (
                <details>
                  <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400">
                    خروجی خام مدل
                  </summary>
                  <pre className="text-xs mt-2 p-3 bg-gray-50 dark:bg-gray-900 dark:text-gray-300 rounded-lg overflow-auto whitespace-pre-wrap">
                    {viewingReport.raw_response}
                  </pre>
                </details>
              )}

              <div className="flex gap-2 pt-3">
                <button
                  onClick={() => {
                    const data = JSON.stringify(viewingReport, null, 2);
                    const blob = new Blob([data], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `report-${viewingReport.id}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
                >
                  ↓ JSON
                </button>
              </div>
            </div>
          </Modal>
        )}

        {/* مودال ویرایش watched */}
        {editingWatched && (
          <Modal onClose={() => setEditingWatched(null)} title="✏️ ویرایش پروژه تحت نظارت">
            <WatchedEditor
              watched={editingWatched}
              onSave={async (updates) => {
                await updateWatched(editingWatched.id, updates);
                setEditingWatched(null);
              }}
              onCancel={() => setEditingWatched(null)}
            />
          </Modal>
        )}
      </div>
    </div>
  );
}

// ============================ Sub-components ============================

function StatusCard({
  label,
  ok,
  okLabel,
  failLabel,
  isCount,
}: {
  label: string;
  ok?: boolean;
  okLabel: string;
  failLabel?: string;
  isCount?: boolean;
}) {
  const ng = !isCount && !ok;
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl p-3 shadow border ${
        ng
          ? 'border-red-300 dark:border-red-800'
          : isCount
          ? 'border-gray-200 dark:border-gray-700'
          : 'border-green-300 dark:border-green-800'
      }`}
    >
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p
        className={`font-bold mt-1 ${
          ng
            ? 'text-red-600 dark:text-red-400'
            : isCount
            ? 'text-gray-800 dark:text-white'
            : 'text-green-600 dark:text-green-400'
        }`}
      >
        {ok ? okLabel : failLabel || okLabel}
      </p>
    </div>
  );
}

function Modal({
  children,
  onClose,
  title,
}: {
  children: React.ReactNode;
  onClose: () => void;
  title: string;
}) {
  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <h2 className="text-lg font-bold dark:text-white">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none px-2"
          >
            ×
          </button>
        </div>
        <div className="overflow-auto p-4 flex-1">{children}</div>
      </div>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-medium mb-2 dark:text-gray-200">{title}</h4>
      <ul className="space-y-1">
        {items.map((it, i) => (
          <li
            key={i}
            className="text-sm dark:text-gray-300 p-2 bg-gray-50 dark:bg-gray-900/40 rounded"
          >
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

function WatchedCard({
  w,
  onChange,
  onRemove,
  onScan,
  onWriteIdea,
  onViewTasks,
}: {
  w: Watched;
  onChange: (updates: Partial<Watched>) => void;
  onRemove: () => void;
  onScan: () => void;
  onWriteIdea: () => void;
  onViewTasks: () => void;
}) {
  const [notes, setNotes] = useState(w.user_notes);
  const [tagInput, setTagInput] = useState('');
  const [interval, setIntervalH] = useState(w.interval_hours);

  const addTag = () => {
    const v = tagInput.trim();
    if (!v) return;
    if (w.tags.includes(v)) return;
    onChange({ tags: [...w.tags, v] });
    setTagInput('');
  };

  const removeTag = (t: string) => {
    onChange({ tags: w.tags.filter((x) => x !== t) });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={w.repo_url}
              target="_blank"
              rel="noreferrer"
              className="font-bold dark:text-white hover:underline truncate"
              dir="ltr"
            >
              {w.repo_full_name}
            </a>
            {w.private && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 dark:text-gray-200 rounded">
                🔒
              </span>
            )}
            {w.language && (
              <span className="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded">
                {w.language}
              </span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                w.autonomy_level === 'auto'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                  : w.autonomy_level === 'assist'
                  ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                  : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
              }`}
            >
              {w.autonomy_level}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
            {w.schedule_enabled ? (
              <span>⏰ هر {w.interval_hours} ساعت</span>
            ) : (
              <span>⏸ زمان‌بندی غیرفعال</span>
            )}
            {w.last_run_at && <span>آخرین: {new Date(w.last_run_at).toLocaleString('fa-IR')}</span>}
            {w.next_run_at && <span>بعدی: {new Date(w.next_run_at).toLocaleString('fa-IR')}</span>}
          </div>
        </div>
      </div>

      {/* یادداشت کاربر */}
      <div className="mb-3">
        <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
          📝 یادداشت من (هدف این پروژه چی بود؟)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={() => {
            if (notes !== w.user_notes) onChange({ user_notes: notes });
          }}
          rows={2}
          placeholder="مثلاً: «این پروژه برای ربات تلگرام برای مدیریت تسک‌های شخصی بود...»"
          className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
        />
      </div>

      {/* تگ‌ها */}
      <div className="mb-3">
        <div className="flex flex-wrap gap-1 mb-1">
          {w.tags.map((t) => (
            <span
              key={t}
              className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded flex items-center gap-1"
            >
              {t}
              <button onClick={() => removeTag(t)} className="hover:text-red-500">
                ×
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTag()}
            placeholder="تگ جدید (Enter)"
            className="flex-1 p-1.5 border rounded text-xs dark:bg-gray-700 dark:text-white dark:border-gray-600"
          />
          <button
            onClick={addTag}
            className="px-2 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded text-xs"
          >
            +
          </button>
        </div>
      </div>

      {/* تنظیمات */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1">سطح خودمختاری</span>
          <select
            value={w.autonomy_level}
            onChange={(e) => onChange({ autonomy_level: e.target.value as any })}
            className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          >
            <option value="manual">manual (فقط گزارش)</option>
            <option value="assist">assist (پیشنهاد)</option>
            <option value="auto">auto (اعمال)</option>
          </select>
        </label>
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1">بازه (ساعت)</span>
          <input
            type="number"
            min="1"
            value={interval}
            onChange={(e) => setIntervalH(parseFloat(e.target.value) || 24)}
            onBlur={() => {
              if (interval !== w.interval_hours) onChange({ interval_hours: interval });
            }}
            className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          />
        </label>
        <label className="text-xs flex items-center gap-2 mt-5">
          <input
            type="checkbox"
            checked={w.schedule_enabled}
            onChange={(e) => onChange({ schedule_enabled: e.target.checked })}
            className="w-4 h-4"
          />
          <span className="dark:text-gray-200">زمان‌بندی فعال</span>
        </label>
      </div>

      {w.autonomy_level === 'auto' && (
        <label className="flex items-center gap-2 mb-3 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs">
          <input
            type="checkbox"
            checked={w.allow_push}
            onChange={(e) => onChange({ allow_push: e.target.checked })}
            className="w-4 h-4"
          />
          <span className="dark:text-red-300">
            ⚠️ اجازهٔ صریح برای push/PR/issue توسط AI (در حالت auto لازم است)
          </span>
        </label>
      )}

      {/* اکشن‌ها */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={onScan}
          className="px-3 py-1.5 bg-cyan-500 text-white rounded text-sm hover:bg-cyan-600"
        >
          🔎 اسکن نیازها
        </button>
        <button
          onClick={onWriteIdea}
          className="px-3 py-1.5 bg-purple-500 text-white rounded text-sm hover:bg-purple-600"
        >
          💡 نوشتن ایده
        </button>
        <button
          onClick={onViewTasks}
          className="px-3 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
        >
          📋 تسک‌ها
        </button>
        <button
          onClick={onRemove}
          className="px-3 py-1.5 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300 rounded text-sm hover:bg-red-200 mr-auto"
        >
          🗑 حذف
        </button>
      </div>
    </div>
  );
}

function WatchedEditor({
  watched,
  onSave,
  onCancel,
}: {
  watched: Watched;
  onSave: (u: Partial<Watched>) => void;
  onCancel: () => void;
}) {
  const [data, setData] = useState({ ...watched });
  return (
    <div className="space-y-3">
      <textarea
        value={data.user_notes}
        onChange={(e) => setData({ ...data, user_notes: e.target.value })}
        rows={4}
        className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
        placeholder="یادداشت..."
      />
      <div className="flex gap-2">
        <button
          onClick={() => onSave(data)}
          className="flex-1 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          ذخیره
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded"
        >
          لغو
        </button>
      </div>
    </div>
  );
}
