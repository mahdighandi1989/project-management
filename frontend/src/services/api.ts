/**
 * API Service for communicating with backend
 */

import axios from 'axios';

// Get API URL from environment or use default
// In production, this should be set to the backend URL
const getApiUrl = () => {
  // Check if we're in browser
  if (typeof window !== 'undefined') {
    // Try to get from window config first (for runtime config)
    const runtimeUrl = (window as any).__NEXT_PUBLIC_API_URL__;
    if (runtimeUrl) return runtimeUrl;
  }

  // Use environment variable or default
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

const API_URL = getApiUrl();

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ===========================================
// Types
// ===========================================

export interface Model {
  id: string;
  provider: string;
  name: string;
  capabilities: string[];
  max_tokens: number;
  context_window: number;
  strengths: string[];
  weaknesses: string[];
  cost_per_1k_tokens: number;
  priority: number;
  enabled: boolean;
  supports_images: boolean;
  supports_video: boolean;
  is_image_generator: boolean;
  is_available: boolean;
}

export interface ProviderStatus {
  provider: string;
  available: boolean;
  model_count: number;
  models: string[];
}

export interface WorkMode {
  id: string;
  name: string;
  name_fa: string;
  icon: string;
  rounds: number;
  scoring: boolean;
  judge: boolean;
  summary: boolean;
  default_roles: string[];
}

export interface Role {
  id: string;
  name: string;
  name_fa: string;
  icon: string;
  description: string;
}

export interface DebateResponse {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models: string[];
  role_assignments: Record<string, string>;
  rounds_count: number;
  scores_count: number;
  has_judge: boolean;
  has_summary: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoundResponse {
  round_number: number;
  model_id: string;
  model_name: string;
  role: string;
  role_name: string;
  role_icon: string;
  content: string;
  tokens_used: number;
  latency_ms: number;
  error?: string;
}

export interface SynthesizedOutput {
  content: string;
  code_blocks: Array<{
    language: string;
    code: string;
    filename?: string;
  }>;
  key_points: string[];
  recommendations: string[];
  synthesizer_model: string;
}

export interface GeneratedFile {
  filename: string;
  content: string;
  language: string;
  description: string;
}

export interface DebateDetail extends DebateResponse {
  detected_mode?: string;
  rounds: RoundResponse[][];
  scores: any[];
  judge_result: any;
  synthesized_output?: SynthesizedOutput;
  generated_files?: GeneratedFile[];
  summary: string;
}

export interface ChatMessage {
  role: string;
  content: string;
  images?: string[];
}

export interface ChatResponse {
  model_id: string;
  content: string;
  tokens_used: number;
  latency_ms: number;
  finish_reason: string;
}

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  debug: boolean;
  available_providers: Record<string, boolean>;
}

// ===========================================
// API Functions
// ===========================================

// Models
export const modelsApi = {
  list: () => api.get<Model[]>('/api/models'),
  available: () => api.get<Model[]>('/api/models/available'),
  providers: () => api.get<ProviderStatus[]>('/api/models/providers'),
  get: (id: string) => api.get<Model>(`/api/models/${id}`),
  smartSelect: (prompt: string, max: number = 3) =>
    api.post<Model[]>('/api/models/smart-select', { prompt, max_models: max }),
  capabilities: () => api.get('/api/models/capabilities'),
};

// Attachment type for debates
export interface DebateAttachment {
  filename: string;
  content: string;
  type?: string;
  file_category?: string;
}

// Debate
export const debateApi = {
  create: (prompt: string, mode: string = 'auto', models?: string[], attachments?: DebateAttachment[], needsFileOutput: boolean = false) =>
    api.post<DebateResponse>('/api/debate/create', { prompt, mode, models, attachments, needs_file_output: needsFileOutput }),

  get: (id: string) => api.get<DebateDetail>(`/api/debate/${id}`),

  list: () => api.get<DebateResponse[]>('/api/debate/'),

  runRound: (id: string, roundNumber: number = 1, context?: string) =>
    api.post<RoundResponse[]>(`/api/debate/${id}/run-round`, { round_number: roundNumber, context }),

  runFull: (id: string) => api.post(`/api/debate/${id}/run-full`),

  score: (id: string) => api.post(`/api/debate/${id}/score`),

  judge: (id: string) => api.post(`/api/debate/${id}/judge`),

  summary: (id: string) => api.post<{ summary: string }>(`/api/debate/${id}/summary`),
};

// Chat
export const chatApi = {
  send: (modelId: string, messages: ChatMessage[], maxTokens: number = 4096) =>
    api.post<ChatResponse>('/api/chat/', {
      model_id: modelId,
      messages,
      max_tokens: maxTokens,
    }),

  multi: (modelIds: string[], messages: ChatMessage[], maxTokens: number = 4096) =>
    api.post<ChatResponse[]>('/api/chat/multi', {
      model_ids: modelIds,
      messages,
      max_tokens: maxTokens,
    }),

  withFallback: (modelIds: string[], messages: ChatMessage[], maxTokens: number = 4096) =>
    api.post<ChatResponse>('/api/chat/with-fallback', {
      model_ids: modelIds,
      messages,
      max_tokens: maxTokens,
    }),
};

// Settings
export const settingsApi = {
  status: () => api.get<SystemStatus>('/api/settings/status'),
  apiKeysStatus: () => api.get('/api/settings/api-keys/status'),
  updateApiKeys: (keys: Record<string, string>) => api.put('/api/settings/api-keys', keys),
  workModes: () => api.get<WorkMode[]>('/api/settings/work-modes'),
  roles: () => api.get<Role[]>('/api/settings/roles'),
  config: () => api.get('/api/settings/config'),
};

// Health
export const healthApi = {
  check: () => api.get('/health'),
  root: () => api.get('/'),
};

export default api;
