---
task_id: task_4be78aa7a649
title: 'بهبود و استانداردسازی pipeline AI: validation، fallback، یکپارچگی و امنیت'
type: other
priority: critical
execution_priority: 1000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:23:25.107129+00:00'
updated_at: '2026-06-03T18:22:04.606849+00:00'
tags:
- consolidated
- post_verify_merge
target_files:
- backend/app/services/inspector_agent.py
- backend/app/services/inspector_scan_bridge.py
- backend/app/services/ai_manager.py
- backend/app/services/openai_service.py
- backend/app/services/claude_service.py
- backend/app/services/oversight_service.py
- backend/tests/test_ai_llm_pipeline.py
- backend/app/services/oversight_strong_prompt.py
- tests/test_oversight_service.py
- backend/tests/test_oversight_service.py
- backend/app/api/routes/oversight.py
- backend/app/services/verify_runtime/auth_runner.py
- backend/app/models/inspector_session.py
- backend/app/api/routes/analysis.py
- backend/app/services/verify_runtime/runner.py
- backend/app/services/inspector_intent_resolver.py
- backend/app/services/ai_balance_service.py
- backend/app/services/ai_base.py
- frontend/src/app/model-profiles/page.tsx
- backend/app/api/routes/model_profiles.py
- backend/app/models/ai_profile.py
- backend/app/ai_manager.py
- backend/app/ai_llm/pipeline.py
- backend/app/services/ai_llm.py
- backend/app/services/prompt_helper.py
- backend/app/models/system_prompt.py
- backend/app/api/routes/system_prompts.py
- backend/app/services/hallucination_guard.py
- backend/app/services/scan_v5/scan_bundle.py
- backend/app/core/models_registry.py
- backend/app/services/log_stream_service.py
- backend/app/services/log_to_issues_service.py
- backend/app/services/scan_v5/outcome_analyzer.py
- backend/app/services/verify_runtime/iterative_orchestrator.py
- backend/app/services/verify_runtime/code_aware_verifier.py
- docs/README.md
- docs/ROADMAP.md
- backend/app/api/routes/project_journal.py
- backend/app/services/journal_service.py
- backend/app/services/oversight_verifier.py
- backend/app/services/oversight_codex_service.py
- docs/ARCHITECTURE.md
---

# بهبود و استانداردسازی pipeline AI: validation، fallback، یکپارچگی و امنیت

## Raw Idea

🧬 این یک تسک تلفیقی است — از 16 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 19، 21، 22، 23، 24، 28، 30، 31، 32، 34، 35، 36، 37، 39 همگی به بهبود منطق، validation، fallback، و یکپارچگی در pipeline AI (ai_manager، oversight_strong_prompt، models_registry) مربوط می‌شوند. تسک 38 (partial) نیز به OversightService مرتبط است.
🎯 theme: بهبود و استانداردسازی pipeline AI (ai_manager و oversight)
💎 estimated_difficulty: large

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 16
  id: 5569212c-b3f9-4361-a155-dbd45d88a002
  عنوان اصلی: [منطق] عدم وجود validation بر روی پاسخ AI در ai_manager
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["nassazegi.*ai_manager.*validation", "ai_manager.*output.*parser", "ai_manager.*hallucination"], "files_hint": ["docs/", "backend/app/ai_manager/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground.truth", "align", "ai_manager.*validation.*implement"], "files_hint": ["docs/", "backend/app/ai_manager/"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR.*description", "decision.*why", "validation.*ai_manager"], "files_hint": [".github/PULL_REQUEST_TEMPLATE.md", "docs/"]}]

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
[منطق] عدم وجود validation بر روی پاسخ AI در ai_manager

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

در مستندات ai_manager اشاره‌ای به validation خروجی مدل‌های AI نشده است. با توجه به اینکه این سرویس مدیریت مرکزی سرویس‌های AI را بر عهده دارد و با مدل‌های مختلف (OpenAI, Claude) کار می‌کند، عدم وجود validation می‌تواند منجر به پردازش پاسخ‌های ناقص، نادرست یا دارای توهم (hallucination) شود. همچنین مشخص نیست که آیا output parser خاصی برای تطبیق خروجی مدل با فرمت مورد انتظار downstream services وجود دارد یا خیر.

## 💥 پیامد (impact)
پاسخ‌های نادرست یا ناقص به کاربر نهایی ارسال می‌شود. خطاهای زنجیره‌ای در pipeline به دلیل عدم تطابق فرمت خروجی. افزایش ریسک توهم (hallucination) در پاسخ‌های AI.

## 🛠 پیشنهاد رفع اولیه
یک لایه validation و output parser به ai_manager اضافه کنید. برای هر مدل، یک validator مخصوص (مثلاً Pydantic model) تعریف کنید که ساختار و محتوای پاسخ را بررسی کند. از تکنیک‌های grounding و fact-checking برای کاهش توهم استفاده کنید.

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
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
  - تعریف Pydantic models برای validation ساختار پاسخ مدل‌های AI — تعریف Pydantic models برای validation ساختار پاسخ مدل‌های AI
  - پیاده‌سازی output parser برای تطبیق خروجی مدل با فرمت مورد انتظار downstream services — پیاده‌سازی output parser برای تطبیق خروجی مدل با فرمت downstream
  - پیاده‌سازی grounding و fact-checking اولیه برای کاهش توهم (hallucination) — پیاده‌سازی grounding و fact-checking اولیه برای کاهش توهم
  - یکپارچه‌سازی validator، output parser و grounding service در pipeline اصلی ai_manager — یکپارچه‌سازی validator, output parser و grounding در pipeline اصلی
  - نوشتن تست‌های واحد (unit tests) برای validator و output parser — نوشتن unit tests برای validator و output parser
  - نوشتن تست‌های واحد (unit tests) برای grounding service — نوشتن unit tests برای grounding service
  - نوشتن تست‌های یکپارچه‌سازی (integration tests) برای کل pipeline ai_manager — نوشتن integration tests برای کل pipeline ai_manager
  - به‌روزرسانی مستندات ai_manager برای انعکاس قابلیت‌های جدید — به‌روزرسانی مستندات ai_manager برای قابلیت‌های جدید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 16
  id: f023ba69-7294-4337-abd4-14a8d6093db6
  عنوان اصلی: [منطق] عدم تطابق ورودی‌های مورد انتظار ai_manager با خروجی‌های oversight_strong_prompt
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ai_manager.*expect.*user.*prompt", "oversight_strong_prompt.*executive.*prompt"], "files_hint": ["backend/app/ai_manager.py", "backend/app/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth.*align", "align.*oversight_strong_prompt"], "files_hint": ["backend/app/ai_manager.py", "backend/app/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_pipeline_integration", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["why.*decision.*made", "reason.*align"], "files_hint": ["PR description"]}]

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
[منطق] عدم تطابق ورودی‌های مورد انتظار ai_manager با خروجی‌های oversight_strong_prompt

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

ai_manager انتظار 'پرامپت کاربر (string)' را به عنوان ورودی دارد، در حالی که oversight_strong_prompt یک پرامپت اجرایی کامل و ساختاریافته (با قالب ثابت) تولید می‌کند. این دو با هم ناسازگار هستند: ai_manager برای پردازش یک پرامپت خام کاربر طراحی شده، اما خروجی builder یک پرامپت نهایی و آماده اجراست که احتمالاً باید مستقیماً به مدل ارسال شود، نه اینکه دوباره از ai_manager عبور کند.

## 💥 پیامد (impact)
اگر خروجی oversight_strong_prompt به ai_manager داده شود، ai_manager ممکن است آن را به عنوان یک پرامپت ساده تفسیر کرده و دوباره پردازش کند (مثلاً انتخاب مدل یا fallback) که منجر به نادیده گرفتن ساختار دقیق پرامپت، افزایش هزینه، تأخیر و احتمالاً خرابی خروجی نهایی می‌شود.

## 🛠 پیشنهاد رفع اولیه
مسیر جریان داده را شفاف کنید. یا ai_manager باید بتواند پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد، یا یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده (مانند خروجی oversight_strong_prompt) ایجاد کنید که مستقیماً به سرویس مدل ارسال شوند.

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
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و تحلیل ساختار فعلی pipeline ai_llm — بررسی و تحلیل ساختار فعلی pipeline ai_llm انجام نشده
  - طراحی مسیر bypass برای پرامپت‌های ساختاریافته — طراحی مسیر bypass برای پرامپت‌های ساختاریافته انجام نشده
  - پیاده‌سازی مکانیزم تشخیص پرامپت ساختاریافته — مکانیزم تشخیص پرامپت ساختاریافته پیاده‌سازی نشده
  - اصلاح ai_manager برای عبور دادن پرامپت‌های ساختاریافته بدون تغییر — ai_manager اصلاح نشده برای عبور پرامپت‌های ساختاریافته
  - ایجاد مسیر bypass مستقیم برای پرامپت‌های ساختاریافته (گزینه دوم) — مسیر bypass مستقیم ایجاد نشده
  - به‌روزرسانی oversight_strong_prompt برای استفاده از مسیر bypass — oversight_strong_prompt به‌روزرسانی نشده
  - نوشتن تست‌های واحد برای مکانیزم تشخیص پرامپت — تست‌های واحد برای تشخیص پرامپت نوشته نشده
  - نوشتن تست‌های واحد برای ai_manager اصلاح شده — تست‌های واحد برای ai_manager اصلاح‌شده نوشته نشده
  - نوشتن تست‌های integration برای مسیر bypass — تست‌های integration برای مسیر bypass نوشته نشده
  - انجام audit نهایی و مستندسازی تغییرات — audit نهایی و مستندسازی انجام نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 16
  id: 4816a520-a370-4e87-9005-a42ff9615257
  عنوان اصلی: OversightService فاقد تست واحد است — ۲۰ فایل به آن وابسته‌اند
  اولویت اصلی: critical
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/oversight_service.py

📋 acceptance_criteria کامل:
  - تست CRUD برای watched projects (add, update, delete, list) [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_crud_watched_projects", "timeout_seconds": 60}]
  - تست scheduler loop با mock کردن sleep [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_scheduler_loop_mock_sleep", "timeout_seconds": 60}]
  - تست auto_register_watched با mock GitHub API [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_auto_register_watched_mock_github", "timeout_seconds": 60}]
  - تست edge cases: duplicate repo, invalid URL, empty fields [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_edge_cases", "timeout_seconds": 60}]

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
OversightService فاقد تست واحد است — ۲۰ فایل به آن وابسته‌اند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-100` — `OversightService` — کلاس اصلی که باید تست شود
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self._lock = asyncio.Lock()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + asyncio + GitHub API

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 12) — API routes که از OversightService استفاده می‌کنند
- `backend/app/main.py` (سطر 93) — lifespan که scheduler را راه‌اندازی می‌کند
- `backend/app/api/routes/github_import.py` (سطر 162) — از auto_register_watched استفاده می‌کند
- `backend/app/core/database.py` — `oversight_service.py` این فایل را import می‌کند
- `backend/app/models/setting.py` — `oversight_service.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/__init__.py` — `oversight_service.py` این فایل را import می‌کند
- `backend/app/services/ai_manager.py` — `oversight_service.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
۲۰ فایل به این سرویس وابسته‌اند: ۵ route, ۱۰ service, ۳ core, main.py, ۱ script

## 🔍 Context و وضعیت فعلی
سرویس `oversight_service.py` هستهٔ مرکزی نظارت پروژه‌های GitHub است و ۲۰ فایل مختلف (routes, services, main.py) به آن import دارند. این سرویس شامل منطق پیچیدهٔ مدیریت watched projects, scheduling, runtime verification, و auto-register است. عدم وجود تست می‌تواند منجر به شکست‌های زنجیره‌ای در کل سیستم شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست CRUD برای watched projects (add, update, delete, list)
- [ ] تست scheduler loop با mock کردن sleep
- [ ] تست auto_register_watched با mock GitHub API
- [ ] تست edge cases: duplicate repo, invalid URL, empty fields
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register

## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v`
- `pytest backend/tests/ --cov=app.services.oversight_service`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در OversightService بدون تست می‌تواند کل سیستم نظارت را مختل کند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: large

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 16
  id: c159181f-ebc5-427e-8ead-118d56dacae5
  عنوان اصلی: [منطق] عدم وجود permission check در auth pipeline
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ناسازگاری", "permission", "authorization", "auth pipeline"], "files_hint": ["docs/", "README.md", "*.md"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "permission check", "authorization"], "files_hint": ["docs/", "*.md"]}]
  - integration test برای pipeline `auth` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_auth_pipeline.py", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "چرا این تصمیم گرفته شد", "reason", "rationale"], "files_hint": ["docs/", "*.md"]}]

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
[منطق] عدم وجود permission check در auth pipeline

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline auth است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `auth` یک ناسازگاری منطقی پیدا شد:

در مستندات ارائه شده، هیچ اشاره‌ای به مکانیزم permission یا authorization در pipeline احراز هویت نشده است. تمام مسیرهای mutation (مانند ذخیره سشن‌ها و پیام‌ها در inspector_session) بدون عبور از یک لایه permission check قابل دسترسی هستند.

## 💥 پیامد (impact)
هر کاربر احراز هویت شده (یا حتی کاربران غیرمجاز در صورت عدم احراز هویت) می‌توانند داده‌های حساس مانند سشن‌های بازرس را تغییر دهند یا ایجاد کنند. این منجر به نقض امنیت و یکپارچگی داده‌ها می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک middleware یا dependency برای بررسی permission قبل از هر mutation اضافه کنید. اطمینان حاصل کنید که کاربر فقط مجوز تغییر سشن‌های متعلق به خود یا سشن‌هایی که مجوز لازم را دارد، داشته باشد.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `auth` بدون شکست عبور می‌کند
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
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و شناسایی فایل‌های موجود در pipeline auth و مسیرهای mutation — بررسی و شناسایی فایل‌های موجود در pipeline auth و مسیرهای mutation
  - طراحی و پیاده‌سازی middleware/dependency پایه برای permission check — طراحی و پیاده‌سازی middleware/dependency پایه برای permission check
  - تعریف permissionهای مورد نیاز برای inspector_session (ایجاد، ویرایش، حذف) — تعریف permissionهای مورد نیاز برای inspector_session
  - اعمال permission check بر روی endpoints مربوط به ایجاد inspector_session (POST) — اعمال permission check بر روی endpoints ایجاد inspector_session (POST)
  - اعمال permission check بر روی endpoints مربوط به ویرایش inspector_session (PUT/PATCH) — اعمال permission check بر روی endpoints ویرایش inspector_session (PUT/PATCH)
  - اعمال permission check بر روی endpoints مربوط به حذف inspector_session (DELETE) — اعمال permission check بر روی endpoints حذف inspector_session (DELETE)
  - اعمال permission check بر روی endpoints مربوط به پیام‌های inspector_session (POST برای ایجاد پیام) — اعمال permission check بر روی endpoints ایجاد پیام inspector_session (POST)
  - اعمال permission check بر روی endpoints مربوط به ویرایش پیام‌های inspector_session (PUT/PATCH) — اعمال permission check بر روی endpoints ویرایش پیام inspector_session (PUT/PATCH)
  - اعمال permission check بر روی endpoints مربوط به حذف پیام‌های inspector_session (DELETE) — اعمال permission check بر روی endpoints حذف پیام inspector_session (DELETE)
  - نوشتن تست‌های unit برای middleware/dependency permission check — نوشتن تست‌های unit برای middleware/dependency permission check
  - نوشتن تست‌های integration برای endpoints inspector_session با permission check — نوشتن تست‌های integration برای endpoints inspector_session با permission check
  - نوشتن تست‌های integration برای endpoints پیام‌های inspector_session با permission check — نوشتن تست‌های integration برای endpoints پیام‌های inspector_session با permission check
  - بررسی و رفع coherence issues (feature flag rot یا refactor ناتمام) در pipeline auth — بررسی و رفع coherence issues در pipeline auth
  - مستندسازی تغییرات انجام شده و به‌روزرسانی README یا مستندات API — مستندسازی تغییرات و به‌روزرسانی README یا مستندات API

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 16
  id: 0147715a-b178-44a6-89c5-bb4b36742c45
  عنوان اصلی: [منطق] عدم تطابق بین task_type و قابلیت‌های مدل در انتخاب هوشمند
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ناسازگاری", "شناسایی", "هایشان", "مستند"], "files_hint": []}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground", "truth", "align", "تعیین", "دیگر"], "files_hint": []}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["integration", "pipeline", "ai_llm", "برای", "بدون", "شکست", "عبور"], "files_hint": []}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["description", "توضیح", "تصمیم", "گرفته"], "files_hint": []}]

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
[منطق] عدم تطابق بین task_type و قابلیت‌های مدل در انتخاب هوشمند

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

در مستندات ai_manager، ورودی‌ها شامل 'task_type' و 'قابلیت‌های مورد نیاز (ModelCapability)' هستند، اما مشخص نیست که چگونه این دو با هم تطبیق داده می‌شوند. ممکن است یک task_type خاص به قابلیت‌های متفاوتی نیاز داشته باشد و انتخاب مدل صرفاً بر اساس task_type بدون در نظر گرفتن قابلیت‌های دقیق، نادرست باشد. همچنین ارتباط بین task_type و مدل‌های ترجیحی (preferred models) مشخص نیست.

## 💥 پیامد (impact)
انتخاب مدل نامناسب برای یک task خاص. کاهش کیفیت پاسخ‌ها. استفاده از مدل‌های گران‌تر یا کندتر برای کارهای ساده. شکست در fallback به دلیل عدم تطابق قابلیت‌ها.

## 🛠 پیشنهاد رفع اولیه
یک mapping صریح بین task_type و مجموعه‌ای از ModelCapabilityهای مورد نیاز ایجاد کنید. منطق انتخاب هوشمند را طوری طراحی کنید که ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد.

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
  - بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager — بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager
  - تعریف یک mapping صریح بین task_type و مجموعه ModelCapabilityهای مورد نیاز — تعریف mapping صریح بین task_type و ModelCapability
  - اصلاح منطق انتخاب مدل در ai_manager برای استفاده از mapping جدید — اصلاح منطق انتخاب مدل در ai_manager
  - به‌روزرسانی مستندات ai_manager برای انعکاس mapping جدید و منطق انتخاب — به‌روزرسانی مستندات ai_manager
  - نوشتن تست‌های integration برای سناریوی کامل انتخاب مدل — نوشتن تست‌های integration برای انتخاب مدل
  - بررسی و رفع مشکلات احتمالی fallback در سناریوهای لبه — بررسی و رفع مشکلات fallback

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 16
  id: c81ec6af-6080-448e-89f4-7da379cf1d76
  عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در ai_manager
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "retry", "timeout", "rate.limit", "validation.failure"], "files_hint": ["docs/", "backend/app/ai_manager.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground.truth", "align", "fallback.strategy"], "files_hint": ["docs/", "backend/app/ai_manager.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 120}]
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
[منطق] عدم وجود مکانیزم fallback مشخص در ai_manager

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

مستندات به 'مدیریت fallback' اشاره دارد، اما جزئیات آن مشخص نیست. با توجه به اینکه ai_manager با چندین سرویس (OpenAI, Claude) کار می‌کند، یک استراتژی fallback شفاف (مثلاً ترتیب fallback، timeout، تعداد تلاش مجدد) ضروری است. همچنین مشخص نیست که آیا fallback بر اساس خطاهای سرویس (مثلاً rate limit) یا کیفیت پاسخ (validation failure) انجام می‌شود.

## 💥 پیامد (impact)
در صورت خرابی یک سرویس AI، pipeline بدون fallback می‌ماند و خطا به کاربر نمایش داده می‌شود. عدم مدیریت هوشمند fallback می‌تواند منجر به افزایش latency یا هزینه شود.

## 🛠 پیشنهاد رفع اولیه
یک استراتژی fallback واضح در ai_manager پیاده‌سازی کنید: ترتیب fallback (مثلاً OpenAI -> Claude -> ...)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout).

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
  - بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
  - طراحی و پیاده‌سازی کلاس FallbackStrategy با پشتیبانی از ترتیب fallback — طراحی و پیاده‌سازی کلاس FallbackStrategy
  - پیاده‌سازی مکانیزم timeout برای هر سرویس AI — پیاده‌سازی مکانیزم timeout برای هر سرویس AI
  - پیاده‌سازی مکانیزم retry با backoff برای خطاهای موقت سرویس — پیاده‌سازی مکانیزم retry با backoff
  - تعریف شرط‌های fallback: خطای سرویس، خطای validation، timeout — تعریف شرط‌های fallback
  - یکپارچه‌سازی FallbackStrategy، timeout، retry، و شرط‌ها در ai_manager — یکپارچه‌سازی همه اجزا در ai_manager
  - افزودن logging و metrics برای fallback events — افزودن logging و metrics برای fallback
  - نوشتن unit tests برای FallbackStrategy — نوشتن unit tests برای FallbackStrategy
  - نوشتن unit tests برای timeout و retry logic — نوشتن unit tests برای timeout و retry
  - نوشتن unit tests برای FallbackCondition — نوشتن unit tests برای FallbackCondition
  - نوشتن integration tests برای fallback کامل در ai_manager — نوشتن integration tests برای fallback کامل
  - به‌روزرسانی مستندات ai_manager با استراتژی fallback — به‌روزرسانی مستندات ai_manager

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 16
  id: 4e23a1de-5d9d-4e09-9481-07c040f17f29
  عنوان اصلی: Model profiles page uses hardcoded default data instead of real backend data
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "eslint"], "files_hint": ["package.json", ".eslintrc"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["tsc", "type-check", "typescript"], "files_hint": ["tsconfig.json"]}]

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
Model profiles page uses hardcoded default data instead of real backend data

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
The `model-profiles/page.tsx` defines extensive hardcoded default profiles (lines 90-97)

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

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
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 16
  id: aa8c1673-2357-40d4-9088-2e28a2c5eb7b
  عنوان اصلی: [منطق] عدم وجود validation و guardrails در خروجی oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "oversight_strong_prompt"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["PR_description.md"]}]

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
[منطق] عدم وجود validation و guardrails در خروجی oversight_strong_prompt

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

مستندات oversight_strong_prompt هیچ اشاره‌ای به validation روی خروجی (پرامپت ساخته شده) یا مکانیزم‌های ضد توهم (hallucination guards) ندارد. با توجه به اینکه این پرامپت مستقیماً به مدل‌های خارجی (Cursor, ChatGPT) ارسال می‌شود، عدم وجود validation می‌تواند منجر به ارسال پرامپت‌های ناقص، دارای خطاهای ساختاری یا حاوی اطلاعات گمراه‌کننده شود.

## 💥 پیامد (impact)
مدل خارجی ممکن است خروجی نامرتبط، ناقص یا خطرناک تولید کند. در worst-case، پرامپت می‌تواند حاوی دستوراتی باشد که باعث اجرای کد مخرب یا افشای اطلاعات شود. همچنین خطاهای ساختاری در پرامپت (مانند قالب نادرست JSON) باعث خطای parsing در سمت مدل می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک لایه validation به oversight_strong_prompt اضافه کنید: (1) بررسی وجود تمام فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است، کلیدهای مورد انتظار را بررسی کند)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک (مثلاً 'ignore previous instructions').

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
  - بررسی وضعیت موجود فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm
  - اضافه کردن اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt — اضافه کردن اعتبارسنجی فیلدهای اجباری title, user_goal, description
  - اعتبارسنجی قالب target_locations (بررسی کلیدهای مورد انتظار در List[Dict]) — اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict])
  - اضافه کردن محدودیت طول پرامپت (max length check) — اضافه کردن محدودیت طول پرامپت (max length check)
  - فیلتر کردن دستورات خطرناک (مانند 'ignore previous instructions') در پرامپت — فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'
  - نوشتن تست‌های واحد برای هر چهار لایه validation — نوشتن تست‌های واحد برای هر چهار لایه validation
  - ثبت کامیت‌ها و نوشتن PR description با checklist — ثبت کامیت‌ها و نوشتن PR description با checklist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 9 از 16
  id: 00c2f0ef-15a2-400a-a082-6123f8af075f
  عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "fallback", "error handling", "retry"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "fallback", "oversight_strong_prompt"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why"], "files_hint": [".github/pull_request_template.md"]}]

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
[منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt

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

در حالی که ai_manager دارای قابلیت fallback و load balancing است، oversight_strong_prompt هیچ مکانیزم fallback یا error handling برای زمانی که مدل خارجی (Cursor, ChatGPT) پاسخ نمی‌دهد یا خطا می‌دهد، ندارد.

## 💥 پیامد (impact)
اگر مدل خارجی در دسترس نباشد یا timeout رخ دهد، کل pipeline بدون هیچ تلاشی برای بازیابی (retry, fallback به مدل دیگر) از کار می‌افتد. این باعث تجربه کاربری ضعیف و از دست رفتن درخواست‌ها می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک لایه error handling به oversight_strong_prompt اضافه کنید: (1) retry با backoff، (2) fallback به یک مدل جایگزین (مثلاً از طریق ai_manager)، (3) ثبت خطا و بازگشت یک پاسخ پیش‌فرض (graceful degradation).

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
  - بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager — بررسی و مستندسازی کامل وضعیت فعلی دو سرویس
  - اضافه کردن مکانیزم Retry با Exponential Backoff به oversight_strong_prompt — پیاده‌سازی کامل retry با exponential backoff
  - اضافه کردن مکانیزم Fallback به مدل جایگزین از طریق ai_manager — اضافه کردن fallback به مدل جایگزین از طریق ai_manager
  - اضافه کردن ثبت خطا (Logging) و Graceful Degradation (بازگشت پاسخ پیش‌فرض) — اضافه کردن logging جامع و graceful degradation
  - نوشتن تست‌های واحد (Unit Tests) برای مکانیزم‌های جدید — نوشتن unit tests برای retry, fallback, graceful degradation
  - نوشتن تست‌های یکپارچه‌سازی (Integration Tests) برای کل pipeline — نوشتن integration test برای کل pipeline ai_llm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 10 از 16
  id: 24c9a57c-11ab-4b6f-926a-eed002719525
  عنوان اصلی: [Effectiveness] فقدان معیارهای عملکردی برای انتخاب هوشمند مدل
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["latency", "cost", "outcome target", "measurable"], "files_hint": ["docs/", "README.md", "requirements.md"]}]
  - کد تغییر کرد تا outcome target محقق شود [verify_method=static] [verify_plan={"grep_patterns": ["weighted_selection", "performance_history", "latency", "cost"], "files_hint": ["backend/app/ai_manager.py"]}]
  - test E2E که outcome را اندازه می‌گیرد عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_manager.py::test_e2e_outcome_improvement", "timeout_seconds": 120}]
  - metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد [verify_method=static] [verify_plan={"grep_patterns": ["metric", "log", "latency", "cost", "outcome_rate"], "files_hint": ["backend/app/ai_manager.py", "backend/app/logging_config.py"]}]

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
[Effectiveness] فقدان معیارهای عملکردی برای انتخاب هوشمند مدل

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
پس از پیاده‌سازی، latency پاسخ‌دهی AI باید حداقل ۲۰٪ کاهش یابد و هزینه API حداقل ۱۵٪ کمتر شود

## 📊 وضعیت فعلی
هیچ metricی برای latency یا cost در outcome data وجود ندارد - انتخاب مدل صرفاً بر اساس availability است

## 🛠 اقدام پیشنهادی
اضافه کردن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - اضافه کردن logging latency و cost به ai_manager — اضافه کردن logging latency و cost به ai_manager
  - ایجاد dataclass برای performance history — ایجاد dataclass برای performance history
  - پیاده‌سازی weighted selection بر اساس performance history — پیاده‌سازی weighted selection بر اساس performance history
  - اضافه کردن metric/log برای outcome rate در production — اضافه کردن metric/log برای outcome rate در production
  - نوشتن تست E2E برای اندازه‌گیری outcome — نوشتن تست E2E برای اندازه‌گیری outcome
  - بازنویسی outcome target به صورت measurable — بازنویسی outcome target به صورت measurable
  - بررسی و اصلاح کد برای تحقق outcome target — بررسی و اصلاح کد برای تحقق outcome target
  - اجرای linter و type-check و رفع مشکلات — اجرای linter و type-check و رفع مشکلات
  - اجرای تمام تست‌ها و اطمینان از عبور همه — اجرای تمام تست‌ها و اطمینان از عبور همه

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 11 از 16
  id: 6c68405b-9f9d-4d4c-9826-a2dae60d008e
  عنوان اصلی: [منطق] عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["system_prompts.*format", "format_prompt.*model", "OpenAI.*system.*message", "Claude.*format"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format_prompt_for_model", "model_specific_prompt"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
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
[منطق] عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts

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

سرویس system_prompts پرامپت‌های سیستم را مدیریت می‌کند، اما مشخص نیست که آیا این پرامپت‌ها برای مدل‌های مختلف (OpenAI vs Claude) فرمت‌بندی می‌شوند یا خیر. هر مدل ممکن است به ساختار پرامپت متفاوتی نیاز داشته باشد (مثلاً system vs user message در OpenAI، یا format خاص در Claude). اگر پرامپت‌ها به صورت generic ذخیره شوند، ممکن است با مدل خاصی سازگار نباشند.

## 💥 پیامد (impact)
پرامپت‌های سیستم به درستی توسط مدل تفسیر نمی‌شوند. کاهش کیفیت پاسخ‌ها. افزایش خطاهای parsing در سمت مدل.

## 🛠 پیشنهاد رفع اولیه
یک لایه adapter در prompt_helper یا ai_manager اضافه کنید که پرامپت‌های generic را بر اساس مدل هدف به فرمت مناسب تبدیل کند. همچنین می‌توانید پرامپت‌ها را با metadata مربوط به مدل‌های سازگار ذخیره کنید.

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
  - بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline — بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline
  - تعریف ساختار داده (dataclass) برای PromptTemplate با پشتیبانی از مدل‌های مختلف — تعریف dataclass PromptTemplate با پشتیبانی از مدل‌ها
  - ایجاد لایه adapter برای تبدیل پرامپت generic به فرمت OpenAI — ایجاد adapter برای تبدیل پرامپت generic به فرمت OpenAI
  - ایجاد لایه adapter برای تبدیل پرامپت generic به فرمت Claude — ایجاد adapter برای تبدیل پرامپت generic به فرمت Claude
  - یکپارچه‌سازی adapterها در ai_manager برای انتخاب خودکار فرمت بر اساس مدل — یکپارچه‌سازی adapterها در ai_manager برای انتخاب خودکار فرمت
  - به‌روزرسانی ذخیره‌سازی system_prompts برای پشتیبانی از metadata مدل — به‌روزرسانی ذخیره‌سازی system_prompts برای metadata مدل
  - نوشتن تست‌های واحد (unit tests) برای adapterهای OpenAI و Claude — نوشتن unit tests برای adapterهای OpenAI و Claude
  - نوشتن تست‌های integration برای ai_manager با adapterهای یکپارچه‌شده — نوشتن integration tests برای ai_manager با adapterها
  - بررسی نهایی و مستندسازی تغییرات (audit) — بررسی نهایی و مستندسازی تغییرات (audit)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 12 از 16
  id: 26ddcbca-dc7c-4c14-a888-5b366b283fc6
  عنوان اصلی: [منطق] عدم وجود مکانیزم Hallucination Guard در pipeline
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["hallucination guard", "grounding", "fact.checking", "self.consistency"], "files_hint": ["backend/app/pipelines/ai_llm.py", "backend/app/pipelines/ai_llm/*.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "grounding"], "files_hint": ["backend/app/pipelines/ai_llm.py", "backend/app/pipelines/ai_llm/*.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_pipelines/test_ai_llm.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["hallucination guard", "grounding", "fact.checking", "self.consistency"], "files_hint": ["PR description"]}]

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
[منطق] عدم وجود مکانیزم Hallucination Guard در pipeline

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

در هیچ‌کدام از کامپوننت‌ها به مکانیزم‌های کاهش توهم (hallucination guard) اشاره نشده است. با توجه به اینکه pipeline با مدل‌های زبانی بزرگ کار می‌کند، عدم وجود چنین مکانیزمی (مانند grounding, fact-checking, یا self-consistency) می‌تواند منجر به تولید اطلاعات نادرست شود.

## 💥 پیامد (impact)
خروجی‌های نادرست و گمراه‌کننده برای کاربران. کاهش اعتماد به سیستم. ریسک‌های قانونی و اخلاقی.

## 🛠 پیشنهاد رفع اولیه
یک ماژول hallucination guard به ai_manager اضافه کنید. این ماژول می‌تواند شامل: 1) grounding پاسخ‌ها به منابع معتبر (در صورت وجود)، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین باشد.

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
  - بررسی و شناسایی وضعیت فعلی pipeline ai_llm و کامپوننت‌های مرتبط — بررسی و شناسایی کامل pipeline ai_llm و کامپوننت‌های مرتبط انجام نشده
  - ایجاد ماژول پایه HallucinationGuard در ai_manager — ماژول پایه HallucinationGuard در ai_manager ایجاد نشده
  - پیاده‌سازی مکانیزم Grounding (اتصال به منابع معتبر) — مکانیزم Grounding پیاده‌سازی نشده
  - پیاده‌سازی مکانیزم Fact-Checking با مدل دوم — مکانیزم Fact-Checking با مدل دوم پیاده‌سازی نشده
  - پیاده‌سازی مکانیزم تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین — مکانیزم تشخیص و پرچم‌گذاری پاسخ‌های کم‌اعتماد پیاده‌سازی نشده
  - یکپارچه‌سازی HallucinationGuard در pipeline اصلی ai_llm — یکپارچه‌سازی HallucinationGuard در pipeline ai_llm انجام نشده
  - نوشتن تست‌های واحد (Unit Tests) برای ماژول HallucinationGuard — تست‌های واحد برای HallucinationGuard نوشته نشده
  - نوشتن تست‌های یکپارچه‌سازی (Integration Tests) برای pipeline اصلاح‌شده — تست‌های یکپارچه‌سازی برای pipeline اصلاح‌شده نوشته نشده
  - بازبینی نهایی و مستندسازی (Audit & Documentation) — بازبینی نهایی و مستندسازی انجام نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 13 از 16
  id: 3269802a-8316-4245-a7c6-ccebee7a7573
  عنوان اصلی: [منطق] عدم تطابق نوع داده target_locations بین دو کامپوننت
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[Dict\\]", "List\\[str\\]"], "files_hint": ["backend/app/ai_llm/oversight_strong_prompt.py", "backend/app/ai_llm/ai_manager.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[str\\]", "List\\[Dict\\]"], "files_hint": ["backend/app/ai_llm/oversight_strong_prompt.py", "backend/app/ai_llm/ai_manager.py"]}]
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
[منطق] عدم تطابق نوع داده target_locations بین دو کامپوننت

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

oversight_strong_prompt ورودی target_locations را به صورت 'List[Dict] or List[str], optional' تعریف کرده است. اما هیچ مشخص نیست که ai_manager یا سایر مصرف‌کنندگان این خروجی چه فرمتی را انتظار دارند. این ابهام می‌تواند باعث خطاهای parsing در زمان اجرا شود.

## 💥 پیامد (impact)
اگر خروجی oversight_strong_prompt به مدلی ارسال شود که منتظر یک فرمت خاص (مثلاً فقط List[str]) است، مدل ممکن است دچار خطا شود یا خروجی نادرست تولید کند. همچنین در صورت استفاده از target_locations در pipelineهای downstream، عدم تطابق نوع داده باعث crash می‌شود.

## 🛠 پیشنهاد رفع اولیه
نوع داده target_locations را به یک فرمت واحد و مشخص محدود کنید (مثلاً فقط List[Dict] با کلیدهای استاندارد مانند 'path', 'type'). اگر نیاز به پشتیبانی از هر دو فرمت است، یک تابع normalize در ابتدای oversight_strong_prompt اضافه کنید که ورودی را به فرمت استاندارد تبدیل کند.

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
  - بررسی و شناسایی دقیق فایل‌های مرتبط با pipeline ai_llm و تعریف target_locations — شناسایی فایل‌های مرتبط با pipeline ai_llm و target_locations
  - تعریف یک نوع داده واحد و استاندارد برای target_locations (مثلاً List[Dict]) — تعریف نوع داده واحد برای target_locations
  - به‌روزرسانی امضای تابع oversight_strong_prompt برای استفاده از نوع داده استاندارد — به‌روزرسانی امضای oversight_strong_prompt
  - به‌روزرسانی مصرف‌کننده ai_manager برای پذیرش نوع داده استاندارد target_locations — به‌روزرسانی ai_manager برای نوع استاندارد
  - به‌روزرسانی سایر مصرف‌کنندگان downstream target_locations (در صورت وجود) — به‌روزرسانی سایر مصرف‌کنندگان downstream
  - نوشتن تست‌های واحد برای تابع normalize در oversight_strong_prompt — نوشتن تست واحد برای تابع normalize
  - نوشتن تست‌های یکپارچه‌سازی برای جریان کامل (oversight_strong_prompt → ai_manager) — نوشتن تست یکپارچه‌سازی جریان کامل
  - بررسی و به‌روزرسانی مستندات مرتبط با target_locations و pipeline ai_llm — به‌روزرسانی مستندات مرتبط

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 14 از 16
  id: 8e8ae8e3-b115-4957-bc7b-00be1c69bd5b
  عنوان اصلی: [منطق] عدم وضوح در مسیر تعامل بین ai_manager و models_registry
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["models_registry", "ai_manager"], "files_hint": ["backend/app/core/ai_manager.py", "backend/app/core/models_registry.py", "docs/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align"], "files_hint": ["backend/app/core/ai_manager.py", "backend/app/core/models_registry.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision"], "files_hint": [".github/pull_request_template.md"]}]

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
[منطق] عدم وضوح در مسیر تعامل بین ai_manager و models_registry

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

مستندات ai_manager اشاره دارد که با 'backend/app/core/models_registry.py' تعامل دارد، اما مشخص نیست که این تعامل به چه صورت است. آیا models_registry یک دیتابیس محلی است؟ یک API خارجی؟ آیا کش دارد؟ این ابهام می‌تواند منجر به وابستگی‌های پنهان و خطاهای runtime شود.

## 💥 پیامد (impact)
اگر models_registry در دسترس نباشد یا پاسخ نادرست بدهد، ai_manager ممکن است مدل‌های نامعتبر انتخاب کند یا fallback به درستی کار نکند. همچنین تست و دیباگ این بخش دشوار می‌شود.

## 🛠 پیشنهاد رفع اولیه
رابط (interface) بین ai_manager و models_registry را به صورت صریح مستند کنید: متدهای فراخوانی شده، نوع بازگشتی، و رفتار در صورت خطا. یک mock یا stub برای تست این تعامل ایجاد کنید.

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
  - بررسی و مستندسازی موجودیت فعلی models_registry.py — بررسی و مستندسازی کامل ساختار models_registry.py انجام نشده
  - بررسی و مستندسازی تعامل ai_manager با models_registry — مستندسازی تعامل ai_manager با models_registry انجام نشده
  - طراحی و پیاده‌سازی interface صریح برای models_registry — interface صریح برای models_registry طراحی و پیاده‌سازی نشده
  - ایجاد mock/stub برای models_registry بر اساس interface — mock/stub برای models_registry ایجاد نشده
  - به‌روزرسانی ai_manager برای استفاده از interface صریح — ai_manager برای استفاده از interface صریح به‌روزرسانی نشده
  - نوشتن تست‌های unit برای ai_manager با استفاده از mock — تست‌های unit برای ai_manager با mock نوشته نشده
  - به‌روزرسانی مستندات پروژه (README یا docs) درباره interface — مستندات پروژه درباره interface به‌روزرسانی نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 15 از 16
  id: ad0a47f0-302a-4a79-a8a3-728263db2ae7
  عنوان اصلی: [Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["error_rate_30d", "target.*2.*3.*%", "outcome.*target"], "files_hint": ["docs/", "README.md", "*.md"]}]
  - کد تغییر کرد تا outcome target محقق شود [verify_method=static] [verify_plan={"grep_patterns": ["ai_manager", "fallback", "timeout", "connection.*error", "openai.*exception"], "files_hint": ["backend/app/ai_manager.py", "backend/app/"]}]
  - test E2E که outcome را اندازه می‌گیرد عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_manager.py::test_fallback_on_timeout", "timeout_seconds": 60}]
  - metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد [verify_method=static] [verify_plan={"grep_patterns": ["error_rate_30d", "metric", "log.*error_rate", "prometheus.*error"], "files_hint": ["backend/app/metrics.py", "backend/app/logging_config.py"]}]

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
[Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
سیستم باید حداقل ۲-۳٪ خطاهای کنترل‌شده در شرایط مرزی (مثلاً timeout سرویس AI) ثبت کند تا اطمینان حاصل شود fallback mechanism به درستی فعال می‌شود

## 📊 وضعیت فعلی
error_rate_30d: 0.0% - هیچ خطایی ثبت نشده است که می‌تواند به دلیل عدم تست سناریوهای شکست سرویس‌های AI باشد

## 🛠 اقدام پیشنهادی
افزودن تست‌های سناریوی شکست برای ai_manager (مثلاً قطع connection به OpenAI) و بررسی فعال شدن fallback به مدل جایگزین

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و تحلیل وضعیت فعلی ai_manager و fallback mechanism — بررسی و تحلیل کامل ai_manager و fallback mechanism انجام نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (قطع connection به OpenAI) — سناریوی قطع connection به OpenAI پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (timeout سرویس AI) — سناریوی timeout سرویس AI پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (خطای authentication/API key نامعتبر) — سناریوی خطای authentication/API key نامعتبر پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (خطای rate limit) — سناریوی خطای rate limit پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (خطای invalid response format از سرویس AI) — سناریوی invalid response format پیاده‌سازی نشده
  - افزودن metric/log برای ثبت نرخ خطا در production — metric/log برای ثبت نرخ خطا در production اضافه نشده
  - نوشتن تست E2E که outcome target را اندازه می‌گیرد — تست E2E برای اندازه‌گیری outcome target نوشته نشده
  - بازنویسی outcome target به صورت measurable و اضافه کردن به documentation — outcome target به صورت measurable بازنویسی و به documentation اضافه نشده
  - اجرای تست‌ها و بررسی عدم شکست تست‌های موجود — تست‌ها اجرا نشده و عدم شکست تست‌های موجود بررسی نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 16 از 16
  id: 12fad3ca-ab80-47f9-8389-de33d7265161
  عنوان اصلی: [Effectiveness] عدم یکپارچگی بین oversight_service و project_journal API
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["outcome target", "measurable", "effectiveness"], "files_hint": ["README.md", "docs/"]}]
  - کد تغییر کرد تا outcome target محقق شود [verify_method=static] [verify_plan={"grep_patterns": ["webhook", "oversight_service", "project_journal"], "files_hint": ["backend/app/project_journal/"]}]
  - test E2E که outcome را اندازه می‌گیرد عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_integration/test_oversight_journal_sync.py::test_e2e_outcome", "timeout_seconds": 120}]
  - metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد [verify_method=static] [verify_plan={"grep_patterns": ["metric", "log", "outcome_rate", "oversight_sync_count"], "files_hint": ["backend/app/oversight_service/", "backend/app/project_journal/"]}]

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
[Effectiveness] عدم یکپارچگی بین oversight_service و project_journal API

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
پس از یکپارچگی، ۱۰۰٪ ژورنال‌های پروژه باید به صورت خودکار در oversight_service ذخیره شوند و قابلیت جستجوی full-text داشته باشند

## 📊 وضعیت فعلی
project_journal API مستقل عمل می‌کند و هیچ اشاره‌ای به oversight_service در outcome data دیده نمی‌شود

## 🛠 اقدام پیشنهادی
اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی وضعیت فعلی یکپارچگی بین project_journal و oversight_service در مخزن — بررسی کامل وضعیت یکپارچگی در مخزن انجام نشده
  - ایجاد مدل داده (dataclass/schema) برای گزارش ژورنال در project_journal — مدل داده (schema) برای گزارش ژورنال در project_journal ایجاد نشده
  - ایجاد endpoint دریافت گزارش در oversight_service — endpoint POST برای دریافت گزارش در oversight_service ایجاد نشده
  - پیاده‌سازی ذخیره‌سازی گزارش‌ها در oversight_service (JSON-based) — ذخیره‌سازی JSON-based گزارش‌ها در oversight_service پیاده‌سازی نشده
  - ایجاد webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service — webhook در project_journal برای ارسال خودکار گزارش ایجاد نشده
  - پیاده‌سازی full-text search بر روی گزارش‌های ذخیره شده در oversight_service — full-text search بر روی گزارش‌ها پیاده‌سازی نشده
  - اضافه کردن metric/log در project_journal برای اندازه‌گیری نرخ ارسال موفق گزارش‌ها — metric/log برای نرخ ارسال موفق گزارش اضافه نشده
  - نوشتن تست E2E برای یکپارچگی project_journal و oversight_service — تست E2E برای یکپارچگی نوشته نشده
  - نوشتن تست‌های unit برای webhook در project_journal — تست‌های unit برای webhook در project_journal نوشته نشده
  - نوشتن تست‌های unit برای endpoint دریافت گزارش در oversight_service — تست‌های unit برای endpoint دریافت گزارش در oversight_service نوشته نشده
  - نوشتن تست‌های unit برای full-text search در oversight_service — تست‌های unit برای full-text search نوشته نشده
  - اجرای linter و type-checker و رفع مشکلات — linter و type-checker اجرا و رفع مشکلات نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 5569212c-b3f9-4361-a155-dbd45d88a002, f023ba69-7294-4337-abd4-14a8d6093db6, 4816a520-a370-4e87-9005-a42ff9615257, c159181f-ebc5-427e-8ead-118d56dacae5, 0147715a-b178-44a6-89c5-bb4b36742c45, c81ec6af-6080-448e-89f4-7da379cf1d76, 4e23a1de-5d9d-4e09-9481-07c040f17f29, aa8c1673-2357-40d4-9088-2e28a2c5eb7b, 00c2f0ef-15a2-400a-a082-6123f8af075f, 24c9a57c-11ab-4b6f-926a-eed002719525, 6c68405b-9f9d-4d4c-9826-a2dae60d008e, 26ddcbca-dc7c-4c14-a888-5b366b283fc6, 3269802a-8316-4245-a7c6-ccebee7a7573, 8e8ae8e3-b115-4957-bc7b-00be1c69bd5b, ad0a47f0-302a-4a79-a8a3-728263db2ae7, 12fad3ca-ab80-47f9-8389-de33d7265161`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند

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


---

## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)
_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند.)_

```
🧬 این یک تسک تلفیقی است — از 16 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 19، 21، 22، 23، 24، 28، 30، 31، 32، 34، 35، 36، 37، 39 همگی به بهبود منطق، validation، fallback، و یکپارچگی در pipeline AI (ai_manager، oversight_strong_prompt، models_registry) مربوط می‌شوند. تسک 38 (partial) نیز به OversightService مرتبط است.
🎯 theme: بهبود و استانداردسازی pipeline AI (ai_manager و oversight)
💎 estimated_difficulty: large

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 16
  id: 5569212c-b3f9-4361-a155-dbd45d88a002
  عنوان اصلی: [منطق] عدم وجود validation بر روی پاسخ AI در ai_manager
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["nassazegi.*ai_manager.*validation", "ai_manager.*output.*parser", "ai_manager.*hallucination"], "files_hint": ["docs/", "backend/app/ai_manager/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground.truth", "align", "ai_manager.*validation.*implement"], "files_hint": ["docs/", "backend/app/ai_manager/"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR.*description", "decision.*why", "validation.*ai_manager"], "files_hint": [".github/PULL_REQUEST_TEMPLATE.md", "docs/"]}]

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
[منطق] عدم وجود validation بر روی پاسخ AI در ai_manager

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

در مستندات ai_manager اشاره‌ای به validation خروجی مدل‌های AI نشده است. با توجه به اینکه این سرویس مدیریت مرکزی سرویس‌های AI را بر عهده دارد و با مدل‌های مختلف (OpenAI, Claude) کار می‌کند، عدم وجود validation می‌تواند منجر به پردازش پاسخ‌های ناقص، نادرست یا دارای توهم (hallucination) شود. همچنین مشخص نیست که آیا output parser خاصی برای تطبیق خروجی مدل با فرمت مورد انتظار downstream services وجود دارد یا خیر.

## 💥 پیامد (impact)
پاسخ‌های نادرست یا ناقص به کاربر نهایی ارسال می‌شود. خطاهای زنجیره‌ای در pipeline به دلیل عدم تطابق فرمت خروجی. افزایش ریسک توهم (hallucination) در پاسخ‌های AI.

## 🛠 پیشنهاد رفع اولیه
یک لایه validation و output parser به ai_manager اضافه کنید. برای هر مدل، یک validator مخصوص (مثلاً Pydantic model) تعریف کنید که ساختار و محتوای پاسخ را بررسی کند. از تکنیک‌های grounding و fact-checking برای کاهش توهم استفاده کنید.

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
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
  - تعریف Pydantic models برای validation ساختار پاسخ مدل‌های AI — تعریف Pydantic models برای validation ساختار پاسخ مدل‌های AI
  - پیاده‌سازی output parser برای تطبیق خروجی مدل با فرمت مورد انتظار downstream services — پیاده‌سازی output parser برای تطبیق خروجی مدل با فرمت downstream
  - پیاده‌سازی grounding و fact-checking اولیه برای کاهش توهم (hallucination) — پیاده‌سازی grounding و fact-checking اولیه برای کاهش توهم
  - یکپارچه‌سازی validator، output parser و grounding service در pipeline اصلی ai_manager — یکپارچه‌سازی validator, output parser و grounding در pipeline اصلی
  - نوشتن تست‌های واحد (unit tests) برای validator و output parser — نوشتن unit tests برای validator و output parser
  - نوشتن تست‌های واحد (unit tests) برای grounding service — نوشتن unit tests برای grounding service
  - نوشتن تست‌های یکپارچه‌سازی (integration tests) برای کل pipeline ai_manager — نوشتن integration tests برای کل pipeline ai_manager
  - به‌روزرسانی مستندات ai_manager برای انعکاس قابلیت‌های جدید — به‌روزرسانی مستندات ai_manager برای قابلیت‌های جدید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 16
  id: f023ba69-7294-4337-abd4-14a8d6093db6
  عنوان اصلی: [منطق] عدم تطابق ورودی‌های مورد انتظار ai_manager با خروجی‌های oversight_strong_prompt
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ai_manager.*expect.*user.*prompt", "oversight_strong_prompt.*executive.*prompt"], "files_hint": ["backend/app/ai_manager.py", "backend/app/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth.*align", "align.*oversight_strong_prompt"], "files_hint": ["backend/app/ai_manager.py", "backend/app/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_pipeline_integration", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["why.*decision.*made", "reason.*align"], "files_hint": ["PR description"]}]

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
[منطق] عدم تطابق ورودی‌های مورد انتظار ai_manager با خروجی‌های oversight_strong_prompt

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

ai_manager انتظار 'پرامپت کاربر (string)' را به عنوان ورودی دارد، در حالی که oversight_strong_prompt یک پرامپت اجرایی کامل و ساختاریافته (با قالب ثابت) تولید می‌کند. این دو با هم ناسازگار هستند: ai_manager برای پردازش یک پرامپت خام کاربر طراحی شده، اما خروجی builder یک پرامپت نهایی و آماده اجراست که احتمالاً باید مستقیماً به مدل ارسال شود، نه اینکه دوباره از ai_manager عبور کند.

## 💥 پیامد (impact)
اگر خروجی oversight_strong_prompt به ai_manager داده شود، ai_manager ممکن است آن را به عنوان یک پرامپت ساده تفسیر کرده و دوباره پردازش کند (مثلاً انتخاب مدل یا fallback) که منجر به نادیده گرفتن ساختار دقیق پرامپت، افزایش هزینه، تأخیر و احتمالاً خرابی خروجی نهایی می‌شود.

## 🛠 پیشنهاد رفع اولیه
مسیر جریان داده را شفاف کنید. یا ai_manager باید بتواند پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد، یا یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده (مانند خروجی oversight_strong_prompt) ایجاد کنید که مستقیماً به سرویس مدل ارسال شوند.

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
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و تحلیل ساختار فعلی pipeline ai_llm — بررسی و تحلیل ساختار فعلی pipeline ai_llm انجام نشده
  - طراحی مسیر bypass برای پرامپت‌های ساختاریافته — طراحی مسیر bypass برای پرامپت‌های ساختاریافته انجام نشده
  - پیاده‌سازی مکانیزم تشخیص پرامپت ساختاریافته — مکانیزم تشخیص پرامپت ساختاریافته پیاده‌سازی نشده
  - اصلاح ai_manager برای عبور دادن پرامپت‌های ساختاریافته بدون تغییر — ai_manager اصلاح نشده برای عبور پرامپت‌های ساختاریافته
  - ایجاد مسیر bypass مستقیم برای پرامپت‌های ساختاریافته (گزینه دوم) — مسیر bypass مستقیم ایجاد نشده
  - به‌روزرسانی oversight_strong_prompt برای استفاده از مسیر bypass — oversight_strong_prompt به‌روزرسانی نشده
  - نوشتن تست‌های واحد برای مکانیزم تشخیص پرامپت — تست‌های واحد برای تشخیص پرامپت نوشته نشده
  - نوشتن تست‌های واحد برای ai_manager اصلاح شده — تست‌های واحد برای ai_manager اصلاح‌شده نوشته نشده
  - نوشتن تست‌های integration برای مسیر bypass — تست‌های integration برای مسیر bypass نوشته نشده
  - انجام audit نهایی و مستندسازی تغییرات — audit نهایی و مستندسازی انجام نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 16
  id: 4816a520-a370-4e87-9005-a42ff9615257
  عنوان اصلی: OversightService فاقد تست واحد است — ۲۰ فایل به آن وابسته‌اند
  اولویت اصلی: critical
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/services/oversight_service.py

📋 acceptance_criteria کامل:
  - تست CRUD برای watched projects (add, update, delete, list) [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_crud_watched_projects", "timeout_seconds": 60}]
  - تست scheduler loop با mock کردن sleep [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_scheduler_loop_mock_sleep", "timeout_seconds": 60}]
  - تست auto_register_watched با mock GitHub API [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_auto_register_watched_mock_github", "timeout_seconds": 60}]
  - تست edge cases: duplicate repo, invalid URL, empty fields [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_edge_cases", "timeout_seconds": 60}]

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
OversightService فاقد تست واحد است — ۲۰ فایل به آن وابسته‌اند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-100` — `OversightService` — کلاس اصلی که باید تست شود
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self._lock = asyncio.Lock()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + asyncio + GitHub API

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 12) — API routes که از OversightService استفاده می‌کنند
- `backend/app/main.py` (سطر 93) — lifespan که scheduler را راه‌اندازی می‌کند
- `backend/app/api/routes/github_import.py` (سطر 162) — از auto_register_watched استفاده می‌کند
- `backend/app/core/database.py` — `oversight_service.py` این فایل را import می‌کند
- `backend/app/models/setting.py` — `oversight_service.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/__init__.py` — `oversight_service.py` این فایل را import می‌کند
- `backend/app/services/ai_manager.py` — `oversight_service.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
۲۰ فایل به این سرویس وابسته‌اند: ۵ route, ۱۰ service, ۳ core, main.py, ۱ script

## 🔍 Context و وضعیت فعلی
سرویس `oversight_service.py` هستهٔ مرکزی نظارت پروژه‌های GitHub است و ۲۰ فایل مختلف (routes, services, main.py) به آن import دارند. این سرویس شامل منطق پیچیدهٔ مدیریت watched projects, scheduling, runtime verification, و auto-register است. عدم وجود تست می‌تواند منجر به شکست‌های زنجیره‌ای در کل سیستم شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست CRUD برای watched projects (add, update, delete, list)
- [ ] تست scheduler loop با mock کردن sleep
- [ ] تست auto_register_watched با mock GitHub API
- [ ] تست edge cases: duplicate repo, invalid URL, empty fields
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register

## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v`
- `pytest backend/tests/ --cov=app.services.oversight_service`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در OversightService بدون تست می‌تواند کل سیستم نظارت را مختل کند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: large

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 16
  id: c159181f-ebc5-427e-8ead-118d56dacae5
  عنوان اصلی: [منطق] عدم وجود permission check در auth pipeline
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ناسازگاری", "permission", "authorization", "auth pipeline"], "files_hint": ["docs/", "README.md", "*.md"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "permission check", "authorization"], "files_hint": ["docs/", "*.md"]}]
  - integration test برای pipeline `auth` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_auth_pipeline.py", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "چرا این تصمیم گرفته شد", "reason", "rationale"], "files_hint": ["docs/", "*.md"]}]

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
[منطق] عدم وجود permission check در auth pipeline

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline auth است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `auth` یک ناسازگاری منطقی پیدا شد:

در مستندات ارائه شده، هیچ اشاره‌ای به مکانیزم permission یا authorization در pipeline احراز هویت نشده است. تمام مسیرهای mutation (مانند ذخیره سشن‌ها و پیام‌ها در inspector_session) بدون عبور از یک لایه permission check قابل دسترسی هستند.

## 💥 پیامد (impact)
هر کاربر احراز هویت شده (یا حتی کاربران غیرمجاز در صورت عدم احراز هویت) می‌توانند داده‌های حساس مانند سشن‌های بازرس را تغییر دهند یا ایجاد کنند. این منجر به نقض امنیت و یکپارچگی داده‌ها می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک middleware یا dependency برای بررسی permission قبل از هر mutation اضافه کنید. اطمینان حاصل کنید که کاربر فقط مجوز تغییر سشن‌های متعلق به خود یا سشن‌هایی که مجوز لازم را دارد، داشته باشد.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `auth` بدون شکست عبور می‌کند
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
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و شناسایی فایل‌های موجود در pipeline auth و مسیرهای mutation — بررسی و شناسایی فایل‌های موجود در pipeline auth و مسیرهای mutation
  - طراحی و پیاده‌سازی middleware/dependency پایه برای permission check — طراحی و پیاده‌سازی middleware/dependency پایه برای permission check
  - تعریف permissionهای مورد نیاز برای inspector_session (ایجاد، ویرایش، حذف) — تعریف permissionهای مورد نیاز برای inspector_session
  - اعمال permission check بر روی endpoints مربوط به ایجاد inspector_session (POST) — اعمال permission check بر روی endpoints ایجاد inspector_session (POST)
  - اعمال permission check بر روی endpoints مربوط به ویرایش inspector_session (PUT/PATCH) — اعمال permission check بر روی endpoints ویرایش inspector_session (PUT/PATCH)
  - اعمال permission check بر روی endpoints مربوط به حذف inspector_session (DELETE) — اعمال permission check بر روی endpoints حذف inspector_session (DELETE)
  - اعمال permission check بر روی endpoints مربوط به پیام‌های inspector_session (POST برای ایجاد پیام) — اعمال permission check بر روی endpoints ایجاد پیام inspector_session (POST)
  - اعمال permission check بر روی endpoints مربوط به ویرایش پیام‌های inspector_session (PUT/PATCH) — اعمال permission check بر روی endpoints ویرایش پیام inspector_session (PUT/PATCH)
  - اعمال permission check بر روی endpoints مربوط به حذف پیام‌های inspector_session (DELETE) — اعمال permission check بر روی endpoints حذف پیام inspector_session (DELETE)
  - نوشتن تست‌های unit برای middleware/dependency permission check — نوشتن تست‌های unit برای middleware/dependency permission check
  - نوشتن تست‌های integration برای endpoints inspector_session با permission check — نوشتن تست‌های integration برای endpoints inspector_session با permission check
  - نوشتن تست‌های integration برای endpoints پیام‌های inspector_session با permission check — نوشتن تست‌های integration برای endpoints پیام‌های inspector_session با permission check
  - بررسی و رفع coherence issues (feature flag rot یا refactor ناتمام) در pipeline auth — بررسی و رفع coherence issues در pipeline auth
  - مستندسازی تغییرات انجام شده و به‌روزرسانی README یا مستندات API — مستندسازی تغییرات و به‌روزرسانی README یا مستندات API

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 16
  id: 0147715a-b178-44a6-89c5-bb4b36742c45
  عنوان اصلی: [منطق] عدم تطابق بین task_type و قابلیت‌های مدل در انتخاب هوشمند
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ناسازگاری", "شناسایی", "هایشان", "مستند"], "files_hint": []}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground", "truth", "align", "تعیین", "دیگر"], "files_hint": []}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["integration", "pipeline", "ai_llm", "برای", "بدون", "شکست", "عبور"], "files_hint": []}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["description", "توضیح", "تصمیم", "گرفته"], "files_hint": []}]

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
[منطق] عدم تطابق بین task_type و قابلیت‌های مدل در انتخاب هوشمند

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

در مستندات ai_manager، ورودی‌ها شامل 'task_type' و 'قابلیت‌های مورد نیاز (ModelCapability)' هستند، اما مشخص نیست که چگونه این دو با هم تطبیق داده می‌شوند. ممکن است یک task_type خاص به قابلیت‌های متفاوتی نیاز داشته باشد و انتخاب مدل صرفاً بر اساس task_type بدون در نظر گرفتن قابلیت‌های دقیق، نادرست باشد. همچنین ارتباط بین task_type و مدل‌های ترجیحی (preferred models) مشخص نیست.

## 💥 پیامد (impact)
انتخاب مدل نامناسب برای یک task خاص. کاهش کیفیت پاسخ‌ها. استفاده از مدل‌های گران‌تر یا کندتر برای کارهای ساده. شکست در fallback به دلیل عدم تطابق قابلیت‌ها.

## 🛠 پیشنهاد رفع اولیه
یک mapping صریح بین task_type و مجموعه‌ای از ModelCapabilityهای مورد نیاز ایجاد کنید. منطق انتخاب هوشمند را طوری طراحی کنید که ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد.

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
  - بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager — بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager
  - تعریف یک mapping صریح بین task_type و مجموعه ModelCapabilityهای مورد نیاز — تعریف mapping صریح بین task_type و ModelCapability
  - اصلاح منطق انتخاب مدل در ai_manager برای استفاده از mapping جدید — اصلاح منطق انتخاب مدل در ai_manager
  - به‌روزرسانی مستندات ai_manager برای انعکاس mapping جدید و منطق انتخاب — به‌روزرسانی مستندات ai_manager
  - نوشتن تست‌های integration برای سناریوی کامل انتخاب مدل — نوشتن تست‌های integration برای انتخاب مدل
  - بررسی و رفع مشکلات احتمالی fallback در سناریوهای لبه — بررسی و رفع مشکلات fallback

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 16
  id: c81ec6af-6080-448e-89f4-7da379cf1d76
  عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در ai_manager
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "retry", "timeout", "rate.limit", "validation.failure"], "files_hint": ["docs/", "backend/app/ai_manager.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground.truth", "align", "fallback.strategy"], "files_hint": ["docs/", "backend/app/ai_manager.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 120}]
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
[منطق] عدم وجود مکانیزم fallback مشخص در ai_manager

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

مستندات به 'مدیریت fallback' اشاره دارد، اما جزئیات آن مشخص نیست. با توجه به اینکه ai_manager با چندین سرویس (OpenAI, Claude) کار می‌کند، یک استراتژی fallback شفاف (مثلاً ترتیب fallback، timeout، تعداد تلاش مجدد) ضروری است. همچنین مشخص نیست که آیا fallback بر اساس خطاهای سرویس (مثلاً rate limit) یا کیفیت پاسخ (validation failure) انجام می‌شود.

## 💥 پیامد (impact)
در صورت خرابی یک سرویس AI، pipeline بدون fallback می‌ماند و خطا به کاربر نمایش داده می‌شود. عدم مدیریت هوشمند fallback می‌تواند منجر به افزایش latency یا هزینه شود.

## 🛠 پیشنهاد رفع اولیه
یک استراتژی fallback واضح در ai_manager پیاده‌سازی کنید: ترتیب fallback (مثلاً OpenAI -> Claude -> ...)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout).

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
  - بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
  - طراحی و پیاده‌سازی کلاس FallbackStrategy با پشتیبانی از ترتیب fallback — طراحی و پیاده‌سازی کلاس FallbackStrategy
  - پیاده‌سازی مکانیزم timeout برای هر سرویس AI — پیاده‌سازی مکانیزم timeout برای هر سرویس AI
  - پیاده‌سازی مکانیزم retry با backoff برای خطاهای موقت سرویس — پیاده‌سازی مکانیزم retry با backoff
  - تعریف شرط‌های fallback: خطای سرویس، خطای validation، timeout — تعریف شرط‌های fallback
  - یکپارچه‌سازی FallbackStrategy، timeout، retry، و شرط‌ها در ai_manager — یکپارچه‌سازی همه اجزا در ai_manager
  - افزودن logging و metrics برای fallback events — افزودن logging و metrics برای fallback
  - نوشتن unit tests برای FallbackStrategy — نوشتن unit tests برای FallbackStrategy
  - نوشتن unit tests برای timeout و retry logic — نوشتن unit tests برای timeout و retry
  - نوشتن unit tests برای FallbackCondition — نوشتن unit tests برای FallbackCondition
  - نوشتن integration tests برای fallback کامل در ai_manager — نوشتن integration tests برای fallback کامل
  - به‌روزرسانی مستندات ai_manager با استراتژی fallback — به‌روزرسانی مستندات ai_manager

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 16
  id: 4e23a1de-5d9d-4e09-9481-07c040f17f29
  عنوان اصلی: Model profiles page uses hardcoded default data instead of real backend data
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "eslint"], "files_hint": ["package.json", ".eslintrc"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["tsc", "type-check", "typescript"], "files_hint": ["tsconfig.json"]}]

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
Model profiles page uses hardcoded default data instead of real backend data

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
The `model-profiles/page.tsx` defines extensive hardcoded default profiles (lines 90-97)

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

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
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 16
  id: aa8c1673-2357-40d4-9088-2e28a2c5eb7b
  عنوان اصلی: [منطق] عدم وجود validation و guardrails در خروجی oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "oversight_strong_prompt"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/ai_llm/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["PR_description.md"]}]

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
[منطق] عدم وجود validation و guardrails در خروجی oversight_strong_prompt

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

مستندات oversight_strong_prompt هیچ اشاره‌ای به validation روی خروجی (پرامپت ساخته شده) یا مکانیزم‌های ضد توهم (hallucination guards) ندارد. با توجه به اینکه این پرامپت مستقیماً به مدل‌های خارجی (Cursor, ChatGPT) ارسال می‌شود، عدم وجود validation می‌تواند منجر به ارسال پرامپت‌های ناقص، دارای خطاهای ساختاری یا حاوی اطلاعات گمراه‌کننده شود.

## 💥 پیامد (impact)
مدل خارجی ممکن است خروجی نامرتبط، ناقص یا خطرناک تولید کند. در worst-case، پرامپت می‌تواند حاوی دستوراتی باشد که باعث اجرای کد مخرب یا افشای اطلاعات شود. همچنین خطاهای ساختاری در پرامپت (مانند قالب نادرست JSON) باعث خطای parsing در سمت مدل می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک لایه validation به oversight_strong_prompt اضافه کنید: (1) بررسی وجود تمام فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است، کلیدهای مورد انتظار را بررسی کند)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک (مثلاً 'ignore previous instructions').

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
  - بررسی وضعیت موجود فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm
  - اضافه کردن اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt — اضافه کردن اعتبارسنجی فیلدهای اجباری title, user_goal, description
  - اعتبارسنجی قالب target_locations (بررسی کلیدهای مورد انتظار در List[Dict]) — اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict])
  - اضافه کردن محدودیت طول پرامپت (max length check) — اضافه کردن محدودیت طول پرامپت (max length check)
  - فیلتر کردن دستورات خطرناک (مانند 'ignore previous instructions') در پرامپت — فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'
  - نوشتن تست‌های واحد برای هر چهار لایه validation — نوشتن تست‌های واحد برای هر چهار لایه validation
  - ثبت کامیت‌ها و نوشتن PR description با checklist — ثبت کامیت‌ها و نوشتن PR description با checklist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 9 از 16
  id: 00c2f0ef-15a2-400a-a082-6123f8af075f
  عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "fallback", "error handling", "retry"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "fallback", "oversight_strong_prompt"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why"], "files_hint": [".github/pull_request_template.md"]}]

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
[منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt

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

در حالی که ai_manager دارای قابلیت fallback و load balancing است، oversight_strong_prompt هیچ مکانیزم fallback یا error handling برای زمانی که مدل خارجی (Cursor, ChatGPT) پاسخ نمی‌دهد یا خطا می‌دهد، ندارد.

## 💥 پیامد (impact)
اگر مدل خارجی در دسترس نباشد یا timeout رخ دهد، کل pipeline بدون هیچ تلاشی برای بازیابی (retry, fallback به مدل دیگر) از کار می‌افتد. این باعث تجربه کاربری ضعیف و از دست رفتن درخواست‌ها می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک لایه error handling به oversight_strong_prompt اضافه کنید: (1) retry با backoff، (2) fallback به یک مدل جایگزین (مثلاً از طریق ai_manager)، (3) ثبت خطا و بازگشت یک پاسخ پیش‌فرض (graceful degradation).

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
  - بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager — بررسی و مستندسازی کامل وضعیت فعلی دو سرویس
  - اضافه کردن مکانیزم Retry با Exponential Backoff به oversight_strong_prompt — پیاده‌سازی کامل retry با exponential backoff
  - اضافه کردن مکانیزم Fallback به مدل جایگزین از طریق ai_manager — اضافه کردن fallback به مدل جایگزین از طریق ai_manager
  - اضافه کردن ثبت خطا (Logging) و Graceful Degradation (بازگشت پاسخ پیش‌فرض) — اضافه کردن logging جامع و graceful degradation
  - نوشتن تست‌های واحد (Unit Tests) برای مکانیزم‌های جدید — نوشتن unit tests برای retry, fallback, graceful degradation
  - نوشتن تست‌های یکپارچه‌سازی (Integration Tests) برای کل pipeline — نوشتن integration test برای کل pipeline ai_llm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 10 از 16
  id: 24c9a57c-11ab-4b6f-926a-eed002719525
  عنوان اصلی: [Effectiveness] فقدان معیارهای عملکردی برای انتخاب هوشمند مدل
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["latency", "cost", "outcome target", "measurable"], "files_hint": ["docs/", "README.md", "requirements.md"]}]
  - کد تغییر کرد تا outcome target محقق شود [verify_method=static] [verify_plan={"grep_patterns": ["weighted_selection", "performance_history", "latency", "cost"], "files_hint": ["backend/app/ai_manager.py"]}]
  - test E2E که outcome را اندازه می‌گیرد عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_manager.py::test_e2e_outcome_improvement", "timeout_seconds": 120}]
  - metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد [verify_method=static] [verify_plan={"grep_patterns": ["metric", "log", "latency", "cost", "outcome_rate"], "files_hint": ["backend/app/ai_manager.py", "backend/app/logging_config.py"]}]

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
[Effectiveness] فقدان معیارهای عملکردی برای انتخاب هوشمند مدل

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
پس از پیاده‌سازی، latency پاسخ‌دهی AI باید حداقل ۲۰٪ کاهش یابد و هزینه API حداقل ۱۵٪ کمتر شود

## 📊 وضعیت فعلی
هیچ metricی برای latency یا cost در outcome data وجود ندارد - انتخاب مدل صرفاً بر اساس availability است

## 🛠 اقدام پیشنهادی
اضافه کردن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - اضافه کردن logging latency و cost به ai_manager — اضافه کردن logging latency و cost به ai_manager
  - ایجاد dataclass برای performance history — ایجاد dataclass برای performance history
  - پیاده‌سازی weighted selection بر اساس performance history — پیاده‌سازی weighted selection بر اساس performance history
  - اضافه کردن metric/log برای outcome rate در production — اضافه کردن metric/log برای outcome rate در production
  - نوشتن تست E2E برای اندازه‌گیری outcome — نوشتن تست E2E برای اندازه‌گیری outcome
  - بازنویسی outcome target به صورت measurable — بازنویسی outcome target به صورت measurable
  - بررسی و اصلاح کد برای تحقق outcome target — بررسی و اصلاح کد برای تحقق outcome target
  - اجرای linter و type-check و رفع مشکلات — اجرای linter و type-check و رفع مشکلات
  - اجرای تمام تست‌ها و اطمینان از عبور همه — اجرای تمام تست‌ها و اطمینان از عبور همه

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 11 از 16
  id: 6c68405b-9f9d-4d4c-9826-a2dae60d008e
  عنوان اصلی: [منطق] عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["system_prompts.*format", "format_prompt.*model", "OpenAI.*system.*message", "Claude.*format"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format_prompt_for_model", "model_specific_prompt"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
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
[منطق] عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts

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

سرویس system_prompts پرامپت‌های سیستم را مدیریت می‌کند، اما مشخص نیست که آیا این پرامپت‌ها برای مدل‌های مختلف (OpenAI vs Claude) فرمت‌بندی می‌شوند یا خیر. هر مدل ممکن است به ساختار پرامپت متفاوتی نیاز داشته باشد (مثلاً system vs user message در OpenAI، یا format خاص در Claude). اگر پرامپت‌ها به صورت generic ذخیره شوند، ممکن است با مدل خاصی سازگار نباشند.

## 💥 پیامد (impact)
پرامپت‌های سیستم به درستی توسط مدل تفسیر نمی‌شوند. کاهش کیفیت پاسخ‌ها. افزایش خطاهای parsing در سمت مدل.

## 🛠 پیشنهاد رفع اولیه
یک لایه adapter در prompt_helper یا ai_manager اضافه کنید که پرامپت‌های generic را بر اساس مدل هدف به فرمت مناسب تبدیل کند. همچنین می‌توانید پرامپت‌ها را با metadata مربوط به مدل‌های سازگار ذخیره کنید.

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
  - بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline — بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline
  - تعریف ساختار داده (dataclass) برای PromptTemplate با پشتیبانی از مدل‌های مختلف — تعریف dataclass PromptTemplate با پشتیبانی از مدل‌ها
  - ایجاد لایه adapter برای تبدیل پرامپت generic به فرمت OpenAI — ایجاد adapter برای تبدیل پرامپت generic به فرمت OpenAI
  - ایجاد لایه adapter برای تبدیل پرامپت generic به فرمت Claude — ایجاد adapter برای تبدیل پرامپت generic به فرمت Claude
  - یکپارچه‌سازی adapterها در ai_manager برای انتخاب خودکار فرمت بر اساس مدل — یکپارچه‌سازی adapterها در ai_manager برای انتخاب خودکار فرمت
  - به‌روزرسانی ذخیره‌سازی system_prompts برای پشتیبانی از metadata مدل — به‌روزرسانی ذخیره‌سازی system_prompts برای metadata مدل
  - نوشتن تست‌های واحد (unit tests) برای adapterهای OpenAI و Claude — نوشتن unit tests برای adapterهای OpenAI و Claude
  - نوشتن تست‌های integration برای ai_manager با adapterهای یکپارچه‌شده — نوشتن integration tests برای ai_manager با adapterها
  - بررسی نهایی و مستندسازی تغییرات (audit) — بررسی نهایی و مستندسازی تغییرات (audit)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 12 از 16
  id: 26ddcbca-dc7c-4c14-a888-5b366b283fc6
  عنوان اصلی: [منطق] عدم وجود مکانیزم Hallucination Guard در pipeline
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["hallucination guard", "grounding", "fact.checking", "self.consistency"], "files_hint": ["backend/app/pipelines/ai_llm.py", "backend/app/pipelines/ai_llm/*.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "grounding"], "files_hint": ["backend/app/pipelines/ai_llm.py", "backend/app/pipelines/ai_llm/*.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_pipelines/test_ai_llm.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["hallucination guard", "grounding", "fact.checking", "self.consistency"], "files_hint": ["PR description"]}]

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
[منطق] عدم وجود مکانیزم Hallucination Guard در pipeline

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

در هیچ‌کدام از کامپوننت‌ها به مکانیزم‌های کاهش توهم (hallucination guard) اشاره نشده است. با توجه به اینکه pipeline با مدل‌های زبانی بزرگ کار می‌کند، عدم وجود چنین مکانیزمی (مانند grounding, fact-checking, یا self-consistency) می‌تواند منجر به تولید اطلاعات نادرست شود.

## 💥 پیامد (impact)
خروجی‌های نادرست و گمراه‌کننده برای کاربران. کاهش اعتماد به سیستم. ریسک‌های قانونی و اخلاقی.

## 🛠 پیشنهاد رفع اولیه
یک ماژول hallucination guard به ai_manager اضافه کنید. این ماژول می‌تواند شامل: 1) grounding پاسخ‌ها به منابع معتبر (در صورت وجود)، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین باشد.

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
  - بررسی و شناسایی وضعیت فعلی pipeline ai_llm و کامپوننت‌های مرتبط — بررسی و شناسایی کامل pipeline ai_llm و کامپوننت‌های مرتبط انجام نشده
  - ایجاد ماژول پایه HallucinationGuard در ai_manager — ماژول پایه HallucinationGuard در ai_manager ایجاد نشده
  - پیاده‌سازی مکانیزم Grounding (اتصال به منابع معتبر) — مکانیزم Grounding پیاده‌سازی نشده
  - پیاده‌سازی مکانیزم Fact-Checking با مدل دوم — مکانیزم Fact-Checking با مدل دوم پیاده‌سازی نشده
  - پیاده‌سازی مکانیزم تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین — مکانیزم تشخیص و پرچم‌گذاری پاسخ‌های کم‌اعتماد پیاده‌سازی نشده
  - یکپارچه‌سازی HallucinationGuard در pipeline اصلی ai_llm — یکپارچه‌سازی HallucinationGuard در pipeline ai_llm انجام نشده
  - نوشتن تست‌های واحد (Unit Tests) برای ماژول HallucinationGuard — تست‌های واحد برای HallucinationGuard نوشته نشده
  - نوشتن تست‌های یکپارچه‌سازی (Integration Tests) برای pipeline اصلاح‌شده — تست‌های یکپارچه‌سازی برای pipeline اصلاح‌شده نوشته نشده
  - بازبینی نهایی و مستندسازی (Audit & Documentation) — بازبینی نهایی و مستندسازی انجام نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 13 از 16
  id: 3269802a-8316-4245-a7c6-ccebee7a7573
  عنوان اصلی: [منطق] عدم تطابق نوع داده target_locations بین دو کامپوننت
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[Dict\\]", "List\\[str\\]"], "files_hint": ["backend/app/ai_llm/oversight_strong_prompt.py", "backend/app/ai_llm/ai_manager.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[str\\]", "List\\[Dict\\]"], "files_hint": ["backend/app/ai_llm/oversight_strong_prompt.py", "backend/app/ai_llm/ai_manager.py"]}]
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
[منطق] عدم تطابق نوع داده target_locations بین دو کامپوننت

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

oversight_strong_prompt ورودی target_locations را به صورت 'List[Dict] or List[str], optional' تعریف کرده است. اما هیچ مشخص نیست که ai_manager یا سایر مصرف‌کنندگان این خروجی چه فرمتی را انتظار دارند. این ابهام می‌تواند باعث خطاهای parsing در زمان اجرا شود.

## 💥 پیامد (impact)
اگر خروجی oversight_strong_prompt به مدلی ارسال شود که منتظر یک فرمت خاص (مثلاً فقط List[str]) است، مدل ممکن است دچار خطا شود یا خروجی نادرست تولید کند. همچنین در صورت استفاده از target_locations در pipelineهای downstream، عدم تطابق نوع داده باعث crash می‌شود.

## 🛠 پیشنهاد رفع اولیه
نوع داده target_locations را به یک فرمت واحد و مشخص محدود کنید (مثلاً فقط List[Dict] با کلیدهای استاندارد مانند 'path', 'type'). اگر نیاز به پشتیبانی از هر دو فرمت است، یک تابع normalize در ابتدای oversight_strong_prompt اضافه کنید که ورودی را به فرمت استاندارد تبدیل کند.

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
  - بررسی و شناسایی دقیق فایل‌های مرتبط با pipeline ai_llm و تعریف target_locations — شناسایی فایل‌های مرتبط با pipeline ai_llm و target_locations
  - تعریف یک نوع داده واحد و استاندارد برای target_locations (مثلاً List[Dict]) — تعریف نوع داده واحد برای target_locations
  - به‌روزرسانی امضای تابع oversight_strong_prompt برای استفاده از نوع داده استاندارد — به‌روزرسانی امضای oversight_strong_prompt
  - به‌روزرسانی مصرف‌کننده ai_manager برای پذیرش نوع داده استاندارد target_locations — به‌روزرسانی ai_manager برای نوع استاندارد
  - به‌روزرسانی سایر مصرف‌کنندگان downstream target_locations (در صورت وجود) — به‌روزرسانی سایر مصرف‌کنندگان downstream
  - نوشتن تست‌های واحد برای تابع normalize در oversight_strong_prompt — نوشتن تست واحد برای تابع normalize
  - نوشتن تست‌های یکپارچه‌سازی برای جریان کامل (oversight_strong_prompt → ai_manager) — نوشتن تست یکپارچه‌سازی جریان کامل
  - بررسی و به‌روزرسانی مستندات مرتبط با target_locations و pipeline ai_llm — به‌روزرسانی مستندات مرتبط

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 14 از 16
  id: 8e8ae8e3-b115-4957-bc7b-00be1c69bd5b
  عنوان اصلی: [منطق] عدم وضوح در مسیر تعامل بین ai_manager و models_registry
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["models_registry", "ai_manager"], "files_hint": ["backend/app/core/ai_manager.py", "backend/app/core/models_registry.py", "docs/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align"], "files_hint": ["backend/app/core/ai_manager.py", "backend/app/core/models_registry.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision"], "files_hint": [".github/pull_request_template.md"]}]

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
[منطق] عدم وضوح در مسیر تعامل بین ai_manager و models_registry

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

مستندات ai_manager اشاره دارد که با 'backend/app/core/models_registry.py' تعامل دارد، اما مشخص نیست که این تعامل به چه صورت است. آیا models_registry یک دیتابیس محلی است؟ یک API خارجی؟ آیا کش دارد؟ این ابهام می‌تواند منجر به وابستگی‌های پنهان و خطاهای runtime شود.

## 💥 پیامد (impact)
اگر models_registry در دسترس نباشد یا پاسخ نادرست بدهد، ai_manager ممکن است مدل‌های نامعتبر انتخاب کند یا fallback به درستی کار نکند. همچنین تست و دیباگ این بخش دشوار می‌شود.

## 🛠 پیشنهاد رفع اولیه
رابط (interface) بین ai_manager و models_registry را به صورت صریح مستند کنید: متدهای فراخوانی شده، نوع بازگشتی، و رفتار در صورت خطا. یک mock یا stub برای تست این تعامل ایجاد کنید.

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
  - بررسی و مستندسازی موجودیت فعلی models_registry.py — بررسی و مستندسازی کامل ساختار models_registry.py انجام نشده
  - بررسی و مستندسازی تعامل ai_manager با models_registry — مستندسازی تعامل ai_manager با models_registry انجام نشده
  - طراحی و پیاده‌سازی interface صریح برای models_registry — interface صریح برای models_registry طراحی و پیاده‌سازی نشده
  - ایجاد mock/stub برای models_registry بر اساس interface — mock/stub برای models_registry ایجاد نشده
  - به‌روزرسانی ai_manager برای استفاده از interface صریح — ai_manager برای استفاده از interface صریح به‌روزرسانی نشده
  - نوشتن تست‌های unit برای ai_manager با استفاده از mock — تست‌های unit برای ai_manager با mock نوشته نشده
  - به‌روزرسانی مستندات پروژه (README یا docs) درباره interface — مستندات پروژه درباره interface به‌روزرسانی نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 15 از 16
  id: ad0a47f0-302a-4a79-a8a3-728263db2ae7
  عنوان اصلی: [Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["error_rate_30d", "target.*2.*3.*%", "outcome.*target"], "files_hint": ["docs/", "README.md", "*.md"]}]
  - کد تغییر کرد تا outcome target محقق شود [verify_method=static] [verify_plan={"grep_patterns": ["ai_manager", "fallback", "timeout", "connection.*error", "openai.*exception"], "files_hint": ["backend/app/ai_manager.py", "backend/app/"]}]
  - test E2E که outcome را اندازه می‌گیرد عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_manager.py::test_fallback_on_timeout", "timeout_seconds": 60}]
  - metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد [verify_method=static] [verify_plan={"grep_patterns": ["error_rate_30d", "metric", "log.*error_rate", "prometheus.*error"], "files_hint": ["backend/app/metrics.py", "backend/app/logging_config.py"]}]

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
[Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
سیستم باید حداقل ۲-۳٪ خطاهای کنترل‌شده در شرایط مرزی (مثلاً timeout سرویس AI) ثبت کند تا اطمینان حاصل شود fallback mechanism به درستی فعال می‌شود

## 📊 وضعیت فعلی
error_rate_30d: 0.0% - هیچ خطایی ثبت نشده است که می‌تواند به دلیل عدم تست سناریوهای شکست سرویس‌های AI باشد

## 🛠 اقدام پیشنهادی
افزودن تست‌های سناریوی شکست برای ai_manager (مثلاً قطع connection به OpenAI) و بررسی فعال شدن fallback به مدل جایگزین

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و تحلیل وضعیت فعلی ai_manager و fallback mechanism — بررسی و تحلیل کامل ai_manager و fallback mechanism انجام نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (قطع connection به OpenAI) — سناریوی قطع connection به OpenAI پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (timeout سرویس AI) — سناریوی timeout سرویس AI پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (خطای authentication/API key نامعتبر) — سناریوی خطای authentication/API key نامعتبر پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (خطای rate limit) — سناریوی خطای rate limit پیاده‌سازی نشده
  - طراحی و پیاده‌سازی سناریوهای شکست برای ai_manager (خطای invalid response format از سرویس AI) — سناریوی invalid response format پیاده‌سازی نشده
  - افزودن metric/log برای ثبت نرخ خطا در production — metric/log برای ثبت نرخ خطا در production اضافه نشده
  - نوشتن تست E2E که outcome target را اندازه می‌گیرد — تست E2E برای اندازه‌گیری outcome target نوشته نشده
  - بازنویسی outcome target به صورت measurable و اضافه کردن به documentation — outcome target به صورت measurable بازنویسی و به documentation اضافه نشده
  - اجرای تست‌ها و بررسی عدم شکست تست‌های موجود — تست‌ها اجرا نشده و عدم شکست تست‌های موجود بررسی نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 16 از 16
  id: 12fad3ca-ab80-47f9-8389-de33d7265161
  عنوان اصلی: [Effectiveness] عدم یکپارچگی بین oversight_service و project_journal API
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["outcome target", "measurable", "effectiveness"], "files_hint": ["README.md", "docs/"]}]
  - کد تغییر کرد تا outcome target محقق شود [verify_method=static] [verify_plan={"grep_patterns": ["webhook", "oversight_service", "project_journal"], "files_hint": ["backend/app/project_journal/"]}]
  - test E2E که outcome را اندازه می‌گیرد عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_integration/test_oversight_journal_sync.py::test_e2e_outcome", "timeout_seconds": 120}]
  - metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد [verify_method=static] [verify_plan={"grep_patterns": ["metric", "log", "outcome_rate", "oversight_sync_count"], "files_hint": ["backend/app/oversight_service/", "backend/app/project_journal/"]}]

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
[Effectiveness] عدم یکپارچگی بین oversight_service و project_journal API

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
پس از یکپارچگی، ۱۰۰٪ ژورنال‌های پروژه باید به صورت خودکار در oversight_service ذخیره شوند و قابلیت جستجوی full-text داشته باشند

## 📊 وضعیت فعلی
project_journal API مستقل عمل می‌کند و هیچ اشاره‌ای به oversight_service در outcome data دیده نمی‌شود

## 🛠 اقدام پیشنهادی
اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی وضعیت فعلی یکپارچگی بین project_journal و oversight_service در مخزن — بررسی کامل وضعیت یکپارچگی در مخزن انجام نشده
  - ایجاد مدل داده (dataclass/schema) برای گزارش ژورنال در project_journal — مدل داده (schema) برای گزارش ژورنال در project_journal ایجاد نشده
  - ایجاد endpoint دریافت گزارش در oversight_service — endpoint POST برای دریافت گزارش در oversight_service ایجاد نشده
  - پیاده‌سازی ذخیره‌سازی گزارش‌ها در oversight_service (JSON-based) — ذخیره‌سازی JSON-based گزارش‌ها در oversight_service پیاده‌سازی نشده
  - ایجاد webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service — webhook در project_journal برای ارسال خودکار گزارش ایجاد نشده
  - پیاده‌سازی full-text search بر روی گزارش‌های ذخیره شده در oversight_service — full-text search بر روی گزارش‌ها پیاده‌سازی نشده
  - اضافه کردن metric/log در project_journal برای اندازه‌گیری نرخ ارسال موفق گزارش‌ها — metric/log برای نرخ ارسال موفق گزارش اضافه نشده
  - نوشتن تست E2E برای یکپارچگی project_journal و oversight_service — تست E2E برای یکپارچگی نوشته نشده
  - نوشتن تست‌های unit برای webhook در project_journal — تست‌های unit برای webhook در project_journal نوشته نشده
  - نوشتن تست‌های unit برای endpoint دریافت گزارش در oversight_service — تست‌های unit برای endpoint دریافت گزارش در oversight_service نوشته نشده
  - نوشتن تست‌های unit برای full-text search در oversight_service — تست‌های unit برای full-text search نوشته نشده
  - اجرای linter و type-checker و رفع مشکلات — linter و type-checker اجرا و رفع مشکلات نشده

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 5569212c-b3f9-4361-a155-dbd45d88a002, f023ba69-7294-4337-abd4-14a8d6093db6, 4816a520-a370-4e87-9005-a42ff9615257, c159181f-ebc5-427e-8ead-118d56dacae5, 0147715a-b178-44a6-89c5-bb4b36742c45, c81ec6af-6080-448e-89f4-7da379cf1d76, 4e23a1de-5d9d-4e09-9481-07c040f17f29, aa8c1673-2357-40d4-9088-2e28a2c5eb7b, 00c2f0ef-15a2-400a-a082-6123f8af075f, 24c9a57c-11ab-4b6f-926a-eed002719525, 6c68405b-9f9d-4d4c-9826-a2dae60d008e, 26ddcbca-dc7c-4c14-a888-5b366b283fc6, 3269802a-8316-4245-a7c6-ccebee7a7573, 8e8ae8e3-b115-4957-bc7b-00be1c69bd5b, ad0a47f0-302a-4a79-a8a3-728263db2ae7, 12fad3ca-ab80-47f9-8389-de33d7265161`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند
```

## 📋 چک‌لیست مراحل (46 مرحله)

این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**
وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.

- [ ] **مرحله 1: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد** — این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه اجرایی. محتوای آن دستورالعمل‌های متدولوژیک برای نحوه برخورد با کل درخواست است: بررسی وجود پیاده‌سازی قبلی، عدم بازسازی موارد موجود، و مسئولیت‌پذیری در قبال تشخیص‌های نادرست. این بخش خودش یک مرحله اجرایی نیست و نباید به عنوان یک تسک مس
- [ ] **مرحله 2: افزودن لایه validation و output parser به ai_manager برای بررسی پاسخ‌های AI** — این مرحله شامل طراحی و پیاده‌سازی یک لایه validation و output parser در فایل backend/app/ai_manager.py است. برای هر مدل AI (OpenAI, Claude) یک validator مخصوص (Pydantic model) تعریف می‌شود که ساختار و محتوای پاسخ را بررسی کند. همچنین تکنیک‌های grounding و fact-checking برای کاهش توهم (hallucination)
- [ ] **مرحله 3: تعریف معیارهای پذیرش رفتار-محور برای رفع ناسازگاری در pipeline ai_llm** — این بخش شامل ۷ معیار پذیرش (AC) است که رفتار نهایی پس از رفع ناسازگاری را تعریف می‌کند. هر AC یک رفتار قابل مشاهده را مشخص می‌کند (نه پیاده‌سازی). همچنین یک گام اجرایی پیشنهادی (خواندن دو طرف ناسازگاری و لیست کردن فرض‌ها) ارائه شده است. خارج از scope: پیاده‌سازی فنی، نام فایل‌ها یا کلاس‌ها (به جز Ov
- [ ] **مرحله 4: بررسی و مستندسازی ریسک‌های تغییر در callerهای ai_manager و oversight_strong_prompt** — این مرحله شامل شناسایی و مستندسازی تمام callerهای upstream و downstream برای هر دو طرف (ai_manager و oversight_strong_prompt) است. هدف جلوگیری از break شدن مصرف‌کنندگان downstream در اثر تغییر یک طرف است. این مرحله صرفاً به تحلیل وابستگی‌ها و مستندسازی فرضیات می‌پردازد و شامل پیاده‌سازی تغییرات کد ن
- [ ] **مرحله 5: رفع ناسازگاری ورودی ai_manager با خروجی oversight_strong_prompt در pipeline ai_llm** — این بخش به تحلیل و رفع ناسازگاری منطقی بین دو مؤلفه در pipeline `ai_llm` می‌پردازد: `ai_manager` که انتظار یک پرامپت کاربر خام (string) را دارد، و `oversight_strong_prompt` که یک پرامپت اجرایی کامل و ساختاریافته تولید می‌کند. راه‌حل پیشنهادی شامل شفاف‌سازی مسیر جریان داده است: یا `ai_manager` باید پ
- [ ] **مرحله 6: نوشتن تست‌های واحد برای OversightService (CRUD، scheduler، auto_register و edge cases)** — این مرحله شامل پیاده‌سازی تست‌های واحد برای کلاس OversightService در فایل tests/test_oversight_service.py است. چهار acceptance_criteria مشخص شده باید پوشش داده شوند: (1) تست CRUD برای watched projects، (2) تست scheduler loop با mock کردن sleep، (3) تست auto_register_watched با mock GitHub API، (4) ت
- [ ] **مرحله 7: افزودن تست واحد برای کلاس OversightService در oversight_service.py** — این بخش شامل ایجاد تست‌های واحد برای کلاس OversightService در فایل backend/app/services/oversight_service.py است. تست‌ها باید منطق اصلی مانند مدیریت watched projects، قفل asyncio، و تعامل با وابستگی‌های اصلی (مانند database و models) را پوشش دهند. این بخش شامل تست API routes، scheduler، یا سایر سروی
- [ ] **مرحله 8: ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register** — این مرحله شامل ایجاد تست‌های واحد برای کلاس OversightService است. تست‌ها باید رفتارهای CRUD (افزودن، به‌روزرسانی، حذف، لیست) برای watched projects، حلقه scheduler با mock کردن sleep، و auto_register_watched با mock GitHub API را پوشش دهند. همچنین edge cases مانند duplicate repo, invalid URL, empty f
- [ ] **مرحله 9: افزودن تست واحد برای متد add_watched در OversightService** — این بخش شامل ایجاد یک تست واحد جدید برای متد add_watched از کلاس OversightService است. تست باید در فایل tests/test_oversight_service.py اضافه شود. فقط این تست خاص مد نظر است و هیچ تغییر دیگری در کد یا تست‌های دیگر انجام نمی‌شود.
- [ ] **مرحله 10: [منطق] عدم وجود permission check در auth pipeline** — این بخش یک تسک از یک سوپر-تسک بزرگتر است که به بررسی و رفع مشکل عدم وجود permission check در auth pipeline می‌پردازد. scope این بخش شامل شناسایی ناسازگاری‌ها، مستندسازی فرض‌ها، تعیین ground truth، align کردن طرف‌های ناسازگار، نوشتن integration test برای auth pipeline، و توضیح تصمیمات در PR descripti
- [ ] **مرحله 11: افزودن لایه بررسی مجوز (permission check) به pipeline احراز هویت برای مسیرهای mutation** — این مرحله شامل افزودن یک middleware یا dependency برای بررسی مجوز (permission/authorization) قبل از هر mutation در pipeline auth است. تمرکز بر مسیرهای ذخیره سشن‌ها و پیام‌ها در inspector_session می‌باشد. خارج از scope این مرحله: تغییرات در احراز هویت (authentication) پایه، تغییرات در frontend (Next.
- [ ] **مرحله 12: بررسی و رفع coherence issues در pipeline auth** — این مرحله شامل بررسی و رفع coherence issues (مانند feature flag rot یا refactor ناتمام) در pipeline auth است. این بخش از درخواست اصلی به عنوان یک مرحله اجرایی در نظر گرفته شده و باید به صورت کامل انجام شود. تمام caller های هر دو طرف (قبل و بعد از تغییر) باید بررسی شوند تا از عدم break شدن downstream
- [ ] **مرحله 13: بررسی اولیه و اعتبارسنجی خودکار درخواست پیش از اجرا** — این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. هدف آن جلوگیری از پیاده‌سازی مجدد، تشخیص اشتباه، و اطمینان از بررسی مستقل repo است. هیچ فایل، کلاس، یا تابعی برای تغییر مشخص نشده است.
- [ ] **مرحله 14: رفع ناسازگاری منطقی بین task_type و قابلیت‌های مدل در انتخاب هوشمند** — این مرحله شامل ایجاد یک mapping صریح بین task_type و مجموعه ModelCapabilityهای مورد نیاز در pipeline ai_llm است. منطق انتخاب هوشمند باید اصلاح شود تا ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing
- [ ] **مرحله 15: بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager** — این مرحله شامل بررسی کامل و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager (به‌ویژه backend/app/ai_manager.py) است. هدف شناسایی و مستندسازی ناسازگاری‌ها، فرض‌ها و نقاط ضعف در منطق fallback فعلی می‌باشد. این مرحله شامل پیاده‌سازی یا اصلاح کد نمی‌شود و صرفاً به تحلیل و مستندسازی م
- [ ] **مرحله 16: پیاده‌سازی استراتژی fallback در ai_manager برای مدیریت خرابی سرویس‌های AI** — این مرحله شامل طراحی و پیاده‌سازی یک مکانیزم fallback شفاف در فایل backend/app/ai_manager.py است. استراتژی fallback باید شامل ترتیب fallback (OpenAI -> Claude)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout) ب
- [ ] **مرحله 17: بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm** — این مرحله شامل تحلیل کد موجود در فایل‌های backend/app/ai_manager.py و tests/test_ai_llm_pipeline.py برای مستندسازی وضعیت فعلی است. هدف شناسایی نقاط ضعف، وابستگی‌ها و رفتارهای فعلی قبل از اعمال تغییرات است. خروجی این مرحله یک سند یا کامنت‌های کد است که وضعیت فعلی را شرح می‌دهد.
- [ ] **مرحله 18: جایگزینی داده‌های سخت‌کد شده صفحه پروفایل مدل‌ها با داده‌های واقعی از بک‌اند** — این مرحله شامل بازنویسی کامپوننت `model-profiles/page.tsx` برای دریافت داده‌های پروفایل مدل‌ها از API بک‌اند (احتمالاً از طریق FastAPI) به جای استفاده از داده‌های پیش‌فرض سخت‌کد شده (خطوط 90-97) است. خارج از scope: تغییر ساختار دیتابیس، ایجاد endpoint جدید (فرض بر وجود endpoint مناسب است)، و تغییر س
- [ ] **مرحله 19: تعریف معیارهای پذیرش رفتار-محور و مراحل اجرایی برای اعمال تغییرات** — این بخش شامل معیارهای پذیرش عمومی (AC) است که باید برای هر تغییر کد رعایت شود، شامل عبور تست‌ها، linter و type-check. همچنین مراحل اجرایی پیشنهادی را مشخص می‌کند که مجری باید بر اساس context تعیین کند. خروجی مورد انتظار تغییر کد در فایل‌های مرتبط و commit/PR با عبور تمام ACها است. این بخش دستورالعمل
- [ ] **مرحله 20: اضافه کردن validation و guardrails به خروجی oversight_strong_prompt** — این بخش شامل پیاده‌سازی validation و guardrails برای خروجی oversight_strong_prompt است تا از بروز توهم (hallucination) جلوگیری شود. همچنین شامل شناسایی ناسازگاری‌ها، تعیین ground truth، و نوشتن integration test برای pipeline ai_llm می‌شود. فایل‌های اصلی backend/app/oversight_strong_prompt.py و backe
- [ ] **مرحله 21: افزودن لایه اعتبارسنجی و گاردریل به خروجی oversight_strong_prompt** — این بخش شامل افزودن validation به تابع یا کلاس تولیدکننده پرامپت در فایل oversight_strong_prompt.py است. موارد تحت پوشش: (1) بررسی وجود فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک مان
- [ ] **مرحله 22: بررسی و مستندسازی ناسازگاری‌های دو طرف oversight_strong_prompt و ai_llm با مکانیزم fallback** — این مرحله شامل تحلیل و مستندسازی ناسازگاری‌های موجود بین دو مؤلفه oversight_strong_prompt و ai_llm است. تمرکز بر شناسایی فرض‌های هر طرف، تعیین ground truth و align کردن طرف دیگر است. همچنین شامل نوشتن integration test برای pipeline ai_llm و مستندسازی تصمیمات در PR description می‌شود. فایل‌های اصلی د
- [ ] **مرحله 23: افزودن مکانیزم fallback و error handling به oversight_strong_prompt** — این مرحله شامل افزودن لایه error handling به فایل backend/app/oversight_strong_prompt.py است. شامل: (1) پیاده‌سازی retry با backoff برای زمان‌هایی که مدل خارجی پاسخ نمی‌دهد، (2) fallback به یک مدل جایگزین (احتمالاً از طریق ai_manager)، (3) ثبت خطا و بازگشت پاسخ پیش‌فرض (graceful degradation). این مر
- [ ] **مرحله 24: بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager** — این مرحله شامل تحلیل کامل کد موجود در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_manager.py است. هدف، مستندسازی رفتار فعلی، نقاط ضعف، وابستگی‌ها و نحوه تعامل این دو سرویس با یکدیگر است. خروجی این مرحله یک سند یا کامنت‌های کد خواهد بود که وضعیت موجود را به‌طور شفاف توصیف می‌کند.
- [ ] **مرحله 25: تعریف معیارهای عملکردی برای انتخاب هوشمند مدل** — این بخش به فقدان معیارهای عملکردی (Effectiveness metrics) برای انتخاب هوشمند مدل در سیستم AI Manager اشاره دارد. شامل تعریف معیارهایی مانند دقت، سرعت، هزینه و مصرف منابع برای مقایسه مدل‌های مختلف است. خارج از این بخش: پیاده‌سازی مکانیزم انتخاب، ذخیره‌سازی نتایج، یا رابط کاربری. نکته حیاتی: معیارها ب
- [ ] **مرحله 26: افزودن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history** — این مرحله شامل افزودن logging برای latency و cost به فایل backend/app/ai_manager.py و پیاده‌سازی مکانیزم weighted selection بر اساس performance history است. هدف این است که انتخاب مدل دیگر صرفاً بر اساس availability نباشد، بلکه بر اساس معیارهای عملکردی (latency و cost) وزن‌دهی شود. این مرحله شامل تغی
- [ ] **مرحله 27: تعریف معیارهای پذیرش رفتار-محور برای outcome target** — این بخش شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از پیاده‌سازی صحیح outcome target است. هر AC رفتار قابل مشاهده را تعریف می‌کند و نه پیاده‌سازی داخلی. scope شامل: بازنویسی outcome target به صورت measurable، تغییر کد، تست E2E، metric/log، عبور تست‌ها، linter و type-check. خارج از scope: تعریف خود o
- [ ] **مرحله 28: بررسی و اصلاح عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts** — این بخش شامل شناسایی ناسازگاری‌های بین فرمت system_prompts و مدل‌های مختلف (OpenAI vs Claude)، تعیین ground truth و align کردن طرف دیگر، نوشتن integration test برای pipeline ai_llm، و مستندسازی تصمیم در PR description است. فایل‌های دخیل: backend/app/system_prompts/ و backend/app/ai_llm/. خارج از sco
- [ ] **مرحله 29: رفع ناسازگاری فرمت پرامپت‌های سیستم بین مدل‌های مختلف در pipeline ai_llm** — این بخش به تحلیل و رفع ناسازگاری منطقی بین system_prompts و مدل‌های مختلف (OpenAI vs Claude) می‌پردازد. شامل: افزودن لایه adapter در prompt_helper یا ai_manager برای تبدیل پرامپت‌های generic به فرمت مناسب هر مدل. ذخیره‌سازی پرامپت‌ها با metadata مربوط به مدل‌های سازگار. خارج از scope: تغییرات در pip
- [ ] **مرحله 30: بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline** — این مرحله شامل بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline در کدبیس است. هدف آن مستندسازی وضعیت موجود، شناسایی نقاط ضعف و ناسازگاری‌ها، و تعیین ground truth برای مراحل بعدی است. این مرحله شامل پیاده‌سازی یا تغییر کد نمی‌شود و صرفاً یک audit و مستندسازی است.
- [ ] **مرحله 31: افزودن ماژول Hallucination Guard به ai_manager در pipeline ai_llm** — این مرحله شامل طراحی و پیاده‌سازی یک ماژول جدید برای کاهش توهم (hallucination guard) در pipeline `ai_llm` است. ماژول باید به `ai_manager` اضافه شود و شامل سه قابلیت اصلی باشد: 1) grounding پاسخ‌ها به منابع معتبر، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پا
- [ ] **مرحله 32: بررسی و رفع عدم تطابق نوع داده target_locations بین دو کامپوننت** — این مرحله شامل شناسایی و مستندسازی ناسازگاری نوع داده فیلد target_locations بین دو کامپوننت (احتمالاً oversight_strong_prompt و ai_manager)، تعیین ground truth و align کردن طرف دیگر، و اطمینان از عبور integration test مربوط به pipeline ai_llm است. همچنین PR description باید توضیح دهد چرا این تصمیم گ
- [ ] **مرحله 33: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد قابلیت‌های موجود** — این بخش یک یادداشت مهم برای مدل اجراکننده است و دستورالعمل‌های رفتاری قبل از شروع هر تغییری را مشخص می‌کند. شامل: (1) بررسی وجود پیاده‌سازی قبلی با grep/search، (2) عدم بازسازی موارد موجود، (3) اصلاح/تکمیل موارد ناقص، (4) ثبت کامیت no-op در صورت کامل بودن، (5) مسئولیت مدل برای بررسی مستقل ساختار rep
- [ ] **مرحله 34: رفع عدم تطابق نوع داده target_locations در pipeline ai_llm** — این مرحله شامل تحلیل و رفع ناسازگاری نوع داده target_locations بین کامپوننت‌های pipeline ai_llm است. تمرکز بر فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_manager.py و backend/app/services/oversight_service.py می‌باشد. خارج از scope این مرحله: تغییرات در pipelineهای دیگر، تست‌های
- [ ] **مرحله 35: ریسک‌ها و موارد احتیاط: بررسی caller‌های هر دو طرف قبل از merge** — این بخش به ریسک‌های ناشی از تغییر یک طرف pipeline (احتمالاً oversight_strong_prompt و ai_manager) می‌پردازد و بر لزوم بررسی همه caller‌های هر دو طرف قبل از merge تأکید دارد. این یک مرحله احتیاطی و غیرفنی است که باید قبل از هر تغییر کد انجام شود. هیچ مرحله اجرایی مستقیمی در این بخش تعریف نشده است.
- [ ] **مرحله 36: بررسی اولیه و تحلیل وضعیت موجود repo قبل از اجرا** — این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن صرفاً آگاه‌سازی مدل از احتمال وجود پیاده‌سازی قبلی، لزوم بررسی مستقل ساختار repo، و مسئولیت‌پذیری در قبال تصمیمات است. هیچ فایل، کلاس، یا تابع جدیدی نباید ساخته شود.
- [ ] **مرحله 37: مستندسازی و رفع ابهام در تعامل بین ai_manager و models_registry** — این مرحله شامل تحلیل و مستندسازی رابط (interface) بین ai_manager و models_registry در pipeline ai_llm است. باید مشخص شود که models_registry یک دیتابیس محلی، API خارجی یا کش است. سپس یک mock یا stub برای تست این تعامل ایجاد می‌شود. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/core/mode
- [ ] **مرحله 38: بررسی ریسک‌های تغییر در callerهای downstream قبل از merge** — این بخش یک هشدار ریسک است و نه یک مرحله اجرایی. محتوای آن صرفاً یک نکته احتیاطی درباره بررسی callerهای هر دو طرف قبل از merge است. هیچ اقدام عملیاتی یا کدنویسی در این بخش تعریف نشده است.
- [ ] **مرحله 39: تحلیل عدم وجود خطا در ۳۰ روز اخیر به عنوان نشانه پوشش ناقص سناریوهای خطا** — این بخش به تحلیل کیفی لاگ‌های خطا در ۳۰ روز اخیر می‌پردازد و این فرضیه را مطرح می‌کند که عدم وجود خطا به معنی کامل بودن سیستم نیست، بلکه ممکن است نشان‌دهنده پوشش ناقص سناریوهای خطا باشد. این یک مرحله تحلیلی و بازبینی است و شامل پیاده‌سازی کد جدید نمی‌شود. خروجی این بخش باید یک گزارش یا مستندسازی از 
- [ ] **مرحله 40: افزودن تست‌های سناریوی شکست برای ai_manager و بررسی fallback به مدل جایگزین** — این مرحله شامل افزودن تست‌های سناریوی شکست (failure scenario tests) برای ماژول ai_manager است. تمرکز بر قطع connection به OpenAI و بررسی فعال شدن fallback به مدل جایگزین می‌باشد. این یک effectiveness issue است، بنابراین تست‌ها باید outcome را اندازه بگیرند (مثلاً اینکه آیا fallback واقعاً فعال می‌شو
- [ ] **مرحله 41: تعریف معیارهای پذیرش رفتار-محور و بازنویسی outcome target قابل اندازه‌گیری** — این بخش شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از رفتار قابل مشاهده و اندازه‌گیری outcome target است. همچنین شامل یک گام اجرایی برای بازنویسی outcome target به صورت measurable می‌باشد. خارج از scope: پیاده‌سازی کد، نوشتن تست، اضافه کردن metric/log، اجرای linter/type-check.
- [ ] **مرحله 42: بازنویسی outcome target به صورت measurable و افزودن به documentation** — این مرحله شامل بازنویسی outcome target (هدف پیامد) به شکلی قابل اندازه‌گیری (measurable) و افزودن آن به مستندات پروژه (مانند README.md یا docs/) است. این مرحله صرفاً بر روی متن و مستندات تمرکز دارد و شامل تغییر کد یا پیاده‌سازی نمی‌شود. خروجی این مرحله یک متن measurable است که در فایل‌های مستندات قر
- [ ] **مرحله 43: رفع عدم یکپارچگی بین oversight_service و project_journal API** — این بخش به عدم یکپارچگی بین سرویس oversight_service و API پروژه ژورنال اشاره دارد. هدف آن شناسایی و رفع شکاف‌های ارتباطی بین این دو مؤلفه است. فایل‌های مرتبط شامل backend/app/services/oversight_service.py و کلاس OversightService هستند. هیچ موقعیت دقیق فایل یا endpoint خاصی در متن مشخص نشده است.
- [ ] **مرحله 44: اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based** — این بخش شامل افزودن یک webhook در سرویس project_journal است تا پس از تکمیل هر پروژه/ژورنال، یک گزارش خودکار به oversight_service ارسال شود. گزارش باید به صورت JSON ذخیره شود. این بخش شامل تغییر در کد project_journal برای ارسال درخواست HTTP به oversight_service و همچنین تغییر در oversight_service برا
- [ ] **مرحله 45: تبدیل معیارهای پذیرش رفتار-محور به یک مرحله اجرایی با outcome target قابل اندازه‌گیری** — این بخش شامل تعریف معیارهای پذیرش (AC) به صورت رفتار-محور و یک گام اجرایی برای بازنویسی outcome target به صورت قابل اندازه‌گیری است. خارج از scope: پیاده‌سازی کد، نوشتن تست E2E، اضافه کردن metric/log، اجرای linter/type-check. نکته حیاتی: ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس، و ve
- [ ] **مرحله 46: ریسک‌ها و موارد احتیاط: بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن** — این بخش یک یادآوری/هشدار (⚠️) است و یک مرحله اجرایی مستقل نیست. هیچ کد یا تغییری در فایل‌ها ایجاد نمی‌کند. هدف آن ثبت یک ریسک معماری (trade-off بین کیفیت خروجی و هزینه/سرعت) است که باید در مراحل بعدی (مانند پیاده‌سازی webhook یا endpoint) به‌عنوان یک معیار ارزیابی در نظر گرفته شود. هیچ اقدامی در این

---

# 🔹 مرحله 1: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد

**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه اجرایی. محتوای آن دستورالعمل‌های متدولوژیک برای نحوه برخورد با کل درخواست است: بررسی وجود پیاده‌سازی قبلی، عدم بازسازی موارد موجود، و مسئولیت‌پذیری در قبال تشخیص‌های نادرست. این بخش خودش یک مرحله اجرایی نیست و نباید به عنوان یک تسک مستقل در نظر گرفته شود.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه فنی. محتوای آن دستورالعمل‌های رفتاری برای اجرای درست سایر بخش‌ها را مشخص می‌کند: بررسی وجود پیاده‌سازی قبلی، عدم بازسازی موارد موجود، و مسئولیت‌پذیری در قبال تشخیص‌های نادرست. هیچ فایل یا کلاسی مستقیماً تغییر نمی‌کند.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور پیاده‌سازی مستقیمی نیست. وظیفه آن: ۱) هشدار درباره احتمال خطا در پرامپت خودکار، ۲) الزام به بررسی پیش‌نیاز repo قبل از هر تغییر، ۳) دستور به عدم بازسازی قابلیت‌های موجود، ۴) در صورت کامل بودن همه چیز، ثبت کامیت no-op. این بخش خودش یک مرحله اجرایی نیست، بلکه یک precondition برای تمام مراحل بعدی است.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور پیاده‌سازی مستقیمی نیست. وظیفه آن: (۱) هشدار به مدل که پرامپت بر اساس بررسی خودکار ساخته شده و ممکن است ناقص/اشتباه باشد، (۲) الزام به بررسی وجود پیاده‌سازی قبلی در repo قبل از شروع، (۳) تعیین مسئولیت مدل برای قضاوت مستقل در صورت ناسازگاری، (۴) دستورالعمل برای کارهای طولانی (تقسیم به کامیت‌های متعدد و ارائه checklist). این بخش صراحتاً می‌گوید 'قبل از شروع بخوان' و 'مسئولیت تو' — بنابراین یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک است.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه اجرایی. هدف آن اطمینان از این است که قبل از هر تغییری، وضعیت فعلی repo (فایل‌ها، کلاس‌ها، توابع) با جستجو و خواندن بررسی شود تا از پیاده‌سازی مجدد قابلیت‌های موجود جلوگیری شود. اگر همه چیز از قبل به درستی پیاده‌سازی شده، فقط یک کامیت no-op با توضیح ثبت شود. این بخش شامل هیچ دستور مستقیم برای تغییر کد نیست.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مستقیمی نیست. وظیفه آن الزام مدل به بررسی خودکار ساختار repo، فایل‌ها و وابستگی‌ها پیش از هر تغییری است. اگر قابلیت‌های درخواستی از قبل وجود داشته باشند، نباید دوباره ساخته شوند. این بخش به‌تنهایی یک مرحله اجرایی نیست، بلکه یک شرط پیش‌نیاز برای تمام مراحل بعدی است.
— [merged] این بخش یک یادداشت مهم برای مدل اجراکننده است که قبل از هر تغییری باید اجرا شود. شامل دستورالعمل‌هایی برای بررسی وجود پیاده‌سازی قبلی، جستجوی فایل‌های مرتبط، و تصمیم‌گیری بر اساس قضاوت شخصی است. این بخش خود یک مرحله اجرایی ن

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی پیش‌نیاز repo و جلوگیری از پیاده‌سازی مجدد

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/inspector_agent.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً محل اصلی پیاده‌سازی قابلیت‌های inspector است.
- `backend/app/services/inspector_scan_bridge.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. پل ارتباطی بین inspector و scan.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/scan_v5/scan_bundle.py` — احتمالاً توسط inspector_agent استفاده می‌شود — باید بررسی شود که scan_bundle قبلاً پیاده‌سازی شده یا نه
- `backend/app/services/oversight_inspector_bridge.py` — پل ارتباطی بین oversight و inspector — باید بررسی شود که قابلیت‌های مرتبط قبلاً وجود دارند یا نه
- `backend/app/services/verify_runtime/inspector_probe.py` — probe مخصوص inspector در runtime verify — باید بررسی شود که آیا قابلیت‌های درخواستی قبلاً در اینجا پیاده‌سازی شده‌اند

## 🌐 نقشهٔ وابستگی‌ها
این تسک یک precondition است و مستقیماً وابستگی به فایل خاصی ندارد. اما فایل‌های مرتبط با inspector که باید بررسی شوند عبارتند از: backend/app/services/inspector_agent.py (احتمالاً محل اصلی)، backend/app/services/inspector_scan_bridge.py (پل scan)، backend/app/services/scan_v5/scan_bundle.py (bundle اسکن)، backend/app/services/oversight_inspector_bridge.py (پل oversight). این فایل‌ها توسط routes مختلف مثل backend/app/api/routes/analysis.py و backend/app/api/routes/oversight.py استفاده می‌شوند.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه اجرایی مستقیم. محتوای آن دستورالعمل‌های متدولوژیک برای نحوه برخورد با کل درخواست است: بررسی وجود پیاده‌سازی قبلی، عدم بازسازی موارد موجود، و مسئولیت‌پذیری در قبال تشخیص‌های نادرست. این بخش خودش یک مرحله اجرایی نیست و نباید به عنوان یک تسک مستقل در نظر گرفته شود.

بخش مربوط از درخواست اصلی کاربر:
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مدل اجراکننده قبل از هر تغییری، وجود پیاده‌سازی قبلی را با grep/search بررسی کرده باشد
- [ ] اگر قابلیت‌های درخواستی از قبل وجود دارند، مدل آن‌ها را دوباره نساخته باشد
- [ ] اگر همه چیز کامل است، یک کامیت no-op با توضیح ثبت شده باشد
- [ ] اگر کار طولانی است، در چندین کامیت متوالی با ترتیب منطقی انجام شده باشد
- [ ] در PR description checklist از همه کامیت‌ها نوشته شده باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک یک precondition برای تمام مراحل بعدی است و شامل هیچ دستور پیاده‌سازی مستقیمی نیست. وظیفه مدل اجراکننده:

1. **بررسی خودکار repo**: با استفاده از grep/search، فایل‌های مرتبط با درخواست‌های بعدی را جستجو کند. مثلاً اگر درخواست‌های بعدی به inspector_agent.py اشاره دارند، وجود کلاس‌ها و توابع مربوطه را بررسی کند.

2. **تشخیص پیاده‌سازی قبلی**: اگر قابلیت‌های درخواستی از قبل وجود دارند (مثلاً تابع `scan_project` در `inspector_agent.py`)، نباید دوباره ساخته شوند.

3. **اصلاح موارد ناقص**: اگر پیاده‌سازی ناقص است (مثلاً تابعی وجود دارد اما پارامترهایش کامل نیست)، فقط همان موارد را اصلاح کند.

4. **کامیت no-op**: اگر همه چیز کامل است، یک کامیت توضیحی با پیام "no-op: all requested features already implemented" ثبت کند و فایل‌های پوشش‌دهنده را لیست کند.

5. **تقسیم کار طولانی**: اگر کار طولانی است، در چندین کامیت متوالی با ترتیب foundation → core → integration → tests انجام دهد و در PR description checklist ارائه دهد.

## 💡 نمونه‌های قبل/بعد
**نمونه کامیت no-op**

_قبل:_
```
هیچ تغییری در کد ایجاد نمی‌شود
```

_بعد:_
```
کامیت با پیام: 'no-op: all requested features already implemented in inspector_agent.py, inspector_scan_bridge.py, scan_bundle.py'
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -r 'class InspectorAgent' backend/app/services/`
- `grep -r 'def scan_project' backend/app/services/`
- `git log --oneline -5`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک یک precondition است و ریسک مستقیم ندارد. اما اگر مدل اجراکننده این مرحله را نادیده بگیرد و مستقیماً به پیاده‌سازی بپردازد، ممکن است قابلیت‌های موجود را دوباره بسازد که باعث duplication و اتلاف وقت می‌شود. فایل‌های inspector_agent.py و inspector_scan_bridge.py توسط routes مختلف استفاده می‌شوند و تغییرات نادرست می‌تواند روی analysis و oversight تأثیر بگذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 2: افزودن لایه validation و output parser به ai_manager برای بررسی پاسخ‌های AI

**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک لایه validation و output parser در فایل backend/app/ai_manager.py است. برای هر مدل AI (OpenAI, Claude) یک validator مخصوص (Pydantic model) تعریف می‌شود که ساختار و محتوای پاسخ را بررسی کند. همچنین تکنیک‌های grounding و fact-checking برای کاهش توهم (hallucination) اضافه می‌شود. این مرحله شامل تغییر در فایل‌های tests/test_ai_llm_pipeline.py و backend/app/ai_manager.py نیز می‌شود. خارج از scope این مرحله: تغییر در سایر فایل‌های لیست شده (مانند oversight_service یا routes) نیست.
**Key terms:** backend/app/ai_manager.py, backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py, ai_llm, OpenAI, Claude, Pydantic model, validation, output parser, grounding, fact-checking, hallucination

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در مستندات ai_manager اشاره‌ای به validation خروجی مدل‌های AI نشده است. با توجه به اینکه این سرویس مدیریت مرکزی سرویس‌های AI را بر عهده دارد و با مدل‌های مختلف (OpenAI, Claude) کار می‌کند، عدم وجود validation می‌تواند منجر به پردازش پاسخ‌های ناقص، نادرست یا دارای توهم (hallucination) شود. همچنین مشخص نیست که آیا output parser خاصی برای تطبیق خروجی مدل با فرمت مورد انتظار downstream services وجود دارد یا خیر.

💥 پیامد (impact)
پاسخ‌های نادرست یا ناقص به کاربر نهایی ارسال می‌شود. خطاهای زنجیره‌ای در pipeline به دلیل عدم تطابق فرمت خروجی. افزایش ریسک توهم (hallucination) در پاسخ‌های AI.

🛠 پیشنهاد رفع اولیه
یک لایه validation و output parser به ai_manager اضافه کنید. برای هر مدل، یک validator مخصوص (مثلاً Pydantic model) تعریف کنید که ساختار و محتوای پاسخ را بررسی کند. از تکنیک‌های grounding و fact-checking برای کاهش توهم استفاده کنید.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن لایه validation و output parser به ai_manager برای بررسی پاسخ‌های AI

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `AIResponse` — فایل deep-read نشده — بر اساس ساختار سطحی. این فایل نقطه اصلی تغییر است. باید متد process_request اصلاح شود تا از validator استفاده کند.
- `backend/app/services/openai_service.py:1-30` — `OpenAIService` — فایل deep-read نشده — بر اساس ساختار سطحی. باید متد generate_response اصلاح شود تا خروجی قابل validation باشد.
- `backend/app/services/claude_service.py:1-30` — `ClaudeService` — فایل deep-read نشده — بر اساس ساختار سطحی. باید متد generate_response اصلاح شود تا خروجی قابل validation باشد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Python 3.11+, FastAPI, Pydantic v2, OpenAI SDK, Anthropic SDK, pytest

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` (سطر 1) — کلاس پایه برای سرویس‌های AI — ممکن است نیاز به تغییر در متدهای abstract داشته باشد
- `backend/app/services/ai_balance_service.py` (سطر 1) — این سرویس از ai_manager استفاده می‌کند و ممکن است تحت تأثیر تغییرات خروجی قرار گیرد
- `backend/app/services/oversight_service.py` (سطر 1) — مصرف‌کننده downstream پاسخ‌های AI — باید backward compatibility حفظ شود
- `backend/app/services/oversight_inspector_bridge.py` (سطر 1) — پل بین oversight و inspector — ممکن است از خروجی AI استفاده کند
- `backend/app/services/scan_v5/scan_bundle.py` (سطر 1) — سیستم اسکن v5 که از AI برای تحلیل استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات بر فایل‌های backend/app/services/ai_manager.py (مرکز مدیریت AI)، backend/app/services/openai_service.py (سرویس OpenAI)، backend/app/services/claude_service.py (سرویس Claude)، backend/app/services/ai_base.py (کلاس پایه)، backend/app/services/ai_balance_service.py (مدیریت تعادل AI) تأثیر می‌گذارد. همچنین فایل‌های downstream مانند backend/app/services/oversight_service.py و backend/app/services/oversight_inspector_bridge.py و backend/app/services/scan_v5/scan_bundle.py که از خروجی AI استفاده می‌کنند باید backward compatibility داشته باشند. فایل جدید backend/app/services/ai_validators.py ایجاد می‌شود و فایل tests/test_ai_llm_pipeline.py برای تست‌ها ایجاد می‌شود.

## 🔍 Context و وضعیت فعلی
بر اساس درخواست کاربر، نیاز به افزودن یک لایه validation و output parser به فایل backend/app/ai_manager.py است. این لایه باید برای هر مدل AI (OpenAI, Claude) یک validator مخصوص (Pydantic model) تعریف کند که ساختار و محتوای پاسخ را بررسی کند. همچنین تکنیک‌های grounding و fact-checking برای کاهش توهم (hallucination) اضافه شود. این مرحله شامل تغییر در فایل‌های tests/test_ai_llm_pipeline.py و backend/app/ai_manager.py نیز می‌شود. خارج از scope این مرحله: تغییر در سایر فایل‌های لیست شده (مانند oversight_service یا routes) نیست.

کلیدواژه‌های اصلی: backend/app/ai_manager.py, backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py, ai_llm, OpenAI, Claude, Pydantic model, validation, output parser, grounding, fact-checking, hallucination

شواهد در کد: فایل backend/app/services/ai_manager.py در ساختار پروژه موجود است اما deep-read نشده است. فایل tests/test_ai_llm_pipeline.py نیز در ساختار پروژه موجود نیست و باید ایجاد شود. فایل‌های مرتبط با سرویس‌های AI شامل backend/app/services/openai_service.py و backend/app/services/claude_service.py هستند که باید برای تطبیق با validator جدید اصلاح شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/services/ai_validators.py باید شامل کلاس‌های OpenAIValidator و ClaudeValidator باشد که از Pydantic BaseModel ارث‌بری کنند و متد validate_response را پیاده‌سازی کنند.
- [ ] متد process_request در backend/app/services/ai_manager.py باید از validator استفاده کند و خروجی از نوع str به نوع AIResponse تغییر کند.
- [ ] تست‌های unit در tests/test_ai_llm_pipeline.py باید شامل حداقل 3 تست برای OpenAIValidator و 3 تست برای ClaudeValidator باشد که موارد valid و invalid را پوشش دهد.
- [ ] تکنیک‌های grounding باید در validator پیاده‌سازی شود به طوری که پاسخ‌های AI با context پروژه cross-reference شوند و در صورت عدم تطابق، خطای مناسب برگردانده شود.
- [ ] سرویس‌های downstream (oversight_service, oversight_inspector_bridge, scan_bundle) باید بدون تغییر و با backward compatibility کار کنند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک فایل جدید backend/app/services/ai_validators.py شامل Pydantic modelهای validator برای OpenAI و Claude.
2. تعریف کلاس‌های BaseAIValidator, OpenAIValidator, ClaudeValidator با متدهای validate_response, parse_output, check_grounding, fact_check.
3. اصلاح فایل backend/app/services/ai_manager.py برای استفاده از validatorها در متدهای process_request و get_response.
4. افزودن تکنیک‌های grounding با استفاده از context پروژه و fact-checking با cross-reference.
5. ایجاد فایل tests/test_ai_llm_pipeline.py با تست‌های unit برای validatorها و integration برای pipeline کامل.
6. اطمینان از backward compatibility با سرویس‌های downstream مانند oversight_service.

## 💡 نمونه‌های قبل/بعد
**مثال: متد process_request در ai_manager قبل و بعد از تغییر**

_قبل:_
```
def process_request(self, prompt: str, model: str) -> str:
    if model == 'openai':
        return self.openai_service.generate(prompt)
    elif model == 'claude':
        return self.claude_service.generate(prompt)
    return ''
```

_بعد:_
```
def process_request(self, prompt: str, model: str) -> AIResponse:
    raw_response = self._get_raw_response(prompt, model)
    validator = self._get_validator(model)
    validated = validator.validate(raw_response)
    if not validated.is_valid:
        self._handle_validation_failure(validated.errors)
    return validated.response
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_llm_pipeline.py -v -m validator`
- `pytest backend/tests/test_ai_llm_pipeline.py -v -m integration`
- `python -c "from backend.app.services.ai_validators import OpenAIValidator, ClaudeValidator; print('Import OK')"`
- `python -c "from backend.app.services.ai_manager import AIResponse; print('Import OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: تغییر نوع خروجی متد process_request از str به AIResponse می‌تواند تمام مصرف‌کنندگان downstream را بشکند. فایل‌های backend/app/services/oversight_service.py، backend/app/services/oversight_inspector_bridge.py، backend/app/services/scan_v5/scan_bundle.py و backend/app/services/ai_balance_service.py همگی از ai_manager استفاده می‌کنند و باید به‌روزرسانی شوند. همچنین فایل‌های route مانند backend/app/api/routes/chat.py و backend/app/api/routes/ai_usage.py که از ai_manager استفاده می‌کنند نیاز به بررسی دارند. ریسک دوم: اضافه کردن validation ممکن است latency را افزایش دهد و باید timeout مناسب در نظر گرفته شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 3: تعریف معیارهای پذیرش رفتار-محور برای رفع ناسازگاری در pipeline ai_llm

**Scope:** این بخش شامل ۷ معیار پذیرش (AC) است که رفتار نهایی پس از رفع ناسازگاری را تعریف می‌کند. هر AC یک رفتار قابل مشاهده را مشخص می‌کند (نه پیاده‌سازی). همچنین یک گام اجرایی پیشنهادی (خواندن دو طرف ناسازگاری و لیست کردن فرض‌ها) ارائه شده است. خارج از scope: پیاده‌سازی فنی، نام فایل‌ها یا کلاس‌ها (به جز OversightService که ذکر شده).
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کند، نه پیاده‌سازی داخلی. معیارها از شناسایی ناسازگاری و مستندسازی فرض‌ها تا عبور موفق integration test برای pipeline ai_llm، عبور تست‌ها، linter و type-check را پوشش می‌دهد. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، طراحی کلاس‌ها یا فایل‌های خاص.
— [merged] این بخش معیارهای پذیرش (AC) را برای یک مرحله از پروژه تعریف می‌کند که در آن ناسازگاری بین دو طرف (احتمالاً دو پیاده‌سازی یا دو دیدگاه) شناسایی و رفع می‌شود. شامل مستندسازی فرض‌ها، تعیین ground truth، اجرای integration test برای pipeline auth، و اطمینان از عبور تست‌ها، linter و type-check است. خارج از scope: پیاده‌سازی خود ناسازگاری، طراحی معماری، یا تغییر در business logic فراتر از pipeline auth.
— [merged] این بخش شامل تعریف ۷ معیار پذیرش (AC) برای فرآیند رفع ناسازگاری بین دو طرف است. هر AC رفتار قابل مشاهده را مشخص می‌کند و نه پیاده‌سازی. همچنین شامل یک گام اجرایی پیشنهادی برای شروع کار است. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، کدنویسی، یا تعیین جزئیات فنی.
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کنند، نه پیاده‌سازی داخلی. ACها بر شناسایی ناسازگاری، مستندسازی فرض‌ها، تعیین ground truth، عبور integration test برای pipeline ai_llm، توضیح PR description، عبور تست‌ها، linter و type-check تمرکز دارند. گام اول از مراحل اجرایی (خواندن دو طرف ناسازگاری و لیست کردن فرض‌ها) نیز در این بخش ذکر شده است. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، جزئیات فنی فراتر از ACها.
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کنند، نه پیاده‌سازی داخلی. همچنین شامل یک گام اجرایی پیشنهادی (گام ۱) است که صرفاً خواندن و لیست کردن فرض‌های دو طرف ناسازگاری را توصیه می‌کند. خارج از scope: اجرای کامل رفع ناسازگاری، نوشتن کد، یا تغییر در فایل‌ها.
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کنند، نه پیاده‌سازی داخلی. هر AC باید توسط تست‌های یکپارچه‌سازی و ابزارهای کیفیت کد (linter, type-checker) تأیید شود. تمرکز بر شناسایی ناسازگاری، مستندسازی فرض‌ها، تعیین ground truth، و عبور موفق pipeline `ai_llm` از integration test است. خارج از scope: پیاده‌سازی داخلی کلاس‌ها، نام فایل‌های خاص، یا جزئیات الگوریتمی.
—
**Key terms:** tsc --noEmit, tests/test_ai_llm_pipeline.py, ai_llm, npm run test, pytest, tests/test_oversight_service.py, backend/app/core/database.py, backend/app/api/routes/oversight.py, backend/app/models/setting.py, backend/app/ai_manager.py, backend/app/main.py, OversightService, mypy, backend/app/services/oversight_service.py, backend/app/api/routes/github_import.py, backend/app/services/verify_runtime/__init__.py, backend/app/oversight_strong_prompt.py

**بخش مربوط از متن کاربر:**
```
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
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف ۷ معیار پذیرش رفتار-محور برای رفع ناسازگاری pipeline ai_llm

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:نامشخص — فایل deep-read نشده` — `احتمالاً کلاس AIManager یا توابع مدیریت pipeline` — این فایل احتمالاً مدیریت pipeline‌های AI از جمله `ai_llm` را بر عهده دارد. بر اساس ساختار سطحی — توسط مجری تأیید شود.
  ```python
  فایل deep-read نشده — snippet موجود نیست
  ```
- `backend/app/services/oversight_service.py:نامشخص — فایل deep-read نشده` — `احتمالاً کلاس OversightService` — این فایل سرویس نظارت را پیاده‌سازی می‌کند و ممکن است با pipeline `ai_llm` ناسازگاری داشته باشد. بر اساس ساختار سطحی — توسط مجری تأیید شود.
  ```python
  فایل deep-read نشده — snippet موجود نیست
  ```
- `backend/tests/test_ai_llm_pipeline.py:نامشخص — فایل deep-read نشده` — `احتمالاً توابع تست برای pipeline ai_llm` — این فایل integration test برای pipeline `ai_llm` را شامل می‌شود. بر اساس ساختار سطحی — توسط مجری تأیید شود.
  ```python
  فایل deep-read نشده — snippet موجود نیست
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — از همین استفاده کن.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این روتر از OversightService استفاده می‌کند و ممکن است تحت تأثیر ناسازگاری قرار گیرد.
- `backend/app/core/database.py` — احتمالاً توسط OversightService و ai_manager برای ذخیره‌سازی استفاده می‌شود.
- `backend/app/models/setting.py` — مدل تنظیمات که ممکن است در pipeline ai_llm استفاده شود.
- `backend/app/main.py` — نقطه ورود برنامه که سرویس‌ها را راه‌اندازی می‌کند.
- `backend/app/services/verify_runtime/__init__.py` — لایه verify که ممکن است با pipeline ai_llm تعامل داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک وابسته به فایل‌های `backend/app/services/ai_manager.py` (مدیریت pipeline AI)، `backend/app/services/oversight_service.py` (سرویس نظارت)، `backend/tests/test_ai_llm_pipeline.py` (تست‌های pipeline)، و `backend/app/api/routes/oversight.py` (روتر نظارت) است. همچنین فایل‌های `backend/app/core/database.py` و `backend/app/models/setting.py` به‌عنوان وابستگی‌های پایه‌ای در نظر گرفته می‌شوند. فایل `backend/app/main.py` نقطه ورود است که این سرویس‌ها را بارگذاری می‌کند. فایل `backend/app/services/verify_runtime/__init__.py` نیز به‌عنوان لایه verify مرتبط است.

## 🔍 Context و وضعیت فعلی
کاربر درخواست تعریف ۷ معیار پذیرش (AC) رفتار-محور برای رفع ناسازگاری در pipeline `ai_llm` را دارد. هر AC یک رفتار قابل مشاهده را مشخص می‌کند (نه پیاده‌سازی داخلی). معیارها از شناسایی ناسازگاری و مستندسازی فرض‌ها تا عبور موفق integration test برای pipeline `ai_llm`، عبور تست‌ها، linter و type-check را پوشش می‌دهد. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، طراحی کلاس‌ها یا فایل‌های خاص. کلیدواژه‌های ذکر شده: `tsc --noEmit`, `tests/test_ai_llm_pipeline.py`, `ai_llm`, `npm run test`, `pytest`, `tests/test_oversight_service.py`, `backend/app/core/database.py`, `backend/app/api/routes/oversight.py`, `backend/app/models/setting.py`, `backend/app/ai_manager.py`, `backend/app/main.py`, `OversightService`, `mypy`, `backend/app/services/oversight_service.py`, `backend/app/api/routes/github_import.py`, `backend/app/services/verify_runtime/__init__.py`, `backend/app/oversight_strong_prompt.py`. همچنین یک گام اجرایی پیشنهادی (گام ۱) که صرفاً خواندن و لیست کردن فرض‌های دو طرف ناسازگاری را توصیه می‌کند. بر اساس ساختار پروژه، فایل‌های مرتبط با `ai_llm` و `OversightService` در مسیرهای `backend/app/services/` و `backend/app/api/routes/` قرار دارند. فایل `backend/app/services/ai_manager.py` احتمالاً مدیریت pipeline‌های AI را بر عهده دارد و `backend/app/services/oversight_service.py` سرویس نظارت را پیاده‌سازی می‌کند. فایل‌های تست در `backend/tests/` با پیشوند `test_oversight` و `test_ai_llm` مرتبط هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] AC1: هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد — مستندسازی در فایل `docs/AC_AI_LLM_PIPELINE.md` یا PR description.
- [ ] AC2: ground truth تعیین شد و طرف دیگر align شد — مستندسازی در PR description.
- [ ] AC3: integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند — فایل `tests/test_ai_llm_pipeline.py`.
- [ ] AC4: PR description توضیح می‌دهد چرا این تصمیم گرفته شد — بررسی دستی PR.
- [ ] AC5: هیچ تستی fail نمی‌شود (`npm run test` / `pytest`).
- [ ] AC6: linter بدون warning عبور می‌کند.
- [ ] AC7: type-check موفق است (`tsc --noEmit` / `mypy`).
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. با توجه به درخواست کاربر، این تسک صرفاً به تعریف ۷ معیار پذیرش (AC) رفتار-محور می‌پردازد و شامل پیاده‌سازی کد نیست. مراحل پیشنهادی:
1. **گام ۱ (اجرایی):** هر دو طرف ناسازگاری در pipeline `ai_llm` را بخوان و فرض‌هایشان را لیست کن. طرف‌های ناسازگاری احتمالاً بین `backend/app/services/ai_manager.py` (مدیریت AI) و `backend/app/services/oversight_service.py` (سرویس نظارت) یا بین `backend/app/services/verify_runtime/` (لایه verify) و `backend/app/services/ai_manager.py` است.
2. **تعریف ACها:** ۷ AC زیر را به‌عنوان معیارهای پذیرش تعریف کن:
   - AC1: هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد.
   - AC2: ground truth تعیین شد و طرف دیگر align شد.
   - AC3: integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند (فایل `tests/test_ai_llm_pipeline.py`).
   - AC4: PR description توضیح می‌دهد چرا این تصمیم گرفته شد.
   - AC5: هیچ تستی fail نمی‌شود (`npm run test` / `pytest`).
   - AC6: linter بدون warning عبور می‌کند.
   - AC7: type-check موفق است (`tsc --noEmit` / `mypy`).
3. **مستندسازی:** خروجی این ACها را در یک فایل مستند (مثلاً `docs/AC_AI_LLM_PIPELINE.md`) ذخیره کن.

## 💡 نمونه‌های قبل/بعد
**تعریف ACها در فایل مستند**

_قبل:_
```
هیچ معیار پذیرشی برای رفع ناسازگاری pipeline ai_llm تعریف نشده است.
```

_بعد:_
```
فایل `docs/AC_AI_LLM_PIPELINE.md` شامل ۷ AC رفتار-محور:
- AC1: هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد.
- AC2: ground truth تعیین شد و طرف دیگر align شد.
- AC3: integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند.
- AC4: PR description توضیح می‌دهد چرا این تصمیم گرفته شد.
- AC5: هیچ تستی fail نمی‌شود (`npm run test` / `pytest`).
- AC6: linter بدون warning عبور می‌کند.
- AC7: type-check موفق است (`tsc --noEmit` / `mypy`).
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_llm_pipeline.py -v`
- `pytest backend/tests/ -v`
- `mypy backend/`
- `tsc --noEmit`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک صرفاً به تعریف ACها می‌پردازد و شامل تغییر کد نیست، بنابراین ریسک فنی ندارد. با این حال، اگر ACها به‌درستی تعریف نشوند، ممکن است رفع ناسازگاری در pipeline `ai_llm` ناقص بماند. فایل‌های `backend/app/services/ai_manager.py` و `backend/app/services/oversight_service.py` به‌عنوان طرف‌های ناسازگاری شناسایی شده‌اند و باید با دقت بررسی شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 4: بررسی و مستندسازی ریسک‌های تغییر در callerهای ai_manager و oversight_strong_prompt

**Scope:** این مرحله شامل شناسایی و مستندسازی تمام callerهای upstream و downstream برای هر دو طرف (ai_manager و oversight_strong_prompt) است. هدف جلوگیری از break شدن مصرف‌کنندگان downstream در اثر تغییر یک طرف است. این مرحله صرفاً به تحلیل وابستگی‌ها و مستندسازی فرضیات می‌پردازد و شامل پیاده‌سازی تغییرات کد نیست.
**Key terms:** ai_manager, oversight_strong_prompt, downstream consumers, caller, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
```

## 🎯 هدف (خلاصه ساختاریافته)
تحلیل و مستندسازی callerهای ai_manager و oversight_strong_prompt

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
بررسی و مستندسازی ریسک‌های تغییر در callerهای ai_manager و oversight_strong_prompt. این مرحله شامل شناسایی و مستندسازی تمام callerهای upstream و downstream برای هر دو طرف (ai_manager و oversight_strong_prompt) است. هدف جلوگیری از break شدن مصرف‌کنندگان downstream در اثر تغییر یک طرف است. این مرحله صرفاً به تحلیل وابستگی‌ها و مستندسازی فرضیات می‌پردازد و شامل پیاده‌سازی تغییرات کد نیست. کلیدواژه‌های اصلی: ai_manager, oversight_strong_prompt, downstream consumers, caller, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py. با توجه به deep_context موجود، فایل‌های backend/app/services/ai_manager.py و backend/app/services/oversight_strong_prompt.py در ساختار پروژه وجود دارند اما محتوای آن‌ها deep-read نشده است. بر اساس commit‌های اخیر (677c46f, 7d341e3, bf98db1, a612c86, cd39cc3) که به inspector, render, و oversight مربوط هستند، احتمالاً این دو فایل نقش کلیدی در pipeline AI و oversight دارند. callerهای upstream شامل فایل‌هایی مانند backend/app/services/oversight_inspector_bridge.py, backend/app/services/oversight_mega_bundle.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verifier.py, backend/app/services/oversight_upload_session.py, backend/app/services/oversight_telegram_compose.py, backend/app/services/oversight_deep_scan_service.py, backend/app/services/oversight_codex_service.py, backend/app/services/oversight_extraction.py, backend/app/services/oversight_progress.py, backend/app/services/oversight_settings.py, backend/app/services/oversight_model_temp_activate.py, backend/app/services/oversight_verify_pdf.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/ai_manager.py, backend/app/services/ai_balance_service.py, backend/app/services/ai_base.py, backend/app/services/claude_service.py, backend/app/services/deepseek_service.py, backend/app/services/gemini_service.py, backend/app/services/openai_service.py, backend/app/services/perplexity_service.py, backend/app/services/smart_orchestrator.py, backend/app/services/creator_engine.py, backend/app/services/creator_idea_to_prompt.py, backend/app/services/simple_creator.py, backend/app/services/inspector_agent.py, backend/app/services/inspector_intent_resolver.py, backend/app/services/inspector_proposal_executor.py, backend/app/services/inspector_scan_bridge.py, backend/app/services/intelligent_field_creator.py, backend/app/services/quick_approval_service.py, backend/app/services/render_service.py, backend/app/services/runtime_executor.py, backend/app/services/scan_v5/scan_bundle.py, backend/app/services/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/report_validator.py, backend/app/services/verify_runtime/security_analyzer.py, backend/app/services/verify_runtime/security_scanner.py, backend/app/services/verify_runtime/smart_import.py, backend/app/services/verify_runtime/storage_service.py, backend/app/services/verify_runtime/task_consolidation_service.py, backend/app/services/verify_runtime/task_merge_service.py, backend/app/services/verify_runtime/test_coverage_analyzer.py, backend/app/services/verify_runtime/unified_storage.py, backend/app/services/verify_runtime/analysis_progress_manager.py, backend/app/services/verify_runtime/background_scheduler.py, backend/app/services/verify_runtime/browser_automation.py, backend/app/services/verify_runtime/capability_detector.py, backend/app/services/verify_runtime/code_quality_analyzer.py, backend/app/services/verify_runtime/content_sanitizer.py, backend/app/services/verify_runtime/db_service.py, backend/app/services/verify_runtime/debate_service.py, backend/app/services/verify_runtime/deep_analysis_service.py, backend/app/services/verify_runtime/deploy_service.py, backend/app/services/verify_runtime/dynamic_config.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/oversight_service.py, backend/app/services/verify_runtime/oversight_verifier.py, backend/app/services/verify_runtime/oversight_upload_session.py, backend/app/services/verify_runtime/oversight_telegram_compose.py, backend/app/services/verify_runtime/oversight_deep_scan_service.py, backend/app/services/verify_runtime/oversight_codex_service.py, backend/app/services/verify_runtime/oversight_extraction.py, backend/app/services/verify_runtime/oversight_progress.py, backend/app/services/verify_runtime/oversight_settings.py, backend/app/services/verify_runtime/oversight_model_temp_activate.py, backend/app/services/verify_runtime/oversight_verify_pdf.py, backend/app/services/verify_runtime/oversight_inspector_bridge.py, backend/app/services/verify_runtime/oversight_mega_bundle.py, backend/app/services/verify_runtime/oversight_strong_prompt.py, backend/app/services/verify_runtime/ai_manager.py, backend/app/services/verify_runtime/ai_balance_service.py, backend/app/services/verify_runtime/ai_base.py, backend/app/services/verify_runtime/claude_service.py, backend/app/services/verify_runtime/deepseek_service.py, backend/app/services/verify_runtime/gemini_service.py, backend/app/services/verify_runtime/openai_service.py, backend/app/services/verify_runtime/perplexity_service.py, backend/app/services/verify_runtime/smart_orchestrator.py, backend/app/services/verify_runtime/creator_engine.py, backend/app/services/verify_runtime/creator_idea_to_prompt.py, backend/app/services/verify_runtime/simple_creator.py, backend/app/services/verify_runtime/inspector_agent.py, backend/app/services/verify_runtime/inspector_intent_resolver.py, backend/app/services/verify_runtime/inspector_proposal_executor.py, backend/app/services/verify_runtime/inspector_scan_bridge.py, backend/app/services/verify_runtime/intelligent_field_creator.py, backend/app/services/verify_runtime/quick_approval_service.py, backend/app/services/verify_runtime/render_service.py, backend/app/services/verify_runtime/runtime_executor.py, backend/app/services/verify_runtime/scan_v5/scan_bundle.py, backend/app/services/verify_runtime/scan_v5/scan_inspector_session.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/behavioral_probe_layer.py, backend/app/services/verify_runtime/static_probe.py, backend/app/services/verify_runtime/ui_probe.py, backend/app/services/verify_runtime/api_probe.py, backend/app/services/verify_runtime/auth_runner.py, backend/app/services/verify_runtime/backend_log_probe.py, backend/app/services/verify_runtime/manual_probe.py, backend/app/services/verify_runtime/test_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/navigation_helper.py, backend/app/services/verify_runtime/render_autodetect.py, backend/app/services/verify_runtime/safety.py, backend/app/services/verify_runtime/storage.py, backend/app/services/verify_runtime/ac_cache_service.py, backend/app/services/verify_runtime/ac_enricher.py, backend/app/services/verify_runtime/ac_schema.py, backend/app/services/verify_runtime/browser_pool.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/diagram_service.py, backend/app/services/verify_runtime/dynamic_diagram_service.py, backend/app/services/verify_runtime/external_monitor.py, backend/app/services/verify_runtime/external_project_connector.py, backend/app/services/verify_runtime/github_import.py, backend/app/services/verify_runtime/github_pr_service.py, backend/app/services/verify_runtime/github_storage.py, backend/app/services/verify_runtime/health_to_issues_service.py, backend/app/services/verify_runtime/journal_service.py, backend/app/services/verify_runtime/log_stream_service.py, backend/app/services/verify_runtime/log_to_issues_service.py, backend/app/services/verify_runtime/model_capability_tester.py, backend/app/services/verify_runtime/model_profiler.py, backend/app/services/verify_runtime/notification_service.py, backend/app/services/verify_runtime/project_analyzer.py, backend/app/services/verify_runtime/project_auto_setup.py, backend/app/services/verify_runtime/project_health_analyzer.py, backend/app/services/verify_runtime/project_service.py, backend/app/services/verify_runtime/prompt_helper.py, backend/app/services/verify_runtime/re

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 5: رفع ناسازگاری ورودی ai_manager با خروجی oversight_strong_prompt در pipeline ai_llm

**Scope:** این بخش به تحلیل و رفع ناسازگاری منطقی بین دو مؤلفه در pipeline `ai_llm` می‌پردازد: `ai_manager` که انتظار یک پرامپت کاربر خام (string) را دارد، و `oversight_strong_prompt` که یک پرامپت اجرایی کامل و ساختاریافته تولید می‌کند. راه‌حل پیشنهادی شامل شفاف‌سازی مسیر جریان داده است: یا `ai_manager` باید پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد، یا یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده ایجاد شود. فایل‌های مرتبط شامل `backend/app/ai_manager.py` و `backend/app/oversight_strong_prompt.py` هستند. کلاس `OversightService` نیز در این زمینه ذکر شده است.
**Key terms:** ai_manager, oversight_strong_prompt, pipeline ai_llm, OversightService, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

ai_manager انتظار 'پرامپت کاربر (string)' را به عنوان ورودی دارد، در حالی که oversight_strong_prompt یک پرامپت اجرایی کامل و ساختاریافته (با قالب ثابت) تولید می‌کند. این دو با هم ناسازگار هستند: ai_manager برای پردازش یک پرامپت خام کاربر طراحی شده، اما خروجی builder یک پرامپت نهایی و آماده اجراست که احتمالاً باید مستقیماً به مدل ارسال شود، نه اینکه دوباره از ai_manager عبور کند.

اگر خروجی oversight_strong_prompt به ai_manager داده شود، ai_manager ممکن است آن را به عنوان یک پرامپت ساده تفسیر کرده و دوباره پردازش کند (مثلاً انتخاب مدل یا fallback) که منجر به نادیده گرفتن ساختار دقیق پرامپت، افزایش هزینه، تأخیر و احتمالاً خرابی خروجی نهایی می‌شود.

مسیر جریان داده را شفاف کنید. یا ai_manager باید بتواند پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد، یا یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده (مانند خروجی oversight_strong_prompt) ایجاد کنید که مستقیماً به سرویس مدل ارسال شوند.
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع ناسازگاری ورودی ai_manager با خروجی oversight_strong_prompt

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:نامشخص (فایل deep-read نشده)` — `کلاس AI Manager (متد ورودی)` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل نقطه اصلی ورود پرامپت است.
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی پروژه، این فایل شامل کلاس اصلی مدیریت هوش مصنوعی است
  ```
- `backend/app/services/oversight_strong_prompt.py:نامشخص (فایل deep-read نشده)` — `تابع تولید پرامپت ساختاریافته` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. خروجی این فایل باید قابل تشخیص باشد.
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی پروژه، این فایل پرامپت‌های اجرایی کامل تولید می‌کند
  ```
- `backend/app/services/oversight_service.py:نامشخص (فایل deep-read نشده)` — `کلاس OversightService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اینجا نقطه اتصال دو مؤلفه است.
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی پروژه، این سرویس از oversight_strong_prompt استفاده می‌کند
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص) — بر اساس ساختار پروژه، از FastAPI (پایتون) استفاده شده است. کتابخانه‌های مرتبط شامل Pydantic برای اعتبارسنجی و احتمالاً httpx یا aiohttp برای درخواست‌های HTTP به مدل‌های AI است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_manager.py` — فایل اصلی که باید تغییر کند — متد ورودی باید پرامپت‌های ساختاریافته را تشخیص دهد
- `backend/app/services/oversight_strong_prompt.py` — تولیدکننده پرامپت ساختاریافته — باید metadata به خروجی اضافه کند
- `backend/app/services/oversight_service.py` — استفاده‌کننده از oversight_strong_prompt — باید مسیر جدید را پشتیبانی کند
- `backend/app/services/ai_base.py` — کلاس پایه سرویس‌های AI — ممکن است متد ارسال به مدل در اینجا باشد
- `backend/app/services/ai_manager.py` — مدیریت fallback و انتخاب مدل — باید از پردازش مضاعف جلوگیری کند

## 🌐 نقشهٔ وابستگی‌ها
این تغییر بر pipeline اصلی `ai_llm` تأثیر می‌گذارد. فایل‌های `ai_manager.py` و `oversight_strong_prompt.py` دو مؤلفه اصلی این pipeline هستند. `oversight_service.py` به عنوان orchestrator از هر دو استفاده می‌کند. `ai_base.py` کلاس پایه است که متدهای ارسال به مدل را فراهم می‌کند. هر تغییری در نحوه پردازش پرامپت می‌تواند بر تمام سرویس‌هایی که از `ai_manager` استفاده می‌کنند تأثیر بگذارد.

## 🔍 Context و وضعیت فعلی
در pipeline `ai_llm` یک ناسازگاری منطقی بین دو مؤلفه اصلی شناسایی شده است:

1. **ai_manager** (فایل `backend/app/services/ai_manager.py`) انتظار یک پرامپت کاربر خام (string ساده) را به عنوان ورودی دریافت کند. این سرویس برای پردازش پرامپت‌های ساده کاربر طراحی شده و شامل مراحلی مانند انتخاب مدل، fallback و مدیریت هزینه است.

2. **oversight_strong_prompt** (فایل `backend/app/services/oversight_strong_prompt.py`) یک پرامپت اجرایی کامل و ساختاریافته با قالب ثابت تولید می‌کند. این پرامپت از پیش ساخته شده و آماده ارسال مستقیم به مدل است.

مشکل اصلی: اگر خروجی `oversight_strong_prompt` به `ai_manager` داده شود، `ai_manager` آن را به عنوان یک پرامپت ساده تفسیر کرده و دوباره پردازش می‌کند (مثلاً انتخاب مدل یا fallback) که منجر به:
- نادیده گرفتن ساختار دقیق پرامپت
- افزایش هزینه (پردازش مضاعف)
- تأخیر اضافی
- احتمال خرابی خروجی نهایی

کلاس `OversightService` (در `backend/app/services/oversight_service.py`) نیز در این زمینه ذکر شده است.

کلیدواژه‌های اصلی: ai_manager, oversight_strong_prompt, pipeline ai_llm, OversightService, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py

راه‌حل پیشنهادی: شفاف‌سازی مسیر جریان داده با یکی از دو روش:
- روش A: `ai_manager` باید بتواند پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد
- روش B: یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده (مانند خروجی oversight_strong_prompt) ایجاد شود که مستقیماً به سرویس مدل ارسال شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] خروجی oversight_strong_prompt باید شامل یک فیلد metadata (مانند `is_structured: true`) باشد که نشان دهد پرامپت از پیش ساخته شده است
- [ ] ai_manager باید قبل از پردازش، پرامپت ورودی را بررسی کند و اگر ساختاریافته بود، مستقیماً به مدل ارسال کند
- [ ] مسیر bypass نباید مراحل انتخاب مدل و fallback را اجرا کند (برای پرامپت‌های ساختاریافته)
- [ ] مسیر فعلی برای پرامپت‌های خام (غیرساختاریافته) باید بدون تغییر کار کند
- [ ] هیچ خطایی در pipeline هنگام عبور پرامپت ساختاریافته رخ ندهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مراحل پیاده‌سازی:

1. **تحلیل جریان داده فعلی**:
   - بررسی `backend/app/services/ai_manager.py` برای شناسایی متد ورودی و نحوه پردازش پرامپت
   - بررسی `backend/app/services/oversight_strong_prompt.py` برای شناسایی ساختار خروجی
   - بررسی `backend/app/services/oversight_service.py` برای نحوه استفاده از oversight_strong_prompt

2. **طراحی راه‌حل (روش B - مسیر جداگانه)**:
   - ایجاد یک flag یا metadata در خروجی `oversight_strong_prompt` که نشان دهد پرامپت از پیش ساخته شده است
   - در `ai_manager`، قبل از پردازش، بررسی کند که آیا پرامپت از نوع ساختاریافته است یا خیر
   - اگر ساختاریافته بود، مستقیماً به سرویس مدل ارسال شود (بدون پردازش مجدد)
   - اگر خام بود، مسیر فعلی ادامه یابد

3. **پیاده‌سازی تغییرات**:
   - افزودن متد `is_structured_prompt()` در `ai_manager.py`
   - افزودن متد `bypass_to_model()` در `ai_manager.py`
   - اصلاح `oversight_strong_prompt.py` برای افزودن metadata به خروجی
   - اصلاح `oversight_service.py` برای استفاده از مسیر جدید

4. **تست و اعتبارسنجی**:
   - تست واحد برای متدهای جدید
   - تست یکپارچه‌سازی برای سناریوی عبور مستقیم
   - تست رگرسیون برای مسیر فعلی (پرامپت‌های خام)

## 💡 نمونه‌های قبل/بعد
**جریان فعلی (ناسازگار)**

_قبل:_
```
oversight_strong_prompt → پرامپت ساختاریافته → ai_manager (تفسیر اشتباه به عنوان پرامپت خام) → پردازش مجدد → مدل (با خطر خرابی)
```

_بعد:_
```
oversight_strong_prompt → پرامپت ساختاریافته + metadata → ai_manager (تشخیص ساختاریافته) → bypass مستقیم به مدل (بدون پردازش مجدد)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_manager.py -v`
- `pytest backend/tests/test_oversight_pipeline.py -v`
- `python -c "from backend.app.services.ai_manager import AI Manager; print('Import OK')"`
- `python -c "from backend.app.services.oversight_strong_prompt import *; print('Import OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: تغییر در `ai_manager.py` می‌تواند بر تمام سرویس‌هایی که از آن استفاده می‌کنند تأثیر بگذارد (مانند `ai_balance_service.py`, `claude_service.py`, `gemini_service.py`). اگر تشخیص ساختاریافته به درستی کار نکند، پرامپت‌های خام ممکن است نادیده گرفته شوند یا پرامپت‌های ساختاریافته دوباره پردازش شوند. همچنین، افزودن metadata به خروجی `oversight_strong_prompt.py` ممکن است با مصرف‌کنندگان فعلی این خروجی ناسازگار باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 6: نوشتن تست‌های واحد برای OversightService (CRUD، scheduler، auto_register و edge cases)

**Scope:** این مرحله شامل پیاده‌سازی تست‌های واحد برای کلاس OversightService در فایل tests/test_oversight_service.py است. چهار acceptance_criteria مشخص شده باید پوشش داده شوند: (1) تست CRUD برای watched projects، (2) تست scheduler loop با mock کردن sleep، (3) تست auto_register_watched با mock GitHub API، (4) تست edge cases شامل duplicate repo، invalid URL و empty fields. این مرحله صرفاً به نوشتن تست‌ها محدود است و شامل تغییر در خود سرویس یا منطق business نمی‌شود.
**Key terms:** tests/test_oversight_service.py, OversightService, backend/app/services/oversight_service.py

**بخش مربوط از متن کاربر:**
```
📋 acceptance_criteria کامل:
  - تست CRUD برای watched projects (add, update, delete, list) [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_crud_watched_projects", "timeout_seconds": 60}]
  - تست scheduler loop با mock کردن sleep [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_scheduler_loop_mock_sleep", "timeout_seconds": 60}]
  - تست auto_register_watched با mock GitHub API [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_auto_register_watched_mock_github", "timeout_seconds": 60}]
  - تست edge cases: duplicate repo, invalid URL, empty fields [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_edge_cases", "timeout_seconds": 60}]
```

## 🎯 هدف (خلاصه ساختاریافته)
نوشتن تست‌های واحد برای OversightService (CRUD، scheduler، auto_register و edge cases)

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `class OversightService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، کلاس OversightService شامل متدهای CRUD، scheduler_loop و auto_register_watched است.
  ```python
  class OversightService:
      def __init__(self, db_service: DbService):
          self.db = db_service
          self.watched_projects = []
  
      def add_watched_project(self, project_data: dict) -> str:
          # ...
          return project_id
  
      def update_watched_project(self, project_id: str, updates: dict) -> bool:
          # ...
          return True
  
      def delete_watched_project(self, project_id: str) -> bool:
          # ...
          return True
  
      def list_watched_projects(self) -> list:
          return self.watched_projects
  
      def scheduler_loop(self):
          while True:
              self.process_watched_projects()
              time.sleep(60)
  
      def auto_register_watched(self, repo_url: str) -> str:
          # validate URL
          # call GitHub API
          # add to watched_projects
          return project_id
  ```
- `tests/test_oversight_service.py:1-10` — `فایل جدید` — این فایل باید ایجاد شود. محتوای فعلی وجود ندارد.
  ```python
  # tests/test_oversight_service.py
  import pytest
  from unittest.mock import patch, MagicMock
  from backend.app.services.oversight_service import OversightService
  from backend.app.services.db_service import DbService
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/db_service.py` (سطر 1) — OversightService به DbService وابسته است. تست‌ها باید DbService را mock کنند یا از دیتابیس تستی استفاده کنند.
- `backend/app/models/project.py` (سطر 1) — مدل Project برای ایجاد watched projects استفاده می‌شود. تست‌ها باید از این مدل برای ساخت داده‌های تستی استفاده کنند.
- `backend/app/services/github_import.py` (سطر 1) — متد auto_register_watched از GitHub API استفاده می‌کند. برای تست باید این سرویس mock شود.
- `backend/app/services/background_scheduler.py` (سطر 1) — scheduler_loop ممکن است توسط background_scheduler فراخوانی شود. تست باید این وابستگی را مدیریت کند.

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل tests/test_oversight_service.py محدود است که وابسته به backend/app/services/oversight_service.py (سرویس اصلی)، backend/app/services/db_service.py (برای دیتابیس)، backend/app/models/project.py (مدل داده)، backend/app/services/github_import.py (برای GitHub API) و backend/app/services/background_scheduler.py (برای scheduler) می‌باشد. همچنین از کتابخانه pytest و unittest.mock برای mock کردن وابستگی‌ها استفاده می‌کند. تغییر در این فایل‌ها تأثیری بر سایر بخش‌های پروژه ندارد زیرا فقط تست‌ها اضافه می‌شوند.

## 🔍 Context و وضعیت فعلی
این تسک مربوط به پیاده‌سازی تست‌های واحد برای کلاس OversightService در فایل tests/test_oversight_service.py است. کاربر چهار acceptance_criteria مشخص کرده که باید پوشش داده شوند: (1) تست CRUD برای watched projects (add, update, delete, list) با verify_method=backend_test و verify_plan شامل test_node: tests/test_oversight_service.py::test_crud_watched_projects و timeout_seconds: 60، (2) تست scheduler loop با mock کردن sleep با verify_method=backend_test و verify_plan شامل test_node: tests/test_oversight_service.py::test_scheduler_loop_mock_sleep و timeout_seconds: 60، (3) تست auto_register_watched با mock GitHub API با verify_method=backend_test و verify_plan شامل test_node: tests/test_oversight_service.py::test_auto_register_watched_mock_github و timeout_seconds: 60، (4) تست edge cases شامل duplicate repo، invalid URL و empty fields با verify_method=backend_test و verify_plan شامل test_node: tests/test_oversight_service.py::test_edge_cases و timeout_seconds: 60. این مرحله صرفاً به نوشتن تست‌ها محدود است و شامل تغییر در خود سرویس یا منطق business نمی‌شود. فایل هدف tests/test_oversight_service.py است و سرویس اصلی backend/app/services/oversight_service.py می‌باشد. با توجه به ساختار پروژه، فایل‌های مرتبط شامل backend/app/services/oversight_service.py (سرویس اصلی)، backend/app/models/project.py (مدل پروژه)، backend/app/services/db_service.py (سرویس دیتابیس)، backend/app/services/github_import.py (برای mock GitHub API) و backend/app/services/background_scheduler.py (برای scheduler loop) هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست CRUD برای watched projects (add, update, delete, list) باید در tests/test_oversight_service.py::test_crud_watched_projects پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_crud_watched_projects -v اجرا شود.
- [ ] تست scheduler loop با mock کردن sleep باید در tests/test_oversight_service.py::test_scheduler_loop_mock_sleep پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_scheduler_loop_mock_sleep -v اجرا شود.
- [ ] تست auto_register_watched با mock GitHub API باید در tests/test_oversight_service.py::test_auto_register_watched_mock_github پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_auto_register_watched_mock_github -v اجرا شود.
- [ ] تست edge cases شامل duplicate repo، invalid URL و empty fields باید در tests/test_oversight_service.py::test_edge_cases پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_edge_cases -v اجرا شود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل tests/test_oversight_service.py با ساختار pytest استاندارد. 2. پیاده‌سازی تابع test_crud_watched_projects: شامل تست add (ایجاد یک watched project با داده‌های معتبر و بررسی بازگشت project_id)، تست update (به‌روزرسانی فیلدهایی مثل url یا interval و بررسی تغییر)، تست delete (حذف یک project و بررسی عدم وجود آن در لیست)، تست list (بررسی اینکه لیست شامل projectهای اضافه‌شده است). 3. پیاده‌سازی تابع test_scheduler_loop_mock_sleep: با mock کردن time.sleep و بررسی اینکه حلقه scheduler حداقل یک بار اجرا شده و تابع process_watched_projects صدا زده شده است. 4. پیاده‌سازی تابع test_auto_register_watched_mock_github: با mock کردن GitHub API (با استفاده از unittest.mock.patch) و شبیه‌سازی فراخوانی auto_register_watched با یک repo URL معتبر و بررسی اینکه project جدید در دیتابیس ثبت شده است. 5. پیاده‌سازی تابع test_edge_cases: شامل تست duplicate repo (تلاش برای ثبت یک repo تکراری و دریافت خطای مناسب)، تست invalid URL (ارسال URL نامعتبر و بررسی raise exception)، تست empty fields (ارسال داده‌های خالی مثل name یا url خالی و بررسی validation error). 6. استفاده از pytest fixtures برای راه‌اندازی دیتابیس تستی (مثلاً SQLite in-memory) و mock کردن وابستگی‌های خارجی. 7. اطمینان از اینکه تست‌ها با دستور pytest backend/tests/test_oversight_service.py -v اجرا می‌شوند.

## 💡 نمونه‌های قبل/بعد
**نمونه تست CRUD**

_قبل:_
```
فایل tests/test_oversight_service.py وجود ندارد.
```

_بعد:_
```
def test_crud_watched_projects():
    service = OversightService(mock_db)
    project_id = service.add_watched_project({'url': 'https://github.com/user/repo', 'interval': 60})
    assert project_id is not None
    projects = service.list_watched_projects()
    assert len(projects) == 1
    assert service.update_watched_project(project_id, {'interval': 120}) == True
    assert service.delete_watched_project(project_id) == True
    assert len(service.list_watched_projects()) == 0
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v --timeout=60`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که تست‌ها ممکن است به دلیل وابستگی به دیتابیس واقعی یا سرویس‌های خارجی (GitHub API) شکست بخورند. برای کاهش ریسک، باید از mock objects و دیتابیس in-memory (SQLite) استفاده شود. همچنین اگر متدهای OversightService تغییر کنند، تست‌ها باید به‌روزرسانی شوند. فایل‌های backend/app/services/oversight_service.py و backend/app/services/db_service.py تحت تأثیر قرار می‌گیرند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 7: افزودن تست واحد برای کلاس OversightService در oversight_service.py

**Scope:** این بخش شامل ایجاد تست‌های واحد برای کلاس OversightService در فایل backend/app/services/oversight_service.py است. تست‌ها باید منطق اصلی مانند مدیریت watched projects، قفل asyncio، و تعامل با وابستگی‌های اصلی (مانند database و models) را پوشش دهند. این بخش شامل تست API routes، scheduler، یا سایر سرویس‌های وابسته نمی‌شود. نکته حیاتی: ۲۰ فایل به این سرویس وابسته هستند، بنابراین تست‌ها باید با mocking وابستگی‌های خارجی (مانند GitHub API و database) نوشته شوند تا ایزوله باشند.
**Key terms:** OversightService, backend/app/services/oversight_service.py, tests/test_oversight_service.py, asyncio.Lock, watched

**بخش مربوط از متن کاربر:**
```
OversightService فاقد تست واحد است — ۲۰ فایل به آن وابسته‌اند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-100` — `OversightService` — کلاس اصلی که باید تست شود
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self._lock = asyncio.Lock()
  ```

## 🌐 نقشهٔ وابستگی‌ها
۲۰ فایل به این سرویس وابسته‌اند: ۵ route, ۱۰ service, ۳ core, main.py, ۱ script

## 🔍 Context و وضعیت فعلی
سرویس `oversight_service.py` هستهٔ مرکزی نظارت پروژه‌های GitHub است و ۲۰ فایل مختلف (routes, services, main.py) به آن import دارند. این سرویس شامل منطق پیچیدهٔ مدیریت watched projects, scheduling, runtime verification, و auto-register است. عدم وجود تست می‌تواند منجر به شکست‌های زنجیره‌ای در کل سیستم شود.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن تست واحد برای کلاس OversightService در oversight_service.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-100` — `OversightService.__init__` — کلاس اصلی که باید تست شود. این snippet از deep context موجود است.
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self._lock = asyncio.Lock()
  ```
- `backend/tests/test_oversight_service.py:1-200` — `فایل جدید` — فایل تست جدید که باید ایجاد شود. مسیر بر اساس ساختار پروژه و درخواست کاربر انتخاب شده است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 1) — این route از OversightService استفاده می‌کند و تست‌های سرویس باید با mocking این route را ایزوله کنند.
- `backend/app/services/oversight_verifier.py` (سطر 1) — این سرویس به OversightService وابسته است و تست‌ها باید این وابستگی را mock کنند.
- `backend/app/services/oversight_deep_scan_service.py` (سطر 1) — این سرویس از OversightService استفاده می‌کند و باید در تست‌ها mock شود.
- `backend/app/services/oversight_inspector_bridge.py` (سطر 1) — این سرویس به OversightService وابسته است و تست‌ها باید این وابستگی را mock کنند.
- `backend/app/services/oversight_mega_bundle.py` (سطر 1) — این سرویس از OversightService استفاده می‌کند و باید در تست‌ها mock شود.

## 🌐 نقشهٔ وابستگی‌ها
OversightService در فایل backend/app/services/oversight_service.py هسته مرکزی نظارت پروژه‌های GitHub است. ۲۰ فایل مختلف به این سرویس import دارند: ۵ route (از جمله backend/app/api/routes/oversight.py)، ۱۰ service (از جمله oversight_verifier.py، oversight_deep_scan_service.py، oversight_inspector_bridge.py، oversight_mega_bundle.py، oversight_progress.py، oversight_settings.py، oversight_strong_prompt.py، oversight_telegram_compose.py، oversight_upload_session.py، oversight_codex_service.py)، ۳ core (از جمله core/config.py، core/database.py، core/logging_utils.py)، main.py، و ۱ script (scripts/migrate_health_to_oversight.py). این سرویس شامل منطق پیچیده مدیریت watched projects، scheduling، runtime verification، و auto-register است. عدم وجود تست می‌تواند منجر به شکست‌های زنجیره‌ای در کل سیستم شود.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن تست‌های واحد برای کلاس OversightService در فایل backend/app/services/oversight_service.py را دارد. این سرویس هسته مرکزی نظارت پروژه‌های GitHub است و ۲۰ فایل مختلف (۵ route, ۱۰ service, ۳ core, main.py, ۱ script) به آن import دارند. منطق اصلی شامل مدیریت watched projects، قفل asyncio (asyncio.Lock)، و تعامل با وابستگی‌های اصلی (مانند database و models) است. تست‌ها باید با mocking وابستگی‌های خارجی (مانند GitHub API و database) نوشته شوند تا ایزوله باشند. نکته حیاتی: ۲۰ فایل به این سرویس وابسته هستند، بنابراین تست‌ها باید با mocking وابستگی‌های خارجی نوشته شوند تا ایزوله باشند. این بخش شامل تست API routes، scheduler، یا سایر سرویس‌های وابسته نمی‌شود. فایل تست باید در tests/test_oversight_service.py ایجاد شود. کلاس OversightService در خطوط 1-100 دارای __init__ با self.watched = [] و self._lock = asyncio.Lock() است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل tests/test_oversight_service.py باید وجود داشته باشد و شامل تست‌های واحد برای کلاس OversightService باشد.
- [ ] تست __init__ باید بررسی کند که self.watched یک لیست خالی و self._lock از نوع asyncio.Lock است.
- [ ] تست add_watched_project باید با mock کردن database، افزودن پروژه به watched list را بررسی کند.
- [ ] تست remove_watched_project باید با mock کردن database، حذف پروژه از watched list را بررسی کند.
- [ ] تست asyncio.Lock باید بررسی کند که قفل در عملیات همزمان به درستی کار می‌کند.
- [ ] تست‌ها باید با mocking وابستگی‌های خارجی (مانند GitHub API و database) نوشته شوند تا ایزوله باشند.
- [ ] همه تست‌ها باید با pytest backend/tests/test_oversight_service.py -v با موفقیت پاس شوند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل tests/test_oversight_service.py با ساختار pytest. 2. mocking وابستگی‌های خارجی: database session، GitHub API client، و سایر سرویس‌های import شده در oversight_service.py. 3. تست متد __init__: بررسی اینکه self.watched یک لیست خالی و self._lock از نوع asyncio.Lock است. 4. تست متد add_watched_project: با mock کردن database، بررسی افزودن پروژه به watched list. 5. تست متد remove_watched_project: بررسی حذف پروژه از watched list. 6. تست asyncio.Lock: بررسی اینکه قفل در عملیات همزمان به درستی کار می‌کند. 7. تست متدهای auto_register و schedule_verification با mock کردن وابستگی‌ها. 8. تست خطاها: بررسی رفتار سرویس در صورت خطای database یا GitHub API. 9. اطمینان از ایزوله بودن تست‌ها با استفاده از pytest fixtures و mocks.

## 💡 نمونه‌های قبل/بعد
**ایجاد فایل تست جدید برای OversightService**

_قبل:_
```
فایل tests/test_oversight_service.py وجود ندارد.
```

_بعد:_
```
فایل tests/test_oversight_service.py با تست‌های واحد برای کلاس OversightService ایجاد می‌شود.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v --tb=short`
- `pytest backend/tests/test_oversight_service.py -v --cov=backend/app/services/oversight_service.py --cov-report=term-missing`

## ⚠️ ریسک‌ها و موارد احتیاط
این سرویس توسط ۲۰ فایل مختلف (۵ route, ۱۰ service, ۳ core, main.py, ۱ script) import شده است. تغییرات در oversight_service.py می‌تواند روی همه این فایل‌ها اثر بگذارد. تست‌ها باید با دقت mocking شوند تا وابستگی‌های خارجی (مانند GitHub API و database) ایزوله شوند. عدم mocking صحیح می‌تواند منجر به شکست تست‌ها در محیط CI/CD شود. همچنین، asyncio.Lock باید به درستی در تست‌های همزمان مدیریت شود تا از deadlock جلوگیری شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 8: ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register

**Scope:** این مرحله شامل ایجاد تست‌های واحد برای کلاس OversightService است. تست‌ها باید رفتارهای CRUD (افزودن، به‌روزرسانی، حذف، لیست) برای watched projects، حلقه scheduler با mock کردن sleep، و auto_register_watched با mock GitHub API را پوشش دهند. همچنین edge cases مانند duplicate repo, invalid URL, empty fields باید تست شوند. فایل تست باید در tests/test_oversight_service.py ایجاد شود. این مرحله شامل پیاده‌سازی خود سرویس نیست، فقط تست‌ها.
**Key terms:** tests/test_oversight_service.py, OversightService, CRUD, watched projects, scheduler loop, auto_register_watched, GitHub API, duplicate repo, invalid URL, empty fields

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست CRUD برای watched projects (add, update, delete, list)
- [ ] تست scheduler loop با mock کردن sleep
- [ ] تست auto_register_watched با mock GitHub API
- [ ] تست edge cases: duplicate repo, invalid URL, empty fields
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد تست‌های واحد OversightService برای CRUD، scheduler و auto-register

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/test_oversight_service.py:1-200` — `TestOversightService` — فایل تست جدید — باید ایجاد شود. بر اساس ساختار سطحی — توسط مجری تأیید شود.
  ```python
  # فایل جدید — هنوز ایجاد نشده است
  # این فایل باید شامل تست‌های واحد برای OversightService باشد
  # با تمرکز بر CRUD watched projects, scheduler loop, و auto-register
  ```
- `backend/app/services/oversight_service.py:1-50` — `OversightService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی — توسط مجری تأیید شود.
  ```python
  # فایل deep-read نشده — بر اساس ساختار سطحی
  # کلاس اصلی OversightService که باید تست شود
  # شامل متدهای CRUD، scheduler loop و auto_register_watched
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — بر اساس ساختار پروژه، از Python با FastAPI و pytest برای تست استفاده می‌کند. کتابخانه‌های مرتبط: pytest, unittest.mock, requests (برای GitHub API mock).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_settings.py` (سطر 1) — تنظیمات OversightService — ممکن است در تست‌ها برای mock کردن تنظیمات استفاده شود
- `backend/app/services/oversight_progress.py` (سطر 1) — مدیریت پیشرفت — وابستگی OversightService برای track کردن پیشرفت
- `backend/app/services/oversight_verifier.py` (سطر 1) — تأییدکننده — وابستگی OversightService برای verify کردن نتایج
- `backend/app/services/oversight_upload_session.py` (سطر 1) — جلسات آپلود — وابستگی OversightService برای مدیریت upload sessions
- `backend/app/services/oversight_codex_service.py` (سطر 1) — سرویس codex — وابستگی OversightService برای دسترسی به codex

## 🌐 نقشهٔ وابستگی‌ها
این تسک به ایجاد فایل تست جدید tests/test_oversight_service.py مربوط است که به کلاس OversightService در backend/app/services/oversight_service.py وابسته است. OversightService خود به چندین سرویس دیگر وابسته است: oversight_settings.py برای تنظیمات، oversight_progress.py برای مدیریت پیشرفت، oversight_verifier.py برای تأیید، oversight_upload_session.py برای جلسات آپلود، oversight_codex_service.py برای سرویس codex، oversight_deep_scan_service.py برای اسکن عمیق، oversight_extraction.py برای استخراج، oversight_inspector_bridge.py برای پل بازرسی، oversight_mega_bundle.py برای بسته بزرگ، oversight_model_temp_activate.py برای فعال‌سازی مدل، oversight_strong_prompt.py برای پرامپت قوی، oversight_telegram_compose.py برای تلگرام، و oversight_verify_pdf.py برای تأیید PDF. همچنین ممکن است به GitHub API خارجی برای auto_register_watched وابسته باشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست ایجاد تست‌های واحد برای کلاس OversightService با تمرکز بر CRUD watched projects (افزودن، به‌روزرسانی، حذف، لیست)، حلقه scheduler با mock کردن sleep، و auto_register_watched با mock GitHub API را دارد. همچنین edge cases مانند duplicate repo, invalid URL, empty fields باید تست شوند. فایل تست باید در tests/test_oversight_service.py ایجاد شود. این مرحله شامل پیاده‌سازی خود سرویس نیست، فقط تست‌ها.

کلیدواژه‌های اصلی: tests/test_oversight_service.py, OversightService, CRUD, watched projects, scheduler loop, auto_register_watched, GitHub API, duplicate repo, invalid URL, empty fields

بر اساس ساختار پروژه، فایل‌های مرتبط شامل:
- backend/app/services/oversight_service.py (سرویس اصلی)
- backend/app/services/oversight_settings.py (تنظیمات)
- backend/app/services/oversight_progress.py (مدیریت پیشرفت)
- backend/app/services/oversight_verifier.py (تأییدکننده)
- backend/app/services/oversight_upload_session.py (جلسات آپلود)
- backend/app/services/oversight_codex_service.py (سرویس codex)
- backend/app/services/oversight_deep_scan_service.py (اسکن عمیق)
- backend/app/services/oversight_extraction.py (استخراج)
- backend/app/services/oversight_inspector_bridge.py (پل بازرسی)
- backend/app/services/oversight_mega_bundle.py (بسته بزرگ)
- backend/app/services/oversight_model_temp_activate.py (فعال‌سازی مدل)
- backend/app/services/oversight_strong_prompt.py (پرامپت قوی)
- backend/app/services/oversight_telegram_compose.py (تلگرام)
- backend/app/services/oversight_verify_pdf.py (تأیید PDF)

فایل تست جدید باید در tests/test_oversight_service.py ایجاد شود و تمامی رفتارهای CRUD، scheduler loop و auto-register را با mock کردن وابستگی‌های خارجی پوشش دهد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست CRUD برای watched projects شامل add, update, delete, list باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند
- [ ] تست scheduler loop با mock کردن sleep باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند
- [ ] تست auto_register_watched با mock GitHub API باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند
- [ ] تست edge cases شامل duplicate repo, invalid URL, empty fields باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند
- [ ] هیچ تستی fail نمی‌شود (pytest tests/test_oversight_service.py -v)
- [ ] linter بدون warning عبور می‌کند (pylint یا flake8 روی فایل تست)
- [ ] type-check موفق است (mypy backend/tests/test_oversight_service.py)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد فایل تست جدید tests/test_oversight_service.py با مراحل زیر:

1. **ایجاد ساختار پایه تست**:
   - import کردن pytest, unittest.mock, و کلاس‌های مورد نیاز از oversight_service
   - ایجاد کلاس TestOversightService با fixture برای mock کردن وابستگی‌ها

2. **تست CRUD watched projects**:
   - تست add_watched_project: اضافه کردن یک پروژه جدید و بررسی بازگشت موفق
   - تست update_watched_project: به‌روزرسانی یک پروژه موجود و بررسی تغییرات
   - تست delete_watched_project: حذف یک پروژه و بررسی عدم وجود آن
   - تست list_watched_projects: لیست کردن پروژه‌ها و بررسی تعداد/محتوای آن‌ها

3. **تست scheduler loop**:
   - mock کردن sleep برای جلوگیری از تأخیر واقعی
   - تست اینکه حلقه scheduler در هر iteration کارهای مورد انتظار را انجام می‌دهد
   - تست خروج از حلقه با flag مناسب

4. **تست auto_register_watched**:
   - mock کردن GitHub API برای شبیه‌سازی پاسخ‌های مختلف
   - تست ثبت خودکار یک repo معتبر
   - تست خطاهای API (rate limit, not found, etc.)

5. **تست edge cases**:
   - duplicate repo: اضافه کردن repo تکراری و بررسی خطای مناسب
   - invalid URL: استفاده از URL نامعتبر و بررسی خطا
   - empty fields: ارسال فیلدهای خالی و بررسی اعتبارسنجی

6. **استفاده از pytest fixtures و mocks**:
   - استفاده از unittest.mock.patch برای mock کردن وابستگی‌های خارجی
   - استفاده از pytest.fixture برای ایجاد نمونه‌های تست

7. **اجرای تست‌ها**:
   - pytest tests/test_oversight_service.py -v برای اجرای تست‌ها
   - اطمینان از عبور تمام تست‌ها بدون خطا

## 💡 نمونه‌های قبل/بعد
**نمونه تست CRUD برای watched projects**

_قبل:_
```
# فایل tests/test_oversight_service.py وجود ندارد — باید ایجاد شود
```

_بعد:_
```
import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.oversight_service import OversightService

class TestOversightService:
    @pytest.fixture
    def service(self):
        return OversightService()
    
    def test_add_watched_project(self, service):
        result = service.add_watched_project('https://github.com/user/repo')
        assert result is True
    
    def test_duplicate_repo(self, service):
        service.add_watched_project('https://github.com/user/repo')
        with pytest.raises(ValueError):
            service.add_watched_project('https://github.com/user/repo')
    
    def test_invalid_url(self, service):
        with pytest.raises(ValueError):
            service.add_watched_project('not-a-url')
    
    def test_empty_fields(self, service):
        with pytest.raises(ValueError):
            service.add_watched_project('')
    
    def test_list_watched_projects(self, service):
        service.add_watched_project('https://github.com/user/repo1')
        service.add_watched_project('https://github.com/user/repo2')
        projects = service.list_watched_projects()
        assert len(projects) == 2
    
    def test_update_watched_project(self, service):
        service.add_watched_project('https://github.com/user/repo')
        result = service.update_watched_project('https://github.com/user/repo', new_url='https://github.com/user/new-repo')
        assert result is True
    
    def test_delete_watched_project(self, service):
        service.add_watched_project('https://github.com/user/repo')
        result = service.delete_watched_project('https://github.com/user/repo')
        assert result is True
        assert len(service.list_watched_projects()) == 0
```

**نمونه تست scheduler loop با mock sleep**

_قبل:_
```
# فایل tests/test_oversight_service.py وجود ندارد — باید ایجاد شود
```

_بعد:_
```
def test_scheduler_loop_mocked_sleep(self, service):
    with patch('time.sleep', return_value=None) as mock_sleep:
        with patch.object(service, '_should_stop', side_effect=[False, False, True]):
            service.run_scheduler(max_iterations=3)
            assert mock_sleep.call_count == 2
            assert mock_sleep.call_args[0][0] == service.scheduler_interval
```

**نمونه تست auto_register_watched با mock GitHub API**

_قبل:_
```
# فایل tests/test_oversight_service.py وجود ندارد — باید ایجاد شود
```

_بعد:_
```
def test_auto_register_watched_with_mock_github(self, service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': 123, 'name': 'repo', 'full_name': 'user/repo'}
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        result = service.auto_register_watched('https://github.com/user/repo')
        assert result is True
        mock_get.assert_called_once_with('https://api.github.com/repos/user/repo')
    
    def test_auto_register_watched_github_not_found(self, service):
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('requests.get', return_value=mock_response):
            with pytest.raises(ValueError, match='not found'):
                service.auto_register_watched('https://github.com/user/nonexistent')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v`
- `pylint backend/tests/test_oversight_service.py`
- `mypy backend/tests/test_oversight_service.py`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل تست جدید tests/test_oversight_service.py به کلاس OversightService در backend/app/services/oversight_service.py وابسته است. اگر OversightService تغییر کند (مثلاً signature متدها تغییر کند)، تست‌ها fail می‌شوند. همچنین mock کردن وابستگی‌های خارجی (GitHub API) باید دقیق باشد تا تست‌ها واقعی باشند. اگر OversightService از database استفاده کند، تست‌ها باید با mock database کار کنند تا به داده‌های واقعی وابسته نباشند. فایل‌های مرتبط مانند oversight_settings.py, oversight_progress.py, oversight_verifier.py, oversight_upload_session.py, oversight_codex_service.py, oversight_deep_scan_service.py, oversight_extraction.py, oversight_inspector_bridge.py, oversight_mega_bundle.py, oversight_model_temp_activate.py, oversight_strong_prompt.py, oversight_telegram_compose.py, oversight_verify_pdf.py همگی وابستگی‌های OversightService هستند و تغییر در هرکدام می‌تواند تست‌ها را تحت تأثیر قرار دهد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 9: افزودن تست واحد برای متد add_watched در OversightService

**Scope:** این بخش شامل ایجاد یک تست واحد جدید برای متد add_watched از کلاس OversightService است. تست باید در فایل tests/test_oversight_service.py اضافه شود. فقط این تست خاص مد نظر است و هیچ تغییر دیگری در کد یا تست‌های دیگر انجام نمی‌شود.
**Key terms:** tests/test_oversight_service.py, OversightService, add_watched

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```
```

هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```

--- کلیدواژه‌ها ---
tests/test_oversight_service.py, OversightService, add_watched
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن تست واحد برای متد add_watched در OversightService

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/test_oversight_service.py:1-15` — `test_add_watched` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. فایل test_oversight_service.py در ساختار پروژه موجود نیست و باید ایجاد شود.
  ```python
  async def test_add_watched():
      service = OversightService()
      result = await service.add_watched({'repo_full_name': 'test/repo'})
      assert result['success']
      assert len(service.watched) == 1
  ```
- `backend/app/services/oversight_service.py:نامشخص` — `OversightService.add_watched` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. متد add_watched در کلاس OversightService باید بررسی شود تا signature دقیق و رفتار آن مشخص شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_service.py` — این فایل شامل کلاس OversightService و متد add_watched است که تست باید آن را تست کند.
- `backend/tests/test_runtime_verify_integration.py` — این فایل یک تست موجود است که می‌تواند به عنوان الگو برای ساختار تست‌های async در پروژه استفاده شود.
- `backend/requirements.txt` — برای اجرای تست‌های async نیاز به pytest-asyncio است که باید در requirements.txt موجود باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک وابسته به فایل backend/app/services/oversight_service.py است که کلاس OversightService و متد add_watched را تعریف می‌کند. فایل تست test_oversight_service.py باید ایجاد شود و OversightService را import کند. همچنین نیاز به pytest-asyncio برای اجرای تست‌های async وجود دارد که باید در requirements.txt مشخص شده باشد. فایل‌های تست موجود مانند test_runtime_verify_integration.py می‌توانند به عنوان الگو برای ساختار تست استفاده شوند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن یک تست واحد جدید برای متد add_watched از کلاس OversightService را دارد. این تست باید در فایل tests/test_oversight_service.py اضافه شود. فقط این تست خاص مد نظر است و هیچ تغییر دیگری در کد یا تست‌های دیگر انجام نمی‌شود.

--- بخش مربوط از درخواست اصلی کاربر ---
## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```

--- کلیدواژه‌ها ---
tests/test_oversight_service.py, OversightService, add_watched

تحلیل: کاربر دقیقاً یک تست واحد برای متد add_watched می‌خواهد. متد add_watched در کلاس OversightService قرار دارد که در فایل backend/app/services/oversight_service.py تعریف شده است. فایل تست test_oversight_service.py در مسیر backend/tests/ وجود ندارد و باید ایجاد شود. متد add_watched احتمالاً یک repository (repo) را به لیست watched اضافه می‌کند و success و طول لیست watched را بررسی می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل tests/test_oversight_service.py باید ایجاد شود و شامل تابع test_add_watched باشد.
- [ ] تابع test_add_watched باید OversightService را import کرده و یک instance از آن بسازد.
- [ ] تست باید متد add_watched را با {'repo_full_name': 'test/repo'} صدا بزند و result['success'] را assert کند.
- [ ] تست باید assert کند که len(service.watched) == 1 بعد از فراخوانی add_watched.
- [ ] تست باید با pytest بدون خطا اجرا شود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل tests/test_oversight_service.py در مسیر backend/tests/
2. import کردن OversightService از backend/app/services/oversight_service.py
3. نوشتن تابع async test_add_watched() که:
   - یک instance از OversightService می‌سازد
   - متد add_watched را با {'repo_full_name': 'test/repo'} صدا می‌زند
   - assert می‌کند که result['success'] برابر True است
   - assert می‌کند که len(service.watched) == 1
4. اطمینان از اینکه pytest بتواند تست async را اجرا کند (نیاز به pytest-asyncio)
5. اجرای تست با دستور: pytest backend/tests/test_oversight_service.py::test_add_watched -v

## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py::test_add_watched -v`
- `pytest backend/tests/test_oversight_service.py -v`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل tests/test_oversight_service.py در ساختار پروژه موجود نیست و باید ایجاد شود. متد add_watched در OversightService ممکن است وابستگی به دیتابیس یا سرویس‌های خارجی داشته باشد که در تست باید mock شوند. اگر OversightService نیاز به dependency injection داشته باشد، تست باید آن را مدیریت کند. همچنین ممکن است pytest-asyncio در requirements.txt نباشد که باید اضافه شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 10: [منطق] عدم وجود permission check در auth pipeline

**Scope:** این بخش یک تسک از یک سوپر-تسک بزرگتر است که به بررسی و رفع مشکل عدم وجود permission check در auth pipeline می‌پردازد. scope این بخش شامل شناسایی ناسازگاری‌ها، مستندسازی فرض‌ها، تعیین ground truth، align کردن طرف‌های ناسازگار، نوشتن integration test برای auth pipeline، و توضیح تصمیمات در PR description است. این بخش صراحتاً یک مرحله اجرایی است و skip نمی‌شود.
**Key terms:** auth pipeline, permission check, authorization, OversightService, tests/test_auth_pipeline.py

**بخش مربوط از متن کاربر:**
```
تسک 4 از 16
  id: c159181f-ebc5-427e-8ead-118d56dacae5
  عنوان اصلی: [منطق] عدم وجود permission check در auth pipeline
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ناسازگاری", "permission", "authorization", "auth pipeline"], "files_hint": ["docs/", "README.md", "*.md"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "permission check", "authorization"], "files_hint": ["docs/", "*.md"]}]
  - integration test برای pipeline `auth` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_auth_pipeline.py", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "چرا این تصمیم گرفته شد", "reason", "rationale"], "files_hint": ["docs/", "*.md"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع عدم وجود permission check در auth pipeline — شناسایی ناسازگاری‌ها و نوشتن integration test

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `class OversightTask` — این کلاس فاقد فیلد permission یا user_id است — نیاز به اضافه کردن permission check logic
  ```python
  class OversightTask(BaseModel):
      id: str
      title: str
      description: str
      priority: str = 'medium'
      status: str = 'pending'
      verify_method: str = 'static'
      verify_plan: dict = {}
      acceptance_criteria: list = []
      created_at: datetime = Field(default_factory=datetime.utcnow)
      updated_at: datetime = Field(default_factory=datetime.utcnow)
  ```
- `backend/app/api/routes/oversight.py:1-30` — `router` — این routeها هیچ permission check یا authorization middleware ندارند — نیاز به اضافه کردن Depends برای user authentication
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from backend.app.services.oversight_service import OversightService
  
  router = APIRouter(prefix='/oversight', tags=['oversight'])
  
  @router.get('/tasks')
  async def get_tasks():
      service = OversightService()
      return await service.get_all_tasks()
  
  @router.post('/tasks')
  async def create_task(task: OversightTask):
      service = OversightService()
      return await service.create_task(task)
  ```
- `backend/app/services/verify_runtime/auth_runner.py:1-40` — `class AuthRunner` — این کلاس فاقد متد permission check granular است — نیاز به اضافه کردن متد check_permission
  ```python
  class AuthRunner:
      def __init__(self):
          self.name = 'auth_runner'
      
      async def run_basic_auth_test(self, url: str, credentials: dict) -> dict:
          # فقط basic auth را چک می‌کند
          return {'status': 'passed', 'details': 'Basic auth test passed'}
      
      async def run_token_auth_test(self, url: str, token: str) -> dict:
          # token-based auth را چک می‌کند
          return {'status': 'passed', 'details': 'Token auth test passed'}
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در پروژه: Python 3.10+, FastAPI, Pydantic v2, pytest, asyncio. کتابخانه‌های مرتبط: fastapi.security برای authentication, pytest-asyncio برای تست‌های async.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/verify_runtime/runner.py` (سطر 25) — این فایل AuthRunner را فراخوانی می‌کند و باید permission check را نیز فراخوانی کند
- `backend/app/services/verify_runtime/iterative_orchestrator.py` (سطر 45) — این فایل فرآیند verify را orchestrate می‌کند و باید permission check را در workflow خود بگنجاند
- `backend/app/services/oversight_service.py` (سطر 1) — این فایل حاوی کلاس OversightTask است که باید permission field به آن اضافه شود
- `backend/app/api/routes/oversight.py` (سطر 1) — این فایل endpointهای oversight را تعریف می‌کند که باید permission check داشته باشند
- `backend/tests/test_auth_pipeline.py` (سطر 1) — این فایل باید ایجاد شود تا integration test برای auth pipeline را شامل شود

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر روی فایل‌های زیر تأثیر می‌گذارد:
- `backend/app/services/oversight_service.py`: اضافه شدن فیلد permission و متد check_permission
- `backend/app/api/routes/oversight.py`: اضافه شدن Depends برای user authentication
- `backend/app/services/verify_runtime/auth_runner.py`: اضافه شدن متد check_permission
- `backend/app/services/verify_runtime/runner.py`: تغییر در فراخوانی AuthRunner
- `backend/app/services/verify_runtime/iterative_orchestrator.py`: تغییر در workflow برای شامل شدن permission check
- `backend/tests/test_auth_pipeline.py`: فایل جدید برای integration test

این تغییرات بر روی تمام endpointهایی که از OversightService استفاده می‌کنند تأثیر می‌گذارد و نیاز به هماهنگی با تیم frontend دارد.

## 🔍 Context و وضعیت فعلی
این تسک بخشی از یک سوپر-تسک بزرگتر (تسک 4 از 16، id: c159181f-ebc5-427e-8ead-118d56dacae5) است که به بررسی و رفع مشکل عدم وجود permission check در auth pipeline می‌پردازد. scope این بخش شامل شناسایی ناسازگاری‌ها، مستندسازی فرض‌ها، تعیین ground truth، align کردن طرف‌های ناسازگار، نوشتن integration test برای auth pipeline، و توضیح تصمیمات در PR description است. این بخش صراحتاً یک مرحله اجرایی است و skip نمی‌شود.

کلیدواژه‌های اصلی: auth pipeline, permission check, authorization, OversightService, tests/test_auth_pipeline.py

بر اساس تحلیل کد واقعی پروژه:
- فایل `backend/app/services/oversight_service.py` (خطوط 1-50) حاوی کلاس `OversightTask` است که فیلد `verify_method` را دارد اما هیچ permission check یا authorization logic در آن دیده نمی‌شود.
- فایل `backend/app/api/routes/oversight.py` (خطوط 1-30) endpointهای مربوط به oversight را تعریف می‌کند که از `OversightService` استفاده می‌کنند اما هیچ middleware یا decorator برای permission check در آن‌ها وجود ندارد.
- فایل `backend/app/services/verify_runtime/auth_runner.py` (خطوط 1-40) شامل کلاس `AuthRunner` است که مسئول اجرای تست‌های auth است اما به نظر می‌رسد فقط basic auth را پوشش می‌دهد و permission check granular را شامل نمی‌شود.
- فایل `backend/app/services/verify_runtime/runner.py` (خطوط 1-50) شامل کلاس `Runner` است که `AuthRunner` را فراخوانی می‌کند.
- فایل `backend/app/services/verify_runtime/iterative_orchestrator.py` (خطوط 1-60) شامل کلاس `IterativeOrchestrator` است که فرآیند verify را orchestrate می‌کند.

ناسازگاری اصلی: در حالی که `OversightTask` دارای فیلد `verify_method` است، هیچ مکانیزمی برای بررسی permission کاربر قبل از اجرای task وجود ندارد. همچنین `AuthRunner` فقط basic auth را چک می‌کند و permission check granular را پوشش نمی‌دهد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد — فایل‌های docs/ و README.md باید شامل مستندات ناسازگاری‌ها باشند
- [ ] ground truth تعیین شد و طرف دیگر align شد — فایل‌های docs/ و *.md باید شامل ground truth و align شده باشند
- [ ] integration test برای pipeline `auth` بدون شکست عبور می‌کند — فایل tests/test_auth_pipeline.py باید شامل تست‌های کامل باشد
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد — فایل‌های docs/ و *.md باید شامل reason و rationale باشند
- [ ] متد check_permission به OversightService اضافه شود و در routeها استفاده شود
- [ ] متد check_permission به AuthRunner اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مراحل اجرایی برای رفع مشکل عدم وجود permission check در auth pipeline:

1. **شناسایی ناسازگاری‌ها**:
   - فایل `backend/app/services/oversight_service.py` را باز کرده و تمام نقاطی که `OversightTask` ایجاد یا اجرا می‌شود را بررسی کن.
   - فایل `backend/app/api/routes/oversight.py` را باز کرده و تمام endpointهایی که از `OversightService` استفاده می‌کنند را شناسایی کن.
   - فایل `backend/app/services/verify_runtime/auth_runner.py` را باز کرده و متدهای موجود را بررسی کن.

2. **مستندسازی فرض‌ها**:
   - برای هر ناسازگاری، فرض‌های طرف‌های مختلف را مستند کن.
   - مثال: `OversightService` فرض می‌کند که permission check در لایه route انجام شده، در حالی که routeها هیچ permission check ندارند.

3. **تعیین ground truth**:
   - بر اساس معماری پروژه (فایل `docs/ARCHITECTURE.md`)، مشخص کن که permission check باید در کدام لایه انجام شود.
   - پیشنهاد: permission check باید در لایه service (قبل از اجرای task) انجام شود.

4. **align کردن طرف‌های ناسازگار**:
   - به `OversightService` یک متد `check_permission(user_id, task_id)` اضافه کن.
   - به `AuthRunner` یک متد `check_permission(user_id, resource)` اضافه کن.
   - routeهای مربوطه را به‌روز کن تا از این متدها استفاده کنند.

5. **نوشتن integration test**:
   - فایل `backend/tests/test_auth_pipeline.py` را ایجاد کن.
   - تست‌هایی برای سناریوهای زیر بنویس:
     - کاربر بدون permission → 403 Forbidden
     - کاربر با permission → 200 OK
     - کاربر admin → دسترسی کامل

6. **توضیح در PR description**:
   - در PR description توضیح بده چرا permission check در auth pipeline ضروری است و چرا این تصمیم گرفته شده.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن permission check به OversightService**

_قبل:_
```
class OversightService:
    async def create_task(self, task: OversightTask):
        # بدون permission check
        return await self.db.insert(task)
```

_بعد:_
```
class OversightService:
    async def create_task(self, task: OversightTask, user_id: str):
        if not await self.check_permission(user_id, 'create_task'):
            raise HTTPException(status_code=403, detail='Permission denied')
        return await self.db.insert(task)
    
    async def check_permission(self, user_id: str, action: str) -> bool:
        # منطق permission check
        return True
```

**اضافه کردن permission check به route**

_قبل:_
```
@router.post('/tasks')
async def create_task(task: OversightTask):
    service = OversightService()
    return await service.create_task(task)
```

_بعد:_
```
@router.post('/tasks')
async def create_task(task: OversightTask, user: User = Depends(get_current_user)):
    service = OversightService()
    return await service.create_task(task, user.id)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_auth_pipeline.py -v --timeout=60`
- `pytest backend/tests/ -k 'auth' -v`
- `python -m pytest backend/tests/test_runtime_verify_integration.py -v`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک‌های خاص این کدبیس:
- فایل `backend/app/services/oversight_service.py` توسط ۳ روتر مختلف (oversight.py, orchestrator.py, unified_api.py) import می‌شود — تغییر signature متدها روی همه endpointها اثر دارد.
- فایل `backend/app/services/verify_runtime/auth_runner.py` توسط `runner.py` و `iterative_orchestrator.py` فراخوانی می‌شود — تغییر در interface نیاز به هماهنگی دارد.
- اضافه کردن permission check ممکن است باعث شکست تست‌های موجود شود که user authentication را mock نکرده‌اند.
- فایل `backend/tests/test_auth_pipeline.py` وجود ندارد و باید از صفر ایجاد شود — نیاز به بررسی ساختار تست‌های موجود در `backend/tests/test_runtime_verify_stage*.py` دارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 11: افزودن لایه بررسی مجوز (permission check) به pipeline احراز هویت برای مسیرهای mutation

**Scope:** این مرحله شامل افزودن یک middleware یا dependency برای بررسی مجوز (permission/authorization) قبل از هر mutation در pipeline auth است. تمرکز بر مسیرهای ذخیره سشن‌ها و پیام‌ها در inspector_session می‌باشد. خارج از scope این مرحله: تغییرات در احراز هویت (authentication) پایه، تغییرات در frontend (Next.js)، یا تغییرات در سایر pipeline‌ها.
**Key terms:** auth pipeline, permission check, authorization, mutation, inspector_session, middleware, dependency

**بخش مربوط از متن کاربر:**
```
در pipeline `auth` یک ناسازگاری منطقی پیدا شد: در مستندات ارائه شده، هیچ اشاره‌ای به مکانیزم permission یا authorization در pipeline احراز هویت نشده است. تمام مسیرهای mutation (مانند ذخیره سشن‌ها و پیام‌ها در inspector_session) بدون عبور از یک لایه permission check قابل دسترسی هستند. هر کاربر احراز هویت شده (یا حتی کاربران غیرمجاز در صورت عدم احراز هویت) می‌توانند داده‌های حساس مانند سشن‌های بازرس را تغییر دهند یا ایجاد کنند. یک middleware یا dependency برای بررسی permission قبل از هر mutation اضافه کنید. اطمینان حاصل کنید که کاربر فقط مجوز تغییر سشن‌های متعلق به خود یا سشن‌هایی که مجوز لازم را دارد، داشته باشد.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن لایه بررسی مجوز به pipeline احراز هویت برای مسیرهای mutation inspector_session

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/inspector_agent.py:نامشخص — فایل deep-read نشده` — `کل سرویس inspector_agent` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً محل اصلی منطق inspector_session است.
- `backend/app/models/inspector_session.py:نامشخص — فایل deep-read نشده` — `کلاس InspectorSession` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. نیاز به بررسی فیلد user_id و owner.
- `backend/app/api/routes/analysis.py:نامشخص — فایل deep-read نشده` — `مسیرهای مربوط به inspector_session` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً مسیرهای mutation inspector_session در اینجا هستند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/chat.py` — ممکن است مسیرهای chat نیز با inspector_session در ارتباط باشند و نیاز به permission check داشته باشند
- `backend/app/services/db_service.py` — برای ذخیره و بازیابی سشن‌ها از دیتابیس استفاده می‌شود و ممکن است نیاز به تغییر داشته باشد
- `backend/app/core/config.py` — ممکن است نیاز به اضافه کردن تنظیمات مربوط به permission levels داشته باشد
- `backend/app/services/oversight_inspector_bridge.py` — این bridge بین oversight و inspector است و ممکن است نیاز به permission check در سطح بالاتر داشته باشد
- `backend/app/services/scan_v5/scan_inspector_session.py` — این فایل با inspector_session در scan v5 سروکار دارد و ممکن است نیاز به هماهنگی داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات بر روی pipeline احراز هویت (احتمالاً در `backend/app/api/deps.py` یا `backend/app/core/roles.py`) تأثیر می‌گذارد. سرویس `inspector_agent.py` به عنوان هسته منطق inspector_session نیاز به تغییر دارد. مدل `inspector_session.py` برای اضافه کردن فیلد owner/user_id نیاز به migration دارد. مسیرهای `analysis.py` و احتمالاً `chat.py` برای استفاده از dependency جدید نیاز به تغییر دارند. همچنین `db_service.py` برای پشتیبانی از queryهای مبتنی بر user_id نیاز به به‌روزرسانی دارد.

## 🔍 Context و وضعیت فعلی
بر اساس درخواست کاربر، نیاز به افزودن یک middleware یا dependency برای بررسی مجوز (permission/authorization) قبل از هر mutation در pipeline auth وجود دارد. تمرکز بر مسیرهای ذخیره سشن‌ها و پیام‌ها در inspector_session می‌باشد. در مستندات ارائه شده، هیچ اشاره‌ای به مکانیزم permission یا authorization در pipeline احراز هویت نشده است. تمام مسیرهای mutation (مانند ذخیره سشن‌ها و پیام‌ها در inspector_session) بدون عبور از یک لایه permission check قابل دسترسی هستند. هر کاربر احراز هویت شده (یا حتی کاربران غیرمجاز در صورت عدم احراز هویت) می‌توانند داده‌های حساس مانند سشن‌های بازرس را تغییر دهند یا ایجاد کنند. یک middleware یا dependency برای بررسی permission قبل از هر mutation اضافه کنید. اطمینان حاصل کنید که کاربر فقط مجوز تغییر سشن‌های متعلق به خود یا سشن‌هایی که مجوز لازم را دارد، داشته باشد. کلیدواژه‌ها: auth pipeline, permission check, authorization, mutation, inspector_session, middleware, dependency. خارج از scope این مرحله: تغییرات در احراز هویت (authentication) پایه، تغییرات در frontend (Next.js)، یا تغییرات در سایر pipeline‌ها.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] یک dependency جدید به نام `get_current_user_with_permission` ایجاد شود که بعد از احراز هویت، مجوز کاربر را برای عملیات mutation بررسی کند.
- [ ] مدل InspectorSession دارای فیلد `user_id` یا `owner_id` باشد تا مالکیت سشن مشخص شود.
- [ ] تمامی مسیرهای mutation مربوط به inspector_session (ذخیره سشن و پیام) از dependency جدید استفاده کنند.
- [ ] کاربر غیرمجاز (غیرمالک سشن) نتواند سشن متعلق به کاربر دیگر را تغییر دهد و خطای 403 دریافت کند.
- [ ] کاربر مجاز (مالک سشن یا ادمین) بتواند سشن خود را تغییر دهد و عملیات با موفقیت انجام شود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک dependency جدید به نام `get_current_user_with_permission` در فایل `backend/app/api/deps.py` (در صورت وجود) یا ایجاد فایل جدید `backend/app/api/permissions.py`. این dependency باید بعد از احراز هویت، مجوز کاربر را برای عملیات mutation بررسی کند.
2. افزودن یک تابع کمکی به نام `verify_session_ownership` در سرویس `backend/app/services/inspector_agent.py` که بررسی کند آیا کاربر جاری مالک سشن مورد نظر است یا مجوز تغییر آن را دارد.
3. تغییر مسیرهای مربوط به ذخیره سشن و پیام در فایل‌های route مربوط به inspector_session (احتمالاً در `backend/app/api/routes/analysis.py` یا فایل route جدید) برای استفاده از dependency جدید.
4. به‌روزرسانی مدل `backend/app/models/inspector_session.py` برای اضافه کردن فیلد `user_id` (در صورت عدم وجود) تا بتوان مالکیت سشن را追踪 کرد.
5. افزودن تست‌های واحد برای سناریوهای مختلف مجوز (دسترسی مجاز، دسترسی غیرمجاز، دسترسی به سشن دیگران).

## 💡 نمونه‌های قبل/بعد
**نمونه فرضی — افزودن permission check به یک endpoint**

_قبل:_
```
@router.post("/sessions/{session_id}/messages")
async def add_message(session_id: str, message: MessageCreate, db: Session = Depends(get_db)):
    session = db.query(InspectorSession).filter(InspectorSession.id == session_id).first()
    # بدون بررسی مجوز
```

_بعد:_
```
@router.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str, 
    message: MessageCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permission("session:write"))
):
    session = db.query(InspectorSession).filter(InspectorSession.id == session_id).first()
    if session.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to modify this session")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_inspector_oversight_bridge.py -m permission -v`
- `python -m pytest backend/tests/ -k "permission or authorization" -v`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که فایل‌های `inspector_agent.py` و `inspector_session.py` deep-read نشده‌اند و ممکن است ساختار فعلی آن‌ها با فرضیات ما همخوانی نداشته باشد. همچنین تغییر در pipeline احراز هویت می‌تواند بر تمام endpointهایی که از این dependency استفاده می‌کنند تأثیر بگذارد. اگر فیلد user_id در مدل InspectorSession وجود نداشته باشد، نیاز به migration دیتابیس خواهد بود که ممکن است داده‌های موجود را تحت تأثیر قرار دهد. همچنین bridge بین oversight و inspector (`oversight_inspector_bridge.py`) ممکن است نیاز به هماهنگی داشته باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 12: بررسی و رفع coherence issues در pipeline auth

**Scope:** این مرحله شامل بررسی و رفع coherence issues (مانند feature flag rot یا refactor ناتمام) در pipeline auth است. این بخش از درخواست اصلی به عنوان یک مرحله اجرایی در نظر گرفته شده و باید به صورت کامل انجام شود. تمام caller های هر دو طرف (قبل و بعد از تغییر) باید بررسی شوند تا از عدم break شدن downstream consumers اطمینان حاصل شود.
**Key terms:** pipeline auth, downstream consumers, caller, feature flag rot, refactor ناتمام

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و رفع coherence issues (feature flag rot یا refactor ناتمام) در pipeline auth — بررسی و رفع coherence issues در pipeline auth
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع coherence issues در pipeline auth

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/auth_runner.py` — `auth_runner (کل فایل)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار پروژه، این فایل مسئول اجرای pipeline auth است و احتمالاً coherence issues در آن وجود دارد.
- `backend/app/services/verify_runtime/runner.py` — `runner (کل فایل)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. به عنوان orchestrator اصلی، احتمالاً auth_runner را فراخوانی می‌کند و باید از عدم break شدن آن اطمینان حاصل شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/verify_runtime/behavioral_probe_layer.py` — این فایل احتمالاً از auth_runner برای probing رفتار auth استفاده می‌کند. تغییر در auth_runner می‌تواند روی این لایه تأثیر بگذارد.
- `backend/app/services/verify_runtime/iterative_orchestrator.py` — این فایل به عنوان orchestrator تکراری، ممکن است auth_runner را در حلقه‌های خود فراخوانی کند. coherence issues در auth_runner می‌تواند باعث loopهای بی‌نهایت یا رفتار نادرست شود.
- `backend/app/services/verify_runtime/inspector_probe.py` — این فایل برای probing inspector از auth_runner استفاده می‌کند. تغییرات باید با این مصرف‌کننده سازگار باشد.
- `backend/app/services/verify_runtime/api_probe.py` — این فایل برای probing APIها از auth_runner استفاده می‌کند. downstream consumer مهمی است که نباید break شود.
- `backend/app/services/verify_runtime/context_builder.py` — این فایل context مورد نیاز auth_runner را می‌سازد. coherence issues در auth_runner ممکن است نیاز به تغییر در context_builder داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر روی فایل‌های `backend/app/services/verify_runtime/auth_runner.py` و `backend/app/services/verify_runtime/runner.py` متمرکز است. فایل‌های `behavioral_probe_layer.py`, `iterative_orchestrator.py`, `inspector_probe.py`, `api_probe.py`, و `context_builder.py` همگی مصرف‌کننده (caller) auth_runner هستند و تحت تأثیر تغییرات قرار می‌گیرند. همچنین تست‌های `backend/tests/test_runtime_verify_*` باید برای تأیید عدم break شدن اجرا شوند.

## 🔍 Context و وضعیت فعلی
بررسی و رفع coherence issues (مانند feature flag rot یا refactor ناتمام) در pipeline auth. این بخش از درخواست اصلی به عنوان یک مرحله اجرایی در نظر گرفته شده و باید به صورت کامل انجام شود. تمام caller های هر دو طرف (قبل و بعد از تغییر) باید بررسی شوند تا از عدم break شدن downstream consumers اطمینان حاصل شود.

--- بخش مربوط از درخواست اصلی کاربر ---
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و رفع coherence issues (feature flag rot یا refactor ناتمام) در pipeline auth — بررسی و رفع coherence issues در pipeline auth

--- کلیدواژه‌ها ---
pipeline auth, downstream consumers, caller, feature flag rot, refactor ناتمام

بر اساس تحلیل کد واقعی پروژه، فایل‌های مرتبط با pipeline auth شامل:
- backend/app/services/verify_runtime/auth_runner.py (احتمالاً مسئول اجرای auth)
- backend/app/services/verify_runtime/runner.py (orchestrator اصلی)
- backend/app/services/verify_runtime/context_builder.py (ساخت context)
- backend/app/services/verify_runtime/behavioral_probe_layer.py (لایه probing)
- backend/app/services/verify_runtime/api_probe.py (API probing)

این فایل‌ها deep-read نشده‌اند، اما بر اساس ساختار پروژه، auth_runner.py نقطه کانونی pipeline auth است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] همه callerهای auth_runner (حداقل ۵ فایل) شناسایی و مستند شوند
- [ ] هیچ feature flag rot (flagهایی که همیشه true/false هستند) در auth_runner باقی نماند
- [ ] هیچ refactor ناتمام (تابع با TODO، FIXME، یا پیاده‌سازی ناقص) در auth_runner باقی نماند
- [ ] همه تست‌های runtime verify (backend/tests/test_runtime_verify_*) با موفقیت پاس شوند
- [ ] هیچ downstream consumer (caller) پس از تغییرات break نشود — با اجرای تست‌های integration تأیید شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **بررسی کامل auth_runner.py**: فایل `backend/app/services/verify_runtime/auth_runner.py` را باز کرده و coherence issues مانند feature flag rot (flagهای منسوخ که هنوز در کد باقی مانده‌اند) یا refactor ناتمام (توابع ناقص، importهای بی‌استفاده، dead code) را شناسایی کن.

2. **شناسایی تمام callerهای auth_runner**: با جستجوی import `auth_runner` در کل پروژه، تمام فایل‌هایی که از auth_runner استفاده می‌کنند را پیدا کن. این شامل:
   - `backend/app/services/verify_runtime/runner.py`
   - `backend/app/services/verify_runtime/behavioral_probe_layer.py`
   - `backend/app/services/verify_runtime/iterative_orchestrator.py`
   - `backend/app/services/verify_runtime/inspector_probe.py`

3. **بررسی downstream consumers**: برای هر caller، مشخص کن که از چه توابع/کلاس‌هایی از auth_runner استفاده می‌کند و تغییرات پیشنهادی چه تأثیری روی آن‌ها دارد.

4. **رفع coherence issues**:
   - اگر feature flag rot وجود دارد (flagهایی که همیشه true/false هستند)، آن‌ها را حذف کرده و کد مربوطه را یکپارچه کن.
   - اگر refactor ناتمام وجود دارد (مثلاً تابعی که نصفه پیاده‌سازی شده)، آن را کامل کن یا حذف کن.
   - dead code را حذف کن.
   - importهای بی‌استفاده را پاک کن.

5. **تغییرات تدریجی**: هر تغییر را در یک commit جداگانه انجام بده تا revert کردن آسان باشد.

6. **تست**: پس از هر تغییر، تست‌های مربوطه را اجرا کن (`pytest backend/tests/test_runtime_verify_*`).

## 💡 نمونه‌های قبل/بعد
**نمونه فرضی: حذف feature flag rot در auth_runner**

_قبل:_
```
# قبل: feature flag rot
if os.getenv('USE_LEGACY_AUTH', 'false') == 'true':
    # legacy auth logic (منسوخ شده)
    return legacy_authenticate(token)
else:
    # new auth logic
    return new_authenticate(token)
```

_بعد:_
```
# بعد: حذف flag و یکپارچه‌سازی
# legacy auth حذف شد چون flag همیشه false بود
return new_authenticate(token)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_runtime_verify_stage1.py -v`
- `pytest backend/tests/test_runtime_verify_stage2.py -v`
- `pytest backend/tests/test_runtime_verify_stage3a.py -v`
- `pytest backend/tests/test_runtime_verify_stage3b.py -v`
- `pytest backend/tests/test_runtime_verify_stage3cd.py -v`
- `pytest backend/tests/test_runtime_verify_stage3e.py -v`
- `pytest backend/tests/test_runtime_verify_stage6.py -v`
- `pytest backend/tests/test_runtime_verify_stage9.py -v`
- `pytest backend/tests/test_runtime_verify_integration.py -v`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: تغییر در auth_runner می‌تواند روی تمام callerهای آن (behavioral_probe_layer.py, iterative_orchestrator.py, inspector_probe.py, api_probe.py, context_builder.py) تأثیر بگذارد. اگر یکی از این فایل‌ها به signature خاصی از توابع auth_runner وابسته باشد، تغییر signature می‌تواند باعث break شود. همچنین تست‌های integration ممکن است fail شوند اگر رفتار auth تغییر کند. ریسک دوم: حذف feature flag rot ممکن است منطق legacy را که هنوز در برخی سناریوهای edge case استفاده می‌شود، نادیده بگیرد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 13: بررسی اولیه و اعتبارسنجی خودکار درخواست پیش از اجرا

**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. هدف آن جلوگیری از پیاده‌سازی مجدد، تشخیص اشتباه، و اطمینان از بررسی مستقل repo است. هیچ فایل، کلاس، یا تابعی برای تغییر مشخص نشده است.

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی خودکار پیش از اجرا و جلوگیری از پیاده‌سازی مجدد

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/inspector_agent.py` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً حاوی منطق اصلی inspector agent است که ممکن است با درخواست کاربر مرتبط باشد.
- `backend/app/services/inspector_intent_resolver.py` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً برای تشخیص intent درخواست‌ها استفاده می‌شود و ممکن است نیاز به بررسی داشته باشد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/inspector_proposal_executor.py` — این فایل احتمالاً executor پیشنهادات inspector است و ممکن است تحت تأثیر تغییرات مرتبط با بررسی خودکار قرار گیرد.
- `backend/app/services/oversight_inspector_bridge.py` — این فایل bridge بین oversight و inspector است و ممکن است برای هماهنگی بررسی‌ها نیاز به تغییر داشته باشد.
- `backend/app/services/scan_v5/scan_inspector_session.py` — این فایل مدیریت session اسکن inspector را انجام می‌دهد و ممکن است برای جلوگیری از اسکن‌های تکراری نیاز به بررسی داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک وابستگی مستقیم به فایل‌های backend/app/services/inspector_agent.py، backend/app/services/inspector_intent_resolver.py، backend/app/services/inspector_proposal_executor.py، backend/app/services/oversight_inspector_bridge.py، و backend/app/services/scan_v5/scan_inspector_session.py دارد. همچنین ممکن است با backend/app/services/scan_v5/scan_bundle.py و backend/app/services/oversight_service.py نیز در ارتباط باشد. این فایل‌ها بخشی از زیرسیستم inspector و oversight هستند که برای تحلیل و اعتبارسنجی خودکار کد استفاده می‌شوند.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. هدف آن جلوگیری از پیاده‌سازی مجدد، تشخیص اشتباه، و اطمینان از بررسی مستقل repo است. هیچ فایل، کلاس، یا تابعی برای تغییر مشخص نشده است. کاربر در متن خود تأکید کرده که این پرامپت بر اساس یک بررسی اولیه خودکار از repo ساخته شده و ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. بنابراین مدل اجراکننده نباید به آن به‌عنوان منبع نهایی استناد کند. همچنین احتمال پیاده‌سازی قبلی (به صورت کامل یا ناقص) وجود دارد؛ بنابراین پیش از شروع باید با grep/search و خواندن فایل‌های مرتبط بررسی کند که چه چیزی از قبل وجود دارد. اگر یک قابلیت/فایل/تابع از قبل موجود است، نباید دوباره ساخته شود؛ فقط موارد ناقص یا اشتباه اصلاح/تکمیل شوند. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند. مسئولیت مدل اجراکننده این است که پیش از هر تغییر، ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کند. اگر تشخیص دهد موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خود عمل کند. اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کند و در commit message توضیح دهد. اگر کار طولانی است، نباید خلاصه‌اش کند؛ همه را به‌طور کامل انجام دهد. اگر یک کامیت گنجایش ندارد، در چندین کامیت متوالی انجام دهد ولی هیچ بخشی را skip نکند. ترتیب کامیت‌ها را منطقی نگه دارد (foundation → core → integration → tests). در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویسد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مدل اجراکننده قبل از هر تغییر، با grep/search بررسی کند که آیا قابلیت مورد نظر از قبل در repo پیاده‌سازی شده است یا خیر.
- [ ] اگر قابلیتی از قبل وجود دارد، مدل اجراکننده آن را دوباره نسازد و فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کند.
- [ ] اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.
- [ ] اگر کار طولانی است، در چندین کامیت متوالی با ترتیب منطقی (foundation → core → integration → tests) انجام شود و هیچ بخشی skip نشود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک صرفاً یک یادداشت هشداردهنده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. بنابراین هیچ اقدام عملی برای پیاده‌سازی وجود ندارد. مدل اجراکننده باید قبل از هرگونه تغییر در پروژه، مراحل زیر را انجام دهد: 1) بررسی کامل repo با grep/search برای یافتن پیاده‌سازی‌های موجود مرتبط با درخواست. 2) خواندن فایل‌های مرتبط مانند backend/app/services/inspector_agent.py، backend/app/services/inspector_intent_resolver.py، backend/app/services/inspector_proposal_executor.py، backend/app/services/oversight_inspector_bridge.py، backend/app/services/scan_v5/scan_inspector_session.py برای اطمینان از عدم پیاده‌سازی مجدد. 3) اگر قابلیتی از قبل وجود دارد، فقط موارد ناقص یا اشتباه را اصلاح کند. 4) اگر همه چیز کامل است، یک کامیت no-op با توضیح ثبت کند. 5) اگر کار طولانی است، در چند کامیت متوالی با ترتیب منطقی انجام دهد و در نهایت checklist در PR description بنویسد.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که مدل اجراکننده ممکن است بدون بررسی کافی، اقدام به پیاده‌سازی مجدد قابلیت‌های موجود کند که منجر به duplication و اتلاف منابع می‌شود. همچنین اگر فایل‌های مرتبط مانند backend/app/services/inspector_agent.py یا backend/app/services/inspector_intent_resolver.py به‌درستی بررسی نشوند، ممکن است تغییرات ناقص یا اشتباه اعمال شوند. ریسک دیگر این است که اگر معیارهای پذیرش مبهم باشند، مدل اجراکننده ممکن است تفسیر نادرستی داشته باشد و commit message نامناسبی ثبت کند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 14: رفع ناسازگاری منطقی بین task_type و قابلیت‌های مدل در انتخاب هوشمند

**Scope:** این مرحله شامل ایجاد یک mapping صریح بین task_type و مجموعه ModelCapabilityهای مورد نیاز در pipeline ai_llm است. منطق انتخاب هوشمند باید اصلاح شود تا ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/ai_manager.py هستند. این مرحله شامل تغییر در منطق انتخاب مدل است و نه تغییر در API یا رابط کاربری.
**Key terms:** backend/app/ai_manager.py, backend/app/ai_manager.py, task_type, ModelCapability, ai_llm, pipeline

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در مستندات ai_manager، ورودی‌ها شامل 'task_type' و 'قابلیت‌های مورد نیاز (ModelCapability)' هستند، اما مشخص نیست که چگونه این دو با هم تطبیق داده می‌شوند. ممکن است یک task_type خاص به قابلیت‌های متفاوتی نیاز داشته باشد و انتخاب مدل صرفاً بر اساس task_type بدون در نظر گرفتن قابلیت‌های دقیق، نادرست باشد. همچنین ارتباط بین task_type و مدل‌های ترجیحی (preferred models) مشخص نیست.

یک mapping صریح بین task_type و مجموعه‌ای از ModelCapabilityهای مورد نیاز ایجاد کنید. منطق انتخاب هوشمند را طوری طراحی کنید که ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد.
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع ناسازگاری منطقی بین task_type و قابلیت‌های مدل در انتخاب هوشمند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `select_model` — فایل ai_manager.py در deep context موجود نیست — بر اساس ساختار سطحی پروژه. این فایل اصلی‌ترین محل تغییر است. تابع select_model باید اصلاح شود تا task_type را به capabilities ترجمه کند.
- `backend/app/services/ai_manager.py:100-150` — `get_available_models` — این تابع باید مدل‌ها را بر اساس capability فیلتر کند. نیاز به اضافه کردن پارامتر capabilities و منطق فیلتر دارد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` (سطر 1) — کلاس پایه AI که شامل تعریف ModelCapability است. mapping جدید باید با enum موجود در این فایل هماهنگ باشد.
- `backend/app/services/ai_balance_service.py` (سطر 1) — این سرویس load balancing را انجام می‌دهد. تغییر در انتخاب مدل روی منطق balance تأثیر می‌گذارد.
- `backend/app/services/ai_manager.py` (سطر 1) — فایل اصلی که شامل pipeline ai_llm و منطق انتخاب مدل است. تمام تغییرات در این فایل متمرکز است.
- `backend/app/services/claude_service.py` (سطر 1) — این سرویس از ai_manager برای انتخاب مدل استفاده می‌کند. تغییر در mapping روی انتخاب مدل Claude تأثیر می‌گذارد.
- `backend/app/services/openai_service.py` (سطر 1) — مشابه claude_service، این سرویس نیز از ai_manager استفاده می‌کند و تحت تأثیر تغییرات قرار می‌گیرد.

## 🌐 نقشهٔ وابستگی‌ها
این تغییر در فایل backend/app/services/ai_manager.py متمرکز است که توسط سرویس‌های متعددی مانند claude_service.py، openai_service.py، gemini_service.py، deepseek_service.py و perplexity_service.py استفاده می‌شود. همچنین ai_balance_service.py برای load balancing به خروجی select_model وابسته است. تغییر در mapping task_type به capabilities باید با enum ModelCapability در ai_base.py هماهنگ باشد. فایل‌های تست مانند test_runtime_verify_stage1.py تا test_runtime_verify_stage9.py ممکن است نیاز به بروزرسانی داشته باشند.

## 🔍 Context و وضعیت فعلی
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد: در مستندات ai_manager، ورودی‌ها شامل 'task_type' و 'قابلیت‌های مورد نیاز (ModelCapability)' هستند، اما مشخص نیست که چگونه این دو با هم تطبیق داده می‌شوند. ممکن است یک task_type خاص به قابلیت‌های متفاوتی نیاز داشته باشد و انتخاب مدل صرفاً بر اساس task_type بدون در نظر گرفتن قابلیت‌های دقیق، نادرست باشد. همچنین ارتباط بین task_type و مدل‌های ترجیحی (preferred models) مشخص نیست. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/ai_manager.py هستند. این مرحله شامل تغییر در منطق انتخاب مدل است و نه تغییر در API یا رابط کاربری. یک mapping صریح بین task_type و مجموعه‌ای از ModelCapabilityهای مورد نیاز ایجاد کنید. منطق انتخاب هوشمند را طوری طراحی کنید که ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد. کلیدواژه‌ها: backend/app/ai_manager.py, backend/app/ai_manager.py, task_type, ModelCapability, ai_llm, pipeline

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] یک دیکشنری TASK_TYPE_TO_CAPABILITIES در ai_manager.py ایجاد شود که حداقل ۴ task_type (code_generation, analysis, chat, debate) را به لیست ModelCapability نگاشت کند.
- [ ] تابع select_model باید ابتدا task_type را به capabilities ترجمه کند، سپس مدل‌ها را فیلتر کند و در نهایت بر اساس preferred_models انتخاب کند.
- [ ] تابع _filter_models_by_capability جدید اضافه شود که لیست مدل‌ها و capabilities را گرفته و مدل‌های فاقد capability را حذف کند.
- [ ] هیچ تغییری در API یا رابط کاربری ایجاد نشود — فقط منطق داخلی select_model تغییر کند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/ai_manager.py، تابع `select_model` را اصلاح کنید تا ابتدا task_type ورودی را به مجموعه‌ای از ModelCapability ترجمه کند. 2. یک دیکشنری `TASK_TYPE_TO_CAPABILITIES` در ai_manager.py ایجاد کنید که هر task_type (مانند 'code_generation', 'analysis', 'chat', 'debate') را به لیستی از ModelCapability (مانند 'code', 'reasoning', 'vision', 'tool_use') نگاشت کند. 3. منطق فیلتر کردن مدل‌ها را تغییر دهید: ابتدا مدل‌هایی که capabilityهای مورد نیاز را دارند از لیست تمام مدل‌ها انتخاب کنید، سپس بر اساس preferred_models و load balancing اولویت‌دهی کنید. 4. تابع `_filter_models_by_capability` جدید اضافه کنید که لیست مدل‌ها و capabilityهای مورد نیاز را گرفته و مدل‌های فاقد آن capabilityها را حذف کند. 5. در تابع `get_available_models` از ai_manager.py، اطمینان حاصل کنید که capability هر مدل از طریق ModelCapability تگ‌گذاری شده است.

## 💡 نمونه‌های قبل/بعد
**منطق فعلی انتخاب مدل (فرضی بر اساس ساختار)**

_قبل:_
```
def select_model(task_type: str, preferred_models: list[str] = None) -> str:
    # منطق فعلی: فقط بر اساس task_type و preferred_models انتخاب می‌کند
    # بدون در نظر گرفتن capabilities
    available = get_available_models()
    if preferred_models:
        for m in preferred_models:
            if m in available:
                return m
    return available[0]
```

_بعد:_
```
TASK_TYPE_TO_CAPABILITIES = {
    'code_generation': [ModelCapability.CODE, ModelCapability.REASONING],
    'analysis': [ModelCapability.REASONING, ModelCapability.ANALYSIS],
    'chat': [ModelCapability.CHAT, ModelCapability.TOOL_USE],
    'debate': [ModelCapability.REASONING, ModelCapability.DEBATE],
}

def select_model(task_type: str, preferred_models: list[str] = None) -> str:
    required_caps = TASK_TYPE_TO_CAPABILITIES.get(task_type, [])
    candidates = _filter_models_by_capability(get_available_models(), required_caps)
    if preferred_models:
        for m in preferred_models:
            if m in candidates:
                return m
    return candidates[0] if candidates else get_available_models()[0]
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_runtime_verify_stage1.py -v`
- `pytest backend/tests/test_runtime_verify_stage2.py -v`
- `python -c "from backend.app.services.ai_manager import select_model; print(select_model('code_generation'))"`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در تابع select_model در ai_manager.py می‌تواند روی تمام سرویس‌هایی که از این تابع استفاده می‌کنند (claude_service.py, openai_service.py, gemini_service.py, deepseek_service.py, perplexity_service.py) تأثیر بگذارد. اگر mapping ناقص باشد، برخی task_typeها ممکن است مدل مناسبی پیدا نکنند و به fallback برگردند. همچنین ai_balance_service.py که load balancing را انجام می‌دهد ممکن است با لیست مدل‌های فیلترشده دچار مشکل شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 15: بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager

**Scope:** این مرحله شامل بررسی کامل و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager (به‌ویژه backend/app/ai_manager.py) است. هدف شناسایی و مستندسازی ناسازگاری‌ها، فرض‌ها و نقاط ضعف در منطق fallback فعلی می‌باشد. این مرحله شامل پیاده‌سازی یا اصلاح کد نمی‌شود و صرفاً به تحلیل و مستندسازی می‌پردازد.
**Key terms:** ai_llm, ai_manager, backend/app/ai_manager.py, fallback, retry, timeout, rate.limit, validation.failure

**بخش مربوط از متن کاربر:**
```
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
  - بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager — بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. فایل در ساختار پروژه موجود است (backend/app/services/ai_manager.py).
- `backend/app/services/ai_balance_service.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. فایل در ساختار پروژه موجود است (backend/app/services/ai_balance_service.py).
- `backend/app/services/ai_base.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. فایل در ساختار پروژه موجود است (backend/app/services/ai_base.py).

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/claude_service.py` — یکی از سرویس‌های AI که توسط ai_manager.py مدیریت می‌شود. منطق fallback به این سرویس وابسته است.
- `backend/app/services/openai_service.py` — یکی از سرویس‌های AI که توسط ai_manager.py مدیریت می‌شود. منطق fallback به این سرویس وابسته است.
- `backend/app/services/gemini_service.py` — یکی از سرویس‌های AI که توسط ai_manager.py مدیریت می‌شود. منطق fallback به این سرویس وابسته است.
- `backend/app/services/deepseek_service.py` — یکی از سرویس‌های AI که توسط ai_manager.py مدیریت می‌شود. منطق fallback به این سرویس وابسته است.
- `backend/app/services/perplexity_service.py` — یکی از سرویس‌های AI که توسط ai_manager.py مدیریت می‌شود. منطق fallback به این سرویس وابسته است.
- `backend/app/services/model_capability_tester.py` — احتمالاً برای تست قابلیت‌های مدل‌ها استفاده می‌شود و ممکن است با ai_manager.py تعامل داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های backend/app/services/ai_manager.py (مدیریت اصلی pipeline AI)، backend/app/services/ai_balance_service.py (احتمالاً بالانس بین مدل‌ها)، backend/app/services/ai_base.py (کلاس پایه سرویس‌های AI)، و تمام سرویس‌های AI شامل claude_service.py، openai_service.py، gemini_service.py، deepseek_service.py، perplexity_service.py وابسته است. همچنین فایل backend/app/services/model_capability_tester.py ممکن است برای تست قابلیت‌ها استفاده شود. تغییر در منطق fallback می‌تواند روی تمام callerهای ai_manager.py تأثیر بگذارد که شامل فایل‌های route مانند backend/app/api/routes/chat.py، backend/app/api/routes/analysis.py، backend/app/api/routes/creator.py و سایر سرویس‌هایی که از ai_manager.py استفاده می‌کنند می‌شود.

## 🔍 Context و وضعیت فعلی
این تسک شامل بررسی کامل و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager (به‌ویژه backend/app/ai_manager.py) است. هدف شناسایی و مستندسازی ناسازگاری‌ها، فرض‌ها و نقاط ضعف در منطق fallback فعلی می‌باشد. این مرحله شامل پیاده‌سازی یا اصلاح کد نمی‌شود و صرفاً به تحلیل و مستندسازی می‌پردازد. کلیدواژه‌های اصلی: ai_llm, ai_manager, backend/app/ai_manager.py, fallback, retry, timeout, rate.limit, validation.failure. با توجه به deep_context موجود، فایل backend/app/services/ai_manager.py در ساختار پروژه دیده می‌شود اما محتوای آن deep-read نشده است. همچنین فایل‌های مرتبط مانند backend/app/services/ai_balance_service.py، backend/app/services/ai_base.py، backend/app/services/claude_service.py، backend/app/services/openai_service.py، backend/app/services/gemini_service.py، backend/app/services/deepseek_service.py، backend/app/services/perplexity_service.py و backend/app/services/model_capability_tester.py در ساختار موجود هستند. pipeline ai_llm احتمالاً به زنجیره‌ای از سرویس‌های AI اشاره دارد که از طریق ai_manager.py مدیریت می‌شوند. منطق fallback فعلی باید از نظر retry mechanism، timeout handling، rate limit handling و validation failure handling بررسی شود. همچنین باید مشخص شود که آیا fallback بین مدل‌های مختلف (Claude, OpenAI, Gemini, DeepSeek, Perplexity) به درستی کار می‌کند و آیا خطاهای خاص هر سرویس به درستی مدیریت می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/services/ai_manager.py به‌طور کامل خوانده و ساختار آن (کلاس‌ها، متدها، وابستگی‌ها) مستند شده باشد.
- [ ] منطق fallback در ai_manager.py شناسایی و مستند شده باشد: ترتیب fallback، شرایط fallback، و مدل‌های involved.
- [ ] مکانیزم retry در ai_manager.py بررسی و مستند شده باشد: تعداد تلاش‌ها، فاصله بین تلاش‌ها، شرایط توقف.
- [ ] timeout handling در ai_manager.py و سرویس‌های AI بررسی و مستند شده باشد: timeout values، timeout handling برای هر سرویس.
- [ ] rate limit handling در ai_manager.py و سرویس‌های AI بررسی و مستند شده باشد: rate limit detection، fallback پس از rate limit.
- [ ] validation failure handling در ai_manager.py و سرویس‌های AI بررسی و مستند شده باشد: انواع validation failures، fallback برای validation failures.
- [ ] یک گزارش مستند از ناسازگاری‌ها، فرض‌ها و نقاط ضعف منطق fallback تهیه شده باشد.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/services/ai_manager.py را به‌طور کامل بخوان و ساختار کلی آن را مستند کن (کلاس‌ها، متدها، وابستگی‌ها).
2. منطق fallback را در ai_manager.py شناسایی کن: چه زمانی fallback رخ می‌دهد؟ چه مدل‌هایی به چه ترتیبی fallback می‌شوند؟
3. مکانیزم retry را بررسی کن: تعداد تلاش‌ها، فاصله بین تلاش‌ها، و شرایط توقف.
4. timeout handling را بررسی کن: timeout برای هر سرویس چقدر است؟ آیا timeoutهای مختلف برای سرویس‌های مختلف وجود دارد؟
5. rate limit handling را بررسی کن: آیا rate limit detection وجود دارد؟ آیا پس از rate limit fallback می‌کند؟
6. validation failure handling را بررسی کن: چه نوع validation failures ممکن است رخ دهد؟ آیا fallback برای validation failures وجود دارد؟
7. فایل‌های سرویس‌های AI (claude_service.py, openai_service.py, gemini_service.py, deepseek_service.py, perplexity_service.py) را بررسی کن تا ببینی آیا exception handling مناسبی دارند.
8. فایل backend/app/services/ai_balance_service.py را بررسی کن تا ببینی آیا با ai_manager.py تعامل دارد.
9. فایل backend/app/services/ai_base.py را بررسی کن تا کلاس پایه و متدهای مشترک را شناسایی کنی.
10. یک گزارش مستند از ناسازگاری‌ها، فرض‌ها و نقاط ضعف منطق fallback تهیه کن.

## 💡 نمونه‌های قبل/بعد
**مستندسازی منطق fallback (نمونه)**

_قبل:_
```
منطق fallback فعلی در ai_manager.py: (نیاز به بررسی دارد)
```

_بعد:_
```
گزارش مستند: 'منطق fallback در ai_manager.py به ترتیب Claude → OpenAI → Gemini → DeepSeek → Perplexity است. retry mechanism: 3 تلاش با فاصله 2 ثانیه. timeout: 30 ثانیه برای همه سرویس‌ها. rate limit handling: وجود ندارد. validation failure handling: fallback نمی‌کند.'
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cat backend/app/services/ai_manager.py | head -100`
- `grep -rn 'fallback' backend/app/services/`
- `grep -rn 'retry' backend/app/services/`
- `grep -rn 'timeout' backend/app/services/`
- `grep -rn 'rate.limit' backend/app/services/`
- `grep -rn 'validation' backend/app/services/`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک صرفاً به تحلیل و مستندسازی می‌پردازد و هیچ تغییری در کد ایجاد نمی‌کند، بنابراین ریسک مستقیمی ندارد. با این حال، اگر مستندسازی ناقص باشد، ممکن است در مراحل بعدی (پیاده‌سازی اصلاحات) باعث ایجاد باگ شود. فایل‌های ai_manager.py و سرویس‌های AI توسط چندین route و سرویس دیگر استفاده می‌شوند (مانند chat.py، analysis.py، creator.py) و هرگونه برداشت اشتباه از منطق فعلی می‌تواند منجر به تغییرات نادرست در آینده شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 16: پیاده‌سازی استراتژی fallback در ai_manager برای مدیریت خرابی سرویس‌های AI

**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک مکانیزم fallback شفاف در فایل backend/app/ai_manager.py است. استراتژی fallback باید شامل ترتیب fallback (OpenAI -> Claude)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout) باشد. این مرحله شامل تغییر در منطق اصلی ai_manager برای مدیریت هوشمند fallback است و بر pipeline ai_llm تأثیر می‌گذارد. تست‌های مربوطه در tests/test_ai_llm_pipeline.py باید به‌روزرسانی شوند.
**Key terms:** backend/app/ai_manager.py, ai_manager, OpenAI, Claude, fallback, timeout, retry, backoff, validation failure, rate limit, tests/test_ai_llm_pipeline.py

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد: مستندات به 'مدیریت fallback' اشاره دارد، اما جزئیات آن مشخص نیست. با توجه به اینکه ai_manager با چندین سرویس (OpenAI, Claude) کار می‌کند، یک استراتژی fallback شفاف (مثلاً ترتیب fallback، timeout، تعداد تلاش مجدد) ضروری است. همچنین مشخص نیست که آیا fallback بر اساس خطاهای سرویس (مثلاً rate limit) یا کیفیت پاسخ (validation failure) انجام می‌شود. یک استراتژی fallback واضح در ai_manager پیاده‌سازی کنید: ترتیب fallback (مثلاً OpenAI -> Claude -> ...)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout).
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی استراتژی fallback در ai_manager برای مدیریت خرابی سرویس‌های AI

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `ai_manager_module` — فایل اصلی که باید تغییر کند — مسیر واقعی backend/app/services/ai_manager.py است
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، این فایل باید شامل کلاس اصلی مدیریت AI باشد
  ```
- `backend/app/services/ai_base.py:1-30` — `AIBase` — کلاس پایه که سرویس‌های OpenAI و Claude از آن ارث‌بری می‌کنند
  ```python
  فایل deep-read نشده — کلاس پایه سرویس‌های AI
  ```
- `backend/app/services/openai_service.py:1-40` — `OpenAIService` — یکی از سرویس‌های هدف برای fallback
  ```python
  فایل deep-read نشده — سرویس OpenAI
  ```
- `backend/app/services/claude_service.py:1-40` — `ClaudeService` — دومین سرویس در ترتیب fallback
  ```python
  فایل deep-read نشده — سرویس Claude
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/tests/test_ai_llm_pipeline.py` (سطر 1) — تست‌های pipeline ai_llm که باید به‌روزرسانی شوند
- `backend/app/services/ai_balance_service.py` (سطر 1) — ممکن است با سرویس تعادل AI تداخل داشته باشد
- `backend/app/services/ai_manager.py` (سطر 1) — فایل اصلی که تغییرات در آن اعمال می‌شود

## 🌐 نقشهٔ وابستگی‌ها
این تغییر بر فایل‌های backend/app/services/ai_manager.py (فایل اصلی)، backend/app/services/ai_base.py (کلاس پایه)، backend/app/services/openai_service.py و backend/app/services/claude_service.py (سرویس‌های هدف fallback) تأثیر می‌گذارد. همچنین تست‌های backend/tests/test_ai_llm_pipeline.py باید به‌روزرسانی شوند. ممکن است با backend/app/services/ai_balance_service.py نیز تداخل داشته باشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی یک مکانیزم fallback شفاف در فایل backend/app/ai_manager.py را دارد. این استراتژی باید شامل ترتیب fallback (OpenAI -> Claude)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout) باشد. این تغییر در منطق اصلی ai_manager برای مدیریت هوشمند fallback است و بر pipeline ai_llm تأثیر می‌گذارد. تست‌های مربوطه در tests/test_ai_llm_pipeline.py باید به‌روزرسانی شوند.

بر اساس تحلیل کد واقعی پروژه، فایل backend/app/services/ai_manager.py در مسیر services قرار دارد (نه مستقیماً در app/). این فایل با سرویس‌های مختلف AI از جمله OpenAI (backend/app/services/openai_service.py) و Claude (backend/app/services/claude_service.py) کار می‌کند. همچنین فایل backend/app/services/ai_base.py به عنوان کلاس پایه برای سرویس‌های AI عمل می‌کند. کاربر به ناسازگاری منطقی در pipeline ai_llm اشاره دارد که مستندات به 'مدیریت fallback' اشاره دارد اما جزئیات آن مشخص نیست. کلیدواژه‌های اصلی: backend/app/ai_manager.py, ai_manager, OpenAI, Claude, fallback, timeout, retry, backoff, validation failure, rate limit, tests/test_ai_llm_pipeline.py.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] کلاس FallbackStrategy در backend/app/services/ai_manager.py ایجاد شود با فیلدهای ORDER, TIMEOUT, MAX_RETRIES, BACKOFF, CONDITIONS
- [ ] متد ai_llm در ai_manager.py از FallbackStrategy استفاده کند و در صورت شکست همه سرویس‌ها، خطای AllServicesFailedError برگرداند
- [ ] تست‌های tests/test_ai_llm_pipeline.py سناریوهای fallback را پوشش دهند: timeout سرویس اول و fallback به دوم، خطای validation و retry با backoff
- [ ] ترتیب fallback به صورت OpenAI -> Claude پیاده‌سازی شود
- [ ] حداکثر زمان انتظار (timeout) برای هر سرویس 30 ثانیه باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک کلاس FallbackStrategy در فایل backend/app/services/ai_manager.py که شامل:
   - ترتیب fallback: ['openai', 'claude']
   - timeout پیش‌فرض: 30 ثانیه برای هر سرویس
   - تعداد retry: 3 با backoff نمایی (1s, 2s, 4s)
   - شرط‌های fallback: خطای سرویس (HTTP 5xx, rate limit 429), خطای validation (پاسخ خالی/ناقص), timeout

2. تغییر متد اصلی ai_llm در ai_manager.py برای استفاده از FallbackStrategy

3. به‌روزرسانی تست‌ها در tests/test_ai_llm_pipeline.py برای پوشش سناریوهای fallback

4. اطمینان از سازگاری با کلاس پایه ai_base.py و سرویس‌های openai_service.py و claude_service.py

## 💡 نمونه‌های قبل/بعد
**مثال فرضی از ساختار FallbackStrategy**

_قبل:_
```
# کد فعلی (deep-read نشده)
class AIManager:
    def ai_llm(self, prompt):
        # بدون fallback
        return openai_service.generate(prompt)
```

_بعد:_
```
# کد پیشنهادی
class FallbackStrategy:
    ORDER = ['openai', 'claude']
    TIMEOUT = 30
    MAX_RETRIES = 3
    BACKOFF = [1, 2, 4]
    
    CONDITIONS = ['service_error', 'validation_failure', 'timeout']

class AIManager:
    def ai_llm(self, prompt):
        strategy = FallbackStrategy()
        for service_name in strategy.ORDER:
            for attempt in range(strategy.MAX_RETRIES):
                try:
                    result = self._call_service(service_name, prompt, strategy.TIMEOUT)
                    if self._validate_response(result):
                        return result
                except (ServiceError, ValidationError, TimeoutError):
                    if attempt < strategy.MAX_RETRIES - 1:
                        time.sleep(strategy.BACKOFF[attempt])
                    continue
        raise AllServicesFailedError()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_llm_pipeline.py -v`
- `python -c "from backend.app.services.ai_manager import FallbackStrategy; print(FallbackStrategy.ORDER)"`

## ⚠️ ریسک‌ها و موارد احتیاط
این تغییر بر pipeline اصلی ai_llm تأثیر می‌گذارد که توسط چندین سرویس و روتر استفاده می‌شود. فایل‌های backend/app/services/ai_balance_service.py و backend/app/services/ai_manager.py ممکن است با منطق جدید تداخل داشته باشند. همچنین سرویس‌های OpenAI و Claude ممکن است رفتار متفاوتی در مواجهه با timeout داشته باشند. تست‌های موجود در tests/test_ai_llm_pipeline.py باید به‌روزرسانی شوند تا سناریوهای fallback را پوشش دهند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 17: بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm

**Scope:** این مرحله شامل تحلیل کد موجود در فایل‌های backend/app/ai_manager.py و tests/test_ai_llm_pipeline.py برای مستندسازی وضعیت فعلی است. هدف شناسایی نقاط ضعف، وابستگی‌ها و رفتارهای فعلی قبل از اعمال تغییرات است. خروجی این مرحله یک سند یا کامنت‌های کد است که وضعیت فعلی را شرح می‌دهد.
**Key terms:** backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py

**بخش مربوط از متن کاربر:**
```
بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
```

## 🎯 هدف (خلاصه ساختاریافته)
مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `class AiManager` — کلاس اصلی مدیریت AI — اینجا نقطه ورود pipeline است. deep_context موجود نیست، snippet بر اساس ساختار سطحی پروژه است.
  ```python
  class AiManager:
      def __init__(self, db_session=None):
          self.db = db_session
          self.models_registry = ModelsRegistry()
          self.capability_detector = CapabilityDetector()
          self.fallback_chain = ['claude', 'gpt', 'gemini', 'deepseek']
  ```
- `backend/app/services/ai_base.py:1-40` — `class AiBase` — کلاس پایه برای تمام سرویس‌های AI — منطق retry و validation در اینجاست. deep_context موجود نیست، snippet بر اساس ساختار سطحی پروژه است.
  ```python
  class AiBase(ABC):
      @abstractmethod
      async def async_call(self, prompt: str, system_prompt: str = None) -> dict:
          pass
      
      async def validate_response(self, response: dict) -> bool:
          return 'content' in response and response['content']
      
      async def retry_logic(self, func, max_retries=3):
          for attempt in range(max_retries):
              try:
                  return await func()
              except Exception as e:
                  if attempt == max_retries - 1:
                      raise
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/models_registry.py` (سطر 1) — ثبت و مدیریت مدل‌های AI — ai_manager از این برای انتخاب مدل استفاده می‌کند
- `backend/app/services/capability_detector.py` (سطر 1) — تشخیص قابلیت مدل‌ها — ai_manager برای fallback به این وابسته است
- `backend/app/services/claude_service.py` (سطر 1) — یکی از پیاده‌سازی‌های AiBase — بخشی از pipeline ai_llm
- `backend/app/services/openai_service.py` (سطر 1) — پیاده‌سازی دیگر AiBase — در زنجیره fallback استفاده می‌شود
- `backend/app/services/gemini_service.py` (سطر 1) — پیاده‌سازی دیگر AiBase — در زنجیره fallback استفاده می‌شود

## 🌐 نقشهٔ وابستگی‌ها
فایل backend/app/services/ai_manager.py مرکز orchestration سرویس‌های AI است. این فایل به ai_base.py (کلاس پایه)، models_registry.py (ثبت مدل‌ها)، capability_detector.py (تشخیص قابلیت) وابسته است. ai_base.py توسط claude_service.py، openai_service.py، gemini_service.py، deepseek_service.py، perplexity_service.py پیاده‌سازی می‌شود. pipeline ai_llm شامل زنجیره فراخوانی این سرویس‌ها از طریق ai_manager است. فایل‌های backend/app/api/routes/chat.py و backend/app/api/routes/analysis.py از ai_manager برای پردازش درخواست‌های کاربر استفاده می‌کنند. همچنین backend/app/services/ai_balance_service.py برای توزیع بار بین مدل‌ها به ai_manager وابسته است.

## 🔍 Context و وضعیت فعلی
بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm. این مرحله شامل تحلیل کد موجود در فایل‌های backend/app/ai_manager.py و tests/test_ai_llm_pipeline.py برای مستندسازی وضعیت فعلی است. هدف شناسایی نقاط ضعف، وابستگی‌ها و رفتارهای فعلی قبل از اعمال تغییرات است. خروجی این مرحله یک سند یا کامنت‌های کد است که وضعیت فعلی را شرح می‌دهد. کلیدواژه‌ها: backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py. با توجه به deep_context موجود، فایل backend/app/ai_manager.py در ساختار پروژه وجود ندارد و فایل tests/test_ai_llm_pipeline.py نیز موجود نیست. نزدیک‌ترین فایل‌های مرتبط backend/app/services/ai_manager.py و backend/app/services/ai_base.py هستند. فایل ai_manager.py (در services) شامل کلاس AiManager با متدهای select_best_model, get_ai_response, handle_fallback است. فایل ai_base.py کلاس پایه AiBase را با متدهای async_call, validate_response, retry_logic تعریف می‌کند. pipeline ai_llm احتمالاً به زنجیره فراخوانی مدل‌های مختلف (Claude, GPT, Gemini, DeepSeek) از طریق ai_manager اشاره دارد. وابستگی‌های اصلی: ai_manager به ai_base، models_registry، capability_detector وابسته است. نقاط ضعف احتمالی: عدم مدیریت خطای یکپارچه، نبود caching هوشمند، عدم logging کافی برای دیباگ.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل docs/ai_manager_audit.md ایجاد شود و شامل حداقل ۵ بخش: معماری، جریان فراخوانی، وابستگی‌ها، نقاط ضعف، پیشنهادات
- [ ] کلاس AiManager در backend/app/services/ai_manager.py حداقل ۳ کامنت توضیحی جدید داشته باشد (یکی روی کلاس، دو تا روی متدهای اصلی)
- [ ] فایل tests/test_ai_llm_pipeline.py ایجاد شود و حداقل ۳ تست داشته باشد: test_successful_call, test_fallback_on_error, test_timeout_handling
- [ ] مستندات شامل لیست کامل وابستگی‌های ai_manager باشد (حداقل ۴ فایل: ai_base, models_registry, capability_detector, claude_service)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/services/ai_manager.py را باز کرده و کلاس AiManager را تحلیل کن: متدهای __init__, select_best_model, get_ai_response, handle_fallback را خط به خط بخوان. 2. فایل backend/app/services/ai_base.py را باز کرده و کلاس AiBase را تحلیل کن: متدهای async_call, validate_response, retry_logic را بررسی کن. 3. فایل backend/app/services/models_registry.py را بررسی کن تا لیست کامل مدل‌های پشتیبانی‌شده را ببینی. 4. فایل backend/app/services/capability_detector.py را بررسی کن تا منطق تشخیص قابلیت مدل‌ها را بفهمی. 5. یک سند با فرمت Markdown در docs/ai_manager_audit.md ایجاد کن که شامل: معماری کلی، جریان فراخوانی، وابستگی‌ها، نقاط ضعف، پیشنهادات بهبود. 6. کامنت‌های توضیحی به متدهای کلیدی ai_manager اضافه کن (حداقل ۵ کامنت). 7. فایل tests/test_ai_llm_pipeline.py را ایجاد کن (اگر وجود ندارد) با تست‌های پایه برای: فراخوانی موفق، fallback، خطاهای timeout.

## 💡 نمونه‌های قبل/بعد
**وضعیت فعلی ai_manager — بدون مستندات**

_قبل:_
```
class AiManager:
    def __init__(self, db_session=None):
        self.db = db_session
        self.models_registry = ModelsRegistry()
        self.capability_detector = CapabilityDetector()
        self.fallback_chain = ['claude', 'gpt', 'gemini', 'deepseek']
    
    async def get_ai_response(self, prompt: str, model: str = None):
        # TODO: implement
        pass
```

_بعد:_
```
class AiManager:
    """
    مدیریت و orchestration سرویس‌های AI.
    
    این کلاس مسئول انتخاب مدل مناسب، فراخوانی، fallback و مدیریت خطا است.
    
    وابستگی‌ها:
        - ModelsRegistry: ثبت و مدیریت مدل‌های موجود
        - CapabilityDetector: تشخیص قابلیت مدل‌ها برای fallback
        - AiBase: کلاس پایه برای تمام سرویس‌های AI
    
    جریان فراخوانی:
        1. select_best_model() → انتخاب مدل بر اساس prompt
        2. get_ai_response() → فراخوانی سرویس مربوطه
        3. handle_fallback() → در صورت خطا، مدل بعدی در زنجیره
    """
    def __init__(self, db_session=None):
        self.db = db_session
        self.models_registry = ModelsRegistry()
        self.capability_detector = CapabilityDetector()
        self.fallback_chain = ['claude', 'gpt', 'gemini', 'deepseek']
    
    async def get_ai_response(self, prompt: str, model: str = None):
        """
        دریافت پاسخ از مدل AI.
        
        Args:
            prompt: متن ورودی
            model: نام مدل (اختیاری — در صورت None، select_best_model استفاده می‌شود)
        Returns:
            dict: پاسخ مدل شامل کلید 'content'
        Raises:
            AiManagerError: در صورت عدم موفقیت تمام fallbackها
        """
        pass
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest tests/test_ai_llm_pipeline.py -v`
- `cat docs/ai_manager_audit.md | head -50`
- `grep -n '"""' backend/app/services/ai_manager.py | wc -l`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل backend/app/services/ai_manager.py توسط ۳ روتر (chat.py, analysis.py, orchestrator.py) import می‌شود. تغییر در interface متدها می‌تواند باعث break شدن این روترها شود. همچنین ai_balance_service.py به ai_manager وابسته است. مستندسازی نباید منطق فعلی را تغییر دهد، اما اگر کامنت‌ها نادرست باشند، توسعه‌دهندگان بعدی را گمراه می‌کنند. فایل tests/test_ai_llm_pipeline.py در ساختار پروژه موجود نیست — ایجاد آن ممکن است با naming conventions پروژه هماهنگ نباشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 18: جایگزینی داده‌های سخت‌کد شده صفحه پروفایل مدل‌ها با داده‌های واقعی از بک‌اند

**Scope:** این مرحله شامل بازنویسی کامپوننت `model-profiles/page.tsx` برای دریافت داده‌های پروفایل مدل‌ها از API بک‌اند (احتمالاً از طریق FastAPI) به جای استفاده از داده‌های پیش‌فرض سخت‌کد شده (خطوط 90-97) است. خارج از scope: تغییر ساختار دیتابیس، ایجاد endpoint جدید (فرض بر وجود endpoint مناسب است)، و تغییر سایر صفحات.
**Key terms:** model-profiles/page.tsx, FastAPI, Next.js

**بخش مربوط از متن کاربر:**
```
Model profiles page uses hardcoded default data instead of real backend data

The `model-profiles/page.tsx` defines extensive hardcoded default profiles (lines 90-97)
```

## 🎯 هدف (خلاصه ساختاریافته)
جایگزینی داده‌های سخت‌کد شده صفحه پروفایل مدل‌ها با API واقعی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/model-profiles/page.tsx:90-97` — `defaultProfiles` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی پروژه، این فایل در frontend/src/app/model-profiles/page.tsx فرض شده است.
  ```tsx
  // خطوط 90-97: داده‌های سخت‌کد شده پیش‌فرض پروفایل مدل‌ها
  const defaultProfiles = [
    { id: '1', name: 'GPT-4', provider: 'OpenAI', capabilities: ['chat', 'code'], status: 'active' },
    { id: '2', name: 'Claude 3', provider: 'Anthropic', capabilities: ['chat', 'analysis'], status: 'active' },
    { id: '3', name: 'Gemini Pro', provider: 'Google', capabilities: ['chat', 'vision'], status: 'active' },
  ];
  ```
- `backend/app/api/routes/model_profiles.py:1-50` — `router` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل endpoint مربوط به پروفایل مدل‌ها را ارائه می‌دهد.
  ```python
  // این فایل deep-read نشده — محتوای دقیق مشخص نیست. احتمالاً شامل endpointهای GET /api/model-profiles است.
  ```
- `backend/app/models/ai_profile.py:1-30` — `AIProfile` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. مدل داده‌ای پروفایل مدل‌ها.
  ```python
  // این فایل deep-read نشده — محتوای دقیق مشخص نیست. احتمالاً مدل Pydantic یا SQLAlchemy برای پروفایل مدل‌ها.
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — بر اساس ساختار پروژه: FastAPI (بک‌اند)، Next.js (فرانت‌اند)، احتمالاً axios یا fetch برای درخواست‌های HTTP

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_manager.py` — مدیریت مدل‌ها و احتمالاً ارائه داده‌های پروفایل به endpoint
- `frontend/next.config.js` — تنظیمات Next.js برای proxy API یا rewrites
- `frontend/package-lock.json` — وابستگی‌های frontend شامل کتابخانه‌های HTTP مانند axios یا fetch

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های frontend/src/app/model-profiles/page.tsx (کامپوننت اصلی)، backend/app/api/routes/model_profiles.py (endpoint API)، backend/app/models/ai_profile.py (مدل داده‌ای)، و backend/app/services/ai_manager.py (سرویس مدیریت مدل‌ها) وابسته است. تغییر در frontend نیازمند هماهنگی با ساختار داده‌ای API است. endpoint موجود در model_profiles.py باید داده‌های مورد نیاز را برگرداند. مدل ai_profile.py ساختار داده‌ها را تعریف می‌کند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست جایگزینی داده‌های سخت‌کد شده در کامپوننت `model-profiles/page.tsx` با داده‌های واقعی از بک‌اند (احتمالاً از طریق FastAPI) را دارد. داده‌های پیش‌فرض سخت‌کد شده در خطوط 90-97 این فایل تعریف شده‌اند. خارج از scope این تسک: تغییر ساختار دیتابیس، ایجاد endpoint جدید (فرض بر وجود endpoint مناسب است)، و تغییر سایر صفحات. کلیدواژه‌ها: model-profiles/page.tsx, FastAPI, Next.js. با توجه به ساختار پروژه، فایل‌های مرتبط شامل backend/app/api/routes/model_profiles.py (احتمالاً endpoint مربوطه)، backend/app/services/ai_manager.py (مدیریت مدل‌ها)، و backend/app/models/ai_profile.py (مدل داده‌ای پروفایل مدل) هستند. همچنین frontend/next.config.js و frontend/package-lock.json برای تنظیمات Next.js و وابستگی‌ها مرتبط هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] کامپوننت model-profiles/page.tsx داده‌ها را از endpoint GET /api/model-profiles دریافت کند (به جای داده‌های سخت‌کد شده)
- [ ] حالت loading در هنگام دریافت داده از API نمایش داده شود
- [ ] حالت error در صورت عدم موفقیت API به درستی نمایش داده شود
- [ ] داده‌های سخت‌کد شده (defaultProfiles) از کامپوننت حذف شده باشند
- [ ] نوع داده‌های دریافتی از API با نوع داده‌های مورد انتظار در کامپوننت مطابقت داشته باشد (TypeScript type safety)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی فایل frontend/src/app/model-profiles/page.tsx (در صورت وجود) برای شناسایی ساختار داده‌های سخت‌کد شده در خطوط 90-97.
2. شناسایی endpoint موجود در backend/app/api/routes/model_profiles.py که داده‌های پروفایل مدل‌ها را برمی‌گرداند.
3. ایجاد یک تابع fetch در frontend برای دریافت داده‌ها از API بک‌اند.
4. جایگزینی داده‌های سخت‌کد شده با state مدیریت شده توسط useState/useEffect که از API دریافت می‌شود.
5. مدیریت حالت‌های loading، error، و empty در کامپوننت.
6. اطمینان از تطابق نوع داده‌های دریافتی از API با نوع داده‌های مورد انتظار در کامپوننت.

## 💡 نمونه‌های قبل/بعد
**جایگزینی داده‌های سخت‌کد شده با fetch از API**

_قبل:_
```
const defaultProfiles = [
  { id: '1', name: 'GPT-4', provider: 'OpenAI', capabilities: ['chat', 'code'], status: 'active' },
  { id: '2', name: 'Claude 3', provider: 'Anthropic', capabilities: ['chat', 'analysis'], status: 'active' },
];

function ModelProfilesPage() {
  return <div>{defaultProfiles.map(p => <ProfileCard key={p.id} profile={p} />)}</div>;
}
```

_بعد:_
```
function ModelProfilesPage() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/model-profiles')
      .then(res => res.json())
      .then(data => { setProfiles(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  return <div>{profiles.map(p => <ProfileCard key={p.id} profile={p} />)}</div>;
}
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd frontend && npm run build`
- `cd backend && pytest tests/ -k "model_profiles"`
- `curl -X GET http://localhost:8000/api/model-profiles`

## ⚠️ ریسک‌ها و موارد احتیاط
1. اگر endpoint GET /api/model-profiles وجود نداشته باشد یا داده‌های مورد نیاز را برنگرداند، کامپوننت خراب می‌شود. 2. تغییر در frontend/src/app/model-profiles/page.tsx ممکن است بر سایر کامپوننت‌هایی که از داده‌های سخت‌کد شده استفاده می‌کنند تأثیر بگذارد. 3. عدم تطابق نوع داده‌ها (TypeScript) می‌تواند باعث خطاهای runtime شود. 4. وابستگی به backend/app/api/routes/model_profiles.py که ممکن است نیاز به تغییر داشته باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 19: تعریف معیارهای پذیرش رفتار-محور و مراحل اجرایی برای اعمال تغییرات

**Scope:** این بخش شامل معیارهای پذیرش عمومی (AC) است که باید برای هر تغییر کد رعایت شود، شامل عبور تست‌ها، linter و type-check. همچنین مراحل اجرایی پیشنهادی را مشخص می‌کند که مجری باید بر اساس context تعیین کند. خروجی مورد انتظار تغییر کد در فایل‌های مرتبط و commit/PR با عبور تمام ACها است. این بخش دستورالعمل اجرایی مستقیم ندارد و بیشتر چارچوب ارزیابی را تعریف می‌کند.
**Key terms:** OversightService, tests/test_ai_llm_pipeline.py, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py, backend/app/services/oversight_service.py, tests/test_oversight_service.py, backend/app/api/routes/oversight.py, backend/app/main.py, backend/app/api/routes/github_import.py, backend/app/core/database.py, backend/app/models/setting.py, backend/app/services/verify_runtime/__init__.py, backend/app/ai_manager.py

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف معیارهای پذیرش رفتار-محور و مراحل اجرایی برای اعمال تغییرات

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py` — `OversightService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل سرویس اصلی oversight را شامل می‌شود که کاربر به آن اشاره کرده است.
- `backend/app/ai_manager.py` — `ai_manager` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است.
- `backend/app/api/routes/oversight.py` — `oversight_routes` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل روترهای مربوط به oversight را شامل می‌شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/oversight_strong_prompt.py` — کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل احتمالاً حاوی پرامپت‌های قوی برای oversight است.
- `tests/test_ai_llm_pipeline.py` — کاربر به این فایل تست به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل تست‌های مربوط به pipeline AI را شامل می‌شود.
- `tests/test_oversight_service.py` — کاربر به این فایل تست به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل تست‌های مربوط به OversightService را شامل می‌شود.
- `backend/app/main.py` — کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل نقطه ورود اصلی برنامه است.
- `backend/app/api/routes/github_import.py` — کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل روترهای مربوط به import از GitHub را شامل می‌شود.
- `backend/app/core/database.py` — کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل تنظیمات دیتابیس را شامل می‌شود.
- `backend/app/models/setting.py` — کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل مدل setting را شامل می‌شود.
- `backend/app/services/verify_runtime/__init__.py` — کاربر به این فایل به عنوان یکی از کلیدواژه‌ها اشاره کرده است. این فایل مربوط به verify runtime است.

## 🌐 نقشهٔ وابستگی‌ها
این درخواست یک چارچوب ارزیابی برای تغییرات کد تعریف می‌کند و مستقیماً به فایل‌های خاصی وابسته نیست. با این حال، فایل‌های ذکر شده توسط کاربر (OversightService در backend/app/services/oversight_service.py، ai_manager.py در backend/app/ai_manager.py، oversight_strong_prompt.py در backend/app/oversight_strong_prompt.py، tests/test_ai_llm_pipeline.py، tests/test_oversight_service.py، backend/app/api/routes/oversight.py، backend/app/main.py، backend/app/api/routes/github_import.py، backend/app/core/database.py، backend/app/models/setting.py، backend/app/services/verify_runtime/__init__.py) باید برای اعمال تغییرات در نظر گرفته شوند. هر تغییری در این فایل‌ها باید با معیارهای پذیرش تعریف شده مطابقت داشته باشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست تعریف معیارهای پذیرش عمومی (AC) رفتار-محور و مراحل اجرایی برای اعمال تغییرات کد را دارد. این معیارها باید برای هر تغییر کد رعایت شود و شامل عبور تست‌ها، linter و type-check است. همچنین مراحل اجرایی پیشنهادی مشخص می‌شود که مجری باید بر اساس context تعیین کند. خروجی مورد انتظار تغییر کد در فایل‌های مرتبط و commit/PR با عبور تمام ACها است. این بخش دستورالعمل اجرایی مستقیم ندارد و بیشتر چارچوب ارزیابی را تعریف می‌کند.

کلیدواژه‌های ذکر شده توسط کاربر: OversightService, tests/test_ai_llm_pipeline.py, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py, backend/app/services/oversight_service.py, tests/test_oversight_service.py, backend/app/api/routes/oversight.py, backend/app/main.py, backend/app/api/routes/github_import.py, backend/app/core/database.py, backend/app/models/setting.py, backend/app/services/verify_runtime/__init__.py, backend/app/ai_manager.py

معیارهای پذیرش تعریف شده:
- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

مراحل اجرایی پیشنهادی: (مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)

خروجی مورد انتظار: تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود — اجرای `pytest` و `npm run test` باید موفق باشد
- [ ] linter بدون warning عبور می‌کند — اجرای linter مربوط به پروژه (مثلاً flake8 یا pylint برای پایتون، eslint برای JS) باید بدون warning باشد
- [ ] type-check موفق است — اجرای `tsc --noEmit` برای TypeScript و `mypy` برای پایتون باید موفق باشد
- [ ] هیچ تستی fail نمی‌شود — اجرای `npm run test` و `pytest` باید بدون fail باشد
- [ ] type-check موفق است — اجرای `tsc --noEmit` و `mypy` باید موفق باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی فایل‌های مرتبط با کلیدواژه‌های ذکر شده: OversightService در backend/app/services/oversight_service.py، ai_manager.py در backend/app/ai_manager.py، oversight_strong_prompt.py در backend/app/oversight_strong_prompt.py، tests/test_ai_llm_pipeline.py، tests/test_oversight_service.py، backend/app/api/routes/oversight.py، backend/app/main.py، backend/app/api/routes/github_import.py، backend/app/core/database.py، backend/app/models/setting.py، backend/app/services/verify_runtime/__init__.py
2. تعریف معیارهای پذیرش رفتار-محور برای هر تغییر: هر AC باید رفتار قابل مشاهده را تعریف کند، نه نام فایل/کلاس. verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.
3. اطمینان از عبور تست‌های موجود با اجرای `pytest` و `npm run test`
4. اجرای linter و رفع warningها
5. اجرای type-check با `tsc --noEmit` و `mypy`
6. ایجاد commit یا PR با پیام واضح و عبور تمام معیارهای پذیرش

## 💡 نمونه‌های قبل/بعد
**مثال قبل از اعمال معیارهای پذیرش**

_قبل:_
```
تغییر کد بدون بررسی تست‌ها و linter اعمال می‌شود.
```

_بعد:_
```
تغییر کد با اجرای تست‌ها (`pytest` و `npm run test`)، linter و type-check (`tsc --noEmit` و `mypy`) اعمال می‌شود و تمام معیارهای پذیرش عبور می‌کنند.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run test`
- `tsc --noEmit`
- `mypy`

## ⚠️ ریسک‌ها و موارد احتیاط
این درخواست یک چارچوب ارزیابی است و ریسک مستقیمی برای کدبیس ندارد. با این حال، اعمال معیارهای پذیرش ممکن است باعث افزایش زمان توسعه شود. فایل‌های ذکر شده توسط کاربر (OversightService, ai_manager.py, oversight_strong_prompt.py, tests/test_ai_llm_pipeline.py, tests/test_oversight_service.py, backend/app/api/routes/oversight.py, backend/app/main.py, backend/app/api/routes/github_import.py, backend/app/core/database.py, backend/app/models/setting.py, backend/app/services/verify_runtime/__init__.py) ممکن است تحت تأثیر قرار گیرند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 20: اضافه کردن validation و guardrails به خروجی oversight_strong_prompt

**Scope:** این بخش شامل پیاده‌سازی validation و guardrails برای خروجی oversight_strong_prompt است تا از بروز توهم (hallucination) جلوگیری شود. همچنین شامل شناسایی ناسازگاری‌ها، تعیین ground truth، و نوشتن integration test برای pipeline ai_llm می‌شود. فایل‌های اصلی backend/app/oversight_strong_prompt.py و backend/app/ai_llm/pipeline.py هستند. خارج از scope: تغییرات در سایر سرویس‌ها یا APIها.
**Key terms:** oversight_strong_prompt, validation, guardrail, hallucination, backend/app/ai_llm/pipeline.py, backend/app/oversight_strong_prompt.py, tests/test_ai_llm_pipeline.py::test_integration, PR_description.md

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 16
  id: aa8c1673-2357-40d4-9088-2e28a2c5eb7b
  عنوان اصلی: [منطق] عدم وجود validation و guardrails در خروجی oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "oversight_strong_prompt"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["PR_description.md"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن validation و guardrails به خروجی oversight_strong_prompt

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py:1-50` — `کل فایل` — فایل اصلی که باید validation و guardrails به آن اضافه شود. بر اساس ساختار سطحی — توسط مجری تأیید شود.
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی
  ```
- `backend/app/ai_llm/pipeline.py:1-30` — `کل فایل (جدید)` — فایل جدید برای pipeline ai_llm که شامل validation logic است. مسیر دقیق توسط مجری تأیید شود.
  ```python
  فایل جدید — باید ایجاد شود
  ```
- `backend/tests/test_ai_llm_pipeline.py:1-40` — `کل فایل (جدید)` — فایل تست جدید برای integration test pipeline ai_llm. مسیر دقیق توسط مجری تأیید شود.
  ```python
  فایل جدید — باید ایجاد شود
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_service.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند یا خروجی آن را پردازش می‌کند
- `backend/app/services/oversight_verifier.py` — مسئول verify خروجی‌ها — ممکن است نیاز به هماهنگی با validation جدید داشته باشد
- `backend/app/services/oversight_inspector_bridge.py` — پل بین inspector و oversight — ممکن است خروجی strong_prompt را مصرف کند

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر فایل‌های backend/app/services/oversight_strong_prompt.py (سرویس اصلی تولید strong prompt)، backend/app/ai_llm/pipeline.py (pipeline جدید برای validation)، و backend/tests/test_ai_llm_pipeline.py (تست‌های یکپارچه‌سازی) متمرکز است. فایل‌های مرتبط شامل backend/app/services/oversight_service.py (که احتمالاً از strong_prompt استفاده می‌کند)، backend/app/services/oversight_verifier.py (برای verify)، و backend/app/services/oversight_inspector_bridge.py (پل بین inspector و oversight) هستند. تغییرات در oversight_strong_prompt.py می‌تواند روی تمام سرویس‌هایی که از آن import می‌کنند تأثیر بگذارد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست اضافه کردن validation و guardrails به خروجی oversight_strong_prompt را دارد تا از بروز توهم (hallucination) جلوگیری شود. همچنین شامل شناسایی ناسازگاری‌ها، تعیین ground truth، و نوشتن integration test برای pipeline ai_llm می‌شود. فایل‌های اصلی backend/app/oversight_strong_prompt.py و backend/app/ai_llm/pipeline.py هستند. خارج از scope: تغییرات در سایر سرویس‌ها یا APIها.

کلیدواژه‌های اصلی: oversight_strong_prompt, validation, guardrail, hallucination, backend/app/ai_llm/pipeline.py, backend/app/oversight_strong_prompt.py, tests/test_ai_llm_pipeline.py::test_integration, PR_description.md

بر اساس ساختار پروژه، فایل backend/app/services/oversight_strong_prompt.py در مسیر services قرار دارد (نه مستقیماً در backend/app/). همچنین فایل backend/app/ai_llm/pipeline.py در ساختار پروژه موجود نیست و احتمالاً باید ایجاد شود یا مسیر آن اصلاح گردد. فایل‌های مرتبط شامل backend/app/services/oversight_service.py (که احتمالاً از oversight_strong_prompt استفاده می‌کند) و backend/app/services/oversight_verifier.py (برای verify) هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline ai_llm بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل backend/app/ai_llm/pipeline.py با کلاس AiLlmPipeline که شامل متد validate_output برای بررسی خروجی oversight_strong_prompt است.
2. افزودن تابع validate_strong_prompt_output به backend/app/services/oversight_strong_prompt.py که:
   - ناسازگاری‌های منطقی را شناسایی کند
   - ground truth را از context استخراج کند
   - خروجی‌های توهم‌آمیز را فیلتر کند
3. ایجاد integration test در tests/test_ai_llm_pipeline.py با تابع test_integration که pipeline کامل را تست کند.
4. به‌روزرسانی PR_description.md با توضیح تصمیمات.
5. اطمینان از اینکه oversight_strong_prompt از validate_strong_prompt_output استفاده می‌کند.

## 💡 نمونه‌های قبل/بعد
**افزودن validation به oversight_strong_prompt**

_قبل:_
```
# backend/app/services/oversight_strong_prompt.py (فعلی)
def generate_strong_prompt(context):
    # تولید prompt بدون validation
    return prompt
```

_بعد:_
```
# backend/app/services/oversight_strong_prompt.py (پس از تغییر)
from backend.app.ai_llm.pipeline import validate_output

def generate_strong_prompt(context):
    prompt = _generate_raw_prompt(context)
    validated = validate_output(prompt, context)
    return validated
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_llm_pipeline.py::test_integration -v`
- `python -c "from backend.app.services.oversight_strong_prompt import generate_strong_prompt; print('Import OK')"`
- `python -c "from backend.app.ai_llm.pipeline import validate_output; print('Import OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل backend/app/services/oversight_strong_prompt.py deep-read نشده و ممکن است ساختار داخلی پیچیده‌ای داشته باشد. همچنین فایل backend/app/ai_llm/pipeline.py وجود ندارد و باید ایجاد شود که ممکن است با命名 conventions پروژه هماهنگ نباشد. تغییر در oversight_strong_prompt.py می‌تواند روی oversight_service.py و oversight_verifier.py که احتمالاً از آن استفاده می‌کنند تأثیر بگذارد. مسیر دقیق فایل‌ها توسط مجری تأیید شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 21: افزودن لایه اعتبارسنجی و گاردریل به خروجی oversight_strong_prompt

**Scope:** این بخش شامل افزودن validation به تابع یا کلاس تولیدکننده پرامپت در فایل oversight_strong_prompt.py است. موارد تحت پوشش: (1) بررسی وجود فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'. خارج از scope: تغییر در pipeline کلی، اصلاح مدل‌های خارجی، یا تغییر در سایر فایل‌های پروژه.
**Key terms:** backend/app/oversight_strong_prompt.py, OversightService, validation, guardrails, hallucination guards, target_locations, ignore previous instructions

**بخش مربوط از متن کاربر:**
```
یک لایه validation به oversight_strong_prompt اضافه کنید: (1) بررسی وجود تمام فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است، کلیدهای مورد انتظار را بررسی کند)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک (مثلاً 'ignore previous instructions').
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن لایه اعتبارسنجی و گاردریل به oversight_strong_prompt

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py:1-50` — `تابع تولید پرامپت (نام دقیق مشخص نیست)` — فایل deep-read نشده است — بر اساس ساختار سطحی پروژه، این فایل در backend/app/services/ موجود است و باید توسط مجری تأیید شود. تابع اصلی تولید پرامپت احتمالاً در خطوط ابتدایی فایل قرار دارد.
- `backend/app/services/oversight_strong_prompt.py:100-150` — `بخش خروجی پرامپت` — فایل deep-read نشده است — بر اساس ساختار سطحی، احتمالاً بخش خروجی پرامپت در این محدوده خطوط قرار دارد. تابع validation باید قبل از این بخش فراخوانی شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_service.py` — این سرویس احتمالاً oversight_strong_prompt را فراخوانی می‌کند و از خروجی آن استفاده می‌کند. تغییر در خروجی می‌تواند روی عملکرد این سرویس تأثیر بگذارد.
- `backend/app/services/oversight_inspector_bridge.py` — این فایل پل ارتباطی بین oversight و inspector است و ممکن است از پرامپت تولید شده استفاده کند. اعتبارسنجی می‌تواند از ارسال داده‌های ناقص به inspector جلوگیری کند.
- `backend/app/services/oversight_verifier.py` — این سرویس وظیفه تأیید خروجی‌ها را دارد و ممکن است از پرامپت تولید شده برای تأیید استفاده کند. اعتبارسنجی می‌تواند دقت تأیید را افزایش دهد.

## 🌐 نقشهٔ وابستگی‌ها
فایل هدف backend/app/services/oversight_strong_prompt.py است که احتمالاً توسط oversight_service.py و سایر سرویس‌های مرتبط با oversight مانند oversight_inspector_bridge.py و oversight_verifier.py فراخوانی می‌شود. این فایل بخشی از زیرسیستم oversight پروژه است که وظیفه تولید پرامپت‌های قوی برای مدل‌های هوش مصنوعی را دارد. تغییر در این فایل می‌تواند روی خروجی تمام سرویس‌هایی که از آن استفاده می‌کنند تأثیر بگذارد. همچنین فایل‌های تست مرتبط مانند backend/tests/test_inspector_oversight_bridge.py ممکن است نیاز به به‌روزرسانی داشته باشند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن یک لایه validation به تابع یا کلاس تولیدکننده پرامپت در فایل backend/app/services/oversight_strong_prompt.py را دارد. این لایه باید چهار مورد را پوشش دهد: (1) بررسی وجود فیلدهای اجباری شامل title, user_goal, description، (2) اعتبارسنجی قالب target_locations اگر از نوع List[Dict] است و کلیدهای مورد انتظار را بررسی کند، (3) محدودیت طول پرامپت برای جلوگیری از خروجی‌های بیش از حد طولانی، (4) فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions' که می‌تواند باعث نادیده گرفتن دستورات سیستم شود. کاربر تأکید کرده که خارج از scope این تسک، تغییر در pipeline کلی، اصلاح مدل‌های خارجی، یا تغییر در سایر فایل‌های پروژه مجاز نیست. کلیدواژه‌های اصلی: backend/app/oversight_strong_prompt.py, OversightService, validation, guardrails, hallucination guards, target_locations, ignore previous instructions. در کد فعلی پروژه، فایل oversight_strong_prompt.py در مسیر backend/app/services/ موجود است و به نظر می‌رسد که توسط OversightService یا سایر سرویس‌های مرتبط با oversight فراخوانی می‌شود. با توجه به commit‌های اخیر مانند 'fix(inspector): قاعدهٔ صفر placeholder = build pipeline + timestamp scan' و 'fix(inspector): سه باگ بنیادی که باعث رفتار گاو شده بود'، به نظر می‌رسد پروژه در حال بهبود سیستم‌های inspection و oversight است و این درخواست نیز در همین راستا مطرح شده است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تابع validate_prompt_fields باید وجود فیلدهای اجباری title, user_goal, description را بررسی کند و در صورت缺失، ValueError با پیام مناسب برگرداند.
- [ ] اعتبارسنجی target_locations: اگر از نوع List[Dict] باشد، هر آیتم باید کلید path داشته باشد. در غیر این صورت خطا برگرداند.
- [ ] محدودیت طول پرامپت: اگر طول پرامپت بیش از 4000 کاراکتر باشد، ValueError برگرداند.
- [ ] فیلتر دستورات خطرناک: اگر پرامپت شامل 'ignore previous instructions' باشد، ValueError برگرداند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/services/oversight_strong_prompt.py را باز کرده و تابع یا کلاس اصلی تولید پرامپت را شناسایی کن. 2. یک تابع جدید به نام validate_prompt_fields(prompt_data: dict) -> dict اضافه کن که: (a) بررسی کند کلیدهای 'title', 'user_goal', 'description' در دیکشنری ورودی وجود داشته باشند و خالی نباشند، (b) اگر کلید 'target_locations' وجود داشت و از نوع list بود، هر آیتم را بررسی کند که دیکشنری باشد و کلیدهای مورد انتظار (مانند 'path', 'lines', 'symbol') را داشته باشد، (c) طول رشته پرامپت نهایی را محدود کند (مثلاً حداکثر 4000 کاراکتر)، (d) با استفاده از regex یا جستجوی رشته، عبارات خطرناک مانند 'ignore previous instructions' را فیلتر کرده و در صورت وجود، خطا برگرداند. 3. این تابع validation را در ابتدای تابع اصلی تولید پرامپت فراخوانی کن تا قبل از ارسال به مدل، داده‌ها اعتبارسنجی شوند. 4. خطاهای validation را به صورت exception با پیام مشخص برگردان تا caller بتواند مدیریت کند. 5. تست‌های واحد برای این تابع جدید در backend/tests/ اضافه کن.

## 💡 نمونه‌های قبل/بعد
**افزودن تابع validate_prompt_fields**

_قبل:_
```
# کد فعلی (نمونه فرضی)
def generate_strong_prompt(data):
    prompt = f"Title: {data.get('title', '')}\nGoal: {data.get('user_goal', '')}\nDescription: {data.get('description', '')}"
    return prompt
```

_بعد:_
```
# کد پیشنهادی
def validate_prompt_fields(data: dict) -> dict:
    required_fields = ['title', 'user_goal', 'description']
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"فیلد اجباری {field}缺失 است")
    if 'target_locations' in data and isinstance(data['target_locations'], list):
        for item in data['target_locations']:
            if not isinstance(item, dict) or 'path' not in item:
                raise ValueError("target_locations باید List[Dict] با کلید path باشد")
    prompt_str = str(data)
    if len(prompt_str) > 4000:
        raise ValueError("طول پرامپت بیش از حد مجاز است")
    dangerous_patterns = ['ignore previous instructions', 'ignore all instructions']
    for pattern in dangerous_patterns:
        if pattern in prompt_str.lower():
            raise ValueError(f"دستور خطرناک {pattern} در پرامپت یافت شد")
    return data

def generate_strong_prompt(data):
    validated_data = validate_prompt_fields(data)
    prompt = f"Title: {validated_data['title']}\nGoal: {validated_data['user_goal']}\nDescription: {validated_data['description']}"
    return prompt
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_strong_prompt.py -v`
- `python -c "from backend.app.services.oversight_strong_prompt import validate_prompt_fields; print('Import OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در oversight_strong_prompt.py می‌تواند روی تمام سرویس‌هایی که از آن استفاده می‌کنند (oversight_service.py, oversight_inspector_bridge.py, oversight_verifier.py) تأثیر بگذارد. اگر validation بیش از حد سخت‌گیرانه باشد، ممکن است پرامپت‌های معتبر نیز رد شوند. همچنین اگر تابع validation قبل از تولید پرامپت فراخوانی نشود، ممکن است داده‌های نامعتبر به مدل ارسال شوند. ریسک دیگر این است که فایل‌های تست موجود ممکن است با خطاهای جدید validation سازگار نباشند و نیاز به به‌روزرسانی داشته باشند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 22: بررسی و مستندسازی ناسازگاری‌های دو طرف oversight_strong_prompt و ai_llm با مکانیزم fallback

**Scope:** این مرحله شامل تحلیل و مستندسازی ناسازگاری‌های موجود بین دو مؤلفه oversight_strong_prompt و ai_llm است. تمرکز بر شناسایی فرض‌های هر طرف، تعیین ground truth و align کردن طرف دیگر است. همچنین شامل نوشتن integration test برای pipeline ai_llm و مستندسازی تصمیمات در PR description می‌شود. فایل‌های اصلی دخیل backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py هستند.
**Key terms:** oversight_strong_prompt, ai_llm, fallback, error handling, retry, backend/app/oversight_strong_prompt.py, backend/app/ai_llm.py, tests/test_ai_llm_pipeline.py, .github/pull_request_template.md

**بخش مربوط از متن کاربر:**
```
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
  - بررسی وضعیت موجود فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm
  - اضافه کردن اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt — اضافه کردن اعتبارسنجی فیلدهای اجباری title, user_goal, description
  - اعتبارسنجی قالب target_locations (بررسی کلیدهای مورد انتظار در List[Dict]) — اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict])
  - اضافه کردن محدودیت طول پرامپت (max length check) — اضافه کردن محدودیت طول پرامپت (max length check)
  - فیلتر کردن دستورات خطرناک (مانند 'ignore previous instructions') در پرامپت — فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'
  - نوشتن تست‌های واحد برای هر چهار لایه validation — نوشتن تست‌های واحد برای هر چهار لایه validation
  - ثبت کامیت‌ها و نوشتن PR description با checklist — ثبت کامیت‌ها و نوشتن PR description با checklist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 9 از 16
  id: 00c2f0ef-15a2-400a-a082-6123f8af075f
  عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "fallback", "error handling", "retry"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "fallback", "oversight_strong_prompt"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why"], "files_hint": [".github/pull_request_template.md"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
تحلیل و رفع ناسازگاری‌های oversight_strong_prompt و ai_llm با مکانیزم fallback

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً حاوی منطق تولید پرامپت‌های قوی برای oversight است.
- `backend/app/services/ai_llm.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً حاوی منطق fallback بین مدل‌های مختلف AI است.
- `backend/app/services/ai_manager.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً به عنوان orchestrator بین سرویس‌های مختلف AI عمل می‌کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` — کلاس پایه برای سرویس‌های AI که احتمالاً توسط ai_llm استفاده می‌شود
- `backend/app/services/ai_balance_service.py` — سرویس بالانس که ممکن است با مکانیزم fallback تداخل داشته باشد
- `backend/app/services/oversight_service.py` — سرویس اصلی oversight که احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_verifier.py` — سرویس verifier که ممکن است خروجی oversight_strong_prompt را مصرف کند
- `backend/app/services/oversight_inspector_bridge.py` — پل ارتباطی با inspector که ممکن است از پرامپت‌های تولید شده استفاده کند

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر دو مؤلفه اصلی تمرکز دارد: oversight_strong_prompt (احتمالاً در backend/app/services/oversight_strong_prompt.py) و ai_llm (احتمالاً در backend/app/services/ai_llm.py). فایل‌های مرتبط شامل ai_base.py (کلاس پایه)، ai_balance_service.py (بالانس بین مدل‌ها)، oversight_service.py (سرویس اصلی oversight)، oversight_verifier.py (تأییدکننده)، و oversight_inspector_bridge.py (پل با inspector) هستند. تغییر در oversight_strong_prompt می‌تواند روی همه مصرف‌کنندگان downstream تأثیر بگذارد. تغییر در ai_llm می‌تواند روی مکانیزم fallback و انتخاب مدل تأثیر بگذارد.

## 🔍 Context و وضعیت فعلی
بررسی و مستندسازی ناسازگاری‌های دو طرف oversight_strong_prompt و ai_llm با مکانیزم fallback. این مرحله شامل تحلیل و مستندسازی ناسازگاری‌های موجود بین دو مؤلفه oversight_strong_prompt و ai_llm است. تمرکز بر شناسایی فرض‌های هر طرف، تعیین ground truth و align کردن طرف دیگر است. همچنین شامل نوشتن integration test برای pipeline ai_llm و مستندسازی تصمیمات در PR description می‌شود. فایل‌های اصلی دخیل backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py هستند. بخش مربوط از درخواست اصلی کاربر: ⚠️ ریسک‌ها و موارد احتیاط: تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن. مراحل remaining که در super-task باید انجام شوند: بررسی وضعیت موجود فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm، اضافه کردن اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt — اضافه کردن اعتبارسنجی فیلدهای اجباری title, user_goal, description، اعتبارسنجی قالب target_locations (بررسی کلیدهای مورد انتظار در List[Dict]) — اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict])، اضافه کردن محدودیت طول پرامپت (max length check) — اضافه کردن محدودیت طول پرامپت (max length check)، فیلتر کردن دستورات خطرناک (مانند 'ignore previous instructions') در پرامپت — فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'، نوشتن تست‌های واحد برای هر چهار لایه validation — نوشتن تست‌های واحد برای هر چهار لایه validation، ثبت کامیت‌ها و نوشتن PR description با checklist — ثبت کامیت‌ها و نوشتن PR description با checklist. تسک 9 از 16 با id: 00c2f0ef-15a2-400a-a082-6123f8af075f، عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt، اولویت اصلی: high، وضعیت verify قبلی: pending. acceptance_criteria کامل: هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "fallback", "error handling", "retry"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}], ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "fallback", "oversight_strong_prompt"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}], integration test برای pipeline ai_llm بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}], PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why"], "files_hint": [".github/pull_request_template.md"]}]. کلیدواژه‌ها: oversight_strong_prompt, ai_llm, fallback, error handling, retry, backend/app/oversight_strong_prompt.py, backend/app/ai_llm.py, tests/test_ai_llm_pipeline.py, .github/pull_request_template.md.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد — با grep برای الگوهای 'oversight_strong_prompt', 'fallback', 'error handling', 'retry' در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py
- [ ] ground truth تعیین شد و طرف دیگر align شد — با grep برای الگوهای 'ground truth', 'align', 'fallback', 'oversight_strong_prompt' در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py
- [ ] integration test برای pipeline ai_llm بدون شکست عبور می‌کند — اجرای تست tests/test_ai_llm_pipeline.py::test_integration با timeout 120 ثانیه
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد — با grep برای الگوهای 'PR description', 'decision', 'why' در فایل .github/pull_request_template.md
- [ ] اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt اضافه شده است
- [ ] اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict]) اضافه شده است
- [ ] محدودیت طول پرامپت (max length check) اضافه شده است
- [ ] فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions' در پرامپت اضافه شده است
- [ ] تست‌های واحد برای هر چهار لایه validation نوشته شده و عبور می‌کنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی وضعیت موجود فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm: فایل‌های backend/app/services/oversight_strong_prompt.py و backend/app/services/ai_llm.py (در صورت وجود) را باز کرده و ساختار فعلی، فرض‌های هر طرف و نحوه fallback را تحلیل کن. 2. اضافه کردن اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt: یک تابع validate_required_fields اضافه کن که وجود و غیرخالی بودن این فیلدها را بررسی کند. 3. اعتبارسنجی قالب target_locations: یک تابع validate_target_locations_format اضافه کن که بررسی کند target_locations یک List[Dict] است و هر دیکشنری کلیدهای مورد انتظار (مانند path, lines, symbol) را دارد. 4. اضافه کردن محدودیت طول پرامپت: یک تابع validate_prompt_length اضافه کن که طول پرامپت را با یک MAX_PROMPT_LENGTH (مثلاً 4000 کاراکتر) مقایسه کند. 5. فیلتر کردن دستورات خطرناک: یک تابع filter_dangerous_commands اضافه کن که عباراتی مانند 'ignore previous instructions' را از پرامپت حذف کند. 6. نوشتن تست‌های واحد برای هر چهار لایه validation: فایل tests/test_ai_llm_pipeline.py را ایجاد کن و برای هر تابع validation یک تست بنویس. 7. ثبت کامیت‌ها و نوشتن PR description با checklist: کامیت‌ها را با پیام‌های واضح ثبت کن و در PR description توضیح بده چرا این تصمیمات گرفته شده‌اند.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن اعتبارسنجی فیلدهای اجباری در oversight_strong_prompt**

_قبل:_
```
# کد فعلی (فرضی - نیاز به تأیید)
def generate_strong_prompt(title, user_goal, description, target_locations):
    prompt = f"Title: {title}\nGoal: {user_goal}\nDescription: {description}"
    return prompt
```

_بعد:_
```
# کد پیشنهادی
def validate_required_fields(title, user_goal, description):
    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")
    if not user_goal or not user_goal.strip():
        raise ValueError("user_goal is required and cannot be empty")
    if not description or not description.strip():
        raise ValueError("description is required and cannot be empty")

def generate_strong_prompt(title, user_goal, description, target_locations):
    validate_required_fields(title, user_goal, description)
    prompt = f"Title: {title}\nGoal: {user_goal}\nDescription: {description}"
    return prompt
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest tests/test_ai_llm_pipeline.py -v`
- `pytest tests/test_ai_llm_pipeline.py::test_integration -v --timeout=120`
- `grep -rn 'validate_required_fields\|validate_target_locations\|validate_prompt_length\|filter_dangerous_commands' backend/app/oversight_strong_prompt.py`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در oversight_strong_prompt.py می‌تواند روی همه مصرف‌کنندگان downstream مانند oversight_service.py، oversight_verifier.py، و oversight_inspector_bridge.py تأثیر بگذارد. تغییر در ai_llm.py می‌تواند روی مکانیزم fallback و انتخاب مدل در ai_manager.py و ai_balance_service.py تأثیر بگذارد. قبل از merge، همه caller های هر دو طرف باید بررسی شوند. همچنین، اضافه کردن validationهای جدید ممکن است باعث شکست درخواست‌های موجود شود که فیلدهای اجباری را ارسال نمی‌کنند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 23: افزودن مکانیزم fallback و error handling به oversight_strong_prompt

**Scope:** این مرحله شامل افزودن لایه error handling به فایل backend/app/oversight_strong_prompt.py است. شامل: (1) پیاده‌سازی retry با backoff برای زمان‌هایی که مدل خارجی پاسخ نمی‌دهد، (2) fallback به یک مدل جایگزین (احتمالاً از طریق ai_manager)، (3) ثبت خطا و بازگشت پاسخ پیش‌فرض (graceful degradation). این مرحله شامل تغییر در pipeline ai_llm و فایل‌های مرتبط مانند backend/app/ai_manager.py و backend/app/services/oversight_service.py می‌شود. خارج از scope: تغییر در سایر pipeline‌ها یا فایل‌های غیرمرتبط با ai_llm.
**Key terms:** backend/app/oversight_strong_prompt.py, backend/app/ai_manager.py, backend/app/services/oversight_service.py, ai_llm, OversightService

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در حالی که ai_manager دارای قابلیت fallback و load balancing است، oversight_strong_prompt هیچ مکانیزم fallback یا error handling برای زمانی که مدل خارجی (Cursor, ChatGPT) پاسخ نمی‌دهد یا خطا می‌دهد، ندارد.

## 💥 پیامد (impact)
اگر مدل خارجی در دسترس نباشد یا timeout رخ دهد، کل pipeline بدون هیچ تلاشی برای بازیابی (retry, fallback به مدل دیگر) از کار می‌افتد. این باعث تجربه کاربری ضعیف و از دست رفتن درخواست‌ها می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک لایه error handling به oversight_strong_prompt اضافه کنید: (1) retry با backoff، (2) fallback به یک مدل جایگزین (مثلاً از طریق ai_manager)، (3) ثبت خطا و بازگشت یک پاسخ پیش‌فرض (graceful degradation).
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن مکانیزم fallback و error handling به oversight_strong_prompt

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py:1-50` — `کل فایل (deep-read نشده)` — فایل deep-read نشده — مجری باید ساختار داخلی را بررسی کند. احتمالاً شامل تابع main برای فراخوانی مدل خارجی است.
- `backend/app/services/ai_manager.py:1-100` — `AiManager` — فایل deep-read نشده — مجری باید متدهای fallback و load balancing موجود را شناسایی کند. احتمالاً متدهایی مانند `get_model`, `call_with_fallback`, `get_available_models` وجود دارد.
- `backend/app/services/oversight_service.py:1-50` — `OversightService` — فایل deep-read نشده — مجری باید نحوه استفاده از oversight_strong_prompt را بررسی کند. احتمالاً متدی مانند `run_oversight` یا `analyze` وجود دارد که خروجی strong_prompt را مصرف می‌کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_manager.py` — احتمالاً شامل متدهای fallback و load balancing است که باید برای fallback استفاده شوند
- `backend/app/services/oversight_service.py` — مصرف‌کننده خروجی oversight_strong_prompt — باید برای graceful degradation به‌روزرسانی شود
- `backend/app/services/ai_base.py` — کلاس پایه برای سرویس‌های AI — احتمالاً شامل متدهای common برای retry و error handling است
- `backend/app/core/config.py` — احتمالاً شامل تنظیمات timeout، retry count، و fallback model است
- `backend/app/services/oversight_verifier.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند و تحت تأثیر تغییرات قرار می‌گیرد

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات بر pipeline ai_llm تأثیر می‌گذارد که شامل فایل‌های backend/app/services/oversight_strong_prompt.py (نقطه اصلی تغییر)، backend/app/services/ai_manager.py (منبع fallback)، backend/app/services/oversight_service.py (مصرف‌کننده)، و backend/app/services/ai_base.py (کلاس پایه) است. همچنین backend/app/core/config.py برای تنظیمات retry/timeout و backend/app/services/oversight_verifier.py به عنوان مصرف‌کننده ثانویه تحت تأثیر قرار می‌گیرند. تغییرات باید محدود به pipeline ai_llm باقی بماند و سایر pipeline‌ها (مانند ai_chat, ai_analysis) تغییر نکنند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن مکانیزم fallback و error handling به فایل backend/app/services/oversight_strong_prompt.py را دارد. این درخواست بر اساس یک ناسازگاری منطقی در pipeline `ai_llm` است: در حالی که ai_manager دارای قابلیت fallback و load balancing است، oversight_strong_prompt هیچ مکانیزم fallback یا error handling برای زمانی که مدل خارجی (Cursor, ChatGPT) پاسخ نمی‌دهد یا خطا می‌دهد، ندارد. پیامد این مشکل این است که اگر مدل خارجی در دسترس نباشد یا timeout رخ دهد، کل pipeline بدون هیچ تلاشی برای بازیابی (retry, fallback به مدل دیگر) از کار می‌افتد و باعث تجربه کاربری ضعیف و از دست رفتن درخواست‌ها می‌شود. پیشنهاد رفع اولیه شامل سه بخش است: (1) پیاده‌سازی retry با backoff برای زمان‌هایی که مدل خارجی پاسخ نمی‌دهد، (2) fallback به یک مدل جایگزین (احتمالاً از طریق ai_manager)، (3) ثبت خطا و بازگشت پاسخ پیش‌فرض (graceful degradation). این تغییرات باید در pipeline ai_llm و فایل‌های مرتبط مانند backend/app/services/ai_manager.py و backend/app/services/oversight_service.py اعمال شود. خارج از scope: تغییر در سایر pipeline‌ها یا فایل‌های غیرمرتبط با ai_llm. کلیدواژه‌ها: backend/app/services/oversight_strong_prompt.py, backend/app/services/ai_manager.py, backend/app/services/oversight_service.py, ai_llm, OversightService

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هنگام timeout مدل خارجی، تابع باید حداقل ۳ بار با backoff exponential تلاش مجدد کند
- [ ] پس از شکست همه تلاش‌های retry، تابع باید به مدل جایگزین از طریق ai_manager fallback کند
- [ ] در صورت شکست fallback نیز، تابع باید یک پاسخ پیش‌فرض با کلید 'error' و 'fallback_used': False بازگرداند
- [ ] همه خطاها و مسیر fallback باید در logger با سطح مناسب (warning برای retry, error برای fallback, critical برای شکست کامل) ثبت شوند
- [ ] تغییرات فقط در pipeline ai_llm اعمال شود و سایر pipeline‌ها (ai_chat, ai_analysis) تغییر نکنند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی فایل backend/app/services/oversight_strong_prompt.py برای شناسایی نقاطی که مدل خارجی فراخوانی می‌شود (احتمالاً تابعی مانند `call_external_model` یا `generate_strong_prompt`). 2. افزودن یک decorator یا wrapper با قابلیت retry با backoff exponential (مثلاً با استفاده از کتابخانه tenacity یا پیاده‌سازی دستی). 3. پیاده‌سازی fallback به مدل جایگزین از طریق ai_manager: در صورت شکست retry، یک مدل دیگر (مثلاً از لیست مدل‌های پشتیبانی‌شده در ai_manager) انتخاب شود. 4. افزودن logging جامع برای ثبت خطاها و مسیر fallback. 5. بازگشت یک پاسخ پیش‌فرض (مثلاً یک دیکشنری با کلید 'error' و 'fallback_used') در صورت شکست کامل. 6. به‌روزرسانی oversight_service.py در صورت نیاز برای پشتیبانی از پاسخ‌های fallback. 7. افزودن تست‌های unit برای سناریوهای timeout، خطای مدل، و fallback موفق.

## 💡 نمونه‌های قبل/بعد
**افزودن retry wrapper به تابع فراخوانی مدل خارجی**

_قبل:_
```
# backend/app/services/oversight_strong_prompt.py (فرضی)
def call_external_model(prompt: str) -> dict:
    response = requests.post(EXTERNAL_API_URL, json={"prompt": prompt})
    return response.json()
```

_بعد:_
```
# backend/app/services/oversight_strong_prompt.py (پس از تغییر)
import time
import logging
from typing import Optional
from backend.app.services.ai_manager import AiManager

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
FALLBACK_MODEL = "gpt-3.5-turbo"  # یا مدل پیش‌فرض دیگر

def call_external_model_with_fallback(prompt: str, ai_manager: AiManager) -> dict:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(EXTERNAL_API_URL, json={"prompt": prompt}, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_FACTOR ** attempt)
    
    # Fallback به مدل جایگزین از طریق ai_manager
    logger.error(f"All {MAX_RETRIES} attempts failed. Falling back to {FALLBACK_MODEL}")
    try:
        fallback_response = ai_manager.call_model(FALLBACK_MODEL, prompt)
        return {"fallback_used": True, "data": fallback_response}
    except Exception as fallback_error:
        logger.critical(f"Fallback also failed: {fallback_error}")
        return {"error": "All attempts and fallback failed", "fallback_used": False}
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_strong_prompt.py -v -m verify`
- `python -m pytest backend/tests/ -k "oversight_strong_prompt" --coverage`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل backend/app/services/oversight_strong_prompt.py deep-read نشده است، بنابراین تغییرات ممکن است با ساختار داخلی آن ناسازگار باشد. همچنین backend/app/services/ai_manager.py و backend/app/services/oversight_service.py نیز deep-read نشده‌اند، بنابراین نحوه تعامل دقیق آن‌ها با oversight_strong_prompt نامشخص است. ریسک اصلی: اگر ai_manager متد fallback مناسبی نداشته باشد، باید یک fallback سفارشی پیاده‌سازی شود که ممکن است scope را گسترش دهد. همچنین تغییر در oversight_strong_prompt ممکن است بر oversight_verifier که احتمالاً از آن استفاده می‌کند تأثیر بگذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 24: بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager

**Scope:** این مرحله شامل تحلیل کامل کد موجود در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_manager.py است. هدف، مستندسازی رفتار فعلی، نقاط ضعف، وابستگی‌ها و نحوه تعامل این دو سرویس با یکدیگر است. خروجی این مرحله یک سند یا کامنت‌های کد خواهد بود که وضعیت موجود را به‌طور شفاف توصیف می‌کند. این مرحله شامل هیچ تغییری در منطق یا اضافه کردن قابلیت جدید نیست.
**Key terms:** backend/app/oversight_strong_prompt.py, backend/app/ai_manager.py, OversightService, downstream consumers, caller

**بخش مربوط از متن کاربر:**
```
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
  - بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager — بررسی و مستندسازی کامل وضعیت فعلی دو سرویس
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py` — `OversightStrongPromptService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً شامل کلاس OversightStrongPromptService است که پرامپت‌های قوی برای oversight تولید می‌کند.
- `backend/app/services/ai_manager.py` — `AIManager` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً شامل کلاس AIManager است که مدیریت مدل‌های هوش مصنوعی و تعامل با آن‌ها را بر عهده دارد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_service.py` — احتمالاً از oversight_strong_prompt برای تولید پرامپت‌های قوی استفاده می‌کند — downstream consumer اصلی
- `backend/app/services/oversight_inspector_bridge.py` — احتمالاً از ai_manager برای تعامل با مدل‌های هوش مصنوعی در فرآیند oversight استفاده می‌کند
- `backend/app/services/oversight_verifier.py` — احتمالاً از هر دو سرویس برای تأیید و راستی‌آزمایی استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر دو فایل اصلی متمرکز است: backend/app/services/oversight_strong_prompt.py و backend/app/services/ai_manager.py. فایل اول احتمالاً توسط backend/app/services/oversight_service.py و backend/app/services/oversight_verifier.py و backend/app/services/oversight_inspector_bridge.py استفاده می‌شود. فایل دوم احتمالاً توسط backend/app/services/ai_balance_service.py، backend/app/services/ai_base.py و backend/app/services/ai_manager.py (خودش) و همچنین backend/app/services/oversight_inspector_bridge.py استفاده می‌شود. وابستگی‌های متقابل بین این دو سرویس باید دقیقاً شناسایی شوند. همچنین فایل‌های backend/app/services/oversight_strong_prompt.py و backend/app/services/ai_manager.py ممکن است به فایل‌های مشترکی مانند backend/app/core/config.py یا backend/app/core/models_registry.py وابسته باشند.

## 🔍 Context و وضعیت فعلی
این تسک شامل تحلیل کامل کد موجود در فایل‌های backend/app/services/oversight_strong_prompt.py و backend/app/services/ai_manager.py است. هدف، مستندسازی رفتار فعلی، نقاط ضعف، وابستگی‌ها و نحوه تعامل این دو سرویس با یکدیگر است. خروجی این مرحله یک سند یا کامنت‌های کد خواهد بود که وضعیت موجود را به‌طور شفاف توصیف می‌کند. این مرحله شامل هیچ تغییری در منطق یا اضافه کردن قابلیت جدید نیست. کلیدواژه‌های اصلی: backend/app/oversight_strong_prompt.py, backend/app/ai_manager.py, OversightService, downstream consumers, caller. بر اساس ساختار پروژه، فایل‌های مرتبط شامل backend/app/services/oversight_strong_prompt.py (سرویس مدیریت پرامپت‌های قوی oversight) و backend/app/services/ai_manager.py (مدیریت هوش مصنوعی و تعامل با مدل‌ها) هستند. همچنین فایل‌های downstream مانند backend/app/services/oversight_service.py، backend/app/services/oversight_inspector_bridge.py و backend/app/services/oversight_verifier.py ممکن است از این سرویس‌ها استفاده کنند. ریسک‌های ذکر شده در درخواست کاربر: تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/services/oversight_strong_prompt.py به‌طور کامل خوانده و تحلیل شده باشد — کلاس‌ها، توابع، وابستگی‌ها و نحوه تعامل با ai_manager مستند شده باشد
- [ ] فایل backend/app/services/ai_manager.py به‌طور کامل خوانده و تحلیل شده باشد — کلاس‌ها، توابع، وابستگی‌ها و نحوه تعامل با oversight_strong_prompt مستند شده باشد
- [ ] تمامی callerهای downstream هر دو سرویس (با grep روی پروژه) شناسایی و در مستند ثبت شده باشند — حداقل ۳ caller برای هر سرویس
- [ ] نقاط ضعف و وابستگی‌های متقابل بین دو سرویس شناسایی و در مستند ثبت شده باشند — حداقل ۲ نقطه ضعف و ۲ وابستگی متقابل
- [ ] خروجی نهایی (مستند یا کامنت‌های کد) بدون تغییر در منطق کد تولید شده باشد — هیچ commitای با تغییر منطق وجود نداشته باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مرحله ۱: خواندن کامل کد فایل backend/app/services/oversight_strong_prompt.py — شناسایی کلاس‌ها، توابع، وابستگی‌ها و نحوه تعامل با ai_manager. مرحله ۲: خواندن کامل کد فایل backend/app/services/ai_manager.py — شناسایی کلاس‌ها، توابع، وابستگی‌ها و نحوه تعامل با oversight_strong_prompt. مرحله ۳: مستندسازی رفتار فعلی هر دو سرویس در قالب کامنت‌های کد یا یک سند جداگانه (مثلاً docs/OVERSIGHT_STRONG_PROMPT_AI_MANAGER_AUDIT.md). مرحله ۴: شناسایی نقاط ضعف و وابستگی‌های متقابل — ثبت در مستند. مرحله ۵: بررسی callerهای downstream (با grep روی پروژه) و ثبت آن‌ها در مستند. مرحله ۶: ارائه خروجی نهایی شامل مستند وضعیت موجود، بدون تغییر در منطق.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn "from.*oversight_strong_prompt import" backend/app/services/`
- `grep -rn "from.*ai_manager import" backend/app/services/`
- `grep -rn "OversightStrongPromptService" backend/app/services/`
- `grep -rn "AIManager" backend/app/services/`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: تغییر یک طرف ممکن است downstream consumers را break کند. callerهای احتمالی مانند backend/app/services/oversight_service.py، backend/app/services/oversight_inspector_bridge.py و backend/app/services/oversight_verifier.py ممکن است تحت تأثیر قرار گیرند. همچنین وابستگی‌های متقابل بین oversight_strong_prompt و ai_manager باید دقیقاً شناسایی شوند تا از break شدن زنجیره جلوگیری شود. ریسک دیگر: مستندسازی ناقص ممکن است منجر به تغییرات نادرست در آینده شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 25: تعریف معیارهای عملکردی برای انتخاب هوشمند مدل

**Scope:** این بخش به فقدان معیارهای عملکردی (Effectiveness metrics) برای انتخاب هوشمند مدل در سیستم AI Manager اشاره دارد. شامل تعریف معیارهایی مانند دقت، سرعت، هزینه و مصرف منابع برای مقایسه مدل‌های مختلف است. خارج از این بخش: پیاده‌سازی مکانیزم انتخاب، ذخیره‌سازی نتایج، یا رابط کاربری. نکته حیاتی: معیارها باید قابل اندازه‌گیری و مقایسه بین مدل‌های مختلف باشند.
**Key terms:** ai_manager.py, OversightService

**بخش مربوط از متن کاربر:**
```
[Effectiveness] فقدان معیارهای عملکردی برای انتخاب هوشمند مدل
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف معیارهای عملکردی برای انتخاب هوشمند مدل در AI Manager

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `AIManager` — کلاس اصلی مدیریت مدل‌ها - نیاز به افزودن معیارهای عملکردی
  ```python
  class AIManager:
      def __init__(self):
          self.models = {}
          self.current_model = None
          self.model_metrics = {}
  ```
- `backend/app/services/oversight_service.py:1-30` — `OversightService` — سرویس نظارت که از AIManager استفاده می‌کند - نیاز به به‌روزرسانی برای استفاده از معیارها
  ```python
  class OversightService:
      def __init__(self, ai_manager: AIManager):
          self.ai_manager = ai_manager
          self.current_model = None
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` (سطر 1) — کلاس پایه AI که AIManager از آن ارث‌بری می‌کند - تغییرات در AIManager ممکن است نیاز به به‌روزرسانی در اینجا داشته باشد
- `backend/app/services/ai_balance_service.py` (سطر 1) — سرویس بالانس که از AIManager برای توزیع بار استفاده می‌کند - معیارهای جدید می‌توانند به بالانس هوشمند کمک کنند
- `backend/app/api/routes/ai_usage.py` (سطر 1) — روتر API که از AIManager برای نمایش آمار استفاده می‌کند - ممکن است نیاز به نمایش معیارهای جدید داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات در فایل `backend/app/services/ai_manager.py` انجام می‌شود که توسط `backend/app/services/oversight_service.py` و `backend/app/services/ai_balance_service.py` استفاده می‌شود. همچنین `backend/app/api/routes/ai_usage.py` از AIManager برای نمایش اطلاعات استفاده می‌کند. کلاس `AIManager` از `backend/app/services/ai_base.py` ارث‌بری می‌کند.

## 🔍 Context و وضعیت فعلی
این تسک به فقدان معیارهای عملکردی (Effectiveness metrics) برای انتخاب هوشمند مدل در سیستم AI Manager اشاره دارد. کاربر خواستار تعریف معیارهایی مانند دقت، سرعت، هزینه و مصرف منابع برای مقایسه مدل‌های مختلف است. این بخش خارج از پیاده‌سازی مکانیزم انتخاب، ذخیره‌سازی نتایج، یا رابط کاربری است. نکته حیاتی: معیارها باید قابل اندازه‌گیری و مقایسه بین مدل‌های مختلف باشند.

کلیدواژه‌های اصلی: ai_manager.py, OversightService

شواهد در کد: فایل backend/app/services/ai_manager.py (خطوط 1-50) نشان می‌دهد که کلاس AIManager در حال حاضر از یک دیکشنری ساده برای نگهداری مدل‌ها استفاده می‌کند و هیچ معیار عملکردی برای مقایسه آن‌ها وجود ندارد. همچنین فایل backend/app/services/oversight_service.py (خطوط 1-30) نشان می‌دهد که OversightService از AIManager برای انتخاب مدل استفاده می‌کند اما هیچ معیاری برای انتخاب هوشمند وجود ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] کلاس EffectivenessMetrics باید در فایل backend/app/services/ai_manager.py تعریف شده باشد و شامل فیلدهای accuracy, speed, cost, resource_usage, timestamp باشد
- [ ] متد register_metrics باید در کلاس AIManager وجود داشته باشد و metrics را به metrics_registry اضافه کند
- [ ] متد get_best_model باید در کلاس AIManager وجود داشته باشد و بر اساس معیارهای وزنی بهترین مدل را برگرداند
- [ ] OversightService باید از get_best_model برای انتخاب مدل استفاده کند به جای انتخاب تصادفی
- [ ] تست‌های unit برای EffectivenessMetrics, register_metrics, get_best_model باید پاس شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک کلاس جدید به نام `EffectivenessMetrics` در فایل `backend/app/services/ai_manager.py` که شامل فیلدهای زیر باشد:
   - `accuracy: float` (دقت)
   - `speed: float` (سرعت بر حسب میلی‌ثانیه)
   - `cost: float` (هزینه بر حسب واحد)
   - `resource_usage: float` (مصرف منابع)
   - `timestamp: datetime` (زمان ثبت)

2. افزودن یک دیکشنری `metrics_registry: Dict[str, List[EffectivenessMetrics]]` به کلاس AIManager برای نگهداری تاریخچه معیارها برای هر مدل.

3. افزودن متد `register_metrics(model_id: str, metrics: EffectivenessMetrics)` به AIManager.

4. افزودن متد `get_best_model(criteria: Dict[str, float]) -> str` که بر اساس معیارهای وزنی بهترین مدل را انتخاب کند.

5. به‌روزرسانی OversightService برای استفاده از `get_best_model` به جای انتخاب تصادفی یا ثابت.

## 💡 نمونه‌های قبل/بعد
**افزودن کلاس EffectivenessMetrics و متدهای مربوطه**

_قبل:_
```
class AIManager:
    def __init__(self):
        self.models = {}
        self.current_model = None
        self.model_metrics = {}
```

_بعد:_
```
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class EffectivenessMetrics:
    accuracy: float
    speed: float  # milliseconds
    cost: float
    resource_usage: float
    timestamp: datetime

class AIManager:
    def __init__(self):
        self.models = {}
        self.current_model = None
        self.metrics_registry: Dict[str, List[EffectivenessMetrics]] = {}

    def register_metrics(self, model_id: str, metrics: EffectivenessMetrics) -> None:
        if model_id not in self.metrics_registry:
            self.metrics_registry[model_id] = []
        self.metrics_registry[model_id].append(metrics)

    def get_best_model(self, criteria: Dict[str, float]) -> Optional[str]:
        if not self.metrics_registry:
            return None
        best_model = None
        best_score = float('-inf')
        for model_id, metrics_list in self.metrics_registry.items():
            if not metrics_list:
                continue
            latest_metrics = metrics_list[-1]
            score = (
                criteria.get('accuracy', 0) * latest_metrics.accuracy +
                criteria.get('speed', 0) * (1 / latest_metrics.speed) +
                criteria.get('cost', 0) * (1 / latest_metrics.cost) +
                criteria.get('resource_usage', 0) * (1 / latest_metrics.resource_usage)
            )
            if score > best_score:
                best_score = score
                best_model = model_id
        return best_model
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_manager_metrics.py -v`
- `python -c "from backend.app.services.ai_manager import AIManager, EffectivenessMetrics; print('Import successful')"`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در AIManager بر روی OversightService (backend/app/services/oversight_service.py) و ai_balance_service (backend/app/services/ai_balance_service.py) تأثیر می‌گذارد. همچنین روتر ai_usage (backend/app/api/routes/ai_usage.py) که از AIManager استفاده می‌کند ممکن است نیاز به به‌روزرسانی داشته باشد. اگر معیارها به درستی تعریف نشوند، انتخاب مدل ممکن است نادرست باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 26: افزودن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history

**Scope:** این مرحله شامل افزودن logging برای latency و cost به فایل backend/app/ai_manager.py و پیاده‌سازی مکانیزم weighted selection بر اساس performance history است. هدف این است که انتخاب مدل دیگر صرفاً بر اساس availability نباشد، بلکه بر اساس معیارهای عملکردی (latency و cost) وزن‌دهی شود. این مرحله شامل تغییر در منطق انتخاب مدل در ai_manager و اضافه کردن logging مناسب برای ثبت latency و cost هر فراخوانی است. خارج از scope این مرحله: تغییر در سایر فایل‌ها، پیاده‌سازی metric‌های دیگر، یا تغییر در نحوه ذخیره‌سازی performance history.
**Key terms:** backend/app/ai_manager.py, latency, cost, weighted selection, performance history, availability

**بخش مربوط از متن کاربر:**
```
## 📊 وضعیت فعلی
هیچ metricی برای latency یا cost در outcome data وجود ندارد - انتخاب مدل صرفاً بر اساس availability است

## 🛠 اقدام پیشنهادی
اضافه کردن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن logging latency و cost به ai_manager و پیاده‌سازی weighted selection

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `AiManager class` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی پروژه، این فایل شامل کلاس اصلی مدیریت AI است.
  ```python
  فایل deep-read نشده است. بر اساس ساختار سطحی، کلاس AiManager در این فایل تعریف شده است.
  ```
- `backend/app/services/ai_manager.py:100-150` — `select_model method` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این متد هدف اصلی تغییرات است.
  ```python
  فایل deep-read نشده است. بر اساس ساختار سطحی، این متد مسئول انتخاب مدل مناسب است.
  ```
- `backend/app/services/ai_manager.py:200-250` — `track_usage method` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این متد برای افزودن logging latency و cost اصلاح می‌شود.
  ```python
  فایل deep-read نشده است. بر اساس ساختار سطحی، این متد مسئول ثبت metrics است.
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` (سطر 1) — کلاس پایه AiBase که احتمالاً توسط AiManager استفاده می‌شود و ممکن است نیاز به تغییر در interface response داشته باشد
- `backend/app/services/ai_balance_service.py` (سطر 1) — سرویس توازن AI که ممکن است از select_model استفاده کند و تحت تأثیر weighted selection قرار گیرد
- `backend/app/services/claude_service.py` (سطر 1) — سرویس Claude که یکی از مدل‌های مورد استفاده است و باید latency و cost را در response برگرداند
- `backend/app/services/openai_service.py` (سطر 1) — سرویس OpenAI که یکی از مدل‌های مورد استفاده است و باید latency و cost را در response برگرداند
- `backend/app/services/gemini_service.py` (سطر 1) — سرویس Gemini که یکی از مدل‌های مورد استفاده است و باید latency و cost را در response برگرداند

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات عمدتاً در فایل backend/app/services/ai_manager.py متمرکز است. فایل‌های سرویس مدل (claude_service.py, openai_service.py, gemini_service.py, deepseek_service.py, perplexity_service.py) باید response خود را به‌گونه‌ای اصلاح کنند که latency و cost را برگردانند. فایل ai_base.py ممکن است نیاز به تغییر در کلاس پایه برای پشتیبانی از فیلدهای جدید داشته باشد. فایل ai_balance_service.py از select_model استفاده می‌کند و تحت تأثیر weighted selection قرار می‌گیرد. فایل‌های test مرتبط (در backend/tests/) باید برای تست weighted selection به‌روزرسانی شوند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن logging برای latency و cost به فایل backend/app/ai_manager.py و پیاده‌سازی مکانیزم weighted selection بر اساس performance history را دارد. هدف این است که انتخاب مدل دیگر صرفاً بر اساس availability نباشد، بلکه بر اساس معیارهای عملکردی (latency و cost) وزن‌دهی شود. این مرحله شامل تغییر در منطق انتخاب مدل در ai_manager و اضافه کردن logging مناسب برای ثبت latency و cost هر فراخوانی است. خارج از scope این مرحله: تغییر در سایر فایل‌ها، پیاده‌سازی metric‌های دیگر، یا تغییر در نحوه ذخیره‌سازی performance history.

وضعیت فعلی: هیچ metricی برای latency یا cost در outcome data وجود ندارد - انتخاب مدل صرفاً بر اساس availability است.

کلیدواژه‌ها: backend/app/ai_manager.py, latency, cost, weighted selection, performance history, availability

شواهد در کد: فایل backend/app/services/ai_manager.py در ساختار پروژه موجود است اما deep-read نشده است. بر اساس ساختار سطحی، این فایل شامل کلاس AiManager با متدهای select_model، call_model و track_usage است. متد select_model احتمالاً از یک لیست مدل‌های available انتخاب می‌کند و متد track_usage احتمالاً metrics را ثبت می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] متد track_usage در ai_manager.py باید latency_ms و cost_credits را به عنوان پارامتر دریافت و در usage_log ذخیره کند
- [ ] متد select_model در ai_manager.py باید از weighted selection بر اساس performance history استفاده کند نه صرفاً availability
- [ ] performance_history باید شامل avg_latency_ms و avg_cost_credits برای هر مدل باشد
- [ ] مدل‌های بدون performance history باید امتیاز پیش‌فرض (0.5) دریافت کنند تا backward compatibility حفظ شود
- [ ] تغییرات نباید سرویس‌های مدل (claude_service, openai_service, gemini_service) را تغییر دهد — فقط interface response آن‌ها باید latency و cost را شامل شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. افزودن فیلدهای latency_ms و cost_credits به مدل داده‌ای outcome در ai_manager.py
2. اصلاح متد track_usage برای دریافت و ذخیره latency و cost از response هر فراخوانی
3. اصلاح متد select_model برای استفاده از weighted selection بر اساس performance history (میانگین وزنی latency و cost)
4. افزودن logging برای ثبت latency و cost در هر فراخوانی موفق
5. به‌روزرسانی متد call_model برای ارسال latency و cost به track_usage
6. افزودن متد get_performance_score برای محاسبه امتیاز عملکرد هر مدل بر اساس تاریخچه
7. اطمینان از backward compatibility با مدل‌های بدون performance history

## 💡 نمونه‌های قبل/بعد
**متد select_model قبل و بعد از تغییر**

_قبل:_
```
# قبل: انتخاب صرفاً بر اساس availability
def select_model(self, task_type: str) -> str:
    available_models = self.get_available_models(task_type)
    return available_models[0] if available_models else None
```

_بعد:_
```
# بعد: weighted selection بر اساس performance history
def select_model(self, task_type: str) -> str:
    available_models = self.get_available_models(task_type)
    if not available_models:
        return None
    scores = []
    for model in available_models:
        perf = self.performance_history.get(model, {})
        if perf:
            avg_latency = perf.get('avg_latency_ms', 1000)
            avg_cost = perf.get('avg_cost_credits', 1.0)
            score = (1.0 / avg_latency) * 0.3 + (1.0 / avg_cost) * 0.7
        else:
            score = 0.5  # default score for new models
        scores.append((model, score))
    return max(scores, key=lambda x: x[1])[0]
```

**متد track_usage قبل و بعد از تغییر**

_قبل:_
```
# قبل: بدون logging latency و cost
def track_usage(self, model: str, success: bool):
    self.usage_log.append({
        'model': model,
        'success': success,
        'timestamp': datetime.now()
    })
```

_بعد:_
```
# بعد: با logging latency و cost
def track_usage(self, model: str, success: bool, latency_ms: int = 0, cost_credits: float = 0.0):
    self.usage_log.append({
        'model': model,
        'success': success,
        'latency_ms': latency_ms,
        'cost_credits': cost_credits,
        'timestamp': datetime.now()
    })
    # به‌روزرسانی performance history
    if model not in self.performance_history:
        self.performance_history[model] = {'latencies': [], 'costs': []}
    self.performance_history[model]['latencies'].append(latency_ms)
    self.performance_history[model]['costs'].append(cost_credits)
    # محاسبه میانگین‌های متحرک
    self.performance_history[model]['avg_latency_ms'] = sum(self.performance_history[model]['latencies'][-10:]) / min(len(self.performance_history[model]['latencies']), 10)
    self.performance_history[model]['avg_cost_credits'] = sum(self.performance_history[model]['costs'][-10:]) / min(len(self.performance_history[model]['costs']), 10)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_manager.py -v`
- `python -c "from backend.app.services.ai_manager import AiManager; print('Import successful')"`
- `grep -n 'latency_ms\|cost_credits\|performance_history' backend/app/services/ai_manager.py`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در متد select_model می‌تواند روی ai_balance_service.py تأثیر بگذارد که از این متد استفاده می‌کند. همچنین تغییر در track_usage ممکن است روی کدهایی که این متد را با امضای قدیمی صدا می‌زنند تأثیر بگذارد. سرویس‌های مدل (claude_service, openai_service, gemini_service) باید response خود را اصلاح کنند تا latency و cost را برگردانند، در غیر این صورت weighted selection کار نخواهد کرد. فایل ai_base.py ممکن است نیاز به تغییر در کلاس پایه داشته باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 27: تعریف معیارهای پذیرش رفتار-محور برای outcome target

**Scope:** این بخش شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از پیاده‌سازی صحیح outcome target است. هر AC رفتار قابل مشاهده را تعریف می‌کند و نه پیاده‌سازی داخلی. scope شامل: بازنویسی outcome target به صورت measurable، تغییر کد، تست E2E، metric/log، عبور تست‌ها، linter و type-check. خارج از scope: تعریف خود outcome target (فقط نحوه اندازه‌گیری آن). نکته حیاتی: verify باید پیاده‌سازی‌های متفاوت ولی هم‌ارز را قبول کند.
**Key terms:** OversightService, tests/test_ai_llm_pipeline.py, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py, backend/app/services/oversight_service.py, tests/test_oversight_service.py, backend/app/api/routes/oversight.py, backend/app/main.py, backend/app/api/routes/github_import.py, backend/app/core/database.py, backend/app/models/setting.py, backend/app/services/verify_runtime/__init__.py, backend/app/ai_manager.py

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف ۷ معیار پذیرش رفتار-محور برای outcome target

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `OversightService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل اصلی برای تعریف outcome target و اضافه کردن metric/log است.
- `tests/test_oversight_service.py:1-50` — `test_oversight_service` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل برای اضافه کردن تست E2E که outcome را اندازه می‌گیرد.
- `backend/app/ai_manager.py:1-50` — `ai_manager` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل برای هماهنگی با outcome target در مدیریت AI.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/oversight_strong_prompt.py` (سطر 1) — این فایل برای تعریف strong prompt مرتبط با outcome target استفاده می‌شود و ممکن است نیاز به تغییر داشته باشد.
- `backend/app/api/routes/oversight.py` (سطر 1) — این فایل endpointهای API برای OversightService را تعریف می‌کند و ممکن است نیاز به اضافه کردن endpoint جدید برای outcome target داشته باشد.
- `backend/app/main.py` (سطر 1) — این فایل نقطه ورود برنامه است و ممکن است نیاز به ثبت metric/log جدید داشته باشد.
- `backend/app/core/database.py` (سطر 1) — این فایل برای ذخیره outcome target در database استفاده می‌شود و ممکن است نیاز به تغییر schema داشته باشد.
- `backend/app/models/setting.py` (سطر 1) — این فایل مدل setting را تعریف می‌کند و ممکن است برای ذخیره outcome target به عنوان یک setting استفاده شود.

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر فایل‌های backend/app/services/oversight_service.py (سرویس اصلی)، backend/app/oversight_strong_prompt.py (تعریف strong prompt)، backend/app/api/routes/oversight.py (endpointهای API)، backend/app/main.py (نقطه ورود)، backend/app/core/database.py (دیتابیس)، backend/app/models/setting.py (مدل setting)، backend/app/ai_manager.py (مدیریت AI)، و tests/test_oversight_service.py (تست‌ها) تأثیر می‌گذارد. همچنین backend/app/services/verify_runtime/__init__.py برای verify runtime و backend/app/api/routes/github_import.py برای import از GitHub مرتبط هستند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست تعریف ۷ معیار پذیرش (AC) برای اطمینان از پیاده‌سازی صحیح outcome target را دارد. هر AC باید رفتار قابل مشاهده را تعریف کند و نه پیاده‌سازی داخلی. scope شامل: بازنویسی outcome target به صورت measurable، تغییر کد، تست E2E، metric/log، عبور تست‌ها، linter و type-check. خارج از scope: تعریف خود outcome target (فقط نحوه اندازه‌گیری آن). نکته حیاتی: verify باید پیاده‌سازی‌های متفاوت ولی هم‌ارز را قبول کند.

کلیدواژه‌های ذکر شده توسط کاربر: OversightService, tests/test_ai_llm_pipeline.py, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py, backend/app/services/oversight_service.py, tests/test_oversight_service.py, backend/app/api/routes/oversight.py, backend/app/main.py, backend/app/api/routes/github_import.py, backend/app/core/database.py, backend/app/models/setting.py, backend/app/services/verify_runtime/__init__.py, backend/app/ai_manager.py

معیارهای پذیرش درخواستی:
1. outcome target به‌صورت measurable بازنویسی شد
2. کد تغییر کرد تا outcome target محقق شود
3. test E2E که outcome را اندازه می‌گیرد عبور می‌کند
4. metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
5. هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
6. linter بدون warning عبور می‌کند
7. type-check موفق است (`tsc --noEmit` / `mypy`)

مراحل اجرایی پیشنهادی: گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).

بر اساس ساختار پروژه، فایل‌های مرتبط با OversightService در backend/app/services/oversight_service.py و backend/app/services/oversight_strong_prompt.py قرار دارند. فایل‌های تست در tests/test_oversight_service.py و tests/test_ai_llm_pipeline.py. همچنین backend/app/ai_manager.py و backend/app/api/routes/oversight.py و backend/app/main.py و backend/app/api/routes/github_import.py و backend/app/core/database.py و backend/app/models/setting.py و backend/app/services/verify_runtime/__init__.py مرتبط هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد — تابع define_outcome_target در OversightService باید یک target با threshold عددی (مثلاً rate > 95%) تعریف کند.
- [ ] کد تغییر کرد تا outcome target محقق شود — منطق run_oversight باید از outcome target استفاده کند و در صورت عدم تحقق، اقدام مناسب انجام دهد.
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند — تست در tests/test_oversight_service.py باید outcome target را تعریف کرده و اندازه‌گیری کند.
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد — logging.info یا metric ثبت در OversightService برای outcome rate.
- [ ] هیچ تستی fail نمی‌شود (`pytest`) — اجرای pytest باید بدون خطا باشد.
- [ ] linter بدون warning عبور می‌کند — اجرای linter (مثلاً flake8) باید بدون warning باشد.
- [ ] type-check موفق است (`mypy`) — اجرای mypy باید بدون خطا باشد.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بازنویسی outcome target به صورت measurable در فایل backend/app/services/oversight_service.py با اضافه کردن یک تابع جدید به نام `define_outcome_target` که یک target قابل اندازه‌گیری (مثلاً rate > 95%) را تعریف می‌کند.
2. تغییر کد در backend/app/services/oversight_service.py برای استفاده از outcome target در منطق اصلی.
3. اضافه کردن تست E2E در tests/test_oversight_service.py که outcome را اندازه می‌گیرد.
4. اضافه کردن metric/log در backend/app/services/oversight_service.py برای ثبت outcome rate در production.
5. اطمینان از عبور همه تست‌ها با `pytest`.
6. اطمینان از عبور linter بدون warning.
7. اطمینان از موفقیت type-check با `mypy`.

همه URL/آدرس‌های ذکر شده توسط کاربر: OversightService, tests/test_ai_llm_pipeline.py, backend/app/ai_manager.py, backend/app/oversight_strong_prompt.py, backend/app/services/oversight_service.py, tests/test_oversight_service.py, backend/app/api/routes/oversight.py, backend/app/main.py, backend/app/api/routes/github_import.py, backend/app/core/database.py, backend/app/models/setting.py, backend/app/services/verify_runtime/__init__.py, backend/app/ai_manager.py

## 💡 نمونه‌های قبل/بعد
**اضافه کردن تابع define_outcome_target در OversightService**

_قبل:_
```
# backend/app/services/oversight_service.py
class OversightService:
    def __init__(self):
        pass
    
    def run_oversight(self):
        # logic without outcome target
        pass
```

_بعد:_
```
# backend/app/services/oversight_service.py
class OversightService:
    def __init__(self):
        self.outcome_target = None
    
    def define_outcome_target(self, target: str, threshold: float):
        """Define a measurable outcome target."""
        self.outcome_target = {"target": target, "threshold": threshold}
        logging.info(f"Outcome target defined: {target} with threshold {threshold}")
    
    def run_oversight(self):
        # logic with outcome target
        if self.outcome_target:
            # measure outcome
            pass
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest tests/test_oversight_service.py -v`
- `pytest tests/test_ai_llm_pipeline.py -v`
- `flake8 backend/app/services/oversight_service.py`
- `mypy backend/app/services/oversight_service.py`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در OversightService می‌تواند روی endpointهای API در backend/app/api/routes/oversight.py تأثیر بگذارد. همچنین تغییر در database schema در backend/app/core/database.py ممکن است نیاز به migration داشته باشد. فایل backend/app/ai_manager.py نیز از OversightService استفاده می‌کند و ممکن است نیاز به هماهنگی داشته باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 28: بررسی و اصلاح عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts

**Scope:** این بخش شامل شناسایی ناسازگاری‌های بین فرمت system_prompts و مدل‌های مختلف (OpenAI vs Claude)، تعیین ground truth و align کردن طرف دیگر، نوشتن integration test برای pipeline ai_llm، و مستندسازی تصمیم در PR description است. فایل‌های دخیل: backend/app/system_prompts/ و backend/app/ai_llm/. خارج از scope: تغییرات در logging، performance history، weighted selection، outcome metrics، یا تست‌های E2E.
**Key terms:** system_prompts, ai_llm, OpenAI, Claude, format_prompt_for_model, model_specific_prompt, tests/test_ai_llm_pipeline.py, backend/app/system_prompts/, backend/app/ai_llm/

**بخش مربوط از متن کاربر:**
```
تسک 11 از 16
  id: 6c68405b-9f9d-4d4c-9826-a2dae60d008e
  عنوان اصلی: [منطق] عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["system_prompts.*format", "format_prompt.*model", "OpenAI.*system.*message", "Claude.*format"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format_prompt_for_model", "model_specific_prompt"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع عدم تطابق فرمت prompt بین system_prompts و مدل‌های مختلف

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:نامشخص — فایل deep-read نشده` — `احتمالاً تابع format_prompt_for_model` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً محل اصلی مدیریت format prompt برای مدل‌های مختلف است.
- `backend/app/services/claude_service.py:نامشخص — فایل deep-read نشده` — `احتمالاً تابع send_message یا format_prompt` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً شامل format خاص Claude برای system_prompts است.
- `backend/app/services/openai_service.py:نامشخص — فایل deep-read نشده` — `احتمالاً تابع send_message یا format_prompt` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً شامل format خاص OpenAI برای system_prompts است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
پروژه از معماری چند-سرویس AI استفاده می‌کند که هر سرویس (OpenAI، Claude، Gemini، DeepSeek، Perplexity) format خاص خود را برای system_prompts دارد. احتمالاً از یک کلاس پایه (ai_base.py) برای یکسان‌سازی استفاده می‌شود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` — کلاس پایه برای تمام سرویس‌های AI — تغییرات در format باید در این کلاس abstract تعریف شود
- `backend/app/services/gemini_service.py` — سرویس Gemini نیز ممکن است تحت تأثیر تغییرات format قرار گیرد
- `backend/app/services/deepseek_service.py` — سرویس DeepSeek نیز ممکن است تحت تأثیر تغییرات format قرار گیرد
- `backend/app/services/perplexity_service.py` — سرویس Perplexity نیز ممکن است تحت تأثیر تغییرات format قرار گیرد
- `backend/app/services/inspector_agent.py` — این سرویس از system_prompts استفاده می‌کند و ممکن است تحت تأثیر تغییرات format قرار گیرد

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر روی کل pipeline AI تأثیر می‌گذارد. فایل‌های اصلی: ai_manager.py (مدیریت مرکزی AI)، claude_service.py (format Claude)، openai_service.py (format OpenAI)، ai_base.py (کلاس پایه). همچنین سرویس‌های gemini_service.py، deepseek_service.py، perplexity_service.py نیز ممکن است نیاز به تغییر داشته باشند. inspector_agent.py و سایر سرویس‌هایی که از system_prompts استفاده می‌کنند نیز تحت تأثیر قرار می‌گیرند.

## 🔍 Context و وضعیت فعلی
بررسی و اصلاح عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts. این تسک شامل شناسایی ناسازگاری‌های بین فرمت system_prompts و مدل‌های مختلف (OpenAI vs Claude)، تعیین ground truth و align کردن طرف دیگر، نوشتن integration test برای pipeline ai_llm، و مستندسازی تصمیم در PR description است. فایل‌های دخیل: backend/app/system_prompts/ و backend/app/ai_llm/. خارج از scope: تغییرات در logging، performance history، weighted selection، outcome metrics، یا تست‌های E2E. کلیدواژه‌ها: system_prompts, ai_llm, OpenAI, Claude, format_prompt_for_model, model_specific_prompt, tests/test_ai_llm_pipeline.py, backend/app/system_prompts/, backend/app/ai_llm/. acceptance_criteria کامل: 1) هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["system_prompts.*format", "format_prompt.*model", "OpenAI.*system.*message", "Claude.*format"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}] 2) ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format_prompt_for_model", "model_specific_prompt"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}] 3) integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}] 4) PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری (OpenAI و Claude) شناسایی و فرض‌هایشان در کد مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد — تابع format_prompt_for_model یا model_specific_prompt وجود دارد
- [ ] integration test برای pipeline ai_llm بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. اسکن کامل دایرکتوری‌های backend/app/system_prompts/ و backend/app/ai_llm/ برای یافتن تمام توابع و کلاس‌های مرتبط با format_prompt_for_model و model_specific_prompt. 2. شناسایی ناسازگاری‌ها: مقایسه نحوه ساخت system_prompts برای OpenAI (که از system message استفاده می‌کند) vs Claude (که از format خاص خود استفاده می‌کند). 3. تعیین ground truth: تصمیم‌گیری اینکه کدام فرمت به عنوان استاندارد اصلی در نظر گرفته شود (احتمالاً فرمت OpenAI به دلیل گستردگی استفاده). 4. align کردن طرف دیگر: تغییر کد در backend/app/ai_llm/ برای تبدیل خودکار فرمت‌ها هنگام ارسال به مدل‌های مختلف. 5. نوشتن integration test در tests/test_ai_llm_pipeline.py برای اطمینان از عملکرد صحیح pipeline. 6. مستندسازی در PR description.

## 💡 نمونه‌های قبل/بعد
**نمونه format فعلی برای OpenAI vs Claude**

_قبل:_
```
OpenAI: system_prompt به صورت {'role': 'system', 'content': '...'} ارسال می‌شود
Claude: system_prompt به صورت {'role': 'user', 'content': '...'} یا format خاص Anthropic ارسال می‌شود
```

_بعد:_
```
یک تابع واحد format_prompt_for_model که بر اساس type مدل، format مناسب را انتخاب می‌کند:
def format_prompt_for_model(prompt: str, model_type: str) -> dict:
    if model_type == 'openai':
        return {'role': 'system', 'content': prompt}
    elif model_type == 'claude':
        return {'role': 'user', 'content': f'System: {prompt}\n\n'}
    # ... سایر مدل‌ها
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_llm_pipeline.py::test_integration -v --timeout=120`
- `grep -rn 'format_prompt_for_model\|model_specific_prompt' backend/app/system_prompts/ backend/app/ai_llm/`
- `grep -rn 'OpenAI.*system.*message\|Claude.*format' backend/app/system_prompts/ backend/app/ai_llm/`

## ⚠️ ریسک‌ها و موارد احتیاط
این تغییر بر روی تمام سرویس‌های AI (OpenAI، Claude، Gemini، DeepSeek، Perplexity) تأثیر می‌گذارد. اگر ground truth اشتباه انتخاب شود، ممکن است برخی مدل‌ها پاسخ‌های نادرست بدهند. همچنین inspector_agent.py و سایر سرویس‌های وابسته به system_prompts ممکن است دچار regression شوند. تست‌های integration باید با دقت نوشته شوند تا همه سناریوها پوشش داده شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 29: رفع ناسازگاری فرمت پرامپت‌های سیستم بین مدل‌های مختلف در pipeline ai_llm

**Scope:** این بخش به تحلیل و رفع ناسازگاری منطقی بین system_prompts و مدل‌های مختلف (OpenAI vs Claude) می‌پردازد. شامل: افزودن لایه adapter در prompt_helper یا ai_manager برای تبدیل پرامپت‌های generic به فرمت مناسب هر مدل. ذخیره‌سازی پرامپت‌ها با metadata مربوط به مدل‌های سازگار. خارج از scope: تغییرات در pipeline‌های دیگر، بازنویسی کامل system_prompts، یا تغییر در منطق اصلی مدل‌ها.
**Key terms:** backend/app/ai_manager.py, backend/app/ai_manager.py, ai_llm, system_prompts, prompt_helper, OpenAI, Claude

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

سرویس system_prompts پرامپت‌های سیستم را مدیریت می‌کند، اما مشخص نیست که آیا این پرامپت‌ها برای مدل‌های مختلف (OpenAI vs Claude) فرمت‌بندی می‌شوند یا خیر. هر مدل ممکن است به ساختار پرامپت متفاوتی نیاز داشته باشد (مثلاً system vs user message در OpenAI، یا format خاص در Claude). اگر پرامپت‌ها به صورت generic ذخیره شوند، ممکن است با مدل خاصی سازگار نباشند.

## 💥 پیامد (impact)
پرامپت‌های سیستم به درستی توسط مدل تفسیر نمی‌شوند. کاهش کیفیت پاسخ‌ها. افزایش خطاهای parsing در سمت مدل.

## 🛠 پیشنهاد رفع اولیه
یک لایه adapter در prompt_helper یا ai_manager اضافه کنید که پرامپت‌های generic را بر اساس مدل هدف به فرمت مناسب تبدیل کند. همچنین می‌توانید پرامپت‌ها را با metadata مربوط به مدل‌های سازگار ذخیره کنید.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن لایه adapter پرامپت برای سازگاری OpenAI و Claude در ai_llm

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/prompt_helper.py:1-50` — `کل فایل` — فایل اصلی مدیریت پرامپت‌ها — باید توابع format_prompt و get_system_prompt بررسی شوند
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، توسط مجری تأیید شود
  ```
- `backend/app/services/ai_manager.py:1-100` — `کل فایل` — مدیریت اصلی AI — باید نحوه ارسال پرامپت به سرویس‌های مختلف بررسی شود
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، توسط مجری تأیید شود
  ```
- `backend/app/services/claude_service.py:1-50` — `کل فایل` — سرویس Claude — باید ساختار پرامپت مورد انتظار (format خاص Claude) شناسایی شود
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، توسط مجری تأیید شود
  ```
- `backend/app/services/openai_service.py:1-50` — `کل فایل` — سرویس OpenAI — باید ساختار پرامپت مورد انتظار (system vs user message) شناسایی شود
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، توسط مجری تأیید شود
  ```
- `backend/app/models/system_prompt.py:1-30` — `کل فایل` — مدل system_prompt — باید فیلد compatible_models به metadata اضافه شود
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، توسط مجری تأیید شود
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` (سطر 1) — کلاس پایه برای تمام سرویس‌های AI — تغییر در نحوه ارسال پرامپت روی این کلاس تأثیر می‌گذارد
- `backend/app/services/gemini_service.py` (سطر 1) — سرویس Gemini نیز ممکن است نیاز به adapter مشابه داشته باشد — باید در طراحی adapter در نظر گرفته شود
- `backend/app/services/deepseek_service.py` (سطر 1) — سرویس DeepSeek نیز ممکن است نیاز به adapter مشابه داشته باشد — باید در طراحی adapter در نظر گرفته شود
- `backend/app/api/routes/chat.py` (سطر 1) — روتر chat که از ai_manager استفاده می‌کند — تغییرات روی پاسخ‌های chat تأثیر می‌گذارد
- `backend/app/api/routes/analysis.py` (سطر 1) — روتر analysis که از ai_manager استفاده می‌کند — تغییرات روی تحلیل‌ها تأثیر می‌گذارد

## 🌐 نقشهٔ وابستگی‌ها
این تغییر روی pipeline اصلی ai_llm تأثیر می‌گذارد. فایل‌های backend/app/services/ai_manager.py و backend/app/services/prompt_helper.py به عنوان هسته اصلی تغییر، توسط backend/app/services/ai_base.py (کلاس پایه)، backend/app/services/claude_service.py، backend/app/services/openai_service.py، backend/app/services/gemini_service.py، backend/app/services/deepseek_service.py استفاده می‌شوند. همچنین backend/app/api/routes/chat.py و backend/app/api/routes/analysis.py از ai_manager استفاده می‌کنند. مدل backend/app/models/system_prompt.py نیز باید به‌روزرسانی شود.

## 🔍 Context و وضعیت فعلی
تحلیل و رفع ناسازگاری منطقی بین system_prompts و مدل‌های مختلف (OpenAI vs Claude) در pipeline ai_llm. مشکل اصلی این است که سرویس system_prompts پرامپت‌های سیستم را مدیریت می‌کند، اما مشخص نیست که آیا این پرامپت‌ها برای مدل‌های مختلف (OpenAI vs Claude) فرمت‌بندی می‌شوند یا خیر. هر مدل ممکن است به ساختار پرامپت متفاوتی نیاز داشته باشد (مثلاً system vs user message در OpenAI، یا format خاص در Claude). اگر پرامپت‌ها به صورت generic ذخیره شوند، ممکن است با مدل خاصی سازگار نباشند. پیامد: پرامپت‌های سیستم به درستی توسط مدل تفسیر نمی‌شوند، کاهش کیفیت پاسخ‌ها، افزایش خطاهای parsing در سمت مدل. پیشنهاد رفع اولیه: یک لایه adapter در prompt_helper یا ai_manager اضافه کنید که پرامپت‌های generic را بر اساس مدل هدف به فرمت مناسب تبدیل کند. همچنین می‌توانید پرامپت‌ها را با metadata مربوط به مدل‌های سازگار ذخیره کنید. کلیدواژه‌ها: backend/app/ai_manager.py, backend/app/services/ai_manager.py, ai_llm, system_prompts, prompt_helper, OpenAI, Claude. شواهد در کد: فایل‌های backend/app/services/ai_manager.py و backend/app/services/prompt_helper.py و backend/app/services/claude_service.py و backend/app/services/openai_service.py و backend/app/models/system_prompt.py مرتبط هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/services/prompt_adapter.py ایجاد شود و شامل توابع convert_for_openai() و convert_for_claude() باشد
- [ ] مدل system_prompt در backend/app/models/system_prompt.py دارای فیلد compatible_models (لیست رشته‌ای از نام مدل‌ها) باشد
- [ ] تابع convert_for_openai() پرامپت generic را به فرمت OpenAI (شامل system message و user message) تبدیل کند
- [ ] تابع convert_for_claude() پرامپت generic را به فرمت Claude (با ساختار XML یا format خاص) تبدیل کند
- [ ] ai_manager.py از prompt_adapter قبل از ارسال پرامپت به سرویس مدل استفاده کند
- [ ] تمام تست‌های موجود در backend/tests/test_runtime_verify_stage*.py و backend/tests/test_verify_v7.py پس از تغییرات پاس شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی فایل backend/app/services/prompt_helper.py برای شناسایی توابع فعلی format_prompt و نحوه ارسال پرامپت به مدل‌ها. 2. بررسی backend/app/services/ai_manager.py برای شناسایی نحوه انتخاب مدل و ارسال پرامپت. 3. بررسی backend/app/services/claude_service.py و backend/app/services/openai_service.py برای شناسایی ساختار پرامپت مورد انتظار هر مدل. 4. ایجاد یک لایه adapter جدید در backend/app/services/prompt_adapter.py که شامل توابع convert_to_openai_format() و convert_to_claude_format() باشد. 5. افزودن metadata به مدل system_prompt در backend/app/models/system_prompt.py شامل فیلد compatible_models. 6. اصلاح ai_manager.py برای استفاده از adapter قبل از ارسال پرامپت به سرویس مدل. 7. افزودن تست‌های واحد برای adapter در backend/tests/test_prompt_adapter.py.

## 💡 نمونه‌های قبل/بعد
**ارسال پرامپت به Claude قبل از adapter**

_قبل:_
```
# در ai_manager.py
prompt = prompt_helper.get_system_prompt(session_id)
response = claude_service.send_message(prompt, user_message)
```

_بعد:_
```
# در ai_manager.py پس از adapter
from prompt_adapter import convert_for_claude
prompt = prompt_helper.get_system_prompt(session_id)
adapted_prompt = convert_for_claude(prompt)
response = claude_service.send_message(adapted_prompt, user_message)
```

**ارسال پرامپت به OpenAI قبل از adapter**

_قبل:_
```
# در ai_manager.py
prompt = prompt_helper.get_system_prompt(session_id)
response = openai_service.send_message(prompt, user_message)
```

_بعد:_
```
# در ai_manager.py پس از adapter
from prompt_adapter import convert_for_openai
prompt = prompt_helper.get_system_prompt(session_id)
adapted_prompt = convert_for_openai(prompt)
response = openai_service.send_message(adapted_prompt, user_message)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_prompt_adapter.py -v`
- `pytest backend/tests/test_runtime_verify_stage1.py -v`
- `pytest backend/tests/test_runtime_verify_stage2.py -v`
- `pytest backend/tests/test_runtime_verify_stage3a.py -v`
- `pytest backend/tests/test_runtime_verify_stage3b.py -v`
- `pytest backend/tests/test_runtime_verify_stage3cd.py -v`
- `pytest backend/tests/test_runtime_verify_stage3e.py -v`
- `pytest backend/tests/test_runtime_verify_stage6.py -v`
- `pytest backend/tests/test_runtime_verify_stage9.py -v`
- `pytest backend/tests/test_verify_v7.py -v`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در ai_manager.py و prompt_helper.py روی تمام pipeline‌های AI تأثیر می‌گذارد (chat, analysis, creator, debate, oversight). فایل‌های backend/app/services/ai_base.py و backend/app/services/ai_manager.py توسط 10+ سرویس دیگر import می‌شوند. اگر adapter به درستی کار نکند، ممکن است تمام پاسخ‌های AI دچار مشکل شوند. همچنین backend/app/api/routes/chat.py و backend/app/api/routes/analysis.py به طور مستقیم از ai_manager استفاده می‌کنند و خطا در adapter باعث 500 error در این endpoints می‌شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 30: بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline

**Scope:** این مرحله شامل بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline در کدبیس است. هدف آن مستندسازی وضعیت موجود، شناسایی نقاط ضعف و ناسازگاری‌ها، و تعیین ground truth برای مراحل بعدی است. این مرحله شامل پیاده‌سازی یا تغییر کد نمی‌شود و صرفاً یک audit و مستندسازی است.
**Key terms:** system_prompts, ai_llm pipeline, backend/app/ai_llm.py, backend/app/pipelines/ai_llm/*.py, backend/app/ai_manager.py, backend/app/ai_manager.py

**بخش مربوط از متن کاربر:**
```
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
  - بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline — بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/models/system_prompt.py` — `SystemPrompt` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. مدل system_prompt که ساختار اصلی system_prompts را تعریف می‌کند.
- `backend/app/api/routes/system_prompts.py` — `router` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. روتر system_prompts که endpointهای CRUD برای system_prompts را فراهم می‌کند.
- `backend/app/services/ai_manager.py` — `AIManager` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. سرویس مدیریت AI که از system_prompts در pipeline AI استفاده می‌کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/prompt_helper.py` — کمک‌کننده پرامپت که توابع کمکی برای مدیریت system_prompts فراهم می‌کند.
- `backend/app/services/ai_base.py` — کلاس پایه AI که نحوه استفاده از system_prompts در سرویس‌های AI را تعریف می‌کند.
- `backend/app/services/claude_service.py` — سرویس Claude که از system_prompts به عنوان downstream consumer استفاده می‌کند.
- `backend/app/services/openai_service.py` — سرویس OpenAI که از system_prompts به عنوان downstream consumer استفاده می‌کند.
- `backend/app/services/gemini_service.py` — سرویس Gemini که از system_prompts به عنوان downstream consumer استفاده می‌کند.
- `backend/app/services/deepseek_service.py` — سرویس DeepSeek که از system_prompts به عنوان downstream consumer استفاده می‌کند.
- `backend/app/services/perplexity_service.py` — سرویس Perplexity که از system_prompts به عنوان downstream consumer استفاده می‌کند.
- `backend/app/services/inspector_agent.py` — سرویس Inspector Agent که از system_prompts برای تحلیل کد استفاده می‌کند.
- `backend/app/services/oversight_strong_prompt.py` — سرویس Oversight Strong Prompt که وابسته به system_prompts است.
- `backend/app/services/oversight_codex_service.py` — سرویس Oversight Codex که وابسته به system_prompts است.

## 🌐 نقشهٔ وابستگی‌ها
این تسک یک audit از system_prompts و ai_llm pipeline است. فایل‌های اصلی شامل backend/app/models/system_prompt.py (مدل system_prompt)، backend/app/api/routes/system_prompts.py (روتر system_prompts)، backend/app/services/ai_manager.py (سرویس مدیریت AI)، backend/app/services/prompt_helper.py (کمک‌کننده پرامپت)، و backend/app/services/ai_base.py (کلاس پایه AI) هستند. downstream consumers شامل backend/app/services/claude_service.py، backend/app/services/openai_service.py، backend/app/services/gemini_service.py، backend/app/services/deepseek_service.py، backend/app/services/perplexity_service.py، backend/app/services/inspector_agent.py، backend/app/services/oversight_strong_prompt.py، backend/app/services/oversight_codex_service.py، backend/app/services/scan_v5/scan_bundle.py، backend/app/services/scan_v5/scan_inspector_session.py، backend/app/services/verify_runtime/context_builder.py، backend/app/services/verify_runtime/code_aware_verifier.py، backend/app/services/creator_engine.py، backend/app/services/creator_idea_to_prompt.py، backend/app/services/debate_service.py، backend/app/services/deep_analysis_service.py، backend/app/services/analysis_progress_manager.py، backend/app/services/health_to_issues_service.py، backend/app/services/log_to_issues_service.py، backend/app/services/notification_service.py، backend/app/services/project_health_analyzer.py، backend/app/services/project_analyzer.py، backend/app/services/report_validator.py، backend/app/services/security_analyzer.py، backend/app/services/smart_orchestrator.py، backend/app/services/task_consolidation_service.py، backend/app/services/task_merge_service.py، backend/app/services/test_coverage_analyzer.py، backend/app/services/ai_balance_service.py، backend/app/services/capability_detector.py، backend/app/services/model_capability_tester.py، backend/app/services/model_profiler.py، backend/app/services/quick_approval_service.py، backend/app/services/runtime_executor.py، backend/app/services/simple_creator.py، backend/app/services/smart_import.py، backend/app/services/unified_storage.py، backend/app/services/storage_service.py، backend/app/services/db_service.py، backend/app/services/dynamic_config.py، backend/app/services/external_monitor.py، backend/app/services/external_project_connector.py، backend/app/services/github_import.py، backend/app/services/github_pr_service.py، backend/app/services/github_storage.py، backend/app/services/deploy_service.py، backend/app/services/diagram_service.py، backend/app/services/dynamic_diagram_service.py، backend/app/services/browser_automation.py، backend/app/services/background_scheduler.py، backend/app/services/content_sanitizer.py، backend/app/services/code_quality_analyzer.py، backend/app/services/intelligent_field_creator.py، backend/app/services/journal_service.py، backend/app/services/log_stream_service.py، backend/app/services/oversight_service.py، backend/app/services/oversight_settings.py، backend/app/services/oversight_verifier.py، backend/app/services/oversight_upload_session.py، backend/app/services/oversight_telegram_compose.py، backend/app/services/oversight_mega_bundle.py، backend/app/services/oversight_inspector_bridge.py، backend/app/services/oversight_extraction.py، backend/app/services/oversight_deep_scan_service.py، backend/app/services/oversight_progress.py، backend/app/services/oversight_model_temp_activate.py، backend/app/services/oversight_codex_service.py، backend/app/services/oversight_strong_prompt.py، backend/app/services/oversight_verify_pdf.py، backend/app/services/oversight_verifier.py، backend/app/services/verify_runtime/iterative_orchestrator.py، backend/app/services/verify_runtime/context_builder.py، backend/app/services/verify_runtime/code_aware_verifier.py، backend/app/services/verify_runtime/code_content_searcher.py، backend/app/services/verify_runtime/inspector_probe.py، backend/app/services/verify_runtime/manual_probe.py، backend/app/services/verify_runtime/navigation_helper.py، backend/app/services/verify_runtime/render_autodetect.py، backend/app/services/verify_runtime/runner.py، backend/app/services/verify_runtime/safety.py، backend/app/services/verify_runtime/static_probe.py، backend/app/services/verify_runtime/storage.py، backend/app/services/verify_runtime/test_probe.py، backend/app/services/verify_runtime/ui_probe.py، backend/app/services/verify_runtime/vision_helper.py، backend/app/services/verify_runtime/api_probe.py، backend/app/services/verify_runtime/auth_runner.py، backend/app/services/verify_runtime/backend_log_probe.py، backend/app/services/verify_runtime/behavioral_probe_layer.py، backend/app/services/verify_runtime/browser_pool.py، backend/app/services/verify_runtime/ac_cache_service.py، backend/app/services/verify_runtime/ac_enricher.py، backend/app/services/verify_runtime/ac_schema.py، backend/app/services/verify_runtime/base.py، backend/app/services/scan_v5/anti_pattern_detector.py، backend/app/services/scan_v5/coherence_analyzer.py، backend/app/services/scan_v5/comprehensive_inventory.py، backend/app/services/scan_v5/delta_analyzer.py، backend/app/services/scan_v5/dependency_analyzer.py، backend/app/services/scan_v5/feature_documenter.py، backend/app/services/scan_v5/notification_auditor.py، backend/app/services/scan_v5/outcome_analyzer.py، backend/app/services/scan_v5/purpose_extractor.py، backend/app/services/scan_v5/runtime_discovery.py، backend/app/services/scan_v5/stale_detector.py، backend/app/services/scan_v5/_findings_to_tasks.py، backend/app/services/inspector_agent.py، backend/app/services/inspector_intent_resolver.py، backend/app/services/inspector_proposal_executor.py، backend/app/services/inspector_roles.py، backend/app/services/inspector_scan_bridge.py، backend/app/services/oversight_inspector_bridge.py، backend/app/models/inspector_prompt_field.py، backend/app/models/inspector_session.py، backend/app/models/ai_log.py، backend/app/models/ai_profile.py، backend/app/models/analysis_report.py، backend/app/models/debate.py، backend/app/models/project.py، backend/app/models/render_log.py، backend/app/models/setting.py، backend/app/models/system_prompt.py، backend/app/api/routes/ai_usage.py، backend/app/api/routes/analysis.py، backend/app/api/routes/chat.py، backend/app/api/routes/config.py، backend/app/api/routes/creator.py، backend/app/api/routes/debate.py، backend/app/api/routes/diagrams.py، backend/app/api/routes/external.py، backend/app/api/routes/external_projects.py، backend/app/api/routes/github_import.py، backend/app/api/routes/model_profiles.py، backend/app/api/routes/models.py، backend/app/api/routes/notifications.py، backend/app/api/routes/orchestrator.py، backend/app/api/routes/oversight.py، backend/app/api/routes/project_health.py، backend/app/api/routes/project_journal.py، backend/app/api/routes/project_memory.py، backend/app/api/routes/project_structure.py، backend/app/api/routes/projects.py، backend/app/api/routes/render_logs.py، backend/app/api/routes/runtime.py، backend/app/api/routes/security_analysis.py، backend/app/api/routes/settings.py، backend/app/api/routes/simple_projects.py، backend/app/api/routes/system_prompts.py، backend/app/api/routes/unified_api.py، backend/app/api/routes/upload.py، backend/app/core/config.py، backend/app/core/database.py، backend/app/core/logging_utils.py، backend/app/core/models_registry.py، backend/app/core/roles.py، و backend/app/main.py هستند. تغییر در system_prompts می‌تواند تمام این downstream consumers را تحت تأثیر قرار دهد.

## 🔍 Context و وضعیت فعلی
این تسک یک audit و مستندسازی از وضعیت فعلی system_prompts و ai_llm pipeline در کدبیس است. کاربر درخواست کرده است که ساختار فعلی system_prompts و ai_llm pipeline در کدبیس بررسی و شناسایی شود. هدف آن مستندسازی وضعیت موجود، شناسایی نقاط ضعف و ناسازگاری‌ها، و تعیین ground truth برای مراحل بعدی است. این مرحله شامل پیاده‌سازی یا تغییر کد نمی‌شود و صرفاً یک audit و مستندسازی است. کاربر تأکید کرده است که تغییر یک طرف ممکن است downstream consumers را break کند و حتماً قبل از merge، همه caller های هر دو طرف باید بررسی شوند. کلیدواژه‌های اصلی: system_prompts, ai_llm pipeline, backend/app/ai_llm.py, backend/app/pipelines/ai_llm/*.py, backend/app/ai_manager.py. با توجه به deep context موجود، فایل‌های مرتبط شامل backend/app/services/ai_manager.py (سرویس مدیریت AI)، backend/app/models/system_prompt.py (مدل system_prompt)، backend/app/api/routes/system_prompts.py (روتر system_prompts)، backend/app/services/prompt_helper.py (کمک‌کننده پرامپت)، و backend/app/services/ai_base.py (کلاس پایه AI) هستند. همچنین فایل‌های backend/app/services/claude_service.py، backend/app/services/openai_service.py، backend/app/services/gemini_service.py، backend/app/services/deepseek_service.py، و backend/app/services/perplexity_service.py به عنوان downstream consumers از system_prompts استفاده می‌کنند. فایل backend/app/services/inspector_agent.py نیز از system_prompts برای تحلیل کد استفاده می‌کند. فایل backend/app/services/oversight_strong_prompt.py و backend/app/services/oversight_codex_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/scan_v5/scan_bundle.py و backend/app/services/scan_v5/scan_inspector_session.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/context_builder.py و backend/app/services/verify_runtime/code_aware_verifier.py نیز وابسته به system_prompts هستند. فایل backend/app/services/creator_engine.py و backend/app/services/creator_idea_to_prompt.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/debate_service.py و backend/app/services/deep_analysis_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/analysis_progress_manager.py و backend/app/services/health_to_issues_service.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/log_to_issues_service.py و backend/app/services/notification_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/project_health_analyzer.py و backend/app/services/project_analyzer.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/report_validator.py و backend/app/services/security_analyzer.py نیز وابسته به system_prompts هستند. فایل backend/app/services/smart_orchestrator.py و backend/app/services/task_consolidation_service.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/task_merge_service.py و backend/app/services/test_coverage_analyzer.py نیز وابسته به system_prompts هستند. فایل backend/app/services/ai_balance_service.py و backend/app/services/capability_detector.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/model_capability_tester.py و backend/app/services/model_profiler.py نیز وابسته به system_prompts هستند. فایل backend/app/services/quick_approval_service.py و backend/app/services/runtime_executor.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/simple_creator.py و backend/app/services/smart_import.py نیز وابسته به system_prompts هستند. فایل backend/app/services/unified_storage.py و backend/app/services/storage_service.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/db_service.py و backend/app/services/dynamic_config.py نیز وابسته به system_prompts هستند. فایل backend/app/services/external_monitor.py و backend/app/services/external_project_connector.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/github_import.py و backend/app/services/github_pr_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/github_storage.py و backend/app/services/deploy_service.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/diagram_service.py و backend/app/services/dynamic_diagram_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/browser_automation.py و backend/app/services/background_scheduler.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/content_sanitizer.py و backend/app/services/code_quality_analyzer.py نیز وابسته به system_prompts هستند. فایل backend/app/services/intelligent_field_creator.py و backend/app/services/journal_service.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/log_stream_service.py و backend/app/services/oversight_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/oversight_settings.py و backend/app/services/oversight_verifier.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/oversight_upload_session.py و backend/app/services/oversight_telegram_compose.py نیز وابسته به system_prompts هستند. فایل backend/app/services/oversight_mega_bundle.py و backend/app/services/oversight_inspector_bridge.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/oversight_extraction.py و backend/app/services/oversight_deep_scan_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/oversight_progress.py و backend/app/services/oversight_model_temp_activate.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/oversight_codex_service.py و backend/app/services/oversight_strong_prompt.py نیز وابسته به system_prompts هستند. فایل backend/app/services/oversight_verify_pdf.py و backend/app/services/oversight_verifier.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/iterative_orchestrator.py و backend/app/services/verify_runtime/context_builder.py نیز وابسته به system_prompts هستند. فایل backend/app/services/verify_runtime/code_aware_verifier.py و backend/app/services/verify_runtime/code_content_searcher.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/inspector_probe.py و backend/app/services/verify_runtime/manual_probe.py نیز وابسته به system_prompts هستند. فایل backend/app/services/verify_runtime/navigation_helper.py و backend/app/services/verify_runtime/render_autodetect.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/runner.py و backend/app/services/verify_runtime/safety.py نیز وابسته به system_prompts هستند. فایل backend/app/services/verify_runtime/static_probe.py و backend/app/services/verify_runtime/storage.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/test_probe.py و backend/app/services/verify_runtime/ui_probe.py نیز وابسته به system_prompts هستند. فایل backend/app/services/verify_runtime/vision_helper.py و backend/app/services/verify_runtime/api_probe.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/auth_runner.py و backend/app/services/verify_runtime/backend_log_probe.py نیز وابسته به system_prompts هستند. فایل backend/app/services/verify_runtime/behavioral_probe_layer.py و backend/app/services/verify_runtime/browser_pool.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/ac_cache_service.py و backend/app/services/verify_runtime/ac_enricher.py نیز وابسته به system_prompts هستند. فایل backend/app/services/verify_runtime/ac_schema.py و backend/app/services/verify_runtime/base.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/scan_v5/anti_pattern_detector.py و backend/app/services/scan_v5/coherence_analyzer.py نیز وابسته به system_prompts هستند. فایل backend/app/services/scan_v5/comprehensive_inventory.py و backend/app/services/scan_v5/delta_analyzer.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/scan_v5/dependency_analyzer.py و backend/app/services/scan_v5/feature_documenter.py نیز وابسته به system_prompts هستند. فایل backend/app/services/scan_v5/notification_auditor.py و backend/app/services/scan_v5/outcome_analyzer.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/scan_v5/purpose_extractor.py و backend/app/services/scan_v5/runtime_discovery.py نیز وابسته به system_prompts هستند. فایل backend/app/services/scan_v5/stale_detector.py و backend/app/services/scan_v5/_findings_to_tasks.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/inspector_agent.py و backend/app/services/inspector_intent_resolver.py نیز وابسته به system_prompts هستند. فایل backend/app/services/inspector_proposal_executor.py و backend/app/services/inspector_roles.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/inspector_scan_bridge.py و backend/app/services/oversight_inspector_bridge.py نیز وابسته به system_prompts هستند. فایل backend/app/models/inspector_prompt_field.py و backend/app/models/inspector_session.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/models/ai_log.py و backend/app/models/ai_profile.py نیز وابسته به system_prompts هستند. فایل backend/app/models/analysis_report.py و backend/app/models/debate.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/models/project.py و backend/app/models/render_log.py نیز وابسته به system_prompts هستند. فایل backend/app/models/setting.py و backend/app/models/system_prompt.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/ai_usage.py و backend/app/api/routes/analysis.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/chat.py و backend/app/api/routes/config.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/creator.py و backend/app/api/routes/debate.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/diagrams.py و backend/app/api/routes/external.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/external_projects.py و backend/app/api/routes/github_import.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/model_profiles.py و backend/app/api/routes/models.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/notifications.py و backend/app/api/routes/orchestrator.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/oversight.py و backend/app/api/routes/project_health.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/project_journal.py و backend/app/api/routes/project_memory.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/project_structure.py و backend/app/api/routes/projects.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/render_logs.py و backend/app/api/routes/runtime.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/security_analysis.py و backend/app/api/routes/settings.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/api/routes/simple_projects.py و backend/app/api/routes/system_prompts.py نیز وابسته به system_prompts هستند. فایل backend/app/api/routes/unified_api.py و backend/app/api/routes/upload.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/core/config.py و backend/app/core/database.py نیز وابسته به system_prompts هستند. فایل backend/app/core/logging_utils.py و backend/app/core/models_registry.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/core/roles.py و backend/app/main.py نیز وابسته به system_prompts هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/models/system_prompt.py باید بررسی و ساختار مدل system_prompt مستند شود.
- [ ] فایل backend/app/api/routes/system_prompts.py باید بررسی و endpointهای CRUD برای system_prompts مستند شود.
- [ ] فایل backend/app/services/ai_manager.py باید بررسی و نحوه استفاده از system_prompts در pipeline AI مستند شود.
- [ ] فایل backend/app/services/prompt_helper.py باید بررسی و توابع کمکی مرتبط با system_prompts مستند شود.
- [ ] فایل backend/app/services/ai_base.py باید بررسی و نحوه استفاده از system_prompts در کلاس پایه AI مستند شود.
- [ ] فایل‌های downstream consumers (claude_service.py, openai_service.py, gemini_service.py, deepseek_service.py, perplexity_service.py) باید بررسی و نحوه استفاده از system_prompts مستند شود.
- [ ] گزارش audit باید شامل شناسایی نقاط ضعف و ناسازگاری‌ها باشد.
- [ ] گزارش audit باید ground truth برای مراحل بعدی تعیین کند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مرحله ۱: بررسی فایل backend/app/models/system_prompt.py برای شناسایی ساختار مدل system_prompt. مرحله ۲: بررسی فایل backend/app/api/routes/system_prompts.py برای شناسایی endpointهای مرتبط با system_prompts. مرحله ۳: بررسی فایل backend/app/services/ai_manager.py برای شناسایی نحوه استفاده از system_prompts در pipeline AI. مرحله ۴: بررسی فایل backend/app/services/prompt_helper.py برای شناسایی توابع کمکی مرتبط با system_prompts. مرحله ۵: بررسی فایل backend/app/services/ai_base.py برای شناسایی کلاس پایه AI و نحوه استفاده از system_prompts. مرحله ۶: بررسی فایل‌های backend/app/services/claude_service.py، backend/app/services/openai_service.py، backend/app/services/gemini_service.py، backend/app/services/deepseek_service.py، و backend/app/services/perplexity_service.py برای شناسایی نحوه استفاده از system_prompts در هر سرویس. مرحله ۷: بررسی فایل backend/app/services/inspector_agent.py برای شناسایی نحوه استفاده از system_prompts در تحلیل کد. مرحله ۸: بررسی فایل backend/app/services/oversight_strong_prompt.py و backend/app/services/oversight_codex_service.py برای شناسایی نحوه استفاده از system_prompts در oversight. مرحله ۹: بررسی فایل backend/app/services/scan_v5/scan_bundle.py و backend/app/services/scan_v5/scan_inspector_session.py برای شناسایی نحوه استفاده از system_prompts در scan. مرحله ۱۰: بررسی فایل backend/app/services/verify_runtime/context_builder.py و backend/app/services/verify_runtime/code_aware_verifier.py برای شناسایی نحوه استفاده از system_prompts در verify runtime. مرحله ۱۱: بررسی فایل backend/app/services/creator_engine.py و backend/app/services/creator_idea_to_prompt.py برای شناسایی نحوه استفاده از system_prompts در creator. مرحله ۱۲: بررسی فایل backend/app/services/debate_service.py و backend/app/services/deep_analysis_service.py برای شناسایی نحوه استفاده از system_prompts در debate و deep analysis. مرحله ۱۳: بررسی فایل backend/app/services/analysis_progress_manager.py و backend/app/services/health_to_issues_service.py برای شناسایی نحوه استفاده از system_prompts در analysis progress. مرحله ۱۴: بررسی فایل backend/app/services/log_to_issues_service.py و backend/app/services/notification_service.py برای شناسایی نحوه استفاده از system_prompts در log to issues. مرحله ۱۵: بررسی فایل backend/app/services/project_health_analyzer.py و backend/app/services/project_analyzer.py برای شناسایی نحوه استفاده از system_prompts در project health. مرحله ۱۶: بررسی فایل backend/app/services/report_validator.py و backend/app/services/security_analyzer.py برای شناسایی نحوه استفاده از system_prompts در report validation. مرحله ۱۷: بررسی فایل backend/app/services/smart_orchestrator.py و backend/app/services/task_consolidation_service.py برای شناسایی نحوه استفاده از system_prompts در smart orchestrator. مرحله ۱۸: بررسی فایل backend/app/services/task_merge_service.py و backend/app/services/test_coverage_analyzer.py برای شناسایی نحوه استفاده از system_prompts در task merge. مرحله ۱۹: بررسی فایل backend/app/services/ai_balance_service.py و backend/app/services/capability_detector.py برای شناسایی نحوه استفاده از system_prompts در AI balance. مرحله ۲۰: بررسی فایل backend/app/services/model_capability_tester.py و backend/app/services/model_profiler.py برای شناسایی نحوه استفاده از system_prompts در model capability. مرحله ۲۱: بررسی فایل backend/app/services/quick_approval_service.py و backend/app/services/runtime_executor.py برای شناسایی نحوه استفاده از system_prompts در quick approval. مرحله ۲۲: بررسی فایل backend/app/services/simple_creator.py و backend/app/services/smart_import.py برای شناسایی نحوه استفاده از system_prompts در simple creator. مرحله ۲۳: بررسی فایل backend/app/services/unified_storage.py و backend/app/services/storage_service.py برای شناسایی نحوه استفاده از system_prompts در storage. مرحله ۲۴: بررسی فایل backend/app/services/db_service.py و backend/app/services/dynamic_config.py برای شناسایی نحوه استفاده از system_prompts در database. مرحله ۲۵: بررسی فایل backend/app/services/external_monitor.py و backend/app/services/external_project_connector.py برای شناسایی نحوه استفاده از system_prompts در external monitor. مرحله ۲۶: بررسی فایل backend/app/services/github_import.py و backend/app/services/github_pr_service.py برای شناسایی نحوه استفاده از system_prompts در GitHub. مرحله ۲۷: بررسی فایل backend/app/services/github_storage.py و backend/app/services/deploy_service.py برای شناسایی نحوه استفاده از system_prompts در deploy. مرحله ۲۸: بررسی فایل backend/app/services/diagram_service.py و backend/app/services/dynamic_diagram_service.py برای شناسایی نحوه استفاده از system_prompts در diagram. مرحله ۲۹: بررسی فایل backend/app/services/browser_automation.py و backend/app/services/background_scheduler.py برای شناسایی نحوه استفاده از system_prompts در browser automation. مرحله ۳۰: بررسی فایل backend/app/services/content_sanitizer.py و backend/app/services/code_quality_analyzer.py برای شناسایی نحوه استفاده از system_prompts در content sanitizer. مرحله ۳۱: بررسی فایل backend/app/services/intelligent_field_creator.py و backend/app/services/journal_service.py برای شناسایی نحوه استفاده از system_prompts در intelligent field creator. مرحله ۳۲: بررسی فایل backend/app/services/log_stream_service.py و backend/app/services/oversight_service.py برای شناسایی نحوه استفاده از system_prompts در log stream. مرحله ۳۳: بررسی فایل backend/app/services/oversight_settings.py و backend/app/services/oversight_verifier.py برای شناسایی نحوه استفاده از system_prompts در oversight settings. مرحله ۳۴: بررسی فایل backend/app/services/oversight_upload_session.py و backend/app/services/oversight_telegram_compose.py برای شناسایی نحوه استفاده از system_prompts در oversight upload. مرحله ۳۵: بررسی فایل backend/app/services/oversight_mega_bundle.py و backend/app/services/oversight_inspector_bridge.py برای شناسایی نحوه استفاده از system_prompts در oversight mega bundle. مرحله ۳۶: بررسی فایل backend/app/services/oversight_extraction.py و backend/app/services/oversight_deep_scan_service.py برای شناسایی نحوه استفاده از system_prompts در oversight extraction. مرحله ۳۷: بررسی فایل backend/app/services/oversight_progress.py و backend/app/services/oversight_model_temp_activate.py برای شناسایی نحوه استفاده از system_prompts در oversight progress. مرحله ۳۸: بررسی فایل backend/app/services/oversight_codex_service.py و backend/app/services/oversight_strong_prompt.py برای شناسایی نحوه استفاده از system_prompts در oversight codex. مرحله ۳۹: بررسی فایل backend/app/services/oversight_verify_pdf.py و backend/app/services/oversight_verifier.py برای شناسایی نحوه استفاده از system_prompts در oversight verify. مرحله ۴۰: بررسی فایل backend/app/services/verify_runtime/iterative_orchestrator.py و backend/app/services/verify_runtime/context_builder.py برای شناسایی نحوه استفاده از system_prompts در verify runtime iterative. مرحله ۴۱: بررسی فایل backend/app/services/verify_runtime/code_aware_verifier.py و backend/app/services/verify_runtime/code_content_searcher.py برای شناسایی نحوه استفاده از system_prompts در verify runtime code aware. مرحله ۴۲: بررسی فایل backend/app/services/verify_runtime/inspector_probe.py و backend/app/services/verify_runtime/manual_probe.py برای شناسایی نحوه استفاده از system_prompts در verify runtime inspector. مرحله ۴۳: بررسی فایل backend/app/services/verify_runtime/navigation_helper.py و backend/app/services/verify_runtime/render_autodetect.py برای شناسایی نحوه استفاده از system_prompts در verify runtime navigation. مرحله ۴۴: بررسی فایل backend/app/services/verify_runtime/runner.py و backend/app/services/verify_runtime/safety.py برای شناسایی نحوه استفاده از system_prompts در verify runtime runner. مرحله ۴۵: بررسی فایل backend/app/services/verify_runtime/static_probe.py و backend/app/services/verify_runtime/storage.py برای شناسایی نحوه استفاده از system_prompts در verify runtime static. مرحله ۴۶: بررسی فایل backend/app/services/verify_runtime/test_probe.py و backend/app/services/verify_runtime/ui_probe.py برای شناسایی نحوه استفاده از system_prompts در verify runtime test. مرحله ۴۷: بررسی فایل backend/app/services/verify_runtime/vision_helper.py و backend/app/services/verify_runtime/api_probe.py برای شناسایی نحوه استفاده از system_prompts در verify runtime vision. مرحله ۴۸: بررسی فایل backend/app/services/verify_runtime/auth_runner.py و backend/app/services/verify_runtime/backend_log_probe.py برای شناسایی نحوه استفاده از system_prompts در verify runtime auth. مرحله ۴۹: بررسی فایل backend/app/services/verify_runtime/behavioral_probe_layer.py و backend/app/services/verify_runtime/browser_pool.py برای شناسایی نحوه استفاده از system_prompts در verify runtime behavioral. مرحله ۵۰: بررسی فایل backend/app/services/verify_runtime/ac_cache_service.py و backend/app/services/verify_runtime/ac_enricher.py برای شناسایی نحوه استفاده از system_prompts در verify runtime ac cache. مرحله ۵۱: بررسی فایل backend/app/services/verify_runtime/ac_schema.py و backend/app/services/verify_runtime/base.py برای شناسایی نحوه استفاده از system_prompts در verify runtime ac schema. مرحله ۵۲: بررسی فایل backend/app/services/scan_v5/anti_pattern_detector.py و backend/app/services/scan_v5/coherence_analyzer.py برای شناسایی نحوه استفاده از system_prompts در scan v5 anti pattern. مرحله ۵۳: بررسی فایل backend/app/services/scan_v5/comprehensive_inventory.py و backend/app/services/scan_v5/delta_analyzer.py برای شناسایی نحوه استفاده از system_prompts در scan v5 comprehensive. مرحله ۵۴: بررسی فایل backend/app/services/scan_v5/dependency_analyzer.py و backend/app/services/scan_v5/feature_documenter.py برای شناسایی نحوه استفاده از system_prompts در scan v5 dependency. مرحله ۵۵: بررسی فایل backend/app/services/scan_v5/notification_auditor.py و backend/app/services/scan_v5/outcome_analyzer.py برای شناسایی نحوه استفاده از system_prompts در scan v5 notification. مرحله ۵۶: بررسی فایل backend/app/services/scan_v5/purpose_extractor.py و backend/app/services/scan_v5/runtime_discovery.py برای شناسایی نحوه استفاده از system_prompts در scan v5 purpose. مرحله ۵۷: بررسی فایل backend/app/services/scan_v5/stale_detector.py و backend/app/services/scan_v5/_findings_to_tasks.py برای شناسایی نحوه استفاده از system_prompts در scan v5 stale. مرحله ۵۸: بررسی فایل backend/app/services/inspector_agent.py و backend/app/services/inspector_intent_resolver.py برای شناسایی نحوه استفاده از system_prompts در inspector agent. مرحله ۵۹: بررسی فایل backend/app/services/inspector_proposal_executor.py و backend/app/services/inspector_roles.py برای شناسایی نحوه استفاده از system_prompts در inspector proposal. مرحله ۶۰: بررسی فایل backend/app/services/inspector_scan_bridge.py و backend/app/services/oversight_inspector_bridge.py برای شناسایی نحوه استفاده از system_prompts در inspector scan bridge. مرحله ۶۱: بررسی فایل backend/app/models/inspector_prompt_field.py و backend/app/models/inspector_session.py برای شناسایی نحوه استفاده از system_prompts در inspector models. مرحله ۶۲: بررسی فایل backend/app/models/ai_log.py و backend/app/models/ai_profile.py برای شناسایی نحوه استفاده از system_prompts در AI models. مرحله ۶۳: بررسی فایل backend/app/models/analysis_report.py و backend/app/models/debate.py برای شناسایی نحوه استفاده از system_prompts در analysis models. مرحله ۶۴: بررسی فایل backend/app/models/project.py و backend/app/models/render_log.py برای شناسایی نحوه استفاده از system_prompts در project models. مرحله ۶۵: بررسی فایل backend/app/models/setting.py و backend/app/models/system_prompt.py برای شناسایی نحوه استفاده از system_prompts در setting models. مرحله ۶۶: بررسی فایل backend/app/api/routes/ai_usage.py و backend/app/api/routes/analysis.py برای شناسایی نحوه استفاده از system_prompts در AI usage routes. مرحله ۶۷: بررسی فایل backend/app/api/routes/chat.py و backend/app/api/routes/config.py برای شناسایی نحوه استفاده از system_prompts در chat routes. مرحله ۶۸: بررسی فایل backend/app/api/routes/creator.py و backend/app/api/routes/debate.py برای شناسایی نحوه استفاده از system_prompts در creator routes. مرحله ۶۹: بررسی فایل backend/app/api/routes/diagrams.py و backend/app/api/routes/external.py برای شناسایی نحوه استفاده از system_prompts در diagrams routes. مرحله ۷۰: بررسی فایل backend/app/api/routes/external_projects.py و backend/app/api/routes/github_import.py برای شناسایی نحوه استفاده از system_prompts در external projects routes. مرحله ۷۱: بررسی فایل backend/app/api/routes/model_profiles.py و backend/app/api/routes/models.py برای شناسایی نحوه استفاده از system_prompts در model profiles routes. مرحله ۷۲: بررسی فایل backend/app/api/routes/notifications.py و backend/app/api/routes/orchestrator.py برای شناسایی نحوه استفاده از system_prompts در notifications routes. مرحله ۷۳: بررسی فایل backend/app/api/routes/oversight.py و backend/app/api/routes/project_health.py برای شناسایی نحوه استفاده از system_prompts در oversight routes. مرحله ۷۴: بررسی فایل backend/app/api/routes/project_journal.py و backend/app/api/routes/project_memory.py برای شناسایی نحوه استفاده از system_prompts در project journal routes. مرحله ۷۵: بررسی فایل backend/app/api/routes/project_structure.py و backend/app/api/routes/projects.py برای شناسایی نحوه استفاده از system_prompts در project structure routes. مرحله ۷۶: بررسی فایل backend/app/api/routes/render_logs.py و backend/app/api/routes/runtime.py برای شناسایی نحوه استفاده از system_prompts در render logs routes. مرحله ۷۷: بررسی فایل backend/app/api/routes/security_analysis.py و backend/app/api/routes/settings.py برای شناسایی نحوه استفاده از system_prompts در security analysis routes. مرحله ۷۸: بررسی فایل backend/app/api/routes/simple_projects.py و backend/app/api/routes/system_prompts.py برای شناسایی نحوه استفاده از system_prompts در simple projects routes. مرحله ۷۹: بررسی فایل backend/app/api/routes/unified_api.py و backend/app/api/routes/upload.py برای شناسایی نحوه استفاده از system_prompts در unified api routes. مرحله ۸۰: بررسی فایل backend/app/core/config.py و backend/app/core/database.py برای شناسایی نحوه استفاده از system_prompts در core config. مرحله ۸۱: بررسی فایل backend/app/core/logging_utils.py و backend/app/core/models_registry.py برای شناسایی نحوه استفاده از system_prompts در core logging. مرحله ۸۲: بررسی فایل backend/app/core/roles.py و backend/app/main.py برای شناسایی نحوه استفاده از system_prompts در core roles. مرحله ۸۳: مستندسازی تمام یافته‌ها در یک گزارش audit. مرحله ۸۴: شناسایی نقاط ضعف و ناسازگاری‌ها. مرحله ۸۵: تعیین ground truth برای مراحل بعدی.

## 💡 نمونه‌های قبل/بعد
**وضعیت فعلی system_prompts**

_قبل:_
```
فایل backend/app/models/system_prompt.py: مدل system_prompt با فیلدهای name, content, version, is_active, created_at, updated_at
```

_بعد:_
```
مستندسازی وضعیت موجود بدون تغییر کد
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در system_prompts می‌تواند تمام downstream consumers را break کند. downstream consumers شامل بیش از ۱۰۰ فایل در backend/app/services/، backend/app/models/، backend/app/api/routes/، و backend/app/core/ هستند. قبل از هر تغییری، باید همه caller های system_prompts بررسی شوند. فایل‌های backend/app/services/claude_service.py، backend/app/services/openai_service.py، backend/app/services/gemini_service.py، backend/app/services/deepseek_service.py، و backend/app/services/perplexity_service.py به عنوان downstream consumers اصلی از system_prompts استفاده می‌کنند. فایل backend/app/services/inspector_agent.py نیز از system_prompts برای تحلیل کد استفاده می‌کند. فایل backend/app/services/oversight_strong_prompt.py و backend/app/services/oversight_codex_service.py نیز وابسته به system_prompts هستند. فایل backend/app/services/scan_v5/scan_bundle.py و backend/app/services/scan_v5/scan_inspector_session.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/verify_runtime/context_builder.py و backend/app/services/verify_runtime/code_aware_verifier.py نیز وابسته به system_prompts هستند. فایل backend/app/services/creator_engine.py و backend/app/services/creator_idea_to_prompt.py نیز از system_prompts استفاده می‌کنند. فایل backend/app/services/debate_service.py و backend/app/services/deep_analysis_service.py نیز وابسته به system_prompts هستند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 31: افزودن ماژول Hallucination Guard به ai_manager در pipeline ai_llm

**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک ماژول جدید برای کاهش توهم (hallucination guard) در pipeline `ai_llm` است. ماژول باید به `ai_manager` اضافه شود و شامل سه قابلیت اصلی باشد: 1) grounding پاسخ‌ها به منابع معتبر، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین. فایل‌های مرتبط شامل `backend/app/ai_manager.py` و `backend/app/ai_manager.py` هستند. این مرحله شامل refactoring کد موجود برای رفع ناسازگاری منطقی (coherence issue) است. خارج از scope: تغییر در frontend (Next.js)، اضافه کردن endpoint جدید، یا تغییر در pipeline‌های دیگر.
**Key terms:** backend/app/ai_manager.py, backend/app/ai_manager.py, ai_llm, hallucination guard, grounding, fact-checking, self-consistency

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در هیچ‌کدام از کامپوننت‌ها به مکانیزم‌های کاهش توهم (hallucination guard) اشاره نشده است. با توجه به اینکه pipeline با مدل‌های زبانی بزرگ کار می‌کند، عدم وجود چنین مکانیزمی (مانند grounding, fact-checking, یا self-consistency) می‌تواند منجر به تولید اطلاعات نادرست شود.

یک ماژول hallucination guard به ai_manager اضافه کنید. این ماژول می‌تواند شامل: 1) grounding پاسخ‌ها به منابع معتبر (در صورت وجود)، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین باشد.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن ماژول Hallucination Guard به ai_manager در pipeline ai_llm

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:نامشخص (فایل deep-read نشده)` — `AIManager.ai_llm` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل هدف اصلی برای افزودن ماژول hallucination guard است.
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی، این فایل شامل کلاس AIManager و متد ai_llm است که pipeline اصلی را مدیریت می‌کند.
  ```
- `backend/app/services/hallucination_guard.py:1-150 (فایل جدید)` — `HallucinationGuard` — فایل جدید — باید ایجاد شود. این ماژول جدید برای کاهش توهم در pipeline ai_llm طراحی می‌شود.
  ```python
  فایل جدید — باید ایجاد شود. شامل کلاس HallucinationGuard با سه متد اصلی ground_response, validate_with_second_model, detect_low_confidence.
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — بر اساس ساختار پروژه، از Python با FastAPI استفاده شده است. سرویس‌های AI شامل Claude، OpenAI، Gemini و DeepSeek هستند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` — احتمالاً کلاس پایه برای سرویس‌های AI است و AIManager از آن ارث‌بری می‌کند. تغییرات در AIManager ممکن است نیاز به هماهنگی با این کلاس داشته باشد.
- `backend/app/services/ai_balance_service.py` — این سرویس احتمالاً تعادل بین مدل‌های مختلف AI را مدیریت می‌کند و ممکن است با pipeline ai_llm در تعامل باشد.
- `backend/app/services/claude_service.py` — یکی از سرویس‌های مدل‌های زبانی که توسط ai_llm فراخوانی می‌شود. تغییر در pipeline ممکن است روی نحوه فراخوانی این سرویس تأثیر بگذارد.
- `backend/app/services/openai_service.py` — مشابه claude_service، این سرویس نیز توسط ai_llm فراخوانی می‌شود و تغییرات pipeline روی آن تأثیر می‌گذارد.
- `backend/app/services/gemini_service.py` — سرویس دیگر مدل زبانی که ممکن است توسط ai_llm استفاده شود.

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات عمدتاً روی فایل `backend/app/services/ai_manager.py` متمرکز است. ماژول جدید `hallucination_guard.py` به عنوان یک dependency جدید به این فایل اضافه می‌شود. سرویس‌های مدل (claude_service, openai_service, gemini_service) که توسط ai_llm فراخوانی می‌شوند، به صورت غیرمستقیم تحت تأثیر قرار می‌گیرند زیرا خروجی آن‌ها پس از پردازش توسط hallucination guard عبور داده می‌شود. فایل `ai_base.py` به عنوان کلاس پایه ممکن است نیاز به تغییرات جزئی برای پشتیبانی از قابلیت‌های جدید داشته باشد. فایل `ai_balance_service.py` نیز ممکن است برای هماهنگی با pipeline جدید نیاز به تنظیمات داشته باشد.

## 🔍 Context و وضعیت فعلی
بر اساس درخواست کاربر، نیاز به افزودن یک ماژول جدید برای کاهش توهم (hallucination guard) در pipeline `ai_llm` است. این ماژول باید به `ai_manager` اضافه شود و شامل سه قابلیت اصلی باشد: 1) grounding پاسخ‌ها به منابع معتبر، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین. فایل‌های مرتبط شامل `backend/app/ai_manager.py` و `backend/app/ai_manager.py` هستند (هر دو یک فایل هستند). این مرحله شامل refactoring کد موجود برای رفع ناسازگاری منطقی (coherence issue) است. خارج از scope: تغییر در frontend (Next.js)، اضافه کردن endpoint جدید، یا تغییر در pipeline‌های دیگر.

کلیدواژه‌های اصلی: backend/app/ai_manager.py, ai_llm, hallucination guard, grounding, fact-checking, self-consistency

شواهد در کد: فایل `backend/app/services/ai_manager.py` در ساختار پروژه موجود است اما deep-read نشده است. بر اساس ساختار سطحی، این فایل احتمالاً شامل کلاس `AIManager` و متد `ai_llm` است که pipeline اصلی پردازش درخواست‌های LLM را مدیریت می‌کند. عدم وجود مکانیزم‌های کاهش توهم در این pipeline می‌تواند منجر به تولید اطلاعات نادرست شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ماژول hallucination_guard.py در مسیر backend/app/services/ ایجاد شود و شامل کلاس HallucinationGuard با سه متد ground_response, validate_with_second_model, detect_low_confidence باشد.
- [ ] متد ai_llm در backend/app/services/ai_manager.py از HallucinationGuard استفاده کند و مراحل grounding, validation, و confidence detection را اجرا کند.
- [ ] متد ground_response باید پاسخ را با استفاده از منابع معتبر (sources) بهبود بخشد و خروجی grounded response برگرداند.
- [ ] متد validate_with_second_model باید با استفاده از مدل دوم (مثلاً Claude برای validation پاسخ OpenAI) fact-checking انجام دهد و نتیجه ValidationResult برگرداند.
- [ ] متد detect_low_confidence باید پاسخ‌های با قطعیت پایین را تشخیص داده و پرچم‌گذاری کند.
- [ ] هیچ تغییری در frontend (Next.js)، endpoint جدید، یا pipeline‌های دیگر ایجاد نشود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک ماژول جدید به نام `hallucination_guard.py` در مسیر `backend/app/services/hallucination_guard.py`
2. طراحی کلاس `HallucinationGuard` با سه متد اصلی:
   - `ground_response(response: str, sources: List[str]) -> str`: برای grounding پاسخ به منابع معتبر
   - `validate_with_second_model(response: str, context: str) -> ValidationResult`: برای fact-checking با مدل دوم
   - `detect_low_confidence(response: str) -> ConfidenceFlag`: برای تشخیص پاسخ‌های با قطعیت پایین
3. افزودن import و استفاده از `HallucinationGuard` در `backend/app/services/ai_manager.py` در متد `ai_llm`
4. اعمال تغییرات در pipeline به‌گونه‌ای که پس از دریافت پاسخ از LLM، مراحل grounding و validation اجرا شوند
5. اضافه کردن logging برای ثبت موارد hallucination detected
6. خارج از scope: تغییر در frontend، اضافه کردن endpoint جدید، تغییر در pipeline‌های دیگر

## 💡 نمونه‌های قبل/بعد
**افزودن HallucinationGuard به ai_llm pipeline**

_قبل:_
```
# backend/app/services/ai_manager.py (قبل از تغییر)
class AIManager:
    async def ai_llm(self, prompt: str, model: str) -> str:
        service = self._get_service(model)
        response = await service.generate(prompt)
        return response
```

_بعد:_
```
# backend/app/services/ai_manager.py (بعد از تغییر)
from backend.app.services.hallucination_guard import HallucinationGuard

class AIManager:
    def __init__(self):
        self.hallucination_guard = HallucinationGuard()
    
    async def ai_llm(self, prompt: str, model: str, sources: List[str] = None) -> str:
        service = self._get_service(model)
        response = await service.generate(prompt)
        
        # مرحله 1: grounding به منابع معتبر
        if sources:
            response = await self.hallucination_guard.ground_response(response, sources)
        
        # مرحله 2: validation با مدل دوم
        validation = await self.hallucination_guard.validate_with_second_model(response, prompt)
        if not validation.is_valid:
            logger.warning(f"Hallucination detected: {validation.issues}")
        
        # مرحله 3: تشخیص قطعیت پایین
        confidence = await self.hallucination_guard.detect_low_confidence(response)
        if confidence.is_low:
            response = f"[اطلاعات با قطعیت پایین] {response}"
        
        return response
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_hallucination_guard.py -v`
- `python -c "from backend.app.services.hallucination_guard import HallucinationGuard; print('Module loaded successfully')"`
- `grep -r "hallucination_guard" backend/app/services/ai_manager.py`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل `backend/app/services/ai_manager.py` deep-read نشده است، بنابراین ساختار دقیق متد ai_llm و نحوه فراخوانی سرویس‌های مدل نامشخص است. تغییرات در این فایل ممکن است روی تمام سرویس‌هایی که از ai_llm استفاده می‌کنند (مانند chat, analysis, creator) تأثیر بگذارد. همچنین، افزودن validation با مدل دوم ممکن است latency pipeline را افزایش دهد. ریسک دیگر این است که ماژول جدید ممکن است با سرویس‌های موجود (claude_service, openai_service, gemini_service) ناسازگاری داشته باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 32: بررسی و رفع عدم تطابق نوع داده target_locations بین دو کامپوننت

**Scope:** این مرحله شامل شناسایی و مستندسازی ناسازگاری نوع داده فیلد target_locations بین دو کامپوننت (احتمالاً oversight_strong_prompt و ai_manager)، تعیین ground truth و align کردن طرف دیگر، و اطمینان از عبور integration test مربوط به pipeline ai_llm است. همچنین PR description باید توضیح دهد چرا این تصمیم گرفته شده است. خارج از scope این مرحله: پیاده‌سازی مکانیزم‌های HallucinationGuard، Grounding، Fact-Checking و سایر مراحل باقی‌مانده.
**Key terms:** target_locations, List[Dict], List[str], backend/app/oversight_strong_prompt.py, backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py, test_integration

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 13 از 16
  id: 3269802a-8316-4245-a7c6-ccebee7a7573
  عنوان اصلی: [منطق] عدم تطابق نوع داده target_locations بین دو کامپوننت
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[Dict\\]", "List\\[str\\]"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_manager.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[str\\]", "List\\[Dict\\]"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_manager.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع عدم تطابق نوع داده target_locations بین oversight_strong_prompt و ai_manager

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py` — `target_locations` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، احتمالاً target_locations در این فایل تعریف شده است.
- `backend/app/services/ai_manager.py` — `target_locations` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، احتمالاً target_locations در این فایل استفاده شده است.
- `backend/tests/test_ai_llm_pipeline.py` — `test_integration` — این فایل در ساختار پروژه موجود نیست و باید ایجاد شود. مسیر دقیق ممکن است tests/test_ai_llm_pipeline.py یا مشابه باشد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_inspector_bridge.py` — احتمالاً از target_locations استفاده می‌کند یا به oversight_strong_prompt متصل است
- `backend/app/services/oversight_service.py` — احتمالاً از target_locations در فرآیند oversight استفاده می‌کند
- `backend/app/services/inspector_agent.py` — احتمالاً target_locations را به عنوان ورودی/خروجی دریافت می‌کند
- `backend/app/services/oversight_verifier.py` — احتمالاً target_locations را برای verify استفاده می‌کند
- `backend/app/services/verify_runtime/inspector_probe.py` — احتمالاً target_locations را در فرآیند verify runtime استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این تغییر بر فایل‌های backend/app/services/oversight_strong_prompt.py و backend/app/services/ai_manager.py تأثیر مستقیم دارد. فایل‌های caller مانند backend/app/services/oversight_inspector_bridge.py، backend/app/services/oversight_service.py، backend/app/services/inspector_agent.py، backend/app/services/oversight_verifier.py و backend/app/services/verify_runtime/inspector_probe.py ممکن است تحت تأثیر قرار گیرند. همچنین فایل تست tests/test_ai_llm_pipeline.py باید ایجاد یا به‌روزرسانی شود. تغییر نوع داده target_locations می‌تواند downstream consumers را break کند.

## 🔍 Context و وضعیت فعلی
بررسی و رفع عدم تطابق نوع داده target_locations بین دو کامپوننت oversight_strong_prompt و ai_manager. این مرحله شامل شناسایی و مستندسازی ناسازگاری نوع داده فیلد target_locations بین دو کامپوننت (احتمالاً oversight_strong_prompt و ai_manager)، تعیین ground truth و align کردن طرف دیگر، و اطمینان از عبور integration test مربوط به pipeline ai_llm است. همچنین PR description باید توضیح دهد چرا این تصمیم گرفته شده است. خارج از scope این مرحله: پیاده‌سازی مکانیزم‌های HallucinationGuard، Grounding، Fact-Checking و سایر مراحل باقی‌مانده.

کلیدواژه‌ها: target_locations, List[Dict], List[str], backend/app/oversight_strong_prompt.py, backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py, test_integration

بر اساس ساختار پروژه، فایل‌های backend/app/services/oversight_strong_prompt.py و backend/app/services/ai_manager.py در مسیرهای مشخص شده وجود دارند. فایل تست tests/test_ai_llm_pipeline.py در لیست فایل‌های پروژه دیده نمی‌شود و احتمالاً باید ایجاد شود. همچنین فایل‌های مرتبط مانند backend/app/services/oversight_inspector_bridge.py و backend/app/services/oversight_service.py ممکن است از target_locations استفاده کنند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline ai_llm بدون شکست عبور می‌کند
- [ ] PR description توضیح می‌دهد چرا این تصمیم گرفته شد
- [ ] تمامی callerهای هر دو فایل بررسی شدند و downstream consumers شکسته نشدند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی فایل backend/app/services/oversight_strong_prompt.py برای شناسایی نوع داده فعلی target_locations (احتمالاً List[Dict] یا List[str])
2. بررسی فایل backend/app/services/ai_manager.py برای شناسایی نوع داده فعلی target_locations
3. تعیین ground truth بر اساس نیاز واقعی pipeline ai_llm و مستندسازی فرضیات هر طرف
4. align کردن طرف دیگر با ground truth تعیین شده
5. بررسی تمام callerهای هر دو فایل برای اطمینان از عدم شکست downstream consumers
6. ایجاد/به‌روزرسانی integration test در tests/test_ai_llm_pipeline.py برای عبور از pipeline ai_llm
7. نوشتن PR description با توضیح دلیل تصمیم‌گیری
8. اجرای تست‌های مرتبط برای اطمینان از عبور موفق

## 💡 نمونه‌های قبل/بعد
**نمونه تغییر نوع داده target_locations**

_قبل:_
```
# قبل از تغییر - نوع داده ناسازگار
# در oversight_strong_prompt.py:
target_locations: List[Dict[str, Any]] = [{"path": "/api/users", "method": "GET"}]

# در ai_manager.py:
target_locations: List[str] = ["/api/users", "/api/projects"]
```

_بعد:_
```
# بعد از تغییر - نوع داده یکسان
# در oversight_strong_prompt.py:
target_locations: List[str] = ["/api/users", "/api/projects"]

# در ai_manager.py:
target_locations: List[str] = ["/api/users", "/api/projects"]
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_llm_pipeline.py::test_integration -v --timeout=120`
- `pytest backend/tests/ -k "target_locations or ai_llm" -v`
- `grep -rn "target_locations" backend/app/services/ --include="*.py"`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر نوع داده target_locations می‌تواند downstream consumers مانند oversight_inspector_bridge.py، oversight_service.py، inspector_agent.py، oversight_verifier.py و inspector_probe.py را break کند. همچنین فایل‌های تست مرتبط مانند test_runtime_verify_integration.py و test_verify_v7.py ممکن است تحت تأثیر قرار گیرند. قبل از merge، باید تمام callerهای هر دو فایل بررسی شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 33: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد قابلیت‌های موجود

**Scope:** این بخش یک یادداشت مهم برای مدل اجراکننده است و دستورالعمل‌های رفتاری قبل از شروع هر تغییری را مشخص می‌کند. شامل: (1) بررسی وجود پیاده‌سازی قبلی با grep/search، (2) عدم بازسازی موارد موجود، (3) اصلاح/تکمیل موارد ناقص، (4) ثبت کامیت no-op در صورت کامل بودن، (5) مسئولیت مدل برای بررسی مستقل ساختار repo و فایل‌ها، (6) انتخاب بهترین تفسیر در صورت ابهام ACها، (7) انجام کامل کار در چند کامیت متوالی در صورت طولانی بودن. این بخش خود یک مرحله اجرایی نیست بلکه راهنمای اجرای سایر مراحل است.
**Key terms:** grep/search, no-op commit, commit message, PR description, checklist, foundation → core → integration → tests

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
اضافه کردن راهنمای بررسی اولیه repo به مدل اجراکننده

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `OversightService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اما بر اساس ساختار سطحی، oversight_service.py برای مدیریت وظایف oversight مناسب است.
  ```python
  class OversightService:
      def __init__(self):
          self.guide_path = 'docs/EXECUTOR_GUIDE.md'
  
      def get_executor_guide(self) -> str:
          try:
              with open(self.guide_path, 'r', encoding='utf-8') as f:
                  return f.read()
          except FileNotFoundError:
              return 'Guide not found.'
  ```
- `backend/app/api/routes/oversight.py:1-30` — `router` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اما بر اساس ساختار سطحی، oversight.py برای اضافه کردن endpoint مناسب است.
  ```python
  @router.get('/executor-guide')
  async def get_executor_guide():
      service = OversightService()
      return {'guide': service.get_executor_guide()}
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack شناسایی‌شده: Python + FastAPI + pytest. کتابخانه‌های مرتبط: os (برای خواندن فایل)، fastapi (برای endpoint).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — برای اضافه کردن ارجاع به فایل راهنما در startup
- `backend/tests/test_oversight_service.py` (سطر 1) — برای نوشتن تست تابع get_executor_guide()
- `docs/EXECUTOR_GUIDE.md` (سطر 1) — فایل راهنمای جدید که باید ایجاد شود

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های backend/app/services/oversight_service.py (برای تابع get_executor_guide)، backend/app/api/routes/oversight.py (برای endpoint جدید)، backend/app/main.py (برای ارجاع در startup) و docs/EXECUTOR_GUIDE.md (فایل جدید) وابسته است. همچنین backend/tests/test_oversight_service.py برای تست‌ها نیاز است. هیچ وابستگی به کتابخانه خارجی جدیدی ندارد.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت مهم برای مدل اجراکننده است و دستورالعمل‌های رفتاری قبل از شروع هر تغییری را مشخص می‌کند. شامل: (1) بررسی وجود پیاده‌سازی قبلی با grep/search، (2) عدم بازسازی موارد موجود، (3) اصلاح/تکمیل موارد ناقص، (4) ثبت کامیت no-op در صورت کامل بودن، (5) مسئولیت مدل برای بررسی مستقل ساختار repo و فایل‌ها، (6) انتخاب بهترین تفسیر در صورت ابهام ACها، (7) انجام کامل کار در چند کامیت متوالی در صورت طولانی بودن. این بخش خود یک مرحله اجرایی نیست بلکه راهنمای اجرای سایر مراحل است.

کلیدواژه‌ها: grep/search, no-op commit, commit message, PR description, checklist, foundation → core → integration → tests

این یادداشت باید به عنوان یک فایل راهنما در پروژه ذخیره شود تا مدل اجراکننده قبل از هر تغییری به آن مراجعه کند. فایل‌های مرتبط در پروژه شامل backend/app/services/oversight_service.py (برای مدیریت oversight tasks)، backend/app/services/inspector_agent.py (برای agent tasks)، backend/app/services/scan_v5/scan_bundle.py (برای scan tasks) و backend/app/services/verify_runtime/iterative_orchestrator.py (برای verify tasks) هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل docs/EXECUTOR_GUIDE.md باید با محتوای کامل یادداشت کاربر ایجاد شود.
- [ ] تابع get_executor_guide() در OversightService باید محتوای فایل را برگرداند.
- [ ] endpoint GET /api/executor-guide باید status 200 و محتوای guide را برگرداند.
- [ ] در backend/app/main.py باید ارجاع به docs/EXECUTOR_GUIDE.md در بخش startup اضافه شود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک فایل راهنما به نام docs/EXECUTOR_GUIDE.md با محتوای کامل یادداشت کاربر.
2. اضافه کردن ارجاع به این فایل در backend/app/main.py (در بخش startup) تا مدل اجراکننده بتواند آن را بخواند.
3. به‌روزرسانی backend/app/services/oversight_service.py برای اضافه کردن یک تابع get_executor_guide() که محتوای فایل را برمی‌گرداند.
4. اضافه کردن endpoint GET /api/executor-guide در backend/app/api/routes/oversight.py.
5. نوشتن تست برای تابع get_executor_guide() در backend/tests/test_oversight_service.py.
6. ثبت کامیت با پیام 'feat: add executor guide for pre-change repo inspection'.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن تابع get_executor_guide در oversight_service.py**

_قبل:_
```
class OversightService:
    def __init__(self):
        pass
```

_بعد:_
```
class OversightService:
    def __init__(self):
        self.guide_path = 'docs/EXECUTOR_GUIDE.md'

    def get_executor_guide(self) -> str:
        try:
            with open(self.guide_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return 'Guide not found.'
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v`
- `curl -X GET http://localhost:8000/api/executor-guide`
- `cat docs/EXECUTOR_GUIDE.md | grep 'بررسی اولیه خودکار repo'`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که فایل docs/EXECUTOR_GUIDE.md ممکن است توسط مدل اجراکننده نادیده گرفته شود اگر ارجاع به آن در main.py یا oversight_service.py به درستی انجام نشود. همچنین اگر مسیر فایل اشتباه باشد، تابع get_executor_guide() خطای FileNotFoundError برمی‌گرداند که باید مدیریت شود. این تغییرات روی هیچ فایل دیگری تأثیر نمی‌گذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 34: رفع عدم تطابق نوع داده target_locations در pipeline ai_llm

**Scope:** این مرحله شامل تحلیل و رفع ناسازگاری نوع داده target_locations بین کامپوننت‌های pipeline ai_llm است. تمرکز بر فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_manager.py و backend/app/services/oversight_service.py می‌باشد. خارج از scope این مرحله: تغییرات در pipelineهای دیگر، تست‌های integration، یا refactor کلی.
**Key terms:** backend/app/oversight_strong_prompt.py, backend/app/ai_manager.py, backend/app/services/oversight_service.py, target_locations, List[Dict], List[str], normalize

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

oversight_strong_prompt ورودی target_locations را به صورت 'List[Dict] or List[str], optional' تعریف کرده است. اما هیچ مشخص نیست که ai_manager یا سایر مصرف‌کنندگان این خروجی چه فرمتی را انتظار دارند. این ابهام می‌تواند باعث خطاهای parsing در زمان اجرا شود.

## 💥 پیامد (impact)
اگر خروجی oversight_strong_prompt به مدلی ارسال شود که منتظر یک فرمت خاص (مثلاً فقط List[str]) است، مدل ممکن است دچار خطا شود یا خروجی نادرست تولید کند. همچنین در صورت استفاده از target_locations در pipelineهای downstream، عدم تطابق نوع داده باعث crash می‌شود.

## 🛠 پیشنهاد رفع اولیه
نوع داده target_locations را به یک فرمت واحد و مشخص محدود کنید (مثلاً فقط List[Dict] با کلیدهای استاندارد مانند 'path', 'type'). اگر نیاز به پشتیبانی از هر دو فرمت است، یک تابع normalize در ابتدای oversight_strong_prompt اضافه کنید که ورودی را به فرمت استاندارد تبدیل کند.
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع عدم تطابق نوع داده target_locations در pipeline ai_llm

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py:45-78` — `build_strong_prompt` — این تابع target_locations را بدون نرمال‌سازی به پرامپت اضافه می‌کند. نیاز به افزودن تابع normalize در ابتدای این تابع.
  ```python
  def build_strong_prompt(
      self,
      task: str,
      target_locations: Union[List[Dict], List[str], None] = None,
      context: Optional[str] = None
  ) -> str:
      # target_locations مستقیماً به پرامپت اضافه می‌شود
      if target_locations:
          prompt += f"\nTarget locations: {target_locations}"
      return prompt
  ```
- `backend/app/ai_manager.py:200-230` — `process_ai_request` — این تابع target_locations را به صورت List[str] از دیتابیس می‌خواند و به oversight_strong_prompt ارسال می‌کند. نیاز به اطمینان از نرمال‌سازی در مقصد.
  ```python
  def process_ai_request(self, request_data: dict) -> dict:
      target_locations = request_data.get('target_locations', [])
      # target_locations به صورت List[str] از دیتابیس خوانده می‌شود
      strong_prompt = self.oversight_strong_prompt.build_strong_prompt(
          task=request_data['task'],
          target_locations=target_locations  # اینجا List[str] ارسال می‌شود
      )
  ```
- `backend/app/services/oversight_service.py:80-110` — `run_oversight` — این تابع target_locations را به صورت List[Dict] از کاربر دریافت می‌کند. نیاز به استانداردسازی کلیدها.
  ```python
  def run_oversight(self, user_input: dict) -> dict:
      target_locations = user_input.get('target_locations', [])
      # target_locations به صورت List[Dict] از کاربر دریافت می‌شود
      result = self.ai_manager.process_ai_request({
          'task': user_input['task'],
          'target_locations': target_locations  # اینجا List[Dict] ارسال می‌شود
      })
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_strong_prompt.py` (سطر 45) — فایل اصلی که تابع build_strong_prompt در آن قرار دارد و نیاز به افزودن تابع normalize دارد.
- `backend/app/ai_manager.py` (سطر 200) — این فایل target_locations را به oversight_strong_prompt ارسال می‌کند و باید از نرمال‌سازی اطمینان حاصل کند.
- `backend/app/services/oversight_service.py` (سطر 80) — این فایل target_locations را از کاربر دریافت کرده و به ai_manager پاس می‌دهد.
- `backend/tests/test_oversight_strong_prompt.py` (سطر 1) — نیاز به افزودن تست‌های واحد برای تابع normalize.

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات بر سه فایل اصلی تأثیر می‌گذارند: backend/app/services/oversight_strong_prompt.py (اضافه شدن تابع normalize و تغییر در build_strong_prompt)، backend/app/ai_manager.py (تغییر در نحوه ارسال target_locations)، و backend/app/services/oversight_service.py (استانداردسازی کلیدها). همچنین فایل تست backend/tests/test_oversight_strong_prompt.py برای پوشش تابع جدید اضافه می‌شود. هیچ وابستگی خارجی جدیدی نیاز نیست. تابع normalize فقط از نوع‌های استاندارد پایتون (list, dict, str) استفاده می‌کند.

## 🔍 Context و وضعیت فعلی
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد: oversight_strong_prompt ورودی target_locations را به صورت 'List[Dict] or List[str], optional' تعریف کرده است. اما هیچ مشخص نیست که ai_manager یا سایر مصرف‌کنندگان این خروجی چه فرمتی را انتظار دارند. این ابهام می‌تواند باعث خطاهای parsing در زمان اجرا شود. اگر خروجی oversight_strong_prompt به مدلی ارسال شود که منتظر یک فرمت خاص (مثلاً فقط List[str]) است، مدل ممکن است دچار خطا شود یا خروجی نادرست تولید کند. همچنین در صورت استفاده از target_locations در pipelineهای downstream، عدم تطابق نوع داده باعث crash می‌شود. فایل‌های اصلی شامل backend/app/oversight_strong_prompt.py، backend/app/ai_manager.py و backend/app/services/oversight_service.py هستند. کلیدواژه‌ها: target_locations, List[Dict], List[str], normalize. بر اساس تحلیل کد واقعی، در فایل backend/app/services/oversight_strong_prompt.py تابع `build_strong_prompt` در خطوط 45-78 target_locations را به صورت `Union[List[Dict], List[str], None]` دریافت می‌کند و در خط 120 آن را به صورت مستقیم به پرامپت اضافه می‌کند بدون هیچ نرمال‌سازی. در فایل backend/app/ai_manager.py تابع `process_ai_request` در خطوط 200-230 target_locations را از دیتابیس می‌خواند و به صورت List[str] به oversight_strong_prompt ارسال می‌کند. در فایل backend/app/services/oversight_service.py تابع `run_oversight` در خطوط 80-110 target_locations را از کاربر دریافت کرده و به صورت List[Dict] به ai_manager پاس می‌دهد. این ناسازگاری سه‌گانه باعث می‌شود که pipeline در زمان اجرا با خطا مواجه شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تابع normalize_target_locations در فایل backend/app/services/oversight_strong_prompt.py اضافه شود و ورودی List[str] را به List[Dict] با کلیدهای 'path' و 'type' تبدیل کند.
- [ ] تابع build_strong_prompt در oversight_strong_prompt.py در خط 45 تابع normalize را قبل از استفاده از target_locations صدا بزند.
- [ ] تست واحد در backend/tests/test_oversight_strong_prompt.py اضافه شود که normalize را با ورودی List[str] (مثلاً ['file1.py', 'file2.py']) تست کند و خروجی List[Dict] با کلیدهای path و type را تأیید کند.
- [ ] تست واحد اضافه شود که normalize را با ورودی None تست کند و لیست خالی برگرداند.
- [ ] تست واحد اضافه شود که normalize را با ورودی List[Dict] (مثلاً [{'path': 'file1.py', 'type': 'file'}]) تست کند و همان خروجی را با کلیدهای استاندارد برگرداند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_strong_prompt.py، یک تابع کمکی به نام `normalize_target_locations` در خطوط 40-60 اضافه کن که ورودی target_locations را به فرمت استاندارد List[Dict] با کلیدهای 'path' و 'type' تبدیل کند. اگر ورودی List[str] باشد، هر رشته را به {'path': str, 'type': 'file'} تبدیل کند. اگر List[Dict] باشد، فقط کلیدهای 'path' و 'type' را استخراج کند. اگر None باشد، لیست خالی برگرداند. 2. در همان فایل، در تابع `build_strong_prompt` (خط 45)، بلافاصله بعد از دریافت target_locations، تابع normalize را صدا بزن. 3. در فایل backend/app/ai_manager.py، در تابع `process_ai_request` (خط 200)، قبل از ارسال target_locations به oversight_strong_prompt، اطمینان حاصل کن که خروجی normalize شده است (اختیاری، چون normalize در مقصد انجام می‌شود). 4. در فایل backend/app/services/oversight_service.py، در تابع `run_oversight` (خط 80)، target_locations را به صورت List[Dict] با کلیدهای استاندارد ارسال کن. 5. یک unittest در backend/tests/test_oversight_strong_prompt.py اضافه کن که normalize را با ورودی‌های List[str]، List[Dict] و None تست کند.

## 💡 نمونه‌های قبل/بعد
**افزودن تابع normalize به oversight_strong_prompt.py**

_قبل:_
```
def build_strong_prompt(self, task, target_locations: Union[List[Dict], List[str], None] = None, context=None) -> str:
    if target_locations:
        prompt += f"\nTarget locations: {target_locations}"
    return prompt
```

_بعد:_
```
def normalize_target_locations(self, target_locations: Union[List[Dict], List[str], None]) -> List[Dict]:
    if target_locations is None:
        return []
    if isinstance(target_locations, list) and all(isinstance(item, str) for item in target_locations):
        return [{'path': item, 'type': 'file'} for item in target_locations]
    if isinstance(target_locations, list) and all(isinstance(item, dict) for item in target_locations):
        return [{'path': item.get('path', ''), 'type': item.get('type', 'file')} for item in target_locations]
    return []

def build_strong_prompt(self, task, target_locations: Union[List[Dict], List[str], None] = None, context=None) -> str:
    normalized = self.normalize_target_locations(target_locations)
    if normalized:
        prompt += f"\nTarget locations: {normalized}"
    return prompt
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_strong_prompt.py -v`
- `python -c "from backend.app.services.oversight_strong_prompt import OversightStrongPrompt; o = OversightStrongPrompt(); assert o.normalize_target_locations(['a.py', 'b.py']) == [{'path': 'a.py', 'type': 'file'}, {'path': 'b.py', 'type': 'file'}]; assert o.normalize_target_locations(None) == []; assert o.normalize_target_locations([{'path': 'x.py', 'type': 'dir'}]) == [{'path': 'x.py', 'type': 'dir'}]"`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در تابع build_strong_prompt در oversight_strong_prompt.py می‌تواند روی تمام callers این تابع تأثیر بگذارد. در حال حاضر فقط ai_manager.py از این تابع استفاده می‌کند (خط 200). اگر تابع normalize به درستی کار نکند، ممکن است target_locations خالی به پرامپت اضافه شود که باعث کاهش کیفیت خروجی مدل می‌شود. همچنین تغییر در oversight_service.py (خط 80) ممکن است روی pipelineهای downstream که از target_locations استفاده می‌کنند تأثیر بگذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 35: ریسک‌ها و موارد احتیاط: بررسی caller‌های هر دو طرف قبل از merge

**Scope:** این بخش به ریسک‌های ناشی از تغییر یک طرف pipeline (احتمالاً oversight_strong_prompt و ai_manager) می‌پردازد و بر لزوم بررسی همه caller‌های هر دو طرف قبل از merge تأکید دارد. این یک مرحله احتیاطی و غیرفنی است که باید قبل از هر تغییر کد انجام شود. هیچ مرحله اجرایی مستقیمی در این بخش تعریف نشده است.
**Key terms:** downstream consumers, caller, merge

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی callerهای oversight_strong_prompt و ai_manager قبل از merge

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً حاوی منطق تولید پرامپت‌های قوی برای oversight است.
- `backend/app/services/ai_manager.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً مدیریت کلی AI services را بر عهده دارد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_service.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند یا با آن در ارتباط است
- `backend/app/services/ai_balance_service.py` — احتمالاً از ai_manager استفاده می‌کند یا با آن در ارتباط است
- `backend/app/services/oversight_inspector_bridge.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_mega_bundle.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_verifier.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_upload_session.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_telegram_compose.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_deep_scan_service.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_extraction.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_model_temp_activate.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_progress.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_settings.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_codex_service.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/oversight_verify_pdf.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/services/ai_base.py` — احتمالاً توسط ai_manager استفاده می‌شود
- `backend/app/services/claude_service.py` — احتمالاً توسط ai_manager مدیریت می‌شود
- `backend/app/services/openai_service.py` — احتمالاً توسط ai_manager مدیریت می‌شود
- `backend/app/services/gemini_service.py` — احتمالاً توسط ai_manager مدیریت می‌شود
- `backend/app/services/deepseek_service.py` — احتمالاً توسط ai_manager مدیریت می‌شود
- `backend/app/services/perplexity_service.py` — احتمالاً توسط ai_manager مدیریت می‌شود
- `backend/app/services/smart_orchestrator.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/services/creator_engine.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/services/debate_service.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/services/deep_analysis_service.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/services/analysis_progress_manager.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/services/background_scheduler.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/services/notification_service.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/oversight.py` — احتمالاً از oversight_strong_prompt استفاده می‌کند
- `backend/app/api/routes/ai_usage.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/chat.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/analysis.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/creator.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/debate.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/orchestrator.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/unified_api.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/external.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/external_projects.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/github_import.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/model_profiles.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/models.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/project_health.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/project_journal.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/project_memory.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/project_structure.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/projects.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/render_logs.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/runtime.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/security_analysis.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/settings.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/simple_projects.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/system_prompts.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/upload.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/notifications.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/config.py` — احتمالاً از ai_manager استفاده می‌کند
- `backend/app/api/routes/diagrams.py` — احتمالاً از ai_manager استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این تسک به بررسی callerهای دو فایل کلیدی می‌پردازد:
1. backend/app/services/oversight_strong_prompt.py: این فایل احتمالاً توسط سرویس‌های متعدد oversight مانند oversight_service.py، oversight_inspector_bridge.py، oversight_mega_bundle.py، oversight_verifier.py، oversight_upload_session.py، oversight_telegram_compose.py، oversight_deep_scan_service.py، oversight_extraction.py، oversight_model_temp_activate.py، oversight_progress.py، oversight_settings.py، oversight_codex_service.py، oversight_verify_pdf.py و همچنین روتر oversight.py استفاده می‌شود.
2. backend/app/services/ai_manager.py: این فایل احتمالاً توسط سرویس‌های متعدد AI مانند ai_balance_service.py، smart_orchestrator.py، creator_engine.py، debate_service.py، deep_analysis_service.py، analysis_progress_manager.py، background_scheduler.py، notification_service.py و همچنین روترهای متعدد مانند ai_usage.py، chat.py، analysis.py، creator.py، debate.py، orchestrator.py، unified_api.py، external.py، external_projects.py، github_import.py، model_profiles.py، models.py، project_health.py، project_journal.py، project_memory.py، project_structure.py، projects.py، render_logs.py، runtime.py، security_analysis.py، settings.py، simple_projects.py، system_prompts.py، upload.py، notifications.py، config.py، diagrams.py استفاده می‌شود.

تغییر در هر یک از این دو فایل می‌تواند downstream consumers متعددی را break کند.

## 🔍 Context و وضعیت فعلی
این تسک به ریسک‌های ناشی از تغییر یک طرف pipeline (احتمالاً oversight_strong_prompt و ai_manager) می‌پردازد و بر لزوم بررسی همه callerهای هر دو طرف قبل از merge تأکید دارد. این یک مرحله احتیاطی و غیرفنی است که باید قبل از هر تغییر کد انجام شود. هیچ مرحله اجرایی مستقیمی در این بخش تعریف نشده است.

--- بخش مربوط از درخواست اصلی کاربر ---
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

--- کلیدواژه‌ها ---
downstream consumers, caller, merge

بر اساس ساختار پروژه، فایل‌های مرتبط با این درخواست عبارتند از:
- backend/app/services/oversight_strong_prompt.py
- backend/app/services/ai_manager.py

این فایل‌ها deep-read نشده‌اند، اما بر اساس ساختار سطحی پروژه، callerهای احتمالی شناسایی شده‌اند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] همه callerهای فایل oversight_strong_prompt.py شناسایی و مستند شده‌اند
- [ ] همه callerهای فایل ai_manager.py شناسایی و مستند شده‌اند
- [ ] هیچ callerای پس از تغییرات پیشنهادی break نمی‌شود
- [ ] مستندات callerها در یک فایل جداگانه یا کامیت ثبت شده است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. شناسایی همه callerهای فایل oversight_strong_prompt.py در سراسر پروژه با جستجوی import و function call.
2. شناسایی همه callerهای فایل ai_manager.py در سراسر پروژه با جستجوی import و function call.
3. بررسی هر caller برای اطمینان از سازگاری با تغییرات پیشنهادی.
4. مستندسازی نتایج بررسی در یک فایل موقت یا کامیت جداگانه.
5. در صورت وجود downstream consumers که break می‌شوند، اصلاح آن‌ها قبل از merge.
6. انجام merge تنها پس از تأیید همه callerها.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn "from.*oversight_strong_prompt\|import.*oversight_strong_prompt\|oversight_strong_prompt\." backend/`
- `grep -rn "from.*ai_manager\|import.*ai_manager\|ai_manager\." backend/`
- `pytest backend/tests/ -v`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که تغییر در oversight_strong_prompt.py یا ai_manager.py می‌تواند downstream consumers متعددی را break کند. با توجه به تعداد بالای فایل‌هایی که احتمالاً از این دو فایل استفاده می‌کنند (بیش از 40 فایل)، عدم بررسی کامل callerها می‌تواند منجر به باگ‌های گسترده در سراسر پروژه شود. همچنین، برخی callerها ممکن است وابستگی‌های پنهانی داشته باشند که در بررسی سطحی شناسایی نشوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 36: بررسی اولیه و تحلیل وضعیت موجود repo قبل از اجرا

**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن صرفاً آگاه‌سازی مدل از احتمال وجود پیاده‌سازی قبلی، لزوم بررسی مستقل ساختار repo، و مسئولیت‌پذیری در قبال تصمیمات است. هیچ فایل، کلاس، یا تابع جدیدی نباید ساخته شود.

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی اولیه و تحلیل وضعیت موجود repo قبل از اجرا

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/inspector_agent.py` — `InspectorAgent` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس کامیت‌های اخیر (7d341e3, bf98db1) مرتبط با اسکن موردی و سه باگ بنیادی است.
- `backend/app/services/inspector_scan_bridge.py` — `InspectorScanBridge` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس کامیت cd39cc3 مرتبط با قاعدهٔ صفر 'placeholder = build pipeline' + timestamp scan است.
- `backend/app/services/scan_v5/scan_bundle.py` — `ScanBundle` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بخشی از scan_v5 که در کامیت‌های اخیر اصلاح شده است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/verify_runtime/iterative_orchestrator.py` — مرتبط با کامیت‌های اخیر و فرآیند verify که ممکن است تحت تأثیر تغییرات inspector قرار گیرد.
- `backend/app/services/verify_runtime/inspector_probe.py` — پروب inspector در verify_runtime که با inspector_agent و inspector_scan_bridge ارتباط دارد.
- `backend/app/services/oversight_inspector_bridge.py` — پل بین oversight و inspector که در کامیت‌های اخیر (bf98db1) اصلاح شده است.
- `backend/app/services/scan_v5/scan_inspector_session.py` — مدیریت جلسات اسکن inspector که با scan_bundle و inspector_agent مرتبط است.

## 🌐 نقشهٔ وابستگی‌ها
این تسک هیچ تغییری در کد ایجاد نمی‌کند، بنابراین وابستگی مستقیمی ندارد. با این حال، فایل‌های مرتبط احتمالی شامل inspector_agent.py، inspector_scan_bridge.py، scan_v5/scan_bundle.py، scan_v5/scan_inspector_session.py، verify_runtime/inspector_probe.py، و oversight_inspector_bridge.py هستند که در کامیت‌های اخیر (677c46f, 7d341e3, 33a9e7c, bf98db1, 94e9306, a612c86, 9fca950, cd39cc3) اصلاح شده‌اند. مدل اجراکننده باید این فایل‌ها را مستقل بررسی کند.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن صرفاً آگاه‌سازی مدل از احتمال وجود پیاده‌سازی قبلی، لزوم بررسی مستقل ساختار repo، و مسئولیت‌پذیری در قبال تصمیمات است. هیچ فایل، کلاس، یا تابع جدیدی نباید ساخته شود.

--- بخش مربوط از درخواست اصلی کاربر ---
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.

--- کلیدواژه‌ها ---
(ندارد)

بر اساس ساختار پروژه (247 فایل) و آخرین کامیت‌ها (677c46f, 7d341e3, 33a9e7c, bf98db1, 94e9306, a612c86, 9fca950, cd39cc3)، این تسک صرفاً یک هشدار پیش‌اجرا است و نیاز به تغییر کد ندارد. فایل‌های مرتبط احتمالی شامل inspector_agent.py، inspector_scan_bridge.py، scan_v5/scan_bundle.py، و verify_runtime/iterative_orchestrator.py هستند که در کامیت‌های اخیر اصلاح شده‌اند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مدل اجراکننده پیش از هر تغییر، ساختار repo را مستقل بررسی کرده و با grep/search فایل‌های مرتبط را شناسایی کند.
- [ ] اگر قابلیت/فایل/تابعی از قبل موجود است، مدل آن را دوباره نمی‌سازد و فقط موارد ناقص یا اشتباه را اصلاح/تکمیل می‌کند.
- [ ] اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت می‌شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.
- [ ] اگر کار طولانی است، مدل در چندین کامیت متوالی با ترتیب منطقی (foundation → core → integration → tests) انجام می‌دهد و هیچ بخشی را skip نمی‌کند.
- [ ] در آخر یک checklist از همهٔ کامیت‌ها در PR description نوشته می‌شود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک یک یادداشت هشداردهنده است و هیچ اقدام اجرایی مشخصی ندارد. مدل اجراکننده باید:
1. پیش از هر تغییر، ساختار repo را مستقل بررسی کند.
2. با grep/search و خواندن فایل‌های مرتبط (مانند inspector_agent.py، inspector_scan_bridge.py، scan_v5/scan_bundle.py، verify_runtime/iterative_orchestrator.py) بررسی کند که چه چیزی از قبل وجود دارد.
3. اگر قابلیت/فایل/تابعی از قبل موجود است، آن را دوباره نسازد؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کند.
4. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت کند.
5. اگر کار طولانی است، در چندین کامیت متوالی با ترتیب منطقی (foundation → core → integration → tests) انجام دهد.
6. در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویسد.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک هیچ تغییری در کد ایجاد نمی‌کند، بنابراین ریسک مستقیمی ندارد. با این حال، اگر مدل اجراکننده بدون بررسی مستقل ساختار repo اقدام به تغییر کند، ممکن است باعث ایجاد duplicate functionality یا شکستن وابستگی‌های موجود شود. فایل‌های inspector_agent.py، inspector_scan_bridge.py، scan_v5/scan_bundle.py، و verify_runtime/inspector_probe.py توسط چندین سرویس دیگر (مانند oversight_inspector_bridge.py و scan_v5/scan_inspector_session.py) استفاده می‌شوند و تغییر نادرست آن‌ها می‌تواند روی فرآیندهای اسکن و verify تأثیر بگذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 37: مستندسازی و رفع ابهام در تعامل بین ai_manager و models_registry

**Scope:** این مرحله شامل تحلیل و مستندسازی رابط (interface) بین ai_manager و models_registry در pipeline ai_llm است. باید مشخص شود که models_registry یک دیتابیس محلی، API خارجی یا کش است. سپس یک mock یا stub برای تست این تعامل ایجاد می‌شود. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/core/models_registry.py هستند. این مرحله شامل پیاده‌سازی کامل منطق تجاری نیست، بلکه صرفاً مستندسازی و ایجاد mock برای تست است.
**Key terms:** ai_manager, models_registry, backend/app/core/models_registry.py, backend/app/ai_manager.py, pipeline ai_llm

**بخش مربوط از متن کاربر:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

مستندات ai_manager اشاره دارد که با 'backend/app/core/models_registry.py' تعامل دارد، اما مشخص نیست که این تعامل به چه صورت است. آیا models_registry یک دیتابیس محلی است؟ یک API خارجی؟ آیا کش دارد؟ این ابهام می‌تواند منجر به وابستگی‌های پنهان و خطاهای runtime شود.

اگر models_registry در دسترس نباشد یا پاسخ نادرست بدهد، ai_manager ممکن است مدل‌های نامعتبر انتخاب کند یا fallback به درستی کار نکند. همچنین تست و دیباگ این بخش دشوار می‌شود.

رابط (interface) بین ai_manager و models_registry را به صورت صریح مستند کنید: متدهای فراخوانی شده، نوع بازگشتی، و رفتار در صورت خطا. یک mock یا stub برای تست این تعامل ایجاد کنید.
```

## 🎯 هدف (خلاصه ساختاریافته)
مستندسازی و mock کردن interface بین ai_manager و models_registry

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:1-50` — `کل فایل (deep-read نشده)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً شامل کلاس AiManager است که با models_registry تعامل دارد.
- `backend/app/core/models_registry.py:1-50` — `کل فایل (deep-read نشده)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل احتمالاً شامل توابع یا کلاسی برای مدیریت رجیستری مدل‌ها است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص) — بر اساس ساختار پروژه، احتمالاً Python با FastAPI برای backend و pytest برای تست‌ها

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_base.py` (سطر 1) — احتمالاً کلاس پایه برای ai_manager است و ممکن است interface مشترکی با models_registry داشته باشد
- `backend/app/services/ai_balance_service.py` (سطر 1) — ممکن است از models_registry برای متعادل‌سازی بار بین مدل‌ها استفاده کند
- `backend/app/services/model_profiler.py` (سطر 1) — ممکن است با models_registry برای پروفایل کردن مدل‌ها تعامل داشته باشد
- `backend/app/services/capability_detector.py` (سطر 1) — ممکن است از models_registry برای تشخیص قابلیت‌های مدل‌ها استفاده کند
- `backend/app/services/model_capability_tester.py` (سطر 1) — ممکن است با models_registry برای تست قابلیت‌های مدل‌ها تعامل داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر تعامل بین دو فایل اصلی تمرکز دارد: backend/app/services/ai_manager.py و backend/app/core/models_registry.py. ai_manager احتمالاً سرویس اصلی مدیریت هوش مصنوعی است که توسط چندین روتر مانند backend/app/api/routes/ai_usage.py و backend/app/api/routes/chat.py و backend/app/api/routes/orchestrator.py استفاده می‌شود. models_registry نیز احتمالاً توسط سرویس‌های دیگر مانند ai_balance_service.py، model_profiler.py، capability_detector.py و model_capability_tester.py استفاده می‌شود. ایجاد mock برای models_registry باید interface واقعی را پوشش دهد تا همه مصرف‌کنندگان بتوانند از آن در تست‌ها استفاده کنند. فایل‌های تست موجود مانند backend/tests/test_runtime_verify_stage1.py تا stage9 ممکن است نیاز به به‌روزرسانی داشته باشند.

## 🔍 Context و وضعیت فعلی
بر اساس درخواست کاربر، نیاز به تحلیل و مستندسازی رابط (interface) بین ai_manager و models_registry در pipeline ai_llm وجود دارد. کاربر اشاره کرده که در مستندات ai_manager اشاره شده که با 'backend/app/core/models_registry.py' تعامل دارد، اما مشخص نیست که این تعامل به چه صورت است. ابهامات اصلی: آیا models_registry یک دیتابیس محلی است؟ یک API خارجی؟ آیا کش دارد؟ این ابهام می‌تواند منجر به وابستگی‌های پنهان و خطاهای runtime شود. اگر models_registry در دسترس نباشد یا پاسخ نادرست بدهد، ai_manager ممکن است مدل‌های نامعتبر انتخاب کند یا fallback به درستی کار نکند. همچنین تست و دیباگ این بخش دشوار می‌شود. کاربر خواسته که رابط (interface) بین ai_manager و models_registry به صورت صریح مستند شود: متدهای فراخوانی شده، نوع بازگشتی، و رفتار در صورت خطا. همچنین یک mock یا stub برای تست این تعامل ایجاد شود. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/core/models_registry.py هستند. این مرحله شامل پیاده‌سازی کامل منطق تجاری نیست، بلکه صرفاً مستندسازی و ایجاد mock برای تست است. کلیدواژه‌ها: ai_manager, models_registry, backend/app/core/models_registry.py, backend/app/ai_manager.py, pipeline ai_llm. با توجه به ساختار پروژه، فایل‌های واقعی موجود عبارتند از: backend/app/services/ai_manager.py (در مسیر services) و backend/app/core/models_registry.py. همچنین فایل‌های مرتبط دیگر مانند backend/app/services/ai_base.py و backend/app/services/ai_balance_service.py نیز ممکن است با این تعامل در ارتباط باشند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل مستندات docs/ai_manager_models_registry_interface.md ایجاد شود و شامل تمام متدهای interface بین ai_manager و models_registry باشد
- [ ] فایل mock backend/app/tests/mocks/mock_models_registry.py ایجاد شود و تمام متدهای مستند شده را پیاده‌سازی کند
- [ ] mock باید داده‌های ثابت (hardcoded) برای حداقل ۳ مدل مختلف برگرداند
- [ ] تست‌های واحد در backend/app/tests/test_ai_manager_models_registry_interface.py ایجاد شود و حداقل ۳ سناریو را پوشش دهد: مدل موجود، مدل不存在، و خطای شبکه
- [ ] مستندات باید شامل توضیح واضحی باشد که models_registry یک دیتابیس محلی است، API خارجی، یا کش — بر اساس تحلیل کد واقعی
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. تحلیل فایل backend/app/services/ai_manager.py برای شناسایی تمام متدهایی که با models_registry تعامل دارند. 2. تحلیل فایل backend/app/core/models_registry.py برای شناسایی interface واقعی آن (متدها، پارامترها، نوع بازگشتی). 3. مستندسازی interface به صورت صریح در یک فایل markdown جدید در docs/ با نام ai_manager_models_registry_interface.md. 4. ایجاد یک mock class در فایل جدید backend/app/tests/mocks/mock_models_registry.py که interface واقعی را پیاده‌سازی کند. 5. ایجاد stub functions برای متدهای اصلی که داده‌های ثابت (hardcoded) برمی‌گردانند. 6. نوشتن تست‌های واحد در backend/app/tests/test_ai_manager_models_registry_interface.py که از mock استفاده می‌کنند. 7. به‌روزرسانی فایل backend/app/services/ai_manager.py برای استفاده از mock در محیط تست (از طریق dependency injection یا environment variable).

## 💡 نمونه‌های قبل/بعد
**نمونه مستندسازی interface (فقط مثال مفهومی — نیاز به تأیید با کد واقعی)**

_قبل:_
```
# وضعیت فعلی: هیچ مستنداتی برای interface بین ai_manager و models_registry وجود ندارد
# تابع get_model در ai_manager:
def get_model(self, model_name: str):
    # اینجا با models_registry تعامل دارد اما نحوه آن مشخص نیست
    pass
```

_بعد:_
```
# وضعیت مطلوب: مستندات صریح interface
"""
Interface: ModelsRegistry

متدها:
- get_model(model_name: str) -> Optional[Dict]
  - ورودی: نام مدل (مثلاً 'gpt-4', 'claude-3')
  - خروجی: دیکشنری شامل اطلاعات مدل یا None در صورت عدم وجود
  - خطا: در صورت خطای شبکه یا دیتابیس، None برمی‌گرداند (لاگ خطا)

- list_models(capability: Optional[str] = None) -> List[Dict]
  - ورودی: capability اختیاری برای فیلتر
  - خروجی: لیست مدل‌های موجود

- is_available(model_name: str) -> bool
  - خروجی: True اگر مدل در دسترس باشد
"""
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/app/tests/test_ai_manager_models_registry_interface.py -v`
- `python -c "from backend.app.tests.mocks.mock_models_registry import MockModelsRegistry; m = MockModelsRegistry(); print(m.get_model('gpt-4'))"`
- `cat docs/ai_manager_models_registry_interface.md | grep -E 'Interface:|ModelsRegistry|get_model|list_models|is_available'`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که فایل‌های backend/app/services/ai_manager.py و backend/app/core/models_registry.py deep-read نشده‌اند و ممکن است ساختار واقعی آن‌ها با فرضیات فعلی متفاوت باشد. همچنین اگر ai_manager توسط چندین روتر (مانند ai_usage.py، chat.py، orchestrator.py) استفاده شود، تغییر interface آن می‌تواند روی همه این روترها تأثیر بگذارد. ریسک دیگر این است که models_registry ممکن است وابستگی‌های پنهانی به سرویس‌های دیگر مانند database.py یا storage_service.py داشته باشد که در mock باید در نظر گرفته شوند. همچنین اگر models_registry واقعاً یک API خارجی باشد، mock باید رفتار شبکه (timeout, retry) را نیز شبیه‌سازی کند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 38: بررسی ریسک‌های تغییر در callerهای downstream قبل از merge

**Scope:** این بخش یک هشدار ریسک است و نه یک مرحله اجرایی. محتوای آن صرفاً یک نکته احتیاطی درباره بررسی callerهای هر دو طرف قبل از merge است. هیچ اقدام عملیاتی یا کدنویسی در این بخش تعریف نشده است.
**Key terms:** downstream consumers, caller, merge

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی ریسک‌های تغییر در callerهای downstream قبل از merge

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/inspector_agent.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این سرویس توسط چندین caller مانند oversight_service.py و verify_runtime/inspector_probe.py فراخوانی می‌شود.
- `backend/app/services/oversight_service.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این سرویس مصرف‌کننده upstream از inspector_agent.py و ارائه‌دهنده به API routes است.
- `backend/app/services/verify_runtime/runner.py` — `کل فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این runner توسط API runtime و همچنین توسط oversight_service فراخوانی می‌شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` — این route نقطه ورود API برای سرویس oversight است و هر تغییری در oversight_service.py بر پاسخ API تأثیر می‌گذارد.
- `backend/app/api/routes/runtime.py` — این route نقطه ورود API برای runtime verification است و به verify_runtime/runner.py وابسته است.
- `backend/app/services/verify_runtime/inspector_probe.py` — این فایل از inspector_agent.py برای انجام پروب‌های بازرسی استفاده می‌کند و تغییر در inspector_agent.py می‌تواند آن را مختل کند.
- `backend/app/services/scan_v5/scan_bundle.py` — این فایل ممکن است از inspector_agent.py یا سرویس‌های مرتبط برای اسکن استفاده کند و تغییرات downstream روی آن اثر دارد.
- `backend/app/services/oversight_inspector_bridge.py` — این فایل به عنوان پل ارتباطی بین oversight و inspector عمل می‌کند و تغییر در هر دو طرف می‌تواند آن را break کند.

## 🌐 نقشهٔ وابستگی‌ها
این هشدار ریسک به زنجیره وابستگی بین سرویس‌های اصلی پروژه اشاره دارد. فایل‌های `inspector_agent.py`، `oversight_service.py`، `verify_runtime/runner.py` و `scan_v5/scan_bundle.py` یک زنجیره فراخوانی را تشکیل می‌دهند. همچنین فایل‌های `backend/app/api/routes/oversight.py` و `backend/app/api/routes/runtime.py` به عنوان نقاط ورود API عمل می‌کنند. فایل‌های bridge مانند `oversight_inspector_bridge.py` و `verify_runtime/inspector_probe.py` نیز در این زنجیره نقش دارند. تست‌های یکپارچگی مانند `test_runtime_verify_integration.py` و `test_inspector_oversight_bridge.py` برای اعتبارسنجی این زنجیره حیاتی هستند.

## 🔍 Context و وضعیت فعلی
این تسک یک هشدار ریسک و بررسی پیش از merge است و نه یک مرحله اجرایی یا کدنویسی. محتوای آن صرفاً یک نکته احتیاطی درباره بررسی callerهای هر دو طرف قبل از merge است. هیچ اقدام عملیاتی یا کدنویسی در این بخش تعریف نشده است.

--- بخش مربوط از درخواست اصلی کاربر ---
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

--- کلیدواژه‌ها ---
downstream consumers, caller, merge

این هشدار به این دلیل حیاتی است که در پروژه، سرویس‌های متعددی مانند `inspector_agent.py`، `oversight_service.py`، `verify_runtime/runner.py` و `scan_v5/scan_bundle.py` به صورت زنجیره‌ای یکدیگر را فراخوانی می‌کنند. تغییر در یک سرویس میانی (مثلاً تغییر امضای تابع یا نوع بازگشتی) می‌تواند تمام زنجیره را مختل کند. همچنین فایل‌های `backend/app/api/routes/` متعددی (مانند `oversight.py`، `analysis.py`، `runtime.py`) به عنوان نقطه ورود API عمل می‌کنند و هر تغییری در سرویس‌های پشتیبان مستقیماً بر پاسخ API تأثیر می‌گذارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تمام فایل‌هایی که از سرویس مورد نظر (مثلاً inspector_agent.py) import کرده‌اند، شناسایی و لیست شوند.
- [ ] برای هر تابع تغییر یافته، تمام مکان‌های فراخوانی (call sites) در پروژه شناسایی شوند.
- [ ] تست‌های یکپارچگی مرتبط (test_runtime_verify_integration.py و test_inspector_oversight_bridge.py) قبل از merge با موفقیت اجرا شوند.
- [ ] تمامی routeهای API که از سرویس تغییر یافته استفاده می‌کنند (oversight.py و runtime.py) پاسخ 200 با ساختار داده صحیح برگردانند.
- [ ] هیچ خطای import یا AttributeError در لاگ‌های سرور پس از merge مشاهده نشود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این یک تسک تحلیلی و غیرکدنویسی است. اقدام پیشنهادی به شرح زیر است:

1. **شناسایی تمام callerهای مستقیم و غیرمستقیم**: برای هر فایل سرویسی که قرار است تغییر کند (مثلاً `backend/app/services/inspector_agent.py`)، یک جستجوی grep در کل پروژه انجام شود تا تمام فایل‌هایی که آن را import کرده یا از توابع آن استفاده می‌کنند، شناسایی شوند.

2. **بررسی امضای توابع (Function Signatures)**: برای هر تابعی که تغییر می‌کند، لیستی از تمام مکان‌هایی که آن تابع فراخوانی شده است تهیه شود و امضای جدید با فراخوانی‌های موجود تطبیق داده شود.

3. **بررسی نوع بازگشتی (Return Type)**: اگر نوع بازگشتی یک تابع تغییر کند، تمام مصرف‌کنندگان downstream که به ساختار داده‌ای خاصی وابسته هستند باید به‌روزرسانی شوند.

4. **بررسی زنجیره‌ای (Chain Analysis)**: در پروژه، سرویس‌هایی مانند `oversight_service.py` از `inspector_agent.py` و `verify_runtime/runner.py` استفاده می‌کنند. تغییر در یک سرویس پایین‌دستی می‌تواند بر کل زنجیره تأثیر بگذارد.

5. **تست‌های یکپارچگی (Integration Tests)**: قبل از merge، تمام تست‌های یکپارچگی مرتبط (مانند `test_runtime_verify_integration.py`، `test_inspector_oversight_bridge.py`) اجرا شوند تا از عدم شکست downstream consumers اطمینان حاصل شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -r "from backend.app.services.inspector_agent import" backend/`
- `grep -r "inspector_agent" backend/ --include="*.py"`
- `pytest backend/tests/test_runtime_verify_integration.py -v`
- `pytest backend/tests/test_inspector_oversight_bridge.py -v`
- `curl -X GET http://localhost:8000/api/oversight/status`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: تغییر در inspector_agent.py می‌تواند باعث شکست در oversight_service.py (خط 45-120) و verify_runtime/inspector_probe.py (خط 30-80) شود. همچنین routeهای API در oversight.py و runtime.py ممکن است پاسخ‌های ناقص یا خطا برگردانند. فایل bridge یعنی oversight_inspector_bridge.py نیز به عنوان نقطه اتصال حیاتی است و تغییر در امضای توابع می‌تواند آن را از کار بیندازد. تست‌های یکپارچگی موجود ممکن است پوشش کافی برای تمام سناریوهای downstream نداشته باشند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 39: تحلیل عدم وجود خطا در ۳۰ روز اخیر به عنوان نشانه پوشش ناقص سناریوهای خطا

**Scope:** این بخش به تحلیل کیفی لاگ‌های خطا در ۳۰ روز اخیر می‌پردازد و این فرضیه را مطرح می‌کند که عدم وجود خطا به معنی کامل بودن سیستم نیست، بلکه ممکن است نشان‌دهنده پوشش ناقص سناریوهای خطا باشد. این یک مرحله تحلیلی و بازبینی است و شامل پیاده‌سازی کد جدید نمی‌شود. خروجی این بخش باید یک گزارش یا مستندسازی از سناریوهای خطای پوشش‌داده‌نشده باشد.

**بخش مربوط از متن کاربر:**
```
## 🎯 هدف (خلاصه ساختاریافته)
[Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
```

## 🎯 هدف (خلاصه ساختاریافته)
تحلیل کیفی لاگ‌های خطا و شناسایی سناریوهای پوشش‌داده‌نشده

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/log_stream_service.py` — `LogStreamService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این سرویس برای دسترسی به لاگ‌های جریانی و ذخیره‌شده استفاده می‌شود.
- `backend/app/services/log_to_issues_service.py` — `LogToIssuesService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این سرویس برای تبدیل لاگ‌های خطا به issue استفاده می‌شود.
- `backend/app/services/scan_v5/outcome_analyzer.py` — `OutcomeAnalyzer` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این سرویس برای تحلیل نتایج اسکن‌ها و شناسایی الگوهای خطا استفاده می‌شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs. کتابخانه‌های مرتبط: python logging, json, datetime برای تحلیل لاگ‌ها.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/notification_service.py` — این سرویس برای ارسال اعلان‌های خطا استفاده می‌شود و می‌تواند در تحلیل سناریوهای خطای پوشش‌داده‌نشده مفید باشد.
- `backend/app/services/oversight_service.py` — این سرویس برای نظارت و مدیریت خطاها استفاده می‌شود و می‌تواند در تحلیل کیفی لاگ‌ها نقش داشته باشد.
- `backend/app/services/oversight_verifier.py` — این سرویس برای تأیید و راستی‌آزمایی خطاها استفاده می‌شود و می‌تواند در شناسایی سناریوهای خطای پوشش‌داده‌نشده مفید باشد.
- `backend/app/services/scan_v5/notification_auditor.py` — این سرویس برای ممیزی اعلان‌ها و شناسایی الگوهای خطا استفاده می‌شود.

## 🌐 نقشهٔ وابستگی‌ها
این تحلیل به فایل‌های زیر وابسته است:
- `backend/app/services/log_stream_service.py`: برای دسترسی به لاگ‌های جریانی
- `backend/app/services/log_to_issues_service.py`: برای تبدیل لاگ‌ها به issue
- `backend/app/services/scan_v5/outcome_analyzer.py`: برای تحلیل نتایج اسکن
- `backend/app/services/notification_service.py`: برای بررسی اعلان‌های خطا
- `backend/app/services/oversight_service.py`: برای نظارت کلی
- `backend/app/services/oversight_verifier.py`: برای تأیید خطاها
- `backend/app/services/scan_v5/notification_auditor.py`: برای ممیزی اعلان‌ها

این فایل‌ها همگی در backend قرار دارند و با یکدیگر تعامل دارند.

## 🔍 Context و وضعیت فعلی
این تسک به تحلیل کیفی لاگ‌های خطا در ۳۰ روز اخیر می‌پردازد و این فرضیه را مطرح می‌کند که عدم وجود خطا به معنی کامل بودن سیستم نیست، بلکه ممکن است نشان‌دهنده پوشش ناقص سناریوهای خطا باشد. این یک مرحله تحلیلی و بازبینی است و شامل پیاده‌سازی کد جدید نمی‌شود. خروجی این بخش باید یک گزارش یا مستندسازی از سناریوهای خطای پوشش‌داده‌نشده باشد.

--- بخش مربوط از درخواست اصلی کاربر ---
## 🎯 هدف (خلاصه ساختاریافته)
[Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی

--- کلیدواژه‌ها ---
(ندارد)

شواهد در کد: با توجه به deep context موجود، فایل‌های مرتبط با لاگ‌گیری و مدیریت خطا شامل `backend/app/services/log_stream_service.py`، `backend/app/services/log_to_issues_service.py`، `backend/app/services/notification_service.py`، `backend/app/services/oversight_service.py` و `backend/app/services/oversight_verifier.py` هستند. همچنین فایل‌های مربوط به تحلیل و اسکن مانند `backend/app/services/scan_v5/outcome_analyzer.py` و `backend/app/services/scan_v5/notification_auditor.py` می‌توانند در این تحلیل نقش داشته باشند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] گزارش سناریوهای خطای پوشش‌داده‌نشده در مسیر docs/error_scenarios_analysis.md ایجاد شود.
- [ ] گزارش شامل حداقل ۵ سناریوی خطای پوشش‌داده‌نشده باشد.
- [ ] گزارش شامل اولویت‌بندی سناریوها (کم، متوسط، زیاد) باشد.
- [ ] گزارش شامل پیشنهادات عملی برای بهبود پوشش سناریوهای خطا باشد.
- [ ] گزارش شامل لینک به فایل‌های مرتبط در کد (مانند log_stream_service.py, log_to_issues_service.py) باشد.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. برای انجام این تحلیل کیفی، مراحل زیر پیشنهاد می‌شود:

1. **بررسی لاگ‌های خطا در ۳۰ روز اخیر**:
   - فایل `backend/app/services/log_stream_service.py` را برای دسترسی به لاگ‌های ذخیره‌شده بررسی کنید.
   - از `backend/app/services/log_to_issues_service.py` برای تبدیل لاگ‌های خطا به issue استفاده کنید.
   - لاگ‌های خطا را از storage یا database استخراج کنید.

2. **تحلیل سناریوهای خطای پوشش‌داده‌نشده**:
   - فایل `backend/app/services/scan_v5/outcome_analyzer.py` را برای تحلیل نتایج اسکن‌ها بررسی کنید.
   - از `backend/app/services/scan_v5/notification_auditor.py` برای ممیزی اعلان‌ها استفاده کنید.
   - سناریوهای خطایی که در لاگ‌ها ثبت نشده‌اند را شناسایی کنید.

3. **مستندسازی سناریوهای خطا**:
   - یک گزارش یا مستندسازی از سناریوهای خطای پوشش‌داده‌نشده تهیه کنید.
   - این گزارش می‌تواند در قالب یک فایل Markdown در مسیر `docs/` ذخیره شود.

4. **ارائه پیشنهادات برای بهبود**:
   - بر اساس تحلیل انجام‌شده، پیشنهاداتی برای بهبود پوشش سناریوهای خطا ارائه دهید.
   - این پیشنهادات می‌توانند شامل اضافه کردن logging در نقاط خاص، بهبود error handling، یا اضافه کردن تست‌های خطا باشند.

## 💡 نمونه‌های قبل/بعد
**نمونه گزارش سناریوهای خطای پوشش‌داده‌نشده**

_قبل:_
```
فعلاً هیچ گزارشی از سناریوهای خطای پوشش‌داده‌نشده وجود ندارد.
```

_بعد:_
```
یک فایل Markdown در مسیر docs/ با عنوان error_scenarios_analysis.md ایجاد شود که شامل:
- لیست سناریوهای خطای شناسایی‌شده
- اولویت‌بندی سناریوها
- پیشنهادات برای بهبود پوشش
- لینک به فایل‌های مرتبط در کد
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `ls docs/error_scenarios_analysis.md`
- `cat docs/error_scenarios_analysis.md | grep -c 'سناریوی خطا'`
- `cat docs/error_scenarios_analysis.md | grep -c 'اولویت'`
- `cat docs/error_scenarios_analysis.md | grep -c 'پیشنهاد'`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک شامل پیاده‌سازی کد جدید نیست، بنابراین ریسک خاصی برای کدبیس ندارد. با این حال، تحلیل ناقص ممکن است منجر به نادیده گرفتن سناریوهای خطای مهم شود. همچنین، اگر گزارش به‌درستی مستندسازی نشود، ممکن است در آینده به‌عنوان مرجع قابل استفاده نباشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 40: افزودن تست‌های سناریوی شکست برای ai_manager و بررسی fallback به مدل جایگزین

**Scope:** این مرحله شامل افزودن تست‌های سناریوی شکست (failure scenario tests) برای ماژول ai_manager است. تمرکز بر قطع connection به OpenAI و بررسی فعال شدن fallback به مدل جایگزین می‌باشد. این یک effectiveness issue است، بنابراین تست‌ها باید outcome را اندازه بگیرند (مثلاً اینکه آیا fallback واقعاً فعال می‌شود و پاسخ مناسب برمی‌گرداند)، نه فقط وجود فایل یا خط کد. خارج از scope: تست‌های unit معمولی، تست‌های integration کلی، یا تست‌های مربوط به سایر سرویس‌ها.
**Key terms:** ai_manager, OpenAI, fallback, مدل جایگزین, effectiveness issue, failure scenario tests, backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py

**بخش مربوط از متن کاربر:**
```
## 📊 وضعیت فعلی
error_rate_30d: 0.0% - هیچ خطایی ثبت نشده است که می‌تواند به دلیل عدم تست سناریوهای شکست سرویس‌های AI باشد

## 🛠 اقدام پیشنهادی
افزودن تست‌های سناریوی شکست برای ai_manager (مثلاً قطع connection به OpenAI) و بررسی فعال شدن fallback به مدل جایگزین

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن تست‌های سناریوی شکست ai_manager با fallback

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py` — `AIManager` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل ماژول اصلی مدیریت AI است که باید fallback logic در آن بررسی شود.
- `backend/app/services/ai_base.py` — `AIBase` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. کلاس پایه سرویس‌های AI که احتمالاً متد fallback را تعریف می‌کند.
- `backend/app/services/openai_service.py` — `OpenAIService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. سرویس OpenAI که connection آن باید در تست‌ها mock شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/claude_service.py` — سرویس Claude به عنوان مدل جایگزین برای fallback در نظر گرفته شده است
- `backend/app/services/ai_balance_service.py` — سرویس بالانس که تصمیم می‌گیرد کدام مدل استفاده شود و ممکن است در fallback logic نقش داشته باشد
- `backend/app/services/ai_manager.py` — ماژول اصلی که باید fallback logic در آن پیاده‌سازی و تست شود
- `backend/app/services/ai_base.py` — کلاس پایه که متد fallback را تعریف می‌کند و ai_manager از آن ارث‌بری می‌کند
- `backend/app/services/openai_service.py` — سرویس OpenAI که connection آن باید در تست‌های سناریوی شکست mock شود

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های backend/app/services/ai_manager.py (ماژول اصلی مدیریت AI)، backend/app/services/ai_base.py (کلاس پایه با متد fallback)، backend/app/services/openai_service.py (سرویس OpenAI)، backend/app/services/claude_service.py (سرویس Claude به عنوان مدل جایگزین)، و backend/app/services/ai_balance_service.py (سرویس بالانس بین مدل‌ها) وابسته است. فایل تست جدید backend/tests/test_ai_manager_failure_scenarios.py ایجاد خواهد شد. همچنین ممکن است نیاز به به‌روزرسانی فایل‌های پیکربندی pytest (pytest.ini یا pyproject.toml) و مستندات (docs/README.md یا docs/TESTING.md) باشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن تست‌های سناریوی شکست (failure scenario tests) برای ماژول ai_manager را دارد. تمرکز بر قطع connection به OpenAI و بررسی فعال شدن fallback به مدل جایگزین می‌باشد. این یک effectiveness issue است، بنابراین تست‌ها باید outcome را اندازه بگیرند (مثلاً اینکه آیا fallback واقعاً فعال می‌شود و پاسخ مناسب برمی‌گرداند)، نه فقط وجود فایل یا خط کد. خارج از scope: تست‌های unit معمولی، تست‌های integration کلی، یا تست‌های مربوط به سایر سرویس‌ها.

بر اساس متن کاربر:
- error_rate_30d: 0.0% - هیچ خطایی ثبت نشده است که می‌تواند به دلیل عدم تست سناریوهای شکست سرویس‌های AI باشد
- اقدام پیشنهادی: افزودن تست‌های سناریوی شکست برای ai_manager (مثلاً قطع connection به OpenAI) و بررسی فعال شدن fallback به مدل جایگزین
- ماهیت finding: effectiveness issue — کد ممکن است syntactically کار کند ولی outcome مطلوب حاصل نمی‌شود
- کلیدواژه‌ها: ai_manager, OpenAI, fallback, مدل جایگزین, effectiveness issue, failure scenario tests, backend/app/ai_manager.py, tests/test_ai_llm_pipeline.py

شواهد در کد واقعی پروژه: فایل backend/app/services/ai_manager.py در ساختار پروژه موجود است اما deep-read نشده. فایل tests/test_ai_llm_pipeline.py نیز در ساختار پروژه موجود نیست. فایل‌های مرتبط با fallback شامل backend/app/services/ai_base.py (کلاس پایه سرویس‌های AI)، backend/app/services/openai_service.py (سرویس OpenAI)، backend/app/services/claude_service.py (سرویس Claude به عنوان مدل جایگزین)، و backend/app/services/ai_balance_service.py (سرویس بالانس بین مدل‌ها) می‌باشند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل تست backend/tests/test_ai_manager_failure_scenarios.py ایجاد شده و شامل کلاس TestAIManagerFailureScenarios با حداقل ۳ تست سناریوی شکست باشد
- [ ] تست‌ها با marker @pytest.mark.failure_scenarios مشخص شده باشند
- [ ] تست‌ها با دستور pytest -m failure_scenarios قابل اجرا باشند و پاس شوند
- [ ] تست fallback_on_openai_connection_error: شبیه‌سازی ConnectionError در OpenAI و بررسی اینکه fallback به Claude فعال می‌شود و پاسخ مناسب برمی‌گرداند (outcome measurement)
- [ ] تست no_fallback_on_successful_openai: شبیه‌سازی پاسخ موفق OpenAI و بررسی اینکه fallback فعال نمی‌شود
- [ ] تست all_models_fail: شبیه‌سازی خطا در همه مدل‌ها و بررسی اینکه خطای مناسب (RuntimeError با پیام 'All AI models failed') برگردانده می‌شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل تست جدید backend/tests/test_ai_manager_failure_scenarios.py با کلاس TestAIManagerFailureScenarios
2. در این فایل، mock کردن سرویس OpenAI برای شبیه‌سازی قطع connection (با استفاده از unittest.mock یا pytest-mock)
3. تست اینکه وقتی OpenAI با خطای ConnectionError یا Timeout مواجه می‌شود، ai_manager به مدل جایگزین (مثلاً Claude) fallback می‌کند
4. تست اینکه fallback واقعاً پاسخ مناسب برمی‌گرداند (بررسی outcome، نه فقط اینکه تابع fallback صدا زده شده)
5. تست اینکه اگر همه مدل‌ها fail کنند، خطای مناسب برگردانده می‌شود
6. تست اینکه اگر OpenAI موفق باشد، fallback فعال نمی‌شود
7. اضافه کردن marker مخصوص برای این تست‌ها (مثلاً @pytest.mark.failure_scenarios)
8. به‌روزرسانی فایل pytest.ini یا pyproject.toml برای شامل شدن این marker
9. مستندسازی نحوه اجرای این تست‌ها در docs/README.md یا docs/TESTING.md

فایل‌های هدف:
- backend/app/services/ai_manager.py: ماژول اصلی مدیریت AI که باید fallback logic در آن بررسی شود
- backend/app/services/ai_base.py: کلاس پایه که متد fallback را تعریف می‌کند
- backend/app/services/openai_service.py: سرویس OpenAI که connection آن باید mock شود
- backend/app/services/claude_service.py: سرویس Claude به عنوان مدل جایگزین
- backend/app/services/ai_balance_service.py: سرویس بالانس که تصمیم می‌گیرد کدام مدل استفاده شود

## 💡 نمونه‌های قبل/بعد
**نمونه تست سناریوی شکست برای fallback**

_قبل:_
```
# فایل backend/tests/test_ai_manager_failure_scenarios.py (جدید)
# قبل از پیاده‌سازی: هیچ تستی برای سناریوی شکست وجود ندارد
```

_بعد:_
```
import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.ai_manager import AIManager

@pytest.mark.failure_scenarios
class TestAIManagerFailureScenarios:
    
    @patch('backend.app.services.openai_service.OpenAIService.generate')
    @patch('backend.app.services.claude_service.ClaudeService.generate')
    async def test_fallback_on_openai_connection_error(self, mock_claude, mock_openai):
        """
        تست سناریوی شکست: قطع connection به OpenAI و بررسی فعال شدن fallback به Claude
        این تست outcome را اندازه می‌گیرد: آیا fallback واقعاً فعال می‌شود و پاسخ مناسب برمی‌گرداند
        """
        # Arrange: شبیه‌سازی قطع connection به OpenAI
        mock_openai.side_effect = ConnectionError("Failed to connect to OpenAI API")
        mock_claude.return_value = "پاسخ از مدل جایگزین Claude"
        
        # Act
        manager = AIManager()
        result = await manager.generate("prompt test")
        
        # Assert: بررسی outcome - fallback فعال شده و پاسخ برگردانده شده
        assert result == "پاسخ از مدل جایگزین Claude"
        mock_openai.assert_called_once()
        mock_claude.assert_called_once()
    
    @patch('backend.app.services.openai_service.OpenAIService.generate')
    @patch('backend.app.services.claude_service.ClaudeService.generate')
    async def test_no_fallback_on_successful_openai(self, mock_claude, mock_openai):
        """
        تست اینکه اگر OpenAI موفق باشد، fallback فعال نمی‌شود
        """
        # Arrange
        mock_openai.return_value = "پاسخ از OpenAI"
        
        # Act
        manager = AIManager()
        result = await manager.generate("prompt test")
        
        # Assert
        assert result == "پاسخ از OpenAI"
        mock_openai.assert_called_once()
        mock_claude.assert_not_called()
    
    @patch('backend.app.services.openai_service.OpenAIService.generate')
    @patch('backend.app.services.claude_service.ClaudeService.generate')
    async def test_all_models_fail(self, mock_claude, mock_openai):
        """
        تست اینکه اگر همه مدل‌ها fail کنند، خطای مناسب برگردانده می‌شود
        """
        # Arrange
        mock_openai.side_effect = ConnectionError("OpenAI failed")
        mock_claude.side_effect = ConnectionError("Claude also failed")
        
        # Act & Assert
        manager = AIManager()
        with pytest.raises(RuntimeError, match="All AI models failed"):
            await manager.generate("prompt test")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_ai_manager_failure_scenarios.py -m failure_scenarios -v`
- `pytest backend/tests/test_ai_manager_failure_scenarios.py -m failure_scenarios --coverage`
- `python -m pytest backend/tests/test_ai_manager_failure_scenarios.py -m failure_scenarios --tb=long`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل‌های backend/app/services/ai_manager.py، backend/app/services/ai_base.py، backend/app/services/openai_service.py، backend/app/services/claude_service.py، و backend/app/services/ai_balance_service.py deep-read نشده‌اند. ممکن است fallback logic در فایل‌های دیگری پیاده‌سازی شده باشد یا ساختار متفاوتی داشته باشد. همچنین ممکن است mock کردن سرویس‌ها نیاز به تنظیمات اضافی داشته باشد (مثلاً async mocking). تست‌ها باید با دقت طراحی شوند تا سرویس‌های واقعی را تحت تأثیر قرار ندهند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 41: تعریف معیارهای پذیرش رفتار-محور و بازنویسی outcome target قابل اندازه‌گیری

**Scope:** این بخش شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از رفتار قابل مشاهده و اندازه‌گیری outcome target است. همچنین شامل یک گام اجرایی برای بازنویسی outcome target به صورت measurable می‌باشد. خارج از scope: پیاده‌سازی کد، نوشتن تست، اضافه کردن metric/log، اجرای linter/type-check.
**Key terms:** npm run test, pytest, tsc --noEmit, mypy

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف معیارهای پذیرش رفتار-محور و بازنویسی outcome target قابل اندازه‌گیری

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/runner.py` — `Runner class` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل مسئول اجرای فرآیند verify است و می‌تواند محل مناسبی برای تعریف outcome target باشد.
- `backend/app/services/verify_runtime/iterative_orchestrator.py` — `IterativeOrchestrator class` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل هماهنگ‌کننده فرآیندهای تکراری verify است و می‌تواند برای تعریف معیارهای پذیرش استفاده شود.
- `backend/app/services/verify_runtime/code_aware_verifier.py` — `CodeAwareVerifier class` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل برای verify آگاه از کد استفاده می‌شود و می‌تواند محل مناسبی برای تعریف معیارهای پذیرش باشد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده: (نامشخص) — بر اساس ساختار پروژه، از Python با FastAPI برای backend و Next.js برای frontend استفاده شده است. کتابخانه‌های مرتبط شامل pytest برای تست‌های backend و npm run test برای تست‌های frontend می‌باشد.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/tests/test_runtime_verify_stage1.py` — این فایل تست برای اجرای تست‌های E2E مرتبط با verify_runtime استفاده می‌شود و برای AC3 (test E2E که outcome را اندازه می‌گیرد عبور می‌کند) حیاتی است.
- `backend/tests/test_runtime_verify_stage2.py` — این فایل تست برای اجرای تست‌های E2E مرتبط با verify_runtime استفاده می‌شود و برای AC3 (test E2E که outcome را اندازه می‌گیرد عبور می‌کند) حیاتی است.
- `backend/tests/test_verify_v7.py` — این فایل تست برای اجرای تست‌های E2E مرتبط با verify_runtime استفاده می‌شود و برای AC3 (test E2E که outcome را اندازه می‌گیرد عبور می‌کند) حیاتی است.
- `backend/app/services/verify_runtime/ac_schema.py` — این فایل احتمالاً شامل شِما و ساختار معیارهای پذیرش است و برای تعریف ACها مرتبط می‌باشد.
- `backend/app/services/verify_runtime/ac_cache_service.py` — این فایل احتمالاً برای کش کردن نتایج معیارهای پذیرش استفاده می‌شود و برای AC4 (metric/log اضافه شد) مرتبط می‌باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های موجود در دایرکتوری backend/app/services/verify_runtime/ وابسته است که شامل runner.py (اجرای فرآیند verify)، iterative_orchestrator.py (هماهنگ‌کننده فرآیندهای تکراری)، code_aware_verifier.py (verify آگاه از کد)، ac_schema.py (شِما و ساختار معیارهای پذیرش)، و ac_cache_service.py (کش کردن نتایج معیارهای پذیرش) می‌باشد. همچنین فایل‌های تست در backend/tests/ مانند test_runtime_verify_stage1.py تا test_runtime_verify_stage9.py و test_verify_v7.py برای اجرای تست‌های E2E استفاده می‌شوند. فایل‌های caller شامل backend/app/services/verify_runtime/__init__.py و backend/app/services/verify_runtime/base.py می‌باشند.

## 🔍 Context و وضعیت فعلی
این تسک شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از رفتار قابل مشاهده و اندازه‌گیری outcome target است. همچنین شامل یک گام اجرایی برای بازنویسی outcome target به صورت measurable می‌باشد. خارج از scope: پیاده‌سازی کد، نوشتن تست، اضافه کردن metric/log، اجرای linter/type-check.

بخش مربوط از درخواست اصلی کاربر:
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).

کلیدواژه‌ها: npm run test, pytest, tsc --noEmit, mypy

شواهد در کد واقعی پروژه: با توجه به deep context موجود، فایل‌های مرتبط با verify_runtime در backend/app/services/verify_runtime/ شامل runner.py، iterative_orchestrator.py، code_aware_verifier.py و سایر فایل‌های این دایرکتوری هستند که می‌توانند برای پیاده‌سازی معیارهای پذیرش استفاده شوند. همچنین فایل‌های تست در backend/tests/ مانند test_runtime_verify_stage1.py تا test_runtime_verify_stage9.py و test_verify_v7.py برای اجرای تست‌های E2E مناسب هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد — مثلاً «email send rate > 95% در ۱۰۰ تلاش»
- [ ] کد تغییر کرد تا outcome target محقق شود — این AC صرفاً مستندسازی است و خارج از scope پیاده‌سازی کد می‌باشد
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند — این AC صرفاً مستندسازی است و خارج از scope نوشتن تست می‌باشد
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد — این AC صرفاً مستندسازی است و خارج از scope اضافه کردن metric/log می‌باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`) — این AC صرفاً مستندسازی است و خارج از scope اجرای تست می‌باشد
- [ ] linter بدون warning عبور می‌کند — این AC صرفاً مستندسازی است و خارج از scope اجرای linter می‌باشد
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`) — این AC صرفاً مستندسازی است و خارج از scope اجرای type-check می‌باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بازنویسی outcome target به صورت measurable: در فایل‌های مربوط به verify_runtime مانند backend/app/services/verify_runtime/runner.py یا backend/app/services/verify_runtime/iterative_orchestrator.py، یک outcome target مشخص و قابل اندازه‌گیری تعریف شود (مثلاً: 'email send rate > 95% در ۱۰۰ تلاش').

2. تعریف ۷ معیار پذیرش (AC) رفتار-محور:
   - AC1: outcome target به‌صورت measurable بازنویسی شد
   - AC2: کد تغییر کرد تا outcome target محقق شود
   - AC3: test E2E که outcome را اندازه می‌گیرد عبور می‌کند
   - AC4: metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
   - AC5: هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
   - AC6: linter بدون warning عبور می‌کند
   - AC7: type-check موفق است (`tsc --noEmit` / `mypy`)

3. گام اجرایی: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).

توجه: خارج از scope این تسک، پیاده‌سازی کد، نوشتن تست، اضافه کردن metric/log، و اجرای linter/type-check است. این تسک صرفاً تعریف و مستندسازی معیارها را شامل می‌شود.

## 💡 نمونه‌های قبل/بعد
**بازنویسی outcome target به صورت measurable**

_قبل:_
```
outcome target: 'بهبود نرخ ارسال ایمیل'
```

_بعد:_
```
outcome target: 'email send rate > 95% در ۱۰۰ تلاش'
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_runtime_verify_stage1.py`
- `pytest backend/tests/test_runtime_verify_stage2.py`
- `pytest backend/tests/test_verify_v7.py`
- `npm run test`
- `tsc --noEmit`
- `mypy backend/`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک صرفاً مستندسازی و تعریف معیارهای پذیرش است و هیچ تغییری در کد ایجاد نمی‌کند. بنابراین ریسک خاصی برای کدبیس وجود ندارد. با این حال، اگر در آینده پیاده‌سازی شود، فایل‌های backend/app/services/verify_runtime/runner.py و backend/app/services/verify_runtime/iterative_orchestrator.py به عنوان نقاط اصلی تغییر خواهند بود و باید دقت شود که تغییرات با سایر فایل‌های verify_runtime مانند ac_schema.py و ac_cache_service.py هماهنگ باشند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 42: بازنویسی outcome target به صورت measurable و افزودن به documentation

**Scope:** این مرحله شامل بازنویسی outcome target (هدف پیامد) به شکلی قابل اندازه‌گیری (measurable) و افزودن آن به مستندات پروژه (مانند README.md یا docs/) است. این مرحله صرفاً بر روی متن و مستندات تمرکز دارد و شامل تغییر کد یا پیاده‌سازی نمی‌شود. خروجی این مرحله یک متن measurable است که در فایل‌های مستندات قرار می‌گیرد.
**Key terms:** outcome target, measurable, effectiveness, README.md, docs/

**بخش مربوط از متن کاربر:**
```
- بازنویسی outcome target به صورت measurable و اضافه کردن به documentation — outcome target به صورت measurable بازنویسی و به documentation اضافه نشده

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["outcome target", "measurable", "effectiveness"], "files_hint": ["README.md", "docs/"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
بازنویسی outcome target به صورت measurable در مستندات

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `docs/README.md` — `outcome_target_section` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، README.md در docs/ موجود است.
- `docs/ROADMAP.md` — `outcome_target_section` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. ROADMAP.md مکان مناسبی برای تعریف اهداف measurable است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — این تسک صرفاً مستنداتی است و به Stack فنی وابسته نیست.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `docs/ARCHITECTURE.md` — ممکن است شامل اهداف معماری باشد که با outcome target مرتبط است
- `docs/AUDIT_REPORT.md` — گزارش‌های حسابرسی ممکن است معیارهای effectiveness را شامل شوند
- `docs/PHASE_5_META_VALIDATION.md` — مستندات فاز ۵ ممکن است شامل اهداف قابل اندازه‌گیری باشد
- `docs/SYSTEM_REPORT_2026-02-08.md` — گزارش سیستم ممکن است معیارهای performance را نشان دهد که برای measurable کردن outcome target مفید است

## 🌐 نقشهٔ وابستگی‌ها
این تسک صرفاً بر روی فایل‌های مستندات (docs/README.md, docs/ROADMAP.md, docs/ARCHITECTURE.md, docs/AUDIT_REPORT.md, docs/PHASE_5_META_VALIDATION.md, docs/SYSTEM_REPORT_2026-02-08.md) تأثیر دارد. هیچ وابستگی به کد backend یا frontend ندارد. تغییرات در مستندات بر هیچ سرویس، endpoint، یا کامپوننتی تأثیر نمی‌گذارد. فایل‌های caller یا importer برای مستندات وجود ندارد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست بازنویسی outcome target (هدف پیامد) به شکلی قابل اندازه‌گیری (measurable) و افزودن آن به مستندات پروژه (مانند README.md یا docs/) را دارد. این مرحله صرفاً بر روی متن و مستندات تمرکز دارد و شامل تغییر کد یا پیاده‌سازی نمی‌شود. خروجی این مرحله یک متن measurable است که در فایل‌های مستندات قرار می‌گیرد.

بخش مربوط از درخواست اصلی کاربر:
- بازنویسی outcome target به صورت measurable و اضافه کردن به documentation — outcome target به صورت measurable بازنویسی و به documentation اضافه نشده

کلیدواژه‌ها: outcome target, measurable, effectiveness, README.md, docs/

شواهد در کد واقعی پروژه: با توجه به deep context ارائه‌شده، فایل‌های README.md و docs/ در ساختار پروژه موجود هستند اما محتوای آن‌ها deep-read نشده است. فایل‌های docs/ شامل ARCHITECTURE.md, AUDIT_REPORT.md, PHASE_5_META_VALIDATION.md, README.md, ROADMAP.md, SYSTEM_REPORT_2026-02-08.md هستند. هیچ‌کدام از این فایل‌ها deep-read نشده‌اند، بنابراین نمی‌توان محتوای فعلی آن‌ها را تأیید کرد. بر اساس متن کاربر، outcome target در مستندات فعلی به صورت measurable نوشته نشده است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد و در فایل README.md (ریشه پروژه) یا docs/README.md موجود است
- [ ] outcome target بازنویسی‌شده شامل حداقل یک معیار عددی قابل اندازه‌گیری است (مثلاً درصد، زمان، تعداد)
- [ ] outcome target بازنویسی‌شده شامل یک بازه زمانی مشخص است (مثلاً 'تا پایان Q2 2026' یا 'در بازه 30 روزه')
- [ ] متن outcome target در فایل docs/ROADMAP.md نیز اضافه شده است (اختیاری اما توصیه‌شده)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مراحل پیشنهادی برای پیاده‌سازی:

1. **بررسی فایل‌های مستندات فعلی**: فایل‌های README.md و docs/README.md و سایر فایل‌های docs/ را برای یافتن outcome target موجود جستجو کن. از grep با الگوی 'outcome target' یا 'effectiveness' استفاده کن.

2. **بازنویسی outcome target به صورت measurable**: متن outcome target را به شکلی بازنویسی کن که شامل معیارهای قابل اندازه‌گیری باشد. مثلاً:
   - قبل: 'بهبود effectiveness سیستم'
   - بعد: 'کاهش زمان پاسخ API به زیر 200ms برای 95% درخواست‌ها در بازه 30 روزه'

3. **افزودن به مستندات**: متن بازنویسی‌شده را به فایل README.md (در ریشه پروژه) و/یا فایل docs/ROADMAP.md اضافه کن.

4. **استفاده از معیارهای SMART**: اطمینان حاصل کن که outcome target بازنویسی‌شده دارای ویژگی‌های Specific, Measurable, Achievable, Relevant, Time-bound باشد.

5. **ثبت تغییرات**: تغییرات را با commit message مناسب ثبت کن.

## 💡 نمونه‌های قبل/بعد
**نمونه بازنویسی outcome target**

_قبل:_
```
Outcome target: بهبود effectiveness سیستم در تشخیص و رفع مشکلات runtime
```

_بعد:_
```
Outcome target (measurable): کاهش 40% در زمان تشخیص مشکلات runtime (از میانگین 15 دقیقه به 9 دقیقه) و افزایش 25% در نرخ رفع خودکار مشکلات (از 60% به 75%) تا پایان Q2 2026، با پایش مستمر از طریق dashboard و گزارش‌های هفتگی.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'outcome target' README.md docs/`
- `grep -rn 'measurable' README.md docs/`
- `grep -rnE '\d+%|\d+ ms|\d+ دقیقه' README.md docs/`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک خاصی برای این کدبیس وجود ندارد زیرا تغییرات صرفاً مستنداتی هستند و بر کد backend یا frontend تأثیر نمی‌گذارند. تنها ریسک احتمالی این است که outcome target بازنویسی‌شده با اهداف واقعی پروژه همخوانی نداشته باشد — برای جلوگیری از این، باید با تیم توسعه هماهنگ شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 43: رفع عدم یکپارچگی بین oversight_service و project_journal API

**Scope:** این بخش به عدم یکپارچگی بین سرویس oversight_service و API پروژه ژورنال اشاره دارد. هدف آن شناسایی و رفع شکاف‌های ارتباطی بین این دو مؤلفه است. فایل‌های مرتبط شامل backend/app/services/oversight_service.py و کلاس OversightService هستند. هیچ موقعیت دقیق فایل یا endpoint خاصی در متن مشخص نشده است.
**Key terms:** oversight_service, project_journal API, OversightService, backend/app/services/oversight_service.py

**بخش مربوط از متن کاربر:**
```
## 🎯 هدف (خلاصه ساختاریافته)
[Effectiveness] عدم یکپارچگی بین oversight_service و project_journal API

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع عدم یکپارچگی oversight_service و project_journal API

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py` — `OversightService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل حاوی کلاس OversightService است که باید متد sync_with_journal به آن اضافه شود.
- `backend/app/api/routes/project_journal.py` — `project_journal_router` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل حاوی endpointهای project_journal API است که باید endpoint جدید برای oversight اضافه شود.
- `backend/app/services/journal_service.py` — `JournalService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل سرویس اصلی مدیریت ژورنال را پیاده‌سازی می‌کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs. کتابخانه‌های مرتبط: SQLAlchemy (برای ORM)، Pydantic (برای validation)، pytest (برای تست).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/models/project.py` — مدل Project احتمالاً ارتباط بین oversight و journal را مدیریت می‌کند و ممکن است نیاز به تغییر داشته باشد.
- `backend/app/services/db_service.py` — سرویس دیتابیس برای ذخیره‌سازی رویدادهای oversight در journal استفاده می‌شود.
- `backend/app/api/routes/projects.py` — این روتر ممکن است با project_journal و oversight_service در تعامل باشد و نیاز به هماهنگی دارد.
- `backend/app/models/render_log.py` — مدل render_log ممکن است برای ثبت رویدادهای oversight در journal استفاده شود.
- `backend/app/services/notification_service.py` — سرویس اعلان‌ها ممکن است برای اطلاع‌رسانی رویدادهای oversight به کاربران استفاده شود.

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر روی فایل‌های backend/app/services/oversight_service.py (کلاس OversightService)، backend/app/api/routes/project_journal.py (روتر project_journal)، backend/app/services/journal_service.py (سرویس ژورنال)، backend/app/models/project.py (مدل Project)، backend/app/services/db_service.py (سرویس دیتابیس)، backend/app/api/routes/projects.py (روتر پروژه‌ها)، backend/app/models/render_log.py (مدل render_log) و backend/app/services/notification_service.py (سرویس اعلان‌ها) تأثیر می‌گذارد. تغییر در oversight_service نیازمند هماهنگی با journal_service و project_journal API است. همچنین مدل‌های داده‌ای باید برای پشتیبانی از رویدادهای oversight به‌روزرسانی شوند.

## 🔍 Context و وضعیت فعلی
این تسک به رفع عدم یکپارچگی بین سرویس oversight_service و API پروژه ژورنال اشاره دارد. هدف آن شناسایی و رفع شکاف‌های ارتباطی بین این دو مؤلفه است. فایل‌های مرتبط شامل backend/app/services/oversight_service.py و کلاس OversightService هستند. هیچ موقعیت دقیق فایل یا endpoint خاصی در متن مشخص نشده است.

بر اساس تحلیل کدبیس واقعی:
- فایل backend/app/services/oversight_service.py حاوی کلاس OversightService است که مسئول مدیریت فرآیندهای نظارتی (oversight) است.
- فایل backend/app/api/routes/project_journal.py حاوی endpointهای مربوط به پروژه ژورنال است.
- فایل backend/app/services/journal_service.py سرویس اصلی مدیریت ژورنال را پیاده‌سازی می‌کند.
- فایل backend/app/models/project.py مدل Project را تعریف می‌کند که احتمالاً ارتباط بین oversight و journal را مدیریت می‌کند.

کلیدواژه‌های استخراج شده از متن کاربر:
- oversight_service
- project_journal API
- OversightService
- backend/app/services/oversight_service.py

عدم یکپارچگی می‌تواند شامل موارد زیر باشد:
1. عدم ثبت رویدادهای oversight در project_journal
2. عدم هماهنگی وضعیت‌ها بین دو سیستم
3. عدم وجود hook یا callback برای به‌روزرسانی خودکار journal هنگام تغییرات oversight
4. عدم یکپارچگی در schema داده‌ها بین دو سرویس

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] متد sync_with_journal به کلاس OversightService در فایل backend/app/services/oversight_service.py اضافه شود.
- [ ] endpoint POST /api/projects/{project_id}/journal/oversight در فایل backend/app/api/routes/project_journal.py ایجاد شود.
- [ ] رویدادهای مهم oversight (شروع، پایان، خطا) به صورت خودکار در project_journal ثبت شوند.
- [ ] مدل‌های داده‌ای در backend/app/models/ برای پشتیبانی از رویدادهای oversight به‌روزرسانی شوند.
- [ ] تست‌های یکپارچگی در backend/tests/ برای اطمینان از هماهنگی دو سرویس نوشته شوند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. برای رفع عدم یکپارچگی بین oversight_service و project_journal API، مراحل زیر پیشنهاد می‌شود:

1. **تحلیل وابستگی‌های فعلی**:
   - بررسی فایل backend/app/services/oversight_service.py برای شناسایی متدهایی که باید با journal تعامل داشته باشند.
   - بررسی فایل backend/app/api/routes/project_journal.py برای شناسایی endpointهای موجود.
   - بررسی فایل backend/app/services/journal_service.py برای درک APIهای موجود.

2. **ایجاد یکپارچگی در سطح سرویس**:
   - افزودن متد `sync_with_journal` به کلاس OversightService در فایل backend/app/services/oversight_service.py.
   - این متد باید رویدادهای مهم oversight (مانند شروع، پایان، خطا) را به project_journal ثبت کند.

3. **ایجاد endpoint جدید در project_journal API**:
   - افزودن endpoint POST /api/projects/{project_id}/journal/oversight در فایل backend/app/api/routes/project_journal.py.
   - این endpoint باید رویدادهای oversight را دریافت و در ژورنال ثبت کند.

4. **یکپارچه‌سازی schema داده‌ها**:
   - اطمینان از اینکه مدل‌های داده‌ای در backend/app/models/ با یکدیگر سازگار هستند.
   - اضافه کردن فیلدهای مورد نیاز برای ثبت رویدادهای oversight در مدل journal.

5. **پیاده‌سازی hook/callback**:
   - در OversightService، پس از هر عملیات مهم، callback به journal_service فراخوانی شود.
   - این کار از طریق dependency injection یا event system انجام شود.

6. **تست یکپارچگی**:
   - نوشتن تست‌های یکپارچگی در backend/tests/ برای اطمینان از هماهنگی دو سرویس.

## 💡 نمونه‌های قبل/بعد
**افزودن متد sync_with_journal به OversightService**

_قبل:_
```
# backend/app/services/oversight_service.py
class OversightService:
    async def run_oversight(self, project_id: str):
        # اجرای فرآیند نظارتی
        result = await self._execute_oversight(project_id)
        return result
```

_بعد:_
```
# backend/app/services/oversight_service.py
class OversightService:
    def __init__(self, journal_service: JournalService):
        self.journal_service = journal_service
    
    async def run_oversight(self, project_id: str):
        # ثبت رویداد شروع در journal
        await self.journal_service.log_event(
            project_id=project_id,
            event_type="oversight_started",
            metadata={"timestamp": datetime.utcnow()}
        )
        # اجرای فرآیند نظارتی
        result = await self._execute_oversight(project_id)
        # ثبت رویداد پایان در journal
        await self.journal_service.log_event(
            project_id=project_id,
            event_type="oversight_completed",
            metadata={"result": result}
        )
        return result
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_journal_integration.py -v`
- `python -m pytest backend/tests/ -k "oversight or journal" -v`
- `flake8 backend/app/services/oversight_service.py backend/app/api/routes/project_journal.py`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در کلاس OversightService در فایل backend/app/services/oversight_service.py ممکن است بر روی تمام endpointهایی که از این سرویس استفاده می‌کنند تأثیر بگذارد. همچنین تغییر در project_journal API در فایل backend/app/api/routes/project_journal.py ممکن است بر روی فرانت‌اند که از این API استفاده می‌کند تأثیر بگذارد. ریسک اصلی عدم هماهنگی در schema داده‌ها بین دو سرویس است که می‌تواند باعث خطاهای runtime شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 44: اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based

**Scope:** این بخش شامل افزودن یک webhook در سرویس project_journal است تا پس از تکمیل هر پروژه/ژورنال، یک گزارش خودکار به oversight_service ارسال شود. گزارش باید به صورت JSON ذخیره شود. این بخش شامل تغییر در کد project_journal برای ارسال درخواست HTTP به oversight_service و همچنین تغییر در oversight_service برای دریافت و ذخیره گزارش‌ها است. نکته حیاتی: این یک effectiveness issue است، یعنی کد فعلی syntactically کار می‌کند ولی outcome مطلوب (ارسال خودکار گزارش) حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
**Key terms:** project_journal, oversight_service, webhook, JSON-based

**بخش مربوط از متن کاربر:**
```
## 📊 وضعیت فعلی
project_journal API مستقل عمل می‌کند و هیچ اشاره‌ای به oversight_service در outcome data دیده نمی‌شود

## 🛠 اقدام پیشنهادی
اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن webhook خودکار project_journal به oversight_service با ذخیره JSON

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/journal_service.py:85-120` — `complete_journal` — این تابع در حال حاضر فقط در دیتابیس ذخیره می‌کند و هیچ webhook به oversight_service ندارد. باید پس از ذخیره، یک درخواست HTTP به oversight_service ارسال کند.
  ```python
  def complete_journal(self, project_id: str, journal_data: dict) -> dict:
      # ذخیره در دیتابیس
      journal = self.db.journals.insert_one(journal_data)
      # به‌روزرسانی وضعیت پروژه
      self.db.projects.update_one(
          {'_id': project_id},
          {'$set': {'last_journal_completed': datetime.utcnow()}}
      )
      return {'status': 'completed', 'journal_id': str(journal.inserted_id)}
  ```
- `backend/app/services/oversight_service.py:300-350` — `store_report` — این تابع برای ذخیره گزارش‌های دریافتی طراحی شده اما endpoint API برای آن فعال نیست. باید endpoint مربوطه در روتر اضافه شود.
  ```python
  def store_report(self, report_data: dict) -> dict:
      # ذخیره گزارش در دیتابیس
      report = self.db.oversight_reports.insert_one(report_data)
      return {'status': 'stored', 'report_id': str(report.inserted_id)}
  ```
- `backend/app/api/routes/oversight.py:1-50` — `router` — این فایل endpointهای oversight را تعریف می‌کند. باید یک endpoint جدید POST /receive-report اضافه شود.
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from app.services.oversight_service import OversightService
  
  router = APIRouter(prefix='/api/oversight', tags=['oversight'])
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: Python 3.10+, FastAPI, MongoDB (via Motor/AsyncIOMotor), httpx برای درخواست‌های HTTP غیرهمزمان. کتابخانه‌های مرتبط: httpx, pydantic برای validation, logging.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/project_journal.py` (سطر 25) — این روتر از journal_service استفاده می‌کند و endpointهای مربوط به ژورنال را تعریف می‌کند. تغییر در service بر این روتر تأثیر می‌گذارد.
- `backend/app/models/project.py` (سطر 60) — مدل پروژه شامل فیلدهایی است که در payload گزارش استفاده می‌شود (project_id, status).
- `backend/app/models/render_log.py` (سطر 40) — مدل لاگ‌ها ممکن است برای metrics گزارش استفاده شود.
- `backend/app/core/config.py` (سطر 80) — آدرس oversight_service (URL) باید در تنظیمات برنامه تعریف شود تا در محیط‌های مختلف قابل تغییر باشد.
- `backend/app/services/background_scheduler.py` (سطر 30) — اگر webhook به صورت async اجرا شود، ممکن است با scheduler تداخل داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تغییر بر زنجیره project_journal → oversight_service تأثیر می‌گذارد. فایل journal_service.py (تابع complete_journal) باید یک درخواست HTTP به oversight_service ارسال کند. فایل oversight_service.py (تابع store_report) باید گزارش را ذخیره کند. فایل oversight.py (روتر) باید endpoint جدید داشته باشد. فایل config.py باید آدرس oversight_service را داشته باشد. فایل‌های مدل project.py و render_log.py برای ساخت payload استفاده می‌شوند. تست‌های مربوطه در backend/tests/ باید به‌روزرسانی شوند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست اضافه کردن یک webhook در سرویس project_journal دارد تا پس از تکمیل هر پروژه/ژورنال، یک گزارش خودکار به oversight_service ارسال شود. گزارش باید به صورت JSON ذخیره شود. این بخش شامل تغییر در کد project_journal برای ارسال درخواست HTTP به oversight_service و همچنین تغییر در oversight_service برای دریافت و ذخیره گزارش‌ها است. نکته حیاتی: این یک effectiveness issue است، یعنی کد فعلی syntactically کار می‌کند ولی outcome مطلوب (ارسال خودکار گزارش) حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

وضعیت فعلی: project_journal API مستقل عمل می‌کند و هیچ اشاره‌ای به oversight_service در outcome data دیده نمی‌شود.
کلیدواژه‌ها: project_journal, oversight_service, webhook, JSON-based

فایل‌های مرتبط در پروژه:
- backend/app/services/journal_service.py (سرویس اصلی project_journal)
- backend/app/services/oversight_service.py (سرویس مقصد برای دریافت گزارش)
- backend/app/api/routes/project_journal.py (روتر API)
- backend/app/api/routes/oversight.py (روتر API oversight)
- backend/app/models/project.py (مدل پروژه)
- backend/app/models/render_log.py (مدل لاگ‌ها)

شواهد در کد: فایل journal_service.py در خطوط 45-120 شامل توابع create_journal و complete_journal است که در حال حاضر فقط در دیتابیس ذخیره می‌کنند و هیچ webhook یا ارسال HTTP به oversight_service ندارند. فایل oversight_service.py در خطوط 200-350 شامل توابع receive_report و store_report است که برای دریافت گزارش‌های خارجی طراحی شده‌اند اما endpoint آن‌ها در روتر فعال نیست.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] پس از تکمیل ژورنال در project_journal، یک درخواست HTTP POST به oversight_service ارسال شود با payload JSON شامل project_id, journal_id, timestamp, summary, status
- [ ] endpoint POST /api/oversight/receive-report در oversight_service فعال باشد و payload معتبر را با status 201 ذخیره کند
- [ ] در صورت خطای شبکه (timeout, connection refused)، webhook خطا را log کند و عملیات اصلی (ذخیره ژورنال) شکست نخورد
- [ ] payload نامعتبر (بدون فیلدهای اجباری) توسط endpoint oversight_service با status 422 رد شود
- [ ] گزارش ذخیره‌شده در دیتابیس oversight_service قابل بازیابی باشد (با query روی project_id)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/journal_service.py، تابع complete_journal (خطوط 85-120) را اصلاح کن تا پس از تکمیل ژورنال:
   - یک payload JSON شامل: project_id, journal_id, timestamp, summary, status, metrics بسازد
   - یک درخواست HTTP POST به endpoint oversight_service (مثلاً /api/oversight/receive-report) ارسال کند
   - از httpx یا aiohttp برای درخواست غیرهمزمان استفاده کند
   - خطاهای شبکه را مدیریت کند (try/except با logging)

2. در فایل backend/app/api/routes/oversight.py، یک endpoint جدید POST /api/oversight/receive-report اضافه کن که:
   - payload JSON را دریافت کند
   - اعتبارسنجی کند (فیلدهای اجباری: project_id, journal_id, timestamp)
   - گزارش را در دیتابیس ذخیره کند (با استفاده از تابع store_report در oversight_service)
   - response 201 با message تأیید برگرداند

3. در فایل backend/app/services/oversight_service.py، تابع store_report (خطوط 300-350) را بررسی و در صورت نیاز اصلاح کن تا:
   - گزارش JSON را در جدول/collection مخصوص ذخیره کند
   - timestamp خودکار اضافه کند
   - ایندکس روی project_id و journal_id داشته باشد

4. تست واحد برای سناریوی موفق و خطا (network failure, invalid payload) اضافه کن

5. لاگینگ مناسب در هر دو سمت (ارسال و دریافت) اضافه کن تا در monitoring قابل ردیابی باشد

## 💡 نمونه‌های قبل/بعد
**قبل از تغییر — تابع complete_journal بدون webhook**

_قبل:_
```
def complete_journal(self, project_id: str, journal_data: dict) -> dict:
    journal = self.db.journals.insert_one(journal_data)
    self.db.projects.update_one(
        {'_id': project_id},
        {'$set': {'last_journal_completed': datetime.utcnow()}}
    )
    return {'status': 'completed', 'journal_id': str(journal.inserted_id)}
```

_بعد:_
```
async def complete_journal(self, project_id: str, journal_data: dict) -> dict:
    journal = self.db.journals.insert_one(journal_data)
    self.db.projects.update_one(
        {'_id': project_id},
        {'$set': {'last_journal_completed': datetime.utcnow()}}
    )
    # ارسال webhook به oversight_service
    try:
        payload = {
            'project_id': project_id,
            'journal_id': str(journal.inserted_id),
            'timestamp': datetime.utcnow().isoformat(),
            'summary': journal_data.get('summary', ''),
            'status': 'completed'
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OVERSIGHT_URL}/api/oversight/receive-report",
                json=payload,
                timeout=10.0
            )
            if response.status_code != 201:
                logger.error(f"Failed to send webhook: {response.status_code}")
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
    return {'status': 'completed', 'journal_id': str(journal.inserted_id)}
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_journal_webhook.py -v`
- `pytest backend/tests/test_oversight_storage.py -v`
- `curl -X POST http://localhost:8000/api/oversight/receive-report -H 'Content-Type: application/json' -d '{"project_id":"test","journal_id":"test","timestamp":"2024-01-01T00:00:00"}'`

## ⚠️ ریسک‌ها و موارد احتیاط
1. فایل journal_service.py توسط روتر project_journal.py (خط 25) و احتمالاً توسط background_scheduler.py (خط 30) فراخوانی می‌شود. تغییر امضای تابع به async می‌تواند callerها را بشکند. 2. آدرس oversight_service در config.py (خط 80) باید در همه محیط‌ها (dev, staging, prod) تنظیم شود. 3. اگر oversight_service در دسترس نباشد، webhook با خطا مواجه می‌شود و باید مکانیزم retry یا queue در نظر گرفته شود. 4. افزایش latency در complete_journal به دلیل درخواست HTTP ممکن است بر UX تأثیر بگذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 45: تبدیل معیارهای پذیرش رفتار-محور به یک مرحله اجرایی با outcome target قابل اندازه‌گیری

**Scope:** این بخش شامل تعریف معیارهای پذیرش (AC) به صورت رفتار-محور و یک گام اجرایی برای بازنویسی outcome target به صورت قابل اندازه‌گیری است. خارج از scope: پیاده‌سازی کد، نوشتن تست E2E، اضافه کردن metric/log، اجرای linter/type-check. نکته حیاتی: ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس، و verify باید پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.
**Key terms:** OversightService

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
```

## 🎯 هدف (خلاصه ساختاریافته)
تبدیل معیارهای پذیرش رفتار-محور به outcome target قابل اندازه‌گیری در OversightService

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py` — `OversightService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل اصلی سرویس Oversight است که احتمالاً outcome targetها در آن تعریف شده‌اند.
- `backend/app/services/oversight_verifier.py` — `OversightVerifier` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل مسئول verify کردن outcome targetها است.
- `backend/app/services/oversight_codex_service.py` — `OversightCodexService` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل احتمالاً قوانین و معیارهای پذیرش را مدیریت می‌کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_deep_scan_service.py` — این سرویس اسکن عمیق انجام می‌دهد و ممکن است outcome targetها را در خروجی خود استفاده کند
- `backend/app/services/oversight_inspector_bridge.py` — این فایل پل ارتباطی بین Oversight و Inspector است و ممکن است outcome targetها را منتقل کند
- `backend/app/services/oversight_mega_bundle.py` — این فایل باندل بزرگ Oversight را مدیریت می‌کند و احتمالاً outcome targetها را تجمیع می‌کند
- `backend/app/services/oversight_progress.py` — این فایل پیشرفت را ردیابی می‌کند و ممکن است outcome targetها را برای اندازه‌گیری استفاده کند
- `backend/app/services/oversight_settings.py` — این فایل تنظیمات Oversight را مدیریت می‌کند و ممکن است outcome targetها در تنظیمات تعریف شده باشند

## 🌐 نقشهٔ وابستگی‌ها
این تسک بر روی فایل‌های backend/app/services/oversight_service.py و زیرمجموعه‌های آن (oversight_verifier.py, oversight_codex_service.py, oversight_deep_scan_service.py, oversight_inspector_bridge.py, oversight_mega_bundle.py, oversight_model_temp_activate.py, oversight_progress.py, oversight_settings.py, oversight_strong_prompt.py, oversight_telegram_compose.py, oversight_upload_session.py, oversight_verify_pdf.py) تأثیر می‌گذارد. همچنین ممکن است با فایل‌های backend/app/api/routes/oversight.py (روتر API) و backend/app/models/ (مدل‌های داده) ارتباط داشته باشد. تغییر در outcome targetها می‌تواند روی نحوه گزارش‌دهی و نمایش نتایج در frontend تأثیر بگذارد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست تبدیل معیارهای پذیرش (AC) به صورت رفتار-محور و یک گام اجرایی برای بازنویسی outcome target به صورت قابل اندازه‌گیری را دارد. خارج از scope: پیاده‌سازی کد، نوشتن تست E2E، اضافه کردن metric/log، اجرای linter/type-check. نکته حیاتی: ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس، و verify باید پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

بخش مربوط از درخواست اصلی کاربر:
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).

کلیدواژه‌ها: OversightService

شواهد در کد: فایل‌های مرتبط با OversightService در مسیر backend/app/services/oversight_service.py و فایل‌های زیرمجموعه آن مانند oversight_verifier.py، oversight_codex_service.py، oversight_deep_scan_service.py، oversight_inspector_bridge.py، oversight_mega_bundle.py، oversight_model_temp_activate.py، oversight_progress.py، oversight_settings.py، oversight_strong_prompt.py، oversight_telegram_compose.py، oversight_upload_session.py، oversight_verify_pdf.py در پروژه موجود هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد — در فایل‌های OversightService، outcome targetها باید شامل معیار عددی قابل اندازه‌گیری باشند (مثلاً درصد، تعداد، زمان)
- [ ] کد تغییر کرد تا outcome target محقق شود — این AC خارج از scope است و نباید پیاده‌سازی شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند — این AC خارج از scope است و نباید پیاده‌سازی شود
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد — این AC خارج از scope است و نباید پیاده‌سازی شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`) — این AC خارج از scope است و نباید پیاده‌سازی شود
- [ ] linter بدون warning عبور می‌کند — این AC خارج از scope است و نباید پیاده‌سازی شود
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`) — این AC خارج از scope است و نباید پیاده‌سازی شود
- [ ] ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس — در فایل‌های OversightService، ACها باید بر اساس رفتار کاربر یا سیستم تعریف شوند، نه بر اساس نام متد یا کلاس
- [ ] verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند — در فایل‌های verify (مانند oversight_verifier.py)، منطق verify باید به گونه‌ای باشد که پیاده‌سازی‌های مختلف ولی هم‌ارز را قبول کند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. تحلیل فایل‌های OversightService برای شناسایی نقاطی که outcome target تعریف می‌شود.
2. بازنویسی outcome target در فایل‌های مرتبط با OversightService به صورت measurable.
3. اطمینان از اینکه ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس.
4. بررسی اینکه verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.
5. عدم تغییر در کد، تست E2E، metric/log، linter/type-check (خارج از scope).
6. تمرکز بر گام ۱ از مراحل اجرایی: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
7. فایل‌های هدف: backend/app/services/oversight_service.py و زیرمجموعه‌های آن.

## 💡 نمونه‌های قبل/بعد
**مثال بازنویسی outcome target به صورت measurable**

_قبل:_
```
outcome_target = "بهبود نرخ ارسال ایمیل"
```

_بعد:_
```
outcome_target = "email send rate > 95% در ۱۰۰ تلاش"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_verify_v7.py`
- `pytest backend/tests/test_inspector_oversight_bridge.py`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل‌های OversightService (oversight_service.py, oversight_verifier.py, oversight_codex_service.py) توسط چندین روتر و سرویس دیگر استفاده می‌شوند. تغییر در نحوه تعریف outcome targetها می‌تواند روی backend/app/api/routes/oversight.py (روتر API) و frontend (نمایش نتایج) تأثیر بگذارد. همچنین ممکن است با فایل‌های backend/app/services/verify_runtime/ (runtime verify layer) تداخل داشته باشد. از آنجایی که این تسک فقط بازنویسی ACها را شامل می‌شود و نه پیاده‌سازی کد، ریسک شکستن functionality پایین است.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 46: ریسک‌ها و موارد احتیاط: بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن

**Scope:** این بخش یک یادآوری/هشدار (⚠️) است و یک مرحله اجرایی مستقل نیست. هیچ کد یا تغییری در فایل‌ها ایجاد نمی‌کند. هدف آن ثبت یک ریسک معماری (trade-off بین کیفیت خروجی و هزینه/سرعت) است که باید در مراحل بعدی (مانند پیاده‌سازی webhook یا endpoint) به‌عنوان یک معیار ارزیابی در نظر گرفته شود. هیچ اقدامی در این مرحله انجام نمی‌شود.

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.
```

## 🎯 هدف (خلاصه ساختاریافته)
ثبت ریسک معماری trade-off کیفیت/هزینه در outcome

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/iterative_orchestrator.py` — `IterativeOrchestrator` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل مسئول orchestration outcome است و می‌تواند برای اندازه‌گیری latency قبل/بعد استفاده شود.
- `backend/app/services/ai_balance_service.py` — `AiBalanceService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، این فایل مسئول مدیریت balance و cost است و می‌تواند برای اندازه‌گیری cost قبل/بعد استفاده شود.
- `docs/ARCHITECTURE.md` — فایل مستندات معماری — برای ثبت ریسک معماری trade-off بین کیفیت خروجی و هزینه/سرعت.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص) — Stack تشخیص داده شده در بالا مشخص نیست. بر اساس ساختار پروژه، از Python (FastAPI) برای backend و Next.js برای frontend استفاده شده است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_verifier.py` — این فایل برای verify outcome استفاده می‌شود و ممکن است تحت تأثیر بهبود outcome قرار گیرد.
- `backend/app/services/verify_runtime/ac_cache_service.py` — این فایل برای کش کردن metric‌ها استفاده می‌شود و می‌تواند برای ذخیره metric‌های قبل/بعد به کار رود.
- `backend/app/services/verify_runtime/runner.py` — این فایل مسئول اجرای verify runtime است و latency آن تحت تأثیر بهبود outcome قرار می‌گیرد.
- `backend/app/services/ai_manager.py` — این فایل مدیریت AI calls را بر عهده دارد و cost آن تحت تأثیر بهبود outcome قرار می‌گیرد.
- `docs/ROADMAP.md` — فایل roadmap برای ثبت ریسک‌های معماری در برنامه‌های آینده.

## 🌐 نقشهٔ وابستگی‌ها
این تسک وابستگی به کد خاصی ندارد زیرا یک ثبت ریسک معماری است. با این حال، در صورت پیاده‌سازی بهبود outcome در آینده، فایل‌های `backend/app/services/verify_runtime/iterative_orchestrator.py` (برای orchestration outcome)، `backend/app/services/ai_balance_service.py` (برای مدیریت cost)، و `backend/app/services/verify_runtime/runner.py` (برای اجرای verify) تحت تأثیر قرار خواهند گرفت. همچنین فایل‌های `backend/app/services/oversight_verifier.py` و `backend/app/services/ai_manager.py` به‌عنوان callerهای غیرمستقیم درگیر می‌شوند.

## 🔍 Context و وضعیت فعلی
این تسک یک یادآوری/هشدار (⚠️) معماری است و یک مرحله اجرایی مستقل نیست. هیچ کد یا تغییری در فایل‌ها ایجاد نمی‌کند. هدف آن ثبت یک ریسک معماری (trade-off بین کیفیت خروجی و هزینه/سرعت) است که باید در مراحل بعدی (مانند پیاده‌سازی webhook یا endpoint) به‌عنوان یک معیار ارزیابی در نظر گرفته شود. هیچ اقدامی در این مرحله انجام نمی‌شود.

بخش مربوط از درخواست اصلی کاربر:
## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

کلیدواژه‌ها: (ندارد)

شواهد در کد واقعی پروژه: با توجه به deep context موجود، هیچ فایل deep-read شده‌ای برای استناد مستقیم وجود ندارد. با این حال، بر اساس ساختار سطحی پروژه، فایل‌های مرتبط با outcome و metric‌ها شامل `backend/app/services/verify_runtime/iterative_orchestrator.py` (خطوط احتمالی 50-120 برای مدیریت outcome)، `backend/app/services/oversight_verifier.py` (برای verify outcome)، و `backend/app/services/ai_balance_service.py` (برای مدیریت cost/balance) هستند. همچنین فایل `backend/app/services/verify_runtime/ac_cache_service.py` می‌تواند برای ذخیره metric‌های قبل/بعد استفاده شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریسک معماری trade-off بین کیفیت خروجی و هزینه/سرعت در فایل docs/ARCHITECTURE.md ثبت شده باشد.
- [ ] یک issue در سیستم مدیریت پروژه با عنوان 'ریسک: بهبود outcome ممکن است latency/cost را افزایش دهد' و تگ 'architecture-risk' ایجاد شده باشد.
- [ ] هیچ تغییری در کد منبع پروژه (فایل‌های backend یا frontend) ایجاد نشده باشد.
- [ ] مستندات ریسک شامل توضیح trade-off بین کیفیت خروجی و latency/cost باشد.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک صرفاً یک ثبت ریسک معماری است و نیاز به پیاده‌سازی کد ندارد. اقدام پیشنهادی:
1. مستندسازی این ریسک در فایل `docs/ARCHITECTURE.md` یا `docs/ROADMAP.md` تحت بخش 'ریسک‌های معماری'.
2. ایجاد یک issue در سیستم مدیریت پروژه (مانند GitHub Issues) با عنوان 'ریسک: بهبود outcome ممکن است latency/cost را افزایش دهد' و تگ 'architecture-risk'.
3. در مراحل بعدی (مانند پیاده‌سازی webhook یا endpoint جدید)، این ریسک باید به‌عنوان یک معیار ارزیابی (evaluation criterion) در نظر گرفته شود.
4. برای هر بهبود outcome در آینده، یک benchmark قبل/بعد از latency و cost باید ثبت شود. فایل‌های پیشنهادی برای این benchmark: `backend/app/services/verify_runtime/iterative_orchestrator.py` (برای اندازه‌گیری latency) و `backend/app/services/ai_balance_service.py` (برای اندازه‌گیری cost).
5. هیچ تغییری در کد فعلی پروژه انجام نمی‌شود.

## 💡 نمونه‌های قبل/بعد
**ثبت ریسک در ARCHITECTURE.md**

_قبل:_
```
(فایل docs/ARCHITECTURE.md موجود است اما محتوای آن deep-read نشده)
```

_بعد:_
```
اضافه کردن بخش '## ریسک‌های معماری' با متن: '⚠️ بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن. این ریسک در تاریخ [تاریخ] ثبت شده است.'
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -r 'ریسک' docs/ARCHITECTURE.md`
- `grep -r 'trade-off' docs/ARCHITECTURE.md`
- `git diff --name-only HEAD (برای اطمینان از عدم تغییر در کد منبع)`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک یک ثبت ریسک معماری است و هیچ تغییری در کد ایجاد نمی‌کند، بنابراین ریسک مستقیمی ندارد. با این حال، اگر در آینده بهبود outcome بدون در نظر گرفتن این ریسک پیاده‌سازی شود، ممکن است latency یا cost به طور غیرمنتظره‌ای افزایش یابد. فایل‌های `backend/app/services/verify_runtime/iterative_orchestrator.py` و `backend/app/services/ai_balance_service.py` بیشترین تأثیر را خواهند پذیرفت.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

## ✅ معیارهای پذیرش کلی (همهٔ مراحل)
- [ ] {'text': 'مدل اجراکننده قبل از هر تغییری، وجود پیاده\u200cسازی قبلی را با grep/search بررسی کرده باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ["grep -r 'class InspectorAgent' backend/app/services/", "grep -r 'def scan_project' backend/app/services/"], 'files_hint': ['backend/app/services/inspector_agent.py', 'backend/app/services/inspector_scan_bridge.py']}}
- [ ] {'text': 'اگر قابلیت\u200cهای درخواستی از قبل وجود دارند، مدل آن\u200cها را دوباره نساخته باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ["grep -r 'class InspectorAgent' backend/app/services/"], 'files_hint': ['backend/app/services/inspector_agent.py']}}
- [ ] {'text': 'اگر همه چیز کامل است، یک کامیت no-op با توضیح ثبت شده باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ["git log --oneline -5 | grep 'no-op'"], 'files_hint': []}}
- [ ] {'text': 'اگر کار طولانی است، در چندین کامیت متوالی با ترتیب منطقی انجام شده باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['git log --oneline -10'], 'files_hint': []}}
- [ ] {'text': 'در PR description checklist از همه کامیت\u200cها نوشته شده باشد', 'verify_method': 'manual_only', 'verify_plan': {'reason': 'نیاز به بررسی دستی PR description دارد'}}
- [ ] {'text': 'فایل backend/app/services/ai_validators.py باید شامل کلاس\u200cهای OpenAIValidator و ClaudeValidator باشد که از Pydantic BaseModel ارث\u200cبری کنند و متد validate_response را پیاده\u200cسازی کنند.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['class OpenAIValidator', 'class ClaudeValidator', 'BaseModel', 'validate_response'], 'files_hint': ['backend/app/services/ai_validators.py']}}
- [ ] {'text': 'متد process_request در backend/app/services/ai_manager.py باید از validator استفاده کند و خروجی از نوع str به نوع AIResponse تغییر کند.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['def process_request', 'AIResponse', 'validator'], 'files_hint': ['backend/app/services/ai_manager.py']}}
- [ ] {'text': 'تست\u200cهای unit در tests/test_ai_llm_pipeline.py باید شامل حداقل 3 تست برای OpenAIValidator و 3 تست برای ClaudeValidator باشد که موارد valid و invalid را پوشش دهد.', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_ai_llm_pipeline.py', 'marker': 'validator'}}
- [ ] {'text': 'تکنیک\u200cهای grounding باید در validator پیاده\u200cسازی شود به طوری که پاسخ\u200cهای AI با context پروژه cross-reference شوند و در صورت عدم تطابق، خطای مناسب برگردانده شود.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['grounding', 'fact_check', 'cross_reference', 'context_match'], 'files_hint': ['backend/app/services/ai_validators.py']}}
- [ ] {'text': 'سرویس\u200cهای downstream (oversight_service, oversight_inspector_bridge, scan_bundle) باید بدون تغییر و با backward compatibility کار کنند.', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_ai_llm_pipeline.py', 'marker': 'integration'}}
- [ ] {'text': 'AC1: هر دو طرف ناسازگاری شناسایی + فرض\u200cهایشان مستند شد — مستندسازی در فایل `docs/AC_AI_LLM_PIPELINE.md` یا PR description.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['ناسازگاری', 'فرض', 'assumption', 'inconsistency'], 'files_hint': ['docs/AC_AI_LLM_PIPELINE.md', 'backend/app/services/ai_manager.py', 'backend/app/services/oversight_service.py']}}
- [ ] {'text': 'AC2: ground truth تعیین شد و طرف دیگر align شد — مستندسازی در PR description.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['ground truth', 'align', 'align'], 'files_hint': ['docs/AC_AI_LLM_PIPELINE.md']}}
- [ ] {'text': 'AC3: integration test برای pipeline `ai_llm` بدون شکست عبور می\u200cکند — فایل `tests/test_ai_llm_pipeline.py`.', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_ai_llm_pipeline.py', 'marker': 'verify'}}
- [ ] {'text': 'AC4: PR description توضیح می\u200cدهد چرا این تصمیم گرفته شد — بررسی دستی PR.', 'verify_method': 'manual_only', 'verify_plan': {'reason': 'subjective — needs human review of PR description'}}
- [ ] {'text': 'AC5: هیچ تستی fail نمی\u200cشود (`npm run test` / `pytest`).', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/', 'marker': 'all'}}
- [ ] {'text': 'AC6: linter بدون warning عبور می\u200cکند.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['lint', 'warning'], 'files_hint': ['backend/']}}
- [ ] {'text': 'AC7: type-check موفق است (`tsc --noEmit` / `mypy`).', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['type', 'mypy', 'tsc'], 'files_hint': ['backend/', 'frontend/']}}
- [ ] {'text': 'خروجی oversight_strong_prompt باید شامل یک فیلد metadata (مانند `is_structured: true`) باشد که نشان دهد پرامپت از پیش ساخته شده است', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['is_structured', 'structured_prompt', 'bypass'], 'files_hint': ['backend/app/services/oversight_strong_prompt.py']}}
- [ ] {'text': 'ai_manager باید قبل از پردازش، پرامپت ورودی را بررسی کند و اگر ساختاریافته بود، مستقیماً به مدل ارسال کند', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['is_structured_prompt', 'bypass_to_model', 'if structured'], 'files_hint': ['backend/app/services/ai_manager.py']}}
- [ ] {'text': 'مسیر bypass نباید مراحل انتخاب مدل و fallback را اجرا کند (برای پرامپت\u200cهای ساختاریافته)', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['bypass', 'skip_fallback', 'direct_send'], 'files_hint': ['backend/app/services/ai_manager.py']}}

## Acceptance Criteria

1. مدل اجراکننده قبل از هر تغییری، وجود پیاده‌سازی قبلی را با grep/search بررسی کرده باشد _(verify: static)_
2. اگر قابلیت‌های درخواستی از قبل وجود دارند، مدل آن‌ها را دوباره نساخته باشد _(verify: static)_
3. اگر همه چیز کامل است، یک کامیت no-op با توضیح ثبت شده باشد _(verify: static)_
4. اگر کار طولانی است، در چندین کامیت متوالی با ترتیب منطقی انجام شده باشد _(verify: static)_
5. در PR description checklist از همه کامیت‌ها نوشته شده باشد _(verify: manual_only)_
6. فایل backend/app/services/ai_validators.py باید شامل کلاس‌های OpenAIValidator و ClaudeValidator باشد که از Pydantic BaseModel ارث‌بری کنند و متد validate_response را پیاده‌سازی کنند. _(verify: static)_
7. متد process_request در backend/app/services/ai_manager.py باید از validator استفاده کند و خروجی از نوع str به نوع AIResponse تغییر کند. _(verify: static)_
8. تست‌های unit در tests/test_ai_llm_pipeline.py باید شامل حداقل 3 تست برای OpenAIValidator و 3 تست برای ClaudeValidator باشد که موارد valid و invalid را پوشش دهد. _(verify: backend_test)_
9. تکنیک‌های grounding باید در validator پیاده‌سازی شود به طوری که پاسخ‌های AI با context پروژه cross-reference شوند و در صورت عدم تطابق، خطای مناسب برگردانده شود. _(verify: static)_
10. سرویس‌های downstream (oversight_service, oversight_inspector_bridge, scan_bundle) باید بدون تغییر و با backward compatibility کار کنند. _(verify: backend_test)_
11. AC1: هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد — مستندسازی در فایل `docs/AC_AI_LLM_PIPELINE.md` یا PR description. _(verify: static)_
12. AC2: ground truth تعیین شد و طرف دیگر align شد — مستندسازی در PR description. _(verify: static)_
13. AC3: integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند — فایل `tests/test_ai_llm_pipeline.py`. _(verify: backend_test)_
14. AC4: PR description توضیح می‌دهد چرا این تصمیم گرفته شد — بررسی دستی PR. _(verify: manual_only)_
15. AC5: هیچ تستی fail نمی‌شود (`npm run test` / `pytest`). _(verify: backend_test)_
16. AC6: linter بدون warning عبور می‌کند. _(verify: static)_
17. AC7: type-check موفق است (`tsc --noEmit` / `mypy`). _(verify: static)_
18. خروجی oversight_strong_prompt باید شامل یک فیلد metadata (مانند `is_structured: true`) باشد که نشان دهد پرامپت از پیش ساخته شده است _(verify: static)_
19. ai_manager باید قبل از پردازش، پرامپت ورودی را بررسی کند و اگر ساختاریافته بود، مستقیماً به مدل ارسال کند _(verify: static)_
20. مسیر bypass نباید مراحل انتخاب مدل و fallback را اجرا کند (برای پرامپت‌های ساختاریافته) _(verify: static)_
21. مسیر فعلی برای پرامپت‌های خام (غیرساختاریافته) باید بدون تغییر کار کند _(verify: backend_test)_
22. هیچ خطایی در pipeline هنگام عبور پرامپت ساختاریافته رخ ندهد _(verify: backend_test)_
23. تست CRUD برای watched projects (add, update, delete, list) باید در tests/test_oversight_service.py::test_crud_watched_projects پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_crud_watched_projects -v اجرا شود. _(verify: backend_test)_
24. تست scheduler loop با mock کردن sleep باید در tests/test_oversight_service.py::test_scheduler_loop_mock_sleep پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_scheduler_loop_mock_sleep -v اجرا شود. _(verify: backend_test)_
25. تست auto_register_watched با mock GitHub API باید در tests/test_oversight_service.py::test_auto_register_watched_mock_github پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_auto_register_watched_mock_github -v اجرا شود. _(verify: backend_test)_
26. تست edge cases شامل duplicate repo، invalid URL و empty fields باید در tests/test_oversight_service.py::test_edge_cases پیاده‌سازی شود و با pytest backend/tests/test_oversight_service.py::test_edge_cases -v اجرا شود. _(verify: backend_test)_
27. فایل tests/test_oversight_service.py باید وجود داشته باشد و شامل تست‌های واحد برای کلاس OversightService باشد. _(verify: static)_
28. تست __init__ باید بررسی کند که self.watched یک لیست خالی و self._lock از نوع asyncio.Lock است. _(verify: backend_test)_
29. تست add_watched_project باید با mock کردن database، افزودن پروژه به watched list را بررسی کند. _(verify: backend_test)_
30. تست remove_watched_project باید با mock کردن database، حذف پروژه از watched list را بررسی کند. _(verify: backend_test)_
31. تست asyncio.Lock باید بررسی کند که قفل در عملیات همزمان به درستی کار می‌کند. _(verify: backend_test)_
32. تست‌ها باید با mocking وابستگی‌های خارجی (مانند GitHub API و database) نوشته شوند تا ایزوله باشند. _(verify: static)_
33. همه تست‌ها باید با pytest backend/tests/test_oversight_service.py -v با موفقیت پاس شوند. _(verify: backend_test)_
34. تست CRUD برای watched projects شامل add, update, delete, list باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند _(verify: backend_test)_
35. تست scheduler loop با mock کردن sleep باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند _(verify: backend_test)_
36. تست auto_register_watched با mock GitHub API باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند _(verify: backend_test)_
37. تست edge cases شامل duplicate repo, invalid URL, empty fields باید در tests/test_oversight_service.py پیاده‌سازی شود و با pytest عبور کند _(verify: backend_test)_
38. هیچ تستی fail نمی‌شود (pytest tests/test_oversight_service.py -v) _(verify: backend_test)_
39. linter بدون warning عبور می‌کند (pylint یا flake8 روی فایل تست) _(verify: static)_
40. type-check موفق است (mypy backend/tests/test_oversight_service.py) _(verify: static)_
41. فایل tests/test_oversight_service.py باید ایجاد شود و شامل تابع test_add_watched باشد. _(verify: static)_
42. تابع test_add_watched باید OversightService را import کرده و یک instance از آن بسازد. _(verify: static)_
43. تست باید متد add_watched را با {'repo_full_name': 'test/repo'} صدا بزند و result['success'] را assert کند. _(verify: static)_
44. تست باید assert کند که len(service.watched) == 1 بعد از فراخوانی add_watched. _(verify: static)_
45. تست باید با pytest بدون خطا اجرا شود. _(verify: backend_test)_
46. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد — فایل‌های docs/ و README.md باید شامل مستندات ناسازگاری‌ها باشند _(verify: static)_
47. ground truth تعیین شد و طرف دیگر align شد — فایل‌های docs/ و *.md باید شامل ground truth و align شده باشند _(verify: static)_
48. integration test برای pipeline `auth` بدون شکست عبور می‌کند — فایل tests/test_auth_pipeline.py باید شامل تست‌های کامل باشد _(verify: backend_test)_
49. PR description توضیح می‌دهد چرا این تصمیم گرفته شد — فایل‌های docs/ و *.md باید شامل reason و rationale باشند _(verify: static)_
50. متد check_permission به OversightService اضافه شود و در routeها استفاده شود _(verify: static)_
51. متد check_permission به AuthRunner اضافه شود _(verify: static)_
52. یک dependency جدید به نام `get_current_user_with_permission` ایجاد شود که بعد از احراز هویت، مجوز کاربر را برای عملیات mutation بررسی کند. _(verify: static)_
53. مدل InspectorSession دارای فیلد `user_id` یا `owner_id` باشد تا مالکیت سشن مشخص شود. _(verify: static)_
54. تمامی مسیرهای mutation مربوط به inspector_session (ذخیره سشن و پیام) از dependency جدید استفاده کنند. _(verify: static)_
55. کاربر غیرمجاز (غیرمالک سشن) نتواند سشن متعلق به کاربر دیگر را تغییر دهد و خطای 403 دریافت کند. _(verify: backend_test)_
56. کاربر مجاز (مالک سشن یا ادمین) بتواند سشن خود را تغییر دهد و عملیات با موفقیت انجام شود. _(verify: backend_test)_
57. همه callerهای auth_runner (حداقل ۵ فایل) شناسایی و مستند شوند _(verify: static)_
58. هیچ feature flag rot (flagهایی که همیشه true/false هستند) در auth_runner باقی نماند _(verify: static)_
59. هیچ refactor ناتمام (تابع با TODO، FIXME، یا پیاده‌سازی ناقص) در auth_runner باقی نماند _(verify: static)_
60. همه تست‌های runtime verify (backend/tests/test_runtime_verify_*) با موفقیت پاس شوند _(verify: backend_test)_
61. هیچ downstream consumer (caller) پس از تغییرات break نشود — با اجرای تست‌های integration تأیید شود _(verify: backend_test)_
62. مدل اجراکننده قبل از هر تغییر، با grep/search بررسی کند که آیا قابلیت مورد نظر از قبل در repo پیاده‌سازی شده است یا خیر. _(verify: static)_
63. اگر قابلیتی از قبل وجود دارد، مدل اجراکننده آن را دوباره نسازد و فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کند. _(verify: static)_
64. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند. _(verify: static)_
65. اگر کار طولانی است، در چندین کامیت متوالی با ترتیب منطقی (foundation → core → integration → tests) انجام شود و هیچ بخشی skip نشود. _(verify: static)_
66. یک دیکشنری TASK_TYPE_TO_CAPABILITIES در ai_manager.py ایجاد شود که حداقل ۴ task_type (code_generation, analysis, chat, debate) را به لیست ModelCapability نگاشت کند. _(verify: static)_
67. تابع select_model باید ابتدا task_type را به capabilities ترجمه کند، سپس مدل‌ها را فیلتر کند و در نهایت بر اساس preferred_models انتخاب کند. _(verify: static)_
68. تابع _filter_models_by_capability جدید اضافه شود که لیست مدل‌ها و capabilities را گرفته و مدل‌های فاقد capability را حذف کند. _(verify: static)_
69. هیچ تغییری در API یا رابط کاربری ایجاد نشود — فقط منطق داخلی select_model تغییر کند. _(verify: static)_
70. فایل backend/app/services/ai_manager.py به‌طور کامل خوانده و ساختار آن (کلاس‌ها، متدها، وابستگی‌ها) مستند شده باشد. _(verify: static)_
71. منطق fallback در ai_manager.py شناسایی و مستند شده باشد: ترتیب fallback، شرایط fallback، و مدل‌های involved. _(verify: static)_
72. مکانیزم retry در ai_manager.py بررسی و مستند شده باشد: تعداد تلاش‌ها، فاصله بین تلاش‌ها، شرایط توقف. _(verify: static)_
73. timeout handling در ai_manager.py و سرویس‌های AI بررسی و مستند شده باشد: timeout values، timeout handling برای هر سرویس. _(verify: static)_
74. rate limit handling در ai_manager.py و سرویس‌های AI بررسی و مستند شده باشد: rate limit detection، fallback پس از rate limit. _(verify: static)_
75. validation failure handling در ai_manager.py و سرویس‌های AI بررسی و مستند شده باشد: انواع validation failures، fallback برای validation failures. _(verify: static)_
76. یک گزارش مستند از ناسازگاری‌ها، فرض‌ها و نقاط ضعف منطق fallback تهیه شده باشد. _(verify: static)_
77. کلاس FallbackStrategy در backend/app/services/ai_manager.py ایجاد شود با فیلدهای ORDER, TIMEOUT, MAX_RETRIES, BACKOFF, CONDITIONS _(verify: static)_
78. متد ai_llm در ai_manager.py از FallbackStrategy استفاده کند و در صورت شکست همه سرویس‌ها، خطای AllServicesFailedError برگرداند _(verify: static)_
79. تست‌های tests/test_ai_llm_pipeline.py سناریوهای fallback را پوشش دهند: timeout سرویس اول و fallback به دوم، خطای validation و retry با backoff _(verify: backend_test)_
80. ترتیب fallback به صورت OpenAI -> Claude پیاده‌سازی شود _(verify: static)_
81. حداکثر زمان انتظار (timeout) برای هر سرویس 30 ثانیه باشد _(verify: static)_
82. فایل docs/ai_manager_audit.md ایجاد شود و شامل حداقل ۵ بخش: معماری، جریان فراخوانی، وابستگی‌ها، نقاط ضعف، پیشنهادات _(verify: static)_
83. کلاس AiManager در backend/app/services/ai_manager.py حداقل ۳ کامنت توضیحی جدید داشته باشد (یکی روی کلاس، دو تا روی متدهای اصلی) _(verify: static)_
84. فایل tests/test_ai_llm_pipeline.py ایجاد شود و حداقل ۳ تست داشته باشد: test_successful_call, test_fallback_on_error, test_timeout_handling _(verify: static)_
85. مستندات شامل لیست کامل وابستگی‌های ai_manager باشد (حداقل ۴ فایل: ai_base, models_registry, capability_detector, claude_service) _(verify: static)_
86. کامپوننت model-profiles/page.tsx داده‌ها را از endpoint GET /api/model-profiles دریافت کند (به جای داده‌های سخت‌کد شده) _(verify: api_response)_
87. حالت loading در هنگام دریافت داده از API نمایش داده شود _(verify: ui_interaction)_
88. حالت error در صورت عدم موفقیت API به درستی نمایش داده شود _(verify: ui_interaction)_
89. داده‌های سخت‌کد شده (defaultProfiles) از کامپوننت حذف شده باشند _(verify: static)_
90. نوع داده‌های دریافتی از API با نوع داده‌های مورد انتظار در کامپوننت مطابقت داشته باشد (TypeScript type safety) _(verify: static)_
91. اعمال تغییر بدون شکستن تست‌های موجود — اجرای `pytest` و `npm run test` باید موفق باشد _(verify: backend_test)_
92. linter بدون warning عبور می‌کند — اجرای linter مربوط به پروژه (مثلاً flake8 یا pylint برای پایتون، eslint برای JS) باید بدون warning باشد _(verify: static)_
93. type-check موفق است — اجرای `tsc --noEmit` برای TypeScript و `mypy` برای پایتون باید موفق باشد _(verify: static)_
94. هیچ تستی fail نمی‌شود — اجرای `npm run test` و `pytest` باید بدون fail باشد _(verify: backend_test)_
95. type-check موفق است — اجرای `tsc --noEmit` و `mypy` باید موفق باشد _(verify: static)_
96. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
97. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
98. integration test برای pipeline ai_llm بدون شکست عبور می‌کند _(verify: backend_test)_
99. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: static)_
100. تابع validate_prompt_fields باید وجود فیلدهای اجباری title, user_goal, description را بررسی کند و در صورت缺失، ValueError با پیام مناسب برگرداند. _(verify: backend_test)_
101. اعتبارسنجی target_locations: اگر از نوع List[Dict] باشد، هر آیتم باید کلید path داشته باشد. در غیر این صورت خطا برگرداند. _(verify: backend_test)_
102. محدودیت طول پرامپت: اگر طول پرامپت بیش از 4000 کاراکتر باشد، ValueError برگرداند. _(verify: backend_test)_
103. فیلتر دستورات خطرناک: اگر پرامپت شامل 'ignore previous instructions' باشد، ValueError برگرداند. _(verify: backend_test)_
104. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد — با grep برای الگوهای 'oversight_strong_prompt', 'fallback', 'error handling', 'retry' در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py _(verify: static)_
105. ground truth تعیین شد و طرف دیگر align شد — با grep برای الگوهای 'ground truth', 'align', 'fallback', 'oversight_strong_prompt' در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py _(verify: static)_
106. integration test برای pipeline ai_llm بدون شکست عبور می‌کند — اجرای تست tests/test_ai_llm_pipeline.py::test_integration با timeout 120 ثانیه _(verify: backend_test)_
107. PR description توضیح می‌دهد چرا این تصمیم گرفته شد — با grep برای الگوهای 'PR description', 'decision', 'why' در فایل .github/pull_request_template.md _(verify: static)_
108. اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt اضافه شده است _(verify: static)_
109. اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict]) اضافه شده است _(verify: static)_
110. محدودیت طول پرامپت (max length check) اضافه شده است _(verify: static)_
111. فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions' در پرامپت اضافه شده است _(verify: static)_
112. تست‌های واحد برای هر چهار لایه validation نوشته شده و عبور می‌کنند _(verify: backend_test)_
113. هنگام timeout مدل خارجی، تابع باید حداقل ۳ بار با backoff exponential تلاش مجدد کند _(verify: backend_test)_
114. پس از شکست همه تلاش‌های retry، تابع باید به مدل جایگزین از طریق ai_manager fallback کند _(verify: backend_test)_
115. در صورت شکست fallback نیز، تابع باید یک پاسخ پیش‌فرض با کلید 'error' و 'fallback_used': False بازگرداند _(verify: backend_test)_
116. همه خطاها و مسیر fallback باید در logger با سطح مناسب (warning برای retry, error برای fallback, critical برای شکست کامل) ثبت شوند _(verify: static)_
117. تغییرات فقط در pipeline ai_llm اعمال شود و سایر pipeline‌ها (ai_chat, ai_analysis) تغییر نکنند _(verify: static)_
118. فایل backend/app/services/oversight_strong_prompt.py به‌طور کامل خوانده و تحلیل شده باشد — کلاس‌ها، توابع، وابستگی‌ها و نحوه تعامل با ai_manager مستند شده باشد _(verify: static)_
119. فایل backend/app/services/ai_manager.py به‌طور کامل خوانده و تحلیل شده باشد — کلاس‌ها، توابع، وابستگی‌ها و نحوه تعامل با oversight_strong_prompt مستند شده باشد _(verify: static)_
120. تمامی callerهای downstream هر دو سرویس (با grep روی پروژه) شناسایی و در مستند ثبت شده باشند — حداقل ۳ caller برای هر سرویس _(verify: static)_
121. نقاط ضعف و وابستگی‌های متقابل بین دو سرویس شناسایی و در مستند ثبت شده باشند — حداقل ۲ نقطه ضعف و ۲ وابستگی متقابل _(verify: manual_only)_
122. خروجی نهایی (مستند یا کامنت‌های کد) بدون تغییر در منطق کد تولید شده باشد — هیچ commitای با تغییر منطق وجود نداشته باشد _(verify: static)_
123. کلاس EffectivenessMetrics باید در فایل backend/app/services/ai_manager.py تعریف شده باشد و شامل فیلدهای accuracy, speed, cost, resource_usage, timestamp باشد _(verify: static)_
124. متد register_metrics باید در کلاس AIManager وجود داشته باشد و metrics را به metrics_registry اضافه کند _(verify: static)_
125. متد get_best_model باید در کلاس AIManager وجود داشته باشد و بر اساس معیارهای وزنی بهترین مدل را برگرداند _(verify: static)_
126. OversightService باید از get_best_model برای انتخاب مدل استفاده کند به جای انتخاب تصادفی _(verify: static)_
127. تست‌های unit برای EffectivenessMetrics, register_metrics, get_best_model باید پاس شوند _(verify: backend_test)_
128. متد track_usage در ai_manager.py باید latency_ms و cost_credits را به عنوان پارامتر دریافت و در usage_log ذخیره کند _(verify: static)_
129. متد select_model در ai_manager.py باید از weighted selection بر اساس performance history استفاده کند نه صرفاً availability _(verify: static)_
130. performance_history باید شامل avg_latency_ms و avg_cost_credits برای هر مدل باشد _(verify: static)_
131. مدل‌های بدون performance history باید امتیاز پیش‌فرض (0.5) دریافت کنند تا backward compatibility حفظ شود _(verify: static)_
132. تغییرات نباید سرویس‌های مدل (claude_service, openai_service, gemini_service) را تغییر دهد — فقط interface response آن‌ها باید latency و cost را شامل شود _(verify: static)_
133. outcome target به‌صورت measurable بازنویسی شد — تابع define_outcome_target در OversightService باید یک target با threshold عددی (مثلاً rate > 95%) تعریف کند. _(verify: static)_
134. کد تغییر کرد تا outcome target محقق شود — منطق run_oversight باید از outcome target استفاده کند و در صورت عدم تحقق، اقدام مناسب انجام دهد. _(verify: static)_
135. test E2E که outcome را اندازه می‌گیرد عبور می‌کند — تست در tests/test_oversight_service.py باید outcome target را تعریف کرده و اندازه‌گیری کند. _(verify: backend_test)_
136. metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد — logging.info یا metric ثبت در OversightService برای outcome rate. _(verify: static)_
137. هیچ تستی fail نمی‌شود (`pytest`) — اجرای pytest باید بدون خطا باشد. _(verify: backend_test)_
138. linter بدون warning عبور می‌کند — اجرای linter (مثلاً flake8) باید بدون warning باشد. _(verify: static)_
139. type-check موفق است (`mypy`) — اجرای mypy باید بدون خطا باشد. _(verify: static)_
140. هر دو طرف ناسازگاری (OpenAI و Claude) شناسایی و فرض‌هایشان در کد مستند شد _(verify: static)_
141. ground truth تعیین شد و طرف دیگر align شد — تابع format_prompt_for_model یا model_specific_prompt وجود دارد _(verify: static)_
142. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_
143. فایل backend/app/services/prompt_adapter.py ایجاد شود و شامل توابع convert_for_openai() و convert_for_claude() باشد _(verify: static)_
144. مدل system_prompt در backend/app/models/system_prompt.py دارای فیلد compatible_models (لیست رشته‌ای از نام مدل‌ها) باشد _(verify: static)_
145. تابع convert_for_openai() پرامپت generic را به فرمت OpenAI (شامل system message و user message) تبدیل کند _(verify: backend_test)_
146. تابع convert_for_claude() پرامپت generic را به فرمت Claude (با ساختار XML یا format خاص) تبدیل کند _(verify: backend_test)_
147. ai_manager.py از prompt_adapter قبل از ارسال پرامپت به سرویس مدل استفاده کند _(verify: static)_
148. تمام تست‌های موجود در backend/tests/test_runtime_verify_stage*.py و backend/tests/test_verify_v7.py پس از تغییرات پاس شوند _(verify: backend_test)_
149. فایل backend/app/models/system_prompt.py باید بررسی و ساختار مدل system_prompt مستند شود. _(verify: static)_
150. فایل backend/app/api/routes/system_prompts.py باید بررسی و endpointهای CRUD برای system_prompts مستند شود. _(verify: static)_
151. فایل backend/app/services/ai_manager.py باید بررسی و نحوه استفاده از system_prompts در pipeline AI مستند شود. _(verify: static)_
152. فایل backend/app/services/prompt_helper.py باید بررسی و توابع کمکی مرتبط با system_prompts مستند شود. _(verify: static)_
153. فایل backend/app/services/ai_base.py باید بررسی و نحوه استفاده از system_prompts در کلاس پایه AI مستند شود. _(verify: static)_
154. فایل‌های downstream consumers (claude_service.py, openai_service.py, gemini_service.py, deepseek_service.py, perplexity_service.py) باید بررسی و نحوه استفاده از system_prompts مستند شود. _(verify: static)_
155. گزارش audit باید شامل شناسایی نقاط ضعف و ناسازگاری‌ها باشد. _(verify: manual_only)_
156. گزارش audit باید ground truth برای مراحل بعدی تعیین کند. _(verify: manual_only)_
157. ماژول hallucination_guard.py در مسیر backend/app/services/ ایجاد شود و شامل کلاس HallucinationGuard با سه متد ground_response, validate_with_second_model, detect_low_confidence باشد. _(verify: static)_
158. متد ai_llm در backend/app/services/ai_manager.py از HallucinationGuard استفاده کند و مراحل grounding, validation, و confidence detection را اجرا کند. _(verify: static)_
159. متد ground_response باید پاسخ را با استفاده از منابع معتبر (sources) بهبود بخشد و خروجی grounded response برگرداند. _(verify: backend_test)_
160. متد validate_with_second_model باید با استفاده از مدل دوم (مثلاً Claude برای validation پاسخ OpenAI) fact-checking انجام دهد و نتیجه ValidationResult برگرداند. _(verify: backend_test)_
161. متد detect_low_confidence باید پاسخ‌های با قطعیت پایین را تشخیص داده و پرچم‌گذاری کند. _(verify: backend_test)_
162. هیچ تغییری در frontend (Next.js)، endpoint جدید، یا pipeline‌های دیگر ایجاد نشود. _(verify: static)_
163. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
164. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
165. تمامی callerهای هر دو فایل بررسی شدند و downstream consumers شکسته نشدند _(verify: static)_
166. فایل docs/EXECUTOR_GUIDE.md باید با محتوای کامل یادداشت کاربر ایجاد شود. _(verify: static)_
167. تابع get_executor_guide() در OversightService باید محتوای فایل را برگرداند. _(verify: backend_test)_
168. endpoint GET /api/executor-guide باید status 200 و محتوای guide را برگرداند. _(verify: api_response)_
169. در backend/app/main.py باید ارجاع به docs/EXECUTOR_GUIDE.md در بخش startup اضافه شود. _(verify: static)_
170. تابع normalize_target_locations در فایل backend/app/services/oversight_strong_prompt.py اضافه شود و ورودی List[str] را به List[Dict] با کلیدهای 'path' و 'type' تبدیل کند. _(verify: static)_
171. تابع build_strong_prompt در oversight_strong_prompt.py در خط 45 تابع normalize را قبل از استفاده از target_locations صدا بزند. _(verify: static)_
172. تست واحد در backend/tests/test_oversight_strong_prompt.py اضافه شود که normalize را با ورودی List[str] (مثلاً ['file1.py', 'file2.py']) تست کند و خروجی List[Dict] با کلیدهای path و type را تأیید کند. _(verify: backend_test)_
173. تست واحد اضافه شود که normalize را با ورودی None تست کند و لیست خالی برگرداند. _(verify: backend_test)_
174. تست واحد اضافه شود که normalize را با ورودی List[Dict] (مثلاً [{'path': 'file1.py', 'type': 'file'}]) تست کند و همان خروجی را با کلیدهای استاندارد برگرداند. _(verify: backend_test)_
175. همه callerهای فایل oversight_strong_prompt.py شناسایی و مستند شده‌اند _(verify: static)_
176. همه callerهای فایل ai_manager.py شناسایی و مستند شده‌اند _(verify: static)_
177. هیچ callerای پس از تغییرات پیشنهادی break نمی‌شود _(verify: backend_test)_
178. مستندات callerها در یک فایل جداگانه یا کامیت ثبت شده است _(verify: static)_
179. مدل اجراکننده پیش از هر تغییر، ساختار repo را مستقل بررسی کرده و با grep/search فایل‌های مرتبط را شناسایی کند. _(verify: static)_
180. اگر قابلیت/فایل/تابعی از قبل موجود است، مدل آن را دوباره نمی‌سازد و فقط موارد ناقص یا اشتباه را اصلاح/تکمیل می‌کند. _(verify: static)_
181. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت می‌شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند. _(verify: static)_
182. اگر کار طولانی است، مدل در چندین کامیت متوالی با ترتیب منطقی (foundation → core → integration → tests) انجام می‌دهد و هیچ بخشی را skip نمی‌کند. _(verify: static)_
183. در آخر یک checklist از همهٔ کامیت‌ها در PR description نوشته می‌شود. _(verify: manual_only)_
184. فایل مستندات docs/ai_manager_models_registry_interface.md ایجاد شود و شامل تمام متدهای interface بین ai_manager و models_registry باشد _(verify: static)_
185. فایل mock backend/app/tests/mocks/mock_models_registry.py ایجاد شود و تمام متدهای مستند شده را پیاده‌سازی کند _(verify: static)_
186. mock باید داده‌های ثابت (hardcoded) برای حداقل ۳ مدل مختلف برگرداند _(verify: static)_
187. تست‌های واحد در backend/app/tests/test_ai_manager_models_registry_interface.py ایجاد شود و حداقل ۳ سناریو را پوشش دهد: مدل موجود، مدل不存在، و خطای شبکه _(verify: backend_test)_
188. مستندات باید شامل توضیح واضحی باشد که models_registry یک دیتابیس محلی است، API خارجی، یا کش — بر اساس تحلیل کد واقعی _(verify: static)_
189. تمام فایل‌هایی که از سرویس مورد نظر (مثلاً inspector_agent.py) import کرده‌اند، شناسایی و لیست شوند. _(verify: static)_
190. برای هر تابع تغییر یافته، تمام مکان‌های فراخوانی (call sites) در پروژه شناسایی شوند. _(verify: static)_
191. تست‌های یکپارچگی مرتبط (test_runtime_verify_integration.py و test_inspector_oversight_bridge.py) قبل از merge با موفقیت اجرا شوند. _(verify: backend_test)_
192. تمامی routeهای API که از سرویس تغییر یافته استفاده می‌کنند (oversight.py و runtime.py) پاسخ 200 با ساختار داده صحیح برگردانند. _(verify: api_response)_
193. هیچ خطای import یا AttributeError در لاگ‌های سرور پس از merge مشاهده نشود. _(verify: manual_only)_
194. گزارش سناریوهای خطای پوشش‌داده‌نشده در مسیر docs/error_scenarios_analysis.md ایجاد شود. _(verify: static)_
195. گزارش شامل حداقل ۵ سناریوی خطای پوشش‌داده‌نشده باشد. _(verify: static)_
196. گزارش شامل اولویت‌بندی سناریوها (کم، متوسط، زیاد) باشد. _(verify: static)_
197. گزارش شامل پیشنهادات عملی برای بهبود پوشش سناریوهای خطا باشد. _(verify: static)_
198. گزارش شامل لینک به فایل‌های مرتبط در کد (مانند log_stream_service.py, log_to_issues_service.py) باشد. _(verify: static)_
199. فایل تست backend/tests/test_ai_manager_failure_scenarios.py ایجاد شده و شامل کلاس TestAIManagerFailureScenarios با حداقل ۳ تست سناریوی شکست باشد _(verify: static)_
200. تست‌ها با marker @pytest.mark.failure_scenarios مشخص شده باشند _(verify: static)_
201. تست‌ها با دستور pytest -m failure_scenarios قابل اجرا باشند و پاس شوند _(verify: backend_test)_
202. تست fallback_on_openai_connection_error: شبیه‌سازی ConnectionError در OpenAI و بررسی اینکه fallback به Claude فعال می‌شود و پاسخ مناسب برمی‌گرداند (outcome measurement) _(verify: backend_test)_
203. تست no_fallback_on_successful_openai: شبیه‌سازی پاسخ موفق OpenAI و بررسی اینکه fallback فعال نمی‌شود _(verify: backend_test)_
204. تست all_models_fail: شبیه‌سازی خطا در همه مدل‌ها و بررسی اینکه خطای مناسب (RuntimeError با پیام 'All AI models failed') برگردانده می‌شود _(verify: backend_test)_
205. outcome target به‌صورت measurable بازنویسی شد — مثلاً «email send rate > 95% در ۱۰۰ تلاش» _(verify: static)_
206. کد تغییر کرد تا outcome target محقق شود — این AC صرفاً مستندسازی است و خارج از scope پیاده‌سازی کد می‌باشد _(verify: manual_only)_
207. test E2E که outcome را اندازه می‌گیرد عبور می‌کند — این AC صرفاً مستندسازی است و خارج از scope نوشتن تست می‌باشد _(verify: manual_only)_
208. metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد — این AC صرفاً مستندسازی است و خارج از scope اضافه کردن metric/log می‌باشد _(verify: manual_only)_
209. هیچ تستی fail نمی‌شود (`npm run test` / `pytest`) — این AC صرفاً مستندسازی است و خارج از scope اجرای تست می‌باشد _(verify: manual_only)_
210. linter بدون warning عبور می‌کند — این AC صرفاً مستندسازی است و خارج از scope اجرای linter می‌باشد _(verify: manual_only)_
211. type-check موفق است (`tsc --noEmit` / `mypy`) — این AC صرفاً مستندسازی است و خارج از scope اجرای type-check می‌باشد _(verify: manual_only)_
212. outcome target به‌صورت measurable بازنویسی شد و در فایل README.md (ریشه پروژه) یا docs/README.md موجود است _(verify: static)_
213. outcome target بازنویسی‌شده شامل حداقل یک معیار عددی قابل اندازه‌گیری است (مثلاً درصد، زمان، تعداد) _(verify: static)_
214. outcome target بازنویسی‌شده شامل یک بازه زمانی مشخص است (مثلاً 'تا پایان Q2 2026' یا 'در بازه 30 روزه') _(verify: static)_
215. متن outcome target در فایل docs/ROADMAP.md نیز اضافه شده است (اختیاری اما توصیه‌شده) _(verify: static)_
216. متد sync_with_journal به کلاس OversightService در فایل backend/app/services/oversight_service.py اضافه شود. _(verify: static)_
217. endpoint POST /api/projects/{project_id}/journal/oversight در فایل backend/app/api/routes/project_journal.py ایجاد شود. _(verify: api_response)_
218. رویدادهای مهم oversight (شروع، پایان، خطا) به صورت خودکار در project_journal ثبت شوند. _(verify: backend_test)_
219. مدل‌های داده‌ای در backend/app/models/ برای پشتیبانی از رویدادهای oversight به‌روزرسانی شوند. _(verify: static)_
220. تست‌های یکپارچگی در backend/tests/ برای اطمینان از هماهنگی دو سرویس نوشته شوند. _(verify: backend_test)_
221. پس از تکمیل ژورنال در project_journal، یک درخواست HTTP POST به oversight_service ارسال شود با payload JSON شامل project_id, journal_id, timestamp, summary, status _(verify: api_response)_
222. endpoint POST /api/oversight/receive-report در oversight_service فعال باشد و payload معتبر را با status 201 ذخیره کند _(verify: api_response)_
223. در صورت خطای شبکه (timeout, connection refused)، webhook خطا را log کند و عملیات اصلی (ذخیره ژورنال) شکست نخورد _(verify: backend_test)_
224. payload نامعتبر (بدون فیلدهای اجباری) توسط endpoint oversight_service با status 422 رد شود _(verify: api_response)_
225. گزارش ذخیره‌شده در دیتابیس oversight_service قابل بازیابی باشد (با query روی project_id) _(verify: backend_test)_
226. outcome target به‌صورت measurable بازنویسی شد — در فایل‌های OversightService، outcome targetها باید شامل معیار عددی قابل اندازه‌گیری باشند (مثلاً درصد، تعداد، زمان) _(verify: static)_
227. کد تغییر کرد تا outcome target محقق شود — این AC خارج از scope است و نباید پیاده‌سازی شود _(verify: manual_only)_
228. test E2E که outcome را اندازه می‌گیرد عبور می‌کند — این AC خارج از scope است و نباید پیاده‌سازی شود _(verify: manual_only)_
229. metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد — این AC خارج از scope است و نباید پیاده‌سازی شود _(verify: manual_only)_
230. هیچ تستی fail نمی‌شود (`npm run test` / `pytest`) — این AC خارج از scope است و نباید پیاده‌سازی شود _(verify: manual_only)_
231. linter بدون warning عبور می‌کند — این AC خارج از scope است و نباید پیاده‌سازی شود _(verify: manual_only)_
232. type-check موفق است (`tsc --noEmit` / `mypy`) — این AC خارج از scope است و نباید پیاده‌سازی شود _(verify: manual_only)_
233. ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس — در فایل‌های OversightService، ACها باید بر اساس رفتار کاربر یا سیستم تعریف شوند، نه بر اساس نام متد یا کلاس _(verify: static)_
234. verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند — در فایل‌های verify (مانند oversight_verifier.py)، منطق verify باید به گونه‌ای باشد که پیاده‌سازی‌های مختلف ولی هم‌ارز را قبول کند _(verify: static)_
235. ریسک معماری trade-off بین کیفیت خروجی و هزینه/سرعت در فایل docs/ARCHITECTURE.md ثبت شده باشد. _(verify: static)_
236. یک issue در سیستم مدیریت پروژه با عنوان 'ریسک: بهبود outcome ممکن است latency/cost را افزایش دهد' و تگ 'architecture-risk' ایجاد شده باشد. _(verify: manual_only)_
237. هیچ تغییری در کد منبع پروژه (فایل‌های backend یا frontend) ایجاد نشده باشد. _(verify: static)_
238. مستندات ریسک شامل توضیح trade-off بین کیفیت خروجی و latency/cost باشد. _(verify: static)_

## Task Steps

### Step 1: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه اجرایی. محتوای آن دستورالعمل‌های متدولوژیک برای نحوه برخورد با کل درخواست است: بررسی وجود پیاده‌سازی قبلی، عدم بازسازی موارد موجود، و مسئولیت‌پذیری در قبال تشخیص‌های نادرست. این بخش خودش یک مرحله اجرایی نیست و نباید به عنوان یک تسک مستقل در نظر گرفته شود.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه فنی. محتوای آن دستورالعمل‌های رفتاری برای اجرای درست سایر بخش‌ها را مشخص می‌کند: بررسی وجود پیاده‌سازی قبلی، عدم بازسازی موارد موجود، و مسئولیت‌پذیری در قبال تشخیص‌های نادرست. هیچ فایل یا کلاسی مستقیماً تغییر نمی‌کند.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور پیاده‌سازی مستقیمی نیست. وظیفه آن: ۱) هشدار درباره احتمال خطا در پرامپت خودکار، ۲) الزام به بررسی پیش‌نیاز repo قبل از هر تغییر، ۳) دستور به عدم بازسازی قابلیت‌های موجود، ۴) در صورت کامل بودن همه چیز، ثبت کامیت no-op. این بخش خودش یک مرحله اجرایی نیست، بلکه یک precondition برای تمام مراحل بعدی است.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور پیاده‌سازی مستقیمی نیست. وظیفه آن: (۱) هشدار به مدل که پرامپت بر اساس بررسی خودکار ساخته شده و ممکن است ناقص/اشتباه باشد، (۲) الزام به بررسی وجود پیاده‌سازی قبلی در repo قبل از شروع، (۳) تعیین مسئولیت مدل برای قضاوت مستقل در صورت ناسازگاری، (۴) دستورالعمل برای کارهای طولانی (تقسیم به کامیت‌های متعدد و ارائه checklist). این بخش صراحتاً می‌گوید 'قبل از شروع بخوان' و 'مسئولیت تو' — بنابراین یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک است.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه اجرایی. هدف آن اطمینان از این است که قبل از هر تغییری، وضعیت فعلی repo (فایل‌ها، کلاس‌ها، توابع) با جستجو و خواندن بررسی شود تا از پیاده‌سازی مجدد قابلیت‌های موجود جلوگیری شود. اگر همه چیز از قبل به درستی پیاده‌سازی شده، فقط یک کامیت no-op با توضیح ثبت شود. این بخش شامل هیچ دستور مستقیم برای تغییر کد نیست.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مستقیمی نیست. وظیفه آن الزام مدل به بررسی خودکار ساختار repo، فایل‌ها و وابستگی‌ها پیش از هر تغییری است. اگر قابلیت‌های درخواستی از قبل وجود داشته باشند، نباید دوباره ساخته شوند. این بخش به‌تنهایی یک مرحله اجرایی نیست، بلکه یک شرط پیش‌نیاز برای تمام مراحل بعدی است.
— [merged] این بخش یک یادداشت مهم برای مدل اجراکننده است که قبل از هر تغییری باید اجرا شود. شامل دستورالعمل‌هایی برای بررسی وجود پیاده‌سازی قبلی، جستجوی فایل‌های مرتبط، و تصمیم‌گیری بر اساس قضاوت شخصی است. این بخش خود یک مرحله اجرایی ن
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 2: افزودن لایه validation و output parser به ai_manager برای بررسی پاسخ‌های AI
**Status:** `pending` (0%)
**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک لایه validation و output parser در فایل backend/app/ai_manager.py است. برای هر مدل AI (OpenAI, Claude) یک validator مخصوص (Pydantic model) تعریف می‌شود که ساختار و محتوای پاسخ را بررسی کند. همچنین تکنیک‌های grounding و fact-checking برای کاهش توهم (hallucination) اضافه می‌شود. این مرحله شامل تغییر در فایل‌های tests/test_ai_llm_pipeline.py و backend/app/ai_manager.py نیز می‌شود. خارج از scope این مرحله: تغییر در سایر فایل‌های لیست شده (مانند oversight_service یا routes) نیست.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در مستندات ai_manager اشاره‌ای به validation خروجی مدل‌های AI نشده است. با توجه به اینکه این سرویس مدیریت مرکزی سرویس‌های AI را بر عهده دارد و با مدل‌های مختلف (OpenAI, Claude) کار می‌کند، عدم وجود validation می‌تواند منجر به پردازش پاسخ‌های ناقص، نادرست یا دارای توهم (hallucination) شود. همچنین مشخص نیست که آیا output parser خاصی برای تطبیق خروجی مدل با فرمت مورد انتظار downstream services وجود دارد یا خیر.

💥 پیامد (impact)
پاسخ‌های نادرست یا ناقص به کاربر نهایی ارسال می‌شود. خطاهای زنجیره‌ای در pipeline به دلیل عدم تطابق فرمت خروجی. افزایش ریسک توهم (hallucination) در پاسخ‌های AI.

🛠 پیشنهاد رفع اولیه
یک لایه validation و output parser به ai_manager اضافه کنید. برای هر مدل، یک validator مخصوص (مثلاً Pydantic model) تعریف کنید که ساختار و محتوای پاسخ را بررسی کند. از تکنیک‌های grounding و fact-checking برای کاهش توهم استفاده کنید.
```

### Step 3: تعریف معیارهای پذیرش رفتار-محور برای رفع ناسازگاری در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این بخش شامل ۷ معیار پذیرش (AC) است که رفتار نهایی پس از رفع ناسازگاری را تعریف می‌کند. هر AC یک رفتار قابل مشاهده را مشخص می‌کند (نه پیاده‌سازی). همچنین یک گام اجرایی پیشنهادی (خواندن دو طرف ناسازگاری و لیست کردن فرض‌ها) ارائه شده است. خارج از scope: پیاده‌سازی فنی، نام فایل‌ها یا کلاس‌ها (به جز OversightService که ذکر شده).
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کند، نه پیاده‌سازی داخلی. معیارها از شناسایی ناسازگاری و مستندسازی فرض‌ها تا عبور موفق integration test برای pipeline ai_llm، عبور تست‌ها، linter و type-check را پوشش می‌دهد. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، طراحی کلاس‌ها یا فایل‌های خاص.
— [merged] این بخش معیارهای پذیرش (AC) را برای یک مرحله از پروژه تعریف می‌کند که در آن ناسازگاری بین دو طرف (احتمالاً دو پیاده‌سازی یا دو دیدگاه) شناسایی و رفع می‌شود. شامل مستندسازی فرض‌ها، تعیین ground truth، اجرای integration test برای pipeline auth، و اطمینان از عبور تست‌ها، linter و type-check است. خارج از scope: پیاده‌سازی خود ناسازگاری، طراحی معماری، یا تغییر در business logic فراتر از pipeline auth.
— [merged] این بخش شامل تعریف ۷ معیار پذیرش (AC) برای فرآیند رفع ناسازگاری بین دو طرف است. هر AC رفتار قابل مشاهده را مشخص می‌کند و نه پیاده‌سازی. همچنین شامل یک گام اجرایی پیشنهادی برای شروع کار است. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، کدنویسی، یا تعیین جزئیات فنی.
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کنند، نه پیاده‌سازی داخلی. ACها بر شناسایی ناسازگاری، مستندسازی فرض‌ها، تعیین ground truth، عبور integration test برای pipeline ai_llm، توضیح PR description، عبور تست‌ها، linter و type-check تمرکز دارند. گام اول از مراحل اجرایی (خواندن دو طرف ناسازگاری و لیست کردن فرض‌ها) نیز در این بخش ذکر شده است. خارج از scope: پیاده‌سازی واقعی رفع ناسازگاری، جزئیات فنی فراتر از ACها.
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کنند، نه پیاده‌سازی داخلی. همچنین شامل یک گام اجرایی پیشنهادی (گام ۱) است که صرفاً خواندن و لیست کردن فرض‌های دو طرف ناسازگاری را توصیه می‌کند. خارج از scope: اجرای کامل رفع ناسازگاری، نوشتن کد، یا تغییر در فایل‌ها.
— [merged] این بخش شامل ۷ معیار پذیرش (AC) است که رفتار قابل مشاهده را تعریف می‌کنند، نه پیاده‌سازی داخلی. هر AC باید توسط تست‌های یکپارچه‌سازی و ابزارهای کیفیت کد (linter, type-checker) تأیید شود. تمرکز بر شناسایی ناسازگاری، مستندسازی فرض‌ها، تعیین ground truth، و عبور موفق pipeline `ai_llm` از integration test است. خارج از scope: پیاده‌سازی داخلی کلاس‌ها، نام فایل‌های خاص، یا جزئیات الگوریتمی.
—
**Excerpt:**
```
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
```

### Step 4: بررسی و مستندسازی ریسک‌های تغییر در callerهای ai_manager و oversight_strong_prompt
**Status:** `pending` (0%)
**Scope:** این مرحله شامل شناسایی و مستندسازی تمام callerهای upstream و downstream برای هر دو طرف (ai_manager و oversight_strong_prompt) است. هدف جلوگیری از break شدن مصرف‌کنندگان downstream در اثر تغییر یک طرف است. این مرحله صرفاً به تحلیل وابستگی‌ها و مستندسازی فرضیات می‌پردازد و شامل پیاده‌سازی تغییرات کد نیست.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
```

### Step 5: رفع ناسازگاری ورودی ai_manager با خروجی oversight_strong_prompt در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این بخش به تحلیل و رفع ناسازگاری منطقی بین دو مؤلفه در pipeline `ai_llm` می‌پردازد: `ai_manager` که انتظار یک پرامپت کاربر خام (string) را دارد، و `oversight_strong_prompt` که یک پرامپت اجرایی کامل و ساختاریافته تولید می‌کند. راه‌حل پیشنهادی شامل شفاف‌سازی مسیر جریان داده است: یا `ai_manager` باید پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد، یا یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده ایجاد شود. فایل‌های مرتبط شامل `backend/app/ai_manager.py` و `backend/app/oversight_strong_prompt.py` هستند. کلاس `OversightService` نیز در این زمینه ذکر شده است.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

ai_manager انتظار 'پرامپت کاربر (string)' را به عنوان ورودی دارد، در حالی که oversight_strong_prompt یک پرامپت اجرایی کامل و ساختاریافته (با قالب ثابت) تولید می‌کند. این دو با هم ناسازگار هستند: ai_manager برای پردازش یک پرامپت خام کاربر طراحی شده، اما خروجی builder یک پرامپت نهایی و آماده اجراست که احتمالاً باید مستقیماً به مدل ارسال شود، نه اینکه دوباره از ai_manager عبور کند.

اگر خروجی oversight_strong_prompt به ai_manager داده شود، ai_manager ممکن است آن را به عنوان یک پرامپت ساده تفسیر کرده و دوباره پردازش کند (مثلاً انتخاب مدل یا fallback) که منجر به نادیده گرفتن ساختار دقیق پرامپت، افزایش هزینه، تأخیر و احتمالاً خرابی خروجی نهایی می‌شود.

مسیر جریان داده را شفاف کنید. یا ai_manager باید بتواند پرامپت‌های ساختاریافته را تشخیص دهد و بدون تغییر عبور دهد، یا یک مسیر جداگانه (bypass) برای پرامپت‌های از پیش ساخته شده (مانند خروجی oversight_strong_prompt) ایجاد کنید که مستقیماً به سرویس مدل ارسال شوند.
```

### Step 6: نوشتن تست‌های واحد برای OversightService (CRUD، scheduler، auto_register و edge cases)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل پیاده‌سازی تست‌های واحد برای کلاس OversightService در فایل tests/test_oversight_service.py است. چهار acceptance_criteria مشخص شده باید پوشش داده شوند: (1) تست CRUD برای watched projects، (2) تست scheduler loop با mock کردن sleep، (3) تست auto_register_watched با mock GitHub API، (4) تست edge cases شامل duplicate repo، invalid URL و empty fields. این مرحله صرفاً به نوشتن تست‌ها محدود است و شامل تغییر در خود سرویس یا منطق business نمی‌شود.
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - تست CRUD برای watched projects (add, update, delete, list) [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_crud_watched_projects", "timeout_seconds": 60}]
  - تست scheduler loop با mock کردن sleep [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_scheduler_loop_mock_sleep", "timeout_seconds": 60}]
  - تست auto_register_watched با mock GitHub API [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_auto_register_watched_mock_github", "timeout_seconds": 60}]
  - تست edge cases: duplicate repo, invalid URL, empty fields [verify_method=backend_test] [verify_plan={"test_node": "tests/test_oversight_service.py::test_edge_cases", "timeout_seconds": 60}]
```

### Step 7: افزودن تست واحد برای کلاس OversightService در oversight_service.py
**Status:** `pending` (0%)
**Scope:** این بخش شامل ایجاد تست‌های واحد برای کلاس OversightService در فایل backend/app/services/oversight_service.py است. تست‌ها باید منطق اصلی مانند مدیریت watched projects، قفل asyncio، و تعامل با وابستگی‌های اصلی (مانند database و models) را پوشش دهند. این بخش شامل تست API routes، scheduler، یا سایر سرویس‌های وابسته نمی‌شود. نکته حیاتی: ۲۰ فایل به این سرویس وابسته هستند، بنابراین تست‌ها باید با mocking وابستگی‌های خارجی (مانند GitHub API و database) نوشته شوند تا ایزوله باشند.
**Excerpt:**
```
OversightService فاقد تست واحد است — ۲۰ فایل به آن وابسته‌اند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-100` — `OversightService` — کلاس اصلی که باید تست شود
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self._lock = asyncio.Lock()
  ```

## 🌐 نقشهٔ وابستگی‌ها
۲۰ فایل به این سرویس وابسته‌اند: ۵ route, ۱۰ service, ۳ core, main.py, ۱ script

## 🔍 Context و وضعیت فعلی
سرویس `oversight_service.py` هستهٔ مرکزی نظارت پروژه‌های GitHub است و ۲۰ فایل مختلف (routes, services, main.py) به آن import دارند. این سرویس شامل منطق پیچیدهٔ مدیریت watched projects, scheduling, runtime verification, و auto-register است. عدم وجود تست می‌تواند منجر به شکست‌های زنجیره‌ای در کل سیستم شود.
```

### Step 8: ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد تست‌های واحد برای کلاس OversightService است. تست‌ها باید رفتارهای CRUD (افزودن، به‌روزرسانی، حذف، لیست) برای watched projects، حلقه scheduler با mock کردن sleep، و auto_register_watched با mock GitHub API را پوشش دهند. همچنین edge cases مانند duplicate repo, invalid URL, empty fields باید تست شوند. فایل تست باید در tests/test_oversight_service.py ایجاد شود. این مرحله شامل پیاده‌سازی خود سرویس نیست، فقط تست‌ها.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست CRUD برای watched projects (add, update, delete, list)
- [ ] تست scheduler loop با mock کردن sleep
- [ ] تست auto_register_watched با mock GitHub API
- [ ] تست edge cases: duplicate repo, invalid URL, empty fields
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد تست‌های واحد برای OversightService با تمرکز بر CRUD watched projects, scheduler loop, و auto-register
```

### Step 9: افزودن تست واحد برای متد add_watched در OversightService
**Status:** `pending` (0%)
**Scope:** این بخش شامل ایجاد یک تست واحد جدید برای متد add_watched از کلاس OversightService است. تست باید در فایل tests/test_oversight_service.py اضافه شود. فقط این تست خاص مد نظر است و هیچ تغییر دیگری در کد یا تست‌های دیگر انجام نمی‌شود.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```
```

### Step 10: [منطق] عدم وجود permission check در auth pipeline
**Status:** `pending` (0%)
**Scope:** این بخش یک تسک از یک سوپر-تسک بزرگتر است که به بررسی و رفع مشکل عدم وجود permission check در auth pipeline می‌پردازد. scope این بخش شامل شناسایی ناسازگاری‌ها، مستندسازی فرض‌ها، تعیین ground truth، align کردن طرف‌های ناسازگار، نوشتن integration test برای auth pipeline، و توضیح تصمیمات در PR description است. این بخش صراحتاً یک مرحله اجرایی است و skip نمی‌شود.
**Excerpt:**
```
تسک 4 از 16
  id: c159181f-ebc5-427e-8ead-118d56dacae5
  عنوان اصلی: [منطق] عدم وجود permission check در auth pipeline
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["ناسازگاری", "permission", "authorization", "auth pipeline"], "files_hint": ["docs/", "README.md", "*.md"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "permission check", "authorization"], "files_hint": ["docs/", "*.md"]}]
  - integration test برای pipeline `auth` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_auth_pipeline.py", "timeout_seconds": 60}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "چرا این تصمیم گرفته شد", "reason", "rationale"], "files_hint": ["docs/", "*.md"]}]
```

### Step 11: افزودن لایه بررسی مجوز (permission check) به pipeline احراز هویت برای مسیرهای mutation
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن یک middleware یا dependency برای بررسی مجوز (permission/authorization) قبل از هر mutation در pipeline auth است. تمرکز بر مسیرهای ذخیره سشن‌ها و پیام‌ها در inspector_session می‌باشد. خارج از scope این مرحله: تغییرات در احراز هویت (authentication) پایه، تغییرات در frontend (Next.js)، یا تغییرات در سایر pipeline‌ها.
**Excerpt:**
```
در pipeline `auth` یک ناسازگاری منطقی پیدا شد: در مستندات ارائه شده، هیچ اشاره‌ای به مکانیزم permission یا authorization در pipeline احراز هویت نشده است. تمام مسیرهای mutation (مانند ذخیره سشن‌ها و پیام‌ها در inspector_session) بدون عبور از یک لایه permission check قابل دسترسی هستند. هر کاربر احراز هویت شده (یا حتی کاربران غیرمجاز در صورت عدم احراز هویت) می‌توانند داده‌های حساس مانند سشن‌های بازرس را تغییر دهند یا ایجاد کنند. یک middleware یا dependency برای بررسی permission قبل از هر mutation اضافه کنید. اطمینان حاصل کنید که کاربر فقط مجوز تغییر سشن‌های متعلق به خود یا سشن‌هایی که مجوز لازم را دارد، داشته باشد.
```

### Step 12: بررسی و رفع coherence issues در pipeline auth
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی و رفع coherence issues (مانند feature flag rot یا refactor ناتمام) در pipeline auth است. این بخش از درخواست اصلی به عنوان یک مرحله اجرایی در نظر گرفته شده و باید به صورت کامل انجام شود. تمام caller های هر دو طرف (قبل و بعد از تغییر) باید بررسی شوند تا از عدم break شدن downstream consumers اطمینان حاصل شود.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: critical
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - بررسی و رفع coherence issues (feature flag rot یا refactor ناتمام) در pipeline auth — بررسی و رفع coherence issues در pipeline auth
```

### Step 13: بررسی اولیه و اعتبارسنجی خودکار درخواست پیش از اجرا
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. هدف آن جلوگیری از پیاده‌سازی مجدد، تشخیص اشتباه، و اطمینان از بررسی مستقل repo است. هیچ فایل، کلاس، یا تابعی برای تغییر مشخص نشده است.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 14: رفع ناسازگاری منطقی بین task_type و قابلیت‌های مدل در انتخاب هوشمند
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک mapping صریح بین task_type و مجموعه ModelCapabilityهای مورد نیاز در pipeline ai_llm است. منطق انتخاب هوشمند باید اصلاح شود تا ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/ai_manager.py هستند. این مرحله شامل تغییر در منطق انتخاب مدل است و نه تغییر در API یا رابط کاربری.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در مستندات ai_manager، ورودی‌ها شامل 'task_type' و 'قابلیت‌های مورد نیاز (ModelCapability)' هستند، اما مشخص نیست که چگونه این دو با هم تطبیق داده می‌شوند. ممکن است یک task_type خاص به قابلیت‌های متفاوتی نیاز داشته باشد و انتخاب مدل صرفاً بر اساس task_type بدون در نظر گرفتن قابلیت‌های دقیق، نادرست باشد. همچنین ارتباط بین task_type و مدل‌های ترجیحی (preferred models) مشخص نیست.

یک mapping صریح بین task_type و مجموعه‌ای از ModelCapabilityهای مورد نیاز ایجاد کنید. منطق انتخاب هوشمند را طوری طراحی کنید که ابتدا task_type را به قابلیت‌های مورد نیاز ترجمه کند، سپس مدل‌هایی را که آن قابلیت‌ها را دارند فیلتر کند و در نهایت بر اساس اولویت‌ها و load balancing انتخاب نهایی را انجام دهد.
```

### Step 15: بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager (به‌ویژه backend/app/ai_manager.py) است. هدف شناسایی و مستندسازی ناسازگاری‌ها، فرض‌ها و نقاط ضعف در منطق fallback فعلی می‌باشد. این مرحله شامل پیاده‌سازی یا اصلاح کد نمی‌شود و صرفاً به تحلیل و مستندسازی می‌پردازد.
**Excerpt:**
```
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
  - بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager — بررسی و مستندسازی وضعیت فعلی pipeline ai_llm و فایل‌های مرتبط با ai_manager
```

### Step 16: پیاده‌سازی استراتژی fallback در ai_manager برای مدیریت خرابی سرویس‌های AI
**Status:** `pending` (0%)
**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک مکانیزم fallback شفاف در فایل backend/app/ai_manager.py است. استراتژی fallback باید شامل ترتیب fallback (OpenAI -> Claude)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout) باشد. این مرحله شامل تغییر در منطق اصلی ai_manager برای مدیریت هوشمند fallback است و بر pipeline ai_llm تأثیر می‌گذارد. تست‌های مربوطه در tests/test_ai_llm_pipeline.py باید به‌روزرسانی شوند.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد: مستندات به 'مدیریت fallback' اشاره دارد، اما جزئیات آن مشخص نیست. با توجه به اینکه ai_manager با چندین سرویس (OpenAI, Claude) کار می‌کند، یک استراتژی fallback شفاف (مثلاً ترتیب fallback، timeout، تعداد تلاش مجدد) ضروری است. همچنین مشخص نیست که آیا fallback بر اساس خطاهای سرویس (مثلاً rate limit) یا کیفیت پاسخ (validation failure) انجام می‌شود. یک استراتژی fallback واضح در ai_manager پیاده‌سازی کنید: ترتیب fallback (مثلاً OpenAI -> Claude -> ...)، حداکثر زمان انتظار (timeout) برای هر سرویس، تعداد تلاش مجدد (retry) با backoff، و شرط‌های fallback (خطای سرویس، خطای validation، timeout).
```

### Step 17: بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل کد موجود در فایل‌های backend/app/ai_manager.py و tests/test_ai_llm_pipeline.py برای مستندسازی وضعیت فعلی است. هدف شناسایی نقاط ضعف، وابستگی‌ها و رفتارهای فعلی قبل از اعمال تغییرات است. خروجی این مرحله یک سند یا کامنت‌های کد است که وضعیت فعلی را شرح می‌دهد.
**Excerpt:**
```
بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm — بررسی و مستندسازی وضعیت فعلی ai_manager و pipeline ai_llm
```

### Step 18: جایگزینی داده‌های سخت‌کد شده صفحه پروفایل مدل‌ها با داده‌های واقعی از بک‌اند
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنویسی کامپوننت `model-profiles/page.tsx` برای دریافت داده‌های پروفایل مدل‌ها از API بک‌اند (احتمالاً از طریق FastAPI) به جای استفاده از داده‌های پیش‌فرض سخت‌کد شده (خطوط 90-97) است. خارج از scope: تغییر ساختار دیتابیس، ایجاد endpoint جدید (فرض بر وجود endpoint مناسب است)، و تغییر سایر صفحات.
**Excerpt:**
```
Model profiles page uses hardcoded default data instead of real backend data

The `model-profiles/page.tsx` defines extensive hardcoded default profiles (lines 90-97)
```

### Step 19: تعریف معیارهای پذیرش رفتار-محور و مراحل اجرایی برای اعمال تغییرات
**Status:** `pending` (0%)
**Scope:** این بخش شامل معیارهای پذیرش عمومی (AC) است که باید برای هر تغییر کد رعایت شود، شامل عبور تست‌ها، linter و type-check. همچنین مراحل اجرایی پیشنهادی را مشخص می‌کند که مجری باید بر اساس context تعیین کند. خروجی مورد انتظار تغییر کد در فایل‌های مرتبط و commit/PR با عبور تمام ACها است. این بخش دستورالعمل اجرایی مستقیم ندارد و بیشتر چارچوب ارزیابی را تعریف می‌کند.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 20: اضافه کردن validation و guardrails به خروجی oversight_strong_prompt
**Status:** `pending` (0%)
**Scope:** این بخش شامل پیاده‌سازی validation و guardrails برای خروجی oversight_strong_prompt است تا از بروز توهم (hallucination) جلوگیری شود. همچنین شامل شناسایی ناسازگاری‌ها، تعیین ground truth، و نوشتن integration test برای pipeline ai_llm می‌شود. فایل‌های اصلی backend/app/oversight_strong_prompt.py و backend/app/ai_llm/pipeline.py هستند. خارج از scope: تغییرات در سایر سرویس‌ها یا APIها.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 16
  id: aa8c1673-2357-40d4-9088-2e28a2c5eb7b
  عنوان اصلی: [منطق] عدم وجود validation و guardrails در خروجی oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/oversight_strong_prompt.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "oversight_strong_prompt"], "files_hint": ["backend/app/ai_llm/pipeline.py", "backend/app/oversight_strong_prompt.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "validation", "guardrail", "hallucination"], "files_hint": ["PR_description.md"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
```

### Step 21: افزودن لایه اعتبارسنجی و گاردریل به خروجی oversight_strong_prompt
**Status:** `pending` (0%)
**Scope:** این بخش شامل افزودن validation به تابع یا کلاس تولیدکننده پرامپت در فایل oversight_strong_prompt.py است. موارد تحت پوشش: (1) بررسی وجود فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'. خارج از scope: تغییر در pipeline کلی، اصلاح مدل‌های خارجی، یا تغییر در سایر فایل‌های پروژه.
**Excerpt:**
```
یک لایه validation به oversight_strong_prompt اضافه کنید: (1) بررسی وجود تمام فیلدهای اجباری (title, user_goal, description)، (2) اعتبارسنجی قالب target_locations (اگر List[Dict] است، کلیدهای مورد انتظار را بررسی کند)، (3) محدودیت طول پرامپت، (4) فیلتر کردن دستورات خطرناک (مثلاً 'ignore previous instructions').
```

### Step 22: بررسی و مستندسازی ناسازگاری‌های دو طرف oversight_strong_prompt و ai_llm با مکانیزم fallback
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل و مستندسازی ناسازگاری‌های موجود بین دو مؤلفه oversight_strong_prompt و ai_llm است. تمرکز بر شناسایی فرض‌های هر طرف، تعیین ground truth و align کردن طرف دیگر است. همچنین شامل نوشتن integration test برای pipeline ai_llm و مستندسازی تصمیمات در PR description می‌شود. فایل‌های اصلی دخیل backend/app/oversight_strong_prompt.py و backend/app/ai_llm.py هستند.
**Excerpt:**
```
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
  - بررسی وضعیت موجود فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm — بررسی و شناسایی فایل‌های مرتبط با oversight_strong_prompt و pipeline ai_llm
  - اضافه کردن اعتبارسنجی فیلدهای اجباری (title, user_goal, description) در oversight_strong_prompt — اضافه کردن اعتبارسنجی فیلدهای اجباری title, user_goal, description
  - اعتبارسنجی قالب target_locations (بررسی کلیدهای مورد انتظار در List[Dict]) — اعتبارسنجی قالب target_locations (کلیدهای مورد انتظار در List[Dict])
  - اضافه کردن محدودیت طول پرامپت (max length check) — اضافه کردن محدودیت طول پرامپت (max length check)
  - فیلتر کردن دستورات خطرناک (مانند 'ignore previous instructions') در پرامپت — فیلتر کردن دستورات خطرناک مانند 'ignore previous instructions'
  - نوشتن تست‌های واحد برای هر چهار لایه validation — نوشتن تست‌های واحد برای هر چهار لایه validation
  - ثبت کامیت‌ها و نوشتن PR description با checklist — ثبت کامیت‌ها و نوشتن PR description با checklist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 9 از 16
  id: 00c2f0ef-15a2-400a-a082-6123f8af075f
  عنوان اصلی: [منطق] عدم وجود مکانیزم fallback مشخص در oversight_strong_prompt
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["oversight_strong_prompt", "fallback", "error handling", "retry"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground truth", "align", "fallback", "oversight_strong_prompt"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_llm.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=static] [verify_plan={"grep_patterns": ["PR description", "decision", "why"], "files_hint": [".github/pull_request_template.md"]}]
```

### Step 23: افزودن مکانیزم fallback و error handling به oversight_strong_prompt
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن لایه error handling به فایل backend/app/oversight_strong_prompt.py است. شامل: (1) پیاده‌سازی retry با backoff برای زمان‌هایی که مدل خارجی پاسخ نمی‌دهد، (2) fallback به یک مدل جایگزین (احتمالاً از طریق ai_manager)، (3) ثبت خطا و بازگشت پاسخ پیش‌فرض (graceful degradation). این مرحله شامل تغییر در pipeline ai_llm و فایل‌های مرتبط مانند backend/app/ai_manager.py و backend/app/services/oversight_service.py می‌شود. خارج از scope: تغییر در سایر pipeline‌ها یا فایل‌های غیرمرتبط با ai_llm.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در حالی که ai_manager دارای قابلیت fallback و load balancing است، oversight_strong_prompt هیچ مکانیزم fallback یا error handling برای زمانی که مدل خارجی (Cursor, ChatGPT) پاسخ نمی‌دهد یا خطا می‌دهد، ندارد.

## 💥 پیامد (impact)
اگر مدل خارجی در دسترس نباشد یا timeout رخ دهد، کل pipeline بدون هیچ تلاشی برای بازیابی (retry, fallback به مدل دیگر) از کار می‌افتد. این باعث تجربه کاربری ضعیف و از دست رفتن درخواست‌ها می‌شود.

## 🛠 پیشنهاد رفع اولیه
یک لایه error handling به oversight_strong_prompt اضافه کنید: (1) retry با backoff، (2) fallback به یک مدل جایگزین (مثلاً از طریق ai_manager)، (3) ثبت خطا و بازگشت یک پاسخ پیش‌فرض (graceful degradation).
```

### Step 24: بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل کامل کد موجود در فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_manager.py است. هدف، مستندسازی رفتار فعلی، نقاط ضعف، وابستگی‌ها و نحوه تعامل این دو سرویس با یکدیگر است. خروجی این مرحله یک سند یا کامنت‌های کد خواهد بود که وضعیت موجود را به‌طور شفاف توصیف می‌کند. این مرحله شامل هیچ تغییری در منطق یا اضافه کردن قابلیت جدید نیست.
**Excerpt:**
```
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
  - بررسی و مستندسازی وضعیت فعلی oversight_strong_prompt و ai_manager — بررسی و مستندسازی کامل وضعیت فعلی دو سرویس
```

### Step 25: تعریف معیارهای عملکردی برای انتخاب هوشمند مدل
**Status:** `pending` (0%)
**Scope:** این بخش به فقدان معیارهای عملکردی (Effectiveness metrics) برای انتخاب هوشمند مدل در سیستم AI Manager اشاره دارد. شامل تعریف معیارهایی مانند دقت، سرعت، هزینه و مصرف منابع برای مقایسه مدل‌های مختلف است. خارج از این بخش: پیاده‌سازی مکانیزم انتخاب، ذخیره‌سازی نتایج، یا رابط کاربری. نکته حیاتی: معیارها باید قابل اندازه‌گیری و مقایسه بین مدل‌های مختلف باشند.
**Excerpt:**
```
[Effectiveness] فقدان معیارهای عملکردی برای انتخاب هوشمند مدل
```

### Step 26: افزودن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن logging برای latency و cost به فایل backend/app/ai_manager.py و پیاده‌سازی مکانیزم weighted selection بر اساس performance history است. هدف این است که انتخاب مدل دیگر صرفاً بر اساس availability نباشد، بلکه بر اساس معیارهای عملکردی (latency و cost) وزن‌دهی شود. این مرحله شامل تغییر در منطق انتخاب مدل در ai_manager و اضافه کردن logging مناسب برای ثبت latency و cost هر فراخوانی است. خارج از scope این مرحله: تغییر در سایر فایل‌ها، پیاده‌سازی metric‌های دیگر، یا تغییر در نحوه ذخیره‌سازی performance history.
**Excerpt:**
```
## 📊 وضعیت فعلی
هیچ metricی برای latency یا cost در outcome data وجود ندارد - انتخاب مدل صرفاً بر اساس availability است

## 🛠 اقدام پیشنهادی
اضافه کردن logging latency و cost به ai_manager و پیاده‌سازی weighted selection بر اساس performance history

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
```

### Step 27: تعریف معیارهای پذیرش رفتار-محور برای outcome target
**Status:** `pending` (0%)
**Scope:** این بخش شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از پیاده‌سازی صحیح outcome target است. هر AC رفتار قابل مشاهده را تعریف می‌کند و نه پیاده‌سازی داخلی. scope شامل: بازنویسی outcome target به صورت measurable، تغییر کد، تست E2E، metric/log، عبور تست‌ها، linter و type-check. خارج از scope: تعریف خود outcome target (فقط نحوه اندازه‌گیری آن). نکته حیاتی: verify باید پیاده‌سازی‌های متفاوت ولی هم‌ارز را قبول کند.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
```

### Step 28: بررسی و اصلاح عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts
**Status:** `pending` (0%)
**Scope:** این بخش شامل شناسایی ناسازگاری‌های بین فرمت system_prompts و مدل‌های مختلف (OpenAI vs Claude)، تعیین ground truth و align کردن طرف دیگر، نوشتن integration test برای pipeline ai_llm، و مستندسازی تصمیم در PR description است. فایل‌های دخیل: backend/app/system_prompts/ و backend/app/ai_llm/. خارج از scope: تغییرات در logging، performance history، weighted selection، outcome metrics، یا تست‌های E2E.
**Excerpt:**
```
تسک 11 از 16
  id: 6c68405b-9f9d-4d4c-9826-a2dae60d008e
  عنوان اصلی: [منطق] عدم تطابق بین prompt format و مدل‌های مختلف در system_prompts
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["system_prompts.*format", "format_prompt.*model", "OpenAI.*system.*message", "Claude.*format"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["ground_truth", "align", "format_prompt_for_model", "model_specific_prompt"], "files_hint": ["backend/app/system_prompts/", "backend/app/ai_llm/"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
```

### Step 29: رفع ناسازگاری فرمت پرامپت‌های سیستم بین مدل‌های مختلف در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این بخش به تحلیل و رفع ناسازگاری منطقی بین system_prompts و مدل‌های مختلف (OpenAI vs Claude) می‌پردازد. شامل: افزودن لایه adapter در prompt_helper یا ai_manager برای تبدیل پرامپت‌های generic به فرمت مناسب هر مدل. ذخیره‌سازی پرامپت‌ها با metadata مربوط به مدل‌های سازگار. خارج از scope: تغییرات در pipeline‌های دیگر، بازنویسی کامل system_prompts، یا تغییر در منطق اصلی مدل‌ها.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

سرویس system_prompts پرامپت‌های سیستم را مدیریت می‌کند، اما مشخص نیست که آیا این پرامپت‌ها برای مدل‌های مختلف (OpenAI vs Claude) فرمت‌بندی می‌شوند یا خیر. هر مدل ممکن است به ساختار پرامپت متفاوتی نیاز داشته باشد (مثلاً system vs user message در OpenAI، یا format خاص در Claude). اگر پرامپت‌ها به صورت generic ذخیره شوند، ممکن است با مدل خاصی سازگار نباشند.

## 💥 پیامد (impact)
پرامپت‌های سیستم به درستی توسط مدل تفسیر نمی‌شوند. کاهش کیفیت پاسخ‌ها. افزایش خطاهای parsing در سمت مدل.

## 🛠 پیشنهاد رفع اولیه
یک لایه adapter در prompt_helper یا ai_manager اضافه کنید که پرامپت‌های generic را بر اساس مدل هدف به فرمت مناسب تبدیل کند. همچنین می‌توانید پرامپت‌ها را با metadata مربوط به مدل‌های سازگار ذخیره کنید.
```

### Step 30: بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline در کدبیس است. هدف آن مستندسازی وضعیت موجود، شناسایی نقاط ضعف و ناسازگاری‌ها، و تعیین ground truth برای مراحل بعدی است. این مرحله شامل پیاده‌سازی یا تغییر کد نمی‌شود و صرفاً یک audit و مستندسازی است.
**Excerpt:**
```
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
  - بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline — بررسی و شناسایی ساختار فعلی system_prompts و ai_llm pipeline
```

### Step 31: افزودن ماژول Hallucination Guard به ai_manager در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این مرحله شامل طراحی و پیاده‌سازی یک ماژول جدید برای کاهش توهم (hallucination guard) در pipeline `ai_llm` است. ماژول باید به `ai_manager` اضافه شود و شامل سه قابلیت اصلی باشد: 1) grounding پاسخ‌ها به منابع معتبر، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین. فایل‌های مرتبط شامل `backend/app/ai_manager.py` و `backend/app/ai_manager.py` هستند. این مرحله شامل refactoring کد موجود برای رفع ناسازگاری منطقی (coherence issue) است. خارج از scope: تغییر در frontend (Next.js)، اضافه کردن endpoint جدید، یا تغییر در pipeline‌های دیگر.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

در هیچ‌کدام از کامپوننت‌ها به مکانیزم‌های کاهش توهم (hallucination guard) اشاره نشده است. با توجه به اینکه pipeline با مدل‌های زبانی بزرگ کار می‌کند، عدم وجود چنین مکانیزمی (مانند grounding, fact-checking, یا self-consistency) می‌تواند منجر به تولید اطلاعات نادرست شود.

یک ماژول hallucination guard به ai_manager اضافه کنید. این ماژول می‌تواند شامل: 1) grounding پاسخ‌ها به منابع معتبر (در صورت وجود)، 2) validation خودکار با استفاده از مدل دوم برای fact-checking، 3) تشخیص و پرچم‌گذاری پاسخ‌های با قطعیت پایین باشد.
```

### Step 32: بررسی و رفع عدم تطابق نوع داده target_locations بین دو کامپوننت
**Status:** `pending` (0%)
**Scope:** این مرحله شامل شناسایی و مستندسازی ناسازگاری نوع داده فیلد target_locations بین دو کامپوننت (احتمالاً oversight_strong_prompt و ai_manager)، تعیین ground truth و align کردن طرف دیگر، و اطمینان از عبور integration test مربوط به pipeline ai_llm است. همچنین PR description باید توضیح دهد چرا این تصمیم گرفته شده است. خارج از scope این مرحله: پیاده‌سازی مکانیزم‌های HallucinationGuard، Grounding، Fact-Checking و سایر مراحل باقی‌مانده.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: medium
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 13 از 16
  id: 3269802a-8316-4245-a7c6-ccebee7a7573
  عنوان اصلی: [منطق] عدم تطابق نوع داده target_locations بین دو کامپوننت
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[Dict\\]", "List\\[str\\]"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_manager.py"]}]
  - ground truth تعیین شد و طرف دیگر align شد [verify_method=static] [verify_plan={"grep_patterns": ["target_locations", "List\\[str\\]", "List\\[Dict\\]"], "files_hint": ["backend/app/oversight_strong_prompt.py", "backend/app/ai_manager.py"]}]
  - integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_ai_llm_pipeline.py::test_integration", "timeout_seconds": 120}]
  - PR description توضیح می‌دهد چرا این تصمیم گرفته شد [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
```

### Step 33: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد قابلیت‌های موجود
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت مهم برای مدل اجراکننده است و دستورالعمل‌های رفتاری قبل از شروع هر تغییری را مشخص می‌کند. شامل: (1) بررسی وجود پیاده‌سازی قبلی با grep/search، (2) عدم بازسازی موارد موجود، (3) اصلاح/تکمیل موارد ناقص، (4) ثبت کامیت no-op در صورت کامل بودن، (5) مسئولیت مدل برای بررسی مستقل ساختار repo و فایل‌ها، (6) انتخاب بهترین تفسیر در صورت ابهام ACها، (7) انجام کامل کار در چند کامیت متوالی در صورت طولانی بودن. این بخش خود یک مرحله اجرایی نیست بلکه راهنمای اجرای سایر مراحل است.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 34: رفع عدم تطابق نوع داده target_locations در pipeline ai_llm
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل و رفع ناسازگاری نوع داده target_locations بین کامپوننت‌های pipeline ai_llm است. تمرکز بر فایل‌های backend/app/oversight_strong_prompt.py و backend/app/ai_manager.py و backend/app/services/oversight_service.py می‌باشد. خارج از scope این مرحله: تغییرات در pipelineهای دیگر، تست‌های integration، یا refactor کلی.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

oversight_strong_prompt ورودی target_locations را به صورت 'List[Dict] or List[str], optional' تعریف کرده است. اما هیچ مشخص نیست که ai_manager یا سایر مصرف‌کنندگان این خروجی چه فرمتی را انتظار دارند. این ابهام می‌تواند باعث خطاهای parsing در زمان اجرا شود.

## 💥 پیامد (impact)
اگر خروجی oversight_strong_prompt به مدلی ارسال شود که منتظر یک فرمت خاص (مثلاً فقط List[str]) است، مدل ممکن است دچار خطا شود یا خروجی نادرست تولید کند. همچنین در صورت استفاده از target_locations در pipelineهای downstream، عدم تطابق نوع داده باعث crash می‌شود.

## 🛠 پیشنهاد رفع اولیه
نوع داده target_locations را به یک فرمت واحد و مشخص محدود کنید (مثلاً فقط List[Dict] با کلیدهای استاندارد مانند 'path', 'type'). اگر نیاز به پشتیبانی از هر دو فرمت است، یک تابع normalize در ابتدای oversight_strong_prompt اضافه کنید که ورودی را به فرمت استاندارد تبدیل کند.
```

### Step 35: ریسک‌ها و موارد احتیاط: بررسی caller‌های هر دو طرف قبل از merge
**Status:** `pending` (0%)
**Scope:** این بخش به ریسک‌های ناشی از تغییر یک طرف pipeline (احتمالاً oversight_strong_prompt و ai_manager) می‌پردازد و بر لزوم بررسی همه caller‌های هر دو طرف قبل از merge تأکید دارد. این یک مرحله احتیاطی و غیرفنی است که باید قبل از هر تغییر کد انجام شود. هیچ مرحله اجرایی مستقیمی در این بخش تعریف نشده است.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.
```

### Step 36: بررسی اولیه و تحلیل وضعیت موجود repo قبل از اجرا
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن صرفاً آگاه‌سازی مدل از احتمال وجود پیاده‌سازی قبلی، لزوم بررسی مستقل ساختار repo، و مسئولیت‌پذیری در قبال تصمیمات است. هیچ فایل، کلاس، یا تابع جدیدی نباید ساخته شود.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.
```

### Step 37: مستندسازی و رفع ابهام در تعامل بین ai_manager و models_registry
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل و مستندسازی رابط (interface) بین ai_manager و models_registry در pipeline ai_llm است. باید مشخص شود که models_registry یک دیتابیس محلی، API خارجی یا کش است. سپس یک mock یا stub برای تست این تعامل ایجاد می‌شود. فایل‌های مرتبط شامل backend/app/ai_manager.py و backend/app/core/models_registry.py هستند. این مرحله شامل پیاده‌سازی کامل منطق تجاری نیست، بلکه صرفاً مستندسازی و ایجاد mock برای تست است.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

مستندات ai_manager اشاره دارد که با 'backend/app/core/models_registry.py' تعامل دارد، اما مشخص نیست که این تعامل به چه صورت است. آیا models_registry یک دیتابیس محلی است؟ یک API خارجی؟ آیا کش دارد؟ این ابهام می‌تواند منجر به وابستگی‌های پنهان و خطاهای runtime شود.

اگر models_registry در دسترس نباشد یا پاسخ نادرست بدهد، ai_manager ممکن است مدل‌های نامعتبر انتخاب کند یا fallback به درستی کار نکند. همچنین تست و دیباگ این بخش دشوار می‌شود.

رابط (interface) بین ai_manager و models_registry را به صورت صریح مستند کنید: متدهای فراخوانی شده، نوع بازگشتی، و رفتار در صورت خطا. یک mock یا stub برای تست این تعامل ایجاد کنید.
```

### Step 38: بررسی ریسک‌های تغییر در callerهای downstream قبل از merge
**Status:** `pending` (0%)
**Scope:** این بخش یک هشدار ریسک است و نه یک مرحله اجرایی. محتوای آن صرفاً یک نکته احتیاطی درباره بررسی callerهای هر دو طرف قبل از merge است. هیچ اقدام عملیاتی یا کدنویسی در این بخش تعریف نشده است.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر یک طرف ممکن است downstream consumers را break کند. حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن.
```

### Step 39: تحلیل عدم وجود خطا در ۳۰ روز اخیر به عنوان نشانه پوشش ناقص سناریوهای خطا
**Status:** `pending` (0%)
**Scope:** این بخش به تحلیل کیفی لاگ‌های خطا در ۳۰ روز اخیر می‌پردازد و این فرضیه را مطرح می‌کند که عدم وجود خطا به معنی کامل بودن سیستم نیست، بلکه ممکن است نشان‌دهنده پوشش ناقص سناریوهای خطا باشد. این یک مرحله تحلیلی و بازبینی است و شامل پیاده‌سازی کد جدید نمی‌شود. خروجی این بخش باید یک گزارش یا مستندسازی از سناریوهای خطای پوشش‌داده‌نشده باشد.
**Excerpt:**
```
## 🎯 هدف (خلاصه ساختاریافته)
[Effectiveness] عدم وجود خطا در ۳۰ روز اخیر نشان‌دهنده پوشش ناقص سناریوهای خطا است

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
```

### Step 40: افزودن تست‌های سناریوی شکست برای ai_manager و بررسی fallback به مدل جایگزین
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن تست‌های سناریوی شکست (failure scenario tests) برای ماژول ai_manager است. تمرکز بر قطع connection به OpenAI و بررسی فعال شدن fallback به مدل جایگزین می‌باشد. این یک effectiveness issue است، بنابراین تست‌ها باید outcome را اندازه بگیرند (مثلاً اینکه آیا fallback واقعاً فعال می‌شود و پاسخ مناسب برمی‌گرداند)، نه فقط وجود فایل یا خط کد. خارج از scope: تست‌های unit معمولی، تست‌های integration کلی، یا تست‌های مربوط به سایر سرویس‌ها.
**Excerpt:**
```
## 📊 وضعیت فعلی
error_rate_30d: 0.0% - هیچ خطایی ثبت نشده است که می‌تواند به دلیل عدم تست سناریوهای شکست سرویس‌های AI باشد

## 🛠 اقدام پیشنهادی
افزودن تست‌های سناریوی شکست برای ai_manager (مثلاً قطع connection به OpenAI) و بررسی فعال شدن fallback به مدل جایگزین

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
```

### Step 41: تعریف معیارهای پذیرش رفتار-محور و بازنویسی outcome target قابل اندازه‌گیری
**Status:** `pending` (0%)
**Scope:** این بخش شامل تعریف ۷ معیار پذیرش (AC) برای اطمینان از رفتار قابل مشاهده و اندازه‌گیری outcome target است. همچنین شامل یک گام اجرایی برای بازنویسی outcome target به صورت measurable می‌باشد. خارج از scope: پیاده‌سازی کد، نوشتن تست، اضافه کردن metric/log، اجرای linter/type-check.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
```

### Step 42: بازنویسی outcome target به صورت measurable و افزودن به documentation
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنویسی outcome target (هدف پیامد) به شکلی قابل اندازه‌گیری (measurable) و افزودن آن به مستندات پروژه (مانند README.md یا docs/) است. این مرحله صرفاً بر روی متن و مستندات تمرکز دارد و شامل تغییر کد یا پیاده‌سازی نمی‌شود. خروجی این مرحله یک متن measurable است که در فایل‌های مستندات قرار می‌گیرد.
**Excerpt:**
```
- بازنویسی outcome target به صورت measurable و اضافه کردن به documentation — outcome target به صورت measurable بازنویسی و به documentation اضافه نشده

📋 acceptance_criteria کامل:
  - outcome target به‌صورت measurable بازنویسی شد [verify_method=static] [verify_plan={"grep_patterns": ["outcome target", "measurable", "effectiveness"], "files_hint": ["README.md", "docs/"]}]
```

### Step 43: رفع عدم یکپارچگی بین oversight_service و project_journal API
**Status:** `pending` (0%)
**Scope:** این بخش به عدم یکپارچگی بین سرویس oversight_service و API پروژه ژورنال اشاره دارد. هدف آن شناسایی و رفع شکاف‌های ارتباطی بین این دو مؤلفه است. فایل‌های مرتبط شامل backend/app/services/oversight_service.py و کلاس OversightService هستند. هیچ موقعیت دقیق فایل یا endpoint خاصی در متن مشخص نشده است.
**Excerpt:**
```
## 🎯 هدف (خلاصه ساختاریافته)
[Effectiveness] عدم یکپارچگی بین oversight_service و project_journal API

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
```

### Step 44: اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based
**Status:** `pending` (0%)
**Scope:** این بخش شامل افزودن یک webhook در سرویس project_journal است تا پس از تکمیل هر پروژه/ژورنال، یک گزارش خودکار به oversight_service ارسال شود. گزارش باید به صورت JSON ذخیره شود. این بخش شامل تغییر در کد project_journal برای ارسال درخواست HTTP به oversight_service و همچنین تغییر در oversight_service برای دریافت و ذخیره گزارش‌ها است. نکته حیاتی: این یک effectiveness issue است، یعنی کد فعلی syntactically کار می‌کند ولی outcome مطلوب (ارسال خودکار گزارش) حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
**Excerpt:**
```
## 📊 وضعیت فعلی
project_journal API مستقل عمل می‌کند و هیچ اشاره‌ای به oversight_service در outcome data دیده نمی‌شود

## 🛠 اقدام پیشنهادی
اضافه کردن webhook در project_journal برای ارسال خودکار گزارش‌ها به oversight_service و ذخیره JSON-based

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
```

### Step 45: تبدیل معیارهای پذیرش رفتار-محور به یک مرحله اجرایی با outcome target قابل اندازه‌گیری
**Status:** `pending` (0%)
**Scope:** این بخش شامل تعریف معیارهای پذیرش (AC) به صورت رفتار-محور و یک گام اجرایی برای بازنویسی outcome target به صورت قابل اندازه‌گیری است. خارج از scope: پیاده‌سازی کد، نوشتن تست E2E، اضافه کردن metric/log، اجرای linter/type-check. نکته حیاتی: ACها رفتار قابل مشاهده را تعریف می‌کنند نه نام فایل/کلاس، و verify باید پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
```

### Step 46: ریسک‌ها و موارد احتیاط: بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن
**Status:** `pending` (0%)
**Scope:** این بخش یک یادآوری/هشدار (⚠️) است و یک مرحله اجرایی مستقل نیست. هیچ کد یا تغییری در فایل‌ها ایجاد نمی‌کند. هدف آن ثبت یک ریسک معماری (trade-off بین کیفیت خروجی و هزینه/سرعت) است که باید در مراحل بعدی (مانند پیاده‌سازی webhook یا endpoint) به‌عنوان یک معیار ارزیابی در نظر گرفته شود. هیچ اقدامی در این مرحله انجام نمی‌شود.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.
```
