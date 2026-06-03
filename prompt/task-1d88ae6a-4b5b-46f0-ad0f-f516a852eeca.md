---
task_id: 1d88ae6a-4b5b-46f0-ad0f-f516a852eeca
title: '[Effectiveness] عدم وجود معیارهای عملکردی برای سرویس AI Manager'
type: logic_audit
priority: high
execution_priority: 2000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-15T16:45:07.767028+00:00'
updated_at: '2026-06-03T17:20:21.001829+00:00'
---

# [Effectiveness] عدم وجود معیارهای عملکردی برای سرویس AI Manager

## Raw Idea

## 🎯 هدف مطلوب (outcome target)
پس از پیاده‌سازی معیارهای latency و throughput، 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند

## 📊 وضعیت فعلی
AI Manager فاقد logging و monitoring برای زمان پاسخ‌دهی و نرخ موفقیت fallback است. تنها error_rate صفر گزارش شده که کافی نیست.

## 🛠 اقدام پیشنهادی
اضافه کردن metrics برای latency هر مدل، نرخ موفقیت fallback، و throughput کلی. پیاده‌سازی alerting برای زمان پاسخ‌دهی بیش از 2 ثانیه.

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.
---
[scan #2 at 2026-05-15T17:42:53.001285+00:00]
## 🎯 هدف مطلوب (outcome target)
پس از پیاده‌سازی معیارهای latency و throughput، 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند.

## 📊 وضعیت فعلی
سیستم error_rate پایینی دارد (0.01) اما هیچ معیاری برای latency یا throughput سرویس AI Manager ثبت نشده است. صرفاً لاگ‌های موفقیت (INFO) وجود دا

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
[Effectiveness] عدم وجود معیارهای عملکردی برای سرویس AI Manager

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
Stack: fastapi, nextjs.

## 🔍 Context و وضعیت فعلی
## 🎯 هدف مطلوب (outcome target)
پس از پیاده‌سازی معیارهای latency و throughput، 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند

## 📊 وضعیت فعلی
AI Manager فاقد logging و monitoring برای زمان پاسخ‌دهی و نرخ موفقیت fallback است. تنها error_rate صفر گزارش شده که کافی نیست.

## 🛠 اقدام پیشنهادی
اضافه کردن metrics برای latency هر مدل، نرخ موفقیت fallback، و throughput کلی. پیاده‌سازی alerting برای زمان پاسخ‌دهی بیش از 2 ثانیه.

## ⚙️ ماهیت این finding
این یک effectiveness issue است — کد ممکن است syntactically کار کند ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] outcome target به‌صورت measurable بازنویسی شد
- [ ] کد تغییر کرد تا outcome target محقق شود
- [ ] test E2E که outcome را اندازه می‌گیرد عبور می‌کند
- [ ] metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن (مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).
گام ۲: کد را تغییر بده تا outcome محقق شود.
گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## 🧪 دستورات اعتبارسنجی
- `pytest -k 'outcome or e2e'`

## ⚠️ ریسک‌ها و موارد احتیاط
بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد metric ها را compare کن.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: logic_audit
- اولویت: high
- تخمین زمان: medium

## Acceptance Criteria

1. outcome target به‌صورت measurable بازنویسی شد _(verify: static)_
2. کد تغییر کرد تا outcome target محقق شود _(verify: static)_
3. test E2E که outcome را اندازه می‌گیرد عبور می‌کند _(verify: backend_test)_
4. metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد _(verify: static)_

## Task Steps

### Step 1: بررسی وضعیت فعلی repo برای وجود metrics و logging در AI Manager
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل جستجوی کامل در repo برای یافتن هرگونه پیاده‌سازی موجود از metrics، logging، monitoring، latency tracking، fallback success rate، throughput، و alerting در بخش AI Manager است. باید فایل‌های مرتبط با AI Manager (مانند ai_manager.py، services/ai_manager.py، یا هر فایل دیگری که مدیریت AI را انجام می‌دهد) شناسایی شوند. همچنین باید بررسی شود که آیا endpointهایی برای metrics وجود دارند، آیا middlewareای برای logging زمان پاسخ وجود دارد، و آیا ساختار داده‌ای برای ذخیره latency هر مدل وجود دارد. این مرحله شامل هیچ تغییری در کد نمی‌شود و صرفاً یک audit است. نکته حیاتی: اگر هر یک از این موارد از قبل وجود دارند، باید دقیقاً مستند شوند تا در مراحل بعدی دوباره ساخته نشوند.
**Excerpt:**
```
AI Manager فاقد logging و monitoring برای زمان پاسخ‌دهی و نرخ موفقیت fallback است. تنها error_rate صفر گزارش شده که کافی نیست. ... پیش از شروع، با grep/search و خواندن فایل‌های مرتبط بررسی کن که چه چیزی از قبل وجود دارد. اگر یک قابلیت/فایل/تابع از قبل موجود است: آن را دوباره نساز؛ فقط موارد ناقص یا اشتباه را اصلاح/تکمیل کن.
```

