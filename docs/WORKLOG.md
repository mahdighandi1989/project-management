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
