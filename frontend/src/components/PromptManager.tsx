'use client';

import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// =====================================================
// Types
// =====================================================

interface SystemPrompt {
  id: string;
  name: string;
  description: string | null;
  category: string;
  prompt_type: string;
  content: string;
  variables: Record<string, string>;
  execution_order: number;
  is_required: boolean;
  is_active: boolean;
  is_default: boolean;
  is_locked: boolean;
  depends_on: string[];
  parent_id: string | null;
  metadata: Record<string, any>;
  usage_count: number;
  success_count: number;
  last_used_at: string | null;
  last_error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface PromptExecution {
  id: string;
  prompt_id: string;
  prompt_name: string;
  prompt_category: string;
  project_id: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  result_summary: string | null;
  error_message: string | null;
  model_used: string | null;
}

interface Category {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface Props {
  category: 'health_analysis' | 'engineering_report' | 'auto_setup' | 'all';
  projectId?: string;
  showExecutionStatus?: boolean;
  compact?: boolean;
  onPromptExecute?: (prompt: SystemPrompt) => void;
}

// =====================================================
// Component
// =====================================================

export default function PromptManager({
  category,
  projectId,
  showExecutionStatus = true,
  compact = false,
  onPromptExecute
}: Props) {
  // States
  const [prompts, setPrompts] = useState<SystemPrompt[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [activeExecutions, setActiveExecutions] = useState<PromptExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit states
  const [editingPrompt, setEditingPrompt] = useState<SystemPrompt | null>(null);
  const [showAddNew, setShowAddNew] = useState(false);
  const [newPromptData, setNewPromptData] = useState({
    name: '',
    description: '',
    content: '',
    execution_order: 10,
    is_required: false
  });

  // Expanded states
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);

  // =====================================================
  // Data Fetching
  // =====================================================

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/prompts/categories`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || []);
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
    }
  }, []);

  const fetchPrompts = useCallback(async () => {
    try {
      setLoading(true);
      const categoryParam = category !== 'all' ? `?category=${category}` : '';
      const res = await fetch(`${API_BASE}/api/prompts${categoryParam}`);

      if (!res.ok) throw new Error('خطا در دریافت پرامپت‌ها');

      const data = await res.json();
      setPrompts(data.prompts || []);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [category]);

  const fetchActiveExecutions = useCallback(async () => {
    if (!showExecutionStatus) return;

    try {
      const projectParam = projectId ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_BASE}/api/prompts/executions/active${projectParam}`);

