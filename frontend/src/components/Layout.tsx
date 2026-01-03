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
} from '@heroicons/react/24/outline';

interface LayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { href: '/', label: 'خانه', icon: HomeIcon },
  { href: '/debate', label: 'مناظره', icon: ChatBubbleLeftRightIcon },
  { href: '/projects', label: 'پروژه‌ها', icon: RocketLaunchIcon },
  { href: '/diagrams', label: 'نمودارها', icon: ChartBarIcon },
  { href: '/models', label: 'مدل‌ها', icon: CpuChipIcon },
  { href: '/settings', label: 'تنظیمات', icon: Cog6ToothIcon },
];

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();
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
      <aside className="hidden md:flex md:flex-col md:w-64 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700">
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

        {/* Theme toggle */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
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
        <header className="md:hidden flex items-center justify-between p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <button onClick={() => setSidebarOpen(true)}>
            <Bars3Icon className="w-6 h-6" />
          </button>
          <span className="font-bold">سیستم مناظره AI</span>
          <button onClick={toggleDarkMode}>
            {darkMode ? <SunIcon className="w-6 h-6" /> : <MoonIcon className="w-6 h-6" />}
          </button>
        </header>

        {/* Page content */}
        <div className="flex-1 p-4 md:p-8 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
