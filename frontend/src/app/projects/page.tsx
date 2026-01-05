'use client';

import { useState, useEffect } from 'react';
// Layout is already provided by app/layout.tsx - DO NOT use here
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
  ArrowUpTrayIcon,
  CodeBracketIcon,
  DocumentArrowUpIcon,
  ArchiveBoxIcon,
  ClipboardDocumentIcon,
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

  async startWorkflow(
    projectId: string,
    autoExecute: boolean = true,
    useCompetition: boolean = true,
    numModels: number = 3
  ): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/start-workflow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        auto_execute: autoExecute,
        use_competition: useCompetition,
        num_models: numModels
      }),
    });
    return res.json();
  },

  async getWorkflowStatus(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/workflow-status/${projectId}`);
    return res.json();
  },

  async getGeneratedFiles(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/generated-files/${projectId}`);
    return res.json();
  },

  async getFileContent(projectId: string, filePath: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/file-content/${projectId}/${encodeURIComponent(filePath)}`);
    return res.json();
  },

  async getAvailableModels(): Promise<any[]> {
    const res = await fetch(`${getApiUrl()}/api/models/available`);
    const data = await res.json();
    return data || [];
  },

  async smartImportFile(projectId: string, file: File, userPrompt?: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (userPrompt) {
      formData.append('user_prompt', userPrompt);
    }
    formData.append('auto_apply', 'true');

    const res = await fetch(`${getApiUrl()}/api/orchestrator/smart-import/${projectId}`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async smartImportText(projectId: string, content: string, fileName: string, userPrompt?: string): Promise<any> {
    const formData = new FormData();
    formData.append('content', content);
    formData.append('file_name', fileName);
    if (userPrompt) {
      formData.append('user_prompt', userPrompt);
    }
    formData.append('auto_apply', 'true');

    const res = await fetch(`${getApiUrl()}/api/orchestrator/smart-import-text/${projectId}`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async syncProject(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/sync-project/${projectId}`, {
      method: 'POST',
    });
    return res.json();
  },

  async getGitHubStatus(): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/github-status`);
    return res.json();
  },

  async reloadFromGitHub(): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/reload-from-github`, {
      method: 'POST',
    });
    return res.json();
  },

  async getProjectState(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/project-state/${projectId}`);
    return res.json();
  },

  async getDeploymentGuide(projectId: string): Promise<any> {
    const res = await fetch(`${getApiUrl()}/api/orchestrator/deployment-guide/${projectId}`);
    return res.json();
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

  // Auto-build progress state
  const [showBuildProgress, setShowBuildProgress] = useState(false);
  const [buildProgress, setBuildProgress] = useState<{
    status: string;
    progress: number;
    currentStep: string;
    currentFile: string;
    currentFileIndex: number;
    totalFiles: number;
    results: any[];
  } | null>(null);
  const [buildingProjectId, setBuildingProjectId] = useState<string | null>(null);

  // File viewer state
  const [viewingFile, setViewingFile] = useState<{
    name: string;
    content: string;
    score: number;
  } | null>(null);

  // Generated files state
  const [generatedFiles, setGeneratedFiles] = useState<any[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  // Smart import state
  const [showSmartImport, setShowSmartImport] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importCode, setImportCode] = useState('');
  const [importFileName, setImportFileName] = useState('');
  const [importPrompt, setImportPrompt] = useState('');
  const [importMode, setImportMode] = useState<'file' | 'code'>('code');
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [syncLoading, setSyncLoading] = useState(false);

  // 🆕 Project state & next steps
  const [projectState, setProjectState] = useState<any>(null);
  const [loadingState, setLoadingState] = useState(false);
  const [showDeployGuide, setShowDeployGuide] = useState(false);
  const [deployGuide, setDeployGuide] = useState<any>(null);

  // Load data
  useEffect(() => {
    loadProjects();
    loadModels();
  }, []);

  // Polling for build progress
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (buildingProjectId && showBuildProgress) {
      interval = setInterval(async () => {
        try {
          const status = await api.getWorkflowStatus(buildingProjectId);
          if (status.success) {
            setBuildProgress({
              status: status.status,
              progress: status.progress || 0,
              currentStep: status.current_step || '',
              currentFile: status.current_file || '',
              currentFileIndex: status.current_file_index || 0,
              totalFiles: status.total_files || 0,
              results: status.results || [],
            });

            // Stop polling when completed
            if (status.status === 'completed' || status.status === 'failed') {
              if (interval) clearInterval(interval);
              await loadProjects();
              if (selectedProject) {
                await selectProject(buildingProjectId);
              }
            }
          }
        } catch (error) {
          console.error('Error polling build status:', error);
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [buildingProjectId, showBuildProgress]);

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
    setGeneratedFiles([]); // Reset files when switching projects
    setProjectState(null); // Reset project state
    try {
      const project = await api.getProject(id);
      setSelectedProject(project);
      // Load generated files for this project
      loadGeneratedFiles(id);
      // 🆕 Load project state with next steps
      loadProjectState(id);
    } catch (error) {
      console.error('Error loading project:', error);
    } finally {
      setActionLoading(false);
    }
  };

  // 🆕 Load project state with next steps
  const loadProjectState = async (projectId: string) => {
    setLoadingState(true);
    try {
      const state = await api.getProjectState(projectId);
      setProjectState(state);
    } catch (error) {
      console.error('Error loading project state:', error);
    } finally {
      setLoadingState(false);
    }
  };

  // 🆕 Load deployment guide
  const loadDeployGuide = async (projectId: string) => {
    try {
      const guide = await api.getDeploymentGuide(projectId);
      if (guide.success) {
        setDeployGuide(guide.guide);
        setShowDeployGuide(true);
      }
    } catch (error) {
      console.error('Error loading deployment guide:', error);
    }
  };

  // 🆕 Handle next step action
  const handleNextStep = async (step: any) => {
    if (!selectedProject) return;

    switch (step.action) {
      case 'build':
        handleStartAutoBuild(selectedProject.project_id);
        break;
      case 'next_phase':
        handleNextPhase(selectedProject.project_id);
        break;
      case 'deploy':
        loadDeployGuide(selectedProject.project_id);
        break;
      case 'review':
        // Scroll to files section
        break;
      case 'download':
        // Open GitHub repo
        break;
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

  const handleNextPhase = async (projectId?: string) => {
    const id = projectId || selectedProject?.project_id;
    if (!id) return;

    setActionLoading(true);
    try {
      const result = await api.startNextPhase(id);
      if (result.success) {
        await selectProject(id);
        await loadProjects();
      }
    } catch (error) {
      console.error('Error starting next phase:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const loadGeneratedFiles = async (projectId: string) => {
    setLoadingFiles(true);
    try {
      const result = await api.getGeneratedFiles(projectId);
      if (result.success && result.files) {
        setGeneratedFiles(result.files);
      } else {
        setGeneratedFiles([]);
      }
    } catch (error) {
      console.error('Error loading generated files:', error);
      setGeneratedFiles([]);
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleStartAutoBuild = async (projectId?: string) => {
    const targetProjectId = projectId || selectedProject?.project_id;
    if (!targetProjectId) return;

    // Show progress modal
    setBuildingProjectId(targetProjectId);
    setBuildProgress({
      status: 'starting',
      progress: 0,
      currentStep: 'شروع فرآیند...',
      currentFile: '',
      currentFileIndex: 0,
      totalFiles: 0,
      results: [],
    });
    setShowBuildProgress(true);

    try {
      // Start the build process (this runs async on the server)
      const result = await api.startWorkflow(targetProjectId, true);
      if (!result.success) {
        setBuildProgress(prev => prev ? {
          ...prev,
          status: 'failed',
          currentStep: result.error || 'خطا در شروع ساخت خودکار'
        } : null);
      }
    } catch (error) {
      console.error('Error starting auto build:', error);
      setBuildProgress(prev => prev ? {
        ...prev,
        status: 'failed',
        currentStep: 'خطا در ارتباط با سرور'
      } : null);
    }
  };

  const handleSmartImport = async () => {
    if (!selectedProject) return;

    setImportLoading(true);
    setImportResult(null);

    try {
      let result;
      if (importMode === 'file' && importFile) {
        result = await api.smartImportFile(
          selectedProject.project_id,
          importFile,
          importPrompt || undefined
        );
      } else if (importMode === 'code' && importCode.trim()) {
        const fileName = importFileName.trim() || 'imported_code.txt';
        result = await api.smartImportText(
          selectedProject.project_id,
          importCode,
          fileName,
          importPrompt || undefined
        );
      } else {
        setImportLoading(false);
        return;
      }

      setImportResult(result);

      // اگه موفق بود، لیست فایل‌ها رو رفرش کن
      if (result.success && result.applied?.success) {
        loadGeneratedFiles(selectedProject.project_id);
      }
    } catch (error) {
      console.error('Error in smart import:', error);
      setImportResult({ success: false, error: 'خطا در ارتباط با سرور' });
    } finally {
      setImportLoading(false);
    }
  };

  const handleSyncProject = async () => {
    if (!selectedProject) return;

    setSyncLoading(true);
    try {
      const result = await api.syncProject(selectedProject.project_id);
      if (result.success) {
        loadGeneratedFiles(selectedProject.project_id);
        alert(`سینک انجام شد! ${result.new_files_found || 0} فایل جدید پیدا شد.`);
      }
    } catch (error) {
      console.error('Error syncing project:', error);
    } finally {
      setSyncLoading(false);
    }
  };

  const handleCheckGitHubStatus = async () => {
    try {
      const status = await api.getGitHubStatus();
      let message = `🔗 وضعیت GitHub:\n\n`;
      message += `Token تنظیم شده: ${status.token_set ? '✅ بله' : '❌ خیر'}\n`;
      message += `Owner: ${status.owner}\n`;
      message += `Repo: ${status.repo}\n`;
      message += `Branch: ${status.branch}\n`;
      message += `متصل: ${status.connected ? '✅ بله' : '❌ خیر'}\n`;

      if (status.connection_error) {
        message += `\n⚠️ خطا: ${status.connection_error}\n`;
      }

      if (status.project_folders && status.project_folders.length > 0) {
        message += `\n📁 پروژه‌ها در GitHub: ${status.project_folders.length}\n`;
        message += status.project_folders.join(', ');
      }

      alert(message);
    } catch (error) {
      alert('خطا در بررسی وضعیت GitHub');
      console.error(error);
    }
  };

  const handleReloadFromGitHub = async () => {
    try {
      const result = await api.reloadFromGitHub();
      if (result.success) {
        alert(`✅ بارگذاری موفق!\n\nپروژه‌ها: ${result.projects_loaded}\nWorkflows: ${result.workflows_loaded}`);
        loadProjects(); // Refresh the list
      } else {
        alert('خطا در بارگذاری از GitHub');
      }
    } catch (error) {
      alert('خطا در ارتباط با سرور');
      console.error(error);
    }
  };

  return (
    <>
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
                onClick={handleCheckGitHubStatus}
                className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition text-sm"
                title="بررسی وضعیت GitHub"
              >
                <Cog6ToothIcon className="w-4 h-4" />
                وضعیت GitHub
              </button>
              <button
                onClick={handleReloadFromGitHub}
                className="flex items-center gap-2 px-3 py-2 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-700 transition text-sm"
                title="بارگذاری مجدد از GitHub"
              >
                <ArrowPathIcon className="w-4 h-4" />
                بارگذاری از GitHub
              </button>
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

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setShowSmartImport(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg hover:from-cyan-600 hover:to-blue-600 transition shadow-lg"
                      >
                        <ArrowUpTrayIcon className="w-5 h-5" />
                        وارد کردن کد
                      </button>
                      <button
                        onClick={() => handleStartAutoBuild()}
                        disabled={actionLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition disabled:opacity-50 shadow-lg"
                      >
                        <RocketLaunchIcon className="w-5 h-5" />
                        ساخت خودکار
                      </button>
                      <button
                        onClick={handleSyncProject}
                        disabled={syncLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-teal-500 to-emerald-500 text-white rounded-lg hover:from-teal-600 hover:to-emerald-600 transition disabled:opacity-50"
                      >
                        <ArrowPathIcon className={`w-5 h-5 ${syncLoading ? 'animate-spin' : ''}`} />
                        سینک GitHub
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

                {/* 🆕 Next Steps Section */}
                {projectState?.next_steps && projectState.next_steps.length > 0 && (
                  <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl shadow-lg p-6 mt-6 text-white">
                    <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
                      <RocketLaunchIcon className="w-6 h-6" />
                      قدم بعدی چیه؟
                    </h3>
                    <div className="space-y-3">
                      {projectState.next_steps.map((step: any, idx: number) => (
                        <div
                          key={idx}
                          className="bg-white/10 backdrop-blur rounded-lg p-4 flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center font-bold">
                              {step.step}
                            </div>
                            <div>
                              <div className="font-medium">{step.title}</div>
                              <div className="text-sm text-white/80">{step.description}</div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleNextStep(step)}
                            className="px-4 py-2 bg-white text-indigo-600 font-medium rounded-lg hover:bg-white/90 transition flex items-center gap-2"
                          >
                            {step.action === 'build' && <SparklesIcon className="w-4 h-4" />}
                            {step.action === 'next_phase' && <ChevronRightIcon className="w-4 h-4" />}
                            {step.action === 'deploy' && <RocketLaunchIcon className="w-4 h-4" />}
                            {step.button}
                          </button>
                        </div>
                      ))}
                    </div>

                    {/* Progress indicator */}
                    {projectState.overall_progress !== undefined && (
                      <div className="mt-4 pt-4 border-t border-white/20">
                        <div className="flex justify-between text-sm mb-2">
                          <span>پیشرفت کلی</span>
                          <span>{projectState.overall_progress}%</span>
                        </div>
                        <div className="h-2 bg-white/20 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-white transition-all duration-500"
                            style={{ width: `${projectState.overall_progress}%` }}
                          />
                        </div>
                        {projectState.project_completed && (
                          <div className="mt-2 text-center text-white/90 text-sm">
                            پروژه کامل شده! آماده استقرار است.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Loading state for project state */}
                {loadingState && (
                  <div className="bg-gray-100 dark:bg-gray-800 rounded-xl p-6 mt-6 animate-pulse">
                    <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-4"></div>
                    <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded mb-3"></div>
                    <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  </div>
                )}

                {/* Generated Files Section */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mt-6">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                      <DocumentTextIcon className="w-5 h-5 text-purple-500" />
                      فایل‌های تولید شده
                      {generatedFiles.length > 0 && (
                        <span className="text-sm font-normal bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded-full">
                          {generatedFiles.length} فایل
                        </span>
                      )}
                    </h3>
                    <button
                      onClick={() => loadGeneratedFiles(selectedProject.project_id)}
                      disabled={loadingFiles}
                      className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-700 transition disabled:opacity-50 text-sm"
                    >
                      <ArrowPathIcon className={`w-4 h-4 ${loadingFiles ? 'animate-spin' : ''}`} />
                      {loadingFiles ? 'در حال بارگذاری...' : 'بارگذاری از GitHub'}
                    </button>
                  </div>

                  {loadingFiles ? (
                    <div className="flex justify-center py-8">
                      <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
                    </div>
                  ) : generatedFiles.length > 0 ? (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {generatedFiles.map((file, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-600 transition"
                        >
                          <div className="flex items-center gap-3">
                            <DocumentTextIcon className="w-5 h-5 text-green-500" />
                            <div>
                              <span className="font-mono text-sm text-gray-900 dark:text-white">
                                {file.path || file.file}
                              </span>
                              {file.winner_model && (
                                <span className="ml-2 text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded-full">
                                  🏆 {file.winner_model.split('-')[0]}
                                </span>
                              )}
                              {file.score && (
                                <span className="ml-2 text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full">
                                  امتیاز: {file.score}
                                </span>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={async () => {
                              const fileData = await api.getFileContent(selectedProject.project_id, file.path || file.file);
                              if (fileData.success) {
                                setViewingFile({
                                  name: file.path || file.file,
                                  content: fileData.content,
                                  score: file.score || fileData.score || 0
                                });
                              }
                            }}
                            className="flex items-center gap-1 px-3 py-1.5 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition text-sm"
                          >
                            <EyeIcon className="w-4 h-4" />
                            مشاهده کد
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <FolderIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500 mb-2">فایلی تولید نشده است</p>
                      <p className="text-sm text-gray-400">
                        از دکمه "ساخت خودکار" برای تولید فایل‌های پروژه استفاده کنید
                        <br />
                        یا دکمه "بارگذاری از GitHub" را بزنید
                      </p>
                    </div>
                  )}
                </div>
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

        {/* File Viewer Modal */}
        {viewingFile && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[60] p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <DocumentTextIcon className="w-6 h-6 text-purple-500" />
                  <h3 className="font-bold text-gray-900 dark:text-white font-mono">{viewingFile.name}</h3>
                  <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300 rounded-full">
                    امتیاز: {viewingFile.score}
                  </span>
                </div>
                <button
                  onClick={() => setViewingFile(null)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
              <div className="overflow-auto max-h-[70vh] bg-gray-900">
                <pre className="p-4 text-sm text-gray-100 font-mono whitespace-pre-wrap">
                  <code>{viewingFile.content}</code>
                </pre>
              </div>
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex gap-3">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(viewingFile.content);
                    alert('کد کپی شد!');
                  }}
                  className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
                >
                  کپی کد
                </button>
                <button
                  onClick={() => setViewingFile(null)}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg"
                >
                  بستن
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Build Progress Modal */}
        {showBuildProgress && buildProgress && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <RocketLaunchIcon className="w-6 h-6 text-purple-500" />
                    ساخت خودکار پروژه
                  </h2>
                  {buildProgress.status === 'completed' || buildProgress.status === 'failed' ? (
                    <button
                      onClick={() => {
                        setShowBuildProgress(false);
                        // Refresh files list and project state after closing
                        if (buildingProjectId) {
                          loadGeneratedFiles(buildingProjectId);
                          loadProjectState(buildingProjectId); // 🆕 Refresh next steps
                        }
                        setBuildingProjectId(null);
                        setBuildProgress(null);
                      }}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  ) : null}
                </div>
              </div>

              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {/* Status */}
                <div className={`rounded-xl p-4 mb-4 ${
                  buildProgress.status === 'completed'
                    ? 'bg-green-50 dark:bg-green-900/20'
                    : buildProgress.status === 'failed'
                    ? 'bg-red-50 dark:bg-red-900/20'
                    : 'bg-blue-50 dark:bg-blue-900/20'
                }`}>
                  <div className="flex items-center gap-3">
                    {buildProgress.status === 'completed' ? (
                      <CheckCircleIcon className="w-8 h-8 text-green-500" />
                    ) : buildProgress.status === 'failed' ? (
                      <ExclamationTriangleIcon className="w-8 h-8 text-red-500" />
                    ) : (
                      <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    )}
                    <div>
                      <h3 className={`font-bold ${
                        buildProgress.status === 'completed'
                          ? 'text-green-700 dark:text-green-300'
                          : buildProgress.status === 'failed'
                          ? 'text-red-700 dark:text-red-300'
                          : 'text-blue-700 dark:text-blue-300'
                      }`}>
                        {buildProgress.status === 'completed'
                          ? 'ساخت کامل شد!'
                          : buildProgress.status === 'failed'
                          ? 'خطا در ساخت'
                          : buildProgress.status === 'building'
                          ? 'در حال ساخت...'
                          : 'شروع فرآیند...'}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {buildProgress.currentStep || buildProgress.currentFile || 'در انتظار...'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">پیشرفت</span>
                    <span className="text-sm font-bold text-primary-500">{buildProgress.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full transition-all duration-500 ${
                        buildProgress.status === 'completed'
                          ? 'bg-gradient-to-r from-green-400 to-green-600'
                          : buildProgress.status === 'failed'
                          ? 'bg-gradient-to-r from-red-400 to-red-600'
                          : 'bg-gradient-to-r from-blue-400 to-purple-600'
                      }`}
                      style={{ width: `${buildProgress.progress}%` }}
                    />
                  </div>
                  {buildProgress.totalFiles > 0 && (
                    <p className="text-sm text-gray-500 mt-1">
                      فایل {buildProgress.currentFileIndex} از {buildProgress.totalFiles}
                    </p>
                  )}
                </div>

                {/* Current file */}
                {buildProgress.currentFile && buildProgress.status !== 'completed' && (
                  <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <div className="flex items-center gap-2">
                      <DocumentTextIcon className="w-5 h-5 text-blue-500 animate-pulse" />
                      <span className="text-sm font-medium">در حال تولید:</span>
                      <span className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                        {buildProgress.currentFile}
                      </span>
                    </div>
                  </div>
                )}

                {/* Results */}
                {buildProgress.results && buildProgress.results.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">فایل‌های تولید شده:</h4>
                    <div className="max-h-48 overflow-y-auto space-y-2">
                      {buildProgress.results.map((result, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-lg flex items-center gap-2 ${
                            result.status === 'created'
                              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                          }`}
                        >
                          {result.status === 'created' ? (
                            <CheckCircleIcon className="w-5 h-5 text-green-500 flex-shrink-0" />
                          ) : (
                            <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0" />
                          )}
                          <span className="font-mono text-sm flex-1">{result.file}</span>
                          {result.winner_model && (
                            <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300 rounded-full">
                              🏆 {result.winner_model.split('-')[0]}
                            </span>
                          )}
                          {result.score && (
                            <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300 rounded-full">
                              امتیاز: {result.score}
                            </span>
                          )}
                          {result.competition && result.competition.participants > 1 && (
                            <span className="text-xs px-2 py-0.5 bg-yellow-100 dark:bg-yellow-800 text-yellow-700 dark:text-yellow-300 rounded-full">
                              🏁 {result.competition.successful}/{result.competition.participants}
                            </span>
                          )}
                          {result.github_saved && (
                            <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded-full">
                              GitHub ✓
                            </span>
                          )}
                          {result.status === 'created' && buildingProjectId && (
                            <button
                              onClick={async () => {
                                const fileData = await api.getFileContent(buildingProjectId, result.file);
                                if (fileData.success) {
                                  setViewingFile({
                                    name: result.file,
                                    content: fileData.content,
                                    score: fileData.score
                                  });
                                }
                              }}
                              className="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-700"
                            >
                              مشاهده کد
                            </button>
                          )}
                          {result.error && (
                            <span className="text-xs text-red-600 dark:text-red-400 max-w-[150px] truncate">
                              {result.error}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              {(buildProgress.status === 'completed' || buildProgress.status === 'failed') && (
                <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        setShowBuildProgress(false);
                        // Refresh files list and project state after closing
                        if (buildingProjectId) {
                          loadGeneratedFiles(buildingProjectId);
                          loadProjectState(buildingProjectId); // 🆕 Refresh next steps
                        }
                        setBuildingProjectId(null);
                        setBuildProgress(null);
                      }}
                      className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
                    >
                      بستن
                    </button>
                    {buildProgress.status === 'failed' && (
                      <button
                        onClick={() => {
                          if (buildingProjectId) {
                            setBuildProgress({
                              status: 'starting',
                              progress: 0,
                              currentStep: 'شروع مجدد...',
                              currentFile: '',
                              currentFileIndex: 0,
                              totalFiles: 0,
                              results: [],
                            });
                            api.startWorkflow(buildingProjectId, true);
                          }
                        }}
                        className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                      >
                        تلاش مجدد
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Smart Import Modal */}
        {showSmartImport && selectedProject && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <ArrowUpTrayIcon className="w-6 h-6 text-cyan-500" />
                    وارد کردن هوشمند کد/فایل
                  </h2>
                  <button
                    onClick={() => {
                      setShowSmartImport(false);
                      setImportResult(null);
                      setImportCode('');
                      setImportFileName('');
                      setImportPrompt('');
                      setImportFile(null);
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
                  کد یا فایل را وارد کنید. مدل‌های نخبه AI تحلیل می‌کنند، ارتباط با پروژه را تشخیص می‌دهند و به پوشه مناسب منتقل می‌کنند.
                </p>
              </div>

              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {!importResult ? (
                  <div className="space-y-4">
                    {/* Mode Selector */}
                    <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-700 rounded-lg">
                      <button
                        onClick={() => setImportMode('code')}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition ${
                          importMode === 'code'
                            ? 'bg-white dark:bg-gray-600 shadow text-cyan-600 dark:text-cyan-400'
                            : 'text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        <CodeBracketIcon className="w-5 h-5" />
                        پیست کردن کد
                      </button>
                      <button
                        onClick={() => setImportMode('file')}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition ${
                          importMode === 'file'
                            ? 'bg-white dark:bg-gray-600 shadow text-cyan-600 dark:text-cyan-400'
                            : 'text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        <DocumentArrowUpIcon className="w-5 h-5" />
                        آپلود فایل
                      </button>
                    </div>

                    {importMode === 'code' ? (
                      <>
                        {/* File Name */}
                        <div>
                          <label className="block text-sm font-medium mb-2">نام فایل (اختیاری)</label>
                          <input
                            type="text"
                            value={importFileName}
                            onChange={(e) => setImportFileName(e.target.value)}
                            placeholder="مثال: auth_service.py یا Button.tsx"
                            className="w-full p-3 border rounded-xl dark:bg-gray-700 dark:border-gray-600 font-mono text-sm"
                          />
                        </div>

                        {/* Code Input */}
                        <div>
                          <label className="block text-sm font-medium mb-2">کد یا محتوا</label>
                          <textarea
                            value={importCode}
                            onChange={(e) => setImportCode(e.target.value)}
                            placeholder="کد خود را اینجا پیست کنید..."
                            className="w-full h-64 p-4 border rounded-xl dark:bg-gray-700 dark:border-gray-600 font-mono text-sm resize-none"
                            dir="ltr"
                          />
                        </div>
                      </>
                    ) : (
                      <div>
                        <label className="block text-sm font-medium mb-2">انتخاب فایل</label>
                        <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 text-center">
                          <input
                            type="file"
                            onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                            className="hidden"
                            id="import-file"
                          />
                          <label htmlFor="import-file" className="cursor-pointer">
                            <DocumentArrowUpIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-gray-600 dark:text-gray-400 mb-2">
                              فایل را بکشید و رها کنید یا کلیک کنید
                            </p>
                            {importFile && (
                              <div className="mt-4 p-3 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg inline-flex items-center gap-2">
                                <DocumentTextIcon className="w-5 h-5 text-cyan-500" />
                                <span className="font-mono text-sm">{importFile.name}</span>
                                <span className="text-xs text-gray-500">
                                  ({(importFile.size / 1024).toFixed(1)} KB)
                                </span>
                              </div>
                            )}
                          </label>
                        </div>
                      </div>
                    )}

                    {/* User Prompt */}
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        توضیحات اضافی (اختیاری)
                      </label>
                      <textarea
                        value={importPrompt}
                        onChange={(e) => setImportPrompt(e.target.value)}
                        placeholder="اگر نکته خاصی هست بنویسید... مثلا: این کد باید جایگزین فایل قبلی شود یا این کامپوننت برای صفحه لاگین است..."
                        className="w-full h-24 p-4 border rounded-xl dark:bg-gray-700 dark:border-gray-600 resize-none"
                      />
                    </div>

                    {/* Info Box */}
                    <div className="bg-cyan-50 dark:bg-cyan-900/20 rounded-xl p-4">
                      <h4 className="font-medium text-cyan-800 dark:text-cyan-300 mb-2 flex items-center gap-2">
                        <SparklesIcon className="w-5 h-5" />
                        مدل‌های نخبه AI این کارها را انجام می‌دهند:
                      </h4>
                      <ul className="text-sm text-cyan-700 dark:text-cyan-400 space-y-1">
                        <li>✓ تشخیص نوع فایل و زبان برنامه‌نویسی</li>
                        <li>✓ بررسی ارتباط با فازهای پروژه</li>
                        <li>✓ اعتبارسنجی کیفیت کد</li>
                        <li>✓ اصلاح خودکار در صورت نیاز</li>
                        <li>✓ انتقال به پوشه مناسب</li>
                        <li>✓ بروزرسانی پیشرفت پروژه</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Result Display */}
                    {importResult.success ? (
                      <>
                        <div className={`rounded-xl p-4 ${
                          importResult.analysis?.decision === 'integrate' || importResult.analysis?.decision === 'modify_and_integrate'
                            ? 'bg-green-50 dark:bg-green-900/20'
                            : importResult.analysis?.decision === 'archive'
                            ? 'bg-yellow-50 dark:bg-yellow-900/20'
                            : 'bg-blue-50 dark:bg-blue-900/20'
                        }`}>
                          <div className="flex items-center gap-3 mb-3">
                            {importResult.analysis?.decision === 'integrate' || importResult.analysis?.decision === 'modify_and_integrate' ? (
                              <CheckCircleIcon className="w-8 h-8 text-green-500" />
                            ) : importResult.analysis?.decision === 'archive' ? (
                              <ArchiveBoxIcon className="w-8 h-8 text-yellow-500" />
                            ) : (
                              <ExclamationTriangleIcon className="w-8 h-8 text-blue-500" />
                            )}
                            <div>
                              <h3 className="font-bold text-lg">
                                {importResult.analysis?.decision === 'integrate' && 'ادغام در پروژه'}
                                {importResult.analysis?.decision === 'modify_and_integrate' && 'اصلاح و ادغام'}
                                {importResult.analysis?.decision === 'archive' && 'بایگانی شد'}
                                {importResult.analysis?.decision === 'needs_review' && 'نیاز به بررسی'}
                              </h3>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                امتیاز ارتباط: {importResult.analysis?.relevance_score}%
                              </p>
                            </div>
                          </div>

                          {importResult.analysis?.analysis_summary && (
                            <p className="text-sm mb-3">{importResult.analysis.analysis_summary}</p>
                          )}

                          {importResult.analysis?.target_phase && (
                            <div className="flex items-center gap-2 text-sm">
                              <span className="font-medium">فاز مرتبط:</span>
                              <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded-full">
                                {importResult.analysis.target_phase}
                              </span>
                            </div>
                          )}

                          {importResult.applied?.saved_path && (
                            <div className="mt-3 p-2 bg-white dark:bg-gray-800 rounded-lg flex items-center gap-2">
                              <FolderIcon className="w-5 h-5 text-green-500" />
                              <span className="font-mono text-sm">{importResult.applied.saved_path}</span>
                            </div>
                          )}
                        </div>

                        {/* Model Votes */}
                        {importResult.analysis?.model_votes && Object.keys(importResult.analysis.model_votes).length > 0 && (
                          <div className="bg-gray-50 dark:bg-gray-700 rounded-xl p-4">
                            <h4 className="font-medium mb-3 flex items-center gap-2">
                              <CpuChipIcon className="w-5 h-5" />
                              نظر مدل‌ها
                            </h4>
                            <div className="space-y-2">
                              {Object.entries(importResult.analysis.model_votes).map(([modelId, vote]: [string, any]) => (
                                <div key={modelId} className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded-lg">
                                  <span className="text-sm font-medium">{modelId.split('-')[0]}</span>
                                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                                    vote.decision === 'integrate' || vote.decision === 'modify_and_integrate'
                                      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                                      : vote.decision === 'archive'
                                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                                      : 'bg-gray-100 text-gray-700 dark:bg-gray-600 dark:text-gray-300'
                                  }`}>
                                    {vote.decision} ({vote.relevance_score}%)
                                  </span>
                                </div>
                              ))}
                            </div>
                            {importResult.analysis.consensus && (
                              <div className="mt-2 text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                                <CheckCircleIcon className="w-4 h-4" />
                                مدل‌ها به اجماع رسیدند
                              </div>
                            )}
                          </div>
                        )}

                        {/* Modifications */}
                        {importResult.analysis?.modifications_needed?.length > 0 && (
                          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
                            <h4 className="font-medium mb-2 text-blue-800 dark:text-blue-300">اصلاحات انجام شده:</h4>
                            <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1">
                              {importResult.analysis.modifications_needed.map((mod: string, i: number) => (
                                <li key={i}>• {mod}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Warnings */}
                        {importResult.analysis?.warnings?.length > 0 && (
                          <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-xl p-4">
                            <h4 className="font-medium mb-2 text-yellow-800 dark:text-yellow-300">هشدارها:</h4>
                            <ul className="text-sm text-yellow-700 dark:text-yellow-400 space-y-1">
                              {importResult.analysis.warnings.map((warn: string, i: number) => (
                                <li key={i}>⚠️ {warn}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-4">
                        <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                          <ExclamationTriangleIcon className="w-5 h-5" />
                          <span>{importResult.error || 'خطا در تحلیل فایل'}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                {!importResult ? (
                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowSmartImport(false)}
                      className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      انصراف
                    </button>
                    <button
                      onClick={handleSmartImport}
                      disabled={importLoading || (importMode === 'code' ? !importCode.trim() : !importFile)}
                      className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg hover:from-cyan-600 hover:to-blue-600 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {importLoading ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          در حال تحلیل...
                        </>
                      ) : (
                        <>
                          <SparklesIcon className="w-5 h-5" />
                          تحلیل و وارد کردن
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        setImportResult(null);
                        setImportCode('');
                        setImportFileName('');
                        setImportFile(null);
                      }}
                      className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      وارد کردن فایل دیگر
                    </button>
                    <button
                      onClick={() => {
                        setShowSmartImport(false);
                        setImportResult(null);
                        setImportCode('');
                        setImportFileName('');
                        setImportPrompt('');
                        setImportFile(null);
                      }}
                      className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
                    >
                      بستن
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 🆕 Deployment Guide Modal */}
        {showDeployGuide && deployGuide && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
              {/* Header */}
              <div className="p-6 bg-gradient-to-r from-green-500 to-emerald-600 text-white">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold flex items-center gap-3">
                    <RocketLaunchIcon className="w-8 h-8" />
                    {deployGuide.title}
                  </h2>
                  <button
                    onClick={() => setShowDeployGuide(false)}
                    className="p-2 hover:bg-white/20 rounded-lg transition"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>
                <p className="mt-2 text-white/80">
                  پروژه: {deployGuide.project_name}
                </p>
              </div>

              {/* Content */}
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {/* Requirements */}
                {deployGuide.requirements && deployGuide.requirements.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                      <CheckCircleIcon className="w-5 h-5 text-green-500" />
                      پیش‌نیازها
                    </h3>
                    <ul className="space-y-2">
                      {deployGuide.requirements.map((req: string, idx: number) => (
                        <li key={idx} className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                          <div className="w-2 h-2 bg-green-500 rounded-full" />
                          {req}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Steps */}
                {deployGuide.steps && deployGuide.steps.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                      <Cog6ToothIcon className="w-5 h-5 text-blue-500" />
                      مراحل اجرا
                    </h3>
                    <div className="space-y-4">
                      {deployGuide.steps.map((step: any) => (
                        <div key={step.step} className="bg-gray-50 dark:bg-gray-700 rounded-xl p-4">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                              {step.step}
                            </div>
                            <div className="font-medium text-gray-900 dark:text-white">{step.title}</div>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">{step.description}</p>
                          {step.command && (
                            <div className="bg-gray-900 text-green-400 rounded-lg p-3 font-mono text-sm flex items-center justify-between">
                              <code dir="ltr">{step.command}</code>
                              <button
                                onClick={() => navigator.clipboard.writeText(step.command)}
                                className="text-gray-400 hover:text-white p-1"
                                title="کپی"
                              >
                                <ClipboardDocumentIcon className="w-5 h-5" />
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Deployment Options */}
                {deployGuide.deployment_options && deployGuide.deployment_options.length > 0 && (
                  <div>
                    <h3 className="font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                      <RocketLaunchIcon className="w-5 h-5 text-purple-500" />
                      گزینه‌های استقرار
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {deployGuide.deployment_options.map((option: any, idx: number) => (
                        <a
                          key={idx}
                          href={option.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-xl p-4 hover:shadow-lg transition border border-purple-200 dark:border-purple-800"
                        >
                          <div className="font-medium text-purple-700 dark:text-purple-300">{option.name}</div>
                          <div className="text-sm text-gray-600 dark:text-gray-400">{option.description}</div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                <button
                  onClick={() => setShowDeployGuide(false)}
                  className="w-full px-4 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-700 transition"
                >
                  متوجه شدم
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
