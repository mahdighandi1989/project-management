---
task_id: task_6053ef86eea5
title: رفع Anti-patternهای Notification Service و بهبود معماری آن
type: other
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:18:37.043052+00:00'
updated_at: '2026-05-20T04:28:22.394291+00:00'
tags:
- consolidated
- post_verify_merge
---

# رفع Anti-patternهای Notification Service و بهبود معماری آن

## Raw Idea

🧬 این یک تسک تلفیقی است — از 3 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به anti-patternهای notification_service.py که شامل over-engineering، broken feedback loop و AI without validation هستند.
🎯 theme: رفع Anti-patternهای مربوط به Notification Service
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 3
  id: ab4d3c38-064a-4e46-b5cd-a09bcd0f45f3
  عنوان اصلی: Anti-pattern: Over-engineering
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/notification_service.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_edge_case", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 3
  id: 2edf6110-1ae1-4e8c-98e8-b34307c65520
  عنوان اصلی: Anti-pattern: Broken feedback loop
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/notification_service.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["_write_index_state", "tmp", "replace"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["def _write_index_state", "comment.*broken feedback loop", "comment.*anti-pattern"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_write_index_state_edge_case", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: Broken feedback loop

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:104`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این فایل `notification_service.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
در خط ۱۰۴-۱۰۶، _write_index_state از یک فایل موقت (tmp) استفاده می‌کند و سپس replace می‌کند، اما اگر replace با خطا مواجه شود، فایل اصلی از بین می‌رود و state از دست می‌رود. همچنین هیچ مکانیزمی برای بازگرداندن state به مدل یا سرویس‌های دیگر وجود ندارد — outcome لاگ می‌شود ولی به جایی بازنخورده می‌شود.

📁 file: backend/app/services/notification_service.py (line 104)

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 3
  id: a9bc629a-d363-4035-8cbc-a4339c21e1c7
  عنوان اصلی: Anti-pattern: AI without validation
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/notification_service.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["os.environ.get", "TOKEN", "API_KEY", "CREDENTIALS"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["def validate_credentials", "if not .*:", "raise ValueError", "# TODO", "# NOTE"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_edge_case_invalid_credentials", "timeout_seconds": 30}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: AI without validation

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:58`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این فایل `notification_service.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
در خط ۵۸-۶۲، از os.environ.get برای خواندن متغیرهای محیطی استفاده شده، اما هیچ validation یا fallback منطقی برای credentials وجود ندارد. اگر credentials ناقص یا اشتباه باشند (مثلاً TOKEN نامعتبر)، سرویس بی‌صدا fail می‌شود و کاربر متوجه نمی‌شود.

📁 file: backend/app/services/notification_service.py (line 58)

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: ab4d3c38-064a-4e46-b5cd-a09bcd0f45f3, 2edf6110-1ae1-4e8c-98e8-b34307c65520, a9bc629a-d363-4035-8cbc-a4339c21e1c7`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 3 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به anti-patternهای notification_service.py که شامل over-engineering، broken feedback loop و AI without validation هستند.
🎯 theme: رفع Anti-patternهای مربوط به Notification Service
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 3
  id: ab4d3c38-064a-4e46-b5cd-a09bcd0f45f3
  عنوان اصلی: Anti-pattern: Over-engineering
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/notification_service.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_edge_case", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 3
  id: 2edf6110-1ae1-4e8c-98e8-b34307c65520
  عنوان اصلی: Anti-pattern: Broken feedback loop
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/notification_service.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["_write_index_state", "tmp", "replace"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["def _write_index_state", "comment.*broken feedback loop", "comment.*anti-pattern"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_write_index_state_edge_case", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: Broken feedback loop

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:104`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این فایل `notification_service.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
در خط ۱۰۴-۱۰۶، _write_index_state از یک فایل موقت (tmp) استفاده می‌کند و سپس replace می‌کند، اما اگر replace با خطا مواجه شود، فایل اصلی از بین می‌رود و state از دست می‌رود. همچنین هیچ مکانیزمی برای بازگرداندن state به مدل یا سرویس‌های دیگر وجود ندارد — outcome لاگ می‌شود ولی به جایی بازنخورده می‌شود.

📁 file: backend/app/services/notification_service.py (line 104)

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 3
  id: a9bc629a-d363-4035-8cbc-a4339c21e1c7
  عنوان اصلی: Anti-pattern: AI without validation
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/notification_service.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["os.environ.get", "TOKEN", "API_KEY", "CREDENTIALS"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["def validate_credentials", "if not .*:", "raise ValueError", "# TODO", "# NOTE"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_edge_case_invalid_credentials", "timeout_seconds": 30}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: AI without validation

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:58`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این فایل `notification_service.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
در خط ۵۸-۶۲، از os.environ.get برای خواندن متغیرهای محیطی استفاده شده، اما هیچ validation یا fallback منطقی برای credentials وجود ندارد. اگر credentials ناقص یا اشتباه باشند (مثلاً TOKEN نامعتبر)، سرویس بی‌صدا fail می‌شود و کاربر متوجه نمی‌شود.

📁 file: backend/app/services/notification_service.py (line 58)

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: ab4d3c38-064a-4e46-b5cd-a09bcd0f45f3, 2edf6110-1ae1-4e8c-98e8-b34307c65520, a9bc629a-d363-4035-8cbc-a4339c21e1c7`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. ریشه anti-pattern تشخیص داده شد _(verify: static)_
2. یا کد اصلاح شد، یا کامنت توجیهی اضافه شد _(verify: static)_
3. تست edge case نوشته شد _(verify: backend_test)_

## Task Steps

### Step 1: بررسی و مستندسازی وضعیت فعلی PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES در notification_service.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل backend/app/services/notification_service.py برای یافتن تمام ارجاعات به PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES است. باید مشخص شود که آیا این کدها واقعاً در سرویس نوتیفیکیشن وجود دارند، چه کاربردی دارند، و آیا می‌توان آن‌ها را به سرویس مجزای telegram_bot_service.py منتقل کرد یا خیر. خروجی این مرحله یک گزارش مستند از وضعیت فعلی است. خارج از این مرحله: انجام هرگونه تغییر در کد، نوشتن تست، یا جابجایی کد.
**Excerpt:**
```
وجود PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES در یک سرویس notification که قرار است فقط ارسال اعلان را مدیریت کند، نشان‌دهنده over-engineering است. این منطق UI/UX ربات تلگرام (مدیریت keyboard و alias) باید در یک سرویس مجزا مثل telegram_bot_service.py باشد، نه در سرویس نوتیفیکیشن. این باعث وابستگی نادرست و افزایش پیچیدگی می‌شود.
📁 file: backend/app/services/notification_service.py (line 88)
📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
```

### Step 2: رفع Anti-pattern Over-engineering: انتقال منطق UI/UX به سرویس مجزا یا افزودن کامنت توجیهی
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح کد در backend/app/services/notification_service.py برای رفع over-engineering است. دو گزینه وجود دارد: (1) انتقال PERSISTENT_REPLY_KEYBOARD و TEXT_ALIASES به یک سرویس مجزا (مثلاً telegram_bot_service.py) و به‌روزرسانی importها در oversight.py، یا (2) اگر به دلایل معماری امکان جابجایی نیست، افزودن کامنت توجیهی در خطوط مربوطه که دلیل وجود این کدها در سرویس نوتیفیکیشن را توضیح دهد. انتخاب بین این دو گزینه بر اساس تحلیل مرحله 1 انجام می‌شود. خارج از این مرحله: نوشتن تست edge case (مرحله بعدی).
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["PERSISTENT_REPLY_KEYBOARD", "TEXT_ALIASES"], "files_hint": ["backend/app/services/notification_service.py"]}]
🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.
```

### Step 3: نوشتن تست edge case برای Over-engineering Anti-pattern
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن یک تست واحد (unit test) در فایل tests/test_notification_service.py است که edge case مربوط به over-engineering را پوشش می‌دهد. تست باید با نام test_edge_case (یا مشابه) تعریف شود و سناریویی را测试 کند که نشان می‌دهد منطق UI/UX (PERSISTENT_REPLY_KEYBOARD یا TEXT_ALIASES) در سرویس نوتیفیکیشن باعث بروز مشکل می‌شود. خارج از این مرحله: اصلاح کد تولیدی (production code) یا نوشتن تست‌های integration.
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_edge_case", "timeout_seconds": 60}]
🧪 دستورات اعتبارسنجی:
- `python -m py_compile backend/app/services/notification_service.py`
- `ruff check backend/app/services/notification_service.py`
- `pytest -x`
```

### Step 4: بررسی و مستندسازی وضعیت فعلی Broken feedback loop در _write_index_state
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل تابع _write_index_state در backend/app/services/notification_service.py (خطوط 104-106) است. باید مشخص شود که آیا این تابع از فایل موقت (tmp) و replace استفاده می‌کند، آیا مکانیزم fallback یا rollback وجود دارد، و آیا outcome به سرویس‌های دیگر بازخورد داده می‌شود. خروجی این مرحله یک گزارش مستند از وضعیت فعلی و تحلیل ریسک است. خارج از این مرحله: انجام هرگونه تغییر در کد یا نوشتن تست.
**Excerpt:**
```
در خط ۱۰۴-۱۰۶، _write_index_state از یک فایل موقت (tmp) استفاده می‌کند و سپس replace می‌کند، اما اگر replace با خطا مواجه شود، فایل اصلی از بین می‌رود و state از دست می‌رود. همچنین هیچ مکانیزمی برای بازگرداندن state به مدل یا سرویس‌های دیگر وجود ندارد — outcome لاگ می‌شود ولی به جایی بازنخورده می‌شود.
📁 file: backend/app/services/notification_service.py (line 104)
📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["_write_index_state", "tmp", "replace"], "files_hint": ["backend/app/services/notification_service.py"]}]
```

### Step 5: رفع Anti-pattern Broken feedback loop: اصلاح _write_index_state با مکانیزم atomic write و fallback
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح تابع _write_index_state در backend/app/services/notification_service.py برای رفع Broken feedback loop است. اصلاحات شامل: (1) استفاده از مکانیزم atomic write که در صورت شکست replace، فایل اصلی را حفظ کند (مثلاً نوشتن در فایل موقت و سپس استفاده از os.replace با try/except)، (2) افزودن مکانیزم بازخورد (feedback) که outcome را به سرویس‌های دیگر (مثلاً از طریق یک callback یا event) اطلاع دهد، و (3) افزودن کامنت‌های توجیهی. خارج از این مرحله: نوشتن تست edge case (مرحله بعدی).
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["def _write_index_state", "comment.*broken feedback loop", "comment.*anti-pattern"], "files_hint": ["backend/app/services/notification_service.py"]}]
🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.
```

### Step 6: نوشتن تست edge case برای Broken feedback loop Anti-pattern
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن یک تست واحد (unit test) در فایل tests/test_notification_service.py است که edge case مربوط به Broken feedback loop را پوشش می‌دهد. تست باید با نام test_write_index_state_edge_case تعریف شود و سناریویی را تست کند که در آن replace با خطا مواجه می‌شود و بررسی می‌کند که فایل اصلی state از بین نرفته است. خارج از این مرحله: اصلاح کد تولیدی یا نوشتن تست‌های integration.
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_write_index_state_edge_case", "timeout_seconds": 60}]
🧪 دستورات اعتبارسنجی:
- `python -m py_compile backend/app/services/notification_service.py`
- `ruff check backend/app/services/notification_service.py`
- `pytest -x`
```

