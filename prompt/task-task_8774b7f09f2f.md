---
task_id: task_8774b7f09f2f
title: 'تلفیق: mechanical:files (2 تسک)'
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:29:46.437938+00:00'
updated_at: '2026-05-20T04:28:36.766902+00:00'
tags:
- consolidated
- post_verify_merge
---

# تلفیق: mechanical:files (2 تسک)

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): اشتراک فایل با Jaccard ≥ 0.5
🎯 theme: mechanical:files
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: d373a01f-167a-4765-aa96-a344e066681d
  عنوان اصلی: Endpoint `/api/analysis/profiles` در فرانت‌اند با مسیر backend ناهمخوان است
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - تب 'پروفایل مدل‌ها' در صفحه تحلیل، لیست پروفایل‌ها را از backend دریافت و نمایش دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-profiles']"}, {"ac]
  - درخواست شبکه به `/api/models/profiles` ارسال شود، نه `/api/analysis/profiles` [verify_method=static] [verify_plan={"grep_patterns": ["/api/models/profiles"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]

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
Endpoint `/api/analysis/profiles` در فرانت‌اند با مسیر backend ناهمخوان است

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — مسیر API اشتباه است
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

- `backend/app/api/routes/models.py` (سطر 266) — مسیر صحیح GET /api/models/profiles در اینجا تعریف شده
- `backend/app/api/routes/model_profiles.py` (سطر 142) — مسیر جایگزین GET /api/models/profiles در اینجا تعریف شده

## 🌐 نقشهٔ وابستگی‌ها
این باگ فقط روی صفحه تحلیل (analysis page) تأثیر می‌گذارد و باعث می‌شود تب پروفایل مدل‌ها داده‌ای نمایش ندهد.

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/analysis/page.tsx` خط ۱۴۷، فرانت‌اند برای بارگذاری پروفایل‌های مدل از `GET /api/analysis/profiles` استفاده می‌کند. اما در backend، این مسیر وجود ندارد. مسیر صحیح برای دریافت پروفایل‌ها `GET /api/models/profiles` است (تعریف‌شده در `backend/app/api/routes/models.py` خط ۲۶۶). این mismatch باعث می‌شود تب 'profiles' در صفحه تحلیل هیچ داده‌ای بارگذاری نکند و کاربر داده‌های خالی یا خطا ببیند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تب 'پروفایل مدل‌ها' در صفحه تحلیل، لیست پروفایل‌ها را از backend دریافت و نمایش دهد
- [ ] درخواست شبکه به `/api/models/profiles` ارسال شود، نه `/api/analysis/profiles`
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مسیر API در فرانت‌اند را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید تا با backend هماهنگ شود.

## 💡 نمونه‌های قبل/بعد
**اصلاح مسیر API**

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
- `curl -X GET http://localhost:8000/api/models/profiles`
- `curl -X GET http://localhost:8000/api/analysis/profiles (باید 404 برگرداند)`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر بسیار کم‌خطر است و فقط یک URL را اصلاح می‌کند.

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
تسک 2 از 2
  id: 5bc92b07-e703-466f-9249-dd58d96c9638
  عنوان اصلی: Frontend analysis page calls /api/analysis/profiles but backend serves it at /api/models/profiles
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/models.py, frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - Analysis page profile tab loads real data from backend instead of fallback defaults [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='profile-tab']", "ti]
  - No 404 errors in browser console when navigating to analysis page [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='profile-tab']", "ti]
  - Backend /api/models/profiles endpoint accepts use_fallback query parameter [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/models/profiles", "headers": null, "json_body": null, "expected_status": 200, "required_fields": ["profiles"], "json_contains": null, "query_params": {"use_fallback": "]

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
Frontend analysis page calls /api/analysis/profiles but backend serves it at /api/models/profiles

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — Wrong endpoint - should be /api/models/profiles
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```
- `backend/app/api/routes/models.py:266-286` — `get_model_profiles` — Backend endpoint - needs use_fallback parameter support
  ```python
  @router.get("/profiles")
  async def get_model_profiles():
      try:
          from ...services.model_profiler import get_model_profiler
          profiler = get_model_profiler()
          profiles = profiler.get_all_profiles()
          profiles_data = [p.model_dump() for p in profiles]
          return {
              "success": True,
              "profiles": profiles_data,
              "count": len(profiles_data),
              "is_fallback": len(profiles_data) == 0
          }
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router frontend + FastAPI backend with multiple route files

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `frontend/src/app/model-profiles/page.tsx` (سطر 116) — This page correctly uses /api/models/profiles but sends use_fallback=false
- `backend/app/api/routes/model_profiles.py` (سطر 142) — Alternative route file that also defines /api/models/profiles
- `backend/app/core/database.py` — `models.py` این فایل را import می‌کند
- `backend/app/core/models_registry.py` — `models.py` این فایل را import می‌کند
- `backend/app/services/ai_manager.py` — `models.py` این فایل را import می‌کند
- `backend/app/models/ai_profile.py` — `models.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `models.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
The analysis page's profile tab will always show fallback data because the API call fails silently. This affects user experience when viewing real model performance data.

