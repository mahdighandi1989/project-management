---
task_id: 6cdc6e7f-bee3-4a0a-a8f1-c801347cddf5
title: 'Session management anti-pattern: direct SessionLocal() calls without dependency injection in multiple route files'
type: refactor
priority: high
execution_priority: 100
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T06:37:53.504146+00:00'
updated_at: '2026-05-20T04:23:46.293083+00:00'
archived: true
archived_at: '2026-05-18T04:24:59.539920+00:00'
tags:
- merged
target_files:
- backend/app/api/routes/analysis.py
- backend/app/api/routes/analysis.py
- backend/app/api/routes/analysis.py
---

# Session management anti-pattern: direct SessionLocal() calls without dependency injection in multiple route files

## Raw Idea

Multiple route files (analysis.py, project_health.py, github_import.py) create database sessions using `SessionLocal()` directly instead of using FastAPI's `Depends(get_db)` dependency injection. This pattern bypasses the DI system, making it impossible to mock sessions in tests, causing potential connection leaks when exceptions occur before `finally` blocks, and violating FastAPI best practices. The `analysis.py` file at lines 117, 280, 299, 315, 349 creates sessions manually. `project_health.py` has similar issues. This is a systemic architectural problem affecting testability and reliability.

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

## Acceptance Criteria

1. Zero direct SessionLocal() calls in route files (except background tasks) _(verify: static)_
2. All CRUD endpoints use Depends(get_db) _(verify: static)_
3. Background tasks use a context-manager based session _(verify: static)_
4. Existing tests pass without modification _(verify: backend_test)_

## Task Steps

### Step 1: Refactor `analysis.py` to use FastAPI `Depends(get_db)` for all database sessions
**Status:** `not_done` (0%)
**Scope:** This step covers replacing all direct `SessionLocal()` calls in `backend/app/api/routes/analysis.py` with FastAPI's dependency injection pattern using `Depends(get_db)`. This includes lines 117, 280, 299, 315, and 349 as identified. The refactor must ensure that each route function receives a `db: Session` parameter via DI, and that the session lifecycle (open/close/rollback on exception) is managed by the DI system. This step does NOT include modifying other files like `project_health.py` or `github_import.py`, nor does it involve writing new tests. Critical: The nested async function at line 117 (`run_analysis_task`) must be refactored to accept `db` as a parameter passed from the outer route, or the session must be created inside the route and passed down. The `finally` blocks with `db.close()` must be removed as DI handles this.
**Excerpt:**
```
Multiple route files (analysis.py, project_health.py, github_import.py) create database sessions using `SessionLocal()` directly instead of using FastAPI's `Depends(get_db)` dependency injection. This pattern bypasses the DI system, making it impossible to mock sessions in tests, causing potential connection leaks when exceptions occur before `finally` blocks, and violating FastAPI best practices. The `analysis.py` file at lines 117, 280, 299, 315, 349 creates sessions manually.
```

### Step 2: Refactor `project_health.py` to use FastAPI `Depends(get_db)` for all database sessions
**Status:** `not_done` (0%)
**Scope:** This step covers replacing all direct `SessionLocal()` calls in `backend/app/api/routes/project_health.py` with FastAPI's dependency injection pattern using `Depends(get_db)`. The file has similar issues to `analysis.py`. All route functions must be updated to receive `db: Session` via DI, and manual session management (`try/finally` with `db.close()`) must be removed. This step does NOT include `analysis.py` (already done in step 1) or `github_import.py`. Critical: Ensure all occurrences in this file are found and refactored — search for `SessionLocal()` and `db.close()` patterns.
**Excerpt:**
```
`project_health.py` has similar issues. This is a systemic architectural problem affecting testability and reliability.
```

### Step 3: Refactor `github_import.py` to use FastAPI `Depends(get_db)` for all database sessions
**Status:** `not_done` (0%)
**Scope:** This step covers replacing all direct `SessionLocal()` calls in `backend/app/api/routes/github_import.py` with FastAPI's dependency injection pattern using `Depends(get_db)`. This file was mentioned as having similar issues. All route functions must be updated to receive `db: Session` via DI, and manual session management must be removed. This step does NOT include `analysis.py` or `project_health.py`. Critical: Search the entire file for `SessionLocal()` and `db.close()` patterns and refactor all occurrences.
**Excerpt:**
```
Multiple route files (analysis.py, project_health.py, github_import.py) create database sessions using `SessionLocal()` directly instead of using FastAPI's `Depends(get_db)` dependency injection.
```

### Step 4: Verify no remaining direct `SessionLocal()` calls exist in any route files
**Status:** `not_done` (0%)
**Scope:** This step involves a comprehensive search across all route files in `backend/app/api/routes/` to ensure no direct `SessionLocal()` calls remain. This is an audit step to catch any missed occurrences. Use `grep` or IDE search for `SessionLocal()` across the entire routes directory. If any are found, they must be refactored following the same pattern as steps 1-3. This step does NOT include modifying non-route files (e.g., services, models). Critical: This is a verification step — if no issues are found, no code changes are needed.
**Excerpt:**
```
This is a systemic architectural problem affecting testability and reliability.
```
