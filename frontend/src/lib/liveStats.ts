'use client';

/**
 * (PM-INS-0010) ONE live source for the app-wide numbers — the home page's status row and the help circle's «آمار»
 * both read this, so they can never disagree again (the help box used to show 10 / 4 / 0 — counts of its own help
 * text — next to the home page's 9 repos / 4 models / 1305 tasks).
 *
 * Model keys are shown in the same three states as «مدل‌ها و تنظیمات» (PM-INS-0005): a provider is
 *   ok       — its newest real call (capability test) succeeded,
 *   failed   — its newest real call failed (e.g. invalid key) — with the real error,
 *   untested — a key is set but no real call was ever recorded.
 */

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type KeyState = 'ok' | 'failed' | 'untested';
export interface ProviderKey { name: string; state: KeyState; error?: string; at?: string }

interface Provider { name: string; available: boolean }
interface ModelRow { id: string; provider: string; is_available?: boolean; last_call?: { ok: boolean; at?: string; error?: string | null } | null }

export interface LiveStats {
  providers: Provider[] | null;
  /** providers that have a key, each with its three-state badge */
  keys: ProviderKey[] | null;
  enabledModels: any[] | null;
  oversight: any;
  inspection: any;
  disk: any;
  /** (PM-INS-0024) «اتاق فرمان» one-page summary — the SAME open-task numbers its card shows */
  summary: any;
  insOpen: number | null;
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API_BASE}${path}`);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

/** newest real call per provider ⇒ ok / failed; no call recorded ⇒ untested */
export function providerKeyStates(providers: Provider[], models: ModelRow[]): ProviderKey[] {
  return providers.filter((p) => p.available).map((p) => {
    const calls = models
      .filter((m) => m.provider === p.name && m.last_call)
      .map((m) => m.last_call!)
      .sort((a, b) => (b.at || '').localeCompare(a.at || ''));
    const last = calls[0];
    if (!last) return { name: p.name, state: 'untested' as const };
    return last.ok
      ? { name: p.name, state: 'ok' as const, at: last.at }
      : { name: p.name, state: 'failed' as const, at: last.at, error: last.error || undefined };
  });
}

export const KEY_STATE_LABEL: Record<KeyState, { icon: string; text: string; cls: string }> = {
  ok: { icon: '✓', text: 'API ✓', cls: 'bg-cyan-100 dark:bg-cyan-900 text-cyan-700 dark:text-cyan-300' },
  failed: { icon: '✕', text: 'API ✕ فراخوانی شکست خورد', cls: 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300' },
  untested: { icon: '?', text: 'کلید ✓ · آزموده نشده', cls: 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300' },
};

export function useLiveStats(active = true): LiveStats {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [models, setModels] = useState<ModelRow[] | null>(null);
  const [enabledModels, setEnabledModels] = useState<any[] | null>(null);
  const [oversight, setOversight] = useState<any>(null);
  const [inspection, setInspection] = useState<any>(null);
  const [disk, setDisk] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    if (!active) return;
    getJson<Provider[]>('/api/settings/providers').then((d) => setProviders(Array.isArray(d) ? d : []));
    getJson<ModelRow[]>('/api/models').then((d) => setModels(Array.isArray(d) ? d : []));
    getJson<any[]>('/api/models/available').then((m) => { if (Array.isArray(m)) setEnabledModels(m); });
    getJson<any>('/api/oversight/status').then(setOversight);
    getJson<any>('/api/inspection?limit=1').then(setInspection);
    getJson<any>('/api/oversight/disk').then(setDisk);
    getJson<any>('/api/oversight/summary').then(setSummary);
  }, [active]);

  const keys = providers && models ? providerKeyStates(providers, models) : null;
  const insOpen = inspection?.counts ? (inspection.counts.open || 0) + (inspection.counts.answered || 0) : null;
  return { providers, keys, enabledModels, oversight, inspection, disk, summary, insOpen };
}
