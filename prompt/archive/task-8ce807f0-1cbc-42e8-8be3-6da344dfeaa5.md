---
task_id: 8ce807f0-1cbc-42e8-8be3-6da344dfeaa5
title: OversightService فاقد تست واحد است — ۱۴ روتر به آن وابسته‌اند
type: bug
priority: critical
execution_priority: 100
status: awaiting_review
external_status: pending
verification_status: partial
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T04:20:34.635662+00:00'
updated_at: '2026-06-03T17:14:02.971234+00:00'
archived: true
archived_at: '2026-05-18T04:17:00.907251+00:00'
tags:
- merged
target_files:
- backend/app/services/oversight_service.py
---

# OversightService فاقد تست واحد است — ۱۴ روتر به آن وابسته‌اند

## Raw Idea

سرویس `oversight_service.py` هاب اصلی ۱۴ endpoint در `oversight.py` است. هیچ فایل تستی برای این سرویس وجود ندارد. با توجه به اینکه این سرویس مدیریت watched projects, tasks, scans, و runtime verification را بر عهده دارد، عدم پوشش تست ریسک بالایی ایجاد می‌کند.

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
OversightService فاقد تست واحد است — ۱۴ روتر به آن وابسته‌اند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `OversightService` — کلاس اصلی که باید تست شود
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self.tasks = []
          self._lock = asyncio.Lock()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + asyncio + SQLite

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 12) — ۱۴ endpoint از این سرویس استفاده می‌کنند
- `backend/app/services/oversight_service.py` (سطر 1) — خود سرویس

## 🌐 نقشهٔ وابستگی‌ها
این سرویس توسط oversight.py (۱۴ route)، main.py (scheduler loop) و چند سرویس دیگر استفاده می‌شود.

## 🔍 Context و وضعیت فعلی
سرویس `oversight_service.py` هاب اصلی ۱۴ endpoint در `oversight.py` است. هیچ فایل تستی برای این سرویس وجود ندارد. با توجه به اینکه این سرویس مدیریت watched projects, tasks, scans, و runtime verification را بر عهده دارد، عدم پوشش تست ریسک بالایی ایجاد می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/tests/test_oversight_service.py ایجاد شود
- [ ] حداقل ۵ تست برای متدهای اصلی: add_watched, update_watched, run_task, scan_project, status_summary
- [ ] تست‌ها با pytest و pytest-asyncio اجرا شوند
- [ ] همه تست‌ها پاس شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد فایل `backend/tests/test_oversight_service.py` با تست‌های واحد برای متدهای اصلی: add_watched, update_watched, run_task, scan_project, status_summary

## 💡 نمونه‌های قبل/بعد
**تست add_watched**

_قبل:_
```
هیچ تستی وجود ندارد
```

_بعد:_
```
async def test_add_watched():
    service = OversightService()
    result = await service.add_watched({
        'repo_full_name': 'test/repo',
        'default_branch': 'main'
    })
    assert result['success']
    assert len(service.watched) == 1
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v`
- `pytest backend/tests/ --cov=app.services.oversight_service`

## ⚠️ ریسک‌ها و موارد احتیاط
بدون تست، تغییرات در oversight_service ممکن است ۱۴ endpoint را بشکند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: medium

## Acceptance Criteria

1. فایل backend/tests/test_oversight_service.py ایجاد شود _(verify: static)_
2. حداقل ۵ تست برای متدهای اصلی: add_watched, update_watched, run_task, scan_project, status_summary _(verify: backend_test)_
3. تست‌ها با pytest و pytest-asyncio اجرا شوند _(verify: backend_test)_
4. همه تست‌ها پاس شوند _(verify: backend_test)_
