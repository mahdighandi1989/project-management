# گزارش جامع سیستم مدیریت پروژه هوشمند

**تاریخ:** 2026-02-08
**شاخه:** `claude/review-project-structure-79Bdk`
**وضعیت:** به‌روز شده - نسخه 3.0 (به‌روزرسانی جامع بازرس ویژه + Visual Debug + Smart-Chat پیشرفته)

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
9. [بازرس ویژه (Inspector Tab)](#9-بازرس-ویژه-inspector-tab)

---

## 1. خلاصه اجرایی

### آمار کلی پروژه (به‌روز شده 2026-02-08)

| بخش | تعداد فایل | خط کد |
|-----|-----------|--------|
| Backend Routes | 26 | ~41,261 |
| Backend Services | 50 | ~34,995 |
| Database Models | 11 | ~1,821 |
| Frontend Pages | 12 | ~17,703 |
| Frontend Components | 12 | ~8,370 |
| **کل** | **129** | **~114,123** |

### فایل‌های کلیدی

| فایل | خط کد | توضیح |
|------|-------|--------|
| render_logs.py | 10,308 | بک‌اند بازرس ویژه + لاگ Render |
| projects/[id]/page.tsx | 11,590 | فرانت‌اند صفحه پروژه |
| project_memory.py | 6,750 | مدیریت حافظه و فیلدها |
| project_journal.py | 5,705 | ژورنال و گزارشات |
| project_health.py | 5,416 | تحلیل سلامت |

### وضعیت کلی

| وضعیت | تعداد | توضیح |
|-------|-------|--------|
| ✅ رفع شده | 55+ | شامل تمام باگ‌های بازرس ویژه |
| ⚠️ نیاز به بهبود | 6 | موارد UI و بهینه‌سازی |
| 🔴 باقیمانده | 3 | مشکلات جزئی |
| 🆕 قابلیت جدید | 25+ | شامل سیستم کامل بازرس ویژه |

---

## 2. بخش‌های اصلی سیستم

### بخش ۱: راه‌اندازی خودکار پروژه

**موقعیت:** تب حافظه و دستورات
**فایل:** `backend/app/services/project_auto_setup.py` (2,325 خط)

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

---

### بخش ۲: پرسش از AI درباره پروژه

**موقعیت:** تب فایل‌ها

#### ✅ قابلیت‌های موجود

- پاسخ به پرسش با اشراف کامل به پروژه
- ایجاد فیلدهای جدید با چک تکراری
- ادغام با فیلدهای مشابه موجود
- تحلیل AI برای تعیین فایل‌های هدف
- درخواست قابلیت جدید (Feature Request)

---

### بخش ۳: تحلیل سلامت پروژه

**فایل‌های اصلی:**
- `backend/app/services/deep_analysis_service.py`
- `backend/app/services/project_health_analyzer.py`
- `backend/app/api/routes/project_health.py` (5,416 خط)

#### تحلیل سه‌مرحله‌ای

| مرحله | وزن | توضیح |
|-------|-----|--------|
| **Micro** | 60% | بررسی تک‌تک فایل‌ها |
| **Macro** | 20% | همکاری بین فایل‌ها |
| **Structural** | 15% | معماری کلی |
| **Finalizing** | 5% | محاسبه نمرات نهایی |

---

### بخش ۴: گزارش مهندسی

**فایل‌های اصلی:**
- `backend/app/api/routes/project_journal.py` (5,705 خط)
- `backend/app/services/deep_analysis_service.py`
- `backend/app/services/quick_approval_service.py`

#### ۴ مرحله گزارش مهندسی

| مرحله | توضیح |
|-------|--------|
| **۱. بررسی پروژه** | اعتبارسنجی فیلدهای پویای موجود |
| **۲. انطباق با تحلیل سلامت** | تایید ایرادات + تولید فیلدهای اقدام‌محور |
| **۳. اعتبارسنجی مدل‌ها** | ارزیابی عملکرد مدل‌ها + ثبت امتیاز |
| **۴. به‌روزرسانی نقشه راه** | تعیین حالت ایده‌آل + چک‌لیست |

---

### بخش ۵: لاگ‌های Render

**فایل:** `backend/app/api/routes/render_logs.py` (10,308 خط)

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

---

### بخش ۶: ژورنال و گزارشات

**فایل:** `backend/app/services/journal_service.py` (734 خط)

#### ✅ پیاده‌سازی شده
- 15+ نوع فعالیت ثبت شده
- قابلیت دانلود در سه فرمت (JSON, CSV, XLSX)

---

### بخش ۷: بایگانی عمومی

**موقعیت:** تب بایگانی ذیل تب تحلیل سلامت

#### ✅ پیاده‌سازی شده
- بایگانی همه موارد پاک شده
- دسته‌بندی (issues, health, files...)
- قابل باز کردن و مشاهده محتوا
- دانلود در 3 فرمت

---

### بخش ۸: سیستم راهنمای جامع

**موقعیت:** در تمام صفحات فرانت‌اند
**فایل‌ها:**
- `frontend/src/components/help/HelpSystem.tsx` (466 خط)
- `frontend/src/components/help/HelpTooltip.tsx` (131 خط)
- `frontend/src/components/help/HelpProvider.tsx` (286 خط)
- `frontend/src/components/help/helpData.ts` (1,265 خط)

#### ✅ قابلیت‌ها
- دکمه شناور راهنما ❓ در گوشه پایین چپ
- پنل کشویی با توضیحات کامل
- دیاگرام ساختاری Mermaid
- قابلیت دانلود Markdown
- حالت Tooltip با Ctrl+H
- جستجو و گروه‌بندی المان‌ها

---

## 3. تغییرات اخیر انجام شده (2026-02-06 تا 2026-02-08)

### 🆕 قابلیت‌های جدید پیاده‌سازی شده

#### 3.1 سیستم Smart-Chat پیشرفته
- **طبقه‌بندی هوشمند پیام:** سه نوع QUESTION / ERROR_LOG / ACTION
- **محدودیت فایل متفاوت:** QUESTION=5, ERROR_LOG=10, ACTION=15
- **خلاصه ساختار پروژه** (`_build_project_tree_summary`) در همه پرامپت‌ها
- **انتخاب متوازن فایل** (`_ensure_balanced_selection`) از دایرکتوری‌های مختلف
- **ردیابی تاریخچه فایل‌ها** (`previously_read_files`) برای جلوگیری از تکرار
- **پاسخ‌گویی به پیام خاص** (Reply-to) با استفاده از مدل اصلی

#### 3.2 Visual Debug با عکس‌برداری
- **عکس‌برداری از صفحه**: endpoint `POST /api/render/inspector/screenshot`
- **تحلیل بصری**: endpoint `POST /api/render/inspector/visual-debug` (SSE)
- **انتخاب خودکار مدل‌های Vision** (GPT-4o, Gemini Pro Vision)
- **خواندن 8-12 فایل مرتبط** برای context تحلیل
- **پرامپت اختصاصی** `VISUAL_DEBUG_SYSTEM_PROMPT` با دسترسی به عکس + لاگ + فایل‌ها

#### 3.3 تشخیص و ردیابی Overlay ها
- **MutationObserver** برای تشخیص overlay‌های جدید
- **اسکن دوره‌ای** هر 2000ms برای المان‌های fullscreen
- **pointerdown fallback** برای کلیک‌هایی که overlay مانع می‌شود
- **console interception کامل**: log, warn, error, info, debug

#### 3.4 سیستم Prompt Field Management
- **مدیریت فیلدهای پرامپت**: دستورات، حافظه، آموزش
- **دسته‌بندی**: instruction, function, variable, context, constraint
- **دکمه ارسال به چت** (Send-to-chat)
- **Highlight** فیلدهای در حال استفاده
- **تزریق در پرامپت Smart-Chat** به صورت `prompt_fields_text`

#### 3.5 جستجوی خطا و اصلاح خودکار (AI Investigation)
- **endpoint**: `POST /api/render/inspector/analyze-error`
- **دو مرحله‌ای**: بررسی (investigate) + اصلاح (fix)
- **خواندن دو مرحله‌ای فایل‌ها**: اول فایل‌های مرتبط با خطا، بعد فایل‌های model/DB
- **دفاع دو لایه** در برابر action_plan‌های ساختگی AI
- **دکمه Apply Fix** برای اعمال تغییرات پیشنهادی

### 🔧 باگ‌فیکس‌های مهم (45+ کامیت)

| دسته | تعداد | توضیح |
|------|-------|--------|
| Smart-Chat | 12+ | طبقه‌بندی اشتباه، خواندن فایل ناموفق، پاسخ خالی، timeout |
| SSE Streaming | 4 | قطعی اتصال، lock bug، chunk parsing، heartbeat |
| Client-Side Crashes | 5 | undefined property access در صفحات مختلف |
| Verification System | 5 | تیک‌مارک‌ها، ذخیره لاگ، شمارشگر صفر |
| Bridge Script | 3 | force_update، تشخیص وضعیت، cross-origin |
| مدل‌ها و API | 4 | timeout، model selection، GitHub push، token fallback |

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
| ۲-۶ | React Error #31 | ✅ رفع شده |
| ۲-۷ | 'str' has no attribute 'get' | ✅ رفع شده |
| ۲-۸ | can only concatenate list to list | ✅ رفع شده |
| ۲-۹ | NameError: ActivityLog not defined | ✅ رفع شده |
| ۲-۱۰ | Model not found: openai | ✅ رفع شده |

### دسته ۳: تحلیل سلامت

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۳-۱ | ادغام ایرادات ناپایدار | ⚠️ نیاز به بهبود |
| ۳-۲ | عدم بررسی فرانت‌اند | 🔴 باقیمانده |
| ۳-۳ | محدودیت 100 فایل در UI | 🔴 Backend OK، Frontend نه |

### دسته ۴: انتقال ایرادات

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۴-۱ | انتقال 0 یافته | ✅ رفع شده |
| ۴-۴ | شمارنده کم نمیشه | ✅ رفع شده |

### دسته ۵: لاگ Render

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۵-۱ | عدم به‌روزرسانی خودکار | ✅ رفع شده (APScheduler) |

### دسته ۶: رابط کاربری

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۶-۱ | رنگ فونت همرنگ پس‌زمینه | ⚠️ نیاز به اصلاح |

### دسته ۷: بازرس ویژه (جدید)

| شماره | مشکل | وضعیت |
|-------|------|--------|
| ۷-۱ | Cross-origin postMessage | ✅ حل شده با WebSocket Bridge |
| ۷-۲ | Overlay ها کلیک را می‌بلعند | ✅ حل شده با pointerdown + MutationObserver |
| ۷-۳ | طبقه‌بندی اشتباه پیام‌ها | ✅ حل شده با prompt engineering عمیق |
| ۷-۴ | AI فایل‌ها را نمی‌خواند | ✅ حل شده با two-pass reading |
| ۷-۵ | پاسخ خالی از مدل‌ها | ✅ حل شده با error handling بهتر |
| ۷-۶ | SSE قطعی و timeout | ✅ حل شده با heartbeat + chunk parser |
| ۷-۷ | تیک‌مارک‌های تایید گیر می‌کنند | ✅ حل شده |
| ۷-۸ | Client crash از undefined | ✅ حل شده با defensive access |
| ۷-۹ | عکس‌برداری بصری (Visual Debug) | ✅ پیاده‌سازی شده |
| ۷-۱۰ | مدیریت فیلدهای پرامپت | ✅ پیاده‌سازی شده |

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
| ۸ | ارتقای پرسش از AI برای ایده‌ها | ✅ پیاده‌سازی شده |
| ۹ | سیستم مدیریت لاگ‌های Render | ✅ پیاده‌سازی شده |
| ۱۰ | مدیریت پرامپت‌ها + نمایش زنده | ✅ پیاده‌سازی شده (Inspector) |
| ۱۱ | بازرس ویژه با چت هوشمند | ✅ پیاده‌سازی شده |
| ۱۲ | عکس‌برداری بصری + تحلیل AI | ✅ پیاده‌سازی شده |
| ۱۳ | تشخیص overlay و خطاهای بصری | ✅ پیاده‌سازی شده |

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

## 7. ساختار تب‌ها (به‌روز شده)

```
├── تب حافظه و دستورات
│   └── راه‌اندازی خودکار پروژه ✅
│       └── انتخاب مدل
│       └── سینک با GitHub
│       └── ایجاد فیلدهای پویا
│
├── تب فایل‌ها
│   └── پرسش از AI درباره پروژه ✅
│       └── درخواست قابلیت جدید (Feature Request)
│       └── تبدیل به فیلد
│       └── تحلیل AI
│
├── تب تحلیل سلامت
│   ├── زیرتب نمای کلی
│   ├── زیرتب ایرادات + تایید سریع
│   ├── زیرتب بایگانی عمومی ✅
│   ├── زیرتب فایلها
│   ├── زیرتب امنیت
│   └── زیرتب پوشش تست
│
├── تب ژورنال و گزارشات
│   ├── ژورنال ✅ (15+ نوع فعالیت)
│   ├── نقشه راه
│   └── گزارشات
│
├── تب گزارش مهندسی
│   ├── ۴ مرحله تحلیل
│   ├── Pre-Execution Validation
│   ├── انتخاب مدل
│   └── سطح عمق (quick/standard/deep/thorough)
│
├── 🆕 تب بازرس ویژه (Inspector) ✅
│   ├── پیش‌نمایش زنده (iframe)
│   │   └── Bridge Script تزریقی
│   │   └── WebSocket Bridge Hub
│   │   └── تشخیص Overlay
│   │   └── Console Interception
│   ├── چت هوشمند (Smart-Chat) ✅
│   │   └── طبقه‌بندی خودکار پیام
│   │   └── انتخاب فایل متوازن
│   │   └── ردیابی تاریخچه فایل
│   │   └── Reply-to پیام خاص
│   │   └── SSE Streaming
│   ├── Visual Debug ✅
│   │   └── عکس‌برداری از صفحه
│   │   └── تحلیل بصری با Vision Models
│   │   └── ادغام لاگ + عکس + فایل
│   ├── مدیریت فیلدهای پرامپت ✅
│   │   └── دستورات عمومی
│   │   └── حافظه
│   │   └── آموزش
│   ├── جستجوی خطا و اصلاح ✅
│   │   └── AI Investigation
│   │   └── Apply Fix
│   │   └── دفاع در برابر hallucination
│   ├── سیستم تایید پیام ✅
│   │   └── اسکن لاگ بک‌اند
│   │   └── تفکیک console از backend
│   │   └── نشانگرهای بصری (✓/✕)
│   └── مدیریت Session ✅
│       └── ذخیره/بارگذاری
│       └── بایگانی
│       └── مشاهده تاریخچه
│
└── تنظیمات
    ├── API Keys
    ├── مدل‌ها
    └── لاگ‌های Render ✅
```

---

## 8. جداول خلاصه

### جدول خلاصه مشکلات

| وضعیت | تعداد | درصد |
|-------|-------|------|
| ✅ رفع شده | 55+ | 85%+ |
| ⚠️ نیاز به بهبود | 6 | 9% |
| 🔴 باقیمانده | 3 | 5% |
| **کل** | **~65** | **100%** |

### کامیت‌های اصلی بازرس ویژه (2026-02-06 تا 2026-02-08)

| Commit | توضیح |
|--------|--------|
| `8ec9297` | Enhanced overlay click detection + visual debug UI improvements |
| `df28faf` | Visual debug with screenshots, full console interception, and error overlay detection |
| `ab4a065` | Smart-chat major upgrade — higher file limits, smarter selection, file history tracking |
| `f8874a8` | Replace DB field auto-injection with general system instructions + add send-to-chat button |
| `5c892f4` | 4 improvements - verify retry, visual task detection, field relevance, search fallthrough |
| `c974b41` | 5 critical issues - GitHub push, model selection, prompt fields, service detection, token fallback |
| `5b0cd00` | Inspector prompt field management - instructions, memory & training controls |
| `801fba4` | Smart-chat AI models fail to understand user intent - deep prompt engineering overhaul |
| `ad09b6f` | Smart-chat models blind to project structure - add tree summary, balanced file selection |
| `c50d5ec` | Inspector smart-chat - wrong classification, no file reading, empty responses, timeouts |
| `3f02a8c` | Smart contextual chat with message classification + Apply button |
| `2eeaab2` | AI-powered error investigation and auto-fix in Inspector tab |
| `9ed3fc2` | Inspector session persistence, chat panel actions, and backend log verification |
| `962de99` | Replace postMessage with WebSocket bridge to solve cross-origin issue |

---

## 9. بازرس ویژه (Inspector Tab) - گزارش جامع

### وضعیت کلی (به‌روزرسانی 2026-02-08)

| معیار | وضعیت |
|-------|--------|
| وضعیت | 🟢 **فعال و عملیاتی** - اکثر قابلیت‌ها پیاده‌سازی شده |
| درصد پیشرفت | ~85% |
| تاریخ شروع | 2026-02-04 |
| آخرین به‌روزرسانی | 2026-02-08 |
| تعداد کامیت‌ها | 50+ |
| خطوط کد بک‌اند | ~6,000+ (از render_logs.py) |
| خطوط کد فرانت‌اند | ~3,000+ (از page.tsx) |

### فازهای توسعه

#### فاز 1: Playwright (منسوخ)
- تلاش برای تعامل با صفحه از طریق headless browser
- 7 راه‌حل مختلف امتحان شد - همه ناموفق
- مشکل اصلی: iframe و Playwright دو instance جدا بودند
- **نتیجه:** کنار گذاشته شد

#### فاز 2: Bridge Script (2026-02-04 تا 2026-02-05)
- تزریق اسکریپت پل در پروژه کاربر
- تشخیص خودکار فریم‌ورک (Next.js, React, Vue, Angular, Python)
- مشکل cross-origin برای postMessage
- **نتیجه:** postMessage ناپایدار بود

#### فاز 3: WebSocket Bridge Hub (2026-02-05 تا حال)
- جایگزینی postMessage با WebSocket
- Bridge Hub مرکزی در بک‌اند
- ارتباط دو طرفه بین Bridge Script و Inspector
- **نتیجه:** ✅ حل مشکل cross-origin

### معماری فعلی

```
┌──────────────────────────────────────────────────────┐
│                      Frontend                         │
│  ┌────────────────┐     ┌───────────────────────┐    │
│  │    iframe       │     │     Chat Panel        │    │
│  │  (پروژه کاربر) │     │  + Smart-Chat         │    │
│  │                 │     │  + Visual Debug        │    │
│  │ Bridge Script ──┼─────│──► WebSocket Client    │    │
│  │  (تزریق شده)   │     │                       │    │
│  └────────────────┘     └───────────────────────┘    │
│           │                        │                  │
│           │ WebSocket              │ API              │
│           ▼                        ▼                  │
│  ┌─────────────────────────────────────────────┐     │
│  │        Backend (FastAPI)                     │     │
│  │                                              │     │
│  │  ┌──────────────┐  ┌──────────────────┐     │     │
│  │  │ Bridge Hub   │  │   Smart-Chat     │     │     │
│  │  │ (WebSocket)  │  │   (SSE Stream)   │     │     │
│  │  └──────────────┘  └──────────────────┘     │     │
│  │                                              │     │
│  │  ┌──────────────┐  ┌──────────────────┐     │     │
│  │  │ Visual Debug │  │   Session DB     │     │     │
│  │  │ (Screenshot) │  │   (Messages)     │     │     │
│  │  └──────────────┘  └──────────────────┘     │     │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

### قابلیت‌های پیاده‌سازی شده

#### 9.1 Bridge Script و اتصال

| قابلیت | وضعیت | توضیح |
|--------|--------|--------|
| تزریق Bridge Script | ✅ | سه قالب: HTML, JS/TS, Next.js Client Component |
| تشخیص خودکار فریم‌ورک | ✅ | Next.js (App/Pages), React, Vue, Angular, Python |
| WebSocket Bridge Hub | ✅ | ارتباط دو طرفه بدون محدودیت cross-origin |
| ثبت رویدادها | ✅ | click, pointerdown, scroll, input, focus, error |
| Console Interception | ✅ | log, warn, error, info, debug (حداکثر 200 لاگ) |
| تشخیص Overlay | ✅ | MutationObserver + اسکن دوره‌ای 2000ms |
| تشخیص خطای بصری | ✅ | error-overlay detection با CSS selector ها |
| Debounce | ✅ | 100ms برای جلوگیری از flood |

#### 9.2 Smart-Chat

| قابلیت | وضعیت | توضیح |
|--------|--------|--------|
| طبقه‌بندی خودکار پیام | ✅ | QUESTION / ERROR_LOG / ACTION |
| خواندن فایل از GitHub | ✅ | server-side با token |
| انتخاب متوازن فایل | ✅ | از دایرکتوری‌های مختلف |
| خلاصه ساختار پروژه | ✅ | درخت فایل در prompt |
| Reply-to | ✅ | پاسخ با مدل اصلی |
| SSE Streaming | ✅ | progress, response, error events |
| Heartbeat | ✅ | جلوگیری از QUIC timeout |
| Context Window Management | ✅ | محاسبه خودکار max_input_chars |
| ردیابی فایل‌های خوانده شده | ✅ | previously_read_files |

#### 9.3 Visual Debug

| قابلیت | وضعیت | توضیح |
|--------|--------|--------|
| عکس‌برداری از صفحه | ✅ | با ابعاد قابل تنظیم |
| تحلیل بصری با AI | ✅ | Vision models (GPT-4o, Gemini) |
| ادغام عکس + لاگ + فایل | ✅ | context کامل برای AI |
| پرامپت اختصاصی | ✅ | VISUAL_DEBUG_SYSTEM_PROMPT |
| SSE Streaming | ✅ | نمایش لحظه‌ای نتایج |
| انتخاب خودکار مدل Vision | ✅ | از MODEL_REGISTRY |

#### 9.4 مدیریت Session

| قابلیت | وضعیت | توضیح |
|--------|--------|--------|
| ایجاد خودکار session | ✅ | هنگام روشن کردن بازرس |
| ذخیره پیام‌ها در DB | ✅ | InspectorMessage model |
| بارگذاری تاریخچه | ✅ | بازگردانی chat هنگام ورود مجدد |
| بایگانی session | ✅ | با عنوان خودکار |
| مشاهده session‌های قبلی | ✅ | read-only |

#### 9.5 تایید پیام (Verification)

| قابلیت | وضعیت | توضیح |
|--------|--------|--------|
| اسکن لاگ بک‌اند | ✅ | در بازه زمانی اقدام |
| تفکیک console از backend | ✅ | جداسازی خطاهای واقعی |
| نشانگر بصری | ✅ | 🔍 pending / ✓ ok / ✕ error |
| Retry خودکار | ✅ | با exponential backoff |
| ذخیره در DB | ✅ | backend_verified + log_summary |

#### 9.6 AI Investigation & Fix

| قابلیت | وضعیت | توضیح |
|--------|--------|--------|
| بررسی خطا (investigate) | ✅ | تحلیل لاگ‌ها + فایل‌ها |
| اصلاح (fix) | ✅ | تولید action_plan |
| Apply Fix | ✅ | اعمال تغییرات |
| دفاع در برابر hallucination | ✅ | dual-layer validation |
| two-pass file reading | ✅ | فایل‌های مرتبط + model files |

#### 9.7 Endpoints بک‌اند

| # | Endpoint | نوع | توضیح |
|---|----------|-----|--------|
| 1 | `ws/bridge/{project_id}` | WebSocket | Bridge Hub |
| 2 | `inspector/session/create` | POST | ایجاد session |
| 3 | `inspector/sessions/{project_id}` | GET | لیست sessions |
| 4 | `inspector/session/{id}/messages` | GET | پیام‌های session |
| 5 | `inspector/session/message` | POST | ذخیره پیام |
| 6 | `inspector/session/{id}/archive` | POST | بایگانی session |
| 7 | `inspector/smart-chat` | POST (SSE) | چت هوشمند |
| 8 | `inspector/smart-select-model/{id}` | GET | انتخاب مدل |
| 9 | `inspector/models` | GET | لیست مدل‌ها |
| 10 | `inspector/screenshot` | POST | عکس‌برداری |
| 11 | `inspector/visual-debug` | POST (SSE) | تحلیل بصری |
| 12 | `inspector/vision-models` | GET | مدل‌های Vision |
| 13 | `inspector/message/{id}/verify` | POST | تایید پیام |
| 14 | `inspector/inject-bridge` | POST | تزریق bridge |
| 15 | `inspector/check-bridge-status` | POST | وضعیت bridge |
| 16 | `inspector/bridge-connections/{id}` | GET | اتصالات bridge |
| 17 | `inspector/analyze-error` | POST | تحلیل خطا |
| 18 | `inspector/visual-scan` | POST | اسکن بصری |
| 19 | `inspector/get-elements` | POST | دریافت المان‌ها |
| 20 | `inspector/find-and-click` | POST | پیدا کردن و کلیک |

### درخواست‌های باقیمانده کاربر

#### درخواست ۱: خطاهای لایه بالاتر از Bridge Script
**وضعیت: ✅ پیاده‌سازی شده**

| مورد | وضعیت |
|------|--------|
| تشخیص overlay ها | ✅ MutationObserver + اسکن دوره‌ای |
| pointerdown fallback | ✅ برای کلیک‌های بلعیده شده |
| Console interception کامل | ✅ log, warn, error, info, debug |
| Error overlay detection | ✅ CSS selectors + className matching |

#### درخواست ۲: عکس‌برداری بصری + تحلیل پیشرفته
**وضعیت: 🔄 در حال تکمیل (بخش اولیه پیاده‌سازی شده)**

| مورد | وضعیت | توضیح |
|------|--------|--------|
| عکس‌برداری از صفحه | ✅ | endpoint screenshot |
| تعداد نامحدود عکس | ⏳ | فعلاً تک‌عکس |
| لاگ بک‌اند همراه عکس | ✅ | ارسال به visual-debug |
| لاگ کنسول تفکیک شده | ✅ | console vs backend جدا |
| شناسایی آدرس‌های مرتبط | ⏳ | نیاز به پیاده‌سازی |
| توضیح اختیاری کاربر | ⏳ | نیاز به UI |
| انتخاب مدل قبل از بررسی | ⏳ | فعلاً خودکار |
| تایید کاربر قبل از اجرا | ⏳ | نیاز به UI |
| پرامپت ثابت قابل مشاهده | ✅ | VISUAL_DEBUG_SYSTEM_PROMPT + fields_in_use |
| اعمال تغییرات در فایل‌ها | ⏳ | فعلاً فقط پیشنهاد |

---

## نتیجه‌گیری

### ✅ دستاوردهای اصلی (نسخه 3.0)

1. **سیستم کامل بازرس ویژه:** 50+ کامیت، 20 endpoint، 9000+ خط کد
2. **WebSocket Bridge Hub:** حل مشکل cross-origin
3. **Smart-Chat پیشرفته:** طبقه‌بندی هوشمند + خواندن فایل + SSE
4. **Visual Debug:** عکس‌برداری + تحلیل بصری با Vision models
5. **Session Management:** ذخیره و بازیابی کامل
6. **Verification System:** تایید خودکار با لاگ بک‌اند
7. **Overlay Detection:** تشخیص و bypass المان‌های روی صفحه

### ⚠️ موارد باقیمانده

1. عکس‌برداری چندتایی با UI بهتر
2. انتخاب مدل توسط کاربر قبل از تحلیل بصری
3. شناسایی خودکار آدرس‌های مرتبط
4. اعمال مستقیم تغییرات در فایل‌های GitHub
5. بهبود UI محدودیت فایل‌ها در تحلیل سلامت
6. تحلیل فرانت‌اند در تحلیل سلامت

### 📊 خلاصه پیشرفت کلی

| معیار | نسخه 2.6 (02-06) | نسخه 3.0 (02-08) |
|-------|-------------------|-------------------|
| خط کد بک‌اند Inspector | ~2,000 | ~6,000+ |
| خط کد فرانت‌اند Inspector | ~1,000 | ~3,000+ |
| Endpoint ها | 6 | 20 |
| باگ‌فیکس‌ها | 10 | 45+ |
| قابلیت‌های اصلی | 4 | 10+ |
| render_logs.py | ~5,800 خط | ~10,308 خط |
| page.tsx | ~8,500 خط | ~11,590 خط |

---

**تاریخ به‌روزرسانی:** 2026-02-08
**نسخه گزارش:** 3.0
**شاخه:** `claude/review-project-structure-79Bdk`
