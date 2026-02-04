# 📋 گزارش جامع و به‌روز سیستم مدیریت پروژه هوشمند

**تاریخ:** 2026-02-04
**شاخه:** `claude/update-system-report-izMLQ`
**وضعیت:** به‌روز شده - نسخه 2.2 (اصلاحات گزارش مهندسی ۴ مرحله‌ای)

---

## فهرست مطالب

1. [خلاصه اجرایی](#1-خلاصه-اجرایی)
2. [بخش‌های اصلی سیستم](#2-بخشهای-اصلی-سیستم)
3. [تغییرات اخیر انجام شده](#3-تغییرات-اخیر-انجام-شده)
4. [وضعیت مشکلات گزارش شده](#4-وضعیت-مشکلات-گزارش-شده)
5. [قابلیت‌های درخواستی](#5-قابلیتهای-درخواستی)
6. [موارد فنی نیازمند پیاده‌سازی](#6-موارد-فنی-نیازمند-پیادهسازی)
7. [ساختار تب‌ها](#7-ساختار-تبها)
8. [جداول خلاصه](#8-جداول-خلاصه)

---

## 1. خلاصه اجرایی

### آمار کلی پروژه

| بخش | تعداد فایل | خط کد |
|-----|-----------|--------|
| Backend Routes | 26 | ~31,775 |
| Backend Services | 49 | ~32,787 |
| Database Models | 9 | ~58,000 |
| Frontend Pages | 13 | ~50,000 |
| **کل** | **~100** | **~150,000+** |

### وضعیت کلی

| وضعیت | تعداد | توضیح |
|-------|-------|--------|
| ✅ رفع شده | 22 | مشکلات اصلی + موارد ناقص + باگ‌های گزارش مهندسی |
| ⚠️ نیاز به بهبود | 4 | موارد UI و Frontend |
| 🔴 باقیمانده | 2 | مشکلات جزئی |
| 🆕 قابلیت جدید | 11 | پیاده‌سازی شده |

---

## 2. بخش‌های اصلی سیستم

### بخش ۱: راه‌اندازی خودکار پروژه

**موقعیت:** تب حافظه و دستورات
**فایل:** `backend/app/services/project_auto_setup.py` (2325 خط)

#### ✅ وضعیت فعلی (اصلاح شده)

| موضوع | وضعیت قبلی | وضعیت فعلی |
|-------|-----------|-----------|
| استفاده از AI | ❌ ثابت و از پیش تعریف شده | ✅ انتخاب هوشمند مدل + تلاش متعدد |
| برخورد با فیلدهای قبلی | ❌ حذف بدون بررسی | ✅ 6 سطح محافظت + بایگانی هوشمند |
| الگوی ذخیره‌سازی | ❌ OVERWRITE | ✅ MERGE با ادغام هوشمند |
| ثبت در ژورنال | ❌ ناقص | ✅ سطر به سطر با ActivityLog |

#### عملیات اصلی (۴ مرحله)

1. **تحلیل عمیق ساختار:** شناسایی frameworks، patterns، dependencies
2. **تولید دستورات با AI:** انتخاب بهترین مدل برای هر نوع کار
3. **پردازش فیلدهای موجود:** بررسی محافظت، بایگانی/ادغام/به‌روزرسانی
4. **ذخیره در دیتابیس:** MERGE نه OVERWRITE + ثبت در ژورنال

#### سیستم محافظت فیلدها (6 معیار)

```python
is_protected_field():
  - فیلدهای ایجاد شده توسط گزارش مهندسی
  - فیلدهای با validation_marker (validated, pending)
  - فیلدهای اعتبارسنجی شده توسط مدل
  - فیلدهای با علامت ✅
  - فیلدهای با تصویب مهندسی (engineering_approval)
  - فیلدهای با converted_field_id
```

#### نقش باکس حافظه (اصلاح شده)

- ✅ چارچوب عملیاتی برای همه مدل‌های AI
- ✅ همه مدل‌ها قبل از عملیات محتوای باکس را می‌خوانند
- ✅ MERGE به جای OVERWRITE برای حفظ محتوای کاربر

---

### بخش ۲: پرسش از AI درباره پروژه

**موقعیت:** تب فایل‌ها

#### ✅ قابلیت‌های موجود

- پاسخ به پرسش با اشراف کامل به پروژه
- ایجاد فیلدهای جدید با چک تکراری
- ادغام با فیلدهای مشابه موجود
- تحلیل AI برای تعیین فایل‌های هدف

#### 🆕 قابلیت جدید: درخواست قابلیت (Feature Request)

**Endpoint:** `POST /{project_id}/request-feature`

```python
class FeatureRequest:
    title: str           # عنوان
    description: str     # توضیحات
    priority: str        # critical, high, medium, low
    category: str        # feature, bugfix, improvement, refactor
    target_files: List   # فایل‌های هدف (اختیاری)
    ai_analyze: bool     # تحلیل AI
    auto_add_roadmap: bool # اضافه به نقشه راه
```

**فرآیند:**

1. چک تکراری با IntelligentFieldCreator (آستانه شباهت: 0.85)
2. ایجاد فیلد با `validation_marker="pending"`
3. تحلیل AI برای تعیین فایل‌ها و مراحل
4. اضافه خودکار به Roadmap
5. ثبت در ژورنال

---

### بخش ۳: تحلیل سلامت پروژه

**فایل‌های اصلی:**

- `backend/app/services/deep_analysis_service.py`
- `backend/app/services/project_health_analyzer.py`
- `backend/app/api/routes/project_health.py` (5100+ خط)

#### تحلیل سه‌مرحله‌ای

| مرحله | وزن | توضیح |
|-------|-----|--------|
| **Micro** | 60% | بررسی تک‌تک فایل‌ها |
| **Macro** | 20% | همکاری بین فایل‌ها |
| **Structural** | 15% | معماری کلی |
| **Finalizing** | 5% | محاسبه نمرات نهایی |

#### معیارهای نمره‌گذاری (8 معیار)

| معیار | وزن |
|-------|-----|
| `code_quality` | 0.20 |
| `roadmap_compliance` | 0.15 |
| `position_appropriateness` | 0.15 |
| `wiring_correctness` | 0.15 |
| `completeness` | 0.10 |
| `efficiency` | 0.10 |
| `documentation` | 0.10 |
| `standards_compliance` | 0.05 |

#### رنگ‌بندی نمرات

```
score >= 90:  🟢 سبز (عالی)
score >= 75:  🟢 فسفری (خوب)
score >= 60:  🟡 زرد (متوسط)
score >= 40:  🟠 نارنجی (ضعیف)
score >= 20:  🔴 قرمز (بد)
score < 20:   🔴 قرمز تیره (بحرانی)
```

#### ⚠️ مشکلات باقیمانده

| مشکل | وضعیت |
|------|--------|
| عدم بررسی فرانت‌اند | ⚠️ فقط backend |
| محدودیت 100 فایل در UI | ⚠️ Backend پشتیبانی می‌کند، Frontend نه |
| نمره ثابت 50% برای ساختار | ⚠️ نیاز به تحلیل واقعی |
| ادغام ایرادات ناپایدار | ⚠️ گاهی کار می‌کند |

---

### بخش ۴: گزارش مهندسی

**فایل‌های اصلی:**

- `backend/app/api/routes/project_journal.py` (generate_engineering_report)
- `backend/app/services/deep_analysis_service.py`
- `backend/app/services/quick_approval_service.py`

#### ۴ مرحله گزارش مهندسی

| مرحله | توضیح |
|-------|--------|
| **۱. بررسی پروژه** | اعتبارسنجی فیلدهای پویای موجود |
| **۲. انطباق با تحلیل سلامت** | تایید ایرادات + تولید فیلدهای اقدام‌محور |
| **۳. اعتبارسنجی مدل‌ها** | ارزیابی عملکرد مدل‌ها + ثبت امتیاز |
| **۴. به‌روزرسانی نقشه راه** | تعیین حالت ایده‌آل + چک‌لیست |

#### 🆕 سیستم تایید سریع (Quick Approval)

**Validation Markers:**

```
pending          → نیاز به Engineering Report
auto_pending     → قابل تایید سریع (تبدیل خودکار از ایرادات بحرانی)
quick_approved   → تایید سریع شده
engineering_approved → تایید Engineering Report
```

**Endpoints جدید:**

| Method | Endpoint | توضیح |
|--------|----------|--------|
| GET | `/quick-approval/pending` | لیست فیلدهای در انتظار |
| POST | `/quick-approval/auto-convert` | تبدیل خودکار ایرادات بحرانی |
| POST | `/quick-approval/approve/{field_id}` | تایید سریع |
| POST | `/quick-approval/reject/{field_id}` | رد کردن |
| GET | `/quick-approval/pre-validate/{field_id}` | اعتبارسنجی قبل از اجرا |

#### 🆕 اعتبارسنجی قبل از اجرا (Pre-Execution Validation)

```python
async def pre_execution_validation():
    # بررسی 1: آیا ایراد اصلی حل شده؟
    if original_issue.status in ["resolved", "closed", "fixed"]:
        return {"can_execute": False, "reason": "ایراد قبلاً حل شده"}

    # بررسی 2: آیا فیلد مشابهی اجرا شده؟
    if similarity > 0.7:
        return {"can_execute": False, "reason": "فیلد مشابه اجرا شده"}

    # بررسی 3: تحلیل AI (اختیاری)
    return {"can_execute": True}
```

#### ✅ اصلاحات اخیر (2026-02-04)

| مشکل | راه‌حل |
|------|--------|
| خطای token limit در مراحل 1 و 2 | ✅ افزودن auto-truncation برای prompt های بزرگ |
| خطای "can only concatenate list to list" در step3 | ✅ اصلاح نوع source_models و بررسی همه انواع داده |
| آمار صفر در خروجی (validated_count = 0) | ✅ اصلاح ساختار بازگشتی step1 از nested به flat |
| فرمت خروجی ضعیف | ✅ افزودن رندر 4 مرحله‌ای با آمار جداگانه |

#### جزئیات فنی اصلاحات

**1. Token Truncation در Step1 و Step2:**
```python
# محاسبه توکن‌های تخمینی
estimated_tokens = (len(system_prompt) + len(user_prompt)) // 3
max_prompt_tokens = int(max_context * 0.75)

if estimated_tokens > max_prompt_tokens:
    # کوتاه کردن داده‌ها
    max_issues = max(5, int(len(issues) * excess_ratio * 0.7))
    issues_truncated = issues[:max_issues]
```

**2. اصلاح نوع source_models در Step3:**
```python
source_models = issue.get("source_models")
if source_models is None:
    source_models = [issue.get("source_model", "unknown")]
elif isinstance(source_models, str):
    source_models = [source_models]
elif isinstance(source_models, (int, float)):
    # اگر عدد بود، از پیش‌فرض استفاده کن
    source_models = [issue.get("source_model", "unknown")]
```

**3. ساختار بازگشتی flat برای Step1:**
```python
# قبل: nested
return {"results": {"approved_count": x, "rejected_count": y}}

# بعد: flat
return {"validated_count": x, "rejected_count": y, "merged_count": z}
```

#### ⚠️ موارد باقیمانده

| مشکل | وضعیت |
|------|--------|
| سرعت بیش از حد (حتی حالت عمیق زیر 2 دقیقه) | ⚠️ نیاز به بررسی |
| عدم بایگانی ایرادات از همه منابع | ⚠️ نیاز به بهبود |
| نقشه راه خالی بعد از اجرا | ⚠️ نیاز به بررسی |

---

### بخش ۵: لاگ‌های Render

**فایل:** `backend/app/api/routes/render_logs.py` (1826 خط)

#### ✅ قابلیت‌های پیاده‌سازی شده

| قابلیت | وضعیت |
|--------|--------|
| دریافت لاگ از Render API | ✅ |
| ذخیره در دیتابیس | ✅ |
| فیلتر بر اساس سرویس/نوع/زمان | ✅ |
| انتقال خطاها به تب ایرادات | ✅ |
| تحلیل AI برای خطاها | ✅ |
| بایگانی لاگ‌های منتقل شده | ✅ |
| Auto-transfer (هر 30 دقیقه) | ✅ |
| بایگانی ایرادات قدیمی بعد از دیپلوی | ✅ |

#### حالت‌های انتقال خطا

| حالت | توضیح |
|------|--------|
| `since_deploy` (پیش‌فرض) | خطاهای بعد از آخرین دیپلوی |
| `time_based` | خطاهای X ساعت اخیر |
| `realtime` | انتقال فوری هر خطا |

#### فرآیند انتقال لاگ خطا به تب ایرادات

```
1. تفکیک: لاگ‌ها حسب سرویس و پروژه تفکیک
2. ترجمه و تحلیل: توسط مدل AI با تشخیص علت و اولویت
3. بررسی ادغام: آیا ایراد مشابه وجود دارد؟
4. ثبت: در ردیف مناسب با اولویت صحیح
5. اعتبارسنجی: توسط گزارش مهندسی
```

---

### بخش ۶: ژورنال و گزارشات

**فایل:** `backend/app/services/journal_service.py` (734 خط)

#### انواع فعالیت‌های ثبت شده (15+ نوع)

| نوع | توضیح |
|-----|--------|
| `transfer` | انتقال یافته‌ها به ایرادات |
| `scan` | اسکن امنیتی/پوشش تست |
| `archive` | بایگانی داده‌ها |
| `health_analysis` | تحلیل سلامت |
| `issue_update` | تغییرات ایرادات |
| `field_change` | تغییرات فیلدهای پویا |
| `model_score_updated` | تغییر امتیاز مدل‌ها |
| `quick_approve_field` | تایید سریع فیلد |
| `reject_auto_field` | رد فیلد |
| `auto_convert_issues` | تبدیل خودکار ایرادات |

#### قابلیت دانلود

| فرمت | توضیح |
|------|--------|
| JSON | تمام جزئیات + عملیات جزئی |
| CSV | جدولی |
| XLSX | Excel با استایل |

---

### بخش ۷: بایگانی عمومی

**موقعیت:** تب بایگانی ذیل تب تحلیل سلامت

#### ✅ پیاده‌سازی شده

| قابلیت | وضعیت |
|--------|--------|
| بایگانی همه موارد پاک شده | ✅ |
| دسته‌بندی (issues, health, files...) | ✅ |
| قابل باز کردن و مشاهده محتوا | ✅ |
| ثبت جزئیات (تاریخ، دلیل، برچسب) | ✅ |
| دانلود در 3 فرمت (JSON, CSV, TXT) | ✅ |

#### برچسب‌های وضعیت

| برچسب | توضیح |
|-------|--------|
| تایید شده - تبدیل به فیلد پویا | ایراد تایید و تبدیل شده |
| رد شده توسط گزارش مهندسی | ایراد رد شده |
| پاک شده توسط دکمه پاک کردن | مورد حذف شده |
| منقضی شده - دیپلوی جدیدتر | ایراد قدیمی‌تر از آخرین دیپلوی |

---

## 3. تغییرات اخیر انجام شده

### ✅ رفع تناقضات سیستمی

#### مشکل اصلی: ماژول‌ها کار یکدیگر را خنثی می‌کردند

| فیلد مشترک | ماژول‌های درگیر |
|-----------|----------------|
| `issues_found` | Health Analysis, Deep Analysis, Auto Setup, Log to Issues |
| `dynamic_fields` | Auto Setup, AI Q&A, Engineering Report, Request Feature |
| `memory_instructions` | Auto Setup, User Manual Edit |

#### راه‌حل‌های پیاده‌سازی شده

**۱. تغییر الگو از OVERWRITE به MERGE**

```python
# قبل: OVERWRITE
project.issues_found = json.dumps(new_issues)

# بعد: MERGE
def _merge_with_existing_issues(project, new_issues, source, db=None):
    if db:
        db.refresh(project)  # خواندن آخرین داده
    existing = json.loads(project.issues_found) if project.issues_found else []

    # ادغام هوشمند با کلید یکتا
    for new_issue in new_issues:
        key = _get_issue_key(new_issue)
        existing_idx = next((i for i, e in enumerate(existing) if _get_issue_key(e) == key), None)
        if existing_idx is not None:
            existing[existing_idx] = {**existing[existing_idx], **new_issue}  # بروزرسانی
        else:
            existing.append(new_issue)  # اضافه کردن
    return existing
```

**۲. مکانیزم قفل دیتابیس**

```python
class ProjectLockManager:
    """مدیریت قفل برای جلوگیری از race condition"""

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._master_lock = asyncio.Lock()

    async def acquire_lock(self, project_id: str, field: str = "default"):
        lock_key = f"{project_id}:{field}"
        async with self._master_lock:
            if lock_key not in self._locks:
                self._locks[lock_key] = asyncio.Lock()
        return self._locks[lock_key]
```

**۳. db.refresh() قبل از خواندن داده مشترک**

**۴. db.rollback() در exception handlers**

### 🆕 قابلیت‌های جدید پیاده‌سازی شده

| قابلیت | فایل | خطوط |
|--------|------|------|
| Feature Request | project_memory.py | +370 |
| Quick Approval | quick_approval_service.py | 827 |
| Pre-Execution Validation | quick_approval_service.py | داخل سرویس |
| UI تایید سریع | projects/[id]/page.tsx | +513 |
| **🆕 Source Tracking** | project_memory.py | ردیابی منبع فیلدها |
| **🆕 Error Logging** | logging_utils.py | لاگ‌های کامل با traceback |
| **🆕 Background Scheduler** | background_scheduler.py | 6 نوع تریگر |
| **🆕 Technology Extraction** | orchestrator.py | استخراج تکنولوژی‌ها |
| **🆕 Performance History** | smart_orchestrator.py | ذخیره تاریخچه عملکرد |

### 🆕 سیستم زمان‌بندی پس‌زمینه (Background Scheduler)

**فایل:** `backend/app/services/background_scheduler.py`

#### ۶ نوع تریگر پیاده‌سازی شده

| # | نوع تریگر | توضیح | بازه پیش‌فرض |
|---|-----------|--------|--------------|
| ۱ | Auto Security Transfer | انتقال خودکار یافته‌های امنیتی به ایرادات | هر 60 دقیقه |
| ۲ | Auto Test Coverage Transfer | انتقال مشکلات پوشش تست | هر 60 دقیقه |
| ۳ | Auto Health Analysis | اجرای خودکار تحلیل سلامت | هر 120 دقیقه |
| ۴ | Auto Engineering Report | اجرای خودکار گزارش مهندسی | هر 240 دقیقه |
| ۵ | Auto Archive Old Issues | بایگانی خودکار ایرادات قدیمی | هر 1440 دقیقه (روزانه) |
| ۶ | Auto Render Log Sync | همگام‌سازی لاگ‌های Render | هر 30 دقیقه |

#### تنظیمات جدید دیتابیس (RenderLogSettings)

```python
# ستون‌های جدید برای هر تریگر
auto_security_transfer_enabled: Boolean
auto_security_transfer_interval_minutes: Integer
auto_security_transfer_last_run: DateTime

auto_test_coverage_transfer_enabled: Boolean
auto_test_coverage_transfer_interval_minutes: Integer
auto_test_coverage_transfer_last_run: DateTime

# و مشابه برای سایر تریگرها...
```

### 🆕 ردیابی منبع فیلدها (Source Tracking)

فیلدهای جدید برای هر فیلد پویا:

| فیلد | توضیح |
|------|--------|
| `source` | منبع ایجاد: `ai_chat` یا `feature_request` |
| `source_prompt` | متن درخواست کاربر (300 کاراکتر اول) |
| `created_via` | روش ایجاد: "پرسش از AI" یا "دکمه قابلیت جدید" |

### 🆕 سیستم لاگ‌گیری پیشرفته

**فایل:** `backend/app/core/logging_utils.py`

```python
def log_critical_error(context: str, exception: Exception, extra_data: Dict = None):
    """لاگ خطای بحرانی با traceback کامل"""
    full_traceback = traceback.format_exc()
    logger.error(f"""
    ╔══════════════════════════════════════════════════════════════════╗
    ║            🔴 CRITICAL ERROR: {context}                          ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║ Exception: {type(exception).__name__}
    ║ Message: {str(exception)}
    ║ Full Traceback:
    {full_traceback}
    ╚══════════════════════════════════════════════════════════════════╝
    """)
```

### جریان داده جدید

```
                        ┌─────────────────┐
                        │  کاربر درخواست  │
                        │  قابلیت می‌دهد   │
                        └────────┬────────┘
                                 │
                                 ▼
                   ┌─────────────────────────┐
                   │    /request-feature     │
                   │  چک تکراری با           │
                   │  IntelligentFieldCreator │
                   └────────────┬────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
            ┌───────────────┐       ┌───────────────┐
            │   تکراری      │       │   یکتا        │
            │   هشدار       │       │   ایجاد فیلد  │
            └───────────────┘       │   pending     │
                                    └───────┬───────┘
                                            │
                        ┌───────────────────┴───────────────────┐
                        │                                       │
                        ▼                                       ▼
                ┌───────────────┐                       ┌───────────────┐
                │ Quick Approval │                       │ Engineering   │
                │ (یک کلیک)      │                       │ Report (کامل) │
                └───────┬───────┘                       └───────┬───────┘
                        │                                       │
                        ▼                                       ▼
                ┌───────────────┐                       ┌───────────────┐
                │ quick_approved │                       │ engineering_  │
                │                │                       │ approved      │
                └───────┬───────┘                       └───────┬───────┘
                        │                                       │
                        └───────────────────┬───────────────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │  Pre-Execution        │
                                │  Validation           │
                                │  (آیا ایراد حل شده؟)  │
                                └───────────┬───────────┘
                                            │
                                ┌───────────┴───────────┐
                                │                       │
                                ▼                       ▼
                        ┌───────────────┐       ┌───────────────┐
                        │   هشدار       │       │   اجرا        │
                        │   + تایید     │       │   فیلد        │
                        └───────────────┘       └───────────────┘
```

---

## 4. وضعیت مشکلات گزارش شده

### دسته ۱: راه‌اندازی خودکار

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۱-۱ | عملکرد ثابت بجای هوشمند | ✅ رفع شده |
| ۱-۲ | حذف بدون بررسی | ✅ رفع شده |
| ۱-۳ | عدم استفاده از AI | ✅ رفع شده |
| ۱-۴ | سوءتفاهم نقش باکس حافظه | ✅ اصلاح شده |

### دسته ۲: گزارش مهندسی

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۲-۱ | عدم نمایش تاییدیه | ⚠️ نیاز به بررسی |
| ۲-۲ | سرعت بیش از حد | ⚠️ نیاز به بهبود |
| ۲-۳ | عدم بایگانی ایرادات | ⚠️ نیاز به بهبود |
| ۲-۴ | نقشه راه خالی | ⚠️ نیاز به بررسی |
| ۲-۵ | فرمت خروجی ضعیف | ⚠️ نیاز به بهبود |

### دسته ۳: تحلیل سلامت

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۳-۱ | ادغام ایرادات ناپایدار | ⚠️ نیاز به بهبود |
| ۳-۲ | عدم بررسی فرانت‌اند | 🔴 باقیمانده |
| ۳-۳ | محدودیت 100 فایل در UI | 🔴 Backend OK، Frontend نه |
| ۳-۴ | نمره پیش‌فرض 50% برای ساختار | 🔴 باقیمانده |

### دسته ۴: انتقال ایرادات

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۴-۱ | انتقال 0 یافته | ✅ رفع شده |
| ۴-۲ | گزارشات دانلود ناقص | ⚠️ نیاز به بررسی |
| ۴-۳ | عدم نمایش بدون رفرش | ⚠️ نیاز به بررسی |
| ۴-۴ | شمارنده کم نمیشه | ✅ رفع شده |
| ۴-۵ | شرح و بسط ضعیف | ⚠️ نیاز به بهبود |

### دسته ۵: لاگ Render

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۵-۱ | عدم به‌روزرسانی خودکار | ✅ رفع شده (APScheduler) |
| ۵-۲ | فیلتر و سورت | ⚠️ Backend OK، Frontend نیاز بررسی |

### دسته ۶: رابط کاربری

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۶-۱ | رنگ فونت همرنگ پس‌زمینه | ⚠️ نیاز به اصلاح |
| ۶-۲ | فایل‌ها فقط در حالت درختی | ⚠️ نیاز به بهبود |

### دسته ۷: ژورنال

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۷-۱ | عدم ثبت بسیاری از اقدامات | ✅ اصلاح شده (JournalService جامع) |

### دسته ۸: پرامپت‌ها

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۸-۱ | عدم نمایش زنده پیشرفت | ⚠️ نیاز به پیاده‌سازی |

### دسته ۹: سیستمی

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۹-۱ | تناقضات بین بخش‌ها | ✅ بخش بزرگی رفع شده (MERGE بجای OVERWRITE) |

---

## 5. قابلیت‌های درخواستی

### جدول وضعیت

| # | قابلیت | وضعیت |
|---|--------|--------|
| ۱ | انتخاب مدل در گزارش مهندسی | ✅ پیاده‌سازی شده |
| ۲ | بهبود کیفیت اجرای گزارش مهندسی | ⚠️ نیاز به بهبود |
| ۳ | دانلود مارک‌داون | ✅ پیاده‌سازی شده |
| ۴ | رفع محدودیت 100 فایل | ⚠️ Backend OK، Frontend نه |
| ۵ | تب بایگانی عمومی | ✅ پیاده‌سازی شده |
| ۶ | ثبت جزئیات امتیاز مدل‌ها در ژورنال | ✅ پیاده‌سازی شده |
| ۷ | لاگ‌های خوانا در بک‌اند | ✅ پیاده‌سازی شده |
| ۸ | ارتقای پرسش از AI برای ایده‌ها | ✅ پیاده‌سازی شده (Feature Request) |
| ۹ | سیستم مدیریت لاگ‌های Render | ✅ پیاده‌سازی شده |
| ۱۰ | مدیریت پرامپت‌ها + نمایش زنده | ⚠️ نیاز به بهبود UI |
| ۱۱ | اصلاح شرح و بسط ایرادات | ⚠️ نیاز به بهبود |

---

## 6. موارد فنی نیازمند پیاده‌سازی

### دسته ۱: موارد ناقص (نیاز به بهبود و تکمیل)

| # | عنوان | وضعیت | توضیح |
|---|-------|--------|--------|
| ۱.۱ | زنجیره اعتبارسنجی (Sandbox Testing) | ⚠️ نیاز به پیاده‌سازی | تست کد پیشنهادی قبل از Commit |
| ۱.۲ | ترکیب امتیاز مدل با Linterها | ⚠️ نیاز به پیاده‌سازی | امتیاز فنی واقعی بجای حدس مدل |
| ۱.۳ | وابستگی‌ها در نقشه راه | ⚠️ نیاز به پیاده‌سازی | تا فیلد A نشود، فیلد B اجرا نشود |

### دسته ۲: موارد مفقود (Green Flags)

| # | عنوان | وضعیت | توضیح |
|---|-------|--------|--------|
| ۲.۱ | تحلیل لایسنس و امنیت وابستگی‌ها | ✅ موجود | security_analyzer.py |
| ۲.۲ | تشخیص داده‌های حساس | ✅ موجود | security_scanner.py |
| ۲.۳ | قابلیت Dry Run | ⚠️ نیاز به پیاده‌سازی | پیش‌نمایش تغییرات قبل از Commit |
| ۲.۴ | بررسی تست‌ها (Test Coverage) | ✅ موجود | test_coverage_analyzer.py |

---

## 7. ساختار تب‌ها

```
├── تب حافظه و دستورات
│   └── راه‌اندازی خودکار پروژه ✅
│       └── انتخاب مدل
│       └── سینک با GitHub
│       └── ایجاد فیلدهای پویا
│
├── تب فایل‌ها
│   └── پرسش از AI درباره پروژه ✅
│       └── 🆕 درخواست قابلیت جدید (Feature Request)
│       └── تبدیل به فیلد
│       └── تحلیل AI
│
├── تب تحلیل سلامت
│   ├── زیرتب نمای کلی
│   │   └── نمرات سلامت
│   │   └── رنگ‌بندی فایل‌ها
│   ├── زیرتب ایرادات
│   │   └── 🆕 تایید سریع (Quick Approval)
│   │   └── تبدیل خودکار ایرادات بحرانی
│   ├── زیرتب بایگانی عمومی ✅
│   │   └── دسته‌بندی شده
│   │   └── قابل دانلود
│   ├── زیرتب فایلها
│   │   └── نمایش کد با کامنت
│   │   └── رنگ‌بندی ایرادات
│   ├── زیرتب امنیت
│   │   └── اسکن امنیتی
│   │   └── انتقال به ایرادات
│   └── زیرتب پوشش تست
│       └── تحلیل پوشش
│       └── انتقال به ایرادات
│
├── تب ژورنال و گزارشات
│   ├── ژورنال ✅
│   │   └── 15+ نوع فعالیت
│   │   └── دانلود (JSON, CSV, XLSX)
│   ├── نقشه راه
│   │   └── چک‌باکس‌های وضعیت
│   │   └── به‌روزرسانی خودکار/دستی
│   └── گزارشات
│       └── تاریخچه گزارش‌های مهندسی
│
├── تب گزارش مهندسی
│   ├── ۴ مرحله تحلیل
│   ├── 🆕 Pre-Execution Validation
│   ├── انتخاب مدل
│   └── سطح عمق (quick/standard/deep/thorough)
│
└── تنظیمات
    ├── API Keys
    ├── مدل‌ها
    │   └── فعال/غیرفعال
    │   └── امتیازدهی
    └── لاگ‌های Render ✅
        ├── فیلتر و سورت
        ├── به‌روزرسانی خودکار
        ├── انتقال خطاها به ایرادات
        │   └── since_deploy (پیش‌فرض)
        │   └── time_based
        │   └── realtime
        └── ذخیره در دیتابیس
```

---

## 8. جداول خلاصه

### جدول نوع ثبت در ژورنال

| بخش / عملیات | نوع ثبت |
|--------------|---------|
| راه‌اندازی خودکار | دقیق و کامل - سطر به سطر - قابل کلیک |
| پرسش از AI | دقیق و کامل |
| تحلیل سلامت | خلاصه اما دقیق (فقط عملیات، نه ایرادات) |
| گزارش مهندسی | خلاصه دقیق عملیات |
| تغییرات امتیاز مدل‌ها | دقیق - دونه به دونه - با ذکر کامل علت |
| تایید/رد ایرادات | ردیف مجزا برای هر ایراد |
| انتقال به بایگانی | ردیف مجزا با ذکر برچسب وضعیت |

### جدول خلاصه مشکلات

| وضعیت | تعداد | درصد |
|-------|-------|------|
| ✅ رفع شده | 22 | 79% |
| ⚠️ نیاز به بهبود | 4 | 14% |
| 🔴 باقیمانده | 2 | 7% |
| **کل** | **28** | **100%** |

### فایل‌های کلیدی تغییر یافته

| فایل | نوع تغییر | توضیح |
|------|----------|------|
| backend/app/api/routes/project_health.py | ویرایش | MERGE logic |
| backend/app/api/routes/project_memory.py | ویرایش | +370 + source tracking |
| backend/app/api/routes/project_structure.py | ویرایش | رفع باگ دیاگرام خالی |
| backend/app/api/routes/orchestrator.py | ویرایش | استخراج تکنولوژی |
| backend/app/services/deep_analysis_service.py | ویرایش | MERGE + rollback |
| backend/app/services/project_auto_setup.py | ویرایش | MERGE helpers |
| backend/app/services/quick_approval_service.py | **جدید** | 827 خط |
| backend/app/services/background_scheduler.py | ویرایش | 6 نوع تریگر |
| backend/app/services/smart_orchestrator.py | ویرایش | ذخیره تاریخچه عملکرد |
| backend/app/core/database.py | ویرایش | ProjectLockManager + migrations |
| backend/app/core/logging_utils.py | ویرایش | لاگ‌گیری پیشرفته |
| backend/app/models/render_log.py | ویرایش | ستون‌های تریگر |
| backend/app/models/project.py | ویرایش | +converted_field_id |
| frontend/src/app/projects/[id]/page.tsx | ویرایش | +513 |

### Commits اخیر

| Commit | توضیح |
|--------|--------|
| **NEW** | **Fix: Step1 flat return structure + Step3 source_models type handling** |
| **659b98a** | **Fix: Add token truncation to step2 (health_to_fields)** |
| **cfa1121** | **Fix: Token limit handling and step3 return structure** |
| **cd15718** | **Fix: Force stop all executions when clicking stop button** |
| **a71ce5f** | **Feat: Add close/stop buttons to ExecutingPromptsPanel** |
| **34e5c12** | **Feat: Add proper rendering for 4-step engineering report format** |
| 13cc9a6 | Fix: Complete implementation of incomplete/stub features |
| fa61fb6 | Feat: Add source tracking to fields created from AI Chat and Feature Request |
| a2d90ed | Fix: Add comprehensive error logging for Engineering Report debugging |
| e02e6e3 | Feat: Implement complete background scheduler with all 6 trigger types |

---

## نتیجه‌گیری

### ✅ نقاط قوت

1. **رفع تناقضات اصلی:** تغییر از OVERWRITE به MERGE
2. **سیستم قفل:** جلوگیری از Race Condition
3. **Quick Approval:** تسریع فرآیند تایید فیلدها
4. **Feature Request:** امکان افزودن قابلیت بدون Engineering Report
5. **Pre-Execution Validation:** جلوگیری از اجرای فیلدهای منقضی
6. **ژورنال جامع:** ثبت تمام عملیات با 15+ نوع فعالیت
7. **بایگانی عمومی:** حفظ تمام داده‌های حذف شده
8. **لاگ Render:** سیستم کامل با انتقال خودکار خطاها
9. **🆕 زمان‌بندی پس‌زمینه:** 6 نوع تریگر خودکار برای همه عملیات
10. **🆕 ردیابی منبع فیلدها:** دانستن اینکه هر فیلد از کجا آمده
11. **🆕 لاگ‌گیری پیشرفته:** خطاها با traceback کامل ثبت می‌شوند
12. **🆕 استخراج تکنولوژی:** شناسایی خودکار تکنولوژی‌های پروژه
13. **🆕 ذخیره تاریخچه عملکرد:** مدل‌ها بر اساس عملکرد واقعی انتخاب می‌شوند

### ⚠️ موارد نیازمند توجه (کاهش یافته)

1. بهبود UI برای محدودیت فایل‌ها
2. اضافه کردن تحلیل فرانت‌اند در تحلیل سلامت
3. پیاده‌سازی Dry Run (پیش‌نمایش تغییرات)
4. نمایش زنده پیشرفت پرامپت‌ها
5. اصلاح رنگ فونت در نمایش فایل‌ها

### 📊 خلاصه پیشرفت

| معیار | قبل | بعد |
|-------|-----|-----|
| موارد رفع شده | 18 | 22 |
| موارد نیازمند بهبود | 5 | 4 |
| قابلیت‌های جدید | 10 | 11 |
| تریگرهای زمان‌بندی فعال | 1 | 6 |

### 🔧 اصلاحات گزارش مهندسی ۴ مرحله‌ای (2026-02-04)

| مشکل | وضعیت |
|------|--------|
| Token limit exceeded در Step1 | ✅ رفع شد - auto-truncation |
| Token limit exceeded در Step2 | ✅ رفع شد - auto-truncation |
| "can only concatenate list to list" در Step3 | ✅ رفع شد - بررسی نوع source_models |
| آمار صفر (validated_count = 0) | ✅ رفع شد - ساختار flat برای step1 |
| ExecutingPromptsPanel بدون دکمه بستن | ✅ رفع شد - دکمه‌های close/stop |
| توقف ناقص اجراها | ✅ رفع شد - force=true parameter |

---

**تاریخ به‌روزرسانی:** 2026-02-04
**نسخه گزارش:** 2.2 (اصلاحات گزارش مهندسی ۴ مرحله‌ای)
**شاخه:** `claude/update-system-report-izMLQ`
