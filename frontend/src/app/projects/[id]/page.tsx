'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

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
  type?: string;
  status?: string;
  created_at?: string;
  files?: ProjectFile[];
  structure?: {
    directories?: string[];
    files?: any[];
  };
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<ProjectFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [deploying, setDeploying] = useState(false);

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
      // اول از creator بگیر
      let res = await fetch(`${API_BASE}/api/creator/projects/${projectId}`);
      let data = await res.json();

      if (res.ok && data.project) {
        setProject(data.project);
        if (data.project.files) {
          setFiles(data.project.files.map((f: any) =>
            typeof f === 'string' ? { path: f } : f
          ));
        }
      } else {
        // اگه نبود از projects بگیر
        res = await fetch(`${API_BASE}/api/projects/${projectId}`);
        data = await res.json();
        if (res.ok) {
          setProject(data.project || data);
        } else {
          showError('پروژه پیدا نشد');
        }
      }

      // فایل‌های پروژه رو بگیر
      const filesRes = await fetch(`${API_BASE}/api/projects/${projectId}/files`);
      if (filesRes.ok) {
        const filesData = await filesRes.json();
        if (filesData.files) {
          setFiles(filesData.files);
        }
      }
    } catch (e) {
      showError('خطا در بارگذاری پروژه');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filePath: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/files/${encodeURIComponent(filePath)}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedFile({ path: filePath, content: data.content });
      }
    } catch (e) {
      showError('خطا در خواندن فایل');
    }
  };

  const deployToRender = async () => {
    setDeploying(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/deploy/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      if (data.success) {
        showSuccess(`Deploy شروع شد! ${data.deploy_url || ''}`);
      } else {
        showError(data.error || 'خطا در Deploy');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setDeploying(false);
    }
  };

  const generateMoreFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/creator/projects/${projectId}/generate`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فایل‌های جدید تولید شدند');
        loadProject();
      } else {
        showError(data.error || 'خطا');
      }
    } catch (e) {
      showError('خطا');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p>در حال بارگذاری پروژه...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <p className="text-xl mb-4">پروژه پیدا نشد</p>
          <Link href="/projects" className="text-blue-500 hover:underline">
            برگشت به لیست پروژه‌ها
          </Link>
        </div>
      </div>
    );
  }

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

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Link href="/projects" className="hover:text-blue-500">پروژه‌ها</Link>
              <span>/</span>
              <span>{project.name}</span>
            </div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            {project.description && (
              <p className="text-gray-500 mt-1">{project.description}</p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={generateMoreFiles}
              className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
            >
              🔄 تولید بیشتر
            </button>
            <button
              onClick={deployToRender}
              disabled={deploying}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
            >
              {deploying ? '⏳ در حال Deploy...' : '🚀 Deploy به Render'}
            </button>
            <Link
              href="/projects"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
            >
              برگشت
            </Link>
          </div>
        </div>

        {/* اطلاعات پروژه */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-500">نوع</div>
            <div className="font-medium">{project.type || 'نامشخص'}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-500">وضعیت</div>
            <div className="font-medium">{project.status || 'ایجاد شده'}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-500">تعداد فایل</div>
            <div className="font-medium">{files.length}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
            <div className="text-sm text-gray-500">شناسه</div>
            <div className="font-mono text-xs truncate">{project.id}</div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* لیست فایل‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              <h2 className="font-bold mb-4">📁 فایل‌های پروژه</h2>

              {files.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">📭</div>
                  <p>هنوز فایلی تولید نشده</p>
                  <button
                    onClick={generateMoreFiles}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm"
                  >
                    تولید فایل‌ها
                  </button>
                </div>
              ) : (
                <div className="space-y-1 max-h-[60vh] overflow-auto">
                  {files.map((file, idx) => (
                    <div
                      key={idx}
                      onClick={() => loadFileContent(file.path)}
                      className={`p-2 rounded cursor-pointer text-sm font-mono ${
                        selectedFile?.path === file.path
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {file.path.endsWith('/') ? '📁' : '📄'} {file.path}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ساختار پروژه */}
            {project.structure && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mt-4">
                <h2 className="font-bold mb-4">🗂️ ساختار</h2>
                <div className="text-sm font-mono space-y-1">
                  {project.structure.directories?.map((dir, idx) => (
                    <div key={idx} className="text-blue-600">📁 {dir}</div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* محتوای فایل */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              <h2 className="font-bold mb-4">
                {selectedFile ? `📄 ${selectedFile.path}` : '📝 محتوای فایل'}
              </h2>

              {selectedFile?.content ? (
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto max-h-[70vh] text-sm">
                  <code>{selectedFile.content}</code>
                </pre>
              ) : (
                <div className="text-center py-12 text-gray-400">
                  <div className="text-6xl mb-4">👈</div>
                  <p>یک فایل از سمت راست انتخاب کنید</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