### Step 2: اضافه کردن dataclass/struct برای ذخیره latency هر مدل AI
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک ساختار داده (مانند dataclass در Python یا interface در TypeScript) برای ذخیره latency هر مدل AI است. این ساختار باید شامل فیلدهای زیر باشد: model_name (str)، latency_ms (float)، timestamp (datetime)، success (bool)، fallback_used (bool). این ساختار در فایل مناسب (مثلاً models/metrics.py یا types/metrics.ts) قرار می‌گیرد. خارج از این مرحله: پیاده‌سازی logic ثبت metrics، endpointها، یا alerting. نکته حیاتی: این ساختار باید immutable باشد (با frozen=True در dataclass یا readonly در TypeScript) تا از تغییر ناخواسته جلوگیری شود.
**Excerpt:**
```
اضافه کردن metrics برای latency هر مدل، نرخ موفقیت fallback، و throughput کلی. ... AI Manager فاقد logging و monitoring برای زمان پاسخ‌دهی و نرخ موفقیت fallback است.
```

### Step 3: اضافه کردن middleware برای ثبت latency هر درخواست AI
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک middleware (در FastAPI به صورت dependency یا middleware) است که زمان شروع و پایان هر درخواست به AI Manager را اندازه‌گیری کرده و latency را محاسبه می‌کند. این middleware باید از ساختار داده مرحله ۲ استفاده کند و metrics را در یک لیست درون‌حافظه‌ای (in-memory list) ذخیره کند. همچنین باید model_name را از request body استخراج کند (یا از یک هدر مخصوص). خارج از این مرحله: ذخیره‌سازی دائمی metrics در دیتابیس، alerting، یا نمایش UI. نکته حیاتی: این middleware باید non-blocking باشد و latency اضافی ناچیزی (کمتر از 1ms) به درخواست اضافه کند.
**Excerpt:**
```
اضافه کردن metrics برای latency هر مدل ... پیاده‌سازی alerting برای زمان پاسخ‌دهی بیش از 2 ثانیه. ... 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند
```

### Step 4: اضافه کردن endpoint GET /metrics برای مشاهده metrics
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک endpoint جدید در FastAPI با مسیر GET /metrics است که metrics جمع‌آوری شده (latency هر مدل، throughput کلی، نرخ موفقیت fallback) را به صورت JSON برمی‌گرداند. این endpoint باید آمار زیر را محاسبه کند: میانگین latency برای هر مدل، p95 latency، تعداد کل درخواست‌ها، تعداد fallbackها، و نرخ موفقیت fallback. خارج از این مرحله: authentication/authorization برای این endpoint، alerting، یا نمایش UI. نکته حیاتی: این endpoint باید از لیست درون‌حافظه‌ای مرحله ۳ بخواند و نباید metrics را پاک کند (مگر اینکه پارامتر reset=true داده شود).
**Excerpt:**
```
اضافه کردن metrics برای latency هر مدل، نرخ موفقیت fallback، و throughput کلی. ... 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند
```

### Step 5: پیاده‌سازی tracking نرخ موفقیت fallback
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اضافه کردن logic به AI Manager است که هر بار که fallback به مدل دیگری انجام می‌شود، این رویداد را ثبت کند. باید مشخص شود که fallback موفق بوده (مدل جایگزین پاسخ داده) یا ناموفق (هیچ مدلی پاسخ نداده). این اطلاعات باید به ساختار داده AIMetric اضافه شود (فیلد fallback_used و success). همچنین باید یک counter جداگانه برای تعداد کل fallbackها و تعداد fallbackهای موفق نگه داشته شود. خارج از این مرحله: alerting بر اساس نرخ fallback، یا نمایش UI. نکته حیاتی: fallback success rate باید به صورت percentage محاسبه شود و در endpoint metrics قابل مشاهده باشد.
**Excerpt:**
```
نرخ موفقیت fallback ... AI Manager فاقد logging و monitoring برای ... نرخ موفقیت fallback است. ... اضافه کردن metrics برای ... نرخ موفقیت fallback
```

### Step 6: پیاده‌سازی tracking throughput کلی
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اضافه کردن یک counter برای تعداد کل درخواست‌های AI در یک بازه زمانی (مثلاً ۱ دقیقه) است. throughput باید به صورت requests per second (RPS) محاسبه شود. این counter باید در endpoint /metrics قابل مشاهده باشد. همچنین باید یک sliding window (مثلاً ۵ دقیقه) برای محاسبه throughput لحظه‌ای پیاده‌سازی شود. خارج از این مرحله: ذخیره‌سازی تاریخی throughput، یا alerting. نکته حیاتی: throughput باید به صورت real-time محاسبه شود و overhead ناچیزی داشته باشد.
**Excerpt:**
```
throughput کلی ... اضافه کردن metrics برای ... throughput کلی
```

