/**
 * Models Page - View and manage AI models
 */

'use client';

import { useState, useEffect } from 'react';
import { modelsApi, Model, ProviderStatus } from '@/services/api';
import ExtractionDefaultPicker from '@/components/ExtractionDefaultPicker';
import {
  CheckCircleIcon,
  XCircleIcon,
  FunnelIcon,
  BeakerIcon,
  Cog6ToothIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CapabilityResult {
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

interface ModelSettings {
  model_id: string;
  model_name: string;
  provider: string;
  enabled: boolean;
  allowed_tasks: string[];
  priority: number;
  max_tokens_override: number | null;
  max_daily_requests: number;
  current_daily_requests: number;
  preferred_for: string[];
  fallback_model_id: string | null;
  max_daily_cost: number;
  current_daily_cost: number;
  notes: string | null;
  advanced_settings: Record<string, any>;
  has_custom_settings: boolean;
}

interface TaskType {
  id: string;
  name: string;
  description: string;
}

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  // View mode: 'view' or 'manage'
  const [viewMode, setViewMode] = useState<'view' | 'manage'>('view');

  // Capability testing state
  const [capabilityResults, setCapabilityResults] = useState<Record<string, CapabilityResult>>({});
  const [testingModel, setTestingModel] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [showTestPanel, setShowTestPanel] = useState(false);

  // Management state
  const [modelSettings, setModelSettings] = useState<ModelSettings[]>([]);
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [editingModel, setEditingModel] = useState<string | null>(null);
  const [savingSettings, setSavingSettings] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (viewMode === 'manage') {
      loadManagementData();
    }
  }, [viewMode]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [modelsRes, providersRes] = await Promise.all([
        modelsApi.list(),
        modelsApi.providers(),
      ]);
      setModels(modelsRes.data);
      setProviders(providersRes.data);
    } catch (err) {
      console.error('Error loading models:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadManagementData = async () => {
    try {
      const [settingsRes, taskTypesRes] = await Promise.all([
        fetch(`${API_BASE}/api/models/settings`),
        fetch(`${API_BASE}/api/models/task-types`),
      ]);

      const settingsData = await settingsRes.json();
      const taskTypesData = await taskTypesRes.json();

      if (settingsData.success) {
        setModelSettings(settingsData.settings);
      }
      if (taskTypesData.success) {
        setTaskTypes(taskTypesData.task_types);
      }
    } catch (err) {
      console.error('Error loading management data:', err);
    }
  };

  const showSuccess = (msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  const showError = (msg: string) => {
    setErrorMessage(msg);
    setTimeout(() => setErrorMessage(''), 3000);
  };

  const toggleModelEnabled = async (modelId: string) => {
    setSavingSettings(modelId);
    try {
      const res = await fetch(`${API_BASE}/api/models/settings/${modelId}/toggle`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        setModelSettings(prev => prev.map(s =>
          s.model_id === modelId ? { ...s, enabled: data.enabled } : s
        ));
        // 🔴 آپدیت لیست models هم برای تب مشاهده
        setModels(prev => prev.map(m =>
          m.id === modelId ? { ...m, enabled: data.enabled } : m
        ));
        showSuccess(`مدل ${data.enabled ? 'فعال' : 'غیرفعال'} شد`);
      } else {
        showError(data.error || 'خطا در تغییر وضعیت');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSavingSettings(null);
    }
  };

  const updateModelSettings = async (modelId: string, updates: Partial<ModelSettings>) => {
    setSavingSettings(modelId);
    try {
      const res = await fetch(`${API_BASE}/api/models/settings/${modelId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      const data = await res.json();
      if (data.success) {
        await loadManagementData();
        // 🔴 اگر enabled تغییر کرده، لیست models رو هم رفرش کن
        if ('enabled' in updates) {
          await loadData();
        }
        showSuccess('تنظیمات ذخیره شد');
        setEditingModel(null);
      } else {
        showError(data.error || 'خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSavingSettings(null);
    }
  };

  const resetModelSettings = async (modelId: string) => {
    if (!confirm('آیا مطمئنید؟ تنظیمات به حالت پیش‌فرض برمی‌گردد.')) return;

    setSavingSettings(modelId);
    try {
      const res = await fetch(`${API_BASE}/api/models/settings/${modelId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        await loadManagementData();
        showSuccess('تنظیمات بازنشانی شد');
      }
    } catch (e) {
      showError('خطا در بازنشانی');
    } finally {
      setSavingSettings(null);
    }
  };

  const filteredModels = filter === 'all'
    ? models
    : filter === 'available'
      ? models.filter(m => m.enabled)  // 🔴 از enabled استفاده می‌کنیم نه is_available
      : models.filter(m => m.provider === filter);

  const getProviderColor = (provider: string) => {
    const colors: Record<string, string> = {
      openai: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      claude: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      gemini: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      deepseek: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      perplexity: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
      groq: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    };
    return colors[provider] || 'bg-gray-100 text-gray-800';
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
        setSelectedModel(modelId);
        setShowTestPanel(true);
      }
    } catch (e) {
      console.error('Error testing model:', e);
    } finally {
      setTestingModel(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner w-12 h-12" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" dir="rtl">
      {/* Messages */}
      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {errorMessage}
        </div>
      )}

      {/* 🆕 (Stage 10 audit fix #4) — انتخاب مدل پیش‌فرض extraction */}
      <ExtractionDefaultPicker apiBase={API_BASE} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            مدل‌های AI 🤖
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {viewMode === 'view' ? 'لیست همه مدل‌های هوش مصنوعی پشتیبانی شده' : 'مدیریت و تنظیمات مدل‌ها'}
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('view')}
            className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition ${
              viewMode === 'view'
                ? 'bg-white dark:bg-gray-700 shadow text-blue-600 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
            }`}
          >
            <EyeIcon className="w-4 h-4" />
            مشاهده
          </button>
          <button
            onClick={() => setViewMode('manage')}
            className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition ${
              viewMode === 'manage'
                ? 'bg-white dark:bg-gray-700 shadow text-purple-600 dark:text-purple-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
            }`}
          >
            <Cog6ToothIcon className="w-4 h-4" />
            مدیریت
          </button>
        </div>
      </div>

      {/* Provider Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {providers.map((provider) => (
          <div
            key={provider.provider}
            onClick={() => setFilter(provider.provider)}
            className={`card cursor-pointer transition-all ${
              filter === provider.provider
                ? 'ring-2 ring-primary-500'
                : ''
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              {provider.available ? (
                <CheckCircleIcon className="w-5 h-5 text-green-500" />
              ) : (
                <XCircleIcon className="w-5 h-5 text-gray-400" />
              )}
              <span className={`badge ${getProviderColor(provider.provider)}`}>
                {provider.provider}
              </span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {provider.model_count}
            </p>
            <p className="text-sm text-gray-500">مدل</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <FunnelIcon className="w-5 h-5 text-gray-400" />
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
              filter === 'all'
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
            }`}
          >
            همه ({models.length})
          </button>
          <button
            onClick={() => setFilter('available')}
            className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
              filter === 'available'
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
            }`}
          >
            فعال ({models.filter(m => m.enabled).length})
          </button>
        </div>
      </div>

      {/* VIEW MODE */}
      {viewMode === 'view' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredModels.map((model) => (
            <div
              key={model.id}
              className={`card ${!model.enabled ? 'opacity-60' : ''}`}  // 🔴 از enabled استفاده می‌کنیم
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white">
                    {model.name}
                  </h3>
                  <p className="text-sm text-gray-500">{model.id}</p>
                </div>
                <span className={`badge ${getProviderColor(model.provider)}`}>
                  {model.provider}
                </span>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-xs text-gray-500">Context</p>
                  <p className="font-medium">
                    {(model.context_window / 1000).toFixed(0)}K
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Max Tokens</p>
                  <p className="font-medium">{model.max_tokens}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">هزینه/1K</p>
                  <p className="font-medium">${model.cost_per_1k_tokens}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">اولویت</p>
                  <p className="font-medium">{model.priority}</p>
                </div>
              </div>

              {/* Capabilities */}
              <div className="flex flex-wrap gap-1 mb-4">
                {model.capabilities.slice(0, 4).map((cap) => (
                  <span
                    key={cap}
                    className="px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                  >
                    {cap}
                  </span>
                ))}
                {model.capabilities.length > 4 && (
                  <span className="px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                    +{model.capabilities.length - 4}
                  </span>
                )}
              </div>

              {/* Features */}
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
                {model.supports_images && (
                  <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300">
                    🖼️ تصویر
                  </span>
                )}
                {model.is_image_generator && (
                  <span className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-300">
                    🎨 تولید تصویر
                  </span>
                )}
                {/* 🔴 وضعیت enabled از دیتابیس - نه is_available */}
                {model.enabled ? (
                  <span className="px-2 py-0.5 rounded bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300">
                    ✓ فعال
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300">
                    ✕ غیرفعال
                  </span>
                )}
                {/* 🔴 وضعیت دسترسی به API */}
                {model.is_available ? (
                  <span className="px-2 py-0.5 rounded bg-cyan-100 dark:bg-cyan-900 text-cyan-600 dark:text-cyan-300">
                    API ✓
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
                    API ✕
                  </span>
                )}
              </div>

              {/* Capability Badges */}
              {capabilityResults[model.id] && (
                <div className="mb-3 pt-3 border-t dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-gray-500">نتیجه تست:</span>
                    <span className={`font-bold text-sm ${
                      capabilityResults[model.id].overall_score >= 80 ? 'text-green-500' :
                      capabilityResults[model.id].overall_score >= 60 ? 'text-yellow-500' : 'text-red-500'
                    }`}>
                      {capabilityResults[model.id].overall_score.toFixed(0)}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {capabilityResults[model.id].badges.slice(0, 3).map((badge, idx) => (
                      <span
                        key={idx}
                        className={`text-xs px-2 py-0.5 rounded-full ${getBadgeColor(badge.color)}`}
                        title={`${badge.label}: ${badge.score.toFixed(0)}`}
                      >
                        {badge.icon} {badge.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Test Button - فقط اگر هم enabled و هم is_available باشد */}
              {model.enabled && model.is_available && (
                <button
                  onClick={() => testModelCapability(model.id)}
                  disabled={testingModel === model.id}
                  className={`w-full py-2 rounded-lg text-sm flex items-center justify-center gap-2 transition ${
                    testingModel === model.id
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                      : 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 hover:bg-orange-200'
                  }`}
                >
                  {testingModel === model.id ? (
                    <>
                      <span className="animate-spin">⏳</span>
                      در حال تست...
                    </>
                  ) : (
                    <>
                      <BeakerIcon className="w-4 h-4" />
                      تست توانایی
                    </>
                  )}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* MANAGE MODE */}
      {viewMode === 'manage' && (
        <div className="space-y-4">
          {/* Task Types Legend */}
          <div className="card">
            <h3 className="font-bold mb-3">انواع کارها</h3>
            <div className="flex flex-wrap gap-2">
              {taskTypes.map(task => (
                <span
                  key={task.id}
                  className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm"
                  title={task.description}
                >
                  {task.name}
                </span>
              ))}
            </div>
          </div>

          {/* Models Management Table */}
          <div className="card overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b dark:border-gray-700">
                  <th className="text-right py-3 px-4">مدل</th>
                  <th className="text-center py-3 px-4">وضعیت</th>
                  <th className="text-center py-3 px-4">اولویت</th>
                  <th className="text-right py-3 px-4">کارهای مجاز</th>
                  <th className="text-right py-3 px-4">ترجیحی برای</th>
                  <th className="text-center py-3 px-4">عملیات</th>
                </tr>
              </thead>
              <tbody>
                {modelSettings.filter(s => {
                  if (filter === 'all') return true;
                  if (filter === 'available') {
                    const model = models.find(m => m.id === s.model_id);
                    return model?.is_available;
                  }
                  return s.provider === filter;
                }).map((setting) => {
                  const model = models.find(m => m.id === setting.model_id);
                  const isEditing = editingModel === setting.model_id;

                  return (
                    <tr key={setting.model_id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      {/* Model Name */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${model?.is_available ? 'bg-green-500' : 'bg-gray-400'}`} />
                          <div>
                            <div className="font-medium">{setting.model_name}</div>
                            <div className="text-xs text-gray-500">{setting.model_id}</div>
                          </div>
                          <span className={`badge text-xs ${getProviderColor(setting.provider)}`}>
                            {setting.provider}
                          </span>
                        </div>
                      </td>

                      {/* Status Toggle */}
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => toggleModelEnabled(setting.model_id)}
                          disabled={savingSettings === setting.model_id}
                          className={`relative w-12 h-6 rounded-full transition ${
                            setting.enabled
                              ? 'bg-green-500'
                              : 'bg-gray-300 dark:bg-gray-600'
                          }`}
                        >
                          <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${
                            setting.enabled ? 'right-1' : 'left-1'
                          }`} />
                        </button>
                      </td>

                      {/* Priority */}
                      <td className="py-3 px-4 text-center">
                        {isEditing ? (
                          <input
                            type="number"
                            min="1"
                            max="10"
                            defaultValue={setting.priority}
                            className="w-16 px-2 py-1 border rounded text-center dark:bg-gray-700 dark:border-gray-600"
                            id={`priority-${setting.model_id}`}
                          />
                        ) : (
                          <span className={`px-2 py-1 rounded ${
                            setting.priority <= 2 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                            setting.priority <= 4 ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                            'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                          }`}>
                            {setting.priority}
                          </span>
                        )}
                      </td>

                      {/* Allowed Tasks */}
                      <td className="py-3 px-4">
                        {isEditing ? (
                          <div className="flex flex-wrap gap-1">
                            {taskTypes.map(task => {
                              const isSelected = setting.allowed_tasks.includes(task.id) || setting.allowed_tasks.includes('all');
                              return (
                                <label key={task.id} className="flex items-center gap-1 text-xs cursor-pointer">
                                  <input
                                    type="checkbox"
                                    defaultChecked={isSelected}
                                    className="w-3 h-3"
                                    data-task={task.id}
                                    data-model={setting.model_id}
                                  />
                                  {task.name}
                                </label>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {setting.allowed_tasks.includes('all') ? (
                              <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded text-xs">
                                همه کارها
                              </span>
                            ) : (
                              setting.allowed_tasks.slice(0, 3).map(task => {
                                const taskInfo = taskTypes.find(t => t.id === task);
                                return (
                                  <span key={task} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                                    {taskInfo?.name || task}
                                  </span>
                                );
                              })
                            )}
                            {setting.allowed_tasks.length > 3 && !setting.allowed_tasks.includes('all') && (
                              <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                                +{setting.allowed_tasks.length - 3}
                              </span>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Preferred For */}
                      <td className="py-3 px-4">
                        {isEditing ? (
                          <div className="flex flex-wrap gap-1">
                            {taskTypes.filter(t => t.id !== 'all').map(task => {
                              const isPreferred = setting.preferred_for.includes(task.id);
                              return (
                                <label key={task.id} className="flex items-center gap-1 text-xs cursor-pointer">
                                  <input
                                    type="checkbox"
                                    defaultChecked={isPreferred}
                                    className="w-3 h-3"
                                    data-preferred={task.id}
                                    data-model={setting.model_id}
                                  />
                                  {task.name}
                                </label>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {setting.preferred_for.length === 0 ? (
                              <span className="text-xs text-gray-400">-</span>
                            ) : (
                              setting.preferred_for.map(task => {
                                const taskInfo = taskTypes.find(t => t.id === task);
                                return (
                                  <span key={task} className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded text-xs">
                                    ⭐ {taskInfo?.name || task}
                                  </span>
                                );
                              })
                            )}
                          </div>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          {isEditing ? (
                            <>
                              <button
                                onClick={() => {
                                  // Collect values
                                  const priorityInput = document.getElementById(`priority-${setting.model_id}`) as HTMLInputElement;
                                  const taskCheckboxes = document.querySelectorAll(`input[data-task][data-model="${setting.model_id}"]`);
                                  const preferredCheckboxes = document.querySelectorAll(`input[data-preferred][data-model="${setting.model_id}"]`);

                                  const allowedTasks: string[] = [];
                                  taskCheckboxes.forEach((cb: any) => {
                                    if (cb.checked) allowedTasks.push(cb.dataset.task);
                                  });

                                  const preferredFor: string[] = [];
                                  preferredCheckboxes.forEach((cb: any) => {
                                    if (cb.checked) preferredFor.push(cb.dataset.preferred);
                                  });

                                  updateModelSettings(setting.model_id, {
                                    priority: parseInt(priorityInput?.value || '5'),
                                    allowed_tasks: allowedTasks.length > 0 ? allowedTasks : ['all'],
                                    preferred_for: preferredFor,
                                  });
                                }}
                                disabled={savingSettings === setting.model_id}
                                className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600 disabled:opacity-50"
                              >
                                {savingSettings === setting.model_id ? '⏳' : '✓ ذخیره'}
                              </button>
                              <button
                                onClick={() => setEditingModel(null)}
                                className="px-3 py-1 bg-gray-200 dark:bg-gray-600 rounded text-xs hover:bg-gray-300"
                              >
                                انصراف
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => setEditingModel(setting.model_id)}
                                className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs hover:bg-blue-200"
                              >
                                ✏️ ویرایش
                              </button>
                              {setting.has_custom_settings && (
                                <button
                                  onClick={() => resetModelSettings(setting.model_id)}
                                  className="px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded text-xs hover:bg-red-200"
                                >
                                  🔄 بازنشانی
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Bulk Actions */}
          <div className="card">
            <h3 className="font-bold mb-3">عملیات گروهی</h3>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={async () => {
                  const updates = modelSettings.map(s => ({
                    model_id: s.model_id,
                    enabled: true,
                  }));
                  await fetch(`${API_BASE}/api/models/settings/batch-update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates),
                  });
                  await loadManagementData();
                  await loadData();  // 🔴 رفرش لیست models برای تب مشاهده
                  showSuccess('همه مدل‌ها فعال شدند');
                }}
                className="px-4 py-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg text-sm hover:bg-green-200"
              >
                ✓ فعال کردن همه
              </button>
              <button
                onClick={async () => {
                  const updates = modelSettings.map(s => ({
                    model_id: s.model_id,
                    enabled: false,
                  }));
                  await fetch(`${API_BASE}/api/models/settings/batch-update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates),
                  });
                  await loadManagementData();
                  await loadData();  // 🔴 رفرش لیست models برای تب مشاهده
                  showSuccess('همه مدل‌ها غیرفعال شدند');
                }}
                className="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm hover:bg-red-200"
              >
                ✕ غیرفعال کردن همه
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Results Panel */}
      {showTestPanel && selectedModel && capabilityResults[selectedModel] && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" dir="rtl">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800">
              <h3 className="font-bold flex items-center gap-2">
                <BeakerIcon className="w-5 h-5" />
                نتایج تست توانایی: {selectedModel}
              </h3>
              <button
                onClick={() => setShowTestPanel(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                ✕
              </button>
            </div>

            <div className="p-6">
              {(() => {
                const result = capabilityResults[selectedModel];
                if (!result) return <div className="text-gray-400 text-center py-8">نتیجه‌ای یافت نشد</div>;
                const score = result.overall_score ?? 0;
                return (
                  <>
                    {/* Header with badges */}
                    <div className="flex items-start gap-4 mb-6">
                      <div className={`w-20 h-20 rounded-xl flex flex-col items-center justify-center text-white ${
                        score >= 80 ? 'bg-gradient-to-br from-purple-500 to-purple-700' :
                        score >= 60 ? 'bg-gradient-to-br from-blue-500 to-blue-700' :
                        'bg-gradient-to-br from-gray-500 to-gray-700'
                      }`}>
                        <div className="text-2xl font-bold">{score.toFixed(0)}</div>
                        <div className="text-xs opacity-75">امتیاز کلی</div>
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-500 text-sm">
                          تست شده: {result.tested_at ? new Date(result.tested_at).toLocaleString('fa-IR') : '-'}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {(result.badges || []).map((badge, idx) => (
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

                    {/* Model Self Description */}
                    {result.self_description && (result.self_description.strengths || result.self_description.best_for) && (
                      <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <h4 className="font-bold mb-2">معرفی توسط مدل</h4>
                        {result.self_description.strengths && result.self_description.strengths.length > 0 && (
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
                        {result.self_description.best_for && result.self_description.best_for.length > 0 && (
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

                    {/* Category Scores */}
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

                    {/* Strengths and Weaknesses */}
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
          </div>
        </div>
      )}
    </div>
  );
}
