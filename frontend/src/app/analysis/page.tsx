'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FileAnalysis {
  file_path: string;
  score: number;
  color: string;
  code_quality: number;
  documentation: number;
  security: number;
  best_practices: number;
  issues: any[];
  suggestions: string[];
  analysis_by_model: Record<string, any>;
}

interface AnalysisReport {
  id: string;
  project_id: string;
  status: string;
  created_at: string;
  completed_at?: string;
  models_used: string[];
  overall_score: number;
  overall_color: string;
  code_quality_score: number;
  documentation_score: number;
  security_score: number;
  structure_score: number;
  roadmap_compliance_score: number;
  file_analyses: FileAnalysis[];
  issues_found: any[];
  recommendations: string[];
  summary?: string;
}

interface AIProfile {
  model_id: string;
  provider: string;
  display_name?: string;
  overall_score: number;
  tier: string;
  rank: number;
  total_analyses: number;
  accuracy_score: number;
  completeness_score: number;
  speed_score: number;
}

interface ModelCapabilityResult {
  model_id: string;
  tested_at: string;
  overall_score: number;
  badges: Array<{
    type: string;
    badge_id: string;
    label: string;
    icon: string;
    color: string;
    score: number;
  }>;
  self_description: {
    name?: string;
    strengths?: string[];
    limitations?: string[];
    best_for?: string[];
  };
  strengths: Array<{ category: string; score: number }>;
  weaknesses: Array<{ category: string; score: number }>;
  categories: Record<string, { avg_score: number; tests: any[] }>;
}

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState<'reports' | 'profiles' | 'run' | 'capabilities'>('reports');

  // Reports state
  const [reports, setReports] = useState<AnalysisReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);

  // Profiles state
  const [profiles, setProfiles] = useState<AIProfile[]>([]);

  // Run analysis state
  const [projectPath, setProjectPath] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [running, setRunning] = useState(false);

  // Progress tracking state
  const [progressData, setProgressData] = useState<{
    phase: string;
    current_file: string;
    current_model: string;
    analyzed_files: number;
    total_files: number;
    progress_percentage: number;
    elapsed_time: number;
    issues_found: number;
    message: string;
    model_statuses: Record<string, string>;
  } | null>(null);
  const [showProgressDetails, setShowProgressDetails] = useState(false);

  // Capability testing state
  const [capabilityResults, setCapabilityResults] = useState<Record<string, ModelCapabilityResult>>({});
  const [testingModel, setTestingModel] = useState<string | null>(null);
  const [selectedCapabilityModel, setSelectedCapabilityModel] = useState<string | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([loadReports(), loadProfiles(), loadModels()]);
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadReports = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/analysis/reports`);
      if (res.ok) {
        const data = await res.json();
        setReports(data || []);
      }
    } catch (e) {
      console.error('Error loading reports:', e);
    }
  };

  const loadProfiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/analysis/profiles`);
      if (res.ok) {
        const data = await res.json();
        setProfiles(data || []);
      }
    } catch (e) {
      console.error('Error loading profiles:', e);
    }
  };

  const loadModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/available`);
      if (res.ok) {
        const data = await res.json();
        setAvailableModels(data.models || []);
      }
    } catch (e) {
      console.error('Error loading models:', e);
    }
  };

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const runAnalysis = async () => {
    if (!projectPath.trim()) {
      showError('مسیر پروژه را وارد کنید');
      return;
    }

    setRunning(true);
    setProgressData(null);

    try {
      // استفاده از Streaming endpoint با EventSource
      const response = await fetch(`${API_BASE}/api/analysis/run-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: `proj_${Date.now()}`,
          project_path: projectPath,
          models: selectedModels.length > 0 ? selectedModels : undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('خطا در شروع تحلیل');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('خطا در خواندن استریم');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              // به‌روزرسانی وضعیت پیشرفت
              if (data.event !== 'heartbeat') {
                setProgressData({
                  phase: data.phase || 'preparing',
                  current_file: data.current_file || '',
                  current_model: data.current_model || '',
                  analyzed_files: data.analyzed_files || 0,
                  total_files: data.total_files || 0,
                  progress_percentage: data.progress_percentage || 0,
                  elapsed_time: data.elapsed_time || 0,
                  issues_found: data.issues_found || 0,
                  message: data.message || '',
                  model_statuses: data.model_statuses || {},
                });
              }

              // اگر تحلیل تمام شد
              if (data.event === 'done' || data.event === 'analysis_completed') {
                showSuccess('تحلیل با موفقیت انجام شد!');
                await loadReports();
                setActiveTab('reports');
                break;
              }

              // اگر خطا داریم
              if (data.event === 'error') {
                showError(data.message || 'خطا در تحلیل');
                break;
              }
            } catch (e) {
              // JSON parse error - ignore
            }
          }
        }
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setRunning(false);
      // پاک کردن progress بعد از چند ثانیه
      setTimeout(() => setProgressData(null), 3000);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 90) return 'bg-green-500';
    if (score >= 70) return 'bg-yellow-500';
    if (score >= 50) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getScoreBgColor = (score: number): string => {
    if (score >= 90) return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    if (score >= 70) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
    if (score >= 50) return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
    return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
  };

  const getTierColor = (tier: string): string => {
    switch (tier) {
      case 'S': return 'bg-purple-500 text-white';
      case 'A': return 'bg-green-500 text-white';
      case 'B': return 'bg-blue-500 text-white';
      case 'C': return 'bg-yellow-500 text-black';
      case 'D': return 'bg-orange-500 text-white';
      case 'F': return 'bg-red-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const testModelCapability = async (modelId: string) => {
    setTestingModel(modelId);
    try {
      const res = await fetch(`${API_BASE}/api/models/capability-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId }),
      });

      const data = await res.json();
      if (data.success) {
        setCapabilityResults(prev => ({
          ...prev,
          [modelId]: data.results
        }));
        setSelectedCapabilityModel(modelId);
        showSuccess(`تست توانایی ${modelId} تکمیل شد!`);
      } else {
        showError(data.error || 'خطا در تست مدل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setTestingModel(null);
    }
  };

  const getBadgeColor = (color: string): string => {
    const colors: Record<string, string> = {
      gold: 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white',
      purple: 'bg-gradient-to-r from-purple-500 to-purple-700 text-white',
      blue: 'bg-gradient-to-r from-blue-500 to-blue-700 text-white',
      green: 'bg-gradient-to-r from-green-500 to-green-700 text-white',
      yellow: 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black',
      gray: 'bg-gradient-to-r from-gray-400 to-gray-600 text-white',
    };
    return colors[color] || colors.gray;
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

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">تحلیل پروژه و پروفایل مدل‌ها</h1>
            <p className="text-gray-500 text-sm">بررسی خودکار سلامت پروژه توسط AI</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadData}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
            >
              بروزرسانی
            </button>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
            >
              خانه
            </Link>
          </div>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('reports')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'reports'
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            گزارش‌ها ({reports.length})
          </button>
          <button
            onClick={() => setActiveTab('profiles')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'profiles'
                ? 'bg-purple-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            پروفایل مدل‌ها ({profiles.length})
          </button>
          <button
            onClick={() => setActiveTab('run')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'run'
                ? 'bg-green-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            اجرای تحلیل
          </button>
          <button
            onClick={() => setActiveTab('capabilities')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'capabilities'
                ? 'bg-orange-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            تست توانایی مدل‌ها
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">در حال بارگذاری...</div>
        ) : (
          <>
            {/* تب گزارش‌ها */}
            {activeTab === 'reports' && (
              <div className="grid lg:grid-cols-3 gap-6">
                {/* لیست گزارش‌ها */}
                <div className="lg:col-span-1">
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
                    <h2 className="font-bold mb-4">گزارش‌های تحلیل</h2>
                    {reports.length === 0 ? (
                      <p className="text-gray-400 text-center py-8">گزارشی وجود ندارد</p>
                    ) : (
                      <div className="space-y-2 max-h-[60vh] overflow-auto">
                        {reports.map((report) => (
                          <div
                            key={report.id}
                            onClick={() => setSelectedReport(report)}
                            className={`p-3 rounded-lg cursor-pointer transition ${
                              selectedReport?.id === report.id
                                ? 'bg-blue-50 dark:bg-blue-900/30 border-2 border-blue-500'
                                : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-sm">{report.project_id}</span>
                              <span className={`px-2 py-1 rounded text-xs ${getScoreBgColor(report.overall_score)}`}>
                                {report.overall_score.toFixed(0)}%
                              </span>
                            </div>
                            <div className="text-xs text-gray-400 mt-1">
                              {new Date(report.created_at).toLocaleString('fa-IR')}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* جزئیات گزارش */}
                <div className="lg:col-span-2">
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                    {!selectedReport ? (
                      <div className="text-center py-12 text-gray-400">
                        <div className="text-5xl mb-4">📊</div>
                        <p>یک گزارش انتخاب کنید</p>
                      </div>
                    ) : (
                      <div>
                        {/* نمره کلی */}
                        <div className="flex items-center gap-4 mb-6">
                          <div className={`w-20 h-20 rounded-xl flex items-center justify-center text-2xl font-bold text-white ${getScoreColor(selectedReport.overall_score)}`}>
                            {selectedReport.overall_score.toFixed(0)}
                          </div>
                          <div>
                            <h2 className="text-xl font-bold">{selectedReport.project_id}</h2>
                            <p className="text-gray-500">
                              {selectedReport.status === 'completed' ? 'تکمیل شده' : selectedReport.status}
                            </p>
                            <p className="text-sm text-gray-400">
                              مدل‌ها: {selectedReport.models_used.join(', ')}
                            </p>
                          </div>
                        </div>

                        {/* نمرات جزئی */}
                        <div className="grid grid-cols-5 gap-4 mb-6">
                          {[
                            { label: 'کیفیت کد', score: selectedReport.code_quality_score },
                            { label: 'مستندات', score: selectedReport.documentation_score },
                            { label: 'امنیت', score: selectedReport.security_score },
                            { label: 'ساختار', score: selectedReport.structure_score },
                            { label: 'نقشه راه', score: selectedReport.roadmap_compliance_score },
                          ].map((item) => (
                            <div key={item.label} className="text-center">
                              <div className="text-sm text-gray-500 mb-1">{item.label}</div>
                              <div className={`text-lg font-bold ${
                                item.score >= 70 ? 'text-green-500' :
                                item.score >= 50 ? 'text-yellow-500' : 'text-red-500'
                              }`}>
                                {item.score.toFixed(0)}%
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* تحلیل فایل‌ها با رنگ‌بندی */}
                        {selectedReport.file_analyses && selectedReport.file_analyses.length > 0 && (
                          <div className="mb-6">
                            <h3 className="font-bold mb-3">تحلیل فایل‌ها (با رنگ‌بندی سلامت)</h3>
                            <div className="space-y-2 max-h-[300px] overflow-auto">
                              {selectedReport.file_analyses.map((fa, idx) => (
                                <div
                                  key={idx}
                                  className="group relative p-3 rounded-lg bg-gray-50 dark:bg-gray-700"
                                  style={{
                                    borderRight: `4px solid ${
                                      fa.score >= 90 ? '#22c55e' :
                                      fa.score >= 70 ? '#eab308' :
                                      fa.score >= 50 ? '#f97316' : '#ef4444'
                                    }`
                                  }}
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-mono text-sm">{fa.file_path}</span>
                                    <span className={`px-2 py-1 rounded text-xs ${getScoreBgColor(fa.score)}`}>
                                      {fa.score.toFixed(0)}%
                                    </span>
                                  </div>

                                  {/* جزئیات با hover */}
                                  <div className="hidden group-hover:block absolute top-full left-0 right-0 z-10 bg-white dark:bg-gray-800 shadow-lg rounded-lg p-4 mt-1">
                                    <div className="text-sm">
                                      <div className="grid grid-cols-2 gap-2 mb-2">
                                        <div>کیفیت کد: {fa.code_quality.toFixed(0)}%</div>
                                        <div>مستندات: {fa.documentation.toFixed(0)}%</div>
                                        <div>امنیت: {fa.security.toFixed(0)}%</div>
                                        <div>بهترین روش‌ها: {fa.best_practices.toFixed(0)}%</div>
                                      </div>
                                      {fa.issues && fa.issues.length > 0 && (
                                        <div className="text-red-500 text-xs">
                                          {fa.issues.length} مشکل
                                        </div>
                                      )}
                                      {Object.keys(fa.analysis_by_model || {}).length > 0 && (
                                        <div className="text-gray-400 text-xs mt-1">
                                          بررسی توسط: {Object.keys(fa.analysis_by_model).join(', ')}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* پیشنهادات */}
                        {selectedReport.recommendations && selectedReport.recommendations.length > 0 && (
                          <div className="mb-6">
                            <h3 className="font-bold mb-3">پیشنهادات بهبود</h3>
                            <ul className="space-y-2">
                              {selectedReport.recommendations.map((rec, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm">
                                  <span className="text-blue-500">*</span>
                                  <span>{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* مشکلات */}
                        {selectedReport.issues_found && selectedReport.issues_found.length > 0 && (
                          <div>
                            <h3 className="font-bold mb-3">مشکلات یافت‌شده ({selectedReport.issues_found.length})</h3>
                            <div className="space-y-2 max-h-[200px] overflow-auto">
                              {selectedReport.issues_found.slice(0, 20).map((issue, idx) => (
                                <div key={idx} className={`p-2 rounded text-sm ${
                                  issue.severity === 'critical' ? 'bg-red-100 dark:bg-red-900/30' :
                                  issue.severity === 'high' ? 'bg-orange-100 dark:bg-orange-900/30' :
                                  'bg-yellow-100 dark:bg-yellow-900/30'
                                }`}>
                                  <div className="font-medium">{issue.file || 'عمومی'}</div>
                                  <div className="text-gray-600 dark:text-gray-400">{issue.message}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* تب پروفایل مدل‌ها */}
            {activeTab === 'profiles' && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                <h2 className="font-bold mb-4">پروفایل و رتبه‌بندی مدل‌های AI</h2>
                <p className="text-sm text-gray-500 mb-4">
                  نمرات تجمعی بر اساس تاریخچه عملکرد (هیچوقت صفر نمی‌شوند)
                </p>

                {profiles.length === 0 ? (
                  <p className="text-gray-400 text-center py-8">پروفایلی وجود ندارد</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                          <th className="p-3 text-right">رتبه</th>
                          <th className="p-3 text-right">مدل</th>
                          <th className="p-3 text-right">پروایدر</th>
                          <th className="p-3 text-right">Tier</th>
                          <th className="p-3 text-right">نمره کلی</th>
                          <th className="p-3 text-right">دقت</th>
                          <th className="p-3 text-right">کامل بودن</th>
                          <th className="p-3 text-right">سرعت</th>
                          <th className="p-3 text-right">تعداد تحلیل</th>
                        </tr>
                      </thead>
                      <tbody>
                        {profiles.map((profile, idx) => (
                          <tr key={profile.model_id} className="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="p-3 font-bold">{idx + 1}</td>
                            <td className="p-3">
                              <span className="font-medium">{profile.display_name || profile.model_id}</span>
                            </td>
                            <td className="p-3">
                              <span className="text-sm text-gray-500">{profile.provider}</span>
                            </td>
                            <td className="p-3">
                              <span className={`px-2 py-1 rounded text-xs font-bold ${getTierColor(profile.tier)}`}>
                                {profile.tier}
                              </span>
                            </td>
                            <td className="p-3">
                              <span className={`font-bold ${
                                profile.overall_score >= 85 ? 'text-green-500' :
                                profile.overall_score >= 70 ? 'text-yellow-500' : 'text-red-500'
                              }`}>
                                {profile.overall_score.toFixed(1)}
                              </span>
                            </td>
                            <td className="p-3">{profile.accuracy_score.toFixed(1)}</td>
                            <td className="p-3">{profile.completeness_score.toFixed(1)}</td>
                            <td className="p-3">{profile.speed_score.toFixed(1)}</td>
                            <td className="p-3">{profile.total_analyses}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* تب اجرای تحلیل */}
            {activeTab === 'run' && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                <h2 className="font-bold mb-4">اجرای تحلیل جدید</h2>

                <div className="space-y-4 max-w-xl">
                  <div>
                    <label className="block text-sm font-medium mb-2">مسیر پروژه</label>
                    <input
                      type="text"
                      value={projectPath}
                      onChange={(e) => setProjectPath(e.target.value)}
                      placeholder="/path/to/project"
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      dir="ltr"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">مدل‌های بررسی‌کننده (اختیاری)</label>
                    <div className="flex flex-wrap gap-2">
                      {availableModels.map((model) => (
                        <button
                          key={model.id}
                          onClick={() => {
                            setSelectedModels((prev) =>
                              prev.includes(model.id)
                                ? prev.filter((m) => m !== model.id)
                                : [...prev, model.id]
                            );
                          }}
                          className={`px-3 py-1 rounded text-sm ${
                            selectedModels.includes(model.id)
                              ? 'bg-blue-500 text-white'
                              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {model.name || model.id}
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      خالی بگذارید برای استفاده از همه مدل‌های فعال
                    </p>
                  </div>

                  <button
                    onClick={runAnalysis}
                    disabled={running}
                    className="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                  >
                    {running ? 'در حال تحلیل...' : 'شروع تحلیل'}
                  </button>
                </div>

                {/* نوار پیشرفت Real-time */}
                {running && progressData && (
                  <div className="mt-6">
                    {/* نوار اصلی پیشرفت - کلیک‌پذیر */}
                    <div
                      onClick={() => setShowProgressDetails(!showProgressDetails)}
                      className="cursor-pointer bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg p-4 text-white relative overflow-hidden"
                    >
                      {/* نوار پیشرفت داخلی */}
                      <div
                        className="absolute inset-0 bg-white/20 transition-all duration-500"
                        style={{ width: `${progressData.progress_percentage}%` }}
                      />

                      <div className="relative z-10">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="animate-pulse">●</span>
                            <span className="font-bold">
                              {progressData.phase === 'micro' && 'بررسی فایل‌ها'}
                              {progressData.phase === 'macro' && 'بررسی همکاری‌ها'}
                              {progressData.phase === 'structural' && 'بررسی ساختار'}
                              {progressData.phase === 'finalizing' && 'نهایی‌سازی'}
                              {progressData.phase === 'preparing' && 'آماده‌سازی'}
                            </span>
                          </div>
                          <span className="font-mono text-lg">{progressData.progress_percentage.toFixed(0)}%</span>
                        </div>

                        <div className="text-sm opacity-90">
                          {progressData.current_model && (
                            <span className="inline-flex items-center gap-1 bg-white/20 px-2 py-1 rounded mr-2">
                              🤖 {progressData.current_model}
                            </span>
                          )}
                          {progressData.message && (
                            <span>{progressData.message}</span>
                          )}
                        </div>

                        <div className="flex items-center justify-between mt-2 text-xs opacity-75">
                          <span>فایل‌ها: {progressData.analyzed_files}/{progressData.total_files}</span>
                          <span>مشکلات: {progressData.issues_found}</span>
                          <span>زمان: {Math.floor(progressData.elapsed_time)}s</span>
                          <span className="cursor-pointer hover:underline">
                            {showProgressDetails ? '▼ بستن' : '▲ جزئیات بیشتر'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* پنل جزئیات - نمایش با کلیک */}
                    {showProgressDetails && (
                      <div className="mt-2 bg-gray-900 text-gray-100 rounded-lg p-4 text-sm font-mono max-h-64 overflow-auto">
                        <div className="mb-3 text-xs text-gray-400">وضعیت مدل‌ها:</div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {Object.entries(progressData.model_statuses || {}).map(([modelId, status]) => (
                            <div
                              key={modelId}
                              className={`p-2 rounded text-xs ${
                                status === 'working'
                                  ? 'bg-yellow-500/20 text-yellow-300 animate-pulse'
                                  : status === 'completed'
                                  ? 'bg-green-500/20 text-green-300'
                                  : status === 'failed'
                                  ? 'bg-red-500/20 text-red-300'
                                  : 'bg-gray-700 text-gray-400'
                              }`}
                            >
                              <div className="flex items-center gap-1">
                                {status === 'working' && '⏳'}
                                {status === 'completed' && '✅'}
                                {status === 'failed' && '❌'}
                                {status === 'waiting' && '⏸️'}
                                <span className="truncate">{modelId.split('/').pop()}</span>
                              </div>
                            </div>
                          ))}
                        </div>

                        {progressData.current_file && (
                          <div className="mt-3 pt-3 border-t border-gray-700">
                            <div className="text-xs text-gray-400 mb-1">فایل فعلی:</div>
                            <div className="text-blue-300 truncate">{progressData.current_file}</div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <h3 className="font-bold mb-2">توضیحات</h3>
                  <ul className="text-sm space-y-1 text-gray-600 dark:text-gray-300">
                    <li>* تحلیل توسط چندین مدل AI به صورت موازی انجام می‌شود</li>
                    <li>* هر فایل از نظر کیفیت کد، مستندات، امنیت و بهترین روش‌ها بررسی می‌شود</li>
                    <li>* نتایج با رنگ‌بندی (سبز تا قرمز) نمایش داده می‌شوند</li>
                    <li>* با hover روی هر فایل، جزئیات بیشتر نمایش داده می‌شود</li>
                    <li>* نمرات مدل‌ها در پروفایلشان ذخیره و تجمیع می‌شوند</li>
                  </ul>
                </div>
              </div>
            )}

            {/* تب تست توانایی مدل‌ها */}
            {activeTab === 'capabilities' && (
              <div className="grid lg:grid-cols-3 gap-6">
                {/* لیست مدل‌ها */}
                <div className="lg:col-span-1">
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
                    <h2 className="font-bold mb-4">مدل‌های قابل تست</h2>
                    <p className="text-xs text-gray-500 mb-4">
                      روی هر مدل کلیک کنید تا تست توانایی اجرا شود
                    </p>

                    <div className="space-y-2 max-h-[60vh] overflow-auto">
                      {availableModels.map((model) => {
                        const hasResult = capabilityResults[model.id];
                        const isSelected = selectedCapabilityModel === model.id;
                        const isTesting = testingModel === model.id;

                        return (
                          <div
                            key={model.id}
                            onClick={() => !isTesting && testModelCapability(model.id)}
                            className={`p-3 rounded-lg cursor-pointer transition ${
                              isSelected
                                ? 'bg-orange-50 dark:bg-orange-900/30 border-2 border-orange-500'
                                : isTesting
                                ? 'bg-yellow-50 dark:bg-yellow-900/30 animate-pulse'
                                : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-sm">{model.name || model.id}</span>
                              {isTesting && (
                                <span className="text-xs text-yellow-600">در حال تست...</span>
                              )}
                              {hasResult && !isTesting && (
                                <span className={`px-2 py-1 rounded text-xs font-bold ${getScoreBgColor(hasResult.overall_score)}`}>
                                  {hasResult.overall_score.toFixed(0)}
                                </span>
                              )}
                            </div>

                            {/* نمایش badge ها */}
                            {hasResult && hasResult.badges && hasResult.badges.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {hasResult.badges.slice(0, 3).map((badge, idx) => (
                                  <span
                                    key={idx}
                                    className={`text-xs px-2 py-0.5 rounded-full ${getBadgeColor(badge.color)}`}
                                    title={`${badge.label}: ${badge.score.toFixed(0)}`}
                                  >
                                    {badge.icon} {badge.label}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* نتایج تست */}
                <div className="lg:col-span-2">
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                    {!selectedCapabilityModel || !capabilityResults[selectedCapabilityModel] ? (
                      <div className="text-center py-12 text-gray-400">
                        <div className="text-5xl mb-4">🧪</div>
                        <p>یک مدل را انتخاب کنید تا تست توانایی اجرا شود</p>
                        <p className="text-sm mt-2">
                          هر مدل با سوالات استاندارد تست می‌شود و badge می‌گیرد
                        </p>
                      </div>
                    ) : (
                      <div>
                        {(() => {
                          const result = capabilityResults[selectedCapabilityModel];
                          return (
                            <>
                              {/* هدر با badge ها */}
                              <div className="flex items-start gap-4 mb-6">
                                <div className={`w-24 h-24 rounded-xl flex flex-col items-center justify-center text-white ${
                                  result.overall_score >= 80 ? 'bg-gradient-to-br from-purple-500 to-purple-700' :
                                  result.overall_score >= 60 ? 'bg-gradient-to-br from-blue-500 to-blue-700' :
                                  'bg-gradient-to-br from-gray-500 to-gray-700'
                                }`}>
                                  <div className="text-3xl font-bold">{result.overall_score.toFixed(0)}</div>
                                  <div className="text-xs opacity-75">امتیاز کلی</div>
                                </div>
                                <div className="flex-1">
                                  <h2 className="text-xl font-bold">{selectedCapabilityModel}</h2>
                                  <p className="text-gray-500 text-sm">
                                    تست شده در {new Date(result.tested_at).toLocaleString('fa-IR')}
                                  </p>

                                  {/* Badge ها */}
                                  <div className="flex flex-wrap gap-2 mt-3">
                                    {result.badges.map((badge, idx) => (
                                      <span
                                        key={idx}
                                        className={`px-3 py-1 rounded-full text-sm font-medium ${getBadgeColor(badge.color)}`}
                                      >
                                        {badge.icon} {badge.label}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>

                              {/* معرفی مدل */}
                              {result.self_description && (result.self_description.strengths || result.self_description.best_for) && (
                                <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                  <h3 className="font-bold mb-2">معرفی مدل</h3>
                                  {result.self_description.strengths && (
                                    <div className="mb-2">
                                      <span className="text-sm text-gray-500">نقاط قوت:</span>
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {result.self_description.strengths.map((s, i) => (
                                          <span key={i} className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded text-xs">
                                            {s}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  {result.self_description.best_for && (
                                    <div>
                                      <span className="text-sm text-gray-500">بهترین برای:</span>
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {result.self_description.best_for.map((b, i) => (
                                          <span key={i} className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs">
                                            {b}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* نمرات دسته‌بندی */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                                {Object.entries(result.categories).map(([category, data]) => {
                                  const categoryLabels: Record<string, string> = {
                                    code_analysis: 'تحلیل کد',
                                    code_generation: 'کدنویسی',
                                    documentation: 'مستندسازی',
                                    security: 'امنیت',
                                    problem_solving: 'حل مسئله',
                                    language: 'زبان',
                                    reasoning: 'استدلال',
                                    identity: 'هویت',
                                  };
                                  return (
                                    <div key={category} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                                      <div className="text-xs text-gray-500 mb-1">
                                        {categoryLabels[category] || category}
                                      </div>
                                      <div className={`text-lg font-bold ${
                                        data.avg_score >= 75 ? 'text-green-500' :
                                        data.avg_score >= 50 ? 'text-yellow-500' : 'text-red-500'
                                      }`}>
                                        {data.avg_score.toFixed(0)}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>

                              {/* نقاط قوت و ضعف */}
                              <div className="grid md:grid-cols-2 gap-4">
                                {result.strengths.length > 0 && (
                                  <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                    <h4 className="font-bold text-green-700 dark:text-green-300 mb-2">نقاط قوت</h4>
                                    {result.strengths.map((s, i) => (
                                      <div key={i} className="flex items-center justify-between text-sm py-1">
                                        <span>{s.category}</span>
                                        <span className="font-mono text-green-600">{s.score.toFixed(0)}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                {result.weaknesses.length > 0 && (
                                  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                    <h4 className="font-bold text-red-700 dark:text-red-300 mb-2">نیاز به بهبود</h4>
                                    {result.weaknesses.map((w, i) => (
                                      <div key={i} className="flex items-center justify-between text-sm py-1">
                                        <span>{w.category}</span>
                                        <span className="font-mono text-red-600">{w.score.toFixed(0)}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
