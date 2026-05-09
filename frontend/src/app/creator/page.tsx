'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const PROJECT_TYPES = [
  { id: 'python', name: 'Python', icon: '🐍', desc: 'اسکریپت یا CLI' },
  { id: 'fastapi', name: 'FastAPI', icon: '⚡', desc: 'API سرور' },
  { id: 'nextjs', name: 'Next.js', icon: '▲', desc: 'وب اپلیکیشن' },
  { id: 'react', name: 'React', icon: '⚛️', desc: 'فرانت‌اند' },
  { id: 'flask', name: 'Flask', icon: '🌶️', desc: 'وب ساده' },
  { id: 'node', name: 'Node.js', icon: '🟢', desc: 'بک‌اند JS' },
];

const PROJECT_TEMPLATES: Record<string, { description: string; technologies: string }> = {
  python: {
    description: 'یک ابزار خط فرمان ساده برای پردازش فایل‌های CSV و تولید گزارش متنی.',
    technologies: 'pandas, click',
  },
  fastapi: {
    description: 'یک API برای مدیریت کاربران شامل ثبت‌نام، ورود با JWT و CRUD کامل.',
    technologies: 'PostgreSQL, JWT, SQLAlchemy',
  },
  nextjs: {
    description: 'یک وب‌اپ بلاگ مدرن با احراز هویت، صفحات داینامیک و پنل ادمین.',
    technologies: 'TypeScript, Tailwind, Prisma',
  },
  react: {
    description: 'یک داشبورد مدیریت تسک با Drag & Drop و فیلترهای پیشرفته.',
    technologies: 'TypeScript, Tailwind, Zustand',
  },
  flask: {
    description: 'یک وب‌اپ ساده برای مدیریت لیست کارها با احراز هویت.',
    technologies: 'SQLite, Jinja2',
  },
  node: {
    description: 'یک سرور Express برای آپلود فایل و تولید thumbnail تصاویر.',
    technologies: 'Express, Multer, Sharp',
  },
};

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
  created_at?: string;
}

