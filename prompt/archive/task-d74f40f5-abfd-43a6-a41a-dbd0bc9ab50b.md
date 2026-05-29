---
task_id: d74f40f5-abfd-43a6-a41a-dbd0bc9ab50b
title: سرویس oversight_service.py فاقد تست واحد است
type: bug
priority: high
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T05:09:14.853126+00:00'
updated_at: '2026-05-29T20:10:12.614630+00:00'
archived: true
archived_at: '2026-05-17T18:07:18.356323+00:00'
target_files:
- backend/app/services/oversight_service.py
---

# سرویس oversight_service.py فاقد تست واحد است

## Raw Idea

فایل backend/app/services/oversight_service.py یک هاب مرکزی است که توسط 5 فایل مختلف (oversight.py route, notification_service.py, verify_runtime/*) import می‌شود. این سرویس شامل منطق حیاتی نظارت پروژه‌های GitHub، مدیریت watched projects، و هماهنگی scanهاست. با وجود 1481 خط کد در route مربوطه، هیچ فایل تستی برای این سرویس وجود ندارد. این یک critical path است چون هر خطا در این سرویس می‌تواند کل سیستم نظارت را مختل کند.

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
سرویس oversight_service.py فاقد تست واحد است

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `OversightService` — کلاس اصلی سرویس - نقطه شروع تست
  ```python
  class OversightService:
      def __init__(self):
          self.watched = []
          self._lock = asyncio.Lock()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + asyncio + GitHub API

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 12) — این route از OversightService استفاده می‌کند
- `backend/app/services/notification_service.py` (سطر 1) — از OversightService import می‌کند
- `backend/app/services/verify_runtime/__init__.py` (سطر 1) — از OversightService استفاده می‌کند

## 🌐 نقشهٔ وابستگی‌ها
هاب مرکزی با 5 مصرف‌کننده مستقیم؛ هر تغییری در این سرویس روی کل سیستم نظارت اثر می‌گذارد.

## 🔍 Context و وضعیت فعلی
فایل backend/app/services/oversight_service.py یک هاب مرکزی است که توسط 5 فایل مختلف (oversight.py route, notification_service.py, verify_runtime/*) import می‌شود. این سرویس شامل منطق حیاتی نظارت پروژه‌های GitHub، مدیریت watched projects، و هماهنگی scanهاست. با وجود 1481 خط کد در route مربوطه، هیچ فایل تستی برای این سرویس وجود ندارد. این یک critical path است چون هر خطا در این سرویس می‌تواند کل سیستم نظارت را مختل کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تست add_watched با repo_full_name معتبر موفق باشد
- [ ] تست add_watched با repo_full_name تکراری ValueError بدهد
- [ ] تست update_watched فیلدهای مختلف را به‌روز کند
- [ ] تست status_summary آمار صحیح برگرداند
- [ ] تست list_user_repos با force_refresh=True کار کند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد فایل تست backend/tests/test_oversight_service.py با تست‌های واحد برای توابع کلیدی: add_watched, update_watched, run_scan, status_summary, list_user_repos

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
    result = await service.add_watched({'repo_full_name': 'test/repo'})
    assert result['success']
    assert len(service.watched) == 1
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_oversight_service.py -v`
- `pytest backend/tests/test_oversight_service.py -k test_add_watched`

## ⚠️ ریسک‌ها و موارد احتیاط
نیاز به mock کردن GitHub API و دیتابیس؛ احتمال شکستن تست‌های موجود در صورت تغییر interface

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. تست add_watched با repo_full_name معتبر موفق باشد _(verify: backend_test)_
2. تست add_watched با repo_full_name تکراری ValueError بدهد _(verify: backend_test)_
3. تست update_watched فیلدهای مختلف را به‌روز کند _(verify: backend_test)_
4. تست status_summary آمار صحیح برگرداند _(verify: backend_test)_
5. تست list_user_repos با force_refresh=True کار کند _(verify: backend_test)_
