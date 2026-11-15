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

## 2026-10-08 (۴) — «نظارت و سرکشی»: هر قالبی کامل خوانده می‌شود — صوت/ویدیو با رونویسیِ کامل، ZIP ِ بازگشتی، doc/xls/rtf/odf/epub/ایمیل

- **[OWNER]** خواستهٔ مالک برای همهٔ پروژه‌هایش (پس از آنکه در Lifemanager دید ناظر فایلِ پیوست را کامل نمی‌خواند):
  «هر نوع فرمتی باید خونده بشه توسط ناظر … و حتی کامل هم خونده بشه نه خلاصه و یا اوایل اون فایل» — صدا، ویدیو،
  زیپ، انواعِ عکس و متن؛ و «روتین‌ها را اشتباه نگیر، چیزی را حذف نکن، قابلیتی را خراب نکن».
- **[FINDING]** در `backend/app/services/inspection_files.py` ِ پیش از این تغییر:
  `.doc` و `.xls` ⇒ `unsupported`؛ ZIP ⇒ فقط **فهرستِ نام‌ها** (`truncated`)؛ صوت/ویدیو ⇒ `media` («بازش کن و
  گوش کن») که با یک بار گرفتنِ `/raw` بدهی‌اش صاف می‌شد — یعنی ناظر بی‌آنکه صدایی شنیده باشد می‌توانست جواب بدهد
  (ناظرِ خودکار اصلاً نمی‌تواند فایلِ صوتی را «گوش» کند)؛ هر پسوندِ ناشناخته (`.rtf`، `.odt`، `.epub`، `.eml`،
  `.msg`، `.conf`…) ⇒ `unsupported`. CLI ِ ناظر HEIC/TIFF/BMP/AVIF را بی‌تبدیل می‌گذاشت (ابزارِ Read نشانشان
  نمی‌دهد)، زیپ را باز نمی‌کرد، و پاک‌سازیِ `files/` با `unlink` روی زیرپوشه می‌شکست.
- **[FINDING]** روتین‌ها (`trig_01SmGK1H3EyJoWpeSBVcqj8F` فوری، `trig_0185k7gpGZBvVs9JY9pZHiHJ` کامل) فقط به
  `docs/supervisor/URGENT_PROMPT.md` / `PROMPT.md` اشاره می‌کنند ⇒ پرامپتِ اصلی همین فایل‌هاست؛ پیامِ روتین‌ها عوض نشد.
- **[CHANGE]** `services/inspection_formats.py` (تازه): خوانندهٔ کامل برای `.doc` (جدولِ قطعه‌های OLE)، `.xls` (همهٔ
  کاربرگ‌ها)، RTF، ODT/ODS/ODP، EPUB به ترتیبِ spine، `.eml`/`.msg` با **همهٔ پیوست‌ها**، ZIP ِ **بازگشتی** (هر عضو
  از همان `extract()` ِ پروژه رد می‌شود)، SVG، و «هر بایتی که متن است، با هر پسوندی». `extract()` فقط در همان
  نقطه‌هایی که «unsupported»/فهرستِ نام می‌داد به آن وصل شد؛ خواننده‌های موجود (PDF، docx، xlsx، pptx) دست نخوردند.
- **[CHANGE]** صوت/ویدیو (و ZIP ِ دارای آن‌ها) ⇒ وضعیتِ تازهٔ **`pending`** (به‌جای `media`). `services/inspection_media.py`
  (تازه): رونویسیِ **کلمه‌به‌کلمه با برچسبِ زمان** با Gemini (`GEMINI_API_KEY` که روی Render هست؛ ویدیو: + شرحِ هر
  صحنه و نوشته‌های روی تصویر)؛ بالای ۱۵MB از Files API؛ ادامه تا نشانگرِ `<<END>>` (حداکثر ۴۰ دور، رسیدن به سقف ⇒
  `truncated` اعلام می‌شود). بی‌کلید/بی‌مدل ⇒ `failed` **با دلیل** (صف گیر نمی‌کند، ناظر ادعای شنیدن نمی‌کند).
- **[CHANGE]** `models/inspection.py`: `pending` بدهیِ خواندن است و با `/raw` صاف **نمی‌شود**؛ برچسبِ `media` برای
  ردیف‌های قدیمی ماند (حذف نشد).
- **[CHANGE]** `POST /api/inspection/files/{id}/extract` (تازه): بایت‌ها را از دیسکِ موقت/درایو می‌گیرد، با خواننده‌های
  امروز دوباره استخراج و رونویسی می‌کند؛ اگر متن عوض شد، متن را همان‌جا که زندگی می‌کند می‌گذارد
  (`inspection_files.replace_text`: روی دیسکِ موقت، یا فایلِ `.متن.txt` ِ تازه در پوشهٔ همان گزارش در درایو و انتقالِ
  نسخهٔ قبلی به «سطلِ حذف‌شده» — قرنطینه، نه حذف)، کشِ متن را خالی و شمارندهٔ خواندن را صفر می‌کند.
- **[CHANGE]** CLI: `ensure_extracted` در `pull` و `urgent` (برای `pending` و `media` ِ قدیمی) پیش از نوشتنِ کارتابل؛
  `scripts/supervisor/inspection_view.py` (تازه): تصویرها ⇒ PNG (HEIC/TIFF ِ چندصفحه/BMP/AVIF/ICO)، SVG با playwright،
  فریمِ ویدیو هر ۵ ثانیه (imageio-ffmpeg)، زیپ باز روی دیسک، و یادآوریِ دیدنِ همهٔ صفحه‌های PDF؛ پاک‌سازی با
  `shutil.rmtree`؛ `client.raw(..., timeout=)`. `scripts/supervisor/requirements.txt` (تازه).
  `backend/requirements.txt`: `olefile`، `xlrd`، `striprtf`.
- **[CHANGE]** دستورها: `PROMPT.md` v2→**v3** و `URGENT_PROMPT.md` v2→**v3** (بخش‌های «هر قالبی، کامل» و «پیوستی که کد
  است — بخوان، بفهم، خودت بنویس؛ عیناً کپی نکن»؛ معرفیِ `pending`)؛ نسخه‌های قبلی در `archive/`.
- **[TEST]** `backend/tests/test_inspection_formats.py` (doc و msg ِ واقعی از دادهٔ آزمونِ Apache POI در
  `tests/fixtures/inspection_formats/`، xls، rtf، odt، epub، eml با پیوست، zip ِ تو در تو، پسوندِ ناشناخته، `pending`،
  ادامهٔ رونویسی تا `<<END>>` از Files API، بی‌کلید)؛ در `test_inspection.py`: بدهیِ `pending` که با `/raw` صاف نمی‌شود
  و اندپوینتِ extract تا پاسخِ پذیرفته‌شده. تستِ قدیمیِ `"abc"` ِ `.bin` به‌روز شد (بایتِ دودوییِ واقعی هنوز
  `unsupported` است؛ `abc` حالا متن خوانده می‌شود).
- **[FINDING→CHANGE]** `.rtf` در `_TEXTY_EXT` بود ⇒ «متنِ ساده» با **نشانه‌گذاریِ خامِ RTF** (`{\rtf1 \u1587?…`) برمی‌گشت؛
  حالا پیش از شاخهٔ متن به خوانندهٔ RTF می‌رود و کلمه‌ها خوانده می‌شوند (تستِ `test_rtf_with_unicode_escapes`).
- **[EXPERIENCE]** `experiences/review-reads-every-format-in-full.md`.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-08 · pytest (کل مجموعه) + next build + docs gate

## 2026-10-09 — ناظرِ خودکار: ثبات‌بخشی به یک تستِ وابسته به دیتابیسِ محلی

- **[FINDING]** `test_get_available_models_excludes_cloud_code_when_disabled_in_db` روی کانتینرِ تازه با `no such table: model_settings` می‌شکست.
- **[CHANGE]** `backend/tests/test_creator_engine_projects_and_cloud_code.py`: `init_db()` پیش از استفاده از `SessionLocal`. کدِ محصول دست نخورد.
- **[VERIFY]** `pytest` کل: ۷۱۹ قبول / ۴ skip؛ `npm run build` سبز؛ درایو در production وصل است.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-09 · pytest + next build

## 2026-10-13 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی (۰ برگه/۰ فایل/۰ فوری)؛ pytest ۷۱۹ قبول/۴ skip؛ `npm run build` سبز؛ درایو در production وصل با ۰ فایلِ منتظر.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`، `OPEN_ITEMS.md` (بستنِ #۱). کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py`/`inventory.py` این دور اجرا نشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-13 · pytest + next build + queue/storage در production

## 2026-10-13 — صفِ فوری PM-INS-0001: چیپِ ناظرِ دوره‌ای + کادرها فقط با «ثبتِ گزارش: روشن»

- **[OWNER]** ۱) کنارِ «دورِ فوریِ بعدی» زمانِ دورِ ناظرِ دوره‌ای هم نشان داده شود (اگر زمان‌بندی دارد؛ وگرنه هیچ). ۲) کادرِ رنگیِ گزارش بعد از ثبت روی همان صفحه دیده نمی‌شد و باید به‌رنگِ وضعیتش دیده شود؛ ۳) با خاموش‌بودنِ «ثبتِ گزارش» هیچ کادری در هیچ وضعیتی نمایش داده نشود (کار انجام می‌شود، فقط نمایش نه) و با روشن‌شدن همه برگردند.
- **[FINDING]** مقایسهٔ زبانه `b.g.tab !== tabNow` سخت‌گیرانه بود: برچسبِ زبانه شاملِ شمارنده/نشان است و بعد از ثبتِ برگه عوض می‌شد ⇒ کادر کنار می‌رفت.
- **[CHANGE]** `frontend/src/lib/inspection/highlights.tsx`: `sameTab` (بی‌اعتنا به رقم و فاصله)، `readCaptureActive`/`notifyCaptureChanged`/`CAPTURE_ACTIVE_KEY`؛ کادرها فقط وقتی کلیدِ «ثبتِ گزارش» روشن است رسم می‌شوند (داده و کارِ ناظر دست‌نخورده). `provider.tsx`: تغییرِ کلید رویداد می‌فرستد. `Board.tsx`: `FullRoundChip` از `/schedule` (`full.next_at`)، فقط اگر مقدار داشته باشد.
- **[VERIFY]** `npm run build` سبز؛ pytest در `ship.sh`. عکسِ «بعد» گرفته نشد (دیپلوی نشده).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-13 · next build + pytest

