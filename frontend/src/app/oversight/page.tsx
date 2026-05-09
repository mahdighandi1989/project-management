'use client';

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
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
  verify_interval_hours?: number;
  default_execution_mode?: 'manual' | 'auto_via_projects_page' | 'auto_via_pr';
  verify_only_mode?: boolean;
  confirmation_streak_required?: number;
  max_apply_retries?: number;
  auto_create_pr_instead_of_commit?: boolean;
  notify_user_before_apply?: boolean;
  // 🆕 (commit 2.3) عمق scan + criteria weights — مهاجرت از Health
  scan_depth?: 'quick' | 'standard' | 'deep' | 'thorough';
  scan_criteria_weights?: { security?: number; quality?: number; tests?: number; completeness?: number };
  last_run_at?: string | null;
  next_run_at?: string | null;
  last_scan_at?: string | null;
  next_scan_at?: string | null;
  last_verify_at?: string | null;
  next_verify_at?: string | null;
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
  execution_mode?: 'manual' | 'auto_via_projects_page' | 'auto_via_pr';
  verification_status?: string;
  verification_history?: Array<{
    report_id: string;
    verified_at: string;
    status: string;
    triggered_by?: string;
    summary?: string;
  }>;
  manually_marked_applied_at?: string | null;
  last_verified_at?: string | null;
  confirmation_streak?: number;
  target_files?: string[];
  acceptance_criteria?: string[];
  applied_evidence?: {
    pr_url?: string;
    pr_branch?: string;
    files_committed?: string[];
    model_ids?: string[];
    executed_via?: string;
    executed_at?: string;
    action_plan_summary?: string;
    [key: string]: any;
  };
  // 🆕 follow-up prompt — وقتی verify نتیجهٔ partial/not_done داد
  followup_prompt?: string;
  followup_generated_at?: string | null;
  followup_target_locations?: Array<{path: string; lines?: string; symbol?: string; snippet?: string; note?: string}>;
  followup_acceptance_criteria?: string[];
  followup_round?: number;
  last_verification_report_id?: string | null;
}

interface Report {
  id: string;
  task_id: string;
  watched_id?: string | null;
  project_full_name: string;
  run_at: string;
  status: 'done' | 'partial' | 'not_done' | 'error' | 'regressed';
  done_parts: string[];
  remaining_parts: string[];
  evidence: Record<string, any>;
  next_actions: string[];
  confidence_score: number;
  raw_response?: string;
  model_id?: string;
  read?: boolean;
  flagged?: boolean;
  user_goal?: string;
  touched_codex?: Record<string, any>;
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
  const [tab, setTab] = useState<'watched' | 'repos' | 'ideas' | 'tasks' | 'reports' | 'project_tasks' | 'health'>('watched');

