---
task_id: task_68e133fe7a97
title: رفع باگ‌های مدیریت خطا و Silent Failure در GitHub Import
type: other
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:20:35.913368+00:00'
updated_at: '2026-05-29T20:23:26.932409+00:00'
tags:
- consolidated
- post_verify_merge
target_files:
- backend/app/api/routes/github_import.py
- backend/app/services/inspector_agent.py
- backend/app/services/oversight_service.py
- backend/app/services/github_import.py
- backend/tests/test_github_import.py
- backend/app/services/project_auto_setup.py
- backend/requirements.txt
- backend/app/main.py
- backend/tests/test_runtime_verify_stage1.py
- backend/tests/test_runtime_verify_stage2.py
- backend/app/services/verify_runtime/iterative_orchestrator.py
---

# رفع باگ‌های مدیریت خطا و Silent Failure در GitHub Import

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به عدم مدیریت خطا در GitHub Import و silent failure در github_import.py که هر دو به فرآیند import مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به GitHub Import و Silent Failure
💎 estimated_difficulty: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 95e241b7-5809-4df2-9733-613094cf56b3
  عنوان اصلی: Silent failure — except/catch بدون log در مسیر crucial
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - نوع exception specific شده (نه bare except/catch) [verify_method=static] [verify_plan={"grep_patterns": ["except\\s*:", "except\\s+Exception\\s*:", "except\\s+[A-Za-z]+\\s+as\\s+\\w+\\s*:"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - log با level مناسب (warning/error) + context کامل اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["logger\\.(warning|error)\\(", "logging\\.(warning|error)\\(", "log\\.(warning|error)\\("], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - تست unit برای edge case شکست‌خورده عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_github_import.py::test_silent_failure_edge_case", "timeout_seconds": 60}]
  - اگر failure قابل recovery است، fallback مستند شده [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "recover", "retry", "alternative"], "files_hint": ["backend/app/api/routes/github_import.py"]}]

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
Silent failure — except/catch بدون log در مسیر crucial

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:353`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
در `backend/app/api/routes/github_import.py` (line 353) یک exception handler خاموش (مثل `except: pass`) در مسیر اصلی کد پیدا شد.

## 🔍 جزئیات
- علت: bare 'except: pass' — هیچ‌چیز handle یا log نمی‌شود

## 🤔 چرا مهم است
silent failure خطرناک‌ترین bug است — کد به‌نظر کار می‌کند ولی در شرایط لبه data drop می‌شود بدون اینکه کسی متوجه شود. production incidents معمولاً ریشه‌شان همین است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] نوع exception specific شده (نه bare except/catch)
- [ ] log با level مناسب (warning/error) + context کامل اضافه شد
- [ ] تست unit برای edge case شکست‌خورده عبور می‌کند
- [ ] اگر failure قابل recovery است، fallback مستند شده
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: مشخص کن چه exception ای واقعاً ممکن است در این نقطه رخ دهد.
گام ۲: یا (الف) آن exception را به‌صورت specific catch کن و log + decision بنویس، یا (ب) اجازه bdo bubble up.
گام ۳: تست unit برای edge case (شکست عمدی این مسیر) بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر silent failure به raise ممکن است upstream caller را break کند که فرض می‌کرده این تابع همیشه return می‌کند. caller را هم چک کن.

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
تسک 2 از 2
  id: 58f05dc2-4934-4be7-ae07-6175eda2a0ad
  عنوان اصلی: عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore", "type-check"], "files_hint": ["backend/"]}]

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
عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در `backend/app/api/routes/github_import.py`، تابع `import_repository` (خط 132-157) از `auto_setup_project_memory` استفاده می‌کند. اگر این تابع خطا بدهد، کل درخواست import با خطای 500 مواجه می‌شود و پروژه import شده اما بدون setup باقی می‌ماند. در حال حاضر یک try/except وجود دارد که خطا را در `result["auto_setup"]` ذخیره می‌کند، اما این کافی

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
- اولویت: medium
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
- در commit message: `merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad`
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
🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به عدم مدیریت خطا در GitHub Import و silent failure در github_import.py که هر دو به فرآیند import مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به GitHub Import و Silent Failure
💎 estimated_difficulty: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 95e241b7-5809-4df2-9733-613094cf56b3
  عنوان اصلی: Silent failure — except/catch بدون log در مسیر crucial
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - نوع exception specific شده (نه bare except/catch) [verify_method=static] [verify_plan={"grep_patterns": ["except\\s*:", "except\\s+Exception\\s*:", "except\\s+[A-Za-z]+\\s+as\\s+\\w+\\s*:"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - log با level مناسب (warning/error) + context کامل اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["logger\\.(warning|error)\\(", "logging\\.(warning|error)\\(", "log\\.(warning|error)\\("], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - تست unit برای edge case شکست‌خورده عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_github_import.py::test_silent_failure_edge_case", "timeout_seconds": 60}]
  - اگر failure قابل recovery است، fallback مستند شده [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "recover", "retry", "alternative"], "files_hint": ["backend/app/api/routes/github_import.py"]}]

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
Silent failure — except/catch بدون log در مسیر crucial

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:353`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
در `backend/app/api/routes/github_import.py` (line 353) یک exception handler خاموش (مثل `except: pass`) در مسیر اصلی کد پیدا شد.

## 🔍 جزئیات
- علت: bare 'except: pass' — هیچ‌چیز handle یا log نمی‌شود

## 🤔 چرا مهم است
silent failure خطرناک‌ترین bug است — کد به‌نظر کار می‌کند ولی در شرایط لبه data drop می‌شود بدون اینکه کسی متوجه شود. production incidents معمولاً ریشه‌شان همین است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] نوع exception specific شده (نه bare except/catch)
- [ ] log با level مناسب (warning/error) + context کامل اضافه شد
- [ ] تست unit برای edge case شکست‌خورده عبور می‌کند
- [ ] اگر failure قابل recovery است، fallback مستند شده
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: مشخص کن چه exception ای واقعاً ممکن است در این نقطه رخ دهد.
گام ۲: یا (الف) آن exception را به‌صورت specific catch کن و log + decision بنویس، یا (ب) اجازه bdo bubble up.
گام ۳: تست unit برای edge case (شکست عمدی این مسیر) بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر silent failure به raise ممکن است upstream caller را break کند که فرض می‌کرده این تابع همیشه return می‌کند. caller را هم چک کن.

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
تسک 2 از 2
  id: 58f05dc2-4934-4be7-ae07-6175eda2a0ad
  عنوان اصلی: عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore", "type-check"], "files_hint": ["backend/"]}]

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
عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در `backend/app/api/routes/github_import.py`، تابع `import_repository` (خط 132-157) از `auto_setup_project_memory` استفاده می‌کند. اگر این تابع خطا بدهد، کل درخواست import با خطای 500 مواجه می‌شود و پروژه import شده اما بدون setup باقی می‌ماند. در حال حاضر یک try/except وجود دارد که خطا را در `result["auto_setup"]` ذخیره می‌کند، اما این کافی

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
- اولویت: medium
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
- در commit message: `merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند
```

## 📋 چک‌لیست مراحل (12 مرحله)

این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**
وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.

- [ ] **مرحله 1: بررسی و شناسایی exception handler خاموش در github_import.py خط 353** — این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py در خط 353 برای یافتن bare except: pass یا catch بدون log است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: قبل از هر تغییری، باید دقیقاً مشخص شود که چه نوع exception ای در این نقطه ممکن است رخ دهد 
- [ ] **مرحله 2: تبدیل bare except به exception specific با log مناسب در github_import.py** — این مرحله شامل تغییر کد در backend/app/api/routes/github_import.py برای جایگزینی bare except: pass با catch exception خاص (مثلاً ValueError, KeyError, یا Exception) و افزودن log با level warning/error و context کامل است. خارج از این مرحله: نوشتن تست، بررسی fallback، یا تغییر سایر فایل‌ها. نکته حیاتی
- [ ] **مرحله 3: نوشتن تست unit برای edge case شکست‌خورده در github_import.py** — این مرحله شامل نوشتن یک تست unit در tests/test_github_import.py برای edge case ای است که قبلاً باعث silent failure می‌شد. تست باید یک سناریوی خطا را شبیه‌سازی کند و بررسی کند که exception به درستی catch و log شده است. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration، یا تست‌های دیگر. نکته
- [ ] **مرحله 4: بررسی و مستندسازی fallback برای failure قابل recovery در github_import.py** — این مرحله شامل بررسی این است که آیا failure در خط 353 قابل recovery است یا خیر. اگر قابل recovery است، باید یک fallback mechanism (مثل retry, alternative path) مستند یا پیاده‌سازی شود. خارج از این مرحله: تغییر کد اصلی برای exception handling یا log. نکته حیاتی: fallback باید در کد یا کامنت مستند شود
- [ ] **مرحله 5: بررسی caller upstream برای عدم break در github_import.py** — این مرحله شامل بررسی callerهای upstream تابع حاوی خط 353 در backend/app/api/routes/github_import.py است تا اطمینان حاصل شود که تغییر silent failure به raise یا log باعث break نمی‌شود. خارج از این مرحله: تغییر کد در callerها. نکته حیاتی: اگر caller فرض می‌کند تابع همیشه return می‌کند، باید آن را اصلا
- [ ] **مرحله 6: اجرای linter و type-check برای github_import.py** — این مرحله شامل اجرای linter (ruff) و type-check (mypy) روی فایل backend/app/api/routes/github_import.py برای اطمینان از عدم وجود warning یا error است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.
- [ ] **مرحله 7: بررسی و شناسایی عدم مدیریت خطا در auto_setup_project_memory در github_import.py** — این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py، به ویژه تابع import_repository (خطوط 132-157) و نحوه استفاده از auto_setup_project_memory است. هدف شناسایی try/except موجود و بررسی کافی بودن آن است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: ب
- [ ] **مرحله 8: بهبود مدیریت خطا برای auto_setup_project_memory در import_repository** — این مرحله شامل بهبود try/except موجود در تابع import_repository در backend/app/api/routes/github_import.py برای auto_setup_project_memory است. باید خطا را به درستی log کند و fallback مناسب (مثل ادامه بدون setup) فراهم کند. خارج از این مرحله: نوشتن تست، تغییر سایر فایل‌ها. نکته حیاتی: تغییر نباید تست
- [ ] **مرحله 9: نوشتن تست برای edge case auto_setup_project_memory failure** — این مرحله شامل نوشتن یک تست unit در tests/test_github_import.py برای سناریوی failure در auto_setup_project_memory است. تست باید بررسی کند که import_repository با خطا مواجه نمی‌شود و fallback به درستی کار می‌کند. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration. نکته حیاتی: تست باید با pyt
- [ ] **مرحله 10: اجرای linter و type-check برای کل backend پس از تغییرات** — این مرحله شامل اجرای linter (ruff) و type-check (mypy) روی کل پوشه backend برای اطمینان از عدم وجود warning یا error پس از تغییرات است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.
- [ ] **مرحله 11: اجرای تمام تست‌های backend برای اطمینان از عدم رگرشن** — این مرحله شامل اجرای تمام تست‌های backend با pytest برای اطمینان از اینکه تغییرات باعث شکستن تست‌های موجود نمی‌شود. خارج از این مرحله: تغییر کد، اجرای تست‌های frontend. نکته حیاتی: هیچ تستی نباید fail شود.
- [ ] **مرحله 12: ایجاد commit با پیام واضح و merge-ready PR** — این مرحله شامل ایجاد یک commit (یا چند commit متوالی) با پیام واضح که تغییرات را توضیح می‌دهد و شامل merged-from IDs است. همچنین ایجاد یک PR description با checklist از همه commitها. خارج از این مرحله: تغییر کد بیشتر. نکته حیاتی: commit message باید شامل merged-from: 95e241b7-5809-4df2-9733-613094cf

---

# 🔹 مرحله 1: بررسی و شناسایی exception handler خاموش در github_import.py خط 353

**Scope:** این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py در خط 353 برای یافتن bare except: pass یا catch بدون log است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: قبل از هر تغییری، باید دقیقاً مشخص شود که چه نوع exception ای در این نقطه ممکن است رخ دهد و آیا این handler واقعاً خاموش است یا خیر.
**Key terms:** backend/app/api/routes/github_import.py, except: pass, exception handler

**بخش مربوط از متن کاربر:**
```
در `backend/app/api/routes/github_import.py` (line 353) یک exception handler خاموش (مثل `except: pass`) در مسیر اصلی کد پیدا شد.

## 🔍 جزئیات
- علت: bare 'except: pass' — هیچ‌چیز handle یا log نمی‌شود
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی bare except:pass در github_import.py خط 353

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:353` — `exception_handler` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی پروژه، این فایل در backend/app/api/routes/github_import.py قرار دارد.
  ```python
  فایل deep-read نشده — مجری باید خط 353 را مستقیماً بررسی کند
  ```
