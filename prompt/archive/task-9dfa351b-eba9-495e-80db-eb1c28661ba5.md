---
task_id: 9dfa351b-eba9-495e-80db-eb1c28661ba5
title: حذف کد مرده و dead code در route‌های backend (analysis.py, project_health.py, model_profiles.py)
type: refactor
priority: medium
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-14T19:48:10.536995+00:00'
updated_at: '2026-05-29T16:43:07.334007+00:00'
archived: true
archived_at: '2026-05-17T10:19:29.514411+00:00'
target_files:
- backend/app/api/routes/project_health.py
- backend/app/api/routes/model_profiles.py
- backend/app/api/routes/analysis.py
---

# حذف کد مرده و dead code در route‌های backend (analysis.py, project_health.py, model_profiles.py)

## Raw Idea

فایل‌های analysis.py (707 خط)، project_health.py (1648 خط) و model_profiles.py (807 خط) حاوی مقادیر زیادی کد مرده، endpoint‌های deprecated و منطق تکراری هستند. در project_health.py، کل endpoint‌ها با هدر Deprecation/Sunset علامت‌گذاری شده‌اند (خطوط 64-81) و به /oversight مهاجرت کرده‌اند. در analysis.py، endpoint‌های /reports/{report_id}/download (خط 328) و /reports (خط 271) با وجود مهاجرت به oversight هنوز فعال هستند. در model_profiles.py، fallback data (خطوط 90-97) و default profiles (خط 191) کد مرده‌ای هستند که هرگز استفاده نمی‌شوند چون profiler از دیتابیس می‌خواند.

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
حذف کد مرده و dead code در route‌های backend (analysis.py, project_health.py, model_profiles.py)

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/project_health.py:64-81` — `deprecated_health_endpoint` — کل middleware deprecated — باید endpoint‌ها حذف شوند
  ```python
  def deprecated_health_endpoint(request: _DepReq, response: _DepResp):
      """Dependency برای علامت‌گذاری endpoint های Health به‌عنوان deprecated."""
      try:
          response.headers["Deprecation"] = "true"
          response.headers["Sunset"] = "Wed, 31 Dec 2026 23:59:59 GMT"
  ```
- `backend/app/api/routes/model_profiles.py:90-97` — `defaultProfiles` — داده‌های پیش‌فرض که هرگز استفاده نمی‌شوند — کد مرده
  ```python
  const defaultProfiles: ModelProfile[] = [
      {model_id: "gpt-4", provider: "openai", display_name: "GPT-4", tier: "S", overall_score: 92.5, ...},
      ...
    ];
  ```
- `backend/app/api/routes/analysis.py:328-400` — `download_analysis_report` — endpoint download با 400 خط کد — اگر مهاجرت به oversight کامل شده، باید حذف شود
  ```python
  @router.get("/reports/{report_id}/download")
  async def download_analysis_report(
      report_id: str,
      format: str = "json"  # json, csv, txt, md
  ):
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🧱 پشتهٔ فناوری و معماری
FastAPI + SQLAlchemy + SQLite

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/api/routes/oversight.py` (سطر 1) — جایگزین project_health.py — همه قابلیت‌ها اینجا هستند
- `backend/app/services/oversight_service.py` (سطر 1) — سرویس اصلی که جایگزین health analyzer شده

## 🌐 نقشهٔ وابستگی‌ها
حذف این کدها روی 3 فایل route و 2 سرویس (project_health_analyzer, model_profiler) اثر می‌گذارد. oversight_service.py وابستگی جدید است.

## 🔍 Context و وضعیت فعلی
فایل‌های analysis.py (707 خط)، project_health.py (1648 خط) و model_profiles.py (807 خط) حاوی مقادیر زیادی کد مرده، endpoint‌های deprecated و منطق تکراری هستند. در project_health.py، کل endpoint‌ها با هدر Deprecation/Sunset علامت‌گذاری شده‌اند (خطوط 64-81) و به /oversight مهاجرت کرده‌اند. در analysis.py، endpoint‌های /reports/{report_id}/download (خط 328) و /reports (خط 271) با وجود مهاجرت به oversight هنوز فعال هستند. در model_profiles.py، fallback data (خطوط 90-97) و default profiles (خط 191) کد مرده‌ای هستند که هرگز استفاده نمی‌شوند چون profiler از دیتابیس می‌خواند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] اعمال تغییر بدون شکستن تست‌های موجود
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. حذف endpoint‌های deprecated در project_health.py که به /oversight مهاجرت کرده‌اند (health/export, debug/single-file-test, health/analyze). 2. حذف fallback data و default profiles در model_profiles.py. 3. حذف endpoint download در analysis.py اگر دیگر استفاده نمی‌شود. 4. جایگزینی منطق تکراری merge issues در project_health.py (خطوط 203-283) با یک سرویس مشترک.

## 💡 نمونه‌های قبل/بعد
**حذف deprecated endpoint**

_قبل:_
```
@router.get("/{project_id}/health/export")
async def
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
- نوع: refactor
- اولویت: medium
- تخمین زمان: medium

