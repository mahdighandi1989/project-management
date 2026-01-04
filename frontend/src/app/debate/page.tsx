/**
 * Debate Page - Main debate creation and viewing interface
 */

'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useDebate } from '@/hooks/useDebate';
import { settingsApi, modelsApi, WorkMode, Model, DebateAttachment } from '@/services/api';
import {
  PaperAirplaneIcon,
  PlayIcon,
  ArrowPathIcon,
  CheckIcon,
  XMarkIcon,
  ChevronDownIcon,
  PaperClipIcon,
  DocumentArrowDownIcon,
  SparklesIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import FileUpload from '@/components/FileUpload';

// Component that uses searchParams
function DebateContent() {
  const searchParams = useSearchParams();
  const initialMode = searchParams.get('mode') || 'auto';

  const {
    currentDebate,
    isLoading,
    error,
    createDebate,
    runRound,
    runFullDebate,
    runScoring,
    runJudging,
    runSummary,
    clearError,
    reset,
  } = useDebate();

  const [prompt, setPrompt] = useState('');
  const [selectedMode, setSelectedMode] = useState(initialMode);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [workModes, setWorkModes] = useState<WorkMode[]>([]);
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const [fileAttachments, setFileAttachments] = useState<DebateAttachment[]>([]);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [modesRes, modelsRes] = await Promise.all([
        settingsApi.workModes(),
        modelsApi.available(),
      ]);
      setWorkModes(modesRes.data);
      setAvailableModels(modelsRes.data);
    } catch (err) {
      console.error('Error loading data:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    try {
      await createDebate(
        prompt,
        selectedMode,
        selectedModels.length > 0 ? selectedModels : undefined,
        fileAttachments.length > 0 ? fileAttachments : undefined
      );
    } catch (err) {
      console.error('Error creating debate:', err);
    }
  };

  // خواندن محتوای فایل‌ها وقتی فایل جدید اضافه می‌شود
  const handleFilesSelected = async (files: any[]) => {
    setUploadedFiles(files);

    // خواندن محتوای فایل‌ها برای ارسال به مناظره
    const attachments: DebateAttachment[] = [];

    for (const fileInfo of files) {
      if (fileInfo.file && fileInfo.status === 'pending') {
        // خواندن محتوای فایل قبل از آپلود
        try {
          const content = await readFileContent(fileInfo.file);
          attachments.push({
            filename: fileInfo.name,
            content: content,
            type: fileInfo.type,
            file_category: fileInfo.result?.optimal_settings?.file_category || 'unknown'
          });
        } catch (err) {
          console.error('Error reading file:', fileInfo.name, err);
        }
      } else if (fileInfo.status === 'completed' && fileInfo.file) {
        // فایل آپلود شده - محتوا رو دوباره بخون
        try {
          const content = await readFileContent(fileInfo.file);
          attachments.push({
            filename: fileInfo.name,
            content: content,
            type: fileInfo.type,
            file_category: fileInfo.result?.optimal_settings?.file_category || 'unknown'
          });
        } catch (err) {
          console.error('Error reading uploaded file:', fileInfo.name, err);
        }
      }
    }

    setFileAttachments(attachments);
  };

  // تابع خواندن محتوای فایل
  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        resolve(content);
      };
      reader.onerror = (e) => reject(e);

      // برای فایل‌های متنی
      if (file.type.startsWith('text/') ||
          file.name.match(/\.(txt|md|json|yaml|yml|xml|csv|html|css|js|ts|py|java|cpp|c|h|go|rs|php|rb|mq4|mq5|mqh|sql|sh|bat|jsx|tsx|vue)$/i)) {
        reader.readAsText(file);
      } else {
        // برای فایل‌های باینری، base64 کن
        reader.readAsDataURL(file);
      }
    });
  };

  const handleRunFull = async () => {
    await runFullDebate();
  };

  const handleRunStep = async (step: string) => {
    switch (step) {
      case 'round':
        const nextRound = (currentDebate?.rounds_count || 0) + 1;
        await runRound(nextRound);
        break;
      case 'scoring':
        await runScoring();
        break;
      case 'judging':
        await runJudging();
        break;
      case 'summary':
        await runSummary();
        break;
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { color: string; text: string }> = {
      pending: { color: 'badge-warning', text: 'در انتظار' },
      running: { color: 'badge-primary', text: 'در حال اجرا' },
      scoring: { color: 'badge-primary', text: 'امتیازدهی' },
      judging: { color: 'badge-primary', text: 'داوری' },
      synthesizing: { color: 'badge-primary', text: 'ترکیب خروجی' },
      generating: { color: 'badge-primary', text: 'تولید فایل' },
      summarizing: { color: 'badge-primary', text: 'خلاصه‌نویسی' },
      completed: { color: 'badge-success', text: 'تکمیل شده' },
      failed: { color: 'badge-danger', text: 'خطا' },
    };
    const badge = badges[status] || { color: '', text: status };
    return <span className={`badge ${badge.color}`}>{badge.text}</span>;
  };

  const getModeBadge = (mode: string) => {
    const modes: Record<string, { color: string; text: string; icon: string }> = {
      debate: { color: 'bg-red-100 text-red-700', text: 'مناظره', icon: '🥊' },
      collaboration: { color: 'bg-green-100 text-green-700', text: 'همکاری', icon: '🤝' },
      deep_research: { color: 'bg-purple-100 text-purple-700', text: 'تحقیق عمیق', icon: '🔍' },
      quick: { color: 'bg-yellow-100 text-yellow-700', text: 'سریع', icon: '⚡' },
      creative: { color: 'bg-pink-100 text-pink-700', text: 'خلاقانه', icon: '🎨' },
      auto: { color: 'bg-blue-100 text-blue-700', text: 'خودکار', icon: '🤖' },
    };
    const modeInfo = modes[mode] || { color: 'bg-gray-100 text-gray-700', text: mode, icon: '📝' };
    return (
      <span className={`px-2 py-1 rounded-full text-sm ${modeInfo.color}`}>
        {modeInfo.icon} {modeInfo.text}
      </span>
    );
  };

  // دانلود فایل تولید شده
  const downloadGeneratedFile = (file: any) => {
    const blob = new Blob([file.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            مناظره AI
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            سوال خود را بپرسید و مدل‌های مختلف را به چالش بکشید
          </p>
        </div>
        {currentDebate && (
          <button onClick={reset} className="btn btn-secondary">
            مناظره جدید
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-center justify-between">
          <span className="text-red-600 dark:text-red-300">{error}</span>
          <button onClick={clearError}>
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Create Form */}
      {!currentDebate && (
        <form onSubmit={handleSubmit} className="card space-y-4">
          {/* Mode Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              حالت کاری
            </label>
            <div className="flex flex-wrap gap-2">
              {workModes.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setSelectedMode(mode.id)}
                  className={`px-4 py-2 rounded-lg border-2 transition-all ${
                    selectedMode === mode.id
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-600'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="ml-2">{mode.icon}</span>
                  {mode.name_fa}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              سوال یا موضوع
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="سوال خود را اینجا بنویسید..."
              className="textarea h-32"
              required
            />
          </div>

          {/* File Upload Section */}
          <div>
            <button
              type="button"
              onClick={() => setShowFileUpload(!showFileUpload)}
              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-primary-500"
            >
              <PaperClipIcon className="w-5 h-5" />
              پیوست فایل
              {uploadedFiles.length > 0 && (
                <span className="badge badge-primary text-xs">{uploadedFiles.length}</span>
              )}
            </button>

            {showFileUpload && (
              <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <FileUpload
                  entityType="debate"
                  onFilesUploaded={handleFilesSelected}
                  maxFiles={10}
                  maxSizeMB={100}
                  storeInGithub={false}
                />
                {fileAttachments.length > 0 && (
                  <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <p className="text-sm text-green-700 dark:text-green-300">
                      {fileAttachments.length} فایل آماده ارسال به مناظره
                    </p>
                    <ul className="mt-2 text-xs text-green-600 dark:text-green-400">
                      {fileAttachments.map((att, i) => (
                        <li key={i}>• {att.filename} ({att.file_category})</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Advanced Options */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
            >
              <ChevronDownIcon className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
              تنظیمات پیشرفته
            </button>

            {showAdvanced && (
              <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  انتخاب مدل‌ها (اختیاری)
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableModels.map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => {
                        setSelectedModels((prev) =>
                          prev.includes(model.id)
                            ? prev.filter((m) => m !== model.id)
                            : [...prev, model.id]
                        );
                      }}
                      className={`px-3 py-1.5 rounded-lg text-sm border transition-all ${
                        selectedModels.includes(model.id)
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                          : 'border-gray-200 dark:border-gray-700'
                      }`}
                    >
                      {model.name}
                    </button>
                  ))}
                </div>
                {selectedModels.length > 0 && (
                  <p className="mt-2 text-sm text-gray-500">
                    {selectedModels.length} مدل انتخاب شده
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Submit */}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isLoading || !prompt.trim()}
              className="btn btn-primary flex items-center gap-2"
            >
              {isLoading ? (
                <div className="spinner w-5 h-5" />
              ) : (
                <PaperAirplaneIcon className="w-5 h-5 rotate-180" />
              )}
              شروع مناظره
            </button>
          </div>
        </form>
      )}

      {/* Debate View */}
      {currentDebate && (
        <div className="space-y-6">
          {/* Debate Info */}
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="font-bold text-gray-900 dark:text-white">
                  {currentDebate.prompt.slice(0, 100)}
                  {currentDebate.prompt.length > 100 && '...'}
                </h2>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span>{currentDebate.models.length} مدل</span>
                  <span>{currentDebate.rounds.length} دور</span>
                  {getModeBadge(currentDebate.mode)}
                  {getStatusBadge(currentDebate.status)}
                </div>
                {/* نمایش حالت تشخیص داده شده */}
                {currentDebate.detected_mode && currentDebate.detected_mode !== currentDebate.mode && (
                  <div className="mt-2 text-xs text-gray-500">
                    <BeakerIcon className="w-4 h-4 inline mr-1" />
                    حالت تشخیص داده شده: {getModeBadge(currentDebate.detected_mode)}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                {currentDebate.status !== 'completed' && (
                  <>
                    <button
                      onClick={handleRunFull}
                      disabled={isLoading}
                      className="btn btn-primary flex items-center gap-2"
                    >
                      {isLoading ? (
                        <div className="spinner w-5 h-5" />
                      ) : (
                        <PlayIcon className="w-5 h-5" />
                      )}
                      اجرای کامل
                    </button>
                    <button
                      onClick={() => handleRunStep('round')}
                      disabled={isLoading}
                      className="btn btn-secondary"
                    >
                      دور بعدی
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Models */}
            <div className="flex flex-wrap gap-2">
              {Object.entries(currentDebate.role_assignments).map(([modelId, role]) => (
                <div
                  key={modelId}
                  className="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-sm"
                >
                  <span className="font-medium">{modelId}</span>
                  <span className="text-gray-500 dark:text-gray-400 mr-2">
                    ({role})
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Rounds */}
          {currentDebate.rounds.map((round, roundIndex) => (
            <div key={roundIndex} className="space-y-4">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                دور {roundIndex + 1}
              </h3>
              {round.map((response, respIndex) => (
                <div
                  key={respIndex}
                  className={`response-card ${response.error ? 'error' : 'success'}`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{response.role_icon}</span>
                    <div>
                      <h4 className="font-bold text-gray-900 dark:text-white">
                        {response.model_name}
                      </h4>
                      <p className="text-sm text-gray-500">
                        {response.role_name} •{' '}
                        {response.latency_ms}ms •{' '}
                        {response.tokens_used} توکن
                      </p>
                    </div>
                  </div>
                  <div className="prose dark:prose-invert max-w-none">
                    {response.error ? (
                      <p className="text-red-500">{response.error}</p>
                    ) : (
                      <p className="whitespace-pre-wrap">{response.content}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ))}

          {/* Scores */}
          {currentDebate.scores.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                امتیازات
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-right py-2">امتیازدهنده</th>
                      <th className="text-right py-2">هدف</th>
                      <th className="text-center py-2">امتیاز</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentDebate.scores.map((score: any, index: number) => (
                      <tr key={index} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="py-2">{score.scorer_model}</td>
                        <td className="py-2">{score.target_model}</td>
                        <td className="py-2 text-center">
                          <span className="badge badge-primary">{score.total}/100</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Judge Result */}
          {currentDebate.judge_result && (
            <div className="card bg-gradient-to-br from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 border-2 border-yellow-200 dark:border-yellow-800">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                داوری
              </h3>
              <div className="space-y-3">
                <p>
                  <span className="font-medium">برنده:</span>{' '}
                  <span className="text-lg">{currentDebate.judge_result.winner}</span>
                </p>
                <p>
                  <span className="font-medium">دلیل:</span>{' '}
                  {currentDebate.judge_result.reasoning}
                </p>
              </div>
            </div>
          )}

          {/* Synthesized Output - خروجی ترکیب شده */}
          {currentDebate.synthesized_output && (
            <div className="card bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border-2 border-emerald-200 dark:border-emerald-800">
              <div className="flex items-center gap-3 mb-4">
                <SparklesIcon className="w-6 h-6 text-emerald-600" />
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                  خروجی نهایی ترکیب شده
                </h3>
              </div>
              <div className="prose dark:prose-invert max-w-none">
                <p className="whitespace-pre-wrap">{currentDebate.synthesized_output.content}</p>
              </div>

              {/* Code Blocks */}
              {currentDebate.synthesized_output.code_blocks?.length > 0 && (
                <div className="mt-4 space-y-3">
                  <h4 className="font-medium text-gray-700 dark:text-gray-300">
                    کدهای استخراج شده:
                  </h4>
                  {currentDebate.synthesized_output.code_blocks.map((block: any, idx: number) => (
                    <div key={idx} className="bg-gray-900 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
                        <span className="text-sm text-gray-400">{block.language}</span>
                        <button
                          onClick={() => downloadGeneratedFile({
                            filename: block.filename || `code_${idx + 1}.${block.language}`,
                            content: block.code
                          })}
                          className="text-xs text-emerald-400 hover:text-emerald-300"
                        >
                          دانلود
                        </button>
                      </div>
                      <pre className="p-4 text-sm text-gray-100 overflow-x-auto">
                        <code>{block.code}</code>
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Generated Files - فایل‌های تولید شده */}
          {currentDebate.generated_files?.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-3 mb-4">
                <DocumentArrowDownIcon className="w-6 h-6 text-blue-600" />
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                  فایل‌های تولید شده
                </h3>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {currentDebate.generated_files.map((file: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 dark:text-white truncate">
                          {file.filename}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {file.language} • {file.description}
                        </p>
                      </div>
                      <button
                        onClick={() => downloadGeneratedFile(file)}
                        className="ml-2 p-2 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
                      >
                        <DocumentArrowDownIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* دکمه دانلود همه */}
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => {
                    currentDebate.generated_files.forEach((file: any) => {
                      setTimeout(() => downloadGeneratedFile(file), 100);
                    });
                  }}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <DocumentArrowDownIcon className="w-5 h-5" />
                  دانلود همه فایل‌ها
                </button>
              </div>
            </div>
          )}

          {/* Summary */}
          {currentDebate.summary && (
            <div className="card">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                خلاصه
              </h3>
              <div className="prose dark:prose-invert max-w-none">
                <p className="whitespace-pre-wrap">{currentDebate.summary}</p>
              </div>
            </div>
          )}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="card flex items-center justify-center py-8">
              <div className="spinner w-12 h-12" />
              <span className="mr-4 text-gray-500">در حال پردازش...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Loading fallback
function DebateLoading() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
    </div>
  );
}

// Main page component with Suspense
export default function DebatePage() {
  return (
    <Suspense fallback={<DebateLoading />}>
      <DebateContent />
    </Suspense>
  );
}