- `backend/app/services/inspector_agent.py:120-145` — `inspect_code` — الگوی صحیح exception handling با log — برای مقایسه با الگوی خاموش github_import.py
  ```python
  def inspect_code(self, code: str) -> dict:
      try:
          result = self._run_inspection(code)
          return result
      except Exception as e:
          logger.error(f"Inspection failed: {e}")
          return {"error": str(e)}
  ```
- `backend/app/services/oversight_service.py:200-220` — `process_task` — نمونه exception handling با log و re-raise — برای مقایسه با الگوی خاموش
  ```python
  def process_task(self, task_id: str) -> dict:
      try:
          task = self._get_task(task_id)
          result = self._execute(task)
          return result
      except ValueError as ve:
          logger.warning(f"Invalid task: {ve}")
          raise
      except Exception as e:
          logger.critical(f"Unexpected error: {e}", exc_info=True)
          return {"status": "failed", "error": str(e)}
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/github_import.py` (سطر 1) — این فایل سرویس منطق import از گیت‌هاب را پیاده‌سازی می‌کند و github_import.py روتر از آن استفاده می‌کند
- `backend/app/services/inspector_agent.py` (سطر 120) — این سرویس الگوی صحیح exception handling را نشان می‌دهد و می‌تواند به عنوان مرجع برای مقایسه استفاده شود
- `backend/app/services/oversight_service.py` (سطر 200) — این سرویس نیز الگوی exception handling با log و exc_info را نشان می‌دهد
- `backend/app/core/logging_utils.py` (سطر 1) — این فایل ابزارهای logging را تعریف می‌کند که می‌تواند برای جایگزینی bare except استفاده شود

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل backend/app/api/routes/github_import.py (روتر) مربوط است که احتمالاً از سرویس backend/app/services/github_import.py برای عملیات import استفاده می‌کند. فایل‌های logging مانند backend/app/core/logging_utils.py و backend/app/core/config.py برای logging پیکربندی شده‌اند. سایر روترها مانند backend/app/api/routes/external_projects.py و backend/app/api/routes/projects.py ممکن است از github_import.py استفاده کنند. الگوهای exception handling در فایل‌های inspector_agent.py و oversight_service.py به عنوان مرجع برای مقایسه استفاده می‌شوند.

## 🔍 Context و وضعیت فعلی
بررسی و شناسایی exception handler خاموش در github_import.py خط 353. این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py در خط 353 برای یافتن bare except: pass یا catch بدون log است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: قبل از هر تغییری، باید دقیقاً مشخص شود که چه نوع exception ای در این نقطه ممکن است رخ دهد و آیا این handler واقعاً خاموش است یا خیر. بخش مربوط از درخواست اصلی کاربر: در `backend/app/api/routes/github_import.py` (line 353) یک exception handler خاموش (مثل `except: pass`) در مسیر اصلی کد پیدا شد. علت: bare 'except: pass' — هیچ‌چیز handle یا log نمی‌شود. کلیدواژه‌ها: backend/app/api/routes/github_import.py, except: pass, exception handler. با توجه به deep context موجود، فایل github_import.py در deep-read ارائه نشده است، بنابراین تحلیل بر اساس ساختار سطحی پروژه و الگوهای مشابه در سایر فایل‌ها انجام می‌شود. فایل‌های مرتبط مانند inspector_agent.py، oversight_service.py و سایر سرویس‌های inspect از الگوی try/except با log مناسب استفاده می‌کنند. این تسک صرفاً بررسی و مستندسازی است و شامل تغییر کد نمی‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] بررسی شود که در خط 353 فایل backend/app/api/routes/github_import.py یک bare except: pass وجود دارد یا خیر
- [ ] نوع exception‌های محتمل در آن نقطه شناسایی و مستند شوند (حداقل ۳ نوع)
- [ ] تأیید شود که bare except: pass هیچ log یا raise یا fallback ندارد
- [ ] گزارش نهایی شامل فهرست exception‌های محتمل و تأیید خاموش بودن handler باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/github_import.py را باز کرده و خط 353 را بررسی کنید. 2. الگوی کد اطراف خط 353 را بخوانید تا مشخص شود آیا bare except: pass وجود دارد یا خیر. 3. نوع exception‌هایی که ممکن است در آن نقطه رخ دهد را شناسایی کنید (مثلاً ConnectionError, TimeoutError, JSONDecodeError, FileNotFoundError). 4. بررسی کنید که آیا exception handler واقعاً خاموش است (بدون log، بدون raise، بدون fallback). 5. نتیجه بررسی را در قالب یک گزارش مستند کنید. 6. اگر bare except: pass تأیید شد، نوع exception‌های محتمل را فهرست کنید. 7. هیچ تغییری در کد اعمال نکنید — این تسک صرفاً بررسی است.

## 💡 نمونه‌های قبل/بعد
**مقایسه bare except با exception handling صحیح**

_قبل:_
```
try:
    result = some_function()
except:
    pass
```

_بعد:_
```
try:
    result = some_function()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
except TimeoutError as e:
    logger.warning(f"Timeout: {e}")
    return None
except Exception as e:
    logger.critical(f"Unexpected error: {e}", exc_info=True)
    return {"error": str(e)}
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -n 'except:' backend/app/api/routes/github_import.py`
- `grep -n 'pass' backend/app/api/routes/github_import.py`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک صرفاً بررسی است و تغییری در کد ایجاد نمی‌کند، بنابراین ریسک خاصی ندارد. با این حال، اگر در آینده تغییر کد انجام شود، باید توجه داشت که github_import.py توسط روترهای دیگر مانند external_projects.py و projects.py نیز استفاده می‌شود و تغییر exception handling ممکن است روی رفتار آن‌ها تأثیر بگذارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 2: تبدیل bare except به exception specific با log مناسب در github_import.py

**Scope:** این مرحله شامل تغییر کد در backend/app/api/routes/github_import.py برای جایگزینی bare except: pass با catch exception خاص (مثلاً ValueError, KeyError, یا Exception) و افزودن log با level warning/error و context کامل است. خارج از این مرحله: نوشتن تست، بررسی fallback، یا تغییر سایر فایل‌ها. نکته حیاتی: باید از bare except (except:) و except Exception: بدون log اجتناب شود.
**Key terms:** backend/app/api/routes/github_import.py, except, logger.warning, logger.error, logging.warning, logging.error

**بخش مربوط از متن کاربر:**
```
- [ ] نوع exception specific شده (نه bare except/catch) [verify_method=static] [verify_plan={"grep_patterns": ["except\\s*:", "except\\s+Exception\\s*:", "except\\s+[A-Za-z]+\\s+as\\s+\\w+\\s*:"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
- [ ] log با level مناسب (warning/error) + context کامل اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["logger\\.(warning|error)\\", "logging\\.(warning|error)\\", "log\\.(warning|error)\\"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
تبدیل bare except به exception specific با log در github_import.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:نامشخص — فایل deep-read نشده` — `تمام بلوک‌های try/except در فایل` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی پروژه، این فایل شامل endpointهای import از GitHub است.
  ```python
  فایل deep-read نشده — مجری باید محتوای واقعی را بررسی کند
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — بر اساس ساختار پروژه: FastAPI (Python), SQLAlchemy, GitHub API

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/logging_utils.py` (سطر 1) — این فایل حاوی تنظیمات logger است که باید در github_import.py import شود. اگر logger از اینجا گرفته نشود، باید logging.getLogger(__name__) استفاده شود.
- `backend/app/services/github_import.py` (سطر 1) — این سرویس توسط github_import.py (روتر) فراخوانی می‌شود. خطاهای احتمالی در سرویس باید در روتر catch شوند.
- `backend/app/services/github_pr_service.py` (سطر 1) — این سرویس ممکن است توسط github_import.py استفاده شود و خطاهای آن نیز باید مدیریت شوند.

## 🌐 نقشهٔ وابستگی‌ها
فایل backend/app/api/routes/github_import.py یک روتر FastAPI است که endpointهای مربوط به import پروژه‌های GitHub را مدیریت می‌کند. این روتر از سرویس‌های backend/app/services/github_import.py و احتمالاً backend/app/services/github_pr_service.py استفاده می‌کند. برای logging، باید از logger تعریف‌شده در backend/app/core/logging_utils.py استفاده کند یا logging.getLogger(__name__) را در ابتدای فایل تعریف کند. تغییر bare exceptها به exception specific با log، تأثیری بر سایر فایل‌ها ندارد اما کیفیت خطایابی و مانیتورینگ را بهبود می‌بخشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست تبدیل bare except به exception specific با log مناسب در فایل backend/app/api/routes/github_import.py را داده است. این تغییر شامل جایگزینی bare except: pass با catch exception خاص (مثلاً ValueError, KeyError, یا Exception) و افزودن log با level warning/error و context کامل است. خارج از این مرحله: نوشتن تست، بررسی fallback، یا تغییر سایر فایل‌ها. نکته حیاتی: باید از bare except (except:) و except Exception: بدون log اجتناب شود.

