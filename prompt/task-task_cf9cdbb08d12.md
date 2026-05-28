---
task_id: task_cf9cdbb08d12
title: 'تلفیق: mechanical:title (2 تسک)'
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:28:05.215807+00:00'
updated_at: '2026-05-20T04:28:34.001492+00:00'
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
  id: 985875ac-4751-4d46-a5bb-769a29d88362
  عنوان اصلی: [منطق] عدم وجود fallback mechanism در صورت خطای validation
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "retry", "backoff", "validation.*fail", "validate.*retry"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm_pipeline.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "fallback.*decision", "retry.*policy"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm_pipeline.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why.*fallback", "rationale"], "files_hint": ["docs/PR_description.md"]}]

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
[منطق] عدم وجود fallback mechanism در صورت خطای validation

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

در ai_manager، fallback فقط در سطح انتخاب مدل (در صورت عدم پاسخگویی یک provider) تعریف شده است. اما اگر مدل پاسخ دهد ولی validation روی خروجی آن fail شود، هیچ fallback یا retry mechanism وجود ندارد.

## 💥 پیامد (impact)
یک مدل ممکن است پاسخ ظاهراً معتبر بدهد ولی محتوای آن بی‌کیفیت یا نامرتبط باشد و pipeline بدون هیچ تلاش دیگری fail شود.

## 🛠 پیشنهاد رفع اولیه
یک retry policy با backoff اضافه کنید که در صورت fail شدن validation، ابتدا با prompt اصلاحی (شامل خطاهای validation) retry کند و سپس به مدل بعدی fallback کند.

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
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی ناسازگاری منطقی در ai_manager — بررسی و مستندسازی ناسازگاری منطقی در ai_manager انجام نشده
  - طراحی retry policy با backoff برای validation failure — طراحی retry policy با backoff برای validation failure انجام نشده
  - پیاده‌سازی retry logic در ai_manager برای validation failure — پیاده‌سازی retry logic در ai_manager برای validation failure انجام نشده
  - اضافه کردن integration test برای retry و fallback در validation failure — اضافه کردن integration test برای retry و fallback انجام نشده
  - اضافه کردن logging و monitoring برای retry events — اضافه کردن logging و monitoring برای retry events انجام نشده
  - به‌روزرسانی مستندات مربوط به fallback و retry mechanism — به‌روزرسانی مستندات مربوط به fallback و retry mechanism انجام نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 7955fc36-2259-421c-be8e-d2ec3605db55
  عنوان اصلی: [منطق] عدم وجود fallback mechanism برای خطاهای validation
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "retry", "validation.*fail", "validate.*fallback"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "fallback.*validation", "validation.*fallback"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why.*fallback", "validation.*fallback"], "files_hint": [".github/pull_request_template.md"]}]

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
[منطق] عدم وجود fallback mechanism برای خطاهای validation

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

در ai_manager fallback برای مدل‌ها وجود دارد، اما اگر validation روی خروجی fail شود، هیچ fallback یا retry mechanism تعریف نشده است.

## 💥 پیامد (impact)
شکست کامل pipeline در صورت خطای validation، حتی اگر مدل دیگری بتواند پاسخ صحیح بدهد

