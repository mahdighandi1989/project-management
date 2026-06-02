/**
 * useScreenRecording — هوک ضبط ویدئوی صفحه + صدا برای «بازرس ویژه».
 *
 * قابلیت‌ها:
 *  - ضبط بصری صفحه با getDisplayMedia (جابجایی صفحات، حرکت موس، …)
 *  - ضبط صدا: میکروفون (mic)، صدای سیستم (system)، هر دو (both)، یا هیچ (none)
 *  - حالت هندزفری: خاموش‌کردن echoCancellation/noiseSuppression
 *  - جمع‌آوری همزمان لاگ‌های console و رویدادهای تعامل کاربر (کلیک/ناوبری/scroll)
 *  - خروجی نهایی: Blob ویدئو + Blob صدا (در صورت وجود) + لاگ‌ها + تعاملات
 *
 * تمام ضبط در مرورگر انجام می‌شود؛ آپلود و transcription در سرور.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type AudioSource = 'mic' | 'system' | 'both' | 'none';

export interface RecordingSettings {
  audioSource: AudioSource;
  handsfree: boolean;
}

export interface ConsoleEntry {
  level: string;
  message: string;
  timestamp: string;
  source: string;
}

export interface InteractionEvent {
  type: string;
  target?: string;
  label?: string;
  page_url?: string;
  timestamp: string;
}

export interface RecordingResult {
  videoBlob: Blob | null;
  audioBlob: Blob | null;
  mimeType: string;
  durationMs: number;
  consoleLogs: ConsoleEntry[];
  interactions: InteractionEvent[];
  settings: RecordingSettings;
}

const DEFAULT_SETTINGS: RecordingSettings = { audioSource: 'mic', handsfree: false };

function pickMimeType(): string {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
    'video/mp4',
  ];
  if (typeof MediaRecorder === 'undefined') return 'video/webm';
  for (const c of candidates) {
    try {
      if (MediaRecorder.isTypeSupported(c)) return c;
    } catch {
      /* ignore */
    }
  }
  return 'video/webm';
}

function describeTarget(el: EventTarget | null): { target: string; label: string } {
  if (!el || !(el instanceof Element)) return { target: '', label: '' };
  const tag = el.tagName.toLowerCase();
  const id = el.id ? `#${el.id}` : '';
  const cls =
    typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.')
      : '';
  const label = (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 80);
  return { target: `${tag}${id}${cls}`, label };
}