## 2026-10-16 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی؛ pytest ۷۱۹ قبول/۴ skip؛ `npm run build` سبز؛ production healthy.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`، و تازه‌سازیِ `INVENTORY.md`/`inventory.json`. کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py` این دور اجرا نشد (playwright نصب نبود).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-16 · pytest + next build + inventory

## 2026-10-20 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی؛ pytest ۷۱۹ قبول/۴ skip (پس از بازنصبِ Pillow در کانتینر)؛ `npm run build` سبز؛ production healthy.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`. کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py` این دور اجرا نشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-20 · pytest + next build

## 2026-10-27 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی؛ pytest ۷۱۹ قبول/۴ skip؛ `npm run build` سبز؛ production healthy.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`، تازه‌سازیِ `INVENTORY.md`/`inventory.json`. کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py` این دور اجرا نشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-27 · pytest + next build

## 2026-10-30 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی؛ pytest ۷۱۹ قبول/۴ skip؛ `npm run build` سبز؛ production healthy.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`. کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py` این دور اجرا نشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-10-30 · pytest + next build

## 2026-11-03 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی؛ pytest ۷۱۹ قبول/۴ skip؛ `npm run build` سبز؛ production healthy.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`. کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py` این دور اجرا نشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-03 · pytest + next build

## 2026-11-06 — ناظرِ خودکار: دورِ سبک، بدونِ برگه

- **[VERIFY]** کارتابل خالی؛ pytest ۷۱۹ قبول/۴ skip؛ `npm run build` سبز؛ production healthy.
- **[CHANGE]** فقط ثبت: `RUNLOG.md`، `runs.jsonl`، تازه‌سازیِ `INVENTORY.md`/`inventory.json`. کدِ محصول دست نخورد.
- **[TODO]** `surface_scan.py` این دور اجرا نشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-06 · pytest + next build

### 2026-11-10 — اجرای ۹ ناظر (فقط ثبت)
- **VERIFY:** pytest ۷۱۹ سبز، build سبز، production healthy، کارتابل خالی. کدِ محصول دست نخورد.
- **CHANGE:** افزودنِ ورودی به `docs/supervisor/RUNLOG.md` و `runs.jsonl`.
— ناظرِ خودکار (Claude)

### 2026-11-13 — اجرای ۱۰ ناظر (فقط ثبت)
- **VERIFY:** pytest ۷۱۹ سبز، build سبز، production healthy، کارتابل خالی، inventory بدونِ کاهش. کدِ محصول دست نخورد.
- **CHANGE:** افزودنِ ورودی به `docs/supervisor/RUNLOG.md` و `runs.jsonl`؛ بازتولیدِ `INVENTORY.md`/`inventory.json`.
— ناظرِ خودکار (Claude)

## 2026-11-15 (۱) — طرحِ ۱۲ بندیِ مالک؛ بند ۱: «مرکز نظارت» ⇐ «اتاق فرمان»

- **[OWNER]** مالک طرحی ۱۲ بندی داد که بند به بند و با راستی‌آزمایی انجام شود: (۱) تغییرِ نامِ «مرکز نظارت» چون با
  «نظارت و سرکشی» هم‌نام است؛ (۲) صفحهٔ «مناظره» به چتِ سیارِ آگاه از همهٔ پروژه تبدیل شود؛ (۳) «پروژه‌ها» و «نمودارها»
  بی‌هیچ کاهشِ قابلیت در یک صفحه ادغام و در منو بلافاصله پس از «خانه» بیاید؛ (۴) سیم‌کشیِ «آرشیو» پس از این تغییرات
  درست شود؛ (۶) «مدل‌ها» و «تنظیمات» ادغام و همهٔ زیربخش‌ها راستی‌آزمایی/اصلاح شوند؛ (۷) ربات تلگرام نباید آسیب ببیند؛
  (۸) بررسیِ کاملِ «مرکز نظارت» از روی مستندات و کد، نه حدس؛ (۹) خانه مرتب و خودکار هم‌گام با صفحه‌ها؛ (۱۰) دایرهٔ
  راهنما همیشه خودکار به‌روز؛ (۱۱) صفحهٔ «جزوه و دفتر کار» به الگوی Detective-1 (فقط الگوبرداری، بدونِ تغییر در آن ریپو)؛
  (۱۲) تبِ «بازرس ویژه» (چت، ضبطِ آزاد/داخلِ پروژه، اسکرینِ کنارِ چت، و کنترلِ مرورگر مثلِ افزونهٔ Claude) اصلاح و تقویت شود.
- **[FINDING]** دکمه‌های تلگرام به `/oversight?tab=…` لینک می‌دهند (`notification_service.py`) ⇒ نشانیِ صفحه نباید عوض شود.
- **[DECISION]** نامِ تازه «اتاق فرمان» (پروژه‌ها) — کارِ این صفحه پایش، اسکن، تسک‌سازی، اجرا و تأییدِ مخازن است؛ «نظارت و
  سرکشی» همان برگه‌های مالک می‌ماند. نشانیِ `/oversight` ثابت ماند.
- **[CHANGE]** جایگزینیِ «مرکز نظارت» ⇐ «اتاق فرمان» در همهٔ متن‌های فرانت (منو، خانه، سرِ صفحه، بازرس ویژه) و پیام‌های
  تلگرامِ بک‌اند. داده‌های تست دست نخورد.
- **[VERIFY]** `grep` صفر موردِ باقی‌مانده در `frontend/src` و `backend/app`؛ pytest و build در ship.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · grep + pytest + next build (ship.sh)

## 2026-11-15 (۲) — بند ۲: «مناظره» ⇐ «دستیار» ِ سیار در همهٔ صفحه‌ها

- **[OWNER]** صفحهٔ مناظره با محتوای فعلیِ پروژه هم‌راستا نیست؛ یا حذف شود یا به چتِ سیاری در همهٔ صفحه‌ها تبدیل شود
  که برای هر کاری کمک کند، به همه چیز اشراف داشته باشد و با هر پیشرفت/اصلاحِ کوچک خودکار آگاه شود.
- **[DECISION]** حذف نه (قاعدهٔ «هیچ قابلیتی حذف نمی‌شود»): `/debate` و `/api/debate/*` دست‌نخورده می‌مانند (قرنطینه، بیرون
  از منو، با نوارِ «بایگانی» و پیوند از آرشیو). ایدهٔ مناظره داخلِ چت ماند: گزینهٔ «چند مدل» تا ۴ مدل را هم‌زمان می‌پرسد.
- **[DECISION]** اشرافِ همیشگی بدونِ هیچ متنِ ثابت: هر پرسش بافتِ زنده می‌سازد — نقشهٔ صفحه‌ها و راهنمای صفحهٔ جاری
  (از فرانت)، ۶ ورودیِ آخرِ WORKLOG + ورودی‌های مرتبط با پرسش، ۱۵ کامیتِ آخرِ `main` (مستقیم از GitHub)، و شمارشِ
  زندهٔ «اتاق فرمان» و «نظارت و سرکشی».
- **[FINDING]** ایمیجِ بک‌اند روی Render فقط از `./backend` ساخته می‌شود (`dockerContext: ./backend`) ⇒ `docs/` در کانتینر
  نیست. راه: `services/repo_docs.py` فایل‌ها را از GitHub (`main`، کشِ ۹۰ث، با بازگشت به نسخهٔ محلی/آخرین نسخه) می‌خواند.
- **[CHANGE]** بک‌اند: `services/assistant.py`، `services/repo_docs.py`، `api/routes/assistant.py` (`/api/assistant/{models,ask,conversations}`؛
  پشتِ دیوارِ ورود)، ثبت در `main.py`. گفت‌وگوها در `storage/assistant/*.json` (حذف = انتقال به `deleted/`).
  فرانت: `lib/siteMap.ts` (رجیستریِ واحدِ صفحه‌ها؛ منوی `Layout.tsx` از آن ساخته می‌شود و «مناظره» از منو بیرون رفت)،
  `components/AssistantChat.tsx` (دایرهٔ سبز، پایینِ چپ بالای دایرهٔ راهنما)، نوارِ بایگانی روی `/debate`.
  دروازهٔ مستندات: هر `page.tsx` باید در `siteMap.ts` ثبت باشد.
- **[VERIFY]** `tests/test_assistant.py` (۶ تست: خواندن/شکستنِ WORKLOG، ذخیره و ادامهٔ گفت‌وگو، چند مدل، بایگانی بی‌حذف،
  پیامِ خالی، ثبتِ مسیر پشتِ دیوار)؛ اجرای محلیِ بک‌اند+فرانت و Playwright: پنل باز شد، پیامِ «مدلی فعال نیست» درست آمد؛
  `build_context` واقعی از GitHub خواند (`WORKLOG (github, 16 ورودی)`, `GitHub commits (15)`).
- **[TODO]** بند ۴: تبِ «گفت‌وگوهای دستیار» در آرشیو (`/archive?tab=assistant`).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build + Playwright محلی

## 2026-11-15 (۳) — بند ۳: «پروژه‌ها» + «نمودارها» ⇐ یک صفحه، بلافاصله پس از «خانه»

