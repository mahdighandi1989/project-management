/**
 * Settings Page - Manage API keys, configuration, and external systems
 */

'use client';

import { useState, useEffect } from 'react';
import { settingsApi } from '@/services/api';
import {
  KeyIcon,
  EyeIcon,
  EyeSlashIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  Cog6ToothIcon,
  GlobeAltIcon,
  PlusIcon,
  TrashIcon,
  ArrowPathIcon,
  SignalIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';

function getApiUrl(): string {
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
    return process.env.NEXT_PUBLIC_API_URL || 'https://ai-creator-engine-backend.onrender.com';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

interface ApiKeyInput {
  key: string;
  visible: boolean;
}

interface ExternalSystem {
  id: string;
  name: string;
  base_url: string;
  status: 'active' | 'error' | 'unknown';
  last_check?: string;
  health_status?: {
    healthy: boolean;
    response_time?: number;
    error?: string;
  };
  discovered_endpoints?: number;
}

interface ConfigValues {
  max_tokens_per_model: number;
  max_prompt_length: number;
  request_timeout: number;
  max_model_time: number;
  temperature: number;
  max_retries: number;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'api-keys' | 'config' | 'external'>('api-keys');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [config, setConfig] = useState<ConfigValues | null>(null);
  const [editedConfig, setEditedConfig] = useState<ConfigValues | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // External systems state
  const [externalSystems, setExternalSystems] = useState<ExternalSystem[]>([]);
  const [showAddSystem, setShowAddSystem] = useState(false);
  const [newSystem, setNewSystem] = useState({ name: '', base_url: '', api_key: '' });
  const [checkingSystem, setCheckingSystem] = useState<string | null>(null);

  const [apiKeys, setApiKeys] = useState<Record<string, ApiKeyInput>>({
    openai: { key: '', visible: false },
    claude: { key: '', visible: false },
    gemini: { key: '', visible: false },
    deepseek: { key: '', visible: false },
    openrouter: { key: '', visible: false },
    groq: { key: '', visible: false },
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statusRes, configRes] = await Promise.all([
        settingsApi.apiKeysStatus(),
        settingsApi.config(),
      ]);
      setStatus(statusRes.data);
      setConfig(configRes.data);
      setEditedConfig(configRes.data);

      // Load external systems
      try {
        const extRes = await fetch(`${getApiUrl()}/api/external/systems`);
        if (extRes.ok) {
          const data = await extRes.json();
          setExternalSystems(data.systems || []);
        }
      } catch (e) {
        console.log('External systems not available');
      }
    } catch (err) {
      console.error('Error loading settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveApiKeys = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const keysToUpdate: Record<string, string> = {};
      Object.entries(apiKeys).forEach(([provider, data]) => {
        if (data.key.trim()) {
          keysToUpdate[provider] = data.key.trim();
        }
      });

      if (Object.keys(keysToUpdate).length === 0) {
        setMessage({ type: 'error', text: 'هیچ کلیدی وارد نشده است' });
        return;
      }

      await settingsApi.updateApiKeys(keysToUpdate);
      setMessage({ type: 'success', text: 'کلیدها با موفقیت ذخیره شدند' });

      setApiKeys((prev) => {
        const updated = { ...prev };
        Object.keys(updated).forEach((key) => {
          updated[key] = { key: '', visible: false };
        });
        return updated;
      });

      await loadData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'خطا در ذخیره کلیدها' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!editedConfig) return;
    setSaving(true);
    setMessage(null);

    try {
      const res = await fetch(`${getApiUrl()}/api/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editedConfig),
      });

      if (res.ok) {
        setConfig(editedConfig);
        setMessage({ type: 'success', text: 'تنظیمات با موفقیت ذخیره شد' });
      } else {
        throw new Error('Failed to save config');
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'خطا در ذخیره تنظیمات' });
    } finally {
      setSaving(false);
    }
  };

  const handleAutoAdjust = async (taskType: string) => {
    setSaving(true);
    setMessage(null);

    try {
      const res = await fetch(`${getApiUrl()}/api/config/auto-adjust`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: taskType, complexity: 'medium' }),
      });

      if (res.ok) {
        const data = await res.json();
        setEditedConfig(prev => ({
          ...prev!,
          max_tokens_per_model: data.recommended.max_tokens,
          temperature: data.recommended.temperature,
          request_timeout: data.recommended.timeout,
        }));
        setMessage({ type: 'success', text: `تنظیمات برای "${taskType}" بهینه شد` });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'خطا در تنظیم خودکار' });
    } finally {
      setSaving(false);
    }
  };

  const handleAddExternalSystem = async () => {
    if (!newSystem.name || !newSystem.base_url) {
      setMessage({ type: 'error', text: 'نام و آدرس سیستم الزامی است' });
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/external/systems`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSystem),
      });

      if (res.ok) {
        const data = await res.json();
        setExternalSystems(prev => [...prev, data.system]);
        setNewSystem({ name: '', base_url: '', api_key: '' });
        setShowAddSystem(false);
        setMessage({ type: 'success', text: 'سیستم با موفقیت اضافه شد' });
      } else {
        throw new Error('Failed to add system');
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'خطا در اضافه کردن سیستم' });
    } finally {
      setSaving(false);
    }
  };

  const handleHealthCheck = async (systemId: string) => {
    setCheckingSystem(systemId);
    try {
      const res = await fetch(`${getApiUrl()}/api/external/systems/${systemId}/health-check`, {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        setExternalSystems(prev => prev.map(sys =>
          sys.id === systemId
            ? { ...sys, health_status: data.result, status: data.result.healthy ? 'active' : 'error' }
            : sys
        ));
      }
    } catch (err) {
      console.error('Health check failed:', err);
    } finally {
      setCheckingSystem(null);
    }
  };

  const handleDiscoverApi = async (systemId: string) => {
    setCheckingSystem(systemId);
    try {
      const res = await fetch(`${getApiUrl()}/api/external/systems/${systemId}/discover`, {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        setExternalSystems(prev => prev.map(sys =>
          sys.id === systemId
            ? { ...sys, discovered_endpoints: data.discovery?.endpoints?.length || 0 }
            : sys
        ));
        setMessage({ type: 'success', text: `${data.discovery?.endpoints?.length || 0} endpoint کشف شد` });
      }
    } catch (err) {
      console.error('Discovery failed:', err);
    } finally {
      setCheckingSystem(null);
    }
  };

  const handleDeleteSystem = async (systemId: string) => {
    try {
      const res = await fetch(`${getApiUrl()}/api/external/systems/${systemId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        setExternalSystems(prev => prev.filter(sys => sys.id !== systemId));
        setMessage({ type: 'success', text: 'سیستم حذف شد' });
      }
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const toggleVisibility = (provider: string) => {
    setApiKeys((prev) => ({
      ...prev,
      [provider]: { ...prev[provider], visible: !prev[provider].visible },
    }));
  };

  const updateKey = (provider: string, value: string) => {
    setApiKeys((prev) => ({
      ...prev,
      [provider]: { ...prev[provider], key: value },
    }));
  };

  const providers = [
    { id: 'openai', name: 'OpenAI', emoji: '🟢', placeholder: 'sk-...' },
    { id: 'claude', name: 'Claude (Anthropic)', emoji: '🟣', placeholder: 'sk-ant-...' },
    { id: 'gemini', name: 'Gemini (Google)', emoji: '🔵', placeholder: 'AIza...' },
    { id: 'deepseek', name: 'DeepSeek', emoji: '🟡', placeholder: 'sk-...' },
    { id: 'openrouter', name: 'OpenRouter', emoji: '🟠', placeholder: 'sk-or-...' },
    { id: 'groq', name: 'Groq', emoji: '⚪', placeholder: 'gsk_...' },
  ];

  const taskTypes = [
    { id: 'code_generation', label: 'تولید کد', icon: '💻' },
    { id: 'analysis', label: 'تحلیل', icon: '🔍' },
    { id: 'large_file', label: 'فایل بزرگ', icon: '📁' },
    { id: 'creative', label: 'خلاقانه', icon: '🎨' },
    { id: 'quick_task', label: 'سریع', icon: '⚡' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner w-12 h-12" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          تنظیمات
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          مدیریت API Keys، پیکربندی سیستم و سیستم‌های خارجی
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('api-keys')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'api-keys'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <KeyIcon className="w-5 h-5 inline ml-2" />
          کلیدهای API
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'config'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Cog6ToothIcon className="w-5 h-5 inline ml-2" />
          پیکربندی
        </button>
        <button
          onClick={() => setActiveTab('external')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'external'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <GlobeAltIcon className="w-5 h-5 inline ml-2" />
          سیستم‌های خارجی
        </button>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`card ${
            message.type === 'success'
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          }`}
        >
          <div className="flex items-center gap-3">
            {message.type === 'success' ? (
              <CheckIcon className="w-6 h-6 text-green-500" />
            ) : (
              <ExclamationTriangleIcon className="w-6 h-6 text-red-500" />
            )}
            <span>{message.text}</span>
          </div>
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api-keys' && (
        <div className="card">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <KeyIcon className="w-5 h-5" />
            کلیدهای API
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            برای فعال‌سازی هر provider، کلید API مربوطه را وارد کنید.
          </p>

          <div className="space-y-4">
            {providers.map((provider) => (
              <div key={provider.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 font-medium text-gray-700 dark:text-gray-300">
                    <span>{provider.emoji}</span>
                    {provider.name}
                  </label>
                  <span
                    className={`badge ${
                      status[provider.id]
                        ? 'badge-success'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-500'
                    }`}
                  >
                    {status[provider.id] ? '✓ فعال' : 'غیرفعال'}
                  </span>
                </div>
                <div className="relative">
                  <input
                    type={apiKeys[provider.id]?.visible ? 'text' : 'password'}
                    value={apiKeys[provider.id]?.key || ''}
                    onChange={(e) => updateKey(provider.id, e.target.value)}
                    placeholder={provider.placeholder}
                    className="input pl-10"
                  />
                  <button
                    type="button"
                    onClick={() => toggleVisibility(provider.id)}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {apiKeys[provider.id]?.visible ? (
                      <EyeSlashIcon className="w-5 h-5" />
                    ) : (
                      <EyeIcon className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <button
              onClick={handleSaveApiKeys}
              disabled={saving}
              className="btn btn-primary flex items-center gap-2"
            >
              {saving ? <div className="spinner w-5 h-5" /> : <CheckIcon className="w-5 h-5" />}
              ذخیره کلیدها
            </button>
          </div>
        </div>
      )}

      {/* Config Tab */}
      {activeTab === 'config' && editedConfig && (
        <div className="space-y-6">
          {/* Auto-Adjust Section */}
          <div className="card bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <SparklesIcon className="w-5 h-5 text-purple-500" />
              تنظیم خودکار بر اساس نوع کار
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              با انتخاب نوع کار، تنظیمات به صورت خودکار بهینه می‌شوند
            </p>
            <div className="flex flex-wrap gap-2">
              {taskTypes.map(task => (
                <button
                  key={task.id}
                  onClick={() => handleAutoAdjust(task.id)}
                  disabled={saving}
                  className="px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow flex items-center gap-2"
                >
                  <span>{task.icon}</span>
                  {task.label}
                </button>
              ))}
            </div>
          </div>

          {/* Manual Config */}
          <div className="card">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <AdjustmentsHorizontalIcon className="w-5 h-5" />
              تنظیمات دستی
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  حداکثر توکن/مدل
                </label>
                <input
                  type="number"
                  value={editedConfig.max_tokens_per_model}
                  onChange={(e) => setEditedConfig({ ...editedConfig, max_tokens_per_model: parseInt(e.target.value) })}
                  className="input"
                  min={100}
                  max={128000}
                />
                <p className="text-xs text-gray-500 mt-1">100 - 128,000</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  حداکثر طول پرامپت
                </label>
                <input
                  type="number"
                  value={editedConfig.max_prompt_length}
                  onChange={(e) => setEditedConfig({ ...editedConfig, max_prompt_length: parseInt(e.target.value) })}
                  className="input"
                  min={1000}
                  max={500000}
                />
                <p className="text-xs text-gray-500 mt-1">1,000 - 500,000 کاراکتر</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Timeout درخواست (ثانیه)
                </label>
                <input
                  type="number"
                  value={editedConfig.request_timeout}
                  onChange={(e) => setEditedConfig({ ...editedConfig, request_timeout: parseInt(e.target.value) })}
                  className="input"
                  min={10}
                  max={600}
                />
                <p className="text-xs text-gray-500 mt-1">10 - 600 ثانیه</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  حداکثر زمان/مدل (ثانیه)
                </label>
                <input
                  type="number"
                  value={editedConfig.max_model_time}
                  onChange={(e) => setEditedConfig({ ...editedConfig, max_model_time: parseInt(e.target.value) })}
                  className="input"
                  min={10}
                  max={300}
                />
                <p className="text-xs text-gray-500 mt-1">10 - 300 ثانیه</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Temperature
                </label>
                <input
                  type="range"
                  value={editedConfig.temperature}
                  onChange={(e) => setEditedConfig({ ...editedConfig, temperature: parseFloat(e.target.value) })}
                  className="w-full"
                  min={0}
                  max={2}
                  step={0.1}
                />
                <p className="text-sm text-center font-mono">{editedConfig.temperature}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  حداکثر تلاش مجدد
                </label>
                <input
                  type="number"
                  value={editedConfig.max_retries}
                  onChange={(e) => setEditedConfig({ ...editedConfig, max_retries: parseInt(e.target.value) })}
                  className="input"
                  min={0}
                  max={10}
                />
                <p className="text-xs text-gray-500 mt-1">0 - 10</p>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={handleSaveConfig}
                disabled={saving}
                className="btn btn-primary flex items-center gap-2"
              >
                {saving ? <div className="spinner w-5 h-5" /> : <CheckIcon className="w-5 h-5" />}
                ذخیره تنظیمات
              </button>
              <button
                onClick={() => setEditedConfig(config)}
                className="btn bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
              >
                بازگشت به پیش‌فرض
              </button>
            </div>
          </div>
        </div>
      )}

      {/* External Systems Tab */}
      {activeTab === 'external' && (
        <div className="space-y-6">
          {/* Add System Button */}
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                سیستم‌های خارجی متصل
              </h3>
              <p className="text-sm text-gray-500">
                اتصال به API‌های خارجی برای مانیتورینگ و مدیریت
              </p>
            </div>
            <button
              onClick={() => setShowAddSystem(true)}
              className="btn btn-primary flex items-center gap-2"
            >
              <PlusIcon className="w-5 h-5" />
              اضافه کردن سیستم
            </button>
          </div>

          {/* Add System Modal */}
          {showAddSystem && (
            <div className="card border-2 border-primary-200 dark:border-primary-800">
              <h4 className="font-bold mb-4">اضافه کردن سیستم جدید</h4>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">نام سیستم</label>
                  <input
                    type="text"
                    value={newSystem.name}
                    onChange={(e) => setNewSystem({ ...newSystem, name: e.target.value })}
                    placeholder="مثال: Trading Backend"
                    className="input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">آدرس API</label>
                  <input
                    type="url"
                    value={newSystem.base_url}
                    onChange={(e) => setNewSystem({ ...newSystem, base_url: e.target.value })}
                    placeholder="https://api.example.com"
                    className="input"
                    dir="ltr"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">API Key (اختیاری)</label>
                  <input
                    type="password"
                    value={newSystem.api_key}
                    onChange={(e) => setNewSystem({ ...newSystem, api_key: e.target.value })}
                    placeholder="اگر سیستم نیاز به احراز هویت دارد"
                    className="input"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleAddExternalSystem}
                    disabled={saving}
                    className="btn btn-primary"
                  >
                    {saving ? <div className="spinner w-5 h-5" /> : 'اضافه کن'}
                  </button>
                  <button
                    onClick={() => setShowAddSystem(false)}
                    className="btn bg-gray-100 dark:bg-gray-700"
                  >
                    انصراف
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Systems List */}
          {externalSystems.length === 0 ? (
            <div className="card text-center py-12">
              <GlobeAltIcon className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <h4 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">
                هیچ سیستمی متصل نیست
              </h4>
              <p className="text-gray-500 mb-4">
                با اضافه کردن سیستم خارجی، می‌توانید آن را مانیتور کنید
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {externalSystems.map((system) => (
                <div
                  key={system.id}
                  className="card border hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="font-bold text-gray-900 dark:text-white">
                          {system.name}
                        </h4>
                        <span
                          className={`badge ${
                            system.status === 'active'
                              ? 'badge-success'
                              : system.status === 'error'
                              ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              : 'bg-gray-100 text-gray-600 dark:bg-gray-700'
                          }`}
                        >
                          {system.status === 'active' ? '✓ فعال' : system.status === 'error' ? '✗ خطا' : '? نامشخص'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 font-mono mb-2" dir="ltr">
                        {system.base_url}
                      </p>
                      {system.health_status && (
                        <div className="text-sm">
                          {system.health_status.healthy ? (
                            <span className="text-green-600">
                              پاسخ‌دهی: {system.health_status.response_time?.toFixed(0)}ms
                            </span>
                          ) : (
                            <span className="text-red-600">
                              خطا: {system.health_status.error}
                            </span>
                          )}
                        </div>
                      )}
                      {system.discovered_endpoints !== undefined && (
                        <p className="text-sm text-blue-600 mt-1">
                          {system.discovered_endpoints} endpoint کشف شده
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleHealthCheck(system.id)}
                        disabled={checkingSystem === system.id}
                        className="p-2 rounded-lg bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-900/20 dark:hover:bg-green-900/40"
                        title="بررسی سلامت"
                      >
                        {checkingSystem === system.id ? (
                          <div className="spinner w-5 h-5" />
                        ) : (
                          <SignalIcon className="w-5 h-5" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDiscoverApi(system.id)}
                        disabled={checkingSystem === system.id}
                        className="p-2 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:hover:bg-blue-900/40"
                        title="کشف API"
                      >
                        <MagnifyingGlassIcon className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteSystem(system.id)}
                        className="p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40"
                        title="حذف"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Instructions */}
          <div className="card bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <h4 className="font-bold text-blue-800 dark:text-blue-300 mb-2">
              راهنما
            </h4>
            <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1 list-disc list-inside">
              <li>سیستم‌های با OpenAPI/Swagger به صورت خودکار کشف می‌شوند</li>
              <li>بررسی سلامت هر 5 دقیقه به صورت خودکار انجام می‌شود</li>
              <li>در صورت بروز خطا، اعلان دریافت خواهید کرد</li>
              <li>می‌توانید با AI تحلیل سیستم خارجی را انجام دهید</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
