'use client';

/** «مدل‌ها» moved under «مدل‌ها و تنظیمات» (owner, 2026-11-15, plan item 6) — the old address keeps working. */

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function ModelsRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/settings?view=models'); }, [router]);
  return (
    <p className="p-6 text-gray-500" dir="rtl">
      «مدل‌ها» اکنون زیرِ <Link href="/settings?view=models" className="text-blue-600 underline">مدل‌ها و تنظیمات</Link> است…
    </p>
  );
}