- **[OWNER]** دو صفحهٔ `/projects` و `/diagrams` هم‌راستا هستند؛ زیرِ یک صفحه ادغام شوند بی‌هیچ آسیب یا کاهشِ قابلیت (حتی
  کوچک‌ترین) و بی‌به‌هم‌خوردنِ سیم‌کشی؛ در منو گزینهٔ بعد از «خانه» باشد.
- **[DECISION]** کدِ دو صفحه **بی‌تغییر** (فقط نامِ تابعِ export) با `git mv` به `components/views/ProjectsView.tsx` و
  `components/views/DiagramsView.tsx` رفت؛ صفحهٔ تازهٔ `/projects` فقط بینِ آن دو تب می‌زند (`?view=diagrams`). هر نما بارِ
  اولِ باز شدن mount و سپس پنهان نگه داشته می‌شود تا تعویضِ تب کارِ نیمه‌تمام (نمودارِ در حالِ ساخت، import ِ باز) را از
  دست ندهد. `/projects?id=…` همچنان کار می‌کند؛ `/diagrams` به `/projects?view=diagrams` هدایت می‌شود (پیوندهای قدیمی سالم).
  `/projects/[id]` (صفحهٔ هر پروژه و «بازرس ویژه») دست نخورد.
- **[CHANGE]** `app/projects/page.tsx` (تب‌ها)، `app/diagrams/page.tsx` (هدایت)، `lib/siteMap.ts` (منو: «پروژه‌ها و نمودارها»
  دومین گزینه؛ «نمودارها» بیرون از منو با `movedTo`)، `scripts/supervisor/inventory.py` (منو را از `siteMap.ts` می‌خواند).
- **[FINDING]** سیاههٔ ناظر: دکمه‌های صفحه‌ها ۴۶۷⇐۴۳۹ و دکمه‌های کامپوننت‌ها ۱۳۲⇐۱۶۵ — **جابه‌جایی است نه کاهش** (جمع ۵۹۹⇐۶۰۴).
  منو ۱۱⇐۹ آگاهانه است: «مناظره» (بند ۲، قرنطینه) و «نمودارها» (اکنون تب). ناظرِ خودکار این را کاهش نشمارد.
- **[VERIFY]** build سبز؛ Playwright محلی: `/projects` دو تب، تبِ نمودارها کامل (رسمِ خودکار، نمونه‌ها، پیش‌نمایشِ Mermaid)،
  `/diagrams` ⇐ `/projects?view=diagrams`، بی‌خطای کنسول.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · next build + Playwright محلی + inventory

## 2026-11-15 (۴) — بند ۴: سیم‌کشیِ «آرشیو» پس از بندهای ۱ تا ۳

- **[OWNER]** آرشیو پس از تغییرات درست سیم‌کشی شود؛ «مناظرات» که کنار می‌رود، چیزِ دیگری جایش را بگیرد و خودش جایی در پروژه پیدا کند.
- **[FINDING]** همهٔ مسیرهای آرشیو بررسی شد: `/api/debate/`، `/api/debate/{id}`، `/api/upload/files`، `GET|DELETE /api/upload/file/{id}`،
  `/api/simple/projects`، `DELETE /api/simple/projects/{id}` — همه در بک‌اند هستند. **ایراد:** پیوندِ «دانلود» ِ فایل‌ها `<a href>` ِ
  خام بود و پشتِ دیوارِ ورود (بدونِ هدرِ Authorization) 401 می‌گرفت.
- **[CHANGE]** `app/archive/page.tsx`: تبِ نخست «گفت‌وگوهای دستیار» (فهرست، جست‌وجو/مرتب‌سازی، نمایشِ کامل، «ادامه در دستیار»،
  بایگانی بی‌حذف)، «مناظره‌های قدیمی» تبِ آخر با همهٔ امکاناتِ قبلی (جزئیات، خروجیِ JSON، پیوند به `/debate` ِ بایگانی‌شده)؛
  `?tab=` (assistant|files|projects|debates)؛ کارتِ آمارِ چهارم؛ دانلود با `withToken()`.
  `AssistantChat.tsx`: رویدادِ `assistant:load` گفت‌وگوی ذخیره‌شده را در چت باز می‌کند (کامیتِ `cab12af`).
- **[CORRECTION]** کامیتِ `cab12af` بدونِ این ورودی و بدونِ خطِ `.gitignore` ارسال شد (یک `sed` شکست خورد و زنجیره قطع شد)؛
  این ورودی و `backend/storage/assistant/` در `.gitignore` در کامیتِ بعدی اضافه شد. هیچ دادهٔ گفت‌وگویی کامیت نشده بود.
- **[VERIFY]** build سبز؛ Playwright محلی با یک گفت‌وگوی نمونه: فهرست، مودالِ گفت‌وگو و «ادامه در دستیار» (چت با همان پیام‌ها باز شد).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · next build + Playwright محلی

## 2026-11-15 (۵) — بند ۶: «مدل‌ها» + «تنظیمات» ⇐ «مدل‌ها و تنظیمات»، با بررسیِ تک‌تکِ زیربخش‌ها

- **[OWNER]** دو صفحهٔ `/models` و `/settings` ادغام شوند بی‌آنکه چیزی کم شود، و همهٔ زیرقسمت‌ها و جزئیاتشان از نظرِ عملکرد و
  صحت بررسی و اصلاح شوند. (بند ۵ در فهرستِ مالک نبود؛ شماره‌ها همان شماره‌های مالک است.)
- **[DECISION]** همان الگوی بند ۳ و یک کامپوننتِ مشترک: `components/ViewHub.tsx` (نما بارِ اول mount و سپس پنهان نگه داشته می‌شود؛
  `?view=`). کدِ دو صفحه بی‌تغییر با `git mv` به `components/views/{SettingsView,ModelsView}.tsx` رفت. `/settings` پیش‌فرض
  «کلیدها و تنظیمات» است تا همهٔ پیوندهای «به تنظیمات بروید» (موتور خالق، اتاق فرمان، بازرس ویژه، …) هنوز به کلیدها برسند؛
  `/models` ⇐ `/settings?view=models`. `/projects/page.tsx` هم به `ViewHub` منتقل شد (رفتار همان).
- **[CHANGE]** `SettingsView`: `?tab=api|deploy|config|limits|logs|notifications|usage` تبِ درونی را باز می‌کند.
- **[FINDING]** ابزارِ تازهٔ `scripts/check_frontend_api.py` (مسیر + متد هر فراخوانی را با OpenAPI ِ بک‌اند تطبیق می‌دهد): ۶۴ فراخوانیِ
  دو صفحه و کامپوننت‌هایشان (`RenderLogsPanel`، `NotificationSettingsPanel`، `AIUsagePanel`، `ExtractionDefaultPicker`،
  `services/api.ts`) مسیر دارند. **دو ایرادِ واقعی در تبِ «پیکربندی»:** ذخیره `PUT /api/config` می‌فرستاد که وجود ندارد (405 —
  ذخیره همیشه شکست می‌خورد)، و بارگذاری کلیدهای تختی (`data.max_tokens`) را می‌خواند که API هرگز نمی‌دهد (همیشه پیش‌فرض نشان می‌داد).
- **[CHANGE]** بارگذاری از `config.processing` و ذخیره با `PUT /api/config/processing` (`max_tokens_per_model`، `request_timeout`،
  `retry_count`، و فیلدِ تازهٔ `default_temperature` در `ProcessingConfig`/`ProcessingConfigUpdate`). یادداشتِ صادقانه روی تب:
  بیشترِ سرویس‌های AI هنوز مقدارِ خودشان را می‌فرستند (`grep`: هیچ مصرف‌کننده‌ای از `max_tokens_per_model`/`retry_count` نمی‌خواند).
- **[VERIFY]** `tests/test_config_processing_roundtrip.py` (ذخیره و بازخوانی؛ و اینکه `PUT /api/config` واقعاً 405 است)؛ build سبز؛
  Playwright محلی روی هر ۷ تبِ تنظیمات + دو حالتِ مدل‌ها: صفر خطای کنسول و صفر پاسخِ ≥400 جز `POST /api/render/services/refresh`
  (400 = کلیدِ Render محلی تنظیم نیست؛ رفتارِ درست)؛ «ذخیرهٔ تنظیمات» ⇐ «تنظیمات ذخیره شدند» و مقادیر برگشتند؛ toggle/ویرایش/
  batch ِ مدل‌ها با curl رفت‌وبرگشت شد؛ `/models` ⇐ `/settings?view=models`.
- **[TODO]** ۱۲ فراخوانیِ بی‌مسیر در `oversight/page.tsx` و `projects/[id]/page.tsx` (فهرستِ `check_frontend_api.py`) — در بندهای ۸ و ۱۲ بررسی می‌شوند.
- **[TODO]** مصرفِ واقعیِ پیش‌فرض‌های «پیکربندی» در `ai_manager` تصمیمِ جداست (رفتارِ همهٔ مدل‌ها را عوض می‌کند).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build + check_frontend_api + Playwright محلی

## 2026-11-15 (۶) — بند ۷: ربات تلگرام و فرانت هم‌گام — یک شکستگیِ قدیمی رفع و قفلِ تستی

- **[OWNER]** سیم‌کشیِ پروژه به قابلیت‌های ربات تلگرام نباید به هم بخورد؛ تغییراتِ بالا و بعدی ابداً نباید به ربات آسیب بزنند و
  باید هم‌گام پیش بروند.
- **[FINDING]** ربات فقط از بک‌اند کار می‌کند (`/api/notifications/telegram/*`، `notification_service.py`) و بندهای ۱ تا ۶ هیچ مسیرِ API
  را عوض نکردند. پیوندهای ربات به فرانت: `/`، `/oversight`، `/oversight?tab=tasks|reports|ideas|watched|repos` (و `&watched=<id>`)،
  `/settings`، `/settings?tab=usage` — همه هنوز صفحه دارند (`/oversight` در بند ۱ عمداً ثابت ماند).
