---
task_id: task_3f9185f87f99
title: رفع ناسازگاری‌های endpoint و باگ‌های UI در صفحه Analysis
type: other
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:17:41.780822+00:00'
updated_at: '2026-06-02T18:00:46.493646+00:00'
tags:
- consolidated
- post_verify_merge
---

# رفع ناسازگاری‌های endpoint و باگ‌های UI در صفحه Analysis

## Raw Idea

🧬 این یک تسک تلفیقی است — از 8 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به صفحه analysis در فرانت‌اند که از endpointهای اشتباه یا وجود نداشته استفاده می‌کنند. این تسک‌ها به فایل page.tsx و endpointهای بک‌اند مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به صفحه Analysis و endpointهای آن در فرانت‌اند
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 8
  id: c1fe5cde-a073-4bbd-b780-ce5cc1f95e05
  عنوان اصلی: Endpoint `/api/analysis/profiles` در فرانت‌اند فراخوانی می‌شود اما در بک‌اند وجود ندارد
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - پس از اصلاح، تب «پروفایل مدل‌ها» در صفحه تحلیل داده‌های واقعی را نمایش می‌دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]
  - کنسول مرورگر خطای 404 برای این endpoint نشان نمی‌دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 8
  id: eb442b5b-e8a2-4791-acee-f6175fafed8d
  عنوان اصلی: صفحهٔ analysis از endpoint اشتباه برای بارگذاری پروفایل‌ها استفاده می‌کند
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - تب «پروفایل مدل‌ها» در صفحه analysis داده‌های واقعی را نمایش دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]
  - کنسول مرورگر خطای 404 برای /api/analysis/profiles نشان ندهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 8
  id: eeecd69a-0df4-4830-af3e-e0e6e3222702
  عنوان اصلی: صفحه analysis از endpoint /api/analysis/profiles استفاده می‌کند که وجود ندارد
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "eslint"], "files_hint": ["frontend/"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["tsc", "type-check", "typescript"], "files_hint": ["frontend/"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
صفحه analysis از endpoint /api/analysis/profiles استفاده می‌کند که وجود ندارد

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — این خط باید اصلاح شود
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` — این فایل endpoint صحیح /

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/analysis/page.tsx` (خط 147)، تابع `loadProfiles` از endpoint `GET /api/analysis/profiles` برای دریافت پروفایل مدل‌ها استفاده می‌کند. با این حال، در فایل‌های بک‌اند، هیچ route ای با این مسیر در `backend/app/api/routes/analysis.py` تعریف نشده است. مسیر صحیح برای دریافت پروفایل‌ها احتمالاً `GET /api/models/profiles` است که در `backend/app/api/routes/models.py` (خط 266) تعریف شده است. این باعث می‌شود که درخواست فرانت‌اند با خطای 404 مواجه شود و پروفایل‌ها هرگز بارگذاری نشوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مسیر API در فرانت‌اند را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید تا با endpoint موجود در بک‌اند مطابقت داشته باشد.

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 8
  id: e0514ce1-0b5d-425c-9099-4c62f7263002
  عنوان اصلی: صفحه Analysis (frontend/src/app/analysis/page.tsx) از endpoint منسوخ /api/analysis/profiles استفاده می‌کند
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - صفحه Analysis در تب 'پروفایل مدل‌ها' داده‌ها را نمایش دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-models-profiles']"]
  - کنسول مرورگر خطای 404 ندهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-models-profiles']"]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
صفحه Analysis (frontend/src/app/analysis/page.tsx) از endpoint منسوخ /api/analysis/profiles استفاده می‌کند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — URL اشتباه: باید /api/models/profiles باشد
  ```tsx
  const loadProfiles = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analysis/profiles`);
        if (res.ok) {
          const data = await res.json();
          setProfiles(data || []);
        }
      } catch (e) {
        console.error('Error loading reports:', e);
      }
    };
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + FastAPI

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` (سطر 266) — endpoint صحیح /api/models/profiles در خط 266 تعریف شده
- `frontend/src/app/model-profiles/page.tsx` (سطر 116) — این صفحه از endpoint صحیح استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
فقط یک fetch call در frontend که باید اصلاح شود.

## 🔍 Context و وضعیت فعلی
در خط 147، تابع loadProfiles از endpoint `/api/analysis/profiles` استفاده می‌کند. این endpoint در backend وجود ندارد. مسیر صحیح `/api/models/profiles` است (که در `backend/app/api/routes/models.py` خط 266 تعریف شده). در نتیجه، تب 'پروفایل مدل‌ها' در صفحه Analysis همیشه خالی می‌ماند و خطای 404 دریافت می‌کند. کاربران نمی‌توانند پروفایل مدل‌ها را از این صفحه مشاهده کنند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] صفحه Analysis در تب 'پروفایل مدل‌ها' داده‌ها را نمایش دهد
- [ ] کنسول مرورگر خطای 404 ندهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. URL تابع loadProfiles را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید.

## 💡 نمونه‌های قبل/بعد
**اصلاح URL**

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
- `صفحه /analysis را باز کنید و به تب 'پروفایل مدل‌ها' بروید`

## ⚠️ ریسک‌ها و موارد احتیاط
ندارد

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 8
  id: 3d4a0007-a5bb-42c3-932b-9e47ae3d4c5a
  عنوان اصلی: Anti-pattern: AI بدون validation (response استفاده می‌شود بدون چ
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["runAnalysis", "loadReports", "loadProfiles", "loadModels"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["schema", "validation", "zod", "yup", "interface", "type guard"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_edge_case", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: AI بدون validation (response استفاده می‌شود بدون چ

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:130`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در تابع runAnalysis، داده‌های استریم شده از سرور مستقیماً بدون اعتبارسنجی ساختار (schema validation) به state اختصاص داده می‌شوند. اگر سرور داده‌ای با ساختار متفاوت یا فیلدهای ناقص برگرداند، برنامه دچار خطای runtime یا نمایش داده‌های نادرست می‌شود. همچنین در loadReports، loadProfiles و loadModels، پاسخ API بدون بررسی صحت ساختار (مثلاً بررسی وجود فیلدهای ضروری) مستقیماً در state قرار می‌گیرد.

