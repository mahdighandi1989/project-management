'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import ProjectHealthPanel from '@/components/ProjectHealthPanel';
import PromptManager from '@/components/PromptManager';
import ExecutingPromptsPanel from '@/components/ExecutingPromptsPanel';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProjectFile {
  path: string;
  content?: string;
  size?: number;
  type?: string;
  github_url?: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  type?: string;
  project_type?: string;
  status?: string;
  created_at?: string;
  files?: ProjectFile[];
  structure?: {
    directories?: string[];
    files?: any[];
    file_tree?: any[];
  };
  metadata?: {
    source?: string;
    source_url?: string;
    owner?: string;
    repo?: string;
    private?: boolean;
    stats?: {
      stars?: number;
      forks?: number;
      file_count?: number;
    };
    primary_language?: string;
  };
  technologies?: string[];
}

interface MemoryInstructions {
  content: string;
  target_models: string[];
}

interface TriggerSettings {
  enabled: boolean;
  interval_minutes: number;
  interval_type: string;
  last_run?: string;
  next_run?: string;
}

interface DynamicField {
  id: string;
  name: string;
  value: string;
  target_models: string[];
  trigger?: TriggerSettings;
  field_type?: string;  // "permanent" | "temporary"
  priority?: number;    // 1-10
  attachments?: string[];
  archived?: boolean;
  action_type?: string;
  target_path?: string;
  engineering_approval?: {
    approved: boolean;
    approved_at?: string;
    approved_by?: string;
    approval_type?: string;
  };
  // 🆕 Quick Approval fields
  needs_approval?: boolean;
  validation_marker?: string;  // "pending" | "auto_pending" | "quick_approved" | "engineering_approved"
  source?: string;
  source_issue_id?: number;
  quick_approved_at?: string;
  approver_note?: string;
  rejection_reason?: string;
  rejected_at?: string;
}

// 🆕 Feature Request interface
interface FeatureRequest {
  title: string;
  description: string;
  priority: string;
  category: string;
  target_files?: string[];
  ai_analyze: boolean;
  auto_add_roadmap: boolean;
  model_id: string;
}

// 🆕 Pending Approval interface
interface PendingApproval {
  id: string;
  name: string;
  value: string;
  priority: number;
  created_at: string;
  source: string;
  can_quick_approve: boolean;
  needs_engineering_report?: boolean;
}

interface AIModel {
  id: string;
  name: string;
  icon: string;
}

interface TriggerInterval {
  value: number;
  type: string;
  label: string;
}

// Diagram interfaces
interface DiagramNode {
  id: string;
  type: string;
  label: string;
  description?: string;
  position: { x: number; y: number };
  data?: Record<string, any>;
  style?: Record<string, any>;
  is_active?: boolean;
}

interface DiagramEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
  style?: Record<string, any>;
  animated?: boolean;
}

interface ProjectStructure {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  metadata?: Record<string, any>;
}

interface StructureSettings {
  instruction: string;
  target_models: string[];
  trigger_enabled: boolean;
  trigger_interval_minutes: number;
  trigger_interval_type: string;
  last_analysis?: string;
  next_analysis?: string;
  auto_analyze_on_import: boolean;
}

// Journal interfaces
interface ActivityLog {
  id: string;
  project_id: string;
  model_id: string;
  model_provider?: string;
  activity_type: string;
  prompt?: string;
  response?: string;
  tokens_used: number;
  latency_ms: number;
  success: boolean;
  error_message?: string;
  field_id?: string;
  field_name?: string;
  created_at: string;
  extra_data?: Record<string, any>;
}

interface ProjectReport {
  id: string;
  report_type: string;
  title: string;
  summary?: string;
  content?: string;
  total_activities: number;
  total_tokens: number;
  models_used?: string[];
  period_start?: string;
  period_end?: string;
  created_at: string;
  generated_by?: string;
}

interface JournalStats {
  period_days: number;
  total_activities: number;
  total_tokens: number;
  avg_latency_ms: number;
  success_rate: number;
  by_model: Record<string, { count: number; tokens: number }>;
  by_type: Record<string, number>;
}

interface ReportTriggerSettings {
  enabled: boolean;
  interval_minutes: number;
  interval_type: string;
  report_model: string;
  last_run?: string;
  next_run?: string;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<ProjectFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [deploying, setDeploying] = useState(false);

  // تب فعال
  const [activeTab, setActiveTab] = useState<'files' | 'memory' | 'structure' | 'journal' | 'health' | 'inspector' | 'external'>('files');

  // 🔗 External Projects state — اتصال به GitHub/Render خارجی
  const [externalConnected, setExternalConnected] = useState(false);
  const [externalProjectId, setExternalProjectId] = useState<string>('');
  const [externalRepoUrl, setExternalRepoUrl] = useState('');
  const [externalToken, setExternalToken] = useState('');
  const [externalBranch, setExternalBranch] = useState('main');
  const [externalConnecting, setExternalConnecting] = useState(false);
  const [externalConnectError, setExternalConnectError] = useState<string | null>(null);
  const [externalProjectInfo, setExternalProjectInfo] = useState<any>(null);
  const [externalFiles, setExternalFiles] = useState<any[]>([]);
  const [externalFilesLoading, setExternalFilesLoading] = useState(false);
  const [externalSelectedFile, setExternalSelectedFile] = useState<string | null>(null);
  const [externalFileContent, setExternalFileContent] = useState<string>('');
  const [externalFileLoading, setExternalFileLoading] = useState(false);
  const [externalReadme, setExternalReadme] = useState<string>('');
  const [externalAnalysis, setExternalAnalysis] = useState<any>(null);
  const [externalAnalyzing, setExternalAnalyzing] = useState(false);

  // Journal & Reports State
  const [journalLogs, setJournalLogs] = useState<ActivityLog[]>([]);
  const [journalStats, setJournalStats] = useState<JournalStats | null>(null);
  const [journalLoading, setJournalLoading] = useState(false);
  const [journalPage, setJournalPage] = useState(1);

  // 🆕 DetailedOperation State - نمایش عملیات سطر به سطر
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [detailedOperations, setDetailedOperations] = useState<Array<{
    id: string;
    operation_number: number;
    operation_type: string;
    summary: string;
    details: any;
    target_type?: string;
    target_name?: string;
    before_value?: string;
    after_value?: string;
    status: string;
    created_at: string;
  }>>([]);
  const [loadingOperations, setLoadingOperations] = useState(false);
  const [journalTotal, setJournalTotal] = useState(0);

  // 🔍 Inspector State - بازرس ویژه
  const [inspectorPowerOn, setInspectorPowerOn] = useState(false);
  const [inspectorLoading, setInspectorLoading] = useState(false);
  const [inspectorFrontendUrl, setInspectorFrontendUrl] = useState<string | null>(null);
  const [inspectorBaseUrl, setInspectorBaseUrl] = useState<string | null>(null); // URL اصلی پروژه (بدون path)
  const [inspectorIframeSrc, setInspectorIframeSrc] = useState(''); // src واقعی iframe — فقط با اقدام صریح تغییر میکند
  const [inspectorIframeLoaded, setInspectorIframeLoaded] = useState(false);
  const [inspectorIframeError, setInspectorIframeError] = useState(false);
  const [inspectorBackendLogs, setInspectorBackendLogs] = useState<Array<{
    id: string;
    timestamp: string;
    level: string;
    message: string;
    service_name: string;
  }>>([]);
  const [inspectorServices, setInspectorServices] = useState<Array<{
    id: string;
    name: string;
    type: string;
    status: string;
    url: string | null;
    role?: string;
  }>>([]);
  const [inspectorError, setInspectorError] = useState<string | null>(null);

  // 🆕 Inspector Chat State - چت با مدل‌های AI
  const [inspectorModels, setInspectorModels] = useState<Array<{
    id: string;
    name: string;
    provider: string;
    enabled: boolean;
  }>>([]);
  const [inspectorSelectedModels, setInspectorSelectedModels] = useState<string[]>([]);
  const [inspectorChatMessages, setInspectorChatMessages] = useState<Array<{
    id: string;
    db_id?: number;
    role: 'user' | 'assistant' | 'system' | 'action';
    content: string;
    model_id?: string;
    timestamp: Date;
    tokens_used?: number;
    action_type?: 'click' | 'type' | 'navigate' | 'edit' | 'read' | 'log' | 'scroll' | 'focus' | 'hover' | 'error' | 'console-error' | 'network-request' | 'network-response' | 'network-error';
    network_meta?: {
      reqId?: string;
      method?: string;
      url?: string;
      status?: number;
      durationMs?: number;
      ok?: boolean;
      errorMessage?: string;
      startedAt?: number;
    } | null;
    backend_verified?: boolean | null;  // null=pending, true=ok, false=error
    backend_log_summary?: string;
    verified_by_model?: string;
    logs_checked?: number;
    error_logs_count?: number;
    checked_logs?: Array<{ level: string; message: string; timestamp: string | null; service_id?: string }>;
  }>>([]);
  const [inspectorSessionId, setInspectorSessionId] = useState<number | null>(null);
  const inspectorSessionIdRef = useRef<number | null>(null);
  const [inspectorMsgInfoId, setInspectorMsgInfoId] = useState<string | null>(null);
  const [inspectorMsgLogsId, setInspectorMsgLogsId] = useState<string | null>(null);  // ID پیام برای نمایش لاگ‌ها
  const [inspectorArchivedSessions, setInspectorArchivedSessions] = useState<Array<{
    id: number;
    title: string;
    created_at: string;
    closed_at: string;
    message_count: number;
    status: string;
  }>>([]);
  const [showArchivedSessions, setShowArchivedSessions] = useState(false);
  const [inspectorChatInput, setInspectorChatInput] = useState('');
  const [inspectorChatLoading, setInspectorChatLoading] = useState(false);
  const [inspectorShowModelSelector, setInspectorShowModelSelector] = useState(false);
  // 🔧 فیلتر انواع اکشن‌ها - همه فعال بجز scroll و network-request پرسر و صدا
  const [inspectorActionFilters, setInspectorActionFilters] = useState<Record<string, boolean>>({
    'click': true,
    'scroll': false,
    'input': true,
    'focus': true,
    'hover': true,
    'error': true,
    'console-error': true,
    'error-overlay': true,
    // 🌐 Network events — پاسخ‌ها و خطاها به‌صورت پیش‌فرض روشن، شروع درخواست خاموش
    'network-request': false,
    'network-response': true,
    'network-error': true,
  });
  const inspectorActionFiltersRef = useRef<Record<string, boolean>>({
    'click': true,
    'scroll': false,
    'input': true,
    'focus': true,
    'hover': true,
    'error': true,
    'console-error': true,
    'error-overlay': true,
    'network-request': false,
    'network-response': true,
    'network-error': true,
  });

  // 🛡️ Inspector hardening: dedup + verify retry tracking + console log cap
  // dedup map: کلید = action_type:timestamp:digest(target+content) → مقدار = Date.now()
  // entryهای قدیمی‌تر از window×۵ هر ۳۰ ثانیه پاک می‌شوند (در WebSocket useEffect)
  const inspectorSeenEventsRef = useRef<Map<string, number>>(new Map());
  const INSPECTOR_DEDUP_WINDOW_MS = 2000;
  const [inspectorDuplicatesDroppedCount, setInspectorDuplicatesDroppedCount] = useState(0);
  const [inspectorVerifyPendingCount, setInspectorVerifyPendingCount] = useState(0);
  const inspectorPowerOnRef = useRef(false);
  // console log cap قابل تنظیم (پیش‌فرض ۲۰۰۰، به جای ۵۰۰)
  const [consoleLogCap, setConsoleLogCap] = useState(2000);
  const [consoleLogDroppedCount, setConsoleLogDroppedCount] = useState(0);
  const consoleLogCapRef = useRef(consoleLogCap);
  consoleLogCapRef.current = consoleLogCap;

  // 🔄 Restore chat from DB on mount + manual reload control
  const [inspectorChatRestored, setInspectorChatRestored] = useState(false);
  const [inspectorChatRestoring, setInspectorChatRestoring] = useState(false);
  const [inspectorRestoreError, setInspectorRestoreError] = useState<string | null>(null);

  const [inspectorReplyTo, setInspectorReplyTo] = useState<{
    id: string;
    content: string;
    role: string;
    model_id?: string;
  } | null>(null);

  // ردیابی فایل‌های خوانده‌شده در طول مکالمه (برای هدایت AI به فایل‌های جدید)
  const [previouslyReadFiles, setPreviouslyReadFiles] = useState<string[]>([]);

  // 🔍 بررسی و اصلاح خطا
  const [investigateModalMsgId, setInvestigateModalMsgId] = useState<string | null>(null);  // شناسه پیام خطا
  const [investigateModels, setInvestigateModels] = useState<Array<{
    id: string; name: string; provider: string; enabled: boolean; provider_available: boolean;
    capabilities: string[]; context_window: number; recommendation_score: number; recommended: boolean;
  }>>([]);
  const [investigateSelectedModels, setInvestigateSelectedModels] = useState<string[]>([]);
  const [investigateLoading, setInvestigateLoading] = useState(false);
  const [investigateReport, setInvestigateReport] = useState<{
    report: string; files_investigated: string[]; files_to_fix: Array<{path: string}>;
    error_content: string; github_repo: string; model_used: string;
  } | null>(null);
  const [fixModalOpen, setFixModalOpen] = useState(false);
  const [fixSelectedModels, setFixSelectedModels] = useState<string[]>([]);
  const [fixLoading, setFixLoading] = useState(false);

  // 🆕 انتخاب چندتایی خطاها برای بررسی کلی
  const [errorMultiSelectMode, setErrorMultiSelectMode] = useState(false);
  const [selectedErrorIds, setSelectedErrorIds] = useState<string[]>([]);
  const [bulkInvestigateModalOpen, setBulkInvestigateModalOpen] = useState(false);

  // 🔒 قفل عملیات - iframe و چت قفل میشن هنگام بررسی/اصلاح
  const [inspectorOpLock, setInspectorOpLock] = useState(false);
  const [inspectorOpPaused, setInspectorOpPaused] = useState(false);
  const inspectorOpAbortRef = useRef<AbortController | null>(null);
  const inspectorBatchTaskKeyRef = useRef<string | null>(null);
  const [inspectorOpType, setInspectorOpType] = useState<'investigate' | 'fix' | null>(null);

  // 🆕 انتخاب خودکار مدل و همکاری
  const [inspectorAutoSelect, setInspectorAutoSelect] = useState(true); // پیش‌فرض فعال
  const [inspectorCollaborativeMode, setInspectorCollaborativeMode] = useState(true);
  const [inspectorSmartPrompt, setInspectorSmartPrompt] = useState(true); // 🧠 پرامپت ساختارمند — پیش‌فرض فعال
  const [inspectorActiveTask, setInspectorActiveTask] = useState<{
    id: string;
    description: string;
    models: string[];
    status: 'running' | 'completed' | 'failed';
    actions: Array<{
      model_id: string;
      action: string;
      timestamp: Date;
      status: 'pending' | 'running' | 'done';
    }>;
  } | null>(null);
  const [inspectorVirtualCursor, setInspectorVirtualCursor] = useState<{
    x: number;
    y: number;
    visible: boolean;
    model_id?: string;
  }>({ x: 0, y: 0, visible: false });
  const [inspectorGithubConnected, setInspectorGithubConnected] = useState(false);

  // 🆕 Visual Scan - نوارهای اسکن بصری
  const [inspectorScanBars, setInspectorScanBars] = useState<{
    verticalX: number;  // موقعیت نوار عمودی (درصد از چپ)
    horizontalY: number;  // موقعیت نوار افقی (درصد از بالا)
    scanning: boolean;  // آیا در حال اسکن است
    targetFound: boolean;  // آیا هدف پیدا شد
    intersection: { x: number; y: number; text: string } | null;  // نقطه تقاطع
  }>({
    verticalX: 0,
    horizontalY: 0,
    scanning: false,
    targetFound: false,
    intersection: null
  });

  // 🆕 Live Action Tracking - رصد لحظه‌ای فعالیت کاربر در پیش‌نمایش
  const [inspectorActionTracking, setInspectorActionTracking] = useState({
    enabled: true,  // آیا ردیابی فعال است
    lastAction: null as {
      type: 'click' | 'scroll' | 'input' | 'navigate';
      x: number;
      y: number;
      timestamp: Date;
      elementInfo?: string;
    } | null,
  });

  const [inspectorTransientMessages, setInspectorTransientMessages] = useState<Array<{
    id: string;
    content: string;
    type: 'action' | 'backend' | 'error' | 'info';
    source?: string;  // کدام مدل این گزارش را داده
    timestamp: Date;
    fadeOut: boolean;  // آیا در حال محو شدن است
  }>>([]);

  const [inspectorPaused, setInspectorPaused] = useState(false);  // متوقف شده به دلیل خطا
  const [inspectorPausedError, setInspectorPausedError] = useState<{
    message: string;
    details: string;
    analyzing: boolean;  // در حال تحلیل علت خطا
    sourceFiles?: Array<{path: string; issue: string}>;
  } | null>(null);

  const inspectorIframeRef = useRef<HTMLIFrameElement>(null);
  const inspectorOverlayRef = useRef<HTMLDivElement>(null);

  // 🌐 WebSocket Bridge - ارتباط مستقیم با Bridge Script بدون وابستگی به iframe/postMessage
  const bridgeWsRef = useRef<WebSocket | null>(null);
  const [bridgeWsConnected, setBridgeWsConnected] = useState(false);
  const [bridgePeerConnected, setBridgePeerConnected] = useState(false);

  // 🌉 وضعیت Bridge Script - اسکریپت ارتباطی با iframe
  const [inspectorBridgeStatus, setInspectorBridgeStatus] = useState<{
    checking: boolean;
    injecting: boolean;
    has_bridge: boolean;
    file_path?: string;
    error?: string;
    needs_update?: boolean;
    update_reasons?: string[];
    version?: string;
    latest_version?: string;
  }>({
    checking: false,
    injecting: false,
    has_bridge: false
  });

  // 🔗 دیالوگ تنظیم آدرس GitHub
  const [showGitHubPathDialog, setShowGitHubPathDialog] = useState(false);
  const [gitHubPathInput, setGitHubPathInput] = useState('');
  const [settingGitHubPath, setSettingGitHubPath] = useState(false);

  // 📁 دیالوگ مسیر سفارشی فایل HTML
  const [showCustomHtmlPathDialog, setShowCustomHtmlPathDialog] = useState(false);
  const [customHtmlPathInput, setCustomHtmlPathInput] = useState('');
  const [foundHtmlFiles, setFoundHtmlFiles] = useState<string[]>([]);
  const [detectedFramework, setDetectedFramework] = useState<string | null>(null);
  const [isBackendOnly, setIsBackendOnly] = useState(false);

  // 📸 Visual Debug - دیباگ بصری با عکس‌برداری
  const [visualDebugMode, setVisualDebugMode] = useState(false);
  const [visualDebugScreenshots, setVisualDebugScreenshots] = useState<Array<{
    id: string;
    base64: string;
    timestamp: Date;
    pageUrl: string;
    // 📦 Pack: snapshot of logs/URLs at capture time
    consoleLogs: Array<{ level: string; message: string; timestamp: number; source: string }>;
    backendLogs: Array<{ level: string; message: string; timestamp: string; service_name: string }>;
    relatedUrls: string[];
    apiPaths: string[];  // Backend API paths detected from logs (e.g., /api/users, /api/products)
  }>>([]);
  const [visualDebugConsoleLogs, setVisualDebugConsoleLogs] = useState<Array<{
    level: string;
    message: string;
    timestamp: number;
    source: string;
  }>>([]);
  const [visualDebugDescription, setVisualDebugDescription] = useState('');
  const [visualDebugTakingScreenshot, setVisualDebugTakingScreenshot] = useState(false);
  const [visualDebugModelSelection, setVisualDebugModelSelection] = useState(false);
  const [visualDebugVisionModels, setVisualDebugVisionModels] = useState<Array<{
    id: string; name: string; provider: string; enabled: boolean;
    supports_images: boolean; capabilities: string[];
    context_window: number; recommended: boolean;
  }>>([]);
  const [visualDebugSelectedModels, setVisualDebugSelectedModels] = useState<string[]>([]);
  const [visualDebugLoading, setVisualDebugLoading] = useState(false);
  const [visualDebugPromptOpen, setVisualDebugPromptOpen] = useState(false);
  const [visualDebugPromptData, setVisualDebugPromptData] = useState<{vd: Array<{id: string; title: string; content: string; icon: string; prompt_detail?: string}>; gen: Array<{id: string; title: string; content: string; icon: string; prompt_detail?: string}>} | null>(null);

  // 🔄 بازتحلیل دیباگ بصری با مدل دوم
  const [reanalyzeModalOpen, setReanalyzeModalOpen] = useState(false);
  const [reanalyzeSourceMsgId, setReanalyzeSourceMsgId] = useState<string>('');
  const [reanalyzeSelectedModel, setReanalyzeSelectedModel] = useState<string>('');
  const [reanalyzeLoading, setReanalyzeLoading] = useState(false);

  // 📋 لاگ‌های کنسول پروژه ایمپورت شده (تفکیک شده از پروژه اصلی)
  const [importedProjectConsoleLogs, setImportedProjectConsoleLogs] = useState<Array<{
    id: string;
    level: string;
    message: string;
    timestamp: number;
    source: string;
  }>>([]);
  const importedConsoleLogsRef = useRef(importedProjectConsoleLogs);
  importedConsoleLogsRef.current = importedProjectConsoleLogs;
  const [showImportedConsoleLogs, setShowImportedConsoleLogs] = useState(false);

  // 🔍 Debug Bridge - برای تشخیص مشکلات
  const [bridgeDebugInfo, setBridgeDebugInfo] = useState<{
    loading: boolean;
    data?: {
      bridge_injected?: boolean;
      deployed_has_bridge?: boolean;
      diagnosis?: string;
      files_with_bridge?: Array<{path: string; has_bridge: boolean}>;
      html_files?: string[];
      preview_url?: string;
    };
  }>({ loading: false });

  // 📋 مدیریت فیلدهای دستورات، حافظه و آموزش مدل‌ها
  const [promptFields, setPromptFields] = useState<Array<{
    id: string;
    project_id: string;
    category: 'instruction' | 'memory' | 'training';
    title: string;
    content: string;
    priority: number;
    is_active: boolean;
    usage_count: number;
    last_used_at: string | null;
    last_tested_at: string | null;
    last_test_passed: boolean | null;
    last_test_result: any;
    created_at: string;
    updated_at: string;
  }>>([]);
  const [promptFieldsLoading, setPromptFieldsLoading] = useState(false);
  const [promptFieldsOpen, setPromptFieldsOpen] = useState(false);
  const [promptFieldEditing, setPromptFieldEditing] = useState<string | null>(null);
  const [promptFieldEditData, setPromptFieldEditData] = useState<{title: string; content: string; category: string; priority: number}>({title: '', content: '', category: 'instruction', priority: 0});
  const [promptFieldAdding, setPromptFieldAdding] = useState(false);
  const [promptFieldNewData, setPromptFieldNewData] = useState<{title: string; content: string; category: string; priority: number}>({title: '', content: '', category: 'instruction', priority: 0});
  const [promptFieldTesting, setPromptFieldTesting] = useState<string | null>(null);
  const [promptFieldTestResult, setPromptFieldTestResult] = useState<{field_id: string; passed: boolean; response: string; model_id: string} | null>(null);
  const [promptFieldsHighlighted, setPromptFieldsHighlighted] = useState<string[]>([]);
  const [promptFieldActiveCategory, setPromptFieldActiveCategory] = useState<'all' | 'instruction' | 'memory' | 'training'>('all');
  const [generalInstructions, setGeneralInstructions] = useState<Array<{id: string; title: string; content: string; icon: string; prompt_detail?: string}>>([]);
  const [generalInstructionsOpen, setGeneralInstructionsOpen] = useState(false);

  const [journalFilter, setJournalFilter] = useState<{type?: string; model?: string; success?: boolean}>({});
  const [selectedLog, setSelectedLog] = useState<ActivityLog | null>(null);
  const [reports, setReports] = useState<ProjectReport[]>([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ProjectReport | null>(null);
  const [reportTrigger, setReportTrigger] = useState<ReportTriggerSettings>({
    enabled: false,
    interval_minutes: 1440,
    interval_type: 'days',
    report_model: 'openai',
  });
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportProgress, setReportProgress] = useState<{step: number; total: number; message: string; progress: number} | null>(null);
  const [journalSubTab, setJournalSubTab] = useState<'logs' | 'reports' | 'validation' | 'profiles' | 'roadmap'>('logs');

  // 🆕 انتخاب مدل برای گزارش مهندسی (دستی)
  const [selectedEngineeringModels, setSelectedEngineeringModels] = useState<string[]>(['claude']);
  const [showEngineeringModelSelector, setShowEngineeringModelSelector] = useState(false);
  const [engineeringReportDepth, setEngineeringReportDepth] = useState<'quick' | 'standard' | 'deep'>('standard');

  // 🆕 مدیریت پرامپت‌ها
  const [showEngineeringPrompts, setShowEngineeringPrompts] = useState(false);
  const [showAutoSetupPrompts, setShowAutoSetupPrompts] = useState(false);

  // 🔴 وضعیت اجرای پرامپت‌ها
  const [activePromptExecutions, setActivePromptExecutions] = useState<{
    id: string;
    prompt_id: string;
    prompt_name: string;
    prompt_category: string;
    status: string;
    started_at: string;
  }[]>([]);

  // Roadmap State (در تب ژورنال)
  const [roadmapContent, setRoadmapContent] = useState<string>('');
  const [roadmapItems, setRoadmapItems] = useState<Array<{
    id: string;
    text: string;
    completed: boolean;
    priority: 'immediate' | 'short_term' | 'long_term';
    has_field?: boolean;
    field_id?: string;
  }>>([]);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [idealState, setIdealState] = useState<string>('');
  const [generatingRoadmapFields, setGeneratingRoadmapFields] = useState(false);

  // Validation & Model Profiles State
  const [modelProfiles, setModelProfiles] = useState<any[]>([]);
  const [profilesLoading, setProfilesLoading] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<any>(null);
  const [modelRankings, setModelRankings] = useState<any[]>([]);
  const [leaderboard, setLeaderboard] = useState<any>(null);
  const [validationInProgress, setValidationInProgress] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);

  // Structure Diagram State
  const [structureData, setStructureData] = useState<ProjectStructure | null>(null);
  const [structureSettings, setStructureSettings] = useState<StructureSettings>({
    instruction: 'تمام پروژه را از ریز تا درشت بررسی کن و ساختار کامل آن را استخراج کن',
    target_models: ['all'],
    trigger_enabled: true,
    trigger_interval_minutes: 30,
    trigger_interval_type: 'minutes',
    auto_analyze_on_import: true,
  });
  const [structureLoading, setStructureLoading] = useState(false);
  const [analyzingStructure, setAnalyzingStructure] = useState(false);
  const [savingStructureSettings, setSavingStructureSettings] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Health Map State - برای رنگ‌بندی دیاگرام بر اساس سلامت
  const [fileHealthMap, setFileHealthMap] = useState<Record<string, {
    score: number;
    color: string;
    hex: string;
    label: string;
    models_analyzed: number;
    model_scores: Record<string, number>;
    issues_count: number;
    analyzed_at: string;
  }>>({});
  const [healthDataLoaded, setHealthDataLoaded] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Memory Box State
  const [memoryInstructions, setMemoryInstructions] = useState<MemoryInstructions>({
    content: '',
    target_models: ['all']
  });
  const [dynamicFields, setDynamicFields] = useState<DynamicField[]>([]);
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [triggerIntervals, setTriggerIntervals] = useState<TriggerInterval[]>([]);
  const [savingMemory, setSavingMemory] = useState(false);
  const [executingTrigger, setExecutingTrigger] = useState<string | null>(null);
  const [runningAutoSetup, setRunningAutoSetup] = useState(false);

  // New Field Form
  const [showNewFieldForm, setShowNewFieldForm] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldValue, setNewFieldValue] = useState('');
  const [newFieldModels, setNewFieldModels] = useState<string[]>(['all']);
  const [newFieldTriggerEnabled, setNewFieldTriggerEnabled] = useState(false);
  const [newFieldTriggerInterval, setNewFieldTriggerInterval] = useState(60);
  const [newFieldTriggerType, setNewFieldTriggerType] = useState('minutes');
  // تنظیمات GitHub و بایگانی
  const [newFieldActionType, setNewFieldActionType] = useState('display');
  const [newFieldTargetPath, setNewFieldTargetPath] = useState('');
  const [newFieldArchiveAfterRun, setNewFieldArchiveAfterRun] = useState(false);
  const [newFieldDeployAfterCommit, setNewFieldDeployAfterCommit] = useState(false);
  const [showArchivedFields, setShowArchivedFields] = useState(false);

  // نوع فیلد و اولویت
  const [newFieldType, setNewFieldType] = useState('temporary');  // temporary | permanent
  const [newFieldPriority, setNewFieldPriority] = useState(5);     // 1-10

  // اجرای گروهی
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [executingBatch, setExecutingBatch] = useState(false);
  const [batchStatus, setBatchStatus] = useState<{
    status: 'idle' | 'running' | 'paused' | 'stopped' | 'completed';
    progress: number;
    current: number;
    total: number;
    currentFieldName?: string;
    archivedCount?: number;
    completedCount?: number;
    failedCount?: number;
  }>({ status: 'idle', progress: 0, current: 0, total: 0 });

  // آپلود پیوست
  const [uploadingAttachment, setUploadingAttachment] = useState<string | null>(null);

  // Edit Field
  const [editingField, setEditingField] = useState<string | null>(null);

  // 🆕 Quick Approval State
  const [showQuickApprovalPanel, setShowQuickApprovalPanel] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState<{
    auto_pending: PendingApproval[];
    pending: PendingApproval[];
    total: number;
  }>({ auto_pending: [], pending: [], total: 0 });
  const [loadingApprovals, setLoadingApprovals] = useState(false);
  const [approvingField, setApprovingField] = useState<string | null>(null);
  const [rejectingField, setRejectingField] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [autoConvertingIssues, setAutoConvertingIssues] = useState(false);

  // 🆕 Feature Request State
  const [showFeatureRequestForm, setShowFeatureRequestForm] = useState(false);
  const [featureRequest, setFeatureRequest] = useState<FeatureRequest>({
    title: '',
    description: '',
    priority: 'medium',
    category: 'feature',
    target_files: [],
    ai_analyze: true,
    auto_add_roadmap: true,
    model_id: 'claude'
  });
  const [submittingFeatureRequest, setSubmittingFeatureRequest] = useState(false);
  const [featureRequestResult, setFeatureRequestResult] = useState<any>(null);

  // AI Chat State
  const [chatPrompt, setChatPrompt] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedChatModel, setSelectedChatModel] = useState('openai');
  const [includeMemory, setIncludeMemory] = useState(true);
  const [showChatBox, setShowChatBox] = useState(false);

  // Enhanced Chat State (Multi-model support)
  const [useEnhancedChat, setUseEnhancedChat] = useState(true);
  const [selectedChatModels, setSelectedChatModels] = useState<string[]>(['openai']);
  const [includeFiles, setIncludeFiles] = useState(true);
  const [includeIssues, setIncludeIssues] = useState(true);
  const [includeHealth, setIncludeHealth] = useState(true);
  const [createDynamicFields, setCreateDynamicFields] = useState(false);
  const [enhancedChatResponses, setEnhancedChatResponses] = useState<Array<{
    model_id: string;
    actual_model?: string;
    content: string | null;
    tokens_used?: number;
    latency_ms?: number;
    success: boolean;
    error?: string;
  }>>([]);
  const [createdFieldsFromChat, setCreatedFieldsFromChat] = useState<DynamicField[]>([]);

  // Activity Visualization State (for diagram blinking/highlighting)
  const [activeWorkflow, setActiveWorkflow] = useState<{
    nodeIds: string[];
    edgeIds: string[];
    type: 'trigger' | 'deploy' | 'commit' | null;
  }>({ nodeIds: [], edgeIds: [], type: null });

  // Sync Settings State
  const [syncSettings, setSyncSettings] = useState({
    auto_sync_enabled: false,
    sync_interval_minutes: 15,
    sync_after_field_execution: true,
    sync_after_commit: true,
    update_diagram_after_sync: true,
    update_structure_after_sync: true,
  });
  const [showSyncSettings, setShowSyncSettings] = useState(false);
  const [savingSyncSettings, setSavingSyncSettings] = useState(false);
  const [syncIntervalTimer, setSyncIntervalTimer] = useState<NodeJS.Timeout | null>(null);

  // Render Service Selector State
  const [showServiceSelector, setShowServiceSelector] = useState(false);
  const [availableRenderServices, setAvailableRenderServices] = useState<{id: string; name: string; type: string}[]>([]);
  const [selectedRenderServices, setSelectedRenderServices] = useState<string[]>([]);
  const [savedRenderServices, setSavedRenderServices] = useState<{id: string; name: string}[]>([]);

  // 🆕 ایجاد سرویس Render
  const [showCreateRenderService, setShowCreateRenderService] = useState(false);
  const [createRenderLoading, setCreateRenderLoading] = useState(false);

  // ==========================================================
  // 🔗 Oversight bridge — وضعیت تسک‌های مرکز نظارت برای این پروژه
  // ==========================================================
  const [oversightBridgeSummary, setOversightBridgeSummary] = useState<{
    project_id: string;
    project_full_name: string;
    total: number;
    pending: number;
    in_review: number;
    done: number;
  } | null>(null);
  const [oversightExternalCount, setOversightExternalCount] = useState<number>(0);

  const loadOversightBridge = useCallback(async () => {
    if (!projectId) return;
    // 1) /projects → /oversight: تسک‌های نظارتی که برای این پروژه ساخته شده‌اند
    try {
      const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectId)}/oversight-summary`);
      if (res.ok) {
        const data = await res.json();
        setOversightBridgeSummary({
          project_id: data.project_id,
          project_full_name: data.project_full_name,
          total: data.total || 0,
          pending: data.pending || 0,
          in_review: data.in_review || 0,
          done: data.done || 0,
        });
      }
    } catch (e) { /* non-critical */ }
    // 2) /oversight → /projects: dynamic_fields این پروژه که در /oversight قابل verify هستند
    try {
      const res2 = await fetch(`${API_BASE}/api/oversight/external-tasks?project_id=${encodeURIComponent(projectId)}`);
      if (res2.ok) {
        const data2 = await res2.json();
        setOversightExternalCount(Array.isArray(data2?.items) ? data2.items.length : 0);
      }
    } catch (e) { /* non-critical */ }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadOversightBridge();
    }
  }, [projectId, loadOversightBridge]);

  useEffect(() => {
    if (projectId) {
      loadProject();
      loadMemory();
      loadSyncSettings();
      loadPendingApprovals(); // 🆕 بارگذاری فیلدهای در انتظار تایید
      // 🔴 چک کردن وضعیت اجرای گروهی هنگام لود صفحه
      checkBatchStatusOnLoad();
    }
  }, [projectId]);

  // 🔴 چک کردن وضعیت اجرای گروهی هنگام لود صفحه
  const checkBatchStatusOnLoad = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/batch-status`);
      const data = await res.json();
      if (data.success && data.is_running) {
        // اگر اجرا در حال انجامه، state رو ست کن و polling رو شروع کن
        setBatchStatus({
          status: data.status,
          progress: data.progress_percent,
          current: data.current_index,
          total: data.total_fields,
        });
        if (data.status === 'running' || data.status === 'paused') {
          setExecutingBatch(true);
        }
      }
    } catch (e) {
      console.log('Error checking batch status on load:', e);
    }
  };

  // راه‌اندازی سینک خودکار وقتی تنظیمات تغییر کنه
  useEffect(() => {
    if (project?.project_type === 'github_import') {
      setupAutoSync();
    }
  }, [syncSettings.auto_sync_enabled, syncSettings.sync_interval_minutes, project?.project_type]);

  // بارگذاری ساختار وقتی تب ساختار باز میشه
  useEffect(() => {
    if (activeTab === 'structure' && projectId) {
      loadStructure();
    }
  }, [activeTab, projectId]);

  // بارگذاری ژورنال وقتی تب ژورنال باز میشه
  useEffect(() => {
    if (activeTab === 'journal' && projectId) {
      loadJournal();
      loadJournalStats();
      loadReports();
      loadReportTrigger();
    }
  }, [activeTab, projectId]);

  // بارگذاری پروفایل مدل‌ها وقتی سابتب تغییر کنه
  useEffect(() => {
    if (activeTab === 'journal' && (journalSubTab === 'profiles' || journalSubTab === 'validation')) {
      loadModelProfiles();
      loadModelRankings();
      loadLeaderboard();
    }
  }, [activeTab, journalSubTab]);

  // بارگذاری نقشه راه وقتی سابتب تغییر کنه
  useEffect(() => {
    if (activeTab === 'journal' && journalSubTab === 'roadmap' && projectId) {
      loadRoadmap();
    }
  }, [activeTab, journalSubTab, projectId]);

  // بروزرسانی استایل نودها و لبه‌ها وقتی workflow فعال میشه
  useEffect(() => {
    if (activeWorkflow.type && activeWorkflow.nodeIds.length > 0) {
      // هایلایت کردن نودها
      setNodes((nds) =>
        nds.map((node) => {
          const isActive = activeWorkflow.nodeIds.includes(node.id);
          return {
            ...node,
            style: {
              ...node.style,
              border: isActive ? '3px solid #22c55e' : node.style?.border || '1px solid #4b5563',
              boxShadow: isActive ? '0 0 20px #22c55e' : node.style?.boxShadow || '0 2px 4px rgba(0,0,0,0.2)',
              animation: isActive ? 'pulse 1s ease-in-out infinite' : 'none',
            },
          };
        })
      );

      // هایلایت کردن لبه‌ها
      setEdges((eds) =>
        eds.map((edge) => {
          const isActive = activeWorkflow.edgeIds.includes(edge.id);
          return {
            ...edge,
            animated: isActive,
            style: {
              ...edge.style,
              stroke: isActive ? '#22c55e' : edge.style?.stroke || '#6b7280',
              strokeWidth: isActive ? 3 : edge.style?.strokeWidth || 2,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: isActive ? '#22c55e' : '#6b7280',
            },
          };
        })
      );

      // غیرفعال کردن بعد از 5 ثانیه
      const timer = setTimeout(() => {
        setActiveWorkflow({ nodeIds: [], edgeIds: [], type: null });
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [activeWorkflow]);

  // 🔧 همگام‌سازی ref فیلتر اکشن‌ها با state
  useEffect(() => {
    inspectorActionFiltersRef.current = inspectorActionFilters;
  }, [inspectorActionFilters]);

  // 🔧 همگام‌سازی ref وضعیت روشنی Inspector — برای abort کردن retry های در جریان
  useEffect(() => {
    inspectorPowerOnRef.current = inspectorPowerOn;
  }, [inspectorPowerOn]);

  // 🔄 Restore chat from DB
  // وقتی session ست می‌شود (یا کاربر force می‌کند) آخرین پیام‌ها از DB pull می‌شوند
  // و در ابتدای chat قرار می‌گیرند. dedup با id تضمین می‌کند تکراری نشوند.
  const restoreInspectorChatFromDb = useCallback(async (force: boolean = false) => {
    const sid = inspectorSessionIdRef.current;
    if (!sid) return;
    if (inspectorChatRestored && !force) return;
    setInspectorChatRestoring(true);
    setInspectorRestoreError(null);
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/session/${sid}/messages`);
      const data = await res.json();
      if (data.success && Array.isArray(data.messages)) {
        const restored = data.messages.map((m: any) => {
          // extract network_meta from extra_data if present
          let networkMeta: any = null;
          try {
            const ed = typeof m.extra_data === 'string' ? JSON.parse(m.extra_data) : m.extra_data;
            if (ed && ed.network_meta) networkMeta = ed.network_meta;
          } catch (e) { /* parse failed - non-critical */ }
          return {
            id: `restored_${m.id}`,
            db_id: m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.timestamp || m.created_at || Date.now()),
            action_type: m.action_type || undefined,
            backend_verified: m.backend_verified ?? null,
            backend_log_summary: m.backend_log_summary,
            verified_by_model: m.verified_by_model,
            logs_checked: m.logs_checked,
            error_logs_count: m.error_logs_count,
            checked_logs: m.checked_logs,
            network_meta: networkMeta,
            ...(m.model_id ? { model_id: m.model_id } : {}),
            ...(m.tokens_used ? { tokens_used: m.tokens_used } : {}),
          };
        });
        // dedup: اگر پیامی با همان db_id در state موجود است، آن را skip کن
        setInspectorChatMessages(prev => {
          const existingDbIds = new Set(prev.map((p: any) => p.db_id).filter(Boolean));
          const filtered = restored.filter((r: any) => !existingDbIds.has(r.db_id));
          // مرتب‌سازی بر اساس timestamp برای حفظ ترتیب چرونولوژیک
          const merged = [...filtered, ...prev];
          merged.sort((a: any, b: any) => {
            const ta = a.timestamp instanceof Date ? a.timestamp.getTime() : new Date(a.timestamp).getTime();
            const tb = b.timestamp instanceof Date ? b.timestamp.getTime() : new Date(b.timestamp).getTime();
            return ta - tb;
          });
          return merged;
        });
        setInspectorChatRestored(true);
      } else {
        setInspectorRestoreError(data.error || 'بارگذاری ناموفق');
      }
    } catch (e: any) {
      setInspectorRestoreError(e?.message || 'خطا در ارتباط با backend');
    } finally {
      setInspectorChatRestoring(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inspectorChatRestored]);

  // trigger خودکار وقتی session_id جدید ست می‌شود (و قبلاً restore نشده)
  useEffect(() => {
    if (inspectorSessionId && !inspectorChatRestored && activeTab === 'inspector') {
      // small debounce: بگذار session آماده شود
      const t = setTimeout(() => { restoreInspectorChatFromDb(false); }, 400);
      return () => clearTimeout(t);
    }
  }, [inspectorSessionId, inspectorChatRestored, activeTab, restoreInspectorChatFromDb]);

  // 🧹 Clear chat (فقط state فرانت — DB دست‌نخورده می‌ماند)
  const clearInspectorChatLocally = useCallback(() => {
    setInspectorChatMessages([]);
    setInspectorChatRestored(false);  // اجازه بده دفعه بعد دوباره از DB بخواند
  }, []);

  // 🔁 Reload from DB (force) — کاربر دستی تاریخچه را از DB می‌کشد
  const reloadInspectorChatFromDb = useCallback(async () => {
    setInspectorChatMessages([]);
    setInspectorChatRestored(false);
    await restoreInspectorChatFromDb(true);
  }, [restoreInspectorChatFromDb]);

  // ===========================================================
  // 🔗 External Projects — اتصال به GitHub/Render خارجی
  // ===========================================================

  const connectExternalGithub = useCallback(async () => {
    if (!externalRepoUrl.trim()) {
      setExternalConnectError('آدرس repo الزامی است');
      return;
    }
    setExternalConnecting(true);
    setExternalConnectError(null);
    try {
      const res = await fetch(`${API_BASE}/api/external-projects/connect/github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: externalRepoUrl.trim(),
          token: externalToken.trim() || null,
          branch: externalBranch.trim() || 'main',
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          setExternalConnectError('توکن لازم است (repo خصوصی) — یک Personal Access Token با scope repo وارد کنید');
        } else {
          setExternalConnectError(data?.detail || 'اتصال ناموفق');
        }
        return;
      }
      // success — extract project info
      const pid = data?.project_id || data?.id || data?.project?.id || '';
      setExternalProjectId(pid);
      setExternalProjectInfo(data?.project || data);
      setExternalConnected(true);
    } catch (e: any) {
      setExternalConnectError(e?.message || 'خطای ناشناخته');
    } finally {
      setExternalConnecting(false);
    }
  }, [externalRepoUrl, externalToken, externalBranch]);

  const loadExternalFiles = useCallback(async () => {
    if (!externalProjectId) return;
    setExternalFilesLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/external-projects/${externalProjectId}/files`);
      const data = await res.json();
      const files = data?.files || data?.items || [];
      setExternalFiles(Array.isArray(files) ? files : []);
    } catch (e) {
      setExternalFiles([]);
    } finally {
      setExternalFilesLoading(false);
    }
  }, [externalProjectId]);

  const loadExternalReadme = useCallback(async () => {
    if (!externalProjectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/external-projects/${externalProjectId}/readme`);
      const data = await res.json();
      setExternalReadme(data?.readme || data?.content || '');
    } catch (e) {
      setExternalReadme('');
    }
  }, [externalProjectId]);

  const loadExternalFileContent = useCallback(async (filePath: string) => {
    if (!externalProjectId || !filePath) return;
    setExternalFileLoading(true);
    setExternalSelectedFile(filePath);
    try {
      const res = await fetch(`${API_BASE}/api/external-projects/${externalProjectId}/file/${encodeURIComponent(filePath)}`);
      const data = await res.json();
      setExternalFileContent(data?.content || data?.file_content || '');
    } catch (e) {
      setExternalFileContent('(خطا در بارگذاری فایل)');
    } finally {
      setExternalFileLoading(false);
    }
  }, [externalProjectId]);

  const analyzeExternalProject = useCallback(async () => {
    if (!externalProjectId) return;
    setExternalAnalyzing(true);
    setExternalAnalysis(null);
    try {
      const res = await fetch(`${API_BASE}/api/external-projects/${externalProjectId}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      setExternalAnalysis(data);
    } catch (e: any) {
      setExternalAnalysis({ success: false, error: e?.message || 'تحلیل ناموفق' });
    } finally {
      setExternalAnalyzing(false);
    }
  }, [externalProjectId]);

  const disconnectExternal = useCallback(async () => {
    if (!externalProjectId) return;
    if (!confirm('قطع اتصال از پروژهٔ خارجی؟ داده‌های local پاک می‌شوند ولی پروژهٔ منبع دست‌نخورده می‌ماند.')) return;
    try {
      await fetch(`${API_BASE}/api/external-projects/${externalProjectId}`, { method: 'DELETE' });
    } catch (e) { /* non-critical */ }
    setExternalConnected(false);
    setExternalProjectId('');
    setExternalProjectInfo(null);
    setExternalFiles([]);
    setExternalSelectedFile(null);
    setExternalFileContent('');
    setExternalReadme('');
    setExternalAnalysis(null);
  }, [externalProjectId]);

  // وقتی تب External روشن می‌شود و قبلاً connect شده، فایل‌ها را load کن
  useEffect(() => {
    if (activeTab === 'external' && externalConnected && externalProjectId && externalFiles.length === 0) {
      loadExternalFiles();
      loadExternalReadme();
    }
  }, [activeTab, externalConnected, externalProjectId, externalFiles.length, loadExternalFiles, loadExternalReadme]);

  // 📋 Build strong external prompt for a prompt-field (client-side)
  // ساختار خروجی هم‌تراز با oversight_strong_prompt است تا کاربر بتواند آن را
  // در ابزار کدنویس خارجی (Cursor/Copilot) paste کند و دقیقاً بداند چه فایل‌هایی
  // باید لمس شوند. بدون نیاز به API call — همه context را از state موجود می‌سازد.
  const buildStrongPromptForField = useCallback((field: any): string => {
    const lines: string[] = [];
    const projectName = project?.name || 'Project';
    const projectDesc = (project as any)?.description || '';
    const technologies: string[] = ((project as any)?.technologies || []) as string[];
    const features: any[] = ((project as any)?.features || []) as any[];
    const memInst: string = ((project as any)?.memory_instructions?.content || '') as string;

    lines.push(`## 🎯 هدف`);
    lines.push(field?.title || 'فیلد بدون عنوان');
    lines.push('');
    lines.push(`## 🧭 هدف اصلی پروژه (از یادداشت کاربر)`);
    lines.push(memInst || projectDesc || '(کاربر یادداشتی ثبت نکرده است)');
    lines.push('');
    if (technologies && technologies.length) {
      lines.push(`## 🧱 پشتهٔ فناوری و معماری`);
      lines.push(`Technologies: ${technologies.slice(0, 12).join(', ')}`);
      if (features && features.length) {
        lines.push('');
        const featTitles = features.slice(0, 6).map((f: any) => typeof f === 'string' ? f : (f?.title || f?.name || JSON.stringify(f).slice(0, 60)));
        lines.push(`Features: ${featTitles.join('؛ ')}`);
      }
      lines.push('');
    }
    lines.push(`## 📍 موقعیت دقیق در پروژه`);
    lines.push(`_(file:line — symbol — snippet — توسط مجری بر اساس Context زیر شناسایی شود)_`);
    lines.push('');
    lines.push(`## 🔍 Context و وضعیت فعلی`);
    lines.push(`Project: \`${projectName}\``);
    if (projectDesc) {
      lines.push('');
      lines.push(`Description: ${projectDesc}`);
    }
    lines.push('');
    lines.push(`### محتوای فیلد:`);
    lines.push('');
    lines.push(field?.content || '(محتوا خالی است)');
    lines.push('');
    if (field?.category) {
      const catLabel = field.category === 'instruction' ? 'دستور' : field.category === 'memory' ? 'حافظه' : 'آموزش';
      lines.push(`> دستهٔ این فیلد: **${catLabel}**`);
      lines.push('');
    }
    lines.push(`## ✅ معیار پذیرش (Acceptance Criteria)`);
    lines.push(`- [ ] نتیجهٔ اعمال این فیلد با مفاد آن مطابقت داشته باشد`);
    lines.push(`- [ ] هیچ تستی fail نمی‌شود (\`npm run test\` / \`pytest\`)`);
    lines.push(`- [ ] linter بدون warning عبور می‌کند`);
    lines.push(`- [ ] type-check موفق است (\`tsc --noEmit\` / \`mypy\`)`);
    lines.push('');
    lines.push(`## 🪜 مراحل اجرایی پیشنهادی`);
    lines.push(`_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_`);
    lines.push('');
    lines.push(`## 📤 خروجی مورد انتظار`);
    lines.push(`تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.`);
    lines.push('');
    lines.push(`## ⚠️ ریسک‌ها و موارد احتیاط`);
    lines.push(`پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.`);
    lines.push('');
    lines.push(`## 🏷 دسته‌بندی`);
    const typeMap: Record<string, string> = { instruction: 'feature_request', memory: 'docs', training: 'docs' };
    lines.push(`- نوع: ${typeMap[field?.category || ''] || 'other'}`);
    lines.push(`- اولویت: ${(field?.priority ?? 0) > 5 ? 'high' : 'medium'}`);
    lines.push(`- تخمین زمان: medium`);
    return lines.join('\n');
  }, [project]);

  const [copyFieldFeedbackId, setCopyFieldFeedbackId] = useState<string | null>(null);
  const copyStrongPromptForField = useCallback(async (field: any) => {
    try {
      // اولویت: اگر backend خود external_prompt را تولید کرده باشد (از طریق
      // build_strong_prompt واقعی با context کامل پروژه)، آن را استفاده کن.
      // در غیر این صورت rollback به client-side render (با context محدودتر).
      const txt: string = (field?.external_prompt && typeof field.external_prompt === 'string' && field.external_prompt.trim().length > 50)
        ? field.external_prompt
        : buildStrongPromptForField(field);
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
      setCopyFieldFeedbackId(field.id);
      setTimeout(() => setCopyFieldFeedbackId(null), 1500);
    } catch (e) {
      alert('کپی ناموفق: ' + (e as any)?.message);
    }
  }, [buildStrongPromptForField]);

  // ===========================================================
  // 📥 Export action timeline + 🔗 Send to Oversight
  // ===========================================================

  // Send to Oversight modal state
  const [showSendToOversightModal, setShowSendToOversightModal] = useState(false);
  const [oversightWatchedList, setOversightWatchedList] = useState<Array<{ id: string; repo_full_name: string; user_notes?: string }>>([]);
  const [sendOversightForm, setSendOversightForm] = useState({
    watched_id: '',
    title: '',
    type: 'bug',
    priority: 'medium',
  });
  const [sendOversightSubmitting, setSendOversightSubmitting] = useState(false);

  // ابزار کمکی: ساختار خروجی timeline
  const buildTimelineSnapshot = useCallback(() => {
    const filters: Record<string, boolean> = inspectorActionFiltersRef.current as Record<string, boolean>;
    return {
      session_id: inspectorSessionId,
      project_id: projectId,
      project_name: project?.name || '',
      started_at:
        inspectorChatMessages.length > 0
          ? (inspectorChatMessages[0].timestamp instanceof Date
              ? inspectorChatMessages[0].timestamp.toISOString()
              : new Date(inspectorChatMessages[0].timestamp).toISOString())
          : null,
      exported_at: new Date().toISOString(),
      total_messages: inspectorChatMessages.length,
      filters_active: Object.keys(filters).filter(k => filters[k]),
      counters: {
        duplicates_dropped: inspectorDuplicatesDroppedCount,
        verify_pending: inspectorVerifyPendingCount,
        console_logs_dropped: consoleLogDroppedCount,
        console_log_cap: consoleLogCap,
      },
      messages: inspectorChatMessages.map((m: any) => ({
        id: m.id,
        db_id: m.db_id || null,
        role: m.role,
        content: m.content,
        timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : new Date(m.timestamp).toISOString(),
        action_type: m.action_type || null,
        backend_verified: m.backend_verified ?? null,
        backend_log_summary: m.backend_log_summary || null,
        verified_by_model: m.verified_by_model || null,
        logs_checked: m.logs_checked ?? null,
        error_logs_count: m.error_logs_count ?? null,
        network_meta: m.network_meta || null,
        model_id: m.model_id || null,
      })),
    };
  }, [inspectorSessionId, projectId, project, inspectorChatMessages, inspectorDuplicatesDroppedCount, inspectorVerifyPendingCount, consoleLogDroppedCount, consoleLogCap]);

  const downloadBlob = (filename: string, content: string, mime: string) => {
    try {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e) {
      console.warn('downloadBlob failed', e);
    }
  };

  const exportInspectorTimelineJSON = useCallback(() => {
    const snap = buildTimelineSnapshot();
    const filename = `inspector-timeline-${(project?.name || 'project').replace(/[^a-zA-Z0-9-_]/g, '_')}-${Date.now()}.json`;
    downloadBlob(filename, JSON.stringify(snap, null, 2), 'application/json');
  }, [buildTimelineSnapshot, project]);

  const exportInspectorTimelineMarkdown = useCallback(() => {
    const snap = buildTimelineSnapshot();
    const lines: string[] = [];
    lines.push(`# 📋 Inspector Timeline — ${snap.project_name || 'Project'}`);
    lines.push('');
    lines.push(`- **Project ID:** \`${snap.project_id}\``);
    lines.push(`- **Session ID:** \`${snap.session_id ?? 'N/A'}\``);
    lines.push(`- **Started at:** ${snap.started_at || 'N/A'}`);
    lines.push(`- **Exported at:** ${snap.exported_at}`);
    lines.push(`- **Total messages:** ${snap.total_messages}`);
    lines.push(`- **Active filters:** ${snap.filters_active.join(', ') || '(none)'}`);
    lines.push(`- **Counters:** duplicates_dropped=${snap.counters.duplicates_dropped}, verify_pending=${snap.counters.verify_pending}, logs_dropped=${snap.counters.console_logs_dropped} (cap=${snap.counters.console_log_cap})`);
    lines.push('');
    lines.push('---');
    lines.push('');
    let lastDate = '';
    for (const m of snap.messages) {
      const d = new Date(m.timestamp);
      const dateStr = d.toISOString().slice(0, 10);
      if (dateStr !== lastDate) {
        lines.push(`## 🗓️ ${dateStr}`);
        lines.push('');
        lastDate = dateStr;
      }
      const time = d.toISOString().slice(11, 19);
      const emoji =
        m.action_type === 'click' ? '🖱️' :
        m.action_type === 'input' ? '⌨️' :
        m.action_type === 'scroll' ? '🔃' :
        m.action_type === 'focus' ? '🎯' :
        m.action_type === 'hover' ? '👆' :
        m.action_type === 'error' || m.action_type === 'console-error' ? '🔴' :
        m.action_type === 'error-overlay' ? '🚨' :
        m.action_type === 'network-request' ? '🌐' :
        m.action_type === 'network-response' ? '✅' :
        m.action_type === 'network-error' ? '🌐❌' :
        m.role === 'user' ? '👤' :
        m.role === 'assistant' ? '🤖' :
        m.role === 'system' ? '⚙️' :
        '•';
      lines.push(`### ${emoji} ${time} — ${m.role}${m.action_type ? ` (\`${m.action_type}\`)` : ''}`);
      lines.push('');
      lines.push(`> ${m.content.replace(/\n/g, '\n> ')}`);
      lines.push('');
      const meta: string[] = [];
      if (m.backend_verified !== null) meta.push(`verified: ${m.backend_verified ? '✅' : '❌'}`);
      if (m.verified_by_model) meta.push(`model: \`${m.verified_by_model}\``);
      if (m.logs_checked !== null) meta.push(`logs_checked: ${m.logs_checked}`);
      if (m.error_logs_count !== null && m.error_logs_count !== 0) meta.push(`errors: ${m.error_logs_count}`);
      if (m.network_meta) {
        const nm = m.network_meta;
        meta.push(`network: ${nm.method || ''} ${nm.url || ''} → ${nm.status || ''} (${nm.durationMs || 0}ms)`);
      }
      if (meta.length) {
        lines.push(`<sub>${meta.join(' · ')}</sub>`);
        lines.push('');
      }
      if (m.backend_log_summary) {
        lines.push(`**Backend log summary:**`);
        lines.push('```');
        lines.push(m.backend_log_summary);
        lines.push('```');
        lines.push('');
      }
    }
    const filename = `inspector-timeline-${(project?.name || 'project').replace(/[^a-zA-Z0-9-_]/g, '_')}-${Date.now()}.md`;
    downloadBlob(filename, lines.join('\n'), 'text/markdown');
  }, [buildTimelineSnapshot, project]);

  // 🔗 Send to Oversight — یک تسک جدید در سیستم نظارت می‌سازد
  const openSendToOversightModal = useCallback(async () => {
    try {
      // pre-load watched list
      const res = await fetch(`${API_BASE}/api/oversight/watched`);
      const data = await res.json();
      const items = (data && data.items) ? data.items : [];
      setOversightWatchedList(items);
      // default title از خطای آخر یا "گزارش مانیتورینگ"
      const lastError = [...inspectorChatMessages].reverse().find((m: any) =>
        m.action_type === 'error' || m.action_type === 'console-error' || m.action_type === 'network-error'
      ) as any;
      setSendOversightForm({
        watched_id: items[0]?.id || '',
        title: lastError ? `بررسی: ${(lastError.content || '').slice(0, 80)}` : `گزارش Inspector — ${project?.name || 'پروژه'}`,
        type: lastError ? 'bug' : 'other',
        priority: lastError ? 'high' : 'medium',
      });
      setShowSendToOversightModal(true);
    } catch (e: any) {
      alert('خطا در بارگذاری watched projects: ' + (e?.message || ''));
    }
  }, [inspectorChatMessages, project]);

  const submitSendToOversight = useCallback(async () => {
    if (!sendOversightForm.watched_id) {
      alert('لطفاً یک پروژهٔ watched انتخاب کنید');
      return;
    }
    setSendOversightSubmitting(true);
    try {
      const snap = buildTimelineSnapshot();
      const watched = oversightWatchedList.find(w => w.id === sendOversightForm.watched_id);

      // استخراج فایل‌های هدف از URL های network requests (مسیر بدون پارامتر)
      const targetFilesSet = new Set<string>();
      for (const m of snap.messages) {
        if (m.network_meta && m.network_meta.url) {
          try {
            const u = new URL(m.network_meta.url, 'http://x');
            if (u.pathname && u.pathname !== '/') targetFilesSet.add(u.pathname);
          } catch (_) {}
        }
      }
      const targetFiles = Array.from(targetFilesSet).slice(0, 10);

      // ساخت Markdown خلاصه به‌عنوان prompt
      const errorMsgs = snap.messages.filter((m: any) =>
        m.action_type === 'error' || m.action_type === 'console-error' || m.action_type === 'network-error'
      );
      const promptParts: string[] = [];
      promptParts.push(`## 🎯 هدف`);
      promptParts.push(sendOversightForm.title);
      promptParts.push('');
      promptParts.push(`## 🧭 هدف اصلی پروژه (از یادداشت کاربر)`);
      promptParts.push(watched?.user_notes || '(کاربر یادداشتی ثبت نکرده است)');
      promptParts.push('');
      promptParts.push(`## 📍 موقعیت‌های مرتبط`);
      if (targetFiles.length) {
        targetFiles.forEach(f => promptParts.push(`- \`${f}\``));
      } else {
        promptParts.push('_(هیچ مسیر network مشخصی شناسایی نشد)_');
      }
      promptParts.push('');
      promptParts.push(`## 🔍 Context — خلاصهٔ Inspector Timeline`);
      promptParts.push(`Project: \`${snap.project_name}\` (ID: \`${snap.project_id}\`)`);
      promptParts.push(`Session: \`${snap.session_id ?? 'N/A'}\` · Total messages: ${snap.total_messages}`);
      promptParts.push(`Exported at: ${snap.exported_at}`);
      promptParts.push('');
      if (errorMsgs.length > 0) {
        promptParts.push(`### 🔴 خطاهای دیده‌شده (${errorMsgs.length})`);
        for (const e of errorMsgs.slice(-15)) {
          const t = new Date(e.timestamp).toISOString().slice(11, 19);
          promptParts.push(`- [${t}] **${e.action_type}**: ${e.content.slice(0, 200)}`);
          if (e.backend_log_summary) {
            promptParts.push(`  - log summary: ${e.backend_log_summary.slice(0, 200)}`);
          }
        }
        promptParts.push('');
      }
      const lastActions = snap.messages.filter((m: any) => m.role === 'action').slice(-20);
      if (lastActions.length > 0) {
        promptParts.push(`### 🪜 آخرین ${lastActions.length} اکشن کاربر`);
        for (const a of lastActions) {
          const t = new Date(a.timestamp).toISOString().slice(11, 19);
          promptParts.push(`- [${t}] ${a.action_type || 'event'}: ${a.content.slice(0, 150)}`);
        }
        promptParts.push('');
      }
      promptParts.push(`## ✅ معیار پذیرش`);
      promptParts.push('- [ ] خطاهای ذکر شده دیگر در Inspector تکرار نمی‌شوند');
      promptParts.push('- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)');
      promptParts.push('- [ ] linter بدون warning عبور می‌کند');
      promptParts.push('');
      promptParts.push(`## 🏷 دسته‌بندی`);
      promptParts.push(`- نوع: ${sendOversightForm.type}`);
      promptParts.push(`- اولویت: ${sendOversightForm.priority}`);

      const promptText = promptParts.join('\n');

      const body = {
        watched_id: sendOversightForm.watched_id,
        project_full_name: watched?.repo_full_name || '',
        title: sendOversightForm.title,
        prompt: promptText,
        raw_idea: 'Generated from Inspector timeline',
        type: sendOversightForm.type,
        priority: sendOversightForm.priority,
        status: 'pending',
        source: 'inspector',
      };
      const res = await fetch(`${API_BASE}/api/oversight/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok || (data && data.detail)) {
        throw new Error(data?.detail || 'ساخت تسک نظارت ناموفق بود');
      }
      setShowSendToOversightModal(false);
      // toast ساده — alert موقتی
      alert('✅ تسک با موفقیت در سیستم نظارت ساخته شد');
    } catch (e: any) {
      alert('خطا: ' + (e?.message || 'ناشناخته'));
    } finally {
      setSendOversightSubmitting(false);
    }
  }, [sendOversightForm, oversightWatchedList, buildTimelineSnapshot]);

  // 🌉 تابع مشترک برای پردازش event های Bridge (postMessage و WebSocket)
  const actionLabelsRef = useRef<Record<string, string>>({
    'click': 'کلیک کردی',
    'scroll': 'اسکرول کردی',
    'input': 'تایپ کردی',
    'focus': 'فوکوس کردی',
    'hover': 'موس بردی روی',
    'error': '🔴 خطای JS',
    'console-error': '🔴 console.error',
    'error-overlay': '🔴 لایه خطا شناسایی شد',
    'network-request': '🌐 درخواست شبکه',
    'network-response': '✅ پاسخ شبکه',
    'network-error': '🔴 خطای شبکه',
  });

  const handleBridgeEvent = useCallback((data: any, sourceLabel: string) => {
    const { action, target, elementInfo, level, source } = data;

    // 🛡️ DEDUP — جلوگیری از log شدن دوبارهٔ یک event که از هر دو کانال
    // (postMessage و WebSocket) رسیده است. کلید بر اساس نوع+timestamp+محتوا.
    // window پیش‌فرض ۲ ثانیه — اگر در این بازه همان کلید دیده شد، drop می‌شود.
    try {
      const evtTs = data.timestamp || Date.now();
      const digestSrc = `${target || ''}|${elementInfo || ''}|${level || ''}`.slice(0, 200);
      // برای network events، reqId را در کلید قرار می‌دهیم تا response/error هر
      // request منحصر به فرد بماند حتی اگر URL یکسان باشد
      const reqIdPart = (data.networkMeta && data.networkMeta.reqId) ? `:${data.networkMeta.reqId}` : '';
      const dedupKey = `${action}:${evtTs}:${digestSrc}${reqIdPart}`;
      const seen = inspectorSeenEventsRef.current;
      const lastSeen = seen.get(dedupKey);
      const now = Date.now();
      if (lastSeen !== undefined && now - lastSeen < INSPECTOR_DEDUP_WINDOW_MS) {
        // این رویداد تکراری است — drop کن و شمارنده را بالا ببر
        setInspectorDuplicatesDroppedCount(c => c + 1);
        return;
      }
      seen.set(dedupKey, now);
      // محدودیت اندازهٔ map (در صورت رشد بیش از حد — معمولاً cleanup interval کافی است)
      if (seen.size > 5000) {
        const cutoff = now - INSPECTOR_DEDUP_WINDOW_MS * 5;
        const toDelete: string[] = [];
        seen.forEach((t, k) => { if (t < cutoff) toDelete.push(k); });
        toDelete.forEach(k => seen.delete(k));
      }
    } catch (e) {
      // dedup نباید critical باشد — اگر چیزی شکست، event را مثل قبل پردازش کن
    }

    // 📋 ذخیره لاگ‌های کنسول (تفکیک شده) — با cap قابل تنظیم + شمارش drop ها
    if (action === 'console-log' || action === 'console-error') {
      setImportedProjectConsoleLogs(prev => {
        const newLog = {
          id: `clog_${sourceLabel}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
          level: level || (action === 'console-error' ? 'error' : 'log'),
          message: elementInfo || '',
          timestamp: data.timestamp || Date.now(),
          source: source || 'imported-project',
        };
        const cap = consoleLogCapRef.current || 2000;
        const merged = [...prev, newLog];
        if (merged.length > cap) {
          // logها silently drop می‌شوند ولی شمارنده را بالا می‌بریم تا کاربر مطلع شود
          setConsoleLogDroppedCount(c => c + (merged.length - cap));
          return merged.slice(-cap);
        }
        return merged;
      });
      if (action === 'console-log') return;
    }

    // 🔍 لایه خطا (Error Overlay) شناسایی شده
    if (action === 'error-overlay') {
      setImportedProjectConsoleLogs(prev => {
        const cap = consoleLogCapRef.current || 2000;
        const merged = [...prev, {
          id: `overlay_${sourceLabel}_${Date.now()}`,
          level: 'error',
          message: `[Error Overlay] ${elementInfo || ''}`,
          timestamp: data.timestamp || Date.now(),
          source: 'imported-project',
        }];
        if (merged.length > cap) {
          setConsoleLogDroppedCount(c => c + (merged.length - cap));
          return merged.slice(-cap);
        }
        return merged;
      });
    }

    // 🔧 فیلتر اکشن: اگر این نوع غیرفعال باشد، در چت ثبت نشود
    if (inspectorActionFiltersRef.current[action] === false) return;

    const actionLabel = actionLabelsRef.current[action] || action;
    const targetInfo = elementInfo || target || 'عنصر ناشناخته';

    // اضافه کردن به پیام‌های دائمی چت
    const msgId = `action_${sourceLabel}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    // برای network events، content را بدون «روی» می‌سازیم — فقط label + targetInfo
    const isNetworkEvt = action === 'network-request' || action === 'network-response' || action === 'network-error';
    setInspectorChatMessages(prev => [...prev, {
      id: msgId,
      role: 'action' as const,
      content: isNetworkEvt ? `${actionLabel}: ${targetInfo}` : `${actionLabel} روی ${targetInfo}`,
      timestamp: new Date(),
      action_type: action as any,
      backend_verified: null,
      network_meta: data.networkMeta || null,
    }]);

    // ذخیره در DB و verify (از ref استفاده می‌کنیم چون closure ممکنه قدیمی باشه)
    const currentSessionId = inspectorSessionIdRef.current;
    if (currentSessionId) {
      (async () => {
        try {
          const saveRes = await fetch(`${API_BASE}/api/render/inspector/session/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: currentSessionId,
              role: 'action',
              content: isNetworkEvt ? `${actionLabel}: ${targetInfo}` : `${actionLabel} روی ${targetInfo}`,
              action_type: action,
              // 🌐 network_meta را داخل extra_data می‌گذاریم تا توسط
              // backend واقعاً persist شود (extra_data یک JSON column است)
              extra_data: data.networkMeta ? { network_meta: data.networkMeta } : undefined,
            })
          });
          const saveData = await saveRes.json();
          if (saveData.success && saveData.message?.id) {
            const dbId = saveData.message.id;
            setInspectorChatMessages(prev =>
              prev.map(m => m.id === msgId ? { ...m, db_id: dbId } : m)
            );
            // 🔁 verify با backoff نمایی + jitter (تا ۵ تلاش) + abort روی خاموش‌شدن
            // -----------------------------------------------------------------
            // STALE-CLOSURE FIX: قبل از await یک snapshot logها می‌گیریم و
            // بعد از await هم snapshot دوم — union دو نسخه به backend می‌رود
            // تا اگر در حین await لاگ‌های جدیدی از bridge رسیده‌اند گم نشوند.
            // (دلیل: importedConsoleLogsRef.current ممکن است در بازهٔ async
            // به‌روز شده باشد، ولی نسخهٔ closure قدیمی شود.)
            // -----------------------------------------------------------------
            const actionTimestamp = Date.now();
            setInspectorVerifyPendingCount(c => c + 1);
            let pendingCounted = true;

            const doVerify = async (attempt: number = 1) => {
              // اگر کاربر inspector را خاموش کرد، تلاش‌های در جریان را abort کن
              if (!inspectorPowerOnRef.current) {
                if (pendingCounted) {
                  setInspectorVerifyPendingCount(c => Math.max(0, c - 1));
                  pendingCounted = false;
                }
                return;
              }
              try {
                const pId = params?.id as string;

                // snapshot قبل از await (نسخهٔ اول)
                const snapBefore = importedConsoleLogsRef.current
                  .filter(l => Math.abs(l.timestamp - actionTimestamp) < 5000)
                  .map(l => ({ level: l.level, message: l.message, timestamp: l.timestamp, _id: l.id }));

                const verifyRes = await fetch(
                  `${API_BASE}/api/render/inspector/message/${dbId}/verify?project_id=${pId}&force=${attempt > 1 ? 'true' : 'false'}`,
                  {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      // snapshot دوم بعد از await (در همین تابع، قبل از send)
                      // — union دو نسخه با dedup روی timestamp+message
                      console_logs: (() => {
                        const snapAfter = importedConsoleLogsRef.current
                          .filter(l => Math.abs(l.timestamp - actionTimestamp) < 5000)
                          .map(l => ({ level: l.level, message: l.message, timestamp: l.timestamp, _id: l.id }));
                        const seenKeys = new Set<string>();
                        const out: Array<{level: string; message: string; timestamp: number}> = [];
                        for (const l of [...snapBefore, ...snapAfter]) {
                          const k = `${l.timestamp}|${l.message}`;
                          if (seenKeys.has(k)) continue;
                          seenKeys.add(k);
                          out.push({ level: l.level, message: l.message, timestamp: l.timestamp });
                        }
                        return out.slice(-30);
                      })(),
                    }),
                  }
                );
                const verifyData = await verifyRes.json();
                if (verifyData.success) {
                  setInspectorChatMessages(prev =>
                    prev.map(m => m.id === msgId ? {
                      ...m,
                      backend_verified: verifyData.verified,
                      backend_log_summary: verifyData.summary,
                      verified_by_model: verifyData.model_used,
                      logs_checked: verifyData.logs_checked,
                      error_logs_count: verifyData.error_logs_count,
                      checked_logs: verifyData.checked_logs,
                    } : m)
                  );
                  // اگر هنوز pending یا logs_checked=0 → تلاش بعدی با backoff نمایی
                  if (attempt < 5 && (verifyData.logs_checked === 0 || verifyData.pending)) {
                    // base 2000ms × 2^attempt  →  2,4,8,16,32 ثانیه + jitter 0..400ms
                    const delay = 2000 * Math.pow(2, attempt) + Math.floor(Math.random() * 400);
                    setTimeout(() => doVerify(attempt + 1), delay);
                  } else {
                    if (pendingCounted) {
                      setInspectorVerifyPendingCount(c => Math.max(0, c - 1));
                      pendingCounted = false;
                    }
                  }
                } else {
                  if (pendingCounted) {
                    setInspectorVerifyPendingCount(c => Math.max(0, c - 1));
                    pendingCounted = false;
                  }
                }
              } catch (err) {
                // verify failed - retry با backoff
                if (attempt < 5 && inspectorPowerOnRef.current) {
                  const delay = 2000 * Math.pow(2, attempt) + Math.floor(Math.random() * 400);
                  setTimeout(() => doVerify(attempt + 1), delay);
                } else {
                  if (pendingCounted) {
                    setInspectorVerifyPendingCount(c => Math.max(0, c - 1));
                    pendingCounted = false;
                  }
                }
              }
            };
            // اولین تلاش بعد از ۲ ثانیه (به جای ۵) چون backoff خودش فاصله ایجاد می‌کند
            setTimeout(() => doVerify(1), 2000);
          }
        } catch (err) { /* save message failed - non-critical */ }
      })();
    }
  }, [params]);

  // پیام موقتی Bridge (اتصال/قطع) با auto-remove
  const showBridgeTransient = useCallback((content: string, sourceLabel: string) => {
    const id = `bridge_${sourceLabel}_${Date.now()}`;
    setInspectorTransientMessages(prev => [...prev, {
      id,
      content,
      type: 'info' as const,
      source: sourceLabel,
      timestamp: new Date(),
      fadeOut: false
    }]);
    setTimeout(() => {
      setInspectorTransientMessages(prev => prev.filter(m => m.id !== id));
    }, 4000);
  }, []);

  // 🆕 Message Listener برای دریافت event ها از Bridge Script داخل iframe (postMessage fallback)
  useEffect(() => {
    const handleBridgeMessage = (event: MessageEvent) => {
      if (event.data?.type === 'inspector-bridge-event') {
        handleBridgeEvent(event.data, 'pm');
      }
      if (event.data?.type === 'inspector-bridge-ready') {
        showBridgeTransient('🔗 اتصال postMessage به پروژه برقرار شد', 'Bridge');
        if (event.data.pageUrl) setInspectorFrontendUrl(event.data.pageUrl);
      }
      // 🆕 دریافت تغییر URL از Bridge Script (ناوبری کاربر در iframe)
      if (event.data?.type === 'inspector-url-changed') {
        if (event.data.pageUrl) setInspectorFrontendUrl(event.data.pageUrl);
      }
      // 🔀 دریافت URL واقعی از اسکریپت تزریقی proxy (same-origin)
      if (event.data?.type === 'proxy-url-change' && event.data.path) {
        const actual = _proxyToActual(event.data.path);
        if (actual) setInspectorFrontendUrl(actual);
      }
    };

    window.addEventListener('message', handleBridgeMessage);
    return () => window.removeEventListener('message', handleBridgeMessage);
  }, [handleBridgeEvent, showBridgeTransient]);

  // 🌐 WebSocket Bridge Connection - ارتباط مستقیم با Bridge Script
  useEffect(() => {
    if (!inspectorPowerOn || !projectId || activeTab !== 'inspector') {
      // قطع اتصال وقتی inspector خاموشه
      if (bridgeWsRef.current) {
        bridgeWsRef.current.close();
        bridgeWsRef.current = null;
        setBridgeWsConnected(false);
        setBridgePeerConnected(false);
      }
      return;
    }

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    let isCancelled = false;

    // 🛡️ Cleanup interval: هر ۳۰ ثانیه entry های قدیمی dedup map را پاک می‌کند
    const dedupCleanupTimer: ReturnType<typeof setInterval> = setInterval(() => {
      try {
        const seen = inspectorSeenEventsRef.current;
        const cutoff = Date.now() - INSPECTOR_DEDUP_WINDOW_MS * 5; // ۱۰ ثانیه
        const toDelete: string[] = [];
        seen.forEach((t, k) => { if (t < cutoff) toDelete.push(k); });
        toDelete.forEach(k => seen.delete(k));
      } catch (e) { /* non-critical */ }
    }, 30000);

    const connectBridgeWs = () => {
      if (isCancelled) return;

      // ساخت WebSocket URL از API_BASE
      const wsBase = API_BASE.replace('https://', 'wss://').replace('http://', 'ws://');
      const wsUrl = `${wsBase}/api/render/ws/bridge/${projectId}`;

      console.log('🌐 Bridge WS: Connecting to', wsUrl);

      try {
        ws = new WebSocket(wsUrl);
        bridgeWsRef.current = ws;

        ws.onopen = () => {
          if (isCancelled) { ws?.close(); return; }
          console.log('🌐 Bridge WS: Connected, registering as inspector');
          ws?.send(JSON.stringify({ type: 'register', role: 'inspector' }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'registered') {
              setBridgeWsConnected(true);
              console.log('🌐 Bridge WS: Registered as inspector');
              return;
            }

            if (data.type === 'pong') return;

            if (data.type === 'peer_connected' && data.peer_role === 'bridge') {
              setBridgePeerConnected(true);
              console.log('🌐 Bridge WS: Bridge peer connected');
              // اطلاع در چت
              const id = `ws_ready_${Date.now()}`;
              setInspectorTransientMessages(prev => [...prev, {
                id,
                content: '🌐 اتصال WebSocket به پروژه برقرار شد',
                type: 'info' as const,
                source: 'WebSocket Bridge',
                timestamp: new Date(),
                fadeOut: false
              }]);
              setTimeout(() => {
                setInspectorTransientMessages(prev => prev.filter(m => m.id !== id));
              }, 4000);
              return;
            }

            if (data.type === 'peer_disconnected' && data.peer_role === 'bridge') {
              setBridgePeerConnected(false);
              console.log('🌐 Bridge WS: Bridge peer disconnected');
              return;
            }

            // پردازش event های Bridge (relay شده از طریق backend) - استفاده از handler مشترک
            if (data.type === 'inspector-bridge-event') {
              if (data.action === 'elements-list') {
                // لیست المان‌ها - پردازش جداگانه
                return;
              }
              handleBridgeEvent(data, 'ws');
            }

            // پیام آماده بودن bridge
            if (data.type === 'inspector-bridge-ready') {
              setBridgePeerConnected(true);
              showBridgeTransient('🌐 Bridge Script از طریق WebSocket متصل شد', 'WebSocket Bridge');
              if (data.pageUrl) setInspectorFrontendUrl(data.pageUrl);
            }
            // 🆕 دریافت تغییر URL از Bridge (WebSocket)
            if (data.type === 'inspector-url-changed' || (data.type === 'inspector-bridge-event' && data.action === 'url-changed')) {
              if (data.pageUrl) setInspectorFrontendUrl(data.pageUrl);
            }

          } catch (e) {
            console.warn('🌐 Bridge WS: Parse error', e);
          }
        };

        ws.onclose = () => {
          setBridgeWsConnected(false);
          setBridgePeerConnected(false);
          bridgeWsRef.current = null;
          if (!isCancelled) {
            console.log('🌐 Bridge WS: Disconnected, reconnecting in 3s...');
            reconnectTimer = setTimeout(connectBridgeWs, 3000);
          }
        };

        ws.onerror = (e) => {
          console.warn('🌐 Bridge WS: Error', e);
        };

        // Heartbeat هر 25 ثانیه
        heartbeatTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            try { ws.send(JSON.stringify({ type: 'ping' })); } catch(e) {}
          }
        }, 25000);

      } catch (e) {
        console.warn('🌐 Bridge WS: Failed to connect', e);
        if (!isCancelled) {
          reconnectTimer = setTimeout(connectBridgeWs, 3000);
        }
      }
    };

    connectBridgeWs();

    return () => {
      isCancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      if (dedupCleanupTimer) clearInterval(dedupCleanupTimer);
      if (ws) {
        try { ws.close(); } catch(e) {}
      }
      bridgeWsRef.current = null;
      setBridgeWsConnected(false);
      setBridgePeerConnected(false);
    };
  }, [inspectorPowerOn, projectId, activeTab, handleBridgeEvent, showBridgeTransient]);

  // 🌉 بررسی وضعیت Bridge وقتی Inspector روشن می‌شود
  useEffect(() => {
    if (inspectorPowerOn && projectId && activeTab === 'inspector') {
      checkBridgeStatus();
    }
  }, [inspectorPowerOn, projectId, activeTab]);

  // 📋 بارگذاری فیلدهای دستور/حافظه/آموزش وقتی Inspector فعال می‌شود
  useEffect(() => {
    if (projectId && activeTab === 'inspector') {
      loadPromptFields();
    }
  }, [projectId, activeTab]);

  // 🌐 ارسال دستور به Bridge از طریق WebSocket
  const sendBridgeCommand = (command: string, data: Record<string, any> = {}) => {
    if (bridgeWsRef.current?.readyState === WebSocket.OPEN) {
      bridgeWsRef.current.send(JSON.stringify({
        type: 'command',
        command,
        ...data
      }));
      return true;
    }
    return false;
  };

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

  // 📋 دستورات عمومی سیستم (همیشه فعال در پرامپت مدل‌ها)
  const loadGeneralInstructions = async () => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/general-instructions/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.instructions) {
          setGeneralInstructions(data.instructions);
        }
      }
    } catch (e) {
      console.error('Error loading general instructions:', e);
    }
  };

  // 📸 پرامپت بازرس بصری (از منبع واحد بکند — خودکار همگام)
  const loadVisualDebugPrompt = async () => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/visual-debug-prompt/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setVisualDebugPromptData({
            vd: data.visual_debug_instructions || [],
            gen: data.general_instructions || []
          });
        }
      }
    } catch (e) {
      console.error('Error loading visual debug prompt:', e);
    }
  };

  // 📋 Prompt Field Functions - مدیریت فیلدهای دستورات، حافظه و آموزش
  const loadPromptFields = async () => {
    if (!projectId) return;
    setPromptFieldsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/prompt-fields/${projectId}`);
      if (!res.ok) {
        console.error('Error loading prompt fields: HTTP', res.status);
        setPromptFieldsLoading(false);
        return;
      }
      const data = await res.json();
      if (data.success) {
        if (data.fields && data.fields.length > 0) {
          setPromptFields(data.fields);
        } else {
          // فیلدها خالی — مقداردهی اولیه از اطلاعات پروژه
          try {
            const initRes = await fetch(`${API_BASE}/api/render/inspector/prompt-fields/init-defaults/${projectId}`, { method: 'POST' });
            const initData = await initRes.json();
            if (initData.success && initData.fields) {
              setPromptFields(initData.fields);
            }
          } catch (initErr) {
            console.error('Error initializing default prompt fields:', initErr);
          }
        }
      }
    } catch (e) {
      console.error('Error loading prompt fields:', e);
    } finally {
      setPromptFieldsLoading(false);
    }
  };

  const createPromptField = async () => {
    if (!projectId || !promptFieldNewData.title.trim() || !promptFieldNewData.content.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/prompt-fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          category: promptFieldNewData.category,
          title: promptFieldNewData.title,
          content: promptFieldNewData.content,
          priority: promptFieldNewData.priority,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setPromptFields(prev => [data.field, ...prev]);
        setPromptFieldAdding(false);
        setPromptFieldNewData({title: '', content: '', category: 'instruction', priority: 0});
      }
    } catch (e) {
      console.error('Error creating prompt field:', e);
    }
  };

  const updatePromptField = async (fieldId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/prompt-fields/${fieldId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(promptFieldEditData),
      });
      const data = await res.json();
      if (data.success) {
        setPromptFields(prev => prev.map(f => f.id === fieldId ? data.field : f));
        setPromptFieldEditing(null);
      }
    } catch (e) {
      console.error('Error updating prompt field:', e);
    }
  };

  const deletePromptField = async (fieldId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/prompt-fields/${fieldId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        setPromptFields(prev => prev.filter(f => f.id !== fieldId));
      }
    } catch (e) {
      console.error('Error deleting prompt field:', e);
    }
  };

  const togglePromptFieldActive = async (fieldId: string, currentActive: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/prompt-fields/${fieldId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentActive }),
      });
      const data = await res.json();
      if (data.success) {
        setPromptFields(prev => prev.map(f => f.id === fieldId ? data.field : f));
      }
    } catch (e) {
      console.error('Error toggling prompt field:', e);
    }
  };

  const testPromptField = async (fieldId: string) => {
    setPromptFieldTesting(fieldId);
    setPromptFieldTestResult(null);
    try {
      const modelId = inspectorSelectedModels[0] || 'gemini-2.0-flash';
      const res = await fetch(`${API_BASE}/api/render/inspector/prompt-fields/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_id: fieldId, model_id: modelId }),
      });
      const data = await res.json();
      if (data.success || data.test_passed !== undefined) {
        setPromptFieldTestResult({
          field_id: fieldId,
          passed: data.test_passed,
          response: data.response || data.error || '',
          model_id: data.model_id || modelId,
        });
        // بروزرسانی فیلد در لیست
        if (data.field) {
          setPromptFields(prev => prev.map(f => f.id === fieldId ? data.field : f));
        }
      }
    } catch (e) {
      console.error('Error testing prompt field:', e);
      setPromptFieldTestResult({
        field_id: fieldId,
        passed: false,
        response: 'خطا در ارتباط با سرور',
        model_id: '',
      });
    } finally {
      setPromptFieldTesting(null);
    }
  };

  // 🔍 Inspector Functions - بازرس ویژه
  const loadInspectorServices = async (refresh: boolean = false) => {
    setInspectorLoading(true);
    setInspectorError(null);
    setInspectorIframeLoaded(false);
    setInspectorIframeError(false);
    try {
      // اول سرویس‌ها رو از Render API رفرش کن (اگر خواسته شده)
      if (refresh) {
        try {
          await fetch(`${API_BASE}/api/render/services?refresh=true`);
          console.log('🔄 Services refreshed from Render API');
        } catch (e) { console.warn('Service refresh failed:', e); }
      }

      const res = await fetch(`${API_BASE}/api/render/services/by-project/${projectId}`);
      const data = await res.json();

      if (data.success) {
        setInspectorServices(data.services || []);

        if (data.services?.length === 0) {
          setInspectorError(data.message || 'هیچ سرویسی یافت نشد');
        } else {
          // شروع fetch لاگ‌ها برای سرویس‌های این پروژه
          for (const svc of (data.services || [])) {
            fetch(`${API_BASE}/api/render/logs/fetch?service_id=${svc.id}`, { method: 'POST' })
              .then(() => console.log(`📋 Fetched logs for ${svc.name}`))
              .catch(err => console.warn(`Log fetch failed for ${svc.name}:`, err));
          }

          if (data.frontend_url) {
            console.log('🔍 Checking frontend URL accessibility:', data.frontend_url);
            try {
              await fetch(data.frontend_url, { method: 'HEAD', mode: 'no-cors' });
              console.log('✅ Frontend URL accessible');
            } catch (healthErr) {
              console.warn('⚠️ Frontend URL may be unreachable:', healthErr);
            }
            setInspectorFrontendUrl(data.frontend_url);
            setInspectorBaseUrl(data.frontend_url); // ذخیره URL پایه برای تبدیل proxy↔actual
            // 🔀 src iframe — مسیر نسبی (same-origin از طریق Next.js rewrite)
            try {
              const _u = new URL(data.frontend_url);
              setInspectorIframeSrc(`/api/render/inspector/proxy/${projectId}${_u.pathname}${_u.search}${_u.hash}`);
            } catch {
              setInspectorIframeSrc(`/api/render/inspector/proxy/${projectId}/`);
            }
          }
        }
      } else {
        setInspectorError(data.error || 'خطا در دریافت سرویس‌ها');
      }
    } catch (err) {
      setInspectorError('خطا در اتصال به سرور');
    } finally {
      setInspectorLoading(false);
    }
  };

  const loadInspectorLogs = async () => {
    try {
      // دریافت لاگ‌های بک‌اند (شامل سرویس‌های یکپارچه)
      const backendServiceIds = inspectorServices
        .filter(s => s.role === 'backend' || s.role === 'unified' || !s.role)
        .map(s => s.id);

      if (backendServiceIds.length === 0) return;

      // 🔴 ابتدا لاگ‌های جدید رو از Render API بگیر و در DB ذخیره کن
      try {
        await Promise.all(backendServiceIds.map(id =>
          fetch(`${API_BASE}/api/render/logs/fetch?service_id=${id}&limit=50`, { method: 'POST' })
            .catch(() => null)
        ));
      } catch {}

      // سپس از DB بخون
      const params = new URLSearchParams();
      backendServiceIds.forEach(id => params.append('service_ids', id));
      params.append('minutes', '30');
      params.append('limit', '50');

      const res = await fetch(`${API_BASE}/api/render/logs?${params}`);
      const data = await res.json();

      if (data.success && data.logs) {
        setInspectorBackendLogs(data.logs);
      }
    } catch (err) {
      console.error('Error loading inspector logs:', err);
    }
  };

  const toggleInspectorPower = async () => {
    if (inspectorPowerOn) {
      // خاموش کردن
      setInspectorPowerOn(false);
      setInspectorFrontendUrl(null);
      setInspectorBaseUrl(null);
      setInspectorIframeSrc('');
      setInspectorIframeLoaded(false);
      setInspectorIframeError(false);
      setInspectorBackendLogs([]);
      setInspectorServices([]);
    } else {
      // روشن کردن - اول سشن رو بساز، بعد power رو روشن کن
      await initInspectorSession();
      setInspectorPowerOn(true);
      // رفرش سرویس‌ها از Render API (نه cache)
      await loadInspectorServices(true);
      await loadInspectorModels();
    }
  };

  // 📋 ایجاد یا بارگذاری سشن بازرسی
  const initInspectorSession = async () => {
    try {
      // ایجاد یا دریافت سشن فعال
      const res = await fetch(`${API_BASE}/api/render/inspector/session/create?project_id=${projectId}`, {
        method: 'POST',
      });
      const data = await res.json();

      if (data.success && data.session) {
        setInspectorSessionId(data.session.id);
        inspectorSessionIdRef.current = data.session.id;

        // بارگذاری پیام‌های قبلی سشن
        const msgRes = await fetch(`${API_BASE}/api/render/inspector/session/${data.session.id}/messages`);
        const msgData = await msgRes.json();

        if (msgData.success && msgData.messages) {
          const loadedMessages = msgData.messages.map((m: any) => ({
            id: `db_${m.id}`,
            db_id: m.id,
            role: m.role,
            content: m.content,
            action_type: m.action_type,
            model_id: m.model_id,
            tokens_used: m.tokens_used,
            timestamp: new Date(m.timestamp),
            backend_verified: m.backend_verified,
            backend_log_summary: m.backend_log_summary,
            verified_by_model: m.verified_by_model,
            logs_checked: m.logs_checked,
            error_logs_count: m.error_logs_count,
            // بازیابی فیلدهای extra_data (action_plan, visual_debug_packs, enhanced_prompt, ...)
            ...(m.action_plan ? { action_plan: m.action_plan } : {}),
            ...(m.visual_debug_packs ? { visual_debug_packs: m.visual_debug_packs } : {}),
            ...(m.enhanced_prompt ? { enhanced_prompt: m.enhanced_prompt } : {}),
            ...(m.original_prompt ? { original_prompt: m.original_prompt } : {}),
            ...(m.is_visual_debug_report ? { is_visual_debug_report: true } : {}),
            ...(m.is_reanalysis_report ? { is_reanalysis_report: true } : {}),
            ...(m.original_user_description ? { original_user_description: m.original_user_description } : {}),
            ...(m.vision_model ? { vision_model: m.vision_model } : {}),
            ...(m.files_were_read !== undefined ? { files_were_read: m.files_were_read } : {}),
            ...(m.reply_to_id ? { reply_to_id: m.reply_to_id, reply_to_content: m.reply_to_content } : {}),
          }));
          setInspectorChatMessages(loadedMessages);
        }

        console.log('📋 Inspector session:', data.existing ? 'loaded' : 'created', data.session.id);
      }

      // بارگذاری سشن‌های آرشیو شده
      const archiveRes = await fetch(`${API_BASE}/api/render/inspector/sessions/${projectId}?status=archived`);
      const archiveData = await archiveRes.json();
      if (archiveData.success) {
        setInspectorArchivedSessions(archiveData.sessions || []);
      }
    } catch (err) {
      console.error('Error initializing inspector session:', err);
    }
  };

  // آرشیو کردن سشن فعلی و شروع سشن جدید
  const archiveInspectorSession = async () => {
    if (!inspectorSessionId) return;
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/session/${inspectorSessionId}/archive`, {
        method: 'POST',
      });
      const data = await res.json();

      if (data.success) {
        // اضافه کردن به لیست آرشیو
        if (data.session) {
          setInspectorArchivedSessions(prev => [data.session, ...prev]);
        }
        // پاک کردن چت فعلی
        setInspectorChatMessages([]);
        setPreviouslyReadFiles([]);
        setInspectorSessionId(null);
        inspectorSessionIdRef.current = null;

        // ایجاد سشن جدید
        await initInspectorSession();
        addTransientMessage('سشن آرشیو شد و سشن جدید شروع شد', 'info');
      }
    } catch (err) {
      console.error('Error archiving session:', err);
    }
  };

  // بارگذاری پیام‌های یک سشن آرشیو شده (فقط نمایش)
  const loadArchivedSession = async (sessionId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/session/${sessionId}/messages`);
      const data = await res.json();

      if (data.success && data.messages) {
        const loadedMessages = data.messages.map((m: any) => ({
          id: `db_${m.id}`,
          db_id: m.id,
          role: m.role,
          content: m.content,
          action_type: m.action_type,
          model_id: m.model_id,
          tokens_used: m.tokens_used,
          timestamp: new Date(m.timestamp),
          backend_verified: m.backend_verified,
          backend_log_summary: m.backend_log_summary,
          verified_by_model: m.verified_by_model,
          logs_checked: m.logs_checked,
          error_logs_count: m.error_logs_count,
          // بازیابی فیلدهای extra_data (action_plan, visual_debug_packs, enhanced_prompt, ...)
          ...(m.action_plan ? { action_plan: m.action_plan } : {}),
          ...(m.visual_debug_packs ? { visual_debug_packs: m.visual_debug_packs } : {}),
          ...(m.enhanced_prompt ? { enhanced_prompt: m.enhanced_prompt } : {}),
          ...(m.original_prompt ? { original_prompt: m.original_prompt } : {}),
          ...(m.is_visual_debug_report ? { is_visual_debug_report: true } : {}),
          ...(m.is_reanalysis_report ? { is_reanalysis_report: true } : {}),
          ...(m.original_user_description ? { original_user_description: m.original_user_description } : {}),
          ...(m.vision_model ? { vision_model: m.vision_model } : {}),
          ...(m.files_were_read !== undefined ? { files_were_read: m.files_were_read } : {}),
          ...(m.reply_to_id ? { reply_to_id: m.reply_to_id, reply_to_content: m.reply_to_content } : {}),
        }));
        setInspectorChatMessages(loadedMessages);
      }
    } catch (err) {
      console.error('Error loading archived session:', err);
    }
  };

  // ذخیره خودکار پیام‌های assistant در دیتابیس
  const lastSavedMsgCountRef = useRef(0);
  useEffect(() => {
    const currentSessionId = inspectorSessionIdRef.current;
    if (!currentSessionId) return;
    const newMsgs = inspectorChatMessages.slice(lastSavedMsgCountRef.current);
    for (const msg of newMsgs) {
      if ((msg.role === 'assistant' || msg.role === 'system') && !msg.db_id) {
        // جمع‌آوری extra_data برای ذخیره فیلدهای اضافی (action_plan, visual_debug, ...)
        const _msgAny = msg as any;
        const _extraData: Record<string, any> = {};
        if (_msgAny.action_plan) _extraData.action_plan = _msgAny.action_plan;
        if (_msgAny.action_type) _extraData.action_type_extra = _msgAny.action_type;
        if (_msgAny.is_visual_debug_report) _extraData.is_visual_debug_report = true;
        if (_msgAny.is_reanalysis_report) _extraData.is_reanalysis_report = true;
        if (_msgAny.original_user_description) _extraData.original_user_description = _msgAny.original_user_description;
        if (_msgAny.vision_model) _extraData.vision_model = _msgAny.vision_model;
        if (_msgAny.files_were_read !== undefined) _extraData.files_were_read = _msgAny.files_were_read;
        fetch(`${API_BASE}/api/render/inspector/session/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: currentSessionId,
            role: msg.role,
            content: msg.content,
            model_id: msg.model_id,
            tokens_used: msg.tokens_used,
            action_type: _msgAny.action_type || undefined,
            ...(Object.keys(_extraData).length > 0 ? { extra_data: _extraData } : {}),
          })
        }).catch(err => console.error('Auto-save msg failed:', err));
      }
    }
    lastSavedMsgCountRef.current = inspectorChatMessages.length;
  }, [inspectorChatMessages.length, inspectorSessionId]);

  // 🆕 لود مدل‌های موجود برای چت
  const loadInspectorModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/models`);
      const data = await res.json();

      if (data.success && data.models_by_provider) {
        // flatten کردن مدل‌ها
        const allModels: Array<{id: string; name: string; provider: string; enabled: boolean}> = [];
        Object.entries(data.models_by_provider).forEach(([provider, models]: [string, any]) => {
          models.forEach((m: any) => {
            allModels.push({
              id: m.id,
              name: m.name,
              provider: provider,
              enabled: m.enabled !== false
            });
          });
        });
        setInspectorModels(allModels);

        // 🆕 بررسی وضعیت GitHub
        if (data.github_connected !== undefined) {
          setInspectorGithubConnected(data.github_connected);
        }

        // انتخاب هوشمند مدل بر اساس آرشیو چت‌ها
        if (inspectorSelectedModels.length === 0 && projectId) {
          try {
            const smartRes = await fetch(`${API_BASE}/api/render/inspector/smart-select-model/${projectId}`);
            const smartData = await smartRes.json();
            if (smartData.success && smartData.model_id) {
              const smartModel = allModels.find(m => m.id === smartData.model_id && m.enabled);
              if (smartModel) {
                setInspectorSelectedModels([smartModel.id]);
              } else {
                // اگر مدل پیشنهادی غیرفعال بود، اولین فعال
                const firstEnabled = allModels.find(m => m.enabled);
                if (firstEnabled) setInspectorSelectedModels([firstEnabled.id]);
              }
            } else {
              const firstEnabled = allModels.find(m => m.enabled);
              if (firstEnabled) setInspectorSelectedModels([firstEnabled.id]);
            }
          } catch {
            const firstEnabled = allModels.find(m => m.enabled);
            if (firstEnabled) setInspectorSelectedModels([firstEnabled.id]);
          }
        }
      }
    } catch (err) {
      console.error('Error loading inspector models:', err);
    }
  };

  // 🔍 باز کردن مودال بررسی خطا
  const openInvestigateModal = async (msgId: string) => {
    setInvestigateModalMsgId(msgId);
    setInvestigateSelectedModels([]);
    setInvestigateReport(null);
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/models/for-investigation/${projectId}`);
      const data = await res.json();
      if (data.success && Array.isArray(data.models)) {
        setInvestigateModels(data.models);
        // انتخاب مدل‌های پیشنهادی
        const recommended = data.models.filter((m: any) => m.recommended).map((m: any) => m.id);
        setInvestigateSelectedModels(recommended.slice(0, 2));
      }
    } catch (err) {
      console.error('Error loading investigation models:', err);
    }
  };

  // فعال‌سازی سریع مدل از مودال بررسی
  const quickEnableModel = async (modelId: string) => {
    try {
      await fetch(`${API_BASE}/api/render/inspector/models/quick-enable/${modelId}`, { method: 'POST' });
      // آپدیت لیست مدل‌ها
      setInvestigateModels(prev => prev.map(m =>
        m.id === modelId ? { ...m, enabled: true } : m
      ));
    } catch (err) {
      console.error('Error enabling model:', err);
    }
  };

  // شروع بررسی خطا با SSE
  const startInvestigation = async () => {
    if (!investigateModalMsgId || investigateSelectedModels.length === 0) return;

    const errorMsg = inspectorChatMessages.find(m => m.id === investigateModalMsgId);
    if (!errorMsg) return;

    setInvestigateLoading(true);
    setInvestigateModalMsgId(null); // بستن مودال

    // 🔒 قفل کردن iframe + chat + سینک مدل‌ها
    setInspectorOpLock(true);
    setInspectorOpType('investigate');
    setInspectorOpPaused(false);
    inspectorOpAbortRef.current = new AbortController();
    // سینک مدل‌های انتخاب شده با چت
    setInspectorSelectedModels(investigateSelectedModels);
    setInspectorAutoSelect(false);

    // اضافه کردن پیام شروع بررسی
    const startMsgId = `investigate_start_${Date.now()}`;
    setInspectorChatMessages(prev => [...prev, {
      id: startMsgId,
      role: 'system' as const,
      content: `🔍 شروع بررسی ریشه‌ای خطا با مدل‌ ${investigateSelectedModels.join(', ')}...`,
      timestamp: new Date(),
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/investigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: errorMsg.db_id || 0,
          project_id: projectId,
          model_ids: investigateSelectedModels,
        }),
        signal: inspectorOpAbortRef.current?.signal,
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) throw new Error('No reader');

      let eventType = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));

              if (eventType === 'progress') {
                const progressId = `inv_progress_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
                setInspectorChatMessages(prev => [...prev, {
                  id: progressId,
                  role: 'system' as const,
                  content: data.message,
                  timestamp: new Date(),
                  model_id: data.model,
                }]);
              } else if (eventType === 'error') {
                const errId = `inv_error_${Date.now()}`;
                setInspectorChatMessages(prev => [...prev, {
                  id: errId,
                  role: 'system' as const,
                  content: `❌ ${data.message}`,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'report') {
                setInvestigateReport(data);
                const reportId = `inv_report_${Date.now()}`;
                setInspectorChatMessages(prev => [...prev, {
                  id: reportId,
                  role: 'assistant' as const,
                  content: data.report,
                  timestamp: new Date(),
                  model_id: data.model_used,
                  action_type: 'investigate_report' as any,
                }]);
              }
            } catch (e) {
              // ignore parse errors
            }
            eventType = '';
          }
        }
      }
    } catch (err) {
      setInspectorChatMessages(prev => [...prev, {
        id: `inv_fail_${Date.now()}`,
        role: 'system' as const,
        content: `❌ خطا در بررسی: ${(err as Error).message}`,
        timestamp: new Date(),
      }]);
    } finally {
      setInvestigateLoading(false);
      // 🔓 آزاد کردن قفل بعد از پایان بررسی (قبل از اصلاح)
      setInspectorOpLock(false);
      setInspectorOpType(null);
    }
  };

  // 🆕 شروع بررسی کلی چند خطا با هم
  const startBulkInvestigation = async () => {
    if (selectedErrorIds.length === 0 || investigateSelectedModels.length === 0) return;

    const errorMsgs = selectedErrorIds
      .map(id => inspectorChatMessages.find(m => m.id === id))
      .filter(Boolean) as typeof inspectorChatMessages;

    if (errorMsgs.length === 0) return;

    setBulkInvestigateModalOpen(false);
    setErrorMultiSelectMode(false);
    setInvestigateLoading(true);
    setInspectorOpLock(true);
    setInspectorOpType('investigate');
    inspectorOpAbortRef.current = new AbortController();

    const errorSummaries = errorMsgs.map((msg, i) => {
      const type = (msg as any).action_type === 'console-error' ? 'خطای کنسول' : 'خطای بک‌اند';
      const verified = (msg as any).backend_verified === false ? 'تأیید شده' : 'بررسی نشده';
      const logs = (msg as any).checked_logs || [];
      const summary = (msg as any).backend_log_summary || '';
      return `${i + 1}. [${type}] ${msg.content} | وضعیت: ${verified}${summary ? ' | خلاصه: ' + summary : ''}${logs.length > 0 ? ' | لاگ: ' + logs.map((l: any) => l.message).join('; ') : ''}`;
    }).join('\n');

    setInspectorChatMessages(prev => [...prev, {
      id: `bulk_inv_start_${Date.now()}`,
      role: 'system' as const,
      content: `🔍 شروع بررسی کلی ${errorMsgs.length} خطا با مدل ${investigateSelectedModels.join(', ')}...\n${errorSummaries}`,
      timestamp: new Date(),
    }]);

    try {
      // ارسال شناسه‌های DB پیام‌های خطا
      const messageIds = errorMsgs.map(m => (m as any).db_id).filter(Boolean);

      const res = await fetch(`${API_BASE}/api/render/inspector/investigate-bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_ids: messageIds,
          project_id: projectId,
          model_ids: investigateSelectedModels,
        }),
        signal: inspectorOpAbortRef.current?.signal,
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let eventType = '';

      if (!reader) throw new Error('No reader');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));
              if (eventType === 'progress') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `bulk_inv_p_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
                  role: 'system' as const,
                  content: data.message,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'error') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `bulk_inv_err_${Date.now()}`,
                  role: 'system' as const,
                  content: `❌ ${data.message}`,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'report') {
                setInvestigateReport(data);
                setInspectorChatMessages(prev => [...prev, {
                  id: `bulk_inv_report_${Date.now()}`,
                  role: 'assistant' as const,
                  content: data.report,
                  timestamp: new Date(),
                  model_id: data.model_used,
                  action_type: 'investigate_report' as any,
                }]);
              } else if (eventType === 'done') {
                setInspectorOpLock(false);
                setInspectorOpType(null);
              }
            } catch {}
            eventType = '';
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setInspectorChatMessages(prev => [...prev, {
          id: `bulk_inv_fail_${Date.now()}`,
          role: 'assistant' as const,
          content: `❌ خطا در بررسی کلی: ${err.message?.slice(0, 100) || 'ناشناخته'}`,
          timestamp: new Date(),
        }]);
      }
    } finally {
      setInvestigateLoading(false);
      setInspectorOpLock(false);
      setInspectorOpType(null);
      setSelectedErrorIds([]);
    }
  };

  // شروع اصلاح خطا با SSE
  const startFix = async () => {
    if (!investigateReport || fixSelectedModels.length === 0) return;

    setFixLoading(true);
    setFixModalOpen(false);

    // 🔒 قفل کردن + سینک مدل‌ها
    setInspectorOpLock(true);
    setInspectorOpType('fix');
    setInspectorOpPaused(false);
    inspectorOpAbortRef.current = new AbortController();
    setInspectorSelectedModels(fixSelectedModels);
    setInspectorAutoSelect(false);

    setInspectorChatMessages(prev => [...prev, {
      id: `fix_start_${Date.now()}`,
      role: 'system' as const,
      content: `🔧 شروع اصلاح خودکار با مدل ${fixSelectedModels.join(', ')}...`,
      timestamp: new Date(),
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          model_ids: fixSelectedModels,
          investigation_report: investigateReport.report,
          files_to_fix: investigateReport.files_to_fix || [],
          error_message: investigateReport.error_content,
        }),
        signal: inspectorOpAbortRef.current?.signal,
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) throw new Error('No reader');

      let eventType = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));

              if (eventType === 'progress') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `fix_p_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
                  role: 'system' as const,
                  content: data.message,
                  timestamp: new Date(),
                  model_id: data.model,
                }]);
              } else if (eventType === 'error') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `fix_err_${Date.now()}`,
                  role: 'system' as const,
                  content: `❌ ${data.message}`,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'fix_complete') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `fix_done_${Date.now()}`,
                  role: 'assistant' as const,
                  content: data.message + (data.pr_url ? `\n\n🔗 [مشاهده Pull Request](${data.pr_url})` : ''),
                  timestamp: new Date(),
                  model_id: data.model_used,
                }]);
                // آزاد کردن صفحه پیش‌نمایش برای تست
                setInspectorChatMessages(prev => [...prev, {
                  id: `fix_test_${Date.now()}`,
                  role: 'system' as const,
                  content: '🧪 الان برو اون قسمت رو تست کن و ببین آیا مشکل حل شده!',
                  timestamp: new Date(),
                }]);
              }
            } catch (e) {}
            eventType = '';
          }
        }
      }
    } catch (err) {
      setInspectorChatMessages(prev => [...prev, {
        id: `fix_fail_${Date.now()}`,
        role: 'system' as const,
        content: `❌ خطا در اصلاح: ${(err as Error).message}`,
        timestamp: new Date(),
      }]);
    } finally {
      setFixLoading(false);
      setInvestigateReport(null);
      // 🔓 آزاد کردن قفل بعد از پایان اصلاح
      setInspectorOpLock(false);
      setInspectorOpType(null);
    }
  };

  // 🧠 اعمال تغییرات پیشنهادی (دکمه "اعمال" در پاسخ‌های smart-chat)
  const applySmartAction = async (msgId: string) => {
    const msg = inspectorChatMessages.find(m => m.id === msgId) as any;
    if (!msg?.action_plan?.files || msg.action_plan.files.length === 0) {
      // بررسی فایل‌های بدون محتوا (modify_sections فایل‌ها بجای content از sections استفاده میکنن)
      const hasEmptyContent = msg?.action_plan?.files?.some((f: any) => !f.content && f.operation !== 'modify_sections');
      setInspectorChatMessages(prev => [...prev, {
        id: `apply_err_${Date.now()}`,
        role: 'system' as const,
        content: hasEmptyContent
          ? '⚠️ فایل‌های تغییر بدون محتوا هستند. لطفاً از مدل بخواهید محتوای کامل فایل‌ها را ارائه دهد.'
          : '⚠️ اطلاعات تغییرات پیدا نشد. مدل AI نتوانست فایل‌های اصلاح‌شده ارائه دهد — لطفاً مجدد درخواست بدهید یا مدل دیگری انتخاب کنید.',
        timestamp: new Date(),
      }]);
      return;
    }

    // لایه ۲ فرانت‌اند: هشدار اگر فایل‌ها خوانده نشده بودن
    if (msg.files_were_read === false) {
      setInspectorChatMessages(prev => [...prev, {
        id: `apply_warn_${Date.now()}`,
        role: 'system' as const,
        content: '🚫 اعمال لغو شد: فایل‌های پروژه خوانده نشده بودند — محتوای ارائه‌شده ممکنه حدسی/ساختگی باشه. لطفاً ابتدا GitHub Token را تنظیم کنید و مجدداً درخواست بدهید.',
        timestamp: new Date(),
      }]);
      return;
    }

    // 🔒 قفل
    setInspectorOpLock(true);
    setInspectorOpType('fix');
    inspectorOpAbortRef.current = new AbortController();

    setInspectorChatMessages(prev => [...prev, {
      id: `apply_start_${Date.now()}`,
      role: 'system' as const,
      content: `🔧 شروع اعمال تغییرات (${msg.action_plan.files.length} فایل${msg.action_plan.files.some((f: any) => f.operation === 'modify_sections') ? ' — شامل modify_sections' : ''})...`,
      timestamp: new Date(),
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/apply-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          model_ids: inspectorSelectedModels,
          action_description: msg.action_plan.commit_message || 'Smart fix',
          action_files: msg.action_plan.files,
          commit_message: msg.action_plan.commit_message || 'Inspector smart fix',
          original_message: msg.original_message || '',
        }),
        signal: inspectorOpAbortRef.current?.signal,
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = '';

      if (!reader) throw new Error('No reader');

      let eventType = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split('\n');
        sseBuffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));

              if (eventType === 'progress') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `apply_p_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
                  role: 'system' as const,
                  content: data.message,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'error') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `apply_err_${Date.now()}`,
                  role: 'system' as const,
                  content: `❌ ${data.message}`,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'apply_complete') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `apply_done_${Date.now()}`,
                  role: 'assistant' as const,
                  content: data.message + (data.pr_url ? `\n\n🔗 [مشاهده Pull Request](${data.pr_url})` : ''),
                  timestamp: new Date(),
                }]);
              }
            } catch (e) {}
            eventType = '';
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setInspectorChatMessages(prev => [...prev, {
          id: `apply_fail_${Date.now()}`,
          role: 'system' as const,
          content: `❌ خطا در اعمال تغییرات: ${err.message}`,
          timestamp: new Date(),
        }]);
      }
    } finally {
      setInspectorOpLock(false);
      setInspectorOpType(null);
    }
  };

  // 🆕 تشخیص اینکه آیا این یک task ویژوال است
  // ⚠️ باید مطمئن بشیم که درخواست‌های مربوط به خطا/مشکل/تحلیل، ویژوال نباشن
  const isVisualTask = (message: string): boolean => {
    const lowerMessage = message.toLowerCase();

    // ❌ اگر پیام حاوی کلمات مرتبط با خطا/مشکل/تحلیل باشه → ویژوال نیست
    const errorExcludeKeywords = [
      // خطا و مشکل - فارسی
      'خطا', 'ارور', 'مشکل', 'باگ', 'درست کن', 'درستش کن', 'فیکس', 'حل کن',
      'کار نمیکنه', 'کار نمی‌کنه', 'نمیشه', 'نمی‌شه', 'خراب', 'اشکال',
      'علت', 'علتش', 'چرا', 'دلیل', 'بررسی کن', 'چک کن', 'تحلیل',
      'ظاهر میشه', 'ظاهر می‌شه', 'نشون میده', 'نشان می‌دهد',
      // خطا و مشکل - انگلیسی
      'error', 'exception', 'bug', 'fix', 'issue', 'problem', 'broken',
      'failed', 'failure', 'crash', 'debug', 'stack trace', 'traceback',
      'typeerror', 'syntaxerror', 'referenceerror', 'undefined',
      'cannot read', 'is not defined', 'is not a function',
      'application error', 'client-side exception', 'server error',
      '500', '404', '403', 'cors', 'timeout',
    ];
    if (errorExcludeKeywords.some(keyword => lowerMessage.includes(keyword))) {
      return false;
    }

    // ✅ فقط اگر هیچ نشانه‌ای از خطا/تحلیل نباشه، بررسی کلمات ویژوال
    const visualKeywords = [
      // ناوبری - فارسی
      'برو به', 'وارد شو', 'بازکن', 'باز کن', 'نمایش بده', 'نشان بده',
      'واردشو', 'رفتن به', 'بروید',
      // ناوبری - انگلیسی
      'navigate', 'go to', 'open', 'visit',
      // لاگین
      'لاگین', 'login', 'sign in', 'ثبت نام', 'register',
      // کلیک
      'کلیک کن', 'click', 'بزن روی', 'فشار بده',
      // تایپ
      'تایپ کن', 'type', 'بنویس', 'وارد کن', 'پر کن', 'fill',
      // اسکرول
      'اسکرول', 'scroll', 'پایین برو', 'بالا برو',
      // جستجو
      'پیدا کن', 'find', 'جستجو کن', 'search',
      // اقدامات خاص
      'ببند', 'حذف کن', 'ویرایش کن', 'ذخیره کن',
      'ارسال کن', 'تایید کن', 'لغو کن'
    ];
    return visualKeywords.some(keyword => lowerMessage.includes(keyword));
  };

  // 🆕 استخراج متن هدف از پیام کاربر
  const extractTargetText = (message: string): string => {
    // الگوهای رایج برای استخراج هدف
    const patterns = [
      // فارسی
      /برو (?:به |روی )?(?:قسمت |بخش |صفحه |تب )?(.+)/i,
      /(?:کلیک|بزن) (?:روی |بر روی )?(.+)/i,
      /وارد (?:قسمت |بخش |صفحه )?(.+) (?:شو|بشو)/i,
      /(?:باز کن|بازکن|نمایش بده) (.+)/i,
      /پیدا کن (.+)/i,
      // انگلیسی
      /go to (.+)/i,
      /click (?:on )?(.+)/i,
      /navigate to (.+)/i,
      /open (.+)/i,
      /find (.+)/i,
      /show (.+)/i,
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match && match[1]) {
        // پاکسازی نتیجه
        return match[1].trim().replace(/[.،؟!]/g, '');
      }
    }

    // اگر الگویی پیدا نشد، کل پیام را برگردان (بدون کلمات کمکی)
    const cleanMessage = message
      .replace(/برو|وارد|کلیک|بزن|باز کن|نمایش/gi, '')
      .replace(/به|روی|شو|بشو|قسمت|بخش|صفحه/gi, '')
      .trim();

    return cleanMessage || message;
  };

  // 🆕 انیمیشن cursor به صورت متوالی
  const animateCursorSequence = async (positions: Array<{x: number; y: number; action: string}>) => {
    for (const pos of positions) {
      setInspectorVirtualCursor({
        x: pos.x,
        y: pos.y,
        visible: true,
        model_id: pos.action
      });
      await new Promise(resolve => setTimeout(resolve, 800)); // 800ms بین هر حرکت
    }
    // پنهان کردن بعد از آخرین حرکت
    setTimeout(() => {
      setInspectorVirtualCursor(prev => ({ ...prev, visible: false }));
    }, 2000);
  };

  // 🆕 اسکن بصری واقعی - نوارها از روی المان‌ها رد می‌شوند و واقعاً چک می‌کنند
  const runVisualScan = async (searchText: string) => {
    if (!inspectorFrontendUrl) return;

    // شروع اسکن - انیمیشن سریع
    setInspectorScanBars({
      verticalX: 0,
      horizontalY: 0,
      scanning: true,
      targetFound: false,
      intersection: null
    });

    try {
      // انیمیشن اسکن سریع (در حالی که بکند کار میکنه)
      const scanAnimation = async () => {
        for (let p = 0; p <= 100; p += 3) {
          setInspectorScanBars(prev => {
            if (prev.targetFound) return prev;  // اگه پیدا شد متوقف شو
            return { ...prev, verticalX: p, horizontalY: p };
          });
          await new Promise(resolve => setTimeout(resolve, 15));
        }
      };

      // همزمان: انیمیشن + درخواست به بکند
      const [_, findResult] = await Promise.all([
        scanAnimation(),
        fetch(`${API_BASE}/api/render/inspector/find-and-click?url=${encodeURIComponent(inspectorFrontendUrl)}&search_text=${encodeURIComponent(searchText)}`, {
          method: 'POST'
        }).then(res => res.json())
      ]);

      console.log('🎯 Find result:', findResult);

      if (findResult.success && findResult.position) {
        // پیدا شد! نمایش موقعیت
        const { percent_x, percent_y } = findResult.position;

        setInspectorScanBars({
          verticalX: percent_x,
          horizontalY: percent_y,
          scanning: true,
          targetFound: true,
          intersection: { x: percent_x, y: percent_y, text: findResult.found }
        });

        setInspectorVirtualCursor({
          x: percent_x,
          y: percent_y,
          visible: true,
          model_id: `🎯 ${findResult.found}`
        });

        // نمایش candidates در console برای debug
        if (findResult.all_candidates) {
          console.log('📋 All candidates:', findResult.all_candidates);
        }

        // پنهان کردن بعد از 3 ثانیه
        setTimeout(() => {
          setInspectorScanBars(prev => ({
            ...prev,
            scanning: false,
            targetFound: false,
            intersection: null
          }));
          setInspectorVirtualCursor(prev => ({ ...prev, visible: false }));
        }, 3000);

        return {
          success: true,
          message: `پیدا شد: ${findResult.found} (${findResult.click_method})`,
          target_position: { x: percent_x, y: percent_y },
          clicked: true,
          url_changed: findResult.url_changed,
          new_url: findResult.new_url  // 🆕 URL جدید برای آپدیت iframe
        };
      }

      // پیدا نشد
      console.log('❌ Not found:', searchText, findResult.all_candidates || []);
      setInspectorScanBars(prev => ({ ...prev, scanning: false }));

      return {
        success: false,
        message: findResult.error || `"${searchText}" پیدا نشد`,
        candidates: findResult.all_candidates
      };

    } catch (error) {
      console.error('Visual scan error:', error);
      setInspectorScanBars(prev => ({ ...prev, scanning: false }));
      throw error;
    }
  };

  // ============================================
  // 🆕🆕🆕 Live Action Tracking - رصد لحظه‌ای فعالیت کاربر
  // ============================================

  // اضافه کردن پیام موقت (گزارش لحظه‌ای)
  const addTransientMessage = (content: string, type: 'action' | 'backend' | 'error' | 'info', source?: string) => {
    const id = `transient_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newMessage = {
      id,
      content,
      type,
      source,
      timestamp: new Date(),
      fadeOut: false
    };

    setInspectorTransientMessages(prev => [...prev, newMessage]);

    // شروع محو شدن بعد از 3 ثانیه
    setTimeout(() => {
      setInspectorTransientMessages(prev =>
        prev.map(m => m.id === id ? { ...m, fadeOut: true } : m)
      );
    }, 3000);

    // حذف کامل بعد از 4 ثانیه
    setTimeout(() => {
      setInspectorTransientMessages(prev => prev.filter(m => m.id !== id));
    }, 4000);
  };

  // تحلیل بصری اقدام کاربر با AI
  const analyzeUserAction = async (actionType: string, x: number, y: number) => {
    if (!inspectorFrontendUrl || !inspectorActionTracking.enabled) return;
    if (inspectorPaused) return; // اگر متوقف شده، کاری نکن

    try {
      // ارسال به backend برای تحلیل بصری
      const res = await fetch(`${API_BASE}/api/render/inspector/analyze-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: inspectorFrontendUrl,
          action_type: actionType,
          position: { x, y },
          project_id: projectId,
          selected_models: inspectorSelectedModels.length > 0 ? inspectorSelectedModels : ['gemini-2.0-flash-exp']
        })
      });

      const data = await res.json();

      if (data.success) {
        // گزارش عمل انجام شده
        if (data.action_description) {
          addTransientMessage(data.action_description, 'action', data.visual_model);
        }

        // گزارش از بک‌اند (اگر وجود داشت)
        if (data.backend_status) {
          addTransientMessage(
            data.backend_status.message,
            data.backend_status.has_error ? 'error' : 'backend',
            data.backend_model
          );
        }

        // بررسی خطا
        if (data.has_error) {
          handleInspectorError(data.error_info);
        }

        // آپدیت URL اگر صفحه تغییر کرده
        if (data.new_url && data.new_url !== inspectorFrontendUrl) {
          addTransientMessage(`صفحه ${data.page_name || 'جدید'} باز شد`, 'info');
          setInspectorFrontendUrl(data.new_url);
        }
      }
    } catch (err) {
      console.error('Error analyzing user action:', err);
    }
  };

  // مدیریت خطای شناسایی شده
  const handleInspectorError = async (errorInfo: {
    message: string;
    log_details?: string;
    source_hint?: string;
  }) => {
    // توقف فوری - غیرفعال کردن تعامل
    setInspectorPaused(true);
    setInspectorPausedError({
      message: errorInfo.message,
      details: errorInfo.log_details || '',
      analyzing: true
    });

    addTransientMessage(`⛔ خطا شناسایی شد: ${errorInfo.message}`, 'error');
    addTransientMessage('🔍 در حال بررسی علت خطا در کد منبع...', 'info');

    try {
      // درخواست تحلیل عمیق از GitHub
      const analysisRes = await fetch(`${API_BASE}/api/render/inspector/analyze-error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          error_message: errorInfo.message,
          log_details: errorInfo.log_details,
          source_hint: errorInfo.source_hint,
          selected_models: inspectorSelectedModels.length > 0 ? inspectorSelectedModels : ['claude-3-5-sonnet-20241022']
        })
      });

      const analysis = await analysisRes.json();

      if (analysis.success) {
        // آپدیت با نتایج تحلیل
        setInspectorPausedError(prev => prev ? {
          ...prev,
          analyzing: false,
          sourceFiles: analysis.source_files || [],
          details: analysis.detailed_report || prev.details
        } : null);

        // نمایش گزارش نهایی در چت
        const reportMsg = {
          id: `error_report_${Date.now()}`,
          role: 'assistant' as const,
          content: `## ⚠️ گزارش خطا

**خطا:** ${errorInfo.message}

**تحلیل:**
${analysis.analysis || 'در حال بررسی...'}

**فایل‌های مرتبط:**
${(analysis.source_files || []).map((f: any) => `- \`${f.path}\`: ${f.issue}`).join('\n') || 'نامشخص'}

**پیشنهاد رفع:**
${analysis.suggested_fix || 'بررسی فایل‌های فوق'}

---
*گزارش از: ${analysis.model_used || 'AI'}*`,
          model_id: analysis.model_used,
          timestamp: new Date()
        };

        setInspectorChatMessages(prev => [...prev, reportMsg]);
      }
    } catch (err) {
      console.error('Error analyzing source:', err);
      setInspectorPausedError(prev => prev ? {
        ...prev,
        analyzing: false,
        details: 'خطا در تحلیل کد منبع'
      } : null);
    }
  };

  // ادامه کار بعد از خطا
  const resumeAfterError = () => {
    setInspectorPaused(false);
    setInspectorPausedError(null);
    addTransientMessage('✅ ادامه کار...', 'info');
  };

  // 🌉 بررسی وضعیت Bridge Script
  const checkBridgeStatus = async () => {
    setInspectorBridgeStatus(prev => ({ ...prev, checking: true, error: undefined }));
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/bridge-status/${projectId}`);
      const data = await res.json();
      setInspectorBridgeStatus(prev => ({
        ...prev,
        checking: false,
        has_bridge: data.has_bridge || false,
        file_path: data.file_path,
        needs_update: data.needs_update || false,
        update_reasons: data.update_reasons || [],
        version: data.version,
        latest_version: data.latest_version
      }));

      // 🔄 Auto-fix: اگر نسخه قدیمی بود، خودکار آپدیت کن
      if (data.has_bridge && data.needs_update) {
        console.log(`🔄 Bridge outdated (v${data.version} → v${data.latest_version}), auto-updating...`);
        addTransientMessage(`🔄 Bridge قدیمی است - آپدیت خودکار به v${data.latest_version}...`, 'info');
        try {
          const updateRes = await fetch(`${API_BASE}/api/render/inspector/update-bridge/${projectId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          });
          const updateData = await updateRes.json();
          if (updateData.success) {
            setInspectorBridgeStatus(prev => ({
              ...prev,
              needs_update: false,
              update_reasons: [],
              version: updateData.version
            }));
            addTransientMessage(`✅ Bridge خودکار به v${updateData.version} آپدیت شد - منتظر deploy باشید`, 'info');
          } else {
            console.warn('Auto-update failed:', updateData.error);
          }
        } catch (autoFixErr) {
          console.warn('Auto-fix bridge failed:', autoFixErr);
        }
      }
    } catch (err) {
      setInspectorBridgeStatus(prev => ({
        ...prev,
        checking: false,
        error: 'خطا در بررسی وضعیت'
      }));
    }
  };

  // 🔍 تشخیص مشکلات Bridge Script
  const debugBridgeStatus = async () => {
    setBridgeDebugInfo({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/debug-bridge/${projectId}`);
      const data = await res.json();
      setBridgeDebugInfo({ loading: false, data });
      console.log('🔍 Bridge Debug Info:', data);
    } catch (err) {
      setBridgeDebugInfo({ loading: false, data: { diagnosis: 'خطا در بررسی: ' + err } });
    }
  };

  // 🌉 تزریق یا حذف Bridge Script
  const toggleBridgeScript = async (customPath?: string) => {
    const isRemoving = inspectorBridgeStatus.has_bridge;
    setInspectorBridgeStatus(prev => ({ ...prev, injecting: true, error: undefined }));

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/inject-bridge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          remove: isRemoving,
          custom_path: customPath || undefined
        })
      });

      const data = await res.json();

      if (data.success) {
        setInspectorBridgeStatus(prev => ({
          ...prev,
          injecting: false,
          has_bridge: !isRemoving,
          file_path: data.file_path
        }));
        addTransientMessage(
          isRemoving ? '🔧 اسکریپت Bridge حذف شد' : '🌉 اسکریپت Bridge تزریق شد - منتظر deploy باشید',
          'info'
        );
        showSuccess(data.message || (isRemoving ? 'حذف شد' : 'تزریق شد'));
        setShowCustomHtmlPathDialog(false);
        setCustomHtmlPathInput('');
      } else {
        // 🔍 Debug: چاپ پاسخ API
        console.log('🔍 Bridge API Response:', data);
        // Debug info کامل
        if (data.debug) {
          console.log('🔍 DEBUG INFO:');
          console.log('  - GitHub Path:', data.debug.github_path);
          console.log('  - Default Branch:', data.debug.default_branch);
          console.log('  - Package.json Found:', data.debug.package_json_found);
          console.log('  - Package.json Status:', data.debug.package_json_status);
          console.log('  - Tree Status:', data.debug.tree_status);
          console.log('  - Detected Framework:', data.debug.detected_framework_raw);
          console.log('  - Total Files:', data.debug.total_files_found);
          console.log('  - HTML Files:', data.debug.html_files_count);
          console.log('  - All HTML Files:', JSON.stringify(data.debug.all_html_files));
          console.log('  - All package.json files:', JSON.stringify(data.debug.all_package_jsons));
          console.log('  - Entry Candidates:', JSON.stringify(data.debug.entry_candidates));
          console.log('  - 📂 Frontend Files:', JSON.stringify(data.debug.frontend_files));
          console.log('  - 🔍 Pattern Match Files:', JSON.stringify(data.debug.pattern_match_files));
          console.log('  - ❓ Pattern Search Reason:', data.debug.pattern_search_reason);
          console.log('  - Dependencies Sample:', JSON.stringify(data.debug.deps_sample));
          console.log('  - Search Error:', data.debug.search_error);
        }

        // اگر index.html پیدا نشد، دیالوگ مسیر سفارشی نشان بده
        if (data.need_custom_path) {
          // ذخیره فایل‌های HTML پیدا شده و فریم‌ورک تشخیص داده شده
          console.log('📁 Found HTML files:', data.found_html_files);
          console.log('🔧 Detected framework:', data.framework_detected);
          console.log('🚫 Is Backend-only:', data.is_backend_only);
          setFoundHtmlFiles(data.found_html_files || []);
          setDetectedFramework(data.framework_detected || null);
          setIsBackendOnly(data.is_backend_only || false);
          setShowCustomHtmlPathDialog(true);
          setInspectorBridgeStatus(prev => ({
            ...prev,
            injecting: false,
            error: data.is_backend_only
              ? 'این پروژه فرانت‌اند ندارد (Backend-only)'
              : data.framework_detected
                ? `پروژه ${data.framework_detected} است - HTML در build ساخته می‌شود`
                : 'فایل HTML یافت نشد - مسیر را وارد کنید'
          }));
        } else {
          setInspectorBridgeStatus(prev => ({
            ...prev,
            injecting: false,
            error: data.error
          }));
          showError(data.error || 'خطا در عملیات');
        }
      }
    } catch (err) {
      setInspectorBridgeStatus(prev => ({
        ...prev,
        injecting: false,
        error: 'خطا در ارتباط با سرور'
      }));
    }
  };

  // 🔄 به‌روزرسانی Bridge Script (حذف نسخه قدیمی و تزریق نسخه جدید با WebSocket)
  const reInjectBridge = async () => {
    setInspectorBridgeStatus(prev => ({ ...prev, injecting: true, error: undefined }));
    addTransientMessage('🔄 به‌روزرسانی Bridge با نسخه WebSocket...', 'info');

    try {
      // یک درخواست force_update - حذف قدیمی + تزریق جدید در یک مرحله
      const res = await fetch(`${API_BASE}/api/render/inspector/inject-bridge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, remove: false, force_update: true })
      });
      const data = await res.json();
      console.log('🔄 Force update result:', data);

      if (data.success) {
        setInspectorBridgeStatus(prev => ({
          ...prev,
          injecting: false,
          has_bridge: true,
          file_path: data.file_path
        }));
        addTransientMessage(
          data.ws_url
            ? '🌐 Bridge با WebSocket تزریق شد - منتظر deploy باشید'
            : '🌉 Bridge تزریق شد - منتظر deploy باشید',
          'info'
        );
        showSuccess(data.message || 'Bridge به‌روزرسانی شد!');
      } else {
        setInspectorBridgeStatus(prev => ({ ...prev, injecting: false, error: data.error }));
        showError(data.error || 'خطا در به‌روزرسانی');
      }
    } catch (err) {
      setInspectorBridgeStatus(prev => ({ ...prev, injecting: false, error: 'خطا در ارتباط با سرور' }));
    }
  };

  // 🔄 به‌روزرسانی مستقیم Bridge به آخرین نسخه (بدون نیاز به re-inject)
  const updateBridgeToLatest = async () => {
    setInspectorBridgeStatus(prev => ({ ...prev, injecting: true, error: undefined }));
    addTransientMessage('🔄 به‌روزرسانی Bridge به آخرین نسخه...', 'info');

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/update-bridge/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      console.log('🔄 Update bridge result:', data);

      if (data.success) {
        setInspectorBridgeStatus(prev => ({
          ...prev,
          injecting: false,
          has_bridge: true,
          needs_update: false,
          update_reasons: [],
          version: data.version,
          file_path: data.file_path
        }));
        addTransientMessage(`✅ Bridge به نسخه ${data.version} به‌روزرسانی شد - منتظر deploy باشید`, 'info');
        showSuccess(data.message || 'Bridge به‌روزرسانی شد!');
      } else {
        // اگر bridge نوع HTML/JS بود، از reInjectBridge استفاده کن
        if (data.hint === 'use_force_update') {
          await reInjectBridge();
          return;
        }
        setInspectorBridgeStatus(prev => ({ ...prev, injecting: false, error: data.error }));
        showError(data.error || 'خطا در به‌روزرسانی');
      }
    } catch (err) {
      setInspectorBridgeStatus(prev => ({ ...prev, injecting: false, error: 'خطا در ارتباط با سرور' }));
    }
  };

  // 🔗 تنظیم آدرس GitHub برای پروژه
  const setGitHubPath = async () => {
    if (!gitHubPathInput.trim()) {
      showError('لطفاً آدرس GitHub را وارد کنید');
      return;
    }

    setSettingGitHubPath(true);
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/set-github-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          github_path: gitHubPathInput.trim()
        })
      });

      const data = await res.json();

      if (data.success) {
        showSuccess(data.message || 'آدرس GitHub تنظیم شد');
        setShowGitHubPathDialog(false);
        setGitHubPathInput('');
        // بررسی مجدد وضعیت Bridge
        checkBridgeStatus();
      } else {
        showError(data.error || 'خطا در تنظیم آدرس');
      }
    } catch (err) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setSettingGitHubPath(false);
    }
  };

  // مدیریت کلیک روی overlay
  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!inspectorOverlayRef.current || inspectorPaused) return;

    const rect = inspectorOverlayRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    // ثبت آخرین اقدام
    setInspectorActionTracking(prev => ({
      ...prev,
      lastAction: { type: 'click', x, y, timestamp: new Date() }
    }));

    // تحلیل با AI
    analyzeUserAction('click', x, y);
  };

  // مدیریت اسکرول
  const handleOverlayScroll = (e: React.WheelEvent<HTMLDivElement>) => {
    if (inspectorPaused) return;

    const direction = e.deltaY > 0 ? 'down' : 'up';
    addTransientMessage(`اسکرول به ${direction === 'down' ? 'پایین' : 'بالا'}`, 'action');

    // فقط یک تحلیل هر 500ms
    if (!inspectorActionTracking.lastAction ||
        new Date().getTime() - inspectorActionTracking.lastAction.timestamp.getTime() > 500) {
      analyzeUserAction('scroll', 50, direction === 'down' ? 75 : 25);
    }
  };

  // 🆕 شروع رصد لاگ‌های بک‌اند برای خطا
  const startBackendLogMonitoring = () => {
    // این interval لاگ‌های بک‌اند را رصد می‌کند
    const interval = setInterval(async () => {
      if (!inspectorPowerOn || !inspectorActionTracking.enabled) {
        clearInterval(interval);
        return;
      }

      try {
        // چک کردن لاگ‌های جدید برای خطا
        const recentLogs = inspectorBackendLogs.slice(0, 5);
        const hasError = recentLogs.some(log => log.level === 'error');

        if (hasError && !inspectorPaused) {
          const errorLog = recentLogs.find(log => log.level === 'error');
          if (errorLog) {
            handleInspectorError({
              message: errorLog.message || 'خطای ناشناخته',
              log_details: JSON.stringify(errorLog)
            });
          }
        }
      } catch (err) {
        console.error('Error monitoring backend logs:', err);
      }
    }, 2000); // هر 2 ثانیه چک کن

    return () => clearInterval(interval);
  };

  // Effect برای شروع رصد وقتی inspector روشن می‌شود
  useEffect(() => {
    if (inspectorPowerOn && inspectorActionTracking.enabled) {
      const cleanup = startBackendLogMonitoring();
      return cleanup;
    }
  }, [inspectorPowerOn, inspectorActionTracking.enabled]);

  // ============================================
  // پایان Live Action Tracking
  // ============================================

  // 🆕 بررسی background batch task فعال هنگام بازگشت به صفحه
  useEffect(() => {
    if (!inspectorPowerOn || !projectId) return;
    const checkActiveBatchTask = async () => {
      try {
        // ابتدا sessionStorage بررسی کن
        const stored = sessionStorage.getItem('inspector_batch_task');
        if (!stored) return;
        const { task_key, message, timestamp } = JSON.parse(stored);
        // فقط task‌های کمتر از ۳۰ دقیقه
        if (Date.now() - timestamp > 30 * 60 * 1000) {
          sessionStorage.removeItem('inspector_batch_task');
          return;
        }
        // بررسی وضعیت از سرور
        const res = await fetch(`${API_BASE}/api/render/inspector/smart-chat/batch-status/${task_key}`);
        const data = await res.json();
        if (data.exists && data.status === 'running') {
          // task هنوز فعاله — اتصال مجدد خودکار
          inspectorBatchTaskKeyRef.current = task_key;
          setInspectorChatMessages(prev => [...prev, {
            id: `reconnect_${Date.now()}`,
            role: 'system' as const,
            content: `♻️ پردازش قبلی هنوز در حال اجرا — اتصال مجدد خودکار... (${data.total_read || 0} فایل تا الان)`,
            timestamp: new Date(),
          }]);
          // re-trigger with retry to follow the existing task
          setTimeout(() => sendInspectorChat(message, true), 500);
        } else {
          // task تمام شده یا وجود نداره — پاکسازی
          sessionStorage.removeItem('inspector_batch_task');
        }
      } catch {
        // ignore errors
      }
    };
    checkActiveBatchTask();
  }, [inspectorPowerOn, projectId]);

  // 🧠 بهینه‌سازی پرامپت قبل از ارسال
  const enhancePrompt = async (message: string, mode: 'chat' | 'visual_debug' = 'chat'): Promise<{ text: string; wasEnhanced: boolean; error?: string; steps?: { step_number: number; description: string }[]; basePrompt?: string }> => {
    if (!inspectorSmartPrompt) return { text: message, wasEnhanced: false };
    // پیام‌های خیلی کوتاه نیاز به بهینه‌سازی ندارن
    if (message.length < 10) return { text: message, wasEnhanced: false };

    try {
      // مدل بهینه‌ساز: بسته به حالت، از مدل‌های مناسب استفاده کن
      const enhancerModel = mode === 'visual_debug'
        ? (visualDebugSelectedModels[0] || inspectorSelectedModels[0] || 'gemini-2.0-flash')
        : (inspectorSelectedModels[0] || 'gemini-2.0-flash');
      // مدل هدف (که قراره جواب بده)
      const targetModel = mode === 'visual_debug'
        ? (visualDebugSelectedModels[0] || undefined)
        : (inspectorSelectedModels[0] || undefined);

      // تاریخچه مختصر چت
      const recentHistory = inspectorChatMessages
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .slice(-10)
        .map(m => ({ role: m.role, content: m.content?.slice(0, 200) }));

      const res = await fetch(`${API_BASE}/api/render/inspector/enhance-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          message,
          model_id: enhancerModel,
          target_model_id: targetModel,
          chat_history: recentHistory,
          mode,
        }),
      });
      const data = await res.json();
      if (data.success && data.enhanced_prompt && data.enhanced_prompt !== message) {
        return {
          text: data.enhanced_prompt,
          wasEnhanced: true,
          steps: data.steps && data.steps.length > 1 ? data.steps : undefined,
          basePrompt: data.base_prompt || data.enhanced_prompt,
        };
      }
      return { text: message, wasEnhanced: false, error: data.error || 'مدل پرامپت رو تغییر نداد' };
    } catch (err: any) {
      console.error('Prompt enhance failed:', err);
      return { text: message, wasEnhanced: false, error: err?.message || String(err) };
    }
  };

  // 🔄 اجرای مرحله‌ای: هر مرحله جداگانه اجرا میشه و نتایج جمع میشه
  const executeMultiStep = async (
    rawMessage: string,
    basePrompt: string,
    steps: { step_number: number; description: string }[],
  ) => {
    setInspectorChatLoading(true);
    setInspectorOpLock(true);
    setInspectorOpType('investigate');

    // نمایش پیام کاربر اصلی
    const userMsgId = `user_ms_${Date.now()}`;
    setInspectorChatMessages(prev => [...prev, {
      id: userMsgId,
      role: 'user' as const,
      content: basePrompt,
      timestamp: new Date(),
      original_prompt: rawMessage,
      enhanced_prompt: basePrompt,
    } as any]);

    // ذخیره پیام کاربر
    if (inspectorSessionIdRef.current) {
      fetch(`${API_BASE}/api/render/inspector/session/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: inspectorSessionIdRef.current,
          role: 'user',
          content: basePrompt,
          extra_data: { original_prompt: rawMessage, enhanced_prompt: basePrompt },
        })
      }).catch(() => {});
    }

    // نمایش نقشه مراحل
    setInspectorChatMessages(prev => [...prev, {
      id: `ms_plan_${Date.now()}`,
      role: 'system' as const,
      content: `📋 درخواست به ${steps.length} مرحله تجزیه شد:\n${steps.map(s => `  ${s.step_number}. ${s.description}`).join('\n')}\n\n▶️ شروع اجرای مرحله‌ای...`,
      timestamp: new Date(),
    }]);

    const collectedActionFiles: any[] = [];
    const collectedAnalysis: string[] = [];
    let commitMessage = '';
    let allFilesWereRead = true;
    let lastModelUsed = '';
    const modelIds = inspectorAutoSelect ? [] : inspectorSelectedModels;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      const stepId = `ms_step_${i}_${Date.now()}`;

      // نمایش شروع مرحله
      setInspectorChatMessages(prev => [...prev, {
        id: `ms_progress_${i}_${Date.now()}`,
        role: 'system' as const,
        content: `⏳ مرحله ${step.step_number} از ${steps.length}: ${step.description}`,
        timestamp: new Date(),
      }]);

      // ساختن پرامپت مرحله با context مراحل قبلی
      let stepPrompt = `${basePrompt}\n\n## ⚡ مرحله فعلی (${step.step_number} از ${steps.length}):\n${step.description}\n`;
      if (collectedAnalysis.length > 0) {
        stepPrompt += `\n## 📊 خلاصه مراحل قبلی:\n${collectedAnalysis.map((a, idx) => `مرحله ${idx + 1}: ${a.slice(0, 300)}`).join('\n')}\n`;
      }
      if (collectedActionFiles.length > 0) {
        // 🔑 پاس دادن محتوای واقعی فایل‌های مراحل قبلی
        stepPrompt += `\n## 📁 فایل‌های تغییر یافته تا الان (محتوای واقعی — بازنویسی نکن!):\n`;
        let contentBudget = 30000;
        for (const f of collectedActionFiles) {
          // modify_sections: نمایش sections بجای content
          if (f.operation === 'modify_sections' && f.sections) {
            const sectionsStr = JSON.stringify(f.sections, null, 2);
            stepPrompt += `\n### 📄 ${f.path} (modify_sections — ${f.sections.length} بخش):\n\`\`\`json\n${sectionsStr.slice(0, 3000)}\n\`\`\`\n`;
            contentBudget -= Math.min(sectionsStr.length, 3000);
            continue;
          }
          const fileContent = f.content || '';
          const truncated = fileContent.length > 5000 ? fileContent.slice(0, 5000) + '\n// ... (ادامه فایل موجود)' : fileContent;
          if (contentBudget <= 0) {
            stepPrompt += `- \`${f.path}\` (${f.operation}) — [محتوا به خاطر حجم نمایش داده نشد]\n`;
            continue;
          }
          stepPrompt += `\n### 📄 ${f.path} (${f.operation}):\n\`\`\`\n${truncated}\n\`\`\`\n`;
          contentBudget -= truncated.length;
        }
        stepPrompt += `\n⚠️ **قانون حیاتی**: اگر فایلی در لیست بالا هست و در مرحله فعلی هم باید تغییر کنه → تمام محتوای بالا حفظ شود و فقط تغییرات جدید اضافه شود. هرگز از صفر بازنویسی نکن!\n`;
      }
      stepPrompt += `\n## ⚠️ دستور: فقط مرحله ${step.step_number} رو انجام بده. تحلیل مختصر (حداکثر ۵ خط) + action_plan کامل.`;

      try {
        // تاریخچه چت برای context
        const chatHistory = inspectorChatMessages
          .filter(m => m.role === 'user' || m.role === 'assistant')
          .slice(-5)
          .map(m => ({ role: m.role, content: m.content?.slice(0, 200) }));

        const res = await fetch(`${API_BASE}/api/render/inspector/smart-chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            model_ids: modelIds,
            message: stepPrompt,
            chat_history: chatHistory,
            backend_logs: inspectorBackendLogs,
            frontend_url: inspectorFrontendUrl,
            previously_read_files: previouslyReadFiles,
          }),
        });

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let sseBuffer = '';
        let eventType = '';
        let stepResponseContent = '';
        let stepActionPlan: any = null;
        let stepFilesWereRead = false;

        if (!reader) throw new Error('No reader');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          sseBuffer += decoder.decode(value, { stream: true });
          const lines = sseBuffer.split('\n');
          sseBuffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ') && eventType) {
              try {
                const data = JSON.parse(line.slice(6));
                if (eventType === 'response') {
                  stepResponseContent = data.content || '';
                  stepActionPlan = data.action_plan || null;
                  stepFilesWereRead = data.files_were_read ?? false;
                  lastModelUsed = data.model_used || '';

                  // ذخیره فایل‌های خوانده‌شده
                  if (data.selected_file_paths?.length) {
                    setPreviouslyReadFiles(prev => {
                      const newF = data.selected_file_paths.filter((f: string) => !prev.includes(f));
                      return [...prev, ...newF];
                    });
                  }
                } else if (eventType === 'error') {
                  stepResponseContent = `❌ ${data.message}`;
                }
              } catch {}
              eventType = '';
            }
          }
        }

        // جمع‌آوری نتایج مرحله
        collectedAnalysis.push(stepResponseContent.slice(0, 500));
        if (!stepFilesWereRead) allFilesWereRead = false;

        if (stepActionPlan?.files?.length) {
          for (const file of stepActionPlan.files) {
            // اگه فایل قبلاً تغییر داده شده، جایگزین کن
            const existingIdx = collectedActionFiles.findIndex((f: any) => f.path === file.path);
            if (existingIdx >= 0) {
              collectedActionFiles[existingIdx] = file;
            } else {
              collectedActionFiles.push(file);
            }
          }
          if (stepActionPlan.commit_message) commitMessage = stepActionPlan.commit_message;
        }

        // نمایش نتیجه مرحله
        setInspectorChatMessages(prev => [...prev, {
          id: `ms_result_${i}_${Date.now()}`,
          role: 'assistant' as const,
          content: `**مرحله ${step.step_number}/${steps.length}: ${step.description}**\n\n${stepResponseContent}`,
          model_id: lastModelUsed,
          timestamp: new Date(),
          action_type: stepActionPlan?.files?.length ? 'smart_action' as any : undefined,
          action_plan: stepActionPlan,
          files_were_read: stepFilesWereRead,
          _is_multi_step_part: true,
        } as any]);

      } catch (err: any) {
        setInspectorChatMessages(prev => [...prev, {
          id: `ms_err_${i}_${Date.now()}`,
          role: 'system' as const,
          content: `❌ خطا در مرحله ${step.step_number}: ${err?.message || 'خطای ناشناخته'}`,
          timestamp: new Date(),
        }]);
      }
    }

    // 📊 گزارش نهایی ترکیبی
    const finalReportId = `ms_final_${Date.now()}`;
    const totalFiles = collectedActionFiles.length;
    let finalContent = `## 📊 گزارش نهایی — ${steps.length} مرحله کامل شد\n\n`;
    finalContent += `**فایل‌های تغییر یافته: ${totalFiles}**\n`;
    if (collectedActionFiles.length > 0) {
      finalContent += collectedActionFiles.map(f => `- \`${f.path}\` (${f.operation || 'modify'})`).join('\n');
      finalContent += '\n\n';
    }
    finalContent += collectedAnalysis.map((a, idx) => `**مرحله ${idx + 1}:** ${a.slice(0, 200)}`).join('\n\n');

    // پیام نهایی با action_plan ترکیبی
    const combinedActionPlan = totalFiles > 0 ? {
      files: collectedActionFiles,
      commit_message: commitMessage || `Multi-step fix: ${steps.map(s => s.description).join(', ')}`,
    } : null;

    setInspectorChatMessages(prev => [...prev, {
      id: finalReportId,
      role: 'assistant' as const,
      content: finalContent,
      model_id: lastModelUsed,
      timestamp: new Date(),
      action_type: combinedActionPlan ? 'smart_action' as any : undefined,
      action_plan: combinedActionPlan,
      files_were_read: allFilesWereRead,
      is_multi_step_report: true,
    } as any]);

    setInspectorChatLoading(false);
    setInspectorOpLock(false);
    setInspectorOpType(null);
  };

  // 🆕 ارسال پیام به AI
  const sendInspectorChat = async (overrideMessage?: string, _isRetry = false) => {
    // در حالت انتخاب خودکار، نیازی به انتخاب دستی مدل نیست
    const rawMessage = (overrideMessage || inspectorChatInput).trim();
    if (!rawMessage) return;
    if (!inspectorAutoSelect && inspectorSelectedModels.length === 0) return;

    if (!overrideMessage && !_isRetry) setInspectorChatInput('');
    setInspectorChatLoading(true);

    // 🧠 بهینه‌سازی پرامپت (اگر فعال باشه) — با نشانگر بارگذاری
    let userMessage = rawMessage;
    let wasEnhanced = false;
    if (inspectorSmartPrompt && rawMessage.length >= 10 && !_isRetry) {
      const _enhLoadId = `enhance_load_${Date.now()}`;
      setInspectorChatMessages(prev => [...prev, {
        id: _enhLoadId,
        role: 'system' as const,
        content: '🧠 در حال ساختارمند کردن پرامپت...',
        timestamp: new Date(),
      }]);
      const enhResult = await enhancePrompt(rawMessage, 'chat');
      // حذف پیام بارگذاری
      setInspectorChatMessages(prev => prev.filter(m => m.id !== _enhLoadId));
      userMessage = enhResult.text;
      wasEnhanced = enhResult.wasEnhanced;

      // 🔄 اگه مراحل تشخیص داده شده → اجرای مرحله‌ای
      if (wasEnhanced && enhResult.steps && enhResult.steps.length > 1) {
        setInspectorChatLoading(false);
        await executeMultiStep(rawMessage, enhResult.basePrompt || userMessage, enhResult.steps);
        return;
      }

      if (!wasEnhanced && enhResult.error) {
        setInspectorChatMessages(prev => [...prev, {
          id: `enhance_warn_${Date.now()}`,
          role: 'system' as const,
          content: `⚠️ ساختارمندسازی ناموفق: ${enhResult.error?.slice(0, 100)} — پیام اصلی ارسال می‌شود`,
          timestamp: new Date(),
        }]);
      }
    }
    if (!userMessage) return;

    // 🆕 در حالت retry: پیام‌های خطای قبلی پاک میشه + پیام سیستمی retry اضافه میشه
    if (_isRetry) {
      setInspectorChatMessages(prev => {
        const filtered = prev.filter(m => !m.id.startsWith('smart_fail_') && !m.id.startsWith('error_') && !m.id.startsWith('retry_'));
        return [...filtered, {
          id: `retry_req_${Date.now()}`,
          role: 'system' as const,
          content: '🔄 درخواست مجدد اصلاح — بدون ساختارمند مجدد',
          timestamp: new Date(),
        }];
      });
    } else {
      // اضافه کردن پیام کاربر به چت — اگر ساختارمند شده، متن ساختارمند اصلی نمایش داده میشه
      const userMsgId = `user_${Date.now()}`;
      setInspectorChatMessages(prev => [...prev, {
        id: userMsgId,
        role: 'user',
        content: wasEnhanced ? userMessage : rawMessage,
        timestamp: new Date(),
        ...(wasEnhanced ? { original_prompt: rawMessage, enhanced_prompt: userMessage } : {}),
        ...(inspectorReplyTo ? { reply_to_id: inspectorReplyTo.id, reply_to_content: inspectorReplyTo.content?.slice(0, 100) } : {}),
      } as any]);

      // ذخیره پیام کاربر در دیتابیس
      if (inspectorSessionIdRef.current) {
        const _userExtra: Record<string, any> = {};
        if (wasEnhanced) { _userExtra.enhanced_prompt = userMessage; _userExtra.original_prompt = rawMessage; }
        if (inspectorReplyTo) { _userExtra.reply_to_id = inspectorReplyTo.id; _userExtra.reply_to_content = inspectorReplyTo.content?.slice(0, 100); }
        fetch(`${API_BASE}/api/render/inspector/session/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: inspectorSessionIdRef.current,
            role: 'user',
            content: wasEnhanced ? userMessage : rawMessage,
            ...(Object.keys(_userExtra).length > 0 ? { extra_data: _userExtra } : {}),
          })
        }).catch(err => console.error('Save user msg failed:', err));
      }
    }

    try {
      // آماده‌سازی فایل‌ها (اگر موجود باشد)
      const projectFiles = files.slice(0, 5).map(f => ({
        path: f.path,
        content: '' // محتوا بعداً می‌تواند از فایل‌های باز شده خوانده شود
      }));

      // 🧠 تشخیص نوع پیام: ویژوال فقط برای پیام‌های کوتاه auto-select
      // هر چیز دیگه‌ای → smart-chat SSE
      const isLongMessage = userMessage.length > 200;
      const shouldUseVision = inspectorAutoSelect && !isLongMessage && isVisualTask(userMessage) && inspectorFrontendUrl;

      if (shouldUseVision) {
        // 🔍 تشخیص ویژوال: Ctrl+F + AI interact (فقط auto-select + پیام کوتاه)
        const targetText = extractTargetText(userMessage);
        setInspectorChatMessages(prev => [...prev, {
          id: `system_${Date.now()}`,
          role: 'assistant',
          content: `🔍 جستجوی "${targetText}" در صفحه...`,
          timestamp: new Date()
        }]);

        try {
          const searchRes = await fetch(`${API_BASE}/api/render/inspector/find-and-click?url=${encodeURIComponent(inspectorFrontendUrl)}&search_text=${encodeURIComponent(targetText)}`, {
            method: 'POST'
          });
          const searchData = await searchRes.json();
          setInspectorChatMessages(prev => prev.filter(m => !m.id.startsWith('system_')));

          if (searchData.success) {
            const pos = searchData.position;
            if (pos) {
              setInspectorVirtualCursor({ x: pos.percent_x, y: pos.percent_y, visible: true, model_id: `🎯 ${searchData.found?.slice(0, 20) || targetText}` });
              setTimeout(() => setInspectorVirtualCursor(prev => ({ ...prev, visible: false })), 3000);
            }
            setInspectorChatMessages(prev => [...prev, {
              id: `assistant_${Date.now()}`, role: 'assistant',
              content: `✅ **پیدا شد!**\n\n🎯 "${searchData.found}"\n📍 (${pos?.percent_x?.toFixed(1)}%, ${pos?.percent_y?.toFixed(1)}%)\n📊 ${searchData.found_count} مورد${searchData.url_changed ? '\n🔄 صفحه تغییر کرد' : ''}`,
              timestamp: new Date()
            }]);
            if (searchData.new_url && searchData.new_url !== inspectorFrontendUrl) setInspectorFrontendUrl(searchData.new_url);
            setInspectorChatLoading(false);
            return;
          }
          if (searchData.found_count === 0) {
            // بجای نمایش "پیدا نشد" و متوقف شدن، به smart-chat ادامه بده
            console.log('Visual search found nothing, falling through to smart-chat...');
            setInspectorChatMessages(prev => prev.filter(m => !m.id.startsWith('system_')));
            // ادامه به smart-chat SSE (پایین‌تر)
          }
        } catch (searchError) {
          console.log('Ctrl+F failed, falling back to AI...', searchError);
          setInspectorChatMessages(prev => prev.filter(m => !m.id.startsWith('system_')));
        }

        // 🤖 فالبک: AI interact
        setInspectorChatMessages(prev => [...prev, {
          id: `system_${Date.now()}`, role: 'assistant',
          content: '🤖 AI در حال تحلیل...', timestamp: new Date()
        }]);

        const visionRes = await fetch(`${API_BASE}/api/render/inspector/ai-interact`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task: userMessage, url: inspectorFrontendUrl, model_id: null, max_steps: 15 })
        });
        const visionData = await visionRes.json();
        setInspectorChatMessages(prev => prev.filter(m => !m.id.startsWith('system_')));

        if (visionData.success) {
          const selectedModel = visionData.selected_model || 'AI';
          const actionsText = (visionData.actions || []).map((a: any) => `${a.status === 'done' ? '✅' : '❌'} ${a.message || a.action}`).join('\n');
          setInspectorChatMessages(prev => [...prev, {
            id: `assistant_${Date.now()}`, role: 'assistant',
            content: `🤖 **انجام شد**\n\n🧠 مدل: **${selectedModel}**\n${actionsText}`,
            model_id: selectedModel, timestamp: new Date()
          }]);
          if (visionData.cursor_positions?.length > 0) animateCursorSequence(visionData.cursor_positions);
          if (visionData.final_url && visionData.final_url !== inspectorFrontendUrl) setInspectorFrontendUrl(visionData.final_url);
        } else {
          setInspectorChatMessages(prev => [...prev, {
            id: `error_${Date.now()}`, role: 'assistant',
            content: `❌ خطا: ${visionData.error || 'ناشناخته'}`, timestamp: new Date()
          }]);
        }

      // 🧠 حالت چت هوشمند - smart-chat SSE برای تمام پیام‌های غیر ویژوال
      } else {
        // ساخت تاریخچه غنی (200 پیام آخر)
        const chatHistory = inspectorChatMessages
          .filter(m => {
            if (m.role === 'system' && m.content?.startsWith('🔍 شروع')) return true;
            if (m.role === 'system' && m.content?.startsWith('🔧 شروع')) return true;
            if (m.role === 'system' && m.content?.startsWith('⏹')) return true;
            if (m.role === 'system' && m.content?.startsWith('❌')) return true;
            if ((m as any).action_type === 'investigate_report') return true;
            if ((m as any).action_type === 'error' || (m as any).action_type === 'console-error') return true;
            if (m.role === 'user') return true;
            if (m.role === 'assistant' && !(m.content?.startsWith('🔍 در حال'))) return true;
            if (m.role === 'action' && (m as any).backend_verified === false) return true;
            return false;
          })
          .slice(-200)
          .map(m => ({
            role: m.role === 'action' ? 'system' : m.role,
            content: (m as any).action_type === 'investigate_report'
              ? `[گزارش بررسی از ${m.model_id || 'AI'}]:\n${m.content}`
              : (m as any).action_type === 'error' || (m as any).action_type === 'console-error'
                ? `[خطای فرانت‌اند]: ${m.content}`
                : m.role === 'action'
                  ? `[اکشن کاربر - ${(m as any).action_type}]: ${m.content}${(m as any).backend_verified === false ? ' (تأیید نشده ✕)' : ''}`
                  : m.content
          }));

        // ساخت context ریپلای (بدون محدودیت 50 تایی - از کل پیام‌ها)
        let replyToPayload: any = undefined;
        if (inspectorReplyTo) {
          const replyMsgIdx = inspectorChatMessages.findIndex(m => m.id === inspectorReplyTo.id);
          const contextMessages: Array<{role: string; content: string}> = [];
          if (replyMsgIdx >= 0) {
            // 5 پیام قبل و 5 پیام بعد
            const start = Math.max(0, replyMsgIdx - 5);
            const end = Math.min(inspectorChatMessages.length, replyMsgIdx + 6);
            for (let i = start; i < end; i++) {
              if (i === replyMsgIdx) continue; // خود پیام ریپلای شده جدا ارسال میشه
              const cm = inspectorChatMessages[i];
              contextMessages.push({
                role: cm.role === 'action' ? 'system' : cm.role,
                content: cm.content,
              });
            }
          }
          replyToPayload = {
            message_id: inspectorReplyTo.id,
            content: inspectorReplyTo.content,
            role: inspectorReplyTo.role,
            model_id: inspectorReplyTo.model_id,
            context_messages: contextMessages,
          };
        }

        // مدل‌ها: دستی یا خودکار
        const modelIds = inspectorAutoSelect ? [] : inspectorSelectedModels;

        // 🔒 قفل
        setInspectorOpLock(true);
        setInspectorOpType('investigate');
        inspectorOpAbortRef.current = new AbortController();

        const res = await fetch(`${API_BASE}/api/render/inspector/smart-chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            model_ids: modelIds,
            message: userMessage,
            chat_history: chatHistory,
            backend_logs: inspectorBackendLogs,
            frontend_url: inspectorFrontendUrl,
            reply_to: replyToPayload,
            previously_read_files: previouslyReadFiles,
          }),
          signal: inspectorOpAbortRef.current?.signal,
        });

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let sseBuffer = '';
        let responseReceived = false; // 🆕 ردیابی دریافت پاسخ
        let lastErrorMessage = ''; // 🆕 ذخیره آخرین خطا برای نمایش در done
        if (!reader) throw new Error('No reader');

        let eventType = '';  // 🔴 باید بیرون while باشه تا بین chunk ها حفظ بشه
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          sseBuffer += decoder.decode(value, { stream: true });
          const lines = sseBuffer.split('\n');
          sseBuffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ') && eventType) {
              try {
                const data = JSON.parse(line.slice(6));

                if (eventType === 'progress') {
                  // ذخیره task_key برای اتصال مجدد و لغو
                  if (data.task_key && data.step === 'batch_task_key') {
                    inspectorBatchTaskKeyRef.current = data.task_key;
                    try {
                      sessionStorage.setItem('inspector_batch_task', JSON.stringify({
                        task_key: data.task_key,
                        project_id: projectId,
                        message: userMessage,
                        timestamp: Date.now(),
                      }));
                    } catch {}
                    // این event رو نمایش نده — فقط ذخیره کردن
                  }
                  setInspectorChatMessages(prev => [...prev, {
                    id: `smart_p_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
                    role: 'system' as const,
                    content: data.message,
                    timestamp: new Date(),
                  }]);
                } else if (eventType === 'error') {
                  lastErrorMessage = data.message || 'خطای ناشناخته';
                  setInspectorChatMessages(prev => [...prev, {
                    id: `smart_err_${Date.now()}`,
                    role: 'assistant' as const,
                    content: `❌ ${data.message}${data.detail ? '\n\n📊 ' + data.detail : ''}`,
                    timestamp: new Date(),
                  }]);
                } else if (eventType === 'response') {
                  responseReceived = true;
                  // پاکسازی batch task — کار تمام شد
                  inspectorBatchTaskKeyRef.current = null;
                  try { sessionStorage.removeItem('inspector_batch_task'); } catch {}
                  const responseId = `smart_response_${Date.now()}`;

                  // ذخیره فایل‌های خوانده‌شده برای هدایت AI به فایل‌های جدید در پیام‌های بعدی
                  if (data.selected_file_paths && Array.isArray(data.selected_file_paths) && data.selected_file_paths.length > 0) {
                    setPreviouslyReadFiles(prev => {
                      const newFiles = data.selected_file_paths.filter((f: string) => !prev.includes(f));
                      return [...prev, ...newFiles];
                    });
                  }

                  setInspectorChatMessages(prev => [...prev, {
                    id: responseId,
                    role: 'assistant' as const,
                    content: data.content,
                    model_id: data.model_used,
                    timestamp: new Date(),
                    tokens_used: data.tokens_used,
                    action_type: (data.type === 'action' || data.has_action) ? 'smart_action' as any : undefined,
                    action_plan: data.action_plan,
                    files_were_read: data.files_were_read ?? false,
                    selected_file_paths: data.selected_file_paths || [],
                    original_message: userMessage,
                  } as any]);

                  // 🔓 آزاد کردن قفل
                  setInspectorOpLock(false);
                  setInspectorOpType(null);
                } else if (eventType === 'timeout_warning') {
                  // هشدار تمدید مهلت مدل
                  setInspectorChatMessages(prev => [...prev, {
                    id: `smart_tw_${Date.now()}`,
                    role: 'system' as const,
                    content: data.message || `⏱️ مدل نیاز به زمان بیشتری دارد... مهلت تمدید شد.`,
                    timestamp: new Date(),
                  }]);
                } else if (eventType === 'fields_in_use') {
                  // هایلایت فیلدهای در حال استفاده
                  setPromptFieldsHighlighted(data.field_ids || []);
                  setInspectorChatMessages(prev => [...prev, {
                    id: `fields_use_${Date.now()}`,
                    role: 'system' as const,
                    content: data.message || `📋 ${data.count} فیلد دستور/حافظه/آموزش در حال استفاده`,
                    timestamp: new Date(),
                  }]);
                } else if (eventType === 'fields_done') {
                  // پایان هایلایت فیلدها (بعد از ۳ ثانیه)
                  setTimeout(() => setPromptFieldsHighlighted([]), 3000);
                } else if (eventType === 'heartbeat') {
                  // 🆕 heartbeat برای جلوگیری از قطع اتصال - فقط مصرف میشه
                  // اختیاری: آخرین پیام progress رو آپدیت کن
                  setInspectorChatMessages(prev => {
                    const lastProgressIdx = prev.findLastIndex(m => m.id.startsWith('smart_p_'));
                    if (lastProgressIdx >= 0) {
                      const updated = [...prev];
                      updated[lastProgressIdx] = {
                        ...updated[lastProgressIdx],
                        content: updated[lastProgressIdx].content.replace(/⏳.*$/, '').trimEnd() + ' ⏳',
                      };
                      return updated;
                    }
                    return prev;
                  });
                } else if (eventType === 'done') {
                  // 🆕 اگر استریم تمام شد ولی پاسخی دریافت نشد → خطای تحلیل
                  if (!responseReceived && !lastErrorMessage) {
                    // هیچ خطایی هم نیامد = مشکل ناشناخته
                    setInspectorChatMessages(prev => [...prev, {
                      id: `smart_fail_${Date.now()}`,
                      role: 'assistant' as const,
                      content: '⚠️ تحلیل بدون نتیجه پایان یافت. ممکن است مدل AI دچار خطا شده باشد. لطفاً دوباره تلاش کنید یا مدل دیگری انتخاب نمایید.',
                      timestamp: new Date(),
                    }]);
                    setInspectorOpLock(false);
                    setInspectorOpType(null);
                  }
                }
              } catch (e) {
                // ignore parse errors
              }
              eventType = '';
            }
          }
        }

        // 🆕 اگر استریم تمام شد ولی هنوز پاسخی نیامده (بدون done event)
        if (!responseReceived) {
          if (!_isRetry) {
            // 🆕 تلاش خودکار — بک‌اند یافته‌های قبلی رو از کش برمیگردونه
            setInspectorChatMessages(prev => [...prev, {
              id: `retry_${Date.now()}`,
              role: 'assistant' as const,
              content: '🔄 اتصال قطع شد — تلاش خودکار برای ادامه از جایی که متوقف شده...',
              timestamp: new Date(),
            }]);
            setTimeout(() => sendInspectorChat(userMessage, true), 2000);
            return;
          }
          // اگر retry هم جواب نداد — پیام خطا نشون بده
          setInspectorChatMessages(prev => {
            const hasFailMsg = prev.some(m => m.id.startsWith('smart_fail_'));
            if (!hasFailMsg) {
              return [...prev, {
                id: `smart_fail_${Date.now()}`,
                role: 'assistant' as const,
                content: '⚠️ ارتباط با سرور قطع شد و گزارشی دریافت نشد. لطفاً دوباره تلاش کنید.',
                timestamp: new Date(),
              }];
            }
            return prev;
          });
        }

        // پاک کردن ریپلای بعد از ارسال
        if (inspectorReplyTo) setInspectorReplyTo(null);
      }
    } catch (err: any) {
      console.error('Error sending inspector chat:', err);
      if (err.name !== 'AbortError') {
        const isNetworkError = err.message?.includes('network') || err.message?.includes('ERR_QUIC') || err.message?.includes('Failed to fetch');
        if (isNetworkError && !_isRetry) {
          // 🆕 خطای شبکه → تلاش خودکار (بک‌اند یافته‌های قبلی رو کش کرده)
          setInspectorChatMessages(prev => {
            const filtered = prev.filter(m => !m.id.startsWith('system_') && !m.id.startsWith('error_'));
            return [...filtered, {
              id: `retry_${Date.now()}`,
              role: 'assistant',
              content: '🔄 اتصال قطع شد — تلاش خودکار برای ادامه از جایی که متوقف شده...',
              timestamp: new Date()
            }];
          });
          setTimeout(() => sendInspectorChat(userMessage, true), 3000);
          return;
        }
        // retry هم جواب نداد یا خطای غیرشبکه‌ای
        setInspectorChatMessages(prev => {
          const filtered = prev.filter(m => !m.id.startsWith('system_') && !m.id.startsWith('retry_'));
          return [...filtered, {
            id: `error_${Date.now()}`,
            role: 'assistant',
            content: isNetworkError
              ? '❌ ارتباط با سرور قطع شد. تلاش خودکار هم ناموفق بود. لطفاً دوباره تلاش کنید.'
              : `❌ خطا در اتصال به سرور: ${err.message?.slice(0, 100) || 'ناشناخته'}`,
            timestamp: new Date()
          }];
        });
      }
    } finally {
      setInspectorChatLoading(false);
      // 🔧 همیشه قفل رو آزاد کن (رفع باگ stale closure)
      setInspectorOpLock(false);
      setInspectorOpType(null);
    }
  };

  // 🆕 Toggle انتخاب مدل
  const toggleInspectorModel = (modelId: string) => {
    setInspectorSelectedModels(prev => {
      if (prev.includes(modelId)) {
        return prev.filter(id => id !== modelId);
      } else {
        return [...prev, modelId];
      }
    });
  };

  // 📸 عکس‌برداری از صفحه پیش‌نمایش

  // 🔀 تبدیل URL پروکسی به URL واقعی (و بالعکس)
  const _proxyPrefix = `/api/render/inspector/proxy/${projectId}`;
  const _getProxyUrl = (actualUrl: string | null): string => {
    if (!actualUrl) return '';
    try {
      const u = new URL(actualUrl);
      // مسیر نسبی — Next.js rewrite خودکار به بکند پروکسی میکنه (same-origin)
      return `${_proxyPrefix}${u.pathname}${u.search}${u.hash}`;
    } catch {
      return `${_proxyPrefix}/`;
    }
  };
  const _proxyToActual = (proxyPath: string): string | null => {
    if (!inspectorBaseUrl) return null;
    const base = inspectorBaseUrl.replace(/\/$/, '');
    // پروکسی path مثل /api/render/inspector/proxy/{id}/about → URL واقعی
    const idx = proxyPath.indexOf(_proxyPrefix);
    if (idx !== -1) {
      const rest = proxyPath.slice(idx + _proxyPrefix.length) || '/';
      return base + rest;
    }
    // SPA pushState — مسیر مستقیم مثل /about (بدون prefix proxy)
    // اگر مسیر با proxy شروع نمیشه ولی ما base داریم → ساخت URL واقعی
    return base + (proxyPath.startsWith('/') ? proxyPath : '/' + proxyPath);
  };
  // خواندن URL واقعی از iframe (same-origin — بدون خطای cross-origin)
  const _readIframeActualUrl = (): string | null => {
    try {
      const loc = inspectorIframeRef.current?.contentWindow?.location;
      if (!loc || loc.href === 'about:blank') return null;
      const fullPath = loc.pathname + loc.search + loc.hash;
      return _proxyToActual(fullPath);
    } catch { return null; }
  };

  const takeVisualDebugScreenshot = async () => {
    // 🔀 خواندن URL واقعی از iframe (same-origin از طریق proxy)
    let _currentPageUrl = _readIframeActualUrl() || inspectorFrontendUrl || '';
    if (!_currentPageUrl) return;
    setVisualDebugTakingScreenshot(true);
    try {
      // 🔴 ابتدا لاگ‌های تازه بکند رو مستقیم از Render API بگیر
      let freshBackendLogs: Array<{ level: string; message: string; timestamp: string; service_name: string }> = [];
      try {
        const backendServiceIds = inspectorServices
          .filter(s => s.role === 'backend' || s.role === 'unified' || !s.role)
          .map(s => s.id);
        if (backendServiceIds.length > 0) {
          // اول از Render API لاگ‌های جدید رو fetch کن
          await Promise.all(backendServiceIds.map(id =>
            fetch(`${API_BASE}/api/render/logs/fetch?service_id=${id}&limit=50`, { method: 'POST' })
              .catch(() => null)
          ));
          // بعد از DB بخون
          const params = new URLSearchParams();
          backendServiceIds.forEach(id => params.append('service_ids', id));
          params.append('minutes', '30');
          params.append('limit', '50');
          const logsRes = await fetch(`${API_BASE}/api/render/logs?${params}`);
          const logsData = await logsRes.json();
          if (logsData.success && logsData.logs) {
            freshBackendLogs = logsData.logs;
            setInspectorBackendLogs(logsData.logs); // state رو هم آپدیت کن
          }
        }
      } catch (err) {
        console.warn('Failed to fetch fresh backend logs:', err);
        // fallback به state فعلی
        freshBackendLogs = [...inspectorBackendLogs];
      }

      // 🔀 DOM snapshot از iframe (same-origin) — برای SPA هایی که URL تغییر نمیکنه
      let _capturedHtml: string | null = null;
      try {
        const iframeDoc = inspectorIframeRef.current?.contentDocument;
        if (iframeDoc) {
          const html = iframeDoc.documentElement.outerHTML;
          if (html && html.length < 5_000_000) _capturedHtml = html; // حداکثر 5MB
        }
      } catch { /* اگر خطا شد ادامه بده با روش عادی */ }

      const res = await fetch(`${API_BASE}/api/render/inspector/screenshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          url: _currentPageUrl,
          viewport_width: 1280,
          viewport_height: 720,
          html_content: _capturedHtml,
        }),
      });
      const data = await res.json();
      if (data.success && data.screenshot) {
        // 📦 Snapshot current logs and URLs at capture time
        // اولویت: URL خوانده شده از iframe (تبدیل شده از proxy) → بعد page_info از Playwright
        const _playwrightUrl = data.page_info?.url || '';
        const capturePageUrl = _currentPageUrl || _playwrightUrl;
        const captureConsoleLogs = [...importedProjectConsoleLogs].slice(-50).map(l => ({
          level: l.level, message: l.message, timestamp: l.timestamp, source: l.source
        }));
        // 🔴 از لاگ‌های تازه استفاده کن (نه state قدیمی)
        const captureBackendLogs = freshBackendLogs.slice(-30).map(l => ({
          level: l.level, message: l.message, timestamp: l.timestamp, service_name: l.service_name
        }));

        // 🔗 Extract related URLs AND backend API paths from logs
        const captureUrls: string[] = [];
        const captureApiPaths: string[] = [];
        if (_currentPageUrl) captureUrls.push(_currentPageUrl);
        if (capturePageUrl && !captureUrls.includes(capturePageUrl)) captureUrls.push(capturePageUrl);

        // 🆕 اضافه کردن URL سرویس‌های بکند پروژه
        inspectorServices.forEach(svc => {
          if (svc.url && !captureUrls.includes(svc.url)) captureUrls.push(svc.url);
        });

        // Extract URLs and API endpoints from console logs
        const allLogMessages = [
          ...importedProjectConsoleLogs.slice(-50).map(l => l.message),
          ...freshBackendLogs.slice(-30).map(l => l.message),
        ];
        allLogMessages.forEach(msg => {
          // Full URLs
          const urlMatch = msg.match(/https?:\/\/[^\s"'<>)]+/g);
          if (urlMatch) urlMatch.forEach(u => { if (!captureUrls.includes(u) && captureUrls.length < 20) captureUrls.push(u); });
          // API endpoint paths: /api/..., /v1/..., /graphql, etc.
          const apiMatch = msg.match(/(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\/[^\s"'<>]+)/gi);
          if (apiMatch) apiMatch.forEach(m => {
            const path = m.replace(/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/i, '').trim();
            if (!captureApiPaths.includes(path) && captureApiPaths.length < 20) captureApiPaths.push(path);
          });
          // Direct path patterns: /api/... or fetch("/api/...")
          const pathMatch = msg.match(/\/api\/[^\s"'<>)]+/g);
          if (pathMatch) pathMatch.forEach(p => { if (!captureApiPaths.includes(p) && captureApiPaths.length < 20) captureApiPaths.push(p); });
        });

        // Also extract route-like patterns from the page URL for mapping frontend→backend
        if (capturePageUrl) {
          try {
            const pageRoute = new URL(capturePageUrl).pathname;
            if (pageRoute && pageRoute !== '/' && !captureApiPaths.includes(pageRoute)) {
              captureApiPaths.push(pageRoute);
            }
          } catch {}
        }

        setVisualDebugScreenshots(prev => [...prev, {
          id: `ss_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
          base64: data.screenshot,
          timestamp: new Date(),
          pageUrl: capturePageUrl,
          consoleLogs: captureConsoleLogs,
          backendLogs: captureBackendLogs,
          relatedUrls: captureUrls,
          apiPaths: captureApiPaths,
        }]);
        // فعال کردن حالت دیباگ بصری
        if (!visualDebugMode) setVisualDebugMode(true);
      } else {
        alert(data.error || 'خطا در عکس‌برداری');
      }
    } catch (err: any) {
      alert(`خطا: ${err.message || 'ناشناخته'}`);
    } finally {
      setVisualDebugTakingScreenshot(false);
    }
  };

  // 📸 بارگذاری مدل‌های Vision
  const loadVisionModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/vision-models`);
      const data = await res.json();
      if (data.success) {
        setVisualDebugVisionModels(data.models);
        // پیش‌انتخاب مدل‌های فعال و پیشنهادی
        const recommended = data.models.filter((m: any) => m.enabled && m.recommended).map((m: any) => m.id);
        if (recommended.length > 0) {
          setVisualDebugSelectedModels(recommended.slice(0, 1));
        } else {
          const enabled = data.models.filter((m: any) => m.enabled).map((m: any) => m.id);
          setVisualDebugSelectedModels(enabled.slice(0, 1));
        }
      }
    } catch (err) {
      console.error('Failed to load vision models:', err);
    }
  };

  // 📸 شروع دیباگ بصری - نمایش انتخاب مدل
  const startVisualDebugModelSelection = () => {
    loadVisionModels();
    setVisualDebugModelSelection(true);
  };

  // 📸 ارسال درخواست دیباگ بصری
  const sendVisualDebug = async () => {
    if (visualDebugScreenshots.length === 0) return;
    if (visualDebugSelectedModels.length === 0) {
      alert('لطفاً حداقل یک مدل Vision انتخاب کنید');
      return;
    }

    // 🧠 بهینه‌سازی توضیح دیباگ بصری (اگر فعال باشه) — با نشانگر بارگذاری
    let enhancedDescription = visualDebugDescription || '';
    let vdWasEnhanced = false;
    let vdSteps: { step_number: number; description: string }[] = [];
    let vdBasePrompt = '';
    if (visualDebugDescription && inspectorSmartPrompt && visualDebugDescription.length >= 10) {
      setInspectorChatMessages(prev => [...prev, {
        id: `vd_enhance_load_${Date.now()}`,
        role: 'system' as const,
        content: '🧠 در حال ساختارمند کردن توضیح دیباگ بصری...',
        timestamp: new Date(),
      }]);
      const vdEnhResult = await enhancePrompt(visualDebugDescription, 'visual_debug');
      setInspectorChatMessages(prev => prev.filter(m => !m.id.startsWith('vd_enhance_load_')));
      vdWasEnhanced = vdEnhResult.wasEnhanced;
      vdBasePrompt = vdEnhResult.basePrompt || vdEnhResult.text;
      if (vdEnhResult.steps && vdEnhResult.steps.length > 1) {
        vdSteps = vdEnhResult.steps;
        // برای visual debug: فقط مرحله اول رو ارسال کن + خلاصه کلی
        enhancedDescription = `${vdBasePrompt}\n\n⚡ لطفاً فقط مرحله اول رو انجام بده:\n${vdSteps[0].description}\n\n⚠️ تحلیل مختصر (۵ خط) + action_plan کامل فقط برای مرحله اول.`;
      } else {
        enhancedDescription = vdEnhResult.text;
      }
      if (!vdWasEnhanced && vdEnhResult.error) {
        setInspectorChatMessages(prev => [...prev, {
          id: `vd_enhance_warn_${Date.now()}`,
          role: 'system' as const,
          content: `⚠️ ساختارمندسازی ناموفق: ${vdEnhResult.error?.slice(0, 100)} — توضیح اصلی ارسال می‌شود`,
          timestamp: new Date(),
        }]);
      }
      // اگه مراحل وجود داره، نقشه رو نشون بده
      if (vdSteps.length > 1) {
        setInspectorChatMessages(prev => [...prev, {
          id: `vd_steps_plan_${Date.now()}`,
          role: 'system' as const,
          content: `📋 درخواست به ${vdSteps.length} مرحله تجزیه شد:\n${vdSteps.map(s => `  ${s.step_number}. ${s.description}`).join('\n')}\n\n▶️ مرحله ۱ با مدل بصری...`,
          timestamp: new Date(),
        }]);
      }
    }

    setVisualDebugLoading(true);
    setVisualDebugModelSelection(false);
    setInspectorOpLock(true);
    setInspectorOpType('investigate');
    inspectorOpAbortRef.current = new AbortController();

    // 📦 Build screenshot packs - each screenshot with its own logs/URLs/API paths
    const screenshotPacks = visualDebugScreenshots.map((ss, idx) => ({
      index: idx + 1,
      base64: ss.base64,
      pageUrl: ss.pageUrl,
      timestamp: ss.timestamp.toISOString(),
      consoleLogs: ss.consoleLogs || [],
      backendLogs: ss.backendLogs || [],
      relatedUrls: ss.relatedUrls || [],
      apiPaths: ss.apiPaths || [],
    }));

    // اضافه کردن پیام کاربر به چت — اگر ساختارمند شده، متن ساختارمند نمایش داده میشه
    const userMsgId = `vd_user_${Date.now()}`;
    const vdDisplayDesc = vdWasEnhanced ? enhancedDescription : visualDebugDescription;
    setInspectorChatMessages(prev => [...prev, {
      id: userMsgId,
      role: 'user' as const,
      content: `📸 دیباگ بصری: ${visualDebugScreenshots.length} عکس${vdDisplayDesc ? `\n💬 ${vdDisplayDesc}` : ''}`,
      timestamp: new Date(),
      ...(vdWasEnhanced ? { original_prompt: visualDebugDescription, enhanced_prompt: enhancedDescription } : {}),
      visual_debug_packs: screenshotPacks.map(p => ({
        index: p.index,
        base64: p.base64,
        pageUrl: p.pageUrl,
        timestamp: p.timestamp,
        consoleLogsCount: p.consoleLogs.length,
        backendLogsCount: p.backendLogs.length,
        consoleLogs: p.consoleLogs,
        backendLogs: p.backendLogs,
        relatedUrls: p.relatedUrls,
        apiPaths: p.apiPaths,
        errorCount: p.consoleLogs.filter(l => l.level === 'error').length + p.backendLogs.filter(l => l.level === 'error').length,
      })),
    } as any]);

    // ذخیره پیام کاربر دیباگ بصری در دیتابیس
    if (inspectorSessionIdRef.current) {
      const _vdUserExtra: Record<string, any> = {
        visual_debug_packs: screenshotPacks.map(p => ({
          index: p.index,
          base64: p.base64,
          pageUrl: p.pageUrl,
          timestamp: p.timestamp,
          consoleLogsCount: p.consoleLogs.length,
          backendLogsCount: p.backendLogs.length,
          consoleLogs: p.consoleLogs,
          backendLogs: p.backendLogs,
          relatedUrls: p.relatedUrls,
          apiPaths: p.apiPaths,
          errorCount: p.consoleLogs.filter((l: any) => l.level === 'error').length + p.backendLogs.filter((l: any) => l.level === 'error').length,
        })),
      };
      if (vdWasEnhanced) { _vdUserExtra.enhanced_prompt = enhancedDescription; _vdUserExtra.original_prompt = visualDebugDescription; }
      fetch(`${API_BASE}/api/render/inspector/session/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: inspectorSessionIdRef.current,
          role: 'user',
          content: `📸 دیباگ بصری: ${visualDebugScreenshots.length} عکس${visualDebugDescription ? `\n💬 ${visualDebugDescription}` : ''}`,
          extra_data: _vdUserExtra,
        })
      }).catch(err => console.error('Save VD user msg failed:', err));
    }

    // جمع‌آوری همه آدرس‌های مرتبط (union از همه پک‌ها)
    const allRelatedUrls: string[] = [];
    screenshotPacks.forEach(p => {
      p.relatedUrls.forEach(u => { if (!allRelatedUrls.includes(u) && allRelatedUrls.length < 30) allRelatedUrls.push(u); });
    });

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/visual-debug`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          model_ids: visualDebugSelectedModels,
          screenshots: screenshotPacks.map(p => p.base64),
          screenshot_packs: screenshotPacks.map(p => ({
            index: p.index,
            pageUrl: p.pageUrl,
            timestamp: p.timestamp,
            console_logs: p.consoleLogs,
            backend_logs: p.backendLogs,
            related_urls: p.relatedUrls,
            api_paths: p.apiPaths,
          })),
          console_logs: importedProjectConsoleLogs.slice(-50).map(l => ({
            level: l.level, message: l.message, timestamp: l.timestamp, source: l.source,
          })),
          backend_logs: inspectorBackendLogs.slice(-30).map(l => ({
            level: l.level, message: l.message, timestamp: l.timestamp, service_id: l.service_name,
          })),
          related_urls: allRelatedUrls,
          user_description: enhancedDescription || undefined,
          previously_read_files: previouslyReadFiles,
        }),
        signal: inspectorOpAbortRef.current?.signal,
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = '';
      let responseReceived = false;
      if (!reader) throw new Error('No reader');

      // 🔑 ذخیره داده‌های پاسخ مرحله اول برای ادامه مراحل بعدی
      let vdStep1Content = '';
      let vdStep1ActionPlan: any = null;
      let vdStep1ModelUsed = '';
      let vdStep1SelectedFiles: string[] = [];
      const _isMultiStep = vdSteps.length > 1;

      let eventType = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split('\n');
        sseBuffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));

              if (eventType === 'progress') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `vd_p_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
                  role: 'system' as const,
                  content: data.message,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'error') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `vd_err_${Date.now()}`,
                  role: 'assistant' as const,
                  content: `❌ ${data.message}${data.detail ? '\n📊 ' + data.detail : ''}`,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'response') {
                responseReceived = true;
                // ذخیره داده‌های مرحله اول
                vdStep1Content = data.content || '';
                vdStep1ActionPlan = data.action_plan || null;
                vdStep1ModelUsed = data.model_used || '';
                vdStep1SelectedFiles = data.selected_file_paths || [];

                setInspectorChatMessages(prev => [...prev, {
                  id: `vd_response_${Date.now()}`,
                  role: 'assistant' as const,
                  content: _isMultiStep ? `**مرحله ۱/${vdSteps.length}: ${vdSteps[0].description}**\n\n${data.content}` : data.content,
                  model_id: data.model_used,
                  timestamp: new Date(),
                  tokens_used: data.tokens_used,
                  action_type: data.has_action ? 'smart_action' as any : undefined,
                  action_plan: data.action_plan,
                  ...(_isMultiStep
                    ? { _is_multi_step_part: true }
                    : { is_visual_debug_report: true }),
                  original_user_description: visualDebugDescription || '',
                } as any]);
                if (!_isMultiStep) {
                  setInspectorOpLock(false);
                  setInspectorOpType(null);
                }
              } else if (eventType === 'fields_in_use') {
                setPromptFieldsHighlighted(data.field_ids || []);
                setInspectorChatMessages(prev => [...prev, {
                  id: `vd_fields_${Date.now()}`,
                  role: 'system' as const,
                  content: data.message || '📋 پرامپت دیباگ بصری در حال استفاده',
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'fields_done') {
                setTimeout(() => setPromptFieldsHighlighted([]), 3000);
              } else if (eventType === 'heartbeat') {
                // keep-alive
              } else if (eventType === 'done') {
                if (!responseReceived) {
                  setInspectorChatMessages(prev => [...prev, {
                    id: `vd_fail_${Date.now()}`,
                    role: 'assistant' as const,
                    content: '⚠️ تحلیل بصری بدون نتیجه پایان یافت. لطفاً دوباره تلاش کنید.',
                    timestamp: new Date(),
                  }]);
                  setInspectorOpLock(false);
                  setInspectorOpType(null);
                }
              }
            } catch (e) {}
            eventType = '';
          }
        }
      }

      // پاکسازی بعد از ارسال موفق
      if (responseReceived) {
        setVisualDebugScreenshots([]);
        setVisualDebugDescription('');
        setVisualDebugMode(false);

        // 🔑 اگه چند مرحله‌ای هست، مراحل بعدی رو با smart-chat اجرا کن
        if (_isMultiStep && vdSteps.length > 1) {
          // ذخیره فایل‌های خوانده‌شده مرحله ۱
          if (vdStep1SelectedFiles.length > 0) {
            setPreviouslyReadFiles(prev => {
              const newF = vdStep1SelectedFiles.filter(f => !prev.includes(f));
              return [...prev, ...newF];
            });
          }

          const collectedActionFiles: any[] = [];
          const collectedAnalysis: string[] = [];
          let commitMessage = '';
          let lastModelUsed = vdStep1ModelUsed;

          // مرحله ۱ رو به لیست نتایج اضافه کن
          collectedAnalysis.push(vdStep1Content.slice(0, 500));
          if (vdStep1ActionPlan?.files?.length) {
            for (const file of vdStep1ActionPlan.files) {
              collectedActionFiles.push(file);
            }
            if (vdStep1ActionPlan.commit_message) commitMessage = vdStep1ActionPlan.commit_message;
          }

          // مراحل ۲ به بعد رو اجرا کن
          const modelIds = inspectorAutoSelect ? [] : inspectorSelectedModels;
          const remainingSteps = vdSteps.slice(1);

          for (let i = 0; i < remainingSteps.length; i++) {
            const step = remainingSteps[i];
            setInspectorChatMessages(prev => [...prev, {
              id: `vd_ms_progress_${i}_${Date.now()}`,
              role: 'system' as const,
              content: `⏳ مرحله ${step.step_number} از ${vdSteps.length}: ${step.description}`,
              timestamp: new Date(),
            }]);

            // ساختن پرامپت مرحله با context مراحل قبلی
            let stepPrompt = `${vdBasePrompt}\n\n## ⚡ مرحله فعلی (${step.step_number} از ${vdSteps.length}):\n${step.description}\n`;
            if (collectedAnalysis.length > 0) {
              stepPrompt += `\n## 📊 خلاصه مراحل قبلی:\n${collectedAnalysis.map((a, idx) => `مرحله ${idx + 1}: ${a.slice(0, 300)}`).join('\n')}\n`;
            }
            if (collectedActionFiles.length > 0) {
              // 🔑 پاس دادن محتوای واقعی فایل‌های تغییر یافته مراحل قبلی
              // تا مدل بداند چه کدی قبلاً نوشته شده و از صفر بازنویسی نکند
              stepPrompt += `\n## 📁 فایل‌های تغییر یافته تا الان (محتوای واقعی — بازنویسی نکن!):\n`;
              let contentBudget = 30000; // حداکثر 30K کاراکتر برای محتوای فایل‌ها
              for (const f of collectedActionFiles) {
                // modify_sections: نمایش sections بجای content
                if (f.operation === 'modify_sections' && f.sections) {
                  const sectionsStr = JSON.stringify(f.sections, null, 2);
                  stepPrompt += `\n### 📄 ${f.path} (modify_sections — ${f.sections.length} بخش):\n\`\`\`json\n${sectionsStr.slice(0, 3000)}\n\`\`\`\n`;
                  contentBudget -= Math.min(sectionsStr.length, 3000);
                  continue;
                }
                const fileContent = f.content || '';
                const truncated = fileContent.length > 5000 ? fileContent.slice(0, 5000) + '\n// ... (ادامه فایل موجود)' : fileContent;
                if (contentBudget <= 0) {
                  stepPrompt += `- \`${f.path}\` (${f.operation}) — [محتوا به خاطر حجم نمایش داده نشد]\n`;
                  continue;
                }
                stepPrompt += `\n### 📄 ${f.path} (${f.operation}):\n\`\`\`\n${truncated}\n\`\`\`\n`;
                contentBudget -= truncated.length;
              }
              stepPrompt += `\n⚠️ **قانون حیاتی**: اگر فایلی در لیست بالا هست و در مرحله فعلی هم باید تغییر کنه → تمام محتوای بالا حفظ شود و فقط تغییرات جدید اضافه شود. هرگز از صفر بازنویسی نکن!\n`;
            }
            stepPrompt += `\n## ⚠️ دستور: فقط مرحله ${step.step_number} رو انجام بده. تحلیل مختصر (حداکثر ۵ خط) + action_plan کامل.`;

            try {
              const chatHistory = inspectorChatMessages
                .filter(m => m.role === 'user' || m.role === 'assistant')
                .slice(-5)
                .map(m => ({ role: m.role, content: m.content?.slice(0, 200) }));

              const stepRes = await fetch(`${API_BASE}/api/render/inspector/smart-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  project_id: projectId,
                  model_ids: modelIds,
                  message: stepPrompt,
                  chat_history: chatHistory,
                  backend_logs: inspectorBackendLogs,
                  frontend_url: inspectorFrontendUrl,
                  previously_read_files: previouslyReadFiles,
                }),
              });

              const stepReader = stepRes.body?.getReader();
              const stepDecoder = new TextDecoder();
              let stepSseBuffer = '';
              let stepEventType = '';
              let stepResponseContent = '';
              let stepActionPlan: any = null;
              let stepFilesWereRead = false;

              if (!stepReader) throw new Error('No reader');

              while (true) {
                const { done, value } = await stepReader.read();
                if (done) break;
                stepSseBuffer += stepDecoder.decode(value, { stream: true });
                const stepLines = stepSseBuffer.split('\n');
                stepSseBuffer = stepLines.pop() || '';
                for (const sLine of stepLines) {
                  if (sLine.startsWith('event: ')) {
                    stepEventType = sLine.slice(7).trim();
                  } else if (sLine.startsWith('data: ') && stepEventType) {
                    try {
                      const sData = JSON.parse(sLine.slice(6));
                      if (stepEventType === 'response') {
                        stepResponseContent = sData.content || '';
                        stepActionPlan = sData.action_plan || null;
                        stepFilesWereRead = sData.files_were_read ?? false;
                        lastModelUsed = sData.model_used || lastModelUsed;
                        if (sData.selected_file_paths?.length) {
                          setPreviouslyReadFiles(prev => {
                            const newF = sData.selected_file_paths.filter((f: string) => !prev.includes(f));
                            return [...prev, ...newF];
                          });
                        }
                      } else if (stepEventType === 'error') {
                        stepResponseContent = `❌ ${sData.message}`;
                      }
                    } catch {}
                    stepEventType = '';
                  }
                }
              }

              // جمع‌آوری نتایج مرحله
              collectedAnalysis.push(stepResponseContent.slice(0, 500));
              if (stepActionPlan?.files?.length) {
                for (const file of stepActionPlan.files) {
                  const existingIdx = collectedActionFiles.findIndex((f: any) => f.path === file.path);
                  if (existingIdx >= 0) {
                    collectedActionFiles[existingIdx] = file;
                  } else {
                    collectedActionFiles.push(file);
                  }
                }
                if (stepActionPlan.commit_message) commitMessage = stepActionPlan.commit_message;
              }

              // نمایش نتیجه مرحله
              setInspectorChatMessages(prev => [...prev, {
                id: `vd_ms_result_${i}_${Date.now()}`,
                role: 'assistant' as const,
                content: `**مرحله ${step.step_number}/${vdSteps.length}: ${step.description}**\n\n${stepResponseContent}`,
                model_id: lastModelUsed,
                timestamp: new Date(),
                action_type: stepActionPlan?.files?.length ? 'smart_action' as any : undefined,
                action_plan: stepActionPlan,
                files_were_read: stepFilesWereRead,
                _is_multi_step_part: true,
              } as any]);

            } catch (err: any) {
              setInspectorChatMessages(prev => [...prev, {
                id: `vd_ms_err_${i}_${Date.now()}`,
                role: 'system' as const,
                content: `❌ خطا در مرحله ${step.step_number}: ${err?.message || 'خطای ناشناخته'}`,
                timestamp: new Date(),
              }]);
            }
          }

          // 📊 گزارش نهایی ترکیبی
          const totalFiles = collectedActionFiles.length;
          let finalContent = `## 📊 گزارش نهایی دیباگ بصری — ${vdSteps.length} مرحله کامل شد\n\n`;
          finalContent += `**فایل‌های تغییر یافته: ${totalFiles}**\n`;
          if (collectedActionFiles.length > 0) {
            finalContent += collectedActionFiles.map(f => `- \`${f.path}\` (${f.operation || 'modify'})`).join('\n');
            finalContent += '\n\n';
          }
          finalContent += collectedAnalysis.map((a, idx) => `**مرحله ${idx + 1}:** ${a.slice(0, 200)}`).join('\n\n');

          const combinedActionPlan = totalFiles > 0 ? {
            files: collectedActionFiles,
            commit_message: commitMessage || `Multi-step visual debug fix: ${vdSteps.map(s => s.description).join(', ')}`,
          } : null;

          setInspectorChatMessages(prev => [...prev, {
            id: `vd_ms_final_${Date.now()}`,
            role: 'assistant' as const,
            content: finalContent,
            model_id: lastModelUsed,
            timestamp: new Date(),
            action_type: combinedActionPlan ? 'smart_action' as any : undefined,
            action_plan: combinedActionPlan,
            is_multi_step_report: true,
            is_visual_debug_report: true,
          } as any]);
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setInspectorChatMessages(prev => [...prev, {
          id: `vd_error_${Date.now()}`,
          role: 'assistant' as const,
          content: `❌ خطا در دیباگ بصری: ${err.message?.slice(0, 100) || 'ناشناخته'}`,
          timestamp: new Date(),
        }]);
      }
    } finally {
      setVisualDebugLoading(false);
      setInspectorOpLock(false);
      setInspectorOpType(null);
    }
  };

  // 🔄 باز کردن مودال انتخاب مدل برای اعمال تغییرات دیباگ بصری
  const handleApplyWithModelSelection = (msgId: string) => {
    setReanalyzeSourceMsgId(msgId);
    setReanalyzeSelectedModel('');
    // بارگذاری لیست مدل‌های فعال
    loadVisionModels();
    setReanalyzeModalOpen(true);
  };

  // 🔄 اعمال تغییرات: اگر همون مدل → مستقیم، اگر مدل دیگه → بازتحلیل
  const handleReanalyzeConfirm = () => {
    if (!reanalyzeSelectedModel || !reanalyzeSourceMsgId) return;
    const msg = inspectorChatMessages.find(m => m.id === reanalyzeSourceMsgId) as any;
    if (!msg) return;

    setReanalyzeModalOpen(false);

    if (reanalyzeSelectedModel === msg.model_id) {
      // همون مدل → اعمال مستقیم
      applySmartAction(reanalyzeSourceMsgId);
    } else {
      // مدل دیگه → بازتحلیل
      sendReanalyze(reanalyzeSourceMsgId, reanalyzeSelectedModel);
    }
  };

  // 🔄 ارسال درخواست بازتحلیل با مدل دوم
  const sendReanalyze = async (msgId: string, newModelId: string) => {
    const msg = inspectorChatMessages.find(m => m.id === msgId) as any;
    if (!msg) return;

    setReanalyzeLoading(true);
    setInspectorOpLock(true);
    setInspectorOpType('investigate');
    inspectorOpAbortRef.current = new AbortController();

    setInspectorChatMessages(prev => [...prev, {
      id: `ra_start_${Date.now()}`,
      role: 'system' as const,
      content: `🔄 شروع بازتحلیل گزارش مدل ${msg.model_id} توسط مدل ${newModelId}...`,
      timestamp: new Date(),
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/visual-debug-reanalyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          model_id: newModelId,
          vision_report: msg.content,
          vision_model_id: msg.model_id || 'unknown',
          vision_action_plan: msg.action_plan || null,
          user_description: (msg as any).original_user_description || '',
          previously_read_files: previouslyReadFiles,
        }),
        signal: inspectorOpAbortRef.current?.signal,
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = '';
      let responseReceived = false;
      if (!reader) throw new Error('No reader');

      let eventType = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split('\n');
        sseBuffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));

              if (eventType === 'progress') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `ra_p_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
                  role: 'system' as const,
                  content: data.message,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'error') {
                setInspectorChatMessages(prev => [...prev, {
                  id: `ra_err_${Date.now()}`,
                  role: 'assistant' as const,
                  content: `❌ ${data.message}${data.detail ? '\n📊 ' + data.detail : ''}`,
                  timestamp: new Date(),
                }]);
              } else if (eventType === 'response') {
                responseReceived = true;
                setInspectorChatMessages(prev => [...prev, {
                  id: `ra_response_${Date.now()}`,
                  role: 'assistant' as const,
                  content: data.content,
                  model_id: data.model_used,
                  timestamp: new Date(),
                  tokens_used: data.tokens_used,
                  action_type: data.has_action ? 'smart_action' as any : undefined,
                  action_plan: data.action_plan,
                  is_reanalysis_report: true,
                  vision_model: data.vision_model,
                } as any]);
                setInspectorOpLock(false);
                setInspectorOpType(null);
              } else if (eventType === 'heartbeat') {
                // keep-alive
              } else if (eventType === 'done') {
                if (!responseReceived) {
                  setInspectorChatMessages(prev => [...prev, {
                    id: `ra_fail_${Date.now()}`,
                    role: 'assistant' as const,
                    content: '⚠️ بازتحلیل بدون نتیجه پایان یافت. لطفاً دوباره تلاش کنید.',
                    timestamp: new Date(),
                  }]);
                  setInspectorOpLock(false);
                  setInspectorOpType(null);
                }
              }
            } catch (e) {}
            eventType = '';
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setInspectorChatMessages(prev => [...prev, {
          id: `ra_error_${Date.now()}`,
          role: 'assistant' as const,
          content: `❌ خطا در بازتحلیل: ${err.message?.slice(0, 100) || 'ناشناخته'}`,
          timestamp: new Date(),
        }]);
      }
    } finally {
      setReanalyzeLoading(false);
      setInspectorOpLock(false);
      setInspectorOpType(null);
    }
  };

  // بارگذاری لاگ‌ها وقتی سرویس‌ها لود شدن
  useEffect(() => {
    if (inspectorPowerOn && inspectorServices.length > 0) {
      loadInspectorLogs();
      // به‌روزرسانی هر 10 ثانیه
      const interval = setInterval(loadInspectorLogs, 10000);
      return () => clearInterval(interval);
    }
  }, [inspectorPowerOn, inspectorServices]);

  const loadProject = async () => {
    setLoading(true);
    try {
      let foundProject = false;

      // اگر ID با gh_ شروع میشه، از GitHub API بگیر
      if (projectId.startsWith('gh_')) {
        const res = await fetch(`${API_BASE}/api/github/imported/${projectId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.project) {
            setProject(data.project);
            if (data.project.files) {
              setFiles(data.project.files.map((f: any) => ({
                path: f.path,
                size: f.size,
                type: f.type,
                github_url: f.github_url,
              })));
            }
            foundProject = true;
          }
        }
      }

      // اگر پیدا نشد، از creator بگیر
      if (!foundProject) {
        let res = await fetch(`${API_BASE}/api/creator/projects/${projectId}`);
        let data = await res.json();

        if (res.ok && data.project) {
          setProject(data.project);
          if (data.project.files) {
            setFiles(data.project.files.map((f: any) =>
              typeof f === 'string' ? { path: f } : f
            ));
          }
          foundProject = true;
        }
      }

      // اگر هنوز پیدا نشد، از projects API بگیر
      if (!foundProject) {
        const res = await fetch(`${API_BASE}/api/projects/${projectId}`);
        const data = await res.json();
        if (res.ok) {
          setProject(data.project || data);
          foundProject = true;
        }
      }

      // اگر پروژه پیدا نشد
      if (!foundProject) {
        showError('پروژه پیدا نشد');
        return;
      }

      // فایل‌های پروژه رو بگیر (برای پروژه‌های غیر GitHub)
      if (!projectId.startsWith('gh_')) {
        const filesRes = await fetch(`${API_BASE}/api/projects/${projectId}/files`);
        if (filesRes.ok) {
          const filesData = await filesRes.json();
          if (filesData.files) {
            setFiles(filesData.files);
          }
        }
      }
    } catch (e) {
      showError('خطا در بارگذاری پروژه');
    } finally {
      setLoading(false);
    }
  };

  const loadMemory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setMemoryInstructions(data.memory_instructions || { content: '', target_models: ['all'] });
          setDynamicFields(data.dynamic_fields || []);
          setAvailableModels(data.available_models || []);
          setTriggerIntervals(data.trigger_intervals || []);
        }
      }
    } catch (e) {
      console.error('Error loading memory:', e);
    }
  };

  // 🆕 بارگذاری فیلدهای در انتظار تایید
  const loadPendingApprovals = async () => {
    setLoadingApprovals(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/quick-approval/pending`);
      if (res.ok) {
        const data = await res.json();
        if (data && !data.error && typeof data.total === 'number') {
          setPendingApprovals(data);
        } else {
          setPendingApprovals({ auto_pending: [], pending: [], total: 0 });
        }
      }
    } catch (e) {
      console.error('Error loading pending approvals:', e);
    } finally {
      setLoadingApprovals(false);
    }
  };

  // 🆕 تایید سریع فیلد
  const quickApproveField = async (fieldId: string, note?: string) => {
    setApprovingField(fieldId);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/quick-approval/approve/${fieldId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approver_note: note }),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(data.message || 'فیلد با موفقیت تایید شد');
        loadMemory();
        loadPendingApprovals();
      } else {
        showError(data.error || 'خطا در تایید فیلد');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setApprovingField(null);
    }
  };

  // 🆕 رد کردن فیلد
  const rejectField = async (fieldId: string, reason: string) => {
    if (!reason.trim()) {
      showError('لطفاً دلیل رد را وارد کنید');
      return;
    }
    setRejectingField(fieldId);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/quick-approval/reject/${fieldId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejection_reason: reason }),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(data.message || 'فیلد رد و آرشیو شد');
        loadMemory();
        loadPendingApprovals();
        setRejectionReason('');
      } else {
        showError(data.error || 'خطا در رد فیلد');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setRejectingField(null);
    }
  };

  // 🆕 تبدیل خودکار ایرادات بحرانی به فیلد
  const autoConvertCriticalIssues = async () => {
    setAutoConvertingIssues(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/quick-approval/auto-convert`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        const msg = `${data.converted} ایراد به فیلد تبدیل شد` +
          (data.skipped_duplicate > 0 ? ` (${data.skipped_duplicate} تکراری رد شد)` : '');
        showSuccess(msg);
        loadMemory();
        loadPendingApprovals();
      } else {
        showError(data.errors?.join(', ') || 'خطا در تبدیل');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setAutoConvertingIssues(false);
    }
  };

  // 🆕 اعتبارسنجی قبل از اجرا
  const preValidateField = async (fieldId: string): Promise<{can_execute: boolean; reason?: string; recommendation?: string}> => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/quick-approval/pre-validate/${fieldId}`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error('Pre-validation error:', e);
    }
    return { can_execute: true }; // در صورت خطا، اجازه اجرا بده
  };

  // 🆕 ارسال درخواست قابلیت جدید
  const submitFeatureRequest = async () => {
    if (!featureRequest.title.trim() || !featureRequest.description.trim()) {
      showError('عنوان و توضیحات الزامی است');
      return;
    }
    setSubmittingFeatureRequest(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/request-feature`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(featureRequest),
      });
      const data = await res.json();
      setFeatureRequestResult(data);
      if (data.success) {
        showSuccess(data.message || 'درخواست قابلیت ثبت شد');
        loadMemory();
        // ریست فرم
        setFeatureRequest({
          title: '',
          description: '',
          priority: 'medium',
          category: 'feature',
          target_files: [],
          ai_analyze: true,
          auto_add_roadmap: true,
          model_id: 'claude'
        });
      } else if (data.duplicate_warning) {
        showError(data.duplicate_warning.message || 'قابلیت مشابه وجود دارد');
      } else {
        showError(data.message || 'خطا در ثبت درخواست');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setSubmittingFeatureRequest(false);
    }
  };

  // بارگذاری تنظیمات سینک
  const loadSyncSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/sync-settings`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSyncSettings(data.sync_settings);
        }
      }
    } catch (e) {
      console.error('Error loading sync settings:', e);
    }
  };

  // ذخیره تنظیمات سینک
  const saveSyncSettings = async () => {
    setSavingSyncSettings(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/sync-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(syncSettings),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('تنظیمات سینک ذخیره شد');
        // راه‌اندازی مجدد تایمر سینک خودکار
        setupAutoSync();
      } else {
        showError(data.error || 'خطا در ذخیره تنظیمات');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setSavingSyncSettings(false);
    }
  };

  // اجرای سینک خودکار با تنظیمات
  const performAutoSync = async () => {
    console.log('[Auto Sync] Performing sync...');
    try {
      // سینک فایل‌ها
      await fetch(`${API_BASE}/api/github/imported/${projectId}/refresh`, {
        method: 'POST',
      });

      // بروزرسانی پروژه
      loadProject();

      // بروزرسانی دیاگرام و ساختار اگر فعال باشه
      if (syncSettings.update_diagram_after_sync || syncSettings.update_structure_after_sync) {
        loadStructure();
      }

      console.log('[Auto Sync] Sync completed');
    } catch (e) {
      console.error('[Auto Sync] Error:', e);
    }
  };

  // راه‌اندازی سینک خودکار با تایمر
  const setupAutoSync = useCallback(() => {
    // پاکسازی تایمر قبلی
    if (syncIntervalTimer) {
      clearInterval(syncIntervalTimer);
      setSyncIntervalTimer(null);
    }

    // اگر سینک خودکار فعال نیست یا پروژه از GitHub نیست، کاری نکن
    if (!syncSettings.auto_sync_enabled || project?.project_type !== 'github_import') {
      return;
    }

    const intervalMs = syncSettings.sync_interval_minutes * 60 * 1000;
    console.log(`[Auto Sync] Setting up timer: every ${syncSettings.sync_interval_minutes} minutes`);

    const timer = setInterval(() => {
      performAutoSync();
    }, intervalMs);

    setSyncIntervalTimer(timer);
  }, [syncSettings.auto_sync_enabled, syncSettings.sync_interval_minutes, project?.project_type]);

  // پاکسازی تایمر در unmount
  useEffect(() => {
    return () => {
      if (syncIntervalTimer) {
        clearInterval(syncIntervalTimer);
      }
    };
  }, [syncIntervalTimer]);

  // بارگذاری داده‌های سلامت فایل‌ها
  const loadFileHealthMap = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/file-map`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.file_map) {
          setFileHealthMap(data.file_map);
          setHealthDataLoaded(true);
        }
      }
    } catch (e) {
      console.error('Error loading file health map:', e);
    }
  };

  // بارگذاری ساختار پروژه
  const loadStructure = async () => {
    setStructureLoading(true);
    try {
      // بارگذاری همزمان ساختار و داده‌های سلامت
      const [structureRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/api/projects/${projectId}/structure`),
        fetch(`${API_BASE}/api/projects/${projectId}/health/file-map`)
      ]);

      let healthMap: Record<string, any> = {};
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        if (healthData.success && healthData.file_map) {
          healthMap = healthData.file_map;
          setFileHealthMap(healthMap);
          setHealthDataLoaded(true);
        }
      }

      if (structureRes.ok) {
        const data = await structureRes.json();
        if (data.success) {
          setStructureData(data.structure);
          setStructureSettings(data.settings);
          // تبدیل به فرمت React Flow با رنگ‌بندی سلامت
          convertToReactFlow(data.structure, healthMap);
        }
      }
    } catch (e) {
      console.error('Error loading structure:', e);
    } finally {
      setStructureLoading(false);
    }
  };

  // تبدیل داده‌ها به فرمت React Flow با رنگ‌بندی سلامت
  const convertToReactFlow = (structure: ProjectStructure, healthMap?: Record<string, any>) => {
    if (!structure?.nodes || !structure?.edges) return;
    const currentHealthMap = healthMap || fileHealthMap;

    const flowNodes: Node[] = structure.nodes.map((node) => {
      // پیدا کردن اطلاعات سلامت برای این نود
      const nodePath = node.data?.path || node.label || node.id;
      const healthInfo = findHealthInfoForNode(nodePath, currentHealthMap);

      // تعیین رنگ نود بر اساس سلامت
      let nodeBackground = node.style?.background || '#6366f1';
      let borderColor = node.is_active ? '#22c55e' : '#4b5563';
      let healthScore = null;
      let healthLabel = '';

      if (healthInfo) {
        nodeBackground = healthInfo.hex || nodeBackground;
        healthScore = healthInfo.score;
        healthLabel = healthInfo.label || '';
        // برای فایل‌های با مشکل، حاشیه قرمز
        if (healthInfo.score < 50) {
          borderColor = '#ef4444';
        } else if (healthInfo.score < 70) {
          borderColor = '#f97316';
        }
      }

      return {
        id: node.id,
        type: 'default',
        position: node.position,
        data: {
          label: (
            <div
              className={`text-center ${node.is_active ? 'animate-pulse' : ''} relative group cursor-pointer`}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
            >
              <div className="font-bold">{node.label}</div>
              {node.description && (
                <div className="text-xs opacity-70 mt-1">{node.description}</div>
              )}
              {/* نمایش نمره سلامت روی نود */}
              {healthScore !== null && (
                <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-white text-xs font-bold flex items-center justify-center shadow"
                     style={{ color: healthInfo?.hex || '#666' }}>
                  {Math.round(healthScore)}
                </div>
              )}

              {/* هاور tooltip با جزئیات سلامت */}
              {healthInfo && hoveredNode === node.id && (
                <div className="absolute z-50 top-full left-1/2 transform -translate-x-1/2 mt-2 w-64 bg-white dark:bg-gray-800 text-gray-800 dark:text-white rounded-lg shadow-xl p-3 text-right border border-gray-200 dark:border-gray-700"
                     style={{ pointerEvents: 'none' }}>
                  <div className="text-sm font-bold mb-2 pb-2 border-b flex items-center justify-between">
                    <span>وضعیت سلامت</span>
                    <span className="px-2 py-0.5 rounded text-xs text-white"
                          style={{ backgroundColor: healthInfo.hex }}>
                      {healthLabel}
                    </span>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-500">نمره کلی:</span>
                      <span className="font-bold" style={{ color: healthInfo.hex }}>
                        {healthInfo.score?.toFixed(1)}%
                      </span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-500">مدل‌های بررسی‌کننده:</span>
                      <span className="font-bold">{healthInfo.models_analyzed || 0}</span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-500">تعداد ایرادات:</span>
                      <span className={`font-bold ${(healthInfo.issues_count || 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                        {healthInfo.issues_count || 0}
                      </span>
                    </div>

                    {healthInfo.analyzed_at && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">تاریخ تحلیل:</span>
                        <span className="text-gray-600 dark:text-gray-400">
                          {new Date(healthInfo.analyzed_at).toLocaleDateString('fa-IR')}
                        </span>
                      </div>
                    )}

                    {/* نمرات هر مدل */}
                    {healthInfo.model_scores && Object.keys(healthInfo.model_scores).length > 0 && (
                      <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
                        <div className="text-gray-500 mb-1">نمره هر مدل:</div>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(healthInfo.model_scores).map(([model, score]) => (
                            <span key={model}
                                  className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                              {model.split('/').pop()}: {(score as number).toFixed(0)}%
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ),
          // ذخیره اطلاعات سلامت در data نود
          healthInfo: healthInfo,
          path: nodePath,
        },
        style: {
          background: nodeBackground,
          color: node.style?.color || 'white',
          border: node.is_active ? `3px solid ${borderColor}` : `2px solid ${borderColor}`,
          borderRadius: '8px',
          padding: '10px',
          fontSize: node.style?.fontSize || '14px',
          fontWeight: node.style?.fontWeight || 'normal',
          boxShadow: node.is_active ? `0 0 15px ${borderColor}` : '0 2px 8px rgba(0,0,0,0.3)',
          transition: 'all 0.3s ease',
        },
      };
    });

    const flowEdges: Edge[] = structure.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type || 'smoothstep',
      animated: edge.animated || false,
      label: edge.label,
      style: {
        stroke: edge.animated ? '#22c55e' : '#6b7280',
        strokeWidth: edge.animated ? 3 : 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edge.animated ? '#22c55e' : '#6b7280',
      },
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);
  };

  // تابع کمکی برای پیدا کردن اطلاعات سلامت یک نود
  const findHealthInfoForNode = (nodePath: string, healthMap: Record<string, any>) => {
    if (!healthMap || !nodePath) return null;

    // جستجوی دقیق
    if (healthMap[nodePath]) {
      return healthMap[nodePath];
    }

    // جستجوی با نام فایل
    const fileName = nodePath.split('/').pop();
    for (const [path, info] of Object.entries(healthMap)) {
      if (path.endsWith(nodePath) || path.split('/').pop() === fileName) {
        return info;
      }
    }

    return null;
  };

  // تحلیل مجدد ساختار
  const analyzeStructure = async () => {
    setAnalyzingStructure(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/structure/analyze`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('ساختار پروژه با موفقیت تحلیل شد');
        setStructureData(data.structure);
        setStructureSettings(data.settings);

        // دریافت داده‌های سلامت برای رنگ‌بندی
        try {
          const healthRes = await fetch(`${API_BASE}/api/projects/${projectId}/health/file-map`);
          if (healthRes.ok) {
            const healthData = await healthRes.json();
            if (healthData.success && healthData.file_map) {
              setFileHealthMap(healthData.file_map);
              convertToReactFlow(data.structure, healthData.file_map);
            } else {
              convertToReactFlow(data.structure);
            }
          } else {
            convertToReactFlow(data.structure);
          }
        } catch {
          convertToReactFlow(data.structure);
        }
      } else {
        showError(data.detail || 'خطا در تحلیل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setAnalyzingStructure(false);
    }
  };

  // ذخیره تنظیمات ساختار
  const saveStructureSettings = async () => {
    setSavingStructureSettings(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/structure/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(structureSettings),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('تنظیمات ذخیره شد');
        setStructureSettings(data.settings);
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSavingStructureSettings(false);
    }
  };

  // ===================== توابع ژورنال =====================

  // بارگذاری لاگ‌های فعالیت
  const loadJournal = async () => {
    setJournalLoading(true);
    try {
      const params = new URLSearchParams({
        page: journalPage.toString(),
        page_size: '20',
      });
      if (journalFilter.type) params.append('activity_type', journalFilter.type);
      if (journalFilter.model) params.append('model_id', journalFilter.model);
      if (journalFilter.success !== undefined) params.append('success', journalFilter.success.toString());

      const res = await fetch(`${API_BASE}/api/projects/${projectId}/journal?${params}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setJournalLogs(data.journal);
          setJournalTotal(data.pagination?.total ?? 0);
        }
      }
    } catch (e) {
      console.error('Error loading journal:', e);
    } finally {
      setJournalLoading(false);
    }
  };

  // بارگذاری آمار ژورنال
  const loadJournalStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/journal/stats?days=30`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setJournalStats(data.stats);
        }
      }
    } catch (e) {
      console.error('Error loading stats:', e);
    }
  };

  // بارگذاری نقشه راه برای تب ژورنال
  const loadRoadmap = async () => {
    setRoadmapLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/roadmap`);
      if (res.ok) {
        const data = await res.json();
        setRoadmapContent(data.roadmap_content || '');
        setIdealState(data.ideal_state || '');

        // پارس کردن نقشه راه به آیتم‌های چک‌باکسی
        const items: typeof roadmapItems = [];
        const content = data.roadmap_content || '';

        // پیدا کردن خطوطی که با - یا * شروع می‌شوند
        const lines = content.split('\n');
        let currentPriority: 'immediate' | 'short_term' | 'long_term' = 'immediate';

        lines.forEach((line: string, index: number) => {
          const trimmed = line.trim();

          // تشخیص بخش‌ها
          if (trimmed.includes('فوری') || trimmed.includes('immediate') || trimmed.includes('کوتاه‌مدت فوری')) {
            currentPriority = 'immediate';
          } else if (trimmed.includes('کوتاه‌مدت') || trimmed.includes('short') || trimmed.includes('میان‌مدت')) {
            currentPriority = 'short_term';
          } else if (trimmed.includes('بلندمدت') || trimmed.includes('long') || trimmed.includes('آینده')) {
            currentPriority = 'long_term';
          }

          // پیدا کردن آیتم‌ها
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.match(/^\d+\./)) {
            const text = trimmed.replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '');
            const isCompleted = trimmed.includes('[x]') || trimmed.includes('✅') || trimmed.includes('✓');

            items.push({
              id: `roadmap_${index}`,
              text: text.replace(/\[x\]|\[✓\]|\[✅\]/gi, '').trim(),
              completed: isCompleted,
              priority: currentPriority,
              has_field: false,
            });
          }
        });

        setRoadmapItems(items);
      }
    } catch (e) {
      console.error('Error loading roadmap:', e);
    } finally {
      setRoadmapLoading(false);
    }
  };

  // تغییر وضعیت چک‌باکس نقشه راه
  const toggleRoadmapItem = async (itemId: string) => {
    const updatedItems = roadmapItems.map(item =>
      item.id === itemId ? { ...item, completed: !item.completed } : item
    );
    setRoadmapItems(updatedItems);

    // به‌روزرسانی در سرور
    try {
      await fetch(`${API_BASE}/api/projects/${projectId}/roadmap/items/${itemId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: !roadmapItems.find(i => i.id === itemId)?.completed }),
      });
    } catch (e) {
      console.error('Error updating roadmap item:', e);
    }
  };

  // تولید فیلد برای آیتم‌های خالی نقشه راه
  const generateFieldsForPendingItems = async () => {
    setGeneratingRoadmapFields(true);
    try {
      const pendingItems = roadmapItems.filter(item => !item.completed && !item.has_field);

      for (const item of pendingItems) {
        const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: `[نقشه راه] ${item.text.slice(0, 60)}`,
            value: `هدف نقشه راه:\n${item.text}\n\nاولویت: ${item.priority === 'immediate' ? 'فوری' : item.priority === 'short_term' ? 'کوتاه‌مدت' : 'بلندمدت'}`,
            target_models: ['all'],
            field_type: 'temporary',
            priority: item.priority === 'immediate' ? 1 : item.priority === 'short_term' ? 4 : 7,
            action_type: 'github_commit',
            archive_after_run: true,
            source: 'roadmap',
            roadmap_item_id: item.id,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          setRoadmapItems(prev => prev.map(i =>
            i.id === item.id ? { ...i, has_field: true, field_id: data.field_id } : i
          ));
        }

        // کمی تاخیر بین درخواست‌ها
        await new Promise(r => setTimeout(r, 300));
      }

      showSuccess(`${pendingItems.length} فیلد برای موارد انتظار ایجاد شد`);
    } catch (e) {
      showError('خطا در تولید فیلدها');
    } finally {
      setGeneratingRoadmapFields(false);
    }
  };

  // بارگذاری جزئیات یک فعالیت
  const loadActivityDetail = async (logId: string) => {
    try {
      setSelectedLogId(logId);
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/journal/${logId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSelectedLog(data.activity);

          // 🆕 بارگذاری عملیات جزئی
          loadDetailedOperations(logId);
        }
      }
    } catch (e) {
      showError('خطا در بارگذاری جزئیات');
    }
  };

  // 🆕 بارگذاری عملیات جزئی (DetailedOperation)
  const loadDetailedOperations = async (logId: string) => {
    setLoadingOperations(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/journal/${logId}/operations`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setDetailedOperations(data.operations || []);
        }
      }
    } catch (e) {
      console.error('Error loading detailed operations:', e);
    } finally {
      setLoadingOperations(false);
    }
  };

  // بارگذاری گزارشات
  const loadReports = async () => {
    setReportsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/reports`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setReports(data.reports);
        }
      }
    } catch (e) {
      console.error('Error loading reports:', e);
    } finally {
      setReportsLoading(false);
    }
  };

  // بارگذاری جزئیات گزارش
  const loadReportDetail = async (reportId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/reports/${reportId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSelectedReport(data.report);
        }
      }
    } catch (e) {
      showError('خطا در بارگذاری گزارش');
    }
  };

  // بارگذاری تنظیمات تریگر گزارش
  const loadReportTrigger = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/reports/trigger`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setReportTrigger(data.trigger);
        }
      }
    } catch (e) {
      console.error('Error loading trigger:', e);
    }
  };

  // ذخیره تنظیمات تریگر
  const saveReportTrigger = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/reports/trigger`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportTrigger),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('تنظیمات تریگر ذخیره شد');
        setReportTrigger(data.trigger);
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  // تولید گزارش جدید
  const generateReport = async (days: number = 7) => {
    setGeneratingReport(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/reports/generate?days=${days}&model_id=${reportTrigger.report_model}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(data.message);
        loadReports();
      } else {
        showError(data.message || 'خطا در تولید گزارش');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setGeneratingReport(false);
    }
  };

  // تولید گزارش مهندسی جامع
  const generateEngineeringReport = async (days: number = 7) => {
    // نمایش پنجره انتخاب مدل و عمق گزارش
    setShowEngineeringModelSelector(true);
  };

  // اجرای واقعی گزارش مهندسی بعد از انتخاب مدل و عمق
  const executeEngineeringReport = async (days: number = 7) => {
    setShowEngineeringModelSelector(false);

    const depthLabels = { quick: 'سریع (۱-۲ دقیقه)', standard: 'استاندارد (۳-۵ دقیقه)', deep: 'عمیق و جامع (۱۰-۲۰ دقیقه)' };
    const modelsText = selectedEngineeringModels.length > 1
      ? `${selectedEngineeringModels.length} مدل`
      : availableModels.find(m => m.id === selectedEngineeringModels[0])?.name || selectedEngineeringModels[0];

    if (!confirm(`تولید گزارش مهندسی جامع؟\n\n📊 مدل‌های انتخابی: ${modelsText}\n⏱️ عمق گزارش: ${depthLabels[engineeringReportDepth]}\n\nاین گزارش شامل:\n• تحلیل کامل ساختار پروژه\n• 🔍 اعتبارسنجی نتایج تحلیل سلامت (تایید/رد ایرادات)\n• شناسایی باگ‌ها و مشکلات\n• پیشنهادات بهبود\n• نقشه راه توسعه\n• تولید خودکار فیلدها برای ایرادات تایید شده`)) {
      return;
    }

    setGeneratingReport(true);
    const totalSteps = engineeringReportDepth === 'deep' ? 12 : (engineeringReportDepth === 'standard' ? 8 : 4);
    setReportProgress({ step: 0, total: totalSteps, message: '🚀 شروع تولید گزارش...', progress: 0 });

    try {
      // 🔴 ارسال مدل‌های انتخابی و عمق گزارش
      const modelIds = selectedEngineeringModels.join(',');
      const response = await fetch(`${API_BASE}/api/projects/${projectId}/reports/generate-engineering-stream?days=${days}&model_ids=${modelIds}&depth=${engineeringReportDepth}&auto_create_fields=true&validate_health_issues=true`, {
        method: 'POST',
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let finalResult: any = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value);
          const lines = text.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                // به‌روزرسانی پیشرفت
                if (data.progress !== undefined) {
                  setReportProgress({
                    step: data.step || 0,
                    total: data.total || 8,
                    message: data.message || '',
                    progress: data.progress
                  });
                  // 🔴 دریافت پرامپت‌های در حال اجرا
                  try {
                    const execRes = await fetch(`${API_BASE}/api/prompts/executions/active?project_id=${projectId}`);
                    if (execRes.ok) {
                      const execData = await execRes.json();
                      if (execData.success && execData.executions) {
                        setActivePromptExecutions(execData.executions);
                      }
                    }
                  } catch (e) {
                    console.error('Error fetching prompt executions:', e);
                  }
                }

                // نتیجه نهایی
                if (data.result) {
                  finalResult = data.result;
                }

                // خطا
                if (data.error && !data.result) {
                  showError(data.error);
                }
              } catch (e) {
                // JSON parsing error, ignore
              }
            }
          }
        }

        // پردازش نتیجه نهایی
        if (finalResult?.success) {
          let successMsg = `✅ گزارش مهندسی تولید شد`;

          if (finalResult.project_health_score) {
            successMsg += ` | امتیاز سلامت: ${finalResult.project_health_score}%`;
          }
          if (finalResult.bugs_found > 0) {
            successMsg += ` | ${finalResult.bugs_found} باگ شناسایی شد`;
          }
          if (finalResult.fields_count > 0) {
            successMsg += ` | ${finalResult.fields_count} فیلد جدید ایجاد شد`;
          }
          if (finalResult.validation_results) {
            const vr = finalResult.validation_results;
            if (vr.issues_reviewed > 0) {
              successMsg += ` | اعتبارسنجی: ${vr.validated_count} تایید، ${vr.rejected_count} رد`;
            }
          }

          showSuccess(successMsg);
          loadReports();

          if (finalResult.fields_count > 0) {
            loadMemory();
          }
        } else if (finalResult) {
          showError(finalResult.error || 'خطا در تولید گزارش');
        }
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setGeneratingReport(false);
      setReportProgress(null);
      setActivePromptExecutions([]); // 🔴 پاک کردن پرامپت‌های در حال اجرا
    }
  };

  // ===================== توابع پروفایل مدل‌ها و اعتبارسنجی =====================

  // داده‌های پیش‌فرض پروفایل مدل‌ها
  const defaultModelProfiles = [
    {model_id: "gpt-4", provider: "openai", display_name: "GPT-4", tier: "S", overall_score: 92.5, accuracy_score: 95, completeness_score: 90, speed_score: 88, reliability_score: 94, total_analyses: 0, total_tasks: 0, avg_response_time: 1200, last_activity: null, rank: 1},
    {model_id: "gpt-4o", provider: "openai", display_name: "GPT-4o", tier: "S", overall_score: 91.0, accuracy_score: 93, completeness_score: 89, speed_score: 95, reliability_score: 92, total_analyses: 0, total_tasks: 0, avg_response_time: 800, last_activity: null, rank: 2},
    {model_id: "claude-3-opus", provider: "anthropic", display_name: "Claude 3 Opus", tier: "S", overall_score: 90.5, accuracy_score: 94, completeness_score: 92, speed_score: 82, reliability_score: 93, total_analyses: 0, total_tasks: 0, avg_response_time: 1500, last_activity: null, rank: 3},
    {model_id: "gpt-4o-mini", provider: "openai", display_name: "GPT-4o Mini", tier: "A", overall_score: 85.0, accuracy_score: 86, completeness_score: 83, speed_score: 92, reliability_score: 88, total_analyses: 0, total_tasks: 0, avg_response_time: 500, last_activity: null, rank: 4},
    {model_id: "claude-3-sonnet", provider: "anthropic", display_name: "Claude 3 Sonnet", tier: "A", overall_score: 84.0, accuracy_score: 88, completeness_score: 85, speed_score: 80, reliability_score: 86, total_analyses: 0, total_tasks: 0, avg_response_time: 1000, last_activity: null, rank: 5},
    {model_id: "deepseek-chat", provider: "deepseek", display_name: "DeepSeek Chat", tier: "B", overall_score: 78.0, accuracy_score: 80, completeness_score: 76, speed_score: 82, reliability_score: 78, total_analyses: 0, total_tasks: 0, avg_response_time: 700, last_activity: null, rank: 6},
  ];

  const defaultLeaderboard: any = {
    best_accuracy: {label: "بهترین دقت", model_id: "gpt-4", display_name: "GPT-4", score: 95, tier: "S"},
    best_speed: {label: "سریع‌ترین", model_id: "gpt-4o", display_name: "GPT-4o", score: 95, tier: "S"},
    best_reliability: {label: "قابل‌اطمینان‌ترین", model_id: "gpt-4", display_name: "GPT-4", score: 94, tier: "S"},
    best_code_quality: {label: "بهترین کیفیت کد", model_id: "claude-3-opus", display_name: "Claude 3 Opus", score: 92, tier: "S"},
    most_active: {label: "فعال‌ترین", model_id: "gpt-4o-mini", display_name: "GPT-4o Mini", score: 0, tier: "A"},
  };

  // بارگذاری لیست پروفایل مدل‌ها
  const loadModelProfiles = async () => {
    setProfilesLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/models/profiles`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.profiles?.length > 0) {
          setModelProfiles(data.profiles);
          return;
        }
      }
      // اگر API کار نکرد، از پیش‌فرض استفاده کن
      setModelProfiles(defaultModelProfiles);
    } catch (e) {
      console.log('Using default model profiles');
      setModelProfiles(defaultModelProfiles);
    } finally {
      setProfilesLoading(false);
    }
  };

  // بارگذاری جزئیات پروفایل یک مدل
  const loadProfileDetail = async (modelId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/models/profiles/${encodeURIComponent(modelId)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSelectedProfile(data.profile);
          return;
        }
      }
      // استفاده از پیش‌فرض
      const found = defaultModelProfiles.find(p => p.model_id === modelId);
      if (found) {
        setSelectedProfile({
          ...found,
          scores: {overall: found.overall_score, accuracy: found.accuracy_score, completeness: found.completeness_score, speed: found.speed_score, reliability: found.reliability_score, code_quality: 80, reasoning: 80},
          stats: {total_analyses: 0, total_tasks: 0, total_debates: 0, correct_findings: 0, missed_issues: 0, false_positives: 0},
          capabilities: {strengths: [], weaknesses: []},
        });
      }
    } catch (e) {
      console.log('Using default profile detail');
      const found = defaultModelProfiles.find(p => p.model_id === modelId);
      if (found) {
        setSelectedProfile({
          ...found,
          scores: {overall: found.overall_score, accuracy: found.accuracy_score, completeness: found.completeness_score, speed: found.speed_score, reliability: found.reliability_score, code_quality: 80, reasoning: 80},
          stats: {total_analyses: 0, total_tasks: 0, total_debates: 0, correct_findings: 0, missed_issues: 0, false_positives: 0},
          capabilities: {strengths: [], weaknesses: []},
        });
      }
    }
  };

  // بارگذاری رتبه‌بندی مدل‌ها
  const loadModelRankings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/rankings`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.rankings?.length > 0) {
          setModelRankings(data.rankings);
          return;
        }
      }
      setModelRankings(defaultModelProfiles);
    } catch (e) {
      console.log('Using default rankings');
      setModelRankings(defaultModelProfiles);
    }
  };

  // بارگذاری لیدربورد
  const loadLeaderboard = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/leaderboard`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && Object.keys(data.leaderboard || {}).length > 0) {
          setLeaderboard(data.leaderboard);
          return;
        }
      }
      setLeaderboard(defaultLeaderboard);
    } catch (e) {
      console.log('Using default leaderboard');
      setLeaderboard(defaultLeaderboard);
    }
  };

  // اعتبارسنجی گزارش تحلیل سلامت
  const validateHealthAnalysis = async (analysisId: string) => {
    setValidationInProgress(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_id: analysisId }),
      });
      if (res.ok) {
        const data = await res.json();
        setValidationResult(data);
        // بروزرسانی پروفایل‌ها
        loadModelProfiles();
        loadModelRankings();
      }
    } catch (e) {
      console.error('Error validating analysis:', e);
    } finally {
      setValidationInProgress(false);
    }
  };

  // بروزرسانی دستی نمره مدل
  const updateModelScore = async (modelId: string, correct: number, missed: number, falsePositive: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/models/profiles/${encodeURIComponent(modelId)}/update-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'manual_validation',
          correct_findings: correct,
          missed_issues: missed,
          false_positives: falsePositive,
        }),
      });
      if (res.ok) {
        loadModelProfiles();
        loadModelRankings();
      }
    } catch (e) {
      console.error('Error updating score:', e);
    }
  };

  // رنگ Tier
  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'S': return 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white';
      case 'A': return 'bg-gradient-to-r from-green-500 to-green-600 text-white';
      case 'B': return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white';
      case 'C': return 'bg-gradient-to-r from-orange-400 to-orange-500 text-white';
      case 'D': return 'bg-gradient-to-r from-red-400 to-red-500 text-white';
      case 'F': return 'bg-gradient-to-r from-gray-500 to-gray-600 text-white';
      default: return 'bg-gray-400 text-white';
    }
  };

  // ===================== پایان توابع ژورنال و پروفایل =====================

  const saveMemoryInstructions = async () => {
    setSavingMemory(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/instructions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(memoryInstructions),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('باکس حافظه ذخیره شد');
      } else {
        showError(data.detail || 'خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSavingMemory(false);
    }
  };

  // راه‌اندازی خودکار جامع حافظه و فیلدهای پویا
  const runAutoSetup = async () => {
    if (!confirm(`🚀 راه‌اندازی خودکار جامع

این عملیات شامل موارد زیر است:
• سینک کامل با GitHub (بازیابی آخرین تغییرات)
• حذف محتوای نامعتبر
• بررسی و به‌روزرسانی فیلدهای موجود
• ایجاد فیلدهای جدید با اولویت‌بندی
• به‌روزرسانی باکس حافظه
• ثبت تمام عملیات در ژورنال

آیا ادامه می‌دهید؟`)) {
      return;
    }

    setRunningAutoSetup(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/projects/${projectId}/memory/auto-setup?use_ai=true&sync_github=true&clean_invalid=true`,
        { method: 'POST' }
      );
      const data = await res.json();

      if (data.success) {
        // نمایش خلاصه عملیات
        const ops = data.operations || {};
        const fieldsOps = ops.fields_analysis || {};

        let message = `✅ راه‌اندازی خودکار کامل شد!\n\n`;
        message += `📊 نوع: ${data.detected_type || 'عمومی'}\n`;
        message += `💻 زبان: ${data.language || 'نامشخص'}\n`;
        message += `🏗️ معماری: ${data.architecture || 'نامشخص'}\n\n`;

        message += `📋 عملیات انجام شده:\n`;

        if (ops.github_sync?.done) {
          const gs = ops.github_sync.details || {};
          message += `• سینک GitHub: ${gs.files_added || 0} اضافه، ${gs.files_updated || 0} به‌روز، ${gs.files_removed || 0} حذف\n`;
        }

        if (ops.invalid_cleanup?.done && ops.invalid_cleanup.removed?.length > 0) {
          message += `• پاکسازی: ${ops.invalid_cleanup.removed.length} مورد نامعتبر حذف شد\n`;
        }

        if (fieldsOps.done) {
          message += `• فیلدها: ${fieldsOps.created || 0} جدید، ${fieldsOps.updated || 0} به‌روز، ${fieldsOps.archived || 0} بایگانی، ${fieldsOps.merged || 0} ادغام\n`;
          if (fieldsOps.protected > 0) {
            message += `• محافظت: ${fieldsOps.protected} فیلد از گزارش مهندسی محافظت شد\n`;
          }
        }

        if (ops.memory_update?.done && ops.memory_update.changed) {
          message += `• حافظه به‌روز شد\n`;
        }

        if (ops.tabs_update?.tabs?.length > 0) {
          message += `• تب‌های به‌روز شده: ${ops.tabs_update.tabs.join('، ')}\n`;
        }

        message += `\n📝 ${data.journal_entries?.length || 0} ردیف در ژورنال ثبت شد`;

        // نمایش توصیه‌ها
        if (data.recommendations && data.recommendations.length > 0) {
          message += `\n\n💡 توصیه‌ها:\n`;
          data.recommendations.slice(0, 3).forEach((rec: string, i: number) => {
            message += `${i + 1}. ${rec}\n`;
          });
        }

        showSuccess(message);

        // بارگذاری مجدد اطلاعات
        loadMemory();
        loadProject();

        // اگر تنظیمات سینک فعال است، ساختار را هم به‌روز کن
        if (syncSettings.update_structure_after_sync) {
          loadStructure();
        }
      } else {
        showError(data.detail || data.error || 'خطا در راه‌اندازی خودکار');
      }
    } catch (e: any) {
      showError(`خطا در ارتباط: ${e.message || e}`);
    } finally {
      setRunningAutoSetup(false);
    }
  };

  const addDynamicField = async () => {
    if (!newFieldName.trim() || !newFieldValue.trim()) {
      showError('نام و مقدار فیلد الزامی است');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newFieldName,
          value: newFieldValue,
          target_models: newFieldModels,
          trigger: {
            enabled: newFieldTriggerEnabled,
            interval_minutes: newFieldTriggerInterval,
            interval_type: newFieldTriggerType,
          },
          action_type: newFieldActionType,
          target_path: newFieldTargetPath || undefined,
          archive_after_run: newFieldArchiveAfterRun,
          deploy_after_commit: newFieldDeployAfterCommit,
          field_type: newFieldType,
          priority: newFieldPriority,
        }),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فیلد جدید اضافه شد');
        setNewFieldName('');
        setNewFieldValue('');
        setNewFieldModels(['all']);
        setNewFieldTriggerEnabled(false);
        setNewFieldTriggerInterval(60);
        setNewFieldTriggerType('minutes');
        setNewFieldActionType('display');
        setNewFieldTargetPath('');
        setNewFieldArchiveAfterRun(false);
        setNewFieldDeployAfterCommit(false);
        setNewFieldType('temporary');
        setNewFieldPriority(5);
        setShowNewFieldForm(false);
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const updateDynamicField = async (field: DynamicField) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${field.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(field),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فیلد بروزرسانی شد');
        setEditingField(null);
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const deleteDynamicField = async (fieldId: string) => {
    if (!confirm('حذف شود؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فیلد حذف شد');
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  // روشن/خاموش کردن تریگر
  const toggleFieldTrigger = async (fieldId: string, enabled: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}/trigger/toggle?enabled=${enabled}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(data.message);
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  // اجرای دستی تریگر
  const executeFieldTrigger = async (fieldId: string) => {
    setExecutingTrigger(fieldId);

    // 🆕 اعتبارسنجی قبل از اجرا
    const field = dynamicFields.find(f => f.id === fieldId);
    if (field && (field.validation_marker === 'auto_pending' || field.source_issue_id)) {
      const validation = await preValidateField(fieldId);
      if (!validation.can_execute) {
        setExecutingTrigger(null);
        const proceed = confirm(`⚠️ هشدار اعتبارسنجی\n\n${validation.reason}\n\n📋 توصیه: ${validation.recommendation}\n\nآیا باز هم می‌خواهید اجرا کنید؟`);
        if (!proceed) {
          return;
        }
      }
    }

    // فعال کردن ویژوالیزیشن workflow - نشان دادن که trigger در حال اجراست
    const triggerNodeId = `trigger_${fieldId}`;
    setActiveWorkflow({
      nodeIds: [triggerNodeId, 'ai_process'],
      edgeIds: ['trigger_to_ai'],
      type: 'trigger',
    });

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}/trigger/execute`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        // ساخت پیام موفقیت با جزئیات
        let successMsg = `تریگر "${data.field_name}" اجرا شد`;
        let workflowNodes: string[] = ['ai_process'];
        let workflowEdges: string[] = [];

        // اگر GitHub commits داشتیم
        if (data.github_commits && data.github_commits.length > 0) {
          const successCommits = data.github_commits.filter((c: any) => c.success);
          if (successCommits.length > 0) {
            successMsg += ` | ${successCommits.length} فایل commit شد`;
            workflowNodes.push('github', 'code_files');
            workflowEdges.push('ai_to_github', 'github_to_files');

            // سینک خودکار از GitHub و بروزرسانی دیاگرام - بر اساس تنظیمات
            if (syncSettings.sync_after_field_execution || syncSettings.sync_after_commit) {
              setTimeout(async () => {
                try {
                  // سینک فایل‌ها از GitHub
                  await fetch(`${API_BASE}/api/github/imported/${projectId}/refresh`, {
                    method: 'POST',
                  });
                  // ریلود پروژه برای نمایش فایل‌های جدید
                  loadProject();
                  // بروزرسانی دیاگرام ساختار - بر اساس تنظیمات
                  if (syncSettings.update_diagram_after_sync || syncSettings.update_structure_after_sync) {
                    loadStructure();
                  }
                  showSuccess('✅ سینک خودکار از GitHub انجام شد');
                } catch (e) {
                  console.log('Auto-sync error:', e);
                }
              }, 2000);
            }
          }
        }

        // اگر Deploy انجام شد
        if (data.deploy_result) {
          if (data.deploy_result.success) {
            successMsg += ` | 🚀 Deploy شروع شد`;
            workflowNodes.push('render', 'deploy');
            workflowEdges.push('github_to_render', 'render_to_deploy');
          } else {
            showError(`خطا در Deploy: ${data.deploy_result.error}`);
          }
        }

        // بروزرسانی workflow visualization با مسیر نهایی
        setActiveWorkflow({
          nodeIds: workflowNodes,
          edgeIds: workflowEdges,
          type: data.deploy_result?.success ? 'deploy' : (data.github_commits?.length > 0 ? 'commit' : 'trigger'),
        });

        showSuccess(successMsg);
        loadMemory();

        // نمایش نتایج در console
        console.log('Trigger execution results:', data.results);
        if (data.github_commits) console.log('GitHub commits:', data.github_commits);
        if (data.deploy_result) console.log('Deploy result:', data.deploy_result);
      } else {
        showError(data.detail || 'خطا در اجرای تریگر');
        // ریست کردن workflow در صورت خطا
        setActiveWorkflow({ nodeIds: [], edgeIds: [], type: null });
      }
    } catch (e) {
      showError('خطا در ارتباط');
      setActiveWorkflow({ nodeIds: [], edgeIds: [], type: null });
    } finally {
      setExecutingTrigger(null);
    }
  };

  // اجرای گروهی فیلدها
  const executeBatchFields = async () => {
    if (selectedFields.length === 0) {
      showError('لطفاً حداقل یک فیلد انتخاب کنید');
      return;
    }

    setExecutingBatch(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/batch-execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          field_ids: selectedFields,
          execute_type: 'selected',
          auto_prioritize: true,
        }),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(`${data.success_count || data.executed_count || 0} فیلد با موفقیت اجرا شد`);
        setSelectedFields([]);
        loadMemory();

        // سینک خودکار بعد از اجرا
        if (syncSettings.sync_after_field_execution) {
          setTimeout(async () => {
            try {
              await fetch(`${API_BASE}/api/github/imported/${projectId}/refresh`, { method: 'POST' });
              loadProject();
              if (syncSettings.update_diagram_after_sync) {
                loadStructure();
              }
            } catch (e) {
              console.log('Auto-sync error:', e);
            }
          }, 2000);
        }
      } else {
        showError(data.detail || 'خطا در اجرای گروهی');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setExecutingBatch(false);
    }
  };

  // انتخاب/عدم انتخاب همه فیلدها
  const toggleSelectAll = () => {
    const activeFields = dynamicFields.filter((f: any) => !f.archived);
    if (selectedFields.length === activeFields.length) {
      setSelectedFields([]);
    } else {
      setSelectedFields(activeFields.map((f: any) => f.id));
    }
  };

  // 🔴 کنترل اجرای گروهی (Pause/Resume/Stop)
  const controlBatchExecution = async (action: 'pause' | 'resume' | 'stop') => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/batch-control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (data.success) {
        setBatchStatus(prev => ({ ...prev, status: data.status }));
        if (action === 'stop') {
          setExecutingBatch(false);
          showSuccess('اجرا متوقف شد');
        } else if (action === 'pause') {
          showSuccess('اجرا موقتاً متوقف شد');
        } else {
          showSuccess('اجرا از سر گرفته شد');
        }
      }
    } catch (e) {
      showError('خطا در کنترل اجرا');
    }
  };

  // 🔴 دریافت وضعیت اجرای گروهی
  const fetchBatchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/batch-status`);
      const data = await res.json();
      if (data.success) {
        setBatchStatus({
          status: data.status,
          progress: data.progress_percent,
          current: data.current_index,
          total: data.total_fields,
          currentFieldName: data.current_field_name,
          archivedCount: data.archived_count,
          completedCount: data.completed_count,
          failedCount: data.failed_count,
        });
        // وقتی اجرا تمام شد
        if ((data.status === 'idle' || data.status === 'completed') && executingBatch) {
          setExecutingBatch(false);
          loadMemory();  // بارگذاری مجدد برای دیدن فیلدهای بایگانی شده
          if (data.completed_count > 0) {
            showSuccess(`اجرای گروهی تمام شد: ${data.completed_count} موفق، ${data.archived_count || 0} بایگانی شده`);
          }
        }
      }
    } catch (e) {
      console.log('Error fetching batch status:', e);
    }
  };

  // 🔴 حذف گروهی فیلدها
  const deleteBatchFields = async () => {
    if (selectedFields.length === 0) {
      showError('لطفاً حداقل یک فیلد انتخاب کنید');
      return;
    }
    if (!confirm(`آیا از حذف ${selectedFields.length} فیلد مطمئن هستید؟`)) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/batch-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_ids: selectedFields }),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(`${data.deleted_count} فیلد حذف شد`);
        setSelectedFields([]);
        loadMemory();
      } else {
        showError(data.detail || 'خطا در حذف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  // 🔴 Polling وضعیت اجرا هنگام running
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (executingBatch || batchStatus.status === 'running' || batchStatus.status === 'paused') {
      interval = setInterval(fetchBatchStatus, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [executingBatch, batchStatus.status]);

  // آپلود پیوست برای فیلد
  const uploadAttachment = async (fieldId: string, file: File) => {
    setUploadingAttachment(fieldId);
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = (e.target?.result as string)?.split(',')[1];
        const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}/attachments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            field_id: fieldId,
            file_content: base64,
            file_name: file.name,
            file_type: file.type,
          }),
        });
        const data = await res.json();
        if (data.success) {
          showSuccess('پیوست اضافه شد');
          loadMemory();
        } else {
          showError(data.detail || 'خطا در آپلود');
        }
        setUploadingAttachment(null);
      };
      reader.readAsDataURL(file);
    } catch (e) {
      showError('خطا در خواندن فایل');
      setUploadingAttachment(null);
    }
  };

  // حذف پیوست
  const deleteAttachment = async (fieldId: string, attachmentIdOrPath: string) => {
    if (!confirm('پیوست حذف شود؟')) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}/attachments/${encodeURIComponent(attachmentIdOrPath)}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('پیوست حذف شد');
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا');
    }
  };

  // دریافت آیکون اولویت
  const getPriorityIcon = (priority: number) => {
    if (priority <= 2) return '🔴';
    if (priority <= 4) return '🟠';
    if (priority <= 6) return '🟢';
    if (priority <= 8) return '🔵';
    return '⚪';
  };

  // دریافت نام اولویت
  const getPriorityName = (priority: number) => {
    if (priority === 1) return 'بحرانی';
    if (priority <= 3) return 'بالا';
    if (priority <= 5) return 'عادی';
    if (priority <= 7) return 'پایین';
    return 'خیلی پایین';
  };

  const toggleModel = (modelId: string, currentModels: string[], setModels: (m: string[]) => void) => {
    if (modelId === 'all') {
      setModels(['all']);
    } else {
      let newModels = currentModels.filter(m => m !== 'all');
      if (newModels.includes(modelId)) {
        newModels = newModels.filter(m => m !== modelId);
      } else {
        newModels.push(modelId);
      }
      if (newModels.length === 0) {
        newModels = ['all'];
      }
      setModels(newModels);
    }
  };

  const loadFileContent = async (filePath: string) => {
    try {
      let res;
      if (projectId.startsWith('gh_')) {
        res = await fetch(`${API_BASE}/api/github/imported/${projectId}/file?path=${encodeURIComponent(filePath)}`);
      } else {
        res = await fetch(`${API_BASE}/api/projects/${projectId}/files/${encodeURIComponent(filePath)}`);
      }

      if (res.ok) {
        const data = await res.json();
        setSelectedFile({
          path: filePath,
          content: data.content,
          github_url: data.github_url,
        });
      } else {
        showError('فایل یافت نشد');
      }
    } catch (e) {
      showError('خطا در خواندن فایل');
    }
  };

  const deployToRender = async () => {
    setDeploying(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/deploy/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      if (data.success) {
        showSuccess(`Deploy شروع شد! ${data.deploy_url || ''}`);
      } else {
        showError(data.error || 'خطا در Deploy');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setDeploying(false);
    }
  };

  // تست Deploy به Render (برای دیباگ)
  const testRenderDeploy = async () => {
    setDeploying(true);
    showSuccess('🔄 در حال جستجوی سرویس‌های Render...');

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/deploy/test`, {
        method: 'POST',
      });
      const data = await res.json();

      console.log('Deploy Result:', data);

      if (data.success) {
        // اگر چند سرویس deploy شد
        if (data.deploy_result?.multiple_services) {
          const results = data.deploy_result.services_deployed;
          const successCount = results.filter((r: any) => r.success).length;
          showSuccess(`✅ Deploy شروع شد برای ${successCount}/${results.length} سرویس: ${results.map((r: any) => r.name).join(', ')}`);
        } else {
          showSuccess('✅ Deploy شروع شد! وضعیت: ' + (data.deploy_result?.status || 'pending'));
        }
      } else {
        // اگر سرویس مطابق پیدا نشد ولی لیست سرویس‌ها موجوده
        if (data.deploy_result?.available_services || data.available_services) {
          const services = data.deploy_result?.available_services || data.available_services;
          // نمایش مودال انتخاب سرویس با چک‌باکس
          setAvailableRenderServices(services);
          setSelectedRenderServices([]);
          setShowServiceSelector(true);
          return;
        }

        let errorMsg = data.error || data.deploy_result?.error || 'خطا در Deploy';

        if (errorMsg.includes('API key') || errorMsg.includes('not set')) {
          errorMsg = '❌ کلید API رندر تنظیم نشده. Settings → Deploy Keys';
        } else if (errorMsg.includes('No Render service')) {
          errorMsg = '❌ سرویسی در Render پیدا نشد. ابتدا پروژه را در Render deploy کنید.';
        }

        console.log('Debug Info:', data.debug_info);
        showError(errorMsg);
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setDeploying(false);
    }
  };

  // ذخیره سرویس‌های Render انتخاب شده و اجرای Deploy
  const saveSelectedRenderServices = async () => {
    if (selectedRenderServices.length === 0) {
      showError('لطفاً حداقل یک سرویس انتخاب کنید');
      return;
    }

    setDeploying(true);
    try {
      // ذخیره سرویس‌های انتخاب شده در پروژه
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/deploy/set-services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_ids: selectedRenderServices,
          services: availableRenderServices.filter(s => selectedRenderServices.includes(s.id))
        }),
      });
      const data = await res.json();

      if (data.success) {
        setSavedRenderServices(availableRenderServices.filter(s => selectedRenderServices.includes(s.id)));
        setShowServiceSelector(false);
        showSuccess(`✅ ${selectedRenderServices.length} سرویس ذخیره شد. در حال Deploy...`);

        // 🔴 بلافاصله Deploy را اجرا کن
        const deployRes = await fetch(`${API_BASE}/api/projects/${projectId}/deploy/test`, {
          method: 'POST',
        });
        const deployData = await deployRes.json();

        if (deployData.success) {
          if (deployData.deploy_result?.multiple_services) {
            const results = deployData.deploy_result.services_deployed;
            const successCount = results.filter((r: any) => r.success).length;
            showSuccess(`✅ Deploy شروع شد برای ${successCount}/${results.length} سرویس`);
          } else {
            showSuccess('✅ Deploy شروع شد! وضعیت: ' + (deployData.deploy_result?.status || 'pending'));
          }
        } else {
          showError('سرویس‌ها ذخیره شدند ولی Deploy با خطا مواجه شد: ' + (deployData.error || ''));
        }
      } else {
        showError(data.error || 'خطا در ذخیره');
      }
    } catch {
      showError('خطا در ارتباط');
    } finally {
      setDeploying(false);
    }
  };

  // 🆕 ایجاد هوشمند سرویس Render (تحلیل خودکار ساختار پروژه)
  const createRenderServiceSmart = async () => {
    setCreateRenderLoading(true);
    setShowCreateRenderService(false);

    // پیام شروع تحلیل در چت
    const startMsgId = `render-ai-start-${Date.now()}`;
    setInspectorChatMessages(prev => [...prev, {
      id: startMsgId,
      role: 'system' as const,
      content: '🤖 در حال تحلیل ساختار پروژه توسط هوش مصنوعی برای ایجاد سرویس‌های Render...',
      timestamp: new Date(),
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/render/inspector/create-render-service`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId }),
      });
      const data = await res.json();

      if (data.success) {
        // ساخت پیام نتیجه برای چت
        let resultContent = `🤖 **تحلیل AI** (مدل: ${data.model_used || 'نامشخص'})\n\n`;
        if (data.analysis) {
          resultContent += `📋 ${data.analysis}\n\n`;
        }
        resultContent += `✅ **${(data.created || []).length} سرویس با موفقیت ایجاد شد:**\n`;
        for (const svc of (data.created || [])) {
          resultContent += `\n🔹 **${svc.name}** (${svc.role}) — نوع: ${svc.service_type}`;
          if (svc.url) resultContent += `\n   🔗 ${svc.url}`;
          if (svc.dashboard_url) resultContent += `\n   ⚙️ [داشبورد](${svc.dashboard_url})`;
          if (svc.notes) resultContent += `\n   📝 ${svc.notes}`;
        }

        // هشدار env vars خالی
        const emptyVars = data.empty_env_vars || [];
        if (emptyVars.length > 0) {
          resultContent += `\n\n⚠️ **متغیرهای محیطی زیر مقدار ندارند** (در داشبورد Render تنظیم کنید):\n`;
          for (const ev of emptyVars) {
            resultContent += `\n  • ${ev}`;
          }
        }

        // خطاها
        if ((data.errors || []).length > 0) {
          resultContent += `\n\n❌ **خطا در ایجاد:**\n`;
          for (const err of data.errors) {
            resultContent += `\n  • ${err.name} (${err.role}): ${err.error}`;
          }
        }

        setInspectorChatMessages(prev => [...prev, {
          id: `render-ai-result-${Date.now()}`,
          role: 'assistant' as const,
          content: resultContent,
          model_id: data.model_used,
          timestamp: new Date(),
        }]);

        showSuccess(data.message);
        loadInspectorServices(true);
      } else {
        // نتیجه ناموفق در چت
        let errorContent = `❌ **خطا در ایجاد سرویس Render**\n\n${data.error || 'خطای ناشناخته'}`;
        if (data.analysis) {
          errorContent += `\n\n📋 تحلیل AI: ${data.analysis}`;
        }
        setInspectorChatMessages(prev => [...prev, {
          id: `render-ai-error-${Date.now()}`,
          role: 'system' as const,
          content: errorContent,
          timestamp: new Date(),
        }]);
        showError(data.error || 'خطا در ایجاد سرویس');
      }
    } catch {
      setInspectorChatMessages(prev => [...prev, {
        id: `render-ai-err-${Date.now()}`,
        role: 'system' as const,
        content: '❌ خطا در ارتباط با سرور برای تحلیل AI',
        timestamp: new Date(),
      }]);
      showError('خطا در ارتباط با سرور');
    } finally {
      setCreateRenderLoading(false);
    }
  };

  // تغییر انتخاب سرویس
  const toggleServiceSelection = (serviceId: string) => {
    setSelectedRenderServices(prev =>
      prev.includes(serviceId)
        ? prev.filter(id => id !== serviceId)
        : [...prev, serviceId]
    );
  };

  const generateMoreFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/creator/projects/${projectId}/generate`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فایل‌های جدید تولید شدند');
        loadProject();
      } else {
        showError(data.error || 'خطا');
      }
    } catch (e) {
      showError('خطا');
    }
  };

  // سینک فایل‌ها از GitHub
  const syncFromGitHub = async () => {
    if (!confirm('آیا می‌خواهید آخرین تغییرات را از GitHub دریافت کنید؟\n\nاین عملیات فایل‌های پروژه را با GitHub همگام‌سازی می‌کند.')) {
      return;
    }

    setLoading(true);
    showSuccess('در حال سینک با GitHub...');

    try {
      const res = await fetch(`${API_BASE}/api/github/imported/${projectId}/refresh`, {
        method: 'POST',
      });
      const data = await res.json();

      if (data.success) {
        showSuccess(`✅ سینک موفق! ${data.files_updated || 0} فایل بروزرسانی شد`);
        // ریلود پروژه
        loadProject();
      } else {
        showError(data.detail || 'خطا در سینک');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  // ارسال پیام به AI
  const sendChatMessage = async () => {
    if (!chatPrompt.trim()) {
      showError('لطفاً سوال خود را وارد کنید');
      return;
    }

    setChatLoading(true);
    setChatResponse('');
    setEnhancedChatResponses([]);
    setCreatedFieldsFromChat([]);

    try {
      if (useEnhancedChat) {
        // Enhanced Chat - با context کامل و چند مدل
        const res = await fetch(`${API_BASE}/api/projects/${projectId}/enhanced-chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: chatPrompt,
            model_ids: selectedChatModels.length > 0 ? selectedChatModels : ['openai'],
            include_memory: includeMemory,
            include_files: includeFiles,
            include_issues: includeIssues,
            include_health: includeHealth,
            create_dynamic_fields: createDynamicFields,
            auto_detect_actions: true,
          }),
        });

        const data = await res.json();
        if (data.success) {
          setEnhancedChatResponses(data.responses || []);
          if (data.created_fields && data.created_fields.length > 0) {
            setCreatedFieldsFromChat(data.created_fields);
            showSuccess(`${data.created_fields.length} فیلد پویا از پاسخ ایجاد شد`);
            // بارگذاری مجدد فیلدهای پویا
            loadMemory();
          }
          // برای سازگاری با نمایش قبلی
          if (data.responses && data.responses.length > 0) {
            const firstSuccess = data.responses.find((r: any) => r.success);
            if (firstSuccess) {
              setChatResponse(firstSuccess.content);
            }
          }
        } else {
          showError(data.detail || 'خطا در دریافت پاسخ');
        }
      } else {
        // Chat ساده قدیمی
        const res = await fetch(`${API_BASE}/api/projects/${projectId}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: chatPrompt,
            model_id: selectedChatModel,
            include_memory: includeMemory,
          }),
        });

        const data = await res.json();
        if (data.success) {
          setChatResponse(data.content);
        } else {
          showError(data.detail || 'خطا در دریافت پاسخ');
        }
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setChatLoading(false);
    }
  };

  // تغییر وضعیت انتخاب مدل برای چت چند مدله
  const toggleChatModel = (modelId: string) => {
    setSelectedChatModels(prev => {
      if (prev.includes(modelId)) {
        // حداقل یک مدل باید انتخاب باشه
        if (prev.length === 1) return prev;
        return prev.filter(m => m !== modelId);
      } else {
        return [...prev, modelId];
      }
    });
  };

  // Model selector component
  const ModelSelector = ({ selectedModels, onChange }: { selectedModels: string[], onChange: (models: string[]) => void }) => (
    <div className="flex flex-wrap gap-2 mt-2">
      {availableModels.map(model => (
        <button
          key={model.id}
          onClick={() => toggleModel(model.id, selectedModels, onChange)}
          className={`px-3 py-1 rounded-full text-xs flex items-center gap-1 transition ${
            selectedModels.includes(model.id) || (selectedModels.includes('all') && model.id === 'all')
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'
          }`}
        >
          <span>{model.icon}</span>
          <span>{model.name}</span>
        </button>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p>در حال بارگذاری پروژه...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <p className="text-xl mb-4">پروژه پیدا نشد</p>
          <Link href="/projects" className="text-blue-500 hover:underline">
            برگشت به لیست پروژه‌ها
          </Link>
        </div>
      </div>
    );
  }

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

      {/* 🔴 نمایش پرامپت‌های در حال اجرا */}
      <ExecutingPromptsPanel projectId={projectId} refreshInterval={2000} />

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Link href="/projects" className="hover:text-blue-500">پروژه‌ها</Link>
              <span>/</span>
              <span>{project.name}</span>
              {project.project_type === 'github_import' && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">GitHub</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {project.project_type === 'github_import' && (
                <svg className="w-6 h-6 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
              )}
              <h1 className="text-2xl font-bold">{project.name}</h1>
              {/* 🔗 Oversight bridge indicator — تعداد تسک‌های نظارتی این پروژه */}
              {((oversightBridgeSummary?.total || 0) + oversightExternalCount) > 0 && (
                <a
                  href={`/oversight?project=${encodeURIComponent(projectId)}`}
                  className="ml-2 px-3 py-1 bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300 rounded-full text-xs flex items-center gap-1.5 hover:bg-cyan-200 dark:hover:bg-cyan-900/50 transition-colors"
                  title={
                    `🔗 تسک‌های نظارتی این پروژه:\n` +
                    `• ${oversightBridgeSummary?.pending || 0} در انتظار\n` +
                    `• ${oversightBridgeSummary?.in_review || 0} در حال بررسی\n` +
                    `• ${oversightBridgeSummary?.done || 0} تکمیل‌شده\n` +
                    `• ${oversightExternalCount} فیلد قابل verify در مرکز نظارت\n\n` +
                    `کلیک: باز کردن /oversight با فیلتر این پروژه`
                  }
                >
                  <span>🔗</span>
                  <span>
                    {oversightBridgeSummary?.total || 0} نظارت
                    {oversightExternalCount > 0 && ` + ${oversightExternalCount} فیلد`}
                  </span>
                  {(oversightBridgeSummary?.pending || 0) > 0 && (
                    <span className="px-1.5 py-0 bg-orange-200 dark:bg-orange-900/50 text-orange-800 dark:text-orange-300 rounded-full text-xs">
                      {oversightBridgeSummary?.pending} pending
                    </span>
                  )}
                </a>
              )}
            </div>
            {project.description && (
              <p className="text-gray-500 mt-1">{project.description}</p>
            )}
          </div>
          <div className="flex gap-2">
            {project.project_type === 'github_import' && project.metadata?.source_url && (
              <a
                href={project.metadata.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 flex items-center gap-2"
              >
                مشاهده در GitHub
              </a>
            )}
            {project.project_type !== 'github_import' && (
              <>
                <button
                  onClick={generateMoreFiles}
                  className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
                >
                  🔄 تولید بیشتر
                </button>
                <button
                  onClick={deployToRender}
                  disabled={deploying}
                  className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                >
                  {deploying ? '⏳ در حال Deploy...' : '🚀 Deploy'}
                </button>
              </>
            )}
            {/* دکمه‌های GitHub */}
            {project.project_type === 'github_import' && (
              <>
                <div className="flex items-center gap-1">
                  <button
                    onClick={syncFromGitHub}
                    disabled={loading}
                    className="px-4 py-2 bg-blue-500 text-white rounded-r-lg hover:bg-blue-600 disabled:opacity-50"
                    title="دریافت آخرین تغییرات از GitHub"
                  >
                    {loading ? '⏳...' : '🔄 سینک از GitHub'}
                  </button>
                  <button
                    onClick={() => setShowSyncSettings(true)}
                    className="px-2 py-2 bg-blue-600 text-white rounded-l-lg hover:bg-blue-700"
                    title="تنظیمات سینک"
                  >
                    ⚙️
                  </button>
                </div>
                {syncSettings.auto_sync_enabled && (
                  <span className="text-xs text-green-500 flex items-center gap-1">
                    <span className="animate-pulse">●</span>
                    سینک خودکار: هر {syncSettings.sync_interval_minutes} دقیقه
                  </span>
                )}
                <button
                  onClick={testRenderDeploy}
                  disabled={deploying}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50"
                  title="تست اتصال به Render و دیباگ مشکلات Deploy"
                >
                  {deploying ? '⏳...' : '🧪 تست Deploy'}
                </button>
              </>
            )}
            <Link
              href="/projects"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
            >
              برگشت
            </Link>
          </div>
        </div>

        {/* تب‌ها */}
        <div className="flex border-b mb-6">
          <button
            onClick={() => setActiveTab('files')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'files'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            📁 فایل‌ها
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'memory'
                ? 'border-b-2 border-purple-500 text-purple-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🧠 حافظه و دستورات AI
          </button>
          <button
            onClick={() => setActiveTab('structure')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'structure'
                ? 'border-b-2 border-green-500 text-green-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🔀 ساختار پروژه
          </button>
          <button
            onClick={() => setActiveTab('journal')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'journal'
                ? 'border-b-2 border-orange-500 text-orange-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            📊 ژورنال و گزارشات
          </button>
          <button
            onClick={() => setActiveTab('health')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'health'
                ? 'border-b-2 border-teal-500 text-teal-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🏥 تحلیل سلامت
          </button>
          <button
            onClick={() => setActiveTab('inspector')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'inspector'
                ? 'border-b-2 border-red-500 text-red-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🔍 بازرس ویژه
          </button>
          <button
            onClick={() => setActiveTab('external')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'external'
                ? 'border-b-2 border-cyan-500 text-cyan-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            title="اتصال به repo خارجی GitHub با URL + توکن جداگانه برای تحلیل و مرور فایل‌ها"
          >
            🔗 External
          </button>
        </div>

        {/* محتوای تب فایل‌ها */}
        {activeTab === 'files' && (
          <>
            {/* اطلاعات پروژه - GitHub */}
            {project.project_type === 'github_import' && project.metadata && (
              <div className="grid grid-cols-5 gap-4 mb-6">
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">⭐</div>
                  <div className="font-bold">{project.metadata.stats?.stars || 0}</div>
                  <div className="text-xs text-gray-500">ستاره</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">🍴</div>
                  <div className="font-bold">{project.metadata.stats?.forks || 0}</div>
                  <div className="text-xs text-gray-500">فورک</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">📄</div>
                  <div className="font-bold">{files.length}</div>
                  <div className="text-xs text-gray-500">فایل</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">💻</div>
                  <div className="font-bold text-sm">{project.metadata.primary_language || '-'}</div>
                  <div className="text-xs text-gray-500">زبان</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">{project.metadata.private ? '🔒' : '🌐'}</div>
                  <div className="font-bold text-sm">{project.metadata.private ? 'خصوصی' : 'عمومی'}</div>
                  <div className="text-xs text-gray-500">دسترسی</div>
                </div>
              </div>
            )}

            <div className="grid lg:grid-cols-3 gap-6">
              {/* لیست فایل‌ها */}
              <div className="lg:col-span-1">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
                  <h2 className="font-bold mb-4">📁 فایل‌های پروژه ({files.length})</h2>

                  {files.length === 0 ? (
                    <div className="text-center py-8 text-gray-400">
                      <div className="text-4xl mb-2">📭</div>
                      <p>{project.project_type === 'github_import' ? 'فایلی import نشده' : 'هنوز فایلی تولید نشده'}</p>
                    </div>
                  ) : (
                    <div className="space-y-1 max-h-[60vh] overflow-auto">
                      {files.map((file, idx) => {
                        const isSelected = selectedFile?.path === file.path;
                        return (
                          <div
                            key={idx}
                            onClick={() => loadFileContent(file.path)}
                            className={`p-2 rounded cursor-pointer text-sm ${
                              isSelected
                                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600'
                                : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span>📄</span>
                              <span className="truncate font-mono text-xs" title={file.path}>{file.path}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* محتوای فایل */}
              <div className="lg:col-span-2">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-bold">
                      {selectedFile ? `📄 ${selectedFile.path}` : '📝 محتوای فایل'}
                    </h2>
                    {selectedFile?.github_url && (
                      <a
                        href={selectedFile.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-500 hover:underline"
                      >
                        مشاهده در GitHub
                      </a>
                    )}
                  </div>

                  {selectedFile?.content ? (
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto max-h-[70vh] text-sm">
                      <code>{selectedFile.content}</code>
                    </pre>
                  ) : (
                    <div className="text-center py-12 text-gray-400">
                      <div className="text-6xl mb-4">👈</div>
                      <p>یک فایل از سمت راست انتخاب کنید</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* باکس چت با AI */}
            <div className="mt-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow">
                {/* هدر چت */}
                <div
                  onClick={() => setShowChatBox(!showChatBox)}
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-xl"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🤖</span>
                    <h3 className="font-bold">پرسش از AI درباره پروژه</h3>
                    {useEnhancedChat && (
                      <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-300 text-xs rounded-full">
                        پیشرفته
                      </span>
                    )}
                  </div>
                  <span className="text-gray-400">{showChatBox ? '▲' : '▼'}</span>
                </div>

                {/* محتوای چت */}
                {showChatBox && (
                  <div className="p-4 border-t dark:border-gray-700">
                    {/* سوییچ حالت پیشرفته */}
                    <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <label className="flex items-center gap-2 text-sm font-medium">
                          <input
                            type="checkbox"
                            checked={useEnhancedChat}
                            onChange={(e) => setUseEnhancedChat(e.target.checked)}
                            className="rounded text-purple-500"
                          />
                          <span>🚀 حالت پیشرفته</span>
                          <span className="text-xs text-gray-500">(دسترسی کامل به فایل‌ها + چند مدل)</span>
                        </label>
                      </div>

                      {useEnhancedChat && (
                        <>
                          {/* انتخاب چند مدل */}
                          <div className="mb-3">
                            <label className="text-xs text-gray-600 dark:text-gray-400 block mb-2">
                              انتخاب مدل‌ها (می‌توانید چند مدل انتخاب کنید):
                            </label>
                            <div className="flex flex-wrap gap-2">
                              {availableModels.filter(m => m.id !== 'all').map(model => (
                                <button
                                  key={model.id}
                                  onClick={() => toggleChatModel(model.id)}
                                  className={`px-3 py-1.5 rounded-full text-xs flex items-center gap-1 transition border ${
                                    selectedChatModels.includes(model.id)
                                      ? 'bg-purple-500 text-white border-purple-500'
                                      : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-purple-400'
                                  }`}
                                >
                                  <span>{model.icon}</span>
                                  <span>{model.name}</span>
                                  {selectedChatModels.includes(model.id) && <span>✓</span>}
                                </button>
                              ))}
                            </div>
                            {selectedChatModels.length > 1 && (
                              <p className="text-xs text-purple-600 dark:text-purple-400 mt-2">
                                ✨ {selectedChatModels.length} مدل انتخاب شده - پاسخ همه آن‌ها نمایش داده می‌شود
                              </p>
                            )}
                          </div>

                          {/* تنظیمات context */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                            <label className="flex items-center gap-1.5 text-xs">
                              <input
                                type="checkbox"
                                checked={includeFiles}
                                onChange={(e) => setIncludeFiles(e.target.checked)}
                                className="rounded text-purple-500 w-3.5 h-3.5"
                              />
                              <span>📁 محتوای فایل‌ها</span>
                            </label>
                            <label className="flex items-center gap-1.5 text-xs">
                              <input
                                type="checkbox"
                                checked={includeIssues}
                                onChange={(e) => setIncludeIssues(e.target.checked)}
                                className="rounded text-purple-500 w-3.5 h-3.5"
                              />
                              <span>🐛 ایرادات شناسایی‌شده</span>
                            </label>
                            <label className="flex items-center gap-1.5 text-xs">
                              <input
                                type="checkbox"
                                checked={includeHealth}
                                onChange={(e) => setIncludeHealth(e.target.checked)}
                                className="rounded text-purple-500 w-3.5 h-3.5"
                              />
                              <span>💚 وضعیت سلامت</span>
                            </label>
                            <label className="flex items-center gap-1.5 text-xs">
                              <input
                                type="checkbox"
                                checked={includeMemory}
                                onChange={(e) => setIncludeMemory(e.target.checked)}
                                className="rounded text-purple-500 w-3.5 h-3.5"
                              />
                              <span>🧠 دستورات حافظه</span>
                            </label>
                          </div>

                          {/* تبدیل به فیلد پویا */}
                          <label className="flex items-center gap-2 text-xs p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
                            <input
                              type="checkbox"
                              checked={createDynamicFields}
                              onChange={(e) => setCreateDynamicFields(e.target.checked)}
                              className="rounded text-yellow-500 w-3.5 h-3.5"
                            />
                            <span>✨ تبدیل خودکار پاسخ به فیلدهای پویا</span>
                            <span className="text-yellow-600 dark:text-yellow-400">(با تشخیص اولویت و نوع اقدام)</span>
                          </label>
                        </>
                      )}

                      {!useEnhancedChat && (
                        <div className="flex items-center gap-3">
                          <label className="text-xs text-gray-600 dark:text-gray-400">مدل:</label>
                          <select
                            value={selectedChatModel}
                            onChange={(e) => setSelectedChatModel(e.target.value)}
                            className="px-3 py-1 border rounded-lg text-xs dark:bg-gray-700 dark:border-gray-600"
                          >
                            {availableModels.filter(m => m.id !== 'all').map(model => (
                              <option key={model.id} value={model.id}>
                                {model.icon} {model.name}
                              </option>
                            ))}
                          </select>
                          <label className="flex items-center gap-1.5 text-xs">
                            <input
                              type="checkbox"
                              checked={includeMemory}
                              onChange={(e) => setIncludeMemory(e.target.checked)}
                              className="rounded w-3.5 h-3.5"
                            />
                            استفاده از دستورات حافظه
                          </label>
                        </div>
                      )}
                    </div>

                    {/* ورودی پرامپت */}
                    <div className="flex gap-2">
                      <textarea
                        value={chatPrompt}
                        onChange={(e) => setChatPrompt(e.target.value)}
                        placeholder={useEnhancedChat
                          ? "سوال خود را بپرسید... AI به تمام فایل‌ها و داده‌های پروژه دسترسی دارد و دقیق پاسخ می‌دهد."
                          : "سوال خود را درباره پروژه بپرسید..."
                        }
                        className="flex-1 p-3 border rounded-lg resize-none dark:bg-gray-700 dark:border-gray-600 text-sm"
                        rows={3}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendChatMessage();
                          }
                        }}
                      />
                      <button
                        onClick={sendChatMessage}
                        disabled={chatLoading || !chatPrompt.trim()}
                        className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 self-end font-medium"
                      >
                        {chatLoading ? '⏳' : '📤 ارسال'}
                      </button>
                    </div>

                    {/* نمایش در حال پردازش */}
                    {chatLoading && (
                      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="flex items-center gap-3 text-gray-500">
                          <div className="animate-spin text-2xl">⏳</div>
                          <div>
                            <p className="font-medium">در حال پردازش...</p>
                            {useEnhancedChat && selectedChatModels.length > 1 && (
                              <p className="text-xs">ارسال به {selectedChatModels.length} مدل همزمان</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* پاسخ‌های چند مدل (حالت پیشرفته) */}
                    {!chatLoading && useEnhancedChat && enhancedChatResponses.length > 0 && (
                      <div className="mt-4 space-y-4">
                        {enhancedChatResponses.map((response, index) => (
                          <div
                            key={index}
                            className={`p-4 rounded-lg border ${
                              response.success
                                ? 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                                : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2 text-sm font-medium">
                                <span>🤖</span>
                                <span>
                                  {availableModels.find(m => m.id === response.model_id)?.name || response.model_id}
                                </span>
                                {response.actual_model && response.actual_model !== response.model_id && (
                                  <span className="text-xs text-gray-400">({response.actual_model})</span>
                                )}
                              </div>
                              {response.success && (
                                <div className="flex items-center gap-3 text-xs text-gray-400">
                                  {response.tokens_used && <span>🎯 {response.tokens_used} توکن</span>}
                                  {response.latency_ms && <span>⚡ {(response.latency_ms / 1000).toFixed(1)}s</span>}
                                </div>
                              )}
                            </div>

                            {response.success ? (
                              <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap">
                                {response.content}
                              </div>
                            ) : (
                              <div className="text-red-600 dark:text-red-400 text-sm">
                                ❌ خطا: {response.error}
                              </div>
                            )}
                          </div>
                        ))}

                        {/* فیلدهای ایجاد شده */}
                        {createdFieldsFromChat.length > 0 && (
                          <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                            <h4 className="font-medium text-green-700 dark:text-green-300 mb-2 flex items-center gap-2">
                              <span>✅</span>
                              <span>{createdFieldsFromChat.length} فیلد پویا ایجاد شد:</span>
                            </h4>
                            <ul className="text-sm space-y-1">
                              {createdFieldsFromChat.map((field, i) => (
                                <li key={i} className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                                  <span className={`w-2 h-2 rounded-full ${
                                    field.priority && field.priority <= 2 ? 'bg-red-500' :
                                    field.priority && field.priority <= 4 ? 'bg-yellow-500' : 'bg-green-500'
                                  }`}></span>
                                  <span className="font-medium">{field.name}</span>
                                  <span className="text-xs text-gray-400">
                                    ({field.action_type === 'github_commit' ? '📤 Commit' :
                                      field.action_type === 'github_multi_commit' ? '📦 Multi-Commit' : '👁️ نمایش'})
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* پاسخ ساده (حالت قدیمی) */}
                    {!chatLoading && !useEnhancedChat && chatResponse && (
                      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
                          <span>🤖</span>
                          <span>پاسخ {availableModels.find(m => m.id === selectedChatModel)?.name || selectedChatModel}:</span>
                        </div>
                        <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap">
                          {chatResponse}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* محتوای تب حافظه */}
        {activeTab === 'memory' && (
          <div className="space-y-6">
            {/* دکمه راه‌اندازی خودکار جامع */}
            <div className="bg-gradient-to-r from-purple-600 via-blue-500 to-cyan-500 rounded-xl shadow-lg p-5 text-white">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex-1 min-w-[250px]">
                  <h3 className="font-bold text-lg flex items-center gap-2">
                    🚀 راه‌اندازی خودکار جامع
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">AI + GitHub</span>
                  </h3>
                  <ul className="text-sm opacity-90 mt-2 space-y-1">
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
                      سینک کامل با GitHub و بررسی تغییرات
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
                      حذف خودکار محتوای نامعتبر و منسوخ
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
                      ایجاد/به‌روزرسانی/ادغام فیلدهای پویا
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
                      ثبت کامل عملیات در ژورنال (قابل کلیک)
                    </li>
                  </ul>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowAutoSetupPrompts(true)}
                    className="px-4 py-3 bg-white/20 hover:bg-white/30 rounded-xl font-medium text-sm flex items-center gap-2 transition-all"
                    title="مدیریت پرامپت‌ها"
                  >
                    <span>📝</span>
                    <span>پرامپت‌ها</span>
                  </button>
                  <button
                    onClick={runAutoSetup}
                    disabled={runningAutoSetup}
                    className="px-6 py-3 bg-white text-purple-600 rounded-xl font-bold hover:bg-gray-100 disabled:opacity-50 shadow-lg transform hover:scale-105 transition-all flex items-center gap-2"
                  >
                    {runningAutoSetup ? (
                      <>
                        <span className="animate-spin">⚙️</span>
                        <span>در حال پردازش...</span>
                      </>
                    ) : (
                      <>
                        <span>✨</span>
                        <span>راه‌اندازی خودکار</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
              {runningAutoSetup && (
                <div className="mt-4 bg-white/10 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>در حال تحلیل هوشمند... لطفاً صبر کنید</span>
                  </div>
                  <div className="mt-2 h-1 bg-white/20 rounded-full overflow-hidden">
                    <div className="h-full bg-white/60 rounded-full animate-pulse" style={{ width: '70%' }}></div>
                  </div>
                </div>
              )}
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
            {/* باکس حافظه - دستورات ثابت */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-2xl">🧠</span>
                <h2 className="font-bold text-lg">باکس حافظه (دستورات ثابت)</h2>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                دستوراتی که همیشه توسط مدل‌های AI در این پروژه رعایت می‌شوند
              </p>

              <textarea
                value={memoryInstructions.content}
                onChange={(e) => setMemoryInstructions({ ...memoryInstructions, content: e.target.value })}
                placeholder="مثال: همیشه کدها را به زبان فارسی کامنت‌گذاری کن. از TypeScript استفاده کن. کدها باید تست‌پذیر باشند..."
                className="w-full h-48 p-4 border rounded-lg resize-none dark:bg-gray-700 dark:border-gray-600 text-sm"
                dir="rtl"
              />

              <div className="mt-4">
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  این دستورات برای کدام مدل‌ها اعمال شود؟
                </label>
                <ModelSelector
                  selectedModels={memoryInstructions.target_models}
                  onChange={(models) => setMemoryInstructions({ ...memoryInstructions, target_models: models })}
                />
              </div>

              <button
                onClick={saveMemoryInstructions}
                disabled={savingMemory}
                className="mt-4 w-full py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
              >
                {savingMemory ? '⏳ در حال ذخیره...' : '💾 ذخیره باکس حافظه'}
              </button>
            </div>

            {/* فیلدهای پویا */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">📝</span>
                  <h2 className="font-bold text-lg">فیلدهای پویا</h2>
                  {/* 🆕 نشانگر تعداد در انتظار تایید */}
                  {(pendingApprovals?.total ?? 0) > 0 && (
                    <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 text-xs rounded-full">
                      {pendingApprovals.total} در انتظار
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {/* 🆕 دکمه درخواست قابلیت */}
                  <button
                    onClick={() => setShowFeatureRequestForm(true)}
                    className="px-3 py-1 bg-purple-500 text-white rounded-lg text-sm hover:bg-purple-600 flex items-center gap-1"
                    title="درخواست قابلیت جدید"
                  >
                    ✨ قابلیت جدید
                  </button>
                  {/* 🆕 دکمه تایید سریع */}
                  <button
                    onClick={() => {
                      loadPendingApprovals();
                      setShowQuickApprovalPanel(!showQuickApprovalPanel);
                    }}
                    className={`px-3 py-1 rounded-lg text-sm flex items-center gap-1 ${
                      showQuickApprovalPanel
                        ? 'bg-amber-600 text-white'
                        : 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 hover:bg-amber-200'
                    }`}
                    title="تایید سریع فیلدها"
                  >
                    ⚡ تایید سریع
                  </button>
                  <button
                    onClick={() => setShowNewFieldForm(true)}
                    className="px-3 py-1 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600"
                  >
                    + افزودن فیلد
                  </button>
                </div>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                دستورات متغیر که ممکن است زود به زود تغییر کنند
              </p>

              {/* 🆕 فرم درخواست قابلیت جدید */}
              {showFeatureRequestForm && (
                <div className="mb-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium flex items-center gap-2">
                      <span>✨</span> درخواست قابلیت جدید
                    </h3>
                    <button
                      onClick={() => setShowFeatureRequestForm(false)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ✕
                    </button>
                  </div>

                  <input
                    type="text"
                    placeholder="عنوان قابلیت (مثلاً: سیستم نوتیفیکیشن)"
                    value={featureRequest.title}
                    onChange={(e) => setFeatureRequest({ ...featureRequest, title: e.target.value })}
                    className="w-full p-2 border rounded mb-2 dark:bg-gray-700 dark:border-gray-600 text-sm"
                  />

                  <textarea
                    placeholder="توضیحات کامل قابلیت..."
                    value={featureRequest.description}
                    onChange={(e) => setFeatureRequest({ ...featureRequest, description: e.target.value })}
                    className="w-full p-2 border rounded mb-2 dark:bg-gray-700 dark:border-gray-600 text-sm h-24 resize-none"
                  />

                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <div>
                      <label className="text-xs text-gray-500">اولویت:</label>
                      <select
                        value={featureRequest.priority}
                        onChange={(e) => setFeatureRequest({ ...featureRequest, priority: e.target.value })}
                        className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        <option value="critical">🔴 بحرانی</option>
                        <option value="high">🟠 بالا</option>
                        <option value="medium">🟡 متوسط</option>
                        <option value="low">🟢 پایین</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500">دسته‌بندی:</label>
                      <select
                        value={featureRequest.category}
                        onChange={(e) => setFeatureRequest({ ...featureRequest, category: e.target.value })}
                        className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        <option value="feature">✨ قابلیت جدید</option>
                        <option value="bugfix">🐛 رفع باگ</option>
                        <option value="improvement">⚡ بهبود</option>
                        <option value="refactor">🔧 بازنویسی</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3 mb-3 text-sm">
                    <label className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={featureRequest.ai_analyze}
                        onChange={(e) => setFeatureRequest({ ...featureRequest, ai_analyze: e.target.checked })}
                      />
                      🤖 تحلیل AI
                    </label>
                    <label className="flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={featureRequest.auto_add_roadmap}
                        onChange={(e) => setFeatureRequest({ ...featureRequest, auto_add_roadmap: e.target.checked })}
                      />
                      📋 اضافه به Roadmap
                    </label>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={submitFeatureRequest}
                      disabled={submittingFeatureRequest}
                      className="flex-1 px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {submittingFeatureRequest ? (
                        <><span className="animate-spin">⏳</span> در حال ثبت...</>
                      ) : (
                        <><span>✨</span> ثبت درخواست</>
                      )}
                    </button>
                    <button
                      onClick={() => setShowFeatureRequestForm(false)}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300"
                    >
                      انصراف
                    </button>
                  </div>

                  {featureRequestResult && (
                    <div className={`mt-3 p-2 rounded text-sm ${
                      featureRequestResult.success
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700'
                    }`}>
                      {featureRequestResult.message}
                      {featureRequestResult.duplicate_warning && (
                        <div className="mt-1 text-amber-600">
                          ⚠️ {featureRequestResult.duplicate_warning.message}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* 🆕 پنل تایید سریع */}
              {showQuickApprovalPanel && (
                <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium flex items-center gap-2">
                      <span>⚡</span> تایید سریع فیلدها
                      <button
                        onClick={autoConvertCriticalIssues}
                        disabled={autoConvertingIssues}
                        className="px-2 py-1 bg-orange-500 text-white rounded text-xs hover:bg-orange-600 disabled:opacity-50"
                        title="تبدیل خودکار ایرادات بحرانی به فیلد"
                      >
                        {autoConvertingIssues ? '⏳' : '🔄'} تبدیل ایرادات
                      </button>
                    </h3>
                    <button
                      onClick={() => setShowQuickApprovalPanel(false)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ✕
                    </button>
                  </div>

                  {loadingApprovals ? (
                    <div className="text-center py-4 text-gray-500">
                      <span className="animate-spin inline-block">⏳</span> در حال بارگذاری...
                    </div>
                  ) : (pendingApprovals?.total ?? 0) === 0 ? (
                    <div className="text-center py-4 text-gray-500">
                      ✅ هیچ فیلدی در انتظار تایید نیست
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {/* فیلدهای auto_pending - قابل تایید سریع */}
                      {(pendingApprovals?.auto_pending ?? []).map((field) => (
                        <div
                          key={field.id}
                          className="p-3 bg-white dark:bg-gray-700 rounded border border-amber-200 dark:border-amber-700"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-amber-500">⚡</span>
                                <span className="font-medium text-sm">{field.name}</span>
                                <span className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300 text-xs rounded">
                                  قابل تایید سریع
                                </span>
                              </div>
                              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{field.value}</p>
                            </div>
                            <div className="flex gap-1 mr-2">
                              <button
                                onClick={() => quickApproveField(field.id)}
                                disabled={approvingField === field.id}
                                className="px-2 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600 disabled:opacity-50"
                                title="تایید"
                              >
                                {approvingField === field.id ? '⏳' : '✅'}
                              </button>
                              <button
                                onClick={() => setRejectingField(field.id)}
                                className="px-2 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600"
                                title="رد"
                              >
                                ❌
                              </button>
                            </div>
                          </div>

                          {/* فرم رد */}
                          {rejectingField === field.id && (
                            <div className="mt-2 flex gap-2">
                              <input
                                type="text"
                                placeholder="دلیل رد..."
                                value={rejectionReason}
                                onChange={(e) => setRejectionReason(e.target.value)}
                                className="flex-1 p-1 border rounded text-xs dark:bg-gray-600 dark:border-gray-500"
                              />
                              <button
                                onClick={() => rejectField(field.id, rejectionReason)}
                                className="px-2 py-1 bg-red-500 text-white rounded text-xs"
                              >
                                تایید رد
                              </button>
                              <button
                                onClick={() => {
                                  setRejectingField(null);
                                  setRejectionReason('');
                                }}
                                className="px-2 py-1 bg-gray-300 rounded text-xs"
                              >
                                انصراف
                              </button>
                            </div>
                          )}
                        </div>
                      ))}

                      {/* فیلدهای pending - نیاز به Engineering Report */}
                      {(pendingApprovals?.pending ?? []).map((field) => (
                        <div
                          key={field.id}
                          className="p-3 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 opacity-75"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">⏳</span>
                            <span className="font-medium text-sm">{field.name}</span>
                            <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300 text-xs rounded">
                              نیاز به گزارش مهندسی
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{field.value}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* فرم افزودن فیلد جدید */}
              {showNewFieldForm && (
                <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <h3 className="font-medium mb-3">فیلد جدید</h3>
                  <input
                    type="text"
                    placeholder="نام فیلد (مثلاً: اولویت فعلی)"
                    value={newFieldName}
                    onChange={(e) => setNewFieldName(e.target.value)}
                    className="w-full p-2 border rounded mb-2 dark:bg-gray-700 dark:border-gray-600 text-sm"
                  />
                  <textarea
                    placeholder="مقدار فیلد (مثلاً: تمرکز روی عملکرد و سرعت)"
                    value={newFieldValue}
                    onChange={(e) => setNewFieldValue(e.target.value)}
                    className="w-full p-2 border rounded mb-2 dark:bg-gray-700 dark:border-gray-600 text-sm h-20 resize-none"
                  />
                  <div className="mb-3">
                    <label className="text-xs text-gray-500">مدل‌های هدف:</label>
                    <ModelSelector
                      selectedModels={newFieldModels}
                      onChange={setNewFieldModels}
                    />
                  </div>

                  {/* نوع فیلد و اولویت */}
                  <div className="mb-3 grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-gray-500 block mb-1">نوع فیلد:</label>
                      <select
                        value={newFieldType}
                        onChange={(e) => setNewFieldType(e.target.value)}
                        className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        <option value="temporary">⏱️ موقت/یکبار مصرف</option>
                        <option value="permanent">🔄 دائمی/تکرارشونده</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 block mb-1">اولویت:</label>
                      <select
                        value={newFieldPriority}
                        onChange={(e) => setNewFieldPriority(parseInt(e.target.value))}
                        className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        <option value={1}>🔴 1 - بحرانی</option>
                        <option value={2}>🔴 2 - خیلی بالا</option>
                        <option value={3}>🟠 3 - بالا</option>
                        <option value={4}>🟠 4 - نسبتاً بالا</option>
                        <option value={5}>🟢 5 - عادی</option>
                        <option value={6}>🟢 6 - نسبتاً پایین</option>
                        <option value={7}>🔵 7 - پایین</option>
                        <option value={8}>🔵 8 - کم اهمیت</option>
                        <option value={9}>⚪ 9 - خیلی پایین</option>
                        <option value={10}>⚪ 10 - کمترین</option>
                      </select>
                    </div>
                  </div>

                  {/* نوع اکشن */}
                  <div className="mb-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
                    <label className="text-xs text-gray-500 block mb-2">نوع اکشن:</label>
                    <select
                      value={newFieldActionType}
                      onChange={(e) => setNewFieldActionType(e.target.value)}
                      className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value="display">👁️ فقط نمایش - نتیجه در ژورنال نمایش داده می‌شود</option>
                      <option value="github_commit">📤 Commit به GitHub - یک فایل در ریپو ایجاد/بروزرسانی می‌شود</option>
                      <option value="github_multi_commit">📦 Multi Commit - چند فایل از پاسخ استخراج و commit می‌شوند</option>
                    </select>

                    {newFieldActionType === 'github_commit' && (
                      <div className="mt-2">
                        <label className="text-xs text-gray-500 block mb-1">مسیر فایل در ریپو:</label>
                        <input
                          type="text"
                          placeholder="مثال: backend/models/customer.py"
                          value={newFieldTargetPath}
                          onChange={(e) => setNewFieldTargetPath(e.target.value)}
                          className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                          dir="ltr"
                        />
                      </div>
                    )}

                    {newFieldActionType !== 'display' && (
                      <>
                        <label className="flex items-center gap-2 text-sm text-orange-600 dark:text-orange-400 mt-2">
                          <input
                            type="checkbox"
                            checked={newFieldArchiveAfterRun}
                            onChange={(e) => setNewFieldArchiveAfterRun(e.target.checked)}
                            className="rounded"
                          />
                          📦 بایگانی خودکار بعد از اجرای موفق
                        </label>
                        <label className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 mt-2">
                          <input
                            type="checkbox"
                            checked={newFieldDeployAfterCommit}
                            onChange={(e) => setNewFieldDeployAfterCommit(e.target.checked)}
                            className="rounded"
                          />
                          🚀 Deploy در Render بعد از Commit
                        </label>
                      </>
                    )}
                  </div>

                  {/* تنظیمات تریگر */}
                  <div className="mb-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <input
                        type="checkbox"
                        checked={newFieldTriggerEnabled}
                        onChange={(e) => setNewFieldTriggerEnabled(e.target.checked)}
                        className="rounded"
                      />
                      ⏰ فعال‌سازی تریگر (اجرای خودکار)
                    </label>
                    {newFieldTriggerEnabled && (
                      <div className="mr-6">
                        <label className="text-xs text-gray-500 block mb-1">بازه زمانی:</label>
                        <select
                          value={`${newFieldTriggerInterval}-${newFieldTriggerType}`}
                          onChange={(e) => {
                            const [val, type] = e.target.value.split('-');
                            setNewFieldTriggerInterval(parseInt(val));
                            setNewFieldTriggerType(type);
                          }}
                          className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                        >
                          {triggerIntervals.map((interval, idx) => (
                            <option key={idx} value={`${interval.value}-${interval.type}`}>
                              {interval.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={addDynamicField}
                      className="flex-1 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
                    >
                      افزودن
                    </button>
                    <button
                      onClick={() => {
                        setShowNewFieldForm(false);
                        setNewFieldName('');
                        setNewFieldValue('');
                        setNewFieldTriggerEnabled(false);
                      }}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg text-sm"
                    >
                      انصراف
                    </button>
                  </div>
                </div>
              )}

              {/* کنترل‌های اجرای گروهی */}
              {dynamicFields.filter((f: any) => !f.archived).length > 0 && (
                <div className="mb-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedFields.length === dynamicFields.filter((f: any) => !f.archived).length && selectedFields.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded"
                        />
                        انتخاب همه ({dynamicFields.filter((f: any) => !f.archived).length})
                      </label>
                      {selectedFields.length > 0 && (
                        <span className="text-xs text-gray-500">
                          {selectedFields.length} فیلد انتخاب شده
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {selectedFields.length > 0 && (
                        <>
                          <button
                            onClick={() => setSelectedFields([])}
                            className="px-2 py-1 text-xs text-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                          >
                            لغو انتخاب
                          </button>
                          {/* 🔴 دکمه حذف گروهی */}
                          <button
                            onClick={deleteBatchFields}
                            className="px-3 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600 flex items-center gap-1"
                            title="حذف گروهی فیلدهای انتخاب شده"
                          >
                            🗑️ حذف ({selectedFields.length})
                          </button>
                          <button
                            onClick={executeBatchFields}
                            disabled={executingBatch || batchStatus.status === 'running'}
                            className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 disabled:opacity-50 flex items-center gap-2"
                          >
                            {executingBatch || batchStatus.status === 'running' ? (
                              <>
                                <span className="animate-spin">⏳</span>
                                در حال اجرا...
                              </>
                            ) : (
                              <>
                                ▶️ اجرای گروهی ({selectedFields.length})
                              </>
                            )}
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* 🔴 نوار پیشرفت و کنترل‌ها */}
                  {(executingBatch || batchStatus.status === 'running' || batchStatus.status === 'paused') && (
                    <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-700">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                            {batchStatus.status === 'paused' ? '⏸️ متوقف موقت' : '🔄 در حال اجرا'}
                            {' - '}{batchStatus.current}/{batchStatus.total} فیلد ({batchStatus.progress.toFixed(1)}%)
                          </span>
                          {batchStatus.currentFieldName && (
                            <p className="text-xs text-blue-500 dark:text-blue-400 mt-1">
                              📝 {batchStatus.currentFieldName}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {batchStatus.status === 'running' && (
                            <button
                              onClick={() => controlBatchExecution('pause')}
                              className="px-3 py-1 bg-yellow-500 text-white rounded text-xs hover:bg-yellow-600"
                            >
                              ⏸️ توقف موقت
                            </button>
                          )}
                          {batchStatus.status === 'paused' && (
                            <button
                              onClick={() => controlBatchExecution('resume')}
                              className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
                            >
                              ▶️ ادامه
                            </button>
                          )}
                          <button
                            onClick={() => controlBatchExecution('stop')}
                            className="px-3 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600"
                          >
                            ⏹️ توقف کامل
                          </button>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-green-500 h-2.5 rounded-full transition-all duration-300"
                          style={{ width: `${batchStatus.progress}%` }}
                        />
                      </div>
                      {/* آمار اجرا */}
                      <div className="flex items-center justify-between mt-2 text-xs">
                        <div className="flex items-center gap-3">
                          {batchStatus.completedCount !== undefined && (
                            <span className="text-green-600 dark:text-green-400">
                              ✓ {batchStatus.completedCount} موفق
                            </span>
                          )}
                          {batchStatus.archivedCount !== undefined && batchStatus.archivedCount > 0 && (
                            <span className="text-purple-600 dark:text-purple-400">
                              📦 {batchStatus.archivedCount} بایگانی شده
                            </span>
                          )}
                          {batchStatus.failedCount !== undefined && batchStatus.failedCount > 0 && (
                            <span className="text-red-600 dark:text-red-400">
                              ✗ {batchStatus.failedCount} ناموفق
                            </span>
                          )}
                        </div>
                        <span className="text-blue-600 dark:text-blue-400">
                          💡 می‌توانید صفحه را ترک کنید
                        </span>
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-gray-500 mt-2">
                    💡 فیلدها بر اساس اولویت مرتب و اجرا می‌شوند (اولویت ۱ = بالاترین)
                  </p>
                </div>
              )}

              {/* 🆕 دکمه‌های دانلود و فیلتر */}
              <div className="mb-3 flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  {dynamicFields.some((f: any) => f.archived) && (
                    <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <input
                        type="checkbox"
                        checked={showArchivedFields}
                        onChange={(e) => setShowArchivedFields(e.target.checked)}
                        className="rounded"
                      />
                      📦 نمایش بایگانی ({dynamicFields.filter((f: any) => f.archived).length})
                    </label>
                  )}
                </div>

                {/* دکمه‌های دانلود مارک‌داون */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => window.open(`${API_BASE}/api/projects/${projectId}/export/fields/markdown?field_ids=active`, '_blank')}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800 flex items-center gap-1"
                    title="دانلود فیلدهای فعال به مارک‌داون"
                  >
                    📥 فعال
                  </button>
                  <button
                    onClick={() => window.open(`${API_BASE}/api/projects/${projectId}/export/fields/markdown?field_ids=all`, '_blank')}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1"
                    title="دانلود همه فیلدها به مارک‌داون"
                  >
                    📥 همه
                  </button>
                  {selectedFields.length > 0 && (
                    <button
                      onClick={() => window.open(`${API_BASE}/api/projects/${projectId}/export/fields/markdown?field_ids=${selectedFields.join(',')}`, '_blank')}
                      className="px-2 py-1 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-800 flex items-center gap-1"
                      title="دانلود فیلدهای انتخاب شده"
                    >
                      📥 انتخابی ({selectedFields.length})
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-3 max-h-[50vh] overflow-auto">
                {dynamicFields.filter((f: any) => !f.archived || showArchivedFields).length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <div className="text-4xl mb-2">📭</div>
                    <p>فیلدی تعریف نشده</p>
                  </div>
                ) : (
                  dynamicFields
                    .filter((f: any) => !f.archived || showArchivedFields)
                    .sort((a: any, b: any) => (a.priority || 5) - (b.priority || 5))
                    .map((field: any) => (
                    <div
                      key={field.id}
                      className={`p-4 rounded-lg ${field.archived
                        ? 'bg-gray-200 dark:bg-gray-800 opacity-60'
                        : 'bg-gray-50 dark:bg-gray-700'
                      }`}
                    >
                      {editingField === field.id ? (
                        // حالت ویرایش
                        <div>
                          <input
                            type="text"
                            value={field.name}
                            onChange={(e) => {
                              const updated = dynamicFields.map(f =>
                                f.id === field.id ? { ...f, name: e.target.value } : f
                              );
                              setDynamicFields(updated);
                            }}
                            className="w-full p-2 border rounded mb-2 dark:bg-gray-600 dark:border-gray-500 text-sm"
                          />
                          <textarea
                            value={field.value}
                            onChange={(e) => {
                              const updated = dynamicFields.map(f =>
                                f.id === field.id ? { ...f, value: e.target.value } : f
                              );
                              setDynamicFields(updated);
                            }}
                            className="w-full p-2 border rounded mb-2 dark:bg-gray-600 dark:border-gray-500 text-sm h-20 resize-none"
                          />
                          <div className="mb-2">
                            <ModelSelector
                              selectedModels={field.target_models}
                              onChange={(models) => {
                                const updated = dynamicFields.map(f =>
                                  f.id === field.id ? { ...f, target_models: models } : f
                                );
                                setDynamicFields(updated);
                              }}
                            />
                          </div>

                          {/* نوع فیلد و اولویت در حالت ویرایش */}
                          <div className="mb-3 grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs text-gray-500 block mb-1">نوع فیلد:</label>
                              <select
                                value={field.field_type || 'temporary'}
                                onChange={(e) => {
                                  const updated = dynamicFields.map(f =>
                                    f.id === field.id ? { ...f, field_type: e.target.value } : f
                                  );
                                  setDynamicFields(updated);
                                }}
                                className="w-full p-2 border rounded text-sm dark:bg-gray-600 dark:border-gray-500"
                              >
                                <option value="temporary">⏱️ موقت/یکبار مصرف</option>
                                <option value="permanent">🔄 دائمی/تکرارشونده</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-xs text-gray-500 block mb-1">اولویت:</label>
                              <select
                                value={field.priority || 5}
                                onChange={(e) => {
                                  const updated = dynamicFields.map(f =>
                                    f.id === field.id ? { ...f, priority: parseInt(e.target.value) } : f
                                  );
                                  setDynamicFields(updated);
                                }}
                                className="w-full p-2 border rounded text-sm dark:bg-gray-600 dark:border-gray-500"
                              >
                                <option value={1}>🔴 1 - بحرانی</option>
                                <option value={2}>🔴 2 - خیلی بالا</option>
                                <option value={3}>🟠 3 - بالا</option>
                                <option value={4}>🟠 4 - نسبتاً بالا</option>
                                <option value={5}>🟢 5 - عادی</option>
                                <option value={6}>🟢 6 - نسبتاً پایین</option>
                                <option value={7}>🔵 7 - پایین</option>
                                <option value={8}>🔵 8 - کم اهمیت</option>
                                <option value={9}>⚪ 9 - خیلی پایین</option>
                                <option value={10}>⚪ 10 - کمترین</option>
                              </select>
                            </div>
                          </div>

                          {/* تنظیمات تریگر در حالت ویرایش */}
                          <div className="mb-3 p-3 bg-white dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
                            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                              <input
                                type="checkbox"
                                checked={field.trigger?.enabled || false}
                                onChange={(e) => {
                                  const updated = dynamicFields.map(f =>
                                    f.id === field.id
                                      ? {
                                          ...f,
                                          trigger: {
                                            ...f.trigger,
                                            enabled: e.target.checked,
                                            interval_minutes: f.trigger?.interval_minutes || 60,
                                            interval_type: f.trigger?.interval_type || 'minutes',
                                          }
                                        }
                                      : f
                                  );
                                  setDynamicFields(updated);
                                }}
                                className="rounded"
                              />
                              ⏰ فعال‌سازی تریگر (اجرای خودکار)
                            </label>
                            {field.trigger?.enabled && (
                              <div className="mr-6">
                                <label className="text-xs text-gray-500 block mb-1">بازه زمانی:</label>
                                <select
                                  value={`${field.trigger?.interval_minutes || 60}-${field.trigger?.interval_type || 'minutes'}`}
                                  onChange={(e) => {
                                    const [val, type] = e.target.value.split('-');
                                    const updated = dynamicFields.map(f =>
                                      f.id === field.id
                                        ? {
                                            ...f,
                                            trigger: {
                                              ...f.trigger,
                                              enabled: true,
                                              interval_minutes: parseInt(val),
                                              interval_type: type,
                                            }
                                          }
                                        : f
                                    );
                                    setDynamicFields(updated);
                                  }}
                                  className="w-full p-2 border rounded text-sm dark:bg-gray-600 dark:border-gray-500"
                                >
                                  {triggerIntervals.map((interval, idx) => (
                                    <option key={idx} value={`${interval.value}-${interval.type}`}>
                                      {interval.label}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            )}
                          </div>

                          <div className="flex gap-2">
                            <button
                              onClick={() => updateDynamicField(field)}
                              className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                            >
                              ذخیره
                            </button>
                            <button
                              onClick={() => { setEditingField(null); loadMemory(); }}
                              className="px-3 py-1 bg-gray-300 dark:bg-gray-600 rounded text-sm"
                            >
                              انصراف
                            </button>
                          </div>
                        </div>
                      ) : (
                        // حالت نمایش
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {/* چک‌باکس انتخاب برای اجرای گروهی */}
                              {!field.archived && (
                                <input
                                  type="checkbox"
                                  checked={selectedFields.includes(field.id)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedFields([...selectedFields, field.id]);
                                    } else {
                                      setSelectedFields(selectedFields.filter(id => id !== field.id));
                                    }
                                  }}
                                  className="rounded"
                                  title="انتخاب برای اجرای گروهی"
                                />
                              )}
                              {/* آیکون نوع فیلد */}
                              <span className="text-sm" title={field.field_type === 'permanent' ? 'دائمی/تکرارشونده' : 'موقت/یکبار مصرف'}>
                                {field.field_type === 'permanent' ? '🔄' : '⏱️'}
                              </span>
                              {/* آیکون اولویت */}
                              <span className="text-sm" title={`اولویت: ${field.priority || 5} - ${getPriorityName(field.priority || 5)}`}>
                                {getPriorityIcon(field.priority || 5)}
                              </span>
                              <span className="font-medium">{field.name}</span>
                              {/* نشانگر نوع اکشن */}
                              {field.action_type === 'github_commit' && (
                                <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs rounded">
                                  📤 GitHub
                                </span>
                              )}
                              {field.action_type === 'github_multi_commit' && (
                                <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 text-xs rounded">
                                  📦 Multi
                                </span>
                              )}
                              {field.archived && (
                                <span className="px-2 py-0.5 bg-gray-300 dark:bg-gray-600 text-gray-600 dark:text-gray-300 text-xs rounded">
                                  📦 بایگانی
                                </span>
                              )}
                              {/* نشانگر تاییدیه - با پشتیبانی از Quick Approval */}
                              {field.validation_marker === 'engineering_approved' || field.engineering_approval?.approved ? (
                                <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 text-xs rounded" title={`تایید شده توسط ${field.engineering_approval?.approved_by || 'AI'} در ${field.engineering_approval?.approved_at || ''}`}>
                                  ✅ تایید مهندسی
                                </span>
                              ) : field.validation_marker === 'quick_approved' ? (
                                <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs rounded" title={`تایید سریع در ${field.quick_approved_at || ''}`}>
                                  ⚡ تایید سریع
                                </span>
                              ) : field.validation_marker === 'auto_pending' ? (
                                <span
                                  className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 text-xs rounded cursor-pointer hover:bg-amber-200"
                                  title="قابل تایید سریع - کلیک کنید"
                                  onClick={() => {
                                    loadPendingApprovals();
                                    setShowQuickApprovalPanel(true);
                                  }}
                                >
                                  🔄 در انتظار تایید
                                </span>
                              ) : field.needs_approval || (field.action_type && field.action_type !== 'display' && !field.archived) ? (
                                <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 text-xs rounded" title="برای اجرا نیاز به تایید گزارش مهندسی دارد">
                                  ⚠️ نیاز به تایید
                                </span>
                              ) : null}
                            </div>
                            <div className="flex gap-1">
                              {field.archived ? (
                                <button
                                  onClick={async () => {
                                    try {
                                      await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${field.id}/unarchive`, { method: 'POST' });
                                      loadMemory();
                                      showSuccess('از بایگانی خارج شد');
                                    } catch { showError('خطا'); }
                                  }}
                                  className="p-1 text-green-500 hover:bg-green-100 rounded"
                                  title="خروج از بایگانی"
                                >
                                  📤
                                </button>
                              ) : (
                                <>
                                  <button
                                    onClick={() => setEditingField(field.id)}
                                    className="p-1 text-blue-500 hover:bg-blue-100 rounded"
                                    title="ویرایش"
                                  >
                                    ✏️
                                  </button>
                                  <button
                                    onClick={async () => {
                                      try {
                                        await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${field.id}/archive`, { method: 'POST' });
                                        loadMemory();
                                        showSuccess('بایگانی شد');
                                      } catch { showError('خطا'); }
                                    }}
                                    className="p-1 text-orange-500 hover:bg-orange-100 rounded"
                                    title="بایگانی"
                                  >
                                    📦
                                  </button>
                                </>
                              )}
                              <button
                                onClick={() => deleteDynamicField(field.id)}
                                className="p-1 text-red-500 hover:bg-red-100 rounded"
                                title="حذف"
                              >
                                🗑️
                              </button>
                            </div>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                            {field.value}
                          </p>

                          {/* نمایش مسیر هدف برای GitHub */}
                          {field.target_path && (
                            <div className="mt-2 px-2 py-1 bg-gray-100 dark:bg-gray-600 rounded text-xs font-mono" dir="ltr">
                              📁 {field.target_path}
                            </div>
                          )}

                          <div className="mt-2 flex flex-wrap gap-1">
                            {field.target_models.map((m: string) => {
                              const model = availableModels.find(am => am.id === m);
                              return (
                                <span
                                  key={m}
                                  className="px-2 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-xs"
                                >
                                  {model?.icon} {model?.name || m}
                                </span>
                              );
                            })}
                          </div>

                          {/* تریگر کنترل‌ها - فقط برای فیلدهای غیر بایگانی */}
                          {!field.archived && (
                          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <div className="relative">
                                    <input
                                      type="checkbox"
                                      checked={field.trigger?.enabled || false}
                                      onChange={(e) => toggleFieldTrigger(field.id, e.target.checked)}
                                      className="sr-only"
                                    />
                                    <div className={`w-10 h-5 rounded-full transition ${
                                      field.trigger?.enabled
                                        ? 'bg-green-500'
                                        : 'bg-gray-300 dark:bg-gray-600'
                                    }`}>
                                      <div className={`w-4 h-4 bg-white rounded-full shadow transform transition ${
                                        field.trigger?.enabled
                                          ? 'translate-x-5'
                                          : 'translate-x-0.5'
                                      } mt-0.5`}></div>
                                    </div>
                                  </div>
                                  <span className="text-xs text-gray-600 dark:text-gray-400">
                                    ⏰ تریگر خودکار
                                  </span>
                                </label>
                                {field.trigger?.enabled && (
                                  <span className="text-xs text-green-600 dark:text-green-400">
                                    ({triggerIntervals.find(
                                      (i: any) => i.value === field.trigger?.interval_minutes && i.type === field.trigger?.interval_type
                                    )?.label || `هر ${field.trigger?.interval_minutes} دقیقه`})
                                  </span>
                                )}
                              </div>

                              <button
                                onClick={() => executeFieldTrigger(field.id)}
                                disabled={executingTrigger === field.id}
                                className="px-3 py-1 bg-orange-500 text-white rounded text-xs hover:bg-orange-600 disabled:opacity-50 flex items-center gap-1"
                                title={field.action_type === 'github_commit' ? 'اجرا و Commit به GitHub' : 'اجرای دستی تریگر'}
                              >
                                {executingTrigger === field.id ? (
                                  <>
                                    <span className="animate-spin">⏳</span>
                                    در حال اجرا...
                                  </>
                                ) : (
                                  <>
                                    ▶️ اجرا الان
                                  </>
                                )}
                              </button>
                            </div>

                            {/* نمایش آخرین و بعدی اجرا */}
                            {field.trigger?.enabled && (field.trigger?.last_run || field.trigger?.next_run) && (
                              <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                                {field.trigger?.last_run && (
                                  <span>
                                    آخرین اجرا: {new Date(field.trigger.last_run).toLocaleString('fa-IR')}
                                  </span>
                                )}
                                {field.trigger?.next_run && (
                                  <span>
                                    اجرای بعدی: {new Date(field.trigger.next_run).toLocaleString('fa-IR')}
                                  </span>
                                )}
                              </div>
                            )}

                            {/* بخش پیوست‌ها */}
                            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-gray-500 flex items-center gap-1">
                                  📎 پیوست‌ها ({field.attachments?.length || 0})
                                </span>
                                <label className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs rounded cursor-pointer hover:bg-blue-200 dark:hover:bg-blue-800">
                                  {uploadingAttachment === field.id ? (
                                    <span className="animate-pulse">در حال آپلود...</span>
                                  ) : (
                                    <>
                                      + افزودن فایل
                                      <input
                                        type="file"
                                        className="hidden"
                                        accept="image/*,.pdf,.txt,.json,.md,.csv"
                                        onChange={(e) => {
                                          const file = e.target.files?.[0];
                                          if (file) {
                                            uploadAttachment(field.id, file);
                                          }
                                          e.target.value = '';
                                        }}
                                      />
                                    </>
                                  )}
                                </label>
                              </div>
                              {field.attachments && field.attachments.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                  {field.attachments.map((att: any, idx: number) => {
                                    // پشتیبانی از string یا object
                                    const attId = typeof att === 'string' ? att : (att?.id || att?.path || String(idx));
                                    const attName = typeof att === 'string' ? att : (att?.name || att?.file_name || att?.path || 'فایل');
                                    const fileName = attName.includes('/') ? attName.split('/').pop() : attName;
                                    const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(fileName || '');
                                    return (
                                      <div
                                        key={idx}
                                        className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-600 rounded text-xs group"
                                      >
                                        <span>{isImage ? '🖼️' : '📄'}</span>
                                        <span className="max-w-[100px] truncate" title={fileName}>{fileName}</span>
                                        <button
                                          onClick={() => deleteAttachment(field.id, attId)}
                                          className="text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                          title="حذف پیوست"
                                        >
                                          ×
                                        </button>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
            </div>
          </div>
        )}

        {/* محتوای تب ساختار پروژه */}
        {activeTab === 'structure' && (
          <div className="space-y-6">
            {/* تنظیمات تحلیل */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">⚙️</span>
                  <h2 className="font-bold text-lg">تنظیمات تحلیل ساختار</h2>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={analyzeStructure}
                    disabled={analyzingStructure}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 flex items-center gap-2"
                  >
                    {analyzingStructure ? (
                      <>
                        <span className="animate-spin">⏳</span>
                        در حال تحلیل...
                      </>
                    ) : (
                      <>
                        🔄 تحلیل مجدد
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                {/* دستور تحلیل */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    دستور تحلیل (برای مدل‌های AI):
                  </label>
                  <textarea
                    value={structureSettings.instruction}
                    onChange={(e) => setStructureSettings({ ...structureSettings, instruction: e.target.value })}
                    className="w-full p-3 border rounded-lg resize-none h-24 dark:bg-gray-700 dark:border-gray-600 text-sm"
                    placeholder="دستور برای تحلیل ساختار پروژه..."
                  />
                </div>

                {/* تنظیمات تریگر */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={structureSettings.trigger_enabled}
                        onChange={(e) => setStructureSettings({ ...structureSettings, trigger_enabled: e.target.checked })}
                        className="rounded"
                      />
                      <span className="text-sm font-medium">⏰ تریگر خودکار (بروزرسانی زمان‌بندی شده)</span>
                    </label>
                  </div>

                  {structureSettings.trigger_enabled && (
                    <div className="mr-6">
                      <label className="text-xs text-gray-500 block mb-1">بازه زمانی:</label>
                      <select
                        value={`${structureSettings.trigger_interval_minutes}-${structureSettings.trigger_interval_type}`}
                        onChange={(e) => {
                          const [val, type] = e.target.value.split('-');
                          setStructureSettings({
                            ...structureSettings,
                            trigger_interval_minutes: parseInt(val),
                            trigger_interval_type: type,
                          });
                        }}
                        className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        {triggerIntervals.map((interval, idx) => (
                          <option key={idx} value={`${interval.value}-${interval.type}`}>
                            {interval.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* مدل‌های هدف */}
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">مدل‌های AI:</label>
                    <ModelSelector
                      selectedModels={structureSettings.target_models}
                      onChange={(models) => setStructureSettings({ ...structureSettings, target_models: models })}
                    />
                  </div>

                  {/* آخرین و بعدی تحلیل */}
                  {(structureSettings.last_analysis || structureSettings.next_analysis) && (
                    <div className="flex flex-wrap gap-3 text-xs text-gray-500 pt-2">
                      {structureSettings.last_analysis && (
                        <span>
                          آخرین تحلیل: {new Date(structureSettings.last_analysis).toLocaleString('fa-IR')}
                        </span>
                      )}
                      {structureSettings.next_analysis && (
                        <span>
                          تحلیل بعدی: {new Date(structureSettings.next_analysis).toLocaleString('fa-IR')}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={saveStructureSettings}
                disabled={savingStructureSettings}
                className="mt-4 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
              >
                {savingStructureSettings ? '⏳ در حال ذخیره...' : '💾 ذخیره تنظیمات'}
              </button>
            </div>

            {/* دیاگرام ساختار */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🔀</span>
                  <h2 className="font-bold text-lg">دیاگرام ساختار پروژه</h2>
                </div>
                {structureData?.metadata && (
                  <div className="flex gap-4 text-sm text-gray-500">
                    <span>📁 {structureData.metadata.total_folders} پوشه</span>
                    <span>📄 {structureData.metadata.total_files} فایل</span>
                  </div>
                )}
              </div>

              {structureLoading ? (
                <div className="h-[600px] flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin text-4xl mb-4">⏳</div>
                    <p>در حال بارگذاری ساختار...</p>
                  </div>
                </div>
              ) : nodes.length === 0 ? (
                <div className="h-[600px] flex items-center justify-center">
                  <div className="text-center text-gray-400">
                    <div className="text-6xl mb-4">📊</div>
                    <p className="mb-4">ساختار پروژه هنوز تحلیل نشده</p>
                    <button
                      onClick={analyzeStructure}
                      disabled={analyzingStructure}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                    >
                      {analyzingStructure ? '⏳ در حال تحلیل...' : '🔄 تحلیل ساختار'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="h-[600px]">
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    fitView
                    attributionPosition="bottom-left"
                    className="bg-gray-50 dark:bg-gray-900"
                  >
                    <Controls className="bg-white dark:bg-gray-800 rounded shadow" />
                    <MiniMap
                      className="bg-white dark:bg-gray-800 rounded shadow"
                      nodeColor={(node) => node.style?.background as string || '#6366f1'}
                      maskColor="rgba(0, 0, 0, 0.2)"
                    />
                    <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#9ca3af" />
                  </ReactFlow>
                </div>
              )}
            </div>

            {/* راهنما */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-800 rounded-xl p-4 border border-blue-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">💡</span>
                <h3 className="font-bold">راهنما</h3>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium text-sm mb-2">🎨 رنگ‌بندی سلامت:</h4>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside mr-4">
                    <li><span className="inline-block w-3 h-3 rounded-full bg-green-500 ml-1"></span> سبز: سالم (90%+)</li>
                    <li><span className="inline-block w-3 h-3 rounded-full bg-lime-500 ml-1"></span> سبز روشن: خوب (75-90%)</li>
                    <li><span className="inline-block w-3 h-3 rounded-full bg-yellow-500 ml-1"></span> زرد: متوسط (60-75%)</li>
                    <li><span className="inline-block w-3 h-3 rounded-full bg-orange-500 ml-1"></span> نارنجی: ضعیف (40-60%)</li>
                    <li><span className="inline-block w-3 h-3 rounded-full bg-red-500 ml-1"></span> قرمز: بد (20-40%)</li>
                    <li><span className="inline-block w-3 h-3 rounded-full bg-red-800 ml-1"></span> قرمز تیره: بحرانی (0-20%)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-sm mb-2">📊 اطلاعات نود:</h4>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside mr-4">
                    <li>عدد روی نود = نمره سلامت</li>
                    <li>با هاور روی نود جزئیات را ببینید</li>
                    <li>مدل‌های بررسی‌کننده و تاریخ</li>
                    <li>نمره هر مدل به تفکیک</li>
                    <li>تعداد ایرادات شناسایی شده</li>
                    <li>برای تحلیل از تب "تحلیل سلامت" استفاده کنید</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* محتوای تب ژورنال و گزارشات */}
        {activeTab === 'journal' && (
          <div className="space-y-6">
            {/* سابتب‌ها */}
            <div className="flex gap-2 bg-white dark:bg-gray-800 rounded-xl p-2 flex-wrap">
              <button
                onClick={() => setJournalSubTab('logs')}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition ${
                  journalSubTab === 'logs'
                    ? 'bg-orange-500 text-white'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                📋 ژورنال فعالیت‌ها
              </button>
              <button
                onClick={() => setJournalSubTab('reports')}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition ${
                  journalSubTab === 'reports'
                    ? 'bg-orange-500 text-white'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                📊 گزارشات
              </button>
              <button
                onClick={() => setJournalSubTab('validation')}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition ${
                  journalSubTab === 'validation'
                    ? 'bg-purple-500 text-white'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                ✅ اعتبارسنجی
              </button>
              <button
                onClick={() => setJournalSubTab('profiles')}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition ${
                  journalSubTab === 'profiles'
                    ? 'bg-blue-500 text-white'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                🤖 پروفایل مدل‌ها
              </button>
              <button
                onClick={() => setJournalSubTab('roadmap')}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition ${
                  journalSubTab === 'roadmap'
                    ? 'bg-green-500 text-white'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                🗺️ نقشه راه
              </button>
            </div>

            {/* آمار کلی */}
            {journalStats && (
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-blue-500">{journalStats.total_activities ?? 0}</div>
                  <div className="text-sm text-gray-500">فعالیت (۳۰ روز)</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-green-500">{(journalStats.total_tokens ?? 0).toLocaleString()}</div>
                  <div className="text-sm text-gray-500">توکن مصرفی</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-purple-500">{journalStats.avg_latency_ms ?? 0}ms</div>
                  <div className="text-sm text-gray-500">میانگین تأخیر</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-emerald-500">{journalStats.success_rate ?? 0}%</div>
                  <div className="text-sm text-gray-500">نرخ موفقیت</div>
                </div>
              </div>
            )}

            {/* ژورنال فعالیت‌ها */}
            {journalSubTab === 'logs' && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
                <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
                  <h2 className="font-bold text-lg flex items-center gap-2">
                    <span className="text-xl">📋</span>
                    ژورنال فعالیت‌های AI
                  </h2>
                  <div className="flex gap-2">
                    <select
                      value={journalFilter.type || ''}
                      onChange={(e) => {
                        setJournalFilter({...journalFilter, type: e.target.value || undefined});
                        setJournalPage(1);
                      }}
                      className="px-3 py-1 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value="">همه انواع</option>
                      <option value="chat">چت</option>
                      <option value="trigger">تریگر</option>
                      <option value="analysis">تحلیل</option>
                      <option value="generation">تولید</option>
                    </select>
                    <button
                      onClick={() => loadJournal()}
                      className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                    >
                      🔄 بروزرسانی
                    </button>
                  </div>
                </div>

                {journalLoading ? (
                  <div className="p-8 text-center text-gray-400">
                    <div className="animate-spin text-3xl mb-2">⏳</div>
                    در حال بارگذاری...
                  </div>
                ) : journalLogs.length === 0 ? (
                  <div className="p-8 text-center text-gray-400">
                    <div className="text-4xl mb-2">📭</div>
                    <p>فعالیتی ثبت نشده</p>
                  </div>
                ) : (
                  <>
                    <div className="divide-y dark:divide-gray-700">
                      {journalLogs.map((log) => (
                        <div
                          key={log.id}
                          onClick={() => loadActivityDetail(log.id)}
                          className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 rounded text-xs ${
                                log.activity_type === 'chat' ? 'bg-blue-100 text-blue-700' :
                                log.activity_type === 'trigger' ? 'bg-orange-100 text-orange-700' :
                                log.activity_type === 'analysis' ? 'bg-purple-100 text-purple-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {log.activity_type}
                              </span>
                              <span className="font-medium text-sm">{log.model_id}</span>
                              {log.field_name && (
                                <span className="text-xs text-gray-500">({log.field_name})</span>
                              )}
                            </div>
                            <div className="flex items-center gap-3 text-xs text-gray-500">
                              <span>{log.tokens_used} توکن</span>
                              <span>{log.latency_ms}ms</span>
                              <span className={log.success ? 'text-green-500' : 'text-red-500'}>
                                {log.success ? '✓' : '✗'}
                              </span>
                            </div>
                          </div>
                          {log.prompt && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                              {log.prompt}
                            </p>
                          )}
                          <div className="text-xs text-gray-400 mt-1">
                            {log.created_at ? new Date(log.created_at).toLocaleString('fa-IR') : ''}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* صفحه‌بندی */}
                    <div className="p-4 border-t dark:border-gray-700 flex items-center justify-between">
                      <span className="text-sm text-gray-500">
                        {journalTotal} فعالیت
                      </span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => { setJournalPage(p => Math.max(1, p-1)); loadJournal(); }}
                          disabled={journalPage <= 1}
                          className="px-3 py-1 border rounded text-sm disabled:opacity-50"
                        >
                          قبلی
                        </button>
                        <span className="px-3 py-1 text-sm">صفحه {journalPage}</span>
                        <button
                          onClick={() => { setJournalPage(p => p+1); loadJournal(); }}
                          disabled={journalLogs.length < 20}
                          className="px-3 py-1 border rounded text-sm disabled:opacity-50"
                        >
                          بعدی
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* گزارشات */}
            {journalSubTab === 'reports' && (
              <div className="space-y-6">
                {/* تنظیمات تریگر گزارش */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-bold text-lg flex items-center gap-2">
                      <span className="text-xl">⚙️</span>
                      تنظیمات گزارش‌گیری خودکار
                    </h2>
                    <div className="flex gap-2">
                      <button
                        onClick={() => generateReport(7)}
                        disabled={generatingReport}
                        className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                      >
                        {generatingReport ? '⏳ در حال تولید...' : '📝 گزارش ساده'}
                      </button>
                      <button
                        onClick={() => generateEngineeringReport(7)}
                        disabled={generatingReport}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                        title="گزارش مهندسی جامع با تحلیل کد، شناسایی باگ‌ها، پیشنهادات و تولید خودکار فیلدها"
                      >
                        {generatingReport ? '⏳ در حال تولید...' : '🔬 گزارش مهندسی'}
                      </button>
                    </div>
                  </div>

                  {/* 🔴 نوار پیشرفت گزارش مهندسی */}
                  {reportProgress && (
                    <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/30 rounded-lg border border-purple-200 dark:border-purple-700">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                          {reportProgress.message}
                        </span>
                        <span className="text-xs text-purple-600 dark:text-purple-400">
                          مرحله {reportProgress.step} از {reportProgress.total}
                        </span>
                      </div>
                      <div className="w-full bg-purple-200 dark:bg-purple-800 rounded-full h-3 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-300 ease-out"
                          style={{ width: `${reportProgress.progress}%` }}
                        />
                      </div>
                      <div className="text-center mt-1">
                        <span className="text-xs text-purple-600 dark:text-purple-400 font-mono">
                          {reportProgress.progress}%
                        </span>
                      </div>

                      {/* 🔴 نمایش پرامپت در حال اجرا */}
                      {activePromptExecutions.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-purple-200 dark:border-purple-700">
                          <div className="flex items-center gap-2 text-sm">
                            <span className="animate-pulse text-yellow-500">●</span>
                            <span className="text-purple-600 dark:text-purple-300">📝 پرامپت:</span>
                            <span className="text-purple-800 dark:text-purple-200 font-medium">
                              {activePromptExecutions[0].prompt_name}
                            </span>
                          </div>
                          {activePromptExecutions.length > 1 && (
                            <div className="mt-2 space-y-1">
                              {activePromptExecutions.slice(1).map((exec) => (
                                <div key={exec.id} className="flex items-center gap-2 text-xs text-purple-500">
                                  <span>⏳</span>
                                  <span>{exec.prompt_name}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 🆕 پنجره انتخاب مدل و عمق گزارش مهندسی */}
                  {showEngineeringModelSelector && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 max-w-lg w-full mx-4">
                        <h3 className="font-bold text-xl mb-4 flex items-center gap-2">
                          <span className="text-2xl">🔬</span>
                          تنظیمات گزارش مهندسی
                        </h3>

                        {/* انتخاب مدل‌ها */}
                        <div className="mb-4">
                          <label className="text-sm font-medium block mb-2">📊 انتخاب مدل(ها):</label>
                          <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-2 bg-gray-50 dark:bg-gray-900 rounded-lg">
                            {availableModels.filter(m => m.id !== 'all').map(model => (
                              <label key={model.id} className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={selectedEngineeringModels.includes(model.id)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedEngineeringModels([...selectedEngineeringModels, model.id]);
                                    } else {
                                      setSelectedEngineeringModels(selectedEngineeringModels.filter(id => id !== model.id));
                                    }
                                  }}
                                  className="rounded"
                                />
                                <span className="text-sm">{model.icon} {model.name}</span>
                              </label>
                            ))}
                          </div>
                          {selectedEngineeringModels.length === 0 && (
                            <p className="text-xs text-red-500 mt-1">حداقل یک مدل انتخاب کنید</p>
                          )}
                        </div>

                        {/* انتخاب عمق گزارش */}
                        <div className="mb-6">
                          <label className="text-sm font-medium block mb-2">⏱️ عمق و دقت گزارش:</label>
                          <div className="space-y-2">
                            <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${engineeringReportDepth === 'quick' ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500' : 'border-gray-200 dark:border-gray-600 hover:border-blue-300'}`}>
                              <input
                                type="radio"
                                name="depth"
                                checked={engineeringReportDepth === 'quick'}
                                onChange={() => setEngineeringReportDepth('quick')}
                                className="text-blue-500"
                              />
                              <div>
                                <div className="font-medium">⚡ سریع</div>
                                <div className="text-xs text-gray-500">۱-۲ دقیقه | بررسی سطحی</div>
                              </div>
                            </label>
                            <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${engineeringReportDepth === 'standard' ? 'bg-purple-50 dark:bg-purple-900/30 border-purple-500' : 'border-gray-200 dark:border-gray-600 hover:border-purple-300'}`}>
                              <input
                                type="radio"
                                name="depth"
                                checked={engineeringReportDepth === 'standard'}
                                onChange={() => setEngineeringReportDepth('standard')}
                                className="text-purple-500"
                              />
                              <div>
                                <div className="font-medium">📊 استاندارد</div>
                                <div className="text-xs text-gray-500">۳-۵ دقیقه | تحلیل متوسط</div>
                              </div>
                            </label>
                            <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${engineeringReportDepth === 'deep' ? 'bg-green-50 dark:bg-green-900/30 border-green-500' : 'border-gray-200 dark:border-gray-600 hover:border-green-300'}`}>
                              <input
                                type="radio"
                                name="depth"
                                checked={engineeringReportDepth === 'deep'}
                                onChange={() => setEngineeringReportDepth('deep')}
                                className="text-green-500"
                              />
                              <div>
                                <div className="font-medium">🔬 عمیق و جامع</div>
                                <div className="text-xs text-gray-500">۱۰-۲۰ دقیقه | بررسی فایل به فایل، اعتبارسنجی کامل</div>
                              </div>
                            </label>
                          </div>
                        </div>

                        {/* دکمه‌ها */}
                        <div className="flex gap-3 justify-between">
                          <button
                            onClick={() => {
                              setShowEngineeringModelSelector(false);
                              setShowEngineeringPrompts(true);
                            }}
                            className="px-4 py-2 text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg flex items-center gap-2"
                          >
                            <span>📝</span>
                            مدیریت پرامپت‌ها
                          </button>
                          <div className="flex gap-3">
                            <button
                              onClick={() => setShowEngineeringModelSelector(false)}
                              className="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400"
                            >
                              انصراف
                            </button>
                            <button
                              onClick={() => executeEngineeringReport(7)}
                              disabled={selectedEngineeringModels.length === 0}
                              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                              <span>🚀</span>
                              شروع گزارش‌گیری
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 🆕 مدال پرامپت‌های گزارش مهندسی */}
                  {showEngineeringPrompts && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="sticky top-0 bg-white dark:bg-gray-800 p-4 border-b flex items-center justify-between">
                          <h3 className="font-bold text-xl flex items-center gap-2">
                            <span className="text-2xl">📝</span>
                            پرامپت‌های گزارش مهندسی
                          </h3>
                          <button
                            onClick={() => setShowEngineeringPrompts(false)}
                            className="text-gray-500 hover:text-gray-700 text-2xl"
                          >
                            ×
                          </button>
                        </div>
                        <div className="p-4">
                          <PromptManager
                            category="engineering_report"
                            projectId={projectId}
                            showExecutionStatus={true}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={reportTrigger.enabled}
                          onChange={(e) => setReportTrigger({...reportTrigger, enabled: e.target.checked})}
                          className="rounded"
                        />
                        <span className="text-sm font-medium">⏰ تریگر خودکار گزارش‌گیری</span>
                      </label>
                    </div>

                    {reportTrigger.enabled && (
                      <>
                        <div>
                          <label className="text-xs text-gray-500 block mb-1">بازه زمانی:</label>
                          <select
                            value={`${reportTrigger.interval_minutes}-${reportTrigger.interval_type}`}
                            onChange={(e) => {
                              const [val, type] = e.target.value.split('-');
                              setReportTrigger({
                                ...reportTrigger,
                                interval_minutes: parseInt(val),
                                interval_type: type,
                              });
                            }}
                            className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                          >
                            {triggerIntervals.map((interval, idx) => (
                              <option key={idx} value={`${interval.value}-${interval.type}`}>
                                {interval.label}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-xs text-gray-500 block mb-1">مدل برای گزارش:</label>
                          <select
                            value={reportTrigger.report_model}
                            onChange={(e) => setReportTrigger({...reportTrigger, report_model: e.target.value})}
                            className="w-full p-2 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
                          >
                            {availableModels.filter(m => m.id !== 'all').map(model => (
                              <option key={model.id} value={model.id}>
                                {model.icon} {model.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </>
                    )}
                  </div>

                  {reportTrigger.enabled && (
                    <button
                      onClick={saveReportTrigger}
                      className="mt-4 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
                    >
                      💾 ذخیره تنظیمات
                    </button>
                  )}

                  {reportTrigger.next_run && (
                    <div className="mt-3 text-sm text-gray-500">
                      گزارش بعدی: {new Date(reportTrigger.next_run).toLocaleString('fa-IR')}
                    </div>
                  )}
                </div>

                {/* لیست گزارشات */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
                  <div className="p-4 border-b dark:border-gray-700">
                    <h2 className="font-bold text-lg flex items-center gap-2">
                      <span className="text-xl">📊</span>
                      گزارشات تولید شده
                    </h2>
                  </div>

                  {reportsLoading ? (
                    <div className="p-8 text-center text-gray-400">
                      <div className="animate-spin text-3xl mb-2">⏳</div>
                      در حال بارگذاری...
                    </div>
                  ) : reports.length === 0 ? (
                    <div className="p-8 text-center text-gray-400">
                      <div className="text-4xl mb-2">📭</div>
                      <p>گزارشی ایجاد نشده</p>
                      <div className="mt-4 flex flex-col gap-2 items-center">
                        <button
                          onClick={() => generateEngineeringReport(7)}
                          disabled={generatingReport}
                          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                        >
                          🔬 تولید گزارش مهندسی جامع
                        </button>
                        <button
                          onClick={() => generateReport(7)}
                          disabled={generatingReport}
                          className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600"
                        >
                          📝 یا گزارش ساده
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="divide-y dark:divide-gray-700">
                      {reports.map((report) => (
                        <div
                          key={report.id}
                          className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h3
                              className="font-medium cursor-pointer hover:text-purple-600"
                              onClick={() => loadReportDetail(report.id)}
                            >
                              {report.title}
                            </h3>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500">
                                {report.created_at ? new Date(report.created_at).toLocaleString('fa-IR') : ''}
                              </span>
                              {/* 🆕 دکمه دانلود مارک‌داون */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  window.open(`${API_BASE}/api/projects/${projectId}/export/report/${report.id}/markdown`, '_blank');
                                }}
                                className="px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
                                title="دانلود گزارش به مارک‌داون"
                              >
                                📥 MD
                              </button>
                            </div>
                          </div>
                          {report.summary && (
                            <p
                              className="text-sm text-gray-600 dark:text-gray-400 mb-2 cursor-pointer"
                              onClick={() => loadReportDetail(report.id)}
                            >
                              {report.summary}
                            </p>
                          )}
                          <div className="flex gap-3 text-xs text-gray-500">
                            <span>{report.total_activities ?? 0} فعالیت</span>
                            <span>{(report.total_tokens ?? 0).toLocaleString()} توکن</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* اعتبارسنجی گزارشات */}
            {journalSubTab === 'validation' && (
              <div className="space-y-6">
                {/* توضیحات */}
                <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-xl p-4">
                  <h3 className="font-bold text-purple-700 dark:text-purple-400 mb-2 flex items-center gap-2">
                    <span>✅</span> سیستم اعتبارسنجی گزارشات AI
                  </h3>
                  <p className="text-sm text-purple-600 dark:text-purple-400">
                    این سیستم گزارشات تحلیل‌های AI را اعتبارسنجی می‌کند و بر اساس نتایج، نمره مدل‌ها را بروزرسانی می‌کند.
                    نمره‌دهی تجمعی است یعنی هر بار به نمره قبلی اضافه/کم می‌شود و هیچوقت از صفر شروع نمی‌شود.
                  </p>
                  <div className="mt-3 text-xs text-purple-500 dark:text-purple-400 space-y-1">
                    <div>- یافته‌های درست = +۱ امتیاز</div>
                    <div>- False Positive (اشتباه) = -۲ امتیاز</div>
                    <div>- مشکلات کشف نشده = -۳ امتیاز</div>
                  </div>
                </div>

                {/* نتیجه اعتبارسنجی */}
                {validationResult && (
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                    <h3 className="font-bold mb-4 flex items-center gap-2">
                      <span>📊</span> نتیجه آخرین اعتبارسنجی
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-green-100 dark:bg-green-900/30 rounded-lg">
                        <div className="text-3xl font-bold text-green-600">{validationResult.correct || 0}</div>
                        <div className="text-sm text-green-500">یافته‌های درست</div>
                      </div>
                      <div className="text-center p-4 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                        <div className="text-3xl font-bold text-yellow-600">{validationResult.false_positives || 0}</div>
                        <div className="text-sm text-yellow-500">False Positive</div>
                      </div>
                      <div className="text-center p-4 bg-red-100 dark:bg-red-900/30 rounded-lg">
                        <div className="text-3xl font-bold text-red-600">{validationResult.missed || 0}</div>
                        <div className="text-sm text-red-500">کشف نشده</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* لیست مدل‌ها برای اعتبارسنجی دستی */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                  <h3 className="font-bold mb-4 flex items-center gap-2">
                    <span>🤖</span> اعتبارسنجی دستی مدل‌ها
                  </h3>
                  <p className="text-sm text-gray-500 mb-4">
                    اگر می‌خواهید نمره یک مدل را به صورت دستی تنظیم کنید، مدل را انتخاب و نتایج را وارد کنید.
                  </p>

                  <div className="grid md:grid-cols-2 gap-4">
                    {modelProfiles.slice(0, 6).map((profile) => (
                      <div key={profile.model_id} className="border dark:border-gray-700 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <span className="font-medium">{profile.display_name}</span>
                            <span className={`mr-2 px-2 py-0.5 rounded text-xs ${getTierColor(profile.tier)}`}>
                              {profile.tier}
                            </span>
                          </div>
                          <span className="text-2xl font-bold text-blue-500">{profile.overall_score ?? 0}</span>
                        </div>
                        <div className="text-xs text-gray-500 mb-2">
                          {profile.total_analyses} تحلیل | {profile.total_tasks} وظیفه
                        </div>
                        <button
                          onClick={() => setSelectedProfile(profile)}
                          className="w-full py-2 bg-purple-100 dark:bg-purple-900/30 text-purple-600 rounded hover:bg-purple-200 dark:hover:bg-purple-900/50 text-sm"
                        >
                          ثبت نتیجه اعتبارسنجی
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* پروفایل مدل‌ها */}
            {journalSubTab === 'profiles' && (
              <div className="space-y-6">
                {/* لیدربورد */}
                {leaderboard && Object.keys(leaderboard).length > 0 && (
                  <div className="bg-gradient-to-r from-yellow-100 to-orange-100 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-xl p-6">
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                      <span>🏆</span> برترین‌ها در هر دسته
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      {Object.entries(leaderboard).map(([key, data]: [string, any]) => (
                        <div key={key} className="bg-white dark:bg-gray-800 rounded-lg p-3 text-center shadow">
                          <div className="text-2xl mb-1">
                            {key === 'best_accuracy' ? '🎯' :
                             key === 'best_speed' ? '⚡' :
                             key === 'best_reliability' ? '🛡️' :
                             key === 'best_code_quality' ? '💎' : '🔥'}
                          </div>
                          <div className="text-xs text-gray-500 mb-1">{data.label}</div>
                          <div className="font-medium text-sm truncate">{data.display_name}</div>
                          <div className="text-lg font-bold text-blue-500">{data.score}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* رتبه‌بندی مدل‌ها */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
                  <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
                    <h3 className="font-bold text-lg flex items-center gap-2">
                      <span>📊</span> رتبه‌بندی جامع مدل‌ها
                    </h3>
                    <button
                      onClick={() => { loadModelProfiles(); loadModelRankings(); loadLeaderboard(); }}
                      className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                    >
                      🔄 بروزرسانی
                    </button>
                  </div>

                  {profilesLoading ? (
                    <div className="p-8 text-center text-gray-400">
                      <div className="animate-spin text-3xl mb-2">⏳</div>
                      در حال بارگذاری...
                    </div>
                  ) : modelProfiles.length === 0 ? (
                    <div className="p-8 text-center text-gray-400">
                      <div className="text-4xl mb-2">🤖</div>
                      <p>هنوز پروفایلی ثبت نشده</p>
                      <p className="text-sm mt-2">با اجرای تحلیل سلامت، پروفایل مدل‌ها ایجاد می‌شود</p>
                    </div>
                  ) : (
                    <div className="divide-y dark:divide-gray-700">
                      {modelProfiles.map((profile, idx) => (
                        <div
                          key={profile.model_id}
                          onClick={() => loadProfileDetail(profile.model_id)}
                          className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              {/* رتبه */}
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                                idx === 0 ? 'bg-yellow-400 text-yellow-900' :
                                idx === 1 ? 'bg-gray-300 text-gray-700' :
                                idx === 2 ? 'bg-orange-400 text-orange-900' :
                                'bg-gray-100 dark:bg-gray-700 text-gray-500'
                              }`}>
                                {idx + 1}
                              </div>

                              {/* اطلاعات مدل */}
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">{profile.display_name}</span>
                                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${getTierColor(profile.tier)}`}>
                                    {profile.tier}
                                  </span>
                                </div>
                                <div className="text-xs text-gray-500">
                                  {profile.provider} | {profile.total_tasks} وظیفه
                                </div>
                              </div>
                            </div>

                            {/* نمرات */}
                            <div className="flex items-center gap-6">
                              <div className="text-center">
                                <div className="text-xs text-gray-500">دقت</div>
                                <div className="font-medium text-green-500">{profile.accuracy_score ?? 0}</div>
                              </div>
                              <div className="text-center">
                                <div className="text-xs text-gray-500">سرعت</div>
                                <div className="font-medium text-blue-500">{profile.speed_score ?? 0}</div>
                              </div>
                              <div className="text-center">
                                <div className="text-xs text-gray-500">کامل‌بودن</div>
                                <div className="font-medium text-purple-500">{profile.completeness_score ?? 0}</div>
                              </div>
                              <div className="text-center border-r pr-4 dark:border-gray-600">
                                <div className="text-xs text-gray-500">نمره کل</div>
                                <div className="text-2xl font-bold text-blue-600">{profile.overall_score ?? 0}</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* نکته */}
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-4">
                  <h4 className="font-medium text-blue-700 dark:text-blue-400 mb-2">💡 درباره نمره‌دهی تجمعی</h4>
                  <p className="text-sm text-blue-600 dark:text-blue-400">
                    نمرات مدل‌ها تجمعی هستند و هیچوقت از صفر شروع نمی‌شوند. هر تحلیل جدید به تاریخچه اضافه می‌شود.
                    این روش باعث می‌شود بهترین مدل‌ها برای پروژه‌های آینده قابل شناسایی باشند.
                  </p>
                </div>
              </div>
            )}

            {/* مودال جزئیات پروفایل */}
            {selectedProfile && journalSubTab === 'profiles' && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
                  <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800">
                    <div className="flex items-center gap-3">
                      <h3 className="font-bold">{selectedProfile.display_name || selectedProfile.model_id}</h3>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${getTierColor(selectedProfile.tier || selectedProfile.ranking?.tier)}`}>
                        {selectedProfile.tier || selectedProfile.ranking?.tier}
                      </span>
                    </div>
                    <button
                      onClick={() => setSelectedProfile(null)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="p-4 space-y-6">
                    {/* نمرات */}
                    <div>
                      <h4 className="font-medium mb-3">📊 نمرات تجمعی</h4>
                      <div className="grid grid-cols-3 gap-3">
                        {selectedProfile.scores ? (
                          <>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-blue-500">{selectedProfile.scores.overall}</div>
                              <div className="text-xs text-gray-500">نمره کل</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-green-500">{selectedProfile.scores.accuracy}</div>
                              <div className="text-xs text-gray-500">دقت</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-purple-500">{selectedProfile.scores.completeness}</div>
                              <div className="text-xs text-gray-500">کامل‌بودن</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-orange-500">{selectedProfile.scores.speed}</div>
                              <div className="text-xs text-gray-500">سرعت</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-cyan-500">{selectedProfile.scores.reliability}</div>
                              <div className="text-xs text-gray-500">قابلیت اطمینان</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-pink-500">{selectedProfile.scores.code_quality}</div>
                              <div className="text-xs text-gray-500">کیفیت کد</div>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-blue-500">{selectedProfile.overall_score}</div>
                              <div className="text-xs text-gray-500">نمره کل</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-green-500">{selectedProfile.accuracy_score}</div>
                              <div className="text-xs text-gray-500">دقت</div>
                            </div>
                            <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                              <div className="text-2xl font-bold text-purple-500">{selectedProfile.completeness_score}</div>
                              <div className="text-xs text-gray-500">کامل‌بودن</div>
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    {/* آمار */}
                    {selectedProfile.stats && (
                      <div>
                        <h4 className="font-medium mb-3">📈 آمار عملکرد</h4>
                        <div className="grid grid-cols-3 gap-3 text-sm">
                          <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded">
                            <div className="font-bold text-green-600">{selectedProfile.stats.correct_findings}</div>
                            <div className="text-xs text-gray-500">یافته‌های درست</div>
                          </div>
                          <div className="p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded">
                            <div className="font-bold text-yellow-600">{selectedProfile.stats.false_positives}</div>
                            <div className="text-xs text-gray-500">False Positive</div>
                          </div>
                          <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded">
                            <div className="font-bold text-red-600">{selectedProfile.stats.missed_issues}</div>
                            <div className="text-xs text-gray-500">کشف نشده</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* نقاط قوت و ضعف */}
                    {selectedProfile.capabilities && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-medium mb-2 text-green-600">💪 نقاط قوت</h4>
                          <ul className="text-sm space-y-1">
                            {(selectedProfile.capabilities.strengths || []).map((s: string, i: number) => (
                              <li key={i} className="text-gray-600 dark:text-gray-400">• {s}</li>
                            ))}
                            {(!selectedProfile.capabilities.strengths || selectedProfile.capabilities.strengths.length === 0) && (
                              <li className="text-gray-400">هنوز شناسایی نشده</li>
                            )}
                          </ul>
                        </div>
                        <div>
                          <h4 className="font-medium mb-2 text-red-600">⚠️ نقاط ضعف</h4>
                          <ul className="text-sm space-y-1">
                            {(selectedProfile.capabilities.weaknesses || []).map((w: string, i: number) => (
                              <li key={i} className="text-gray-600 dark:text-gray-400">• {w}</li>
                            ))}
                            {(!selectedProfile.capabilities.weaknesses || selectedProfile.capabilities.weaknesses.length === 0) && (
                              <li className="text-gray-400">هنوز شناسایی نشده</li>
                            )}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* مودال ثبت اعتبارسنجی دستی */}
            {selectedProfile && journalSubTab === 'validation' && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full">
                  <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
                    <h3 className="font-bold">ثبت نتیجه اعتبارسنجی: {selectedProfile.display_name}</h3>
                    <button
                      onClick={() => setSelectedProfile(null)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">یافته‌های درست:</label>
                      <input
                        type="number"
                        min="0"
                        defaultValue="0"
                        id="correct_input"
                        className="w-full mt-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">False Positive (اشتباه):</label>
                      <input
                        type="number"
                        min="0"
                        defaultValue="0"
                        id="false_positive_input"
                        className="w-full mt-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-gray-600 dark:text-gray-400">مشکلات کشف نشده:</label>
                      <input
                        type="number"
                        min="0"
                        defaultValue="0"
                        id="missed_input"
                        className="w-full mt-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                      />
                    </div>
                    <button
                      onClick={() => {
                        const correct = parseInt((document.getElementById('correct_input') as HTMLInputElement)?.value || '0');
                        const falsePos = parseInt((document.getElementById('false_positive_input') as HTMLInputElement)?.value || '0');
                        const missed = parseInt((document.getElementById('missed_input') as HTMLInputElement)?.value || '0');
                        updateModelScore(selectedProfile.model_id, correct, missed, falsePos);
                        setSelectedProfile(null);
                      }}
                      className="w-full py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 font-medium"
                    >
                      ثبت و بروزرسانی نمره
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* تب نقشه راه */}
            {journalSubTab === 'roadmap' && (
              <div className="space-y-6">
                {/* هدر و دکمه‌ها */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="font-bold text-lg flex items-center gap-2">
                        <span className="text-xl">🗺️</span>
                        نقشه راه پروژه
                      </h2>
                      <p className="text-sm text-gray-500 mt-1">
                        موارد انجام‌شده با تیک سبز و موارد در انتظار با باکس خالی نمایش داده می‌شوند
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={generateFieldsForPendingItems}
                        disabled={generatingRoadmapFields || roadmapItems.filter(i => !i.completed && !i.has_field).length === 0}
                        className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 flex items-center gap-2"
                      >
                        {generatingRoadmapFields ? (
                          <>
                            <span className="animate-spin">⏳</span>
                            در حال تولید...
                          </>
                        ) : (
                          <>
                            <span>⚡</span>
                            تولید فیلد برای موارد خالی ({roadmapItems.filter(i => !i.completed && !i.has_field).length})
                          </>
                        )}
                      </button>
                      <button
                        onClick={loadRoadmap}
                        disabled={roadmapLoading}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                      >
                        🔄 بروزرسانی
                      </button>
                    </div>
                  </div>

                  {/* آمار نقشه راه */}
                  <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {roadmapItems.filter(i => i.completed).length}
                      </div>
                      <div className="text-xs text-gray-500">انجام شده</div>
                    </div>
                    <div className="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-yellow-600">
                        {roadmapItems.filter(i => !i.completed).length}
                      </div>
                      <div className="text-xs text-gray-500">در انتظار</div>
                    </div>
                    <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {roadmapItems.filter(i => i.has_field).length}
                      </div>
                      <div className="text-xs text-gray-500">دارای فیلد</div>
                    </div>
                    <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {roadmapItems.length > 0 ? Math.round((roadmapItems.filter(i => i.completed).length / roadmapItems.length) * 100) : 0}%
                      </div>
                      <div className="text-xs text-gray-500">پیشرفت</div>
                    </div>
                  </div>
                </div>

                {roadmapLoading ? (
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-8 text-center text-gray-400">
                    <div className="animate-spin text-3xl mb-2">⏳</div>
                    در حال بارگذاری...
                  </div>
                ) : roadmapItems.length === 0 ? (
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-8 text-center text-gray-400">
                    <div className="text-4xl mb-2">📭</div>
                    <p>نقشه راه تعریف نشده</p>
                    <p className="text-sm mt-2">از تب تحلیل سلامت، گزارش مهندسی را اجرا کنید تا نقشه راه تولید شود</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* بخش فوری */}
                    {roadmapItems.filter(i => i.priority === 'immediate').length > 0 && (
                      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 border-b dark:border-gray-700">
                          <h3 className="font-bold text-red-700 dark:text-red-400 flex items-center gap-2">
                            <span>🔴</span> اقدامات فوری
                          </h3>
                        </div>
                        <div className="divide-y dark:divide-gray-700">
                          {roadmapItems.filter(i => i.priority === 'immediate').map((item) => (
                            <div
                              key={item.id}
                              className="p-4 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                              onClick={() => toggleRoadmapItem(item.id)}
                            >
                              <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                                item.completed
                                  ? 'bg-green-500 border-green-500 text-white'
                                  : 'border-gray-300 dark:border-gray-600'
                              }`}>
                                {item.completed && '✓'}
                              </div>
                              <span className={`flex-1 ${item.completed ? 'line-through text-gray-400' : ''}`}>
                                {item.text}
                              </span>
                              {item.has_field && (
                                <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded">
                                  فیلد ایجاد شده
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* بخش کوتاه‌مدت */}
                    {roadmapItems.filter(i => i.priority === 'short_term').length > 0 && (
                      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
                        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border-b dark:border-gray-700">
                          <h3 className="font-bold text-yellow-700 dark:text-yellow-400 flex items-center gap-2">
                            <span>🟡</span> اقدامات کوتاه‌مدت
                          </h3>
                        </div>
                        <div className="divide-y dark:divide-gray-700">
                          {roadmapItems.filter(i => i.priority === 'short_term').map((item) => (
                            <div
                              key={item.id}
                              className="p-4 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                              onClick={() => toggleRoadmapItem(item.id)}
                            >
                              <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                                item.completed
                                  ? 'bg-green-500 border-green-500 text-white'
                                  : 'border-gray-300 dark:border-gray-600'
                              }`}>
                                {item.completed && '✓'}
                              </div>
                              <span className={`flex-1 ${item.completed ? 'line-through text-gray-400' : ''}`}>
                                {item.text}
                              </span>
                              {item.has_field && (
                                <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded">
                                  فیلد ایجاد شده
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* بخش بلندمدت */}
                    {roadmapItems.filter(i => i.priority === 'long_term').length > 0 && (
                      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
                        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border-b dark:border-gray-700">
                          <h3 className="font-bold text-blue-700 dark:text-blue-400 flex items-center gap-2">
                            <span>🔵</span> اقدامات بلندمدت
                          </h3>
                        </div>
                        <div className="divide-y dark:divide-gray-700">
                          {roadmapItems.filter(i => i.priority === 'long_term').map((item) => (
                            <div
                              key={item.id}
                              className="p-4 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                              onClick={() => toggleRoadmapItem(item.id)}
                            >
                              <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                                item.completed
                                  ? 'bg-green-500 border-green-500 text-white'
                                  : 'border-gray-300 dark:border-gray-600'
                              }`}>
                                {item.completed && '✓'}
                              </div>
                              <span className={`flex-1 ${item.completed ? 'line-through text-gray-400' : ''}`}>
                                {item.text}
                              </span>
                              {item.has_field && (
                                <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded">
                                  فیلد ایجاد شده
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* حالت ایده‌آل */}
                {idealState && (
                  <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl shadow p-6">
                    <h3 className="font-bold text-lg mb-3 flex items-center gap-2">
                      <span>✨</span> حالت ایده‌آل پروژه
                    </h3>
                    <div className="prose dark:prose-invert max-w-none text-sm">
                      <pre className="whitespace-pre-wrap bg-white/50 dark:bg-gray-800/50 p-4 rounded-lg">
                        {idealState}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* مودال جزئیات فعالیت */}
            {selectedLog && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
                  <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800">
                    <h3 className="font-bold">جزئیات فعالیت</h3>
                    <button
                      onClick={() => setSelectedLog(null)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">مدل:</span>
                        <span className="mr-2 font-medium">{selectedLog.model_id}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">نوع:</span>
                        <span className="mr-2 font-medium">{selectedLog.activity_type}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">توکن:</span>
                        <span className="mr-2 font-medium">{selectedLog.tokens_used}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">تأخیر:</span>
                        <span className="mr-2 font-medium">{selectedLog.latency_ms}ms</span>
                      </div>
                    </div>

                    {selectedLog.prompt && (
                      <div>
                        <h4 className="font-medium text-sm text-gray-500 mb-1">پرامپت:</h4>
                        <pre className="p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm overflow-auto whitespace-pre-wrap">
                          {selectedLog.prompt}
                        </pre>
                      </div>
                    )}

                    {selectedLog.response && (
                      <div>
                        <h4 className="font-medium text-sm text-gray-500 mb-1">پاسخ:</h4>
                        <pre className="p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm overflow-auto whitespace-pre-wrap max-h-64">
                          {selectedLog.response}
                        </pre>
                      </div>
                    )}

                    {selectedLog.error_message && (
                      <div>
                        <h4 className="font-medium text-sm text-red-500 mb-1">خطا:</h4>
                        <pre className="p-3 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-600">
                          {selectedLog.error_message}
                        </pre>
                      </div>
                    )}

                    {/* 🆕 عملیات جزئی (DetailedOperation) */}
                    <div className="border-t dark:border-gray-700 pt-4">
                      <h4 className="font-medium text-sm text-gray-500 mb-2 flex items-center gap-2">
                        <span>📋</span>
                        عملیات جزئی ({detailedOperations.length})
                        {loadingOperations && <span className="animate-spin">⏳</span>}
                      </h4>

                      {detailedOperations.length === 0 && !loadingOperations ? (
                        <div className="text-center py-4 text-gray-400 text-sm">
                          عملیات جزئی ثبت نشده
                        </div>
                      ) : (
                        <div className="space-y-2 max-h-64 overflow-auto">
                          {detailedOperations.map((op, idx) => (
                            <div
                              key={op.id}
                              className={`p-3 rounded-lg border text-sm ${
                                op.status === 'success' ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' :
                                op.status === 'error' ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' :
                                'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono bg-gray-200 dark:bg-gray-600 px-1 rounded">
                                    #{op.operation_number}
                                  </span>
                                  <span className="font-medium">{op.operation_type}</span>
                                  {op.target_name && (
                                    <span className="text-xs text-gray-500">
                                      ({op.target_type}: {op.target_name})
                                    </span>
                                  )}
                                </div>
                                <span className={`text-xs ${
                                  op.status === 'success' ? 'text-green-600' :
                                  op.status === 'error' ? 'text-red-600' : 'text-gray-500'
                                }`}>
                                  {op.status === 'success' ? '✓' : op.status === 'error' ? '✗' : '○'}
                                </span>
                              </div>
                              <p className="text-gray-600 dark:text-gray-400">{op.summary}</p>
                              {op.before_value && op.after_value && (
                                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                                  <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded">
                                    <span className="text-red-600">قبل:</span> {op.before_value.substring(0, 100)}...
                                  </div>
                                  <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded">
                                    <span className="text-green-600">بعد:</span> {op.after_value.substring(0, 100)}...
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* مودال جزئیات گزارش */}
            {selectedReport && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-3xl w-full max-h-[80vh] overflow-auto">
                  <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800">
                    <h3 className="font-bold">{selectedReport.title}</h3>
                    <button
                      onClick={() => setSelectedReport(null)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                        <div className="text-2xl font-bold text-blue-500">{selectedReport.total_activities}</div>
                        <div className="text-xs text-gray-500">فعالیت</div>
                      </div>
                      <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                        <div className="text-2xl font-bold text-green-500">{(selectedReport.total_tokens ?? 0).toLocaleString()}</div>
                        <div className="text-xs text-gray-500">توکن</div>
                      </div>
                      <div className="text-center p-3 bg-gray-100 dark:bg-gray-700 rounded">
                        <div className="text-2xl font-bold text-purple-500">{selectedReport.models_used?.length || 0}</div>
                        <div className="text-xs text-gray-500">مدل</div>
                      </div>
                    </div>

                    {selectedReport.summary && (
                      <div>
                        <h4 className="font-medium text-sm text-gray-500 mb-1">خلاصه:</h4>
                        <p className="p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm">
                          {selectedReport.summary}
                        </p>
                      </div>
                    )}

                    {selectedReport.content && (() => {
                      // تلاش برای پارس JSON
                      let parsed: any = null;
                      try {
                        parsed = typeof selectedReport.content === 'string'
                          ? JSON.parse(selectedReport.content)
                          : selectedReport.content;

                        // اگر parsed دارای raw_content است، تلاش برای پارس آن
                        if (parsed?.raw_content) {
                          // تلاش برای استخراج JSON از داخل raw_content (ممکن است در code block باشد)
                          const rawContent = parsed.raw_content;
                          const codeBlockMatch = rawContent.match(/```(?:json)?\s*([\s\S]*?)```/);
                          if (codeBlockMatch) {
                            try {
                              const innerParsed = JSON.parse(codeBlockMatch[1].trim());
                              parsed = innerParsed;
                            } catch (e2) {}
                          } else {
                            // تلاش برای پیدا کردن { و }
                            const firstBrace = rawContent.indexOf('{');
                            const lastBrace = rawContent.lastIndexOf('}');
                            if (firstBrace !== -1 && lastBrace > firstBrace) {
                              try {
                                const innerParsed = JSON.parse(rawContent.substring(firstBrace, lastBrace + 1));
                                parsed = innerParsed;
                              } catch (e3) {}
                            }
                          }
                        }
                      } catch (e) {
                        // اگر JSON نیست، به صورت متن نمایش بده
                      }

                      // اگر parsed نشد یا raw_content دارد (خطای parse در بکند)
                      if (!parsed || parsed.raw_content) {
                        return (
                          <div className="space-y-2">
                            {parsed?.parse_error && (
                              <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded text-sm text-yellow-800 dark:text-yellow-400">
                                ⚠️ خطا در پردازش JSON گزارش - نمایش محتوای خام
                              </div>
                            )}
                            <div>
                              <h4 className="font-medium text-sm text-gray-500 mb-1">جزئیات:</h4>
                              <pre className="p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm overflow-auto max-h-64 whitespace-pre-wrap" dir="ltr">
                                {parsed?.raw_content || selectedReport.content}
                              </pre>
                            </div>
                          </div>
                        );
                      }

                      // رندر ساختاریافته گزارش مهندسی
                      return (
                        <div className="space-y-4">
                          {/* خلاصه مدیریتی */}
                          {parsed.executive_summary && (
                            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
                              <h4 className="font-bold text-blue-700 dark:text-blue-400 mb-2 flex items-center gap-2">
                                <span>📋</span> خلاصه مدیریتی
                              </h4>
                              <p className="text-sm text-blue-800 dark:text-blue-300 whitespace-pre-wrap">
                                {parsed.executive_summary}
                              </p>
                            </div>
                          )}

                          {/* 🆕 گزارش ۴ مرحله‌ای */}
                          {parsed.four_step_results && (
                            <div className="space-y-4">
                              {/* آمار کلی */}
                              {parsed.statistics && (
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                  <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
                                    <div className="text-2xl font-bold text-purple-600">{parsed.statistics.fields_validated || 0}</div>
                                    <div className="text-xs text-gray-500">فیلد تایید شده</div>
                                  </div>
                                  <div className="text-center p-3 bg-red-50 dark:bg-red-900/30 rounded-lg">
                                    <div className="text-2xl font-bold text-red-600">{parsed.statistics.fields_rejected || 0}</div>
                                    <div className="text-xs text-gray-500">فیلد رد شده</div>
                                  </div>
                                  <div className="text-center p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
                                    <div className="text-2xl font-bold text-green-600">{parsed.statistics.issues_converted || 0}</div>
                                    <div className="text-xs text-gray-500">ایراد به فیلد</div>
                                  </div>
                                  <div className="text-center p-3 bg-yellow-50 dark:bg-yellow-900/30 rounded-lg">
                                    <div className="text-2xl font-bold text-yellow-600">{parsed.statistics.issues_archived || 0}</div>
                                    <div className="text-xs text-gray-500">بایگانی شده</div>
                                  </div>
                                  <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                    <div className="text-2xl font-bold text-blue-600">{parsed.statistics.models_count || 0}</div>
                                    <div className="text-xs text-gray-500">مدل استفاده شده</div>
                                  </div>
                                </div>
                              )}

                              {/* مرحله ۱: اعتبارسنجی فیلدها */}
                              {parsed.four_step_results.step1_validate_fields && (
                                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700">
                                  <h4 className="font-bold text-purple-700 dark:text-purple-400 mb-3 flex items-center gap-2">
                                    <span>1️⃣</span> اعتبارسنجی فیلدهای پویا
                                  </h4>
                                  <div className="grid grid-cols-2 gap-3 text-sm">
                                    <div className="p-2 bg-green-100 dark:bg-green-800/30 rounded text-center">
                                      <div className="text-xl font-bold text-green-600">{parsed.four_step_results.step1_validate_fields.validated_count || 0}</div>
                                      <div className="text-xs">✅ تایید شده</div>
                                    </div>
                                    <div className="p-2 bg-red-100 dark:bg-red-800/30 rounded text-center">
                                      <div className="text-xl font-bold text-red-600">{parsed.four_step_results.step1_validate_fields.rejected_count || 0}</div>
                                      <div className="text-xs">❌ رد شده</div>
                                    </div>
                                  </div>
                                  {parsed.four_step_results.step1_validate_fields.error && (
                                    <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-sm text-red-600">
                                      ⚠️ خطا: {parsed.four_step_results.step1_validate_fields.error}
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* مرحله ۲: تبدیل ایرادات به فیلد */}
                              {parsed.four_step_results.step2_health_to_fields && (
                                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700">
                                  <h4 className="font-bold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                                    <span>2️⃣</span> تبدیل ایرادات سلامت به فیلد
                                  </h4>
                                  <div className="grid grid-cols-2 gap-3 text-sm">
                                    <div className="p-2 bg-blue-100 dark:bg-blue-800/30 rounded text-center">
                                      <div className="text-xl font-bold text-blue-600">{parsed.four_step_results.step2_health_to_fields.created_count || 0}</div>
                                      <div className="text-xs">🆕 فیلد ایجاد شده</div>
                                    </div>
                                    <div className="p-2 bg-yellow-100 dark:bg-yellow-800/30 rounded text-center">
                                      <div className="text-xl font-bold text-yellow-600">{parsed.four_step_results.step2_health_to_fields.archived_count || 0}</div>
                                      <div className="text-xs">📦 بایگانی شده</div>
                                    </div>
                                  </div>
                                  {parsed.four_step_results.step2_health_to_fields.error && (
                                    <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-sm text-red-600">
                                      ⚠️ خطا: {parsed.four_step_results.step2_health_to_fields.error}
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* مرحله ۳: ارزیابی مدل‌ها */}
                              {parsed.four_step_results.step3_evaluate_models && (
                                <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-700">
                                  <h4 className="font-bold text-orange-700 dark:text-orange-400 mb-3 flex items-center gap-2">
                                    <span>3️⃣</span> ارزیابی مدل‌ها
                                  </h4>
                                  {parsed.four_step_results.step3_evaluate_models.models_evaluated?.length > 0 ? (
                                    <div className="space-y-2">
                                      {parsed.four_step_results.step3_evaluate_models.models_evaluated.map((model: any, idx: number) => (
                                        <div key={idx} className="p-2 bg-white dark:bg-gray-800 rounded flex justify-between items-center">
                                          <span className="font-medium">{model.model_id || model}</span>
                                          {model.score && <span className="text-orange-600 font-bold">{model.score}%</span>}
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-sm text-gray-500">مدلی ارزیابی نشد</p>
                                  )}
                                  {parsed.four_step_results.step3_evaluate_models.error && (
                                    <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-sm text-red-600">
                                      ⚠️ خطا: {parsed.four_step_results.step3_evaluate_models.error}
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* مرحله ۴: به‌روزرسانی نقشه راه */}
                              {parsed.four_step_results.step4_update_roadmap && (
                                <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-700">
                                  <h4 className="font-bold text-indigo-700 dark:text-indigo-400 mb-3 flex items-center gap-2">
                                    <span>4️⃣</span> به‌روزرسانی نقشه راه
                                  </h4>
                                  <div className="grid grid-cols-2 gap-3 text-sm">
                                    <div className={`p-2 rounded text-center ${parsed.four_step_results.step4_update_roadmap.roadmap_updated ? 'bg-green-100 dark:bg-green-800/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
                                      <div className="text-xl">{parsed.four_step_results.step4_update_roadmap.roadmap_updated ? '✅' : '➖'}</div>
                                      <div className="text-xs">نقشه راه</div>
                                    </div>
                                    <div className={`p-2 rounded text-center ${parsed.four_step_results.step4_update_roadmap.ideal_state_updated ? 'bg-green-100 dark:bg-green-800/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
                                      <div className="text-xl">{parsed.four_step_results.step4_update_roadmap.ideal_state_updated ? '✅' : '➖'}</div>
                                      <div className="text-xs">وضعیت ایده‌آل</div>
                                    </div>
                                  </div>
                                  {parsed.four_step_results.step4_update_roadmap.error && (
                                    <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-sm text-red-600">
                                      ⚠️ خطا: {parsed.four_step_results.step4_update_roadmap.error}
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* مدل‌های استفاده شده */}
                              {parsed.models_used?.length > 0 && (
                                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                  <span className="text-xs text-gray-500">مدل‌های استفاده شده: </span>
                                  {parsed.models_used.map((model: string, idx: number) => (
                                    <span key={idx} className="inline-block px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs rounded mr-1">
                                      {model}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* امتیاز سلامت */}
                          {parsed.project_health && (
                            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700">
                              <h4 className="font-bold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
                                <span>💚</span> سلامت پروژه
                              </h4>
                              <div className="flex items-center gap-4 mb-3">
                                <div className="text-4xl font-bold text-green-600">{parsed.project_health.score}%</div>
                                <div className="text-lg text-green-700 dark:text-green-400">{parsed.project_health.status}</div>
                              </div>
                              {parsed.project_health.key_metrics && (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                                  {Object.entries(parsed.project_health.key_metrics).map(([key, value]) => (
                                    <div key={key} className="text-center p-2 bg-white dark:bg-gray-800 rounded">
                                      <div className="font-bold text-green-600">{String(value)}%</div>
                                      <div className="text-gray-500">{key.replace(/_/g, ' ')}</div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* اعتبارسنجی تحلیل سلامت */}
                          {parsed.health_analysis_validation && (
                            <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700">
                              <h4 className="font-bold text-purple-700 dark:text-purple-400 mb-3 flex items-center gap-2">
                                <span>🔍</span> نتیجه اعتبارسنجی تحلیل سلامت
                              </h4>
                              <div className="grid grid-cols-3 gap-3 mb-3">
                                <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
                                  <div className="text-2xl font-bold text-purple-600">{parsed.health_analysis_validation.total_reviewed || 0}</div>
                                  <div className="text-xs text-gray-500">بررسی شده</div>
                                </div>
                                <div className="text-center p-2 bg-green-100 dark:bg-green-800/30 rounded">
                                  <div className="text-2xl font-bold text-green-600">{parsed.health_analysis_validation.validated_issues?.length || 0}</div>
                                  <div className="text-xs text-gray-500">✅ تایید شده</div>
                                </div>
                                <div className="text-center p-2 bg-red-100 dark:bg-red-800/30 rounded">
                                  <div className="text-2xl font-bold text-red-600">{parsed.health_analysis_validation.rejected_issues?.length || 0}</div>
                                  <div className="text-xs text-gray-500">❌ رد شده</div>
                                </div>
                              </div>
                              {parsed.health_analysis_validation.validation_summary && (
                                <p className="text-sm text-purple-600 dark:text-purple-400 bg-white dark:bg-gray-800 p-2 rounded">
                                  {parsed.health_analysis_validation.validation_summary}
                                </p>
                              )}

                              {/* ایرادات تایید شده */}
                              {parsed.health_analysis_validation.validated_issues?.length > 0 && (
                                <div className="mt-3">
                                  <h5 className="font-medium text-sm text-green-700 dark:text-green-400 mb-2">ایرادات تایید شده:</h5>
                                  <div className="space-y-2 max-h-40 overflow-auto">
                                    {parsed.health_analysis_validation.validated_issues.map((issue: any, idx: number) => (
                                      <div key={idx} className="text-xs p-2 bg-green-100 dark:bg-green-800/30 rounded border-r-2 border-green-500">
                                        <div className="font-medium">{issue.original_issue?.file || 'نامشخص'}</div>
                                        <div className="text-gray-600 dark:text-gray-400">{issue.original_issue?.message || issue.validation_note}</div>
                                        <div className="flex gap-2 mt-1">
                                          <span className="text-green-600">امتیاز: {issue.validation_score}</span>
                                          <span className="text-purple-600">اولویت: {issue.priority}</span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* ایرادات رد شده */}
                              {parsed.health_analysis_validation.rejected_issues?.length > 0 && (
                                <div className="mt-3">
                                  <h5 className="font-medium text-sm text-red-700 dark:text-red-400 mb-2">ایرادات رد شده:</h5>
                                  <div className="space-y-2 max-h-40 overflow-auto">
                                    {parsed.health_analysis_validation.rejected_issues.map((issue: any, idx: number) => (
                                      <div key={idx} className="text-xs p-2 bg-red-100 dark:bg-red-800/30 rounded border-r-2 border-red-500">
                                        <div className="font-medium">{issue.original_issue?.file || 'نامشخص'}</div>
                                        <div className="text-gray-600 dark:text-gray-400">{issue.original_issue?.message}</div>
                                        <div className="text-red-600 mt-1">دلیل رد: {issue.rejection_reason}</div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* باگ‌ها و مشکلات */}
                          {parsed.bugs_and_issues?.length > 0 && (
                            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700">
                              <h4 className="font-bold text-red-700 dark:text-red-400 mb-3 flex items-center gap-2">
                                <span>🐛</span> باگ‌ها و مشکلات ({parsed.bugs_and_issues.length})
                              </h4>
                              <div className="space-y-2 max-h-48 overflow-auto">
                                {parsed.bugs_and_issues.map((bug: any, idx: number) => (
                                  <div key={idx} className={`p-2 rounded text-sm ${
                                    bug.severity === 'critical' ? 'bg-red-200 dark:bg-red-800/50' :
                                    bug.severity === 'high' ? 'bg-orange-100 dark:bg-orange-800/30' :
                                    'bg-yellow-100 dark:bg-yellow-800/30'
                                  }`}>
                                    <div className="flex items-center justify-between">
                                      <span className="font-medium">{bug.title}</span>
                                      <span className={`text-xs px-2 py-0.5 rounded ${
                                        bug.severity === 'critical' ? 'bg-red-500 text-white' :
                                        bug.severity === 'high' ? 'bg-orange-500 text-white' :
                                        'bg-yellow-500 text-black'
                                      }`}>{bug.severity}</span>
                                    </div>
                                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">{bug.description}</div>
                                    {bug.file && <div className="text-xs text-blue-500 mt-1">📁 {bug.file}</div>}
                                    {bug.suggested_fix && <div className="text-xs text-green-600 mt-1">💡 {bug.suggested_fix}</div>}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* تحلیل فنی */}
                          {parsed.technical_analysis && (
                            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border dark:border-gray-700">
                              <h4 className="font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                                <span>🔧</span> تحلیل فنی
                              </h4>
                              <div className="grid md:grid-cols-2 gap-4">
                                {parsed.technical_analysis.strengths?.length > 0 && (
                                  <div>
                                    <h5 className="text-sm font-medium text-green-600 mb-1">💪 نقاط قوت:</h5>
                                    <ul className="text-xs space-y-1">
                                      {parsed.technical_analysis.strengths.map((s: string, i: number) => (
                                        <li key={i} className="text-gray-600 dark:text-gray-400">• {s}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {parsed.technical_analysis.weaknesses?.length > 0 && (
                                  <div>
                                    <h5 className="text-sm font-medium text-red-600 mb-1">⚠️ نقاط ضعف:</h5>
                                    <ul className="text-xs space-y-1">
                                      {parsed.technical_analysis.weaknesses.map((w: string, i: number) => (
                                        <li key={i} className="text-gray-600 dark:text-gray-400">• {w}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                              {parsed.technical_analysis.architecture_review && (
                                <div className="mt-3 text-xs text-gray-600 dark:text-gray-400 p-2 bg-white dark:bg-gray-700 rounded">
                                  <span className="font-medium">معماری: </span>
                                  {parsed.technical_analysis.architecture_review}
                                </div>
                              )}
                            </div>
                          )}

                          {/* پیشنهادات */}
                          {parsed.recommendations?.length > 0 && (
                            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700">
                              <h4 className="font-bold text-amber-700 dark:text-amber-400 mb-3 flex items-center gap-2">
                                <span>💡</span> پیشنهادات ({parsed.recommendations.length})
                              </h4>
                              <div className="space-y-2 max-h-48 overflow-auto">
                                {parsed.recommendations.map((rec: any, idx: number) => (
                                  <div key={idx} className={`p-2 rounded text-sm ${
                                    rec.priority === 'high' ? 'bg-amber-200 dark:bg-amber-800/50' :
                                    'bg-amber-100 dark:bg-amber-800/30'
                                  }`}>
                                    <div className="flex items-center justify-between">
                                      <span className="font-medium">{rec.title}</span>
                                      <span className="text-xs text-gray-500">تلاش: {rec.effort || 'نامشخص'}</span>
                                    </div>
                                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">{rec.description}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* نقشه راه */}
                          {parsed.roadmap && (
                            <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-700">
                              <h4 className="font-bold text-indigo-700 dark:text-indigo-400 mb-3 flex items-center gap-2">
                                <span>🗺️</span> نقشه راه
                              </h4>
                              <div className="space-y-3">
                                {parsed.roadmap.immediate?.length > 0 && (
                                  <div>
                                    <h5 className="text-sm font-medium text-red-600 mb-1">🔥 فوری:</h5>
                                    <div className="space-y-1">
                                      {parsed.roadmap.immediate.map((t: any, i: number) => (
                                        <div key={i} className="text-xs p-2 bg-red-100 dark:bg-red-800/30 rounded">
                                          <span className="font-medium">{t.task}</span>
                                          {t.target_path && <span className="text-blue-500 mr-2">📁 {t.target_path}</span>}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {parsed.roadmap.short_term?.length > 0 && (
                                  <div>
                                    <h5 className="text-sm font-medium text-amber-600 mb-1">📅 کوتاه‌مدت:</h5>
                                    <div className="space-y-1">
                                      {parsed.roadmap.short_term.map((t: any, i: number) => (
                                        <div key={i} className="text-xs p-2 bg-amber-100 dark:bg-amber-800/30 rounded">
                                          <span className="font-medium">{t.task}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {parsed.roadmap.long_term?.length > 0 && (
                                  <div>
                                    <h5 className="text-sm font-medium text-green-600 mb-1">🎯 بلندمدت:</h5>
                                    <div className="space-y-1">
                                      {parsed.roadmap.long_term.map((t: any, i: number) => (
                                        <div key={i} className="text-xs p-2 bg-green-100 dark:bg-green-800/30 rounded">
                                          <span className="font-medium">{t.task}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* حالت ایده‌آل */}
                          {parsed.comprehensive_ideal_state && (
                            <div className="p-4 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg border border-cyan-200 dark:border-cyan-700">
                              <h4 className="font-bold text-cyan-700 dark:text-cyan-400 mb-3 flex items-center gap-2">
                                <span>🌟</span> حالت ایده‌آل
                              </h4>
                              <p className="text-sm text-cyan-800 dark:text-cyan-300 whitespace-pre-wrap mb-3">
                                {parsed.comprehensive_ideal_state.description}
                              </p>
                              {parsed.comprehensive_ideal_state.current_deficiencies?.length > 0 && (
                                <div className="mb-2">
                                  <h5 className="text-xs font-medium text-red-600">کمبودهای فعلی:</h5>
                                  <ul className="text-xs text-gray-600 dark:text-gray-400">
                                    {parsed.comprehensive_ideal_state.current_deficiencies.map((d: string, i: number) => (
                                      <li key={i}>• {d}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 🆕 Fallback: اگر هیچ بخش ساختاریافته‌ای نبود، محتوا را به شکل خوانا نمایش بده */}
                          {!parsed.executive_summary && !parsed.project_health && !parsed.bugs_and_issues?.length && !parsed.recommendations?.length && !parsed.technical_analysis && !parsed.health_analysis_validation && (
                            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border dark:border-gray-700">
                              <h4 className="font-bold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                                <span>📋</span> محتوای گزارش
                              </h4>
                              <div className="space-y-2">
                                {Object.entries(parsed).filter(([key, value]) =>
                                  value && typeof value !== 'function' && key !== 'raw_content_backup' && key !== 'parse_recovered'
                                ).map(([key, value]) => (
                                  <div key={key} className="border-b border-gray-200 dark:border-gray-600 pb-2 last:border-0">
                                    <div className="text-xs font-medium text-gray-500 mb-1">{key.replace(/_/g, ' ')}:</div>
                                    <div className="text-sm text-gray-700 dark:text-gray-300">
                                      {typeof value === 'string' ? (
                                        <p className="whitespace-pre-wrap">{value}</p>
                                      ) : typeof value === 'number' ? (
                                        <span className="font-bold">{value}</span>
                                      ) : Array.isArray(value) ? (
                                        <ul className="list-disc list-inside">
                                          {value.slice(0, 10).map((item, idx) => (
                                            <li key={idx}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
                                          ))}
                                          {value.length > 10 && <li className="text-gray-400">... و {value.length - 10} مورد دیگر</li>}
                                        </ul>
                                      ) : typeof value === 'object' ? (
                                        <pre className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded overflow-auto max-h-24">
                                          {JSON.stringify(value, null, 2)}
                                        </pre>
                                      ) : (
                                        String(value)
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* نمایش محتوای خام در صورت نیاز */}
                          <details className="text-xs">
                            <summary className="cursor-pointer text-gray-500 hover:text-gray-700">📄 نمایش JSON خام</summary>
                            <pre className="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-auto max-h-48">
                              {JSON.stringify(parsed, null, 2)}
                            </pre>
                          </details>
                        </div>
                      );
                    })()}

                    <div className="text-xs text-gray-500 flex justify-between">
                      <span>بازه: {selectedReport.period_start ? new Date(selectedReport.period_start).toLocaleDateString('fa-IR') : ''} تا {selectedReport.period_end ? new Date(selectedReport.period_end).toLocaleDateString('fa-IR') : ''}</span>
                      <span>تولید شده توسط: {selectedReport.generated_by}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* محتوای تب تحلیل سلامت */}
        {activeTab === 'health' && (
          <div className="space-y-6">
            <ProjectHealthPanel projectId={projectId as string} onHealthUpdate={loadProject} />
          </div>
        )}

        {/* محتوای تب بازرس ویژه */}
        {activeTab === 'inspector' && (
          <div className="space-y-4">
            {/* هدر */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <span className="text-3xl">🔍</span>
                <div>
                  <h2 className="text-xl font-bold text-red-800 dark:text-red-200">بازرس ویژه</h2>
                  <p className="text-red-600 dark:text-red-400 text-sm">ابزار پیشرفته برای بازرسی و تحلیل عمیق پروژه</p>
                </div>
              </div>
              {/* نمایش سرویس‌های متصل */}
              {inspectorPowerOn && inspectorServices.length > 0 && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-500">سرویس‌ها:</span>
                  {inspectorServices.map(s => (
                    <span
                      key={s.id}
                      className={`px-2 py-1 rounded-full ${
                        s.status === 'deployed'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                      }`}
                    >
                      {s.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* محتوای اصلی - اسکرین و چت */}
            <div className="flex flex-row-reverse gap-4" style={{ minHeight: '520px' }}>
              {/* اسکرین سمت چپ (در RTL) - ابعاد 5.1" x 2.8" (نسبت 1.82:1 - افقی/landscape) - 1.5x بزرگتر */}
              <div className="flex-shrink-0 flex flex-col items-center" style={{ width: '840px' }}>
                <div className="bg-black rounded-2xl p-2 shadow-2xl w-full">
                  {/* فریم دستگاه - افقی */}
                  <div
                    className="bg-gray-900 rounded-xl overflow-hidden relative"
                    style={{ aspectRatio: '1.82/1' }}
                  >
                    {/* صفحه نمایش */}
                    <div className="h-full w-full bg-gradient-to-br from-gray-800 to-gray-900 p-1 flex flex-col relative">
                      {/* لایه لاگ‌های پس‌زمینه */}
                      {inspectorPowerOn && inspectorBackendLogs.length > 0 && (
                        <div className="absolute inset-0 p-1 overflow-hidden opacity-30 pointer-events-none z-0">
                          <div className="h-full bg-black/50 rounded-lg p-2 font-mono text-[8px] text-green-400 overflow-hidden">
                            {inspectorBackendLogs.slice(0, 15).map((log, i) => (
                              <div key={log.id} className={`truncate ${log.level === 'error' ? 'text-red-400' : log.level === 'warn' ? 'text-yellow-400' : ''}`}>
                                [{new Date(log.timestamp).toLocaleTimeString('fa-IR')}] {log.message?.slice(0, 60)}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* محتوای اسکرین */}
                      <div className="flex-1 bg-gray-800/50 rounded-lg overflow-hidden relative z-10">
                        {inspectorLoading ? (
                          <div className="h-full flex items-center justify-center">
                            <div className="text-center text-gray-400">
                              <div className="animate-spin text-3xl mb-2">⚡</div>
                              <p className="text-xs">در حال بارگذاری...</p>
                            </div>
                          </div>
                        ) : inspectorPowerOn && inspectorFrontendUrl ? (
                          <div className="relative w-full h-full">
                            {/* 🆕 نوار آدرس — نمایش URL فعلی + امکان ویرایش + ناوبری */}
                            <div className="absolute top-0 left-0 right-0 z-40 flex items-center gap-1 px-2 py-1 bg-gray-800/95 backdrop-blur-sm border-b border-gray-600" dir="ltr">
                              <span className="text-[10px] text-gray-400 flex-shrink-0">🔗</span>
                              <input
                                type="text"
                                value={inspectorFrontendUrl || ''}
                                onChange={(e) => setInspectorFrontendUrl(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    const typed = (e.target as HTMLInputElement).value;
                                    setInspectorFrontendUrl(typed);
                                    setInspectorIframeSrc(_getProxyUrl(typed));
                                  }
                                }}
                                className="flex-1 text-[10px] bg-gray-700/80 text-gray-200 rounded px-2 py-0.5 border border-gray-600 focus:border-blue-500 focus:outline-none truncate"
                                title="آدرس صفحه فعلی — قابل ویرایش. Enter برای ناوبری"
                                placeholder="URL..."
                              />
                              <button
                                onClick={() => {
                                  // same-origin — reload مستقیم بدون تغییر آدرس
                                  try {
                                    inspectorIframeRef.current?.contentWindow?.location.reload();
                                  } catch {
                                    // fallback: تنظیم مجدد src
                                    if (inspectorFrontendUrl) setInspectorIframeSrc(_getProxyUrl(inspectorFrontendUrl));
                                  }
                                }}
                                className="text-[10px] text-gray-400 hover:text-white px-1 flex-shrink-0"
                                title="بارگذاری مجدد"
                              >🔄</button>
                            </div>
                            <iframe
                              ref={inspectorIframeRef}
                              src={inspectorIframeSrc}
                              style={{ paddingTop: '24px' }}
                              className="w-full h-full border-0 bg-white"
                              title="پیش‌نمایش فرانت‌اند"
                              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                              onLoad={() => {
                                setInspectorIframeLoaded(true);
                                setInspectorIframeError(false);
                                // 🔀 same-origin (proxy) — خواندن URL واقعی بعد از هر navigation
                                const actual = _readIframeActualUrl();
                                if (actual) setInspectorFrontendUrl(actual);
                              }}
                              onError={() => {
                                setInspectorIframeError(true);
                                setInspectorIframeLoaded(false);
                              }}
                            />
                            {/* 📸 نوار ابزار بالای iframe (زیر نوار آدرس) */}
                            <div className="absolute top-7 left-2 z-50 flex gap-1 pointer-events-auto">
                              {/* دکمه عکس‌برداری (Playwright) */}
                              <button
                                onClick={takeVisualDebugScreenshot}
                                disabled={visualDebugTakingScreenshot || inspectorOpLock}
                                className="px-2 py-1 bg-purple-600/90 hover:bg-purple-700 text-white text-[10px] rounded-md shadow-lg transition-all disabled:opacity-50 flex items-center gap-1"
                                title="عکس‌برداری از آدرس نوار بالا (Playwright)"
                              >
                                {visualDebugTakingScreenshot ? <span className="animate-spin">⏳</span> : <span>📸</span>}
                                عکس
                                {visualDebugScreenshots.length > 0 && (
                                  <span className="bg-white text-purple-600 text-[9px] rounded-full px-1 font-bold">{visualDebugScreenshots.length}</span>
                                )}
                              </button>
                              {/* دکمه لاگ‌های کنسول پروژه ایمپورت شده */}
                              <button
                                onClick={() => setShowImportedConsoleLogs(!showImportedConsoleLogs)}
                                className={`px-2 py-1 text-[10px] rounded-md shadow-lg transition-all flex items-center gap-1 ${
                                  showImportedConsoleLogs ? 'bg-blue-600 text-white' : 'bg-gray-700/90 hover:bg-gray-600 text-gray-200'
                                }`}
                                title="لاگ‌های کنسول پروژه ایمپورت شده"
                              >
                                📋 کنسول
                                {importedProjectConsoleLogs.length > 0 && (
                                  <span className={`text-[9px] rounded-full px-1 font-bold ${
                                    importedProjectConsoleLogs.some(l => l.level === 'error') ? 'bg-red-500 text-white' : 'bg-gray-500 text-white'
                                  }`}>{importedProjectConsoleLogs.length}</span>
                                )}
                              </button>
                            </div>

                            {/* 📋 پنل لاگ‌های کنسول پروژه ایمپورت شده */}
                            {showImportedConsoleLogs && importedProjectConsoleLogs.length > 0 && (
                              <div className="absolute bottom-0 left-0 right-0 z-40 max-h-[40%] bg-gray-900/95 backdrop-blur border-t border-gray-700 overflow-auto" dir="ltr">
                                <div className="sticky top-0 bg-gray-900 px-3 py-1.5 flex items-center justify-between border-b border-gray-700">
                                  <span className="text-[10px] text-gray-400 font-mono">📋 Console Logs (پروژه ایمپورت شده) - {importedProjectConsoleLogs.length} لاگ</span>
                                  <div className="flex gap-2">
                                    <button onClick={() => setImportedProjectConsoleLogs([])} className="text-[10px] text-red-400 hover:text-red-300">پاک‌سازی</button>
                                    <button onClick={() => setShowImportedConsoleLogs(false)} className="text-[10px] text-gray-400 hover:text-white">✕</button>
                                  </div>
                                </div>
                                <div className="p-2 font-mono text-[10px] space-y-0.5">
                                  {importedProjectConsoleLogs.slice(-100).map(log => (
                                    <div key={log.id} className={`px-2 py-0.5 rounded ${
                                      log.level === 'error' ? 'text-red-400 bg-red-900/20' :
                                      log.level === 'warn' ? 'text-yellow-400 bg-yellow-900/20' :
                                      log.level === 'info' ? 'text-blue-400' :
                                      log.level === 'debug' ? 'text-gray-500' :
                                      'text-green-400'
                                    }`}>
                                      <span className="text-gray-500">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                                      <span className={`ml-1 font-bold ${
                                        log.level === 'error' ? 'text-red-500' : log.level === 'warn' ? 'text-yellow-500' : 'text-gray-500'
                                      }`}>{log.level.toUpperCase()}</span>
                                      <span className="ml-2">{log.message}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* 🔒 قفل iframe هنگام عملیات بررسی/اصلاح */}
                            {inspectorOpLock && (
                              <div className="absolute inset-0 z-50 bg-black/20 backdrop-blur-[1px] flex flex-col items-center justify-center cursor-not-allowed"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <div className="bg-gray-900/90 rounded-xl px-6 py-4 text-center shadow-2xl border border-gray-700">
                                  <div className="text-2xl mb-2 animate-pulse">
                                    {inspectorOpType === 'investigate' ? '🔍' : '🔧'}
                                  </div>
                                  <p className="text-white text-sm font-medium mb-1">
                                    {inspectorOpType === 'investigate' ? 'در حال بررسی خطا...' : 'در حال اصلاح خودکار...'}
                                  </p>
                                  <p className="text-gray-400 text-xs">
                                    صفحه پیش‌نمایش قفل است
                                  </p>
                                  {/* دکمه لغو */}
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (inspectorOpAbortRef.current) {
                                        inspectorOpAbortRef.current.abort();
                                      }
                                      // لغو background batch task
                                      if (inspectorBatchTaskKeyRef.current) {
                                        fetch(`${API_BASE}/api/render/inspector/smart-chat/batch-cancel/${inspectorBatchTaskKeyRef.current}`, { method: 'POST' }).catch(() => {});
                                        inspectorBatchTaskKeyRef.current = null;
                                        try { sessionStorage.removeItem('inspector_batch_task'); } catch {}
                                      }
                                      setInspectorOpLock(false);
                                      setInspectorOpType(null);
                                      setInvestigateLoading(false);
                                      setFixLoading(false);
                                      setInspectorChatMessages(prev => [...prev, {
                                        id: `cancel_${Date.now()}`,
                                        role: 'system' as const,
                                        content: '⏹ عملیات توسط کاربر لغو شد',
                                        timestamp: new Date(),
                                      }]);
                                    }}
                                    className="mt-3 px-4 py-1.5 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded-lg transition-colors"
                                  >
                                    ⏹ لغو عملیات
                                  </button>
                                </div>
                              </div>
                            )}
                            {/* نمایش خطای بارگذاری iframe */}
                            {inspectorIframeError && (
                              <div className="absolute inset-0 z-40 flex items-center justify-center bg-gray-900/80">
                                <div className="text-center p-4">
                                  <div className="text-4xl mb-3">🔴</div>
                                  <p className="text-red-400 text-sm font-medium mb-2">صفحه پیش‌نمایش بارگذاری نشد</p>
                                  <p className="text-gray-400 text-xs mb-3">سرویس ممکن است خاموش یا در حال راه‌اندازی باشد (503)</p>
                                  <button
                                    onClick={() => {
                                      setInspectorIframeError(false);
                                      setInspectorIframeLoaded(false);
                                      setInspectorIframeSrc(_getProxyUrl(inspectorFrontendUrl));
                                    }}
                                    className="px-4 py-2 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors"
                                  >
                                    تلاش مجدد
                                  </button>
                                </div>
                              </div>
                            )}
                            {/* نمایش وضعیت بارگذاری */}
                            {!inspectorIframeLoaded && !inspectorIframeError && (
                              <div className="absolute inset-0 z-40 flex items-center justify-center bg-gray-900/60 pointer-events-none">
                                <div className="text-center">
                                  <div className="animate-spin text-2xl mb-2">⏳</div>
                                  <p className="text-gray-300 text-xs">بارگذاری صفحه پیش‌نمایش...</p>
                                </div>
                              </div>
                            )}

                            {/* لایه ردیابی فعالیت کاربر */}
                            <div
                              ref={inspectorOverlayRef}
                              className="absolute inset-0 z-30 pointer-events-none"
                            >
                              {/* پیام‌های سیستمی موقت (فقط info/error، نه action) */}
                              {inspectorTransientMessages.filter(m => m.type !== 'action').length > 0 && (
                                <div className="absolute top-2 right-2 flex flex-col gap-1 z-50 pointer-events-auto" dir="rtl">
                                  {inspectorTransientMessages.filter(m => m.type !== 'action').map(msg => (
                                    <div
                                      key={msg.id}
                                      className={`px-3 py-1.5 rounded-lg text-xs font-medium shadow-lg transition-all duration-500 max-w-[280px] ${
                                        msg.fadeOut ? 'opacity-0 transform translate-x-4' : 'opacity-100'
                                      } ${
                                        msg.type === 'backend' ? 'bg-purple-500/90 text-white' :
                                        msg.type === 'error' ? 'bg-red-500/90 text-white' :
                                        'bg-gray-700/90 text-white'
                                      }`}
                                    >
                                      <span className="truncate">{msg.content}</span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* لایه توقف (وقتی خطا شناسایی شده) */}
                              {inspectorPaused && (
                                <div className="absolute inset-0 bg-red-900/50 backdrop-blur-sm flex items-center justify-center z-40">
                                  <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-2xl max-w-md text-center">
                                    <div className="text-4xl mb-2">⛔</div>
                                    <h3 className="text-lg font-bold text-red-600 mb-2">خطا شناسایی شد</h3>
                                    {inspectorPausedError && (
                                      <>
                                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                                          {inspectorPausedError.message}
                                        </p>
                                        {inspectorPausedError.analyzing ? (
                                          <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
                                            <div className="animate-spin">🔍</div>
                                            <span>در حال بررسی کد منبع...</span>
                                          </div>
                                        ) : (
                                          <button
                                            onClick={resumeAfterError}
                                            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm"
                                          >
                                            ✅ ادامه کار
                                          </button>
                                        )}
                                      </>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                            {/* 🆕 نشانگر موس مجازی */}
                            {inspectorVirtualCursor.visible && (
                              <div
                                className="absolute pointer-events-none z-50 transition-all duration-300 ease-out"
                                style={{
                                  left: `${inspectorVirtualCursor.x}%`,
                                  top: `${inspectorVirtualCursor.y}%`,
                                  transform: 'translate(-50%, -50%)'
                                }}
                              >
                                {/* نشانگر موس */}
                                <svg
                                  width="24"
                                  height="24"
                                  viewBox="0 0 24 24"
                                  className="drop-shadow-lg animate-pulse"
                                >
                                  <path
                                    d="M3 3l9 18 3-9 9-3z"
                                    fill="#ef4444"
                                    stroke="#fff"
                                    strokeWidth="2"
                                  />
                                </svg>
                                {/* نشانگر مدل */}
                                {inspectorVirtualCursor.model_id && (
                                  <div className="absolute -top-6 -right-2 bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap shadow-lg">
                                    {inspectorVirtualCursor.model_id}
                                  </div>
                                )}
                                {/* افکت کلیک */}
                                <div className="absolute inset-0 w-6 h-6 bg-red-500/30 rounded-full animate-ping" />
                              </div>
                            )}

                            {/* 🆕 نوارهای اسکن بصری */}
                            {inspectorScanBars.scanning && (
                              <>
                                {/* نوار عمودی - حرکت از چپ به راست */}
                                <div
                                  className="absolute top-0 bottom-0 w-0.5 bg-green-500 pointer-events-none z-40 transition-all duration-75"
                                  style={{
                                    left: `${inspectorScanBars.verticalX}%`,
                                    boxShadow: '0 0 8px 2px rgba(34, 197, 94, 0.6), 0 0 20px 4px rgba(34, 197, 94, 0.3)'
                                  }}
                                />

                                {/* نوار افقی - حرکت از بالا به پایین */}
                                <div
                                  className="absolute left-0 right-0 h-0.5 bg-green-500 pointer-events-none z-40 transition-all duration-75"
                                  style={{
                                    top: `${inspectorScanBars.horizontalY}%`,
                                    boxShadow: '0 0 8px 2px rgba(34, 197, 94, 0.6), 0 0 20px 4px rgba(34, 197, 94, 0.3)'
                                  }}
                                />

                                {/* نقطه تقاطع (هدف) */}
                                {inspectorScanBars.targetFound && inspectorScanBars.intersection && (
                                  <div
                                    className="absolute pointer-events-none z-50"
                                    style={{
                                      left: `${inspectorScanBars.intersection.x}%`,
                                      top: `${inspectorScanBars.intersection.y}%`,
                                      transform: 'translate(-50%, -50%)'
                                    }}
                                  >
                                    {/* دایره هدف */}
                                    <div className="w-8 h-8 border-2 border-green-500 rounded-full animate-ping" />
                                    <div className="absolute inset-0 w-8 h-8 border-2 border-green-400 rounded-full" />
                                    <div className="absolute inset-2 w-4 h-4 bg-green-500 rounded-full" />
                                    {/* برچسب هدف */}
                                    <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 bg-green-500 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap shadow-lg">
                                      🎯 {inspectorScanBars.intersection.text}
                                    </div>
                                  </div>
                                )}

                                {/* نشانگر درصد اسکن */}
                                <div className="absolute bottom-2 left-2 bg-black/70 text-green-400 text-[10px] px-2 py-1 rounded font-mono">
                                  اسکن: {Math.round(Math.max(inspectorScanBars.verticalX, inspectorScanBars.horizontalY))}%
                                </div>
                              </>
                            )}
                          </div>
                        ) : inspectorPowerOn && inspectorError ? (
                          <div className="h-full flex items-center justify-center p-3">
                            <div className="text-center text-yellow-500">
                              <div className="text-3xl mb-2">⚠️</div>
                              <p className="text-xs">{inspectorError}</p>
                              <button
                                onClick={() => setShowCreateRenderService(true)}
                                className="mt-3 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg text-xs font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-lg"
                              >
                                ➕ ایجاد سرویس Render
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="h-full flex items-center justify-center p-4">
                            <div className="text-center text-gray-500">
                              <div className="text-4xl mb-2">📱</div>
                              <p className="text-sm font-medium">پیش‌نمایش پروژه</p>
                              <p className="text-xs mt-1 text-gray-600">دکمه پاور را بزنید</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* دکمه پاور زیر اسکرین */}
                <button
                  onClick={toggleInspectorPower}
                  disabled={inspectorLoading}
                  className={`mt-4 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 ${
                    inspectorPowerOn
                      ? 'bg-gradient-to-br from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 shadow-green-500/30'
                      : 'bg-gradient-to-br from-gray-600 to-gray-700 hover:from-gray-500 hover:to-gray-600 shadow-gray-500/20'
                  } ${inspectorLoading ? 'opacity-50 cursor-wait' : ''}`}
                  title={inspectorPowerOn ? 'خاموش کردن' : 'روشن کردن'}
                >
                  <svg
                    className={`w-7 h-7 ${inspectorPowerOn ? 'text-white' : 'text-gray-300'}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v9m0 0a7 7 0 100 14 7 7 0 000-14z" />
                  </svg>
                </button>
                <span className={`text-xs mt-1 ${inspectorPowerOn ? 'text-green-600' : 'text-gray-500'}`}>
                  {inspectorLoading ? 'در حال اتصال...' : inspectorPowerOn ? 'روشن' : 'خاموش'}
                </span>

                {/* 🆕 دکمه رصد لاگ‌ها */}
                {inspectorPowerOn && (
                  <button
                    onClick={() => setInspectorActionTracking(prev => ({ ...prev, enabled: !prev.enabled }))}
                    className={`mt-3 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      inspectorActionTracking.enabled
                        ? 'bg-blue-500 text-white hover:bg-blue-600'
                        : 'bg-gray-200 text-gray-600 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300'
                    }`}
                    title={inspectorActionTracking.enabled ? 'غیرفعال کردن رصد لاگ' : 'فعال کردن رصد لاگ'}
                  >
                    {inspectorActionTracking.enabled ? '🔴 رصد فعال' : '⚪ رصد غیرفعال'}
                  </button>
                )}

                {/* 🌉 دکمه Bridge Script - رصد فعالیت داخل iframe */}
                {inspectorPowerOn && (
                  <div className="mt-3 flex flex-col items-center">
                    <button
                      onClick={() => {
                        // اگر خطای عدم اتصال به GitHub داشت، دیالوگ باز شود
                        if (inspectorBridgeStatus.error?.includes('GitHub متصل نیست')) {
                          setShowGitHubPathDialog(true);
                        } else {
                          toggleBridgeScript();
                        }
                      }}
                      disabled={inspectorBridgeStatus.checking || inspectorBridgeStatus.injecting}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        inspectorBridgeStatus.has_bridge
                          ? 'bg-green-500 text-white hover:bg-green-600'
                          : inspectorBridgeStatus.error?.includes('GitHub')
                          ? 'bg-yellow-500 text-white hover:bg-yellow-600'
                          : 'bg-orange-500 text-white hover:bg-orange-600'
                      } ${(inspectorBridgeStatus.checking || inspectorBridgeStatus.injecting) ? 'opacity-50 cursor-wait' : ''}`}
                      title={inspectorBridgeStatus.has_bridge
                        ? 'حذف اسکریپت رصد از پروژه'
                        : inspectorBridgeStatus.error?.includes('GitHub')
                        ? 'اتصال به GitHub'
                        : 'فعال‌سازی رصد کلیک/تایپ داخل پروژه'}
                    >
                      {inspectorBridgeStatus.checking ? (
                        '⏳ بررسی...'
                      ) : inspectorBridgeStatus.injecting ? (
                        '⏳ در حال اعمال...'
                      ) : inspectorBridgeStatus.has_bridge ? (
                        '🌉 Bridge فعال'
                      ) : inspectorBridgeStatus.error?.includes('GitHub') ? (
                        '⚠️ اتصال GitHub'
                      ) : (
                        '🔗 فعال‌سازی Bridge'
                      )}
                    </button>
                    <span className="text-[10px] text-gray-500 mt-1 text-center max-w-[90px]">
                      {inspectorBridgeStatus.has_bridge
                        ? 'رصد کلیک/تایپ فعال'
                        : inspectorBridgeStatus.error?.includes('GitHub')
                        ? 'ابتدا GitHub را وصل کنید'
                        : 'برای رصد کامل فعال کنید'}
                    </span>
                    {inspectorBridgeStatus.error && !inspectorBridgeStatus.error.includes('GitHub') && (
                      <span className="text-[10px] text-red-500 mt-0.5">{inspectorBridgeStatus.error}</span>
                    )}
                    {/* 🌐 وضعیت WebSocket Bridge */}
                    {inspectorPowerOn && (
                      <div className={`mt-1 flex items-center gap-1 text-[10px] ${
                        bridgePeerConnected ? 'text-green-600' : bridgeWsConnected ? 'text-yellow-600' : 'text-gray-400'
                      }`}>
                        <span className={`w-2 h-2 rounded-full ${
                          bridgePeerConnected ? 'bg-green-500 animate-pulse' : bridgeWsConnected ? 'bg-yellow-500' : 'bg-gray-400'
                        }`} />
                        {bridgePeerConnected ? 'WS: متصل' : bridgeWsConnected ? 'WS: منتظر Bridge' : 'WS: در حال اتصال...'}
                      </div>
                    )}
                    {/* ⚠️ هشدار نسخه قدیمی */}
                    {inspectorBridgeStatus.has_bridge && inspectorBridgeStatus.needs_update && (
                      <div className="mt-1 p-1.5 bg-amber-50 border border-amber-200 rounded-lg max-w-[140px]">
                        <div className="text-[10px] text-amber-700 font-medium text-center">
                          ⚠️ نسخه قدیمی (v{inspectorBridgeStatus.version})
                        </div>
                        {inspectorBridgeStatus.update_reasons && inspectorBridgeStatus.update_reasons.length > 0 && (
                          <div className="text-[9px] text-amber-600 mt-0.5 text-center">
                            {inspectorBridgeStatus.update_reasons[0]}
                          </div>
                        )}
                        <button
                          onClick={updateBridgeToLatest}
                          disabled={inspectorBridgeStatus.injecting}
                          className="mt-1 w-full px-2 py-1 text-[10px] bg-amber-500 text-white hover:bg-amber-600 rounded transition-all font-medium"
                        >
                          {inspectorBridgeStatus.injecting ? '⏳ در حال آپدیت...' : `🔄 آپدیت به v${inspectorBridgeStatus.latest_version}`}
                        </button>
                      </div>
                    )}
                    {/* دکمه‌های کمکی */}
                    <div className="flex gap-1 mt-1">
                      {/* دکمه به‌روزرسانی Bridge (re-inject با WebSocket) */}
                      {inspectorBridgeStatus.has_bridge && inspectorPowerOn && !inspectorBridgeStatus.needs_update && (
                        <button
                          onClick={updateBridgeToLatest}
                          disabled={inspectorBridgeStatus.injecting}
                          className="px-2 py-0.5 text-[10px] text-orange-500 hover:text-orange-700 hover:bg-orange-50 rounded transition-all"
                          title="به‌روزرسانی Bridge به آخرین نسخه"
                        >
                          {inspectorBridgeStatus.injecting ? '⏳' : '🔄 به‌روزرسانی'}
                        </button>
                      )}
                      {/* دکمه Debug */}
                      <button
                        onClick={debugBridgeStatus}
                        disabled={bridgeDebugInfo.loading}
                        className="px-2 py-0.5 text-[10px] text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-all"
                        title="بررسی دقیق وضعیت Bridge"
                      >
                        {bridgeDebugInfo.loading ? '⏳' : '🔍 تشخیص'}
                      </button>
                    </div>
                    {/* نمایش نتیجه Debug */}
                    {bridgeDebugInfo.data && (
                      <div className={`mt-1 p-2 rounded text-[10px] ${
                        bridgeDebugInfo.data.deployed_has_bridge
                          ? 'bg-green-100 text-green-700'
                          : bridgeDebugInfo.data.bridge_injected
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        <div className="font-bold">{bridgeDebugInfo.data.diagnosis}</div>
                        {bridgeDebugInfo.data.files_with_bridge && bridgeDebugInfo.data.files_with_bridge.length > 0 && (
                          <div className="mt-1">
                            📁 فایل: {bridgeDebugInfo.data.files_with_bridge[0]?.path}
                          </div>
                        )}
                        {bridgeDebugInfo.data.bridge_injected && !bridgeDebugInfo.data.deployed_has_bridge && (
                          <div className="mt-1 text-yellow-600">
                            💡 Deploy جدید انجام دهید و کمی صبر کنید
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 🔗 دیالوگ تنظیم آدرس GitHub */}
                {showGitHubPathDialog && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowGitHubPathDialog(false)}>
                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
                      <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white">🔗 اتصال به GitHub</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        برای فعال‌سازی Bridge، آدرس ریپوی GitHub پروژه را وارد کنید:
                      </p>
                      <input
                        type="text"
                        value={gitHubPathInput}
                        onChange={(e) => setGitHubPathInput(e.target.value)}
                        placeholder="مثال: username/repo-name"
                        className="w-full px-4 py-2 border rounded-lg mb-4 text-left dir-ltr dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                        dir="ltr"
                      />
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => setShowGitHubPathDialog(false)}
                          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg dark:text-gray-300 dark:hover:bg-gray-700"
                        >
                          انصراف
                        </button>
                        <button
                          onClick={setGitHubPath}
                          disabled={settingGitHubPath || !gitHubPathInput.trim()}
                          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                        >
                          {settingGitHubPath ? '⏳ در حال ذخیره...' : '✓ ذخیره'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 📁 دیالوگ مسیر سفارشی فایل HTML */}
                {showCustomHtmlPathDialog && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCustomHtmlPathDialog(false)}>
                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
                      <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white">📁 مسیر فایل HTML</h3>

                      {/* 🚫 هشدار پروژه Backend-only */}
                      {isBackendOnly && (
                        <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-4 mb-4">
                          <div className="flex items-center gap-2 text-red-800 dark:text-red-300 font-bold text-sm mb-2">
                            🚫 این پروژه فرانت‌اند ندارد (Backend-only)
                          </div>
                          <p className="text-xs text-red-700 dark:text-red-400 mb-2">
                            Bridge Script فقط روی پروژه‌هایی با فایل HTML کار می‌کند.
                            <br />
                            این پروژه فقط Backend/API است و فایل HTML ندارد.
                          </p>
                          <p className="text-xs text-red-600 dark:text-red-300 font-medium">
                            💡 راه‌حل: اگر فرانت‌اند جداگانه دارید، Bridge را روی آن پروژه فعال کنید.
                          </p>
                        </div>
                      )}

                      {/* هشدار فریم‌ورک */}
                      {detectedFramework && !isBackendOnly && (
                        <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded-lg p-3 mb-4">
                          <div className="flex items-center gap-2 text-yellow-800 dark:text-yellow-300 font-bold text-sm mb-1">
                            ⚠️ پروژه {detectedFramework} تشخیص داده شد
                          </div>
                          <p className="text-xs text-yellow-700 dark:text-yellow-400">
                            این فریم‌ورک HTML را در زمان build می‌سازد و فایل HTML ثابت ندارد.
                            <br />
                            برای این پروژه باید اسکریپت را مستقیماً در کد اضافه کنید.
                          </p>
                        </div>
                      )}

                      {/* لیست فایل‌های HTML پیدا شده */}
                      {foundHtmlFiles.length > 0 && (
                        <div className="mb-4">
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                            فایل‌های HTML پیدا شده - روی یکی کلیک کنید:
                          </p>
                          <div className="space-y-1 max-h-40 overflow-y-auto">
                            {foundHtmlFiles.map((file, idx) => (
                              <button
                                key={idx}
                                onClick={() => {
                                  setCustomHtmlPathInput(file);
                                  toggleBridgeScript(file);
                                }}
                                disabled={inspectorBridgeStatus.injecting}
                                className="w-full text-left px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-blue-100 dark:hover:bg-blue-900 rounded-lg text-sm font-mono transition-all disabled:opacity-50"
                                dir="ltr"
                              >
                                📄 {file}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* فرم ورود دستی */}
                      <div className="border-t pt-4 mt-2">
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {foundHtmlFiles.length > 0 ? 'یا مسیر را دستی وارد کنید:' : 'مسیر فایل HTML اصلی پروژه را وارد کنید:'}
                        </p>
                        <input
                          type="text"
                          value={customHtmlPathInput}
                          onChange={(e) => setCustomHtmlPathInput(e.target.value)}
                          placeholder="مثال: frontend/public/index.html"
                          className="w-full px-4 py-2 border rounded-lg mb-3 text-left dir-ltr dark:bg-gray-700 dark:border-gray-600 dark:text-white font-mono text-sm"
                          dir="ltr"
                        />
                        {foundHtmlFiles.length === 0 && !detectedFramework && (
                          <div className="text-xs text-gray-500 mb-3">
                            مثال‌ها:
                            <ul className="list-disc list-inside mt-1 space-y-0.5">
                              <li>frontend/index.html</li>
                              <li>client/public/index.html</li>
                              <li>web/src/index.html</li>
                            </ul>
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2 justify-end mt-4">
                        <button
                          onClick={() => {
                            setShowCustomHtmlPathDialog(false);
                            setFoundHtmlFiles([]);
                            setDetectedFramework(null);
                            setIsBackendOnly(false);
                          }}
                          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg dark:text-gray-300 dark:hover:bg-gray-700"
                        >
                          انصراف
                        </button>
                        <button
                          onClick={() => toggleBridgeScript(customHtmlPathInput.trim())}
                          disabled={inspectorBridgeStatus.injecting || !customHtmlPathInput.trim()}
                          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                        >
                          {inspectorBridgeStatus.injecting ? '⏳ در حال تزریق...' : '✓ تزریق Bridge'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* چت باکس سمت راست (در RTL) - با قابلیت چت با AI */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden relative" style={{ width: '380px', flexShrink: 0 }}>
                {/* هدر چت با انتخاب مدل */}
                <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🤖</span>
                      <div>
                        <h3 className="font-bold text-sm">دستیار بازرس هوشمند</h3>
                        <p className="text-xs opacity-80">
                          {inspectorSelectedModels.length > 0
                            ? `${inspectorSelectedModels.length} مدل انتخاب شده`
                            : 'مدلی انتخاب نشده'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {/* دکمه آرشیو سشن */}
                      {inspectorSessionId && inspectorChatMessages.length > 0 && (
                        <button
                          onClick={archiveInspectorSession}
                          className="p-2 bg-white/20 rounded-lg hover:bg-white/30 transition text-sm"
                          title="بستن و آرشیو این سشن"
                        >
                          📥
                        </button>
                      )}
                      {/* دکمه نمایش آرشیو */}
                      {inspectorArchivedSessions.length > 0 && (
                        <button
                          onClick={() => setShowArchivedSessions(!showArchivedSessions)}
                          className={`p-2 rounded-lg transition text-sm ${showArchivedSessions ? 'bg-white/40' : 'bg-white/20 hover:bg-white/30'}`}
                          title="سشن‌های آرشیو شده"
                        >
                          📋
                        </button>
                      )}
                      <button
                        onClick={() => setInspectorShowModelSelector(!inspectorShowModelSelector)}
                        className="p-2 bg-white/20 rounded-lg hover:bg-white/30 transition text-sm"
                        title="انتخاب مدل‌های AI"
                      >
                        ⚙️
                      </button>
                    </div>
                  </div>

                  {/* انتخابگر مدل */}
                  {inspectorShowModelSelector && (
                    <div className="mt-3 bg-white/10 rounded-lg p-2 max-h-60 overflow-auto">
                      {/* 🆕 چک‌باکس انتخاب خودکار */}
                      <div className="mb-3 pb-2 border-b border-white/20">
                        <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                          <input
                            type="checkbox"
                            checked={inspectorAutoSelect}
                            onChange={(e) => setInspectorAutoSelect(e.target.checked)}
                            className="w-4 h-4 rounded accent-white"
                          />
                          <div>
                            <span className="text-xs font-medium">🎯 انتخاب خودکار مدل</span>
                            <p className="text-[10px] opacity-70">مدل‌ها بر اساس نوع درخواست انتخاب می‌شوند</p>
                          </div>
                        </label>

                        <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded mt-1">
                          <input
                            type="checkbox"
                            checked={inspectorCollaborativeMode}
                            onChange={(e) => setInspectorCollaborativeMode(e.target.checked)}
                            className="w-4 h-4 rounded accent-white"
                          />
                          <div>
                            <span className="text-xs font-medium">🤝 همکاری چند مدل</span>
                            <p className="text-[10px] opacity-70">مدل‌ها از کار همدیگر آگاه هستند</p>
                          </div>
                        </label>

                        <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded mt-1">
                          <input
                            type="checkbox"
                            checked={inspectorSmartPrompt}
                            onChange={(e) => setInspectorSmartPrompt(e.target.checked)}
                            className="w-4 h-4 rounded accent-white"
                          />
                          <div>
                            <span className="text-xs font-medium">🧠 پرامپت ساختارمند</span>
                            <p className="text-[10px] opacity-70">پیام شما قبل از ارسال بهینه‌سازی و ساختارمند می‌شود</p>
                          </div>
                        </label>

                        {/* نشانگر GitHub */}
                        <div className="flex items-center gap-2 mt-2 p-1">
                          <span className={`w-2 h-2 rounded-full ${inspectorGithubConnected ? 'bg-green-400' : 'bg-gray-400'}`}></span>
                          <span className="text-[10px] opacity-70">
                            {inspectorGithubConnected ? '✓ متصل به GitHub' : 'GitHub غیرمتصل'}
                          </span>
                        </div>
                      </div>

                      {/* 🔧 فیلتر انواع اکشن‌ها */}
                      <div className="mb-3 pb-2 border-b border-white/20">
                        <p className="text-xs mb-2 opacity-80 font-medium">🎛️ فیلتر اکشن‌ها در چت:</p>
                        <div className="grid grid-cols-2 gap-1">
                          {Object.entries({
                            'click': 'کلیک',
                            'scroll': 'اسکرول',
                            'input': 'تایپ',
                            'focus': 'فوکوس',
                            'hover': 'هاور',
                            'error': 'خطای JS',
                            'console-error': 'console.error',
                            'error-overlay': 'لایه خطا',
                          }).map(([key, label]) => (
                            <label key={key} className="flex items-center gap-1.5 cursor-pointer hover:bg-white/10 px-1 py-0.5 rounded text-[11px]">
                              <input
                                type="checkbox"
                                checked={inspectorActionFilters[key] !== false}
                                onChange={(e) => setInspectorActionFilters(prev => ({ ...prev, [key]: e.target.checked }))}
                                className="w-3.5 h-3.5 rounded accent-white"
                              />
                              <span className={inspectorActionFilters[key] !== false ? 'opacity-100' : 'opacity-50'}>{label}</span>
                            </label>
                          ))}
                        </div>
                        <button
                          onClick={() => setInspectorActionFilters({
                            'click': true, 'scroll': false, 'input': true, 'focus': true,
                            'hover': true, 'error': true, 'console-error': true, 'error-overlay': true,
                          })}
                          className="text-[10px] mt-1 opacity-60 hover:opacity-100 underline"
                        >
                          بازنشانی پیش‌فرض
                        </button>
                      </div>

                      {/* انتخاب دستی مدل‌ها */}
                      {!inspectorAutoSelect && (
                        <>
                          <p className="text-xs mb-2 opacity-80">مدل‌های موجود (کلیک برای انتخاب):</p>
                          <div className="flex flex-wrap gap-1">
                            {inspectorModels.map(model => (
                              <button
                                key={model.id}
                                onClick={() => toggleInspectorModel(model.id)}
                                className={`text-xs px-2 py-1 rounded-full transition ${
                                  inspectorSelectedModels.includes(model.id)
                                    ? 'bg-white text-red-500 font-bold'
                                    : model.enabled
                                      ? 'bg-white/20 hover:bg-white/30'
                                      : 'bg-white/10 opacity-50'
                                }`}
                                disabled={!model.enabled}
                              >
                                {model.name}
                              </button>
                            ))}
                          </div>
                        </>
                      )}

                      {inspectorAutoSelect && (
                        <p className="text-xs opacity-60 text-center py-2">
                          ✨ مدل‌ها خودکار انتخاب می‌شوند
                        </p>
                      )}

                      {inspectorModels.length === 0 && (
                        <p className="text-xs opacity-60">دکمه پاور را بزنید تا مدل‌ها لود شوند</p>
                      )}
                    </div>
                  )}
                </div>

                {/* پنل سشن‌های آرشیو شده */}
                {showArchivedSessions && (
                  <div className="bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-2 max-h-40 overflow-auto">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-gray-600 dark:text-gray-400">سشن‌های قبلی</span>
                      <button onClick={() => setShowArchivedSessions(false)} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
                    </div>
                    {inspectorArchivedSessions.map(s => (
                      <button
                        key={s.id}
                        onClick={() => { loadArchivedSession(s.id); setShowArchivedSessions(false); }}
                        className="w-full text-right px-2 py-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition text-xs flex items-center justify-between"
                      >
                        <span className="text-gray-600 dark:text-gray-400">{s.title || `سشن #${s.id}`}</span>
                        <span className="text-gray-400 text-[10px]">{s.message_count} پیام</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* محتوای چت */}
                <div className="flex-1 p-3 overflow-auto bg-gray-50 dark:bg-gray-900 space-y-3" style={{ maxHeight: '400px' }}>
                  {/* پیام خوش‌آمد */}
                  {inspectorChatMessages.length === 0 && (
                    <>
                      <div className="flex gap-2">
                        <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center text-white text-sm flex-shrink-0">
                          🔍
                        </div>
                        <div className="bg-white dark:bg-gray-800 rounded-lg rounded-tl-none p-3 shadow-sm max-w-[85%]">
                          <p className="text-sm text-gray-700 dark:text-gray-300">
                            سلام! من بازرس هوشمند هستم. به تمام داده‌های پروژه دسترسی دارم:
                          </p>
                          <ul className="text-xs text-gray-500 mt-2 space-y-1">
                            <li>• لاگ‌های بک‌اند (زنده)</li>
                            <li>• پیش‌نمایش فرانت‌اند</li>
                            <li>• فایل‌های پروژه</li>
                          </ul>
                        </div>
                      </div>

                      {/* دکمه‌های سریع */}
                      <div className="flex flex-wrap gap-1 px-2">
                        <button
                          onClick={() => { setInspectorChatInput('لاگ‌های خطا را تحلیل کن'); }}
                          className="text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 px-2 py-1 rounded-full hover:bg-red-200 transition"
                        >
                          تحلیل خطاها
                        </button>
                        <button
                          onClick={() => { setInspectorChatInput('امنیت پروژه را بررسی کن'); }}
                          className="text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 px-2 py-1 rounded-full hover:bg-orange-200 transition"
                        >
                          بررسی امنیت
                        </button>
                        <button
                          onClick={() => { setInspectorChatInput('باگ‌های احتمالی را پیدا کن'); }}
                          className="text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 px-2 py-1 rounded-full hover:bg-yellow-200 transition"
                        >
                          یافتن باگ
                        </button>
                      </div>
                    </>
                  )}

                  {/* نمایش خطاهای لاگ */}
                  {inspectorPowerOn && inspectorBackendLogs.filter(l => l.level === 'error').length > 0 && inspectorChatMessages.length === 0 && (
                    <div className="flex gap-2">
                      <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-white text-sm flex-shrink-0">
                        ⚠️
                      </div>
                      <div className="bg-red-50 dark:bg-red-900/30 rounded-lg rounded-tl-none p-3 shadow-sm max-w-[85%] border border-red-200 dark:border-red-800">
                        <p className="text-sm text-red-700 dark:text-red-300 font-medium mb-1">
                          {inspectorBackendLogs.filter(l => l.level === 'error').length} خطا شناسایی شد!
                        </p>
                        <div className="text-xs text-red-600 dark:text-red-400 space-y-1 max-h-20 overflow-auto">
                          {inspectorBackendLogs.filter(l => l.level === 'error').slice(0, 3).map(log => (
                            <div key={log.id} className="truncate">• {log.message?.slice(0, 60)}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 🛡️ Live Indicator (chips) — وضعیت زندهٔ Inspector */}
                  {inspectorPowerOn && (
                    <div className="flex flex-wrap gap-1.5 items-center px-2 py-1.5 mb-2 bg-gray-50 dark:bg-gray-800/50 rounded border border-gray-200 dark:border-gray-700 text-[11px]">
                      {/* وضعیت WebSocket */}
                      <span
                        className={`px-2 py-0.5 rounded-full font-medium ${
                          bridgeWsConnected && bridgePeerConnected
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                            : bridgeWsConnected
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                            : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                        }`}
                        title={
                          bridgeWsConnected && bridgePeerConnected
                            ? 'WebSocket فعال و bridge داخل پروژه متصل است'
                            : bridgeWsConnected
                            ? 'WebSocket فعال است ولی bridge هنوز متصل نشده — منتظر می‌مانیم'
                            : 'WebSocket قطع — تلاش برای اتصال مجدد در جریان است'
                        }
                      >
                        ●{' '}
                        {bridgeWsConnected && bridgePeerConnected
                          ? 'WS متصل'
                          : bridgeWsConnected
                          ? 'منتظر bridge'
                          : 'WS قطع'}
                      </span>
                      {/* Verify pending */}
                      <span
                        className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                        title="تعداد عملیات verify که هنوز پاسخ نهایی نگرفته‌اند (با backoff تلاش می‌کنند)"
                      >
                        ⏳ verify pending: {inspectorVerifyPendingCount}
                      </span>
                      {/* Duplicates dropped */}
                      <span
                        className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                        title="رویدادهای تکراری که از هر دو کانال (postMessage و WebSocket) رسیده و dedup شده‌اند"
                      >
                        🔁 duplicate dropped: {inspectorDuplicatesDroppedCount}
                      </span>
                      {/* Console logs dropped */}
                      <span
                        className="px-2 py-0.5 rounded-full bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300"
                        title={`لاگ‌های کنسولی که به دلیل سقف (${consoleLogCap}) از ابتدای buffer حذف شده‌اند`}
                      >
                        📉 logs dropped: {consoleLogDroppedCount}
                      </span>
                      {/* Network filter status */}
                      <span
                        className={`px-2 py-0.5 rounded-full ${
                          inspectorActionFilters['network-response'] || inspectorActionFilters['network-error']
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                        }`}
                        title="نمایش/مخفی‌سازی درخواست‌های شبکه (fetch + XHR) — کلیک کن تا toggle شود"
                        onClick={() => {
                          // toggle همه‌ی network filterها با هم
                          const newVal = !(inspectorActionFilters['network-response'] || inspectorActionFilters['network-error']);
                          setInspectorActionFilters(prev => ({
                            ...prev,
                            'network-request': newVal && prev['network-request'],
                            'network-response': newVal,
                            'network-error': newVal,
                          }));
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        🌐 network: {inspectorActionFilters['network-response'] || inspectorActionFilters['network-error'] ? 'ON' : 'OFF'}
                      </span>
                      {/* Restore status / Reload / Clear */}
                      {inspectorChatRestoring && (
                        <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300" title="در حال بارگذاری تاریخچه از DB">
                          ⏳ بارگذاری چت...
                        </span>
                      )}
                      {inspectorRestoreError && (
                        <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" title={`خطای بارگذاری: ${inspectorRestoreError}`}>
                          ⚠️ restore failed
                        </span>
                      )}
                      <div className="ml-auto flex gap-1 flex-wrap">
                        <button
                          onClick={exportInspectorTimelineJSON}
                          disabled={inspectorChatMessages.length === 0}
                          className="px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition disabled:opacity-50"
                          title="دانلود کامل timeline به‌صورت JSON (شامل network_meta و verification metadata)"
                        >
                          📥 JSON
                        </button>
                        <button
                          onClick={exportInspectorTimelineMarkdown}
                          disabled={inspectorChatMessages.length === 0}
                          className="px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 transition disabled:opacity-50"
                          title="دانلود timeline به‌صورت Markdown با headerهای زمانی"
                        >
                          📝 Markdown
                        </button>
                        <button
                          onClick={openSendToOversightModal}
                          disabled={inspectorChatMessages.length === 0}
                          className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 transition disabled:opacity-50"
                          title="ساخت یک تسک جدید در سیستم نظارت با خلاصهٔ این timeline"
                        >
                          🔗 Oversight
                        </button>
                        <button
                          onClick={reloadInspectorChatFromDb}
                          disabled={inspectorChatRestoring}
                          className="px-2 py-0.5 rounded bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-500 transition disabled:opacity-50"
                          title="پاک کردن state و بارگذاری مجدد از DB"
                        >
                          🔁 Reload
                        </button>
                        <button
                          onClick={clearInspectorChatLocally}
                          className="px-2 py-0.5 rounded bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200 hover:bg-red-100 hover:text-red-700 dark:hover:bg-red-900/30 dark:hover:text-red-300 transition"
                          title="فقط state فرانت پاک می‌شود — DB دست‌نخورده می‌ماند"
                        >
                          🧹 Clear
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 🔗 Send to Oversight Modal */}
                  {showSendToOversightModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => !sendOversightSubmitting && setShowSendToOversightModal(false)}>
                      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-5 max-w-lg w-full mx-4 border border-gray-200 dark:border-gray-700" onClick={e => e.stopPropagation()}>
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                          🔗 ارسال timeline به سیستم نظارت
                        </h3>
                        <div className="space-y-3">
                          <div>
                            <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">پروژهٔ تحت نظارت (watched)</label>
                            {oversightWatchedList.length === 0 ? (
                              <div className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 p-2 rounded">
                                هیچ پروژه‌ای در سیستم نظارت ثبت نشده — ابتدا از صفحهٔ /oversight یک پروژه به watched list اضافه کنید
                              </div>
                            ) : (
                              <select
                                value={sendOversightForm.watched_id}
                                onChange={e => setSendOversightForm(f => ({ ...f, watched_id: e.target.value }))}
                                className="w-full text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-2 py-1.5"
                              >
                                {oversightWatchedList.map(w => (
                                  <option key={w.id} value={w.id}>{w.repo_full_name}</option>
                                ))}
                              </select>
                            )}
                          </div>
                          <div>
                            <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">عنوان تسک</label>
                            <input
                              type="text"
                              value={sendOversightForm.title}
                              onChange={e => setSendOversightForm(f => ({ ...f, title: e.target.value }))}
                              className="w-full text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-2 py-1.5"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">نوع</label>
                              <select
                                value={sendOversightForm.type}
                                onChange={e => setSendOversightForm(f => ({ ...f, type: e.target.value }))}
                                className="w-full text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-2 py-1.5"
                              >
                                <option value="bug">bug</option>
                                <option value="feature_request">feature_request</option>
                                <option value="refactor">refactor</option>
                                <option value="security">security</option>
                                <option value="docs">docs</option>
                                <option value="other">other</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">اولویت</label>
                              <select
                                value={sendOversightForm.priority}
                                onChange={e => setSendOversightForm(f => ({ ...f, priority: e.target.value }))}
                                className="w-full text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-2 py-1.5"
                              >
                                <option value="low">low</option>
                                <option value="medium">medium</option>
                                <option value="high">high</option>
                                <option value="critical">critical</option>
                              </select>
                            </div>
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 p-2 rounded border border-gray-200 dark:border-gray-700">
                            خلاصهٔ {inspectorChatMessages.length} پیام (شامل خطاها، اکشن‌ها، network requests) به‌عنوان prompt در تسک قرار می‌گیرد. می‌توانید بعداً در صفحهٔ /oversight ویرایش کنید.
                          </div>
                        </div>
                        <div className="flex gap-2 justify-end mt-4">
                          <button
                            onClick={() => setShowSendToOversightModal(false)}
                            disabled={sendOversightSubmitting}
                            className="px-3 py-1.5 text-sm rounded bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-500 disabled:opacity-50"
                          >
                            انصراف
                          </button>
                          <button
                            onClick={submitSendToOversight}
                            disabled={sendOversightSubmitting || oversightWatchedList.length === 0 || !sendOversightForm.watched_id}
                            className="px-3 py-1.5 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                          >
                            {sendOversightSubmitting ? '⏳ در حال ارسال...' : '🚀 ارسال به نظارت'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* پیام‌های چت */}
                  {inspectorChatMessages.map(msg => (
                    <div key={msg.id} className={`group flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0 ${
                        msg.role === 'user' ? 'bg-blue-500' :
                        msg.role === 'action' && msg.verified_by_model === 'console-error' ? 'bg-orange-500' :
                        msg.role === 'action' && msg.backend_verified === false ? 'bg-red-500' :
                        msg.role === 'action' && (msg.action_type === 'error' || msg.action_type === 'console-error') && msg.backend_verified === null ? 'bg-red-500' :
                        msg.role === 'action' ? 'bg-emerald-500' :
                        'bg-red-500'
                      }`}>
                        {msg.role === 'user' ? '👤' :
                         msg.role === 'action' && msg.verified_by_model === 'console-error' ? '🖥️' :
                         msg.role === 'action' && msg.backend_verified === false ? '⚠️' :
                         msg.role === 'action' && (msg.action_type === 'error' || msg.action_type === 'console-error') && msg.backend_verified === null ? '⚠️' :
                         msg.role === 'action' ? '👆' :
                         '🤖'}
                      </div>
                      <div
                        className={`rounded-lg p-2.5 shadow-sm max-w-[85%] cursor-pointer transition-all ${
                          msg.role === 'user'
                            ? 'bg-blue-500 text-white rounded-tr-none'
                            : msg.role === 'action' && msg.verified_by_model === 'console-error'
                              ? 'bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-tl-none hover:border-orange-400'
                            : msg.role === 'action' && msg.backend_verified === false
                              ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-tl-none hover:border-red-400'
                            : msg.role === 'action' && (msg.action_type === 'error' || msg.action_type === 'console-error') && msg.backend_verified === null
                              ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-tl-none hover:border-red-400'
                            : msg.role === 'action'
                              ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-tl-none hover:border-emerald-400'
                              : 'bg-white dark:bg-gray-800 rounded-tl-none hover:bg-gray-50 dark:hover:bg-gray-750'
                        } ${inspectorMsgInfoId === msg.id ? 'ring-2 ring-blue-300' : ''}`}
                        onClick={() => setInspectorMsgInfoId(inspectorMsgInfoId === msg.id ? null : msg.id)}
                      >
                        {/* نمایش پیام ریپلای‌شده */}
                        {(msg as any).reply_to_content && (
                          <div className={`text-[10px] mb-1 px-2 py-1 rounded border-r-2 ${
                            msg.role === 'user'
                              ? 'bg-blue-400/30 border-white/50 text-white/80'
                              : 'bg-gray-100 dark:bg-gray-700/50 border-gray-400 text-gray-500 dark:text-gray-400'
                          }`}>
                            ↩️ {(msg as any).reply_to_content}...
                          </div>
                        )}
                        {/* 🧠 نشانگر ساختارمندسازی + نمایش پیام اصلی */}
                        {msg.role === 'user' && (msg as any).original_prompt && (
                          <div className="mb-1">
                            <span className="inline-block text-[9px] bg-green-400/30 text-green-100 px-1.5 py-0.5 rounded-full mb-1">🧠 ساختارمند شده</span>
                            <details className="text-[10px]">
                              <summary className="cursor-pointer text-blue-200 hover:text-white">📝 پیام اصلی</summary>
                              <div className="mt-1 p-1.5 bg-blue-400/20 rounded text-[10px] text-blue-100 whitespace-pre-wrap max-h-32 overflow-auto">
                                {(msg as any).original_prompt}
                              </div>
                            </details>
                          </div>
                        )}
                        {msg.model_id && msg.role === 'assistant' && (
                          <p className="text-xs text-gray-400 mb-1">{msg.model_id}</p>
                        )}
                        {(msg as any).is_visual_debug_report && (
                          <div className="text-[10px] text-purple-500 dark:text-purple-400 mb-1 flex items-center gap-1">
                            <span>📸</span>
                            <span>گزارش دیباگ بصری</span>
                          </div>
                        )}
                        {(msg as any).is_reanalysis_report && (
                          <div className="text-[10px] text-blue-500 dark:text-blue-400 mb-1 flex items-center gap-1">
                            <span>🔄</span>
                            <span>بازتحلیل مستقل (گزارش اولیه: {(msg as any).vision_model})</span>
                          </div>
                        )}
                        {(msg as any).is_multi_step_report && (
                          <div className="text-[10px] text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500 mb-1 flex items-center gap-1 font-bold">
                            <span>📊</span>
                            <span>گزارش نهایی اجرای مرحله‌ای</span>
                          </div>
                        )}
                        {(msg as any)._is_multi_step_part && (
                          <div className="text-[9px] text-gray-400 dark:text-gray-500 mb-0.5">
                            📎 بخشی از اجرای مرحله‌ای
                          </div>
                        )}
                        <p className={`text-sm whitespace-pre-wrap ${
                          msg.role === 'user' ? '' :
                          msg.role === 'action' && msg.verified_by_model === 'console-error' ? 'text-orange-800 dark:text-orange-200' :
                          msg.role === 'action' && msg.backend_verified === false ? 'text-red-800 dark:text-red-200' :
                          msg.role === 'action' && (msg.action_type === 'error' || msg.action_type === 'console-error') && msg.backend_verified === null ? 'text-red-800 dark:text-red-200' :
                          msg.role === 'action' ? 'text-emerald-800 dark:text-emerald-200' :
                          'text-gray-700 dark:text-gray-300'
                        }`}>
                          {msg.content}
                        </p>
                        {/* 📦 نمایش پک‌های دیباگ بصری */}
                        {(msg as any).visual_debug_packs && (msg as any).visual_debug_packs.length > 0 && (
                          <div className="mt-2 space-y-2">
                            {(msg as any).visual_debug_packs.map((pack: any, pIdx: number) => (
                              <div key={pIdx} className="rounded-lg border border-purple-200 dark:border-purple-800 bg-purple-50/50 dark:bg-purple-900/10 overflow-hidden">
                                {/* Header + Image */}
                                <div className="flex items-start gap-2 p-2">
                                  <img
                                    src={`data:image/png;base64,${pack.base64}`}
                                    alt={`عکس ${pack.index}`}
                                    className="h-20 w-auto rounded border border-purple-300 dark:border-purple-700 cursor-pointer hover:ring-2 hover:ring-purple-400 transition-all flex-shrink-0"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      const win = window.open();
                                      if (win) { win.document.write(`<img src="data:image/png;base64,${pack.base64}" style="max-width:100%">`); }
                                    }}
                                  />
                                  <div className="flex-1 min-w-0 text-[10px]">
                                    <div className="font-bold text-purple-700 dark:text-purple-300 mb-1">📸 عکس {pack.index}</div>
                                    {pack.pageUrl && <div className="text-purple-500 dark:text-purple-400 truncate">🔗 {pack.pageUrl}</div>}
                                    <div className="flex flex-wrap gap-1.5 mt-1">
                                      {pack.consoleLogsCount > 0 && (
                                        <span className={`px-1 py-0.5 rounded ${pack.errorCount > 0 ? 'bg-red-100 dark:bg-red-900/30 text-red-600' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}>
                                          📋 {pack.consoleLogsCount} لاگ کنسول
                                          {pack.errorCount > 0 && ` (${pack.errorCount} خطا)`}
                                        </span>
                                      )}
                                      {pack.backendLogsCount > 0 && (
                                        <span className="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
                                          🖥️ {pack.backendLogsCount} لاگ بکند
                                        </span>
                                      )}
                                      {pack.relatedUrls && pack.relatedUrls.length > 0 && (
                                        <span className="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
                                          🔗 {pack.relatedUrls.length} آدرس
                                        </span>
                                      )}
                                      {pack.apiPaths && pack.apiPaths.length > 0 && (
                                        <span className="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                                          🛤️ {pack.apiPaths.length} مسیر API
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                {/* Expandable details */}
                                {(pack.consoleLogs?.length > 0 || pack.backendLogs?.length > 0 || pack.relatedUrls?.length > 0 || pack.apiPaths?.length > 0) && (
                                  <details className="text-[10px]">
                                    <summary className="px-2 py-1 cursor-pointer text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/20 border-t border-purple-200 dark:border-purple-800">
                                      جزئیات لاگ‌ها و آدرس‌ها
                                    </summary>
                                    <div className="px-2 pb-2 space-y-1.5 max-h-32 overflow-auto">
                                      {pack.consoleLogs?.length > 0 && (
                                        <div>
                                          <div className="font-bold text-gray-600 dark:text-gray-400 mb-0.5">📋 لاگ‌های کنسول:</div>
                                          {pack.consoleLogs.slice(0, 10).map((log: any, li: number) => (
                                            <div key={li} className={`truncate ${log.level === 'error' ? 'text-red-600 dark:text-red-400' : log.level === 'warn' ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-500 dark:text-gray-400'}`}>
                                              [{log.level?.toUpperCase()}] {log.message?.slice(0, 100)}
                                            </div>
                                          ))}
                                          {pack.consoleLogs.length > 10 && <div className="text-gray-400">... و {pack.consoleLogs.length - 10} لاگ دیگر</div>}
                                        </div>
                                      )}
                                      {pack.backendLogs?.length > 0 && (
                                        <div>
                                          <div className="font-bold text-gray-600 dark:text-gray-400 mb-0.5">🖥️ لاگ‌های بکند:</div>
                                          {pack.backendLogs.slice(0, 10).map((log: any, li: number) => (
                                            <div key={li} className={`truncate ${log.level === 'error' ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>
                                              [{log.level?.toUpperCase()}] {log.message?.slice(0, 100)}
                                            </div>
                                          ))}
                                          {pack.backendLogs.length > 10 && <div className="text-gray-400">... و {pack.backendLogs.length - 10} لاگ دیگر</div>}
                                        </div>
                                      )}
                                      {pack.relatedUrls?.length > 0 && (
                                        <div>
                                          <div className="font-bold text-gray-600 dark:text-gray-400 mb-0.5">🔗 آدرس‌ها:</div>
                                          {pack.relatedUrls.map((url: string, ui: number) => (
                                            <div key={ui} className="text-blue-500 dark:text-blue-400 truncate">{url}</div>
                                          ))}
                                        </div>
                                      )}
                                      {pack.apiPaths?.length > 0 && (
                                        <div>
                                          <div className="font-bold text-gray-600 dark:text-gray-400 mb-0.5">🛤️ مسیرهای API بکند:</div>
                                          {pack.apiPaths.map((p: string, pi: number) => (
                                            <div key={pi} className="text-indigo-500 dark:text-indigo-400 truncate font-mono">{p}</div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </details>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs ${
                            msg.role === 'user' ? 'opacity-70' :
                            msg.role === 'action' ? 'text-emerald-500' :
                            'text-gray-400'
                          }`}>
                            {msg.timestamp.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          {msg.tokens_used && (
                            <span className="text-xs text-gray-400">({msg.tokens_used} توکن)</span>
                          )}
                          {/* تیک تأیید بک‌اند */}
                          {msg.role === 'action' && (
                            <span className={`text-xs font-bold ${
                              msg.backend_verified === true && msg.logs_checked && msg.logs_checked > 0 ? 'text-blue-500' :
                              msg.backend_verified === false ? 'text-red-500' :
                              'text-gray-400'
                            }`} title={
                              msg.backend_verified === true && msg.logs_checked && msg.logs_checked > 0 ? `تأیید شده - ${msg.logs_checked} لاگ بررسی شد` :
                              msg.backend_verified === true ? 'تأیید شده' :
                              msg.backend_verified === false ? 'خطا در لاگ‌ها' :
                              msg.logs_checked === 0 && msg.verified_by_model === 'no-logs' ? 'بدون لاگ - در حال تلاش مجدد' :
                              'در حال بررسی...'
                            }>
                              {msg.backend_verified === true && msg.logs_checked && msg.logs_checked > 0 ? '✓✓' :
                               msg.backend_verified === false ? '✕' :
                               '✓'}
                            </span>
                          )}
                          {/* دکمه بررسی خطا + چک‌باکس انتخاب چندتایی */}
                          {msg.role === 'action' && msg.backend_verified === false && (
                            <>
                              {errorMultiSelectMode && (
                                <input
                                  type="checkbox"
                                  checked={selectedErrorIds.includes(msg.id)}
                                  onChange={(e) => {
                                    e.stopPropagation();
                                    if (e.target.checked) {
                                      setSelectedErrorIds(prev => [...prev, msg.id]);
                                    } else {
                                      setSelectedErrorIds(prev => prev.filter(id => id !== msg.id));
                                    }
                                  }}
                                  className="w-3.5 h-3.5 rounded border-red-300 text-red-500 focus:ring-red-400 cursor-pointer"
                                  title="انتخاب برای بررسی کلی"
                                />
                              )}
                              <button
                                onClick={(e) => { e.stopPropagation(); openInvestigateModal(msg.id); }}
                                className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${
                                  msg.verified_by_model === 'console-error'
                                    ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 hover:bg-orange-200 dark:hover:bg-orange-800/40'
                                    : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800/40'
                                }`}
                                disabled={investigateLoading}
                              >
                                {investigateLoading ? '...' : msg.verified_by_model === 'console-error' ? '🖥️ بررسی' : '🔍 بررسی'}
                              </button>
                            </>
                          )}
                          {/* دکمه اصلاح روی گزارش بررسی */}
                          {(msg as any).action_type === 'investigate_report' && investigateReport && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setFixModalOpen(true); }}
                              className="text-[10px] bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded hover:bg-blue-200 dark:hover:bg-blue-800/40 transition-colors"
                              disabled={fixLoading}
                            >
                              {fixLoading ? '...' : '🔧 اصلاح'}
                            </button>
                          )}
                          {/* 🧠 دکمه اعمال تغییرات روی پاسخ‌های smart-chat */}
                          {(msg as any).action_type === 'smart_action' && (msg as any).action_plan?.files?.length > 0 && !(msg as any)._is_multi_step_part && (
                            (msg as any).is_multi_step_report ? (
                              <div className="flex gap-1.5">
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleApplyWithModelSelection(msg.id); }}
                                  className="text-[11px] bg-gradient-to-r from-blue-500 to-purple-500 text-white px-3 py-1 rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all font-bold shadow-md"
                                  disabled={inspectorOpLock}
                                >
                                  {inspectorOpLock ? '⏳ ...' : `🚀 اعمال تمام تغییرات (${(msg as any).action_plan?.files?.length} فایل)`}
                                </button>
                              </div>
                            ) : (msg as any).is_visual_debug_report ? (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleApplyWithModelSelection(msg.id); }}
                                className="text-[10px] bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-2 py-0.5 rounded hover:bg-purple-200 dark:hover:bg-purple-800/40 transition-colors font-medium"
                                disabled={inspectorOpLock}
                              >
                                {inspectorOpLock ? '⏳ ...' : '🔄 اعمال تغییرات (انتخاب مدل)'}
                              </button>
                            ) : (
                              <button
                                onClick={(e) => { e.stopPropagation(); applySmartAction(msg.id); }}
                                className="text-[10px] bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-0.5 rounded hover:bg-green-200 dark:hover:bg-green-800/40 transition-colors font-medium"
                                disabled={inspectorOpLock}
                              >
                                {inspectorOpLock ? '⏳ ...' : '✅ اعمال تغییرات'}
                              </button>
                            )
                          )}
                          {(msg as any).action_type === 'smart_action' && (msg as any).action_plan?.files?.length > 0 && (msg as any).files_were_read === false && (
                            <span className="text-[9px] text-red-500 dark:text-red-400 px-1">
                              🚫 فایل‌ها خوانده نشدند - ممکنه محتوا حدسی باشه
                            </span>
                          )}
                          {/* نشانگر modify_sections — فایل‌هایی که بصورت بخشی تغییر میکنن */}
                          {(msg as any).action_plan?.files?.some((f: any) => f.operation === 'modify_sections') && (
                            <div className="w-full mt-1 p-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700 rounded text-[10px]">
                              <span className="font-bold text-blue-700 dark:text-blue-300">🔧 تغییرات بخشی (modify_sections):</span>
                              <ul className="mt-0.5 space-y-0.5 text-blue-600 dark:text-blue-400">
                                {(msg as any).action_plan.files.filter((f: any) => f.operation === 'modify_sections').map((f: any, i: number) => (
                                  <li key={i} className="pr-2">
                                    <code className="text-[9px]">{f.path}</code>: {f.sections?.length || 0} بخش تغییر
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {/* فایل‌های حذف‌شده به خاطر خطای بحرانی سینتکس */}
                          {(msg as any).action_plan?._rejected_files?.length > 0 && (
                            <div className="w-full mt-1 p-1.5 bg-red-50 dark:bg-red-900/20 border border-red-400 dark:border-red-700 rounded text-[10px]">
                              <span className="font-bold text-red-700 dark:text-red-300">🚫 {(msg as any).action_plan._rejected_files.length} فایل به خاطر خطای سینتکس بحرانی حذف شدند:</span>
                              <ul className="mt-0.5 space-y-0.5 text-red-600 dark:text-red-400">
                                {(msg as any).action_plan._rejected_files.map((rf: any, i: number) => (
                                  <li key={i} className="pr-2">
                                    <code className="text-[9px]">{rf.path}</code>: {rf.reasons?.[0] || 'خطای سینتکس'}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {/* هشدارهای سینتکس action_plan */}
                          {(msg as any).action_plan?._syntax_warnings?.length > 0 && (
                            <div className="w-full mt-1 p-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded text-[10px]">
                              <span className="font-bold text-amber-700 dark:text-amber-300">⚠️ هشدار سینتکس ({(msg as any).action_plan._syntax_warnings.length}):</span>
                              <ul className="mt-0.5 space-y-0.5 text-amber-600 dark:text-amber-400">
                                {(msg as any).action_plan._syntax_warnings.slice(0, 5).map((w: string, i: number) => (
                                  <li key={i} className="pr-2">{w}</li>
                                ))}
                                {(msg as any).action_plan._syntax_warnings.length > 5 && (
                                  <li className="text-amber-500">و {(msg as any).action_plan._syntax_warnings.length - 5} هشدار دیگر...</li>
                                )}
                              </ul>
                            </div>
                          )}
                          {/* نشانگر has_action بدون action_plan معتبر - دکمه درخواست مجدد اصلاح (مستقیم — بدون ساختارمند مجدد) */}
                          {(msg as any).action_type === 'smart_action' && (!(msg as any).action_plan || !(msg as any).action_plan?.files?.length) && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                // 🔑 مستقیم ارسال با _isRetry=true — بدون enhance مجدد (جلوگیری از حلقه تکرار)
                                const retryMsg = (msg as any).original_user_description
                                  || (msg as any).original_prompt
                                  || (msg as any).original_message
                                  || '';
                                const fixPrompt = retryMsg
                                  ? `لطفاً دوباره بررسی کن و حتماً action_plan با فرمت JSON و فیلد "files" و کد کامل فایل‌ها ارائه بده:\n${retryMsg}`
                                  : `لطفاً مشکل قبلی را دوباره بررسی کن و حتماً action_plan با فرمت JSON و فیلد "files" و کد کامل فایل‌ها ارائه بده.\n\nپاسخ قبلی شما:\n${msg.content?.slice(0, 500)}`;
                                setInspectorReplyTo({ id: msg.id, content: msg.content, role: msg.role, model_id: msg.model_id });
                                sendInspectorChat(fixPrompt, true);
                              }}
                              className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 px-1.5 py-0.5 rounded hover:bg-amber-200 dark:hover:bg-amber-800/40 transition-colors"
                              disabled={inspectorOpLock}
                            >
                              🔄 درخواست مجدد اصلاح
                            </button>
                          )}
                          {/* دکمه ریپلای */}
                          <button
                            onClick={(e) => { e.stopPropagation(); setInspectorReplyTo({ id: msg.id, content: msg.content, role: msg.role, model_id: msg.model_id }); }}
                            className={`text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ${
                              msg.role === 'user' ? 'text-white/60 hover:text-white' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                            }`}
                            title="ریپلای"
                          >
                            ↩️
                          </button>
                          {/* دکمه info */}
                          <button
                            onClick={(e) => { e.stopPropagation(); setInspectorMsgInfoId(inspectorMsgInfoId === msg.id ? null : msg.id); }}
                            className={`text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ${
                              msg.role === 'user' ? 'text-white/60 hover:text-white' : 'text-gray-400 hover:text-gray-600'
                            }`}
                            style={{ opacity: inspectorMsgInfoId === msg.id ? 1 : undefined }}
                          >
                            i
                          </button>
                        </div>

                        {/* پنل جزئیات (مثل info در پیام‌رسان‌ها) */}
                        {inspectorMsgInfoId === msg.id && (
                          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs space-y-1.5" dir="rtl">
                            {/* نوع پیام */}
                            <div className="flex items-center justify-between">
                              <span className="text-gray-500">نوع:</span>
                              <span className={`font-medium ${
                                msg.role === 'action' ? 'text-emerald-600' :
                                msg.role === 'assistant' ? 'text-red-500' :
                                msg.role === 'user' ? 'text-blue-500' : 'text-gray-600'
                              }`}>
                                {msg.role === 'action' ? `اکشن (${msg.action_type || 'نامشخص'})` :
                                 msg.role === 'assistant' ? 'پاسخ AI' :
                                 msg.role === 'user' ? 'پیام کاربر' : 'سیستم'}
                              </span>
                            </div>

                            {/* مدل AI (برای پاسخ‌های assistant) */}
                            {msg.model_id && (
                              <div className="flex items-center justify-between">
                                <span className="text-gray-500">مدل پاسخ‌دهنده:</span>
                                <span className="font-mono text-[11px] bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">{msg.model_id}</span>
                              </div>
                            )}

                            {/* اطلاعات تأیید بک‌اند (برای action) */}
                            {msg.role === 'action' && (
                              <>
                                {/* منبع خطا */}
                                {(msg.action_type === 'error' || msg.action_type === 'console-error') && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-gray-500">منبع خطا:</span>
                                    <span className="font-medium text-orange-600 dark:text-orange-400">
                                      {msg.action_type === 'console-error' ? '🖥️ کنسول مرورگر' : '🖥️ خطای JavaScript'}
                                    </span>
                                  </div>
                                )}

                                <div className="flex items-center justify-between">
                                  <span className="text-gray-500">وضعیت بک‌اند:</span>
                                  <span className={`font-medium ${
                                    msg.backend_verified === true ? 'text-green-600' :
                                    msg.backend_verified === false && msg.verified_by_model === 'console-error' ? 'text-orange-600' :
                                    msg.backend_verified === false ? 'text-red-600' :
                                    'text-yellow-500'
                                  }`}>
                                    {msg.backend_verified === false && msg.verified_by_model === 'console-error'
                                      ? 'خطای سمت مرورگر (نه بک‌اند)'
                                      : msg.backend_verified === true ? 'سالم'
                                      : msg.backend_verified === false ? 'خطای بک‌اند'
                                      : 'در حال بررسی...'}
                                  </span>
                                </div>

                                {msg.verified_by_model && msg.verified_by_model !== 'console-error' && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-gray-500">بررسی توسط:</span>
                                    <span className="font-mono text-[11px] bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 px-1.5 py-0.5 rounded">
                                      {msg.verified_by_model}
                                    </span>
                                  </div>
                                )}

                                {msg.logs_checked !== undefined && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-gray-500">لاگ‌های بررسی شده:</span>
                                    {msg.checked_logs && msg.checked_logs.length > 0 ? (
                                      <button
                                        onClick={(e) => { e.stopPropagation(); setInspectorMsgLogsId(inspectorMsgLogsId === msg.id ? null : msg.id); }}
                                        className="font-medium text-blue-500 hover:text-blue-700 underline underline-offset-2"
                                      >
                                        {msg.logs_checked} لاگ {msg.error_logs_count ? `(${msg.error_logs_count} خطا)` : ''}
                                      </button>
                                    ) : (
                                      <span className="text-gray-400 italic">
                                        {msg.logs_checked === 0 ? 'بدون لاگ' : `${msg.logs_checked} لاگ`}
                                      </span>
                                    )}
                                  </div>
                                )}

                                {/* لاگ‌های واقعی بررسی شده (باز/بسته با کلیک) */}
                                {inspectorMsgLogsId === msg.id && msg.checked_logs && msg.checked_logs.length > 0 && (
                                  <div className="mt-1.5 bg-gray-900 rounded overflow-hidden">
                                    <div className="flex items-center justify-between px-2 py-1 bg-gray-800 text-gray-300">
                                      <span className="text-[10px] font-bold">لاگ‌های بررسی شده ({msg.checked_logs.length})</span>
                                      <button onClick={(e) => { e.stopPropagation(); setInspectorMsgLogsId(null); }} className="text-gray-500 hover:text-white text-[10px]">✕</button>
                                    </div>
                                    <div className="max-h-32 overflow-auto p-1.5 space-y-0.5">
                                      {msg.checked_logs.map((log, i) => (
                                        <div key={i} className={`text-[10px] font-mono px-1 py-0.5 rounded ${
                                          log.level?.toUpperCase() === 'ERROR' || log.level?.toUpperCase() === 'CRITICAL'
                                            ? 'bg-red-900/50 text-red-300'
                                            : log.level?.toUpperCase() === 'WARN' || log.level?.toUpperCase() === 'WARNING'
                                              ? 'bg-yellow-900/30 text-yellow-300'
                                              : 'text-gray-400'
                                        }`}>
                                          <span className={`font-bold ${
                                            log.level?.toUpperCase() === 'ERROR' ? 'text-red-400' :
                                            log.level?.toUpperCase() === 'WARN' ? 'text-yellow-400' : 'text-green-400'
                                          }`}>[{log.level}]</span> {log.message}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {msg.backend_log_summary && (
                                  <div className={`mt-1 p-1.5 rounded text-[11px] ${
                                    msg.backend_verified === false
                                      ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                                      : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                                  }`}>
                                    {msg.backend_log_summary}
                                  </div>
                                )}
                              </>
                            )}

                            {/* توکن مصرفی */}
                            {msg.tokens_used && (
                              <div className="flex items-center justify-between">
                                <span className="text-gray-500">توکن مصرفی:</span>
                                <span className="text-gray-600 dark:text-gray-400">{msg.tokens_used}</span>
                              </div>
                            )}

                            {/* زمان دقیق */}
                            <div className="flex items-center justify-between">
                              <span className="text-gray-500">زمان:</span>
                              <span className="text-gray-600 dark:text-gray-400 font-mono text-[11px]">
                                {msg.timestamp.toLocaleString('fa-IR')}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* در حال لود */}
                  {inspectorChatLoading && (
                    <div className="flex gap-2">
                      <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center text-white text-sm flex-shrink-0 animate-pulse">
                        🤖
                      </div>
                      <div className="bg-white dark:bg-gray-800 rounded-lg rounded-tl-none p-3 shadow-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* 🔍 مودال انتخاب مدل برای بررسی خطا */}
                {investigateModalMsgId && (
                  <div className="absolute inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md max-h-[80%] overflow-hidden" dir="rtl">
                      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <h3 className="font-bold text-sm">🔍 انتخاب مدل برای بررسی خطا</h3>
                        <button onClick={() => setInvestigateModalMsgId(null)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
                      </div>
                      <div className="p-3 max-h-[50vh] overflow-y-auto space-y-1.5">
                        {investigateModels.length === 0 ? (
                          <div className="text-center py-4 text-gray-400 text-sm">در حال بارگذاری مدل‌ها...</div>
                        ) : investigateModels.map(model => (
                          <label
                            key={model.id}
                            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                              investigateSelectedModels.includes(model.id)
                                ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700'
                                : 'hover:bg-gray-50 dark:hover:bg-gray-750 border border-transparent'
                            } ${!model.enabled || !model.provider_available ? 'opacity-60' : ''}`}
                          >
                            <input
                              type="checkbox"
                              checked={investigateSelectedModels.includes(model.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setInvestigateSelectedModels(prev => [...prev, model.id]);
                                } else {
                                  setInvestigateSelectedModels(prev => prev.filter(id => id !== model.id));
                                }
                              }}
                              disabled={!model.enabled || !model.provider_available}
                              className="rounded"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-medium truncate">{model.name}</span>
                                {model.recommended && (
                                  <span className="text-[9px] bg-green-100 dark:bg-green-900/30 text-green-600 px-1 rounded">پیشنهادی</span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-[10px] text-gray-400">{model.provider}</span>
                                {model.capabilities.includes('CODE') && (
                                  <span className="text-[9px] bg-purple-100 dark:bg-purple-900/30 text-purple-600 px-1 rounded">کد</span>
                                )}
                                {model.capabilities.includes('REASONING') && (
                                  <span className="text-[9px] bg-orange-100 dark:bg-orange-900/30 text-orange-600 px-1 rounded">استدلال</span>
                                )}
                              </div>
                            </div>
                            {!model.enabled && (
                              <button
                                onClick={(e) => { e.preventDefault(); e.stopPropagation(); quickEnableModel(model.id); }}
                                className="text-[10px] bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-2 py-1 rounded hover:bg-yellow-200 transition-colors flex-shrink-0"
                              >
                                فعال‌سازی
                              </button>
                            )}
                            {model.enabled && !model.provider_available && (
                              <span className="text-[10px] text-red-400 flex-shrink-0">بدون API</span>
                            )}
                          </label>
                        ))}
                      </div>
                      <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <span className="text-[11px] text-gray-400">{investigateSelectedModels.length} مدل انتخاب شده</span>
                        <button
                          onClick={startInvestigation}
                          disabled={investigateSelectedModels.length === 0}
                          className="px-4 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          🔍 شروع بررسی
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 🆕 مودال بررسی کلی چند خطا */}
                {bulkInvestigateModalOpen && (
                  <div className="absolute inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md max-h-[80%] overflow-hidden" dir="rtl">
                      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <h3 className="font-bold text-sm">🔍 بررسی کلی {selectedErrorIds.length} خطا</h3>
                        <button onClick={() => setBulkInvestigateModalOpen(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
                      </div>
                      <div className="p-3 text-xs text-gray-500 bg-red-50 dark:bg-red-900/10 border-b border-gray-200 dark:border-gray-700">
                        <p className="font-medium text-red-700 dark:text-red-300 mb-1">خطاهای انتخاب شده:</p>
                        <ul className="space-y-0.5 max-h-24 overflow-y-auto">
                          {selectedErrorIds.map((id, i) => {
                            const m = inspectorChatMessages.find(msg => msg.id === id);
                            return m ? (
                              <li key={id} className="text-[10px] text-gray-600 dark:text-gray-300 truncate">
                                {i + 1}. {(m as any).action_type === 'console-error' ? '🖥️' : '⚠️'} {m.content?.slice(0, 80)}
                              </li>
                            ) : null;
                          })}
                        </ul>
                        <p className="mt-2 text-[10px] text-gray-400">مدل اولویت‌بندی، وابستگی و ریشه مشترک خطاها را تحلیل می‌کند.</p>
                      </div>
                      <div className="p-3 max-h-[40vh] overflow-y-auto space-y-1.5">
                        {investigateModels.length === 0 ? (
                          <div className="text-center py-4 text-gray-400 text-sm">در حال بارگذاری مدل‌ها...</div>
                        ) : investigateModels.filter(m => m.enabled && m.provider_available).map(model => (
                          <label
                            key={model.id}
                            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                              investigateSelectedModels.includes(model.id)
                                ? 'bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700'
                                : 'hover:bg-gray-50 dark:hover:bg-gray-750 border border-transparent'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={investigateSelectedModels.includes(model.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setInvestigateSelectedModels(prev => [...prev, model.id]);
                                } else {
                                  setInvestigateSelectedModels(prev => prev.filter(id => id !== model.id));
                                }
                              }}
                              className="rounded"
                            />
                            <div className="flex-1 min-w-0">
                              <span className="text-xs font-medium">{model.name}</span>
                              <span className="text-[10px] text-gray-400 mr-1">({model.provider})</span>
                              {model.recommended && (
                                <span className="text-[9px] bg-green-100 text-green-600 px-1 rounded mr-1">پیشنهادی</span>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                      <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <span className="text-[11px] text-gray-400">{investigateSelectedModels.length} مدل | {selectedErrorIds.length} خطا</span>
                        <button
                          onClick={startBulkInvestigation}
                          disabled={investigateSelectedModels.length === 0}
                          className="px-4 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          🔍 شروع بررسی کلی
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 🔧 مودال انتخاب مدل برای اصلاح */}
                {fixModalOpen && (
                  <div className="absolute inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md max-h-[80%] overflow-hidden" dir="rtl">
                      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <h3 className="font-bold text-sm">🔧 انتخاب مدل برای اصلاح خودکار</h3>
                        <button onClick={() => setFixModalOpen(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
                      </div>
                      <div className="p-3 text-xs text-gray-500 bg-yellow-50 dark:bg-yellow-900/10 border-b border-gray-200 dark:border-gray-700">
                        ⚠️ مدل انتخابی branch جدید ایجاد کرده و تغییرات را commit می‌کند. سپس Pull Request ایجاد می‌شود.
                      </div>
                      <div className="p-3 max-h-[50vh] overflow-y-auto space-y-1.5">
                        {investigateModels.filter(m => m.enabled && m.provider_available).map(model => (
                          <label
                            key={model.id}
                            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                              fixSelectedModels.includes(model.id)
                                ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700'
                                : 'hover:bg-gray-50 dark:hover:bg-gray-750 border border-transparent'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={fixSelectedModels.includes(model.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setFixSelectedModels(prev => [...prev, model.id]);
                                } else {
                                  setFixSelectedModels(prev => prev.filter(id => id !== model.id));
                                }
                              }}
                              className="rounded"
                            />
                            <div className="flex-1 min-w-0">
                              <span className="text-xs font-medium">{model.name}</span>
                              <span className="text-[10px] text-gray-400 mr-1">({model.provider})</span>
                              {model.recommended && (
                                <span className="text-[9px] bg-green-100 text-green-600 px-1 rounded mr-1">پیشنهادی</span>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                      <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <span className="text-[11px] text-gray-400">{fixSelectedModels.length} مدل انتخاب شده</span>
                        <button
                          onClick={startFix}
                          disabled={fixSelectedModels.length === 0}
                          className="px-4 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          🔧 شروع اصلاح
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 📸 مودال انتخاب مدل برای دیباگ بصری */}
                {visualDebugModelSelection && (
                  <div className="absolute inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md max-h-[80%] overflow-hidden" dir="rtl">
                      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <h3 className="font-bold text-sm">🔍 انتخاب مدل Vision — بازرس بصری هوشمند</h3>
                        <button onClick={() => setVisualDebugModelSelection(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
                      </div>
                      <div className="p-3 text-xs text-gray-500 bg-purple-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-gray-700">
                        📸 {visualDebugScreenshots.length} عکس (📦 هر عکس با پک لاگ مجزا)
                        {visualDebugScreenshots.map((ss, i) => {
                          const cLogs = ss.consoleLogs?.length || 0;
                          const bLogs = ss.backendLogs?.length || 0;
                          return cLogs + bLogs > 0 ? (
                            <span key={i} className="ml-1 text-[10px] text-purple-400">| عکس {i+1}: {cLogs} کنسول + {bLogs} بکند</span>
                          ) : null;
                        })}
                        {visualDebugDescription && <span className="block mt-1">💬 {visualDebugDescription.slice(0, 60)}...</span>}
                      </div>
                      <div className="p-3 max-h-[50vh] overflow-y-auto space-y-1.5">
                        {visualDebugVisionModels.length === 0 ? (
                          <div className="text-center py-4 text-gray-400 text-sm">در حال بارگذاری مدل‌ها...</div>
                        ) : visualDebugVisionModels.map(model => (
                          <label
                            key={model.id}
                            className={`flex items-center gap-2 p-2 rounded-lg transition-colors ${
                              !model.enabled ? 'opacity-40 cursor-not-allowed' :
                              visualDebugSelectedModels.includes(model.id)
                                ? 'bg-purple-50 dark:bg-purple-900/20 border border-purple-300 dark:border-purple-700 cursor-pointer'
                                : 'hover:bg-gray-50 dark:hover:bg-gray-750 border border-transparent cursor-pointer'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={visualDebugSelectedModels.includes(model.id)}
                              disabled={!model.enabled}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setVisualDebugSelectedModels(prev => [...prev, model.id]);
                                } else {
                                  setVisualDebugSelectedModels(prev => prev.filter(id => id !== model.id));
                                }
                              }}
                              className="rounded"
                            />
                            <div className="flex-1 min-w-0">
                              <span className="text-xs font-medium">{model.name}</span>
                              <span className="text-[10px] text-gray-400 mr-1">({model.provider})</span>
                              {model.recommended && (
                                <span className="text-[9px] bg-green-100 text-green-600 px-1 rounded mr-1">پیشنهادی</span>
                              )}
                              {model.supports_images && (
                                <span className="text-[9px] bg-purple-100 text-purple-600 px-1 rounded">Vision</span>
                              )}
                            </div>
                            {!model.enabled && (
                              <span className="text-[10px] text-red-400 flex-shrink-0">غیرفعال</span>
                            )}
                          </label>
                        ))}
                      </div>
                      <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <span className="text-[11px] text-gray-400">{visualDebugSelectedModels.length} مدل انتخاب شده</span>
                        <button
                          onClick={sendVisualDebug}
                          disabled={visualDebugSelectedModels.length === 0}
                          className="px-4 py-2 bg-purple-500 text-white text-sm rounded-lg hover:bg-purple-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          🔍 شروع تحلیل هوشمند
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 🔄 مودال انتخاب مدل برای اعمال تغییرات (بازتحلیل دیباگ بصری) */}
                {reanalyzeModalOpen && (
                  <div className="absolute inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md max-h-[80%] overflow-hidden" dir="rtl">
                      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <h3 className="font-bold text-sm">🔄 انتخاب مدل برای اعمال تغییرات</h3>
                        <button onClick={() => setReanalyzeModalOpen(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
                      </div>
                      <div className="p-3 text-xs text-gray-500 bg-purple-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-gray-700">
                        💡 اگر همان مدل Vision را انتخاب کنید، تغییرات مستقیم اعمال می‌شود.
                        اگر مدل دیگری انتخاب کنید، آن مدل گزارش را بازتحلیل کرده و گزارش مستقل خودش را تولید می‌کند.
                      </div>
                      <div className="p-3 max-h-[50vh] overflow-y-auto space-y-1.5">
                        {(() => {
                          const sourceMsg = inspectorChatMessages.find(m => m.id === reanalyzeSourceMsgId) as any;
                          const visionModelId = sourceMsg?.model_id;
                          // ترکیب مدل‌های Vision و مدل‌های عادی
                          const allModels = [
                            ...visualDebugVisionModels.map(m => ({ ...m, isVision: true })),
                            ...inspectorModels
                              .filter(m => m.enabled && !visualDebugVisionModels.some(vm => vm.id === m.id))
                              .map(m => ({ ...m, isVision: false, supports_images: false, capabilities: [], context_window: 0, recommended: false })),
                          ];
                          return allModels.length === 0 ? (
                            <div className="text-center py-4 text-gray-400 text-sm">در حال بارگذاری مدل‌ها...</div>
                          ) : allModels.map(model => (
                            <label
                              key={model.id}
                              className={`flex items-center gap-2 p-2 rounded-lg transition-colors ${
                                !model.enabled ? 'opacity-40 cursor-not-allowed' :
                                reanalyzeSelectedModel === model.id
                                  ? 'bg-purple-50 dark:bg-purple-900/20 border border-purple-300 dark:border-purple-700 cursor-pointer'
                                  : 'hover:bg-gray-50 dark:hover:bg-gray-750 border border-transparent cursor-pointer'
                              }`}
                            >
                              <input
                                type="radio"
                                name="reanalyze_model"
                                checked={reanalyzeSelectedModel === model.id}
                                disabled={!model.enabled}
                                onChange={() => setReanalyzeSelectedModel(model.id)}
                                className="rounded"
                              />
                              <div className="flex-1 min-w-0">
                                <span className="text-xs font-medium">{model.name}</span>
                                <span className="text-[10px] text-gray-400 mr-1">({model.provider})</span>
                                {model.id === visionModelId && (
                                  <span className="text-[9px] bg-purple-100 text-purple-600 px-1 rounded mr-1">مدل فعلی (اعمال مستقیم)</span>
                                )}
                                {model.id !== visionModelId && (model as any).isVision && (
                                  <span className="text-[9px] bg-blue-100 text-blue-600 px-1 rounded mr-1">Vision</span>
                                )}
                                {model.id !== visionModelId && !(model as any).isVision && (
                                  <span className="text-[9px] bg-gray-100 text-gray-500 px-1 rounded mr-1">بازتحلیل متنی</span>
                                )}
                              </div>
                            </label>
                          ));
                        })()}
                      </div>
                      <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <span className="text-[11px] text-gray-400">
                          {reanalyzeSelectedModel
                            ? (reanalyzeSelectedModel === (inspectorChatMessages.find(m => m.id === reanalyzeSourceMsgId) as any)?.model_id
                                ? '✅ اعمال مستقیم'
                                : '🔄 بازتحلیل با مدل جدید')
                            : 'یک مدل انتخاب کنید'}
                        </span>
                        <button
                          onClick={handleReanalyzeConfirm}
                          disabled={!reanalyzeSelectedModel}
                          className="px-4 py-2 bg-purple-500 text-white text-sm rounded-lg hover:bg-purple-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          {reanalyzeSelectedModel === (inspectorChatMessages.find(m => m.id === reanalyzeSourceMsgId) as any)?.model_id
                            ? '✅ اعمال تغییرات'
                            : '🔄 شروع بازتحلیل'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 🆕 نوار انتخاب چندتایی خطاها */}
                {errorMultiSelectMode && (
                  <div className="px-3 py-2 border-t border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs text-red-700 dark:text-red-300">
                      <span className="font-medium">{selectedErrorIds.length} خطا انتخاب شده</span>
                      {selectedErrorIds.length > 0 && (
                        <button
                          onClick={() => setSelectedErrorIds([])}
                          className="text-[10px] text-red-400 hover:text-red-600 underline"
                        >
                          پاک کردن
                        </button>
                      )}
                      {/* دکمه انتخاب همه خطاها */}
                      <button
                        onClick={() => {
                          const allErrorIds = inspectorChatMessages
                            .filter(m => m.role === 'action' && (m as any).backend_verified === false)
                            .map(m => m.id);
                          setSelectedErrorIds(allErrorIds);
                        }}
                        className="text-[10px] text-red-400 hover:text-red-600 underline"
                      >
                        انتخاب همه
                      </button>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={async () => {
                          if (selectedErrorIds.length === 0) return;
                          // باز کردن مودال انتخاب مدل
                          setBulkInvestigateModalOpen(true);
                          // بارگذاری مدل‌ها
                          try {
                            const res = await fetch(`${API_BASE}/api/render/inspector/models/for-investigation/${projectId}`);
                            const data = await res.json();
                            if (data.success && Array.isArray(data.models)) {
                              setInvestigateModels(data.models);
                              const recommended = data.models.filter((m: any) => m.recommended).map((m: any) => m.id);
                              setInvestigateSelectedModels(recommended.slice(0, 2));
                            }
                          } catch {}
                        }}
                        disabled={selectedErrorIds.length === 0 || investigateLoading}
                        className="px-3 py-1 bg-red-500 text-white text-xs rounded-lg hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        🔍 بررسی کلی ({selectedErrorIds.length})
                      </button>
                      <button
                        onClick={() => { setErrorMultiSelectMode(false); setSelectedErrorIds([]); }}
                        className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        انصراف
                      </button>
                    </div>
                  </div>
                )}

                {/* ورودی پیام */}
                <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                  {/* 🔒 نمایش وضعیت قفل عملیات */}
                  {inspectorOpLock && (
                    <div className="mb-2 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg text-xs border border-amber-200 dark:border-amber-800">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                          <span className="animate-pulse">{inspectorOpType === 'investigate' ? '🔍' : '🔧'}</span>
                          <span className="font-medium">
                            {inspectorOpType === 'investigate' ? 'بررسی در حال انجام...' : 'اصلاح در حال انجام...'}
                          </span>
                        </div>
                        <button
                          onClick={() => {
                            if (inspectorOpAbortRef.current) {
                              inspectorOpAbortRef.current.abort();
                            }
                            // لغو background batch task
                            if (inspectorBatchTaskKeyRef.current) {
                              fetch(`${API_BASE}/api/render/inspector/smart-chat/batch-cancel/${inspectorBatchTaskKeyRef.current}`, { method: 'POST' }).catch(() => {});
                              inspectorBatchTaskKeyRef.current = null;
                              try { sessionStorage.removeItem('inspector_batch_task'); } catch {}
                            }
                            setInspectorOpLock(false);
                            setInspectorOpType(null);
                            setInvestigateLoading(false);
                            setFixLoading(false);
                            setInspectorChatMessages(prev => [...prev, {
                              id: `cancel_${Date.now()}`,
                              role: 'system' as const,
                              content: '⏹ عملیات توسط کاربر لغو شد',
                              timestamp: new Date(),
                            }]);
                          }}
                          className="px-3 py-1 bg-red-500 hover:bg-red-600 text-white text-[10px] rounded-md transition-colors"
                        >
                          ⏹ لغو
                        </button>
                      </div>
                      <p className="text-amber-600/70 dark:text-amber-500/70 text-[10px] mt-1">
                        ارسال پیام و تعامل با پیش‌نمایش تا پایان عملیات غیرفعال است
                      </p>
                    </div>
                  )}
                  {/* 🆕 نمایش تسک فعال */}
                  {!inspectorOpLock && inspectorActiveTask && inspectorActiveTask.status === 'running' && (
                    <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-xs">
                      <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
                        <span className="animate-spin">⚙️</span>
                        <span>در حال اجرا: {inspectorActiveTask.description.slice(0, 40)}...</span>
                      </div>
                      <div className="mt-1 text-blue-500/80 text-[10px]">
                        مدل‌ها: {inspectorActiveTask.models.join(', ')}
                      </div>
                    </div>
                  )}

                  {/* 📸 پنل دیباگ بصری - گالری عکس‌ها + توضیح */}
                  {visualDebugMode && visualDebugScreenshots.length > 0 && !inspectorOpLock && (
                    <div className="mb-2 p-2 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-200 dark:border-purple-800" dir="rtl">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm">📸</span>
                          <span className="text-xs font-bold text-purple-700 dark:text-purple-300">دیباگ بصری</span>
                          <span className="text-[10px] text-purple-500 bg-purple-100 dark:bg-purple-900/40 px-1.5 rounded-full">{visualDebugScreenshots.length} عکس</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={takeVisualDebugScreenshot}
                            disabled={visualDebugTakingScreenshot}
                            className="text-[10px] text-purple-600 hover:text-purple-800 dark:text-purple-400 px-1.5 py-0.5 rounded hover:bg-purple-100 dark:hover:bg-purple-800/30 transition-colors disabled:opacity-50"
                          >
                            {visualDebugTakingScreenshot ? '⏳' : '📸'} عکس جدید
                          </button>
                          <button
                            onClick={() => { setVisualDebugScreenshots([]); setVisualDebugMode(false); setVisualDebugDescription(''); }}
                            className="text-[10px] text-red-500 hover:text-red-700 px-1.5 py-0.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                          >
                            پاک‌سازی
                          </button>
                        </div>
                      </div>

                      {/* گالری عکس‌ها - با نشانگر تعداد لاگ مرتبط */}
                      <div className="flex gap-2 overflow-x-auto pb-2 mb-2">
                        {visualDebugScreenshots.map((ss, idx) => {
                          const errCount = (ss.consoleLogs?.filter(l => l.level === 'error').length || 0) + (ss.backendLogs?.filter(l => l.level === 'error').length || 0);
                          const totalLogs = (ss.consoleLogs?.length || 0) + (ss.backendLogs?.length || 0);
                          return (
                          <div key={ss.id} className="relative flex-shrink-0 group">
                            <img
                              src={`data:image/png;base64,${ss.base64}`}
                              alt={`عکس ${idx + 1}`}
                              className="h-16 w-auto rounded-lg border border-purple-300 dark:border-purple-700 shadow-sm cursor-pointer hover:ring-2 hover:ring-purple-400 transition-all"
                              onClick={() => {
                                const win = window.open();
                                if (win) { win.document.write(`<img src="data:image/png;base64,${ss.base64}" style="max-width:100%">`); }
                              }}
                            />
                            <button
                              onClick={() => setVisualDebugScreenshots(prev => prev.filter(s => s.id !== ss.id))}
                              className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[8px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow"
                            >
                              ✕
                            </button>
                            <span className="absolute bottom-0.5 left-0.5 text-[8px] bg-black/60 text-white px-1 rounded">
                              {idx + 1}
                            </span>
                            {/* نشانگر تعداد لاگ و خطا مرتبط */}
                            {totalLogs > 0 && (
                              <span className={`absolute top-0.5 left-0.5 text-[7px] px-1 rounded ${errCount > 0 ? 'bg-red-500 text-white' : 'bg-purple-500 text-white'}`}>
                                {errCount > 0 ? `${errCount}!` : totalLogs}
                              </span>
                            )}
                          </div>
                          );
                        })}
                      </div>

                      {/* ورودی توضیح */}
                      <div className="flex gap-2 items-end">
                        <textarea
                          value={visualDebugDescription}
                          onChange={(e) => setVisualDebugDescription(e.target.value)}
                          placeholder="توضیح اختیاری درباره مشکل... (مثلاً: دکمه لاگین کار نمیکنه)"
                          className="flex-1 text-xs bg-white dark:bg-gray-700 border border-purple-200 dark:border-purple-700 rounded-lg px-3 py-1.5 resize-none focus:outline-none focus:ring-1 focus:ring-purple-400"
                          rows={2}
                        />
                        <button
                          onClick={startVisualDebugModelSelection}
                          className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-lg shadow-md transition-colors flex items-center gap-1 flex-shrink-0"
                        >
                          📸 ارسال برای تحلیل
                        </button>
                      </div>

                      {/* اطلاعات جمع‌آوری شده - هر عکس با پک مجزا */}
                      <div className="flex flex-wrap gap-2 mt-2 text-[9px] text-purple-500 dark:text-purple-400">
                        <span>📋 {importedProjectConsoleLogs.length} لاگ کنسول (زنده)</span>
                        <span>🖥️ {inspectorBackendLogs.length} لاگ بکند (زنده)</span>
                        {inspectorFrontendUrl && <span className="truncate max-w-[150px]">🔗 {inspectorFrontendUrl}</span>}
                        <span className="text-purple-400 dark:text-purple-500">| 📦 هر عکس لاگ‌ها و آدرس‌های مربوط به خودش را دارد</span>
                      </div>
                    </div>
                  )}

                  {/* نوار ریپلای */}
                  {inspectorReplyTo && (
                    <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-1.5 mb-1" dir="rtl">
                      <span className="text-blue-500 text-sm">↩️</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] text-blue-600 dark:text-blue-400 font-medium">
                          پاسخ به {inspectorReplyTo.role === 'user' ? 'پیام شما' : inspectorReplyTo.model_id || 'AI'}
                          {inspectorReplyTo.role === 'assistant' && inspectorReplyTo.model_id && (
                            <span className="text-green-600 dark:text-green-400 mr-1">
                              — از همان مدل پاسخ داده می‌شود
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                          {inspectorReplyTo.content?.slice(0, 80)}...
                        </p>
                      </div>
                      <button
                        onClick={() => setInspectorReplyTo(null)}
                        className="text-gray-400 hover:text-red-500 transition-colors text-sm flex-shrink-0"
                      >
                        ✕
                      </button>
                    </div>
                  )}

                  {/* 🆕 دکمه ورود به حالت انتخاب چندتایی — فقط وقتی خطایی وجود داره */}
                  {!errorMultiSelectMode && !inspectorOpLock && inspectorChatMessages.some(m => m.role === 'action' && (m as any).backend_verified === false) && (
                    <div className="mb-2 flex items-center">
                      <button
                        onClick={() => setErrorMultiSelectMode(true)}
                        className="text-[10px] px-2 py-1 bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors border border-red-200 dark:border-red-800"
                      >
                        ☑️ انتخاب چند خطا برای بررسی کلی
                      </button>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={inspectorChatInput}
                      onChange={(e) => setInspectorChatInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && !inspectorChatLoading && !inspectorOpLock && sendInspectorChat()}
                      placeholder={
                        inspectorOpLock
                          ? (inspectorOpType === 'investigate' ? '🔒 در حال بررسی... لطفاً صبر کنید' : '🔒 در حال اصلاح... لطفاً صبر کنید')
                          : inspectorAutoSelect
                            ? "درخواست خود را بنویسید... (مدل‌ها خودکار انتخاب می‌شوند)"
                            : inspectorSelectedModels.length > 0
                              ? "پیام خود را بنویسید..."
                              : "ابتدا مدلی انتخاب کنید..."
                      }
                      disabled={(!inspectorAutoSelect && inspectorSelectedModels.length === 0) || inspectorChatLoading || inspectorOpLock}
                      className={`flex-1 bg-gray-100 dark:bg-gray-700 rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 ${inspectorOpLock ? 'cursor-not-allowed' : ''}`}
                    />
                    <button
                      onClick={() => sendInspectorChat()}
                      disabled={!inspectorChatInput.trim() || (!inspectorAutoSelect && inspectorSelectedModels.length === 0) || inspectorChatLoading || inspectorOpLock}
                      className="bg-gradient-to-r from-red-500 to-orange-500 text-white rounded-full w-10 h-10 flex items-center justify-center hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {inspectorChatLoading ? (
                        <span className="animate-spin">⏳</span>
                      ) : inspectorOpLock ? (
                        <span>🔒</span>
                      ) : (
                        <span>➤</span>
                      )}
                    </button>
                  </div>
                  {!inspectorAutoSelect && inspectorSelectedModels.length === 0 && inspectorPowerOn && (
                    <p className="text-xs text-red-500 mt-1 text-center">از بالا مدلی انتخاب کنید یا انتخاب خودکار را فعال کنید</p>
                  )}
                </div>
              </div>
            </div>

            {/* 📋 پنل مدیریت فیلدهای دستورات، حافظه و آموزش */}
            <div className="mt-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden" dir="rtl">
              {/* هدر پنل - کلیک برای باز/بسته شدن */}
              <button
                onClick={() => { setPromptFieldsOpen(!promptFieldsOpen); if (!promptFieldsOpen) { if (promptFields.length === 0) loadPromptFields(); if (generalInstructions.length === 0) loadGeneralInstructions(); if (!visualDebugPromptData) loadVisualDebugPrompt(); } }}
                className="w-full flex items-center justify-between px-4 py-3 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 hover:from-purple-100 hover:to-indigo-100 dark:hover:from-purple-900/30 dark:hover:to-indigo-900/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">📋</span>
                  <div className="text-right">
                    <h3 className="font-bold text-sm text-purple-800 dark:text-purple-200">دستورات سیستم و فیلدهای قابل ارسال</h3>
                    <p className="text-xs text-purple-600 dark:text-purple-400">
                      دستورات عمومی همیشه فعال | {promptFields.length > 0 ? `${promptFields.length} فیلد قابل ارسال به چت` : 'هنوز فیلدی اضافه نشده'}
                    </p>
                  </div>
                </div>
                <span className={`text-lg transition-transform ${promptFieldsOpen ? 'rotate-180' : ''}`}>▼</span>
              </button>

              {/* محتوای پنل */}
              {promptFieldsOpen && (
                <div className="p-4">
                  {/* 📌 دستورات عمومی سیستم - همیشه فعال */}
                  <div className="mb-4 rounded-xl border-2 border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-900/10 overflow-hidden">
                    <button
                      onClick={() => setGeneralInstructionsOpen(!generalInstructionsOpen)}
                      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-lg">🔒</span>
                        <div className="text-right">
                          <span className="text-sm font-bold text-green-800 dark:text-green-200">دستورات عمومی سیستم</span>
                          <span className="text-xs text-green-600 dark:text-green-400 mr-2">(همیشه فعال در پرامپت مدل‌ها)</span>
                        </div>
                      </div>
                      <span className={`text-xs transition-transform ${generalInstructionsOpen ? 'rotate-180' : ''}`}>▼</span>
                    </button>
                    {generalInstructionsOpen && generalInstructions.length > 0 && (
                      <div className="px-4 pb-3 space-y-2">
                        {generalInstructions.map(inst => (
                          <div key={inst.id} className="flex items-start gap-2 p-2 bg-white/60 dark:bg-gray-800/40 rounded-lg">
                            <span className="text-sm mt-0.5">{inst.icon}</span>
                            <div className="flex-1 min-w-0">
                              <span className="text-xs font-bold text-green-800 dark:text-green-200">{inst.title}</span>
                              <p className="text-[11px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">
                                {inst.prompt_detail || inst.content}
                              </p>
                            </div>
                            <span className="text-[10px] bg-green-200 dark:bg-green-800 text-green-700 dark:text-green-300 px-1.5 py-0.5 rounded-full whitespace-nowrap">همیشه فعال</span>
                          </div>
                        ))}
                        <p className="text-[10px] text-green-500 dark:text-green-600 text-center mt-1">
                          دقیقاً همین متن‌ها در پرامپت مدل‌ها تزریق می‌شود — تغییرات خودکار منعکس می‌شوند
                        </p>
                      </div>
                    )}
                  </div>

                  {/* 📸 پرامپت ثابت دیباگ بصری - فقط خواندنی */}
                  <div className={`mb-4 rounded-xl border-2 overflow-hidden transition-all duration-500 ${
                    promptFieldsHighlighted.includes('visual_debug_prompt')
                      ? 'border-purple-400 bg-purple-50 dark:bg-purple-900/30 shadow-lg shadow-purple-500/20 ring-2 ring-purple-400/50 animate-pulse'
                      : 'border-purple-200 dark:border-purple-800 bg-purple-50/30 dark:bg-purple-900/5'
                  }`}>
                    <button
                      onClick={() => setVisualDebugPromptOpen(!visualDebugPromptOpen)}
                      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-purple-50 dark:hover:bg-purple-900/20 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-lg">📸</span>
                        <div className="text-right">
                          <span className="text-sm font-bold text-purple-800 dark:text-purple-200">پرامپت بازرس بصری هوشمند</span>
                          <span className="text-xs text-purple-600 dark:text-purple-400 mr-2">(رفع باگ + ایجاد قابلیت + تغییر ظاهر — با تحلیل عکس و کد)</span>
                          {promptFieldsHighlighted.includes('visual_debug_prompt') && (
                            <span className="text-xs font-bold text-purple-600 animate-pulse mr-2">در حال استفاده</span>
                          )}
                        </div>
                      </div>
                      <span className={`text-xs transition-transform ${visualDebugPromptOpen ? 'rotate-180' : ''}`}>▼</span>
                    </button>
                    {visualDebugPromptOpen && (
                      <div className="px-4 pb-3">
                        {visualDebugPromptData ? (
                          <div className="space-y-2 max-h-[300px] overflow-auto">
                            <p className="text-[10px] font-bold text-purple-600 dark:text-purple-300 mb-1">پرامپت بازرس بصری ({visualDebugPromptData.vd.length} بخش):</p>
                            {visualDebugPromptData.vd.map(inst => (
                              <div key={inst.id} className="p-2 bg-white/60 dark:bg-gray-800/40 rounded-lg border border-purple-100 dark:border-purple-800/40">
                                <div className="flex items-center gap-1 mb-1">
                                  <span className="text-sm">{inst.icon}</span>
                                  <span className="text-[11px] font-bold text-purple-800 dark:text-purple-200">{inst.title}</span>
                                </div>
                                <p className="text-[10px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">{inst.prompt_detail || inst.content}</p>
                              </div>
                            ))}
                            {visualDebugPromptData.gen.length > 0 && (
                              <>
                                <p className="text-[10px] font-bold text-green-600 dark:text-green-300 mt-2">+ دستورات عمومی ({visualDebugPromptData.gen.length} مورد) — خودکار تزریق می‌شود</p>
                                {visualDebugPromptData.gen.map(inst => (
                                  <div key={inst.id} className="p-1.5 bg-green-50/50 dark:bg-green-900/10 rounded border border-green-100 dark:border-green-800/30">
                                    <span className="text-[10px] text-green-700 dark:text-green-300">{inst.icon} {inst.title}: </span>
                                    <span className="text-[10px] text-gray-500 dark:text-gray-400">{inst.content}</span>
                                  </div>
                                ))}
                              </>
                            )}
                          </div>
                        ) : (
                          <div className="p-3 bg-white/60 dark:bg-gray-800/40 rounded-lg text-[11px] text-gray-500 text-center">در حال بارگذاری...</div>
                        )}
                        <p className="text-[10px] text-purple-400 mt-2">منبع واحد — هر تغییری در بکند خودکار اینجا منعکس می‌شود</p>
                      </div>
                    )}
                  </div>

                  {/* تب‌های دسته‌بندی + دکمه اضافه */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex gap-1">
                      {[
                        { key: 'all', label: 'همه', icon: '📋' },
                        { key: 'instruction', label: 'دستورات', icon: '📌' },
                        { key: 'memory', label: 'حافظه', icon: '🧠' },
                        { key: 'training', label: 'آموزش', icon: '📚' },
                      ].map(tab => (
                        <button
                          key={tab.key}
                          onClick={() => setPromptFieldActiveCategory(tab.key as any)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            promptFieldActiveCategory === tab.key
                              ? 'bg-purple-500 text-white shadow-sm'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                          }`}
                        >
                          {tab.icon} {tab.label}
                          <span className="mr-1 opacity-70">
                            ({tab.key === 'all' ? promptFields.length : promptFields.filter(f => f.category === tab.key).length})
                          </span>
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() => { setPromptFieldAdding(true); setPromptFieldNewData({title: '', content: '', category: promptFieldActiveCategory === 'all' ? 'instruction' : promptFieldActiveCategory, priority: promptFields.length}); }}
                      className="px-3 py-1.5 bg-green-500 text-white rounded-lg text-xs font-medium hover:bg-green-600 transition-colors"
                    >
                      + افزودن فیلد جدید
                    </button>
                  </div>

                  {/* فرم اضافه کردن فیلد جدید */}
                  {promptFieldAdding && (
                    <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-200 dark:border-green-800">
                      <h4 className="text-sm font-bold text-green-800 dark:text-green-200 mb-3">فیلد جدید</h4>
                      <div className="space-y-3">
                        <div className="flex gap-3">
                          <div className="flex-1">
                            <label className="text-xs text-gray-500 mb-1 block">عنوان</label>
                            <input
                              type="text"
                              value={promptFieldNewData.title}
                              onChange={e => setPromptFieldNewData(p => ({...p, title: e.target.value}))}
                              placeholder="عنوان فیلد..."
                              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-gray-500 mb-1 block">دسته‌بندی</label>
                            <select
                              value={promptFieldNewData.category}
                              onChange={e => setPromptFieldNewData(p => ({...p, category: e.target.value}))}
                              className="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:outline-none"
                            >
                              <option value="instruction">📌 دستور</option>
                              <option value="memory">🧠 حافظه</option>
                              <option value="training">📚 آموزش</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-xs text-gray-500 mb-1 block">اولویت</label>
                            <input
                              type="number"
                              value={promptFieldNewData.priority}
                              onChange={e => setPromptFieldNewData(p => ({...p, priority: parseInt(e.target.value) || 0}))}
                              min={0}
                              max={100}
                              className="w-20 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:outline-none"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">محتوا</label>
                          <textarea
                            value={promptFieldNewData.content}
                            onChange={e => setPromptFieldNewData(p => ({...p, content: e.target.value}))}
                            placeholder="محتوای دستور / حافظه / آموزش..."
                            rows={4}
                            className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:outline-none resize-y"
                          />
                        </div>
                        <div className="flex items-center gap-2 justify-end">
                          <button onClick={() => setPromptFieldAdding(false)} className="px-4 py-2 text-gray-500 hover:text-gray-700 text-sm">انصراف</button>
                          <button
                            onClick={createPromptField}
                            disabled={!promptFieldNewData.title.trim() || !promptFieldNewData.content.trim()}
                            className="px-4 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600 disabled:opacity-40 transition-colors"
                          >
                            ذخیره
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* لیست فیلدها */}
                  {promptFieldsLoading ? (
                    <div className="text-center py-8 text-gray-400 text-sm">در حال بارگذاری...</div>
                  ) : promptFields.length === 0 ? (
                    <div className="text-center py-8">
                      <span className="text-4xl block mb-2">📋</span>
                      <p className="text-gray-500 text-sm">هنوز فیلد سفارشی اضافه نشده</p>
                      <p className="text-gray-400 text-xs mt-1">فیلدها را اضافه کنید و با دکمه 📨 به عنوان درخواست به چت ارسال کنید</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {promptFields
                        .filter(f => promptFieldActiveCategory === 'all' || f.category === promptFieldActiveCategory)
                        .map((field, idx) => {
                          const isHighlighted = promptFieldsHighlighted.includes(field.id);
                          const isEditing = promptFieldEditing === field.id;
                          const isTesting = promptFieldTesting === field.id;
                          const testResult = promptFieldTestResult?.field_id === field.id ? promptFieldTestResult : null;
                          const categoryIcon = field.category === 'instruction' ? '📌' : field.category === 'memory' ? '🧠' : '📚';
                          const categoryLabel = field.category === 'instruction' ? 'دستور' : field.category === 'memory' ? 'حافظه' : 'آموزش';
                          const categoryColor = field.category === 'instruction' ? 'red' : field.category === 'memory' ? 'blue' : 'amber';

                          return (
                            <div
                              key={field.id}
                              className={`rounded-xl border-2 transition-all duration-500 ${
                                isHighlighted
                                  ? 'border-green-400 bg-green-50 dark:bg-green-900/30 shadow-lg shadow-green-500/20 ring-2 ring-green-400/50 animate-pulse'
                                  : field.is_active
                                    ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-750'
                                    : 'border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 opacity-60'
                              }`}
                            >
                              {/* هدر فیلد */}
                              <div className="flex items-center justify-between px-4 py-3">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                  {/* شماره اولویت */}
                                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                                    isHighlighted ? 'bg-green-500 text-white' : `bg-${categoryColor}-100 dark:bg-${categoryColor}-900/30 text-${categoryColor}-700 dark:text-${categoryColor}-300`
                                  }`}>
                                    {field.priority}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="text-sm">{categoryIcon}</span>
                                      <span className="text-xs font-medium text-gray-400">{categoryLabel}</span>
                                      {isHighlighted && <span className="text-xs font-bold text-green-600 animate-pulse">در حال استفاده توسط مدل</span>}
                                    </div>
                                    <h4 className="text-sm font-bold text-gray-800 dark:text-gray-200 truncate">{field.title}</h4>
                                  </div>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  {/* آمار استفاده */}
                                  {field.usage_count > 0 && (
                                    <span className="text-[10px] bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 px-2 py-0.5 rounded-full">
                                      {field.usage_count}x استفاده
                                    </span>
                                  )}
                                  {/* نتیجه آخرین تست */}
                                  {field.last_test_passed !== null && (
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                                      field.last_test_passed ? 'bg-green-100 dark:bg-green-900/30 text-green-600' : 'bg-red-100 dark:bg-red-900/30 text-red-600'
                                    }`}>
                                      {field.last_test_passed ? '✅ تست موفق' : '❌ تست ناموفق'}
                                    </span>
                                  )}
                                  {/* سوییچ فعال/غیرفعال */}
                                  <button
                                    onClick={() => togglePromptFieldActive(field.id, field.is_active)}
                                    className={`relative w-10 h-5 rounded-full transition-colors ${
                                      field.is_active ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
                                    }`}
                                  >
                                    <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${
                                      field.is_active ? 'right-0.5' : 'right-5'
                                    }`} />
                                  </button>
                                  {/* دکمه ارسال به چت - فیلد را به عنوان پیام چت ارسال می‌کند */}
                                  <button
                                    onClick={() => {
                                      const fieldMsg = `📌 [${field.title}]: ${field.content}`;
                                      sendInspectorChat(fieldMsg);
                                    }}
                                    disabled={inspectorChatLoading || inspectorOpLock}
                                    className="p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-lg transition-colors disabled:opacity-50"
                                    title="ارسال به چت - این فیلد را به عنوان درخواست در چت اجرا کن"
                                  >
                                    <span className="text-sm">📨</span>
                                  </button>
                                  {/* دکمه تست زنده */}
                                  <button
                                    onClick={() => testPromptField(field.id)}
                                    disabled={isTesting}
                                    className="p-1.5 text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded-lg transition-colors disabled:opacity-50"
                                    title="تست زنده - بررسی اینکه مدل واقعاً این فیلد را می‌خواند"
                                  >
                                    {isTesting ? <span className="animate-spin text-sm">⏳</span> : <span className="text-sm">🧪</span>}
                                  </button>
                                  {/* 📋 کپی پرامپت قوی — برای ابزار کدنویس خارجی */}
                                  <button
                                    onClick={() => copyStrongPromptForField(field)}
                                    className={`p-1.5 rounded-lg transition-colors ${
                                      copyFieldFeedbackId === field.id
                                        ? 'text-green-600 bg-green-50 dark:bg-green-900/30'
                                        : 'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                                    }`}
                                    title="کپی پرامپت قوی - این پرامپت با ساختار scan_strong + موقعیت فایل‌ها قابل اعمال در ابزار خارجی (Cursor/Copilot) است"
                                  >
                                    <span className="text-sm">{copyFieldFeedbackId === field.id ? '✅' : '📋'}</span>
                                  </button>
                                  {/* دکمه ویرایش */}
                                  <button
                                    onClick={() => {
                                      if (isEditing) {
                                        setPromptFieldEditing(null);
                                      } else {
                                        setPromptFieldEditing(field.id);
                                        setPromptFieldEditData({title: field.title, content: field.content, category: field.category, priority: field.priority});
                                      }
                                    }}
                                    className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                                    title="ویرایش"
                                  >
                                    <span className="text-sm">{isEditing ? '✕' : '✏️'}</span>
                                  </button>
                                  {/* دکمه حذف */}
                                  <button
                                    onClick={() => { if (confirm(`آیا از حذف فیلد «${field.title}» مطمئنید؟`)) deletePromptField(field.id); }}
                                    className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                    title="حذف"
                                  >
                                    <span className="text-sm">🗑️</span>
                                  </button>
                                </div>
                              </div>

                              {/* محتوای فیلد */}
                              {!isEditing && (
                                <div className="px-4 pb-3">
                                  <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 dark:bg-gray-900/30 rounded-lg p-3 max-h-32 overflow-y-auto">
                                    {field.content}
                                  </pre>
                                  {field.last_used_at && (
                                    <p className="text-[10px] text-gray-400 mt-2">
                                      آخرین استفاده: {new Date(field.last_used_at).toLocaleDateString('fa-IR')} {new Date(field.last_used_at).toLocaleTimeString('fa-IR')}
                                    </p>
                                  )}
                                </div>
                              )}

                              {/* فرم ویرایش */}
                              {isEditing && (
                                <div className="px-4 pb-4 space-y-3 border-t border-gray-100 dark:border-gray-700 pt-3">
                                  <div className="flex gap-3">
                                    <div className="flex-1">
                                      <label className="text-xs text-gray-500 mb-1 block">عنوان</label>
                                      <input
                                        type="text"
                                        value={promptFieldEditData.title}
                                        onChange={e => setPromptFieldEditData(p => ({...p, title: e.target.value}))}
                                        className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                      />
                                    </div>
                                    <div>
                                      <label className="text-xs text-gray-500 mb-1 block">دسته‌بندی</label>
                                      <select
                                        value={promptFieldEditData.category}
                                        onChange={e => setPromptFieldEditData(p => ({...p, category: e.target.value}))}
                                        className="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                      >
                                        <option value="instruction">📌 دستور</option>
                                        <option value="memory">🧠 حافظه</option>
                                        <option value="training">📚 آموزش</option>
                                      </select>
                                    </div>
                                    <div>
                                      <label className="text-xs text-gray-500 mb-1 block">اولویت</label>
                                      <input
                                        type="number"
                                        value={promptFieldEditData.priority}
                                        onChange={e => setPromptFieldEditData(p => ({...p, priority: parseInt(e.target.value) || 0}))}
                                        min={0} max={100}
                                        className="w-20 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                      />
                                    </div>
                                  </div>
                                  <div>
                                    <label className="text-xs text-gray-500 mb-1 block">محتوا</label>
                                    <textarea
                                      value={promptFieldEditData.content}
                                      onChange={e => setPromptFieldEditData(p => ({...p, content: e.target.value}))}
                                      rows={5}
                                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-y"
                                    />
                                  </div>
                                  <div className="flex items-center gap-2 justify-end">
                                    <button onClick={() => setPromptFieldEditing(null)} className="px-4 py-2 text-gray-500 hover:text-gray-700 text-sm">انصراف</button>
                                    <button
                                      onClick={() => updatePromptField(field.id)}
                                      className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 transition-colors"
                                    >
                                      ذخیره تغییرات
                                    </button>
                                    <button
                                      onClick={() => { updatePromptField(field.id); setTimeout(() => testPromptField(field.id), 500); }}
                                      className="px-4 py-2 bg-yellow-500 text-white rounded-lg text-sm hover:bg-yellow-600 transition-colors"
                                    >
                                      ذخیره + تست زنده
                                    </button>
                                  </div>
                                </div>
                              )}

                              {/* نتیجه تست زنده */}
                              {testResult && (
                                <div className={`mx-4 mb-3 p-3 rounded-lg border ${
                                  testResult.passed
                                    ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                    : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                                }`}>
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-sm">{testResult.passed ? '✅' : '❌'}</span>
                                    <span className={`text-xs font-bold ${testResult.passed ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                                      {testResult.passed ? 'مدل این فیلد را خواند و درک کرد' : 'مدل نتوانست فیلد را تأیید کند'}
                                    </span>
                                    <span className="text-[10px] text-gray-400 mr-auto">مدل: {testResult.model_id}</span>
                                  </div>
                                  <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-sans leading-relaxed bg-white dark:bg-gray-800 rounded p-2 max-h-40 overflow-y-auto">
                                    {testResult.response}
                                  </pre>
                                  <button
                                    onClick={() => setPromptFieldTestResult(null)}
                                    className="mt-2 text-[10px] text-gray-400 hover:text-gray-600"
                                  >
                                    بستن نتیجه تست
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  )}

                  {/* راهنما */}
                  <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    <p className="font-bold text-gray-600 dark:text-gray-300 mb-1">راهنما:</p>
                    <ul className="space-y-1 list-disc pr-4">
                      <li><strong>📌 دستورات:</strong> قوانین و رفتارهایی که مدل باید دقیقاً رعایت کند</li>
                      <li><strong>🧠 حافظه:</strong> اطلاعات مهم پروژه مثل معماری، تصمیمات فنی، باگ‌های شناخته‌شده</li>
                      <li><strong>📚 آموزش:</strong> الگوها و رویکردهای اختصاصی پروژه برای مدل</li>
                      <li><strong>🧪 تست زنده:</strong> مدل AI واقعاً فراخوانی شده و تأیید می‌کند فیلد را خوانده</li>
                      <li><strong>🟢 هایلایت سبز:</strong> وقتی مدل در حال استفاده از یک فیلد است، آن فیلد سبز رنگ می‌شود</li>
                      <li><strong>اولویت:</strong> عدد بزرگتر = اولویت بالاتر (اول تزریق می‌شود به پرامپت)</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 🔗 External Projects Panel */}
        {activeTab === 'external' && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            {!externalConnected ? (
              // ─── حالت اتصال ───
              <div className="max-w-2xl mx-auto">
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-3xl">🔗</span>
                  <div>
                    <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">اتصال به پروژهٔ خارجی</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      یک repo GitHub خارجی را با URL + توکن مستقل وصل کن — مستقل از پروژهٔ فعلی
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      🌐 URL ریپو GitHub <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={externalRepoUrl}
                      onChange={e => setExternalRepoUrl(e.target.value)}
                      placeholder="https://github.com/owner/repo"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      disabled={externalConnecting}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      🔑 Personal Access Token (اختیاری برای repo عمومی، الزامی برای خصوصی)
                    </label>
                    <input
                      type="password"
                      value={externalToken}
                      onChange={e => setExternalToken(e.target.value)}
                      placeholder="ghp_..."
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                      disabled={externalConnecting}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      توکن فقط برای این اتصال استفاده می‌شود و در DB رمزنگاری ذخیره می‌شود
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      🌿 شاخه (branch)
                    </label>
                    <input
                      type="text"
                      value={externalBranch}
                      onChange={e => setExternalBranch(e.target.value)}
                      placeholder="main"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      disabled={externalConnecting}
                    />
                  </div>

                  {externalConnectError && (
                    <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-3 rounded-lg text-sm">
                      ❌ {externalConnectError}
                    </div>
                  )}

                  <button
                    onClick={connectExternalGithub}
                    disabled={externalConnecting || !externalRepoUrl.trim()}
                    className="w-full px-4 py-2.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 flex items-center justify-center gap-2 font-medium"
                  >
                    {externalConnecting ? (
                      <>⏳ در حال اتصال...</>
                    ) : (
                      <>🔗 اتصال به repo خارجی</>
                    )}
                  </button>
                </div>

                <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-700 dark:text-blue-300">
                  <strong>💡 توضیح:</strong> این تب به شما اجازه می‌دهد یک repo GitHub <em>خارج از</em> سیستم
                  مدیریت پروژه را وصل کرده، فایل‌هایش را مرور و با AI تحلیل کنید — بدون اینکه آن repo
                  به‌صورت پروژهٔ کامل import شود.
                </div>
              </div>
            ) : (
              // ─── حالت متصل: نمایش فایل‌ها و تحلیل ───
              <div>
                <div className="flex items-center justify-between mb-4 pb-4 border-b dark:border-gray-700">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🔗</span>
                    <div>
                      <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">
                        {externalProjectInfo?.name || externalProjectInfo?.repo_name || externalRepoUrl.split('/').slice(-2).join('/')}
                      </h2>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Project ID: <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{externalProjectId}</code>
                        {externalProjectInfo?.branch && <> · branch: <code>{externalProjectInfo.branch}</code></>}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={analyzeExternalProject}
                      disabled={externalAnalyzing}
                      className="px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm"
                      title="تحلیل AI روی این پروژهٔ خارجی"
                    >
                      {externalAnalyzing ? '⏳' : '🧠'} Analyze
                    </button>
                    <button
                      onClick={loadExternalFiles}
                      disabled={externalFilesLoading}
                      className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 text-sm"
                    >
                      🔄 Refresh
                    </button>
                    <button
                      onClick={disconnectExternal}
                      className="px-3 py-1.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 text-sm"
                    >
                      ✕ Disconnect
                    </button>
                  </div>
                </div>

                {/* 2-column layout: files | content */}
                <div className="grid lg:grid-cols-3 gap-4">
                  {/* فایل‌ها */}
                  <div className="lg:col-span-1 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 dark:bg-gray-900/50 px-3 py-2 border-b dark:border-gray-700 text-sm font-medium">
                      📁 فایل‌ها {externalFiles.length > 0 && `(${externalFiles.length})`}
                    </div>
                    <div className="max-h-96 overflow-auto">
                      {externalFilesLoading ? (
                        <div className="p-4 text-sm text-gray-500">⏳ در حال بارگذاری...</div>
                      ) : externalFiles.length === 0 ? (
                        <div className="p-4 text-sm text-gray-500">هیچ فایلی یافت نشد</div>
                      ) : (
                        <ul className="text-sm">
                          {externalFiles.slice(0, 200).map((f: any, idx: number) => {
                            const fpath = typeof f === 'string' ? f : (f.path || f.name || '');
                            return (
                              <li key={idx}>
                                <button
                                  onClick={() => loadExternalFileContent(fpath)}
                                  className={`w-full text-right px-3 py-1.5 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 truncate ${
                                    externalSelectedFile === fpath ? 'bg-cyan-100 dark:bg-cyan-900/30 font-medium' : ''
                                  }`}
                                  title={fpath}
                                >
                                  <code className="text-xs">{fpath}</code>
                                </button>
                              </li>
                            );
                          })}
                          {externalFiles.length > 200 && (
                            <li className="px-3 py-2 text-xs text-gray-500 italic">
                              +{externalFiles.length - 200} فایل دیگر — refresh کنید برای فیلتر
                            </li>
                          )}
                        </ul>
                      )}
                    </div>
                  </div>

                  {/* محتوای فایل / README / تحلیل */}
                  <div className="lg:col-span-2 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 dark:bg-gray-900/50 px-3 py-2 border-b dark:border-gray-700 text-sm font-medium flex items-center justify-between">
                      <span>
                        {externalSelectedFile ? `📄 ${externalSelectedFile}` : externalAnalysis ? '🧠 تحلیل AI' : '📖 README'}
                      </span>
                    </div>
                    <div className="max-h-96 overflow-auto p-3">
                      {externalAnalyzing && (
                        <div className="text-sm text-gray-500">⏳ در حال تحلیل با AI...</div>
                      )}
                      {externalAnalysis && !externalAnalyzing && (
                        <div className="bg-purple-50 dark:bg-purple-900/20 p-3 rounded mb-3">
                          <div className="text-xs font-medium text-purple-700 dark:text-purple-300 mb-1">🧠 نتیجهٔ تحلیل</div>
                          <pre className="text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300 font-mono">
                            {typeof externalAnalysis === 'string' ? externalAnalysis : JSON.stringify(externalAnalysis, null, 2).slice(0, 4000)}
                          </pre>
                        </div>
                      )}
                      {externalSelectedFile ? (
                        externalFileLoading ? (
                          <div className="text-sm text-gray-500">⏳ در حال بارگذاری فایل...</div>
                        ) : (
                          <pre className="text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300 font-mono">
                            {externalFileContent || '(فایل خالی است)'}
                          </pre>
                        )
                      ) : (
                        <pre className="text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300">
                          {externalReadme || '(README موجود نیست — یک فایل از لیست انتخاب کنید)'}
                        </pre>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* مودال تنظیمات سینک */}
        {showSyncSettings && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full">
              <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
                <h3 className="font-bold flex items-center gap-2">
                  <span>🔄</span>
                  تنظیمات سینک GitHub
                </h3>
                <button
                  onClick={() => setShowSyncSettings(false)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  ✕
                </button>
              </div>
              <div className="p-4 space-y-4">
                {/* سینک خودکار با تایمر */}
                <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div>
                    <div className="font-medium">⏰ سینک خودکار</div>
                    <div className="text-xs text-gray-500">سینک خودکار با فاصله زمانی مشخص</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={syncSettings.auto_sync_enabled}
                      onChange={(e) => setSyncSettings({...syncSettings, auto_sync_enabled: e.target.checked})}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                {syncSettings.auto_sync_enabled && (
                  <div className="mr-4">
                    <label className="text-sm text-gray-600 dark:text-gray-400">بازه زمانی سینک:</label>
                    <select
                      value={syncSettings.sync_interval_minutes}
                      onChange={(e) => setSyncSettings({...syncSettings, sync_interval_minutes: parseInt(e.target.value)})}
                      className="w-full mt-1 p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value={5}>هر ۵ دقیقه</option>
                      <option value={10}>هر ۱۰ دقیقه</option>
                      <option value={15}>هر ۱۵ دقیقه</option>
                      <option value={30}>هر ۳۰ دقیقه</option>
                      <option value={60}>هر ۱ ساعت</option>
                      <option value={120}>هر ۲ ساعت</option>
                      <option value={360}>هر ۶ ساعت</option>
                      <option value={720}>هر ۱۲ ساعت</option>
                      <option value={1440}>روزانه</option>
                    </select>
                  </div>
                )}

                {/* سینک بعد از اجرای فیلد */}
                <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div>
                    <div className="font-medium">📤 سینک بعد از اجرای فیلد</div>
                    <div className="text-xs text-gray-500">بعد از اجرای فیلد و commit، خودکار سینک شود</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={syncSettings.sync_after_field_execution}
                      onChange={(e) => setSyncSettings({...syncSettings, sync_after_field_execution: e.target.checked})}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 dark:peer-focus:ring-green-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-green-600"></div>
                  </label>
                </div>

                {/* بروزرسانی دیاگرام */}
                <div className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <div>
                    <div className="font-medium">📊 بروزرسانی دیاگرام</div>
                    <div className="text-xs text-gray-500">دیاگرام و ساختار پروژه بعد از سینک بروز شود</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={syncSettings.update_diagram_after_sync}
                      onChange={(e) => setSyncSettings({...syncSettings, update_diagram_after_sync: e.target.checked, update_structure_after_sync: e.target.checked})}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                  </label>
                </div>

                {/* دکمه‌های عملیات */}
                <div className="flex gap-2 pt-4">
                  <button
                    onClick={() => {
                      saveSyncSettings();
                      setShowSyncSettings(false);
                    }}
                    disabled={savingSyncSettings}
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                  >
                    {savingSyncSettings ? '⏳...' : '💾 ذخیره'}
                  </button>
                  <button
                    onClick={() => setShowSyncSettings(false)}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    لغو
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* مودال انتخاب سرویس‌های Render */}
        {showServiceSelector && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-auto">
              <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800">
                <h3 className="font-bold flex items-center gap-2">
                  <span>🚀</span>
                  انتخاب سرویس‌های Render
                </h3>
                <button
                  onClick={() => setShowServiceSelector(false)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  ✕
                </button>
              </div>
              <div className="p-4">
                <p className="text-sm text-gray-500 mb-4">
                  سرویسی با نام این پروژه پیدا نشد. لطفاً سرویس‌های مرتبط را انتخاب کنید:
                </p>

                <div className="space-y-2 max-h-64 overflow-auto">
                  {availableRenderServices.map((service) => (
                    <label
                      key={service.id}
                      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition ${
                        selectedRenderServices.includes(service.id)
                          ? 'bg-orange-100 dark:bg-orange-900/30 border-2 border-orange-500'
                          : 'bg-gray-50 dark:bg-gray-700 border-2 border-transparent hover:bg-gray-100 dark:hover:bg-gray-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedRenderServices.includes(service.id)}
                        onChange={() => toggleServiceSelection(service.id)}
                        className="w-5 h-5 rounded text-orange-500 focus:ring-orange-500"
                      />
                      <div className="flex-1">
                        <div className="font-medium">{service.name}</div>
                        <div className="text-xs text-gray-500 font-mono">{service.id}</div>
                      </div>
                      <span className="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-600 rounded">
                        {service.type}
                      </span>
                    </label>
                  ))}
                </div>

                {selectedRenderServices.length > 0 && (
                  <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div className="text-sm text-green-700 dark:text-green-300">
                      ✅ {selectedRenderServices.length} سرویس انتخاب شد
                    </div>
                  </div>
                )}

                <div className="flex gap-2 mt-4">
                  <button
                    onClick={saveSelectedRenderServices}
                    disabled={selectedRenderServices.length === 0}
                    className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50"
                  >
                    💾 ذخیره و Deploy
                  </button>
                  <button
                    onClick={() => setShowServiceSelector(false)}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    لغو
                  </button>
                </div>

                <p className="text-xs text-gray-400 mt-3">
                  💡 این انتخاب ذخیره میشه و دیگه نیازی به انتخاب مجدد نیست.
                  برای تغییر، از تنظیمات Deploy استفاده کنید.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 🆕 مدال ایجاد سرویس Render */}
        {showCreateRenderService && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full">
              <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
                <h3 className="font-bold flex items-center gap-2">
                  <span>🚀</span> ایجاد سرویس Render
                </h3>
                <button onClick={() => setShowCreateRenderService(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">✕</button>
              </div>
              <div className="p-4 space-y-4">
                {project?.metadata?.source_url && (
                  <div className="p-2 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs">
                    <span className="opacity-60">ریپو: </span>
                    <span className="font-mono">{project.metadata.source_url.replace('https://github.com/', '')}</span>
                  </div>
                )}

                <p className="text-sm text-gray-600 dark:text-gray-400">
                  روش ایجاد سرویس را انتخاب کنید:
                </p>

                {/* گزینه رایگان */}
                <button
                  onClick={() => {
                    const repoUrl = project?.metadata?.source_url || '';
                    const renderUrl = repoUrl
                      ? `https://dashboard.render.com/select-repo?type=web&q=${encodeURIComponent(repoUrl.replace('https://github.com/', ''))}`
                      : 'https://dashboard.render.com/select-repo?type=web';
                    window.open(renderUrl, '_blank');
                    setShowCreateRenderService(false);
                  }}
                  className="w-full p-4 rounded-xl border-2 border-green-200 dark:border-green-800 hover:border-green-500 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition-all text-right"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🆓</span>
                    <div className="flex-1">
                      <div className="font-bold text-green-700 dark:text-green-400">پلن رایگان (Free)</div>
                      <p className="text-xs text-gray-500 mt-1">
                        به داشبورد Render منتقل می‌شوید. بعد از ایجاد، دکمه پاور را بزنید.
                      </p>
                    </div>
                    <span className="text-gray-400">↗</span>
                  </div>
                </button>

                {/* گزینه پولی - هوشمند */}
                <button
                  onClick={() => createRenderServiceSmart()}
                  disabled={createRenderLoading}
                  className="w-full p-4 rounded-xl border-2 border-orange-200 dark:border-orange-800 hover:border-orange-500 dark:hover:border-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-all text-right disabled:opacity-50"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{createRenderLoading ? '⏳' : '💎'}</span>
                    <div className="flex-1">
                      <div className="font-bold text-orange-700 dark:text-orange-400">
                        ایجاد خودکار با AI (Starter - $7/ماه)
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {createRenderLoading
                          ? '🤖 AI در حال تحلیل ساختار پروژه و ایجاد سرویس‌ها...'
                          : 'مدل هوش مصنوعی ساختار پروژه رو بررسی میکنه و سرویس‌ها رو دقیق ایجاد میکنه. نتیجه در چت دستیار نمایش داده میشه.'}
                      </p>
                    </div>
                    {!createRenderLoading && <span className="text-gray-400">⚡</span>}
                  </div>
                </button>

                <p className="text-[11px] text-gray-400 text-center">
                  💡 ایجاد خودکار: ساختار ریپو بررسی شده، سرویس‌ها با تنظیمات صحیح ایجاد می‌شوند.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 🆕 مدال پرامپت‌های راه‌اندازی خودکار */}
        {showAutoSetupPrompts && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="sticky top-0 bg-white dark:bg-gray-800 p-4 border-b flex items-center justify-between">
                <h3 className="font-bold text-xl flex items-center gap-2">
                  <span className="text-2xl">📝</span>
                  پرامپت‌های راه‌اندازی خودکار
                </h3>
                <button
                  onClick={() => setShowAutoSetupPrompts(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
              <div className="p-4">
                <PromptManager
                  category="auto_setup"
                  projectId={projectId}
                  showExecutionStatus={true}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
