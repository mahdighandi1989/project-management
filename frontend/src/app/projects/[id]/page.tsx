'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProjectFile {
  path: string;
  content?: string;
  size?: number;
  type?: string;
  github_url?: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  type?: string;
  project_type?: string;
  status?: string;
  created_at?: string;
  files?: ProjectFile[];
  structure?: {
    directories?: string[];
    files?: any[];
    file_tree?: any[];
  };
  metadata?: {
    source?: string;
    source_url?: string;
    owner?: string;
    repo?: string;
    private?: boolean;
    stats?: {
      stars?: number;
      forks?: number;
      file_count?: number;
    };
    primary_language?: string;
  };
  technologies?: string[];
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
      let foundProject = false;

      // اگر ID با gh_ شروع میشه، از GitHub API بگیر
      if (projectId.startsWith('gh_')) {
        const res = await fetch(`${API_BASE}/api/github/imported/${projectId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.project) {
            setProject(data.project);
            if (data.project.files) {
              setFiles(data.project.files.map((f: any) => ({
                path: f.path,
                size: f.size,
                type: f.type,
                github_url: f.github_url,
              })));
            }
            foundProject = true;
          }
        }
      }

      // اگر پیدا نشد، از creator بگیر
      if (!foundProject) {
        let res = await fetch(`${API_BASE}/api/creator/projects/${projectId}`);
        let data = await res.json();

        if (res.ok && data.project) {
          setProject(data.project);
          if (data.project.files) {
            setFiles(data.project.files.map((f: any) =>
              typeof f === 'string' ? { path: f } : f
            ));
          }
          foundProject = true;
        }
      }

      // اگر هنوز پیدا نشد، از projects API بگیر
      if (!foundProject) {
        const res = await fetch(`${API_BASE}/api/projects/${projectId}`);
        const data = await res.json();
        if (res.ok) {
          setProject(data.project || data);
          foundProject = true;
        }
      }

      // اگر پروژه پیدا نشد
      if (!foundProject) {
        showError('پروژه پیدا نشد');
        return;
      }

      // فایل‌های پروژه رو بگیر (برای پروژه‌های غیر GitHub)
      if (!projectId.startsWith('gh_')) {
        const filesRes = await fetch(`${API_BASE}/api/projects/${projectId}/files`);
        if (filesRes.ok) {
          const filesData = await filesRes.json();
          if (filesData.files) {
            setFiles(filesData.files);
          }
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
      let res;
      // برای پروژه‌های GitHub از API مخصوص استفاده کن
      if (projectId.startsWith('gh_')) {
        res = await fetch(`${API_BASE}/api/github/imported/${projectId}/file?path=${encodeURIComponent(filePath)}`);
      } else {
        res = await fetch(`${API_BASE}/api/projects/${projectId}/files/${encodeURIComponent(filePath)}`);
      }

      if (res.ok) {
        const data = await res.json();
        setSelectedFile({
          path: filePath,
          content: data.content,
          github_url: data.github_url,
        });
      } else {
        showError('فایل یافت نشد');
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
              {project.project_type === 'github_import' && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">GitHub</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {project.project_type === 'github_import' && (
                <svg className="w-6 h-6 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
              )}
              <h1 className="text-2xl font-bold">{project.name}</h1>
            </div>
            {project.description && (
              <p className="text-gray-500 mt-1">{project.description}</p>
            )}
          </div>
          <div className="flex gap-2">
            {project.project_type === 'github_import' && project.metadata?.source_url && (
              <a
                href={project.metadata.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                مشاهده در GitHub
              </a>
            )}
            {project.project_type !== 'github_import' && (
              <>
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
              </>
            )}
            <Link
              href="/projects"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
            >
              برگشت
            </Link>
          </div>
        </div>

        {/* اطلاعات پروژه - GitHub */}
        {project.project_type === 'github_import' && project.metadata && (
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl mb-1">⭐</div>
              <div className="font-bold">{project.metadata.stats?.stars || 0}</div>
              <div className="text-xs text-gray-500">ستاره</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl mb-1">🍴</div>
              <div className="font-bold">{project.metadata.stats?.forks || 0}</div>
              <div className="text-xs text-gray-500">فورک</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl mb-1">📄</div>
              <div className="font-bold">{files.length}</div>
              <div className="text-xs text-gray-500">فایل</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl mb-1">💻</div>
              <div className="font-bold text-sm">{project.metadata.primary_language || '-'}</div>
              <div className="text-xs text-gray-500">زبان</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-2xl mb-1">{project.metadata.private ? '🔒' : '🌐'}</div>
              <div className="font-bold text-sm">{project.metadata.private ? 'خصوصی' : 'عمومی'}</div>
              <div className="text-xs text-gray-500">دسترسی</div>
            </div>
          </div>
        )}

        {/* اطلاعات پروژه - عادی */}
        {project.project_type !== 'github_import' && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-500">نوع</div>
              <div className="font-medium">{project.type || project.project_type || 'نامشخص'}</div>
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
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* لیست فایل‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              <h2 className="font-bold mb-4">📁 فایل‌های پروژه</h2>

              {files.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="text-4xl mb-2">📭</div>
                  <p>{project.project_type === 'github_import' ? 'فایلی import نشده' : 'هنوز فایلی تولید نشده'}</p>
                  {project.project_type !== 'github_import' && (
                    <button
                      onClick={generateMoreFiles}
                      className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm"
                    >
                      تولید فایل‌ها
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-1 max-h-[60vh] overflow-auto">
                  {files.map((file, idx) => {
                    const fileName = file.path.split('/').pop() || file.path;
                    const isSelected = selectedFile?.path === file.path;
                    return (
                      <div
                        key={idx}
                        onClick={() => loadFileContent(file.path)}
                        className={`p-2 rounded cursor-pointer text-sm ${
                          isSelected
                            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600'
                            : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span>{file.path.endsWith('/') ? '📁' : '📄'}</span>
                          <span className="truncate font-mono text-xs" title={file.path}>{file.path}</span>
                        </div>
                        {file.size && (
                          <div className="text-xs text-gray-400 mr-5">
                            {file.size > 1024 ? `${(file.size / 1024).toFixed(1)} KB` : `${file.size} B`}
                          </div>
                        )}
                      </div>
                    );
                  })}
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
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">
                  {selectedFile ? `📄 ${selectedFile.path}` : '📝 محتوای فایل'}
                </h2>
                {selectedFile?.github_url && (
                  <a
                    href={selectedFile.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-500 hover:underline flex items-center gap-1"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                    </svg>
                    مشاهده در GitHub
                  </a>
                )}
              </div>

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
