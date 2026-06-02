---
task_id: fabf29f8-36b4-43ec-911a-5f6f47ccabfc
title: Endpoint `/api/models/available` در فرانت‌اند با ساختار پاسخ بک‌اند ناسازگار است
type: bug
priority: high
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-14T19:47:49.433099+00:00'
updated_at: '2026-06-02T17:41:24.431790+00:00'
archived: true
archived_at: '2026-05-17T10:17:05.885801+00:00'
---

# Endpoint `/api/models/available` در فرانت‌اند با ساختار پاسخ بک‌اند ناسازگار است

## Raw Idea

در `frontend/src/app/analysis/page.tsx` خط ۱۵۹، تابع `loadModels` به `/api/models/available` درخواست می‌دهد و انتظار دارد پاسخ شامل فیلد `data.models` باشد (خط ۱۶۲: `data.models || []`). اما بک‌اند در `backend/app/api/routes/models.py` خط ۲۰۷-۲۳۶، این endpoint یک آرایه مستقیم از `ModelInfo` برمی‌گرداند (نه یک object با فیلد `models`). این mismatch باعث می‌شود `availableModels` همیشه یک آرایه خالی باشد و کاربر نتواند مدلی برای تحلیل انتخاب کند.
---
[scan #2 at 2026-05-17T08:02:06.983239+00:00]
در frontend/src/app/analysis/page.tsx خط ۱۵۹، تابع loadModels از `${API_BASE}/api/models/available` استفاده می‌کند. این endpoint در backend/app/api/routes/models.py خط ۲۰۷ تعریف شده و `List[ModelInfo]` برمی‌گرداند. اما کد frontend در خط ۱۶۲ انتظار `data.models` را دارد (`setAvailableModels(data.mode
---
[scan #3 at 2026-05-17T08:02:38.224674+00:00]
در frontend/src/app/analysis/page.tsx خط ۱۵۹، فرانت‌اند از /api/models/available برای دریافت مدل‌های موجود استفاده می‌کند و انتظار دارد پاسخ شامل فیلد 'models' باشد (خط ۱۶۲: data.models || [])، اما backend در models.py خط ۲۰۷-۲۳۶ مستقیماً یک آرایه از ModelInfo برمی‌گرداند، نه یک آبجکت با فیلد models
---
[scan #4 at 2026-05-17T08:39:14.829031+00:00]
در frontend/src/app/analysis/page.tsx خط ۱۵۹، تابع loadModels از `${API_BASE}/api/models/available` استفاده می‌کند. اما این endpoint در backend/app/api/routes/models.py خط ۲۰۷-۲۳۶ تعریف شده و لیست ModelInfo برمی

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
Endpoint `/api/models/available` در فرانت‌اند با ساختار پاسخ بک‌اند ناسازگار است

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/analysis/page.tsx` خط ۱۵۹، تابع `loadModels` به `/api/models/available` درخواست می‌دهد و انتظار دارد پاسخ شامل فیلد `data.models` باشد (خط ۱۶۲: `data.models || []`). اما بک‌اند در `backend/app/api/routes/models.py` خط ۲۰۷-۲۳۶، این endpoint یک آرایه مستقیم از `ModelInfo` برمی‌گرداند (نه یک object با فیلد `models`). این mismatch باعث می‌شود `availableModels` همیشه یک آرایه خالی باشد و کاربر نتواند مدلی برای تحلیل انتخاب کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در `frontend/src/app/analysis/page.tsx` خط ۱۶۲، دسترسی به داده

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

## Acceptance Criteria

1. اعمال تغییر بدون شکستن تست‌های موجود _(verify: backend_test)_
2. linter بدون warning عبور می‌کند _(verify: static)_
3. type-check موفق است _(verify: static)_