      if (res.ok) {
        const data = await res.json();
        setActiveExecutions(data.executions || []);
      }
    } catch (err) {
      console.error('Error fetching active executions:', err);
    }
  }, [projectId, showExecutionStatus]);

  useEffect(() => {
    fetchCategories();
    fetchPrompts();
    fetchActiveExecutions();

    // Polling for active executions
    if (showExecutionStatus) {
      const interval = setInterval(fetchActiveExecutions, 3000);
      return () => clearInterval(interval);
    }
  }, [fetchCategories, fetchPrompts, fetchActiveExecutions, showExecutionStatus]);

  // =====================================================
  // Actions
  // =====================================================

  const handleTogglePrompt = async (promptId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/prompts/${promptId}/toggle`, {
        method: 'POST'
      });

      if (!res.ok) throw new Error('خطا در تغییر وضعیت');

      fetchPrompts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleUpdatePrompt = async () => {
    if (!editingPrompt) return;

    try {
      const res = await fetch(`${API_BASE}/api/prompts/${editingPrompt.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editingPrompt.name,
          description: editingPrompt.description,
          content: editingPrompt.content,
          execution_order: editingPrompt.execution_order,
          is_required: editingPrompt.is_required
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'خطا در به‌روزرسانی');
      }

      setEditingPrompt(null);
      fetchPrompts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCreatePrompt = async () => {
    if (!newPromptData.name || !newPromptData.content) {
      alert('نام و محتوا الزامی است');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/prompts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newPromptData,
          category: category !== 'all' ? category : 'custom',
          prompt_type: 'instruction'
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'خطا در ایجاد پرامپت');
      }

      setShowAddNew(false);
      setNewPromptData({ name: '', description: '', content: '', execution_order: 10, is_required: false });
      fetchPrompts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeletePrompt = async (promptId: string, promptName: string) => {
    if (!confirm(`آیا از حذف پرامپت "${promptName}" مطمئن هستید؟`)) return;

    try {
      const res = await fetch(`${API_BASE}/api/prompts/${promptId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'خطا در حذف');
      }

      fetchPrompts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDuplicatePrompt = async (promptId: string) => {
    const newName = prompt('نام پرامپت جدید را وارد کنید:');
    if (!newName) return;

    try {
      const res = await fetch(`${API_BASE}/api/prompts/${promptId}/duplicate?new_name=${encodeURIComponent(newName)}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'خطا در کپی');
      }

      fetchPrompts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // 🔴 بازیابی پرامپت‌های پیش‌فرض
  const handleRestoreDefaults = async () => {
    if (!confirm('آیا می‌خواهید پرامپت‌های پیش‌فرض را بازیابی کنید؟')) return;

    try {
      setLoading(true);
      const categoryParam = category !== 'all' ? `?category=${category}` : '';
      const res = await fetch(`${API_BASE}/api/prompts/restore-defaults${categoryParam}`, {
        method: 'POST'
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'خطا در بازیابی');
      }

      const data = await res.json();
      alert(`✅ ${data.total_default_prompts || 0} پرامپت پیش‌فرض موجود است`);
      fetchPrompts();
    } catch (err: any) {
      alert('خطا: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // Render Helpers
  // =====================================================

  const getCategoryInfo = (catId: string): Category | undefined => {
    return categories.find(c => c.id === catId);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'pending': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return 'در حال اجرا';
      case 'completed': return 'تکمیل شده';
      case 'failed': return 'خطا';
      case 'pending': return 'در انتظار';
      default: return status;
    }
  };

  // =====================================================
  // Render
  // =====================================================

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        <span className="mr-3 text-gray-600">در حال بارگذاری پرامپت‌ها...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        <p className="font-bold">خطا</p>
        <p>{error}</p>
        <button
          onClick={fetchPrompts}
          className="mt-2 text-sm text-red-600 hover:underline"
        >
          تلاش مجدد
        </button>
      </div>
    );
  }

  // Group prompts by category
  const groupedPrompts: Record<string, SystemPrompt[]> = {};
  prompts.forEach(p => {
    if (!groupedPrompts[p.category]) {
      groupedPrompts[p.category] = [];
    }
    groupedPrompts[p.category].push(p);
  });

  return (
    <div className={`prompt-manager ${compact ? 'compact' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-800">
          مدیریت پرامپت‌ها
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRestoreDefaults}
            className="flex items-center gap-1 px-3 py-1.5 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm"
            title="بازیابی پرامپت‌های پیش‌فرض"
          >
            <span>🔄</span>
            <span>بازیابی</span>
          </button>
          <button
            onClick={() => setShowAddNew(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
          >
            <span>+</span>
            <span>پرامپت جدید</span>
          </button>
        </div>
      </div>

      {/* Active Executions */}
      {showExecutionStatus && activeExecutions.length > 0 && (
        <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h4 className="text-sm font-bold text-blue-700 mb-2">
            در حال اجرا ({activeExecutions.length})
          </h4>
          <div className="space-y-2">
            {activeExecutions.map(exec => (
              <div
                key={exec.id}
                className="flex items-center gap-2 text-sm"
              >
                <div className={`w-2 h-2 rounded-full ${getStatusColor(exec.status)} animate-pulse`} />
                <span className="font-medium">{exec.prompt_name}</span>
                <span className="text-gray-500">-</span>
                <span className="text-gray-600">{getStatusText(exec.status)}</span>
                {exec.model_used && (
                  <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                    {exec.model_used}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prompts List */}
      {Object.entries(groupedPrompts).map(([catId, catPrompts]) => {
        const catInfo = getCategoryInfo(catId);
        return (
          <div key={catId} className="mb-6">
            {/* Category Header */}
            {category === 'all' && (
              <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                <span className="text-xl">{catInfo?.icon || '📝'}</span>
                <h4 className="font-bold text-gray-700">
                  {catInfo?.name || catId}
                </h4>
                <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">
                  {catPrompts.length}
                </span>
              </div>
            )}

            {/* Prompts */}
            <div className="space-y-2">
              {catPrompts.map(prompt => {
                const isExpanded = expandedPrompt === prompt.id;
                const isEditing = editingPrompt?.id === prompt.id;
                const isExecuting = activeExecutions.some(e => e.prompt_id === prompt.id);

                return (
                  <div
                    key={prompt.id}
                    className={`border rounded-lg transition-all ${
                      isExpanded ? 'bg-gray-50' : 'bg-white'
                    } ${!prompt.is_active ? 'opacity-60' : ''} ${
                      isExecuting ? 'border-blue-400 ring-2 ring-blue-200' : 'border-gray-200'
                    }`}
                  >
                    {/* Prompt Header */}
                    <div
                      className="flex items-center gap-3 p-3 cursor-pointer"
                      onClick={() => setExpandedPrompt(isExpanded ? null : prompt.id)}
                    >
                      {/* Status Indicator */}
                      {isExecuting && (
                        <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                      )}

                      {/* Order Badge */}
                      <span className="w-6 h-6 flex items-center justify-center bg-gray-100 rounded text-xs font-mono">
                        {prompt.execution_order}
                      </span>

                      {/* Name */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">
                            {prompt.name}
                          </span>
                          {prompt.is_default && (
                            <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                              پیش‌فرض
                            </span>
                          )}
                          {prompt.is_locked && (
                            <span className="text-xs" title="قفل شده">🔒</span>
                          )}
                          {prompt.is_required && (
                            <span className="text-xs text-red-500" title="اجباری">*</span>
                          )}
                        </div>
                        {prompt.description && !isExpanded && (
                          <p className="text-xs text-gray-500 truncate max-w-md">
                            {prompt.description}
                          </p>
                        )}
                      </div>

                      {/* Stats */}
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span title="تعداد استفاده">
                          📊 {prompt.usage_count || 0}
                        </span>
                        {prompt.success_count > 0 && (
                          <span title="موفقیت" className="text-green-600">
                            ✓ {prompt.success_count}
                          </span>
                        )}
                      </div>

                      {/* Toggle */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePrompt(prompt.id);
                        }}
                        className={`w-10 h-5 rounded-full relative transition-colors ${
                          prompt.is_active ? 'bg-green-500' : 'bg-gray-300'
                        }`}
                        title={prompt.is_active ? 'فعال' : 'غیرفعال'}
                      >
                        <div
                          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                            prompt.is_active ? 'left-5' : 'left-0.5'
                          }`}
                        />
                      </button>

                      {/* Expand Icon */}
                      <span className={`text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
                        ▼
                      </span>
                    </div>

                    {/* Expanded Content */}
                    {isExpanded && (
                      <div className="border-t p-4">
                        {isEditing ? (
                          /* Edit Mode */
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                نام
                              </label>
                              <input
                                type="text"
                                value={editingPrompt.name}
                                onChange={e => setEditingPrompt({ ...editingPrompt, name: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg"
                                disabled={prompt.is_locked}
                              />
                            </div>

                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                توضیحات
                              </label>
                              <input
                                type="text"
                                value={editingPrompt.description || ''}
                                onChange={e => setEditingPrompt({ ...editingPrompt, description: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg"
                              />
                            </div>

                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                محتوای پرامپت
                              </label>
                              <textarea
                                value={editingPrompt.content}
                                onChange={e => setEditingPrompt({ ...editingPrompt, content: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                                rows={15}
                                dir="auto"
                              />
                            </div>

                            <div className="flex items-center gap-4">
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  ترتیب اجرا
                                </label>
                                <input
                                  type="number"
                                  value={editingPrompt.execution_order}
                                  onChange={e => setEditingPrompt({ ...editingPrompt, execution_order: parseInt(e.target.value) || 1 })}
                                  className="w-20 px-3 py-2 border rounded-lg"
                                  min={1}
                                  max={100}
                                  disabled={prompt.is_locked}
                                />
                              </div>

                              <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={editingPrompt.is_required}
                                  onChange={e => setEditingPrompt({ ...editingPrompt, is_required: e.target.checked })}
                                  className="w-4 h-4"
                                />
                                <span className="text-sm">اجباری</span>
                              </label>
                            </div>

                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => setEditingPrompt(null)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                              >
                                انصراف
                              </button>
                              <button
                                onClick={handleUpdatePrompt}
                                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                              >
                                ذخیره تغییرات
                              </button>
                            </div>
                          </div>
                        ) : (
                          /* View Mode */
                          <div>
                            {prompt.description && (
                              <p className="text-sm text-gray-600 mb-4">
                                {prompt.description}
                              </p>
                            )}

                            {/* Variables */}
                            {Object.keys(prompt.variables).length > 0 && (
                              <div className="mb-4">
                                <h5 className="text-sm font-medium text-gray-700 mb-2">
                                  متغیرها:
                                </h5>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(prompt.variables).map(([key, desc]) => (
                                    <span
                                      key={key}
                                      className="text-xs bg-purple-50 text-purple-700 px-2 py-1 rounded"
                                      title={String(desc)}
                                    >
                                      {`{${key}}`}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Content Preview */}
                            <div className="mb-4">
                              <h5 className="text-sm font-medium text-gray-700 mb-2">
                                محتوای پرامپت:
                              </h5>
                              <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-auto max-h-80" dir="auto">
                                {prompt.content}
                              </pre>
                            </div>

                            {/* Metadata */}
                            {prompt.metadata && Object.keys(prompt.metadata).length > 0 && (
                              <div className="mb-4">
                                <h5 className="text-sm font-medium text-gray-700 mb-2">
                                  تنظیمات:
                                </h5>
                                <div className="flex flex-wrap gap-2 text-xs">
                                  {prompt.metadata.output_format && (
                                    <span className="bg-gray-100 px-2 py-1 rounded">
                                      فرمت: {prompt.metadata.output_format}
                                    </span>
                                  )}
                                  {prompt.metadata.min_tokens && (
                                    <span className="bg-gray-100 px-2 py-1 rounded">
                                      حداقل توکن: {prompt.metadata.min_tokens}
                                    </span>
                                  )}
                                  {prompt.metadata.max_tokens && (
                                    <span className="bg-gray-100 px-2 py-1 rounded">
                                      حداکثر توکن: {prompt.metadata.max_tokens}
                                    </span>
                                  )}
                                  {prompt.metadata.tags?.map((tag: string) => (
                                    <span key={tag} className="bg-blue-50 text-blue-700 px-2 py-1 rounded">
                                      #{tag}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Last Error */}
                            {prompt.last_error && (
                              <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
                                <h5 className="text-sm font-medium text-red-700 mb-1">
                                  آخرین خطا:
                                </h5>
                                <p className="text-xs text-red-600">{prompt.last_error}</p>
                              </div>
                            )}

                            {/* Actions */}
                            <div className="flex justify-end gap-2 pt-4 border-t">
                              <button
                                onClick={() => handleDuplicatePrompt(prompt.id)}
                                className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
                                title="کپی"
                              >
                                📋 کپی
                              </button>

                              <button
                                onClick={() => setEditingPrompt(prompt)}
                                className="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded"
                              >
                                ✏️ ویرایش
                              </button>

                              {!prompt.is_locked && !prompt.is_default && (
                                <button
                                  onClick={() => handleDeletePrompt(prompt.id, prompt.name)}
                                  className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded"
                                >
                                  🗑️ حذف
                                </button>
                              )}

                              {onPromptExecute && (
                                <button
                                  onClick={() => onPromptExecute(prompt)}
                                  className="px-3 py-1.5 text-sm bg-green-500 text-white hover:bg-green-600 rounded"
                                >
                                  ▶️ اجرا
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Add New Prompt Modal */}
      {showAddNew && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">
                ایجاد پرامپت جدید
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    نام پرامپت *
                  </label>
                  <input
                    type="text"
                    value={newPromptData.name}
                    onChange={e => setNewPromptData({ ...newPromptData, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="مثال: بررسی امنیتی فایل"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    توضیحات
                  </label>
                  <input
                    type="text"
                    value={newPromptData.description}
                    onChange={e => setNewPromptData({ ...newPromptData, description: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="توضیح کوتاه درباره این پرامپت"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    محتوای پرامپت *
                  </label>
                  <textarea
                    value={newPromptData.content}
                    onChange={e => setNewPromptData({ ...newPromptData, content: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                    rows={12}
                    placeholder="دستورات AI را اینجا بنویسید..."
                    dir="auto"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    می‌توانید از متغیرها استفاده کنید: {'{project_name}'}, {'{file_path}'}, ...
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ترتیب اجرا
                    </label>
                    <input
                      type="number"
                      value={newPromptData.execution_order}
                      onChange={e => setNewPromptData({ ...newPromptData, execution_order: parseInt(e.target.value) || 10 })}
                      className="w-20 px-3 py-2 border rounded-lg"
                      min={1}
                      max={100}
                    />
                  </div>

                  <label className="flex items-center gap-2 cursor-pointer mt-6">
                    <input
                      type="checkbox"
                      checked={newPromptData.is_required}
                      onChange={e => setNewPromptData({ ...newPromptData, is_required: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">اجباری</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6 pt-4 border-t">
                <button
                  onClick={() => setShowAddNew(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  انصراف
                </button>
                <button
                  onClick={handleCreatePrompt}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  ایجاد پرامپت
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {prompts.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg mb-4">هیچ پرامپتی یافت نشد</p>
          <div className="flex flex-col gap-3 items-center">
            {/* 🔴 دکمه بازیابی پیش‌فرض‌ها */}
            <button
              onClick={handleRestoreDefaults}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center gap-2"
            >
              <span>🔄</span>
              بازیابی پرامپت‌های پیش‌فرض
            </button>
            <span className="text-sm text-gray-400">یا</span>
            <button
              onClick={() => setShowAddNew(true)}
              className="text-blue-500 hover:underline"
            >
              ایجاد پرامپت جدید
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
