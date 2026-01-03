/**
 * Settings Page - Manage API keys and configuration
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
} from '@heroicons/react/24/outline';

interface ApiKeyInput {
  key: string;
  visible: boolean;
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [config, setConfig] = useState<any>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

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
    } catch (err) {
      console.error('Error loading settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
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
      setMessage({ type: 'success', text: 'کلیدها با موفقیت ذخیره شدند. لطفاً صفحه را رفرش کنید.' });

      // Reset inputs
      setApiKeys((prev) => {
        const updated = { ...prev };
        Object.keys(updated).forEach((key) => {
          updated[key] = { key: '', visible: false };
        });
        return updated;
      });

      // Reload status
      await loadData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'خطا در ذخیره کلیدها' });
    } finally {
      setSaving(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner w-12 h-12" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          تنظیمات ⚙️
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          مدیریت API Keys و پیکربندی سیستم
        </p>
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

      {/* API Keys */}
      <div className="card">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <KeyIcon className="w-5 h-5" />
          کلیدهای API
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          برای فعال‌سازی هر provider، کلید API مربوطه را وارد کنید.
          کلیدها فقط در حافظه سرور ذخیره می‌شوند.
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
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary flex items-center gap-2"
          >
            {saving ? (
              <div className="spinner w-5 h-5" />
            ) : (
              <CheckIcon className="w-5 h-5" />
            )}
            ذخیره تغییرات
          </button>
        </div>
      </div>

      {/* Current Config */}
      {config && (
        <div className="card">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
            پیکربندی فعلی
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">حداکثر توکن/مدل</p>
              <p className="font-medium">{config.max_tokens_per_model}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">حداکثر طول پرامپت</p>
              <p className="font-medium">{(config.max_prompt_length / 1000).toFixed(0)}K</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Timeout درخواست</p>
              <p className="font-medium">{config.request_timeout}s</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">حداکثر زمان/مدل</p>
              <p className="font-medium">{config.max_model_time}s</p>
            </div>
          </div>
        </div>
      )}

      {/* Help Links */}
      <div className="card bg-gray-50 dark:bg-gray-800">
        <h3 className="font-bold text-gray-900 dark:text-white mb-4">
          راهنمای دریافت API Key
        </h3>
        <ul className="space-y-2 text-sm">
          <li>
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline"
            >
              🟢 OpenAI → platform.openai.com/api-keys
            </a>
          </li>
          <li>
            <a
              href="https://console.anthropic.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline"
            >
              🟣 Claude → console.anthropic.com
            </a>
          </li>
          <li>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline"
            >
              🔵 Gemini → aistudio.google.com/app/apikey
            </a>
          </li>
          <li>
            <a
              href="https://platform.deepseek.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline"
            >
              🟡 DeepSeek → platform.deepseek.com
            </a>
          </li>
        </ul>
      </div>
    </div>
  );
}
