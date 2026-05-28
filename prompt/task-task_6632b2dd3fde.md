---
task_id: task_6632b2dd3fde
title: پاکسازی فیلدهای بلااستفاده در مدل‌های داده و سرویس‌های بک‌اند
type: other
priority: low
execution_priority: 4000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:24:08.813343+00:00'
updated_at: '2026-05-20T04:28:28.635886+00:00'
tags:
- consolidated
- post_verify_merge
---

# پاکسازی فیلدهای بلااستفاده در مدل‌های داده و سرویس‌های بک‌اند

## Raw Idea

🧬 این یک تسک تلفیقی است — از 5 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 15، 16، 17، 18، 25 همگی به حذف فیلدهای بلااستفاده در مدل‌ها و سرویس‌های مختلف مربوط می‌شوند. تسک‌های 16 و 18 partial هستند و با not_doneهای این خوشه هم‌موضوع هستند.
🎯 theme: پاکسازی فیلدهای بلااستفاده در مدل‌ها و سرویس‌ها
💎 estimated_difficulty: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 5
  id: 68e7fb2a-a006-4a4d-acbb-0572cbc4629c
  عنوان اصلی: فیلد بلااستفاده: Capability.optional_capabilities
  اولویت اصلی: low
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/services/capability_detector.py

📋 acceptance_criteria کامل:
  - تأیید شد `optional_capabilities` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["optional_capabilities"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["optional_capabilities"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_capability.py", "timeout_seconds": 60}]

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 5
  id: aae100e2-c004-48ef-87ef-f2939305e82a
  عنوان اصلی: فیلد بلااستفاده: ProjectRequirements.os_type
  اولویت اصلی: low
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/capability_detector.py

📋 acceptance_criteria کامل:
  - تأیید شد `os_type` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["os_type"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["os_type"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema.py::test_serialization", "timeout_seconds": 60}]

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
فیلد بلااستفاده: ProjectRequirements.os_type

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
فیلد `os_type` در dataclass/model `ProjectRequirements` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in ProjectRequirements but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `os_type` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.os_type` + `['os_type']` در کل کدبیس.
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 5
  id: 71e7520b-1627-42c8-96dc-0a592d784347
  عنوان اصلی: فیلد بلااستفاده: TaskResult.parent_task_id
  اولویت اصلی: low
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/services/creator_engine.py

📋 acceptance_criteria کامل:
  - تأیید شد `parent_task_id` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["parent_task_id"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["parent_task_id"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema_serialization.py", "timeout_seconds": 60}]

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
فیلد بلااستفاده: TaskResult.parent_task_id

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/creator_engine.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `parent_task_id` در dataclass/model `TaskResult` (فایل `backend/app/services/creator_engine.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in TaskResult but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `parent_task_id` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.parent_task_id` + `['parent_task_id']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/creator_engine.py`
- `ruff check backend/app/services/creator_engine.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 5
  id: 44491bc6-56e8-425b-9f33-383f06329539
  عنوان اصلی: فیلد بلااستفاده: Task.subtasks
  اولویت اصلی: low
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/creator_engine.py

📋 acceptance_criteria کامل:
  - تأیید شد `subtasks` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["subtasks"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["subtasks"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema_serialization.py", "timeout_seconds": 60}]

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
فیلد بلااستفاده: Task.subtasks

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/creator_engine.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `subtasks` در dataclass/model `Task` (فایل `backend/app/services/creator_engine.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in Task but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `subtasks` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.subtasks` + `['subtasks']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/creator_engine.py`
- `ruff check backend/app/services/creator_engine.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 5
  id: bda978bd-d070-49c4-b0fc-7e6c2baa3a18
  عنوان اصلی: فیلد بلااستفاده: DeployConfig.else
  اولویت اصلی: low
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/services/deploy_service.py

📋 acceptance_criteria کامل:
  - تأیید شد `else` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["DeployConfig\\(.*else\\s*=", "\\.else\\b"], "files_hint": ["backend/app/services/deploy_service.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["else"], "files_hint": ["backend/app/services/deploy_service.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_deploy_service.py::test_schema_and_serialization", "timeout_seconds": 60}]

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
فیلد بلااستفاده: DeployConfig.else

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/deploy_service.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/project_memory.py` — این فایل `deploy_service.py` را import می‌کند (caller)
- `backend/app/api/routes/simple_projects.py` — این فایل `deploy_service.py` را import می‌کند (caller)
- `backend/app/api/routes/unified_api.py` — این فایل `deploy_service.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `else` در dataclass/model `DeployConfig` (فایل `backend/app/services/deploy_service.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in DeployConfig but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `else` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.else` + `['else']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/deploy_service.py`
- `ruff check backend/app/services/deploy_service.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
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
- در commit message: `merged-from: 68e7fb2a-a006-4a4d-acbb-0572cbc4629c, aae100e2-c004-48ef-87ef-f2939305e82a, 71e7520b-1627-42c8-96dc-0a592d784347, 44491bc6-56e8-425b-9f33-383f06329539, bda978bd-d070-49c4-b0fc-7e6c2baa3a18`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 5 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 15، 16، 17، 18، 25 همگی به حذف فیلدهای بلااستفاده در مدل‌ها و سرویس‌های مختلف مربوط می‌شوند. تسک‌های 16 و 18 partial هستند و با not_doneهای این خوشه هم‌موضوع هستند.
🎯 theme: پاکسازی فیلدهای بلااستفاده در مدل‌ها و سرویس‌ها
💎 estimated_difficulty: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 5
  id: 68e7fb2a-a006-4a4d-acbb-0572cbc4629c
  عنوان اصلی: فیلد بلااستفاده: Capability.optional_capabilities
  اولویت اصلی: low
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/services/capability_detector.py

📋 acceptance_criteria کامل:
  - تأیید شد `optional_capabilities` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["optional_capabilities"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["optional_capabilities"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_capability.py", "timeout_seconds": 60}]

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 5
  id: aae100e2-c004-48ef-87ef-f2939305e82a
  عنوان اصلی: فیلد بلااستفاده: ProjectRequirements.os_type
  اولویت اصلی: low
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/capability_detector.py

📋 acceptance_criteria کامل:
  - تأیید شد `os_type` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["os_type"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["os_type"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema.py::test_serialization", "timeout_seconds": 60}]

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
فیلد بلااستفاده: ProjectRequirements.os_type

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
فیلد `os_type` در dataclass/model `ProjectRequirements` (فایل `backend/app/services/capability_detector.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in ProjectRequirements but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `os_type` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.os_type` + `['os_type']` در کل کدبیس.
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 5
  id: 71e7520b-1627-42c8-96dc-0a592d784347
  عنوان اصلی: فیلد بلااستفاده: TaskResult.parent_task_id
  اولویت اصلی: low
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/services/creator_engine.py

📋 acceptance_criteria کامل:
  - تأیید شد `parent_task_id` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["parent_task_id"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["parent_task_id"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema_serialization.py", "timeout_seconds": 60}]

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
فیلد بلااستفاده: TaskResult.parent_task_id

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/creator_engine.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `parent_task_id` در dataclass/model `TaskResult` (فایل `backend/app/services/creator_engine.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in TaskResult but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `parent_task_id` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.parent_task_id` + `['parent_task_id']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/creator_engine.py`
- `ruff check backend/app/services/creator_engine.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 5
  id: 44491bc6-56e8-425b-9f33-383f06329539
  عنوان اصلی: فیلد بلااستفاده: Task.subtasks
  اولویت اصلی: low
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/creator_engine.py

📋 acceptance_criteria کامل:
  - تأیید شد `subtasks` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["subtasks"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["subtasks"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema_serialization.py", "timeout_seconds": 60}]

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
فیلد بلااستفاده: Task.subtasks

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/creator_engine.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `subtasks` در dataclass/model `Task` (فایل `backend/app/services/creator_engine.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in Task but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `subtasks` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.subtasks` + `['subtasks']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/creator_engine.py`
- `ruff check backend/app/services/creator_engine.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 5
  id: bda978bd-d070-49c4-b0fc-7e6c2baa3a18
  عنوان اصلی: فیلد بلااستفاده: DeployConfig.else
  اولویت اصلی: low
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/services/deploy_service.py

📋 acceptance_criteria کامل:
  - تأیید شد `else` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["DeployConfig\\(.*else\\s*=", "\\.else\\b"], "files_hint": ["backend/app/services/deploy_service.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["else"], "files_hint": ["backend/app/services/deploy_service.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_deploy_service.py::test_schema_and_serialization", "timeout_seconds": 60}]

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
فیلد بلااستفاده: DeployConfig.else

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/deploy_service.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/project_memory.py` — این فایل `deploy_service.py` را import می‌کند (caller)
- `backend/app/api/routes/simple_projects.py` — این فایل `deploy_service.py` را import می‌کند (caller)
- `backend/app/api/routes/unified_api.py` — این فایل `deploy_service.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
فیلد `else` در dataclass/model `DeployConfig` (فایل `backend/app/services/deploy_service.py`) تعریف شده ولی هرگز خوانده نمی‌شود.

## 🤔 چرا مهم است
یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).

## 🔍 جزئیات
- علت: field defined in DeployConfig but not read/written anywhere

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد `else` در هیچ reader مصرف نمی‌شود
- [ ] یا حذف شد (با migration در صورت persist)، یا reader اضافه شد
- [ ] تست‌های schema و serialization عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `\.else` + `['else']` در کل کدبیس.
گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.
گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/services/deploy_service.py`
- `ruff check backend/app/services/deploy_service.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: low
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
- در commit message: `merged-from: 68e7fb2a-a006-4a4d-acbb-0572cbc4629c, aae100e2-c004-48ef-87ef-f2939305e82a, 71e7520b-1627-42c8-96dc-0a592d784347, 44491bc6-56e8-425b-9f33-383f06329539, bda978bd-d070-49c4-b0fc-7e6c2baa3a18`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. تأیید شد `optional_capabilities` در هیچ reader مصرف نمی‌شود _(verify: static)_
2. یا حذف شد (با migration در صورت persist)، یا reader اضافه شد _(verify: static)_
3. تست‌های schema و serialization عبور می‌کنند _(verify: backend_test)_
4. تأیید شد `os_type` در هیچ reader مصرف نمی‌شود _(verify: static)_
5. تأیید شد `parent_task_id` در هیچ reader مصرف نمی‌شود _(verify: static)_
6. تأیید شد `subtasks` در هیچ reader مصرف نمی‌شود _(verify: static)_
7. تأیید شد `else` در هیچ reader مصرف نمی‌شود _(verify: static)_

## Task Steps

### Step 1: حذف فیلد بلااستفاده optional_capabilities از Capability در capability_detector.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل کدبیس برای یافتن تمام ارجاعات به فیلد optional_capabilities در مدل Capability (فایل backend/app/services/capability_detector.py) و حذف آن از تعریف dataclass است. همچنین شامل حذف هرگونه ارجاع به این فیلد در serializerها، validatorها، یا هر جای دیگر می‌شود. خارج از این مرحله: ایجاد migration برای دیتابیس (اگر فیلد persist شده باشد)، تغییر در frontend، یا افزودن reader جدید. نکته حیاتی: قبل از حذف، باید با grep دقیق بررسی شود که هیچ consumer دیگری (حتی در فایل‌های importکننده) از این فیلد استفاده نمی‌کند.
**Excerpt:**
```
تسک 1 از 5
  id: 68e7fb2a-a006-4a4d-acbb-0572cbc4629c
  عنوان اصلی: فیلد بلااستفاده: Capability.optional_capabilities
  فایل‌های دخیل: backend/app/services/capability_detector.py
📋 acceptance_criteria کامل:
  - تأیید شد `optional_capabilities` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["optional_capabilities"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["optional_capabilities"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_capability.py", "timeout_seconds": 60}]
```

### Step 2: حذف فیلد بلااستفاده os_type از ProjectRequirements در capability_detector.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل کدبیس برای یافتن تمام ارجاعات به فیلد os_type در مدل ProjectRequirements (فایل backend/app/services/capability_detector.py) و حذف آن از تعریف dataclass است. همچنین شامل حذف هرگونه ارجاع به این فیلد در serializerها، validatorها، یا هر جای دیگر می‌شود. خارج از این مرحله: ایجاد migration برای دیتابیس (اگر فیلد persist شده باشد)، تغییر در frontend، یا افزودن reader جدید. نکته حیاتی: وضعیت verify قبلی 'partial' است، یعنی ممکن است بخشی از کار قبلاً انجام شده باشد؛ باید با دقت بررسی شود که چه چیزی باقی مانده.
**Excerpt:**
```
تسک 2 از 5
  id: aae100e2-c004-48ef-87ef-f2939305e82a
  عنوان اصلی: فیلد بلااستفاده: ProjectRequirements.os_type
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/capability_detector.py
📋 acceptance_criteria کامل:
  - تأیید شد `os_type` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["os_type"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["os_type"], "files_hint": ["backend/app/services/capability_detector.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema.py::test_serialization", "timeout_seconds": 60}]
```

### Step 3: حذف فیلد بلااستفاده parent_task_id از TaskResult در creator_engine.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل کدبیس برای یافتن تمام ارجاعات به فیلد parent_task_id در مدل TaskResult (فایل backend/app/services/creator_engine.py) و حذف آن از تعریف dataclass است. همچنین شامل حذف هرگونه ارجاع به این فیلد در serializerها، validatorها، یا هر جای دیگر می‌شود. خارج از این مرحله: ایجاد migration برای دیتابیس (اگر فیلد persist شده باشد)، تغییر در frontend، یا افزودن reader جدید. نکته حیاتی: فایل creator_engine.py ممکن است وابستگی‌های بیشتری نسبت به capability_detector.py داشته باشد؛ باید importها و usageهای cross-file نیز بررسی شوند.
**Excerpt:**
```
تسک 3 از 5
  id: 71e7520b-1627-42c8-96dc-0a592d784347
  عنوان اصلی: فیلد بلااستفاده: TaskResult.parent_task_id
  فایل‌های دخیل: backend/app/services/creator_engine.py
📋 acceptance_criteria کامل:
  - تأیید شد `parent_task_id` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["parent_task_id"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["parent_task_id"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema_serialization.py", "timeout_seconds": 60}]
```

### Step 4: حذف فیلد بلااستفاده subtasks از Task در creator_engine.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل کدبیس برای یافتن تمام ارجاعات به فیلد subtasks در مدل Task (فایل backend/app/services/creator_engine.py) و حذف آن از تعریف dataclass است. همچنین شامل حذف هرگونه ارجاع به این فیلد در serializerها، validatorها، یا هر جای دیگر می‌شود. خارج از این مرحله: ایجاد migration برای دیتابیس (اگر فیلد persist شده باشد)، تغییر در frontend، یا افزودن reader جدید. نکته حیاتی: وضعیت verify قبلی 'partial' است، یعنی ممکن است بخشی از کار قبلاً انجام شده باشد؛ باید با دقت بررسی شود که چه چیزی باقی مانده. همچنین subtasks یک نام عمومی است، grep باید با دقت بیشتری انجام شود تا false positive نداشته باشد.
**Excerpt:**
```
تسک 4 از 5
  id: 44491bc6-56e8-425b-9f33-383f06329539
  عنوان اصلی: فیلد بلااستفاده: Task.subtasks
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/creator_engine.py
📋 acceptance_criteria کامل:
  - تأیید شد `subtasks` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["subtasks"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["subtasks"], "files_hint": ["backend/app/services/creator_engine.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_schema_serialization.py", "timeout_seconds": 60}]
```

### Step 5: حذف فیلد بلااستفاده else از DeployConfig در deploy_service.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل کدبیس برای یافتن تمام ارجاعات به فیلد else در مدل DeployConfig (فایل backend/app/services/deploy_service.py) و حذف آن از تعریف dataclass است. همچنین شامل حذف هرگونه ارجاع به این فیلد در serializerها، validatorها، یا هر جای دیگر می‌شود. خارج از این مرحله: ایجاد migration برای دیتابیس (اگر فیلد persist شده باشد)، تغییر در frontend، یا افزودن reader جدید. نکته حیاتی: 'else' یک کلمه کلیدی پایتون است و همچنین یک نام بسیار عمومی؛ grep باید با الگوی دقیق‌تر (مثل 'DeployConfig\(.*else\s*=' یا '\.else\b') انجام شود تا false positive نداشته باشد. همچنین فایل‌های importکننده (project_memory.py, simple_projects.py, unified_api.py) باید بررسی شوند.
**Excerpt:**
```
تسک 5 از 5
  id: bda978bd-d070-49c4-b0fc-7e6c2baa3a18
  عنوان اصلی: فیلد بلااستفاده: DeployConfig.else
  فایل‌های دخیل: backend/app/services/deploy_service.py
📋 acceptance_criteria کامل:
  - تأیید شد `else` در هیچ reader مصرف نمی‌شود [verify_method=static] [verify_plan={"grep_patterns": ["DeployConfig\\(.*else\\s*=", "\\.else\\b"], "files_hint": ["backend/app/services/deploy_service.py"]}]
  - یا حذف شد (با migration در صورت persist)، یا reader اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["else"], "files_hint": ["backend/app/services/deploy_service.py"]}]
  - تست‌های schema و serialization عبور می‌کنند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_deploy_service.py::test_schema_and_serialization", "timeout_seconds": 60}]
```