بخش مربوط از درخواست اصلی کاربر:
- [ ] نوع exception specific شده (نه bare except/catch) [verify_method=static] [verify_plan={"grep_patterns": ["except\\s*:", "except\\s+Exception\\s*:", "except\\s+[A-Za-z]+\\s+as\\s+\\w+\\s*:"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
- [ ] log با level مناسب (warning/error) + context کامل اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["logger\\.(warning|error)\\", "logging\\.(warning|error)\\", "log\\.(warning|error)\\"], "files_hint": ["backend/app/api/routes/github_import.py"]}]

کلیدواژه‌ها: backend/app/api/routes/github_import.py, except, logger.warning, logger.error, logging.warning, logging.error

فایل github_import.py در backend/app/api/routes/ قرار دارد و مسئول مدیریت عملیات import از GitHub است. این فایل شامل endpointهای API برای import پروژه‌ها، repositoryها و مدیریت خطاهای مرتبط با GitHub می‌باشد. با توجه به اینکه این فایل deep-read نشده، مجری باید محتوای دقیق فایل را بررسی کرده و تمام bare exceptها را شناسایی کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ bare except (except:) در فایل backend/app/api/routes/github_import.py وجود نداشته باشد
- [ ] هیچ except Exception بدون log در فایل backend/app/api/routes/github_import.py وجود نداشته باشد
- [ ] هر بلوک except در فایل backend/app/api/routes/github_import.py دارای logger.warning یا logger.error با context کامل باشد
- [ ] تعداد logger.warning/logger.error در فایل backend/app/api/routes/github_import.py حداقل به تعداد بلوک‌های except باشد
- [ ] logger در ابتدای فایل backend/app/api/routes/github_import.py به درستی import شده باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/github_import.py را باز کرده و تمام بلوک‌های try/except را اسکن کنید.
2. هر bare except (except:) را شناسایی کنید — این الگوها شامل:
   - except: (بدون هیچ نوع exception)
   - except Exception: (بدون log)
   - except: pass (بدون هیچ اقدامی)
3. برای هر مورد، نوع exception خاص را بر اساس عملیات داخل try block تعیین کنید:
   - اگر عملیات JSON است → except json.JSONDecodeError
   - اگر عملیات HTTP/API است → except requests.RequestException
   - اگر عملیات فایل است → except (FileNotFoundError, PermissionError)
   - اگر عملیات دیتابیس است → except sqlalchemy.exc.SQLAlchemyError
   - در غیر این صورت → except Exception as e (با log مناسب)
4. برای هر except، یک logger.warning یا logger.error با context کامل اضافه کنید:
   - logger.error(f"Failed to import GitHub repository {repo_url}: {e}", exc_info=True)
   - logger.warning(f"Invalid JSON in response from GitHub API: {e}")
5. اطمینان حاصل کنید که logger در ابتدای فایل import شده است:
   - from app.core.logging_utils import logger
   - یا import logging / logger = logging.getLogger(__name__)
6. تمام تغییرات را با grep patterns تأیید کنید:
   - grep -n "except\s*:" backend/app/api/routes/github_import.py (نباید نتیجه داشته باشد)
   - grep -n "except\s+Exception\s*:" backend/app/api/routes/github_import.py (فقط با log مجاز است)
   - grep -n "logger\.(warning|error)" backend/app/api/routes/github_import.py (باید حداقل به تعداد exceptها باشد)

## 💡 نمونه‌های قبل/بعد
**تبدیل bare except به exception specific با log**

_قبل:_
```
try:
    response = requests.get(github_api_url)
    data = response.json()
except:
    pass
```

_بعد:_
```
try:
    response = requests.get(github_api_url)
    data = response.json()
except requests.RequestException as e:
    logger.error(f"Failed to fetch from GitHub API {github_api_url}: {e}", exc_info=True)
    raise HTTPException(status_code=502, detail=f"GitHub API error: {str(e)}")
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON response from GitHub API: {e}", exc_info=True)
    raise HTTPException(status_code=502, detail="Invalid response from GitHub")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -n "except\s*:" backend/app/api/routes/github_import.py || echo "No bare except found"`
- `grep -n "except\s+Exception\s*:" backend/app/api/routes/github_import.py || echo "No bare Exception found"`
- `grep -n "logger\.(warning|error)" backend/app/api/routes/github_import.py`
- `python -c "import ast; ast.parse(open('backend/app/api/routes/github_import.py').read()); print('Syntax OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل backend/app/api/routes/github_import.py deep-read نشده، بنابراین تعداد دقیق bare exceptها مشخص نیست. تغییر bare except به exception specific ممکن است باعث break شدن flowهای خاصی شود که قبلاً با bare except مدیریت می‌شدند (مثلاً اگر exception مورد انتظار نباشد). همچنین اگر logger به درستی import نشود، ممکن است خطاهای runtime ایجاد کند. توصیه می‌شود پس از تغییر، endpointهای import GitHub به صورت دستی تست شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 3: نوشتن تست unit برای edge case شکست‌خورده در github_import.py

**Scope:** این مرحله شامل نوشتن یک تست unit در tests/test_github_import.py برای edge case ای است که قبلاً باعث silent failure می‌شد. تست باید یک سناریوی خطا را شبیه‌سازی کند و بررسی کند که exception به درستی catch و log شده است. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration، یا تست‌های دیگر. نکته حیاتی: تست باید با pytest کار کند و edge case شکست‌خورده را پوشش دهد.
**Key terms:** tests/test_github_import.py, test_silent_failure_edge_case, pytest, edge case

**بخش مربوط از متن کاربر:**
```
- [ ] تست unit برای edge case شکست‌خورده عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_github_import.py::test_silent_failure_edge_case", "timeout_seconds": 60}]
```

## 🎯 هدف (خلاصه ساختاریافته)
نوشتن تست unit برای edge case شکست‌خورده در github_import.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/github_import.py:1-50` — `import_repository` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار سطحی، تابع import_repository در این فایل قرار دارد و edge case شکست‌خورده احتمالاً در این تابع رخ می‌دهد.
- `backend/tests/test_github_import.py:1-30` — `test_silent_failure_edge_case` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل باید ایجاد شود و شامل تابع تست test_silent_failure_edge_case باشد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/github_import.py` — فایل اصلی که edge case در آن رخ می‌دهد و تست باید آن را پوشش دهد.
- `backend/tests/test_github_import.py` — فایل تست که باید ایجاد شود و شامل تست unit برای edge case باشد.
- `backend/app/services/__init__.py` — فایل __init__ سرویس‌ها که ممکن است github_import را export کند و تست نیاز به import آن داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل backend/app/services/github_import.py وابسته است که شامل توابع اصلی import است. فایل tests/test_github_import.py باید ایجاد شود و از pytest و احتمالاً pytest-mock یا unittest.mock استفاده کند. همچنین ممکن است نیاز به import از backend/app/services/github_import.py داشته باشد. فایل backend/app/services/__init__.py ممکن است برای export ماژول استفاده شود. edge case شکست‌خورده احتمالاً مربوط به تابع import_repository است که در github_import.py تعریف شده است.

## 🔍 Context و وضعیت فعلی
کاربر درخواست نوشتن یک تست unit برای edge case شکست‌خورده در فایل github_import.py دارد. این edge case قبلاً باعث silent failure می‌شد و باید در tests/test_github_import.py پیاده‌سازی شود. تست باید یک سناریوی خطا را شبیه‌سازی کند و بررسی کند که exception به درستی catch و log شده است. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration، یا تست‌های دیگر. نکته حیاتی: تست باید با pytest کار کند و edge case شکست‌خورده را پوشش دهد. بخش مربوط از درخواست اصلی کاربر: [ ] تست unit برای edge case شکست‌خورده عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_github_import.py::test_silent_failure_edge_case", "timeout_seconds": 60}]. کلیدواژه‌ها: tests/test_github_import.py, test_silent_failure_edge_case, pytest, edge case. با توجه به deep context موجود، فایل github_import.py در backend/app/services/github_import.py قرار دارد و شامل توابعی مانند import_repository، clone_repository، parse_github_url و handle_import_error است. edge case شکست‌خورده احتمالاً مربوط به حالتی است که URL مخزن نامعتبر است یا دسترسی به مخزن وجود ندارد و exception به درستی catch و log نمی‌شود. فایل tests/test_github_import.py در deep context موجود نیست، بنابراین باید ایجاد شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست unit test_silent_failure_edge_case در tests/test_github_import.py وجود داشته باشد و با pytest کار کند.
- [ ] تست یک سناریوی خطا را شبیه‌سازی کند (مثلاً URL نامعتبر) و بررسی کند که exception به درستی catch و log شده است.
- [ ] تست edge case شکست‌خورده را پوشش دهد که قبلاً باعث silent failure می‌شد.
- [ ] تست با pytest کار کند و بدون خطا اجرا شود.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل tests/test_github_import.py با یک تابع تست به نام test_silent_failure_edge_case. 2. در این تست، یک سناریوی خطا شبیه‌سازی شود: فراخوانی تابع import_repository با یک URL نامعتبر (مثلاً 'https://github.com/invalid/repo') که باعث raise Exception می‌شود. 3. با استفاده از pytest.raises یا mock کردن، بررسی شود که exception به درستی catch شده و در log ثبت می‌شود. 4. اطمینان از اینکه تست با pytest کار می‌کند و edge case شکست‌خورده را پوشش می‌دهد. 5. تست باید شامل assert برای بررسی log message یا exception type باشد. 6. از pytest-mock یا unittest.mock برای شبیه‌سازی تابع handle_import_error استفاده شود.

## 💡 نمونه‌های قبل/بعد
**نمونه تست unit برای edge case شکست‌خورده**

_بعد:_
```
import pytest
from unittest.mock import patch
from backend.app.services.github_import import import_repository

def test_silent_failure_edge_case():
    """Test that silent failure edge case is handled correctly."""
    invalid_url = 'https://github.com/invalid/repo'
    with patch('backend.app.services.github_import.handle_import_error') as mock_handle:
        with pytest.raises(Exception):
            import_repository(invalid_url)
        mock_handle.assert_called_once()
        assert 'silent failure' in str(mock_handle.call_args)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_github_import.py::test_silent_failure_edge_case -v`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک فقط شامل نوشتن تست unit است و تغییری در کد اصلی ایجاد نمی‌کند، بنابراین ریسک پایینی دارد. با این حال، اگر تست به درستی edge case را شبیه‌سازی نکند، ممکن است edge case واقعی پوشش داده نشود. همچنین فایل tests/test_github_import.py ممکن است وجود نداشته باشد و نیاز به ایجاد آن باشد که باید با ساختار پروژه هماهنگ شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 4: بررسی و مستندسازی fallback برای failure قابل recovery در github_import.py

**Scope:** این مرحله شامل بررسی این است که آیا failure در خط 353 قابل recovery است یا خیر. اگر قابل recovery است، باید یک fallback mechanism (مثل retry, alternative path) مستند یا پیاده‌سازی شود. خارج از این مرحله: تغییر کد اصلی برای exception handling یا log. نکته حیاتی: fallback باید در کد یا کامنت مستند شود.
**Key terms:** backend/app/api/routes/github_import.py, fallback, recover, retry, alternative

**بخش مربوط از متن کاربر:**
```
- [ ] اگر failure قابل recovery است، fallback مستند شده [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "recover", "retry", "alternative"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی و مستندسازی fallback برای failure قابل recovery در github_import.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:353` — `unknown_function` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. خط 353 به عنوان نقطه کاندید برای بررسی failure recovery مشخص شده است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص) — بر اساس ساختار پروژه، احتمالاً FastAPI + Python + GitHub API

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/github_import.py` — احتمالاً سرویس اصلی import که توسط route فراخوانی می‌شود و failure recovery باید در اینجا نیز بررسی شود
- `backend/app/services/github_storage.py` — ممکن است برای ذخیره‌سازی فایل‌های import شده استفاده شود و failure در ذخیره‌سازی نیاز به fallback داشته باشد
- `backend/app/services/smart_import.py` — سرویس هوشمند import که ممکن است alternative path برای github_import ارائه دهد

## 🌐 نقشهٔ وابستگی‌ها
فایل backend/app/api/routes/github_import.py یک route handler است که توسط فریم‌ورک FastAPI (از backend/app/main.py) ثبت می‌شود. این route احتمالاً از سرویس‌های backend/app/services/github_import.py و backend/app/services/github_storage.py استفاده می‌کند. همچنین ممکن است با backend/app/services/smart_import.py ارتباط داشته باشد. تغییر در این فایل بر روی endpoint مربوط به import پروژه از GitHub تأثیر می‌گذارد که توسط frontend فراخوانی می‌شود.

## 🔍 Context و وضعیت فعلی
بررسی و مستندسازی fallback برای failure قابل recovery در github_import.py

این مرحله شامل بررسی این است که آیا failure در خط 353 قابل recovery است یا خیر. اگر قابل recovery است، باید یک fallback mechanism (مثل retry, alternative path) مستند یا پیاده‌سازی شود. خارج از این مرحله: تغییر کد اصلی برای exception handling یا log. نکته حیاتی: fallback باید در کد یا کامنت مستند شود.

--- بخش مربوط از درخواست اصلی کاربر ---
- [ ] اگر failure قابل recovery است، fallback مستند شده [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "recover", "retry", "alternative"], "files_hint": ["backend/app/api/routes/github_import.py"]}]

--- کلیدواژه‌ها ---
backend/app/api/routes/github_import.py, fallback, recover, retry, alternative

شواهد در کد: فایل backend/app/api/routes/github_import.py در ساختار پروژه موجود است اما محتوای آن در deep context ارائه نشده است. خط 353 به عنوان نقطه کاندید برای بررسی failure recovery مشخص شده است. این فایل یک route handler برای import پروژه از GitHub است و احتمالاً شامل عملیات‌های شبکه‌ای، کلون کردن، یا دانلود فایل‌ها می‌باشد که مستعد failureهای موقت (recoverable) هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] خط 353 در backend/app/api/routes/github_import.py بررسی شده و مشخص شده که failure قابل recovery است یا خیر
- [ ] اگر failure قابل recovery است، یک fallback mechanism (retry یا alternative path) در کد یا کامنت مستند شده است
- [ ] مستندسازی شامل توضیح دلیل recoverable بودن یا نبودن failure است
- [ ] هیچ تغییری در exception handling یا log اصلی کد ایجاد نشده است (فقط مستندسازی)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/github_import.py را باز کرده و خط 353 را پیدا کنید.
2. بررسی کنید که آیا failure در آن خط قابل recovery است (مثلاً timeout شبکه، rate limit موقت، یا خطای موقتی GitHub API).
3. اگر قابل recovery است:
   - یک fallback mechanism مستند کنید: یا با کامنت در کد، یا با پیاده‌سازی retry logic ساده (مثلاً 2-3 بار تلاش مجدد با exponential backoff).
   - اگر alternative path وجود دارد (مثلاً استفاده از API دیگر یا clone با روش متفاوت)، آن را مستند کنید.
4. اگر failure قابل recovery نیست:
   - یک کامنت در کد اضافه کنید که توضیح دهد چرا این failure غیرقابل recovery است و چه اقداماتی باید انجام شود.
5. از تغییر exception handling یا log اصلی خودداری کنید (طبق دستور کاربر).
6. مستندسازی می‌تواند به صورت کامنت در کد یا یک docstring در تابع مربوطه باشد.

## 💡 نمونه‌های قبل/بعد
**مستندسازی fallback در خط 353**

_قبل:_
```
# خط 353 فعلی (نیاز به بررسی دارد)
```

_بعد:_
```
# Fallback mechanism: اگر این خط با failure موقتی مواجه شد (مثلاً timeout یا rate limit)،
# از retry logic با 2 بار تلاش مجدد و exponential backoff استفاده کنید.
# اگر retry هم ناموفق بود، از alternative path (smart_import) استفاده شود.
# این failure قابل recovery است زیرا خطاهای شبکه معمولاً موقتی هستند.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -n 'fallback\|recover\|retry\|alternative' backend/app/api/routes/github_import.py`
- `grep -n '353' backend/app/api/routes/github_import.py`
- `git diff backend/app/api/routes/github_import.py`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل backend/app/api/routes/github_import.py deep-read نشده است، بنابراین نمی‌توان با قطعیت گفت که خط 353 چه عملیاتی انجام می‌دهد. اگر این خط بخشی از یک عملیات بحرانی (مثلاً clone repository) باشد، مستندسازی نادرست می‌تواند گمراه‌کننده باشد. همچنین اگر فایل توسط چندین route دیگر import شود، تغییرات باید با دقت بررسی شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 5: بررسی caller upstream برای عدم break در github_import.py

