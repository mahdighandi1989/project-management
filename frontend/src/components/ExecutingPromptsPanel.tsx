'use client';

import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PromptExecution {
  id: string;
  prompt_id: string;
  prompt_name: string;
  prompt_category: string;
  project_id?: string;
  status: string;
  started_at?: string;
  model_used?: string;
  // 🔴 اطلاعات پیشرفت real-time
  current_step?: string;
  current_progress?: number;
  total_steps?: number;
  current_step_index?: number;
}

interface ExecutingPromptsPanelProps {
  projectId?: string;
  refreshInterval?: number;
  onExecutionComplete?: (execution: PromptExecution) => void;
  compact?: boolean;
}

const categoryIcons: Record<string, string> = {
  health_analysis: '🩺',
  engineering_report: '📊',
  auto_setup: '🚀',
  deep_analysis: '🔬',
  custom: '⚙️'
};

const categoryLabels: Record<string, string> = {
  health_analysis: 'تحلیل سلامت',
  engineering_report: 'گزارش مهندسی',
  auto_setup: 'راه‌اندازی خودکار',
  deep_analysis: 'تحلیل عمیق',
  custom: 'سفارشی'
};

export default function ExecutingPromptsPanel({
  projectId,
  refreshInterval = 2000,
  onExecutionComplete,
  compact = false
}: ExecutingPromptsPanelProps) {
  const [executions, setExecutions] = useState<PromptExecution[]>([]);
  const [previousExecutions, setPreviousExecutions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);

  const fetchExecutions = useCallback(async () => {
    try {
      const url = projectId
        ? `${API_BASE}/api/prompts/executions/active?project_id=${projectId}`
        : `${API_BASE}/api/prompts/executions/active`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const newExecutions = data.executions || [];

        // Check for completed executions
        if (onExecutionComplete) {
          const currentIds = newExecutions.map((e: PromptExecution) => e.id);
          const completedIds = previousExecutions.filter(id => !currentIds.includes(id));
          // Note: We don't have the full execution object here, but we can notify
        }

        setExecutions(newExecutions);
        setPreviousExecutions(newExecutions.map((e: PromptExecution) => e.id));
        setVisible(newExecutions.length > 0);
      }
    } catch (e) {
      console.error('Error fetching executions:', e);
    }
  }, [projectId, previousExecutions, onExecutionComplete]);

  useEffect(() => {
    // Initial fetch
    fetchExecutions();

    // Set up polling
    const interval = setInterval(fetchExecutions, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchExecutions, refreshInterval]);

  // Don't render if no executions
  if (!visible && executions.length === 0) {
    return null;
  }

  // Calculate elapsed time
  const getElapsedTime = (startedAt?: string) => {
    if (!startedAt) return '';
    const start = new Date(startedAt);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);

    if (seconds < 60) return `${seconds} ثانیه`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (compact) {
    return (
      <div className="fixed bottom-4 left-4 z-50 animate-pulse">
        {executions.map((exec) => (
          <div
            key={exec.id}
            className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-500 text-white px-4 py-2 rounded-full shadow-lg mb-2"
          >
            <div className="w-2 h-2 bg-white rounded-full animate-ping" />
            <span className="text-lg">{categoryIcons[exec.prompt_category] || '📝'}</span>
            <span className="text-sm font-medium">{exec.prompt_name}</span>
            <span className="text-xs opacity-75">{getElapsedTime(exec.started_at)}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-purple-200 dark:border-purple-700 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-blue-500 px-4 py-3 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
              <span className="font-bold">پرامپت در حال اجرا</span>
            </div>
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
              {executions.length} فعال
            </span>
          </div>
        </div>

        {/* Executions List */}
        <div className="max-h-64 overflow-y-auto">
          {executions.map((exec, index) => (
            <div
              key={exec.id}
              className={`p-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0 ${
                index === 0 ? 'bg-purple-50 dark:bg-purple-900/20' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Icon with animation */}
                <div className="flex-shrink-0">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl ${
                    index === 0
                      ? 'bg-gradient-to-br from-purple-500 to-blue-500 animate-spin-slow'
                      : 'bg-gray-100 dark:bg-gray-700'
                  }`}>
                    {categoryIcons[exec.prompt_category] || '📝'}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-gray-900 dark:text-white truncate">
                      {exec.prompt_name}
                    </h4>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {getElapsedTime(exec.started_at)}
                    </span>
                  </div>

                  {/* 🔴 نمایش مرحله فعلی */}
                  {exec.current_step && (
                    <div className="mt-1 text-xs text-gray-600 dark:text-gray-300 truncate font-mono">
                      {exec.current_step}
                    </div>
                  )}

                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded">
                      {categoryLabels[exec.prompt_category] || exec.prompt_category}
                    </span>
                    {exec.model_used && (
                      <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded">
                        {exec.model_used}
                      </span>
                    )}
                    {/* 🔴 نمایش شماره مرحله */}
                    {exec.total_steps && exec.total_steps > 0 && (
                      <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded">
                        {exec.current_step_index || 0}/{exec.total_steps}
                      </span>
                    )}
                  </div>

                  {/* 🔴 Progress bar با درصد واقعی */}
                  {index === 0 && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                        <span>پیشرفت</span>
                        <span>{exec.current_progress || 0}%</span>
                      </div>
                      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        {exec.current_progress ? (
                          <div
                            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500"
                            style={{ width: `${exec.current_progress}%` }}
                          />
                        ) : (
                          <div className="h-full bg-gradient-to-r from-purple-500 to-blue-500 animate-progress" />
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900 text-xs text-gray-500 dark:text-gray-400 text-center">
          پرامپت‌ها به ترتیب اجرا می‌شوند
        </div>
      </div>

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes spin-slow {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
        .animate-spin-slow {
          animation: spin-slow 3s linear infinite;
        }
        @keyframes progress {
          0% {
            width: 0%;
            margin-left: 0;
          }
          50% {
            width: 100%;
            margin-left: 0;
          }
          100% {
            width: 0%;
            margin-left: 100%;
          }
        }
        .animate-progress {
          animation: progress 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