- **[FINDING]** **شکستگیِ قدیمی:** «اتاق فرمان» `?tab=` را از نشانی نمی‌خواند ⇒ همهٔ دکمه‌های «📋 تسک‌ها»، «📊 گزارش‌ها»، «💡 ایده‌ها»
  … روی تبِ پیش‌فرض باز می‌شدند؛ `/settings?tab=usage` هم تا بند ۶ نادیده گرفته می‌شد. متن‌های «مرکز نظارت» ⇐ «اتاق فرمان» در
  پیام‌های ربات فقط نمایشی‌اند (دکمه‌ها URL هستند، هیچ تطبیقِ متنی روی آن‌ها نیست).
- **[CHANGE]** `oversight/page.tsx`: یک بار در بارگذاری `tab` و `watched` را از نشانی می‌خواند.
- **[CHANGE]** تستِ نگهبانِ تازه `tests/test_telegram_frontend_links.py`: هر پیوندِ `{base}/…` در بک‌اند باید به صفحه‌ای واقعی در
  `frontend/src/app` برسد و هر `?tab=` باید در فهرستِ تب‌هایی باشد که آن صفحه از نشانی می‌پذیرد؛ وبهوکِ تلگرام باید عمومی بماند.
  ⇐ هر تغییرِ آیندهٔ صفحه/تب که ربات را بشکند، ارسال را متوقف می‌کند.
- **[VERIFY]** تست ۴/۴ (۳۸ پیوند یافت شد)؛ Playwright محلی: هر شش پیوندِ نمونهٔ ربات روی تبِ درست باز شد.
- **[TODO]** بررسیِ زندهٔ ربات روی production (getWebhookInfo) از این سشن ممکن نبود — کلیدِ بک‌اندِ این پروژه در اختیارِ سشن نیست؛
  ناظرِ خودکار یا مالک می‌تواند از تبِ «نوتیفیکیشن» دکمهٔ «تست Telegram» را بزند.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build + Playwright محلی

## 2026-11-15 (۷) — بند ۸: بررسیِ کاملِ «اتاق فرمان» از روی کد، مستندات و تاریخچه — ۱۸ ایرادِ تأییدشده رفع شد

- **[OWNER]** «مرکز نظارت» (اکنون «اتاق فرمان») کاملاً بررسی شود؛ همهٔ مستندات خوانده شود تا دقیق — نه از حدس — فهمیده شود چه
  می‌کرد و چه می‌کند؛ ایده‌های مالک مدت‌ها رسیدگی نشده و خطاهایش باید گرفته شود.
- **[FINDING]** کلون کم‌عمق بود (۹۵ کامیت)؛ با `git fetch --unshallow` همهٔ ۴٬۴۹۴ کامیت آمد. این بخش ۳۸۵ کامیت دارد: ساخت از ۹ مه تا ۲۸ ژوئن ۲۰۲۶،
  سپس ۴٫۵ ماه بی‌تغییر. README/ARCHITECTURE/ROADMAP آن را نمی‌شناسند — مستندِ واقعی docstring ها، برچسب‌های ایده در کد و متنِ کامیت‌هاست.
- **[DECISION]** پنج بازبینِ فقط‌خواندنیِ موازی (صفحه، هستهٔ سرویس، اسکنِ عمیق، اجرا/تأیید، مستندات+تاریخچه)؛ هر ایرادِ گزارش‌شده پیش از رفع
  **خودم در کد تأیید کردم**؛ فقط ایرادهای روشن و کم‌خطر رفع شد؛ هر چه رفتار یا هزینه را عوض می‌کند به تصمیمِ مالک سپرده شد.
- **[CHANGE]** سندِ کامل: `docs/handbook/OVERSIGHT.md` (هدف، تاریخچهٔ فاز به فاز با SHA، نقشهٔ صفحه، جریان‌ها، اسکن، اجرا، تأیید، زمان‌بند،
  ذخیره‌سازی، وابستگی‌های ربات، ۱۸ رفع، ۱۳ ایرادِ باز).
- **[CHANGE]** بک‌اند: `routes/oversight.py` (۱۸ فیلدِ جاافتادهٔ `WatchedUpdate` + پاک‌کردنِ نشانی‌ها با null؛ ذخیرهٔ واقعیِ `verify-v6-config`)،
  `oversight_service.py` (قفلِ تک‌نوبتِ زمان‌بند، عقب‌نشینیِ ۱ساعته پس از اسکنِ ناموفق، نادیده‌گرفتنِ آرشیوشده‌ها، بازیابیِ `running` ⇐ `failed`
  در بارگذاری، ۲ تنظیمِ runner، `runtime_auth_recipe`، کلیدِ ماشینیِ خودفراخوانی، علامت‌گذاریِ اسکن‌های قطع‌شده)، `oversight_deep_scan_service.py`
  (صفرکردنِ stop/pause، پیامِ شروع پس از توکن، `passes_total` ِ واقعی، `mark_interrupted_scans`)، `external_prompts.py` (نگهبانِ بی‌پیشرفت با
  `run_at` و بی‌گزارشِ جاری؛ آزادسازیِ قفلِ verify در خطا)، `removesuffix` در `inspector_scan_bridge.py`، `inspector_proposal_executor.py`،
  `scan_v5/comprehensive_inventory.py`.
- **[CHANGE]** فرانت: `oversight/page.tsx` (ref ِ پرامپتِ ادامه و تابعِ verify ِ auto-loop، بنرِ سقفِ دور، تازه‌سازیِ زنده، `found:false`، پایانِ
  polling روی stopped/interrupted، ادغامِ ترجیحاتِ نما، وابستگیِ کانبان، خطای تاریخچهٔ verify)، `projects/[id]/page.tsx` (مسیرِ درستِ scan).
- **[FINDING]** سه موردِ «بی‌مسیر» ِ `check_frontend_api.py` در `oversight/page.tsx` مثبتِ کاذب بودند (عبارتِ `${…}` در نشانی). پنج موردِ
  `projects/[id]/page.tsx` واقعاً بی‌مسیرند (`/api/creator/projects/{id}/generate`، `/api/projects/{id}/deploy/render`، `/files`، `/files/{path}`،
  `/health/validate`) — در بند ۱۲ (همان صفحه) رفع می‌شوند.
- **[VERIFY]** pytest ۷۳۸ سبز (۸ تستِ تازه: `test_oversight_watched_update_schema.py`، `test_oversight_audit_fixes_2026_11_15.py`)؛ build سبز؛
  محلی: PATCH ِ سه تنظیم و بازخوانی؛ در مرورگر کلیکِ «logic audit» ⇐ ری‌لود ⇐ ماندگار و روی سرور `True`؛ هر پنج تب بی‌خطای کنسول/شبکه.
- **[TODO]** ۱۳ ایرادِ بازِ `OVERSIGHT.md` §۱۲ نیازمندِ تصمیمِ مالک (به‌ویژه رشدِ دیسک، done ِ بی‌تأیید، آسان‌گیریِ verify، runner ِ دستی).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build + Playwright محلی + بازبینیِ پنج‌گانه با تأییدِ دستی

## 2026-11-15 (۸) — بندهای ۹ و ۱۰: خانهٔ خودکار و دایرهٔ راهنمای همیشه به‌روز

- **[OWNER]** (۹) صفحهٔ خانه مرتب شود و طوری باشد که هر تغییرِ بعدی در صفحه‌ها خودکار سینک شود. (۱۰) دایرهٔ راهنمای پایینِ هر صفحه
  به‌روز شود و طوری در پروژه ثبت شود که همیشه خودکار به‌روز بماند.
- **[FINDING]** خانه فهرستِ دستیِ ۹ کارت داشت (هنوز «مناظره»، «نمودارها» و «تنظیمات» ِ جدا) و عنوانِ «سیستم مناظره AI». راهنما فقط برای ۷ صفحه
  دادهٔ دستی داشت (`helpData.ts`)؛ روی «اتاق فرمان»، «نظارت و سرکشی»، «مرکز دانش»، «آرشیو» و … اصلاً دیده نمی‌شد؛ راهنمای «مدل‌ها» پس از ادغام دیگر باز نمی‌شد.
- **[DECISION]** هیچ فهرستِ دستیِ تازه: همه از رجیستریِ `lib/siteMap.ts` (که دروازهٔ مستندات صفحهٔ بی‌ثبت را رد می‌کند) + دادهٔ زنده.
- **[CHANGE]** خانه (`app/page.tsx`): نام و هدفِ برنامه از `APP_NAME`/`APP_TAGLINE` (منوی کناری، سرِ موبایل و عنوانِ مرورگر هم همین‌ها)؛ وضعیتِ زنده
  (مدل‌های فعال، مخازنِ اتاق فرمان و توکن‌ها، تسک‌های فعال، برگه‌های بازِ نظارت)؛ کارت‌ها گروه‌بندی‌شده از رجیستری با پیوندِ مستقیم به هر تب؛
  «تازه‌ها»: آخرین ورودی‌های دفتر کار با امضا و آخرین کامیت‌ها، زنده از GitHub؛ دکمهٔ «از دستیار بپرس».
- **[CHANGE]** راهنما: `resolvePageHelp` (نام و تب‌های فعلی از رجیستری؛ متنِ دستی هر جا هست حفظ؛ برای صفحهٔ بی‌متن، راهنمای خودکار؛ در صفحه‌های
  ادغامی راهنمای نمای باز — `/settings?view=models` ⇐ مدل‌ها)؛ دو تبِ زنده: «📍 این صفحه الان» (بخش‌ها، تب‌ها، دکمه‌ها و ورودی‌هایی که همین الان روی
  صفحه‌اند) و «🕒 تغییراتِ اخیر» (کامیت‌های فایل‌های همان صفحه از GitHub؛ `files` در رجیستری).