### Step 7: بررسی و مستندسازی وضعیت فعلی AI without validation در خواندن credentials
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل خطوط 58-62 در backend/app/services/notification_service.py است که از os.environ.get برای خواندن متغیرهای محیطی (TOKEN، API_KEY، CREDENTIALS) استفاده می‌کنند. باید مشخص شود که آیا هیچ validation یا fallback منطقی برای credentials وجود دارد یا خیر. خروجی این مرحله یک گزارش مستند از وضعیت فعلی و تحلیل ریسک است. خارج از این مرحله: انجام هرگونه تغییر در کد یا نوشتن تست.
**Excerpt:**
```
در خط ۵۸-۶۲، از os.environ.get برای خواندن متغیرهای محیطی استفاده شده، اما هیچ validation یا fallback منطقی برای credentials وجود ندارد. اگر credentials ناقص یا اشتباه باشند (مثلاً TOKEN نامعتبر)، سرویس بی‌صدا fail می‌شود و کاربر متوجه نمی‌شود.
📁 file: backend/app/services/notification_service.py (line 58)
📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["os.environ.get", "TOKEN", "API_KEY", "CREDENTIALS"], "files_hint": ["backend/app/services/notification_service.py"]}]
```

### Step 8: رفع Anti-pattern AI without validation: افزودن validation و fallback برای credentials
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح خطوط 58-62 در backend/app/services/notification_service.py برای افزودن validation و fallback منطقی برای credentials است. اصلاحات شامل: (1) افزودن یک تابع validate_credentials که بررسی می‌کند آیا credentials معتبر هستند یا خیر، (2) در صورت نامعتبر بودن credentials، raise ValueError با پیام خطای مناسب، (3) افزودن کامنت‌های توجیهی (مثلاً # TODO یا # NOTE). خارج از این مرحله: نوشتن تست edge case (مرحله بعدی).
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["def validate_credentials", "if not .*:", "raise ValueError", "# TODO", "# NOTE"], "files_hint": ["backend/app/services/notification_service.py"]}]
🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.
```

### Step 9: نوشتن تست edge case برای AI without validation Anti-pattern
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن یک تست واحد (unit test) در فایل tests/test_notification_service.py است که edge case مربوط به AI without validation را پوشش می‌دهد. تست باید با نام test_edge_case_invalid_credentials تعریف شود و سناریویی را تست کند که در آن credentials نامعتبر هستند و بررسی می‌کند که ValueError raise می‌شود. خارج از این مرحله: اصلاح کد تولیدی یا نوشتن تست‌های integration.
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_notification_service.py::test_edge_case_invalid_credentials", "timeout_seconds": 30}]
🧪 دستورات اعتبارسنجی:
- `python -m py_compile backend/app/services/notification_service.py`
- `ruff check backend/app/services/notification_service.py`
- `pytest -x`
```

### Step 10: اجرای تست‌های نهایی و بررسی linting/type-checking
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های موجود (pytest -x)، بررسی linter (ruff check) و type-checking (mypy) برای اطمینان از عدم وجود رگرشن و عبور از تمام معیارهای پذیرش است. همچنین شامل بررسی نهایی فایل‌های تغییر یافته با grep برای اطمینان از وجود تمام الگوهای مورد نیاز است. خارج از این مرحله: انجام هرگونه تغییر جدید در کد.
**Excerpt:**
```
🧪 دستورات اعتبارسنجی:
- `python -m py_compile backend/app/services/notification_service.py`
- `ruff check backend/app/services/notification_service.py`
- `pytest -x`
✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)
```
