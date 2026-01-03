/**
 * Models Page - View and manage AI models
 */

'use client';

import { useState, useEffect } from 'react';
import { modelsApi, Model, ProviderStatus } from '@/services/api';
import {
  CheckCircleIcon,
  XCircleIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, []);

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

  const filteredModels = filter === 'all'
    ? models
    : filter === 'available'
      ? models.filter(m => m.is_available)
      : models.filter(m => m.provider === filter);

  const getProviderColor = (provider: string) => {
    const colors: Record<string, string> = {
      openai: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      claude: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      gemini: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      deepseek: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    };
    return colors[provider] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner w-12 h-12" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          مدل‌های AI 🤖
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          لیست همه مدل‌های هوش مصنوعی پشتیبانی شده
        </p>
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
            فعال ({models.filter(m => m.is_available).length})
          </button>
        </div>
      </div>

      {/* Models Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredModels.map((model) => (
          <div
            key={model.id}
            className={`card ${!model.is_available ? 'opacity-60' : ''}`}
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
            <div className="flex items-center gap-2 text-xs text-gray-500">
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
              {model.is_available ? (
                <span className="px-2 py-0.5 rounded bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300">
                  ✓ فعال
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
                  غیرفعال
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