- **[CHANGE]** بک‌اند: `routes/handbook.py` — `GET /api/handbook/recent` و `GET /api/handbook/changes?files=` (زنده از GitHub با `repo_docs`؛ مسیرِ ناامن رد).
- **[VERIFY]** `tests/test_handbook_routes.py` (۲ تست) + تست‌های مرکز دانش به رجیستری منتقل شد؛ build سبز؛ Playwright محلی: خانه، راهنمای «اتاق فرمان»
  (۲ بخش، ۲۵ دکمه، ۲۶ ورودی خوانده شد؛ ۱۰+ کامیتِ واقعی)، «مدل‌ها» ِ ادغامی و «آرشیو»؛ بی‌خطای کنسول.
- **[TODO]** پیوندِ «دفتر کار ←» در خانه به `/handbook` است که در بند ۱۱ (بلافاصله بعد) ساخته می‌شود.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build + Playwright محلی

## 2026-11-15 (۹) — بند ۱۱: صفحهٔ «جزوه و دفتر کار» (الگوی Detective-1، زنده از GitHub)

- **[OWNER]** برای مستندسازیِ دقیق‌تر و بی‌تداخل با مستندسازیِ داخلِ گیت، چیزی مشابهِ Detective-1 (`/handbook?doc=HANDBOOK`) ساخته شود: صفحه‌ای
  به نامِ «جزوه و دفتر کار» که با GitHub متصل باشد و هم‌زمان سینک شود؛ همه‌چیز را دقیق ثبت کند — نه فقط کارِ سشن‌ها، بلکه کارهای جزئی و
  درشتِ مدل‌ها و سایرِ تغییرات؛ هر بخشی که در پروژهٔ نمونه هست اینجا هم بیاید و همان رفتارها را ثبت و سینک کند؛ فهرست‌بندی شود، جزوه شود،
  خروجی داشته باشد، فهرست‌ها مدام به‌روز شوند؛ ترتیبِ بعضی بر اساسِ تاریخ و بعضی بر اساسِ محتوا/عنوان؛ مطلبِ بی‌فهرست در جای مناسب فهرست بگیرد.
- **[FINDING]** Detective-1 (فقط خوانده شد): `docs/handbook/{HANDBOOK,PROGRESS}.md` + `docs/WORKLOG.md` از دیسکِ سرور خوانده می‌شوند (rootDir
  backend + buildFilter `docs/**`)؛ نمودارِ روند Mermaid ِ دستی است؛ قاعدهٔ «پس از هر کار HANDBOOK + PROGRESS». اینجا ایمیج فقط `./backend` است.
- **[DECISION]** همه زنده از GitHub (`repo_docs`)، پس سینکِ هم‌زمان بی‌دیپلوی؛ اسناد **کشف** می‌شوند (هر `.md` ِ تازه در `docs/handbook`،
  `docs/supervisor`، `experiences` خودش ظاهر می‌شود)؛ دو سندِ **خودکار** تا هیچ کاری گم نشود: «تاریخچهٔ تغییرات» (همهٔ کامیت‌های main از هر
  سشن/مدل/روتین/انسان، روزبه‌روز، همگام‌سازی‌های پرامپت جمع‌شده) و «فعالیتِ مدل‌ها» (فراخوانی‌های مدل از `ai_logs` روزبه‌روز×مدل، اجرا/تأییدهای
  اتاق فرمان، گفت‌وگوهای دستیار). نمودارِ روند برخلافِ Detective-1 دستی نیست — از جدولِ PROGRESS کشیده می‌شود (هرگز ناهم‌خوان نمی‌شود).
- **[CHANGE]** اسناد: `docs/handbook/HANDBOOK.md` (واژه‌نامه، نقشه، هر زیرسامانه، تصمیم‌های کلیدی، کارهای باز)، `docs/handbook/PROGRESS.md`
  (۱۸ رویداد از ۲۰۲۶-۰۱-۰۳، شمارِ کامیت‌ها از تاریخچهٔ کامل). بک‌اند `routes/handbook.py`: `/docs` (فهرستِ گروه‌بندی، `order` = date|content)،
  `/doc/{slug}`، `/search`، `/export` (یک فایلِ Markdown ِ همه یا انتخابی)؛ `repo_docs.commits_page` و `list_dir` (GitHub ∪ نسخهٔ محلی).
  فرانت `app/handbook/page.tsx`: فهرستِ گروه‌ها، فهرستِ هر سند با جست‌وجو (تاریخی‌ها «جدیدترین اول» با کلیدِ ⇅)، لنگرِ عنوان با قاعدهٔ GitHub،
  پیوندِ میانِ اسناد، Mermaid، نمودارِ PROGRESS، جست‌وجوی سراسری، خروجیِ این سند/همه، چاپ/PDF (منو و دکمه‌های شناور در چاپ پنهان). منو + خانه + راهنما
  از رجیستری (`/handbook`، با تب‌های `?doc=`).
- **[CHANGE]** قاعده‌ها: `AGENTS.md` و `CLAUDE.md` («جزوه همیشه زنده»)؛ `scripts/docs_gate.py` §۷: بخشِ HANDBOOK بی‌سطر در «فهرست»، لنگرِ ناموجود در
  پیوندهای جزوه، و PROGRESS ِ عقب‌تر از آخرین ورودیِ WORKLOG ⇒ ارسال رد می‌شود (آزمونِ جهشی: سه خطای ساختگی هر سه گرفته شد).
- **[VERIFY]** `tests/test_handbook_routes.py` (۴ تست)؛ pytest ۷۴۲ سبز؛ build سبز؛ Playwright محلی: جزوه، پیوند به «اتاق فرمان»، نمودارِ PROGRESS،
  فهرستِ WORKLOG جدیدترین‌اول، جست‌وجوی «تلگرام» ۲۸ نتیجه، لنگرِ عمیق §۱۲، تاریخچهٔ کامیت‌ها؛ صفر خطای کنسول.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build + docs gate (با آزمونِ جهشی) + Playwright محلی

## 2026-11-15 (۱۰) — بند ۱۲-الف: اسکرینِ کنارِ چتِ «بازرس ویژه» و ضبط — ریشه: دیوارِ ورود

- **[OWNER]** (بند ۱۲) «بازرس ویژه»: چتِ هوشمند با ضعیف‌ترین مدل‌ها بهترین خروجی را بدهد؛ بخشِ ضبطِ آزاد/داخلِ پروژه (لاگِ همه‌چیز، ویدیو، ارسال با
  پرامپت) ضعیف و خراب شده؛ اسکرینِ فرانتِ پروژه کنارِ چت خراب است و یک به‌روزرسانیِ قبلی بدترش کرد — با احتیاط درست شود و همیشه خودش را اصلاح کند؛
  سپس مثلِ افزونهٔ Claude بتواند فرم پر کند، در سایت‌ها کار کند و موس را در دست بگیرد، با همهٔ مدل‌ها، و همه‌چیز ثبت شود.
- **[DECISION]** چهار بازبینِ فقط‌خواندنی (چت، ضبط، اسکرین، طراحیِ عاملِ مرورگر)؛ اجرا در چهار گام: ۱۲-الف اسکرین و ضبط، ۱۲-ب چت برای مدل‌های ضعیف،
  ۱۲-ج عاملِ مرورگر، ۱۲-د پنج فراخوانیِ بی‌مسیرِ صفحهٔ پروژه.
- **[FINDING]** ریشهٔ مشترکِ «اسکرین خراب است» و «ضبط خراب است»: iframe ِ کنارِ چت `/api/render/inspector/proxy/{پروژه}/…` است (پروکسیِ بک‌اند از
  فرانتِ پروژه، از `193426b9` ۲۰۲۶-۰۲-۲۲). از دیوارِ ورود (`5f941b48`، ۲۰۲۶-۱۰-۰۸) هر بارِ صفحه و هر فایلِ آن 401 می‌گرفت (iframe هدرِ Authorization
  نمی‌فرستد) ⇒ اسکرین JSON ِ خطا نشان می‌داد، `onLoad` باز هم «بارگذاری شد» می‌گفت، عکسِ 📸 از صفحهٔ خطا گرفته می‌شد و ضبطِ «داخلِ پروژه» همان را ضبط
  می‌کرد و هیچ تعاملی نمی‌رسید. همین «به‌روزرسانیِ بدترکننده» است؛ کدِ ضبط از ۲۰۲۶-۰۶-۰۵ عملاً تغییر نکرده بود.
- **[DECISION]** «بلیتِ پیش‌نمایش» به‌جای گذاشتنِ توکنِ نشست در URL (که به جاوااسکریپتِ صفحهٔ هدف و لاگ‌ها نشت می‌کرد): HMAC با کلیدِ امضای نشست،
  بسته به **یک** پروژه، ۳۰ دقیقه، در کوکیِ `pm_preview` با `path` = پیشوندِ پروکسیِ همان پروژه؛ دیوار فقط GET/HEAD ِ همان مسیر را با بلیتِ معتبر
  می‌پذیرد (`core/auth.preview_allowed`). مسیرِ عمومیِ تازه‌ای به `PUBLIC` اضافه نشد (قاعدهٔ ۴: دلیل همین بند).
