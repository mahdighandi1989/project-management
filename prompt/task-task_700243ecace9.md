---
task_id: task_700243ecace9
title: 'تلفیق: mechanical:files (2 تسک)'
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:27:21.527720+00:00'
updated_at: '2026-05-29T20:23:47.389913+00:00'
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
  id: f6834c73-8cbd-469b-94eb-9f6e75e67a01
  عنوان اصلی: ناسازگاری نسخه‌های وابستگی‌های فرانت‌اند: reactflow v11 با react 18 و next 14
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/package.json, frontend/src/app/projects/[id]/page.tsx

📋 acceptance_criteria کامل:
  - صفحه project detail بدون خطای hydration رندر شود [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/projects/1"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='react-flow']", "t]
  - build production با `npm run build` موفق باشد [verify_method=backend_test] [verify_plan={"test_node": "npm run build", "timeout_seconds": 120}]
  - نمودار ReactFlow به درستی نمایش داده شود و interactive باشد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/projects/1"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='react-flow']", "t]

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
ناسازگاری نسخه‌های وابستگی‌های فرانت‌اند: reactflow v11 با react 18 و next 14

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/package.json:18` — `reactflow` — وابستگی reactflow که باید به @xyflow/react ارتقا یابد یا با dynamic import محافظت شود
  ```json
  "reactflow": "^11.11.4"
  ```
- `frontend/src/app/projects/[id]/page.tsx:9-19` — `import ReactFlow` — import مستقیم reactflow در یک فایل App Router که می‌تواند باعث شکست SSR شود
  ```tsx
  import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    useNodesState,
    useEdgesState,
    BackgroundVariant,
    MarkerType,
  } from 'reactflow';
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + React 18 + reactflow 11

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `frontend/package-lock.json` (سطر 1) — lock file که باید با تغییر package.json هماهنگ شود
- `frontend/next.config.js` (سطر 1) — ممکن است نیاز به transpilePackages برای @xyflow/react داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
reactflow v11 توسط یک صفحه (project detail) استفاده می‌شود. ارتقا به @xyflow/react v12 نیازمند تغییر importها و بررسی API changes است.

## 🔍 Context و وضعیت فعلی
در `frontend/package.json`، وابستگی `reactflow` با نسخه `^11.11.4` تعریف شده است. این کتابخانه (که اکنون با نام `@xyflow/react` منتشر می‌شود) در نسخه 11 خود با React 18 و Next.js 14 App Router ناسازگاری‌های شناخته‌شده‌ای در رندر سمت سرور (SSR) و hydration دارد. فایل `frontend/src/app/projects/[id]/page.tsx` (خط 9) مستقیماً `reactflow` را import می‌کند و از `ReactFlow`, `Controls`, `Background`, `MiniMap`, `useNodesState`, `useEdgesState`, `BackgroundVariant`, `MarkerType` استفاده می‌کند. این می‌تواند باعث خطاهای hydration و شکست build در محیط production شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] صفحه project detail بدون خطای hydration رندر شود
- [ ] build production با `npm run build` موفق باشد
- [ ] نمودار ReactFlow به درستی نمایش داده شود و interactive باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مهاجرت به `@xyflow/react` نسخه 12 (که رسماً React 18 و Next.js 14 را پشتیبانی می‌کند) یا نصب `reactflow@11.11.4` با `--legacy-peer-deps` و افزودن `'use client'` در بالای کامپوننت‌های استفاده‌کننده و اطمینان از dynamic import با `next/dynamic` و `ssr: false`.

## 💡 نمونه‌های قبل/بعد
**تغییر import و نصب**

_قبل:_
```
import ReactFlow from 'reactflow';
```

