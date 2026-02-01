'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RenderService {
  id: string;
  name: string;
  type: string;
  region: string;
  status: string;
  auto_fetch_logs: boolean;
}

interface RenderLog {
  id: string;
  service_id: string;
  service_name: string;
  timestamp: string;
  level: string;
  message: string;
  deploy_id?: string;
}

interface LogSettings {
  polling_interval_seconds: number;
  polling_enabled: boolean;
  retention_hours: number;
  archive_enabled: boolean;
  default_log_levels: string;
  auto_scroll: boolean;
}

interface LogStats {
  total_logs: number;
  by_level: Record<string, number>;
  by_service: { service_id: string; service_name: string; count: number }[];
  error_count: number;
  warning_count: number;
}

export default function RenderLogsPanel() {
  // State
  const [services, setServices] = useState<RenderService[]>([]);
  const [logs, setLogs] = useState<RenderLog[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [settings, setSettings] = useState<LogSettings>({
    polling_interval_seconds: 10,
    polling_enabled: true,
    retention_hours: 48,
    archive_enabled: true,
    default_log_levels: 'info,warn,error',
    auto_scroll: true,
  });

  // Filters
  const [selectedService, setSelectedService] = useState<string>('all');
  const [selectedLevels, setSelectedLevels] = useState<string[]>(['info', 'warn', 'error']);
  const [searchTerm, setSearchTerm] = useState('');
  const [timeRange, setTimeRange] = useState(30); // minutes

  // UI State
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState<'live' | 'settings' | 'stats'>('live');
  const [isPolling, setIsPolling] = useState(false);

  // Refs
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastTimestampRef = useRef<string | null>(null);

  // Load initial data
  useEffect(() => {
    loadInitialData();
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Start/stop polling
  useEffect(() => {
    if (settings.polling_enabled && activeTab === 'live') {
      startPolling();
    } else {
      stopPolling();
    }
    return () => stopPolling();
  }, [settings.polling_enabled, settings.polling_interval_seconds, activeTab]);

  // Auto scroll
  useEffect(() => {
    if (settings.auto_scroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs, settings.auto_scroll]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const loadInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadServices(),
        loadSettings(),
        loadStats(),
      ]);
      await fetchNewLogs();
      await loadLogs();
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadServices = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/services`);
      if (res.ok) {
        const data = await res.json();
        setServices(data.services || []);
      }
    } catch (e) {
      console.error('Error loading services:', e);
    }
  };

  const refreshServices = async () => {
    setFetching(true);
    try {
      const res = await fetch(`${API_BASE}/api/render/services/refresh`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setServices(data.services || []);
        showSuccess(`${data.services?.length || 0} سرویس یافت شد`);
      } else {
        const err = await res.json();
        showError(err.detail || 'خطا در بروزرسانی سرویس‌ها');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    } finally {
      setFetching(false);
    }
  };

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/settings`);
      if (res.ok) {
        const data = await res.json();
        if (data.settings) {
          setSettings(data.settings);
          setSelectedLevels(data.settings.default_log_levels.split(','));
        }
      }
    } catch (e) {
      console.error('Error loading settings:', e);
    }
  };

  const saveSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        showSuccess('تنظیمات ذخیره شد');
      } else {
        showError('خطا در ذخیره تنظیمات');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/stats?hours=24`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Error loading stats:', e);
    }
  };

  const loadLogs = async () => {
    try {
      const params = new URLSearchParams({
        minutes: timeRange.toString(),
        limit: '500',
        level: selectedLevels.join(','),
      });
      if (selectedService !== 'all') {
        params.append('service_id', selectedService);
      }
      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const res = await fetch(`${API_BASE}/api/render/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
        if (data.logs?.length > 0) {
          lastTimestampRef.current = data.logs[0].timestamp;
        }
      }
    } catch (e) {
      console.error('Error loading logs:', e);
    }
  };

  const fetchNewLogs = async () => {
    setFetching(true);
    try {
      const params: Record<string, string> = { limit: '100' };
      if (selectedService !== 'all') {
        params.service_id = selectedService;
      }

      const res = await fetch(`${API_BASE}/api/render/logs/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.saved > 0) {
          showSuccess(`${data.saved} لاگ جدید ذخیره شد`);
          await loadLogs();
        }
      }
    } catch (e) {
      console.error('Error fetching new logs:', e);
    } finally {
      setFetching(false);
    }
  };

  const pollForNewLogs = useCallback(async () => {
    if (!lastTimestampRef.current) return;

    try {
      const params = new URLSearchParams({
        since_timestamp: lastTimestampRef.current,
        levels: selectedLevels.join(','),
        limit: '50',
      });
      if (selectedService !== 'all') {
        params.append('service_id', selectedService);
      }

      const res = await fetch(`${API_BASE}/api/render/logs/live?${params}`);
      if (res.ok) {
        const data = await res.json();
        if (data.logs?.length > 0) {
          setLogs(prev => [...prev, ...data.logs]);
          lastTimestampRef.current = data.latest_timestamp;
        }
      }
    } catch (e) {
      console.error('Error polling logs:', e);
    }
  }, [selectedService, selectedLevels]);

  const startPolling = () => {
    if (pollingIntervalRef.current) return;
    setIsPolling(true);
    pollingIntervalRef.current = setInterval(() => {
      pollForNewLogs();
    }, settings.polling_interval_seconds * 1000);
  };

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  };

  const toggleLevel = (level: string) => {
    setSelectedLevels(prev =>
      prev.includes(level)
        ? prev.filter(l => l !== level)
        : [...prev, level]
    );
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'warn': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'debug': return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
      default: return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    }
  };

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('fa-IR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return timestamp;
    }
  };

  const filteredLogs = logs.filter(log => {
    if (searchTerm && !log.message.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin text-4xl">🔄</div>
        <span className="mr-2">در حال بارگذاری...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* پیام‌ها */}
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded-lg">{error}</div>
      )}
      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded-lg">{success}</div>
      )}

      {/* تب‌های داخلی */}
      <div className="flex gap-2 border-b pb-2">
        <button
          onClick={() => setActiveTab('live')}
          className={`px-4 py-2 rounded-t-lg font-medium ${
            activeTab === 'live'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
          }`}
        >
          📺 لاگ زنده
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`px-4 py-2 rounded-t-lg font-medium ${
            activeTab === 'stats'
              ? 'bg-purple-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
          }`}
        >
          📊 آمار
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`px-4 py-2 rounded-t-lg font-medium ${
            activeTab === 'settings'
              ? 'bg-gray-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
          }`}
        >
          ⚙️ تنظیمات
        </button>
      </div>

      {activeTab === 'live' && (
        <>
          {/* فیلترها */}
          <div className="flex flex-wrap gap-3 items-center bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            {/* انتخاب سرویس */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">سرویس:</label>
              <select
                value={selectedService}
                onChange={(e) => {
                  setSelectedService(e.target.value);
                  setTimeout(loadLogs, 100);
                }}
                className="p-2 border rounded dark:bg-gray-700"
              >
                <option value="all">همه سرویس‌ها</option>
                {services.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <button
                onClick={refreshServices}
                disabled={fetching}
                className="p-2 text-blue-500 hover:bg-blue-50 rounded"
                title="بروزرسانی سرویس‌ها"
              >
                🔄
              </button>
            </div>

            {/* سطوح لاگ */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">سطح:</label>
              {['info', 'warn', 'error', 'debug'].map(level => (
                <button
                  key={level}
                  onClick={() => toggleLevel(level)}
                  className={`px-3 py-1 rounded text-sm ${
                    selectedLevels.includes(level)
                      ? getLevelColor(level)
                      : 'bg-gray-200 dark:bg-gray-600 opacity-50'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>

            {/* بازه زمانی */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">بازه:</label>
              <select
                value={timeRange}
                onChange={(e) => {
                  setTimeRange(parseInt(e.target.value));
                  setTimeout(loadLogs, 100);
                }}
                className="p-2 border rounded dark:bg-gray-700"
              >
                <option value={10}>10 دقیقه</option>
                <option value={30}>30 دقیقه</option>
                <option value={60}>1 ساعت</option>
                <option value={180}>3 ساعت</option>
                <option value={720}>12 ساعت</option>
                <option value={1440}>24 ساعت</option>
              </select>
            </div>

            {/* جستجو */}
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="جستجو در لاگ‌ها..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full p-2 border rounded dark:bg-gray-700"
              />
            </div>

            {/* دکمه‌های کنترل */}
            <div className="flex gap-2">
              <button
                onClick={fetchNewLogs}
                disabled={fetching}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {fetching ? '...' : '🔄 بروزرسانی'}
              </button>
              <button
                onClick={() => settings.polling_enabled ? stopPolling() : startPolling()}
                className={`px-4 py-2 rounded ${
                  isPolling
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-600'
                }`}
              >
                {isPolling ? '⏸️ توقف' : '▶️ زنده'}
              </button>
            </div>
          </div>

          {/* وضعیت */}
          <div className="flex justify-between items-center text-sm text-gray-500">
            <span>{filteredLogs.length} لاگ نمایش داده می‌شود</span>
            {isPolling && (
              <span className="flex items-center gap-1 text-green-500">
                <span className="animate-pulse">●</span>
                در حال دریافت لاگ زنده هر {settings.polling_interval_seconds} ثانیه
              </span>
            )}
          </div>

          {/* لیست لاگ‌ها */}
          <div
            ref={logsContainerRef}
            className="h-[500px] overflow-y-auto bg-gray-900 rounded-lg p-4 font-mono text-sm"
            dir="ltr"
          >
            {filteredLogs.length === 0 ? (
              <div className="text-gray-500 text-center py-8">
                لاگی یافت نشد. روی "بروزرسانی" کلیک کنید.
              </div>
            ) : (
              filteredLogs.map((log, idx) => (
                <div
                  key={log.id || idx}
                  className="flex gap-2 py-1 hover:bg-gray-800 rounded px-2"
                >
                  <span className="text-gray-500 shrink-0">
                    {formatTime(log.timestamp)}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs shrink-0 ${getLevelColor(log.level)}`}>
                    {log.level.toUpperCase()}
                  </span>
                  {log.service_name && (
                    <span className="text-purple-400 shrink-0">
                      [{log.service_name}]
                    </span>
                  )}
                  <span className={`flex-1 ${
                    log.level === 'error' ? 'text-red-400' :
                    log.level === 'warn' ? 'text-yellow-400' :
                    'text-gray-300'
                  }`}>
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {activeTab === 'stats' && stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* کل لاگ‌ها */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow">
            <div className="text-3xl font-bold text-blue-500">{stats.total_logs}</div>
            <div className="text-gray-500">کل لاگ‌ها (24 ساعت)</div>
          </div>

          {/* خطاها */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow">
            <div className="text-3xl font-bold text-red-500">{stats.error_count}</div>
            <div className="text-gray-500">خطاها</div>
          </div>

          {/* هشدارها */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow">
            <div className="text-3xl font-bold text-yellow-500">{stats.warning_count}</div>
            <div className="text-gray-500">هشدارها</div>
          </div>

          {/* بر اساس سرویس */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow col-span-full">
            <h3 className="font-bold mb-4">لاگ‌ها بر اساس سرویس</h3>
            <div className="space-y-2">
              {stats.by_service.map(s => (
                <div key={s.service_id} className="flex justify-between items-center">
                  <span>{s.service_name || s.service_id}</span>
                  <span className="bg-blue-100 dark:bg-blue-900 px-3 py-1 rounded">
                    {s.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow space-y-6">
          <h3 className="font-bold text-lg">تنظیمات لاگ Render</h3>

          {/* Polling */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="font-medium">دریافت خودکار لاگ (Polling)</label>
              <button
                onClick={() => setSettings(s => ({ ...s, polling_enabled: !s.polling_enabled }))}
                className={`w-12 h-6 rounded-full transition ${
                  settings.polling_enabled ? 'bg-green-500' : 'bg-gray-300'
                }`}
              >
                <div className={`w-5 h-5 rounded-full bg-white shadow transition transform ${
                  settings.polling_enabled ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            <div>
              <label className="block text-sm mb-2">
                فاصله دریافت: {settings.polling_interval_seconds} ثانیه
              </label>
              <input
                type="range"
                min="5"
                max="60"
                step="5"
                value={settings.polling_interval_seconds}
                onChange={(e) => setSettings(s => ({
                  ...s,
                  polling_interval_seconds: parseInt(e.target.value)
                }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>5 ثانیه</span>
                <span>60 ثانیه</span>
              </div>
            </div>
          </div>

          {/* Retention */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm mb-2">
                نگه‌داری لاگ زنده: {settings.retention_hours} ساعت
              </label>
              <input
                type="range"
                min="6"
                max="168"
                step="6"
                value={settings.retention_hours}
                onChange={(e) => setSettings(s => ({
                  ...s,
                  retention_hours: parseInt(e.target.value)
                }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>6 ساعت</span>
                <span>7 روز</span>
              </div>
            </div>
          </div>

          {/* Auto Scroll */}
          <div className="flex items-center justify-between">
            <label className="font-medium">اسکرول خودکار به آخرین لاگ</label>
            <button
              onClick={() => setSettings(s => ({ ...s, auto_scroll: !s.auto_scroll }))}
              className={`w-12 h-6 rounded-full transition ${
                settings.auto_scroll ? 'bg-green-500' : 'bg-gray-300'
              }`}
            >
              <div className={`w-5 h-5 rounded-full bg-white shadow transition transform ${
                settings.auto_scroll ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>

          <button
            onClick={saveSettings}
            className="w-full py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600"
          >
            💾 ذخیره تنظیمات
          </button>
        </div>
      )}
    </div>
  );
}
