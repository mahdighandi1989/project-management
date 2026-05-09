'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const DIAGRAM_TYPES = [
  { id: 'flowchart', name: 'فلوچارت', icon: '📊' },
  { id: 'sequence', name: 'توالی', icon: '📋' },
  { id: 'class', name: 'کلاس', icon: '🏗️' },
  { id: 'er', name: 'ER دیتابیس', icon: '🗄️' },
  { id: 'gantt', name: 'گانت', icon: '📅' },
  { id: 'pie', name: 'دایره‌ای', icon: '🥧' },
  { id: 'mindmap', name: 'نقشه ذهنی', icon: '🧠' },
  { id: 'state', name: 'وضعیت', icon: '🔄' },
];

const FALLBACK_EXAMPLES: Record<string, string> = {
  flowchart: `flowchart TD
    A[شروع] --> B{تصمیم}
    B -->|بله| C[عملیات یک]
    B -->|خیر| D[عملیات دو]
    C --> E[پایان]
    D --> E`,
  sequence: `sequenceDiagram
    participant U as کاربر
    participant S as سرور
    participant DB as دیتابیس
    U->>S: درخواست
    S->>DB: کوئری
    DB-->>S: نتیجه
    S-->>U: پاسخ`,
  class: `classDiagram
    class User {
        +String name
        +String email
        +login()
    }
    class Order {
        +Int id
        +Date date
        +calculateTotal()
    }
    User "1" --> "*" Order : places`,
  er: `erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ ITEM : contains
    USER {
        int id
        string name
    }
    ORDER {
        int id
        date created_at
    }`,
  gantt: `gantt
    title برنامه پروژه
    dateFormat YYYY-MM-DD
    section فاز یک
    تحلیل :a1, 2026-01-01, 7d
    طراحی :a2, after a1, 5d
    section فاز دو
    توسعه :a3, after a2, 14d
    تست :a4, after a3, 7d`,
  pie: `pie title توزیع زمان
    "توسعه" : 40
    "تست" : 25
    "طراحی" : 20
    "مستندسازی" : 15`,
  mindmap: `mindmap
  root((پروژه))
    Backend
      API
      Database
      Auth
    Frontend
      UI
      State
    DevOps
      CI/CD
      Monitoring`,
  state: `stateDiagram-v2
    [*] --> Idle
    Idle --> Running : شروع
    Running --> Paused : توقف
    Paused --> Running : ادامه
    Running --> Done : اتمام
    Done --> [*]`,
};

interface DiagramHistory {
  id: number;
  type: string;
  code: string;
  createdAt: number;
}

