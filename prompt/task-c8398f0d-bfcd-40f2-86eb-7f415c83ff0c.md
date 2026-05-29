---
task_id: c8398f0d-bfcd-40f2-86eb-7f415c83ff0c
title: '[منطق] عدم coherence در مدیریت storage path'
type: logic_audit
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-17T08:11:28.862684+00:00'
updated_at: '2026-05-29T20:17:12.322010+00:00'
---

# [منطق] عدم coherence در مدیریت storage path

## Raw Idea

## 📋 شرح ناسازگاری
در pipeline `auth` یک ناسازگاری منطقی پیدا شد:

سرویس oversight_upload_session از UPLOAD_DIR استفاده می‌کند که از oversight_service.STORAGE_DIR گرفته شده، اما مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند. همچنین فایل JSON persistent (upload_sessions.json) در کدام مسیر ذخیره می‌شود مشخص نیست.

## 💥 پیامد (impact)
در صورت restart سرور، ممکن است فایل persistent پیدا نشود و سشن‌های ناقص از دست بروند. همچنین اگر STORAGE_DIR تغییر کند، داده‌های قبلی غیرقابل دسترس می‌شوند.

## 🛠 پیشنهاد رفع اولیه
مسیر ذخیره‌سازی را در config متمرکز کنید (مثلاً در backend/app/core/config.py) و در همه کامپوننت‌ها از آن استفاده کنید. مسیر فایل persistent را نیز در config تعریف کنید.

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
[منطق] عدم coherence در مدیریت storage path

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

سرویس oversight_upload_session از UPLOAD_DIR استفاده می‌کند که از oversight_service.STORAGE_DIR گرفته شده، اما مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند. همچنین فایل JSON persistent (upload_sessions.json) در کدام مسیر ذخیره می‌شود مشخص نیست.

## 💥 پیامد (impact)
در صورت restart سرور، ممکن است فایل persistent پیدا نشود و سشن‌های ناقص از دست بروند. همچنین اگر STORAGE_DIR تغییر کند، داده‌های قبلی غیرقابل دسترس می‌شوند.

## 🛠 پیشنهاد رفع اولیه
مسیر ذخیره‌سازی را در config متمرکز کنید (مثلاً در backend/app/core/config.py) و در همه کامپوننت‌ها از آن استفاده کنید. مسیر فایل persistent را نیز در config تعریف کنید.

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
- اولویت: medium
- تخمین زمان: medium

## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: static)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: static)_
3. integration test برای pipeline `auth` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: بررسی و شناسایی دقیق تمام نقاط استفاده از STORAGE_DIR و UPLOAD_DIR در pipeline auth
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل جستجوی کامل در repository برای یافتن تمام ارجاعات به STORAGE_DIR، UPLOAD_DIR، oversight_service.STORAGE_DIR، و هر مسیر ذخیره‌سازی مرتبط با oversight_upload_session است. باید فایل‌های backend/app/services/oversight_service.py، backend/app/services/oversight_upload_session.py، backend/app/models/، و backend/app/database/ بررسی شوند. همچنین باید مشخص شود که آیا فایل upload_sessions.json در حال حاضر در کد ایجاد/خوانده می‌شود و اگر بله، مسیر آن چیست. خروجی این مرحله یک لیست کامل از تمام فایل‌ها و خطوط کد است که با این مسیرها سروکار دارند. این مرحله فقط شامل شناسایی است و هیچ تغییری در کد ایجاد نمی‌کند.
**Excerpt:**
```
در pipeline `auth` یک ناسازگاری منطقی پیدا شد: سرویس oversight_upload_session از UPLOAD_DIR استفاده می‌کند که از oversight_service.STORAGE_DIR گرفته شده، اما مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند. همچنین فایل JSON persistent (upload_sessions.json) در کدام مسیر ذخیره می‌شود مشخص نیست.
```

### Step 2: ایجاد/به‌روزرسانی متغیرهای مسیر ذخیره‌سازی متمرکز در config (backend/app/core/config.py)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل افزودن متغیرهای جدید به کلاس Settings در backend/app/core/config.py است. متغیرها باید شامل STORAGE_DIR (مسیر پایه ذخیره‌سازی)، UPLOAD_DIR (مسیر زیرمجموعه برای آپلودها)، و PERSISTENT_SESSIONS_FILE (مسیر کامل فایل upload_sessions.json) باشند. مقادیر پیش‌فرض باید به گونه‌ای تعیین شوند که با مسیرهای فعلی سازگار باشند (مثلاً './storage' برای STORAGE_DIR). همچنین باید اطمینان حاصل شود که این متغیرها از طریق متغیرهای محیطی (env vars) قابل تنظیم هستند. این مرحله شامل تغییر در هیچ فایل دیگری غیر از config.py نیست.
**Excerpt:**
```
مسیر ذخیره‌سازی را در config متمرکز کنید (مثلاً در backend/app/core/config.py) و در همه کامپوننت‌ها از آن استفاده کنید. مسیر فایل persistent را نیز در config تعریف کنید.
```

