'use client';

import { useState, useEffect, useMemo } from 'react';
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
  allow_create_issue?: boolean;
  scan_interval_hours?: number;
  last_run_at?: string | null;
  next_run_at?: string | null;
  last_scan_at?: string | null;
  next_scan_at?: string | null;
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

const KANBAN_COLUMNS: Array<{ id: string; label: string; color: string }> = [
  { id: 'suggested', label: '🤖 پیشنهاد', color: 'border-cyan-400' },
  { id: 'pending', label: '📥 در صف', color: 'border-yellow-400' },
  { id: 'running', label: '⏳ در حال اجرا', color: 'border-blue-400' },
  { id: 'awaiting_review', label: '👁 بازبینی', color: 'border-purple-400' },
  { id: 'done', label: '✅ انجام شده', color: 'border-green-400' },
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

type RepoSort = 'pushed_desc' | 'pushed_asc' | 'name' | 'stars';

export default function OversightPage() {
  const [tab, setTab] = useState<'watched' | 'repos' | 'ideas' | 'tasks' | 'reports'>('watched');

  const [status, setStatus] = useState<Status | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);

  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposSyncedAt, setReposSyncedAt] = useState<string | null>(null);
  const [reposLoading, setReposLoading] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');
  const [repoLangFilter, setRepoLangFilter] = useState('');
  const [repoVisibility, setRepoVisibility] = useState<'all' | 'public' | 'private'>('all');
  const [repoSort, setRepoSort] = useState<RepoSort>('pushed_desc');
  const [selectedRepoNames, setSelectedRepoNames] = useState<Set<string>>(new Set());

  const [watched, setWatched] = useState<Watched[]>([]);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskFilterStatus, setTaskFilterStatus] = useState<string>('all');
  const [taskFilterWatched, setTaskFilterWatched] = useState<string>('all');
  const [taskView, setTaskView] = useState<'list' | 'kanban'>('list');
  const [selectedSuggested, setSelectedSuggested] = useState<Set<string>>(new Set());
  const [viewingTask, setViewingTask] = useState<Task | null>(null);

  const [reports, setReports] = useState<Report[]>([]);
  const [reportStatusFilter, setReportStatusFilter] = useState<string>('all');
  const [reportWatchedFilter, setReportWatchedFilter] = useState<string>('all');
  const [reportSinceFilter, setReportSinceFilter] = useState<string>('');
  const [reportFlaggedOnly, setReportFlaggedOnly] = useState(false);
  const [viewingReport, setViewingReport] = useState<Report | null>(null);

  // Idea inbox
  const [idea, setIdea] = useState('');
  const [ideaWatchedIds, setIdeaWatchedIds] = useState<string[]>([]);
  const [ideaType, setIdeaType] = useState('idea');
  const [ideaPriority, setIdeaPriority] = useState('medium');
  const [ideaDeadline, setIdeaDeadline] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genPhase, setGenPhase] = useState('');
  const [genPct, setGenPct] = useState(0);
  const [previewPrompt, setPreviewPrompt] = useState<{ title: string; prompt: string } | null>(null);

  const [runningTaskIds, setRunningTaskIds] = useState<Set<string>>(new Set());

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
    if (typeof window === 'undefined') return;
    try {
      const saved = localStorage.getItem('oversight_models_multi');
      if (saved) {
        const arr = JSON.parse(saved);
        if (Array.isArray(arr)) setSelectedModelIds(arr);
      } else {
        const single = localStorage.getItem('oversight_model');
        if (single) setSelectedModelIds([single]);
      }
    } catch {}
  }, []);

  // پیشرفت زنده هنگام تولید
  useEffect(() => {
    if (!generating) {
      setGenPct(0);
      return;
    }
    const t = setInterval(() => {
      setGenPct((p) => (p < 88 ? p + 2 : p));
    }, 500);
    return () => clearInterval(t);
  }, [generating]);

  const saveModelChoice = (ids: string[]) => {
    setSelectedModelIds(ids);
    try {
      localStorage.setItem('oversight_models_multi', JSON.stringify(ids));
      // sync با تنظیمات بک‌اند
      fetch(`${API_BASE}/api/oversight/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ default_models: ids }),
      }).catch(() => {});
    } catch {}
  };

  const init = async () => {
    setLoading(true);
    try {
      const [statusRes, modelsRes, watchedRes, tasksRes, reportsRes] =
        await Promise.allSettled([
          fetch(`${API_BASE}/api/oversight/status`),
          fetch(`${API_BASE}/api/models/available`),
          fetch(`${API_BASE}/api/oversight/watched`),
          fetch(`${API_BASE}/api/oversight/tasks`),
          fetch(`${API_BASE}/api/oversight/reports?limit=300`),
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
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const reloadStatus = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/oversight/status`);
      if (r.ok) setStatus(await r.json());
    } catch {}
  };

  const reloadTasks = async () => {
    const r = await fetch(`${API_BASE}/api/oversight/tasks`);
    if (r.ok) {
      const data = await r.json();
      setTasks(data.items || []);
    }
  };

  const reloadReports = async () => {
    const r = await fetch(`${API_BASE}/api/oversight/reports?limit=300`);
    if (r.ok) {
      const data = await r.json();
      setReports(data.items || []);
    }
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
        setWatched((prev) => (prev.some((x) => x.id === w.id) ? prev : [...prev, w]));
        reloadStatus();
        return true;
      }
    } catch {}
    return false;
  };

  const watchSelected = async () => {
    const reposToAdd = repos.filter((r) => selectedRepoNames.has(r.full_name));
    let added = 0;
    for (const r of reposToAdd) {
      if (await addToWatch(r)) added++;
    }
    setSelectedRepoNames(new Set());
    showSuccess(`${added} پروژه به نظارت اضافه شد`);
    if (added > 0) setTab('watched');
  };

  const filteredRepos = useMemo(() => {
    let arr = repos.filter((r) => {
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
    arr = [...arr].sort((a, b) => {
      if (repoSort === 'pushed_desc') return (b.pushed_at || '').localeCompare(a.pushed_at || '');
      if (repoSort === 'pushed_asc') return (a.pushed_at || '').localeCompare(b.pushed_at || '');
      if (repoSort === 'name') return (a.full_name || '').localeCompare(b.full_name || '');
      if (repoSort === 'stars') return (b.stargazers_count || 0) - (a.stargazers_count || 0);
      return 0;
    });
    return arr;
  }, [repos, repoSearch, repoLangFilter, repoVisibility, repoSort]);

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
    showSuccess('اسکن شروع شد - چند لحظه صبر کنید...');
    try {
      const res = await fetch(`${API_BASE}/api/oversight/scan/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: selectedModelIds[0],
          model_ids: selectedModelIds.length > 0 ? selectedModelIds : undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(`${data.created_count} نیاز/پیشنهاد جدید شناسایی شد`);
        await reloadTasks();
        setTab('tasks');
        setTaskFilterStatus('suggested');
        setTaskFilterWatched(id);
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در اسکن');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const runAllPendingForWatched = async (id: string) => {
    showSuccess('در حال اجرای همهٔ تسک‌های pending...');
    try {
      const res = await fetch(`${API_BASE}/api/oversight/watched/${id}/run-now`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: selectedModelIds[0],
          model_ids: selectedModelIds.length > 1 ? selectedModelIds : undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(data.message || `${data.ran_count} تسک اجرا شد`);
        await reloadTasks();
        await reloadReports();
        await reloadStatus();
      } else {
        showError('خطا در اجرا');
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
    setGenPhase('AI در حال خواندن context پروژه...');
    setGenPct(8);
    try {
      // برای multi-project: یک پرامپت تولید می‌شود اما هنگام ذخیره برای هر پروژه یکی ساخته می‌شود
      const firstId = ideaWatchedIds[0] || null;
      setTimeout(() => setGenPhase('در حال ساخت پرامپت قدرتمند...'), 800);
      const res = await fetch(`${API_BASE}/api/oversight/tasks/from-idea`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea,
          watched_id: firstId,
          type: ideaType,
          priority: ideaPriority,
          model_id: selectedModelIds[0],
          model_ids: selectedModelIds.length > 1 ? selectedModelIds : undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewPrompt({ title: data.title, prompt: data.prompt });
        setGenPhase('پرامپت آماده شد');
        setGenPct(100);
        showSuccess('پرامپت تولید شد - بررسی و تأیید کنید');
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در تولید پرامپت');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setGenerating(false);
      setTimeout(() => setGenPhase(''), 1500);
    }
  };

  const savePromptAsTask = async () => {
    if (!previewPrompt) return;
    const targetIds = ideaWatchedIds.length ? ideaWatchedIds : [''];
    let created = 0;
    for (const wid of targetIds) {
      const w = watched.find((x) => x.id === wid);
      try {
        const res = await fetch(`${API_BASE}/api/oversight/tasks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            watched_id: wid || null,
            project_full_name: w?.repo_full_name || '',
            title: previewPrompt.title,
            prompt: previewPrompt.prompt,
            raw_idea: idea,
            type: ideaType,
            priority: ideaPriority,
            status: 'pending',
            deadline: ideaDeadline || null,
          }),
        });
        if (res.ok) {
          const t = await res.json();
          setTasks((prev) => [t, ...prev]);
          created++;
        }
      } catch {}
    }
    if (created > 0) {
      setIdea('');
      setIdeaDeadline('');
      setPreviewPrompt(null);
      showSuccess(`${created} تسک ساخته شد`);
      reloadStatus();
      setTab('tasks');
    } else {
      showError('هیچ تسکی ساخته نشد');
    }
  };

  const runTask = async (id: string) => {
    setRunningTaskIds((prev) => new Set(prev).add(id));
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, status: 'running' } : t)));
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: selectedModelIds[0],
          model_ids: selectedModelIds.length > 1 ? selectedModelIds : undefined,
        }),
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
        await reloadTasks();
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setRunningTaskIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
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
    } catch (e) {
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

  const bulkApproveSuggested = async () => {
    if (selectedSuggested.size === 0) return;
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/bulk-approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_ids: Array.from(selectedSuggested) }),
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(`${data.updated_count} پیشنهاد تأیید شد`);
        await reloadTasks();
        setSelectedSuggested(new Set());
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

  // ============================ Reports ============================

  const filteredReports = useMemo(() => {
    return reports.filter((r) => {
      if (reportStatusFilter !== 'all' && r.status !== reportStatusFilter) return false;
      if (reportWatchedFilter !== 'all' && r.watched_id !== reportWatchedFilter) return false;
      if (reportFlaggedOnly && !r.flagged) return false;
      if (reportSinceFilter && r.run_at < reportSinceFilter) return false;
      return true;
    });
  }, [reports, reportStatusFilter, reportWatchedFilter, reportFlaggedOnly, reportSinceFilter]);

  const markReport = async (
    reportId: string,
    updates: { read?: boolean; flagged?: boolean },
  ) => {
    const params = new URLSearchParams();
    if (updates.read !== undefined) params.set('read', String(updates.read));
    if (updates.flagged !== undefined) params.set('flagged', String(updates.flagged));
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/reports/${reportId}/mark?${params.toString()}`,
        { method: 'PATCH' },
      );
      if (res.ok) {
        const updated = await res.json();
        setReports((prev) => prev.map((r) => (r.id === reportId ? updated : r)));
        if (viewingReport?.id === reportId) setViewingReport(updated);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const exportReportMd = (r: Report) => {
    const lines: string[] = [];
    lines.push(`# گزارش oversight — ${r.project_full_name}`);
    lines.push(`- **تاریخ**: ${new Date(r.run_at).toLocaleString('fa-IR')}`);
    lines.push(`- **وضعیت**: \`${r.status}\``);
    lines.push(`- **اعتماد مدل**: ${Math.round((r.confidence_score || 0) * 100)}%`);
    if (r.model_id) lines.push(`- **مدل**: \`${r.model_id}\``);
    lines.push('');
    if (r.done_parts?.length) {
      lines.push('## ✅ انجام شده');
      r.done_parts.forEach((p) => lines.push(`- ${p}`));
      lines.push('');
    }
    if (r.remaining_parts?.length) {
      lines.push('## ⏳ باقی‌مانده');
      r.remaining_parts.forEach((p) => lines.push(`- ${p}`));
      lines.push('');
    }
    if (r.next_actions?.length) {
      lines.push('## 🎯 اقدامات بعدی');
      r.next_actions.forEach((p) => lines.push(`- ${p}`));
      lines.push('');
    }
    if (r.evidence && Object.keys(r.evidence).length > 0) {
      lines.push('## 🔗 شواهد');
      lines.push('```json');
      lines.push(JSON.stringify(r.evidence, null, 2));
      lines.push('```');
      lines.push('');
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-${r.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportReportJson = (r: Report) => {
    const blob = new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-${r.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ============================ Helpers ============================

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

  const watchedNameById = (id?: string | null) => {
    if (!id) return '';
    return watched.find((w) => w.id === id)?.repo_full_name || '';
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

        {/* وضعیت */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
          <StatusCard label="GitHub" ok={status?.github_token} okLabel="متصل" failLabel="توکن ندارد" />
          <StatusCard label="Render" ok={status?.render_token} okLabel="متصل" failLabel="توکن ندارد" />
          <StatusCard label="پروژه‌های تحت نظارت" ok okLabel={`${status?.watched_count ?? 0} پروژه`} isCount />
          <StatusCard label="تسک‌ها" ok okLabel={`${status?.tasks_count ?? 0} تسک`} isCount />
          <StatusCard label="گزارش‌ها" ok okLabel={`${status?.reports_count ?? 0} گزارش`} isCount />
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

        {/* انتخابگر مدل (multi-select) */}
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl shadow">
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <h3 className="font-bold dark:text-white">🤖 مدل‌های نظارت (انتخاب چندتایی)</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {models.length} مدل فعال — انتخاب چند مدل = consensus بین آنها
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {models.length === 0 ? (
              <Link
                href="/settings"
                className="text-sm text-blue-500 hover:underline"
              >
                هیچ مدلی فعال نیست — به تنظیمات بروید
              </Link>
            ) : (
              models.map((m) => {
                const checked = selectedModelIds.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      const next = checked
                        ? selectedModelIds.filter((x) => x !== m.id)
                        : [...selectedModelIds, m.id];
                      saveModelChoice(next);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition ${
                      checked
                        ? 'bg-blue-500 text-white border-blue-500'
                        : 'bg-gray-50 dark:bg-gray-700 dark:text-gray-200 border-gray-200 dark:border-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {checked ? '✓ ' : ''}
                    {m.name} {m.provider ? <span className="opacity-70 text-xs">· {m.provider}</span> : null}
                  </button>
                );
              })
            )}
          </div>
          {selectedModelIds.length === 0 && models.length > 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              هیچ مدلی انتخاب نشده — اولین مدل موجود به‌طور خودکار استفاده می‌شود.
            </p>
          )}
          {selectedModelIds.length > 1 && (
            <p className="text-xs text-purple-600 dark:text-purple-300 mt-2">
              🤝 حالت consensus فعال — همهٔ مدل‌ها همزمان اجرا می‌شوند و نتیجه با بالاترین اعتماد انتخاب می‌شود.
            </p>
          )}
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
                  onRunNow={() => runAllPendingForWatched(w.id)}
                  onWriteIdea={() => {
                    setIdeaWatchedIds([w.id]);
                    setTab('ideas');
                  }}
                  onViewTasks={() => {
                    setTaskFilterWatched(w.id);
                    setTaskFilterStatus('all');
                    setTab('tasks');
                  }}
                  onViewReports={() => {
                    setReportWatchedFilter(w.id);
                    setReportStatusFilter('all');
                    setTab('reports');
                  }}
                />
              ))
            )}
          </div>
        ) : tab === 'repos' ? (
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
              <div className="flex gap-2">
                {selectedRepoNames.size > 0 && (
                  <button
                    onClick={watchSelected}
                    className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
                  >
                    + افزودن گروهی ({selectedRepoNames.size})
                  </button>
                )}
                <button
                  onClick={loadRepos}
                  disabled={reposLoading || !status?.github_token}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  {reposLoading ? '⏳ در حال بارگذاری...' : '🔄 بارگذاری از GitHub'}
                </button>
              </div>
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
                  value={repoSort}
                  onChange={(e) => setRepoSort(e.target.value as RepoSort)}
                  className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="pushed_desc">📅 جدیدترین push</option>
                  <option value="pushed_asc">📅 قدیمی‌ترین push</option>
                  <option value="name">🔤 الفبایی</option>
                  <option value="stars">⭐ ستاره</option>
                </select>
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
                  const selected = selectedRepoNames.has(r.full_name);
                  return (
                    <div
                      key={r.id}
                      className={`p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border-2 transition ${
                        selected
                          ? 'border-purple-400 dark:border-purple-500'
                          : 'border-transparent hover:border-blue-300 dark:hover:border-blue-700'
                      }`}
                    >
                      <div className="flex items-start gap-2 mb-2">
                        {!watching && (
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={(e) => {
                              const next = new Set(selectedRepoNames);
                              if (e.target.checked) next.add(r.full_name);
                              else next.delete(r.full_name);
                              setSelectedRepoNames(next);
                            }}
                            className="mt-1 w-4 h-4"
                          />
                        )}
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
                        onClick={async () => {
                          if (!watching) {
                            await addToWatch(r);
                            showSuccess('اضافه شد');
                          }
                        }}
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
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold mb-4 dark:text-white">💡 ایده / مشکل / درخواست</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              هر چه به ذهنت می‌رسد بنویس - AI آن را به یک پرامپت قدرتمند با ساختار «هدف /
              context / مراحل / معیار پذیرش / خروجی» تبدیل می‌کند.
            </p>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              <div>
                <label className="block text-xs mb-1 dark:text-gray-300">پروژه‌ها (چندتایی)</label>
                <select
                  multiple
                  value={ideaWatchedIds}
                  onChange={(e) => {
                    const opts = Array.from(e.target.selectedOptions).map((o) => o.value);
                    setIdeaWatchedIds(opts);
                  }}
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 h-24"
                >
                  {watched.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.repo_full_name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-1">Ctrl/Cmd برای انتخاب چندتایی</p>
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
              <div>
                <label className="block text-xs mb-1 dark:text-gray-300">Deadline (اختیاری)</label>
                <input
                  type="date"
                  value={ideaDeadline}
                  onChange={(e) => setIdeaDeadline(e.target.value)}
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                />
              </div>
            </div>

            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              rows={6}
              placeholder="مثلاً: «authentication این پروژه ضعیفه. JWT اضافه کن، rate limit بذار، endpoint های login/register رو امن کن، اگه کاربر سه بار اشتباه پسورد بزنه قفل بشه...»"
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 mb-3"
            />

            {/* نوار پیشرفت */}
            {generating && (
              <div className="mb-3 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-purple-700 dark:text-purple-300">{genPhase}</span>
                  <span className="text-gray-500">{Math.round(genPct)}%</span>
                </div>
                <div className="w-full h-2 bg-purple-100 dark:bg-purple-900/40 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all duration-500"
                    style={{ width: `${genPct}%` }}
                  />
                </div>
              </div>
            )}

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
                {ideaWatchedIds.length > 1 && (
                  <p className="text-xs text-purple-700 dark:text-purple-300 mt-2">
                    ℹ️ هنگام ذخیره، {ideaWatchedIds.length} تسک جداگانه (یکی برای هر پروژه) ساخته می‌شود.
                  </p>
                )}
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={savePromptAsTask}
                    className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    ✓ ذخیره به‌عنوان تسک
                    {ideaWatchedIds.length > 1 ? ` (×${ideaWatchedIds.length})` : ''}
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
          <TasksPanel
            tasks={tasks}
            filteredTasks={filteredTasks}
            watched={watched}
            taskFilterStatus={taskFilterStatus}
            setTaskFilterStatus={setTaskFilterStatus}
            taskFilterWatched={taskFilterWatched}
            setTaskFilterWatched={setTaskFilterWatched}
            taskView={taskView}
            setTaskView={setTaskView}
            selectedSuggested={selectedSuggested}
            setSelectedSuggested={setSelectedSuggested}
            bulkApprove={bulkApproveSuggested}
            runningTaskIds={runningTaskIds}
            onRun={runTask}
            onUpdate={updateTask}
            onDelete={deleteTask}
            onView={(t) => setViewingTask(t)}
            fmtDate={fmtDate}
          />
        ) : (
          <ReportsPanel
            reports={filteredReports}
            allCount={reports.length}
            watched={watched}
            reportStatusFilter={reportStatusFilter}
            setReportStatusFilter={setReportStatusFilter}
            reportWatchedFilter={reportWatchedFilter}
            setReportWatchedFilter={setReportWatchedFilter}
            reportSinceFilter={reportSinceFilter}
            setReportSinceFilter={setReportSinceFilter}
            reportFlaggedOnly={reportFlaggedOnly}
            setReportFlaggedOnly={setReportFlaggedOnly}
            onView={(r) => setViewingReport(r)}
            onMark={markReport}
            fmtDate={fmtDate}
          />
        )}

        {/* مودال تسک */}
        {viewingTask && (
          <Modal onClose={() => setViewingTask(null)} title="📋 جزئیات تسک">
            <div className="space-y-3">
              <div>
                <h4 className="text-xs text-gray-500 mb-1">عنوان</h4>
                <p className="font-medium dark:text-white">{viewingTask.title}</p>
              </div>
              {viewingTask.project_full_name && (
                <p className="text-xs text-gray-500 dark:text-gray-400" dir="ltr">
                  {viewingTask.project_full_name}
                </p>
              )}
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
                {viewingReport.model_id && (
                  <span className="text-xs text-gray-500" dir="ltr">
                    {viewingReport.model_id}
                  </span>
                )}
                <span className="text-xs text-gray-500 mr-auto">
                  {fmtDate(viewingReport.run_at)}
                </span>
              </div>

              {viewingReport.evidence?.github_issue && (
                <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded text-sm">
                  <a
                    href={viewingReport.evidence.github_issue.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-700 dark:text-blue-300 hover:underline"
                  >
                    🔗 GitHub Issue #{viewingReport.evidence.github_issue.number} ساخته شد
                  </a>
                </div>
              )}

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
                <details>
                  <summary className="cursor-pointer text-sm font-medium dark:text-gray-200">
                    🔗 شواهد (JSON)
                  </summary>
                  <pre className="text-xs p-3 bg-gray-50 dark:bg-gray-900 dark:text-gray-200 rounded-lg overflow-auto mt-2" dir="ltr">
                    {JSON.stringify(viewingReport.evidence, null, 2)}
                  </pre>
                </details>
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

              <div className="flex gap-2 pt-3 flex-wrap">
                <button
                  onClick={() => exportReportJson(viewingReport)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
                >
                  ↓ JSON
                </button>
                <button
                  onClick={() => exportReportMd(viewingReport)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
                >
                  ↓ Markdown
                </button>
                <button
                  onClick={() =>
                    markReport(viewingReport.id, { read: !viewingReport.read })
                  }
                  className={`px-4 py-2 rounded-lg text-sm ${
                    viewingReport.read
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                      : 'bg-gray-200 dark:bg-gray-700 dark:text-white'
                  }`}
                >
                  {viewingReport.read ? '✓ خوانده شد' : '👁 علامت خوانده'}
                </button>
                <button
                  onClick={() =>
                    markReport(viewingReport.id, { flagged: !viewingReport.flagged })
                  }
                  className={`px-4 py-2 rounded-lg text-sm ${
                    viewingReport.flagged
                      ? 'bg-yellow-200 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300'
                      : 'bg-gray-200 dark:bg-gray-700 dark:text-white'
                  }`}
                >
                  {viewingReport.flagged ? '⚑ نشان شده' : '⚐ علامت پیگیری'}
                </button>
              </div>
            </div>
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
  onRunNow,
  onWriteIdea,
  onViewTasks,
  onViewReports,
}: {
  w: Watched;
  onChange: (updates: Partial<Watched>) => void;
  onRemove: () => void;
  onScan: () => void;
  onRunNow: () => void;
  onWriteIdea: () => void;
  onViewTasks: () => void;
  onViewReports: () => void;
}) {
  const [notes, setNotes] = useState(w.user_notes);
  const [tagInput, setTagInput] = useState('');
  const [intervalH, setIntervalH] = useState(w.interval_hours);
  const [scanH, setScanH] = useState(w.scan_interval_hours ?? 168);

  useEffect(() => {
    setNotes(w.user_notes);
    setIntervalH(w.interval_hours);
    setScanH(w.scan_interval_hours ?? 168);
  }, [w.id]);

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
            {w.last_scan_at && <span>scan: {new Date(w.last_scan_at).toLocaleString('fa-IR')}</span>}
          </div>
        </div>
      </div>

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
          placeholder="مثلاً: «این پروژه برای ربات تلگرام مدیریت تسک‌های شخصی بود...»"
          className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
        />
      </div>

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

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1">سطح خودمختاری</span>
          <select
            value={w.autonomy_level}
            onChange={(e) => onChange({ autonomy_level: e.target.value as any })}
            className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          >
            <option value="manual">manual</option>
            <option value="assist">assist</option>
            <option value="auto">auto</option>
          </select>
        </label>
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1">بازه run (ساعت)</span>
          <input
            type="number"
            min="1"
            value={intervalH}
            onChange={(e) => setIntervalH(parseFloat(e.target.value) || 24)}
            onBlur={() => {
              if (intervalH !== w.interval_hours) onChange({ interval_hours: intervalH });
            }}
            className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          />
        </label>
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1">بازه scan (ساعت)</span>
          <input
            type="number"
            min="1"
            value={scanH}
            onChange={(e) => setScanH(parseFloat(e.target.value) || 168)}
            onBlur={() => {
              if (scanH !== (w.scan_interval_hours ?? 168))
                onChange({ scan_interval_hours: scanH });
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

      <div className="flex flex-col sm:flex-row gap-2 mb-3">
        <label className="flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs flex-1">
          <input
            type="checkbox"
            checked={!!w.allow_create_issue}
            onChange={(e) => onChange({ allow_create_issue: e.target.checked })}
            className="w-4 h-4"
          />
          <span className="dark:text-blue-300">
            اجازهٔ ساخت GitHub Issue پس از هر اجرا
          </span>
        </label>
        {w.autonomy_level === 'auto' && (
          <label className="flex items-center gap-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs flex-1">
            <input
              type="checkbox"
              checked={w.allow_push}
              onChange={(e) => onChange({ allow_push: e.target.checked })}
              className="w-4 h-4"
            />
            <span className="dark:text-red-300">
              ⚠️ اجازهٔ صریح push/PR در حالت auto
            </span>
          </label>
        )}
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={onRunNow}
          className="px-3 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
        >
          ▶ بررسی فوری
        </button>
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
          className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 dark:text-white rounded text-sm hover:bg-gray-300"
        >
          📋 تسک‌ها
        </button>
        <button
          onClick={onViewReports}
          className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 dark:text-white rounded text-sm hover:bg-gray-300"
        >
          📊 گزارش‌ها
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

function TasksPanel({
  tasks,
  filteredTasks,
  watched,
  taskFilterStatus,
  setTaskFilterStatus,
  taskFilterWatched,
  setTaskFilterWatched,
  taskView,
  setTaskView,
  selectedSuggested,
  setSelectedSuggested,
  bulkApprove,
  runningTaskIds,
  onRun,
  onUpdate,
  onDelete,
  onView,
  fmtDate,
}: {
  tasks: Task[];
  filteredTasks: Task[];
  watched: Watched[];
  taskFilterStatus: string;
  setTaskFilterStatus: (s: string) => void;
  taskFilterWatched: string;
  setTaskFilterWatched: (s: string) => void;
  taskView: 'list' | 'kanban';
  setTaskView: (v: 'list' | 'kanban') => void;
  selectedSuggested: Set<string>;
  setSelectedSuggested: (s: Set<string>) => void;
  bulkApprove: () => void;
  runningTaskIds: Set<string>;
  onRun: (id: string) => void;
  onUpdate: (id: string, u: Partial<Task>) => void;
  onDelete: (id: string) => void;
  onView: (t: Task) => void;
  fmtDate: (d?: string | null) => string;
}) {
  const tasksByCol = useMemo(() => {
    const map: Record<string, Task[]> = {};
    KANBAN_COLUMNS.forEach((c) => (map[c.id] = []));
    filteredTasks.forEach((t) => {
      if (map[t.status]) map[t.status].push(t);
    });
    return map;
  }, [filteredTasks]);

  const renderTaskRow = (t: Task) => {
    const statusInfo = TASK_STATUSES.find((s) => s.id === t.status);
    const isRunning = runningTaskIds.has(t.id) || t.status === 'running';
    return (
      <div
        key={t.id}
        className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-transparent hover:border-blue-300 dark:hover:border-blue-700"
      >
        <div className="flex items-start justify-between gap-2 mb-2 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              {t.status === 'suggested' && (
                <input
                  type="checkbox"
                  checked={selectedSuggested.has(t.id)}
                  onChange={(e) => {
                    const next = new Set(selectedSuggested);
                    if (e.target.checked) next.add(t.id);
                    else next.delete(t.id);
                    setSelectedSuggested(next);
                  }}
                  className="w-4 h-4"
                />
              )}
              <span className="text-lg">{TYPE_ICONS[t.type] || '📌'}</span>
              <button
                onClick={() => onView(t)}
                className="font-medium dark:text-white text-right hover:underline"
              >
                {t.title}
              </button>
              <span className={`text-xs px-2 py-0.5 rounded ${statusInfo?.color || ''}`}>
                {statusInfo?.label || t.status}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${PRIORITY_COLORS[t.priority] || ''}`}>
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
              {t.deadline && <span>📅 deadline: {t.deadline}</span>}
            </div>
          </div>
          <div className="flex gap-1 flex-wrap">
            <button
              onClick={() => onRun(t.id)}
              disabled={isRunning}
              className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600 disabled:opacity-50"
            >
              {isRunning ? '⏳' : '▶'} اجرا
            </button>
            {t.status === 'suggested' && (
              <button
                onClick={() => onUpdate(t.id, { status: 'pending' })}
                className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
              >
                ✓ تأیید
              </button>
            )}
            <button
              onClick={() => onView(t)}
              className="px-3 py-1 bg-gray-200 dark:bg-gray-600 dark:text-white rounded text-xs hover:bg-gray-300"
            >
              👁
            </button>
            <button
              onClick={() => onDelete(t.id)}
              className="px-3 py-1 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300 rounded text-xs hover:bg-red-200"
            >
              🗑
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-bold dark:text-white">📋 صف تسک‌ها</h2>
        <div className="flex gap-2 flex-wrap">
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setTaskView('list')}
              className={`px-3 py-1 rounded text-sm ${
                taskView === 'list' ? 'bg-blue-500 text-white' : 'dark:text-gray-300'
              }`}
            >
              📋 لیست
            </button>
            <button
              onClick={() => setTaskView('kanban')}
              className={`px-3 py-1 rounded text-sm ${
                taskView === 'kanban' ? 'bg-blue-500 text-white' : 'dark:text-gray-300'
              }`}
            >
              📊 Kanban
            </button>
          </div>
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

      {/* Bulk approve bar */}
      {selectedSuggested.size > 0 && (
        <div className="mb-4 p-3 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded-lg flex items-center justify-between flex-wrap gap-2">
          <span className="text-sm dark:text-cyan-200">
            {selectedSuggested.size} پیشنهاد انتخاب شده
          </span>
          <div className="flex gap-2">
            <button
              onClick={bulkApprove}
              className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600"
            >
              ✓ تأیید گروهی → pending
            </button>
            <button
              onClick={() => setSelectedSuggested(new Set())}
              className="px-3 py-1 bg-gray-300 dark:bg-gray-600 dark:text-white rounded text-sm"
            >
              لغو انتخاب
            </button>
          </div>
        </div>
      )}

      {filteredTasks.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <div className="text-5xl mb-3">📋</div>
          <p>تسکی نیست</p>
        </div>
      ) : taskView === 'list' ? (
        <div className="space-y-3">{filteredTasks.map(renderTaskRow)}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3 overflow-x-auto">
          {KANBAN_COLUMNS.map((col) => (
            <div
              key={col.id}
              className={`min-w-[220px] bg-gray-50 dark:bg-gray-900/40 rounded-lg p-3 border-t-4 ${col.color}`}
            >
              <div className="font-bold text-sm dark:text-white mb-2 flex items-center justify-between">
                <span>{col.label}</span>
                <span className="text-xs text-gray-500">{tasksByCol[col.id].length}</span>
              </div>
              <div className="space-y-2">
                {tasksByCol[col.id].length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-4">خالی</p>
                ) : (
                  tasksByCol[col.id].map((t) => (
                    <button
                      key={t.id}
                      onClick={() => onView(t)}
                      className="w-full text-right p-2 bg-white dark:bg-gray-800 rounded hover:bg-blue-50 dark:hover:bg-gray-700 text-xs"
                    >
                      <div className="flex items-center gap-1 mb-1 flex-wrap">
                        <span>{TYPE_ICONS[t.type] || '📌'}</span>
                        <span className="font-medium dark:text-white truncate flex-1">
                          {t.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 flex-wrap">
                        <span
                          className={`text-[10px] px-1 rounded ${PRIORITY_COLORS[t.priority] || ''}`}
                        >
                          {t.priority}
                        </span>
                        {t.runs_count !== undefined && t.runs_count > 0 && (
                          <span className="text-[10px] text-gray-500">×{t.runs_count}</span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReportsPanel({
  reports,
  allCount,
  watched,
  reportStatusFilter,
  setReportStatusFilter,
  reportWatchedFilter,
  setReportWatchedFilter,
  reportSinceFilter,
  setReportSinceFilter,
  reportFlaggedOnly,
  setReportFlaggedOnly,
  onView,
  onMark,
  fmtDate,
}: {
  reports: Report[];
  allCount: number;
  watched: Watched[];
  reportStatusFilter: string;
  setReportStatusFilter: (s: string) => void;
  reportWatchedFilter: string;
  setReportWatchedFilter: (s: string) => void;
  reportSinceFilter: string;
  setReportSinceFilter: (s: string) => void;
  reportFlaggedOnly: boolean;
  setReportFlaggedOnly: (v: boolean) => void;
  onView: (r: Report) => void;
  onMark: (id: string, updates: { read?: boolean; flagged?: boolean }) => void;
  fmtDate: (d?: string | null) => string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h2 className="font-bold dark:text-white">
          📊 گزارش‌ها{' '}
          <span className="text-xs text-gray-500">
            ({reports.length} از {allCount})
          </span>
        </h2>
        <div className="flex gap-2 flex-wrap">
          <select
            value={reportStatusFilter}
            onChange={(e) => setReportStatusFilter(e.target.value)}
            className="p-2 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          >
            <option value="all">همه وضعیت‌ها</option>
            <option value="done">done</option>
            <option value="partial">partial</option>
            <option value="not_done">not_done</option>
            <option value="error">error</option>
          </select>
          <select
            value={reportWatchedFilter}
            onChange={(e) => setReportWatchedFilter(e.target.value)}
            className="p-2 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          >
            <option value="all">همه پروژه‌ها</option>
            {watched.map((w) => (
              <option key={w.id} value={w.id}>
                {w.repo_full_name}
              </option>
            ))}
          </select>
          <input
            type="datetime-local"
            value={reportSinceFilter ? reportSinceFilter.slice(0, 16) : ''}
            onChange={(e) => setReportSinceFilter(e.target.value ? e.target.value : '')}
            className="p-2 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
            title="از تاریخ"
          />
          <label className="flex items-center gap-1 text-sm dark:text-gray-300">
            <input
              type="checkbox"
              checked={reportFlaggedOnly}
              onChange={(e) => setReportFlaggedOnly(e.target.checked)}
              className="w-4 h-4"
            />
            ⚑ فقط نشان‌شده
          </label>
        </div>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <div className="text-5xl mb-3">📊</div>
          <p>گزارشی پیدا نشد</p>
        </div>
      ) : (
        <div className="space-y-2">
          {reports.map((r) => (
            <div
              key={r.id}
              className={`flex items-center gap-2 p-3 rounded-lg transition border ${
                r.read
                  ? 'bg-gray-50 dark:bg-gray-700/30 border-transparent'
                  : 'bg-blue-50/40 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900/40'
              } hover:border-blue-300 dark:hover:border-blue-700`}
            >
              <button
                onClick={() => onView(r)}
                className="flex-1 text-right flex items-center gap-2 flex-wrap"
              >
                <span
                  className={`text-xs px-2 py-0.5 rounded ${
                    r.status === 'done'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                      : r.status === 'partial'
                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                      : r.status === 'not_done'
                      ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                  }`}
                >
                  {r.status}
                </span>
                <span className="dark:text-gray-200 text-sm" dir="ltr">
                  {r.project_full_name}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  ⏱ {fmtDate(r.run_at)}
                </span>
                <span className="text-xs text-gray-500 mr-auto">
                  اعتماد: {Math.round((r.confidence_score || 0) * 100)}%
                </span>
              </button>
              <button
                onClick={() => onMark(r.id, { flagged: !r.flagged })}
                className={`text-lg px-1 ${r.flagged ? 'text-yellow-500' : 'text-gray-400 hover:text-yellow-500'}`}
                title={r.flagged ? 'لغو نشان' : 'نشان برای پیگیری'}
              >
                {r.flagged ? '⚑' : '⚐'}
              </button>
              {!r.read && (
                <button
                  onClick={() => onMark(r.id, { read: true })}
                  className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200"
                >
                  ✓ خواندم
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
