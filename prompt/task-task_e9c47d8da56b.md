---
task_id: task_e9c47d8da56b
title: 'تلفیق: mechanical:title (2 تسک)'
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:28:37.266283+00:00'
updated_at: '2026-06-03T18:22:20.428527+00:00'
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
  id: fe8c7644-c1ed-4004-9006-080f2d91f642
  عنوان اصلی: [منطق] عدم تطابق فرمت پرامپت oversight_strong_prompt با مدل‌های مختلف
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "format adapter", "target.*model"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/format_adapter.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format.*mapping"], "files_hint": ["backend/app/ai_llm/format_adapter.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
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
[منطق] عدم تطابق فرمت پرامپت oversight_strong_prompt با مدل‌های مختلف

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

oversight_strong_prompt یک قالب ثابت برای پرامپت تولید می‌کند، اما مدل‌های مختلف (Cursor, ChatGPT, Claude Code) ممکن است فرمت‌های متفاوتی (مانند system vs user message, XML tags vs markdown) بپذیرند. هیچ مکانیزمی برای تطبیق فرمت با مدل هدف دیده نمی‌شود.

## 💥 پیامد (impact)
کاهش کیفیت پاسخ مدل‌ها، احتمال نادیده گرفتن بخش‌هایی از پرامپت توسط مدل‌های خاص

## 🛠 پیشنهاد رفع اولیه
اضافه کردن یک لایه format adapter که بر اساس target model (از metadata یا input) قالب پرامپت را تنظیم کند

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
  - بررسی و مستندسازی ناسازگاری‌های موجود در pipeline ai_llm — بررسی و مستندسازی ناسازگاری‌های موجود در pipeline ai_llm انجام نشده است
  - طراحی و پیاده‌سازی لایه format adapter برای تطبیق پرامپت با مدل هدف — طراحی و پیاده‌سازی لایه format adapter انجام نشده است
  - یکپارچه‌سازی format adapter با تابع oversight_strong_prompt — یکپارچه‌سازی format adapter با oversight_strong_prompt انجام نشده است
  - نوشتن unit test برای format adapter — unit test برای format adapter نوشته نشده است
  - نوشتن integration test برای pipeline ai_llm با format adapter — integration test برای pipeline ai_llm نوشته نشده است
  - مستندسازی تغییرات و به‌روزرسانی معیارهای پذیرش — مستندسازی تغییرات و به‌روزرسانی معیارهای پذیرش انجام نشده است

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 1998473b-fea5-47cb-af96-72d193883f16
  عنوان اصلی: [منطق] عدم تطابق ساختار پرامپت oversight_strong_prompt با نیازمندی‌های مدل‌های مختلف
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "GPT-4|Claude|Gemini", "system.*user.*message|XML.*tag|token.*limit"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/prompts.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "adapt.*prompt|prompt.*adapt"], "files_hint": ["backend/app/ai_llm/prompts.py", "backend/app/ai_llm/adapters.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description|decision.*rationale|why.*chosen"], "files_hint": [".github/PULL_REQUEST_TEMPLATE.md"]}]

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
[منطق] عدم تطابق ساختار پرامپت oversight_strong_prompt با نیازمندی‌های مدل‌های مختلف

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

پرامپت oversight_strong_prompt یک template ثابت با ساختار مشخص (هدف، موقعیت، فایل‌ها، disclaimer) تولید می‌کند. اما مدل‌های مختلف (GPT-4, Claude, Gemini) فرمت‌های ورودی متفاوتی دارند (مثلاً system vs user message، support for XML tags, token limits). هیچ مکانیزمی برای تطبیق پرامپت با مدل خاص وجود ندارد.

