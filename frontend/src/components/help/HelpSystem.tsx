'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { getPageHelp, PageHelp, ElementHelp } from './helpData';

// ============================================
// کامپوننت نمایش دیاگرام Mermaid
// ============================================
function MermaidDiagram({ chart }: { chart: string }) {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: 'base',
          themeVariables: {
            primaryColor: '#3b82f6',
            primaryTextColor: '#1f2937',
            primaryBorderColor: '#2563eb',
            lineColor: '#6b7280',
            secondaryColor: '#f3f4f6',
            tertiaryColor: '#e5e7eb',
          },
          flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis',
          },
        });

        const id = `mermaid-${Date.now()}`;
        const { svg: renderedSvg } = await mermaid.render(id, chart);
        setSvg(renderedSvg);
        setError('');
      } catch (err) {
        console.error('Mermaid render error:', err);
        setError('خطا در رندر دیاگرام');
      }
    };

    renderDiagram();
  }, [chart]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div
      className="mermaid-container overflow-auto max-h-[400px] p-4 bg-white dark:bg-gray-800 rounded-lg"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

// ============================================
// کامپوننت نمایش المان‌های راهنما
// ============================================
function ElementHelpCard({ element }: { element: ElementHelp }) {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'button': return '🔘';
      case 'input': return '📝';
      case 'section': return '📦';
      case 'tab': return '📑';
      case 'panel': return '🖼️';
      case 'checkbox': return '☑️';
      case 'select': return '📋';
      case 'area': return '🗺️';
      default: return '•';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'button': return 'دکمه';
      case 'input': return 'ورودی';
      case 'section': return 'بخش';
      case 'tab': return 'تب';
      case 'panel': return 'پنل';
      case 'checkbox': return 'چک‌باکس';
      case 'select': return 'انتخاب';
      case 'area': return 'ناحیه';
      default: return type;
    }
  };

  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
      <div className="flex items-start gap-2">
        <span className="text-lg">{getTypeIcon(element.type)}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-gray-900 dark:text-white">
              {element.title}
            </span>
            <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-600 rounded">
              {getTypeLabel(element.type)}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
            {element.description}
          </p>
          {element.tips && element.tips.length > 0 && (
            <div className="mt-2 space-y-1">
              {element.tips.map((tip, i) => (
                <div key={i} className="flex items-start gap-1 text-xs text-blue-600 dark:text-blue-400">
                  <span>💡</span>
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// تابع تولید محتوای دانلود
// ============================================
function generateDownloadContent(pageHelp: PageHelp): string {
  let content = `# ${pageHelp.title}\n\n`;
  content += `## توضیحات\n${pageHelp.description}\n\n`;
  content += `## مسیر\n\`${pageHelp.path}\`\n\n`;
  content += `## نمای کلی\n${pageHelp.overview}\n\n`;

  content += `## قابلیت‌ها\n`;
  pageHelp.features.forEach(f => {
    content += `- ${f}\n`;
  });
  content += '\n';

  content += `## المان‌ها و قابلیت‌های صفحه\n\n`;
  pageHelp.elements.forEach(el => {
    content += `### ${el.title}\n`;
    content += `- **نوع:** ${el.type}\n`;
    content += `- **توضیحات:** ${el.description}\n`;
    if (el.tips && el.tips.length > 0) {
      content += `- **نکات:**\n`;
      el.tips.forEach(tip => {
        content += `  - ${tip}\n`;
      });
    }
    content += '\n';
  });

  content += `## دیاگرام ساختاری\n\n`;
  content += '```mermaid\n';
  content += pageHelp.diagram;
  content += '\n```\n';

  return content;
}

// ============================================
// کامپوننت اصلی سیستم راهنما
// ============================================
export default function HelpSystem() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [pageHelp, setPageHelp] = useState<PageHelp | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'elements' | 'diagram'>('overview');
  const [searchQuery, setSearchQuery] = useState('');

  // بارگذاری راهنمای صفحه فعلی
  useEffect(() => {
    const help = getPageHelp(pathname);
    setPageHelp(help || null);
  }, [pathname]);

  // فیلتر المان‌ها بر اساس جستجو
  const filteredElements = pageHelp?.elements.filter(el =>
    el.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    el.description.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // دانلود راهنما
  const handleDownload = useCallback(() => {
    if (!pageHelp) return;

    const content = generateDownloadContent(pageHelp);
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `help-${pageHelp.id}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [pageHelp]);

  // اگر راهنمایی نیست، نمایش نده
  if (!pageHelp) return null;

  return (
    <>
      {/* دکمه شناور راهنما */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 left-6 z-40 w-14 h-14 bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all flex items-center justify-center group"
        title="راهنمای صفحه"
      >
        <span className="text-2xl">❓</span>
        <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-3 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          راهنمای صفحه
        </span>
      </button>

      {/* پنل راهنما */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex" dir="rtl">
          {/* پس‌زمینه تاریک */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />

          {/* پنل اصلی */}
          <div className="relative mr-auto w-full max-w-2xl h-full bg-white dark:bg-gray-900 shadow-2xl overflow-hidden flex flex-col animate-slide-in-right">
            {/* هدر */}
            <div className="flex-shrink-0 p-4 border-b dark:border-gray-700 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">📖</span>
                  <div>
                    <h2 className="text-xl font-bold">{pageHelp.title}</h2>
                    <p className="text-sm opacity-80">{pageHelp.path}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleDownload}
                    className="p-2 hover:bg-white/20 rounded-lg transition"
                    title="دانلود راهنما"
                  >
                    📥
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 hover:bg-white/20 rounded-lg transition text-xl"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>

            {/* تب‌ها */}
            <div className="flex-shrink-0 flex border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              {[
                { id: 'overview', label: 'نمای کلی', icon: '📋' },
                { id: 'elements', label: 'المان‌ها', icon: '🧩' },
                { id: 'diagram', label: 'دیاگرام', icon: '📊' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveSection(tab.id as any)}
                  className={`flex-1 py-3 px-4 flex items-center justify-center gap-2 transition font-medium ${
                    activeSection === tab.id
                      ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400 bg-white dark:bg-gray-900'
                      : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>

            {/* محتوا */}
            <div className="flex-1 overflow-auto p-4">
              {/* نمای کلی */}
              {activeSection === 'overview' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
                      <span>📝</span>
                      <span>توضیحات</span>
                    </h3>
                    <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                      {pageHelp.overview}
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
                      <span>✨</span>
                      <span>قابلیت‌های این صفحه</span>
                    </h3>
                    <ul className="space-y-2">
                      {pageHelp.features.map((feature, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg"
                        >
                          <span className="text-green-500">✓</span>
                          <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
                      <span>📊</span>
                      <span>آمار</span>
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center">
                        <div className="text-2xl font-bold text-blue-600">{pageHelp.elements.length}</div>
                        <div className="text-xs text-gray-500">المان</div>
                      </div>
                      <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-center">
                        <div className="text-2xl font-bold text-purple-600">{pageHelp.features.length}</div>
                        <div className="text-xs text-gray-500">قابلیت</div>
                      </div>
                      <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
                        <div className="text-2xl font-bold text-green-600">
                          {pageHelp.elements.filter(e => e.tips && e.tips.length > 0).length}
                        </div>
                        <div className="text-xs text-gray-500">نکته</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* المان‌ها */}
              {activeSection === 'elements' && (
                <div className="space-y-4">
                  {/* جستجو */}
                  <div className="sticky top-0 bg-white dark:bg-gray-900 pb-2">
                    <input
                      type="text"
                      placeholder="جستجو در المان‌ها..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full p-3 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                    />
                  </div>

                  {/* گروه‌بندی المان‌ها */}
                  <div className="space-y-4">
                    {['button', 'input', 'tab', 'section', 'panel', 'checkbox', 'select', 'area'].map(type => {
                      const elements = filteredElements.filter(e => e.type === type);
                      if (elements.length === 0) return null;

                      const typeLabels: Record<string, string> = {
                        button: '🔘 دکمه‌ها',
                        input: '📝 ورودی‌ها',
                        tab: '📑 تب‌ها',
                        section: '📦 بخش‌ها',
                        panel: '🖼️ پنل‌ها',
                        checkbox: '☑️ چک‌باکس‌ها',
                        select: '📋 لیست‌های انتخاب',
                        area: '🗺️ ناحیه‌ها',
                      };

                      return (
                        <div key={type}>
                          <h3 className="font-bold text-gray-700 dark:text-gray-300 mb-2">
                            {typeLabels[type]}
                          </h3>
                          <div className="space-y-2">
                            {elements.map(el => (
                              <ElementHelpCard key={el.id} element={el} />
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {filteredElements.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                      <span className="text-4xl">🔍</span>
                      <p className="mt-2">المانی یافت نشد</p>
                    </div>
                  )}
                </div>
              )}

              {/* دیاگرام */}
              {activeSection === 'diagram' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                      <span>🗺️</span>
                      <span>ساختار صفحه</span>
                    </h3>
                  </div>

                  <MermaidDiagram chart={pageHelp.diagram} />

                  <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                    <h4 className="font-bold text-yellow-700 dark:text-yellow-300 mb-2">
                      💡 راهنمای دیاگرام
                    </h4>
                    <ul className="text-sm text-yellow-600 dark:text-yellow-400 space-y-1">
                      <li>• مستطیل‌ها = بخش‌ها و کامپوننت‌ها</li>
                      <li>• فلش‌ها = جریان داده یا ناوبری</li>
                      <li>• گروه‌ها = بخش‌های مرتبط</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {/* فوتر */}
            <div className="flex-shrink-0 p-3 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-center text-xs text-gray-500">
              برای دانلود راهنما روی دکمه 📥 کلیک کنید
            </div>
          </div>
        </div>
      )}

      {/* استایل‌های انیمیشن */}
      <style jsx global>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }

        @keyframes fade-in {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        .animate-fade-in {
          animation: fade-in 0.2s ease-out;
        }

        .mermaid-container svg {
          max-width: 100%;
          height: auto;
        }
      `}</style>
    </>
  );
}
