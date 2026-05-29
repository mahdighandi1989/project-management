---
task_id: e6b2fbcb-bf87-4e86-950e-b3108ecc7f43
title: سیستم جامع ردیابی و گزارش‌دهی مصرف توکن مدل‌های AI با هشدار شارژ و تشخیص نشتی
type: feature_request
priority: high
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-11T11:01:07.514797+00:00'
updated_at: '2026-05-29T16:41:23.382369+00:00'
archived: true
archived_at: '2026-05-11T15:18:03.812049+00:00'
target_files:
- backend/app/services/ai_manager.py
- backend/app/services/openai_service.py
- backend/app/services/claude_service.py
- backend/app/models/ai_log.py
- backend/app/api/routes/models.py
---

# سیستم جامع ردیابی و گزارش‌دهی مصرف توکن مدل‌های AI با هشدار شارژ و تشخیص نشتی

## Raw Idea

میخوام مدل ها در هر جا که استفاده میشن به طور دقیق گزارش مصرف توکن بدن و این رو در جایی ثبت بشه و در گزارش ها و قسمت های لازم نوتیفیکشن ها هم اشاره بشه و رتبه بندی بشه
سیستم نشتی ها رو ببینه کجا مدل ها بدون کار مفید دارن توکن مصرف میکنن و باعث ایجاد هزینه میشه
و سوم اینکه برای هر مدل بشه مستقیم از پلتفرمش فهمید که چقدر شارجش باقی مونده و نزدیک اتمامش که بود بهش گزارش داده بشه و همینطور در گزارش هایی که مصرف ها رو میگه همین میزان باقی مونده شارج هم بهم گفته بشه

## Prompt

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
سیستم جامع ردیابی و گزارش‌دهی مصرف توکن مدل‌های AI با هشدار شارژ و تشخیص نشتی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/ai_manager.py:مشاهده نشده در deep context` — `AIProviderManager` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً اینجا نقطه مرکزی مدیریت تمام سرویس‌های AI است و باید hook مصرف توکن اضافه شود.
- `backend/app/services/openai_service.py:مشاهده نشده در deep context` — `OpenAIService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً متدهای `chat_completion` یا `generate` در اینجا مصرف توکن را از response استخراج می‌کنند.
- `backend/app/services/claude_service.py:مشاهده نشده در deep context` — `ClaudeService` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. مشابه OpenAI، باید مصرف توکن را از response Anthropic استخراج کند.
- `backend/app/models/ai_log.py:مشاهده نشده در deep context` — `AILog` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. احتمالاً مدل دیتابیس موجود برای لاگ‌های AI است که باید فیلدهای مصرف توکن به آن اضافه شود.
- `backend/app/api/routes/models.py:78-159` — `list_models` — این endpoint لیست مدل‌ها
  ```python
  @router.get("", response_model=List[ModelInfo])
      @router.get("/", response_model=List[ModelInfo])
      async def list_models(
          provider: Optional[str] = None,
          capability: Optional[str] = None,
          db: Session = Depends(get_db)
      ):
          """لیست همه مدل‌ها"""
          try:
              from ...core.models_registry import MODEL_REGISTRY, ModelCapability
              from ...services.ai_manager import get_ai_manager
              from ...models.ai_profile import ModelSettings
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست سه قابلیت مرتبط دارد: (1) ردیابی دقیق مصرف توکن در تمام نقاط استفاده از مدل‌ها و ثبت آن در دیتابیس، (2) تشخیص نشتی‌های مصرف توکن (جایی که مدل‌ها بدون خروجی مفید توکن مصرف می‌کنند)، (3) نمایش موجودی شارژ باقی‌مانده هر پلتفرم با هشدار نزدیک اتمام. در کد فعلی، سرویس‌های AI مانند `backend/app/services/openai_service.py` و `claude_service.py` مصرف توکن را لاگ می‌کنند اما این داده‌ها به صورت متمرکز در دیتابیس ذخیره نمی‌شوند و در گزارش‌ها و نوتیفیکیشن‌ها استفاده نمی‌شوند. همچنین هیچ مکانیزمی برای رصد موجودی API Keyها وجود ندارد.

## ✅ معیار پذیرش (Acceptance Criteria)
- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ایجاد یک سرویس مرکزی `TokenUsageService` که مصرف توکن را از تمام سرویس‌های AI جمع‌آوری کرده و در جدول جدید دیتابیس ذخیره کند. سپس API endpoints برای گزارش‌گیری و نوتیفیکیشن ایجاد شود. برای تشخیص نشتی، یک تحلیلگر پس‌زمینه‌ای بنویسیم که session‌های طولانی با خروجی کم را شناسایی کند. برای مانیتورینگ شارژ، از APIهای status پلتفرم‌ها (مثلاً OpenAI Usage API) استفاده کنیم.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: large

## Acceptance Criteria

1. هیچ تستی fail نمی‌شود (`npm run test` / `pytest`) _(verify: backend_test)_
2. linter بدون warning عبور می‌کند _(verify: backend_test)_
3. type-check موفق است (`tsc --noEmit` / `mypy`) _(verify: backend_test)_
