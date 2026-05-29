---
task_id: c1fe5cde-a073-4bbd-b780-ce5cc1f95e05
title: Endpoint `/api/analysis/profiles` در فرانت‌اند فراخوانی می‌شود اما در بک‌اند وجود ندارد
type: bug
priority: high
execution_priority: 100
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-14T19:47:49.424906+00:00'
updated_at: '2026-05-29T20:09:16.890953+00:00'
archived: true
archived_at: '2026-05-18T04:17:48.910659+00:00'
tags:
- merged
target_files:
- frontend/src/app/analysis/page.tsx
---

# Endpoint `/api/analysis/profiles` در فرانت‌اند فراخوانی می‌شود اما در بک‌اند وجود ندارد

## Raw Idea

در `frontend/src/app/analysis/page.tsx` خط ۱۴۷، تابع `loadProfiles` درخواست GET به `/api/analysis/profiles` می‌فرستد. اما در بک‌اند، هیچ route ای با این prefix در `backend/app/api/routes/analysis.py` تعریف نشده است. مسیر صحیح برای دریافت پروفایل‌ها `/api/models/profiles` است (که در `backend/app/api/routes/models.py` خط ۲۶۶ تعریف شده). این mismatch باعث می‌شود تب «پروفایل مدل‌ها» در صفحه تحلیل هیچوقت داده واقعی دریافت نکند و همیشه خالی بماند.
---
[scan #2 at 2026-05-17T08:39:14.820396+00:00]
در frontend/src/app/analysis/page.tsx خط ۱۴۷، تابع loadProfiles از `${API_BASE}/api/analysis/profiles` استفاده می‌کند. اما این endpoint در backend وجود ندارد — مسیر صحیح برای پروفایل‌ها `/api/models/profiles` است (که در backend/app/api/routes/models.py خط ۲۶۶ تعریف شده). در نتیجه تب «پروفایل مدل‌ها»

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
Endpoint `/api/analysis/profiles` در فرانت‌اند فراخوانی می‌شود اما در بک‌اند وجود ندارد

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — URL اشتباه: باید `/api/models/profiles` باشد
  ```tsx
  const loadProfiles = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analysis/profiles`);
        if (res.ok) {
          const data = await res.json();
          setProfiles(data || []);
        }
      } catch (e) {
        console.error('Error loading profiles:', e);
      }
    };
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + FastAPI

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` (سطر 266) — route صحیح در این فایل تعریف شده
- `backend/app/api/routes/analysis.py` (سطر 1) — route اشتباه در این فایل وجود ندارد

## 🌐 نقشهٔ وابستگی‌ها
این باگ فقط در فرانت‌اند است و بک‌اند را تحت تأثیر قرار نمی‌دهد، اما قابلیت مشاهده پروفایل‌ها در صفحه تحلیل را کاملاً از کار می‌اندازد.

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/analysis/page.tsx` خط ۱۴۷، تابع `loadProfiles` درخواست GET به `/api/analysis/profiles` می‌فرستد. اما در بک‌اند، هیچ route ای با این prefix در `backend/app/api/routes/analysis.py` تعریف نشده است. مسیر صحیح برای دریافت پروفایل‌ها `/api/models/profiles` است (که در `backend/app/api/routes/models.py` خط ۲۶۶ تعریف شده). این mismatch باعث می‌شود تب «پروفایل مدل‌ها» در صفحه تحلیل هیچوقت داده واقعی دریافت نکند و همیشه خالی بماند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] پس از اصلاح، تب «پروفایل مدل‌ها» در صفحه تحلیل داده‌های واقعی را نمایش می‌دهد
- [ ] کنسول مرورگر خطای 404 برای این endpoint نشان نمی‌دهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در `frontend/src/app/analysis/page.tsx` خط ۱۴۷، URL درخواست را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید.

## 💡 نمونه‌های قبل/بعد
**اصلاح URL**

_قبل:_
```
`${API_BASE}/api/analysis/profiles`
```

_بعد:_
```
`${API_BASE}/api/models/profiles`
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run build --prefix frontend`
- `مرور صفحه /analysis و کلیک روی تب «پروفایل مدل‌ها»`

## ⚠️ ریسک‌ها و موارد احتیاط
بدون ریسک — تغییر یک رشته ساده

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

## Acceptance Criteria

1. پس از اصلاح، تب «پروفایل مدل‌ها» در صفحه تحلیل داده‌های واقعی را نمایش می‌دهد _(verify: ui_interaction)_
2. کنسول مرورگر خطای 404 برای این endpoint نشان نمی‌دهد _(verify: ui_interaction)_