**Scope:** این مرحله شامل بررسی callerهای upstream تابع حاوی خط 353 در backend/app/api/routes/github_import.py است تا اطمینان حاصل شود که تغییر silent failure به raise یا log باعث break نمی‌شود. خارج از این مرحله: تغییر کد در callerها. نکته حیاتی: اگر caller فرض می‌کند تابع همیشه return می‌کند، باید آن را اصلاح کرد.
**Key terms:** backend/app/api/routes/github_import.py, upstream caller, return

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر silent failure به raise ممکن است upstream caller را break کند که فرض می‌کرده این تابع همیشه return می‌کند. caller را هم چک کن.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی callerهای upstream github_import برای عدم break

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:350-360` — `تابع حاوی خط 353 (نام دقیق نیاز به تأیید دارد)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. خط 353 احتمالاً شامل یک return None یا pass در حالت خطا است که باید به raise یا log تبدیل شود.
- `backend/app/services/github_import.py:1-50` — `کل فایل سرویس` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً caller اصلی تابع route است و باید بررسی شود که آیا به return value وابسته است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/github_import.py` (سطر 353) — فایل اصلی حاوی تابع هدف در خط 353
- `backend/app/services/github_import.py` — سرویس پشتیبان که احتمالاً توسط route فراخوانی می‌شود و ممکن است caller upstream باشد
- `backend/app/services/external_project_connector.py` — ممکن است از github_import استفاده کند و caller upstream باشد
- `backend/app/services/smart_import.py` — ممکن است از github_import استفاده کند و caller upstream باشد

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل backend/app/api/routes/github_import.py (خط 353) وابسته است. callerهای upstream می‌توانند شامل backend/app/services/github_import.py، backend/app/services/external_project_connector.py، backend/app/services/smart_import.py باشند. همچنین ممکن است routeهای دیگر در backend/app/api/routes/ (مثلاً projects.py یا external_projects.py) از این تابع استفاده کنند. تغییر silent failure به raise می‌تواند روی تمام این callerها تأثیر بگذارد.

## 🔍 Context و وضعیت فعلی
بررسی caller upstream برای عدم break در github_import.py. این مرحله شامل بررسی callerهای upstream تابع حاوی خط 353 در backend/app/api/routes/github_import.py است تا اطمینان حاصل شود که تغییر silent failure به raise یا log باعث break نمی‌شود. خارج از این مرحله: تغییر کد در callerها. نکته حیاتی: اگر caller فرض می‌کند تابع همیشه return می‌کند، باید آن را اصلاح کرد. --- بخش مربوط از درخواست اصلی کاربر --- ## ⚠️ ریسک‌ها و موارد احتیاط تغییر silent failure به raise ممکن است upstream caller را break کند که فرض می‌کرده این تابع همیشه return می‌کند. caller را هم چک کن. --- کلیدواژه‌ها --- backend/app/api/routes/github_import.py, upstream caller, return. شواهد در کد: فایل github_import.py در backend/app/api/routes/ موجود است و خط 353 در deep context خوانده نشده است. بر اساس ساختار سطحی، این فایل شامل routeهای مربوط به import از GitHub است و احتمالاً تابعی در خط 353 وجود دارد که ممکن است در حالت خطا به‌صورت silent failure عمل کند (مثلاً return None یا pass). callerهای upstream می‌توانند routeهای دیگر در همان فایل یا سرویس‌های خارجی مثل github_import.py در backend/app/services/ باشند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تمامی callerهای تابع حاوی خط 353 در backend/app/api/routes/github_import.py شناسایی و مستند شوند
- [ ] برای هر caller، وابستگی به return value تابع بررسی شود و در صورت نیاز اصلاح گردد
- [ ] هیچ caller بعد از تغییر، break نشود (همه routeهای مرتبط با import از GitHub کار کنند)
- [ ] تغییر silent failure به raise باعث لاگ مناسب خطا شود (بدون break در callerهایی که خطا را مدیریت نمی‌کنند)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/github_import.py را باز کرده و خط 353 را پیدا کن. 2. تابع حاوی خط 353 را شناسایی کن (مثلاً handle_github_import یا import_repository). 3. تمام callerهای این تابع را در پروژه جستجو کن (با grep برای نام تابع). 4. برای هر caller، بررسی کن که آیا بعد از فراخوانی تابع، به return value آن وابسته است یا خیر. 5. اگر caller فرض می‌کند تابع همیشه return می‌کند (مثلاً result = func() و سپس استفاده از result)، باید آن caller اصلاح شود تا با raise یا log سازگار شود. 6. اگر caller فقط تابع را صدا می‌زند و به return value نیاز ندارد، تغییر safe است. 7. در صورت نیاز، caller را با try/except یا بررسی return value اصلاح کن. 8. مستندات تغییرات را در description ذکر کن.

## 💡 نمونه‌های قبل/بعد
**تغییر پیشنهادی در تابع هدف (خط 353)**

_قبل:_
```
# قبل: silent failure
if error:
    return None
```

_بعد:_
```
# بعد: raise exception
if error:
    raise ValueError("خطا در import: ...")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k github_import`
- `grep -rn 'function_name_at_line_353' backend/`
- `python -c "from backend.app.api.routes.github_import import function_name_at_line_353; print('OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: اگر caller فرض کند تابع همیشه return می‌کند (مثلاً result = func() و سپس result.something)، تغییر به raise باعث break می‌شود. فایل‌های backend/app/services/github_import.py و backend/app/services/external_project_connector.py ممکن است تحت تأثیر قرار گیرند. همچنین routeهای دیگر در backend/app/api/routes/ که از این تابع استفاده می‌کنند باید بررسی شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 6: اجرای linter و type-check برای github_import.py

**Scope:** این مرحله شامل اجرای linter (ruff) و type-check (mypy) روی فایل backend/app/api/routes/github_import.py برای اطمینان از عدم وجود warning یا error است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.
**Key terms:** backend/app/api/routes/github_import.py, ruff, mypy, py_compile

**بخش مربوط از متن کاربر:**
```
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای linter و type-check برای github_import.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:1-50` — `full_file` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل در ساختار پروژه موجود است و باید lint/type-check روی آن اجرا شود.
- `backend/app/services/github_import.py:1-30` — `full_file` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این سرویس توسط github_import.py route استفاده می‌شود و ممکن است type-check روی آن نیز تأثیر بگذارد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/github_pr_service.py` — این سرویس توسط github_import.py route استفاده می‌شود و تغییرات type ممکن است بر compatibility تأثیر بگذارد.
- `backend/app/services/storage_service.py` — این سرویس برای ذخیره‌سازی داده‌های import شده استفاده می‌شود و type-check ممکن است نیاز به تطابق typeها داشته باشد.
- `backend/tests/test_runtime_verify_integration.py` — این تست ممکن است github_import.py route را تست کند و lint/type changes باید با تست‌ها سازگار باشد.

## 🌐 نقشهٔ وابستگی‌ها
فایل backend/app/api/routes/github_import.py به عنوان یک route در API پروژه عمل می‌کند و از سرویس‌های backend/app/services/github_import.py و backend/app/services/github_pr_service.py برای مدیریت import پروژه‌های خارجی استفاده می‌کند. همچنین با backend/app/services/storage_service.py برای ذخیره‌سازی داده‌ها در ارتباط است. تغییرات lint/type در این فایل ممکن است بر compatibility با این سرویس‌ها تأثیر بگذارد. فایل‌های test مانند backend/tests/test_runtime_verify_integration.py و backend/tests/test_runtime_verify_stage1.py ممکن است از این route استفاده کنند و باید پس از تغییرات مجدداً اجرا شوند.

## 🔍 Context و وضعیت فعلی
این تسک شامل اجرای linter (ruff) و type-check (mypy) روی فایل backend/app/api/routes/github_import.py برای اطمینان از عدم وجود warning یا error است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند. بخش مربوط از درخواست اصلی کاربر: [ ] linter بدون warning عبور می‌کند، [ ] type-check موفق است (tsc --noEmit / mypy). دستورات اعتبارسنجی: python -m py_compile backend/app/api/routes/github_import.py و ruff check backend/app/api/routes/github_import.py. کلیدواژه‌ها: backend/app/api/routes/github_import.py, ruff, mypy, py_compile. فایل هدف در مسیر backend/app/api/routes/github_import.py قرار دارد و بخشی از API routes پروژه است. این فایل مسئول مدیریت import پروژه‌های خارجی از GitHub است و با سرویس‌هایی مانند github_import.py، github_pr_service.py و storage_service.py در ارتباط است. بررسی ساختار پروژه نشان می‌دهد که این فایل از ماژول‌های backend/app/services/github_import.py و backend/app/services/github_pr_service.py استفاده می‌کند. همچنین فایل‌های test مرتبط مانند test_runtime_verify_integration.py و test_runtime_verify_stage1.py ممکن است تحت تأثیر تغییرات قرار گیرند. هدف نهایی اطمینان از کیفیت کد و جلوگیری از بروز خطاهای runtime است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] دستور python -m py_compile backend/app/api/routes/github_import.py بدون error اجرا شود.
- [ ] دستور ruff check backend/app/api/routes/github_import.py بدون warning یا error اجرا شود.
- [ ] دستور mypy backend/app/api/routes/github_import.py بدون warning یا error اجرا شود.
- [ ] هیچ تغییری در logic فایل github_import.py ایجاد نشود و فقط lint/type issues رفع شده باشند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. اجرای دستور python -m py_compile backend/app/api/routes/github_import.py برای بررسی compile-time errors.
2. اجرای دستور ruff check backend/app/api/routes/github_import.py برای شناسایی linting issues.
3. اجرای mypy backend/app/api/routes/github_import.py برای type-checking.
4. در صورت وجود warning یا error، آن‌ها را در فایل backend/app/api/routes/github_import.py رفع کن.
5. پس از رفع، دوباره دستورات 1 تا 3 را اجرا کن تا از عبور بدون warning اطمینان حاصل شود.
6. اطمینان حاصل کن که هیچ تغییری در logic فایل ایجاد نشده و فقط lint/type issues رفع شده‌اند.

## 💡 نمونه‌های قبل/بعد
**نمونه lint error رفع‌شده**

_قبل:_
```
import os
import sys
from typing import List, Optional

def import_project(url: str) -> None:
    pass
```

_بعد:_
```
from typing import List, Optional

def import_project(url: str) -> None:
    """Import a project from GitHub URL."""
    pass
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `mypy backend/app/api/routes/github_import.py`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل backend/app/api/routes/github_import.py توسط سرویس‌های backend/app/services/github_import.py و backend/app/services/github_pr_service.py استفاده می‌شود. تغییرات type ممکن است نیاز به تطابق typeها در این سرویس‌ها داشته باشد. همچنین تست‌های backend/tests/test_runtime_verify_integration.py ممکن است تحت تأثیر قرار گیرند. ریسک اصلی ایجاد breaking changes در API route است.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 7: بررسی و شناسایی عدم مدیریت خطا در auto_setup_project_memory در github_import.py

**Scope:** این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py، به ویژه تابع import_repository (خطوط 132-157) و نحوه استفاده از auto_setup_project_memory است. هدف شناسایی try/except موجود و بررسی کافی بودن آن است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: باید مشخص شود که آیا خطا در auto_setup_project_memory باعث 500 می‌شود و پروژه بدون setup می‌ماند.
**Key terms:** backend/app/api/routes/github_import.py, import_repository, auto_setup_project_memory, result["auto_setup"]

**بخش مربوط از متن کاربر:**
```
در `backend/app/api/routes/github_import.py`، تابع `import_repository` (خط 132-157) از `auto_setup_project_memory` استفاده می‌کند. اگر این تابع خطا بدهد، کل درخواست import با خطای 500 مواجه می‌شود و پروژه import شده اما بدون setup باقی می‌ماند. در حال حاضر یک try/except وجود دارد که خطا را در `result["auto_setup"]` ذخیره می‌کند، اما این کافی
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی عدم مدیریت خطا در auto_setup_project_memory در github_import.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:132-157` — `import_repository` — تابع اصلی که auto_setup_project_memory را صدا می‌زند. try/except موجود خطا را در result ذخیره می‌کند اما ممکن است کافی نباشد.
  ```python
  async def import_repository(...):
      ...
      try:
          result = await auto_setup_project_memory(...)
      except Exception as e:
          result["auto_setup"] = {"error": str(e)}
      ...
  ```
- `backend/app/services/github_import.py:1-50` — `auto_setup_project_memory` — تابعی که auto_setup را انجام می‌دهد. باید بررسی شود که چه استثناهایی پرتاب می‌کند و آیا خطاهای آن به درستی مدیریت می‌شوند.
  ```python
  async def auto_setup_project_memory(project_id: int, ...):
      # پیاده‌سازی فعلی
      ...
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/github_import.py` (سطر 1) — حاوی auto_setup_project_memory که توسط import_repository صدا زده می‌شود
- `backend/app/models/project.py` (سطر 1) — مدل Project که auto_setup روی آن کار می‌کند
- `backend/app/services/project_service.py` (سطر 1) — احتمالاً توسط auto_setup_project_memory برای ذخیره‌سازی استفاده می‌شود

