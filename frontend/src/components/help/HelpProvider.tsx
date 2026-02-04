'use client';

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { getPageHelp, getElementHelp, PageHelp, ElementHelp } from './helpData';

// ============================================
// Context برای سیستم راهنما
// ============================================
interface HelpContextType {
  pageHelp: PageHelp | null;
  isHelpMode: boolean;
  toggleHelpMode: () => void;
  getTooltipContent: (elementId: string) => ElementHelp | undefined;
  showGlobalTooltip: (content: string, title: string, x: number, y: number) => void;
  hideGlobalTooltip: () => void;
}

const HelpContext = createContext<HelpContextType>({
  pageHelp: null,
  isHelpMode: false,
  toggleHelpMode: () => {},
  getTooltipContent: () => undefined,
  showGlobalTooltip: () => {},
  hideGlobalTooltip: () => {},
});

export const useHelp = () => useContext(HelpContext);

// ============================================
// Global Tooltip Component
// ============================================
interface GlobalTooltipState {
  visible: boolean;
  content: string;
  title: string;
  x: number;
  y: number;
}

function GlobalTooltip({ state }: { state: GlobalTooltipState }) {
  if (!state.visible) return null;

  // محاسبه موقعیت برای جلوگیری از خروج از صفحه
  const style: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(state.x, window.innerWidth - 320),
    top: Math.max(state.y - 80, 10),
    zIndex: 99999,
  };

  return (
    <div style={style} className="animate-fade-in">
      <div className="bg-gray-900 text-white text-sm rounded-xl shadow-2xl max-w-xs p-4 border border-gray-700">
        {state.title && (
          <div className="font-bold text-yellow-400 mb-2 pb-2 border-b border-gray-700 flex items-center gap-2">
            <span>💡</span>
            <span>{state.title}</span>
          </div>
        )}
        <div className="text-gray-200 leading-relaxed whitespace-pre-wrap">
          {state.content}
        </div>
      </div>
      <div className="absolute -bottom-2 left-4 w-0 h-0 border-l-[8px] border-r-[8px] border-t-[8px] border-l-transparent border-r-transparent border-t-gray-900" />
    </div>
  );
}

// ============================================
// Provider Component
// ============================================
export function HelpProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [pageHelp, setPageHelp] = useState<PageHelp | null>(null);
  const [isHelpMode, setIsHelpMode] = useState(false);
  const [tooltipState, setTooltipState] = useState<GlobalTooltipState>({
    visible: false,
    content: '',
    title: '',
    x: 0,
    y: 0,
  });

  // بارگذاری راهنمای صفحه
  useEffect(() => {
    const help = getPageHelp(pathname);
    setPageHelp(help || null);
  }, [pathname]);

  // تغییر حالت راهنما
  const toggleHelpMode = useCallback(() => {
    setIsHelpMode(prev => !prev);
  }, []);

  // دریافت محتوای tooltip برای یک المان
  const getTooltipContent = useCallback((elementId: string): ElementHelp | undefined => {
    if (!pageHelp) return undefined;
    return pageHelp.elements.find(e => e.id === elementId);
  }, [pageHelp]);

  // نمایش tooltip سراسری
  const showGlobalTooltip = useCallback((content: string, title: string, x: number, y: number) => {
    setTooltipState({
      visible: true,
      content,
      title,
      x,
      y,
    });
  }, []);

  // مخفی کردن tooltip سراسری
  const hideGlobalTooltip = useCallback(() => {
    setTooltipState(prev => ({ ...prev, visible: false }));
  }, []);

  // Keyboard shortcut برای حالت راهنما (Ctrl+H)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'h') {
        e.preventDefault();
        toggleHelpMode();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleHelpMode]);

  return (
    <HelpContext.Provider
      value={{
        pageHelp,
        isHelpMode,
        toggleHelpMode,
        getTooltipContent,
        showGlobalTooltip,
        hideGlobalTooltip,
      }}
    >
      {children}
      <GlobalTooltip state={tooltipState} />

      {/* نشانگر حالت راهنما */}
      {isHelpMode && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-blue-500 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 animate-bounce">
          <span>❓</span>
          <span>حالت راهنما فعال است - روی هر قسمت نگه دارید</span>
          <button
            onClick={toggleHelpMode}
            className="mr-2 p-1 hover:bg-blue-600 rounded"
          >
            ✕
          </button>
        </div>
      )}
    </HelpContext.Provider>
  );
}

// ============================================
// HOC برای اضافه کردن tooltip به المان‌ها
// ============================================
interface WithHelpTooltipProps {
  helpId: string;
  children: ReactNode;
  className?: string;
}

export function WithHelpTooltip({ helpId, children, className = '' }: WithHelpTooltipProps) {
  const { isHelpMode, getTooltipContent, showGlobalTooltip, hideGlobalTooltip } = useHelp();
  const [isHovered, setIsHovered] = useState(false);

  const elementHelp = getTooltipContent(helpId);

  const handleMouseEnter = (e: React.MouseEvent) => {
    if (isHelpMode && elementHelp) {
      setIsHovered(true);
      showGlobalTooltip(
        elementHelp.description + (elementHelp.tips?.length ? '\n\n💡 ' + elementHelp.tips.join('\n💡 ') : ''),
        elementHelp.title,
        e.clientX,
        e.clientY
      );
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    hideGlobalTooltip();
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isHelpMode && elementHelp && isHovered) {
      showGlobalTooltip(
        elementHelp.description + (elementHelp.tips?.length ? '\n\n💡 ' + elementHelp.tips.join('\n💡 ') : ''),
        elementHelp.title,
        e.clientX,
        e.clientY
      );
    }
  };

  return (
    <div
      className={`${className} ${isHelpMode ? 'cursor-help' : ''} ${isHovered && isHelpMode ? 'ring-2 ring-blue-400 ring-offset-2 rounded' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
    >
      {children}
    </div>
  );
}

// ============================================
// کامپوننت tooltip ساده (بدون حالت راهنما)
// ============================================
interface SimpleTooltipProps {
  content: string;
  title?: string;
  children: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export function SimpleTooltip({ content, title, children, position = 'top' }: SimpleTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });

  const handleMouseEnter = (e: React.MouseEvent) => {
    setIsVisible(true);
    setCoords({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    setCoords({ x: e.clientX, y: e.clientY });
  };

  const handleMouseLeave = () => {
    setIsVisible(false);
  };

  const getPositionStyle = (): React.CSSProperties => {
    const offset = 10;
    switch (position) {
      case 'bottom':
        return { left: coords.x, top: coords.y + offset };
      case 'left':
        return { left: coords.x - 250 - offset, top: coords.y - 30 };
      case 'right':
        return { left: coords.x + offset, top: coords.y - 30 };
      default: // top
        return { left: coords.x, top: coords.y - 80 };
    }
  };

  return (
    <div
      className="inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {isVisible && (
        <div
          className="fixed z-[99999] animate-fade-in"
          style={getPositionStyle()}
        >
          <div className="bg-gray-900 text-white text-sm rounded-lg shadow-xl max-w-xs p-3">
            {title && (
              <div className="font-bold text-yellow-400 mb-1 pb-1 border-b border-gray-700">
                {title}
              </div>
            )}
            <div className="text-gray-200 leading-relaxed">
              {content}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
