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
  BeakerIcon,
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

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  // Capability testing state
  const [capabilityResults, setCapabilityResults] = useState<Record<string, CapabilityResult>>({});
  const [testingModel, setTestingModel] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [showTestPanel, setShowTestPanel] = useState(false);

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

            {/* Test Button */}
            {model.is_available && (
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
                return (
                  <>
                    {/* هدر با badge ها */}
                    <div className="flex items-start gap-4 mb-6">
                      <div className={`w-20 h-20 rounded-xl flex flex-col items-center justify-center text-white ${
                        result.overall_score >= 80 ? 'bg-gradient-to-br from-purple-500 to-purple-700' :
                        result.overall_score >= 60 ? 'bg-gradient-to-br from-blue-500 to-blue-700' :
                        'bg-gradient-to-br from-gray-500 to-gray-700'
                      }`}>
                        <div className="text-2xl font-bold">{result.overall_score.toFixed(0)}</div>
                        <div className="text-xs opacity-75">امتیاز کلی</div>
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-500 text-sm">
                          تست شده: {new Date(result.tested_at).toLocaleString('fa-IR')}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-2">
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
          </div>
        </div>
      )}
    </div>
  );
}
