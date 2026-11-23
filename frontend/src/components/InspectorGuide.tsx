'use client';

/**
 * PM-INS-0031 — «از این‌جا شروع کن» + one plain Persian sentence for every inspector button, always visible
 * (the owner: «توضیحی ندارد که بفهمم هر دکمه چه می‌کند»). Collapsible, but open by default; the choice is remembered.
 */

import { useEffect, useState } from 'react';

const STEPS: [string, string][] = [
  ['۱. روشن', 'دکمهٔ گردِ پاور زیرِ اسکرین را بزنید تا سایتِ پروژه در اسکرین بیاید.'],
  ['۲. ورود', '«🔐 ورودِ یک‌باره» را بزنید، در پنجرهٔ زنده با حسابِ خودتان وارد شوید و «ذخیره» بزنید — فقط یک بار برای هر سایت. اگر گوگل گفت «این مرورگر امن نیست»: «📥 از کرومِ من».'],
  ['۳. بپرس / بررسی کن', 'در چتِ کنار بنویسید چه می‌خواهید؛ یا 📸 عکس و 🖱 عامل را بزنید تا صفحه‌های داخلی دیده و آزموده شوند.'],
];

export const BUTTONS: [string, string][] = [
  ['🔐 ورودِ یک‌باره', 'سایتِ پروژه را روی سرور باز می‌کند تا یک بار واردش شوید؛ بعد 📸 و عامل با همان حساب کار می‌کنند. وقتی صفحه «ورود» خواست بزنید.'],
  ['📥 از کرومِ من', 'وقتی گوگل در مرورگرِ سرور ورود را رد می‌کند: پنجره‌ای با ۴ گامِ ساده باز می‌شود (نوارِ بوک‌مارک را نمایان کن، دکمه را رویش بکش، سایت را باز کن، یک کلیک) و خودش «✅ ورود رسید» را نشان می‌دهد.'],
  ['📸 عکس', 'از صفحه‌ای که در نوارِ نشانی است عکسِ واقعی می‌گیرد و به چت می‌دهد. وقتی می‌خواهید هوش مصنوعی صفحه را «ببیند».'],
  ['🖱 عامل', 'یک کار را به زبانِ ساده بدهید («برو به تنظیمات و ذخیره را بزن»)؛ مرورگرِ سرور گام‌به‌گام انجامش می‌دهد و گزارش می‌دهد.'],
  ['🎬 ضبط', 'کارهایی که در پیش‌نمایش می‌کنید با لاگ‌ها ضبط می‌شود و یک پرامپتِ آماده به چت می‌دهد. وقتی باگی را می‌خواهید نشان دهید.'],
  ['📋 کنسول', 'لاگ‌ها و خطاهای جاوااسکریپتِ داخلِ پیش‌نمایش را نشان می‌دهد (نیاز به Bridge و «WS: متصل»).'],
  ['⛶ / ↗', '⛶ اسکرین را تمام‌صفحه می‌کند (صفحهٔ باریک)؛ ↗ سایت را در پنجرهٔ جدا باز می‌کند.'],
  ['🩹 خوداصلاح', 'وقتی روشن است، هر خطای تازهٔ پیش‌نمایش خودکار تحلیل و یک اصلاحِ پیشنهادی در چت می‌آید (اعمال فقط با تأییدِ شما).'],
  ['▶️ رصدِ لاگ', 'خطاهای بک‌اندِ Render را همین‌جا زنده دنبال می‌کند؛ چیزی در ریپو عوض نمی‌شود.'],
  ['➕ نصبِ Bridge', 'یک اسکریپتِ کوچک در ریپوی پروژه commit می‌کند تا کلیک/تایپ و کنسولِ پیش‌نمایش به چت برسد. یک بار برای هر پروژه.'],
  ['🩺', 'وقتی پاسخِ چت نیامد، وضعیتِ تشخیصیِ اسکن را نشان می‌دهد.'],
  ['📥', 'گفت‌وگوی فعلی را می‌بندد و بایگانی می‌کند تا از نو شروع کنید.'],
  ['📋 (بالای چت)', 'گفت‌وگوهای بایگانی‌شدهٔ قبلی را نشان می‌دهد.'],
  ['⚙️', 'انتخابِ مدلِ هوش مصنوعی و موتورِ پردازش برای چت.'],
];

export default function InspectorGuide() {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    try { if (localStorage.getItem('pm.inspectorGuide') === '0') setOpen(false); } catch { /* ignore */ }
  }, []);
  const toggle = () => {
    setOpen((v) => {
      try { localStorage.setItem('pm.inspectorGuide', v ? '0' : '1'); } catch { /* ignore */ }
      return !v;
    });
  };
  return (
    <div className="mb-3 rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700 text-sm" dir="rtl">
      <button onClick={toggle} className="w-full text-right px-3 py-2 font-bold text-amber-900 dark:text-amber-200">
        🧭 از این‌جا شروع کن {open ? '▾' : '▸ (راهنما)'}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          <ol className="grid gap-2 sm:grid-cols-3">
            {STEPS.map(([t, d]) => (
              <li key={t} className="rounded-lg bg-white/70 dark:bg-gray-800/60 p-2">
                <b className="text-amber-800 dark:text-amber-300">{t}</b>
                <div className="text-xs text-gray-700 dark:text-gray-300 mt-0.5 leading-5">{d}</div>
              </li>
            ))}
          </ol>
          <div className="grid gap-x-4 gap-y-1 sm:grid-cols-2 text-xs text-gray-700 dark:text-gray-300 leading-5">
            {BUTTONS.map(([b, d]) => (
              <div key={b}><b className="text-gray-900 dark:text-gray-100 whitespace-nowrap">{b}</b> — {d}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