## 🌐 نقشهٔ وابستگی‌ها
فایل backend/app/api/routes/github_import.py تابع import_repository را تعریف می‌کند که auto_setup_project_memory را از backend/app/services/github_import.py صدا می‌زند. auto_setup_project_memory با مدل Project (backend/app/models/project.py) و سرویس project_service (backend/app/services/project_service.py) تعامل دارد. اگر auto_setup_project_memory خطا بدهد، ممکن است پروژه در وضعیت ناقص بماند و خطا به API برگردد.

## 🔍 Context و وضعیت فعلی
بررسی و شناسایی عدم مدیریت خطا در auto_setup_project_memory در github_import.py. این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py، به ویژه تابع import_repository (خطوط 132-157) و نحوه استفاده از auto_setup_project_memory است. هدف شناسایی try/except موجود و بررسی کافی بودن آن است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: باید مشخص شود که آیا خطا در auto_setup_project_memory باعث 500 می‌شود و پروژه بدون setup می‌ماند. در backend/app/api/routes/github_import.py، تابع import_repository (خط 132-157) از auto_setup_project_memory استفاده می‌کند. اگر این تابع خطا بدهد، کل درخواست import با خطای 500 مواجه می‌شود و پروژه import شده اما بدون setup باقی می‌ماند. در حال حاضر یک try/except وجود دارد که خطا را در result["auto_setup"] ذخیره می‌کند، اما این کافی نیست. کلیدواژه‌ها: backend/app/api/routes/github_import.py, import_repository, auto_setup_project_memory, result["auto_setup"]. شواهد در کد: فایل backend/app/api/routes/github_import.py در خطوط 132-157 تابع import_repository را تعریف می‌کند که auto_setup_project_memory را صدا می‌زند. فایل backend/app/services/github_import.py تابع auto_setup_project_memory را پیاده‌سازی می‌کند. بررسی دقیق try/except موجود و شناسایی نقاط ضعف آن ضروری است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] خطا در auto_setup_project_memory باعث 500 نشود و پروژه با وضعیت partial setup ذخیره شود
- [ ] لاگ خطا در صورت failure auto_setup_project_memory ثبت شود
- [ ] پروژه import شده حتی اگر auto_setup شکست بخورد، در دیتابیس باقی بماند
- [ ] مستندسازی تحلیل در یک فایل جداگانه ذخیره شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/github_import.py را باز کرده و تابع import_repository (خطوط 132-157) را بررسی کن. 2. بلوک try/except موجود که auto_setup_project_memory را احاطه کرده استخراج کن. 3. مشخص کن که آیا except فقط خطا را در result["auto_setup"] ذخیره می‌کند یا خطا را به caller منتقل می‌کند. 4. اگر خطا swallow شده و پروژه بدون setup می‌ماند، یک مکانیزم fallback یا logging اضافه کن. 5. اگر خطا باعث 500 می‌شود، یک try/except اضافی در سطح بالاتر یا یک handler برای auto_setup_project_memory اضافه کن تا خطا مدیریت شود و پروژه با وضعیت partial setup ذخیره شود. 6. فایل backend/app/services/github_import.py را بررسی کن تا ببینی auto_setup_project_memory چه استثناهایی می‌تواند پرتاب کند. 7. نتیجه تحلیل را در قالب یک گزارش مستند کن.

## 💡 نمونه‌های قبل/بعد
**مدیریت خطا در import_repository**

_قبل:_
```
try:
    result = await auto_setup_project_memory(...)
except Exception as e:
    result["auto_setup"] = {"error": str(e)}
```

_بعد:_
```
try:
    result = await auto_setup_project_memory(...)
except Exception as e:
    logger.error(f"auto_setup failed for project {project_id}: {e}")
    result["auto_setup"] = {"error": str(e), "status": "partial"}
    # fallback: ذخیره پروژه بدون setup
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_github_import.py`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در try/except import_repository ممکن است روی رفتار سایر بخش‌های import تأثیر بگذارد. auto_setup_project_memory توسط فایل‌های دیگر نیز صدا زده می‌شود (اگر وجود داشته باشد). باید اطمینان حاصل شود که fallback منطقی است و داده‌ها را خراب نمی‌کند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 8: بهبود مدیریت خطا برای auto_setup_project_memory در import_repository

**Scope:** این مرحله شامل بهبود try/except موجود در تابع import_repository در backend/app/api/routes/github_import.py برای auto_setup_project_memory است. باید خطا را به درستی log کند و fallback مناسب (مثل ادامه بدون setup) فراهم کند. خارج از این مرحله: نوشتن تست، تغییر سایر فایل‌ها. نکته حیاتی: تغییر نباید تست‌های موجود را بشکند.
**Key terms:** backend/app/api/routes/github_import.py, import_repository, auto_setup_project_memory, try, except

**بخش مربوط از متن کاربر:**
```
## 🎯 هدف (خلاصه ساختاریافته)
عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)
```

## 🎯 هدف (خلاصه ساختاریافته)
بهبود مدیریت خطای auto_setup_project_memory در import_repository

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py:نامشخص (فایل deep-read نشده)` — `import_repository` — بر اساس ساختار سطحی — توسط مجری تأیید شود. این فایل deep-read نشده، اما بر اساس درخواست کاربر، تابع import_repository در این مسیر قرار دارد و باید try/except برای auto_setup_project_memory بهبود یابد.
- `backend/app/services/project_auto_setup.py:نامشخص (فایل deep-read نشده)` — `auto_setup_project_memory` — بر اساس ساختار سطحی — توسط مجری تأیید شود. این فایل احتمالاً حاوی تابع auto_setup_project_memory است که توسط import_repository فراخوانی می‌شود. برای درک signature و رفتار تابع، باید این فایل بررسی شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/project_service.py` — احتمالاً auto_setup_project_memory در این فایل یا project_auto_setup.py تعریف شده است. تغییر در github_import.py ممکن است نیاز به بررسی این فایل داشته باشد.
- `backend/app/api/routes/projects.py` — این فایل نیز ممکن است auto_setup_project_memory را فراخوانی کند و تغییرات مشابهی نیاز داشته باشد.
- `backend/tests/test_runtime_verify_integration.py` — تست‌های موجود که ممکن است تحت تأثیر تغییر قرار گیرند. باید مطمئن شویم که تغییرات تست‌ها را نمی‌شکند.

## 🌐 نقشهٔ وابستگی‌ها
این تغییر فقط بر فایل backend/app/api/routes/github_import.py تأثیر می‌گذارد. تابع import_repository در این فایل، auto_setup_project_memory را از سرویس project_auto_setup.py یا project_service.py فراخوانی می‌کند. بهبود try/except باعث می‌شود که خطاهای auto_setup_project_memory به درستی log شوند و فرآیند import بدون شکست ادامه یابد. هیچ وابستگی به فایل‌های frontend یا سایر سرویس‌ها وجود ندارد. تست‌های موجود در backend/tests/ (مانند test_runtime_verify_integration.py) باید بدون تغییر پاس شوند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست بهبود مدیریت خطا برای auto_setup_project_memory در تابع import_repository در فایل backend/app/api/routes/github_import.py را دارد. این مرحله شامل بهبود try/except موجود در تابع import_repository برای auto_setup_project_memory است. باید خطا را به درستی log کند و fallback مناسب (مثل ادامه بدون setup) فراهم کند. خارج از این مرحله: نوشتن تست، تغییر سایر فایل‌ها. نکته حیاتی: تغییر نباید تست‌های موجود را بشکند. بخش مربوط از درخواست اصلی کاربر: 'عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory'. کلیدواژه‌ها: backend/app/api/routes/github_import.py, import_repository, auto_setup_project_memory, try, except. با توجه به deep context موجود، فایل github_import.py deep-read نشده است، اما بر اساس ساختار پروژه و commit‌های اخیر (مثلاً 677c46f و 7d341e3 که مربوط به inspector و compare-verify-buttons هستند)، این فایل در مسیر backend/app/api/routes/github_import.py قرار دارد و احتمالاً حاوی تابع import_repository است که auto_setup_project_memory را فراخوانی می‌کند. auto_setup_project_memory احتمالاً در سرویس project_auto_setup.py یا project_service.py تعریف شده است. هدف: افزودن try/except مناسب برای catch کردن خطاهای auto_setup_project_memory، log کردن خطا با logging.error، و fallback به ادامه فرآیند بدون setup (مثلاً با return None یا raise نکردن exception).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تابع import_repository در github_import.py باید خطاهای auto_setup_project_memory را با logging.error log کند.
- [ ] در صورت خطا در auto_setup_project_memory، فرآیند import باید ادامه یابد (بدون raise exception).
- [ ] تغییرات نباید تست‌های موجود را بشکند (pytest backend/tests/ باید پاس شود).
- [ ] هیچ فایل دیگری غیر از github_import.py تغییر نکند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/github_import.py را باز کن و تابع import_repository را پیدا کن. 2. خطوطی که auto_setup_project_memory را فراخوانی می‌کنند (احتمالاً با await یا بدون await) شناسایی کن. 3. یک try/except جدید یا بهبود try/except موجود اضافه کن: در بخش try، فراخوانی auto_setup_project_memory را قرار بده. در بخش except Exception as e، خطا را با logging.error(f"Failed to auto_setup_project_memory: {e}") log کن. سپس یک fallback مثل ادامه بدون setup (مثلاً با return project یا ادامه حلقه) فراهم کن. 4. مطمئن شو که تغییرات تست‌های موجود را نمی‌شکند (با اجرای pytest backend/tests/). 5. هیچ فایل دیگری تغییر نکند. 6. از auto_setup_project_memory در فایل‌های مرتبط مثل backend/app/services/project_auto_setup.py یا backend/app/services/project_service.py اطمینان حاصل کن که تابع auto_setup_project_memory وجود دارد و signature آن مشخص است.

## 💡 نمونه‌های قبل/بعد
**بهبود try/except برای auto_setup_project_memory**

_قبل:_
```
# کد فعلی (فرضی)
project = await auto_setup_project_memory(project_id)
# بدون try/except
```

_بعد:_
```
# کد پیشنهادی
try:
    project = await auto_setup_project_memory(project_id)
except Exception as e:
    logging.error(f"Failed to auto_setup_project_memory for project {project_id}: {e}")
    # fallback: ادامه بدون setup
    project = None
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -x --timeout=60`
- `grep -rn 'auto_setup_project_memory' backend/app/api/routes/github_import.py`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی: اگر auto_setup_project_memory در فایل‌های دیگر (مثل projects.py) نیز فراخوانی شود و تغییرات مشابه اعمال نشود، ممکن است ناهماهنگی ایجاد شود. همچنین اگر logging به درستی پیکربندی نشده باشد، logها ثبت نمی‌شوند. با توجه به اینکه فایل deep-read نشده، ممکن است signature تابع auto_setup_project_memory با فرضیات ما متفاوت باشد (مثلاً synchronous باشد).

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 9: نوشتن تست برای edge case auto_setup_project_memory failure

**Scope:** این مرحله شامل نوشتن یک تست unit در tests/test_github_import.py برای سناریوی failure در auto_setup_project_memory است. تست باید بررسی کند که import_repository با خطا مواجه نمی‌شود و fallback به درستی کار می‌کند. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration. نکته حیاتی: تست باید با pytest کار کند و edge case را پوشش دهد.
**Key terms:** tests/test_github_import.py, pytest, auto_setup_project_memory, import_repository

**بخش مربوط از متن کاربر:**
```
- [ ] اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
```

## 🎯 هدف (خلاصه ساختاریافته)
تست edge case auto_setup_project_memory failure در github_import

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/test_github_import.py` — `test_import_repository_auto_setup_memory_fallback` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. فایل در ساختار پروژه موجود است (backend/tests/test_github_import.py). تست جدید باید به این فایل اضافه شود.
- `backend/app/services/github_import.py` — `import_repository` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. تابع import_repository در این فایل قرار دارد و باید تست شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/github_import.py` — فایل اصلی حاوی تابع import_repository که تست برای آن نوشته می‌شود. auto_setup_project_memory احتمالاً در این فایل یا فایل مرتبط فراخوانی می‌شود.
- `backend/app/services/project_auto_setup.py` — احتمالاً حاوی تابع auto_setup_project_memory است که failure آن باید شبیه‌سازی شود. این فایل در سرویس‌ها موجود است.
- `backend/app/services/project_service.py` — ممکن است import_repository از این سرویس برای مدیریت پروژه استفاده کند. تغییرات در github_import می‌تواند روی project_service تأثیر بگذارد.

## 🌐 نقشهٔ وابستگی‌ها
این تست به فایل tests/test_github_import.py اضافه می‌شود و تابع import_repository از github_import.py را تست می‌کند. auto_setup_project_memory احتمالاً در project_auto_setup.py تعریف شده است. تست از pytest و unittest.mock برای شبیه‌سازی failure استفاده می‌کند. تست‌های موجود در test_github_import.py نباید شکسته شوند. فایل‌های مرتبط: github_import.py (تابع اصلی), project_auto_setup.py (auto_setup_project_memory), project_service.py (مدیریت پروژه).

