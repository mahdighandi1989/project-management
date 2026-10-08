# دفتر کار (Work Log) — ثبتِ جزئیِ همهٔ کارها

ثبتِ پیوستهٔ هر یافته، تصمیم، تغییر، راستی‌آزمایی و بازگشت در project-management (الگو: `docs/WORKLOG.md` در Detective-1
و `docs/AUDIT_LOG.md` در ALLIN1). **جدیدترین ورودی در انتهای فایل است.** هر کس (Claude یا هر هوش مصنوعی/انسانِ دیگر)
پس از **هر کار** یک بخش به انتها اضافه می‌کند — هیچ ورودیِ قبلی پاک یا بازنویسی نمی‌شود؛ اصلاح = ورودیِ تازه با برچسب
`[REVERT]` یا `[CORRECTION]`.

**قالبِ هر سطر:** `- **[نوع]** شرح — دلیل/مدرک (فایل، کامیت، خروجیِ تست)`
**انواع:** `[FINDING]` یافته · `[DECISION]` تصمیم · `[CHANGE]` تغییرِ کد/پیکربندی · `[VERIFY]` راستی‌آزمایی ·
`[REVERT]` بازگشت · `[CORRECTION]` اصلاحِ ثبتِ قبلی · `[OWNER]` دستور/درخواستِ مالک · `[TODO]` کارِ باز · `[BLOCKED]` مسدود

**امضا الزامی است:** آخرین خطِ هر بخش —
`> **امضا:** \`<agent-id>\` · YYYY-MM-DD · <یک خط: چطور راستی‌آزمایی شد>` (جزئیات: `AGENTS.md` §4).
`scripts/docs_gate.py` اگر **جدیدترین** بخش امضا نداشته باشد ارسال را رد می‌کند.

هر بخش با `## تاریخ (شماره) — عنوان` شروع می‌شود و در صورتِ وجود، کامیت را ذکر می‌کند.

---

## 2026-10-08 (۱) — «نظارت و سرکشی» و ناظرِ خودکار، به الگوی Detective-1 و ALLIN1

- **[OWNER]** مالک خواست سامانهٔ «نظارت و سرکشی» دو پروژهٔ Detective-1 و ALLIN1 (بدونِ هیچ تغییری در آن دو) کامل و
  دقیق روی این پروژه پیاده شود: شناختن و ثبتِ همهٔ صفحه‌ها و زیرصفحه‌ها با مختصات (چه الان، چه بعداً)، گزینهٔ فوری و
  روتینِ فوری مثلِ Detective-1، آپلودِ هر نوع فایل، بخشِ «درخواستِ عمومی» مثلِ ALLIN1، تغییرِ رنگِ گزارش‌ها با وضعیت و
  بایگانیِ تأییدشده‌ها در دورِ بعد، ثبتِ تازه ذیلِ هر گزارش با فایلِ همان ثبت، انتخابِ «گزارشِ جدید / ذیلِ گزارشِ باز»
  هنگامِ اسکرین، الگوگیری از زمان‌بندی و محلِ بایگانیِ پرامپت‌های روتین‌ها؛ و فایل‌ها به‌جای بک‌اند در پوشهٔ پروژه در
  گوگل درایو با رفرنس و لینکِ مشخص ذخیره شوند و «در بک‌اند چیزی نگه داشته نشود».
- **[FINDING]** روتین‌های دو پروژهٔ مرجع: دورِ کامل دو بار در هفته + صفِ فوری هر ۳ ساعت با دقیقهٔ جدا، هر اجرا نشستِ
  تازه؛ پرامپتِ روتین کوتاه و ثابت و فقط ارجاع به `docs/supervisor/PROMPT.md` / `URGENT_PROMPT.md` با frontmatter ِ
  نسخه‌دار و بایگانیِ نسخه‌های قبلی در `docs/supervisor/archive/`؛ مجوزِ پوش روی `main` در متنِ خودِ روتین.
- **[FINDING]** این پروژه ورودِ کاربر نداشت، به گوگل درایو وصل نبود، و دیسکِ Render آن ۱ گیگ است (پایگاه‌داده هم همان‌جاست).
- **[DECISION]** هویتِ ناظر با توکن (`X-Supervisor-Token` = `SUPERVISOR_TOKEN`، با بازگشت به `EXTERNAL_TOOL_TOKEN`)؛
  اسکریپت‌ها توکن و نشانی را در زمانِ اجرا از Render API می‌خوانند (الگوی Detective-1) — هیچ رازی در ریپو.
- **[DECISION]** فایل‌ها فقط «در راه» روی دیسک (spool)؛ سپس انتقال به `project-management/نظارت و سرکشی/گزارش-NNNN/`
  با رفرنسِ `PM-INS-NNNN-Fnn`، تطبیقِ MD5، و حذفِ نسخهٔ محلی؛ متنِ استخراج‌شده هم به‌صورتِ فایلِ کناری در درایو.
  گزینهٔ ردشده: نگه‌داشتنِ متن/بایت در پایگاه‌داده (الگوی ALLIN1) — خلافِ خواستهٔ صریحِ مالک.
