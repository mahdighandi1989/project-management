'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', key: 'OPENAI_API_KEY' },
  { id: 'anthropic', name: 'Claude', key: 'ANTHROPIC_API_KEY' },
  { id: 'google', name: 'Gemini', key: 'GOOGLE_API_KEY' },
  { id: 'deepseek', name: 'DeepSeek', key: 'DEEPSEEK_API_KEY' },
  { id: 'openrouter', name: 'OpenRouter', key: 'OPENROUTER_API_KEY' },
  { id: 'groq', name: 'Groq', key: 'GROQ_API_KEY' },
];

export default function SettingsPage() {
  const [tab, setTab] = useState<'keys' | 'config'>('keys');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // API Keys
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [keysStatus, setKeysStatus] = useState<Record<string, boolean>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

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
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const saveApiKeys = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings/api-keys`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiKeys),
      });

      if (res.ok) {
        showSuccess('کلیدها ذخیره شدند');
        setApiKeys({});
        loadData();
      } else {
        showError('خطا در ذخیره');
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

  const hasChanges = Object.keys(apiKeys).some((k) => apiKeys[k]?.trim());

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

      <div className="max-w-3xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">تنظیمات</h1>
            <p className="text-gray-500 text-sm">پیکربندی API و سیستم</p>
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
            onClick={() => setTab('keys')}
            className={`px-4 py-2 rounded-lg ${
              tab === 'keys'
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            کلیدهای API
          </button>
          <button
            onClick={() => setTab('config')}
            className={`px-4 py-2 rounded-lg ${
              tab === 'config'
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 hover:bg-gray-100'
            }`}
          >
            پیکربندی
          </button>
        </div>

        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <p className="text-gray-400 text-center">در حال بارگذاری...</p>
          </div>
        ) : tab === 'keys' ? (
          // کلیدهای API
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold mb-4">کلیدهای API</h2>
            <p className="text-sm text-gray-500 mb-6">
              برای استفاده از مدل‌ها، کلید API هر سرویس را وارد کنید
            </p>

            <div className="space-y-4">
              {PROVIDERS.map((provider) => (
                <div key={provider.id}>
                  <div className="flex items-center justify-between mb-2">
                    <label className="font-medium">{provider.name}</label>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        keysStatus[provider.id]
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {keysStatus[provider.id] ? 'فعال' : 'غیرفعال'}
                    </span>
                  </div>
                  <div className="relative">
                    <input
                      type={showKeys[provider.id] ? 'text' : 'password'}
                      placeholder={`${provider.key}...`}
                      value={apiKeys[provider.id] || ''}
                      onChange={(e) =>
                        setApiKeys({ ...apiKeys, [provider.id]: e.target.value })
                      }
                      className="w-full p-3 pr-12 border rounded-lg dark:bg-gray-700 dark:border-gray-600 font-mono text-sm"
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
              disabled={saving || !hasChanges}
              className="w-full mt-6 py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 disabled:opacity-50"
            >
              {saving ? 'در حال ذخیره...' : 'ذخیره کلیدها'}
            </button>
          </div>
        ) : (
          // پیکربندی
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold mb-4">پیکربندی سیستم</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  حداکثر توکن ({config.max_tokens})
                </label>
                <input
                  type="range"
                  min="100"
                  max="128000"
                  step="100"
                  value={config.max_tokens}
                  onChange={(e) =>
                    setConfig({ ...config, max_tokens: parseInt(e.target.value) })
                  }
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  دما ({config.temperature})
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
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  تایم‌اوت درخواست (ثانیه)
                </label>
                <input
                  type="number"
                  min="10"
                  max="600"
                  value={config.request_timeout}
                  onChange={(e) =>
                    setConfig({ ...config, request_timeout: parseInt(e.target.value) })
                  }
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  تعداد تلاش مجدد
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={config.max_retries}
                  onChange={(e) =>
                    setConfig({ ...config, max_retries: parseInt(e.target.value) })
                  }
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                />
              </div>
            </div>

            <button
              onClick={saveConfig}
              disabled={saving}
              className="w-full mt-6 py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 disabled:opacity-50"
            >
              {saving ? 'در حال ذخیره...' : 'ذخیره تنظیمات'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
