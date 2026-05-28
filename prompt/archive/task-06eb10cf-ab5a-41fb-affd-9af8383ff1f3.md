---
task_id: 06eb10cf-ab5a-41fb-affd-9af8383ff1f3
title: API Keys در فایل .env.example ذخیره شده و در دیتابیس به صورت رمزگذاری‌نشده ذخیره می‌شوند
type: security
priority: critical
execution_priority: 100
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T07:36:36.684773+00:00'
updated_at: '2026-05-20T04:24:01.092662+00:00'
archived: true
archived_at: '2026-05-18T04:22:43.565589+00:00'
tags:
- merged
target_files:
- backend/app/models/setting.py
- backend/app/api/routes/settings.py
---

# API Keys در فایل .env.example ذخیره شده و در دیتابیس به صورت رمزگذاری‌نشده ذخیره می‌شوند

## Raw Idea

فایل `backend/.env.example` حاوی placeholder برای API keys است که نشان‌دهنده وجود این کلیدها در محیط است. مهم‌تر از آن، در `backend/app/api/routes/settings.py` (خطوط 183-198 و 300-328)، کلیدهای API از طریق `Setting.set_value` با `value_type="encrypted"` ذخیره می‌شوند، اما بررسی `backend/app/models/setting.py` نشان می‌دهد که متد `set_value` هیچ رمزگذاری واقعی انجام نمی‌دهد و مقدار را به صورت plain text در دیتابیس SQLite ذخیره می‌کند. این یک نقص امنیتی بحرانی است زیرا هر کسی که به دیتابیس دسترسی داشته باشد (مثلاً از طریق یک vulnerability دیگر) می‌تواند تمام API keys را بخواند.

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
API Keys در فایل .env.example ذخیره شده و در دیتابیس به صورت رمزگذاری‌نشده ذخیره می‌شوند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/models/setting.py:50-80` — `Setting.set_value` — متد اصلی که باید اصلاح شود تا از رمزگذاری استفاده کند
  ```python
  def set_value(db, key, value, value_type='string', category='general', description='', is_secret=False):
      setting = db.query(Setting).filter(Setting.key == key).first()
      if not setting:
          setting = Setting(key=key, category=category, description=description, is_secret=is_secret)
          db.add(setting)
      setting.value = value  # ⚠️ ذخیره به صورت plain text
      setting.value_type = value_type
      db.commit()
  ```
- `backend/app/api/routes/settings.py:183-198` — `update_api_keys` — endpoint که کلیدها را با flag 'encrypted' ذخیره می‌کند اما رمزگذاری واقعی نیست
  ```python
  Setting.set_value(
      db=db,
      key=db_key,
      value=value,
      value_type="encrypted",  # ⚠️ اینجا ادعای رمزگذاری شده اما پیاده‌سازی نشده
      category="api_keys",
      description=description,
      is_secret=True
  )
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/config.py` (سطر 1) — محل ذخیره master key برای رمزگذاری
- `backend/.env.example` (سطر 1) — نمونه فایل environment که placeholder کلیدها را نشان می‌دهد
- `backend/app/api/routes/project_health.py` — این فایل `setting.py` را import می‌کند (caller)
- `backend/app/api/routes/project_memory.py` — این فایل `setting.py` را import می‌کند (caller)
- `backend/app/api/routes/settings.py` — این فایل `setting.py` را import می‌کند (caller)
- `backend/app/api/routes/simple_projects.py` — این فایل `setting.py` را import می‌کند (caller)
- `backend/app/core/roles.py` — `settings.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این issue تمام endpointهای settings که API keys را ذخیره می‌کنند (settings.py, deploy-keys) و همچنین متد `load_api_keys_from_database` در `main.py` را تحت تأ

## 🔍 Context و وضعیت فعلی
فایل `backend/.env.example` حاوی placeholder برای API keys است که نشان‌دهنده وجود این کلیدها در محیط است. مهم‌تر از آن، در `backend/app/api/routes/settings.py` (خطوط 183-198 و 300-328)، کلیدهای API از طریق `Setting.set_value` با `value_type="encrypted"` ذخیره می‌شوند، اما بررسی `backend/app/models/setting.py` نشان می‌دهد که متد `set_value` هیچ رمزگذاری واقعی انجام نمی‌دهد و مقدار را به صورت plain text در دیتابیس SQLite ذخیره می‌کند. این یک نقص امنیتی بحرانی است زیرا هر کسی که به دیتابیس دسترسی داشته باشد (مثلاً از طریق یک vulnerability دیگر) می‌تواند تمام API keys را بخواند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. یک مکانیزم رمزگذاری واقعی (مانند `cryptography.fernet` یا `python-jose`) برای ذخیره‌سازی API keys در دیتابیس پیاده‌سازی کنید. متد `Setting.set_value` را اصلاح کنید تا قبل از ذخیره، مقدار را با یک کلید master که در environment variable (مثلاً `SETTINGS_ENCRYPTION_KEY`) ذخیره شده، رمزگذاری کند. متد `Setting.get_value` نیز باید رمزگشایی را انجام دهد.

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
- نوع: security
- اولویت: critical
- تخمین زمان: medium

## Acceptance Criteria

1. اعمال تغییر بدون شکستن تست‌های موجود _(verify: backend_test)_
2. linter بدون warning عبور می‌کند _(verify: static)_
3. type-check موفق است _(verify: static)_
