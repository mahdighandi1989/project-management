---
task_id: 484e1daf-d8c0-4e7b-87c2-d62322b7ecce
title: '[منطق] عدم هماهنگی بین ModelCapability در ai_manager.py و system_prompt.py'
type: logic_audit
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T19:20:35.642820+00:00'
updated_at: '2026-06-03T18:15:12.433706+00:00'
---

# [منطق] عدم هماهنگی بین ModelCapability در ai_manager.py و system_prompt.py

## Raw Idea

## 📋 شرح ناسازگاری
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

ai_manager.py از ModelCapability برای فیلتر مدل‌ها استفاده می‌کند اما system_prompt.py هیچ اشاره‌ای به capability مورد نیاز برای پرامپت‌های مختلف ندارد. مثلاً پرامپت deep_analysis ممکن است نیاز به مدلی با context window بزرگ داشته باشد.

## 💥 پیامد (impact)
مدل‌های نامناسب ممکن است برای پرامپت‌های خاص انتخاب شوند و باعث خطا یا خروجی بی‌کیفیت شوند

## 🛠 پیشنهاد رفع اولیه
اضافه کردن فیلد required_capabilities به مدل system_prompt و تطبیق آن با ModelCapability در ai_manager.py هنگام انتخاب مدل.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

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
[منطق] عدم هماهنگی بین ModelCapability در ai_manager.py و system_prompt.py

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

ai_manager.py از ModelCapability برای فیلتر مدل‌ها استفاده می‌کند اما system_prompt.py هیچ اشاره‌ای به capability مورد نیاز برای پرامپت‌های مختلف ندارد. مثلاً پرامپت deep_analysis ممکن است نیاز به مدلی با context window بزرگ داشته باشد.

## 💥 پیامد (impact)
مدل‌های نامناسب ممکن است برای پرامپت‌های خاص انتخاب شوند و باعث خطا یا خروجی بی‌کیفیت شوند

## 🛠 پیشنهاد رفع اولیه
اضافه کردن فیلد required_capabilities به مدل system_prompt و تطبیق آن با ModelCapability در ai_manager.py هنگام انتخاب مدل.

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

## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
3. integration test برای pipeline `ai_llm` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: بررسی و مستندسازی ناسازگاری بین ModelCapability در ai_manager.py و system_prompt.py
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل جستجو و شناسایی دقیق فایل‌های ai_manager.py و system_prompt.py در pipeline ai_llm است. باید مشخص شود که ModelCapability چگونه در ai_manager.py تعریف و استفاده می‌شود و system_prompt.py چه ساختاری دارد و آیا فیلد capabilities یا required_capabilities در آن وجود دارد یا خیر. همچنین باید فرضیات هر دو طرف (مثلاً اینکه ai_manager.py فرض می‌کند system_prompt.py capability دارد) مستند شود. خروجی این مرحله یک گزارش متنی از وضعیت فعلی است. خارج از این مرحله: هیچ تغییری در کد ایجاد نمی‌شود.
**Excerpt:**
```
در pipeline `ai_llm` یک ناسازگاری منطقی پیدا شد:

ai_manager.py از ModelCapability برای فیلتر مدل‌ها استفاده می‌کند اما system_prompt.py هیچ اشاره‌ای به capability مورد نیاز برای پرامپت‌های مختلف ندارد. مثلاً پرامپت deep_analysis ممکن است نیاز به مدلی با context window بزرگ داشته باشد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
```

### Step 2: اضافه کردن فیلد required_capabilities به مدل system_prompt در system_prompt.py
**Status:** `not_done` (0%)
**Scope:** در این مرحله، فیلد required_capabilities از نوع List[ModelCapability] (یا معادل آن) به کلاس/مدل system_prompt در فایل system_prompt.py اضافه می‌شود. این فیلد مشخص می‌کند که هر پرامپت (مثلاً deep_analysis) به چه قابلیت‌هایی از مدل نیاز دارد. باید اطمینان حاصل شود که این فیلد اختیاری است (Optional) تا پرامپت‌های قدیمی بدون این فیلد هم کار کنند. خارج از این مرحله: تغییر در ai_manager.py یا منطق انتخاب مدل انجام نمی‌شود.
**Excerpt:**
```
اضافه کردن فیلد required_capabilities به مدل system_prompt و تطبیق آن با ModelCapability در ai_manager.py هنگام انتخاب مدل.

مثلاً پرامپت deep_analysis ممکن است نیاز به مدلی با context window بزرگ داشته باشد.
```

### Step 3: به‌روزرسانی پرامپت deep_analysis برای تنظیم required_capabilities
**Status:** `not_done` (0%)
**Scope:** در این مرحله، پرامپت deep_analysis (و سایر پرامپت‌های موجود در system_prompt.py که نیاز به capability خاصی دارند) به‌روزرسانی می‌شوند تا فیلد required_capabilities را با مقادیر مناسب (مثلاً ModelCapability.LARGE_CONTEXT_WINDOW) مقداردهی کنند. باید مشخص شود که deep_analysis به چه capability نیاز دارد (مثلاً context window بزرگ). خارج از این مرحله: پرامپت‌های جدید ایجاد نمی‌شوند.
**Excerpt:**
```
مثلاً پرامپت deep_analysis ممکن است نیاز به مدلی با context window بزرگ داشته باشد.
```

### Step 4: تطبیق منطق انتخاب مدل در ai_manager.py با required_capabilities
**Status:** `not_done` (0%)
**Scope:** در این مرحله، تابع یا منطقی در ai_manager.py که مدل را بر اساس ModelCapability فیلتر می‌کند، به‌روزرسانی می‌شود تا هنگام انتخاب مدل برای یک پرامپت، required_capabilities آن پرامپت را نیز در نظر بگیرد. یعنی اگر پرامپتی required_capabilities داشته باشد، فقط مدل‌هایی که آن capabilities را دارند انتخاب شوند. اگر required_capabilities خالی یا None باشد، رفتار قبلی (فیلتر بر اساس capabilities موجود) حفظ شود. خارج از این مرحله: تغییر در system_prompt.py انجام نمی‌شود.
**Excerpt:**
```
اضافه کردن فیلد required_capabilities به مدل system_prompt و تطبیق آن با ModelCapability در ai_manager.py هنگام انتخاب مدل.
```

### Step 5: نوشتن integration test برای pipeline انتخاب مدل با required_capabilities
**Status:** `not_done` (0%)
**Scope:** در این مرحله، یک integration test نوشته می‌شود که سناریوی کامل را تست کند: یک پرامپت با required_capabilities تعریف می‌شود، و سپس ai_manager.py مدل مناسب را انتخاب می‌کند. تست باید بررسی کند که مدل انتخاب‌شده دارای capabilities مورد نیاز است. همچنین سناریوی بدون required_capabilities (رفتار قبلی) نیز تست شود. خارج از این مرحله: unit test برای تک تک توابع نوشته نمی‌شود.
**Excerpt:**
```
integration test برای pipeline ai_llm

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
- [ ] integration test برای pipeline
```
