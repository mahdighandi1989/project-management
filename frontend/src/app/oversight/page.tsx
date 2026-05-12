'use client';

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import Link from 'next/link';
import TaskFilePicker, { type UploadSessionState } from '@/components/TaskFilePicker';
import ExtractedFilesPanel from '@/components/ExtractedFilesPanel';

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
  scan_criteria_weights?: {
    security?: number;
    quality?: number;
    tests?: number;
    completeness?: number;
    // 🆕 (P3) dimensions جدید
    logical_alignment?: number;
    functional_correctness?: number;
  };
  // 🆕 (auto-loop) ping-pong scheduler-driven
  auto_continue_until_done?: boolean;
  max_auto_loop_rounds?: number;
  // 🆕 (P1) مدل‌های auto-scan
  selected_models?: string[];
  // 🆕 (Creator) منبع auto-add
  auto_added_source?: 'creator_via_web' | 'creator_via_telegram' | 'github_import' | 'manual_api' | string | null;
  // 🆕 (Smart Task Lifecycle)
  auto_regenerate_old_prompts?: boolean;
  prompt_quality_threshold?: number;
  last_prompt_audit_at?: string | null;
  dedup_in_manual_create?: boolean;
  dedup_score_threshold?: number;
  // 🆕 (P4) خلاصهٔ آخرین scan
  last_scan_metadata?: {
    model_used?: string;
    models_used_list?: string[];
    scan_depth?: string;
    passes_run?: number;
    passes_total?: number;
    files_analyzed_count?: number;
    findings_count?: number;
    tasks_created?: number;
    duplicates_skipped?: number;
    critical_count?: number;
    scan_id?: string;
    completed_at?: string;
    pass_breakdown?: Record<string, number>;
  } | null;
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
  archived?: boolean;
  archived_at?: string | null;
  // 🆕 (P1) metadata scan که این task را ساخته
  created_by_scan_metadata?: {
    model?: string;
    models_used_list?: string[];
    depth?: string;
    passes?: number;
    passes_total?: number;
    files_count?: number;
    scan_id?: string;
    scanned_at?: string;
    _pass?: string;
  } | null;
  // 🆕 (P2) cross-scan tracking
  scan_seen_count?: number;
  last_seen_in_scan_at?: string | null;
  prompt_history?: Array<{
    prompt: string;
    raw_idea: string;
    model_id: string;
    generated_at: string;
    source?: string;  // 'regenerate' | 'followup_round_N' | undefined (اولیه)
  }>;
  last_verification_report_id?: string | null;
  // 🆕 (Smart Task Lifecycle)
  merge_count?: number;
  manual_seen_count?: number;
  prompt_quality_score?: number | null;
  last_quality_audit_at?: string | null;
  // 🆕 (Inspector → Oversight)
  inspector_context_id?: string | null;
  inspector_mode?: 'chat' | 'visual_debug' | null;
  inspector_meta_summary?: string | null;
  raw_idea_history?: Array<{
    ts: string;
    source: string;
    raw_idea: string;
    candidate_title?: string;
    merged_fields?: string[];
    similarity_score?: number;
  }>;
  // 🆕 (Multi-pass Checklist) — مراحل تسک با وضعیت per-step که verifier به‌روز می‌کند
  task_steps?: Array<{
    id: number;
    title: string;
    scope?: string;
    raw_excerpt?: string;
    key_terms?: string[];
    status: 'pending' | 'done' | 'partial' | 'not_done' | 'error';
    completion_pct: number;
    remaining?: string;
    evidence?: string;
    last_verified_at?: string | null;
    completed_at?: string | null;
  }>;
  overall_completion_pct?: number | null;
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
  const [tab, setTab] = useState<'watched' | 'repos' | 'ideas' | 'tasks' | 'reports'>('watched');

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

  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskFilterStatus, setTaskFilterStatus] = useState<string>('all');
  const [taskFilterWatched, setTaskFilterWatched] = useState<string>('all');
  // 🆕 (P3) فیلتر archived: 'active' | 'archived' | 'all' — default: active
  const [taskFilterArchived, setTaskFilterArchived] = useState<'active' | 'archived' | 'all'>('active');
  // 🆕 (P4) modal state برای regenerate prompt
  const [regenTask, setRegenTask] = useState<Task | null>(null);
  const [regenRawIdea, setRegenRawIdea] = useState<string>('');
  const [regenLoading, setRegenLoading] = useState(false);
  const [regenError, setRegenError] = useState<string>('');
  const [historyTask, setHistoryTask] = useState<Task | null>(null);
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
  // 🆕 (Stage 3 — File Attachment) — یک taskDraftId پایدار برای گروه فایل‌ها
  // در طول lifecycle این فرم. وقتی تسک ساخته می‌شود یا کاربر idea را reset کند،
  // یک id جدید تولید می‌شود.
  const [taskDraftId, setTaskDraftId] = useState<string>(() => {
    try {
      const saved = sessionStorage.getItem('oversight-current-task-draft-id');
      if (saved) return saved;
    } catch {}
    const v = `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    try { sessionStorage.setItem('oversight-current-task-draft-id', v); } catch {}
    return v;
  });
  const [uploadedSessions, setUploadedSessions] = useState<UploadSessionState[]>([]);
  // 🆕 (Stage 8) — modal برای پیشنهاد فعال‌سازی موقت مدل بصری
  const [modelBlockModal, setModelBlockModal] = useState<{
    candidates: Array<{ id: string; name: string; provider: string; priority: number }>;
    mime_type?: string;
    session_id?: string;
  } | null>(null);
  // 🆕 (audit fix) — اگر کاربر از طریق modal toggle مدلی را موقتاً فعال کرد،
  // model_id آن اینجا ذخیره می‌شود تا پس از اتمام (save یا cancel) خودکار
  // revert شود.
  const [tempActivatedModelId, setTempActivatedModelId] = useState<string | null>(null);

  // helper: revert temp-activated model (silent، best-effort)
  const revertTempActivatedIfAny = useCallback(async () => {
    if (!tempActivatedModelId) return;
    const mid = tempActivatedModelId;
    setTempActivatedModelId(null);
    try {
      await fetch(
        `${API_BASE}/api/oversight/models/${encodeURIComponent(mid)}/temp-revert?trigger=ui-task-create-done`,
        { method: 'POST' },
      );
    } catch {
      // ignore — best effort. اگر شکست خورد، در DB stale می‌ماند ولی boot
      // recovery پاکش می‌کند.
    }
  }, [tempActivatedModelId]);
  const resetTaskDraft = useCallback(() => {
    const v = `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    try { sessionStorage.setItem('oversight-current-task-draft-id', v); } catch {}
    setTaskDraftId(v);
    setUploadedSessions([]);
  }, []);
  const [ideaType, setIdeaType] = useState('idea');
  const [ideaPriority, setIdeaPriority] = useState('medium');
  const [ideaDeadline, setIdeaDeadline] = useState('');
  // 🆕 (Multi-pass) حالت تبدیل ایده به پرامپت
  // "auto" = heuristic، "always" = همیشه تقسیم مرحله‌ای، "never" = single-pass
  const [multiPassMode, setMultiPassMode] = useState<'auto' | 'always' | 'never'>('auto');
  const [generating, setGenerating] = useState(false);
  const [genPhase, setGenPhase] = useState('');
  const [genPct, setGenPct] = useState(0);
  const [previewPrompt, setPreviewPrompt] = useState<{
    title: string;
    prompt: string;
    task_steps?: any[];
    overall_completion_pct?: number;
  } | null>(null);

  // 🆕 (Smart Task Lifecycle) Dedup state — وقتی save تسک با duplicate_detected برمی‌گردد
  const [duplicatePrompt, setDuplicatePrompt] = useState<null | {
    watched_id: string | null;
    title: string;
    prompt: string;
    raw_idea: string;
    type: string;
    priority: string;
    matches: Array<{
      task_id: string;
      title: string;
      score: number;
      title_jaccard: number;
      idea_overlap: number;
      ac_overlap: number;
      reasons: string[];
    }>;
  }>(null);
  // similarity preview (debounced check before submit)
  const [similarityHints, setSimilarityHints] = useState<Array<{
    task_id: string;
    title: string;
    score: number;
  }>>([]);

  // merge preview modal
  const [mergeModal, setMergeModal] = useState<null | {
    existingTaskId: string;
    candidate: {
      title: string;
      raw_idea: string;
      prompt: string;
      acceptance_criteria?: string[];
      target_files?: string[];
    };
    similarity_score: number;
    preview: any | null;  // MergePreview dict
    loading: boolean;
    choices: Record<string, 'existing' | 'candidate' | 'ai_merged'>;
  }>(null);

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
          // 🆕 archived=all تا هم active هم archived بیاید و فیلتر سمت کلاینت کار کند
          fetch(`${API_BASE}/api/oversight/tasks?archived=all`),
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
    // 🆕 archived=all تا فیلتر آرشیو در UI کار کند
    const r = await fetch(`${API_BASE}/api/oversight/tasks?archived=all`);
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
    // 🛡 (audit fix) — pollInterval را خارج از try/finally نگه دار تا
    // در catch/finally هم قابل پاک کردن باشد.
    let pollInterval: any = null;
    try {
      // برای multi-project: یک پرامپت تولید می‌شود اما هنگام ذخیره برای هر پروژه یکی ساخته می‌شود
      const firstId = ideaWatchedIds[0] || null;
      setTimeout(() => setGenPhase('در حال ساخت پرامپت قدرتمند...'), 800);
      // 🆕 (Stage 7) — sessionهای آپلود کامل‌شده (completed/extracting/extracted)
      // را به idea_to_prompt می‌فرستیم تا extraction قبل از پرامپت‌سازی انجام شود
      const validSessionIds = uploadedSessions
        .filter((s) => ['completed', 'extracting', 'extracted'].includes(s.status))
        .sort((a, b) => a.file_order - b.file_order)
        .map((s) => s.session_id);
      // 🆕 (Stage 6 — Progress) اگر فایل پیوست شده، progress live را poll کن
      if (validSessionIds.length > 0) {
        pollInterval = setInterval(async () => {
          try {
            const pr = await fetch(`${API_BASE}/api/oversight/progress/${taskDraftId}`);
            if (pr.ok) {
              const pd = await pr.json();
              if (pd.found) {
                setGenPhase(`${pd.stage}: ${pd.detail || ''}`);
                if (typeof pd.percent === 'number') setGenPct(Math.max(8, Math.min(99, pd.percent)));
                if (pd.completed) {
                  clearInterval(pollInterval);
                  pollInterval = null;
                }
              }
            }
          } catch {}
        }, 2000);
      }
      // 🛡 (audit fix #3 + HIGH #1) — اگر فایل پیوست شده و کاربر در حالت 'auto'
      // است (نه explicit 'never')، multi_pass را به 'always' override کن.
      // اگر کاربر صراحتاً 'never' را انتخاب کرده، انتخابش محترم است.
      const effectiveMultiPassMode =
        validSessionIds.length && multiPassMode === 'auto'
          ? 'always'
          : multiPassMode;
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
          multi_pass_mode: effectiveMultiPassMode,
          upload_session_ids: validSessionIds.length ? validSessionIds : undefined,
          progress_track_id: validSessionIds.length ? taskDraftId : undefined,
        }),
      });
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      if (res.ok) {
        const data = await res.json();
        setPreviewPrompt({
          title: data.title,
          prompt: data.prompt,
          task_steps: data.task_steps || [],
          overall_completion_pct: data.overall_completion_pct,
        });
        setGenPhase('پرامپت آماده شد');
        setGenPct(100);
        // 🆕 (Smart Task Lifecycle) اگر AI نتوانست JSON معتبر تولید کند،
        // backend پرامپت minimal با _quality_flag برمی‌گرداند.
        if (data._quality_flag === 'json_parse_failed') {
          showError(
            '⚠️ AI نتوانست JSON معتبر تولید کند. پرامپت minimal است — '
            + 'لطفاً پرامپت را ویرایش کنید یا با مدل دیگری دوباره تلاش کنید.'
          );
        } else {
          showSuccess('پرامپت تولید شد - بررسی و تأیید کنید');
        }
      } else {
        const err = await res.json().catch(() => ({}));
        // 🆕 (Stage 8) — detect "blocked_no_vision_model" → modal
        // backend در /uploads/{id}/extract این status را برمی‌گرداند،
        // اما idea_to_prompt هنگام extraction به ExtractionError می‌رسد که
        // در detail پیامش `هیچ مدل بصری enabled` دارد.
        const detail = err.detail;
        const msg = typeof detail === 'string' ? detail : (detail?.message || detail?.error || '');
        if (typeof detail === 'object' && detail?.error === 'blocked_no_vision_model') {
          setModelBlockModal({
            candidates: detail.candidates || [],
            mime_type: detail.mime_type,
            session_id: detail.session_id,
          });
        } else if (typeof msg === 'string' && msg.includes('هیچ مدل بصری enabled')) {
          // fallback parsing — اگر extraction از طریق idea_to_prompt صدا زده شد
          setModelBlockModal({ candidates: [] });
          showError(msg);
        } else {
          showError(msg || 'خطا در تولید پرامپت');
        }
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      // 🛡 (audit fix) — تضمین پاک‌سازی pollInterval در همه paths
      if (pollInterval) {
        try { clearInterval(pollInterval); } catch {}
        pollInterval = null;
      }
      setGenerating(false);
      setTimeout(() => setGenPhase(''), 1500);
    }
  };

  // 🆕 (Stage 8 + audit fix) — فعال‌سازی موقت مدل و retry
  const activateModelAndRetry = async (modelId: string) => {
    try {
      const r = await fetch(
        `${API_BASE}/api/oversight/models/${encodeURIComponent(modelId)}/temp-activate?trigger=ui-task-create-${taskDraftId}`,
        { method: 'POST' },
      );
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        showError(e.detail || 'فعال‌سازی موقت ناموفق');
        return;
      }
      const d = await r.json();
      // 🆕 (audit fix) — model_id را track کن تا بعداً (پس از save یا
      // cancel) خودکار revert شود
      setTempActivatedModelId(modelId);
      showSuccess(`✅ ${d.name} موقتاً فعال شد — پس از اتمام کار، خودکار غیرفعال خواهد شد.`);
      setModelBlockModal(null);
      // retry generatePrompt — اکنون extraction باید کار کند
      await generatePrompt();
    } catch (e: any) {
      showError(e?.message || 'خطا');
    }
  };

  // 🆕 (Smart Task Lifecycle) لیست watched های در حال پردازش — برای avoid
  // double-create در فلوی duplicate. وقتی یک watched تسک ساخت یا کاربر صراحتاً
  // force_create کرد، باید از همان نقطه ادامه بدهد، نه از اول.
  const [savePendingIds, setSavePendingIds] = useState<string[]>([]);

  const savePromptAsTask = async (
    forceCreate: boolean = false,
    pendingIds?: string[],
  ) => {
    if (!previewPrompt) return;
    const targetIds = pendingIds ?? (ideaWatchedIds.length ? ideaWatchedIds : ['']);
    let created = 0;
    let duplicate: typeof duplicatePrompt = null;
    const remaining: string[] = [];
    let idx = 0;
    // 🛡 (audit fix) — جمع‌آوری خطاهای دقیق به‌جای silent fail
    const errors: string[] = [];
    for (const wid of targetIds) {
      idx++;
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
            force_create: forceCreate,
            task_steps: previewPrompt.task_steps || [],
            overall_completion_pct: previewPrompt.overall_completion_pct ?? null,
            upload_session_ids: uploadedSessions
              .filter((s) => ['completed', 'extracting', 'extracted'].includes(s.status))
              .sort((a, b) => a.file_order - b.file_order)
              .map((s) => s.session_id),
          }),
        });
        if (res.ok) {
          const result = await res.json();
          if (result.status === 'duplicate_detected' && !forceCreate) {
            duplicate = {
              watched_id: wid || null,
              title: previewPrompt.title,
              prompt: previewPrompt.prompt,
              raw_idea: idea,
              type: ideaType,
              priority: ideaPriority,
              matches: result.similar_matches || [],
            };
            remaining.push(...targetIds.slice(idx - 1));
            break;
          }
          if (result.task) {
            setTasks((prev) => [result.task, ...prev]);
            created++;
          } else {
            // 🛡 backend OK ولی task null — بهتر هشدار بدهیم
            errors.push(
              `پروژه «${w?.repo_full_name || '(بدون پروژه)'}»: status=${result.status || '?'}, task=null`,
            );
          }
        } else {
          // 🛡 HTTP error — body را بخوان و نمایش بده
          const errBody = await res.text().catch(() => '');
          errors.push(
            `پروژه «${w?.repo_full_name || '(بدون پروژه)'}»: HTTP ${res.status} — ${errBody.slice(0, 200)}`,
          );
        }
      } catch (e: any) {
        errors.push(
          `پروژه «${w?.repo_full_name || '(بدون پروژه)'}»: network — ${e?.message || e}`,
        );
      }
    }
    if (duplicate) {
      setSavePendingIds(remaining);
      setDuplicatePrompt(duplicate);
      // 🛡 (audit fix HIGH) — حتی در duplicate path، اگر کاربر مدلی را
      // موقتاً فعال کرده، revert کن. در غیر این صورت مدل تا restart
      // backend stale می‌ماند.
      await revertTempActivatedIfAny();
      return;
    }
    setSavePendingIds([]);
    // 🆕 (audit fix) — پس از اتمام کار (موفق یا با خطا)، اگر کاربر مدلی را
    // موقتاً فعال کرده بود، revert کن.
    await revertTempActivatedIfAny();
    if (created > 0) {
      setIdea('');
      setIdeaDeadline('');
      setPreviewPrompt(null);
      // 🆕 (Stage 3 — File Attachment) — draft id را reset کن تا فایل‌های قبلی
      // در تسک بعدی نباشند. (sessions در سرور persist هستند ولی به task_id
      // مربوطه ربط خورده‌اند — UI آنها را نمایش نمی‌دهد.)
      resetTaskDraft();
      // اگر برخی هم موفق بودند و برخی نه، هر دو پیام
      const msg = errors.length
        ? `${created} تسک ساخته شد ولی ${errors.length} خطا:\n${errors.join('\n')}`
        : `${created} تسک ساخته شد`;
      if (errors.length) showError(msg); else showSuccess(msg);
      reloadStatus();
      setTab('tasks');
    } else {
      // 🛡 نمایش جزئیات خطا (به‌جای پیام مبهم)
      if (errors.length) {
        showError(`هیچ تسکی ساخته نشد:\n${errors.join('\n')}`);
        // log به console برای debug کاربر
        console.error('[savePromptAsTask] errors:', errors);
      } else {
        showError('هیچ تسکی ساخته نشد — هیچ پروژه‌ای انتخاب نشده؟');
      }
    }
  };

  // 🆕 پیش‌نمایش similarity همراه با debounce — تماس با check-similarity
  const checkSimilarityDebounced = (
    watchedId: string | null,
    title: string,
    rawIdea: string,
  ) => {
    if (!watchedId || (!title.trim() && !rawIdea.trim())) {
      setSimilarityHints([]);
      return;
    }
    if ((window as any).__simTimer) clearTimeout((window as any).__simTimer);
    (window as any).__simTimer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/oversight/tasks/check-similarity`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            watched_id: watchedId,
            title,
            raw_idea: rawIdea,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setSimilarityHints(
            (data.matches || []).slice(0, 3).map((m: any) => ({
              task_id: m.task_id,
              title: m.title,
              score: m.score,
            })),
          );
        } else {
          setSimilarityHints([]);
        }
      } catch {
        setSimilarityHints([]);
      }
    }, 500);
  };

  // 🆕 باز کردن merge modal از duplicate dialog
  const openMergeFromDuplicate = async (existingTaskId: string) => {
    if (!duplicatePrompt) return;
    const matchEntry = duplicatePrompt.matches.find((m) => m.task_id === existingTaskId);
    setMergeModal({
      existingTaskId,
      candidate: {
        title: duplicatePrompt.title,
        raw_idea: duplicatePrompt.raw_idea,
        prompt: duplicatePrompt.prompt,
      },
      similarity_score: matchEntry?.score || 0,
      preview: null,
      loading: true,
      choices: {},
    });
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/merge-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          existing_task_id: existingTaskId,
          candidate_title: duplicatePrompt.title,
          candidate_raw_idea: duplicatePrompt.raw_idea,
          candidate_prompt: duplicatePrompt.prompt,
          similarity_score: matchEntry?.score || 0,
          use_ai: false,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        // pre-fill choices با recommendation
        const init: Record<string, any> = {};
        for (const d of data.field_diffs || []) {
          init[d.name] = d.recommendation;
        }
        setMergeModal((prev) =>
          prev ? { ...prev, preview: data, loading: false, choices: init } : prev,
        );
      } else {
        showError('خطا در preview ادغام');
        setMergeModal(null);
      }
    } catch (e: any) {
      showError(e.message);
      setMergeModal(null);
    }
  };

  // 🆕 اعمال نهایی ادغام
  const applyMerge = async () => {
    if (!mergeModal) return;
    // استخراج ai_merged_values از field_diffs برای پاس به backend
    // (تا apply_merge از همان متن AI استفاده کند نه concat ساده)
    const aiMergedValues: Record<string, any> = {};
    for (const d of (mergeModal.preview?.field_diffs || [])) {
      if (d.ai_merged_value !== undefined && d.ai_merged_value !== null) {
        aiMergedValues[d.name] = d.ai_merged_value;
      }
    }
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/merge-apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          existing_task_id: mergeModal.existingTaskId,
          candidate_title: mergeModal.candidate.title,
          candidate_raw_idea: mergeModal.candidate.raw_idea,
          candidate_prompt: mergeModal.candidate.prompt,
          candidate_acceptance_criteria: mergeModal.candidate.acceptance_criteria,
          candidate_target_files: mergeModal.candidate.target_files,
          chosen_fields: mergeModal.choices,
          source: 'manual',
          similarity_score: mergeModal.similarity_score,
          ai_merged_values: aiMergedValues,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        // update task in list
        setTasks((prev) => prev.map((t) => (t.id === data.task.id ? data.task : t)));
        showSuccess('ادغام انجام شد');
        setMergeModal(null);
        setDuplicatePrompt(null);
        // پس از merge این watched، اگر watched های باقی‌مانده وجود دارد، ادامه بده
        // (در حالت تک watched_id، rest خالی است → flow بسته می‌شود)
        const rest = savePendingIds.slice(1);
        if (rest.length > 0) {
          setSavePendingIds(rest);
          // فلوی duplicate برای watched های بعدی همچنان فعال است
          await savePromptAsTask(false, rest);
        } else {
          setSavePendingIds([]);
          setPreviewPrompt(null);
          setIdea('');
          setTab('tasks');
        }
        reloadStatus();
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در اعمال ادغام');
      }
    } catch (e: any) {
      showError(e.message);
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
    if (selectedModelIds.length === 0) {
      showError(
        '⚠️ هیچ مدلی انتخاب نشده. ابتدا از بخش «انتخاب مدل» در بالای صفحه '
        + 'حداقل یک مدل AI را انتخاب کنید.'
      );
      return;
    }
    setCodexLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/oversight/codex/${codexWatchedId}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModelIds[0], only_changed: false }),
      });
      if (res.ok) {
        const data = await res.json();
        const modelInfo = data.model_used ? ` (با مدل ${data.model_used})` : '';
        const depthInfo = data.used_deep_structure ? '' : ' — توصیه: ابتدا Deep Scan اجرا شود';
        if ((data.files_documented || 0) > 0) {
          showSuccess(
            `✅ ${data.newly_added || 0} فایل جدید مستند شد` + modelInfo
            + ` — مجموع: ${data.files_documented} فایل${depthInfo}`
          );
        } else {
          showError(
            `هیچ فایلی مستند نشد${modelInfo}. لطفاً ابتدا یک Deep Scan کامل اجرا کنید.`
          );
        }
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

  // 🆕 (P4) regenerate prompt
  const openRegenModal = (t: Task) => {
    setRegenTask(t);
    setRegenRawIdea(t.raw_idea || '');
    setRegenError('');
  };
  const closeRegenModal = () => {
    setRegenTask(null);
    setRegenRawIdea('');
    setRegenError('');
    setRegenLoading(false);
  };
  const submitRegenerate = async () => {
    if (!regenTask) return;
    setRegenLoading(true);
    setRegenError('');
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${regenTask.id}/regenerate-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_idea: regenRawIdea.trim() || null,
          model_ids: selectedModelIds.length ? selectedModelIds : null,
          model_id: selectedModelIds[0] || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRegenError(data?.detail || `HTTP ${res.status}`);
        return;
      }
      setTasks(prev => prev.map(x => (x.id === regenTask.id ? data.task : x)));
      closeRegenModal();
    } catch (e: any) {
      setRegenError(e?.message || 'failed');
    } finally {
      setRegenLoading(false);
    }
  };
  const rollbackPrompt = async (taskId: string, idx: number) => {
    if (!confirm('این نسخهٔ پرامپت را برگردانم؟ (نسخهٔ فعلی به history منتقل می‌شود)')) return;
    try {
      const res = await fetch(`${API_BASE}/api/oversight/tasks/${taskId}/rollback-prompt/${idx}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setTasks(prev => prev.map(x => (x.id === taskId ? data.task : x)));
        setHistoryTask(data.task);
      }
    } catch (e) { console.error(e); }
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
      // 🆕 (P3) archived filter
      if (taskFilterArchived === 'active' && t.archived) return false;
      if (taskFilterArchived === 'archived' && !t.archived) return false;
      return true;
    });
  }, [tasks, taskFilterStatus, taskFilterWatched, taskFilterArchived]);

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
              { id: 'tasks', label: `تسک‌ها (${tasks.length})`, icon: '📋', count: tasks.length },
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
              watched.map((w) => {
                const wActiveTasks = tasks.filter(t => t.watched_id === w.id && !t.archived);
                const wArchivedTasks = tasks.filter(t => t.watched_id === w.id && t.archived);
                const wReportCount = reports.filter(r => r.watched_id === w.id).length;
                return (
                <WatchedCard
                  key={w.id}
                  w={w}
                  taskCount={wActiveTasks.length}
                  archivedCount={wArchivedTasks.length}
                  reportCount={wReportCount}
                  availableModels={models}
                  isScanning={deepScanWatchedId === w.id}
                  scanProgress={deepScanWatchedId === w.id ? deepScanProgress : null}
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
                    setTaskFilterArchived('active');
                    setTab('tasks');
                  }}
                  onViewArchive={() => {
                    setTaskFilterWatched(w.id);
                    setTaskFilterStatus('all');
                    setTaskFilterArchived('archived');
                    setTab('tasks');
                  }}
                  onViewReports={() => {
                    setReportWatchedFilter(w.id);
                    setReportStatusFilter('all');
                    setTab('reports');
                  }}
                  onOpenCodex={() => openCodex(w.id)}
                />
                );
              })
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
              <div>
                <label
                  className="block text-xs mb-1 dark:text-gray-300"
                  title="auto: heuristic. always: همیشه AI ایده را به مراحل تقسیم می‌کند (کیفیت بهتر، ~10s overhead). never: تک‌مرحله."
                >
                  حالت تبدیل
                </label>
                <select
                  value={multiPassMode}
                  onChange={(e) => setMultiPassMode(e.target.value as 'auto' | 'always' | 'never')}
                  className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600"
                >
                  <option value="auto">🤖 Auto (هوشمند — پیش‌فرض)</option>
                  <option value="always">🎯 همیشه تقسیم مرحله‌ای</option>
                  <option value="never">⚡ تک‌مرحله سریع</option>
                </select>
              </div>
            </div>

            {/* 🆕 (Stage 3 — File Attachment) — drag-drop چند فایل با chunked upload */}
            <TaskFilePicker
              taskDraftId={taskDraftId}
              apiBase={API_BASE}
              onSessionsChange={setUploadedSessions}
              disabled={generating}
            />

            <textarea
              value={idea}
              onChange={(e) => {
                const v = e.target.value;
                setIdea(v);
                // 🆕 (Smart Task Lifecycle) debounce check-similarity همزمان با تایپ
                // تا قبل از زدن «تبدیل به پرامپت»، تسک‌های مشابه نمایش داده شود.
                checkSimilarityDebounced(
                  ideaWatchedIds[0] || null,
                  v.split('\n')[0].slice(0, 120),  // اولین خط = title فرضی
                  v,
                );
              }}
              rows={6}
              placeholder="مثلاً: «authentication این پروژه ضعیفه. JWT اضافه کن، rate limit بذار، endpoint های login/register رو امن کن، اگه کاربر سه بار اشتباه پسورد بزنه قفل بشه...»"
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 mb-3"
            />
            {/* 🆕 نمایش similarity hints قبل از تولید پرامپت — تا کاربر زودتر بفهمد */}
            {similarityHints.length > 0 && !previewPrompt && (
              <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded">
                <div className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">
                  ⚠️ {similarityHints.length} تسک مشابه در این پروژه پیدا شد:
                </div>
                <ul className="text-xs text-amber-700 dark:text-amber-300 space-y-1">
                  {similarityHints.map((m) => (
                    <li key={m.task_id}>
                      • «{m.title.slice(0, 70)}» — شباهت {Math.round(m.score * 100)}٪
                    </li>
                  ))}
                </ul>
                <div className="text-[11px] text-amber-600 dark:text-amber-400 mt-1">
                  اگر ادامه دهید، پس از تولید پرامپت گزینهٔ «ادغام / جداگانه» داده می‌شود.
                </div>
              </div>
            )}

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
                  onChange={(e) => {
                    setPreviewPrompt({ ...previewPrompt, title: e.target.value });
                    checkSimilarityDebounced(
                      ideaWatchedIds[0] || null,
                      e.target.value,
                      idea,
                    );
                  }}
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
                {/* 🆕 (Multi-pass Checklist) — اگر multi-pass مراحل تولید کرد، در preview نشان بده */}
                {Array.isArray(previewPrompt.task_steps) && previewPrompt.task_steps.length > 0 && (
                  <div className="mt-3 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded">
                    <div className="text-sm font-semibold text-indigo-800 dark:text-indigo-200 mb-1">
                      📋 چک‌لیست مراحل ({previewPrompt.task_steps.length} مرحله) — پس از ذخیره، verifier هر مرحله را به‌صورت خودکار تیک می‌زند
                    </div>
                    <ul className="text-xs text-indigo-700 dark:text-indigo-300 space-y-1 mt-1">
                      {previewPrompt.task_steps.map((s: any) => (
                        <li key={s.id} className="flex gap-1.5 items-start">
                          <span className="mt-0.5">⬜</span>
                          <span><b>مرحله {s.id}: {s.title}</b>{s.scope ? ` — ${String(s.scope).slice(0, 200)}` : ''}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {similarityHints.length > 0 && (
                  <div className="mt-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded">
                    <div className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">
                      ⚠️ {similarityHints.length} تسک مشابه پیدا شد:
                    </div>
                    <ul className="text-xs text-amber-700 dark:text-amber-300 space-y-1">
                      {similarityHints.map((m) => (
                        <li key={m.task_id}>
                          • «{m.title.slice(0, 60)}» — شباهت {Math.round(m.score * 100)}٪
                        </li>
                      ))}
                    </ul>
                    <div className="text-[11px] text-amber-600 dark:text-amber-400 mt-1">
                      اگر ذخیره کنید، سیستم گزینهٔ «ادغام / جداگانه» را پیشنهاد می‌دهد.
                    </div>
                  </div>
                )}
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => savePromptAsTask(false)}
                    className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    ✓ ذخیره به‌عنوان تسک
                    {ideaWatchedIds.length > 1 ? ` (×${ideaWatchedIds.length})` : ''}
                  </button>
                  <button
                    onClick={async () => {
                      setPreviewPrompt(null);
                      // 🆕 (audit fix) — اگر کاربر cancel کرد، مدل temp-activated را revert کن
                      await revertTempActivatedIfAny();
                    }}
                    className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded-lg hover:bg-gray-400"
                  >
                    لغو
                  </button>
                </div>
              </div>
            )}

            {/* 🆕 (Stage 8 — File Attachment) — modal فعال‌سازی موقت مدل بصری */}
            {modelBlockModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-xl p-5 shadow-2xl">
                  <h3 className="font-bold text-lg mb-2 text-orange-700 dark:text-orange-300">
                    🔓 مدل بصری فعال نیست
                  </h3>
                  <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                    فایل پیوست کردی، اما هیچ مدل multimodal فعال (enabled) برای استخراج
                    {modelBlockModal.mime_type && (
                      <> <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">{modelBlockModal.mime_type}</code></>
                    )}
                    {' '}نیست. می‌توانم یکی را موقتاً فعال کنم، کار را انجام دهم، و دوباره غیرفعال کنم.
                    در هر دو نقطه به تلگرام اطلاع می‌رسد.
                  </p>
                  {modelBlockModal.candidates && modelBlockModal.candidates.length > 0 ? (
                    <div className="space-y-2 my-3">
                      {modelBlockModal.candidates.map((c, i) => (
                        <button
                          key={c.id}
                          onClick={() => activateModelAndRetry(c.id)}
                          className={`w-full text-left p-2 border rounded transition-colors ${
                            i === 0
                              ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 hover:bg-emerald-100'
                              : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold dark:text-white">
                              {i === 0 ? '⭐ ' : ''}
                              {c.name}
                            </span>
                            <span className="text-[10px] text-gray-500 ml-auto">
                              {c.provider} · priority {c.priority}
                            </span>
                          </div>
                          <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                            <code>{c.id}</code>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-amber-700 dark:text-amber-300 my-3">
                      ⚠️ هیچ مدل multimodal در registry پیدا نشد. لطفاً از <a href="/models" className="underline">صفحهٔ مدل‌ها</a> یک مدل وارد کنید.
                    </p>
                  )}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => setModelBlockModal(null)}
                      className="flex-1 py-2 bg-gray-200 dark:bg-gray-600 dark:text-white rounded hover:bg-gray-300"
                    >
                      انصراف
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 🆕 (Smart Task Lifecycle) Duplicate Detected Dialog */}
            {duplicatePrompt && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-2xl p-5 shadow-2xl">
                  <h3 className="font-bold text-lg mb-2 text-amber-700 dark:text-amber-300">
                    🔍 تسک‌های مشابه پیدا شد
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                    عنوان جدید: <span className="font-medium">«{duplicatePrompt.title.slice(0, 80)}»</span>
                  </p>
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {duplicatePrompt.matches.map((m) => (
                      <div
                        key={m.task_id}
                        className="border border-gray-200 dark:border-gray-700 rounded p-3 flex items-center justify-between gap-2"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="font-medium dark:text-white truncate">{m.title}</div>
                          <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                            شباهت کلی: {Math.round(m.score * 100)}٪ • title: {Math.round(m.title_jaccard * 100)}٪ • idea: {Math.round(m.idea_overlap * 100)}٪
                          </div>
                          {m.reasons.length > 0 && (
                            <div className="text-[11px] text-gray-400 mt-0.5" dir="ltr">
                              {m.reasons.join(' · ')}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => openMergeFromDuplicate(m.task_id)}
                          className="px-3 py-1.5 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 shrink-0"
                        >
                          🔀 ادغام
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => {
                        const pending = savePendingIds.length ? savePendingIds : undefined;
                        setDuplicatePrompt(null);
                        // فقط برای watched های باقی‌مانده force_create — قبلی‌های
                        // موفق دوباره ساخته نمی‌شوند.
                        savePromptAsTask(true, pending);
                      }}
                      className="flex-1 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 text-sm"
                    >
                      ➕ ایجاد جداگانه با وجود تشابه
                      {savePendingIds.length > 1 ? ` (${savePendingIds.length} باقی‌مانده)` : ''}
                    </button>
                    <button
                      onClick={() => {
                        setDuplicatePrompt(null);
                        setSavePendingIds([]);
                      }}
                      className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded hover:bg-gray-400 text-sm"
                    >
                      ❌ انصراف
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 🆕 (Smart Task Lifecycle) Merge Preview Modal */}
            {mergeModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-4xl p-5 shadow-2xl max-h-[90vh] overflow-y-auto">
                  <h3 className="font-bold text-lg mb-1 dark:text-white">
                    🔀 پیش‌نمایش ادغام تسک
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                    شباهت: {Math.round(mergeModal.similarity_score * 100)}٪
                  </p>
                  {mergeModal.loading ? (
                    <div className="text-center py-8 text-gray-500">⏳ در حال آماده‌سازی پیش‌نمایش...</div>
                  ) : !mergeModal.preview ? (
                    <div className="text-center py-8 text-gray-500">پیش‌نمایش در دسترس نیست</div>
                  ) : (
                    <>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-3 p-2 bg-gray-50 dark:bg-gray-900 rounded">
                        {mergeModal.preview.summary}
                      </p>
                      {(mergeModal.preview.field_diffs || []).length === 0 ? (
                        <p className="text-sm text-gray-500 text-center py-4">
                          هیچ تغییر واقعی پیشنهاد نشد — فقط شمارنده‌ها افزایش می‌یابد.
                        </p>
                      ) : (
                        <div className="space-y-3">
                          {(mergeModal.preview.field_diffs || []).map((d: any) => (
                            <div key={d.name} className="border border-gray-200 dark:border-gray-700 rounded p-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-semibold text-sm dark:text-white">
                                  📌 {d.name}
                                </span>
                                <select
                                  value={mergeModal.choices[d.name] || d.recommendation}
                                  onChange={(e) =>
                                    setMergeModal((prev) =>
                                      prev
                                        ? {
                                            ...prev,
                                            choices: { ...prev.choices, [d.name]: e.target.value as any },
                                          }
                                        : prev,
                                    )
                                  }
                                  className="text-xs px-2 py-1 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
                                >
                                  <option value="existing">نگه داشتن موجود</option>
                                  <option value="candidate">جایگزینی با کاندید</option>
                                  {d.ai_merged_value && <option value="ai_merged">ادغام پیشنهاد AI</option>}
                                </select>
                              </div>
                              {d.notes && (
                                <div className="text-[11px] text-gray-500 dark:text-gray-400 mb-2">{d.notes}</div>
                              )}
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                                <div className="border border-gray-200 dark:border-gray-700 rounded p-2 bg-gray-50 dark:bg-gray-900/40">
                                  <div className="font-medium mb-1 text-gray-500">موجود</div>
                                  <pre className="whitespace-pre-wrap break-words text-[11px] dark:text-gray-200">
                                    {typeof d.existing_value === 'string'
                                      ? d.existing_value.slice(0, 400)
                                      : JSON.stringify(d.existing_value, null, 2).slice(0, 400)}
                                  </pre>
                                </div>
                                <div className="border border-blue-200 dark:border-blue-800 rounded p-2 bg-blue-50/40 dark:bg-blue-900/20">
                                  <div className="font-medium mb-1 text-blue-600 dark:text-blue-300">کاندید</div>
                                  <pre className="whitespace-pre-wrap break-words text-[11px] dark:text-gray-200">
                                    {typeof d.candidate_value === 'string'
                                      ? d.candidate_value.slice(0, 400)
                                      : JSON.stringify(d.candidate_value, null, 2).slice(0, 400)}
                                  </pre>
                                </div>
                                <div className="border border-emerald-200 dark:border-emerald-800 rounded p-2 bg-emerald-50/40 dark:bg-emerald-900/20">
                                  <div className="font-medium mb-1 text-emerald-600 dark:text-emerald-300">پیشنهاد ادغام</div>
                                  <pre className="whitespace-pre-wrap break-words text-[11px] dark:text-gray-200">
                                    {d.ai_merged_value
                                      ? typeof d.ai_merged_value === 'string'
                                        ? d.ai_merged_value.slice(0, 400)
                                        : JSON.stringify(d.ai_merged_value, null, 2).slice(0, 400)
                                      : '—'}
                                  </pre>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={applyMerge}
                      disabled={mergeModal.loading || !mergeModal.preview}
                      className="flex-1 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600 disabled:opacity-50 text-sm"
                    >
                      ✅ اعمال ادغام
                    </button>
                    <button
                      onClick={() => setMergeModal(null)}
                      className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded hover:bg-gray-400 text-sm"
                    >
                      ❌ لغو
                    </button>
                  </div>
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
            taskFilterArchived={taskFilterArchived}
            setTaskFilterArchived={setTaskFilterArchived}
            onOpenRegen={openRegenModal}
            onOpenHistory={(t) => setHistoryTask(t)}
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

        {/* 🆕 (P4) مودال بازتولید پرامپت */}
        {regenTask && (
          <Modal onClose={closeRegenModal} title="🔄 بازتولید پرامپت">
            <div className="space-y-3">
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-3 text-xs text-gray-700 dark:text-gray-200">
                نسخهٔ فعلی پرامپت به <b>تاریخچه</b> منتقل می‌شود (max 10 نسخه قابل rollback).
                AI با ایدهٔ خام زیر پرامپت جدید با کیفیت ارتقایافته می‌سازد —
                هیچ تسک جدیدی ساخته نمی‌شود.
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-gray-200">ایدهٔ خام (raw_idea):</label>
                <textarea
                  value={regenRawIdea}
                  onChange={e => setRegenRawIdea(e.target.value)}
                  rows={6}
                  placeholder="ایده/مشکل را به زبان طبیعی توضیح دهید..."
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 text-sm"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  اگر خالی بگذارید، از raw_idea فعلی تسک استفاده می‌شود.
                </p>
              </div>
              {selectedModelIds.length === 0 && (
                <div className="text-xs text-amber-600 dark:text-amber-400">
                  ⚠️ هیچ مدلی انتخاب نشده — backend default را استفاده می‌کند.
                </div>
              )}
              {regenError && (
                <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                  ❌ {regenError}
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button onClick={closeRegenModal} className="px-4 py-2 bg-gray-300 dark:bg-gray-600 dark:text-white rounded-lg hover:bg-gray-400">
                  لغو
                </button>
                <button
                  onClick={submitRegenerate}
                  disabled={regenLoading}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {regenLoading ? '⏳ در حال بازتولید (15-30 ثانیه)...' : '🔄 بازتولید'}
                </button>
              </div>
            </div>
          </Modal>
        )}

        {/* 🆕 (P4) مودال history پرامپت */}
        {historyTask && (
          <Modal onClose={() => setHistoryTask(null)} title={`📜 تاریخچهٔ پرامپت — ${historyTask.title.slice(0, 50)}`}>
            <div className="space-y-3 text-sm">
              {(historyTask.prompt_history || []).length === 0 ? (
                <div className="text-gray-500 dark:text-gray-400 text-center py-8">
                  هنوز هیچ نسخهٔ قبلی ذخیره نشده. با اولین «بازتولید پرامپت» history ساخته می‌شود.
                </div>
              ) : (
                <>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {historyTask.prompt_history!.length} نسخهٔ قبلی — newest first
                  </div>
                  {historyTask.prompt_history!.map((h, i) => (
                    <div key={i} className="border dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-gray-900/30">
                      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                        <div className="text-xs flex items-center gap-2 flex-wrap">
                          <span className="font-semibold dark:text-gray-200">نسخه #{i + 1}</span>
                          {/* 🆕 نمایش source که این نسخه چطور ساخته شده */}
                          {h.source ? (
                            h.source.startsWith('followup_round_') ? (
                              <span className="bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300 px-1.5 py-0.5 rounded text-[10px]">
                                🔁 followup (دور {h.source.replace('followup_round_', '')})
                              </span>
                            ) : h.source === 'regenerate' ? (
                              <span className="bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300 px-1.5 py-0.5 rounded text-[10px]">
                                🔄 بازتولید دستی
                              </span>
                            ) : (
                              <span className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-[10px]">
                                {h.source}
                              </span>
                            )
                          ) : (
                            <span className="bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-1.5 py-0.5 rounded text-[10px]">
                              📝 پرامپت اولیه
                            </span>
                          )}
                          {h.generated_at && (
                            <span className="text-gray-500 dark:text-gray-400">
                              {fmtDate(h.generated_at)}
                            </span>
                          )}
                          {h.model_id && (
                            <span className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-[10px] font-mono">
                              {h.model_id}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => rollbackPrompt(historyTask.id, i)}
                          className="px-2 py-1 bg-amber-500 text-white rounded text-xs hover:bg-amber-600"
                        >
                          ↩️ بازگردانی این نسخه
                        </button>
                      </div>
                      {h.raw_idea && (
                        <details className="mb-1">
                          <summary className="cursor-pointer text-xs text-gray-600 dark:text-gray-300">💭 raw_idea</summary>
                          <div className="mt-1 p-2 bg-white dark:bg-black/30 rounded text-xs whitespace-pre-wrap">{h.raw_idea}</div>
                        </details>
                      )}
                      <details>
                        <summary className="cursor-pointer text-xs text-gray-600 dark:text-gray-300">📋 prompt</summary>
                        <pre className="mt-1 p-2 bg-white dark:bg-black/30 rounded text-[10px] whitespace-pre-wrap max-h-48 overflow-auto font-mono">{h.prompt.slice(0, 3000)}{h.prompt.length > 3000 ? '\n... [truncated]' : ''}</pre>
                      </details>
                    </div>
                  ))}
                </>
              )}
            </div>
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
              selectedModel={selectedModelIds[0]}
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
  taskCount,
  archivedCount,
  reportCount,
  availableModels,
  isScanning,
  scanProgress,
  onChange,
  onRemove,
  onScan,
  onDeepScan,
  onRunNow,
  onWriteIdea,
  onViewTasks,
  onViewArchive,
  onViewReports,
  onOpenCodex,
}: {
  w: Watched;
  taskCount: number;
  archivedCount: number;
  reportCount: number;
  availableModels: ModelInfo[];
  isScanning?: boolean;
  scanProgress?: any;
  onChange: (updates: Partial<Watched>) => void;
  onRemove: () => void;
  onScan: () => void;
  onDeepScan: () => void;
  onRunNow: () => void;
  onWriteIdea: () => void;
  onViewTasks: () => void;
  onViewArchive: () => void;
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
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow p-5 ${
      isScanning ? 'ring-2 ring-orange-400 dark:ring-orange-500 animate-pulse' : ''
    }`}>
      {/* 🆕 (P4) banner در حین scan */}
      {isScanning && scanProgress && (
        <div className="mb-3 -mx-5 -mt-5 px-5 py-2 bg-orange-100 dark:bg-orange-900/30 border-b border-orange-300 dark:border-orange-800 rounded-t-xl text-xs flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 text-orange-800 dark:text-orange-200">
            <span className="animate-spin">🔬</span>
            <span className="font-semibold">scan در حال اجرا</span>
            {scanProgress.phase && (
              <span className="text-[10px]">
                · {PASS_LABELS[scanProgress.phase] || scanProgress.phase}
              </span>
            )}
            {scanProgress.passes_done != null && scanProgress.passes_total != null && (
              <span className="text-[10px]">
                · pass {scanProgress.passes_done}/{scanProgress.passes_total}
              </span>
            )}
          </div>
          {scanProgress.findings_count != null && (
            <span className="text-[10px] text-orange-700 dark:text-orange-300">
              🔎 {scanProgress.findings_count} finding تا کنون
            </span>
          )}
        </div>
      )}
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
            {/* 🆕 (Creator) badge منبع auto-add */}
            {w.auto_added_source && (
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  w.auto_added_source.startsWith('creator')
                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                    : w.auto_added_source === 'github_import'
                    ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
                }`}
                title={`source: ${w.auto_added_source}`}
              >
                {w.auto_added_source === 'creator_via_telegram'
                  ? '🤖🚀 از ربات'
                  : w.auto_added_source === 'creator_via_web'
                  ? '🚀 از Creator'
                  : w.auto_added_source === 'github_import'
                  ? '📥 از Import'
                  : '📌 auto'}
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
            {w.auto_regenerate_old_prompts && (
              <span
                className="text-xs px-1.5 py-0.5 rounded bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300"
                title={`بازتولید خودکار پرامپت‌های ناقص (آستانهٔ کیفیت ${w.prompt_quality_threshold ?? 60}٪)`}
              >
                🔄 auto-regen
              </span>
            )}
            {w.dedup_in_manual_create !== false && (
              <span
                className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                title={`بررسی مشابهت در ایجاد دستی (آستانه ${Math.round((w.dedup_score_threshold ?? 0.65) * 100)}٪)`}
              >
                🔍 dedup
              </span>
            )}
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
              عمق scan <span className="text-blue-400" title="quick: 3 pass سبک، standard: 6 pass، deep: تمام 12 pass، thorough: تمام 12 pass + per-file health scoring">ⓘ</span>
            </span>
            <select
              value={w.scan_depth || 'deep'}
              onChange={(e) => onChange({ scan_depth: e.target.value as any })}
              className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600"
            >
              <option value="quick">⚡ quick (3 pass — سریع: frontend + backend + security)</option>
              <option value="standard">⚖ standard (6 pass — متعادل + logical_alignment)</option>
              <option value="deep">🔍 deep (12 pass — کامل، پیش‌فرض)</option>
              <option value="thorough">🔬 thorough (12 pass + per-file health scoring + roadmap)</option>
            </select>
          </label>
          <div className="text-xs text-gray-500 dark:text-gray-400 self-end">
            وزن‌های معیار را تنظیم کنید تا scoring per-file به اولویت‌های شما حساس باشد:
          </div>
          {(['security', 'quality', 'tests', 'completeness', 'logical_alignment', 'functional_correctness'] as const).map(key => {
            const weights = w.scan_criteria_weights || {};
            const defaultValue = (
              key === 'security' ? 1.5 :
              key === 'tests' ? 1.2 :
              key === 'functional_correctness' ? 1.5 :
              1.0
            );
            const value = weights[key] ?? defaultValue;
            const labels: Record<string, string> = {
              security: '🔒 امنیت',
              quality: '🛠 کیفیت',
              tests: '🧪 تست',
              completeness: '✅ کامل بودن',
              logical_alignment: '🧩 منطق/هم‌راستایی',
              functional_correctness: '⚙️ صحت رفتاری',
            };
            const tooltips: Record<string, string> = {
              security: 'وزن یافته‌های امنیتی (XSS، SQL injection، secret leakage، ...) در health score هر فایل',
              quality: 'وزن کد کیفیت پایین، dead code، duplicate logic',
              tests: 'وزن فایل‌های بدون test یا coverage پایین',
              completeness: 'وزن قابلیت‌های ناقص نسبت به user_goal',
              logical_alignment: 'وزن orphan endpointها، duplicate logic، contract mismatch بین frontend و backend',
              functional_correctness: 'وزن edge case‌های unhandled، exception swallowed، race conditions، failure modes',
            };
            return (
              <label key={key} className="block">
                <span className="block text-gray-600 dark:text-gray-300 mb-1 flex items-center gap-1">
                  {labels[key]}: <strong>{value.toFixed(1)}×</strong>
                  <span className="cursor-help text-blue-400" title={tooltips[key]}>ⓘ</span>
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

        {/* 🆕 (P1) Multi-select مدل برای auto-scan */}
        <div className="mt-4 pt-3 border-t border-cyan-200 dark:border-cyan-800/40">
          <label className="block">
            <span className="block text-gray-600 dark:text-gray-300 mb-1 flex items-center gap-1">
              🤖 مدل‌های AI برای auto-scan
              <span
                className="cursor-help text-blue-400"
                title="Ctrl/Cmd-click برای انتخاب چندتایی. اگر چندتایی، هر pass با همهٔ مدل‌ها اجرا می‌شود و findings ادغام می‌شوند (consensus). خالی = مدل پیش‌فرض backend"
              >ⓘ</span>
            </span>
            <select
              multiple
              value={w.selected_models || []}
              onChange={(e) => {
                const opts = Array.from(e.target.selectedOptions).map(o => o.value);
                onChange({ selected_models: opts });
              }}
              className="w-full p-1.5 border rounded text-sm dark:bg-gray-700 dark:text-white dark:border-gray-600 h-24"
            >
              {availableModels.map(m => (
                <option key={m.id} value={m.id}>
                  {m.name}{m.provider ? ` (${m.provider})` : ''}
                </option>
              ))}
            </select>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {(w.selected_models || []).length === 0 && '⚠️ هیچ مدلی انتخاب نشده — backend default استفاده می‌شود'}
              {(w.selected_models || []).length === 1 && `✓ یک‌مدل (${w.selected_models![0]})`}
              {(w.selected_models || []).length > 1 && `🤝 consensus mode: ${w.selected_models!.length} مدل (هر pass × ${w.selected_models!.length} = هزینه/زمان بیشتر)`}
            </div>
          </label>
        </div>
      </details>

      {/* 🆕 (P4) accordion آخرین scan — فقط اگر metadata موجود باشد */}
      {w.last_scan_metadata && (
        <details className="mt-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/40 rounded-lg p-3 text-xs">
          <summary className="cursor-pointer font-medium text-emerald-800 dark:text-emerald-200 flex items-center justify-between">
            <span>📊 آخرین scan</span>
            <span className="text-[10px] text-gray-500 dark:text-gray-400">
              {w.last_scan_metadata.completed_at && new Date(w.last_scan_metadata.completed_at).toLocaleString('fa-IR')}
            </span>
          </summary>
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div className="bg-white dark:bg-gray-900/40 p-2 rounded">
              <div className="text-gray-500 dark:text-gray-400 text-[10px]">🤖 مدل</div>
              <div className="font-mono text-gray-800 dark:text-gray-100 truncate">
                {w.last_scan_metadata.model_used || '—'}
              </div>
              {(w.last_scan_metadata.models_used_list || []).length > 1 && (
                <div className="text-[10px] text-gray-500">
                  +{w.last_scan_metadata.models_used_list!.length - 1} consensus
                </div>
              )}
            </div>
            <div className="bg-white dark:bg-gray-900/40 p-2 rounded">
              <div className="text-gray-500 dark:text-gray-400 text-[10px]">🔍 depth</div>
              <div className="font-semibold text-gray-800 dark:text-gray-100">
                {w.last_scan_metadata.scan_depth || '—'}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900/40 p-2 rounded">
              <div className="text-gray-500 dark:text-gray-400 text-[10px]">📊 passes</div>
              <div className="font-semibold text-gray-800 dark:text-gray-100">
                {w.last_scan_metadata.passes_run ?? '—'}/{w.last_scan_metadata.passes_total ?? '—'}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900/40 p-2 rounded">
              <div className="text-gray-500 dark:text-gray-400 text-[10px]">📄 files</div>
              <div className="font-semibold text-gray-800 dark:text-gray-100">
                {w.last_scan_metadata.files_analyzed_count ?? '—'}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900/40 p-2 rounded">
              <div className="text-gray-500 dark:text-gray-400 text-[10px]">🔎 findings</div>
              <div className="font-semibold text-gray-800 dark:text-gray-100">
                {w.last_scan_metadata.findings_count ?? '—'}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-900/40 p-2 rounded">
              <div className="text-gray-500 dark:text-gray-400 text-[10px]">📝 tasks جدید</div>
              <div className="font-semibold text-gray-800 dark:text-gray-100">
                {w.last_scan_metadata.tasks_created ?? '—'}
              </div>
            </div>
            {(w.last_scan_metadata.duplicates_skipped ?? 0) > 0 && (
              <div className="bg-amber-50 dark:bg-amber-900/30 p-2 rounded">
                <div className="text-amber-700 dark:text-amber-300 text-[10px]">🔁 تکراری</div>
                <div className="font-semibold text-amber-700 dark:text-amber-300">
                  {w.last_scan_metadata.duplicates_skipped}
                </div>
              </div>
            )}
            {(w.last_scan_metadata.critical_count ?? 0) > 0 && (
              <div className="bg-red-50 dark:bg-red-900/30 p-2 rounded">
                <div className="text-red-700 dark:text-red-300 text-[10px]">🚨 critical</div>
                <div className="font-semibold text-red-700 dark:text-red-300">
                  {w.last_scan_metadata.critical_count}
                </div>
              </div>
            )}
          </div>
          {w.last_scan_metadata.pass_breakdown && Object.keys(w.last_scan_metadata.pass_breakdown).length > 0 && (
            <div className="mt-3">
              <div className="text-gray-500 dark:text-gray-400 text-[10px] mb-1">📊 per-pass breakdown:</div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(w.last_scan_metadata.pass_breakdown).map(([p, n]) => (
                  <span
                    key={p}
                    className="bg-white dark:bg-gray-900/40 px-1.5 py-0.5 rounded text-[10px] font-mono border border-gray-200 dark:border-gray-700"
                    title={`${p}: ${n} finding`}
                  >
                    {p}: <strong>{n}</strong>
                  </span>
                ))}
              </div>
            </div>
          )}
          {w.next_scan_at && (
            <div className="mt-3 text-[10px] text-gray-500 dark:text-gray-400">
              🕐 next scan: {new Date(w.next_scan_at).toLocaleString('fa-IR')}
            </div>
          )}
        </details>
      )}

      {/* بازه verify — همیشه قابل تنظیم چون scheduler verify را مستقل از autonomy اجرا می‌کند */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
        <label className="text-xs">
          <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            بازه verify (ساعت)
            <span
              title="هر چند ساعت، تسک‌های اعمال‌شده (یا نشده) دوباره بررسی می‌شوند تا تأیید نهایی — مستقل از مسیر اجرا و autonomy_level"
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

        {/* مسیر اجرا و verify_only فقط وقتی autonomy=auto معنی دارند —
            در manual/assist، scheduler هیچ‌گاه auto-apply نمی‌کند پس این کنترل‌ها redundant هستند */}
        {w.autonomy_level === 'auto' ? (
          <>
            <label className="text-xs">
              <span className="block text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
                مسیر اجرا
                <span
                  title="فقط در autonomy=auto معنی دارد. auto_via_projects_page: از طریق صفحهٔ /projects اعمال شود. auto_via_pr: AI خودش PR می‌سازد. manual: scheduler نمی‌نویسد، فقط verify."
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
            <label className="text-xs flex items-center gap-2 mt-5">
              <input
                type="checkbox"
                checked={!!w.verify_only_mode}
                onChange={(e) => onChange({ verify_only_mode: e.target.checked })}
                className="w-4 h-4"
              />
              <span
                className="dark:text-gray-200"
                title="کلید فوریت: اگر فعال باشد، scheduler در حالت auto هم apply نمی‌کند — فقط verify"
              >
                فقط verify (هرگز apply نکن)
              </span>
            </label>
          </>
        ) : (
          <div className="text-xs text-gray-500 dark:text-gray-400 sm:col-span-2 self-center px-2">
            ℹ️ «مسیر اجرا» و «فقط verify» فقط در حالت autonomy=auto معنی دارند.
            {w.autonomy_level === 'manual' && ' در حالت manual، تسک‌ها فقط با کلیک شما اجرا می‌شوند.'}
          </div>
        )}
      </div>

      {/* 🆕 (Smart Task Lifecycle) چرخهٔ تسک — dedup + auto-regenerate */}
      <div className="mb-3 p-3 bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-lg">
        <div className="text-sm font-semibold dark:text-teal-200 mb-2">
          🔁 چرخهٔ تسک (Smart Task Lifecycle)
        </div>
        <label className="flex items-start gap-2 cursor-pointer mb-2">
          <input
            type="checkbox"
            checked={w.dedup_in_manual_create !== false}
            onChange={(e) => onChange({ dedup_in_manual_create: e.target.checked })}
            className="mt-0.5 w-4 h-4"
          />
          <div className="flex-1">
            <div className="text-xs font-semibold dark:text-teal-200">
              🔍 بررسی مشابهت در ایجاد دستی
            </div>
            <div className="text-[11px] text-gray-600 dark:text-gray-300 mt-0.5">
              وقتی فعال است، در ایجاد تسک دستی (وب/تلگرام) تسک‌های مشابه نمایش داده می‌شود
              و پیش از ساخت، گزینهٔ «ادغام/جداگانه/انصراف» داده می‌شود.
            </div>
          </div>
        </label>
        {w.dedup_in_manual_create !== false && (
          <label className="block text-xs mt-1 mb-3 dark:text-gray-200">
            <span>آستانهٔ شباهت (0.50..0.95)</span>
            <input
              type="number"
              min="0.50"
              max="0.95"
              step="0.05"
              defaultValue={w.dedup_score_threshold ?? 0.65}
              onBlur={(e) => {
                const v = parseFloat(e.target.value) || 0.65;
                if (v !== (w.dedup_score_threshold ?? 0.65))
                  onChange({ dedup_score_threshold: v });
              }}
              className="w-24 mr-2 p-1.5 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
            />
            <span className="text-gray-500 dark:text-gray-400 text-[11px]">
              (پیش‌فرض 0.65 — کوچک‌تر = حساس‌تر)
            </span>
          </label>
        )}

        <label className="flex items-start gap-2 cursor-pointer mb-2">
          <input
            type="checkbox"
            checked={!!w.auto_regenerate_old_prompts}
            onChange={(e) => onChange({ auto_regenerate_old_prompts: e.target.checked })}
            className="mt-0.5 w-4 h-4"
          />
          <div className="flex-1">
            <div className="text-xs font-semibold dark:text-teal-200">
              🔄 بازتولید خودکار پرامپت‌های ناقص
            </div>
            <div className="text-[11px] text-gray-600 dark:text-gray-300 mt-0.5">
              پس از هر scan خودکار، پرامپت‌های با کیفیت پایین (کمتر از آستانه)
              با AI بازتولید می‌شوند. حداکثر ۵ تسک در هر tick.
            </div>
          </div>
        </label>
        {w.auto_regenerate_old_prompts && (
          <label className="block text-xs mt-1 dark:text-gray-200">
            <span>آستانهٔ کیفیت (40..90)</span>
            <input
              type="number"
              min="40"
              max="90"
              step="5"
              defaultValue={w.prompt_quality_threshold ?? 60}
              onBlur={(e) => {
                const v = parseInt(e.target.value, 10) || 60;
                if (v !== (w.prompt_quality_threshold ?? 60))
                  onChange({ prompt_quality_threshold: v });
              }}
              className="w-24 mr-2 p-1.5 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
            />
            <span className="text-gray-500 dark:text-gray-400 text-[11px]">
              (تسک‌های با کیفیت کمتر بازتولید می‌شوند)
            </span>
          </label>
        )}
        <div className="flex gap-2 mt-2">
          <button
            onClick={async () => {
              try {
                const res = await fetch(
                  `${API_BASE}/api/oversight/watched/${w.id}/audit-prompt-quality`,
                  { method: 'POST' },
                );
                if (res.ok) {
                  const d = await res.json();
                  alert(`scan: ${d.scanned}, کیفیت پایین: ${d.low_quality_count}`);
                }
              } catch {}
            }}
            className="text-[11px] px-2 py-1 bg-teal-200 dark:bg-teal-700 dark:text-white rounded hover:bg-teal-300"
            title="امتیاز کیفیت پرامپت تسک‌های active را به‌روز می‌کند (بدون AI call)"
          >
            🔍 امتیازدهی کیفیت
          </button>
          <button
            onClick={async () => {
              if (!confirm('پرامپت‌های با کیفیت پایین (حداکثر ۵) بازتولید شوند؟')) return;
              try {
                const res = await fetch(
                  `${API_BASE}/api/oversight/watched/${w.id}/regenerate-low-quality-prompts`,
                  {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ max_count: 5, reason: 'manual_override' }),
                  },
                );
                if (res.ok) {
                  const d = await res.json();
                  alert(`بازتولید شد: ${d.regenerated_count} از ${d.low_quality_count} ناقص`);
                }
              } catch (e: any) {
                alert(`خطا: ${e.message}`);
              }
            }}
            className="text-[11px] px-2 py-1 bg-fuchsia-500 text-white rounded hover:bg-fuchsia-600"
            title="بازتولید فوری پرامپت‌های ناقص این پروژه"
          >
            🔄 بازتولید پرامپت‌های ناقص
          </button>
        </div>
      </div>

      {/* 🆕 (auto-loop) — ping-pong continuous: فقط اگر autonomy=auto و verify_only=false */}
      {w.autonomy_level === 'auto' && !w.verify_only_mode && (
        <div className="mb-3 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
          <label className="flex items-start gap-2 cursor-pointer mb-2">
            <input
              type="checkbox"
              checked={!!w.auto_continue_until_done}
              onChange={(e) => onChange({ auto_continue_until_done: e.target.checked })}
              className="mt-0.5 w-4 h-4"
            />
            <div className="flex-1">
              <div className="text-sm font-semibold dark:text-purple-200">
                🔁 ادامهٔ خودکار تا تکمیل (ping-pong)
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 leading-relaxed">
                وقتی verify=partial شد، scheduler خودکار:
                <br />۱. پرامپت ادامه (focused on remaining) را تولید می‌کند (و نسخهٔ قبلی به history)
                <br />۲. apply می‌کند و کامیت می‌سازد
                <br />۳. دوباره verify می‌کند
                <br />تا verify=done یا max round برسد. شما فقط بعد notify می‌شوید.
              </div>
            </div>
          </label>
          {w.auto_continue_until_done && (
            <label className="block text-xs mt-2 dark:text-gray-200">
              <span>حداکثر تعداد دور (max rounds)</span>
              <input
                type="number"
                min="1"
                max="20"
                defaultValue={w.max_auto_loop_rounds ?? 5}
                onBlur={(e) => {
                  const v = parseInt(e.target.value, 10) || 5;
                  if (v !== (w.max_auto_loop_rounds ?? 5))
                    onChange({ max_auto_loop_rounds: v });
                }}
                className="w-24 mr-2 p-1.5 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
              />
              <span className="text-gray-500 dark:text-gray-400">
                (پیش‌فرض ۵ — برای جلوگیری از infinite loop)
              </span>
            </label>
          )}
        </div>
      )}

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
          title="اسکن چندفازی AI (طبق «عمق scan» در تنظیمات بالا) — یافته‌ها به تسک تبدیل می‌شوند + per-file health score"
          className="px-3 py-1.5 bg-indigo-500 text-white rounded text-sm hover:bg-indigo-600"
        >
          🔬 Deep Scan
        </button>
        <button
          onClick={onScan}
          title="اسکن تک‌پاس و سریع (~30 ثانیه) — برای کشف کلی نیازها بدون per-file scoring"
          className="px-3 py-1.5 bg-cyan-500 text-white rounded text-sm hover:bg-cyan-600"
        >
          🔎 اسکن سریع
        </button>
        <button
          onClick={onRunNow}
          disabled={taskCount === 0}
          title={
            taskCount === 0
              ? 'هیچ تسکی برای این پروژه وجود ندارد — ابتدا Deep Scan یا اسکن سریع بزنید یا یک ایده ثبت کنید'
              : `اجرای فوری ${taskCount} تسک pending موجود (تسک جدید نمی‌سازد) — برای وقتی که قبلاً تسک ساخته‌اید`
          }
          className="px-3 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ▶ بررسی فوری{taskCount > 0 ? ` (${taskCount})` : ''}
        </button>
        <button
          onClick={onWriteIdea}
          title="ایدهٔ شما را با AI به یک پرامپت ساختاریافته (هدف/context/مراحل/معیار پذیرش) تبدیل می‌کند و به‌صورت تسک ذخیره می‌کند"
          className="px-3 py-1.5 bg-purple-500 text-white rounded text-sm hover:bg-purple-600"
        >
          💡 نوشتن ایده
        </button>
        <button
          onClick={onOpenCodex}
          title="خلاصهٔ خودکار ساختار پروژه — لیست فایل‌ها با توضیح هر کدام (read-only، بدون ساخت تسک)"
          className="px-3 py-1.5 bg-amber-500 text-white rounded text-sm hover:bg-amber-600"
        >
          📖 خلاصهٔ پروژه
        </button>
        <button
          onClick={onViewTasks}
          title={`${taskCount} تسک فعال برای این پروژه — کلیک: تب «تسک‌ها» با فیلتر همین پروژه`}
          className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 dark:text-white rounded text-sm hover:bg-gray-300"
        >
          📋 تسک‌ها ({taskCount})
        </button>
        {archivedCount > 0 && (
          <button
            onClick={onViewArchive}
            title={`${archivedCount} تسک آرشیوشده (done) — تسک‌هایی که verify شده‌اند و کامل تمام شده‌اند`}
            className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 dark:text-white rounded text-sm hover:bg-gray-300"
          >
            📦 آرشیو ({archivedCount})
          </button>
        )}
        <button
          onClick={onViewReports}
          title={`${reportCount} گزارش verify برای این پروژه — کلیک: تب «گزارش‌ها» با فیلتر همین پروژه`}
          className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 dark:text-white rounded text-sm hover:bg-gray-300"
        >
          📊 گزارش‌ها ({reportCount})
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
  taskFilterArchived,
  setTaskFilterArchived,
  onOpenRegen,
  onOpenHistory,
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
  taskFilterArchived: 'active' | 'archived' | 'all';
  setTaskFilterArchived: (v: 'active' | 'archived' | 'all') => void;
  onOpenRegen: (t: Task) => void;
  onOpenHistory: (t: Task) => void;
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
            {/* 🆕 (P1+P2) metadata scan: مدل، depth، passes، files + scan_seen_count */}
            {(t.created_by_scan_metadata
              || (t.scan_seen_count ?? 1) > 1
              || (t.merge_count ?? 0) > 0
              || (t.manual_seen_count ?? 0) > 0
              || (t.prompt_history?.length ?? 0) > 0
              || typeof t.prompt_quality_score === 'number'
              || t.inspector_mode) && (
              <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2 flex-wrap" dir="ltr"
                title={t.created_by_scan_metadata ? JSON.stringify(t.created_by_scan_metadata, null, 2) : ''}>
                {t.inspector_mode === 'visual_debug' && (
                  <span
                    className="bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 px-1.5 py-0.5 rounded font-semibold"
                    title="ساخته‌شده از بازرس ویژه — حالت دیباگ بصری (با screenshots)"
                  >
                    📸 از بازرس بصری
                  </span>
                )}
                {t.inspector_mode === 'chat' && (
                  <span
                    className="bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300 px-1.5 py-0.5 rounded font-semibold"
                    title="ساخته‌شده از بازرس ویژه — حالت چت"
                  >
                    💬 از بازرس چت
                  </span>
                )}
                {t.created_by_scan_metadata?.model && (
                  <span>🤖 {t.created_by_scan_metadata.model}</span>
                )}
                {t.created_by_scan_metadata?.depth && (
                  <span>🔍 {t.created_by_scan_metadata.depth}{
                    t.created_by_scan_metadata.passes && t.created_by_scan_metadata.passes_total
                      ? ` (${t.created_by_scan_metadata.passes}/${t.created_by_scan_metadata.passes_total})` : ''
                  }</span>
                )}
                {t.created_by_scan_metadata?.files_count != null && (
                  <span>📄 {t.created_by_scan_metadata.files_count} files</span>
                )}
                {t.created_by_scan_metadata?._pass && (
                  <span className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                    {t.created_by_scan_metadata._pass}
                  </span>
                )}
                {(t.scan_seen_count ?? 1) > 1 && (
                  <span className="bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 rounded font-semibold">
                    🔁 در {t.scan_seen_count} scan دیده شد
                  </span>
                )}
                {(t.merge_count ?? 0) > 0 && (
                  <span
                    className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 px-1.5 py-0.5 rounded font-semibold"
                    title="چندبار با تسک کاندید جدید ادغام شده"
                  >
                    🔀 ادغام‌شده ({t.merge_count})
                  </span>
                )}
                {(t.manual_seen_count ?? 0) > 0 && (
                  <span
                    className="bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-1.5 py-0.5 rounded"
                    title="چندبار از طریق ایجاد دستی به همین تسک ادغام شد"
                  >
                    ✏️ {t.manual_seen_count} ایجاد دستی
                  </span>
                )}
                {(t.prompt_history?.length ?? 0) > 0 && (
                  <span
                    className="bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300 px-1.5 py-0.5 rounded"
                    title={`${t.prompt_history!.length} نسخهٔ قبلی پرامپت`}
                  >
                    🔄 پرامپت v{(t.prompt_history?.length ?? 0) + 1}
                  </span>
                )}
                {typeof t.prompt_quality_score === 'number' && (
                  <span
                    className={
                      t.prompt_quality_score >= 75
                        ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 px-1.5 py-0.5 rounded"
                        : t.prompt_quality_score >= 60
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300 px-1.5 py-0.5 rounded"
                        : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 px-1.5 py-0.5 rounded font-semibold"
                    }
                    title="امتیاز کیفیت پرامپت (0..100)"
                  >
                    {t.prompt_quality_score >= 60 ? '✓' : '⚠️'} کیفیت {t.prompt_quality_score}٪
                  </span>
                )}
              </div>
            )}
            {/* 🆕 (Inspector → Oversight) meta summary در کادر جدا (خارج از پرامپت اصلی) */}
            {t.inspector_meta_summary && (
              <details className="mt-2 text-[11px] bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded p-2">
                <summary className="cursor-pointer font-semibold text-cyan-700 dark:text-cyan-300">
                  📥 Inspector meta (خارج از کادر پرامپت — برای copy نمی‌رود)
                </summary>
                <pre className="mt-1.5 whitespace-pre-wrap break-words text-cyan-800 dark:text-cyan-200 text-[10px] leading-relaxed">
                  {t.inspector_meta_summary}
                </pre>
              </details>
            )}
            {/* 🆕 (Stage 8 — File Attachment) — فایل‌های پیوست + متن استخراج‌شده */}
            <ExtractedFilesPanel taskId={t.id} apiBase={API_BASE} />
            {/* 🆕 (Multi-pass Checklist) — وضعیت per-step + progress bar */}
            {Array.isArray(t.task_steps) && t.task_steps.length > 0 && (() => {
              const steps = t.task_steps!;
              const total = steps.length;
              const doneN = steps.filter((s) => s.status === 'done').length;
              const partialN = steps.filter((s) => s.status === 'partial').length;
              const pct = typeof t.overall_completion_pct === 'number'
                ? t.overall_completion_pct
                : Math.round(steps.reduce((a, s) => a + (s.completion_pct || 0), 0) / total);
              return (
                <details
                  className="mt-2 text-[11px] bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded p-2"
                  open={doneN < total}
                >
                  <summary className="cursor-pointer font-semibold text-indigo-700 dark:text-indigo-300 flex items-center gap-2 flex-wrap">
                    <span>📋 چک‌لیست مراحل ({doneN}/{total} انجام‌شده{partialN > 0 ? `, ${partialN} ناقص` : ''})</span>
                    <span className="text-[10px] text-indigo-600 dark:text-indigo-400">— پیشرفت کلی: <b>{pct}%</b></span>
                  </summary>
                  {/* progress bar */}
                  <div className="mt-2 h-1.5 w-full bg-indigo-100 dark:bg-indigo-900/40 rounded overflow-hidden">
                    <div
                      className={`h-full ${pct >= 100 ? 'bg-green-500' : pct >= 60 ? 'bg-indigo-500' : pct >= 30 ? 'bg-amber-500' : 'bg-red-400'}`}
                      style={{ width: `${Math.max(2, Math.min(100, pct))}%` }}
                    />
                  </div>
                  <ul className="mt-2 space-y-1">
                    {steps.map((s) => {
                      const st = s.status || 'pending';
                      const icon = st === 'done' ? '✅' : st === 'partial' ? '🟡' : st === 'error' ? '⚠️' : '⬜';
                      const titleCls = st === 'done'
                        ? 'line-through text-gray-500 dark:text-gray-400'
                        : 'text-indigo-900 dark:text-indigo-100';
                      return (
                        <li key={s.id} className="flex gap-1.5 items-start">
                          <span className="mt-0.5">{icon}</span>
                          <div className="flex-1 min-w-0">
                            <div className={`text-[11px] ${titleCls}`}>
                              <b>مرحله {s.id}: {s.title}</b>
                              {typeof s.completion_pct === 'number' && st !== 'done' && st !== 'pending' && (
                                <span className="ml-1.5 text-[10px] text-gray-500 dark:text-gray-400">({s.completion_pct}%)</span>
                              )}
                            </div>
                            {st !== 'done' && s.remaining && (
                              <div className="text-[10px] text-amber-700 dark:text-amber-300 mt-0.5">
                                ⏳ باقی‌مانده: {s.remaining}
                              </div>
                            )}
                            {s.evidence && st === 'done' && (
                              <div className="text-[10px] text-green-700 dark:text-green-300 mt-0.5 truncate">
                                📎 {s.evidence}
                              </div>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </details>
              );
            })()}
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
            <button
              onClick={() => onOpenRegen(t)}
              title="بازتولید پرامپت با کیفیت ارتقایافته (raw_idea را ویرایش کنید — تسک جدید ساخته نمی‌شود)"
              className="px-3 py-1 bg-fuchsia-500 text-white rounded text-xs hover:bg-fuchsia-600"
            >
              🔄 بازتولید
            </button>
            {(t.prompt_history && t.prompt_history.length > 0) && (
              <button
                onClick={() => onOpenHistory(t)}
                title={`${t.prompt_history!.length} نسخهٔ قبلی — شامل پرامپت‌های ادامه (followup) و بازتولید‌ها — قابل rollback`}
                className={`px-3 py-1 rounded text-xs ${
                  (t.followup_round || 0) > 0
                    ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300 hover:bg-cyan-200'
                    : 'bg-gray-200 dark:bg-gray-700 dark:text-white text-gray-700 hover:bg-gray-300'
                }`}
              >
                📜 تاریخچه ({t.prompt_history!.length})
                {(t.followup_round || 0) > 0 && <span className="mr-1">• 🔁{t.followup_round}</span>}
              </button>
            )}
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
              onClick={() => {
                if (confirm(t.archived ? 'این تسک را از آرشیو خارج کنم؟' : 'این تسک را آرشیو کنم؟')) {
                  onUpdate(t.id, { archived: !t.archived });
                }
              }}
              title={t.archived ? 'بازگردانی از آرشیو' : 'انتقال به آرشیو'}
              className="px-3 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded text-xs hover:bg-amber-200"
            >
              {t.archived ? '↩️' : '📦'}
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
                    {r.evidence && (Object.keys(r.evidence).length > 0) && (() => {
                      // نمایش زیباتر شواهد: commits، files، issues به صورت جدا
                      const commits = Array.isArray(r.evidence.commits) ? r.evidence.commits : [];
                      const files = Array.isArray(r.evidence.files) ? r.evidence.files : [];
                      const issues = Array.isArray(r.evidence.issues) ? r.evidence.issues : [];
                      const otherKeys = Object.keys(r.evidence).filter(
                        (k) => !['commits', 'files', 'issues', 'summary', 'criteria_results'].includes(k)
                      );
                      if (commits.length === 0 && files.length === 0 && issues.length === 0 && otherKeys.length === 0) {
                        return null;
                      }
                      return (
                        <div>
                          <div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">📁 شواهد:</div>
                          <div className="bg-white dark:bg-black/30 p-2 rounded text-xs space-y-1">
                            {commits.length > 0 && (
                              <div>
                                <span className="font-mono text-gray-500 dark:text-gray-400">📦 commits ({commits.length}):</span>
                                <div className="flex gap-1 flex-wrap mt-0.5">
                                  {commits.slice(0, 8).map((c: string, i: number) => (
                                    <code key={i} className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-[10px]">{String(c).slice(0, 8)}</code>
                                  ))}
                                  {commits.length > 8 && <span className="text-[10px] text-gray-500">+{commits.length - 8}</span>}
                                </div>
                              </div>
                            )}
                            {files.length > 0 && (
                              <div>
                                <span className="font-mono text-gray-500 dark:text-gray-400">📄 files ({files.length}):</span>
                                <ul className="list-disc list-inside text-[10px] mt-0.5 space-y-0.5">
                                  {files.slice(0, 10).map((f: string, i: number) => (
                                    <li key={i} className="font-mono text-gray-700 dark:text-gray-300 truncate">{f}</li>
                                  ))}
                                  {files.length > 10 && <li className="text-gray-500">… و {files.length - 10} مورد دیگر</li>}
                                </ul>
                              </div>
                            )}
                            {issues.length > 0 && (
                              <div>
                                <span className="font-mono text-gray-500 dark:text-gray-400">⚠️ issues ({issues.length}):</span>
                                <ul className="list-disc list-inside text-[10px] mt-0.5">
                                  {issues.slice(0, 5).map((iss: any, i: number) => (
                                    <li key={i}>{typeof iss === 'string' ? iss : JSON.stringify(iss).slice(0, 100)}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })()}
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
          {/* 🆕 (P3) archive filter */}
          <select
            value={taskFilterArchived}
            onChange={(e) => setTaskFilterArchived(e.target.value as any)}
            className="p-2 border rounded-lg dark:bg-gray-700 dark:text-white dark:border-gray-600 text-sm"
            title="نمایش تسک‌های فعال یا آرشیوشده"
          >
            <option value="active">📋 فعال</option>
            <option value="archived">📦 آرشیو</option>
            <option value="all">همه</option>
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
  phase3_security_deep: 'I — امنیت عمیق',
  phase3_coverage: 'J — پوشش تست',
  // 🆕 (P3) دو pass جدید
  phase3_logical_alignment: 'K — همراستایی منطقی + UI binding',
  phase3_functional_correctness: 'L — صحت رفتاری',
  phase4_aggregate: 'تجمیع و dedup',
  completed: '✅ کامل شد',
  queued: 'در صف',
};

// 🆕 (P4) tooltip توضیحی برای هر pass — برای hover روی pass label
const PASS_TOOLTIPS: Record<string, string> = {
  frontend: 'تحلیل صفحات و کامپوننت‌های Frontend — چه می‌کنند، به کدام endpoint وصل‌اند، dead link/component undefined؟',
  backend: 'تحلیل Routes و Endpointهای Backend — input/output، error handling، side effects',
  cross_stack: 'سازگاری Frontend↔Backend — orphan endpoint، contract mismatch، missing API client',
  security: 'آسیب‌پذیری‌های امنیتی پایه — XSS، CSRF، input validation، secret leakage در کد',
  integrity: 'یکپارچگی Cross-cutting — naming conflict، شارپ‌سازی state، logic duplicate',
  quality: 'کیفیت کد — dead code، complexity زیاد، magic numbers، comment‌های ناقص',
  dependency: 'ناسازگاری‌های runtime — version mismatch، deprecated API، unused dep',
  completeness: 'کامل بودن نسبت به user_goal — قابلیت‌های ذکرشده در یادداشت کاربر اجرا شده‌اند؟',
  security_deep: 'اسکن امنیتی عمیق — secrets در history، license incompatible، CVE در dependencies',
  coverage: 'پوشش تست — فایل‌های critical untested، gap detection، coverage_score',
  logical_alignment: 'همراستایی منطقی — هر فایل چه می‌کند، کجا در UI نمایان می‌شود، تضاد با file دیگر؟',
  functional_correctness: 'صحت رفتاری — edge cases، error handling، race conditions، failure modes',
};

function DeepScanProgressView({ progress }: { progress: any }) {
  if (!progress) {
    return <p className="text-center text-gray-400 py-4">در حال شروع...</p>;
  }
  const phase = progress.phase || 'init';
  const passes_total = progress.passes_total || 12;
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
  // 🆕 (P4) استخراج pass_id از phase (مثلاً phase3_logical_alignment → logical_alignment)
  const currentPassId = phase.startsWith('phase3_') ? phase.replace('phase3_', '') : '';
  const currentPassTooltip = currentPassId ? PASS_TOOLTIPS[currentPassId] : '';

  return (
    <div className="space-y-3">
      <div className="text-center">
        <div className="text-2xl mb-1">
          {isDone ? '✅' : isError ? '❌' : '🔬'}
        </div>
        <p className="font-bold dark:text-white" title={currentPassTooltip}>
          {PASS_LABELS[phase] || phase}
          {currentPassTooltip && <span className="text-blue-400 mr-1 text-sm">ⓘ</span>}
        </p>
        {!isDone && !isError && passes_total > 0 && (
          <p className="text-xs text-gray-600 dark:text-gray-300">
            pass {passes_done + 1} از {passes_total}
          </p>
        )}
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
  selectedModel,
}: {
  data: any;
  loading: boolean;
  onRefresh: () => void;
  search: string;
  onSearch: (s: string) => void;
  selectedModel?: string;
}) {
  const files = data?.files || {};
  const filtered = Object.keys(files).filter(
    (p) => !search || p.toLowerCase().includes(search.toLowerCase()),
  );

  // دسته‌بندی فایل بر اساس path — هم‌منطق با backend _categorize_file
  // اولویت: top-level dir اول، سپس extension fallback.
  const categorizeFile = (p: string): string => {
    const pl = (p || '').toLowerCase();
    // 1) tests
    if (pl.includes('/__tests__/') || pl.includes('.test.') || pl.includes('.spec.')) return 'tests';
    if (pl.includes('/tests/') || pl.startsWith('tests/') || pl.startsWith('test_')) return 'tests';
    // 2) top-level dir
    if (pl.startsWith('frontend/') || pl.startsWith('client/') || pl.startsWith('web/') || pl.startsWith('ui/'))
      return 'frontend';
    if (pl.startsWith('backend/') || pl.startsWith('server/') || pl.startsWith('api/'))
      return 'backend';
    if (pl.startsWith('scripts/') || pl.startsWith('tools/') || pl.startsWith('bin/'))
      return 'scripts';
    if (pl.includes('/docs/') || pl.startsWith('docs/')) return 'docs';
    // 3) extension fallback
    if (pl.endsWith('.py')) return 'backend';
    if (pl.endsWith('.tsx') || pl.endsWith('.jsx') || pl.endsWith('.ts') || pl.endsWith('.js')
        || pl.endsWith('.vue') || pl.endsWith('.svelte')) return 'frontend';
    const base = pl.split('/').pop() || '';
    if (pl.endsWith('.yml') || pl.endsWith('.yaml') || pl.endsWith('.toml')
        || pl.endsWith('.json') || pl.endsWith('.env.example') || base.includes('dockerfile'))
      return 'config';
    if (pl.endsWith('.md') || pl.endsWith('.rst') || pl.endsWith('.txt')) return 'docs';
    return 'other';
  };

  const overview = data?.overview || {};
  const actionItems = data?.action_items || {};

  // گروه‌بندی فایل‌های filtered بر اساس دسته
  const grouped: Record<string, string[]> = {};
  filtered.forEach((p) => {
    const cat = categorizeFile(p);
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(p);
  });
  Object.keys(grouped).forEach((k) => grouped[k].sort());

  const categoryOrder = ['backend', 'frontend', 'config', 'docs', 'scripts', 'tests', 'other'];
  const categoryLabels: Record<string, string> = {
    backend: '🐍 Backend',
    frontend: '⚛️ Frontend',
    config: '⚙️ Config',
    docs: '📖 Docs',
    scripts: '🔧 Scripts',
    tests: '🧪 Tests',
    other: '📁 سایر',
  };

  const exportMd = () => {
    // ساخت markdown کامل (همان ساختار backend _render_codex_markdown)
    const lines: string[] = [];
    lines.push(`# 📚 Codex — ${data?.repo || ''}\n`);
    if (data?.user_goal) lines.push(`> 🎯 **هدف کاربر**: ${data.user_goal}\n`);
    if (data?.stacks?.length) lines.push(`**Stack**: ${data.stacks.join(', ')}`);
    if (data?.model_used) lines.push(`**مدل**: \`${data.model_used}\``);
    if (data?.total_repo_files)
      lines.push(`**فایل‌های تحلیل‌شده**: ${data.files_count || 0} از ${data.total_repo_files}`);
    lines.push('\n---\n');
    // Overview
    if (overview.purpose) {
      lines.push('## 🎯 توضیح کلی پروژه\n');
      lines.push(overview.purpose + '\n');
      if (overview.capabilities?.length) {
        lines.push('### ✨ قابلیت‌ها\n');
        overview.capabilities.forEach((c: string) => lines.push(`- ${c}`));
        lines.push('');
      }
      if (overview.use_cases?.length) {
        lines.push('### 🎯 کاربردها\n');
        overview.use_cases.forEach((u: string) => lines.push(`- ${u}`));
        lines.push('');
      }
      if (overview.target_users) lines.push(`**کاربران هدف**: ${overview.target_users}\n`);
      const ts = overview.tech_stack || {};
      if (ts.backend || ts.frontend || ts.storage || ts.integrations?.length) {
        lines.push('### 🛠 Tech Stack\n');
        if (ts.backend) lines.push(`- **Backend**: ${ts.backend}`);
        if (ts.frontend) lines.push(`- **Frontend**: ${ts.frontend}`);
        if (ts.storage) lines.push(`- **Storage**: ${ts.storage}`);
        if (ts.integrations?.length) lines.push(`- **Integrations**: ${ts.integrations.join(', ')}`);
        lines.push('');
      }
      if (overview.architecture_summary) {
        lines.push('### 🏗 معماری\n');
        lines.push(overview.architecture_summary + '\n');
      }
      if (overview.key_concepts?.length) {
        lines.push('### 🔑 مفاهیم کلیدی\n');
        overview.key_concepts.forEach((k: string) => lines.push(`- ${k}`));
        lines.push('');
      }
      lines.push('---\n');
    }
    // Files (grouped)
    if (Object.keys(files).length > 0) {
      lines.push(`## 📂 فایل‌ها (${Object.keys(files).length} مورد)\n`);
      categoryOrder.forEach((cat) => {
        const allInCat = Object.keys(files).filter((p) => categorizeFile(p) === cat).sort();
        if (!allInCat.length) return;
        lines.push(`### ${categoryLabels[cat]} (${allInCat.length})\n`);
        allInCat.forEach((path) => {
          const f = files[path];
          lines.push(`#### \`${path}\``);
          if (f.what_is_it) lines.push(`- **این چیست؟** ${f.what_is_it}`);
          if (f.what_it_does) lines.push(`- **چه می‌کند؟** ${f.what_it_does}`);
          if (f.use_cases?.length) {
            lines.push('- **کاربردها**:');
            f.use_cases.forEach((u: string) => lines.push(`  - ${u}`));
          }
          if (f.depends_on?.length)
            lines.push(`- **وابسته به**: ${f.depends_on.map((x: string) => '`' + x + '`').join(', ')}`);
          if (f.used_by?.length)
            lines.push(`- **استفاده‌شده در**: ${f.used_by.map((x: string) => '`' + x + '`').join(', ')}`);
          if (f.relations && !f.depends_on && !f.used_by) lines.push(`- **روابط**: ${f.relations}`);
          if (f.breaks_if_removed) lines.push(`- **در صورت حذف**: ${f.breaks_if_removed}`);
          lines.push('');
        });
      });
    }
    // Action items
    if (actionItems.summary || actionItems.needs_attention?.length) {
      lines.push('---\n');
      lines.push('## 🚧 نیازمندی‌ها و بهبودها\n');
      if (actionItems.summary) lines.push(`> ${actionItems.summary}\n`);
      const priorityIcon: Record<string, string> = { critical: '🔴', high: '🟠', medium: '🟡', low: '🔵' };
      if (actionItems.needs_attention?.length) {
        lines.push('### ⚠️ موارد نیازمند توجه\n');
        actionItems.needs_attention.forEach((n: any) => {
          if (typeof n === 'object' && n.item) {
            const pri = (n.priority || 'medium').toLowerCase();
            lines.push(`- ${priorityIcon[pri] || '•'} [${pri}] ${n.item}`);
          } else {
            lines.push(`- ${n}`);
          }
        });
        lines.push('');
      }
      if (actionItems.suggested_improvements?.length) {
        lines.push('### 💡 پیشنهادات بهبود\n');
        actionItems.suggested_improvements.forEach((i: string) => lines.push(`- ${i}`));
        lines.push('');
      }
      if (actionItems.risks?.length) {
        lines.push('### ⚠️ ریسک‌ها\n');
        actionItems.risks.forEach((r: string) => lines.push(`- ${r}`));
        lines.push('');
      }
    }
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
            {data?.model_used && (
              <span className="mr-2 px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded text-[10px]" dir="ltr">
                🤖 {data.model_used}
              </span>
            )}
            {data?.used_deep_structure === false && (
              <span className="mr-2 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded text-[10px]">
                ⚠️ بدون Deep Scan
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex gap-2">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="px-3 py-1 bg-amber-500 text-white rounded text-sm hover:bg-amber-600 disabled:opacity-50"
              title={
                selectedModel
                  ? `ساخت Codex با مدل: ${selectedModel}`
                  : 'هیچ مدلی انتخاب نشده — ابتدا از بالای صفحه مدل انتخاب کنید'
              }
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
          {selectedModel ? (
            <span className="text-[10px] text-gray-500 dark:text-gray-400" dir="ltr">
              مدل انتخابی: {selectedModel}
            </span>
          ) : (
            <span className="text-[10px] text-red-500 dark:text-red-400">
              ⚠️ هیچ مدلی انتخاب نشده
            </span>
          )}
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
          <p className="text-xs mt-1">شامل: توضیح پروژه + مستندات per-file (بک + فرانت) + وابستگی‌ها + نیازمندی‌ها</p>
          <p className="text-xs mt-1">روی «به‌روزرسانی با AI» کلیک کنید</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[70vh] overflow-auto pr-1">

          {/* 🆕 (Overview) توضیح کلی پروژه */}
          {overview && (overview.purpose || overview.capabilities?.length) && (
            <details
              open
              className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded p-3"
            >
              <summary className="cursor-pointer font-bold text-sm dark:text-indigo-200">
                🎯 توضیح کلی پروژه
              </summary>
              <div className="mt-3 space-y-3 text-sm dark:text-gray-200">
                {overview.purpose && (
                  <p className="leading-relaxed">{overview.purpose}</p>
                )}
                {overview.capabilities?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1">✨ قابلیت‌ها</div>
                    <ul className="list-disc mr-5 space-y-0.5">
                      {overview.capabilities.map((c: string, i: number) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {overview.use_cases?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1">🎯 کاربردها</div>
                    <ul className="list-disc mr-5 space-y-0.5">
                      {overview.use_cases.map((u: string, i: number) => (
                        <li key={i}>{u}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {overview.target_users && (
                  <div>
                    <span className="font-semibold">کاربران هدف: </span>
                    <span>{overview.target_users}</span>
                  </div>
                )}
                {overview.tech_stack && (
                  <div>
                    <div className="font-semibold mb-1">🛠 Tech Stack</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs">
                      {overview.tech_stack.backend && <div><span className="text-gray-500">Backend:</span> {overview.tech_stack.backend}</div>}
                      {overview.tech_stack.frontend && <div><span className="text-gray-500">Frontend:</span> {overview.tech_stack.frontend}</div>}
                      {overview.tech_stack.storage && <div><span className="text-gray-500">Storage:</span> {overview.tech_stack.storage}</div>}
                      {overview.tech_stack.integrations?.length > 0 && (
                        <div className="sm:col-span-2">
                          <span className="text-gray-500">Integrations:</span> {overview.tech_stack.integrations.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                )}
                {overview.architecture_summary && (
                  <div>
                    <div className="font-semibold mb-1">🏗 معماری</div>
                    <p>{overview.architecture_summary}</p>
                  </div>
                )}
                {overview.key_concepts?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1">🔑 مفاهیم کلیدی</div>
                    <ul className="list-disc mr-5 space-y-0.5 text-xs">
                      {overview.key_concepts.map((k: string, i: number) => (
                        <li key={i}>{k}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          )}

          {/* 📂 فایل‌ها (گروه‌بندی‌شده) */}
          <div>
            <div className="font-bold text-sm dark:text-white mb-2">
              📂 فایل‌ها ({filtered.length}{filtered.length !== Object.keys(files).length ? `/${Object.keys(files).length}` : ''})
            </div>
            {categoryOrder.map((cat) => {
              const items = grouped[cat] || [];
              if (!items.length) return null;
              return (
                <details key={cat} open className="mb-2">
                  <summary className="cursor-pointer text-xs font-semibold text-gray-600 dark:text-gray-300 py-1">
                    {categoryLabels[cat]} ({items.length})
                  </summary>
                  <div className="space-y-1 mt-1 mr-2">
                    {items.map((path) => {
                      const f = files[path];
                      return (
                        <details
                          key={path}
                          className="bg-gray-50 dark:bg-gray-700/50 rounded p-2"
                        >
                          <summary className="cursor-pointer text-xs font-medium dark:text-white" dir="ltr">
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
                            {f?.depends_on?.length > 0 && (
                              <div>
                                <strong>وابسته به:</strong>{' '}
                                {f.depends_on.map((d: string, i: number) => (
                                  <code key={i} className="bg-gray-200 dark:bg-gray-600 px-1 mr-1 rounded text-[10px]" dir="ltr">
                                    {d}
                                  </code>
                                ))}
                              </div>
                            )}
                            {f?.used_by?.length > 0 && (
                              <div>
                                <strong>استفاده‌شده در:</strong>{' '}
                                {f.used_by.map((d: string, i: number) => (
                                  <code key={i} className="bg-gray-200 dark:bg-gray-600 px-1 mr-1 rounded text-[10px]" dir="ltr">
                                    {d}
                                  </code>
                                ))}
                              </div>
                            )}
                            {f?.relations && !f?.depends_on?.length && !f?.used_by?.length && (
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
                </details>
              );
            })}
          </div>

          {/* 🚧 (Action Items) نیازمندی‌ها در انتها */}
          {actionItems && (actionItems.summary || actionItems.needs_attention?.length || actionItems.suggested_improvements?.length || actionItems.risks?.length) && (
            <details
              open
              className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3"
            >
              <summary className="cursor-pointer font-bold text-sm dark:text-amber-200">
                🚧 نیازمندی‌ها و بهبودها
              </summary>
              <div className="mt-3 space-y-3 text-sm dark:text-gray-200">
                {actionItems.summary && (
                  <blockquote className="border-r-4 border-amber-400 pr-3 italic text-gray-700 dark:text-gray-300">
                    {actionItems.summary}
                  </blockquote>
                )}
                {actionItems.needs_attention?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1">⚠️ موارد نیازمند توجه</div>
                    <ul className="space-y-1">
                      {actionItems.needs_attention.map((n: any, i: number) => {
                        const item = typeof n === 'object' ? n.item : String(n);
                        const pri = typeof n === 'object' ? (n.priority || 'medium').toLowerCase() : 'medium';
                        const iconMap: Record<string, string> = { critical: '🔴', high: '🟠', medium: '🟡', low: '🔵' };
                        const colorMap: Record<string, string> = {
                          critical: 'bg-red-100 dark:bg-red-900/40',
                          high: 'bg-orange-100 dark:bg-orange-900/40',
                          medium: 'bg-yellow-100 dark:bg-yellow-900/40',
                          low: 'bg-blue-100 dark:bg-blue-900/40',
                        };
                        const icon = iconMap[pri] || '•';
                        const colorClass = colorMap[pri] || 'bg-gray-100 dark:bg-gray-700';
                        return (
                          <li key={i} className={`${colorClass} p-2 rounded text-xs flex items-start gap-2`}>
                            <span>{icon}</span>
                            <span className="flex-1">{item}</span>
                            <span className="text-[10px] text-gray-500">{pri}</span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                {actionItems.suggested_improvements?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1">💡 پیشنهادات بهبود</div>
                    <ul className="list-disc mr-5 space-y-0.5 text-xs">
                      {actionItems.suggested_improvements.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {actionItems.risks?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1">⚠️ ریسک‌ها</div>
                    <ul className="list-disc mr-5 space-y-0.5 text-xs text-red-700 dark:text-red-300">
                      {actionItems.risks.map((r: string, i: number) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          )}
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