_بعد:_
```
import ReactFlow from '@xyflow/react';
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd frontend && npm run build`
- `cd frontend && npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر API بین reactflow v11 و @xyflow/react v12 ممکن است نیاز به تطبیق کد داشته باشد؛ مستندات migration باید بررسی شود.

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
تسک 2 از 2
  id: cd9a0974-a2c0-426e-be99-52c3c8aa8fc8
  عنوان اصلی: ناسازگاری نسخه‌های react-markdown و react-syntax-highlighter با React 18
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/package.json

📋 acceptance_criteria کامل:
  - npm install بدون خطا اجرا شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_dependencies.py::test_npm_install", "timeout_seconds": 120}]
  - build پروژه با npm run build موفق باشد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_dependencies.py::test_npm_build", "timeout_seconds": 300}]
  - کامپوننت‌های استفاده‌کننده از react-markdown و react-syntax-highlighter بدون خطا رندر شوند [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "navigate", "url": "/page-with-markdown"}, {"action": "wait_for_lo]

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
ناسازگاری نسخه‌های react-markdown و react-syntax-highlighter با React 18

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/package.json:20-21` — `dependencies` — نسخه‌های ناسازگار با React 18
  ```json
  "react-markdown": "^9.0.1",
  "react-syntax-highlighter": "^15.5.0",
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 + React 18 + TypeScript 5.3

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `frontend/package-lock.json` (سطر 1) — قفل وابستگی‌ها که باید با تغییر package.json هماهنگ شود
- `frontend/next.config.js` (سطر 1) — تنظیمات Next.js که ممکن است نیاز به transpilePackages داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
react-markdown v9 به React 19 نیاز دارد در حالی که پروژه از React 18 استفاده می‌کند. react-syntax-highlighter v15.5.0 ممکن است با React 18 سازگار باشد اما بهتر است نسخه پایدارتر استفاده شود.

## 🔍 Context و وضعیت فعلی
در frontend/package.json، react-markdown نسخه ^9.0.1 و react-syntax-highlighter نسخه ^15.5.0 به عنوان وابستگی ذکر شده‌اند. react-markdown v9 به React 19 نیاز دارد و با React 18 ناسازگار است. react-syntax-highlighter v15.5.0 نیز ممکن است با نسخه‌های جدیدتر React سازگار نباشد. این ناسازگاری باعث خطاهای build و runtime در Next.js 14 می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] npm install بدون خطا اجرا شود
- [ ] build پروژه با npm run build موفق باشد
- [ ] کامپوننت‌های استفاده‌کننده از react-markdown و react-syntax-highlighter بدون خطا رندر شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. react-markdown را به نسخه 8.0.7 (سازگار با React 18) کاهش دهید و react-syntax-highlighter را به نسخه 15.5.0 نگه دارید یا به نسخه پایدارتر 15.4.5 کاهش دهید.

## 💡 نمونه‌های قبل/بعد
**اصلاح نسخه react-markdown**

_قبل:_
```
"react-markdown": "^9.0.1"
```

_بعد:_
```
"react-markdown": "^8.0.7"
```

**اصلاح نسخه react-syntax-highlighter**

_قبل:_
```
"react-syntax-highlighter": "^15.5.0"
```

_بعد:_
```
"react-syntax-highlighter": "^15.4.5"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd frontend && npm install`
- `cd frontend && npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
کاهش نسخه ممکن است برخی APIهای جدید را از دسترس خارج کند اما با React 18 سازگاری تضمین می‌شود.

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
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: f6834c73-8cbd-469b-94eb-9f6e75e67a01, cd9a0974-a2c0-426e-be99-52c3c8aa8fc8`
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
  id: f6834c73-8cbd-469b-94eb-9f6e75e67a01
  عنوان اصلی: ناسازگاری نسخه‌های وابستگی‌های فرانت‌اند: reactflow v11 با react 18 و next 14
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/package.json, frontend/src/app/projects/[id]/page.tsx

📋 acceptance_criteria کامل:
  - صفحه project detail بدون خطای hydration رندر شود [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/projects/1"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='react-flow']", "t]
  - build production با `npm run build` موفق باشد [verify_method=backend_test] [verify_plan={"test_node": "npm run build", "timeout_seconds": 120}]
  - نمودار ReactFlow به درستی نمایش داده شود و interactive باشد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/projects/1"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='react-flow']", "t]

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
ناسازگاری نسخه‌های وابستگی‌های فرانت‌اند: reactflow v11 با react 18 و next 14

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/package.json:18` — `reactflow` — وابستگی reactflow که باید به @xyflow/react ارتقا یابد یا با dynamic import محافظت شود
  ```json
  "reactflow": "^11.11.4"
  ```
