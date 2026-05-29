---
task_id: 68e7fb2a-a006-4a4d-acbb-0572cbc4629c
title: 'فیلد بلااستفاده: Capability.optional_capabilities'
type: cleanup
priority: low
execution_priority: 100
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T06:07:26.167864+00:00'
updated_at: '2026-05-29T20:11:53.904671+00:00'
archived: true
archived_at: '2026-05-18T04:24:08.813357+00:00'
tags:
- merged
target_files:
- backend/app/services/capability_detector.py
---

# فیلد بلااستفاده: Capability.optional_capabilities

## Raw Idea

## 📋 شرح
فیلد `optional_capabilities` در dataclass/model `Capability` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in Capability but not read/written anywhere
---
[scan #2 at 2026-05-15T06:07:26.280761+00:00]
## 📋 شرح
فیلد `os_type` در dataclass/model `Capability` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- ع
---
[scan #3 at 2026-05-15T06:07:26.338981+00:00]
## 📋 شرح
فیلد `os_version` در dataclass/model `Capability` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات

---
[scan #4 at 2026-05-15T06:07:26.392255+00:00]
## 📋 شرح
فیلد `optional_capabilities` در dataclass/model `ProjectRequirements` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف م
---
[scan #5 at 2026-05-15T06:07:26.496022+00:00]
## 📋 شرح
فیلد `os_version` در dataclass/model `ProjectRequirements` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 
---
[scan #6 at 2026-05-15T06:07:26.603024+00:00]
## 📋 شرح
فیلد `os_version` در dataclass/model `SystemCapabilities` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍

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
فیلد بلااستفاده: Capability.optional_capabilities

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/capability_detector.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `optional_capabilities` در dataclass/model `Capability` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in Capability but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `optional_capabilities` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.optional_capabilities` + `['optional_capabilities']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/capability_detector.py`
- `ruff check backend/app/services/capability_detector.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
- تخمین زمان: medium

## Acceptance Criteria

1. تأیید شد `optional_capabilities` در هیچ reader مصرف نمی‌شود _(verify: static)_
2. یا حذف شد (با migration در صورت persist)، یا reader اضافه شد _(verify: static)_
3. تست‌های schema و serialization عبور می‌کنند _(verify: backend_test)_
