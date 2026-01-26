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

interface MemoryInstructions {
  content: string;
  target_models: string[];
}

interface DynamicField {
  id: string;
  name: string;
  value: string;
  target_models: string[];
}

interface AIModel {
  id: string;
  name: string;
  icon: string;
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

  // تب فعال
  const [activeTab, setActiveTab] = useState<'files' | 'memory'>('files');

  // Memory Box State
  const [memoryInstructions, setMemoryInstructions] = useState<MemoryInstructions>({
    content: '',
    target_models: ['all']
  });
  const [dynamicFields, setDynamicFields] = useState<DynamicField[]>([]);
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [savingMemory, setSavingMemory] = useState(false);

  // New Field Form
  const [showNewFieldForm, setShowNewFieldForm] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldValue, setNewFieldValue] = useState('');
  const [newFieldModels, setNewFieldModels] = useState<string[]>(['all']);

  // Edit Field
  const [editingField, setEditingField] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadProject();
      loadMemory();
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

  const loadMemory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setMemoryInstructions(data.memory_instructions || { content: '', target_models: ['all'] });
          setDynamicFields(data.dynamic_fields || []);
          setAvailableModels(data.available_models || []);
        }
      }
    } catch (e) {
      console.error('Error loading memory:', e);
    }
  };

  const saveMemoryInstructions = async () => {
    setSavingMemory(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/instructions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(memoryInstructions),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('باکس حافظه ذخیره شد');
      } else {
        showError(data.detail || 'خطا در ذخیره');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setSavingMemory(false);
    }
  };

  const addDynamicField = async () => {
    if (!newFieldName.trim() || !newFieldValue.trim()) {
      showError('نام و مقدار فیلد الزامی است');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newFieldName,
          value: newFieldValue,
          target_models: newFieldModels,
        }),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فیلد جدید اضافه شد');
        setNewFieldName('');
        setNewFieldValue('');
        setNewFieldModels(['all']);
        setShowNewFieldForm(false);
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const updateDynamicField = async (field: DynamicField) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${field.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(field),
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فیلد بروزرسانی شد');
        setEditingField(null);
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const deleteDynamicField = async (fieldId: string) => {
    if (!confirm('حذف شود؟')) return;

    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/memory/fields/${fieldId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        showSuccess('فیلد حذف شد');
        loadMemory();
      } else {
        showError(data.detail || 'خطا');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    }
  };

  const toggleModel = (modelId: string, currentModels: string[], setModels: (m: string[]) => void) => {
    if (modelId === 'all') {
      setModels(['all']);
    } else {
      let newModels = currentModels.filter(m => m !== 'all');
      if (newModels.includes(modelId)) {
        newModels = newModels.filter(m => m !== modelId);
      } else {
        newModels.push(modelId);
      }
      if (newModels.length === 0) {
        newModels = ['all'];
      }
      setModels(newModels);
    }
  };

  const loadFileContent = async (filePath: string) => {
    try {
      let res;
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

  // Model selector component
  const ModelSelector = ({ selectedModels, onChange }: { selectedModels: string[], onChange: (models: string[]) => void }) => (
    <div className="flex flex-wrap gap-2 mt-2">
      {availableModels.map(model => (
        <button
          key={model.id}
          onClick={() => toggleModel(model.id, selectedModels, onChange)}
          className={`px-3 py-1 rounded-full text-xs flex items-center gap-1 transition ${
            selectedModels.includes(model.id) || (selectedModels.includes('all') && model.id === 'all')
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'
          }`}
        >
          <span>{model.icon}</span>
          <span>{model.name}</span>
        </button>
      ))}
    </div>
  );

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
                  {deploying ? '⏳ در حال Deploy...' : '🚀 Deploy'}
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

        {/* تب‌ها */}
        <div className="flex border-b mb-6">
          <button
            onClick={() => setActiveTab('files')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'files'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            📁 فایل‌ها
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`px-6 py-3 font-medium ${
              activeTab === 'memory'
                ? 'border-b-2 border-purple-500 text-purple-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🧠 حافظه و دستورات AI
          </button>
        </div>

        {/* محتوای تب فایل‌ها */}
        {activeTab === 'files' && (
          <>
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

            <div className="grid lg:grid-cols-3 gap-6">
              {/* لیست فایل‌ها */}
              <div className="lg:col-span-1">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
                  <h2 className="font-bold mb-4">📁 فایل‌های پروژه ({files.length})</h2>

                  {files.length === 0 ? (
                    <div className="text-center py-8 text-gray-400">
                      <div className="text-4xl mb-2">📭</div>
                      <p>{project.project_type === 'github_import' ? 'فایلی import نشده' : 'هنوز فایلی تولید نشده'}</p>
                    </div>
                  ) : (
                    <div className="space-y-1 max-h-[60vh] overflow-auto">
                      {files.map((file, idx) => {
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
                              <span>📄</span>
                              <span className="truncate font-mono text-xs" title={file.path}>{file.path}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
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
                        className="text-sm text-blue-500 hover:underline"
                      >
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
          </>
        )}

        {/* محتوای تب حافظه */}
        {activeTab === 'memory' && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* باکس حافظه - دستورات ثابت */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-2xl">🧠</span>
                <h2 className="font-bold text-lg">باکس حافظه (دستورات ثابت)</h2>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                دستوراتی که همیشه توسط مدل‌های AI در این پروژه رعایت می‌شوند
              </p>

              <textarea
                value={memoryInstructions.content}
                onChange={(e) => setMemoryInstructions({ ...memoryInstructions, content: e.target.value })}
                placeholder="مثال: همیشه کدها را به زبان فارسی کامنت‌گذاری کن. از TypeScript استفاده کن. کدها باید تست‌پذیر باشند..."
                className="w-full h-48 p-4 border rounded-lg resize-none dark:bg-gray-700 dark:border-gray-600 text-sm"
                dir="rtl"
              />

              <div className="mt-4">
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  این دستورات برای کدام مدل‌ها اعمال شود؟
                </label>
                <ModelSelector
                  selectedModels={memoryInstructions.target_models}
                  onChange={(models) => setMemoryInstructions({ ...memoryInstructions, target_models: models })}
                />
              </div>

              <button
                onClick={saveMemoryInstructions}
                disabled={savingMemory}
                className="mt-4 w-full py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
              >
                {savingMemory ? '⏳ در حال ذخیره...' : '💾 ذخیره باکس حافظه'}
              </button>
            </div>

            {/* فیلدهای پویا */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">📝</span>
                  <h2 className="font-bold text-lg">فیلدهای پویا</h2>
                </div>
                <button
                  onClick={() => setShowNewFieldForm(true)}
                  className="px-3 py-1 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600"
                >
                  + افزودن فیلد
                </button>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                دستورات متغیر که ممکن است زود به زود تغییر کنند
              </p>

              {/* فرم افزودن فیلد جدید */}
              {showNewFieldForm && (
                <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <h3 className="font-medium mb-3">فیلد جدید</h3>
                  <input
                    type="text"
                    placeholder="نام فیلد (مثلاً: اولویت فعلی)"
                    value={newFieldName}
                    onChange={(e) => setNewFieldName(e.target.value)}
                    className="w-full p-2 border rounded mb-2 dark:bg-gray-700 dark:border-gray-600 text-sm"
                  />
                  <textarea
                    placeholder="مقدار فیلد (مثلاً: تمرکز روی عملکرد و سرعت)"
                    value={newFieldValue}
                    onChange={(e) => setNewFieldValue(e.target.value)}
                    className="w-full p-2 border rounded mb-2 dark:bg-gray-700 dark:border-gray-600 text-sm h-20 resize-none"
                  />
                  <div className="mb-3">
                    <label className="text-xs text-gray-500">مدل‌های هدف:</label>
                    <ModelSelector
                      selectedModels={newFieldModels}
                      onChange={setNewFieldModels}
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={addDynamicField}
                      className="flex-1 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
                    >
                      افزودن
                    </button>
                    <button
                      onClick={() => { setShowNewFieldForm(false); setNewFieldName(''); setNewFieldValue(''); }}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg text-sm"
                    >
                      انصراف
                    </button>
                  </div>
                </div>
              )}

              {/* لیست فیلدها */}
              <div className="space-y-3 max-h-[50vh] overflow-auto">
                {dynamicFields.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <div className="text-4xl mb-2">📭</div>
                    <p>فیلدی تعریف نشده</p>
                  </div>
                ) : (
                  dynamicFields.map((field) => (
                    <div
                      key={field.id}
                      className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                    >
                      {editingField === field.id ? (
                        // حالت ویرایش
                        <div>
                          <input
                            type="text"
                            value={field.name}
                            onChange={(e) => {
                              const updated = dynamicFields.map(f =>
                                f.id === field.id ? { ...f, name: e.target.value } : f
                              );
                              setDynamicFields(updated);
                            }}
                            className="w-full p-2 border rounded mb-2 dark:bg-gray-600 dark:border-gray-500 text-sm"
                          />
                          <textarea
                            value={field.value}
                            onChange={(e) => {
                              const updated = dynamicFields.map(f =>
                                f.id === field.id ? { ...f, value: e.target.value } : f
                              );
                              setDynamicFields(updated);
                            }}
                            className="w-full p-2 border rounded mb-2 dark:bg-gray-600 dark:border-gray-500 text-sm h-20 resize-none"
                          />
                          <div className="mb-2">
                            <ModelSelector
                              selectedModels={field.target_models}
                              onChange={(models) => {
                                const updated = dynamicFields.map(f =>
                                  f.id === field.id ? { ...f, target_models: models } : f
                                );
                                setDynamicFields(updated);
                              }}
                            />
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => updateDynamicField(field)}
                              className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                            >
                              ذخیره
                            </button>
                            <button
                              onClick={() => { setEditingField(null); loadMemory(); }}
                              className="px-3 py-1 bg-gray-300 dark:bg-gray-600 rounded text-sm"
                            >
                              انصراف
                            </button>
                          </div>
                        </div>
                      ) : (
                        // حالت نمایش
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium">{field.name}</span>
                            <div className="flex gap-1">
                              <button
                                onClick={() => setEditingField(field.id)}
                                className="p-1 text-blue-500 hover:bg-blue-100 rounded"
                                title="ویرایش"
                              >
                                ✏️
                              </button>
                              <button
                                onClick={() => deleteDynamicField(field.id)}
                                className="p-1 text-red-500 hover:bg-red-100 rounded"
                                title="حذف"
                              >
                                🗑️
                              </button>
                            </div>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                            {field.value}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {field.target_models.map(m => {
                              const model = availableModels.find(am => am.id === m);
                              return (
                                <span
                                  key={m}
                                  className="px-2 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-xs"
                                >
                                  {model?.icon} {model?.name || m}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