- `frontend/src/app/projects/[id]/page.tsx:9-19` — `import ReactFlow` — import مستقیم reactflow در یک فایل App Router که می‌تواند باعث شکست SSR شود
  ```tsx
  import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    useNodesState,
    useEdgesState,
    BackgroundVariant,
    MarkerType,
  } from 'reactflow';
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 App Router + React 18 + reactflow 11

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `frontend/package-lock.json` (سطر 1) — lock file که باید با تغییر package.json هماهنگ شود
- `frontend/next.config.js` (سطر 1) — ممکن است نیاز به transpilePackages برای @xyflow/react داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
reactflow v11 توسط یک صفحه (project detail) استفاده می‌شود. ارتقا به @xyflow/react v12 نیازمند تغییر importها و بررسی API changes است.

## 🔍 Context و وضعیت فعلی
در `frontend/package.json`، وابستگی `reactflow` با نسخه `^11.11.4` تعریف شده است. این کتابخانه (که اکنون با نام `@xyflow/react` منتشر می‌شود) در نسخه 11 خود با React 18 و Next.js 14 App Router ناسازگاری‌های شناخته‌شده‌ای در رندر سمت سرور (SSR) و hydration دارد. فایل `frontend/src/app/projects/[id]/page.tsx` (خط 9) مستقیماً `reactflow` را import می‌کند و از `ReactFlow`, `Controls`, `Background`, `MiniMap`, `useNodesState`, `useEdgesState`, `BackgroundVariant`, `MarkerType` استفاده می‌کند. این می‌تواند باعث خطاهای hydration و شکست build در محیط production شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] صفحه project detail بدون خطای hydration رندر شود
- [ ] build production با `npm run build` موفق باشد
- [ ] نمودار ReactFlow به درستی نمایش داده شود و interactive باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مهاجرت به `@xyflow/react` نسخه 12 (که رسماً React 18 و Next.js 14 را پشتیبانی می‌کند) یا نصب `reactflow@11.11.4` با `--legacy-peer-deps` و افزودن `'use client'` در بالای کامپوننت‌های استفاده‌کننده و اطمینان از dynamic import با `next/dynamic` و `ssr: false`.

## 💡 نمونه‌های قبل/بعد
**تغییر import و نصب**

_قبل:_
```
import ReactFlow from 'reactflow';
```

_بعد:_
```
import ReactFlow from '@xyflow/react';
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd frontend && npm run build`
- `cd frontend && npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
تغییر API بین reactflow v11 و @xyflow/react v12 ممکن است نیاز به تطبیق کد داشته باشد؛ مستندات migration باید بررسی شود.

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
تسک 2 از 2
  id: cd9a0974-a2c0-426e-be99-52c3c8aa8fc8
  عنوان اصلی: ناسازگاری نسخه‌های react-markdown و react-syntax-highlighter با React 18
  اولویت اصلی: high
  وضعیت verify قبلی: pending
  فایل‌های دخیل: frontend/package.json

📋 acceptance_criteria کامل:
  - npm install بدون خطا اجرا شود [verify_method=backend_test] [verify_plan={"test_node": "tests/test_dependencies.py::test_npm_install", "timeout_seconds": 120}]
  - build پروژه با npm run build موفق باشد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_dependencies.py::test_npm_build", "timeout_seconds": 300}]
  - کامپوننت‌های استفاده‌کننده از react-markdown و react-syntax-highlighter بدون خطا رندر شوند [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "navigate", "url": "/page-with-markdown"}, {"action": "wait_for_lo]

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
ناسازگاری نسخه‌های react-markdown و react-syntax-highlighter با React 18

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/package.json:20-21` — `dependencies` — نسخه‌های ناسازگار با React 18
  ```json
  "react-markdown": "^9.0.1",
  "react-syntax-highlighter": "^15.5.0",
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Next.js 14 + React 18 + TypeScript 5.3

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `frontend/package-lock.json` (سطر 1) — قفل وابستگی‌ها که باید با تغییر package.json هماهنگ شود
- `frontend/next.config.js` (سطر 1) — تنظیمات Next.js که ممکن است نیاز به transpilePackages داشته باشد

## 🌐 نقشهٔ وابستگی‌ها
react-markdown v9 به React 19 نیاز دارد در حالی که پروژه از React 18 استفاده می‌کند. react-syntax-highlighter v15.5.0 ممکن است با React 18 سازگار باشد اما بهتر است نسخه پایدارتر استفاده شود.

## 🔍 Context و وضعیت فعلی
در frontend/package.json، react-markdown نسخه ^9.0.1 و react-syntax-highlighter نسخه ^15.5.0 به عنوان وابستگی ذکر شده‌اند. react-markdown v9 به React 19 نیاز دارد و با React 18 ناسازگار است. react-syntax-highlighter v15.5.0 نیز ممکن است با نسخه‌های جدیدتر React سازگار نباشد. این ناسازگاری باعث خطاهای build و runtime در Next.js 14 می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] npm install بدون خطا اجرا شود
- [ ] build پروژه با npm run build موفق باشد
- [ ] کامپوننت‌های استفاده‌کننده از react-markdown و react-syntax-highlighter بدون خطا رندر شوند
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. react-markdown را به نسخه 8.0.7 (سازگار با React 18) کاهش دهید و react-syntax-highlighter را به نسخه 15.5.0 نگه دارید یا به نسخه پایدارتر 15.4.5 کاهش دهید.

