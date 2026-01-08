'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// انواع پروژه
const PROJECT_TYPES = [
  { id: 'python', name: 'Python', icon: '🐍' },
  { id: 'fastapi', name: 'FastAPI', icon: '⚡' },
  { id: 'nextjs', name: 'Next.js', icon: '▲' },
  { id: 'react', name: 'React', icon: '⚛️' },
  { id: 'node', name: 'Node.js', icon: '🟢' },
  { id: 'flask', name: 'Flask', icon: '🌶️' },
  { id: 'django', name: 'Django', icon: '🎸' },
  { id: 'express', name: 'Express', icon: '🚀' },
];

export default function CreatorPage() {
  const router = useRouter();

  // لیست پروژه‌های ساخته شده
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // فرم ساخت پروژه
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [projectType, setProjectType] = useState('python');
  const [technologies, setTechnologies] = useState('');
  const [features, setFeatures] = useState('');
  const [creating, setCreating] = useState(false);
  const [progress, setProgress] = useState('');

  // پروژه انتخاب شده
  const [selectedProject, setSelectedProject] = useState<any>(null);

  // مدل‌های AI موجود
  const [availableModels, setAvailableModels] = useState<string[]>([]);

  useEffect(() => {
    loadProjects();
    loadModels();
  }, []);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

  const loadModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/available`);
      if (res.ok) {
        const data = await res.json();
        // API آرایه مستقیم برمیگردونه، نه object با models
        const models = Array.isArray(data) ? data : (data.models || data || []);
        setAvailableModels(models.map((m: any) => m.id || m.name || m));
      }
    } catch (e) {
      console.error('خطا در بارگذاری مدل‌ها');
    }
  };

  const loadProjects = async () => {
    try {
      // از هر دو منبع بارگذاری کن
      const [basicRes, creatorRes] = await Promise.all([
        fetch(`${API_BASE}/api/projects`),
        fetch(`${API_BASE}/api/creator/projects/active`)
      ]);

      let allProjects: any[] = [];

      if (basicRes.ok) {
        const data = await basicRes.json();
        allProjects = data.projects || [];
      }

      if (creatorRes.ok) {
        const data = await creatorRes.json();
        const creatorProjects = data.projects || [];
        // اضافه کردن پروژه‌های creator که تکراری نیستن
        for (const p of creatorProjects) {
          if (!allProjects.find((x: any) => x.id === p.id)) {
            allProjects.push(p);
          }
        }
      }

      setProjects(allProjects);
    } catch (e) {
      console.error(e);
    }
  };

  const createProject = async () => {
    if (!projectName.trim()) {
      showError('نام پروژه را وارد کنید');
      return;
    }

    if (!projectDesc.trim()) {
      showError('توضیحات پروژه را وارد کنید - این برای AI مهمه!');
      return;
    }

    if (availableModels.length === 0) {
      showError('هیچ مدل AI فعالی نیست! ابتدا از تنظیمات کلید API وارد کنید');
      return;
    }

    setCreating(true);
    setProgress('در حال آماده‌سازی...');

    try {
      // استفاده از Creator Engine واقعی
      setProgress('در حال تولید ساختار پروژه با AI...');

      const res = await fetch(`${API_BASE}/api/creator/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName,
          description: projectDesc,
          project_type: projectType,
          technologies: technologies.split(',').map(t => t.trim()).filter(t => t),
          features: features.split(',').map(f => f.trim()).filter(f => f),
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setProgress('پروژه با موفقیت ساخته شد! در حال انتقال...');
        showSuccess(`پروژه "${projectName}" با AI ساخته شد!`);

        // پاکسازی فرم
        setProjectName('');
        setProjectDesc('');
        setTechnologies('');
        setFeatures('');

        // انتقال به صفحه پروژه
        const projectId = data.project?.id;
        if (projectId) {
          setTimeout(() => {
            router.push(`/projects/${projectId}`);
          }, 1500);
        } else {
          loadProjects();
          setSelectedProject(data.project);
        }
      } else {
        // Fallback به روش ساده
        setProgress('در حال ذخیره پروژه...');

        const fallbackRes = await fetch(`${API_BASE}/api/projects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: projectName,
            description: projectDesc,
            project_type: projectType,
          }),
        });

        if (fallbackRes.ok) {
          showSuccess('پروژه ذخیره شد (بدون تولید کد)');
          setProjectName('');
          setProjectDesc('');
          loadProjects();
        } else {
          showError(data.error || 'خطا در ساخت پروژه');
        }
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setCreating(false);
      setProgress('');
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm('آیا مطمئنید؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showSuccess('حذف شد');
        if (selectedProject?.id === id) setSelectedProject(null);
        loadProjects();
      }
    } catch (e) {
      showError('خطا در حذف');
    }
  };

  const generateFile = async (filePath: string, description: string) => {
    if (!selectedProject) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/projects/${selectedProject.id}/generate-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath,
          description: description,
        }),
      });

      const data = await res.json();
      if (data.success) {
        showSuccess(`فایل ${filePath} ساخته شد`);
        // بروزرسانی اطلاعات پروژه
        const projectRes = await fetch(`${API_BASE}/api/creator/projects/${selectedProject.id}`);
        if (projectRes.ok) {
          const projectData = await projectRes.json();
          setSelectedProject(projectData.project);
        }
      } else {
        showError(data.error || 'خطا در ساخت فایل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900" dir="rtl">
      {/* پیام‌ها */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-md">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-md">
          {success}
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">موتور خالق</h1>
            <p className="text-gray-500 text-sm">
              با AI پروژه بساز - {availableModels.length > 0
                ? `${availableModels.length} مدل فعال`
                : '⚠️ مدل فعالی نیست'}
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/settings" className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600">
              تنظیمات API
            </Link>
            <Link href="/" className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300">
              خانه
            </Link>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* فرم ساخت پروژه */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-6">
              <h2 className="text-lg font-bold mb-4">ساخت پروژه جدید</h2>

              {/* نام */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">نام پروژه *</label>
                <input
                  type="text"
                  placeholder="مثال: فروشگاه آنلاین"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                />
              </div>

              {/* توضیحات */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">توضیحات (مهم برای AI) *</label>
                <textarea
                  placeholder="دقیق بنویس چی میخوای... مثال: یک فروشگاه آنلاین با سبد خرید، پرداخت آنلاین، پنل مدیریت محصولات"
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  rows={3}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                />
              </div>

              {/* نوع پروژه */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">نوع پروژه</label>
                <div className="grid grid-cols-4 gap-2">
                  {PROJECT_TYPES.map((type) => (
                    <button
                      key={type.id}
                      onClick={() => setProjectType(type.id)}
                      className={`p-3 rounded-lg border text-center transition ${
                        projectType === type.id
                          ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500'
                          : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="text-2xl mb-1">{type.icon}</div>
                      <div className="text-xs">{type.name}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* تکنولوژی‌ها */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">تکنولوژی‌ها (اختیاری)</label>
                <input
                  type="text"
                  placeholder="با کاما جدا کن... مثال: PostgreSQL, Redis, Docker"
                  value={technologies}
                  onChange={(e) => setTechnologies(e.target.value)}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                />
              </div>

              {/* قابلیت‌ها */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">قابلیت‌ها (اختیاری)</label>
                <input
                  type="text"
                  placeholder="با کاما جدا کن... مثال: احراز هویت, پرداخت, جستجو"
                  value={features}
                  onChange={(e) => setFeatures(e.target.value)}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                />
              </div>

              {/* دکمه ساخت */}
              <button
                onClick={createProject}
                disabled={creating || availableModels.length === 0}
                className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-bold hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin">⏳</span>
                    {progress || 'در حال ساخت...'}
                  </span>
                ) : (
                  '🚀 ساخت پروژه با AI'
                )}
              </button>

              {availableModels.length === 0 && (
                <p className="text-center text-yellow-600 mt-2 text-sm">
                  ⚠️ ابتدا از صفحه تنظیمات کلید API وارد کنید
                </p>
              )}
            </div>

            {/* نمایش پروژه انتخاب شده */}
            {selectedProject && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold">{selectedProject.name}</h2>
                  <span className={`px-3 py-1 rounded text-sm ${
                    selectedProject.status === 'created' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {selectedProject.status || 'نامشخص'}
                  </span>
                </div>

                <p className="text-gray-500 mb-4">{selectedProject.description}</p>

                {/* ساختار پروژه */}
                {selectedProject.structure && (
                  <div className="mb-4">
                    <h3 className="font-medium mb-2">ساختار پروژه:</h3>
                    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-sm font-mono">
                      {selectedProject.structure.directories?.map((dir: string, i: number) => (
                        <div key={i} className="text-blue-600">📁 {dir}</div>
                      ))}
                      {selectedProject.structure.files?.map((file: any, i: number) => (
                        <div key={i} className="text-gray-600">
                          📄 {typeof file === 'string' ? file : file.path}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* فایل‌های تولید شده */}
                {selectedProject.files && selectedProject.files.length > 0 && (
                  <div className="mb-4">
                    <h3 className="font-medium mb-2">فایل‌های تولید شده:</h3>
                    <div className="space-y-1">
                      {selectedProject.files.map((file: string, i: number) => (
                        <div key={i} className="text-sm bg-gray-50 dark:bg-gray-700 px-3 py-2 rounded">
                          ✅ {file}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* مسیر پروژه */}
                {selectedProject.path && (
                  <div className="text-sm text-gray-500">
                    📂 مسیر: <code className="bg-gray-100 px-2 py-1 rounded">{selectedProject.path}</code>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* لیست پروژه‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">پروژه‌ها ({projects.length})</h2>
                <button onClick={loadProjects} className="text-blue-500 text-sm hover:underline">
                  بروزرسانی
                </button>
              </div>

              {projects.length === 0 ? (
                <p className="text-center text-gray-400 py-8">پروژه‌ای نیست</p>
              ) : (
                <div className="space-y-2 max-h-[70vh] overflow-auto">
                  {projects.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => setSelectedProject(p)}
                      className={`p-3 rounded-lg cursor-pointer transition ${
                        selectedProject?.id === p.id
                          ? 'bg-blue-50 dark:bg-blue-900/30 border-2 border-blue-500'
                          : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="font-medium truncate">{p.name}</div>
                      <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                        <span>{p.type || p.project_type || 'custom'}</span>
                        {p.files?.length > 0 && (
                          <span className="text-green-600">{p.files.length} فایل</span>
                        )}
                      </div>
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteProject(p.id);
                          }}
                          className="text-xs px-2 py-1 bg-red-100 text-red-600 rounded hover:bg-red-200"
                        >
                          حذف
                        </button>
                      </div>
                    </div>
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