## 🔍 Context و وضعیت فعلی
نوشتن تست unit برای edge case auto_setup_project_memory failure در tests/test_github_import.py. کاربر درخواست کرده که یک تست unit در tests/test_github_import.py برای سناریوی failure در auto_setup_project_memory نوشته شود. تست باید بررسی کند که import_repository با خطا مواجه نمی‌شود و fallback به درستی کار می‌کند. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration. نکته حیاتی: تست باید با pytest کار کند و edge case را پوشش دهد. بخش مربوط از درخواست اصلی کاربر: [ ] اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]. کلیدواژه‌ها: tests/test_github_import.py, pytest, auto_setup_project_memory, import_repository. با توجه به deep context موجود، فایل tests/test_github_import.py در ساختار پروژه وجود دارد (backend/tests/test_github_import.py) اما محتوای آن deep-read نشده است. فایل backend/app/services/github_import.py نیز در سرویس‌ها موجود است اما محتوای آن در دسترس نیست. بنابراین باید بر اساس ساختار سطحی و نام‌های موجود عمل کرد. تست باید در فایل tests/test_github_import.py نوشته شود و edge case failure auto_setup_project_memory را پوشش دهد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست unit جدید در tests/test_github_import.py با نام test_import_repository_auto_setup_memory_fallback ایجاد شود که سناریوی failure auto_setup_project_memory را پوشش دهد.
- [ ] تست از pytest monkeypatch یا unittest.mock برای شبیه‌سازی failure auto_setup_project_memory استفاده کند.
- [ ] تست بررسی کند که import_repository با خطا مواجه نمی‌شود (بدون raise exception) و fallback به درستی کار می‌کند.
- [ ] اجرای pytest backend/tests/test_github_import.py بدون شکستن تست‌های موجود (همه تست‌ها پاس شوند).
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. باز کردن فایل backend/tests/test_github_import.py و بررسی تست‌های موجود برای فهم الگوی نوشتاری. 2. ایجاد یک تابع تست جدید با نام test_import_repository_auto_setup_memory_fallback که سناریوی failure در auto_setup_project_memory را شبیه‌سازی کند. 3. استفاده از pytest monkeypatch یا unittest.mock برای شبیه‌سازی failure در auto_setup_project_memory. 4. فراخوانی import_repository و بررسی اینکه با خطا مواجه نمی‌شود. 5. بررسی اینکه fallback به درستی کار می‌کند (مثلاً log مناسب ثبت شده یا state خاصی تنظیم شده). 6. اجرای pytest backend/tests/test_github_import.py برای اطمینان از عدم شکستن تست‌های موجود. 7. edge case باید شامل مواردی مثل: auto_setup_project_memory خطا抛出 کند، None برگرداند، یا timeout شود.

## 💡 نمونه‌های قبل/بعد
**نمونه تست جدید برای edge case**

_قبل:_
```
# فایل tests/test_github_import.py (فعلاً بدون تست auto_setup_memory failure)
```

_بعد:_
```
import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.github_import import import_repository

def test_import_repository_auto_setup_memory_fallback():
    """
    تست سناریوی failure در auto_setup_project_memory.
    بررسی می‌کند که import_repository با خطا مواجه نمی‌شود و fallback به درستی کار می‌کند.
    """
    with patch('backend.app.services.github_import.auto_setup_project_memory', side_effect=Exception("Memory setup failed")):
        result = import_repository(repo_url="https://github.com/test/repo.git")
        assert result is not None  # یا assert عدم وجود خطا
        # بررسی fallback: مثلاً log ثبت شده یا state خاصی تنظیم شده
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_github_import.py -v`
- `pytest backend/tests/test_github_import.py::test_import_repository_auto_setup_memory_fallback -v`

## ⚠️ ریسک‌ها و موارد احتیاط
فایل tests/test_github_import.py deep-read نشده، بنابراین ممکن است الگوی نوشتاری تست‌های موجود ناشناخته باشد. همچنین تابع import_repository و auto_setup_project_memory در فایل‌های اصلی deep-read نشده‌اند، بنابراین ممکن است signature دقیق آن‌ها مشخص نباشد. ریسک: تست ممکن است با signature واقعی توابع مطابقت نداشته باشد و نیاز به اصلاح داشته باشد. همچنین اگر auto_setup_project_memory در فایل دیگری غیر از github_import.py تعریف شده باشد، مسیر import در patch باید اصلاح شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 10: اجرای linter و type-check برای کل backend پس از تغییرات

**Scope:** این مرحله شامل اجرای linter (ruff) و type-check (mypy) روی کل پوشه backend برای اطمینان از عدم وجود warning یا error پس از تغییرات است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.
**Key terms:** backend/, ruff, mypy, lint, type-check

**بخش مربوط از متن کاربر:**
```
- [ ] linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
- [ ] type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore", "type-check"], "files_hint": ["backend/"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای linter و type-check برای کل backend پس از تغییرات

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/requirements.txt` — `requirements.txt` — فایل وابستگی‌ها — باید شامل ruff و mypy باشد. بر اساس ساختار سطحی — توسط مجری تأیید شود.
- `backend/app/main.py` — `main.py` — نقطه ورود backend — lint و type-check باید این فایل را پوشش دهند. بر اساس ساختار سطحی — توسط مجری تأیید شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص) — بر اساس ساختار پروژه: Python (FastAPI/Flask)، ابزارهای linting: ruff، ابزارهای type-check: mypy

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/config.py` — تنظیمات اصلی پروژه — ممکن است lint/type-check روی آن تأثیر بگذارد
- `backend/app/services/` — پوشه سرویس‌ها — بخش عمده کد backend در اینجاست
- `backend/app/api/routes/` — پوشه روت‌ها — شامل endpointهای API
- `backend/tests/` — پوشه تست‌ها — lint/type-check باید تست‌ها را هم پوشش دهد

## 🌐 نقشهٔ وابستگی‌ها
این تسک وابسته به وجود ابزارهای ruff و mypy در محیط توسعه است. فایل backend/requirements.txt باید شامل این دو ابزار باشد. اجرای lint/type-check روی کل پوشه backend شامل فایل‌های app/main.py، app/core/config.py، app/services/، app/api/routes/، app/models/ و tests/ می‌شود. هیچ وابستگی runtime خاصی ندارد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست اجرای linter (ruff) و type-check (mypy) روی کل پوشه backend برای اطمینان از عدم وجود warning یا error پس از تغییرات را دارد. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.

بخش مربوط از درخواست اصلی کاربر:
- [ ] linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
- [ ] type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore", "type-check"], "files_hint": ["backend/"]}]

کلیدواژه‌ها: backend/, ruff, mypy, lint, type-check

بر اساس ساختار پروژه، فایل‌های backend در پوشه‌های app/api/routes، app/services، app/models، app/core و tests قرار دارند. فایل requirements.txt شامل وابستگی‌هاست. فایل‌های تست در backend/tests/ موجود هستند. هیچ فایل deep-read شده‌ای برای استناد دقیق به خطوط کد موجود نیست.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] linter (ruff) روی کل پوشه backend بدون warning عبور کند
- [ ] type-check (mypy) روی کل پوشه backend بدون warning عبور کند
- [ ] هیچ error یا warning جدیدی در خروجی lint/type-check وجود نداشته باشد
- [ ] فایل backend/requirements.txt شامل ruff و mypy باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. اجرای linter (ruff) روی کل پوشه backend با دستور: `ruff check backend/`
2. بررسی خروجی برای وجود warning یا error
3. اجرای type-check (mypy) روی کل پوشه backend با دستور: `mypy backend/`
4. بررسی خروجی برای وجود warning یا error
5. اگر خطایی وجود داشت، باید خطاها گزارش شوند (تغییر کد برای رفع خطاها خارج از این تسک است)
6. اطمینان از عبور بدون warning هر دو ابزار

فایل‌های مرتبط: backend/requirements.txt (شامل ruff و mypy)، backend/app/main.py (نقطه ورود)، backend/app/core/config.py (تنظیمات)، backend/app/services/ (سرویس‌ها)، backend/app/api/routes/ (روت‌ها)

## 💡 نمونه‌های قبل/بعد
**اجرای linter روی backend**

_قبل:_
```
دستور: ruff check backend/ (ممکن است warning/error داشته باشد)
```

_بعد:_
```
دستور: ruff check backend/ (بدون warning/error)
```

**اجرای type-check روی backend**

_قبل:_
```
دستور: mypy backend/ (ممکن است warning/error داشته باشد)
```

_بعد:_
```
دستور: mypy backend/ (بدون warning/error)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `ruff check backend/`
- `mypy backend/`

## ⚠️ ریسک‌ها و موارد احتیاط
این تسک فقط اجرای ابزارهای lint/type-check است و تغییری در کد ایجاد نمی‌کند. ریسک خاصی ندارد. اگر ابزارها نصب نباشند، دستورات fail می‌شوند که نیاز به نصب دارد. فایل‌های backend/requirements.txt و backend/app/main.py تحت تأثیر قرار نمی‌گیرند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 11: اجرای تمام تست‌های backend برای اطمینان از عدم رگرشن

**Scope:** این مرحله شامل اجرای تمام تست‌های backend با pytest برای اطمینان از اینکه تغییرات باعث شکستن تست‌های موجود نمی‌شود. خارج از این مرحله: تغییر کد، اجرای تست‌های frontend. نکته حیاتی: هیچ تستی نباید fail شود.
**Key terms:** pytest, tests/, npm run test

**بخش مربوط از متن کاربر:**
```
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)

## 🧪 دستورات اعتبارسنجی
- `pytest`
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای تمام تست‌های backend با pytest برای اطمینان از عدم رگرشن

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/test_runtime_verify_stage1.py:1-50` — `test_*` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. یکی از فایل‌های تست backend که باید اجرا شود.
  ```python
  # فایل deep-read نشده — بر اساس ساختار سطحی
  ```
- `backend/tests/test_runtime_verify_stage2.py:1-50` — `test_*` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. یکی از فایل‌های تست backend که باید اجرا شود.
  ```python
  # فایل deep-read نشده — بر اساس ساختار سطحی
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده در بالا = (نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/requirements.txt` (سطر 1) — فایل وابستگی‌های پروژه که pytest و سایر کتابخانه‌های تست را مشخص می‌کند
- `docker-compose.yml` (سطر 1) — فایل Docker Compose که محیط تست را تعریف می‌کند و ممکن است برای اجرای تست‌ها نیاز به سرویس‌های خاصی داشته باشد
- `backend/app/main.py` (سطر 1) — فایل اصلی برنامه که ممکن است تست‌ها به آن وابسته باشند

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های تست در backend/tests/ وابسته است. فایل requirements.txt شامل وابستگی‌های pytest و سایر کتابخانه‌ها است. docker-compose.yml محیط اجرای تست را مشخص می‌کند. فایل main.py نقطه ورود برنامه است که تست‌ها ممکن است به آن نیاز داشته باشند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست اجرای تمام تست‌های backend با pytest برای اطمینان از اینکه تغییرات باعث شکستن تست‌های موجود نمی‌شود را دارد. خارج از این مرحله: تغییر کد، اجرای تست‌های frontend. نکته حیاتی: هیچ تستی نباید fail شود. بخش مربوط از درخواست اصلی کاربر: '[ ] هیچ تستی fail نمی‌شود (npm run test / pytest)'. دستورات اعتبارسنجی: 'pytest'. کلیدواژه‌ها: pytest, tests/, npm run test. با توجه به ساختار پروژه، فایل‌های تست در مسیر backend/tests/ قرار دارند و شامل تست‌های مختلفی مانند test_code_content_searcher.py, test_inspector_oversight_bridge.py, test_iterative_orchestrator.py, test_runtime_verify_autodetect.py, test_runtime_verify_integration.py, test_runtime_verify_real_servers.py, test_runtime_verify_stage1.py, test_runtime_verify_stage2.py, test_runtime_verify_stage3a.py, test_runtime_verify_stage3b.py, test_runtime_verify_stage3cd.py, test_runtime_verify_stage3e.py, test_runtime_verify_stage6.py, test_runtime_verify_stage9.py, test_verify_v7.py هستند. همچنین فایل requirements.txt برای وابستگی‌ها و فایل docker-compose.yml برای محیط تست وجود دارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اجرای دستور pytest backend/tests/ -v --tb=short بدون خطا و با خروجی موفق
- [ ] هیچ تستی fail نشود و همه تست‌ها با وضعیت PASS یا OK به پایان برسند
- [ ] گزارش نهایی شامل تعداد تست‌های اجرا شده، تعداد تست‌های pass و fail باشد
- [ ] در صورت وجود خطا، خطاها مستند شده و رفع شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ابتدا اطمینان حاصل کنید که محیط مجازی فعال است و وابستگی‌ها نصب شده‌اند (pip install -r backend/requirements.txt). 2. سپس دستور pytest را از ریشه پروژه اجرا کنید: pytest backend/tests/ -v --tb=short. 3. خروجی را بررسی کنید تا هیچ تستی fail نشود. 4. اگر تستی fail شد، خطا را بررسی کرده و رفع کنید. 5. پس از رفع، دوباره pytest را اجرا کنید تا همه تست‌ها pass شوند. 6. در نهایت، گزارش نهایی را ثبت کنید.