## 💡 نمونه‌های قبل/بعد
**اصلاح نسخه react-markdown**

_قبل:_
```
"react-markdown": "^9.0.1"
```

_بعد:_
```
"react-markdown": "^8.0.7"
```

**اصلاح نسخه react-syntax-highlighter**

_قبل:_
```
"react-syntax-highlighter": "^15.5.0"
```

_بعد:_
```
"react-syntax-highlighter": "^15.4.5"
```

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `cd frontend && npm install`
- `cd frontend && npm run build`

## ⚠️ ریسک‌ها و موارد احتیاط
کاهش نسخه ممکن است برخی APIهای جدید را از دسترس خارج کند اما با React 18 سازگاری تضمین می‌شود.

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
💡 نکات استاندارد (همان bullet هایی که در ساخت پرامپت‌های معمولی پروژه رعایت می‌شود — وراثت کامل، نه کپی):
- ساختار AC ها: acceptance_criteria با verify_method و verify_plan و evidence_locations برای هر AC
- edge cases را در نظر بگیر و در پرامپت ذکر کن
- وابستگی‌ها را اول حل کن (dependency-aware ordering)
- اگر بخشی از یکی از تسک‌ها قبلاً done است (pre_done در بالا)، تکرار نکن — فقط روی remaining_parts تمرکز کن
- در commit message: `merged-from: f6834c73-8cbd-469b-94eb-9f6e75e67a01, cd9a0974-a2c0-426e-be99-52c3c8aa8fc8`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. صفحه project detail بدون خطای hydration رندر شود _(verify: ui_interaction)_
2. build production با `npm run build` موفق باشد _(verify: backend_test)_
3. نمودار ReactFlow به درستی نمایش داده شود و interactive باشد _(verify: ui_interaction)_
4. npm install بدون خطا اجرا شود _(verify: backend_test)_
5. build پروژه با npm run build موفق باشد _(verify: backend_test)_
6. کامپوننت‌های استفاده‌کننده از react-markdown و react-syntax-highlighter بدون خطا رندر شوند _(verify: ui_interaction)_

## Task Steps

### Step 1: بررسی وضعیت فعلی وابستگی‌ها و فایل‌های مرتبط در مخزن
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل مخزن برای یافتن وضعیت فعلی وابستگی‌های reactflow، react-markdown و react-syntax-highlighter در frontend/package.json است. همچنین باید فایل‌های frontend/src/app/projects/[id]/page.tsx و frontend/next.config.js و frontend/package-lock.json بررسی شوند تا مشخص شود آیا تغییراتی قبلاً اعمال شده است یا خیر. این مرحله فقط شامل بررسی و مستندسازی وضعیت فعلی است و هیچ تغییری در کد ایجاد نمی‌کند. نکته حیاتی: اگر reactflow قبلاً به @xyflow/react مهاجرت شده یا react-markdown به نسخه 8 کاهش یافته، این مرحله باید آن را ثبت کند و مراحل بعدی را لغو کند.
**Excerpt:**
```
♻️ **احتمال پیاده‌سازی قبلی (مهم):** - ممکن است **بخشی یا تمامِ** این درخواست قبلاً (به صورت کامل یا ناقص) در repo پیاده‌سازی شده باشد. پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی **از قبل وجود دارد**. - اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را **دوباره نساز**؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن. - اگر همه چیز از قبل به‌درستی انجام شده: یک کامیت توضیحی (no-op) ثبت کن که چرا تغییری لازم نبود و دقیقاً کدام فایل‌ها این درخواست را پوشش می‌دهند.
```

