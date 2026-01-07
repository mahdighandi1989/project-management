'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Project {
  id: string;
  name: string;
  description?: string;
  type?: string;
  status?: string;
  progress?: number;
  created_at?: string;
}

interface AIModel {
  id: string;
  name: string;
  provider: string;
  capabilities: string[];
  is_available: boolean;
  priority?: number;
  strengths?: string[];
}

export default function CreatorPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // AI Models
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('auto');
  const [modelsLoading, setModelsLoading] = useState(false);

  // Create project
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');

  // Selected project for actions
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // Render deploy
  const [renderApiKey, setRenderApiKey] = useState('');
  const [renderConnected, setRenderConnected] = useState(false);

  // Diagrams
  const [showDiagrams, setShowDiagrams] = useState(false);
  const [diagrams, setDiagrams] = useState<any[]>([]);
  const [selectedDiagram, setSelectedDiagram] = useState<string>('');

  // Settings panel
  const [showSettings, setShowSettings] = useState(false);

  // Load on mount
  useEffect(() => {
    loadProjects();
    loadModels();
    checkRenderStatus();
  }, []);

  // Show message and auto-hide
  const showMessage = (type: 'success' | 'error' | 'info', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  // Load AI models
  const loadModels = async () => {
    setModelsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/models/available`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setModels(data);
        // Auto-select best model
        const best = data.find((m: AIModel) => m.is_available && m.priority === 1);
        if (best) {
          setSelectedModel(best.id);
        }
      }
    } catch (error) {
      console.error('Error loading models:', error);
    } finally {
      setModelsLoading(false);
    }
  };

  // Load all projects
  const loadProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects`);
      const data = await res.json();
      if (data.projects) {
        setProjects(data.projects);
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  // Get best model for task type
  const getBestModelForTask = (taskType: string): string => {
    const availableModels = models.filter(m => m.is_available);

    if (taskType === 'code') {
      const codeModel = availableModels.find(m =>
        m.capabilities?.includes('code') || m.id.includes('claude') || m.id.includes('gpt-4')
      );
      return codeModel?.id || selectedModel;
    }

    if (taskType === 'creative') {
      const creativeModel = availableModels.find(m =>
        m.capabilities?.includes('creative') || m.id.includes('claude')
      );
      return creativeModel?.id || selectedModel;
    }

    // Default: highest priority available
    const sorted = availableModels.sort((a, b) => (a.priority || 99) - (b.priority || 99));
    return sorted[0]?.id || selectedModel;
  };

  // Create new project
  const createProject = async () => {
    if (!newProjectName.trim()) {
      showMessage('error', 'لطفاً نام پروژه را وارد کنید');
      return;
    }

    setLoading(true);
    const modelToUse = selectedModel === 'auto' ? getBestModelForTask('code') : selectedModel;

    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProjectName,
          description: newProjectDesc || `پروژه ${newProjectName}`,
          project_type: 'web',
          model: modelToUse,
        }),
      });
      const data = await res.json();
      if (data.success || data.project) {
        showMessage('success', '✅ پروژه با موفقیت ساخته شد!');
        setNewProjectName('');
        setNewProjectDesc('');
        loadProjects();
      } else {
        showMessage('error', data.error || 'خطا در ساخت پروژه');
      }
    } catch (error) {
      showMessage('error', 'خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  // Check Render connection status
  const checkRenderStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/unified/deploy/render/status`);
      const data = await res.json();
      setRenderConnected(data.configured || false);
    } catch (error) {
      console.error('Error checking Render status:', error);
    }
  };

  // Connect to Render
  const connectRender = async () => {
    if (!renderApiKey.trim()) {
      showMessage('error', 'لطفاً API Key رندر را وارد کنید');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/unified/deploy/configure/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: renderApiKey }),
      });
      const data = await res.json();
      if (data.success) {
        setRenderConnected(true);
        setRenderApiKey('');
        showMessage('success', '✅ به رندر متصل شدید!');
      } else {
        showMessage('error', data.error || 'خطا در اتصال');
      }
    } catch (error) {
      showMessage('error', 'خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  // Deploy project to Render
  const deployToRender = async (project: Project) => {
    if (!renderConnected) {
      showMessage('error', 'ابتدا به رندر متصل شوید');
      return;
    }

    setLoading(true);
    showMessage('info', `🚀 در حال دیپلوی ${project.name}...`);

    try {
      const res = await fetch(`${API_BASE}/api/unified/projects/${project.id}/deploy/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.success) {
        showMessage('success', `✅ ${project.name} با موفقیت دیپلوی شد!`);
        if (data.deployment?.url) {
          window.open(data.deployment.url, '_blank');
        }
      } else {
        showMessage('error', data.error || 'خطا در دیپلوی');
      }
    } catch (error) {
      showMessage('error', 'خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  // Load diagrams for a project
  const loadDiagrams = async (project: Project) => {
    setSelectedProject(project);
    setShowDiagrams(true);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/unified/projects/${project.id}/diagrams`);
      const data = await res.json();
      if (data.success && data.diagrams?.length > 0) {
        setDiagrams(data.diagrams);
        setSelectedDiagram(data.diagrams[0].type);
      } else {
        setDiagrams([]);
        showMessage('info', 'نموداری برای این پروژه وجود ندارد');
      }
    } catch (error) {
      showMessage('error', 'خطا در بارگذاری نمودارها');
    } finally {
      setLoading(false);
    }
  };

  // Delete project
  const deleteProject = async (project: Project) => {
    if (!confirm(`آیا از حذف "${project.name}" مطمئن هستید؟`)) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${project.id}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        showMessage('success', '✅ پروژه حذف شد');
        loadProjects();
      } else {
        showMessage('error', data.error || 'خطا در حذف');
      }
    } catch (error) {
      showMessage('error', 'خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  const getDiagramName = (type: string) => {
    const names: Record<string, string> = {
      'class': '🏛️ ساختار کلاس‌ها',
      'flowchart': '📊 فلوچارت',
      'sequence': '📋 نمودار توالی',
      'er': '🗄️ دیتابیس',
      'mindmap': '🧠 نقشه ذهنی',
      'state': '🔄 حالت‌ها',
    };
    return names[type] || type;
  };

  const getProviderColor = (provider: string) => {
    const colors: Record<string, string> = {
      'anthropic': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      'openai': 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      'google': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      'deepseek': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    };
    return colors[provider?.toLowerCase()] || 'bg-gray-100 text-gray-700';
  };

  const availableModels = models.filter(m => m.is_available);
  const unavailableModels = models.filter(m => !m.is_available);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6" dir="rtl">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-2">
              🚀 موتور خالق هوشمند
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              پروژه بساز، یک کلیک دیپلوی کن، نمودارها رو ببین
            </p>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-3 rounded-xl transition ${
              showSettings
                ? 'bg-blue-500 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100'
            }`}
          >
            ⚙️ تنظیمات
          </button>
        </div>
      </div>

      {/* Message Toast */}
      {message && (
        <div className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 rounded-lg shadow-lg ${
          message.type === 'success' ? 'bg-green-500 text-white' :
          message.type === 'error' ? 'bg-red-500 text-white' :
          'bg-blue-500 text-white'
        }`}>
          {message.text}
        </div>
      )}

      {/* Settings Panel */}
      {showSettings && (
        <div className="max-w-6xl mx-auto mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">⚙️ تنظیمات و مدل‌های AI</h2>
              <button
                onClick={loadModels}
                disabled={modelsLoading}
                className="px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm hover:bg-blue-200"
              >
                {modelsLoading ? '⏳' : '🔄 بروزرسانی مدل‌ها'}
              </button>
            </div>

            {/* Available Models */}
            <div className="mb-6">
              <h3 className="font-bold mb-3 text-green-600 dark:text-green-400">
                ✅ مدل‌های فعال ({availableModels.length})
              </h3>
              {availableModels.length === 0 ? (
                <p className="text-gray-500 text-sm">هیچ مدلی فعال نیست. به تنظیمات بروید و API Key وارد کنید.</p>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {availableModels.map((model) => (
                    <div
                      key={model.id}
                      onClick={() => setSelectedModel(model.id)}
                      className={`p-4 rounded-xl cursor-pointer transition border-2 ${
                        selectedModel === model.id
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-transparent bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{model.name}</span>
                        {selectedModel === model.id && <span className="text-blue-500">✓</span>}
                      </div>
                      <span className={`text-xs px-2 py-1 rounded ${getProviderColor(model.provider)}`}>
                        {model.provider}
                      </span>
                      {model.capabilities && model.capabilities.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {model.capabilities.slice(0, 3).map((cap) => (
                            <span key={cap} className="text-xs bg-gray-200 dark:bg-gray-600 px-2 py-0.5 rounded">
                              {cap}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Unavailable Models */}
            {unavailableModels.length > 0 && (
              <div>
                <h3 className="font-bold mb-3 text-gray-400">
                  ❌ مدل‌های غیرفعال ({unavailableModels.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {unavailableModels.map((model) => (
                    <span
                      key={model.id}
                      className="text-sm px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-400 rounded-lg"
                    >
                      {model.name}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  برای فعال‌سازی، به صفحه تنظیمات بروید و API Key‌ها را وارد کنید
                </p>
              </div>
            )}

            {/* Link to Settings */}
            <div className="mt-6 pt-4 border-t dark:border-gray-700">
              <a
                href="/settings"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 transition"
              >
                ⚙️ رفتن به تنظیمات کامل
              </a>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto grid lg:grid-cols-3 gap-6">

        {/* Right Column - Projects List */}
        <div className="lg:col-span-2 space-y-6">

          {/* My Projects */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2">
                📁 پروژه‌های من
                <span className="text-sm font-normal text-gray-500">({projects.length})</span>
              </h2>
              <button
                onClick={loadProjects}
                className="text-gray-400 hover:text-gray-600 p-2"
                title="بروزرسانی"
              >
                🔄
              </button>
            </div>

            {projects.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-5xl mb-4">📭</div>
                <p>هنوز پروژه‌ای نساختید</p>
                <p className="text-sm mt-2">از بخش کناری یک پروژه جدید بسازید</p>
              </div>
            ) : (
              <div className="space-y-4">
                {projects.map((project) => (
                  <div
                    key={project.id}
                    className="border dark:border-gray-700 rounded-xl p-4 hover:shadow-md transition"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-bold text-lg">{project.name}</h3>
                        {project.description && (
                          <p className="text-sm text-gray-500 mt-1">{project.description}</p>
                        )}
                        <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                          <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
                            {project.type || 'web'}
                          </span>
                          {project.progress !== undefined && (
                            <span className={`px-2 py-1 rounded ${
                              project.progress === 100
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            }`}>
                              {project.progress}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => deployToRender(project)}
                        disabled={loading || !renderConnected}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg text-sm hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        🚀 دیپلوی به رندر
                      </button>

                      <button
                        onClick={() => loadDiagrams(project)}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm hover:bg-blue-200"
                      >
                        📊 نمودارها
                      </button>

                      <button
                        onClick={() => window.open(`/projects?id=${project.id}`, '_self')}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-200"
                      >
                        📝 جزئیات
                      </button>

                      <button
                        onClick={() => deleteProject(project)}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-sm"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Diagrams Modal/Section */}
          {showDiagrams && selectedProject && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">
                  📊 نمودارهای {selectedProject.name}
                </h2>
                <button
                  onClick={() => setShowDiagrams(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ✕
                </button>
              </div>

              {diagrams.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>نموداری یافت نشد</p>
                  <p className="text-sm mt-2">پروژه باید فایل‌های کد داشته باشد</p>
                </div>
              ) : (
                <div>
                  {/* Diagram Type Buttons */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {diagrams.map((d) => (
                      <button
                        key={d.type}
                        onClick={() => setSelectedDiagram(d.type)}
                        className={`px-4 py-2 rounded-lg text-sm transition ${
                          selectedDiagram === d.type
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {getDiagramName(d.type)}
                      </button>
                    ))}
                  </div>

                  {/* Diagram Preview */}
                  {selectedDiagram && (
                    <div className="border dark:border-gray-700 rounded-xl p-4">
                      <div className="flex justify-end mb-2">
                        <button
                          onClick={() => {
                            const content = diagrams.find(d => d.type === selectedDiagram)?.content;
                            if (content) {
                              const encoded = btoa(unescape(encodeURIComponent(content)));
                              window.open(`https://mermaid.live/edit#base64:${encoded}`, '_blank');
                            }
                          }}
                          className="px-3 py-1 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200"
                        >
                          🌐 باز کردن در Mermaid Live
                        </button>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 overflow-auto max-h-96">
                        <img
                          src={`https://mermaid.ink/img/${btoa(diagrams.find(d => d.type === selectedDiagram)?.content || '')}`}
                          alt="Diagram"
                          className="max-w-full mx-auto"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                        <pre className="text-xs text-gray-600 dark:text-gray-400 mt-4 whitespace-pre-wrap">
                          {diagrams.find(d => d.type === selectedDiagram)?.content}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Left Column - Actions */}
        <div className="space-y-6">

          {/* Create New Project */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              ✨ پروژه جدید
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  نام پروژه
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="مثال: فروشگاه آنلاین"
                  className="w-full p-3 border dark:border-gray-600 rounded-xl dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  توضیحات (اختیاری)
                </label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="چه چیزی می‌خواهید بسازید؟"
                  rows={3}
                  className="w-full p-3 border dark:border-gray-600 rounded-xl dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                />
              </div>

              {/* Model Selection */}
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  🤖 مدل AI
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full p-3 border dark:border-gray-600 rounded-xl dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="auto">🎯 انتخاب هوشمند (پیشنهادی)</option>
                  {availableModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedModel === 'auto'
                    ? '✨ بهترین مدل برای کار شما انتخاب می‌شود'
                    : `مدل انتخابی: ${models.find(m => m.id === selectedModel)?.name}`
                  }
                </p>
              </div>

              <button
                onClick={createProject}
                disabled={loading || !newProjectName.trim() || availableModels.length === 0}
                className="w-full py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-bold hover:from-green-600 hover:to-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {loading ? '⏳ در حال ساخت...' : '🎉 ساخت پروژه'}
              </button>

              {availableModels.length === 0 && (
                <p className="text-sm text-orange-500 text-center">
                  ⚠️ ابتدا یک مدل AI فعال کنید
                </p>
              )}
            </div>
          </div>

          {/* Render Connection */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              ☁️ اتصال به رندر
            </h2>

            {renderConnected ? (
              <div className="text-center py-4">
                <div className="text-4xl mb-2">✅</div>
                <p className="text-green-600 dark:text-green-400 font-medium">متصل شده</p>
                <p className="text-sm text-gray-500 mt-2">می‌توانید پروژه‌ها را دیپلوی کنید</p>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">
                  برای دیپلوی خودکار، API Key رندر را وارد کنید
                </p>
                <input
                  type="password"
                  value={renderApiKey}
                  onChange={(e) => setRenderApiKey(e.target.value)}
                  placeholder="rnd_xxxxxxxxxxxx"
                  className="w-full p-3 border dark:border-gray-600 rounded-xl dark:bg-gray-700 focus:ring-2 focus:ring-purple-500 outline-none font-mono text-sm"
                  dir="ltr"
                />
                <button
                  onClick={connectRender}
                  disabled={loading || !renderApiKey.trim()}
                  className="w-full py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-xl font-bold hover:from-purple-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {loading ? '⏳ در حال اتصال...' : '🔗 اتصال به رندر'}
                </button>
                <a
                  href="https://dashboard.render.com/u/settings/api-keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-center text-sm text-blue-500 hover:underline"
                >
                  📖 راهنمای دریافت API Key
                </a>
              </div>
            )}
          </div>

          {/* Quick Help */}
          <div className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-2xl p-6">
            <h3 className="font-bold mb-3 flex items-center gap-2">
              💡 راهنمای سریع
            </h3>
            <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex items-start gap-2">
                <span className="text-lg">1️⃣</span>
                <span>یک پروژه جدید بسازید</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-lg">2️⃣</span>
                <span>به رندر متصل شوید (یکبار کافیه)</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-lg">3️⃣</span>
                <span>روی "دیپلوی به رندر" کلیک کنید</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-lg">✨</span>
                <span>تمام! پروژه شما آنلاین شد</span>
              </div>
            </div>
          </div>

          {/* Active Model Indicator */}
          {availableModels.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">مدل فعال:</span>
                <span className={`text-sm px-3 py-1 rounded-lg ${getProviderColor(
                  models.find(m => m.id === selectedModel)?.provider || ''
                )}`}>
                  {selectedModel === 'auto'
                    ? '🎯 هوشمند'
                    : models.find(m => m.id === selectedModel)?.name || selectedModel
                  }
                </span>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