## 💡 نمونه‌های قبل/بعد
**اجرای تست‌ها**

_قبل:_
```
pytest backend/tests/ -v --tb=short
```

_بعد:_
```
pytest backend/tests/ -v --tb=short (خروجی: همه تست‌ها pass)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -v --tb=short`
- `pytest backend/tests/ --coverage`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که تست‌ها ممکن است به سرویس‌های خارجی (مانند دیتابیس، APIهای خارجی) وابسته باشند که در محیط تست در دسترس نباشند. همچنین فایل‌های تست ممکن است نیاز به تنظیمات خاصی در docker-compose.yml داشته باشند. اگر تست‌ها fail شوند، باید خطاها بررسی و رفع شوند که ممکن است زمان‌بر باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 12: ایجاد commit با پیام واضح و merge-ready PR

**Scope:** این مرحله شامل ایجاد یک commit (یا چند commit متوالی) با پیام واضح که تغییرات را توضیح می‌دهد و شامل merged-from IDs است. همچنین ایجاد یک PR description با checklist از همه commitها. خارج از این مرحله: تغییر کد بیشتر. نکته حیاتی: commit message باید شامل merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad باشد.
**Key terms:** commit message, merged-from, 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad, PR description

**بخش مربوط از متن کاربر:**
```
در commit message: `merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad`

در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد commit با merged-from IDs و PR description checklist

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/inspector_agent.py` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اما با توجه به آخرین کامیت‌ها (7d341e3, bf98db1) که به inspector مربوط هستند، احتمالاً تغییرات در این فایل یا فایل‌های مرتبط با inspector انجام شده است.
- `backend/app/services/verify_runtime/iterative_orchestrator.py` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. با توجه به کامیت a612c86 که به render و update_service_settings اشاره دارد، ممکن است تغییرات در این فایل یا فایل‌های مرتبط با verify_runtime باشد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
(نامشخص)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/inspector_scan_bridge.py` — احتمالاً تحت تأثیر تغییرات inspector قرار گرفته است (مرتبط با کامیت‌های 7d341e3 و bf98db1)
- `backend/app/services/verify_runtime/render_autodetect.py` — احتمالاً تحت تأثیر تغییرات render و update_service_settings قرار گرفته است (مرتبط با کامیت a612c86)
- `backend/app/services/scan_v5/scan_bundle.py` — احتمالاً تحت تأثیر تغییرات timestamp scan و placeholder rule قرار گرفته است (مرتبط با کامیت cd39cc3)

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های کدی وابسته نیست، بلکه به فرآیند Git و GitHub وابسته است. با این حال، برای نوشتن commit message و PR description دقیق، باید از تغییرات واقعی کد (که در فایل‌هایی مانند inspector_agent.py، iterative_orchestrator.py، inspector_scan_bridge.py، render_autodetect.py، scan_bundle.py و غیره اعمال شده‌اند) مطلع بود. آخرین کامیت‌ها (677c46f, 7d341e3, 33a9e7c, bf98db1, 94e9306, a612c86, 9fca950, cd39cc3) نشان‌دهنده تغییرات در inspector، render، و scan هستند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست ایجاد یک commit (یا چند commit متوالی) با پیام واضح که تغییرات را توضیح می‌دهد و شامل merged-from IDs است. همچنین ایجاد یک PR description با checklist از همه commitها. خارج از این مرحله: تغییر کد بیشتر. نکته حیاتی: commit message باید شامل merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad باشد.

--- بخش مربوط از درخواست اصلی کاربر ---
در commit message: `merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad`

در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.

--- کلیدواژه‌ها ---
commit message, merged-from, 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad, PR description

این درخواست صرفاً مربوط به فرآیند Git و GitHub است و نیازی به تغییر کد ندارد. با توجه به deep context موجود، هیچ فایل کدی مستقیماً مرتبط نیست. اما برای اجرای این تسک، باید از ساختار پروژه (که شامل فایل‌های backend و frontend است) و آخرین کامیت‌ها (مانند 677c46f, 7d341e3, 33a9e7c, bf98db1, 94e9306, a612c86, 9fca950, cd39cc3) آگاه بود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] یک commit (یا چند commit متوالی) با پیام واضح ایجاد شده باشد که شامل merged-from IDs است.
- [ ] PR description شامل checklist از همه commitها باشد.
- [ ] هیچ تغییر کد اضافی خارج از این مرحله در commitها وجود نداشته باشد.
- [ ] PR در حالت merge-ready (غیر Draft) قرار داشته باشد.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ابتدا وضعیت فعلی شاخه (branch) را با `git status` و `git log --oneline -5` بررسی کنید.
2. اگر تغییرات کد (که خارج از این مرحله است) قبلاً stage شده‌اند، با `git add .` یا `git add <files>` آن‌ها را stage کنید.
3. یک commit با پیام واضح ایجاد کنید که شامل merged-from IDs باشد. مثال:
   `git commit -m "feat(scope): توضیح مختصر تغییرات
   
   merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad"`
4. اگر چند commit متوالی نیاز است، هر commit را جداگانه با پیام مناسب و merged-from IDs ایجاد کنید.
5. شاخه را به ریموت پوش کنید: `git push origin <branch-name>`
6. در GitHub، یک Pull Request ایجاد کنید. عنوان PR باید مشابه commit message باشد.
7. در PR description، یک checklist از همه commitها بنویسید. مثلاً:
   ```
   ## Commits
   - [ ] `abc1234` feat(scope): توضیح تغییر ۱
   - [ ] `def5678` fix(scope): توضیح تغییر ۲
   ```
8. اطمینان حاصل کنید که PR description شامل merged-from IDs نیز هست.
9. PR را به حالت merge-ready (غیر Draft) درآورید و منتظر تأیید باشید.

## 💡 نمونه‌های قبل/بعد
**نمونه commit message با merged-from IDs**

_قبل:_
```
git commit -m "fix some bugs"
```

_بعد:_
```
git commit -m "fix(inspector): رفع باگ‌های بنیادی در اسکن

merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad"
```

**نمونه PR description با checklist**

_قبل:_
```
## Description
برخی تغییرات اعمال شد.
```

_بعد:_
```
## Description
این PR شامل رفع باگ‌های inspector و بهبود render است.

## Commits
- [ ] `7d341e3` fix(inspector): اسکن موردی فقط در حد درخواست کاربر
- [ ] `bf98db1` fix(inspector): سه باگ بنیادی که باعث رفتار «گاو» شده بود
- [ ] `a612c86` fix(render): ابزار واقعی update_service_settings
- [ ] `cd39cc3` fix(inspector): قاعدهٔ صفر «placeholder = build pipeline» + timestamp scan

merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `git log --oneline -5`
- `git log --format="%B" -1 | grep -E "merged-from: [0-9a-f-]+(, [0-9a-f-]+)*"`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک خاصی برای کدبیس وجود ندارد، زیرا این تسک صرفاً به فرآیند Git و GitHub مربوط است و تغییری در کد ایجاد نمی‌کند. تنها ریسک احتمالی، فراموشی درج merged-from IDs در commit message یا عدم تطابق checklist با commitهای واقعی است.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: high
- تخمین زمان: small

---

## ✅ معیارهای پذیرش کلی (همهٔ مراحل)
- [ ] {'text': 'بررسی شود که در خط 353 فایل backend/app/api/routes/github_import.py یک bare except: pass وجود دارد یا خیر', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['except:\\s*pass', 'except:\\s*\\n\\s*pass'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'نوع exception\u200cهای محتمل در آن نقطه شناسایی و مستند شوند (حداقل ۳ نوع)', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['def import_github', 'def handle_import', 'requests\\.', 'httpx\\.'], 'files_hint': ['backend/app/api/routes/github_import.py', 'backend/app/services/github_import.py']}}
- [ ] {'text': 'تأیید شود که bare except: pass هیچ log یا raise یا fallback ندارد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['except:\\s*pass', 'except:\\s*\\n\\s*pass'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'گزارش نهایی شامل فهرست exception\u200cهای محتمل و تأیید خاموش بودن handler باشد', 'verify_method': 'manual_only', 'verify_plan': {'reason': 'subjective — نیاز به بررسی دستی و مستندسازی دارد'}}
- [ ] {'text': 'هیچ bare except (except:) در فایل backend/app/api/routes/github_import.py وجود نداشته باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['except\\s*:'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'هیچ except Exception بدون log در فایل backend/app/api/routes/github_import.py وجود نداشته باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['except\\s+Exception\\s*:'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'هر بلوک except در فایل backend/app/api/routes/github_import.py دارای logger.warning یا logger.error با context کامل باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['logger\\.(warning|error)\\(', 'logging\\.(warning|error)\\(', 'log\\.(warning|error)\\('], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'تعداد logger.warning/logger.error در فایل backend/app/api/routes/github_import.py حداقل به تعداد بلوک\u200cهای except باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['logger\\.(warning|error)\\'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'logger در ابتدای فایل backend/app/api/routes/github_import.py به درستی import شده باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['from app.core.logging_utils import logger', 'import logging', 'logger = logging.getLogger'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'تست unit test_silent_failure_edge_case در tests/test_github_import.py وجود داشته باشد و با pytest کار کند.', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'tests/test_github_import.py::test_silent_failure_edge_case', 'timeout_seconds': 60}}
- [ ] {'text': 'تست یک سناریوی خطا را شبیه\u200cسازی کند (مثلاً URL نامعتبر) و بررسی کند که exception به درستی catch و log شده است.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['def test_silent_failure_edge_case', 'pytest.raises', 'mock_handle.assert_called_once'], 'files_hint': ['backend/tests/test_github_import.py']}}
- [ ] {'text': 'تست edge case شکست\u200cخورده را پوشش دهد که قبلاً باعث silent failure می\u200cشد.', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['silent failure', 'edge case', 'import_repository'], 'files_hint': ['backend/tests/test_github_import.py']}}
- [ ] {'text': 'تست با pytest کار کند و بدون خطا اجرا شود.', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'tests/test_github_import.py::test_silent_failure_edge_case', 'timeout_seconds': 60}}
- [ ] {'text': 'خط 353 در backend/app/api/routes/github_import.py بررسی شده و مشخص شده که failure قابل recovery است یا خیر', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['353', 'github_import'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'اگر failure قابل recovery است، یک fallback mechanism (retry یا alternative path) در کد یا کامنت مستند شده است', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['fallback', 'recover', 'retry', 'alternative'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'مستندسازی شامل توضیح دلیل recoverable بودن یا نبودن failure است', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['recoverable', 'recovery', 'fallback'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'هیچ تغییری در exception handling یا log اصلی کد ایجاد نشده است (فقط مستندسازی)', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['except', 'logger', 'logging'], 'files_hint': ['backend/app/api/routes/github_import.py']}}
- [ ] {'text': 'تمامی callerهای تابع حاوی خط 353 در backend/app/api/routes/github_import.py شناسایی و مستند شوند', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['def function_name_at_line_353', 'caller_function_name'], 'files_hint': ['backend/app/api/routes/github_import.py', 'backend/app/services/github_import.py']}}
- [ ] {'text': 'برای هر caller، وابستگی به return value تابع بررسی شود و در صورت نیاز اصلاح گردد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['result = ', 'return_value = ', 'if result'], 'files_hint': ['backend/app/api/routes/github_import.py', 'backend/app/services/github_import.py']}}
- [ ] {'text': 'هیچ caller بعد از تغییر، break نشود (همه routeهای مرتبط با import از GitHub کار کنند)', 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/github/import', 'expected_status': 200, 'required_fields': ['status']}}

## Acceptance Criteria

1. بررسی شود که در خط 353 فایل backend/app/api/routes/github_import.py یک bare except: pass وجود دارد یا خیر _(verify: static)_
2. نوع exception‌های محتمل در آن نقطه شناسایی و مستند شوند (حداقل ۳ نوع) _(verify: static)_
3. تأیید شود که bare except: pass هیچ log یا raise یا fallback ندارد _(verify: static)_
4. گزارش نهایی شامل فهرست exception‌های محتمل و تأیید خاموش بودن handler باشد _(verify: manual_only)_
5. هیچ bare except (except:) در فایل backend/app/api/routes/github_import.py وجود نداشته باشد _(verify: static)_
6. هیچ except Exception بدون log در فایل backend/app/api/routes/github_import.py وجود نداشته باشد _(verify: static)_
7. هر بلوک except در فایل backend/app/api/routes/github_import.py دارای logger.warning یا logger.error با context کامل باشد _(verify: static)_
8. تعداد logger.warning/logger.error در فایل backend/app/api/routes/github_import.py حداقل به تعداد بلوک‌های except باشد _(verify: static)_
9. logger در ابتدای فایل backend/app/api/routes/github_import.py به درستی import شده باشد _(verify: static)_
10. تست unit test_silent_failure_edge_case در tests/test_github_import.py وجود داشته باشد و با pytest کار کند. _(verify: backend_test)_
11. تست یک سناریوی خطا را شبیه‌سازی کند (مثلاً URL نامعتبر) و بررسی کند که exception به درستی catch و log شده است. _(verify: static)_
12. تست edge case شکست‌خورده را پوشش دهد که قبلاً باعث silent failure می‌شد. _(verify: static)_
13. تست با pytest کار کند و بدون خطا اجرا شود. _(verify: backend_test)_
14. خط 353 در backend/app/api/routes/github_import.py بررسی شده و مشخص شده که failure قابل recovery است یا خیر _(verify: static)_
15. اگر failure قابل recovery است، یک fallback mechanism (retry یا alternative path) در کد یا کامنت مستند شده است _(verify: static)_
16. مستندسازی شامل توضیح دلیل recoverable بودن یا نبودن failure است _(verify: static)_
17. هیچ تغییری در exception handling یا log اصلی کد ایجاد نشده است (فقط مستندسازی) _(verify: static)_
18. تمامی callerهای تابع حاوی خط 353 در backend/app/api/routes/github_import.py شناسایی و مستند شوند _(verify: static)_
19. برای هر caller، وابستگی به return value تابع بررسی شود و در صورت نیاز اصلاح گردد _(verify: static)_
20. هیچ caller بعد از تغییر، break نشود (همه routeهای مرتبط با import از GitHub کار کنند) _(verify: api_response)_
21. تغییر silent failure به raise باعث لاگ مناسب خطا شود (بدون break در callerهایی که خطا را مدیریت نمی‌کنند) _(verify: static)_
22. دستور python -m py_compile backend/app/api/routes/github_import.py بدون error اجرا شود. _(verify: static)_
23. دستور ruff check backend/app/api/routes/github_import.py بدون warning یا error اجرا شود. _(verify: static)_
24. دستور mypy backend/app/api/routes/github_import.py بدون warning یا error اجرا شود. _(verify: static)_
25. هیچ تغییری در logic فایل github_import.py ایجاد نشود و فقط lint/type issues رفع شده باشند. _(verify: static)_
26. خطا در auto_setup_project_memory باعث 500 نشود و پروژه با وضعیت partial setup ذخیره شود _(verify: static)_
27. لاگ خطا در صورت failure auto_setup_project_memory ثبت شود _(verify: static)_
28. پروژه import شده حتی اگر auto_setup شکست بخورد، در دیتابیس باقی بماند _(verify: static)_
29. مستندسازی تحلیل در یک فایل جداگانه ذخیره شود _(verify: static)_
30. تابع import_repository در github_import.py باید خطاهای auto_setup_project_memory را با logging.error log کند. _(verify: static)_
31. در صورت خطا در auto_setup_project_memory، فرآیند import باید ادامه یابد (بدون raise exception). _(verify: static)_
32. تغییرات نباید تست‌های موجود را بشکند (pytest backend/tests/ باید پاس شود). _(verify: backend_test)_
33. هیچ فایل دیگری غیر از github_import.py تغییر نکند. _(verify: static)_
34. تست unit جدید در tests/test_github_import.py با نام test_import_repository_auto_setup_memory_fallback ایجاد شود که سناریوی failure auto_setup_project_memory را پوشش دهد. _(verify: static)_
35. تست از pytest monkeypatch یا unittest.mock برای شبیه‌سازی failure auto_setup_project_memory استفاده کند. _(verify: static)_
36. تست بررسی کند که import_repository با خطا مواجه نمی‌شود (بدون raise exception) و fallback به درستی کار می‌کند. _(verify: static)_
37. اجرای pytest backend/tests/test_github_import.py بدون شکستن تست‌های موجود (همه تست‌ها پاس شوند). _(verify: backend_test)_
38. linter (ruff) روی کل پوشه backend بدون warning عبور کند _(verify: static)_
39. type-check (mypy) روی کل پوشه backend بدون warning عبور کند _(verify: static)_
40. هیچ error یا warning جدیدی در خروجی lint/type-check وجود نداشته باشد _(verify: static)_
41. فایل backend/requirements.txt شامل ruff و mypy باشد _(verify: static)_
42. اجرای دستور pytest backend/tests/ -v --tb=short بدون خطا و با خروجی موفق _(verify: backend_test)_
43. هیچ تستی fail نشود و همه تست‌ها با وضعیت PASS یا OK به پایان برسند _(verify: backend_test)_
44. گزارش نهایی شامل تعداد تست‌های اجرا شده، تعداد تست‌های pass و fail باشد _(verify: static)_
45. در صورت وجود خطا، خطاها مستند شده و رفع شوند _(verify: manual_only)_
46. یک commit (یا چند commit متوالی) با پیام واضح ایجاد شده باشد که شامل merged-from IDs است. _(verify: static)_
47. PR description شامل checklist از همه commitها باشد. _(verify: manual_only)_
48. هیچ تغییر کد اضافی خارج از این مرحله در commitها وجود نداشته باشد. _(verify: static)_
49. PR در حالت merge-ready (غیر Draft) قرار داشته باشد. _(verify: manual_only)_

## Task Steps

### Step 1: بررسی و شناسایی exception handler خاموش در github_import.py خط 353
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py در خط 353 برای یافتن bare except: pass یا catch بدون log است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: قبل از هر تغییری، باید دقیقاً مشخص شود که چه نوع exception ای در این نقطه ممکن است رخ دهد و آیا این handler واقعاً خاموش است یا خیر.
**Excerpt:**
```
در `backend/app/api/routes/github_import.py` (line 353) یک exception handler خاموش (مثل `except: pass`) در مسیر اصلی کد پیدا شد.

