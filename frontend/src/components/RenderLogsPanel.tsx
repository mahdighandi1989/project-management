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
  // Auto transfer settings
  auto_transfer_enabled: boolean;
  auto_transfer_interval_minutes: number;
  auto_transfer_hours_back: number;
  auto_transfer_mode: 'since_deploy' | 'time_based' | 'realtime';
  last_auto_transfer?: string;
}

// Progress interface for SSE transfer
interface TransferProgress {
  type: 'start' | 'progress' | 'log_processed' | 'complete' | 'error' | 'debug';
  total_logs?: number;
  current?: number;
  total?: number;
  status?: string;
  service?: string;
  action?: string;
  transferred?: number;
  merged?: number;
  skipped?: number;
  message?: string;
  force?: boolean;
  debug?: {
    total_logs_in_period?: number;
    error_logs_in_period?: number;
    already_transferred?: number | string;
    services_count?: number;
    projects_count?: number;
    period_hours?: number;
    hint?: string;
    error?: string;
  };
  mappings?: string[];
}

interface LogStats {
  total_logs: number;
  by_level: Record<string, number>;
  by_service: { service_id: string; service_name: string; count: number }[];
  error_count: number;
  warning_count: number;
}

interface LogArchive {
  id: number;
  service_id: string;
  start_time: string;
  end_time: string;
  logs_count: number;
  size_bytes: number;
  archived_at: string;
}