📁 file: frontend/src/app/analysis/page.tsx (line 130)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 8
  id: 9733c833-f8fa-4c2b-b401-dc8446f22fe8
  عنوان اصلی: Anti-pattern: Stale assumption (کد فرض می‌کند رفتار X خاصه، ولی
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["data\\.models", "response\\.body\\?\\.", "getReader\\(\\)"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["TODO", "FIXME", "stale assumption", "//.*edge case"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis_edge_cases.py::test_stale_assumption", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: Stale assumption (کد فرض می‌کند رفتار X خاصه، ولی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:120`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
کد فرض می‌کند که endpointهای API همیشه با ساختار ثابت پاسخ می‌دهند (مثلاً data.models برای لیست مدل‌ها). اگر API تغییر کند (مثلاً فیلد models به models_list تغییر نام دهد)، کد بدون خطای واضح از کار می‌افتد. همچنین فرض شده که response.body?.getReader() همیشه در دسترس است، در حالی که در برخی مرورگرها یا شرایط شبکه ممکن است null باشد.

📁 file: frontend/src/app/analysis/page.tsx (line 120)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 8
  id: 2a262bff-97b6-4009-97e7-9e4c2386a710
  عنوان اصلی: Anti-pattern: Threshold-Outcome mismatch (parameters → نتیجه مطل
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["project_id.*proj_\\$\\{Date\\.now\\(\\)\\}", "selectedModels.*undefined"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["//.*threshold.*outcome.*mismatch", "//.*anti.pattern.*explanation"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_edge_case_invalid_project_id", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: Threshold-Outcome mismatch (parameters → نتیجه مطل

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:125`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
پارامترهای ارسالی به API (project_id با مقدار proj_${Date.now()}) ممکن است با انتظارات سرور همخوانی نداشته باشد. اگر سرور نیاز به project_id معتبر از قبل داشته باشد، این مقدار موقت باعث خطا می‌شود. همچنین ارسال selectedModels به صورت undefined در صورت خالی بودن، ممکن است باعث رفتار غیرمنتظره در سرور شود.

📁 file: frontend/src/app/analysis/page.tsx (line 125)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 8
  id: 6a6acb47-b1b6-4ed1-808f-944d9ad101a6
  عنوان اصلی: دکمه‌ی UI بدون handler: بروزرسانی
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - git blame مشخص می‌کند چرا این دکمه `بروزرسانی` فاقد handler است [verify_method=static] [verify_plan={"grep_patterns": ["git blame", "بروزرسانی", "onClick"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده [verify_method=static] [verify_plan={"grep_patterns": ["onClick", "بروزرسانی", "decorative", "disabled"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='update-button']"}, {"a]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
دکمه‌ی UI بدون handler: بروزرسانی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
یک دکمه/کنترل UI در فایل `frontend/src/app/analysis/page.tsx` پیدا شد که هیچ event handler معنادار به آن متصل نیست (onClick، onChange، form submit، router push، یا API call شناسایی نشد).

## 🔍 جزئیات
- label/متن دکمه: `بروزرسانی`
- فایل: `frontend/src/app/analysis/page.tsx`
- علت تشخیص stale_detector: button has no onClick handler

## 🤔 چرا مهم است
دکمه بدون handler از دید کاربر کار نمی‌کند و دو حالت دارد:
  ۱) **dead UI**: دکمه از قبل کار می‌کرده و در refactor شکست خورده (regression) — باید handler بازگردانده شود.
  ۲) **forgotten option**: دکمه placeholder بوده و هرگز پیاده‌سازی نشده — باید یا حذف شود یا پیاده‌سازی کامل شود.
  ۳) **decorative**: فقط نمایشی است — باید با `aria-disabled` یا `role="presentation"` علامت شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] git blame مشخص می‌کند چرا این دکمه `بروزرسانی` فاقد handler است
  🎯 معیار قابل-verify: git blame خروجی + توضیح در PR description
- [ ] یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده
  🎯 معیار قابل-verify: تست دستی روی UI + screenshot قبل/بعد
- [ ] اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده
  🎯 معیار قابل-verify: test passing + assertion روی نتیجه کلیک
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: مشخص کن کدام یک از سه حالت بالاست — git blame روی این خط بزن تا commit اصلی + intent اولیه را ببینی.
گام ۲: اگر regression است، handler از commit قبلی را restore کن.
گام ۳: اگر forgotten است، یا feature را کامل پیاده کن یا دکمه را حذف کن.
گام ۴: اگر decorative است، attribute مناسب اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر این دکمه از طریق DOM event delegation در فایل دیگری handle می‌شود، حذف آن سکوت می‌شکند. قبل از حذف، grep روی `data-action`، `data-testid`، یا label/text در کل کدبیس انجام شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: c1fe5cde-a073-4bbd-b780-ce5cc1f95e05, eb442b5b-e8a2-4791-acee-f6175fafed8d, eeecd69a-0df4-4830-af3e-e0e6e3222702, e0514ce1-0b5d-425c-9099-4c62f7263002, 3d4a0007-a5bb-42c3-932b-9e47ae3d4c5a, 9733c833-f8fa-4c2b-b401-dc8446f22fe8, 2a262bff-97b6-4009-97e7-9e4c2386a710, 6a6acb47-b1b6-4ed1-808f-944d9ad101a6`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 8 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به صفحه analysis در فرانت‌اند که از endpointهای اشتباه یا وجود نداشته استفاده می‌کنند. این تسک‌ها به فایل page.tsx و endpointهای بک‌اند مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به صفحه Analysis و endpointهای آن در فرانت‌اند
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 8
  id: c1fe5cde-a073-4bbd-b780-ce5cc1f95e05
  عنوان اصلی: Endpoint `/api/analysis/profiles` در فرانت‌اند فراخوانی می‌شود اما در بک‌اند وجود ندارد
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - پس از اصلاح، تب «پروفایل مدل‌ها» در صفحه تحلیل داده‌های واقعی را نمایش می‌دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]
  - کنسول مرورگر خطای 404 برای این endpoint نشان نمی‌دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 8
  id: eb442b5b-e8a2-4791-acee-f6175fafed8d
  عنوان اصلی: صفحهٔ analysis از endpoint اشتباه برای بارگذاری پروفایل‌ها استفاده می‌کند
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - تب «پروفایل مدل‌ها» در صفحه analysis داده‌های واقعی را نمایش دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]
  - کنسول مرورگر خطای 404 برای /api/analysis/profiles نشان ندهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-model-profiles']"}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 8
  id: eeecd69a-0df4-4830-af3e-e0e6e3222702
  عنوان اصلی: صفحه analysis از endpoint /api/analysis/profiles استفاده می‌کند که وجود ندارد
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "eslint"], "files_hint": ["frontend/"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["tsc", "type-check", "typescript"], "files_hint": ["frontend/"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
صفحه analysis از endpoint /api/analysis/profiles استفاده می‌کند که وجود ندارد

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — این خط باید اصلاح شود
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` — این فایل endpoint صحیح /

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/analysis/page.tsx` (خط 147)، تابع `loadProfiles` از endpoint `GET /api/analysis/profiles` برای دریافت پروفایل مدل‌ها استفاده می‌کند. با این حال، در فایل‌های بک‌اند، هیچ route ای با این مسیر در `backend/app/api/routes/analysis.py` تعریف نشده است. مسیر صحیح برای دریافت پروفایل‌ها احتمالاً `GET /api/models/profiles` است که در `backend/app/api/routes/models.py` (خط 266) تعریف شده است. این باعث می‌شود که درخواست فرانت‌اند با خطای 404 مواجه شود و پروفایل‌ها هرگز بارگذاری نشوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مسیر API در فرانت‌اند را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید تا با endpoint موجود در بک‌اند مطابقت داشته باشد.

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 8
  id: e0514ce1-0b5d-425c-9099-4c62f7263002
  عنوان اصلی: صفحه Analysis (frontend/src/app/analysis/page.tsx) از endpoint منسوخ /api/analysis/profiles استفاده می‌کند
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - صفحه Analysis در تب 'پروفایل مدل‌ها' داده‌ها را نمایش دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-models-profiles']"]
  - کنسول مرورگر خطای 404 ندهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-models-profiles']"]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
صفحه Analysis (frontend/src/app/analysis/page.tsx) از endpoint منسوخ /api/analysis/profiles استفاده می‌کند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — URL اشتباه: باید /api/models/profiles باشد
  ```tsx
  const loadProfiles = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analysis/profiles`);
        if (res.ok) {
          const data = await res.json();
          setProfiles(data || []);
        }
      } catch (e) {
        console.error('Error loading reports:', e);
      }
    };
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + FastAPI

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/models.py` (سطر 266) — endpoint صحیح /api/models/profiles در خط 266 تعریف شده
- `frontend/src/app/model-profiles/page.tsx` (سطر 116) — این صفحه از endpoint صحیح استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
فقط یک fetch call در frontend که باید اصلاح شود.

## 🔍 Context و وضعیت فعلی
در خط 147، تابع loadProfiles از endpoint `/api/analysis/profiles` استفاده می‌کند. این endpoint در backend وجود ندارد. مسیر صحیح `/api/models/profiles` است (که در `backend/app/api/routes/models.py` خط 266 تعریف شده). در نتیجه، تب 'پروفایل مدل‌ها' در صفحه Analysis همیشه خالی می‌ماند و خطای 404 دریافت می‌کند. کاربران نمی‌توانند پروفایل مدل‌ها را از این صفحه مشاهده کنند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] صفحه Analysis در تب 'پروفایل مدل‌ها' داده‌ها را نمایش دهد
- [ ] کنسول مرورگر خطای 404 ندهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. URL تابع loadProfiles را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید.

## 💡 نمونه‌های قبل/بعد
**اصلاح URL**

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
- `صفحه /analysis را باز کنید و به تب 'پروفایل مدل‌ها' بروید`

## ⚠️ ریسک‌ها و موارد احتیاط
ندارد

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 8
  id: 3d4a0007-a5bb-42c3-932b-9e47ae3d4c5a
  عنوان اصلی: Anti-pattern: AI بدون validation (response استفاده می‌شود بدون چ
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["runAnalysis", "loadReports", "loadProfiles", "loadModels"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["schema", "validation", "zod", "yup", "interface", "type guard"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_edge_case", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: AI بدون validation (response استفاده می‌شود بدون چ

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:130`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
در تابع runAnalysis، داده‌های استریم شده از سرور مستقیماً بدون اعتبارسنجی ساختار (schema validation) به state اختصاص داده می‌شوند. اگر سرور داده‌ای با ساختار متفاوت یا فیلدهای ناقص برگرداند، برنامه دچار خطای runtime یا نمایش داده‌های نادرست می‌شود. همچنین در loadReports، loadProfiles و loadModels، پاسخ API بدون بررسی صحت ساختار (مثلاً بررسی وجود فیلدهای ضروری) مستقیماً در state قرار می‌گیرد.

📁 file: frontend/src/app/analysis/page.tsx (line 130)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 8
  id: 9733c833-f8fa-4c2b-b401-dc8446f22fe8
  عنوان اصلی: Anti-pattern: Stale assumption (کد فرض می‌کند رفتار X خاصه، ولی
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["data\\.models", "response\\.body\\?\\.", "getReader\\(\\)"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["TODO", "FIXME", "stale assumption", "//.*edge case"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis_edge_cases.py::test_stale_assumption", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: Stale assumption (کد فرض می‌کند رفتار X خاصه، ولی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:120`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
کد فرض می‌کند که endpointهای API همیشه با ساختار ثابت پاسخ می‌دهند (مثلاً data.models برای لیست مدل‌ها). اگر API تغییر کند (مثلاً فیلد models به models_list تغییر نام دهد)، کد بدون خطای واضح از کار می‌افتد. همچنین فرض شده که response.body?.getReader() همیشه در دسترس است، در حالی که در برخی مرورگرها یا شرایط شبکه ممکن است null باشد.

📁 file: frontend/src/app/analysis/page.tsx (line 120)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 8
  id: 2a262bff-97b6-4009-97e7-9e4c2386a710
  عنوان اصلی: Anti-pattern: Threshold-Outcome mismatch (parameters → نتیجه مطل
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["project_id.*proj_\\$\\{Date\\.now\\(\\)\\}", "selectedModels.*undefined"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["//.*threshold.*outcome.*mismatch", "//.*anti.pattern.*explanation"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_edge_case_invalid_project_id", "timeout_seconds": 60}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
Anti-pattern: Threshold-Outcome mismatch (parameters → نتیجه مطل

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:125`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
پارامترهای ارسالی به API (project_id با مقدار proj_${Date.now()}) ممکن است با انتظارات سرور همخوانی نداشته باشد. اگر سرور نیاز به project_id معتبر از قبل داشته باشد، این مقدار موقت باعث خطا می‌شود. همچنین ارسال selectedModels به صورت undefined در صورت خالی بودن، ممکن است باعث رفتار غیرمنتظره در سرور شود.

📁 file: frontend/src/app/analysis/page.tsx (line 125)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 8
  id: 6a6acb47-b1b6-4ed1-808f-944d9ad101a6
  عنوان اصلی: دکمه‌ی UI بدون handler: بروزرسانی
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - git blame مشخص می‌کند چرا این دکمه `بروزرسانی` فاقد handler است [verify_method=static] [verify_plan={"grep_patterns": ["git blame", "بروزرسانی", "onClick"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده [verify_method=static] [verify_plan={"grep_patterns": ["onClick", "بروزرسانی", "decorative", "disabled"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]
  - اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='update-button']"}, {"a]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
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
دکمه‌ی UI بدون handler: بروزرسانی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
یک دکمه/کنترل UI در فایل `frontend/src/app/analysis/page.tsx` پیدا شد که هیچ event handler معنادار به آن متصل نیست (onClick، onChange، form submit، router push، یا API call شناسایی نشد).

## 🔍 جزئیات
- label/متن دکمه: `بروزرسانی`
- فایل: `frontend/src/app/analysis/page.tsx`
- علت تشخیص stale_detector: button has no onClick handler

## 🤔 چرا مهم است
دکمه بدون handler از دید کاربر کار نمی‌کند و دو حالت دارد:
  ۱) **dead UI**: دکمه از قبل کار می‌کرده و در refactor شکست خورده (regression) — باید handler بازگردانده شود.
  ۲) **forgotten option**: دکمه placeholder بوده و هرگز پیاده‌سازی نشده — باید یا حذف شود یا پیاده‌سازی کامل شود.
  ۳) **decorative**: فقط نمایشی است — باید با `aria-disabled` یا `role="presentation"` علامت شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] git blame مشخص می‌کند چرا این دکمه `بروزرسانی` فاقد handler است
  🎯 معیار قابل-verify: git blame خروجی + توضیح در PR description
- [ ] یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده
  🎯 معیار قابل-verify: تست دستی روی UI + screenshot قبل/بعد
- [ ] اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده
  🎯 معیار قابل-verify: test passing + assertion روی نتیجه کلیک
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: مشخص کن کدام یک از سه حالت بالاست — git blame روی این خط بزن تا commit اصلی + intent اولیه را ببینی.
گام ۲: اگر regression است، handler از commit قبلی را restore کن.
گام ۳: اگر forgotten است، یا feature را کامل پیاده کن یا دکمه را حذف کن.
گام ۴: اگر decorative است، attribute مناسب اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `npm run type-check`
- `npm run lint`
- `npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر این دکمه از طریق DOM event delegation در فایل دیگری handle می‌شود، حذف آن سکوت می‌شکند. قبل از حذف، grep روی `data-action`، `data-testid`، یا label/text در کل کدبیس انجام شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: c1fe5cde-a073-4bbd-b780-ce5cc1f95e05, eb442b5b-e8a2-4791-acee-f6175fafed8d, eeecd69a-0df4-4830-af3e-e0e6e3222702, e0514ce1-0b5d-425c-9099-4c62f7263002, 3d4a0007-a5bb-42c3-932b-9e47ae3d4c5a, 9733c833-f8fa-4c2b-b401-dc8446f22fe8, 2a262bff-97b6-4009-97e7-9e4c2386a710, 6a6acb47-b1b6-4ed1-808f-944d9ad101a6`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. پس از اصلاح، تب «پروفایل مدل‌ها» در صفحه تحلیل داده‌های واقعی را نمایش می‌دهد _(verify: ui_interaction)_
2. کنسول مرورگر خطای 404 برای این endpoint نشان نمی‌دهد _(verify: ui_interaction)_
3. تب «پروفایل مدل‌ها» در صفحه analysis داده‌های واقعی را نمایش دهد _(verify: ui_interaction)_
4. کنسول مرورگر خطای 404 برای /api/analysis/profiles نشان ندهد _(verify: ui_interaction)_
5. اعمال تغییر بدون شکستن تست‌های موجود _(verify: backend_test)_
6. linter بدون warning عبور می‌کند _(verify: static)_
7. type-check موفق است _(verify: static)_
8. صفحه Analysis در تب 'پروفایل مدل‌ها' داده‌ها را نمایش دهد _(verify: ui_interaction)_
9. کنسول مرورگر خطای 404 ندهد _(verify: ui_interaction)_
10. ریشه anti-pattern تشخیص داده شد _(verify: static)_
11. یا کد اصلاح شد، یا کامنت توجیهی اضافه شد _(verify: static)_
12. تست edge case نوشته شد _(verify: backend_test)_
13. git blame مشخص می‌کند چرا این دکمه `بروزرسانی` فاقد handler است _(verify: static)_
14. یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده _(verify: static)_
15. اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده _(verify: ui_interaction)_

## Task Steps

### Step 1: اصلاح endpoint پروفایل‌ها در تابع loadProfiles
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر URL درخواست fetch در تابع loadProfiles از `/api/analysis/profiles` به `/api/models/profiles` در فایل `frontend/src/app/analysis/page.tsx` است. خارج از این مرحله: تغییر سایر endpointها، اصلاح anti-patternها، یا رفع دکمه بدون handler. نکته حیاتی: این تغییر باید با endpoint موجود در بک‌اند (`backend/app/api/routes/models.py` خط 266) مطابقت داشته باشد.
**Excerpt:**
```
تسک 1 از 8
  id: c1fe5cde-a073-4bbd-b780-ce5cc1f95e05
  عنوان اصلی: Endpoint `/api/analysis/profiles` در فرانت‌اند فراخوانی می‌شود اما در بک‌اند وجود ندارد
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - پس از اصلاح، تب «پروفایل مدل‌ها» در صفحه تحلیل داده‌های واقعی را نمایش می‌دهد
  - کنسول مرورگر خطای 404 برای این endpoint نشان نمی‌دهد

---

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
```

### Step 2: اصلاح endpoint پروفایل‌ها در تابع loadProfiles (تسک 2)
**Status:** `pending` (0%)
**Scope:** این مرحله تغییر URL درخواست fetch در تابع loadProfiles از `${API_BASE}/api/analysis/profiles` به `${API_BASE}/api/models/profiles` در فایل `frontend/src/app/analysis/page.tsx` خط 147 است. خارج از این مرحله: تغییر endpointهای دیگر، اصلاح anti-patternها، یا رفع دکمه بدون handler. نکته حیاتی: این تغییر باید با endpoint صحیح در بک‌اند مطابقت داشته باشد.
**Excerpt:**
```
تسک 2 از 8
  id: eb442b5b-e8a2-4791-acee-f6175fafed8d
  عنوان اصلی: صفحهٔ analysis از endpoint اشتباه برای بارگذاری پروفایل‌ها استفاده می‌کند
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - تب «پروفایل مدل‌ها» در صفحه analysis داده‌های واقعی را نمایش دهد
  - کنسول مرورگر خطای 404 برای /api/analysis/profiles نشان ندهد

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — این خط باید اصلاح شود
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```
```

### Step 3: اصلاح endpoint پروفایل‌ها در تابع loadProfiles (تسک 3)
**Status:** `pending` (0%)
**Scope:** این مرحله تغییر مسیر API در فرانت‌اند از `/api/analysis/profiles` به `/api/models/profiles` در فایل `frontend/src/app/analysis/page.tsx` خط 147 است تا با endpoint موجود در بک‌اند مطابقت داشته باشد. خارج از این مرحله: اصلاح endpointهای دیگر، رفع anti-patternها، یا رفع دکمه بدون handler. نکته حیاتی: این تغییر نباید تست‌های موجود را بشکند و باید linter و type-check را پاس کند.
**Excerpt:**
```
تسک 3 از 8
  id: eeecd69a-0df4-4830-af3e-e0e6e3222702
  عنوان اصلی: صفحه analysis از endpoint /api/analysis/profiles استفاده می‌کند که وجود ندارد
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود
  - linter بدون warning عبور می‌کند
  - type-check موفق است

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — این خط باید اصلاح شود
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```
```

### Step 4: اصلاح endpoint پروفایل‌ها در تابع loadProfiles (تسک 4)
**Status:** `pending` (0%)
**Scope:** این مرحله تغییر URL تابع loadProfiles از `/api/analysis/profiles` به `/api/models/profiles` در فایل `frontend/src/app/analysis/page.tsx` خطوط 145-155 است. خارج از این مرحله: اصلاح endpointهای دیگر، رفع anti-patternها، یا رفع دکمه بدون handler. نکته حیاتی: این تغییر باید با endpoint صحیح در بک‌اند مطابقت داشته باشد.
**Excerpt:**
```
تسک 4 از 8
  id: e0514ce1-0b5d-425c-9099-4c62f7263002
  عنوان اصلی: صفحه Analysis (frontend/src/app/analysis/page.tsx) از endpoint منسوخ /api/analysis/profiles استفاده می‌کند
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - صفحه Analysis در تب 'پروفایل مدل‌ها' داده‌ها را نمایش دهد
  - کنسول مرورگر خطای 404 ندهد

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — URL اشتباه: باید /api/models/profiles باشد
  ```tsx
  const loadProfiles = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analysis/profiles`);
        if (res.ok) {
          const data = await res.json();
          setProfiles(data || []);
        }
      } catch (e) {
        console.error('Error loading reports:', e);
      }
    };
  ```
```

### Step 5: رفع anti-pattern: عدم اعتبارسنجی پاسخ API (AI بدون validation)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنگری و اصلاح منطق در تابع‌های `runAnalysis`، `loadReports`، `loadProfiles` و `loadModels` در فایل `frontend/src/app/analysis/page.tsx` است تا پاسخ API قبل از ذخیره در state اعتبارسنجی شود. خارج از این مرحله: اصلاح endpointها، رفع stale assumption، رفع threshold-outcome mismatch، یا رفع دکمه بدون handler. نکته حیاتی: می‌توان از type guard، interface، یا schema validation (مانند zod یا yup) استفاده کرد.
**Excerpt:**
```
تسک 5 از 8
  id: 3d4a0007-a5bb-42c3-932b-9e47ae3d4c5a
  عنوان اصلی: Anti-pattern: AI بدون validation (response استفاده می‌شود بدون چ
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
  - تست edge case نوشته شد

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:130`

## 🔍 Context و وضعیت فعلی
در تابع runAnalysis، داده‌های استریم شده از سرور مستقیماً بدون اعتبارسنجی ساختار (schema validation) به state اختصاص داده می‌شود. اگر سرور داده‌ای با ساختار متفاوت یا فیلدهای ناقص برگرداند، برنامه دچار خطای runtime یا نمایش داده‌های نادرست می‌شود. همچنین در loadReports، loadProfiles و loadModels، پاسخ API بدون بررسی صحت ساختار (مثلاً بررسی وجود فیلدهای ضروری) مستقیماً در state قرار می‌گیرد.
```

### Step 6: رفع anti-pattern: فرض ثابت بودن ساختار پاسخ API (Stale assumption)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنگری و اصلاح منطق در فایل `frontend/src/app/analysis/page.tsx` خط 120 است که فرض می‌کند endpointهای API همیشه با ساختار ثابت پاسخ می‌دهند (مثلاً `data.models`) و `response.body?.getReader()` همیشه در دسترس است. خارج از این مرحله: اصلاح endpointها، رفع AI بدون validation، رفع threshold-outcome mismatch، یا رفع دکمه بدون handler. نکته حیاتی: می‌توان از guard یا کامنت توجیهی استفاده کرد.
**Excerpt:**
```
تسک 6 از 8
  id: 9733c833-f8fa-4c2b-b401-dc8446f22fe8
  عنوان اصلی: Anti-pattern: Stale assumption (کد فرض می‌کند رفتار X خاصه، ولی
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
  - تست edge case نوشته شد

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:120`

## 🔍 Context و وضعیت فعلی
کد فرض می‌کند که endpointهای API همیشه با ساختار ثابت پاسخ می‌دهند (مثلاً data.models برای لیست مدل‌ها). اگر API تغییر کند (مثلاً فیلد models به models_list تغییر نام دهد)، کد بدون خطای واضح از کار می‌افتد. همچنین فرض شده که response.body?.getReader() همیشه در دسترس است، در حالی که در برخی مرورگرها یا شرایط شبکه ممکن است null باشد.
```

### Step 7: رفع anti-pattern: عدم تطابق پارامترها با خروجی (Threshold-Outcome mismatch)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بازنگری و اصلاح منطق در فایل `frontend/src/app/analysis/page.tsx` خط 125 است که پارامترهای ارسالی به API (مانند `project_id` با مقدار `proj_${Date.now()}` و `selectedModels` به صورت `undefined`) ممکن است با انتظارات سرور همخوانی نداشته باشد. خارج از این مرحله: اصلاح endpointها، رفع AI بدون validation، رفع stale assumption، یا رفع دکمه بدون handler. نکته حیاتی: می‌توان از guard یا کامنت توجیهی استفاده کرد.
**Excerpt:**
```
تسک 7 از 8
  id: 2a262bff-97b6-4009-97e7-9e4c2386a710
  عنوان اصلی: Anti-pattern: Threshold-Outcome mismatch (parameters → نتیجه مطل
  اولویت اصلی: high
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
  - تست edge case نوشته شد

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:125`

## 🔍 Context و وضعیت فعلی
پارامترهای ارسالی به API (project_id با مقدار proj_${Date.now()}) ممکن است با انتظارات سرور همخوانی نداشته باشد. اگر سرور نیاز به project_id معتبر از قبل داشته باشد، این مقدار موقت باعث خطا می‌شود. همچنین ارسال selectedModels به صورت undefined در صورت خالی بودن، ممکن است باعث رفتار غیرمنتظره در سرور شود.
```

### Step 8: رفع دکمه UI بدون handler: بروزرسانی
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی و رفع دکمه «بروزرسانی» در فایل `frontend/src/app/analysis/page.tsx` است که فاقد event handler معنادار (onClick) است. خارج از این مرحله: اصلاح endpointها، رفع anti-patternها. نکته حیاتی: باید یکی از سه حالت زیر تعیین شود: (a) handler restore شده و کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده. قبل از حذف، باید با grep بررسی شود که دکمه از طریق DOM event delegation در فایل دیگری handle نمی‌شود.
**Excerpt:**
```
تسک 8 از 8
  id: 6a6acb47-b1b6-4ed1-808f-944d9ad101a6
  عنوان اصلی: دکمه‌ی UI بدون handler: بروزرسانی
  اولویت اصلی: medium
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - git blame مشخص می‌کند چرا این دکمه `بروزرسانی` فاقد handler است
  - یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده
  - اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده

---

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx`

## 🔍 Context و وضعیت فعلی
## 📋 شرح
یک دکمه/کنترل UI در فایل `frontend/src/app/analysis/page.tsx` پیدا شد که هیچ event handler معنادار به آن متصل نیست (onClick، onChange، form submit، router push، یا API call شناسایی نشد).

## 🔍 جزئیات
- label/متن دکمه: `بروزرسانی`
- فایل: `frontend/src/app/analysis/page.tsx`
- علت تشخیص stale_detector: button has no onClick handler
```