## 🛠 پیشنهاد رفع اولیه
اضافه کردن retry logic با مدل جایگزین در صورت fail شدن validation، یا کاهش strictness validation در fallback

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
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی وضعیت فعلی fallback و validation در pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی fallback و validation در pipeline ai_llm
  - تعیین ground truth و تصمیم‌گیری درباره رویکرد رفع (retry vs کاهش strictness) — تعیین ground truth و تصمیم‌گیری درباره رویکرد رفع
  - اضافه کردن retry logic با مدل جایگزین در ai_manager هنگام fail شدن validation — اضافه کردن retry logic با مدل جایگزین در ai_manager
  - اضافه کردن مکانیزم retry count و timeout برای جلوگیری از infinite loop — اضافه کردن مکانیزم retry count و timeout
  - به‌روزرسانی validation logic برای پشتیبانی از retry (interface compatibility) — به‌روزرسانی validation logic برای پشتیبانی از retry
  - اضافه کردن integration test برای سناریوی validation fail + retry موفق — نوشتن integration test برای سناریوی validation fail + retry موفق
  - اضافه کردن integration test برای سناریوی validation fail + همه retry‌ها fail — نوشتن integration test برای سناریوی validation fail + همه retry‌ها fail
  - به‌روزرسانی مستندات pipeline ai_llm با توضیح retry mechanism — به‌روزرسانی مستندات pipeline ai_llm با توضیح retry mechanism
  - ثبت کامیت‌ها و ایجاد PR description با checklist کامل — ثبت کامیت‌ها و ایجاد PR description با checklist کامل

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 985875ac-4751-4d46-a5bb-769a29d88362, 7955fc36-2259-421c-be8e-d2ec3605db55`
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
  id: 985875ac-4751-4d46-a5bb-769a29d88362
  عنوان اصلی: [منطق] عدم وجود fallback mechanism در صورت خطای validation
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "retry", "backoff", "validation.*fail", "validate.*retry"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm_pipeline.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "fallback.*decision", "retry.*policy"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm_pipeline.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why.*fallback", "rationale"], "files_hint": ["docs/PR_description.md"]}]

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
[منطق] عدم وجود fallback mechanism در صورت خطای validation

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

در ai_manager، fallback فقط در سطح انتخاب مدل (در صورت عدم پاسخگویی یک provider) تعریف شده است. اما اگر مدل پاسخ دهد ولی validation روی خروجی آن fail شود، هیچ fallback یا retry mechanism وجود ندارد.

## 💥 پیامد (impact)
یک مدل ممکن است پاسخ ظاهراً معتبر بدهد ولی محتوای آن بی‌کیفیت یا نامرتبط باشد و pipeline بدون هیچ تلاش دیگری fail شود.

## 🛠 پیشنهاد رفع اولیه
یک retry policy با backoff اضافه کنید که در صورت fail شدن validation، ابتدا با prompt اصلاحی (شامل خطاهای validation) retry کند و سپس به مدل بعدی fallback کند.

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
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی ناسازگاری منطقی در ai_manager — بررسی و مستندسازی ناسازگاری منطقی در ai_manager انجام نشده
  - طراحی retry policy با backoff برای validation failure — طراحی retry policy با backoff برای validation failure انجام نشده
  - پیاده‌سازی retry logic در ai_manager برای validation failure — پیاده‌سازی retry logic در ai_manager برای validation failure انجام نشده
  - اضافه کردن integration test برای retry و fallback در validation failure — اضافه کردن integration test برای retry و fallback انجام نشده
  - اضافه کردن logging و monitoring برای retry events — اضافه کردن logging و monitoring برای retry events انجام نشده
  - به‌روزرسانی مستندات مربوط به fallback و retry mechanism — به‌روزرسانی مستندات مربوط به fallback و retry mechanism انجام نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 7955fc36-2259-421c-be8e-d2ec3605db55
  عنوان اصلی: [منطق] عدم وجود fallback mechanism برای خطاهای validation
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "retry", "validation.*fail", "validate.*fallback"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "fallback.*validation", "validation.*fallback"], "files_hint": ["backend/app/ai_manager.py", "backend/app/ai_llm.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why.*fallback", "validation.*fallback"], "files_hint": [".github/pull_request_template.md"]}]

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
[منطق] عدم وجود fallback mechanism برای خطاهای validation

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

در ai_manager fallback برای مدل‌ها وجود دارد، اما اگر validation روی خروجی fail شود، هیچ fallback یا retry mechanism تعریف نشده است.

## 💥 پیامد (impact)
شکست کامل pipeline در صورت خطای validation، حتی اگر مدل دیگری بتواند پاسخ صحیح بدهد

## 🛠 پیشنهاد رفع اولیه
اضافه کردن retry logic با مدل جایگزین در صورت fail شدن validation، یا کاهش strictness validation در fallback

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
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی وضعیت فعلی fallback و validation در pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی fallback و validation در pipeline ai_llm
  - تعیین ground truth و تصمیم‌گیری درباره رویکرد رفع (retry vs کاهش strictness) — تعیین ground truth و تصمیم‌گیری درباره رویکرد رفع
  - اضافه کردن retry logic با مدل جایگزین در ai_manager هنگام fail شدن validation — اضافه کردن retry logic با مدل جایگزین در ai_manager
  - اضافه کردن مکانیزم retry count و timeout برای جلوگیری از infinite loop — اضافه کردن مکانیزم retry count و timeout
  - به‌روزرسانی validation logic برای پشتیبانی از retry (interface compatibility) — به‌روزرسانی validation logic برای پشتیبانی از retry
  - اضافه کردن integration test برای سناریوی validation fail + retry موفق — نوشتن integration test برای سناریوی validation fail + retry موفق
  - اضافه کردن integration test برای سناریوی validation fail + همه retry‌ها fail — نوشتن integration test برای سناریوی validation fail + همه retry‌ها fail
  - به‌روزرسانی مستندات pipeline ai_llm با توضیح retry mechanism — به‌روزرسانی مستندات pipeline ai_llm با توضیح retry mechanism
  - ثبت کامیت‌ها و ایجاد PR description با checklist کامل — ثبت کامیت‌ها و ایجاد PR description با checklist کامل

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 985875ac-4751-4d46-a5bb-769a29d88362, 7955fc36-2259-421c-be8e-d2ec3605db55`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
3. integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: static)_

## Task Steps