## Acceptance Criteria

1. اعمال تغییر بدون شکستن تست‌های موجود _(verify: backend_test)_
2. linter بدون warning عبور می‌کند _(verify: static)_
3. type-check موفق است _(verify: static)_

## Task Steps

### Step 1: حذف endpoint‌های deprecated در project_health.py و middleware مربوطه
**Status:** `done` (100%)
**Scope:** این مرحله شامل حذف کامل middleware `deprecated_health_endpoint` (خطوط 64-81) و تمام endpoint‌هایی است که از این middleware استفاده می‌کنند در فایل `backend/app/api/routes/project_health.py`. همچنین حذف importهای مرتبط با `_DepReq` و `_DepResp`. خارج از این مرحله: تغییر مسیر endpoint‌ها به /oversight (این کار قبلاً انجام شده)، حذف endpoint‌های analysis.py یا model_profiles.py. نکته حیاتی: قبل از حذف، بررسی شود که هیچ کلاینتی هنوز از این endpoint‌ها استفاده نمی‌کند و مهاجرت به oversight کامل شده است.
**Excerpt:**
```
در project_health.py، کل endpoint‌ها با هدر Deprecation/Sunset علامت‌گذاری شده‌اند (خطوط 64-81) و به /oversight مهاجرت کرده‌اند. ... `backend/app/api/routes/project_health.py:64-81` — `deprecated_health_endpoint` — کل middleware deprecated — باید endpoint‌ها حذف شوند
```

### Step 2: حذف endpoint /reports/{report_id}/download در analysis.py
**Status:** `done` (100%)
**Scope:** این مرحله شامل حذف کامل endpoint `download_analysis_report` در خطوط 328-400 فایل `backend/app/api/routes/analysis.py` است. این endpoint با 400 خط کد برای دانلود گزارش‌ها با فرمت‌های مختلف (json, csv, txt, md) طراحی شده بود. خارج از این مرحله: حذف endpoint /reports (خط 271) که در مرحله بعدی انجام می‌شود. نکته حیاتی: بررسی شود که تابع download_analysis_report در جای دیگری import یا استفاده نشده باشد.
**Excerpt:**
```
در analysis.py، endpoint‌های /reports/{report_id}/download (خط 328) و /reports (خط 271) با وجود مهاجرت به oversight هنوز فعال هستند. ... `backend/app/api/routes/analysis.py:328-400` — `download_analysis_report` — endpoint download با 400 خط کد — اگر مهاجرت به oversight کامل شده، باید حذف شود
```

### Step 3: حذف endpoint /reports در analysis.py
**Status:** `done` (100%)
**Scope:** این مرحله شامل حذف کامل endpoint مربوط به `/reports` در خط 271 فایل `backend/app/api/routes/analysis.py` است. این endpoint لیست گزارش‌ها را برمی‌گرداند. خارج از این مرحله: حذف endpoint /reports/{report_id}/download که در مرحله قبل انجام شد. نکته حیاتی: بررسی شود که این endpoint در جای دیگری import یا استفاده نشده باشد و مهاجرت به oversight کامل شده باشد.
**Excerpt:**
```
در analysis.py، endpoint‌های /reports/{report_id}/download (خط 328) و /reports (خط 271) با وجود مهاجرت به oversight هنوز فعال هستند.
```

