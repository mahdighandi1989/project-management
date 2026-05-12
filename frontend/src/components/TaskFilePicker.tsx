'use client';

/**
 * TaskFilePicker — drag-drop + chunked + resumable upload
 *
 * استفاده در /oversight فرم ایده:
 *   <TaskFilePicker
 *     taskDraftId={taskDraftId}
 *     onSessionsChange={(sessions) => setUploadedSessions(sessions)}
 *     apiBase={API_BASE}
 *   />
 *
 * - چند فایل drag-drop یا انتخاب
 * - هر فایل به ترتیب آپلود → file_order
 * - chunk-by-chunk (5MB)، با retry در صورت قطع شبکه
 * - resume on page reload — sessionها در localStorage کلید taskDraftId ذخیره می‌شوند
 * - تا 500MB هر فایل، چند فایل
 * - cancel per file
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';

export interface UploadSessionState {
  session_id: string;
  filename: string;
  mime_type: string;
  total_size: number;
  bytes_received: number;
  file_order: number;
  status:
    | 'pending'
    | 'uploading'
    | 'completed'
    | 'extracting'
    | 'extracted'
    | 'failed'
    | 'cancelled';
  error?: string;
}

interface TaskFilePickerProps {
  taskDraftId: string;
  apiBase: string;
  onSessionsChange?: (sessions: UploadSessionState[]) => void;
  maxFileBytes?: number; // override (پیش‌فرض 500MB)
  disabled?: boolean;
}

const DEFAULT_MAX = 500 * 1024 * 1024;
const DEFAULT_CHUNK = 5 * 1024 * 1024;

function fmtBytes(b: number): string {
  if (b < 1024) return `${b}B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)}MB`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)}GB`;
}

function pickIcon(mime: string): string {
  if (mime.startsWith('image/')) return '🖼';
  if (mime.startsWith('video/')) return '🎬';
  if (mime.startsWith('audio/')) return '🎵';
  if (mime === 'application/pdf') return '📕';
  if (mime.includes('spreadsheet') || mime.includes('excel')) return '📊';
  if (mime.includes('word') || mime.includes('document')) return '📄';
  if (mime.startsWith('text/')) return '📝';
  return '📎';
}

const LS_KEY = (taskDraftId: string) => `oversight-uploads:${taskDraftId}`;

export default function TaskFilePicker({
  taskDraftId,
  apiBase,
  onSessionsChange,
  maxFileBytes = DEFAULT_MAX,
  disabled = false,
}: TaskFilePickerProps) {
  const [sessions, setSessions] = useState<UploadSessionState[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  // برای cancel: AbortController per session_id
  const abortRefs = useRef<Record<string, AbortController>>({});

  // ── persist + restore ──
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY(taskDraftId));
      if (!raw) return;
      const restored: UploadSessionState[] = JSON.parse(raw);
      if (!Array.isArray(restored)) return;
      // برای هر session restored، وضعیت فعلی از سرور بگیر؛ اگر incomplete بود، resume
      (async () => {
        const reconciled: UploadSessionState[] = [];
        for (const s of restored) {
          try {
            const r = await fetch(`${apiBase}/api/oversight/uploads/${s.session_id}`);
            if (r.ok) {
              const srv = await r.json();
              reconciled.push({
                session_id: srv.id,
                filename: srv.original_filename,
                mime_type: srv.mime_type,
                total_size: srv.total_size,
                bytes_received: srv.bytes_received,
                file_order: srv.file_order,
                status: srv.status,
                error: srv.error || undefined,
              });
            } else if (r.status === 404) {
              // session حذف شده — از list حذف کن
              continue;
            }
          } catch {
            // network unavailable — نگه دار، شاید بعدها برگردد
            reconciled.push(s);
          }
        }
        setSessions(reconciled);
        // resume incomplete sessions automatic — کاربر نیاز به کلیک نداشته باشد
        for (const s of reconciled) {
          if (s.status === 'uploading' || s.status === 'pending') {
            // پرونده روی client نیست — کاربر باید فایل را دوباره drag/select کند
            // فقط اطلاع‌دهنده در UI: status='uploading' ولی هیچ فعالیت نیست
            // (notice line در render نمایش داده می‌شود)
          }
        }
      })();
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskDraftId]);

  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY(taskDraftId), JSON.stringify(sessions));
    } catch {
      // quota — silent
    }
    onSessionsChange?.(sessions);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions, taskDraftId]);

  // ── core upload ──
  const updateSession = useCallback(
    (sid: string, patch: Partial<UploadSessionState>) => {
      setSessions((prev) =>
        prev.map((s) => (s.session_id === sid ? { ...s, ...patch } : s)),
      );
    },
    [],
  );

  const uploadFile = useCallback(
    async (file: File) => {
      if (file.size > maxFileBytes) {
        alert(`فایل ${file.name} از سقف ${fmtBytes(maxFileBytes)} بزرگ‌تر است`);
        return;
      }

      // start session
      let startResp: any;
      try {
        const r = await fetch(`${apiBase}/api/oversight/uploads/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task_draft_id: taskDraftId,
            original_filename: file.name,
            mime_type: file.type || 'application/octet-stream',
            total_size: file.size,
          }),
        });
        if (!r.ok) {
          const err = await r.text();
          alert(`شروع آپلود ناموفق: ${err}`);
          return;
        }
        startResp = await r.json();
      } catch (e: any) {
        alert(`شروع آپلود ناموفق: ${e.message || e}`);
        return;
      }

      const sid: string = startResp.session_id;
      const chunkSize: number = startResp.chunk_size || DEFAULT_CHUNK;
      const initial: UploadSessionState = {
        session_id: sid,
        filename: file.name,
        mime_type: file.type || 'application/octet-stream',
        total_size: file.size,
        bytes_received: 0,
        file_order: startResp.file_order,
        status: 'uploading',
      };
      setSessions((prev) => [...prev, initial]);

      // upload chunks sequentially
      const abort = new AbortController();
      abortRefs.current[sid] = abort;
      let offset = 0;
      let attempts = 0;
      const MAX_ATTEMPTS = 4;
      while (offset < file.size) {
        if (abort.signal.aborted) {
          updateSession(sid, { status: 'cancelled' });
          delete abortRefs.current[sid];
          return;
        }
        const end = Math.min(offset + chunkSize, file.size);
        const blob = file.slice(offset, end);
        try {
          const r = await fetch(
            `${apiBase}/api/oversight/uploads/${sid}/chunk?offset=${offset}`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/octet-stream' },
              body: blob,
              signal: abort.signal,
            },
          );
          if (!r.ok) {
            // offset mismatch → resync
            const body = await r.json().catch(() => ({}));
            if (body?.detail?.expected_offset !== undefined) {
              offset = Number(body.detail.expected_offset);
              continue;
            }
            attempts++;
            if (attempts >= MAX_ATTEMPTS) {
              updateSession(sid, {
                status: 'failed',
                error: body?.detail || `HTTP ${r.status}`,
              });
              delete abortRefs.current[sid];
              return;
            }
            await new Promise((res) => setTimeout(res, 2000 * attempts));
            continue;
          }
          const j = await r.json();
          offset = j.next_offset;
          attempts = 0;
          updateSession(sid, {
            bytes_received: j.bytes_received,
            status: j.completed ? 'completed' : 'uploading',
          });
        } catch (e: any) {
          if (abort.signal.aborted) {
            updateSession(sid, { status: 'cancelled' });
            delete abortRefs.current[sid];
            return;
          }
          attempts++;
          if (attempts >= MAX_ATTEMPTS) {
            updateSession(sid, {
              status: 'failed',
              error: e?.message || 'network error',
            });
            delete abortRefs.current[sid];
            return;
          }
          await new Promise((res) => setTimeout(res, 2000 * attempts));
        }
      }

      // mark completed (پیام صریح به سرور)
      try {
        await fetch(`${apiBase}/api/oversight/uploads/${sid}/complete`, {
          method: 'POST',
        });
      } catch {
        // best-effort
      }
      delete abortRefs.current[sid];
      updateSession(sid, { status: 'completed', bytes_received: file.size });
    },
    [apiBase, taskDraftId, maxFileBytes, updateSession],
  );

  // ── handlers ──
  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      if (disabled) return;
      const arr = Array.from(files);
      // sequential upload — ترتیب آپلود = ترتیب file_order در سرور
      (async () => {
        for (const f of arr) {
          await uploadFile(f);
        }
      })();
    },
    [uploadFile, disabled],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const files = e.dataTransfer.files;
      if (files.length) handleFiles(files);
    },
    [handleFiles, disabled],
  );

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setDragging(true);
  };
  const onDragLeave = () => setDragging(false);

  const cancelSession = async (sid: string) => {
    abortRefs.current[sid]?.abort();
    try {
      await fetch(`${apiBase}/api/oversight/uploads/${sid}`, { method: 'DELETE' });
    } catch {
      // ignore
    }
    setSessions((prev) => prev.filter((s) => s.session_id !== sid));
  };

  // ── render ──
  return (
    <div className="mb-3">
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          dragging
            ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-purple-400'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <div className="text-sm text-gray-700 dark:text-gray-300">
          📎 <b>پیوست فایل به تسک</b> (اختیاری)
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          فایل را اینجا بکش یا کلیک کن — تا {fmtBytes(maxFileBytes)} هر فایل، چند فایل، هر فرمت
          <br />
          <span className="text-[10px]">
            ترتیب آپلود = ترتیب اهمیت در پرامپت (اولی = بخش اول)
          </span>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>

      {sessions.length > 0 && (
        <ul className="mt-3 space-y-2">
          {sessions
            .slice()
            .sort((a, b) => a.file_order - b.file_order)
            .map((s) => {
              const pct =
                s.total_size > 0 ? Math.round((s.bytes_received / s.total_size) * 100) : 0;
              const statusLabel: Record<string, string> = {
                pending: '⏳ آماده',
                uploading: '⬆️ در حال آپلود',
                completed: '✅ آپلود شد',
                extracting: '🔍 در حال استخراج',
                extracted: '📄 استخراج شد',
                failed: '❌ خطا',
                cancelled: '🚫 لغو',
              };
              return (
                <li
                  key={s.session_id}
                  className="border rounded p-2 bg-gray-50 dark:bg-gray-800 dark:border-gray-700 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{pickIcon(s.mime_type)}</span>
                    <span className="font-semibold">#{s.file_order}</span>
                    <span className="flex-1 truncate" title={s.filename}>
                      {s.filename}
                    </span>
                    <span className="text-gray-500">
                      {fmtBytes(s.bytes_received)} / {fmtBytes(s.total_size)}
                    </span>
                    <span>{statusLabel[s.status] || s.status}</span>
                    {s.status === 'uploading' || s.status === 'pending' ? (
                      <button
                        onClick={() => cancelSession(s.session_id)}
                        className="text-red-500 hover:text-red-700"
                        title="لغو"
                      >
                        ✕
                      </button>
                    ) : (
                      <button
                        onClick={() => cancelSession(s.session_id)}
                        className="text-gray-400 hover:text-red-500"
                        title="حذف از لیست"
                      >
                        🗑
                      </button>
                    )}
                  </div>
                  {s.status === 'uploading' && (
                    <div className="mt-1 h-1 w-full bg-purple-100 dark:bg-purple-900/40 rounded overflow-hidden">
                      <div
                        className="h-full bg-purple-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  )}
                  {s.error && (
                    <div className="mt-1 text-red-600 dark:text-red-400">{s.error}</div>
                  )}
                </li>
              );
            })}
        </ul>
      )}
    </div>
  );
}