### Step 1: بررسی و مستندسازی وضعیت فعلی fallback و validation در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این مرحله شامل خواندن کدهای موجود در فایل‌های backend/app/ai_manager.py و backend/app/ai_llm.py (یا ai_llm_pipeline.py) برای شناسایی منطق فعلی fallback و validation است. باید فرض‌های هر دو طرف (مدیریت مدل و اعتبارسنجی خروجی) استخراج و مستند شود. خارج از این مرحله: هرگونه تغییر کد یا تصمیم‌گیری درباره راه‌حل. نکته حیاتی: از grep برای یافتن الگوهای fallback, retry, validation.*fail استفاده شود.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد: در ai_manager، fallback فقط در سطح انتخاب مدل (در صورت عدم پاسخگویی یک provider) تعریف شده است. اما اگر مدل پاسخ دهد ولی validation روی خروجی آن fail شود، هیچ fallback یا retry mechanism وجود ندارد.
```

### Step 2: تعیین ground truth و تصمیم‌گیری درباره رویکرد رفع (retry vs کاهش strictness)
**Status:** `pending` (0%)
**Scope:** بر اساس مستندات مرحله قبل، تصمیم گرفته شود کدام طرف (منطق fallback مدل یا منطق validation) ground truth است. معمولاً business logic مهم‌تر است. سپس رویکرد رفع انتخاب شود: اضافه کردن retry logic با مدل جایگزین یا کاهش strictness validation در fallback. خارج از این مرحله: پیاده‌سازی. نکته حیاتی: این تصمیم باید در PR description بعدی توضیح داده شود.
**Excerpt:**
```
🛠 پیشنهاد رفع اولیه: یک retry policy با backoff اضافه کنید که در صورت fail شدن validation، ابتدا با prompt اصلاحی (شامل خطاهای validation) retry کند و سپس به مدل بعدی fallback کند.
```

### Step 3: پیاده‌سازی retry logic با مدل جایگزین در ai_manager هنگام fail شدن validation
**Status:** `pending` (0%)
**Scope:** در فایل backend/app/ai_manager.py، منطق جدیدی اضافه شود که در صورت fail شدن validation خروجی مدل، ابتدا با یک prompt اصلاحی (شامل خطاهای validation) retry کند و سپس به مدل بعدی fallback کند. مکانیزم retry count و timeout نیز پیاده‌سازی شود. خارج از این مرحله: تغییر validation logic یا نوشتن تست. نکته حیاتی: باید از infinite loop جلوگیری شود.
**Excerpt:**
```
🛠 پیشنهاد رفع اولیه: یک retry policy با backoff اضافه کنید که در صورت fail شدن validation، ابتدا با prompt اصلاحی (شامل خطاهای validation) retry کند و سپس به مدل بعدی fallback کند.
```

### Step 4: به‌روزرسانی validation logic برای پشتیبانی از retry (interface compatibility)
**Status:** `pending` (0%)
**Scope:** در فایل backend/app/ai_llm.py (یا ai_llm_pipeline.py)، interface validation logic به‌روزرسانی شود تا بتواند خطاهای validation را به صورت ساختاریافته به ai_manager برگرداند (مثلاً از طریق exception یا return value). خارج از این مرحله: تغییر logic خود validation. نکته حیاتی: باید backward compatible باشد.
**Excerpt:**
```
🛠 پیشنهاد رفع اولیه: اضافه کردن retry logic با مدل جایگزین در صورت fail شدن validation، یا کاهش strictness validation در fallback
```

### Step 5: نوشتن integration test برای سناریوی validation fail + retry موفق
**Status:** `pending` (0%)
**Scope:** یک integration test در tests/test_ai_llm_pipeline.py (یا tests/test_ai_llm.py) نوشته شود که سناریوی زیر را پوشش دهد: validation fail می‌شود، retry با prompt اصلاحی موفق می‌شود و pipeline ادامه می‌یابد. خارج از این مرحله: تست سناریوی همه retry‌ها fail. نکته حیاتی: تست باید timeout 120 ثانیه‌ای داشته باشد.
**Excerpt:**
```
integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
```

### Step 6: نوشتن integration test برای سناریوی validation fail + همه retry‌ها fail
**Status:** `pending` (0%)
**Scope:** یک integration test دیگر نوشته شود که سناریوی زیر را پوشش دهد: validation fail می‌شود، همه retry‌ها نیز fail می‌شوند و pipeline در نهایت با خطای مناسب fail می‌شود. خارج از این مرحله: تست سناریوی retry موفق. نکته حیاتی: تست باید timeout 120 ثانیه‌ای داشته باشد و خطای نهایی را بررسی کند.
**Excerpt:**
```
اضافه کردن integration test برای سناریوی validation fail + همه retry‌ها fail — نوشتن integration test برای سناریوی validation fail + همه retry‌ها fail
```