export default function CreatorPage() {
  const router = useRouter();

  const [aiReady, setAiReady] = useState(false);
  const [githubReady, setGithubReady] = useState(false);
  const [models, setModels] = useState<AIModel[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [projectType, setProjectType] = useState('fastapi');
  const [autoDetectType, setAutoDetectType] = useState(false);
  const [technologies, setTechnologies] = useState('');

  // 🆕 انتخاب مدل‌ها (multi-select)
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);

  const [creating, setCreating] = useState(false);
  const [progress, setProgress] = useState('');
  const [progressPct, setProgressPct] = useState(0);

  const [detecting, setDetecting] = useState(false);

  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 🆕 GitHub push modal
  const [pushTarget, setPushTarget] = useState<Project | null>(null);
  const [pushRepoName, setPushRepoName] = useState('');
  const [pushDescription, setPushDescription] = useState('');
  const [pushPrivate, setPushPrivate] = useState(true);
  const [pushing, setPushing] = useState(false);

  useEffect(() => {
    checkStatus();
    loadProjects();

    // بازیابی انتخاب مدل
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('creator_selected_models');
        if (saved) {
          const arr = JSON.parse(saved);
          if (Array.isArray(arr)) setSelectedModelIds(arr);
        }
      } catch {}
    }
  }, []);

  const persistModelChoice = (ids: string[]) => {
    setSelectedModelIds(ids);
    try {
      localStorage.setItem('creator_selected_models', JSON.stringify(ids));
    } catch {}
  };

  const toggleModel = (id: string) => {
    if (selectedModelIds.includes(id)) {
      persistModelChoice(selectedModelIds.filter((x) => x !== id));
    } else {
      persistModelChoice([...selectedModelIds, id]);
    }
  };

  // شبیه‌سازی پیشرفت تدریجی هنگام تولید
  useEffect(() => {
    if (!creating) {
      setProgressPct(0);
      return;
    }
    const interval = setInterval(() => {
      setProgressPct((p) => (p < 90 ? p + 1.5 : p));
    }, 400);
    return () => clearInterval(interval);
  }, [creating]);

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
        setGithubReady(!!data.github_ready);
        setModels(data.models || []);
      }
    } catch (e) {
      console.error('Error checking status:', e);
    } finally {
      setLoading(false);
    }
  };

  // تشخیص خودکار نوع پروژه
  const detectType = async () => {
    if (description.trim().length < 10) {
      showError('برای تشخیص خودکار، حداقل ۱۰ کاراکتر توضیحات بنویسید');
      return;
    }
    setDetecting(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/detect-type`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          name,
          model_id: selectedModelIds[0] || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.primary_type) {
          setProjectType(data.primary_type);
        }
        if (Array.isArray(data.technologies) && data.technologies.length > 0) {
          // ترکیب با موارد فعلی
          const existing = technologies
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean);
          const combined = [...existing];
          for (const t of data.technologies) {
            if (t && !combined.includes(t)) combined.push(t);
          }
          setTechnologies(combined.join(', '));
        }
        showSuccess(
          `AI پیشنهاد می‌دهد: ${data.primary_type}` +
            (data.alternative_types?.length ? ` (یا ${data.alternative_types.join(', ')})` : ''),
        );
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'تشخیص خودکار ناموفق بود');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setDetecting(false);
    }
  };

  // push به GitHub
  const openPushModal = (p: Project) => {
    setPushTarget(p);
    setPushRepoName(p.name.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''));
    setPushDescription(p.description || '');
    setPushPrivate(true);
  };

  const submitPush = async () => {
    if (!pushTarget) return;
    setPushing(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${pushTarget.id}/push-to-github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_name: pushRepoName,
          description: pushDescription,
          private: pushPrivate,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.repo_url) {
          showSuccess(`${data.uploaded} فایل به GitHub push شد`);
          window.open(data.repo_url, '_blank');
          setPushTarget(null);
        } else if (data.repo_url) {
          showError(`Push با ${data.failed?.length || 0} خطا انجام شد. repo: ${data.repo_url}`);
        } else {
          showError(data.message || 'Push ناموفق');
        }
      } else {
        const err = await res.json().catch(() => ({}));
        showError(err.detail || 'خطا در push به GitHub');
      }
    } catch (e: any) {
      showError(e.message);
    } finally {
      setPushing(false);
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
    }
  };

  const useTemplate = () => {
    const tmpl = PROJECT_TEMPLATES[projectType];
    if (tmpl) {
      setDescription(tmpl.description);
      setTechnologies(tmpl.technologies);
    }
  };

  const createProject = async () => {
    if (!name.trim()) {
      showError('نام پروژه را وارد کنید');
      return;
    }
    if (description.trim().length < 15) {
      showError('توضیحات باید حداقل ۱۵ کاراکتر باشد - این برای AI مهم است!');
      return;
    }
    if (!aiReady) {
      showError('ابتدا از تنظیمات کلید API را وارد کنید');
      return;
    }

    setCreating(true);
    setProgress('در حال آماده‌سازی...');
    setProgressPct(5);

    try {
      setProgress('AI در حال تحلیل و تولید ساختار پروژه...');

      const res = await fetch(`${API_BASE}/api/simple/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          project_type: projectType,
          technologies: technologies.split(',').map((t) => t.trim()).filter(Boolean),
          model_ids: selectedModelIds.length > 0 ? selectedModelIds : undefined,
          auto_detect_type: autoDetectType,
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setProgress('پروژه با موفقیت ساخته شد!');
        setProgressPct(100);
        showSuccess(data.message || 'پروژه ساخته شد!');

        setName('');
        setDescription('');
        setTechnologies('');
        loadProjects();

        setTimeout(() => {
          router.push(`/project/${data.project.id}`);
        }, 800);
      } else {
        showError(data.detail || data.error || 'خطا در ساخت پروژه');
      }
    } catch (e: any) {
      showError(e.message || 'خطا در ارتباط با سرور');
    } finally {
      setCreating(false);
      setProgress('');
    }
  };

  const deleteProject = async (id: string, projectName: string) => {
    if (!confirm(`پروژه «${projectName}» حذف شود؟ این عمل قابل بازگشت نیست.`)) return;

    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('پروژه حذف شد');
        loadProjects();
      } else {
        showError('خطا در حذف');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const filteredProjects = useMemo(
    () =>
      projects.filter(
        (p) =>
          !search ||
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.description?.toLowerCase().includes(search.toLowerCase()),
      ),
    [projects, search],
  );

  const charsLeft = description.length;
  const descColor =
    charsLeft < 15 ? 'text-red-400' : charsLeft < 50 ? 'text-yellow-400' : 'text-green-400';

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white"
      dir="rtl"
    >
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-pulse max-w-md">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 max-w-md">
          {success}
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
              <span>🛠️</span>
              <span>موتور خالق</span>
            </h1>
            <p className="text-gray-400">با AI پروژه بساز - توضیح بده، کد کامل بگیر</p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/settings"
              className="px-4 py-2 bg-yellow-500/20 text-yellow-300 rounded-lg hover:bg-yellow-500/30 border border-yellow-500/50 transition"
            >
              ⚙️ تنظیمات
            </Link>
            <Link
              href="/"
              className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 transition"
            >
              🏠 خانه
            </Link>
          </div>
        </div>

        {/* وضعیت AI */}
        <div
          className={`mb-6 p-4 rounded-xl backdrop-blur ${
            aiReady
              ? 'bg-green-500/15 border border-green-500/40'
              : 'bg-red-500/15 border border-red-500/40'
          }`}
        >
          {loading ? (
            <p className="text-center text-gray-300">در حال بررسی وضعیت...</p>
          ) : aiReady ? (
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl">✅</span>
                <div>
                  <p className="font-medium text-green-300">AI آماده است!</p>
                  <p className="text-sm text-gray-400">
                    {models.length} مدل فعال:{' '}
                    {models
                      .slice(0, 3)
                      .map((m) => m.name)
                      .join('، ')}
                    {models.length > 3 ? ` و ${models.length - 3} مدل دیگر` : ''}
                  </p>
                </div>
              </div>
              <button
                onClick={checkStatus}
                className="text-sm text-blue-300 hover:underline"
              >
                🔄 بروزرسانی
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl">⚠️</span>
                <div>
                  <p className="font-medium text-red-300">AI فعال نیست!</p>
                  <p className="text-sm text-gray-400">
                    برای ساخت پروژه، حداقل یک کلید API در تنظیمات وارد کنید.
                  </p>
                </div>
              </div>
              <Link
                href="/settings"
                className="px-4 py-2 bg-yellow-500 text-black rounded-lg font-medium hover:bg-yellow-400"
              >
                تنظیم کلید
              </Link>
            </div>
          )}
        </div>

        {/* انتخاب مدل‌ها */}
        {models.length > 0 && (
          <div className="mb-6 p-4 bg-white/10 backdrop-blur rounded-2xl border border-white/10">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <h3 className="font-bold flex items-center gap-2">
                🤖 مدل‌های مورد استفاده
              </h3>
              <div className="flex gap-1 text-xs">
                <button
                  type="button"
                  onClick={() => persistModelChoice(models.map((m) => m.id))}
                  className="px-2 py-0.5 bg-blue-500/30 text-blue-200 rounded hover:bg-blue-500/40"
                >
                  انتخاب همه
                </button>
                <button
                  type="button"
                  onClick={() => persistModelChoice([])}
                  className="px-2 py-0.5 bg-white/10 rounded hover:bg-white/20"
                >
                  لغو همه
                </button>
              </div>
            </div>
            <p className="text-xs text-gray-400 mb-2">
              {selectedModelIds.length === 0
                ? 'اولین مدل موجود به‌طور خودکار استفاده می‌شود.'
                : `${selectedModelIds.length} مدل انتخاب شد - با ترتیب fallback (اگر یکی شکست خورد، بعدی امتحان می‌شود)`}
            </p>
            <div className="flex flex-wrap gap-2">
              {models.map((m) => {
                const checked = selectedModelIds.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleModel(m.id)}
                    className={`px-3 py-1.5 rounded-full text-xs border transition ${
                      checked
                        ? 'bg-green-500 text-white border-green-500'
                        : 'bg-white/5 border-white/20 hover:bg-white/10'
                    }`}
                  >
                    {checked ? '✓ ' : ''}
                    {m.name}
                    {m.provider ? <span className="opacity-70"> · {m.provider}</span> : null}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* فرم ساخت */}
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/10">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">🆕 ساخت پروژه جدید</h2>
                <button
                  onClick={useTemplate}
                  type="button"
                  className="text-sm px-3 py-1 bg-purple-500/20 text-purple-300 rounded-lg border border-purple-500/40 hover:bg-purple-500/30"
                >
                  💡 استفاده از قالب نمونه
                </button>
              </div>

              {/* نام */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  نام پروژه <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="مثال: فروشگاه آنلاین"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={80}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none transition"
                />
              </div>

              {/* توضیحات */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium">
                    توضیحات پروژه <span className="text-red-400">*</span>
                  </label>
                  <span className={`text-xs ${descColor}`}>
                    {charsLeft} کاراکتر {charsLeft < 15 ? '(کم)' : ''}
                  </span>
                </div>
                <textarea
                  placeholder="چه می‌خواهید بسازید؟ ویژگی‌ها و قابلیت‌ها را دقیق توضیح دهید..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={6}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none resize-none transition"
                />
                <p className="text-xs text-gray-500 mt-1">
                  💡 هر چه دقیق‌تر بنویسید، خروجی AI بهتر می‌شود.
                </p>
              </div>

              {/* نوع پروژه */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                  <label className="block text-sm font-medium">نوع پروژه</label>
                  <div className="flex gap-2 items-center">
                    <button
                      type="button"
                      onClick={detectType}
                      disabled={detecting || description.trim().length < 10 || !aiReady}
                      className="text-xs px-3 py-1 bg-cyan-500/20 text-cyan-300 rounded-lg border border-cyan-500/40 hover:bg-cyan-500/30 disabled:opacity-50"
                      title="AI از روی توضیحات شما بهترین نوع و تکنولوژی را پیشنهاد می‌دهد"
                    >
                      {detecting ? '⏳ تشخیص...' : '🪄 تشخیص خودکار'}
                    </button>
                    <label className="flex items-center gap-1 text-xs text-gray-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoDetectType}
                        onChange={(e) => setAutoDetectType(e.target.checked)}
                        className="w-3.5 h-3.5"
                      />
                      <span title="هنگام ساخت پروژه، AI خودش نوع و تکنولوژی‌ها را تشخیص می‌دهد">
                        خودکار هنگام ساخت
                      </span>
                    </label>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {PROJECT_TYPES.map((type) => (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setProjectType(type.id)}
                      className={`p-4 rounded-xl border text-center transition-all ${
                        projectType === type.id
                          ? 'bg-blue-500/30 border-blue-400 shadow-lg shadow-blue-500/20'
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
                  تکنولوژی‌های اضافی <span className="text-gray-400 text-xs">(اختیاری)</span>
                </label>
                <input
                  type="text"
                  placeholder="با کاما جدا کنید... مثال: PostgreSQL, Redis, JWT"
                  value={technologies}
                  onChange={(e) => setTechnologies(e.target.value)}
                  className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:border-blue-500 focus:outline-none transition"
                />
              </div>

              {/* نوار پیشرفت */}
              {creating && (
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-blue-300">{progress}</span>
                    <span className="text-gray-400">{Math.round(progressPct)}%</span>
                  </div>
                  <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    این کار ممکن است یک تا چند دقیقه طول بکشد. لطفاً صبور باشید.
                  </p>
                </div>
              )}

              {/* دکمه ساخت */}
              <button
                onClick={createProject}
                disabled={creating || !aiReady}
                className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-bold text-lg hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-500/20"
              >
                {creating ? (
                  <span className="flex items-center justify-center gap-3">
                    <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    در حال ساخت...
                  </span>
                ) : (
                  '🚀 ساخت پروژه با AI'
                )}
              </button>
            </div>
          </div>

          {/* لیست پروژه‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/10 sticky top-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">📂 پروژه‌های من ({projects.length})</h2>
                <button
                  onClick={loadProjects}
                  className="text-sm text-blue-400 hover:underline"
                >
                  🔄
                </button>
              </div>

              {projects.length > 0 && (
                <input
                  type="text"
                  placeholder="جستجو..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full p-2 bg-white/5 border border-white/20 rounded-lg text-sm mb-4 focus:border-blue-500 focus:outline-none"
                />
              )}

              {filteredProjects.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">📭</div>
                  <p>{projects.length === 0 ? 'هنوز پروژه‌ای نساختید' : 'نتیجه‌ای پیدا نشد'}</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[60vh] overflow-auto">
                  {filteredProjects.map((p) => {
                    const typeInfo = PROJECT_TYPES.find((t) => t.id === p.project_type);
                    return (
                      <div
                        key={p.id}
                        className="group p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-all border border-transparent hover:border-white/10"
                      >
                        <Link href={`/project/${p.id}`} className="block">
                          <div className="font-medium truncate flex items-center gap-2">
                            <span>{typeInfo?.icon || '📦'}</span>
                            <span>{p.name}</span>
                          </div>
                          {p.description && (
                            <p className="text-xs text-gray-400 line-clamp-2 mt-1">
                              {p.description}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                            <span>{p.project_type}</span>
                            {p.files?.length > 0 && (
                              <span className="text-green-400">📄 {p.files.length} فایل</span>
                            )}
                            {p.status && (
                              <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-300 rounded">
                                {p.status}
                              </span>
                            )}
                          </div>
                        </Link>
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 mt-2 text-xs transition">
                          <button
                            onClick={() => openPushModal(p)}
                            disabled={!githubReady}
                            title={
                              githubReady
                                ? 'ساخت repo در GitHub و push همه فایل‌ها'
                                : 'ابتدا توکن GitHub را در /settings تنظیم کنید'
                            }
                            className="text-cyan-300 hover:text-cyan-200 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            🚀 push به GitHub
                          </button>
                          <button
                            onClick={() => deleteProject(p.id, p.name)}
                            className="text-red-400 hover:text-red-300 mr-auto"
                          >
                            🗑️ حذف
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* مودال push به GitHub */}
      {pushTarget && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => !pushing && setPushTarget(null)}
        >
          <div
            className="bg-gray-800 border border-white/10 rounded-2xl w-full max-w-md p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
              🚀 Push «{pushTarget.name}» به GitHub
            </h3>
            <p className="text-xs text-gray-400 mb-4">
              یک repo جدید ساخته می‌شود (یا اگر وجود داشت، فایل‌ها به‌روزرسانی می‌شوند) و همه فایل‌های پروژه upload می‌شوند.
            </p>

            <label className="block text-sm mb-1 text-gray-300">نام repo</label>
            <input
              type="text"
              value={pushRepoName}
              onChange={(e) =>
                setPushRepoName(
                  e.target.value.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/-+/g, '-'),
                )
              }
              dir="ltr"
              maxLength={80}
              className="w-full p-2 bg-white/5 border border-white/20 rounded-lg mb-3 focus:border-blue-500 focus:outline-none"
            />

            <label className="block text-sm mb-1 text-gray-300">توضیحات</label>
            <textarea
              value={pushDescription}
              onChange={(e) => setPushDescription(e.target.value)}
              rows={2}
              maxLength={300}
              className="w-full p-2 bg-white/5 border border-white/20 rounded-lg mb-3 focus:border-blue-500 focus:outline-none resize-none"
            />

            <label className="flex items-center gap-2 mb-4 cursor-pointer">
              <input
                type="checkbox"
                checked={pushPrivate}
                onChange={(e) => setPushPrivate(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm">🔒 repo خصوصی باشد</span>
            </label>

            <div className="flex gap-2">
              <button
                onClick={submitPush}
                disabled={pushing || !pushRepoName}
                className="flex-1 py-2 bg-cyan-500 text-white rounded-lg font-bold hover:bg-cyan-600 disabled:opacity-50"
              >
                {pushing ? '⏳ در حال push...' : '🚀 شروع push'}
              </button>
              <button
                onClick={() => !pushing && setPushTarget(null)}
                disabled={pushing}
                className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 disabled:opacity-50"
              >
                لغو
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