- **[CHANGE]** بک‌اند: `core/auth.py` (`preview_ticket`/`preview_ticket_ok`/`preview_allowed` + یک شرط در `AuthWall`)، `POST /api/auth/preview-ticket`
  (پشتِ دیوار)، `inspector_recording_processor.extract_keyframes_from_video` (ffmpeg، وقتی `frames/` خالی است — تحلیلِ تصویریِ حالتِ «داخلِ پروژه» و
  ویدیوهای بلندِ «آزاد» که قبلاً هرگز انجام نمی‌شد). فرانت: `lib/previewTicket.ts` (کوکی + تمدید در ⅔ عمر)، `projects/[id]/page.tsx` (بلیت پیش از
  iframe؛ **خودترمیمی**: `onLoad` محتوای واقعی را می‌بیند — خطای ورود ⇒ تمدیدِ بلیت و بارگذاریِ دوباره، خطای دیگر ⇒ حالتِ قرمز؛ پرامپتِ ضبط در کادرِ چت)،
  `InspectorRecordingPanel.tsx` (فاز در ref ⇒ توقفِ خودکار با Stop sharing/۶۰ دقیقه کار می‌کند؛ هر تکه ۳ بار تلاش و پیش از `/stop` منتظرِ پایانِ
  ضبط‌کننده‌ها و همهٔ آپلودها، نه ۱٫۵ ثانیهٔ ثابت؛ اگر `/stop` تایم‌اوت شد پیگیریِ نتیجه؛ خطا/هشدارِ ارسال نمایش داده می‌شود)، `InspectorBridge.tsx`
  (`navigate` فقط http(s) — سوکتِ پل احرازِ هویت ندارد).
- **[VERIFY]** `test_preview_ticket.py` (۳: بلیت بسته به پروژه/انقضا، فقط GET ِ همان پروکسی، و end-to-end با خودِ `AuthWall`: بی‌کوکی 401، با کوکی 200،
  پروژهٔ دیگر و API ِ دیگر 401)؛ `test_recording_keyframes.py` (۲، با webm ِ ساخته‌شده با ffmpeg)؛ ۳۱ تستِ ضبط سبز؛ pytest ۷۴۷؛ build سبز.
- **[TODO]** حالتِ C ِ پیشنهادی (اسکرینِ سمتِ سرور با Playwright برای سایت‌هایی که پروکسی برایشان کار نمی‌کند: chunk های پویای Next، POST ها)، بستنِ
  سوکتِ پل با بلیت، تبدیلِ ویدیو به MP4 برای تلگرام، بردنِ ضبط‌ها به گوگل درایو، ماندگاریِ جلسه‌های ضبط پس از ری‌استارت.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build (بی‌کلیدِ واقعی؛ دیوار با AuthWall ِ واقعی در تست)

## 2026-11-15 (۱۱) — بند ۱۲-ب: چتِ «بازرس ویژه» با مدل‌های ضعیف

- **[FINDING]** (بازبینیِ چت، تأییدشده در کد) مهم‌ترین علتِ ضعف: `read_file` هر فایل را در ۱۸٬۰۰۰ نویسه می‌بُرید (≈ ۴۰۰ خطِ اول؛ فایل‌های داغِ همین مخزن
  ~۱۸٬۰۰۰ خط‌اند) و راهی برای خواندنِ بقیه، جست‌وجو یا دیدنِ نقشهٔ فایل نبود؛ `submit_action_plan` هر `find` ی را می‌پذیرفت ⇒ مدل `find` را از کدی که
  ندیده بود حدس می‌زد و مرحلهٔ اعمال با تطبیقِ فازیِ ۸۵٪ گاهی بلوکِ اشتباه را جایگزین می‌کرد. مسیرِ تک‌مرحله‌ای هم یک ویرگولِ اضافه یا خطِ خامِ داخلِ رشته را
  با `json.loads` ِ سخت‌گیر رد و کلِ پلان را گم می‌کرد. موارد دیگرِ گزارش (پرامپتِ ~۳۳ هزار نویسه‌ای، تناقض‌های دستور، انتخابِ مدل بر اساسِ «پرکاربرد»، حافظهٔ
  بینِ نوبت‌ها، بازبینِ کم‌دید) در [TODO] زیر — رفتارِ کلی را عوض می‌کنند و گام‌به‌گام باید رفت.
