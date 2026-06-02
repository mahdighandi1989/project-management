---
task_id: f6fa284d-ccac-4487-b56c-fbddcc10a6da
title: 'dependency بلااستفاده: Pillow (python)'
type: cleanup
priority: medium
execution_priority: 3300
status: awaiting_review
external_status: pending
verification_status: partial
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-17T08:43:37.735746+00:00'
updated_at: '2026-06-02T17:52:48.810361+00:00'
---

# dependency بلااستفاده: Pillow (python)

## Raw Idea

## 📋 شرح
package `Pillow` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `Pillow`
- زبان: `python`
- علت: in requirements but no 'import pillow' or 'from pillow' found
---
[scan #2 at 2026-05-17T08:43:38.085723+00:00]
## 📋 شرح
package `aiosqlite` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `aiosqlite`
- زبان: `python`
- علت: in requiremen
---
[scan #3 at 2026-05-17T08:43:38.246050+00:00]
## 📋 شرح
package `black` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `black`
- زبان: `python`
- علت: in requirements but n
---
[scan #4 at 2026-05-17T08:43:38.413635+00:00]
## 📋 شرح
package `orjson` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `orjson`
- زبان: `python`
- علت: in requirements but
---
[scan #5 at 2026-05-17T08:43:38.576028+00:00]
## 📋 شرح
package `passlib` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `passlib`
- زبان: `python`
- علت: in requirements b
---
[scan #6 at 2026-05-17T08:43:38.740552+00:00]
## 📋 شرح
package `pydub` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `pydub`
- زبان: `python`
- علت: in requirements but n

## Prompt

## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در
  repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های
  مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط
  موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که
  چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را
  مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر
  است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه
  باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در
  commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی
  هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.

---


## 🎯 هدف (خلاصه ساختاریافته)
dependency بلااستفاده: Pillow (python)

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
package `Pillow` در `` declare شده ولی در هیچ import کدبیس مصرف نمی‌شود.

## 🤔 چرا مهم است
dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface بیشتر برای vulnerabilities، (۳) supply chain risk.

## 🔍 جزئیات
- نام package: `Pillow`
- زبان: `python`
- علت: in requirements but no 'import pillow' or 'from pillow' found

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] `Pillow` در هیچ direct import مصرف نمی‌شود + هیچ transitive dep ای آن را require نمی‌کند
- [ ] package از manifest حذف شد + lockfile به‌روز
- [ ] build/test/CI همچنان عبور می‌کند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: `npm/pip list --depth=0` و grep import روی `Pillow`.
گام ۲: اگر transitive dep ای دیگری به این نیاز دارد، نگه دار.
گام ۳: در غیر این صورت، uninstall + از `package.json`/`requirements.txt` حذف کن.
گام ۴: lockfile (`package-lock.json`/`poetry.lock`) refresh کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف dependency که peer dependency دیگری است، خاموش break می‌کند. حتماً build کامل + test کامل بعد از حذف اجرا کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: medium
- تخمین زمان: medium

## Acceptance Criteria

1. `Pillow` در هیچ direct import مصرف نمی‌شود + هیچ transitive dep ای آن را require نمی‌کند _(verify: static)_
2. package از manifest حذف شد + lockfile به‌روز _(verify: static)_
3. build/test/CI همچنان عبور می‌کند _(verify: backend_test)_