## 🔍 Context و وضعیت فعلی
In `frontend/src/app/analysis/page.tsx` line 147, the frontend fetches from `${API_BASE}/api/analysis/profiles` to load AI model profiles. However, the backend route for model profiles is defined in `backend/app/api/routes/model_profiles.py` with prefix `/api/models` (line 50: `router = APIRouter(prefix="/api/models", tags=["model-profiles"])`), and the actual endpoint is `/api/models/profiles`. Additionally, `backend/app/api/routes/models.py` line 266 defines a `/profiles` endpoint under the `/models` prefix. This mismatch causes the frontend to receive a 404 error when loading profiles, resulting in fallback to default data (lines 130-137). The same issue exists in `frontend/src/app/model-profiles/page.tsx` line 116 which correctly uses `/api/models/profiles` but with `use_fallback=false` parameter that may not be supported by the backend.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] Analysis page profile tab loads real data from backend instead of fallback defaults
- [ ] No 404 errors in browser console when navigating to analysis page
- [ ] Backend /api/models/profiles endpoint accepts use_fallback query parameter
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. Change the frontend API call in `frontend/src/app/analysis/page.tsx` line 147 from `${API_BASE}/api/analysis/profiles` to `${API_BASE}/api/models/profiles`. Also ensure the backend endpoint at `backend/app/api/routes/models.py` line 266-286 properly supports the `use_fallback` query parameter that the frontend sends.

## 💡 نمونه‌های قبل/بعد
**Fix frontend endpoint**

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
- `curl -s http://localhost:8000/api/models/profiles | jq '.success'`
- `Check browser console for 404 errors on analysis page load`

## ⚠️ ریسک‌ها و موارد احتیاط
Minimal - only changes a URL string and adds a query parameter handler

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
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: d373a01f-167a-4765-aa96-a344e066681d, 5bc92b07-e703-466f-9249-dd58d96c9638`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): اشتراک فایل با Jaccard ≥ 0.5
🎯 theme: mechanical:files
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: d373a01f-167a-4765-aa96-a344e066681d
  عنوان اصلی: Endpoint `/api/analysis/profiles` در فرانت‌اند با مسیر backend ناهمخوان است
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - تب 'پروفایل مدل‌ها' در صفحه تحلیل، لیست پروفایل‌ها را از backend دریافت و نمایش دهد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='tab-profiles']"}, {"ac]
  - درخواست شبکه به `/api/models/profiles` ارسال شود، نه `/api/analysis/profiles` [verify_method=static] [verify_plan={"grep_patterns": ["/api/models/profiles"], "files_hint": ["frontend/src/app/analysis/page.tsx"]}]

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
Endpoint `/api/analysis/profiles` در فرانت‌اند با مسیر backend ناهمخوان است

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:145-155` — `loadProfiles` — مسیر API اشتباه است
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

- `backend/app/api/routes/models.py` (سطر 266) — مسیر صحیح GET /api/models/profiles در اینجا تعریف شده
- `backend/app/api/routes/model_profiles.py` (سطر 142) — مسیر جایگزین GET /api/models/profiles در اینجا تعریف شده

