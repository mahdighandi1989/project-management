---
task_id: d50f2e06-82b9-4094-a7fd-540adecaebe0
title: 'audit notification: caption_incomplete'
type: notification_audit
priority: high
execution_priority: 2000
status: suggested
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-24T09:11:17.541995+00:00'
updated_at: '2026-05-31T09:08:43.108945+00:00'
target_files:
- backend/app/api/routes/oversight.py
---

# audit notification: caption_incomplete

## Raw Idea

caption فاقد title و context و action link است. فقط subject='Backfill AC completed' دارد.

🛠 پیشنهاد: {"title": "Backfill AC Completed", "context": "Backfill for acceptance criteria completed successfully.", "action_link": "/projects/{project_id}/backfill", "attachments": []}
---
[scan #2 at 2026-05-31T09:08:43.108939+00:00]
Missing title, context, action link, and attachments. Only subject and priority are set.

🛠 پیشنهاد: notify_event('backfill_ac_completed', 'Backfill AC completed for project {project_name}', subject='Backfill AC completed', priority=_priority, context='Backfill process finished successfully', action

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
audit notification: caption_incomplete

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/oversight.py:852`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/oversight_service.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/core/database.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/context_builder.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/storage.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `oversight.py` را import می‌کند (caller)
- `backend/app/services/notification_service.py` — این فایل `oversight.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
این مورد روی notification pipeline تأثیر می‌گذارد — همه consumer های این event باید چک شوند.

## 🔍 Context و وضعیت فعلی
caption فاقد title و context و action link است. فقط subject='Backfill AC completed' دارد.

🛠 پیشنهاد: {"title": "Backfill AC Completed", "context": "Backfill for acceptance criteria completed successfully.", "action_link": "/projects/{project_id}/backfill", "attachments": []}

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] این مورد بررسی و حل شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/oversight.py`
- `ruff check backend/app/api/routes/oversight.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: notification_audit
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. این مورد بررسی و حل شد _(verify: ui_interaction)_
