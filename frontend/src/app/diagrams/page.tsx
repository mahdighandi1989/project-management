'use client';

/** «نمودارها» moved under «پروژه‌ها» (owner, 2026-11-15, plan item 3) — the old address keeps working. */

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function DiagramsRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/projects?view=diagrams'); }, [router]);
  return (
    <p className="p-6 text-gray-500" dir="rtl">
      «نمودارها» اکنون زیرِ <Link href="/projects?view=diagrams" className="text-blue-600 underline">پروژه‌ها</Link> است…
    </p>
  );
}