## 🌐 نقشهٔ وابستگی‌ها
این باگ فقط روی صفحه تحلیل (analysis page) تأثیر می‌گذارد و باعث می‌شود تب پروفایل مدل‌ها داده‌ای نمایش ندهد.

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/analysis/page.tsx` خط ۱۴۷، فرانت‌اند برای بارگذاری پروفایل‌های مدل از `GET /api/analysis/profiles` استفاده می‌کند. اما در backend، این مسیر وجود ندارد. مسیر صحیح برای دریافت پروفایل‌ها `GET /api/models/profiles` است (تعریف‌شده در `backend/app/api/routes/models.py` خط ۲۶۶). این mismatch باعث می‌شود تب 'profiles' در صفحه تحلیل هیچ داده‌ای بارگذاری نکند و کاربر داده‌های خالی یا خطا ببیند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تب 'پروفایل مدل‌ها' در صفحه تحلیل، لیست پروفایل‌ها را از backend دریافت و نمایش دهد
- [ ] درخواست شبکه به `/api/models/profiles` ارسال شود، نه `/api/analysis/profiles`
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مسیر API در فرانت‌اند را از `/api/analysis/profiles` به `/api/models/profiles` تغییر دهید تا با backend هماهنگ شود.

## 💡 نمونه‌های قبل/بعد
**اصلاح مسیر API**

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
- `curl -X GET http://localhost:8000/api/models/profiles`
- `curl -X GET http://localhost:8000/api/analysis/profiles (باید 404 برگرداند)`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر بسیار کم‌خطر است و فقط یک URL را اصلاح می‌کند.

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
تسک 2 از 2
  id: 5bc92b07-e703-466f-9249-dd58d96c9638
  عنوان اصلی: Frontend analysis page calls /api/analysis/profiles but backend serves it at /api/models/profiles
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/models.py, frontend/src/app/analysis/page.tsx

📋 acceptance_criteria کامل:
  - Analysis page profile tab loads real data from backend instead of fallback defaults [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='profile-tab']", "ti]
  - No 404 errors in browser console when navigating to analysis page [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/analysis"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='profile-tab']", "ti]
  - Backend /api/models/profiles endpoint accepts use_fallback query parameter [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/models/profiles", "headers": null, "json_body": null, "expected_status": 200, "required_fields": ["profiles"], "json_contains": null, "query_params": {"use_fallback": "]

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
Frontend analysis page calls /api/analysis/profiles but backend serves it at /api/models/profiles

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/analysis/page.tsx:147` — `loadProfiles` — Wrong endpoint - should be /api/models/profiles
  ```tsx
  const res = await fetch(`${API_BASE}/api/analysis/profiles`);
  ```
- `backend/app/api/routes/models.py:266-286` — `get_model_profiles` — Backend endpoint - needs use_fallback parameter support
  ```python
  @router.get("/profiles")
  async def get_model_profiles():
      try:
          from ...services.model_profiler import get_model_profiler
          profiler = get_model_profiler()
          profiles = profiler.get_all_profiles()
          profiles_data = [p.model_dump() for p in profiles]
          return {
              "success": True,
              "profiles": profiles_data,
              "count": len(profiles_data),
              "is_fallback": len(profiles_data) == 0
          }
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router frontend + FastAPI backend with multiple route files

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `frontend/src/app/model-profiles/page.tsx` (سطر 116) — This page correctly uses /api/models/profiles but sends use_fallback=false
- `backend/app/api/routes/model_profiles.py` (سطر 142) — Alternative route file that also defines /api/models/profiles
- `backend/app/core/database.py` — `models.py` این فایل را import می‌کند
- `backend/app/core/models_registry.py` — `models.py` این فایل را import می‌کند
- `backend/app/services/ai_manager.py` — `models.py` این فایل را import می‌کند
- `backend/app/models/ai_profile.py` — `models.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `models.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
The analysis page's profile tab will always show fallback data because the API call fails silently. This affects user experience when viewing real model performance data.

## 🔍 Context و وضعیت فعلی
In `frontend/src/app/analysis/page.tsx` line 147, the frontend fetches from `${API_BASE}/api/analysis/profiles` to load AI model profiles. However, the backend route for model profiles is defined in `backend/app/api/routes/model_profiles.py` with prefix `/api/models` (line 50: `router = APIRouter(prefix="/api/models", tags=["model-profiles"])`), and the actual endpoint is `/api/models/profiles`. Additionally, `backend/app/api/routes/models.py` line 266 defines a `/profiles` endpoint under the `/models` prefix. This mismatch causes the frontend to receive a 404 error when loading profiles, resulting in fallback to default data (lines 130-137). The same issue exists in `frontend/src/app/model-profiles/page.tsx` line 116 which correctly uses `/api/models/profiles` but with `use_fallback=false` parameter that may not be supported by the backend.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] Analysis page profile tab loads real data from backend instead of fallback defaults
- [ ] No 404 errors in browser console when navigating to analysis page
- [ ] Backend /api/models/profiles endpoint accepts use_fallback query parameter
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. Change the frontend API call in `frontend/src/app/analysis/page.tsx` line 147 from `${API_BASE}/api/analysis/profiles` to `${API_BASE}/api/models/profiles`. Also ensure the backend endpoint at `backend/app/api/routes/models.py` line 266-286 properly supports the `use_fallback` query parameter that the frontend sends.