export default function DiagramsPage() {
  const [selectedType, setSelectedType] = useState('flowchart');
  const [diagram, setDiagram] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [codeInput, setCodeInput] = useState('');
  const [codeLanguage, setCodeLanguage] = useState('python');
  const [analyzing, setAnalyzing] = useState(false);

  const [theme, setTheme] = useState<'default' | 'dark' | 'forest' | 'neutral'>('default');
  const [history, setHistory] = useState<DiagramHistory[]>([]);

  const [renderError, setRenderError] = useState('');
  const [svgContent, setSvgContent] = useState('');
  const previewRef = useRef<HTMLDivElement>(null);

  // بارگذاری history
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const saved = localStorage.getItem('diagrams_history');
      if (saved) setHistory(JSON.parse(saved).slice(0, 10));
    } catch (e) {}
    loadExample('flowchart');
  }, []);

  // ذخیره history
  const saveHistory = (type: string, code: string) => {
    if (!code.trim()) return;
    const newItem: DiagramHistory = {
      id: Date.now(),
      type,
      code,
      createdAt: Date.now(),
    };
    const updated = [newItem, ...history.filter((h) => h.code !== code)].slice(0, 10);
    setHistory(updated);
    try {
      localStorage.setItem('diagrams_history', JSON.stringify(updated));
    } catch (e) {}
  };

  // رندر mermaid
  useEffect(() => {
    let cancelled = false;

    const render = async () => {
      if (!diagram.trim()) {
        setSvgContent('');
        setRenderError('');
        return;
      }

      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: theme,
          securityLevel: 'loose',
          fontFamily: 'inherit',
          flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
          sequence: { useMaxWidth: true },
          gantt: { useMaxWidth: true },
        });

        // اعتبارسنجی اولیه
        const id = `mermaid-${Date.now()}`;
        const { svg } = await mermaid.render(id, diagram);

        if (!cancelled) {
          setSvgContent(svg);
          setRenderError('');
        }
      } catch (err: any) {
        if (!cancelled) {
          setSvgContent('');
          setRenderError(err?.message || 'خطا در رندر نمودار');
        }
      }
    };

    const timer = setTimeout(render, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [diagram, theme]);

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 2500);
  };

  const loadExample = async (type: string) => {
    setLoading(true);
    setSelectedType(type);

    try {
      const res = await fetch(`${API_BASE}/api/diagrams/examples/${type}`);
      if (res.ok) {
        const data = await res.json();
        const code = data.mermaid || data.diagram || data.content || FALLBACK_EXAMPLES[type] || '';
        setDiagram(code);
      } else {
        setDiagram(FALLBACK_EXAMPLES[type] || '');
      }
    } catch (e) {
      setDiagram(FALLBACK_EXAMPLES[type] || '');
    } finally {
      setLoading(false);
    }
  };

  const analyzeCode = async () => {
    if (!codeInput.trim()) {
      showError('کد را وارد کنید');
      return;
    }

    setAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/api/diagrams/analyze-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: codeInput, language: codeLanguage }),
      });

      if (res.ok) {
        const data = await res.json();
        const code = data.class_diagram || data.diagram || data.mermaid || '';
        if (code) {
          setDiagram(code);
          setSelectedType('class');
          saveHistory('class', code);
          showSuccess('نمودار کلاس تولید شد');
        } else {
          showError('نمودار قابل تولید نبود');
        }
      } else {
        showError('خطا در تحلیل کد');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setAnalyzing(false);
    }
  };

  const copyDiagram = async () => {
    try {
      await navigator.clipboard.writeText(diagram);
      showSuccess('کد کپی شد');
    } catch (e) {
      showError('کپی ناموفق');
    }
  };

  const openMermaidLive = () => {
    if (!diagram) return;
    try {
      const state = {
        code: diagram,
        mermaid: { theme: theme },
        autoSync: true,
        updateDiagram: true,
      };
      const json = JSON.stringify(state);
      const encoded = btoa(unescape(encodeURIComponent(json)));
      window.open(`https://mermaid.live/edit#base64:${encoded}`, '_blank');
    } catch (e) {
      showError('خطا در باز کردن لینک');
    }
  };

  const downloadSvg = () => {
    if (!svgContent) {
      showError('نموداری برای دانلود نیست');
      return;
    }
    const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diagram-${selectedType}-${Date.now()}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPng = async () => {
    if (!svgContent) {
      showError('نموداری برای دانلود نیست');
      return;
    }
    try {
      // تبدیل SVG به PNG
      const img = new Image();
      const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);

      img.onload = () => {
        const canvas = document.createElement('canvas');
        const scale = 2; // کیفیت بالا
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = theme === 'dark' ? '#1f2937' : '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.scale(scale, scale);
          ctx.drawImage(img, 0, 0);
          canvas.toBlob((pngBlob) => {
            if (pngBlob) {
              const pngUrl = URL.createObjectURL(pngBlob);
              const a = document.createElement('a');
              a.href = pngUrl;
              a.download = `diagram-${selectedType}-${Date.now()}.png`;
              a.click();
              URL.revokeObjectURL(pngUrl);
            }
          });
        }
        URL.revokeObjectURL(url);
      };

      img.onerror = () => {
        showError('خطا در تبدیل به PNG');
        URL.revokeObjectURL(url);
      };

      img.src = url;
    } catch (e) {
      showError('خطا در دانلود');
    }
  };

  const loadFromHistory = (item: DiagramHistory) => {
    setDiagram(item.code);
    setSelectedType(item.type);
  };

  const clearHistory = () => {
    if (!confirm('پاک کردن تمام تاریخچه؟')) return;
    setHistory([]);
    try {
      localStorage.removeItem('diagrams_history');
    } catch (e) {}
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900" dir="rtl">
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-md">
          {error}
        </div>
      )}
      {success && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-md">
          {success}
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
              📊 نمودارها
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              تولید و ویرایش نمودارها با Mermaid + پیش‌نمایش زنده
            </p>
          </div>
          <div className="flex gap-2">
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as any)}
              className="px-3 py-2 bg-white dark:bg-gray-800 dark:text-white border dark:border-gray-700 rounded-lg text-sm"
            >
              <option value="default">تم پیش‌فرض</option>
              <option value="dark">تاریک</option>
              <option value="forest">جنگل</option>
              <option value="neutral">خنثی</option>
            </select>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              🏠 خانه
            </Link>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* انتخاب و ویرایش */}
          <div className="space-y-6">
            {/* انواع نمودار */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <h2 className="font-bold mb-4 dark:text-white">نوع نمودار</h2>
              <div className="grid grid-cols-4 gap-2">
                {DIAGRAM_TYPES.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => loadExample(type.id)}
                    disabled={loading}
                    className={`p-3 rounded-lg text-center transition border ${
                      selectedType === type.id
                        ? 'bg-blue-500 text-white border-blue-500'
                        : 'bg-gray-50 dark:bg-gray-700 dark:text-gray-200 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                    } disabled:opacity-50`}
                  >
                    <div className="text-2xl mb-1">{type.icon}</div>
                    <div className="text-xs font-medium">{type.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* ویرایشگر */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                <h2 className="font-bold dark:text-white">کد Mermaid</h2>
                <div className="flex gap-1 flex-wrap">
                  <button
                    onClick={copyDiagram}
                    disabled={!diagram}
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-700 dark:text-gray-200 rounded text-sm hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                  >
                    📋 کپی
                  </button>
                  <button
                    onClick={() => saveHistory(selectedType, diagram)}
                    disabled={!diagram}
                    className="px-3 py-1 bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 rounded text-sm hover:bg-purple-200 disabled:opacity-50"
                  >
                    💾 ذخیره
                  </button>
                  <button
                    onClick={openMermaidLive}
                    disabled={!diagram}
                    className="px-3 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 rounded text-sm hover:bg-blue-200 disabled:opacity-50"
                  >
                    ↗ Mermaid Live
                  </button>
                </div>
              </div>
              <textarea
                value={diagram}
                onChange={(e) => setDiagram(e.target.value)}
                placeholder="کد Mermaid را اینجا وارد یا ویرایش کنید..."
                rows={12}
                className="w-full p-3 border rounded-lg dark:bg-gray-900 dark:border-gray-700 dark:text-white font-mono text-sm focus:outline-none focus:border-blue-500"
                dir="ltr"
                spellCheck={false}
              />
              <div className="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
                <span>{diagram.length} کاراکتر</span>
                {renderError && <span className="text-red-500">⚠ خطای syntax</span>}
                {!renderError && diagram && <span className="text-green-500">✓ معتبر</span>}
              </div>
            </div>

            {/* تحلیل کد */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <h2 className="font-bold mb-4 dark:text-white">🔍 تولید نمودار از کد</h2>

              <div className="mb-3">
                <select
                  value={codeLanguage}
                  onChange={(e) => setCodeLanguage(e.target.value)}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                </select>
              </div>

              <textarea
                value={codeInput}
                onChange={(e) => setCodeInput(e.target.value)}
                placeholder="کد خود را اینجا paste کنید (class‌ها استخراج می‌شوند)..."
                rows={6}
                className="w-full p-3 border rounded-lg dark:bg-gray-900 dark:border-gray-700 dark:text-white font-mono text-sm mb-3 focus:outline-none focus:border-blue-500"
                dir="ltr"
                spellCheck={false}
              />

              <button
                onClick={analyzeCode}
                disabled={analyzing || !codeInput.trim()}
                className="w-full py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition"
              >
                {analyzing ? '⏳ در حال تحلیل...' : '🚀 تولید نمودار کلاس'}
              </button>
            </div>

            {/* تاریخچه */}
            {history.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold dark:text-white">🕐 تاریخچه ({history.length})</h2>
                  <button
                    onClick={clearHistory}
                    className="text-xs text-red-500 hover:underline"
                  >
                    پاک کردن
                  </button>
                </div>
                <div className="space-y-2 max-h-60 overflow-auto">
                  {history.map((h) => {
                    const typeInfo = DIAGRAM_TYPES.find((t) => t.id === h.type);
                    return (
                      <button
                        key={h.id}
                        onClick={() => loadFromHistory(h)}
                        className="w-full text-right p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
                      >
                        <div className="flex items-center gap-2">
                          <span>{typeInfo?.icon || '📊'}</span>
                          <span className="dark:text-gray-200">
                            {typeInfo?.name || h.type}
                          </span>
                          <span className="text-xs text-gray-500 mr-auto">
                            {new Date(h.createdAt).toLocaleString('fa-IR')}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1" dir="ltr">
                          {h.code.split('\n')[0]}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* پیش‌نمایش */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 lg:sticky lg:top-4 lg:self-start">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <h2 className="font-bold dark:text-white">👁️ پیش‌نمایش زنده</h2>
              <div className="flex gap-1">
                <button
                  onClick={downloadSvg}
                  disabled={!svgContent}
                  className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 rounded text-sm hover:bg-green-200 disabled:opacity-50"
                >
                  ↓ SVG
                </button>
                <button
                  onClick={downloadPng}
                  disabled={!svgContent}
                  className="px-3 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 rounded text-sm hover:bg-blue-200 disabled:opacity-50"
                >
                  ↓ PNG
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center text-gray-400 py-12">
                <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                <p>در حال بارگذاری...</p>
              </div>
            ) : !diagram ? (
              <div className="text-center text-gray-400 py-12">
                <div className="text-5xl mb-4">📊</div>
                <p>یک نوع نمودار انتخاب کنید یا کد Mermaid وارد کنید</p>
              </div>
            ) : renderError ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-sm text-red-700 dark:text-red-300 font-medium mb-2">
                  ⚠ خطا در رندر نمودار:
                </p>
                <pre className="text-xs text-red-600 dark:text-red-400 whitespace-pre-wrap break-all">
                  {renderError}
                </pre>
                <p className="text-xs text-gray-500 mt-3">
                  syntax کد را بررسی کنید یا یکی از نمونه‌ها را انتخاب کنید.
                </p>
              </div>
            ) : (
              <div
                ref={previewRef}
                className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 min-h-[400px] flex items-center justify-center overflow-auto border dark:border-gray-700"
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