  // 🆕 تب «🏥 سلامت پروژه» — مهاجرت از Health analysis در /projects
  type HealthSubTab = 'overview' | 'files' | 'security' | 'coverage' | 'validation' | 'docs';
  const [selectedHealthWatchedId, setSelectedHealthWatchedId] = useState<string>('');
  const [healthSubTab, setHealthSubTab] = useState<HealthSubTab>('overview');
  const [healthSummaries, setHealthSummaries] = useState<{
    pass_summaries?: {
      health_summary?: any;
      file_health_map?: Record<string, any>;
      security_summary?: any;
      coverage_summary?: any;
    };
    findings_count?: number;
    tasks_created_count?: number;
    ran_at?: string;
    passes_run?: number;
  } | null>(null);
  const [healthChainStatus, setHealthChainStatus] = useState<any | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthSelectedFile, setHealthSelectedFile] = useState<string | null>(null);

  // 🆕 (commit 2.2) state برای روadmap/README/ideal_state
  const [healthRoadmap, setHealthRoadmap] = useState<{
    roadmap_markdown?: string;
    ideal_state?: string;
    phases?: Array<{name?: string; eta?: string; items?: Array<{text?: string; completed?: boolean; priority?: string}>}>;
    generated_at?: string;
    updated_at?: string;
  } | null>(null);
  const [healthReadme, setHealthReadme] = useState<{
    readme_markdown?: string;
    generated_at?: string;
    updated_at?: string;
  } | null>(null);
  const [healthRoadmapEditing, setHealthRoadmapEditing] = useState(false);
  const [healthRoadmapDraft, setHealthRoadmapDraft] = useState({ markdown: '', ideal: '' });
  const [healthReadmeEditing, setHealthReadmeEditing] = useState(false);
  const [healthReadmeDraft, setHealthReadmeDraft] = useState('');
  const [healthDocsLoading, setHealthDocsLoading] = useState<string>('');  // 'roadmap' | 'readme' | ''

  const loadHealthDocs = useCallback(async (watchedId: string) => {
    if (!watchedId) return;
    try {
      const [rm, rd] = await Promise.all([
        fetch(`${API_BASE}/api/oversight/codex/${encodeURIComponent(watchedId)}/roadmap`),
        fetch(`${API_BASE}/api/oversight/codex/${encodeURIComponent(watchedId)}/readme`),
      ]);
      setHealthRoadmap(rm.ok ? await rm.json() : null);
      setHealthReadme(rd.ok ? await rd.json() : null);
    } catch (e) { /* non-critical */ }
  }, []);

  const generateRoadmap = useCallback(async () => {
    if (!selectedHealthWatchedId) return;
    setHealthDocsLoading('roadmap');
    try {
      // model_id را undefined می‌فرستیم تا backend default را انتخاب کند
      // (selectedModelIds در ادامهٔ component تعریف شده ولی این callback
      // قبل از آن render می‌شود؛ برای جلوگیری از use-before-declaration،
      // backend خود model را پیدا می‌کند)
      const res = await fetch(
        `${API_BASE}/api/oversight/codex/${encodeURIComponent(selectedHealthWatchedId)}/generate-roadmap`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tone: 'professional' }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setHealthRoadmap(data);
      } else {
        alert(`خطا در تولید روadmap: ${await res.text().catch(() => '')}`);
      }
    } catch (e: any) {
      alert(`خطا: ${e?.message}`);
    } finally {
      setHealthDocsLoading('');
    }
  }, [selectedHealthWatchedId]);

  const generateReadme = useCallback(async () => {
    if (!selectedHealthWatchedId) return;
    setHealthDocsLoading('readme');
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/codex/${encodeURIComponent(selectedHealthWatchedId)}/generate-readme`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setHealthReadme(data);
      } else {
        alert(`خطا در تولید README: ${await res.text().catch(() => '')}`);
      }
    } catch (e: any) {
      alert(`خطا: ${e?.message}`);
    } finally {
      setHealthDocsLoading('');
    }
  }, [selectedHealthWatchedId]);

  const saveRoadmapManual = useCallback(async () => {
    if (!selectedHealthWatchedId) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/codex/${encodeURIComponent(selectedHealthWatchedId)}/roadmap`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            roadmap_markdown: healthRoadmapDraft.markdown,
            ideal_state: healthRoadmapDraft.ideal,
          }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setHealthRoadmap(data);
        setHealthRoadmapEditing(false);
      }
    } catch (e) { /* non-critical */ }
  }, [selectedHealthWatchedId, healthRoadmapDraft]);

  const saveReadmeManual = useCallback(async () => {
    if (!selectedHealthWatchedId) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/codex/${encodeURIComponent(selectedHealthWatchedId)}/readme`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ readme_markdown: healthReadmeDraft }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setHealthReadme(data);
        setHealthReadmeEditing(false);
      }
    } catch (e) { /* non-critical */ }
  }, [selectedHealthWatchedId, healthReadmeDraft]);

  const toggleRoadmapItemHandler = useCallback(async (phaseIdx: number, itemIdx: number) => {
    if (!selectedHealthWatchedId) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/codex/${encodeURIComponent(selectedHealthWatchedId)}/roadmap/items/${phaseIdx}:${itemIdx}`,
        { method: 'PATCH' }
      );
      if (res.ok) {
        const data = await res.json();
        setHealthRoadmap(data);
      }
    } catch (e) { /* non-critical */ }
  }, [selectedHealthWatchedId]);

  const downloadReadme = useCallback(() => {
    const md = healthReadme?.readme_markdown || '';
    if (!md) return;
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `README_${selectedHealthWatchedId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [healthReadme, selectedHealthWatchedId]);

  const loadHealthData = useCallback(async (watchedId: string) => {
    if (!watchedId) return;
    setHealthLoading(true);
    setHealthError(null);
    try {
      // fetch موازی سه endpoint
      const [summariesRes, chainRes] = await Promise.all([
        fetch(`${API_BASE}/api/oversight/scan/${encodeURIComponent(watchedId)}/summaries`),
        fetch(`${API_BASE}/api/oversight/watched/${encodeURIComponent(watchedId)}/chain-status`),
      ]);
      const summaries = summariesRes.ok ? await summariesRes.json() : null;
      const chain = chainRes.ok ? await chainRes.json() : null;
      setHealthSummaries(summaries);
      setHealthChainStatus(chain);
    } catch (e: any) {
      setHealthError(e?.message || 'خطا در بارگذاری data سلامت');
    } finally {
      setHealthLoading(false);
    }
  }, []);

  // وقتی selectedHealthWatchedId تغییر می‌کند، fresh load
  // (auto-select effect در ادامه — بعد از تعریف watched state)
  useEffect(() => {
    if (tab === 'health' && selectedHealthWatchedId) {
      loadHealthData(selectedHealthWatchedId);
      loadHealthDocs(selectedHealthWatchedId);
    }
  }, [tab, selectedHealthWatchedId, loadHealthData, loadHealthDocs]);

  // 🔗 External project tasks bridge — تسک‌های /projects که در /oversight نمایش داده می‌شوند
  const [externalTasks, setExternalTasks] = useState<Array<{
    id: string;
    source: string;
    origin_project_id: string;
    origin_project_name: string;
    origin_field_id: string;
    project_full_name: string;
    title: string;
    type: string;
    priority: string;
    status: string;
    prompt: string;
    target_files: string[];
    target_locations: Array<{path: string}>;
    external_prompt: string;
    action_type: string;
    last_run_at?: string;
    next_run_at?: string;
    created_at?: string;
    field_type?: string;
  }>>([]);
  const [externalTasksLoading, setExternalTasksLoading] = useState(false);
  const [externalTasksFilterProject, setExternalTasksFilterProject] = useState<string>('');
  const [externalVerifyingId, setExternalVerifyingId] = useState<string | null>(null);
  const [externalVerifyResult, setExternalVerifyResult] = useState<Record<string, any>>({});
  const [externalCopyFeedbackId, setExternalCopyFeedbackId] = useState<string | null>(null);

  // 🚀 Inspector apply-action bridge — modal state (declarations only here;
  // توابع و logic بعد از selectedModelIds تعریف می‌شوند تا closure سالم باشد)
  const [executeModalOpen, setExecuteModalOpen] = useState(false);
  const [executeModalTask, setExecuteModalTask] = useState<any | null>(null);
  type ExecuteStage =
    | 'idle' | 'resolving' | 'planning' | 'preview'
    | 'applying' | 'recording' | 'done' | 'error';
  type ActionFile = {
    path: string;
    operation?: 'modify' | 'create' | 'delete' | 'modify_sections';
    content?: string;
    sections?: Array<{ find?: string; replace?: string }>;
    description?: string;
  };
  type ActionPlan = { files: ActionFile[]; commit_message?: string };
  const [executeStage, setExecuteStage] = useState<ExecuteStage>('idle');
  const [executeProjectInfo, setExecuteProjectInfo] = useState<{
    matched: boolean;
    project_id: string;
    project_name: string;
    repo_full_name: string;
    reason: string;
  } | null>(null);
  const [executeActionPlan, setExecuteActionPlan] = useState<ActionPlan | null>(null);
  const [executePrUrl, setExecutePrUrl] = useState<string | null>(null);
  const [executePrBranch, setExecutePrBranch] = useState<string | null>(null);
  const [executeFilesCommitted, setExecuteFilesCommitted] = useState<string[]>([]);
  const [executeProgress, setExecuteProgress] = useState<string[]>([]);
  const [executeError, setExecuteError] = useState<string | null>(null);
  const [executeStartedAt, setExecuteStartedAt] = useState<number | null>(null);
  const executeReaderRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const closeExecuteModal = useCallback(() => {
    // اگر stream در جریان است، abort کن
    if (executeReaderRef.current) {
      try { executeReaderRef.current.cancel(); } catch {}
      executeReaderRef.current = null;
    }
    setExecuteModalOpen(false);
    setExecuteModalTask(null);
    setExecuteStage('idle');
    setExecuteProjectInfo(null);
    setExecuteActionPlan(null);
    setExecutePrUrl(null);
    setExecutePrBranch(null);
    setExecuteFilesCommitted([]);
    setExecuteProgress([]);
    setExecuteError(null);
    setExecuteStartedAt(null);
    setExecutePromptOverride(null);
    setExecuteIsFollowup(false);
    // auto-loop cleanup
    autoLoopActiveRef.current = false;
    if (autoLoopCountdownTimerRef.current) {
      clearInterval(autoLoopCountdownTimerRef.current);
      autoLoopCountdownTimerRef.current = null;
    }
    setAutoLoopEnabled(false);
    setAutoLoopRound(0);
    setAutoLoopStatus('idle');
    setAutoLoopCountdown(0);
  }, []);

  const loadExternalTasks = useCallback(async (projectId?: string) => {
    setExternalTasksLoading(true);
    try {
      const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
      const res = await fetch(`${API_BASE}/api/oversight/external-tasks${qs}`);
      const data = await res.json();
      setExternalTasks(Array.isArray(data?.items) ? data.items : []);
    } catch (e) {
      console.warn('loadExternalTasks failed', e);
      setExternalTasks([]);
    } finally {
      setExternalTasksLoading(false);
    }
  }, []);

  const verifyExternalTask = useCallback(async (it: any) => {
    setExternalVerifyingId(it.id);
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/external-tasks/${encodeURIComponent(it.origin_project_id)}/${encodeURIComponent(it.origin_field_id)}/verify-now`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        }
      );
      const data = await res.json();
      setExternalVerifyResult(prev => ({ ...prev, [it.id]: data }));
      if (typeof showSuccess === 'function') showSuccess('verify انجام شد');
    } catch (e: any) {
      setExternalVerifyResult(prev => ({ ...prev, [it.id]: { error: e?.message || 'failed' } }));
    } finally {
      setExternalVerifyingId(null);
    }
  }, []);

  const copyExternalPrompt = useCallback(async (it: any) => {
    try {
      const txt = (it.external_prompt && it.external_prompt.trim().length > 50) ? it.external_prompt : it.prompt;
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(txt);
      } else {
        const ta = document.createElement('textarea');
        ta.value = txt;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setExternalCopyFeedbackId(it.id);
      setTimeout(() => setExternalCopyFeedbackId(null), 1500);
    } catch (e) { /* non-critical */ }
  }, []);

  // وقتی تب project_tasks باز می‌شود، خودکار بارگذاری
  useEffect(() => {
    if (tab === 'project_tasks' && externalTasks.length === 0 && !externalTasksLoading) {
      loadExternalTasks(externalTasksFilterProject || undefined);
    }
  }, [tab, externalTasks.length, externalTasksLoading, externalTasksFilterProject, loadExternalTasks]);

  // اگر URL پارام project=ID داشت، خودکار به این تب برو و فیلتر کن
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const sp = new URLSearchParams(window.location.search);
      const pid = sp.get('project');
      if (pid) {
        setExternalTasksFilterProject(pid);
        setTab('project_tasks');
        loadExternalTasks(pid);
      }
    } catch (e) {}
    // فقط یک بار در mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [status, setStatus] = useState<Status | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);

  // ======================================================================
  // 🚀 Inspector apply-action bridge — توابع SSE/orchestration
  // (state ها در ابتدای کامپوننت تعریف شده‌اند؛ این توابع به selectedModelIds
  //  وابسته‌اند پس باید بعد از آن قرار گیرند)
  // ======================================================================
  const consumeSSEStream = useCallback(async (
    res: Response,
    onEvent: (eventName: string | null, dataObj: any) => void
  ): Promise<void> => {
    if (!res.body) throw new Error('پاسخ SSE خالی است');
    const reader = res.body.getReader();
    executeReaderRef.current = reader;
    const decoder = new TextDecoder();
    let buf = '';
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          let eventName: string | null = null;
          let dataLine = '';
          for (const ln of block.split('\n')) {
            if (ln.startsWith('event:')) eventName = ln.slice(6).trim();
            else if (ln.startsWith('data:')) dataLine += ln.slice(5).trim();
          }
          if (!dataLine) continue;
          let parsed: any = null;
          try { parsed = JSON.parse(dataLine); } catch { parsed = { raw: dataLine }; }
          onEvent(eventName, parsed);
        }
      }
    } finally {
      try { reader.releaseLock(); } catch {}
      if (executeReaderRef.current === reader) executeReaderRef.current = null;
    }
  }, []);

  // 🆕 وقتی modal روی followup باز می‌شود، promptOverride را به جای task.prompt
  // به smart-chat می‌فرستیم. این state بدون ذخیرهٔ دائمی روی task است.
  const [executePromptOverride, setExecutePromptOverride] = useState<string | null>(null);
  const [executeIsFollowup, setExecuteIsFollowup] = useState(false);

  // 🔁 Auto-loop state — اگر فعال باشد، پس از done در apply-action، خودکار
  // verify می‌کند، اگر partial بود، followup را از backend می‌گیرد و دور
  // بعدی را trigger می‌کند تا 5 دور یا تأیید نهایی.
  const [autoLoopEnabled, setAutoLoopEnabled] = useState(false);
  const [autoLoopRound, setAutoLoopRound] = useState(0);
  const AUTO_LOOP_MAX_ROUNDS = 5;
  const AUTO_LOOP_VERIFY_DELAY_MS = 30000;
  const [autoLoopStatus, setAutoLoopStatus] = useState<'idle' | 'waiting_verify' | 'verifying' | 'next_round' | 'finished' | 'cancelled'>('idle');
  const [autoLoopCountdown, setAutoLoopCountdown] = useState<number>(0);
  const autoLoopActiveRef = useRef(false);
  const autoLoopCountdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // فاز ۲: smart-chat برای تولید action_plan
  const startSmartChat = useCallback(async (task: any, projectId: string) => {
    if (!task || !projectId) return;
    setExecuteStage('planning');
    const isFollowup = !!executePromptOverride;
    setExecuteProgress(prev => [
      ...prev,
      isFollowup
        ? `🔁 دور ${task.followup_round || '?'}: ارسال پرامپت ادامه به مدل...`
        : '🧠 ارسال پرامپت به مدل برای تولید action_plan...',
    ]);
    try {
      const messageToSend = executePromptOverride || task.prompt || task.title || '';
      const res = await fetch(`${API_BASE}/api/render/inspector/smart-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          model_ids: selectedModelIds.length > 0 ? selectedModelIds : ['claude'],
          message: messageToSend,
          chat_history: [],
          previously_read_files: [],
        }),
      });
      if (!res.ok) {
        throw new Error(`smart-chat HTTP ${res.status}: ${await res.text().catch(() => '')}`);
      }
      let extractedPlan: ActionPlan | null = null;
      await consumeSSEStream(res, (eventName, data) => {
        if (eventName === 'progress' && data?.message) {
          setExecuteProgress(prev => [...prev.slice(-30), `… ${data.message}`]);
        } else if (eventName === 'response') {
          if (data?.action_plan && Array.isArray(data.action_plan?.files) && data.action_plan.files.length > 0) {
            extractedPlan = data.action_plan as ActionPlan;
          }
        } else if (eventName === 'error') {
          throw new Error(data?.message || 'خطا در smart-chat');
        }
      });
      if (!extractedPlan) {
        throw new Error('مدل action_plan تولید نکرد — احتمالاً سؤال شما نیاز به تغییر کد ندارد. پرامپت را بازنویسی کنید یا مدل دیگری انتخاب کنید.');
      }
      setExecuteActionPlan(extractedPlan);
      setExecuteStage('preview');
      setExecuteProgress(prev => [...prev, `✅ action_plan آماده شد: ${(extractedPlan as ActionPlan).files.length} فایل`]);
    } catch (e: any) {
      setExecuteError(e?.message || 'خطای ناشناخته در smart-chat');
      setExecuteStage('error');
    }
  }, [selectedModelIds, consumeSSEStream, executePromptOverride]);

  const openExecuteModal = useCallback(async (task: any) => {
    if (!task) return;
    closeExecuteModal();
    setExecuteModalOpen(true);
    setExecuteModalTask(task);
    setExecuteStage('resolving');
    setExecuteProgress(['🔍 یافتن پروژهٔ محلی برای این تسک...']);
    setExecuteStartedAt(Date.now());
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${encodeURIComponent(task.id)}/resolve-project`);
      if (!res.ok) {
        throw new Error(`resolve-project HTTP ${res.status}: ${await res.text().catch(() => '')}`);
      }
      const info = await res.json();
      setExecuteProjectInfo(info);
      if (!info.matched) {
        setExecuteError(info.reason || 'پروژه پیدا نشد');
        setExecuteStage('error');
        return;
      }
      setExecuteProgress(prev => [...prev, `✅ پروژه پیدا شد: ${info.project_name} (${info.project_id})`]);
      if (selectedModelIds.length === 0) {
        setExecuteError('حداقل یک مدل فعال انتخاب کنید (در بالای صفحه /oversight)');
        setExecuteStage('error');
        return;
      }
      await startSmartChat(task, info.project_id);
    } catch (e: any) {
      setExecuteError(e?.message || 'خطای ناشناخته در resolve-project');
      setExecuteStage('error');
    }
  }, [closeExecuteModal, selectedModelIds, startSmartChat]);

  // 🔁 باز کردن execute modal با followup_prompt به جای task.prompt
  // (بدون تغییر دائمی روی task — فقط برای این modal)
  const openExecuteModalWithFollowup = useCallback(async (task: any) => {
    if (!task) return;
    if (!task.followup_prompt || !task.followup_prompt.trim()) {
      alert('پرامپت بعدی موجود نیست. ابتدا verify انجام دهید.');
      return;
    }
    closeExecuteModal();
    setExecuteModalOpen(true);
    setExecuteModalTask(task);
    setExecutePromptOverride(task.followup_prompt);
    setExecuteIsFollowup(true);
    setExecuteStage('resolving');
    setExecuteProgress([
      `🔁 دور ${task.followup_round || 1}: شروع پردازش پرامپت ادامه...`,
      '🔍 یافتن پروژهٔ محلی برای این تسک...',
    ]);
    setExecuteStartedAt(Date.now());
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${encodeURIComponent(task.id)}/resolve-project`);
      if (!res.ok) {
        throw new Error(`resolve-project HTTP ${res.status}: ${await res.text().catch(() => '')}`);
      }
      const info = await res.json();
      setExecuteProjectInfo(info);
      if (!info.matched) {
        setExecuteError(info.reason || 'پروژه پیدا نشد');
        setExecuteStage('error');
        return;
      }
      setExecuteProgress(prev => [...prev, `✅ پروژه پیدا شد: ${info.project_name} (${info.project_id})`]);
      if (selectedModelIds.length === 0) {
        setExecuteError('حداقل یک مدل فعال انتخاب کنید (در بالای صفحه /oversight)');
        setExecuteStage('error');
        return;
      }
      // smart-chat با followup_prompt اجرا می‌شود (به‌خاطر executePromptOverride)
      await startSmartChat(task, info.project_id);
    } catch (e: any) {
      setExecuteError(e?.message || 'خطای ناشناخته در resolve-project');
      setExecuteStage('error');
    }
  }, [closeExecuteModal, selectedModelIds, startSmartChat]);

  // 📋 کپی پرامپت بعدی
  const [followupCopyFeedbackId, setFollowupCopyFeedbackId] = useState<string | null>(null);
  const copyFollowupPrompt = useCallback(async (task: any) => {
    if (!task?.followup_prompt) {
      alert('پرامپت بعدی موجود نیست. ابتدا verify انجام دهید.');
      return;
    }
    try {
      const txt = task.followup_prompt;
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(txt);
      } else {
        const ta = document.createElement('textarea');
        ta.value = txt;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setFollowupCopyFeedbackId(task.id);
      setTimeout(() => setFollowupCopyFeedbackId(null), 1500);
    } catch (e: any) {
      alert('کپی ناموفق: ' + e?.message);
    }
  }, []);

  // 👁 مشاهدهٔ پرامپت بعدی در modal
  const [viewingFollowupTask, setViewingFollowupTask] = useState<any | null>(null);
  const viewFollowupPrompt = useCallback((task: any) => {
    setViewingFollowupTask(task);
  }, []);

  // 📂 cache گزارش‌ها برای نمایش inline (per task_id → آخرین Report)
  const [taskReportCache, setTaskReportCache] = useState<Record<string, any>>({});
  const [taskReportLoading, setTaskReportLoading] = useState<Record<string, boolean>>({});
  const fetchLatestReportForTask = useCallback(async (taskId: string) => {
    if (taskReportCache[taskId] || taskReportLoading[taskId]) return;
    setTaskReportLoading(prev => ({ ...prev, [taskId]: true }));
    try {
      const res = await fetch(`${API_BASE}/api/oversight/reports?task_id=${encodeURIComponent(taskId)}&limit=1`);
      if (res.ok) {
        const data = await res.json();
        const reports = Array.isArray(data) ? data : (data?.items || data?.reports || []);
        if (reports.length > 0) {
          setTaskReportCache(prev => ({ ...prev, [taskId]: reports[0] }));
        }
      }
    } catch (e) { /* non-critical */ }
    finally {
      setTaskReportLoading(prev => ({ ...prev, [taskId]: false }));
    }
  }, [taskReportCache, taskReportLoading]);

  // فاز ۳: confirm + apply-action + record-execution
  const confirmAndApply = useCallback(async () => {
    const task = executeModalTask;
    const info = executeProjectInfo;
    const plan = executeActionPlan;
    if (!task || !info || !plan) return;
    setExecuteStage('applying');
    setExecuteProgress(prev => [...prev, '🚀 ارسال action_plan به apply-action...']);
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/apply-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: info.project_id,
          model_ids: selectedModelIds.length > 0 ? selectedModelIds : ['claude'],
          action_description: task.title || 'اعمال از /oversight',
          action_files: plan.files || [],
          commit_message: plan.commit_message || `oversight: ${task.title || task.id}`,
          original_message: task.prompt?.slice(0, 1000) || task.title || '',
        }),
      });
      if (!res.ok) {
        throw new Error(`apply-action HTTP ${res.status}: ${await res.text().catch(() => '')}`);
      }
      let prUrl = '';
      let prBranch = '';
      let filesCommitted: string[] = [];
      await consumeSSEStream(res, (eventName, data) => {
        if (eventName === 'progress' && data?.message) {
          setExecuteProgress(prev => [...prev.slice(-30), `… ${data.message}`]);
        } else if (eventName === 'apply_complete') {
          if (data?.pr_url) prUrl = data.pr_url;
          if (data?.branch) prBranch = data.branch;
          if (Array.isArray(data?.files_committed)) filesCommitted = data.files_committed;
        } else if (eventName === 'error') {
          throw new Error(data?.message || 'خطا در apply-action');
        }
      });
      if (!prUrl && !prBranch) {
        throw new Error('apply-action کامل شد ولی PR/branch ساخته نشد. لاگ‌ها را بررسی کنید.');
      }
      setExecutePrUrl(prUrl);
      setExecutePrBranch(prBranch);
      setExecuteFilesCommitted(filesCommitted);

      // فاز ۴: record-execution در Oversight
      setExecuteStage('recording');
      setExecuteProgress(prev => [...prev, '📝 ثبت نتیجه در Oversight...']);
      try {
        const recRes = await fetch(`${API_BASE}/api/oversight/tasks/${encodeURIComponent(task.id)}/record-execution`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pr_url: prUrl,
            pr_branch: prBranch,
            files_committed: filesCommitted,
            model_ids: selectedModelIds,
            action_plan_summary: (
              executeIsFollowup
                ? `[round ${executeModalTask?.followup_round || '?'}] ${plan.commit_message || ''}`
                : (plan.commit_message || '')
            ).slice(0, 500),
            executed_via: executeIsFollowup ? 'inspector_apply_action_followup' : 'inspector_apply_action',
          }),
        });
        if (!recRes.ok) {
          setExecuteProgress(prev => [...prev, `⚠️ ثبت در Oversight ناموفق (HTTP ${recRes.status}) — ولی PR ساخته شد`]);
        } else {
          setExecuteProgress(prev => [...prev, '✅ ثبت در Oversight موفق']);
          // refresh تسک‌ها تا badge PR نمایش داده شود
          try { await reloadTasks?.(); } catch {}
        }
      } catch (recErr: any) {
        setExecuteProgress(prev => [...prev, `⚠️ ثبت در Oversight شکست خورد: ${recErr?.message}`]);
      }

      setExecuteStage('done');

      // 🔁 Auto-loop: اگر فعال است و به max نرسیدیم، شروع countdown verify
      if (autoLoopActiveRef.current && autoLoopRound < AUTO_LOOP_MAX_ROUNDS) {
        scheduleAutoLoopVerify();
      }
    } catch (e: any) {
      setExecuteError(e?.message || 'خطای ناشناخته در apply-action');
      setExecuteStage('error');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executeModalTask, executeProjectInfo, executeActionPlan, selectedModelIds, consumeSSEStream, autoLoopRound]);

  // ===== Auto-loop helpers =====

  const cancelAutoLoop = useCallback(() => {
    autoLoopActiveRef.current = false;
    setAutoLoopEnabled(false);
    setAutoLoopStatus('cancelled');
    setAutoLoopCountdown(0);
    if (autoLoopCountdownTimerRef.current) {
      clearInterval(autoLoopCountdownTimerRef.current);
      autoLoopCountdownTimerRef.current = null;
    }
    setExecuteProgress(prev => [...prev, '🛑 auto-loop توسط کاربر متوقف شد']);
  }, []);

  // پس از done، 30 ثانیه صبر، سپس verify
  const scheduleAutoLoopVerify = useCallback(() => {
    if (!autoLoopActiveRef.current) return;
    setAutoLoopStatus('waiting_verify');
    setAutoLoopCountdown(Math.floor(AUTO_LOOP_VERIFY_DELAY_MS / 1000));
    setExecuteProgress(prev => [...prev, `⏱ ${AUTO_LOOP_VERIFY_DELAY_MS / 1000} ثانیه صبر برای verify...`]);
    if (autoLoopCountdownTimerRef.current) clearInterval(autoLoopCountdownTimerRef.current);
    autoLoopCountdownTimerRef.current = setInterval(() => {
      setAutoLoopCountdown(prev => {
        if (prev <= 1) {
          if (autoLoopCountdownTimerRef.current) {
            clearInterval(autoLoopCountdownTimerRef.current);
            autoLoopCountdownTimerRef.current = null;
          }
          // ⚠️ trigger verify در next tick — درون setState callback نمی‌توانیم
          setTimeout(() => runAutoLoopVerify(), 0);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runAutoLoopVerify = useCallback(async () => {
    if (!autoLoopActiveRef.current || !executeModalTask) return;
    setAutoLoopStatus('verifying');
    setExecuteProgress(prev => [...prev, '🔍 verify در حال اجرا...']);
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/tasks/${encodeURIComponent(executeModalTask.id)}/verify-now`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) },
      );
      if (!res.ok) {
        throw new Error(`verify-now HTTP ${res.status}`);
      }
      const data = await res.json();
      const status = data?.report?.status || data?.task?.verification_status || 'unknown';
      const final = !!data?.final;
      setExecuteProgress(prev => [...prev, `🔍 verify: status=${status}${final ? ' (تأیید نهایی)' : ''}`]);

      if (final || status === 'done') {
        setAutoLoopStatus('finished');
        setExecuteProgress(prev => [...prev, '✅ auto-loop به تأیید نهایی رسید']);
        autoLoopActiveRef.current = false;
        return;
      }

      // status partial/not_done/regressed → followup
      const updatedTask = data?.task;
      const followup = updatedTask?.followup_prompt;
      if (!followup || followup.length < 50) {
        setExecuteProgress(prev => [...prev, '⚠️ followup prompt تولید نشد — auto-loop متوقف']);
        autoLoopActiveRef.current = false;
        setAutoLoopStatus('cancelled');
        return;
      }

      const nextRound = autoLoopRound + 1;
      if (nextRound >= AUTO_LOOP_MAX_ROUNDS) {
        setExecuteProgress(prev => [...prev, `⚠️ به max ${AUTO_LOOP_MAX_ROUNDS} دور رسیدیم — دستی ادامه دهید`]);
        autoLoopActiveRef.current = false;
        setAutoLoopStatus('cancelled');
        // مدل را در حالت 'done' نگه می‌داریم تا کاربر دکمه‌های بعدی را ببیند
        return;
      }

      // شروع دور بعدی
      setAutoLoopRound(nextRound);
      setAutoLoopStatus('next_round');
      setExecuteProgress(prev => [...prev, `🚀 شروع دور ${nextRound + 1}: استفاده از followup_prompt`]);

      // reset modal state برای دور جدید (ولی autoLoop خاموش نمی‌شود)
      setExecuteActionPlan(null);
      setExecutePrUrl(null);
      setExecutePrBranch(null);
      setExecuteFilesCommitted([]);
      setExecuteError(null);
      setExecutePromptOverride(followup);
      setExecuteIsFollowup(true);
      // شروع دوباره — resolve از قبل انجام شده، مستقیم برو smart-chat
      setExecuteStage('planning');
      try {
        if (executeProjectInfo?.project_id) {
          await startSmartChat(updatedTask, executeProjectInfo.project_id);
          // اگر action_plan تولید شد، خودکار confirmAndApply را trigger می‌کنیم
          // (در غیر این صورت user دستی preview را تأیید می‌کند)
          // در اینجا فقط منتظر می‌مانیم — startSmartChat تنظیم state می‌کند
          // به stage='preview' که modal preview را نشان می‌دهد
          // — auto-loop می‌خواهد خودکار باشد، پس بعد از رسیدن به preview،
          //   خودش confirmAndApply را call می‌کنیم
          // (این در useEffect جداگانه handle می‌شود — پایین‌تر)
        } else {
          throw new Error('project_id برای دور بعدی موجود نیست');
        }
      } catch (e: any) {
        setExecuteError(e?.message || 'خطا در شروع دور بعدی');
        setExecuteStage('error');
        autoLoopActiveRef.current = false;
        setAutoLoopStatus('cancelled');
      }
    } catch (e: any) {
      setExecuteProgress(prev => [...prev, `⚠️ verify ناموفق: ${e?.message}`]);
      autoLoopActiveRef.current = false;
      setAutoLoopStatus('cancelled');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executeModalTask, executeProjectInfo, autoLoopRound, startSmartChat]);

  // skip countdown — verify الان
  const skipCountdownAndVerify = useCallback(() => {
    if (autoLoopCountdownTimerRef.current) {
      clearInterval(autoLoopCountdownTimerRef.current);
      autoLoopCountdownTimerRef.current = null;
    }
    setAutoLoopCountdown(0);
    runAutoLoopVerify();
  }, [runAutoLoopVerify]);

  // ⚙️ هنگامی که auto-loop فعال است و stage='preview' (یعنی smart-chat
  // در دور جدید action_plan تولید کرد)، خودکار confirmAndApply را trigger
  // می‌کنیم تا چرخه ادامه پیدا کند بدون دخالت کاربر.
  useEffect(() => {
    if (autoLoopActiveRef.current && executeStage === 'preview' && executeActionPlan && autoLoopRound > 0) {
      setExecuteProgress(prev => [...prev, `🤖 auto-loop: تأیید خودکار preview دور ${autoLoopRound + 1}...`]);
      // فاصلهٔ کوتاه برای جلوگیری از race
      setTimeout(() => {
        if (autoLoopActiveRef.current) {
          confirmAndApply();
        }
      }, 500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executeStage, executeActionPlan, autoLoopRound]);

  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposSyncedAt, setReposSyncedAt] = useState<string | null>(null);
  const [reposLoading, setReposLoading] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');
  const [repoLangFilter, setRepoLangFilter] = useState('');
  const [repoVisibility, setRepoVisibility] = useState<'all' | 'public' | 'private'>('all');
  const [repoSort, setRepoSort] = useState<RepoSort>('pushed_desc');
  const [selectedRepoNames, setSelectedRepoNames] = useState<Set<string>>(new Set());

  const [watched, setWatched] = useState<Watched[]>([]);

  // 🆕 (commit 2.1) auto-select اولین watched برای تب health
  // اینجا قرار دارد چون به watched state وابسته است
  useEffect(() => {
    if (tab === 'health' && !selectedHealthWatchedId && watched.length > 0) {
      setSelectedHealthWatchedId(watched[0].id);
    }
  }, [tab, selectedHealthWatchedId, watched]);

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

  // Deep scan progress
  const [deepScanWatchedId, setDeepScanWatchedId] = useState<string | null>(null);
  const [deepScanProgress, setDeepScanProgress] = useState<any>(null);
  const deepScanPollRef = useRef<any>(null);

  // Codex modal
  const [codexWatchedId, setCodexWatchedId] = useState<string | null>(null);
  const [codexData, setCodexData] = useState<any>(null);
  const [codexLoading, setCodexLoading] = useState(false);
  const [codexSearch, setCodexSearch] = useState('');

  // Verification history modal
  const [verifyHistoryTaskId, setVerifyHistoryTaskId] = useState<string | null>(null);
  const [verifyHistoryData, setVerifyHistoryData] = useState<any>(null);

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
    return () => {
      if (deepScanPollRef.current) clearInterval(deepScanPollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

    // بازیابی لیست مخازن از کش localStorage
    try {
      const cached = localStorage.getItem('oversight_repos_cache');
      if (cached) {
        const parsed = JSON.parse(cached);
        if (parsed && Array.isArray(parsed.repos)) {
          setRepos(parsed.repos);
          setReposSyncedAt(parsed.synced_at || null);
        }
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

  const loadRepos = async (forceRefresh: boolean = false) => {
    setReposLoading(true);
    try {
      const url = `${API_BASE}/api/oversight/repos${forceRefresh ? '?refresh=true' : ''}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.success) {
        const list = data.repos || [];
        setRepos(list);
        setReposSyncedAt(data.synced_at || new Date().toISOString());
        // ذخیره در localStorage
        try {
          localStorage.setItem(
            'oversight_repos_cache',
            JSON.stringify({
              repos: list,
              synced_at: data.synced_at || new Date().toISOString(),
              cached_at: Date.now(),
            }),
          );
        } catch {}
        if (data.from_cache) {
          showSuccess(`${data.count} مخزن (از کش) — برای بازخوانی روی «بارگذاری مجدد» کلیک کنید`);
        } else {
          showSuccess(`${data.count} مخزن از GitHub بارگذاری شد`);
        }
        if (data.warning) showError(data.warning);
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

  // اگر تب repos باز شد و لیست خالی است، خودکار از کش/GitHub بارگذاری کن
  useEffect(() => {
    if (tab === 'repos' && repos.length === 0 && !reposLoading) {
      loadRepos(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

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

  // ============================ Deep Scan ============================
  const startDeepScan = async (watchedId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/oversight/scan/${watchedId}/deep`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModelIds[0] || undefined }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'شروع deep scan ناموفق');
        return;
      }
      setDeepScanWatchedId(watchedId);
      setDeepScanProgress({ status: 'queued', message: 'در انتظار شروع' });
      // شروع polling
      if (deepScanPollRef.current) clearInterval(deepScanPollRef.current);
      deepScanPollRef.current = setInterval(async () => {
        try {
          const pr = await fetch(`${API_BASE}/api/oversight/scan/${watchedId}/progress`);
          if (pr.ok) {
            const data = await pr.json();
            setDeepScanProgress(data);
            if (data.status === 'completed' || data.status === 'error') {
              clearInterval(deepScanPollRef.current);
              deepScanPollRef.current = null;
              await reloadTasks();
              if (data.status === 'completed') {
                showSuccess(
                  `Deep scan تمام شد - ${data.tasks_created || 0} تسک ساخته شد`,
                );
              } else {
                showError(`خطا در deep scan: ${data.message || ''}`);
              }
            }
          }
        } catch {}
      }, 2000);
    } catch (e: any) {
      showError(e.message);
    }
  };

  const closeDeepScan = () => {
    if (deepScanPollRef.current) clearInterval(deepScanPollRef.current);
    deepScanPollRef.current = null;
    setDeepScanWatchedId(null);
    setDeepScanProgress(null);
  };

  // ============================ Codex ============================
  const openCodex = async (watchedId: string) => {
    setCodexWatchedId(watchedId);
    setCodexLoading(true);
    setCodexData(null);
    try {
      const res = await fetch(`${API_BASE}/api/oversight/codex/${watchedId}`);
      if (res.ok) {
        const data = await res.json();
        setCodexData(data);
      }
    } catch {}
    setCodexLoading(false);
  };

  const refreshCodex = async () => {
    if (!codexWatchedId) return;
    setCodexLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/oversight/codex/${codexWatchedId}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModelIds[0] || undefined, only_changed: false }),
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(`${data.files_documented || 0} فایل مستند شد`);
        // reload codex
        const reload = await fetch(`${API_BASE}/api/oversight/codex/${codexWatchedId}`);
        if (reload.ok) setCodexData(await reload.json());
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'به‌روزرسانی Codex ناموفق');
      }
    } catch (e: any) {
      showError(e.message);
    }
    setCodexLoading(false);
  };

  // ============================ Verifier / Manual external ============================
  const verifyTaskNow = async (id: string) => {
    setRunningTaskIds((p) => new Set(p).add(id));
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${id}/verify-now`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModelIds[0] || undefined }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.task) setTasks((prev) => prev.map((t) => (t.id === id ? data.task : t)));
        if (data.report) setReports((prev) => [data.report, ...prev]);
        if (data.final) {
          showSuccess('✅ تأیید نهایی! تسک done شد.');
        } else {
          showSuccess(
            `Verify تمام شد - وضعیت: ${data.report?.status || 'partial'} (streak ${data.streak}/${data.streak_required})`,
          );
        }
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'verify ناموفق');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setRunningTaskIds((p) => {
        const next = new Set(p);
        next.delete(id);
        return next;
      });
    }
  };

  const markTaskAppliedExternally = async (id: string) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/tasks/${id}/mark-applied-externally`,
        { method: 'POST' },
      );
      if (res.ok) {
        const data = await res.json();
        setTasks((prev) => prev.map((t) => (t.id === id ? data : t)));
        showSuccess('علامت زده شد - در دور verify بعدی بررسی می‌شود (یا الان verify کنید)');
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const copyFullPrompt = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${id}/full-prompt`);
      if (!res.ok) {
        showError('دریافت پرامپت ناموفق');
        return;
      }
      const data = await res.json();
      const text = data.prompt || '';
      try {
        await navigator.clipboard.writeText(text);
        showSuccess('پرامپت کامل در کلیپ‌بورد کپی شد');
      } catch {
        // fallback: show in modal
        showError('کپی خودکار ناموفق - پرامپت در console چاپ شد');
        console.log(text);
      }
    } catch (e: any) {
      showError(e.message);
    }
  };

  const openVerifyHistory = async (id: string) => {
    setVerifyHistoryTaskId(id);
    setVerifyHistoryData(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/oversight/tasks/${id}/verification-history`,
      );
      if (res.ok) setVerifyHistoryData(await res.json());
    } catch {}
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
              { id: 'project_tasks', label: 'تسک‌های پروژه‌ها', icon: '🔗', count: externalTasks.length },
              { id: 'health', label: 'سلامت پروژه', icon: '🏥', count: 0 },
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
                  onDeepScan={() => startDeepScan(w.id)}
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
                  onOpenCodex={() => openCodex(w.id)}
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
                  onClick={() => loadRepos(true)}
                  disabled={reposLoading || !status?.github_token}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                  title="بازخوانی تازه از GitHub (cache نادیده گرفته می‌شود)"
                >
                  {reposLoading ? '⏳ در حال بارگذاری...' : '🔄 بازخوانی از GitHub'}
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
              title="AI کل ساختار پروژه را اسکن می‌کند، ۱۸ فایل کلیدی را می‌خواند، گراف importها را می‌سازد، و پرامپت را با ارجاع به کد واقعی (file:line) می‌نویسد. ممکن است ۱۰–۳۰ ثانیه طول بکشد."
              className="w-full py-3 bg-purple-500 text-white rounded-lg font-bold hover:bg-purple-600 disabled:opacity-50"
            >
              {generating ? '⏳ در حال خواندن پروژه (۱۸ فایل کلیدی) و ساخت پرامپت grounded...' : '🪄 تبدیل به پرامپت با AI (با خواندن کد پروژه)'}
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
            onVerify={verifyTaskNow}
            onMarkExternal={markTaskAppliedExternally}
            onCopyPrompt={copyFullPrompt}
            onShowHistory={openVerifyHistory}
            onExecuteWithAi={openExecuteModal}
            onCopyFollowup={copyFollowupPrompt}
            onExecuteFollowupWithAi={openExecuteModalWithFollowup}
            onViewFollowup={viewFollowupPrompt}
            followupCopyFeedbackId={followupCopyFeedbackId}
            taskReportCache={taskReportCache}
            taskReportLoading={taskReportLoading}
            fetchLatestReportForTask={fetchLatestReportForTask}
            executeDisabledReason={selectedModelIds.length === 0 ? 'حداقل یک مدل انتخاب کنید' : ''}
            fmtDate={fmtDate}
          />
        ) : tab === 'project_tasks' ? (
          // ─── 🔗 تب «تسک‌های پروژه‌ها» — bridge با /projects ───
          <div>
            <div className="flex items-center justify-between mb-4 pb-3 border-b dark:border-gray-700">
              <div>
                <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                  <span>🔗</span> تسک‌های پروژه‌های محلی
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  فیلدهای dynamic از <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">/projects</code>
                  &nbsp;که action_type آنها commit/refactor است — با verifier همان مرکز نظارت قابل بررسی‌اند.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={externalTasksFilterProject}
                  onChange={e => setExternalTasksFilterProject(e.target.value)}
                  placeholder="فیلتر بر اساس project_id"
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm w-56"
                />
                <button
                  onClick={() => loadExternalTasks(externalTasksFilterProject || undefined)}
                  disabled={externalTasksLoading}
                  className="px-3 py-1.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 text-sm"
                >
                  {externalTasksLoading ? '⏳' : '🔄'} بروزرسانی
                </button>
              </div>
            </div>

            {externalTasksLoading ? (
              <div className="text-center py-12 text-gray-500">⏳ در حال بارگذاری تسک‌های پروژه‌ها...</div>
            ) : externalTasks.length === 0 ? (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <div className="text-4xl mb-2">🔗</div>
                <p className="mb-1">هیچ تسک پروژه‌ای یافت نشد</p>
                <p className="text-xs">
                  در صفحهٔ <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">/projects</code> یک پروژه باز کنید،
                  تب memory ⇒ یک dynamic field با action_type=github_commit بسازید — اینجا ظاهر می‌شود.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {externalTasks.map(it => {
                  const verifyResult = externalVerifyResult[it.id];
                  const verifyReportStatus = verifyResult?.report?.status;
                  return (
                    <div key={it.id} className="border border-gray-200 dark:border-gray-700 rounded-xl p-4 bg-white dark:bg-gray-800">
                      {/* Header */}
                      <div className="flex items-start justify-between mb-2 gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-gray-800 dark:text-gray-100 truncate">{it.title}</h3>
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              it.priority === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' :
                              it.priority === 'high' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' :
                              it.priority === 'medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' :
                              'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                            }`}>
                              {it.priority}
                            </span>
                            <span className="px-2 py-0.5 rounded text-xs bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300">
                              🔗 {it.action_type}
                            </span>
                            {verifyReportStatus && (
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                verifyReportStatus === 'done' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                                verifyReportStatus === 'partial' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' :
                                verifyReportStatus === 'not_done' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' :
                                'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                              }`}>
                                verify: {verifyReportStatus}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            <span>📁 پروژه: <strong>{it.origin_project_name}</strong></span>
                            {it.project_full_name && it.project_full_name !== it.origin_project_name && (
                              <> · <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{it.project_full_name}</code></>
                            )}
                            {it.last_run_at && <> · last_run: {fmtDate(it.last_run_at)}</>}
                          </div>
                        </div>
                      </div>

                      {/* Prompt preview */}
                      {it.prompt && (
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
                            👁 نمایش پرامپت ({it.prompt.length} کاراکتر)
                          </summary>
                          <pre className="mt-2 text-xs bg-gray-50 dark:bg-gray-900/50 p-3 rounded max-h-64 overflow-auto whitespace-pre-wrap font-mono text-gray-700 dark:text-gray-300">
                            {it.prompt.slice(0, 4000)}
                            {it.prompt.length > 4000 && '\n... [TRUNCATED]'}
                          </pre>
                        </details>
                      )}

                      {/* Verify result preview */}
                      {verifyResult?.report?.summary && (
                        <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-xs">
                          <div className="font-medium text-blue-800 dark:text-blue-200 mb-1">📋 خلاصه verifier:</div>
                          <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                            {verifyResult.report.summary || verifyResult.report.raw_response?.slice(0, 500) || '(بدون خلاصه)'}
                          </div>
                        </div>
                      )}
                      {verifyResult?.error && (
                        <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-700 dark:text-red-300">
                          ❌ {verifyResult.error}
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex items-center gap-2 mt-3 pt-3 border-t dark:border-gray-700">
                        <button
                          onClick={() => copyExternalPrompt(it)}
                          className="px-3 py-1.5 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-900/50 text-xs flex items-center gap-1"
                          title="کپی پرامپت قوی برای استفاده در ابزار خارجی (Cursor / ChatGPT / ...)"
                        >
                          📋 {externalCopyFeedbackId === it.id ? 'کپی شد ✓' : 'کپی پرامپت'}
                        </button>
                        <button
                          onClick={() => verifyExternalTask(it)}
                          disabled={externalVerifyingId === it.id}
                          className="px-3 py-1.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 text-xs flex items-center gap-1"
                          title="verify فوری — وضعیت فعلی repo را با acceptance criteria مقایسه می‌کند (semantic equivalence)"
                        >
                          {externalVerifyingId === it.id ? '⏳ در حال verify...' : '🔍 verify الان'}
                        </button>
                        <a
                          href={`/projects/${it.origin_project_id}`}
                          className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-xs flex items-center gap-1"
                          title="باز کردن پروژه در /projects/[id]"
                        >
                          👁 مشاهده در /projects
                        </a>
                        {it.target_files.length > 0 && (
                          <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                            🎯 {it.target_files.length} فایل هدف
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : tab === 'health' ? (
          // ─── 🏥 تب سلامت پروژه (مهاجرت از Health analysis) ───
          <div>
            <div className="flex items-center justify-between mb-4 pb-3 border-b dark:border-gray-700 flex-wrap gap-3">
              <div>
                <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                  <span>🏥</span> سلامت پروژه
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  متریک‌های سلامت کد، امنیت، پوشش تست و chain status — بر اساس آخرین Deep Scan
                </p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={selectedHealthWatchedId}
                  onChange={e => setSelectedHealthWatchedId(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                >
                  <option value="">— پروژه را انتخاب کنید —</option>
                  {watched.map(w => (
                    <option key={w.id} value={w.id}>{w.repo_full_name}</option>
                  ))}
                </select>
                <button
                  onClick={() => loadHealthData(selectedHealthWatchedId)}
                  disabled={!selectedHealthWatchedId || healthLoading}
                  className="px-3 py-1.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 text-sm"
                >
                  {healthLoading ? '⏳' : '🔄'} بروزرسانی
                </button>
              </div>
            </div>

            {!selectedHealthWatchedId ? (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <div className="text-4xl mb-2">🏥</div>
                <p>یک پروژهٔ تحت نظارت انتخاب کنید</p>
              </div>
            ) : healthError ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 rounded-lg p-4 text-red-800 dark:text-red-200 text-sm">
                ❌ {healthError}
              </div>
            ) : !healthSummaries && !healthChainStatus ? (
              <div className="text-center py-12 text-gray-500">
                {healthLoading ? '⏳ در حال بارگذاری...' : 'data موجود نیست — ابتدا یک Deep Scan اجرا کنید'}
              </div>
            ) : (
              <>
                {/* Sub-tabs */}
                <div className="flex gap-2 mb-4 flex-wrap border-b dark:border-gray-700 pb-2">
                  {([
                    { id: 'overview', label: 'مرور کلی', icon: '📊' },
                    { id: 'files', label: 'نقشهٔ سلامت فایل‌ها', icon: '🗺️' },
                    { id: 'security', label: 'امنیت', icon: '🔒' },
                    { id: 'coverage', label: 'پوشش تست', icon: '🧪' },
                    { id: 'docs', label: 'Roadmap & README', icon: '📋' },
                    { id: 'validation', label: 'Chain Status', icon: '⛓️' },
                  ] as const).map(st => (
                    <button
                      key={st.id}
                      onClick={() => setHealthSubTab(st.id as HealthSubTab)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition ${
                        healthSubTab === st.id
                          ? 'bg-cyan-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
                    >
                      {st.icon} {st.label}
                    </button>
                  ))}
                </div>

                {/* Sub-tab: overview */}
                {healthSubTab === 'overview' && (
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                    {(() => {
                      const hs = healthSummaries?.pass_summaries?.health_summary;
                      const score = hs?.overall_health_score;
                      return (
                        <>
                          <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4 text-center">
                            <div className="text-3xl mb-1">
                              {score >= 70 ? '🟢' : score >= 40 ? '🟡' : '🔴'}
                            </div>
                            <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                              {score != null ? Math.round(score) : '—'}
                            </div>
                            <div className="text-xs text-gray-500">overall_health_score</div>
                          </div>
                          <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4 text-center">
                            <div className="text-3xl mb-1">📁</div>
                            <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                              {hs?.files_analyzed_count ?? 0}
                            </div>
                            <div className="text-xs text-gray-500">فایل‌های تحلیل‌شده</div>
                          </div>
                          <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4 text-center">
                            <div className="text-3xl mb-1">🚨</div>
                            <div className="text-2xl font-bold text-red-700 dark:text-red-300">
                              {hs?.red_files_count ?? 0}
                            </div>
                            <div className="text-xs text-gray-500">فایل‌های قرمز (نیاز فوری)</div>
                          </div>
                          <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4 text-center">
                            <div className="text-3xl mb-1">📋</div>
                            <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                              {healthSummaries?.findings_count ?? 0}
                            </div>
                            <div className="text-xs text-gray-500">findings از scan</div>
                          </div>
                        </>
                      );
                    })()}
                    {healthSummaries?.ran_at && (
                      <div className="md:col-span-2 lg:col-span-4 text-xs text-gray-500 dark:text-gray-400 text-center mt-2">
                        🕐 آخرین scan: {fmtDate(healthSummaries.ran_at)} · {healthSummaries.passes_run} pass اجرا شد
                      </div>
                    )}
                  </div>
                )}

                {/* Sub-tab: files (heatmap) */}
                {healthSubTab === 'files' && (
                  <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                    {(() => {
                      const fhm = healthSummaries?.pass_summaries?.file_health_map || {};
                      const entries = Object.entries(fhm).sort((a: any, b: any) => (a[1].score || 0) - (b[1].score || 0));
                      if (entries.length === 0) {
                        return <div className="text-center text-gray-500 py-8">file_health_map تولید نشده — یک scan اجرا کنید</div>;
                      }
                      return (
                        <div className="space-y-2 max-h-[500px] overflow-auto">
                          {entries.map(([path, fh]: any) => (
                            <button
                              key={path}
                              onClick={() => setHealthSelectedFile(path)}
                              className="w-full text-right flex items-center gap-3 p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-900/40"
                            >
                              <div
                                className="w-3 h-8 rounded flex-shrink-0"
                                style={{ backgroundColor: fh.hex || '#888' }}
                                title={`${fh.color} · score=${fh.score}`}
                              />
                              <code className="text-xs flex-1 text-gray-800 dark:text-gray-200 truncate">{path}</code>
                              <span className={`text-xs font-bold ${
                                fh.color === 'red' ? 'text-red-600' :
                                fh.color === 'yellow' ? 'text-yellow-600' : 'text-green-600'
                              }`}>
                                {Math.round(fh.score || 0)}
                              </span>
                              <span className="text-xs text-gray-500">
                                {fh.findings_count || 0} finding
                              </span>
                            </button>
                          ))}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Sub-tab: security */}
                {healthSubTab === 'security' && (
                  <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                    {(() => {
                      const ss = healthSummaries?.pass_summaries?.security_summary;
                      if (!ss) return <div className="text-center text-gray-500 py-8">security_summary موجود نیست — Pass I (security_deep) اجرا نشده</div>;
                      return (
                        <div className="space-y-3">
                          <div className="flex items-center gap-3 mb-3 pb-3 border-b dark:border-gray-700">
                            <div className={`text-4xl ${
                              (ss.overall_security_score || 0) >= 70 ? 'text-green-500' :
                              (ss.overall_security_score || 0) >= 40 ? 'text-yellow-500' : 'text-red-500'
                            }`}>🔒</div>
                            <div>
                              <div className="text-2xl font-bold">{ss.overall_security_score || 0}/100</div>
                              <div className="text-xs text-gray-500">overall_security_score</div>
                            </div>
                          </div>
                          <div className="grid sm:grid-cols-2 gap-3 text-sm">
                            <div>🔑 secrets: <strong>{ss.secrets_count || 0}</strong></div>
                            <div>📜 license: <strong>{ss.license_status || '?'}</strong> ({ss.license_name || '—'})</div>
                            <div>📦 vulnerable deps: <strong>{ss.vulnerable_deps_count || 0}</strong></div>
                            <div>🔐 sensitive files: <strong>{ss.sensitive_files_count || 0}</strong></div>
                            <div>🌐 CORS open: <strong>{ss.cors_open ? 'بله ⚠️' : 'خیر ✓'}</strong></div>
                            <div>🔓 endpoints بدون auth: <strong>{ss.endpoints_without_auth_count || 0}</strong></div>
                          </div>
                          {Array.isArray(ss.secrets_files) && ss.secrets_files.length > 0 && (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-sm font-medium">🔑 secrets یافت‌شده ({ss.secrets_files.length})</summary>
                              <ul className="mt-2 text-xs space-y-1 list-disc pr-5">
                                {ss.secrets_files.map((f: string, i: number) => <li key={i}><code>{f}</code></li>)}
                              </ul>
                            </details>
                          )}
                          {Array.isArray(ss.vulnerable_deps) && ss.vulnerable_deps.length > 0 && (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-sm font-medium">📦 dependencies آسیب‌پذیر</summary>
                              <ul className="mt-2 text-xs space-y-1 list-disc pr-5">
                                {ss.vulnerable_deps.map((d: any, i: number) => (
                                  <li key={i}>{d.name}@{d.version} - {d.cve} ({d.severity})</li>
                                ))}
                              </ul>
                            </details>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Sub-tab: coverage */}
                {healthSubTab === 'coverage' && (
                  <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                    {(() => {
                      const cs = healthSummaries?.pass_summaries?.coverage_summary;
                      if (!cs) return <div className="text-center text-gray-500 py-8">coverage_summary موجود نیست — Pass J (coverage) اجرا نشده</div>;
                      return (
                        <div className="space-y-3">
                          <div className="flex items-center gap-3 mb-3 pb-3 border-b dark:border-gray-700">
                            <div className="text-4xl">🧪</div>
                            <div>
                              <div className="text-2xl font-bold">{cs.coverage_estimate_percent || 0}%</div>
                              <div className="text-xs text-gray-500">coverage_estimate · score: {cs.coverage_score || 0}/100</div>
                            </div>
                          </div>
                          <div className="grid sm:grid-cols-3 gap-3 text-sm text-center">
                            <div className="bg-gray-50 dark:bg-gray-900/40 p-3 rounded">
                              <div className="text-xl font-bold">{cs.total_source_files || 0}</div>
                              <div className="text-xs text-gray-500">source files</div>
                            </div>
                            <div className="bg-gray-50 dark:bg-gray-900/40 p-3 rounded">
                              <div className="text-xl font-bold">{cs.total_test_files || 0}</div>
                              <div className="text-xs text-gray-500">test files</div>
                            </div>
                            <div className="bg-gray-50 dark:bg-gray-900/40 p-3 rounded">
                              <div className="text-xl font-bold text-orange-600">{cs.untested_files_count || 0}</div>
                              <div className="text-xs text-gray-500">untested files</div>
                            </div>
                          </div>
                          {Array.isArray(cs.critical_untested) && cs.critical_untested.length > 0 && (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-sm font-medium text-red-700 dark:text-red-300">
                                🚨 critical untested ({cs.critical_untested.length})
                              </summary>
                              <ul className="mt-2 text-xs space-y-2">
                                {cs.critical_untested.map((c: any, i: number) => (
                                  <li key={i} className="border-r-2 border-red-500 pr-2">
                                    <code>{c.path}</code> — <em>{c.reason}</em>
                                    {Array.isArray(c.suggested_tests) && c.suggested_tests.length > 0 && (
                                      <ul className="mt-1 list-disc pr-5 text-gray-600 dark:text-gray-400">
                                        {c.suggested_tests.map((t: string, j: number) => <li key={j}>{t}</li>)}
                                      </ul>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            </details>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Sub-tab: docs (Roadmap + README + Ideal State) */}
                {healthSubTab === 'docs' && (
                  <div className="space-y-4">
                    {/* بخش Ideal State */}
                    <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3 pb-2 border-b dark:border-gray-700">
                        <h3 className="font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                          🎯 Ideal State
                        </h3>
                        <span className="text-xs text-gray-500">توصیف وضعیت مطلوب پروژه — استفاده در Pass H (completeness)</span>
                      </div>
                      {healthRoadmapEditing ? (
                        <textarea
                          value={healthRoadmapDraft.ideal}
                          onChange={e => setHealthRoadmapDraft(d => ({ ...d, ideal: e.target.value }))}
                          rows={4}
                          className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm font-mono"
                          placeholder="پروژه در حالت ایده‌آل به چه شکل است؟"
                        />
                      ) : (
                        <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap min-h-[3em]">
                          {healthRoadmap?.ideal_state || <em className="text-gray-400">هنوز تعریف نشده — با AI تولید کنید یا دستی ویرایش کنید.</em>}
                        </div>
                      )}
                    </div>

                    {/* بخش Roadmap */}
                    <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3 pb-2 border-b dark:border-gray-700 flex-wrap gap-2">
                        <h3 className="font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                          📋 Roadmap
                          {healthRoadmap?.generated_at && (
                            <span className="text-xs text-gray-500 font-normal">
                              ({fmtDate(healthRoadmap.generated_at)})
                            </span>
                          )}
                        </h3>
                        <div className="flex gap-2">
                          <button
                            onClick={generateRoadmap}
                            disabled={!!healthDocsLoading}
                            className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
                          >
                            {healthDocsLoading === 'roadmap' ? '⏳ در حال تولید...' : '🤖 تولید با AI'}
                          </button>
                          {!healthRoadmapEditing ? (
                            <button
                              onClick={() => {
                                setHealthRoadmapDraft({
                                  markdown: healthRoadmap?.roadmap_markdown || '',
                                  ideal: healthRoadmap?.ideal_state || '',
                                });
                                setHealthRoadmapEditing(true);
                              }}
                              className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-xs hover:bg-gray-300 dark:hover:bg-gray-600"
                            >
                              ✏️ ویرایش
                            </button>
                          ) : (
                            <>
                              <button
                                onClick={saveRoadmapManual}
                                className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                              >
                                💾 ذخیره
                              </button>
                              <button
                                onClick={() => setHealthRoadmapEditing(false)}
                                className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-xs hover:bg-gray-300 dark:hover:bg-gray-600"
                              >
                                لغو
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      {healthRoadmapEditing ? (
                        <textarea
                          value={healthRoadmapDraft.markdown}
                          onChange={e => setHealthRoadmapDraft(d => ({ ...d, markdown: e.target.value }))}
                          rows={20}
                          className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm font-mono"
                          placeholder="## فاز اول&#10;- [ ] task 1&#10;- [x] task done"
                        />
                      ) : healthRoadmap?.phases && healthRoadmap.phases.length > 0 ? (
                        <div className="space-y-3">
                          {healthRoadmap.phases.map((phase, pi) => (
                            <div key={pi} className="border-r-4 border-cyan-500 pr-3">
                              <h4 className="font-medium text-gray-800 dark:text-gray-100 mb-1">
                                {phase.name || `فاز ${pi + 1}`}
                                {phase.eta && <span className="text-xs text-gray-500 mr-2">({phase.eta})</span>}
                              </h4>
                              <ul className="space-y-1">
                                {(phase.items || []).map((item, ii) => (
                                  <li key={ii} className="flex items-start gap-2 text-sm">
                                    <input
                                      type="checkbox"
                                      checked={!!item.completed}
                                      onChange={() => toggleRoadmapItemHandler(pi, ii)}
                                      className="mt-1"
                                    />
                                    <span className={`flex-1 ${item.completed ? 'line-through text-gray-500' : 'text-gray-700 dark:text-gray-300'}`}>
                                      {item.text}
                                      {item.priority === 'high' && <span className="mr-2 text-xs text-red-600">[high]</span>}
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ))}
                        </div>
                      ) : healthRoadmap?.roadmap_markdown ? (
                        <pre className="text-sm whitespace-pre-wrap bg-gray-50 dark:bg-gray-900/40 p-3 rounded font-mono max-h-96 overflow-auto">
                          {healthRoadmap.roadmap_markdown}
                        </pre>
                      ) : (
                        <div className="text-center py-6 text-gray-500 text-sm">
                          روadmap موجود نیست — کلیک «🤖 تولید با AI»
                        </div>
                      )}
                    </div>

                    {/* بخش README */}
                    <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3 pb-2 border-b dark:border-gray-700 flex-wrap gap-2">
                        <h3 className="font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                          📖 README
                          {healthReadme?.generated_at && (
                            <span className="text-xs text-gray-500 font-normal">
                              ({fmtDate(healthReadme.generated_at)})
                            </span>
                          )}
                        </h3>
                        <div className="flex gap-2">
                          <button
                            onClick={generateReadme}
                            disabled={!!healthDocsLoading}
                            className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
                          >
                            {healthDocsLoading === 'readme' ? '⏳ در حال تولید...' : '🤖 تولید با AI'}
                          </button>
                          {healthReadme?.readme_markdown && (
                            <button
                              onClick={downloadReadme}
                              className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                            >
                              📥 دانلود
                            </button>
                          )}
                          {!healthReadmeEditing ? (
                            <button
                              onClick={() => {
                                setHealthReadmeDraft(healthReadme?.readme_markdown || '');
                                setHealthReadmeEditing(true);
                              }}
                              className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-xs hover:bg-gray-300 dark:hover:bg-gray-600"
                            >
                              ✏️ ویرایش
                            </button>
                          ) : (
                            <>
                              <button
                                onClick={saveReadmeManual}
                                className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                              >
                                💾 ذخیره
                              </button>
                              <button
                                onClick={() => setHealthReadmeEditing(false)}
                                className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-xs hover:bg-gray-300 dark:hover:bg-gray-600"
                              >
                                لغو
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      {healthReadmeEditing ? (
                        <textarea
                          value={healthReadmeDraft}
                          onChange={e => setHealthReadmeDraft(e.target.value)}
                          rows={25}
                          className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm font-mono"
                        />
                      ) : healthReadme?.readme_markdown ? (
                        <pre className="text-sm whitespace-pre-wrap bg-gray-50 dark:bg-gray-900/40 p-3 rounded font-mono max-h-[500px] overflow-auto">
                          {healthReadme.readme_markdown}
                        </pre>
                      ) : (
                        <div className="text-center py-6 text-gray-500 text-sm">
                          README موجود نیست — کلیک «🤖 تولید با AI»
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Sub-tab: validation chain */}
                {healthSubTab === 'validation' && (
                  <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
                    {!healthChainStatus ? (
                      <div className="text-center text-gray-500 py-8">chain status بارگذاری نشد</div>
                    ) : (
                      <div className="space-y-3">
                        {([
                          { key: 'scan', label: 'Phase 1: Deep Scan', icon: '🔍' },
                          { key: 'codex', label: 'Phase 2: Project Codex', icon: '📚' },
                          { key: 'roadmap', label: 'Phase 3: Roadmap & Ideal State', icon: '🗺️' },
                          { key: 'tasks', label: 'Phase 4: Tasks', icon: '📋' },
                          { key: 'verification', label: 'Phase 5: Verification', icon: '✅' },
                        ] as const).map(p => {
                          const data = healthChainStatus[p.key] || {};
                          const status = data.status || (data.total != null ? 'has_data' : 'never');
                          return (
                            <div key={p.key} className="flex items-center gap-3 p-3 border dark:border-gray-700 rounded">
                              <div className="text-2xl">{p.icon}</div>
                              <div className="flex-1">
                                <div className="font-medium text-gray-800 dark:text-gray-100">{p.label}</div>
                                <div className="text-xs text-gray-500 mt-1">
                                  {p.key === 'scan' && `${data.findings_count || 0} finding · ${data.passes_run || 0} pass`}
                                  {p.key === 'codex' && `${data.files_documented || 0} فایل documented`}
                                  {p.key === 'roadmap' && `${data.phases_count || 0} فاز · ideal state: ${data.ideal_state_set ? 'تعریف شده' : 'تعریف نشده'}`}
                                  {p.key === 'tasks' && `total=${data.total || 0} · pending=${data.pending || 0} · done=${data.done || 0}`}
                                  {p.key === 'verification' && `verified=${data.verified_count || 0} · partial=${data.partial_count || 0}`}
                                </div>
                              </div>
                              <span className={`px-2 py-1 rounded text-xs ${
                                status === 'done' || status === 'has_data' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                              }`}>
                                {status === 'done' || status === 'has_data' ? '✓' : '○'}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Modal جزئیات فایل (heatmap drill-down) */}
            {healthSelectedFile && (() => {
              const fh = healthSummaries?.pass_summaries?.file_health_map?.[healthSelectedFile];
              return (
                <Modal onClose={() => setHealthSelectedFile(null)} title={`📄 ${healthSelectedFile}`}>
                  <div className="space-y-3 text-sm">
                    {fh ? (
                      <>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded" style={{ backgroundColor: fh.hex }} />
                          <div>
                            <div className="text-2xl font-bold">{Math.round(fh.score)}/100</div>
                            <div className="text-xs text-gray-500">color: {fh.color} · {fh.findings_count} finding</div>
                          </div>
                        </div>
                        <div>
                          <strong>severity weighted:</strong> {fh.severity_weighted?.toFixed(2)}
                        </div>
                        <div>
                          <strong>passes touched:</strong> {(fh.passes_touched || []).join(', ') || 'هیچ'}
                        </div>
                      </>
                    ) : (
                      <p>data این فایل در نقشهٔ سلامت موجود نیست.</p>
                    )}
                  </div>
                </Modal>
              );
            })()}
          </div>
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

        {/* 🚀 مودال اجرا با AI روی پروژه — Inspector apply-action bridge */}
        {executeModalOpen && (
          <Modal onClose={closeExecuteModal} title="🚀 اجرا با AI روی پروژه (PR ساخته می‌شود)">
            <div className="space-y-4">
              {/* عنوان تسک */}
              {executeModalTask && (
                <div className="bg-gray-50 dark:bg-gray-900/40 rounded-lg p-3">
                  <div className="text-xs text-gray-500 mb-1">تسک</div>
                  <div className="font-medium text-gray-800 dark:text-gray-100">{executeModalTask.title}</div>
                </div>
              )}

              {/* اطلاعات پروژه */}
              {executeProjectInfo && (
                <div className={`p-3 rounded-lg text-sm ${
                  executeProjectInfo.matched
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200'
                    : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
                }`}>
                  {executeProjectInfo.matched ? (
                    <>✅ پروژه: <strong>{executeProjectInfo.project_name}</strong> · <code className="bg-white/40 dark:bg-black/20 px-1 rounded">{executeProjectInfo.repo_full_name}</code></>
                  ) : (
                    <>❌ {executeProjectInfo.reason}</>
                  )}
                </div>
              )}

              {/* مدل‌های فعال */}
              <div className="text-xs text-gray-500 dark:text-gray-400">
                مدل‌های انتخاب‌شده: {selectedModelIds.length === 0 ? <span className="text-red-600">هیچ — یکی انتخاب کنید</span> : selectedModelIds.join('، ')}
              </div>

              {/* Progress log */}
              {executeProgress.length > 0 && (
                <div className="bg-gray-900 dark:bg-black/50 rounded-lg p-3 max-h-48 overflow-auto">
                  {executeProgress.map((line, i) => (
                    <div key={i} className="text-xs font-mono text-gray-300 leading-relaxed">{line}</div>
                  ))}
                </div>
              )}

              {/* State: preview */}
              {executeStage === 'preview' && executeActionPlan && (
                <div className="border border-purple-200 dark:border-purple-700 rounded-lg p-3">
                  <div className="text-sm font-semibold text-purple-800 dark:text-purple-200 mb-2">
                    📋 پیش‌نمایش تغییرات ({executeActionPlan.files.length} فایل)
                  </div>
                  {executeActionPlan.commit_message && (
                    <div className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                      <strong>پیام commit:</strong> {executeActionPlan.commit_message}
                    </div>
                  )}
                  <div className="space-y-2 max-h-72 overflow-auto">
                    {executeActionPlan.files.map((f, i) => (
                      <details key={i} className="bg-gray-50 dark:bg-gray-900/40 rounded p-2">
                        <summary className="cursor-pointer text-xs">
                          <span className={`px-1.5 py-0.5 rounded mr-2 text-xs ${
                            f.operation === 'create' ? 'bg-green-100 text-green-800 dark:bg-green-900/40' :
                            f.operation === 'delete' ? 'bg-red-100 text-red-800 dark:bg-red-900/40' :
                            f.operation === 'modify_sections' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40' :
                            'bg-blue-100 text-blue-800 dark:bg-blue-900/40'
                          }`}>{f.operation || 'modify'}</span>
                          <code className="text-xs">{f.path}</code>
                        </summary>
                        <pre className="text-xs whitespace-pre-wrap font-mono bg-white dark:bg-black/30 p-2 rounded mt-2 max-h-40 overflow-auto">
                          {f.sections
                            ? f.sections.map((s, si) => `--- بخش ${si + 1} ---\n[find] ${(s.find || '').slice(0, 400)}\n[replace] ${(s.replace || '').slice(0, 400)}`).join('\n\n')
                            : (f.content || '').slice(0, 2000) + ((f.content || '').length > 2000 ? '\n... [TRUNCATED]' : '')}
                        </pre>
                      </details>
                    ))}
                  </div>
                </div>
              )}

              {/* State: done */}
              {executeStage === 'done' && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-4">
                  <div className="text-2xl mb-2">✅</div>
                  <div className="font-semibold text-green-800 dark:text-green-200 mb-1">اعمال موفقیت‌آمیز</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                    <div>📁 فایل‌های commit شده: <strong>{executeFilesCommitted.length}</strong></div>
                    {executePrBranch && <div>🌿 branch: <code className="bg-white/40 dark:bg-black/20 px-1 rounded">{executePrBranch}</code></div>}
                    {executeStartedAt && <div>⏱ زمان: {Math.round((Date.now() - executeStartedAt) / 1000)} ثانیه</div>}
                    <div>🤖 مدل‌ها: {selectedModelIds.join('، ')}</div>
                  </div>
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 italic">
                    💡 verify خودکار بعد از merge شدن PR اجرا می‌شود (یا الان دستی verify کنید).
                  </div>
                </div>
              )}

              {/* State: error */}
              {executeStage === 'error' && executeError && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-3 text-sm text-red-800 dark:text-red-200">
                  ❌ {executeError}
                </div>
              )}

              {/* 🔁 Auto-loop checkbox — فقط در preview، فقط در دور اول */}
              {executeStage === 'preview' && autoLoopRound === 0 && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 rounded-lg p-3">
                  <label className="flex items-start gap-2 cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      checked={autoLoopEnabled}
                      onChange={(e) => {
                        setAutoLoopEnabled(e.target.checked);
                        autoLoopActiveRef.current = e.target.checked;
                      }}
                      className="mt-0.5"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-blue-800 dark:text-blue-200">
                        🔁 اجرای خودکار تا تأیید نهایی (تا {AUTO_LOOP_MAX_ROUNDS} دور)
                      </div>
                      <div className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                        پس از هر apply-action، {AUTO_LOOP_VERIFY_DELAY_MS / 1000} ثانیه صبر، verify خودکار،
                        و اگر done نبود، followup_prompt را از backend می‌گیرد و دور بعدی را trigger می‌کند.
                        می‌توانید هر زمان لغو کنید.
                      </div>
                    </div>
                  </label>
                </div>
              )}

              {/* 🔁 Auto-loop status — در حال countdown یا verify */}
              {(autoLoopStatus === 'waiting_verify' || autoLoopStatus === 'verifying' || autoLoopStatus === 'next_round') && (
                <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800/40 rounded-lg p-3 flex items-center gap-3">
                  <div className="text-purple-700 dark:text-purple-300 font-medium text-sm flex-1">
                    {autoLoopStatus === 'waiting_verify' && (
                      <>⏱ auto-loop دور {autoLoopRound + 1}: verify در {autoLoopCountdown} ثانیه...</>
                    )}
                    {autoLoopStatus === 'verifying' && <>🔍 auto-loop: در حال verify...</>}
                    {autoLoopStatus === 'next_round' && <>🚀 auto-loop: شروع دور {autoLoopRound + 1}...</>}
                  </div>
                  {autoLoopStatus === 'waiting_verify' && (
                    <button
                      onClick={skipCountdownAndVerify}
                      className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700"
                    >
                      ⏭ verify الان
                    </button>
                  )}
                  <button
                    onClick={cancelAutoLoop}
                    className="px-3 py-1 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded text-xs hover:bg-red-200"
                  >
                    🛑 توقف auto-loop
                  </button>
                </div>
              )}

              {/* 🔁 Auto-loop finished/cancelled */}
              {autoLoopStatus === 'finished' && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 rounded-lg p-3 text-sm text-green-800 dark:text-green-200">
                  ✅ auto-loop به تأیید نهایی رسید (پس از {autoLoopRound + 1} دور)
                </div>
              )}
              {autoLoopStatus === 'cancelled' && autoLoopRound >= AUTO_LOOP_MAX_ROUNDS && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg p-3 text-sm text-amber-800 dark:text-amber-200">
                  ⚠️ به max {AUTO_LOOP_MAX_ROUNDS} دور رسیدیم. روی کارت تسک، دکمه‌های پرامپت بعدی را برای ادامهٔ دستی ببینید.
                </div>
              )}

              {/* دکمه‌ها بر اساس state */}
              <div className="flex gap-2 justify-end pt-2 border-t dark:border-gray-700">
                {executeStage === 'preview' && (
                  <>
                    <button
                      onClick={closeExecuteModal}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                    >
                      ❌ لغو
                    </button>
                    <button
                      onClick={confirmAndApply}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                    >
                      🚀 تأیید و اعمال (PR ساخته می‌شود)
                    </button>
                  </>
                )}
                {executeStage === 'done' && (
                  <>
                    {executePrUrl && (
                      <a
                        href={executePrUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                      >
                        🔗 مشاهدهٔ PR
                      </a>
                    )}
                    {executeModalTask && (
                      <button
                        onClick={() => {
                          const taskId = executeModalTask.id;
                          closeExecuteModal();
                          verifyTaskNow(taskId);
                        }}
                        className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm"
                      >
                        🔍 verify الان
                      </button>
                    )}
                    <button
                      onClick={closeExecuteModal}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                    >
                      بستن
                    </button>
                  </>
                )}
                {executeStage === 'error' && (
                  <>
                    <button
                      onClick={() => executeModalTask && openExecuteModal(executeModalTask)}
                      className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 text-sm"
                    >
                      🔁 تلاش مجدد
                    </button>
                    <button
                      onClick={closeExecuteModal}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                    >
                      بستن
                    </button>
                  </>
                )}
                {(executeStage === 'resolving' || executeStage === 'planning' || executeStage === 'applying' || executeStage === 'recording') && (
                  <button
                    onClick={closeExecuteModal}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                  >
                    لغو
                  </button>
                )}
              </div>
            </div>
          </Modal>
        )}

        {/* 📄 مودال مشاهدهٔ پرامپت بعدی (followup) */}
        {viewingFollowupTask && (
          <Modal onClose={() => setViewingFollowupTask(null)} title={`📄 پرامپت ادامه (دور ${viewingFollowupTask.followup_round || 1})`}>
            <div className="space-y-3">
              <div className="text-xs text-gray-600 dark:text-gray-400">
                این پرامپت پس از verify آخر (status={viewingFollowupTask.verification_status || '?'}) به‌طور خودکار توسط AI ساخته شده. تمرکز آن روی AC هایی است که هنوز برآورده نشده‌اند.
                {viewingFollowupTask.followup_generated_at && (
                  <> · 🕐 تولید: {fmtDate(viewingFollowupTask.followup_generated_at)}</>
                )}
              </div>
              <pre className="text-xs whitespace-pre-wrap font-mono bg-gray-50 dark:bg-gray-900/40 p-3 rounded max-h-[60vh] overflow-auto text-gray-800 dark:text-gray-200">
                {viewingFollowupTask.followup_prompt}
              </pre>
              <div className="flex gap-2 justify-end pt-2 border-t dark:border-gray-700">
                <button
                  onClick={() => copyFollowupPrompt(viewingFollowupTask)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 text-sm"
                >
                  📋 کپی
                </button>
                <button
                  onClick={() => {
                    const t = viewingFollowupTask;
                    setViewingFollowupTask(null);
                    openExecuteModalWithFollowup(t);
                  }}
                  disabled={selectedModelIds.length === 0}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm disabled:opacity-50"
                >
                  🚀 اجرا با AI
                </button>
                <button
                  onClick={() => setViewingFollowupTask(null)}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                >
                  بستن
                </button>
              </div>
            </div>
          </Modal>
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

              {viewingReport.user_goal && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-sm border border-blue-200 dark:border-blue-800">
                  <p className="text-xs text-blue-700 dark:text-blue-300 font-medium mb-1">
                    🎯 معیار راهنمای ارزیابی (یادداشت کاربر)
                  </p>
                  <p className="dark:text-blue-100">{viewingReport.user_goal}</p>
                </div>
              )}

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

              {viewingReport.evidence?.criteria_results && (
                <div>
                  <h4 className="text-sm font-medium mb-2 dark:text-gray-200">
                    ✅ نتیجهٔ هر معیار پذیرش
                  </h4>
                  <ul className="space-y-1">
                    {(viewingReport.evidence.criteria_results as any[]).map((cr, i) => (
                      <li
                        key={i}
                        className={`text-sm p-2 rounded ${
                          cr.met
                            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                        }`}
                      >
                        <strong>{cr.met ? '✓' : '✗'}</strong> {cr.criterion}
                        {cr.evidence && (
                          <div className="text-xs opacity-80 mt-1">{cr.evidence}</div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {viewingReport.touched_codex &&
                Object.keys(viewingReport.touched_codex).length > 0 && (
                  <details>
                    <summary className="cursor-pointer text-sm font-medium dark:text-gray-200">
                      📚 شناسنامهٔ بخش‌های لمس‌شده
                    </summary>
                    <div className="mt-2 space-y-2">
                      {Object.keys(viewingReport.touched_codex).map((path) => {
                        const f = viewingReport.touched_codex![path];
                        if (!f) return null;
                        return (
                          <div
                            key={path}
                            className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-xs"
                          >
                            <p className="font-medium dark:text-white" dir="ltr">
                              {path}
                            </p>
                            {f.what_is_it && (
                              <p className="dark:text-gray-300 mt-1">
                                <strong>این چیست:</strong> {f.what_is_it}
                              </p>
                            )}
                            {f.what_it_does && (
                              <p className="dark:text-gray-300">
                                <strong>چه می‌کند:</strong> {f.what_it_does}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </details>
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

        {/* مودال Deep Scan progress */}
        {deepScanWatchedId && (
          <Modal onClose={closeDeepScan} title="🔬 Deep Scan در حال اجرا">
            <DeepScanProgressView progress={deepScanProgress} />
          </Modal>
        )}

        {/* مودال Codex */}
        {codexWatchedId && (
          <Modal onClose={() => setCodexWatchedId(null)} title="📚 شناسنامهٔ پروژه (Codex)">
            <CodexView
              data={codexData}
              loading={codexLoading}
              onRefresh={refreshCodex}
              search={codexSearch}
              onSearch={setCodexSearch}
            />
          </Modal>
        )}

        {/* مودال Verification History */}
        {verifyHistoryTaskId && (
          <Modal
            onClose={() => setVerifyHistoryTaskId(null)}
            title="🕐 تاریخچهٔ verification"
          >
            <VerifyHistoryView data={verifyHistoryData} />
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
  onDeepScan,
  onRunNow,
  onWriteIdea,
  onViewTasks,
  onViewReports,
  onOpenCodex,
}: {
  w: Watched;
  onChange: (updates: Partial<Watched>) => void;
  onRemove: () => void;
  onScan: () => void;
  onDeepScan: () => void;
  onRunNow: () => void;
  onWriteIdea: () => void;
  onViewTasks: () => void;
  onViewReports: () => void;
  onOpenCodex: () => void;
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
        <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block flex items-center gap-1">
          📝 یادداشت من (هدف این پروژه چی بود؟)
          <span
            title="AI این متن را به‌عنوان «هدف اصلی پروژه» در همهٔ تحلیل‌ها، scan‌ها، تولید تسک، verify و گزارش‌ها استفاده می‌کند."
            className="cursor-help text-blue-400"
          >
            ⓘ
          </span>
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
          <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            سطح خودمختاری
            <span
              title="manual: AI فقط بررسی و گزارش می‌دهد. assist: پیشنهاد می‌دهد ولی اعمال نمی‌کند. auto: اجازهٔ اعمال خودکار با opt-in جداگانه (allow_push)"
              className="cursor-help text-blue-400"
            >
              ⓘ
            </span>
          </span>
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
          <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            بازه run (ساعت)
            <span
              title="هر چند ساعت، تسک‌های pending شما اجرا و گزارش‌گیری می‌شوند (فقط در حالت auto)"
              className="cursor-help text-blue-400"
            >
              ⓘ
            </span>
          </span>
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
          <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            بازه scan (ساعت)
            <span
              title="هر چند ساعت، AI خود پروژه را از صفر بررسی می‌کند تا نیازها/مشکلات جدید پیدا کند"
              className="cursor-help text-blue-400"
            >
              ⓘ
            </span>
          </span>
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

      {/* 🆕 (commit 2.3) Scan settings — مهاجرت از Health analysis */}
      <details className="mt-3 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800/40 rounded-lg p-3 text-xs">
        <summary className="cursor-pointer font-medium text-cyan-800 dark:text-cyan-200">
          ⚙️ تنظیمات پیشرفتهٔ scan (عمق + وزن‌های معیار)
        </summary>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="block text-gray-600 dark:text-gray-300 mb-1">
              عمق scan <span className="text-blue-400" title="quick: 3 pass، standard: 5 pass، deep: همه (default)، thorough: همه + per-file scoring">ⓘ</span>
            </span>
            <select
              value={w.scan_depth || 'deep'}
              onChange={(e) => onChange({ scan_depth: e.target.value as any })}
              className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
            >
              <option value="quick">⚡ quick (3 pass — سریع)</option>
              <option value="standard">⚖ standard (5 pass — متعادل)</option>
              <option value="deep">🔍 deep (10 pass — کامل، پیش‌فرض)</option>
              <option value="thorough">🔬 thorough (10 pass + اولویت‌بندی)</option>
            </select>
          </label>
          <div className="text-xs text-gray-500 dark:text-gray-400 self-end">
            وزن‌های معیار را تنظیم کنید تا scoring per-file به اولویت‌های شما حساس باشد:
          </div>
          {(['security', 'quality', 'tests', 'completeness'] as const).map(key => {
            const weights = w.scan_criteria_weights || {};
            const value = weights[key] ?? (key === 'security' ? 1.5 : key === 'tests' ? 1.2 : 1.0);
            const labels: Record<string, string> = {
              security: '🔒 امنیت', quality: '🛠 کیفیت',
              tests: '🧪 تست', completeness: '✅ کامل بودن',
            };
            return (
              <label key={key} className="block">
                <span className="block text-gray-600 dark:text-gray-300 mb-1">
                  {labels[key]}: <strong>{value.toFixed(1)}×</strong>
                </span>
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={0.1}
                  value={value}
                  onChange={(e) => {
                    const newWeights = { ...weights, [key]: parseFloat(e.target.value) };
                    onChange({ scan_criteria_weights: newWeights });
                  }}
                  className="w-full"
                />
              </label>
            );
          })}
        </div>
        <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          💡 این تنظیمات روی scan های آینده اعمال می‌شوند. scan فعلی (اگر در حال اجراست) تأثیر نمی‌گیرد.
        </div>
      </details>

      {/* execution mode + verify interval + verify_only_mode */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            مسیر اجرا
            <span
              title="manual: تسک‌ها را خودتان بیرون اعمال می‌کنید (با Cursor/ChatGPT/...) و سیستم فقط verify می‌کند. auto_via_projects_page: از طریق صفحهٔ /projects اعمال شود. auto_via_pr: AI خودش PR می‌سازد."
              className="cursor-help text-blue-400"
            >
              ⓘ
            </span>
          </span>
          <select
            value={w.default_execution_mode || 'manual'}
            onChange={(e) =>
              onChange({ default_execution_mode: e.target.value as any })
            }
            className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          >
            <option value="manual">manual (اعمال بیرونی)</option>
            <option value="auto_via_projects_page">auto via /projects</option>
            <option value="auto_via_pr">auto via PR</option>
          </select>
        </label>
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            بازه verify (ساعت)
            <span
              title="هر چند ساعت، تسک‌های اعمال‌شده (یا نشده) دوباره بررسی می‌شوند تا تأیید نهایی - مستقل از روش اعمال"
              className="cursor-help text-blue-400"
            >
              ⓘ
            </span>
          </span>
          <input
            type="number"
            min="1"
            defaultValue={w.verify_interval_hours ?? 12}
            onBlur={(e) => {
              const v = parseFloat(e.target.value) || 12;
              if (v !== (w.verify_interval_hours ?? 12))
                onChange({ verify_interval_hours: v });
            }}
            className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
          />
        </label>
        <label className="text-xs flex items-center gap-2 mt-5">
          <input
            type="checkbox"
            checked={!!w.verify_only_mode}
            onChange={(e) => onChange({ verify_only_mode: e.target.checked })}
            className="w-4 h-4"
          />
          <span
            className="dark:text-gray-200"
            title="اگر فعال باشد، scheduler هرگز apply نمی‌کند، فقط verify می‌کند"
          >
            فقط verify (هرگز apply نکن)
          </span>
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
          onClick={onDeepScan}
          title="اسکن چندفازی عمیق روی همهٔ فایل‌ها/صفحات/روتها با progress زنده"
          className="px-3 py-1.5 bg-indigo-500 text-white rounded text-sm hover:bg-indigo-600"
        >
          🔬 Deep Scan
        </button>
        <button
          onClick={onScan}
          title="اسکن سادهٔ سریع (تک پاس) برای یافتن نیازهای کلی"
          className="px-3 py-1.5 bg-cyan-500 text-white rounded text-sm hover:bg-cyan-600"
        >
          🔎 اسکن سریع
        </button>
        <button
          onClick={onRunNow}
          className="px-3 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
        >
          ▶ بررسی فوری
        </button>
        <button
          onClick={onWriteIdea}
          className="px-3 py-1.5 bg-purple-500 text-white rounded text-sm hover:bg-purple-600"
        >
          💡 نوشتن ایده
        </button>
        <button
          onClick={onOpenCodex}
          title="شناسنامهٔ خودکار پروژه - توضیح هر فایل/فیچر"
          className="px-3 py-1.5 bg-amber-500 text-white rounded text-sm hover:bg-amber-600"
        >
          📚 شناسنامه
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
  onVerify,
  onMarkExternal,
  onCopyPrompt,
  onShowHistory,
  onExecuteWithAi,
  onCopyFollowup,
  onExecuteFollowupWithAi,
  onViewFollowup,
  followupCopyFeedbackId,
  taskReportCache,
  taskReportLoading,
  fetchLatestReportForTask,
  executeDisabledReason,
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
  onVerify: (id: string) => void;
  onMarkExternal: (id: string) => void;
  onCopyPrompt: (id: string) => void;
  onShowHistory: (id: string) => void;
  onExecuteWithAi: (t: Task) => void;
  onCopyFollowup: (t: Task) => void;
  onExecuteFollowupWithAi: (t: Task) => void;
  onViewFollowup: (t: Task) => void;
  followupCopyFeedbackId: string | null;
  taskReportCache: Record<string, any>;
  taskReportLoading: Record<string, boolean>;
  fetchLatestReportForTask: (taskId: string) => void;
  executeDisabledReason: string;
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
              onClick={() => onCopyPrompt(t.id)}
              title="کپی پرامپت کامل برای استفاده در ابزار خارجی (Cursor، ChatGPT، ...)"
              className="px-3 py-1 bg-purple-500 text-white rounded text-xs hover:bg-purple-600"
            >
              📋 کپی پرامپت
            </button>
            {t.execution_mode !== 'manual' ? (
              <button
                onClick={() => onRun(t.id)}
                disabled={isRunning}
                title="apply خودکار توسط AI"
                className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600 disabled:opacity-50"
              >
                {isRunning ? '⏳' : '▶'} اعمال خودکار
              </button>
            ) : (
              <button
                onClick={() => onMarkExternal(t.id)}
                disabled={!!t.manually_marked_applied_at}
                title="من این تسک را بیرون از سیستم اعمال کرده‌ام"
                className="px-3 py-1 bg-emerald-500 text-white rounded text-xs hover:bg-emerald-600 disabled:opacity-50"
              >
                🔖 من اعمال کردم
              </button>
            )}
            <button
              onClick={() => onVerify(t.id)}
              disabled={isRunning}
              title="بررسی الان: آیا کار انجام شده؟ مستقل از روش execution"
              className="px-3 py-1 bg-cyan-500 text-white rounded text-xs hover:bg-cyan-600 disabled:opacity-50"
            >
              🔍 verify
            </button>
            <button
              onClick={() => onExecuteWithAi(t)}
              disabled={!!executeDisabledReason}
              title={
                executeDisabledReason
                  ? executeDisabledReason
                  : 'این تسک را به Inspector پروژه می‌فرستد، AI کد تولید می‌کند، PR ساخته می‌شود'
              }
              className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50"
            >
              🚀 اجرا با AI
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
              onClick={() => onShowHistory(t.id)}
              title="تاریخچهٔ verification"
              className="px-3 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded text-xs hover:bg-amber-200"
            >
              🕐
            </button>
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
        {/* نشانگر execution mode + verification status + streak */}
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
          <span
            className={`px-1.5 py-0.5 rounded ${
              t.execution_mode === 'manual'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
            }`}
            title={
              t.execution_mode === 'manual'
                ? 'manual: کاربر بیرون اعمال می‌کند، فقط verify می‌شود'
                : 'auto: AI خودش اعمال می‌کند'
            }
          >
            {t.execution_mode === 'manual'
              ? '✋ manual'
              : t.execution_mode === 'auto_via_pr'
              ? '🔀 auto-PR'
              : '⚡ auto'}
          </span>
          {t.verification_status && t.verification_status !== 'pending' && (
            <span className="px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
              verify: {t.verification_status}
            </span>
          )}
          {(t.confirmation_streak ?? 0) > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">
              ✓ streak {t.confirmation_streak}
            </span>
          )}
          {/* 🔗 PR badge — تسک از طریق Inspector apply-action اجرا شده */}
          {t.applied_evidence?.pr_url && (
            <a
              href={t.applied_evidence.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/60"
              title={
                `PR ساخته شده توسط ${t.applied_evidence.executed_via || 'inspector_apply_action'}\n` +
                `branch: ${t.applied_evidence.pr_branch || '(نامشخص)'}\n` +
                `${(t.applied_evidence.files_committed || []).length} فایل commit شده\n` +
                `زمان: ${t.applied_evidence.executed_at || '(نامشخص)'}\n` +
                `کلیک: باز کردن PR در GitHub`
              }
            >
              🔗 PR
            </a>
          )}
          {/* در انتظار merge / verify */}
          {t.verification_status === 'applied_externally_pending_verify' && t.applied_evidence?.pr_url && (
            <span
              className="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300"
              title="PR ساخته شده ولی هنوز merge/verify نشده. پس از merge، verify خودکار اجرا می‌شود."
            >
              ⏳ در انتظار merge
            </span>
          )}
          {t.manually_marked_applied_at && (
            <span className="px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300">
              🔖 منتظر verify بعدی
            </span>
          )}
          {/* 🔁 followup badge — وقتی پرامپت ادامه آماده است */}
          {t.followup_prompt && t.followup_prompt.length > 50 && (
            <span
              className="px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300"
              title="پرامپت ادامه (با تمرکز روی AC های ناموفق) آماده است. پایین‌تر دکمه‌های کپی/اجرا را ببینید."
            >
              📄 پرامپت بعدی (دور {t.followup_round || 1})
            </span>
          )}
        </div>

        {/* 📋 جزئیات آخرین verify — expandable */}
        {t.last_verification_report_id && (
          <details
            className="mt-3 bg-gray-50 dark:bg-gray-900/40 rounded-lg p-2"
            onToggle={(e) => {
              const el = e.currentTarget as HTMLDetailsElement;
              if (el.open && !taskReportCache[t.id] && !taskReportLoading[t.id]) {
                fetchLatestReportForTask(t.id);
              }
            }}
          >
            <summary className="cursor-pointer text-xs text-gray-700 dark:text-gray-300 font-medium select-none">
              📋 جزئیات آخرین verify
              {taskReportCache[t.id]?.status && (
                <span className={`mr-2 px-1.5 py-0.5 rounded text-xs ${
                  taskReportCache[t.id].status === 'done' ? 'bg-green-100 text-green-700 dark:bg-green-900/40' :
                  taskReportCache[t.id].status === 'partial' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40' :
                  taskReportCache[t.id].status === 'regressed' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40' :
                  'bg-red-100 text-red-700 dark:bg-red-900/40'
                }`}>
                  {taskReportCache[t.id].status}
                  {typeof taskReportCache[t.id].confidence_score === 'number' && (
                    <> · {Math.round((taskReportCache[t.id].confidence_score || 0) * 100)}%</>
                  )}
                </span>
              )}
              <span className="text-gray-500 mr-1 text-[10px]">(کلیک برای جزئیات)</span>
            </summary>
            <div className="mt-2 space-y-2 text-xs">
              {taskReportLoading[t.id] && <div className="text-gray-500">⏳ در حال بارگذاری گزارش...</div>}
              {taskReportCache[t.id] && (() => {
                const r = taskReportCache[t.id];
                return (
                  <>
                    {r.summary && (
                      <div>
                        <div className="font-semibold text-gray-800 dark:text-gray-200 mb-1">📝 خلاصه:</div>
                        <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">{r.summary}</div>
                      </div>
                    )}
                    {Array.isArray(r.done_parts) && r.done_parts.length > 0 && (
                      <div>
                        <div className="font-semibold text-green-700 dark:text-green-300 mb-1">✅ انجام‌شده ({r.done_parts.length}):</div>
                        <ul className="list-disc pr-5 space-y-0.5 text-gray-700 dark:text-gray-300">
                          {r.done_parts.map((p: string, i: number) => <li key={i}>{p}</li>)}
                        </ul>
                      </div>
                    )}
                    {Array.isArray(r.remaining_parts) && r.remaining_parts.length > 0 && (
                      <div>
                        <div className="font-semibold text-orange-700 dark:text-orange-300 mb-1">⏳ باقی‌مانده ({r.remaining_parts.length}):</div>
                        <ul className="list-disc pr-5 space-y-0.5 text-gray-700 dark:text-gray-300">
                          {r.remaining_parts.map((p: string, i: number) => <li key={i}>{p}</li>)}
                        </ul>
                      </div>
                    )}
                    {Array.isArray(r.next_actions) && r.next_actions.length > 0 && (
                      <div>
                        <div className="font-semibold text-blue-700 dark:text-blue-300 mb-1">🪜 اقدامات بعدی پیشنهادی:</div>
                        <ul className="list-disc pr-5 space-y-0.5 text-gray-700 dark:text-gray-300">
                          {r.next_actions.map((p: string, i: number) => <li key={i}>{p}</li>)}
                        </ul>
                      </div>
                    )}
                    {r.evidence && (Object.keys(r.evidence).length > 0) && (
                      <div>
                        <div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">📁 شواهد:</div>
                        <pre className="text-[10px] bg-white dark:bg-black/30 p-2 rounded font-mono whitespace-pre-wrap max-h-32 overflow-auto">
                          {JSON.stringify(r.evidence, null, 2).slice(0, 1000)}
                        </pre>
                      </div>
                    )}
                    {r.model_id && (
                      <div className="text-[10px] text-gray-500 dark:text-gray-400">
                        🤖 verifier model: <code className="bg-white dark:bg-black/30 px-1 rounded">{r.model_id}</code>
                        {r.run_at && <> · 🕐 {fmtDate(r.run_at)}</>}
                      </div>
                    )}
                  </>
                );
              })()}
              {!taskReportLoading[t.id] && !taskReportCache[t.id] && (
                <div className="text-gray-500">گزارش هنوز fetch نشده — کلیک کنید.</div>
              )}
            </div>
          </details>
        )}

        {/* 🔁 ردیف دکمه‌های follow-up — فقط در حالت partial/not_done/regressed */}
        {t.followup_prompt && t.followup_prompt.length > 50 &&
         ['partial', 'not_done', 'regressed', 'error', 'needs_clarification'].includes(t.verification_status || '') && (
          <div className="mt-3 pt-2 border-t border-orange-200 dark:border-orange-800/40 flex flex-wrap gap-1.5">
            <span className="text-xs text-orange-700 dark:text-orange-300 font-medium ml-2">
              🔁 پرامپت ادامه آماده (دور {t.followup_round || 1}):
            </span>
            <button
              onClick={() => onCopyFollowup(t)}
              title="کپی پرامپت ادامه — برای اعمال در ابزار خارجی (Cursor / ChatGPT) و رفع AC های باقی‌مانده"
              className="px-3 py-1 bg-orange-500 text-white rounded text-xs hover:bg-orange-600"
            >
              📋 {followupCopyFeedbackId === t.id ? 'کپی شد ✓' : 'کپی پرامپت بعدی'}
            </button>
            <button
              onClick={() => onExecuteFollowupWithAi(t)}
              disabled={!!executeDisabledReason}
              title={executeDisabledReason || 'اجرای دور بعدی با AI — PR جدید روی همان repo ساخته می‌شود'}
              className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50"
            >
              🚀 اجرای پرامپت بعدی با AI
            </button>
            <button
              onClick={() => onViewFollowup(t)}
              title="مشاهدهٔ متن کامل پرامپت ادامه"
              className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-xs hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              👁 مشاهده
            </button>
          </div>
        )}
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

const PASS_LABELS: Record<string, string> = {
  init: 'آماده‌سازی',
  phase1_structure: 'بارگذاری ساختار پروژه',
  phase2_scoring: 'انتخاب فایل‌های کلیدی',
  phase2_reading: 'خواندن فایل‌های کلیدی',
  phase3_frontend: 'A — تحلیل Frontend',
  phase3_backend: 'B — تحلیل Backend',
  phase3_cross_stack: 'C — سازگاری Frontend↔Backend',
  phase3_security: 'D — امنیت',
  phase3_integrity: 'E — یکپارچگی Cross-cutting',
  phase3_quality: 'F — کیفیت کد',
  phase3_dependency: 'G — Dependency',
  phase3_completeness: 'H — Completeness',
  phase4_aggregate: 'تجمیع و dedup',
  completed: '✅ کامل شد',
  queued: 'در صف',
};

function DeepScanProgressView({ progress }: { progress: any }) {
  if (!progress) {
    return <p className="text-center text-gray-400 py-4">در حال شروع...</p>;
  }
  const phase = progress.phase || 'init';
  const passes_total = progress.passes_total || 8;
  const passes_done = progress.passes_done || 0;
  const pct = Math.min(
    100,
    Math.max(
      progress.status === 'completed' ? 100 : 0,
      Math.round((passes_done / Math.max(passes_total, 1)) * 100),
    ),
  );
  const isError = progress.status === 'error';
  const isDone = progress.status === 'completed';

  return (
    <div className="space-y-3">
      <div className="text-center">
        <div className="text-2xl mb-1">
          {isDone ? '✅' : isError ? '❌' : '🔬'}
        </div>
        <p className="font-bold dark:text-white">
          {PASS_LABELS[phase] || phase}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {progress.message || ''}
        </p>
      </div>

      <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            isError ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-indigo-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded">
          <div className="text-xs text-gray-500">فایل‌ها</div>
          <div className="font-bold dark:text-white">
            {progress.files_analyzed ?? 0} / {progress.files_total ?? 0}
          </div>
        </div>
        <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded">
          <div className="text-xs text-gray-500">فازها</div>
          <div className="font-bold dark:text-white">
            {passes_done} / {passes_total}
          </div>
        </div>
        <div className="p-2 bg-cyan-50 dark:bg-cyan-900/20 rounded">
          <div className="text-xs text-gray-500">یافته</div>
          <div className="font-bold dark:text-white">
            {progress.findings_count ?? 0}
          </div>
        </div>
        <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded">
          <div className="text-xs text-gray-500">critical</div>
          <div className="font-bold text-red-600 dark:text-red-300">
            {progress.critical_count ?? 0}
          </div>
        </div>
      </div>

      {progress.stacks && progress.stacks.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Stack تشخیص داده شده:</p>
          <div className="flex flex-wrap gap-1">
            {progress.stacks.map((s: string) => (
              <span
                key={s}
                className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {isDone && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded text-sm dark:text-green-200">
          ✅ {progress.tasks_created ?? 0} تسک پیشنهادی ساخته شد. به تب «تسک‌ها» بروید.
        </div>
      )}
    </div>
  );
}

function CodexView({
  data,
  loading,
  onRefresh,
  search,
  onSearch,
}: {
  data: any;
  loading: boolean;
  onRefresh: () => void;
  search: string;
  onSearch: (s: string) => void;
}) {
  const files = data?.files || {};
  const filtered = Object.keys(files).filter(
    (p) => !search || p.toLowerCase().includes(search.toLowerCase()),
  );

  const exportMd = () => {
    const lines: string[] = [];
    lines.push(`# 📚 Codex — ${data?.repo || ''}`);
    if (data?.user_goal) lines.push(`\n> 🎯 ${data.user_goal}\n`);
    if (data?.stacks?.length) lines.push(`Stack: ${data.stacks.join(', ')}\n`);
    Object.keys(files).forEach((path) => {
      const f = files[path];
      lines.push(`\n## ${path}`);
      lines.push(`- **این چیست؟** ${f.what_is_it || ''}`);
      lines.push(`- **چه می‌کند؟** ${f.what_it_does || ''}`);
      if (f.use_cases?.length)
        lines.push(`- **کاربردها:**\n${f.use_cases.map((u: string) => `  - ${u}`).join('\n')}`);
      lines.push(`- **روابط:** ${f.relations || ''}`);
      lines.push(`- **در صورت حذف:** ${f.breaks_if_removed || ''}`);
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `codex-${(data?.repo || 'project').replace('/', '-')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h3 className="font-bold dark:text-white" dir="ltr">
            {data?.repo || ''}
          </h3>
          {data?.user_goal && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              🎯 {data.user_goal}
            </p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            {Object.keys(files).length} فایل مستند شده
            {data?.updated_at ? ` · ${new Date(data.updated_at).toLocaleString('fa-IR')}` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="px-3 py-1 bg-amber-500 text-white rounded text-sm hover:bg-amber-600 disabled:opacity-50"
          >
            {loading ? '⏳ در حال ساخت...' : '🪄 به‌روزرسانی با AI'}
          </button>
          <button
            onClick={exportMd}
            disabled={!Object.keys(files).length}
            className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:opacity-50"
          >
            ↓ Markdown
          </button>
        </div>
      </div>

      {Object.keys(files).length > 0 && (
        <input
          type="text"
          placeholder="🔍 جستجو در فایل‌ها..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
        />
      )}

      {Object.keys(files).length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <div className="text-4xl mb-2">📭</div>
          <p>Codex هنوز ساخته نشده</p>
          <p className="text-xs mt-1">روی «به‌روزرسانی با AI» کلیک کنید</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[60vh] overflow-auto">
          {filtered.map((path) => {
            const f = files[path];
            return (
              <details
                key={path}
                className="bg-gray-50 dark:bg-gray-700/50 rounded p-2"
              >
                <summary className="cursor-pointer text-sm font-medium dark:text-white" dir="ltr">
                  {path}
                </summary>
                <div className="mt-2 text-xs space-y-1 dark:text-gray-200" dir="rtl">
                  {f?.what_is_it && (
                    <div>
                      <strong>این چیست؟</strong> {f.what_is_it}
                    </div>
                  )}
                  {f?.what_it_does && (
                    <div>
                      <strong>چه می‌کند؟</strong> {f.what_it_does}
                    </div>
                  )}
                  {f?.use_cases?.length > 0 && (
                    <div>
                      <strong>کاربردها:</strong>
                      <ul className="list-disc mr-4">
                        {f.use_cases.map((u: string, i: number) => (
                          <li key={i}>{u}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {f?.relations && (
                    <div>
                      <strong>روابط:</strong> {f.relations}
                    </div>
                  )}
                  {f?.breaks_if_removed && (
                    <div>
                      <strong>در صورت حذف:</strong> {f.breaks_if_removed}
                    </div>
                  )}
                </div>
              </details>
            );
          })}
        </div>
      )}
    </div>
  );
}

function VerifyHistoryView({ data }: { data: any }) {
  if (!data) return <p className="text-center text-gray-400">در حال بارگذاری...</p>;
  const history = data.history || [];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 text-center text-sm">
        <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded">
          <div className="text-xs text-gray-500">وضعیت</div>
          <div className="font-bold dark:text-white">{data.verification_status}</div>
        </div>
        <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded">
          <div className="text-xs text-gray-500">streak</div>
          <div className="font-bold text-green-700 dark:text-green-300">
            {data.confirmation_streak || 0}
          </div>
        </div>
        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
          <div className="text-xs text-gray-500">verify ها</div>
          <div className="font-bold text-blue-700 dark:text-blue-300">
            {history.length}
          </div>
        </div>
      </div>

      {data.manually_marked_applied_at && (
        <div className="p-2 bg-purple-50 dark:bg-purple-900/20 text-sm rounded">
          🔖 کاربر گفته اعمال شده در:{' '}
          {new Date(data.manually_marked_applied_at).toLocaleString('fa-IR')}
        </div>
      )}

      {history.length === 0 ? (
        <p className="text-center text-gray-400 py-4">هنوز verify انجام نشده</p>
      ) : (
        <div className="space-y-2">
          {history
            .slice()
            .reverse()
            .map((h: any, i: number) => (
              <div
                key={i}
                className="border-r-2 border-blue-400 pr-3 py-1 bg-gray-50 dark:bg-gray-700/40 rounded text-sm"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      h.status === 'done'
                        ? 'bg-green-100 text-green-700'
                        : h.status === 'partial'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {h.status}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(h.verified_at).toLocaleString('fa-IR')}
                  </span>
                  {h.triggered_by && (
                    <span className="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 dark:text-gray-200 rounded">
                      {h.triggered_by}
                    </span>
                  )}
                </div>
                {h.summary && (
                  <p className="text-xs mt-1 dark:text-gray-300">{h.summary}</p>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
