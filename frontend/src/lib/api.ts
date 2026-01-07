// API مرکزی
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// درخواست‌های پایه
async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<{ ok: boolean; data?: T; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });

    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    } else {
      return { ok: false, error: `خطا: ${res.status}` };
    }
  } catch (e) {
    return { ok: false, error: 'خطا در ارتباط با سرور' };
  }
}

// پروژه‌ها
export const projectsApi = {
  list: () => request<{ projects: any[] }>('/api/projects'),

  get: (id: string) => request<any>(`/api/projects/${id}`),

  create: (data: { name: string; description?: string }) =>
    request<any>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<any>(`/api/projects/${id}`, { method: 'DELETE' }),
};

// مناظره
export const debateApi = {
  list: () => request<any[]>('/api/debate/'),

  get: (id: string) => request<any>(`/api/debate/${id}`),

  create: (data: { prompt: string; mode: string; models?: string[] }) =>
    request<any>('/api/debate/create', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  runFull: (id: string) =>
    request<any>(`/api/debate/${id}/run-full`, { method: 'POST' }),
};

// مدل‌ها
export const modelsApi = {
  list: () => request<any[]>('/api/models'),

  available: () => request<any[]>('/api/models/available'),

  providers: () => request<any[]>('/api/settings/providers'),
};

// تنظیمات
export const settingsApi = {
  status: () => request<any>('/api/settings/status'),

  apiKeysStatus: () => request<any>('/api/settings/api-keys/status'),

  updateApiKeys: (keys: Record<string, string>) =>
    request<any>('/api/settings/api-keys', {
      method: 'PUT',
      body: JSON.stringify(keys),
    }),

  config: () => request<any>('/api/config'),

  updateConfig: (config: any) =>
    request<any>('/api/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),

  workModes: () => request<any[]>('/api/settings/work-modes'),
};

// آرشیو
export const archiveApi = {
  debates: () => request<any[]>('/api/debate/'),

  files: () => request<{ files: any[] }>('/api/upload/files'),

  fileStats: () => request<any>('/api/upload/stats'),

  deleteFile: (id: string) =>
    request<any>(`/api/upload/file/${id}`, { method: 'DELETE' }),
};

// نمودارها
export const diagramsApi = {
  example: (type: string) => request<any>(`/api/diagrams/examples/${type}`),

  analyzeCode: (code: string, language: string) =>
    request<any>('/api/diagrams/analyze-code', {
      method: 'POST',
      body: JSON.stringify({ code, language }),
    }),
};

export { API_BASE };
