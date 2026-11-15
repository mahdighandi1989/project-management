'use client';

/**
 * A page made of several whole views that used to be separate pages (owner, 2026-11-15:
 * «پروژه‌ها + نمودارها», «مدل‌ها + تنظیمات»). The views' code is unchanged; this only
 * switches between them with `?view=<id>` (the first view is the default and has no
 * param). A view is mounted the first time it is opened and then kept mounted (hidden),
 * so switching never loses unsaved input or a running job.
 */

import { ReactNode, Suspense, useEffect, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

export interface HubView {
  id: string;
  label: string;
  emoji: string;
  render: () => ReactNode;
}

function Hub({ views, section }: { views: HubView[]; section: string }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname() || '/';
  const wanted = params.get('view');
  const view = views.find((v) => v.id === wanted)?.id || views[0].id;
  const [mounted, setMounted] = useState<Record<string, boolean>>({ [view]: true });

  useEffect(() => { setMounted((m) => (m[view] ? m : { ...m, [view]: true })); }, [view]);

  const go = (id: string) => {
    const q = new URLSearchParams(params.toString());
    if (id === views[0].id) q.delete('view'); else q.set('view', id);
    q.delete('tab'); // a tab inside one view means nothing in another
    const s = q.toString();
    router.push(s ? `${pathname}?${s}` : pathname);
  };

  return (
    <div dir="rtl">
      <div className="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-700 overflow-x-auto" role="tablist"
        data-report-section={`${section}-tabs`} data-report-section-label="تب‌های بالای صفحه">
        {views.map((t) => (
          <button key={t.id} role="tab" aria-selected={view === t.id} onClick={() => go(t.id)}
            className={`px-4 py-2 -mb-px border-b-2 font-medium whitespace-nowrap transition ${view === t.id
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}`}>
            {t.emoji} {t.label}
          </button>
        ))}
      </div>
      {views.map((v) => (mounted[v.id] ? <div key={v.id} hidden={view !== v.id}>{v.render()}</div> : null))}
    </div>
  );
}

export default function ViewHub(props: { views: HubView[]; section: string }) {
  return (
    <Suspense fallback={<p className="p-6 text-gray-500" dir="rtl">در حال بارگذاری...</p>}>
      <Hub {...props} />
    </Suspense>
  );
}
