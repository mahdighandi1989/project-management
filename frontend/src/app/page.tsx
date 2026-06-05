'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function HomePage() {
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/providers`);
      if (res.ok) {
        const data = await res.json();
        setProviders(data || []);
      }
    } catch (e) {
      console.error('Error loading providers:', e);
      // Continue silently - providers are optional
    } finally {
      setLoading(false);
    }
  };

  const menuItems = [
    { href: '/oversight', icon: '🛰️', title: 'مرکز نظارت پروژه‌ها', desc: 'مدیریت یکپارچه مخازن GitHub با AI' },
    { href: '/creator', icon: '🚀', title: 'موتور خالق', desc: 'ساخت پروژه جدید' },
    { href: '/knowledge-center', icon: '📚', title: 'مرکز دانش', desc: 'تجربیات قابل‌استفاده‌مجدد از همهٔ پروژه‌ها' },
    { href: '/projects', icon: '📁', title: 'پروژه‌ها', desc: 'مدیریت پروژه‌ها' },
    { href: '/debate', icon: '💬', title: 'مناظره', desc: 'مناظره هوش مصنوعی' },
    { href: '/analysis', icon: '🔍', title: 'تحلیل پروژه', desc: 'بررسی سلامت و پروفایل AI' },
    { href: '/archive', icon: '📦', title: 'آرشیو', desc: 'تاریخچه و فایل‌ها' },
    { href: '/settings', icon: '⚙️', title: 'تنظیمات', desc: 'پیکربندی سیستم' },
    { href: '/diagrams', icon: '📊', title: 'نمودارها', desc: 'تولید نمودار' },
  ];

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900" dir="rtl">
      <div className="max-w-5xl mx-auto p-6">
        {/* هدر */}
        <div className="text-center mb-10 pt-8">
          <h1 className="text-4xl font-bold mb-3">سیستم مناظره AI</h1>
          <p className="text-gray-500">مدیریت پروژه و مناظره هوش مصنوعی</p>
        </div>

        {/* وضعیت مدل‌ها */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 mb-8 shadow">
          <h2 className="text-lg font-bold mb-4">وضعیت مدل‌ها</h2>

          {loading ? (
            <p className="text-gray-400">در حال بارگذاری...</p>
          ) : providers.length === 0 ? (
            <p className="text-gray-400">مدلی فعال نیست - به تنظیمات بروید</p>
          ) : (
            <div className="flex flex-wrap gap-3">
              {providers.map((p) => (
                <div
                  key={p.name}
                  className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${
                    p.available
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-400 dark:bg-gray-700'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${p.available ? 'bg-green-500' : 'bg-gray-400'}`} />
                  {p.name}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* منو اصلی */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {menuItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow hover:shadow-lg transition group"
            >
              <div className="text-4xl mb-3">{item.icon}</div>
              <h3 className="text-lg font-bold mb-1 group-hover:text-blue-500 transition">
                {item.title}
              </h3>
              <p className="text-sm text-gray-500">{item.desc}</p>
            </Link>
          ))}
        </div>

        {/* فوتر */}
        <div className="text-center mt-10 text-sm text-gray-400">
          نسخه ۲.۰
        </div>
      </div>
    </div>
  );
}
