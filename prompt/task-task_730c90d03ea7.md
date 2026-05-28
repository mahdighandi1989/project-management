---
task_id: task_730c90d03ea7
title: 'تلفیق: mechanical:files (2 تسک)'
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:26:38.825617+00:00'
updated_at: '2026-05-20T04:28:31.320741+00:00'
tags:
- consolidated
- post_verify_merge
---

# تلفیق: mechanical:files (2 تسک)

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): اشتراک فایل با Jaccard ≥ 0.5
🎯 theme: mechanical:files
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 149fda5d-2295-405e-96f3-ebc31c6faa1a
  عنوان اصلی: CORS middleware با Allow-Origin wildcard در production
  اولویت اصلی: critical
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/main.py

📋 acceptance_criteria کامل:
  - CORS middleware از settings.CORS_ORIGINS استفاده می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["allow_origins\\s*=\\s*settings\\.CORS_ORIGINS", "CORS_ORIGINS"], "files_hint": ["backend/app/main.py"]}]
  - هدر Access-Control-Allow-Origin دستی در analysis.py حذف شده [verify_method=static] [verify_plan={"grep_patterns": ["Access-Control-Allow-Origin"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - درخواست‌های cross-origin از دامنه‌های غیرمجاز blocked می‌شوند [verify_method=api_response] [verify_plan={"method": "OPTIONS", "path": "/api/analysis/stream", "headers": {"Origin": "https://evil.com"}, "json_body": null, "expected_status": 403, "required_fields": [], "json_contains": null}]

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
CORS middleware با Allow-Origin wildcard در production

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:7-8` — `CORSMiddleware` — allow_origins باید از settings.CORS_ORIGINS خوانده شود
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  ...
  app.add_middleware(
      CORSMiddleware,
      allow_origins=['*'],
  ```
- `backend/app/api/routes/analysis.py:265-266` — `Access-Control-Allow-Origin` — هدر دستی که CORS middleware را دور می‌زند
  ```python
  "Access-Control-Allow-Origin": "*"
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + CORS middleware + SSE streaming

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/config.py` (سطر 40) — settings.CORS_ORIGINS در این فایل تعریف شده
- `backend/app/api/routes/settings.py` (سطر 283) — endpoint /settings/config مقدار CORS_ORIGINS را برمی‌گرداند
- `backend/app/core/database.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/__init__.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/debate.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/orchestrator.py` — این فایل `main.py` را import می‌کند (caller)
- `backend/app/services/project_analyzer.py` — `analysis.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
CORS middleware در main.py روی همه routeها اعمال می‌شود. analysis.py یک route خاص است که هدر را override می‌کند.

## 🔍 Context و وضعیت فعلی
در backend/app/main.py، CORS middleware با allow_origins=['*'] پیکربندی شده است. این تنظیم در محیط production به مهاجمان اجازه می‌دهد درخواست‌های cross-origin به API ارسال کنند و داده‌های حساس را بدزدند. همچنین هدر Access-Control-Allow-Origin: * در endpoint استریم analysis (analysis.py خط 266) به صورت دستی ست شده که این vulnerability را تشدید می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] CORS middleware از settings.CORS_ORIGINS استفاده می‌کند
- [ ] هدر Access-Control-Allow-Origin دستی در analysis.py حذف شده
- [ ] درخواست‌های cross-origin از دامنه‌های غیرمجاز blocked می‌شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. CORS origins را به لیست سفید دامنه‌های مجاز محدود کن. از متغیر محیطی CORS_ORIGINS استفاده کن که در config.py تعریف شده. هدر دستی Access-Control-Allow-Origin را از analysis.py حذف کن چون CORS middleware این کار را انجام می‌دهد.

## 💡 نمونه‌های قبل/بعد
**اصلاح CORS origins**

_قبل:_
```
allow_origins=['*']
```

_بعد:_
```
allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ['*']
```

**حذف هدر دستی**

_قبل:_
```
"Access-Control-Allow-Origin": "*"
```

_بعد:_
```
// حذف شود — CORS middleware مدیریت می‌کند
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -H 'Origin: https://evil.com' -I http://localhost:8000/api/analysis/reports | grep -i 'access-control'`
- `grep -rn 'Access-Control-Allow-Origin.*\*' backend/app/`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر CORS ممکن است frontendهای legit را در محیط dev موقتاً قطع کند

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
تسک 2 از 2
  id: c7771dde-ebe7-4015-881f-bcd260a6a438
  عنوان اصلی: عدم وجود Rate Limiting در تمامی API Endpoints
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/main.py

📋 acceptance_criteria کامل:
  - ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/analysis/reports", "headers": null, "json_body": null, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run-stream", "headers": null, "json_body": null, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - هدرهای Retry-After در پاسخ 429 وجود داشته باشد [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/analysis/reports", "headers": null, "json_body": null, "expected_status": 429, "required_fields": ["Retry-After"], "json_contains": null}]
  - تنظیمات rate limit از طریق متغیر محیطی یا دیتابیس قابل تغییر باشد [verify_method=static] [verify_plan={"grep_patterns": ["RATE_LIMIT", "os\\.getenv\\(\"RATE_LIMIT", "settings\\.RATE_LIMIT"], "files_hint": ["backend/app/main.py", "backend/app/config.py"]}]

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
عدم وجود Rate Limiting در تمامی API Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:1-712` — `app = FastAPI(...)` — تنها middleware فعال CORS است؛ هیچ rate limiter یا throttling وجود ندارد
  ```python
  app = FastAPI(
      title=settings.APP_NAME,
      version=settings.APP_VERSION,
      lifespan=lifespan
  )
  
  # CORS middleware — تنها middleware موجود
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ORIGINS,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Uvicorn + Python 3.11

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 83) — endpoint /analysis/run-stream که مدل‌های AI را فراخوانی می‌کند و هزینه‌بر است
- `backend/app/api/routes/github_import.py` (سطر 94) — endpoint /github/import که درخواست‌های خارجی به GitHub API می‌زند
- `backend/app/api/routes/oversight.py` (سطر 192) — endpoint /oversight/scan که اسکن عمیق پروژه را اجرا می‌کند
- `backend/app/core/config.py` — `main.py` این فایل را import می‌کند
- `backend/app/core/database.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/__init__.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/debate.py` — `main.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این مشکل تمام روترهای API را تحت تأثیر قرار می‌دهد. فایل main.py نقطه مرکزی برای افزودن middleware است.

## 🔍 Context و وضعیت فعلی
هیچ‌کدام از روترهای API (analysis, github_import, oversight, project_health, settings و غیره) از مکانیزم rate limiting استفاده نمی‌کنند. این موضوع امکان حملات brute-force، DoS و abuse از طریق فراخوانی مکرر endpoint‌های پرهزینه (مانند /analysis/run-stream که مستقیماً مدل‌های AI را فراخوانی می‌کند) را فراهم می‌کند. فایل backend/app/main.py هیچ middleware یا dependencyای برای محدودسازی نرخ درخواست ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود
- [ ] ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود
- [ ] هدرهای Retry-After در پاسخ 429 وجود داشته باشد
- [ ] تنظیمات rate limit از طریق متغیر محیطی یا دیتابیس قابل تغییر باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware سراسری rate limiting با استفاده از کتابخانه‌ای مانند slowapi یا aioredis-based rate limiter. برای endpoint‌های حساس (تحلیل، تولید محتوا با AI، import گیت‌هاب) محدودیت سخت‌گیرانه‌تر (مثلاً ۵ درخواست در دقیقه) و برای endpoint‌های خواندنی محدودیت ملایم‌تر (مثلاً ۶۰ درخواست در دقیقه) اعمال شود.

## 💡 نمونه‌های قبل/بعد
**افزودن Rate Limiter Middleware**

_قبل:_
```
app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```

_بعد:_
```
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `for i in $(seq 1 11); do curl -s -o /dev/null`

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
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 149fda5d-2295-405e-96f3-ebc31c6faa1a, c7771dde-ebe7-4015-881f-bcd260a6a438`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): اشتراک فایل با Jaccard ≥ 0.5
🎯 theme: mechanical:files
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 149fda5d-2295-405e-96f3-ebc31c6faa1a
  عنوان اصلی: CORS middleware با Allow-Origin wildcard در production
  اولویت اصلی: critical
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/analysis.py, backend/app/main.py

📋 acceptance_criteria کامل:
  - CORS middleware از settings.CORS_ORIGINS استفاده می‌کند [verify_method=static] [verify_plan={"grep_patterns": ["allow_origins\\s*=\\s*settings\\.CORS_ORIGINS", "CORS_ORIGINS"], "files_hint": ["backend/app/main.py"]}]
  - هدر Access-Control-Allow-Origin دستی در analysis.py حذف شده [verify_method=static] [verify_plan={"grep_patterns": ["Access-Control-Allow-Origin"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - درخواست‌های cross-origin از دامنه‌های غیرمجاز blocked می‌شوند [verify_method=api_response] [verify_plan={"method": "OPTIONS", "path": "/api/analysis/stream", "headers": {"Origin": "https://evil.com"}, "json_body": null, "expected_status": 403, "required_fields": [], "json_contains": null}]

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
CORS middleware با Allow-Origin wildcard در production

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:7-8` — `CORSMiddleware` — allow_origins باید از settings.CORS_ORIGINS خوانده شود
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  ...
  app.add_middleware(
      CORSMiddleware,
      allow_origins=['*'],
  ```
- `backend/app/api/routes/analysis.py:265-266` — `Access-Control-Allow-Origin` — هدر دستی که CORS middleware را دور می‌زند
  ```python
  "Access-Control-Allow-Origin": "*"
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + CORS middleware + SSE streaming

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/config.py` (سطر 40) — settings.CORS_ORIGINS در این فایل تعریف شده
- `backend/app/api/routes/settings.py` (سطر 283) — endpoint /settings/config مقدار CORS_ORIGINS را برمی‌گرداند
- `backend/app/core/database.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/__init__.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/debate.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/orchestrator.py` — این فایل `main.py` را import می‌کند (caller)
- `backend/app/services/project_analyzer.py` — `analysis.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
CORS middleware در main.py روی همه routeها اعمال می‌شود. analysis.py یک route خاص است که هدر را override می‌کند.

## 🔍 Context و وضعیت فعلی
در backend/app/main.py، CORS middleware با allow_origins=['*'] پیکربندی شده است. این تنظیم در محیط production به مهاجمان اجازه می‌دهد درخواست‌های cross-origin به API ارسال کنند و داده‌های حساس را بدزدند. همچنین هدر Access-Control-Allow-Origin: * در endpoint استریم analysis (analysis.py خط 266) به صورت دستی ست شده که این vulnerability را تشدید می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] CORS middleware از settings.CORS_ORIGINS استفاده می‌کند
- [ ] هدر Access-Control-Allow-Origin دستی در analysis.py حذف شده
- [ ] درخواست‌های cross-origin از دامنه‌های غیرمجاز blocked می‌شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. CORS origins را به لیست سفید دامنه‌های مجاز محدود کن. از متغیر محیطی CORS_ORIGINS استفاده کن که در config.py تعریف شده. هدر دستی Access-Control-Allow-Origin را از analysis.py حذف کن چون CORS middleware این کار را انجام می‌دهد.

## 💡 نمونه‌های قبل/بعد
**اصلاح CORS origins**

_قبل:_
```
allow_origins=['*']
```

_بعد:_
```
allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ['*']
```

**حذف هدر دستی**

_قبل:_
```
"Access-Control-Allow-Origin": "*"
```

_بعد:_
```
// حذف شود — CORS middleware مدیریت می‌کند
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `curl -H 'Origin: https://evil.com' -I http://localhost:8000/api/analysis/reports | grep -i 'access-control'`
- `grep -rn 'Access-Control-Allow-Origin.*\*' backend/app/`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر CORS ممکن است frontendهای legit را در محیط dev موقتاً قطع کند

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
تسک 2 از 2
  id: c7771dde-ebe7-4015-881f-bcd260a6a438
  عنوان اصلی: عدم وجود Rate Limiting در تمامی API Endpoints
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/main.py

📋 acceptance_criteria کامل:
  - ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/analysis/reports", "headers": null, "json_body": null, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود [verify_method=api_response] [verify_plan={"method": "POST", "path": "/api/analysis/run-stream", "headers": null, "json_body": null, "expected_status": 429, "required_fields": [], "json_contains": null}]
  - هدرهای Retry-After در پاسخ 429 وجود داشته باشد [verify_method=api_response] [verify_plan={"method": "GET", "path": "/api/analysis/reports", "headers": null, "json_body": null, "expected_status": 429, "required_fields": ["Retry-After"], "json_contains": null}]
  - تنظیمات rate limit از طریق متغیر محیطی یا دیتابیس قابل تغییر باشد [verify_method=static] [verify_plan={"grep_patterns": ["RATE_LIMIT", "os\\.getenv\\(\"RATE_LIMIT", "settings\\.RATE_LIMIT"], "files_hint": ["backend/app/main.py", "backend/app/config.py"]}]

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
عدم وجود Rate Limiting در تمامی API Endpoints

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:1-712` — `app = FastAPI(...)` — تنها middleware فعال CORS است؛ هیچ rate limiter یا throttling وجود ندارد
  ```python
  app = FastAPI(
      title=settings.APP_NAME,
      version=settings.APP_VERSION,
      lifespan=lifespan
  )
  
  # CORS middleware — تنها middleware موجود
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ORIGINS,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + Uvicorn + Python 3.11

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/analysis.py` (سطر 83) — endpoint /analysis/run-stream که مدل‌های AI را فراخوانی می‌کند و هزینه‌بر است
- `backend/app/api/routes/github_import.py` (سطر 94) — endpoint /github/import که درخواست‌های خارجی به GitHub API می‌زند
- `backend/app/api/routes/oversight.py` (سطر 192) — endpoint /oversight/scan که اسکن عمیق پروژه را اجرا می‌کند
- `backend/app/core/config.py` — `main.py` این فایل را import می‌کند
- `backend/app/core/database.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/__init__.py` — `main.py` این فایل را import می‌کند
- `backend/app/api/routes/debate.py` — `main.py` این فایل را import می‌کند

## 🌐 نقشهٔ وابستگی‌ها
این مشکل تمام روترهای API را تحت تأثیر قرار می‌دهد. فایل main.py نقطه مرکزی برای افزودن middleware است.

## 🔍 Context و وضعیت فعلی
هیچ‌کدام از روترهای API (analysis, github_import, oversight, project_health, settings و غیره) از مکانیزم rate limiting استفاده نمی‌کنند. این موضوع امکان حملات brute-force، DoS و abuse از طریق فراخوانی مکرر endpoint‌های پرهزینه (مانند /analysis/run-stream که مستقیماً مدل‌های AI را فراخوانی می‌کند) را فراهم می‌کند. فایل backend/app/main.py هیچ middleware یا dependencyای برای محدودسازی نرخ درخواست ندارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود
- [ ] ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود
- [ ] هدرهای Retry-After در پاسخ 429 وجود داشته باشد
- [ ] تنظیمات rate limit از طریق متغیر محیطی یا دیتابیس قابل تغییر باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن middleware سراسری rate limiting با استفاده از کتابخانه‌ای مانند slowapi یا aioredis-based rate limiter. برای endpoint‌های حساس (تحلیل، تولید محتوا با AI، import گیت‌هاب) محدودیت سخت‌گیرانه‌تر (مثلاً ۵ درخواست در دقیقه) و برای endpoint‌های خواندنی محدودیت ملایم‌تر (مثلاً ۶۰ درخواست در دقیقه) اعمال شود.

## 💡 نمونه‌های قبل/بعد
**افزودن Rate Limiter Middleware**

_قبل:_
```
app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```

_بعد:_
```
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `for i in $(seq 1 11); do curl -s -o /dev/null`

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
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: 149fda5d-2295-405e-96f3-ebc31c6faa1a, c7771dde-ebe7-4015-881f-bcd260a6a438`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود _(verify: api_response)_
2. ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود _(verify: api_response)_
3. هدرهای Retry-After در پاسخ 429 وجود داشته باشد _(verify: api_response)_
4. تنظیمات rate limit از طریق متغیر محیطی یا دیتابیس قابل تغییر باشد _(verify: static)_
5. CORS middleware از settings.CORS_ORIGINS استفاده می‌کند _(verify: static)_
6. هدر Access-Control-Allow-Origin دستی در analysis.py حذف شده _(verify: static)_
7. درخواست‌های cross-origin از دامنه‌های غیرمجاز blocked می‌شوند _(verify: api_response)_

## Task Steps

### Step 1: بررسی و اصلاح CORS middleware در main.py برای استفاده از settings.CORS_ORIGINS
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی فایل backend/app/main.py برای یافتن پیکربندی فعلی CORS middleware و اصلاح آن است. باید اطمینان حاصل شود که allow_origins از settings.CORS_ORIGINS خوانده می‌شود نه از wildcard '*'. اگر قبلاً از settings.CORS_ORIGINS استفاده می‌کند، نیازی به تغییر نیست. خارج از این مرحله: حذف هدر دستی در analysis.py، افزودن rate limiting، یا تغییر در config.py.
**Excerpt:**
```
- `backend/app/main.py:7-8` — `CORSMiddleware` — allow_origins باید از settings.CORS_ORIGINS خوانده شود
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  ...
  app.add_middleware(
      CORSMiddleware,
      allow_origins=['*'],
  ```
- `backend/app/core/config.py` (سطر 40) — settings.CORS_ORIGINS در این فایل تعریف شده

**اصلاح CORS origins**
_قبل:_
```
allow_origins=['*']
```
_بعد:_
```
allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ['*']
```
```

### Step 2: حذف هدر دستی Access-Control-Allow-Origin از analysis.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل یافتن و حذف هدر دستی `Access-Control-Allow-Origin: *` در فایل backend/app/api/routes/analysis.py است. CORS middleware این هدر را مدیریت می‌کند و وجود دستی آن vulnerability ایجاد می‌کند. خارج از این مرحله: تغییر CORS middleware در main.py، افزودن rate limiting، یا تغییر در سایر فایل‌ها.
**Excerpt:**
```
- `backend/app/api/routes/analysis.py:265-266` — `Access-Control-Allow-Origin` — هدر دستی که CORS middleware را دور می‌زند
  ```python
  "Access-Control-Allow-Origin": "*"
  ```

**حذف هدر دستی**
_قبل:_
```
"Access-Control-Allow-Origin": "*"
```
_بعد:_
```
// حذف شود — CORS middleware مدیریت می‌کند
```
```

### Step 3: بررسی و نصب کتابخانه rate limiting (slowapi) در پروژه
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی فایل requirements.txt یا pyproject.toml برای وجود کتابخانه slowapi (یا معادل آن) و نصب آن در صورت نیاز است. اگر slowapi از قبل نصب است، نیازی به تغییر نیست. خارج از این مرحله: پیکربندی middleware، تنظیم محدودیت‌ها، یا نوشتن تست.
**Excerpt:**
```
1. افزودن middleware سراسری rate limiting با استفاده از کتابخانه‌ای مانند slowapi یا aioredis-based rate limiter.

**افزودن Rate Limiter Middleware**
_قبل:_
```
app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```
_بعد:_
```
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```
```

### Step 4: افزودن تنظیمات rate limit به config.py (متغیر محیطی)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن متغیرهای محیطی برای rate limiting در فایل backend/app/core/config.py است. باید متغیرهایی مانند RATE_LIMIT_GLOBAL (محدودیت پیش‌فرض) و RATE_LIMIT_SENSITIVE (محدودیت برای endpoint‌های حساس) تعریف شود. خارج از این مرحله: پیکربندی middleware در main.py یا نوشتن تست.
**Excerpt:**
```
- تنظیمات rate limit از طریق متغیر محیطی یا دیتابیس قابل تغییر باشد [verify_method=static] [verify_plan={"grep_patterns": ["RATE_LIMIT", "os\.getenv\(\"RATE_LIMIT", "settings\.RATE_LIMIT"], "files_hint": ["backend/app/main.py", "backend/app/config.py"]}]

- `backend/app/core/config.py` — `main.py` این فایل را import می‌کند
```

### Step 5: افزودن middleware سراسری rate limiting در main.py با slowapi
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن middleware rate limiting در فایل backend/app/main.py با استفاده از slowapi است. باید Limiter با key_func=get_remote_address ایجاد شود، به app.state.limiter اختصاص یابد، و exception handler برای status 429 اضافه شود. خارج از این مرحله: تنظیم محدودیت‌های خاص برای هر endpoint (در مرحله بعدی انجام می‌شود).
**Excerpt:**
```
1. افزودن middleware سراسری rate limiting با استفاده از کتابخانه‌ای مانند slowapi یا aioredis-based rate limiter.

**افزودن Rate Limiter Middleware**
_قبل:_
```
app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```
_بعد:_
```
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(CORSMiddleware, ...)

# include routers
app.include_router(debate.router)
```
```

### Step 6: اعمال محدودیت rate limit خاص برای endpoint‌های حساس (analysis/run-stream و analysis/reports)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اعمال محدودیت‌های خاص برای endpoint‌های حساس با استفاده از دکوراتور @limiter.limit است. برای /api/analysis/reports محدودیت ۱۰ درخواست در دقیقه و برای /api/analysis/run-stream محدودیت ۵ درخواست در دقیقه اعمال می‌شود. خارج از این مرحله: اعمال محدودیت برای سایر endpoint‌ها (github_import, oversight) یا نوشتن تست.
**Excerpt:**
```
- ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود [verify_method=api_response]
- ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود [verify_method=api_response]
- هدرهای Retry-After در پاسخ 429 وجود داشته باشد [verify_method=api_response]

برای endpoint‌های حساس (تحلیل، تولید محتوا با AI، import گیت‌هاب) محدودیت سخت‌گیرانه‌تر (مثلاً ۵ درخواست در دقیقه) و برای endpoint‌های خواندنی محدودیت ملایم‌تر (مثلاً ۶۰ درخواست در دقیقه) اعمال شود.
```

### Step 7: اعمال محدودیت rate limit برای endpoint‌های github_import و oversight
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اعمال محدودیت rate limit برای endpoint‌های /api/github/import و /api/oversight/scan با محدودیت ۵ درخواست در دقیقه (مشابه endpoint‌های حساس) است. خارج از این مرحله: اعمال محدودیت برای endpoint‌های خواندنی عمومی یا نوشتن تست.
**Excerpt:**
```
- `backend/app/api/routes/github_import.py` (سطر 94) — endpoint /github/import که درخواست‌های خارجی به GitHub API می‌زند
- `backend/app/api/routes/oversight.py` (سطر 192) — endpoint /oversight/scan که اسکن عمیق پروژه را اجرا می‌کند

برای endpoint‌های حساس (تحلیل، تولید محتوا با AI، import گیت‌هاب) محدودیت سخت‌گیرانه‌تر (مثلاً ۵ درخواست در دقیقه)
```

### Step 8: اجرای تست‌های موجود و اطمینان از عدم شکست آن‌ها
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های موجود پروژه (pytest) پس از اعمال تغییرات است. باید اطمینان حاصل شود که هیچ تستی fail نمی‌شود. اگر تست‌ها fail شدند، باید رفع شوند. خارج از این مرحله: نوشتن تست‌های جدید برای rate limiting.
**Excerpt:**
```
- هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- linter بدون warning عبور می‌کند
- type-check موفق است (`tsc --noEmit` / `mypy`)
```

### Step 9: نوشتن تست‌های rate limiting برای endpoint‌های حساس
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های خودکار برای بررسی عملکرد rate limiting است. تست‌ها باید شامل ارسال درخواست‌های متوالی به endpoint‌های /api/analysis/reports و /api/analysis/run-stream و بررسی status 429 و هدر Retry-After باشند. خارج از این مرحله: تست‌های integration یا end-to-end.
**Excerpt:**
```
- ارسال ۱۱ درخواست متوالی به /api/analysis/reports در ۱ دقیقه، دهمین درخواست با status 429 رد شود [verify_method=api_response]
- ارسال ۶ درخواست به /api/analysis/run-stream در ۱ دقیقه، ششمین درخواست با status 429 رد شود [verify_method=api_response]
- هدرهای Retry-After در پاسخ 429 وجود داشته باشد [verify_method=api_response]
```
