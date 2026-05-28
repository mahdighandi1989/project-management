---
task_id: task_47c564b8072d
title: رفع باگ‌های مدیریت Session، خطا و اعتبارسنجی در API Routes بک‌اند
type: other
priority: critical
execution_priority: 1000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:15:51.118096+00:00'
updated_at: '2026-05-24T09:21:41.586768+00:00'
tags:
- consolidated
- post_verify_merge
target_files:
- docs/ARCHITECTURE.md
- docs/README.md
- docs/AUDIT_REPORT.md
- backend/app/api/routes/analysis.py
- backend/app/core/config.py
- backend/app/api/routes/simple_projects.py
- backend/app/api/routes/projects.py
- backend/app/api/routes/system_prompts.py
- backend/app/core/
- backend/app/main.py
- backend/app/api/routes/chat.py
- backend/app/core/logging_utils.py
- backend/app/api/routes/github_import.py
- backend/app/services/deep_analysis_service.py
- backend/app/core/database.py
- backend/app/api/routes/model_profiles.py
- backend/tests/test_runtime_verify_stage1.py
- backend/tests/test_security.py
- docs/ROADMAP.md
- backend/app/services/ai_manager.py
- backend/tests/test_runtime_verify_integration.py
- frontend/package.json
---

# رفع باگ‌های مدیریت Session، خطا و اعتبارسنجی در API Routes بک‌اند

## Raw Idea

🧬 این یک تسک تلفیقی است — از 8 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به مدیریت خطا، لاگینگ، Session دیتابیس و اعتبارسنجی ورودی در فایل‌های analysis.py و chat.py هستند. این تسک‌ها همگی به بهبود پایداری و امنیت API Routes مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به API Routes و مدیریت Session دیتابیس در بک‌اند
💎 estimated_difficulty: large

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 8
  id: 1ffe1e50-b675-40a2-8840-0b82a7a59677
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint تحلیل استریم (analysis.py)
  اولویت اصلی: critical
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال `project_path=../../etc` خطای 400 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run-stream", "headers": null, "json_body": {"project_path": "../../etc"}, "expected_status": 400, "required_fields": [], "json_contains": null}]
  - ارسال `project_path=/proc/1/environ` خطای 400 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run-stream", "headers": null, "json_body": {"project_path": "/proc/1/environ"}, "expected_status": 400, "required_fields": [], "json_contains": null}]
  - مسیرهای معتبر داخل `./projects` به درستی کار می‌کنند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run-stream", "headers": null, "json_body": {"project_path": "./projects/valid_project"}, "expected_status": 200, "required_fields": [], "json_contains": null}]
  - تست واحد برای path traversal اضافه شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_path_traversal", "timeout_seconds": 30}]

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
عدم اعتبارسنجی ورودی در endpoint تحلیل استریم (analysis.py)

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:126-180` — `run_analysis_stream` — مسیر ورودی کاربر بدون sanitization در os.walk و open استفاده شده
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Python standard library (os.walk, open)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 127) — محل آسیب‌پذیری اصلی
- `backend/app/core/config.py` (سطر 1) — محل مناسب برای تعریف ALLOWED_PROJECTS_DIR

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend در `frontend/src/app/analysis/page.tsx` (خط 190) فراخوانی می‌شود. هیچ middleware یا validator دیگری در مسیر درخواست وجود ندارد.

## 🔍 Context و وضعیت فعلی
در endpoint `POST /analysis/run-stream` (فایل `backend/app/api/routes/analysis.py`، خطوط 83-268)، پارامتر `project_path` مستقیماً از درخواست کاربر دریافت شده و بدون هیچ sanitization در `os.walk` و `open` استفاده می‌شود. مهاجم می‌تواند با ارسال مسیرهایی مثل `../../etc` یا `/proc/1/environ` به فایل‌های حساس سیستم دسترسی پیدا کند. همچنین `supported_extensions` فقط پسوند فایل را چک می‌کند و محتوای واقعی فایل را بررسی نمی‌کند. این آسیب‌پذیری Path Traversal کلاسیک است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال `project_path=../../etc` خطای 400 برمی‌گرداند
- [ ] ارسال `project_path=/proc/1/environ` خطای 400 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `./projects` به درستی کار می‌کنند
- [ ] تست واحد برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی و محدود کردن `project_path` به یک دایرکتوری مجاز (مثلاً `/tmp/projects` یا `./projects`). از `os.path.abspath` و `os.path.commonpath` برای اطمینان از اینکه مسیر نهایی خارج از محدوده مجاز نیست استفاده شود. همچنین محدودیت حجم فایل خوانده‌شده (مثلاً 1MB) و timeout برای کل عملیات اضافه شود.

## 💡 نمونه‌های قبل/بعد
**اعتبارسنجی مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
BASE_DIR = os.path.abspath('./projects')
user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR):
    raise HTTPException(400, 'Invalid project path')
for root, dirs, filenames in os.walk(user_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'`
- `pytest backend/tests/test_analysis.py -k path_traversal`

## ⚠️ ریسک‌ها و موارد احتیاط
بدون این فیکس، مهاجم می‌تواند تمام فایل‌های سرور را بخواند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 8
  id: a555551a-e741-4642-9f7b-55122ab94221
  عنوان اصلی: عدم مدیریت خطا و لاگینگ مناسب در API Routes
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/

📋 acceptance_criteria کامل:
  - همه route handlers دارای try-except باشند [verify_method=static] [verify_plan={"grep_patterns": ["try:", "except"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - خطاهای 500 به درستی لاگ شوند [verify_method=static] [verify_plan={"grep_patterns": ["logging.error", "logger.error", "log.error"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند [verify_method=static] [verify_plan={"grep_patterns": ["HTTPException", "status_code", "return JSONResponse"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - لاگ‌ها شامل timestamp, level, message, traceback باشند [verify_method=static] [verify_plan={"grep_patterns": ["timestamp", "level", "message", "traceback"], "files_hint": ["backend/app/core/"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

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


## 🎯 هدف
عدم مدیریت خطا و لاگینگ مناسب در API Routes

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن exception handler middleware و logging configuration
- `backend/app/api/routes/analysis.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد
- `backend/app/api/routes/chat.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, structlog/loguru, Python logging

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
مدیریت خطا و لاگینگ برای پایداری و عیب‌یابی پروژه ضروری است. بدون آن، خطاهای تولید (production) قابل ردیابی نیستند.

## 🔍 Context و وضعیت فعلی
با بررسی نمونه فایل‌های routes (مانند analysis.py, chat.py, projects.py)، مشخص نیست که مدیریت خطا (exception handling) و لاگینگ به صورت سیستماتیک پیاده‌سازی شده باشد. این موضوع باعث می‌شود خطاهای runtime به درستی ثبت نشوند و عیب‌یابی دشوار شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] همه route handlers دارای try-except باشند
- [ ] خطاهای 500 به درستی لاگ شوند
- [ ] پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند
- [ ] لاگ‌ها شامل timestamp, level, message, traceback باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware برای مدیریت خطاهای سراسری (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru. همچنین اضافه کردن try-except در تمام route handlers و بازگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx).

## 💡 نمونه‌های قبل/بعد
**قبل: عدم مدیریت خطا**

_قبل:_
```
@router.get('/projects')
async def get_projects():
    return await service.get_all()
```

_بعد:_
```
@router.get('/projects')
async def get_projects():
    try:
        return await service.get_all()
    except Exception as e:
        logger.error('Failed to get projects', exc_info=e)
        raise HTTPException(status_code=500, detail='Internal server error')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd backend && python -c "from app.main import app; print('OK')"`
- `curl -X GET http://localhost:8000/api/projects/invalid-endpoint`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در مدیریت خطا ممکن است باعث تغییر رفتار API شود. نیاز به تست کامل endpoints.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 8
  id: 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd
  عنوان اصلی: نبود Rate Limiting و Input Validation در API Endpoints
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/

📋 acceptance_criteria کامل:
  - Rate limiting برای تمام AI endpoints فعال باشد [verify_method=static] [verify_plan={"grep_patterns": ["RateLimiter", "rate_limit", "limiter"], "files_hint": ["backend/app/core/", "backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - پس از تجاوز از محدودیت، پاسخ 429 Too Many Requests برگردانده شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/chat", "headers": null, "json_body": {"message": "test"}, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - Input validation با Pydantic برای تمام endpoints پیاده‌سازی شده باشد [verify_method=static] [verify_plan={"grep_patterns": ["BaseModel", "Field", "validator", "pydantic"], "files_hint": ["backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - محدودیت‌ها قابل تنظیم از طریق متغیرهای محیطی باشند [verify_method=static] [verify_plan={"grep_patterns": ["os.getenv", "environ.get", "RATE_LIMIT", "MAX_REQUESTS"], "files_hint": ["backend/app/core/"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

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


## 🎯 هدف
نبود Rate Limiting و Input Validation در API Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن rate limiter middleware
- `backend/app/api/routes/chat.py` — Endpoint حساس که نیاز به rate limiting دارد
- `backend/app/api/routes/analysis.py` — Endpoint حساس که نیاز به rate limiting دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, slowapi, Pydantic

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
Rate limiting برای محافظت در برابر سوءاستفاده و کنترل هزینه‌ها ضروری است. Input validation برای جلوگیری از حملات injection حیاتی است.

## 🔍 Context و وضعیت فعلی
با توجه به وجود endpoints برای AI calls (chat, analysis, debate) که هزینه‌بر هستند، نبود rate limiting می‌تواند منجر به حملات DoS و هزینه‌های غیرمنتظره شود. همچنین نبود input validation مناسب می‌تواند باعث injection attacks شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] Rate limiting برای تمام AI endpoints فعال باشد
- [ ] پس از تجاوز از محدودیت، پاسخ 429 Too Many Requests برگردانده شود
- [ ] Input validation با Pydantic برای تمام endpoints پیاده‌سازی شده باشد
- [ ] محدودیت‌ها قابل تنظیم از طریق متغیرهای محیطی باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن rate limiting با استفاده از کتابخانه slowapi یا middleware سفارشی. پیاده‌سازی input validation با Pydantic models (که احتمالاً وجود دارند اما باید بررسی شوند). محدود کردن نرخ درخواست‌ها به AI endpoints به صورت جداگانه.

## 💡 نمونه‌های قبل/بعد
**قبل: بدون rate limiting**

_قبل:_
```
@router.post('/chat')
async def chat(request: ChatRequest):
    # بدون محدودیت نرخ
```

_بعد:_
```
@router.post('/chat')
@limiter.limit('10/minute')
async def chat(request: ChatRequest):
    # با محدودیت نرخ
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'`
- `for i in {1..20}; do curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' &; done`

## ⚠️ ریسک‌ها و موارد احتیاط
Rate limiting ممکن است کاربران قانونی را تحت تأثیر قرار دهد. نیاز به تنظیم دقیق محدودیت‌ها.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 8
  id: 979942ad-03ba-4cd6-a5ba-dd563d8d5462
  عنوان اصلی: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - session در `run_analysis_stream` در finally بسته شود [verify_method=static] [verify_plan={"grep_patterns": ["analysis_db\\.close\\(\\)", "finally"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - هیچ نشت connection در لاگ‌ها دیده نشود [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
  - تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_stress_100_concurrent", "timeout_seconds": 120}]

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
مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:115-124` — `run_analysis_task` — این session در finally بسته نمی‌شود
  ```python
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

- `backend/app/services/deep_analysis_service.py` (سطر 1) — این سرویس session را دریافت می‌کند و ممکن است آن را مدیریت کند

## 🌐 نقشهٔ وابستگی‌ها
این باگ در endpoint استریمینگ analysis رخ می‌دهد که توسط `frontend/src/app/analysis/page.tsx` (خط 190) فراخوانی می‌شود.

## 🔍 Context و وضعیت فعلی
در فایل `backend/app/api/routes/analysis.py`، توابع `get_analysis_reports`، `get_analysis_report`، `delete_analysis_report` و `download_analysis_report` از الگوی `SessionLocal()` استفاده می‌کنند و session را در `finally` می‌بندند. اما در `run_analysis_stream` (خط 117)، یک `analysis_db = SessionLocal()` ایجاد می‌شود که در `finally` بسته نمی‌شود. اگر خطایی در `run_analysis_task` رخ دهد، session باز می‌ماند و باعث نشت connection در SQLite می‌شود. همچنین در `backend/app/api/routes/github_import.py`، تابع `import_repository` (خط 137) یک `db_session = SessionLocal()` ایجاد می‌کند و در `finally` می‌بندد، اما اگر `auto_setup_project_memory` خطا بدهد، session همچنان بسته می‌شود. مشکل اصلی در `analysis.py` است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] session در `run_analysis_stream` در finally بسته شود
- [ ] هیچ نشت connection در لاگ‌ها دیده نشود
- [ ] تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در `run_analysis_stream`، session ایجاد شده در خط 117 را در `finally` ببندید. همچنین بررسی کنید که آیا `DeepAnalysisService` ownership session را می‌گیرد یا خیر. اگر سرویس session را مدیریت می‌کند، نیازی به بستن در اینجا نیست، اما اگر ownership با این تابع است، حتماً بسته شود.

## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
analysis_db = SessionLocal()
# ... استفاده ...
# finally: بسته نمی‌شود
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    # ... استفاده ...
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k analysis_stream`
- `بررسی لاگ‌ها برای 'DB connection leak'`

## ⚠️ ریسک‌ها و موارد احتیاط
کم — فقط اضافه کردن finally block

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 8
  id: 49be9ac4-ed23-4874-975e-841175c6974b
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال project_path='../../etc/' با خطای 400 رد شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run-stream", "headers": null, "json_body": {"project_path": "../../etc/"}, "expected_status": 400, "required_fields": ["error"], "json_contains": null}]
  - مسیرهای درون /app/projects مجاز باشند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run-stream", "headers": null, "json_body": {"project_path": "/app/projects/valid_project"}, "expected_status": 200, "required_fields": [], "json_contains": nu]
  - تست واحد جدید برای path traversal اضافه شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_path_traversal_rejected", "timeout_seconds": 60}]

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
عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:84-268` — `run_analysis_stream` — کل endpoint نیاز به validation مسیر دارد
  ```python
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      project_path = request.project_path  # ⚠️ user-supplied, no validation
      ...
      for root, dirs, filenames in os.walk(project_path):  # ⚠️ path traversal
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Python os.walk + Pydantic models

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 127) — محل اصلی آسیب‌پذیری
- `backend/app/models/analysis_report.py` (سطر 1) — مدل AnalysisRequest که project_path را تعریف می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend/src/app/analysis/page.tsx (خط 190) فراخوانی می‌شود. هیچ middleware یا dependency دیگری مسیر را قبل از رسیدن به این تابع validation نمی‌کند.

## 🔍 Context و وضعیت فعلی
در فایل backend/app/api/routes/analysis.py، endpoint run_analysis_stream (خط 84) پارامتر project_path را مستقیماً از درخواست کاربر دریافت کرده و در os.walk (خط 160) بدون هیچ sanitization استفاده می‌کند. این آسیب‌پذیری Path Traversal امکان خواندن فایل‌های خارج از مسیر پروژه را فراهم می‌کند. همچنین در خط 133-141، README از مسیر user-supplied خوانده می‌شود. مهاجم می‌تواند با ارسال project_path='../../etc/' فایل‌های حساس سیستم را بخواند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path='../../etc/' با خطای 400 رد شود
- [ ] مسیرهای درون /app/projects مجاز باشند
- [ ] تست واحد جدید برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اضافه کردن اعتبارسنجی مسیر: 1) استفاده از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز است. 2) تعریف یک ریشه مجاز (مثلاً /projects یا /data) و reject کردن مسیرهای خارج از آن. 3) اضافه کردن validation با Pydantic برای project_path که الگوی مسیر امن را enforce کند.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن validation مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
from pathlib import Path

ALLOWED_BASE = Path('/app/projects').resolve()
user_path = Path(request.project_path).resolve()
if not str(user_path).startswith(str(ALLOWED_BASE)):
    raise HTTPException(400, 'Invalid project path')
project_path = str(user_path)
for root, dirs, filenames in os.walk(project_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc/"}'`
- `pytest backend/tests/test_security.py -k path_traversal`

## ⚠️ ریسک‌ها و موارد احتیاط
کم — تغییر فقط validation است و منطق business را تغییر نمی‌دهد

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 8
  id: 866ea2f9-0e88-4848-9c2a-d9b72c654747
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "../../etc/passwd"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - ارسال مسیر `/etc/` خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/etc/"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - مسیرهای معتبر داخل `/ [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/valid/path"}, "expected_status": 200, "required_fields": ["result"], "json_contains": null}]

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
عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — فیلد project_path بدون validator است
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_task` — استفاده مستقیم از project_path در os.walk بدون اعتبارسنجی
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Python os.walk + Pydantic

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 46) — فایل اصلی حاوی endpoint آسیب‌پذیر
- `backend/app/services/deep_analysis_service.py` (سطر 1) — سرویسی که فایل‌ها را دریافت و پردازش می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend در `frontend/src/app/analysis/page.tsx` (خط 190) فراخوانی می‌شود. هیچ middleware یا guardian در frontend برای محدود کردن مسیر وجود ندارد.

## 🔍 Context و وضعیت فعلی
در فایل `backend/app/api/routes/analysis.py`، endpoint `POST /analysis/run` و `POST /analysis/run-stream` از مدل Pydantic `AnalysisRequest` استفاده می‌کنند که فیلد `project_path` از نوع `str` است. هیچ اعتبارسنجی روی این فیلد انجام نمی‌شود و در خطوط 127-180، این مسیر مستقیماً در `os.walk` و `open` استفاده می‌شود. این آسیب‌پذیری امکان Path Traversal را فراهم می‌کند: مهاجم می‌تواند با ارسال مسیرهایی مانند `../../etc/passwd` یا `/etc/` فایل‌های حساس سیستم را بخواند. همچنین در خط 137، فایل‌ها با `encoding='utf-8'` باز می‌شوند که در صورت خطا، خطا نادیده گرفته می‌شود (pass) و این می‌تواند منجر به نشت اطلاعات در لاگ‌ها شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند
- [ ] ارسال مسیر `/etc/` خطای 422 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `/
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی مسیر پروژه با استفاده از `os.path.abspath` و `os.path.commonpath` برای جلوگیری از Path Traversal. همچنین محدود کردن مسیر به یک دایرکتوری مجاز (مثلاً `/projects`).

## 💡 نمونه‌های قبل/بعد
**اضافه کردن validator به Pydantic مدل**

_قبل:_
```
project_path: str
```

_بعد:_
```
project_path: str = Field(..., description="مسیر پروژه")

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        abs_path = os.path.abspath(v)
        allowed_base = os.path.abspath(os.environ.get('PROJECTS_BASE_DIR', '/projects'))
        if not abs_path.startswith(allowed_base):
            raise ValueError(f'Path must be within {allowed_base}')
        if not os.path.isdir(abs_path):
            raise ValueError('Path must be an existing directory')
        return abs_path
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
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 8
  id: 51fab7d9-dba0-486e-8e29-77a459785fc3
  عنوان اصلی: نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند [verify_method=static] [verify_plan={"grep_patterns": ["SessionLocal\\(\\)"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - همه endpointها از Depends(get_db) یا async context manager استفاده کنند [verify_method=static] [verify_plan={"grep_patterns": ["Depends\\(get_db\\)", "async with.*get_db"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/model_profiles.py", "backend/app/api/routes/project_health]
  - تست نشت connection با 1000 درخواست هم‌زمان پاس شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_db_connection_leak.py::test_concurrent_requests_no_leak", "timeout_seconds": 120}]

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
نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:277-290` — `get_analysis_reports` — این تابع درست بسته می‌شود — الگو را به بقیه تعمیم بده
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
      return ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:293-306` — `get_analysis_report` — استثناء قبل از finally باعث نشت می‌شود — باید db را قبل از raise ببندیم یا از context manager استفاده کنیم
  ```python
  db = SessionLocal()
  try:
      report = db.query(...).first()
      if not report:
          raise HTTPException(...)  # ⚠️ اینجا db بسته نمی‌شود
      return ...
  finally:
      db.close()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + SQLite

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 277) — همه endpointهای analysis که SessionLocal مستقیم می‌سازند
- `backend/app/core/database.py` (سطر 1) — تعریف SessionLocal و get_db

## 🌐 نقشهٔ وابستگی‌ها
این باگ روی تمام endpointهایی که از SessionLocal مستقیم استفاده می‌کنند تأثیر دارد: analysis.py (5 endpoint), model_profiles.py (احتمالاً).

## 🔍 Context و وضعیت فعلی
در چندین endpoint (analysis.py, model_profiles.py, project_health.py) Session دیتابیس با `SessionLocal()` ساخته می‌شود اما در مسیرهای خطا (Exception) بسته نمی‌شود. این باعث نشت connection و در نهایت exhaustion pool دیتابیس می‌شود. نمونه: analysis.py خطوط 277-290 و 293-306 و 309-325 و 328-370 — همه از `SessionLocal()` استفاده می‌کنند و `db.close()` را در `finally` ندارند. در model_profiles.py خطوط 248-350 نیز `db` از `Depends(get_db)` می‌آید که احتمالاً مدیریت می‌شود ولی در analysis.py مستقیماً `SessionLocal()` ساخته می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند
- [ ] همه endpointها از Depends(get_db) یا async context manager استفاده کنند
- [ ] تست نشت connection با 1000 درخواست هم‌زمان پاس شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. تمام `SessionLocal()` ها را با context manager یا try/finally جایگزین کن تا در همه مسیرها (موفقیت و خطا) session بسته شود. یا از `Depends(get_db)` در همه endpointها استفاده کن.

## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
db = SessionLocal()
try:
    ...
    raise HTTPException(...)
finally:
    db.close()
```

_بعد:_
```
async with SessionLocal() as db:
    ...
    raise HTTPException(...)
# خودکار بسته می‌شود
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/api/routes/`
- `pytest backend/tests/ -k db_session`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در signature endpointها ممکن است frontend را بشکند اگر response type تغییر کند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 8
  id: 037dbd0d-9561-4c00-be73-7bc923e2565b
  عنوان اصلی: exception swallowed در run_analysis_stream بدون لاگ کافی
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run", "headers": null, "json_body": {"analysis_type": "deep", "target": "test"}, "expected_status": 200, "required_fields": [], "json_contains": null}]
  - اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت ارسال می [verify_method=static] [verify_plan={"grep_patterns": ["except Exception", "json.dumps", "fallback_error_message"], "files_hint": ["backend/app/api/routes/analysis.py"]}]

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
exception swallowed در run_analysis_stream بدون لاگ کافی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:251-253` — `generate_events` — اگر json.dumps روی str(e) خطا بدهد، این except هم بلعیده می‌شود
  ```python
  except Exception as e:
              logger.error(f"Error in SSE stream: {e}")
              yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
  ```
- `backend/app/api/routes/analysis.py:200-206` — `run_analysis_task` — اگر progress_queue.put خطا بدهد (صف بسته)، خطا بلعیده می‌شود
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                  await progress_queue.put({
                      "event": "error",
                      "message": str(e),
                      "error": True
                  })
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SSE streaming + asyncio.Queue

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/deep_analysis_service.py` (سطر 1) — run_full_analysis که از اینجا صدا زده می‌شود ممکن است خطاهای بیشتری تولید کند

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend در analysis/page.tsx (خط ۱۹۰) استفاده می‌شود. اگر خطا بلعیده شود، کاربر تا ۳۰ ثانیه heartbeat می‌بیند و بعد timeout می‌خورد.

## 🔍 Context و وضعیت فعلی
در `backend/app/api/routes/analysis.py` خط ۲۵۱-۲۵۳، یک `except Exception as e` عام وجود دارد که خطا را فقط با `logger.error` لاگ می‌کند و سپس یک رویداد `error` به SSE stream می‌فرستد. اما اگر خطا در حین ارسال رویداد `error` رخ دهد (مثلاً `json.dumps` روی یک شیء غیرقابل سریال‌سازی)، آن خطا هم بلعیده می‌شود و کاربر هیچ بازخوردی نمی‌بیند. همچنین در خط ۲۰۰-۲۰۶، خطاهای `run_full_analysis` در try/except داخلی گرفته می‌شوند و فقط یک رویداد `error` به صف اضافه می‌شود، اما اگر `progress_queue.put` خودش خطا بدهد (مثلاً صف بسته شده باشد)، آن خطا هم بلعیده می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند
- [ ] اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت ارسال می
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. در `except Exception as e` خط ۲۵۱، یک try/except تو در تو برای ارسال رویداد خطا اضافه کن. ۲. در خط ۲۰۰-۲۰۶، بعد از `progress_queue.put` یک `try/except` بگذار که اگر صف خطا داد، حداقل با `logger.critical` لاگ شود. ۳. یک `finally` در سطح `generate_events` اضافه کن که اگر خطای غیرمنتظره‌ای رخ داد، یک رویداد `fatal` با پیام ثابت به صف اضافه کند.

## 💡 نمونه‌های قبل/بعد
**ایمن‌سازی ارسال رویداد خطا**

_قبل:_
```
yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

_بعد:_
```
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
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
- نوع: bug
- اولویت: high
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
- در commit message: `merged-from: 1ffe1e50-b675-40a2-8840-0b82a7a59677, a555551a-e741-4642-9f7b-55122ab94221, 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd, 979942ad-03ba-4cd6-a5ba-dd563d8d5462, 49be9ac4-ed23-4874-975e-841175c6974b, 866ea2f9-0e88-4848-9c2a-d9b72c654747, 51fab7d9-dba0-486e-8e29-77a459785fc3, 037dbd0d-9561-4c00-be73-7bc923e2565b`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند

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


---

## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)
_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند.)_

```
🧬 این یک تسک تلفیقی است — از 8 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به مدیریت خطا، لاگینگ، Session دیتابیس و اعتبارسنجی ورودی در فایل‌های analysis.py و chat.py هستند. این تسک‌ها همگی به بهبود پایداری و امنیت API Routes مرتبط هستند.
🎯 theme: رفع باگ‌های مربوط به API Routes و مدیریت Session دیتابیس در بک‌اند
💎 estimated_difficulty: large

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 8
  id: 1ffe1e50-b675-40a2-8840-0b82a7a59677
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint تحلیل استریم (analysis.py)
  اولویت اصلی: critical
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال `project_path=../../etc` خطای 400 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run-stream", "headers": null, "json_body": {"project_path": "../../etc"}, "expected_status": 400, "required_fields": [], "json_contains": null}]
  - ارسال `project_path=/proc/1/environ` خطای 400 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run-stream", "headers": null, "json_body": {"project_path": "/proc/1/environ"}, "expected_status": 400, "required_fields": [], "json_contains": null}]
  - مسیرهای معتبر داخل `./projects` به درستی کار می‌کنند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run-stream", "headers": null, "json_body": {"project_path": "./projects/valid_project"}, "expected_status": 200, "required_fields": [], "json_contains": null}]
  - تست واحد برای path traversal اضافه شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_path_traversal", "timeout_seconds": 30}]

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
عدم اعتبارسنجی ورودی در endpoint تحلیل استریم (analysis.py)

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:126-180` — `run_analysis_stream` — مسیر ورودی کاربر بدون sanitization در os.walk و open استفاده شده
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Python standard library (os.walk, open)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 127) — محل آسیب‌پذیری اصلی
- `backend/app/core/config.py` (سطر 1) — محل مناسب برای تعریف ALLOWED_PROJECTS_DIR

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend در `frontend/src/app/analysis/page.tsx` (خط 190) فراخوانی می‌شود. هیچ middleware یا validator دیگری در مسیر درخواست وجود ندارد.

## 🔍 Context و وضعیت فعلی
در endpoint `POST /analysis/run-stream` (فایل `backend/app/api/routes/analysis.py`، خطوط 83-268)، پارامتر `project_path` مستقیماً از درخواست کاربر دریافت شده و بدون هیچ sanitization در `os.walk` و `open` استفاده می‌شود. مهاجم می‌تواند با ارسال مسیرهایی مثل `../../etc` یا `/proc/1/environ` به فایل‌های حساس سیستم دسترسی پیدا کند. همچنین `supported_extensions` فقط پسوند فایل را چک می‌کند و محتوای واقعی فایل را بررسی نمی‌کند. این آسیب‌پذیری Path Traversal کلاسیک است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال `project_path=../../etc` خطای 400 برمی‌گرداند
- [ ] ارسال `project_path=/proc/1/environ` خطای 400 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `./projects` به درستی کار می‌کنند
- [ ] تست واحد برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی و محدود کردن `project_path` به یک دایرکتوری مجاز (مثلاً `/tmp/projects` یا `./projects`). از `os.path.abspath` و `os.path.commonpath` برای اطمینان از اینکه مسیر نهایی خارج از محدوده مجاز نیست استفاده شود. همچنین محدودیت حجم فایل خوانده‌شده (مثلاً 1MB) و timeout برای کل عملیات اضافه شود.

## 💡 نمونه‌های قبل/بعد
**اعتبارسنجی مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
BASE_DIR = os.path.abspath('./projects')
user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR):
    raise HTTPException(400, 'Invalid project path')
for root, dirs, filenames in os.walk(user_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'`
- `pytest backend/tests/test_analysis.py -k path_traversal`

## ⚠️ ریسک‌ها و موارد احتیاط
بدون این فیکس، مهاجم می‌تواند تمام فایل‌های سرور را بخواند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 8
  id: a555551a-e741-4642-9f7b-55122ab94221
  عنوان اصلی: عدم مدیریت خطا و لاگینگ مناسب در API Routes
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/

📋 acceptance_criteria کامل:
  - همه route handlers دارای try-except باشند [verify_method=static] [verify_plan={"grep_patterns": ["try:", "except"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - خطاهای 500 به درستی لاگ شوند [verify_method=static] [verify_plan={"grep_patterns": ["logging.error", "logger.error", "log.error"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند [verify_method=static] [verify_plan={"grep_patterns": ["HTTPException", "status_code", "return JSONResponse"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - لاگ‌ها شامل timestamp, level, message, traceback باشند [verify_method=static] [verify_plan={"grep_patterns": ["timestamp", "level", "message", "traceback"], "files_hint": ["backend/app/core/"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

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


## 🎯 هدف
عدم مدیریت خطا و لاگینگ مناسب در API Routes

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن exception handler middleware و logging configuration
- `backend/app/api/routes/analysis.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد
- `backend/app/api/routes/chat.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, structlog/loguru, Python logging

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
مدیریت خطا و لاگینگ برای پایداری و عیب‌یابی پروژه ضروری است. بدون آن، خطاهای تولید (production) قابل ردیابی نیستند.

## 🔍 Context و وضعیت فعلی
با بررسی نمونه فایل‌های routes (مانند analysis.py, chat.py, projects.py)، مشخص نیست که مدیریت خطا (exception handling) و لاگینگ به صورت سیستماتیک پیاده‌سازی شده باشد. این موضوع باعث می‌شود خطاهای runtime به درستی ثبت نشوند و عیب‌یابی دشوار شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] همه route handlers دارای try-except باشند
- [ ] خطاهای 500 به درستی لاگ شوند
- [ ] پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند
- [ ] لاگ‌ها شامل timestamp, level, message, traceback باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware برای مدیریت خطاهای سراسری (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru. همچنین اضافه کردن try-except در تمام route handlers و بازگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx).

## 💡 نمونه‌های قبل/بعد
**قبل: عدم مدیریت خطا**

_قبل:_
```
@router.get('/projects')
async def get_projects():
    return await service.get_all()
```

_بعد:_
```
@router.get('/projects')
async def get_projects():
    try:
        return await service.get_all()
    except Exception as e:
        logger.error('Failed to get projects', exc_info=e)
        raise HTTPException(status_code=500, detail='Internal server error')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd backend && python -c "from app.main import app; print('OK')"`
- `curl -X GET http://localhost:8000/api/projects/invalid-endpoint`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در مدیریت خطا ممکن است باعث تغییر رفتار API شود. نیاز به تست کامل endpoints.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 8
  id: 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd
  عنوان اصلی: نبود Rate Limiting و Input Validation در API Endpoints
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/

📋 acceptance_criteria کامل:
  - Rate limiting برای تمام AI endpoints فعال باشد [verify_method=static] [verify_plan={"grep_patterns": ["RateLimiter", "rate_limit", "limiter"], "files_hint": ["backend/app/core/", "backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - پس از تجاوز از محدودیت، پاسخ 429 Too Many Requests برگردانده شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/chat", "headers": null, "json_body": {"message": "test"}, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - Input validation با Pydantic برای تمام endpoints پیاده‌سازی شده باشد [verify_method=static] [verify_plan={"grep_patterns": ["BaseModel", "Field", "validator", "pydantic"], "files_hint": ["backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - محدودیت‌ها قابل تنظیم از طریق متغیرهای محیطی باشند [verify_method=static] [verify_plan={"grep_patterns": ["os.getenv", "environ.get", "RATE_LIMIT", "MAX_REQUESTS"], "files_hint": ["backend/app/core/"]}]

📝 idea_prompt اصلی (بدون تغییر و بدون خلاصه‌سازی):
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

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


## 🎯 هدف
نبود Rate Limiting و Input Validation در API Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن rate limiter middleware
- `backend/app/api/routes/chat.py` — Endpoint حساس که نیاز به rate limiting دارد
- `backend/app/api/routes/analysis.py` — Endpoint حساس که نیاز به rate limiting دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, slowapi, Pydantic

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
Rate limiting برای محافظت در برابر سوءاستفاده و کنترل هزینه‌ها ضروری است. Input validation برای جلوگیری از حملات injection حیاتی است.

## 🔍 Context و وضعیت فعلی
با توجه به وجود endpoints برای AI calls (chat, analysis, debate) که هزینه‌بر هستند، نبود rate limiting می‌تواند منجر به حملات DoS و هزینه‌های غیرمنتظره شود. همچنین نبود input validation مناسب می‌تواند باعث injection attacks شود.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] Rate limiting برای تمام AI endpoints فعال باشد
- [ ] پس از تجاوز از محدودیت، پاسخ 429 Too Many Requests برگردانده شود
- [ ] Input validation با Pydantic برای تمام endpoints پیاده‌سازی شده باشد
- [ ] محدودیت‌ها قابل تنظیم از طریق متغیرهای محیطی باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن rate limiting با استفاده از کتابخانه slowapi یا middleware سفارشی. پیاده‌سازی input validation با Pydantic models (که احتمالاً وجود دارند اما باید بررسی شوند). محدود کردن نرخ درخواست‌ها به AI endpoints به صورت جداگانه.

## 💡 نمونه‌های قبل/بعد
**قبل: بدون rate limiting**

_قبل:_
```
@router.post('/chat')
async def chat(request: ChatRequest):
    # بدون محدودیت نرخ
```

_بعد:_
```
@router.post('/chat')
@limiter.limit('10/minute')
async def chat(request: ChatRequest):
    # با محدودیت نرخ
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'`
- `for i in {1..20}; do curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' &; done`

## ⚠️ ریسک‌ها و موارد احتیاط
Rate limiting ممکن است کاربران قانونی را تحت تأثیر قرار دهد. نیاز به تنظیم دقیق محدودیت‌ها.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 8
  id: 979942ad-03ba-4cd6-a5ba-dd563d8d5462
  عنوان اصلی: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - session در `run_analysis_stream` در finally بسته شود [verify_method=static] [verify_plan={"grep_patterns": ["analysis_db\\.close\\(\\)", "finally"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - هیچ نشت connection در لاگ‌ها دیده نشود [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
  - تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_stress_100_concurrent", "timeout_seconds": 120}]

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
مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:115-124` — `run_analysis_task` — این session در finally بسته نمی‌شود
  ```python
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

- `backend/app/services/deep_analysis_service.py` (سطر 1) — این سرویس session را دریافت می‌کند و ممکن است آن را مدیریت کند

## 🌐 نقشهٔ وابستگی‌ها
این باگ در endpoint استریمینگ analysis رخ می‌دهد که توسط `frontend/src/app/analysis/page.tsx` (خط 190) فراخوانی می‌شود.

## 🔍 Context و وضعیت فعلی
در فایل `backend/app/api/routes/analysis.py`، توابع `get_analysis_reports`، `get_analysis_report`، `delete_analysis_report` و `download_analysis_report` از الگوی `SessionLocal()` استفاده می‌کنند و session را در `finally` می‌بندند. اما در `run_analysis_stream` (خط 117)، یک `analysis_db = SessionLocal()` ایجاد می‌شود که در `finally` بسته نمی‌شود. اگر خطایی در `run_analysis_task` رخ دهد، session باز می‌ماند و باعث نشت connection در SQLite می‌شود. همچنین در `backend/app/api/routes/github_import.py`، تابع `import_repository` (خط 137) یک `db_session = SessionLocal()` ایجاد می‌کند و در `finally` می‌بندد، اما اگر `auto_setup_project_memory` خطا بدهد، session همچنان بسته می‌شود. مشکل اصلی در `analysis.py` است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] session در `run_analysis_stream` در finally بسته شود
- [ ] هیچ نشت connection در لاگ‌ها دیده نشود
- [ ] تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در `run_analysis_stream`، session ایجاد شده در خط 117 را در `finally` ببندید. همچنین بررسی کنید که آیا `DeepAnalysisService` ownership session را می‌گیرد یا خیر. اگر سرویس session را مدیریت می‌کند، نیازی به بستن در اینجا نیست، اما اگر ownership با این تابع است، حتماً بسته شود.

## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
analysis_db = SessionLocal()
# ... استفاده ...
# finally: بسته نمی‌شود
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    # ... استفاده ...
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k analysis_stream`
- `بررسی لاگ‌ها برای 'DB connection leak'`

## ⚠️ ریسک‌ها و موارد احتیاط
کم — فقط اضافه کردن finally block

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 8
  id: 49be9ac4-ed23-4874-975e-841175c6974b
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال project_path='../../etc/' با خطای 400 رد شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run-stream", "headers": null, "json_body": {"project_path": "../../etc/"}, "expected_status": 400, "required_fields": ["error"], "json_contains": null}]
  - مسیرهای درون /app/projects مجاز باشند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run-stream", "headers": null, "json_body": {"project_path": "/app/projects/valid_project"}, "expected_status": 200, "required_fields": [], "json_contains": nu]
  - تست واحد جدید برای path traversal اضافه شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_path_traversal_rejected", "timeout_seconds": 60}]

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
عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:84-268` — `run_analysis_stream` — کل endpoint نیاز به validation مسیر دارد
  ```python
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      project_path = request.project_path  # ⚠️ user-supplied, no validation
      ...
      for root, dirs, filenames in os.walk(project_path):  # ⚠️ path traversal
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Python os.walk + Pydantic models

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 127) — محل اصلی آسیب‌پذیری
- `backend/app/models/analysis_report.py` (سطر 1) — مدل AnalysisRequest که project_path را تعریف می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend/src/app/analysis/page.tsx (خط 190) فراخوانی می‌شود. هیچ middleware یا dependency دیگری مسیر را قبل از رسیدن به این تابع validation نمی‌کند.

## 🔍 Context و وضعیت فعلی
در فایل backend/app/api/routes/analysis.py، endpoint run_analysis_stream (خط 84) پارامتر project_path را مستقیماً از درخواست کاربر دریافت کرده و در os.walk (خط 160) بدون هیچ sanitization استفاده می‌کند. این آسیب‌پذیری Path Traversal امکان خواندن فایل‌های خارج از مسیر پروژه را فراهم می‌کند. همچنین در خط 133-141، README از مسیر user-supplied خوانده می‌شود. مهاجم می‌تواند با ارسال project_path='../../etc/' فایل‌های حساس سیستم را بخواند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path='../../etc/' با خطای 400 رد شود
- [ ] مسیرهای درون /app/projects مجاز باشند
- [ ] تست واحد جدید برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اضافه کردن اعتبارسنجی مسیر: 1) استفاده از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز است. 2) تعریف یک ریشه مجاز (مثلاً /projects یا /data) و reject کردن مسیرهای خارج از آن. 3) اضافه کردن validation با Pydantic برای project_path که الگوی مسیر امن را enforce کند.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن validation مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
from pathlib import Path

ALLOWED_BASE = Path('/app/projects').resolve()
user_path = Path(request.project_path).resolve()
if not str(user_path).startswith(str(ALLOWED_BASE)):
    raise HTTPException(400, 'Invalid project path')
project_path = str(user_path)
for root, dirs, filenames in os.walk(project_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc/"}'`
- `pytest backend/tests/test_security.py -k path_traversal`

## ⚠️ ریسک‌ها و موارد احتیاط
کم — تغییر فقط validation است و منطق business را تغییر نمی‌دهد

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 8
  id: 866ea2f9-0e88-4848-9c2a-d9b72c654747
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "../../etc/passwd"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - ارسال مسیر `/etc/` خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/etc/"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - مسیرهای معتبر داخل `/ [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/valid/path"}, "expected_status": 200, "required_fields": ["result"], "json_contains": null}]

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
عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — فیلد project_path بدون validator است
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_task` — استفاده مستقیم از project_path در os.walk بدون اعتبارسنجی
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Python os.walk + Pydantic

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 46) — فایل اصلی حاوی endpoint آسیب‌پذیر
- `backend/app/services/deep_analysis_service.py` (سطر 1) — سرویسی که فایل‌ها را دریافت و پردازش می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend در `frontend/src/app/analysis/page.tsx` (خط 190) فراخوانی می‌شود. هیچ middleware یا guardian در frontend برای محدود کردن مسیر وجود ندارد.

## 🔍 Context و وضعیت فعلی
در فایل `backend/app/api/routes/analysis.py`، endpoint `POST /analysis/run` و `POST /analysis/run-stream` از مدل Pydantic `AnalysisRequest` استفاده می‌کنند که فیلد `project_path` از نوع `str` است. هیچ اعتبارسنجی روی این فیلد انجام نمی‌شود و در خطوط 127-180، این مسیر مستقیماً در `os.walk` و `open` استفاده می‌شود. این آسیب‌پذیری امکان Path Traversal را فراهم می‌کند: مهاجم می‌تواند با ارسال مسیرهایی مانند `../../etc/passwd` یا `/etc/` فایل‌های حساس سیستم را بخواند. همچنین در خط 137، فایل‌ها با `encoding='utf-8'` باز می‌شوند که در صورت خطا، خطا نادیده گرفته می‌شود (pass) و این می‌تواند منجر به نشت اطلاعات در لاگ‌ها شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند
- [ ] ارسال مسیر `/etc/` خطای 422 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `/
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی مسیر پروژه با استفاده از `os.path.abspath` و `os.path.commonpath` برای جلوگیری از Path Traversal. همچنین محدود کردن مسیر به یک دایرکتوری مجاز (مثلاً `/projects`).

## 💡 نمونه‌های قبل/بعد
**اضافه کردن validator به Pydantic مدل**

_قبل:_
```
project_path: str
```

_بعد:_
```
project_path: str = Field(..., description="مسیر پروژه")

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        abs_path = os.path.abspath(v)
        allowed_base = os.path.abspath(os.environ.get('PROJECTS_BASE_DIR', '/projects'))
        if not abs_path.startswith(allowed_base):
            raise ValueError(f'Path must be within {allowed_base}')
        if not os.path.isdir(abs_path):
            raise ValueError('Path must be an existing directory')
        return abs_path
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
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 8
  id: 51fab7d9-dba0-486e-8e29-77a459785fc3
  عنوان اصلی: نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند [verify_method=static] [verify_plan={"grep_patterns": ["SessionLocal\\(\\)"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - همه endpointها از Depends(get_db) یا async context manager استفاده کنند [verify_method=static] [verify_plan={"grep_patterns": ["Depends\\(get_db\\)", "async with.*get_db"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/model_profiles.py", "backend/app/api/routes/project_health]
  - تست نشت connection با 1000 درخواست هم‌زمان پاس شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_db_connection_leak.py::test_concurrent_requests_no_leak", "timeout_seconds": 120}]

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
نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:277-290` — `get_analysis_reports` — این تابع درست بسته می‌شود — الگو را به بقیه تعمیم بده
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
      return ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:293-306` — `get_analysis_report` — استثناء قبل از finally باعث نشت می‌شود — باید db را قبل از raise ببندیم یا از context manager استفاده کنیم
  ```python
  db = SessionLocal()
  try:
      report = db.query(...).first()
      if not report:
          raise HTTPException(...)  # ⚠️ اینجا db بسته نمی‌شود
      return ...
  finally:
      db.close()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + SQLite

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 277) — همه endpointهای analysis که SessionLocal مستقیم می‌سازند
- `backend/app/core/database.py` (سطر 1) — تعریف SessionLocal و get_db

## 🌐 نقشهٔ وابستگی‌ها
این باگ روی تمام endpointهایی که از SessionLocal مستقیم استفاده می‌کنند تأثیر دارد: analysis.py (5 endpoint), model_profiles.py (احتمالاً).

## 🔍 Context و وضعیت فعلی
در چندین endpoint (analysis.py, model_profiles.py, project_health.py) Session دیتابیس با `SessionLocal()` ساخته می‌شود اما در مسیرهای خطا (Exception) بسته نمی‌شود. این باعث نشت connection و در نهایت exhaustion pool دیتابیس می‌شود. نمونه: analysis.py خطوط 277-290 و 293-306 و 309-325 و 328-370 — همه از `SessionLocal()` استفاده می‌کنند و `db.close()` را در `finally` ندارند. در model_profiles.py خطوط 248-350 نیز `db` از `Depends(get_db)` می‌آید که احتمالاً مدیریت می‌شود ولی در analysis.py مستقیماً `SessionLocal()` ساخته می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند
- [ ] همه endpointها از Depends(get_db) یا async context manager استفاده کنند
- [ ] تست نشت connection با 1000 درخواست هم‌زمان پاس شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. تمام `SessionLocal()` ها را با context manager یا try/finally جایگزین کن تا در همه مسیرها (موفقیت و خطا) session بسته شود. یا از `Depends(get_db)` در همه endpointها استفاده کن.

## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
db = SessionLocal()
try:
    ...
    raise HTTPException(...)
finally:
    db.close()
```

_بعد:_
```
async with SessionLocal() as db:
    ...
    raise HTTPException(...)
# خودکار بسته می‌شود
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/api/routes/`
- `pytest backend/tests/ -k db_session`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در signature endpointها ممکن است frontend را بشکند اگر response type تغییر کند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 8
  id: 037dbd0d-9561-4c00-be73-7bc923e2565b
  عنوان اصلی: exception swallowed در run_analysis_stream بدون لاگ کافی
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run", "headers": null, "json_body": {"analysis_type": "deep", "target": "test"}, "expected_status": 200, "required_fields": [], "json_contains": null}]
  - اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت ارسال می [verify_method=static] [verify_plan={"grep_patterns": ["except Exception", "json.dumps", "fallback_error_message"], "files_hint": ["backend/app/api/routes/analysis.py"]}]

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
exception swallowed در run_analysis_stream بدون لاگ کافی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:251-253` — `generate_events` — اگر json.dumps روی str(e) خطا بدهد، این except هم بلعیده می‌شود
  ```python
  except Exception as e:
              logger.error(f"Error in SSE stream: {e}")
              yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
  ```
- `backend/app/api/routes/analysis.py:200-206` — `run_analysis_task` — اگر progress_queue.put خطا بدهد (صف بسته)، خطا بلعیده می‌شود
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                  await progress_queue.put({
                      "event": "error",
                      "message": str(e),
                      "error": True
                  })
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SSE streaming + asyncio.Queue

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/deep_analysis_service.py` (سطر 1) — run_full_analysis که از اینجا صدا زده می‌شود ممکن است خطاهای بیشتری تولید کند

## 🌐 نقشهٔ وابستگی‌ها
این endpoint توسط frontend در analysis/page.tsx (خط ۱۹۰) استفاده می‌شود. اگر خطا بلعیده شود، کاربر تا ۳۰ ثانیه heartbeat می‌بیند و بعد timeout می‌خورد.

## 🔍 Context و وضعیت فعلی
در `backend/app/api/routes/analysis.py` خط ۲۵۱-۲۵۳، یک `except Exception as e` عام وجود دارد که خطا را فقط با `logger.error` لاگ می‌کند و سپس یک رویداد `error` به SSE stream می‌فرستد. اما اگر خطا در حین ارسال رویداد `error` رخ دهد (مثلاً `json.dumps` روی یک شیء غیرقابل سریال‌سازی)، آن خطا هم بلعیده می‌شود و کاربر هیچ بازخوردی نمی‌بیند. همچنین در خط ۲۰۰-۲۰۶، خطاهای `run_full_analysis` در try/except داخلی گرفته می‌شوند و فقط یک رویداد `error` به صف اضافه می‌شود، اما اگر `progress_queue.put` خودش خطا بدهد (مثلاً صف بسته شده باشد)، آن خطا هم بلعیده می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند
- [ ] اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت ارسال می
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. در `except Exception as e` خط ۲۵۱، یک try/except تو در تو برای ارسال رویداد خطا اضافه کن. ۲. در خط ۲۰۰-۲۰۶، بعد از `progress_queue.put` یک `try/except` بگذار که اگر صف خطا داد، حداقل با `logger.critical` لاگ شود. ۳. یک `finally` در سطح `generate_events` اضافه کن که اگر خطای غیرمنتظره‌ای رخ داد، یک رویداد `fatal` با پیام ثابت به صف اضافه کند.

## 💡 نمونه‌های قبل/بعد
**ایمن‌سازی ارسال رویداد خطا**

_قبل:_
```
yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

_بعد:_
```
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
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
- نوع: bug
- اولویت: high
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
- در commit message: `merged-from: 1ffe1e50-b675-40a2-8840-0b82a7a59677, a555551a-e741-4642-9f7b-55122ab94221, 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd, 979942ad-03ba-4cd6-a5ba-dd563d8d5462, 49be9ac4-ed23-4874-975e-841175c6974b, 866ea2f9-0e88-4848-9c2a-d9b72c654747, 51fab7d9-dba0-486e-8e29-77a459785fc3, 037dbd0d-9561-4c00-be73-7bc923e2565b`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند
```

## 📋 چک‌لیست مراحل (39 مرحله)

این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**
وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.

- [ ] **مرحله 1: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد** — این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه فنی. محتوای آن دستورالعمل‌های متدولوژیک برای شروع کار است: بررسی وجود پیاده‌سازی قبلی، جستجوی فایل‌های مرتبط، و اجتناب از دوباره‌سازی. هیچ کد یا تغییری در این بخش درخواست نشده است. scope واقعی این بخش، فرآیند قبل از اجراست.
— [merged]
- [ ] **مرحله 2: اعتبارسنجی و sanitize مسیر پروژه در endpoint تحلیل استریم** — این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint POST /analysis/run-stream است. مسیر باید در برابر دایرکتوری مجاز (ALLOWED_PROJECTS_DIR) بررسی شود و از Path Traversal جلوگیری شود. همچنین باید بررسی شود که فایل‌های خوانده شده دارای پسوند مجاز (supported_extensions) باشند. این مر
- [ ] **مرحله 3: اعتبارسنجی امنیتی مسیر پروژه (Path Traversal Prevention)** — این مرحله شامل پیاده‌سازی مکانیزم اعتبارسنجی برای پارامتر `project_path` در endpoint مربوطه است. هدف اصلی جلوگیری از حملات path traversal با محدود کردن مسیرها به یک دایرکتوری مجاز (مانند `./projects`). این مرحله شامل افزودن محدودیت حجم فایل (1MB) و timeout برای عملیات خواندن فایل نیز می‌شود. خارج از
- [ ] **مرحله 4: اعتبارسنجی مسیر پروژه در تحلیل کد** — این مرحله شامل افزودن اعتبارسنجی امنیتی برای مسیر پروژه در endpoint تحلیل کد است. مسیر ورودی کاربر باید با BASE_DIR (که ./projects است) شروع شود تا از دسترسی به دایرکتوری‌های خارج از محدوده جلوگیری شود. فقط فایل backend/app/api/routes/analysis.py تحت تأثیر قرار می‌گیرد. تست‌های مرتبط در tests/test_a
- [ ] **مرحله 5: اجرای دستورات اعتبارسنجی امنیتی (Path Traversal)** — این بخش شامل دو دستور اعتبارسنجی است: (1) یک درخواست curl برای تست نفوذ path traversal با ارسال project_path='../../etc' به endpoint /analysis/run-stream، و (2) اجرای تست pytest مخصوص test_analysis.py با فیلتر path_traversal. این مرحله صرفاً اجرای دستورات تست است و شامل پیاده‌سازی کد یا تغییرات نمی‌
- [ ] **مرحله 6: پیاده‌سازی مدیریت خطا و لاگینگ در API Routes (analysis.py و chat.py)** — این مرحله شامل افزودن try-except به تمام route handlers در فایل‌های backend/app/api/routes/analysis.py و backend/app/api/routes/chat.py، لاگ کردن خطاهای 500 با timestamp, level, message, traceback، و برگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx) است. همچنین پیکربندی لاگر در backend/app/core/ باید بررسی ش
- [ ] **مرحله 7: یادداشت مهم برای مدل اجراکننده — بررسی مستقل پیش از تغییر** — این بخش یک یادداشت هشداردهنده است که به مدل اجراکننده یادآوری می‌کند پیش از هر تغییری، ساختار repo، فایل‌های ذکرشده و وابستگی‌های آن‌ها را مستقل بررسی کند. این بخش شامل دستورالعمل‌های رفتاری برای مدل است و هیچ وظیفهٔ اجرایی مشخصی ندارد. بنابراین، این بخش به‌عنوان یک مرحلهٔ اجرایی در نظر گرفته نمی‌شو
- [ ] **مرحله 8: افزودن middleware مدیریت خطا و لاگینگ سیستماتیک به API Routes** — این مرحله شامل پیاده‌سازی exception handler middleware در backend/app/core/، افزودن logging configuration با structlog/loguru، و بهبود مدیریت خطا در routes analysis.py و chat.py است. خارج از scope: تغییر در سایر routes (مانند github_import.py, model_profiles.py)، تغییر در frontend، یا تغییر در سرویس
- [ ] **مرحله 9: پیاده‌سازی مدیریت خطا و لاگینگ ساختاریافته در route handlers** — این مرحله شامل افزودن middleware سراسری برای مدیریت خطاها (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru است. همچنین باید تمام route handlers موجود (analysis, chat, github_import, model_profiles) به try-except مجهز شوند و پاسخ‌های HTTP مناسب (4xx,
- [ ] **مرحله 10: افزودن مدیریت خطا به endpointهای API** — این بخش شامل افزودن try/except و logging به endpointهای موجود در فایل‌های routes است. فقط endpointهای مشخص‌شده در مثال (مانند get_projects) هدف هستند، نه کل پروژه. نکته حیاتی: باید از logger و HTTPException مطابق مثال استفاده شود و خطاها به صورت 500 برگردانده شوند.
- [ ] **مرحله 11: پیاده‌سازی Rate Limiting و Input Validation برای API Endpoints** — این مرحله شامل پیاده‌سازی Rate Limiting برای تمام AI endpoints (chat و analysis) با بازگشت پاسخ 429 در صورت تجاوز از محدودیت، و همچنین پیاده‌سازی Input Validation با Pydantic برای تمام endpoints است. محدودیت‌ها باید از طریق متغیرهای محیطی قابل تنظیم باشند. فایل‌های اصلی backend/app/api/routes/analys
- [ ] **مرحله 12: افزودن Rate Limiting و Input Validation به API Endpoints** — این مرحله شامل افزودن middleware rate limiting با استفاده از slowapi به برنامه FastAPI، اعمال rate limiting به endpoints حساس (chat و analysis)، و اطمینان از وجود validation مناسب Pydantic برای ورودی‌های این endpoints است. خارج از scope این مرحله: پیاده‌سازی rate limiting برای سایر endpoints، تست‌ها
- [ ] **مرحله 13: افزودن rate limiting به endpoint چت** — این بخش شامل افزودن محدودیت نرخ (rate limiting) به endpoint POST /chat است. کد نمونه نشان‌دهنده استفاده از دکوراتور `@limiter.limit('10/minute')` است. خارج از scope: پیاده‌سازی خود limiter، تغییرات در config، یا تست‌های مرتبط. نکته حیاتی: فایل هدف backend/app/api/routes/chat.py است و باید از همان sy
- [ ] **مرحله 14: اجرای دستورات اعتبارسنجی curl برای endpoint /api/chat** — این بخش شامل اجرای دو دستور curl برای اعتبارسنجی endpoint /api/chat است. دستور اول یک درخواست POST ساده با body خالی است. دستور دوم ۲۰ درخواست همزمان POST با body خالی را اجرا می‌کند. این بخش صرفاً بر اجرای این دستورات و مشاهده خروجی آنها تمرکز دارد و شامل پیاده‌سازی یا تغییر کد نمی‌شود.
- [ ] **مرحله 15: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا** — این تسک مربوط به رفع نشت connection در تابع `run_analysis_stream` در فایل `backend/app/api/routes/analysis.py` است. هدف اصلی اطمینان از بسته شدن session دیتابیس در بلاک `finally` است تا در صورت بروز خطا، connection به دیتابیس بازگردانده شود. همچنین باید تست استرس با ۱۰۰ درخواست هم‌زمان برای اطمینان 
- [ ] **مرحله 16: بررسی اولیه و پیش‌نیازهای اجرای درخواست (یادداشت مهم برای مدل اجراکننده)** — این بخش یک یادداشت هشداردهنده و راهنمای کلی برای مدل اجراکننده است، نه یک درخواست اجرایی مشخص. شامل دستورالعمل‌هایی برای بررسی وجود پیاده‌سازی قبلی، مسئولیت‌پذیری در قبال تشخیص‌های خودکار، و نحوه برخورد با کارهای طولانی است. این بخش خودش یک مرحله اجرایی نیست، بلکه یک prelude برای تمام مراحل بعدی است
- [ ] **مرحله 17: رفع نشت Session در run_analysis_task با افزودن finally block برای بستن Session** — این بخش فقط به رفع باگ نشت Session در تابع run_analysis_task در فایل backend/app/api/routes/analysis.py می‌پردازد. شامل افزودن try/finally برای بستن analysis_db در مسیر خطا و موفقیت است. سایر توابع موجود در analysis.py که از الگوی صحیح استفاده می‌کنند (get_analysis_reports, get_analysis_report, dele
- [ ] **مرحله 18: بستن session در finally تابع run_analysis_stream** — این مرحله فقط به بستن session در بلوک finally تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py می‌پردازد. شامل بررسی ownership session بین تابع و DeepAnalysisService است. خارج از scope: سایر بخش‌های کد، تست‌ها، linter، type-check و تست استرس (این موارد در AC ذکر شده‌اند اما بخشی ا
- [ ] **مرحله 19: رفع نشت session در analysis_db با استفاده از try/finally** — این بخش شامل اصلاح الگوی استفاده از SessionLocal در فایل‌های backend برای اطمینان از بسته شدن session پس از استفاده است. نمونه ارائه‌شده نشان‌دهنده تغییر از حالت بدون finally به حالت try/finally می‌باشد. خارج از scope: تغییرات در frontend، تست‌ها، یا فایل‌های config.
- [ ] **مرحله 20: اضافه کردن finally block برای مدیریت ریسک در endpoint /api/analysis/run-stream** — این بخش صرفاً به اضافه کردن یک finally block در endpoint /api/analysis/run-stream (فایل backend/app/api/routes/analysis.py) محدود می‌شود. هدف آن اطمینان از پاک‌سازی منابع (مانند بستن فایل‌ها یا اتصالات) حتی در صورت بروز خطا است. هیچ تغییر دیگری در منطق اعتبارسنجی ورودی یا مسیردهی انجام نمی‌شود. این 
- [ ] **مرحله 21: بررسی اولیه و مستندسازی وضعیت موجود repo قبل از هرگونه تغییر** — این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن الزام مدل به بررسی مستقل repo، شناسایی پیاده‌سازی‌های قبلی، و جلوگیری از بازسازی موارد موجود است. این بخش به‌تنهایی یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک برای کل فرآیند است. اگر تمام درخواس
- [ ] **مرحله 22: اعتبارسنجی مسیر پروژه در endpoint run_analysis_stream** — این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint run_analysis_stream است. مسیر باید از نظر وجود دایرکتوری، عدم وجود path traversal (مانند '..' یا '/') و محدود بودن به دایرکتوری‌های مجاز پروژه بررسی شود. همچنین باید از خواندن README از مسیرهای غیرمجاز جلوگیری کند. این مرحله شامل
- [ ] **مرحله 23: افزودن اعتبارسنجی مسیر برای جلوگیری از Path Traversal در project_path** — این بخش شامل پیاده‌سازی اعتبارسنجی مسیر در endpoint مربوط به project_path است. باید از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز (/app/projects) است استفاده شود. همچنین باید validation با Pydantic برای enforce کردن الگوی مسیر امن اضافه شود. تست واحد جد
- [ ] **مرحله 24: اضافه کردن اعتبارسنجی مسیر پروژه در endpoint تحلیل** — این مرحله شامل افزودن validation برای پارامتر project_path در endpoint مربوط به تحلیل پروژه است. مسیر باید به یک دایرکتوری مجاز (ALLOWED_BASE) محدود شود تا از دسترسی به فایل‌های خارج از محدوده جلوگیری شود. تغییرات فقط در فایل backend/app/api/routes/analysis.py اعمال می‌شود. تست‌های امنیتی مرتبط در b
- [ ] **مرحله 25: اجرای دستورات اعتبارسنجی امنیتی برای مسیرهای فایل** — این بخش شامل دو دستور اعتبارسنجی است: (1) یک درخواست curl برای تست endpoint تحلیل با مسیر فایل مخرب (path traversal) و (2) اجرای تست pytest مخصوص آسیب‌پذیری path traversal. هدف این مرحله تأیید امنیت endpoint در برابر حملات path traversal است. این بخش صرفاً دستورات تست را مشخص می‌کند و شامل پیاده‌ساز
- [ ] **مرحله 26: اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)** — این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint /analysis/run است. فقط validation سمت سرور (backend) در فایل backend/app/api/routes/analysis.py انجام می‌شود. منطق business (تحلیل پروژه) تغییر نمی‌کند. مسیرهای معتبر باید همچنان کار کنند و مسیرهای نامعتبر (مانند path traversal ی
- [ ] **مرحله 27: اعتبارسنجی ورودی project_path در endpoint تحلیل پروژه** — این مرحله شامل افزودن validator به فیلد project_path در مدل Pydantic AnalysisRequest است تا از حملات Path Traversal جلوگیری شود. همچنین شامل اصلاح نحوه استفاده از project_path در تابع run_analysis_task برای امنیت بیشتر می‌شود. خارج از scope: تغییرات در frontend، middleware، یا سایر endpointها.
- [ ] **مرحله 28: اعتبارسنجی مسیر پروژه برای جلوگیری از Path Traversal** — این بخش شامل پیاده‌سازی اعتبارسنجی مسیرهای فایل در endpoint مربوط به تحلیل پروژه است. مسیرهای معتبر باید داخل دایرکتوری مجاز `/projects` باشند و مسیرهای حاوی `..` یا مسیرهای مطلق غیرمجاز (مانند `/etc/`) رد شوند. خروجی این مرحله فقط شامل منطق اعتبارسنجی است و شامل پیاده‌سازی endpoint یا تست‌ها نمی‌شو
- [ ] **مرحله 29: اضافه کردن validator به Pydantic مدل برای اعتبارسنجی مسیر پروژه** — این بخش شامل افزودن یک validator به فیلد project_path در یک Pydantic مدل است. validator باید مسیر را به absolute تبدیل کند، بررسی کند که درون دایرکتوری مجاز (PROJECTS_BASE_DIR) قرار دارد و یک دایرکتوری موجود است. فایل دقیق مدل مشخص نشده، اما با توجه به مسیرهای موجود، احتمالاً در backend/app/models/a
- [ ] **مرحله 30: رفع نقص مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا** — این مرحله شامل اصلاح تمام endpointهای موجود در فایل‌های backend/app/api/routes/analysis.py، backend/app/api/routes/model_profiles.py و backend/app/api/routes/project_health است تا به جای استفاده مستقیم از SessionLocal()، از Depends(get_db) یا async context manager استفاده کنند. همچنین شامل اجرای تست
- [ ] **مرحله 31: بررسی اولیه و اعتبارسنجی خودکار پیش از اجرا** — این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. محتوای آن صرفاً یک راهنمای رفتاری برای مدل است که باید پیش از هر اقدامی، ساختار repo را مستقل بررسی کند، از بازسازی موارد موجود خودداری کند، و در صورت نیاز به چند کامیت، ترتیب منطقی را رعایت کند. هیچ فا
- [ ] **مرحله 32: رفع نشت Session دیتابیس در endpointهای analysis.py با استفاده از context manager یا finally block** — این مرحله فقط به رفع نشت Session در فایل backend/app/api/routes/analysis.py می‌پردازد. تمام endpointهایی که مستقیماً SessionLocal() می‌سازند و db.close() را در finally ندارند، باید اصلاح شوند. فایل‌های model_profiles.py و project_health.py در این مرحله گنجانده نشده‌اند. راهکار پیشنهادی: استفاده از c
- [ ] **مرحله 33: جایگزینی SessionLocal مستقیم با context manager یا Depends(get_db) در تمام endpointها** — این بخش شامل جایگزینی تمام استفاده‌های مستقیم از SessionLocal() در endpointها با context manager (try/finally یا async context manager) یا Depends(get_db) است. هدف اطمینان از بسته شدن session در همه مسیرها (موفقیت و خطا) و جلوگیری از نشت connection است. خارج از scope: تغییر منطق business، اضافه کردن
- [ ] **مرحله 34: رفع نشت session با استفاده از context manager** — این بخش شامل تغییر الگوی مدیریت session در کد backend از try/finally به async with context manager است. فقط فایل‌هایی که از SessionLocal استفاده می‌کنند تحت تأثیر قرار می‌گیرند. تغییرات باید در routes و service‌های مرتبط اعمال شود. تست‌ها نیز باید به‌روزرسانی شوند.
- [ ] **مرحله 35: رفع exception swallowed در run_analysis_stream با لاگ کافی و ارسال خطا به کاربر** — این مرحله شامل پیاده‌سازی مدیریت خطا در تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py است. باید اطمینان حاصل شود که اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار دریافت کند. همچنین اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت
- [ ] **مرحله 36: رفع بلعیده شدن استثناها در run_analysis_stream با لاگ‌گیری و مدیریت خطای جامع‌تر** — این مرحله شامل اصلاح دو بخش از فایل backend/app/api/routes/analysis.py است: (1) خطوط 251-253 در تابع generate_events که در آن خطای json.dumps درون except بلعیده می‌شود، و (2) خطوط 200-206 در تابع run_analysis_task که در آن خطای progress_queue.put بلعیده می‌شود. هدف این است که اطمینان حاصل شود هیچ اس
- [ ] **مرحله 37: پیاده‌سازی مدیریت خطاهای مقاوم در deep_analysis_service و generate_events** — این مرحله شامل سه تغییر مجزا در مدیریت خطا است: (1) افزودن try/except تو در تو در خط 251 برای ارسال رویداد خطا در صورت شکست json.dumps، (2) افزودن try/except در خطوط 200-206 برای مدیریت خطای صف progress_queue، (3) افزودن finally در سطح تابع generate_events برای ارسال رویداد fatal در صورت خطای غیرمنت
- [ ] **مرحله 38: ایمن‌سازی ارسال رویداد خطا در استریم رویداد** — این مرحله شامل تغییر کد در فایل‌های مرتبط با استریم رویداد خطا (احتمالاً در backend/app/api/routes/chat.py یا backend/app/services/deep_analysis_service.py) است. تغییرات شامل محدود کردن طول پیام خطا به 500 کاراکتر و افزودن try/except برای جلوگیری از شکست استریم است. خارج از scope: تغییرات در سایر بخ
- [ ] **مرحله 39: اجرای تست‌های موجود پیش از merge برای جلوگیری از رگرشن** — این بخش شامل اجرای تمام تست‌های موجود در پروژه (unit, integration, e2e) پیش از انجام merge است. هدف اطمینان از عدم ایجاد رگرشن (regression) در کد موجود است. هیچ تغییری در کد یا تست‌ها در این مرحله انجام نمی‌شود. این یک مرحله QA/اعتبارسنجی است و نه توسعه.

---

# 🔹 مرحله 1: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد

**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه فنی. محتوای آن دستورالعمل‌های متدولوژیک برای شروع کار است: بررسی وجود پیاده‌سازی قبلی، جستجوی فایل‌های مرتبط، و اجتناب از دوباره‌سازی. هیچ کد یا تغییری در این بخش درخواست نشده است. scope واقعی این بخش، فرآیند قبل از اجراست.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک درخواست پیاده‌سازی. هدف آن اطمینان از این است که قبل از هر تغییری، ساختار repo، فایل‌های موجود و وابستگی‌ها بررسی شوند تا از پیاده‌سازی مجدد قابلیت‌های موجود جلوگیری شود. این بخش شامل دستورالعمل‌هایی برای جستجو، خواندن فایل‌های مرتبط، و تصمیم‌گیری بر اساس یافته‌ها است. هیچ کد یا تغییری در این بخش درخواست نشده است.

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
مستندسازی پروتکل بررسی اولیه repo قبل از هر تغییر

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `docs/ARCHITECTURE.md` — `N/A` — این فایل در ساختار پروژه موجود است و محل مناسب برای اضافه کردن بخش 'Execution Protocol' یا لینک به فایل پروتکل جدید است. deep-read نشده — مجری باید محتوا را تأیید کند.
- `docs/README.md` — `N/A` — فایل README اصلی مستندات — باید به پروتکل جدید اشاره کند. deep-read نشده — مجری باید محتوا را تأیید کند.
- `docs/AUDIT_REPORT.md` — `N/A` — فایل audit موجود در پروژه — می‌تواند الگوی ساختاری برای فایل پروتکل جدید باشد. deep-read نشده — مجری باید محتوا را تأیید کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js (TypeScript). پروژه دارای ۲۴۷ فایل با ساختار پیچیده است. مستندات موجود در پوشهٔ `docs/` شامل ARCHITECTURE.md، AUDIT_REPORT.md، PHASE_5_META_VALIDATION.md، README.md، ROADMAP.md، SYSTEM_REPORT_2026-02-08.md است. فایل جدید `docs/EXECUTION_PROTOCOL.md` باید با همین ساختار Markdown هماهنگ باشد.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `docs/ROADMAP.md` (سطر 1) — پروتکل اجرا باید با roadmap هماهنگ باشد — مدل اجراکننده باید roadmap را قبل از هر تغییر بررسی کند
- `docs/PHASE_5_META_VALIDATION.md` (سطر 1) — این فایل احتمالاً شامل validation protocol های قبلی است که پروتکل جدید باید با آن‌ها سازگار باشد
- `backend/app/main.py` (سطر 1) — entry point اصلی backend — هر تغییر در repo باید با بررسی این فایل شروع شود چون router های اصلی اینجا register می‌شوند
- `backend/app/core/database.py` (سطر 1) — hub اصلی با 16 importer — پروتکل باید تأکید کند که تغییر این فایل بدون بررسی همهٔ 16 importer ممنوع است
- `docs/SYSTEM_REPORT_2026-02-08.md` (سطر 1) — گزارش سیستم موجود — baseline وضعیت فعلی repo که مدل اجراکننده باید قبل از تغییر با آن آشنا شود

## 🌐 نقشهٔ وابستگی‌ها
این تسک هیچ dependency کدی ندارد و صرفاً مستنداتی است. با این حال، پروتکلی که مستند می‌شود مستقیماً بر نحوهٔ تعامل با hub های اصلی پروژه تأثیر می‌گذارد: `backend/app/core/database.py` (16 importer از جمله analysis.py، github_import.py، model_profiles.py، models.py، oversight.py)، `backend/app/services/ai_manager.py` (15 importer از جمله analysis.py، models.py، orchestrator.py، oversight.py، project_health.py)، و `backend/app/models/project.py` (10 importer از جمله github_import.py، models.py، oversight.py، project_health.py، project_journal.py). پروتکل باید به‌صراحت بگوید که تغییر هر یک از این hub ها نیازمند بررسی همهٔ importer های آن است.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت متدولوژیک رسمی برای مدل اجراکننده (Cursor/Copilot/ChatGPT) است که باید به‌عنوان پروتکل اجباری قبل از هر تغییر در این repo رعایت شود. محتوای درخواست کاربر به‌صراحت بیان می‌کند: «این پرامپت بر اساس یک بررسی اولیهٔ خودکار از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.»

پروتکل الزامی شامل سه محور اصلی است:

**محور ۱ — بررسی پیاده‌سازی قبلی (♻️):**
پیش از هر تغییر، با grep/search و خواندن فایل‌های مرتبط بررسی شود که چه چیزی از قبل وجود دارد. اگر قابلیت/فایل/تابع از قبل موجود است، دوباره ساخته نشود — فقط موارد ناقص یا اشتباه اصلاح/تکمیل شوند. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

**محور ۲ — مسئولیت مستقل مدل اجراکننده (🔍):**
پیش از هر تغییر، مدل اجراکننده باید خودش ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کند. اگر تشخیص داد موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودش عمل کند — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد. اگر معیارهای پذیرش مبهم/ناقص بودند، بهترین تفسیر انتخاب شود و در commit message توضیح داده شود.

**محور ۳ — مدیریت کارهای طولانی (📦):**
خلاصه‌سازی ممنوع است. همه چیز به‌طور کامل انجام شود. اگر یک کامیت گنجایش ندارد، در چندین کامیت متوالی انجام شود — ولی هیچ بخشی skip نشود. ترتیب کامیت‌ها منطقی نگه داشته شود (foundation → core → integration → tests). در آخر یک checklist از همهٔ کامیت‌ها در PR description نوشته شود.

این پروتکل به‌ویژه در این repo با ۲۴۷ فایل و ساختار پیچیده (FastAPI backend + Next.js frontend) اهمیت دارد، چون فایل‌های hub مانند `backend/app/core/database.py` (16 importer)، `backend/app/services/ai_manager.py` (15 importer)، و `backend/app/models/project.py` (10 importer) وجود دارند که تغییر هر یک اثر cascade دارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل `docs/EXECUTION_PROTOCOL.md` در repo وجود داشته باشد و شامل سه بخش اصلی: بررسی پیاده‌سازی قبلی، مسئولیت مستقل مدل، و مدیریت کارهای طولانی باشد
- [ ] فایل پروتکل باید شامل قالب کامیت no-op با مثال واقعی باشد
- [ ] فایل پروتکل باید به hub های اصلی پروژه (database.py با 16 importer، ai_manager.py با 15 importer) اشاره کند
- [ ] فایل `docs/ARCHITECTURE.md` یا `docs/README.md` باید لینک یا اشاره‌ای به EXECUTION_PROTOCOL.md داشته باشد
- [ ] هیچ فایل کد (py، ts، tsx) تغییر نکرده باشد — این تسک کاملاً مستنداتی است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. از آنجا که این درخواست «هیچ کد یا تغییری» نمی‌خواهد و صرفاً یک پروتکل متدولوژیک است، اقدام پیشنهادی به شرح زیر است:

1. **ایجاد فایل مستندات پروتکل** در `docs/EXECUTION_PROTOCOL.md` — این فایل پروتکل بررسی اولیه را به‌صورت رسمی مستند می‌کند تا همهٔ مدل‌های اجراکننده آینده از آن آگاه باشند.

2. **محتوای فایل** باید شامل باشد:
   - چک‌لیست grep/search قبل از هر تغییر
   - دستورالعمل تشخیص پیاده‌سازی موجود
   - قالب کامیت no-op برای موارد «همه چیز از قبل موجود است»
   - ترتیب منطقی کامیت‌ها (foundation → core → integration → tests)
   - قالب PR description با checklist

3. **به‌روزرسانی `docs/README.md`** (اگر موجود باشد) با اشاره به این پروتکل.

4. **هیچ تغییری در کد backend یا frontend** انجام نشود — این تسک کاملاً مستنداتی است.

5. **کامیت نهایی** باید پیام واضحی داشته باشد: `docs: add execution protocol for pre-change repo inspection`

## 💡 نمونه‌های قبل/بعد
**قالب کامیت no-op وقتی قابلیت از قبل موجود است**

_قبل:_
```
// مدل اجراکننده بدون بررسی، کد جدید می‌نویسد و duplicate ایجاد می‌کند
```

_بعد:_
```
// کامیت no-op:
// docs(no-op): verify pre-existing implementation of [feature]
//
// بررسی انجام شد. این قابلیت از قبل در فایل‌های زیر پیاده‌سازی شده:
// - backend/app/services/foo.py (lines 45-89)
// - backend/app/api/routes/bar.py (lines 120-145)
// هیچ تغییری لازم نیست.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `test -f docs/EXECUTION_PROTOCOL.md && echo 'OK: protocol file exists' || echo 'FAIL: missing'`
- `grep -l 'EXECUTION_PROTOCOL' docs/ARCHITECTURE.md docs/README.md 2>/dev/null || echo 'WARN: no reference found'`
- `grep -c 'no-op' docs/EXECUTION_PROTOCOL.md || echo 'FAIL: no-op template missing'`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این تسک غیرفنی است: اگر پروتکل مستند شده خیلی کلی یا مبهم باشد، مدل‌های اجراکننده آینده آن را نادیده می‌گیرند. ریسک دوم: تداخل با `docs/PHASE_5_META_VALIDATION.md` که احتمالاً پروتکل‌های مشابهی دارد — مجری باید قبل از نوشتن، این فایل را بخواند تا duplicate نشود. ریسک سوم: اگر `docs/ARCHITECTURE.md` ساختار خاصی دارد، اضافه کردن لینک به پروتکل جدید باید با آن ساختار هماهنگ باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 2: اعتبارسنجی و sanitize مسیر پروژه در endpoint تحلیل استریم

**Scope:** این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint POST /analysis/run-stream است. مسیر باید در برابر دایرکتوری مجاز (ALLOWED_PROJECTS_DIR) بررسی شود و از Path Traversal جلوگیری شود. همچنین باید بررسی شود که فایل‌های خوانده شده دارای پسوند مجاز (supported_extensions) باشند. این مرحله شامل تغییر در فایل backend/app/api/routes/analysis.py و احتمالاً backend/app/core/config.py است. تست‌های مربوطه در tests/test_analysis.py یا backend/tests/test_security.py اضافه می‌شوند.
**Key terms:** backend/app/api/routes/analysis.py, run_analysis_stream, project_path, os.walk, open, supported_extensions, ALLOWED_PROJECTS_DIR, backend/app/core/config.py, tests/test_analysis.py, backend/tests/test_security.py

**بخش مربوط از متن کاربر:**
```
در endpoint `POST /analysis/run-stream` (فایل `backend/app/api/routes/analysis.py`، خطوط 83-268)، پارامتر `project_path` مستقیماً از درخواست کاربر دریافت شده و بدون هیچ sanitization در `os.walk` و `open` استفاده می‌شود. مهاجم می‌تواند با ارسال مسیرهایی مثل `../../etc` یا `/proc/1/environ` به فایل‌های حساس سیستم دسترسی پیدا کند. همچنین `supported_extensions` فقط پسوند فایل را چک می‌کند و محتوای واقعی فایل را بررسی نمی‌کند. این آسیب‌پذیری Path Traversal کلاسیک است.
```

## 🎯 هدف (خلاصه ساختاریافته)
اعتبارسنجی و sanitize پارامتر project_path در endpoint تحلیل استریم

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:83-130` — `run_analysis_stream` — نقطه اصلی آسیب‌پذیری: `project_path = request.project_path` در خط ۱۲۷ بدون هیچ validation مستقیماً از request گرفته می‌شود و سپس در os.walk و open استفاده می‌شود
  ```python
  @router.post("/run-stream")
  async def run_analysis_stream(request: AnalysisRequest):
      import os
      from ...services.ai_manager import get_ai_manager
      from ...services.deep_analysis_service import DeepAnalysisService
  
      # صف برای ارسال رویدادها
      progress_queue: asyncio.Queue = asyncio.Queue()
  
      async def progress_callback(progress_data: dict):
          """callback برای دریافت رویدادهای پیشرفت"""
          await progress_queue.put(progress_data)
  
      async def generate_events():
          """ژنراتور رویدادهای SSE"""
          final_result = None
  
          async def run_analysis_task():
              nonlocal final_result
              try:
                  # دریافت AI Manager
                  ai_manager = get_ai_manager()
  
                  # 🔴 ایجاد db session برای استفاده از پرامپت‌های دیتابیس
                  from ...core.database import SessionLocal
                  analysis_db = SessionLocal()
  
                  # ساخت DeepAnalysisService با progress callback و db_session
                  deep_analyzer = DeepAnalysisService(
                      ai_manager=ai_manager,
                      progress_callback=progress_callback,
                      db_session=analysis_db
                  )
  
                  # جمع‌آوری فایل‌های پروژه
                  project_path = request.project_path
  ```
- `backend/app/api/routes/analysis.py:153-180` — `run_analysis_task` — حلقه os.walk روی project_path بدون resolved path اجرا می‌شود. full_path نیز بدون بررسی canonical path در open استفاده می‌شود. symlink escape از اینجا ممکن است
  ```python
  supported_extensions = {
                      '.py', '.js', '.ts', '.tsx', '.jsx', '.java',
                      '.go', '.rs', '.cpp', '.c', '.h', '.hpp',
                      '.rb', '.php', '.swift', '.kt', '.scala',
                      '.vue', '.svelte', '.html', '.css', '.scss'
                  }
  
                  for root, dirs, filenames in os.walk(project_path):
                      # فیلتر دایرکتوری‌های غیرضروری
                      dirs[:] = [d for d in dirs if d not in {
                          'node_modules', '.git', '__pycache__', 'venv',
                          '.venv', 'env', 'dist', 'build', '.next'
                      }]
  
                      for filename in filenames:
                          ext = os.path.splitext(filename)[1].lower()
                          if ext in supported_extensions:
                              full_path = os.path.join(root, filename)
                              rel_path = os.path.relpath(full_path, project_path)
                              try:
                                  with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                      content = f.read()
                                  files.append({
                                      "path": rel_path,
                                      "content": content
                                  })
                              except:
                                  pass
  ```
- `backend/app/core/config.py` — `Settings` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. باید متغیر ALLOWED_PROJECTS_DIR به Settings class اضافه شود تا از environment variable خوانده شود

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js 14. کتابخانه‌های مرتبط: `os.path` (stdlib Python) برای path manipulation، `pathlib.Path` برای مقایسه امن‌تر مسیرها، `pydantic>=2.5.0` برای validation در AnalysisRequest model، `python-dotenv>=1.0.0` برای خواندن ALLOWED_PROJECTS_DIR از environment. در frontend: `fetch` API با SSE stream reading. روش توصیه‌شده: استفاده از `pathlib.Path.resolve()` و `Path.is_relative_to()` (Python 3.9+) به جای string comparison برای جلوگیری از edge case های path traversal.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 46) — فایل اصلی تغییر — تابع run_analysis (خطوط ۴۶-۸۰) نیز همان AnalysisRequest را می‌پذیرد و project_path را به analyzer.analyze_project پاس می‌دهد؛ باید همان validation آنجا هم اعمال شود
- `backend/app/services/content_sanitizer.py` (سطر 1) — سرویس موجود برای sanitize محتوا — باید بررسی شود آیا می‌توان path validation را اینجا centralize کرد یا باید utility جداگانه ساخت
- `backend/app/api/routes/security_analysis.py` (سطر 61) — این route نیز project files را می‌خواند (خطوط ۶۱-۷۷) و از ProjectFile model استفاده می‌کند؛ pattern validation باید consistent باشد
- `frontend/src/app/analysis/page.tsx` (سطر 190) — در خط ۱۹۰-۱۹۸، frontend مستقیماً project_path را از input کاربر به endpoint /api/analysis/run-stream ارسال می‌کند؛ باید error handling برای 400 response اضافه شود
- `backend/app/core/database.py` (سطر 1) — 15 فایل این را import می‌کنند؛ اگر config.py تغییر کند و ALLOWED_PROJECTS_DIR از آن خوانده شود، باید مطمئن شد که initialization order مشکلی ایجاد نمی‌کند

## 🌐 نقشهٔ وابستگی‌ها
تابع `run_analysis_stream` در `backend/app/api/routes/analysis.py` (خطوط ۸۳-۲۶۸) مستقیماً توسط frontend در `frontend/src/app/analysis/page.tsx` (خط ۱۹۰) از طریق fetch به `/api/analysis/run-stream` فراخوانی می‌شود. تابع `run_analysis` (خطوط ۴۶-۸۰) در همان فایل نیز همان `AnalysisRequest` model را می‌پذیرد و باید validation یکسانی داشته باشد. `backend/app/core/config.py` باید متغیر `ALLOWED_PROJECTS_DIR` را expose کند تا در route استفاده شود. `backend/app/services/content_sanitizer.py` سرویس موجود sanitize است که می‌تواند برای centralize کردن path validation استفاده شود. `backend/app/services/deep_analysis_service.py` نیز `project_path` را از طریق `run_full_analysis` دریافت می‌کند (خط ۱۹۱) و باید بررسی شود آیا آنجا هم path validation لازم است.

## 🔍 Context و وضعیت فعلی
در endpoint `POST /analysis/run-stream` (فایل `backend/app/api/routes/analysis.py`، خطوط ۸۳-۲۶۸)، پارامتر `project_path` مستقیماً از درخواست کاربر دریافت شده و بدون هیچ sanitization در `os.walk` (خط ۱۶۰) و `open` (خط ۱۷۳) استفاده می‌شود. مهاجم می‌تواند با ارسال مسیرهایی مثل `../../etc` یا `/proc/1/environ` به فایل‌های حساس سیستم دسترسی پیدا کند. همچنین `supported_extensions` (خطوط ۱۵۳-۱۵۸) فقط پسوند فایل را چک می‌کند و محتوای واقعی فایل را بررسی نمی‌کند — این آسیب‌پذیری Path Traversal کلاسیک است.

این مرحله شامل افزودن اعتبارسنجی برای پارامتر `project_path` در endpoint `POST /analysis/run-stream` است. مسیر باید در برابر دایرکتوری مجاز (`ALLOWED_PROJECTS_DIR`) بررسی شود و از Path Traversal جلوگیری شود. همچنین باید بررسی شود که فایل‌های خوانده شده دارای پسوند مجاز (`supported_extensions`) باشند.

تغییرات اصلی در فایل `backend/app/api/routes/analysis.py` و احتمالاً `backend/app/core/config.py` انجام می‌شود. تست‌های مربوطه در `tests/test_analysis.py` یا `backend/tests/test_security.py` اضافه می‌شوند.

کلیدواژه‌های فنی: `run_analysis_stream`، `project_path`، `os.walk`، `open`، `supported_extensions`، `ALLOWED_PROJECTS_DIR`، `backend/app/api/routes/analysis.py`، `backend/app/core/config.py`، `tests/test_analysis.py`، `backend/tests/test_security.py`.

شواهد در کد: در خط ۱۲۷ فایل `analysis.py`، مقدار `project_path = request.project_path` بدون هیچ validation مستقیماً به `os.walk(project_path)` در خط ۱۶۰ پاس داده می‌شود. در خط ۱۷۳، `open(full_path, 'r', ...)` نیز بدون بررسی canonical path اجرا می‌شود. هیچ‌گونه `os.path.realpath` یا `os.path.abspath` برای مقایسه با base directory وجود ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path برابر با `../../etc/passwd` به endpoint POST /api/analysis/run-stream باید HTTP 400 یا 422 برگرداند و هیچ فایلی خوانده نشود
- [ ] ارسال project_path برابر با `/proc/1/environ` به endpoint POST /api/analysis/run-stream باید HTTP 400 برگرداند
- [ ] تابع validate_project_path باید در فایل analysis.py یا یک utility module وجود داشته باشد و از pathlib.Path.resolve() و relative_to() استفاده کند
- [ ] متغیر ALLOWED_PROJECTS_DIR باید در backend/app/core/config.py یا از os.environ خوانده شود
- [ ] تست‌های path traversal در backend/tests/test_security.py باید pass شوند — شامل تست ../../etc، /proc/1/environ، و symlink escape
- [ ] یک project_path معتبر زیرمجموعه ALLOWED_PROJECTS_DIR باید بدون خطا پردازش شود و stream را شروع کند
- [ ] در حلقه os.walk، هر full_path باید با os.path.realpath بررسی شود که هنوز زیرمجموعه project_path است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. **افزودن متغیر `ALLOWED_PROJECTS_DIR` به `backend/app/core/config.py`**: یک متغیر محیطی جدید با مقدار پیش‌فرض `/projects` یا مسیر مشخص تعریف کن که تمام project_path ها باید زیرمجموعه آن باشند.

۲. **ایجاد تابع `validate_project_path(path: str) -> Path` در `backend/app/api/routes/analysis.py` یا یک utility module**: این تابع باید:
   - `os.path.realpath` را روی path اعمال کند تا symlink ها resolve شوند
   - بررسی کند که resolved path با `ALLOWED_PROJECTS_DIR` شروع می‌شود (`resolved.startswith(allowed_base)`)
   - در صورت خروج از محدوده، `HTTPException(status_code=400, detail='مسیر غیرمجاز')` raise کند
   - بررسی کند که مسیر واقعاً وجود دارد (`os.path.isdir`)

۳. **اعمال validation در تابع `run_analysis_stream` (خطوط ۸۳-۲۶۸ فایل `analysis.py`)**:
   - قبل از خط ۱۲۷ (`project_path = request.project_path`)، تابع validate را صدا بزن
   - مقدار `project_path` را با نتیجه resolved path جایگزین کن

۴. **اعمال validation در تابع `run_analysis` (خطوط ۴۶-۸۰ فایل `analysis.py`)**:
   - همان validation را برای endpoint غیر-streaming نیز اعمال کن تا consistency حفظ شود

۵. **بررسی double-check در حلقه `os.walk` (خط ۱۶۰-۱۸۰)**:
   - برای هر `full_path` که در حلقه ساخته می‌شود، `os.path.realpath(full_path)` را بررسی کن که هنوز زیرمجموعه `project_path` است (جلوگیری از symlink escape)
   - `supported_extensions` را به عنوان whitelist نگه دار و هیچ extension دیگری را نپذیر

۶. **نوشتن تست‌ها در `backend/tests/test_security.py`**:
   - تست path traversal با `../../etc/passwd`
   - تست مسیر absolute خارج از allowed dir مثل `/proc/1/environ`
   - تست symlink escape
   - تست مسیر معتبر که باید pass شود

## 💡 نمونه‌های قبل/بعد
**اعمال validation قبل از استفاده از project_path در run_analysis_stream**

_قبل:_
```
# جمع‌آوری فایل‌های پروژه
                project_path = request.project_path
                files = []

                # خواندن README اگر موجود باشد
                readme_content = ""
                readme_paths = ["README.md", "readme.md", "README.txt"]
                for readme_name in readme_paths:
                    readme_path = os.path.join(project_path, readme_name)
```

_بعد:_
```
# ── اعتبارسنجی و sanitize مسیر پروژه ──
                import pathlib
                from ...core.config import settings

                allowed_base = pathlib.Path(
                    os.environ.get('ALLOWED_PROJECTS_DIR', '/projects')
                ).resolve()
                requested = pathlib.Path(request.project_path).resolve()

                if not requested.is_dir():
                    raise ValueError(f'مسیر پروژه وجود ندارد: {request.project_path}')
                try:
                    requested.relative_to(allowed_base)
                except ValueError:
                    raise ValueError(
                        f'مسیر پروژه خارج از محدوده مجاز است: {request.project_path}'
                    )

                project_path = str(requested)  # resolved, safe path
                files = []

                # خواندن README اگر موجود باشد
                readme_content = ""
                readme_paths = ["README.md", "readme.md", "README.txt"]
                for readme_name in readme_paths:
                    readme_path = os.path.join(project_path, readme_name)
```

**بررسی canonical path در حلقه os.walk برای جلوگیری از symlink escape**

_قبل:_
```
for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in supported_extensions:
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path, project_path)
                            try:
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
```

_بعد:_
```
for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext not in supported_extensions:
                            continue
                        full_path = os.path.join(root, filename)
                        # جلوگیری از symlink escape
                        real_full = os.path.realpath(full_path)
                        if not real_full.startswith(project_path + os.sep) and real_full != project_path:
                            logger.warning(f'Skipping suspicious path: {full_path}')
                            continue
                        rel_path = os.path.relpath(full_path, project_path)
                        try:
                            with open(real_full, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_security.py -v -m security`
- `pytest backend/tests/ -k 'path_traversal or project_path' -v`
- `python -c "import pathlib; p = pathlib.Path('../../etc').resolve(); print(p)"`
- `grep -n 'ALLOWED_PROJECTS_DIR\|relative_to\|realpath' backend/app/api/routes/analysis.py backend/app/core/config.py`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **تابع `run_analysis` (خطوط ۴۶-۸۰ فایل `analysis.py`)** نیز همان `AnalysisRequest` را می‌پذیرد و `project_path` را به `analyzer.analyze_project` پاس می‌دهد — اگر validation فقط در `run_analysis_stream` اعمال شود، endpoint دیگر همچنان آسیب‌پذیر می‌ماند. هر دو endpoint باید یکجا fix شوند.
۲. **مقدار پیش‌فرض `ALLOWED_PROJECTS_DIR`**: اگر این متغیر در production تنظیم نشود و مقدار پیش‌فرض `/projects` باشد که وجود ندارد، تمام درخواست‌های معتبر نیز reject می‌شوند — باید در deployment docs و `.env.example` مستند شود.
۳. **`backend/app/services/deep_analysis_service.py`** که توسط `run_analysis_stream` (خط ۱۲۰-۱۹۸) instantiate می‌شود، ممکن است خودش نیز path operations انجام دهد — باید بررسی شود.
۴. **symlink در `os.walk`**: Python's `os.walk` به صورت پیش‌فرض `followlinks=False` است، اما `os.path.realpath` در بررسی `full_path` ضروری است چون symlink ها می‌توانند در داخل project_path به خارج اشاره کنند.
۵. **frontend error handling**: `frontend/src/app/analysis/page.tsx` (خط ۲۰۰-۲۰۲) فقط `response.ok` را چک می‌کند — باید پیام خطای 400 را به کاربر نمایش دهد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 3: اعتبارسنجی امنیتی مسیر پروژه (Path Traversal Prevention)

**Scope:** این مرحله شامل پیاده‌سازی مکانیزم اعتبارسنجی برای پارامتر `project_path` در endpoint مربوطه است. هدف اصلی جلوگیری از حملات path traversal با محدود کردن مسیرها به یک دایرکتوری مجاز (مانند `./projects`). این مرحله شامل افزودن محدودیت حجم فایل (1MB) و timeout برای عملیات خواندن فایل نیز می‌شود. خارج از scope این مرحله: پیاده‌سازی خود endpoint یا تغییر در ساختار دیتابیس.
**Key terms:** project_path, os.path.abspath, os.path.commonpath, ./projects, backend/app/api/routes/analysis.py, tests/test_analysis.py, backend/tests/test_security.py

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال `project_path=../../etc` خطای 400 برمی‌گرداند
- [ ] ارسال `project_path=/proc/1/environ` خطای 400 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `./projects` به درستی کار می‌کنند
- [ ] تست واحد برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی و محدود کردن `project_path` به یک دایرکتوری مجاز (مثلاً `/tmp/projects` یا `./projects`). از `os.path.abspath` و `os.path.commonpath` برای اطمینان از اینکه مسیر نهایی خارج از محدوده مجاز نیست استفاده شود. همچنین محدودیت حجم فایل خوانده‌شده (مثلاً 1MB) و timeout برای کل عملیات اضافه شود.
```

## 🎯 هدف (خلاصه ساختاریافته)
اعتبارسنجی امنیتی مسیر پروژه (Path Traversal Prevention) در analysis.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_stream` — نقطهٔ ورود آسیب‌پذیری path traversal. `project_path` بدون اعتبارسنجی به `os.walk` و `open` داده می‌شود. اینجا باید تابع اعتبارسنجی اضافه شود.
  ```python
  127:                 project_path = request.project_path
  128:                 files = []
  ...
  160:                 for root, dirs, filenames in os.walk(project_path):
  ...
  173:                                 with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
  174:                                     content = f.read()
  ```
- `backend/app/api/routes/analysis.py:46-80` — `run_analysis`
  ```python
  46:
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی مکانیزم اعتبارسنجی برای پارامتر `project_path` در endpoint مربوطه در فایل `backend/app/api/routes/analysis.py`. هدف اصلی جلوگیری از حملات path traversal با محدود کردن مسیرها به یک دایرکتوری مجاز (مانند `./projects`). این مرحله شامل افزودن محدودیت حجم فایل (1MB) و timeout برای عملیات خواندن فایل نیز می‌شود. خارج از scope این مرحله: پیاده‌سازی خود endpoint یا تغییر در ساختار دیتابیس.

کلیدواژه‌های کاربر: `project_path`, `os.path.abspath`, `os.path.commonpath`, `./projects`, `backend/app/api/routes/analysis.py`, `tests/test_analysis.py`, `backend/tests/test_security.py`.

شواهد در کد واقعی: در `backend/app/api/routes/analysis.py`، خطوط 127-180، پارامتر `project_path` از `request.project_path` (خط 127) گرفته می‌شود و بدون هیچ اعتبارسنجی امنیتی در `os.walk` (خط 160) و `open` (خط 173) استفاده می‌شود. این یک آسیب‌پذیری path traversal بحرانی است. همچنین در خطوط 132-141، مسیر README نیز بدون اعتبارسنجی خوانده می‌شود. فایل‌های تست مرتبط: `backend/tests/test_runtime_verify_integration.py` و `backend/tests/test_runtime_verify_stage1.py` که می‌توان تست‌های امنیتی به آن‌ها اضافه کرد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل `backend/app/api/routes/analysis.py`، یک تابع کمکی به نام `validate_project_path(path: str) -> str` در خطوط قبل از 127 اضافه کن که:
   - با `os.path.abspath` مسیر مطلق را محاسبه کند.
   - با `os.path.commonpath` بررسی کند که مسیر مطلق زیرمجموعهٔ `./projects` (یا یک دایرکتوری مجاز کانفیگ‌شده) باشد.
   - اگر مسیر نامعتبر بود، `HTTPException` با status 400 برگرداند.
2. در خط 127، بعد از `project_path = request.project_path`، تابع `validate_project_path` را صدا بزن.
3. محدودیت حجم فایل: در حلقهٔ خواندن فایل‌ها (خطوط 160-180)، قبل از `content = f.read()`، حجم فایل را با `os.path.getsize` بررسی کن و اگر > 1MB بود، فایل را رد کن (یا با warning ادامه بده).
4. timeout: عملیات خواندن فایل را در `asyncio.wait_for` با timeout مثلاً 30 ثانیه قرار بده.
5. تست واحد: در `backend/tests/test_security.py` (یا `backend/tests/test_runtime_verify_integration.py`) تست‌هایی برای سناریوهای `project_path=../../etc` و `project_path=/proc/1/environ` اضافه کن که انتظار 400 دارند.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 4: اعتبارسنجی مسیر پروژه در تحلیل کد

**Scope:** این مرحله شامل افزودن اعتبارسنجی امنیتی برای مسیر پروژه در endpoint تحلیل کد است. مسیر ورودی کاربر باید با BASE_DIR (که ./projects است) شروع شود تا از دسترسی به دایرکتوری‌های خارج از محدوده جلوگیری شود. فقط فایل backend/app/api/routes/analysis.py تحت تأثیر قرار می‌گیرد. تست‌های مرتبط در tests/test_analysis.py باید به‌روزرسانی شوند.
**Key terms:** backend/app/api/routes/analysis.py, tests/test_analysis.py, BASE_DIR, project_path, HTTPException

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**اعتبارسنجی مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
BASE_DIR = os.path.abspath('./projects')
user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR):
    raise HTTPException(400, 'Invalid project path')
for root, dirs, filenames in os.walk(user_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
BASE_DIR = os.path.abspath('./projects')
user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR):
    raise HTTPException(400, 'Invalid project path')
for root, dirs, filenames in os.walk(user_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
backend/app/api/routes/analysis.py, tests/test_analysis.py, BASE_DIR, project_path, HTTPException
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن اعتبارسنجی امنیتی مسیر پروژه در endpoint تحلیل کد

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py` — `endpoint تحلیل کد — استفاده از request.project_path` — این فایل deep-read شده است (در لیست deep-read files موجود است) اما محتوای آن در deep_context ارائه‌شده truncate شده و snippet مستقیم در دسترس نیست. مجری باید فایل را باز کند و تمام مکان‌هایی که `project_path` یا `request.project_path` به `os.walk`، `os.listdir` یا `open()` پاس داده می‌شود را شناسایی کند. طبق درخواست کاربر، pattern فعلی `for root, dirs, filenames in os.walk(project_path):` است که باید با اعتبارسنجی BASE_DIR جایگزین شود.
- `backend/app/api/routes/simple_projects.py:554-574` — `generate_more_files` — این endpoint نیز از مسیر پروژه برای عملیات فایل‌سیستمی استفاده می‌کند. اگرچه هدف اصلی تسک analysis.py است، این الگو در simple_projects.py هم وجود دارد و باید در آینده بررسی شود. `file_path` از request.file_paths می‌آید و به `project_path / file_path` تبدیل می‌شود — path traversal احتمالی.
  ```python
  project_path = creator.workspace / project_id
  
      for file_path in file_paths:
          try:
              # توضیح فایل
              file_desc = descriptions.get(file_path, f"فایل {file_path} برای پروژه")
  
              # تولید محتوای فایل با AI
              content = await creator._generate_file(
                  project_name=project.name,
                  project_desc=project.description,
                  project_type=project.project_type,
                  file_path=file_path,
                  file_desc=file_desc,
                  ai_generate=ai_generate
              )
  
              # ذخیره فایل در دیسک
              full_path = project_path / file_path
              full_path.parent.mkdir(parents=True, exist_ok=True)
  ```
- `backend/app/api/routes/projects.py:81-88` — `get_project` — این فایل deep-read شده است. الگوی HTTPException در این فایل نشان می‌دهد که پروژه از HTTPException با status_code و detail استفاده می‌کند — همان الگویی که باید در analysis.py برای path validation استفاده شود.
  ```python
  @router.get("/{project_id}")
  async def get_project(project_id: str):
      """دریافت اطلاعات پروژه"""
      service = get_project_service()
      result = service.get_project(project_id)
      if not result.get("success"):
          raise HTTPException(status_code=404, detail=result.get("error"))
      return result
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js (TypeScript). کتابخانه‌های مرتبط: `os` (stdlib Python برای path manipulation)، `fastapi.HTTPException` برای error handling، `pydantic.BaseModel` برای request validation. الگوی موجود در پروژه برای HTTPException: `raise HTTPException(status_code=400, detail='...')` — همان‌طور که در projects.py خط ۸۷ و simple_projects.py خط ۲۵۳-۲۵۶ دیده می‌شود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 1) — فایل هدف اصلی تسک — طبق درخواست کاربر، اعتبارسنجی BASE_DIR باید در این فایل اضافه شود. این فایل در نقشه import‌های داخلی توسط ai_manager، database و model_profiler import می‌شود.
- `backend/app/services/project_analyzer.py` (سطر 1) — طبق نقشه import‌های داخلی، model_profiler توسط project_analyzer.py import می‌شود و project_analyzer احتمالاً توسط analysis.py فراخوانی می‌شود. اگر project_path در لایه service هم استفاده شود، باید اعتبارسنجی در آنجا هم اعمال شود.
- `backend/app/services/deep_analysis_service.py` (سطر 1) — طبق نقشه import‌های داخلی، ai_base.py و model_profiler.py توسط deep_analysis_service.py import می‌شوند — همان‌هایی که analysis.py هم استفاده می‌کند. اگر deep_analysis_service مسیر پروژه را دریافت کند، باید اعتبارسنجی مشابه داشته باشد.
- `backend/app/api/routes/security_analysis.py` (سطر 1) — این فایل در نقشه import‌های داخلی از database.py و models/project.py استفاده می‌کند — همان وابستگی‌های analysis.py. اگر security_analysis.py هم از project_path استفاده کند، باید همان اعتبارسنجی را داشته باشد تا consistency حفظ شود.
- `backend/app/services/project_health_analyzer.py` (سطر 1) — طبق نقشه import‌های داخلی، project_health_analyzer توسط project_health route استفاده می‌شود که با analysis.py در یک لایه قرار دارد. اگر این سرویس هم از مسیر فایل‌سیستم استفاده کند، باید اعتبارسنجی مشابه اعمال شود.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/api/routes/analysis.py` در نقشه import‌های داخلی پروژه یکی از مصرف‌کنندگان اصلی `backend/app/services/ai_manager.py` (که ۱۴ فایل آن را import می‌کنند)، `backend/app/core/database.py` (که ۲۰ فایل آن را import می‌کنند) و `backend/app/services/model_profiler.py` (که ۸ فایل آن را import می‌کنند) است. تغییر در analysis.py مستقیماً روی هیچ فایل دیگری اثر نمی‌گذارد (چون analysis.py یک route است نه یک service که توسط دیگران import شود). اما الگوی اعتبارسنجی که اینجا پیاده می‌شود باید به‌عنوان best practice در `backend/app/api/routes/security_analysis.py`، `backend/app/api/routes/project_health.py` و `backend/app/services/project_analyzer.py` هم اعمال شود تا consistency امنیتی در کل پروژه حفظ شود. تست‌های `backend/tests/test_analysis.py` باید برای پوشش سناریوهای path traversal به‌روزرسانی شوند.

## 🔍 Context و وضعیت فعلی
این تسک شامل افزودن اعتبارسنجی امنیتی (path traversal prevention) برای مسیر پروژه در endpoint تحلیل کد است. طبق درخواست کاربر، فایل هدف اصلی `backend/app/api/routes/analysis.py` است و تست‌های مرتبط در `tests/test_analysis.py` باید به‌روزرسانی شوند.

مشکل اصلی: در حال حاضر مسیر ورودی کاربر (`request.project_path`) بدون هیچ اعتبارسنجی‌ای مستقیماً به `os.walk(project_path)` پاس داده می‌شود. این یعنی یک کاربر مخرب می‌تواند با ارسال مسیرهایی مثل `../../etc/passwd` یا `../../../root` به دایرکتوری‌های خارج از محدوده مجاز دسترسی پیدا کند — این یک آسیب‌پذیری path traversal کلاسیک است.

راه‌حل پیشنهادی کاربر: تعریف `BASE_DIR = os.path.abspath('./projects')` و سپس بررسی اینکه `os.path.abspath(request.project_path)` با `BASE_DIR` شروع می‌شود. اگر مسیر خارج از `BASE_DIR` بود، باید `HTTPException(400, 'Invalid project path')` raise شود.

کد قبل (آسیب‌پذیر):
```python
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

کد بعد (ایمن):
```python
import os
BASE_DIR = os.path.abspath('./projects')
user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR):
    raise HTTPException(400, 'Invalid project path')
for root, dirs, filenames in os.walk(user_path):
```

کلیدواژه‌های مرتبط از درخواست کاربر: `backend/app/api/routes/analysis.py`, `tests/test_analysis.py`, `BASE_DIR`, `project_path`, `HTTPException`. این تغییر فقط فایل `analysis.py` را تحت تأثیر قرار می‌دهد و تست‌های `tests/test_analysis.py` باید برای پوشش سناریوهای مسیر معتبر و نامعتبر به‌روزرسانی شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] درخواست با project_path معتبر داخل ./projects باید با status 200 پاسخ دهد
- [ ] درخواست با project_path حاوی path traversal (مثل ../../etc/passwd) باید با status 400 و detail 'Invalid project path' رد شود
- [ ] متغیر BASE_DIR در analysis.py با مقدار os.path.abspath('./projects') تعریف شده باشد
- [ ] تست‌های tests/test_analysis.py برای سناریوهای path traversal pass شوند
- [ ] مسیر ./projects_evil که با ./projects شروع می‌شود اما خارج از BASE_DIR است باید با 400 رد شود (false positive prevention)
- [ ] کد اعتبارسنجی از os.sep برای جداکننده مسیر استفاده کند تا cross-platform باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل `backend/app/api/routes/analysis.py` را باز کن و endpoint(های) تحلیل کد که از `request.project_path` استفاده می‌کنند را شناسایی کن.
2. در ابتدای تابع endpoint (قبل از هر عملیات فایل‌سیستمی)، کد اعتبارسنجی زیر را اضافه کن:
   ```python
   import os
   BASE_DIR = os.path.abspath('./projects')
   user_path = os.path.abspath(request.project_path)
   if not user_path.startswith(BASE_DIR + os.sep) and user_path != BASE_DIR:
       raise HTTPException(status_code=400, detail='Invalid project path')
   ```
   (توجه: استفاده از `BASE_DIR + os.sep` برای جلوگیری از false positive در مسیرهایی مثل `./projects_evil` که با `./projects` شروع می‌شوند اما خارج از محدوده هستند)
3. تمام جاهایی که `project_path` به `os.walk`، `os.listdir`، `open()` یا هر عملیات فایل‌سیستمی دیگری پاس داده می‌شود را با `user_path` (مسیر normalize شده) جایگزین کن.
4. فایل `backend/tests/test_analysis.py` را به‌روزرسانی کن و تست‌های زیر را اضافه کن:
   - تست مسیر معتبر داخل `./projects` → باید 200 برگرداند
   - تست path traversal با `../../etc` → باید 400 برگرداند
   - تست مسیر absolute خارج از BASE_DIR → باید 400 برگرداند
   - تست مسیر `./projects_evil` (false positive check) → باید 400 برگرداند
5. اطمینان حاصل کن که `BASE_DIR` به‌صورت constant در سطح module تعریف شده (نه داخل تابع) تا قابل override در تست باشد.

## 💡 نمونه‌های قبل/بعد
**اعتبارسنجی مسیر پروژه در analysis.py — طبق نمونه کاربر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
    # پردازش فایل‌ها بدون اعتبارسنجی مسیر
```

_بعد:_
```
import os

BASE_DIR = os.path.abspath('./projects')

user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR + os.sep) and user_path != BASE_DIR:
    raise HTTPException(status_code=400, detail='Invalid project path')

for root, dirs, filenames in os.walk(user_path):
    # پردازش فایل‌ها با مسیر اعتبارسنجی‌شده
```

**تست path traversal در tests/test_analysis.py**

_قبل:_
```
# تست موجود — فقط مسیر معتبر را تست می‌کند
def test_analyze_project():
    response = client.post('/api/analysis/...', json={'project_path': './projects/my_project'})
    assert response.status_code == 200
```

_بعد:_
```
# تست‌های جدید برای اعتبارسنجی مسیر
def test_analyze_project_valid_path():
    response = client.post('/api/analysis/...', json={'project_path': './projects/my_project'})
    assert response.status_code == 200

def test_analyze_project_path_traversal_blocked():
    response = client.post('/api/analysis/...', json={'project_path': '../../etc/passwd'})
    assert response.status_code == 400
    assert 'Invalid project path' in response.json()['detail']

def test_analyze_project_outside_base_dir_blocked():
    response = client.post('/api/analysis/...', json={'project_path': '/tmp/evil'})
    assert response.status_code == 400

def test_analyze_project_false_positive_check():
    # مسیری که با 'projects' شروع می‌شود اما خارج از BASE_DIR است
    response = client.post('/api/analysis/...', json={'project_path': './projects_evil/hack'})
    assert response.status_code == 400
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_analysis.py -v`
- `pytest backend/tests/test_analysis.py -v -k 'path'`
- `grep -n 'BASE_DIR\|startswith\|project_path' backend/app/api/routes/analysis.py`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **False positive در startswith**: اگر فقط از `user_path.startswith(BASE_DIR)` استفاده شود (بدون `os.sep`)، مسیر `./projects_evil` هم معتبر تشخیص داده می‌شود — باید از `BASE_DIR + os.sep` استفاده شود. ۲. **Symlink bypass**: `os.path.abspath` symlink ها را resolve نمی‌کند — برای امنیت بیشتر باید از `os.path.realpath` استفاده شود. ۳. **BASE_DIR نسبی**: اگر working directory سرور تغییر کند، `./projects` به مسیر اشتباه resolve می‌شود — باید از `__file__` برای مسیر absolute استفاده شود: `BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../projects'))`. ۴. **تأثیر بر تست‌های موجود**: تست‌های فعلی در `backend/tests/test_analysis.py` که با مسیرهای mock کار می‌کنند ممکن است fail شوند — باید BASE_DIR را در تست‌ها mock کنند. ۵. **سایر endpoints مشابه**: `backend/app/api/routes/security_analysis.py` و `backend/app/services/project_analyzer.py` هم احتمالاً از project_path استفاده می‌کنند و باید بررسی شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 5: اجرای دستورات اعتبارسنجی امنیتی (Path Traversal)

**Scope:** این بخش شامل دو دستور اعتبارسنجی است: (1) یک درخواست curl برای تست نفوذ path traversal با ارسال project_path='../../etc' به endpoint /analysis/run-stream، و (2) اجرای تست pytest مخصوص test_analysis.py با فیلتر path_traversal. این مرحله صرفاً اجرای دستورات تست است و شامل پیاده‌سازی کد یا تغییرات نمی‌شود.
**Key terms:** curl, POST, http://localhost:8000/analysis/run-stream, project_id, project_path, ../../etc, pytest, tests/test_analysis.py, path_traversal

**بخش مربوط از متن کاربر:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'`
- `pytest tests/test_analysis.py -k path_traversal`
```

## 🎯 هدف (خلاصه ساختاریافته)
اعتبارسنجی امنیتی Path Traversal در endpoint /analysis/run-stream

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:83-198` — `run_analysis_stream` — این تابع مقدار `request.project_path` را بدون هیچ validation یا sanitization مستقیماً در `os.path.join` و `os.walk` استفاده می‌کند. ارسال `../../etc` می‌تواند منجر به path traversal شود. خط ۱۲۷ نقطه ورود اصلی است.
  ```python
  @router.post("/run-stream")
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      async def run_analysis_task():
          nonlocal final_result
          try:
              ...
              project_path = request.project_path
              files = []
              readme_paths = ["README.md", "readme.md", "README.txt"]
              for readme_name in readme_paths:
                  readme_path = os.path.join(project_path, readme_name)
  ```
- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — مدل Pydantic `AnalysisRequest` فیلد `project_path` را به‌صورت `str` خام تعریف کرده بدون هیچ validator. این نقطه‌ای است که باید path traversal validation اضافه شود (مثلاً با `@validator` یا `field_validator` در Pydantic v2).
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:160-180` — `run_analysis_stream` — این بخش `os.walk(project_path)` را با مقدار خام کاربر اجرا می‌کند. اگر `project_path='../../etc'` باشد، سیستم شروع به walk کردن `/etc` می‌کند و فایل‌های حساس سیستم را می‌خواند.
  ```python
  for root, dirs, filenames in os.walk(project_path):
      # فیلتر دایرکتوری‌های غیرضروری
      dirs[:] = [d for d in dirs if d not in {
          'node_modules', '.git', '__pycache__', 'venv',
          '.venv', 'env', 'dist', 'build', '.next'
      }]
  
      for filename in filenames:
          ext = os.path.splitext(filename)[1].lower()
          if ext in supported_extensions:
              full_path = os.path.join(root, filename)
              rel_path = os.path.relpath(full_path, project_path)
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js 14. کتابخانه‌های مرتبط: Pydantic v2 (برای validation مدل‌ها)، os.walk و os.path.join (Python stdlib — نقطه آسیب‌پذیری). تست: pytest با pytest-asyncio. سرور: uvicorn روی پورت 8000. endpoint مورد نظر: POST /api/analysis/run-stream که StreamingResponse برمی‌گرداند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/content_sanitizer.py` (سطر 1) — این سرویس احتمالاً توابع sanitization دارد که باید بررسی شود آیا path validation در آن وجود دارد یا نه. اگر وجود دارد، باید در `run_analysis_stream` فراخوانی شود.
- `backend/app/api/routes/analysis.py` (سطر 46) — فایل اصلی که endpoint /analysis/run-stream و /analysis/run را تعریف می‌کند. هر دو endpoint از `AnalysisRequest` استفاده می‌کنند و هر دو در معرض path traversal هستند.
- `backend/app/services/deep_analysis_service.py` (سطر 120) — این سرویس توسط `run_analysis_stream` در خط ۱۲۰ فراخوانی می‌شود و `project_path` را دریافت می‌کند. اگر validation در route انجام نشود، این سرویس هم در معرض خطر است.
- `backend/app/api/routes/security_analysis.py` (سطر 39) — این فایل endpoint های امنیتی مثل `/scan-secrets` و `/validate-code` را تعریف می‌کند. الگوی validation در این فایل می‌تواند به‌عنوان مرجع برای اضافه کردن path validation به `analysis.py` استفاده شود.
- `backend/app/main.py` (سطر 1) — فایل اصلی FastAPI که router های مختلف را register می‌کند. برای اطمینان از اینکه middleware امنیتی (مثل rate limiting یا input validation) روی همه endpoint ها اعمال می‌شود، باید بررسی شود.

## 🌐 نقشهٔ وابستگی‌ها
endpoint `/analysis/run-stream` در `backend/app/api/routes/analysis.py` (خط ۸۳) توسط `frontend/src/app/analysis/page.tsx` (خط ۱۹۰) فراخوانی می‌شود. این endpoint از `DeepAnalysisService` در `backend/app/services/deep_analysis_service.py` استفاده می‌کند که خود به `ai_manager` از `backend/app/services/ai_manager.py` وابسته است (۱۴ فایل آن را import می‌کنند). مدل `AnalysisRequest` در هر دو endpoint `/run` و `/run-stream` مشترک است، پس هر تغییر در validation این مدل روی هر دو تأثیر می‌گذارد. همچنین `backend/app/core/database.py` در خط ۱۱۶ داخل `run_analysis_stream` استفاده می‌شود که ۱۶ فایل آن را import می‌کنند.

## 🔍 Context و وضعیت فعلی
این تسک شامل اجرای دو دستور اعتبارسنجی امنیتی برای تست آسیب‌پذیری Path Traversal در endpoint `/analysis/run-stream` است. کاربر دو دستور مشخص را تعریف کرده:

**دستور ۱ — تست نفوذ با curl:**
```
curl -X POST http://localhost:8000/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'
```
این دستور یک درخواست POST به endpoint `http://localhost:8000/analysis/run-stream` ارسال می‌کند و مقدار `project_path='../../etc'` را به‌عنوان payload می‌فرستد تا بررسی شود آیا سرور در برابر حملات path traversal محافظت شده است یا خیر.

**دستور ۲ — اجرای pytest:**
```
pytest tests/test_analysis.py -k path_traversal
```
این دستور تست‌های مخصوص path_traversal را در فایل `tests/test_analysis.py` اجرا می‌کند.

**شواهد در کد واقعی:**
در `backend/app/api/routes/analysis.py` خط ۸۳-۱۹۸، تابع `run_analysis_stream` مقدار `request.project_path` را مستقیماً در `os.walk(project_path)` (خط ۱۶۰) و `os.path.join(project_path, readme_name)` (خط ۱۳۴) استفاده می‌کند بدون هیچ‌گونه sanitization یا validation. این یعنی ارسال `../../etc` می‌تواند منجر به خواندن فایل‌های خارج از محدوده مجاز شود.

همچنین در `backend/app/api/routes/analysis.py` خط ۳۰-۳۶، مدل `AnalysisRequest` فیلد `project_path: str` را بدون هیچ validator تعریف کرده است.

این تسک **صرفاً اجرای دستورات تست** است و شامل پیاده‌سازی کد یا تغییرات نمی‌شود — هدف تأیید وجود یا عدم وجود آسیب‌پذیری است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] دستور curl با project_path='../../etc' باید پاسخ HTTP 4xx (400 یا 422) دریافت کند، نه 200 با stream داده
- [ ] دستور `pytest tests/test_analysis.py -k path_traversal` باید بدون خطای import اجرا شود (حتی اگر تست‌ها وجود نداشته باشند، باید collected 0 items نشان دهد نه error)
- [ ] مقدار project_path='../../etc' نباید منجر به خواندن فایل‌های خارج از دایرکتوری مجاز شود — بررسی با grep در لاگ‌های سرور
- [ ] endpoint /analysis/run-stream باید در برابر project_path='/etc/passwd' نیز محافظت کند (absolute path)
- [ ] endpoint /analysis/run با project_path معتبر (مثلاً './myproject') باید همچنان کار کند و status 200 برگرداند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. **مرحله ۱ — اطمینان از اجرای سرور:**
مطمئن شو backend روی `http://localhost:8000` در حال اجراست:
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

**مرحله ۲ — اجرای تست curl برای path traversal:**
```bash
curl -X POST http://localhost:8000/analysis/run-stream \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"test","project_path":"../../etc"}'
```
انتظار: سرور باید با خطای ۴۰۰ یا ۴۲۲ پاسخ دهد و اجازه دسترسی به `../../etc` را ندهد. اگر سرور شروع به stream کردن فایل‌های `/etc` کرد، آسیب‌پذیری تأیید شده است.

**مرحله ۳ — اجرای pytest با فیلتر path_traversal:**
```bash
cd backend && pytest tests/test_analysis.py -k path_traversal -v
```
اگر فایل `tests/test_analysis.py` وجود ندارد، باید ابتدا ایجاد شود (این خارج از scope این تسک است).

**مرحله ۴ — ثبت نتایج:**
- اگر curl موفق شد (status 200 + stream داده): آسیب‌پذیری وجود دارد → باید در `backend/app/api/routes/analysis.py` تابع `run_analysis_stream` در خط ۱۲۷ validation اضافه شود.
- اگر pytest fail شد: تست‌های path_traversal وجود ندارند یا fail می‌شوند → نیاز به پیاده‌سازی محافظت.

**فایل‌های مرتبط برای بررسی:**
- `backend/app/api/routes/analysis.py` — endpoint اصلی (خط ۸۳-۱۹۸)
- `backend/app/services/content_sanitizer.py` — بررسی وجود sanitization موجود

## 💡 نمونه‌های قبل/بعد
**مدل AnalysisRequest بدون validation (وضعیت فعلی آسیب‌پذیر)**

_قبل:_
```
class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None
```

_بعد:_
```
import os
from pydantic import field_validator

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None

    @field_validator('project_path')
    @classmethod
    def validate_no_path_traversal(cls, v: str) -> str:
        # نرمال‌سازی مسیر
        normalized = os.path.normpath(v)
        # بررسی path traversal
        if normalized.startswith('..') or '/../' in normalized or normalized.startswith('/'):
            raise ValueError('مسیر پروژه نامعتبر است — path traversal مجاز نیست')
        return v
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'`
- `curl -X POST http://localhost:8000/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'`
- `cd backend && pytest tests/test_analysis.py -k path_traversal -v`
- `cd backend && pytest tests/test_analysis.py -k path_traversal -v --tb=short 2>&1 | head -50`
- `cd backend && python -c "import os; p='../../etc'; print(os.path.normpath(p)); print(p.startswith('..'))"`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **تابع `run_analysis_stream` در `backend/app/api/routes/analysis.py` خط ۱۶۰**: `os.walk(project_path)` با مقدار خام کاربر اجرا می‌شود — اگر path traversal وجود داشته باشد، سرور فایل‌های `/etc` را می‌خواند و از طریق SSE stream به کاربر ارسال می‌کند. این یک آسیب‌پذیری critical است.
۲. **مدل `AnalysisRequest` مشترک بین دو endpoint**: هر دو `/run` (خط ۴۶) و `/run-stream` (خط ۸۳) از همین مدل استفاده می‌کنند — اگر validation اضافه شود، هر دو تحت تأثیر قرار می‌گیرند (مثبت).
۳. **`roadmap_path` هم آسیب‌پذیر است**: در خط ۱۴۵ مقدار `request.roadmap_path` نیز بدون validation در `os.path.exists` استفاده می‌شود.
۴. **فایل `tests/test_analysis.py` ممکن است وجود نداشته باشد**: در ساختار پروژه فقط `backend/tests/` دیده می‌شود و فایل `test_analysis.py` در لیست فایل‌های موجود نیست — دستور pytest ممکن است با خطای `file not found` مواجه شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 6: پیاده‌سازی مدیریت خطا و لاگینگ در API Routes (analysis.py و chat.py)

**Scope:** این مرحله شامل افزودن try-except به تمام route handlers در فایل‌های backend/app/api/routes/analysis.py و backend/app/api/routes/chat.py، لاگ کردن خطاهای 500 با timestamp, level, message, traceback، و برگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx) است. همچنین پیکربندی لاگر در backend/app/core/ باید بررسی شود. خارج از scope: تغییر در سایر فایل‌ها یا endpointها.
**Key terms:** backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/, try-except, logging.error, logger.error, log.error, HTTPException, status_code, JSONResponse, timestamp, level, message, traceback

**بخش مربوط از متن کاربر:**
```
📋 acceptance_criteria کامل:
  - همه route handlers دارای try-except باشند [verify_method=static] [verify_plan={"grep_patterns": ["try:", "except"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - خطاهای 500 به درستی لاگ شوند [verify_method=static] [verify_plan={"grep_patterns": ["logging.error", "logger.error", "log.error"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند [verify_method=static] [verify_plan={"grep_patterns": ["HTTPException", "status_code", "return JSONResponse"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - لاگ‌ها شامل timestamp, level, message, traceback باشند [verify_method=static] [verify_plan={"grep_patterns": ["timestamp", "level", "message", "traceback"], "files_hint": ["backend/app/core/"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن مدیریت خطا و لاگینگ به analysis.py و chat.py

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی مدیریت خطا و لاگینگ در API Routes (analysis.py و chat.py). این مرحله شامل افزودن try-except به تمام route handlers در فایل‌های backend/app/api/routes/analysis.py و backend/app/api/routes/chat.py، لاگ کردن خطاهای 500 با timestamp, level, message, traceback، و برگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx) است. همچنین پیکربندی لاگر در backend/app/core/ باید بررسی شود. خارج از scope: تغییر در سایر فایل‌ها یا endpointها.

بررسی کد فعلی در analysis.py (فایل deep-read شده) نشان می‌دهد:
- خط 75-80: در تابع run_analysis یک try-except وجود دارد اما فقط logger.error می‌کند و AnalysisResponse برمی‌گرداند — نه HTTPException با status_code مناسب.
- خط 200-206: در run_analysis_stream یک try-except وجود دارد که خطا را به progress_queue می‌فرستد اما پاسخ HTTP مناسب (5xx) برنمی‌گرداند.
- خط 251-253: در generate_events یک try-except دیگر وجود دارد که خطا را yield می‌کند اما status_code مناسب ندارد.
- خط 76: از logger.error استفاده شده اما timestamp, level, message, traceback به صورت ساختاریافته لاگ نمی‌شوند.
- خط 303: در get_analysis_report از HTTPException با status_code=404 استفاده شده — این خوب است.
- خط 509: در download_analysis_report از HTTPException با status_code=400 استفاده شده — این خوب است.
- سایر route handlers (get_analysis_reports در خط 271، delete_analysis_report در خط 309، get_schedule در خط 594، update_schedule در خط 624، delete_schedule در خط 654، get_analysis_stats در خط 679) فاقد try-except هستند و خطاهای پیش‌بینی‌نشده را مدیریت نمی‌کنند.

کلیدواژه‌های کاربر: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/, try-except, logging.error, logger.error, log.error, HTTPException, status_code, JSONResponse, timestamp, level, message, traceback

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/api/routes/analysis.py:
   - به تابع get_analysis_reports (خط 271) try-except اضافه کن: خطاهای دیتابیس را با logger.error لاگ کن (شامل timestamp, level, message, traceback) و HTTPException با status_code=500 برگردان.
   - به تابع delete_analysis_report (خط 309) try-except اضافه کن: مشابه بالا.
   - به تابع get_schedule (خط 594) try-except اضافه کن: مشابه بالا.
   - به تابع update_schedule (خط 624) try-except اضافه کن: مشابه بالا.
   - به تابع delete_schedule (خط 654) try-except اضافه کن: مشابه بالا.
   - به تابع get_analysis_stats (خط 679) try-except اضافه کن: مشابه بالا.
   - در تابع run_analysis_stream (خط 83)، بلوک except خط 200-206 را اصلاح کن تا علاوه بر progress_queue، یک HTTPException با status_code=500 نیز برگرداند.
   - در تابع download_analysis_report (خط 328)، بلوک except (که وجود ندارد) را اضافه کن.

2. در فایل backend/app/api/routes/chat.py (که deep-read نشده):
   - تمام route handlers را بررسی کن.
   - به هر handler که فاقد try-except است، try-except اضافه کن.
   - خطاهای 500 را با logger.error لاگ کن (شامل timestamp, level, message, traceback).
   - پاسخ‌های HTTP مناسب (4xx برای خطاهای کاربر، 5xx برای خطاهای سرور) برگردان.

3. در backend/app/core/ (فایل‌های config.py و logging_utils.py):
   - بررسی کن که logger پیکربندی شده باشد و timestamp, level, message, traceback را پشتیبانی کند.
   - اگر logging_utils.py از StructuredLogger استفاده می‌

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 7: یادداشت مهم برای مدل اجراکننده — بررسی مستقل پیش از تغییر

**Scope:** این بخش یک یادداشت هشداردهنده است که به مدل اجراکننده یادآوری می‌کند پیش از هر تغییری، ساختار repo، فایل‌های ذکرشده و وابستگی‌های آن‌ها را مستقل بررسی کند. این بخش شامل دستورالعمل‌های رفتاری برای مدل است و هیچ وظیفهٔ اجرایی مشخصی ندارد. بنابراین، این بخش به‌عنوان یک مرحلهٔ اجرایی در نظر گرفته نمی‌شود و باید رد شود.
— [merged] این بخش یک یادداشت هشداردهنده است که به مدل اجراکننده یادآوری می‌کند قبل از هر تغییری، ساختار repo، فایل‌های ذکرشده و وابستگی‌ها را مستقل بررسی کند. این بخش خودش یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک برای نحوه اجرای سایر مراحل است. شامل هیچ آیتم explicit برای اجرا نیست.

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن دستورالعمل بررسی مستقل repo به مدل اجراکننده

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `docs/ARCHITECTURE.md` — اگر هدف مستندسازی دستورالعمل‌های رفتاری برای مدل اجراکننده است، docs/ARCHITECTURE.md یا docs/README.md مناسب‌ترین محل در ساختار فعلی پروژه هستند. این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند.
- `backend/app/api/routes/system_prompts.py` — اگر هدف embed کردن این دستورالعمل در system prompt‌های پروژه است، این فایل محل مناسب است. این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs. این درخواست فنی نیست و نیازی به هیچ library یا framework خاصی ندارد. اگر به مستندسازی تبدیل شود، فقط Markdown لازم است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `docs/ARCHITECTURE.md` (سطر 1) — مستندات معماری پروژه — محل طبیعی برای دستورالعمل‌های متدولوژیک و رفتاری
- `docs/README.md` (سطر 1) — مستندات اصلی پروژه — ممکن است محل مناسبی برای دستورالعمل‌های contributor باشد
- `backend/app/api/routes/system_prompts.py` (سطر 1) — مدیریت system prompt‌های پروژه — اگر هدف embed کردن دستورالعمل در prompt است

## 🌐 نقشهٔ وابستگی‌ها
این درخواست هیچ وابستگی کدی به فایل‌های موجود پروژه ندارد. اگر به‌عنوان مستندسازی پیاده شود: docs/ARCHITECTURE.md مستقل است و هیچ فایلی آن را import نمی‌کند. backend/app/api/routes/system_prompts.py توسط backend/app/main.py رجیستر می‌شود. backend/app/services/oversight_strong_prompt.py توسط سرویس‌های oversight استفاده می‌شود. هیچ تغییر کدی در این تسک وجود ندارد که بتواند روی فایل‌های دیگر اثر بگذارد.

## 🔍 Context و وضعیت فعلی
این درخواست یک یادداشت متدولوژیک و هشداردهنده برای مدل اجراکننده است — نه یک وظیفهٔ اجرایی مشخص با کد قابل تغییر. متن کاربر به‌صراحت اعلام می‌کند: «این بخش شامل دستورالعمل‌های رفتاری برای مدل است و هیچ وظیفهٔ اجرایی مشخصی ندارد» و «این بخش خودش یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک برای نحوه اجرای سایر مراحل است. شامل هیچ آیتم explicit برای اجرا نیست.»

محتوای اصلی درخواست شامل سه بخش است:

۱. **یادداشت هشداردهنده به مدل اجراکننده**: پیش از هر تغییر، ساختار repo، فایل‌های ذکرشده و وابستگی‌های آن‌ها را مستقل بررسی کن. اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد («خودت گفتی» قابل قبول نیست).

۲. **دستورالعمل کار طولانی**: خلاصه‌اش نکن. همه را به‌طور کامل انجام بده. اگر یک کامیت گنجایش ندارد، در چندین کامیت متوالی انجام بده — ولی هیچ بخشی را skip نکن. ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests). در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.

۳. **دستورالعمل معیارهای پذیرش مبهم**: اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

این دستورالعمل‌ها در هیچ فایل کد پروژه (نه در backend/app/api/routes/analysis.py، نه در backend/app/api/routes/github_import.py، نه در backend/app/api/routes/model_profiles.py و نه در هیچ فایل دیگری از ساختار پروژه) جای پیاده‌سازی ندارند. این یک راهنمای رفتاری برای مدل AI است که تسک‌های آینده را اجرا می‌کند.

اگر هدف واقعی کاربر مستندسازی این دستورالعمل‌ها در پروژه است (مثلاً در CONTRIBUTING.md یا ARCHITECTURE.md)، باید به‌صورت یک تسک مستقل با هدف مشخص تعریف شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] این تسک هیچ معیار پذیرش اجرایی ندارد — کاربر خودش تصریح کرده که این بخش شامل هیچ آیتم explicit برای اجرا نیست
- [ ] اگر هدف مستندسازی است: فایل docs/ARCHITECTURE.md باید بخش جدیدی با عنوان 'دستورالعمل‌های مدل اجراکننده' داشته باشد
- [ ] اگر هدف PR template است: فایل .github/PULL_REQUEST_TEMPLATE.md باید ایجاد شده و شامل checklist کامیت‌ها باشد
- [ ] کاربر باید clarify کند که هدف واقعی این درخواست چیست: مستندسازی در docs، PR template، یا embed در system prompt
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. چون این درخواست هیچ وظیفهٔ اجرایی مشخصی ندارد و کاربر خودش تصریح کرده «شامل هیچ آیتم explicit برای اجرا نیست»، اقدام پیشنهادی به شرح زیر است:

1. **رد کردن به‌عنوان تسک اجرایی**: این درخواست نباید به‌عنوان یک تسک کدنویسی به Cursor/Copilot/ChatGPT ارسال شود — چون خروجی قابل تعریفی ندارد.

2. **اگر هدف مستندسازی است**: کاربر باید یک تسک جدید با هدف مشخص تعریف کند، مثلاً: «افزودن CONTRIBUTING.md با دستورالعمل‌های بررسی مستقل repo برای مدل‌های AI» — در این صورت فایل هدف docs/CONTRIBUTING.md (که در ساختار پروژه موجود نیست ولی docs/ARCHITECTURE.md و docs/README.md موجودند) یا docs/ARCHITECTURE.md خواهد بود.

3. **اگر هدف اضافه کردن این دستورالعمل به PR template است**: فایل .github/PULL_REQUEST_TEMPLATE.md باید ایجاد شود (در ساختار فعلی موجود نیست).

4. **اگر هدف embed کردن این دستورالعمل در system prompt پروژه است**: فایل‌های backend/app/api/routes/system_prompts.py و backend/app/services/oversight_strong_prompt.py محل مناسب‌تری هستند.

در وضعیت فعلی، این تسک به‌عنوان «non-actionable» طبقه‌بندی می‌شود و نیاز به clarification از کاربر دارد.

## 💡 نمونه‌های قبل/بعد
**اگر هدف افزودن به docs/ARCHITECTURE.md باشد**

_قبل:_
```
# ARCHITECTURE.md
(محتوای فعلی بدون بخش دستورالعمل مدل اجراکننده)
```

_بعد:_
```
# ARCHITECTURE.md

## دستورالعمل‌های مدل اجراکننده

### بررسی مستقل پیش از تغییر
- پیش از هر تغییر، ساختار repo، فایل‌های ذکرشده و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر موقعیت ذکرشده در پرامپت اشتباه است، بر اساس قضاوت خودت عمل کن.
- اگر AC مبهم بود، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

### کارهای طولانی
- خلاصه نکن — همه را کامل انجام بده.
- ترتیب کامیت‌ها: foundation → core → integration → tests
- در PR description یک checklist از همهٔ کامیت‌ها بنویس.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -r 'دستورالعمل‌های مدل اجراکننده' docs/`
- `ls .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null && echo 'exists' || echo 'not found'`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که اگر این تسک بدون clarification به مدل اجراکننده داده شود، مدل ممکن است تغییرات غیرضروری در فایل‌های کلیدی مثل backend/app/api/routes/system_prompts.py یا backend/app/services/oversight_strong_prompt.py ایجاد کند که توسط backend/app/main.py رجیستر شده‌اند و روی کل سیستم prompt اثر می‌گذارند. همچنین تغییر در docs/ARCHITECTURE.md که توسط هیچ فایلی import نمی‌شود ریسک کمتری دارد. **توصیه: این تسک را بدون clarification اجرا نکن.**

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 8: افزودن middleware مدیریت خطا و لاگینگ سیستماتیک به API Routes

**Scope:** این مرحله شامل پیاده‌سازی exception handler middleware در backend/app/core/، افزودن logging configuration با structlog/loguru، و بهبود مدیریت خطا در routes analysis.py و chat.py است. خارج از scope: تغییر در سایر routes (مانند github_import.py, model_profiles.py)، تغییر در frontend، یا تغییر در سرویس‌های عمیق (DeepAnalysisService). نکته حیاتی: middleware باید در backend/app/main.py ثبت شود و لاگینگ باید خطاهای runtime را به صورت ساختاریافته ثبت کند.
**Key terms:** backend/app/core/, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/main.py, FastAPI, structlog, loguru, Python logging, exception handler middleware, logging configuration

**بخش مربوط از متن کاربر:**
```
## 🎯 هدف
عدم مدیریت خطا و لاگینگ مناسب در API Routes

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن exception handler middleware و logging configuration
- `backend/app/api/routes/analysis.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد
- `backend/app/api/routes/chat.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, structlog/loguru, Python logging

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
مدیریت خطا و لاگینگ برای پایداری و عیب‌یابی پروژه ضروری است. بدون آن، خطاهای تولید (production) قابل ردیابی نیستند.

## 🔍 Context و وضعیت فعلی
با بررسی نمونه فایل‌های routes (مانند analysis.py, chat.py, projects.py)، مشخص نیست که مدیریت خطا (exception handling) و لاگینگ به صورت سیستماتیک پیاده‌سازی شده باشد. این موضوع باعث می‌شود خطاهای runtime به درستی ثبت نشوند و عیب‌یابی دشوار شود.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن middleware مدیریت خطا و لاگینگ سیستماتیک به API Routes

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — `exception_handler.py (فایل جدید)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. نیاز به ایجاد فایل جدید exception_handler.py با middleware سفارشی برای مدیریت خطاهای HTTP و عمومی.
- `backend/app/core/` — `logging_config.py (فایل جدید)` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. نیاز به ایجاد فایل جدید logging_config.py با تنظیمات structlog/loguru برای لاگینگ ساختاریافته.
- `backend/app/main.py:1-50` — `app (FastAPI instance)` — فایل اصلی که middlewareها در آن ثبت می‌شوند. نیاز به import کردن exception_handler و logging_config و ثبت middleware در app.
- `backend/app/api/routes/analysis.py` — `router (APIRouter)` — نمونه route که نیاز به بهبود مدیریت خطا دارد. باید try/except و logger به endpointهای اصلی اضافه شود.
- `backend/app/api/routes/chat.py` — `router (APIRouter)` — نمونه route که نیاز به بهبود مدیریت خطا دارد. باید try/except و logger به endpointهای اصلی اضافه شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده: fastapi. کتابخانه‌های مرتبط: structlog/loguru برای logging، Python logging استاندارد، FastAPI exception handlers. نیاز به نصب structlog یا loguru در requirements.txt (در حال حاضر موجود نیست).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/config.py` (سطر 1) — احتمالاً تنظیمات logging (مانند LOG_LEVEL, ENVIRONMENT) از config.py خوانده می‌شود. logging_config.py باید از این فایل برای تنظیمات محیطی استفاده کند.
- `backend/app/core/database.py` (سطر 1) — در صورت بروز خطاهای دیتابیس، exception handler باید بتواند آن‌ها را مدیریت کند. ممکن است نیاز به import کردن استثناهای دیتابیس در exception_handler.py باشد.
- `backend/app/services/ai_manager.py` (سطر 1) — این سرویس توسط analysis.py و chat.py استفاده می‌شود. خطاهای AI service باید توسط exception handler مدیریت شوند.
- `backend/app/services/ai_base.py` (سطر 1) — کلاس پایه برای سرویس‌های AI. استثناهای مرتبط با AI (مانند APIError, RateLimitError) باید در exception handler پشتیبانی شوند.
- `backend/app/services/analysis_progress_manager.py` (سطر 1) — مدیریت پیشرفت تحلیل که توسط analysis.py استفاده می‌شود. خطاهای مربوط به progress tracking باید لاگ شوند.

## 🌐 نقشهٔ وابستگی‌ها
این تسک به فایل‌های backend/app/core/ (برای exception handler و logging config)، backend/app/main.py (برای ثبت middleware)، و backend/app/api/routes/analysis.py و chat.py (برای بهبود مدیریت خطا) وابسته است. فایل‌های caller مانند backend/app/services/ai_manager.py و backend/app/services/ai_base.py تحت تأثیر قرار می‌گیرند زیرا خطاهای آن‌ها توسط middleware مدیریت خواهد شد. همچنین backend/app/core/config.py برای خواندن تنظیمات logging مورد نیاز است. تغییرات در routes analysis.py و chat.py باید با ساختار موجود (APIRouter, dependency injection) سازگار باشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن middleware مدیریت خطا و لاگینگ سیستماتیک به API Routes را دارد. این شامل پیاده‌سازی exception handler middleware در backend/app/core/، افزودن logging configuration با structlog/loguru، و بهبود مدیریت خطا در routes analysis.py و chat.py است. خارج از scope: تغییر در سایر routes (مانند github_import.py, model_profiles.py)، تغییر در frontend، یا تغییر در سرویس‌های عمیق (DeepAnalysisService). نکته حیاتی: middleware باید در backend/app/main.py ثبت شود و لاگینگ باید خطاهای runtime را به صورت ساختاریافته ثبت کند.

موقعیت دقیق در پروژه:
- backend/app/core/ — نیاز به افزودن exception handler middleware و logging configuration
- backend/app/api/routes/analysis.py — نمونه route که نیاز به بهبود مدیریت خطا دارد
- backend/app/api/routes/chat.py — نمونه route که نیاز به بهبود مدیریت خطا دارد

فایل‌های مرتبط:
- backend/app/main.py (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

کلیدواژه‌ها: backend/app/core/, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/main.py, FastAPI, structlog, loguru, Python logging, exception handler middleware, logging configuration

با بررسی نمونه فایل‌های routes (مانند analysis.py, chat.py, projects.py)، مشخص نیست که مدیریت خطا (exception handling) و لاگینگ به صورت سیستماتیک پیاده‌سازی شده باشد. این موضوع باعث می‌شود خطاهای runtime به درستی ثبت نشوند و عیب‌یابی دشوار شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/core/exception_handler.py باید وجود داشته باشد و شامل exception handler middleware برای HTTPException و Exception عمومی باشد.
- [ ] فایل backend/app/core/logging_config.py باید وجود داشته باشد و شامل تنظیمات structlog یا loguru برای لاگینگ ساختاریافته JSON باشد.
- [ ] middleware مدیریت خطا باید در backend/app/main.py ثبت شده باشد (app.add_exception_handler یا register_exception_handlers).
- [ ] endpointهای اصلی در backend/app/api/routes/analysis.py باید دارای try/except و logging برای خطاهای runtime باشند.
- [ ] endpointهای اصلی در backend/app/api/routes/chat.py باید دارای try/except و logging برای خطاهای runtime باشند.
- [ ] لاگ‌های runtime باید به صورت ساختاریافته (JSON) با timestamp, level, module, message ثبت شوند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل backend/app/core/exception_handler.py با exception handler middleware سفارشی برای FastAPI که:
   - تمام استثناهای HTTPException را به صورت ساختاریافته لاگ کند
   - استثناهای عمومی (500) را با stack trace کامل لاگ کند
   - پاسخ JSON یکسان با ساختار {'error': {'code': ..., 'message': ..., 'details': ...}} برگرداند

2. ایجاد فایل backend/app/core/logging_config.py با logging configuration مبتنی بر structlog یا loguru که:
   - لاگ‌های runtime را به صورت JSON ساختاریافته ثبت کند
   - شامل timestamp, level, module, line, message, trace_id باشد
   - برای محیط development و production تنظیمات جداگانه داشته باشد

3. بهبود مدیریت خطا در backend/app/api/routes/analysis.py:
   - افزودن try/except در endpointهای اصلی
   - استفاده از logger برای ثبت خطاها
   - برگرداندن پاسخ مناسب HTTP با پیام خطای معنادار

4. بهبود مدیریت خطا در backend/app/api/routes/chat.py:
   - افزودن try/except در endpointهای اصلی
   - استفاده از logger برای ثبت خطاها
   - برگرداندن پاسخ مناسب HTTP با پیام خطای معنادار

5. ثبت middleware در backend/app/main.py:
   - import کردن exception_handler از backend/app/core/exception_handler
   - اضافه کردن app.add_exception_handler(...) برای HTTPException و Exception عمومی
   - اطمینان از اجرای logging configuration در startup

## 💡 نمونه‌های قبل/بعد
**افزودن exception handler middleware به main.py**

_قبل:_
```
# backend/app/main.py (فعلی)
from fastapi import FastAPI

app = FastAPI()

# هیچ middleware مدیریت خطا ثبت نشده است
```

_بعد:_
```
# backend/app/main.py (پس از تغییر)
from fastapi import FastAPI
from app.core.exception_handler import register_exception_handlers
from app.core.logging_config import setup_logging

app = FastAPI()

# ثبت middleware مدیریت خطا
register_exception_handlers(app)

# راه‌اندازی logging در startup
@app.on_event("startup")
async def startup_event():
    setup_logging()
```

**بهبود مدیریت خطا در analysis.py**

_قبل:_
```
# backend/app/api/routes/analysis.py (فعلی - فرضی)
@router.post("/analyze")
async def analyze_project(request: AnalyzeRequest):
    result = await analysis_service.analyze(request)
    return result
```

_بعد:_
```
# backend/app/api/routes/analysis.py (پس از تغییر)
import logging
logger = logging.getLogger(__name__)

@router.post("/analyze")
async def analyze_project(request: AnalyzeRequest):
    try:
        result = await analysis_service.analyze(request)
        return result
    except ValueError as e:
        logger.warning(f"Invalid request: {e}", extra={"request_id": request.id})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True, extra={"request_id": request.id})
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k "test_exception_handler or test_logging" -v`
- `python -c "from app.core.exception_handler import register_exception_handlers; print('OK')"`
- `python -c "from app.core.logging_config import setup_logging; print('OK')"`
- `ruff check backend/app/core/exception_handler.py backend/app/core/logging_config.py`
- `python -m pytest backend/tests/test_runtime_verify_stage1.py -v`

## ⚠️ ریسک‌ها و موارد احتیاط
1. تغییر در backend/app/main.py ممکن است با middlewareهای موجود تداخل داشته باشد (در حال حاضر middlewareای ثبت نشده، اما باید بررسی شود). 2. افزودن logging به analysis.py و chat.py ممکن است performance را تحت تأثیر قرار دهد اگر logging همگام (synchronous) باشد — باید از logging ناهمگام استفاده شود. 3. اگر structlog یا loguru در requirements.txt نباشد، باید اضافه شود که ممکن است با dependencyهای موجود conflict داشته باشد. 4. exception handler ممکن است خطاهای خاص سرویس‌های AI (مانند APIError در ai_base.py) را به درستی مدیریت نکند اگر type hinting مناسب انجام نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 9: پیاده‌سازی مدیریت خطا و لاگینگ ساختاریافته در route handlers

**Scope:** این مرحله شامل افزودن middleware سراسری برای مدیریت خطاها (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru است. همچنین باید تمام route handlers موجود (analysis, chat, github_import, model_profiles) به try-except مجهز شوند و پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شود. لاگ‌ها باید شامل timestamp, level, message, traceback باشند. این مرحله شامل نوشتن تست جدید نیست اما نباید تست‌های موجود را بشکند.
**Key terms:** backend/app/main.py, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/api/routes/github_import.py, backend/app/api/routes/model_profiles.py, structlog, loguru, DeepAnalysisService

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] همه route handlers دارای try-except باشند
- [ ] خطاهای 500 به درستی لاگ شوند
- [ ] پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند
- [ ] لاگ‌ها شامل timestamp, level, message, traceback باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware برای مدیریت خطاهای سراسری (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru. همچنین اضافه کردن try-except در تمام route handlers و بازگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx).
```

## هدف
این مرحله شامل افزودن middleware سراسری برای مدیریت خطاها (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru است. همچنین باید تمام route handlers موجود (analysis, chat, github_import, model_profiles) به try-except مجهز شوند و پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شود. لاگ‌ها باید شامل timestamp, level, message, traceback باشند. این مرحله شامل نوشتن تست جدید نیست اما نباید تست‌های موجود را بشکند.

## بخش مربوط از متن کاربر
```
## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] همه route handlers دارای try-except باشند
- [ ] خطاهای 500 به درستی لاگ شوند
- [ ] پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند
- [ ] لاگ‌ها شامل timestamp, level, message, traceback باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware برای مدیریت خطاهای سراسری (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru. همچنین اضافه کردن try-except در تمام route handlers و بازگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx).
```

## معیار پذیرش
- پیاده‌سازی موفق این مرحله

---

# 🔹 مرحله 10: افزودن مدیریت خطا به endpointهای API

**Scope:** این بخش شامل افزودن try/except و logging به endpointهای موجود در فایل‌های routes است. فقط endpointهای مشخص‌شده در مثال (مانند get_projects) هدف هستند، نه کل پروژه. نکته حیاتی: باید از logger و HTTPException مطابق مثال استفاده شود و خطاها به صورت 500 برگردانده شوند.
**Key terms:** @router.get, service.get_all, logger.error, HTTPException, status_code=500

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**قبل: عدم مدیریت خطا**

_قبل:_
```
@router.get('/projects')
async def get_projects():
    return await service.get_all()
```

_بعد:_
```
@router.get('/projects')
async def get_projects():
    try:
        return await service.get_all()
    except Exception as e:
        logger.error('Failed to get projects', exc_info=e)
        raise HTTPException(status_code=500, detail='Internal server error')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

@router.get('/projects')
async def get_projects():
    return await service.get_all()
```

_بعد:_
```
@router.get('/projects')
async def get_projects():
    try:
        return await service.get_all()
    except Exception as e:
        logger.error('Failed to get projects', exc_info=e)
        raise HTTPException(status_code=500, detail='Internal server error')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
@router.get, service.get_all, logger.error, HTTPException, status_code=500
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن مدیریت خطا به endpointهای API در فایل‌های routes

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/projects.py:نامشخص — فایل deep-read نشده` — `get_projects` — بر اساس ساختار سطحی — توسط مجری تأیید شود. این فایل در ساختار پروژه موجود است و باید تابع get_projects با @router.get('/projects') در آن یافت شود.
- `backend/app/api/routes/analysis.py:نامشخص — فایل deep-read نشده` — `احتمالاً get_analysis یا مشابه` — بر اساس ساختار سطحی — توسط مجری تأیید شود. این فایل نیز در مسیر routes قرار دارد و احتمالاً endpointهای GET مشابه دارد.
- `backend/app/api/routes/chat.py:نامشخص — فایل deep-read نشده` — `احتمالاً get_chat یا مشابه` — بر اساس ساختار سطحی — توسط مجری تأیید شود. این فایل نیز در مسیر routes قرار دارد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده: fastapi. کتابخانه‌های مرتبط: fastapi (برای HTTPException و Router)، logging (برای logger)، python-json-logger یا structlog (احتمالاً در logging_utils.py).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/project_service.py` — این سرویس شامل تابع get_all است که توسط endpoint get_projects فراخوانی می‌شود. تغییر در مدیریت خطای endpoint روی نحوه فراخوانی این سرویس تأثیر می‌گذارد.
- `backend/app/core/logging_utils.py` — این فایل حاوی تنظیمات logger است که باید در endpointها import و استفاده شود. اطمینان از وجود logger مناسب در این فایل ضروری است.
- `backend/app/core/config.py` — این فایل حاوی پیکربندی کلی پروژه است. ممکن است تنظیمات logging سطح بالا در اینجا تعریف شده باشد.
- `backend/app/main.py` — این فایل نقطه ورود برنامه است و روترها را注册 می‌کند. تغییر در endpointها ممکن است نیاز به بررسی نحوه注册 روترها داشته باشد.

## 🌐 نقشهٔ وابستگی‌ها
این تغییرات مستقیماً روی فایل‌های backend/app/api/routes/projects.py، analysis.py، chat.py و سایر فایل‌های routes تأثیر می‌گذارد. این فایل‌ها از backend/app/services/project_service.py و سایر سرویس‌ها برای عملیات دیتابیس استفاده می‌کنند. همچنین از backend/app/core/logging_utils.py برای logging و از fastapi برای HTTPException استفاده می‌شود. فایل backend/app/main.py این روترها را import و注册 می‌کند. تغییر در مدیریت خطاها روی نحوه پاسخ‌دهی API به خطاهای غیرمنتظره تأثیر می‌گذارد و تجربه کاربری را بهبود می‌بخشد.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن مدیریت خطا (try/except و logging) به endpointهای مشخص‌شده در فایل‌های routes پروژه را دارد. این درخواست صرفاً شامل endpointهایی است که در مثال ذکر شده (مانند get_projects با @router.get('/projects') و service.get_all()) و مشابه آن‌ها در سایر فایل‌های routes می‌شود. نکته حیاتی: باید از logger و HTTPException مطابق مثال استفاده شود و خطاها به صورت status_code=500 برگردانده شوند. کاربر تأکید کرده که فقط endpointهای مشخص‌شده هدف هستند، نه کل پروژه. کلیدواژه‌های اصلی: @router.get, service.get_all, logger.error, HTTPException, status_code=500. با توجه به deep context موجود، فایل‌های routes در مسیر backend/app/api/routes/ قرار دارند و شامل فایل‌های متعددی مانند projects.py، analysis.py، chat.py، config.py و غیره می‌شوند. در ساختار پروژه، فایل backend/app/api/routes/projects.py به عنوان یکی از فایل‌های اصلی routes شناسایی شده است. همچنین فایل backend/app/services/project_service.py به عنوان سرویس مرتبط با get_all وجود دارد. فایل backend/app/core/logging_utils.py برای تنظیمات logging و backend/app/core/config.py برای پیکربندی کلی پروژه موجود است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تابع get_projects در backend/app/api/routes/projects.py باید دارای بلوک try/except باشد و خطاها را با logger.error و HTTPException(status_code=500) مدیریت کند.
- [ ] تمامی endpointهای GET در فایل‌های routes (حداقل projects.py، analysis.py، chat.py) باید دارای مدیریت خطای مشابه باشند.
- [ ] import مربوط به logger و HTTPException در فایل‌های routes وجود داشته باشد.
- [ ] پیام خطا در logger.error مختص هر endpoint باشد (مثلاً 'Failed to get projects' برای projects و 'Failed to get analysis' برای analysis).
- [ ] commit یا PR جدید با پیام واضح مانند 'feat: add error handling to API endpoints' ایجاد شده باشد.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. باز کردن فایل backend/app/api/routes/projects.py و یافتن تابع get_projects (یا async def get_projects) که از @router.get('/projects') استفاده می‌کند.
2. افزودن try/except به بدنه تابع: کل محتوای فعلی تابع در بلوک try قرار گیرد.
3. در بخش except Exception as e: افزودن logger.error('Failed to get projects', exc_info=e) و raise HTTPException(status_code=500, detail='Internal server error').
4. اطمینان از import بودن logger از backend/app/core/logging_utils و HTTPException از fastapi.
5. تکرار همین الگو برای سایر endpointهای مشابه در فایل‌های routes که از @router.get با الگوی مشابه استفاده می‌کنند (مانند analysis.py، chat.py، config.py).
6. برای هر endpoint، پیام خطای مناسب در logger.error بنویسید (مثلاً 'Failed to get analysis results').
7. commit یا PR جدید با پیام واضح مانند 'feat: add error handling to API endpoints' ایجاد شود.

## 💡 نمونه‌های قبل/بعد
**افزودن try/except به get_projects**

_قبل:_
```
@router.get('/projects')
async def get_projects():
    return await service.get_all()
```

_بعد:_
```
@router.get('/projects')
async def get_projects():
    try:
        return await service.get_all()
    except Exception as e:
        logger.error('Failed to get projects', exc_info=e)
        raise HTTPException(status_code=500, detail='Internal server error')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k "test_projects or test_analysis" -v`
- `ruff check backend/app/api/routes/`
- `black --check backend/app/api/routes/`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در فایل‌های routes ممکن است روی endpointهایی که توسط frontend یا سایر سرویس‌ها فراخوانی می‌شوند تأثیر بگذارد. اگر try/except به درستی پیاده‌سازی نشود، ممکن است خطاهای واقعی پنهان شوند و دیباگ کردن مشکل‌تر شود. همچنین تغییر در نحوه پاسخ‌دهی به خطاها (از response مستقیم به HTTPException) ممکن است روی کلاینت‌هایی که به فرمت خاصی از خطا وابسته هستند تأثیر بگذارد. فایل‌های routes توسط frontend (احتمالاً در مسیر frontend/) و همچنین توسط ابزارهای تست فراخوانی می‌شوند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 11: پیاده‌سازی Rate Limiting و Input Validation برای API Endpoints

**Scope:** این مرحله شامل پیاده‌سازی Rate Limiting برای تمام AI endpoints (chat و analysis) با بازگشت پاسخ 429 در صورت تجاوز از محدودیت، و همچنین پیاده‌سازی Input Validation با Pydantic برای تمام endpoints است. محدودیت‌ها باید از طریق متغیرهای محیطی قابل تنظیم باشند. فایل‌های اصلی backend/app/api/routes/analysis.py، backend/app/api/routes/chat.py و backend/app/core/ هستند. تست endpoints برای اطمینان از عدم تغییر رفتار API ضروری است.
— [merged] این مرحله شامل افزودن rate limiting برای تمام AI endpoints با استفاده از slowapi یا middleware سفارشی، و پیاده‌سازی input validation با Pydantic models است. محدودیت‌ها باید از طریق متغیرهای محیطی قابل تنظیم باشند. پس از تجاوز از محدودیت، پاسخ 429 برگردانده شود. تمام تست‌ها، linter و type-check باید پاس شوند. فایل‌های مرتبط شامل backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/config.py, backend/app/main.py هستند.
**Key terms:** متغیرهای محیطی, AI endpoints, backend/app/core/config.py, middleware سفارشی, backend/app/main.py, os.getenv, Rate limiting, BaseModel, 429 Too Many Requests, RATE_LIMIT, slowapi, MAX_REQUESTS, rate_limit, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/, Input validation, /api/chat, Field, pydantic, limiter, RateLimiter, Pydantic, environ.get, validator

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در مدیریت خطا ممکن است باعث تغییر رفتار API شود. نیاز به تست کامل endpoints.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 8
  id: 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd
  عنوان اصلی: نبود Rate Limiting و Input Validation در API Endpoints
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/

📋 acceptance_criteria کامل:
  - Rate limiting برای تمام AI endpoints فعال باشد [verify_method=static] [verify_plan={"grep_patterns": ["RateLimiter", "rate_limit", "limiter"], "files_hint": ["backend/app/core/", "backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - پس از تجاوز از محدودیت، پاسخ 429 Too Many Requests برگردانده شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/chat", "headers": null, "json_body": {"message": "test"}, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - Input validation با Pydantic برای تمام endpoints پیاده‌سازی شده باشد [verify_method=static] [verify_plan={"grep_patterns": ["BaseModel", "Field", "validator", "pydantic"], "files_hint": ["backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - محدودیت‌ها قابل تنظیم از طریق متغیرهای محیطی باشند [verify_method=static] [verify_plan={"grep_patterns": ["os.getenv", "environ.get", "RATE_LIMIT", "MAX_REQUESTS"], "files_hint": ["backend/app/core/"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی Rate Limiting و Input Validation در AI Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-44` — `AnalysisRequest` — کلاس AnalysisRequest فاقد Field validators است — project_id و project_path بدون محدودیت طول، models بدون max_items، و هیچ validator برای path traversal وجود ندارد. باید با Field و validator تقویت شود.
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  
  
  class AnalysisResponse(BaseModel):
      """پاسخ تحلیل"""
      success: bool
      report_id: Optional[str] = None
      message: str
      report: Optional[AnalysisReportSchema] = None
  ```
- `backend/app/api/routes/analysis.py:46-80` — `run_analysis` — endpoint اصلی analysis که باید rate limiting decorator دریافت کند. هیچ @limiter.limit یا decorator مشابهی وجود ندارد. Request object هم از AnalysisRequest بدون validation می‌آید.
  ```python
  @router.post("/run", response_model=AnalysisResponse)
  async def run_analysis(
      request: AnalysisRequest,
      background_tasks: BackgroundTasks
  ):
      """
      اجرای تحلیل جدید
  
      تحلیل کامل پروژه توسط مدل‌های انتخابی
      """
      try:
          analyzer = get_project_analyzer()
          analyzer.initialize()
  ```
- `backend/app/api/routes/analysis.py:83-100` — `run_analysis_stream` — endpoint streaming analysis — این endpoint به دلیل ماهیت SSE و مصرف بالای منابع AI، نیاز به rate limiting سخت‌گیرانه‌تری دارد. فاقد هرگونه محدودیت است.
  ```python
  @router.post("/run-stream")
  async def run_analysis_stream(request: AnalysisRequest):
      """
      اجرای تحلیل با استریم پیشرفت (Server-Sent Events)
  
      این endpoint پیشرفت تحلیل را به صورت Real-time ارسال می‌کند:
      - کدام مدل در حال کار است
      - کدام فایل در حال تحلیل است
      - درصد پیشرفت
      - زمان سپری شده
      """
      import os
      from ...services.ai_manager import get_ai_manager
      from ...services.deep_analysis_service import DeepAnalysisService
  ```
- `backend/app/core/config.py` — `Settings` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. باید متغیرهای RATE_LIMIT_CHAT، RATE_LIMIT_ANALYSIS، RATE_LIMIT_DEFAULT و MAX_REQUESTS با os.getenv یا pydantic-settings اضافه شوند.
- `backend/app/main.py` — `app` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. نقطه ورود FastAPI که باید Limiter instance، app.state.limiter، و exception handler برای RateLimitExceeded (HTTP 429) اینجا register شوند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js 14. کتابخانه‌های مرتبط: `pydantic>=2.5.0` (در requirements.txt موجود — برای Field و validator)، `fastapi>=0.109.0` (در requirements.txt موجود — برای Request object در rate limiting)، `slowapi>=0.1.9` (باید اضافه شود — wrapper روی limits library برای FastAPI/Starlette). جایگزین: middleware سفارشی با `starlette.middleware.base.BaseHTTPMiddleware`. در Pydantic v2 (که در requirements.txt است)، `@validator` به `@field_validator` تغییر نام داده — باید از syntax جدید استفاده شود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/chat.py` (سطر 1) — endpoint اصلی /api/chat که در verify_plan تسک اصلی به‌صراحت ذکر شده — POST /api/chat باید پس از تجاوز از محدودیت 429 برگرداند. این فایل هم نیاز به rate limiting decorator و تقویت Input Validation دارد.
- `backend/app/main.py` (سطر 1) — نقطه ورود FastAPI — Limiter باید اینجا به app.state اضافه شود و exception handler برای RateLimitExceeded register شود. این فایل توسط oversight_service و project_service import می‌شود.
- `backend/requirements.txt` (سطر 1) — باید slowapi>=0.1.9 به این فایل اضافه شود تا dependency در محیط production نیز نصب شود.
- `backend/app/api/routes/model_profiles.py` (سطر 50) — این route هم AI endpoints دارد و از get_model_profiler استفاده می‌کند — باید rate limiting default روی آن اعمال شود. در خط ۵۰ router با prefix /api/models تعریف شده.
- `backend/app/core/database.py` (سطر 1) — توسط ۱۶ فایل import می‌شود از جمله analysis.py و chat.py — تغییر در config.py که database settings را هم نگه می‌دارد ممکن است روی این فایل اثر بگذارد.
- `backend/app/api/routes/orchestrator.py` (سطر 1) — از ai_manager استفاده می‌کند و احتمالاً AI endpoints دارد که باید rate limiting روی آن‌ها هم اعمال شود.

## 🌐 نقشهٔ وابستگی‌ها
تغییرات این تسک روی چندین لایه از پروژه اثر می‌گذارد:

1. **backend/app/main.py** — مرکزی‌ترین فایل: Limiter باید اینجا instantiate شود و به app.state اضافه شود. این فایل توسط `backend/app/services/project_service.py`، `backend/app/services/oversight_service.py` (که ۷ فایل آن را import می‌کنند) و سایر services در startup استفاده می‌شود.

2. **backend/app/core/config.py** — تنظیمات جدید `RATE_LIMIT_CHAT`، `RATE_LIMIT_ANALYSIS`، `RATE_LIMIT_DEFAULT` و `MAX_REQUESTS` باید اینجا اضافه شوند. این فایل توسط تمام services و routes استفاده می‌شود.

3. **backend/app/api/routes/analysis.py** — دو endpoint اصلی `run_analysis` و `run_analysis_stream` که از `get_ai_manager` (import در خط ۹۵) و `DeepAnalysisService` استفاده می‌کنند باید decorator دریافت کنند.

4. **backend/app/api/routes/chat.py** — endpoint `/api/chat` که در verify_plan تسک اصلی به‌صراحت ذکر شده.

5. **backend/requirements.txt** — باید `slowapi>=0.1.9` اضافه شود تا در Docker build و Railway deploy نصب شود.

6. **backend/app/api/routes/model_profiles.py** — router با prefix `/api/models` (خط ۵۰) که AI profiling endpoints دارد.

اگر از middleware سفارشی به‌جای slowapi استفاده شود، تمام route files باید بررسی شوند چون `backend/app/core/database.py` توسط ۱۶ فایل import می‌شود و تغییر در config ممکن است cascade effect داشته باشد.

## 🔍 Context و وضعیت فعلی
این تسک شامل دو بخش اصلی است که باید به‌صورت هم‌زمان پیاده‌سازی شوند:

**بخش ۱ — Rate Limiting:**
پیاده‌سازی Rate Limiting برای تمام AI endpoints (chat و analysis) با بازگشت پاسخ `429 Too Many Requests` در صورت تجاوز از محدودیت. محدودیت‌ها باید از طریق متغیرهای محیطی (`RATE_LIMIT`, `MAX_REQUESTS`) قابل تنظیم باشند. رویکرد پیشنهادی استفاده از `slowapi` یا middleware سفارشی است. endpoint اصلی برای تست: `POST /api/chat`.

**بخش ۲ — Input Validation:**
پیاده‌سازی Input Validation با Pydantic models (`BaseModel`, `Field`, `validator`) برای تمام endpoints. در حال حاضر در `backend/app/api/routes/analysis.py` کلاس‌های `AnalysisRequest` (خط ۳۰) و `AnalysisResponse` (خط ۳۸) وجود دارند اما فاقد `Field` validators با محدودیت‌های دقیق هستند — مثلاً `project_id: str` بدون حداقل/حداکثر طول، `project_path: str` بدون validation مسیر.

**فایل‌های اصلی درگیر:**
- `backend/app/api/routes/analysis.py` — endpoint های `/analysis/run` و `/analysis/run-stream`
- `backend/app/api/routes/chat.py` — endpoint های chat که AI را فراخوانی می‌کنند
- `backend/app/core/config.py` — تنظیمات محیطی پروژه
- `backend/app/main.py` — نقطه ورود FastAPI که middleware ها باید اینجا register شوند

**شواهد در کد:**
در `analysis.py` خط ۳۰-۳۵، کلاس `AnalysisRequest` فاقد `Field` validators است:
```python
class AnalysisRequest(BaseModel):
    project_id: str
    project_path: str
    models: List[str] = []
    roadmap_path: Optional[str] = None
```
هیچ محدودیتی روی طول `project_id`، اعتبارسنجی `project_path`، یا حداکثر تعداد `models` وجود ندارد. همچنین هیچ decorator یا middleware ای برای rate limiting در هیچ‌کدام از route های موجود دیده نمی‌شود.

**verify criteria از تسک اصلی (id: 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd):**
- `grep_patterns`: `["RateLimiter", "rate_limit", "limiter"]` در `backend/app/core/` و route files
- `grep_patterns`: `["os.getenv", "environ.get", "RATE_LIMIT", "MAX_REQUESTS"]` در `backend/app/core/`
- API test: `POST /api/chat` با body `{"message": "test"}` باید پس از تجاوز از محدودیت `429` برگرداند
- `grep_patterns`: `["BaseModel", "Field", "validator", "pydantic"]` در route files

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] Rate limiting برای endpoint /analysis/run فعال باشد — decorator @limiter.limit در تابع run_analysis در analysis.py وجود داشته باشد
- [ ] پس از تجاوز از محدودیت، endpoint POST /api/chat پاسخ 429 Too Many Requests برگرداند
- [ ] Input validation با Pydantic Field در AnalysisRequest پیاده‌سازی شده باشد — min_length، max_length و field_validator برای project_path وجود داشته باشد
- [ ] متغیرهای محیطی RATE_LIMIT_CHAT، RATE_LIMIT_ANALYSIS و MAX_REQUESTS در config.py تعریف شده و با os.getenv یا pydantic-settings خوانده شوند
- [ ] slowapi در requirements.txt اضافه شده باشد
- [ ] Limiter در main.py به app.state اضافه شده و exception handler برای RateLimitExceeded register شده باشد
- [ ] ارسال project_path با مقدار '../../../etc/passwd' به endpoint /analysis/run باید پاسخ 422 Unprocessable Entity برگرداند
- [ ] تمام تست‌های موجود در backend/tests/ پس از تغییرات همچنان pass شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. **مرحله ۱ — افزودن `slowapi` به dependencies:**
در `backend/requirements.txt` اضافه کن:
```
slowapi>=0.1.9
```

**مرحله ۲ — تعریف تنظیمات Rate Limit در `backend/app/core/config.py`:**
متغیرهای محیطی زیر را اضافه کن:
- `RATE_LIMIT_CHAT`: محدودیت برای chat endpoints (پیش‌فرض: `"10/minute"`)
- `RATE_LIMIT_ANALYSIS`: محدودیت برای analysis endpoints (پیش‌فرض: `"5/minute"`)
- `RATE_LIMIT_DEFAULT`: محدودیت پیش‌فرض (پیش‌فرض: `"30/minute"`)
این مقادیر با `os.getenv` یا از طریق `pydantic-settings` خوانده شوند.

**مرحله ۳ — راه‌اندازی Limiter در `backend/app/main.py`:**
یک `Limiter` instance از `slowapi` بساز و به app اضافه کن:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**مرحله ۴ — اعمال decorator در `backend/app/api/routes/chat.py`:**
به تمام endpoint های AI decorator اضافه کن:
```python
@limiter.limit(settings.RATE_LIMIT_CHAT)
```

**مرحله ۵ — اعمال decorator در `backend/app/api/routes/analysis.py`:**
به `run_analysis` (خط ۴۶) و `run_analysis_stream` (خط ۸۳) decorator اضافه کن:
```python
@limiter.limit(settings.RATE_LIMIT_ANALYSIS)
```

**مرحله ۶ — تقویت Input Validation در `backend/app/api/routes/analysis.py`:**
کلاس `AnalysisRequest` (خط ۳۰-۳۵) را با `Field` validators تقویت کن:
```python
from pydantic import BaseModel, Field, validator
class AnalysisRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=100)
    project_path: str = Field(..., min_length=1, max_length=500)
    models: List[str] = Field(default=[], max_items=10)
    roadmap_path: Optional[str] = Field(None, max_length=500)
    @validator('project_path')
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError('path traversal not allowed')
        return v
```

**مرحله ۷ — تقویت Input Validation در `backend/app/api/routes/chat.py`:**
مدل‌های Pydantic موجود را با `Field` validators تقویت کن.

**مرحله ۸ — تست و verify:**
اجرای `pytest backend/tests/` و تست دستی endpoint `/api/chat` برای اطمینان از بازگشت `429`.

## 💡 نمونه‌های قبل/بعد
**AnalysisRequest — قبل از Input Validation**

_قبل:_
```
class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None
```

_بعد:_
```
from pydantic import BaseModel, Field, field_validator

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str = Field(..., min_length=1, max_length=100, description="شناسه پروژه")
    project_path: str = Field(..., min_length=1, max_length=500, description="مسیر پروژه")
    models: List[str] = Field(default=[], max_length=10, description="مدل‌های انتخابی")
    roadmap_path: Optional[str] = Field(None, max_length=500)

    @field_validator('project_path')
    @classmethod
    def validate_no_path_traversal(cls, v: str) -> str:
        if '..' in v or v.startswith('/'):
            raise ValueError('path traversal or absolute path not allowed')
        return v

    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        import re
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('project_id must be alphanumeric with _ and -')
        return v
```

**run_analysis endpoint — قبل و بعد از Rate Limiting**

_قبل:_
```
@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    try:
        analyzer = get_project_analyzer()
        analyzer.initialize()
```

_بعد:_
```
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

# در main.py:
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter

@router.post("/run", response_model=AnalysisResponse)
@limiter.limit(settings.RATE_LIMIT_ANALYSIS)  # e.g. "5/minute" از env var
async def run_analysis(
    request: Request,  # باید Request اضافه شود برای slowapi
    body: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    try:
        analyzer = get_project_analyzer()
        analyzer.initialize()
```

**config.py — اضافه کردن متغیرهای محیطی Rate Limit**

_قبل:_
```
# تنظیمات موجود در config.py (محتوا deep-read نشده)
```

_بعد:_
```
import os

# Rate Limiting Settings
RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "10/minute")
RATE_LIMIT_ANALYSIS: str = os.getenv("RATE_LIMIT_ANALYSIS", "5/minute")
RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "30/minute")
MAX_REQUESTS_PER_HOUR: int = int(os.getenv("MAX_REQUESTS", "100"))
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pip install slowapi>=0.1.9`
- `pytest backend/tests/ -v --tb=short`
- `pytest backend/tests/test_runtime_verify_integration.py -v`
- `python -m ruff check backend/app/api/routes/analysis.py backend/app/api/routes/chat.py backend/app/core/config.py backend/app/main.py`
- `python -m mypy backend/app/api/routes/analysis.py --ignore-missing-imports`
- `curl -X POST http://localhost:8000/api/analysis/run -H 'Content-Type: application/json' -d '{"project_id": "test", "project_path": "../../../etc"}' | python -m json.tool`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **تغییر signature تابع run_analysis و run_analysis_stream در analysis.py (خط ۴۷ و ۸۴):** slowapi نیاز دارد `Request` object از fastapi به‌عنوان اولین پارامتر تابع باشد. این تغییر signature ممکن است با `BackgroundTasks` که در `run_analysis` (خط ۴۹) وجود دارد conflict ایجاد کند — باید ترتیب پارامترها دقیق باشد.

۲. **Pydantic v2 breaking change:** در requirements.txt نسخه `pydantic>=2.5.0` است. در Pydantic v2، `@validator` deprecated شده و باید از `@field_validator` استفاده شود. استفاده از `@validator` قدیمی باعث warning یا خطا می‌شود.

۳. **backend/app/main.py به‌عنوان hub مرکزی:** این فایل توسط `oversight_service.py` (که ۷ فایل آن را import می‌کنند) و `project_service.py` (که ۴ فایل آن را import می‌کنند) استفاده می‌شود. تغییر در startup sequence یا اضافه کردن middleware اشتباه می‌تواند کل app را break کند.

۴. **SSE endpoint run_analysis_stream (خط ۸۳):** این endpoint از `StreamingResponse` استفاده می‌کند. rate limiting روی streaming endpoints ممکن است رفتار غیرمنتظره داشته باشد — اگر request در وسط stream قطع شود، client ممکن است state نامعتبر داشته باشد.

۵. **backend/.env.example:** باید متغیرهای جدید `RATE_LIMIT_CHAT`، `RATE_LIMIT_ANALYSIS` و `MAX_REQUESTS` به این فایل اضافه شوند وگرنه در deploy جدید (Railway طبق `backend/railway.json`) این متغیرها undefined خواهند بود و fallback default استفاده می‌شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 12: افزودن Rate Limiting و Input Validation به API Endpoints

**Scope:** این مرحله شامل افزودن middleware rate limiting با استفاده از slowapi به برنامه FastAPI، اعمال rate limiting به endpoints حساس (chat و analysis)، و اطمینان از وجود validation مناسب Pydantic برای ورودی‌های این endpoints است. خارج از scope این مرحله: پیاده‌سازی rate limiting برای سایر endpoints، تست‌های امنیتی، یا تغییرات در frontend.
**Key terms:** backend/app/core/, backend/app/api/routes/chat.py, backend/app/api/routes/analysis.py, backend/app/main.py, FastAPI, slowapi, Pydantic, Rate Limiting, Input Validation

**بخش مربوط از متن کاربر:**
```
## 🎯 هدف
نبود Rate Limiting و Input Validation در API Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن rate limiter middleware
- `backend/app/api/routes/chat.py` — Endpoint حساس که نیاز به rate limiting دارد
- `backend/app/api/routes/analysis.py` — Endpoint حساس که نیاز به rate limiting دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, slowapi, Pydantic

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
Rate limiting برای محافظت در برابر سوءاستفاده و کنترل هزینه‌ها ضروری است. Input validation برای جلوگیری از حملات injection حیاتی است.

## 🔍 Context و وضعیت فعلی
با توجه به وجود endpoints برای AI calls (chat, analysis, debate) که هزینه‌بر هستند، نبود rate limiting می‌تواند منجر به حملات DoS و هزینه‌های غیرمنتظره شود. همچنین نبود input validation مناسب می‌تواند باعث injection attacks شود.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن Rate Limiting با slowapi و Input Validation به endpoints حساس chat و analysis

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-35` — `AnalysisRequest` — مدل Pydantic ورودی برای هر دو endpoint /run و /run-stream. فاقد هرگونه validation روی project_path (خطر path traversal) و project_id (خطر injection). باید field_validator اضافه شود.
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:46-50` — `run_analysis` — Endpoint پرهزینه که مستقیماً AI را فراخوانی می‌کند. فاقد rate limiting است. باید @limiter.limit و پارامتر Request اضافه شود.
  ```python
  @router.post("/run", response_model=AnalysisResponse)
  async def run_analysis(
      request: AnalysisRequest,
      background_tasks: BackgroundTasks
  ):
  ```
- `backend/app/api/routes/analysis.py:83-84` — `run_analysis_stream` — Endpoint streaming که DeepAnalysisService را اجرا می‌کند و بسیار پرهزینه‌تر از /run است. باید rate limit سخت‌تری (5/minute) داشته باشد.
  ```python
  @router.post("/run-stream")
  async def run_analysis_stream(request: AnalysisRequest):
  ```
- `backend/app/main.py:1-1` — `app` — فایل اصلی FastAPI که middlewareها در آن ثبت می‌شوند. SlowAPIMiddleware و exception handler برای RateLimitExceeded باید اینجا اضافه شوند. این فایل deep-read نشده — مجری باید محل دقیق app = FastAPI() را تأیید کند.
- `backend/app/api/routes/chat.py:1-1` — `router` — Endpoint حساس chat که AI calls انجام می‌دهد. این فایل deep-read نشده — مجری باید endpointها را شناسایی و @limiter.limit اعمال کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (backend) + Next.js 14 (frontend). کتابخانه‌های مرتبط: slowapi>=0.1.9 (rate limiting برای FastAPI، مبتنی بر limits)، Pydantic v2 (که در requirements.txt موجود است: pydantic>=2.5.0) با syntax جدید @field_validator. در Pydantic v2 از model_validator و field_validator به جای validator استفاده می‌شود. slowapi با FastAPI از طریق SlowAPIMiddleware و app.state.limiter یکپارچه می‌شود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/requirements.txt` (سطر 1) — باید slowapi>=0.1.9 و limits>=3.6.0 به این فایل اضافه شود تا dependency در محیط نصب شود
- `backend/app/api/routes/orchestrator.py` (سطر 1) — این route نیز از ai_manager استفاده می‌کند (طبق import map) و ممکن است endpointهای AI-heavy داشته باشد که در آینده نیاز به rate limiting داشته باشند — باید بررسی شود
- `backend/app/api/routes/oversight.py` (سطر 1) — از ai_manager import می‌کند و endpointهای AI-heavy دارد. در scope فعلی نیست اما باید مستند شود که rate limiting روی آن اعمال نشده
- `backend/app/services/deep_analysis_service.py` (سطر 1) — توسط run_analysis_stream در analysis.py فراخوانی می‌شود. اگر validation در AnalysisRequest ضعیف باشد، project_path مستقیماً به os.walk در این سرویس می‌رسد (خطر path traversal)
- `backend/app/core/config.py` (سطر 1) — محل مناسب برای تعریف تنظیمات rate limit (مثل RATE_LIMIT_PER_MINUTE) به عنوان environment variable تا در production قابل تنظیم باشد

## 🌐 نقشهٔ وابستگی‌ها
تغییرات در `backend/app/main.py` (ثبت SlowAPIMiddleware) روی کل برنامه تأثیر می‌گذارد چون middleware به همه requestها اعمال می‌شود. تغییر signature توابع `run_analysis` و `run_analysis_stream` در `backend/app/api/routes/analysis.py` برای اضافه کردن `request: Request` باید با دقت انجام شود چون این توابع توسط frontend در `frontend/src/app/analysis/page.tsx` (خط ۱۹۰ — fetch به /api/analysis/run-stream) فراخوانی می‌شوند. تقویت `AnalysisRequest` validator روی هر کلاینتی که این endpoint را صدا می‌زند تأثیر می‌گذارد. `backend/app/services/deep_analysis_service.py` که توسط `run_analysis_stream` فراخوانی می‌شود، مستقیماً `project_path` را در `os.walk` استفاده می‌کند (خطوط ۱۶۰-۱۸۰ analysis.py) — validation در لایه Pydantic این خطر را کاهش می‌دهد. `backend/app/core/database.py` که توسط ۱۵ فایل import می‌شود تحت تأثیر مستقیم نیست.

## 🔍 Context و وضعیت فعلی
پروژه در حال حاضر هیچ‌گونه Rate Limiting روی endpoints حساس AI ندارد. با توجه به وجود endpointهای پرهزینه مانند `/api/analysis/run-stream` (در `backend/app/api/routes/analysis.py`) و مسیرهای chat (در `backend/app/api/routes/chat.py`)، نبود rate limiting می‌تواند منجر به حملات DoS، مصرف بی‌رویه توکن‌های AI، و هزینه‌های غیرمنتظره شود. همچنین نبود input validation مناسب Pydantic روی فیلدهایی مثل `project_path` و `project_id` در `AnalysisRequest` (خطوط ۳۰-۳۵ فایل analysis.py) می‌تواند باعث injection attacks شود.

محدوده این تسک:
1. نصب و پیکربندی `slowapi` به عنوان middleware در `backend/app/main.py`
2. اعمال rate limiting به endpoint `/api/analysis/run-stream` و `/api/analysis/run` در `backend/app/api/routes/analysis.py`
3. اعمال rate limiting به endpointهای `backend/app/api/routes/chat.py`
4. تقویت Pydantic validation در `AnalysisRequest` (خطوط ۳۰-۳۵ analysis.py) با اضافه کردن field validators برای `project_path` (جلوگیری از path traversal) و `project_id` (الگوی مجاز)
5. افزودن `slowapi` به `backend/requirements.txt`

خارج از scope: rate limiting برای سایر endpoints، تست‌های امنیتی، یا تغییرات در frontend.

کلیدواژه‌ها: backend/app/core/, backend/app/api/routes/chat.py, backend/app/api/routes/analysis.py, backend/app/main.py, FastAPI, slowapi, Pydantic, Rate Limiting, Input Validation

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] endpoint POST /api/analysis/run-stream باید بعد از ۵ درخواست در یک دقیقه از یک IP، پاسخ HTTP 429 Too Many Requests برگرداند
- [ ] endpoint POST /api/analysis/run باید بعد از ۱۰ درخواست در یک دقیقه از یک IP، پاسخ HTTP 429 برگرداند
- [ ] AnalysisRequest با project_path حاوی '..' باید HTTP 422 Unprocessable Entity برگرداند
- [ ] AnalysisRequest با project_id حاوی کاراکترهای غیرمجاز (مثل ';DROP TABLE') باید HTTP 422 برگرداند
- [ ] کلاس Limiter از slowapi باید در فایل analysis.py یا یک فایل core مشترک import و استفاده شده باشد
- [ ] SlowAPIMiddleware باید در backend/app/main.py ثبت شده باشد
- [ ] slowapi باید در backend/requirements.txt موجود باشد
- [ ] field_validator برای project_path و project_id باید در AnalysisRequest تعریف شده باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **نصب slowapi**: افزودن `slowapi>=0.1.9` و `limits>=3.6.0` به `backend/requirements.txt`.

2. **پیکربندی Limiter در `backend/app/core/config.py` یا فایل جدید `backend/app/core/rate_limiter.py`**: ساخت instance مشترک از `slowapi.Limiter` با `key_func=get_remote_address`.

3. **ثبت middleware در `backend/app/main.py`**: افزودن `SlowAPIMiddleware` به app و تنظیم `app.state.limiter`، همچنین افزودن exception handler برای `RateLimitExceeded`.

4. **اعمال decorator در `backend/app/api/routes/analysis.py`**:
   - روی `run_analysis` (خط ۴۶): `@limiter.limit("10/minute")`
   - روی `run_analysis_stream` (خط ۸۳): `@limiter.limit("5/minute")` (چون streaming هزینه‌برتر است)
   - اضافه کردن `request: Request` به signature هر دو تابع

5. **اعمال decorator در `backend/app/api/routes/chat.py`**: بررسی endpointها و اعمال `@limiter.limit("20/minute")` روی هر endpoint.

6. **تقویت Pydantic validation در `AnalysisRequest` (خطوط ۳۰-۳۵ analysis.py)**:
   - افزودن `@field_validator('project_path')` برای جلوگیری از `..` و path traversal
   - افزودن `@field_validator('project_id')` با regex `^[a-zA-Z0-9_-]+$`
   - محدود کردن طول `project_path` با `max_length=500`
   - محدود کردن تعداد مدل‌ها در `models` با `max_items=10`

## 💡 نمونه‌های قبل/بعد
**تقویت AnalysisRequest با Pydantic v2 validators**

_قبل:_
```
class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None
```

_بعد:_
```
from pydantic import BaseModel, field_validator
import re

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []
    roadmap_path: Optional[str] = None

    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_\-]{1,100}$', v):
            raise ValueError('project_id باید فقط شامل حروف، اعداد، _ و - باشد')
        return v

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        if '..' in v or v.startswith('/'):
            raise ValueError('مسیر پروژه نامعتبر است')
        if len(v) > 500:
            raise ValueError('مسیر پروژه بیش از حد طولانی است')
        return v

    @field_validator('models')
    @classmethod
    def validate_models(cls, v: List[str]) -> List[str]:
        if len(v) > 10:
            raise ValueError('حداکثر ۱۰ مدل مجاز است')
        return v
```

**اعمال rate limiting روی run_analysis_stream**

_قبل:_
```
@router.post("/run-stream")
async def run_analysis_stream(request: AnalysisRequest):
    """
    اجرای تحلیل با استریم پیشرفت (Server-Sent Events)
    """
```

_بعد:_
```
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.post("/run-stream")
@limiter.limit("5/minute")
async def run_analysis_stream(request: Request, body: AnalysisRequest):
    """
    اجرای تحلیل با استریم پیشرفت (Server-Sent Events)
    محدودیت: ۵ درخواست در دقیقه برای جلوگیری از سوءاستفاده
    """
```

**ثبت SlowAPIMiddleware در main.py**

_قبل:_
```
# فرض: app = FastAPI(...) بدون middleware rate limiting
```

_بعد:_
```
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pip install slowapi limits`
- `pytest backend/tests/ -v -k 'rate_limit or analysis' --tb=short`
- `python -c "from slowapi import Limiter; print('slowapi OK')"`
- `cd backend && python -m pytest tests/ -v --tb=short`
- `curl -X POST http://localhost:8000/api/analysis/run -H 'Content-Type: application/json' -d '{"project_id":"test;bad","project_path":"../../etc","models":[]}' | python -m json.tool`

## ⚠️ ریسک‌ها و موارد احتیاط
1. **تغییر signature توابع در analysis.py**: اضافه کردن `request: Request` به `run_analysis` و `run_analysis_stream` ممکن است ترتیب پارامترها را بشکند — در FastAPI پارامتر Request باید قبل از Body model باشد، پس باید `async def run_analysis_stream(request: Request, body: AnalysisRequest)` نوشته شود و در بدنه تابع از `body` به جای `request` استفاده شود (خطوط ۱۲۷-۱۹۸ analysis.py که `request.project_path`, `request.models` و غیره را استفاده می‌کنند باید به `body.project_path` تغییر کنند).
2. **Limiter instance مشترک**: اگر Limiter در هر فایل route جداگانه ساخته شود، state مشترک نخواهند داشت. باید یک instance مشترک در `backend/app/core/` تعریف و import شود.
3. **تأثیر روی frontend**: `frontend/src/app/analysis/page.tsx` خط ۱۹۰ مستقیماً به `/api/analysis/run-stream` POST می‌کند — اگر کاربر سریع چند بار کلیک کند، 429 دریافت می‌کند. باید error handling در frontend برای 429 اضافه شود (خارج از scope فعلی اما باید مستند شود).
4. **محیط‌های توسعه**: rate limit در محیط dev ممکن است آزمایش را دشوار کند — باید یک env variable مثل `RATE_LIMIT_ENABLED=false` برای disable کردن در dev در نظر گرفته شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 13: افزودن rate limiting به endpoint چت

**Scope:** این بخش شامل افزودن محدودیت نرخ (rate limiting) به endpoint POST /chat است. کد نمونه نشان‌دهنده استفاده از دکوراتور `@limiter.limit('10/minute')` است. خارج از scope: پیاده‌سازی خود limiter، تغییرات در config، یا تست‌های مرتبط. نکته حیاتی: فایل هدف backend/app/api/routes/chat.py است و باید از همان syntax نمونه پیروی کند.
**Key terms:** backend/app/api/routes/chat.py, @router.post('/chat'), @limiter.limit('10/minute'), ChatRequest

**بخش مربوط از متن کاربر:**
```
**قبل: بدون rate limiting**

_قبل:_
```
@router.post('/chat')
async def chat(request: ChatRequest):
    # بدون محدودیت نرخ
```

_بعد:_
```
@router.post('/chat')
@limiter.limit('10/minute')
async def chat(request: ChatRequest):
    # با محدودیت نرخ
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

@router.post('/chat')
async def chat(request: ChatRequest):
    # بدون محدودیت نرخ
```

_بعد:_
```
@router.post('/chat')
@limiter.limit('10/minute')
async def chat(request: ChatRequest):
    # با محدودیت نرخ
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
backend/app/api/routes/chat.py, @router.post('/chat'), @limiter.limit('10/minute'), ChatRequest
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن rate limiting به endpoint POST /chat

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/chat.py:نامشخص (فایل deep-read نشده)` — `chat` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بر اساس ساختار پروژه، این فایل شامل @router.post('/chat') و تابع chat با پارامتر ChatRequest است.
- `backend/app/main.py:نامشخص (فایل deep-read نشده)` — `app` — احتمالاً نیاز به تعریف Limiter در سطح app دارد. فایل deep-read نشده — مجری باید مسیر را خود تأیید کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده: fastapi. کتابخانه‌های مرتبط: slowapi (برای rate limiting)، pydantic (برای ChatRequest).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/ai_manager.py` — این سرویس احتمالاً توسط endpoint چت فراخوانی می‌شود و rate limiting روی آن تأثیر می‌گذارد.
- `backend/app/api/routes/analysis.py` — ساختار مشابه با chat.py دارد و می‌توان از آن برای الگوبرداری از syntax دکوراتورها استفاده کرد.
- `backend/app/core/config.py` — اگر limiter نیاز به تنظیمات config داشته باشد (مثلاً نرخ پیش‌فرض)، این فایل تحت تأثیر قرار می‌گیرد.

## 🌐 نقشهٔ وابستگی‌ها
این تغییر مستقیماً روی فایل backend/app/api/routes/chat.py اعمال می‌شود. اگر limiter در سطح app تعریف شود، فایل backend/app/main.py نیز تغییر می‌کند. سرویس ai_manager.py که احتمالاً توسط chat.py فراخوانی می‌شود، تحت تأثیر غیرمستقیم قرار می‌گیرد (درخواست‌های محدود). همچنین ممکن است نیاز به افزودن وابستگی slowapi به backend/requirements.txt باشد. فایل config.py ممکن است برای ذخیره نرخ پیش‌فرض استفاده شود.

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن محدودیت نرخ (rate limiting) به endpoint POST /chat در فایل backend/app/api/routes/chat.py را دارد. کد نمونه نشان‌دهنده استفاده از دکوراتور `@limiter.limit('10/minute')` است. خارج از scope: پیاده‌سازی خود limiter، تغییرات در config، یا تست‌های مرتبط. نکته حیاتی: فایل هدف backend/app/api/routes/chat.py است و باید از همان syntax نمونه پیروی کند. کاربر دو بخش قبل/بعد ارائه داده: قبل بدون rate limiting با `@router.post('/chat') async def chat(request: ChatRequest):` و بعد با `@router.post('/chat') @limiter.limit('10/minute') async def chat(request: ChatRequest):`. کلیدواژه‌ها: backend/app/api/routes/chat.py, @router.post('/chat'), @limiter.limit('10/minute'), ChatRequest. در ساختار پروژه فایل backend/app/api/routes/chat.py موجود است اما deep-read نشده، بنابراین محتوای دقیق آن در دسترس نیست. با این حال بر اساس ساختار مشابه سایر routeها (مثلاً backend/app/api/routes/analysis.py یا backend/app/api/routes/settings.py) می‌توان حدس زد که این فایل شامل یک APIRouter با دکوراتور @router.post('/chat') و تابع async با پارامتر ChatRequest است. همچنین فایل backend/app/services/ai_manager.py احتمالاً سرویس پشتیبان چت است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل backend/app/api/routes/chat.py باید دکوراتور @limiter.limit('10/minute') را بالای تابع chat داشته باشد.
- [ ] import مربوط به limiter (از slowapi) در فایل chat.py یا main.py اضافه شده باشد.
- [ ] ارسال درخواست POST به /chat با نرخ بیش از 10 در دقیقه باید پاسخ HTTP 429 Too Many Requests برگرداند.
- [ ] ارسال درخواست POST به /chat با نرخ کمتر از 10 در دقیقه باید پاسخ موفق (200) برگرداند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/chat.py را باز کرده و خط مربوط به تعریف تابع chat را پیدا کن (احتمالاً با دکوراتور @router.post('/chat')). 2. دکوراتور @limiter.limit('10/minute') را بلافاصله بعد از @router.post('/chat') و قبل از تعریف تابع اضافه کن. 3. اطمینان حاصل کن که limiter از کتابخانه مناسب (مثلاً slowapi) import شده باشد: `from slowapi import Limiter` و `from slowapi.util import get_remote_address`. 4. اگر limiter در سطح app تعریف نشده، یک نمونه Limiter با key_func=get_remote_address در همان فایل یا در فایل main.py ایجاد کن. 5. تغییرات را commit کن با پیام 'feat(chat): افزودن rate limiting 10/minute به endpoint POST /chat'. 6. PR جدید ایجاد کن.

## 💡 نمونه‌های قبل/بعد
**افزودن دکوراتور rate limiting به endpoint chat**

_قبل:_
```
@router.post('/chat')
async def chat(request: ChatRequest):
    # بدون محدودیت نرخ
```

_بعد:_
```
@router.post('/chat')
@limiter.limit('10/minute')
async def chat(request: ChatRequest):
    # با محدودیت نرخ
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k chat`
- `curl -X POST http://localhost:8000/chat -H 'Content-Type: application/json' -d '{}'`

## ⚠️ ریسک‌ها و موارد احتیاط
اگر limiter در سطح app تعریف نشود و فقط در route اضافه شود، ممکن است با خطای runtime مواجه شویم. همچنین اگر slowapi به requirements.txt اضافه نشود، import شکست می‌خورد. endpoint chat احتمالاً توسط frontend فراخوانی می‌شود و rate limiting ممکن است تجربه کاربری را تحت تأثیر قرار دهد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 14: اجرای دستورات اعتبارسنجی curl برای endpoint /api/chat

**Scope:** این بخش شامل اجرای دو دستور curl برای اعتبارسنجی endpoint /api/chat است. دستور اول یک درخواست POST ساده با body خالی است. دستور دوم ۲۰ درخواست همزمان POST با body خالی را اجرا می‌کند. این بخش صرفاً بر اجرای این دستورات و مشاهده خروجی آنها تمرکز دارد و شامل پیاده‌سازی یا تغییر کد نمی‌شود.
**Key terms:** /api/chat, localhost:8000, curl

**بخش مربوط از متن کاربر:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'`
- `for i in {1..20}; do curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' &; done`
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای دستورات curl اعتبارسنجی endpoint /api/chat

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/chat.py` — `chat router` — این فایل endpoint /api/chat را تعریف می‌کند. deep-read نشده — مجری باید محتوا را خود بررسی کند تا schema مورد انتظار (فیلدهای اجباری) را شناسایی کند. این مهم است چون body خالی {} ممکن است 422 برگرداند.
- `backend/app/main.py` — `app / router mount` — این فایل entry point اصلی FastAPI است و router های مختلف از جمله chat را با prefix /api mount می‌کند. تأیید کن که prefix واقعی /api/chat است نه /chat.
- `backend/app/core/logging_utils.py` — `StructuredLogger` — برای مشاهده لاگ‌های ساختاریافته هنگام اجرای curl — این فایل توسط chat.py و سایر route ها import می‌شود و خروجی لاگ را شکل می‌دهد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. Backend روی uvicorn با پورت 8000. دستورات curl در bash shell اجرا می‌شوند. برای concurrent test از & (background process) در bash استفاده شده. پروژه از docker-compose.yml برای orchestration استفاده می‌کند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/chat.py` (سطر 1) — فایل اصلی که endpoint POST /api/chat را تعریف می‌کند — schema ورودی، validation، و response را مشخص می‌کند
- `backend/app/main.py` (سطر 1) — router های FastAPI اینجا mount می‌شوند؛ prefix /api و include_router برای chat router اینجاست — تأیید آدرس نهایی endpoint
- `backend/app/core/logging_utils.py` (سطر 1) — StructuredLogger توسط chat.py import می‌شود (بر اساس نقشه import‌های داخلی)؛ لاگ‌های اجرای curl از اینجا عبور می‌کنند
- `backend/app/services/ai_manager.py` (سطر 1) — احتمالاً توسط chat route برای فراخوانی مدل‌های AI استفاده می‌شود — اگر body خالی باشد ممکن است در این لایه خطا رخ دهد

## 🌐 نقشهٔ وابستگی‌ها
endpoint /api/chat در `backend/app/api/routes/chat.py` تعریف شده و از طریق `backend/app/main.py` با prefix /api در دسترس است. بر اساس نقشه import‌های داخلی، `backend/app/core/logging_utils.py` توسط chat.py import می‌شود. همچنین `backend/app/services/ai_manager.py` که توسط ۱۵ فایل import می‌شود احتمالاً در مسیر پردازش chat درگیر است. اجرای ۲۰ درخواست همزمان ممکن است روی connection pool دیتابیس (`backend/app/core/database.py`) و AI manager فشار بیاورد.

## 🔍 Context و وضعیت فعلی
این تسک شامل اجرای دو دستور curl برای اعتبارسنجی endpoint /api/chat روی سرور localhost:8000 است. هیچ تغییر کدی در این تسک وجود ندارد — هدف صرفاً اجرای دستورات و مشاهده خروجی آن‌هاست.

دستور اول: یک درخواست POST ساده با body خالی:
`curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'`

دستور دوم: ۲۰ درخواست همزمان POST با body خالی (load test ابتدایی):
`for i in {1..20}; do curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' &; done`

این endpoint در پروژه در فایل `backend/app/api/routes/chat.py` تعریف شده و از طریق `backend/app/main.py` با prefix `/api` mount می‌شود. بر اساس ساختار پروژه (FastAPI + Next.js)، backend روی پورت 8000 اجرا می‌شود. هدف از اجرای این دستورات:
1. بررسی اینکه endpoint /api/chat در حالت body خالی چه response و status code برمی‌گرداند (validation error 422، یا 200، یا 500)
2. بررسی رفتار سرور تحت ۲۰ درخواست همزمان — آیا race condition، memory leak، یا crash رخ می‌دهد
3. مشاهده response time و consistency پاسخ‌ها

کلیدواژه‌های اصلی: `/api/chat`، `localhost:8000`، `curl`، `POST`، body خالی `{}`، ۲۰ درخواست همزمان.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] دستور اول curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' اجرا شود و HTTP status code مشخصی (200، 422، یا 500) برگرداند
- [ ] دستور دوم (۲۰ درخواست همزمان) بدون crash سرور اجرا شود — سرور بعد از اتمام همه درخواست‌ها همچنان پاسخگو باشد
- [ ] لاگ‌های backend در طول اجرای دستورات هیچ unhandled exception یا traceback نشان ندهند
- [ ] response body دستور اول یک JSON معتبر باشد (نه HTML error page یا plain text)
- [ ] بعد از اجرای ۲۰ درخواست همزمان، memory usage سرور به‌طور غیرعادی افزایش نیابد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک نیازی به تغییر کد ندارد. مراحل اجرا:

1. **اطمینان از اجرای backend**: سرور FastAPI باید روی `http://localhost:8000` در حال اجرا باشد. با `docker-compose up` یا `uvicorn app.main:app --port 8000` راه‌اندازی کن.

2. **اجرای دستور اول** (single request):
```bash
curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'
```
خروجی مورد انتظار: احتمالاً HTTP 422 (Unprocessable Entity) چون body خالی است و endpoint احتمالاً فیلدهای اجباری دارد، یا HTTP 200 اگر body اختیاری باشد.

3. **اجرای دستور دوم** (20 concurrent requests):
```bash
for i in {1..20}; do curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' &; done
```
برای مشاهده بهتر خروجی می‌توان از `wait` بعد از loop استفاده کرد:
```bash
for i in {1..20}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' & done; wait
```

4. **ثبت و تحلیل خروجی**: status code هر درخواست، response body، و لاگ‌های backend را بررسی کن. فایل `backend/app/api/routes/chat.py` را برای درک schema مورد انتظار مطالعه کن.

5. **بررسی لاگ‌های backend**: بعد از اجرا، لاگ‌های سرور را برای خطاهای احتمالی (500، timeout، unhandled exception) بررسی کن.

## 💡 نمونه‌های قبل/بعد
**دستور curl با verbose output برای دیدن کامل response**

_قبل:_
```
curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'
```

_بعد:_
```
curl -v -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' 2>&1 | tee /tmp/chat_test_output.txt
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -v -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'`
- `for i in {1..20}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' & done; wait`
- `curl -X GET http://localhost:8000/health || curl -X GET http://localhost:8000/api/health`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. اگر endpoint /api/chat در `backend/app/api/routes/chat.py` به AI service (از طریق `backend/app/services/ai_manager.py`) متصل باشد، ۲۰ درخواست همزمان با body خالی ممکن است ۲۰ فراخوانی API به سرویس‌های خارجی (OpenAI/Claude/Gemini) ایجاد کند و هزینه‌بر باشد. ۲. connection pool دیتابیس در `backend/app/core/database.py` ممکن است تحت ۲۰ درخواست همزمان به حد max connections برسد. ۳. prefix واقعی endpoint ممکن است `/api/chat` نباشد — باید در `backend/app/main.py` تأیید شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 15: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا

**Scope:** این تسک مربوط به رفع نشت connection در تابع `run_analysis_stream` در فایل `backend/app/api/routes/analysis.py` است. هدف اصلی اطمینان از بسته شدن session دیتابیس در بلاک `finally` است تا در صورت بروز خطا، connection به دیتابیس بازگردانده شود. همچنین باید تست استرس با ۱۰۰ درخواست هم‌زمان برای اطمینان از عدم بروز خطای connection انجام شود. این تسک شامل بازبینی دستی لاگ‌ها برای عدم وجود نشت connection نیز می‌شود.
**Key terms:** backend/app/api/routes/analysis.py, run_analysis_stream, analysis_db.close(), finally, tests/test_analysis.py, test_stress_100_concurrent

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
Rate limiting ممکن است کاربران قانونی را تحت تأثیر قرار دهد. نیاز به تنظیم دقیق محدودیت‌ها.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 8
  id: 979942ad-03ba-4cd6-a5ba-dd563d8d5462
  عنوان اصلی: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - session در `run_analysis_stream` در finally بسته شود [verify_method=static] [verify_plan={"grep_patterns": ["analysis_db\\.close\\(\\)", "finally"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - هیچ نشت connection در لاگ‌ها دیده نشود [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
  - تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_stress_100_concurrent", "timeout_seconds": 120}]
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع نشت connection دیتابیس در run_analysis_stream

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:115-124` — `run_analysis_stream` — محل ایجاد session دیتابیس — analysis_db در اینجا تعریف شده اما close() ندارد
  ```python
  # 🔴 ایجاد db session برای استفاده از پرامپت‌های دیتابیس
                  from ...core.database import SessionLocal
                  analysis_db = SessionLocal()
  
                  # ساخت DeepAnalysisService با progress callback و db_session
                  deep_analyzer = DeepAnalysisService(
                      ai_manager=ai_manager,
                      progress_callback=progress_callback,
                      db_session=analysis_db  # 🔴 برای استفاده از پرامپت‌های دیتابیس
                  )
  ```
- `backend/app/api/routes/analysis.py:207-212` — `run_analysis_stream -> finally block` — بلاک finally فعلی — session را نمی‌بندد، فقط رویداد done را ارسال می‌کند
  ```python
  finally:
                  # سیگنال اتمام
                  await progress_queue.put({
                      "event": "done",
                      "result": final_result if final_result else None
                  })
  ```
- `backend/app/api/routes/analysis.py:200-206` — `run_analysis_stream -> except block`
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}",
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به رفع نشت connection در تابع `run_analysis_stream` در فایل `backend/app/api/routes/analysis.py` است. هدف اصلی اطمینان از بسته شدن session دیتابیس (analysis_db) در بلاک `finally` است تا در صورت بروز خطا، connection به دیتابیس بازگردانده شود. همچنین باید تست استرس با ۱۰۰ درخواست هم‌زمان برای اطمینان از عدم بروز خطای connection انجام شود. این تسک شامل بازبینی دستی لاگ‌ها برای عدم وجود نشت connection نیز می‌شود.

در کد فعلی (خطوط 115-124 فایل analysis.py)، session دیتابیس با `SessionLocal()` ایجاد می‌شود اما در هیچ‌جایی `analysis_db.close()` فراخوانی نشده است. بلاک `finally` موجود (خطوط 207-212) فقط رویداد 'done' را ارسال می‌کند و session را نمی‌بندد. این یک نشت connection قطعی است که در سناریوهای خطا (Exception در خط 200-206) یا اتمام عادی، session باز می‌ماند.

کلیدواژه‌ها: backend/app/api/routes/analysis.py, run_analysis_stream, analysis_db.close(), finally, tests/test_analysis.py, test_stress_100_concurrent

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل `backend/app/api/routes/analysis.py`، در تابع `run_analysis_stream` (خط 84)، متغیر `analysis_db` را در scope خارج از try/finally تعریف کن تا در finally قابل دسترس باشد.
2. در بلاک `finally` موجود (خطوط 207-212)، قبل از ارسال رویداد 'done'، `analysis_db.close()` را اضافه کن.
3. برای ایمنی بیشتر، `analysis_db` را در یک بلاک try/except جداگانه ببند تا خطای بستن session باعث نشود رویداد 'done' ارسال نشود.
4. فایل تست `tests/test_analysis.py` را ایجاد یا ویرایش کن تا تابع `test_stress_100_concurrent` را شامل شود که ۱۰۰ درخواست هم‌زمان به endpoint /analysis/run-stream ارسال کند و بررسی کند که هیچ خطای connection رخ ندهد.
5. لاگ‌های سرور را پس از اجرای تست استرس بازبینی دستی کن تا از عدم وجود پیام‌های 'connection leak' یا 'too many connections' اطمینان حاصل شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 16: بررسی اولیه و پیش‌نیازهای اجرای درخواست (یادداشت مهم برای مدل اجراکننده)

**Scope:** این بخش یک یادداشت هشداردهنده و راهنمای کلی برای مدل اجراکننده است، نه یک درخواست اجرایی مشخص. شامل دستورالعمل‌هایی برای بررسی وجود پیاده‌سازی قبلی، مسئولیت‌پذیری در قبال تشخیص‌های خودکار، و نحوه برخورد با کارهای طولانی است. این بخش خودش یک مرحله اجرایی نیست، بلکه یک prelude برای تمام مراحل بعدی است. هیچ فایل یا کلاس خاصی برای تغییر در این بخش ذکر نشده، بلکه یک چارچوب رفتاری برای مدل تعیین می‌کند.

**بخش مربوط از متن کاربر:**
```
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
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف چارچوب رفتاری مدل اجراکننده — prelude پیش از تمام مراحل

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py` — `app (FastAPI entry point)` — فایل entry point اصلی backend — مناسب‌ترین مکان برای افزودن reference به راهنمای رفتاری مدل اجراکننده. این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند، اما از ساختار پروژه مشخص است که entry point اصلی است.
- `docs/ARCHITECTURE.md` — `N/A — مستند معماری` — فایل معماری موجود در docs/ — باید بررسی شود که آیا بخشی برای راهنمای مدل اجراکننده دارد یا خیر. اگر ندارد، یا این فایل به‌روزرسانی می‌شود یا فایل جدید docs/AGENT_EXECUTION_GUIDELINES.md ایجاد می‌شود. این فایل deep-read نشده — مجری باید محتوا را خود تأیید کند.
- `backend/app/api/routes/analysis.py:46-80` — `run_analysis` — نمونه‌ای از یک endpoint پیچیده که قبل از هر تغییر باید بررسی شود آیا قبلاً پیاده‌سازی مشابهی وجود دارد. این endpoint توسط frontend/src/app/analysis/page.tsx فراخوانی می‌شود و تغییر آن روی جریان کامل تحلیل اثر می‌گذارد.
  ```python
  @router.post("/run", response_model=AnalysisResponse)
  async def run_analysis(
      request: AnalysisRequest,
      background_tasks: BackgroundTasks
  ):
      """
      اجرای تحلیل جدید
  
      تحلیل کامل پروژه توسط مدل‌های انتخابی
      """
      try:
          analyzer = get_project_analyzer()
          analyzer.initialize()
  ```
- `backend/app/api/routes/github_import.py:94-130` — `import_repository` — این endpoint پس از import، به‌طور خودکار auto_setup_project_memory و auto_register_watched را فراخوانی می‌کند (خطوط 132-181). نمونه‌ای از کدی که قبلاً قابلیت‌های متعددی به آن اضافه شده — مدل اجراکننده باید قبل از هر تغییر بررسی کند چه چیزی از قبل وجود دارد.
  ```python
  @router.post("/import")
  async def import_repository(request: ImportRepoRequest):
      """
      Import کامل یک repository از GitHub
  
      - پشتیبانی از repo های public و private
      - برای private repos، توکن GitHub لازم است
      - فایل‌های بزرگ و باینری فیلتر می‌شوند
      """
      service = get_github_import_service()
  
      # دریافت توکن مناسب
      token = get_effective_token(request.token, request.use_global_token)
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js 14 (TypeScript). Backend: Python با SQLAlchemy، Pydantic v2، asyncio، APScheduler. Frontend: React 18، Zustand، Tailwind CSS، axios. مستندات در docs/ به فرمت Markdown. چارچوب رفتاری باید با این stack سازگار باشد و در فرمت Markdown در docs/ ذخیره شود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — پرکاربردترین فایل در پروژه با 16 importer — هر تغییر در آن روی analysis.py، github_import.py، model_profiles.py، models.py، oversight.py و 11 فایل دیگر اثر مستقیم دارد. چارچوب رفتاری باید به‌ویژه برای این فایل رعایت شود.
- `backend/app/services/ai_manager.py` (سطر 1) — دومین فایل پرکاربرد با 15 importer — شامل analysis.py، models.py، orchestrator.py، oversight.py، project_health.py. تغییر بدون بررسی قبلی می‌تواند کل pipeline تحلیل AI را خراب کند.
- `backend/app/services/oversight_service.py` (سطر 161) — 7 فایل آن را import می‌کنند: github_import.py، oversight.py، render_logs.py، simple_projects.py، main.py. در github_import.py خط 161 فراخوانی می‌شود. نمونه‌ای از سرویسی که قبلاً قابلیت auto_register_watched به آن اضافه شده — باید قبل از هر تغییر بررسی شود.
- `backend/app/api/routes/model_profiles.py` (سطر 23) — این فایل defensive imports دارد (خطوط 23-48) که نشان می‌دهد قبلاً مشکلاتی در import وجود داشته و راه‌حل‌هایی اعمال شده. مدل اجراکننده باید این pattern را قبل از تغییر بشناسد.
- `docs/ROADMAP.md` (سطر 1) — فایل roadmap پروژه — باید قبل از هر تغییر بررسی شود که آیا درخواست با roadmap همخوانی دارد یا خیر. این فایل deep-read نشده — مجری باید محتوا را خود تأیید کند.

## 🌐 نقشهٔ وابستگی‌ها
این چارچوب رفتاری روی تمام فایل‌های پروژه اثر غیرمستقیم دارد، اما به‌ویژه روی هاب‌های اصلی import تأثیرگذار است. backend/app/core/database.py با 16 importer و backend/app/services/ai_manager.py با 15 importer بیشترین ریسک را دارند. backend/app/models/project.py با 10 importer (github_import.py، models.py، oversight.py، project_health.py، project_journal.py) نیز در این دسته قرار دارد. backend/app/services/oversight_service.py با 7 importer و backend/app/api/routes/project_journal.py با 6 importer نیز باید با احتیاط تغییر داده شوند. چارچوب رفتاری مستند شده در docs/ باید به‌گونه‌ای باشد که مدل اجراکننده هنگام بررسی هر یک از این فایل‌ها به آن دسترسی داشته باشد.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت هشداردهنده و راهنمای کلی (prelude) برای مدل اجراکننده است که باید پیش از شروع هر مرحله اجرایی در repo خوانده و رعایت شود. محتوای اصلی درخواست کاربر شامل چند بخش کلیدی است:

۱. **احتمال پیاده‌سازی قبلی**: ممکن است بخشی یا تمامِ هر درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط باید بررسی شود که چه چیزی از قبل وجود دارد. اگر یک قابلیت/فایل/تابع از قبل موجود است، نباید دوباره ساخته شود؛ فقط موارد ناقص یا اشتباه اصلاح/تکمیل می‌شوند. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت می‌شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

۲. **مسئولیت مدل اجراکننده**: پیش از هر تغییر، مدل باید خودش ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کند. اگر تشخیص داد موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودش عمل کند — پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد. اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر انتخاب شده و در commit message توضیح داده می‌شود.

۳. **کارهای طولانی**: خلاصه‌سازی ممنوع است. همه چیز به‌طور کامل انجام می‌شود. اگر یک کامیت گنجایش ندارد، در چندین کامیت متوالی انجام می‌شود — ولی هیچ بخشی skip نمی‌شود. ترتیب کامیت‌ها باید منطقی باشد (foundation → core → integration → tests). در آخر یک checklist از همه‌ی کامیت‌ها در PR description نوشته می‌شود.

این پرامپت بر اساس یک بررسی اولیهٔ خودکار از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نشود.

در کدبیس فعلی، این چارچوب رفتاری باید در تمام روترهای backend (مانند analysis.py، github_import.py، model_profiles.py) و سرویس‌های اصلی (مانند oversight_service.py، inspector_agent.py) رعایت شود. به‌ویژه در فایل‌هایی که چندین بار import می‌شوند مانند backend/app/core/database.py (16 importer) و backend/app/services/ai_manager.py (15 importer)، هر تغییر باید با احتیاط کامل و بررسی قبلی انجام شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل راهنمای رفتاری مدل اجراکننده در docs/ وجود داشته باشد (یا ARCHITECTURE.md به‌روزرسانی شده باشد) و شامل سه بخش: بررسی پیاده‌سازی قبلی، مسئولیت مدل، مدیریت کارهای طولانی
- [ ] در صورت وجود قابلیت از قبل پیاده‌شده، یک کامیت no-op با توضیح کامل ثبت شده باشد که مشخص کند کدام فایل‌ها درخواست را پوشش می‌دهند
- [ ] ترتیب کامیت‌ها در هر PR طولانی باید الگوی foundation → core → integration → tests را دنبال کند و checklist در PR description موجود باشد
- [ ] فایل backend/app/main.py یا docs/ شامل reference به راهنمای رفتاری باشد تا مدل‌های اجراکننده هنگام بررسی entry point آن را ببینند
- [ ] هیچ فایل یا تابع موجودی بدون بررسی قبلی دوباره ساخته نشده باشد — به‌ویژه در فایل‌های پرکاربرد مانند backend/app/core/database.py و backend/app/services/ai_manager.py
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک یک تسک اجرایی مستقیم نیست بلکه یک چارچوب رفتاری (behavioral framework) است که باید به صورت مستند در repo ثبت شود تا تمام مدل‌های اجراکننده آینده از آن پیروی کنند. مراحل پیشنهادی:

1. **بررسی وجود مستندات مشابه**: ابتدا در docs/ بررسی کن که آیا فایلی مانند CONTRIBUTING.md، AGENT_GUIDELINES.md یا مشابه وجود دارد که این قوانین را پوشش دهد. فایل‌های موجود: docs/ARCHITECTURE.md، docs/AUDIT_REPORT.md، docs/PHASE_5_META_VALIDATION.md، docs/README.md، docs/ROADMAP.md، docs/SYSTEM_REPORT_2026-02-08.md.

2. **ایجاد یا به‌روزرسانی فایل راهنما**: اگر فایل مناسبی وجود ندارد، یک فایل docs/AGENT_EXECUTION_GUIDELINES.md ایجاد کن که شامل سه بخش اصلی باشد: الف) بررسی پیاده‌سازی قبلی (grep/search قبل از شروع)، ب) مسئولیت‌پذیری مدل (قضاوت مستقل، no-op commit)، ج) مدیریت کارهای طولانی (multi-commit، checklist در PR).

3. **افزودن reference در فایل‌های کلیدی**: در backend/app/main.py یک comment یا docstring اضافه کن که به این راهنما اشاره کند تا مدل‌های اجراکننده هنگام بررسی entry point آن را ببینند.

4. **تأیید با no-op commit**: اگر این چارچوب قبلاً در docs/ موجود بود، یک کامیت توضیحی ثبت کن که مشخص کند کدام فایل‌ها این درخواست را پوشش می‌دهند.

## 💡 نمونه‌های قبل/بعد
**defensive import pattern — نمونه‌ای از رفتار صحیح که قبلاً در model_profiles.py پیاده شده**

_قبل:_
```
# بدون بررسی قبلی — import مستقیم که ممکن است fail شود
from ...core.database import get_db
from ...models.ai_profile import AIProfile, ModelValidationRecord
from ...services.model_profiler import get_model_profiler
```

_بعد:_
```
# با بررسی قبلی — defensive imports که در model_profiles.py خطوط 23-48 پیاده شده
try:
    from ...core.database import get_db
    DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import database: {e}")
    DB_AVAILABLE = False
    def get_db():
        return None

try:
    from ...models.ai_profile import AIProfile, ModelValidationRecord
    MODELS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import ai_profile models: {e}")
    MODELS_AVAILABLE = False
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -r 'no-op\|already implemented\|قبلاً' docs/ --include='*.md'`
- `grep -r 'AGENT_EXECUTION_GUIDELINES\|راهنمای مدل' backend/app/main.py docs/`
- `find docs/ -name '*.md' | xargs grep -l 'foundation.*core.*integration.*tests' 2>/dev/null`
- `pytest backend/tests/ -v --tb=short -q`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. backend/app/core/database.py با 16 importer: هر تغییر در این فایل روی analysis.py، github_import.py، model_profiles.py، models.py، oversight.py و 11 فایل دیگر اثر مستقیم دارد — بدون بررسی قبلی نباید تغییر داده شود. ۲. backend/app/services/ai_manager.py با 15 importer: تغییر بدون بررسی می‌تواند کل pipeline تحلیل AI را خراب کند. ۳. backend/app/api/routes/github_import.py خطوط 132-181: قابلیت‌های auto_setup_project_memory و auto_register_watched قبلاً اضافه شده‌اند — مدل اجراکننده باید قبل از هر تغییر این بخش را بخواند تا دوباره‌سازی نکند. ۴. defensive imports در model_profiles.py خطوط 23-48: این pattern نشان می‌دهد قبلاً مشکلاتی در import وجود داشته — تغییر بدون درک این context می‌تواند regression ایجاد کند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 17: رفع نشت Session در run_analysis_task با افزودن finally block برای بستن Session

**Scope:** این بخش فقط به رفع باگ نشت Session در تابع run_analysis_task در فایل backend/app/api/routes/analysis.py می‌پردازد. شامل افزودن try/finally برای بستن analysis_db در مسیر خطا و موفقیت است. سایر توابع موجود در analysis.py که از الگوی صحیح استفاده می‌کنند (get_analysis_reports, get_analysis_report, delete_analysis_report, download_analysis_report) نیازی به تغییر ندارند. مشکل مشابه در github_import.py قبلاً حل شده است و خارج از scope این بخش است.
**Key terms:** backend/app/api/routes/analysis.py, run_analysis_task, run_analysis_stream, SessionLocal, analysis_db, DeepAnalysisService, finally

**بخش مربوط از متن کاربر:**
```
در فایل `backend/app/api/routes/analysis.py`، توابع `get_analysis_reports`، `get_analysis_report`، `delete_analysis_report` و `download_analysis_report` از الگوی `SessionLocal()` استفاده می‌کنند و session را در `finally` می‌بندند. اما در `run_analysis_stream` (خط 117)، یک `analysis_db = SessionLocal()` ایجاد می‌شود که در `finally` بسته نمی‌شود. اگر خطایی در `run_analysis_task` رخ دهد، session باز می‌ماند و باعث نشت connection در SQLite می‌شود.

```python
analysis_db = SessionLocal()

deep_analyzer = DeepAnalysisService(
    ai_manager=ai_manager,
    progress_callback=progress_callback,
    db_session=analysis_db
)
```
```

python
analysis_db = SessionLocal()

deep_analyzer = DeepAnalysisService(
    ai_manager=ai_manager,
    progress_callback=progress_callback,
    db_session=analysis_db
)
```

--- کلیدواژه‌ها ---
backend/app/api/routes/analysis.py, run_analysis_task, run_analysis_stream, SessionLocal, analysis_db, DeepAnalysisService, finally
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع نشت Session در run_analysis_task با finally block

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:117-130` — `run_analysis_stream` — اینجا analysis_db ایجاد می‌شود اما در finally بسته نمی‌شود — نشت session
  ```python
  analysis_db = SessionLocal()
  
  deep_analyzer = DeepAnalysisService(
      ai_manager=ai_manager,
      progress_callback=progress_callback,
      db_session=analysis_db
  )
  ```
- `backend/app/api/routes/analysis.py:45-60` — `get_analysis_reports` — الگوی صحیح بستن session در finally — این تابع نیازی به تغییر ندارد و به عنوان مرجع استفاده می‌شود
  ```python
  def get_analysis_reports(...):
      db = SessionLocal()
      try:
          ...
      finally:
          db.close()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
fastapi, sqlalchemy, aiosqlite, SessionLocal از backend/app/core/database.py

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/deep_analysis_service.py` (سطر 25) — DeepAnalysisService که analysis_db را به عنوان db_session دریافت می‌کند — اگر session بسته نشود، این سرویس با connection مرده کار می‌کند
- `backend/app/api/routes/github_import.py` (سطر 80) — مشکل مشابه نشت session قبلاً در این فایل حل شده است — می‌توان از الگوی آن استفاده کرد
- `backend/app/core/database.py` (سطر 15) — SessionLocal از اینجا import می‌شود — نحوه تعریف session و مدیریت connection pool

## 🌐 نقشهٔ وابستگی‌ها
این تغییر مستقیماً روی فایل backend/app/api/routes/analysis.py اعمال می‌شود. تابع run_analysis_task که توسط run_analysis_stream فراخوانی می‌شود، analysis_db را از SessionLocal() ایجاد می‌کند و به DeepAnalysisService (در backend/app/services/deep_analysis_service.py) پاس می‌دهد. اگر session بسته نشود، connection به SQLite (از طریق sqlalchemy و aiosqlite) نشت می‌کند و ممکن است باعث exhaustion connection pool شود. الگوی صحیح در توابع دیگر analysis.py (get_analysis_reports, get_analysis_report, delete_analysis_report, download_analysis_report) وجود دارد و باید replicated شود. مشکل مشابه در github_import.py قبلاً حل شده است.

## 🔍 Context و وضعیت فعلی
رفع نشت Session در تابع run_analysis_task در فایل backend/app/api/routes/analysis.py. کاربر گزارش داده که در فایل `backend/app/api/routes/analysis.py`، توابع `get_analysis_reports`، `get_analysis_report`، `delete_analysis_report` و `download_analysis_report` از الگوی `SessionLocal()` استفاده می‌کنند و session را در `finally` می‌بندند. اما در `run_analysis_stream` (خط 117)، یک `analysis_db = SessionLocal()` ایجاد می‌شود که در `finally` بسته نمی‌شود. اگر خطایی در `run_analysis_task` رخ دهد، session باز می‌ماند و باعث نشت connection در SQLite می‌شود. کد فعلی: `analysis_db = SessionLocal()` سپس `deep_analyzer = DeepAnalysisService(ai_manager=ai_manager, progress_callback=progress_callback, db_session=analysis_db)`. مشکل مشابه در github_import.py قبلاً حل شده است و خارج از scope این بخش است. سایر توابع موجود در analysis.py که از الگوی صحیح استفاده می‌کنند (get_analysis_reports, get_analysis_report, delete_analysis_report, download_analysis_report) نیازی به تغییر ندارند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تابع run_analysis_task باید analysis_db.close() را در finally block فراخوانی کند — بررسی با grep برای وجود finally و close
- [ ] پس از تغییر، هیچ session بازی در صورت خطا باقی نماند — شبیه‌سازی با raise Exception در run_analysis_task و بررسی لاگ connection
- [ ] الگوی finally block با توابع دیگر analysis.py (get_analysis_reports) همخوانی داشته باشد
- [ ] تغییر فقط روی run_analysis_task اعمال شود و توابع دیگر (get_analysis_reports, get_analysis_report, delete_analysis_report, download_analysis_report) untouched بمانند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/api/routes/analysis.py، تابع run_analysis_task (که توسط run_analysis_stream فراخوانی می‌شود) را با try/finally block بپیچید. 2. در بخش try، کد موجود شامل ایجاد analysis_db = SessionLocal() و استفاده از آن در DeepAnalysisService را قرار دهید. 3. در بخش finally، analysis_db.close() را اضافه کنید تا session حتی در صورت بروز خطا بسته شود. 4. اطمینان حاصل کنید که analysis_db در scope تابع تعریف شده و در finally قابل دسترسی است. 5. از الگوی مشابه توابع دیگر analysis.py (get_analysis_reports و ...) پیروی کنید که session را در finally می‌بندند.

## 💡 نمونه‌های قبل/بعد
**قبل از تغییر — run_analysis_task بدون finally**

_قبل:_
```
analysis_db = SessionLocal()

deep_analyzer = DeepAnalysisService(
    ai_manager=ai_manager,
    progress_callback=progress_callback,
    db_session=analysis_db
)

# ادامه کد بدون finally block
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    deep_analyzer = DeepAnalysisService(
        ai_manager=ai_manager,
        progress_callback=progress_callback,
        db_session=analysis_db
    )
    # ادامه کد
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_analysis_session_leak.py -v`
- `grep -n 'finally:' backend/app/api/routes/analysis.py`
- `grep -n 'analysis_db.close()' backend/app/api/routes/analysis.py`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر کوچک و محدود به یک تابع — ریسک پایین. اما اگر finally block اشتباه placed شود (مثلاً قبل از تعریف analysis_db)، ممکن است NameError رخ دهد. همچنین باید دقت شود که analysis_db در scope finally قابل دسترسی باشد. این تابع توسط run_analysis_stream فراخوانی می‌شود و ممکن است در آینده توسط endpointهای دیگر نیز استفاده شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 18: بستن session در finally تابع run_analysis_stream

**Scope:** این مرحله فقط به بستن session در بلوک finally تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py می‌پردازد. شامل بررسی ownership session بین تابع و DeepAnalysisService است. خارج از scope: سایر بخش‌های کد، تست‌ها، linter، type-check و تست استرس (این موارد در AC ذکر شده‌اند اما بخشی از اجرای این مرحله نیستند).
**Key terms:** backend/app/api/routes/analysis.py, run_analysis_stream, DeepAnalysisService, session, finally

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] session در `run_analysis_stream` در finally بسته شود
- [ ] هیچ نشت connection در لاگ‌ها دیده نشود
- [ ] تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در `run_analysis_stream`، session ایجاد شده در خط 117 را در `finally` ببندید. همچنین بررسی کنید که آیا `DeepAnalysisService` ownership session را می‌گیرد یا خیر. اگر سرویس session را مدیریت می‌کند، نیازی به بستن در اینجا نیست، اما اگر ownership با این تابع است، حتماً بسته شود.
```

## 🎯 هدف (خلاصه ساختاریافته)
بستن session در finally تابع run_analysis_stream

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:117` — `run_analysis_stream` — session در این خط ایجاد می‌شود و باید در finally بسته شود
  ```python
  session = next(get_db())  # خط 117
  ```
- `backend/app/services/deep_analysis_service.py:نامشخص` — `DeepAnalysisService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بررسی شود که آیا این سرویس ownership session را می‌گیرد یا خیر.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack تشخیص داده شده: fastapi. کتابخانه‌های مرتبط: SQLAlchemy (برای مدیریت session)، python-dotenv (برای تنظیمات).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 117) — فایل اصلی که تابع run_analysis_stream در آن قرار دارد
- `backend/app/services/deep_analysis_service.py` (سطر نامشخص) — سرویسی که ممکن است ownership session را بگیرد
- `backend/app/core/database.py` (سطر نامشخص) — احتمالاً تابع get_db در این فایل تعریف شده است

## 🌐 نقشهٔ وابستگی‌ها
این تغییر مستقیماً روی تابع run_analysis_stream در backend/app/api/routes/analysis.py تأثیر می‌گذارد. DeepAnalysisService در backend/app/services/deep_analysis_service.py ممکن است تحت تأثیر قرار گیرد اگر ownership session را تغییر دهیم. تابع get_db در backend/app/core/database.py احتمالاً session را ایجاد می‌کند. هیچ فایل دیگری مستقیماً تحت تأثیر قرار نمی‌گیرد زیرا تغییر محدود به یک بلوک finally است.

## 🔍 Context و وضعیت فعلی
این تسک به بستن session در بلوک finally تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py می‌پردازد. کاربر درخواست کرده که session ایجاد شده در خط 117 این فایل در finally بسته شود. همچنین باید بررسی شود که آیا DeepAnalysisService ownership session را می‌گیرد یا خیر. اگر سرویس session را مدیریت می‌کند، نیازی به بستن در اینجا نیست، اما اگر ownership با این تابع است، حتماً بسته شود. کلیدواژه‌های اصلی: backend/app/api/routes/analysis.py, run_analysis_stream, DeepAnalysisService, session, finally. خارج از scope: سایر بخش‌های کد، تست‌ها، linter، type-check و تست استرس (این موارد در AC ذکر شده‌اند اما بخشی از اجرای این مرحله نیستند).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] session در run_analysis_stream در finally بسته شود
- [ ] هیچ نشت connection در لاگ‌ها دیده نشود
- [ ] تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود
- [ ] هیچ تستی fail نمی‌شود (pytest)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (mypy)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل backend/app/api/routes/analysis.py را باز کرده و تابع run_analysis_stream را پیدا کنید. 2. session ایجاد شده در خط 117 را شناسایی کنید. 3. بررسی کنید که آیا DeepAnalysisService (که در backend/app/services/deep_analysis_service.py تعریف شده) ownership session را می‌گیرد یا خیر. 4. اگر سرویس session را مدیریت نمی‌کند، یک بلوک finally به تابع اضافه کنید که session را ببندد. 5. اگر سرویس session را مدیریت می‌کند، نیازی به تغییر نیست. 6. از بسته شدن صحیح session با استفاده از session.close() اطمینان حاصل کنید.

## 💡 نمونه‌های قبل/بعد
**بستن session در finally**

_قبل:_
```
session = next(get_db())
# ... کد فعلی بدون finally
```

_بعد:_
```
session = next(get_db())
try:
    # ... کد فعلی
finally:
    session.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/`
- `ruff check backend/app/api/routes/analysis.py`
- `mypy backend/app/api/routes/analysis.py`

## ⚠️ ریسک‌ها و موارد احتیاط
ریسک اصلی این است که اگر DeepAnalysisService ownership session را بگیرد، بستن session در finally باعث بسته شدن زودهنگام session می‌شود و سرویس نمی‌تواند از آن استفاده کند. همچنین اگر session در finally بسته شود، ممکن است خطاهای دیگری در کد ایجاد شود که به session نیاز دارند. باید با دقت بررسی شود که آیا سرویس session را مدیریت می‌کند یا خیر.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 19: رفع نشت session در analysis_db با استفاده از try/finally

**Scope:** این بخش شامل اصلاح الگوی استفاده از SessionLocal در فایل‌های backend برای اطمینان از بسته شدن session پس از استفاده است. نمونه ارائه‌شده نشان‌دهنده تغییر از حالت بدون finally به حالت try/finally می‌باشد. خارج از scope: تغییرات در frontend، تست‌ها، یا فایل‌های config.
**Key terms:** SessionLocal, analysis_db, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/services/deep_analysis_service.py, backend/app/api/routes/github_import.py

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
analysis_db = SessionLocal()
# ... استفاده ...
# finally: بسته نمی‌شود
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    # ... استفاده ...
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

analysis_db = SessionLocal()
# ... استفاده ...
# finally: بسته نمی‌شود
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    # ... استفاده ...
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
SessionLocal, analysis_db, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/services/deep_analysis_service.py, backend/app/api/routes/github_import.py
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع نشت session با try/finally در analysis_db

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py` — `SessionLocal usage in route handlers` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اما طبق نقشه import‌ها، این فایل از `backend/app/core/database.py` (که 19 فایل آن را import می‌کنند) و `backend/app/services/model_profiler.py` استفاده می‌کند. جستجو برای `SessionLocal()` در این فایل الزامی است.
- `backend/app/services/deep_analysis_service.py:540-545` — `_save_analysis_results` — در متد `run_full_analysis` (خط ۳۱۴)، `db_session` از بیرون دریافت می‌شود. اگر caller این session را بدون try/finally می‌سازد، نشت رخ می‌دهد. همچنین باید بررسی شود که آیا در داخل `_save_analysis_results` یا سایر متدهای این کلاس، `SessionLocal()` مستقیم ساخته می‌شود.
  ```python
  # ذخیره در دیتابیس
              if db_session:
                  await self._save_analysis_results(project_id, results, db_session)
  ```
- `backend/app/services/deep_analysis_service.py:231-244` — `DeepAnalysisService.__init__` — `db_session` در `__init__` ذخیره می‌شود و در `_get_prompt_from_db`، `_start_prompt_execution`، `_complete_prompt_execution` استفاده می‌شود. اگر caller این session را بدون try/finally بسازد، نشت رخ می‌دهد.
  ```python
  def __init__(self, ai_manager=None, progress_callback: Optional[Callable[[Dict], None]] = None, db_session=None):
          """
          مقداردهی اولیه
  
          Args:
              ai_manager: مدیر مدل‌های AI (برای فراخوانی مدل‌ها)
              progress_callback: callback برای گزارش پیشرفت (برای streaming)
              db_session: session دیتابیس برای پرامپت‌ها
          """
          self.ai_manager = ai_manager
          self.analysis_factors = DEFAULT_ANALYSIS_FACTORS.copy()
          self.progress = AnalysisProgressTracker(progress_callback)
          self._db_session = db_session
          self._prompt_executions = {}  # ذخیره شناسه‌های اجرای پرامپت‌ها
  ```
- `backend/app/api/routes/github_import.py` — `SessionLocal usage` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. طبق نقشه import‌ها، این فایل از `backend/app/core/database.py` استفاده می‌کند. جستجو برای `SessionLocal()` الزامی است.
- `backend/app/core/database.py` — `SessionLocal / get_db` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل هاب اصلی است که 19 فایل آن را import می‌کنند. باید اطمینان حاصل شود که `get_db` generator با `yield` و `try/finally` پیاده‌سازی شده است.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. دیتابیس: SQLAlchemy با `SessionLocal` (احتمالاً SQLite یا PostgreSQL بر اساس `aiosqlite` در requirements.txt). الگوی صحیح FastAPI برای session management: استفاده از `Depends(get_db)` با generator که `yield` دارد و `finally: db.close()` در آن. کتابخانه‌های مرتبط: `sqlalchemy>=2.0.0`، `aiosqlite>=0.19.0` (از requirements.txt).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/chat.py` — کاربر صراحتاً این فایل را به‌عنوان یکی از فایل‌های هدف نام برده. احتمالاً `SessionLocal()` بدون try/finally در handler های این روتر استفاده می‌شود.
- `backend/app/services/analysis_progress_manager.py` — طبق نقشه import‌ها، این فایل از `backend/app/models/project.py` استفاده می‌کند و احتمالاً با session دیتابیس تعامل دارد. باید بررسی شود.
- `backend/app/services/oversight_upload_session.py` — طبق نقشه import‌ها، این فایل از `backend/app/services/oversight_service.py` استفاده می‌کند و ممکن است الگوی مشابه SessionLocal داشته باشد.
- `backend/app/services/scan_v5/scan_inspector_session.py` — طبق نقشه import‌ها، این فایل از `backend/app/core/database.py` و `backend/app/services/oversight_service.py` استفاده می‌کند — احتمال وجود SessionLocal بدون try/finally.
- `backend/app/services/github_import.py` — طبق نقشه import‌ها، این فایل از `backend/app/core/database.py` استفاده می‌کند و باید بررسی شود.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/core/database.py` هاب اصلی است که ۱۹ فایل آن را import می‌کنند، از جمله: `backend/app/api/routes/analysis.py`، `backend/app/api/routes/github_import.py`، `backend/app/api/routes/security_analysis.py`، `backend/app/services/github_import.py`، و `backend/app/services/scan_v5/scan_inspector_session.py`. هر تغییری در الگوی `get_db` یا `SessionLocal` در این فایل روی تمام ۱۹ فایل caller اثر می‌گذارد. `backend/app/services/deep_analysis_service.py` از `db_session` خارجی استفاده می‌کند (خط ۲۳۱) و توسط `backend/app/api/routes/analysis.py` و `backend/app/api/routes/project_health.py` فراخوانی می‌شود. `backend/app/models/project.py` توسط ۱۳ فایل import می‌شود و در session‌های دیتابیس نقش مدل اصلی را دارد.

## 🔍 Context و وضعیت فعلی
این تسک به رفع نشت session (session leak) در فایل‌های backend مربوط به استفاده از `SessionLocal` می‌پردازد. مشکل اصلی این است که در چندین فایل، یک نمونه از `SessionLocal()` ساخته می‌شود (مثلاً `analysis_db = SessionLocal()`) اما در صورت بروز exception یا خروج غیرعادی از تابع، متد `analysis_db.close()` هرگز فراخوانی نمی‌شود. این باعث نشت connection به دیتابیس و در نهایت تخلیه connection pool می‌شود.

کاربر به‌صراحت الگوی قبل/بعد را مشخص کرده است:

**قبل (مشکل‌دار):**
```python
analysis_db = SessionLocal()
# ... استفاده ...
# finally: بسته نمی‌شود
```

**بعد (صحیح):**
```python
analysis_db = SessionLocal()
try:
    # ... استفاده ...
finally:
    analysis_db.close()
```

فایل‌های هدف که کاربر صراحتاً نام برده:
- `backend/app/api/routes/analysis.py`
- `backend/app/api/routes/chat.py`
- `backend/app/services/deep_analysis_service.py`
- `backend/app/api/routes/github_import.py`

از بررسی کد `deep_analysis_service.py` (خطوط ۲۳۱-۳۵۱) مشخص است که این سرویس `db_session` را از بیرون دریافت می‌کند و در `run_full_analysis` (خط ۳۱۴) از آن استفاده می‌کند. اما در روترهایی که این سرویس را فراخوانی می‌کنند، ممکن است `SessionLocal()` بدون `try/finally` ساخته شده باشد. همچنین `_save_analysis_results` (خط ۵۴۳) مستقیماً از `db_session` استفاده می‌کند. خارج از scope این تسک: تغییرات در frontend، تست‌ها، یا فایل‌های config.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] در `backend/app/api/routes/analysis.py`، هر فراخوانی `SessionLocal()` باید درون بلوک `try/finally` با `db.close()` در finally باشد
- [ ] در `backend/app/api/routes/chat.py`، هر فراخوانی `SessionLocal()` باید درون بلوک `try/finally` با `db.close()` در finally باشد
- [ ] در `backend/app/api/routes/github_import.py`، هر فراخوانی `SessionLocal()` باید درون بلوک `try/finally` با `db.close()` در finally باشد
- [ ] تابع `get_db` در `backend/app/core/database.py` باید از الگوی `yield` با `try/finally` استفاده کند
- [ ] هیچ `SessionLocal()` بدون `try/finally` در کل پوشه `backend/app/` وجود نداشته باشد — grep سراسری باید نتیجه صفر برگرداند
- [ ] endpoint `POST /api/analysis/run-stream` باید بعد از اتمام تحلیل (موفق یا ناموفق) session را ببندد — قابل تست با بررسی connection pool
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **بررسی `backend/app/api/routes/analysis.py`**: تمام مکان‌هایی که `SessionLocal()` فراخوانی می‌شود را شناسایی کن. هر بلوک را با `try/finally` و `db.close()` در finally wrap کن. اگر از dependency injection فعلی FastAPI (`Depends(get_db)`) استفاده می‌شود، بررسی کن که generator آن `yield` دارد و `finally` در آن وجود دارد — اگر نه، اصلاح کن.

2. **بررسی `backend/app/api/routes/chat.py`**: همان الگو — جستجو برای `SessionLocal()` و wrap با `try/finally`.

3. **بررسی `backend/app/api/routes/github_import.py`**: این فایل طبق نقشه import‌ها از `backend/app/core/database.py` استفاده می‌کند. تمام نمونه‌سازی‌های `SessionLocal()` را پیدا و اصلاح کن.

4. **بررسی `backend/app/services/deep_analysis_service.py`**: در متد `run_full_analysis` (خط ۳۱۴)، `db_session` از بیرون می‌آید — اما اگر در داخل سرویس جایی `SessionLocal()` مستقیم ساخته می‌شود (مثلاً در `_save_analysis_results` خط ۵۴۳)، باید با `try/finally` wrap شود.

5. **بررسی `backend/app/core/database.py`**: اطمینان حاصل کن که تابع `get_db` (اگر وجود دارد) از الگوی `yield` با `try/finally` استفاده می‌کند — این الگوی استاندارد FastAPI است.

6. **جستجوی سراسری**: با `grep -rn 'SessionLocal()' backend/app/` تمام مکان‌های دیگر را پیدا کن و همه را بررسی کن.

7. **commit**: با پیام `fix(db): رفع نشت session با try/finally در analysis_db و سایر روترها`.

## 💡 نمونه‌های قبل/بعد
**رفع نشت session در route handler (الگوی کاربر)**

_قبل:_
```
# در یک route handler
analysis_db = SessionLocal()
result = analysis_db.query(AnalysisReport).filter(...).all()
# اگر exception رخ دهد، analysis_db.close() هرگز فراخوانی نمی‌شود
return result
```

_بعد:_
```
# در یک route handler
analysis_db = SessionLocal()
try:
    result = analysis_db.query(AnalysisReport).filter(...).all()
    return result
finally:
    analysis_db.close()
```

**الگوی استاندارد FastAPI با get_db generator**

_قبل:_
```
# در database.py — بدون finally
def get_db():
    db = SessionLocal()
    yield db
    # اگر exception رخ دهد، db.close() فراخوانی نمی‌شود
```

_بعد:_
```
# در database.py — با finally
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**رفع نشت در DeepAnalysisService caller**

_قبل:_
```
# در route handler که DeepAnalysisService را فراخوانی می‌کند
analysis_db = SessionLocal()
service = DeepAnalysisService(ai_manager=ai_manager, db_session=analysis_db)
result = await service.run_full_analysis(..., db_session=analysis_db)
# analysis_db.close() فراموش شده
```

_بعد:_
```
# در route handler که DeepAnalysisService را فراخوانی می‌کند
analysis_db = SessionLocal()
try:
    service = DeepAnalysisService(ai_manager=ai_manager, db_session=analysis_db)
    result = await service.run_full_analysis(..., db_session=analysis_db)
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/ | grep -v 'try:' | grep -v '#'`
- `grep -rn 'analysis_db' backend/app/api/routes/analysis.py`
- `python -m pytest backend/tests/ -v -k 'analysis or session' --tb=short`
- `python -m pytest backend/tests/test_runtime_verify_integration.py -v`
- `python -c "from backend.app.core.database import get_db; import inspect; print(inspect.getsource(get_db))"`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **تغییر `get_db` در `backend/app/core/database.py`**: این فایل توسط ۱۹ فایل import می‌شود — هر تغییر در signature یا رفتار `get_db` روی تمام روترها اثر می‌گذارد. اگر `get_db` قبلاً بدون `finally` بود و حالا اضافه شود، باید مطمئن شد که `Depends(get_db)` در همه روترها به‌درستی کار می‌کند.
۲. **async vs sync session**: `aiosqlite` در requirements.txt وجود دارد — اگر بعضی handler ها async هستند، باید از `AsyncSession` و `async with` به‌جای `try/finally` ساده استفاده شود. مخلوط کردن sync/async session می‌تواند deadlock ایجاد کند.
۳. **`DeepAnalysisService._db_session`**: این session در `__init__` ذخیره می‌شود (خط ۲۴۳) و در چندین متد (`_get_prompt_from_db`، `_start_prompt_execution`، `_complete_prompt_execution`) استفاده می‌شود. اگر caller session را زودتر ببندد، این متدها با `DetachedInstanceError` مواجه می‌شوند.
۴. **`background_scheduler.py`**: اگر تسک‌های پس‌زمینه از `SessionLocal()` استفاده می‌کنند، باید جداگانه بررسی شوند — چون lifecycle آن‌ها با request lifecycle متفاوت است.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 20: اضافه کردن finally block برای مدیریت ریسک در endpoint /api/analysis/run-stream

**Scope:** این بخش صرفاً به اضافه کردن یک finally block در endpoint /api/analysis/run-stream (فایل backend/app/api/routes/analysis.py) محدود می‌شود. هدف آن اطمینان از پاک‌سازی منابع (مانند بستن فایل‌ها یا اتصالات) حتی در صورت بروز خطا است. هیچ تغییر دیگری در منطق اعتبارسنجی ورودی یا مسیردهی انجام نمی‌شود. این مرحله مستقل از سایر تسک‌ها است.
**Key terms:** finally block, backend/app/api/routes/analysis.py, /api/analysis/run-stream

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
کم — فقط اضافه کردن finally block

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 8
  id: 49be9ac4-ed23-4874-975e-841175c6974b
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن finally block به endpoint /api/analysis/run-stream برای پاک‌سازی منابع

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:109-212` — `run_analysis_task` — این تابع درون generate_events تعریف شده است. متغیر analysis_db در خط ۱۱۷ ساخته می‌شود اما در finally block موجود (خطوط ۲۰۷-۲۱۲) بسته نمی‌شود — نشت اتصال دیتابیس.
  ```python
  async def run_analysis_task():
              nonlocal final_result
              try:
                  # دریافت AI Manager
                  ai_manager = get_ai_manager()
  
                  # 🔴 ایجاد db session برای استفاده از پرامپت‌های دیتابیس
                  from ...core.database import SessionLocal
                  analysis_db = SessionLocal()
  
                  # ساخت DeepAnalysisService با progress callback و db_session
                  deep_analyzer = DeepAnalysisService(
                      ai_manager=ai_manager,
                      progress_callback=progress_callback,
                      db_session=analysis_db  # 🔴 برای استفاده از پرامپت‌های دیتابیس
                  )
  ```
- `backend/app/api/routes/analysis.py:200-212` — `run_analysis_task.finally` — این finally block موجود است اما analysis_db.close() در آن غایب است. باید قبل از ارسال سیگنال done، session بسته شود.
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                  await progress_queue.put({
                      "event": "error",
                      "message": str(e),
                      "error": True
                  })
              finally:
                  # سیگنال اتمام
                  await progress_queue.put({
                      "event": "done",
                      "result": final_result if final_result else None
                  })
  ```
- `backend/app/api/routes/analysis.py:83-100` — `run_analysis_stream` — endpoint اصلی که باید finally block در تابع داخلی‌اش اصلاح شود.
  ```python
  @router.post("/run-stream")
  async def run_analysis_stream(request: AnalysisRequest):
      """
      اجرای تحلیل با استریم پیشرفت (Server-Sent Events)
      """
      import os
      from ...services.ai_manager import get_ai_manager
      from ...services.deep_analysis_service import DeepAnalysisService
  
      # صف برای ارسال رویدادها
      progress_queue: asyncio.Queue = asyncio.Queue()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI + SQLAlchemy (sync SessionLocal) + asyncio. تابع run_analysis_task یک coroutine است که با asyncio.create_task اجرا می‌شود. SessionLocal یک sync session است که در context async استفاده می‌شود — بستن آن با .close() در finally block استاندارد است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 116) — SessionLocal از این فایل import می‌شود (خط ۱۱۶ analysis.py). این فایل توسط ۱۹ فایل دیگر import می‌شود و مدیریت صحیح session در آن تعریف شده است.
- `backend/app/services/deep_analysis_service.py` (سطر 120) — DeepAnalysisService در خط ۱۲۰ analysis.py با analysis_db ساخته می‌شود. اگر session بدون بستن رها شود، این سرویس ممکن است state ناسازگار داشته باشد.
- `backend/app/services/ai_manager.py` (سطر 113) — get_ai_manager در خط ۱۱۳ فراخوانی می‌شود و در کنار analysis_db در همان try block قرار دارد — باید مطمئن شد ترتیب cleanup صحیح است.

## 🌐 نقشهٔ وابستگی‌ها
endpoint `/api/analysis/run-stream` در `backend/app/api/routes/analysis.py` از `SessionLocal` در `backend/app/core/database.py` (که ۱۹ فایل آن را import می‌کنند) برای ساخت `analysis_db` استفاده می‌کند. این session به `DeepAnalysisService` در `backend/app/services/deep_analysis_service.py` پاس داده می‌شود. اگر session بسته نشود، pool اتصالات SQLAlchemy تحت فشار قرار می‌گیرد. تغییر پیشنهادی فقط در `run_analysis_task` درون `generate_events` است و هیچ تأثیری بر `@router.post('/run')` (خطوط ۴۶-۸۰) یا سایر endpointها ندارد.

## 🔍 Context و وضعیت فعلی
در endpoint `/api/analysis/run-stream` واقع در فایل `backend/app/api/routes/analysis.py`، یک مشکل مدیریت منابع وجود دارد: شیء `analysis_db` (از نوع `SessionLocal`) که در خط ۱۱۷ ایجاد می‌شود، در صورت بروز خطا یا قطع اتصال SSE هرگز بسته نمی‌شود. این موضوع می‌تواند منجر به نشت اتصال دیتابیس (connection leak) شود.

بر اساس کد موجود در خطوط ۱۱۵–۱۲۴، یک `SessionLocal` با نام `analysis_db` ساخته شده و به `DeepAnalysisService` پاس داده می‌شود، اما هیچ `finally` block یا `try/finally` ای برای بستن این session وجود ندارد. تابع `run_analysis_task` (خطوط ۱۰۹–۲۱۲) یک `try/except/finally` دارد که فقط سیگنال `done` را ارسال می‌کند، اما `analysis_db.close()` در آن غایب است.

هدف این تسک صرفاً اضافه کردن یک `finally` block در تابع `run_analysis_task` (درون `generate_events`) است تا `analysis_db.close()` حتی در صورت بروز exception یا اتمام طبیعی فراخوانی شود. هیچ تغییر دیگری در منطق اعتبارسنجی ورودی، مسیردهی، یا ساختار SSE انجام نمی‌شود. این تسک مستقل از سایر تسک‌هاست (id: 49be9ac4-ed23-4874-975e-841175c6974b).

کلیدواژه‌های اصلی: `finally block`, `backend/app/api/routes/analysis.py`, `/api/analysis/run-stream`, `SessionLocal`, `analysis_db`, `DeepAnalysisService`.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] متغیر analysis_db با مقدار اولیه None قبل از try block تعریف شده باشد (خط قبل از try در run_analysis_task)
- [ ] در finally block تابع run_analysis_task، دستور analysis_db.close() با guard مناسب (if analysis_db is not None) وجود داشته باشد
- [ ] endpoint POST /api/analysis/run-stream همچنان پاسخ ۲۰۰ با content-type text/event-stream برمی‌گرداند
- [ ] در صورت بروز exception در run_analysis_task، سیگنال done همچنان در progress_queue قرار می‌گیرد (رفتار قبلی حفظ شده باشد)
- [ ] بستن analysis_db در یک try/except جداگانه داخل finally انجام شود تا خطای close باعث از دست رفتن سیگنال done نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. فایل `backend/app/api/routes/analysis.py` را باز کن.
۲. تابع `run_analysis_task` را در خطوط ۱۰۹–۲۱۲ پیدا کن.
۳. در بلوک `finally` موجود (خطوط ۲۰۷–۲۱۲)، دستور `analysis_db.close()` را اضافه کن — قبل از `await progress_queue.put({"event": "done", ...})`.
۴. برای اطمینان بیشتر، متغیر `analysis_db` را با مقدار اولیه `None` تعریف کن و در finally با `if analysis_db:` چک کن تا در صورتی که session اصلاً ساخته نشده باشد، خطا ندهد.
۵. هیچ تغییری در منطق SSE، `generate_events`، یا `StreamingResponse` انجام نده.
۶. تست دستی: endpoint را با یک درخواست معتبر و یک درخواست که در میانه قطع می‌شود فراخوانی کن و مطمئن شو connection leak رخ نمی‌دهد.

## 💡 نمونه‌های قبل/بعد
**افزودن finally block برای بستن analysis_db**

_قبل:_
```
async def run_analysis_task():
            nonlocal final_result
            try:
                ai_manager = get_ai_manager()
                from ...core.database import SessionLocal
                analysis_db = SessionLocal()
                deep_analyzer = DeepAnalysisService(
                    ai_manager=ai_manager,
                    progress_callback=progress_callback,
                    db_session=analysis_db
                )
                # ... rest of logic ...
            except Exception as e:
                logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                await progress_queue.put({"event": "error", "message": str(e), "error": True})
            finally:
                await progress_queue.put({"event": "done", "result": final_result if final_result else None})
```

_بعد:_
```
async def run_analysis_task():
            nonlocal final_result
            analysis_db = None
            try:
                ai_manager = get_ai_manager()
                from ...core.database import SessionLocal
                analysis_db = SessionLocal()
                deep_analyzer = DeepAnalysisService(
                    ai_manager=ai_manager,
                    progress_callback=progress_callback,
                    db_session=analysis_db
                )
                # ... rest of logic ...
            except Exception as e:
                logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                await progress_queue.put({"event": "error", "message": str(e), "error": True})
            finally:
                if analysis_db is not None:
                    try:
                        analysis_db.close()
                    except Exception as close_err:
                        logger.warning(f"Failed to close analysis_db: {close_err}")
                await progress_queue.put({"event": "done", "result": final_result if final_result else None})
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k 'analysis' -v`
- `grep -n 'analysis_db' backend/app/api/routes/analysis.py`
- `grep -n 'finally' backend/app/api/routes/analysis.py`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. اگر analysis_db.close() بدون guard اجرا شود و session هرگز ساخته نشده باشد (مثلاً get_ai_manager خطا داد)، AttributeError روی None رخ می‌دهد — با مقداردهی اولیه None و چک if analysis_db is not None برطرف می‌شود. ۲. اگر close() خودش exception بدهد و در finally اصلی catch نشود، سیگنال done هرگز ارسال نمی‌شود و SSE client منتظر می‌ماند — با try/except جداگانه دور close() برطرف می‌شود. ۳. این تغییر فقط روی run_analysis_task اثر دارد و endpoint /api/analysis/run (خطوط ۴۶-۸۰) که از get_project_analyzer استفاده می‌کند تحت تأثیر نیست.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 21: بررسی اولیه و مستندسازی وضعیت موجود repo قبل از هرگونه تغییر

**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن الزام مدل به بررسی مستقل repo، شناسایی پیاده‌سازی‌های قبلی، و جلوگیری از بازسازی موارد موجود است. این بخش به‌تنهایی یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک برای کل فرآیند است. اگر تمام درخواست‌های بعدی قبلاً پیاده‌سازی شده باشند، باید یک کامیت no-op با توضیح ثبت شود.

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
بررسی و مستندسازی وضعیت موجود repo قبل از تغییر

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:1-23` — `router (APIRouter prefix=/analysis)` — این فایل نقطه مرجع اصلی برای بررسی وضعیت analysis routes است. قبل از هر تغییر در analysis، باید تمام 706 خط این فایل خوانده شود تا از تکرار پیاده‌سازی جلوگیری شود.
  ```python
  """
  API Routes for Project Analysis
  مسیرهای API برای تحلیل پروژه و پروفایل مدل‌ها
  """
  
  from fastapi import APIRouter, HTTPException, BackgroundTasks
  from fastapi.responses import StreamingResponse
  from typing import List, Optional
  from pydantic import BaseModel
  import logging
  import json
  import asyncio
  
  from ...services.project_analyzer import get_project_analyzer
  from ...services.model_profiler import get_model_profiler
  
  router = APIRouter(prefix="/analysis", tags=["Analysis"])
  ```
- `backend/app/api/routes/github_import.py:94-183` — `import_repository (POST /github/import)` — این endpoint شامل auto_setup_project_memory و auto_register_watched است که ممکن است در درخواست‌های بعدی دوباره پیاده‌سازی شوند. باید قبل از هر تغییر بررسی شود.
  ```python
  @router.post("/import")
  async def import_repository(request: ImportRepoRequest):
      """
      Import کامل یک repository از GitHub
  
      - پشتیبانی از repo های public و private
      - برای private repos، توکن GitHub لازم است
      - فایل‌های بزرگ و باینری فیلتر می‌شوند
      """
      service = get_github_import_service()
  
      # دریافت توکن مناسب
      token = get_effective_token(request.token, request.use_global_token)
  ```
- `backend/app/api/routes/model_profiles.py:142-227` — `get_all_profiles (GET /api/models/profiles)` — این فایل دارای defensive imports و fallback mechanism است. بررسی وضعیت این pattern قبل از تغییر ضروری است تا از شکستن fallback جلوگیری شود.
  ```python
  @router.get("/profiles")
  async def get_all_profiles(
      sort_by: str = Query("overall_score", description="فیلد مرتب‌سازی"),
      order: str = Query("desc", description="ترتیب: asc یا desc"),
      limit: int = Query(50, description="تعداد نتایج"),
      use_fallback: bool = Query(True, description="استفاده از داده‌های پیش‌فرض در صورت خالی بودن"),
      db=Depends(get_db)
  ):
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (backend) + Next.js 14 (frontend). Backend: Python با SQLAlchemy، Pydantic v2، asyncio، APScheduler. Frontend: React 18، TypeScript، Tailwind CSS، Zustand، axios. AI Services: claude_service، openai_service، gemini_service، deepseek_service، perplexity_service. Browser Automation: Playwright. این پروژه یک سیستم مدیریت پروژه با قابلیت‌های AI analysis، GitHub import، oversight، inspector، و runtime verification است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — هاب اصلی با 14 importer — هر تغییر در این فایل روی analysis.py، github_import.py، model_profiles.py، models.py، و oversight.py تأثیر مستقیم دارد. باید اول بررسی شود.
- `backend/app/services/ai_manager.py` (سطر 1) — هاب دوم با 11 importer — در analysis.py خط 113 (get_ai_manager) و در routes/models.py، orchestrator.py، oversight.py، project_health.py استفاده می‌شود. وضعیت این سرویس باید قبل از هر تغییر AI-related بررسی شود.
- `backend/app/models/project.py` (سطر 1) — هاب سوم با 9 importer — در github_import.py (Project, ProjectFile)، models.py، oversight.py، project_health.py، project_journal.py استفاده می‌شود. ساختار model باید قبل از تغییر schema بررسی شود.
- `backend/app/services/oversight_service.py` (سطر 1) — در github_import.py خط 161 (auto_register_watched)، oversight.py، render_logs.py، simple_projects.py، و main.py import می‌شود. آخرین کامیت‌ها نشان می‌دهند این سرویس اخیراً تغییر کرده — وضعیت فعلی باید مستند شود.
- `backend/app/main.py` (سطر 1) — entry point اصلی که oversight_service را import می‌کند و تمام routers را register می‌کند. بررسی این فایل نشان می‌دهد کدام routes فعال هستند و کدام ممکن است تکراری باشند.
- `backend/app/services/inspector_agent.py` (سطر 1) — بر اساس آخرین کامیت‌ها (7d341e3، bf98db1، cd39cc3)، inspector اخیراً تغییرات بنیادی داشته. این فایل باید برای شناسایی وضعیت فعلی inspector بررسی شود تا از تکرار fix های اخیر جلوگیری شود.

## 🌐 نقشهٔ وابستگی‌ها
این تسک یک فاز بررسی است که روی کل repo تأثیر دارد. فایل‌های هاب که باید اول بررسی شوند:

1. **backend/app/core/database.py** (14 importer): هر تغییر در SessionLocal یا get_db روی analysis.py، github_import.py، model_profiles.py، models.py، oversight.py تأثیر می‌گذارد.

2. **backend/app/services/ai_manager.py** (11 importer): get_ai_manager() در analysis.py خط 113، و در models.py، orchestrator.py، oversight.py، project_health.py استفاده می‌شود.

3. **backend/app/models/project.py** (9 importer): Project و ProjectFile در github_import.py، models.py، oversight.py، project_health.py، project_journal.py استفاده می‌شوند.

4. **backend/app/api/routes/project_journal.py** (6 importer): ActivityLog، Report، ReportTrigger در github_import.py خط 349-352 import می‌شوند.

5. **backend/app/services/oversight_service.py** (5 importer): auto_register_watched در github_import.py خط 170 call می‌شود.

آخرین کامیت‌ها (677c46f تا cd39cc3) نشان می‌دهند inspector_agent.py، render_service.py، و compare/verify buttons اخیراً تغییر کرده‌اند — این فایل‌ها باید با دقت بیشتری بررسی شوند.

## 🔍 Context و وضعیت فعلی
این تسک یک دستورالعمل متدولوژیک الزامی است که باید پیش از هرگونه تغییر در repo اجرا شود. بر اساس متن کاربر، این بخش «یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست» — وظیفه‌اش الزام مدل به بررسی مستقل repo، شناسایی پیاده‌سازی‌های قبلی، و جلوگیری از بازسازی موارد موجود است.

محور اصلی درخواست کاربر:
1. **احتمال پیاده‌سازی قبلی**: ممکن است بخشی یا تمامِ درخواست‌های بعدی قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشند. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط باید بررسی شود که چه چیزی از قبل وجود دارد.
2. **قاعده no-op**: اگر یک قابلیت/فایل/تابع از قبل موجود است، نباید دوباره ساخته شود — فقط موارد ناقص یا اشتباه اصلاح/تکمیل شوند. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت شود که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.
3. **مسئولیت مستقل مدل اجراکننده**: پیش از هر تغییر، ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها باید مستقل بررسی شوند. اگر تشخیص داده شد موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، باید بر اساس قضاوت مستقل عمل شود.
4. **کامل‌بودن اجرا**: اگر کار طولانی است، نباید خلاصه شود. همه باید به‌طور کامل انجام شود. اگر یک کامیت گنجایش ندارد، در چندین کامیت متوالی انجام شود — ولی هیچ بخشی skip نشود. ترتیب کامیت‌ها باید منطقی باشد: foundation → core → integration → tests.
5. **PR description**: در آخر یک checklist از همهٔ کامیت‌ها در PR description نوشته شود.

در کدبیس فعلی، آخرین کامیت‌ها نشان می‌دهند که تغییرات اخیر روی inspector، render، و compare/verify buttons بوده‌اند (کامیت‌های 677c46f، 7d341e3، bf98db1، cd39cc3). این context نشان می‌دهد repo در حال تکامل فعال است و احتمال وجود پیاده‌سازی‌های نیمه‌کاره یا تکراری بالاست. فایل‌های کلیدی مانند backend/app/api/routes/analysis.py (خطوط 1-706)، backend/app/api/routes/github_import.py (خطوط 1-644)، و backend/app/api/routes/model_profiles.py (خطوط 1-230) باید به‌عنوان نقاط مرجع اولیه بررسی شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] قبل از هر تغییر، grep -r روی backend/ و frontend/ اجرا شده و نتایج مستند شده‌اند — هیچ تغییری بدون این بررسی اولیه اعمال نمی‌شود
- [ ] اگر قابلیت درخواست‌شده از قبل در repo موجود است، یک کامیت no-op با پیام توضیحی ثبت شده که دقیقاً کدام فایل و خطوط آن را پوشش می‌دهند
- [ ] فایل‌های هاب (database.py با 14 importer، ai_manager.py با 11 importer، project.py با 9 importer) قبل از هر تغییر بررسی و وضعیت‌شان مستند شده است
- [ ] ترتیب کامیت‌ها منطقی است: foundation → core → integration → tests — هیچ کامیت integration قبل از foundation وجود ندارد
- [ ] PR description شامل checklist کامل از همه کامیت‌ها با وضعیت هر مورد (✅ انجام شد / ⏭️ no-op / 🔧 اصلاح شد) است
- [ ] هیچ تابع یا class موجود در backend/app/services/ دوباره ساخته نشده — فقط موارد ناقص تکمیل شده‌اند
- [ ] آخرین کامیت‌های inspector (7d341e3، bf98db1، cd39cc3) بررسی شده‌اند و تغییرات جدید با آن‌ها conflict ندارند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک یک فاز pre-execution است، نه یک تغییر کد مستقیم. مراحل اجرایی به شرح زیر است:

1. **اسکن ساختاری repo**: با استفاده از grep و file search، تمام فایل‌های موجود در backend/app/api/routes/، backend/app/services/، و frontend/src/ را فهرست کن و با ساختار مستند شده در پروژه مقایسه کن.

2. **شناسایی پیاده‌سازی‌های موجود**: برای هر درخواست بعدی، ابتدا با grep -r 'function_name\|class_name\|endpoint_path' backend/ frontend/ بررسی کن که آیا پیاده‌سازی قبلی وجود دارد.

3. **بررسی فایل‌های هاب**: فایل‌هایی که بیشترین import را دارند باید اول بررسی شوند:
   - backend/app/core/database.py (14 importer)
   - backend/app/services/ai_manager.py (11 importer)
   - backend/app/models/project.py (9 importer)
   - backend/app/api/routes/project_journal.py (6 importer)

4. **مستندسازی وضعیت**: یک فایل CURRENT_STATE.md یا comment در PR ایجاد کن که:
   - کدام فایل‌ها بررسی شدند
   - کدام قابلیت‌ها از قبل موجودند
   - کدام موارد ناقص یا نیازمند اصلاح هستند
   - کدام موارد کاملاً جدید هستند

5. **تصمیم‌گیری**: بر اساس بررسی:
   - اگر همه چیز موجود است → کامیت no-op با توضیح
   - اگر ناقص است → فقط تکمیل موارد ناقص
   - اگر جدید است → پیاده‌سازی کامل با ترتیب foundation → core → integration → tests

6. **PR description checklist**: در پایان، checklist کامل از همه کامیت‌ها با وضعیت هر مورد.

## 💡 نمونه‌های قبل/بعد
**نمونه کامیت no-op در صورت وجود پیاده‌سازی قبلی**

_قبل:_
```
# وضعیت: درخواست پیاده‌سازی feature X رسیده
# بدون بررسی اولیه، مستقیم شروع به کدنویسی می‌شود
# نتیجه: تکرار کد، conflict، یا override پیاده‌سازی موجود
```

_بعد:_
```
# وضعیت: بررسی اولیه انجام شد
# grep -r 'feature_x\|FeatureX' backend/ frontend/
# نتیجه: backend/app/services/feature_x.py موجود است (خطوط 45-120)
# تصمیم: no-op commit
# git commit -m 'chore: no-op — feature X already implemented in backend/app/services/feature_x.py (lines 45-120). No changes needed.'
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -r 'def ' backend/app/services/ | wc -l`
- `grep -r '@router\.' backend/app/api/routes/ | wc -l`
- `pytest backend/tests/test_inspector_oversight_bridge.py -v`
- `pytest backend/tests/test_runtime_verify_integration.py -v`
- `grep -r 'auto_setup_project_memory\|auto_register_watched' backend/ --include='*.py'`
- `grep -r 'SessionLocal\|get_db' backend/app/api/routes/ --include='*.py' | wc -l`

## ⚠️ ریسک‌ها و موارد احتیاط
1. **تکرار پیاده‌سازی در فایل‌های هاب**: backend/app/core/database.py توسط 14 فایل import می‌شود — هر تغییر بدون بررسی اولیه می‌تواند روی analysis.py، github_import.py، model_profiles.py، models.py، و oversight.py به‌طور همزمان اثر بگذارد.

2. **conflict با تغییرات اخیر inspector**: کامیت‌های 7d341e3 و bf98db1 تغییرات بنیادی در inspector داشته‌اند — هر تغییر جدید در inspector_agent.py یا inspector_scan_bridge.py بدون بررسی این کامیت‌ها می‌تواند regression ایجاد کند.

3. **auto_register_watched در github_import.py خط 170**: این تابع از oversight_service.py فراخوانی می‌شود که خود 5 importer دارد — تغییر در oversight_service.py می‌تواند import در github_import.py، render_logs.py، simple_projects.py، و main.py را بشکند.

4. **defensive imports در model_profiles.py**: این فایل از try/except برای import استفاده می‌کند (خطوط 23-48) — اگر پیاده‌سازی جدیدی این pattern را نادیده بگیرد، fallback mechanism شکسته می‌شود.

5. **project_journal.py با 6 importer**: ActivityLog، Report، ReportTrigger در github_import.py خط 349-352 با try/except import می‌شوند — تغییر schema این جداول می‌تواند delete cascade در github_import.py را بشکند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 22: اعتبارسنجی مسیر پروژه در endpoint run_analysis_stream

**Scope:** این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint run_analysis_stream است. مسیر باید از نظر وجود دایرکتوری، عدم وجود path traversal (مانند '..' یا '/') و محدود بودن به دایرکتوری‌های مجاز پروژه بررسی شود. همچنین باید از خواندن README از مسیرهای غیرمجاز جلوگیری کند. این مرحله شامل تغییر در backend/app/api/routes/analysis.py و احتمالاً backend/app/core/config.py برای تعریف مسیرهای مجاز است. تست‌های مربوطه در tests/test_analysis.py یا backend/tests/test_security.py اضافه می‌شوند.
**Key terms:** backend/app/api/routes/analysis.py, run_analysis_stream, project_path, os.walk, AnalysisRequest, backend/app/models/analysis_report.py, frontend/src/app/analysis/page.tsx, backend/app/core/config.py, tests/test_analysis.py, backend/tests/test_security.py

**بخش مربوط از متن کاربر:**
```
عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream

- `backend/app/api/routes/analysis.py:84-268` — `run_analysis_stream` — کل endpoint نیاز به validation مسیر دارد
  ```python
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      project_path = request.project_path  # ⚠️ user-supplied, no validation
      ...
      for root, dirs, filenames in os.walk(project_path):  # ⚠️ path traversal
  ```

FastAPI + Python os.walk + Pydantic models

- `backend/app/api/routes/analysis.py` (سطر 127) — محل اصلی آسیب‌پذیری
- `backend/app/models/analysis_report.py` (سطر 1) — مدل AnalysisRequest که project_path را تعریف می‌کند

این endpoint توسط frontend/src/app/analysis/page.tsx (خط 190) فراخوانی می‌شود. هیچ middleware یا dependency دیگری مسیر را قبل از رسیدن به این تابع validation نمی‌کند.

در فایل backend/app/api/routes/analysis.py، endpoint run_analysis_stream (خط 84) پارامتر project_path را مستقیماً از درخواست کاربر دریافت کرده و در os.walk (خط 160) بدون هیچ sanitization استفاده می‌کند. این آسیب‌پذیری Path Traversal امکان خواندن فایل‌های خارج از مسیر پروژه را فراهم می‌کند. همچنین در خط 133-141، README از مسیر user-supplied خوانده می‌شود. مهاجم می‌تواند با ارسال project_path='../../etc/' فایل‌های حساس سیستم را بخواند.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن اعتبارسنجی مسیر پروژه در endpoint run_analysis_stream

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
اعتبارسنجی مسیر پروژه در endpoint run_analysis_stream. این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint run_analysis_stream است. مسیر باید از نظر وجود دایرکتوری، عدم وجود path traversal (مانند '..' یا '/') و محدود بودن به دایرکتوری‌های مجاز پروژه بررسی شود. همچنین باید از خواندن README از مسیرهای غیرمجاز جلوگیری کند. این مرحله شامل تغییر در backend/app/api/routes/analysis.py و احتمالاً backend/app/core/config.py برای تعریف مسیرهای مجاز است. تست‌های مربوطه در tests/test_analysis.py یا backend/tests/test_security.py اضافه می‌شوند.

عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream

- `backend/app/api/routes/analysis.py:84-268` — `run_analysis_stream` — کل endpoint نیاز به validation مسیر دارد
  ```python
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      project_path = request.project_path  # ⚠️ user-supplied, no validation
      ...
      for root, dirs, filenames in os.walk(project_path):  # ⚠️ path traversal
  ```

FastAPI + Python os.walk + Pydantic models

- `backend/app/api/routes/analysis.py` (سطر 127) — محل اصلی آسیب‌پذیری
- `backend/app/models/analysis_report.py` (سطر 1) — مدل AnalysisRequest که project_path را تعریف می‌کند

این endpoint توسط frontend/src/app/analysis/page.tsx (خط 190) فراخوانی می‌شود. هیچ middleware یا dependency دیگری مسیر را قبل از رسیدن به این تابع validation نمی‌کند.

در فایل backend/app/api/routes/analysis.py، endpoint run_analysis_stream (خط 84) پارامتر project_path را مستقیماً از درخواست کاربر دریافت کرده و در os.walk (خط 160) بدون هیچ sanitization استفاده می‌کند. این آسیب‌پذیری Path Traversal امکان خواندن فایل‌های خارج از مسیر پروژه را فراهم می‌کند. همچنین در خط 133-141، README از مسیر user-supplied خوانده می‌شود. مهاجم می‌تواند با ارسال project_path='../../etc/' فایل‌های حساس سیستم را بخواند.

کلیدواژه‌ها: backend/app/api/routes/analysis.py, run_analysis_stream, project_path, os.walk, AnalysisRequest, backend/app/models/analysis_report.py, frontend/src/app/analysis/page.tsx, backend/app/core/config.py, tests/test_analysis.py, backend/tests/test_security.py

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در backend/app/core/config.py یک لیست از مسیرهای مجاز پروژه (ALLOWED_PROJECT_PATHS) تعریف کن که شامل دایرکتوری‌های استاندارد پروژه باشد.
2. در backend/app/api/routes/analysis.py، تابع کمکی validate_project_path(path: str) -> bool ایجاد کن که:
   - مسیر را با os.path.abspath نرمال کند
   - بررسی کند که مسیر نرمال شده با یکی از ALLOWED_PROJECT_PATHS شروع شود
   - بررسی کند که مسیر وجود داشته باشد و دایرکتوری باشد
   - از path traversal با چک کردن '..' و '/' جلوگیری کند
3. در ابتدای تابع run_analysis_stream (خط 84)، قبل از هر عملیات فایل، validate_project_path را فراخوانی کن و در صورت نامعتبر بودن HTTPException 400 برگردان.
4. خواندن README در خطوط 133-141 را نیز با همان مسیر معتبر محدود کن.
5. تست‌های مربوطه در backend/tests/test_security.py اضافه شوند که موارد زیر را پوشش دهند:
   - مسیر معتبر پروژه
   - مسیر با path traversal ('../../etc/')
   - مسیر غیرمجاز
   - مسیر وجود ندارد

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 23: افزودن اعتبارسنجی مسیر برای جلوگیری از Path Traversal در project_path

**Scope:** این بخش شامل پیاده‌سازی اعتبارسنجی مسیر در endpoint مربوط به project_path است. باید از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز (/app/projects) است استفاده شود. همچنین باید validation با Pydantic برای enforce کردن الگوی مسیر امن اضافه شود. تست واحد جدید برای path traversal باید اضافه شود و همه تست‌های موجود باید پاس شوند. linter و type-check نیز باید بدون مشکل عبور کنند.
**Key terms:** project_path, os.path.abspath, os.path.commonpath, /app/projects, Pydantic, backend/app/api/routes/analysis.py, backend/tests/test_security.py, backend/app/core/config.py

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path='../../etc/' با خطای 400 رد شود
- [ ] مسیرهای درون /app/projects مجاز باشند
- [ ] تست واحد جدید برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اضافه کردن اعتبارسنجی مسیر: 1) استفاده از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز است. 2) تعریف یک ریشه مجاز (مثلاً /projects یا /data) و reject کردن مسیرهای خارج از آن. 3) اضافه کردن validation با Pydantic برای project_path که الگوی مسیر امن را enforce کند.
```

## 🎯 هدف (خلاصه ساختاریافته)
اعتبارسنجی Path Traversal برای project_path در analysis endpoint

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — فیلد project_path بدون هیچ validator تعریف شده — باید Pydantic field_validator اضافه شود تا path traversal جلوگیری شود
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-165` — `run_analysis_stream` — project_path مستقیماً در os.path.join و os.walk استفاده می‌شود بدون هیچ sanitization — نقطه اصلی آسیب‌پذیری
  ```python
  project_path = request.project_path
                  files = []
  
                  # خواندن README اگر موجود باشد
                  readme_content = ""
                  readme_paths = ["README.md", "readme.md", "README.txt"]
                  for readme_name in readme_paths:
                      readme_path = os.path.join(project_path, readme_name)
                      if os.path.exists(readme_path):
                          try:
                              with open(readme_path, 'r', encoding='utf-8') as f:
                                  readme_content = f.read()
                              break
                          except:
                              pass
  ```
- `backend/app/core/config.py` — `ALLOWED_PROJECT_ROOT` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. باید متغیر ALLOWED_PROJECT_ROOT با مقدار پیش‌فرض /app/projects اضافه شود و تابع validate_project_path در اینجا تعریف شود
- `backend/tests/test_runtime_verify_stage1.py` — فایل تست موجود برای الگوگیری از ساختار تست‌های موجود — فایل جدید backend/tests/test_security.py باید با همین الگو ساخته شود

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. کتابخانه‌های مرتبط: Pydantic v2 (>=2.5.0 در requirements.txt) برای field_validator و model_validator، os.path از stdlib Python برای abspath/commonpath، pytest (>=7.4.0) برای تست‌های واحد، mypy برای type-check. در Pydantic v2 از `@field_validator` یا `Annotated` با `AfterValidator` استفاده می‌شود (نه `@validator` که Pydantic v1 بود).

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 30) — فایل اصلی که AnalysisRequest و هر دو endpoint run_analysis و run_analysis_stream را تعریف می‌کند — تغییر validator مستقیماً اینجاست
- `backend/app/core/config.py` (سطر 1) — باید ALLOWED_PROJECT_ROOT و تابع validate_project_path در اینجا تعریف شوند تا از یک نقطه مرکزی قابل import باشند — 16 فایل از database.py در همین پکیج import می‌کنند
- `backend/app/core/database.py` (سطر 1) — در همان پکیج core قرار دارد و توسط analysis.py import می‌شود (خط 116-117 analysis.py: from ...core.database import SessionLocal) — تغییر config.py باید با این فایل سازگار باشد
- `backend/app/api/routes/simple_projects.py` (سطر 1) — این فایل نیز project_path را در context مشابه استفاده می‌کند و از ai_manager و database import می‌کند — باید بررسی شود آیا همان آسیب‌پذیری وجود دارد
- `backend/app/services/deep_analysis_service.py` (سطر 1) — توسط analysis.py در خط 96 import می‌شود (from ...services.deep_analysis_service import DeepAnalysisService) و project_path را دریافت می‌کند — باید بررسی شود که validation در لایه route کافی است

## 🌐 نقشهٔ وابستگی‌ها
تابع `validate_project_path` که در `backend/app/core/config.py` تعریف می‌شود توسط `AnalysisRequest` در `backend/app/api/routes/analysis.py` (خط ۳۰) import و استفاده می‌شود. هر دو endpoint `run_analysis` (خط ۴۶) و `run_analysis_stream` (خط ۸۴) از همین مدل Pydantic استفاده می‌کنند، پس validation یک‌بار در مدل تعریف شده هر دو را cover می‌کند. `backend/app/services/deep_analysis_service.py` که توسط `run_analysis_stream` در خط ۱۲۰ instantiate می‌شود، `project_path` را از `request.project_path` دریافت می‌کند — اگر validation در لایه Pydantic انجام شود، این سرویس مسیر clean دریافت می‌کند. همچنین `backend/app/core/database.py` که توسط ۱۶ فایل import می‌شود در همان پکیج `core` قرار دارد و تغییر `config.py` نباید روی آن اثر بگذارد. تست‌های جدید در `backend/tests/test_security.py` باید با `pytest` اجرا شوند و با تست‌های موجود در `backend/tests/test_runtime_verify_stage1.py` و سایر فایل‌های test سازگار باشند.

## 🔍 Context و وضعیت فعلی
این تسک شامل پیاده‌سازی اعتبارسنجی مسیر (Path Traversal Prevention) در endpoint مربوط به `project_path` است. مشکل اصلی این است که در حال حاضر در `backend/app/api/routes/analysis.py`، فیلد `project_path` در کلاس `AnalysisRequest` (خط ۳۳) بدون هیچ‌گونه اعتبارسنجی پذیرفته می‌شود و مستقیماً در `run_analysis_stream` (خط ۱۲۷) به عنوان `project_path = request.project_path` استفاده می‌شود. این یعنی یک مهاجم می‌تواند مقدار `../../etc/passwd` یا `../../root/.ssh` را ارسال کند و به فایل‌های خارج از دایرکتوری مجاز دسترسی پیدا کند.

طبق درخواست کاربر، باید:
1. از `os.path.abspath` و `os.path.commonpath` برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز (`/app/projects`) است استفاده شود.
2. یک ریشه مجاز (مثلاً `/app/projects` یا `/data`) تعریف شود و مسیرهای خارج از آن reject شوند.
3. اعتبارسنجی با Pydantic برای `project_path` اضافه شود که الگوی مسیر امن را enforce کند.
4. ارسال `project_path='../../etc/'` باید با خطای 400 رد شود.
5. مسیرهای درون `/app/projects` مجاز باشند.
6. تست واحد جدید برای path traversal در `backend/tests/test_security.py` اضافه شود.
7. هیچ تستی fail نشود (`pytest`).
8. linter بدون warning عبور کند.
9. type-check موفق باشد (`mypy`).

کلیدواژه‌های مرتبط: `project_path`, `os.path.abspath`, `os.path.commonpath`, `/app/projects`, `Pydantic`, `backend/app/api/routes/analysis.py`, `backend/tests/test_security.py`, `backend/app/core/config.py`.

در کد فعلی `analysis.py` خط ۳۰-۳۵، کلاس `AnalysisRequest` فیلد `project_path: str` را بدون هیچ validator تعریف کرده است. همچنین در خط ۱۲۷ این مقدار مستقیماً به `os.walk(project_path)` در خط ۱۶۰ پاس داده می‌شود که خطر path traversal را کاملاً واقعی می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path='../../etc/' به POST /analysis/run-stream باید با خطای 400 یا 422 رد شود
- [ ] ارسال project_path='/app/projects/myproject' باید مجاز باشد و خطای validation ندهد
- [ ] تابع validate_project_path در backend/app/core/config.py تعریف شده باشد و با os.path.abspath و os.path.commonpath کار کند
- [ ] کلاس AnalysisRequest در analysis.py باید field_validator برای project_path داشته باشد
- [ ] تست‌های واحد path traversal در backend/tests/test_security.py باید pass شوند
- [ ] همه تست‌های موجود (backend/tests/) باید بدون fail باقی بمانند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **ایجاد تابع اعتبارسنجی مرکزی در `backend/app/core/config.py`**: یک تابع `validate_project_path(path: str) -> str` اضافه کن که با `os.path.abspath` مسیر را normalize کند، سپس با `os.path.commonpath([abs_path, ALLOWED_ROOT])` بررسی کند که مسیر درون `ALLOWED_ROOT` (مثلاً `/app/projects`) باشد. اگر خارج بود، `ValueError` raise کند.

2. **اضافه کردن Pydantic validator به `AnalysisRequest` در `backend/app/api/routes/analysis.py` خط ۳۰-۳۵**: فیلد `project_path` را با `@field_validator('project_path')` یا `Annotated[str, AfterValidator(...)]` تجهیز کن تا قبل از رسیدن به business logic، مسیر validate شود و در صورت نامعتبر بودن، FastAPI به‌صورت خودکار 422 (یا با HTTPException دستی 400) برگرداند.

3. **تعریف `ALLOWED_PROJECT_ROOT` در `backend/app/core/config.py`**: یک متغیر محیطی با مقدار پیش‌فرض `/app/projects` تعریف کن تا در محیط‌های مختلف (dev/prod) قابل تنظیم باشد.

4. **اعمال همان validation در `run_analysis` (خط ۴۶) و `run_analysis_stream` (خط ۸۴)**: هر دو endpoint از `request.project_path` استفاده می‌کنند — validator در مدل Pydantic هر دو را cover می‌کند.

5. **نوشتن تست‌های واحد در `backend/tests/test_security.py`** (فایل جدید): تست‌هایی برای موارد زیر:
   - `project_path='../../etc/'` → 400/422
   - `project_path='/app/projects/myproject'` → مجاز
   - `project_path='/app/projects/../../../etc'` → 400/422
   - `project_path='/tmp/evil'` → 400/422

6. **اجرای `pytest backend/tests/test_security.py` و `mypy backend/app/api/routes/analysis.py backend/app/core/config.py`** برای تأیید.

## 💡 نمونه‌های قبل/بعد
**AnalysisRequest بدون validation (فعلی) vs با validation (پیشنهادی)**

_قبل:_
```
class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None
```

_بعد:_
```
from pydantic import field_validator
from ..core.config import validate_project_path

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None

    @field_validator('project_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        try:
            return validate_project_path(v)
        except ValueError as e:
            raise ValueError(str(e)) from e
```

**تابع validate_project_path در config.py (جدید)**

_قبل:_
```
# هیچ تابع validate_project_path در config.py وجود ندارد
```

_بعد:_
```
import os

ALLOWED_PROJECT_ROOT: str = os.environ.get("ALLOWED_PROJECT_ROOT", "/app/projects")

def validate_project_path(path: str) -> str:
    """اعتبارسنجی مسیر پروژه برای جلوگیری از Path Traversal."""
    abs_path = os.path.abspath(path)
    allowed = os.path.abspath(ALLOWED_PROJECT_ROOT)
    try:
        common = os.path.commonpath([abs_path, allowed])
    except ValueError:
        raise ValueError(f"مسیر نامعتبر: {path}")
    if common != allowed:
        raise ValueError(
            f"مسیر '{path}' خارج از دایرکتوری مجاز '{ALLOWED_PROJECT_ROOT}' است"
        )
    return abs_path
```

**تست واحد path traversal در test_security.py (جدید)**

_قبل:_
```
# فایل backend/tests/test_security.py وجود ندارد
```

_بعد:_
```
import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import validate_project_path

def test_path_traversal_rejected():
    with pytest.raises(ValueError):
        validate_project_path('../../etc/')

def test_path_traversal_with_absolute_rejected():
    with pytest.raises(ValueError):
        validate_project_path('/app/projects/../../../etc/passwd')

def test_valid_path_accepted():
    result = validate_project_path('/app/projects/myproject')
    assert result == '/app/projects/myproject'

def test_tmp_path_rejected():
    with pytest.raises(ValueError):
        validate_project_path('/tmp/evil')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_security.py -v`
- `pytest backend/tests/ -v --tb=short`
- `mypy backend/app/api/routes/analysis.py backend/app/core/config.py --ignore-missing-imports`
- `ruff check backend/app/api/routes/analysis.py backend/app/core/config.py`

## ⚠️ ریسک‌ها و موارد احتیاط
1. **تأثیر روی هر دو endpoint**: تغییر `AnalysisRequest` در `analysis.py` هم `run_analysis` (خط ۴۶) و هم `run_analysis_stream` (خط ۸۴) را تحت تأثیر قرار می‌دهد — هر دو از همین مدل استفاده می‌کنند. اگر validator خیلی سخت‌گیر باشد، ممکن است مسیرهای dev-local (مثل `/home/user/projects/...`) را هم رد کند.
2. **مقدار ALLOWED_PROJECT_ROOT در محیط‌های مختلف**: اگر در محیط development مسیر پروژه‌ها `/app/projects` نباشد، تمام تست‌های integration شکست می‌خورند. باید env var قابل override باشد.
3. **Pydantic v2 vs v1**: پروژه از Pydantic >=2.5.0 استفاده می‌کند (requirements.txt) — باید از `@field_validator` (v2) استفاده شود نه `@validator` (v1 deprecated). اشتباه در این مورد باعث warning یا خطای runtime می‌شود.
4. **تأثیر روی simple_projects.py**: این فایل نیز ممکن است project_path را handle کند — باید بررسی شود که آیا همان آسیب‌پذیری وجود دارد و آیا validate_project_path باید آنجا هم اعمال شود.
5. **os.path.commonpath روی Windows**: اگر محیط dev ویندوز باشد، رفتار `commonpath` با `/` prefix متفاوت است — اما چون پروژه روی Docker/Linux deploy می‌شود (Dockerfile موجود است)، این ریسک در production وجود ندارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 24: اضافه کردن اعتبارسنجی مسیر پروژه در endpoint تحلیل

**Scope:** این مرحله شامل افزودن validation برای پارامتر project_path در endpoint مربوط به تحلیل پروژه است. مسیر باید به یک دایرکتوری مجاز (ALLOWED_BASE) محدود شود تا از دسترسی به فایل‌های خارج از محدوده جلوگیری شود. تغییرات فقط در فایل backend/app/api/routes/analysis.py اعمال می‌شود. تست‌های امنیتی مرتبط در backend/tests/test_security.py باید به‌روزرسانی شوند. این مرحله شامل تغییرات frontend یا سایر سرویس‌ها نیست.
**Key terms:** backend/app/api/routes/analysis.py, project_path, ALLOWED_BASE, Path, HTTPException, os.walk, backend/tests/test_security.py

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**اضافه کردن validation مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
from pathlib import Path

ALLOWED_BASE = Path('/app/projects').resolve()
user_path = Path(request.project_path).resolve()
if not str(user_path).startswith(str(ALLOWED_BASE)):
    raise HTTPException(400, 'Invalid project path')
project_path = str(user_path)
for root, dirs, filenames in os.walk(project_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
from pathlib import Path

ALLOWED_BASE = Path('/app/projects').resolve()
user_path = Path(request.project_path).resolve()
if not str(user_path).startswith(str(ALLOWED_BASE)):
    raise HTTPException(400, 'Invalid project path')
project_path = str(user_path)
for root, dirs, filenames in os.walk(project_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
backend/app/api/routes/analysis.py, project_path, ALLOWED_BASE, Path, HTTPException, os.walk, backend/tests/test_security.py
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن اعتبارسنجی مسیر project_path در endpoint تحلیل

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py` — `project_path usage in analysis endpoint` — این فایل deep-read شده است. محل دقیق استفاده از `request.project_path` و `os.walk(project_path)` باید در این فایل یافت شود. بر اساس نمونه کد کاربر، کد فعلی به شکل `project_path = request.project_path` و سپس `for root, dirs, filenames in os.walk(project_path):` است. validation block باید بلافاصله بعد از دریافت `request.project_path` و قبل از `os.walk` اضافه شود.
- `backend/tests/test_security.py` — `test_project_path_validation` — این فایل در ساختار پروژه موجود نیست (فقط test_code_content_searcher.py، test_inspector_oversight_bridge.py و سایر test‌ها موجودند). باید ایجاد شود. تست‌های path traversal، مسیر معتبر، و مسیر خارج از ALLOWED_BASE باید در این فایل نوشته شوند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (backend) + Next.js (frontend). کتابخانه‌های مرتبط: `pathlib.Path` (stdlib Python)، `fastapi.HTTPException`، `os.walk` (stdlib). پروژه از `pydantic>=2.5.0` برای validation مدل‌ها استفاده می‌کند — می‌توان validator سطح Pydantic هم اضافه کرد. Python version: بر اساس requirements.txt از `python-jose`، `passlib` و `playwright` استفاده می‌شود که Python 3.8+ را نشان می‌دهد. `pathlib.Path.resolve()` در Python 3.6+ موجود است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — توسط analysis.py import می‌شود (طبق نقشه import‌های داخلی — ۱۰ فایل آن را import می‌کنند از جمله analysis.py). تغییر در analysis.py نباید این dependency را بشکند.
- `backend/app/services/ai_manager.py` (سطر 1) — توسط analysis.py import می‌شود (طبق نقشه import‌های داخلی). اگر endpoint تحلیل از ai_manager برای پردازش فایل‌های پروژه استفاده می‌کند، validation باید قبل از فراخوانی ai_manager اعمال شود.
- `backend/app/models/ai_profile.py` (سطر 1) — توسط analysis.py import می‌شود (طبق نقشه import‌های داخلی). مدل‌های request/response تحلیل ممکن است فیلد project_path را در خود داشته باشند — باید بررسی شود آیا validation در لایه model هم لازم است.
- `backend/app/services/model_profiler.py` (سطر 1) — توسط analysis.py import می‌شود (طبق نقشه import‌های داخلی). اگر model_profiler هم مسیر پروژه را دریافت می‌کند، باید بررسی شود که validated path به آن پاس داده شود نه raw input.
- `backend/app/core/config.py` (سطر 1) — مقدار ALLOWED_BASE ('/app/projects') بهتر است از config خوانده شود نه hardcode باشد. این فایل تنظیمات محیطی پروژه را نگه می‌دارد و می‌تواند PROJECTS_BASE_PATH را expose کند.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/api/routes/analysis.py` یکی از route‌های اصلی پروژه است که در نقشه import‌های داخلی به‌عنوان یکی از ۵ فایل import‌کننده `backend/app/core/database.py` شناسایی شده. همچنین `backend/app/services/ai_manager.py` (که ۹ فایل آن را import می‌کنند)، `backend/app/models/ai_profile.py` (که ۵ فایل آن را import می‌کنند) و `backend/app/services/model_profiler.py` (که ۵ فایل آن را import می‌کنند) توسط این فایل استفاده می‌شوند. تغییر validation در analysis.py تأثیر مستقیمی روی سایر فایل‌ها ندارد چون validation یک لایه guard است، اما اگر `ALLOWED_BASE` از `backend/app/core/config.py` خوانده شود، وابستگی جدیدی ایجاد می‌شود. فایل `backend/tests/test_security.py` باید از صفر ایجاد شود چون در ساختار فعلی پروژه وجود ندارد.

## 🔍 Context و وضعیت فعلی
این تسک شامل افزودن validation امنیتی برای پارامتر `project_path` در endpoint مربوط به تحلیل پروژه در فایل `backend/app/api/routes/analysis.py` است. مشکل اصلی این است که در حال حاضر مسیر ورودی کاربر (`request.project_path`) بدون هیچ‌گونه بررسی مرزی مستقیماً به `os.walk` داده می‌شود، که این یک آسیب‌پذیری Path Traversal (CWE-22) محسوب می‌شود و به مهاجم اجازه می‌دهد با ارسال مسیرهایی مثل `../../etc/passwd` به فایل‌های خارج از محدوده مجاز دسترسی پیدا کند.

راه‌حل پیشنهادی کاربر: تعریف یک ثابت `ALLOWED_BASE = Path('/app/projects').resolve()` و سپس resolve کردن مسیر ورودی با `Path(request.project_path).resolve()` و بررسی اینکه آیا مسیر resolve‌شده با `str(user_path).startswith(str(ALLOWED_BASE))` درون محدوده مجاز قرار دارد یا نه. در صورت خروج از محدوده، باید `HTTPException(400, 'Invalid project path')` raise شود.

کلیدواژه‌های اصلی از متن کاربر: `backend/app/api/routes/analysis.py`، `project_path`، `ALLOWED_BASE`، `Path`، `HTTPException`، `os.walk`، `backend/tests/test_security.py`.

تغییرات فقط در فایل `backend/app/api/routes/analysis.py` اعمال می‌شود و تست‌های امنیتی مرتبط در `backend/tests/test_security.py` باید به‌روزرسانی شوند. این تسک شامل تغییرات frontend یا سایر سرویس‌ها نیست.

بر اساس ساختار پروژه، `backend/app/api/routes/analysis.py` یکی از route‌های اصلی است که توسط `backend/app/core/database.py`، `backend/app/services/ai_manager.py`، `backend/app/models/ai_profile.py` و `backend/app/services/model_profiler.py` import می‌شود. این فایل در نقشه import‌های داخلی به‌عنوان یکی از ۵ فایل اصلی که `database.py` را import می‌کنند شناسایی شده است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path با مقدار '../../etc/passwd' به endpoint تحلیل باید HTTP 400 با detail 'Invalid project path' برگرداند
- [ ] ارسال project_path با مقدار '/tmp/evil' (مسیر absolute خارج از ALLOWED_BASE) باید HTTP 400 برگرداند
- [ ] ثابت ALLOWED_BASE در analysis.py تعریف شده و از pathlib.Path استفاده می‌کند
- [ ] validation block با startswith check در analysis.py وجود دارد و HTTPException raise می‌کند
- [ ] تست‌های backend/tests/test_security.py همگی pass شوند
- [ ] ارسال project_path معتبر درون /app/projects باید endpoint را بدون خطای 400 اجرا کند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **باز کردن `backend/app/api/routes/analysis.py`** و یافتن محل استفاده از `request.project_path` و `os.walk(project_path)`.
2. **افزودن import‌های لازم** در ابتدای فایل: `import os` (اگر موجود نیست)، `from pathlib import Path`، و اطمینان از وجود `from fastapi import HTTPException`.
3. **تعریف ثابت `ALLOWED_BASE`** در سطح ماژول (بعد از import‌ها، قبل از router): `ALLOWED_BASE = Path('/app/projects').resolve()`
4. **جایگزینی کد ناامن** با validation block:
   ```python
   user_path = Path(request.project_path).resolve()
   if not str(user_path).startswith(str(ALLOWED_BASE)):
       raise HTTPException(status_code=400, detail='Invalid project path')
   project_path = str(user_path)
   ```
5. **بررسی تمام endpoint‌های analysis.py** که از `project_path` استفاده می‌کنند — ممکن است بیش از یک endpoint این پارامتر را دریافت کند.
6. **ایجاد یا به‌روزرسانی `backend/tests/test_security.py`** با تست‌های زیر:
   - تست path traversal با `../../etc/passwd`
   - تست مسیر معتبر درون `ALLOWED_BASE`
   - تست مسیر absolute خارج از `ALLOWED_BASE`
   - تست مسیر با symlink (اگر لازم باشد)
7. **اجرای `pytest backend/tests/test_security.py`** برای تأیید pass شدن تست‌ها.

## 💡 نمونه‌های قبل/بعد
**validation مسیر پروژه در endpoint تحلیل (analysis.py)**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
from pathlib import Path
from fastapi import HTTPException

ALLOWED_BASE = Path('/app/projects').resolve()

# داخل endpoint handler:
user_path = Path(request.project_path).resolve()
if not str(user_path).startswith(str(ALLOWED_BASE)):
    raise HTTPException(status_code=400, detail='Invalid project path')
project_path = str(user_path)
for root, dirs, filenames in os.walk(project_path):
```

**تست امنیتی در test_security.py**

_قبل:_
```
# فایل وجود ندارد
```

_بعد:_
```
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_path_traversal_rejected():
    res = client.post('/api/analysis/...', json={'project_path': '../../etc/passwd'})
    assert res.status_code == 400
    assert 'Invalid project path' in res.json()['detail']

def test_valid_path_accepted():
    res = client.post('/api/analysis/...', json={'project_path': '/app/projects/my_project'})
    assert res.status_code != 400

def test_absolute_path_outside_base_rejected():
    res = client.post('/api/analysis/...', json={'project_path': '/tmp/evil'})
    assert res.status_code == 400
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_security.py -v`
- `pytest backend/tests/ -v -k 'security or path'`
- `grep -n 'ALLOWED_BASE\|startswith\|Invalid project path' backend/app/api/routes/analysis.py`
- `grep -n 'os.walk\|project_path' backend/app/api/routes/analysis.py`

## ⚠️ ریسک‌ها و موارد احتیاط
1. **Hardcode مسیر `/app/projects`**: اگر در محیط development مسیر پروژه‌ها متفاوت باشد (مثلاً `/home/user/projects`)، validation همه درخواست‌های dev را رد می‌کند. راه‌حل: خواندن `ALLOWED_BASE` از `backend/app/core/config.py` یا environment variable.
2. **چند endpoint در analysis.py**: اگر فایل `backend/app/api/routes/analysis.py` بیش از یک endpoint دارد که `project_path` می‌گیرد، باید validation در همه آن‌ها اعمال شود — نه فقط یکی.
3. **Symlink bypass**: `Path.resolve()` symlink‌ها را دنبال می‌کند، اما اگر symlink به خارج از `ALLOWED_BASE` اشاره کند، `startswith` آن را رد می‌کند — این رفتار صحیح است ولی باید مستند شود.
4. **وابستگی به `backend/app/services/ai_manager.py`**: این سرویس که توسط analysis.py استفاده می‌شود ممکن است خودش هم `project_path` را به توابع دیگر پاس دهد — باید بررسی شود validated path تا انتها منتقل می‌شود.
5. **فایل `backend/tests/test_security.py` وجود ندارد**: باید از صفر ایجاد شود و endpoint دقیق analysis برای تست مشخص شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 25: اجرای دستورات اعتبارسنجی امنیتی برای مسیرهای فایل

**Scope:** این بخش شامل دو دستور اعتبارسنجی است: (1) یک درخواست curl برای تست endpoint تحلیل با مسیر فایل مخرب (path traversal) و (2) اجرای تست pytest مخصوص آسیب‌پذیری path traversal. هدف این مرحله تأیید امنیت endpoint در برابر حملات path traversal است. این بخش صرفاً دستورات تست را مشخص می‌کند و شامل پیاده‌سازی کد یا تغییر در فایل‌ها نیست.
**Key terms:** backend/tests/test_security.py, path_traversal, /api/analysis/run-stream, project_path

**بخش مربوط از متن کاربر:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc/"}'`
- `pytest backend/tests/test_security.py -k path_traversal`
```

## 🎯 هدف (خلاصه ساختاریافته)
اعتبارسنجی امنیتی endpoint تحلیل در برابر حملات path traversal

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:127-165` — `run_analysis_stream` — نقطه اصلی آسیب‌پذیری: project_path بدون هیچ اعتبارسنجی مستقیماً در os.walk استفاده می‌شود. ارسال '../../etc/' باعث می‌شود سیستم فایل‌های خارج از محدوده مجاز را بخواند.
  ```python
  project_path = request.project_path
                  files = []
  
                  # خواندن README اگر موجود باشد
                  readme_content = ""
                  readme_paths = ["README.md", "readme.md", "README.txt"]
                  for readme_name in readme_paths:
                      readme_path = os.path.join(project_path, readme_name)
                      if os.path.exists(readme_path):
                  ...
                  for root, dirs, filenames in os.walk(project_path):
  ```
- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — مدل Pydantic درخواست — فیلد project_path هیچ validator ندارد. باید @validator یا field_validator اضافه شود که path traversal را رد کند.
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  ```
- `backend/tests/test_security.py` — `test_path_traversal` — این فایل در ساختار پروژه وجود ندارد — مجری باید آن را ایجاد کند. تست‌های path_traversal باید شامل: ارسال '../../etc/'، '/etc/passwd'، '../../../root' به عنوان project_path باشند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI + Next.js 14. Backend: Python با Pydantic v2 برای validation مدل‌ها، SQLAlchemy برای ORM، pytest برای تست. فیلد project_path از نوع str در Pydantic BaseModel — می‌توان با @field_validator یا Annotated[str, AfterValidator(...)] path traversal را block کرد. os.path.realpath و os.path.commonpath ابزارهای استاندارد Python برای تشخیص path traversal هستند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 84) — فایل اصلی حاوی endpoint /api/analysis/run-stream و /api/analysis/run — هر دو از project_path استفاده می‌کنند بدون validation
- `backend/app/api/routes/security_analysis.py` (سطر 39) — روتر امنیتی پروژه — endpoint های scan-secrets و full-report از project_id استفاده می‌کنند اما الگوی مشابه path handling دارند؛ باید بررسی شود
- `backend/app/services/content_sanitizer.py` (سطر 1) — ماژول sanitization موجود در پروژه — می‌تواند الگوی مناسب برای path sanitization باشد؛ CODE_EXTENSIONS و validation patterns در آن تعریف شده
- `backend/app/core/database.py` (سطر 1) — 18 فایل آن را import می‌کنند از جمله analysis.py — SessionLocal در run_analysis_stream (خط 117) استفاده می‌شود
- `backend/tests/test_runtime_verify_integration.py` (سطر 1) — نمونه تست integration موجود در پروژه — الگوی نوشتن تست‌های backend برای راهنمایی ساخت test_security.py

## 🌐 نقشهٔ وابستگی‌ها
endpoint `/api/analysis/run-stream` در `backend/app/api/routes/analysis.py` (خط ۸۴) توسط `backend/app/main.py` register می‌شود. این endpoint از `DeepAnalysisService` (خط ۱۲۰) و `get_ai_manager` (خط ۱۱۳) استفاده می‌کند. فیلد `project_path` در `AnalysisRequest` (خط ۳۳) بدون validator تعریف شده و مستقیماً به `os.walk()` (خط ۱۶۰) و `os.path.join()` (خط ۱۳۴) پاس می‌شود. endpoint `/api/analysis/run` (خط ۴۶) نیز همین مدل را استفاده می‌کند. فایل `backend/tests/test_security.py` در ساختار پروژه وجود ندارد و باید ایجاد شود. تست‌های موجود در `backend/tests/` شامل test_runtime_verify_* هستند که الگوی مناسبی برای ساخت تست امنیتی ارائه می‌دهند.

## 🔍 Context و وضعیت فعلی
کاربر درخواست اجرای دو دستور اعتبارسنجی امنیتی برای تأیید مقاومت endpoint `/api/analysis/run-stream` در برابر حملات path traversal دارد. دستور اول یک curl POST به `http://localhost:8000/api/analysis/run-stream` با payload مخرب `{"project_id":"test","project_path":"../../etc/"}` است که هدفش بررسی رفتار endpoint هنگام دریافت مسیر فایل مخرب (path traversal) می‌باشد. دستور دوم اجرای `pytest backend/tests/test_security.py -k path_traversal` است که تست‌های مخصوص آسیب‌پذیری path traversal را اجرا می‌کند.

بررسی کد واقعی نشان می‌دهد که در `backend/app/api/routes/analysis.py` خط ۱۲۷، مقدار `project_path = request.project_path` بدون هیچ اعتبارسنجی یا sanitization مستقیماً در `os.walk(project_path)` (خط ۱۶۰) استفاده می‌شود. این یعنی یک مهاجم می‌تواند با ارسال `../../etc/` به عنوان `project_path`، به فایل‌های خارج از محدوده مجاز دسترسی پیدا کند. همچنین فایل `backend/tests/test_security.py` در ساختار پروژه وجود ندارد و باید ایجاد شود. فایل `backend/app/api/routes/security_analysis.py` نیز endpoint های مشابه دارد که `project_id` را از DB اعتبارسنجی می‌کند اما `project_path` را نه. این تسک صرفاً دستورات تست را مشخص می‌کند و شامل پیاده‌سازی کد یا تغییر در فایل‌ها نیست — هدف تأیید وضعیت فعلی امنیت است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] دستور curl با project_path='../../etc/' باید HTTP 400 یا 422 برگرداند، نه 200
- [ ] pytest backend/tests/test_security.py -k path_traversal باید pass شود
- [ ] فایل backend/tests/test_security.py باید وجود داشته باشد و حداقل یک تابع test_path_traversal داشته باشد
- [ ] ارسال project_path='/etc/passwd' نیز باید با 400/422 رد شود
- [ ] AnalysisRequest در analysis.py باید field_validator یا validator برای project_path داشته باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. اجرای دستور curl برای تست path traversal روی endpoint `/api/analysis/run-stream`:
   `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc/"}'`
   انتظار: باید HTTP 400 یا 422 برگرداند، نه 200 با stream فایل‌های `/etc/`.

2. اجرای pytest برای تست‌های path traversal:
   `pytest backend/tests/test_security.py -k path_traversal`
   اگر فایل `backend/tests/test_security.py` وجود ندارد، باید ابتدا ایجاد شود با تست‌هایی که:
   - ارسال `../../etc/` به عنوان `project_path` را تست کنند
   - ارسال `/absolute/path/outside/project` را تست کنند
   - تأیید کنند endpoint با status 400/422 پاسخ می‌دهد

3. بررسی کد `backend/app/api/routes/analysis.py` خطوط ۱۲۷-۱۶۵ برای شناسایی نقطه آسیب‌پذیر (`project_path = request.project_path` → `os.walk(project_path)` بدون validation).

4. در صورت fail شدن تست‌ها (یعنی endpoint آسیب‌پذیر است)، باید validation به `AnalysisRequest` در خط ۳۰-۳۶ اضافه شود.

## 💡 نمونه‌های قبل/بعد
**اضافه کردن validator به AnalysisRequest برای جلوگیری از path traversal**

_قبل:_
```
class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []
    roadmap_path: Optional[str] = None
```

_بعد:_
```
import os
from pydantic import field_validator

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []
    roadmap_path: Optional[str] = None

    @field_validator('project_path')
    @classmethod
    def validate_no_path_traversal(cls, v: str) -> str:
        real = os.path.realpath(v)
        # جلوگیری از خروج از دایرکتوری مجاز
        if '..' in v or v.startswith('/'):
            raise ValueError('مسیر فایل مخرب شناسایی شد')
        return v
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc/"}'`
- `pytest backend/tests/test_security.py -k path_traversal -v`
- `pytest backend/tests/test_security.py -v`
- `pytest backend/tests/ -k security -v`

## ⚠️ ریسک‌ها و موارد احتیاط
1. تابع `run_analysis_stream` در `analysis.py` خط ۱۶۰ از `os.walk(project_path)` بدون هیچ چک امنیتی استفاده می‌کند — اگر validation اضافه شود، endpoint `/api/analysis/run` (خط ۴۶) که همین `AnalysisRequest` را استفاده می‌کند نیز تحت تأثیر قرار می‌گیرد (مثبت). 2. فایل `backend/tests/test_security.py` وجود ندارد — دستور pytest بدون ایجاد این فایل با `ERROR: not found` شکست می‌خورد. 3. اگر validator اضافه شود، `roadmap_path` در همین مدل (خط ۳۵) نیز باید validate شود چون در خط ۱۴۵ با `os.path.exists(request.roadmap_path)` استفاده می‌شود. 4. `DeepAnalysisService` که از `ai_manager` (16 فایل importer) استفاده می‌کند ممکن است خودش نیز path را پاس دهد — باید بررسی شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 26: اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)

**Scope:** این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint /analysis/run است. فقط validation سمت سرور (backend) در فایل backend/app/api/routes/analysis.py انجام می‌شود. منطق business (تحلیل پروژه) تغییر نمی‌کند. مسیرهای معتبر باید همچنان کار کنند و مسیرهای نامعتبر (مانند path traversal یا مسیرهای مطلق غیرمجاز) باید خطای 422 برگردانند.
**Key terms:** backend/app/api/routes/analysis.py, /analysis/run, project_path, 422, path traversal, validation

**بخش مربوط از متن کاربر:**
```
تسک 6 از 8
  id: 866ea2f9-0e88-4848-9c2a-d9b72c654747
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "../../etc/passwd"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - ارسال مسیر `/etc/` خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/etc/"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - مسیرهای معتبر داخل `/ [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/valid/path"}, "expected_status": 200, "required_fields": ["result"], "json_contains": null}]
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن اعتبارسنجی project_path در endpoint /analysis/run

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-35` — `AnalysisRequest` — کلاس Pydantic که ورودی endpoint /analysis/run را تعریف می‌کند. فیلد project_path هیچ validator ندارد و مستعد path traversal است. باید @field_validator اضافه شود.
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:46-80` — `run_analysis` — endpoint اصلی که project_path را بدون validation به analyzer.analyze_project() پاس می‌دهد. با افزودن validator به AnalysisRequest، این endpoint به‌صورت خودکار محافظت می‌شود.
  ```python
  @router.post("/run", response_model=AnalysisResponse)
  async def run_analysis(
      request: AnalysisRequest,
      background_tasks: BackgroundTasks
  ):
      try:
          analyzer = get_project_analyzer()
          analyzer.initialize()
          report = await analyzer.analyze_project(
              project_id=request.project_id,
              project_path=request.project_path,
  ```
- `backend/app/api/routes/analysis.py:83-130` — `run_analysis_stream` — endpoint streaming که همان AnalysisRequest را استفاده می‌کند. با اصلاح validator در AnalysisRequest، این endpoint نیز به‌صورت خودکار محافظت می‌شود — نیازی به تغییر جداگانه نیست.
  ```python
  @router.post("/run-stream")
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      async def run_analysis_task():
          nonlocal final_result
          try:
              ai_manager = get_ai_manager()
              ...
              project_path = request.project_path
              files = []
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (backend) + Next.js (frontend). Pydantic v2 (>=2.5.0 طبق requirements.txt) — از `@field_validator` و `model_validator` استفاده می‌شود نه `@validator` قدیمی. FastAPI به‌صورت خودکار `ValidationError` پایدانتیک را به HTTP 422 با body `{"detail": [...]}` تبدیل می‌کند. نیازی به دستکاری دستی response نیست.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/project_analyzer.py` — تابع analyze_project() در این سرویس project_path را دریافت می‌کند. اگر validation در route انجام شود، این سرویس مقدار پاک‌شده دریافت می‌کند و نیازی به تغییر ندارد.
- `backend/app/services/deep_analysis_service.py` (سطر 120) — DeepAnalysisService در run_analysis_stream (خط ۱۲۰) استفاده می‌شود و project_path را از request می‌گیرد. validation در لایه route از رسیدن مسیر مخرب به این سرویس جلوگیری می‌کند.
- `backend/app/core/database.py` (سطر 116) — توسط analysis.py در خطوط ۱۱۶-۱۱۷ import می‌شود (SessionLocal). تغییر در AnalysisRequest validator هیچ تأثیری بر database layer ندارد — فقط برای اطمینان از عدم side effect.
- `backend/app/services/ai_manager.py` (سطر 113) — در run_analysis_stream (خط ۱۱۳) استفاده می‌شود. validation در لایه route قبل از رسیدن به ai_manager اجرا می‌شود — هیچ تغییری در این فایل لازم نیست.
- `backend/app/main.py` — router مربوط به analysis را register می‌کند. تغییر در AnalysisRequest validator به‌صورت خودکار در همه endpointهایی که این router را mount می‌کنند اعمال می‌شود.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/api/routes/analysis.py` توسط `backend/app/main.py` به عنوان router mount می‌شود. کلاس `AnalysisRequest` توسط دو endpoint استفاده می‌شود: `run_analysis` (خط ۴۶) و `run_analysis_stream` (خط ۸۳). تغییر در این کلاس هر دو endpoint را به‌صورت خودکار تحت تأثیر قرار می‌دهد. `backend/app/services/project_analyzer.py` (از طریق `get_project_analyzer()`) و `backend/app/services/deep_analysis_service.py` (از طریق `DeepAnalysisService`) مقدار `project_path` را دریافت می‌کنند — با validation در لایه route، این سرویس‌ها مقدار پاک‌شده دریافت می‌کنند. `backend/app/core/database.py` نیز در این route import می‌شود (خط ۱۱۶) اما تحت تأثیر این تغییر نیست.

## 🔍 Context و وضعیت فعلی
این تسک مربوط به افزودن اعتبارسنجی سمت سرور (backend-only) برای پارامتر `project_path` در endpoint `POST /analysis/run` است که در فایل `backend/app/api/routes/analysis.py` تعریف شده. هدف جلوگیری از حملات path traversal (مانند `../../etc/passwd`) و مسیرهای مطلق غیرمجاز (مانند `/etc/`) است.

طبق درخواست کاربر (تسک 6 از 8، id: 866ea2f9-0e88-4848-9c2a-d9b72c654747)، فقط validation سمت سرور در `backend/app/api/routes/analysis.py` انجام می‌شود و منطق business (تحلیل پروژه در `DeepAnalysisService`) تغییر نمی‌کند.

مشکل فعلی: در کلاس `AnalysisRequest` (خط ۳۰-۳۵ فایل analysis.py)، فیلد `project_path: str` هیچ validator ندارد. endpoint `run_analysis` (خط ۴۶-۸۰) مستقیماً مقدار را به `analyzer.analyze_project()` پاس می‌دهد. endpoint `run_analysis_stream` (خط ۸۳-۲۶۸) نیز همین مشکل را دارد — `project_path = request.project_path` در خط ۱۲۷ بدون هیچ بررسی استفاده می‌شود.

کلیدواژه‌های مرتبط: `backend/app/api/routes/analysis.py`، `/analysis/run`، `project_path`، `422`، path traversal، validation.

مسیرهای نامعتبر که باید خطای 422 برگردانند:
- `../../etc/passwd` (path traversal با `..`)
- `/etc/` (مسیر مطلق سیستمی)

مسیرهای معتبر داخل محدوده مجاز باید همچنان کار کنند و 200 برگردانند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال مسیر `../../etc/passwd` به endpoint POST /analysis/run خطای 422 با فیلد `detail` برمی‌گرداند
- [ ] ارسال مسیر `/etc/` به endpoint POST /analysis/run خطای 422 با فیلد `detail` برمی‌گرداند
- [ ] ارسال مسیر `/proc/self/environ` به endpoint POST /analysis/run خطای 422 برمی‌گرداند
- [ ] decorator @field_validator با نام validate_project_path در کلاس AnalysisRequest در فایل analysis.py تعریف شده باشد
- [ ] مسیرهای معتبر مانند `/valid/path` یا `/app/projects/myproject` باید بدون خطای validation پردازش شوند (status 200 یا خطای business logic — نه 422)
- [ ] ارسال مسیر `../../../root/.ssh/id_rsa` (path traversal عمیق‌تر) نیز خطای 422 برمی‌گرداند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل `backend/app/api/routes/analysis.py`، کلاس `AnalysisRequest` (خطوط ۳۰-۳۵) را با افزودن Pydantic validator برای فیلد `project_path` تغییر بده.
2. از `pydantic.field_validator` (Pydantic v2) یا `validator` (Pydantic v1) استفاده کن — با توجه به `pydantic>=2.5.0` در requirements.txt، از `@field_validator` استفاده می‌شود.
3. قوانین validation:
   - اگر `project_path` شامل `..` باشد → ValueError با پیام مناسب
   - اگر `project_path` با `/etc`, `/proc`, `/sys`, `/dev`, `/root`, `/var/log` شروع شود → ValueError
   - اگر `project_path` مسیر مطلق باشد و خارج از محدوده مجاز (مثلاً `/tmp`, `/home`, `/app`, `/workspace`) → ValueError
4. همین validator را برای endpoint `run_analysis_stream` (خط ۸۳) نیز اعمال کن — چون هر دو endpoint از همان `AnalysisRequest` model استفاده می‌کنند، یک بار تعریف کافی است.
5. خطای Pydantic ValidationError به‌صورت خودکار توسط FastAPI به HTTP 422 تبدیل می‌شود — نیازی به دستکاری response نیست.
6. تست‌های موجود در `backend/tests/` را بررسی کن تا مطمئن شوی تست‌های موجود break نشوند.

## 💡 نمونه‌های قبل/بعد
**افزودن field_validator به AnalysisRequest برای جلوگیری از path traversal**

_قبل:_
```
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None
```

_بعد:_
```
from pydantic import BaseModel, field_validator
import os

# مسیرهای سیستمی که دسترسی به آن‌ها ممنوع است
_BLOCKED_PREFIXES = (
    "/etc", "/proc", "/sys", "/dev",
    "/root", "/var/log", "/boot", "/bin", "/sbin",
)

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        # جلوگیری از path traversal
        if ".." in v:
            raise ValueError(
                "مسیر پروژه نمی‌تواند شامل '..' باشد (path traversal مجاز نیست)"
            )
        # نرمال‌سازی مسیر
        normalized = os.path.normpath(v)
        # بررسی مسیرهای سیستمی ممنوع
        for blocked in _BLOCKED_PREFIXES:
            if normalized.startswith(blocked):
                raise ValueError(
                    f"دسترسی به مسیر '{blocked}' مجاز نیست"
                )
        return v
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -v -k 'analysis' --tb=short`
- `pytest backend/tests/test_runtime_verify_integration.py -v --tb=short`
- `python -c "from backend.app.api.routes.analysis import AnalysisRequest; r = AnalysisRequest(project_id='x', project_path='../../etc/passwd'); print('FAIL: no validation')" 2>&1 | grep -E 'ValidationError|FAIL'`
- `python -m pytest backend/tests/ -v --tb=short -x`

## ⚠️ ریسک‌ها و موارد احتیاط
1. **هر دو endpoint تحت تأثیر**: تغییر در `AnalysisRequest` هم `run_analysis` (خط ۴۶) و هم `run_analysis_stream` (خط ۸۳) را تحت تأثیر قرار می‌دهد — اگر تست‌های موجود مسیرهای edge-case ارسال می‌کنند، ممکن است break شوند.
2. **تعریف «مسیر مجاز»**: لیست `_BLOCKED_PREFIXES` باید با محیط deploy (Railway/Docker) هماهنگ باشد — اگر پروژه‌ها در `/tmp` یا `/var/app` ذخیره می‌شوند، باید از لیست blocked خارج باشند.
3. **Pydantic v2 syntax**: پروژه از `pydantic>=2.5.0` استفاده می‌کند — باید از `@field_validator` (نه `@validator` قدیمی) استفاده شود. اگر جای دیگری در کد از Pydantic v1 syntax استفاده شده، ممکن است conflict ایجاد شود.
4. **run_analysis_stream نیز باید تست شود**: endpoint `/analysis/run-stream` نیز از همان `AnalysisRequest` استفاده می‌کند (خط ۸۴) — validation باید برای هر دو endpoint verify شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 27: اعتبارسنجی ورودی project_path در endpoint تحلیل پروژه

**Scope:** این مرحله شامل افزودن validator به فیلد project_path در مدل Pydantic AnalysisRequest است تا از حملات Path Traversal جلوگیری شود. همچنین شامل اصلاح نحوه استفاده از project_path در تابع run_analysis_task برای امنیت بیشتر می‌شود. خارج از scope: تغییرات در frontend، middleware، یا سایر endpointها.
**Key terms:** AnalysisRequest, project_path, validator, run_analysis_task, os.walk, Path Traversal, backend/app/api/routes/analysis.py

**بخش مربوط از متن کاربر:**
```
عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — فیلد project_path بدون validator است
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_task` — استفاده مستقیم از project_path در os.walk بدون اعتبارسنجی
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

این آسیب‌پذیری امکان Path Traversal را فراهم می‌کند: مهاجم می‌تواند با ارسال مسیرهایی مانند `../../etc/passwd` یا `/etc/` فایل‌های حساس سیستم را بخواند.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن validator امنیتی به project_path در AnalysisRequest

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — کلاس Pydantic که فیلد project_path بدون validator است. اینجا باید validator اضافه شود.
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_task`
  ```python
  project_path = request.project_path
  files = []
  ...
  for root, dirs, filenames in
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
اعتبارسنجی ورودی project_path در endpoint تحلیل پروژه (analysis.py). این مرحله شامل افزودن validator به فیلد project_path در مدل Pydantic AnalysisRequest است تا از حملات Path Traversal جلوگیری شود. همچنین شامل اصلاح نحوه استفاده از project_path در تابع run_analysis_task برای امنیت بیشتر می‌شود. خارج از scope: تغییرات در frontend، middleware، یا سایر endpointها.

--- بخش مربوط از درخواست اصلی کاربر ---
عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — فیلد project_path بدون validator است
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_task` — استفاده مستقیم از project_path در os.walk بدون اعتبارسنجی
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

این آسیب‌پذیری امکان Path Traversal را فراهم می‌کند: مهاجم می‌تواند با ارسال مسیرهایی مانند `../../etc/passwd` یا `/etc/` فایل‌های حساس سیستم را بخواند.

--- کلیدواژه‌ها ---
AnalysisRequest, project_path, validator, run_analysis_task, os.walk, Path Traversal, backend/app/api/routes/analysis.py

شواهد در کد واقعی: در فایل `backend/app/api/routes/analysis.py` خطوط 30-36 کلاس AnalysisRequest فاقد validator برای project_path است. همچنین در خطوط 127-180 تابع run_analysis_task از project_path مستقیماً در os.walk استفاده می‌کند بدون هیچ بررسی امنیتی. این دو نقطه آسیب‌پذیری اصلی هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. افزودن validator به فیلد project_path در کلاس AnalysisRequest (خطوط 30-36 فایل backend/app/api/routes/analysis.py) با استفاده از @field_validator از Pydantic v2. validator باید: (الف) مسیر را به مسیر مطلق تبدیل کند، (ب) بررسی کند که مسیر در دایرکتوری مجاز (مثلاً /home/user/projects یا مسیر مشخص شده در config) قرار دارد، (ج) از کاراکترهای خطرناک مانند '..' جلوگیری کند، (د) از symbolic link attacks جلوگیری کند.
2. اصلاح تابع run_analysis_task (خطوط 127-180) برای استفاده از project_path اعتبارسنجی شده به جای request.project_path مستقیم.
3. افزودن resolve_path ایمن که مسیر را نرمال کرده و از path traversal جلوگیری کند.
4. افزودن exception handling مناسب برای خطاهای اعتبارسنجی.
5. اطمینان از اینکه roadmap_path نیز به همین روش اعتبارسنجی شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 28: اعتبارسنجی مسیر پروژه برای جلوگیری از Path Traversal

**Scope:** این بخش شامل پیاده‌سازی اعتبارسنجی مسیرهای فایل در endpoint مربوط به تحلیل پروژه است. مسیرهای معتبر باید داخل دایرکتوری مجاز `/projects` باشند و مسیرهای حاوی `..` یا مسیرهای مطلق غیرمجاز (مانند `/etc/`) رد شوند. خروجی این مرحله فقط شامل منطق اعتبارسنجی است و شامل پیاده‌سازی endpoint یا تست‌ها نمی‌شود.
**Key terms:** os.path.abspath, os.path.commonpath, /projects, 422, Path Traversal, backend/app/api/routes/analysis.py, tests/test_analysis.py, backend/app/core/config.py

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند
- [ ] ارسال مسیر `/etc/` خطای 422 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `/
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی مسیر پروژه با استفاده از `os.path.abspath` و `os.path.commonpath` برای جلوگیری از Path Traversal. همچنین محدود کردن مسیر به یک دایرکتوری مجاز (مثلاً `/projects`).
```

## 🎯 هدف (خلاصه ساختاریافته)
اعتبارسنجی Path Traversal در endpoint تحلیل پروژه

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:46-80` — `run_analysis` — مسیر `request.project_path` بدون هیچ اعتبارسنجی مستقیماً به `analyze_project` پاس داده می‌شود. باید قبل از خط ۶۱ (فراخوانی `analyzer.analyze_project`) اعتبارسنجی Path Traversal اضافه شود.
  ```python
  @router.post("/run", response_model=AnalysisResponse)
  async def run_analysis(
      request: AnalysisRequest,
      background_tasks: BackgroundTasks
  ):
      try:
          analyzer = get_project_analyzer()
          analyzer.initialize()
  
          # اجرای تحلیل
          report = await analyzer.analyze_project(
              project_id=request.project_id,
              project_path=request.project_path,
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_stream` — در تابع `run_analysis_task` (nested در `generate_events`)، مقدار `request.project_path` مستقیماً در `os.path.join` (خط ۱۳۴) و `os.walk` (خط ۱۶۰) استفاده می‌شود. این نقطه اصلی آسیب‌پذیری Path Traversal است.
  ```python
  # جمع‌آوری فایل‌های پروژه
                  project_path = request.project_path
                  files = []
  
                  # خواندن README اگر موجود باشد
                  readme_content = ""
                  readme_paths = ["README.md", "readme.md", "README.txt"]
                  for readme_name in readme_paths:
                      readme_path = os.path.join(project_path, readme_name)
                      if os.path.exists(readme_path):
                          ...
  
                  for root, dirs, filenames in os.walk(project_path):
  ```
- `backend/app/core/config.py` — `Settings` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. باید متغیر `PROJECT_ROOT_DIR` (با مقدار پیش‌فرض `/projects`) به کلاس Settings اضافه شود تا `validate_project_path` از آن استفاده کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI + Python (backend). کتابخانه‌های مرتبط: `os.path` (stdlib — `abspath`, `commonpath`, `realpath`)، `pydantic>=2.5.0` (برای validation در مدل‌های request)، `fastapi>=0.109.0` (برای `HTTPException` با status_code=422). هیچ dependency خارجی جدیدی نیاز نیست — همه ابزارها در stdlib Python موجودند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/security_analysis.py` (سطر 1) — این فایل نیز از `project_path` در context های مختلف استفاده می‌کند و ممکن است در آینده نیاز به همین validation داشته باشد. همچنین pattern مشابه `get_security_analyzer()` نشان می‌دهد که validation utility باید shared باشد.
- `backend/app/core/database.py` (سطر 1) — این فایل توسط `analysis.py` import می‌شود (خط ۱۱۶ و ۲۷۷). هر تغییر در config یا core باید با database session management سازگار باشد.
- `backend/app/services/deep_analysis_service.py` (سطر 191) — تابع `run_full_analysis` در خط ۱۹۱ فراخوانی می‌شود و `project_path` را از طریق `files` دریافت می‌کند. اگر validation در route انجام نشود، این service نیز در معرض خطر است.
- `backend/app/services/project_analyzer.py` (سطر 61) — تابع `analyze_project` در خط ۶۱ با `project_path=request.project_path` فراخوانی می‌شود. این service مستقیماً مسیر را دریافت می‌کند و اگر validation در route نباشد، آسیب‌پذیر است.

## 🌐 نقشهٔ وابستگی‌ها
تابع `run_analysis` و `run_analysis_stream` در `backend/app/api/routes/analysis.py` هر دو `request.project_path` را بدون validation مصرف می‌کنند. این route توسط `backend/app/main.py` register می‌شود. تابع validation جدید (`validate_project_path`) باید در `backend/app/core/config.py` یا یک ماژول utility جدید تعریف شود تا توسط هر دو endpoint قابل استفاده باشد. `backend/app/services/deep_analysis_service.py` و `backend/app/services/project_analyzer.py` نیز از `project_path` استفاده می‌کنند اما validation باید در لایه route (نزدیک‌ترین نقطه به ورودی کاربر) انجام شود. `backend/app/core/database.py` که توسط ۱۳ فایل import می‌شود تحت تأثیر مستقیم نیست اما config تغییر می‌کند.

## 🔍 Context و وضعیت فعلی
این تسک شامل پیاده‌سازی منطق اعتبارسنجی مسیرهای فایل در endpoint مربوط به تحلیل پروژه (`backend/app/api/routes/analysis.py`) است تا از حملات Path Traversal جلوگیری شود. مسیرهای معتبر باید داخل دایرکتوری مجاز `/projects` باشند و مسیرهای حاوی `..` یا مسیرهای مطلق غیرمجاز (مانند `/etc/`) رد شوند.

بر اساس درخواست کاربر، خروجی این مرحله **فقط شامل منطق اعتبارسنجی** است و شامل پیاده‌سازی endpoint جدید یا تست‌ها نمی‌شود.

**مشکل فعلی در کد:**
در `backend/app/api/routes/analysis.py`، endpoint های `POST /analysis/run` (خط ۴۶) و `POST /analysis/run-stream` (خط ۸۳) مقدار `request.project_path` را مستقیماً بدون هیچ اعتبارسنجی به `os.walk` و `os.path.join` می‌دهند (خطوط ۱۶۰-۱۸۰). این یعنی یک مهاجم می‌تواند مسیری مانند `../../etc/passwd` یا `/etc/shadow` ارسال کند و سیستم فایل‌های حساس را بخواند.

**رفتار مورد انتظار:**
- ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند
- ارسال مسیر `/etc/` خطای 422 برمی‌گرداند
- مسیرهای معتبر داخل `/projects` بدون خطا پردازش می‌شوند
- هیچ تستی fail نمی‌شود (`pytest`)
- linter بدون warning عبور می‌کند
- type-check موفق است (`mypy`)

**کلیدواژه‌های فنی:** `os.path.abspath`, `os.path.commonpath`, `/projects`, `422`, `Path Traversal`, `backend/app/api/routes/analysis.py`, `tests/test_analysis.py`, `backend/app/core/config.py`

**روش پیشنهادی:** استفاده از `os.path.abspath` برای نرمال‌سازی مسیر و `os.path.commonpath` برای بررسی اینکه مسیر نرمال‌شده داخل دایرکتوری مجاز (`ALLOWED_PROJECT_ROOT`) قرار دارد. این مقدار باید از `backend/app/core/config.py` خوانده شود تا قابل پیکربندی باشد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال `project_path: '../../etc/passwd'` به `POST /analysis/run` باید HTTP 422 برگرداند
- [ ] ارسال `project_path: '/etc/'` به `POST /analysis/run` باید HTTP 422 برگرداند
- [ ] تابع `validate_project_path` در فایل `backend/app/core/path_utils.py` یا `backend/app/core/config.py` تعریف شده باشد و از `os.path.abspath` و `os.path.commonpath` استفاده کند
- [ ] تابع `validate_project_path` در هر دو endpoint `run_analysis` و `run_analysis_stream` در `backend/app/api/routes/analysis.py` فراخوانی شده باشد
- [ ] ارسال `project_path: '/projects/my-valid-project'` به `POST /analysis/run` نباید خطای 422 بدهد (مسیر معتبر داخل /projects پذیرفته شود)
- [ ] اجرای `pytest backend/` بدون failure پاس شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **افزودن تابع `validate_project_path` در `backend/app/core/config.py` یا یک ماژول utility جدید** (مثلاً `backend/app/core/path_utils.py`):
   - ورودی: `project_path: str`
   - خروجی: `str` (مسیر نرمال‌شده) یا raise `ValueError`
   - منطق: `abs_path = os.path.abspath(project_path)` سپس `os.path.commonpath([abs_path, ALLOWED_ROOT]) == ALLOWED_ROOT`
   - اگر مسیر خارج از `ALLOWED_ROOT` بود، `ValueError` با پیام مناسب raise کند

2. **تعریف `ALLOWED_PROJECT_ROOT` در `backend/app/core/config.py`**:
   - مقدار پیش‌فرض: `/projects`
   - قابل override از طریق environment variable `PROJECT_ROOT_DIR`

3. **فراخوانی `validate_project_path` در `backend/app/api/routes/analysis.py`**:
   - در endpoint `POST /analysis/run` (تابع `run_analysis`، خط ۴۷): قبل از `analyzer.analyze_project(...)` در خط ۶۱، مسیر را validate کن و در صورت خطا `HTTPException(status_code=422)` raise کن
   - در endpoint `POST /analysis/run-stream` (تابع `run_analysis_stream`، خط ۸۴): قبل از `os.walk(project_path)` در خط ۱۶۰، همین validation را اعمال کن

4. **نکته مهم:** تابع validation باید edge case های زیر را پوشش دهد:
   - مسیرهای relative با `..` مانند `../../etc/passwd`
   - مسیرهای absolute خارج از allowed root مانند `/etc/`
   - symlink ها (اختیاری: `os.path.realpath` به جای `os.path.abspath`)
   - مسیر خالی یا None

## 💡 نمونه‌های قبل/بعد
**افزودن تابع validate_project_path (فایل جدید یا در config.py)**

_قبل:_
```
# هیچ validation ای وجود ندارد
# در analysis.py خط 127:
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):  # مستقیم بدون بررسی
```

_بعد:_
```
# backend/app/core/path_utils.py (فایل جدید)
import os
from fastapi import HTTPException

ALLOWED_PROJECT_ROOT = os.environ.get("PROJECT_ROOT_DIR", "/projects")

def validate_project_path(project_path: str) -> str:
    """اعتبارسنجی مسیر پروژه برای جلوگیری از Path Traversal."""
    if not project_path or not project_path.strip():
        raise HTTPException(status_code=422, detail="مسیر پروژه نمی‌تواند خالی باشد")
    
    abs_path = os.path.abspath(project_path)
    allowed_root = os.path.abspath(ALLOWED_PROJECT_ROOT)
    
    try:
        common = os.path.commonpath([abs_path, allowed_root])
    except ValueError:
        raise HTTPException(status_code=422, detail="مسیر پروژه نامعتبر است")
    
    if common != allowed_root:
        raise HTTPException(
            status_code=422,
            detail=f"مسیر پروژه باید داخل {ALLOWED_PROJECT_ROOT} باشد"
        )
    
    return abs_path

# در analysis.py — run_analysis (خط 56):
from ...core.path_utils import validate_project_path

async def run_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    try:
        validated_path = validate_project_path(request.project_path)  # 🔒 اضافه شد
        analyzer = get_project_analyzer()
        analyzer.initialize()
        report = await analyzer.analyze_project(
            project_id=request.project_id,
            project_path=validated_path,  # از validated_path استفاده می‌شود
            ...
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -v -k 'path or traversal or analysis'`
- `python -m mypy backend/app/core/config.py backend/app/api/routes/analysis.py --ignore-missing-imports`
- `python -c "from backend.app.core.path_utils import validate_project_path; print('import OK')"`
- `ruff check backend/app/core/ backend/app/api/routes/analysis.py`

## ⚠️ ریسک‌ها و موارد احتیاط
1. **تابع `run_analysis_task` در `analysis.py` خطوط ۱۰۹-۲۱۲ یک nested async function است** — validation باید در scope بیرونی (`run_analysis_stream`) انجام شود، نه داخل nested function، تا قبل از شروع task اجرا شود و HTTPException به درستی propagate شود.
2. **`os.path.abspath` symlink ها را resolve نمی‌کند** — اگر مهاجم یک symlink داخل `/projects` به `/etc` بسازد، `abspath` آن را معتبر می‌داند. برای امنیت بیشتر باید از `os.path.realpath` استفاده شود.
3. **مقدار `ALLOWED_PROJECT_ROOT` در محیط‌های مختلف متفاوت است** — در development ممکن است `/projects` وجود نداشته باشد. باید fallback یا config مناسب برای dev environment تعریف شود تا تست‌ها fail نشوند.
4. **`backend/app/services/project_analyzer.py` و `deep_analysis_service.py` نیز `project_path` دریافت می‌کنند** — اگر این service ها از جای دیگری (غیر از این route) فراخوانی شوند، validation bypass می‌شود. validation در route کافی است اما باید documented شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 29: اضافه کردن validator به Pydantic مدل برای اعتبارسنجی مسیر پروژه

**Scope:** این بخش شامل افزودن یک validator به فیلد project_path در یک Pydantic مدل است. validator باید مسیر را به absolute تبدیل کند، بررسی کند که درون دایرکتوری مجاز (PROJECTS_BASE_DIR) قرار دارد و یک دایرکتوری موجود است. فایل دقیق مدل مشخص نشده، اما با توجه به مسیرهای موجود، احتمالاً در backend/app/models/analysis_report.py یا مدل مشابهی است. خارج از scope: تغییرات در API routes، سرویس‌ها یا frontend.
**Key terms:** project_path, Pydantic, field_validator, PROJECTS_BASE_DIR, backend/app/models/analysis_report.py

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**اضافه کردن validator به Pydantic مدل**

_قبل:_
```
project_path: str
```

_بعد:_
```
project_path: str = Field(..., description="مسیر پروژه")

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        abs_path = os.path.abspath(v)
        allowed_base = os.path.abspath(os.environ.get('PROJECTS_BASE_DIR', '/projects'))
        if not abs_path.startswith(allowed_base):
            raise ValueError(f'Path must be within {allowed_base}')
        if not os.path.isdir(abs_path):
            raise ValueError('Path must be an existing directory')
        return abs_path
```
```

project_path: str
```

_بعد:_
```
project_path: str = Field(..., description="مسیر پروژه")

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        abs_path = os.path.abspath(v)
        allowed_base = os.path.abspath(os.environ.get('PROJECTS_BASE_DIR', '/projects'))
        if not abs_path.startswith(allowed_base):
            raise ValueError(f'Path must be within {allowed_base}')
        if not os.path.isdir(abs_path):
            raise ValueError('Path must be an existing directory')
        return abs_path
```

--- کلیدواژه‌ها ---
project_path, Pydantic, field_validator, PROJECTS_BASE_DIR, backend/app/models/analysis_report.py
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن validator Pydantic برای اعتبارسنجی project_path در مدل‌های تحلیل

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:30-35` — `AnalysisRequest` — این کلاس در analysis.py خط 30-35 دارای فیلد project_path: str بدون validator است. کاربر خواسته validator به Pydantic مدل اضافه شود. اگر مدل اصلی در analysis_report.py نبود، اینجا هدف است.
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []  # خالی = همه مدل‌های فعال
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/github_import.py:23-28` — `CheckRepoRequest`
  ```python
  class CheckRepoRequest(BaseModel):
      """درخواست بررسی دسترسی به repo"""
      url: str
      token: Optional[str] = None
      use_global_token: bool = False  #
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن یک validator به Pydantic مدل برای اعتبارسنجی مسیر پروژه (project_path) را دارد. validator باید مسیر را به absolute تبدیل کند (os.path.abspath(v))، بررسی کند که درون دایرکتوری مجاز (PROJECTS_BASE_DIR) قرار دارد (با os.environ.get('PROJECTS_BASE_DIR', '/projects')) و یک دایرکتوری موجود است (os.path.isdir(abs_path)). فایل دقیق مدل مشخص نشده، اما با توجه به مسیرهای موجود در پروژه و ساختار deep context، محتمل‌ترین فایل‌ها backend/app/models/analysis_report.py (شامل کلاس‌های AnalysisRequestSchema, AnalysisScheduleSchema) و backend/app/api/routes/analysis.py (شامل کلاس AnalysisRequest در خطوط 30-35 با فیلد project_path: str) هستند. همچنین backend/app/api/routes/github_import.py شامل کلاس‌های ImportRepoRequest و CheckRepoRequest با فیلد url است. کاربر تأکید کرده خارج از scope: تغییرات در API routes، سرویس‌ها یا frontend. کلیدواژه‌ها: project_path, Pydantic, field_validator, PROJECTS_BASE_DIR, backend/app/models/analysis_report.py. شواهد در کد: در analysis.py خط 32 فیلد project_path: str بدون validator وجود دارد. در github_import.py خط 25 فیلد url: str بدون validator مسیر. در model_profiles.py خط 57-67 ProfileSummary فاقد فیلد مسیر است. در backend/app/models/analysis_report.py (deep-read نشده) احتمالاً AnalysisRequestSchema دارای project_path است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. شناسایی دقیق فایل مدل: ابتدا فایل backend/app/models/analysis_report.py را باز کرده و کلاس‌های AnalysisRequestSchema و AnalysisScheduleSchema را بررسی کن. اگر project_path در آن‌ها وجود دارد، validator را به همان کلاس اضافه کن. 2. اگر project_path در analysis_report.py نبود، به backend/app/api/routes/analysis.py مراجعه کن (خطوط 30-35) و validator را به کلاس AnalysisRequest اضافه کن. 3. پیاده‌سازی validator: از pydantic v2 @field_validator استفاده کن (با import از pydantic). تابع validate_project_path باید: a) os.path.abspath(v) بزند، b) os.environ.get('PROJECTS_BASE_DIR', '/projects') را بخواند، c) if not abs_path.startswith(allowed_base): raise ValueError, d) if not os.path.isdir(abs_path): raise ValueError, e) return abs_path. 4. import os و from pydantic import Field, field_validator را به بالای فایل اضافه کن. 5. فیلد project_path را به project_path: str = Field(..., description="مسیر پروژه") تغییر بده. 6. خارج از scope: هیچ تغییری در routes (analysis.py, github_import.py, model_profiles.py)، سرویس‌ها یا frontend نده.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 30: رفع نقص مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا

**Scope:** این مرحله شامل اصلاح تمام endpointهای موجود در فایل‌های backend/app/api/routes/analysis.py، backend/app/api/routes/model_profiles.py و backend/app/api/routes/project_health است تا به جای استفاده مستقیم از SessionLocal()، از Depends(get_db) یا async context manager استفاده کنند. همچنین شامل اجرای تست‌های رگرشن قبل از merge و اجرای تست نشت connection با 1000 درخواست هم‌زمان می‌شود. خارج از scope: تغییرات در frontend، config، یا سایر routeها.
**Key terms:** SessionLocal, Depends(get_db), backend/app/api/routes/analysis.py, backend/app/api/routes/model_profiles.py, backend/app/api/routes/project_health, tests/test_db_connection_leak.py::test_concurrent_requests_no_leak

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 8
  id: 51fab7d9-dba0-486e-8e29-77a459785fc3
  عنوان اصلی: نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند [verify_method=static] [verify_plan={"grep_patterns": ["SessionLocal\\(\\)"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - همه endpointها از Depends(get_db) یا async context manager استفاده کنند [verify_method=static] [verify_plan={"grep_patterns": ["Depends\\(get_db\\)", "async with.*get_db"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/model_profiles.py", "backend/app/api/routes/project_health"]}]
  - تست نشت connection با 1000 درخواست هم‌زمان پاس شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_db_connection_leak.py::test_concurrent_requests_no_leak", "timeout_seconds": 120}]
```

## 🎯 هدف (خلاصه ساختاریافته)
جایگزینی SessionLocal مستقیم با Depends(get_db) در سه روتر

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:271-290` — `get_analysis_reports` — نمونهٔ اصلی مشکل: SessionLocal مستقیم بدون Depends. اگر HTTPException قبل از finally raise شود، session بسته نمی‌شود. این pattern در ۸ endpoint این فایل تکرار شده است.
  ```python
  @router.get("/reports", response_model=List[AnalysisReportSchema])
  async def get_analysis_reports(
      project_id: Optional[str] = None,
      limit: int = 20
  ):
      """دریافت لیست گزارش‌های تحلیل"""
      from ...core.database import SessionLocal
      from ...models.analysis_report import AnalysisReport
  
      db = SessionLocal()
      try:
          query = db.query(AnalysisReport)
  
          if project_id:
              query = query.filter(AnalysisReport.project_id == project_id)
  
          reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
          return [AnalysisReportSchema.model_validate(r) for r in reports]
      finally:
          db.close()
  ```
- `backend/app/api/routes/analysis.py:109-125` — `run_analysis_task (inner function in run_analysis_stream)` — بدترین نمونه: analysis_db = SessionLocal() در یک inner async function ساخته می‌شود اما هیچ‌گاه بسته نمی‌شود — نه finally دارد، نه context manager. در صورت exception در DeepAnalysisService، connection برای همیشه باز می‌ماند.
  ```python
  async def run_analysis_task():
              nonlocal final_result
              try:
                  # دریافت AI Manager
                  ai_manager = get_ai_manager()
  
                  # 🔴 ایجاد db session برای استفاده از پرامپت‌های دیتابیس
                  from ...core.database import SessionLocal
                  analysis_db = SessionLocal()
  
                  # ساخت DeepAnalysisService با progress callback و db_session
                  deep_analyzer = DeepAnalysisService(
                      ai_manager=ai_manager,
                      progress_callback=progress_callback,
                      db_session=analysis_db  # 🔴 برای استفاده از پرامپت‌های دیتابیس
                  )
  ```
- `backend/app/api/routes/model_profiles.py:142-175` — `get_all_profiles` — این endpoint درست از Depends(get_db) استفاده می‌کند — نمونهٔ صحیح برای مقایسه. سایر endpointهای این فایل باید به همین pattern تبدیل شوند.
  ```python
  @router.get("/profiles")
  async def get_all_profiles(
      sort_by: str = Query("overall_score", description="فیلد مرتب‌سازی"),
      order: str = Query("desc", description="ترتیب: asc یا desc"),
      limit: int = Query(50, description="تعداد نتایج"),
      use_fallback: bool = Query(True, description="استفاده از داده‌های پیش‌فرض در صورت خالی بودن"),
      db=Depends(get_db)
  ):
  ```
- `backend/app/api/routes/analysis.py:6-12` — `imports block` — در این import block، نه Depends و نه get_db وجود دارد. باید `Depends` به import از fastapi اضافه شود و `get_db` از `...core.database` import شود تا pattern صحیح در همهٔ endpointها قابل استفاده باشد.
  ```python
  from fastapi import APIRouter, HTTPException, BackgroundTasks
  from fastapi.responses import StreamingResponse
  from typing import List, Optional
  from pydantic import BaseModel
  import logging
  import json
  import asyncio
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. کتابخانه‌های مرتبط: SQLAlchemy >= 2.0.0 (از requirements.txt)، aiosqlite >= 0.19.0 برای async. FastAPI's `Depends(get_db)` pattern تضمین می‌کند که session در پایان هر request (موفق یا خطا) بسته شود — این مکانیزم از generator-based dependency injection استفاده می‌کند (`yield` در get_db). برای `run_analysis_stream` که یک background task است، باید از `contextlib.asynccontextmanager` یا explicit try/finally با `async with` استفاده شود چون Depends در background tasks کار نمی‌کند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — تعریف‌کنندهٔ هر دو `SessionLocal` و `get_db` — این فایل توسط ۱۶ فایل import می‌شود. تابع `get_db` باید به‌عنوان dependency در همهٔ endpointها استفاده شود. تغییر pattern استفاده از SessionLocal به get_db مستقیماً به این فایل وابسته است.
- `backend/app/services/deep_analysis_service.py` (سطر 120) — در `run_analysis_stream` (analysis.py خط ۱۲۰)، `DeepAnalysisService` با `db_session=analysis_db` ساخته می‌شود. بعد از اصلاح، باید مطمئن شویم که session به‌درستی به این service پاس داده می‌شود و lifecycle آن مدیریت می‌شود.
- `backend/app/api/routes/project_health.py` (سطر 1) — سومین فایل در scope تسک — طبق acceptance_criteria کاربر، این فایل هم باید از SessionLocal مستقیم به Depends(get_db) مهاجرت کند. این فایل از database.py، ai_manager.py، و models/project.py import می‌کند.
- `backend/app/models/analysis_report.py` (سطر 1) — مدل‌های `AnalysisReport` و `AnalysisSchedule` که در analysis.py query می‌شوند. بعد از تغییر session management، باید مطمئن شویم که lazy loading این مدل‌ها در scope session درست کار می‌کند.
- `backend/app/models/ai_profile.py` (سطر 33) — مدل `AIProfile` و `ModelValidationRecord` که در model_profiles.py query می‌شوند (خط ۳۳-۳۸). تغییر session management روی query های این مدل‌ها تأثیر مستقیم دارد.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/core/database.py` هاب مرکزی این تسک است و توسط ۱۶ فایل import می‌شود. تابع `get_db` در آن تعریف شده و در `model_profiles.py` (خط ۲۴) و `project_health.py` import شده اما در `analysis.py` هنوز import نشده. تغییرات این تسک روی سه فایل روتر اثر مستقیم دارد: `analysis.py` (۸ endpoint با SessionLocal مستقیم)، `model_profiles.py` (endpointهایی که هنوز pattern قدیمی دارند)، و `project_health.py`. سرویس `deep_analysis_service.py` که توسط `analysis.py` در `run_analysis_stream` فراخوانی می‌شود، `db_session` را به‌عنوان پارامتر می‌گیرد — باید مطمئن شویم lifecycle session در این مسیر هم درست مدیریت می‌شود. `model_profiler.py` که توسط هر دو `analysis.py` و `model_profiles.py` import می‌شود (۷ فایل importer) نیز باید بررسی شود که session را leak نکند.

## 🔍 Context و وضعیت فعلی
این تسک به رفع نقص بنیادی مدیریت Session دیتابیس در سه فایل روتر می‌پردازد: `backend/app/api/routes/analysis.py`، `backend/app/api/routes/model_profiles.py` و `backend/app/api/routes/project_health`. مشکل اصلی این است که endpointهای متعددی در این فایل‌ها به‌جای استفاده از `Depends(get_db)` یا async context manager، مستقیماً `SessionLocal()` را فراخوانی می‌کنند و session را فقط در بلوک `finally` می‌بندند — اما در مسیرهای خطا (مثلاً raise HTTPException قبل از finally، یا exception در میانهٔ کد) این بستن تضمین نمی‌شود و connection leak رخ می‌دهد.

شواهد در کد واقعی:
- `analysis.py` خط ۲۷۷: `db = SessionLocal()` در `get_analysis_reports` بدون Depends
- `analysis.py` خط ۲۹۸: `db = SessionLocal()` در `get_analysis_report`
- `analysis.py` خط ۳۱۴: `db = SessionLocal()` در `delete_analysis_report`
- `analysis.py` خط ۳۴۸: `db = SessionLocal()` در `download_analysis_report`
- `analysis.py` خط ۵۹۷: `db = SessionLocal()` در `get_schedule`
- `analysis.py` خط ۶۳۰: `db = SessionLocal()` در `update_schedule`
- `analysis.py` خط ۶۵۸: `db = SessionLocal()` در `delete_schedule`
- `analysis.py` خط ۶۸۷: `db = SessionLocal()` در `get_analysis_stats`
- `model_profiles.py` خط ۲۴: `from ...core.database import get_db` — این فایل get_db را import کرده اما در برخی endpointها مستقیم SessionLocal استفاده می‌شود
- `model_profiles.py` خط ۵۸۲: `refresh_rankings_from_logs` از `db=Depends(get_db)` استفاده می‌کند (درست) اما سایر endpointها باید بررسی شوند

همچنین در `analysis.py` خط ۱۱۶-۱۱۷ در `run_analysis_stream`، یک `SessionLocal()` مستقیم برای `analysis_db` ساخته می‌شود که هیچ‌گاه بسته نمی‌شود (نه finally، نه context manager).

Scope این تسک: اصلاح تمام endpointهای سه فایل فوق برای استفاده از `Depends(get_db)` یا `async with` context manager. خارج از scope: تغییرات در frontend، config، یا سایر routeها.

پس از اصلاح، باید تست نشت connection با 1000 درخواست هم‌زمان (`tests/test_db_connection_leak.py::test_concurrent_requests_no_leak`) پاس شود و تست‌های رگرشن موجود نیز اجرا شوند.

کلیدواژه‌های اصلی: `SessionLocal`, `Depends(get_db)`, `backend/app/api/routes/analysis.py`, `backend/app/api/routes/model_profiles.py`, `backend/app/api/routes/project_health`, `tests/test_db_connection_leak.py::test_concurrent_requests_no_leak`

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ endpointای در analysis.py از SessionLocal() مستقیم بدون context manager استفاده نکند
- [ ] همهٔ endpointهای analysis.py، model_profiles.py و project_health.py از Depends(get_db) یا async context manager استفاده کنند
- [ ] تست نشت connection با 1000 درخواست هم‌زمان پاس شود: tests/test_db_connection_leak.py::test_concurrent_requests_no_leak
- [ ] import Depends از fastapi در ابتدای analysis.py وجود داشته باشد
- [ ] import get_db از core.database در ابتدای analysis.py (نه داخل توابع) وجود داشته باشد
- [ ] تست‌های رگرشن موجود (backend/tests/) بدون fail اجرا شوند
- [ ] endpoint GET /analysis/reports با پارامتر project_id پاسخ 200 برگرداند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. **مرحله ۱ — اصلاح `backend/app/api/routes/analysis.py`:**
1. به signature همهٔ endpointهایی که `db = SessionLocal()` دارند، پارامتر `db=Depends(get_db)` اضافه کن (خطوط ۲۷۷، ۲۹۸، ۳۱۴، ۳۴۸، ۵۹۷، ۶۳۰، ۶۵۸، ۶۸۷).
2. بلوک‌های `db = SessionLocal()` و `try/finally: db.close()` را حذف کن — FastAPI خودش session را مدیریت می‌کند.
3. در `run_analysis_stream` (خط ۱۱۶-۱۱۷)، `analysis_db = SessionLocal()` را با `async with get_db() as analysis_db:` یا `contextlib.asynccontextmanager` جایگزین کن تا در همهٔ مسیرها (موفق/خطا) بسته شود.
4. import `Depends` را از `fastapi` در بالای فایل اضافه کن (خط ۶ — در حال حاضر فقط `APIRouter, HTTPException, BackgroundTasks` import شده).
5. import `get_db` را از `...core.database` اضافه کن.

**مرحله ۲ — اصلاح `backend/app/api/routes/model_profiles.py`:**
1. بررسی کن کدام endpointها هنوز `SessionLocal()` مستقیم دارند (فایل get_db را import کرده — خط ۲۴).
2. endpointهایی مثل `get_profile_detail` (خط ۲۴۹) که `db=Depends(get_db)` دارند درست هستند — فقط موارد استثنا را اصلاح کن.
3. در `refresh_rankings_from_logs` (خط ۵۸۲) که از Depends استفاده می‌کند، بررسی کن rollback در مسیر خطا درست انجام می‌شود.

**مرحله ۳ — اصلاح `backend/app/api/routes/project_health`:**
1. همان pattern — جایگزینی `SessionLocal()` با `Depends(get_db)`.

**مرحله ۴ — نوشتن تست:**
1. فایل `backend/tests/test_db_connection_leak.py` را بساز.
2. تست `test_concurrent_requests_no_leak` را پیاده‌سازی کن: 1000 درخواست هم‌زمان به endpointهای اصلاح‌شده بزن و تعداد connection های باز را قبل/بعد مقایسه کن.

**مرحله ۵ — تست رگرشن:**
1. `pytest backend/tests/` را اجرا کن و مطمئن شو هیچ تست موجودی fail نشده.

## 💡 نمونه‌های قبل/بعد
**اصلاح endpoint معمولی — get_analysis_reports**

_قبل:_
```
@router.get("/reports", response_model=List[AnalysisReportSchema])
async def get_analysis_reports(
    project_id: Optional[str] = None,
    limit: int = 20
):
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisReport

    db = SessionLocal()
    try:
        query = db.query(AnalysisReport)
        if project_id:
            query = query.filter(AnalysisReport.project_id == project_id)
        reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
        return [AnalysisReportSchema.model_validate(r) for r in reports]
    finally:
        db.close()
```

_بعد:_
```
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from ...core.database import get_db
from ...models.analysis_report import AnalysisReport

@router.get("/reports", response_model=List[AnalysisReportSchema])
async def get_analysis_reports(
    project_id: Optional[str] = None,
    limit: int = 20,
    db=Depends(get_db)
):
    query = db.query(AnalysisReport)
    if project_id:
        query = query.filter(AnalysisReport.project_id == project_id)
    reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
    return [AnalysisReportSchema.model_validate(r) for r in reports]
```

**اصلاح SessionLocal در background task (run_analysis_stream)**

_قبل:_
```
async def run_analysis_task():
    nonlocal final_result
    try:
        ai_manager = get_ai_manager()
        from ...core.database import SessionLocal
        analysis_db = SessionLocal()
        deep_analyzer = DeepAnalysisService(
            ai_manager=ai_manager,
            progress_callback=progress_callback,
            db_session=analysis_db
        )
        # ... rest of logic
```

_بعد:_
```
async def run_analysis_task():
    nonlocal final_result
    from ...core.database import get_db
    from contextlib import asynccontextmanager
    # استفاده از context manager برای تضمین بستن session
    db_gen = get_db()
    analysis_db = next(db_gen)
    try:
        ai_manager = get_ai_manager()
        deep_analyzer = DeepAnalysisService(
            ai_manager=ai_manager,
            progress_callback=progress_callback,
            db_session=analysis_db
        )
        # ... rest of logic
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_db_connection_leak.py::test_concurrent_requests_no_leak -v --timeout=120`
- `pytest backend/tests/ -v --tb=short`
- `grep -n 'SessionLocal()' backend/app/api/routes/analysis.py backend/app/api/routes/model_profiles.py backend/app/api/routes/project_health.py`
- `grep -n 'Depends(get_db)' backend/app/api/routes/analysis.py backend/app/api/routes/model_profiles.py backend/app/api/routes/project_health.py`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **`run_analysis_stream` در analysis.py (خط ۱۰۹-۲۱۲)**: این تابع یک background async task است — `Depends(get_db)` در background tasks کار نمی‌کند چون خارج از request lifecycle است. باید از generator-based pattern دستی استفاده شود (next(get_db()) + try/finally). اشتباه در این بخش می‌تواند session را زودتر از موعد ببندد و `DeepAnalysisService` را با closed session مواجه کند.
۲. **`model_profiles.py` — `refresh_rankings_from_logs` (خط ۵۸۲)**: این endpoint از `ActivityLog` که در `project_journal.py` تعریف شده import می‌کند. تغییر session management ممکن است روی cross-table query های این endpoint اثر بگذارد.
۳. **`deep_analysis_service.py`**: این سرویس `db_session` را به‌عنوان پارامتر می‌گیرد و توسط `analysis.py` فراخوانی می‌شود. بعد از اصلاح، باید مطمئن شویم که session در طول کل عمر DeepAnalysisService باز است — اگر session زودتر بسته شود، lazy-loaded relationships fail می‌شوند.
۴. **`model_profiler.py`** که توسط ۷ فایل import می‌شود (از جمله analysis.py و model_profiles.py): اگر این سرویس داخلاً SessionLocal مستقیم داشته باشد، خارج از scope این تسک است اما باید flag شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 31: بررسی اولیه و اعتبارسنجی خودکار پیش از اجرا

**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. محتوای آن صرفاً یک راهنمای رفتاری برای مدل است که باید پیش از هر اقدامی، ساختار repo را مستقل بررسی کند، از بازسازی موارد موجود خودداری کند، و در صورت نیاز به چند کامیت، ترتیب منطقی را رعایت کند. هیچ فایل، کلاس یا تابعی برای تغییر در این بخش مشخص نشده است.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل دستورالعمل‌های اجرایی مستقیم نیست. وظیفه آن اطلاع‌رسانی درباره ماهیت احتمالی ناقص/اشتباه پرامپت، لزوم بررسی مستقل repo، و جلوگیری از بازسازی موارد موجود است. این بخش هیچ مرحله اجرایی مشخصی را تعریف نمی‌کند و صرفاً یک راهنمای رفتاری برای مدل است.

**بخش مربوط از متن کاربر:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن راهنمای رفتاری بررسی مستقل repo به مستندات

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `docs/ARCHITECTURE.md` — `N/A` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اما از ساختار پروژه مشخص است که docs/ARCHITECTURE.md وجود دارد و مناسب‌ترین مکان برای افزودن یک بخش ارجاع به راهنمای رفتاری مدل است. مجری باید ابتدا محتوای فعلی را بخواند و بررسی کند آیا بخشی مشابه از قبل وجود دارد.
- `docs/README.md` — `N/A` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. docs/README.md در ساختار پروژه موجود است و می‌تواند لینک ارجاع به AGENT_EXECUTION_GUIDE.md را در خود داشته باشد.
- `docs/ROADMAP.md` — `N/A` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. بررسی کن آیا ROADMAP.md بخشی درباره فرآیند توسعه/contribution دارد که این راهنما باید به آن اضافه شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi (backend), nextjs (frontend). این تسک فنی نیست — صرفاً مستندسازی Markdown است. هیچ library یا framework خاصی درگیر نیست. فایل‌های مستند موجود در دایرکتوری docs/ شامل ARCHITECTURE.md، AUDIT_REPORT.md، PHASE_5_META_VALIDATION.md، README.md، ROADMAP.md، SYSTEM_REPORT_2026-02-08.md هستند.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `docs/AUDIT_REPORT.md` (سطر 1) — این فایل احتمالاً حاوی گزارش‌های بررسی کد است و ممکن است بخشی از راهنمای رفتاری مدل را پوشش دهد — مجری باید پیش از ایجاد فایل جدید، محتوای آن را بررسی کند تا از تکرار جلوگیری شود.
- `docs/PHASE_5_META_VALIDATION.md` (سطر 1) — نام این فایل نشان می‌دهد احتمالاً درباره validation و meta-level بررسی‌ها است — ممکن است بخشی از راهنمای رفتاری مدل را پوشش دهد و مجری باید آن را بخواند.
- `backend/app/main.py` (سطر 1) — entry point اصلی backend است و از oversight_service و project_service import می‌کند — اگر راهنمای رفتاری شامل نکاتی درباره ساختار startup پروژه باشد، این فایل مرجع است.
- `docs/SYSTEM_REPORT_2026-02-08.md` (سطر 1) — گزارش سیستمی که ممکن است وضعیت فعلی پروژه و تصمیمات معماری را مستند کرده باشد — مجری باید بررسی کند آیا راهنمای رفتاری مدل در آن ذکر شده است.

## 🌐 نقشهٔ وابستگی‌ها
این تسک صرفاً یک تسک مستندسازی است و هیچ تغییر کدی ایجاد نمی‌کند. فایل‌های تحت تأثیر:
- `docs/ARCHITECTURE.md`: ممکن است یک بخش ارجاع به راهنمای جدید دریافت کند
- `docs/README.md`: ممکن است لینک به AGENT_EXECUTION_GUIDE.md اضافه شود
- `docs/ROADMAP.md`: بررسی برای تکمیل احتمالی
- `docs/AUDIT_REPORT.md` و `docs/PHASE_5_META_VALIDATION.md`: باید پیش از ایجاد فایل جدید خوانده شوند تا از تکرار جلوگیری شود

هیچ فایل Python یا TypeScript تحت تأثیر قرار نمی‌گیرد. هیچ import یا dependency کدی تغییر نمی‌کند. این تسک فقط یک فایل Markdown جدید (`docs/AGENT_EXECUTION_GUIDE.md`) ایجاد می‌کند و احتمالاً چند خط به فایل‌های مستند موجود اضافه می‌کند.

## 🔍 Context و وضعیت فعلی
این تسک یک یادداشت هشداردهنده و راهنمای رفتاری برای مدل اجراکننده (Cursor/Copilot/ChatGPT) است که پیش از هر اقدام اجرایی باید رعایت شود. محتوای درخواست کاربر صراحتاً اعلام می‌کند که «شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود» و «هیچ فایل، کلاس یا تابعی برای تغییر در این بخش مشخص نشده است».

محورهای اصلی یادداشت کاربر:

۱. **احتمال پیاده‌سازی قبلی**: ممکن است بخشی یا تمام درخواست‌های آینده قبلاً در repo پیاده‌سازی شده باشند. مدل اجراکننده باید پیش از شروع با grep/search و خواندن فایل‌های مرتبط بررسی کند چه چیزی از قبل وجود دارد. اگر قابلیت/فایل/تابعی از قبل موجود است، نباید دوباره ساخته شود — فقط موارد ناقص یا اشتباه اصلاح/تکمیل شوند. اگر همه چیز از قبل به‌درستی انجام شده، یک کامیت توضیحی (no-op) ثبت شود.

۲. **مسئولیت مستقل مدل اجراکننده**: پیش از هر تغییر، مدل باید خودش ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کند. اگر تشخیص داد موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، باید بر اساس قضاوت خودش عمل کند. استناد به «خودت گفتی» به‌عنوان بهانه قابل قبول نیست.

۳. **تفسیر معیارهای پذیرش مبهم**: اگر AC ها مبهم/ناقص بودند، مدل باید بهترین تفسیر را انتخاب کند و در commit message توضیح دهد.

۴. **مدیریت کارهای طولانی**: خلاصه‌سازی ممنوع است. اگر یک کامیت گنجایش ندارد، در چندین کامیت متوالی انجام شود — ولی هیچ بخشی skip نشود. ترتیب کامیت‌ها باید منطقی باشد: foundation → core → integration → tests. در آخر یک checklist از همه کامیت‌ها در PR description نوشته شود.

این راهنما باید به‌صورت یک فایل مستند در پروژه ثبت شود تا در تمام تسک‌های آینده قابل ارجاع باشد. مناسب‌ترین مکان برای این مستند، دایرکتوری `docs/` است که از قبل در پروژه وجود دارد (فایل‌های ARCHITECTURE.md، AUDIT_REPORT.md، PHASE_5_META_VALIDATION.md، README.md، ROADMAP.md در آن موجودند).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] فایل docs/AGENT_EXECUTION_GUIDE.md در repo وجود داشته باشد و شامل ۵ بخش اصلی (بررسی پیش از اجرا، no-op commit، مسئولیت مستقل، ترتیب کامیت‌ها، AC های مبهم) باشد
- [ ] هیچ فایل Python یا TypeScript در این تسک تغییر نکرده باشد — تسک صرفاً مستندسازی است
- [ ] محتوای docs/ARCHITECTURE.md یا docs/README.md شامل یک ارجاع (لینک) به AGENT_EXECUTION_GUIDE.md باشد
- [ ] پیش از ایجاد فایل جدید، مجری باید بررسی کرده باشد که محتوای مشابه در docs/AUDIT_REPORT.md یا docs/PHASE_5_META_VALIDATION.md وجود ندارد — این بررسی باید در commit message مستند شده باشد
- [ ] commit message تسک باید شامل توضیح دلیل ایجاد فایل جدید (به‌جای تکمیل فایل موجود) باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. بررسی مستقل repo: ابتدا با grep/search بررسی کن آیا فایلی با محتوای مشابه این راهنما در docs/ یا ریشه repo وجود دارد (مثلاً CONTRIBUTING.md، AGENT_GUIDE.md، یا بخشی از ARCHITECTURE.md).

۲. اگر چنین مستندی وجود ندارد: فایل جدید `docs/AGENT_EXECUTION_GUIDE.md` ایجاد کن با محتوای کامل راهنمای رفتاری شامل:
   - بخش «بررسی پیش از اجرا» (grep/search برای موارد موجود)
   - بخش «قانون no-op commit» (وقتی همه چیز از قبل پیاده‌سازی شده)
   - بخش «مسئولیت مستقل مدل» (عدم استناد به پرامپت به‌عنوان بهانه)
   - بخش «مدیریت کارهای طولانی» (ترتیب کامیت‌ها: foundation → core → integration → tests)
   - بخش «تفسیر AC های مبهم» (بهترین تفسیر + توضیح در commit message)

۳. اگر بخشی از این راهنما در ARCHITECTURE.md یا README.md موجود است: فقط بخش‌های ناقص را تکمیل کن، نه بازنویسی کامل.

۴. یک لینک ارجاع به `docs/AGENT_EXECUTION_GUIDE.md` در `docs/README.md` یا `ARCHITECTURE.md` اضافه کن تا قابل کشف باشد.

۵. کامیت با پیام توضیحی: `docs(agent-guide): راهنمای رفتاری بررسی مستقل repo برای مدل اجراکننده`

## 💡 نمونه‌های قبل/بعد
**ایجاد فایل راهنمای رفتاری مدل اجراکننده**

_قبل:_
```
# وضعیت فعلی: فایل docs/AGENT_EXECUTION_GUIDE.md وجود ندارد
# هیچ راهنمای رفتاری مستقلی برای مدل اجراکننده در docs/ موجود نیست
```

_بعد:_
```
# docs/AGENT_EXECUTION_GUIDE.md

## ⚠️ راهنمای رفتاری مدل اجراکننده

### ۱. بررسی پیش از اجرا
پیش از هر تغییر، با grep/search بررسی کن چه چیزی از قبل وجود دارد.
اگر قابلیت/فایل/تابعی موجود است: آن را دوباره نساز.

### ۲. قانون no-op commit
اگر همه چیز از قبل پیاده‌سازی شده:
- یک کامیت توضیحی ثبت کن
- دقیقاً مشخص کن کدام فایل‌ها درخواست را پوشش می‌دهند

### ۳. مسئولیت مستقل
- اگر موقعیت پرامپت اشتباه است، بر اساس قضاوت خودت عمل کن
- «خودت گفتی» بهانه قابل قبول نیست

### ۴. ترتیب کامیت‌ها
foundation → core → integration → tests

### ۵. AC های مبهم
بهترین تفسیر را انتخاب کن و در commit message توضیح بده.
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `ls docs/AGENT_EXECUTION_GUIDE.md`
- `grep -l 'AGENT_EXECUTION_GUIDE' docs/`
- `grep -c 'no-op' docs/AGENT_EXECUTION_GUIDE.md`
- `grep -c 'foundation' docs/AGENT_EXECUTION_GUIDE.md`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **تکرار محتوا**: فایل‌های docs/AUDIT_REPORT.md و docs/PHASE_5_META_VALIDATION.md deep-read نشده‌اند — ممکن است بخشی از راهنمای رفتاری مدل از قبل در آن‌ها وجود داشته باشد. مجری باید پیش از ایجاد فایل جدید، این دو فایل را بخواند.

۲. **تداخل با ARCHITECTURE.md**: این فایل نیز deep-read نشده — ممکن است بخش «Contributing» یا «Development Guide» داشته باشد که با محتوای جدید تداخل ایجاد کند.

۳. **این تسک هیچ تغییر کدی ندارد**: اگر مجری اشتباهاً شروع به تغییر فایل‌های Python یا TypeScript کند، خارج از scope تسک است و باید متوقف شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: docs
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 32: رفع نشت Session دیتابیس در endpointهای analysis.py با استفاده از context manager یا finally block

**Scope:** این مرحله فقط به رفع نشت Session در فایل backend/app/api/routes/analysis.py می‌پردازد. تمام endpointهایی که مستقیماً SessionLocal() می‌سازند و db.close() را در finally ندارند، باید اصلاح شوند. فایل‌های model_profiles.py و project_health.py در این مرحله گنجانده نشده‌اند. راهکار پیشنهادی: استفاده از context manager (with SessionLocal() as db) یا اضافه کردن db.close() در finally قبل از raise. این مرحله شامل تست‌های unit test یا integration test نمی‌شود.
**Key terms:** backend/app/api/routes/analysis.py, SessionLocal, get_analysis_reports, get_analysis_report, db.close(), finally, HTTPException, context manager

**بخش مربوط از متن کاربر:**
```
نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا

- `backend/app/api/routes/analysis.py:277-290` — `get_analysis_reports` — این تابع درست بسته می‌شود — الگو را به بقیه تعمیم بده
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
      return ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:293-306` — `get_analysis_report` — استثناء قبل از finally باعث نشت می‌شود — باید db را قبل از raise ببندیم یا از context manager استفاده کنیم
  ```python
  db = SessionLocal()
  try:
      report = db.query(...).first()
      if not report:
          raise HTTPException(...)  # ⚠️ اینجا db بسته نمی‌شود
      return ...
  finally:
      db.close()
  ```

در چندین endpoint (analysis.py, model_profiles.py, project_health.py) Session دیتابیس با `SessionLocal()` ساخته می‌شود اما در مسیرهای خطا (Exception) بسته نمی‌شود. این باعث نشت connection و در نهایت exhaustion pool دیتابیس می‌شود. نمونه: analysis.py خطوط 277-290 و 293-306 و 309-325 و 328-370 — همه از `SessionLocal()` استفاده می‌کنند و `db.close()` را در `finally` ندارند.
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع نشت Session دیتابیس در endpointهای analysis.py با finally/context manager

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:277-290` — `get_analysis_reports` — این تابع الگوی صحیح را دارد — finally با db.close() وجود دارد. این الگو باید به توابع get_analysis_report (293-306)، endpoint خطوط 309-325 و endpoint خطوط 328-370 تعمیم داده شود.
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
      return ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:293-306` — `get_analysis_report` — این تابع مشکل نشت Session دارد — وقتی HTTPException raise می‌شود، اگر finally: db.close() وجود نداشته باشد، connection نشت می‌کند. باید finally block اضافه شود.
  ```python
  db = SessionLocal()
  try:
      report = db.query(...).first()
      if not report:
          raise HTTPException(...)  # ⚠️ اینجا db بسته نمی‌شود
      return ...
  ```
- `backend/app/api/routes/analysis.py:309-325` — `endpoint at line 309` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. طبق توضیح کاربر، این endpoint نیز از SessionLocal() استفاده می‌کند و db.close() در finally ندارد.
  ```python
  db = SessionLocal()
  try:
      ...
      # فاقد finally: db.close()
      return ...
  ```
- `backend/app/api/routes/analysis.py:328-370` — `endpoint at line 328` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. طبق توضیح کاربر، این endpoint نیز از SessionLocal() استفاده می‌کند و db.close() در finally ندارد.
  ```python
  db = SessionLocal()
  try:
      ...
      # فاقد finally: db.close()
      return ...
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI + SQLAlchemy (backend) + Next.js 14 (frontend). کتابخانه‌های مرتبط: sqlalchemy>=2.0.0 (از requirements.txt)، fastapi>=0.109.0. الگوی مدیریت Session: دو الگو در پروژه وجود دارد — (1) `db = SessionLocal()` با `try/finally` صریح که در analysis.py استفاده شده، (2) `db=Depends(get_db)` که در model_profiles.py و project_health.py استفاده شده و ایمن‌تر است. راهکار پیشنهادی: اضافه کردن `finally: db.close()` به endpointهای معیوب در analysis.py بدون تغییر معماری کلی.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — تعریف SessionLocal و get_db در این فایل است. 15 فایل آن را import می‌کنند از جمله analysis.py. اگر تصمیم به استفاده از context manager گرفته شود، باید بررسی شود SessionLocal از __enter__/__exit__ پشتیبانی می‌کند یا نه.
- `backend/app/api/routes/project_health.py` (سطر 24) — طبق درخواست کاربر، این فایل در این مرحله اصلاح نمی‌شود اما همین مشکل نشت Session را دارد. برای آگاهی مجری ذکر می‌شود تا در مرحله بعد اصلاح شود.
- `backend/app/api/routes/model_profiles.py` (سطر 148) — طبق درخواست کاربر، این فایل در این مرحله اصلاح نمی‌شود اما همین مشکل نشت Session را دارد. در خطوط 157-245 از db=Depends(get_db) استفاده می‌کند که الگوی متفاوتی است.
- `backend/app/models/analysis_report.py` (سطر 1) — مدل AnalysisReport که در analysis.py با db.query(AnalysisReport) استفاده می‌شود اینجا تعریف شده. تغییر در نحوه مدیریت session روی query های این مدل تأثیر مستقیم دارد.
- `backend/app/main.py` (سطر 1) — router های analysis.py در main.py register می‌شوند. اگر تغییری در signature endpoint ها ایجاد شود (مثلاً تبدیل به async context manager) باید سازگاری با app startup بررسی شود.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/api/routes/analysis.py` از `backend/app/core/database.py` برای `SessionLocal` import می‌کند (15 فایل این ماژول را import می‌کنند). مدل `AnalysisReport` از `backend/app/models/analysis_report.py` در query های این فایل استفاده می‌شود. سرویس `backend/app/services/model_profiler.py` نیز توسط analysis.py import می‌شود (6 فایل آن را import می‌کنند). تغییر الگوی مدیریت Session در analysis.py فقط روی همین فایل تأثیر دارد چون هر endpoint Session خود را مستقل می‌سازد — اما اگر `SessionLocal` در `database.py` تغییر کند، روی تمام 15 فایل importer تأثیر می‌گذارد. در این تسک فقط `analysis.py` تغییر می‌کند و `database.py` دست نخورده می‌ماند.

## 🔍 Context و وضعیت فعلی
این تسک به رفع نشت Session دیتابیس در فایل `backend/app/api/routes/analysis.py` می‌پردازد. طبق درخواست کاربر، تمام endpointهایی که مستقیماً `SessionLocal()` می‌سازند و `db.close()` را در `finally` ندارند باید اصلاح شوند. فایل‌های `model_profiles.py` و `project_health.py` در این مرحله گنجانده نشده‌اند.

مشکل اصلی: در چندین endpoint از `analysis.py`، Session دیتابیس با `SessionLocal()` ساخته می‌شود اما در مسیرهای خطا (Exception یا HTTPException) بسته نمی‌شود. این باعث نشت connection و در نهایت exhaustion pool دیتابیس می‌شود.

خطوط مشخص‌شده توسط کاربر:
- `backend/app/api/routes/analysis.py:277-290` — تابع `get_analysis_reports` — این تابع الگوی درست دارد (finally با db.close()) و باید به بقیه تعمیم داده شود.
- `backend/app/api/routes/analysis.py:293-306` — تابع `get_analysis_report` — استثناء قبل از finally باعث نشت می‌شود؛ وقتی `raise HTTPException(...)` اجرا می‌شود، db بسته نمی‌شود.
- `backend/app/api/routes/analysis.py:309-325` — endpoint دیگری با همین مشکل.
- `backend/app/api/routes/analysis.py:328-370` — endpoint دیگری با همین مشکل.

راهکار پیشنهادی کاربر: استفاده از context manager (`with SessionLocal() as db`) یا اضافه کردن `db.close()` در `finally` قبل از `raise`. این مرحله شامل تست‌های unit test یا integration test نمی‌شود.

کلیدواژه‌های فنی: `backend/app/api/routes/analysis.py`, `SessionLocal`, `get_analysis_reports`, `get_analysis_report`, `db.close()`, `finally`, `HTTPException`, `context manager`.

الگوی صحیح که باید به همه تعمیم یابد (از خطوط 277-290 همان فایل):
```python
db = SessionLocal()
try:
    query = db.query(AnalysisReport)
    ...
    return ...
finally:
    db.close()
```
الگوی معیوب (خطوط 293-306) که باید اصلاح شود:
```python
db = SessionLocal()
try:
    report = db.query(...).first()
    if not report:
        raise HTTPException(...)  # ⚠️ اینجا db بسته نمی‌شود
    return ...
finally:
    db.close()  # این finally وجود ندارد یا ناقص است
```

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تمام فراخوانی‌های SessionLocal() در analysis.py باید یک finally: db.close() متناظر داشته باشند — grep روی فایل نباید هیچ SessionLocal() بدون finally پیدا کند
- [ ] endpoint GET /api/analysis/reports باید با status 200 پاسخ دهد و session leak نداشته باشد
- [ ] endpoint GET /api/analysis/reports/{report_id} با id نامعتبر باید 404 برگرداند و session را ببندد — یعنی finally block اجرا شده باشد
- [ ] در فایل analysis.py هیچ بلوک try که SessionLocal() دارد نباید بدون finally: db.close() باشد — بررسی static با شمارش تعداد SessionLocal() و تعداد db.close() در finally
- [ ] فایل‌های model_profiles.py و project_health.py در این مرحله تغییر نکرده باشند — git diff نباید این فایل‌ها را نشان دهد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل `backend/app/api/routes/analysis.py` را باز کن و تمام مکان‌هایی که `SessionLocal()` فراخوانی می‌شود را شناسایی کن (خطوط 277-290، 293-306، 309-325، 328-370 و هر مورد دیگری در همین فایل).
2. برای هر endpoint که `db = SessionLocal()` دارد ولی `finally: db.close()` ندارد، یکی از دو الگو را اعمال کن:
   - **الگو A (context manager):** `with SessionLocal() as db:` — اگر SQLAlchemy session از `contextmanager` پشتیبانی می‌کند.
   - **الگو B (try/finally صریح):** اطمینان حاصل کن که `finally: db.close()` بعد از هر `try` وجود دارد، حتی اگر داخل `try` یک `raise HTTPException` باشد — چون `finally` همیشه اجرا می‌شود حتی بعد از raise.
3. تابع `get_analysis_reports` (خطوط 277-290) را به‌عنوان الگوی مرجع نگه دار — این تابع درست پیاده‌سازی شده.
4. تابع `get_analysis_report` (خطوط 293-306) را اصلاح کن: اطمینان حاصل کن `finally: db.close()` بعد از بلوک `try` وجود دارد.
5. endpointهای خطوط 309-325 و 328-370 را به همین شکل اصلاح کن.
6. یک grep سراسری روی `analysis.py` برای `SessionLocal()` اجرا کن تا مطمئن شوی هیچ مورد جاافتاده‌ای نیست.
7. فایل‌های `model_profiles.py` و `project_health.py` را در این مرحله دست نزن — طبق درخواست کاربر خارج از scope هستند.

## 💡 نمونه‌های قبل/بعد
**تابع get_analysis_report — اضافه کردن finally block برای جلوگیری از نشت Session**

_قبل:_
```
db = SessionLocal()
try:
    report = db.query(AnalysisReport).filter(
        AnalysisReport.id == report_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    return {"success": True, "report": report}
```

_بعد:_
```
db = SessionLocal()
try:
    report = db.query(AnalysisReport).filter(
        AnalysisReport.id == report_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    return {"success": True, "report": report}
finally:
    db.close()  # ✅ همیشه اجرا می‌شود — حتی بعد از raise HTTPException
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -n 'SessionLocal()' backend/app/api/routes/analysis.py`
- `grep -n 'db.close()' backend/app/api/routes/analysis.py`
- `grep -n 'finally:' backend/app/api/routes/analysis.py`
- `python -m pytest backend/tests/ -k 'analysis' -v --tb=short`
- `python -c "import ast; ast.parse(open('backend/app/api/routes/analysis.py').read()); print('Syntax OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
1. اگر `SessionLocal` در `backend/app/core/database.py` از context manager (`__enter__`/`__exit__`) پشتیبانی نکند، استفاده از `with SessionLocal() as db` باعث AttributeError می‌شود — پس الگوی try/finally صریح ایمن‌تر است. 2. اگر در endpointهای 309-325 و 328-370 قبلاً یک `finally` وجود داشته که `db.close()` نداشته، اضافه کردن `db.close()` به آن finally کافی است و نباید ساختار try را تغییر داد. 3. تغییر در `analysis.py` روی 5 فایل importer آن (از جمله `backend/app/main.py`) تأثیر ندارد چون فقط منطق داخلی endpoint تغییر می‌کند نه signature. 4. اگر `db.close()` دوبار فراخوانی شود (مثلاً یک‌بار در try و یک‌بار در finally)، SQLAlchemy خطا نمی‌دهد اما باید مطمئن شد که `db.close()` فقط در finally باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 33: جایگزینی SessionLocal مستقیم با context manager یا Depends(get_db) در تمام endpointها

**Scope:** این بخش شامل جایگزینی تمام استفاده‌های مستقیم از SessionLocal() در endpointها با context manager (try/finally یا async context manager) یا Depends(get_db) است. هدف اطمینان از بسته شدن session در همه مسیرها (موفقیت و خطا) و جلوگیری از نشت connection است. خارج از scope: تغییر منطق business، اضافه کردن endpoint جدید، یا تغییر ساختار database. نکته حیاتی: این تغییر باید در تمام فایل‌های routes اعمال شود و تست نشت connection با 1000 درخواست هم‌زمان پاس شود.
**Key terms:** SessionLocal, Depends(get_db), context manager, try/finally, backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/api/routes/github_import.py, backend/app/api/routes/model_profiles.py

**بخش مربوط از متن کاربر:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند
- [ ] همه endpointها از Depends(get_db) یا async context manager استفاده کنند
- [ ] تست نشت connection با 1000 درخواست هم‌زمان پاس شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. تمام `SessionLocal()` ها را با context manager یا try/finally جایگزین کن تا در همه مسیرها (موفقیت و خطا) session بسته شود. یا از `Depends(get_db)` در همه endpointها استفاده کن.
```

## 🎯 هدف (خلاصه ساختاریافته)
جایگزینی SessionLocal مستقیم با Depends(get_db) در تمام route‌های backend

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:271-290` — `get_analysis_reports` — این endpoint از SessionLocal مستقیم استفاده می‌کند. باید به Depends(get_db) تبدیل شود. همین pattern در get_analysis_report (خط ۲۹۳)، delete_analysis_report (خط ۳۰۹)، download_analysis_report (خط ۳۲۸)، get_schedule (خط ۵۹۴)، update_schedule (خط ۶۲۴)، delete_schedule (خط ۶۵۴)، get_analysis_stats (خط ۶۷۹) تکرار شده.
  ```python
  @router.get("/reports", response_model=List[AnalysisReportSchema])
  async def get_analysis_reports(
      project_id: Optional[str] = None,
      limit: int = 20
  ):
      """دریافت لیست گزارش‌های تحلیل"""
      from ...core.database import SessionLocal
      from ...models.analysis_report import AnalysisReport
  
      db = SessionLocal()
      try:
          query = db.query(AnalysisReport)
          if project_id:
              query = query.filter(AnalysisReport.project_id == project_id)
          reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
          return [AnalysisReportSchema.model_validate(r) for r in reports]
      finally:
          db.close()
  ```
- `backend/app/api/routes/analysis.py:115-124` — `run_analysis_stream / run_analysis_task` — این SessionLocal داخل یک nested async coroutine (run_analysis_task) است. Depends(get_db) اینجا کار نمی‌کند. باید try/finally با analysis_db.close() اضافه شود تا در همه مسیرها (موفقیت، exception، cancel) session بسته شود. این یک نشت واقعی است.
  ```python
  # 🔴 ایجاد db session برای استفاده از پرامپت‌های دیتابیس
                  from ...core.database import SessionLocal
                  analysis_db = SessionLocal()
  
                  # ساخت DeepAnalysisService با progress callback و db_session
                  deep_analyzer = DeepAnalysisService(
                      ai_manager=ai_manager,
                      progress_callback=progress_callback,
                      db_session=analysis_db  # 🔴 برای استفاده از پرامپت‌های دیتابیس
                  )
  ```
- `backend/app/api/routes/github_import.py:133-157` — `import_repository / auto_setup_project_memory block` — این SessionLocal داخل handler است و try/finally دارد — اما چون داخل یک try/except بیرونی است، باید مطمئن شد exception path هم session را می‌بندد. این pattern قابل قبول است اما باید با contextlib.asynccontextmanager یا with statement یکپارچه شود.
  ```python
  try:
              from ...services.project_auto_setup import auto_setup_project_memory
              from ...core.database import SessionLocal
  
              db_session = SessionLocal()
              try:
                  auto_result = await auto_setup_project_memory(
                      project_id=save_result["project_id"],
                      project_name=result.get("name", "پروژه"),
                      project_description=result.get("description", ""),
                      project_type="github_import",
                      files=result.get("files", []),
                      use_ai=True,
                      db_session=db_session
                  )
              finally:
                  db_session.close()
  ```
- `backend/app/api/routes/model_profiles.py:142-149` — `get_all_profiles` — این فایل الگوی صحیح Depends(get_db) را دارد — می‌تواند به عنوان reference implementation برای سایر فایل‌ها استفاده شود. اما باید بررسی شود که _create_default_profiles(db) داخل همین endpoint نیز SessionLocal جدید نمی‌سازد.
  ```python
  @router.get("/profiles")
  async def get_all_profiles(
      sort_by: str = Query("overall_score", description="فیلد مرتب‌سازی"),
      order: str = Query("desc", description="ترتیب: asc یا desc"),
      limit: int = Query(50, description="تعداد نتایج"),
      use_fallback: bool = Query(True, description="استفاده از داده‌های پیش‌فرض در صورت خالی بودن"),
      db=Depends(get_db)
  ):
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. کتابخانه‌های مرتبط: SQLAlchemy>=2.0.0 (ORM)، FastAPI Depends (dependency injection)، aiosqlite>=0.19.0 (async SQLite). الگوی صحیح در FastAPI: استفاده از `Depends(get_db)` که یک generator است و session را در finally می‌بندد. برای nested coroutines که Depends کار نمی‌کند، باید از `contextlib.contextmanager` یا صریح `try/finally` استفاده شود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — تعریف get_db generator و SessionLocal — این فایل توسط ۱۷ فایل import می‌شود. get_db باید به درستی yield کند و session را در finally ببندد. هر تغییری در این فایل روی همه routes اثر می‌گذارد.
- `backend/app/api/routes/security_analysis.py` (سطر 1) — از database.py import می‌کند — احتمالاً SessionLocal مستقیم دارد. باید بررسی و اصلاح شود.
- `backend/app/api/routes/project_health.py` (سطر 1) — از database.py و models/setting.py import می‌کند — یکی از فایل‌هایی که احتمالاً SessionLocal مستقیم دارد.
- `backend/app/api/routes/settings.py` (سطر 1) — از models/setting.py import می‌کند — احتمالاً SessionLocal مستقیم در endpointهای CRUD دارد.
- `backend/app/api/routes/simple_projects.py` (سطر 1) — از oversight_service.py import می‌کند — باید بررسی شود SessionLocal مستقیم دارد یا نه.
- `backend/app/api/routes/render_logs.py` (سطر 1) — از models/setting.py و logging_utils.py import می‌کند — احتمالاً SessionLocal مستقیم دارد.

## 🌐 نقشهٔ وابستگی‌ها
تابع `get_db` در `backend/app/core/database.py` توسط ۱۷ فایل import می‌شود. فایل‌های اصلی که باید اصلاح شوند: `backend/app/api/routes/analysis.py` (۸+ endpoint با SessionLocal مستقیم)، `backend/app/api/routes/github_import.py` (SessionLocal داخل handler)، `backend/app/api/routes/security_analysis.py`، `backend/app/api/routes/project_health.py`، `backend/app/api/routes/settings.py`، `backend/app/api/routes/render_logs.py`، `backend/app/api/routes/simple_projects.py`. فایل `backend/app/api/routes/model_profiles.py` الگوی صحیح `Depends(get_db)` را دارد و باید به عنوان reference استفاده شود. `backend/app/services/deep_analysis_service.py` و `backend/app/services/ai_manager.py` نیز `database.py` را import می‌کنند اما خارج از scope این تسک هستند (services نه routes). تغییر signature endpointها (اضافه کردن `db: Session = Depends(get_db)`) روی هیچ frontend callی اثر نمی‌گذارد چون Depends یک FastAPI dependency injection است و در request body/query params ظاهر نمی‌شود.

## 🔍 Context و وضعیت فعلی
درخواست کاربر: جایگزینی تمام استفاده‌های مستقیم از `SessionLocal()` در endpointها با context manager (try/finally یا async context manager) یا `Depends(get_db)` در تمام فایل‌های routes. هدف اطمینان از بسته شدن session در همه مسیرها (موفقیت و خطا) و جلوگیری از نشت connection است.

کلیدواژه‌های اصلی: `SessionLocal`, `Depends(get_db)`, `context manager`, `try/finally`, `backend/app/api/routes/analysis.py`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/github_import.py`, `backend/app/api/routes/model_profiles.py`

شواهد در کد واقعی:
- در `backend/app/api/routes/analysis.py` خط ۲۷۷-۲۸۹: تابع `get_analysis_reports` از `db = SessionLocal()` مستقیم استفاده می‌کند و فقط در `finally` بسته می‌شود — اما این pattern در همه endpointها یکسان نیست.
- در همان فایل خط ۲۹۸-۳۰۶: `get_analysis_report` نیز `db = SessionLocal()` مستقیم دارد.
- در `backend/app/api/routes/analysis.py` خط ۳۱۴-۳۲۵: `delete_analysis_report` نیز همین pattern.
- در `backend/app/api/routes/analysis.py` خط ۱۱۶-۱۱۷: داخل `run_analysis_stream` یک `analysis_db = SessionLocal()` ایجاد می‌شود که در `finally` بسته نمی‌شود — این یک نشت واقعی است.
- در `backend/app/api/routes/github_import.py` خط ۱۳۶-۱۵۵: داخل `import_repository` یک `db_session = SessionLocal()` ایجاد می‌شود که در `finally` بسته می‌شود — این درست است اما باید با `Depends(get_db)` یکپارچه شود.
- در `backend/app/api/routes/model_profiles.py` خط ۱۴۸: از `db=Depends(get_db)` استفاده می‌شود — این الگوی صحیح است.

خارج از scope: تغییر منطق business، اضافه کردن endpoint جدید، یا تغییر ساختار database.

نکته حیاتی از کاربر: این تغییر باید در تمام فایل‌های routes اعمال شود و تست نشت connection با 1000 درخواست هم‌زمان پاس شود. معیارهای پذیرش: هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند، همه endpointها از Depends(get_db) یا async context manager استفاده کنند، تست نشت connection با 1000 درخواست هم‌زمان پاس شود، هیچ تستی fail نشود (pytest)، linter بدون warning عبور کند، type-check موفق باشد (mypy).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ endpoint در backend/app/api/routes/ از SessionLocal() مستقیم بدون try/finally یا Depends(get_db) استفاده نکند
- [ ] تمام endpointهای CRUD در analysis.py (get_analysis_reports، get_analysis_report، delete_analysis_report، download_analysis_report، get_schedule، update_schedule، delete_schedule، get_analysis_stats) از db: Session = Depends(get_db) در signature استفاده کنند
- [ ] GET /api/analysis/reports → 200 با فیلد array خالی یا پر (بدون خطای connection leak)
- [ ] تست نشت connection: 1000 درخواست هم‌زمان به GET /api/analysis/reports بدون افزایش تعداد connection های باز در pool
- [ ] pytest backend/tests/ بدون هیچ failure اجرا شود
- [ ] analysis_db در run_analysis_stream (backend/app/api/routes/analysis.py خط ۱۱۷) در همه مسیرها (موفقیت، exception، task cancel) بسته شود
- [ ] mypy یا ruff روی backend/app/api/routes/ بدون error اجرا شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ## مراحل اجرایی

1. **شناسایی همه موارد SessionLocal مستقیم در routes**: با grep روی `backend/app/api/routes/` تمام `SessionLocal()` را پیدا کن. فایل‌های اصلی: `analysis.py`, `github_import.py`, `model_profiles.py`, `security_analysis.py`, `project_health.py`, `project_journal.py`, `project_memory.py`, `render_logs.py`, `settings.py`, `simple_projects.py`, `system_prompts.py`, `unified_api.py`.

2. **اصلاح `backend/app/api/routes/analysis.py`**:
   - توابع `get_analysis_reports` (خط ۲۷۱)، `get_analysis_report` (خط ۲۹۳)، `delete_analysis_report` (خط ۳۰۹)، `download_analysis_report` (خط ۳۲۸)، `get_schedule` (خط ۵۹۴)، `update_schedule` (خط ۶۲۴)، `delete_schedule` (خط ۶۵۴)، `get_analysis_stats` (خط ۶۷۹) — همه باید `db: Session = Depends(get_db)` به signature اضافه کنند و `db = SessionLocal()` + `try/finally db.close()` را حذف کنند.
   - **مهم**: در `run_analysis_stream` (خط ۱۱۶-۱۱۷) `analysis_db = SessionLocal()` داخل coroutine است — باید `try/finally` با `analysis_db.close()` اضافه شود چون Depends در nested coroutine کار نمی‌کند.

3. **اصلاح `backend/app/api/routes/github_import.py`**:
   - `import_repository` (خط ۹۵): `db_session = SessionLocal()` داخل handler — باید `try/finally` با `db_session.close()` تضمین شود (خط ۱۵۴ فقط در `finally` بسته می‌شود — بررسی کن exception path هم cover شده باشد).

4. **اصلاح سایر route‌ها**: برای هر endpoint که `db = SessionLocal()` دارد و `db: Session = Depends(get_db)` ندارد، signature را تغییر بده و `try/finally db.close()` را حذف کن.

5. **اطمینان از import**: در هر فایل اصلاح‌شده، `from ...core.database import get_db` و `from sqlalchemy.orm import Session` import شده باشد.

6. **اجرای تست‌ها**: `pytest backend/tests/ -v` و بررسی نشت connection با ابزار load test.

## 💡 نمونه‌های قبل/بعد
**تبدیل SessionLocal مستقیم به Depends(get_db) در get_analysis_reports**

_قبل:_
```
@router.get("/reports", response_model=List[AnalysisReportSchema])
async def get_analysis_reports(
    project_id: Optional[str] = None,
    limit: int = 20
):
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisReport

    db = SessionLocal()
    try:
        query = db.query(AnalysisReport)
        if project_id:
            query = query.filter(AnalysisReport.project_id == project_id)
        reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
        return [AnalysisReportSchema.model_validate(r) for r in reports]
    finally:
        db.close()
```

_بعد:_
```
from sqlalchemy.orm import Session
from ...core.database import get_db
from ...models.analysis_report import AnalysisReport

@router.get("/reports", response_model=List[AnalysisReportSchema])
async def get_analysis_reports(
    project_id: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(AnalysisReport)
    if project_id:
        query = query.filter(AnalysisReport.project_id == project_id)
    reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
    return [AnalysisReportSchema.model_validate(r) for r in reports]
```

**اصلاح SessionLocal داخل nested coroutine در run_analysis_stream**

_قبل:_
```
analysis_db = SessionLocal()

# ساخت DeepAnalysisService با progress callback و db_session
deep_analyzer = DeepAnalysisService(
    ai_manager=ai_manager,
    progress_callback=progress_callback,
    db_session=analysis_db
)
# ... rest of code
# هیچ finally برای analysis_db وجود ندارد
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    # ساخت DeepAnalysisService با progress callback و db_session
    deep_analyzer = DeepAnalysisService(
        ai_manager=ai_manager,
        progress_callback=progress_callback,
        db_session=analysis_db
    )
    # ... rest of code
except Exception as e:
    logger.error(f"Streaming analysis failed: {e}", exc_info=True)
    await progress_queue.put({"event": "error", "message": str(e), "error": True})
finally:
    analysis_db.close()  # تضمین بسته شدن در همه مسیرها
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/api/routes/ | grep -v 'try\|finally\|Depends'`
- `pytest backend/tests/ -v --tb=short`
- `ruff check backend/app/api/routes/`
- `python -m mypy backend/app/api/routes/ --ignore-missing-imports`
- `grep -rn 'Depends(get_db)' backend/app/api/routes/ | wc -l`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **نشت واقعی در analysis.py خط ۱۱۷**: `analysis_db = SessionLocal()` داخل `run_analysis_task` coroutine بدون `finally` — اگر task cancel شود (خط ۲۵۷: `analysis_task.cancel()`)، session هرگز بسته نمی‌شود. این بالاترین ریسک است.
۲. **تغییر signature endpoint**: اضافه کردن `db: Session = Depends(get_db)` به endpointهایی که قبلاً این parameter نداشتند — اگر جایی این endpoint را مستقیم (نه از طریق HTTP) صدا می‌زند، باید بررسی شود. در `backend/app/services/deep_analysis_service.py` و `backend/app/services/ai_manager.py` که از database.py import می‌کنند، این تغییر اثر ندارد.
۳. **get_db generator در database.py**: اگر `get_db` در `backend/app/core/database.py` به درستی `yield` و `finally db.close()` نداشته باشد، تمام Depends(get_db) ها نشت خواهند داشت — باید قبل از شروع این فایل را verify کرد.
۴. **۱۷ فایل importer**: `backend/app/core/database.py` توسط ۱۷ فایل import می‌شود — هر تغییر در get_db روی همه اثر می‌گذارد.
۵. **nested SessionLocal در github_import.py**: `db_session = SessionLocal()` داخل `import_repository` (خط ۱۳۶) در یک try/except بیرونی است — اگر exception قبل از `try` داخلی رخ دهد، session بسته نمی‌شود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 34: رفع نشت session با استفاده از context manager

**Scope:** این بخش شامل تغییر الگوی مدیریت session در کد backend از try/finally به async with context manager است. فقط فایل‌هایی که از SessionLocal استفاده می‌کنند تحت تأثیر قرار می‌گیرند. تغییرات باید در routes و service‌های مرتبط اعمال شود. تست‌ها نیز باید به‌روزرسانی شوند.
**Key terms:** SessionLocal, async with, context manager, HTTPException, db.close()

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
db = SessionLocal()
try:
    ...
    raise HTTPException(...)
finally:
    db.close()
```

_بعد:_
```
async with SessionLocal() as db:
    ...
    raise HTTPException(...)
# خودکار بسته می‌شود
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

db = SessionLocal()
try:
    ...
    raise HTTPException(...)
finally:
    db.close()
```

_بعد:_
```
async with SessionLocal() as db:
    ...
    raise HTTPException(...)
# خودکار بسته می‌شود
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
SessionLocal, async with, context manager, HTTPException, db.close()
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع نشت session با context manager در SessionLocal

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:91-101` — `get_available_models` — الگوی try/finally در متد get_available_models — اگر query خطا بدهد یا HTTPException raise شود، db.close() ممکن است در برخی edge caseها اجرا نشود. باید به `with SessionLocal() as db:` تبدیل شود.
  ```python
  db = SessionLocal()
          try:
              db_settings = db.query(ModelSettings).all()
              db_settings_map = {s.model_id: s for s in db_settings}
              logger.debug(f"Loaded {len(db_settings_map)} model settings from DB")
          finally:
              db.close()
  ```
- `backend/app/services/ai_manager.py:382-392` — `get_enabled_status` — متد get_enabled_status — همان الگوی try/finally. این متد از generate() فراخوانی می‌شود و در hot path قرار دارد. نشت session اینجا می‌تواند connection pool را تخلیه کند.
  ```python
  db = SessionLocal()
          try:
              db_setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
              if db_setting:
                  return bool(db_setting.enabled)
              # اگر تنظیمات نداشت، از registry استفاده کن
              model = get_model(model_id)
              return model.enabled if model else False
          finally:
              db.close()
  ```
- `backend/app/services/ai_manager.py:629-654` — `_do_log` — تابع داخلی _do_log در _log_ai_usage_async — این تابع در thread executor اجرا می‌شود. الگوی try/finally اینجا هم باید به with SessionLocal() as db: تبدیل شود.
  ```python
  def _do_log() -> None:
                  from ..core.database import SessionLocal
                  from ..models.ai_log import AILog
                  db = SessionLocal()
                  try:
                      AILog.log_request(
                          db,
                          provider=provider_str,
                          model=model_id,
                          request_type="chat",
                          prompt=prompt_text,
                          response=response_text,
                          input_tokens=input_tokens,
                          output_tokens=output_tokens,
                          cost=cost,
                          latency_ms=int(getattr(response, "latency_ms", 0) or 0),
                          project_id=project_id,
                          debate_id=debate_id,
                          status=status,
                          error_message=str(err)[:500] if err else None,
                          extra_data=extra,
                      )
                  except Exception as _de:
                      slog.debug(f"AILog write failed: {_de}")
                  finally:
                      db.close()
  ```
- `backend/app/core/database.py` — `SessionLocal` — این فایل deep-read نشده — مجری باید تأیید کند که SessionLocal از نوع sync sessionmaker است یا async. اگر sync است: `with SessionLocal() as db:` کار می‌کند. اگر async است: `async with AsyncSessionLocal() as db:` لازم است. این تأیید پیش‌نیاز همه تغییرات دیگر است.
- `backend/app/api/routes/analysis.py` — این فایل deep-read نشده — مجری باید با grep بررسی کند. طبق نقشه import، این route از ai_manager، model_profiler و ai_profile import می‌کند و احتمالاً مستقیم SessionLocal دارد.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI + SQLAlchemy (sync یا async) + Next.js. کتابخانه‌های مرتبط: `sqlalchemy>=2.0.0` (از requirements.txt)، `aiosqlite>=0.19.0` (نشان‌دهنده احتمال async session). در SQLAlchemy 2.0، sessionmaker با `with` context manager کار می‌کند اگر Session.__enter__ تعریف شده باشد. برای async: `AsyncSession` + `async_sessionmaker` + `async with`. در FastAPI معمول‌ترین الگو استفاده از `Depends(get_db)` با generator است که `yield` + `finally` دارد — این الگو ایمن‌تر از مستقیم SessionLocal است.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/database.py` (سطر 1) — تعریف SessionLocal — 22 فایل آن را import می‌کنند. باید بررسی شود آیا SessionLocal از contextmanager پشتیبانی می‌کند (یعنی __enter__/__exit__ دارد). اگر نه، باید یک wrapper اضافه شود.
- `backend/app/services/health_to_issues_service.py` (سطر 1) — طبق نقشه import، هم database.py و هم ai_manager.py را import می‌کند — احتمال بالای استفاده مستقیم از SessionLocal دارد.
- `backend/app/services/log_to_issues_service.py` (سطر 1) — طبق نقشه import، هم database.py و هم ai_manager.py را import می‌کند — باید برای الگوی try/finally بررسی شود.
- `backend/app/services/journal_service.py` (سطر 1) — طبق نقشه import، database.py را import می‌کند — باید بررسی شود.
- `backend/app/services/oversight_service.py` (سطر 1) — 12 فایل آن را import می‌کنند و خود از database.py استفاده می‌کند — یکی از بزرگ‌ترین هاب‌های پروژه است و احتمالاً چندین SessionLocal مستقیم دارد.
- `backend/app/services/render_service.py` (سطر 1) — طبق نقشه import، از models/setting.py استفاده می‌کند که نیاز به SessionLocal دارد.
- `backend/app/api/routes/models.py` (سطر 1) — از ai_profile و model_profiler import می‌کند — احتمال استفاده مستقیم از SessionLocal در route handlers.

## 🌐 نقشهٔ وابستگی‌ها
تغییر الگوی SessionLocal روی تمام ۲۲ فایلی که `backend/app/core/database.py` را import می‌کنند تأثیر می‌گذارد. مهم‌ترین‌ها:
- `backend/app/services/ai_manager.py`: ۳ مکان مستقیم (get_available_models، get_enabled_status، _do_log) + تابع load_api_keys_and_reset
- `backend/app/services/health_to_issues_service.py` و `log_to_issues_service.py`: هر دو database.py و ai_manager.py را import می‌کنند
- `backend/app/services/journal_service.py`: database.py را import می‌کند
- `backend/app/services/oversight_service.py`: هاب مرکزی با ۱۲ importer — تغییر اینجا cascade effect دارد
- `backend/app/api/routes/analysis.py`: از ai_manager و model_profiler استفاده می‌کند
- `backend/app/models/setting.py`: توسط ۸ فایل import می‌شود که همه نیاز به session دارند
پیش‌نیاز اصلی: تأیید نوع SessionLocal در `backend/app/core/database.py` (sync vs async) قبل از هر تغییری.

## 🔍 Context و وضعیت فعلی
این تسک به رفع الگوی مدیریت session دیتابیس در سراسر backend می‌پردازد. مشکل اصلی این است که در فایل‌های متعددی از الگوی `db = SessionLocal()` + `try/finally` + `db.close()` استفاده شده که در صورت raise شدن `HTTPException` یا خطاهای غیرمنتظره، ممکن است `db.close()` هرگز فراخوانی نشود و منجر به session leak شود.

کاربر به‌صراحت خواسته است الگوی قبل:
```
db = SessionLocal()
try:
    ...
    raise HTTPException(...)
finally:
    db.close()
```
به الگوی بعد تبدیل شود:
```
async with SessionLocal() as db:
    ...
    raise HTTPException(...)
# خودکار بسته می‌شود
```

شواهد در کد واقعی پروژه:
- `backend/app/services/ai_manager.py` خطوط ۹۵-۱۰۱: `db = SessionLocal()` + `try/finally db.close()` در متد `get_available_models`
- همان فایل خطوط ۳۸۳-۳۹۲: `db = SessionLocal()` + `try/finally db.close()` در متد `get_enabled_status`
- همان فایل خطوط ۷۷۷-۸۰۰: `db = SessionLocal()` + `db.close()` در تابع `load_api_keys_and_reset`
- `backend/app/services/analysis_progress_manager.py` خطوط ۶۰-۶۸ و ۸۲-۹۴: استفاده از `db_session` که از بیرون inject می‌شود (این فایل مستقیم SessionLocal نمی‌سازد ولی باید بررسی شود)
- `backend/app/services/oversight_upload_session.py` از `oversight_service.py` import می‌کند و به‌طور غیرمستقیم با DB در تماس است

تغییرات باید در routes و service‌های مرتبط اعمال شود. تست‌ها نیز باید به‌روزرسانی شوند. کلیدواژه‌های اصلی: `SessionLocal`, `async with`, `context manager`, `HTTPException`, `db.close()`.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ فراخوانی مستقیم `db = SessionLocal()` بدون `with` در فایل‌های services و routes وجود نداشته باشد
- [ ] الگوی `with SessionLocal() as db:` در تمام مکان‌هایی که قبلاً try/finally داشتند وجود داشته باشد
- [ ] متد get_available_models در ai_manager.py بدون session leak اجرا شود — تست با mock SessionLocal که __exit__ را track می‌کند
- [ ] متد get_enabled_status در ai_manager.py حتی در صورت raise شدن exception، session را ببندد
- [ ] هیچ `db.close()` مستقیم در کد services وجود نداشته باشد (چون context manager خودکار می‌بندد)
- [ ] تمام تست‌های موجود در backend/tests/ بعد از تغییرات pass شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **بررسی پیش‌نیاز**: تأیید کن که `SessionLocal` در `backend/app/core/database.py` از `sessionmaker` ساخته شده و آیا از `AsyncSession` یا `Session` sync استفاده می‌کند. اگر sync است، باید از `contextlib.contextmanager` یا `with SessionLocal() as db` استفاده شود (نه `async with` که برای async session است).

2. **اصلاح `backend/app/services/ai_manager.py`**:
   - متد `get_available_models` (خطوط ۹۵-۱۰۱): تبدیل `db = SessionLocal()` + `try/finally` به `with SessionLocal() as db:`
   - متد `get_enabled_status` (خطوط ۳۸۳-۳۹۲): همان تبدیل
   - متد `_log_ai_usage_async` تابع داخلی `_do_log` (خطوط ۶۲۹-۶۵۴): همان تبدیل
   - تابع `load_api_keys_and_reset` (خطوط ۷۷۷-۸۰۰): همان تبدیل

3. **اسکن سایر فایل‌های service**: با grep روی `SessionLocal()` در تمام فایل‌های `backend/app/services/` و `backend/app/api/routes/` جستجو کن و همه موارد را به `with SessionLocal() as db:` تبدیل کن.

4. **اسکن routes**: فایل‌های `backend/app/api/routes/analysis.py`، `backend/app/api/routes/models.py`، `backend/app/api/routes/model_profiles.py` و سایر routes که از `SessionLocal` مستقیم استفاده می‌کنند.

5. **به‌روزرسانی تست‌ها**: فایل‌های `backend/tests/` که session را mock می‌کنند باید با الگوی جدید سازگار شوند.

6. **اگر SessionLocal از نوع async است**: از `async with AsyncSessionLocal() as db:` استفاده کن و توابع sync را به async تبدیل کن یا از `run_in_executor` استفاده کن.

7. **commit با پیام واضح**: `fix(db): replace try/finally SessionLocal with context manager to prevent session leaks`

## 💡 نمونه‌های قبل/بعد
**get_available_models در ai_manager.py (خطوط ۹۵-۱۰۱)**

_قبل:_
```
db = SessionLocal()
        try:
            db_settings = db.query(ModelSettings).all()
            db_settings_map = {s.model_id: s for s in db_settings}
            logger.debug(f"Loaded {len(db_settings_map)} model settings from DB")
        finally:
            db.close()
```

_بعد:_
```
with SessionLocal() as db:
            db_settings = db.query(ModelSettings).all()
            db_settings_map = {s.model_id: s for s in db_settings}
            logger.debug(f"Loaded {len(db_settings_map)} model settings from DB")
```

**get_enabled_status در ai_manager.py (خطوط ۳۸۳-۳۹۲)**

_قبل:_
```
db = SessionLocal()
        try:
            db_setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if db_setting:
                return bool(db_setting.enabled)
            model = get_model(model_id)
            return model.enabled if model else False
        finally:
            db.close()
```

_بعد:_
```
with SessionLocal() as db:
            db_setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if db_setting:
                return bool(db_setting.enabled)
            model = get_model(model_id)
            return model.enabled if model else False
```

**_do_log در _log_ai_usage_async (خطوط ۶۲۹-۶۵۴)**

_قبل:_
```
def _do_log() -> None:
                from ..core.database import SessionLocal
                from ..models.ai_log import AILog
                db = SessionLocal()
                try:
                    AILog.log_request(db, ...)
                except Exception as _de:
                    slog.debug(f"AILog write failed: {_de}")
                finally:
                    db.close()
```

_بعد:_
```
def _do_log() -> None:
                from ..core.database import SessionLocal
                from ..models.ai_log import AILog
                try:
                    with SessionLocal() as db:
                        AILog.log_request(db, ...)
                except Exception as _de:
                    slog.debug(f"AILog write failed: {_de}")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'db = SessionLocal()' backend/app/services/ backend/app/api/routes/`
- `grep -rn 'db.close()' backend/app/services/ backend/app/api/routes/`
- `grep -rn 'with SessionLocal() as db' backend/app/services/ backend/app/api/routes/`
- `pytest backend/tests/ -v --tb=short`
- `pytest backend/tests/test_iterative_orchestrator.py -v`
- `pytest backend/tests/test_runtime_verify_integration.py -v`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **نوع SessionLocal (sync vs async)**: اگر `backend/app/core/database.py` از `AsyncSession` استفاده کند، `with SessionLocal() as db:` کار نمی‌کند و باید `async with` شود — این تغییر cascade effect روی تمام ۲۲ importer دارد و توابع sync باید async شوند یا در `run_in_executor` بمانند.
۲. **_do_log در ai_manager.py**: این تابع sync است و در `loop.run_in_executor` اجرا می‌شود (خط ۶۵۸). اگر SessionLocal async باشد، نمی‌توان `async with` را در تابع sync داخل executor استفاده کرد — نیاز به refactor جداگانه دارد.
۳. **oversight_service.py با ۱۲ importer**: این فایل هاب مرکزی است و تغییر الگوی session در آن روی `oversight_upload_session.py`، `scan_v5/scan_inspector_session.py`، `verify_runtime/context_builder.py`، `notification_service.py` و `oversight_codex_service.py` تأثیر می‌گذارد.
۴. **analysis_progress_manager.py**: این سرویس `db_session` را از بیرون inject می‌گیرد (خط ۲۸) — تغییر الگو در caller‌های آن (مثل `deep_analysis_service.py`) باید هماهنگ باشد.
۵. **load_api_keys_and_reset در ai_manager.py**: این تابع `db.close()` را مستقیم فراخوانی می‌کند (خط ۸۰۰) — باید به context manager تبدیل شود ولی چون async است، نوع SessionLocal اهمیت دارد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 35: رفع exception swallowed در run_analysis_stream با لاگ کافی و ارسال خطا به کاربر

**Scope:** این مرحله شامل پیاده‌سازی مدیریت خطا در تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py است. باید اطمینان حاصل شود که اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار دریافت کند. همچنین اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت (fallback) ارسال شود. خارج از scope: تغییرات در frontend، تغییرات در signature endpointها، یا تغییرات در سایر فایل‌ها.
**Key terms:** backend/app/api/routes/analysis.py, run_analysis_stream, deep_analysis_service, json.dumps, fallback_error_message, DeepAnalysisService

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در signature endpointها ممکن است frontend را بشکند اگر response type تغییر کند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 8
  id: 037dbd0d-9561-4c00-be73-7bc923e2565b
  عنوان اصلی: exception swallowed در run_analysis_stream بدون لاگ کافی
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run", "headers": null, "json_body": {"analysis_type": "deep", "target": "test"}, "expected_status": 200, "required_fields": [], "json_contains": null}]
  - اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت ارسال می [verify_method=static] [verify_plan={"grep_patterns": ["except Exception", "json.dumps", "fallback_error_message"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع exception swallowed در run_analysis_stream با fallback error event

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py` — `run_analysis_stream` — تابع اصلی هدف این تسک. این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. تابع run_analysis_stream یک async generator است که SSE events تولید می‌کند و deep_analysis_service را فراخوانی می‌کند. مشکل: exception از deep_analysis_service بلعیده می‌شود بدون ارسال error event به کاربر.
- `backend/app/services/deep_analysis_service.py` — `DeepAnalysisService` — سرویسی که توسط run_analysis_stream فراخوانی می‌شود و منبع احتمالی exception است. این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. باید interface آن (متدها و exception typeهایی که raise می‌کند) بررسی شود تا except clause دقیق‌تر نوشته شود.
- `backend/app/core/logging_utils.py` — `logger` — ابزار لاگینگ مرکزی پروژه. باید بررسی شود که logger چگونه در routes استفاده می‌شود تا در run_analysis_stream از همان pattern استفاده شود. این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. SSE (Server-Sent Events) با async generator در FastAPI. کتابخانه‌های مرتبط: `json` (stdlib)، `logging` (stdlib)، `fastapi.responses.StreamingResponse`. Pattern مورد استفاده: `yield f"data: {payload}\n\n"` برای SSE events. Python version: 3.10+. pytest + pytest-asyncio برای تست‌ها.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/deep_analysis_service.py` — منبع مستقیم exception — run_analysis_stream این سرویس را call می‌کند. باید exception typeها و رفتار آن بررسی شود تا except clause مناسب نوشته شود.
- `backend/app/core/logging_utils.py` — ابزار لاگینگ مشترک پروژه — برای اضافه کردن logger.exception() در بلوک except باید از همین utility استفاده شود تا با بقیهٔ پروژه consistent باشد.
- `backend/app/services/analysis_progress_manager.py` — احتمالاً state مربوط به progress analysis را مدیریت می‌کند. اگر exception در run_analysis_stream رخ دهد، باید بررسی شود که آیا این manager نیاز به cleanup دارد یا نه (در غیر این صورت state leak می‌شود).
- `backend/tests/test_runtime_verify_integration.py` — نزدیک‌ترین تست integration موجود در پروژه — می‌توان pattern تست‌نویسی برای SSE stream و error handling را از اینجا الگو گرفت.
- `backend/app/api/routes/runtime.py` — route مشابه که احتمالاً SSE streaming دارد — می‌توان pattern مدیریت خطای آن را به عنوان reference برای analysis.py استفاده کرد.

## 🌐 نقشهٔ وابستگی‌ها
تابع `run_analysis_stream` در `backend/app/api/routes/analysis.py` یک SSE endpoint است که توسط frontend (Next.js) از طریق EventSource یا fetch با streaming مصرف می‌شود. این تابع `DeepAnalysisService` از `backend/app/services/deep_analysis_service.py` را فراخوانی می‌کند. همچنین احتمالاً از `backend/app/services/analysis_progress_manager.py` برای track کردن وضعیت استفاده می‌کند. لاگینگ باید از `backend/app/core/logging_utils.py` تأمین شود. تغییرات فقط داخل generator body هستند و signature endpoint (`/api/analysis/run`) تغییر نمی‌کند — بنابراین frontend تحت تأثیر قرار نمی‌گیرد. `backend/app/main.py` این router را mount می‌کند.

## 🔍 Context و وضعیت فعلی
این تسک مربوط به رفع باگ بنیادی «exception swallowed» در تابع `run_analysis_stream` در فایل `backend/app/api/routes/analysis.py` است. مشکل اصلی این است که اگر `deep_analysis_service` در حین پردازش خطا بدهد، این خطا بدون لاگ کافی بلعیده می‌شود و کاربر هیچ رویداد error معنی‌داری دریافت نمی‌کند — SSE stream بدون پیام خطا قطع می‌شود یا silent fail رخ می‌دهد.

بر اساس acceptance_criteria تسک اصلی (id: 037dbd0d-9561-4c00-be73-7bc923e2565b)، دو شرط باید برقرار باشد:
1. اگر `deep_analysis_service` خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند [verify_method=api_response] — endpoint: POST /api/analysis/run با body {"analysis_type": "deep", "target": "test"}
2. اگر `json.dumps` روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت (fallback_error_message) ارسال می‌شود [verify_method=static] — grep_patterns: ["except Exception", "json.dumps", "fallback_error_message"] در فایل `backend/app/api/routes/analysis.py`

کلیدواژه‌های فنی مرتبط: `run_analysis_stream`, `deep_analysis_service`, `DeepAnalysisService`, `json.dumps`, `fallback_error_message`, `backend/app/api/routes/analysis.py`.

خارج از scope این تسک: تغییرات در frontend، تغییرات در signature endpointها، یا تغییرات در سایر فایل‌ها. تنها فایل هدف `backend/app/api/routes/analysis.py` است.

ریسک اصلی: تغییر در response type یا signature endpoint ممکن است frontend را بشکند — بنابراین فقط داخل generator function تغییر اعمال می‌شود و SSE event format ثابت می‌ماند.

این تسک آخرین (تسک 8 از 8) در یک سری اصلاحات بوده و وضعیت verify قبلی آن `partial` بوده است، یعنی بخشی از مدیریت خطا وجود داشته ولی ناقص بوده.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند — SSE stream باید حاوی event با فیلد type=error و message غیرخالی باشد
- [ ] اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت (fallback_error_message) ارسال می‌شود — کد باید شامل literal string fallback_error_message باشد
- [ ] خطا با logger.exception یا logger.error با traceback کامل در لاگ‌های سرور ثبت می‌شود — نه silent fail
- [ ] signature endpoint /api/analysis/run تغییر نکرده و response type (StreamingResponse با media_type text/event-stream) ثابت مانده است
- [ ] تست backend برای سناریوی exception در deep_analysis_service وجود دارد و pass می‌شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. فایل `backend/app/api/routes/analysis.py` را باز کن و تابع `run_analysis_stream` (generator یا async generator که SSE events تولید می‌کند) را پیدا کن.
2. داخل بدنهٔ اصلی generator، یک `try/except Exception as e` بیرونی اضافه کن که کل فراخوانی `deep_analysis_service` را در بر بگیرد.
3. در بلوک `except`، ابتدا با `logger.exception(...)` یا `logger.error(...)` خطا را با traceback کامل لاگ کن.
4. سپس سعی کن یک SSE event از نوع `error` با پیام معنی‌دار بسازی:
   ```python
   try:
       error_payload = json.dumps({"type": "error", "message": str(e)})
       yield f"data: {error_payload}\n\n"
   except Exception:
       fallback_error_message = '{"type": "error", "message": "An unexpected error occurred"}'
       yield f"data: {fallback_error_message}\n\n"
   ```
5. اطمینان حاصل کن که `fallback_error_message` به‌صورت literal string (نه متغیر پویا) تعریف شده تا grep_pattern `fallback_error_message` در static verify پیدا شود.
6. مطمئن شو `import json` و `import logging` (یا `logger`) در بالای فایل موجود است.
7. signature endpoint و response type را تغییر نده — فقط داخل generator body کار کن.
8. یک تست در `backend/tests/` بنویس (یا موجود را آپدیت کن) که `deep_analysis_service` را mock کرده و exception می‌اندازد، سپس بررسی می‌کند که SSE stream حاوی event با `type: error` است.

## 💡 نمونه‌های قبل/بعد
**مدیریت خطا در run_analysis_stream — قبل و بعد**

_قبل:_
```
async def run_analysis_stream(...):
    async for chunk in deep_analysis_service.run(...):
        yield f"data: {json.dumps(chunk)}\n\n"
    # exception از deep_analysis_service بلعیده می‌شود
    # کاربر هیچ error event دریافت نمی‌کند
```

_بعد:_
```
async def run_analysis_stream(...):
    try:
        async for chunk in deep_analysis_service.run(...):
            yield f"data: {json.dumps(chunk)}\n\n"
    except Exception as e:
        logger.exception("run_analysis_stream failed: %s", str(e))
        try:
            error_payload = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_payload}\n\n"
        except Exception:
            fallback_error_message = '{"type": "error", "message": "An unexpected error occurred"}'
            yield f"data: {fallback_error_message}\n\n"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/ -k 'analysis' -v`
- `grep -n 'fallback_error_message\|except Exception\|json.dumps\|logger.exception' backend/app/api/routes/analysis.py`
- `pytest backend/tests/ --tb=short -v`

## ⚠️ ریسک‌ها و موارد احتیاط
1. اگر `run_analysis_stream` از چندین جا در `backend/app/api/routes/analysis.py` فراخوانی شود یا چندین generator داخلی داشته باشد، باید مطمئن شد که try/except در سطح درست قرار گرفته — نه فقط یک iteration.
2. اگر `analysis_progress_manager.py` state مربوط به این stream را نگه می‌دارد، exception بدون cleanup می‌تواند باعث state leak شود — باید بررسی شود آیا در finally block نیاز به cleanup هست.
3. اگر `deep_analysis_service` خودش exception را catch کرده و re-raise می‌کند با type خاص، except clause باید آن را هم cover کند.
4. تغییر format SSE event (اضافه کردن فیلد type) ممکن است frontend را تحت تأثیر قرار دهد اگر frontend انتظار format خاصی داشته باشد — اما چون این تسک خارج از scope frontend است، باید با تیم frontend هماهنگ شود که آیا event با type=error قبلاً handle می‌شود یا نه.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 36: رفع بلعیده شدن استثناها در run_analysis_stream با لاگ‌گیری و مدیریت خطای جامع‌تر

**Scope:** این مرحله شامل اصلاح دو بخش از فایل backend/app/api/routes/analysis.py است: (1) خطوط 251-253 در تابع generate_events که در آن خطای json.dumps درون except بلعیده می‌شود، و (2) خطوط 200-206 در تابع run_analysis_task که در آن خطای progress_queue.put بلعیده می‌شود. هدف این است که اطمینان حاصل شود هیچ استثنایی بدون لاگ یا بازخورد به کاربر باقی نمی‌ماند. خارج از scope این مرحله: اصلاح خطاهای run_full_analysis در deep_analysis_service.py، تغییرات در frontend، یا اضافه کردن heartbeat.
**Key terms:** backend/app/api/routes/analysis.py, generate_events, run_analysis_task, run_analysis_stream, json.dumps, progress_queue.put, SSE stream, asyncio.Queue

**بخش مربوط از متن کاربر:**
```
exception swallowed در run_analysis_stream بدون لاگ کافی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:251-253` — `generate_events` — اگر json.dumps روی str(e) خطا بدهد، این except هم بلعیده می‌شود
  ```python
  except Exception as e:
              logger.error(f"Error in SSE stream: {e}")
              yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
  ```
- `backend/app/api/routes/analysis.py:200-206` — `run_analysis_task` — اگر progress_queue.put خطا بدهد (صف بسته)، خطا بلعیده می‌شود
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                  await progress_queue.put({
                      "event": "error",
                      "message": str(e),
                      "error": True
                  })
  ```
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع بلعیده شدن استثناها در run_analysis_stream با لاگ‌گیری و مدیریت خطای جامع‌تر

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:251-253` — `generate_events` — این بلوک except در تابع generate_events است. اگر json.dumps روی str(e) خطا بدهد (مثلاً به دلیل کاراکتر غیر UTF-8)، خود این خطا هم بلعیده می‌شود و کاربر هیچ خطایی دریافت نمی‌کند. باید یک try/except مجزا برای json.dumps اضافه شود.
  ```python
  except Exception as e:
              logger.error(f"Error in SSE stream: {e}")
              yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
  ```
- `backend/app/api/routes/analysis.py:200-206` — `run_analysis_task` — این بلوک except در تابع run_analysis_task است. اگر progress_queue.put خطا بدهد (مثلاً به دلیل بسته شدن صف asyncio.Queue)، خطا بلعیده می‌شود. باید یک try/except مجزا برای progress_queue.put اضافه شود تا در صورت شکست، خطا از طریق logger.error مستقیم ثبت شود.
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                  await progress_queue.put({
                      "event": "error",
                      "message": str(e),
                      "error": True
                  })
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/deep_analysis_service.py` — این سرویس توسط run_analysis_task فراخوانی می‌شود (خط 191 analysis.py). اگر run_full_analysis خطا بدهد،

## 🔍 Context و وضعیت فعلی
این تسک به رفع دو نقطه از فایل backend/app/api/routes/analysis.py می‌پردازد که در آن استثناها بدون لاگ کافی یا بازخورد به کاربر بلعیده می‌شوند. (1) در خطوط 251-253 تابع generate_events، اگر json.dumps روی str(e) خطا بدهد (مثلاً به دلیل کاراکتر غیرقابل سریال‌سازی)، این except هم بلعیده می‌شود و کاربر هیچ خطایی دریافت نمی‌کند. (2) در خطوط 200-206 تابع run_analysis_task، اگر progress_queue.put خطا بدهد (مثلاً به دلیل بسته شدن صف asyncio.Queue)، خطا بلعیده می‌شود و تحلیل بدون اطلاع کاربر متوقف می‌شود. هدف این است که اطمینان حاصل شود هیچ استثنایی بدون لاگ یا بازخورد به کاربر باقی نمی‌ماند. خارج از scope این مرحله: اصلاح خطاهای run_full_analysis در deep_analysis_service.py، تغییرات در frontend، یا اضافه کردن heartbeat. کلیدواژه‌های دقیق از متن کاربر: backend/app/api/routes/analysis.py, generate_events, run_analysis_task, run_analysis_stream, json.dumps, progress_queue.put, SSE stream, asyncio.Queue.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در تابع generate_events (backend/app/api/routes/analysis.py:251-253): بلوک except را به دو بخش تقسیم کن: ابتدا یک try/except مجزا برای json.dumps که در صورت خطا یک پیام خطای fallback تولید کند، سپس yield خطا با آن fallback. لاگ خطا با exc_info=True ثبت شود. 2. در تابع run_analysis_task (backend/app/api/routes/analysis.py:200-206): قبل از progress_queue.put، یک try/except مجزا اضافه کن که اگر صف بسته بود، خطا را لاگ کند و از یک مسیر جایگزین (مثلاً logger.error مستقیم) برای ثبت خطا استفاده کند. 3. در هر دو نقطه، اطمینان حاصل شود که خطا به صورت structured در خروجی SSE (با event: error) به کاربر اعلام می‌شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 37: پیاده‌سازی مدیریت خطاهای مقاوم در deep_analysis_service و generate_events

**Scope:** این مرحله شامل سه تغییر مجزا در مدیریت خطا است: (1) افزودن try/except تو در تو در خط 251 برای ارسال رویداد خطا در صورت شکست json.dumps، (2) افزودن try/except در خطوط 200-206 برای مدیریت خطای صف progress_queue، (3) افزودن finally در سطح تابع generate_events برای ارسال رویداد fatal در صورت خطای غیرمنتظره. خارج از scope: تغییر منطق اصلی، افزودن قابلیت جدید، یا تغییر تست‌ها.
**Key terms:** deep_analysis_service, generate_events, progress_queue.put, logger.critical, json.dumps, except Exception as e, backend/app/services/deep_analysis_service.py

**بخش مربوط از متن کاربر:**
```
1. ۱. در `except Exception as e` خط ۲۵۱، یک try/except تو در تو برای ارسال رویداد خطا اضافه کن. ۲. در خط ۲۰۰-۲۰۶، بعد از `progress_queue.put` یک `try/except` بگذار که اگر صف خطا داد، حداقل با `logger.critical` لاگ شود. ۳. یک `finally` در سطح `generate_events` اضافه کن که اگر خطای غیرمنتظره‌ای رخ داد، یک رویداد `fatal` با پیام ثابت به صف اضافه کند.
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن مدیریت خطای مقاوم در generate_events و progress_queue

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/deep_analysis_service.py:56-86` — `AnalysisProgressTracker.emit` — این متد callback پیشرفت را فراخوانی می‌کند. خط ۸۰-۸۶ بلوک try/except موجود است که فقط warning لاگ می‌کند. تغییر اول کاربر (try/except تو در تو برای ارسال رویداد خطا) باید اینجا اعمال شود. توجه: این متد داخل `async with self._lock` است — try/except داخلی نباید lock را آزاد کند.
  ```python
  async def emit(self, event_type: str, data: Dict = None):
          """ارسال رویداد پیشرفت"""
          if not self.callback:
              return
  
          async with self._lock:
              progress_data = {
                  "event": event_type,
                  "analysis_id": self.analysis_id,
                  ...
              }
  
              try:
                  if asyncio.iscoroutinefunction(self.callback):
                      await self.callback(progress_data)
                  else:
                      self.callback(progress_data)
              except Exception as e:
                  logger.warning(f"Error in progress callback: {e}")
  ```
- `backend/app/services/deep_analysis_service.py:314-574` — `DeepAnalysisService.run_full_analysis` — تابع اصلی تحلیل. تغییر سوم کاربر (finally در سطح generate_events) مستقیماً به این تابع یا تابع generate_events مرتبط است. بخش truncate شده فایل (بعد از خط ۸۰۰) شامل generate_events است — مجری باید فایل کامل را بررسی کند.
  ```python
  async def run_full_analysis(
          self,
          project_id: str,
          files: List[Dict],
          roadmap_content: str = "",
          readme_content: str = "",
          model_ids: List[str] = None,
          instruction: str = "",
          db_session=None,
          progress_manager=None,
          depth: str = "standard",
          analysis_settings: Dict[str, Any] = None
      ) -> Dict[str, Any]:
  ```
- `backend/app/services/deep_analysis_service.py:800-2294` — `generate_events` — تابع generate_events در بخش truncate شده فایل (بعد از خط ۸۰۰ از ۲۲۹۴ خط کل) قرار دارد. deep context این بخش را نشان نمی‌دهد. مجری باید فایل را کامل باز کند، محل دقیق generate_events، progress_queue.put (خطوط ۲۰۰-۲۰۶ طبق کاربر)، و except Exception as e خط ۲۵۱ را پیدا کند. snippet خالی گذاشته شده چون کد در deep blob موجود نیست.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python async) + Next.js 14. سرویس از `asyncio` برای موازی‌سازی، `asyncio.Lock` برای thread-safety در `AnalysisProgressTracker.emit`، و احتمالاً `asyncio.Queue` یا `queue.Queue` برای `progress_queue` استفاده می‌کند. SSE (Server-Sent Events) برای streaming پیشرفت به کلاینت. کتابخانه‌های مرتبط: `fastapi` (SSE via `StreamingResponse` یا `EventSourceResponse`)، `asyncio` (gather, Lock, sleep)، `logging` (logger.warning, logger.critical). Python >= 3.9 بر اساس syntax موجود.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 1) — این route فایل deep_analysis_service را import می‌کند و run_full_analysis را فراخوانی می‌کند. تغییر در مدیریت خطا ممکن است رفتار SSE streaming این route را تحت تأثیر قرار دهد.
- `backend/app/api/routes/project_health.py` (سطر 1) — از ai_manager و deep_analysis_service استفاده می‌کند. اگر generate_events در این route هم استفاده شود، تغییرات finally و progress_queue.put روی آن اثر می‌گذارد.
- `backend/app/services/analysis_progress_manager.py` (سطر 1) — مدیر پیشرفت تحلیل که با progress_queue و وضعیت pause/resume/stop کار می‌کند. تغییر try/except دور progress_queue.put مستقیماً با این سرویس تعامل دارد.
- `backend/tests/test_runtime_verify_integration.py` (سطر 1) — تست‌های integration که رفتار سرویس‌های backend را verify می‌کنند. بعد از تغییرات باید اجرا شوند تا regression رخ ندهد.
- `backend/tests/test_iterative_orchestrator.py` (سطر 1) — تست‌های orchestrator که جریان کامل تحلیل را شامل می‌شوند. تغییر در generate_events و progress_queue ممکن است این تست‌ها را تحت تأثیر قرار دهد.

## 🌐 نقشهٔ وابستگی‌ها
فایل `backend/app/services/deep_analysis_service.py` یکی از هاب‌های اصلی پروژه است. طبق نقشه import‌های داخلی، `backend/app/models/project.py` (12 فایل importer) و `backend/app/services/ai_base.py` (11 فایل importer) توسط این سرویس استفاده می‌شوند. `backend/app/api/routes/analysis.py` این سرویس را مستقیم import می‌کند و endpoint‌های تحلیل را expose می‌کند. `backend/app/api/routes/project_health.py` نیز از این سرویس استفاده می‌کند. تغییرات در `generate_events` و `progress_queue.put` روی جریان SSE streaming تأثیر مستقیم دارند — اگر `finally` به اشتباه پیاده شود، ممکن است رویداد `fatal` در پایان هر stream موفق هم ارسال شود که کلاینت را گمراه می‌کند. `backend/app/services/analysis_progress_manager.py` که وضعیت pause/resume/stop را مدیریت می‌کند، با همان `progress_queue` کار می‌کند و باید با تغییرات هماهنگ باشد.

## 🔍 Context و وضعیت فعلی
درخواست کاربر شامل سه تغییر مجزا در مدیریت خطا در فایل `backend/app/services/deep_analysis_service.py` است که هدف آن‌ها افزایش مقاومت سرویس در برابر خطاهای غیرمنتظره در جریان تحلیل عمیق پروژه است.

**تغییر اول (خط ۲۵۱):** در بلوک `except Exception as e` که مربوط به شکست `json.dumps` است، یک try/except تو در تو اضافه شود تا در صورت شکست ارسال رویداد خطا (مثلاً اگر خود رویداد خطا هم serialize نشود)، سیستم crash نکند و حداقل یک لاگ ثبت شود.

**تغییر دوم (خطوط ۲۰۰-۲۰۶):** بعد از فراخوانی `progress_queue.put`، یک `try/except` اضافه شود که اگر صف (queue) به هر دلیلی خطا داد (مثلاً پر بودن صف، بسته بودن صف، یا خطای threading)، حداقل با `logger.critical` لاگ شود تا سکوت خطرناک رخ ندهد.

**تغییر سوم (سطح تابع generate_events):** یک بلوک `finally` در سطح تابع `generate_events` اضافه شود که اگر هر خطای غیرمنتظره‌ای در کل جریان رخ داد، یک رویداد `fatal` با پیام ثابت به صف اضافه کند تا consumer سمت کلاینت بداند که stream به پایان رسیده یا دچار خطای بحرانی شده است.

**خارج از scope:** تغییر منطق اصلی تحلیل، افزودن قابلیت جدید، یا تغییر تست‌ها.

کلیدواژه‌های اصلی: `deep_analysis_service`, `generate_events`, `progress_queue.put`, `logger.critical`, `json.dumps`, `except Exception as e`, `backend/app/services/deep_analysis_service.py`.

در کد فعلی فایل `deep_analysis_service.py` (که تا خط ۸۰۰ در deep context موجود است)، کلاس `AnalysisProgressTracker` در خطوط ۳۲-۱۸۱ تعریف شده و متد `emit` در خطوط ۵۶-۸۶ مدیریت callback را انجام می‌دهد. بلوک `try/except` در متد `emit` (خطوط ۸۰-۸۶) وجود دارد اما تنها یک `logger.warning` ثبت می‌کند و هیچ fallback رویدادی ارسال نمی‌شود. تابع `generate_events` و `progress_queue` در بخش truncate شده فایل (بعد از خط ۸۰۰) قرار دارند، اما بر اساس کلیدواژه‌های کاربر و ساختار سرویس، این تابع بخشی از مکانیزم SSE/streaming است که رویدادهای پیشرفت را به کلاینت ارسال می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] در متد `AnalysisProgressTracker.emit` (خطوط ۸۰-۸۶ فایل deep_analysis_service.py)، بلوک `except Exception as e` باید شامل یک try/except داخلی باشد که تلاش می‌کند رویداد خطا را به callback ارسال کند و در صورت شکست، `logger.critical` فراخوانی شود.
- [ ] در تابع `generate_events` (بخش truncate شده deep_analysis_service.py)، فراخوانی `progress_queue.put` باید داخل یک بلوک try/except باشد که در صورت خطا، `logger.critical` با پیام شامل نام event فراخوانی شود.
- [ ] تابع `generate_events` باید دارای بلوک `finally` در سطح تابع باشد که رویداد `fatal` با پیام ثابت به `progress_queue` اضافه کند.
- [ ] تست‌های موجود در `backend/tests/test_runtime_verify_integration.py` و `backend/tests/test_iterative_orchestrator.py` باید بدون regression pass شوند.
- [ ] منطق اصلی تحلیل (run_full_analysis، _run_micro_analysis، _analyze_single_file_with_models) نباید تغییر کند — فقط مدیریت خطا اضافه شده باشد.
- [ ] رویداد `fatal` در `finally` نباید در جریان موفق (بدون exception) باعث ارسال رویداد اضافی به کلاینت شود — `finally` فقط در صورت خطا یا پایان غیرعادی باید رویداد ارسال کند.
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. **مراحل پیاده‌سازی:**

1. **شناسایی دقیق محل `generate_events` در `backend/app/services/deep_analysis_service.py`:** این تابع در بخش truncate شده (بعد از خط ۸۰۰) قرار دارد. مجری باید فایل را کامل باز کند و خطوط دقیق را پیدا کند.

2. **تغییر اول — try/except تو در تو در `except Exception as e` مربوط به `json.dumps` (خط ۲۵۱ طبق کاربر):**
```python
# قبل:
except Exception as e:
    logger.warning(f"Error in progress callback: {e}")

# بعد:
except Exception as e:
    logger.warning(f"Error in progress callback: {e}")
    try:
        # ارسال رویداد خطا به callback
        error_event = {"event": "error", "message": str(e)}
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback(error_event)
        else:
            self.callback(error_event)
    except Exception as inner_e:
        logger.critical(f"Failed to send error event to callback: {inner_e}")
```

3. **تغییر دوم — try/except دور `progress_queue.put` (خطوط ۲۰۰-۲۰۶):**
```python
# قبل:
progress_queue.put(progress_data)

# بعد:
try:
    progress_queue.put(progress_data)
except Exception as queue_err:
    logger.critical(f"Failed to put event into progress_queue: {queue_err}")
```

4. **تغییر سوم — افزودن `finally` در سطح `generate_events`:**
```python
async def generate_events(...):
    try:
        # ... منطق اصلی موجود ...
    except Exception as e:
        logger.error(f"Unexpected error in generate_events: {e}")
        raise
    finally:
        try:
            fatal_event = {"event": "fatal", "message": "stream ended unexpectedly"}
            progress_queue.put(fatal_event)
        except Exception as final_err:
            logger.critical(f"Failed to send fatal event: {final_err}")
```

5. **بررسی تأثیر روی `AnalysisProgressTracker.emit` (خطوط ۵۶-۸۶):** مطمئن شو که try/except تو در تو با lock موجود (`self._lock`) تداخل ندارد.

6. **اجرای تست‌های موجود:** `pytest backend/tests/test_runtime_verify_integration.py` و `pytest backend/tests/test_iterative_orchestrator.py` برای اطمینان از عدم regression.

## 💡 نمونه‌های قبل/بعد
**تغییر اول: try/except تو در تو در emit برای ارسال رویداد خطا**

_قبل:_
```
try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(progress_data)
                else:
                    self.callback(progress_data)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")
```

_بعد:_
```
try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(progress_data)
                else:
                    self.callback(progress_data)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")
                try:
                    error_payload = {"event": "error", "message": str(e), "analysis_id": self.analysis_id}
                    if asyncio.iscoroutinefunction(self.callback):
                        await self.callback(error_payload)
                    else:
                        self.callback(error_payload)
                except Exception as inner_e:
                    logger.critical(f"Failed to send error event to callback: {inner_e}")
```

**تغییر دوم: try/except دور progress_queue.put**

_قبل:_
```
progress_queue.put(progress_data)
```

_بعد:_
```
try:
                    progress_queue.put(progress_data)
                except Exception as queue_err:
                    logger.critical(
                        f"Failed to put event into progress_queue "
                        f"(event={progress_data.get('event', 'unknown')}): {queue_err}"
                    )
```

**تغییر سوم: finally در سطح generate_events برای ارسال رویداد fatal**

_قبل:_
```
async def generate_events(...):
    # ... منطق اصلی ...
    # بدون finally
```

_بعد:_
```
async def generate_events(...):
    try:
        # ... منطق اصلی بدون تغییر ...
        pass
    except Exception as e:
        logger.error(f"Unexpected error in generate_events: {e}", exc_info=True)
        raise
    finally:
        try:
            fatal_event = {"event": "fatal", "message": "stream ended unexpectedly", "timestamp": datetime.now().isoformat()}
            progress_queue.put_nowait(fatal_event)
        except Exception as final_err:
            logger.critical(f"Failed to send fatal event in generate_events finally: {final_err}")
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest backend/tests/test_runtime_verify_integration.py -v`
- `pytest backend/tests/test_iterative_orchestrator.py -v`
- `pytest backend/tests/test_runtime_verify_stage1.py -v`
- `grep -n 'logger.critical' backend/app/services/deep_analysis_service.py`
- `grep -n 'finally' backend/app/services/deep_analysis_service.py`
- `grep -n 'fatal' backend/app/services/deep_analysis_service.py`
- `python -c "import ast; ast.parse(open('backend/app/services/deep_analysis_service.py').read()); print('Syntax OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **خطر double-send در emit:** چون try/except داخلی داخل `async with self._lock` است، اگر callback خودش هم lock بگیرد، deadlock رخ می‌دهد. باید مطمئن شد callback هیچ‌گاه همان lock را نمی‌گیرد. فایل مرتبط: `AnalysisProgressTracker.emit` خطوط ۵۶-۸۶.
۲. **خطر finally همیشه‌فعال:** اگر `finally` در `generate_events` بدون شرط پیاده شود، رویداد `fatal` در پایان هر stream موفق هم ارسال می‌شود. کلاینت Next.js که این SSE را consume می‌کند ممکن است رویداد `fatal` را به عنوان خطا تفسیر کند. باید از `put_nowait` با شرط یا flag استفاده شود.
۳. **خطر queue پر:** اگر `progress_queue` از نوع `queue.Queue(maxsize=N)` باشد، `put_nowait` در finally ممکن است `queue.Full` بدهد — باید از `put_nowait` با try/except استفاده شود نه `put` blocking.
۴. **تأثیر روی `analysis_progress_manager.py`:** این سرویس با همان queue کار می‌کند. تغییر رفتار queue ممکن است وضعیت pause/resume/stop را مختل کند.
۵. **فایل ۲۲۹۴ خطی truncate شده:** بخش اصلی تغییرات (generate_events، progress_queue) در بخش truncate شده (بعد از خط ۸۰۰) است — مجری باید فایل کامل را بخواند و خطوط دقیق را verify کند قبل از اعمال تغییر.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 38: ایمن‌سازی ارسال رویداد خطا در استریم رویداد

**Scope:** این مرحله شامل تغییر کد در فایل‌های مرتبط با استریم رویداد خطا (احتمالاً در backend/app/api/routes/chat.py یا backend/app/services/deep_analysis_service.py) است. تغییرات شامل محدود کردن طول پیام خطا به 500 کاراکتر و افزودن try/except برای جلوگیری از شکست استریم است. خارج از scope: تغییرات در سایر بخش‌های کد، تست‌ها، یا مستندات.
**Key terms:** backend/app/api/routes/chat.py, backend/app/services/deep_analysis_service.py, event: error, json.dumps, str(e)[:500], internal stream error

**بخش مربوط از متن کاربر:**
```
## 💡 نمونه‌های قبل/بعد
**ایمن‌سازی ارسال رویداد خطا**

_قبل:_
```
yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

_بعد:_
```
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

_بعد:_
```
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

--- کلیدواژه‌ها ---
backend/app/api/routes/chat.py, backend/app/services/deep_analysis_service.py, event: error, json.dumps, str(e)[:500], internal stream error
```

## 🎯 هدف (خلاصه ساختاریافته)
ایمن‌سازی ارسال رویداد خطا در SSE stream با محدودیت طول و try/except

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/chat.py` — `streaming_generator_function` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. کاربر صراحتاً این فایل را به‌عنوان محل اصلی `yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"` ذکر کرده. باید تمام generator functionهایی که SSE stream تولید می‌کنند را بررسی کرد.
- `backend/app/services/deep_analysis_service.py:568-573` — `run_full_analysis` — این بلوک except در `run_full_analysis` است. `results['error'] = str(e)` بدون محدودیت طول set می‌شود. اگر caller این نتیجه را در یک SSE stream به client ارسال کند، پیام خطا می‌تواند بسیار طولانی باشد. باید `str(e)[:500]` اعمال شود. همچنین اگر caller مستقیماً `yield` می‌کند، باید try/except اضافه شود.
  ```python
  except Exception as e:
              elapsed_total = time.time() - start_time_unix
              logger.error(f"❌ [{analysis_id}] ANALYSIS FAILED after {elapsed_total:.2f}s: {str(e)}", exc_info=True)
              results["status"] = "failed"
              results["error"] = str(e)
  
          return results
  ```
- `backend/app/api/routes/analysis.py` — `streaming_analysis_endpoint` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این route از `deep_analysis_service.py` استفاده می‌کند (طبق نقشه import‌ها) و احتمالاً SSE streaming endpoint دارد که نتایج تحلیل را stream می‌کند. باید بررسی شود آیا `event: error` در اینجا هم yield می‌شود.

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: FastAPI (Python) + Next.js. SSE (Server-Sent Events) با `yield` در FastAPI generator functions. کتابخانه‌های مرتبط: `json` (stdlib)، `asyncio` (stdlib). Pattern فعلی: `yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"` که هیچ محدودیت طولی یا error handling ندارد. راه‌حل: `str(e)[:500]` برای محدودیت طول + try/except برای fallback.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 1) — این route از `deep_analysis_service.py` import می‌کند (طبق نقشه import‌های داخلی) و احتمالاً streaming endpoint دارد که خطاهای تحلیل را به client ارسال می‌کند — باید بررسی شود آیا pattern ناامن `yield event: error` در اینجا هم وجود دارد
- `backend/app/api/routes/project_health.py` (سطر 1) — این route هم از `deep_analysis_service.py` و `ai_manager.py` استفاده می‌کند (طبق نقشه import‌ها) و ممکن است streaming health analysis داشته باشد که همان pattern خطا را داشته باشد
- `backend/app/services/log_stream_service.py` (سطر 148) — این سرویس streaming لاگ‌ها را مدیریت می‌کند و در `_broadcast_logs` و `_polling_loop` بلوک‌های except دارد (خطوط ۱۴۸-۱۴۹، ۲۶۷-۲۶۹) که خطاها را log می‌کنند — باید بررسی شود آیا خطاها به client هم stream می‌شوند
- `backend/app/api/routes/orchestrator.py` (سطر 1) — این route از `ai_manager.py` و `ai_base.py` استفاده می‌کند و احتمالاً streaming orchestration دارد — باید بررسی شود آیا pattern ناامن `event: error` در اینجا هم وجود دارد
- `backend/app/api/routes/oversight.py` (سطر 1) — این route از `oversight_service.py` استفاده می‌کند که یکی از سرویس‌های اصلی است — اگر oversight هم streaming دارد، باید همان ایمن‌سازی اعمال شود

## 🌐 نقشهٔ وابستگی‌ها
تغییرات در `backend/app/api/routes/chat.py` مستقیماً روی SSE streaming endpoint تأثیر می‌گذارد که frontend آن را consume می‌کند. تغییر در `backend/app/services/deep_analysis_service.py` (خطوط ۵۶۸-۵۷۳، تابع `run_full_analysis`) روی تمام callerهای این سرویس اثر دارد: `backend/app/api/routes/analysis.py` و `backend/app/api/routes/project_health.py` که هر دو این سرویس را import می‌کنند. همچنین `backend/app/services/deep_analysis_service.py` از `backend/app/models/project.py` (که ۱۱ فایل آن را import می‌کنند) و `backend/app/services/ai_base.py` (که ۹ فایل آن را import می‌کنند) استفاده می‌کند. تغییر در error handling نباید روی logic اصلی تأثیر بگذارد چون فقط در بلوک‌های except اعمال می‌شود.

## 🔍 Context و وضعیت فعلی
کاربر درخواست کرده است که در فایل‌های مرتبط با استریم رویداد خطا — به‌خصوص `backend/app/api/routes/chat.py` و `backend/app/services/deep_analysis_service.py` — کد ارسال رویداد `event: error` ایمن‌سازی شود. مشکل اصلی این است که در حال حاضر خطاهای Python به‌صورت خام با `str(e)` در payload JSON قرار می‌گیرند و yield می‌شوند، بدون هیچ محدودیت طولی یا حفاظتی. این می‌تواند باعث شود: ۱) پیام خطای بسیار طولانی (مثلاً stack trace کامل) در stream ارسال شود و client را دچار مشکل کند، ۲) اگر خود عملیات json.dumps یا yield با خطا مواجه شود، کل stream بشکند و client هیچ پاسخی دریافت نکند. راه‌حل پیشنهادی کاربر دقیقاً این است: الف) طول پیام خطا را با `str(e)[:500]` به ۵۰۰ کاراکتر محدود کن، ب) کل بلوک yield را در try/except بپیچ تا اگر حتی ارسال رویداد خطا هم fail شد، یک fallback ثابت `event: error
data: {"error": "internal stream error"}

` ارسال شود. کلیدواژه‌های مستقیم کاربر: `backend/app/api/routes/chat.py`، `backend/app/services/deep_analysis_service.py`، `event: error`، `json.dumps`، `str(e)[:500]`، `internal stream error`. در `deep_analysis_service.py` که deep-read شده، در خطوط ۵۶۸-۵۷۳ بلوک except اصلی وجود دارد که `results['error'] = str(e)` را set می‌کند — این نقطه‌ای است که اگر streaming generator باشد، باید ایمن‌سازی شود. فایل `chat.py` در ساختار پروژه موجود است (`backend/app/api/routes/chat.py`) و احتمالاً generator-based SSE endpoint دارد که `yield f"event: error\ndata: ..."` را مستقیم اجرا می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] در `backend/app/api/routes/chat.py` هیچ `yield` ای با `event: error` بدون try/except وجود نداشته باشد
- [ ] در `backend/app/services/deep_analysis_service.py` خط ۵۷۲، `results['error']` باید با `str(e)[:500]` محدود شده باشد
- [ ] اگر json.dumps یا yield خودش با خطا مواجه شود، fallback ثابت `event: error\ndata: {"error": "internal stream error"}\n\n` ارسال شود
- [ ] هیچ streaming endpoint دیگری در `backend/app/api/routes/` از pattern ناامن `yield.*event: error.*str(e)` بدون محدودیت طول استفاده نکند
- [ ] تست واحد: شبیه‌سازی خطای بزرگ (مثلاً `Exception('x' * 1000)`) در streaming endpoint و تأیید اینکه payload ارسال‌شده حداکثر ۵۰۰ کاراکتر در فیلد error دارد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. **فایل `backend/app/api/routes/chat.py`**: تمام مکان‌هایی که `yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"` یا مشابه آن وجود دارد را شناسایی کن. هر کدام را با الگوی زیر جایگزین کن:
```python
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
```
۲. **فایل `backend/app/services/deep_analysis_service.py`**: در بلوک except اصلی (خطوط ۵۶۸-۵۷۳) که `results['error'] = str(e)` را set می‌کند، اگر این سرویس در context یک streaming generator استفاده می‌شود (مثلاً از طریق `analysis.py` یا `project_health.py`)، همان الگوی ایمن‌سازی را اعمال کن. اگر این سرویس مستقیماً yield نمی‌کند، حداقل `str(e)[:500]` را در `results['error']` اعمال کن تا payload بزرگ نشود.
۳. **جستجوی کامل**: با grep روی کل backend دنبال `event: error` و `yield.*error.*json.dumps` بگرد تا مطمئن شوی هیچ مکان دیگری از این pattern استفاده نمی‌کند.
۴. **بررسی `backend/app/api/routes/analysis.py`**: این فایل از `deep_analysis_service.py` استفاده می‌کند و احتمالاً streaming endpoint دارد — همان الگو را بررسی و اعمال کن.
۵. commit با پیام: `fix(stream): limit error message to 500 chars and wrap yield in try/except`

## 💡 نمونه‌های قبل/بعد
**ایمن‌سازی yield رویداد خطا در SSE stream (chat.py و سایر streaming endpoints)**

_قبل:_
```
yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

_بعد:_
```
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
```

**محدود کردن طول خطا در deep_analysis_service.py (خط ۵۷۲)**

_قبل:_
```
results["status"] = "failed"
            results["error"] = str(e)
```

_بعد:_
```
results["status"] = "failed"
            results["error"] = str(e)[:500]
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'event: error' backend/app/api/routes/ backend/app/services/`
- `grep -rn 'str(e)\[:500\]' backend/app/api/routes/ backend/app/services/`
- `grep -rn 'internal stream error' backend/app/api/routes/`
- `pytest backend/tests/ -k 'stream' -v`
- `python -c "import ast; ast.parse(open('backend/app/api/routes/chat.py').read()); print('syntax OK')"`

## ⚠️ ریسک‌ها و موارد احتیاط
۱. **تغییر در `chat.py`**: این فایل deep-read نشده — اگر چندین generator function داشته باشد، باید همه را پیدا کرد؛ جا انداختن یکی از آن‌ها ریسک امنیتی باقی می‌گذارد. ۲. **تغییر در `deep_analysis_service.py` خط ۵۷۲**: این تابع (`run_full_analysis`) توسط `backend/app/api/routes/analysis.py` و `backend/app/api/routes/project_health.py` call می‌شود — تغییر در error payload ممکن است روی parsing نتیجه در این دو route اثر بگذارد اگر آن‌ها انتظار فیلد `error` با طول نامحدود داشته باشند. ۳. **fallback string**: رشته fallback `event: error\ndata: {"error": "internal stream error"}\n\n` باید دقیقاً valid SSE format باشد — اشتباه در escape کردن `"` می‌تواند client را دچار parse error کند. ۴. **grep ناقص**: اگر pattern `event: error` در فایل‌های دیگر (مثل `orchestrator.py` یا `oversight.py`) هم وجود داشته باشد و پیدا نشود، ریسک باقی می‌ماند.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 39: اجرای تست‌های موجود پیش از merge برای جلوگیری از رگرشن

**Scope:** این بخش شامل اجرای تمام تست‌های موجود در پروژه (unit, integration, e2e) پیش از انجام merge است. هدف اطمینان از عدم ایجاد رگرشن (regression) در کد موجود است. هیچ تغییری در کد یا تست‌ها در این مرحله انجام نمی‌شود. این یک مرحله QA/اعتبارسنجی است و نه توسعه.
**Key terms:** merge, تست‌های موجود, رگرشن, regression

**بخش مربوط از متن کاربر:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای تست‌های موجود پیش از merge برای جلوگیری از رگرشن

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/test_runtime_verify_stage1.py:1-10` — `کل فایل تست` — یکی از فایل‌های تست موجود در پروژه که باید اجرا شود. محتوای دقیق آن در deep context موجود نیست.
  ```python
  # فایل تست stage1 از runtime verify
  ```
- `backend/tests/test_runtime_verify_integration.py:1-10` — `کل فایل تست` — یکی از فایل‌های تست موجود در پروژه که باید اجرا شود. محتوای دقیق آن در deep context موجود نیست.
  ```python
  # فایل تست integration از runtime verify
  ```
- `frontend/package.json:10-12` — `scripts.lint` — اسکریپت lint برای frontend که باید اجرا شود.
  ```json
  "lint": "next lint"
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/tests/test_code_content_searcher.py` (سطر 1) — یکی از فایل‌های تست موجود در پروژه که باید اجرا شود.
- `backend/tests/test_inspector_oversight_bridge.py` (سطر 1) — یکی از فایل‌های تست موجود در پروژه که باید اجرا شود.

## 🔍 Context و وضعیت فعلی
این تسک شامل اجرای تمام تست‌های موجود در پروژه (unit, integration, e2e) پیش از انجام merge است. هدف اطمینان از عدم ایجاد رگرشن (regression) در کد موجود است. هیچ تغییری در کد یا تست‌ها در این مرحله انجام نمی‌شود. این یک مرحله QA/اعتبارسنجی است و نه توسعه.

کلیدواژه‌های کاربر: merge, تست‌های موجود, رگرشن, regression.

بر اساس ساختار پروژه، تست‌های موجود در مسیر `backend/tests/` قرار دارند و شامل فایل‌های زیر هستند:
- backend/tests/test_code_content_searcher.py
- backend/tests/test_inspector_oversight_bridge.py
- backend/tests/test_iterative_orchestrator.py
- backend/tests/test_runtime_verify_autodetect.py
- backend/tests/test_runtime_verify_integration.py
- backend/tests/test_runtime_verify_real_servers.py
- backend/tests/test_runtime_verify_stage1.py
- backend/tests/test_runtime_verify_stage2.py
- backend/tests/test_runtime_verify_stage3a.py
- backend/tests/test_runtime_verify_stage3b.py
- backend/tests/test_runtime_verify_stage3cd.py
- backend/tests/test_runtime_verify_stage3e.py
- backend/tests/test_runtime_verify_stage6.py
- backend/tests/test_runtime_verify_stage9.py
- backend/tests/test_verify_v7.py

همچنین در `frontend/package.json` اسکریپت lint تعریف شده است. هیچ فایل تست frontend در ساختار پروژه دیده نمی‌شود.

این تسک مستقل است و وابستگی به تسک دیگری ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مراحل اجرای تست‌ها:
1. اجرای تمام تست‌های backend با دستور `pytest backend/tests/ -v` از ریشه پروژه.
2. بررسی خروجی pytest برای اطمینان از عبور تمام تست‌ها (PASS).
3. در صورت وجود خطا (FAIL/ERROR)، گزارش خطا به توسعه‌دهنده برای رفع قبل از merge.
4. اجرای lint برای frontend با دستور `cd frontend && npm run lint`.
5. ثبت نتیجه نهایی (همه تست‌ها PASS / برخی FAIL) در گزارش merge.

هیچ تغییری در کد یا فایل‌های تست انجام نمی‌شود. این یک مرحله purely QA است.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: critical
- تخمین زمان: small

---

## ✅ معیارهای پذیرش کلی (همهٔ مراحل)
- [ ] {'text': 'فایل `docs/EXECUTION_PROTOCOL.md` در repo وجود داشته باشد و شامل سه بخش اصلی: بررسی پیاده\u200cسازی قبلی، مسئولیت مستقل مدل، و مدیریت کارهای طولانی باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['EXECUTION_PROTOCOL', 'بررسی پیاده\u200cسازی قبلی', 'no-op', 'foundation.*core.*integration.*tests'], 'files_hint': ['docs/EXECUTION_PROTOCOL.md']}}
- [ ] {'text': 'فایل پروتکل باید شامل قالب کامیت no-op با مثال واقعی باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['no-op', 'commit', 'pre-existing'], 'files_hint': ['docs/EXECUTION_PROTOCOL.md']}}
- [ ] {'text': 'فایل پروتکل باید به hub های اصلی پروژه (database.py با 16 importer، ai_manager.py با 15 importer) اشاره کند', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['database.py', 'ai_manager.py', 'importer', 'hub'], 'files_hint': ['docs/EXECUTION_PROTOCOL.md']}}
- [ ] {'text': 'فایل `docs/ARCHITECTURE.md` یا `docs/README.md` باید لینک یا اشاره\u200cای به EXECUTION_PROTOCOL.md داشته باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['EXECUTION_PROTOCOL'], 'files_hint': ['docs/ARCHITECTURE.md', 'docs/README.md']}}
- [ ] {'text': 'هیچ فایل کد (py، ts، tsx) تغییر نکرده باشد — این تسک کاملاً مستنداتی است', 'verify_method': 'manual_only', 'verify_plan': {'reason': 'بررسی git diff برای اطمینان از اینکه فقط فایل\u200cهای docs/ تغییر کرده\u200cاند'}}
- [ ] {'text': 'ارسال project_path برابر با `../../etc/passwd` به endpoint POST /api/analysis/run-stream باید HTTP 400 یا 422 برگرداند و هیچ فایلی خوانده نشود', 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/analysis/run-stream', 'body': {'project_id': 'test', 'project_path': '../../etc/passwd', 'models': []}, 'expected_status': 400, 'required_fields': []}}
- [ ] {'text': 'ارسال project_path برابر با `/proc/1/environ` به endpoint POST /api/analysis/run-stream باید HTTP 400 برگرداند', 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/analysis/run-stream', 'body': {'project_id': 'test', 'project_path': '/proc/1/environ', 'models': []}, 'expected_status': 400, 'required_fields': []}}
- [ ] {'text': 'تابع validate_project_path باید در فایل analysis.py یا یک utility module وجود داشته باشد و از pathlib.Path.resolve() و relative_to() استفاده کند', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['resolve()', 'relative_to(', 'ALLOWED_PROJECTS_DIR', 'validate_project_path'], 'files_hint': ['backend/app/api/routes/analysis.py', 'backend/app/core/config.py']}}
- [ ] {'text': 'متغیر ALLOWED_PROJECTS_DIR باید در backend/app/core/config.py یا از os.environ خوانده شود', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['ALLOWED_PROJECTS_DIR', 'allowed_projects_dir', 'allowed_base'], 'files_hint': ['backend/app/core/config.py', 'backend/app/api/routes/analysis.py']}}
- [ ] {'text': 'تست\u200cهای path traversal در backend/tests/test_security.py باید pass شوند — شامل تست ../../etc، /proc/1/environ، و symlink escape', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_security.py::test_path_traversal', 'marker': 'security'}}
- [ ] {'text': 'یک project_path معتبر زیرمجموعه ALLOWED_PROJECTS_DIR باید بدون خطا پردازش شود و stream را شروع کند', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_security.py::test_valid_project_path_accepted', 'marker': 'security'}}
- [ ] {'text': 'در حلقه os.walk، هر full_path باید با os.path.realpath بررسی شود که هنوز زیرمجموعه project_path است', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['realpath', 'startswith(project_path', 'Skipping suspicious'], 'files_hint': ['backend/app/api/routes/analysis.py']}}
- [ ] {'text': 'درخواست با project_path معتبر داخل ./projects باید با status 200 پاسخ دهد', 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/analysis/analyze', 'body': {'project_path': './projects/test_project'}, 'expected_status': 200, 'required_fields': ['success']}}
- [ ] {'text': "درخواست با project_path حاوی path traversal (مثل ../../etc/passwd) باید با status 400 و detail 'Invalid project path' رد شود", 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/analysis/analyze', 'body': {'project_path': '../../etc/passwd'}, 'expected_status': 400, 'required_fields': ['detail']}}
- [ ] {'text': "متغیر BASE_DIR در analysis.py با مقدار os.path.abspath('./projects') تعریف شده باشد", 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['BASE_DIR', 'os.path.abspath', 'startswith(BASE_DIR'], 'files_hint': ['backend/app/api/routes/analysis.py']}}
- [ ] {'text': 'تست\u200cهای tests/test_analysis.py برای سناریوهای path traversal pass شوند', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_analysis.py', 'marker': 'path_validation'}}
- [ ] {'text': 'مسیر ./projects_evil که با ./projects شروع می\u200cشود اما خارج از BASE_DIR است باید با 400 رد شود (false positive prevention)', 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/analysis/analyze', 'body': {'project_path': './projects_evil/hack'}, 'expected_status': 400, 'required_fields': ['detail']}}
- [ ] {'text': 'کد اعتبارسنجی از os.sep برای جداکننده مسیر استفاده کند تا cross-platform باشد', 'verify_method': 'static', 'verify_plan': {'grep_patterns': ['BASE_DIR + os.sep', 'os.sep'], 'files_hint': ['backend/app/api/routes/analysis.py']}}
- [ ] {'text': "دستور curl با project_path='../../etc' باید پاسخ HTTP 4xx (400 یا 422) دریافت کند، نه 200 با stream داده", 'verify_method': 'api_response', 'verify_plan': {'method': 'POST', 'path': '/api/analysis/run-stream', 'body': {'project_id': 'test', 'project_path': '../../etc'}, 'expected_status': 422, 'required_fields': ['detail'], 'note': 'اگر status 200 برگشت و stream شروع شد، آسیب\u200cپذیری تأیید شده است'}}
- [ ] {'text': 'دستور `pytest tests/test_analysis.py -k path_traversal` باید بدون خطای import اجرا شود (حتی اگر تست\u200cها وجود نداشته باشند، باید collected 0 items نشان دهد نه error)', 'verify_method': 'backend_test', 'verify_plan': {'test_path': 'backend/tests/test_analysis.py', 'marker': 'path_traversal', 'command': 'pytest tests/test_analysis.py -k path_traversal -v'}}

## Acceptance Criteria

1. فایل `docs/EXECUTION_PROTOCOL.md` در repo وجود داشته باشد و شامل سه بخش اصلی: بررسی پیاده‌سازی قبلی، مسئولیت مستقل مدل، و مدیریت کارهای طولانی باشد _(verify: static)_
2. فایل پروتکل باید شامل قالب کامیت no-op با مثال واقعی باشد _(verify: static)_
3. فایل پروتکل باید به hub های اصلی پروژه (database.py با 16 importer، ai_manager.py با 15 importer) اشاره کند _(verify: static)_
4. فایل `docs/ARCHITECTURE.md` یا `docs/README.md` باید لینک یا اشاره‌ای به EXECUTION_PROTOCOL.md داشته باشد _(verify: static)_
5. هیچ فایل کد (py، ts، tsx) تغییر نکرده باشد — این تسک کاملاً مستنداتی است _(verify: manual_only)_
6. ارسال project_path برابر با `../../etc/passwd` به endpoint POST /api/analysis/run-stream باید HTTP 400 یا 422 برگرداند و هیچ فایلی خوانده نشود _(verify: api_response)_
7. ارسال project_path برابر با `/proc/1/environ` به endpoint POST /api/analysis/run-stream باید HTTP 400 برگرداند _(verify: api_response)_
8. تابع validate_project_path باید در فایل analysis.py یا یک utility module وجود داشته باشد و از pathlib.Path.resolve() و relative_to() استفاده کند _(verify: static)_
9. متغیر ALLOWED_PROJECTS_DIR باید در backend/app/core/config.py یا از os.environ خوانده شود _(verify: static)_
10. تست‌های path traversal در backend/tests/test_security.py باید pass شوند — شامل تست ../../etc، /proc/1/environ، و symlink escape _(verify: backend_test)_
11. یک project_path معتبر زیرمجموعه ALLOWED_PROJECTS_DIR باید بدون خطا پردازش شود و stream را شروع کند _(verify: backend_test)_
12. در حلقه os.walk، هر full_path باید با os.path.realpath بررسی شود که هنوز زیرمجموعه project_path است _(verify: static)_
13. درخواست با project_path معتبر داخل ./projects باید با status 200 پاسخ دهد _(verify: api_response)_
14. درخواست با project_path حاوی path traversal (مثل ../../etc/passwd) باید با status 400 و detail 'Invalid project path' رد شود _(verify: api_response)_
15. متغیر BASE_DIR در analysis.py با مقدار os.path.abspath('./projects') تعریف شده باشد _(verify: static)_
16. تست‌های tests/test_analysis.py برای سناریوهای path traversal pass شوند _(verify: backend_test)_
17. مسیر ./projects_evil که با ./projects شروع می‌شود اما خارج از BASE_DIR است باید با 400 رد شود (false positive prevention) _(verify: api_response)_
18. کد اعتبارسنجی از os.sep برای جداکننده مسیر استفاده کند تا cross-platform باشد _(verify: static)_
19. دستور curl با project_path='../../etc' باید پاسخ HTTP 4xx (400 یا 422) دریافت کند، نه 200 با stream داده _(verify: api_response)_
20. دستور `pytest tests/test_analysis.py -k path_traversal` باید بدون خطای import اجرا شود (حتی اگر تست‌ها وجود نداشته باشند، باید collected 0 items نشان دهد نه error) _(verify: backend_test)_
21. مقدار project_path='../../etc' نباید منجر به خواندن فایل‌های خارج از دایرکتوری مجاز شود — بررسی با grep در لاگ‌های سرور _(verify: static)_
22. endpoint /analysis/run-stream باید در برابر project_path='/etc/passwd' نیز محافظت کند (absolute path) _(verify: api_response)_
23. endpoint /analysis/run با project_path معتبر (مثلاً './myproject') باید همچنان کار کند و status 200 برگرداند _(verify: api_response)_
24. این تسک هیچ معیار پذیرش اجرایی ندارد — کاربر خودش تصریح کرده که این بخش شامل هیچ آیتم explicit برای اجرا نیست _(verify: manual_only)_
25. اگر هدف مستندسازی است: فایل docs/ARCHITECTURE.md باید بخش جدیدی با عنوان 'دستورالعمل‌های مدل اجراکننده' داشته باشد _(verify: static)_
26. اگر هدف PR template است: فایل .github/PULL_REQUEST_TEMPLATE.md باید ایجاد شده و شامل checklist کامیت‌ها باشد _(verify: static)_
27. کاربر باید clarify کند که هدف واقعی این درخواست چیست: مستندسازی در docs، PR template، یا embed در system prompt _(verify: manual_only)_
28. فایل backend/app/core/exception_handler.py باید وجود داشته باشد و شامل exception handler middleware برای HTTPException و Exception عمومی باشد. _(verify: static)_
29. فایل backend/app/core/logging_config.py باید وجود داشته باشد و شامل تنظیمات structlog یا loguru برای لاگینگ ساختاریافته JSON باشد. _(verify: static)_
30. middleware مدیریت خطا باید در backend/app/main.py ثبت شده باشد (app.add_exception_handler یا register_exception_handlers). _(verify: static)_
31. endpointهای اصلی در backend/app/api/routes/analysis.py باید دارای try/except و logging برای خطاهای runtime باشند. _(verify: static)_
32. endpointهای اصلی در backend/app/api/routes/chat.py باید دارای try/except و logging برای خطاهای runtime باشند. _(verify: static)_
33. لاگ‌های runtime باید به صورت ساختاریافته (JSON) با timestamp, level, module, message ثبت شوند. _(verify: static)_
34. تابع get_projects در backend/app/api/routes/projects.py باید دارای بلوک try/except باشد و خطاها را با logger.error و HTTPException(status_code=500) مدیریت کند. _(verify: static)_
35. تمامی endpointهای GET در فایل‌های routes (حداقل projects.py، analysis.py، chat.py) باید دارای مدیریت خطای مشابه باشند. _(verify: static)_
36. import مربوط به logger و HTTPException در فایل‌های routes وجود داشته باشد. _(verify: static)_
37. پیام خطا در logger.error مختص هر endpoint باشد (مثلاً 'Failed to get projects' برای projects و 'Failed to get analysis' برای analysis). _(verify: static)_
38. commit یا PR جدید با پیام واضح مانند 'feat: add error handling to API endpoints' ایجاد شده باشد. _(verify: manual_only)_
39. Rate limiting برای endpoint /analysis/run فعال باشد — decorator @limiter.limit در تابع run_analysis در analysis.py وجود داشته باشد _(verify: static)_
40. پس از تجاوز از محدودیت، endpoint POST /api/chat پاسخ 429 Too Many Requests برگرداند _(verify: api_response)_
41. Input validation با Pydantic Field در AnalysisRequest پیاده‌سازی شده باشد — min_length، max_length و field_validator برای project_path وجود داشته باشد _(verify: static)_
42. متغیرهای محیطی RATE_LIMIT_CHAT، RATE_LIMIT_ANALYSIS و MAX_REQUESTS در config.py تعریف شده و با os.getenv یا pydantic-settings خوانده شوند _(verify: static)_
43. slowapi در requirements.txt اضافه شده باشد _(verify: static)_
44. Limiter در main.py به app.state اضافه شده و exception handler برای RateLimitExceeded register شده باشد _(verify: static)_
45. ارسال project_path با مقدار '../../../etc/passwd' به endpoint /analysis/run باید پاسخ 422 Unprocessable Entity برگرداند _(verify: api_response)_
46. تمام تست‌های موجود در backend/tests/ پس از تغییرات همچنان pass شوند _(verify: backend_test)_
47. endpoint POST /api/analysis/run-stream باید بعد از ۵ درخواست در یک دقیقه از یک IP، پاسخ HTTP 429 Too Many Requests برگرداند _(verify: api_response)_
48. endpoint POST /api/analysis/run باید بعد از ۱۰ درخواست در یک دقیقه از یک IP، پاسخ HTTP 429 برگرداند _(verify: api_response)_
49. AnalysisRequest با project_path حاوی '..' باید HTTP 422 Unprocessable Entity برگرداند _(verify: api_response)_
50. AnalysisRequest با project_id حاوی کاراکترهای غیرمجاز (مثل ';DROP TABLE') باید HTTP 422 برگرداند _(verify: api_response)_
51. کلاس Limiter از slowapi باید در فایل analysis.py یا یک فایل core مشترک import و استفاده شده باشد _(verify: static)_
52. SlowAPIMiddleware باید در backend/app/main.py ثبت شده باشد _(verify: static)_
53. slowapi باید در backend/requirements.txt موجود باشد _(verify: static)_
54. field_validator برای project_path و project_id باید در AnalysisRequest تعریف شده باشد _(verify: static)_
55. فایل backend/app/api/routes/chat.py باید دکوراتور @limiter.limit('10/minute') را بالای تابع chat داشته باشد. _(verify: static)_
56. import مربوط به limiter (از slowapi) در فایل chat.py یا main.py اضافه شده باشد. _(verify: static)_
57. ارسال درخواست POST به /chat با نرخ بیش از 10 در دقیقه باید پاسخ HTTP 429 Too Many Requests برگرداند. _(verify: api_response)_
58. ارسال درخواست POST به /chat با نرخ کمتر از 10 در دقیقه باید پاسخ موفق (200) برگرداند. _(verify: api_response)_
59. دستور اول curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' اجرا شود و HTTP status code مشخصی (200، 422، یا 500) برگرداند _(verify: api_response)_
60. دستور دوم (۲۰ درخواست همزمان) بدون crash سرور اجرا شود — سرور بعد از اتمام همه درخواست‌ها همچنان پاسخگو باشد _(verify: api_response)_
61. لاگ‌های backend در طول اجرای دستورات هیچ unhandled exception یا traceback نشان ندهند _(verify: manual_only)_
62. response body دستور اول یک JSON معتبر باشد (نه HTML error page یا plain text) _(verify: api_response)_
63. بعد از اجرای ۲۰ درخواست همزمان، memory usage سرور به‌طور غیرعادی افزایش نیابد _(verify: manual_only)_
64. فایل راهنمای رفتاری مدل اجراکننده در docs/ وجود داشته باشد (یا ARCHITECTURE.md به‌روزرسانی شده باشد) و شامل سه بخش: بررسی پیاده‌سازی قبلی، مسئولیت مدل، مدیریت کارهای طولانی _(verify: static)_
65. در صورت وجود قابلیت از قبل پیاده‌شده، یک کامیت no-op با توضیح کامل ثبت شده باشد که مشخص کند کدام فایل‌ها درخواست را پوشش می‌دهند _(verify: static)_
66. ترتیب کامیت‌ها در هر PR طولانی باید الگوی foundation → core → integration → tests را دنبال کند و checklist در PR description موجود باشد _(verify: manual_only)_
67. فایل backend/app/main.py یا docs/ شامل reference به راهنمای رفتاری باشد تا مدل‌های اجراکننده هنگام بررسی entry point آن را ببینند _(verify: static)_
68. هیچ فایل یا تابع موجودی بدون بررسی قبلی دوباره ساخته نشده باشد — به‌ویژه در فایل‌های پرکاربرد مانند backend/app/core/database.py و backend/app/services/ai_manager.py _(verify: static)_
69. تابع run_analysis_task باید analysis_db.close() را در finally block فراخوانی کند — بررسی با grep برای وجود finally و close _(verify: static)_
70. پس از تغییر، هیچ session بازی در صورت خطا باقی نماند — شبیه‌سازی با raise Exception در run_analysis_task و بررسی لاگ connection _(verify: backend_test)_
71. الگوی finally block با توابع دیگر analysis.py (get_analysis_reports) همخوانی داشته باشد _(verify: static)_
72. تغییر فقط روی run_analysis_task اعمال شود و توابع دیگر (get_analysis_reports, get_analysis_report, delete_analysis_report, download_analysis_report) untouched بمانند _(verify: static)_
73. session در run_analysis_stream در finally بسته شود _(verify: static)_
74. هیچ نشت connection در لاگ‌ها دیده نشود _(verify: manual_only)_
75. تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود _(verify: manual_only)_
76. هیچ تستی fail نمی‌شود (pytest) _(verify: backend_test)_
77. linter بدون warning عبور می‌کند _(verify: static)_
78. type-check موفق است (mypy) _(verify: static)_
79. در `backend/app/api/routes/analysis.py`، هر فراخوانی `SessionLocal()` باید درون بلوک `try/finally` با `db.close()` در finally باشد _(verify: static)_
80. در `backend/app/api/routes/chat.py`، هر فراخوانی `SessionLocal()` باید درون بلوک `try/finally` با `db.close()` در finally باشد _(verify: static)_
81. در `backend/app/api/routes/github_import.py`، هر فراخوانی `SessionLocal()` باید درون بلوک `try/finally` با `db.close()` در finally باشد _(verify: static)_
82. تابع `get_db` در `backend/app/core/database.py` باید از الگوی `yield` با `try/finally` استفاده کند _(verify: static)_
83. هیچ `SessionLocal()` بدون `try/finally` در کل پوشه `backend/app/` وجود نداشته باشد — grep سراسری باید نتیجه صفر برگرداند _(verify: static)_
84. endpoint `POST /api/analysis/run-stream` باید بعد از اتمام تحلیل (موفق یا ناموفق) session را ببندد — قابل تست با بررسی connection pool _(verify: api_response)_
85. متغیر analysis_db با مقدار اولیه None قبل از try block تعریف شده باشد (خط قبل از try در run_analysis_task) _(verify: static)_
86. در finally block تابع run_analysis_task، دستور analysis_db.close() با guard مناسب (if analysis_db is not None) وجود داشته باشد _(verify: static)_
87. endpoint POST /api/analysis/run-stream همچنان پاسخ ۲۰۰ با content-type text/event-stream برمی‌گرداند _(verify: api_response)_
88. در صورت بروز exception در run_analysis_task، سیگنال done همچنان در progress_queue قرار می‌گیرد (رفتار قبلی حفظ شده باشد) _(verify: static)_
89. بستن analysis_db در یک try/except جداگانه داخل finally انجام شود تا خطای close باعث از دست رفتن سیگنال done نشود _(verify: static)_
90. قبل از هر تغییر، grep -r روی backend/ و frontend/ اجرا شده و نتایج مستند شده‌اند — هیچ تغییری بدون این بررسی اولیه اعمال نمی‌شود _(verify: static)_
91. اگر قابلیت درخواست‌شده از قبل در repo موجود است، یک کامیت no-op با پیام توضیحی ثبت شده که دقیقاً کدام فایل و خطوط آن را پوشش می‌دهند _(verify: static)_
92. فایل‌های هاب (database.py با 14 importer، ai_manager.py با 11 importer، project.py با 9 importer) قبل از هر تغییر بررسی و وضعیت‌شان مستند شده است _(verify: static)_
93. ترتیب کامیت‌ها منطقی است: foundation → core → integration → tests — هیچ کامیت integration قبل از foundation وجود ندارد _(verify: manual_only)_
94. PR description شامل checklist کامل از همه کامیت‌ها با وضعیت هر مورد (✅ انجام شد / ⏭️ no-op / 🔧 اصلاح شد) است _(verify: manual_only)_
95. هیچ تابع یا class موجود در backend/app/services/ دوباره ساخته نشده — فقط موارد ناقص تکمیل شده‌اند _(verify: static)_
96. آخرین کامیت‌های inspector (7d341e3، bf98db1، cd39cc3) بررسی شده‌اند و تغییرات جدید با آن‌ها conflict ندارند _(verify: backend_test)_
97. ارسال project_path='../../etc/' به POST /analysis/run-stream باید با خطای 400 یا 422 رد شود _(verify: api_response)_
98. ارسال project_path='/app/projects/myproject' باید مجاز باشد و خطای validation ندهد _(verify: api_response)_
99. تابع validate_project_path در backend/app/core/config.py تعریف شده باشد و با os.path.abspath و os.path.commonpath کار کند _(verify: static)_
100. کلاس AnalysisRequest در analysis.py باید field_validator برای project_path داشته باشد _(verify: static)_
101. تست‌های واحد path traversal در backend/tests/test_security.py باید pass شوند _(verify: backend_test)_
102. همه تست‌های موجود (backend/tests/) باید بدون fail باقی بمانند _(verify: backend_test)_
103. ارسال project_path با مقدار '../../etc/passwd' به endpoint تحلیل باید HTTP 400 با detail 'Invalid project path' برگرداند _(verify: api_response)_
104. ارسال project_path با مقدار '/tmp/evil' (مسیر absolute خارج از ALLOWED_BASE) باید HTTP 400 برگرداند _(verify: api_response)_
105. ثابت ALLOWED_BASE در analysis.py تعریف شده و از pathlib.Path استفاده می‌کند _(verify: static)_
106. validation block با startswith check در analysis.py وجود دارد و HTTPException raise می‌کند _(verify: static)_
107. تست‌های backend/tests/test_security.py همگی pass شوند _(verify: backend_test)_
108. ارسال project_path معتبر درون /app/projects باید endpoint را بدون خطای 400 اجرا کند _(verify: api_response)_
109. دستور curl با project_path='../../etc/' باید HTTP 400 یا 422 برگرداند، نه 200 _(verify: api_response)_
110. pytest backend/tests/test_security.py -k path_traversal باید pass شود _(verify: backend_test)_
111. فایل backend/tests/test_security.py باید وجود داشته باشد و حداقل یک تابع test_path_traversal داشته باشد _(verify: static)_
112. ارسال project_path='/etc/passwd' نیز باید با 400/422 رد شود _(verify: api_response)_
113. AnalysisRequest در analysis.py باید field_validator یا validator برای project_path داشته باشد _(verify: static)_
114. ارسال مسیر `../../etc/passwd` به endpoint POST /analysis/run خطای 422 با فیلد `detail` برمی‌گرداند _(verify: api_response)_
115. ارسال مسیر `/etc/` به endpoint POST /analysis/run خطای 422 با فیلد `detail` برمی‌گرداند _(verify: api_response)_
116. ارسال مسیر `/proc/self/environ` به endpoint POST /analysis/run خطای 422 برمی‌گرداند _(verify: api_response)_
117. decorator @field_validator با نام validate_project_path در کلاس AnalysisRequest در فایل analysis.py تعریف شده باشد _(verify: static)_
118. مسیرهای معتبر مانند `/valid/path` یا `/app/projects/myproject` باید بدون خطای validation پردازش شوند (status 200 یا خطای business logic — نه 422) _(verify: api_response)_
119. ارسال مسیر `../../../root/.ssh/id_rsa` (path traversal عمیق‌تر) نیز خطای 422 برمی‌گرداند _(verify: api_response)_
120. ارسال `project_path: '../../etc/passwd'` به `POST /analysis/run` باید HTTP 422 برگرداند _(verify: api_response)_
121. ارسال `project_path: '/etc/'` به `POST /analysis/run` باید HTTP 422 برگرداند _(verify: api_response)_
122. تابع `validate_project_path` در فایل `backend/app/core/path_utils.py` یا `backend/app/core/config.py` تعریف شده باشد و از `os.path.abspath` و `os.path.commonpath` استفاده کند _(verify: static)_
123. تابع `validate_project_path` در هر دو endpoint `run_analysis` و `run_analysis_stream` در `backend/app/api/routes/analysis.py` فراخوانی شده باشد _(verify: static)_
124. ارسال `project_path: '/projects/my-valid-project'` به `POST /analysis/run` نباید خطای 422 بدهد (مسیر معتبر داخل /projects پذیرفته شود) _(verify: backend_test)_
125. اجرای `pytest backend/` بدون failure پاس شود _(verify: backend_test)_
126. هیچ endpointای در analysis.py از SessionLocal() مستقیم بدون context manager استفاده نکند _(verify: static)_
127. همهٔ endpointهای analysis.py، model_profiles.py و project_health.py از Depends(get_db) یا async context manager استفاده کنند _(verify: static)_
128. تست نشت connection با 1000 درخواست هم‌زمان پاس شود: tests/test_db_connection_leak.py::test_concurrent_requests_no_leak _(verify: backend_test)_
129. import Depends از fastapi در ابتدای analysis.py وجود داشته باشد _(verify: static)_
130. import get_db از core.database در ابتدای analysis.py (نه داخل توابع) وجود داشته باشد _(verify: static)_
131. تست‌های رگرشن موجود (backend/tests/) بدون fail اجرا شوند _(verify: backend_test)_
132. endpoint GET /analysis/reports با پارامتر project_id پاسخ 200 برگرداند _(verify: api_response)_
133. فایل docs/AGENT_EXECUTION_GUIDE.md در repo وجود داشته باشد و شامل ۵ بخش اصلی (بررسی پیش از اجرا، no-op commit، مسئولیت مستقل، ترتیب کامیت‌ها، AC های مبهم) باشد _(verify: static)_
134. هیچ فایل Python یا TypeScript در این تسک تغییر نکرده باشد — تسک صرفاً مستندسازی است _(verify: static)_
135. محتوای docs/ARCHITECTURE.md یا docs/README.md شامل یک ارجاع (لینک) به AGENT_EXECUTION_GUIDE.md باشد _(verify: static)_
136. پیش از ایجاد فایل جدید، مجری باید بررسی کرده باشد که محتوای مشابه در docs/AUDIT_REPORT.md یا docs/PHASE_5_META_VALIDATION.md وجود ندارد — این بررسی باید در commit message مستند شده باشد _(verify: manual_only)_
137. commit message تسک باید شامل توضیح دلیل ایجاد فایل جدید (به‌جای تکمیل فایل موجود) باشد _(verify: manual_only)_
138. تمام فراخوانی‌های SessionLocal() در analysis.py باید یک finally: db.close() متناظر داشته باشند — grep روی فایل نباید هیچ SessionLocal() بدون finally پیدا کند _(verify: static)_
139. endpoint GET /api/analysis/reports باید با status 200 پاسخ دهد و session leak نداشته باشد _(verify: api_response)_
140. endpoint GET /api/analysis/reports/{report_id} با id نامعتبر باید 404 برگرداند و session را ببندد — یعنی finally block اجرا شده باشد _(verify: api_response)_
141. در فایل analysis.py هیچ بلوک try که SessionLocal() دارد نباید بدون finally: db.close() باشد — بررسی static با شمارش تعداد SessionLocal() و تعداد db.close() در finally _(verify: static)_
142. فایل‌های model_profiles.py و project_health.py در این مرحله تغییر نکرده باشند — git diff نباید این فایل‌ها را نشان دهد _(verify: static)_
143. هیچ endpoint در backend/app/api/routes/ از SessionLocal() مستقیم بدون try/finally یا Depends(get_db) استفاده نکند _(verify: static)_
144. تمام endpointهای CRUD در analysis.py (get_analysis_reports، get_analysis_report، delete_analysis_report، download_analysis_report، get_schedule، update_schedule، delete_schedule، get_analysis_stats) از db: Session = Depends(get_db) در signature استفاده کنند _(verify: static)_
145. GET /api/analysis/reports → 200 با فیلد array خالی یا پر (بدون خطای connection leak) _(verify: api_response)_
146. تست نشت connection: 1000 درخواست هم‌زمان به GET /api/analysis/reports بدون افزایش تعداد connection های باز در pool _(verify: backend_test)_
147. pytest backend/tests/ بدون هیچ failure اجرا شود _(verify: backend_test)_
148. analysis_db در run_analysis_stream (backend/app/api/routes/analysis.py خط ۱۱۷) در همه مسیرها (موفقیت، exception، task cancel) بسته شود _(verify: static)_
149. mypy یا ruff روی backend/app/api/routes/ بدون error اجرا شود _(verify: backend_test)_
150. هیچ فراخوانی مستقیم `db = SessionLocal()` بدون `with` در فایل‌های services و routes وجود نداشته باشد _(verify: static)_
151. الگوی `with SessionLocal() as db:` در تمام مکان‌هایی که قبلاً try/finally داشتند وجود داشته باشد _(verify: static)_
152. متد get_available_models در ai_manager.py بدون session leak اجرا شود — تست با mock SessionLocal که __exit__ را track می‌کند _(verify: backend_test)_
153. متد get_enabled_status در ai_manager.py حتی در صورت raise شدن exception، session را ببندد _(verify: backend_test)_
154. هیچ `db.close()` مستقیم در کد services وجود نداشته باشد (چون context manager خودکار می‌بندد) _(verify: static)_
155. تمام تست‌های موجود در backend/tests/ بعد از تغییرات pass شوند _(verify: backend_test)_
156. اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند — SSE stream باید حاوی event با فیلد type=error و message غیرخالی باشد _(verify: api_response)_
157. اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت (fallback_error_message) ارسال می‌شود — کد باید شامل literal string fallback_error_message باشد _(verify: static)_
158. خطا با logger.exception یا logger.error با traceback کامل در لاگ‌های سرور ثبت می‌شود — نه silent fail _(verify: static)_
159. signature endpoint /api/analysis/run تغییر نکرده و response type (StreamingResponse با media_type text/event-stream) ثابت مانده است _(verify: static)_
160. تست backend برای سناریوی exception در deep_analysis_service وجود دارد و pass می‌شود _(verify: backend_test)_
161. در متد `AnalysisProgressTracker.emit` (خطوط ۸۰-۸۶ فایل deep_analysis_service.py)، بلوک `except Exception as e` باید شامل یک try/except داخلی باشد که تلاش می‌کند رویداد خطا را به callback ارسال کند و در صورت شکست، `logger.critical` فراخوانی شود. _(verify: static)_
162. در تابع `generate_events` (بخش truncate شده deep_analysis_service.py)، فراخوانی `progress_queue.put` باید داخل یک بلوک try/except باشد که در صورت خطا، `logger.critical` با پیام شامل نام event فراخوانی شود. _(verify: static)_
163. تابع `generate_events` باید دارای بلوک `finally` در سطح تابع باشد که رویداد `fatal` با پیام ثابت به `progress_queue` اضافه کند. _(verify: static)_
164. تست‌های موجود در `backend/tests/test_runtime_verify_integration.py` و `backend/tests/test_iterative_orchestrator.py` باید بدون regression pass شوند. _(verify: backend_test)_
165. منطق اصلی تحلیل (run_full_analysis، _run_micro_analysis، _analyze_single_file_with_models) نباید تغییر کند — فقط مدیریت خطا اضافه شده باشد. _(verify: static)_
166. رویداد `fatal` در `finally` نباید در جریان موفق (بدون exception) باعث ارسال رویداد اضافی به کلاینت شود — `finally` فقط در صورت خطا یا پایان غیرعادی باید رویداد ارسال کند. _(verify: manual_only)_
167. در `backend/app/api/routes/chat.py` هیچ `yield` ای با `event: error` بدون try/except وجود نداشته باشد _(verify: static)_
168. در `backend/app/services/deep_analysis_service.py` خط ۵۷۲، `results['error']` باید با `str(e)[:500]` محدود شده باشد _(verify: static)_
169. اگر json.dumps یا yield خودش با خطا مواجه شود، fallback ثابت `event: error\ndata: {"error": "internal stream error"}\n\n` ارسال شود _(verify: static)_
170. هیچ streaming endpoint دیگری در `backend/app/api/routes/` از pattern ناامن `yield.*event: error.*str(e)` بدون محدودیت طول استفاده نکند _(verify: static)_
171. تست واحد: شبیه‌سازی خطای بزرگ (مثلاً `Exception('x' * 1000)`) در streaming endpoint و تأیید اینکه payload ارسال‌شده حداکثر ۵۰۰ کاراکتر در فیلد error دارد _(verify: backend_test)_

## Task Steps

### Step 1: بررسی اولیه خودکار repo و جلوگیری از پیاده‌سازی مجدد
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک وظیفه فنی. محتوای آن دستورالعمل‌های متدولوژیک برای شروع کار است: بررسی وجود پیاده‌سازی قبلی، جستجوی فایل‌های مرتبط، و اجتناب از دوباره‌سازی. هیچ کد یا تغییری در این بخش درخواست نشده است. scope واقعی این بخش، فرآیند قبل از اجراست.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است، نه یک درخواست پیاده‌سازی. هدف آن اطمینان از این است که قبل از هر تغییری، ساختار repo، فایل‌های موجود و وابستگی‌ها بررسی شوند تا از پیاده‌سازی مجدد قابلیت‌های موجود جلوگیری شود. این بخش شامل دستورالعمل‌هایی برای جستجو، خواندن فایل‌های مرتبط، و تصمیم‌گیری بر اساس یافته‌ها است. هیچ کد یا تغییری در این بخش درخواست نشده است.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 2: اعتبارسنجی و sanitize مسیر پروژه در endpoint تحلیل استریم
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint POST /analysis/run-stream است. مسیر باید در برابر دایرکتوری مجاز (ALLOWED_PROJECTS_DIR) بررسی شود و از Path Traversal جلوگیری شود. همچنین باید بررسی شود که فایل‌های خوانده شده دارای پسوند مجاز (supported_extensions) باشند. این مرحله شامل تغییر در فایل backend/app/api/routes/analysis.py و احتمالاً backend/app/core/config.py است. تست‌های مربوطه در tests/test_analysis.py یا backend/tests/test_security.py اضافه می‌شوند.
**Excerpt:**
```
در endpoint `POST /analysis/run-stream` (فایل `backend/app/api/routes/analysis.py`، خطوط 83-268)، پارامتر `project_path` مستقیماً از درخواست کاربر دریافت شده و بدون هیچ sanitization در `os.walk` و `open` استفاده می‌شود. مهاجم می‌تواند با ارسال مسیرهایی مثل `../../etc` یا `/proc/1/environ` به فایل‌های حساس سیستم دسترسی پیدا کند. همچنین `supported_extensions` فقط پسوند فایل را چک می‌کند و محتوای واقعی فایل را بررسی نمی‌کند. این آسیب‌پذیری Path Traversal کلاسیک است.
```

### Step 3: اعتبارسنجی امنیتی مسیر پروژه (Path Traversal Prevention)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل پیاده‌سازی مکانیزم اعتبارسنجی برای پارامتر `project_path` در endpoint مربوطه است. هدف اصلی جلوگیری از حملات path traversal با محدود کردن مسیرها به یک دایرکتوری مجاز (مانند `./projects`). این مرحله شامل افزودن محدودیت حجم فایل (1MB) و timeout برای عملیات خواندن فایل نیز می‌شود. خارج از scope این مرحله: پیاده‌سازی خود endpoint یا تغییر در ساختار دیتابیس.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال `project_path=../../etc` خطای 400 برمی‌گرداند
- [ ] ارسال `project_path=/proc/1/environ` خطای 400 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `./projects` به درستی کار می‌کنند
- [ ] تست واحد برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی و محدود کردن `project_path` به یک دایرکتوری مجاز (مثلاً `/tmp/projects` یا `./projects`). از `os.path.abspath` و `os.path.commonpath` برای اطمینان از اینکه مسیر نهایی خارج از محدوده مجاز نیست استفاده شود. همچنین محدودیت حجم فایل خوانده‌شده (مثلاً 1MB) و timeout برای کل عملیات اضافه شود.
```

### Step 4: اعتبارسنجی مسیر پروژه در تحلیل کد
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن اعتبارسنجی امنیتی برای مسیر پروژه در endpoint تحلیل کد است. مسیر ورودی کاربر باید با BASE_DIR (که ./projects است) شروع شود تا از دسترسی به دایرکتوری‌های خارج از محدوده جلوگیری شود. فقط فایل backend/app/api/routes/analysis.py تحت تأثیر قرار می‌گیرد. تست‌های مرتبط در tests/test_analysis.py باید به‌روزرسانی شوند.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**اعتبارسنجی مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
BASE_DIR = os.path.abspath('./projects')
user_path = os.path.abspath(request.project_path)
if not user_path.startswith(BASE_DIR):
    raise HTTPException(400, 'Invalid project path')
for root, dirs, filenames in os.walk(user_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 5: اجرای دستورات اعتبارسنجی امنیتی (Path Traversal)
**Status:** `pending` (0%)
**Scope:** این بخش شامل دو دستور اعتبارسنجی است: (1) یک درخواست curl برای تست نفوذ path traversal با ارسال project_path='../../etc' به endpoint /analysis/run-stream، و (2) اجرای تست pytest مخصوص test_analysis.py با فیلتر path_traversal. این مرحله صرفاً اجرای دستورات تست است و شامل پیاده‌سازی کد یا تغییرات نمی‌شود.
**Excerpt:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc"}'`
- `pytest tests/test_analysis.py -k path_traversal`
```

### Step 6: پیاده‌سازی مدیریت خطا و لاگینگ در API Routes (analysis.py و chat.py)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن try-except به تمام route handlers در فایل‌های backend/app/api/routes/analysis.py و backend/app/api/routes/chat.py، لاگ کردن خطاهای 500 با timestamp, level, message, traceback، و برگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx) است. همچنین پیکربندی لاگر در backend/app/core/ باید بررسی شود. خارج از scope: تغییر در سایر فایل‌ها یا endpointها.
**Excerpt:**
```
📋 acceptance_criteria کامل:
  - همه route handlers دارای try-except باشند [verify_method=static] [verify_plan={"grep_patterns": ["try:", "except"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - خطاهای 500 به درستی لاگ شوند [verify_method=static] [verify_plan={"grep_patterns": ["logging.error", "logger.error", "log.error"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند [verify_method=static] [verify_plan={"grep_patterns": ["HTTPException", "status_code", "return JSONResponse"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/chat.py"]}]
  - لاگ‌ها شامل timestamp, level, message, traceback باشند [verify_method=static] [verify_plan={"grep_patterns": ["timestamp", "level", "message", "traceback"], "files_hint": ["backend/app/core/"]}]
```

### Step 7: یادداشت مهم برای مدل اجراکننده — بررسی مستقل پیش از تغییر
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده است که به مدل اجراکننده یادآوری می‌کند پیش از هر تغییری، ساختار repo، فایل‌های ذکرشده و وابستگی‌های آن‌ها را مستقل بررسی کند. این بخش شامل دستورالعمل‌های رفتاری برای مدل است و هیچ وظیفهٔ اجرایی مشخصی ندارد. بنابراین، این بخش به‌عنوان یک مرحلهٔ اجرایی در نظر گرفته نمی‌شود و باید رد شود.
— [merged] این بخش یک یادداشت هشداردهنده است که به مدل اجراکننده یادآوری می‌کند قبل از هر تغییری، ساختار repo، فایل‌های ذکرشده و وابستگی‌ها را مستقل بررسی کند. این بخش خودش یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک برای نحوه اجرای سایر مراحل است. شامل هیچ آیتم explicit برای اجرا نیست.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 8: افزودن middleware مدیریت خطا و لاگینگ سیستماتیک به API Routes
**Status:** `pending` (0%)
**Scope:** این مرحله شامل پیاده‌سازی exception handler middleware در backend/app/core/، افزودن logging configuration با structlog/loguru، و بهبود مدیریت خطا در routes analysis.py و chat.py است. خارج از scope: تغییر در سایر routes (مانند github_import.py, model_profiles.py)، تغییر در frontend، یا تغییر در سرویس‌های عمیق (DeepAnalysisService). نکته حیاتی: middleware باید در backend/app/main.py ثبت شود و لاگینگ باید خطاهای runtime را به صورت ساختاریافته ثبت کند.
**Excerpt:**
```
## 🎯 هدف
عدم مدیریت خطا و لاگینگ مناسب در API Routes

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن exception handler middleware و logging configuration
- `backend/app/api/routes/analysis.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد
- `backend/app/api/routes/chat.py` — نمونه route که نیاز به بهبود مدیریت خطا دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, structlog/loguru, Python logging

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
مدیریت خطا و لاگینگ برای پایداری و عیب‌یابی پروژه ضروری است. بدون آن، خطاهای تولید (production) قابل ردیابی نیستند.

## 🔍 Context و وضعیت فعلی
با بررسی نمونه فایل‌های routes (مانند analysis.py, chat.py, projects.py)، مشخص نیست که مدیریت خطا (exception handling) و لاگینگ به صورت سیستماتیک پیاده‌سازی شده باشد. این موضوع باعث می‌شود خطاهای runtime به درستی ثبت نشوند و عیب‌یابی دشوار شود.
```

### Step 9: پیاده‌سازی مدیریت خطا و لاگینگ ساختاریافته در route handlers
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن middleware سراسری برای مدیریت خطاها (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru است. همچنین باید تمام route handlers موجود (analysis, chat, github_import, model_profiles) به try-except مجهز شوند و پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شود. لاگ‌ها باید شامل timestamp, level, message, traceback باشند. این مرحله شامل نوشتن تست جدید نیست اما نباید تست‌های موجود را بشکند.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] همه route handlers دارای try-except باشند
- [ ] خطاهای 500 به درستی لاگ شوند
- [ ] پاسخ‌های HTTP مناسب (4xx, 5xx) برگردانده شوند
- [ ] لاگ‌ها شامل timestamp, level, message, traceback باشند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware برای مدیریت خطاهای سراسری (global exception handler) و لاگینگ ساختاریافته با استفاده از کتابخانه‌ای مانند structlog یا loguru. همچنین اضافه کردن try-except در تمام route handlers و بازگرداندن پاسخ‌های HTTP مناسب (4xx, 5xx).
```

### Step 10: افزودن مدیریت خطا به endpointهای API
**Status:** `pending` (0%)
**Scope:** این بخش شامل افزودن try/except و logging به endpointهای موجود در فایل‌های routes است. فقط endpointهای مشخص‌شده در مثال (مانند get_projects) هدف هستند، نه کل پروژه. نکته حیاتی: باید از logger و HTTPException مطابق مثال استفاده شود و خطاها به صورت 500 برگردانده شوند.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**قبل: عدم مدیریت خطا**

_قبل:_
```
@router.get('/projects')
async def get_projects():
    return await service.get_all()
```

_بعد:_
```
@router.get('/projects')
async def get_projects():
    try:
        return await service.get_all()
    except Exception as e:
        logger.error('Failed to get projects', exc_info=e)
        raise HTTPException(status_code=500, detail='Internal server error')
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 11: پیاده‌سازی Rate Limiting و Input Validation برای API Endpoints
**Status:** `pending` (0%)
**Scope:** این مرحله شامل پیاده‌سازی Rate Limiting برای تمام AI endpoints (chat و analysis) با بازگشت پاسخ 429 در صورت تجاوز از محدودیت، و همچنین پیاده‌سازی Input Validation با Pydantic برای تمام endpoints است. محدودیت‌ها باید از طریق متغیرهای محیطی قابل تنظیم باشند. فایل‌های اصلی backend/app/api/routes/analysis.py، backend/app/api/routes/chat.py و backend/app/core/ هستند. تست endpoints برای اطمینان از عدم تغییر رفتار API ضروری است.
— [merged] این مرحله شامل افزودن rate limiting برای تمام AI endpoints با استفاده از slowapi یا middleware سفارشی، و پیاده‌سازی input validation با Pydantic models است. محدودیت‌ها باید از طریق متغیرهای محیطی قابل تنظیم باشند. پس از تجاوز از محدودیت، پاسخ 429 برگردانده شود. تمام تست‌ها، linter و type-check باید پاس شوند. فایل‌های مرتبط شامل backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/config.py, backend/app/main.py هستند.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در مدیریت خطا ممکن است باعث تغییر رفتار API شود. نیاز به تست کامل endpoints.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 8
  id: 9c9bdd20-dd93-45b1-93fc-13e6e6de2afd
  عنوان اصلی: نبود Rate Limiting و Input Validation در API Endpoints
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/api/routes/chat.py, backend/app/core/

📋 acceptance_criteria کامل:
  - Rate limiting برای تمام AI endpoints فعال باشد [verify_method=static] [verify_plan={"grep_patterns": ["RateLimiter", "rate_limit", "limiter"], "files_hint": ["backend/app/core/", "backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - پس از تجاوز از محدودیت، پاسخ 429 Too Many Requests برگردانده شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/chat", "headers": null, "json_body": {"message": "test"}, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - Input validation با Pydantic برای تمام endpoints پیاده‌سازی شده باشد [verify_method=static] [verify_plan={"grep_patterns": ["BaseModel", "Field", "validator", "pydantic"], "files_hint": ["backend/app/api/routes/chat.py", "backend/app/api/routes/analysis.py"]}]
  - محدودیت‌ها قابل تنظیم از طریق متغیرهای محیطی باشند [verify_method=static] [verify_plan={"grep_patterns": ["os.getenv", "environ.get", "RATE_LIMIT", "MAX_REQUESTS"], "files_hint": ["backend/app/core/"]}]
```

### Step 12: افزودن Rate Limiting و Input Validation به API Endpoints
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن middleware rate limiting با استفاده از slowapi به برنامه FastAPI، اعمال rate limiting به endpoints حساس (chat و analysis)، و اطمینان از وجود validation مناسب Pydantic برای ورودی‌های این endpoints است. خارج از scope این مرحله: پیاده‌سازی rate limiting برای سایر endpoints، تست‌های امنیتی، یا تغییرات در frontend.
**Excerpt:**
```
## 🎯 هدف
نبود Rate Limiting و Input Validation در API Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/core/` — نیاز به افزودن rate limiter middleware
- `backend/app/api/routes/chat.py` — Endpoint حساس که نیاز به rate limiting دارد
- `backend/app/api/routes/analysis.py` — Endpoint حساس که نیاز به rate limiting دارد

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI, slowapi, Pydantic

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/main.py` (سطر 1) — فایل اصلی که middlewareها در آن ثبت می‌شوند

## 🌐 نقشهٔ وابستگی‌ها
Rate limiting برای محافظت در برابر سوءاستفاده و کنترل هزینه‌ها ضروری است. Input validation برای جلوگیری از حملات injection حیاتی است.

## 🔍 Context و وضعیت فعلی
با توجه به وجود endpoints برای AI calls (chat, analysis, debate) که هزینه‌بر هستند، نبود rate limiting می‌تواند منجر به حملات DoS و هزینه‌های غیرمنتظره شود. همچنین نبود input validation مناسب می‌تواند باعث injection attacks شود.
```

### Step 13: افزودن rate limiting به endpoint چت
**Status:** `pending` (0%)
**Scope:** این بخش شامل افزودن محدودیت نرخ (rate limiting) به endpoint POST /chat است. کد نمونه نشان‌دهنده استفاده از دکوراتور `@limiter.limit('10/minute')` است. خارج از scope: پیاده‌سازی خود limiter، تغییرات در config، یا تست‌های مرتبط. نکته حیاتی: فایل هدف backend/app/api/routes/chat.py است و باید از همان syntax نمونه پیروی کند.
**Excerpt:**
```
**قبل: بدون rate limiting**

_قبل:_
```
@router.post('/chat')
async def chat(request: ChatRequest):
    # بدون محدودیت نرخ
```

_بعد:_
```
@router.post('/chat')
@limiter.limit('10/minute')
async def chat(request: ChatRequest):
    # با محدودیت نرخ
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 14: اجرای دستورات اعتبارسنجی curl برای endpoint /api/chat
**Status:** `pending` (0%)
**Scope:** این بخش شامل اجرای دو دستور curl برای اعتبارسنجی endpoint /api/chat است. دستور اول یک درخواست POST ساده با body خالی است. دستور دوم ۲۰ درخواست همزمان POST با body خالی را اجرا می‌کند. این بخش صرفاً بر اجرای این دستورات و مشاهده خروجی آنها تمرکز دارد و شامل پیاده‌سازی یا تغییر کد نمی‌شود.
**Excerpt:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json'`
- `for i in {1..20}; do curl -X POST http://localhost:8000/api/chat -d '{}' -H 'Content-Type: application/json' &; done`
```

### Step 15: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا
**Status:** `pending` (0%)
**Scope:** این تسک مربوط به رفع نشت connection در تابع `run_analysis_stream` در فایل `backend/app/api/routes/analysis.py` است. هدف اصلی اطمینان از بسته شدن session دیتابیس در بلاک `finally` است تا در صورت بروز خطا، connection به دیتابیس بازگردانده شود. همچنین باید تست استرس با ۱۰۰ درخواست هم‌زمان برای اطمینان از عدم بروز خطای connection انجام شود. این تسک شامل بازبینی دستی لاگ‌ها برای عدم وجود نشت connection نیز می‌شود.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
Rate limiting ممکن است کاربران قانونی را تحت تأثیر قرار دهد. نیاز به تنظیم دقیق محدودیت‌ها.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 8
  id: 979942ad-03ba-4cd6-a5ba-dd563d8d5462
  عنوان اصلی: مدیریت Session دیتابیس ناقص و عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - session در `run_analysis_stream` در finally بسته شود [verify_method=static] [verify_plan={"grep_patterns": ["analysis_db\\.close\\(\\)", "finally"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - هیچ نشت connection در لاگ‌ها دیده نشود [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
  - تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_analysis.py::test_stress_100_concurrent", "timeout_seconds": 120}]
```

### Step 16: بررسی اولیه و پیش‌نیازهای اجرای درخواست (یادداشت مهم برای مدل اجراکننده)
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده و راهنمای کلی برای مدل اجراکننده است، نه یک درخواست اجرایی مشخص. شامل دستورالعمل‌هایی برای بررسی وجود پیاده‌سازی قبلی، مسئولیت‌پذیری در قبال تشخیص‌های خودکار، و نحوه برخورد با کارهای طولانی است. این بخش خودش یک مرحله اجرایی نیست، بلکه یک prelude برای تمام مراحل بعدی است. هیچ فایل یا کلاس خاصی برای تغییر در این بخش ذکر نشده، بلکه یک چارچوب رفتاری برای مدل تعیین می‌کند.
**Excerpt:**
```
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
```

### Step 17: رفع نشت Session در run_analysis_task با افزودن finally block برای بستن Session
**Status:** `pending` (0%)
**Scope:** این بخش فقط به رفع باگ نشت Session در تابع run_analysis_task در فایل backend/app/api/routes/analysis.py می‌پردازد. شامل افزودن try/finally برای بستن analysis_db در مسیر خطا و موفقیت است. سایر توابع موجود در analysis.py که از الگوی صحیح استفاده می‌کنند (get_analysis_reports, get_analysis_report, delete_analysis_report, download_analysis_report) نیازی به تغییر ندارند. مشکل مشابه در github_import.py قبلاً حل شده است و خارج از scope این بخش است.
**Excerpt:**
```
در فایل `backend/app/api/routes/analysis.py`، توابع `get_analysis_reports`، `get_analysis_report`، `delete_analysis_report` و `download_analysis_report` از الگوی `SessionLocal()` استفاده می‌کنند و session را در `finally` می‌بندند. اما در `run_analysis_stream` (خط 117)، یک `analysis_db = SessionLocal()` ایجاد می‌شود که در `finally` بسته نمی‌شود. اگر خطایی در `run_analysis_task` رخ دهد، session باز می‌ماند و باعث نشت connection در SQLite می‌شود.

```python
analysis_db = SessionLocal()

deep_analyzer = DeepAnalysisService(
    ai_manager=ai_manager,
    progress_callback=progress_callback,
    db_session=analysis_db
)
```
```

### Step 18: بستن session در finally تابع run_analysis_stream
**Status:** `pending` (0%)
**Scope:** این مرحله فقط به بستن session در بلوک finally تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py می‌پردازد. شامل بررسی ownership session بین تابع و DeepAnalysisService است. خارج از scope: سایر بخش‌های کد، تست‌ها، linter، type-check و تست استرس (این موارد در AC ذکر شده‌اند اما بخشی از اجرای این مرحله نیستند).
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] session در `run_analysis_stream` در finally بسته شود
- [ ] هیچ نشت connection در لاگ‌ها دیده نشود
- [ ] تست استرس با ۱۰۰ درخواست هم‌زمان باعث خطای connection نشود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. در `run_analysis_stream`، session ایجاد شده در خط 117 را در `finally` ببندید. همچنین بررسی کنید که آیا `DeepAnalysisService` ownership session را می‌گیرد یا خیر. اگر سرویس session را مدیریت می‌کند، نیازی به بستن در اینجا نیست، اما اگر ownership با این تابع است، حتماً بسته شود.
```

### Step 19: رفع نشت session در analysis_db با استفاده از try/finally
**Status:** `pending` (0%)
**Scope:** این بخش شامل اصلاح الگوی استفاده از SessionLocal در فایل‌های backend برای اطمینان از بسته شدن session پس از استفاده است. نمونه ارائه‌شده نشان‌دهنده تغییر از حالت بدون finally به حالت try/finally می‌باشد. خارج از scope: تغییرات در frontend، تست‌ها، یا فایل‌های config.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
analysis_db = SessionLocal()
# ... استفاده ...
# finally: بسته نمی‌شود
```

_بعد:_
```
analysis_db = SessionLocal()
try:
    # ... استفاده ...
finally:
    analysis_db.close()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 20: اضافه کردن finally block برای مدیریت ریسک در endpoint /api/analysis/run-stream
**Status:** `pending` (0%)
**Scope:** این بخش صرفاً به اضافه کردن یک finally block در endpoint /api/analysis/run-stream (فایل backend/app/api/routes/analysis.py) محدود می‌شود. هدف آن اطمینان از پاک‌سازی منابع (مانند بستن فایل‌ها یا اتصالات) حتی در صورت بروز خطا است. هیچ تغییر دیگری در منطق اعتبارسنجی ورودی یا مسیردهی انجام نمی‌شود. این مرحله مستقل از سایر تسک‌ها است.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
کم — فقط اضافه کردن finally block

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 8
  id: 49be9ac4-ed23-4874-975e-841175c6974b
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py
```

### Step 21: بررسی اولیه و مستندسازی وضعیت موجود repo قبل از هرگونه تغییر
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی مشخصی نیست. وظیفه آن الزام مدل به بررسی مستقل repo، شناسایی پیاده‌سازی‌های قبلی، و جلوگیری از بازسازی موارد موجود است. این بخش به‌تنهایی یک مرحله اجرایی نیست، بلکه یک دستورالعمل متدولوژیک برای کل فرآیند است. اگر تمام درخواست‌های بعدی قبلاً پیاده‌سازی شده باشند، باید یک کامیت no-op با توضیح ثبت شود.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 22: اعتبارسنجی مسیر پروژه در endpoint run_analysis_stream
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint run_analysis_stream است. مسیر باید از نظر وجود دایرکتوری، عدم وجود path traversal (مانند '..' یا '/') و محدود بودن به دایرکتوری‌های مجاز پروژه بررسی شود. همچنین باید از خواندن README از مسیرهای غیرمجاز جلوگیری کند. این مرحله شامل تغییر در backend/app/api/routes/analysis.py و احتمالاً backend/app/core/config.py برای تعریف مسیرهای مجاز است. تست‌های مربوطه در tests/test_analysis.py یا backend/tests/test_security.py اضافه می‌شوند.
**Excerpt:**
```
عدم اعتبارسنجی ورودی در endpoint /api/analysis/run-stream

- `backend/app/api/routes/analysis.py:84-268` — `run_analysis_stream` — کل endpoint نیاز به validation مسیر دارد
  ```python
  async def run_analysis_stream(request: AnalysisRequest):
      ...
      project_path = request.project_path  # ⚠️ user-supplied, no validation
      ...
      for root, dirs, filenames in os.walk(project_path):  # ⚠️ path traversal
  ```

FastAPI + Python os.walk + Pydantic models

- `backend/app/api/routes/analysis.py` (سطر 127) — محل اصلی آسیب‌پذیری
- `backend/app/models/analysis_report.py` (سطر 1) — مدل AnalysisRequest که project_path را تعریف می‌کند

این endpoint توسط frontend/src/app/analysis/page.tsx (خط 190) فراخوانی می‌شود. هیچ middleware یا dependency دیگری مسیر را قبل از رسیدن به این تابع validation نمی‌کند.

در فایل backend/app/api/routes/analysis.py، endpoint run_analysis_stream (خط 84) پارامتر project_path را مستقیماً از درخواست کاربر دریافت کرده و در os.walk (خط 160) بدون هیچ sanitization استفاده می‌کند. این آسیب‌پذیری Path Traversal امکان خواندن فایل‌های خارج از مسیر پروژه را فراهم می‌کند. همچنین در خط 133-141، README از مسیر user-supplied خوانده می‌شود. مهاجم می‌تواند با ارسال project_path='../../etc/' فایل‌های حساس سیستم را بخواند.
```

### Step 23: افزودن اعتبارسنجی مسیر برای جلوگیری از Path Traversal در project_path
**Status:** `pending` (0%)
**Scope:** این بخش شامل پیاده‌سازی اعتبارسنجی مسیر در endpoint مربوط به project_path است. باید از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز (/app/projects) است استفاده شود. همچنین باید validation با Pydantic برای enforce کردن الگوی مسیر امن اضافه شود. تست واحد جدید برای path traversal باید اضافه شود و همه تست‌های موجود باید پاس شوند. linter و type-check نیز باید بدون مشکل عبور کنند.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال project_path='../../etc/' با خطای 400 رد شود
- [ ] مسیرهای درون /app/projects مجاز باشند
- [ ] تست واحد جدید برای path traversal اضافه شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اضافه کردن اعتبارسنجی مسیر: 1) استفاده از os.path.abspath و os.path.commonpath برای اطمینان از اینکه مسیر نهایی درون دایرکتوری مجاز است. 2) تعریف یک ریشه مجاز (مثلاً /projects یا /data) و reject کردن مسیرهای خارج از آن. 3) اضافه کردن validation با Pydantic برای project_path که الگوی مسیر امن را enforce کند.
```

### Step 24: اضافه کردن اعتبارسنجی مسیر پروژه در endpoint تحلیل
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن validation برای پارامتر project_path در endpoint مربوط به تحلیل پروژه است. مسیر باید به یک دایرکتوری مجاز (ALLOWED_BASE) محدود شود تا از دسترسی به فایل‌های خارج از محدوده جلوگیری شود. تغییرات فقط در فایل backend/app/api/routes/analysis.py اعمال می‌شود. تست‌های امنیتی مرتبط در backend/tests/test_security.py باید به‌روزرسانی شوند. این مرحله شامل تغییرات frontend یا سایر سرویس‌ها نیست.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**اضافه کردن validation مسیر**

_قبل:_
```
project_path = request.project_path
for root, dirs, filenames in os.walk(project_path):
```

_بعد:_
```
import os
from pathlib import Path

ALLOWED_BASE = Path('/app/projects').resolve()
user_path = Path(request.project_path).resolve()
if not str(user_path).startswith(str(ALLOWED_BASE)):
    raise HTTPException(400, 'Invalid project path')
project_path = str(user_path)
for root, dirs, filenames in os.walk(project_path):
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 25: اجرای دستورات اعتبارسنجی امنیتی برای مسیرهای فایل
**Status:** `pending` (0%)
**Scope:** این بخش شامل دو دستور اعتبارسنجی است: (1) یک درخواست curl برای تست endpoint تحلیل با مسیر فایل مخرب (path traversal) و (2) اجرای تست pytest مخصوص آسیب‌پذیری path traversal. هدف این مرحله تأیید امنیت endpoint در برابر حملات path traversal است. این بخش صرفاً دستورات تست را مشخص می‌کند و شامل پیاده‌سازی کد یا تغییر در فایل‌ها نیست.
**Excerpt:**
```
## 🧪 دستورات اعتبارسنجی
- `curl -X POST http://localhost:8000/api/analysis/run-stream -H 'Content-Type: application/json' -d '{"project_id":"test","project_path":"../../etc/"}'`
- `pytest backend/tests/test_security.py -k path_traversal`
```

### Step 26: اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن اعتبارسنجی برای پارامتر project_path در endpoint /analysis/run است. فقط validation سمت سرور (backend) در فایل backend/app/api/routes/analysis.py انجام می‌شود. منطق business (تحلیل پروژه) تغییر نمی‌کند. مسیرهای معتبر باید همچنان کار کنند و مسیرهای نامعتبر (مانند path traversal یا مسیرهای مطلق غیرمجاز) باید خطای 422 برگردانند.
**Excerpt:**
```
تسک 6 از 8
  id: 866ea2f9-0e88-4848-9c2a-d9b72c654747
  عنوان اصلی: عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "../../etc/passwd"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - ارسال مسیر `/etc/` خطای 422 برمی‌گرداند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/etc/"}, "expected_status": 422, "required_fields": ["detail"], "json_contains": null}]
  - مسیرهای معتبر داخل `/ [verify_method=api_response] [verify_plan={"method": "POST", "path": "/analysis/run", "headers": null, "json_body": {"project_path": "/valid/path"}, "expected_status": 200, "required_fields": ["result"], "json_contains": null}]
```

### Step 27: اعتبارسنجی ورودی project_path در endpoint تحلیل پروژه
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن validator به فیلد project_path در مدل Pydantic AnalysisRequest است تا از حملات Path Traversal جلوگیری شود. همچنین شامل اصلاح نحوه استفاده از project_path در تابع run_analysis_task برای امنیت بیشتر می‌شود. خارج از scope: تغییرات در frontend، middleware، یا سایر endpointها.
**Excerpt:**
```
عدم اعتبارسنجی ورودی در endpoint تحلیل پروژه (analysis.py)

- `backend/app/api/routes/analysis.py:30-36` — `AnalysisRequest` — فیلد project_path بدون validator است
  ```python
  class AnalysisRequest(BaseModel):
      """درخواست تحلیل"""
      project_id: str
      project_path: str
      models: List[str] = []
      roadmap_path: Optional[str] = None
  ```
- `backend/app/api/routes/analysis.py:127-180` — `run_analysis_task` — استفاده مستقیم از project_path در os.walk بدون اعتبارسنجی
  ```python
  project_path = request.project_path
  ...
  for root, dirs, filenames in os.walk(project_path):
      ...
      with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
  ```

این آسیب‌پذیری امکان Path Traversal را فراهم می‌کند: مهاجم می‌تواند با ارسال مسیرهایی مانند `../../etc/passwd` یا `/etc/` فایل‌های حساس سیستم را بخواند.
```

### Step 28: اعتبارسنجی مسیر پروژه برای جلوگیری از Path Traversal
**Status:** `pending` (0%)
**Scope:** این بخش شامل پیاده‌سازی اعتبارسنجی مسیرهای فایل در endpoint مربوط به تحلیل پروژه است. مسیرهای معتبر باید داخل دایرکتوری مجاز `/projects` باشند و مسیرهای حاوی `..` یا مسیرهای مطلق غیرمجاز (مانند `/etc/`) رد شوند. خروجی این مرحله فقط شامل منطق اعتبارسنجی است و شامل پیاده‌سازی endpoint یا تست‌ها نمی‌شود.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال مسیر `../../etc/passwd` به endpoint خطای 422 برمی‌گرداند
- [ ] ارسال مسیر `/etc/` خطای 422 برمی‌گرداند
- [ ] مسیرهای معتبر داخل `/
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. اعتبارسنجی مسیر پروژه با استفاده از `os.path.abspath` و `os.path.commonpath` برای جلوگیری از Path Traversal. همچنین محدود کردن مسیر به یک دایرکتوری مجاز (مثلاً `/projects`).
```

### Step 29: اضافه کردن validator به Pydantic مدل برای اعتبارسنجی مسیر پروژه
**Status:** `pending` (0%)
**Scope:** این بخش شامل افزودن یک validator به فیلد project_path در یک Pydantic مدل است. validator باید مسیر را به absolute تبدیل کند، بررسی کند که درون دایرکتوری مجاز (PROJECTS_BASE_DIR) قرار دارد و یک دایرکتوری موجود است. فایل دقیق مدل مشخص نشده، اما با توجه به مسیرهای موجود، احتمالاً در backend/app/models/analysis_report.py یا مدل مشابهی است. خارج از scope: تغییرات در API routes، سرویس‌ها یا frontend.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**اضافه کردن validator به Pydantic مدل**

_قبل:_
```
project_path: str
```

_بعد:_
```
project_path: str = Field(..., description="مسیر پروژه")

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        abs_path = os.path.abspath(v)
        allowed_base = os.path.abspath(os.environ.get('PROJECTS_BASE_DIR', '/projects'))
        if not abs_path.startswith(allowed_base):
            raise ValueError(f'Path must be within {allowed_base}')
        if not os.path.isdir(abs_path):
            raise ValueError('Path must be an existing directory')
        return abs_path
```
```

### Step 30: رفع نقص مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح تمام endpointهای موجود در فایل‌های backend/app/api/routes/analysis.py، backend/app/api/routes/model_profiles.py و backend/app/api/routes/project_health است تا به جای استفاده مستقیم از SessionLocal()، از Depends(get_db) یا async context manager استفاده کنند. همچنین شامل اجرای تست‌های رگرشن قبل از merge و اجرای تست نشت connection با 1000 درخواست هم‌زمان می‌شود. خارج از scope: تغییرات در frontend، config، یا سایر routeها.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: security
- اولویت: high
- تخمین زمان: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 8
  id: 51fab7d9-dba0-486e-8e29-77a459785fc3
  عنوان اصلی: نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند [verify_method=static] [verify_plan={"grep_patterns": ["SessionLocal\\(\\)"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - همه endpointها از Depends(get_db) یا async context manager استفاده کنند [verify_method=static] [verify_plan={"grep_patterns": ["Depends\\(get_db\\)", "async with.*get_db"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/model_profiles.py", "backend/app/api/routes/project_health"]}]
  - تست نشت connection با 1000 درخواست هم‌زمان پاس شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_db_connection_leak.py::test_concurrent_requests_no_leak", "timeout_seconds": 120}]
```

### Step 31: بررسی اولیه و اعتبارسنجی خودکار پیش از اجرا
**Status:** `pending` (0%)
**Scope:** این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل هیچ دستور اجرایی یا تغییر کد نمی‌شود. محتوای آن صرفاً یک راهنمای رفتاری برای مدل است که باید پیش از هر اقدامی، ساختار repo را مستقل بررسی کند، از بازسازی موارد موجود خودداری کند، و در صورت نیاز به چند کامیت، ترتیب منطقی را رعایت کند. هیچ فایل، کلاس یا تابعی برای تغییر در این بخش مشخص نشده است.
— [merged] این بخش یک یادداشت هشداردهنده برای مدل اجراکننده است و شامل دستورالعمل‌های اجرایی مستقیم نیست. وظیفه آن اطلاع‌رسانی درباره ماهیت احتمالی ناقص/اشتباه پرامپت، لزوم بررسی مستقل repo، و جلوگیری از بازسازی موارد موجود است. این بخش هیچ مرحله اجرایی مشخصی را تعریف نمی‌کند و صرفاً یک راهنمای رفتاری برای مدل است.
**Excerpt:**
```
## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به آن استناد نکن.

♻️ **احتمال پیاده‌سازی قبلی (مهم):**
- ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**.
- اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
- اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.

🔍 **مسئولیت تو (مدل اجراکننده):**
- پیش از هر تغییر، خودت ساختار repo، فایل‌های ذکرشده، و وابستگی‌های آن‌ها را مستقل بررسی کن.
- اگر تشخیص دادی موقعیت ذکرشده در پرامپت اشتباه است یا فایل دیگری مناسب‌تر است، بر اساس قضاوت خودت عمل کن — این پرامپت نمی‌تواند بهانهٔ کار اشتباه باشد ("خودت گفتی" قابل قبول نیست).
- اگر معیارهای پذیرش (AC) مبهم/ناقص بودند، بهترین تفسیر را انتخاب کن و در commit message توضیح بده.

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همهٔ کامیت‌ها در PR description بنویس.
```

### Step 32: رفع نشت Session دیتابیس در endpointهای analysis.py با استفاده از context manager یا finally block
**Status:** `pending` (0%)
**Scope:** این مرحله فقط به رفع نشت Session در فایل backend/app/api/routes/analysis.py می‌پردازد. تمام endpointهایی که مستقیماً SessionLocal() می‌سازند و db.close() را در finally ندارند، باید اصلاح شوند. فایل‌های model_profiles.py و project_health.py در این مرحله گنجانده نشده‌اند. راهکار پیشنهادی: استفاده از context manager (with SessionLocal() as db) یا اضافه کردن db.close() در finally قبل از raise. این مرحله شامل تست‌های unit test یا integration test نمی‌شود.
**Excerpt:**
```
نقص در مدیریت Session دیتابیس — عدم بستن Session در مسیرهای خطا

- `backend/app/api/routes/analysis.py:277-290` — `get_analysis_reports` — این تابع درست بسته می‌شود — الگو را به بقیه تعمیم بده
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
      return ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:293-306` — `get_analysis_report` — استثناء قبل از finally باعث نشت می‌شود — باید db را قبل از raise ببندیم یا از context manager استفاده کنیم
  ```python
  db = SessionLocal()
  try:
      report = db.query(...).first()
      if not report:
          raise HTTPException(...)  # ⚠️ اینجا db بسته نمی‌شود
      return ...
  finally:
      db.close()
  ```

در چندین endpoint (analysis.py, model_profiles.py, project_health.py) Session دیتابیس با `SessionLocal()` ساخته می‌شود اما در مسیرهای خطا (Exception) بسته نمی‌شود. این باعث نشت connection و در نهایت exhaustion pool دیتابیس می‌شود. نمونه: analysis.py خطوط 277-290 و 293-306 و 309-325 و 328-370 — همه از `SessionLocal()` استفاده می‌کنند و `db.close()` را در `finally` ندارند.
```

### Step 33: جایگزینی SessionLocal مستقیم با context manager یا Depends(get_db) در تمام endpointها
**Status:** `pending` (0%)
**Scope:** این بخش شامل جایگزینی تمام استفاده‌های مستقیم از SessionLocal() در endpointها با context manager (try/finally یا async context manager) یا Depends(get_db) است. هدف اطمینان از بسته شدن session در همه مسیرها (موفقیت و خطا) و جلوگیری از نشت connection است. خارج از scope: تغییر منطق business، اضافه کردن endpoint جدید، یا تغییر ساختار database. نکته حیاتی: این تغییر باید در تمام فایل‌های routes اعمال شود و تست نشت connection با 1000 درخواست هم‌زمان پاس شود.
**Excerpt:**
```
## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ endpointای از SessionLocal مستقیم بدون context manager استفاده نکند
- [ ] همه endpointها از Depends(get_db) یا async context manager استفاده کنند
- [ ] تست نشت connection با 1000 درخواست هم‌زمان پاس شود
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. تمام `SessionLocal()` ها را با context manager یا try/finally جایگزین کن تا در همه مسیرها (موفقیت و خطا) session بسته شود. یا از `Depends(get_db)` در همه endpointها استفاده کن.
```

### Step 34: رفع نشت session با استفاده از context manager
**Status:** `pending` (0%)
**Scope:** این بخش شامل تغییر الگوی مدیریت session در کد backend از try/finally به async with context manager است. فقط فایل‌هایی که از SessionLocal استفاده می‌کنند تحت تأثیر قرار می‌گیرند. تغییرات باید در routes و service‌های مرتبط اعمال شود. تست‌ها نیز باید به‌روزرسانی شوند.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**رفع نشت session**

_قبل:_
```
db = SessionLocal()
try:
    ...
    raise HTTPException(...)
finally:
    db.close()
```

_بعد:_
```
async with SessionLocal() as db:
    ...
    raise HTTPException(...)
# خودکار بسته می‌شود
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 35: رفع exception swallowed در run_analysis_stream با لاگ کافی و ارسال خطا به کاربر
**Status:** `pending` (0%)
**Scope:** این مرحله شامل پیاده‌سازی مدیریت خطا در تابع run_analysis_stream در فایل backend/app/api/routes/analysis.py است. باید اطمینان حاصل شود که اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار دریافت کند. همچنین اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت (fallback) ارسال شود. خارج از scope: تغییرات در frontend، تغییرات در signature endpointها، یا تغییرات در سایر فایل‌ها.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
تغییر در signature endpointها ممکن است frontend را بشکند اگر response type تغییر کند

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 8
  id: 037dbd0d-9561-4c00-be73-7bc923e2565b
  عنوان اصلی: exception swallowed در run_analysis_stream بدون لاگ کافی
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - اگر deep_analysis_service خطا بدهد، کاربر یک رویداد error با پیام معنی‌دار می‌بیند [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run", "headers": null, "json_body": {"analysis_type": "deep", "target": "test"}, "expected_status": 200, "required_fields": [], "json_contains": null}]
  - اگر json.dumps روی پیام خطا شکست بخورد، یک رویداد error با پیام ثابت ارسال می [verify_method=static] [verify_plan={"grep_patterns": ["except Exception", "json.dumps", "fallback_error_message"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
```

### Step 36: رفع بلعیده شدن استثناها در run_analysis_stream با لاگ‌گیری و مدیریت خطای جامع‌تر
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اصلاح دو بخش از فایل backend/app/api/routes/analysis.py است: (1) خطوط 251-253 در تابع generate_events که در آن خطای json.dumps درون except بلعیده می‌شود، و (2) خطوط 200-206 در تابع run_analysis_task که در آن خطای progress_queue.put بلعیده می‌شود. هدف این است که اطمینان حاصل شود هیچ استثنایی بدون لاگ یا بازخورد به کاربر باقی نمی‌ماند. خارج از scope این مرحله: اصلاح خطاهای run_full_analysis در deep_analysis_service.py، تغییرات در frontend، یا اضافه کردن heartbeat.
**Excerpt:**
```
exception swallowed در run_analysis_stream بدون لاگ کافی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:251-253` — `generate_events` — اگر json.dumps روی str(e) خطا بدهد، این except هم بلعیده می‌شود
  ```python
  except Exception as e:
              logger.error(f"Error in SSE stream: {e}")
              yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
  ```
- `backend/app/api/routes/analysis.py:200-206` — `run_analysis_task` — اگر progress_queue.put خطا بدهد (صف بسته)، خطا بلعیده می‌شود
  ```python
  except Exception as e:
                  logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                  await progress_queue.put({
                      "event": "error",
                      "message": str(e),
                      "error": True
                  })
  ```
```

### Step 37: پیاده‌سازی مدیریت خطاهای مقاوم در deep_analysis_service و generate_events
**Status:** `pending` (0%)
**Scope:** این مرحله شامل سه تغییر مجزا در مدیریت خطا است: (1) افزودن try/except تو در تو در خط 251 برای ارسال رویداد خطا در صورت شکست json.dumps، (2) افزودن try/except در خطوط 200-206 برای مدیریت خطای صف progress_queue، (3) افزودن finally در سطح تابع generate_events برای ارسال رویداد fatal در صورت خطای غیرمنتظره. خارج از scope: تغییر منطق اصلی، افزودن قابلیت جدید، یا تغییر تست‌ها.
**Excerpt:**
```
1. ۱. در `except Exception as e` خط ۲۵۱، یک try/except تو در تو برای ارسال رویداد خطا اضافه کن. ۲. در خط ۲۰۰-۲۰۶، بعد از `progress_queue.put` یک `try/except` بگذار که اگر صف خطا داد، حداقل با `logger.critical` لاگ شود. ۳. یک `finally` در سطح `generate_events` اضافه کن که اگر خطای غیرمنتظره‌ای رخ داد، یک رویداد `fatal` با پیام ثابت به صف اضافه کند.
```

### Step 38: ایمن‌سازی ارسال رویداد خطا در استریم رویداد
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر کد در فایل‌های مرتبط با استریم رویداد خطا (احتمالاً در backend/app/api/routes/chat.py یا backend/app/services/deep_analysis_service.py) است. تغییرات شامل محدود کردن طول پیام خطا به 500 کاراکتر و افزودن try/except برای جلوگیری از شکست استریم است. خارج از scope: تغییرات در سایر بخش‌های کد، تست‌ها، یا مستندات.
**Excerpt:**
```
## 💡 نمونه‌های قبل/بعد
**ایمن‌سازی ارسال رویداد خطا**

_قبل:_
```
yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

_بعد:_
```
try:
    yield f"event: error\ndata: {json.dumps({'error': str(e)[:500]})}\n\n"
except Exception:
    yield "event: error\ndata: {\"error\": \"internal stream error\"}\n\n"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.
```

### Step 39: اجرای تست‌های موجود پیش از merge برای جلوگیری از رگرشن
**Status:** `pending` (0%)
**Scope:** این بخش شامل اجرای تمام تست‌های موجود در پروژه (unit, integration, e2e) پیش از انجام merge است. هدف اطمینان از عدم ایجاد رگرشن (regression) در کد موجود است. هیچ تغییری در کد یا تست‌ها در این مرحله انجام نمی‌شود. این یک مرحله QA/اعتبارسنجی است و نه توسعه.
**Excerpt:**
```
## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)
```
