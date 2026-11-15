'use client';

/**
 * «مدل‌ها و تنظیمات» — owner, 2026-11-15 (plan item 6): the two pages are merged with
 * nothing removed. Their code lives unchanged in `components/views/SettingsView.tsx`
 * (keys, deploy, config, limits, Render logs, notifications/Telegram, AI usage — each
 * reachable with `?tab=`) and `components/views/ModelsView.tsx` (`?view=models`).
 * The old `/models` address redirects here; every «به تنظیمات بروید» link still lands
 * on the keys tab.
 */

import ViewHub from '@/components/ViewHub';
import SettingsView from '@/components/views/SettingsView';
import ModelsView from '@/components/views/ModelsView';

export default function SettingsPage() {
  return (
    <ViewHub section="settings-hub" views={[
      { id: 'settings', label: 'کلیدها و تنظیمات', emoji: '⚙️', render: () => <SettingsView /> },
      { id: 'models', label: 'مدل‌ها', emoji: '🧠', render: () => <ModelsView /> },
    ]} />
  );
}
