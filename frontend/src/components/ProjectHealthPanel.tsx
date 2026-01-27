'use client';

import { useState, useEffect } from 'react';

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
}

interface Issue {
  file?: string;
  severity: string;
  message: string;
  line?: number;
  model?: string;
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
  const [activeTab, setActiveTab] = useState<'overview' | 'settings' | 'files' | 'roadmap' | 'issues'>('overview');
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

  // Edit states
  const [editingSettings, setEditingSettings] = useState(false);
  const [tempSettings, setTempSettings] = useState<AnalysisSettings | null>(null);

  // Messages
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadAllData();
    loadAvailableModels();
  }, [projectId]);

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
        loadIssues()
      ]);
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableModels = async () => {
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
          update_readme: true
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

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tempSettings)
      });

      if (res.ok) {
        setSettings(tempSettings);
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
          </div>
          <button
            onClick={runAnalysis}
            disabled={analyzing}
            className="px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30 disabled:opacity-50 flex items-center gap-2"
          >
            {analyzing ? (
              <>
                <span className="animate-spin">*</span>
                <span>در حال تحلیل...</span>
              </>
            ) : (
              <>
                <span>*</span>
                <span>شروع تحلیل</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* تب‌ها */}
      <div className="flex border-b dark:border-gray-700 overflow-x-auto">
        {[
          { id: 'overview', label: 'نمای کلی', icon: '*' },
          { id: 'settings', label: 'تنظیمات', icon: '+' },
          { id: 'files', label: 'فایل‌ها', icon: '-' },
          { id: 'roadmap', label: 'نقشه راه', icon: '#' },
          { id: 'issues', label: `ایرادات (${issues.length})`, icon: '!' },
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
            {/* نمره کلی */}
            <div className="flex items-center gap-6">
              <div className={`w-24 h-24 rounded-2xl flex items-center justify-center text-3xl font-bold text-white ${getScoreBg(healthScores?.overall || 0)}`}>
                {healthScores?.overall?.toFixed(0) || '?'}
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
                        {settings.target_models.map((m) => (
                          <span key={m} className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded text-sm">
                            {m}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
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
                      <label className="block text-sm font-medium mb-2">مدل‌های منتخب</label>
                      <div className="flex flex-wrap gap-2">
                        {availableModels.map((model) => (
                          <button
                            key={model.id}
                            onClick={() => {
                              const models = tempSettings.target_models.includes(model.id)
                                ? tempSettings.target_models.filter((m) => m !== model.id)
                                : [...tempSettings.target_models, model.id];
                              setTempSettings({ ...tempSettings, target_models: models });
                            }}
                            className={`px-3 py-1 rounded-lg text-sm transition ${
                              tempSettings.target_models.includes(model.id)
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            {model.name || model.id}
                          </button>
                        ))}
                      </div>
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

        {/* تب فایل‌ها */}
        {activeTab === 'files' && (
          <div className="space-y-4">
            <h3 className="font-bold">نقشه سلامت فایل‌ها</h3>
            <p className="text-sm text-gray-500">
              هر فایل بر اساس نمره سلامت رنگ‌بندی شده است. با hover روی هر فایل جزئیات را ببینید.
            </p>

            {Object.keys(fileHealthMap).length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <div className="text-5xl mb-4">?</div>
                <p>هنوز تحلیلی انجام نشده</p>
                <button
                  onClick={runAnalysis}
                  className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg"
                >
                  شروع تحلیل
                </button>
              </div>
            ) : (
              <div className="space-y-2 max-h-[500px] overflow-auto">
                {Object.entries(fileHealthMap).map(([filePath, health]) => (
                  <div
                    key={filePath}
                    className="group relative p-3 rounded-lg bg-gray-50 dark:bg-gray-700 border-r-4 hover:bg-gray-100 dark:hover:bg-gray-600 transition"
                    style={{ borderColor: health.hex }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm truncate max-w-[70%]">{filePath}</span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-bold text-white`}
                        style={{ backgroundColor: health.hex }}
                      >
                        {health.score?.toFixed(0) || 0}%
                      </span>
                    </div>

                    {/* Hover tooltip */}
                    <div className="hidden group-hover:block absolute top-full right-0 left-0 z-20 bg-white dark:bg-gray-800 shadow-xl rounded-lg p-4 mt-1 border dark:border-gray-600">
                      <div className="text-sm space-y-2">
                        <div className="font-bold text-blue-600 dark:text-blue-400">{filePath}</div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>نمره کلی: <span className="font-bold">{health.score?.toFixed(1)}%</span></div>
                          <div>تعداد مدل‌ها: <span className="font-bold">{health.models_analyzed}</span></div>
                        </div>
                        {health.analyzed_at && (
                          <div className="text-xs text-gray-400">
                            تاریخ: {new Date(health.analyzed_at).toLocaleString('fa-IR')}
                          </div>
                        )}
                        {health.model_scores && Object.keys(health.model_scores).length > 0 && (
                          <div className="border-t dark:border-gray-600 pt-2 mt-2">
                            <div className="text-xs text-gray-500 mb-1">نمره هر مدل:</div>
                            <div className="flex flex-wrap gap-1">
                              {Object.entries(health.model_scores).map(([model, score]) => (
                                <span
                                  key={model}
                                  className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs"
                                >
                                  {model}: {(score as number).toFixed(0)}%
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* راهنمای رنگ‌ها */}
            <div className="flex items-center gap-4 text-xs text-gray-500 pt-4 border-t dark:border-gray-700">
              <span>راهنما:</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500"></span> 90+</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500"></span> 70-90</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-500"></span> 50-70</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500"></span> 0-50</span>
            </div>
          </div>
        )}

        {/* تب نقشه راه */}
        {activeTab === 'roadmap' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold">نقشه راه پروژه (ROADMAP)</h3>
              <button
                onClick={async () => {
                  try {
                    const res = await fetch(`${API_BASE}/api/projects/${projectId}/roadmap`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ auto_generate: true })
                    });
                    if (res.ok) {
                      showSuccess('نقشه راه تولید شد');
                      loadRoadmap();
                    }
                  } catch (e) {
                    showError('خطا');
                  }
                }}
                className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
              >
                تولید/به‌روزرسانی خودکار
              </button>
            </div>

            {roadmap ? (
              <div className="prose dark:prose-invert max-w-none">
                <pre className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg overflow-auto max-h-[400px] text-sm whitespace-pre-wrap">
                  {roadmap}
                </pre>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">
                <div className="text-5xl mb-4">#</div>
                <p>نقشه راه وجود ندارد</p>
                <p className="text-sm">با کلیک روی دکمه بالا، نقشه راه تولید می‌شود</p>
              </div>
            )}
          </div>
        )}

        {/* تب ایرادات */}
        {activeTab === 'issues' && (
          <div className="space-y-4">
            <h3 className="font-bold">ایرادات شناسایی شده ({issues.length})</h3>

            {issues.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <div className="text-5xl mb-4">!</div>
                <p>ایرادی شناسایی نشده</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-auto">
                {issues.map((issue, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700 border-r-4"
                    style={{
                      borderColor: issue.severity === 'critical' ? '#ef4444' :
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
                        {issue.line && (
                          <span className="text-xs text-gray-400">خط {issue.line}</span>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(issue.severity)}`}>
                          {issue.severity}
                        </span>
                        {issue.model && (
                          <span className="text-xs text-gray-400">{issue.model}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