### Step 4: حذف fallback data در model_profiles.py (خطوط 90-97)
**Status:** `done` (100%)
**Scope:** این مرحله شامل حذف متغیر `defaultProfiles` در خطوط 90-97 فایل `backend/app/api/routes/model_profiles.py` است. این داده‌های پیش‌فرض شامل پروفایل‌های مدل‌های مختلف (gpt-4, claude-3, gemini-pro, llama-3) با امتیاز و tier هستند. خارج از این مرحله: حذف default profiles در خط 191 که در مرحله بعدی انجام می‌شود. نکته حیاتی: بررسی شود که این متغیر در جای دیگری import یا استفاده نشده باشد.
**Excerpt:**
```
در model_profiles.py، fallback data (خطوط 90-97) و default profiles (خط 191) کد مرده‌ای هستند که هرگز استفاده نمی‌شوند چون profiler از دیتابیس می‌خواند. ... `backend/app/api/routes/model_profiles.py:90-97` — `defaultProfiles` — داده‌های پیش‌فرض که هرگز استفاده نمی‌شوند — کد مرده
```

### Step 5: حذف default profiles در model_profiles.py (خط 191)
**Status:** `done` (100%)
**Scope:** این مرحله شامل حذف کد مربوط به default profiles در خط 191 فایل `backend/app/api/routes/model_profiles.py` است. این کد مرده‌ای است که هرگز استفاده نمی‌شود چون profiler از دیتابیس می‌خواند. خارج از این مرحله: حذف fallback data در خطوط 90-97 که در مرحله قبل انجام شد. نکته حیاتی: بررسی شود که این کد در جای دیگری استفاده نشده باشد.
**Excerpt:**
```
در model_profiles.py، fallback data (خطوط 90-97) و default profiles (خط 191) کد مرده‌ای هستند که هرگز استفاده نمی‌شوند چون profiler از دیتابیس می‌خواند.
```

### Step 6: بررسی و حذف importهای غیرضروری در فایل‌های اصلاح‌شده
**Status:** `done` (100%)
**Scope:** این مرحله شامل بررسی و حذف importهای غیرضروری در فایل‌های `backend/app/api/routes/project_health.py`، `backend/app/api/routes/analysis.py` و `backend/app/api/routes/model_profiles.py` است که پس از حذف کدهای مرده، دیگر استفاده نمی‌شوند. خارج از این مرحله: تغییر در منطق business یا اضافه کردن کد جدید. نکته حیاتی: فقط importهایی که مستقیماً به کدهای حذف‌شده مرتبط هستند باید حذف شوند.
**Excerpt:**
```
فایل‌های analysis.py (707 خط)، project_health.py (1648 خط) و model_profiles.py (807 خط) حاوی مقادیر زیادی کد مرده، endpoint‌های deprecated و منطق تکراری هستند.
```

### Step 7: اجرای تست‌های موجود و رفع خطاهای ناشی از حذف کد
**Status:** `done` (100%)
**Scope:** این مرحله شامل اجرای تمام تست‌های موجود در پروژه برای اطمینان از عدم شکستن functionality پس از حذف کدهای مرده است. اگر تست‌هایی به endpoint‌های حذف‌شده اشاره دارند، باید آن‌ها را به‌روزرسانی یا حذف کرد. خارج از این مرحله: نوشتن تست‌های جدید. نکته حیاتی: تمام تست‌ها باید پاس شوند قبل از اتمام این مرحله.
**Excerpt:**
```
فایل‌های analysis.py (707 خط)، project_health.py (1648 خط) و model_profiles.py (807 خط) حاوی مقادیر زیادی کد مرده، endpoint‌های deprecated و منطق تکراری هستند.
```
