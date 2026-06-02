---
task_id: b501fec9-c7fe-4875-b5db-16c63cb22cac
title: '[منطق] عدم تطابق schema در state machine oversight_upload_session.py'
type: logic_audit
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-17T07:13:43.266989+00:00'
updated_at: '2026-06-02T17:51:37.091668+00:00'
---

# [منطق] عدم تطابق schema در state machine oversight_upload_session.py

## Raw Idea

## 📋 شرح ناسازگاری
در pipeline `data` یک ناسازگاری منطقی پیدا شد:

state machine به صورت `pending→uploading→completed→extracting→extracted/failed` تعریف شده است، اما در expected_outputs اشاره‌ای به state `failed` در مسیر نهایی نشده است (فقط extracted/fail ذکر شده). همچنین transition از `completed` به `extracting` نیاز به trigger مشخصی دارد که در مستندات نیست.

## 💥 پیامد (impact)
اگر state machine دقیق پیاده‌سازی نشود، session ممکن است در state نامعتبر گیر کند و garbage collection یا cleanup انجام نشود.

## 🛠 پیشنهاد رفع اولیه
state machine را به صورت کامل با تمام transitions (از جمله failed از هر state) مستند کنید و در کد enforce کنید.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.
---
[scan #2 at 2026-05-17T08:38:39.570465+00:00]
## 📋 شرح ناسازگاری
در pipeline `data` یک ناسازگاری منطقی پیدا شد:

در بخش purpose، state machine به صورت 'pending → uploading → completed → extracting → extrac' تعریف شده است که ناقص است (آخرین state 'extrac' بریده شده). همچنین در expected_outputs به state 'extracting' اشاره شده اما در purpose به 'e
---
[scan #3 at 2026-05-17T08:43:29.720349+00:00]
## 📋 شرح ناسازگاری
در pipeline `auth` یک ناسازگاری منطقی پیدا شد:

سرویس upload_session دارای state machine (pending → uploading → completed → extracting → ...) است، اما مدل inspector_session هیچ فیلدی برای tracking وضعیت آپلود ندارد. این دو کامپوننت به‌طور مجزا کار می‌کنند و coherence ندارند.

## 💥

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
[منطق] عدم تطابق schema در state machine oversight_upload_session.py

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در pipeline data است — همه فایل‌های این pipeline مرتبط هستند.

## 🔍 Context و وضعیت فعلی
## 📋 شرح ناسازگاری
در pipeline `data` یک ناسازگاری منطقی پیدا شد:

state machine به صورت `pending→uploading→completed→extracting→extracted/failed` تعریف شده است، اما در expected_outputs اشاره‌ای به state `failed` در مسیر نهایی نشده است (فقط extracted/fail ذکر شده). همچنین transition از `completed` به `extracting` نیاز به trigger مشخصی دارد که در مستندات نیست.

## 💥 پیامد (impact)
اگر state machine دقیق پیاده‌سازی نشود، session ممکن است در state نامعتبر گیر کند و garbage collection یا cleanup انجام نشود.

## 🛠 پیشنهاد رفع اولیه
state machine را به صورت کامل با تمام transitions (از جمله failed از هر state) مستند کنید و در کد enforce کنید.

## 🤔 چرا مهم است
coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی refactor ناتمام یا feature flag rot است. این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد
- [ ] ground truth تعیین شد و طرف دیگر align شد
- [ ] integration test برای pipeline `data` بدون شکست عبور می‌کند
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

## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
3. integration test برای pipeline `data` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: شناسایی و مستندسازی کامل state machine فعلی در pipeline data
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل جستجو و شناسایی تمام فایل‌های مرتبط با state machine در pipeline data (به خصوص oversight_upload_session.py و فایل‌های مشابه) است. باید تمام states موجود (pending, uploading, completed, extracting, extracted, failed) و transitions بین آن‌ها از کد استخراج شود. همچنین باید مستندات موجود (docstrings, README, diagrams) بررسی شوند تا مشخص شود چه چیزی مستند شده و چه چیزی نه. خروجی این مرحله یک مستند کامل از state machine فعلی است. خارج از این مرحله: تغییر کد، اصلاح transitions، یا نوشتن تست.
**Excerpt:**
```
در pipeline `data` یک ناسازگاری منطقی پیدا شد: state machine به صورت `pending→uploading→completed→extracting→extracted/failed` تعریف شده است، اما در expected_outputs اشاره‌ای به state `failed` در مسیر نهایی نشده است (فقط extracted/fail ذکر شده). همچنین transition از `completed` به `extracting` نیاز به trigger مشخصی دارد که در مستندات نیست.
```

### Step 2: مستندسازی فرضیات ناسازگار دو بخش کد
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل تحلیل و مستندسازی دقیق دو فرض متفاوت است: (1) فرض state machine که failed را به عنوان state مجزا در مسیر نهایی دارد، و (2) فرض expected_outputs که فقط extracted/fail را ذکر کرده. باید مشخص شود کدام فایل‌ها/ماژول‌ها هر فرض را دارند و conflict دقیقاً کجاست. خروجی: یک گزارش conflict. خارج از این مرحله: تصمیم‌گیری درباره اینکه کدام فرض درست است.
**Excerpt:**
```
state machine به صورت `pending→uploading→completed→extracting→extracted/failed` تعریف شده است، اما در expected_outputs اشاره‌ای به state `failed` در مسیر نهایی نشده است (فقط extracted/fail ذکر شده).
```

### Step 3: تعریف state machine کامل با تمام transitions (شامل failed از هر state)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل طراحی و مستندسازی یک state machine کامل و سازگار است. باید تمام states معتبر (pending, uploading, completed, extracting, extracted, failed) و تمام transitions مجاز بین آن‌ها تعریف شود. به خصوص باید مشخص شود: (1) از کدام states می‌توان به failed رفت، (2) transition از completed به extracting چه triggerی دارد، (3) آیا extracted می‌تواند به failed برود یا نه. خروجی: یک state machine diagram (به صورت متن یا mermaid) و توضیحات transitions. خارج از این مرحله: پیاده‌سازی در کد.
**Excerpt:**
```
transition از `completed` به `extracting` نیاز به trigger مشخصی دارد که در مستندات نیست. state machine را به صورت کامل با تمام transitions (از جمله failed از هر state) مستند کنید و در کد enforce کنید.
```

### Step 4: به‌روزرسانی expected_outputs برای انعکاس state failed در مسیر نهایی
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اصلاح expected_outputs (احتمالاً در فایل‌های تست یا مستندات) است تا state failed را به عنوان یک state مجزا و معتبر در مسیر نهایی session بشناسد. باید مشخص شود expected_outputs در کدام فایل‌ها/ماژول‌ها تعریف شده و چگونه باید اصلاح شود. خارج از این مرحله: تغییر state machine یا transitions.
**Excerpt:**
```
در expected_outputs اشاره‌ای به state `failed` در مسیر نهایی نشده است (فقط extracted/fail ذکر شده).
```

### Step 5: اضافه کردن trigger مشخص برای transition از completed به extracting در مستندات
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل تعریف و مستندسازی trigger دقیق برای transition از state completed به extracting است. باید مشخص شود چه رویداد/شرطی (مثلاً فراخوانی API، timeout، callback) باعث این transition می‌شود. trigger باید در مستندات state machine و در صورت لزوم در کد (به صورت comment یا docstring) ثبت شود. خارج از این مرحله: پیاده‌سازی trigger در کد.
**Excerpt:**
```
transition از `completed` به `extracting` نیاز به trigger مشخصی دارد که در مستندات نیست.
```

### Step 6: پیاده‌سازی enforce state machine در کد با تمام transitions (شامل failed از هر state)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل پیاده‌سازی state machine کامل در کد است. باید یک مکانیزم (مثلاً enum برای states، validation برای transitions، decorator یا middleware) ایجاد شود که transitions نامعتبر را رد کند. باید تمام transitions تعریف شده در مرحله 3 پیاده‌سازی شوند، به خصوص: (1) امکان رفتن به failed از هر state، (2) trigger برای completed→extracting. خارج از این مرحله: تست‌های unit یا integration.
**Excerpt:**
```
state machine را به صورت کامل با تمام transitions (از جمله failed از هر state) مستند کنید و در کد enforce کنید.
```

### Step 7: نوشتن تست‌های unit برای state machine transitions
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های unit برای تمام transitions state machine است. تست‌ها باید موارد زیر را پوشش دهند: (1) transitions مجاز (مثلاً pending→uploading, completed→extracting), (2) transitions نامعتبر (مثلاً pending→extracted), (3) رفتن به failed از هر state, (4) trigger برای completed→extracting. تست‌ها باید در فایل تست مربوطه (مثلاً test_state_machine.py) نوشته شوند. خارج از این مرحله: تست‌های integration یا end-to-end.
**Excerpt:**
```
اگر state machine دقیق پیاده‌سازی نشود، session ممکن است در state نامعتبر گیر کند و garbage collection یا cleanup انجام نشود.
```

### Step 8: نوشتن تست‌های integration برای سناریوی کامل session lifecycle
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های integration است که یک session کامل را از state pending تا extracted یا failed شبیه‌سازی می‌کند. تست باید transitions واقعی را از طریق API یا فراخوانی توابع اصلی آزمایش کند. باید موارد زیر پوشش داده شود: (1) مسیر موفق (pending→uploading→completed→extracting→extracted), (2) مسیر failed در مراحل مختلف (مثلاً failed از uploading, failed از extracting). خارج از این مرحله: تست‌های unit یا end-to-end با UI.
**Excerpt:**
```
اگر state machine دقیق پیاده‌سازی نشود، session ممکن است در state نامعتبر گیر کند و garbage collection یا cleanup انجام نشود.
```

### Step 9: بررسی و اصلاح garbage collection و cleanup برای state‌های نامعتبر
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل بررسی مکانیزم‌های garbage collection و cleanup موجود در pipeline data است. باید مشخص شود: (1) آیا مکانیزمی برای پاکسازی session‌های گیر کرده در state نامعتبر وجود دارد، (2) آیا cleanup برای state failed به درستی پیاده‌سازی شده است، (3) آیا timeout mechanism برای transitions وجود دارد. در صورت نیاز، کد cleanup اصلاح شود. خارج از این مرحله: تغییر state machine یا transitions.
**Excerpt:**
```
اگر state machine دقیق پیاده‌سازی نشود، session ممکن است در state نامعتبر گیر کند و garbage collection یا cleanup انجام نشود.
```

### Step 10: به‌روزرسانی مستندات کلی pipeline data با state machine جدید
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل به‌روزرسانی تمام مستندات مرتبط با pipeline data (README، docs، diagrams) با state machine جدید و کامل است. باید diagram جدید، جدول transitions، و توضیحات triggerها اضافه شود. همچنین باید اشاره‌ای به مکانیزم enforce و cleanup شود. خارج از این مرحله: تغییر کد یا تست‌ها.
**Excerpt:**
```
state machine را به صورت کامل با تمام transitions (از جمله failed از هر state) مستند کنید و در کد enforce کنید.
```
