'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import ProjectHealthPanel from '@/components/ProjectHealthPanel';
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
  const [activeTab, setActiveTab] = useState<'files' | 'memory' | 'structure' | 'journal' | 'health'>('files');

  // Journal & Reports State
  const [journalLogs, setJournalLogs] = useState<ActivityLog[]>([]);
  const [journalStats, setJournalStats] = useState<JournalStats | null>(null);
  const [journalLoading, setJournalLoading] = useState(false);
  const [journalPage, setJournalPage] = useState(1);
  const [journalTotal, setJournalTotal] = useState(0);
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
  const [journalSubTab, setJournalSubTab] = useState<'logs' | 'reports' | 'validation' | 'profiles'>('logs');

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

  // آپلود پیوست
  const [uploadingAttachment, setUploadingAttachment] = useState<string | null>(null);

  // Edit Field
  const [editingField, setEditingField] = useState<string | null>(null);

  // AI Chat State
  const [chatPrompt, setChatPrompt] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedChatModel, setSelectedChatModel] = useState('openai');
  const [includeMemory, setIncludeMemory] = useState(true);
  const [showChatBox, setShowChatBox] = useState(false);

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

  useEffect(() => {
    if (projectId) {
      loadProject();
      loadMemory();
      loadSyncSettings();
    }
  }, [projectId]);

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

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

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
          setJournalTotal(data.pagination.total);
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

  // بارگذاری جزئیات یک فعالیت
  const loadActivityDetail = async (logId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/journal/${logId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSelectedLog(data.activity);
        }
      }
    } catch (e) {
      showError('خطا در بارگذاری جزئیات');
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
    if (!confirm('تولید گزارش مهندسی جامع؟\n\nاین گزارش شامل:\n• تحلیل کامل ساختار پروژه\n• 🔍 اعتبارسنجی نتایج تحلیل سلامت (تایید/رد ایرادات)\n• شناسایی باگ‌ها و مشکلات\n• پیشنهادات بهبود\n• نقشه راه توسعه\n• تولید خودکار فیلدها برای ایرادات تایید شده\n\nاین عملیات ممکن است چند دقیقه طول بکشد.')) {
      return;
    }

    setGeneratingReport(true);
    showSuccess('در حال تحلیل پروژه و تولید گزارش مهندسی... لطفاً صبر کنید');

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/reports/generate-engineering?days=${days}&model_id=claude&auto_create_fields=true&validate_health_issues=true`, {
        method: 'POST',
      });
      const data = await res.json();

      if (data.success) {
        let successMsg = `✅ گزارش مهندسی تولید شد`;

        if (data.project_health_score) {
          successMsg += ` | امتیاز سلامت: ${data.project_health_score}%`;
        }
        if (data.bugs_found > 0) {
          successMsg += ` | ${data.bugs_found} باگ شناسایی شد`;
        }
        if (data.fields_count > 0) {
          successMsg += ` | ${data.fields_count} فیلد جدید ایجاد شد`;
        }
        // 🆕 نمایش نتایج اعتبارسنجی health analysis
        if (data.validation_results) {
          const vr = data.validation_results;
          if (vr.issues_reviewed > 0) {
            successMsg += ` | اعتبارسنجی: ${vr.validated_count} تایید، ${vr.rejected_count} رد`;
          }
        }

        showSuccess(successMsg);
        loadReports();

        // اگر فیلد جدید ایجاد شد، حافظه رو هم ریلود کن
        if (data.fields_count > 0) {
          loadMemory();
        }
      } else {
        showError(data.error || 'خطا در تولید گزارش');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setGeneratingReport(false);
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

  // راه‌اندازی خودکار حافظه و فیلدهای پویا
  const runAutoSetup = async () => {
    if (!confirm('راه‌اندازی خودکار تنظیمات حافظه و فیلدهای پویا؟\n\nاین عملیات بر اساس تحلیل AI از فایل‌های پروژه انجام می‌شود و تنظیمات فعلی را جایگزین می‌کند.')) {
      return;
    }

    setRunningAutoSetup(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/auto-setup?use_ai=true`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(`راه‌اندازی خودکار انجام شد! نوع تشخیص داده شده: ${data.detected_type || 'عمومی'}`);
        // بارگذاری مجدد اطلاعات حافظه
        loadMemory();
      } else {
        showError(data.detail || 'خطا در راه‌اندازی خودکار');
      }
    } catch (e) {
      showError('خطا در ارتباط');
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

  // ذخیره سرویس‌های Render انتخاب شده
  const saveSelectedRenderServices = async () => {
    if (selectedRenderServices.length === 0) {
      showError('لطفاً حداقل یک سرویس انتخاب کنید');
      return;
    }

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
        showSuccess(`✅ ${selectedRenderServices.length} سرویس ذخیره شد. حالا Deploy را بزنید.`);
        setShowServiceSelector(false);
        setSavedRenderServices(availableRenderServices.filter(s => selectedRenderServices.includes(s.id)));
      } else {
        showError(data.error || 'خطا در ذخیره');
      }
    } catch {
      showError('خطا در ارتباط');
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

    try {
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
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setChatLoading(false);
    }
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
                  </div>
                  <span className="text-gray-400">{showChatBox ? '▲' : '▼'}</span>
                </div>

                {/* محتوای چت */}
                {showChatBox && (
                  <div className="p-4 border-t dark:border-gray-700">
                    {/* انتخاب مدل */}
                    <div className="flex flex-wrap items-center gap-3 mb-4">
                      <label className="text-sm text-gray-600 dark:text-gray-400">مدل:</label>
                      <select
                        value={selectedChatModel}
                        onChange={(e) => setSelectedChatModel(e.target.value)}
                        className="px-3 py-1 border rounded-lg text-sm dark:bg-gray-700 dark:border-gray-600"
                      >
                        {availableModels.filter(m => m.id !== 'all').map(model => (
                          <option key={model.id} value={model.id}>
                            {model.icon} {model.name}
                          </option>
                        ))}
                      </select>

                      <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <input
                          type="checkbox"
                          checked={includeMemory}
                          onChange={(e) => setIncludeMemory(e.target.checked)}
                          className="rounded"
                        />
                        استفاده از دستورات حافظه
                      </label>
                    </div>

                    {/* ورودی پرامپت */}
                    <div className="flex gap-2">
                      <textarea
                        value={chatPrompt}
                        onChange={(e) => setChatPrompt(e.target.value)}
                        placeholder="سوال خود را درباره پروژه بپرسید... مثلاً: این پروژه چه کاری انجام می‌دهد؟ یا: چگونه یک فیچر جدید اضافه کنم؟"
                        className="flex-1 p-3 border rounded-lg resize-none dark:bg-gray-700 dark:border-gray-600 text-sm"
                        rows={2}
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
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 self-end"
                      >
                        {chatLoading ? '⏳' : '📤 ارسال'}
                      </button>
                    </div>

                    {/* پاسخ AI */}
                    {(chatResponse || chatLoading) && (
                      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
                          <span>🤖</span>
                          <span>پاسخ {availableModels.find(m => m.id === selectedChatModel)?.name || selectedChatModel}:</span>
                        </div>
                        {chatLoading ? (
                          <div className="flex items-center gap-2 text-gray-400">
                            <div className="animate-spin">⏳</div>
                            <span>در حال پردازش...</span>
                          </div>
                        ) : (
                          <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap">
                            {chatResponse}
                          </div>
                        )}
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
            {/* دکمه راه‌اندازی خودکار */}
            <div className="bg-gradient-to-r from-purple-500 to-blue-500 rounded-xl shadow p-4 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-lg">🤖 راه‌اندازی خودکار با AI</h3>
                  <p className="text-sm opacity-90">
                    تحلیل هوشمند پروژه و تولید دستورات و فیلدهای مناسب
                  </p>
                </div>
                <button
                  onClick={runAutoSetup}
                  disabled={runningAutoSetup}
                  className="px-4 py-2 bg-white text-purple-600 rounded-lg font-medium hover:bg-gray-100 disabled:opacity-50"
                >
                  {runningAutoSetup ? '⏳ در حال تحلیل...' : '✨ راه‌اندازی خودکار'}
                </button>
              </div>
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
                </div>
                <button
                  onClick={() => setShowNewFieldForm(true)}
                  className="px-3 py-1 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600"
                >
                  + افزودن فیلد
                </button>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                دستورات متغیر که ممکن است زود به زود تغییر کنند
              </p>

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
                          <button
                            onClick={executeBatchFields}
                            disabled={executingBatch}
                            className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 disabled:opacity-50 flex items-center gap-2"
                          >
                            {executingBatch ? (
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
                  <p className="text-xs text-gray-500 mt-2">
                    💡 فیلدها بر اساس اولویت مرتب و اجرا می‌شوند (اولویت ۱ = بالاترین)
                  </p>
                </div>
              )}

              {/* فیلتر و لیست فیلدها */}
              {dynamicFields.some((f: any) => f.archived) && (
                <div className="mb-3 flex items-center gap-2">
                  <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <input
                      type="checkbox"
                      checked={showArchivedFields}
                      onChange={(e) => setShowArchivedFields(e.target.checked)}
                      className="rounded"
                    />
                    📦 نمایش فیلدهای بایگانی شده ({dynamicFields.filter((f: any) => f.archived).length})
                  </label>
                </div>
              )}

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
            </div>

            {/* آمار کلی */}
            {journalStats && (
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-blue-500">{journalStats.total_activities}</div>
                  <div className="text-sm text-gray-500">فعالیت (۳۰ روز)</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-green-500">{journalStats.total_tokens.toLocaleString()}</div>
                  <div className="text-sm text-gray-500">توکن مصرفی</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-purple-500">{journalStats.avg_latency_ms}ms</div>
                  <div className="text-sm text-gray-500">میانگین تأخیر</div>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow">
                  <div className="text-3xl font-bold text-emerald-500">{journalStats.success_rate}%</div>
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
                          onClick={() => loadReportDetail(report.id)}
                          className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h3 className="font-medium">{report.title}</h3>
                            <span className="text-xs text-gray-500">
                              {report.created_at ? new Date(report.created_at).toLocaleString('fa-IR') : ''}
                            </span>
                          </div>
                          {report.summary && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                              {report.summary}
                            </p>
                          )}
                          <div className="flex gap-3 text-xs text-gray-500">
                            <span>{report.total_activities} فعالیت</span>
                            <span>{report.total_tokens.toLocaleString()} توکن</span>
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
                          <span className="text-2xl font-bold text-blue-500">{profile.overall_score}</span>
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
                                <div className="font-medium text-green-500">{profile.accuracy_score}</div>
                              </div>
                              <div className="text-center">
                                <div className="text-xs text-gray-500">سرعت</div>
                                <div className="font-medium text-blue-500">{profile.speed_score}</div>
                              </div>
                              <div className="text-center">
                                <div className="text-xs text-gray-500">کامل‌بودن</div>
                                <div className="font-medium text-purple-500">{profile.completeness_score}</div>
                              </div>
                              <div className="text-center border-r pr-4 dark:border-gray-600">
                                <div className="text-xs text-gray-500">نمره کل</div>
                                <div className="text-2xl font-bold text-blue-600">{profile.overall_score}</div>
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
                        <div className="text-2xl font-bold text-green-500">{selectedReport.total_tokens.toLocaleString()}</div>
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
                      } catch (e) {
                        // اگر JSON نیست، به صورت متن نمایش بده
                      }

                      if (!parsed) {
                        return (
                          <div>
                            <h4 className="font-medium text-sm text-gray-500 mb-1">جزئیات:</h4>
                            <pre className="p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm overflow-auto max-h-64 whitespace-pre-wrap">
                              {selectedReport.content}
                            </pre>
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
      </div>
    </div>
  );
}
