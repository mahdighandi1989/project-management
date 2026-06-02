---
task_id: task_48a9493b4a8b
title: راه‌اندازی CI/CD Pipeline و تست‌های خودکار برای Backend و Frontend
type: other
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:19:25.307719+00:00'
updated_at: '2026-06-02T18:00:51.872746+00:00'
tags:
- consolidated
- post_verify_merge
---

# راه‌اندازی CI/CD Pipeline و تست‌های خودکار برای Backend و Frontend

## Raw Idea

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به نبود تست خودکار و CI/CD pipeline که هر دو برای تضمین کیفیت کد ضروری هستند.
🎯 theme: رفع باگ‌های مربوط به CI/CD و تست خودکار
💎 estimated_difficulty: large

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 0a7da653-b6ab-4ac3-b1da-1a4710c17841
  عنوان اصلی: نبود تست خودکار (Unit/Integration Tests) برای Backend و Frontend
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/tests/, frontend/tests/

📋 acceptance_criteria کامل:
  - حداقل 10 تست unit برای Backend وجود داشته باشد [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
  - حداقل 5 تست integration برای API endpoints وجود داشته باشد [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
  - همه تست‌ها با موفقیت پاس شوند [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
  - پوشش کد حداقل 50% برای ماژول‌های اصلی [verify_method=static] [verify_plan={"grep_patterns": ["coverage", "pytest-cov", "coverage run"], "files_hint": ["backend/pyproject.toml", "backend/tox.ini", "backend/.coveragerc"]}]

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
نبود تست خودکار (Unit/Integration Tests) برای Backend و Frontend

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/` — پوشه tests وجود ندارد - باید ایجاد شود
- `frontend/tests/` — پوشه tests وجود ندارد - باید ایجاد شود

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
pytest, httpx, Jest, React Testing Library

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/projects.py` (سطر 1) — Route اصلی برای CRUD پروژه - نیاز به تست دارد
- `backend/app/api/routes/chat.py` (سطر 1) — Route برای AI chat - نیاز به تست دارد

## 🌐 نقشهٔ وابستگی‌ها
تست‌ها برای اطمینان از پایداری پروژه حیاتی هستند. بدون تست، هر commit می‌تواند باعث شکستن قابلیت‌های موجود شود.

## 🔍 Context و وضعیت فعلی
پروژه فاقد هرگونه تست خودکار است. با توجه به 169 فایل و 36+ route در Backend، عدم وجود تست باعث می‌شود تغییرات با ریسک بالای رگرشن همراه باشند. همچنین CI/CD بدون تست بی‌معنی است.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] حداقل 10 تست unit برای Backend وجود داشته باشد
- [ ] حداقل 5 تست integration برای API endpoints وجود داشته باشد
- [ ] همه تست‌ها با موفقیت پاس شوند
- [ ] پوشش کد حداقل 50% برای ماژول‌های اصلی
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن تست‌های unit و integration برای Backend با pytest و httpx (برای تست API). برای Frontend، افزودن تست با Jest و React Testing Library. حداقل 80% پوشش برای مسیرهای بحرانی (authentication, project CRUD, AI calls).

## 💡 نمونه‌های قبل/بعد
**قبل: عدم وجود تست**

_قبل:_
```
backend/tests/ (پوشه خالی یا وجود ندارد)
```

_بعد:_
```
backend/tests/test_projects.py, backend/tests/test_chat.py, ...
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd backend && pytest --cov=app --cov-report=term-missing`
- `cd frontend && npm test -- --coverage`

## ⚠️ ریسک‌ها و موارد احتیاط
نیاز به mock کردن سرویس‌های خارجی (AI providers) که ممکن است پیچیده باشد. همچنین ممکن است نیاز به بازنویسی بخش‌هایی از کد برای تست‌پذیری باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: large

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: c84540c6-68a8-4636-806a-e50be486f559
  عنوان اصلی: نبود CI/CD Pipeline و GitHub Actions Workflow
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: .github/workflows/ci.yml, .github/workflows/deploy.yml

📋 acceptance_criteria کامل:
  - workflow CI در هر push به شاخه اصلی اجرا شود [verify_method=static] [verify_plan={"grep_patterns": ["on:.*push", "branches:.*main"], "files_hint": [".github/workflows/ci.yml"]}]
  - workflow شامل تست، lint و امنیت اسکن باشد [verify_method=static] [verify_plan={"grep_patterns": ["test", "lint", "security"], "files_hint": [".github/workflows/ci.yml"]}]
  - workflow deploy به صورت دستی یا خودکار اجرا شود [verify_method=static] [verify_plan={"grep_patterns": ["workflow_dispatch", "on:.*push"], "files_hint": [".github/workflows/deploy.yml"]}]
  - همه مراحل workflow با موفقیت پاس شوند [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

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
نبود CI/CD Pipeline و GitHub Actions Workflow

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `.github/workflows/ci.yml` — فایل وجود ندارد - باید ایجاد شود
- `.github/workflows/deploy.yml` — فایل وجود ندارد - باید ایجاد شود

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
GitHub Actions, Docker, pytest, flake8, eslint

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/Dockerfile` (سطر 1) — برای build image در CI استفاده می‌شود
- `render.yaml` (سطر 1) — برای استقرار به Render استفاده می‌شود

## 🌐 نقشهٔ وابستگی‌ها
CI/CD برای تضمین کیفیت کد و استقرار خودکار حیاتی است. بدون آن، فرآیند توسعه کند و پرخطا خواهد بود.

## 🔍 Context و وضعیت فعلی
پروژه فاقد هرگونه فایل CI/CD (مانند .github/workflows/) است. با توجه به تعداد زیاد commits و merge requests، وجود CI/CD برای اجرای خودکار تست‌ها، linting و امنیت اسکن ضروری است.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] workflow CI در هر push به شاخه اصلی اجرا شود
- [ ] workflow شامل تست، lint و امنیت اسکن باشد
- [ ] workflow deploy به صورت دستی یا خودکار اجرا شود
- [ ] همه مراحل workflow با موفقیت پاس شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد فایل‌های GitHub Actions workflow برای: 1) اجرای تست‌ها در هر push/PR، 2) linting با flake8/black برای Python و eslint برای JS، 3) امنیت اسکن با bandit و npm audit، 4) build و deploy خودکار به Render/Railway.

## 💡 نمونه‌های قبل/بعد
**قبل: عدم وجود CI/CD**

_قبل:_
```
.github/workflows/ (پوشه وجود ندارد)
```

_بعد:_
```
.github/workflows/ci.yml, .github/workflows/deploy.yml
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `git push origin main # بررسی اجرای خودکار workflow`
- `gh run list # بررسی وضعیت workflow`

## ⚠️ ریسک‌ها و موارد احتیاط
نیاز به تنظیم secrets در GitHub (API keys, tokens). ممکن است workflow زمان‌بر باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
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
- در commit message: `merged-from: 0a7da653-b6ab-4ac3-b1da-1a4710c17841, c84540c6-68a8-4636-806a-e50be486f559`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 2 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های مربوط به نبود تست خودکار و CI/CD pipeline که هر دو برای تضمین کیفیت کد ضروری هستند.
🎯 theme: رفع باگ‌های مربوط به CI/CD و تست خودکار
💎 estimated_difficulty: large

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 2
  id: 0a7da653-b6ab-4ac3-b1da-1a4710c17841
  عنوان اصلی: نبود تست خودکار (Unit/Integration Tests) برای Backend و Frontend
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/tests/, frontend/tests/

📋 acceptance_criteria کامل:
  - حداقل 10 تست unit برای Backend وجود داشته باشد [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
  - حداقل 5 تست integration برای API endpoints وجود داشته باشد [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
  - همه تست‌ها با موفقیت پاس شوند [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
  - پوشش کد حداقل 50% برای ماژول‌های اصلی [verify_method=static] [verify_plan={"grep_patterns": ["coverage", "pytest-cov", "coverage run"], "files_hint": ["backend/pyproject.toml", "backend/tox.ini", "backend/.coveragerc"]}]

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
نبود تست خودکار (Unit/Integration Tests) برای Backend و Frontend

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/tests/` — پوشه tests وجود ندارد - باید ایجاد شود
- `frontend/tests/` — پوشه tests وجود ندارد - باید ایجاد شود

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
pytest, httpx, Jest, React Testing Library

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/projects.py` (سطر 1) — Route اصلی برای CRUD پروژه - نیاز به تست دارد
- `backend/app/api/routes/chat.py` (سطر 1) — Route برای AI chat - نیاز به تست دارد

## 🌐 نقشهٔ وابستگی‌ها
تست‌ها برای اطمینان از پایداری پروژه حیاتی هستند. بدون تست، هر commit می‌تواند باعث شکستن قابلیت‌های موجود شود.

## 🔍 Context و وضعیت فعلی
پروژه فاقد هرگونه تست خودکار است. با توجه به 169 فایل و 36+ route در Backend، عدم وجود تست باعث می‌شود تغییرات با ریسک بالای رگرشن همراه باشند. همچنین CI/CD بدون تست بی‌معنی است.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] حداقل 10 تست unit برای Backend وجود داشته باشد
- [ ] حداقل 5 تست integration برای API endpoints وجود داشته باشد
- [ ] همه تست‌ها با موفقیت پاس شوند
- [ ] پوشش کد حداقل 50% برای ماژول‌های اصلی
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. افزودن تست‌های unit و integration برای Backend با pytest و httpx (برای تست API). برای Frontend، افزودن تست با Jest و React Testing Library. حداقل 80% پوشش برای مسیرهای بحرانی (authentication, project CRUD, AI calls).

## 💡 نمونه‌های قبل/بعد
**قبل: عدم وجود تست**

_قبل:_
```
backend/tests/ (پوشه خالی یا وجود ندارد)
```

_بعد:_
```
backend/tests/test_projects.py, backend/tests/test_chat.py, ...
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd backend && pytest --cov=app --cov-report=term-missing`
- `cd frontend && npm test -- --coverage`

## ⚠️ ریسک‌ها و موارد احتیاط
نیاز به mock کردن سرویس‌های خارجی (AI providers) که ممکن است پیچیده باشد. همچنین ممکن است نیاز به بازنویسی بخش‌هایی از کد برای تست‌پذیری باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: high
- تخمین زمان: large

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 2
  id: c84540c6-68a8-4636-806a-e50be486f559
  عنوان اصلی: نبود CI/CD Pipeline و GitHub Actions Workflow
  اولویت اصلی: high
  وضعیت verify قبلی: partial
  فایل‌های دخیل: .github/workflows/ci.yml, .github/workflows/deploy.yml

📋 acceptance_criteria کامل:
  - workflow CI در هر push به شاخه اصلی اجرا شود [verify_method=static] [verify_plan={"grep_patterns": ["on:.*push", "branches:.*main"], "files_hint": [".github/workflows/ci.yml"]}]
  - workflow شامل تست، lint و امنیت اسکن باشد [verify_method=static] [verify_plan={"grep_patterns": ["test", "lint", "security"], "files_hint": [".github/workflows/ci.yml"]}]
  - workflow deploy به صورت دستی یا خودکار اجرا شود [verify_method=static] [verify_plan={"grep_patterns": ["workflow_dispatch", "on:.*push"], "files_hint": [".github/workflows/deploy.yml"]}]
  - همه مراحل workflow با موفقیت پاس شوند [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]

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
نبود CI/CD Pipeline و GitHub Actions Workflow

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `.github/workflows/ci.yml` — فایل وجود ندارد - باید ایجاد شود
- `.github/workflows/deploy.yml` — فایل وجود ندارد - باید ایجاد شود

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
GitHub Actions, Docker, pytest, flake8, eslint

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/Dockerfile` (سطر 1) — برای build image در CI استفاده می‌شود
- `render.yaml` (سطر 1) — برای استقرار به Render استفاده می‌شود

## 🌐 نقشهٔ وابستگی‌ها
CI/CD برای تضمین کیفیت کد و استقرار خودکار حیاتی است. بدون آن، فرآیند توسعه کند و پرخطا خواهد بود.

## 🔍 Context و وضعیت فعلی
پروژه فاقد هرگونه فایل CI/CD (مانند .github/workflows/) است. با توجه به تعداد زیاد commits و merge requests، وجود CI/CD برای اجرای خودکار تست‌ها، linting و امنیت اسکن ضروری است.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] workflow CI در هر push به شاخه اصلی اجرا شود
- [ ] workflow شامل تست، lint و امنیت اسکن باشد
- [ ] workflow deploy به صورت دستی یا خودکار اجرا شود
- [ ] همه مراحل workflow با موفقیت پاس شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد فایل‌های GitHub Actions workflow برای: 1) اجرای تست‌ها در هر push/PR، 2) linting با flake8/black برای Python و eslint برای JS، 3) امنیت اسکن با bandit و npm audit، 4) build و deploy خودکار به Render/Railway.

## 💡 نمونه‌های قبل/بعد
**قبل: عدم وجود CI/CD**

_قبل:_
```
.github/workflows/ (پوشه وجود ندارد)
```

_بعد:_
```
.github/workflows/ci.yml, .github/workflows/deploy.yml
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `git push origin main # بررسی اجرای خودکار workflow`
- `gh run list # بررسی وضعیت workflow`

## ⚠️ ریسک‌ها و موارد احتیاط
نیاز به تنظیم secrets در GitHub (API keys, tokens). ممکن است workflow زمان‌بر باشد.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
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
- در commit message: `merged-from: 0a7da653-b6ab-4ac3-b1da-1a4710c17841, c84540c6-68a8-4636-806a-e50be486f559`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. حداقل 10 تست unit برای Backend وجود داشته باشد _(verify: backend_test)_
2. حداقل 5 تست integration برای API endpoints وجود داشته باشد _(verify: backend_test)_
3. همه تست‌ها با موفقیت پاس شوند _(verify: backend_test)_
4. پوشش کد حداقل 50% برای ماژول‌های اصلی _(verify: static)_
5. workflow CI در هر push به شاخه اصلی اجرا شود _(verify: static)_
6. workflow شامل تست، lint و امنیت اسکن باشد _(verify: static)_
7. workflow deploy به صورت دستی یا خودکار اجرا شود _(verify: static)_
8. همه مراحل workflow با موفقیت پاس شوند _(verify: manual_only)_

## Task Steps

### Step 1: ایجاد پوشه و فایل‌های پایه تست برای Backend
**Status:** `pending` (0%)
**Scope:** ایجاد پوشه `backend/tests/` و فایل‌های خالی `__init__.py` و `conftest.py` با fixtureهای پایه (مثل client تست با httpx). این مرحله فقط زیرساخت تست را فراهم می‌کند و شامل نوشتن هیچ تستی نیست. نکته حیاتی: اطمینان از اینکه pytest و httpx در `backend/requirements.txt` یا `pyproject.toml` وجود دارند.
**Excerpt:**
```
- `backend/tests/` — پوشه tests وجود ندارد - باید ایجاد شود
- `backend/app/api/routes/projects.py` (سطر 1) — Route اصلی برای CRUD پروژه - نیاز به تست دارد
- `backend/app/api/routes/chat.py` (سطر 1) — Route برای AI chat - نیاز به تست دارد
```

### Step 2: نوشتن 10 تست Unit برای Backend (ماژول‌های اصلی)
**Status:** `pending` (0%)
**Scope:** نوشتن حداقل 10 تست Unit در فایل‌های `backend/tests/test_projects.py` و `backend/tests/test_chat.py` (و سایر ماژول‌های اصلی). این تست‌ها باید توابع و کلاس‌های غیر API (مثل سرویس‌ها، مدل‌ها، utility functions) را پوشش دهند. از pytest و mocking برای وابستگی‌های خارجی استفاده شود. نکته حیاتی: تست‌ها باید مستقل از دیتابیس واقعی و سرویس‌های خارجی باشند.
**Excerpt:**
```
- حداقل 10 تست unit برای Backend وجود داشته باشد [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
- همه تست‌ها با موفقیت پاس شوند [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
```

### Step 3: نوشتن 5 تست Integration برای API Endpoints Backend
**Status:** `pending` (0%)
**Scope:** نوشتن حداقل 5 تست Integration در `backend/tests/test_api.py` که API endpoints اصلی (مثل CRUD پروژه و AI chat) را با استفاده از httpx TestClient تست می‌کنند. این تست‌ها باید شامل ارسال درخواست HTTP واقعی به اپلیکیشن FastAPI (با دیتابیس تستی) باشند. نکته حیاتی: از دیتابیس مجزا (SQLite in-memory) برای ایزوله کردن تست‌ها استفاده شود.
**Excerpt:**
```
- حداقل 5 تست integration برای API endpoints وجود داشته باشد [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
- همه تست‌ها با موفقیت پاس شوند [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
```

### Step 4: پیکربندی پوشش کد (Code Coverage) برای Backend
**Status:** `pending` (0%)
**Scope:** اضافه کردن پکیج `pytest-cov` به وابستگی‌های Backend و پیکربندی آن در `backend/pyproject.toml` یا `backend/.coveragerc`. تنظیم coverage برای ماژول‌های اصلی (`backend/app/`) با حداقل آستانه 50%. نکته حیاتی: اطمینان از اینکه فایل‌های تست از coverage محاسبه نشوند.
**Excerpt:**
```
- پوشش کد حداقل 50% برای ماژول‌های اصلی [verify_method=static] [verify_plan={"grep_patterns": ["coverage", "pytest-cov", "coverage run"], "files_hint": ["backend/pyproject.toml", "backend/tox.ini", "backend/.coveragerc"]}]
```

### Step 5: ایجاد پوشه و فایل‌های پایه تست برای Frontend
**Status:** `pending` (0%)
**Scope:** ایجاد پوشه `frontend/tests/` و فایل‌های پیکربندی Jest (اگر وجود ندارد) و یک فایل تست نمونه (`frontend/tests/setupTests.ts`). اطمینان از اینکه Jest و React Testing Library در `frontend/package.json` وجود دارند. نکته حیاتی: بررسی اینکه `frontend/package.json` اسکریپت `test` را دارد.
**Excerpt:**
```
- `frontend/tests/` — پوشه tests وجود ندارد - باید ایجاد شود
- `cd frontend && npm test -- --coverage`
```

### Step 6: نوشتن تست‌های Unit برای Frontend (کامپوننت‌ها و هوک‌ها)
**Status:** `pending` (0%)
**Scope:** نوشتن حداقل 5 تست Unit برای کامپوننت‌ها و هوک‌های اصلی Frontend با استفاده از Jest و React Testing Library. تست‌ها باید در `frontend/tests/` قرار گیرند و شامل رندر کردن کامپوننت‌ها، شبیه‌سازی رویدادها و بررسی وضعیت‌ها باشند. نکته حیاتی: از mocking برای وابستگی‌های خارجی (API calls) استفاده شود.
**Excerpt:**
```
برای Frontend، افزودن تست با Jest و React Testing Library. حداقل 80% پوشش برای مسیرهای بحرانی (authentication, project CRUD, AI calls).
```

### Step 7: ایجاد فایل GitHub Actions CI Workflow (ci.yml)
**Status:** `pending` (0%)
**Scope:** ایجاد فایل `.github/workflows/ci.yml` که در هر push به شاخه اصلی (main) و هر Pull Request اجرا شود. این workflow باید شامل مراحل زیر باشد: 1) Checkout کد، 2) Setup Python و Node.js، 3) نصب وابستگی‌های Backend و Frontend، 4) اجرای Linter (flake8 برای Python، eslint برای JS)، 5) اجرای تست‌ها (pytest برای Backend، npm test برای Frontend)، 6) اجرای امنیت اسکن (bandit برای Python، npm audit برای JS). نکته حیاتی: از actions/setup-python و actions/setup-node با نسخه‌های مشخص استفاده شود.
**Excerpt:**
```
- workflow CI در هر push به شاخه اصلی اجرا شود [verify_method=static] [verify_plan={"grep_patterns": ["on:.*push", "branches:.*main"], "files_hint": [".github/workflows/ci.yml"]}]
- workflow شامل تست، lint و امنیت اسکن باشد [verify_method=static] [verify_plan={"grep_patterns": ["test", "lint", "security"], "files_hint": [".github/workflows/ci.yml"]}]
```

