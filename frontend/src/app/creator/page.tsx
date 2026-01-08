'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// انواع پروژه
const PROJECT_TYPES = [
  { id: 'python', name: 'Python', icon: '🐍', desc: 'اسکریپت یا CLI' },
  { id: 'fastapi', name: 'FastAPI', icon: '⚡', desc: 'API سرور' },
  { id: 'nextjs', name: 'Next.js', icon: '▲', desc: 'وب اپلیکیشن' },
  { id: 'react', name: 'React', icon: '⚛️', desc: 'فرانت‌اند' },
  { id: 'flask', name: 'Flask', icon: '🌶️', desc: 'وب ساده' },
  { id: 'node', name: 'Node.js', icon: '🟢', desc: 'بک‌اند JS' },
];

interface AIModel {
  id: string;
  name: string;
  provider: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  project_type: string;
  status: string;
  files: any[];
}

export default function CreatorPage() {
  const router = useRouter();

  // وضعیت سیستم
  const [aiReady, setAiReady] = useState(false);
  const [models, setModels] = useState<AIModel[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // فرم
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [projectType, setProjectType] = useState('fastapi');
  const [technologies, setTechnologies] = useState('');

  // حالت ساخت
  const [creating, setCreating] = useState(false);
  const [progress, setProgress] = useState('');

  // پیام‌ها
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    checkStatus();
    loadProjects();
  }, []);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simple/status`);
      if (res.ok) {
        const data = await res.json();
        setAiReady(data.ai_ready);
        setModels(data.models || []);
      }
    } catch (e) {
      console.error('Error checking status:', e);
      // AI status check failed - will show as unavailable
    } finally {
      setLoading(false);
    }
  };

  const loadProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch (e) {
      console.error('Error loading projects:', e);
      // Continue silently - will show empty project list
    }
  };

  const createProject = async () => {
    if (!name.trim()) {
      showError('نام پروژه رو وارد کن');
      return;
    }
    if (!description.trim()) {
      showError('توضیحات رو وارد کن - این برای AI مهمه!');
      return;
    }
    if (!aiReady) {
      showError('اول از تنظیمات کلید API وارد کن');
      return;
    }

    setCreating(true);
    setProgress('در حال آماده‌سازی...');

    try {
      setProgress('در حال تولید ساختار با AI...');

      const res = await fetch(`${API_BASE}/api/simple/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          project_type: projectType,
          technologies: technologies.split(',').map(t => t.trim()).filter(t => t),
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setProgress('پروژه ساخته شد!');
        showSuccess(data.message || 'پروژه ساخته شد!');

        // پاکسازی فرم
        setName('');
        setDescription('');
        setTechnologies('');

        // رفتن به صفحه پروژه
        setTimeout(() => {
          router.push(`/project/${data.project.id}`);
        }, 1000);

      } else {
        showError(data.detail || data.error || 'خطا در ساخت پروژه');
      }

    } catch (e: any) {
      showError(e.message || 'خطا در ارتباط');
    } finally {
      setCreating(false);
      setProgress('');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white" dir="rtl">
      {/* پیام‌ها */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-pulse">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50">
          {success}
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">موتور خالق</h1>
            <p className="text-gray-400">
              با AI پروژه بساز - توضیح بده، کد بگیر
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/settings"
              className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 border border-yellow-500/50"
            >
              تنظیمات
            </Link>
            <Link
              href="/"
              className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
            >
              خانه
            </Link>
          </div>
        </div>

        {/* وضعیت AI */}
        <div className={`mb-6 p-4 rounded-xl ${aiReady ? 'bg-green-500/20 border border-green-500/50' : 'bg-red-500/20 border border-red-500/50'}`}>
          {loading ? (
            <p className="text-center">در حال بررسی...</p>
          ) : aiReady ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">+</span>
                <div>
                  <p className="font-medium">AI آماده است!</p>
                  <p className="text-sm text-gray-400">
                    {models.length} مدل فعال: {models.map(m => m.name).join(', ')}
                  </p>
                </div>
              </div>
              <button onClick={checkStatus} className="text-sm text-blue-400 hover:underline">
                بروزرسانی
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">!</span>
                <div>
                  <p className="font-medium">AI فعال نیست!</p>
                  <p className="text-sm text-gray-400">
                    برو به تنظیمات و کلید API وارد کن
                  </p>
                </div>
              </div>
              <Link href="/settings" className="px-4 py-2 bg-yellow-500 text-black rounded-lg font-medium">
                تنظیم کلید
              </Link>
            </div>
          )}
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* فرم ساخت */}
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
              <h2 className="text-xl font-bold mb-6">ساخت پروژه جدید</h2>

              {/* نام */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">نام پروژه *</label>
                <input
                  type="text"
                  placeholder="مثال: فروشگاه آنلاین"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none"
                />
              </div>

              {/* توضیحات */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  توضیحات پروژه * <span className="text-gray-400">(هر چی دقیق‌تر، بهتر)</span>
                </label>
                <textarea
                  placeholder="دقیق بنویس چی میخوای..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={5}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>

              {/* نوع پروژه */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">نوع پروژه</label>
                <div className="grid grid-cols-3 gap-3">
                  {PROJECT_TYPES.map((type) => (
                    <button
                      key={type.id}
                      onClick={() => setProjectType(type.id)}
                      className={`p-4 rounded-xl border text-center transition-all ${
                        projectType === type.id
                          ? 'bg-blue-500/30 border-blue-500'
                          : 'bg-white/5 border-white/20 hover:bg-white/10'
                      }`}
                    >
                      <div className="text-2xl mb-1">{type.icon}</div>
                      <div className="font-medium">{type.name}</div>
                      <div className="text-xs text-gray-400">{type.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* تکنولوژی‌ها */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">
                  تکنولوژی‌های اضافی <span className="text-gray-400">(اختیاری)</span>
                </label>
                <input
                  type="text"
                  placeholder="با کاما جدا کن... مثال: PostgreSQL, Redis, JWT"
                  value={technologies}
                  onChange={(e) => setTechnologies(e.target.value)}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none"
                />
              </div>

              {/* دکمه ساخت */}
              <button
                onClick={createProject}
                disabled={creating || !aiReady}
                className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-bold text-lg hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {creating ? (
                  <span className="flex items-center justify-center gap-3">
                    <span className="animate-spin">*</span>
                    {progress}
                  </span>
                ) : (
                  'ساخت پروژه با AI'
                )}
              </button>
            </div>
          </div>

          {/* لیست پروژه‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">پروژه‌های من</h2>
                <button onClick={loadProjects} className="text-sm text-blue-400 hover:underline">
                  بروزرسانی
                </button>
              </div>

              {projects.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">-</div>
                  <p>هنوز پروژه‌ای نساختی</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[60vh] overflow-auto">
                  {projects.map((p) => (
                    <Link
                      key={p.id}
                      href={`/project/${p.id}`}
                      className="block p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-all"
                    >
                      <div className="font-medium truncate">{p.name}</div>
                      <div className="flex items-center gap-2 mt-1 text-sm text-gray-400">
                        <span>{PROJECT_TYPES.find(t => t.id === p.project_type)?.icon || '*'}</span>
                        <span>{p.project_type}</span>
                        {p.files?.length > 0 && (
                          <span className="text-green-400">- {p.files.length} فایل</span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
