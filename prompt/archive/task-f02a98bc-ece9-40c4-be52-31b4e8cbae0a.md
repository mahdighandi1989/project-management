---
task_id: f02a98bc-ece9-40c4-be52-31b4e8cbae0a
title: نقص در مدیریت Session دیتابیس در analysis.py — عدم بستن Session در مسیر خطا
type: bug
priority: high
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T04:20:34.673487+00:00'
updated_at: '2026-05-29T16:43:30.977191+00:00'
archived: true
archived_at: '2026-05-17T18:03:26.805152+00:00'
target_files:
- backend/app/api/routes/analysis.py
---

# نقص در مدیریت Session دیتابیس در analysis.py — عدم بستن Session در مسیر خطا

## Raw Idea

در endpoint `run_analysis_stream` (خطوط 115-124)، یک `SessionLocal()` ایجاد می‌شود و به `DeepAnalysisService` پاس داده می‌شود، اما این session در هیچ‌جایی بسته نمی‌شود. در صورت بروز استثنا در `run_full_analysis`، بلوک `finally` فقط یک سیگنال `done` می‌فرستد و session را نمی‌بندد. این باعث نشت اتصال دیتابیس (connection leak) می‌شود که در طولانی‌مدت منجر به exhaustion pool و کرش سرور می‌گردد.
---
[scan #2 at 2026-05-15T10:28:15.700696+00:00]
در endpoint `run_analysis_stream` (خطوط 115-124)، یک `SessionLocal()` ایجاد می‌شود و به `DeepAnalysisService` پاس داده می‌شود. اما این session در هیچ‌جایی (نه در `try`، نه در `except`، نه در `finally`) بسته نمی‌شود. اگر تحلیل با خطا مواجه شود یا connection قطع شود، session باز می‌ماند و可能导致 connecti
---
[scan #3 at 2026-05-15T16:41:11.918827+00:00]
در endpoint run_analysis_stream (analysis.py خط 116-124)، یک session دیتابیس (analysis_db) ساخته می‌شود و به DeepAnalysisService داده می‌شود. اما این session در هیچ‌جایی بسته نمی‌شود — نه در try, نه در except, نه در finally. این باعث نشت connection به SQLite می‌شود و در طولانی‌مدت باعث خطای 'databas
---
[scan #4 at 2026-05-15T17:36:09.679173+00:00]
در endpoint `run_analysis_stream` (analysis.py:116-117)، یک `SessionLocal()` جدید ساخته می‌شود و به `DeepAnalysisService` داده می‌شود. این Session در `finally` بلاک بسته نمی‌شود. اگر تحلیل با خطا مواجه شود (Exception در خط 200-206)، Session باز می‌ماند و باعث نشت connection در SQLite (و به‌ویژه در ح
---
[scan #5 at 2026-05-17T08:02:38.211692+00:00]
در چندین endpoint (analysis.py, model_profiles.py, project_health.py) session دیتابیس با `SessionLocal()` ساخته می‌شود اما در صورت بروز exception قبل از رسیدن به `finally`، session بسته نمی‌شود. این باعث نشت connection و در نهایت exhaustion pool SQLite می‌شود. مثال: analysis.py خط ۱۱۷ `analysis_db =
---
[scan #6 at 2026-05-17T08:02:38.881670+00:00]
در endpoint استریم `/analysis/run-stream`، یک `SessionLocal()` در خط 117 ساخته می‌شود و به `DeepAnalysisService` پاس داده می‌شود، اما هیچ‌گاه `db.close()` یا `finally` برای بستن آن وجود ندارد. این باعث نشت connection در طولانی‌مدت می‌شود. همچنین در صورت بروز خطا در `run_analysis_task`، session بسته 

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
نقص در مدیریت Session دیتابیس در analysis.py — عدم بستن Session در مسیر خطا

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:115-124` — `run_analysis_stream` — ایجاد Session بدون بستن آن — باید در finally بسته شود
  ```python
  from ...core.database import SessionLocal
  analysis_db = SessionLocal()
  
  deep_analyzer = DeepAnalysisService(
      ai_manager=ai_manager,
      progress_callback=progress_callback,
      db_session=analysis_db
  )
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + SQLite

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — تعریف SessionLocal و get_db
- `backend/app/services/deep_analysis_service.py` (سطر 1) — سرویسی که session را مصرف می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این باگ روی تمام endpoint‌هایی که از `SessionLocal()` مستقیم استفاده می‌کنند تأثیر می‌گذارد. الگوی مشابه در `analysis.py` خطوط 277-290 و 296-306 و 315-325 و 348-373 نیز دیده می‌شود.

## 🔍 Context و وضعیت فعلی
در endpoint `run_analysis_stream` (خطوط 115-124)، یک `SessionLocal()` ایجاد می‌شود و به `DeepAnalysisService` پاس داده می‌شود، اما این session در هیچ‌جایی بسته نمی‌شود. در صورت بروز استثنا در `run_full_analysis`، بلوک `finally` فقط یک سیگنال `done` می‌فرستد و session را نمی‌بندد. این باعث نشت اتصال دیتابیس (connection leak) می‌شود که در طولانی‌مدت منجر به exhaustion pool و کرش سرور می‌گردد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تمامی session‌های ایجادشده با SessionLocal() در کمتر از ۵ ثانیه پس از پایان درخواست بسته شوند
- [ ] تعداد اتصالات همزمان دیتابیس از ۱۰ تجاوز نکند (قبلاً در بار بالا به ۵۰+ می‌رسید)
- [ ] هیچ warning یا error مربوط به 'unclosed session' در لاگ‌ها ظاهر نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. استفاده از context manager یا try/finally برای بستن `analysis_db` در تمام مسیرهای اجرا (success و error). همچنین بهتر است از وابستگی `Depends(get_db)` به‌جای `SessionLocal()` مستقیم استفاده شود تا FastAPI خودش مدیریت lifecycle را انجام دهد.

## 💡 نمونه‌های قبل/بعد
**رفع نشت session در run_analysis_stream**

_قبل:_
```
analysis_db = SessionLocal()
deep_analyzer = DeepAnalysisService(..., db_session=analysis_db)
...
finally:
    await progress_queue.put({'event': 'done'})
```

_بعد:_
```
async with SessionLocal() as analysis_db:
    deep_analyzer = DeepAnalysisService(..., db_session=analysis_db)
    ...
finally:
    await progress_queue.put({'event': 'done'})
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/api/routes/ -- فایل‌هایی که session می‌سازند و نمی‌بندند را شناسایی کن`
- `ab -n 100 -c 10 http://localhost:8000/api/analysis/run-stream -- تست بار برای مشاهده نشت`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر به async with ممکن است نیاز به تغییر در سرویس‌هایی که session را به صورت synchronous مصرف می‌کنند داشته باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

## Acceptance Criteria

1. تمامی session‌های ایجادشده با SessionLocal() در کمتر از ۵ ثانیه پس از پایان درخواست بسته شوند _(verify: backend_test)_
2. تعداد اتصالات همزمان دیتابیس از ۱۰ تجاوز نکند (قبلاً در بار بالا به ۵۰+ می‌رسید) _(verify: backend_test)_
3. هیچ warning یا error مربوط به 'unclosed session' در لاگ‌ها ظاهر نشود _(verify: backend_test)_