### Step 8: ایجاد فایل GitHub Actions Deploy Workflow (deploy.yml)
**Status:** `pending` (0%)
**Scope:** ایجاد فایل `.github/workflows/deploy.yml` که به صورت دستی (workflow_dispatch) یا خودکار (push به شاخه main) اجرا شود. این workflow باید شامل مراحل زیر باشد: 1) Checkout کد، 2) Setup Python و Node.js، 3) نصب وابستگی‌ها، 4) Build پروژه (Backend و Frontend)، 5) استقرار به Render (با استفاده از render.yaml یا Dockerfile). نکته حیاتی: از secrets برای ذخیره API keys و tokens استفاده شود.
**Excerpt:**
```
- workflow deploy به صورت دستی یا خودکار اجرا شود [verify_method=static] [verify_plan={"grep_patterns": ["workflow_dispatch", "on:.*push"], "files_hint": [".github/workflows/deploy.yml"]}]
- همه مراحل workflow با موفقیت پاس شوند [verify_method=manual_only] [verify_plan={"reason": "نیاز به بازبینی دستی"}]
```

### Step 9: اجرای تست‌ها و رفع خطاهای احتمالی
**Status:** `pending` (0%)
**Scope:** اجرای کامل تست‌های Backend و Frontend و رفع هرگونه خطا یا شکست در تست‌ها. این شامل رفع باگ‌های کد، اصلاح mocking، و اطمینان از عبور همه تست‌ها است. نکته حیاتی: تست‌ها باید به صورت ایزوله و بدون وابستگی به سرویس‌های خارجی اجرا شوند.
**Excerpt:**
```
- همه تست‌ها با موفقیت پاس شوند [verify_method=backend_test] [verify_plan={"test_node": "backend/tests/", "timeout_seconds": 120}]
- هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
```

### Step 10: اجرای Linter و Type-Check و رفع هشدارها
**Status:** `pending` (0%)
**Scope:** اجرای Linter برای Backend (flake8) و Frontend (eslint) و رفع تمام هشدارها و خطاها. همچنین اجرای type-check برای Backend (mypy) و Frontend (tsc --noEmit) و رفع خطاهای تایپ. نکته حیاتی: پیکربندی Linter و type-check باید در فایل‌های پیکربندی مربوطه (مثل `.flake8`، `.eslintrc`، `tsconfig.json`) انجام شود.
**Excerpt:**
```
- linter بدون warning عبور می‌کند
- type-check موفق است (`tsc --noEmit` / `mypy`)
```
