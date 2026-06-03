---
task_id: b673cafa-5a7b-47a7-8da7-db4772ce0b94
title: 'Dead Code: تابع _get_default_profile_list در model_profiles.py هرگز فراخوانی نمی‌شود'
type: refactor
priority: low
execution_priority: 4300
status: awaiting_review
external_status: pending
verification_status: partial
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T10:34:17.925750+00:00'
updated_at: '2026-06-03T17:19:42.206662+00:00'
target_files:
- backend/app/api/routes/model_profiles.py
---

# Dead Code: تابع _get_default_profile_list در model_profiles.py هرگز فراخوانی نمی‌شود

## Raw Idea

در فایل backend/app/api/routes/model_profiles.py، تابع _get_default_profile_list (که در خطوط 400+ تعریف شده) در هیچ‌جای کد فراخوانی نمی‌شود. این تابع یک لیست پیش‌فرض از پروفایل‌های مدل برمی‌گرداند، اما تمام مسیرهای استفاده از fallback درون خود endpointها (get_all_profiles) مستقیماً _get_default_profile_list را صدا نمی‌زنند بلکه از fallback داخلی استفاده می‌کنند. این dead code حجم فایل را بدون استفاده افزایش داده و خوانایی را کاهش می‌دهد.
---
[scan #2 at 2026-05-15T19:19:47.154532+00:00]
در فایل `backend/app/api/routes/model_profiles.py`، تابع `_get_default_profile_list` تعریف شده است (خطوط ۴۰۱+، خارج از محدوده نمایش داده شده) اما هیچ فراخوانی از آن در کل پروژه وجود ندارد. این تابع یک لیست پیش‌فرض از پروفایل‌های مدل را برمی‌گرداند، اما منطق fallback در endpoint `get_all_profiles` از

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
Dead Code: تابع _get_default_profile_list در model_profiles.py هرگز فراخوانی نمی‌شود

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/model_profiles.py:400-807` — `_get_default_profile_list` — کل تابع dead — هیچ فراخوانی ندارد
  ```python
  def _get_default_profile_list():
      return [
          {"model_id": "gpt-4", "provider": "openai", ...},
          ...
      ]
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Pydantic + SQLAlchemy

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/model_profiles.py` (سطر 400) — فایل حاوی تابع مرده
- `frontend/src/app/model-profiles/page.tsx` (سطر 90) — داده‌های پیش‌فرض مشابه در سمت کلاینت تعریف شده
- `backend/app/core/database.py` — `model_profiles.py` این فایل را import می‌کند
- `backend/app/models/ai_profile.py` — `model_profiles.py` این فایل را import می‌کند
- `backend/app/services/model_profiler.py` — `model_profiles.py` این فایل را import می‌کند
- `backend/app/api/routes/project_journal.py` — `model_profiles.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `model_profiles.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
هیچ وابستگی به این تابع وجود ندارد — حذف آن بی‌خطر است.

## 🔍 Context و وضعیت فعلی
در فایل backend/app/api/routes/model_profiles.py، تابع _get_default_profile_list (که در خطوط 400+ تعریف شده) در هیچ‌جای کد فراخوانی نمی‌شود. این تابع یک لیست پیش‌فرض از پروفایل‌های مدل برمی‌گرداند، اما تمام مسیرهای استفاده از fallback درون خود endpointها (get_all_profiles) مستقیماً _get_default_profile_list را صدا نمی‌زنند بلکه از fallback داخلی استفاده می‌کنند. این dead code حجم فایل را بدون استفاده افزایش داده و خوانایی را کاهش می‌دهد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تابع _get_default_profile_list از فایل حذف شود
- [ ] تمامی مسیرهای fallback در get_all_profiles به جای آن یک لیست خالی یا خطای مناسب برگردانند
- [ ] هیچ خطای import یا runtime پس از حذف رخ ندهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. حذف تابع _get_default_profile_list و هرگونه ارجاع مرده به آن. اگر در آینده نیاز به fallback پیش‌فرض بود، می‌توان از defaultProfiles در frontend/src/app/model-profiles/page.tsx (خطوط 90-97) الگوبرداری کرد که در سمت کلاینت تعریف شده است.

## 💡 نمونه‌های قبل/بعد
**حذف تابع مرده**

_قبل:_
```
def _get_default_profile_list():
    return [...]

@router.get('/profiles')
async def get_all_profiles(...):
    if use_fallback:
        return {"profiles": _get_default_profile_list(), ...}
```

_بعد:_
```
@router.get('/profiles')
async def get_all_profiles(...):
    if use_fallback:
        return {"profiles": [], "is_fallback": True, ...}
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn '_get_default_profile_list' backend/app/`
- `pytest backend/tests/ -k profile`

## ⚠️ ریسک‌ها و موارد احتیاط
بسیار کم — فقط یک تابع بدون استفاده حذف می‌شود

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: low
- تخمین زمان: small

## Acceptance Criteria

1. تابع _get_default_profile_list از فایل حذف شود _(verify: static)_
2. تمامی مسیرهای fallback در get_all_profiles به جای آن یک لیست خالی یا خطای مناسب برگردانند _(verify: static)_
3. هیچ خطای import یا runtime پس از حذف رخ ندهد _(verify: backend_test)_