### Step 2: مهاجرت reactflow v11 به @xyflow/react v12 در frontend/package.json
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر وابستگی reactflow در frontend/package.json از نسخه ^11.11.4 به @xyflow/react با نسخه مناسب (v12) است. همچنین باید دستور npm install اجرا شود تا وابستگی جدید نصب و package-lock.json به‌روزرسانی شود. این مرحله فقط تغییر در package.json و نصب وابستگی را شامل می‌شود و شامل تغییر importها در فایل‌های TypeScript نیست. نکته حیاتی: باید از نسخه‌ای از @xyflow/react استفاده شود که با React 18 و Next.js 14 سازگار باشد.
**Excerpt:**
```
- `frontend/package.json:18` — `reactflow` — وابستگی reactflow که باید به @xyflow/react ارتقا یابد یا با dynamic import محافظت شود
  ```json
  "reactflow": "^11.11.4"
  ```

**تغییر import و نصب**

_قبل:_
```
import ReactFlow from 'reactflow';
```

_بعد:_
```
import ReactFlow from '@xyflow/react';
```
```

### Step 3: به‌روزرسانی importهای reactflow در frontend/src/app/projects/[id]/page.tsx به @xyflow/react
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر تمام importهای reactflow در frontend/src/app/projects/[id]/page.tsx به @xyflow/react است. importهای ReactFlow, Node, Edge, Controls, Background, MiniMap, useNodesState, useEdgesState, BackgroundVariant, MarkerType باید از '@xyflow/react' وارد شوند. همچنین باید بررسی شود که آیا API بین reactflow v11 و @xyflow/react v12 تغییر کرده است و کد استفاده‌کننده از این importها باید تطبیق داده شود. این مرحله فقط فایل page.tsx را تغییر می‌دهد. نکته حیاتی: مستندات migration باید بررسی شود تا از تطبیق صحیح API اطمینان حاصل شود.
**Excerpt:**
```
- `frontend/src/app/projects/[id]/page.tsx:9-19` — `import ReactFlow` — import مستقیم reactflow در یک فایل App Router که می‌تواند باعث شکست SSR شود
  ```tsx
  import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    useNodesState,
    useEdgesState,
    BackgroundVariant,
    MarkerType,
  } from 'reactflow';
  ```

**تغییر import و نصب**

_قبل:_
```
import ReactFlow from 'reactflow';
```

_بعد:_
```
import ReactFlow from '@xyflow/react';
```
```

### Step 4: افزودن 'use client' و dynamic import با next/dynamic برای کامپوننت ReactFlow در page.tsx
**Status:** `pending` (0%)
**Scope:** این مرحله شامل افزودن 'use client' در بالای فایل frontend/src/app/projects/[id]/page.tsx و استفاده از next/dynamic با ssr: false برای import کامپوننت ReactFlow است. این کار از شکست SSR و خطاهای hydration جلوگیری می‌کند. کامپوننت ReactFlow باید به صورت dynamic و فقط در سمت کلاینت بارگذاری شود. این مرحله شامل تغییر ساختار کامپوننت برای پشتیبانی از dynamic import است. نکته حیاتی: تمام کامپوننت‌های وابسته به ReactFlow (Controls, Background, MiniMap) نیز باید در همان dynamic import قرار گیرند.
**Excerpt:**
```
نصب `reactflow@11.11.4` با `--legacy-peer-deps` و افزودن `'use client'` در بالای کامپوننت‌های استفاده‌کننده و اطمینان از dynamic import با `next/dynamic` و `ssr: false`.

- صفحه project detail بدون خطای hydration رندر شود [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/projects/1"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "wait_for", "selector": "[data-testid='react-flow']", "t}]
```

### Step 5: کاهش نسخه react-markdown به 8.0.7 در frontend/package.json
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر وابستگی react-markdown در frontend/package.json از نسخه ^9.0.1 به ^8.0.7 است. react-markdown v9 به React 19 نیاز دارد و با React 18 ناسازگار است. نسخه 8.0.7 با React 18 سازگار است. پس از تغییر، دستور npm install اجرا می‌شود تا وابستگی جدید نصب و package-lock.json به‌روزرسانی شود. این مرحله فقط تغییر در package.json و نصب وابستگی را شامل می‌شود. نکته حیاتی: کاهش نسخه ممکن است برخی APIهای جدید react-markdown v9 را از دسترس خارج کند.
**Excerpt:**
```
react-markdown v9 به React 19 نیاز دارد در حالی که پروژه از React 18 استفاده می‌کند.

**اصلاح نسخه react-markdown**

_قبل:_
```
"react-markdown": "^9.0.1"
```

_بعد:_
```
"react-markdown": "^8.0.7"
```
```

