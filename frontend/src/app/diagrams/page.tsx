'use client';

import { useState } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const DIAGRAM_TYPES = [
  { id: 'flowchart', name: 'فلوچارت', icon: '📊' },
  { id: 'sequence', name: 'توالی', icon: '📋' },
  { id: 'class', name: 'کلاس', icon: '🏗️' },
  { id: 'er', name: 'ER', icon: '🗄️' },
  { id: 'gantt', name: 'Gantt', icon: '📅' },
  { id: 'pie', name: 'دایره‌ای', icon: '🥧' },
  { id: 'mindmap', name: 'ذهنی', icon: '🧠' },
  { id: 'state', name: 'وضعیت', icon: '🔄' },
];

export default function DiagramsPage() {
  const [selectedType, setSelectedType] = useState('flowchart');
  const [diagram, setDiagram] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // تحلیل کد
  const [codeInput, setCodeInput] = useState('');
  const [codeLanguage, setCodeLanguage] = useState('python');

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(''), 4000);
  };

  const loadExample = async (type: string) => {
    setLoading(true);
    setSelectedType(type);
    setDiagram('');

    try {
      const res = await fetch(`${API_BASE}/api/diagrams/examples/${type}`);
      if (res.ok) {
        const data = await res.json();
        setDiagram(data.diagram || data.content || '');
      } else {
        // نمونه پیش‌فرض
        const examples: Record<string, string> = {
          flowchart: `flowchart TD
    A[شروع] --> B{تصمیم}
    B -->|بله| C[عملیات ۱]
    B -->|خیر| D[عملیات ۲]
    C --> E[پایان]
    D --> E`,
          sequence: `sequenceDiagram
    کاربر->>سرور: درخواست
    سرور->>دیتابیس: کوئری
    دیتابیس-->>سرور: نتیجه
    سرور-->>کاربر: پاسخ`,
          class: `classDiagram
    class User {
        +String name
        +String email
        +login()
    }
    class Order {
        +Int id
        +Date date
    }
    User --> Order`,
          er: `erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ ITEM : contains`,
          gantt: `gantt
    title پروژه
    section فاز ۱
    تحلیل :a1, 2024-01-01, 7d
    طراحی :a2, after a1, 5d`,
          pie: `pie title توزیع
    "بخش ۱" : 40
    "بخش ۲" : 30
    "بخش ۳" : 30`,
          mindmap: `mindmap
  root((موضوع))
    شاخه ۱
      زیرشاخه
    شاخه ۲`,
          state: `stateDiagram-v2
    [*] --> Idle
    Idle --> Running : شروع
    Running --> Stopped : توقف
    Stopped --> [*]`,
        };
        setDiagram(examples[type] || '');
      }
    } catch (e) {
      showError('خطا در بارگذاری');
    } finally {
      setLoading(false);
    }
  };

  const analyzeCode = async () => {
    if (!codeInput.trim()) {
      showError('کد را وارد کنید');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/diagrams/analyze-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: codeInput, language: codeLanguage }),
      });

      if (res.ok) {
        const data = await res.json();
        setDiagram(data.diagram || '');
        setSelectedType('class');
      } else {
        showError('خطا در تحلیل');
      }
    } catch (e) {
      showError('خطا در ارتباط');
    } finally {
      setLoading(false);
    }
  };

  const copyDiagram = () => {
    navigator.clipboard.writeText(diagram);
  };

  const openMermaidLive = () => {
    if (diagram) {
      const encoded = btoa(unescape(encodeURIComponent(diagram)));
      window.open(`https://mermaid.live/edit#base64:${encoded}`, '_blank');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900" dir="rtl">
      {/* پیام‌ها */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {error}
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6">
        {/* هدر */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">نمودارها</h1>
            <p className="text-gray-500 text-sm">تولید نمودار با Mermaid</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300"
          >
            خانه
          </Link>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* انتخاب و ویرایش */}
          <div className="space-y-6">
            {/* انواع نمودار */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <h2 className="font-bold mb-4">نوع نمودار</h2>
              <div className="grid grid-cols-4 gap-2">
                {DIAGRAM_TYPES.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => loadExample(type.id)}
                    className={`p-3 rounded-lg text-center transition ${
                      selectedType === type.id
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <div className="text-2xl mb-1">{type.icon}</div>
                    <div className="text-xs">{type.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* ویرایشگر */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">کد Mermaid</h2>
                <div className="flex gap-2">
                  <button
                    onClick={copyDiagram}
                    disabled={!diagram}
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
                  >
                    کپی
                  </button>
                  <button
                    onClick={openMermaidLive}
                    disabled={!diagram}
                    className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200 disabled:opacity-50"
                  >
                    Mermaid Live
                  </button>
                </div>
              </div>
              <textarea
                value={diagram}
                onChange={(e) => setDiagram(e.target.value)}
                placeholder="کد Mermaid اینجا..."
                rows={10}
                className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 font-mono text-sm"
                dir="ltr"
              />
            </div>

            {/* تحلیل کد */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
              <h2 className="font-bold mb-4">تحلیل کد</h2>

              <div className="mb-3">
                <select
                  value={codeLanguage}
                  onChange={(e) => setCodeLanguage(e.target.value)}
                  className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                </select>
              </div>

              <textarea
                value={codeInput}
                onChange={(e) => setCodeInput(e.target.value)}
                placeholder="کد خود را اینجا بنویسید..."
                rows={6}
                className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 font-mono text-sm mb-3"
                dir="ltr"
              />

              <button
                onClick={analyzeCode}
                disabled={loading}
                className="w-full py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {loading ? 'در حال تحلیل...' : 'تولید نمودار کلاس'}
              </button>
            </div>
          </div>

          {/* پیش‌نمایش */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h2 className="font-bold mb-4">پیش‌نمایش</h2>

            {loading ? (
              <div className="text-center text-gray-400 py-12">
                در حال بارگذاری...
              </div>
            ) : !diagram ? (
              <div className="text-center text-gray-400 py-12">
                <div className="text-5xl mb-4">📊</div>
                <p>یک نوع نمودار انتخاب کنید</p>
              </div>
            ) : (
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 min-h-[400px] flex items-center justify-center">
                <img
                  src={`https://mermaid.ink/img/${btoa(diagram)}`}
                  alt="Diagram"
                  className="max-w-full max-h-[500px]"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
