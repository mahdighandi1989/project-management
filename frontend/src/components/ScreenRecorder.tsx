'use client';

/**
 * ScreenRecorder — دکمه + تنظیمات ضبط ویدئوی صفحه برای «بازرس ویژه».
 *
 * کنار دکمهٔ اسکرین‌شات قرار می‌گیرد. با زدن آن یک رکورد حالت فیلم شروع
 * می‌شود (با صدا، طبق تنظیمات). هنگام توقف:
 *   1) فایل ویدئو روی سرور آپلود می‌شود
 *   2) لاگ‌های console + تعاملات کاربر ثبت و transcript صوت تولید می‌شود
 *   3) از طریق onComplete یک payload آمادهٔ ارسال به مرکز نظارت تحویل می‌شود
 *
 * این کامپوننت منطق ضبط را به useScreenRecording واگذار می‌کند و خودش
 * صرفاً UI + چرخهٔ آپلود/finalize را مدیریت می‌کند.
 */
import React, { useState } from 'react';
import { VideoCameraIcon, StopIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import {
  useScreenRecording,
  type AudioSource,
  type ConsoleEntry,
  type InteractionEvent,
} from '../hooks/useScreenRecording';

export interface ScreenRecordingPayload {
  recording_id: number | null;
  recording_video_file_id: string | null;
  recording_audio_file_id: string | null;
  recording_duration_ms: number;
  transcript: string;
  console_logs: ConsoleEntry[];
  user_interactions: InteractionEvent[];
  video_url: string | null;
  transcription_error?: string | null;
}

interface ScreenRecorderProps {
  apiBase: string;
  projectId: string;
  inspectorSessionId?: string | null;
  /** فراخوانی پس از پایان و آپلود کامل ضبط، با payload آمادهٔ ارسال. */
  onComplete: (payload: ScreenRecordingPayload) => void;
  /** لاگ‌های backend که parent جداگانه جمع‌آوری کرده (اختیاری) برای finalize. */
  getBackendLogs?: () => Array<Record<string, unknown>>;
  className?: string;
  compact?: boolean;
}

const AUDIO_OPTIONS: Array<{ value: AudioSource; label: string }> = [
  { value: 'mic', label: '🎤 میکروفون' },
  { value: 'system', label: '🔊 صدای سیستم' },
  { value: 'both', label: '🎤+🔊 هر دو' },
  { value: 'none', label: '🔇 بدون صدا' },
];

function fmtDuration(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export const ScreenRecorder: React.FC<ScreenRecorderProps> = ({
  apiBase,
  projectId,
  inspectorSessionId,
  onComplete,
  getBackendLogs,
  className = '',
  compact = false,
}) => {
  const rec = useScreenRecording();
  const [showSettings, setShowSettings] = useState(false);
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const handleStart = async () => {
    setStatusMsg(null);
    setBusy(true);
    try {
      // ساخت رکورد metadata روی سرور (برای ثبت تنظیمات + لاگ شروع)
      let recordingId: number | null = null;
      try {
        const r = await fetch(`${apiBase}/api/screen-recording/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            inspector_session_id: inspectorSessionId || null,
            audio_source: rec.settings.audioSource,
            handsfree: rec.settings.handsfree,
          }),
        });
        if (r.ok) {
          const data = await r.json();
          recordingId = data?.recording?.id ?? null;
        }
      } catch {
        /* اگر سرور در دسترس نبود، ضبط محلی همچنان ادامه می‌یابد */
      }
      (rec as unknown as { _recordingId?: number | null })._recordingId = recordingId;
      const ok = await rec.start();
      if (!ok) {
        setStatusMsg(rec.error || 'شروع ضبط ناموفق بود');
      } else {
        setShowSettings(false);
      }
    } finally {
      setBusy(false);
    }
  };

  const handleStop = async () => {
    setBusy(true);
    setStatusMsg('در حال نهایی‌سازی ضبط…');
    try {
      const result = await rec.stop();
      const recordingId =
        (rec as unknown as { _recordingId?: number | null })._recordingId ?? null;

      let videoFileId: string | null = null;
      let videoUrl: string | null = null;
      let transcript = '';
      let transcriptionError: string | null = null;

      // 1) آپلود ویدئو
      if (recordingId && result.videoBlob) {
        try {
          setStatusMsg('در حال آپلود ویدئو…');
          const fd = new FormData();
          const ext = result.mimeType.includes('mp4') ? 'mp4' : 'webm';
          fd.append('file', result.videoBlob, `recording-${recordingId}.${ext}`);
          fd.append('kind', 'video');
          const up = await fetch(`${apiBase}/api/screen-recording/${recordingId}/upload`, {
            method: 'POST',
            body: fd,
          });
          if (up.ok) {
            const upData = await up.json();
            videoFileId = upData?.file_id ?? null;
            if (videoFileId) videoUrl = `${apiBase}/api/screen-recording/file/${videoFileId}`;
          }
        } catch (e) {
          console.warn('video upload failed', e);
        }
      }

      // 2) finalize: ثبت لاگ‌ها/تعاملات + transcription صوت (سمت سرور)
      if (recordingId) {
        try {
          setStatusMsg('در حال تبدیل گفتار به متن…');
          const fin = await fetch(`${apiBase}/api/screen-recording/${recordingId}/finalize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              duration_ms: result.durationMs,
              console_logs: result.consoleLogs,
              backend_logs: getBackendLogs ? getBackendLogs() : [],
              user_interactions: result.interactions,
              auto_transcribe: result.settings.audioSource !== 'none',
            }),
          });
          if (fin.ok) {
            const finData = await fin.json();
            transcript = finData?.recording?.transcript || '';
            transcriptionError = finData?.transcription_error || null;
          }
        } catch (e) {
          console.warn('finalize failed', e);
        }
      }

      setStatusMsg(null);
      onComplete({
        recording_id: recordingId,
        recording_video_file_id: videoFileId,
        recording_audio_file_id: null,
        recording_duration_ms: result.durationMs,
        transcript,
        console_logs: result.consoleLogs,
        user_interactions: result.interactions,
        video_url: videoUrl,
        transcription_error: transcriptionError,
      });
    } finally {
      setBusy(false);
    }
  };

  if (!rec.isSupported) {
    return (
      <span
        className={`text-[10px] text-gray-400 ${className}`}
        title="مرورگر از ضبط صفحه پشتیبانی نمی‌کند"
      >
        🎬 (ضبط پشتیبانی نمی‌شود)
      </span>
    );
  }

  return (
    <div className={`relative inline-flex items-center gap-1 ${className}`}>
      {!rec.isRecording ? (
        <>
          <button
            type="button"
            onClick={handleStart}
            disabled={busy}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 disabled:opacity-50"
            title="شروع ضبط ویدئو از صفحه (با صدا و لاگ‌ها)"
          >
            <VideoCameraIcon className="h-4 w-4" />
            {!compact && <span>ضبط ویدئو</span>}
          </button>
          <button
            type="button"
            onClick={() => setShowSettings((s) => !s)}
            className="inline-flex items-center rounded-md px-1.5 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
            title="تنظیمات صدا"
            aria-label="تنظیمات ضبط صدا"
          >
            <Cog6ToothIcon className="h-4 w-4" />
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={handleStop}
          disabled={busy}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white animate-pulse disabled:opacity-60"
          title="توقف ضبط"
        >
          <StopIcon className="h-4 w-4" />
          <span>توقف · {fmtDuration(rec.durationMs)}</span>
        </button>
      )}

      {showSettings && !rec.isRecording && (
        <div className="absolute top-full right-0 z-50 mt-1 w-56 rounded-lg border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 text-xs font-bold text-gray-700 dark:text-gray-200">
            🎙 تنظیمات ضبط صدا
          </div>
          <label className="mb-1 block text-[11px] text-gray-500">منبع صدا</label>
          <select
            value={rec.settings.audioSource}
            onChange={(e) =>
              rec.setSettings((s) => ({ ...s, audioSource: e.target.value as AudioSource }))
            }
            className="mb-2 w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-800"
          >
            {AUDIO_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-[11px] text-gray-600 dark:text-gray-300">
            <input
              type="checkbox"
              checked={rec.settings.handsfree}
              onChange={(e) =>
                rec.setSettings((s) => ({ ...s, handsfree: e.target.checked }))
              }
            />
            حالت هندزفری (بدون حذف اکو/نویز)
          </label>
        </div>
      )}

      {statusMsg && (
        <span className="text-[10px] text-purple-500" role="status">
          {statusMsg}
        </span>
      )}
    </div>
  );
};

export default ScreenRecorder;