export function useScreenRecording() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState(0);
  const [settings, setSettings] = useState<RecordingSettings>(DEFAULT_SETTINGS);

  const isSupported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getDisplayMedia === 'function' &&
    typeof MediaRecorder !== 'undefined';

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const displayStreamRef = useRef<MediaStream | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const startTsRef = useRef<number>(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consoleLogsRef = useRef<ConsoleEntry[]>([]);
  const interactionsRef = useRef<InteractionEvent[]>([]);
  const restoreConsoleRef = useRef<(() => void) | null>(null);
  const cleanupListenersRef = useRef<(() => void) | null>(null);
  const mimeRef = useRef<string>('video/webm');

  const cleanupStreams = useCallback(() => {
    [displayStreamRef.current, micStreamRef.current].forEach((s) => {
      if (s) s.getTracks().forEach((t) => t.stop());
    });
    displayStreamRef.current = null;
    micStreamRef.current = null;
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    if (restoreConsoleRef.current) {
      restoreConsoleRef.current();
      restoreConsoleRef.current = null;
    }
    if (cleanupListenersRef.current) {
      cleanupListenersRef.current();
      cleanupListenersRef.current = null;
    }
  }, []);

  const interceptConsole = useCallback(() => {
    const methods: Array<'log' | 'info' | 'warn' | 'error'> = ['log', 'info', 'warn', 'error'];
    const originals: Record<string, (...a: unknown[]) => void> = {};
    methods.forEach((m) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      originals[m] = (console as any)[m].bind(console);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (console as any)[m] = (...args: unknown[]) => {
        try {
          consoleLogsRef.current.push({
            level: m,
            message: args
              .map((a) => {
                try {
                  return typeof a === 'string' ? a : JSON.stringify(a);
                } catch {
                  return String(a);
                }
              })
              .join(' ')
              .slice(0, 2000),
            timestamp: new Date().toISOString(),
            source: 'console',
          });
        } catch {
          /* ignore */
        }
        originals[m](...args);
      };
    });
    const onError = (ev: ErrorEvent) => {
      consoleLogsRef.current.push({
        level: 'error',
        message: `${ev.message} @ ${ev.filename}:${ev.lineno}`,
        timestamp: new Date().toISOString(),
        source: 'window.onerror',
      });
    };
    const onRejection = (ev: PromiseRejectionEvent) => {
      consoleLogsRef.current.push({
        level: 'error',
        message: `unhandledrejection: ${String(ev.reason).slice(0, 1000)}`,
        timestamp: new Date().toISOString(),
        source: 'promise',
      });
    };
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      methods.forEach((m) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (console as any)[m] = originals[m];
      });
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, []);

  const trackInteractions = useCallback(() => {
    const push = (type: string, target = '', label = '') => {
      interactionsRef.current.push({
        type,
        target,
        label,
        page_url: typeof location !== 'undefined' ? location.href : '',
        timestamp: new Date().toISOString(),
      });
    };
    const onClick = (e: MouseEvent) => {
      const { target, label } = describeTarget(e.target);
      push('click', target, label);
    };
    let scrollTimer: ReturnType<typeof setTimeout> | null = null;
    const onScroll = () => {
      if (scrollTimer) return;
      scrollTimer = setTimeout(() => {
        push('scroll', `scrollY=${Math.round(window.scrollY)}`);
        scrollTimer = null;
      }, 400);
    };
    const onNav = () => push('navigate', typeof location !== 'undefined' ? location.pathname : '');
    document.addEventListener('click', onClick, true);
    window.addEventListener('scroll', onScroll, true);
    window.addEventListener('popstate', onNav);
    window.addEventListener('hashchange', onNav);
    push('record-start', typeof location !== 'undefined' ? location.href : '');
    return () => {
      document.removeEventListener('click', onClick, true);
      window.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('popstate', onNav);
      window.removeEventListener('hashchange', onNav);
      if (scrollTimer) clearTimeout(scrollTimer);
    };
  }, []);

  const start = useCallback(
    async (opts?: Partial<RecordingSettings>) => {
      setError(null);
      if (!isSupported) {
        setError('مرورگر شما از ضبط صفحه پشتیبانی نمی‌کند (getDisplayMedia/MediaRecorder).');
        return false;
      }
      const cfg: RecordingSettings = { ...DEFAULT_SETTINGS, ...settings, ...opts };
      setSettings(cfg);
      consoleLogsRef.current = [];
      interactionsRef.current = [];
      chunksRef.current = [];

      try {
        const wantSystemAudio = cfg.audioSource === 'system' || cfg.audioSource === 'both';
        const display = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: wantSystemAudio,
        });
        displayStreamRef.current = display;

        const audioTracks: MediaStreamTrack[] = [];
        // صدای سیستم از stream نمایش (در صورت در دسترس بودن مرورگر)
        if (wantSystemAudio) {
          display.getAudioTracks().forEach((t) => audioTracks.push(t));
        }
        // صدای میکروفون
        if (cfg.audioSource === 'mic' || cfg.audioSource === 'both') {
          try {
            const mic = await navigator.mediaDevices.getUserMedia({
              audio: {
                echoCancellation: !cfg.handsfree,
                noiseSuppression: !cfg.handsfree,
                autoGainControl: !cfg.handsfree,
              },
            });
            micStreamRef.current = mic;
            mic.getAudioTracks().forEach((t) => audioTracks.push(t));
          } catch (micErr) {
            // اگر میکروفون رد شد ولی ویدئو داریم، ادامه می‌دهیم
            console.warn('mic access denied/failed:', micErr);
          }
        }

        const combined = new MediaStream([...display.getVideoTracks(), ...audioTracks]);
        const mime = pickMimeType();
        mimeRef.current = mime;
        const recorder = new MediaRecorder(combined, { mimeType: mime });
        recorder.ondataavailable = (e: BlobEvent) => {
          if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
        };
        recorderRef.current = recorder;

        // اگر کاربر از طریق UI مرورگر «Stop sharing» را زد
        const vTrack = display.getVideoTracks()[0];
        if (vTrack) {
          vTrack.addEventListener('ended', () => {
            if (recorderRef.current && recorderRef.current.state !== 'inactive') {
              try {
                recorderRef.current.stop();
              } catch {
                /* ignore */
              }
            }
          });
        }

        restoreConsoleRef.current = interceptConsole();
        cleanupListenersRef.current = trackInteractions();

        recorder.start(1000);
        startTsRef.current = Date.now();
        setDurationMs(0);
        tickRef.current = setInterval(() => {
          setDurationMs(Date.now() - startTsRef.current);
        }, 250);
        setIsRecording(true);
        return true;
      } catch (e) {
        cleanupStreams();
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg.includes('Permission') || msg.includes('denied') ? 'دسترسی به ضبط صفحه رد شد.' : `خطا در شروع ضبط: ${msg}`);
        return false;
      }
    },
    [isSupported, settings, interceptConsole, trackInteractions, cleanupStreams],
  );

  const stop = useCallback((): Promise<RecordingResult> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      const finishedSettings = settings;
      const finalize = () => {
        const durationMsFinal = startTsRef.current ? Date.now() - startTsRef.current : 0;
        const videoBlob =
          chunksRef.current.length > 0
            ? new Blob(chunksRef.current, { type: mimeRef.current })
            : null;
        const result: RecordingResult = {
          videoBlob,
          audioBlob: null, // صدا داخل همان فایل ویدئو ضبط می‌شود (audio track)
          mimeType: mimeRef.current,
          durationMs: durationMsFinal,
          consoleLogs: [...consoleLogsRef.current],
          interactions: [...interactionsRef.current],
          settings: finishedSettings,
        };
        cleanupStreams();
        recorderRef.current = null;
        setIsRecording(false);
        resolve(result);
      };

      if (!recorder || recorder.state === 'inactive') {
        finalize();
        return;
      }
      recorder.onstop = finalize;
      try {
        recorder.stop();
      } catch {
        finalize();
      }
    });
  }, [settings, cleanupStreams]);

  // پاکسازی هنگام unmount
  useEffect(() => {
    return () => {
      cleanupStreams();
    };
  }, [cleanupStreams]);

  return {
    isSupported,
    isRecording,
    error,
    durationMs,
    settings,
    setSettings,
    start,
    stop,
  };
}

export default useScreenRecording;