interface ArchivedLog {
  timestamp: string;
  level: string;
  message: string;
  deploy_id?: string;
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
    auto_transfer_enabled: false,
    auto_transfer_interval_minutes: 30,
    auto_transfer_hours_back: 24,
    auto_transfer_mode: 'since_deploy',
  });

  // Filters
  const [selectedServices, setSelectedServices] = useState<string[]>([]); // Multi-select services
  const [selectedLevels, setSelectedLevels] = useState<string[]>(['info', 'warn', 'error']);
  const [searchTerm, setSearchTerm] = useState('');
  const [timeRange, setTimeRange] = useState(30); // minutes

  // Download modal
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [downloadOptions, setDownloadOptions] = useState({
    type: 'time_range' as 'time_range' | 'count' | 'level' | 'after_deploy',
    timeRangeHours: 24,
    logCount: 1000,
    logLevel: 'error',
    format: 'json' as 'json' | 'txt' | 'csv',
  });

  // Transfer to issues
  const [transferStatus, setTransferStatus] = useState<{
    pending_errors: number;
    transferred_errors: number;
    can_transfer: boolean;
  } | null>(null);
  const [transferring, setTransferring] = useState(false);
  const [transferProgress, setTransferProgress] = useState<TransferProgress | null>(null);
  const [forceTransfer, setForceTransfer] = useState(false);
  const [transferAbortController, setTransferAbortController] = useState<AbortController | null>(null);
  const [transferPaused, setTransferPaused] = useState(false);

  // Service-Project Mapping State
  const [serviceMappings, setServiceMappings] = useState<{
    mapped: any[];
    unmapped: any[];
    projects: { id: string; name: string }[];
  } | null>(null);
  const [loadingMappings, setLoadingMappings] = useState(false);

  // Archive State
  const [archives, setArchives] = useState<LogArchive[]>([]);
  const [selectedArchive, setSelectedArchive] = useState<number | null>(null);
  const [archivedLogs, setArchivedLogs] = useState<ArchivedLog[]>([]);
  const [loadingArchive, setLoadingArchive] = useState(false);

  // UI State
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState<'live' | 'settings' | 'stats' | 'archive'>('live');
  const [isPolling, setIsPolling] = useState(false);

  // Refs
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastTimestampRef = useRef<string | null>(null);
  const isInitializedRef = useRef(false); // 🆕 برای جلوگیری از بارگذاری مجدد در اولین render

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

  // 🆕 بارگذاری مجدد لاگ‌ها وقتی فیلترها تغییر می‌کنند
  useEffect(() => {
    // در اولین render کاری نکن (loadInitialData خودش لاگ‌ها را بارگذاری می‌کند)
    if (!isInitializedRef.current) {
      return;
    }
    // وقتی فیلتر تغییر کرد، لاگ‌ها را مجدداً بارگذاری کن
    loadLogs();
  }, [selectedLevels, selectedServices, timeRange]);

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
        loadTransferStatus(),
      ]);
      await fetchNewLogs();
      await loadLogs();
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setLoading(false);
      isInitializedRef.current = true; // 🆕 علامت‌گذاری که بارگذاری اولیه انجام شد
    }
  };

  const loadServices = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/services`);
      const data = await res.json();

      if (res.ok && data.services && data.services.length > 0) {
        setServices(data.services);
      } else {
        // اگر سرویسی نبود، سعی کن از API بگیری
        console.log('No services in cache, trying to refresh from API...');
        await refreshServicesQuietly();
      }
    } catch (e) {
      console.error('Error loading services:', e);
      // در صورت خطا هم سعی کن refresh کنی
      await refreshServicesQuietly();
    }
  };

  const refreshServicesQuietly = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/services/refresh`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        if (data.services && data.services.length > 0) {
          setServices(data.services);
        }
      }
    } catch (e) {
      console.error('Error refreshing services:', e);
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

  const loadArchives = async () => {
    try {
      const params = new URLSearchParams();
      selectedServices.forEach(sid => {
        params.append('service_ids', sid);
      });
      const res = await fetch(`${API_BASE}/api/render/archives?${params}`);
      if (res.ok) {
        const data = await res.json();
        setArchives(data.archives || []);
      }
    } catch (e) {
      console.error('Error loading archives:', e);
    }
  };

  const loadArchiveContent = async (archiveId: number) => {
    setLoadingArchive(true);
    setSelectedArchive(archiveId);
    try {
      const res = await fetch(`${API_BASE}/api/render/archives/${archiveId}`);
      if (res.ok) {
        const data = await res.json();
        setArchivedLogs(data.logs || []);
      } else {
        showError('خطا در بارگذاری محتوای آرشیو');
      }
    } catch (e) {
      console.error('Error loading archive content:', e);
      showError('خطا در ارتباط با سرور');
    } finally {
      setLoadingArchive(false);
    }
  };

  const triggerCleanup = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/cleanup?retention_hours=${settings.retention_hours}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        showSuccess(data.message || 'پاکسازی انجام شد');
        await loadArchives();
      } else {
        showError('خطا در پاکسازی');
      }
    } catch (e) {
      showError('خطا در ارتباط با سرور');
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDateTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('fa-IR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const loadLogs = async () => {
    try {
      const params = new URLSearchParams({
        minutes: timeRange.toString(),
        limit: '500',
        level: selectedLevels.join(','),
      });

      // Add multiple service IDs
      selectedServices.forEach(sid => {
        params.append('service_ids', sid);
      });

      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const res = await fetch(`${API_BASE}/api/render/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        // Reverse to show oldest first, newest at bottom
        const reversedLogs = (data.logs || []).reverse();
        setLogs(reversedLogs);
        if (reversedLogs.length > 0) {
          lastTimestampRef.current = reversedLogs[reversedLogs.length - 1].timestamp;
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
      if (selectedServices.length === 1) {
        params.service_id = selectedServices[0];
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
        }
        await loadLogs();
      }
    } catch (e) {
      console.error('Error fetching new logs:', e);
    } finally {
      setFetching(false);
    }
  };

  const toggleService = (serviceId: string) => {
    setSelectedServices(prev =>
      prev.includes(serviceId)
        ? prev.filter(id => id !== serviceId)
        : [...prev, serviceId]
    );
  };

  const selectAllServices = () => {
    setSelectedServices(services.map(s => s.id));
  };

  const clearServiceSelection = () => {
    setSelectedServices([]);
  };

  const downloadLogs = async () => {
    try {
      const params = new URLSearchParams();

      // Add selected services
      selectedServices.forEach(sid => {
        params.append('service_ids', sid);
      });

      switch (downloadOptions.type) {
        case 'time_range':
          params.append('hours', downloadOptions.timeRangeHours.toString());
          break;
        case 'count':
          params.append('limit', downloadOptions.logCount.toString());
          break;
        case 'level':
          params.append('level', downloadOptions.logLevel);
          break;
        case 'after_deploy':
          params.append('after_deploy', 'true');
          break;
      }

      params.append('format', downloadOptions.format);

      const res = await fetch(`${API_BASE}/api/render/logs/download?${params}`);
      if (res.ok) {
        const contentType = res.headers.get('content-type');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `render-logs-${new Date().toISOString().slice(0, 10)}.${downloadOptions.format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        setShowDownloadModal(false);
        showSuccess('لاگ‌ها دانلود شد');
      } else {
        showError('خطا در دانلود لاگ‌ها');
      }
    } catch (e) {
      console.error('Error downloading logs:', e);
      showError('خطا در ارتباط با سرور');
    }
  };

  const loadTransferStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/render/transfer-status`);
      if (res.ok) {
        const data = await res.json();
        setTransferStatus(data);
      }
    } catch (e) {
      console.error('Error loading transfer status:', e);
    }
  };

  // بارگذاری نگاشت سرویس‌ها به پروژه‌ها
  const loadServiceMappings = async () => {
    setLoadingMappings(true);
    try {
      const res = await fetch(`${API_BASE}/api/render/services/mappings`);
      if (res.ok) {
        const data = await res.json();
        setServiceMappings({
          mapped: data.mapped || [],
          unmapped: data.unmapped || [],
          projects: data.projects || []
        });
      }
    } catch (e) {
      console.error('Error loading service mappings:', e);
    } finally {
      setLoadingMappings(false);
    }
  };

  // بروزرسانی نگاشت سرویس به پروژه
  const updateServiceMapping = async (serviceId: string, projectId: string | null) => {
    try {
      const res = await fetch(`${API_BASE}/api/render/services/${serviceId}?project_id=${projectId || ''}`, {
        method: 'PATCH'
      });
      if (res.ok) {
        showSuccess('نگاشت سرویس بروزرسانی شد');
        loadServiceMappings(); // بارگذاری مجدد
      } else {
        const data = await res.json();
        showError(data.detail || 'خطا در بروزرسانی نگاشت');
      }
    } catch (e) {
      console.error('Error updating service mapping:', e);
      showError('خطا در ارتباط با سرور');
    }
  };

  const transferErrorsToIssues = async () => {
    setTransferring(true);
    setTransferProgress(null);
    setTransferPaused(false);

    // ایجاد AbortController برای امکان لغو
    const abortController = new AbortController();
    setTransferAbortController(abortController);

    try {
      const params = new URLSearchParams();
      selectedServices.forEach(sid => {
        params.append('service_ids', sid);
      });
      params.append('hours', '24');
      params.append('mode', settings.auto_transfer_mode || 'since_deploy');
      if (forceTransfer) {
        params.append('force', 'true');
      }

      // استفاده از SSE برای نمایش پیشرفت لحظه‌ای
      const response = await fetch(`${API_BASE}/api/render/transfer-errors-stream?${params}`, {
        method: 'POST',
        signal: abortController.signal,
      });

      if (!response.ok) {
        const err = await response.json();
        showError(err.detail || 'خطا در انتقال');
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        showError('خطا در دریافت پاسخ');
        return;
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // بررسی لغو
        if (abortController.signal.aborted) {
          reader.cancel();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: TransferProgress = JSON.parse(line.slice(6));
              setTransferProgress(data);

              if (data.type === 'complete') {
                const msg = data.message || `✅ ${data.transferred} خطا منتقل شد، ${data.merged} ادغام شد`;
                showSuccess(msg);
                // بروزرسانی آمار بعد از اتمام
                await loadTransferStatus();
                await loadStats();
              } else if (data.type === 'error') {
                showError(data.message || 'خطا در انتقال');
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        showSuccess('انتقال متوقف شد');
        // هنوز آمار را بروزرسانی کن
        await loadTransferStatus();
        await loadStats();
      } else {
        console.error('Error transferring errors:', e);
        showError('خطا در ارتباط با سرور');
      }
    } finally {
      setTransferring(false);
      setTransferAbortController(null);
      setTransferPaused(false);
      // پاک کردن پیشرفت بعد از 5 ثانیه (بیشتر برای دیدن نتیجه)
      setTimeout(() => setTransferProgress(null), 5000);
    }
  };

  // توقف انتقال
  const stopTransfer = () => {
    if (transferAbortController) {
      transferAbortController.abort();
      setTransferAbortController(null);
    }
  };

  const pollForNewLogs = useCallback(async () => {
    try {
      // First, fetch new logs from Render API and save to DB
      const fetchParams: Record<string, string> = { limit: '50' };
      if (selectedServices.length === 1) {
        fetchParams.service_id = selectedServices[0];
      }

      await fetch(`${API_BASE}/api/render/logs/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fetchParams),
      });

      // Then, get the latest logs from database
      const params = new URLSearchParams({
        minutes: timeRange.toString(),
        limit: '500',
        level: selectedLevels.join(','),
      });

      // Add multiple service IDs
      selectedServices.forEach(sid => {
        params.append('service_ids', sid);
      });

      const res = await fetch(`${API_BASE}/api/render/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        if (data.logs) {
          // Reverse to show oldest first, newest at bottom
          setLogs(data.logs.reverse());
          if (data.logs.length > 0) {
            lastTimestampRef.current = data.logs[data.logs.length - 1].timestamp;
          }
        }
      }
    } catch (e) {
      console.error('Error polling logs:', e);
    }
  }, [selectedServices, selectedLevels, timeRange]);

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
        <button
          onClick={() => {
            setActiveTab('archive');
            loadArchives();
          }}
          className={`px-4 py-2 rounded-t-lg font-medium ${
            activeTab === 'archive'
              ? 'bg-amber-500 text-white'
              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200'
          }`}
        >
          📦 آرشیو
        </button>
      </div>

      {activeTab === 'live' && (
        <>
          {/* فیلترها */}
          <div className="space-y-3 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            {/* ردیف اول: انتخاب سرویس‌ها */}
            <div className="flex flex-wrap items-start gap-3">
              <label className="text-sm font-medium pt-2">سرویس‌ها:</label>
              <div className="flex flex-wrap gap-2 flex-1">
                {services.length === 0 ? (
                  <div className="flex items-center gap-2 text-gray-500 text-sm">
                    <span>هیچ سرویسی یافت نشد.</span>
                    <button
                      onClick={refreshServices}
                      disabled={fetching}
                      className="text-blue-500 hover:underline"
                    >
                      {fetching ? 'در حال بارگذاری...' : 'بروزرسانی از Render'}
                    </button>
                  </div>
                ) : (
                  services.map(s => (
                    <button
                      key={s.id}
                      onClick={() => {
                        toggleService(s.id);
                        setTimeout(loadLogs, 100);
                      }}
                      className={`px-3 py-1 rounded text-sm border transition ${
                        selectedServices.includes(s.id)
                          ? 'bg-blue-500 text-white border-blue-600'
                          : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {s.name}
                    </button>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { selectAllServices(); setTimeout(loadLogs, 100); }}
                  className="px-3 py-1 text-xs bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300"
                >
                  انتخاب همه
                </button>
                <button
                  onClick={() => { clearServiceSelection(); setTimeout(loadLogs, 100); }}
                  className="px-3 py-1 text-xs bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300"
                >
                  پاک کردن
                </button>
                <button
                  onClick={refreshServices}
                  disabled={fetching}
                  className="px-3 py-1 text-xs text-blue-500 hover:bg-blue-50 rounded"
                  title="بروزرسانی لیست سرویس‌ها"
                >
                  🔄
                </button>
              </div>
            </div>

            {/* ردیف دوم: سطوح، بازه، جستجو و دکمه‌ها */}
            <div className="flex flex-wrap gap-3 items-center">
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
                  onClick={() => isPolling ? stopPolling() : startPolling()}
                  className={`px-4 py-2 rounded ${
                    isPolling
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-200 dark:bg-gray-600'
                  }`}
                >
                  {isPolling ? '⏸️ توقف' : '▶️ زنده'}
                </button>
                <button
                  onClick={() => setShowDownloadModal(true)}
                  className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
                >
                  📥 دانلود
                </button>
                <div className="flex items-center gap-2">
                  {transferring ? (
                    <button
                      onClick={stopTransfer}
                      className="px-4 py-2 rounded bg-orange-500 text-white hover:bg-orange-600"
                      title="توقف انتقال"
                    >
                      ⏹️ توقف
                    </button>
                  ) : (
                    <button
                      onClick={transferErrorsToIssues}
                      disabled={!transferStatus?.can_transfer && !forceTransfer}
                      className={`px-4 py-2 rounded ${
                        (transferStatus?.can_transfer || forceTransfer)
                          ? 'bg-red-500 text-white hover:bg-red-600'
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                      title="انتقال خطاها به تب ایرادات پروژه‌ها"
                    >
                      🚨 انتقال خطاها ({transferStatus?.pending_errors || 0})
                    </button>
                  )}
                  <label
                    className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer"
                    title="انتقال مجدد لاگ‌هایی که قبلاً منتقل شده‌اند"
                  >
                    <input
                      type="checkbox"
                      checked={forceTransfer}
                      onChange={(e) => setForceTransfer(e.target.checked)}
                      className="w-3 h-3"
                      disabled={transferring}
                    />
                    اجباری
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* نمایش پیشرفت انتقال */}
          {transferProgress && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-3">
                {transferProgress.type === 'complete' ? (
                  <span className="text-2xl">✅</span>
                ) : transferProgress.type === 'error' ? (
                  <span className="text-2xl">❌</span>
                ) : (
                  <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full" />
                )}
                <div className="flex-1">
                  <div className="font-medium text-blue-800 dark:text-blue-200">
                    {transferProgress.status || transferProgress.message || 'در حال پردازش...'}
                  </div>
                  {transferProgress.current !== undefined && transferProgress.total !== undefined && (
                    <div className="mt-2">
                      <div className="flex justify-between text-sm text-blue-600 dark:text-blue-300 mb-1">
                        <span>{transferProgress.current} از {transferProgress.total}</span>
                        <span>{Math.round((transferProgress.current / transferProgress.total) * 100)}%</span>
                      </div>
                      <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${(transferProgress.current / transferProgress.total) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {transferProgress.service && (
                    <div className="text-sm text-blue-500 dark:text-blue-400 mt-1">
                      سرویس: {transferProgress.service}
                    </div>
                  )}
                  {/* نمایش اطلاعات دیباگ */}
                  {transferProgress.debug && (
                    <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded text-sm">
                      <div className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">🔍 اطلاعات دیباگ:</div>
                      <div className="grid grid-cols-2 gap-2 text-yellow-700 dark:text-yellow-300">
                        <div>کل لاگ‌ها ({transferProgress.debug.period_hours}h): {transferProgress.debug.total_logs_in_period}</div>
                        <div>لاگ‌های خطا: {transferProgress.debug.error_logs_in_period}</div>
                        <div>منتقل شده قبلی: {transferProgress.debug.already_transferred}</div>
                        <div>تعداد سرویس‌ها: {transferProgress.debug.services_count}</div>
                        <div>تعداد پروژه‌ها: {transferProgress.debug.projects_count}</div>
                      </div>
                      {transferProgress.debug.hint && (
                        <div className="mt-2 text-yellow-600 dark:text-yellow-400 text-xs">
                          💡 {transferProgress.debug.hint}
                        </div>
                      )}
                    </div>
                  )}
                  {/* نمایش mappings */}
                  {transferProgress.mappings && transferProgress.mappings.length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      نگاشت: {transferProgress.mappings.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

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

          {/* Auto Transfer to Issues */}
          <div className="border-t pt-6 mt-6">
            <h4 className="font-bold text-lg mb-4 flex items-center gap-2">
              🚨 انتقال خودکار خطاها به ایرادات
            </h4>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="font-medium">فعال‌سازی انتقال خودکار</label>
                <button
                  onClick={() => setSettings(s => ({ ...s, auto_transfer_enabled: !s.auto_transfer_enabled }))}
                  className={`w-12 h-6 rounded-full transition ${
                    settings.auto_transfer_enabled ? 'bg-red-500' : 'bg-gray-300'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full bg-white shadow transition transform ${
                    settings.auto_transfer_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </div>

              {/* حالت انتقال */}
              <div>
                <label className="block text-sm font-medium mb-2">حالت انتقال</label>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => setSettings(s => ({ ...s, auto_transfer_mode: 'since_deploy' }))}
                    className={`flex-1 min-w-[120px] px-3 py-2 rounded-lg text-sm transition ${
                      settings.auto_transfer_mode === 'since_deploy'
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                    }`}
                    disabled={!settings.auto_transfer_enabled}
                  >
                    🚀 از آخرین دیپلوی
                  </button>
                  <button
                    onClick={() => setSettings(s => ({ ...s, auto_transfer_mode: 'time_based' }))}
                    className={`flex-1 min-w-[120px] px-3 py-2 rounded-lg text-sm transition ${
                      settings.auto_transfer_mode === 'time_based'
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                    }`}
                    disabled={!settings.auto_transfer_enabled}
                  >
                    ⏰ بازه زمانی
                  </button>
                  <button
                    onClick={() => setSettings(s => ({ ...s, auto_transfer_mode: 'realtime' }))}
                    className={`flex-1 min-w-[120px] px-3 py-2 rounded-lg text-sm transition ${
                      settings.auto_transfer_mode === 'realtime'
                        ? 'bg-orange-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                    }`}
                    disabled={!settings.auto_transfer_enabled}
                  >
                    ⚡ لحظه‌ای
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {settings.auto_transfer_mode === 'since_deploy'
                    ? '✨ خطاهای بعد از آخرین دیپلوی هر سرویس منتقل می‌شوند (پیشنهادی)'
                    : settings.auto_transfer_mode === 'realtime'
                    ? '⚡ هر خطا فوراً پس از دریافت منتقل می‌شود (بدون اینتروال)'
                    : 'خطاهای X ساعت گذشته منتقل می‌شوند'}
                </p>
              </div>

              {/* فقط در حالت‌های غیر realtime نمایش داده شود */}
              {settings.auto_transfer_mode !== 'realtime' && (
                <div>
                  <label className="block text-sm mb-2">
                    فاصله بررسی: هر {settings.auto_transfer_interval_minutes} دقیقه
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="120"
                    step="5"
                    value={settings.auto_transfer_interval_minutes}
                    onChange={(e) => setSettings(s => ({
                      ...s,
                      auto_transfer_interval_minutes: parseInt(e.target.value)
                    }))}
                    className="w-full"
                    disabled={!settings.auto_transfer_enabled}
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>5 دقیقه</span>
                    <span>2 ساعت</span>
                  </div>
                </div>
              )}

              {/* فقط در حالت time_based نمایش داده شود */}
              {settings.auto_transfer_mode === 'time_based' && (
                <div>
                  <label className="block text-sm mb-2">
                    بازه زمانی بررسی: {settings.auto_transfer_hours_back} ساعت گذشته
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="72"
                    step="1"
                    value={settings.auto_transfer_hours_back}
                    onChange={(e) => setSettings(s => ({
                      ...s,
                      auto_transfer_hours_back: parseInt(e.target.value)
                    }))}
                    className="w-full"
                    disabled={!settings.auto_transfer_enabled}
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>1 ساعت</span>
                    <span>3 روز</span>
                  </div>
                </div>
              )}

              {settings.last_auto_transfer && (
                <div className="text-sm text-gray-500 bg-gray-100 dark:bg-gray-700 p-3 rounded">
                  آخرین انتقال خودکار: {new Date(settings.last_auto_transfer).toLocaleString('fa-IR')}
                </div>
              )}

              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm">
                <p className="font-medium mb-2">توضیحات:</p>
                <ul className="text-gray-600 dark:text-gray-300 space-y-1 list-disc list-inside">
                  <li>خطاهای لاگ به صورت خودکار به تب ایرادات پروژه‌های مرتبط منتقل می‌شوند</li>
                  <li>AI توضیح علت خطا و راه‌حل پیشنهادی را تولید می‌کند</li>
                  <li>خطاهای تکراری با ایرادات موجود ادغام می‌شوند</li>
                  <li>فقط پروژه‌های ایمپورت شده پشتیبانی می‌شوند</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 🆕 نگاشت سرویس‌ها به پروژه‌ها */}
          <div className="border-t pt-6 mt-6">
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-bold text-lg flex items-center gap-2">
                🔗 نگاشت سرویس‌ها به پروژه‌ها
              </h4>
              <button
                onClick={loadServiceMappings}
                disabled={loadingMappings}
                className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
              >
                {loadingMappings ? '...' : '🔄 بارگذاری'}
              </button>
            </div>

            {serviceMappings ? (
              <div className="space-y-4">
                {/* سرویس‌های بدون نگاشت */}
                {serviceMappings.unmapped.length > 0 && (
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                    <h5 className="font-medium text-yellow-800 dark:text-yellow-200 mb-3">
                      ⚠️ سرویس‌های بدون نگاشت ({serviceMappings.unmapped.length})
                    </h5>
                    <div className="space-y-2">
                      {serviceMappings.unmapped.map(service => (
                        <div key={service.service_id} className="flex items-center gap-3 bg-white dark:bg-gray-800 p-2 rounded">
                          <span className="font-mono text-sm flex-1">{service.service_name}</span>
                          <select
                            onChange={(e) => updateServiceMapping(service.service_id, e.target.value)}
                            className="px-2 py-1 border rounded text-sm dark:bg-gray-700"
                            defaultValue=""
                          >
                            <option value="">انتخاب پروژه...</option>
                            {serviceMappings.projects.map(p => (
                              <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* سرویس‌های نگاشت شده */}
                {serviceMappings.mapped.length > 0 && (
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <h5 className="font-medium text-green-800 dark:text-green-200 mb-3">
                      ✅ سرویس‌های نگاشت شده ({serviceMappings.mapped.length})
                    </h5>
                    <div className="space-y-2">
                      {serviceMappings.mapped.map(service => (
                        <div key={service.service_id} className="flex items-center gap-3 bg-white dark:bg-gray-800 p-2 rounded">
                          <span className="font-mono text-sm flex-1">{service.service_name}</span>
                          <span className="text-xs text-gray-500">
                            {service.mapping_type === 'manual' ? '🔧 دستی' : '🤖 خودکار'}
                          </span>
                          <select
                            value={service.project_id || ''}
                            onChange={(e) => updateServiceMapping(service.service_id, e.target.value || null)}
                            className="px-2 py-1 border rounded text-sm dark:bg-gray-700"
                          >
                            <option value="">بدون پروژه</option>
                            {serviceMappings.projects.map(p => (
                              <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {serviceMappings.mapped.length === 0 && serviceMappings.unmapped.length === 0 && (
                  <div className="text-center text-gray-500 py-4">
                    هیچ سرویسی یافت نشد
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-4">
                برای مشاهده نگاشت‌ها کلیک کنید «بارگذاری»
              </div>
            )}
          </div>

          <button
            onClick={saveSettings}
            className="w-full py-3 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600"
          >
            💾 ذخیره تنظیمات
          </button>
        </div>
      )}

      {activeTab === 'archive' && (
        <div className="space-y-4">
          {/* هدر آرشیو */}
          <div className="flex flex-wrap gap-3 items-center bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-2 flex-wrap">
              <label className="text-sm font-medium">سرویس:</label>
              {services.map(s => (
                <button
                  key={s.id}
                  onClick={() => {
                    toggleService(s.id);
                    setTimeout(loadArchives, 100);
                  }}
                  className={`px-3 py-1 rounded text-sm border ${
                    selectedServices.includes(s.id)
                      ? 'bg-amber-500 text-white border-amber-600'
                      : 'bg-white dark:bg-gray-700 border-gray-300'
                  }`}
                >
                  {s.name}
                </button>
              ))}
            </div>

            <div className="flex-1"></div>

            <button
              onClick={loadArchives}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              🔄 بروزرسانی لیست
            </button>

            <button
              onClick={triggerCleanup}
              className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600"
            >
              🗂️ آرشیو لاگ‌های قدیمی
            </button>
          </div>

          {/* لیست آرشیوها و محتوا */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* لیست آرشیوها */}
            <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl shadow p-4 max-h-[600px] overflow-y-auto">
              <h3 className="font-bold mb-4 flex items-center gap-2">
                📦 آرشیوها
                <span className="text-sm font-normal text-gray-500">
                  ({archives.length} مورد)
                </span>
              </h3>

              {archives.length === 0 ? (
                <div className="text-gray-500 text-center py-8">
                  <div className="text-4xl mb-2">📭</div>
                  <p>هیچ آرشیوی یافت نشد</p>
                  <p className="text-sm mt-2">
                    لاگ‌های قدیمی به صورت خودکار یا با دکمه "آرشیو لاگ‌های قدیمی" آرشیو می‌شوند
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {archives.map(archive => (
                    <button
                      key={archive.id}
                      onClick={() => loadArchiveContent(archive.id)}
                      className={`w-full text-right p-3 rounded-lg border transition ${
                        selectedArchive === archive.id
                          ? 'bg-amber-100 dark:bg-amber-900 border-amber-500'
                          : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-sm">
                          {formatDateTime(archive.start_time)}
                        </span>
                        <span className="text-xs bg-blue-100 dark:bg-blue-900 px-2 py-0.5 rounded">
                          {archive.logs_count} لاگ
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 flex justify-between">
                        <span>تا {formatDateTime(archive.end_time)}</span>
                        <span>{formatBytes(archive.size_bytes)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* محتوای آرشیو */}
            <div className="lg:col-span-2 bg-gray-900 rounded-xl p-4 max-h-[600px] overflow-y-auto font-mono text-sm" dir="ltr">
              {loadingArchive ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin text-4xl">🔄</div>
                  <span className="mr-2 text-gray-400">در حال بارگذاری...</span>
                </div>
              ) : selectedArchive === null ? (
                <div className="text-gray-500 text-center py-12">
                  <div className="text-4xl mb-2">👈</div>
                  <p>یک آرشیو را از لیست انتخاب کنید</p>
                </div>
              ) : archivedLogs.length === 0 ? (
                <div className="text-gray-500 text-center py-12">
                  <div className="text-4xl mb-2">📭</div>
                  <p>این آرشیو خالی است</p>
                </div>
              ) : (
                <>
                  <div className="sticky top-0 bg-gray-800 p-2 mb-2 rounded text-gray-400 text-xs">
                    نمایش {archivedLogs.length} لاگ از آرشیو #{selectedArchive}
                  </div>
                  {archivedLogs.map((log, idx) => (
                    <div
                      key={idx}
                      className="flex gap-2 py-1 hover:bg-gray-800 rounded px-2"
                    >
                      <span className="text-gray-500 shrink-0">
                        {formatTime(log.timestamp)}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs shrink-0 ${getLevelColor(log.level)}`}>
                        {log.level.toUpperCase()}
                      </span>
                      <span className={`flex-1 ${
                        log.level === 'error' ? 'text-red-400' :
                        log.level === 'warn' ? 'text-yellow-400' :
                        'text-gray-300'
                      }`}>
                        {log.message}
                      </span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          {/* راهنما */}
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <h4 className="font-bold mb-2 flex items-center gap-2">
              💡 درباره آرشیو لاگ‌ها
            </h4>
            <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1 list-disc list-inside">
              <li>لاگ‌های قدیمی‌تر از {settings.retention_hours} ساعت به صورت خودکار آرشیو می‌شوند</li>
              <li>آرشیوها فشرده شده (gzip) ذخیره می‌شوند تا فضای کمتری اشغال کنند</li>
              <li>می‌توانید با دکمه "آرشیو لاگ‌های قدیمی" به صورت دستی آرشیو کنید</li>
              <li>آرشیوها تا {settings.archive_enabled ? '30 روز' : 'غیرفعال'} نگهداری می‌شوند</li>
            </ul>
          </div>
        </div>
      )}

      {/* Download Modal */}
      {showDownloadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
              📥 دانلود لاگ‌ها
            </h3>

            {/* انتخاب نوع فیلتر */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">نوع انتخاب:</label>
                <select
                  value={downloadOptions.type}
                  onChange={(e) => setDownloadOptions(prev => ({
                    ...prev,
                    type: e.target.value as any
                  }))}
                  className="w-full p-2 border rounded dark:bg-gray-700"
                >
                  <option value="time_range">بازه زمانی</option>
                  <option value="count">تعداد لاگ اخیر</option>
                  <option value="level">نوع لاگ</option>
                  <option value="after_deploy">بعد از آخرین دیپلوی</option>
                </select>
              </div>

              {downloadOptions.type === 'time_range' && (
                <div>
                  <label className="block text-sm font-medium mb-2">
                    بازه زمانی: {downloadOptions.timeRangeHours} ساعت
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="168"
                    value={downloadOptions.timeRangeHours}
                    onChange={(e) => setDownloadOptions(prev => ({
                      ...prev,
                      timeRangeHours: parseInt(e.target.value)
                    }))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>1 ساعت</span>
                    <span>7 روز</span>
                  </div>
                </div>
              )}

              {downloadOptions.type === 'count' && (
                <div>
                  <label className="block text-sm font-medium mb-2">تعداد لاگ:</label>
                  <input
                    type="number"
                    min="100"
                    max="10000"
                    step="100"
                    value={downloadOptions.logCount}
                    onChange={(e) => setDownloadOptions(prev => ({
                      ...prev,
                      logCount: parseInt(e.target.value)
                    }))}
                    className="w-full p-2 border rounded dark:bg-gray-700"
                  />
                </div>
              )}

              {downloadOptions.type === 'level' && (
                <div>
                  <label className="block text-sm font-medium mb-2">سطح لاگ:</label>
                  <select
                    value={downloadOptions.logLevel}
                    onChange={(e) => setDownloadOptions(prev => ({
                      ...prev,
                      logLevel: e.target.value
                    }))}
                    className="w-full p-2 border rounded dark:bg-gray-700"
                  >
                    <option value="error">فقط خطاها (error)</option>
                    <option value="warn">خطا و هشدار (error + warn)</option>
                    <option value="info">همه لاگ‌ها</option>
                  </select>
                </div>
              )}

              {downloadOptions.type === 'after_deploy' && (
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                  تمام لاگ‌های بعد از آخرین دیپلوی موفق سرویس‌های انتخاب شده دانلود می‌شود.
                </div>
              )}

              {/* فرمت خروجی */}
              <div>
                <label className="block text-sm font-medium mb-2">فرمت خروجی:</label>
                <div className="flex gap-2">
                  {['json', 'txt', 'csv'].map(fmt => (
                    <button
                      key={fmt}
                      onClick={() => setDownloadOptions(prev => ({ ...prev, format: fmt as any }))}
                      className={`flex-1 py-2 rounded border ${
                        downloadOptions.format === fmt
                          ? 'bg-purple-500 text-white border-purple-600'
                          : 'bg-white dark:bg-gray-700 border-gray-300'
                      }`}
                    >
                      {fmt.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {/* سرویس‌های انتخاب شده */}
              <div className="text-sm text-gray-600 dark:text-gray-400">
                سرویس‌های انتخاب شده: {
                  selectedServices.length === 0
                    ? 'همه سرویس‌ها'
                    : selectedServices.length === 1
                    ? services.find(s => s.id === selectedServices[0])?.name
                    : `${selectedServices.length} سرویس`
                }
              </div>
            </div>

            {/* دکمه‌ها */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowDownloadModal(false)}
                className="flex-1 py-2 bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300"
              >
                انصراف
              </button>
              <button
                onClick={downloadLogs}
                className="flex-1 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
              >
                📥 دانلود
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
