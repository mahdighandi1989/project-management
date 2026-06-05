---
task_id: task_594ab2aa219b
title: پاکسازی و حذف endpointها و routeهای بلااستفاده در بک‌اند و فرانت‌اند
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-18T04:21:34.892704+00:00'
updated_at: '2026-06-03T18:22:00.658020+00:00'
tags:
- consolidated
- post_verify_merge
---

# پاکسازی و حذف endpointها و routeهای بلااستفاده در بک‌اند و فرانت‌اند

## Raw Idea

🧬 این یک تسک تلفیقی است — از 11 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 0، 1، 2، 3، 4، 5، 6، 7، 8، 9، 10 همگی به حذف endpointها یا routeهای بلااستفاده مربوط می‌شوند. تسک‌های 0 و 1 partial هستند و با not_doneهای این خوشه هم‌موضوع هستند.
🎯 theme: حذف endpointها و routeهای بلااستفاده در بک‌اند و فرانت‌اند
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 11
  id: 05088e2f-a9fd-4c71-811d-74d09a5b8629
  عنوان اصلی: route فرانت‌اند بلااستفاده: /analysis
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - تأیید شد که `/analysis` orphan است (هیچ Link/router.push اشاره نمی‌کند) [verify_method=static] [verify_plan={"grep_patterns": ["/analysis", "router.push.*analysis", "Link.*analysis"], "files_hint": ["frontend/src/**/*.{tsx,ts,jsx,js}"]}]
  - یا navigation link اضافه شد، یا route حذف/redirect شد [verify_method=static] [verify_plan={"grep_patterns": ["/analysis", "router.push.*analysis", "Link.*analysis", "redirect.*analysis"], "files_hint": ["frontend/src/**/*.{tsx,ts,jsx,js}"]}]
  - تست navigation: کاربر بتواند به این صفحه (یا destination) برسد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='nav-analysis']"}, {"action": "]

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
route فرانت‌اند بلااستفاده: /analysis

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
route `/analysis` در فایل `` تعریف شده ولی هیچ `Link`، `router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.

## 🔍 جزئیات
- route path: `/analysis`
- فایل: ``
- علت: route exists in app router but no Link/router.push references it

## 🤔 چرا مهم است
route orphan یعنی صفحه‌ای که فقط با تایپ مستقیم URL قابل دسترسی است. یا فراموش شده یا منسوخ. باعث می‌شود کاربر هرگز به feature نرسد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد که `/analysis` orphan است (هیچ Link/router.push اشاره نمی‌کند)
- [ ] یا navigation link اضافه شد، یا route حذف/redirect شد
- [ ] تست navigation: کاربر بتواند به این صفحه (یا destination) برسد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: بررسی کن آیا این route از طریق dynamic URL (مثل sidebar config) اشاره می‌شود — grep روی `/analysis` در کل کدبیس بزن.
گام ۲: اگر orphan واقعی است، یا (الف) lin/redirect در navigation اصلی اضافه کن، یا (ب) فایل route را حذف کن.
گام ۳: اگر deprecated است، redirect 301 به route جدید بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف route ممکن است bookmark خارجی/SEO link خارجی را بشکند. اگر SEO اهمیت دارد، redirect بنویس نه delete.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 11
  id: 5565b1ea-cbe1-4858-9850-b791c5f7bf92
  عنوان اصلی: route فرانت‌اند بلااستفاده: /model-profiles
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - تأیید شد که `/model-profiles` orphan است (هیچ Link/router.push اشاره نمی‌کند) [verify_method=static] [verify_plan={"grep_patterns": ["Link.*to=\"/model-profiles\"", "router\\.push.*\"/model-profiles\"", "router\\.replace.*\"/model-profiles\""], "files_hint": ["frontend/**/*.{tsx,ts,jsx,js}"]}]
  - یا navigation link اضافه شد، یا route حذف/redirect شد [verify_method=static] [verify_plan={"grep_patterns": ["Link.*to=\"/model-profiles\"", "router\\.push.*\"/model-profiles\"", "router\\.replace.*\"/model-profiles\"", "redirect.*\"/model-profiles\""], "files_hint": ["frontend/**/*.{tsx,t]
  - تست navigation: کاربر بتواند به این صفحه (یا destination) برسد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='nav-link-model-profiles']"}, {]

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
route فرانت‌اند بلااستفاده: /model-profiles

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
route `/model-profiles` در فایل `` تعریف شده ولی هیچ `Link`، `router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.

## 🔍 جزئیات
- route path: `/model-profiles`
- فایل: ``
- علت: route exists in app router but no Link/router.push references it

