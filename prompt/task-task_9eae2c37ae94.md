---
task_id: task_9eae2c37ae94
title: رفع Duplicate Logic و Anti-pattern در مدیریت API Key و main.py
type: other
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:19:54.863009+00:00'
updated_at: '2026-05-20T04:28:24.238859+00:00'
tags:
- consolidated
- post_verify_merge
---

# رفع Duplicate Logic و Anti-pattern در مدیریت API Key و main.py

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به duplicate logic در مدیریت API Key و anti-pattern در main.py که به فایل main.py مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به مدیریت API Key و Anti-pattern در main.py
💎 estimated_difficulty: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: a585b41a-0175-423f-9533-42180f1e9c84
  عنوان اصلی: تکراری بودن منطق مدیریت API Key در settings.py و main.py
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/main.py

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint"], "files_hint": ["backend/app/main.py", "backend/app/api/routes/settings.py"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore"], "files_hint": ["backend/app/main.py", "backend/app/api/routes/settings.py"]}]

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
تکراری بودن منطق مدیریت API Key در settings.py و main.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:227-271` — `load_api_keys_from_database`
  ```python
  async def load_api_keys_from_database():
      ...
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
منطق بارگذاری API keys از دیتابیس و environment در دو مکان مجزا پیاده شده است: تابع `load_api_keys_from_database` در `backend/app/main.py` (خطوط 227-271) و endpoint `PUT /api-keys` در `backend/app/api/routes/settings.py` (خطوط 165-241). هر دو تابع تقریباً یکسان عمل می‌کنند: کلیدها را از دیتابیس می‌خوانند و در environment تنظیم می‌کنند. این تکرار باعث می‌شود تغییر در یکی، دیگری را ناسازگار کند و باگ‌های احتمالی افزایش یابد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. یک تابع واحد به نام `load_api_keys_to_env` در `backend/app/core/config.py` ایجاد کن و آن را هم در startup و هم در endpoint settings فراخوانی کن. منطق تکراری را از هر دو فایل حذف کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 490a990b-17a0-4a8b-9a6b-6b69931df53d
  عنوان اصلی: Anti-pattern: conditional-inconsistency
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/main.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["get_upload_session_service", "OVERSIGHT_AVAILABLE"], "files_hint": ["backend/app/main.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["OVERSIGHT_AVAILABLE", "conditional-inconsistency"], "files_hint": ["backend/app/main.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_cleanup_orphan_uploads.py::test_conditional_inconsistency_edge_case", "timeout_seconds": 60}]

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
Anti-pattern: conditional-inconsistency

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:82`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در بخش cleanup orphan uploads، از get_upload_session_service استفاده شده اما در try/except فقط warning گرفته شده. اگر این سرویس وابستگی به oversight داشته باشد و oversight در دسترس نباشد (OVERSIGHT_AVAILABLE=False)، این کد fail می‌شود ولی هیچ چکی روی OVERSIGHT_AVAILABLE انجام نشده است.

📁 file: backend/app/main.py (line 82)

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
- `python -m py_compile backend/app/main.py`
- `ruff check backend/app/main.py`
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
- در commit message: `merged-from: a585b41a-0175-423f-9533-42180f1e9c84, 490a990b-17a0-4a8b-9a6b-6b69931df53d`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به duplicate logic در مدیریت API Key و anti-pattern در main.py که به فایل main.py مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به مدیریت API Key و Anti-pattern در main.py
💎 estimated_difficulty: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: a585b41a-0175-423f-9533-42180f1e9c84
  عنوان اصلی: تکراری بودن منطق مدیریت API Key در settings.py و main.py
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/main.py

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint"], "files_hint": ["backend/app/main.py", "backend/app/api/routes/settings.py"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore"], "files_hint": ["backend/app/main.py", "backend/app/api/routes/settings.py"]}]

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
تکراری بودن منطق مدیریت API Key در settings.py و main.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:227-271` — `load_api_keys_from_database`
  ```python
  async def load_api_keys_from_database():
      ...
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
منطق بارگذاری API keys از دیتابیس و environment در دو مکان مجزا پیاده شده است: تابع `load_api_keys_from_database` در `backend/app/main.py` (خطوط 227-271) و endpoint `PUT /api-keys` در `backend/app/api/routes/settings.py` (خطوط 165-241). هر دو تابع تقریباً یکسان عمل می‌کنند: کلیدها را از دیتابیس می‌خوانند و در environment تنظیم می‌کنند. این تکرار باعث می‌شود تغییر در یکی، دیگری را ناسازگار کند و باگ‌های احتمالی افزایش یابد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. یک تابع واحد به نام `load_api_keys_to_env` در `backend/app/core/config.py` ایجاد کن و آن را هم در startup و هم در endpoint settings فراخوانی کن. منطق تکراری را از هر دو فایل حذف کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 490a990b-17a0-4a8b-9a6b-6b69931df53d
  عنوان اصلی: Anti-pattern: conditional-inconsistency
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/main.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["get_upload_session_service", "OVERSIGHT_AVAILABLE"], "files_hint": ["backend/app/main.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["OVERSIGHT_AVAILABLE", "conditional-inconsistency"], "files_hint": ["backend/app/main.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_cleanup_orphan_uploads.py::test_conditional_inconsistency_edge_case", "timeout_seconds": 60}]

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
Anti-pattern: conditional-inconsistency

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:82`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در بخش cleanup orphan uploads، از get_upload_session_service استفاده شده اما در try/except فقط warning گرفته شده. اگر این سرویس وابستگی به oversight داشته باشد و oversight در دسترس نباشد (OVERSIGHT_AVAILABLE=False)، این کد fail می‌شود ولی هیچ چکی روی OVERSIGHT_AVAILABLE انجام نشده است.

📁 file: backend/app/main.py (line 82)

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
- `python -m py_compile backend/app/main.py`
- `ruff check backend/app/main.py`
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
- در commit message: `merged-from: a585b41a-0175-423f-9533-42180f1e9c84, 490a990b-17a0-4a8b-9a6b-6b69931df53d`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. اعمال تغییر بدون شکستن تست‌های موجود _(verify: backend_test)_
2. linter بدون warning عبور می‌کند _(verify: static)_
3. type-check موفق است _(verify: static)_
4. ریشه anti-pattern تشخیص داده شد _(verify: static)_
5. یا کد اصلاح شد، یا کامنت توجیهی اضافه شد _(verify: static)_
6. تست edge case نوشته شد _(verify: backend_test)_

## Task Steps

### Step 1: بررسی و تحلیل کد فعلی برای شناسایی duplicate logic در مدیریت API Key
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل‌های backend/app/main.py و backend/app/api/routes/settings.py برای یافتن منطق تکراری بارگذاری API Keys از دیتابیس و تنظیم در environment است. همچنین بررسی تابع `load_api_keys_from_database` در main.py و endpoint `PUT /api-keys` در settings.py. خروجی این مرحله یک گزارش از بخش‌های تکراری و نحوه ادغام آن‌هاست. هیچ تغییری در کد در این مرحله انجام نمی‌شود.
**Excerpt:**
```
منطق بارگذاری API keys از دیتابیس و environment در دو مکان مجزا پیاده شده است: تابع `load_api_keys_from_database` در `backend/app/main.py` (خطوط 227-271) و endpoint `PUT /api-keys` در `backend/app/api/routes/settings.py` (خطوط 165-241). هر دو تابع تقریباً یکسان عمل می‌کنند: کلیدها را از دیتابیس می‌خوانند و در environment تنظیم می‌کنند.
```

### Step 2: ایجاد تابع واحد `load_api_keys_to_env` در `backend/app/core/config.py`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک تابع جدید به نام `load_api_keys_to_env` در فایل `backend/app/core/config.py` است. این تابع باید منطق مشترک بارگذاری API Keys از دیتابیس و تنظیم آن‌ها در environment variables را شامل شود. تابع باید async باشد و از session دیتابیس استفاده کند. همچنین باید از type hints و docstring مناسب برخوردار باشد. خارج از این مرحله: تغییر در main.py یا settings.py انجام نمی‌شود.
**Excerpt:**
```
یک تابع واحد به نام `load_api_keys_to_env` در `backend/app/core/config.py` ایجاد کن و آن را هم در startup و هم در endpoint settings فراخوانی کن. منطق تکراری را از هر دو فایل حذف کن.
```

### Step 3: جایگزینی منطق تکراری در `backend/app/main.py` با فراخوانی `load_api_keys_to_env`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی بدنه تابع `load_api_keys_from_database` در `backend/app/main.py` با یک فراخوانی ساده به تابع `load_api_keys_to_env` از `backend/app/core/config.py` است. همچنین باید import مربوطه اضافه شود. خارج از این مرحله: تغییر در settings.py انجام نمی‌شود.
**Excerpt:**
```
منطق بارگذاری API keys از دیتابیس و environment در دو مکان مجزا پیاده شده است: تابع `load_api_keys_from_database` در `backend/app/main.py` (خطوط 227-271) و endpoint `PUT /api-keys` در `backend/app/api/routes/settings.py` (خطوط 165-241).
```

### Step 4: جایگزینی منطق تکراری در `backend/app/api/routes/settings.py` با فراخوانی `load_api_keys_to_env`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی منطق تکراری در endpoint `PUT /api-keys` در `backend/app/api/routes/settings.py` با یک فراخوانی به تابع `load_api_keys_to_env` از `backend/app/core/config.py` است. همچنین باید import مربوطه اضافه شود. خارج از این مرحله: تغییر در main.py انجام نمی‌شود.
**Excerpt:**
```
منطق بارگذاری API keys از دیتابیس و environment در دو مکان مجزا پیاده شده است: تابع `load_api_keys_from_database` در `backend/app/main.py` (خطوط 227-271) و endpoint `PUT /api-keys` در `backend/app/api/routes/settings.py` (خطوط 165-241).
```

### Step 5: بررسی و تحلیل anti-pattern `conditional-inconsistency` در `backend/app/main.py`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی دقیق خط 82 فایل `backend/app/main.py` و منطق مربوط به `get_upload_session_service` و `OVERSIGHT_AVAILABLE` است. هدف شناسایی ریشه anti-pattern و تصمیم‌گیری در مورد اصلاح یا افزودن کامنت توجیهی است. هیچ تغییری در کد در این مرحله انجام نمی‌شود.
**Excerpt:**
```
در بخش cleanup orphan uploads، از get_upload_session_service استفاده شده اما در try/except فقط warning گرفته شده. اگر این سرویس وابستگی به oversight داشته باشد و oversight در دسترس نباشد (OVERSIGHT_AVAILABLE=False)، این کد fail می‌شود ولی هیچ چکی روی OVERSIGHT_AVAILABLE انجام نشده است.
```

### Step 6: اصلاح anti-pattern `conditional-inconsistency` در `backend/app/main.py`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح کد در خط 82 فایل `backend/app/main.py` است. بسته به تحلیل مرحله قبل، یا یک guard condition برای بررسی `OVERSIGHT_AVAILABLE` اضافه می‌شود، یا یک کامنت توجیهی برای توضیح دلیل عدم وجود چک اضافه می‌شود. خارج از این مرحله: تغییر در فایل‌های دیگر انجام نمی‌شود.
**Excerpt:**
```
ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["get_upload_session_service", "OVERSIGHT_AVAILABLE"], "files_hint": ["backend/app/main.py"]}] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["OVERSIGHT_AVAILABLE", "conditional-inconsistency"], "files_hint": ["backend/app/main.py"]}]
```

### Step 7: نوشتن تست edge case برای anti-pattern `conditional-inconsistency`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن یک تست جدید در فایل `tests/test_cleanup_orphan_uploads.py` با نام `test_conditional_inconsistency_edge_case` است. این تست باید سناریوی عدم وجود `OVERSIGHT_AVAILABLE` را شبیه‌سازی کند و اطمینان حاصل کند که کد به درستی رفتار می‌کند (fail نمی‌شود). خارج از این مرحله: تغییر در فایل‌های اصلی برنامه انجام نمی‌شود.
**Excerpt:**
```
تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_cleanup_orphan_uploads.py::test_conditional_inconsistency_edge_case", "timeout_seconds": 60}]
```

### Step 8: اجرای تست‌های موجود و اطمینان از عدم شکست
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های موجود با دستور `pytest` است. هدف اطمینان از این است که تغییرات اعمال شده در مراحل قبل هیچ تستی را نشکسته است. خارج از این مرحله: هیچ تغییری در کد انجام نمی‌شود.
**Excerpt:**
```
اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
```

### Step 9: اجرای linter و اطمینان از عدم وجود warning
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای linter (مانند flake8 یا pylint) بر روی فایل‌های تغییر یافته (`backend/app/main.py` و `backend/app/api/routes/settings.py`) است. هدف اطمینان از این است که کد از نظر linting بدون مشکل است. خارج از این مرحله: هیچ تغییری در کد انجام نمی‌شود.
**Excerpt:**
```
linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint"], "files_hint": ["backend/app/main.py", "backend/app/api/routes/settings.py"]}]
```

### Step 10: اجرای type-checker و اطمینان از موفقیت آن
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای type-checker (مانند mypy) بر روی فایل‌های تغییر یافته (`backend/app/main.py` و `backend/app/api/routes/settings.py`) است. هدف اطمینان از این است که type hints به درستی رعایت شده‌اند. خارج از این مرحله: هیچ تغییری در کد انجام نمی‌شود.
**Excerpt:**
```
type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore"], "files_hint": ["backend/app/main.py", "backend/app/api/routes/settings.py"]}]
```
