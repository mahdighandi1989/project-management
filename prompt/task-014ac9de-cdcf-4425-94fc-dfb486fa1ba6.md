---
task_id: 014ac9de-cdcf-4425-94fc-dfb486fa1ba6
title: صفحه Analysis از endpoint‌های ناقص و fallback داده استفاده می‌کند
type: bug
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T10:28:15.597981+00:00'
updated_at: '2026-05-31T09:06:50.611569+00:00'
target_files:
- frontend/src/app/analysis/page.tsx
- frontend/src/app/analysis/page.tsx
---

# صفحه Analysis از endpoint‌های ناقص و fallback داده استفاده می‌کند

## Raw Idea

صفحه `frontend/src/app/analysis/page.tsx` از endpoint‌های `/api/analysis/profiles` و `/api/models/available` استفاده می‌کند که در backend یا وجود ندارند یا داده‌های fallback برمی‌گردانند. endpoint `/api/analysis/profiles` در backend تعریف نشده است (فقط `/api/models/profiles` وجود دارد). endpoint `/api/models/available` در `backend/app/api/routes/models.py` خط ۲۰۷ تعریف شده ولی در صورت خطا آرایه خالی برمی‌گرداند. همچنین صفحه از `loadProfiles` برای دریافت پروفایل‌ها استفاده می‌کند که به endpoint اشتباه می‌رود. این باعث می‌شود کاربر داده‌های واقعی نبیند و خطاهای خاموش داشته باشد.
---
[scan #2 at 2026-05-24T09:09:12.258924+00:00]
در frontend/src/app/analysis/page.tsx خط 147، تابع loadProfiles درخواست GET به /api/analysis/profiles می‌زند. اما در backend هیچ route ای با این prefix و path وجود ندارد. مسیر صحیح برای دریافت پروفایل‌ها /api/models/profiles است (که در backend/app/api/routes/models.py خط 266 تعریف شده). این باعث می‌
---
[scan #3 at 2026-05-31T09:06:50.611561+00:00]
صفحه Analysis از endpoint های `/api/analysis/reports` و `/api/analysis/profiles` و `/api/models/available` استفاده می‌کند. endpoint `/api/analysis/reports` در backend وجود دارد (analysis.py line 271) اما endpoint `/api/analysis/profiles` در backend تعریف نشده است (در analysis.py وجود ندارد). endpoin

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
صفحه Analysis از endpoint‌های ناقص و fallback داده استفاده می‌کند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — endpoint اشتباه: باید `/api/models/profiles` باشد
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
- `frontend/src/app/analysis/page.tsx:157-167` — `loadModels` — endpoint `/api/models/available` در backend داده را به صورت آرایه برمی‌گرداند نه `{models: []}`
  ```tsx
  const loadModels = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/models/available`);
        if (res.ok) {
          const data = await res.json();
          setAvailableModels(data.models || []);
        }
      } catch (e) {
        console.error('Error loading models:', e);
      }
    };
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + FastAPI

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` (سطر 207) — endpoint `/api/models/available` در خط ۲۰۷ تعریف شده
- `backend/app/api/routes/model_profiles.py` (سطر 142) — endpoint `/api/models/profiles` در خط ۱۴۲ تعریف شده

## 🌐 نقشهٔ وابستگی‌ها
این صفحه به دو endpoint backend وابسته است که یکی مسیر اشتباه دارد و دیگری ساختار پاسخ متفاوتی دارد.

## 🔍 Context و وضعیت فعلی
صفحه `frontend/src/app/analysis/page.tsx` از endpoint‌های `/api/analysis/profiles` و `/api/models/available` استفاده می‌کند که در backend یا وجود ندارند یا داده‌های fallback برمی‌گردانند. endpoint `/api/analysis/profiles` در backend تعریف نشده است (فقط `/api/models/profiles` وجود دارد). endpoint `/api/models/available` در `backend/app/api/routes/models.py` خط ۲۰۷ تعریف شده ولی در صورت خطا آرایه خالی برمی‌گرداند. همچنین صفحه از `loadProfiles` برای دریافت پروفایل‌ها استفاده می‌کند که به endpoint اشتباه می‌رود. این باعث می‌شود کاربر داده‌های واقعی نبیند و خطاهای خاموش داشته باشد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] صفحه Analysis پروفایل‌های واقعی مدل‌ها را نمایش می‌دهد
- [ ] مدل‌های موجود به‌درستی در dropdown انتخاب مدل ظاهر می‌شوند
- [ ] هیچ خطای ۴۰۴ یا ۵۰۰ در console مرورگر ثبت نمی‌شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اصلاح endpoint‌های فراخوانی‌شده در frontend: `/api/analysis/profiles` به `/api/models/profiles` تغییر کند. endpoint `/api/models/available` باید خطاهای خود را به‌درستی مدیریت کند و داده‌های fallback را در frontend حذف یا با پیام مناسب جایگزین کند.

## 💡 نمونه‌های قبل/بعد
**اصلاح loadProfiles**

_قبل:_
```
fetch(`${API_BASE}/api/analysis/profiles`)
```

_بعد:_
```
fetch(`${API_BASE}/api/models/profiles`)
```

**اصلاح loadModels**

_قبل:_
```
setAvailableModels(data.models || [])
```

_بعد:_
```
setAvailableModels(Array.isArray(data) ? data : [])
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X GET http://localhost:8000/api/models/profiles`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. صفحه Analysis پروفایل‌های واقعی مدل‌ها را نمایش می‌دهد _(verify: ui_interaction)_
2. مدل‌های موجود به‌درستی در dropdown انتخاب مدل ظاهر می‌شوند _(verify: ui_interaction)_
3. هیچ خطای ۴۰۴ یا ۵۰۰ در console مرورگر ثبت نمی‌شود _(verify: ui_interaction)_
