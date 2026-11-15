/**
 * The ONE registry of the app's screens (owner, 2026-11-15 — plan items 2, 9, 10).
 *
 * Everything that lists pages reads it, so nothing falls out of step when a page is
 * added, renamed or moved:
 *   - the side menu (`components/Layout.tsx`)          ← entries with `menu: true`, in this order
 *   - the home page cards (`app/page.tsx`)              ← entries with `home: true`
 *   - the help circle's page list (`components/help`)   ← every entry
 *   - «دستیار» (the roaming chat) — sent to the backend with each question
 *
 * `scripts/docs_gate.py` refuses to ship when a folder in `frontend/src/app` with a
 * `page.tsx` has no entry here — so a new page cannot ship unknown to the menu, the
 * home page, the help circle and the assistant.
 */

export type SiteGroup = 'main' | 'tools' | 'system' | 'hidden';

export interface SiteEntry {
  href: string;
  label: string;
  emoji: string;
  /** one line: what the page is for (home card, assistant, help) */
  desc: string;
  group: SiteGroup;
  menu?: boolean;
  home?: boolean;
  /** heroicon name used by the side menu (mapped in Layout.tsx) */
  icon?: string;
  /** page tabs, `?tab=` keys → label (the assistant links them) */
  tabs?: Record<string, string>;
  /** where an old address now lives (kept working, see the page itself) */
  movedTo?: string;
}

export const SITE: SiteEntry[] = [
  { href: '/', label: 'خانه', emoji: '🏠', desc: 'نمای کلیِ برنامه، وضعیتِ مدل‌ها و دسترسیِ سریع به همهٔ بخش‌ها', group: 'main', menu: true, icon: 'home' },
  { href: '/projects', label: 'پروژه‌ها', emoji: '📁', desc: 'پروژه‌ها، واردکردن از GitHub، تب‌های هر پروژه (از جمله «بازرس ویژه»)', group: 'main', menu: true, home: true, icon: 'rocket' },
  { href: '/oversight', label: 'اتاق فرمان', emoji: '🛰️', desc: 'پایشِ مخازنِ GitHub با AI: اسکنِ عمیق، ایده، تسک، اجرا، تأیید و گزارش', group: 'main', menu: true, home: true, icon: 'eye',
    tabs: { watched: 'پروژه‌های تحتِ پایش', tasks: 'تسک‌ها', reports: 'گزارش‌ها', ideas: 'ایده‌ها' } },
  { href: '/inspection', label: 'نظارت و سرکشی', emoji: '📋', desc: 'برگه‌های ایراد/پیشنهادِ مالک روی هر صفحه و پاسخِ ناظرِ خودکار', group: 'main', menu: true, home: true, icon: 'clipboard' },
  { href: '/creator', label: 'موتور خالق', emoji: '🚀', desc: 'ساختِ پروژهٔ تازه از یک ایده با AI', group: 'tools', menu: true, home: true, icon: 'command' },
  { href: '/knowledge-center', label: 'مرکز دانش', emoji: '📚', desc: 'تجربه‌های قابلِ استفادهٔ مجدد از همهٔ پروژه‌ها', group: 'tools', menu: true, home: true, icon: 'book' },
  { href: '/diagrams', label: 'نمودارها', emoji: '📊', desc: 'تولیدِ نمودار از پروژه‌ها', group: 'tools', menu: true, home: true, icon: 'chart' },
  { href: '/archive', label: 'آرشیو', emoji: '📦', desc: 'تاریخچه: گفت‌وگوهای دستیار، فایل‌ها، پروژه‌ها و مناظره‌های قدیمی', group: 'tools', menu: true, home: true, icon: 'archive' },
  { href: '/models', label: 'مدل‌ها', emoji: '🧠', desc: 'مدل‌های AI: فعال/غیرفعال، اولویت، تستِ توانایی', group: 'system', menu: true, home: true, icon: 'cpu' },
  { href: '/settings', label: 'تنظیمات', emoji: '⚙️', desc: 'کلیدهای API، توکن‌ها، اعلان‌ها و تلگرام، محدودیت‌ها', group: 'system', menu: true, home: true, icon: 'cog' },
  // reachable, not in the menu
  { href: '/analysis', label: 'تحلیل پروژه', emoji: '🔍', desc: 'بررسیِ سلامتِ پروژه و پروفایلِ AI (در حالِ مهاجرت به اتاق فرمان)', group: 'hidden', home: true },
  { href: '/model-profiles', label: 'پروفایلِ مدل‌ها', emoji: '🧪', desc: 'پروفایل و رتبه‌بندیِ توانایی‌های مدل‌ها', group: 'hidden' },
  { href: '/project/[id]', label: 'پروژهٔ موتور خالق', emoji: '🧩', desc: 'جزئیاتِ پروژه‌ای که موتور خالق ساخته', group: 'hidden' },
  { href: '/projects/[id]', label: 'یک پروژه', emoji: '🗂️', desc: 'تب‌های پروژه: فایل‌ها، لاگ‌ها، بازرس ویژه، حافظه و …', group: 'hidden' },
  { href: '/debate', label: 'مناظره (بایگانی)', emoji: '🥊', desc: 'صفحهٔ قدیمیِ مناظرهٔ چندمدلی — جایش را «دستیار» گرفت؛ از آرشیو در دسترس است', group: 'hidden' },
  { href: '/users', label: 'کاربران', emoji: '👥', desc: 'تأیید و مدیریتِ کاربرانِ واردشده با گوگل (فقط مالک)', group: 'hidden' },
];

/** Entries for the side menu, in order. */
export const MENU = SITE.filter((s) => s.menu);

/** The entry for a pathname — the longest matching href (dynamic `[id]` segments match anything). */
export function entryFor(pathname: string): SiteEntry | undefined {
  let best: SiteEntry | undefined;
  for (const s of SITE) {
    const re = new RegExp('^' + s.href.replace(/\[[^\]]+\]/g, '[^/]+').replace(/\/$/, '') + '(/|$)');
    const hit = s.href === '/' ? pathname === '/' : re.test(pathname);
    if (hit && (!best || s.href.length > best.href.length)) best = s;
  }
  return best;
}

/** The compact form sent to «دستیار». */
export function siteMapForAssistant() {
  return SITE.map((s) => ({
    href: s.href,
    label: s.label,
    desc: s.desc + (s.tabs ? ` — تب‌ها: ${Object.entries(s.tabs).map(([k, v]) => `${v} (?tab=${k})`).join('، ')}` : '') + (s.menu ? '' : ' [خارج از منو]'),
  }));
}