## 🤔 چرا مهم است
route orphan یعنی صفحه‌ای که فقط با تایپ مستقیم URL قابل دسترسی است. یا فراموش شده یا منسوخ. باعث می‌شود کاربر هرگز به feature نرسد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد که `/model-profiles` orphan است (هیچ Link/router.push اشاره نمی‌کند)
- [ ] یا navigation link اضافه شد، یا route حذف/redirect شد
- [ ] تست navigation: کاربر بتواند به این صفحه (یا destination) برسد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: بررسی کن آیا این route از طریق dynamic URL (مثل sidebar config) اشاره می‌شود — grep روی `/model-profiles` در کل کدبیس بزن.
گام ۲: اگر orphan واقعی است، یا (الف) lin/redirect در navigation اصلی اضافه کن، یا (ب) فایل route را حذف کن.
گام ۳: اگر deprecated است، redirect 301 به route جدید بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف route ممکن است bookmark خارجی/SEO link خارجی را بشکند. اگر SEO اهمیت دارد، redirect بنویس نه delete.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 11
  id: 633abd7a-c942-43cc-91fd-60e35eadd353
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /profiles/compare
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /profiles/compare` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def compare", "POST.*/profiles/compare", "profiles/compare"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["profiles/compare", "fetch.*profiles/compare", "axios.*profiles/compare", "apiClient.*profiles/compare"], "files_hint": ["backend/app/api/routes/analysis.py", "frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["profiles/compare", "test.*compare", "compare.*test"], "files_hint": ["backend/tests/", "backend/app/api/routes/analysis.py"]}]

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
endpoint بک‌اند بلااستفاده: POST /profiles/compare

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /profiles/compare` در `backend/app/api/routes/analysis.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/profiles/compare`
- فایل: `backend/app/api/routes/analysis.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /profiles/compare` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/profiles/compare` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/analysis.py`
- `ruff check backend/app/api/routes/analysis.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 11
  id: 6838f513-dd7d-4f24-abdc-416a5bc791b5
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /imported/{project_id}/refresh
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /imported/{project_id}/refresh` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def refresh", "POST /imported/", "refresh"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["imported.*refresh", "refresh.*imported", "apiClient.*refresh", "fetch.*refresh"], "files_hint": ["frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["test.*refresh", "refresh.*test"], "files_hint": ["backend/tests/"]}]

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
endpoint بک‌اند بلااستفاده: POST /imported/{project_id}/refresh

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /imported/{project_id}/refresh` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/imported/{project_id}/refresh`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /imported/{project_id}/refresh` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/imported/{project_id}/refresh` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 11
  id: df88b572-69f7-4265-92ac-2a870f3b6d2d
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /parse-url
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /parse-url` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def parse_url", "POST.*/parse-url", "parse-url"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["parse-url", "parse_url"], "files_hint": ["backend/app/api/routes/github_import.py", "frontend/src"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["parse_url", "parse-url"], "files_hint": ["backend/tests", "backend/app/api/openapi.json", "backend/app/api/routes/github_import.py"]}]

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
endpoint بک‌اند بلااستفاده: POST /parse-url

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /parse-url` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/parse-url`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /parse-url` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/parse-url` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 11
  id: 248d1575-ca2a-4446-9cfd-7db48d43b59e
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /pr/from-project/{project_id}
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /pr/from-project/{project_id}` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def.*from_project", "POST.*/pr/from-project", "from-project"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["from_project", "from-project", "github_import"], "files_hint": ["backend/app/api/routes/github_import.py", "frontend/src/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["from_project", "from-project", "github_import"], "files_hint": ["backend/tests/", "backend/app/openapi/"]}]

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
endpoint بک‌اند بلااستفاده: POST /pr/from-project/{project_id}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /pr/from-project/{project_id}` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/pr/from-project/{project_id}`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /pr/from-project/{project_id}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/pr/from-project/{project_id}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 11
  id: 0384d4bf-a08f-48b6-95a2-0f9d5f9df8d8
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /profiles/{model_id}/update-score
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/model_profiles.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /profiles/{model_id}/update-score` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def update_score", "POST.*update-score"], "files_hint": ["backend/app/api/routes/model_profiles.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["update-score", "update_score"], "files_hint": ["backend/app/api/routes/model_profiles.py", "backend/app/api/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["update-score", "update_score"], "files_hint": ["backend/tests/", "backend/app/openapi/"]}]

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
endpoint بک‌اند بلااستفاده: POST /profiles/{model_id}/update-score

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/model_profiles.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /profiles/{model_id}/update-score` در `backend/app/api/routes/model_profiles.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/profiles/{model_id}/update-score`
- فایل: `backend/app/api/routes/model_profiles.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /profiles/{model_id}/update-score` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/profiles/{model_id}/update-score` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/model_profiles.py`
- `ruff check backend/app/api/routes/model_profiles.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 11
  id: 9214af19-5c4f-4eaa-ad69-f461a7664a17
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /smart-select
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/models.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /smart-select` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["POST /smart-select", "smart.select", "smartSelect"], "files_hint": ["backend/app/api/routes/models.py", "frontend/"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["smart.select", "smartSelect", "smart_select"], "files_hint": ["backend/app/api/routes/models.py", "frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["smart.select", "smartSelect", "smart_select"], "files_hint": ["backend/app/api/routes/models.py", "tests/", "openapi.json"]}]

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
endpoint بک‌اند بلااستفاده: POST /smart-select

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/models.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /smart-select` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/smart-select`
- فایل: `backend/app/api/routes/models.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /smart-select` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/smart-select` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/models.py`
- `ruff check backend/app/api/routes/models.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 9 از 11
  id: 4b131f30-a36c-4a32-8bc7-9acd6f3a3ec6
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /auto-build
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/orchestrator.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /auto-build` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["POST /auto-build", "auto-build"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["fetch.*auto-build", "axios.*auto-build", "apiClient.*auto-build", "auto-build"], "files_hint": ["frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["auto-build"], "files_hint": ["backend/tests/", "backend/app/api/openapi.json"]}]

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
endpoint بک‌اند بلااستفاده: POST /auto-build

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/orchestrator.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /auto-build` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/auto-build`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /auto-build` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/auto-build` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/orchestrator.py`
- `ruff check backend/app/api/routes/orchestrator.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 10 از 11
  id: 16f13037-6643-40a1-9a1e-9e953048d054
  عنوان اصلی: endpoint بک‌اند بلااستفاده: GET /file-content/{project_id}/{file_path:path}
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/orchestrator.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `GET /file-content/{project_id}/{file_path:path}` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def get_file_content", "file-content", "orphan", "internal", "deprecated"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["file-content", "connection", "internal", "deprecated", "remove", "delete"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["file-content", "test_file_content", "openapi", "yaml"], "files_hint": ["backend/app/api/routes/orchestrator.py", "backend/tests/", "backend/app/openapi/"]}]

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
endpoint بک‌اند بلااستفاده: GET /file-content/{project_id}/{file_path:path}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/orchestrator.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `GET /file-content/{project_id}/{file_path:path}` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/file-content/{project_id}/{file_path:path}`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `GET /file-content/{project_id}/{file_path:path}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/file-content/{project_id}/{file_path:path}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/orchestrator.py`
- `ruff check backend/app/api/routes/orchestrator.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 11 از 11
  id: 57b1b3d7-3409-4ea3-b8ea-132947696bcf
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /analyze-file/{file_id}
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/orchestrator.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /analyze-file/{file_id}` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def analyze_file", "POST.*analyze-file", "analyze-file"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["analyze-file", "analyze_file"], "files_hint": ["backend/app/api/routes/orchestrator.py", "frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["analyze-file", "analyze_file"], "files_hint": ["backend/tests/", "backend/app/api/openapi.json", "backend/app/api/openapi.yaml"]}]

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
endpoint بک‌اند بلااستفاده: POST /analyze-file/{file_id}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/orchestrator.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /analyze-file/{file_id}` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/analyze-file/{file_id}`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /analyze-file/{file_id}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/analyze-file/{file_id}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/orchestrator.py`
- `ruff check backend/app/api/routes/orchestrator.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
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
- در commit message: `merged-from: 05088e2f-a9fd-4c71-811d-74d09a5b8629, 5565b1ea-cbe1-4858-9850-b791c5f7bf92, 633abd7a-c942-43cc-91fd-60e35eadd353, 6838f513-dd7d-4f24-abdc-416a5bc791b5, df88b572-69f7-4265-92ac-2a870f3b6d2d, 248d1575-ca2a-4446-9cfd-7db48d43b59e, 0384d4bf-a08f-48b6-95a2-0f9d5f9df8d8, 9214af19-5c4f-4eaa-ad69-f461a7664a17, 4b131f30-a36c-4a32-8bc7-9acd6f3a3ec6, 16f13037-6643-40a1-9a1e-9e953048d054, 57b1b3d7-3409-4ea3-b8ea-132947696bcf`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Prompt

🧬 این یک تسک تلفیقی است — از 11 تسک منفرد ساخته شده.
📌 دلیل تلفیق (rationale توسط AI): تسک‌های 0، 1، 2، 3، 4، 5، 6، 7، 8، 9، 10 همگی به حذف endpointها یا routeهای بلااستفاده مربوط می‌شوند. تسک‌های 0 و 1 partial هستند و با not_doneهای این خوشه هم‌موضوع هستند.
🎯 theme: حذف endpointها و routeهای بلااستفاده در بک‌اند و فرانت‌اند
💎 estimated_difficulty: medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 1 از 11
  id: 05088e2f-a9fd-4c71-811d-74d09a5b8629
  عنوان اصلی: route فرانت‌اند بلااستفاده: /analysis
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - تأیید شد که `/analysis` orphan است (هیچ Link/router.push اشاره نمی‌کند) [verify_method=static] [verify_plan={"grep_patterns": ["/analysis", "router.push.*analysis", "Link.*analysis"], "files_hint": ["frontend/src/**/*.{tsx,ts,jsx,js}"]}]
  - یا navigation link اضافه شد، یا route حذف/redirect شد [verify_method=static] [verify_plan={"grep_patterns": ["/analysis", "router.push.*analysis", "Link.*analysis", "redirect.*analysis"], "files_hint": ["frontend/src/**/*.{tsx,ts,jsx,js}"]}]
  - تست navigation: کاربر بتواند به این صفحه (یا destination) برسد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='nav-analysis']"}, {"action": "]

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
route فرانت‌اند بلااستفاده: /analysis

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
route `/analysis` در فایل `` تعریف شده ولی هیچ `Link`، `router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.

## 🔍 جزئیات
- route path: `/analysis`
- فایل: ``
- علت: route exists in app router but no Link/router.push references it

## 🤔 چرا مهم است
route orphan یعنی صفحه‌ای که فقط با تایپ مستقیم URL قابل دسترسی است. یا فراموش شده یا منسوخ. باعث می‌شود کاربر هرگز به feature نرسد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد که `/analysis` orphan است (هیچ Link/router.push اشاره نمی‌کند)
- [ ] یا navigation link اضافه شد، یا route حذف/redirect شد
- [ ] تست navigation: کاربر بتواند به این صفحه (یا destination) برسد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: بررسی کن آیا این route از طریق dynamic URL (مثل sidebar config) اشاره می‌شود — grep روی `/analysis` در کل کدبیس بزن.
گام ۲: اگر orphan واقعی است، یا (الف) lin/redirect در navigation اصلی اضافه کن، یا (ب) فایل route را حذف کن.
گام ۳: اگر deprecated است، redirect 301 به route جدید بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف route ممکن است bookmark خارجی/SEO link خارجی را بشکند. اگر SEO اهمیت دارد، redirect بنویس نه delete.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 2 از 11
  id: 5565b1ea-cbe1-4858-9850-b791c5f7bf92
  عنوان اصلی: route فرانت‌اند بلااستفاده: /model-profiles
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: -

📋 acceptance_criteria کامل:
  - تأیید شد که `/model-profiles` orphan است (هیچ Link/router.push اشاره نمی‌کند) [verify_method=static] [verify_plan={"grep_patterns": ["Link.*to=\"/model-profiles\"", "router\\.push.*\"/model-profiles\"", "router\\.replace.*\"/model-profiles\""], "files_hint": ["frontend/**/*.{tsx,ts,jsx,js}"]}]
  - یا navigation link اضافه شد، یا route حذف/redirect شد [verify_method=static] [verify_plan={"grep_patterns": ["Link.*to=\"/model-profiles\"", "router\\.push.*\"/model-profiles\"", "router\\.replace.*\"/model-profiles\"", "redirect.*\"/model-profiles\""], "files_hint": ["frontend/**/*.{tsx,t]
  - تست navigation: کاربر بتواند به این صفحه (یا destination) برسد [verify_method=ui_interaction] [verify_plan={"base": "frontend", "ui_steps": [{"action": "navigate", "url": "/"}, {"action": "wait_for_load", "state": "networkidle"}, {"action": "click", "selector": "[data-testid='nav-link-model-profiles']"}, {]

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
route فرانت‌اند بلااستفاده: /model-profiles

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
route `/model-profiles` در فایل `` تعریف شده ولی هیچ `Link`، `router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.

## 🔍 جزئیات
- route path: `/model-profiles`
- فایل: ``
- علت: route exists in app router but no Link/router.push references it

## 🤔 چرا مهم است
route orphan یعنی صفحه‌ای که فقط با تایپ مستقیم URL قابل دسترسی است. یا فراموش شده یا منسوخ. باعث می‌شود کاربر هرگز به feature نرسد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] تأیید شد که `/model-profiles` orphan است (هیچ Link/router.push اشاره نمی‌کند)
- [ ] یا navigation link اضافه شد، یا route حذف/redirect شد
- [ ] تست navigation: کاربر بتواند به این صفحه (یا destination) برسد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: بررسی کن آیا این route از طریق dynamic URL (مثل sidebar config) اشاره می‌شود — grep روی `/model-profiles` در کل کدبیس بزن.
گام ۲: اگر orphan واقعی است، یا (الف) lin/redirect در navigation اصلی اضافه کن، یا (ب) فایل route را حذف کن.
گام ۳: اگر deprecated است، redirect 301 به route جدید بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest`
- `npm run build`
- `npm run lint`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف route ممکن است bookmark خارجی/SEO link خارجی را بشکند. اگر SEO اهمیت دارد، redirect بنویس نه delete.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: cleanup
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 3 از 11
  id: 633abd7a-c942-43cc-91fd-60e35eadd353
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /profiles/compare
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/analysis.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /profiles/compare` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def compare", "POST.*/profiles/compare", "profiles/compare"], "files_hint": ["backend/app/api/routes/analysis.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["profiles/compare", "fetch.*profiles/compare", "axios.*profiles/compare", "apiClient.*profiles/compare"], "files_hint": ["backend/app/api/routes/analysis.py", "frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["profiles/compare", "test.*compare", "compare.*test"], "files_hint": ["backend/tests/", "backend/app/api/routes/analysis.py"]}]

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
endpoint بک‌اند بلااستفاده: POST /profiles/compare

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /profiles/compare` در `backend/app/api/routes/analysis.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/profiles/compare`
- فایل: `backend/app/api/routes/analysis.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /profiles/compare` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/profiles/compare` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/analysis.py`
- `ruff check backend/app/api/routes/analysis.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 4 از 11
  id: 6838f513-dd7d-4f24-abdc-416a5bc791b5
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /imported/{project_id}/refresh
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /imported/{project_id}/refresh` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def refresh", "POST /imported/", "refresh"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["imported.*refresh", "refresh.*imported", "apiClient.*refresh", "fetch.*refresh"], "files_hint": ["frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["test.*refresh", "refresh.*test"], "files_hint": ["backend/tests/"]}]

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
endpoint بک‌اند بلااستفاده: POST /imported/{project_id}/refresh

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /imported/{project_id}/refresh` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/imported/{project_id}/refresh`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /imported/{project_id}/refresh` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/imported/{project_id}/refresh` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 5 از 11
  id: df88b572-69f7-4265-92ac-2a870f3b6d2d
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /parse-url
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /parse-url` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def parse_url", "POST.*/parse-url", "parse-url"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["parse-url", "parse_url"], "files_hint": ["backend/app/api/routes/github_import.py", "frontend/src"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["parse_url", "parse-url"], "files_hint": ["backend/tests", "backend/app/api/openapi.json", "backend/app/api/routes/github_import.py"]}]

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
endpoint بک‌اند بلااستفاده: POST /parse-url

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /parse-url` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/parse-url`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /parse-url` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/parse-url` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 6 از 11
  id: 248d1575-ca2a-4446-9cfd-7db48d43b59e
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /pr/from-project/{project_id}
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/github_import.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /pr/from-project/{project_id}` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def.*from_project", "POST.*/pr/from-project", "from-project"], "files_hint": ["backend/app/api/routes/github_import.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["from_project", "from-project", "github_import"], "files_hint": ["backend/app/api/routes/github_import.py", "frontend/src/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["from_project", "from-project", "github_import"], "files_hint": ["backend/tests/", "backend/app/openapi/"]}]

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
endpoint بک‌اند بلااستفاده: POST /pr/from-project/{project_id}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/github_import.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /pr/from-project/{project_id}` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/pr/from-project/{project_id}`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /pr/from-project/{project_id}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/pr/from-project/{project_id}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/github_import.py`
- `ruff check backend/app/api/routes/github_import.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 7 از 11
  id: 0384d4bf-a08f-48b6-95a2-0f9d5f9df8d8
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /profiles/{model_id}/update-score
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/model_profiles.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /profiles/{model_id}/update-score` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def update_score", "POST.*update-score"], "files_hint": ["backend/app/api/routes/model_profiles.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["update-score", "update_score"], "files_hint": ["backend/app/api/routes/model_profiles.py", "backend/app/api/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["update-score", "update_score"], "files_hint": ["backend/tests/", "backend/app/openapi/"]}]

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
endpoint بک‌اند بلااستفاده: POST /profiles/{model_id}/update-score

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/model_profiles.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /profiles/{model_id}/update-score` در `backend/app/api/routes/model_profiles.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/profiles/{model_id}/update-score`
- فایل: `backend/app/api/routes/model_profiles.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /profiles/{model_id}/update-score` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/profiles/{model_id}/update-score` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/model_profiles.py`
- `ruff check backend/app/api/routes/model_profiles.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 8 از 11
  id: 9214af19-5c4f-4eaa-ad69-f461a7664a17
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /smart-select
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/models.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /smart-select` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["POST /smart-select", "smart.select", "smartSelect"], "files_hint": ["backend/app/api/routes/models.py", "frontend/"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["smart.select", "smartSelect", "smart_select"], "files_hint": ["backend/app/api/routes/models.py", "frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["smart.select", "smartSelect", "smart_select"], "files_hint": ["backend/app/api/routes/models.py", "tests/", "openapi.json"]}]

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
endpoint بک‌اند بلااستفاده: POST /smart-select

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/models.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /smart-select` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/smart-select`
- فایل: `backend/app/api/routes/models.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /smart-select` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/smart-select` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/models.py`
- `ruff check backend/app/api/routes/models.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 9 از 11
  id: 4b131f30-a36c-4a32-8bc7-9acd6f3a3ec6
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /auto-build
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/orchestrator.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /auto-build` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["POST /auto-build", "auto-build"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["fetch.*auto-build", "axios.*auto-build", "apiClient.*auto-build", "auto-build"], "files_hint": ["frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["auto-build"], "files_hint": ["backend/tests/", "backend/app/api/openapi.json"]}]

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
endpoint بک‌اند بلااستفاده: POST /auto-build

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/orchestrator.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /auto-build` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/auto-build`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /auto-build` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/auto-build` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/orchestrator.py`
- `ruff check backend/app/api/routes/orchestrator.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 10 از 11
  id: 16f13037-6643-40a1-9a1e-9e953048d054
  عنوان اصلی: endpoint بک‌اند بلااستفاده: GET /file-content/{project_id}/{file_path:path}
  اولویت اصلی: medium
  وضعیت verify قبلی: pending
  فایل‌های دخیل: backend/app/api/routes/orchestrator.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `GET /file-content/{project_id}/{file_path:path}` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def get_file_content", "file-content", "orphan", "internal", "deprecated"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["file-content", "connection", "internal", "deprecated", "remove", "delete"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["file-content", "test_file_content", "openapi", "yaml"], "files_hint": ["backend/app/api/routes/orchestrator.py", "backend/tests/", "backend/app/openapi/"]}]

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
endpoint بک‌اند بلااستفاده: GET /file-content/{project_id}/{file_path:path}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/orchestrator.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `GET /file-content/{project_id}/{file_path:path}` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `GET`
- path: `/file-content/{project_id}/{file_path:path}`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `GET /file-content/{project_id}/{file_path:path}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/file-content/{project_id}/{file_path:path}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/orchestrator.py`
- `ruff check backend/app/api/routes/orchestrator.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
- اولویت: medium
- تخمین زمان: medium

✅ مراحل قبلاً done شده (در super-task به‌عنوان pre_done):
  (هیچ مرحله‌ای قبلاً done نشده بود)

🔧 مراحل remaining که در super-task باید انجام شوند:
  (همهٔ مراحل remaining هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تسک 11 از 11
  id: 57b1b3d7-3409-4ea3-b8ea-132947696bcf
  عنوان اصلی: endpoint بک‌اند بلااستفاده: POST /analyze-file/{file_id}
  اولویت اصلی: medium
  وضعیت verify قبلی: partial
  فایل‌های دخیل: backend/app/api/routes/orchestrator.py

📋 acceptance_criteria کامل:
  - مشخص شد endpoint `POST /analyze-file/{file_id}` در کدام دسته است (orphan/internal/deprecated) [verify_method=static] [verify_plan={"grep_patterns": ["def analyze_file", "POST.*analyze-file", "analyze-file"], "files_hint": ["backend/app/api/routes/orchestrator.py"]}]
  - اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف [verify_method=static] [verify_plan={"grep_patterns": ["analyze-file", "analyze_file"], "files_hint": ["backend/app/api/routes/orchestrator.py", "frontend/"]}]
  - اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد [verify_method=static] [verify_plan={"grep_patterns": ["analyze-file", "analyze_file"], "files_hint": ["backend/tests/", "backend/app/api/openapi.json", "backend/app/api/openapi.yaml"]}]

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
endpoint بک‌اند بلااستفاده: POST /analyze-file/{file_id}

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/orchestrator.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🌐 نقشهٔ وابستگی‌ها
این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ قبل از تغییر، grep روی نام symbol/path اصلی انجام شود.

## 🔍 Context و وضعیت فعلی
## 📋 شرح
endpoint `POST /analyze-file/{file_id}` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.

## 🔍 جزئیات
- method: `POST`
- path: `/analyze-file/{file_id}`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs

## 🤔 چرا مهم است
endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend feature روی آن broken است، یا (ب) admin/internal endpoint است که از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا (ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] مشخص شد endpoint `POST /analyze-file/{file_id}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: grep روی `/analyze-file/{file_id}` در frontend + scripts/ + docs/ — اگر caller هست، اتصال را drop شده اصلاح کن.
گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.
گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `python -m py_compile backend/app/api/routes/orchestrator.py`
- `ruff check backend/app/api/routes/orchestrator.py`
- `pytest -x`

## ⚠️ ریسک‌ها و موارد احتیاط
حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: audit
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
- در commit message: `merged-from: 05088e2f-a9fd-4c71-811d-74d09a5b8629, 5565b1ea-cbe1-4858-9850-b791c5f7bf92, 633abd7a-c942-43cc-91fd-60e35eadd353, 6838f513-dd7d-4f24-abdc-416a5bc791b5, df88b572-69f7-4265-92ac-2a870f3b6d2d, 248d1575-ca2a-4446-9cfd-7db48d43b59e, 0384d4bf-a08f-48b6-95a2-0f9d5f9df8d8, 9214af19-5c4f-4eaa-ad69-f461a7664a17, 4b131f30-a36c-4a32-8bc7-9acd6f3a3ec6, 16f13037-6643-40a1-9a1e-9e953048d054, 57b1b3d7-3409-4ea3-b8ea-132947696bcf`
- task_steps را با dependency-aware ordering مرتب کن
- هیچ کار قبلاً done شده‌ای نباید دوباره انجام شود
- هیچ خلاصه‌سازی نکن — جزئیات کامل از همهٔ منابع باید حفظ شوند


## Acceptance Criteria

1. تأیید شد که `/analysis` orphan است (هیچ Link/router.push اشاره نمی‌کند) _(verify: static)_
2. یا navigation link اضافه شد، یا route حذف/redirect شد _(verify: static)_
3. تست navigation: کاربر بتواند به این صفحه (یا destination) برسد _(verify: ui_interaction)_
4. تأیید شد که `/model-profiles` orphan است (هیچ Link/router.push اشاره نمی‌کند) _(verify: static)_
5. مشخص شد endpoint `POST /profiles/compare` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
6. اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف _(verify: static)_
7. اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد _(verify: static)_
8. مشخص شد endpoint `POST /imported/{project_id}/refresh` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
9. مشخص شد endpoint `POST /parse-url` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
10. مشخص شد endpoint `POST /pr/from-project/{project_id}` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
11. مشخص شد endpoint `POST /profiles/{model_id}/update-score` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
12. مشخص شد endpoint `POST /smart-select` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
13. مشخص شد endpoint `POST /auto-build` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
14. مشخص شد endpoint `GET /file-content/{project_id}/{file_path:path}` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_
15. مشخص شد endpoint `POST /analyze-file/{file_id}` در کدام دسته است (orphan/internal/deprecated) _(verify: static)_

## Task Steps

### Step 1: بررسی و حذف/اصلاح route فرانت‌اند بلااستفاده: /analysis
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی orphan بودن route /analysis در فرانت‌اند (Next.js) و سپس حذف یا اضافه کردن navigation link به آن است. ابتدا با grep روی کل کدبیس فرانت‌اند بررسی می‌شود که آیا هیچ Link، router.push، یا ارجاع دیگری به /analysis وجود دارد. اگر orphan تشخیص داده شد، یا یک navigation link معتبر اضافه می‌شود، یا route به طور کامل حذف می‌شود. در صورت حذف، فایل route و هرگونه import مرتبط پاک می‌شود. در صورت deprecated بودن، redirect 301 به route جدید نوشته می‌شود. این مرحله شامل تغییرات بک‌اند یا تست‌های integration نیست.
**Excerpt:**
```
route فرانت‌اند بلااستفاده: /analysis
route `/analysis` در فایل `` تعریف شده ولی هیچ `Link`، `router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.
- route path: `/analysis`
- فایل: ``
- علت: route exists in app router but no Link/router.push references it
- [ ] تأیید شد که `/analysis` orphan است (هیچ Link/router.push اشاره نمی‌کند)
- [ ] یا navigation link اضافه شد، یا route حذف/redirect شد
- [ ] تست navigation: کاربر بتواند به این صفحه (یا destination) برسد
```

### Step 2: بررسی و حذف/اصلاح route فرانت‌اند بلااستفاده: /model-profiles
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی orphan بودن route /model-profiles در فرانت‌اند است. با grep روی کل کدبیس فرانت‌اند (frontend/src) بررسی می‌شود که آیا هیچ Link، router.push، router.replace یا ارجاع دیگری به /model-profiles وجود دارد. اگر orphan تشخیص داده شد، یا navigation link اضافه می‌شود، یا route حذف/redirect می‌شود. در صورت حذف، فایل route و importهای مرتبط پاک می‌شوند. این مرحله مستقل از سایر مراحل است و فقط به route /model-profiles می‌پردازد.
**Excerpt:**
```
route فرانت‌اند بلااستفاده: /model-profiles
route `/model-profiles` در فایل `` تعریف شده ولی هیچ `Link`، `router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.
- route path: `/model-profiles`
- فایل: ``
- علت: route exists in app router but no Link/router.push references it
- [ ] تأیید شد که `/model-profiles` orphan است (هیچ Link/router.push اشاره نمی‌کند)
- [ ] یا navigation link اضافه شد، یا route حذف/redirect شد
- [ ] تست navigation: کاربر بتواند به این صفحه (یا destination) برسد
```

### Step 3: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /profiles/compare
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /profiles/compare در فایل backend/app/api/routes/analysis.py است. ابتدا با grep روی کل کدبیس (frontend, scripts, docs) مشخص می‌شود که آیا هیچ caller فرانت‌اندی (fetch, axios, apiClient) به این endpoint اشاره می‌کند. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal به آن اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI نیز به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /profiles/compare
endpoint `POST /profiles/compare` در `backend/app/api/routes/analysis.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/profiles/compare`
- فایل: `backend/app/api/routes/analysis.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /profiles/compare` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 4: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /imported/{project_id}/refresh
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /imported/{project_id}/refresh در فایل backend/app/api/routes/github_import.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /imported/{project_id}/refresh
endpoint `POST /imported/{project_id}/refresh` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/imported/{project_id}/refresh`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /imported/{project_id}/refresh` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 5: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /parse-url
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /parse-url در فایل backend/app/api/routes/github_import.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /parse-url
endpoint `POST /parse-url` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/parse-url`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /parse-url` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 6: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /pr/from-project/{project_id}
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /pr/from-project/{project_id} در فایل backend/app/api/routes/github_import.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /pr/from-project/{project_id}
endpoint `POST /pr/from-project/{project_id}` در `backend/app/api/routes/github_import.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/pr/from-project/{project_id}`
- فایل: `backend/app/api/routes/github_import.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /pr/from-project/{project_id}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 7: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /profiles/{model_id}/update-score
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /profiles/{model_id}/update-score در فایل backend/app/api/routes/model_profiles.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /profiles/{model_id}/update-score
endpoint `POST /profiles/{model_id}/update-score` در `backend/app/api/routes/model_profiles.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/profiles/{model_id}/update-score`
- فایل: `backend/app/api/routes/model_profiles.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /profiles/{model_id}/update-score` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 8: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /smart-select
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /smart-select در فایل backend/app/api/routes/models.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /smart-select
endpoint `POST /smart-select` در `backend/app/api/routes/models.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/smart-select`
- فایل: `backend/app/api/routes/models.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /smart-select` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 9: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /auto-build
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /auto-build در فایل backend/app/api/routes/orchestrator.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /auto-build
endpoint `POST /auto-build` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/auto-build`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /auto-build` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 10: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: GET /file-content/{project_id}/{file_path:path}
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint GET /file-content/{project_id}/{file_path:path} در فایل backend/app/api/routes/orchestrator.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: GET /file-content/{project_id}/{file_path:path}
endpoint `GET /file-content/{project_id}/{file_path:path}` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `GET`
- path: `/file-content/{project_id}/{file_path:path}`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `GET /file-content/{project_id}/{file_path:path}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```

### Step 11: بررسی و حذف/اصلاح endpoint بک‌اند بلااستفاده: POST /analyze-file/{file_id}
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی endpoint POST /analyze-file/{file_id} در فایل backend/app/api/routes/orchestrator.py است. با grep روی frontend, scripts, docs مشخص می‌شود که آیا caller فرانت‌اندی وجود دارد. اگر orphan تشخیص داده شد، یا connection بازسازی می‌شود، یا تگ internal اضافه می‌شود، یا endpoint به همراه تست‌های مرتبط حذف می‌شود. در صورت حذف، OpenAPI به‌روزرسانی می‌شود. این مرحله فقط به این endpoint خاص می‌پردازد.
**Excerpt:**
```
endpoint بک‌اند بلااستفاده: POST /analyze-file/{file_id}
endpoint `POST /analyze-file/{file_id}` در `backend/app/api/routes/orchestrator.py` تعریف شده ولی هیچ `fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.
- method: `POST`
- path: `/analyze-file/{file_id}`
- فایل: `backend/app/api/routes/orchestrator.py`
- علت: no frontend fetch + no recent call in logs
- [ ] مشخص شد endpoint `POST /analyze-file/{file_id}` در کدام دسته است (orphan/internal/deprecated)
- [ ] اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف
- [ ] اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد
```
