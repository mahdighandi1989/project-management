---
task_id: cbcd3da3-b842-4a8e-a614-f4a63bd7f78d
title: '[منطق] عدم وجود user/role context در مدل inspector_session'
type: logic_audit
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T16:44:18.111020+00:00'
updated_at: '2026-06-03T18:13:30.617383+00:00'
---

# [منطق] عدم وجود user/role context در مدل inspector_session

## Raw Idea

## 📋 شرح ناسازگاری
در pipeline `auth` یک ناسازگاری منطقی پیدا شد:

مدل inspector_session شامل فیلدهایی برای ذخیره سشن و پیام است، اما هیچ فیلدی برای user_id یا role_id ندارد. این یعنی نمی‌توان تشخیص داد چه کاربری سشن را ایجاد کرده یا چه نقشی دارد.

## 💥 پیامد (impact)
بدون user context، امکان پیاده‌سازی permission checking مبتنی بر نقش وجود ندارد. همه کاربران به طور یکسان به سشن‌ها دسترسی خواهند داشت.

## 🛠 پیشنهاد رفع اولیه
فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید. همچنین یک رابطه به مدل User ایجاد کنید.

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
[منطق] عدم وجود user/role context در مدل inspector_session

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

مدل inspector_session شامل فیلدهایی برای ذخیره سشن و پیام است، اما هیچ فیلدی برای user_id یا role_id ندارد. این یعنی نمی‌توان تشخیص داد چه کاربری سشن را ایجاد کرده یا چه نقشی دارد.

## 💥 پیامد (impact)
بدون user context، امکان پیاده‌سازی permission checking مبتنی بر نقش وجود ندارد. همه کاربران به طور یکسان به سشن‌ها دسترسی خواهند داشت.

## 🛠 پیشنهاد رفع اولیه
فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید. همچنین یک رابطه به مدل User ایجاد کنید.

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
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد _(verify: manual_only)_
2. ground truth تعیین شد و طرف دیگر align شد _(verify: manual_only)_
3. integration test برای pipeline `auth` بدون شکست عبور می‌کند _(verify: backend_test)_
4. PR description توضیح می‌دهد چرا این تصمیم گرفته شد _(verify: manual_only)_

## Task Steps

### Step 1: بررسی وضعیت فعلی مدل inspector_session و فایل‌های مرتبط در pipeline auth
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل جستجوی کامل در repo برای یافتن فایل‌های مربوط به مدل inspector_session، مدل User، و pipeline auth است. باید مشخص شود که آیا فیلدهای user_id و role_id از قبل وجود دارند یا خیر. همچنین باید فایل‌های migration، schema، و model definitions بررسی شوند. خارج از این مرحله: ایجاد تغییرات یا نوشتن کد جدید. نکته حیاتی: اگر فیلدها از قبل وجود دارند، مراحل بعدی باید اصلاح شوند.
**Excerpt:**
```
مدل inspector_session شامل فیلدهایی برای ذخیره سشن و پیام است، اما هیچ فیلدی برای user_id یا role_id ندارد. این یعنی نمی‌توان تشخیص داد چه کاربری سشن را ایجاد کرده یا چه نقشی دارد. ... فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید. همچنین یک رابطه به مدل User ایجاد کنید.
```

### Step 2: اضافه کردن فیلد user_id به مدل inspector_session
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل افزودن فیلد user_id از نوع ForeignKey به مدل inspector_session در فایل مدل مربوطه است. این فیلد باید به مدل User اشاره کند. همچنین باید فیلد nullable=false باشد مگر اینکه نیاز به backward compatibility باشد. خارج از این مرحله: اضافه کردن role_id، migration، یا تغییرات UI. نکته حیاتی: اگر فیلد از قبل وجود دارد، این مرحله را رد کن.
**Excerpt:**
```
فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید. همچنین یک رابطه به مدل User ایجاد کنید.
```

### Step 3: اضافه کردن فیلد role_id به مدل inspector_session
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل افزودن فیلد role_id از نوع ForeignKey به مدل inspector_session است. این فیلد باید به یک مدل Role (اگر وجود دارد) یا یک فیلد string ساده اشاره کند. اگر مدل Role وجود ندارد، باید یک فیلد string role_id اضافه شود. خارج از این مرحله: ایجاد مدل Role، migration، یا تغییرات UI. نکته حیاتی: اگر role_id از قبل وجود دارد، این مرحله را رد کن.
**Excerpt:**
```
فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید. همچنین یک رابطه به مدل User ایجاد کنید.
```