- **[CHANGE]** بک‌اند: `models/inspection.py`، `api/routes/inspection.py`، `services/{gdrive,inspection_files,supervisor_rounds}.py`.
  فرانت: `lib/inspection/*`، `components/inspection/*`، `app/inspection/page.tsx`، ادغام در `Layout.tsx`.
  ناظر: `docs/supervisor/*` (PROMPT v1، URGENT_PROMPT v1، README، RUNLOG، OPEN_ITEMS، INVENTORY)، `scripts/supervisor/*`.
  کامیت‌ها `747b000`، `2bbe78b`، `8b14635`؛ مالک با PR #929 در `main` ادغام کرد و Render دیپلوی کرد (`6d440f9`).
- **[CHANGE]** دو روتین ساخته شد: `trig_0185k7gpGZBvVs9JY9pZHiHJ` (کامل، `37 0 * * 2,5`) و `trig_01SmGK1H3EyJoWpeSBVcqj8F`
  (فوری، `11 */3 * * *`)؛ تا رسیدنِ کد به `main` متوقف ماندند.
- **[VERIFY]** pytest ۷۰۲ قبول / ۳ رد؛ `npm run build` سبز؛ سرتاسری با Chromium روی نسخهٔ محلی (کادر → برگه → ذیلِ برگه →
  urgent → answer با نگهبان‌ها → تأیید → بایگانی)؛ `surface_scan.py` محلی ۱۳ صفحه / ۲۵ نقشه / ۰ شکست.

> **امضا:** `claude-opus-5-5 (Claude Code)` · 2026-10-08 · pytest + next build + سرتاسری با Chromium روی نسخهٔ محلی

## 2026-10-08 (۲) — ارسالِ خودکار، دفترِ کار، ورود با گوگل، و فعال‌سازیِ روتین‌ها

- **[OWNER]** مالک سه الگوی دیگر را هم از دو پروژه خواست: (۱) کامیت/پوش/دیپلوی خودکار پس از هر کار بدونِ کارِ دستی در
  GitHub؛ (۲) ثبتِ دقیقِ همهٔ تغییرات در ریپو؛ (۳) ورود با گوگل و «بدونِ لاگین چیزی نشون نده». پرسید
  `GOOGLE_DRIVE_REFRESH_TOKEN` را از کجا بگیرد (خالی گذاشته) و `SUPERVISOR_TOKEN` چیست؛ خواست همه چیز چک و روتین‌ها
  روشن شوند. اسکرین‌شات: دکمهٔ «اتصال به گوگل درایو» ⇒ `Error 400: origin_mismatch`.
- **[FINDING]** `origin_mismatch` یعنی نشانیِ `https://ai-creator-frontend.onrender.com` در «Authorized JavaScript origins»
  ِ همان OAuth client در Google Cloud Console نیست — تنظیمِ سمتِ گوگل است، نه کد. ورود با گوگل هم به همین نیاز دارد.
  با دکمهٔ اتصال، `GOOGLE_DRIVE_REFRESH_TOKEN` لازم نیست؛ مقدارِ خالی نادیده گرفته می‌شود (`gdrive._refresh_token`).
- **[FINDING]** production روی `6d440f9` زنده است؛ `client_configured: true`، `connected: false`.
- **[FINDING]** ریشه‌یابیِ `.gitignore`: قاعدهٔ `archive/` در ریشه، `docs/supervisor/archive/README.md` را بی‌صدا از ریپو
  بیرون نگه داشته بود (همان کلاسِ باگِ ثبت‌شده در Detective-1). با `!archive/` در `docs/supervisor/.gitignore` رفع شد و
  `scripts/ship.sh` حالا پیش از هر ارسال این را می‌گیرد.
- **[CHANGE]** `SUPERVISOR_TOKEN` (تصادفی، فقط روی Render، هیچ‌جا چاپ نشد) روی سرویسِ بک‌اند تنظیم شد.
- **[BLOCKED]** تنظیمِ `ADMIN_EMAILS` روی Render از این سشن را نگهبانِ مجوز رد کرد ⇒ مالک خودش باید بگذارد.
- **[DECISION]** دیوارِ ورود **خودکار با تنظیمِ `ADMIN_EMAILS` روشن می‌شود** — پیش از آن هیچ مالکی نمی‌تواند وارد شود و
  روشن‌کردنش مالک را از برنامهٔ خودش بیرون می‌انداخت. `AUTH_DISABLED=1` کلیدِ اضطراری است (مثلِ ALLIN1).
  گزینهٔ ردشده: «اولین واردشونده مالک می‌شود» — هر غریبه‌ای که زودتر برسد مالک می‌شد.