### Step 7: پیاده‌سازی alerting برای latency بیش از ۲ ثانیه
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل ایجاد یک مکانیزم alerting است که وقتی latency یک درخواست AI از ۲ ثانیه بیشتر می‌شود، یک هشدار ثبت کند. این alerting می‌تواند به صورت logging با سطح WARNING، ارسال به یک سرویس خارجی (مانند Slack یا email) از طریق webhook، یا ذخیره در یک فایل جداگانه باشد. باید threshold 2 ثانیه قابل تنظیم باشد (از طریق environment variable). خارج از این مرحله: UI برای نمایش alerts، یا integration با سرویس‌های خاص. نکته حیاتی: alerting نباید performance را تحت تأثیر قرار دهد و باید به صورت async انجام شود.
**Excerpt:**
```
پیاده‌سازی alerting برای زمان پاسخ‌دهی بیش از 2 ثانیه. ... 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند
```

### Step 8: اضافه کردن logging برای metrics در production (فایل لاگ یا سرویس خارجی)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اضافه کردن logging دائمی برای metrics است تا در production قابل بررسی باشند. metrics باید در یک فایل لاگ جداگانه (مثلاً ai_metrics.log) یا از طریق یک سرویس logging خارجی (مانند ELK، Datadog، یا Prometheus) ثبت شوند. هر metric باید شامل timestamp، model_name، latency_ms، success، fallback_used باشد. خارج از این مرحله: integration با سرویس‌های خاص (فقط یک interface generic). نکته حیاتی: logging باید به صورت batch انجام شود (هر ۱۰ ثانیه یا هر ۱۰۰ metric) تا overhead کاهش یابد.
**Excerpt:**
```
metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد ... AI Manager فاقد logging و monitoring برای زمان پاسخ‌دهی و نرخ موفقیت fallback است.
```

### Step 9: نوشتن تست E2E برای اندازه‌گیری outcome target (95% درخواست‌ها زیر ۲ ثانیه)
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن یک تست E2E (با pytest یا ابزار مشابه) است که ۱۰۰ درخواست به AI Manager ارسال می‌کند و بررسی می‌کند که حداقل ۹۵٪ آن‌ها latency کمتر از ۲ ثانیه داشته باشند. تست باید از endpoint /metrics برای جمع‌آوری آمار استفاده کند. خارج از این مرحله: تست‌های unit برای تک تک توابع. نکته حیاتی: تست باید realistic باشد و از مدل‌های واقعی (یا mockهای realistic) استفاده کند. اگر مدل‌های واقعی در دسترس نیستند، باید mockهایی با latency شبیه‌سازی شده استفاده شوند.
**Excerpt:**
```
test E2E که outcome را اندازه می‌گیرد عبور می‌کند ... 95% درخواست‌های AI باید در کمتر از 2 ثانیه پاسخ داده شوند ... outcome target به‌صورت measurable بازنویسی شد
```

### Step 10: نوشتن تست‌های unit برای توابع metrics و alerting
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل نوشتن تست‌های unit برای توابع جدید ایجاد شده است: تابع محاسبه latency، تابع ثبت fallback، تابع محاسبه throughput، و تابع alerting. هر تابع باید حداقل ۲ تست داشته باشد: یک تست برای حالت عادی و یک تست برای edge case (مثلاً latency صفر، fallback ناموفق، throughput صفر). خارج از این مرحله: تست‌های E2E یا integration. نکته حیاتی: تست‌ها باید از mock استفاده کنند و به سرویس‌های خارجی وابسته نباشند.
**Excerpt:**
```
هیچ تستی fail نمی‌شود (npm run test / pytest) ... linter بدون warning عبور می‌کند ... type-check موفق است
```

### Step 11: بررسی و رفع linting و type-check issues
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل اجرای linter (مثلاً flake8 یا pylint برای Python، eslint برای TypeScript) و type-checker (mypy برای Python، tsc برای TypeScript) بر روی تمام فایل‌های جدید و تغییر یافته است. هر warning یا error باید رفع شود. خارج از این مرحله: تغییر logic یا اضافه کردن feature جدید. نکته حیاتی: اگر linter rule خاصی با پروژه هماهنگ نیست، می‌توان آن rule را در config غیرفعال کرد، اما باید دلیل آن مستند شود.
**Excerpt:**
```
linter بدون warning عبور می‌کند ... type-check موفق است (tsc --noEmit / ...)
```

### Step 12: به‌روزرسانی documentation برای metrics و alerting
**Status:** `not_done` (0%)
**Scope:** این مرحله شامل به‌روزرسانی README یا فایل‌های documentation موجود (مثلاً docs/metrics.md) برای توضیح metrics جدید، endpoint /metrics، و مکانیزم alerting است. باید نحوه استفاده از endpoint، تفسیر metrics، و تنظیم threshold alerting توضیح داده شود. خارج از این مرحله: نوشتن documentation از صفر (فقط به‌روزرسانی). نکته حیاتی: documentation باید به زبان فارسی یا انگلیسی (بر اساس پروژه) نوشته شود و شامل مثال‌های curl باشد.
**Excerpt:**
```
هدف مطلوب (outcome target) ... پس از پیاده‌سازی معیارهای latency و throughput ...
```
