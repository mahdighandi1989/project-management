---
task_id: ca56e78a-f669-43fe-a8dc-367e8c6ed54f
title: عدم تطابق بین endpoint‌های Health Analysis و Oversight در مهاجرت
type: bug
priority: high
execution_priority: 2300
status: awaiting_review
external_status: pending
verification_status: partial
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T17:36:09.679407+00:00'
updated_at: '2026-06-03T17:20:58.159117+00:00'
target_files:
- backend/app/api/routes/project_health.py
---

# عدم تطابق بین endpoint‌های Health Analysis و Oversight در مهاجرت

## Raw Idea

فایل `backend/app/api/routes/project_health.py` دارای deprecation header است که کاربران را به `/oversight` هدایت می‌کند، اما endpoint‌های Oversight (در `backend/app/api/routes/oversight.py`) هنوز تمام قابلیت‌های Health Analysis را پوشش نمی‌دهند. به‌طور خاص، endpoint `/{project_id}/health/export` در Health وجود دارد اما معادل آن در Oversight پیاده‌سازی نشده است. همچنین، `backend/app/main.py` هر دو روتر را بدون هیچ منطق feature flag یا fallback ثبت می‌کند که باعث سردرگمی و داده‌های پراکنده می‌شود.
---
[scan #2 at 2026-05-17T07:08:48.565362+00:00]
فایل `backend/app/api/routes/project_health.py` دارای deprecation header است که به `/api/oversight/scan` اشاره می‌کند، اما endpoint‌های Oversight در `backend/app/api/routes/oversight.py` مسیر `/oversight/scan` را ندارند. این باعث می‌شود کاربران به مسیر اشتباه هدایت شوند. همچنین endpoint `export_heal

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
عدم تطابق بین endpoint‌های Health Analysis و Oversight در مهاجرت

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/project_health.py:89-145` — `export_health_data` — این endpoint باید به Oversight منتقل شود یا یک proxy در Oversight ایجاد شود
  ```python
  @router.get("/{project_id}/health/export")
  async def export_health_data(project_id: str, db: Session = Depends(get_db)):
      """خروجی JSON کامل از تمام health data یک پروژه برای backup یا migration."""
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + Deprecation headers

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 1) — مقصد مهاجرت که endpoint معادل ندارد
- `backend/app/main.py` (سطر 24) — هر دو روتر بدون feature flag ثبت شده‌اند
- `backend/app/core/database.py` — `project_health.py` این فایل را import می‌کند
- `backend/app/core/logging_utils.py` — `project_health.py` این فایل را import می‌کند
- `backend/app/models/project.py` — `project_health.py` این فایل را import می‌کند
- `backend/app/services/project_health_analyzer.py` — `project_health.py` این فایل را import می‌کند
- `backend/app/services/background_scheduler.py` — این فایل `project_health.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
این issue روی ۳ فایل اصلی تأثیر دارد: route health، route oversight، و main.py. همچنین سرویس‌های `project_health_analyzer` و `oversight_service` هر دو درگیر هستند.

## 🔍 Context و وضعیت فعلی
فایل `backend/app/api/routes/project_health.py` دارای deprecation header است که کاربران را به `/oversight` هدایت می‌کند، اما endpoint‌های Oversight (در `backend/app/api/routes/oversight.py`) هنوز تمام قابلیت‌های Health Analysis را پوشش نمی‌دهند. به‌طور خاص، endpoint `/{project_id}/health/export` در Health وجود دارد اما معادل آن در Oversight پیاده‌سازی نشده است. همچنین، `backend/app/main.py` هر دو روتر را بدون هیچ منطق feature flag یا fallback ثبت می‌کند که باعث سردرگمی و داده‌های پراکنده می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] endpoint `/oversight/{watched_id}/health-export` داده‌های مشابه `/api/projects/{id}/health/export` برگرداند
- [ ] header Deprecation در Health همچنان فعال باشد
- [ ] هیچ duplicate logic در دو سرویس ایجاد نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد یک endpoint معادل `/oversight/{watched_id}/health-export` که داده‌های Health را از طریق Oversight سرو کند و منطق مهاجرت را در `backend/app/services/oversight_service.py` پیاده‌سازی کند.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن endpoint proxy در Oversight**

_قبل:_
```
// وجود ندارد
```

_بعد:_
```
@router.get("/{watched_id}/health-export")
async def export_watched_health(watched_id: str):
    service = get_oversight_service()
    return await service.export_health_data(watched_id)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -v http://localhost:8000/api/projects/test/health/export | grep -c 'health_scores'`
- `curl -v http://localhost:8000/oversight/test/health-export | grep -c 'health_scores'`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر Overservice سرویس داده‌های Health را نداشته باشد، endpoint جدید خالی برمی‌گرداند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. endpoint `/oversight/{watched_id}/health-export` داده‌های مشابه `/api/projects/{id}/health/export` برگرداند _(verify: api_response)_
2. header Deprecation در Health همچنان فعال باشد _(verify: static)_
3. هیچ duplicate logic در دو سرویس ایجاد نشود _(verify: static)_
