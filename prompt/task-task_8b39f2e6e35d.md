---
task_id: task_8b39f2e6e35d
title: 'رفع آسیب‌پذیری‌های امنیتی: اعتبارسنجی JWT و رمزگذاری API Keys'
type: other
priority: critical
execution_priority: 1000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:22:43.565570+00:00'
updated_at: '2026-05-29T20:23:32.345874+00:00'
tags:
- consolidated
- post_verify_merge
---

# رفع آسیب‌پذیری‌های امنیتی: اعتبارسنجی JWT و رمزگذاری API Keys

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 26 و 27 هر دو به مسائل امنیتی حیاتی مربوط می‌شوند: عدم اعتبارسنجی JWT و ذخیره‌سازی API Keys به صورت رمزگذاری‌نشده.
🎯 theme: رفع مشکلات امنیتی: JWT و API Keys
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: a83013ef-82a8-4156-a06d-1e2a2b235dc5
  عنوان اصلی: عدم اعتبارسنجی توکن JWT در endpoint‌های Oversight و GitHub Import
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py, backend/app/api/routes/oversight.py

📋 acceptance_criteria کامل:
  - تمامی endpointهای /oversight/* بدون توکن معتبر [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/oversight/status", "headers": null, "json_body": null, "expected_status": 401, "required_fields": [], "json_contains": null}]

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
عدم اعتبارسنجی توکن JWT در endpoint‌های Oversight و GitHub Import

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/oversight.py:1-15` — `router` — هیچ dependency احراز هویت به router اضافه نشده است
  ```python
  from fastapi import APIRouter, HTTPException, Query, Depends
  from pydantic import BaseModel, Field
  from typing import List, Optional, Dict, Any
  from sqlalchemy.orm import Session
  
  from ...services.oversight_service import get_oversight_service
  from ...core.database import get_db
  
  router = APIRouter(prefix="/oversight", tags=["Oversight"])
  ```
- `backend/app/api/routes/github_import.py:1-15` — `router` — هیچ dependency احراز هویت به router اضافه نشده است
  ```python
  from fastapi import APIRouter, HTTPException, Depends
  from pydantic import BaseModel
  from typing import Optional, List
  from sqlalchemy.orm import Session
  
  from ...core.database import get_db
  from ...services.github_import import get_github_import_service
  from ...models.project import Project, ProjectFile
  from ...core.logging_utils import StructuredLogger
  
  router = APIRouter(prefix="/github", tags=["GitHub Import"])
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + JWT + Python-jose

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 15) — فایل اصلی که routerها را mount می‌کند و می‌توان middleware اضافه کرد
- `backend/app/core/config.py` (سطر 1) — تنظیمات JWT_SECRET و ALGORITHM در این فایل تعریف می‌شود
- `backend/app/services/oversight_service.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/core/database.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/storage.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/ac_enricher.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/github_import.py` — `github_import.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این آسیب‌پذیری تمام endpointهای Oversight (حدود 30 endpoint) و GitHub Import (حدود 10 endpoint) را تحت تأثیر قرار می‌دهد. هر کدام از این endpointها می‌توانند توسط مهاجم بدون احراز هویت فراخوانی شوند.

## 🔍 Context و وضعیت فعلی
در فایل‌های `backend/app/api/routes/oversight.py` و `backend/app/api/routes/github_import.py`، هیچ middleware یا dependency برای احراز هویت و اعتبارسنجی توکن JWT وجود ندارد. هر endpoint در این ماژول‌ها بدون نیاز به توکن معتبر قابل دسترسی است. این یک آسیب‌پذیری امنیتی بحرانی است زیرا هر کاربر ناشناس می‌تواند به عملیات حساس مانند مشاهده لیست مخازن گیت‌هاب کاربر، ایجاد تسک، اجرای اسکن و حتی commit به ریپوهای گیت‌هاب دسترسی داشته باشد. شواهد در خطوط 1-15 فایل `oversight.py` و خطوط 1-15 فایل `github_import.py` نشان می‌دهد که هیچ import یا استفاده‌ای از `Depends(get_current_user)` یا مشابه آن وجود ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تمامی endpointهای /oversight/* بدون توکن معتبر
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. یک dependency احراز هویت (مانند `get_current_user`) ایجاد کنید که توکن JWT را از هدر Authorization استخراج و اعتبارسنجی کند. سپس این dependency را به تمام endpointهای حساس در `oversight.py` و `github_import.py` اضافه کنید. همچنین یک middleware سراسری برای مسیر `/oversight` و `/github` در `main.py` اضافه کنید.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن dependency احراز هویت به router**

_قبل:_
```
router = APIRouter(prefix="/oversight", tags=["Oversight"])
```

_بعد:_
```
from ...core.auth import get_current_user

router = APIRouter(
    prefix="/oversight",
    tags=["Oversight"],
    dependencies=[Depends(get_current_user)]
)
```

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 06eb10cf-ab5a-41fb-affd-9af8383ff1f3
  عنوان اصلی: API Keys در فایل .env.example ذخیره شده و در دیتابیس به صورت رمزگذاری‌نشده ذخیره می‌شوند
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/settings.py, backend/app/models/setting.py

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "pyright", "type: ignore"], "files_hint": ["backend/"]}]

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
- در commit message: `merged-from: a83013ef-82a8-4156-a06d-1e2a2b235dc5, 06eb10cf-ab5a-41fb-affd-9af8383ff1f3`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 26 و 27 هر دو به مسائل امنیتی حیاتی مربوط می‌شوند: عدم اعتبارسنجی JWT و ذخیره‌سازی API Keys به صورت رمزگذاری‌نشده.
🎯 theme: رفع مشکلات امنیتی: JWT و API Keys
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: a83013ef-82a8-4156-a06d-1e2a2b235dc5
  عنوان اصلی: عدم اعتبارسنجی توکن JWT در endpoint‌های Oversight و GitHub Import
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py, backend/app/api/routes/oversight.py

📋 acceptance_criteria کامل:
  - تمامی endpointهای /oversight/* بدون توکن معتبر [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/oversight/status", "headers": null, "json_body": null, "expected_status": 401, "required_fields": [], "json_contains": null}]

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
عدم اعتبارسنجی توکن JWT در endpoint‌های Oversight و GitHub Import

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/oversight.py:1-15` — `router` — هیچ dependency احراز هویت به router اضافه نشده است
  ```python
  from fastapi import APIRouter, HTTPException, Query, Depends
  from pydantic import BaseModel, Field
  from typing import List, Optional, Dict, Any
  from sqlalchemy.orm import Session
  
  from ...services.oversight_service import get_oversight_service
  from ...core.database import get_db
  
  router = APIRouter(prefix="/oversight", tags=["Oversight"])
  ```
- `backend/app/api/routes/github_import.py:1-15` — `router` — هیچ dependency احراز هویت به router اضافه نشده است
  ```python
  from fastapi import APIRouter, HTTPException, Depends
  from pydantic import BaseModel
  from typing import Optional, List
  from sqlalchemy.orm import Session
  
  from ...core.database import get_db
  from ...services.github_import import get_github_import_service
  from ...models.project import Project, ProjectFile
  from ...core.logging_utils import StructuredLogger
  
  router = APIRouter(prefix="/github", tags=["GitHub Import"])
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + JWT + Python-jose

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 15) — فایل اصلی که routerها را mount می‌کند و می‌توان middleware اضافه کرد
- `backend/app/core/config.py` (سطر 1) — تنظیمات JWT_SECRET و ALGORITHM در این فایل تعریف می‌شود
- `backend/app/services/oversight_service.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/core/database.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/storage.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/verify_runtime/ac_enricher.py` — `oversight.py` این فایل را import می‌کند
- `backend/app/services/github_import.py` — `github_import.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این آسیب‌پذیری تمام endpointهای Oversight (حدود 30 endpoint) و GitHub Import (حدود 10 endpoint) را تحت تأثیر قرار می‌دهد. هر کدام از این endpointها می‌توانند توسط مهاجم بدون احراز هویت فراخوانی شوند.

## 🔍 Context و وضعیت فعلی
در فایل‌های `backend/app/api/routes/oversight.py` و `backend/app/api/routes/github_import.py`، هیچ middleware یا dependency برای احراز هویت و اعتبارسنجی توکن JWT وجود ندارد. هر endpoint در این ماژول‌ها بدون نیاز به توکن معتبر قابل دسترسی است. این یک آسیب‌پذیری امنیتی بحرانی است زیرا هر کاربر ناشناس می‌تواند به عملیات حساس مانند مشاهده لیست مخازن گیت‌هاب کاربر، ایجاد تسک، اجرای اسکن و حتی commit به ریپوهای گیت‌هاب دسترسی داشته باشد. شواهد در خطوط 1-15 فایل `oversight.py` و خطوط 1-15 فایل `github_import.py` نشان می‌دهد که هیچ import یا استفاده‌ای از `Depends(get_current_user)` یا مشابه آن وجود ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تمامی endpointهای /oversight/* بدون توکن معتبر
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. یک dependency احراز هویت (مانند `get_current_user`) ایجاد کنید که توکن JWT را از هدر Authorization استخراج و اعتبارسنجی کند. سپس این dependency را به تمام endpointهای حساس در `oversight.py` و `github_import.py` اضافه کنید. همچنین یک middleware سراسری برای مسیر `/oversight` و `/github` در `main.py` اضافه کنید.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن dependency احراز هویت به router**

_قبل:_
```
router = APIRouter(prefix="/oversight", tags=["Oversight"])
```

_بعد:_
```
from ...core.auth import get_current_user

router = APIRouter(
    prefix="/oversight",
    tags=["Oversight"],
    dependencies=[Depends(get_current_user)]
)
```

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

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: 06eb10cf-ab5a-41fb-affd-9af8383ff1f3
  عنوان اصلی: API Keys در فایل .env.example ذخیره شده و در دیتابیس به صورت رمزگذاری‌نشده ذخیره می‌شوند
  اولویت اصلی: critical
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/settings.py, backend/app/models/setting.py

📋 acceptance_criteria کامل:
  - اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
  - linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
  - type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "pyright", "type: ignore"], "files_hint": ["backend/"]}]

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
- در commit message: `merged-from: a83013ef-82a8-4156-a06d-1e2a2b235dc5, 06eb10cf-ab5a-41fb-affd-9af8383ff1f3`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. تمامی endpointهای /oversight/* بدون توکن معتبر _(verify: api_response)_
2. اعمال تغییر بدون شکستن تست‌های موجود _(verify: backend_test)_
3. linter بدون warning عبور می‌کند _(verify: static)_
4. type-check موفق است _(verify: static)_

## Task Steps

### Step 1: بررسی و تحلیل ساختار فعلی احراز هویت JWT در پروژه
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل‌های backend/app/core/auth.py (در صورت وجود)، backend/app/core/config.py، backend/app/main.py و backend/app/api/deps.py برای یافتن dependency احراز هویت موجود (مانند get_current_user) است. همچنین بررسی می‌شود که آیا middleware یا dependency سراسری برای JWT وجود دارد یا خیر. این مرحله فقط تحلیل است و هیچ تغییری در کد ایجاد نمی‌کند. خروجی این مرحله یک گزارش از وضعیت موجود است که مشخص می‌کند چه dependency‌هایی از قبل وجود دارند و چه چیزهایی باید ساخته شوند.
**Excerpt:**
```
در فایل‌های `backend/app/api/routes/oversight.py` و `backend/app/api/routes/github_import.py`، هیچ middleware یا dependency برای احراز هویت و اعتبارسنجی توکن JWT وجود ندارد. هر endpoint در این ماژول‌ها بدون نیاز به توکن معتبر قابل دسترسی است. شواهد در خطوط 1-15 فایل `oversight.py` و خطوط 1-15 فایل `github_import.py` نشان می‌دهد که هیچ import یا استفاده‌ای از `Depends(get_current_user)` یا مشابه آن وجود ندارد.
```

### Step 2: ایجاد dependency احراز هویت JWT (get_current_user) در فایل auth.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یا تکمیل فایل backend/app/core/auth.py با تابع get_current_user است که توکن JWT را از هدر Authorization (با فرمت Bearer) استخراج کرده، آن را با استفاده از python-jose و کلید SECRET_KEY از config.py اعتبارسنجی می‌کند. این تابع باید یک شیء User (یا دیکشنری حاوی user_id و role) برگرداند و در صورت نامعتبر بودن توکن، HTTPException با status 401 برگرداند. همچنین باید تابع get_optional_current_user (که در صورت نبود توکن خطا نمی‌دهد) نیز ایجاد شود. این مرحله شامل ایجاد مدل Pydantic برای TokenData نیز می‌شود.
**Excerpt:**
```
یک dependency احراز هویت (مانند `get_current_user`) ایجاد کنید که توکن JWT را از هدر Authorization استخراج و اعتبارسنجی کند. سپس این dependency را به تمام endpointهای حساس در `oversight.py` و `github_import.py` اضافه کنید. همچنین یک middleware سراسری برای مسیر `/oversight` و `/github` در `main.py` اضافه کنید.
```

### Step 3: اضافه کردن dependency احراز هویت به router Oversight در oversight.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/api/routes/oversight.py است. dependency احراز هویت get_current_user به router اضافه می‌شود تا تمام endpointهای این router (حدود 30 endpoint) نیاز به توکن JWT معتبر داشته باشند. این کار با اضافه کردن پارامتر dependencies=[Depends(get_current_user)] به تعریف router انجام می‌شود. همچنین import مربوطه به فایل اضافه می‌شود. این مرحله شامل بررسی endpointهایی که ممکن است نیاز به دسترسی عمومی داشته باشند (مانند status) نیست و فرض می‌شود همه endpointها نیاز به احراز هویت دارند.
**Excerpt:**
```
تمام endpointهای /oversight/* بدون توکن معتبر [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/oversight/status", "headers": null, "json_body": null, "expected_status": 401, "required_fields": [], "json_contains": null}]
```

### Step 4: اضافه کردن dependency احراز هویت به router GitHub Import در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/api/routes/github_import.py است. dependency احراز هویت get_current_user به router اضافه می‌شود تا تمام endpointهای این router (حدود 10 endpoint) نیاز به توکن JWT معتبر داشته باشند. این کار با اضافه کردن پارامتر dependencies=[Depends(get_current_user)] به تعریف router انجام می‌شود. import مربوطه نیز اضافه می‌شود.
**Excerpt:**
```
در فایل‌های `backend/app/api/routes/oversight.py` و `backend/app/api/routes/github_import.py`، هیچ middleware یا dependency برای احراز هویت و اعتبارسنجی توکن JWT وجود ندارد. هر endpoint در این ماژول‌ها بدون نیاز به توکن معتبر قابل دسترسی است.
```

### Step 5: بررسی و تحلیل ساختار فعلی مدل Setting و رمزگذاری API Keys
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل‌های backend/app/models/setting.py، backend/app/api/routes/settings.py، backend/app/core/config.py و backend/.env.example است. هدف شناسایی متدهای set_value و get_value در مدل Setting، نحوه ذخیره‌سازی API keys در settings.py (به ویژه endpoint update_api_keys)، و وجود هرگونه مکانیزم رمزگذاری موجود است. همچنین بررسی می‌شود که آیا کتابخانه cryptography.fernet یا مشابه آن در پروژه موجود است یا خیر. این مرحله فقط تحلیل است و هیچ تغییری در کد ایجاد نمی‌کند.
**Excerpt:**
```
در `backend/app/api/routes/settings.py` (خطوط 183-198 و 300-328)، کلیدهای API از طریق `Setting.set_value` با `value_type="encrypted"` ذخیره می‌شوند، اما بررسی `backend/app/models/setting.py` نشان می‌دهد که متد `set_value` هیچ رمزگذاری واقعی انجام نمی‌دهد و مقدار را به صورت plain text در دیتابیس SQLite ذخیره می‌کند.
```

### Step 6: ایجاد ماژول رمزگذاری (encryption.py) با توابع encrypt_value و decrypt_value
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد فایل جدید backend/app/core/encryption.py است. این ماژول شامل دو تابع اصلی encrypt_value و decrypt_value است که از کتابخانه cryptography.fernet برای رمزگذاری و رمزگشایی مقادیر استفاده می‌کنند. کلید رمزگذاری (master key) از environment variable با نام SETTINGS_ENCRYPTION_KEY خوانده می‌شود. اگر این متغیر وجود نداشت، یک کلید جدید تولید کرده و در لاگ هشدار می‌دهد. همچنین تابع get_encryption_key برای مدیریت کلید ایجاد می‌شود. این ماژول باید از cryptography.fernet استفاده کند و خطاهای مربوط به کلید نامعتبر را مدیریت کند.
**Excerpt:**
```
یک مکانیزم رمزگذاری واقعی (مانند `cryptography.fernet` یا `python-jose`) برای ذخیره‌سازی API keys در دیتابیس پیاده‌سازی کنید. متد `Setting.set_value` را اصلاح کنید تا قبل از ذخیره، مقدار را با یک کلید master که در environment variable (مثلاً `SETTINGS_ENCRYPTION_KEY`) ذخیره شده، رمزگذاری کند. متد `Setting.get_value` نیز باید رمزگشایی را انجام دهد.
```

### Step 7: اصلاح متد set_value در مدل Setting برای رمزگذاری مقادیر secret
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/models/setting.py است. متد set_value (یا کلاس Setting) اصلاح می‌شود تا قبل از ذخیره مقدار در دیتابیس، اگر پارامتر is_secret=True باشد یا value_type='encrypted' باشد، مقدار را با استفاده از تابع encrypt_value از ماژول encryption.py رمزگذاری کند. مقدار رمزگذاری شده در فیلد value ذخیره می‌شود. همچنین یک فیلد جدید مانند is_encrypted (Boolean) به مدل اضافه می‌شود تا مشخص کند آیا مقدار ذخیره شده رمزگذاری شده است یا خیر. این تغییر باید backward-compatible باشد یعنی مقادیر قبلی که رمزگذاری نشده‌اند، همچنان قابل خواندن باشند.
**Excerpt:**
```
متد `Setting.set_value` را اصلاح کنید تا قبل از ذخیره، مقدار را با یک کلید master که در environment variable (مثلاً `SETTINGS_ENCRYPTION_KEY`) ذخیره شده، رمزگذاری کند.
```

### Step 8: اصلاح متد get_value در مدل Setting برای رمزگشایی مقادیر secret
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/models/setting.py است. متد get_value (یا property value) اصلاح می‌شود تا هنگام خواندن مقدار از دیتابیس، اگر فیلد is_encrypted=True باشد، مقدار را با استفاده از تابع decrypt_value از ماژول encryption.py رمزگشایی کند و متن اصلی را برگرداند. اگر مقدار رمزگذاری نشده باشد (backward-compatibility)، همان مقدار plain text برگردانده می‌شود. این متد باید خطاهای رمزگشایی را مدیریت کند و در صورت عدم موفقیت، مقدار اصلی (رمزگذاری شده) را برگرداند یا خطای مناسب بدهد.
**Excerpt:**
```
متد `Setting.get_value` نیز باید رمزگشایی را انجام دهد.
```

### Step 9: به‌روزرسانی endpoint update_api_keys در settings.py برای استفاده از رمزگذاری واقعی
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/api/routes/settings.py است. endpoint update_api_keys (خطوط 183-198) که در حال حاضر value_type='encrypted' را تنظیم می‌کند اما رمزگذاری واقعی انجام نمی‌دهد، بررسی می‌شود. با توجه به تغییرات ایجاد شده در مدل Setting (مرحله 7)، این endpoint به صورت خودکار از رمزگذاری استفاده خواهد کرد. اما باید اطمینان حاصل شود که پارامتر is_secret=True به درستی به متد set_value ارسال می‌شود. همچنین بررسی می‌شود که آیا endpointهای دیگری در settings.py وجود دارند که API keys را ذخیره می‌کنند (مانند خطوط 300-328) و آن‌ها نیز اصلاح می‌شوند.
**Excerpt:**
```
در `backend/app/api/routes/settings.py` (خطوط 183-198 و 300-328)، کلیدهای API از طریق `Setting.set_value` با `value_type="encrypted"` ذخیره می‌شوند، اما بررسی `backend/app/models/setting.py` نشان می‌دهد که متد `set_value` هیچ رمزگذاری واقعی انجام نمی‌دهد.
```

### Step 10: به‌روزرسانی فایل .env.example برای اضافه کردن SETTINGS_ENCRYPTION_KEY
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/.env.example است. یک متغیر محیطی جدید با نام SETTINGS_ENCRYPTION_KEY به این فایل اضافه می‌شود که placeholder آن یک کلید نمونه (مثلاً 'your-32-byte-encryption-key-here') است. همچنین یک کامنت توضیحی اضافه می‌شود که این کلید برای رمزگذاری API Keys در دیتابیس استفاده می‌شود و باید حداقل 32 بایت باشد. همچنین بررسی می‌شود که آیا فایل .env.example حاوی placeholder برای API keys است که باید حذف یا به‌روزرسانی شود.
**Excerpt:**
```
فایل `backend/.env.example` حاوی placeholder برای API keys است که نشان‌دهنده وجود این کلیدها در محیط است.
```

### Step 11: اضافه کردن SETTINGS_ENCRYPTION_KEY به config.py و تولید خودکار کلید در صورت عدم وجود
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح فایل backend/app/core/config.py است. یک فیلد جدید به نام SETTINGS_ENCRYPTION_KEY به کلاس Settings اضافه می‌شود که مقدار آن از environment variable با همین نام خوانده می‌شود. اگر این متغیر در environment وجود نداشت، یک کلید جدید با استفاده از cryptography.fernet.Fernet.generate_key() تولید شده و در لاگ یک warning ثبت می‌شود که کلید به صورت خودکار تولید شده و در حافظه موقت است. این کلید تولید شده در یک متغیر ماژول سطح بالا ذخیره می‌شود تا در طول عمر برنامه پایدار بماند.
**Excerpt:**
```
کلید رمزگذاری (master key) برای رمزگذاری از environment variable (مثلاً `SETTINGS_ENCRYPTION_KEY`) ذخیره شده.
```

### Step 12: اجرای تست‌های موجود (pytest) برای اطمینان از عدم شکستگی
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای کامل تست‌های پروژه با دستور pytest است. هدف اطمینان از این است که تمام تغییرات ایجاد شده در مراحل قبل (اضافه کردن dependency JWT به routerها و اصلاح رمزگذاری) باعث شکستن تست‌های موجود نشده است. اگر تستی fail شود، باید بررسی و رفع شود. این مرحله شامل نوشتن تست جدید نیست.
**Excerpt:**
```
اعمال تغییر بدون شکستن تست‌های موجود [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]
```

### Step 13: اجرای linter (ruff/flake8) برای اطمینان از عدم وجود warning
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای linter پروژه (بر اساس فایل‌های راهنما: ruff یا flake8) بر روی فایل‌های تغییر یافته و کل پروژه backend است. هدف اطمینان از این است که کد جدید با استانداردهای پروژه مطابقت دارد و هیچ warning یا خطای linting وجود ندارد. اگر warning وجود داشت، باید رفع شود.
**Excerpt:**
```
linter بدون warning عبور می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["lint", "flake8", "pylint", "ruff"], "files_hint": ["backend/"]}]
```

### Step 14: اجرای type-checker (mypy) برای اطمینان از صحت type hints
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای type-checker پروژه (mypy) بر روی فایل‌های تغییر یافته و کل پروژه backend است. هدف اطمینان از این است که type hints جدید و تغییرات ایجاد شده با mypy سازگار هستند و هیچ خطای type checking وجود ندارد. اگر خطایی وجود داشت، باید رفع شود.
**Excerpt:**
```
type-check موفق است [verify_method=static] [verify_plan={"grep_patterns": ["mypy", "pyright", "type: ignore"], "files_hint": ["backend/"]}]
```
