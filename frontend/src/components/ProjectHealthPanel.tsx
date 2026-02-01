'use client';

import { useState, useEffect } from 'react';
import HealthDiagram from './HealthDiagram';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface HealthScores {
  overall: number;
  overall_color: string;
  file_scores: {
    code_quality: number;
    documentation: number;
    security: number;
    cooperation: number;
    roadmap_compliance: number;
  };
  structure_score: number;
}

interface FileHealth {
  score: number;
  color: string;
  hex: string;
  models_analyzed: number;
  analyzed_at: string;
  model_scores: Record<string, number>;
}

interface AnalysisSettings {
  instruction: string;
  target_models: string[];
  trigger_enabled: boolean;
  trigger_interval_minutes: number;
  trigger_interval_type: string;
  criteria_weights: Record<string, number>;
  depth: 'quick' | 'standard' | 'deep' | 'thorough';  // 🆕 عمق تحلیل
}

interface Issue {
  id?: string;  // شناسه یکتا برای issue
  file?: string;
  severity: string;
  message: string;
  line?: number;
  model?: string;
  converted_to_field?: boolean;  // آیا به فیلد پویا تبدیل شده؟
  converted_field_id?: string;  // شناسه فیلد ایجاد شده
  converted_at?: string;  // زمان تبدیل
  archived?: boolean;  // آیا بایگانی شده؟
  archived_at?: string;  // زمان بایگانی
  archived_reason?: string;  // دلیل بایگانی: approved, rejected, engineering_report_completed, etc.
}

interface AvailableModel {
  id: string;
  name: string;
  provider: string;
}

interface Props {
  projectId: string;
  onHealthUpdate?: () => void;
}

