---
task_id: eb442b5b-e8a2-4791-acee-f6175fafed8d
title: صفحهٔ analysis از endpoint اشتباه برای بارگذاری پروفایل‌ها استفاده می‌کند
type: bug
priority: high
execution_priority: 100
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T04:20:34.648013+00:00'
updated_at: '2026-05-29T16:43:21.524729+00:00'
archived: true
archived_at: '2026-05-18T04:17:48.910659+00:00'
tags:
- merged
target_files:
- frontend/src/app/analysis/page.tsx
---

# صفحهٔ analysis از endpoint اشتباه برای بارگذاری پروفایل‌ها استفاده می‌کند

## Raw Idea

در frontend/src/app/analysis/page.tsx خط ۱۴۷، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند. اما endpoint صحیح برای دریافت پروفایل‌های مدل در backend در دو مسیر تعریف شده: backend/app/api/routes/models.py خط ۲۶۶ (`/models/profiles`) و backend/app/api/routes/model_profiles.py خط ۱۴۲ (`/api/models/profiles`). مسیر `/api/analysis/profiles` وجود خارجی ندارد و همیشه ۴۰۴ برمی‌گرداند. این باعث می‌شود تب «پروفایل مدل‌ها» همیشه خالی بماند و کاربر داده‌های واقعی نبیند.
---
[scan #2 at 2026-05-15T06:37:33.013541+00:00]
در frontend/src/app/analysis/page.tsx خط 147، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند، در حالی که endpoint صحیح برای پروفایل‌ها در backend/app/api/routes/models.py خط 266 با مسیر `/models/profiles` تعریف شده است. endpoint `/api/analysis/profiles` در backend وجود ندارد
---
[scan #3 at 2026-05-15T07:37:26.039748+00:00]
در frontend/src/app/analysis/page.tsx خط ۱۴۷، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند. اما endpoint صحیح برای دریافت پروفایل‌های مدل در backend در دو مسیر تعریف شده: `backend/app/api/routes/models.py` خط ۲۶۶ (`/models/profiles`) و `backend/app/api/routes/model_profile
---
[scan #4 at 2026-05-15T16:41:11.904496+00:00]
در frontend/src/app/analysis/page.tsx خط 147، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند در حالی که endpoint صحیح برای پروفایل‌ها در backend در مسیر `/api/models/profiles` (فایل model_profiles.py) یا `/models/profiles` (فایل models.py) تعریف شده است. endpoint `/api/analy
---
[scan #5 at 2026-05-15T17:36:09.541977+00:00]
در frontend/src/app/analysis/page.tsx خط 147، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` درخواست می‌کند. اما endpoint صحیح برای پروفایل مدل‌ها در backend در مسیر `/api/models/profiles` (فایل model_profiles.py) یا `/models/profiles` (فایل models.py خط 266) تعریف شده است. مسیر `/api/anal
---
[scan #6 at 2026-05-17T07:08:48.432800+00:00]
در frontend/src/app/analysis/page.tsx خط ۱۴۷، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند، در حالی که endpoint صحیح برای پروفایل مدل‌ها در backend/app/api/routes/models.py خط ۲۶۶ با مسیر `/models/profiles` تعریف شده است. endpoint `/api/analysis/profiles` در backend وجود ن

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
صفحهٔ analysis از endpoint اشتباه برای بارگذاری پروفایل‌ها استفاده می‌کند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — این خط باید اصلاح شود
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + FastAPI

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` (سطر 266) — endpoint صحیح /models/profiles در این فایل تعریف شده
- `backend/app/api/routes/model_profiles.py` (سطر 142) — endpoint جایگزین /api/models/profiles در این فایل تعریف شده

## 🌐 نقشهٔ وابستگی‌ها
فقط یک خط در فرانت‌اند نیاز به تغییر دارد. هیچ وابستگی دیگری تحت تأثیر قرار نمی‌گیرد.

## 🔍 Context و وضعیت فعلی
در frontend/src/app/analysis/page.tsx خط ۱۴۷، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند. اما endpoint صحیح برای دریافت پروفایل‌های مدل در backend در دو مسیر تعریف شده: backend/app/api/routes/models.py خط ۲۶۶ (`/models/profiles`) و backend/app/api/routes/model_profiles.py خط ۱۴۲ (`/api/models/profiles`). مسیر `/api/analysis/profiles` وجود خارجی ندارد و همیشه ۴۰۴ برمی‌گرداند. این باعث می‌شود تب «پروفایل مدل‌ها» همیشه خالی بماند و کاربر داده‌های واقعی نبیند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تب «پروفایل مدل‌ها» در صفحه analysis داده‌های واقعی را نمایش دهد
- [ ] کنسول مرورگر خطای 404 برای /api/analysis/profiles نشان ندهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در frontend/src/app/analysis/page.tsx خط ۱۴۷، آدرس fetch را از `${API_BASE}/api/analysis/profiles` به `${API_BASE}/api/models/profiles` تغییر بده.

## 💡 نمونه‌های قبل/بعد
**اصلاح آدرس API**

_قبل:_
```
const res = await fetch(`${API_BASE}/api/analysis/profiles`);
```

_بعد:_
```
const res = await fetch(`${API_BASE}/api/models/profiles`);
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl http://localhost:8000/api/models/profiles | jq .success`
- `curl http://localhost:8000/api/analysis/profiles | jq .detail`

## ⚠️ ریسک‌ها و موارد احتیاط
بدون ریسک — فقط یک تغییر مسیر ساده

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

## Acceptance Criteria

1. تب «پروفایل مدل‌ها» در صفحه analysis داده‌های واقعی را نمایش دهد _(verify: ui_interaction)_
2. کنسول مرورگر خطای 404 برای /api/analysis/profiles نشان ندهد _(verify: ui_interaction)_
