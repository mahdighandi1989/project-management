---
task_id: 6eee9e60-fb0d-47df-b2fd-42ae1169fafc
title: 'audit notification: template_duplicate'
type: notification_audit
priority: medium
execution_priority: 3300
status: awaiting_review
external_status: pending
verification_status: partial
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T16:47:34.404794+00:00'
updated_at: '2026-06-02T17:48:26.540638+00:00'
target_files:
- backend/app/api/routes/notifications.py
---

# audit notification: template_duplicate

## Raw Idea

این notify_event یک wrapper generic است که پارامترها را پاس می‌دهد. caption کامل نیست چون payload ساختار caption را ندارد.

🛠 پیشنهاد: {"title": "{payload.subject}", "context": "{payload.message}", "action": {"label": "View", "url": "/notifications/{payload.watched_id}"}, "attachments": []}
---
[scan #2 at 2026-05-15T17:43:34.081031+00:00]
الگوی caption در sample 1 و sample 9 بسیار شبیه است (هر دو با ایموجی و متن ساده). این یکنواختی باعث کاهش تمایز بین event types می‌شود.

🛠 پیشنهاد: {"title": "Project Created", "context": "...", "action_link": "...", "attachments": []}
---
[scan #3 at 2026-05-31T09:08:43.441893+00:00]
Template message is a meta-instruction about how to write the notification, not an actual notification. Duplicate of generic pattern.

🛠 پیشنهاد: notify_event('{event}', message, silent=False, priority='high', context='Acceptance criteria update', action_link='/tasks/{task_id}/criteria')

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
audit notification: template_duplicate

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/notifications.py:91`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/notification_service.py` — `notifications.py` این فایل را import می‌کند
- `backend/app/services/oversight_service.py` — `notifications.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `notifications.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
این مورد روی notification pipeline تأثیر می‌گذارد — همه consumer های این event باید چک شوند.

## 🔍 Context و وضعیت فعلی
این notify_event یک wrapper generic است که پارامترها را پاس می‌دهد. caption کامل نیست چون payload ساختار caption را ندارد.

🛠 پیشنهاد: {"title": "{payload.subject}", "context": "{payload.message}", "action": {"label": "View", "url": "/notifications/{payload.watched_id}"}, "attachments": []}

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
- `python -m py_compile backend/app/api/routes/notifications.py`
- `ruff check backend/app/api/routes/notifications.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: notification_audit
- اولویت: medium
- تخمین زمان: medium

## Acceptance Criteria

1. این مورد بررسی و حل شد _(verify: static)_
