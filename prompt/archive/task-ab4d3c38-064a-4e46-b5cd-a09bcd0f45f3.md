---
task_id: ab4d3c38-064a-4e46-b5cd-a09bcd0f45f3
title: 'Anti-pattern: Over-engineering'
type: bug_fix
priority: high
execution_priority: 100
status: awaiting_review
external_status: pending
verification_status: partial
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T06:05:54.644793+00:00'
updated_at: '2026-06-02T17:43:03.436988+00:00'
archived: true
archived_at: '2026-05-18T04:18:45.154698+00:00'
tags:
- merged
target_files:
- backend/app/services/notification_service.py
---

# Anti-pattern: Over-engineering

## Raw Idea

وجود PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES در یک سرویس notification که قرار است فقط ارسال اعلان را مدیریت کند، نشان‌دهنده over-engineering است. این منطق UI/UX ربات تلگرام (مدیریت keyboard و alias) باید در یک سرویس مجزا مثل telegram_bot_service.py باشد، نه در سرویس نوتیفیکیشن. این باعث وابستگی نادرست و افزایش پیچیدگی می‌شود.

📁 file: backend/app/services/notification_service.py (line 88)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.
---
[scan #2 at 2026-05-15T06:05:58.004242+00:00]
در useEffect دوم، برای بازیابی انتخاب مدل از localStorage، کد هم در mount و هم بعد از loadData اجرا می‌شود. این باعث دو بار اجرای منطق مشابه و احتمال inconsistency می‌شود.

📁 file: frontend/src/app/debate/page.tsx (line 60)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.
---
[scan #3 at 2026-05-15T06:37:54.439719+00:00]
WatchedProject شامل 30+ فیلد است که بسیاری از آن‌ها (مانند verify_mode, stale_detection_enabled, delta_analysis_enabled) هرگز در کد فعلی استفاده نمی‌شوند. این پیچیدگی بی‌مورد برای یک سرویس JSON-based است.

📁 file: backend/app/services/oversight_service.py (line 120)

🎯 پیشنهاد: این الگو معمولاً منطق
---
[scan #4 at 2026-05-15T06:37:54.587801+00:00]
پیاده‌سازی کامل یک سرویس نوتیفیکیشن با 12+ نوع رویداد، کیبوردهای مختلف، و تنظیمات runtime-mutable در یک فایل واحد. این حجم از پیچیدگی در یک فایل منجر به نقض Single Responsibility Principle می‌شود. منطق مدیریت رویدادها، ذخیره‌سازی، ارتباط با تلگرام، ایمیل، و مدیریت کیبوردها همگی در یک کلاس/ماژول قرار
---
[scan #5 at 2026-05-15T07:39:32.962586+00:00]
متد `get_available_models` هر بار که فراخوانی می‌شود، یک session دیتابیس جدید ایجاد می‌کند و تمام تنظیمات مدل‌ها را از دیتابیس می‌خواند. این کار برای هر درخواست کاربر بسیار پرهزینه است و می‌تواند باعث کاهش performance شود. بهتر است این داده‌ها کش (cache) شوند و فقط در صورت تغییر به‌روزرسانی شوند.

📁
---
[scan #6 at 2026-05-15T10:32:36.144689+00:00]
در متد `get_available_models`، یک session دیتابیس به صورت دستی ایجاد و بسته می‌شود (`SessionLocal()` و `db.close()`). این کار باعث تکرار کد و افزایش پیچیدگی می‌شود. بهتر است از یک context manager سراسری (مانند `get_db` که در کامنت اشاره شده) استفاده شود تا مدیریت session یکپارچه باشد.

📁 file: backe

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
Anti-pattern: Over-engineering

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:88`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این فایل `notification_service.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
وجود PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES در یک سرویس notification که قرار است فقط ارسال اعلان را مدیریت کند، نشان‌دهنده over-engineering است. این منطق UI/UX ربات تلگرام (مدیریت keyboard و alias) باید در یک سرویس مجزا مثل telegram_bot_service.py باشد، نه در سرویس نوتیفیکیشن. این باعث وابستگی نادرست و افزایش پیچیدگی می‌شود.

📁 file: backend/app/services/notification_service.py (line 88)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/notification_service.py`
- `ruff check backend/app/services/notification_service.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. ریشه anti-pattern تشخیص داده شد _(verify: static)_
2. یا کد اصلاح شد، یا کامنت توجیهی اضافه شد _(verify: static)_
3. تست edge case نوشته شد _(verify: backend_test)_
