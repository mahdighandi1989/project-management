---
task_id: 94ed2718-71d4-4b1b-bd28-ca4be03c9beb
title: 'endpoint بک‌اند بلااستفاده: GET /settings/by-task/{task_type}'
type: audit
priority: medium
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T06:05:56.979665+00:00'
updated_at: '2026-05-20T04:23:26.250510+00:00'
archived: true
archived_at: '2026-05-17T18:16:33.813582+00:00'
target_files:
- backend/app/api/routes/models.py
---

# endpoint بک‌اند بلااستفاده: GET /settings/by-task/{task_type}

## Raw Idea

## 📋 شرح
endpoint `GET /settings/by-task/{task_type}` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/settings/by-task/{task_type}`
- فایل: `backend/app/api/routes/models.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).
---
[scan #2 at 2026-05-15T06:39:20.344837+00:00]
## 📋 شرح
endpoint `GET /settings/by-task/{task_type}` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/settings/by-task/{task_type}`
- فایل: `backend/app/api/routes/models.py`
- علت: n
---
[scan #3 at 2026-05-15T07:39:32.132114+00:00]
## 📋 شرح
endpoint `GET /settings/by-task/{task_type}` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/settings/by-task/{task_type}`
- فایل: `backend/app/api/routes/models.py`
- علت: n
---
[scan #4 at 2026-05-15T10:32:35.321337+00:00]
## 📋 شرح
endpoint `GET /settings/by-task/{task_type}` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/settings/by-task/{task_type}`
- فایل: `backend/app/api/routes/models.py`
- علت: n
---
[scan #5 at 2026-05-15T16:45:13.185446+00:00]
## 📋 شرح
endpoint `GET /settings/by-task/{task_type}` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/settings/by-task/{task_type}`
- فایل: `backend/app/api/routes/models.py`
- علت: n

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
endpoint بک‌اند بلااستفاده: GET /settings/by-task/{task_type}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/models.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `GET /settings/by-task/{task_type}` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/settings/by-task/{task_type}`
- فایل: `backend/app/api/routes/models.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `GET /settings/by-task/{task_type}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/settings/by-task/{task_type}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/models.py`
- `ruff check backend/app/api/routes/models.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

## Acceptance Criteria

1. مشخص شد endpoint `GET /settings/by-task/{task_type}` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
2. اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف _(verify: static)_
3. اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد _(verify: static)_
