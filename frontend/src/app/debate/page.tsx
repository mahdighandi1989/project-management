/**
 * Debate Page - Main debate creation and viewing interface
 */

'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useDebate } from '@/hooks/useDebate';
import { settingsApi, modelsApi, WorkMode, Model } from '@/services/api';
import {
  PaperAirplaneIcon,
  PlayIcon,
  ArrowPathIcon,
  CheckIcon,
  XMarkIcon,
  ChevronDownIcon,
  PaperClipIcon,
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
        selectedModels.length > 0 ? selectedModels : undefined
      );
    } catch (err) {
      console.error('Error creating debate:', err);
    }
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
      summarizing: { color: 'badge-primary', text: 'خلاصه‌نویسی' },
      completed: { color: 'badge-success', text: 'تکمیل شده' },
      failed: { color: 'badge-danger', text: 'خطا' },
    };
    const badge = badges[status] || { color: '', text: status };
    return <span className={`badge ${badge.color}`}>{badge.text}</span>;
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
                  onFilesUploaded={(files) => setUploadedFiles(files)}
                  maxFiles={5}
                  maxSizeMB={25}
                  storeInGithub={true}
                />
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
                  {getStatusBadge(currentDebate.status)}
                </div>
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
