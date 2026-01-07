// تایپ‌های اصلی

export interface Project {
  id: string;
  name: string;
  description?: string;
  type?: string;
  status?: string;
  progress?: number;
  created_at?: string;
}

export interface Debate {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models: string[];
  rounds?: DebateRound[];
  scores?: any;
  judge_result?: any;
  summary?: string;
  created_at?: string;
}

export interface DebateRound {
  round_number: number;
  responses: DebateResponse[];
}

export interface DebateResponse {
  model: string;
  role: string;
  content: string;
  latency_ms?: number;
  tokens?: number;
}

export interface AIModel {
  id: string;
  name: string;
  provider: string;
  capabilities?: string[];
  max_tokens?: number;
  context_window?: number;
  cost_per_1k_tokens?: number;
  is_available?: boolean;
  priority?: number;
}

export interface Provider {
  name: string;
  available: boolean;
  models_count?: number;
}

export interface ApiKeysStatus {
  openai: boolean;
  anthropic: boolean;
  google: boolean;
  deepseek: boolean;
  openrouter?: boolean;
  groq?: boolean;
}

export interface AppConfig {
  max_tokens?: number;
  max_prompt_length?: number;
  request_timeout?: number;
  temperature?: number;
  max_retries?: number;
}

export interface FileItem {
  id: string;
  name: string;
  size: number;
  type: string;
  category?: string;
  uploaded_at?: string;
}

export interface WorkMode {
  id: string;
  name: string;
  description?: string;
}
