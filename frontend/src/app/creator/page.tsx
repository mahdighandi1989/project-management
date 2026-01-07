'use client';

import { useState, useEffect, useRef } from 'react';
// Layout is already provided by app/layout.tsx - DO NOT use here

// Tabs
const TABS = [
  { id: 'terminal', name: 'ترمینال', icon: '💻' },
  { id: 'files', name: 'فایل‌ها', icon: '📁' },
  { id: 'git', name: 'Git', icon: '🔀' },
  { id: 'services', name: 'سرویس‌ها', icon: '🌐' },
  { id: 'agents', name: 'AI Agents', icon: '🤖' },
  { id: 'projects', name: 'پروژه‌ها', icon: '🏗️' },
  { id: 'deploy', name: 'دیپلوی', icon: '🚀' },
  { id: 'diagrams', name: 'نمودارها', icon: '📊' },
];

interface CommandResult {
  success: boolean;
  output: string;
  error?: string;
  duration_ms?: number;
}

interface FileItem {
  path: string;
  name: string;
  is_dir: boolean;
  size: number;
}

interface Service {
  id: string;
  name: string;
  base_url: string;
  status: string;
  endpoints_count: number;
}

interface Agent {
  id: string;
  role: string;
  model: string;
  created_at: string;
  messages_count: number;
}

interface Project {
  id: string;
  name: string;
  path: string;
  type: string;
  status: string;
  created_at: string;
}

