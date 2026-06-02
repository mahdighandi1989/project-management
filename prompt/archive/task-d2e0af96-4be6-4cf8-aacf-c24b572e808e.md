---
task_id: d2e0af96-4be6-4cf8-aacf-c24b572e808e
title: پروفایل مدل‌ها فقط داده‌های نمایشی (mock) برمی‌گرداند — هیچ داده‌ای از تحلیل‌های واقعی جمع‌آوری نمی‌شود
type: bug
priority: high
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T05:09:14.831252+00:00'
updated_at: '2026-06-02T17:42:33.377123+00:00'
archived: true
archived_at: '2026-05-17T10:26:30.324846+00:00'
target_files:
- frontend/src/app/model-profiles/page.tsx
- backend/app/api/routes/model_profiles.py
- backend/app/api/routes/models.py
---

# پروفایل مدل‌ها فقط داده‌های نمایشی (mock) برمی‌گرداند — هیچ داده‌ای از تحلیل‌های واقعی جمع‌آوری نمی‌شود

## Raw Idea

در `frontend/src/app/model-profiles/page.tsx` (خطوط 90-97 و 99-105)، یک `defaultProfiles` و `defaultLeaderboard` هاردکد شده وجود دارد که وقتی API پاسخ واقعی نمی‌دهد (مثلاً دیتابیس خالی است یا خطا دارد) استفاده می‌شود. در `backend/app/api/routes/model_profiles.py` (خطوط 157-173 و 189-200) هم یک fallback به `_get_default_profile_list()` وجود دارد که داده‌های ساختگی برمی‌گرداند. این یعنی سیستم هرگز داده‌های واقعی از تحلیل‌های سلامت پروژه را جمع‌آوری و ذخیره نمی‌کند — پروفایل‌ها همیشه نمایشی هستند. در `backend/app/api/routes/models.py` (خطوط 266-286) endpoint `/profiles` از `model_profiler.get_all_profiles()` استفاده می‌کند که اگر خالی باشد، fallback می‌خورد. در `backend/app/services/model_profiler.py` (که در لیست فایل‌ها موجود است) احتمالاً داده‌ها از دیتابیس خوانده می‌شوند ولی هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.

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
پروفایل مدل‌ها فقط داده‌های نمایشی (mock) برمی‌گرداند — هیچ داده‌ای از تحلیل‌های واقعی جمع‌آوری نمی‌شود

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/model-profiles/page.tsx:90-97` — `defaultProfiles` — داده‌های نمایشی هاردکد شده — باید با داده‌های واقعی از API جایگزین شود
  ```tsx
  const defaultProfiles: ModelProfile[] = [
      {model_id: "gpt-4", provider: "openai", display_name: "GPT-4", tier: "S", overall_score: 92.5, ...},
      ...
    ];
  ```
- `backend/app/api/routes/model_profiles.py:157-173` — `get_all_profiles` — Fallback به داده‌های پیش‌فرض به جای خطای واقعی
  ```python
  if not DB_AVAILABLE or not MODELS_AVAILABLE or db is None:
          if use_fallback:
              return {
                  "success": True,
                  "profiles": _get_default_profile_list(),
                  ...
              }
  ```
- `backend/app/api/routes/models.py:266-286` — `get_model_profiles` — اگر profiler خالی باشد، fallback به داده‌های خالی — هیچ داده‌ای ساخته نمی‌شود
  ```python
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
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/model_profiler.py` (سطر 1) — سرویس اصلی که پروفایل‌ها را مدیریت می‌کند — باید داده‌ها را از تحلیل‌ها پر کند
- `backend/app/services/project_health_analyzer.py` (سطر 1) — بعد از هر تحلیل سلامت، باید نتایج را به model_profiler بفرستد

## 🔍 Context و وضعیت فعلی
در `frontend/src/app/model-profiles/page.tsx` (خطوط 90-97 و 99-105)، یک `defaultProfiles` و `defaultLeaderboard` هاردکد شده وجود دارد که وقتی API پاسخ واقعی نمی‌دهد (مثلاً دیتابیس خالی است یا خطا دارد) استفاده می‌شود. در `backend/app/api/routes/model_profiles.py` (خطوط 157-173 و 189-200) هم یک fallback به `_get_default_profile_list()` وجود دارد که داده‌های ساختگی برمی‌گرداند. این یعنی سیستم هرگز داده‌های واقعی از تحلیل‌های سلامت پروژه را جمع‌آوری و ذخیره نمی‌کند — پروفایل‌ها همیشه نمایشی هستند. در `backend/app/api/routes/models.py` (خطوط 266-286) endpoint `/profiles` از `model_profiler.get_all_profiles()` استفاده می‌کند که اگر خالی باشد، fallback می‌خورد. در `backend/app/services/model_profiler.py` (که در لیست فایل‌ها موجود است) احتمالاً داده‌ها از دیتابیس خوانده می‌شوند ولی هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. یک pipeline خودکار ایجاد کن که بعد از هر تحلیل سلامت پروژه (در `project_health_analyzer` یا `deep_analysis_service`)، نتایج را به `model_profiler` بفرستد تا پروفایل‌ها به‌روز شوند. همچنین یک endpoint برای بازسازی پروفایل‌ها از تاریخچه لاگ‌های فعالیت (ActivityLog) اضافه کن.

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

## Task Steps

### Step 1: حذف fallback به داده‌های پیش‌فرض در backend endpoint model_profiles و بازگرداندن خطای واقعی
**Status:** `done` (100%)
**Scope:** در فایل backend/app/api/routes/model_profiles.py، خطوط 157-173 که شامل fallback به _get_default_profile_list() است باید اصلاح شود. به جای بازگرداندن داده‌های ساختگی وقتی DB_AVAILABLE یا MODELS_AVAILABLE False است یا db None است، باید یک خطای HTTP 503 یا 500 با پیام مناسب بازگرداند. این مرحله فقط مربوط به endpoint /api/model-profiles است و شامل endpoint /profiles در models.py نمی‌شود. نکته حیاتی: باید مطمئن شویم که این تغییر باعث نمی‌شود frontend crash کند — frontend باید بعداً برای handling خطا آماده شود.
**Excerpt:**
```
در `backend/app/api/routes/model_profiles.py` (خطوط 157-173 و 189-200) هم یک fallback به `_get_default_profile_list()` وجود دارد که داده‌های ساختگی برمی‌گرداند. ... if not DB_AVAILABLE or not MODELS_AVAILABLE or db is None: if use_fallback: return { "success": True, "profiles": _get_default_profile_list(), ... }
```

### Step 2: حذف fallback به داده‌های خالی در endpoint /profiles و بازگرداندن خطای واقعی
**Status:** `done` (100%)
**Scope:** در فایل backend/app/api/routes/models.py، خطوط 266-286 که endpoint /profiles را تعریف می‌کند، باید اصلاح شود. به جای بازگرداندن داده‌های خالی با is_fallback=True وقتی profiler.get_all_profiles() خالی است، باید یک خطای HTTP 404 یا 204 با پیام 'No profiles found' بازگرداند. این مرحله فقط مربوط به endpoint /profiles است. نکته حیاتی: باید مطمئن شویم که profiler.get_all_profiles() واقعاً داده‌های دیتابیس را می‌خواند و fallback نمی‌کند.
**Excerpt:**
```
در `backend/app/api/routes/models.py` (خطوط 266-286) endpoint `/profiles` از `model_profiler.get_all_profiles()` استفاده می‌کند که اگر خالی باشد، fallback می‌خورد. ... profiles = profiler.get_all_profiles() profiles_data = [p.model_dump() for p in profiles] return { "success": True, "profiles": profiles_data, "count": len(profiles_data), "is_fallback": len(profiles_data) == 0 }
```

### Step 3: حذف داده‌های هاردکد شده defaultProfiles و defaultLeaderboard در frontend و نمایش خطا از API
**Status:** `done` (100%)
**Scope:** در فایل frontend/src/app/model-profiles/page.tsx، خطوط 90-97 که defaultProfiles هاردکد شده است و خطوط 99-105 که defaultLeaderboard هاردکد شده است باید حذف شوند. به جای استفاده از این داده‌ها وقتی API خطا می‌دهد، frontend باید خطای API را نمایش دهد (مثلاً یک پیام 'No data available' یا 'Error loading profiles'). این مرحله شامل اصلاح منطق fetch data در frontend است تا از داده‌های ساختگی استفاده نکند. نکته حیاتی: frontend باید خطاهای HTTP 503 و 404 را به درستی handling کند.
**Excerpt:**
```
در `frontend/src/app/model-profiles/page.tsx` (خطوط 90-97 و 99-105)، یک `defaultProfiles` و `defaultLeaderboard` هاردکد شده وجود دارد که وقتی API پاسخ واقعی نمی‌دهد (مثلاً دیتابیس خالی است یا خطا دارد) استفاده می‌شود. ... const defaultProfiles: ModelProfile[] = [ {model_id: "gpt-4", provider: "openai", display_name: "GPT-4", tier: "S", overall_score: 92.5, ...}, ... ];
```

### Step 4: بررسی و اصلاح backend/app/services/model_profiler.py برای اطمینان از خواندن داده‌های واقعی از دیتابیس
**Status:** `done` (100%)
**Scope:** فایل backend/app/services/model_profiler.py باید بررسی شود تا مطمئن شویم متد get_all_profiles() داده‌ها را از دیتابیس واقعی می‌خواند و fallback به داده‌های ساختگی ندارد. اگر fallback وجود دارد، باید حذف شود. همچنین باید مطمئن شویم که این سرویس داده‌ها را از جدول profiles در دیتابیس می‌خواند. نکته حیاتی: اگر سرویس از دیتابیس نمی‌خواند، باید اصلاح شود تا از session دیتابیس استفاده کند.
**Excerpt:**
```
در `backend/app/services/model_profiler.py` (که در لیست فایل‌ها موجود است) احتمالاً داده‌ها از دیتابیس خوانده می‌شوند ولی هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.
```

### Step 5: ایجاد فرآیند پر کردن خودکار پروفایل‌ها از نتایج تحلیل‌های سلامت پروژه
**Status:** `done` (100%)
**Scope:** یک فرآیند (مثلاً یک تابع یا سرویس جدید) باید ایجاد شود که پس از اتمام تحلیل‌های سلامت پروژه، نتایج را به پروفایل‌های مدل تبدیل کرده و در دیتابیس ذخیره کند. این فرآیند باید در backend/app/services/model_profiler.py یا یک فایل جدید مانند backend/app/services/profile_populator.py قرار گیرد. این فرآیند باید از نتایج تحلیل‌ها (مثلاً از جدول analysis_results یا هر جدول دیگری که نتایج تحلیل‌ها را ذخیره می‌کند) استفاده کند. نکته حیاتی: باید مشخص شود که نتایج تحلیل‌ها در کدام جدول/سرویس ذخیره می‌شوند و چگونه به پروفایل تبدیل می‌شوند.
**Excerpt:**
```
هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.
```

### Step 6: اتصال فرآیند پرکننده پروفایل به pipeline تحلیل سلامت پروژه
**Status:** `done` (100%)
**Scope:** فرآیند ایجاد شده در مرحله 5 باید به pipeline تحلیل سلامت پروژه متصل شود. یعنی بعد از اینکه یک تحلیل کامل شد (مثلاً در endpoint یا سرویس مربوطه)، تابع populate_profile فراخوانی شود. این اتصال باید در جایی انجام شود که تحلیل‌ها اجرا می‌شوند (مثلاً در backend/app/api/routes/analysis.py یا backend/app/services/analysis_service.py). نکته حیاتی: باید مطمئن شویم که این فراخوانی خطاهای تحلیل را تحت تأثیر قرار نمی‌دهد.
**Excerpt:**
```
هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.
```

### Step 7: نوشتن تست‌های واحد برای backend endpoint model_profiles بدون fallback
**Status:** `done` (100%)
**Scope:** تست‌های واحد برای endpoint /api/model-profiles در backend/app/api/routes/model_profiles.py باید نوشته شود تا اطمینان حاصل شود که: 1) وقتی دیتابیس در دسترس است و داده وجود دارد، داده‌ها برگردانده می‌شوند. 2) وقتی دیتابیس در دسترس نیست، خطای 503 برگردانده می‌شود. 3) وقتی دیتابیس خالی است، خطای 404 برگردانده می‌شود. این تست‌ها باید در فایل tests/test_model_profiles.py یا مشابه قرار گیرند. نکته حیاتی: تست‌ها باید از mocking برای شبیه‌سازی شرایط مختلف استفاده کنند.
**Excerpt:**
```
در `backend/app/api/routes/model_profiles.py` (خطوط 157-173 و 189-200) هم یک fallback به `_get_default_profile_list()` وجود دارد که داده‌های ساختگی برمی‌گرداند.
```

### Step 8: نوشتن تست‌های واحد برای backend endpoint /profiles بدون fallback
**Status:** `done` (100%)
**Scope:** تست‌های واحد برای endpoint /profiles در backend/app/api/routes/models.py باید نوشته شود تا اطمینان حاصل شود که: 1) وقتی profiler داده دارد، داده‌ها برگردانده می‌شوند. 2) وقتی profiler داده ندارد، خطای 404 برگردانده می‌شود. این تست‌ها باید در فایل tests/test_models.py یا مشابه قرار گیرند. نکته حیاتی: تست‌ها باید از mocking برای شبیه‌سازی profiler استفاده کنند.
**Excerpt:**
```
در `backend/app/api/routes/models.py` (خطوط 266-286) endpoint `/profiles` از `model_profiler.get_all_profiles()` استفاده می‌کند که اگر خالی باشد، fallback می‌خورد.
```

### Step 9: نوشتن تست‌های واحد برای سرویس model_profiler بدون fallback
**Status:** `done` (100%)
**Scope:** تست‌های واحد برای backend/app/services/model_profiler.py باید نوشته شود تا اطمینان حاصل شود که: 1) get_all_profiles() داده‌ها را از دیتابیس می‌خواند. 2) وقتی دیتابیس خالی است، لیست خالی برمی‌گرداند. 3) هیچ fallback به داده‌های ساختگی وجود ندارد. این تست‌ها باید در فایل tests/test_model_profiler.py قرار گیرند. نکته حیاتی: تست‌ها باید از دیتابیس تست استفاده کنند.
**Excerpt:**
```
در `backend/app/services/model_profiler.py` (که در لیست فایل‌ها موجود است) احتمالاً داده‌ها از دیتابیس خوانده می‌شوند ولی هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.
```

### Step 10: نوشتن تست‌های واحد برای فرآیند پرکننده پروفایل
**Status:** `done` (100%)
**Scope:** تست‌های واحد برای فرآیند پرکننده پروفایل (ایجاد شده در مرحله 5) باید نوشته شود تا اطمینان حاصل شود که: 1) پروفایل‌ها از نتایج تحلیل‌ها به درستی ساخته می‌شوند. 2) پروفایل‌های موجود به‌روزرسانی می‌شوند. 3) خطاها به درستی handling می‌شوند. این تست‌ها باید در فایل tests/test_profile_populator.py قرار گیرند. نکته حیاتی: تست‌ها باید از mocking برای شبیه‌سازی نتایج تحلیل‌ها استفاده کنند.
**Excerpt:**
```
هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.
```

### Step 11: نوشتن تست‌های integration برای اتصال فرآیند پرکننده به pipeline تحلیل
**Status:** `done` (100%)
**Scope:** تست‌های integration باید نوشته شود تا اطمینان حاصل شود که فرآیند پرکننده پروفایل به درستی به pipeline تحلیل متصل شده است. این تست‌ها باید یک تحلیل کامل را شبیه‌سازی کنند و بررسی کنند که پروفایل مربوطه در دیتابیس ایجاد یا به‌روزرسانی شده است. این تست‌ها باید در فایل tests/test_analysis_integration.py قرار گیرند. نکته حیاتی: این تست‌ها باید از دیتابیس تست و mocking مناسب استفاده کنند.
**Excerpt:**
```
هیچ فرآیندی برای پر کردن خودکار آن‌ها از نتایج تحلیل‌ها وجود ندارد.
```

### Step 12: نوشتن تست‌های frontend برای نمایش خطا به جای داده‌های ساختگی
**Status:** `done` (100%)
**Scope:** تست‌های frontend برای کامپوننت model-profiles باید نوشته شود تا اطمینان حاصل شود که: 1) وقتی API داده برمی‌گرداند، داده‌ها نمایش داده می‌شوند. 2) وقتی API خطای 503 برمی‌گرداند، پیام خطا نمایش داده می‌شود. 3) وقتی API خطای 404 برمی‌گرداند، پیام 'No profiles found' نمایش داده می‌شود. این تست‌ها باید در فایل frontend/src/app/model-profiles/page.test.tsx یا مشابه قرار گیرند. نکته حیاتی: تست‌ها باید از mocking برای شبیه‌سازی پاسخ‌های API استفاده کنند.
**Excerpt:**
```
در `frontend/src/app/model-profiles/page.tsx` (خطوط 90-97 و 99-105)، یک `defaultProfiles` و `defaultLeaderboard` هاردکد شده وجود دارد که وقتی API پاسخ واقعی نمی‌دهد (مثلاً دیتابیس خالی است یا خطا دارد) استفاده می‌شود.
```
