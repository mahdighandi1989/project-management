'use client';

import { useState, useEffect, useCallback } from 'react';
// Layout is already provided by app/layout.tsx - DO NOT use here

const DIAGRAM_TYPES = [
  { id: 'flowchart', name: 'نمودار جریان', icon: '📊', description: 'فرآیندها و تصمیم‌گیری' },
  { id: 'sequence', name: 'نمودار توالی', icon: '📋', description: 'تعامل بین اجزا' },
  { id: 'class', name: 'نمودار کلاس', icon: '🏗️', description: 'ساختار کد OOP' },
  { id: 'er', name: 'نمودار ER', icon: '🗄️', description: 'مدل دیتابیس' },
  { id: 'gantt', name: 'نمودار Gantt', icon: '📅', description: 'برنامه‌ریزی زمانی' },
  { id: 'pie', name: 'نمودار دایره‌ای', icon: '🥧', description: 'نسبت و سهم' },
  { id: 'mindmap', name: 'نقشه ذهنی', icon: '🧠', description: 'ایده‌پردازی' },
  { id: 'state', name: 'نمودار وضعیت', icon: '🔄', description: 'State machine' },
];

export default function DiagramsPage() {
  const [selectedType, setSelectedType] = useState('flowchart');
  const [diagram, setDiagram] = useState('');
  const [loading, setLoading] = useState(false);

  // برای تحلیل کد
  const [codeInput, setCodeInput] = useState('');
  const [codeLanguage, setCodeLanguage] = useState('python');
  const [codeAnalysis, setCodeAnalysis] = useState<any>(null);

  // بارگذاری نمونه
  const loadExample = async (type: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/diagrams/examples/${type}`);
      const data = await res.json();
      if (data.success) {
        setDiagram(data.mermaid);
      }
    } catch (error) {
      console.error('Error loading example:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExample(selectedType);
  }, [selectedType]);

  // تحلیل کد
  const analyzeCode = async () => {
    if (!codeInput.trim()) return;

    setLoading(true);
    try {
      const res = await fetch('/api/diagrams/analyze-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: codeInput,
          language: codeLanguage,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setCodeAnalysis(data.analysis);
        setDiagram(data.class_diagram);
        setSelectedType('class');
      }
    } catch (error) {
      console.error('Error analyzing code:', error);
    } finally {
      setLoading(false);
    }
  };

  // کپی نمودار
  const copyDiagram = () => {
    navigator.clipboard.writeText(diagram);
    alert('نمودار کپی شد!');
  };

  // باز کردن در Mermaid Live
  const openInMermaidLive = () => {
    const encoded = btoa(unescape(encodeURIComponent(diagram)));
    const url = `https://mermaid.live/edit#base64:${encoded}`;
    window.open(url, '_blank');
  };

  return (
    <>
      <div className="p-6">
        {/* هدر */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold">📊 تولید نمودار</h1>
          <p className="text-gray-600 dark:text-gray-400">
            تولید نمودارهای Mermaid داینامیک برای پروژه‌ها
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* انتخاب نوع نمودار */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4">
              <h2 className="font-semibold mb-4">انواع نمودار</h2>
              <div className="space-y-2">
                {DIAGRAM_TYPES.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setSelectedType(type.id)}
                    className={`w-full p-3 rounded-lg text-right transition flex items-center gap-3 ${
                      selectedType === type.id
                        ? 'bg-primary text-white'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <span className="text-xl">{type.icon}</span>
                    <div>
                      <div className="font-medium text-sm">{type.name}</div>
                      <div className={`text-xs ${selectedType === type.id ? 'text-white/80' : 'text-gray-500'}`}>
                        {type.description}
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* تحلیل کد */}
              <div className="mt-6 pt-6 border-t dark:border-gray-600">
                <h3 className="font-semibold mb-3">🔍 تحلیل کد</h3>
                <div className="mb-3">
                  <select
                    value={codeLanguage}
                    onChange={(e) => setCodeLanguage(e.target.value)}
                    className="w-full p-2 border rounded-lg text-sm dark:bg-gray-700 dark:border-gray-600"
                  >
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="typescript">TypeScript</option>
                  </select>
                </div>
                <textarea
                  value={codeInput}
                  onChange={(e) => setCodeInput(e.target.value)}
                  className="w-full p-2 border rounded-lg text-sm font-mono h-32 dark:bg-gray-700 dark:border-gray-600"
                  placeholder="کد خود را اینجا وارد کنید..."
                  dir="ltr"
                />
                <button
                  onClick={analyzeCode}
                  disabled={!codeInput.trim() || loading}
                  className="w-full mt-2 py-2 bg-secondary text-white rounded-lg hover:bg-secondary/90 disabled:opacity-50"
                >
                  {loading ? '...' : 'تحلیل و تولید نمودار'}
                </button>
              </div>
            </div>
          </div>

          {/* نمایش نمودار */}
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              {/* دکمه‌های عملیات */}
              <div className="flex justify-between items-center mb-4">
                <h2 className="font-semibold">
                  {DIAGRAM_TYPES.find(t => t.id === selectedType)?.icon}{' '}
                  {DIAGRAM_TYPES.find(t => t.id === selectedType)?.name}
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={copyDiagram}
                    className="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    📋 کپی
                  </button>
                  <button
                    onClick={openInMermaidLive}
                    className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-dark"
                  >
                    🔗 مشاهده آنلاین
                  </button>
                </div>
              </div>

              {loading ? (
                <div className="text-center py-12">
                  <div className="animate-spin w-10 h-10 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
                  <p className="mt-4 text-gray-500">در حال تولید نمودار...</p>
                </div>
              ) : (
                <>
                  {/* کد نمودار */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">کد Mermaid</label>
                    <textarea
                      value={diagram}
                      onChange={(e) => setDiagram(e.target.value)}
                      className="w-full h-64 p-4 font-mono text-sm border rounded-lg bg-gray-50 dark:bg-gray-900 dark:border-gray-600"
                      dir="ltr"
                    />
                  </div>

                  {/* راهنمای سریع */}
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                    <h3 className="font-medium mb-2">💡 راهنما</h3>
                    <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
                      <li>• کد Mermaid را می‌توانید ویرایش کنید</li>
                      <li>• برای مشاهده گرافیکی، روی "مشاهده آنلاین" کلیک کنید</li>
                      <li>• در GitHub/Notion/GitLab می‌توانید نمودار را مستقیم استفاده کنید</li>
                    </ul>
                  </div>
                </>
              )}

              {/* نتیجه تحلیل کد */}
              {codeAnalysis && (
                <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <h3 className="font-semibold mb-3">نتیجه تحلیل کد</h3>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500">کلاس‌ها</div>
                      <div className="font-bold text-lg">{codeAnalysis.classes?.length || 0}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">توابع</div>
                      <div className="font-bold text-lg">{codeAnalysis.functions?.length || 0}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">imports</div>
                      <div className="font-bold text-lg">{codeAnalysis.imports?.length || 0}</div>
                    </div>
                  </div>

                  {codeAnalysis.classes?.length > 0 && (
                    <div className="mt-4">
                      <div className="text-sm text-gray-500 mb-2">کلاس‌های شناسایی شده:</div>
                      <div className="flex flex-wrap gap-2">
                        {codeAnalysis.classes.map((cls: any, i: number) => (
                          <span key={i} className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm">
                            {cls.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* نمونه‌های کاربردی */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mt-6">
              <h3 className="font-semibold mb-4">💡 کاربردهای رایج</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                  <div className="text-3xl mb-2">🏗️</div>
                  <div className="text-sm font-medium">معماری سیستم</div>
                  <div className="text-xs text-gray-500">flowchart</div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                  <div className="text-3xl mb-2">🔀</div>
                  <div className="text-sm font-medium">API Flow</div>
                  <div className="text-xs text-gray-500">sequence</div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                  <div className="text-3xl mb-2">📅</div>
                  <div className="text-sm font-medium">برنامه‌ریزی</div>
                  <div className="text-xs text-gray-500">gantt</div>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center">
                  <div className="text-3xl mb-2">🗄️</div>
                  <div className="text-sm font-medium">دیتابیس</div>
                  <div className="text-xs text-gray-500">er</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
