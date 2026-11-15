'use client';

/**
 * «پروژه‌ها و نمودارها» — owner, 2026-11-15 (plan item 3): the two pages work on the same
 * projects, so they live under one page. Their code is unchanged and lives in
 * `components/views/ProjectsView.tsx` and `components/views/DiagramsView.tsx`; this page
 * only switches between them with `?view=diagrams`. The old `/diagrams` address
 * redirects here, and `/projects?id=…` keeps working (ProjectsView reads it).
 *
 * A view is mounted the first time it is opened and then kept mounted (hidden), so
 * switching tabs never loses a half-made diagram or an open import.
 */

import { Suspense, useEffect, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import ProjectsView from '@/components/views/ProjectsView';
import DiagramsView from '@/components/views/DiagramsView';

type View = 'projects' | 'diagrams';
const TABS: { id: View; label: string; emoji: string }[] = [
  { id: 'projects', label: 'پروژه‌ها', emoji: '📁' },
  { id: 'diagrams', label: 'نمودارها', emoji: '📊' },
];

function ProjectsHub() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname() || '/projects';
  const view: View = params.get('view') === 'diagrams' ? 'diagrams' : 'projects';
  const [mounted, setMounted] = useState<Record<View, boolean>>({ projects: view === 'projects', diagrams: view === 'diagrams' });

  useEffect(() => { setMounted((m) => (m[view] ? m : { ...m, [view]: true })); }, [view]);

  const go = (v: View) => {
    const q = new URLSearchParams(params.toString());
    if (v === 'projects') q.delete('view'); else q.set('view', v);
    const s = q.toString();
    router.push(s ? `${pathname}?${s}` : pathname);
  };

  return (
    <div dir="rtl">
      <div className="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-700" role="tablist"
        data-report-section="projects-hub-tabs" data-report-section-label="تب‌های پروژه‌ها و نمودارها">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={view === t.id} onClick={() => go(t.id)}
            className={`px-4 py-2 -mb-px border-b-2 font-medium transition ${view === t.id
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}`}>
            {t.emoji} {t.label}
          </button>
        ))}
      </div>
      {mounted.projects && <div hidden={view !== 'projects'}><ProjectsView /></div>}
      {mounted.diagrams && <div hidden={view !== 'diagrams'}><DiagramsView /></div>}
    </div>
  );
}

export default function ProjectsPage() {
  return (
    <Suspense fallback={<p className="p-6 text-gray-500" dir="rtl">در حال بارگذاری...</p>}>
      <ProjectsHub />
    </Suspense>
  );
}
