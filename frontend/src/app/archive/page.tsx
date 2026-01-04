/**
 * Archive Page - آرشیو مناظرات و مدیریت فایل‌ها
 */

'use client';

import { useState, useEffect } from 'react';
import {
  ChatBubbleLeftRightIcon,
  DocumentIcon,
  FolderIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  EyeIcon,
  ClockIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  PhotoIcon,
} from '@heroicons/react/24/outline';

function getApiUrl(): string {
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
    return process.env.NEXT_PUBLIC_API_URL || 'https://ai-creator-engine-backend.onrender.com';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

interface DebateItem {
  id: string;
  prompt: string;
  mode: string;
  status: string;
  models: string[];
  rounds_count: number;
  created_at: string;
  updated_at: string;
}

interface FileItem {
  id: string;
  original_name: string;
  stored_name: string;
  relative_path: string;
  mime_type: string;
  size: number;
  category: string;
  subcategory?: string;
  created_at: string;
  tags: string[];
}

interface StorageStats {
  total_files: number;
  total_size: number;
  total_size_mb: number;
  by_category: Record<string, { count: number; size: number }>;
}

export default function ArchivePage() {
  const [activeTab, setActiveTab] = useState<'debates' | 'files'>('debates');
  const [loading, setLoading] = useState(true);
  const [debates, setDebates] = useState<DebateItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDebate, setSelectedDebate] = useState<any>(null);
  const [showDebateModal, setShowDebateModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load debates
      const debatesRes = await fetch(`${getApiUrl()}/api/debate/`);
      if (debatesRes.ok) {
        const data = await debatesRes.json();
        setDebates(data);
      }

      // Load files
      const filesRes = await fetch(`${getApiUrl()}/api/upload/files`);
      if (filesRes.ok) {
        const data = await filesRes.json();
        setFiles(data);
      }

      // Load stats
      const statsRes = await fetch(`${getApiUrl()}/api/upload/stats`);
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadFile = async (fileId: string, filename: string) => {
    try {
      const res = await fetch(`${getApiUrl()}/api/upload/file/${fileId}`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!confirm('آیا از حذف این فایل مطمئن هستید؟')) return;

    try {
      const res = await fetch(`${getApiUrl()}/api/upload/file/${fileId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setFiles(prev => prev.filter(f => f.id !== fileId));
      }
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleViewDebate = async (debateId: string) => {
    try {
      const res = await fetch(`${getApiUrl()}/api/debate/${debateId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedDebate(data);
        setShowDebateModal(true);
      }
    } catch (err) {
      console.error('Error loading debate:', err);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return PhotoIcon;
    if (mimeType.includes('text') || mimeType.includes('json')) return DocumentTextIcon;
    if (mimeType.includes('javascript') || mimeType.includes('python')) return CodeBracketIcon;
    return DocumentIcon;
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { color: string; text: string }> = {
      pending: { color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400', text: 'در انتظار' },
      running: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', text: 'در حال اجرا' },
      completed: { color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', text: 'تکمیل شده' },
      failed: { color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', text: 'خطا' },
    };
    const badge = badges[status] || { color: 'bg-gray-100 text-gray-700', text: status };
    return <span className={`px-2 py-0.5 rounded text-xs ${badge.color}`}>{badge.text}</span>;
  };

  // Filter debates
  const filteredDebates = debates.filter(d =>
    d.prompt.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter files
  const filteredFiles = files.filter(f => {
    const matchesSearch = f.original_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || f.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Get unique categories
  const categories = ['all', ...Array.from(new Set(files.map(f => f.category)))];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner w-12 h-12" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            آرشیو و فایل‌ها
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            مدیریت مناظرات و فایل‌های آپلود شده
          </p>
        </div>
        <button
          onClick={loadData}
          className="btn bg-gray-100 dark:bg-gray-700 flex items-center gap-2"
        >
          <ArrowPathIcon className="w-5 h-5" />
          بروزرسانی
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-800">
          <ChatBubbleLeftRightIcon className="w-8 h-8 text-blue-500 mb-2" />
          <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{debates.length}</p>
          <p className="text-sm text-blue-600 dark:text-blue-400">مناظره</p>
        </div>
        <div className="card bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-800">
          <DocumentIcon className="w-8 h-8 text-green-500 mb-2" />
          <p className="text-2xl font-bold text-green-700 dark:text-green-300">{stats?.total_files || 0}</p>
          <p className="text-sm text-green-600 dark:text-green-400">فایل</p>
        </div>
        <div className="card bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-800">
          <FolderIcon className="w-8 h-8 text-purple-500 mb-2" />
          <p className="text-2xl font-bold text-purple-700 dark:text-purple-300">
            {stats?.total_size_mb?.toFixed(1) || 0} MB
          </p>
          <p className="text-sm text-purple-600 dark:text-purple-400">حجم کل</p>
        </div>
        <div className="card bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-800/20 border-orange-200 dark:border-orange-800">
          <CheckCircleIcon className="w-8 h-8 text-orange-500 mb-2" />
          <p className="text-2xl font-bold text-orange-700 dark:text-orange-300">
            {debates.filter(d => d.status === 'completed').length}
          </p>
          <p className="text-sm text-orange-600 dark:text-orange-400">مناظره موفق</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('debates')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'debates'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <ChatBubbleLeftRightIcon className="w-5 h-5 inline ml-2" />
          مناظرات ({debates.length})
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'files'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FolderIcon className="w-5 h-5 inline ml-2" />
          فایل‌ها ({files.length})
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-wrap gap-4">
        <div className="flex-1 min-w-[200px] relative">
          <MagnifyingGlassIcon className="w-5 h-5 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="جستجو..."
            className="input pr-10"
          />
        </div>
        {activeTab === 'files' && (
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="input w-auto"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'همه دسته‌ها' : cat}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Debates Tab */}
      {activeTab === 'debates' && (
        <div className="space-y-4">
          {filteredDebates.length === 0 ? (
            <div className="card text-center py-12">
              <ChatBubbleLeftRightIcon className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <p className="text-gray-500">هیچ مناظره‌ای یافت نشد</p>
            </div>
          ) : (
            filteredDebates.map((debate) => (
              <div
                key={debate.id}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewDebate(debate.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-gray-900 dark:text-white">
                        {debate.prompt.slice(0, 100)}
                        {debate.prompt.length > 100 && '...'}
                      </h3>
                      {getStatusBadge(debate.status)}
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <ClockIcon className="w-4 h-4" />
                        {formatDate(debate.created_at)}
                      </span>
                      <span>{debate.models.length} مدل</span>
                      <span>{debate.rounds_count} دور</span>
                      <span className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                        {debate.mode}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleViewDebate(debate.id);
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <EyeIcon className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Files Tab */}
      {activeTab === 'files' && (
        <div className="space-y-4">
          {filteredFiles.length === 0 ? (
            <div className="card text-center py-12">
              <FolderIcon className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <p className="text-gray-500">هیچ فایلی یافت نشد</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredFiles.map((file) => {
                const FileIcon = getFileIcon(file.mime_type);
                return (
                  <div
                    key={file.id}
                    className="card flex items-center gap-4 hover:shadow-md transition-shadow"
                  >
                    <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                      <FileIcon className="w-8 h-8 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 dark:text-white truncate">
                        {file.original_name}
                      </h4>
                      <div className="flex flex-wrap gap-3 text-sm text-gray-500 mt-1">
                        <span>{formatFileSize(file.size)}</span>
                        <span>{file.category}</span>
                        {file.subcategory && (
                          <span className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                            {file.subcategory}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <ClockIcon className="w-3 h-3" />
                          {formatDate(file.created_at)}
                        </span>
                      </div>
                      {file.tags.length > 0 && (
                        <div className="flex gap-1 mt-2">
                          {file.tags.map((tag, i) => (
                            <span
                              key={i}
                              className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleDownloadFile(file.id, file.original_name)}
                        className="p-2 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-lg text-green-600"
                        title="دانلود"
                      >
                        <ArrowDownTrayIcon className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteFile(file.id)}
                        className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg text-red-600"
                        title="حذف"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Debate Detail Modal */}
      {showDebateModal && selectedDebate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  جزئیات مناظره
                </h2>
                <p className="text-sm text-gray-500 mt-1">{selectedDebate.id}</p>
              </div>
              <button
                onClick={() => setShowDebateModal(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <XCircleIcon className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[70vh] space-y-6">
              {/* Prompt */}
              <div>
                <h3 className="font-bold text-gray-900 dark:text-white mb-2">سوال/موضوع:</h3>
                <p className="text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  {selectedDebate.prompt}
                </p>
              </div>

              {/* Rounds */}
              {selectedDebate.rounds?.map((round: any[], roundIndex: number) => (
                <div key={roundIndex}>
                  <h3 className="font-bold text-gray-900 dark:text-white mb-3">
                    دور {roundIndex + 1}
                  </h3>
                  <div className="space-y-3">
                    {round.map((response: any, respIndex: number) => (
                      <div
                        key={respIndex}
                        className={`p-4 rounded-lg ${
                          response.error
                            ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                            : 'bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xl">{response.role_icon}</span>
                          <span className="font-bold">{response.model_name}</span>
                          <span className="text-sm text-gray-500">({response.role_name})</span>
                          <span className="text-xs text-gray-400">
                            {response.tokens_used} توکن • {response.latency_ms}ms
                          </span>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap text-sm">
                          {response.error || response.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Summary */}
              {selectedDebate.summary && (
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white mb-2">خلاصه:</h3>
                  <p className="text-gray-700 dark:text-gray-300 bg-green-50 dark:bg-green-900/20 p-4 rounded-lg whitespace-pre-wrap">
                    {selectedDebate.summary}
                  </p>
                </div>
              )}

              {/* Judge Result */}
              {selectedDebate.judge_result && (
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white mb-2">نتیجه داوری:</h3>
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                    <p className="font-bold text-yellow-700 dark:text-yellow-300">
                      برنده: {selectedDebate.judge_result.winner}
                    </p>
                    <p className="text-gray-700 dark:text-gray-300 mt-2">
                      {selectedDebate.judge_result.reasoning}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