- **[DECISION]** دیوار به‌صورتِ یک middleware ِ ASGI روی همهٔ HTTP؛ استثناها: OPTIONS، `/health`، `/`،
  `/api/auth/{config,google,supervisor-session}`، وب‌هوکِ تلگرام، و فراخواننده‌های ماشینی با رازِ خودشان
  (`X-External-Token` ِ workflow ِ GitHub، `X-Admin-Token`، `X-Supervisor-Token`). WebSocketها (پلِ بازرس در اپ‌های
  دیگر) دست نخوردند. فرانت به‌جای ویرایشِ صدها فراخوانی، یک رهگیرِ fetch/XHR/EventSource دارد.
- **[CHANGE]** `core/auth.py`، `api/routes/auth.py`، `models/app_user.py`، `tests/test_auth.py`، `tests/conftest.py`
  (دیوار برای مجموعه‌تستِ قدیمی خاموش)، `frontend/src/lib/auth.tsx` (صفحهٔ ورود + رهگیر)، `app/users/page.tsx`،
  کادرِ حساب و «خروج» در منو؛ لینک‌های تصویر/فایلِ نظارت با `access_token` (فقط GET)؛ اسکریپت‌های مرورگرِ ناظر با
  نشستِ `supervisor` (`/api/auth/supervisor-session`).
- **[CHANGE]** ارسال و ثبت: `scripts/ship.sh`، `scripts/docs_gate.py`، `.claude/settings.json` (+ hook ِ Stop)، `CLAUDE.md`،
  `AGENTS.md`، `GEMINI.md`، `.github/copilot-instructions.md`، همین `docs/WORKLOG.md`؛ پرامپت‌های ناظر نسخهٔ ۲ (نسخهٔ ۱
  بایگانی شد) با وظیفهٔ ثبت در WORKLOG.

> **امضا:** `claude-opus-5-5 (Claude Code)` · 2026-10-08 · pytest (auth + inspection + کل مجموعه) + next build + docs gate

## 2026-10-08 (۳) — بازبینیِ عمیقِ production پس از تنظیماتِ مالک، و رفعِ خطای «scopes that cannot be requested together»

- **[OWNER]** مالک گفت همهٔ کارهای خواسته‌شده (origin در Google Cloud Console، `ADMIN_EMAILS` روی Render) را انجام داده؛
  بازبینیِ عمیق خواست، و اسکرین‌شاتِ تازه: دکمهٔ «اتصال به گوگل درایو» ⇒ `Error 400: invalid_request` —
  «This request contains scopes that cannot be requested together: drive.file, youtube, youtube.force-ssl, youtube.upload».
- **[FINDING]** ریشه: GIS ِ `initCodeClient` به‌طورِ پیش‌فرض `include_granted_scopes` دارد و همهٔ scopeهایی را که این
  OAuth client قبلاً گرفته (این کلاینت در اپِ یوتیوبِ مالک هم استفاده شده) به درخواست اضافه می‌کند؛ گوگل `drive.file`
  را با `youtube.*` در یک درخواست نمی‌پذیرد. خطای origin دیگر نیست (ورودِ مالک با گوگل موفق بود).
- **[CHANGE]** `frontend/src/components/inspection/Panels.tsx`: `include_granted_scopes: false` — فقط `drive.file` خواسته می‌شود.
- **[VERIFY]** production (`47a83b8`): `/api/auth/config` ⇒ `auth_enforced: true`؛ `/api/inspection` بدونِ نشست ⇒ ۴۰۱؛
  متغیرها روی Render: `ADMIN_EMAILS`، `GOOGLE_CLIENT_ID/SECRET`، `SUPERVISOR_TOKEN` (و `GOOGLE_DRIVE_REFRESH_TOKEN` ِ خالی حذف شده).
  Chromium با نشستِ ناظر روی **هر ۱۳ صفحه**: هیچ ۴۰۱/۴۰۳/۵xx از بک‌اند و هیچ خطای صفحه — یعنی رهگیرِ توکن روی همهٔ
  فراخوانی‌ها کار می‌کند؛ بدونِ نشست فقط صفحهٔ ورود. workflow ِ GitHub با `X-External-Token` ⇒ ۲۰۰ (توکنِ غلط ⇒ ۴۰۱)؛
  وب‌هوکِ تلگرام ⇒ ۲۰۰؛ `inspection.py whoami/urgent/pull` ⇒ ناظر شناخته شد، صف خالی؛ `inventory.py --post` ⇒ ۱۶ صفحه؛
  `surface_scan.py` روی production ⇒ ۱۴ صفحه، ۲۳ نقشه، ۰ شکست. روتین‌ها فعال؛ اولین دورِ فوری ۱۲:۱۱ UTC.
- **[TODO]** پس از دیپلوی، مالک «اتصال به گوگل درایو» را دوباره بزند؛ اگر باز خطا بود، متنِ خطا را بفرستد.

> **امضا:** `claude-opus-5-5 (Claude Code)` · 2026-10-08 · بازبینیِ production با Chromium + curl + اسکریپت‌های ناظر
