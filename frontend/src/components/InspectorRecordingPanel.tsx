/**
 * 🎬 Inspector Recording Panel — UI کامل برای ضبط دوحالته از تب بازرس ویژه.
 *
 * این component یک "نقطه تک" است که همه UI ضبط را در خود دارد:
 *   - Picker (انتخاب حالت A/B + تنظیمات صدا)
 *   - نوار وضعیت در طول ضبط
 *   - Modal آماده‌سازی (processing)
 *   - Modal پیش‌نمایش با transcript editor + چک‌باکس ارسال به نظارت
 *   - منطق client-side: MediaRecorder (audio + video B), screenshot polling (A)
 *
 * یک دکمه render می‌کند که در parent (inspector tab) کنار دکمه screenshot
 * گذاشته می‌شود. وقتی کلیک شد، کل flow را خودش مدیریت می‌کند.
 *
 * Backend dependencies: /api/recording/inspector/* (commits 1-5)
 */
'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE =
  (typeof process !== 'undefined' ? (process as any).env?.NEXT_PUBLIC_API_URL : '') || '';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

type RecordingMode = 'A' | 'B';
type Phase =
  | 'idle'
  | 'picker'
  | 'starting'
  | 'recording'
  | 'stopping'
  | 'processing'
  | 'preview'
  | 'finalizing'
  | 'completed'
  | 'error';

interface AudioConfig {
  mic: boolean;
  system: boolean;
  micDeviceId: string | null;
}

interface PreviewData {
  transcript: string;
  transcript_language: string;
  visual_summary: any[];
  location_timeline: any[];
  interactions: any[];
  console_logs_count: number;
  backend_logs_count: number;
  prompt: string;
  prompt_chars?: number;
}

interface InspectorRecordingPanelProps {
  /** project_id که برای backend (watched_id یا hint) ارسال می‌شود */
  projectId: string;
  /** نام repo (e.g., "owner/repo") برای caption تلگرام و resolve watched */
  projectFullName?: string;
  /** آیا feature فعال است (مثلاً اگر کاربر inspector را باز کرده) */
  enabled: boolean;
  /** صدا زده می‌شود وقتی recording completed/finalized — برای refresh state */
  onComplete?: (result: { task_id?: string | null; chat_message_sent?: boolean }) => void;
  /** کلیک روی icon این button — رنگ/سایز را با buttonClassName کنترل کن */
  buttonClassName?: string;
  /** ref به iframe بازرس برای دسترسی به URL و post message — اختیاری */
  inspectorIframeRef?: React.MutableRefObject<HTMLIFrameElement | null>;
  /** snapshot لاگ‌های frontend console برای ارسال در /stop */
  getConsoleLogsSnapshot?: () => any[];
  /** snapshot لاگ‌های backend برای ارسال در /stop */
  getBackendLogsSnapshot?: () => any[];
}

// ────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────