- **[CHANGE]** `services/inspector_code_tools.py` (توابعِ خالص: بازهٔ شماره‌دار، نقشهٔ فایل برای Python/TS/Markdown، جست‌وجو، سنجشِ `find` و نزدیک‌ترین
  متنِ واقعی)؛ `inspector_agent.py`: `read_file` با `start_line`/`end_line`؛ فایلِ بزرگ ⇒ نقشهٔ کامل + ۲۲۰ خطِ اول + راهنما (نه برشِ بی‌صدا)؛ ابزارهای
  تازهٔ `search_code` و `file_outline`؛ `submit_action_plan` تا ۲ بار با فهرستِ find های ناموجود و نزدیک‌ترین متن برگردانده می‌شود (`INSPECTOR_VERIFY_FIND=0`
  خاموشش می‌کند). `render_logs.py`: `_lenient_json` برای همهٔ بلوک‌های ```json و حصارِ بی‌خطِ‌تازه.
- **[VERIFY]** `test_inspector_code_tools.py` (۶ تست، از جمله حلقهٔ واقعیِ عامل با یک «مدلِ ضعیفِ» برنامه‌ریزی‌شده: find ِ اشتباه رد ⇒ خواندنِ بازه ⇒ پلانِ درست
  پذیرفته؛ فایلِ ۳٬۰۰۸ خطی با نقشه برگشت)؛ pytest ۷۵۳ سبز.
- **[TODO]** (از بازبینی، به ترتیبِ کم‌خطر) نقشهٔ کاملِ مخزن با نماد برای انتخابِ فایل (نه فقط ۵۰۰ نامِ اول)؛ پرامپتِ کوتاه و بی‌تناقض برای مدل‌های کم‌ظرفیت
  (پشتِ تنظیم)؛ فشرده‌سازیِ تاریخچهٔ حلقه؛ بازبین با متنِ اصلی؛ انتخابِ مدل بر اساسِ موفقیت؛ حافظهٔ جلسه؛ حالتِ Cloud Code که پلان را دور می‌ریزد؛ ردِ اعمالِ جزئی/فازی.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest (با حلقهٔ عاملِ واقعی و مدلِ ساختگی)

## 2026-11-15 (۱۲) — بند ۱۲-ج: «عاملِ مرورگر» ِ بازرس ویژه (موس در دستِ مدل)

- **[FINDING]** (بازبینیِ عاملِ مرورگر) قطعه‌ها وجود داشت ولی ناقص: `browser_automation.py` (عاملِ بینایی ۲۰۲۶-۰۲، فقط مدل‌های تصویری، بی‌مرزِ دامنه،
  بی‌تأیید، بی‌تست، هر جلسه یک Chromium ِ جدا و نشتِ درایور)، `/inspector/ai-interact` یک درخواستِ مسدودکنندهٔ طولانی که فقط آدرسِ نهایی را به iframe
  می‌داد؛ `verify_runtime/browser_pool.py` پایهٔ درست (یک Chromium ِ مشترک، بستن پس از بیکاری).
- **[DECISION]** ماژولِ تازه و جدا (`services/browser_agent.py`) روی همان `browser_pool`، بی‌دست‌زدن به مسیرهای قدیمی (هیچ قابلیتی حذف نشد). برای مدل‌های
  ضعیف: مشاهدهٔ متنیِ فشرده (فهرستِ شماره‌دارِ عناصر با نقش/نام/وضعیت، متنِ قابِ دید؛ ≤۸۰ عنصر) + در صورتِ بینایی، عکس؛ یک کنشِ JSON ِ کوچک در هر گام
  با سه مثال؛ پارسِ بخشنده (حصار، تک‌کوتیشن، ویرگولِ اضافه)؛ یک بار تلاشِ ترمیم با خطای دقیق؛ تشخیصِ «گیر کرد». ایمنی **در سرور**: `context.route` هر
  میزبانِ بیرون از فهرست را قطع می‌کند؛ کلیکِ ثبت/ارسال/حذف/پرداخت و تایپ در فیلدِ رمز منتظرِ «اجازه» (۱۰ دقیقه)؛ رمز فقط `secret_ref` = `WATCHED_AUTH_*`
  و هرگز به مدل یا لاگ نمی‌رسد؛ متنِ صفحه «داده است نه دستور»؛ یک اجرا در هر زمان (۵۱۲MB)، ≤۴۰ گام، ۸ دقیقه، ۲۰ث برای هر کنش؛ عکس‌ها در `/tmp`، لاگِ
  متنی در `storage/browser_agent` (سقفِ ۲۰۰). پیگیری با polling (نه یک درخواستِ طولانی که لبهٔ Render قطعش می‌کند).
- **[CHANGE]** `services/browser_agent.py`، `api/routes/browser_agent.py` (`/api/inspector-agent/{models,runs,runs/{id},runs/{id}/reply,cancel,shots}`؛
  پشتِ دیوار؛ `BROWSER_AGENT_ENABLED=0` خاموش می‌کند)، `browser_pool.py` (`CHROMIUM_EXECUTABLE` ِ اختیاری و `--disable-dev-shm-usage`)،
  `components/BrowserAgentPanel.tsx` (کار، نشانی، سایت‌های مجاز، مدل با نشانِ 👁/📝، عکسِ زندهٔ هر گام، خطِ زمانِ گام‌ها، اجازه/رد، پاسخ به پرسش، توقف،
  گزارش به چتِ بازرس، دانلودِ .md)، دکمهٔ «🖱 عامل» کنارِ دکمهٔ ضبط در `projects/[id]/page.tsx`.
- **[VERIFY]** `test_browser_agent.py` (۵ تست با Chromium ِ واقعی و صفحهٔ محلی و یک «مدلِ ضعیفِ» برنامه‌ریزی‌شده که فقط متنِ مشاهده را می‌خواند: پرکردنِ
  ایمیل/انتخابِ پلن/تیک با JSON ِ نامرتب، توقف برای اجازه پیش از «ثبت» و نتیجهٔ واقعیِ فرم؛ مسدود شدنِ `evil.example`؛ دو پاسخِ نامعتبر ⇒ ناموفق؛ «گیر کرد»؛
  و سرتاسری از API روی pool ِ مشترک تا عکسِ گام)؛ pytest ۷۵۸ سبز؛ build سبز.
- **[TODO]** کیفیت با مدل‌های واقعی (کلیدِ API لازم است) با همین صفحه‌های آزمون سنجیده شود؛ اتصالِ اختیاری به جلسهٔ ضبط برای ساختِ ویدیو از گام‌ها؛ ورودِ خودکار
  با Auth Recipe ِ پروژه (`auth_runner`).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest با Chromium ِ واقعی + next build

## 2026-11-15 (۱۳) — بند ۱۲-د: پنج فراخوانیِ بی‌مسیرِ صفحهٔ پروژه؛ قفلِ «سیم‌کشیِ» فرانت↔بک‌اند در ارسالِ خودکار

- **[FINDING]** (`scripts/check_frontend_api.py` + بازبینِ چت، تأییدشده) در `projects/[id]/page.tsx` پنج دکمه/بارگذاری به مسیری می‌رفتند که هرگز در بک‌اند
  نبوده (`git -S` هیچ): فهرستِ فایل‌ها و خواندنِ فایل برای پروژه‌های موتور خالق (`/api/projects/{id}/files…`)، «Deploy» (`/deploy/render`)، «تولیدِ فایل‌های
  بیشتر» (`/api/creator/projects/{id}/generate`) و `validateHealthAnalysis` (کدِ بی‌فراخوان).
- **[CHANGE]** به مسیرهای واقعیِ `/api/simple/projects/{id}/…` (`files`، `files/{path}` با کدگذاریِ هر بخش، `deploy` با نمایشِ `url` و حالتِ «اول به GitHub
  ببرید»، `generate-more` با پرسیدنِ مسیرِ فایل‌ها) و `/health/validate-reports`. `check_frontend_api.py`: فهرستِ ۸ مثبتِ کاذبِ دستی‌بررسی‌شده.
- **[CHANGE]** `scripts/ship.sh` اکنون `check_frontend_api.py` را اجرا می‌کند (و `AGENTS.md` آن را نام می‌برد) ⇒ هر تغییرِ آینده‌ای که صفحه‌ای را به مسیرِ
  ناموجود یا متدِ اشتباه وصل کند، ارسال نمی‌شود — پاسخِ مستقیم به خواستِ مالک «سیم‌کشی‌ها به هم نخورد».
- **[VERIFY]** کلِ فرانت: ۳۹۸ فراخوانیِ متمایز، ۷۵۶ مسیرِ بک‌اند، **۰ بی‌مسیر**؛ build و pytest ۷۵۸ سبز؛ دروازهٔ مستندات سبز.
- **[OWNER]** بند ۱۲ و با آن کلِ طرحِ ۱۲ بندی انجام و ارسال شد؛ کارهای بازِ نیازمندِ تصمیمِ مالک: [OVERSIGHT.md §۱۲](handbook/OVERSIGHT.md) و TODO های (۱۰) تا (۱۲).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · check_frontend_api (۰ بی‌مسیر) + pytest + next build

## 2026-11-15 (۱۴) — تصمیم‌های مالک برای ایرادهای بازِ «اتاق فرمان» (دستهٔ ۱)

- **[OWNER]** «اون ۴ موردی که گفتی تصمیمِ منه نمی‌فهمم باید چی کار کنم — دقیق و خلاصه بگو یا خودت بهترین رو طبقِ خواسته‌های قبلی انجام بده؛
  ایرادهای بازِ اتاق فرمان و سایرِ قسمت‌ها را هم انجام بده.»
- **[DECISION]** (۱) دیسک: بایگانی در درایو سپس پاک‌سازی، بی‌پاک‌کردنِ دادهٔ بی‌بایگانی (قاعدهٔ ۳ و ۶) — دستهٔ بعد. (۲) فقط تأییدکنندهٔ مستقل «انجام‌شده»
  می‌گوید. (۳) تأییدِ سخت‌گیرتر. (۴) کلیکِ صریحِ مالک = اجازه؛ قاعدهٔ «اجرای خودکار خاموش ⇒ هیچ تغییری در GitHub» فقط برای کارِ **خودکار** است.
- **[CHANGE]** `prompt_github_sync._resolve_repo_and_branch(explicit=)`؛ `claude_runner_bootstrap` (نصب/حذف/تعمیر/dispatch صریح؛ dispatch با شاخهٔ مخزن؛ MASTER_PROMPT
  به شاخهٔ checkout‌شده push می‌کند)؛ `external_prompts` (TO-DO صریح؛ failed/abandoned از `/next` بیرون)؛ `oversight_service` (`run_task` هرگز done نمی‌زند؛ شمارهٔ
  دورِ auto-loop وقتی runner خاموش است؛ `created_at` در فهرستِ مخازن؛ اسکنِ اولِ مخزنِ تازه ~۱ ساعت بعد)؛ `oversight_verifier` (`_enough_real_passes`، شرطِ
  پوششِ v6)؛ `api_probe` (فقط خواندن مگر `RUNTIME_VERIFY_ALLOW_WRITES=1`).
- **[VERIFY]** `test_owner_decisions_2026_11_15.py` (۴)، آزمونِ پیش‌فرضِ «POST روی production رد» در `test_runtime_verify_real_servers.py`، تستِ نگهبانِ قدیمیِ شمارهٔ دور
  دقیق‌تر شد (مسیرِ runner همچنان قفل)؛ pytest ۷۶۳ سبز. وضعیتِ هر بند: `docs/handbook/OVERSIGHT.md` «به‌روزرسانیِ ۲۰۲۶-۱۱-۱۵ (ب)».

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest

## 2026-11-15 (۱۵) — ایرادهای بازِ «اتاق فرمان» (دستهٔ ۲): دیسک، اسکن، تکراری‌یابی، مستندات

- **[DECISION]** (تصمیمِ ۱ ِ مالک) دیسکِ ۱ گیگ: «اول بایگانی در گوگل درایو، بعد پاک‌سازی»؛ بی‌درایو هیچ چیز پاک نمی‌شود (قاعده‌های ۳ و ۶)؛ فقط کشِ بازسازی‌پذیر
  (`full_text_cache` ِ استخراج که کپیِ تکه‌های خودش است) در جا حذف می‌شود.
- **[CHANGE]** `services/disk_janitor.py` (+ `GET /api/oversight/disk`، `POST /api/oversight/disk/janitor`، اجرای ۶ساعته در زمان‌بند، رویدادِ تلگرامِ `disk_alert` در
  بک‌اند و تنظیماتِ اعلان، کارتِ «دیسکِ سرور» و نوارِ هشدار در خانه)؛ `oversight_service._write_json`: JSON ِ فشرده و ثبتِ خطای نوشتن (`last_write_error`) به‌جای بلعیدن.
- **[CHANGE]** اسکنِ عمیق: `run_deep_scan` یک اسکن برای هر پروژه (`ScanAlreadyRunning`) و سقفِ `DEEP_SCAN_TIMEOUT_MIN` (۶۰)؛ زمان‌بند آن را در پس‌زمینه اجرا
  می‌کند (`_spawn_bg`، `_scheduled_scan`) و نوبتِ بعد را از آغاز رزرو می‌کند؛ `POST /scan/{id}/deep` هنگامِ اسکنِ در جریان ۴۰۹ می‌دهد.
- **[CHANGE]** تکراری‌یابی: تطابقِ «هم‌نوع + هم‌فایل» شباهتِ عنوان (≥۰٫۳۵) هم می‌خواهد؛ تسک‌های لغوشده/آرشیوِ نیمه‌تمام «شناخته‌شده» حساب می‌شوند؛ بررسی پیش از
  فراخوانیِ چک‌لیستِ AI؛ اسکنِ سریع هم تکراری‌یابی گرفت.
- **[CHANGE]** بنرِ اصلاح بالای README/ARCHITECTURE/ROADMAP/AUDIT_REPORT/SYSTEM_REPORT (متنِ قدیم دست‌نخورده).
- **[VERIFY]** `test_disk_janitor.py` (۴: بی‌درایو هیچ حذفی؛ با درایو بایگانی‌سپس‌حذف و نگه‌داشتنِ تازه‌ها؛ آپلودِ ناموفق فایل را نگه می‌دارد؛ گزارشِ خطای نوشتن)، دو تستِ
  تازه در `test_oversight_audit_fixes_2026_11_15.py` (یک اسکن برای هر پروژه + سقفِ زمان؛ تکراری‌یابی)؛ pytest ۷۶۹ سبز؛ build سبز.
- **[TODO]** بایگانیِ گزارش‌های بسیار قدیمیِ `reports.json` به درایو وقتی بزرگ شد (فعلاً هشدار می‌دهد)؛ نوشتنِ کاملاً غیرهمگامِ `tasks.json`.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build

## 2026-11-15 (۱۶) — «بازرس ویژه» (دستهٔ ۳): ویدیوی تلگرام، امنیتِ سوکتِ پل، Cloud Code، اعمالِ نیمه‌کاره

- **[FINDING]** (TODO های (۱۰) تا (۱۲)) webm ِ MediaRecorder در تلگرام پخش نمی‌شد و برشِ بایتیِ ۴۵MB بخش‌های ۲ به بعد را خراب می‌کرد؛ سمتِ «inspector» ِ سوکتِ
  `/api/render/ws/bridge/{project}` بی‌احراز بود (دیوارِ ورود WebSocket را نمی‌بیند) و هر کس نامِ کانال را داشت می‌توانست به صفحه‌های واردشدهٔ مالک فرمانِ کلیک/ناوبری
  بفرستد؛ `chat-cloud-code` پلانِ ثبت‌شده را دور می‌ریخت (callback نداشت) و شاخه را `main` فرض می‌کرد؛ `apply-action` فایلی را که بخش‌هایش نیمه جور شده بود commit می‌کرد.
- **[CHANGE]** `inspector_recording_finalize.webm_to_mp4_parts` (H.264/AAC، faststart، تقسیمِ زمانی) و `webm_audio_to_m4a` (بازگشت به مسیرِ قبلی اگر ffmpeg شکست خورد)؛
  `render_logs` سوکتِ پل: ثبتِ «inspector» با `preview_ticket` (پیام یا `?ticket=`)، «bridge» بی‌تغییر؛ فرانت: `getPreviewTicket` و ارسالِ بلیت در register؛
  `chat-cloud-code`: شاخهٔ پیش‌فرضِ واقعی از GitHub، `on_submit_action_plan` و رویدادِ SSE ِ `action_plan` ⇐ دکمهٔ اعمال؛ `apply-action`: ردِ اعمالِ ناقص
  (`INSPECTOR_ALLOW_PARTIAL_APPLY=1` برای اجازه) با پیامِ روشن.
- **[VERIFY]** `test_recording_keyframes.py` (+۲: MP4 و m4a با ffmpeg ِ واقعی)، `test_preview_ticket.py` (+۱: سوکت با روترِ واقعی — بی‌بلیت رد، با بلیت پذیرفته، bridge
  بی‌تغییر)؛ pytest ۷۷۲ سبز؛ build سبز.
- **[TODO]** ماندگاریِ جلسه‌های ضبط پس از ری‌استارت؛ بردنِ ویدیوی نهایی به گوگل درایو؛ حالتِ اسکرینِ سمتِ سرور برای سایت‌هایی که پروکسی را نمی‌پذیرند؛ ورودِ خودکارِ
  عاملِ مرورگر با Auth Recipe.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest (ffmpeg و WebSocket ِ واقعی) + next build

## 2026-11-15 (۱۷) — «بازرس ویژه» (دستهٔ ۴): اسکرینِ خودترمیم با «نمای سرور»، ورودِ خودکارِ عامل، ضبط به درایو، انتخابِ مدل

- **[CHANGE]** `GET /api/inspector-agent/snapshot` (عکسِ JPEG ِ یک نشانیِ http(s) از Chromium ِ مشترکِ سرور؛ فقط خواندن؛ یکی‌یکی) و `components/ServerScreen.tsx`:
  وقتی iframe ِ کنارِ چت خطا می‌دهد **یا ۵ ثانیه پس از بار شدن خالی می‌ماند** (chunk های پویای Next از پروکسی نمی‌رسند)، به‌جای کادرِ قرمز «نمای سرور» با تصویرِ زندهٔ
  همان صفحه نشان داده می‌شود و هر دقیقه (و با دکمه) iframe دوباره با بلیتِ تازه امتحان می‌شود — همان «خودکار خودش را اصلاح کند» ِ مالک.
- **[CHANGE]** عاملِ مرورگر: `login_state_for` — اگر پروژه‌ای در اتاق فرمان با همان سایت Auth Recipe داشته باشد، اجرا با نشستِ واردشدهٔ آن آغاز می‌شود (`auth_runner`؛ رمزها
  فقط از `WATCHED_AUTH_*`)؛ تیکِ «اول وارد شو» در پنل (پیش‌فرض روشن).
- **[CHANGE]** ضبط: `_archive_recording_to_drive` — ویدیو/صدا/پرامپتِ نهایی در «project-management/ضبط‌های بازرس/<تاریخ>_<جلسه>/» (اگر درایو وصل است) و پیوندش در
  کپشنِ تلگرام و نتیجه (قاعدهٔ ۶)؛ پنل: 404 ِ «session» ⇒ «جلسه با به‌روزرسانی/ری‌استارتِ سرور از دست رفت — دوباره ضبط کنید».
- **[CHANGE]** چت: `_smart_select_model` مدل‌های آرشیو را با نرخِ موفقیتِ هموارشده (`backend_verified`) مرتب می‌کند، نه تعدادِ استفاده.
- **[VERIFY]** `test_browser_agent.py` (+۱: نمای سرور با Chromium ِ واقعی؛ `file://` رد)؛ pytest ۷۷۳ سبز؛ build سبز.
- **[TODO]** (تصمیمِ آگاهانه، نه فراموشی) پیش‌فرض‌های «پیکربندی» در «مدل‌ها و تنظیمات» به `ai_manager` وصل نشد: هر فراخواننده مقدارِ خودش را می‌فرستد و تغییرِ سراسری
  رفتارِ همهٔ مدل‌ها را عوض می‌کند — برچسبِ روشن روی همان تب هست. کوتاه‌کردنِ پرامپتِ ~۳۳ هزار نویسه‌ایِ چت برای مدل‌های کم‌ظرفیت و نقشهٔ کاملِ مخزن گامِ بعدِ کیفیتِ چت‌اند.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest (Chromium ِ واقعی) + next build