### Step 6: کاهش نسخه react-syntax-highlighter به 15.4.5 در frontend/package.json
**Status:** `pending` (0%)
**Scope:** این مرحله شامل تغییر وابستگی react-syntax-highlighter در frontend/package.json از نسخه ^15.5.0 به ^15.4.5 است. نسخه 15.4.5 با React 18 سازگاری بیشتری دارد. پس از تغییر، دستور npm install اجرا می‌شود تا وابستگی جدید نصب و package-lock.json به‌روزرسانی شود. این مرحله فقط تغییر در package.json و نصب وابستگی را شامل می‌شود. نکته حیاتی: کاهش نسخه ممکن است برخی APIهای جدید react-syntax-highlighter v15.5.0 را از دسترس خارج کند.
**Excerpt:**
```
react-syntax-highlighter v15.5.0 ممکن است با React 18 سازگار باشد اما بهتر است نسخه پایدارتر استفاده شود.

**اصلاح نسخه react-syntax-highlighter**

_قبل:_
```
"react-syntax-highlighter": "^15.5.0"
```

_بعد:_
```
"react-syntax-highlighter": "^15.4.5"
```
```

### Step 7: به‌روزرسانی frontend/next.config.js برای transpilePackages در صورت نیاز
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی و به‌روزرسانی frontend/next.config.js برای افزودن transpilePackages برای @xyflow/react و react-markdown و react-syntax-highlighter در صورت نیاز است. برخی کتابخانه‌های ESM نیاز به transpile در Next.js دارند. این مرحله فقط در صورتی انجام می‌شود که build با خطا مواجه شود. نکته حیاتی: ابتدا build را بدون این تغییر امتحان کنید و فقط در صورت نیاز transpilePackages را اضافه کنید.
**Excerpt:**
```
- `frontend/next.config.js` (سطر 1) — تنظیمات Next.js که ممکن است نیاز به transpilePackages داشته باشد

- `frontend/next.config.js` (سطر 1) — ممکن است نیاز به transpilePackages برای @xyflow/react داشته باشد
```

### Step 8: اجرای build production و رفع خطاهای احتمالی
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای `cd frontend && npm run build` برای اطمینان از موفقیت build production است. اگر خطایی رخ دهد، باید رفع شود. خطاهای احتمالی شامل خطاهای type-check، linting، یا خطاهای مربوط به importهای نادرست است. این مرحله شامل رفع تمام خطاهای build است. نکته حیاتی: build باید بدون خطا و بدون warning (تا حد امکان) انجام شود.
**Excerpt:**
```
- build production با `npm run build` موفق باشد [verify_method=backend_test] [verify_plan={"test_node": "npm run build", "timeout_seconds": 120}]

- build پروژه با npm run build موفق باشد [verify_method=backend_test] [verify_plan={"test_node": "tests/test_dependencies.py::test_npm_build", "timeout_seconds": 300}]
```

### Step 9: اجرای تست‌ها و اطمینان از عدم شکست
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تمام تست‌های پروژه با دستورات `cd frontend && npm run test` و `cd frontend && npm run lint` و `cd frontend && npx tsc --noEmit` است. اگر هر یک از این دستورات با خطا مواجه شود، باید رفع شود. این مرحله شامل رفع تمام خطاهای تست، linting و type-check است. نکته حیاتی: هیچ تستی نباید fail شود و linter باید بدون warning عبور کند.
**Excerpt:**
```
- هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- linter بدون warning عبور می‌کند
- type-check موفق است (`tsc --noEmit` / `mypy`)
```

### Step 10: ثبت commit با پیام واضح و ارجاع به تسک‌های مبدأ
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ثبت یک commit (یا چند commit در صورت لزوم) با پیام واضح است که تمام تغییرات اعمال شده را توضیح می‌دهد. پیام commit باید شامل ارجاع به IDهای تسک مبدأ (f6834c73-8cbd-469b-94eb-9f6e75e67a01 و cd9a0974-a2c0-426e-be99-52c3c8aa8fc8) با فرمت `merged-from: f6834c73-8cbd-469b-94eb-9f6e75e67a01, cd9a0974-a2c0-426e-be99-52c3c8aa8fc8` باشد. همچنین باید checklist از تمام کامیت‌ها در PR description نوشته شود. نکته حیاتی: پیام commit باید دقیق و کامل باشد و تمام تغییرات را پوشش دهد.
**Excerpt:**
```
در commit message: `merged-from: f6834c73-8cbd-469b-94eb-9f6e75e67a01, cd9a0974-a2c0-426e-be99-52c3c8aa8fc8`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند
```
