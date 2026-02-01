'use client';

import { useState, useEffect, useMemo } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FileIssue {
  line?: number;
  start_line?: number;
  end_line?: number;
  message: string;
  severity: string;
  suggestion?: string;
  fix_code?: string;
  type?: string;
  validated?: boolean;
  validation_notes?: string;
}

interface FileHealth {
  score: number;
  validated?: boolean;
  validated_by?: string;
  validated_at?: string;
  stamp?: string;
}

interface Props {
  projectId: string;
  filePath: string;
  onClose: () => void;
}

/**
 * 🔴 نمایشگر فایل با هایلایت ایرادات
 * - نمایش محتوای کامل فایل با شماره خط
 * - هایلایت خطوط دارای ایراد
 * - نمایش پیشنهادات به صورت کامنت
 * - امکان دانلود فایل
 */
export default function FileViewer({ projectId, filePath, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [originalContent, setOriginalContent] = useState('');
  const [annotatedContent, setAnnotatedContent] = useState('');
  const [issues, setIssues] = useState<FileIssue[]>([]);
  const [health, setHealth] = useState<FileHealth | null>(null);
  const [language, setLanguage] = useState('text');
  const [showAnnotated, setShowAnnotated] = useState(true);
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);
  const [validating, setValidating] = useState(false);

  // بارگذاری محتوای فایل
  useEffect(() => {
    loadFile();
  }, [filePath]);

  const loadFile = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/projects/${projectId}/health/file/${encodeURIComponent(filePath)}/view?include_suggestions=true`
      );
      const data = await res.json();

      if (data.success) {
        setOriginalContent(data.original_content);
        setAnnotatedContent(data.annotated_content);
        setIssues(data.issues || []);
        setHealth(data.health);
        setLanguage(data.language);
      } else {
        setError(data.detail || 'خطا در بارگذاری فایل');
      }
    } catch (err) {
      setError('خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  // تولید پیشنهادات AI
  const generateSuggestions = async () => {
    setGeneratingSuggestions(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/projects/${projectId}/health/file/${encodeURIComponent(filePath)}/generate-suggestions?model_id=claude`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.success) {
        await loadFile(); // بارگذاری مجدد
      }
    } catch (err) {
      console.error('Error generating suggestions:', err);
    } finally {
      setGeneratingSuggestions(false);
    }
  };

  // اعتبارسنجی فایل
  const validateFile = async () => {
    setValidating(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/projects/${projectId}/health/file/${encodeURIComponent(filePath)}/validate?model_id=claude`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.success) {
        await loadFile(); // بارگذاری مجدد
      }
    } catch (err) {
      console.error('Error validating file:', err);
    } finally {
      setValidating(false);
    }
  };

  // دانلود فایل
  const downloadFile = (withSuggestions: boolean) => {
    window.open(
      `${API_BASE}/api/projects/${projectId}/health/file/${encodeURIComponent(filePath)}/download?include_suggestions=${withSuggestions}`,
      '_blank'
    );
  };

  // رندر خطوط با هایلایت
  const renderLines = useMemo(() => {
    const content = showAnnotated ? annotatedContent : originalContent;
    const lines = content.split('\n');

    // ساخت مپ خطوط دارای ایراد
    const issueLines = new Map<number, FileIssue[]>();
    issues.forEach(issue => {
      const line = issue.line || issue.start_line;
      if (line) {
        if (!issueLines.has(line)) {
          issueLines.set(line, []);
        }
        issueLines.get(line)!.push(issue);
      }
    });

    return lines.map((line, idx) => {
      const lineNum = idx + 1;
      const lineIssues = issueLines.get(lineNum);
      const hasIssue = lineIssues && lineIssues.length > 0;

      // تشخیص خطوط کامنت ایراد (اضافه شده توسط سیستم)
      const isIssueComment = line.includes('[ایراد') || line.includes('[پیشنهاد]') || line.includes('[کد پیشنهادی]');
      const isSuggestionLine = line.includes('💡') || line.includes('✅');

      let bgColor = '';
      let textColor = '';

      if (isIssueComment) {
        if (line.includes('🔴')) {
          bgColor = 'bg-red-900/30';
          textColor = 'text-red-300';
        } else if (line.includes('🟠')) {
          bgColor = 'bg-orange-900/30';
          textColor = 'text-orange-300';
        } else if (line.includes('🟡')) {
          bgColor = 'bg-yellow-900/30';
          textColor = 'text-yellow-300';
        } else if (line.includes('💡')) {
          bgColor = 'bg-blue-900/30';
          textColor = 'text-blue-300';
        } else if (line.includes('✅')) {
          bgColor = 'bg-green-900/30';
          textColor = 'text-green-300';
        }
      } else if (hasIssue) {
        const severity = lineIssues![0].severity;
        if (severity === 'critical') {
          bgColor = 'bg-red-900/20';
        } else if (severity === 'high') {
          bgColor = 'bg-orange-900/20';
        } else if (severity === 'medium') {
          bgColor = 'bg-yellow-900/20';
        }
      }

      return (
        <div
          key={idx}
          className={`flex hover:bg-gray-700/50 ${bgColor}`}
          style={{ direction: 'ltr' }}
        >
          <span className="w-12 text-right pr-2 text-gray-500 select-none border-l border-gray-700 flex-shrink-0">
            {lineNum}
          </span>
          <pre className={`flex-1 px-2 whitespace-pre-wrap break-all ${textColor || 'text-gray-300'}`}>
            {line || ' '}
          </pre>
          {hasIssue && !showAnnotated && (
            <span className="px-2 text-xs text-red-400" title={lineIssues!.map(i => i.message).join('\n')}>
              ⚠️ {lineIssues!.length}
            </span>
          )}
        </div>
      );
    });
  }, [originalContent, annotatedContent, issues, showAnnotated]);

  // رنگ نمره سلامت
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    if (score >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-lg p-8 text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p>در حال بارگذاری فایل...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/90 flex flex-col z-50">
      {/* هدر */}
      <div className="bg-gray-800 border-b border-gray-700 p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white"
          >
            ✕
          </button>
          <div>
            <h2 className="font-bold text-lg" dir="ltr">{filePath}</h2>
            <div className="flex items-center gap-3 text-sm text-gray-400">
              <span>زبان: {language}</span>
              <span>ایرادات: {issues.length}</span>
              {health && (
                <span className={getScoreColor(health.score)}>
                  نمره: {health.score}%
                </span>
              )}
              {health?.validated && (
                <span className="text-green-400">
                  ✅ تایید شده
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* سوییچ نمایش حالت */}
          <div className="flex bg-gray-700 rounded-lg p-1">
            <button
              className={`px-3 py-1 text-sm rounded ${!showAnnotated ? 'bg-blue-600' : ''}`}
              onClick={() => setShowAnnotated(false)}
            >
              اصلی
            </button>
            <button
              className={`px-3 py-1 text-sm rounded ${showAnnotated ? 'bg-blue-600' : ''}`}
              onClick={() => setShowAnnotated(true)}
            >
              با پیشنهادات
            </button>
          </div>

          {/* دکمه‌های عملیات */}
          <button
            onClick={generateSuggestions}
            disabled={generatingSuggestions}
            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm disabled:opacity-50"
          >
            {generatingSuggestions ? '⏳ در حال تولید...' : '🤖 تولید پیشنهادات'}
          </button>

          <button
            onClick={validateFile}
            disabled={validating}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded-lg text-sm disabled:opacity-50"
          >
            {validating ? '⏳ در حال اعتبارسنجی...' : '✅ اعتبارسنجی'}
          </button>

          <div className="flex gap-1">
            <button
              onClick={() => downloadFile(false)}
              className="px-3 py-1.5 bg-gray-600 hover:bg-gray-500 rounded-lg text-sm"
              title="دانلود فایل اصلی"
            >
              📥 اصلی
            </button>
            <button
              onClick={() => downloadFile(true)}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm"
              title="دانلود با پیشنهادات"
            >
              📥 با پیشنهاد
            </button>
          </div>
        </div>
      </div>

      {/* محتوای فایل */}
      <div className="flex-1 overflow-auto bg-gray-900 font-mono text-sm">
        {error ? (
          <div className="p-8 text-center text-red-400">
            <div className="text-4xl mb-4">❌</div>
            <p>{error}</p>
          </div>
        ) : (
          <div className="min-w-max">
            {renderLines}
          </div>
        )}
      </div>

      {/* پنل ایرادات */}
      {issues.length > 0 && (
        <div className="bg-gray-800 border-t border-gray-700 p-4 max-h-48 overflow-auto">
          <h3 className="font-bold mb-2">ایرادات این فایل ({issues.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {issues.slice(0, 10).map((issue, idx) => (
              <div
                key={idx}
                className={`p-2 rounded text-sm border-r-4 ${
                  issue.severity === 'critical' ? 'bg-red-900/30 border-red-500' :
                  issue.severity === 'high' ? 'bg-orange-900/30 border-orange-500' :
                  issue.severity === 'medium' ? 'bg-yellow-900/30 border-yellow-500' :
                  'bg-blue-900/30 border-blue-500'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">خط {issue.line || '?'}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${
                    issue.severity === 'critical' ? 'bg-red-600' :
                    issue.severity === 'high' ? 'bg-orange-600' :
                    issue.severity === 'medium' ? 'bg-yellow-600' :
                    'bg-blue-600'
                  }`}>
                    {issue.severity}
                  </span>
                  {issue.validated !== undefined && (
                    <span className={issue.validated ? 'text-green-400' : 'text-red-400'}>
                      {issue.validated ? '✓' : '✗'}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-gray-300">{issue.message}</p>
                {issue.suggestion && (
                  <p className="mt-1 text-blue-300 text-xs">💡 {issue.suggestion}</p>
                )}
              </div>
            ))}
          </div>
          {issues.length > 10 && (
            <p className="text-center text-gray-500 mt-2">
              و {issues.length - 10} ایراد دیگر...
            </p>
          )}
        </div>
      )}

      {/* برچسب تایید */}
      {health?.stamp && (
        <div className="absolute bottom-4 left-4 bg-green-900/80 text-green-300 px-4 py-2 rounded-lg text-sm">
          {health.stamp}
        </div>
      )}
    </div>
  );
}
