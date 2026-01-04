'use client';

import { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import {
  PlusIcon,
  TrashIcon,
  PencilIcon,
  PlayIcon,
  SparklesIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
  DocumentTextIcon,
  FolderIcon,
  Cog6ToothIcon,
  EyeIcon,
  XMarkIcon,
  RocketLaunchIcon,
} from '@heroicons/react/24/outline';

// Types
interface Project {
  project_id: string;
  name: string;
  description?: string;
  type: string;
  status: string;
  progress: number;
  goal?: string;
  complexity?: string;
  created_at: string;
  updated_at: string;
  phases?: Phase[];
  model_scores?: Record<string, any>;
  conversations?: any[];
  files?: any[];
}

interface Phase {
  id: string;
  name: string;
  description?: string;
  status: string;
  progress: number;
  steps: string[];
  completed_steps: string[];
  started_at?: string;
  completed_at?: string;
}

interface SmartSetupResult {
  success: boolean;
  project_id?: string;
  analysis?: {
    project_name: string;
    project_type: string;
    description: string;
    goal: string;
    complexity: string;
    technologies: string[];
    features: string[];
    phases: any[];
    estimated_files: string[];
    risks: string[];
    success_criteria: string[];
  };
  error?: string;
}

// API URL helper
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const runtimeUrl = (window as any).__NEXT_PUBLIC_API_URL__;
    if (runtimeUrl) return runtimeUrl;
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

// API functions
const api = {
  async listProjects(): Promise<Project[]> {
    const res = await fetch(`${getApiUrl()}/api/projects`);
    const data = await res.json();
    return data.success ? data.projects : [];
  },

  async getProject(id: string): Promise<Project | null> {
    const res = await fetch(`${getApiUrl()}/api/projects/${id}`);
    const data = await res.json();
    return data.success ? data.project : null;
  },

  async deleteProject(id: string): Promise<boolean> {
    const res = await fetch(`${getApiUrl()}/api/projects/${id}`, { method: 'DELETE' });
    const data = await res.json();
    return data.success;
  },

  async smartSetup(request: string): Promise<SmartSetupResult> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/smart-setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request }),
    });
    return res.json();
  },

  async executeTask(projectId: string, task: string, category: string = 'code_generation'): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/execute-task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, task, category }),
    });
    return res.json();
  },

  async startNextPhase(id: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/projects/${id}/next-phase`, { method: 'POST' });
    return res.json();
  },

  async startAutoBuild(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/auto-build`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    });
    return res.json();
  },

  async startWorkflow(projectId: string, autoExecute: boolean = true): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/start-workflow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, auto_execute: autoExecute }),
    });
    return res.json();
  },

  async getWorkflowStatus(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/workflow-status/${projectId}`);
    return res.json();
  },

  async getAvailableModels(): Promise<any[]> {
    const res = await fetch(`${getApiUrl()}/api/models/available`);
    const data = await res.json();
    return data || [];
  },
};

// Status helpers
const getStatusInfo = (status: string) => {
  const statusMap: Record<string, { icon: any; color: string; text: string }> = {
    active: { icon: PlayIcon, color: 'text-blue-500 bg-blue-50', text: 'فعال' },
    completed: { icon: CheckCircleIcon, color: 'text-green-500 bg-green-50', text: 'تکمیل شده' },
    pending: { icon: ArrowPathIcon, color: 'text-yellow-500 bg-yellow-50', text: 'در انتظار' },
    failed: { icon: ExclamationTriangleIcon, color: 'text-red-500 bg-red-50', text: 'ناموفق' },
    in_progress: { icon: ArrowPathIcon, color: 'text-blue-500 bg-blue-50', text: 'در حال اجرا' },
  };
  return statusMap[status] || statusMap.pending;
};

const PROJECT_TYPES: Record<string, { name: string; icon: string }> = {
  web_app: { name: 'اپلیکیشن وب', icon: '🌐' },
  mobile_app: { name: 'اپلیکیشن موبایل', icon: '📱' },
  api_service: { name: 'سرویس API', icon: '⚙️' },
  data_pipeline: { name: 'پایپلاین داده', icon: '📊' },
  ml_project: { name: 'پروژه ML', icon: '🤖' },
  custom: { name: 'سفارشی', icon: '📦' },
};

export default function ProjectsPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);

  // Modal states
  const [showSmartSetup, setShowSmartSetup] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [showExecuteTask, setShowExecuteTask] = useState(false);

  // Smart setup state
  const [smartRequest, setSmartRequest] = useState('');
  const [setupResult, setSetupResult] = useState<SmartSetupResult | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);

  // Task execution state
  const [taskInput, setTaskInput] = useState('');
  const [taskCategory, setTaskCategory] = useState('code_generation');
  const [taskResult, setTaskResult] = useState<any>(null);

  // Load data
  useEffect(() => {
    loadProjects();
    loadModels();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const data = await api.listProjects();
      setProjects(data);
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async () => {
    try {
      const data = await api.getAvailableModels();
      setAvailableModels(data);
    } catch (error) {
      console.error('Error loading models:', error);
    }
  };

  const selectProject = async (id: string) => {
    setActionLoading(true);
    try {
      const project = await api.getProject(id);
      setSelectedProject(project);
    } catch (error) {
      console.error('Error loading project:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const deleteProject = async (id: string) => {
    setActionLoading(true);
    try {
      const success = await api.deleteProject(id);
      if (success) {
        setProjects(projects.filter(p => p.project_id !== id));
        if (selectedProject?.project_id === id) {
          setSelectedProject(null);
        }
      }
    } catch (error) {
      console.error('Error deleting project:', error);
    } finally {
      setActionLoading(false);
      setShowDeleteConfirm(null);
    }
  };

  const handleSmartSetup = async () => {
    if (!smartRequest.trim()) return;

    setSetupLoading(true);
    setSetupResult(null);

    try {
      const result = await api.smartSetup(smartRequest);
      setSetupResult(result);

      if (result.success && result.project_id) {
        await loadProjects();
      }
    } catch (error) {
      console.error('Error in smart setup:', error);
      setSetupResult({ success: false, error: 'خطا در ارتباط با سرور' });
    } finally {
      setSetupLoading(false);
    }
  };

  const handleExecuteTask = async () => {
    if (!selectedProject || !taskInput.trim()) return;

    setActionLoading(true);
    setTaskResult(null);

    try {
      const result = await api.executeTask(selectedProject.project_id, taskInput, taskCategory);
      setTaskResult(result);

      // Reload project to see updates
      await selectProject(selectedProject.project_id);
    } catch (error) {
      console.error('Error executing task:', error);
      setTaskResult({ success: false, error: 'خطا در اجرای وظیفه' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleNextPhase = async () => {
    if (!selectedProject) return;

    setActionLoading(true);
    try {
      const result = await api.startNextPhase(selectedProject.project_id);
      if (result.success) {
        await selectProject(selectedProject.project_id);
        await loadProjects();
      }
    } catch (error) {
      console.error('Error starting next phase:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartAutoBuild = async (projectId?: string) => {
    const targetProjectId = projectId || selectedProject?.project_id;
    if (!targetProjectId) return;

    setActionLoading(true);
    try {
      const result = await api.startWorkflow(targetProjectId, true);
      if (result.success) {
        await loadProjects();
        if (selectedProject) {
          await selectProject(targetProjectId);
        }
        alert('ساخت خودکار شروع شد! سیستم در حال اجرای فازها و تولید فایل‌ها است.');
      } else {
        alert(`خطا: ${result.error || 'خطا در شروع ساخت خودکار'}`);
      }
    } catch (error) {
      console.error('Error starting auto build:', error);
      alert('خطا در ارتباط با سرور');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <RocketLaunchIcon className="w-7 h-7 text-primary-500" />
                مدیریت پروژه هوشمند
              </h1>
              <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
                ایجاد، مدیریت و اجرای پروژه‌ها با کمک AI
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowSmartSetup(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition shadow-lg"
              >
                <SparklesIcon className="w-5 h-5" />
                راه‌اندازی هوشمند
              </button>
            </div>
          </div>
        </div>

        <div className="flex h-[calc(100vh-130px)]">
          {/* Sidebar - Project List */}
          <div className="w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 overflow-y-auto">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <FolderIcon className="w-5 h-5" />
                پروژه‌ها ({projects.length})
              </h2>
            </div>

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full" />
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-12 px-4">
                <FolderIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">هنوز پروژه‌ای ندارید</p>
                <button
                  onClick={() => setShowSmartSetup(true)}
                  className="text-primary-500 hover:text-primary-600 font-medium"
                >
                  اولین پروژه را بسازید
                </button>
              </div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {projects.map((project) => {
                  const typeInfo = PROJECT_TYPES[project.type] || PROJECT_TYPES.custom;
                  const statusInfo = getStatusInfo(project.status);
                  const isSelected = selectedProject?.project_id === project.project_id;

                  return (
                    <div
                      key={project.project_id}
                      onClick={() => selectProject(project.project_id)}
                      className={`p-4 cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-primary-50 dark:bg-primary-900/30 border-r-4 border-primary-500'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{typeInfo.icon}</span>
                          <span className="font-medium text-gray-900 dark:text-white truncate max-w-[140px]">
                            {project.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setShowDeleteConfirm(project.project_id);
                            }}
                            className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-gray-400 hover:text-red-500"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusInfo.color}`}>
                          {statusInfo.text}
                        </span>
                        <span className="text-xs text-gray-500">{typeInfo.name}</span>
                      </div>

                      {/* Progress bar */}
                      <div className="relative pt-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-gray-500">پیشرفت</span>
                          <span className="text-xs font-semibold text-primary-500">{project.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                          <div
                            className="bg-gradient-to-r from-primary-400 to-primary-600 h-1.5 rounded-full transition-all"
                            style={{ width: `${project.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Main Content - Project Details */}
          <div className="flex-1 overflow-y-auto">
            {selectedProject ? (
              <div className="p-6">
                {/* Project Header */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-3xl">{PROJECT_TYPES[selectedProject.type]?.icon || '📦'}</span>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                          {selectedProject.name}
                        </h2>
                      </div>
                      <p className="text-gray-600 dark:text-gray-400 mb-4">
                        {selectedProject.description || selectedProject.goal || 'بدون توضیحات'}
                      </p>

                      <div className="flex flex-wrap gap-3">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm ${getStatusInfo(selectedProject.status).color}`}>
                          {getStatusInfo(selectedProject.status).text}
                        </span>
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm text-gray-600 dark:text-gray-300">
                          {PROJECT_TYPES[selectedProject.type]?.name || 'سفارشی'}
                        </span>
                        {selectedProject.complexity && (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm text-gray-600 dark:text-gray-300">
                            پیچیدگی: {selectedProject.complexity}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() => handleStartAutoBuild()}
                        disabled={actionLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition disabled:opacity-50 shadow-lg"
                      >
                        <RocketLaunchIcon className="w-5 h-5" />
                        ساخت خودکار
                      </button>
                      <button
                        onClick={() => setShowExecuteTask(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition"
                      >
                        <CpuChipIcon className="w-5 h-5" />
                        اجرای وظیفه
                      </button>
                      <button
                        onClick={handleNextPhase}
                        disabled={actionLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition disabled:opacity-50"
                      >
                        <PlayIcon className="w-5 h-5" />
                        فاز بعدی
                      </button>
                    </div>
                  </div>

                  {/* Progress Overview */}
                  <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">پیشرفت کلی</span>
                      <span className="text-lg font-bold text-primary-500">{selectedProject.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-green-400 to-green-600 h-3 rounded-full transition-all"
                        style={{ width: `${selectedProject.progress}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Phases */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <DocumentTextIcon className="w-5 h-5" />
                    فازهای پروژه
                  </h3>

                  {selectedProject.phases && selectedProject.phases.length > 0 ? (
                    <div className="space-y-4">
                      {selectedProject.phases.map((phase, index) => (
                        <div
                          key={phase.id}
                          className={`p-4 rounded-lg border-2 transition-all ${
                            phase.status === 'in_progress'
                              ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                              : phase.status === 'completed'
                              ? 'border-green-400 bg-green-50 dark:bg-green-900/20'
                              : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/30'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                                phase.status === 'completed'
                                  ? 'bg-green-500 text-white'
                                  : phase.status === 'in_progress'
                                  ? 'bg-blue-500 text-white'
                                  : 'bg-gray-300 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                              }`}>
                                {phase.status === 'completed' ? '✓' : index + 1}
                              </div>
                              <div>
                                <h4 className="font-semibold text-gray-900 dark:text-white">{phase.name}</h4>
                                {phase.description && (
                                  <p className="text-sm text-gray-500">{phase.description}</p>
                                )}
                              </div>
                            </div>
                            <span className="text-lg font-bold text-gray-700 dark:text-gray-300">
                              {phase.progress}%
                            </span>
                          </div>

                          {/* Phase steps */}
                          {phase.steps && phase.steps.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-3">
                              {phase.steps.map((step, i) => {
                                const isCompleted = phase.completed_steps?.includes(step);
                                return (
                                  <span
                                    key={i}
                                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm ${
                                      isCompleted
                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                                        : 'bg-gray-100 text-gray-600 dark:bg-gray-600 dark:text-gray-300'
                                    }`}
                                  >
                                    {isCompleted && <CheckCircleIcon className="w-4 h-4" />}
                                    {step}
                                  </span>
                                );
                              })}
                            </div>
                          )}

                          {/* Phase progress bar */}
                          <div className="mt-3">
                            <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full transition-all ${
                                  phase.status === 'completed'
                                    ? 'bg-green-500'
                                    : phase.status === 'in_progress'
                                    ? 'bg-blue-500'
                                    : 'bg-gray-400'
                                }`}
                                style={{ width: `${phase.progress}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <p>فازی تعریف نشده است</p>
                    </div>
                  )}
                </div>

                {/* Model Scores */}
                {selectedProject.model_scores && Object.keys(selectedProject.model_scores).length > 0 && (
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                      <CpuChipIcon className="w-5 h-5" />
                      عملکرد مدل‌ها
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {Object.entries(selectedProject.model_scores).map(([modelId, scores]: [string, any]) => (
                        <div key={modelId} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            {modelId}
                          </div>
                          <div className="text-2xl font-bold text-primary-500">
                            {scores.average || 0}
                          </div>
                          <div className="text-xs text-gray-500">
                            {scores.count || 0} وظیفه
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <FolderIcon className="w-24 h-24 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-xl font-medium text-gray-600 dark:text-gray-400 mb-2">
                    پروژه‌ای انتخاب نشده
                  </h3>
                  <p className="text-gray-500 mb-4">از لیست سمت چپ یک پروژه انتخاب کنید</p>
                  <button
                    onClick={() => setShowSmartSetup(true)}
                    className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600"
                  >
                    <SparklesIcon className="w-5 h-5" />
                    یا پروژه جدید بسازید
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Smart Setup Modal */}
        {showSmartSetup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <SparklesIcon className="w-6 h-6 text-purple-500" />
                    راه‌اندازی هوشمند پروژه
                  </h2>
                  <button
                    onClick={() => {
                      setShowSmartSetup(false);
                      setSetupResult(null);
                      setSmartRequest('');
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
                  فقط بگویید چه می‌خواهید بسازید. AI همه چیز را برنامه‌ریزی می‌کند.
                </p>
              </div>

              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {!setupResult ? (
                  <div className="space-y-4">
                    <textarea
                      value={smartRequest}
                      onChange={(e) => setSmartRequest(e.target.value)}
                      placeholder="مثال: یک سیستم مدیریت فروشگاه آنلاین با Next.js و FastAPI بساز که قابلیت پرداخت آنلاین، مدیریت موجودی و گزارش‌گیری داشته باشه..."
                      className="w-full h-40 p-4 border rounded-xl dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                    />

                    <div className="bg-purple-50 dark:bg-purple-900/20 rounded-xl p-4">
                      <h4 className="font-medium text-purple-800 dark:text-purple-300 mb-2">AI این کارها را انجام می‌دهد:</h4>
                      <ul className="text-sm text-purple-700 dark:text-purple-400 space-y-1">
                        <li>✓ تحلیل درخواست و استخراج نیازمندی‌ها</li>
                        <li>✓ انتخاب تکنولوژی‌های مناسب</li>
                        <li>✓ تعریف فازها و گام‌های اجرایی</li>
                        <li>✓ تخمین فایل‌های مورد نیاز</li>
                        <li>✓ شناسایی ریسک‌ها</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {setupResult.success && setupResult.analysis ? (
                      <>
                        <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-4">
                          <div className="flex items-center gap-2 text-green-700 dark:text-green-300 mb-2">
                            <CheckCircleIcon className="w-5 h-5" />
                            <span className="font-medium">پروژه با موفقیت ایجاد شد!</span>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <h4 className="font-medium mb-2">{setupResult.analysis.project_name}</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">{setupResult.analysis.description}</p>
                          </div>

                          {setupResult.analysis.technologies && (
                            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                              <h4 className="font-medium mb-2">تکنولوژی‌ها</h4>
                              <div className="flex flex-wrap gap-2">
                                {setupResult.analysis.technologies.map((tech, i) => (
                                  <span key={i} className="px-3 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full text-sm">
                                    {tech}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {setupResult.analysis.phases && (
                            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                              <h4 className="font-medium mb-2">فازها ({setupResult.analysis.phases.length})</h4>
                              <div className="space-y-2">
                                {setupResult.analysis.phases.map((phase: any, i: number) => (
                                  <div key={i} className="flex items-center gap-2 text-sm">
                                    <span className="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400 flex items-center justify-center text-xs font-medium">
                                      {i + 1}
                                    </span>
                                    <span>{phase.name}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-4">
                        <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                          <ExclamationTriangleIcon className="w-5 h-5" />
                          <span>{setupResult.error || 'خطا در ایجاد پروژه'}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                {!setupResult ? (
                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowSmartSetup(false)}
                      className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      انصراف
                    </button>
                    <button
                      onClick={handleSmartSetup}
                      disabled={!smartRequest.trim() || setupLoading}
                      className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {setupLoading ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          در حال تحلیل...
                        </>
                      ) : (
                        <>
                          <SparklesIcon className="w-5 h-5" />
                          شروع راه‌اندازی
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        setShowSmartSetup(false);
                        setSetupResult(null);
                        setSmartRequest('');
                        if (setupResult?.project_id) {
                          selectProject(setupResult.project_id);
                        }
                      }}
                      className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      بستن
                    </button>
                    {setupResult?.success && setupResult?.project_id && (
                      <button
                        onClick={() => {
                          if (setupResult.project_id) {
                            handleStartAutoBuild(setupResult.project_id);
                            setShowSmartSetup(false);
                            setSetupResult(null);
                            setSmartRequest('');
                            selectProject(setupResult.project_id);
                          }
                        }}
                        disabled={actionLoading}
                        className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        <RocketLaunchIcon className="w-5 h-5" />
                        شروع ساخت خودکار
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Execute Task Modal */}
        {showExecuteTask && selectedProject && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <CpuChipIcon className="w-6 h-6 text-primary-500" />
                    اجرای وظیفه با AI
                  </h2>
                  <button
                    onClick={() => {
                      setShowExecuteTask(false);
                      setTaskResult(null);
                      setTaskInput('');
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div className="p-6 overflow-y-auto max-h-[60vh]">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">نوع وظیفه</label>
                    <select
                      value={taskCategory}
                      onChange={(e) => setTaskCategory(e.target.value)}
                      className="w-full p-3 border rounded-xl dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value="code_generation">تولید کد</option>
                      <option value="analysis">تحلیل</option>
                      <option value="debugging">رفع باگ</option>
                      <option value="documentation">مستندسازی</option>
                      <option value="research">تحقیق</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">توضیح وظیفه</label>
                    <textarea
                      value={taskInput}
                      onChange={(e) => setTaskInput(e.target.value)}
                      placeholder="چه کاری می‌خواهید انجام شود؟"
                      className="w-full h-32 p-4 border rounded-xl dark:bg-gray-700 dark:border-gray-600 resize-none"
                    />
                  </div>

                  {taskResult && (
                    <div className={`rounded-xl p-4 ${taskResult.success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                      <h4 className={`font-medium mb-2 ${taskResult.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                        {taskResult.success ? 'نتیجه اجرا' : 'خطا'}
                      </h4>
                      {taskResult.success ? (
                        <div className="space-y-2 text-sm">
                          {taskResult.evaluation && (
                            <div className="flex items-center gap-2">
                              <span>امتیاز:</span>
                              <span className="font-bold text-green-600">{taskResult.evaluation.score}/100</span>
                            </div>
                          )}
                          <div className="bg-white dark:bg-gray-800 rounded p-3 max-h-40 overflow-y-auto">
                            <pre className="whitespace-pre-wrap text-xs">{taskResult.output?.slice(0, 500)}...</pre>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-red-600 dark:text-red-400">{taskResult.error}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowExecuteTask(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg"
                  >
                    بستن
                  </button>
                  <button
                    onClick={handleExecuteTask}
                    disabled={!taskInput.trim() || actionLoading}
                    className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {actionLoading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        در حال اجرا...
                      </>
                    ) : (
                      <>
                        <PlayIcon className="w-5 h-5" />
                        اجرا
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-full max-w-md">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                  <TrashIcon className="w-8 h-8 text-red-500" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">حذف پروژه</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  آیا از حذف این پروژه اطمینان دارید؟ این عمل قابل بازگشت نیست.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowDeleteConfirm(null)}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg"
                  >
                    انصراف
                  </button>
                  <button
                    onClick={() => showDeleteConfirm && deleteProject(showDeleteConfirm)}
                    disabled={actionLoading}
                    className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50"
                  >
                    {actionLoading ? 'در حال حذف...' : 'حذف'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