## 💡 نمونه‌های قبل/بعد
**Fix frontend endpoint**

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
- `curl -s http://localhost:8000/api/models/profiles | jq '.success'`
- `Check browser console for 404 errors on analysis page load`

## ⚠️ ریسک‌ها و موارد احتیاط
Minimal - only changes a URL string and adds a query parameter handler

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
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: d373a01f-167a-4765-aa96-a344e066681d, 5bc92b07-e703-466f-9249-dd58d96c9638`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. تب 'پروفایل مدل‌ها' در صفحه تحلیل، لیست پروفایل‌ها را از backend دریافت و نمایش دهد _(verify: ui_interaction)_
2. درخواست شبکه به `/api/models/profiles` ارسال شود، نه `/api/analysis/profiles` _(verify: static)_
3. Analysis page profile tab loads real data from backend instead of fallback defaults _(verify: ui_interaction)_
4. No 404 errors in browser console when navigating to analysis page _(verify: ui_interaction)_
5. Backend /api/models/profiles endpoint accepts use_fallback query parameter _(verify: api_response)_

## Task Steps

### Step 1: اصلاح مسیر API در فرانت‌اند analysis/page.tsx از `/api/analysis/profiles` به `/api/models/profiles`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر یک خط کد در فایل frontend/src/app/analysis/page.tsx است: در تابع loadProfiles، آدرس fetch از `${API_BASE}/api/analysis/profiles` به `${API_BASE}/api/models/profiles` تغییر می‌کند. هیچ تغییر دیگری در این فایل یا فایل‌های دیگر انجام نمی‌شود. نکته حیاتی: این تغییر باید دقیقاً در خط ۱۴۷ (یا نزدیک‌ترین خط معادل) انجام شود و مطمئن شوید که هیچ ارجاع دیگری به `/api/analysis/profiles` در این فایل باقی نمانده است.
**Excerpt:**
```
در `frontend/src/app/analysis/page.tsx` خط ۱۴۷، فرانت‌اند برای بارگذاری پروفایل‌های مدل از `GET /api/analysis/profiles` استفاده می‌کند. اما در backend، این مسیر وجود ندارد. مسیر صحیح برای دریافت پروفایل‌ها `GET /api/models/profiles` است (تعریف‌شده در `backend/app/api/routes/models.py` خط ۲۶۶). این mismatch باعث می‌شود تب 'profiles' در صفحه تحلیل هیچ داده‌ای بارگذاری نکند و کاربر داده‌های خالی یا خطا ببیند.

