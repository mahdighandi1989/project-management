'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ProviderStats {
  provider: string;
  request_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  error_count: number;
  error_rate: number;
}

interface StatsResponse {
  days: number;
  providers: ProviderStats[];
  totals: {
    request_count: number;
    total_tokens: number;
    total_cost_usd: number;
  };
}

interface SummaryResponse {
  today: { count: number; tokens: number; cost_usd: number };
  last_7d: { count: number; tokens: number; cost_usd: number };
  last_30d: { count: number; tokens: number; cost_usd: number };
  last_request_at: string | null;
  distinct_providers_30d: number;
}

interface Leak {
  id: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  output_ratio: number;
  cost_usd: number;
  latency_ms: number;
  created_at: string;
  leak_reason: string;
  prompt_preview?: string;
  error_message?: string;
}

interface LeaksResponse {
  days: number;
  leaks_count: number;
  total_wasted_tokens_est: number;
  total_wasted_cost_usd_est: number;
  leaks: Leak[];
}

interface BalanceInfo {
  type?: 'remote_api' | 'manual_budget';
  // remote_api fields:
  remote_balance_usd?: number;
  currency?: string;
  is_available?: boolean;
  // manual_budget fields:
  budget_usd?: number;
  consumed_usd?: number;
  remaining_estimate_usd?: number;
  budget_reset_at?: string;
  // shared:
  alert_threshold_usd?: number;
  alert_last_sent_at?: string | null;
  last_checked_at?: string;
}

interface BalancesResponse {
  balances: Record<string, BalanceInfo>;
  providers_with_remote_api: string[];
  manual_only_providers: string[];
}

const PROVIDER_ICON: Record<string, string> = {
  openai: '🤖',
  claude: '🟣',
  anthropic: '🟣',
  gemini: '💎',
  google: '💎',
  deepseek: '🔍',
  perplexity: '🔮',
  openrouter: '🌐',
  groq: '⚡',
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return n.toString();
}

function formatCost(c: number): string {
  if (c < 0.01) return '$' + c.toFixed(6);
  if (c < 1) return '$' + c.toFixed(4);
  return '$' + c.toFixed(2);
}

function formatRelative(iso: string | null): string {
  if (!iso) return '—';
  try {
    const date = new Date(iso);
    const diff = Date.now() - date.getTime();
    if (diff < 60_000) return 'همین الان';
    if (diff < 3_600_000) return Math.floor(diff / 60_000) + ' دقیقه پیش';
    if (diff < 86_400_000) return Math.floor(diff / 3_600_000) + ' ساعت پیش';
    return Math.floor(diff / 86_400_000) + ' روز پیش';
  } catch {
    return iso;
  }
}