## 💥 پیامد (impact)
یک پرامپت که برای Claude بهینه است ممکن است برای Gemini خروجی ضعیف یا ناقص بدهد. این باعث کاهش کیفیت پاسخ‌ها در برخی providerها و افزایش نرخ خطا می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک abstraction layer برای format کردن پرامپت بر اساس provider ایجاد کنید. هر provider باید متدی برای تبدیل پرامپت استاندارد به فرمت مخصوص خود داشته باشد (مثلاً OpenAI از messages list، Anthropic از system/user split).

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
  - بررسی و شناسایی فایل‌های موجود در pipeline ai_llm — شناسایی فایل‌های مرتبط با oversight_strong_prompt و provider-specific formatters
  - طراحی abstraction layer برای format کردن پرامپت بر اساس provider — طراحی interface PromptFormatter با متد format_prompt و enum providerها
  - پیاده‌سازی OpenAI PromptFormatter (GPT-4) — ایجاد کلاس OpenAIPromptFormatter با فرمت messages list
  - پیاده‌سازی Anthropic PromptFormatter (Claude) — ایجاد کلاس AnthropicPromptFormatter با فرمت system/user split و XML tags
  - پیاده‌سازی Gemini PromptFormatter — ایجاد کلاس GeminiPromptFormatter با فرمت simpler text-based
  - ایجاد factory method برای انتخاب PromptFormatter بر اساس provider — ایجاد تابع get_prompt_formatter با mapping provider->formatter
  - اصلاح oversight_strong_prompt برای استفاده از PromptFormatter — اصلاح oversight_strong_prompt برای دریافت provider و استفاده از PromptFormatter
  - به‌روزرسانی تمام فراخوانی‌های oversight_strong_prompt در pipeline ai_llm — به‌روزرسانی فراخوانی‌های oversight_strong_prompt با پارامتر provider
  - نوشتن unit tests برای PromptFormatter و کلاس‌های concrete — نوشتن unit tests برای PromptFormatter و کلاس‌های concrete
  - نوشتن integration tests برای oversight_strong_prompt با providerهای مختلف — نوشتن integration tests برای oversight_strong_prompt با providerهای مختلف

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: fe8c7644-c1ed-4004-9006-080f2d91f642, 1998473b-fea5-47cb-af96-72d193883f16`
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
  id: fe8c7644-c1ed-4004-9006-080f2d91f642
  عنوان اصلی: [منطق] عدم تطابق فرمت پرامپت oversight_strong_prompt با مدل‌های مختلف
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "format adapter", "target.*model"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/format_adapter.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format.*mapping"], "files_hint": ["backend/app/ai_llm/format_adapter.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
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
[منطق] عدم تطابق فرمت پرامپت oversight_strong_prompt با مدل‌های مختلف

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

oversight_strong_prompt یک قالب ثابت برای پرامپت تولید می‌کند، اما مدل‌های مختلف (Cursor, ChatGPT, Claude Code) ممکن است فرمت‌های متفاوتی (مانند system vs user message, XML tags vs markdown) بپذیرند. هیچ مکانیزمی برای تطبیق فرمت با مدل هدف دیده نمی‌شود.

## 💥 پیامد (impact)
کاهش کیفیت پاسخ مدل‌ها، احتمال نادیده گرفتن بخش‌هایی از پرامپت توسط مدل‌های خاص

## 🛠 پیشنهاد رفع اولیه
اضافه کردن یک لایه format adapter که بر اساس target model (از metadata یا input) قالب پرامپت را تنظیم کند

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
  - بررسی و مستندسازی ناسازگاری‌های موجود در pipeline ai_llm — بررسی و مستندسازی ناسازگاری‌های موجود در pipeline ai_llm انجام نشده است
  - طراحی و پیاده‌سازی لایه format adapter برای تطبیق پرامپت با مدل هدف — طراحی و پیاده‌سازی لایه format adapter انجام نشده است
  - یکپارچه‌سازی format adapter با تابع oversight_strong_prompt — یکپارچه‌سازی format adapter با oversight_strong_prompt انجام نشده است
  - نوشتن unit test برای format adapter — unit test برای format adapter نوشته نشده است
  - نوشتن integration test برای pipeline ai_llm با format adapter — integration test برای pipeline ai_llm نوشته نشده است
  - مستندسازی تغییرات و به‌روزرسانی معیارهای پذیرش — مستندسازی تغییرات و به‌روزرسانی معیارهای پذیرش انجام نشده است

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 1998473b-fea5-47cb-af96-72d193883f16
  عنوان اصلی: [منطق] عدم تطابق ساختار پرامپت oversight_strong_prompt با نیازمندی‌های مدل‌های مختلف
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "GPT-4|Claude|Gemini", "system.*user.*message|XML.*tag|token.*limit"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/prompts.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "adapt.*prompt|prompt.*adapt"], "files_hint": ["backend/app/ai_llm/prompts.py", "backend/app/ai_llm/adapters.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description|decision.*rationale|why.*chosen"], "files_hint": [".github/PULL_REQUEST_TEMPLATE.md"]}]

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
[منطق] عدم تطابق ساختار پرامپت oversight_strong_prompt با نیازمندی‌های مدل‌های مختلف

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

پرامپت oversight_strong_prompt یک template ثابت با ساختار مشخص (هدف، موقعیت، فایل‌ها، disclaimer) تولید می‌کند. اما مدل‌های مختلف (GPT-4, Claude, Gemini) فرمت‌های ورودی متفاوتی دارند (مثلاً system vs user message، support for XML tags, token limits). هیچ مکانیزمی برای تطبیق پرامپت با مدل خاص وجود ندارد.

## 💥 پیامد (impact)
یک پرامپت که برای Claude بهینه است ممکن است برای Gemini خروجی ضعیف یا ناقص بدهد. این باعث کاهش کیفیت پاسخ‌ها در برخی providerها و افزایش نرخ خطا می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک abstraction layer برای format کردن پرامپت بر اساس provider ایجاد کنید. هر provider باید متدی برای تبدیل پرامپت استاندارد به فرمت مخصوص خود داشته باشد (مثلاً OpenAI از messages list، Anthropic از system/user split).

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
  - بررسی و شناسایی فایل‌های موجود در pipeline ai_llm — شناسایی فایل‌های مرتبط با oversight_strong_prompt و provider-specific formatters
  - طراحی abstraction layer برای format کردن پرامپت بر اساس provider — طراحی interface PromptFormatter با متد format_prompt و enum providerها
  - پیاده‌سازی OpenAI PromptFormatter (GPT-4) — ایجاد کلاس OpenAIPromptFormatter با فرمت messages list
  - پیاده‌سازی Anthropic PromptFormatter (Claude) — ایجاد کلاس AnthropicPromptFormatter با فرمت system/user split و XML tags
  - پیاده‌سازی Gemini PromptFormatter — ایجاد کلاس GeminiPromptFormatter با فرمت simpler text-based
  - ایجاد factory method برای انتخاب PromptFormatter بر اساس provider — ایجاد تابع get_prompt_formatter با mapping provider->formatter
  - اصلاح oversight_strong_prompt برای استفاده از PromptFormatter — اصلاح oversight_strong_prompt برای دریافت provider و استفاده از PromptFormatter
  - به‌روزرسانی تمام فراخوانی‌های oversight_strong_prompt در pipeline ai_llm — به‌روزرسانی فراخوانی‌های oversight_strong_prompt با پارامتر provider
  - نوشتن unit tests برای PromptFormatter و کلاس‌های concrete — نوشتن unit tests برای PromptFormatter و کلاس‌های concrete
  - نوشتن integration tests برای oversight_strong_prompt با providerهای مختلف — نوشتن integration tests برای oversight_strong_prompt با providerهای مختلف

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: fe8c7644-c1ed-4004-9006-080f2d91f642, 1998473b-fea5-47cb-af96-72d193883f16`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
3. integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: بررسی و مستندسازی ناسازگاری‌های موجود در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این مرحله شامل خواندن کدهای موجود در pipeline ai_llm (فایل‌های backend/app/ai_llm/pipeline.py، backend/app/ai_llm/format_adapter.py، backend/app/ai_llm/prompts.py و هر فایل مرتبط دیگر) برای شناسایی هر دو طرف ناسازگاری است: oversight_strong_prompt که یک قالب ثابت تولید می‌کند و مدل‌های مختلف (Cursor, ChatGPT, Claude Code, GPT-4, Claude, Gemini) که فرمت‌های متفاوتی می‌پذیرند. فرض‌های هر طرف باید به صورت مستند (در فایل مستندسازی یا کامیت) لیست شوند. خارج از این مرحله است: هرگونه تغییر کد، طراحی یا پیاده‌سازی راه‌حل. نکته حیاتی: این مرحله صرفاً تحلیل و مستندسازی است و باید شامل جستجوی grep برای الگوهای 'oversight_strong_prompt', 'format adapter', 'target.*model' و همچنین بررسی callerهای هر دو طرف باشد.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد: oversight_strong_prompt یک قالب ثابت برای پرامپت تولید می‌کند، اما مدل‌های مختلف (Cursor, ChatGPT, Claude Code) ممکن است فرمت‌های متفاوتی (مانند system vs user message, XML tags vs markdown) بپذیرند. هیچ مکانیزمی برای تطبیق فرمت با مدل هدف دیده نمی‌شود. ... هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "format adapter", "target.*model"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/format_adapter.py"]}]
```

### Step 2: تعیین ground truth و تصمیم‌گیری برای alignment
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل فرض‌های مستند شده در مرحله قبل و تصمیم‌گیری درباره اینکه کدام طرف ناسازگاری به عنوان ground truth (حقیقت مرجع) در نظر گرفته شود است. معمولاً business logic مهم‌تر است، اما باید با بررسی downstream consumers و نیازمندی‌های واقعی تأیید شود. پس از تصمیم‌گیری، باید در فایل‌های مرتبط (مانند backend/app/ai_llm/format_adapter.py یا backend/app/ai_llm/prompts.py) ground truth را مشخص کرد و طرف دیگر را با آن align کرد. خارج از این مرحله است: پیاده‌سازی کامل format adapter یا تغییرات گسترده کد. نکته حیاتی: این تصمیم باید مستند شود و در PR description توضیح داده شود.
**Excerpt:**
```
ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format.*mapping"], "files_hint": ["backend/app/ai_llm/format_adapter.py"]}] ... گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است. گام ۳: طرف دیگر را با ground truth align کن.
```

### Step 3: طراحی و پیاده‌سازی لایه format adapter برای تطبیق پرامپت با مدل هدف
**Status:** `pending` (0%)
**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک abstraction layer (format adapter) است که بر اساس target model (از metadata یا input) قالب پرامپت را تنظیم می‌کند. این لایه باید شامل یک interface یا abstract base class برای PromptFormatter باشد که متد format_prompt را تعریف می‌کند. همچنین باید enum یا mapping برای providerهای مختلف (OpenAI/GPT-4, Anthropic/Claude, Google/Gemini, Cursor, ChatGPT, Claude Code) ایجاد شود. خارج از این مرحله است: پیاده‌سازی concrete formatterها برای هر provider (مرحله بعد). نکته حیاتی: این لایه باید در فایل جدید backend/app/ai_llm/format_adapter.py یا فایل مشابه پیاده‌سازی شود و باید قابلیت توسعه برای providerهای جدید را داشته باشد.
**Excerpt:**
```
اضافه کردن یک لایه format adapter که بر اساس target model (از metadata یا input) قالب پرامپت را تنظیم کند ... یک abstraction layer برای format کردن پرامپت بر اساس provider ایجاد کنید. هر provider باید متدی برای تبدیل پرامپت استاندارد به فرمت مخصوص خود داشته باشد (مثلاً OpenAI از messages list، Anthropic از system/user split).
```

### Step 4: پیاده‌سازی OpenAI PromptFormatter (GPT-4)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد کلاس OpenAIPromptFormatter است که از PromptFormatter ارث‌بری می‌کند و متد format_prompt را برای OpenAI/GPT-4 پیاده‌سازی می‌کند. فرمت خروجی باید به صورت messages list (system message, user message) باشد. خارج از این مرحله است: پیاده‌سازی formatter برای سایر providerها. نکته حیاتی: باید token limits مربوط به GPT-4 را در نظر بگیرد و در صورت نیاز پرامپت را کوتاه کند.
**Excerpt:**
```
پیاده‌سازی OpenAI PromptFormatter (GPT-4) — ایجاد کلاس OpenAIPromptFormatter با فرمت messages list ... هر provider باید متدی برای تبدیل پرامپت استاندارد به فرمت مخصوص خود داشته باشد (مثلاً OpenAI از messages list).
```

### Step 5: پیاده‌سازی Anthropic PromptFormatter (Claude)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد کلاس AnthropicPromptFormatter است که از PromptFormatter ارث‌بری می‌کند و متد format_prompt را برای Anthropic/Claude پیاده‌سازی می‌کند. فرمت خروجی باید به صورت system/user split با پشتیبانی از XML tags باشد. خارج از این مرحله است: پیاده‌سازی formatter برای سایر providerها. نکته حیاتی: باید از XML tags برای ساختاردهی پرامپت استفاده کند و token limits مربوط به Claude را در نظر بگیرد.
**Excerpt:**
```
پیاده‌سازی Anthropic PromptFormatter (Claude) — ایجاد کلاس AnthropicPromptFormatter با فرمت system/user split و XML tags ... Anthropic از system/user split.
```

### Step 6: پیاده‌سازی Gemini PromptFormatter
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد کلاس GeminiPromptFormatter است که از PromptFormatter ارث‌بری می‌کند و متد format_prompt را برای Google/Gemini پیاده‌سازی می‌کند. فرمت خروجی باید به صورت simpler text-based (بدون XML tags پیچیده) باشد. خارج از این مرحله است: پیاده‌سازی formatter برای سایر providerها. نکته حیاتی: باید از فرمت ساده‌تر متنی استفاده کند و token limits مربوط به Gemini را در نظر بگیرد.
**Excerpt:**
```
پیاده‌سازی Gemini PromptFormatter — ایجاد کلاس GeminiPromptFormatter با فرمت simpler text-based ... Gemini از simpler text-based.
```
