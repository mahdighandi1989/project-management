/**
 * Home Page
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { settingsApi, modelsApi, SystemStatus, ProviderStatus } from '@/services/api';
import {
  ChatBubbleLeftRightIcon,
  CpuChipIcon,
  Cog6ToothIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline';

export default function HomePage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statusRes, providersRes] = await Promise.all([
        settingsApi.status(),
        modelsApi.providers(),
      ]);
      setStatus(statusRes.data);
      setProviders(providersRes.data);
    } catch (err: any) {
      setError(err.message || 'خطا در اتصال به سرور');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    {
      icon: '🥊',
      title: 'مناظره AI',
      description: 'مناظره بین مدل‌های مختلف AI با نقش‌های متفاوت',
      href: '/debate',
      color: 'from-orange-500 to-red-500',
    },
    {
      icon: '🤝',
      title: 'همکاری',
      description: 'همکاری مدل‌ها برای حل مسائل پیچیده',
      href: '/debate?mode=collaboration',
      color: 'from-green-500 to-emerald-500',
    },
    {
      icon: '🔍',
      title: 'تحقیق عمیق',
      description: 'تحقیق چندمرحله‌ای با تحلیل و ترکیب',
      href: '/debate?mode=deep_research',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: '⚡',
      title: 'پاسخ سریع',
      description: 'پاسخ فوری با بهترین مدل موجود',
      href: '/debate?mode=quick',
      color: 'from-yellow-500 to-amber-500',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner w-12 h-12" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
          سیستم مناظره و همکاری AI 🤖
        </h1>
        <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          با قدرت هوش مصنوعی، ایده‌هایتان را به چالش بکشید، پاسخ‌های بهتر بگیرید
          و پروژه‌هایتان را مدیریت کنید.
        </p>
      </div>

      {/* Status Card */}
      {error ? (
        <div className="card bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-3">
            <XCircleIcon className="w-8 h-8 text-red-500" />
            <div>
              <h3 className="font-bold text-red-800 dark:text-red-200">خطا در اتصال</h3>
              <p className="text-red-600 dark:text-red-300">{error}</p>
            </div>
          </div>
          <button onClick={loadData} className="btn btn-secondary mt-4">
            تلاش مجدد
          </button>
        </div>
      ) : (
        <div className="card bg-gradient-to-br from-primary-500 to-purple-600 text-white">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold mb-1">{status?.app_name}</h2>
              <p className="text-white/80">
                نسخه {status?.version} • {status?.environment}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircleIcon className="w-6 h-6 text-green-300" />
              <span>سیستم فعال</span>
            </div>
          </div>
        </div>
      )}

      {/* Features Grid */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          شروع کنید
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map((feature) => (
            <Link
              key={feature.title}
              href={feature.href}
              className="card card-hover group"
            >
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center text-2xl`}>
                  {feature.icon}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
                    {feature.title}
                    <ArrowLeftIcon className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {feature.description}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Providers Status */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          وضعیت Provider ها
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {providers.map((provider) => (
            <div
              key={provider.provider}
              className={`card text-center ${
                provider.available
                  ? 'border-2 border-green-200 dark:border-green-800'
                  : 'border-2 border-gray-200 dark:border-gray-700 opacity-60'
              }`}
            >
              <div className="text-3xl mb-2">
                {provider.provider === 'openai' && '🟢'}
                {provider.provider === 'claude' && '🟣'}
                {provider.provider === 'gemini' && '🔵'}
                {provider.provider === 'deepseek' && '🟡'}
                {provider.provider === 'openrouter' && '🟠'}
                {provider.provider === 'groq' && '⚪'}
              </div>
              <h3 className="font-medium text-gray-900 dark:text-white capitalize">
                {provider.provider}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {provider.available ? (
                  <span className="text-green-600 dark:text-green-400">
                    {provider.model_count} مدل
                  </span>
                ) : (
                  <span>غیرفعال</span>
                )}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/debate" className="card card-hover flex items-center gap-4">
          <ChatBubbleLeftRightIcon className="w-8 h-8 text-primary-500" />
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">شروع مناظره جدید</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">یک سوال بپرسید</p>
          </div>
        </Link>

        <Link href="/models" className="card card-hover flex items-center gap-4">
          <CpuChipIcon className="w-8 h-8 text-purple-500" />
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">مدل‌های موجود</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">لیست همه مدل‌ها</p>
          </div>
        </Link>

        <Link href="/settings" className="card card-hover flex items-center gap-4">
          <Cog6ToothIcon className="w-8 h-8 text-gray-500" />
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">تنظیمات</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">API Keys و پیکربندی</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