export default function CreatorPage() {
  const [activeTab, setActiveTab] = useState('terminal');
  const [loading, setLoading] = useState(false);

  // Terminal state
  const [terminalHistory, setTerminalHistory] = useState<Array<{ type: 'input' | 'output' | 'error'; content: string }>>([]);
  const [command, setCommand] = useState('');
  const terminalRef = useRef<HTMLDivElement>(null);

  // Files state
  const [currentPath, setCurrentPath] = useState('.');
  const [files, setFiles] = useState<FileItem[]>([]);
  const [fileContent, setFileContent] = useState('');
  const [selectedFile, setSelectedFile] = useState('');
  const [fileTree, setFileTree] = useState<any>(null);

  // Git state
  const [gitPath, setGitPath] = useState('.');
  const [gitOutput, setGitOutput] = useState('');
  const [commitMessage, setCommitMessage] = useState('');

  // Services state
  const [services, setServices] = useState<Service[]>([]);
  const [newService, setNewService] = useState({ name: '', base_url: '', auth_type: 'none' });
  const [selectedService, setSelectedService] = useState('');
  const [serviceResponse, setServiceResponse] = useState<any>(null);

  // Agents state
  const [agents, setAgents] = useState<Agent[]>([]);
  const [newAgentRole, setNewAgentRole] = useState('coder');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [agentMessage, setAgentMessage] = useState('');
  const [agentResponse, setAgentResponse] = useState('');
  const [collaborativeTask, setCollaborativeTask] = useState('');
  const [collaborativeResult, setCollaborativeResult] = useState<any>(null);

  // Projects state
  const [projects, setProjects] = useState<Project[]>([]);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    project_type: 'python',
    technologies: '',
    features: ''
  });
  const [selectedProject, setSelectedProject] = useState('');
  const [generateFileDesc, setGenerateFileDesc] = useState('');
  const [generateFilePath, setGenerateFilePath] = useState('');

  // 🚀 Deploy state
  const [renderApiKey, setRenderApiKey] = useState('');
  const [renderConfigured, setRenderConfigured] = useState(false);
  const [deployStatus, setDeployStatus] = useState<any>(null);
  const [deployLoading, setDeployLoading] = useState(false);
  const [renderServices, setRenderServices] = useState<any[]>([]);

  // 📊 Diagrams state
  const [diagrams, setDiagrams] = useState<any[]>([]);
  const [selectedDiagram, setSelectedDiagram] = useState<string>('');
  const [diagramContent, setDiagramContent] = useState('');
  const [diagramsLoading, setDiagramsLoading] = useState(false);

  // Workspace info
  const [workspaceInfo, setWorkspaceInfo] = useState<any>(null);

  // Load workspace info on mount
  useEffect(() => {
    fetchWorkspaceInfo();
  }, []);

  // Auto scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalHistory]);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchWorkspaceInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/creator/workspace/info`);
      const data = await res.json();
      if (data.success) {
        setWorkspaceInfo(data);
      }
    } catch (error) {
      console.error('Error fetching workspace info:', error);
    }
  };

  // =====================================
  // Terminal Functions
  // =====================================

  const executeCommand = async () => {
    if (!command.trim()) return;

    setTerminalHistory(prev => [...prev, { type: 'input', content: `$ ${command}` }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/creator/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      });
      const data: CommandResult = await res.json();

      if (data.success) {
        setTerminalHistory(prev => [...prev, { type: 'output', content: data.output || '(no output)' }]);
      } else {
        setTerminalHistory(prev => [...prev, { type: 'error', content: data.error || 'Error' }]);
      }
    } catch (error) {
      setTerminalHistory(prev => [...prev, { type: 'error', content: String(error) }]);
    } finally {
      setCommand('');
      setLoading(false);
    }
  };

  // =====================================
  // File Functions
  // =====================================

  const loadFiles = async (path: string = currentPath) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation: 'list', path, pattern: '*', recursive: false }),
      });
      const data = await res.json();
      if (data.success) {
        setFiles(data.output || []);
        setCurrentPath(path);
      }
    } catch (error) {
      console.error('Error loading files:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFileTree = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/creator/files/tree?path=.&max_depth=3`);
      const data = await res.json();
      if (data.success) {
        setFileTree(data.tree);
      }
    } catch (error) {
      console.error('Error loading file tree:', error);
    }
  };

  const readFile = async (path: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation: 'read', path }),
      });
      const data = await res.json();
      if (data.success) {
        setFileContent(data.output || '');
        setSelectedFile(path);
      }
    } catch (error) {
      console.error('Error reading file:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveFile = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation: 'write', path: selectedFile, content: fileContent }),
      });
      const data = await res.json();
      if (data.success) {
        alert('فایل ذخیره شد!');
      }
    } catch (error) {
      console.error('Error saving file:', error);
    } finally {
      setLoading(false);
    }
  };

  // =====================================
  // Git Functions
  // =====================================

  const gitOperation = async (operation: string, extra: any = {}) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/git`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation, path: gitPath, ...extra }),
      });
      const data = await res.json();
      setGitOutput(data.success ? (data.output || 'Success') : (data.error || 'Error'));
    } catch (error) {
      setGitOutput(String(error));
    } finally {
      setLoading(false);
    }
  };

  // =====================================
  // Services Functions
  // =====================================

  const loadServices = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/creator/services`);
      const data = await res.json();
      if (data.success) {
        setServices(data.services || []);
      }
    } catch (error) {
      console.error('Error loading services:', error);
    }
  };

  const registerService = async () => {
    if (!newService.name || !newService.base_url) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newService),
      });
      const data = await res.json();
      if (data.success) {
        setNewService({ name: '', base_url: '', auth_type: 'none' });
        loadServices();
      }
    } catch (error) {
      console.error('Error registering service:', error);
    } finally {
      setLoading(false);
    }
  };

  const discoverService = async (serviceId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/services/${serviceId}/discover`, {
        method: 'POST',
      });
      const data = await res.json();
      setServiceResponse(data);
      loadServices();
    } catch (error) {
      console.error('Error discovering service:', error);
    } finally {
      setLoading(false);
    }
  };

  // =====================================
  // Agents Functions
  // =====================================

  const loadAgents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/creator/agents`);
      const data = await res.json();
      if (data.success) {
        setAgents(data.agents || []);
      }
    } catch (error) {
      console.error('Error loading agents:', error);
    }
  };

  const createAgent = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newAgentRole }),
      });
      const data = await res.json();
      if (data.success) {
        loadAgents();
        setSelectedAgent(data.agent_id);
      }
    } catch (error) {
      console.error('Error creating agent:', error);
    } finally {
      setLoading(false);
    }
  };

  const queryAgent = async () => {
    if (!selectedAgent || !agentMessage.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/agents/${selectedAgent}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: agentMessage }),
      });
      const data = await res.json();
      setAgentResponse(data.success ? data.response : data.error);
      loadAgents();
    } catch (error) {
      setAgentResponse(String(error));
    } finally {
      setLoading(false);
      setAgentMessage('');
    }
  };

  const runCollaborativeTask = async () => {
    if (!collaborativeTask.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/agents/collaborative`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: collaborativeTask,
          roles: ['architect', 'coder', 'reviewer'],
          iterations: 2
        }),
      });
      const data = await res.json();
      setCollaborativeResult(data);
    } catch (error) {
      console.error('Error running collaborative task:', error);
    } finally {
      setLoading(false);
    }
  };

  // =====================================
  // Projects Functions
  // =====================================

  const loadProjects = async () => {
    try {
      // Load from main projects API (same as Projects page)
      const res = await fetch(`${API_BASE}/api/projects`);
      const data = await res.json();
      if (data.projects) {
        // Transform to match our interface
        const transformed = data.projects.map((p: any) => ({
          id: p.id,
          name: p.name,
          path: p.path || `/storage/projects/${p.id}`,
          type: p.type || p.project_type || 'python',
          status: p.status || 'active',
          created_at: p.created_at || new Date().toISOString(),
        }));
        setProjects(transformed);
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  const createProject = async () => {
    if (!newProject.name || !newProject.description) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newProject,
          technologies: newProject.technologies.split(',').map(t => t.trim()).filter(Boolean),
          features: newProject.features.split(',').map(f => f.trim()).filter(Boolean),
        }),
      });
      const data = await res.json();
      if (data.success) {
        loadProjects();
        setNewProject({ name: '', description: '', project_type: 'python', technologies: '', features: '' });
      }
    } catch (error) {
      console.error('Error creating project:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateFile = async () => {
    if (!selectedProject || !generateFilePath || !generateFileDesc) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/creator/projects/${selectedProject}/generate-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: generateFilePath, description: generateFileDesc }),
      });
      const data = await res.json();
      if (data.success) {
        alert('فایل تولید شد!');
        setGenerateFilePath('');
        setGenerateFileDesc('');
      }
    } catch (error) {
      console.error('Error generating file:', error);
    } finally {
      setLoading(false);
    }
  };

  // =====================================
  // 🚀 Deploy Functions
  // =====================================

  const checkRenderStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/unified/deploy/render/status`);
      const data = await res.json();
      setRenderConfigured(data.configured || false);
      if (data.configured) {
        loadRenderServices();
      }
    } catch (error) {
      console.error('Error checking Render status:', error);
    }
  };

  const configureRender = async () => {
    if (!renderApiKey) return;
    setDeployLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/unified/deploy/configure/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: renderApiKey }),
      });
      const data = await res.json();
      if (data.success) {
        setRenderConfigured(true);
        setRenderApiKey('');
        loadRenderServices();
      }
    } catch (error) {
      console.error('Error configuring Render:', error);
    } finally {
      setDeployLoading(false);
    }
  };

  const loadRenderServices = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/unified/deploy/render/services`);
      const data = await res.json();
      if (data.success) {
        setRenderServices(data.services || []);
      }
    } catch (error) {
      console.error('Error loading Render services:', error);
    }
  };

  const deployProject = async (projectId: string) => {
    setDeployLoading(true);
    setDeployStatus(null);
    try {
      const res = await fetch(`${API_BASE}/api/unified/projects/${projectId}/deploy/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      setDeployStatus(data);
      if (data.success) {
        loadRenderServices();
      }
    } catch (error: any) {
      setDeployStatus({ success: false, error: error.message });
    } finally {
      setDeployLoading(false);
    }
  };

  const getProjectDeployStatus = async (projectId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/unified/projects/${projectId}/deploy/status`);
      const data = await res.json();
      return data;
    } catch (error) {
      console.error('Error getting deploy status:', error);
      return null;
    }
  };

  // =====================================
  // 📊 Diagrams Functions
  // =====================================

  const loadProjectDiagrams = async (projectId: string, regenerate: boolean = false) => {
    setDiagramsLoading(true);
    try {
      const url = `${API_BASE}/api/unified/projects/${projectId}/diagrams${regenerate ? '?regenerate=true' : ''}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.success) {
        setDiagrams(data.diagrams || []);
        if (data.diagrams?.length > 0) {
          setSelectedDiagram(data.diagrams[0].type);
          setDiagramContent(data.diagrams[0].content);
        }
      }
    } catch (error) {
      console.error('Error loading diagrams:', error);
    } finally {
      setDiagramsLoading(false);
    }
  };

  const selectDiagram = (diagramType: string) => {
    const diagram = diagrams.find(d => d.type === diagramType);
    if (diagram) {
      setSelectedDiagram(diagramType);
      setDiagramContent(diagram.content);
    }
  };

  const regenerateDiagram = async (projectId: string, diagramType: string) => {
    setDiagramsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/unified/projects/${projectId}/diagrams/${diagramType}?regenerate=true`);
      const data = await res.json();
      if (data.success) {
        setDiagramContent(data.diagram.content);
        // Update in list
        setDiagrams(prev => prev.map(d =>
          d.type === diagramType ? { ...d, content: data.diagram.content } : d
        ));
      }
    } catch (error) {
      console.error('Error regenerating diagram:', error);
    } finally {
      setDiagramsLoading(false);
    }
  };

  const openInMermaidLive = (content: string) => {
    const encoded = btoa(unescape(encodeURIComponent(content)));
    window.open(`https://mermaid.live/edit#base64:${encoded}`, '_blank');
  };

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === 'files') {
      loadFiles();
      loadFileTree();
    } else if (activeTab === 'services') {
      loadServices();
    } else if (activeTab === 'agents') {
      loadAgents();
    } else if (activeTab === 'projects') {
      loadProjects();
    } else if (activeTab === 'deploy') {
      checkRenderStatus();
      loadProjects();
    } else if (activeTab === 'diagrams') {
      loadProjects();
    }
  }, [activeTab]);

  // =====================================
  // Render
  // =====================================

  const renderTreeNode = (node: any, depth: number = 0) => {
    if (!node) return null;
    return (
      <div style={{ paddingRight: depth * 16 }} className="text-sm">
        <span className={node.type === 'directory' ? 'text-blue-500' : 'text-gray-600'}>
          {node.type === 'directory' ? '📁' : '📄'} {node.name}
        </span>
        {node.children?.map((child: any, i: number) => (
          <div key={i}>{renderTreeNode(child, depth + 1)}</div>
        ))}
      </div>
    );
  };

  return (
    <>
      <div className="p-4 md:p-6 min-h-screen">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            🚀 AI Creator Engine
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            موتور خالق هوشمند - ایجاد پروژه، مدیریت فایل، Git، اتصال به سرویس‌ها و همکاری با AI
          </p>
        </div>

        {/* Workspace Info */}
        {workspaceInfo && (
          <div className="mb-6 grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="text-2xl font-bold text-primary">{workspaceInfo.active_projects || 0}</div>
              <div className="text-sm text-gray-500">پروژه فعال</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="text-2xl font-bold text-green-500">{workspaceInfo.active_agents || 0}</div>
              <div className="text-sm text-gray-500">AI Agent</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="text-2xl font-bold text-blue-500">{workspaceInfo.active_services || 0}</div>
              <div className="text-sm text-gray-500">سرویس متصل</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="text-2xl font-bold text-purple-500">{workspaceInfo.command_history_count || 0}</div>
              <div className="text-sm text-gray-500">دستور اجرا شده</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
              <div className="text-2xl font-bold text-orange-500">{workspaceInfo.tasks_count || 0}</div>
              <div className="text-sm text-gray-500">تسک</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {tab.icon} {tab.name}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          {/* Terminal Tab */}
          {activeTab === 'terminal' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">💻 ترمینال</h2>
              <div
                ref={terminalRef}
                className="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg h-80 overflow-auto mb-4"
                dir="ltr"
              >
                {terminalHistory.map((item, i) => (
                  <div
                    key={i}
                    className={`mb-1 ${
                      item.type === 'error' ? 'text-red-400' : item.type === 'input' ? 'text-white' : ''
                    }`}
                  >
                    {item.content}
                  </div>
                ))}
                {loading && <div className="animate-pulse">...</div>}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && executeCommand()}
                  className="flex-1 p-3 border rounded-lg font-mono dark:bg-gray-700 dark:border-gray-600"
                  placeholder="دستور را وارد کنید..."
                  dir="ltr"
                />
                <button
                  onClick={executeCommand}
                  disabled={loading}
                  className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50"
                >
                  اجرا
                </button>
              </div>
            </div>
          )}

          {/* Files Tab */}
          {activeTab === 'files' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div>
                <h3 className="font-semibold mb-4">📁 ساختار فایل‌ها</h3>
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 max-h-96 overflow-auto">
                  {fileTree ? renderTreeNode(fileTree) : <p>در حال بارگذاری...</p>}
                </div>
                <div className="mt-4">
                  <h4 className="font-medium mb-2">فایل‌ها در: {currentPath}</h4>
                  <div className="space-y-1 max-h-48 overflow-auto">
                    {files.map((file, i) => (
                      <button
                        key={i}
                        onClick={() => file.is_dir ? loadFiles(file.path) : readFile(file.path)}
                        className="w-full text-right p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded flex items-center gap-2"
                      >
                        <span>{file.is_dir ? '📁' : '📄'}</span>
                        <span className="flex-1">{file.name}</span>
                        {!file.is_dir && <span className="text-xs text-gray-500">{file.size}B</span>}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="lg:col-span-2">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold">
                    {selectedFile ? `📝 ${selectedFile}` : 'انتخاب فایل'}
                  </h3>
                  {selectedFile && (
                    <button
                      onClick={saveFile}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                    >
                      💾 ذخیره
                    </button>
                  )}
                </div>
                <textarea
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  className="w-full h-96 p-4 font-mono text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  placeholder="محتوای فایل..."
                  dir="ltr"
                />
              </div>
            </div>
          )}

          {/* Git Tab */}
          {activeTab === 'git' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">🔀 عملیات Git</h2>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">مسیر Repository</label>
                <input
                  type="text"
                  value={gitPath}
                  onChange={(e) => setGitPath(e.target.value)}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  dir="ltr"
                />
              </div>
              <div className="flex flex-wrap gap-2 mb-4">
                <button onClick={() => gitOperation('status')} className="px-4 py-2 bg-blue-500 text-white rounded-lg">Status</button>
                <button onClick={() => gitOperation('log')} className="px-4 py-2 bg-purple-500 text-white rounded-lg">Log</button>
                <button onClick={() => gitOperation('diff')} className="px-4 py-2 bg-yellow-500 text-white rounded-lg">Diff</button>
                <button onClick={() => gitOperation('add', { files: '.' })} className="px-4 py-2 bg-green-500 text-white rounded-lg">Add All</button>
                <button onClick={() => gitOperation('pull')} className="px-4 py-2 bg-cyan-500 text-white rounded-lg">Pull</button>
                <button onClick={() => gitOperation('push')} className="px-4 py-2 bg-orange-500 text-white rounded-lg">Push</button>
              </div>
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={commitMessage}
                  onChange={(e) => setCommitMessage(e.target.value)}
                  className="flex-1 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  placeholder="پیام commit..."
                />
                <button
                  onClick={() => gitOperation('commit', { message: commitMessage })}
                  disabled={!commitMessage}
                  className="px-6 py-3 bg-primary text-white rounded-lg disabled:opacity-50"
                >
                  Commit
                </button>
              </div>
              <div className="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg h-64 overflow-auto" dir="ltr">
                {gitOutput || 'خروجی Git اینجا نمایش داده می‌شود...'}
              </div>
            </div>
          )}

          {/* Services Tab */}
          {activeTab === 'services' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">🌐 سرویس‌های خارجی</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-medium mb-3">افزودن سرویس جدید</h3>
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={newService.name}
                      onChange={(e) => setNewService({ ...newService, name: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      placeholder="نام سرویس"
                    />
                    <input
                      type="text"
                      value={newService.base_url}
                      onChange={(e) => setNewService({ ...newService, base_url: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      placeholder="URL پایه (مثال: https://api.example.com)"
                      dir="ltr"
                    />
                    <select
                      value={newService.auth_type}
                      onChange={(e) => setNewService({ ...newService, auth_type: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value="none">بدون احراز هویت</option>
                      <option value="api_key">API Key</option>
                      <option value="bearer">Bearer Token</option>
                      <option value="basic">Basic Auth</option>
                    </select>
                    <button
                      onClick={registerService}
                      className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary-dark"
                    >
                      ثبت سرویس
                    </button>
                  </div>
                </div>
                <div>
                  <h3 className="font-medium mb-3">سرویس‌های متصل ({services.length})</h3>
                  <div className="space-y-2 max-h-64 overflow-auto">
                    {services.map((service) => (
                      <div
                        key={service.id}
                        className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg flex justify-between items-center"
                      >
                        <div>
                          <div className="font-medium">{service.name}</div>
                          <div className="text-xs text-gray-500" dir="ltr">{service.base_url}</div>
                        </div>
                        <div className="flex gap-2">
                          <span className={`px-2 py-1 text-xs rounded ${
                            service.status === 'connected' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {service.status}
                          </span>
                          <button
                            onClick={() => discoverService(service.id)}
                            className="px-3 py-1 text-sm bg-blue-500 text-white rounded"
                          >
                            کشف API
                          </button>
                        </div>
                      </div>
                    ))}
                    {services.length === 0 && (
                      <p className="text-gray-500 text-center py-4">هیچ سرویسی ثبت نشده</p>
                    )}
                  </div>
                  {serviceResponse && (
                    <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <h4 className="font-medium mb-2">نتیجه:</h4>
                      <pre className="text-xs overflow-auto" dir="ltr">
                        {JSON.stringify(serviceResponse, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Agents Tab */}
          {activeTab === 'agents' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">🤖 AI Agents</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Create Agent */}
                <div>
                  <h3 className="font-medium mb-3">ایجاد Agent جدید</h3>
                  <div className="flex gap-2 mb-4">
                    <select
                      value={newAgentRole}
                      onChange={(e) => setNewAgentRole(e.target.value)}
                      className="flex-1 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value="architect">🏛️ معمار (Architect)</option>
                      <option value="coder">💻 کدنویس (Coder)</option>
                      <option value="reviewer">🔍 بازبین (Reviewer)</option>
                      <option value="tester">🧪 تستر (Tester)</option>
                      <option value="analyzer">📊 تحلیلگر (Analyzer)</option>
                      <option value="orchestrator">🎭 هماهنگ‌کننده (Orchestrator)</option>
                    </select>
                    <button
                      onClick={createAgent}
                      className="px-6 py-3 bg-primary text-white rounded-lg"
                    >
                      ایجاد
                    </button>
                  </div>

                  {/* Active Agents */}
                  <h3 className="font-medium mb-3">Agents فعال ({agents.length})</h3>
                  <div className="space-y-2 max-h-48 overflow-auto">
                    {agents.map((agent) => (
                      <button
                        key={agent.id}
                        onClick={() => setSelectedAgent(agent.id)}
                        className={`w-full p-3 rounded-lg text-right ${
                          selectedAgent === agent.id
                            ? 'bg-primary text-white'
                            : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                      >
                        <div className="font-medium">{agent.role}</div>
                        <div className="text-xs opacity-75">{agent.model} | {agent.messages_count} پیام</div>
                      </button>
                    ))}
                  </div>

                  {/* Collaborative Task */}
                  <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg">
                    <h3 className="font-medium mb-3">🎭 تسک همکارانه</h3>
                    <textarea
                      value={collaborativeTask}
                      onChange={(e) => setCollaborativeTask(e.target.value)}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 h-24"
                      placeholder="توضیح تسک برای همکاری چند AI..."
                    />
                    <button
                      onClick={runCollaborativeTask}
                      disabled={!collaborativeTask.trim() || loading}
                      className="w-full mt-2 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg disabled:opacity-50"
                    >
                      {loading ? 'در حال پردازش...' : 'شروع همکاری'}
                    </button>
                  </div>
                </div>

                {/* Chat with Agent */}
                <div>
                  <h3 className="font-medium mb-3">
                    گفتگو با Agent
                    {selectedAgent && <span className="text-primary mr-2">({selectedAgent})</span>}
                  </h3>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 h-64 overflow-auto mb-4">
                    {agentResponse ? (
                      <div className="whitespace-pre-wrap text-sm">{agentResponse}</div>
                    ) : collaborativeResult ? (
                      <pre className="text-xs overflow-auto" dir="ltr">
                        {JSON.stringify(collaborativeResult, null, 2)}
                      </pre>
                    ) : (
                      <p className="text-gray-500 text-center">پاسخ Agent اینجا نمایش داده می‌شود...</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <textarea
                      value={agentMessage}
                      onChange={(e) => setAgentMessage(e.target.value)}
                      className="flex-1 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      placeholder="پیام خود را بنویسید..."
                      rows={2}
                    />
                    <button
                      onClick={queryAgent}
                      disabled={!selectedAgent || !agentMessage.trim() || loading}
                      className="px-6 bg-primary text-white rounded-lg disabled:opacity-50"
                    >
                      ارسال
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Projects Tab */}
          {activeTab === 'projects' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">🏗️ ایجاد پروژه</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Create Project */}
                <div>
                  <h3 className="font-medium mb-3">پروژه جدید</h3>
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={newProject.name}
                      onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      placeholder="نام پروژه"
                    />
                    <textarea
                      value={newProject.description}
                      onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 h-24"
                      placeholder="توضیحات پروژه..."
                    />
                    <select
                      value={newProject.project_type}
                      onChange={(e) => setNewProject({ ...newProject, project_type: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    >
                      <option value="python">Python</option>
                      <option value="fastapi">FastAPI</option>
                      <option value="flask">Flask</option>
                      <option value="django">Django</option>
                      <option value="node">Node.js</option>
                      <option value="react">React</option>
                      <option value="nextjs">Next.js</option>
                      <option value="vue">Vue.js</option>
                    </select>
                    <input
                      type="text"
                      value={newProject.technologies}
                      onChange={(e) => setNewProject({ ...newProject, technologies: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      placeholder="تکنولوژی‌ها (با کاما جدا کنید)"
                    />
                    <input
                      type="text"
                      value={newProject.features}
                      onChange={(e) => setNewProject({ ...newProject, features: e.target.value })}
                      className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                      placeholder="قابلیت‌ها (با کاما جدا کنید)"
                    />
                    <button
                      onClick={createProject}
                      disabled={!newProject.name || !newProject.description || loading}
                      className="w-full py-3 bg-primary text-white rounded-lg disabled:opacity-50"
                    >
                      {loading ? 'در حال ایجاد...' : '🚀 ایجاد پروژه'}
                    </button>
                  </div>
                </div>

                {/* Active Projects */}
                <div>
                  <h3 className="font-medium mb-3">پروژه‌های فعال ({projects.length})</h3>
                  <div className="space-y-2 max-h-48 overflow-auto mb-6">
                    {projects.map((project: any) => (
                      <button
                        key={project.id}
                        onClick={() => setSelectedProject(project.id)}
                        className={`w-full p-3 rounded-lg text-right ${
                          selectedProject === project.id
                            ? 'bg-primary text-white'
                            : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <div className="font-medium">{project.name}</div>
                        <div className="text-xs opacity-75">{project.type} | {project.status}</div>
                      </button>
                    ))}
                    {projects.length === 0 && (
                      <p className="text-gray-500 text-center py-4">هیچ پروژه‌ای ایجاد نشده</p>
                    )}
                  </div>

                  {/* Generate File */}
                  {selectedProject && (
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <h3 className="font-medium mb-3">📄 تولید فایل با AI</h3>
                      <input
                        type="text"
                        value={generateFilePath}
                        onChange={(e) => setGenerateFilePath(e.target.value)}
                        className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 mb-2"
                        placeholder="مسیر فایل (مثال: src/main.py)"
                        dir="ltr"
                      />
                      <textarea
                        value={generateFileDesc}
                        onChange={(e) => setGenerateFileDesc(e.target.value)}
                        className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 h-20 mb-2"
                        placeholder="توضیحات فایل..."
                      />
                      <button
                        onClick={generateFile}
                        disabled={!generateFilePath || !generateFileDesc || loading}
                        className="w-full py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
                      >
                        تولید فایل
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 🚀 Deploy Tab */}
          {activeTab === 'deploy' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                🚀 دیپلوی یک‌کلیکه به Render
              </h2>

              {/* Render Configuration */}
              {!renderConfigured ? (
                <div className="mb-6 p-6 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl">
                  <h3 className="font-bold text-lg mb-4">⚙️ تنظیم Render</h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    برای Deploy خودکار، API key رندر خود را وارد کنید.
                    <br />
                    <a
                      href="https://dashboard.render.com/account/api-keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:underline"
                    >
                      دریافت API Key از Render Dashboard
                    </a>
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={renderApiKey}
                      onChange={(e) => setRenderApiKey(e.target.value)}
                      className="flex-1 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 font-mono"
                      placeholder="rnd_xxxxxxxxxxxx"
                      dir="ltr"
                    />
                    <button
                      onClick={configureRender}
                      disabled={!renderApiKey || deployLoading}
                      className="px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
                    >
                      {deployLoading ? '...' : 'ذخیره'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg flex items-center gap-2">
                  <span className="text-green-500 text-xl">✅</span>
                  <span>Render متصل شده</span>
                </div>
              )}

              {/* Deploy Status */}
              {deployStatus && (
                <div className={`mb-6 p-4 rounded-lg ${
                  deployStatus.success
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700'
                    : 'bg-red-50 dark:bg-red-900/20 text-red-700'
                }`}>
                  {deployStatus.success ? (
                    <div>
                      <div className="font-bold mb-2">✅ Deploy شروع شد!</div>
                      {deployStatus.deployment?.url && (
                        <a
                          href={deployStatus.deployment.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:underline"
                        >
                          {deployStatus.deployment.url}
                        </a>
                      )}
                    </div>
                  ) : (
                    <div>❌ خطا: {deployStatus.error || deployStatus.deployment?.error}</div>
                  )}
                </div>
              )}

              {/* Projects List for Deploy */}
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-bold mb-4">پروژه‌ها</h3>
                  <div className="space-y-2 max-h-96 overflow-auto">
                    {projects.map((project: any) => (
                      <div
                        key={project.id}
                        className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <div className="font-medium">{project.name}</div>
                            <div className="text-xs text-gray-500">{project.type}</div>
                          </div>
                          <button
                            onClick={() => deployProject(project.id)}
                            disabled={!renderConfigured || deployLoading}
                            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg text-sm hover:from-purple-600 hover:to-blue-600 disabled:opacity-50"
                          >
                            {deployLoading ? '⏳' : '🚀 Deploy'}
                          </button>
                        </div>
                      </div>
                    ))}
                    {projects.length === 0 && (
                      <p className="text-gray-500 text-center py-8">هیچ پروژه‌ای وجود ندارد</p>
                    )}
                  </div>
                </div>

                {/* Render Services */}
                <div>
                  <h3 className="font-bold mb-4">سرویس‌های Deploy شده</h3>
                  <div className="space-y-2 max-h-96 overflow-auto">
                    {renderServices.map((service: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg"
                      >
                        <div className="font-medium">{service.name || service.service?.name}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {service.serviceDetails?.url || service.service?.serviceDetails?.url || 'URL نامشخص'}
                        </div>
                        <div className="text-xs mt-1">
                          وضعیت: {service.suspended === 'not_suspended' ? '🟢 فعال' : '🔴 متوقف'}
                        </div>
                      </div>
                    ))}
                    {renderServices.length === 0 && (
                      <p className="text-gray-500 text-center py-8">هیچ سرویسی Deploy نشده</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 📊 Diagrams Tab */}
          {activeTab === 'diagrams' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                📊 نمودارهای داینامیک پروژه
              </h2>

              {/* Project Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">انتخاب پروژه</label>
                <div className="flex gap-2">
                  <select
                    value={selectedProject}
                    onChange={(e) => {
                      setSelectedProject(e.target.value);
                      if (e.target.value) {
                        loadProjectDiagrams(e.target.value);
                      }
                    }}
                    className="flex-1 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  >
                    <option value="">انتخاب کنید...</option>
                    {projects.map((project: any) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                  {selectedProject && (
                    <button
                      onClick={() => loadProjectDiagrams(selectedProject, true)}
                      disabled={diagramsLoading}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                    >
                      {diagramsLoading ? '⏳' : '🔄 بازسازی'}
                    </button>
                  )}
                </div>
              </div>

              {selectedProject && diagrams.length > 0 && (
                <div className="grid md:grid-cols-4 gap-6">
                  {/* Diagram Type Selector */}
                  <div className="md:col-span-1">
                    <h3 className="font-bold mb-3">نوع نمودار</h3>
                    <div className="space-y-2">
                      {diagrams.map((diagram: any) => (
                        <button
                          key={diagram.type}
                          onClick={() => selectDiagram(diagram.type)}
                          className={`w-full p-3 rounded-lg text-right transition ${
                            selectedDiagram === diagram.type
                              ? 'bg-primary text-white'
                              : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <div className="font-medium">
                            {diagram.type === 'class' && '🏛️ کلاس'}
                            {diagram.type === 'flowchart' && '📊 فلوچارت'}
                            {diagram.type === 'sequence' && '📋 توالی'}
                            {diagram.type === 'er' && '🗄️ ER'}
                            {diagram.type === 'mindmap' && '🧠 نقشه ذهنی'}
                            {diagram.type === 'state' && '🔄 وضعیت'}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Diagram Preview */}
                  <div className="md:col-span-3">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold">پیش‌نمایش</h3>
                      <div className="flex gap-2">
                        <button
                          onClick={() => openInMermaidLive(diagramContent)}
                          className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded text-sm"
                        >
                          🌐 باز کردن در Mermaid Live
                        </button>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(diagramContent);
                            alert('کپی شد!');
                          }}
                          className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm"
                        >
                          📋 کپی
                        </button>
                      </div>
                    </div>

                    {/* Mermaid Code */}
                    <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-96">
                      <pre className="text-green-400 text-sm font-mono whitespace-pre-wrap" dir="ltr">
                        {diagramContent}
                      </pre>
                    </div>

                    {/* Mermaid Render (using img with mermaid.ink) */}
                    <div className="mt-4 p-4 bg-white dark:bg-gray-900 rounded-lg border">
                      <h4 className="font-medium mb-2 text-sm text-gray-600">نمایش گرافیکی</h4>
                      {diagramContent && (
                        <div className="flex justify-center">
                          <img
                            src={`https://mermaid.ink/img/${btoa(unescape(encodeURIComponent(diagramContent)))}`}
                            alt="Diagram"
                            className="max-w-full"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {selectedProject && diagrams.length === 0 && !diagramsLoading && (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-4">📊</div>
                  <p>نموداری برای این پروژه وجود ندارد</p>
                  <button
                    onClick={() => loadProjectDiagrams(selectedProject, true)}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg"
                  >
                    تولید نمودارها
                  </button>
                </div>
              )}

              {diagramsLoading && (
                <div className="flex justify-center py-12">
                  <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
                </div>
              )}

              {!selectedProject && (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-4">👆</div>
                  <p>یک پروژه انتخاب کنید</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
