'use client';

import { useState, useEffect } from 'react';
import Layout from '@/components/Layout';

interface Project {
  project_id: string;
  name: string;
  type: string;
  status: string;
  progress: number;
  created_at: string;
  updated_at: string;
}

interface Phase {
  id: string;
  name: string;
  status: string;
  progress: number;
  steps: string[];
  completed_steps: string[];
}

const PROJECT_TYPES = [
  { id: 'web_app', name: 'اپلیکیشن وب', icon: '🌐' },
  { id: 'mobile_app', name: 'اپلیکیشن موبایل', icon: '📱' },
  { id: 'api_service', name: 'سرویس API', icon: '⚙️' },
  { id: 'data_pipeline', name: 'پایپلاین داده', icon: '📊' },
  { id: 'ml_project', name: 'پروژه ML', icon: '🤖' },
  { id: 'custom', name: 'سفارشی', icon: '📦' },
];

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState<any>(null);
  const [diagram, setDiagram] = useState<string>('');

  // فرم ایجاد پروژه
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    project_type: 'custom',
    goal: '',
    complexity: 'medium',
  });

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const res = await fetch('/api/projects');
      const data = await res.json();
      if (data.success) {
        setProjects(data.projects);
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const createProject = async () => {
    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject),
      });
      const data = await res.json();
      if (data.success) {
        setShowCreateModal(false);
        loadProjects();
        setNewProject({
          name: '',
          description: '',
          project_type: 'custom',
          goal: '',
          complexity: 'medium',
        });
      }
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  const loadProject = async (projectId: string) => {
    try {
      const [projectRes, diagramRes] = await Promise.all([
        fetch(`/api/projects/${projectId}`),
        fetch(`/api/projects/${projectId}/diagram`),
      ]);

      const projectData = await projectRes.json();
      const diagramData = await diagramRes.json();

      if (projectData.success) {
        setSelectedProject(projectData.project);
      }
      if (diagramData.success) {
        setDiagram(diagramData.mermaid);
      }
    } catch (error) {
      console.error('Error loading project:', error);
    }
  };

  const startNextPhase = async () => {
    if (!selectedProject) return;

    try {
      const res = await fetch(`/api/projects/${selectedProject.project_id}/next-phase`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        loadProject(selectedProject.project_id);
        loadProjects();
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'in_progress': return '🔄';
      case 'pending': return '⏳';
      case 'failed': return '❌';
      case 'paused': return '⏸️';
      default: return '📌';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'in_progress': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'pending': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
      case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Layout>
      <div className="p-6">
        {/* هدر */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold">🚀 مدیریت پروژه</h1>
            <p className="text-gray-600 dark:text-gray-400">
              ایجاد و مدیریت پروژه‌های هوشمند با کمک AI
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition"
          >
            + پروژه جدید
          </button>
        </div>

        {/* محتوای اصلی */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* لیست پروژه‌ها */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4">
              <h2 className="text-lg font-semibold mb-4">پروژه‌ها</h2>

              {loading ? (
                <div className="text-center py-8">
                  <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>هنوز پروژه‌ای ندارید</p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="mt-2 text-primary hover:underline"
                  >
                    اولین پروژه را بسازید
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {projects.map((project) => (
                    <div
                      key={project.project_id}
                      onClick={() => loadProject(project.project_id)}
                      className={`p-4 rounded-lg cursor-pointer transition border-2
                        ${selectedProject?.project_id === project.project_id
                          ? 'border-primary bg-primary/10'
                          : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-medium">{project.name}</h3>
                        <span className={`text-xs px-2 py-1 rounded ${getStatusColor(project.status)}`}>
                          {getStatusIcon(project.status)} {project.status === 'active' ? 'فعال' : project.status === 'completed' ? 'تکمیل' : project.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span>{PROJECT_TYPES.find(t => t.id === project.type)?.icon}</span>
                        <span>{PROJECT_TYPES.find(t => t.id === project.type)?.name}</span>
                      </div>

                      {/* نوار پیشرفت */}
                      <div className="mt-3">
                        <div className="flex justify-between text-xs mb-1">
                          <span>پیشرفت</span>
                          <span>{project.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{ width: `${project.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* جزئیات پروژه */}
          <div className="lg:col-span-2">
            {selectedProject ? (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-xl font-bold">{selectedProject.name}</h2>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                      {selectedProject.description || 'بدون توضیحات'}
                    </p>
                  </div>
                  <button
                    onClick={startNextPhase}
                    className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition"
                  >
                    شروع فاز بعدی
                  </button>
                </div>

                {/* فازها */}
                <div className="mb-6">
                  <h3 className="font-semibold mb-3">فازهای پروژه</h3>
                  <div className="space-y-3">
                    {selectedProject.phases?.map((phase: Phase, index: number) => (
                      <div
                        key={phase.id}
                        className={`p-4 rounded-lg border-2 ${
                          phase.status === 'in_progress'
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : phase.status === 'completed'
                            ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                            : 'border-gray-200 dark:border-gray-600'
                        }`}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xl">{getStatusIcon(phase.status)}</span>
                            <span className="font-medium">
                              فاز {index + 1}: {phase.name}
                            </span>
                          </div>
                          <span className="text-sm text-gray-500">
                            {phase.progress}%
                          </span>
                        </div>

                        {phase.steps && phase.steps.length > 0 && (
                          <div className="mt-2 text-sm">
                            <div className="flex flex-wrap gap-2">
                              {phase.steps.map((step, i) => (
                                <span
                                  key={i}
                                  className={`px-2 py-1 rounded ${
                                    phase.completed_steps?.includes(step)
                                      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200'
                                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                                  }`}
                                >
                                  {phase.completed_steps?.includes(step) ? '✓ ' : '○ '}
                                  {step}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* نوار پیشرفت فاز */}
                        <div className="mt-3">
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full transition-all ${
                                phase.status === 'completed' ? 'bg-green-500' :
                                phase.status === 'in_progress' ? 'bg-blue-500' : 'bg-gray-400'
                              }`}
                              style={{ width: `${phase.progress}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* نمودار */}
                {diagram && (
                  <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <h3 className="font-semibold mb-3">نمودار پروژه</h3>
                    <pre className="text-xs overflow-x-auto p-4 bg-white dark:bg-gray-800 rounded border">
                      {diagram}
                    </pre>
                    <p className="text-xs text-gray-500 mt-2">
                      این نمودار Mermaid است. می‌توانید در mermaid.live آن را مشاهده کنید.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
                <div className="text-6xl mb-4">📋</div>
                <h3 className="text-lg font-medium mb-2">پروژه‌ای انتخاب نشده</h3>
                <p className="text-gray-500">از لیست سمت راست یک پروژه انتخاب کنید</p>
              </div>
            )}
          </div>
        </div>

        {/* مودال ایجاد پروژه */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-full max-w-lg mx-4">
              <h2 className="text-xl font-bold mb-4">ایجاد پروژه جدید</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">نام پروژه *</label>
                  <input
                    type="text"
                    value={newProject.name}
                    onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    placeholder="نام پروژه..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">توضیحات</label>
                  <textarea
                    value={newProject.description}
                    onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    rows={3}
                    placeholder="توضیحات پروژه..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">نوع پروژه</label>
                  <div className="grid grid-cols-3 gap-2">
                    {PROJECT_TYPES.map((type) => (
                      <button
                        key={type.id}
                        onClick={() => setNewProject({ ...newProject, project_type: type.id })}
                        className={`p-3 rounded-lg border-2 transition text-center ${
                          newProject.project_type === type.id
                            ? 'border-primary bg-primary/10'
                            : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-2xl mb-1">{type.icon}</div>
                        <div className="text-xs">{type.name}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">هدف</label>
                  <input
                    type="text"
                    value={newProject.goal}
                    onChange={(e) => setNewProject({ ...newProject, goal: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    placeholder="هدف اصلی پروژه..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">پیچیدگی</label>
                  <select
                    value={newProject.complexity}
                    onChange={(e) => setNewProject({ ...newProject, complexity: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  >
                    <option value="low">ساده</option>
                    <option value="medium">متوسط</option>
                    <option value="high">پیچیده</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  انصراف
                </button>
                <button
                  onClick={createProject}
                  disabled={!newProject.name}
                  className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50"
                >
                  ایجاد پروژه
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
