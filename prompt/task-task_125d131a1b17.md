---
task_id: task_125d131a1b17
title: 'تلفیق: mechanical:title (2 تسک)'
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:29:09.429761+00:00'
updated_at: '2026-05-29T20:23:58.142281+00:00'
tags:
- consolidated
- post_verify_merge
---

# تلفیق: mechanical:title (2 تسک)

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): شباهت عنوان (trigram Jaccard ≥ 0.7)
🎯 theme: mechanical:title
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 3e009678-6312-438d-90c2-578d446b8cb9
  عنوان اصلی: [منطق] عدم هماهنگی بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["prompt_helper.*variables", "oversight_strong_prompt.*title.*user_goal.*target_locations"], "files_hint": ["backend/app/prompt_helper.py", "backend/app/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align"], "files_hint": ["backend/app/prompt_helper.py", "backend/app/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

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
[منطق] عدم هماهنگی بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline ai_llm است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

prompt_helper از variables dictionary برای جایگزینی در پرامپت‌های دیتابیسی استفاده می‌کند، در حالی که oversight_strong_prompt پارامترهای مشخصی (title, user_goal, target_locations) را به صورت positional دریافت می‌کند. این دو رویکرد با هم ناسازگار هستند و ممکن است تداخل ایجاد کنند.

## 💥 پیامد (impact)
اگر oversight_strong_prompt بخواهد از prompt_helper برای بارگذاری پرامپت‌های پویا استفاده کند، ساختار متغیرها mismatch خواهد داشت. این باعث خطاهای runtime یا پرامپت‌های ناقص می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک interface واحد برای همه سازنده‌های پرامپت تعریف کنید که از یک dictionary استاندارد (context) استفاده کند. oversight_strong_prompt باید بازنویسی شود تا پارامترهای خود را از context dictionary استخراج کند، نه از positional arguments.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: هر دو طرف ناسازگاری را بخوان و فرض‌هایشان را لیست کن.
گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است.
گام ۳: طرف دیگر را با ground truth align کن.
گام ۴: integration test برای این pipeline بنویس تا regression جلوگیری شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run test`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و شناسایی فایل‌های مرتبط با prompt_helper و oversight_strong_prompt در pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با prompt_helper و oversight_strong_prompt
  - طراحی interface واحد (Protocol/ABC) برای همه سازنده‌های پرامپت با context dictionary — طراحی interface واحد (Protocol/ABC) با context dictionary
  - بازنویسی prompt_helper برای استفاده از context dictionary و interface جدید — بازنویسی prompt_helper برای استفاده از context dictionary
  - بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary به جای positional arguments — بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary
  - به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt برای استفاده از context dictionary — به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt
  - نوشتن تست‌های unit برای interface جدید و هر دو سازنده پرامپت (prompt_helper و oversight_strong_prompt) — نوشتن تست‌های unit برای interface و سازنده‌های پرامپت
  - نوشتن integration test برای pipeline ai_llm با استفاده از سازنده‌های پرامپت جدید — نوشتن integration test برای pipeline ai_llm
  - مستندسازی interface جدید و استاندارد context dictionary در docs/ یا README — مستندسازی interface جدید و استاندارد context dictionary
  - بررسی و حذف کدهای قدیمی مرتبط با positional arguments در صورت عدم استفاده — بررسی و حذف کدهای قدیمی مرتبط با positional arguments

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 05ccd19e-bcf1-45e8-a93c-e815554d6b12
  عنوان اصلی: [منطق] عدم coherence بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["prompt_helper.*variables", "oversight_strong_prompt.*title", "oversight_strong_prompt.*user_goal", "oversight_strong_prompt.*raw_user_request"], "files_hint": ["backend/app/ai_llm/]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt.*variables", "oversight_strong_prompt.*Dict"], "files_hint": ["backend/app/ai_llm/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm.py::test_pipeline_integration", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

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
[منطق] عدم coherence بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline ai_llm است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

prompt_helper از variables (Dict) برای جایگزینی استفاده می‌کند، در حالی که oversight_strong_prompt مستقیماً ورودی‌های title, user_goal, raw_user_request را دریافت می‌کند. این دو رویکرد متفاوت می‌توانند باعث ناسازگاری در نحوه ساخت پرامپت نهایی شوند.

## 💥 پیامد (impact)
احتمال نادیده گرفته شدن متغیرهای پویا یا تداخل در جایگزینی مقادیر

## 🛠 پیشنهاد رفع اولیه
یکسان‌سازی interface: یا oversight_strong_prompt از variables dict استفاده کند، یا prompt_helper بتواند خروجی oversight_strong_prompt را به عنوان ورودی بپذیرد

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: هر دو طرف ناسازگاری را بخوان و فرض‌هایشان را لیست کن.
گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است.
گام ۳: طرف دیگر را با ground truth align کن.
گام ۴: integration test برای این pipeline بنویس تا regression جلوگیری شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run test`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  - شناسایی و مستندسازی فرض‌های ناسازگار در prompt_helper و oversight_strong_prompt
  - تعیین ground truth و تصمیم‌گیری روی interface یکسان
  - اصلاح oversight_strong_prompt برای پذیرش variables Dict (در صورت انتخاب این گزینه)
  - اصلاح prompt_helper برای پذیرش خروجی oversight_strong_prompt (در صورت انتخاب این گزینه)
  - به‌روزرسانی type hints و docstrings برای هر دو تابع
  - ثبت کامیت با پیام توضیحی و ارجاع به issue

🔧 مراحل remaining که در super-task باید انجام شوند:
  - نوشتن unit tests برای interface جدید — unit tests برای interface جدید نوشته نشده است
  - اجرای linting و type checking روی کد تغییر یافته — linting و type checking اجرا نشده است

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 3e009678-6312-438d-90c2-578d446b8cb9, 05ccd19e-bcf1-45e8-a93c-e815554d6b12`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): شباهت عنوان (trigram Jaccard ≥ 0.7)
🎯 theme: mechanical:title
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 3e009678-6312-438d-90c2-578d446b8cb9
  عنوان اصلی: [منطق] عدم هماهنگی بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["prompt_helper.*variables", "oversight_strong_prompt.*title.*user_goal.*target_locations"], "files_hint": ["backend/app/prompt_helper.py", "backend/app/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align"], "files_hint": ["backend/app/prompt_helper.py", "backend/app/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

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
[منطق] عدم هماهنگی بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline ai_llm است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

prompt_helper از variables dictionary برای جایگزینی در پرامپت‌های دیتابیسی استفاده می‌کند، در حالی که oversight_strong_prompt پارامترهای مشخصی (title, user_goal, target_locations) را به صورت positional دریافت می‌کند. این دو رویکرد با هم ناسازگار هستند و ممکن است تداخل ایجاد کنند.

## 💥 پیامد (impact)
اگر oversight_strong_prompt بخواهد از prompt_helper برای بارگذاری پرامپت‌های پویا استفاده کند، ساختار متغیرها mismatch خواهد داشت. این باعث خطاهای runtime یا پرامپت‌های ناقص می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک interface واحد برای همه سازنده‌های پرامپت تعریف کنید که از یک dictionary استاندارد (context) استفاده کند. oversight_strong_prompt باید بازنویسی شود تا پارامترهای خود را از context dictionary استخراج کند، نه از positional arguments.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: هر دو طرف ناسازگاری را بخوان و فرض‌هایشان را لیست کن.
گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است.
گام ۳: طرف دیگر را با ground truth align کن.
گام ۴: integration test برای این pipeline بنویس تا regression جلوگیری شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run test`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و شناسایی فایل‌های مرتبط با prompt_helper و oversight_strong_prompt در pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با prompt_helper و oversight_strong_prompt
  - طراحی interface واحد (Protocol/ABC) برای همه سازنده‌های پرامپت با context dictionary — طراحی interface واحد (Protocol/ABC) با context dictionary
  - بازنویسی prompt_helper برای استفاده از context dictionary و interface جدید — بازنویسی prompt_helper برای استفاده از context dictionary
  - بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary به جای positional arguments — بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary
  - به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt برای استفاده از context dictionary — به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt
  - نوشتن تست‌های unit برای interface جدید و هر دو سازنده پرامپت (prompt_helper و oversight_strong_prompt) — نوشتن تست‌های unit برای interface و سازنده‌های پرامپت
  - نوشتن integration test برای pipeline ai_llm با استفاده از سازنده‌های پرامپت جدید — نوشتن integration test برای pipeline ai_llm
  - مستندسازی interface جدید و استاندارد context dictionary در docs/ یا README — مستندسازی interface جدید و استاندارد context dictionary
  - بررسی و حذف کدهای قدیمی مرتبط با positional arguments در صورت عدم استفاده — بررسی و حذف کدهای قدیمی مرتبط با positional arguments

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 05ccd19e-bcf1-45e8-a93c-e815554d6b12
  عنوان اصلی: [منطق] عدم coherence بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["prompt_helper.*variables", "oversight_strong_prompt.*title", "oversight_strong_prompt.*user_goal", "oversight_strong_prompt.*raw_user_request"], "files_hint": ["backend/app/ai_llm/]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt.*variables", "oversight_strong_prompt.*Dict"], "files_hint": ["backend/app/ai_llm/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm.py::test_pipeline_integration", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

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
[منطق] عدم coherence بین prompt_helper و oversight_strong_prompt در مدیریت متغیرها

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline ai_llm است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

prompt_helper از variables (Dict) برای جایگزینی استفاده می‌کند، در حالی که oversight_strong_prompt مستقیماً ورودی‌های title, user_goal, raw_user_request را دریافت می‌کند. این دو رویکرد متفاوت می‌توانند باعث ناسازگاری در نحوه ساخت پرامپت نهایی شوند.

## 💥 پیامد (impact)
احتمال نادیده گرفته شدن متغیرهای پویا یا تداخل در جایگزینی مقادیر

## 🛠 پیشنهاد رفع اولیه
یکسان‌سازی interface: یا oversight_strong_prompt از variables dict استفاده کند، یا prompt_helper بتواند خروجی oversight_strong_prompt را به عنوان ورودی بپذیرد

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: هر دو طرف ناسازگاری را بخوان و فرض‌هایشان را لیست کن.
گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است.
گام ۳: طرف دیگر را با ground truth align کن.
گام ۴: integration test برای این pipeline بنویس تا regression جلوگیری شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run test`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  - شناسایی و مستندسازی فرض‌های ناسازگار در prompt_helper و oversight_strong_prompt
  - تعیین ground truth و تصمیم‌گیری روی interface یکسان
  - اصلاح oversight_strong_prompt برای پذیرش variables Dict (در صورت انتخاب این گزینه)
  - اصلاح prompt_helper برای پذیرش خروجی oversight_strong_prompt (در صورت انتخاب این گزینه)
  - به‌روزرسانی type hints و docstrings برای هر دو تابع
  - ثبت کامیت با پیام توضیحی و ارجاع به issue

🔧 مراحل remaining که در super-task باید انجام شوند:
  - نوشتن unit tests برای interface جدید — unit tests برای interface جدید نوشته نشده است
  - اجرای linting و type checking روی کد تغییر یافته — linting و type checking اجرا نشده است

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 3e009678-6312-438d-90c2-578d446b8cb9, 05ccd19e-bcf1-45e8-a93c-e815554d6b12`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
3. integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: بررسی و شناسایی فایل‌های مرتبط با prompt_helper و oversight_strong_prompt در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جستجو و شناسایی دقیق فایل‌های مربوط به prompt_helper و oversight_strong_prompt در دایرکتوری backend/app/ai_llm/ و backend/app/ است. باید ساختار فعلی این فایل‌ها، نحوه استفاده از متغیرها و پارامترهای ورودی آن‌ها بررسی شود. خروجی این مرحله یک مستند از فرضیات فعلی هر دو طرف است. خارج از این مرحله: هیچ تغییری در کد ایجاد نمی‌شود.
**Excerpt:**
```
گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است.
گام ۳: طرف دیگر را با ground truth align کن.
گام ۴: integration test برای این pipeline بنویس تا regression جلوگیری شود.

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["prompt_helper.*variables", "oversight_strong_prompt.*title.*user_goal.*target_locations"], "files_hint": ["backend/app/prompt_helper.py", "backend/app/oversight_strong_prompt.py"]}]
```

### Step 2: طراحی interface واحد (Protocol/ABC) برای همه سازنده‌های پرامپت با context dictionary
**Status:** `pending` (0%)
**Scope:** این مرحله شامل طراحی یک interface انتزاعی (مانند Protocol یا ABC در Python) است که یک متد واحد برای ساخت پرامپت با یک context dictionary به عنوان ورودی تعریف می‌کند. این interface باید توسط prompt_helper و oversight_strong_prompt پیاده‌سازی شود. خارج از این مرحله: پیاده‌سازی واقعی interface در فایل‌های موجود، تغییر کدهای موجود، یا نوشتن تست.
**Excerpt:**
```
🛠 پیشنهاد رفع اولیه
یک interface واحد برای همه سازنده‌های پرامپت تعریف کنید که از یک dictionary استاندارد (context) استفاده کند. oversight_strong_prompt باید بازنویسی شود تا پارامترهای خود را از context dictionary استخراج کند، نه از positional arguments.

🔧 مراحل remaining که در super-task باید انجام شوند:
  - طراحی interface واحد (Protocol/ABC) برای همه سازنده‌های پرامپت با context dictionary — طراحی interface واحد (Protocol/ABC) با context dictionary
```

### Step 3: بازنویسی prompt_helper برای استفاده از context dictionary و interface جدید
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنویسی تابع یا کلاس prompt_helper (در فایل backend/app/prompt_helper.py) است تا interface طراحی شده در مرحله قبل را پیاده‌سازی کند. به این معنی که prompt_helper باید یک متد build_prompt(context: Dict[str, Any]) داشته باشد که از context dictionary برای جایگزینی متغیرها در پرامپت‌های دیتابیسی استفاده کند. خارج از این مرحله: تغییر oversight_strong_prompt، به‌روزرسانی کدهای استفاده‌کننده از prompt_helper، یا نوشتن تست.
**Excerpt:**
```
🔧 مراحل remaining که در super-task باید انجام شوند:
  - بازنویسی prompt_helper برای استفاده از context dictionary و interface جدید — بازنویسی prompt_helper برای استفاده از context dictionary

📋 شرح ناسازگاری
prompt_helper از variables dictionary برای جایگزینی در پرامپت‌های دیتابیسی استفاده می‌کند، در حالی که oversight_strong_prompt پارامترهای مشخصی (title, user_goal, target_locations) را به صورت positional دریافت می‌کند.
```

### Step 4: بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary به جای positional arguments
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنویسی تابع یا کلاس oversight_strong_prompt (در فایل backend/app/oversight_strong_prompt.py) است تا interface طراحی شده در مرحله 2 را پیاده‌سازی کند. oversight_strong_prompt باید یک متد build_prompt(context: Dict[str, Any]) داشته باشد که پارامترهای title, user_goal, target_locations, raw_user_request را از context dictionary استخراج کند. خارج از این مرحله: تغییر prompt_helper، به‌روزرسانی کدهای استفاده‌کننده از oversight_strong_prompt، یا نوشتن تست.
**Excerpt:**
```
🛠 پیشنهاد رفع اولیه
یک interface واحد برای همه سازنده‌های پرامپت تعریف کنید که از یک dictionary استاندارد (context) استفاده کند. oversight_strong_prompt باید بازنویسی شود تا پارامترهای خود را از context dictionary استخراج کند، نه از positional arguments.

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary به جای positional arguments — بازنویسی oversight_strong_prompt برای دریافت پارامترها از context dictionary
```

### Step 5: به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt برای استفاده از context dictionary
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جستجوی تمام کدهایی است که از oversight_strong_prompt استفاده می‌کنند (با grep برای import یا فراخوانی) و به‌روزرسانی آن‌ها برای استفاده از interface جدید (context dictionary) به جای positional arguments. این شامل به‌روزرسانی type hints و docstrings نیز می‌شود. خارج از این مرحله: تغییر prompt_helper، نوشتن تست‌های جدید، یا مستندسازی.
**Excerpt:**
```
🔧 مراحل remaining که در super-task باید انجام شوند:
  - به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt برای استفاده از context dictionary — به‌روزرسانی تمام کدهای استفاده‌کننده از oversight_strong_prompt

⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.
```

### Step 6: نوشتن تست‌های unit برای interface جدید و هر دو سازنده پرامپت (prompt_helper و oversight_strong_prompt)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های unit برای interface جدید (Protocol/ABC) و هر دو سازنده پرامپت (prompt_helper و oversight_strong_prompt) است. تست‌ها باید بررسی کنند که هر دو کلاس interface را به درستی پیاده‌سازی می‌کنند، context dictionary را به درستی پردازش می‌کنند، و پرامپت نهایی صحیح را تولید می‌کنند. همچنین باید edge cases مانند context خالی یا کلیدهای missing را پوشش دهند. خارج از این مرحله: نوشتن integration test برای pipeline ai_llm، اجرای linting و type checking، یا مستندسازی.
**Excerpt:**
```
🔧 مراحل remaining که در super-task باید انجام شوند:
  - نوشتن تست‌های unit برای interface جدید و هر دو سازنده پرامپت (prompt_helper و oversight_strong_prompt) — نوشتن تست‌های unit برای interface و سازنده‌های پرامپت

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test]
```