export default function ProjectHealthPanel({ projectId, onHealthUpdate }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'settings' | 'files' | 'issues' | 'archive' | 'validation' | 'security' | 'coverage'>('overview');
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Data states
  const [healthScores, setHealthScores] = useState<HealthScores | null>(null);
  const [fileHealthMap, setFileHealthMap] = useState<Record<string, FileHealth>>({});
  const [settings, setSettings] = useState<AnalysisSettings | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [roadmap, setRoadmap] = useState('');
  const [readme, setReadme] = useState('');
  const [idealState, setIdealState] = useState('');
  const [lastAnalysis, setLastAnalysis] = useState<{ id: string; at: string; models: string[] } | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);

  // 🆕 Validation Chain states
  const [validationChainStatus, setValidationChainStatus] = useState<{
    health_analysis: { scores: any; total_issues: number; last_analysis: string | null; models_used: string[] };
    validation: { last_validated: string | null; validator_model: string; total_reviewed: number; validated_count: number; rejected_count: number; summary: string };
    fields: { total_active: number; validated_fields: number; unexecuted_fields: number; archived_fields: number };
    rejected_archive: { total: number; recent: any[] };
    ideal_state: { defined: boolean; preview: string };
    roadmap: { defined: boolean; preview: string };
  } | null>(null);
  const [rejectedIssues, setRejectedIssues] = useState<any[]>([]);
  const [loadingValidation, setLoadingValidation] = useState(false);
  const [convertingIssue, setConvertingIssue] = useState<string | null>(null);  // شناسه issue در حال تبدیل

  // Security & Coverage states
  const [securityData, setSecurityData] = useState<{
    security_score: number;
    secrets: { count: number; findings: any[] };
    license: { has_license: boolean; licenses: any[] };
    sensitive_files: { count: number; findings: any[] };
    dependencies: { vulnerability_count: number; vulnerabilities: any[] };
  } | null>(null);
  const [coverageData, setCoverageData] = useState<{
    summary: {
      total_test_files: number;
      total_source_files: number;
      total_tests: number;
      coverage_percent: number;
      untested_file_count: number;
    };
    untested_files: any[];
    recommendations: any[];
    health_score: number;
  } | null>(null);
  const [loadingSecurity, setLoadingSecurity] = useState(false);
  const [loadingCoverage, setLoadingCoverage] = useState(false);

  // Edit states
  const [editingSettings, setEditingSettings] = useState(false);
  const [tempSettings, setTempSettings] = useState<AnalysisSettings | null>(null);

  // Status states
  const [hasRealData, setHasRealData] = useState(false);
  const [analysisLog, setAnalysisLog] = useState<string[]>([]);

  // Progress tracking state
  const [progressData, setProgressData] = useState<{
    status: string;
    phase: string;
    current_file: string;
    current_model: string;
    analyzed_files: number;
    total_files: number;
    progress_percentage: number;
    percentage: number;
    elapsed_time: number;
    issues_found: number;
    message: string;
    model_statuses: Record<string, string>;
    can_resume: boolean;
    error?: string;
  } | null>(null);
  const [showProgressDetails, setShowProgressDetails] = useState(false);
  const [pollingInterval, setPollingIntervalState] = useState<NodeJS.Timeout | null>(null);

  // Messages
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    // Only run if projectId is valid
    if (!projectId) return;

    loadAllData();
    loadAvailableModels();
    checkAnalysisStatus();
    // بررسی وضعیت تحلیل در حال اجرا
    pollProgress();

    return () => {
      // پاک‌سازی interval در هنگام unmount
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [projectId]);

  // شروع polling خودکار وقتی تحلیل در حال اجراست
  useEffect(() => {
    if (progressData?.status === 'running') {
      if (!pollingInterval) {
        const interval = setInterval(pollProgress, 2000); // هر 2 ثانیه
        setPollingIntervalState(interval);
      }
    } else {
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingIntervalState(null);
      }
    }
  }, [progressData?.status]);

  const checkAnalysisStatus = async () => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/status`);
      if (res.ok) {
        const data = await res.json();
        setHasRealData(data.has_analysis_data);
      }
    } catch (e) {
      console.error('Error checking status:', e);
    }
  };

  // Polling برای وضعیت پیشرفت - این باعث میشه حتی با جابجایی صفحه تحلیل قطع نشه
  const pollProgress = async () => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/progress`);
      if (res.ok) {
        const data = await res.json();
        const progress = data.progress;

        if (progress.status === 'running' || progress.status === 'paused') {
          setAnalyzing(progress.status === 'running');
          setProgressData({
            status: progress.status,
            phase: progress.phase || 'preparing',
            current_file: progress.current_file || '',
            current_model: progress.current_model || '',
            analyzed_files: progress.analyzed_files || 0,
            total_files: progress.total_files || 0,
            progress_percentage: progress.percentage || 0,
            percentage: progress.percentage || 0,
            elapsed_time: progress.elapsed_time || 0,
            issues_found: progress.issues_found || 0,
            message: progress.message || '',
            model_statuses: progress.model_statuses || {},
            can_resume: progress.can_resume || false,
            error: progress.error
          });
        } else if (progress.status === 'completed') {
          setAnalyzing(false);
          setProgressData(null);
          showSuccess('تحلیل کامل شد!');
          await loadAllData();
          await checkAnalysisStatus();
        } else if (progress.status === 'failed') {
          setAnalyzing(false);
          setProgressData({
            ...progress,
            status: 'failed',
            can_resume: progress.can_resume || false
          });
          showError(progress.error || 'خطا در تحلیل');
        } else if (progress.status === 'stopped') {
          setAnalyzing(false);
          setProgressData(null);
          showSuccess('تحلیل متوقف شد');
          await loadAllData();
        } else {
          // idle یا سایر
          setProgressData(null);
        }
      }
    } catch (e) {
      console.error('Error polling progress:', e);
    }
  };

  // توقف موقت تحلیل
  const pauseAnalysis = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/pause`, {
        method: 'POST'
      });
      if (res.ok) {
        showSuccess('تحلیل متوقف شد');
        pollProgress();
      } else {
        showError('خطا در توقف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  // ادامه تحلیل
  const resumeAnalysis = async () => {
    try {
      setAnalyzing(true);
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/resume`, {
        method: 'POST'
      });
      if (res.ok) {
        showSuccess('تحلیل ادامه یافت');
        pollProgress();
      } else {
        showError('خطا در ادامه تحلیل');
        setAnalyzing(false);
      }
    } catch (e) {
      showError('خطا در ارتباط');
      setAnalyzing(false);
    }
  };

  // توقف کامل تحلیل
  const stopAnalysis = async () => {
    if (!confirm('آیا مطمئنید؟ تحلیل متوقف شده و نتایج جزئی ذخیره می‌شوند.')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/stop`, {
        method: 'POST'
      });
      if (res.ok) {
        showSuccess('تحلیل متوقف شد');
        setAnalyzing(false);
        setProgressData(null);
        await loadAllData();
      } else {
        showError('خطا در توقف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const clearAnalysisData = async () => {
    if (!confirm('آیا مطمئنید؟ همه داده‌های تحلیل پاک خواهند شد.')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/clear`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showSuccess('داده‌های تحلیل پاک شدند');
        setHealthScores(null);
        setFileHealthMap({});
        setIssues([]);
        setIdealState('');
        setLastAnalysis(null);
        setHasRealData(false);
      } else {
        showError('خطا در پاک کردن داده‌ها');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const runDirectAnalysis = async () => {
    setAnalyzing(true);
    setAnalysisLog(['🚀 شروع تحلیل...']);

    try {
      // فیلتر کردن "all" از لیست مدل‌ها
      const selectedModels = (settings?.target_models || []).filter(m => m !== 'all');

      // شروع تحلیل با API معمولی (پس‌زمینه)
      // 🆕 اضافه کردن depth به درخواست
      const response = await fetch(`${API_BASE}/api/projects/${projectId}/health/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_ids: selectedModels,
          full_analysis: true,
          update_roadmap: true,
          update_readme: true,
          depth: settings?.depth || 'standard'  // 🆕 عمق تحلیل
        })
      });

      const data = await response.json();

      if (data.success) {
        setAnalysisLog(prev => [...prev, '✅ تحلیل شروع شد']);
        showSuccess('تحلیل شروع شد! وضعیت به‌روزرسانی می‌شود...');
        // شروع polling برای دریافت وضعیت
        pollProgress();
      } else {
        setAnalysisLog(prev => [...prev, `❌ خطا: ${data.error || data.detail}`]);
        showError(data.error || data.detail || 'خطا در شروع تحلیل');
        setAnalyzing(false);
      }
    } catch (e) {
      setAnalysisLog(prev => [...prev, `❌ خطای شبکه: ${e}`]);
      showError('خطا در ارتباط با سرور');
      setAnalyzing(false);
    }
  };

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 3000);
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadHealth(),
        loadSettings(),
        loadFileMap(),
        loadRoadmap(),
        loadIssues(),
        loadValidationChainStatus()
      ]);
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setLoading(false);
    }
  };

  // 🆕 بارگذاری وضعیت زنجیره اعتبارسنجی
  const loadValidationChainStatus = async () => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/chain-status`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setValidationChainStatus(data.chain_status);
        }
      }
    } catch (e) {
      console.error('Error loading validation chain status:', e);
    }
  };

  // 🆕 بارگذاری ایرادات رد شده
  const loadRejectedIssues = async () => {
    if (!projectId) return;
    setLoadingValidation(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/rejected-issues`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setRejectedIssues(data.rejected_issues || []);
        }
      }
    } catch (e) {
      console.error('Error loading rejected issues:', e);
    } finally {
      setLoadingValidation(false);
    }
  };

  // 🆕 بازگرداندن ایراد رد شده
  const restoreRejectedIssue = async (issueId: string) => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/rejected-issues/${issueId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        showSuccess('ایراد به لیست فعال بازگردانده شد');
        loadRejectedIssues();
        loadValidationChainStatus();
        loadIssues();
      } else {
        showError('خطا در بازگرداندن ایراد');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    }
  };

  const loadAvailableModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/available`);
      if (res.ok) {
        const data = await res.json();
        // API میتونه یا آرایه برگردونه یا {models: [...]}
        const models = Array.isArray(data) ? data : (data.models || []);
        setAvailableModels(models);
        console.log('Loaded available models:', models.length);
      }
    } catch (e) {
      console.error('Error loading models:', e);
    }
  };

  const loadHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthScores(data.health?.scores || null);
        setFileHealthMap(data.health?.file_health_map || {});
        setLastAnalysis(data.last_analysis);
        setIdealState(data.ideal_state || '');
        setIssues(data.health?.issues_found || []);
      }
    } catch (e) {
      console.error('Error loading health:', e);
    }
  };

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(data.settings);
      }
    } catch (e) {
      console.error('Error loading settings:', e);
    }
  };

  const loadFileMap = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/file-map`);
      if (res.ok) {
        const data = await res.json();
        setFileHealthMap(data.file_map || {});
      }
    } catch (e) {
      console.error('Error loading file map:', e);
    }
  };

  const loadRoadmap = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/roadmap`);
      if (res.ok) {
        const data = await res.json();
        setRoadmap(data.roadmap_content || '');
        setIdealState(data.ideal_state || '');
      }
    } catch (e) {
      console.error('Error loading roadmap:', e);
    }
  };

  const loadIssues = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/issues`);
      if (res.ok) {
        const data = await res.json();
        setIssues(data.issues || []);
      }
    } catch (e) {
      console.error('Error loading issues:', e);
    }
  };

  // 🆕 تبدیل issue به فیلد پویا
  const convertIssueToField = async (issue: Issue, index: number) => {
    const issueId = issue.id || `issue_${index}`;
    setConvertingIssue(issueId);

    try {
      // تشخیص اولویت از severity
      const priorityMap: Record<string, number> = {
        'critical': 1,
        'high': 2,
        'medium': 4,
        'low': 6,
      };
      const priority = priorityMap[issue.severity] || 5;

      // تشخیص action_type
      const actionType = issue.file ? 'github_commit' : 'display';

      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `[${issue.severity.toUpperCase()}] ${issue.message.slice(0, 80)}`,
          value: `مشکل شناسایی شده:\n${issue.message}${issue.file ? `\n\nفایل: ${issue.file}` : ''}${issue.line ? `\nخط: ${issue.line}` : ''}${issue.model ? `\n\nشناسایی شده توسط: ${issue.model}` : ''}`,
          target_models: ['all'],
          field_type: 'temporary',
          priority: priority,
          action_type: actionType,
          target_path: issue.file || null,
          archive_after_run: true,
          source_issue_id: issueId,  // برای جلوگیری از تکرار
        }),
      });

      const data = await res.json();
      if (data.success || data.field_id) {
        // علامت‌گذاری issue به عنوان تبدیل شده
        const updatedIssues = [...issues];
        updatedIssues[index] = {
          ...issue,
          id: issueId,
          converted_to_field: true,
          converted_field_id: data.field_id,
          converted_at: new Date().toISOString(),
        };
        setIssues(updatedIssues);

        // ذخیره در backend
        await markIssueAsConverted(issueId, data.field_id);

        showSuccess('ایراد به فیلد پویا تبدیل شد');
      } else {
        showError(data.detail || 'خطا در تبدیل');
      }
    } catch (e) {
      console.error('Error converting issue:', e);
      showError('خطا در تبدیل ایراد به فیلد');
    } finally {
      setConvertingIssue(null);
    }
  };

  // علامت‌گذاری issue در backend
  const markIssueAsConverted = async (issueId: string, fieldId: string) => {
    try {
      await fetch(`${API_BASE}/api/projects/${projectId}/health/issues/${issueId}/mark-converted`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_id: fieldId }),
      });
    } catch (e) {
      console.error('Error marking issue as converted:', e);
    }
  };

  // تبدیل همه issues به فیلد (batch)
  const convertAllIssuesToFields = async () => {
    const unconvertedIssues = issues.filter(i => !i.converted_to_field);
    if (unconvertedIssues.length === 0) {
      showError('همه ایرادات قبلاً تبدیل شده‌اند');
      return;
    }

    setConvertingIssue('all');
    let convertedCount = 0;

    for (let i = 0; i < issues.length; i++) {
      if (!issues[i].converted_to_field) {
        await convertIssueToField(issues[i], i);
        convertedCount++;
        // کمی تاخیر بین درخواست‌ها
        await new Promise(r => setTimeout(r, 200));
      }
    }

    setConvertingIssue(null);
    showSuccess(`${convertedCount} ایراد به فیلد پویا تبدیل شد`);
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_ids: settings?.target_models || [],
          full_analysis: true,
          update_roadmap: true,
          update_readme: true,
          depth: settings?.depth || 'standard'  // 🆕 عمق تحلیل
        })
      });

      const data = await res.json();
      if (data.success) {
        showSuccess('تحلیل شروع شد! نتایج به زودی نمایش داده می‌شود');
        // Poll for results
        setTimeout(() => loadAllData(), 5000);
        setTimeout(() => loadAllData(), 15000);
        setTimeout(() => loadAllData(), 30000);
        if (onHealthUpdate) onHealthUpdate();
      } else {
        showError(data.detail || 'خطا در شروع تحلیل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setAnalyzing(false);
    }
  };

  const saveSettings = async () => {
    if (!tempSettings) return;

    // فیلتر کردن "all" از لیست مدل‌ها قبل از ذخیره
    const cleanedSettings = {
      ...tempSettings,
      target_models: tempSettings.target_models.filter(m => m !== 'all')
    };

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cleanedSettings)
      });

      if (res.ok) {
        setSettings(cleanedSettings);
        setEditingSettings(false);
        showSuccess('تنظیمات ذخیره شد');
      } else {
        showError('خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 90) return 'text-green-500';
    if (score >= 70) return 'text-yellow-500';
    if (score >= 50) return 'text-orange-500';
    return 'text-red-500';
  };

  const getScoreBg = (score: number): string => {
    if (score >= 90) return 'bg-green-500';
    if (score >= 70) return 'bg-yellow-500';
    if (score >= 50) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return 'bg-red-500 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-yellow-500 text-black';
      case 'low': return 'bg-blue-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 text-center">
        <div className="animate-spin text-3xl mb-2">*</div>
        <p className="text-gray-500">در حال بارگذاری...</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden" dir="rtl">
      {/* پیام‌ها */}
      {error && (
        <div className="absolute top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {error}
        </div>
      )}
      {success && (
        <div className="absolute top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {success}
        </div>
      )}

      {/* هدر */}
      <div className="bg-gradient-to-l from-blue-500 to-purple-600 text-white p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">تحلیل سلامت پروژه</h2>
            <p className="text-sm opacity-80">بررسی خودکار ساختار و کیفیت</p>
            {hasRealData ? (
              <span className="text-xs bg-green-500/50 px-2 py-0.5 rounded mt-1 inline-block">✓ داده واقعی</span>
            ) : (
              <span className="text-xs bg-yellow-500/50 px-2 py-0.5 rounded mt-1 inline-block">⚠ بدون تحلیل</span>
            )}
          </div>
          <div className="flex gap-2">
            {hasRealData && (
              <button
                onClick={clearAnalysisData}
                className="px-3 py-2 bg-red-500/30 rounded-lg hover:bg-red-500/50 text-sm"
                title="پاک کردن داده‌های تحلیل"
              >
                🗑️ پاک کردن
              </button>
            )}
            <button
              onClick={runDirectAnalysis}
              disabled={analyzing}
              className="px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30 disabled:opacity-50 flex items-center gap-2"
            >
              {analyzing ? (
                <>
                  <span className="animate-spin">⏳</span>
                  <span>در حال تحلیل...</span>
                </>
              ) : (
                <>
                  <span>🔬</span>
                  <span>شروع تحلیل</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* نوار پیشرفت Real-time با دکمه‌های کنترل */}
        {progressData && (progressData.status === 'running' || progressData.status === 'paused' || progressData.status === 'failed') && (
          <div className="mt-3">
            {/* نوار اصلی پیشرفت - کلیک‌پذیر */}
            <div
              onClick={() => setShowProgressDetails(!showProgressDetails)}
              className={`cursor-pointer rounded-lg p-3 relative overflow-hidden ${
                progressData.status === 'paused' ? 'bg-yellow-900/50' :
                progressData.status === 'failed' ? 'bg-red-900/50' :
                'bg-black/30'
              }`}
            >
              {/* نوار پیشرفت داخلی */}
              <div
                className={`absolute inset-0 transition-all duration-500 ${
                  progressData.status === 'paused' ? 'bg-yellow-500/30' :
                  progressData.status === 'failed' ? 'bg-red-500/30' :
                  'bg-white/20'
                }`}
                style={{ width: `${progressData.percentage || progressData.progress_percentage || 0}%` }}
              />

              <div className="relative z-10">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {progressData.status === 'running' && <span className="animate-pulse text-yellow-300">●</span>}
                    {progressData.status === 'paused' && <span className="text-yellow-300">⏸️</span>}
                    {progressData.status === 'failed' && <span className="text-red-300">❌</span>}
                    <span className="font-medium text-sm">
                      {progressData.status === 'paused' && 'متوقف شده - '}
                      {progressData.status === 'failed' && 'خطا - '}
                      {progressData.phase === 'micro' && 'بررسی فایل‌ها'}
                      {progressData.phase === 'macro' && 'بررسی همکاری‌ها'}
                      {progressData.phase === 'structural' && 'بررسی ساختار'}
                      {progressData.phase === 'finalizing' && 'نهایی‌سازی'}
                      {progressData.phase === 'preparing' && 'آماده‌سازی'}
                      {!progressData.phase && 'در حال تحلیل'}
                    </span>
                  </div>
                  <span className="font-mono text-lg font-bold">
                    {(progressData.percentage || progressData.progress_percentage || 0).toFixed(0)}%
                  </span>
                </div>

                <div className="text-xs opacity-90">
                  {progressData.current_model && (
                    <span className="inline-flex items-center gap-1 bg-white/20 px-2 py-0.5 rounded mr-2">
                      🤖 {progressData.current_model.split('/').pop()}
                    </span>
                  )}
                  {progressData.message && (
                    <span className="truncate">{progressData.message}</span>
                  )}
                  {progressData.error && (
                    <span className="text-red-300 truncate">{progressData.error}</span>
                  )}
                </div>

                <div className="flex items-center justify-between mt-1 text-xs opacity-75">
                  <span>فایل: {progressData.analyzed_files}/{progressData.total_files}</span>
                  <span>مشکلات: {progressData.issues_found}</span>
                  <span>{Math.floor(progressData.elapsed_time)}s</span>
                  <span className="hover:underline">
                    {showProgressDetails ? '▼' : '▲'} جزئیات
                  </span>
                </div>
              </div>
            </div>

            {/* دکمه‌های کنترل */}
            <div className="flex gap-2 mt-2">
              {progressData.status === 'running' && (
                <>
                  <button
                    onClick={(e) => { e.stopPropagation(); pauseAnalysis(); }}
                    className="flex-1 px-3 py-2 bg-yellow-500/30 rounded-lg hover:bg-yellow-500/50 text-sm flex items-center justify-center gap-2"
                  >
                    ⏸️ توقف موقت
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); stopAnalysis(); }}
                    className="flex-1 px-3 py-2 bg-red-500/30 rounded-lg hover:bg-red-500/50 text-sm flex items-center justify-center gap-2"
                  >
                    ⏹️ توقف کامل
                  </button>
                </>
              )}
              {(progressData.status === 'paused' || (progressData.status === 'failed' && progressData.can_resume)) && (
                <>
                  <button
                    onClick={(e) => { e.stopPropagation(); resumeAnalysis(); }}
                    className="flex-1 px-3 py-2 bg-green-500/30 rounded-lg hover:bg-green-500/50 text-sm flex items-center justify-center gap-2"
                  >
                    ▶️ ادامه تحلیل
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); stopAnalysis(); }}
                    className="flex-1 px-3 py-2 bg-red-500/30 rounded-lg hover:bg-red-500/50 text-sm flex items-center justify-center gap-2"
                  >
                    ⏹️ توقف کامل
                  </button>
                </>
              )}
            </div>

            {/* پنل جزئیات - نمایش با کلیک */}
            {showProgressDetails && (
              <div className="mt-2 bg-gray-900 text-gray-100 rounded-lg p-3 text-xs font-mono max-h-48 overflow-auto">
                <div className="mb-2 text-gray-400">وضعیت مدل‌ها:</div>
                <div className="grid grid-cols-2 gap-1">
                  {Object.entries(progressData.model_statuses || {}).map(([modelId, status]) => (
                    <div
                      key={modelId}
                      className={`p-1.5 rounded text-xs ${
                        status === 'working'
                          ? 'bg-yellow-500/30 text-yellow-300 animate-pulse'
                          : status === 'completed'
                          ? 'bg-green-500/30 text-green-300'
                          : status === 'failed'
                          ? 'bg-red-500/30 text-red-300'
                          : 'bg-gray-700 text-gray-400'
                      }`}
                    >
                      {status === 'working' && '⏳'}
                      {status === 'completed' && '✅'}
                      {status === 'failed' && '❌'}
                      {status === 'waiting' && '⏸️'}
                      {' '}{modelId.split('/').pop()}
                    </div>
                  ))}
                </div>

                {progressData.current_file && (
                  <div className="mt-2 pt-2 border-t border-gray-700">
                    <span className="text-gray-400">فایل: </span>
                    <span className="text-blue-300">{progressData.current_file}</span>
                  </div>
                )}

                {progressData.can_resume && progressData.status !== 'running' && (
                  <div className="mt-2 pt-2 border-t border-gray-700 text-green-400">
                    ✓ امکان ادامه از نقطه توقف وجود دارد
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* لاگ تحلیل (فقط وقتی progress نیست) */}
        {analysisLog.length > 0 && !progressData && (
          <div className="mt-3 bg-black/20 rounded-lg p-2 text-xs font-mono max-h-32 overflow-auto">
            {analysisLog.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
        )}
      </div>

      {/* تب‌ها */}
      <div className="flex border-b dark:border-gray-700 overflow-x-auto">
        {[
          { id: 'overview', label: 'نمای کلی', icon: '*' },
          { id: 'settings', label: 'تنظیمات', icon: '+' },
          { id: 'files', label: 'فایل‌ها', icon: '-' },
          { id: 'issues', label: `ایرادات (${issues.filter(i => !i.archived).length})`, icon: '!' },
          { id: 'archive', label: `بایگانی (${issues.filter(i => i.archived).length})`, icon: '📦' },
          { id: 'validation', label: 'زنجیره اعتبارسنجی', icon: '✓' },
          { id: 'security', label: 'امنیت', icon: '🔒' },
          { id: 'coverage', label: 'پوشش تست', icon: '🧪' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-3 font-medium whitespace-nowrap transition ${
              activeTab === tab.id
                ? 'border-b-2 border-blue-500 text-blue-500'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <span className="ml-1">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-6">
        {/* تب نمای کلی */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* هشدار اگر داده‌ای نیست */}
            {!hasRealData && (
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div>
                    <h4 className="font-bold text-yellow-800 dark:text-yellow-400">هیچ تحلیلی انجام نشده</h4>
                    <p className="text-sm text-yellow-700 dark:text-yellow-500">
                      برای مشاهده نمرات واقعی، دکمه "شروع تحلیل" را بزنید.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* نمره کلی */}
            <div className="flex items-center gap-6">
              <div className={`w-24 h-24 rounded-2xl flex items-center justify-center text-3xl font-bold text-white ${hasRealData ? getScoreBg(healthScores?.overall || 0) : 'bg-gray-400'}`}>
                {hasRealData ? (healthScores?.overall?.toFixed(0) || '0') : '?'}
              </div>
              <div>
                <h3 className="text-xl font-bold">نمره سلامت کلی</h3>
                <p className="text-gray-500 text-sm">
                  {lastAnalysis?.at
                    ? `آخرین تحلیل: ${new Date(lastAnalysis.at).toLocaleString('fa-IR')}`
                    : 'هنوز تحلیلی انجام نشده'}
                </p>
                {lastAnalysis?.models && lastAnalysis.models.length > 0 && (
                  <p className="text-xs text-gray-400 mt-1">
                    مدل‌ها: {lastAnalysis.models.join(', ')}
                  </p>
                )}
              </div>
            </div>

            {/* نمرات جزئی */}
            {healthScores?.file_scores && (
              <div className="grid grid-cols-5 gap-4">
                {[
                  { key: 'code_quality', label: 'کیفیت کد' },
                  { key: 'documentation', label: 'مستندات' },
                  { key: 'security', label: 'امنیت' },
                  { key: 'cooperation', label: 'همکاری' },
                  { key: 'roadmap_compliance', label: 'نقشه راه' },
                ].map((item) => {
                  const score = (healthScores.file_scores as any)[item.key] || 0;
                  return (
                    <div key={item.key} className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">{item.label}</div>
                      <div className={`text-2xl font-bold ${getScoreColor(score)}`}>
                        {score.toFixed(0)}%
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* حالت ایده‌آل */}
            {idealState && (
              <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800">
                <h4 className="font-bold text-blue-700 dark:text-blue-300 mb-2">حالت ایده‌آل پروژه</h4>
                <p className="text-sm text-blue-600 dark:text-blue-400 whitespace-pre-wrap">
                  {idealState}
                </p>
              </div>
            )}

            {/* آمار سریع */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                <div className="text-2xl font-bold">{Object.keys(fileHealthMap).length}</div>
                <div className="text-sm text-gray-500">فایل تحلیل‌شده</div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                <div className="text-2xl font-bold text-red-500">{issues.length}</div>
                <div className="text-sm text-gray-500">ایراد شناسایی‌شده</div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                <div className="text-2xl font-bold">{healthScores?.structure_score?.toFixed(0) || 0}%</div>
                <div className="text-sm text-gray-500">نمره ساختار</div>
              </div>
            </div>
          </div>
        )}

        {/* تب تنظیمات */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            {!editingSettings ? (
              <>
                <div className="flex justify-between items-center">
                  <h3 className="font-bold">تنظیمات تحلیل</h3>
                  <button
                    onClick={() => {
                      setTempSettings(settings);
                      setEditingSettings(true);
                    }}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    ویرایش
                  </button>
                </div>

                {settings && (
                  <div className="space-y-4">
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">دستورات تحلیل (Prompt)</div>
                      <p className="font-mono text-sm">{settings.instruction}</p>
                    </div>

                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">مدل‌های منتخب</div>
                      <div className="flex flex-wrap gap-2">
                        {(() => {
                          // فیلتر کردن "all" از لیست مدل‌ها
                          const selectedModels = settings.target_models.filter(m => m !== 'all');
                          if (selectedModels.length === 0) {
                            return (
                              <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded text-sm">
                                ✓ همه مدل‌های در دسترس ({availableModels.length} مدل)
                              </span>
                            );
                          }
                          return selectedModels.map((m) => (
                            <span key={m} className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded text-sm">
                              {availableModels.find(am => am.id === m)?.name || m}
                            </span>
                          ));
                        })()}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="text-sm text-gray-500 mb-1">عمق تحلیل</div>
                        <p className="font-medium">
                          {{
                            'quick': '⚡ سریع (۱-۲ دقیقه)',
                            'standard': '📊 استاندارد (۳-۵ دقیقه)',
                            'deep': '🔬 عمیق (۱۰-۲۰ دقیقه)',
                            'thorough': '🔍 کامل (۳۰+ دقیقه)'
                          }[settings.depth] || '📊 استاندارد'}
                        </p>
                      </div>
                      <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="text-sm text-gray-500 mb-1">زمان‌بندی</div>
                        <p>
                          {settings.trigger_enabled
                            ? `هر ${settings.trigger_interval_minutes} ${settings.trigger_interval_type === 'minutes' ? 'دقیقه' : 'ساعت'}`
                            : 'غیرفعال'}
                        </p>
                      </div>
                      <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="text-sm text-gray-500 mb-1">وزن معیارها</div>
                        <div className="text-xs space-y-1">
                          {Object.entries(settings.criteria_weights || {}).map(([key, val]) => (
                            <div key={key} className="flex justify-between">
                              <span>{key}</span>
                              <span>{((val as number) * 100).toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="flex justify-between items-center">
                  <h3 className="font-bold">ویرایش تنظیمات</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditingSettings(false)}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-600 rounded-lg"
                    >
                      انصراف
                    </button>
                    <button
                      onClick={saveSettings}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                    >
                      ذخیره
                    </button>
                  </div>
                </div>

                {tempSettings && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">دستورات تحلیل (Prompt قوی)</label>
                      <textarea
                        value={tempSettings.instruction}
                        onChange={(e) => setTempSettings({ ...tempSettings, instruction: e.target.value })}
                        rows={4}
                        className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 font-mono text-sm"
                        placeholder="دستورات دقیق برای تحلیل پروژه..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">مدل‌های منتخب برای تحلیل</label>
                      <p className="text-xs text-gray-500 mb-3">
                        مدل‌هایی که می‌خواهید در تحلیل شرکت کنند را انتخاب کنید. خالی = همه مدل‌ها
                      </p>

                      {availableModels.length === 0 ? (
                        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-center">
                          <p className="text-yellow-700 dark:text-yellow-300">
                            هیچ مدلی در دسترس نیست!
                          </p>
                          <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                            لطفاً API key ها را در تنظیمات وارد کنید
                          </p>
                        </div>
                      ) : (
                        <>
                          {/* دکمه‌های انتخاب سریع */}
                          <div className="flex gap-2 mb-3">
                            <button
                              onClick={() => setTempSettings({ ...tempSettings, target_models: [] })}
                              className={`px-3 py-1 rounded text-xs ${
                                tempSettings.target_models.length === 0
                                  ? 'bg-green-500 text-white'
                                  : 'bg-gray-100 dark:bg-gray-700'
                              }`}
                            >
                              همه مدل‌ها
                            </button>
                            <button
                              onClick={() => setTempSettings({
                                ...tempSettings,
                                target_models: availableModels.map(m => m.id)
                              })}
                              className="px-3 py-1 rounded text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200"
                            >
                              انتخاب همه ({availableModels.length})
                            </button>
                            <button
                              onClick={() => setTempSettings({ ...tempSettings, target_models: [] })}
                              className="px-3 py-1 rounded text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200"
                            >
                              پاک کردن انتخاب
                            </button>
                          </div>

                          {/* لیست مدل‌ها به تفکیک provider */}
                          <div className="space-y-3 max-h-64 overflow-auto">
                            {/* گروه‌بندی بر اساس provider */}
                            {Array.from(new Set(availableModels.map(m => m.provider))).map(provider => (
                              <div key={provider} className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                <div className="text-xs font-bold text-gray-500 mb-2 flex items-center gap-2">
                                  <span className={`px-2 py-0.5 rounded ${
                                    provider === 'openai' ? 'bg-green-100 text-green-700' :
                                    provider === 'claude' ? 'bg-purple-100 text-purple-700' :
                                    provider === 'gemini' ? 'bg-blue-100 text-blue-700' :
                                    'bg-gray-100 text-gray-700'
                                  }`}>
                                    {provider}
                                  </span>
                                  <span>({availableModels.filter(m => m.provider === provider).length} مدل)</span>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {availableModels
                                    .filter(m => m.provider === provider)
                                    .map((model) => (
                                      <button
                                        key={model.id}
                                        onClick={() => {
                                          const models = tempSettings.target_models.includes(model.id)
                                            ? tempSettings.target_models.filter((m) => m !== model.id)
                                            : [...tempSettings.target_models, model.id];
                                          setTempSettings({ ...tempSettings, target_models: models });
                                        }}
                                        className={`px-2 py-1 rounded text-xs transition ${
                                          tempSettings.target_models.length === 0 ||
                                          tempSettings.target_models.includes(model.id)
                                            ? 'bg-blue-500 text-white'
                                            : 'bg-white dark:bg-gray-600 hover:bg-gray-100 dark:hover:bg-gray-500'
                                        }`}
                                        title={model.id}
                                      >
                                        {model.name || model.id.split('/').pop()}
                                      </button>
                                    ))}
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* نمایش تعداد انتخاب شده */}
                          <div className="mt-2 text-xs text-gray-500">
                            {tempSettings.target_models.length === 0 ? (
                              <span className="text-green-600">✓ همه {availableModels.length} مدل استفاده می‌شوند</span>
                            ) : (
                              <span>{tempSettings.target_models.length} مدل انتخاب شده</span>
                            )}
                          </div>
                        </>
                      )}
                    </div>

                    {/* 🆕 انتخاب عمق تحلیل */}
                    <div className="mb-4">
                      <label className="block text-sm font-medium mb-2">عمق تحلیل</label>
                      <div className="grid grid-cols-4 gap-2">
                        {[
                          { value: 'quick', label: '⚡ سریع', desc: '۱-۲ دقیقه' },
                          { value: 'standard', label: '📊 استاندارد', desc: '۳-۵ دقیقه' },
                          { value: 'deep', label: '🔬 عمیق', desc: '۱۰-۲۰ دقیقه' },
                          { value: 'thorough', label: '🔍 کامل', desc: '۳۰+ دقیقه' }
                        ].map(option => (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => setTempSettings({ ...tempSettings, depth: option.value as any })}
                            className={`p-3 rounded-lg border text-center transition-all ${
                              tempSettings.depth === option.value
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 hover:border-blue-400'
                            }`}
                          >
                            <div className="font-medium">{option.label}</div>
                            <div className="text-xs mt-1 opacity-75">{option.desc}</div>
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        عمق بیشتر = بررسی دقیق‌تر فایل‌ها، شناسایی مشکلات بیشتر، زمان بیشتر
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={tempSettings.trigger_enabled}
                            onChange={(e) => setTempSettings({ ...tempSettings, trigger_enabled: e.target.checked })}
                            className="w-4 h-4"
                          />
                          <span className="text-sm">فعال‌سازی زمان‌بندی خودکار</span>
                        </label>
                      </div>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={tempSettings.trigger_interval_minutes}
                          onChange={(e) => setTempSettings({ ...tempSettings, trigger_interval_minutes: parseInt(e.target.value) })}
                          className="w-20 p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                          disabled={!tempSettings.trigger_enabled}
                        />
                        <select
                          value={tempSettings.trigger_interval_type}
                          onChange={(e) => setTempSettings({ ...tempSettings, trigger_interval_type: e.target.value })}
                          className="p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                          disabled={!tempSettings.trigger_enabled}
                        >
                          <option value="minutes">دقیقه</option>
                          <option value="hours">ساعت</option>
                          <option value="daily">روزانه</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* تب فایل‌ها - 🆕 با دیاگرام رنگی */}
        {activeTab === 'files' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold">🎨 دیاگرام سلامت فایل‌ها</h3>
                <p className="text-sm text-gray-500">
                  ساختار پروژه با رنگ‌بندی براساس نمره سلامت هر فایل
                </p>
              </div>
              {Object.keys(fileHealthMap).length === 0 && (
                <button
                  onClick={runAnalysis}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm"
                >
                  شروع تحلیل
                </button>
              )}
            </div>

            {/* 🆕 کامپوننت دیاگرام سلامت */}
            <HealthDiagram
              projectId={projectId}
              fileHealthMap={fileHealthMap}
              onFileClick={(filePath) => {
                // نمایش جزئیات فایل در آینده
                console.log('File clicked:', filePath);
              }}
            />
          </div>
        )}

        {/* نقشه راه به تب ژورنال منتقل شد */}

        {/* تب ایرادات - فقط ایرادات فعال (غیر بایگانی) */}
        {activeTab === 'issues' && (() => {
          const activeIssues = issues.filter(i => !i.archived);
          return (
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className="font-bold">ایرادات فعال ({activeIssues.length})</h3>
                {activeIssues.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-500">
                      {activeIssues.filter(i => i.converted_to_field).length} تبدیل شده
                    </span>
                    {/* 🆕 دکمه‌های دانلود مارک‌داون */}
                    <button
                      onClick={() => window.open(`${API_BASE}/api/projects/${projectId}/export/issues/markdown?issue_ids=validated`, '_blank')}
                      className="px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 text-xs rounded hover:bg-blue-200 dark:hover:bg-blue-800 flex items-center gap-1"
                      title="دانلود ایرادات تایید شده"
                    >
                      📥 MD
                    </button>
                    <button
                      onClick={() => window.open(`${API_BASE}/api/projects/${projectId}/export/issues/markdown?issue_ids=all`, '_blank')}
                      className="px-2 py-1 bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 text-xs rounded hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1"
                      title="دانلود همه ایرادات (تایید و رد شده)"
                    >
                      📥 همه
                    </button>
                    <button
                      onClick={convertAllIssuesToFields}
                      disabled={convertingIssue === 'all' || activeIssues.every(i => i.converted_to_field)}
                      className="px-3 py-1 bg-purple-500 text-white text-xs rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      {convertingIssue === 'all' ? (
                        <>
                          <span className="animate-spin">⏳</span>
                          در حال تبدیل...
                        </>
                      ) : (
                        <>
                          <span>✨</span>
                          تبدیل همه به فیلد پویا
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>

              {activeIssues.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-5xl mb-4">✓</div>
                  <p>ایرادی فعال وجود ندارد</p>
                  {issues.filter(i => i.archived).length > 0 && (
                    <p className="text-sm mt-2">
                      {issues.filter(i => i.archived).length} ایراد در تب بایگانی
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-auto">
                  {activeIssues.map((issue, idx) => {
                    const issueId = issue.id || `issue_${idx}`;
                    const isConverting = convertingIssue === issueId;

                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border-r-4 transition-all ${
                          issue.converted_to_field
                            ? 'bg-green-50 dark:bg-green-900/20 opacity-70'
                            : 'bg-gray-50 dark:bg-gray-700'
                        }`}
                        style={{
                          borderColor: issue.converted_to_field ? '#22c55e' :
                                      issue.severity === 'critical' ? '#ef4444' :
                                      issue.severity === 'high' ? '#f97316' :
                                      issue.severity === 'medium' ? '#eab308' : '#3b82f6'
                        }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            {issue.file && (
                              <div className="text-xs font-mono text-blue-500 mb-1">{issue.file}</div>
                            )}
                            <p className="text-sm">{issue.message}</p>
                            <div className="flex items-center gap-2 mt-1">
                              {issue.line && (
                                <span className="text-xs text-gray-400">خط {issue.line}</span>
                              )}
                              {issue.converted_to_field && (
                                <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                                  <span>✓</span>
                                  تبدیل شده به فیلد
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(issue.severity)}`}>
                              {issue.severity}
                            </span>
                            {issue.model && (
                              <span className="text-xs text-gray-400">{issue.model}</span>
                            )}
                            {!issue.converted_to_field && (
                              <button
                                onClick={() => convertIssueToField(issue, issues.indexOf(issue))}
                                disabled={isConverting}
                                className="mt-1 px-2 py-0.5 bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-300 text-xs rounded hover:bg-purple-200 disabled:opacity-50"
                                title="تبدیل به فیلد پویا"
                              >
                                {isConverting ? '⏳' : '➜ فیلد'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })()}

        {/* 🆕 تب بایگانی - ایرادات بایگانی شده با برچسب */}
        {activeTab === 'archive' && (() => {
          const archivedIssues = issues.filter(i => i.archived);

          // تابع برای گرفتن برچسب فارسی از دلیل بایگانی
          const getArchiveLabel = (reason?: string): { text: string; color: string } => {
            if (!reason) return { text: 'بایگانی شده', color: 'bg-gray-500' };

            if (reason.includes('approved') || reason.includes('converted') || reason.includes('validated') || reason.includes('field')) {
              return { text: 'تایید شده ✓', color: 'bg-green-500' };
            }
            if (reason.includes('rejected') || reason.includes('invalid')) {
              return { text: 'رد شده ✗', color: 'bg-red-500' };
            }
            if (reason.includes('engineering_report') || reason.includes('4step')) {
              return { text: 'گزارش مهندسی', color: 'bg-blue-500' };
            }
            if (reason.includes('duplicate')) {
              return { text: 'تکراری', color: 'bg-yellow-500' };
            }
            return { text: 'بایگانی شده', color: 'bg-gray-500' };
          };

          return (
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className="font-bold">ایرادات بایگانی شده ({archivedIssues.length})</h3>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
                    تایید شده: {archivedIssues.filter(i =>
                      i.archived_reason?.includes('approved') ||
                      i.archived_reason?.includes('converted') ||
                      i.archived_reason?.includes('validated') ||
                      i.archived_reason?.includes('field')
                    ).length}
                  </span>
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded">
                    رد شده: {archivedIssues.filter(i =>
                      i.archived_reason?.includes('rejected') ||
                      i.archived_reason?.includes('invalid')
                    ).length}
                  </span>
                </div>
              </div>

              {archivedIssues.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-5xl mb-4">📦</div>
                  <p>هیچ ایرادی بایگانی نشده</p>
                  <p className="text-sm mt-2">
                    ایرادات پس از گزارش مهندسی به اینجا منتقل می‌شوند
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-auto">
                  {archivedIssues.map((issue, idx) => {
                    const label = getArchiveLabel(issue.archived_reason);

                    return (
                      <div
                        key={idx}
                        className="p-3 rounded-lg border-r-4 bg-gray-50 dark:bg-gray-700/50 opacity-80"
                        style={{
                          borderColor: label.color.includes('green') ? '#22c55e' :
                                      label.color.includes('red') ? '#ef4444' :
                                      label.color.includes('blue') ? '#3b82f6' : '#6b7280'
                        }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            {issue.file && (
                              <div className="text-xs font-mono text-blue-500 mb-1">{issue.file}</div>
                            )}
                            <p className="text-sm">{issue.message}</p>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {issue.line && (
                                <span className="text-xs text-gray-400">خط {issue.line}</span>
                              )}
                              {issue.archived_at && (
                                <span className="text-xs text-gray-400">
                                  بایگانی: {new Date(issue.archived_at).toLocaleString('fa-IR')}
                                </span>
                              )}
                              {issue.converted_to_field && (
                                <span className="text-xs text-green-600 flex items-center gap-1">
                                  <span>✓</span>
                                  تبدیل به فیلد
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            {/* برچسب وضعیت بایگانی */}
                            <span className={`px-2 py-0.5 rounded text-xs text-white ${label.color}`}>
                              {label.text}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(issue.severity)}`}>
                              {issue.severity}
                            </span>
                            {issue.model && (
                              <span className="text-xs text-gray-400">{issue.model}</span>
                            )}
                          </div>
                        </div>
                        {/* نمایش دلیل بایگانی */}
                        {issue.archived_reason && (
                          <div className="mt-2 text-xs text-gray-500 bg-gray-100 dark:bg-gray-600 px-2 py-1 rounded">
                            دلیل: {issue.archived_reason}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })()}

        {/* 🆕 تب زنجیره اعتبارسنجی */}
        {activeTab === 'validation' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg">زنجیره اعتبارسنجی</h3>
              <button
                onClick={() => {
                  loadValidationChainStatus();
                  loadRejectedIssues();
                }}
                className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300"
              >
                بروزرسانی
              </button>
            </div>

            {!validationChainStatus ? (
              <div className="text-center py-8 text-gray-400">
                <div className="text-5xl mb-4">✓</div>
                <p>داده‌ای برای نمایش وجود ندارد</p>
                <p className="text-sm mt-2">ابتدا تحلیل سلامت و سپس گزارش مهندسی تولید کنید</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* خلاصه زنجیره */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-blue-600">
                      {validationChainStatus.health_analysis?.total_issues || 0}
                    </div>
                    <div className="text-sm text-blue-500">ایرادات شناسایی شده</div>
                  </div>
                  <div className="p-4 bg-green-50 dark:bg-green-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-green-600">
                      {validationChainStatus.validation?.validated_count || 0}
                    </div>
                    <div className="text-sm text-green-500">تایید شده</div>
                  </div>
                  <div className="p-4 bg-red-50 dark:bg-red-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-red-600">
                      {validationChainStatus.validation?.rejected_count || 0}
                    </div>
                    <div className="text-sm text-red-500">رد شده</div>
                  </div>
                  <div className="p-4 bg-purple-50 dark:bg-purple-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-purple-600">
                      {validationChainStatus.fields?.validated_fields || 0}
                    </div>
                    <div className="text-sm text-purple-500">فیلدهای معتبر</div>
                  </div>
                </div>

                {/* وضعیت اعتبارسنجی */}
                {validationChainStatus.validation?.last_validated && (
                  <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl">
                    <h4 className="font-bold mb-2">آخرین اعتبارسنجی</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">تاریخ:</span>{' '}
                        {new Date(validationChainStatus.validation.last_validated).toLocaleString('fa-IR')}
                      </div>
                      <div>
                        <span className="text-gray-500">مدل اعتبارسنج:</span>{' '}
                        {validationChainStatus.validation.validator_model || 'نامشخص'}
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-500">خلاصه:</span>{' '}
                        {validationChainStatus.validation.summary || 'ندارد'}
                      </div>
                    </div>
                  </div>
                )}

                {/* وضعیت فیلدها */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl">
                  <h4 className="font-bold mb-2">وضعیت فیلدها</h4>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div className="text-center">
                      <div className="text-2xl font-bold">{validationChainStatus.fields?.total_active || 0}</div>
                      <div className="text-gray-500">فعال</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{validationChainStatus.fields?.validated_fields || 0}</div>
                      <div className="text-gray-500">معتبرشده</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-yellow-600">{validationChainStatus.fields?.unexecuted_fields || 0}</div>
                      <div className="text-gray-500">اجرانشده</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-400">{validationChainStatus.fields?.archived_fields || 0}</div>
                      <div className="text-gray-500">بایگانی</div>
                    </div>
                  </div>
                </div>

                {/* آرشیو ایرادات رد شده */}
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-bold text-red-700 dark:text-red-400">
                      ایرادات رد شده ({validationChainStatus.rejected_archive?.total || 0})
                    </h4>
                    {!loadingValidation && rejectedIssues.length === 0 && (
                      <button
                        onClick={loadRejectedIssues}
                        className="text-sm text-red-600 hover:underline"
                      >
                        بارگذاری
                      </button>
                    )}
                  </div>

                  {loadingValidation ? (
                    <div className="text-center py-4 text-gray-400">در حال بارگذاری...</div>
                  ) : rejectedIssues.length === 0 && validationChainStatus.rejected_archive?.total === 0 ? (
                    <p className="text-sm text-red-600 dark:text-red-400">هیچ ایرادی رد نشده است</p>
                  ) : (
                    <div className="space-y-2 max-h-[300px] overflow-auto">
                      {(rejectedIssues.length > 0 ? rejectedIssues : validationChainStatus.rejected_archive?.recent || []).map((item: any, idx: number) => (
                        <div
                          key={item.id || idx}
                          className="p-3 bg-white dark:bg-gray-800 rounded-lg"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <div className="text-xs font-mono text-blue-500 mb-1">
                                {item.original_issue?.file || 'نامشخص'}
                              </div>
                              <p className="text-sm">{item.original_issue?.message || item.rejection_reason}</p>
                              <div className="flex gap-2 mt-1 text-xs text-gray-400">
                                <span>منبع: {item.source_model}</span>
                                <span>•</span>
                                <span>اعتبارسنج: {item.validator_model}</span>
                              </div>
                            </div>
                            <div className="flex flex-col items-end gap-1">
                              <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-700">
                                امتیاز: {item.validation_score || 0}
                              </span>
                              {item.id && (
                                <button
                                  onClick={() => restoreRejectedIssue(item.id)}
                                  className="text-xs text-blue-500 hover:underline"
                                >
                                  بازگرداندن
                                </button>
                              )}
                            </div>
                          </div>
                          {item.rejection_reason && (
                            <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/30 rounded text-xs text-red-600 dark:text-red-400">
                              <strong>دلیل رد:</strong> {item.rejection_reason}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* حالت ایده‌آل */}
                {validationChainStatus.ideal_state?.defined && (
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-xl">
                    <h4 className="font-bold text-blue-700 dark:text-blue-400 mb-2">حالت ایده‌آل پروژه</h4>
                    <p className="text-sm text-blue-600 dark:text-blue-400 whitespace-pre-wrap">
                      {validationChainStatus.ideal_state.preview}
                      {validationChainStatus.ideal_state.preview.length >= 500 && '...'}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* تب امنیت */}
        {activeTab === 'security' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold">اسکن امنیتی پروژه</h3>
              <button
                onClick={async () => {
                  setLoadingSecurity(true);
                  try {
                    const res = await fetch(`${API_BASE}/api/projects/${projectId}/security/scan`);
                    const data = await res.json();
                    if (data.success) {
                      setSecurityData(data.scan_result);
                    }
                  } catch (err) {
                    console.error('Security scan error:', err);
                  }
                  setLoadingSecurity(false);
                }}
                disabled={loadingSecurity}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loadingSecurity ? 'در حال اسکن...' : 'اسکن امنیتی'}
              </button>
            </div>

            {securityData && (
              <div className="space-y-4">
                {/* امتیاز امنیتی */}
                <div className={`p-4 rounded-xl ${securityData.security_score >= 80 ? 'bg-green-100 dark:bg-green-900/30' : securityData.security_score >= 50 ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-bold text-white ${securityData.security_score >= 80 ? 'bg-green-500' : securityData.security_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}>
                      {securityData.security_score}
                    </div>
                    <div>
                      <h4 className="font-bold">امتیاز امنیتی</h4>
                      <p className="text-sm opacity-75">
                        {securityData.security_score >= 80 ? 'وضعیت امنیتی خوب' : securityData.security_score >= 50 ? 'نیاز به بهبود' : 'مشکلات جدی امنیتی'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Secrets */}
                {securityData.secrets.count > 0 && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
                    <h4 className="font-bold text-red-700 dark:text-red-400 mb-2">
                      🔑 Secrets یافت شده ({securityData.secrets.count})
                    </h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {securityData.secrets.findings.map((finding: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white dark:bg-gray-800 rounded text-sm">
                          <div className="flex justify-between">
                            <span className="font-mono text-red-600">{finding.file}:{finding.line}</span>
                            <span className={`px-2 py-0.5 rounded text-xs ${finding.severity === 'critical' ? 'bg-red-600 text-white' : 'bg-orange-500 text-white'}`}>
                              {finding.severity}
                            </span>
                          </div>
                          <p className="text-gray-600 dark:text-gray-400 mt-1">{finding.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* لایسنس */}
                <div className={`p-4 rounded-xl ${securityData.license.has_license ? 'bg-green-50 dark:bg-green-900/20' : 'bg-yellow-50 dark:bg-yellow-900/20'}`}>
                  <h4 className="font-bold mb-2">📄 لایسنس پروژه</h4>
                  {securityData.license.has_license ? (
                    <div className="space-y-1">
                      {securityData.license.licenses.map((lic: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="px-2 py-1 bg-green-200 dark:bg-green-800 rounded text-sm">{lic.license}</span>
                          <span className="text-sm text-gray-600">{lic.file}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-yellow-700 dark:text-yellow-400">پروژه فاقد فایل لایسنس است</p>
                  )}
                </div>

                {/* آسیب‌پذیری وابستگی‌ها */}
                {securityData.dependencies.vulnerability_count > 0 && (
                  <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl border border-orange-200 dark:border-orange-800">
                    <h4 className="font-bold text-orange-700 dark:text-orange-400 mb-2">
                      ⚠️ آسیب‌پذیری وابستگی‌ها ({securityData.dependencies.vulnerability_count})
                    </h4>
                    <div className="space-y-2">
                      {securityData.dependencies.vulnerabilities.map((vuln: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white dark:bg-gray-800 rounded text-sm">
                          <div className="flex justify-between items-center">
                            <span className="font-mono font-bold">{vuln.package}</span>
                            <span className="text-xs text-gray-500">{vuln.cve}</span>
                          </div>
                          <p className="text-gray-600 dark:text-gray-400">{vuln.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* فایل‌های حساس */}
                {securityData.sensitive_files.count > 0 && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
                    <h4 className="font-bold text-red-700 dark:text-red-400 mb-2">
                      🚨 فایل‌های حساس ({securityData.sensitive_files.count})
                    </h4>
                    <div className="space-y-1">
                      {securityData.sensitive_files.findings.map((file: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <span className="font-mono text-red-600">{file.file}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* تب پوشش تست */}
        {activeTab === 'coverage' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold">تحلیل پوشش تست</h3>
              <button
                onClick={async () => {
                  setLoadingCoverage(true);
                  try {
                    const res = await fetch(`${API_BASE}/api/projects/${projectId}/test-coverage`);
                    const data = await res.json();
                    if (data.success) {
                      setCoverageData(data.coverage);
                    }
                  } catch (err) {
                    console.error('Coverage analysis error:', err);
                  }
                  setLoadingCoverage(false);
                }}
                disabled={loadingCoverage}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {loadingCoverage ? 'در حال تحلیل...' : 'تحلیل پوشش'}
              </button>
            </div>

            {coverageData && (
              <div className="space-y-4">
                {/* خلاصه پوشش */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-blue-600">{coverageData.summary.coverage_percent}%</div>
                    <div className="text-sm text-gray-600">پوشش کد</div>
                  </div>
                  <div className="p-4 bg-green-50 dark:bg-green-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-green-600">{coverageData.summary.total_tests}</div>
                    <div className="text-sm text-gray-600">تعداد تست</div>
                  </div>
                  <div className="p-4 bg-purple-50 dark:bg-purple-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-purple-600">{coverageData.summary.total_test_files}</div>
                    <div className="text-sm text-gray-600">فایل تست</div>
                  </div>
                  <div className="p-4 bg-orange-50 dark:bg-orange-900/30 rounded-xl text-center">
                    <div className="text-3xl font-bold text-orange-600">{coverageData.summary.untested_file_count}</div>
                    <div className="text-sm text-gray-600">فایل بدون تست</div>
                  </div>
                </div>

                {/* امتیاز سلامت */}
                <div className={`p-4 rounded-xl ${coverageData.health_score >= 70 ? 'bg-green-100 dark:bg-green-900/30' : coverageData.health_score >= 40 ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-bold text-white ${coverageData.health_score >= 70 ? 'bg-green-500' : coverageData.health_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}>
                      {coverageData.health_score}
                    </div>
                    <div>
                      <h4 className="font-bold">امتیاز سلامت تست</h4>
                      <p className="text-sm opacity-75">
                        {coverageData.health_score >= 70 ? 'پوشش تست مناسب' : coverageData.health_score >= 40 ? 'نیاز به تست بیشتر' : 'پوشش تست بسیار پایین'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* توصیه‌ها */}
                {coverageData.recommendations.length > 0 && (
                  <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl">
                    <h4 className="font-bold text-yellow-700 dark:text-yellow-400 mb-2">💡 توصیه‌ها</h4>
                    <div className="space-y-2">
                      {coverageData.recommendations.map((rec: any, idx: number) => (
                        <div key={idx} className="flex items-start gap-2 text-sm">
                          <span className={`px-2 py-0.5 rounded text-xs ${rec.severity === 'critical' ? 'bg-red-600 text-white' : rec.severity === 'high' ? 'bg-orange-500 text-white' : 'bg-yellow-500 text-white'}`}>
                            {rec.severity}
                          </span>
                          <div>
                            <p className="font-medium">{rec.message}</p>
                            <p className="text-gray-600">{rec.recommendation}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* فایل‌های بدون تست */}
                {coverageData.untested_files.length > 0 && (
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <h4 className="font-bold mb-2">📁 فایل‌های بدون تست ({coverageData.untested_files.length})</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {coverageData.untested_files.map((file: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white dark:bg-gray-700 rounded text-sm">
                          <div className="font-mono text-purple-600">{file.path}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            {file.entity_count} موجودیت | نمونه: {file.entities?.slice(0, 3).join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