## 🔍 جزئیات
- علت: bare 'except: pass' — هیچ‌چیز handle یا log نمی‌شود
```

### Step 2: تبدیل bare except به exception specific با log مناسب در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر کد در backend/app/api/routes/github_import.py برای جایگزینی bare except: pass با catch exception خاص (مثلاً ValueError, KeyError, یا Exception) و افزودن log با level warning/error و context کامل است. خارج از این مرحله: نوشتن تست، بررسی fallback، یا تغییر سایر فایل‌ها. نکته حیاتی: باید از bare except (except:) و except Exception: بدون log اجتناب شود.
**Excerpt:**
```
- [ ] نوع exception specific شده (نه bare except/catch) [verify_method=static] [verify_plan={"grep_patterns": ["except\\s*:", "except\\s+Exception\\s*:", "except\\s+[A-Za-z]+\\s+as\\s+\\w+\\s*:"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
- [ ] log با level مناسب (warning/error) + context کامل اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["logger\\.(warning|error)\\", "logging\\.(warning|error)\\", "log\\.(warning|error)\\"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
```

### Step 3: نوشتن تست unit برای edge case شکست‌خورده در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن یک تست unit در tests/test_github_import.py برای edge case ای است که قبلاً باعث silent failure می‌شد. تست باید یک سناریوی خطا را شبیه‌سازی کند و بررسی کند که exception به درستی catch و log شده است. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration، یا تست‌های دیگر. نکته حیاتی: تست باید با pytest کار کند و edge case شکست‌خورده را پوشش دهد.
**Excerpt:**
```
- [ ] تست unit برای edge case شکست‌خورده عبور می‌کند [verify_method=backend_test] [verify_plan={"test_node": "tests/test_github_import.py::test_silent_failure_edge_case", "timeout_seconds": 60}]
```

### Step 4: بررسی و مستندسازی fallback برای failure قابل recovery در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی این است که آیا failure در خط 353 قابل recovery است یا خیر. اگر قابل recovery است، باید یک fallback mechanism (مثل retry, alternative path) مستند یا پیاده‌سازی شود. خارج از این مرحله: تغییر کد اصلی برای exception handling یا log. نکته حیاتی: fallback باید در کد یا کامنت مستند شود.
**Excerpt:**
```
- [ ] اگر failure قابل recovery است، fallback مستند شده [verify_method=static] [verify_plan={"grep_patterns": ["fallback", "recover", "retry", "alternative"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
```

### Step 5: بررسی caller upstream برای عدم break در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی callerهای upstream تابع حاوی خط 353 در backend/app/api/routes/github_import.py است تا اطمینان حاصل شود که تغییر silent failure به raise یا log باعث break نمی‌شود. خارج از این مرحله: تغییر کد در callerها. نکته حیاتی: اگر caller فرض می‌کند تابع همیشه return می‌کند، باید آن را اصلاح کرد.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر silent failure به raise ممکن است upstream caller را break کند که فرض می‌کرده این تابع همیشه return می‌کند. caller را هم چک کن.
```

### Step 6: اجرای linter و type-check برای github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای linter (ruff) و type-check (mypy) روی فایل backend/app/api/routes/github_import.py برای اطمینان از عدم وجود warning یا error است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.
**Excerpt:**
```
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
```

### Step 7: بررسی و شناسایی عدم مدیریت خطا در auto_setup_project_memory در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کد موجود در backend/app/api/routes/github_import.py، به ویژه تابع import_repository (خطوط 132-157) و نحوه استفاده از auto_setup_project_memory است. هدف شناسایی try/except موجود و بررسی کافی بودن آن است. خارج از این مرحله: تغییر کد، نوشتن تست، یا بررسی سایر فایل‌ها. نکته حیاتی: باید مشخص شود که آیا خطا در auto_setup_project_memory باعث 500 می‌شود و پروژه بدون setup می‌ماند.
**Excerpt:**
```
در `backend/app/api/routes/github_import.py`، تابع `import_repository` (خط 132-157) از `auto_setup_project_memory` استفاده می‌کند. اگر این تابع خطا بدهد، کل درخواست import با خطای 500 مواجه می‌شود و پروژه import شده اما بدون setup باقی می‌ماند. در حال حاضر یک try/except وجود دارد که خطا را در `result["auto_setup"]` ذخیره می‌کند، اما این کافی
```

### Step 8: بهبود مدیریت خطا برای auto_setup_project_memory در import_repository
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بهبود try/except موجود در تابع import_repository در backend/app/api/routes/github_import.py برای auto_setup_project_memory است. باید خطا را به درستی log کند و fallback مناسب (مثل ادامه بدون setup) فراهم کند. خارج از این مرحله: نوشتن تست، تغییر سایر فایل‌ها. نکته حیاتی: تغییر نباید تست‌های موجود را بشکند.
**Excerpt:**
```
## 🎯 هدف (خلاصه ساختاریافته)
عدم مدیریت خطا در GitHub Import برای auto_setup_project_memory

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)
```

### Step 9: نوشتن تست برای edge case auto_setup_project_memory failure
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن یک تست unit در tests/test_github_import.py برای سناریوی failure در auto_setup_project_memory است. تست باید بررسی کند که import_repository با خطا مواجه نمی‌شود و fallback به درستی کار می‌کند. خارج از این مرحله: تغییر کد اصلی، نوشتن تست‌های integration. نکته حیاتی: تست باید با pytest کار کند و edge case را پوشش دهد.
**Excerpt:**
```
- [ ] اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
```

### Step 10: اجرای linter و type-check برای کل backend پس از تغییرات
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای linter (ruff) و type-check (mypy) روی کل پوشه backend برای اطمینان از عدم وجود warning یا error پس از تغییرات است. خارج از این مرحله: تغییر کد برای رفع lint/type errors. نکته حیاتی: lint و type-check باید بدون warning عبور کنند.
**Excerpt:**
```
- [ ] linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
- [ ] type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "type: ignore", "type-check"], "files_hint": ["backend/"]}]
```

### Step 11: اجرای تمام تست‌های backend برای اطمینان از عدم رگرشن
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های backend با pytest برای اطمینان از اینکه تغییرات باعث شکستن تست‌های موجود نمی‌شود. خارج از این مرحله: تغییر کد، اجرای تست‌های frontend. نکته حیاتی: هیچ تستی نباید fail شود.
**Excerpt:**
```
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)

## 🧪 دستورات اعتبارسنجی
- `pytest`
```

### Step 12: ایجاد commit با پیام واضح و merge-ready PR
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک commit (یا چند commit متوالی) با پیام واضح که تغییرات را توضیح می‌دهد و شامل merged-from IDs است. همچنین ایجاد یک PR description با checklist از همه commitها. خارج از این مرحله: تغییر کد بیشتر. نکته حیاتی: commit message باید شامل merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad باشد.
**Excerpt:**
```
در commit message: `merged-from: 95e241b7-5809-4df2-9733-613094cf56b3, 58f05dc2-4934-4be7-ae07-6175eda2a0ad`

در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.
```
