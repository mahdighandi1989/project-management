---
task_id: task_e16d3af7f6e3
title: 'رفع anti-patternها: تزریق وابستگی session دیتابیس و بهبود معماری پروژه'
type: other
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:24:59.539905+00:00'
updated_at: '2026-05-29T20:23:40.677044+00:00'
tags:
- consolidated
- post_verify_merge
---

# رفع anti-patternها: تزریق وابستگی session دیتابیس و بهبود معماری پروژه

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک 20 به anti-pattern در مدیریت session دیتابیس مربوط می‌شود و تسک 33 نیز یک anti-pattern دیگر (under-engineering) را نشان می‌دهد. هر دو به بهبود کیفیت کد و معماری مربوط هستند.
🎯 theme: رفع anti-pattern در مدیریت session دیتابیس
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 6cdc6e7f-bee3-4a0a-a8f1-c801347cddf5
  عنوان اصلی: Session management anti-pattern: direct SessionLocal() calls without dependency injection in multiple route files
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - Zero direct SessionLocal() calls in route files (except background tasks) [verify_method=static] [verify_plan={"grep_patterns": ["SessionLocal()"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/github_import.py"]}]
  - All CRUD endpoints use Depends(get_db) [verify_method=static] [verify_plan={"grep_patterns": ["Depends\\(get_db\\)"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/github_import.py"]}]
  - Background tasks use a context-manager based session [verify_method=static] [verify_plan={"grep_patterns": ["with SessionLocal\\(\\) as session", "context_manager"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/gi]
  - Existing tests pass without modification [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]

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
Session management anti-pattern: direct SessionLocal() calls without dependency injection in multiple route files

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:117-124` — `run_analysis_task` — Direct SessionLocal() inside a nested async function — no DI, no proper cleanup on exception
  ```python
  from ...core.database import SessionLocal
  analysis_db = SessionLocal()
  
  deep_analyzer = DeepAnalysisService(
      ai_manager=ai_manager,
      progress_callback=progress_callback,
      db_session=analysis_db
  )
  ```
- `backend/app/api/routes/analysis.py:280-290` — `get_analysis_reports` — Manual session management instead of Depends(get_db)
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:299-306` — `get_analysis_report` — Same pattern repeated — 5 occurrences in this file alone
  ```python
  db = SessionLocal()
  try:
      report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
      ...
  finally:
      db.close()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + SQLite. FastAPI's Depends system is designed for proper session lifecycle management.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/project_health.py` (سطر 1) — Same anti-pattern with direct SessionLocal() calls
- `backend/app/api/routes/github_import.py` (سطر 137) — Uses SessionLocal() at lines 137-155 for auto_setup
- `backend/app/core/database.py` (سطر 1) — Defines get_db dependency that should be used everywhere
- `backend/app/services/project_analyzer.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/services/model_profiler.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/models/analysis_report.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/models/ai_profile.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `analysis.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
Affects 3+ route files with ~10+ direct SessionLocal() calls. The get_db dependency exists in database.py but is inconsistently used. This pattern prevents proper session mocking in tests and risks connection leaks.

## 🔍 Context و وضعیت فعلی
Multiple route files (analysis.py, project_health.py, github_import.py) create database sessions using `SessionLocal()` directly instead of using FastAPI's `Depends(get_db)` dependency injection. This pattern bypasses the DI system, making it impossible to mock sessions in tests, causing potential connection leaks when exceptions occur before `finally` blocks, and violating FastAPI best practices. The `analysis.py` file at lines 117, 280, 299, 315, 349 creates sessions manually. `project_health.py` has similar issues. This is a systemic architectural problem affecting testability and reliability.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] Zero direct SessionLocal() calls in route files (except background tasks)
- [ ] All CRUD endpoints use Depends(get_db)
- [ ] Background tasks use a context-manager based session
- [ ] Existing tests pass without modification
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. Replace all direct `SessionLocal()` calls with FastAPI `Depends(get_db)` injection. For background tasks that need sessions, create a dedicated `get_db_contextmanager` that can be used with `async with`. For the streaming endpoint in analysis.py, pass the db session through the service constructor or use a context variable.

## 💡 نمونه‌های قبل/بعد
**Replace direct SessionLocal with Depends**

_قبل:_
```
db = SessionLocal()
try:
    result = db.query(...)
finally:
    db.close()
```

_بعد:_
```
@router.get("/reports")
async def get_reports(db: Session = Depends(get_db)):
    return db.query(...).all()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/api/routes/ --include='*.py' | wc -l`
- `pytest backend/tests/ -x -v`

## ⚠️ ریسک‌ها و موارد احتیاط
Low risk if done carefully — the get_db dependency already exists and

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - Refactor `analysis.py` to use FastAPI `Depends(get_db)` for all database sessions — جایگزینی SessionLocal() در analysis.py خطوط 117، 280، 299، 315، 349 با Depends(get_db)
  - Refactor `project_health.py` to use FastAPI `Depends(get_db)` for all database sessions — جایگزینی SessionLocal() در project_health.py با Depends(get_db)
  - Refactor `github_import.py` to use FastAPI `Depends(get_db)` for all database sessions — جایگزینی SessionLocal() در github_import.py با Depends(get_db)
  - Verify no remaining direct `SessionLocal()` calls exist in any route files — بررسی و حذف تمام SessionLocal()های باقی‌مانده در route files

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: b07e4d11-0d5f-4c32-b5a1-bf420415aab8
  عنوان اصلی: Anti-pattern: Under-engineering
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/models/project.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["technologies", "features", "structure", "extra_data", "memory_instructions", "dynamic_fields"], "files_hint": ["backend/app/models/project.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["class Project", "Text", "JSONString", "json.dumps", "json.loads"], "files_hint": ["backend/app/models/project.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_project.py::test_edge_case", "timeout_seconds": 60}]

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
Anti-pattern: Under-engineering

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/models/project.py:35`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/github_import.py` — این فایل `project.py` را import می‌کند (caller)
- `backend/app/api/routes/models.py` — این فایل `project.py` را import می‌کند (caller)
- `backend/app/api/routes/project_health.py` — این فایل `project.py` را import می‌کند (caller)
- `backend/app/api/routes/project_journal.py` — این فایل `project.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
فیلدهای technologies, features, structure, extra_data, memory_instructions, dynamic_fields همگی به صورت Text (JSON string) ذخیره می‌شوند. این فیلدها ساختارهای داده‌ای با روابط مشخص دارند (مثلاً dynamic_fields شامل target_models است که به مدل‌های AI اشاره دارد). عدم استفاده از جداول مجزا یا JSONB (در صورت استفاده از PostgreSQL) باعث از دست رفتن قابلیت‌های query, index, validation و referential inte

📁 file: backend/app/models/project.py (line 35)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/models/project.py`
- `ruff check backend/app/models/project.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: medium
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
- در commit message: `merged-from: 6cdc6e7f-bee3-4a0a-a8f1-c801347cddf5, b07e4d11-0d5f-4c32-b5a1-bf420415aab8`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک 20 به anti-pattern در مدیریت session دیتابیس مربوط می‌شود و تسک 33 نیز یک anti-pattern دیگر (under-engineering) را نشان می‌دهد. هر دو به بهبود کیفیت کد و معماری مربوط هستند.
🎯 theme: رفع anti-pattern در مدیریت session دیتابیس
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 6cdc6e7f-bee3-4a0a-a8f1-c801347cddf5
  عنوان اصلی: Session management anti-pattern: direct SessionLocal() calls without dependency injection in multiple route files
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - Zero direct SessionLocal() calls in route files (except background tasks) [verify_method=static] [verify_plan={"grep_patterns": ["SessionLocal()"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/github_import.py"]}]
  - All CRUD endpoints use Depends(get_db) [verify_method=static] [verify_plan={"grep_patterns": ["Depends\\(get_db\\)"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/github_import.py"]}]
  - Background tasks use a context-manager based session [verify_method=static] [verify_plan={"grep_patterns": ["with SessionLocal\\(\\) as session", "context_manager"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/gi]
  - Existing tests pass without modification [verify_method=backend_test] [verify_plan={"test_node": "tests/", "timeout_seconds": 120}]

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
Session management anti-pattern: direct SessionLocal() calls without dependency injection in multiple route files

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:117-124` — `run_analysis_task` — Direct SessionLocal() inside a nested async function — no DI, no proper cleanup on exception
  ```python
  from ...core.database import SessionLocal
  analysis_db = SessionLocal()
  
  deep_analyzer = DeepAnalysisService(
      ai_manager=ai_manager,
      progress_callback=progress_callback,
      db_session=analysis_db
  )
  ```
- `backend/app/api/routes/analysis.py:280-290` — `get_analysis_reports` — Manual session management instead of Depends(get_db)
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:299-306` — `get_analysis_report` — Same pattern repeated — 5 occurrences in this file alone
  ```python
  db = SessionLocal()
  try:
      report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
      ...
  finally:
      db.close()
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + SQLite. FastAPI's Depends system is designed for proper session lifecycle management.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/project_health.py` (سطر 1) — Same anti-pattern with direct SessionLocal() calls
- `backend/app/api/routes/github_import.py` (سطر 137) — Uses SessionLocal() at lines 137-155 for auto_setup
- `backend/app/core/database.py` (سطر 1) — Defines get_db dependency that should be used everywhere
- `backend/app/services/project_analyzer.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/services/model_profiler.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/models/analysis_report.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/models/ai_profile.py` — `analysis.py` این فایل را import می‌کند
- `backend/app/main.py` — این فایل `analysis.py` را import می‌کند (caller)

## 🌐 نقشهٔ وابستگی‌ها
Affects 3+ route files with ~10+ direct SessionLocal() calls. The get_db dependency exists in database.py but is inconsistently used. This pattern prevents proper session mocking in tests and risks connection leaks.

## 🔍 Context و وضعیت فعلی
Multiple route files (analysis.py, project_health.py, github_import.py) create database sessions using `SessionLocal()` directly instead of using FastAPI's `Depends(get_db)` dependency injection. This pattern bypasses the DI system, making it impossible to mock sessions in tests, causing potential connection leaks when exceptions occur before `finally` blocks, and violating FastAPI best practices. The `analysis.py` file at lines 117, 280, 299, 315, 349 creates sessions manually. `project_health.py` has similar issues. This is a systemic architectural problem affecting testability and reliability.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] Zero direct SessionLocal() calls in route files (except background tasks)
- [ ] All CRUD endpoints use Depends(get_db)
- [ ] Background tasks use a context-manager based session
- [ ] Existing tests pass without modification
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. Replace all direct `SessionLocal()` calls with FastAPI `Depends(get_db)` injection. For background tasks that need sessions, create a dedicated `get_db_contextmanager` that can be used with `async with`. For the streaming endpoint in analysis.py, pass the db session through the service constructor or use a context variable.

## 💡 نمونه‌های قبل/بعد
**Replace direct SessionLocal with Depends**

_قبل:_
```
db = SessionLocal()
try:
    result = db.query(...)
finally:
    db.close()
```

_بعد:_
```
@router.get("/reports")
async def get_reports(db: Session = Depends(get_db)):
    return db.query(...).all()
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `grep -rn 'SessionLocal()' backend/app/api/routes/ --include='*.py' | wc -l`
- `pytest backend/tests/ -x -v`

## ⚠️ ریسک‌ها و موارد احتیاط
Low risk if done carefully — the get_db dependency already exists and

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  - Refactor `analysis.py` to use FastAPI `Depends(get_db)` for all database sessions — جایگزینی SessionLocal() در analysis.py خطوط 117، 280، 299، 315، 349 با Depends(get_db)
  - Refactor `project_health.py` to use FastAPI `Depends(get_db)` for all database sessions — جایگزینی SessionLocal() در project_health.py با Depends(get_db)
  - Refactor `github_import.py` to use FastAPI `Depends(get_db)` for all database sessions — جایگزینی SessionLocal() در github_import.py با Depends(get_db)
  - Verify no remaining direct `SessionLocal()` calls exist in any route files — بررسی و حذف تمام SessionLocal()های باقی‌مانده در route files

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: b07e4d11-0d5f-4c32-b5a1-bf420415aab8
  عنوان اصلی: Anti-pattern: Under-engineering
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/models/project.py

📋 acceptance_criteria کامل:
  - ریشه anti-pattern تشخیص داده شد [verify_method=static] [verify_plan={"grep_patterns": ["technologies", "features", "structure", "extra_data", "memory_instructions", "dynamic_fields"], "files_hint": ["backend/app/models/project.py"]}]
  - یا کد اصلاح شد، یا کامنت توجیهی اضافه شد [verify_method=static] [verify_plan={"grep_patterns": ["class Project", "Text", "JSONString", "json.dumps", "json.loads"], "files_hint": ["backend/app/models/project.py"]}]
  - تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_project.py::test_edge_case", "timeout_seconds": 60}]

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
Anti-pattern: Under-engineering

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/models/project.py:35`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/github_import.py` — این فایل `project.py` را import می‌کند (caller)
- `backend/app/api/routes/models.py` — این فایل `project.py` را import می‌کند (caller)
- `backend/app/api/routes/project_health.py` — این فایل `project.py` را import می‌کند (caller)
- `backend/app/api/routes/project_journal.py` — این فایل `project.py` را import می‌کند (caller)

## 🔍 Context و وضعیت فعلی
فیلدهای technologies, features, structure, extra_data, memory_instructions, dynamic_fields همگی به صورت Text (JSON string) ذخیره می‌شوند. این فیلدها ساختارهای داده‌ای با روابط مشخص دارند (مثلاً dynamic_fields شامل target_models است که به مدل‌های AI اشاره دارد). عدم استفاده از جداول مجزا یا JSONB (در صورت استفاده از PostgreSQL) باعث از دست رفتن قابلیت‌های query, index, validation و referential inte

📁 file: backend/app/models/project.py (line 35)

🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] ریشه anti-pattern تشخیص داده شد
- [ ] یا کد اصلاح شد، یا کامنت توجیهی اضافه شد
- [ ] تست edge case نوشته شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/models/project.py`
- `ruff check backend/app/models/project.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: bug_fix
- اولویت: medium
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
- در commit message: `merged-from: 6cdc6e7f-bee3-4a0a-a8f1-c801347cddf5, b07e4d11-0d5f-4c32-b5a1-bf420415aab8`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. Zero direct SessionLocal() calls in route files (except background tasks) _(verify: static)_
2. All CRUD endpoints use Depends(get_db) _(verify: static)_
3. Background tasks use a context-manager based session _(verify: static)_
4. Existing tests pass without modification _(verify: backend_test)_
5. ریشه anti-pattern تشخیص داده شد _(verify: static)_
6. یا کد اصلاح شد، یا کامنت توجیهی اضافه شد _(verify: static)_
7. تست edge case نوشته شد _(verify: backend_test)_

## Task Steps

### Step 1: بررسی و مستندسازی وضعیت فعلی SessionLocal() در analysis.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل backend/app/api/routes/analysis.py برای یافتن تمام موارد استفاده از SessionLocal() است. باید خطوط 117، 280، 299، 315، 349 و هر خط دیگری که SessionLocal() را فراخوانی می‌کند شناسایی شود. همچنین باید بررسی شود که آیا قبلاً برخی از این موارد اصلاح شده‌اند یا خیر. خروجی این مرحله یک مستندسازی کامل از وضعیت فعلی است، نه تغییر کد.
**Excerpt:**
```
- `backend/app/api/routes/analysis.py:117-124` — `run_analysis_task` — Direct SessionLocal() inside a nested async function — no DI, no proper cleanup on exception
  ```python
  from ...core.database import SessionLocal
  analysis_db = SessionLocal()
  
  deep_analyzer = DeepAnalysisService(
      ai_manager=ai_manager,
      progress_callback=progress_callback,
      db_session=analysis_db
  )
  ```
- `backend/app/api/routes/analysis.py:280-290` — `get_analysis_reports` — Manual session management instead of Depends(get_db)
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
  finally:
      db.close()
  ```
- `backend/app/api/routes/analysis.py:299-306` — `get_analysis_report` — Same pattern repeated — 5 occurrences in this file alone
  ```python
  db = SessionLocal()
  try:
      report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
      ...
  finally:
      db.close()
  ```
```

### Step 2: بررسی و مستندسازی وضعیت فعلی SessionLocal() در project_health.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل backend/app/api/routes/project_health.py برای یافتن تمام موارد استفاده از SessionLocal() است. باید تمام خطوطی که SessionLocal() را فراخوانی می‌کنند شناسایی شود. همچنین باید بررسی شود که آیا قبلاً برخی از این موارد اصلاح شده‌اند یا خیر. خروجی این مرحله یک مستندسازی کامل از وضعیت فعلی است، نه تغییر کد.
**Excerpt:**
```
- `backend/app/api/routes/project_health.py` (سطر 1) — Same anti-pattern with direct SessionLocal() calls
```

### Step 3: بررسی و مستندسازی وضعیت فعلی SessionLocal() در github_import.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل backend/app/api/routes/github_import.py برای یافتن تمام موارد استفاده از SessionLocal() است. باید خطوط 137-155 و هر خط دیگری که SessionLocal() را فراخوانی می‌کند شناسایی شود. همچنین باید بررسی شود که آیا قبلاً برخی از این موارد اصلاح شده‌اند یا خیر. خروجی این مرحله یک مستندسازی کامل از وضعیت فعلی است، نه تغییر کد.
**Excerpt:**
```
- `backend/app/api/routes/github_import.py` (سطر 137) — Uses SessionLocal() at lines 137-155 for auto_setup
```

### Step 4: بررسی get_db و database.py برای اطمینان از وجود dependency injection صحیح
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی فایل backend/app/core/database.py برای اطمینان از وجود تابع get_db با پیاده‌سازی صحیح است. باید بررسی شود که get_db از SessionLocal استفاده می‌کند و yield می‌کند تا FastAPI بتواند lifecycle session را مدیریت کند. همچنین باید بررسی شود که SessionLocal چگونه تعریف شده است. اگر get_db وجود ندارد یا ناقص است، باید اصلاح شود.
**Excerpt:**
```
- `backend/app/core/database.py` (سطر 1) — Defines get_db dependency that should be used everywhere
```

### Step 5: ایجاد context manager برای session در background tasks
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک context manager (مثلاً get_db_contextmanager) در backend/app/core/database.py است که برای background tasks قابل استفاده باشد. این context manager باید session را ایجاد کند، yield کند، و در نهایت session را ببندد. این برای مواردی مانند run_analysis_task که در background اجرا می‌شوند ضروری است.
**Excerpt:**
```
Background tasks use a context-manager based session [verify_method=static] [verify_plan={"grep_patterns": ["with SessionLocal\(\) as session", "context_manager"], "files_hint": ["backend/app/api/routes/analysis.py", "backend/app/api/routes/project_health.py", "backend/app/api/routes/gi]
```

### Step 6: رفع SessionLocal() در run_analysis_task (analysis.py خط 117)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی SessionLocal() مستقیم در تابع run_analysis_task (analysis.py خط 117-124) با context manager جدید get_db_contextmanager است. این تابع یک background task است، بنابراین نمی‌تواند از Depends(get_db) استفاده کند. باید از get_db_contextmanager با 'with' استفاده شود. همچنین باید cleanup مناسب در صورت exception اضافه شود.
**Excerpt:**
```
- `backend/app/api/routes/analysis.py:117-124` — `run_analysis_task` — Direct SessionLocal() inside a nested async function — no DI, no proper cleanup on exception
  ```python
  from ...core.database import SessionLocal
  analysis_db = SessionLocal()
  
  deep_analyzer = DeepAnalysisService(
      ai_manager=ai_manager,
      progress_callback=progress_callback,
      db_session=analysis_db
  )
  ```
```

### Step 7: رفع SessionLocal() در get_analysis_reports (analysis.py خط 280)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی SessionLocal() مستقیم در تابع get_analysis_reports (analysis.py خط 280-290) با Depends(get_db) است. این یک endpoint عادی است، بنابراین می‌تواند از DI استفاده کند. باید امضای تابع تغییر کند تا db: Session = Depends(get_db) را بپذیرد.
**Excerpt:**
```
- `backend/app/api/routes/analysis.py:280-290` — `get_analysis_reports` — Manual session management instead of Depends(get_db)
  ```python
  db = SessionLocal()
  try:
      query = db.query(AnalysisReport)
      ...
  finally:
      db.close()
  ```
```

### Step 8: رفع SessionLocal() در get_analysis_report (analysis.py خط 299)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی SessionLocal() مستقیم در تابع get_analysis_report (analysis.py خط 299-306) با Depends(get_db) است. این یک endpoint عادی است. باید امضای تابع تغییر کند تا db: Session = Depends(get_db) را بپذیرد.
**Excerpt:**
```
- `backend/app/api/routes/analysis.py:299-306` — `get_analysis_report` — Same pattern repeated — 5 occurrences in this file alone
  ```python
  db = SessionLocal()
  try:
      report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
      ...
  finally:
      db.close()
  ```
```

### Step 9: رفع SessionLocal() در سایر endpoints analysis.py (خطوط 315 و 349)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی SessionLocal() مستقیم در سایر endpoints فایل analysis.py (خطوط 315 و 349) با Depends(get_db) است. باید تمام موارد باقی‌مانده در این فایل اصلاح شود.
**Excerpt:**
```
The `analysis.py` file at lines 117, 280, 299, 315, 349 creates sessions manually.
```

### Step 10: رفع SessionLocal() در project_health.py
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی تمام SessionLocal() مستقیم در فایل backend/app/api/routes/project_health.py با Depends(get_db) است. باید تمام endpoints اصلاح شوند. اگر background task وجود دارد، باید از get_db_contextmanager استفاده کند.
**Excerpt:**
```
- `backend/app/api/routes/project_health.py` (سطر 1) — Same anti-pattern with direct SessionLocal() calls
```

### Step 11: رفع SessionLocal() در github_import.py (خطوط 137-155)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل جایگزینی SessionLocal() مستقیم در فایل backend/app/api/routes/github_import.py (خطوط 137-155) با Depends(get_db) است. اگر این بخش یک background task است، باید از get_db_contextmanager استفاده کند. اگر endpoint عادی است، باید از Depends(get_db) استفاده کند.
**Excerpt:**
```
- `backend/app/api/routes/github_import.py` (سطر 137) — Uses SessionLocal() at lines 137-155 for auto_setup
```

### Step 12: بررسی نهایی و حذف تمام SessionLocal() باقی‌مانده در route files
**Status:** `pending` (0%)
**Scope:** این مرحله شامل یک بررسی جامع با grep برای یافتن هرگونه SessionLocal() باقی‌مانده در تمام فایل‌های backend/app/api/routes/ است. باید از دستور grep -rn 'SessionLocal()' backend/app/api/routes/ --include='*.py' استفاده شود. اگر SessionLocal() باقی‌مانده‌ای یافت شود، باید اصلاح شود.
**Excerpt:**
```
- `grep -rn 'SessionLocal()' backend/app/api/routes/ --include='*.py' | wc -l`
```

### Step 13: بررسی و مستندسازی وضعیت فعلی فیلدهای JSON در Project model
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل فایل backend/app/models/project.py برای شناسایی فیلدهایی است که به صورت Text (JSON string) ذخیره می‌شوند: technologies, features, structure, extra_data, memory_instructions, dynamic_fields. باید مشخص شود که آیا این فیلدها واقعاً anti-pattern هستند یا خیر، با توجه به محدودیت‌های SQLite که از JSONB پشتیبانی نمی‌کند. خروجی این مرحله یک مستندسازی کامل از وضعیت فعلی است.
**Excerpt:**
```
فیلدهای technologies, features, structure, extra_data, memory_instructions, dynamic_fields همگی به صورت Text (JSON string) ذخیره می‌شوند. این فیلدها ساختارهای داده‌ای با روابط مشخص دارند (مثلاً dynamic_fields شامل target_models است که به مدل‌های AI اشاره دارد). عدم استفاده از جداول مجزا یا JSONB (در صورت استفاده از PostgreSQL) باعث از دست رفتن قابلیت‌های query, index, validation و referential inte
```

### Step 14: تحلیل و تصمیم‌گیری درباره فیلدهای JSON در Project model
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تحلیل عمیق anti-pattern under-engineering در Project model است. با توجه به اینکه پروژه از SQLite استفاده می‌کند که از JSONB پشتیبانی نمی‌کند، و با توجه به اینکه جداول مجزا برای هر فیلد JSON پیچیدگی زیادی ایجاد می‌کند، باید تصمیم گرفته شود که آیا اصلاح لازم است یا خیر. اگر اصلاح لازم است، باید مشخص شود که چه رویکردی (JSON validator, Pydantic model, جدول مجزا) مناسب‌تر است. اگر اصلاح لازم نیست، باید کامنت توجیهی اضافه شود.
**Excerpt:**
```
🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند.
```

### Step 15: اضافه کردن validation و type hint برای فیلدهای JSON در Project model
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اضافه کردن validation و type hint برای فیلدهای JSON در Project model است. با توجه به محدودیت SQLite، بهترین رویکرد استفاده از Pydantic models برای validation در زمان读写 است. باید یک Pydantic model برای dynamic_fields و سایر فیلدهای JSON ایجاد شود و در setter/getter یا در validator استفاده شود. همچنین باید edge cases مانند None, empty string, invalid JSON handle شود.
**Excerpt:**
```
تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_project.py::test_edge_case", "timeout_seconds": 60}]
```

### Step 16: نوشتن تست edge case برای فیلدهای JSON Project model
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های edge case برای فیلدهای JSON در Project model است. باید تست‌هایی برای موارد زیر نوشته شود: None value, empty string, invalid JSON, valid JSON با ساختار درست, valid JSON با ساختار نادرست. تست‌ها باید در فایل tests/test_project.py قرار گیرند.
**Excerpt:**
```
تست edge case نوشته شد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_project.py::test_edge_case", "timeout_seconds": 60}]
```

### Step 17: اجرای تست‌های موجود برای اطمینان از عدم رگرشن
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های موجود با pytest برای اطمینان از اینکه تغییرات ایجاد شده باعث رگرشن نشده است. باید از دستور pytest backend/tests/ -x -v استفاده شود. اگر تست‌ها fail شوند، باید رفع شوند.
**Excerpt:**
```
- `pytest backend/tests/ -x -v`
```

### Step 18: اجرای linter و type checker برای اطمینان از کیفیت کد
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای linter (ruff) و type checker (mypy) برای اطمینان از کیفیت کد است. باید از دستورات ruff check backend/ و mypy backend/ استفاده شود. اگر warning یا error وجود دارد، باید رفع شود.
**Excerpt:**
```
- linter بدون warning عبور می‌کند
- type-check موفق است (`tsc --noEmit` / `mypy`)
```
