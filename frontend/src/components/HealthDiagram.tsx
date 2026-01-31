'use client';

import { useState, useEffect, useMemo } from 'react';
import FileViewer from './FileViewer';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FileHealth {
  score: number;
  color: string;
  hex: string;
  issues?: number;
  models_analyzed?: number;
}

interface Props {
  projectId: string;
  fileHealthMap: Record<string, FileHealth>;
  onFileClick?: (filePath: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  health?: FileHealth;
  children: TreeNode[];
  expanded?: boolean;
}

/**
 * 🔴 کامپوننت دیاگرام سلامت
 * نمایش ساختار پروژه با رنگ‌بندی براساس نمره سلامت هر فایل
 */

// تابع رنگ براساس امتیاز - باید قبل از استفاده تعریف شود
const getColorForScore = (score: number): string => {
  if (score >= 80) return '#22c55e'; // سبز
  if (score >= 60) return '#eab308'; // زرد
  if (score >= 40) return '#f97316'; // نارنجی
  return '#ef4444'; // قرمز
};

// آیکون فایل براساس پسوند
const getFileIcon = (ext: string): string => {
  const icons: Record<string, string> = {
    ts: '📘',
    tsx: '⚛️',
    js: '📒',
    jsx: '⚛️',
    py: '🐍',
    json: '📋',
    md: '📝',
    css: '🎨',
    html: '🌐',
    sql: '🗃️',
    yml: '⚙️',
    yaml: '⚙️',
    sh: '🖥️',
    env: '🔐',
    lock: '🔒',
  };
  return icons[ext.toLowerCase()] || '📄';
};

export default function HealthDiagram({ projectId, fileHealthMap, onFileClick }: Props) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'tree' | 'grid' | 'mermaid'>('tree');
  const [filterScore, setFilterScore] = useState<number>(0); // 0 = همه
  const [selectedFile, setSelectedFile] = useState<string | null>(null); // فایل انتخاب شده برای نمایش
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set()); // فایل‌های انتخاب شده برای دانلود

  // ساخت درخت از فایل‌ها
  const fileTree = useMemo(() => {
    const root: TreeNode = { name: 'root', path: '', type: 'folder', children: [] };

    Object.entries(fileHealthMap).forEach(([filePath, health]) => {
      const parts = filePath.split('/').filter(Boolean);
      let current = root;

      parts.forEach((part, index) => {
        const isFile = index === parts.length - 1;
        const currentPath = parts.slice(0, index + 1).join('/');

        let child = current.children.find(c => c.name === part);
        if (!child) {
          child = {
            name: part,
            path: currentPath,
            type: isFile ? 'file' : 'folder',
            children: [],
            health: isFile ? health : undefined,
          };
          current.children.push(child);
        }
        if (!isFile) {
          current = child;
        }
      });
    });

    // محاسبه سلامت پوشه‌ها (میانگین فرزندان)
    const calculateFolderHealth = (node: TreeNode): FileHealth | undefined => {
      if (node.type === 'file') return node.health;

      const childHealths: FileHealth[] = [];
      node.children.forEach(child => {
        const childHealth = calculateFolderHealth(child);
        if (childHealth) childHealths.push(childHealth);
      });

      if (childHealths.length === 0) return undefined;

      const avgScore = Math.round(
        childHealths.reduce((sum, h) => sum + h.score, 0) / childHealths.length
      );

      return {
        score: avgScore,
        color: getColorForScore(avgScore),
        hex: getColorForScore(avgScore),
        issues: childHealths.reduce((sum, h) => sum + (h.issues || 0), 0),
      };
    };

    // اعمال محاسبه به همه پوشه‌ها
    const applyFolderHealth = (node: TreeNode) => {
      if (node.type === 'folder') {
        node.health = calculateFolderHealth(node);
        node.children.forEach(applyFolderHealth);
      }
    };

    applyFolderHealth(root);

    // مرتب‌سازی: پوشه‌ها اول، سپس فایل‌ها
    const sortChildren = (node: TreeNode) => {
      node.children.sort((a, b) => {
        if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      node.children.forEach(sortChildren);
    };
    sortChildren(root);

    return root;
  }, [fileHealthMap]);

  // تابع رنگ براساس امتیاز - رنگ‌های روشن‌تر برای خوانایی بهتر
  const getColorForScore = (score: number): string => {
    if (score >= 80) return '#4ade80'; // سبز روشن
    if (score >= 60) return '#facc15'; // زرد روشن
    if (score >= 40) return '#fb923c'; // نارنجی روشن
    return '#f87171'; // قرمز روشن
  };

  // تابع رنگ متن - همیشه خوانا روی پس‌زمینه تاریک
  const getTextColorForScore = (score: number): string => {
    // رنگ‌های روشن‌تر برای متن که روی bg-gray-800 خوانا باشند
    if (score >= 80) return '#86efac'; // سبز خیلی روشن
    if (score >= 60) return '#fef08a'; // زرد خیلی روشن
    if (score >= 40) return '#fdba74'; // نارنجی خیلی روشن
    return '#fca5a5'; // قرمز خیلی روشن
  };

  // toggle پوشه
  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  // باز کردن همه
  const expandAll = () => {
    const allPaths = new Set<string>();
    const collect = (node: TreeNode) => {
      if (node.type === 'folder' && node.path) {
        allPaths.add(node.path);
      }
      node.children.forEach(collect);
    };
    collect(fileTree);
    setExpandedFolders(allPaths);
  };

  // بستن همه
  const collapseAll = () => {
    setExpandedFolders(new Set());
  };

  // رندر درخت
  const renderTreeNode = (node: TreeNode, depth: number = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path);
    const score = node.health?.score ?? 50;
    // استفاده از رنگ‌های روشن‌تر برای خوانایی بهتر
    const healthColor = getColorForScore(score);
    const textColor = getTextColorForScore(score);
    const issues = node.health?.issues || 0;

    // فیلتر براساس امتیاز
    if (filterScore > 0 && score && score > filterScore) return null;

    const indent = depth * 16;

    if (node.type === 'folder' && node.path) {
      return (
        <div key={node.path}>
          <div
            className="flex items-center py-1 px-2 hover:bg-gray-700 cursor-pointer rounded group"
            style={{ paddingRight: `${indent}px`, direction: 'ltr' }}
            onClick={() => toggleFolder(node.path)}
          >
            <span className="ml-1 text-gray-400">
              {isExpanded ? '📂' : '📁'}
            </span>
            <span className="ml-2 text-gray-300 flex-1">{node.name}</span>
            {score !== undefined && (
              <span
                className="px-2 py-0.5 text-xs rounded-full font-bold"
                style={{ backgroundColor: healthColor + '30', color: healthColor }}
              >
                {score}%
              </span>
            )}
            {issues > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-red-900/50 text-red-400 rounded">
                ⚠ {issues}
              </span>
            )}
          </div>
          {isExpanded && node.children.map(child => renderTreeNode(child, depth + 1))}
        </div>
      );
    }

    if (node.type === 'file') {
      const ext = node.name.split('.').pop() || '';
      const fileIcon = getFileIcon(ext);
      const isSelected = selectedFiles.has(node.path);

      return (
        <div
          key={node.path}
          className={`flex items-center py-1 px-2 hover:bg-gray-700 cursor-pointer rounded group ${isSelected ? 'bg-blue-900/30' : ''}`}
          style={{ paddingRight: `${indent + 16}px`, direction: 'ltr' }}
        >
          {/* چک‌باکس انتخاب */}
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => {
              e.stopPropagation();
              const newSelected = new Set(selectedFiles);
              if (e.target.checked) {
                newSelected.add(node.path);
              } else {
                newSelected.delete(node.path);
              }
              setSelectedFiles(newSelected);
            }}
            className="mr-2 rounded"
            onClick={(e) => e.stopPropagation()}
          />
          <div
            className="flex items-center flex-1"
            onClick={() => setSelectedFile(node.path)}
          >
            <span className="ml-1">{fileIcon}</span>
            <span
              className="ml-2 flex-1 font-medium"
              style={{ color: textColor }}  // 🔴 استفاده از رنگ متن روشن‌تر
            >
              {node.name}
            </span>
          {score !== undefined && (
            <div className="flex items-center gap-2">
              {/* نوار پیشرفت کوچک */}
              <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${score}%`,
                    backgroundColor: healthColor,
                  }}
                />
              </div>
              <span
                className="text-xs font-mono"
                style={{ color: textColor }}
              >
                {score}
              </span>
            </div>
          )}
          </div>
        </div>
      );
    }

    return node.children.map(child => renderTreeNode(child, depth));
  };

  // رندر نمای گرید
  const renderGridView = () => {
    const files = Object.entries(fileHealthMap)
      .filter(([_, health]) => filterScore === 0 || health.score <= filterScore)
      .sort((a, b) => a[1].score - b[1].score); // بدترین‌ها اول

    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 p-2">
        {files.map(([path, health]) => {
          // 🔴 استفاده از رنگ‌های روشن‌تر برای خوانایی بهتر
          const bgColor = getColorForScore(health.score);
          const txtColor = getTextColorForScore(health.score);

          return (
            <div
              key={path}
              className="p-3 rounded-lg border cursor-pointer hover:scale-105 transition-transform"
              style={{
                borderColor: bgColor,
                backgroundColor: bgColor + '15',
              }}
              onClick={() => onFileClick?.(path)}
            >
              <div className="text-xs text-gray-400 truncate" dir="ltr">
                {path.split('/').slice(0, -1).join('/')}
              </div>
              <div className="font-medium truncate" style={{ color: txtColor }}>
                {path.split('/').pop()}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${health.score}%`,
                      backgroundColor: bgColor,
                    }}
                  />
                </div>
                <span className="text-sm font-bold" style={{ color: txtColor }}>
                  {health.score}%
                </span>
              </div>
              {health.issues && health.issues > 0 && (
                <div className="mt-1 text-xs text-red-400">
                  ⚠ {health.issues} ایراد
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // تولید کد Mermaid
  const mermaidCode = useMemo(() => {
    const lines: string[] = ['graph TD'];
    const nodeStyles: string[] = [];

    let nodeId = 0;
    const getNodeId = () => `N${nodeId++}`;

    const processNode = (node: TreeNode, parentId?: string) => {
      const id = getNodeId();
      const label = node.name.replace(/[[\](){}]/g, '');
      const healthColor = node.health?.hex || '#6b7280';

      if (node.type === 'folder' && node.path) {
        lines.push(`  ${id}[📁 ${label}]`);
        nodeStyles.push(`style ${id} fill:${healthColor}20,stroke:${healthColor}`);
      } else if (node.type === 'file') {
        const score = node.health?.score || 0;
        lines.push(`  ${id}[${label}<br/>${score}%]`);
        nodeStyles.push(`style ${id} fill:${healthColor}30,stroke:${healthColor},stroke-width:2px`);
      }

      if (parentId) {
        lines.push(`  ${parentId} --> ${id}`);
      }

      node.children.forEach(child => processNode(child, id));
    };

    fileTree.children.forEach(child => processNode(child));
    lines.push(...nodeStyles);

    return lines.join('\n');
  }, [fileTree]);

  // آمار کلی
  const stats = useMemo(() => {
    const files = Object.values(fileHealthMap);
    if (files.length === 0) return null;

    const avgScore = Math.round(files.reduce((sum, f) => sum + f.score, 0) / files.length);
    const critical = files.filter(f => f.score < 40).length;
    const warning = files.filter(f => f.score >= 40 && f.score < 60).length;
    const good = files.filter(f => f.score >= 60 && f.score < 80).length;
    const excellent = files.filter(f => f.score >= 80).length;
    const totalIssues = files.reduce((sum, f) => sum + (f.issues || 0), 0);

    return { avgScore, critical, warning, good, excellent, total: files.length, totalIssues };
  }, [fileHealthMap]);

  if (Object.keys(fileHealthMap).length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        <p>🔍 هنوز تحلیل سلامت انجام نشده است</p>
        <p className="text-sm mt-2">ابتدا تحلیل سلامت را اجرا کنید</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      {/* هدر با آمار */}
      {stats && (
        <div className="p-4 bg-gray-700/50 border-b border-gray-600">
          <div className="flex flex-wrap items-center gap-4">
            {/* امتیاز کلی */}
            <div className="flex items-center gap-2">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold"
                style={{
                  backgroundColor: getColorForScore(stats.avgScore) + '30',
                  color: getColorForScore(stats.avgScore),
                  border: `2px solid ${getColorForScore(stats.avgScore)}`,
                }}
              >
                {stats.avgScore}
              </div>
              <div className="text-sm">
                <div className="text-gray-300">میانگین سلامت</div>
                <div className="text-gray-500">{stats.total} فایل</div>
              </div>
            </div>

            {/* توزیع امتیازات */}
            <div className="flex gap-2">
              {stats.excellent > 0 && (
                <span className="px-2 py-1 text-xs rounded bg-green-900/50 text-green-400">
                  ✅ {stats.excellent} عالی
                </span>
              )}
              {stats.good > 0 && (
                <span className="px-2 py-1 text-xs rounded bg-yellow-900/50 text-yellow-400">
                  👍 {stats.good} خوب
                </span>
              )}
              {stats.warning > 0 && (
                <span className="px-2 py-1 text-xs rounded bg-orange-900/50 text-orange-400">
                  ⚠️ {stats.warning} متوسط
                </span>
              )}
              {stats.critical > 0 && (
                <span className="px-2 py-1 text-xs rounded bg-red-900/50 text-red-400">
                  🔴 {stats.critical} بحرانی
                </span>
              )}
            </div>

            {stats.totalIssues > 0 && (
              <span className="px-2 py-1 text-xs rounded bg-red-900/50 text-red-400">
                ⚠ {stats.totalIssues} ایراد کل
              </span>
            )}
          </div>
        </div>
      )}

      {/* کنترل‌ها */}
      <div className="p-3 border-b border-gray-700 flex flex-wrap items-center gap-3">
        {/* تغییر نما */}
        <div className="flex gap-1 bg-gray-700 rounded-lg p-1">
          <button
            className={`px-3 py-1 text-sm rounded ${viewMode === 'tree' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            onClick={() => setViewMode('tree')}
          >
            🌲 درخت
          </button>
          <button
            className={`px-3 py-1 text-sm rounded ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            onClick={() => setViewMode('grid')}
          >
            🔲 گرید
          </button>
          <button
            className={`px-3 py-1 text-sm rounded ${viewMode === 'mermaid' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            onClick={() => setViewMode('mermaid')}
          >
            📊 نمودار
          </button>
        </div>

        {/* فیلتر امتیاز */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">فیلتر:</span>
          <select
            className="bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600"
            value={filterScore}
            onChange={(e) => setFilterScore(Number(e.target.value))}
          >
            <option value={0}>همه</option>
            <option value={40}>بحرانی (&lt;40)</option>
            <option value={60}>نیاز به توجه (&lt;60)</option>
            <option value={80}>قابل بهبود (&lt;80)</option>
          </select>
        </div>

        {/* دکمه‌های باز/بستن */}
        {viewMode === 'tree' && (
          <div className="flex gap-1">
            <button
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
              onClick={expandAll}
            >
              باز کردن همه
            </button>
            <button
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
              onClick={collapseAll}
            >
              بستن همه
            </button>
          </div>
        )}

        {/* دکمه‌های دانلود */}
        <div className="flex gap-1 mr-auto">
          {selectedFiles.size > 0 && (
            <>
              <button
                className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center gap-1"
                onClick={async () => {
                  const files = Array.from(selectedFiles);
                  try {
                    const res = await fetch(`${API_BASE}/api/projects/${projectId}/health/files/download-batch`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ file_paths: files, include_suggestions: true }),
                    });
                    if (res.ok) {
                      const blob = await res.blob();
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'selected_files.zip';
                      a.click();
                      window.URL.revokeObjectURL(url);
                    }
                  } catch (err) {
                    console.error('Error downloading files:', err);
                  }
                }}
              >
                📥 دانلود انتخاب شده ({selectedFiles.size})
              </button>
              <button
                className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-500 text-white rounded"
                onClick={() => setSelectedFiles(new Set())}
              >
                ✕ لغو انتخاب
              </button>
            </>
          )}
          <button
            className="px-2 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded flex items-center gap-1"
            onClick={() => {
              window.open(
                `${API_BASE}/api/projects/${projectId}/health/files/download-all?include_suggestions=true`,
                '_blank'
              );
            }}
          >
            📦 دانلود همه
          </button>
        </div>
      </div>

      {/* محتوا */}
      <div className="max-h-96 overflow-auto p-2">
        {viewMode === 'tree' && renderTreeNode(fileTree)}
        {viewMode === 'grid' && renderGridView()}
        {viewMode === 'mermaid' && (
          <div className="p-4">
            <pre className="bg-gray-900 p-4 rounded text-xs text-gray-300 overflow-auto" dir="ltr">
              {mermaidCode}
            </pre>
            <p className="text-xs text-gray-500 mt-2">
              این کد را در ابزارهای Mermaid وارد کنید
            </p>
          </div>
        )}
      </div>

      {/* راهنما - با رنگ‌های روشن‌تر */}
      <div className="p-3 bg-gray-700/30 border-t border-gray-700">
        <div className="flex items-center gap-4 text-xs text-gray-300">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: '#4ade80' }}></span>
            80-100 (عالی)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: '#facc15' }}></span>
            60-79 (خوب)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: '#fb923c' }}></span>
            40-59 (متوسط)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: '#f87171' }}></span>
            0-39 (بحرانی)
          </span>
        </div>
      </div>

      {/* نمایشگر فایل */}
      {selectedFile && (
        <FileViewer
          projectId={projectId}
          filePath={selectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </div>
  );
}
