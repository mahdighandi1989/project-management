---
task_id: eb08817e-88b6-444a-8dc3-4a8a6ef8bffc
title: '[منطق] عدم وجود endpoint برای احراز هویت'
type: logic_audit
priority: critical
execution_priority: 1000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T16:41:11.739570+00:00'
updated_at: '2026-06-02T17:47:47.259901+00:00'
---

# [منطق] عدم وجود endpoint برای احراز هویت

## Raw Idea

## 📋 شرح ناسازگاری
در pipeline `auth` یک ناسازگاری منطقی پیدا شد:

در توضیحات هیچ endpoint یا سرویسی برای login/register/token generation ذکر نشده است. pipeline auth بدون این موارد نمی‌تواند کاربران را احراز هویت کند.

## 💥 پیامد (impact)
کاربران نمی‌توانند وارد سیستم شوند. هیچ توکن یا session ای برای authentication وجود ندارد.

## 🛠 پیشنهاد رفع اولیه
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید. همچنین middleware برای اعتبارسنجی token در هر درخواست.

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
[منطق] عدم وجود endpoint برای احراز هویت

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

در توضیحات هیچ endpoint یا سرویسی برای login/register/token generation ذکر نشده است. pipeline auth بدون این موارد نمی‌تواند کاربران را احراز هویت کند.

## 💥 پیامد (impact)
کاربران نمی‌توانند وارد سیستم شوند. هیچ توکن یا session ای برای authentication وجود ندارد.

## 🛠 پیشنهاد رفع اولیه
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید. همچنین middleware برای اعتبارسنجی token در هر درخواست.

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

## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: manual_only)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: manual_only)_
3. integration test برای pipeline `auth` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: بررسی و مستندسازی وضعیت فعلی pipeline auth
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل جستجوی کامل در repo برای یافتن تمام فایل‌ها، endpointها، middlewareها و سرویس‌های مرتبط با pipeline auth است. باید مشخص شود چه چیزی از قبل وجود دارد (login, register, token generation, token validation middleware) و چه چیزی وجود ندارد. خروجی این مرحله یک مستند (فایل MARKDOWN یا کامیت) است که وضعیت فعلی را شرح می‌دهد. خارج از این مرحله: ایجاد endpoint جدید، تغییر کد موجود.
**Excerpt:**
```
در pipeline `auth` یک ناسازگاری منطقی پیدا شد: در توضیحات هیچ endpoint یا سرویسی برای login/register/token generation ذکر نشده است. pipeline auth بدون این موارد نمی‌تواند کاربران را احراز هویت کند. ... پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**. اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
```

### Step 2: طراحی و مستندسازی مدل داده کاربر (User model)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل طراحی مدل داده‌ای برای کاربران شامل فیلدهای ضروری (username, email, hashed_password, is_active, created_at) و انتخاب روش ذخیره‌سازی (مثلاً دیتابیس یا فایل) است. باید با معماری موجود (FastAPI, Next.js) هماهنگ باشد. خارج از این مرحله: پیاده‌سازی endpointها، پیاده‌سازی middleware.
**Excerpt:**
```
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید. همچنین middleware برای اعتبارسنجی token در هر درخواست.
```

### Step 3: پیاده‌سازی سرویس هش کردن رمز عبور (Password hashing service)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک سرویس (یا تابع) برای هش کردن امن رمز عبور با استفاده از کتابخانه‌ای مانند passlib یا bcrypt است. باید توابع hash_password و verify_password را شامل شود. خارج از این مرحله: endpointها، middleware، مدل کاربر.
**Excerpt:**
```
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید. همچنین middleware برای اعتبارسنجی token در هر درخواست.
```

### Step 4: پیاده‌سازی سرویس تولید و اعتبارسنجی JWT (JWT service)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک سرویس برای تولید توکن JWT (با استفاده از کتابخانه‌ای مانند PyJWT) و اعتبارسنجی آن است. باید توابع create_access_token, create_refresh_token, decode_token را شامل شود. پارامترهایی مانند SECRET_KEY, ALGORITHM, EXPIRY_TIME باید قابل تنظیم باشند. خارج از این مرحله: endpointها، middleware، مدل کاربر.
**Excerpt:**
```
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید. همچنین middleware برای اعتبارسنجی token در هر درخواست.
```

### Step 5: پیاده‌سازی endpoint ثبت‌نام (Register endpoint)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک endpoint POST /api/auth/register است که اطلاعات کاربر (username, email, password) را دریافت کرده، رمز عبور را هش کرده، کاربر را در دیتابیس ذخیره کرده و یک توکن JWT برمی‌گرداند. باید اعتبارسنجی ورودی (مثلاً unique بودن username/email) انجام شود. خارج از این مرحله: endpoint login، middleware.
**Excerpt:**
```
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید.
```

### Step 6: پیاده‌سازی endpoint ورود (Login endpoint)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک endpoint POST /api/auth/login است که username/email و password را دریافت کرده، اعتبارسنجی کرده و یک توکن JWT برمی‌گرداند. باید از سرویس هش رمز عبور برای تأیید استفاده کند. خارج از این مرحله: endpoint register، middleware.
**Excerpt:**
```
یک endpoint برای login (با تولید JWT یا session token) و یک endpoint برای register اضافه کنید.
```

### Step 7: پیاده‌سازی middleware اعتبارسنجی JWT
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک middleware (یا dependency در FastAPI) است که در هر درخواست (به جز endpointهای auth) توکن JWT را از هدر Authorization استخراج کرده، اعتبارسنجی کرده و کاربر جاری را به request اضافه می‌کند. خارج از این مرحله: endpointها، مدل کاربر.
**Excerpt:**
```
همچنین middleware برای اعتبارسنجی token در هر درخواست.
```

### Step 8: نوشتن تست‌های واحد برای سرویس‌های auth
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های واحد برای سرویس هش رمز عبور، سرویس JWT، و مدل کاربر است. تست‌ها باید موارد موفق و ناموفق را پوشش دهند. خارج از این مرحله: تست‌های integration، تست‌های endpoint.
**Excerpt:**
```
integration test برای pipeline `auth` بدون شکست عبور می‌کند
```

### Step 9: نوشتن تست‌های integration برای pipeline auth
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های integration است که جریان کامل ثبت‌نام، ورود، و دسترسی به endpoint محافظت‌شده را تست می‌کند. تست‌ها باید با دیتابیس تستی کار کنند. خارج از این مرحله: تست‌های واحد.
**Excerpt:**
```
integration test برای pipeline `auth` بدون شکست عبور می‌کند
```

### Step 10: مستندسازی تصمیمات و ایجاد PR description
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن یک توضیح کامل در PR description است که چرا این تغییرات انجام شده، چه گزینه‌هایی بررسی شده، و چرا این تصمیمات گرفته شده است. همچنین شامل به‌روزرسانی هرگونه مستندات مرتبط. خارج از این مرحله: تغییر کد.
**Excerpt:**
```
PR description توضیح می‌دهد چرا این تصمیم گرفته شد
```