### Step 3: به‌روزرسانی oversight_service.py برای استفاده از config متمرکز به جای STORAGE_DIR محلی
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/services/oversight_service.py است. باید import مربوط به settings از backend/app/core/config.py اضافه شود. سپس تمام ارجاعات به STORAGE_DIR (که احتمالاً یک متغیر محلی یا ثابت در همین فایل است) با settings.STORAGE_DIR جایگزین شود. همچنین اگر تابع یا کلاسی وجود دارد که از STORAGE_DIR استفاده می‌کند، باید به‌روزرسانی شود. این مرحله شامل تغییر در oversight_upload_session.py یا سایر فایل‌ها نیست.
**Excerpt:**
```
سرویس oversight_upload_session از UPLOAD_DIR استفاده می‌کند که از oversight_service.STORAGE_DIR گرفته شده، اما مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند.
```

### Step 4: به‌روزرسانی oversight_upload_session.py برای استفاده از UPLOAD_DIR و PERSISTENT_SESSIONS_FILE از config
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/services/oversight_upload_session.py است. باید import settings از config.py اضافه شود. سپس تمام ارجاعات به UPLOAD_DIR (که احتمالاً از oversight_service.STORAGE_DIR گرفته شده) با settings.UPLOAD_DIR جایگزین شود. همچنین اگر این سرویس فایل upload_sessions.json را می‌خواند/می‌نویسد، باید مسیر آن را از settings.PERSISTENT_SESSIONS_FILE بگیرد. اگر سرویس در حال حاضر از یک مسیر سخت‌کد شده یا نسبی برای این فایل استفاده می‌کند، باید اصلاح شود. این مرحله شامل تغییر در مدل‌ها یا database نیست.
**Excerpt:**
```
سرویس oversight_upload_session از UPLOAD_DIR استفاده می‌کند که از oversight_service.STORAGE_DIR گرفته شده، اما مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند. همچنین فایل JSON persistent (upload_sessions.json) در کدام مسیر ذخیره می‌شود مشخص نیست.
```

### Step 5: بررسی و به‌روزرسانی مدل‌های مرتبط با upload session برای ذخیره‌سازی مسیر فایل (در صورت نیاز)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل بررسی فایل‌های مدل در backend/app/models/ (مثلاً models/upload_session.py یا مشابه) است. اگر مدلی برای upload session وجود دارد که شامل فیلد مسیر فایل (مثلاً file_path) است، باید اطمینان حاصل شود که این مسیر به صورت نسبی (relative to UPLOAD_DIR) ذخیره می‌شود، نه مطلق. اگر مدل از یک مسیر مطلق استفاده می‌کند، باید اصلاح شود تا فقط نام فایل یا مسیر نسبی را ذخیره کند. اگر مدلی وجود ندارد، این مرحله هیچ تغییری ایجاد نمی‌کند. این مرحله شامل تغییر در database schema نیست.
**Excerpt:**
```
مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند.
```

### Step 6: بررسی و به‌روزرسانی database layer برای استفاده از مسیرهای متمرکز (در صورت نیاز)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل بررسی فایل‌های database در backend/app/database/ (مثلاً database/session.py یا مشابه) است. اگر database layer شامل هرگونه ارجاع به STORAGE_DIR، UPLOAD_DIR، یا مسیر فایل persistent است، باید با مقادیر settings جایگزین شود. اگر database layer از این مسیرها استفاده نمی‌کند، این مرحله هیچ تغییری ایجاد نمی‌کند. این مرحله شامل تغییر در schema یا migration نیست.
**Excerpt:**
```
مدل‌ها و database هیچ اشاره‌ای به این مسیر ندارند.
```

### Step 7: نوشتن تست‌های واحد (unit tests) برای تایید coherence مسیرها در pipeline auth
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های واحد جدید در backend/app/tests/ (یا دایرکتوری تست موجود) است. تست‌ها باید بررسی کنند که: 1) oversight_service از settings.STORAGE_DIR استفاده می‌کند، 2) oversight_upload_session از settings.UPLOAD_DIR و settings.PERSISTENT_SESSIONS_FILE استفاده می‌کند، 3) اگر مدل upload session وجود دارد، مسیر فایل را به صورت نسبی ذخیره می‌کند. تست‌ها باید با استفاده از monkeypatch یا mocking، settings را با مقادیر تست جایگزین کنند تا وابستگی به فایل‌سیستم واقعی نداشته باشند. این مرحله شامل نوشتن تست‌های integration یا end-to-end نیست.
**Excerpt:**
```
این کلاس bug ها در test معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند.
```

### Step 8: به‌روزرسانی مستندات (در صورت وجود) برای انعکاس تغییرات مسیرها
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل بررسی و به‌روزرسانی هرگونه مستندات مرتبط با pipeline auth است. اگر فایل README.md، docs/، یا هر مستند دیگری وجود دارد که به STORAGE_DIR، UPLOAD_DIR، یا upload_sessions.json اشاره می‌کند، باید به‌روزرسانی شود تا منعکس‌کننده استفاده از settings متمرکز باشد. اگر مستنداتی وجود ندارد، این مرحله هیچ تغییری ایجاد نمی‌کند.
**Excerpt:**
```
مسیر ذخیره‌سازی را در config متمرکز کنید (مثلاً در backend/app/core/config.py) و در همه کامپوننت‌ها از آن استفاده کنید.
```
