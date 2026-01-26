'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// تعریف providers
const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', icon: '🤖', env: 'OPENAI_API_KEY' },
  { id: 'claude', name: 'Claude', icon: '🟣', env: 'CLAUDE_API_KEY' },
  { id: 'gemini', name: 'Gemini', icon: '💎', env: 'GEMINI_API_KEY' },
  { id: 'deepseek', name: 'DeepSeek', icon: '🔍', env: 'DEEPSEEK_API_KEY' },
  { id: 'openrouter', name: 'OpenRouter', icon: '🌐', env: 'OPENROUTER_API_KEY' },
  { id: 'groq', name: 'Groq', icon: '⚡', env: 'GROQ_API_KEY' },
  { id: 'perplexity', name: 'Perplexity AI', icon: '🔮', env: 'PERPLEXITY_API_KEY' },  // 🆕
];

// سرویس‌های Deploy
const DEPLOY_SERVICES = [
  { id: 'render', name: 'Render', icon: '🚀', desc: 'برای Deploy خودکار پروژه‌ها' },
  { id: 'github', name: 'GitHub Token', icon: '🐙', desc: 'برای دسترسی به ریپوهای Private و Push' },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'api' | 'deploy' | 'config'>('api');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // کلیدهای API
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [keysStatus, setKeysStatus] = useState<Record<string, boolean>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  // کلیدهای Deploy
  const [deployKeys, setDeployKeys] = useState<Record<string, string>>({});

  // Config
  const [config, setConfig] = useState({
    max_tokens: 4096,
    temperature: 0.7,
    request_timeout: 60,
    max_retries: 3,
  });

  useEffect(() => {
    loadData();
  }, []);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // وضعیت کلیدها
      const statusRes = await fetch(`${API_BASE}/api/settings/api-keys/status`);
      if (statusRes.ok) {
        const data = await statusRes.json();
        setKeysStatus(data || {});
      }

      // تنظیمات
      const configRes = await fetch(`${API_BASE}/api/config`);
      if (configRes.ok) {
        const data = await configRes.json();
        if (data) {
          setConfig({
            max_tokens: data.max_tokens || 4096,
            temperature: data.temperature || 0.7,
            request_timeout: data.request_timeout || 60,
            max_retries: data.max_retries || 3,
          });
        }
      }
    } catch (e) {
      console.error('Error loading settings:', e);
      // Settings load failed - will use defaults
    } finally {
      setLoading(false);
    }
  };

  const saveApiKeys = async () => {
    // فقط کلیدهایی که مقدار دارن رو بفرست
    const keysToSave: Record<string, string> = {};
    for (const [key, value] of Object.entries(apiKeys)) {
      if (value && value.trim()) {
        keysToSave[key] = value.trim();
      }
    }

    if (Object.keys(keysToSave).length === 0) {
      showError('هیچ کلیدی وارد نشده');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings/api-keys`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keysToSave),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        showSuccess(`${data.updated?.length || 0} کلید AI ذخیره شد`);
        setApiKeys({});
        loadData();
      } else {
        showError(data.detail || 'خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSaving(false);
    }
  };

  const saveDeployKeys = async () => {
    // ذخیره کلیدهای Deploy
    const keysToSave: Record<string, string> = {};
    for (const [key, value] of Object.entries(deployKeys)) {
      if (value && value.trim()) {
        keysToSave[key] = value.trim();
      }
    }

    if (Object.keys(keysToSave).length === 0) {
      showError('هیچ کلیدی وارد نشده');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings/deploy-keys`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keysToSave),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        showSuccess('کلیدهای Deploy ذخیره شدند');
        setDeployKeys({});
      } else {
        showError(data.detail || 'خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSaving(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (res.ok) {
        showSuccess('تنظیمات ذخیره شدند');
      } else {
        showError('خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSaving(false);
    }
  };

  const hasApiChanges = Object.keys(apiKeys).some((k) => apiKeys[k]?.trim());
  const hasDeployChanges = Object.keys(deployKeys).some((k) => deployKeys[k]?.trim());

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

      <div className="max-w-4xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">تنظیمات</h1>
            <p className="text-gray-500 text-sm">کلیدهای API، Deploy و پیکربندی</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
          >
            خانه
          </Link>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('api')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'api'
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            🤖 کلیدهای AI
          </button>
          <button
            onClick={() => setActiveTab('deploy')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'deploy'
                ? 'bg-green-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            🚀 Deploy
          </button>
          <button
            onClick={() => setActiveTab('config')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'config'
                ? 'bg-purple-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            ⚙️ پیکربندی
          </button>
        </div>

        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <p className="text-gray-400 text-center">در حال بارگذاری...</p>
          </div>
        ) : activeTab === 'api' ? (
          // کلیدهای AI
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold text-lg mb-2">کلیدهای API مدل‌های AI</h2>
            <p className="text-sm text-gray-500 mb-6">
              برای استفاده از موتور خالق، حداقل یک کلید API وارد کنید
            </p>

            <div className="space-y-4">
              {PROVIDERS.map((provider) => (
                <div key={provider.id} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{provider.icon}</span>
                      <span className="font-medium">{provider.name}</span>
                    </div>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        keysStatus[provider.id]
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-200 text-gray-500'
                      }`}
                    >
                      {keysStatus[provider.id] ? '✓ فعال' : 'غیرفعال'}
                    </span>
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys[provider.id] ? 'text' : 'password'}
                      placeholder={`کلید ${provider.name} را وارد کنید...`}
                      value={apiKeys[provider.id] || ''}
                      onChange={(e) =>
                        setApiKeys({ ...apiKeys, [provider.id]: e.target.value })
                      }
                      className="w-full p-3 pr-12 border rounded-lg dark:bg-gray-600 dark:border-gray-500 font-mono text-sm"
                      dir="ltr"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setShowKeys({ ...showKeys, [provider.id]: !showKeys[provider.id] })
                      }
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showKeys[provider.id] ? '🙈' : '👁️'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={saveApiKeys}
              disabled={saving || !hasApiChanges}
              className="w-full mt-6 py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 disabled:opacity-50"
            >
              {saving ? 'در حال ذخیره...' : '💾 ذخیره کلیدهای AI'}
            </button>
          </div>
        ) : activeTab === 'deploy' ? (
          // کلیدهای Deploy
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold text-lg mb-2">کلیدهای Deploy</h2>
            <p className="text-sm text-gray-500 mb-6">
              برای Deploy یک کلیکی پروژه‌ها به Render و Push به GitHub
            </p>

            <div className="space-y-4">
              {DEPLOY_SERVICES.map((service) => (
                <div key={service.id} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{service.icon}</span>
                      <div>
                        <span className="font-medium">{service.name}</span>
                        <p className="text-xs text-gray-500">{service.desc}</p>
                      </div>
                    </div>
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys[service.id] ? 'text' : 'password'}
                      placeholder={`کلید ${service.name} را وارد کنید...`}
                      value={deployKeys[service.id] || ''}
                      onChange={(e) =>
                        setDeployKeys({ ...deployKeys, [service.id]: e.target.value })
                      }
                      className="w-full p-3 pr-12 border rounded-lg dark:bg-gray-600 dark:border-gray-500 font-mono text-sm"
                      dir="ltr"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setShowKeys({ ...showKeys, [service.id]: !showKeys[service.id] })
                      }
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showKeys[service.id] ? '🙈' : '👁️'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={saveDeployKeys}
              disabled={saving || !hasDeployChanges}
              className="w-full mt-6 py-3 bg-green-500 text-white rounded-lg font-bold hover:bg-green-600 disabled:opacity-50"
            >
              {saving ? 'در حال ذخیره...' : '💾 ذخیره کلیدهای Deploy'}
            </button>

            {/* راهنما */}
            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
              <h3 className="font-medium mb-2">📌 راهنمای دریافت کلید:</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-2">
                <li>
                  <strong>🚀 Render:</strong>
                  <br />
                  Dashboard → Account Settings → API Keys → Create API Key
                </li>
                <li>
                  <strong>🐙 GitHub Token:</strong>
                  <br />
                  1. به <a href="https://github.com/settings/tokens" target="_blank" className="text-blue-500 underline">github.com/settings/tokens</a> برید
                  <br />
                  2. روی <strong>Generate new token (classic)</strong> کلیک کنید
                  <br />
                  3. تیک <strong>repo</strong> رو بزنید (دسترسی کامل)
                  <br />
                  4. Generate token و کپی کنید
                </li>
              </ul>
            </div>

            {/* نکته مهم */}
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/30 rounded-lg border border-green-200 dark:border-green-800">
              <h3 className="font-medium mb-1 text-green-700 dark:text-green-300">💡 نکته مهم</h3>
              <p className="text-sm text-green-600 dark:text-green-400">
                با یک توکن GitHub می‌تونید به <strong>همه ریپوهای Private</strong> زیر اکانتتون دسترسی داشته باشید.
                بعد از ذخیره، در صفحه پروژه‌ها نیازی به وارد کردن مجدد توکن نیست!
              </p>
            </div>
          </div>
        ) : (
          // پیکربندی
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold text-lg mb-4">پیکربندی سیستم</h2>

            <div className="space-y-6">
              {/* Max Tokens */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  حداکثر توکن: <span className="text-blue-500">{config.max_tokens}</span>
                </label>
                <input
                  type="range"
                  min="1000"
                  max="32000"
                  step="1000"
                  value={config.max_tokens}
                  onChange={(e) =>
                    setConfig({ ...config, max_tokens: parseInt(e.target.value) })
                  }
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1,000</span>
                  <span>32,000</span>
                </div>
              </div>

              {/* Temperature */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  دما (خلاقیت): <span className="text-blue-500">{config.temperature}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.temperature}
                  onChange={(e) =>
                    setConfig({ ...config, temperature: parseFloat(e.target.value) })
                  }
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>دقیق (0)</span>
                  <span>خلاق (2)</span>
                </div>
              </div>

              {/* Timeout */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  تایم‌اوت (ثانیه): <span className="text-blue-500">{config.request_timeout}</span>
                </label>
                <input
                  type="range"
                  min="30"
                  max="300"
                  step="30"
                  value={config.request_timeout}
                  onChange={(e) =>
                    setConfig({ ...config, request_timeout: parseInt(e.target.value) })
                  }
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>30s</span>
                  <span>300s</span>
                </div>
              </div>

              {/* Retries */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  تلاش مجدد: <span className="text-blue-500">{config.max_retries}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="5"
                  step="1"
                  value={config.max_retries}
                  onChange={(e) =>
                    setConfig({ ...config, max_retries: parseInt(e.target.value) })
                  }
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>5</span>
                </div>
              </div>
            </div>

            <button
              onClick={saveConfig}
              disabled={saving}
              className="w-full mt-6 py-3 bg-purple-500 text-white rounded-lg font-bold hover:bg-purple-600 disabled:opacity-50"
            >
              {saving ? 'در حال ذخیره...' : '💾 ذخیره تنظیمات'}
            </button>
          </div>
        )}

        {/* لینک‌ها */}
        <div className="mt-6 flex justify-center gap-4 text-sm">
          <Link href="/creator" className="text-blue-500 hover:underline">
            موتور خالق
          </Link>
          <Link href="/projects" className="text-blue-500 hover:underline">
            پروژه‌ها
          </Link>
        </div>
      </div>
    </div>
  );
}