## 2026-11-15 (۱۸) — ده ایرادِ کوچک‌ترِ صفحهٔ «اتاق فرمان» (بازبینیِ فرانت، موارد ۷ تا ۲۰)

- **[CHANGE]** `oversight/page.tsx`: `consumeSSEStream` پاسخِ JSON (ردِ «پروژه یافت نشد»/«review gate» با ۲۰۰) را به‌صورتِ خطای واقعی نشان می‌دهد به‌جای «PR ساخته نشد»؛
  جست‌وجوی گزارش‌ها روی `project_full_name`/`done_parts`/`remaining_parts`/`next_actions`/`raw_response`/`model_id`؛ «از تاریخ» با مقایسهٔ زمان (نه رشته) و «تا تاریخ»
  شاملِ کلِ روز؛ کلیدِ «auto-loop eligible» شاخه گرفت؛ `verifyTaskNow` حالتِ `verify_mode` ِ پروژه را رعایت می‌کند؛ `onReplaced` وضعیتِ runner را در فهرستِ صفحه نگه
  می‌دارد؛ interval های bulk-verify و backfill هنگامِ بسته شدن پاک می‌شوند؛ پس از ادغام، شناسهٔ پیش‌نویس تازه و مدلِ موقت برگردانده می‌شود؛ متن‌های ناهمخوان اصلاح.
  `ExtractedFilesPanel.tsx`: وضعیتِ بارگذاری برای هر فایل (خطا / بی‌متن به‌جای «بارگذاری» ِ ابدی). `tailwind.config.js`: safelist ِ کلاس‌های پویای دکمه‌های تنظیمات.
- **[VERIFY]** build سبز؛ Playwright محلی: هر ۵ تبِ اتاق فرمان و خانه بی‌خطای کنسول/شبکه؛ `GET /api/oversight/disk` پاسخ داد؛ pytest ۷۷۳ سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · next build + Playwright محلی + pytest

## 2026-11-15 (۱۹) — آخرین دستهٔ ایرادهای تأییدشده (اتاق فرمان و بخش‌های دیگر) + پاسخ به «چهار تصمیم»

- **[OWNER]** «اون ۴ موردی که گفتی تصمیمِ منه نمی‌فهمم … یا خودت بهترین رو طبقِ خواسته‌های قبلی انجام بده؛ ایرادهای بازِ اتاق فرمان و سایر قسمت‌ها رو هم انجام بده».
- **[DECISION]** چهار تصمیم را خودم گرفتم (ورودیِ ۱۵-۱۱ در کامیتِ 67130a68): اجرای خودکار فقط با اجازهٔ صریح، تسکِ اجراشده «منتظرِ بازبینی» نه «انجام‌شده»،
  probe های تأیید فقط خواندنی، و شاخهٔ کاری به‌جای main — همه در جهتِ «با احتیاط» و «هیچ قابلیتی حذف نشود».
- **[CHANGE]** `oversight_upload_session.py`: بررسیِ offset/اندازهٔ تکه داخلِ قفلِ همان نشست (دو تکهٔ هم‌زمان دیگر هر دو نمی‌گذرند).
- **[CHANGE]** `oversight_model_temp_activate.py`: موقتاً روشن‌شدن فقط وقتی «موقت» ثبت می‌شود که مدل از قبل خاموش بوده؛ پاک‌سازیِ هنگامِ راه‌اندازی مدل را واقعاً خاموش می‌کند.
- **[CHANGE]** `verify_runtime/storage.resolve_evidence_file`: `task_id`/`run_id` فقط `[A-Za-z0-9_.-]` و بی «..» (قبلاً فقط `rel_path` بررسی می‌شد).
- **[CHANGE]** `routes/oversight.py`: `_clamp_intervals` — `interval_hours`/`scan_interval_hours`/`verify_interval_hours` ِ صفر/منفی/NaN ⇒ ۰٫۲۵ (هم پروژه هم تنظیماتِ کلی)؛
  `start_bulk_verify` پرچمِ running را پیش از ساختنِ task می‌گذارد (finally ِ اجرا همیشه پاکش می‌کند).
- **[CHANGE]** `backend_log_probe._fetch_relevant_logs(project_urls=…)` + `_service_ids_for_urls`: نشانیِ فرانت/بک‌اند ⇒ سرویس‌های Render (با `service_url` یا نامِ زیردامنهٔ
  onrender.com) ⇒ فقط لاگِ همان‌ها؛ نشانیِ ناشناخته ⇒ هیچ. فراخواننده‌ها: probe ِ تأیید، `runtime_discovery`، تحلیلِ اثربخشیِ اسکنِ عمیق. بدونِ نشانی رفتارِ قبلی.
- **[VERIFY]** `tests/test_oversight_small_fixes_2026_11_15.py` (۴ تست، SQLite ِ واقعی برای لاگ‌ها)؛ pytest ۷۷۷ سبز.
- **[TODO]** (اختیاری، ثبت‌شده) بایگانیِ `reports.json` ِ بزرگ در درایو؛ نوشتنِ کاملاً async ِ `tasks.json`؛ ماندگاریِ نشست‌های ضبط پس از ری‌استارت.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest

