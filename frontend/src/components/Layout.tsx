/**
 * Main Layout Component
 */

'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  CpuChipIcon,
  Cog6ToothIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  XMarkIcon,
  RocketLaunchIcon,
  ChartBarIcon,
  CommandLineIcon,
  ArchiveBoxIcon,
  EyeIcon,
  BookOpenIcon,
  ClipboardDocumentCheckIcon,
  UsersIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/lib/auth';
import GlobalAnalysisProgress from './GlobalAnalysisProgress';
import { InspectionProvider, InspectionToggle } from '@/lib/inspection/provider';
import { InspectionHighlights } from '@/lib/inspection/highlights';
import { SurfaceRecorder } from '@/lib/inspection/surface';

interface LayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { href: '/', label: 'خانه', icon: HomeIcon },
  { href: '/oversight', label: 'مرکز نظارت', icon: EyeIcon },
  { href: '/inspection', label: 'نظارت و سرکشی', icon: ClipboardDocumentCheckIcon },
  { href: '/creator', label: 'موتور خالق', icon: CommandLineIcon },
  { href: '/knowledge-center', label: 'مرکز دانش', icon: BookOpenIcon },
  { href: '/debate', label: 'مناظره', icon: ChatBubbleLeftRightIcon },
  { href: '/projects', label: 'پروژه‌ها', icon: RocketLaunchIcon },
  { href: '/diagrams', label: 'نمودارها', icon: ChartBarIcon },
  { href: '/archive', label: 'آرشیو', icon: ArchiveBoxIcon },
  { href: '/models', label: 'مدل‌ها', icon: CpuChipIcon },
  { href: '/settings', label: 'تنظیمات', icon: Cog6ToothIcon },
];

/** The label of the screen the owner is on — the longest matching menu entry. */
function labelFor(pathname: string): string {
  let best = '';
  let label = '';
  for (const item of navItems) {
    const hit = item.href === '/' ? pathname === '/' : (pathname === item.href || pathname.startsWith(`${item.href}/`));
    if (hit && item.href.length > best.length) { best = item.href; label = item.label; }
  }
  if (!label && pathname.startsWith('/project/')) return 'پروژه';
  return label || pathname;
}

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname() || '/';
  const pageLabel = labelFor(pathname);
  return (
    // «نظارت و سرکشی» wraps the whole shell, so the capture overlay, the
    // highlights and the surface map work on every screen — including screens
    // added later, without touching them.
    <InspectionProvider pathname={pathname} pageLabel={pageLabel}>
      <Shell pathname={pathname} pageLabel={pageLabel}>{children}</Shell>
      <InspectionHighlights pathname={pathname} />
      <SurfaceRecorder pathname={pathname} />
    </InspectionProvider>
  );
}

/** Who is signed in, the owner-only «کاربران» entry, and «خروج». */
function AccountBox() {
  const { user, role, enforced, logout } = useAuth();
  if (!user && !enforced) return null;
  return (
    <div className="space-y-1">
      {role === 'owner' && (
        <Link href="/users" className="flex items-center gap-3 px-4 py-2 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
          <UsersIcon className="w-5 h-5" /><span className="font-medium">کاربران</span>
        </Link>
      )}
      {user && (
        <div className="flex items-center gap-2 px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
          {user.picture
            // eslint-disable-next-line @next/next/no-img-element
            ? <img src={user.picture} alt="" className="w-6 h-6 rounded-full" referrerPolicy="no-referrer" />
            : <span>👤</span>}
          <span className="flex-1 truncate" dir="ltr">{user.email}</span>
          <button onClick={logout} title="خروج" className="hover:text-red-600"><ArrowRightOnRectangleIcon className="w-5 h-5" /></button>
        </div>
      )}
    </div>
  );
}

function Shell({ children, pathname, pageLabel }: LayoutProps & { pathname: string; pageLabel: string }) {
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    // Check system preference
    const isDark = localStorage.getItem('darkMode') === 'true' ||
      (!localStorage.getItem('darkMode') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setDarkMode(isDark);
    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', String(newDarkMode));
    document.documentElement.classList.toggle('dark', newDarkMode);
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar for desktop */}
      <aside data-report-section="sidebar" data-report-section-label="منوی کناری" className="hidden md:flex md:flex-col md:w-64 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700">
        {/* Logo */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center">
              <span className="text-white text-xl">🤖</span>
            </div>
            <div>
              <h1 className="font-bold text-gray-900 dark:text-white">سیستم مناظره AI</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">نسخه 2.0</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                  isActive
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Global Analysis Progress */}
        <GlobalAnalysisProgress />

        {/* Theme toggle */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-1">
          <AccountBox />
          <InspectionToggle />
          <button
            onClick={toggleDarkMode}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
          >
            {darkMode ? (
              <>
                <SunIcon className="w-5 h-5" />
                <span>حالت روشن</span>
              </>
            ) : (
              <>
                <MoonIcon className="w-5 h-5" />
                <span>حالت تاریک</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <aside className="fixed top-0 right-0 bottom-0 w-64 bg-white dark:bg-gray-800 shadow-xl">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <span className="font-bold text-gray-900 dark:text-white">منو</span>
              <button onClick={() => setSidebarOpen(false)}>
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>
            <nav className="p-4 space-y-2">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                    pathname === item.href
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col min-h-screen">
        {/* Mobile header */}
        <header data-report-section="mobile-header" data-report-section-label="سرصفحهٔ موبایل" className="md:hidden flex items-center justify-between p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <button onClick={() => setSidebarOpen(true)}>
            <Bars3Icon className="w-6 h-6" />
          </button>
          <span className="font-bold">سیستم مناظره AI</span>
          <button onClick={toggleDarkMode}>
            {darkMode ? <SunIcon className="w-6 h-6" /> : <MoonIcon className="w-6 h-6" />}
          </button>
        </header>

        {/* Page content — the reportable surface of every screen */}
        <div className="flex-1 p-4 md:p-8 overflow-auto"
          data-report-surface={pathname} data-report-surface-label={pageLabel}>
          {children}
        </div>
      </main>
    </div>
  );
}