### Step 4: ایجاد رابطه (relationship) بین inspector_session و User
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل افزودن یک relationship property در مدل inspector_session است که به مدل User اشاره می‌کند. همچنین در مدل User باید یک relationship معکوس (back_populates) اضافه شود. خارج از این مرحله: migration، تغییرات schema، یا تغییرات UI. نکته حیاتی: اگر relationship از قبل وجود دارد، این مرحله را رد کن.
**Excerpt:**
```
همچنین یک رابطه به مدل User ایجاد کنید.
```

### Step 5: ایجاد migration فایل برای اضافه کردن فیلدهای جدید به دیتابیس
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک فایل migration جدید (با استفاده از Alembic یا ابزار مشابه) است که فیلدهای user_id و role_id را به جدول inspector_session اضافه می‌کند. همچنین باید foreign key constraints و indexes لازم ایجاد شود. خارج از این مرحله: تغییرات مدل، تغییرات منطق business، یا تست. نکته حیاتی: migration باید backward compatible باشد (فیلدهای nullable=true برای سشن‌های موجود).
**Excerpt:**
```
فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید.
```

### Step 6: اجرای migration و به‌روزرسانی دیتابیس
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اجرای migration ایجاد شده در مرحله قبل بر روی دیتابیس است. باید مطمئن شویم که migration با موفقیت اجرا می‌شود و فیلدهای جدید در دیتابیس ایجاد می‌شوند. خارج از این مرحله: تغییرات مدل، تغییرات منطق business، یا تست. نکته حیاتی: اگر دیتابیس حاوی داده است، migration باید nullable=true باشد.
**Excerpt:**
```
فیلدهای user_id و role_id را به مدل inspector_session اضافه کنید.
```

### Step 7: به‌روزرسانی منطق ایجاد سشن برای ذخیره user_id و role_id
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل به‌روزرسانی endpoint یا تابعی است که inspector_session ایجاد می‌کند تا user_id و role_id کاربر فعلی را ذخیره کند. باید از context کاربر (مثلاً JWT token یا session) user_id و role_id استخراج شود. خارج از این مرحله: تغییرات مدل، migration، یا تست. نکته حیاتی: اگر کاربر احراز هویت نشده است، باید خطا برگرداند.
**Excerpt:**
```
بدون user context، امکان پیاده‌سازی permission checking مبتنی بر نقش وجود ندارد. همه کاربران به طور یکسان به سشن‌ها دسترسی خواهند داشت.
```

### Step 8: به‌روزرسانی منطق permission checking برای استفاده از user_id و role_id
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل به‌روزرسانی middleware یا تابع permission checking در pipeline auth است تا از user_id و role_id ذخیره شده در inspector_session برای بررسی دسترسی استفاده کند. باید بررسی شود که کاربر فعلی با user_id سشن مطابقت دارد یا role_id مجوز لازم را دارد. خارج از این مرحله: تغییرات مدل، migration، یا تست. نکته حیاتی: permission checking باید برای همه endpoint‌های مربوط به inspector_session اعمال شود.
**Excerpt:**
```
بدون user context، امکان پیاده‌سازی permission checking مبتنی بر نقش وجود ندارد. همه کاربران به طور یکسان به سشن‌ها دسترسی خواهند داشت.
```

### Step 9: نوشتن integration test برای pipeline auth با user context
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن یک integration test است که سناریوهای زیر را پوشش می‌دهد: ایجاد سشن با user_id و role_id، دسترسی به سشن توسط کاربر مجاز، دسترسی به سشن توسط کاربر غیرمجاز، و دسترسی به سشن توسط کاربر با نقش مناسب. خارج از این مرحله: unit test، تغییرات مدل، یا تغییرات منطق business. نکته حیاتی: تست باید درون pipeline auth اجرا شود و با دیتابیس واقعی کار کند.
**Excerpt:**
```
integration test برای pipeline `auth` بدون شکست عبور می‌کند
```

### Step 10: مستندسازی coherence issue و تغییرات انجام شده در PR description
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن یک PR description کامل است که شامل: شرح coherence issue، تغییرات انجام شده، فایل‌های تغییر یافته، و checklist از همه مراحل انجام شده. همچنین باید ground truth تعیین شده و توضیح داده شود که چرا این تغییرات coherence issue را حل می‌کند. خارج از این مرحله: تغییرات کد، تست، یا migration. نکته حیاتی: PR description باید شامل لینک به issue اصلی و توضیح impact باشد.
**Excerpt:**
```
هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد. ground truth تعیین شد و طرف دیگر align شد.
```
