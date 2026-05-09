'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
// ProjectHealthPanel در commit 3.3a حذف شد — به /oversight منتقل شد

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProjectFile {
  path: string;
  content?: string;
  size?: number;
}

interface Project {
  id: string;
  name: string;
  description: string;
  project_type: string;
  status: string;
  created_at: string;
  files: ProjectFile[];
  structure: {
    directories: string[];
    files: { path: string; description: string }[];
  };
}

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [selectedFile, setSelectedFile] = useState<ProjectFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [fileLoading, setFileLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Deploy state
  const [deploying, setDeploying] = useState(false);
  const [deployUrl, setDeployUrl] = useState('');

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 5000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 5000);
  };

  const loadProject = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}`);
      const data = await res.json();

      if (res.ok && data.success) {
        setProject(data.project);

        // اگه فایل‌ها وجود داره، اولین فایل رو انتخاب کن
        if (data.project.files?.length > 0) {
          const firstFile = data.project.files[0];
          if (typeof firstFile === 'object' && firstFile.path) {
            loadFileContent(firstFile.path);
          }
        }
      } else {
        showError(data.detail || 'پروژه پیدا نشد');
      }
    } catch (e) {
      showError('خطا در بارگذاری پروژه');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filePath: string) => {
    setFileLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}/files/${encodeURIComponent(filePath)}`);
      const data = await res.json();

      if (res.ok && data.success) {
        setSelectedFile({ path: filePath, content: data.content });
      } else {
        showError('خطا در خواندن فایل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setFileLoading(false);
    }
  };

  const deployToRender = async () => {
    setDeploying(true);
    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      if (data.success) {
        setDeployUrl(data.deploy_url || '');
        showSuccess('Deploy شروع شد!');
      } else {
        showError(data.detail || 'خطا در Deploy');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setDeploying(false);
    }
  };

  const deleteProject = async () => {
    if (!confirm('آیا مطمئنی میخوای این پروژه رو حذف کنی؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/simple/projects/${projectId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        showSuccess('پروژه حذف شد');
        setTimeout(() => router.push('/creator'), 1000);
      } else {
        showError('خطا در حذف');
      }
    } catch (e) {
      showError('خطا');
    }
  };

  const getFileIcon = (path: string) => {
    if (path.endsWith('.py')) return '🐍';
    if (path.endsWith('.js') || path.endsWith('.ts')) return '📜';
    if (path.endsWith('.tsx') || path.endsWith('.jsx')) return '⚛️';
    if (path.endsWith('.json')) return '📋';
    if (path.endsWith('.md')) return '📝';
    if (path.endsWith('.html')) return '🌐';
    if (path.endsWith('.css')) return '🎨';
    if (path.endsWith('.yaml') || path.endsWith('.yml')) return '⚙️';
    if (path.endsWith('.env') || path.endsWith('.env.example')) return '🔐';
    if (path.includes('Dockerfile') || path.includes('docker')) return '🐳';
    if (path.includes('requirements') || path.includes('package')) return '📦';
    return '📄';
  };

  const getLanguage = (path: string) => {
    if (path.endsWith('.py')) return 'python';
    if (path.endsWith('.js')) return 'javascript';
    if (path.endsWith('.ts')) return 'typescript';
    if (path.endsWith('.tsx')) return 'tsx';
    if (path.endsWith('.jsx')) return 'jsx';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.md')) return 'markdown';
    if (path.endsWith('.html')) return 'html';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml';
    return 'text';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center text-white">
          <div className="animate-spin text-5xl mb-4">*</div>
          <p className="text-xl">در حال بارگذاری پروژه...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center text-white">
          <div className="text-6xl mb-4">!</div>
          <p className="text-xl mb-4">پروژه پیدا نشد</p>
          <Link href="/creator" className="px-6 py-3 bg-blue-500 rounded-lg hover:bg-blue-600">
            برگشت به موتور خالق
          </Link>
        </div>
      </div>
    );
  }

  const files = project.files || [];

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

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
              <Link href="/creator" className="hover:text-blue-400">موتور خالق</Link>
              <span>/</span>
              <span>{project.name}</span>
            </div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="text-gray-400 mt-1">{project.description}</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={deployToRender}
              disabled={deploying}
              className="px-5 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 font-medium"
            >
              {deploying ? '... در حال Deploy' : 'Deploy به Render'}
            </button>
            <button
              onClick={deleteProject}
              className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 border border-red-500/50"
            >
              حذف
            </button>
            <Link
              href="/creator"
              className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
            >
              برگشت
            </Link>
          </div>
        </div>

        {/* اطلاعات پروژه */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">نوع پروژه</div>
            <div className="font-medium text-lg">{project.project_type}</div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">وضعیت</div>
            <div className="font-medium text-lg">
              <span className={`inline-block px-2 py-1 rounded text-sm ${
                project.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                project.status === 'generating' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-blue-500/20 text-blue-400'
              }`}>
                {project.status === 'completed' ? 'تکمیل شده' :
                 project.status === 'generating' ? 'در حال تولید' : project.status}
              </span>
            </div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">تعداد فایل</div>
            <div className="font-medium text-lg">{files.length} فایل</div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-sm text-gray-400 mb-1">تاریخ ایجاد</div>
            <div className="font-medium text-sm">
              {new Date(project.created_at).toLocaleDateString('fa-IR')}
            </div>
          </div>
        </div>

        {/* Deploy URL */}
        {deployUrl && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/50 rounded-xl">
            <p className="text-green-400">
              Deploy موفق! آدرس: <a href={deployUrl} target="_blank" rel="noopener noreferrer" className="underline">{deployUrl}</a>
            </p>
          </div>
        )}

        {/* پنل تحلیل سلامت در commit 3.3a حذف شد. کاربران باید برای
            تحلیل پروژه به /oversight بروند. */}

        <div className="grid lg:grid-cols-4 gap-6">
          {/* لیست فایل‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-4 sticky top-6">
              <h2 className="font-bold mb-4 flex items-center gap-2">
                <span>*</span> فایل‌های پروژه
              </h2>

              {files.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">-</div>
                  <p>هنوز فایلی تولید نشده</p>
                </div>
              ) : (
                <div className="space-y-1 max-h-[65vh] overflow-auto">
                  {files.map((file, idx) => {
                    const filePath = typeof file === 'string' ? file : file.path;
                    return (
                      <button
                        key={idx}
                        onClick={() => loadFileContent(filePath)}
                        className={`w-full text-right p-3 rounded-lg text-sm font-mono transition-all ${
                          selectedFile?.path === filePath
                            ? 'bg-blue-500/30 border border-blue-500'
                            : 'bg-white/5 hover:bg-white/10 border border-transparent'
                        }`}
                      >
                        <span className="ml-2">{getFileIcon(filePath)}</span>
                        <span className="truncate">{filePath}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ساختار پروژه */}
            {project.structure?.directories && project.structure.directories.length > 0 && (
              <div className="bg-white/10 backdrop-blur rounded-2xl p-4 mt-4">
                <h2 className="font-bold mb-3">* ساختار پوشه‌ها</h2>
                <div className="space-y-1 text-sm font-mono">
                  {project.structure.directories.map((dir, idx) => (
                    <div key={idx} className="text-blue-400">
                      + {dir}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* محتوای فایل */}
          <div className="lg:col-span-3">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold flex items-center gap-2">
                  {selectedFile ? (
                    <>
                      <span>{getFileIcon(selectedFile.path)}</span>
                      <span className="font-mono">{selectedFile.path}</span>
                    </>
                  ) : (
                    <span>محتوای فایل</span>
                  )}
                </h2>
                {selectedFile && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(selectedFile.content || '');
                      showSuccess('کپی شد!');
                    }}
                    className="px-3 py-1 bg-white/10 rounded text-sm hover:bg-white/20"
                  >
                    کپی
                  </button>
                )}
              </div>

              {fileLoading ? (
                <div className="text-center py-12 text-gray-400">
                  <div className="animate-spin text-3xl mb-2">*</div>
                  <p>در حال بارگذاری...</p>
                </div>
              ) : selectedFile?.content ? (
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-auto max-h-[70vh] text-sm leading-relaxed">
                    <code>{selectedFile.content}</code>
                  </pre>
                  <div className="absolute top-2 left-2 px-2 py-1 bg-gray-700 rounded text-xs text-gray-300">
                    {getLanguage(selectedFile.path)}
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 text-gray-400">
                  <div className="text-6xl mb-4">-</div>
                  <p className="text-lg">یک فایل از سمت راست انتخاب کن</p>
                </div>
              )}
            </div>

            {/* راهنمای Deploy */}
            <div className="bg-white/10 backdrop-blur rounded-2xl p-4 mt-4">
              <h2 className="font-bold mb-3">* راهنمای Deploy</h2>
              <div className="text-sm text-gray-300 space-y-2">
                <p>۱. دکمه "Deploy به Render" رو بزن</p>
                <p>۲. یا فایل‌ها رو دانلود کن و دستی آپلود کن به GitHub</p>
                <p>۳. بعد از Render اتصال بده به repo</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