export default function AIUsagePanel() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [leaks, setLeaks] = useState<LeaksResponse | null>(null);
  const [balances, setBalances] = useState<BalancesResponse | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [refreshingBalance, setRefreshingBalance] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'providers' | 'leaks' | 'balances'>('overview');

  // budget edit form state
  const [editProvider, setEditProvider] = useState<string | null>(null);
  const [editBudget, setEditBudget] = useState('');
  const [editThreshold, setEditThreshold] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, summaryRes, leaksRes, balancesRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/ai-usage/stats?days=${days}`),
        fetch(`${API_BASE}/api/ai-usage/summary`),
        fetch(`${API_BASE}/api/ai-usage/leaks?days=7`),
        fetch(`${API_BASE}/api/ai-usage/balances`),
      ]);
      if (statsRes.status === 'fulfilled' && statsRes.value.ok)
        setStats(await statsRes.value.json());
      if (summaryRes.status === 'fulfilled' && summaryRes.value.ok)
        setSummary(await summaryRes.value.json());
      if (leaksRes.status === 'fulfilled' && leaksRes.value.ok)
        setLeaks(await leaksRes.value.json());
      if (balancesRes.status === 'fulfilled' && balancesRes.value.ok)
        setBalances(await balancesRes.value.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshBalances = async () => {
    setRefreshingBalance(true);
    try {
      const res = await fetch(`${API_BASE}/api/ai-usage/balances/refresh`, { method: 'POST' });
      if (res.ok) {
        // reload state
        const r = await fetch(`${API_BASE}/api/ai-usage/balances`);
        if (r.ok) setBalances(await r.json());
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRefreshingBalance(false);
    }
  };

  const saveBudget = async (provider: string) => {
    const budget_usd = parseFloat(editBudget);
    const threshold_usd = parseFloat(editThreshold);
    if (isNaN(budget_usd) || budget_usd < 0) {
      alert('Budget باید عددی مثبت باشد');
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/ai-usage/balances/${provider}/budget`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          budget_usd,
          alert_threshold_usd: isNaN(threshold_usd) ? undefined : threshold_usd,
        }),
      });
      if (res.ok) {
        setEditProvider(null);
        setEditBudget('');
        setEditThreshold('');
        await refreshBalances();
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const removeBudget = async (provider: string) => {
    if (!confirm(`Budget برای ${provider} حذف شود؟`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/ai-usage/balances/${provider}`, { method: 'DELETE' });
      if (res.ok) await refreshBalances();
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => { loadData(); }, [days]);

  const maxTokens = stats?.providers.reduce((m, p) => Math.max(m, p.total_tokens), 0) || 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-xl font-bold dark:text-white">📊 مصرف AI و نشتی‌ها</h2>
        <div className="flex gap-2 items-center text-sm">
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value, 10))}
            className="px-2 py-1 border rounded dark:bg-gray-700 dark:text-white dark:border-gray-600"
          >
            <option value={1}>۲۴ ساعت اخیر</option>
            <option value={7}>۷ روز اخیر</option>
            <option value={30}>۳۰ روز اخیر</option>
            <option value={90}>۹۰ روز اخیر</option>
          </select>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? '⏳' : '🔄'} به‌روزرسانی
          </button>
        </div>
      </div>

      {error && (
        <div className="p-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded text-sm">
          ❌ {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        {([
          ['overview', '📈 خلاصه'],
          ['providers', '🤖 Providers'],
          ['leaks', '🩸 نشتی‌ها'],
          ['balances', '💰 موجودی'],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-3 py-2 text-sm font-medium ${
              activeTab === key
                ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && summary && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
              <div className="text-xs text-gray-500 dark:text-gray-400">امروز</div>
              <div className="text-2xl font-bold dark:text-white">{formatNumber(summary.today.tokens)}</div>
              <div className="text-xs text-gray-500">{summary.today.count} request · {formatCost(summary.today.cost_usd)}</div>
            </div>
            <div className="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded">
              <div className="text-xs text-gray-500 dark:text-gray-400">۷ روز اخیر</div>
              <div className="text-2xl font-bold dark:text-white">{formatNumber(summary.last_7d.tokens)}</div>
              <div className="text-xs text-gray-500">{summary.last_7d.count} request · {formatCost(summary.last_7d.cost_usd)}</div>
            </div>
            <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded">
              <div className="text-xs text-gray-500 dark:text-gray-400">۳۰ روز اخیر</div>
              <div className="text-2xl font-bold dark:text-white">{formatNumber(summary.last_30d.tokens)}</div>
              <div className="text-xs text-gray-500">{summary.last_30d.count} request · {formatCost(summary.last_30d.cost_usd)}</div>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded text-sm dark:text-gray-200">
              🕒 آخرین درخواست: <span className="font-medium">{formatRelative(summary.last_request_at)}</span>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded text-sm dark:text-gray-200">
              🌐 Provider های فعال: <span className="font-medium">{summary.distinct_providers_30d}</span>
            </div>
          </div>
          {(!summary.last_request_at) && (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded text-sm">
              ℹ️ هنوز هیچ مصرف AI ثبت نشده. لاگ‌ها از زمان deploy کد جدید شروع می‌شوند.
            </div>
          )}
        </div>
      )}

      {/* Providers */}
      {activeTab === 'providers' && stats && (
        <div className="space-y-3">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            مجموع: <strong>{formatNumber(stats.totals.total_tokens)} توکن</strong> ·{' '}
            {stats.totals.request_count} درخواست · {formatCost(stats.totals.total_cost_usd)}
          </div>
          {stats.providers.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <div className="text-4xl mb-2">📭</div>
              <p>هنوز هیچ داده‌ای ثبت نشده</p>
            </div>
          ) : (
            <div className="space-y-2">
              {stats.providers.map((p) => (
                <div key={p.provider} className="p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{PROVIDER_ICON[p.provider] || '🔌'}</span>
                      <span className="font-semibold dark:text-white">{p.provider}</span>
                      {p.error_count > 0 && (
                        <span className="text-xs px-1.5 py-0.5 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300 rounded">
                          ⚠️ {p.error_count} خطا ({Math.round(p.error_rate * 100)}%)
                        </span>
                      )}
                    </div>
                    <div className="text-sm dark:text-gray-300">
                      <span className="font-bold">{formatNumber(p.total_tokens)}</span>{' '}
                      <span className="text-gray-500 text-xs">توکن · {formatCost(p.total_cost_usd)}</span>
                    </div>
                  </div>
                  {/* Bar */}
                  <div className="w-full h-2 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden mb-2">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${(p.total_tokens / maxTokens) * 100}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-gray-600 dark:text-gray-300">
                    <div>📥 input: <strong>{formatNumber(p.input_tokens)}</strong></div>
                    <div>📤 output: <strong>{formatNumber(p.output_tokens)}</strong></div>
                    <div>🔁 requests: <strong>{p.request_count}</strong></div>
                    <div>⏱ avg: <strong>{Math.round(p.avg_latency_ms)}ms</strong></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Leaks */}
      {activeTab === 'leaks' && leaks && (
        <div className="space-y-3">
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
            <div className="text-sm font-semibold dark:text-red-200">
              🩸 {leaks.leaks_count} نشتی در {leaks.days} روز اخیر
            </div>
            <div className="text-xs text-red-700 dark:text-red-300 mt-1">
              مجموع توکن هدررفته (تخمینی): <strong>{formatNumber(leaks.total_wasted_tokens_est)}</strong>{' '}
              · هزینه: <strong>{formatCost(leaks.total_wasted_cost_usd_est)}</strong>
            </div>
            <div className="text-[11px] text-gray-600 dark:text-gray-400 mt-1">
              «نشتی» = درخواست‌هایی با input سنگین ولی output ناچیز (output_ratio ≤ 10٪)،
              یا خطا با مصرف توکن. این نشانهٔ پرامپت بیش‌از‌حد، context اشباع‌شده، یا truncation است.
            </div>
          </div>
          {leaks.leaks.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <div className="text-4xl mb-2">✅</div>
              <p>هیچ نشتی شناسایی نشده</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[60vh] overflow-auto">
              {leaks.leaks.map((leak) => (
                <details key={leak.id} className="bg-gray-50 dark:bg-gray-700/50 rounded p-2 border border-red-100 dark:border-red-900/40">
                  <summary className="cursor-pointer text-sm flex items-center gap-2 flex-wrap">
                    <span className="text-base">{PROVIDER_ICON[leak.provider] || '🔌'}</span>
                    <code className="text-xs bg-gray-200 dark:bg-gray-600 px-1 rounded" dir="ltr">{leak.model}</code>
                    <span className="text-xs">
                      {formatNumber(leak.total_tokens)} → {formatNumber(leak.output_tokens)} ({Math.round(leak.output_ratio * 100)}%)
                    </span>
                    <span className="text-xs text-red-600 dark:text-red-300">
                      {leak.leak_reason === 'error_with_consumption' ? '💥 error' : '📉 low output'}
                    </span>
                    <span className="text-xs text-gray-500 mr-auto">{formatRelative(leak.created_at)}</span>
                  </summary>
                  <div className="mt-2 text-xs dark:text-gray-200 space-y-1">
                    <div>📥 input: {leak.input_tokens} · 📤 output: {leak.output_tokens} · ⏱ {leak.latency_ms}ms · 💰 {formatCost(leak.cost_usd)}</div>
                    {leak.error_message && (
                      <div className="text-red-600 dark:text-red-300">❌ {leak.error_message}</div>
                    )}
                    {leak.prompt_preview && (
                      <pre className="bg-white dark:bg-gray-800 p-2 rounded whitespace-pre-wrap break-words text-[11px]">
                        {leak.prompt_preview}
                      </pre>
                    )}
                  </div>
                </details>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Balances tab */}
      {activeTab === 'balances' && balances && (
        <div className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="text-xs text-gray-500 dark:text-gray-400">
              <strong>DeepSeek</strong>: موجودی واقعی از API ·{' '}
              <strong>بقیه</strong>: budget دستی (شارژ کرده‌اید چقدر؟) با محاسبهٔ مصرف از لاگ‌ها
            </div>
            <button
              onClick={refreshBalances}
              disabled={refreshingBalance}
              className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600 disabled:opacity-50"
            >
              {refreshingBalance ? '⏳ refresh...' : '🔄 refresh + check alerts'}
            </button>
          </div>

          {/* Remote API providers (DeepSeek) */}
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mt-3">🌐 موجودی واقعی (از API)</div>
          {balances.providers_with_remote_api.map((p) => {
            const b = balances.balances[p];
            if (!b) {
              return (
                <div key={p} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2">
                    <span>{PROVIDER_ICON[p]}</span>
                    <span className="font-medium dark:text-white">{p}</span>
                    <span className="text-xs text-gray-500 mr-auto">هنوز refresh نشده</span>
                  </div>
                </div>
              );
            }
            const balance = b.remote_balance_usd ?? 0;
            const threshold = b.alert_threshold_usd ?? 1.0;
            const isLow = balance <= threshold;
            return (
              <div key={p} className={`p-3 rounded border ${isLow ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700' : 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{PROVIDER_ICON[p]}</span>
                  <span className="font-semibold dark:text-white">{p}</span>
                  {isLow && <span className="text-xs px-1.5 py-0.5 bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200 rounded">⚠️ کم</span>}
                  <span className="mr-auto text-2xl font-bold dark:text-white">
                    {balance.toFixed(2)} <span className="text-xs">{b.currency || 'USD'}</span>
                  </span>
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  آستانه alert: <strong>${threshold.toFixed(2)}</strong> ·{' '}
                  آخرین بررسی: {formatRelative(b.last_checked_at || null)}
                </div>
                {editProvider === p ? (
                  <div className="mt-2 flex gap-2">
                    <input
                      type="number"
                      value={editThreshold}
                      onChange={(e) => setEditThreshold(e.target.value)}
                      placeholder="آستانه (USD)"
                      className="px-2 py-1 text-xs border rounded dark:bg-gray-700 dark:text-white"
                      step="0.5"
                      min="0"
                    />
                    <button
                      onClick={async () => {
                        const t = parseFloat(editThreshold);
                        if (!isNaN(t) && t >= 0) {
                          await fetch(`${API_BASE}/api/ai-usage/balances/${p}/threshold`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ threshold_usd: t }),
                          });
                          setEditProvider(null);
                          await refreshBalances();
                        }
                      }}
                      className="px-2 py-1 text-xs bg-blue-500 text-white rounded"
                    >
                      ذخیره
                    </button>
                    <button onClick={() => setEditProvider(null)} className="px-2 py-1 text-xs bg-gray-300 rounded">
                      انصراف
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => {
                      setEditProvider(p);
                      setEditThreshold(threshold.toString());
                    }}
                    className="mt-1 text-xs text-blue-600 dark:text-blue-300 hover:underline"
                  >
                    ✏️ تنظیم آستانه
                  </button>
                )}
              </div>
            );
          })}

          {/* Manual budget providers */}
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mt-4">
            ✋ Budget دستی (شارژ خودتان را ثبت کنید)
          </div>
          {balances.manual_only_providers.map((p) => {
            const b = balances.balances[p];
            const hasBudget = b && b.type === 'manual_budget';
            const budget = b?.budget_usd ?? 0;
            const consumed = b?.consumed_usd ?? 0;
            const remaining = b?.remaining_estimate_usd ?? 0;
            const threshold = b?.alert_threshold_usd ?? 1.0;
            const isLow = hasBudget && remaining <= threshold;
            const pct = hasBudget && budget > 0 ? Math.min(100, (consumed / budget) * 100) : 0;
            return (
              <div key={p} className={`p-3 rounded border ${hasBudget ? (isLow ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700' : 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700') : 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-700'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{PROVIDER_ICON[p]}</span>
                  <span className="font-semibold dark:text-white">{p}</span>
                  {hasBudget && isLow && (
                    <span className="text-xs px-1.5 py-0.5 bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200 rounded">⚠️ رو به اتمام</span>
                  )}
                  {hasBudget && (
                    <span className="mr-auto text-sm dark:text-white">
                      باقی <strong>${remaining.toFixed(2)}</strong> از <strong>${budget.toFixed(2)}</strong>
                    </span>
                  )}
                </div>
                {hasBudget && (
                  <>
                    <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden mb-1">
                      <div
                        className={`h-full ${isLow ? 'bg-red-500' : pct > 75 ? 'bg-yellow-500' : 'bg-green-500'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      مصرف: ${consumed.toFixed(2)} ({pct.toFixed(0)}%) · آستانه: ${threshold.toFixed(2)} · از: {b?.budget_reset_at?.slice(0, 10) || '—'}
                    </div>
                  </>
                )}
                {!hasBudget && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    Budget تعریف نشده — برای دریافت alert موجودی، شارژ خود را ثبت کنید
                  </div>
                )}
                {editProvider === p ? (
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      value={editBudget}
                      onChange={(e) => setEditBudget(e.target.value)}
                      placeholder="Budget (USD) مثلاً 10"
                      className="px-2 py-1 text-xs border rounded dark:bg-gray-700 dark:text-white"
                      step="1"
                      min="0"
                    />
                    <input
                      type="number"
                      value={editThreshold}
                      onChange={(e) => setEditThreshold(e.target.value)}
                      placeholder="آستانه (USD)"
                      className="px-2 py-1 text-xs border rounded dark:bg-gray-700 dark:text-white"
                      step="0.5"
                      min="0"
                    />
                    <button
                      onClick={() => saveBudget(p)}
                      className="col-span-2 px-2 py-1 text-xs bg-blue-500 text-white rounded"
                    >
                      ذخیره
                    </button>
                    <button
                      onClick={() => { setEditProvider(null); setEditBudget(''); setEditThreshold(''); }}
                      className="col-span-2 px-2 py-1 text-xs bg-gray-300 rounded"
                    >
                      انصراف
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-2 mt-1">
                    <button
                      onClick={() => {
                        setEditProvider(p);
                        setEditBudget(budget.toString());
                        setEditThreshold(threshold.toString());
                      }}
                      className="text-xs text-blue-600 dark:text-blue-300 hover:underline"
                    >
                      {hasBudget ? '✏️ ویرایش' : '➕ تنظیم budget'}
                    </button>
                    {hasBudget && (
                      <button
                        onClick={() => removeBudget(p)}
                        className="text-xs text-red-600 dark:text-red-300 hover:underline"
                      >
                        🗑 حذف
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded text-xs text-amber-800 dark:text-amber-300">
            💡 <strong>نکته:</strong> Anthropic / OpenAI / Gemini / Perplexity هیچ public API برای موجودی ندارند.
            با ثبت budget دستی، سیستم مصرف را از لاگ‌ها محاسبه و وقتی نزدیک آستانه است، notification می‌فرستد.
            DeepSeek تنها provider با API موجودی واقعی است.
          </div>
        </div>
      )}
    </div>
  );
}
