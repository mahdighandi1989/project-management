'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
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
  const [activeTab, setActiveTab] = useState<'files' | 'memory' | 'structure' | 'journal'>('files');

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
  const [journalSubTab, setJournalSubTab] = useState<'logs' | 'reports'>('logs');

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

  // Edit Field
  const [editingField, setEditingField] = useState<string | null>(null);

  // AI Chat State
  const [chatPrompt, setChatPrompt] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedChatModel, setSelectedChatModel] = useState('openai');
  const [includeMemory, setIncludeMemory] = useState(true);
  const [showChatBox, setShowChatBox] = useState(false);

  useEffect(() => {
    if (projectId) {
      loadProject();
      loadMemory();
    }
  }, [projectId]);

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

  // بارگذاری ساختار پروژه
  const loadStructure = async () => {
    setStructureLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/structure`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setStructureData(data.structure);
          setStructureSettings(data.settings);
          // تبدیل به فرمت React Flow
          convertToReactFlow(data.structure);
        }
      }
    } catch (e) {
      console.error('Error loading structure:', e);
    } finally {
      setStructureLoading(false);
    }
  };

  // تبدیل داده‌ها به فرمت React Flow
  const convertToReactFlow = (structure: ProjectStructure) => {
    const flowNodes: Node[] = structure.nodes.map((node) => ({
      id: node.id,
      type: 'default',
      position: node.position,
      data: {
        label: (
          <div className={`text-center ${node.is_active ? 'animate-pulse' : ''}`}>
            <div className="font-bold">{node.label}</div>
            {node.description && (
              <div className="text-xs opacity-70 mt-1">{node.description}</div>
            )}
          </div>
        ),
      },
      style: {
        background: node.style?.background || '#6366f1',
        color: node.style?.color || 'white',
        border: node.is_active ? '3px solid #22c55e' : '1px solid #4b5563',
        borderRadius: '8px',
        padding: '10px',
        fontSize: node.style?.fontSize || '14px',
        fontWeight: node.style?.fontWeight || 'normal',
        boxShadow: node.is_active ? '0 0 15px #22c55e' : '0 2px 4px rgba(0,0,0,0.2)',
      },
    }));

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
        convertToReactFlow(data.structure);
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

  // ===================== پایان توابع ژورنال =====================

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
        loadProjectMemory();
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
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}/trigger/execute`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess(`تریگر "${data.field_name}" اجرا شد`);
        loadMemory();
        // نمایش نتایج در console
        console.log('Trigger execution results:', data.results);
      } else {
        showError(data.detail || 'خطا در اجرای تریگر');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setExecutingTrigger(null);
    }
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

              {/* لیست فیلدها */}
              <div className="space-y-3 max-h-[50vh] overflow-auto">
                {dynamicFields.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <div className="text-4xl mb-2">📭</div>
                    <p>فیلدی تعریف نشده</p>
                  </div>
                ) : (
                  dynamicFields.map((field) => (
                    <div
                      key={field.id}
                      className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
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
                            <span className="font-medium">{field.name}</span>
                            <div className="flex gap-1">
                              <button
                                onClick={() => setEditingField(field.id)}
                                className="p-1 text-blue-500 hover:bg-blue-100 rounded"
                                title="ویرایش"
                              >
                                ✏️
                              </button>
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
                          <div className="mt-2 flex flex-wrap gap-1">
                            {field.target_models.map(m => {
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

                          {/* تریگر کنترل‌ها */}
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
                                      i => i.value === field.trigger?.interval_minutes && i.type === field.trigger?.interval_type
                                    )?.label || `هر ${field.trigger?.interval_minutes} دقیقه`})
                                  </span>
                                )}
                              </div>

                              <button
                                onClick={() => executeFieldTrigger(field.id)}
                                disabled={executingTrigger === field.id}
                                className="px-3 py-1 bg-orange-500 text-white rounded text-xs hover:bg-orange-600 disabled:opacity-50 flex items-center gap-1"
                                title="اجرای دستی تریگر"
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
                          </div>
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
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside mr-4">
                <li>نودهای سبز: نقاط ورودی و فایل‌های اصلی</li>
                <li>نودهای بنفش: پوشه‌ها و دایرکتوری‌ها</li>
                <li>نودهای سبز روشن: فایل‌ها</li>
                <li>خطوط متحرک: اتصالات فعال و جریان داده</li>
                <li>نودهای چشمک‌زن: فرآیندهای در حال اجرا</li>
                <li>با ماوس می‌توانید نودها را جابه‌جا کنید و زوم کنید</li>
              </ul>
            </div>
          </div>
        )}

        {/* محتوای تب ژورنال و گزارشات */}
        {activeTab === 'journal' && (
          <div className="space-y-6">
            {/* سابتب‌ها */}
            <div className="flex gap-2 bg-white dark:bg-gray-800 rounded-xl p-2">
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
                    <button
                      onClick={() => generateReport(7)}
                      disabled={generatingReport}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                    >
                      {generatingReport ? '⏳ در حال تولید...' : '📝 تولید گزارش ۷ روزه'}
                    </button>
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
                      <button
                        onClick={() => generateReport(7)}
                        disabled={generatingReport}
                        className="mt-4 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                      >
                        📝 اولین گزارش را بسازید
                      </button>
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

                    {selectedReport.content && (
                      <div>
                        <h4 className="font-medium text-sm text-gray-500 mb-1">جزئیات:</h4>
                        <pre className="p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm overflow-auto max-h-64 whitespace-pre-wrap">
                          {selectedReport.content}
                        </pre>
                      </div>
                    )}

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
      </div>
    </div>
  );
}