**اصلاح مسیر API**
_قبل:_
```
const res = await fetch(`${API_BASE}/api/analysis/profiles`);
```
_بعد:_
```
const res = await fetch(`${API_BASE}/api/models/profiles`);
```
```

### Step 2: اضافه کردن پشتیبانی از query parameter `use_fallback` در endpoint backend `/api/models/profiles`
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر فایل backend/app/api/routes/models.py (یا backend/app/api/routes/model_profiles.py بسته به اینکه کدام endpoint واقعاً استفاده می‌شود) است. تابع get_model_profiles باید یک پارامتر query اختیاری `use_fallback: bool = False` دریافت کند. اگر use_fallback=True باشد، endpoint باید داده‌های fallback (پیش‌فرض) را برگرداند. اگر use_fallback=False (یا وجود نداشته باشد)، باید داده‌های واقعی از profiler دریافت شود. نکته حیاتی: باید بررسی کنید که frontend در کدام فایل‌ها از این query parameter استفاده می‌کند (frontend/src/app/model-profiles/page.tsx خط ۱۱۶ از use_fallback=false استفاده می‌کند) و مطمئن شوید که backend این پارامتر را به درستی پردازش می‌کند.
**Excerpt:**
```
Backend /api/models/profiles endpoint accepts use_fallback query parameter [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/models/profiles", "headers": null, "json_body": null, "expected_status": 200, "required_fields": ["profiles"], "json_contains": null, "query_params": {"use_fallback": "..."}]

- `backend/app/api/routes/models.py:266-286` — `get_model_profiles` — Backend endpoint - needs use_fallback parameter support
  ```python
  @router.get("/profiles")
  async def get_model_profiles():
      try:
          from ...services.model_profiler import get_model_profiler
          profiler = get_model_profiler()
          profiles = profiler.get_all_profiles()
          profiles_data = [p.model_dump() for p in profiles]
          return {
              "success": True,
              "profiles": profiles_data,
              "count": len(profiles_data),
              "is_fallback": len(profiles_data) == 0
          }
  ```
- `frontend/src/app/model-profiles/page.tsx` (سطر 116) — This page correctly uses /api/models/profiles but sends use_fallback=false
```

### Step 3: بررسی و رفع ناهماهنگی‌های احتمالی در فایل‌های backend تکراری (models.py و model_profiles.py)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی دو فایل backend است که هر دو endpoint `/api/models/profiles` را تعریف می‌کنند: backend/app/api/routes/models.py و backend/app/api/routes/model_profiles.py. باید مشخص شود کدام یک از این دو endpoint واقعاً در حال استفاده است (بر اساس importها در main.py و سایر فایل‌ها). اگر هر دو فعال باشند، ممکن است conflict ایجاد شود. در صورت وجود conflict، باید یکی از آن‌ها را غیرفعال یا حذف کرد. نکته حیاتی: تغییرات باید به گونه‌ای باشد که هیچ endpoint تکراری با مسیر یکسان وجود نداشته باشد.
**Excerpt:**
```
- `backend/app/api/routes/models.py` (سطر 266) — مسیر صحیح GET /api/models/profiles در اینجا تعریف شده
- `backend/app/api/routes/model_profiles.py` (سطر 142) — مسیر جایگزین GET /api/models/profiles در اینجا تعریف شده

- `backend/app/main.py` — این فایل `models.py` را import می‌کند (caller)
- `backend/app/core/database.py` — `models.py` این فایل را import می‌کند
- `backend/app/core/models_registry.py` — `models.py` این فایل را import می‌کند
- `backend/app/services/ai_manager.py` — `models.py` این فایل را import می‌کند
- `backend/app/models/ai_profile.py` — `models.py` این فایل را import می‌کند
```

### Step 4: اجرای تست‌های backend (pytest) و اطمینان از عبور همه تست‌ها
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های backend با دستور `pytest` است. باید مطمئن شوید که هیچ تستی به دلیل تغییرات ایجادشده fail نمی‌شود. اگر تست‌های موجود برای endpoint `/api/models/profiles` وجود دارند، باید آن‌ها را بررسی کنید تا با تغییرات جدید (پشتیبانی از use_fallback) سازگار باشند. در صورت نیاز، تست‌های موجود را به‌روزرسانی کنید. نکته حیاتی: اگر تستی fail شد، باید علت را بررسی و رفع کنید، نه اینکه تست را حذف کنید.
**Excerpt:**
```
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🧪 دستورات اعتبارسنجی
- `curl -X GET http://localhost:8000/api/models/profiles`
- `curl -X GET http://localhost:8000/api/analysis/profiles (باید 404 برگرداند)`
```

### Step 5: اجرای linter و type-check برای frontend و backend و رفع warnings
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای linter (مثلاً ESLint برای frontend و flake8/pylint برای backend) و type-checker (tsc --noEmit برای frontend و mypy برای backend) است. باید مطمئن شوید که هیچ warning یا خطایی وجود ندارد. اگر تغییرات ایجادشده باعث warning جدید شده است، آن‌ها را رفع کنید. نکته حیاتی: اگر linter یا type-checker قبلاً warning داشت که مربوط به تغییرات شما نیست، آن‌ها را نادیده بگیرید و فقط warningهای جدید را رفع کنید.
**Excerpt:**
```
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)
```

### Step 6: تأیید نهایی با تست دستی: curl به endpoint قدیمی باید 404 برگرداند
**Status:** `pending` (0%)
**Scope:** این مرحله شامل یک تست دستی نهایی است: با دستور `curl -X GET http://localhost:8000/api/analysis/profiles` بررسی کنید که endpoint قدیمی (که frontend قبلاً استفاده می‌کرد) دیگر وجود ندارد و باید پاسخ 404 برگرداند. این تأیید می‌کند که تغییر مسیر در frontend صحیح است و هیچ endpoint قدیمی‌ای باقی نمانده است. نکته حیاتی: این تست باید بعد از راه‌اندازی مجدد سرور backend انجام شود.
**Excerpt:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X GET http://localhost:8000/api/models/profiles`
- `curl -X GET http://localhost:8000/api/analysis/profiles (باید 404 برگرداند)`
```