export default function InspectorRecordingPanel(props: InspectorRecordingPanelProps) {
  const {
    projectId,
    projectFullName,
    enabled,
    onComplete,
    buttonClassName,
    inspectorIframeRef,
    getConsoleLogsSnapshot,
    getBackendLogsSnapshot,
  } = props;

  const [phase, setPhase] = useState<Phase>('idle');
  const [mode, setMode] = useState<RecordingMode>('A');
  const [audioConfig, setAudioConfig] = useState<AudioConfig>({
    mic: true,
    system: false,
    micDeviceId: null,
  });
  const [micDevices, setMicDevices] = useState<MediaDeviceInfo[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [durationSec, setDurationSec] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [editedTranscript, setEditedTranscript] = useState('');
  const [userNote, setUserNote] = useState('');
  const [sendToOversight, setSendToOversight] = useState(false); // پیش‌فرض خاموش
  const [processingStage, setProcessingStage] = useState<string>('');

  // refs برای منابع stream/recorder
  const audioRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const videoRecorderRef = useRef<MediaRecorder | null>(null);
  const videoStreamRef = useRef<MediaStream | null>(null);
  const audioSeqRef = useRef(0);
  const videoSeqRef = useRef(0);
  const frameSeqRef = useRef(0);
  const timerRef = useRef<any>(null);
  const startedAtRef = useRef<number>(0);
  const screenshotIntervalRef = useRef<any>(null);
  const interactionEventsRef = useRef<any[]>([]);
  const sessionIdRef = useRef<string | null>(null); // برای handler ها

  // ─────────────────────────────────────────────────────────────────────────
  // Helpers — fetch wrappers
  // ─────────────────────────────────────────────────────────────────────────

  const apiPost = useCallback(
    async (path: string, body: any) => {
      const res = await fetch(`${API_BASE}/api/recording/inspector${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(j?.detail || `HTTP ${res.status}`);
      return j;
    },
    [],
  );

  const apiUploadBlob = useCallback(
    async (path: string, blob: Blob, seq: number, extraForm?: Record<string, string>) => {
      const form = new FormData();
      form.append('seq', String(seq));
      if (extraForm) {
        for (const [k, v] of Object.entries(extraForm)) form.append(k, v);
      }
      // field name باید مطابق با endpoint باشد
      const fieldName = path.includes('/audio-chunk')
        ? 'chunk'
        : path.includes('/video-chunk')
        ? 'chunk'
        : path.includes('/frame')
        ? 'frame'
        : 'file';
      form.append(fieldName, blob);
      const res = await fetch(`${API_BASE}/api/recording/inspector${path}`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j?.detail || `upload HTTP ${res.status}`);
      }
    },
    [],
  );

  // ─────────────────────────────────────────────────────────────────────────
  // Open picker — enumerate microphones
  // ─────────────────────────────────────────────────────────────────────────

  const openPicker = useCallback(async () => {
    setErrorMsg(null);
    // درخواست permission میکروفون برای enumerate (labels فقط با permission)
    let micPermissionOk = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop()); // فقط برای permission
      micPermissionOk = true;
    } catch {
      // permission denied یا میکروفون وجود ندارد — checkbox mic را auto-off می‌کنیم
      micPermissionOk = false;
    }
    let mics: MediaDeviceInfo[] = [];
    try {
      const devs = await navigator.mediaDevices.enumerateDevices();
      mics = devs.filter((d) => d.kind === 'audioinput');
      setMicDevices(mics);
    } catch {
      setMicDevices([]);
    }
    // 🆕 (fix #429-recording) — اگر میکروفون موجود نیست یا permission نگرفتیم،
    // پیش‌فرض mic را خاموش کن تا کاربر هنگام شروع ضبط با
    // "Requested device not found" مواجه نشود. کاربر در picker می‌تواند
    // دستی برگردونه روشن (مثلاً اگر بعداً mic نصب کرد).
    if (!micPermissionOk || mics.length === 0) {
      setAudioConfig((prev) => ({ ...prev, mic: false, micDeviceId: null }));
    }
    setPhase('picker');
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // Start recording
  // ─────────────────────────────────────────────────────────────────────────

  const startRecording = useCallback(async () => {
    setPhase('starting');
    setErrorMsg(null);
    try {
      const startRes = await apiPost('/start', {
        project_id: projectId,
        project_full_name: projectFullName || null,
        mode,
        audio_mic: audioConfig.mic,
        audio_system: audioConfig.system,
        mic_device_id: audioConfig.micDeviceId,
      });
      const sid = startRes?.session?.session_id;
      if (!sid) throw new Error('session_id not returned');
      setSessionId(sid);
      sessionIdRef.current = sid;

      // ─── شروع audio recording (mic + اختیاری system audio)
      if (audioConfig.mic || audioConfig.system) {
        const audioStream = await getAudioStream(audioConfig);
        // 🆕 (fix #429-recording) — اگر هیچ track صوتی واقعی برگردانده نشد
        // (مثلاً mic در دسترس نیست و system هم پشتیبانی نمی‌شود)، اصلاً
        // MediaRecorder صوتی نسازید — وگرنه recorder خالی شروع/پایان
        // می‌شود که ممکن است سمت بک‌اند خطا تولید کند.
        const hasRealAudio = audioStream.getAudioTracks().some((t) => t.enabled && t.readyState === 'live');
        audioStreamRef.current = audioStream;
        if (!hasRealAudio) {
          console.info('skipping audio recorder — no live audio tracks');
        } else {
        const rec = new MediaRecorder(audioStream, {
          mimeType: pickSupportedMime(['audio/webm;codecs=opus', 'audio/webm']),
        });
        rec.ondataavailable = async (e) => {
          if (e.data && e.data.size > 0) {
            const seq = audioSeqRef.current++;
            try {
              await apiUploadBlob(`/${sid}/audio-chunk`, e.data, seq);
            } catch (err) {
              console.warn('audio chunk upload failed', err);
            }
          }
        };
        rec.start(10_000); // هر 10 ثانیه chunk
        audioRecorderRef.current = rec;
        }  // close: if (hasRealAudio)
      }

      // ─── شروع video/frames بسته به mode
      if (mode === 'B') {
        // getDisplayMedia: کاربر تب/پنجره/screen را انتخاب می‌کند
        // 🆕 (fix #429-recording) — اگر system audio درخواست شد ولی browser
        // یا device نتوانست (مثلاً system audio روی macOS/Linux معمولاً
        // not supported)، یک بار retry بدون audio.
        let displayStream: MediaStream;
        try {
          displayStream = await navigator.mediaDevices.getDisplayMedia({
            video: { frameRate: 15 },
            audio: audioConfig.system,
          });
        } catch (dmErr: any) {
          if (audioConfig.system) {
            console.warn('getDisplayMedia with audio failed, retrying video-only:', dmErr?.name, dmErr?.message);
            displayStream = await navigator.mediaDevices.getDisplayMedia({
              video: { frameRate: 15 },
              audio: false,
            });
            setErrorMsg('صدای سیستم در مرورگر شما پشتیبانی نمی‌شود — فقط ویدئو ضبط می‌شود.');
          } else {
            throw dmErr;
          }
        }
        videoStreamRef.current = displayStream;
        const vrec = new MediaRecorder(displayStream, {
          mimeType: pickSupportedMime(['video/webm;codecs=vp9', 'video/webm']),
          videoBitsPerSecond: 600_000,
        });
        vrec.ondataavailable = async (e) => {
          if (e.data && e.data.size > 0) {
            const seq = videoSeqRef.current++;
            try {
              await apiUploadBlob(`/${sid}/video-chunk`, e.data, seq);
            } catch (err) {
              console.warn('video chunk upload failed', err);
            }
          }
        };
        // اگر کاربر روی browser از سهم‌گذاری دست کشید (close button)
        displayStream.getVideoTracks()[0].onended = () => {
          stopRecording().catch(() => {});
        };
        vrec.start(15_000); // هر 15 ثانیه chunk
        videoRecorderRef.current = vrec;
      } else {
        // mode A: ابتدا تلاش به Playwright backend screencast (بهینه‌تر)،
        // اگر در دسترس نبود → fallback به polling سمت client
        const iframeUrl = inspectorIframeRef?.current?.contentWindow?.location?.href || '';
        let useFrontendPolling = true;
        if (iframeUrl) {
          try {
            const scRes = await apiPost(`/${sid}/start-screencast`, {
              target_url: iframeUrl,
              viewport_width: 1280,
              viewport_height: 720,
            });
            if (scRes?.success && scRes?.method === 'playwright_backend') {
              useFrontendPolling = false;
              console.log('🎬 Playwright backend screencast active');
            } else {
              console.log('🎬 Playwright unavailable, falling back to polling:', scRes?.error);
            }
          } catch (e) {
            console.warn('start-screencast call failed, falling back to polling:', e);
          }
        }
        if (useFrontendPolling) {
          startScreenshotPolling(sid);
        }
        // postMessage bridge برای interactions
        attachPostMessageBridge();
      }

      startedAtRef.current = Date.now();
      timerRef.current = setInterval(() => {
        const sec = (Date.now() - startedAtRef.current) / 1000;
        setDurationSec(sec);
        // 60min auto-stop
        if (sec >= 60 * 60) {
          stopRecording().catch(() => {});
        }
      }, 500);

      setPhase('recording');
    } catch (e: any) {
      console.error('startRecording failed', e);
      setErrorMsg(e?.message || 'خطا در شروع ضبط');
      setPhase('error');
      // cleanup any partial state
      cleanupStreams();
    }
  }, [apiPost, apiUploadBlob, projectId, projectFullName, mode, audioConfig]);

  // ─────────────────────────────────────────────────────────────────────────
  // Audio stream (mic + optional system)
  // ─────────────────────────────────────────────────────────────────────────

  async function getAudioStream(cfg: AudioConfig): Promise<MediaStream> {
    const streams: MediaStream[] = [];
    if (cfg.mic) {
      // 🆕 (fix #429-recording) — تلاش soft برای mic. اگر deviceId مشخص‌شده
      // دیگر موجود نیست (مثلاً USB mic disconnect)، یا اصلاً mic روی دستگاه
      // نیست، به‌جای throw → fall back به constraint ساده، و اگر آن هم
      // failed شد، silently بدون audio ادامه بده. این جلوی
      // "Requested device not found" را می‌گیرد.
      const tryGetUserMedia = async (
        constraints: MediaStreamConstraints,
      ): Promise<MediaStream | null> => {
        try {
          return await navigator.mediaDevices.getUserMedia(constraints);
        } catch (e: any) {
          console.warn('getUserMedia(audio) failed', e?.name, e?.message);
          return null;
        }
      };
      let s: MediaStream | null = null;
      if (cfg.micDeviceId) {
        s = await tryGetUserMedia({
          audio: { deviceId: { exact: cfg.micDeviceId } },
        });
        if (!s) {
          // deviceId exact شکست خورد → constraint عمومی
          s = await tryGetUserMedia({ audio: true });
        }
      } else {
        s = await tryGetUserMedia({ audio: true });
      }
      if (s) {
        streams.push(s);
      } else {
        // mic غیرقابل دسترس — کاربر را مطلع کن ولی ضبط ادامه پیدا کند
        setErrorMsg(
          'میکروفون در دسترس نیست — ضبط بدون صدا ادامه می‌یابد.',
        );
      }
    }
    // system audio پیچیده‌تر است و در حالت A معمولاً نیست — اگر mode B بود
    // در getDisplayMedia جداگانه handle می‌شود
    if (streams.length === 0) {
      // یک silent stream فیک — برای جلوگیری از crash MediaRecorder
      const ctx = new AudioContext();
      const dst = ctx.createMediaStreamDestination();
      return dst.stream;
    }
    if (streams.length === 1) return streams[0];
    // ترکیب چند stream با Web Audio API
    const ctx = new AudioContext();
    const dst = ctx.createMediaStreamDestination();
    streams.forEach((s) => {
      const src = ctx.createMediaStreamSource(s);
      src.connect(dst);
    });
    return dst.stream;
  }

  function pickSupportedMime(candidates: string[]): string {
    for (const m of candidates) {
      if (MediaRecorder.isTypeSupported(m)) return m;
    }
    return candidates[candidates.length - 1];
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Mode A: Screenshot polling
  // ─────────────────────────────────────────────────────────────────────────

  function startScreenshotPolling(sid: string) {
    if (screenshotIntervalRef.current) {
      clearInterval(screenshotIntervalRef.current);
    }
    let inFlight = false;
    screenshotIntervalRef.current = setInterval(async () => {
      if (inFlight) return; // skip اگر قبلی هنوز در حال انجام است
      inFlight = true;
      try {
        // درخواست screenshot از endpoint موجود
        const url = inspectorIframeRef?.current?.contentWindow?.location?.href || '';
        const res = await fetch(`${API_BASE}/api/render/inspector/screenshot`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, project_id: projectId }),
        });
        if (!res.ok) {
          inFlight = false;
          return;
        }
        const j = await res.json();
        const b64 = j?.base64 || j?.screenshot_base64 || '';
        if (!b64) {
          inFlight = false;
          return;
        }
        // تبدیل base64 به Blob
        const bin = atob(b64);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        const blob = new Blob([arr], { type: 'image/png' });
        const seq = frameSeqRef.current++;
        await apiUploadBlob(`/${sid}/frame`, blob, seq, { ext: 'png' });
      } catch (e) {
        console.warn('screenshot poll failed', e);
      } finally {
        inFlight = false;
      }
    }, 500); // هر ۵۰۰ms = 2fps
  }

  function stopScreenshotPolling() {
    if (screenshotIntervalRef.current) {
      clearInterval(screenshotIntervalRef.current);
      screenshotIntervalRef.current = null;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // PostMessage bridge for iframe interactions (mode A)
  // ─────────────────────────────────────────────────────────────────────────

  function attachPostMessageBridge() {
    const handler = (event: MessageEvent) => {
      const d = event.data;
      if (!d || typeof d !== 'object' || !d.__inspector_event) return;
      interactionEventsRef.current.push({
        ts_ms: Math.max(0, Date.now() - startedAtRef.current),
        type: String(d.type || 'unknown'),
        details: { ...(d.details || {}), selector: d.selector, x: d.x, y: d.y },
        source: 'postmessage',
      });
    };
    window.addEventListener('message', handler);
    // ذخیره برای cleanup
    (window as any).__inspectorRecordingMsgHandler = handler;
  }

  function detachPostMessageBridge() {
    const h = (window as any).__inspectorRecordingMsgHandler;
    if (h) {
      window.removeEventListener('message', h);
      delete (window as any).__inspectorRecordingMsgHandler;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Stop recording
  // ─────────────────────────────────────────────────────────────────────────

  const stopRecording = useCallback(async () => {
    if (phase !== 'recording') return;
    setPhase('stopping');
    if (timerRef.current) clearInterval(timerRef.current);
    stopScreenshotPolling();
    detachPostMessageBridge();

    // متوقف کردن recorders + جمع‌آوری آخرین chunk ها
    if (audioRecorderRef.current && audioRecorderRef.current.state !== 'inactive') {
      audioRecorderRef.current.stop();
    }
    if (videoRecorderRef.current && videoRecorderRef.current.state !== 'inactive') {
      videoRecorderRef.current.stop();
    }
    // کمی صبر کن تا ondataavailable کامل شود
    await new Promise((r) => setTimeout(r, 1500));
    cleanupStreams();

    const sid = sessionIdRef.current;
    if (!sid) {
      setErrorMsg('session_id از دست رفت');
      setPhase('error');
      return;
    }

    // ارسال interactions تجمعی
    if (interactionEventsRef.current.length > 0) {
      try {
        await apiPost(`/${sid}/interactions`, { events: interactionEventsRef.current });
      } catch (e) {
        console.warn('interactions upload failed', e);
      }
    }

    // ارسال stop با logs و user_note فعلی (یادداشت در preview ویرایش می‌شود)
    setPhase('processing');
    setProcessingStage('در حال آماده‌سازی...');
    try {
      const consoleLogs = getConsoleLogsSnapshot?.() || [];
      const backendLogs = getBackendLogsSnapshot?.() || [];
      await apiPost(`/${sid}/stop`, {
        user_note: userNote,
        console_logs: consoleLogs,
        backend_logs: backendLogs,
      });
      // پس از stop سرور processing را همزمان اجرا می‌کند → الان response آمده
      // یعنی processing تمام شده. preview را fetch کن.
      await fetchPreview(sid);
    } catch (e: any) {
      console.error('stop failed', e);
      setErrorMsg(e?.message || 'خطا در پایان ضبط');
      setPhase('error');
    }
  }, [phase, apiPost, userNote, getConsoleLogsSnapshot, getBackendLogsSnapshot]);

  function cleanupStreams() {
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((t) => t.stop());
      audioStreamRef.current = null;
    }
    if (videoStreamRef.current) {
      videoStreamRef.current.getTracks().forEach((t) => t.stop());
      videoStreamRef.current = null;
    }
    audioRecorderRef.current = null;
    videoRecorderRef.current = null;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Fetch preview
  // ─────────────────────────────────────────────────────────────────────────

  async function fetchPreview(sid: string) {
    try {
      const res = await fetch(`${API_BASE}/api/recording/inspector/${sid}/preview`);
      const j = await res.json();
      if (!res.ok) throw new Error(j?.detail || `HTTP ${res.status}`);
      setPreview(j as PreviewData);
      setEditedTranscript(j.transcript || '');
      setPhase('preview');
    } catch (e: any) {
      setErrorMsg(e?.message || 'خطا در دریافت پیش‌نمایش');
      setPhase('error');
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Regenerate prompt
  // ─────────────────────────────────────────────────────────────────────────

  const regeneratePrompt = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    setProcessingStage('بازتولید پرامپت...');
    try {
      const res = await apiPost(`/${sid}/regenerate-prompt`, {
        edited_transcript: editedTranscript,
        user_note: userNote,
      });
      if (preview) {
        setPreview({ ...preview, prompt: res.prompt, prompt_chars: res.prompt_chars });
      }
    } catch (e: any) {
      setErrorMsg(`regenerate: ${e?.message}`);
    } finally {
      setProcessingStage('');
    }
  }, [apiPost, editedTranscript, userNote, preview]);

  // ─────────────────────────────────────────────────────────────────────────
  // Finalize
  // ─────────────────────────────────────────────────────────────────────────

  const finalize = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    setPhase('finalizing');
    try {
      const res = await apiPost(`/${sid}/finalize`, {
        user_note: userNote,
        send_to_oversight: sendToOversight,
        edited_transcript: editedTranscript,
      });
      setPhase('completed');
      if (onComplete) {
        onComplete({
          task_id: res?.task_id || null,
          chat_message_sent: res?.chat_message_sent || false,
        });
      }
      // پس از ۳ ثانیه reset
      setTimeout(() => resetAll(), 3000);
    } catch (e: any) {
      setErrorMsg(`finalize: ${e?.message}`);
      setPhase('error');
    }
  }, [apiPost, userNote, sendToOversight, editedTranscript, onComplete]);

  // ─────────────────────────────────────────────────────────────────────────
  // Cancel
  // ─────────────────────────────────────────────────────────────────────────

  const cancelAll = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (sid) {
      try {
        await apiPost(`/${sid}/cancel`, {});
      } catch {}
    }
    cleanupStreams();
    stopScreenshotPolling();
    detachPostMessageBridge();
    if (timerRef.current) clearInterval(timerRef.current);
    resetAll();
  }, [apiPost]);

  function resetAll() {
    setPhase('idle');
    setSessionId(null);
    sessionIdRef.current = null;
    setDurationSec(0);
    setErrorMsg(null);
    setPreview(null);
    setEditedTranscript('');
    setUserNote('');
    setSendToOversight(false);
    setProcessingStage('');
    audioSeqRef.current = 0;
    videoSeqRef.current = 0;
    frameSeqRef.current = 0;
    interactionEventsRef.current = [];
  }

  // cleanup هنگام unmount
  useEffect(() => {
    return () => {
      cleanupStreams();
      stopScreenshotPolling();
      detachPostMessageBridge();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  const fmtTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <>
      {/* دکمه trigger */}
      <button
        onClick={openPicker}
        disabled={!enabled || phase === 'recording' || phase === 'processing' || phase === 'finalizing'}
        title="ضبط ویدئو از iframe بازرس ویژه یا صفحات آزاد — با لاگ‌ها، صدا، تعاملات و پرامپت AI"
        className={
          buttonClassName ||
          'px-2 py-1 bg-orange-600/90 hover:bg-orange-700 text-white text-[10px] rounded-md shadow-lg transition-all disabled:opacity-50 flex items-center gap-1'
        }
      >
        {phase === 'recording' ? (
          <span className="animate-pulse">⏺</span>
        ) : phase === 'processing' || phase === 'finalizing' ? (
          <span className="animate-spin">⏳</span>
        ) : (
          <span>🎬</span>
        )}
        ضبط
      </button>

      {/* Picker modal */}
      {phase === 'picker' && (
        <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
              🎬 شروع ضبط — حالت را انتخاب کنید
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
              <button
                onClick={() => setMode('A')}
                className={`p-4 rounded-lg border-2 text-right transition-all ${
                  mode === 'A'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400'
                }`}
              >
                <div className="text-2xl mb-1">🎯</div>
                <div className="font-bold text-sm text-gray-900 dark:text-white">
                  ضبط بازرس ویژه (پیش‌فرض)
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 leading-relaxed">
                  فقط محتوای داخل iframe ضبط می‌شود. لاگ‌ها، تعاملات و کلیک‌های شما داخل
                  همین مانیتور رصد می‌شود. AI فقط حول همین پروژه پرامپت می‌سازد.
                </div>
              </button>

              <button
                onClick={() => setMode('B')}
                className={`p-4 rounded-lg border-2 text-right transition-all ${
                  mode === 'B'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400'
                }`}
              >
                <div className="text-2xl mb-1">🌐</div>
                <div className="font-bold text-sm text-gray-900 dark:text-white">
                  ضبط آزاد (تب/پنجره/دسکتاپ)
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 leading-relaxed">
                  مرورگر یک دیالوگ باز می‌کند با <b>سه گزینه بالا</b>:
                  <br />
                  • <b>Microsoft Edge Tab / Chrome Tab</b> — فقط تب‌های مرورگر
                  <br />
                  • <b>Window</b> — پنجرهٔ یک برنامه (File Explorer برای فولدر، VS Code، WhatsApp، …)
                  <br />
                  • <b>Entire Screen</b> — کل دسکتاپ + هر چیزی که روی صفحه می‌بینید (taskbar، چند برنامه با هم، فولدرها)
                  <br />
                  می‌توانید آزادانه بین صفحات/برنامه‌ها/فولدرها سیر کنید. AI با تحلیل
                  بصری متوجه می‌شود کجا هستید و چه می‌کنید.
                </div>
              </button>
            </div>

            <div className="border-t pt-4 mb-4">
              <h3 className="text-sm font-bold mb-2 text-gray-900 dark:text-white">
                ⚙️ تنظیمات صدا
              </h3>
              <label className="flex items-center gap-2 mb-2 text-sm text-gray-800 dark:text-gray-200">
                <input
                  type="checkbox"
                  checked={audioConfig.mic}
                  onChange={(e) => setAudioConfig({ ...audioConfig, mic: e.target.checked })}
                />
                🎤 ضبط صدای میکروفون
              </label>
              {audioConfig.mic && micDevices.length > 0 && (
                <select
                  value={audioConfig.micDeviceId || ''}
                  onChange={(e) =>
                    setAudioConfig({ ...audioConfig, micDeviceId: e.target.value || null })
                  }
                  className="w-full p-2 mb-2 border rounded text-xs bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="">پیش‌فرض سیستم</option>
                  {micDevices.map((d) => (
                    <option key={d.deviceId} value={d.deviceId}>
                      {d.label || `میکروفون ${d.deviceId.slice(0, 8)}`}
                    </option>
                  ))}
                </select>
              )}
              <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200">
                <input
                  type="checkbox"
                  checked={audioConfig.system}
                  onChange={(e) =>
                    setAudioConfig({ ...audioConfig, system: e.target.checked })
                  }
                />
                🔊 ضبط صدای سیستم{' '}
                <span className="text-xs text-gray-500">(در حالت B از همان picker، در A اضافی)</span>
              </label>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setPhase('idle')}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded hover:bg-gray-300"
              >
                انصراف
              </button>
              <button
                onClick={startRecording}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-bold"
              >
                ▶ شروع ضبط
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status bar در طول ضبط */}
      {phase === 'recording' && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-[9999] bg-red-600 text-white px-4 py-2 rounded-full shadow-2xl flex items-center gap-3 text-sm">
          <span className="animate-pulse">⏺</span>
          <span className="font-mono font-bold">{fmtTime(durationSec)}</span>
          <span className="opacity-75">|</span>
          <span>{mode === 'A' ? '🎯 iframe' : '🌐 free'}</span>
          {audioConfig.mic && <span>🎤</span>}
          {audioConfig.system && <span>🔊</span>}
          {durationSec > 55 * 60 && (
            <span className="bg-yellow-400 text-red-900 px-2 py-0.5 rounded text-xs font-bold">
              ⚠️ {Math.ceil((60 * 60 - durationSec) / 60)}m مانده
            </span>
          )}
          <button
            onClick={stopRecording}
            className="ml-2 px-3 py-1 bg-white text-red-600 rounded font-bold hover:bg-gray-100"
          >
            ⏹ پایان
          </button>
        </div>
      )}

      {/* Processing modal */}
      {(phase === 'processing' || phase === 'stopping') && (
        <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-md w-full p-6 text-center">
            <div className="text-4xl mb-3 animate-spin">⏳</div>
            <h2 className="text-lg font-bold mb-2 text-gray-900 dark:text-white">
              در حال آماده‌سازی...
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
              {processingStage || 'لطفاً صبر کنید — این می‌تواند تا چند دقیقه طول بکشد.'}
            </p>
            <div className="text-xs text-gray-500">
              transcribe صوت • تحلیل بصری keyframes • سنتز پرامپت AI
            </div>
          </div>
        </div>
      )}

      {/* Preview modal */}
      {phase === 'preview' && preview && (
        <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full p-6 max-h-[95vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
              📋 پیش‌نمایش ضبط — قبل از ارسال نهایی بازبینی کنید
            </h2>

            {/* یادداشت اولیه */}
            <section className="mb-4">
              <label className="block text-sm font-bold mb-1 text-gray-800 dark:text-gray-200">
                📝 یادداشت اولیه (raw_idea — در ابتدای پرامپت تسک حفظ می‌شود)
              </label>
              <textarea
                value={userNote}
                onChange={(e) => setUserNote(e.target.value)}
                rows={3}
                placeholder="یادداشت اولیه (اختیاری) — این متن عین به عین در ابتدای پرامپت تسک حفظ می‌شود..."
                className="w-full p-2 border rounded text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </section>

            {/* Transcript editable */}
            <section className="mb-4">
              <label className="block text-sm font-bold mb-1 text-gray-800 dark:text-gray-200">
                🎙 Transcript صوت{' '}
                <span className="text-xs text-gray-500">
                  ({preview.transcript_language || 'auto'} —{' '}
                  {editedTranscript.length} char)
                </span>
              </label>
              <textarea
                value={editedTranscript}
                onChange={(e) => setEditedTranscript(e.target.value)}
                rows={5}
                className="w-full p-2 border rounded text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
              />
              {editedTranscript !== preview.transcript && (
                <button
                  onClick={regeneratePrompt}
                  className="mt-1 text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  🔄 تولید مجدد پرامپت با transcript اصلاح‌شده
                </button>
              )}
            </section>

            {/* Stats accordion */}
            <details className="mb-3 text-sm">
              <summary className="cursor-pointer font-bold text-gray-800 dark:text-gray-200">
                🔍 خلاصه بصری ({preview.visual_summary.length} keyframe)
              </summary>
              <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs max-h-40 overflow-y-auto">
                {preview.visual_summary.map((v: any, i: number) => (
                  <div key={i} className="mb-2 pb-2 border-b last:border-0">
                    <div className="font-mono text-gray-500">
                      [{Math.floor((v.timestamp_ms || 0) / 1000)}s]
                    </div>
                    <div className="text-gray-700 dark:text-gray-300">{v.scene}</div>
                  </div>
                ))}
              </div>
            </details>

            {preview.location_timeline.length > 0 && (
              <details className="mb-3 text-sm">
                <summary className="cursor-pointer font-bold text-gray-800 dark:text-gray-200">
                  🌐 نقشه فعالیت (mode B — {preview.location_timeline.length} نقطه)
                </summary>
                <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs max-h-40 overflow-y-auto">
                  {preview.location_timeline.map((l: any, i: number) => (
                    <div key={i} className="mb-1">
                      <span className="font-mono text-gray-500">
                        [{Math.floor((l.ts_ms || 0) / 1000)}s]
                      </span>{' '}
                      {l.related_to_project ? '✓' : '✗'} {l.category} —{' '}
                      {l.url_or_app_name} — {l.activity_description}
                    </div>
                  ))}
                </div>
              </details>
            )}

            <details className="mb-3 text-sm">
              <summary className="cursor-pointer font-bold text-gray-800 dark:text-gray-200">
                🖱 تعاملات ({preview.interactions.length})
              </summary>
              <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs max-h-32 overflow-y-auto font-mono">
                {preview.interactions.slice(0, 50).map((ev: any, i: number) => (
                  <div key={i}>
                    [{Math.floor((ev.ts_ms || 0) / 1000)}s] {ev.type} {JSON.stringify(ev.details).slice(0, 80)}
                  </div>
                ))}
              </div>
            </details>

            <details className="mb-3 text-sm">
              <summary className="cursor-pointer font-bold text-gray-800 dark:text-gray-200">
                📋 لاگ‌ها (console: {preview.console_logs_count}، backend: {preview.backend_logs_count})
              </summary>
            </details>

            {/* پرامپت قوی */}
            <section className="mb-4">
              <label className="block text-sm font-bold mb-1 text-gray-800 dark:text-gray-200">
                🎯 پرامپت قوی تولیدشده ({preview.prompt?.length || 0} char — بدون محدودیت)
              </label>
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded text-xs max-h-60 overflow-y-auto whitespace-pre-wrap font-mono text-gray-900 dark:text-gray-100">
                {preview.prompt || '(پرامپت خالی — احتمالاً AI provider در دسترس نبود)'}
              </div>
            </section>

            {/* چک‌باکس ارسال به نظارت */}
            <section className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded">
              <label className="flex items-center gap-2 text-sm font-bold text-gray-900 dark:text-white">
                <input
                  type="checkbox"
                  checked={sendToOversight}
                  onChange={(e) => setSendToOversight(e.target.checked)}
                />
                ارسال به مرکز نظارت (ساخت تسک جدید زیر همین پروژه)
              </label>
              <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 pr-6">
                اگر تیک نخورد: پرامپت به چت inspector اضافه می‌شود.
                <br />
                اگر تیک خورد: تسک جدید با raw_idea = یادداشت اولیه و prompt = پرامپت قوی ایجاد می‌شود.
              </div>
            </section>

            <div className="flex gap-2 justify-end">
              <button
                onClick={cancelAll}
                className="px-4 py-2 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 rounded hover:bg-red-200"
              >
                🗑 لغو و دور انداختن
              </button>
              <button
                onClick={finalize}
                className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-bold"
              >
                ✓ ارسال نهایی
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Finalizing toast */}
      {phase === 'finalizing' && (
        <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-md w-full p-6 text-center">
            <div className="text-4xl mb-3 animate-spin">📤</div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
              ارسال نهایی به تلگرام و ساخت تسک...
            </h2>
          </div>
        </div>
      )}

      {/* Completed toast */}
      {phase === 'completed' && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-[9999] bg-green-600 text-white px-6 py-3 rounded-lg shadow-2xl">
          ✓ ارسال موفق — ضبط در تلگرام و تسک ایجاد شد
        </div>
      )}

      {/* Error display */}
      {phase === 'error' && errorMsg && (
        <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-md w-full p-6">
            <h2 className="text-lg font-bold text-red-600 mb-2">❌ خطا</h2>
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">{errorMsg}</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={cancelAll}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded"
              >
                بستن
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
