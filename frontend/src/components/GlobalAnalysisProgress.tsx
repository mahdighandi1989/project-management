'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface AnalysisProgress {
  project_id: string;
  project_name?: string;
  status: string;
  phase: string;
  percentage: number;
  analyzed_files: number;
  total_files: number;
  message: string;
  can_resume: boolean;
}

export default function GlobalAnalysisProgress() {
  const [activeAnalyses, setActiveAnalyses] = useState<AnalysisProgress[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    // Poll for active analyses every 3 seconds
    const checkActiveAnalyses = async () => {
      try {
        // Get list of projects
        const projectsRes = await fetch(`${API_BASE}/api/projects`);
        if (!projectsRes.ok) return;

        const projectsData = await projectsRes.json();
        const projects = projectsData.projects || [];

        // Check progress for each project
        const activeList: AnalysisProgress[] = [];

        for (const project of projects.slice(0, 10)) { // Limit to 10 projects
          // Skip if project has no valid id
          if (!project || !project.id) continue;

          try {
            const progressRes = await fetch(`${API_BASE}/api/projects/${project.id}/health/progress`);
            if (progressRes.ok) {
              const data = await progressRes.json();
              const progress = data.progress;

              if (progress.status === 'running' || progress.status === 'paused') {
                activeList.push({
                  project_id: project.id,
                  project_name: project.name,
                  status: progress.status,
                  phase: progress.phase || 'preparing',
                  percentage: progress.percentage || 0,
                  analyzed_files: progress.analyzed_files || 0,
                  total_files: progress.total_files || 0,
                  message: progress.message || '',
                  can_resume: progress.can_resume || false,
                });
              }
            }
          } catch (e) {
            // Ignore individual project errors
          }
        }

        setActiveAnalyses(activeList);
      } catch (e) {
        console.error('Error checking active analyses:', e);
      }
    };

    // Initial check
    checkActiveAnalyses();

    // Poll every 3 seconds
    const interval = setInterval(checkActiveAnalyses, 3000);

    return () => clearInterval(interval);
  }, []);

  if (activeAnalyses.length === 0) {
    return null;
  }

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
      {/* Summary bar */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="cursor-pointer bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl p-3 text-white"
      >
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="animate-pulse">
              {activeAnalyses.some(a => a.status === 'running') ? '🔄' : '⏸️'}
            </span>
            <span className="text-sm font-medium">
              {activeAnalyses.length} تحلیل در جریان
            </span>
          </div>
          <span className="text-xs">{expanded ? '▼' : '▲'}</span>
        </div>

        {/* Progress bars */}
        <div className="space-y-1">
          {activeAnalyses.slice(0, expanded ? undefined : 1).map((analysis) => (
            <div key={analysis.project_id}>
              <div className="flex justify-between text-xs mb-0.5">
                <span className="truncate max-w-[70%]">{analysis.project_name || 'پروژه'}</span>
                <span>{analysis.percentage.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    analysis.status === 'paused' ? 'bg-yellow-400' : 'bg-white'
                  }`}
                  style={{ width: `${analysis.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-2 space-y-2">
          {activeAnalyses.map((analysis) => (
            <Link
              key={analysis.project_id}
              href={`/projects/${analysis.project_id}`}
              className="block p-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{analysis.project_name}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {analysis.phase === 'micro' && 'بررسی فایل‌ها'}
                    {analysis.phase === 'macro' && 'بررسی همکاری‌ها'}
                    {analysis.phase === 'structural' && 'بررسی ساختار'}
                    {analysis.phase === 'preparing' && 'آماده‌سازی'}
                    {' - '}
                    {analysis.analyzed_files}/{analysis.total_files} فایل
                  </div>
                </div>
                <div className="text-left">
                  <div className={`text-sm font-bold ${
                    analysis.status === 'paused' ? 'text-yellow-500' : 'text-blue-500'
                  }`}>
                    {analysis.percentage.toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-400">
                    {analysis.status === 'paused' ? '⏸️ متوقف' : '🔄 در حال اجرا'}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
