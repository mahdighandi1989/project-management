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

## 2026-11-15 (۲۰) — «موارد اختیاری»: ضبطی که با ری‌استارت گم نمی‌شود، بایگانیِ گزارش‌های قدیمی در درایو، نوشتنِ پس‌زمینهٔ tasks.json

- **[OWNER]** «موارد اختیاری ماند هر رو هم انجام بده».
- **[CHANGE]** ضبطِ بازرس — ادامه پس از دیپلوی/ری‌استارت: مرورگر هر تکهٔ صدا/ویدیو را (تا ۵۱۲ مگابایت) نگه می‌دارد؛ با «session_not_found»
  `POST /api/recording/inspector/{id}/resume` جلسه را **با همان شناسه** و طولِ واقعیِ ضبط دوباره می‌سازد و همهٔ تکه‌ها را دوباره می‌فرستد؛ ضبط ادامه
  می‌یابد. اگر سرور بینِ آخرین تکه و «پایان» ری‌استارت شد، همین کار پیش از stop انجام می‌شود؛ تکه‌هایی که ۳ تلاششان شکست خورده بود پیش از stop
  یک دورِ دیگر فرستاده می‌شوند. سرور هر seq را یک بار می‌شمارد و تکه‌های باقی‌مانده روی دیسک را هنگامِ بازسازی می‌شمارد؛ شناسهٔ غیرِ uuid رد می‌شود.
  (`inspector_recording_service.resume_session`، `InspectorRecordingPanel.tsx`). محدودیت: قاب‌های حالتِ A ِ polling که در لحظهٔ قطعی رسیدند جبران نمی‌شوند.
- **[CHANGE]** `services/reports_archive.py`: وقتی `reports.json` از ۵ مگابایت گذشت (`REPORTS_ARCHIVE_MIN_BYTES`)، گزارش‌های قدیمی‌تر از ۳۰ روز که آخرین گزارشِ
  تسکشان نیستند **کامل** در درایو («بایگانیِ سرور/reports/»، gzip) بایگانی و فقط **پس از تأییدِ درایو** فیلدهای سنگینشان (خروجیِ خام، شواهد، trace، probe ها،
  config) روی سرور خالی می‌شود؛ خودِ گزارش (وضعیت، بخش‌ها، گام‌های بعد، شناسنامه، خوانده/پرچم) و `archived_to` می‌ماند — هیچ داده‌ای حذف نشده.
  باز کردنِ گزارش (`GET /reports/{id}`، verify-trace) نسخهٔ کامل را خودکار از درایو برمی‌گرداند؛ پنجرهٔ «جزئیات گزارش» این را نشان می‌دهد. درایو وصل نباشد ⇒ هیچ.
  هر ۶ ساعت با پاک‌سازِ دیسک اجرا می‌شود.
- **[CHANGE]** `oversight_service._write_json_soon`: `tasks.json` و `reports.json` (۵۶ نقطهٔ ذخیره) در یک رشتهٔ پس‌زمینه نوشته می‌شوند — عکسِ داده روی همان
  حلقه گرفته می‌شود (`asdict` = کپیِ عمیق)، فقط json.dump/نوشتن/rename بیرون؛ برای هر فایل تازه‌ترین عکس برنده است و شمارهٔ ترتیب نمی‌گذارد نسخهٔ کهنه روی
  تازه بنشیند؛ در خاموش‌شدن `flush_pending_writes` منتظر می‌ماند. بیرونِ حلقه همان نوشتنِ همگام؛ `OVERSIGHT_SYNC_WRITES=1` = رفتارِ قبلی.
- **[VERIFY]** `tests/test_optional_items_2026_11_15.py` (۸ تست: بازسازیِ جلسه، شمارشِ یک‌باره، ردِ شناسهٔ بد، انتخاب و بایگانی و بازیابیِ گزارش، بی‌درایو بی‌کار،
  ترتیب و flush و نبستنِ حلقه)؛ آزمونِ واقعی: uvicorn ِ محلی، شروعِ ضبط ⇐ تکه ⇐ **کشتنِ سرور و راه‌اندازیِ دوباره** ⇐ ۴۰۴ ⇐ resume ⇐ تکه‌ها ⇐ وضعیت «recording»
  با طولِ درست؛ pytest ۷۸۵ سبز؛ next build سبز.
- **[TODO]** (کیفیت، نه ایراد) کوتاه‌کردنِ پرامپتِ بزرگِ چتِ بازرس برای مدل‌های کم‌ظرفیت + نقشهٔ مخزن (WORKLOG ۱۷).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + uvicorn ِ محلی با ری‌استارتِ واقعی + next build

## 2026-11-15 (۲۱) — پرامپتِ فشرده برای مدل‌های ضعیف‌تر در چتِ «بازرس ویژه» + نقشهٔ واقعیِ مخزن

- **[OWNER]** «اونم انجام بده» (کوتاه‌کردنِ پرامپتِ چتِ بازرس برای مدل‌های کم‌ظرفیت — TODO ِ WORKLOG ۱۷).
- **[FINDING]** اندازه‌گیری: ۱۲ «دستورِ عمومیِ سیستم» به‌تنهایی ۲۴٬۹۶۴ نویسه‌اند (قاعدهٔ «ممنوعیتِ بازنویسیِ مخرب» ۸٬۶۰۸ و «قانونِ ابهام» ۶٬۱۵۶) و پرامپتِ
  سیستمیِ حالتِ عامل ~۹٬۱۰۰ نویسهٔ دیگر — جمعاً ~۳۴ هزار پیش از خواندنِ حتی یک فایل؛ نقشهٔ پروژه فقط «📁 پوشه (N فایل)» بود و مدل مسیرِ واقعی را حدس می‌زد.
- **[CHANGE]** `services/inspector_compact_prompt.py`: `is_compact_model` (پنجرهٔ زمینهٔ ≤ ۱۳۱k، نام‌های mini/flash/lite/…، یا خانوادهٔ غیرِ مرزی؛
  `INSPECTOR_COMPACT_PROMPT=1|0` برای اجبار)؛ `SHORT_RULES` — خلاصهٔ هر قاعده با حفظِ **تصمیم‌ها و قالب‌ها** (modify_sections، ask_user، render_actions،
  route_to، runtime.txt، user_clarification) ⇒ ۲٬۹۸۵ نویسه؛ قاعده‌ای که خلاصه ندارد کامل می‌ماند (هیچ قاعده‌ای بی‌صدا حذف نمی‌شود)؛ `build_repo_map` — نامِ
  واقعیِ فایل‌ها با اولویتِ پوشه‌های مرتبط با متنِ درخواست/لاگ، در بودجه؛ `agent_system_compact` — روشِ گام‌به‌گام + دفترچهٔ Render/Postgres فقط وقتی درخواست
  دربارهٔ deploy/پایگاه‌داده است (~۴٬۵۰۰ نویسه با همه‌چیز).
- **[CHANGE]** `render_logs.py` (smart-chat): تصمیم روی **مدلِ نهایی** (پس از مسیریابیِ فاز ۲) گرفته می‌شود؛ بلوک‌های بافتِ تسک/حافظه/آموزش جدا نگه داشته و برای
  مدلِ فشرده تا ۶٬۰۰۰ نویسه (بافتِ تسک اول است و می‌ماند)؛ رویدادِ پیشرفتِ «🪶 پرامپتِ فشرده … ⇐ …». نقشهٔ واقعیِ مخزن برای **همهٔ** مدل‌ها در حالتِ عامل
  جای خلاصهٔ پوشه‌ای را گرفت. مدل‌های قوی (Claude و …) همان متنِ کامل را می‌گیرند؛ پنلِ «دستورات عمومی» دست نخورد.
- **[VERIFY]** `tests/test_inspector_compact_prompt.py` (۶ تست: پوششِ همهٔ قاعده‌ها، قالب‌های حیاتی در متنِ کوتاه، انتخابِ مدل، نقشه، Render ِ شرطی، سیم‌کشی)؛
  pytest سبز. آزمونِ با مدلِ واقعی انجام نشد (کلیدِ مدل در این محیط نیست) — رویدادِ «🪶» در چت نشان می‌دهد کدام مدل فشرده گرفته.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest

## 2026-11-15 (۲۲) — «مدل‌ها همه رفتند»: یافتنِ علت و توقفِ خاموش‌شدنِ خودکارِ مدل‌ها

- **[OWNER]** «مدل‌های داخلِ سیستم و پروژه چی شد؟ گویا همه‌شون رفتن اما کجا؟ مگه تو رندر ثبت نشدن؟»
- **[FINDING]** کلیدها سرِ جایشان‌اند: در Render برای OpenAI، Claude، Gemini، DeepSeek، Perplexity کلید هست و هنگامِ راه‌اندازی هر ۵ سرویس «initialized» می‌شوند
  (لاگِ ۱۵-۱۱ ساعتِ ۱۴:۰۲). ولی از ۲۰۲۶-۱۱-۱۳ لاگ پر از «No available models for fallback» است ⇒ مدل‌ها در **تنظیماتِ پایگاه‌داده خاموش** شده‌اند (`ModelSettings.enabled=0`).
- **[FINDING]** علت: `temp_revert_model` (فعال‌سازیِ موقتِ مدل برای کارهای اتاق فرمان) وقتی سابقهٔ «حالتِ اولیه» را نداشت (ری‌استارت بینِ فعال‌سازی و بازگردانی، یا
  بازگردانیِ دوباره) فرض می‌کرد «قبلاً خاموش بوده» و مدل را **خاموش** می‌کرد — حتی مدلی که مالک خودش روشن کرده بود؛ هر بار یکی، تا همه رفتند. اصلاحِ امروزِ من
  (۱۹) هم در پاک‌سازیِ هنگامِ راه‌اندازی مدل‌های پرچم‌دار را خاموش می‌کرد، در حالی که کدِ قدیمی و `inspector_roles` این پرچم را روی مدل‌های از قبل روشن هم می‌گذاشتند — آن هم برگردانده شد.
- **[CHANGE]** `oversight_model_temp_activate.temp_revert_model`: بی‌سابقه ⇒ هیچ تغییری. `cleanup_stale_temp_activations_on_boot`: فقط پرچم پاک می‌شود، `enabled` نه.
  `inspector_roles`: مدلِ از قبل روشن «موقت» علامت نمی‌خورد.
- **[VERIFY]** `tests/test_models_never_switched_off_blindly.py` (۳ تست).
- **[OWNER-ACTION]** مدل‌هایی که خاموش شده‌اند خودکار روشن نمی‌شوند (نمی‌دانم کدام را شما روشن خواسته بودید و روشن‌کردنِ همه هزینه دارد): «مدل‌ها و تنظیمات» ⇐ تبِ «مدل‌ها» ⇐ روشن کنید.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + لاگ‌های Render

## 2026-11-15 (۲۳) — بازبینیِ فوق‌العاده عمیقِ کارتِ پروژه‌ها در «اتاق فرمان» + جعبهٔ جدا برای هر پروژه + وارسیِ دوبارهٔ ۱۲ بند

- **[OWNER]** «همهٔ زیر و بم از درشت تا ریزترین کارهای این قسمت‌ها و ارتباطات و سیم‌کشی‌ها و ریزتنظیمات رو بفهمی و فلسفه‌ش رو دربیاری … خطاها چیه …
  اسکن دوره‌ای … فولدر TO-DO … مدل‌ها از طریقِ گیت‌هاب و اشتراکِ کلاد … تداخل با سشن‌ها … مرزِ دو پروژه مشخص نیست، تو یه باکسِ مشخص‌تر …
  ۱۲ بندِ ابتدایی رو بازبینی کن».
- **[FINDING]** پنج بازبینِ مستقل (فقط‌خواندنی؛ کد + لاگ‌های Render + اجرای محلی): (۱) از ۱۱ آبان هر ۲۰ اسکنِ هفتگی بی‌مدل اجرا شد ولی «۱۲/۱۲ موفق»
  ثبت، به تلگرام فرستاده و برنامهٔ بعدی یک هفته عقب رفت؛ (۲) هر ۲۰ verify از ۹ آبان شکست خورد و تسک‌ها در «error» ماندند (زمان‌بند هرگز سراغشان نمی‌رفت)؛
  (۳) verify ِ زمان‌بندی‌شده پیشنهادهای تأییدنشدهٔ اسکن را «pending» (قابلِ اجرا) می‌کرد؛ (۴) workflow ِ کهنهٔ Claude Runner در **همین مخزن** فعال و قابلِ اجرا
  بود و مستقیم روی main (= production) push می‌کرد؛ (۵) کلیدِ اصلیِ سرور (`EXTERNAL_TOOL_TOKEN`) در secret ِ مخازنِ پروژه‌ها کپی می‌شد؛ (۶) فایلِ TO-DO از مسیرهای خودکار
  بی‌اجازه روی main ِ مخزنِ پروژه کامیت می‌شد؛ (۷) «زمان‌بندی فعال» verify را متوقف نمی‌کرد؛ (۸) هر ویرایشِ یادداشت/برچسب «بعدی» را یک بازهٔ کامل عقب می‌برد؛
  (۹) اسلایدرِ وزن‌ها تا ۲۰ PATCH در هر کشیدن؛ ورودی‌های عددی «24/168» را برمی‌گرداندند و «96» ⇒ «2496»؛ (۱۰) دو کلیدِ بی‌اثر (cleanup، صدای auto-task)؛
  (۱۱) چند راهنما دروغ می‌گفتند (assist، auto via PR، allow_push، fast ~۵ ثانیه، عمقِ اسکن)؛ (۱۲) v6 می‌توانست «not_done» را با grep «done» کند و مرحلهٔ مدلِ قوی‌اش
  با ImportError همیشه بی‌اثر بود؛ (۱۳) پروب‌های UI روی سایتِ زنده می‌توانستند فرم ارسال کنند. ۱۲ بند: ۱۱ کامل، بازرسِ ویژه دو ایراد (پهنای صفحه، لینکِ ‎?tab=inspector).
- **[DECISION]** «با احتیاط»: اسکنِ بی‌مدل = شکست؛ اسکنِ خودکار مدلِ خاموش را روشن نمی‌کند؛ «زمان‌بندی فعال» = سوییچِ اصلیِ هر سه ساعت؛ ۰ = خاموش برای اسکن/verify؛
  runner پیش‌فرض شاخهٔ جدا + PR (push ِ مستقیم فقط با «اجازهٔ push»)؛ مخزنِ خودِ برنامه همیشه مستثنا؛ workflow ِ کهنه **قرنطینه** نه حذف.
- **[CHANGE]** بک‌اند: `oversight_deep_scan_service` (`ai_passes_ok`، `ScanNoModel`، `passes_total=len(enabled)`، اسکنِ موردی برنامه را عقب نمی‌برد، ری‌استارت ⇒ تلاش پس از ۱ ساعت)؛
  `oversight_service` (`_scheduled_scan` با `pick_scan_model` و back-off ۱/۶/۲۴ ساعت + `scan_fail_count` + تلگرامِ `scan_failed`؛ `_scheduled_verify` در پس‌زمینه؛ فیلترِ نامزدها؛
  «بعدی» فقط با تغییرِ زمان‌بندی؛ `last_run_at` فقط با اجرای واقعی؛ کلیدهای cleanup/صدا؛ بازتولید با cooldown و حفظِ ۵۰ نسخه)؛ `routes/oversight` (Literal و بازه‌ها، ۰=خاموش،
  مسابقهٔ Deep Scan)؛ `oversight_verifier` (v6 فقط از partial)؛ `iterative_orchestrator` (مرحلهٔ ۳ و `_model_available`)؛ `inspector_probe` (گام‌های تغییردهنده پشتِ پرچم)؛
  `core/auth` (`runner_token_for`)؛ `external_prompts` (کلیدِ runner، حالتِ PR ⇒ awaiting_review، TO-DO با دروازهٔ خودکار)؛ `claude_runner_bootstrap` (شاخه + PR،
  مسیرِ درستِ فایلِ تسک، کلیدِ محدود)؛ `prompt_github_sync` (`_SELF_REPOS`، `allow_excluded` فقط برای حذفِ نصب)؛ `render_logs` (قاعدهٔ یکسانِ «روشن بودنِ» مدل).
  فرانت: `oversight/page.tsx` (جعبهٔ هر پروژه: قابِ کامل، نوارِ رنگیِ لبهٔ آغاز، نوارِ عنوان، پانویسِ دکمه‌ها؛ سه خطِ دقیقِ زمان‌بندی؛ `NumField`؛ اسلایدرِ یک‌باره؛ پیامِ خطای ۴۲۲؛
  متن‌های درست)؛ `Layout.tsx` (`min-w-0`)؛ `projects/[id]` (لینکِ ‎?tab=inspector&session=)؛ خانه («مدل‌های روشن» به‌جای سرویس‌های کلیددار)؛ راهنما (مسیرِ واقعی).
  مخزن: `.github/workflows/claude-auto-task.yml` ⇐ `docs/quarantine/` (+ README).
- **[VERIFY]** `tests/test_oversight_owner_audit_2026_11_15.py` (۹ تست)؛ pytest ۸۰۳ سبز؛ next build سبز؛ Playwright محلی: دو پروژه در حالتِ روشن و تاریک (جعبه‌ها جدا، بی‌خطای کنسول)،
  ورودیِ عددی (۹۶ ذخیره شد، ‎-4 با پیام رد شد)، اسکنِ محلیِ بی‌GitHub «۱ شکستِ پیاپی · تلاشِ بعدی» نشان داد.
- **[OWNER-ACTION]** (۱) مدل‌ها را در «مدل‌ها و تنظیمات» ⇐ «🧠 مدل‌ها» ⇐ «مدیریت» روشن کنید (یکی‌یکی یا «✓ فعال کردن همه»)؛ (۲) در GitHub ِ project-management، secret های
  قدیمیِ `CLAUDE_CODE_OAUTH_TOKEN`/`OVERSIGHT_EXTERNAL_TOKEN`/`OVERSIGHT_BACKEND_URL` ِ آن workflow را اگر خواستید پاک کنید (من به secret ها دسترسی ندارم).
- **[TODO]** موارد «باز» در OVERSIGHT.md به‌روزرسانیِ (و).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · ۵ بازبینِ مستقل + pytest + next build + Playwright محلی + لاگ‌های Render

## 2026-11-15 (۲۴) — «موارد باز» ِ بازبینیِ کارتِ پروژه، بسته شد

- **[OWNER]** «موارد باز مانده رو هم انجام بده».
- **[CHANGE]** `routes/oversight.py`: `_BULK_VERIFY_STATE` (سراسری) ⇐ `_new_bulk_state()` + `_BULK_STATES[watched_id]` + `_bulk_running_other`؛ شروع با `_spawn_bg` (مرجع نگه داشته می‌شود).
  `oversight_service`: `report_counts_by_watched` در `/status`؛ `_scheduled_run` + `_RUNNING_RUNS` (اجرای خودکار در پس‌زمینه)؛ فیلترِ همگام‌سازیِ اول. `external_prompts.require_external_token`:
  محدودهٔ کلیدِ runner (۴۰۳ برای پروژهٔ دیگر). `oversight_verifier._enough_real_passes`: نرمال‌سازی به شمارهٔ AC و حداقلِ ۲ بی AC ِ ذخیره‌شده (تستِ قبلی آگاهانه تغییر کرد).
  فرانت: شمارهٔ گزارش‌ها از سرور؛ ادغامِ polling تسکِ تازه‌بایگانی‌شده را نگه می‌دارد.
- **[VERIFY]** `tests/test_oversight_open_items_2026_11_15.py` (۵ تست) + به‌روزرسانیِ دو تستِ قبلی؛ pytest ۸۰۸ سبز؛ next build سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest + next build

## 2026-11-15 (۲۵) — فوری PM-INS-0002: «بازرس ویژه» با تنها مدلِ روشن (cloud_code) و چیدمانِ ۱۳۶۰px

- **[OWNER]** برگهٔ فوریِ PM-INS-0002 (بند ۱۲): (۱) «دستیار بازرس هوشمند» می‌گوید «مدلی انتخاب نشده» در حالی که تنها مدلِ روشن cloud_code است — باید خودکار
  بهترین مدلِ روشن (رتبهٔ موفقیت) انتخاب و پیامِ روشن داده شود؛ (۲) در ۱۳۶۰px پنلِ چت زیرِ منوی کناری بریده می‌شود؛ (۳) پیش‌نمایشِ «دکمه پاور» را مالک بعداً گزارش می‌کند.
- **[FINDING]** `/inspector/models` و `_smart_select_model` «در دسترس بودن» را فقط با `provider in ai_manager._services` می‌سنجیدند؛ cloud_code سرویسِ کلیددار ندارد
  (dispatcher ِ OAuth است) ⇒ همیشه `enabled=false` و انتخابِ خودکار به `gemini-2.0-flash` ِ خاموش برمی‌گشت. مدل‌ها هم فقط با دکمهٔ پاور بار می‌شدند.
- **[FINDING]** ردیفِ اسکرین/چت عرضِ ثابتِ ۸۴۰+۳۸۰px داشت (+ منوی کناری ⇒ سرریز در ۱۳۶۰px).
- **[CHANGE]** `render_logs._oauth_model_ready` (dispatcher + توکن، همان قاعدهٔ `ai_manager.get_available_models`) در `/inspector/models` و `_smart_select_model`.
  فرانت `projects/[id]`: بارگذاریِ مدل‌ها هنگامِ باز شدنِ صفحه؛ سرِ چت «✨ خودکار: <نامِ مدل>» / «⚠️ هیچ مدلِ روشنی نیست — …»؛ ردیف `flex-wrap` با `flex: 1 1 560px / 340px`.
- **[VERIFY]** `tests/test_inspector_oauth_model_ready.py` (۳ تست)؛ pytest ۸۱۱ سبز؛ next build سبز. محلی با توکنِ ساختگی: `/inspector/models` فقط `cloud_code` را روشن و
  `smart-select-model` آن را برگزید؛ Playwright در ۱۳۶۰ و ۱۶۰۰px: سرِ چت «✨ خودکار: Cloud Code (Claude OAuth)»، بی‌سرریزِ افقی (scrollWidth = clientWidth).
- **[TODO]** بند ۳ (پیش‌نمایش/پاور) منتظرِ گزارشِ مالک.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest ۸۱۱ + next build + Playwright محلی ۱۳۶۰/۱۶۰۰px

## 2026-11-15 (۲۶) — فوری PM-INS-0005: نمرهٔ «۰» ِ تستِ توانایی، «API ✓» ِ بی‌پشتوانه، خاموش‌شدنِ خودبه‌خود

- **[OWNER]** برگهٔ فوریِ PM-INS-0005: همهٔ ۲۲ مدل خاموش دیده شدند؛ پس از روشن‌کردنِ ۷ مدل، gpt-4o-mini، claude-sonnet-4-6، claude-haiku-4-5 و sonar در «تست توانایی» «۰ مبتدی»
  گرفتند با اینکه کارت «API ✓» بود. خواسته: (۱) علتِ واقعیِ هر ۰ در کارت؛ (۲) «API ✓» فقط پس از فراخوانیِ واقعیِ موفق؛ (۳) مدل‌های روشن خودبه‌خود خاموش نشوند؛
  (۴) بازرس/اتاق فرمان/دستیار پیش‌فرض را از مدل‌های موفق بگیرند.
- **[FINDING]** خطای هر تست در `categories[*].tests[*].error` بود ولی UI فقط نمرهٔ کلی (۰) و نشانِ «مبتدی» را نشان می‌داد. «API ✓» فقط «کلیدِ provider هست» بود.
- **[FINDING]** پاک‌سازیِ فعال‌سازیِ موقت (`render_logs` سه جا) مدلی را که `temporary_enabled=1` دارد خاموش می‌کند — و روشن‌کردنِ دستیِ مالک آن پرچم را پاک نمی‌کرد ⇒ مدلِ
  روشن‌شده توسطِ مالک بعداً خاموش می‌شد. toggle ِ مدلی که ردیفِ DB نداشت همیشه `enabled=0` می‌ساخت ⇒ «روشن کن» برای مدلی با پیش‌فرضِ خاموش، خاموش می‌ماند.
- **[CHANGE]** `model_capability_tester`: `errors`، `calls_ok/calls_total`، `all_failed` + `record_last_call` (در `ModelSettings.advanced_settings["last_call"]`، بی‌مهاجرت).
  `routes/models.py`: `last_call` در `/api/models`؛ پاک‌کردنِ `temporary_enabled` در PUT/toggle/batch-update؛ toggle ِ بی‌ردیف = برعکسِ پیش‌فرضِ رجیستری.
  فرانت `ModelsView`: نشانِ سه‌حالته (API ✓ / کلید ✓ · آزموده نشده / API ✕ فراخوانی شکست خورد) و جعبهٔ خطای واقعی؛ پس از تست فهرست تازه می‌شود. `services/api.ts`: `last_call`.
- **[VERIFY]** `tests/test_model_last_call_pm_ins_0005.py` (۴ تست)؛ pytest ۸۱۵ سبز؛ next build سبز؛ Playwright محلی `/settings?view=models` در ۱۳۶۰px: gpt-4o-mini با خطای ثبت‌شدهٔ ۴۰۱
  جعبهٔ قرمز و «API ✕» نشان داد، deepseek-chat «API ✓»، بقیه «کلید ✓ · آزموده نشده».
- **[TODO]** بند ۴: بازرس ویژه از رتبهٔ موفقیت می‌گیرد (`_smart_select_model`، و از PM-INS-0002 با cloud_code)؛ اتاق فرمان و دستیار هنوز سنجیده/هم‌سو نشده‌اند. علتِ
  «همهٔ ۲۲ خاموش» در production و ناهمخوانیِ ✅ های فهرستِ «مدل پیش‌فرض استخراج» هم هنوز بررسی نشده — دورِ بعد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest ۸۱۵ + next build + Playwright محلی

## 2026-11-15 (۲۷) — فوری PM-INS-0006: چتِ «بازرس ویژه» با یک مدلِ خراب از کار نمی‌افتد

- **[OWNER]** برگهٔ فوریِ PM-INS-0006 (تستِ ناظر ۲۲:۲۴ و ۲۲:۲۶ دبی): (۱) پیش از روشن‌کردنِ پاورِ پیش‌نمایش «ساختارمندسازی ناموفق: Failed to fetch» و «❌ ارتباط با
  سرور قطع شد»؛ (۲) با رادیوی «Local AI»، انتخابِ خودکار cloud_code را برداشت و 400 «Claude Code 1.0.110 does not support this model» گرفت؛ (۳) هیچ fallback
  به gemini-2.5-flash / deepseek-chat نبود («کار با ضعیف‌ترین مدل‌ها»)؛ (۴) سرِ چت «مدلی انتخاب نشده» و «⚠️ GitHub متصل نیست» با اینکه پروژه از GitHub سینک است؛
  (۵) «خطا در دسترسی GitHub» در واقع خطای مدل بود. پذیرش: «آخرین commit چیست؟» با پاورِ خاموش/روشن و هر دو موتور جوابِ درست، مدلِ بعدی وقتی یکی خطا داد، و نامِ
  مدلِ پاسخ‌دهنده.
- **[FINDING]** (۱) ۲۲:۲۴ دبی = ۱۸:۲۴Z، یک دقیقه پس از کامیتِ `2b3626d` (۱۸:۲۳:۳۰Z) — سرور وسطِ دیپلوی بود؛ چت به پاور وابسته نیست، ولی تلاشِ خودکار کورکورانه ۳ ثانیه
  بعد می‌زد و پیام می‌گفت «ارتباط قطع شد». (۲) `cloud_code_service` خود را `claude-cli/1.0.110` معرفی می‌کرد؛ تستِ توانایی با tier=opus می‌گذشت ولی مسیرِ بازرس
  (`min_tier=sonnet`/auto) مدلِ تازه‌تری می‌گرفت که این نسخه را نمی‌پذیرد. `_smart_select_model` در مسیرِ Local AI بین مدل‌های API و OAuth فرقی نمی‌گذاشت.
  (۳) هر خطای مدل در smart-chat پایانِ کار بود. (۴) بازرس فقط کلیدِ `api_key_github` را می‌خواند، سینکِ پروژه `github_token`/`GITHUB_TOKEN` را هم.
  (۵) فراخوانیِ مدل برای «انتخابِ فایل» داخلِ try ِ GitHub بود ⇒ هر خطای مدل «خطا در دسترسی GitHub» نام می‌گرفت. پرامپتِ سؤال هیچ تاریخچهٔ کامیتی نداشت.
- **[CHANGE]** `cloud_code_service`: نسخهٔ CLI از env `CLOUD_CODE_CLI_VERSION` (پیش‌فرض 2.1.0)؛ 400 ِ «does not support this model» ⇒ اگر نسخهٔ لازم را نام برد یک‌بار
  ارتقا و تکرار، وگرنه مدلِ بعدیِ فهرست (حداکثر ۳)، و مدلِ ردشده از picker کنار می‌رود؛ راهنمای فارسی. `render_logs`: `_FallbackAIManager` (پراکسیِ هر درخواستِ
  smart-chat — مدلِ خراب ⇒ gemini-2.5-flash، deepseek-chat، …، OAuth آخر؛ مدلِ کارا چسبنده؛ یادداشتِ «⚠️ مدل X خطا داد — با Y ادامه» در SSE؛ همه خراب ⇒
  `InspectorModelError`)؛ `_smart_select_model` اول فقط مدل‌های API، cloud_code فقط وقتی هیچ مدلِ API نیست (خواستهٔ PM-INS-0002 حفظ شد)؛ `_github_token_from_db`
  (هر سه کلید، ۱۷ جا)؛ برچسبِ «خطای مدل (نه GitHub)»؛ ۵ کامیتِ آخر (زنده از GitHub) در پرامپتِ سؤال. فرانت `projects/[id]`: «Failed to fetch» ⇒ پیامِ روشن
  «سرور پاسخ نداد (دیپلوی/بیدارشدن — ربطی به پاور ندارد)» و انتظار برای `/health` تا ۹۰ ثانیه پیش از ارسال/تلاشِ دوباره؛ موتورِ Cloud Code بی‌پاسخ ⇒ همان پیام
  خودکار با Local AI (`_forceLocal`) و نامِ مدلِ پاسخ‌دهنده زیرِ پاسخ.
- **[VERIFY]** `tests/test_inspector_model_fallback.py` (۵ تست: تشخیص و ارتقای نسخه، fallback و چسبندگی، خطای مدل)؛ pytest ۸۲۰ سبز؛ next build سبز. اجرای زنده با
  توکنِ واقعیِ Cloud Code در این محیط ممکن نبود — پس از دیپلوی باید سنجیده شود.
- **[TODO]** اگر پیامِ 400 نسخهٔ لازم را نام نبرد و 2.1.0 هم کم باشد، `CLOUD_CODE_CLI_VERSION` را روی Render بگذارید (تا آن موقع fallback جواب می‌دهد).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest ۸۲۰ + next build

## 2026-11-15 (۲۸) — فوری PM-INS-0008: «اجرای خودکار از خرداد اجرا نشده» در اتاق فرمان

- **[OWNER]** برگهٔ فوریِ PM-INS-0008 (بند ۸ اتاق فرمان): کارتِ هر ۹ پروژه «▶️ اجرای خودکارِ تسک‌ها هر 96 ساعت · آخرین: ۱۴۰۵/۳/۹ · بعدی: ۱۴۰۵/۳/۱۷» نشان
  می‌دهد با اینکه خودمختاری auto است و ۱۳۰۵ تسک باز است. خواسته: علت (زمان‌بند/worker/قفل) پیدا و رفع شود؛ «بعدی» ِ گذشته قرمز «عقب‌افتاده» با دکمهٔ «اجرای الان»؛
  «هیچ مدلی انتخاب نشده» در مدل‌های نظارت ⇒ پیش‌فرضِ خودکار (cloud_code یا deepseek-chat). پذیرش: «آخرین» تاریخِ امروز و نتیجه در گزارش‌ها.
- **[FINDING]** دادهٔ زندهٔ `/api/oversight/watched` (با توکنِ ناظر، فقط خواندن): هر ۹ پروژه `verify_only_mode=true`، `default_execution_mode=manual`، `next_run_at` همه
  ۲۰۲۶-۰۶-۰۷ ۰۷:۰۵. زمان‌بند (حلقهٔ ۶۰ ثانیه‌ای، لاگِ «Oversight scheduler loop started» در Render) سالم است؛ در بندِ ۳ ِ `_scheduler_tick_inner` پروژهٔ «فقط verify»
  عمداً `continue` می‌شود — پس اجرا نمی‌شود و `next_run_at` هم جلو نمی‌رود، ولی کارت همان خطِ «▶️ … بعدی» ِ کهنه را می‌نوشت. شبیه‌سازیِ محلیِ tick با پروژهٔ
  بدونِ verify-only، `next_run_at` را درست جلو برد. ۸ پروژه `selected_models=[]` داشتند.
- **[DECISION]** «فقط verify» تنظیمِ مالک است و خاموش‌کردنش یعنی اجرای خودکارِ تسک‌ها روی ۹ مخزن — **روی production عوض نشد**؛ تصمیمش با مالک (needs-owner).
- **[CHANGE]** `oversight_service`: `autorun_state` (schedule_off / not_auto / verify_only / overdue / running / ok + شمارِ تسک‌های آمادهٔ auto از pending)،
  `autorun_now` (یک دورِ اجرا در پس‌زمینه، «فقط verify» را رعایت می‌کند و دلیل را برمی‌گرداند؛ بدونِ تسکِ auto «آخرین» را جعل نمی‌کند)، `_default_watch_models`
  (default_models ِ مالک، وگرنه deepseek-chat، وگرنه cloud_code) در `list_watched.effective_models` و اسکنِ زمان‌بندی‌شدهٔ بی‌مدل. route ِ
  `POST /api/oversight/watched/{id}/autorun-now`. فرانت `oversight`: خطِ اجرای خودکار وضعیتِ واقعی را می‌گوید (کهربایی برای «فقط verify»، قرمز «⚠️ عقب‌افتاده»)،
  دکمهٔ «▶️ اجرای الان» با پیامِ سرور؛ «✨ پیش‌فرضِ خودکار: …» به‌جای «هیچ مدلی انتخاب نشده»؛ انتخابِ مدل‌های نظارت بی‌انتخاب ⇒ deepseek-chat/cloud_code (فقط محلی).
- **[VERIFY]** `tests/test_oversight_autorun_state_pm_ins_0008.py` (۳ تست)؛ pytest ۸۲۳ سبز؛ next build سبز. رندرِ زنده نشده.
- **[TODO]** مالک: برای اجرای خودکار، «فقط verify» را در کارتِ پروژه خاموش و حالتِ اجرای تسک‌ها را auto_via_* کند؛ بعد «اجرای الان».

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest ۸۲۳ + next build + خواندنِ دادهٔ زنده

## 2026-11-15 (۲۹) — فوری PM-INS-0012: «عامل» و «ضبط» ِ بازرس ویژه

- **[OWNER]** برگهٔ فوریِ PM-INS-0012 (وارسی ۰۱:۱۷ دبی، پاور روشن، نوارِ بالای اسکرین): (۱) «🖱 عامل» با Gemini 2.5 Flash و تیکِ «اول با Auth Recipe وارد شو»
  در گام ۲ ناموفق: «The website requires login, but the Google login is not configured» — عامل حتی واردِ خودِ AI Creator نمی‌شود؛ Recipe پیکربندی شود یا از نشستِ
  واردشدهٔ همین مرورگر استفاده کند، و اگر Recipe نیست پیش از شروع صریح بگوید. پذیرش: «از منو به آرشیو برو و تعداد گفت‌وگوها را بگو» با Gemini Flash و DeepSeek.
  (۲) «🎬 ضبط» با کلیکِ واقعی هیچ پنجره/نشانگری نشان نداد. (۳) بازشدنِ پنجرهٔ عامل در چت «🔴 لایه خطا شناسایی شد» ثبت کرد — false positive.
- **[FINDING]** (۱) `login_state_for` فقط Recipe ِ پروژهٔ هم‌میزبان را می‌شناسد؛ AI Creator ورودِ گوگل دارد و توکنِ جلسه را در `localStorage['pm.auth.token']` نگه می‌دارد؛
  مرورگرِ عامل جلسه نداشت، و چون `allowed_hosts` میزبانِ API را نداشت، فراخوانی‌های داده هم بسته می‌شد. بی‌Recipe چیزی گفته نمی‌شد.
  (۲) `openPicker` پیش از بازکردنِ پنجره منتظرِ مجوزِ میکروفون می‌ماند؛ و پنجره‌ها `fixed` داخلِ نوارِ اسکرین بودند (والدِ بریده/transform‌دار ⇒ نامرئی).
  (۳) تشخیص‌دهندهٔ «لایه خطا» هر لایهٔ fixed/absolute ِ بزرگ یا z>1000 (هر مودال) را خطا می‌شمرد.
- **[CHANGE]** `routes/browser_agent`: `use_session` — وقتی صفحهٔ شروع همان سایتِ درخواست‌دهنده است (هدرِ Origin) و Recipe نیست، توکنِ **خودِ** کاربر در
  `localStorage` ِ زمینهٔ یک‌بارمصرفِ مرورگرِ عامل گذاشته می‌شود (`_own_session_state`؛ هرگز برای سایتِ دیگر)؛ بی‌Recipe و بی‌جلسه ⇒ «⚠️ Auth Recipe نیست» پیش از شروع.
  `BrowserAgentPanel`: روی همین برنامه `use_session` و افزودنِ میزبانِ API به میزبان‌های مجاز. `InspectorRecordingPanel`: پنجره اول باز می‌شود (بررسیِ میکروفون
  بعد، با سقفِ ۱۵ ثانیه) و همهٔ پنجره‌ها/نوارِ «⏺ زمان + ⏹ پایان» با portal در `<body>`. پل‌های بازرس (`InspectorBridge.tsx` و سه نسخهٔ JS در `render_logs`):
  «لایه خطا» فقط وقتی لایه شبیهِ خطاست (overlay ِ خطای Next/Vite/webpack یا واژه‌های خطا).
- **[VERIFY]** `tests/test_browser_agent_own_session_pm_ins_0012.py` (۲ تست)؛ pytest ۸۲۵ سبز؛ next build سبز. اجرای واقعیِ عامل/ضبط در این محیط سنجیده نشد.
- **[TODO]** پذیرشِ زنده (آرشیو: ۱ گفت‌وگو، ۳ مناظره) با Gemini Flash و DeepSeek پس از دیپلوی؛ پروژه‌های دیگر هنوز Recipe ِ خودشان را لازم دارند.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-15 · pytest ۸۲۵ + next build

## 2026-11-16 (۳۰) — فوری PM-INS-0007: آرشیو (بند ۴) + بازرس ویژه (بند ۱۲a)

- **[OWNER]** برگهٔ فوریِ PM-INS-0007 (وارسی ۲۳:۰۵ دبی): آرشیو سیم‌کشیِ درستی دارد، ولی (۱) مناظرهٔ «نظرتون راجع به این اکسپرت چیه» دوبار با همان زمان
  ۱۴۰۴/۱۰/۱۴ ۱۵:۴۰:۴۰ آمده؛ (۲) «در چه زمینه هایی بهتر میتونید…» از ۱۴۰۴/۱۱/۱۲ هنوز «synthesizing» است؛ (۳) برچسب‌های وضعیت فارسی شوند. بازرس ویژه:
  (۴) «آخرین commit چیست؟» «درخواست اقدام» شد و با deepseek-chat در حالتِ عامل رفت (۵۱هزار توکن) در حالی که سرِ چت «Cloud Code» می‌گفت — نامِ مدلِ واقعی؛
  (۵) عامل گفت ابزارِ خواندنِ commit ندارد — `list_commits` بدهید. پذیرش: با یک سؤالِ ساده پاسخ با هشِ commit و نامِ مدلِ واقعی.
- **[FINDING]** (۱) `DebateService.list_sessions` هر فایل را جدا برمی‌گرداند؛ ساختِ دوباره (دوبار ارسال) دو شناسه با همان متن/ثانیه ساخته بود.
  (۲) کارِ پس‌زمینهٔ مناظره با ری‌استارتِ سرور می‌میرد و وضعیتِ میانی هرگز عوض نمی‌شد. (۳) `archive/page.tsx` مقدارِ خامِ enum را نشان می‌داد.
  (۴) طبقه‌بندِ LLM دستور دارد «در شک ⇒ ACTION»؛ مسیریابیِ فاز ۲ مدلِ نقشِ orchestrator (این‌جا deepseek-chat) را برمی‌دارد و پیامش «Claude» ِ ثابت بود؛
  سرِ چت در حالتِ خودکار فقط حدس می‌زد (اولین مدلِ روشن). (۵) `_build_tools` هیچ ابزارِ کامیتی نداشت (فقط مسیرِ QUESTION ۵ کامیت را در پرامپت می‌گذاشت).
- **[CHANGE]** `debate_service`: `list_sessions` بی‌تکرار بر پایهٔ (متن، ثانیهٔ ساخت) — آن‌که جلوتر رفته می‌ماند؛ **هیچ فایلی حذف نمی‌شود** و با شناسه در دسترس است.
  `_reconcile_stale`: وضعیتِ میانی (pending/running/scoring/judging/synthesizing/generating/summarizing) که >۲ ساعت دست نخورده ⇒ با نتیجه `completed`، بی‌نتیجه
  `failed`، با `metadata.stale_reconciled` و ذخیره روی دیسک. `archive/page.tsx`: `DEBATE_STATUS_FA` برای کارت، فیلتر و جزئیات.
  بازرس: `services/inspector_quick_classify.py` (پرسشِ کوتاهِ بی‌مشکل ⇒ QUESTION بی‌فراخوانیِ مدل؛ ریپلای همچنان با LLM)؛ ابزارِ `list_commits` در `inspector_agent`
  (+ `format_commits`) و در `cloud_code_executor`، و معرفی در پرامپتِ عامل؛ پیامِ «🧠 برای این کار از {مدل} (حالت عامل)» با نامِ واقعی؛ سرِ چت پس از پاسخ
  «✨ خودکار — پاسخِ آخر: <مدلِ واقعی>» (و در Cloud Code «موتور: Cloud Code · پاسخِ آخر: …»).
- **[VERIFY]** `tests/test_pm_ins_0007_archive_and_inspector.py` (۶ تست: طبقه‌بندِ سریع، ابزار در هر دو موتور، قالبِ کامیت، تکرار، گیرکرده/زنده)؛ pytest ۸۳۱ سبز؛
  next build سبز. دادهٔ واقعیِ آرشیو و پاسخِ زندهٔ بازرس در این محیط سنجیده نشد (دسترسی به سرورِ production نیست).
- **[TODO]** مالک پس از دیپلوی: در بازرس «آخرین commit چیست؟» بپرسد (باید «سؤال» باشد، با هش و نامِ مدل)؛ آرشیو را تازه کند.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest ۸۳۱ + next build

## 2026-11-16 (۳۱) — فوری PM-INS-0004: نمودارها — تکرار در فهرست + نمودار ذیلِ هر پروژه

- **[OWNER]** برگهٔ فوریِ PM-INS-0004 (بند ۳ و «نمودار ذیل هر پروژه»): (۱) در `/projects?view=diagrams` فهرستِ «پروژه» «Detective-1 · fullstack» را دوبار
  (اول و آخر) نشان می‌دهد — تکراری حذف شود؛ (۲) نمودارها ذیلِ هر پروژه هم دیده شوند — در صفحهٔ هر پروژه نمودارهای ذخیره‌شدهٔ همان پروژه و «رسم خودکار»،
  بدونِ حذفِ تبِ فعلی.
- **[FINDING]** دادهٔ زنده (`/api/diagrams/projects`): `local proj_fa454439 Detective-1 fullstack` و `github … mahdighandi1989/Detective-1 fullstack` —
  پروژهٔ محلی با `github_owner/github_repo` به همان مخزنِ تحت نظارت وصل است. نمودارها هیچ ذخیره‌گاهِ سمتِ سرور نداشتند (فقط `localStorage`).
- **[CHANGE]** `routes/diagrams.py`: `_local_repo_full_name` و ردکردنِ مخزنِ تحت نظارتی که پروژهٔ محلیِ وصل دارد (فیلدِ `repo` روی موردِ محلی)؛
  `GET/POST /api/diagrams/saved` (کلید `local:<id>`/`github:<id>`، فایلِ `DATABASE_DIR/diagrams_saved.json`، تکراری ذخیره نمی‌شود، سقفِ ۲۰۰ با ۴۰۹ — بی‌حذف).
  فرانت: `components/ProjectDiagramsPanel.tsx` (فهرستِ تاشوی نمودارهای ذخیره‌شده با رندرِ Mermaid، انتخابِ نوع، «🪄 رسم خودکار» ⇐ ذخیره)، تبِ تازهٔ
  «📈 نمودارها» در `/projects/[id]` (+ `?tab=diagrams`)؛ `DiagramsView` رسمِ خودکار را ذیلِ همان پروژه هم ذخیره می‌کند؛ `siteMap` به‌روز. هیچ تبی حذف نشد.
- **[VERIFY]** `tests/test_pm_ins_0004_project_diagrams.py` (۳ تست)؛ pytest ۸۳۴ سبز؛ next build سبز؛ پس از دیپلوی عکسِ فهرستِ پروژه و تبِ تازه از production.
- **[TODO]** —

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest ۸۳۴ + next build

## 2026-11-16 (۳۲) — PM-INS-0004 تکمیل: تبِ نمودارها روی صفحه‌های واقعیِ پروژه

- **[FINDING]** عکسِ production پس از d564727: `/projects/proj_fa454439` «پروژه پیدا نشد» — صفحهٔ `/projects/[id]` پروژه‌های `gh_…` (ورودِ GitHub) و `proj_…` ِ
  `project_service` را باز می‌کند، نه پروژه‌های `simple_creator` که فهرستِ نمودارها می‌شناسد. پس تبِ تازه با `source=local` برای این صفحه‌ها کلیدِ غلط داشت.
- **[CHANGE]** `diagrams._project_key`: هر مخزن یک کلید (`github:owner/repo`، کوچک‌حرف) — شناسهٔ «تحت نظارت»، `owner/repo` و پروژهٔ محلیِ وصل به مخزن همه به آن می‌رسند؛
  `_get_project_payload("local")` اگر در `simple_creator` نبود از `project_service` می‌خواند. صفحهٔ پروژه: `gh_…` ⇒ `source=github` با `owner/repo` از
  `metadata.source_url`، بقیه ⇒ `source=local` با شناسهٔ خودش.
- **[VERIFY]** `tests/test_pm_ins_0004_project_diagrams.py` ۵ تست؛ pytest و next build سبز؛ پس از دیپلوی عکس از `/projects/gh_mahdighandi1989_detective_1?tab=diagrams`.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build

## 2026-11-16 (۳۳) — فوری PM-INS-0009: نام‌گذاریِ کلیک/فوکوس در اسکرینِ بازرس

- **[OWNER]** برگهٔ فوریِ PM-INS-0009 (وارسی ۲۳:۳۶ دبی): پاور، Reload، تشخیصِ scan، سشن‌های آرشیو و ثبتِ کلیک ✓. ایرادها: (۱) کلیک روی منوی همبرگری داخلِ اسکرین
  «کلیک کردی روی  (pointerdown)» با متنِ خالی — دکمه‌های آیکونی از aria-label/title/selector نام بگیرند؛ (۲) بازشدنِ منوی کشویی «🔴 لایه خطا» شد (false positive)؛
  (۳) فوکوس‌ها «عنصر ناشناخته».
- **[FINDING]** (۱) `InspectorBridge.tsx`: `if (!(el instanceof HTMLElement)) return ""` — هدفِ کلیک روی آیکون یک `<svg>`/`<path>` است (Element، نه HTMLElement) ⇒ رشتهٔ خالی؛
  سه نسخهٔ JS در `render_logs` هم بی‌متن فقط تگ/کلاس می‌دادند. (۳) رویدادِ focus روی خودِ window (نه عنصر) ⇒ "" ⇒ «عنصر ناشناخته» در چت.
  (۲) پیش‌تر در 4c59a18 (۲۱:۳۷Z، دو ساعت پس از این برگه) رفع شده بود: «لایه خطا» فقط برای overlay ِ خطای واقعی یا متنِ خطا.
- **[CHANGE]** هر چهار پل: صعود با `closest(button,a,[role=button|menuitem|tab|switch],input,select,textarea,summary,label)` و نامِ دسترس‌پذیر
  (aria-label، title، alt، placeholder، name، aria-labelledby، `<title>`/alt/aria-label ِ درونی، data-testid) ⇒ «دکمه «باز کردن منو»»؛ فوکوس فقط برای Element.
  `Layout.tsx`: دکمه‌های باز/بستنِ منو `aria-label` و `title` گرفتند.
- **[VERIFY]** `tests/test_pm_ins_0009_bridge_names.py` (۳ تست)؛ `node --check` روی دو نسخهٔ JS و transpile ِ دو نسخهٔ TSX بی‌خطا؛ اجرای واقعیِ `getElementInfo` در Chromium:
  `path`/`svg`/`button` ⇒ «دکمه «باز کردن منو»»، title ⇒ «دکمه «بستن»»، window ⇒ "". pytest و next build سبز.
- **[TODO]** پلِ تزریق‌شده در مخزن‌های دیگر با «به‌روزرسانیِ پل» تازه می‌شود (خودکار نیست).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + Chromium

## 2026-11-16 (۳۴) — فوری PM-INS-0013: «هاب همهٔ پروژه‌ها» — نظارتِ هر پروژه، فیدِ رویداد، آزمایشی/قدیمی

- **[OWNER]** برگهٔ فوریِ PM-INS-0013 (وارسی ۰۱:۵۲ دبی): هر ۹ مخزن در /projects و اتاق فرمان ✓، «مرکز نظارت» نمانده ✓. کمبودها: (۱) برای هر پروژه تبِ «نظارت و
  سرکشیِ همان پروژه» با برگه‌های باز/فوری/پاسخ‌داده و زمانِ دورِ بعدیِ ناظرِ همان پروژه، زنده (اول فقط‌خواندنی)؛ (۲) هر ایجاد/تغییر/حذفِ فایل یا کامیت در هر ۹
  ریپو در یک «فیدِ رویدادِ همهٔ پروژه‌ها» (خانه یا اتاق فرمان)؛ (۳) پروژه‌های محلیِ «تست» (active 0%) و تکمیل‌شده‌های قدیمی برچسب «آزمایشی/قدیمی» یا آرشیو — حذف نه.
- **[FINDING]** برگه‌های هر پروژهٔ دیگر (Detective-1، ALLIN1، قرآن) در پایگاه‌دادهٔ سرورِ خودِ آن پروژه است، نه در git؛ از git فقط دستورهای نسخه‌دار، شاخه‌های
  `supervisor-pending/*` و کامیت‌های برگه‌ها خواندنی است. نشانی و توکنِ خواندنِ سرورهای دیگر در این برنامه نیست.
- **[DECISION]** تب دو لایه دارد: «برگه‌های زنده» (این برنامه از DB؛ پروژهٔ دیگر از سرورش فقط با `PROJECT_SUPERVISION_SOURCES` در Render، توکن در متغیرِ محیطی)
  و «ناظر در خودِ مخزن» (همیشه از GitHub). بی‌تنظیم، تب صریح می‌گوید چرا برگه‌ها خوانده نشد — چیزی ساختگی نشان نمی‌دهد. «آزمایشی/قدیمی» فقط نمایشی و برگشت‌پذیر.
- **[CHANGE]** `services/project_supervision.py` + `api/routes/project_supervision.py` (`GET /api/project-supervision/repos|board|feed`، پشتِ دیوارِ ورود، فقط خواندن،
  کشِ ۵ دقیقه‌ای GitHub)؛ `components/ProjectSupervisionPanel.tsx` و تبِ «🛡️ نظارت و سرکشی» در `/projects/[id]` (`?tab=supervision`)؛
  `components/ProjectsEventFeed.tsx` بالای `/oversight` (`#events-feed`)؛ `views/ProjectsView.tsx` برچسب «🗄️ آزمایشی/قدیمی» + دکمهٔ «نمایشِ آزمایشی/قدیمی (n)».
- **[VERIFY]** `tests/test_pm_ins_0013_project_supervision.py` (۶ تست)؛ pytest ۸۴۵ سبز، next build سبز، `check_frontend_api` ۰ نامنطبق. اجرای محلی: `board` برای همین
  مخزن از DB + نسخهٔ ۳ ِ دو دستور از GitHub؛ `feed` کامیت‌های واقعی با فایل‌ها؛ عکس از `#events-feed` و `/projects` («تست» پنهان، دکمهٔ (1)).
- **[TODO]** مالک: برای دیدنِ برگه‌های زندهٔ Detective-1/ALLIN1/قرآن، `PROJECT_SUPERVISION_SOURCES` و توکنِ خواندنِ هر کدام را در Render بگذارد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + Chromium

## 2026-11-16 (۳۵) — فوری PM-INS-0003: اتاق فرمان — وضعیتِ منفیِ گذرا، عددِ تبِ تسک‌ها، مدلِ پیش‌فرض

- **[OWNER]** برگهٔ فوریِ PM-INS-0003 (بندِ ۸ ِ طرح): (۱) هنگامِ باز شدن چند ثانیه «GitHub: توکن ندارد · Render: توکن ندارد · ۰ پروژه · ⚠️ توکن گیت‌هاب تنظیم نشده» —
  باید «در حال بارگذاری» باشد؛ (۲) تبِ «📋 تسک‌ها (0)» در حالی که کارت «۱۳۰۵ تسک فعال از ۱۹۲۰» می‌گوید؛ (۳) «هیچ مدلی انتخاب نشده» با ۱ مدلِ روشن — پیش‌فرضِ خودکار.
- **[FINDING]** (۱) `StatusCard` با `status === null` همان شاخهٔ «ناموفق» را می‌کشید و بنر شرطِ `!status?.github_token` داشت. (۲) عددِ تب `tasks.length` ِ فهرستِ
  کاملِ `/tasks?archived=all` بود (فعال+آرشیو) و وقتی آن درخواستِ سنگین نمی‌رسید ۰ می‌ماند — «نرسید» و «صفر است» یکی بودند. (۳) پیش‌فرضِ PM-INS-0008 فقط
  deepseek-chat یا cloud_code بود؛ مدلِ روشنِ دیگر، یا انتخابِ ذخیره‌شده‌ای که مدلش خاموش شده، به «هیچ مدلی» می‌رسید.
- **[CHANGE]** `frontend/src/app/oversight/page.tsx`: `StatusCard` حالتِ `loading`/`loadingText`؛ بنر فقط با وضعیتِ رسیده؛ `statusFailed` ⇒ «خوانده نشد — 🔄 بروزرسانی».
  `tasksLoad` (loading/ok/failed) و برچسبِ «تسک‌ها (N فعال از کل)» / «(در حال بارگذاری…)» / «(X فعال — فهرست بار نشد)» از عددِ سرور. انتخابِ مدل: اشتراکِ ذخیره با
  مدل‌های روشن؛ خالی ⇒ deepseek-chat ⇐ cloud_code ⇐ اولین مدلِ روشن.
- **[VERIFY]** next build سبز، pytest ۸۴۵ سبز. Chromium محلی با نگه‌داشتنِ پاسخِ `/status`: هر پنج کارت «در حال بارگذاری…»، بنری نیست، تب «تسک‌ها (در حال بارگذاری…)»؛
  پس از رسیدن: «تسک‌ها (0 فعال از 0)» (پایگاه‌دادهٔ محلیِ خالی). پیش‌فرضِ مدل محلی سنجیده نشد (محلی هیچ مدلِ روشنی نیست) — منطقش در کد خوانا است.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + Chromium

## 2026-11-16 (۳۶) — فوری PM-INS-0010: نشانِ سه‌حالتهٔ کلیدها در خانه، آمارِ زندهٔ راهنما، جزوهٔ همهٔ پروژه‌ها

- **[OWNER]** برگهٔ فوریِ PM-INS-0010 (بندهای ۹، ۱۰، ۱۱ ِ طرح — وارسی ۰۰:۱۰ دبی): خانه، راهنما و جزوه کار می‌کنند ✓. ریزه‌کاری‌ها: (۱) کارتِ «مدل‌های روشن ۴» می‌نویسد
  «کلیدِ openai، claude، gemini، deepseek، perplexity» در حالی که تستِ توانایی کلیدِ openai و claude را نامعتبر نشان داد — همان نشانِ سه‌حالتهٔ صفحهٔ مدل‌ها؛
  (۲) کادرِ «آمار» ِ دایرهٔ راهنما (تبِ نمای کلی) سه عددِ بی‌برچسب (۱۰، ۴، ۰) دارد که با خانه (۹ مخزن، ۴ مدل، ۱۳۰۵ تسک) نمی‌خواند — از همان دادهٔ زنده؛
  (۳) جزوه فقط مالِ project-management است — انتخابِ پروژه تا جزوه/دفتر کارِ هر مخزنِ تحتِ نظارت (مثلِ Detective-1/docs/HANDBOOK) هم خوانده شود.
- **[FINDING]** (۱) راهنمای کارت فقط `available` ِ `/api/settings/providers` (= کلید تنظیم شده) را فهرست می‌کرد؛ `last_call` ِ هر مدل (PM-INS-0005) را نمی‌دید.
  (۲) آن سه عدد شمارِ خودِ متنِ راهنما بودند (المان/قابلیت/نکته)، نه آمارِ برنامه. (۳) `repo_docs` فقط `SELF_REPO` را می‌خواند و برای فایلِ نیافته به نسخهٔ محلی برمی‌گشت.
- **[CHANGE]** `frontend/src/lib/liveStats.ts` (تازه): `useLiveStats` + `providerKeyStates` (آخرین فراخوانیِ واقعیِ هر provider ⇒ ok/failed/untested) — منبعِ واحدِ
  خانه و راهنما. `app/page.tsx`: چیپ‌های `openai ✕ · gemini ✓ · perplexity ?` زیرِ کارت (خطای واقعی در title)، کارت با کلیدِ شکست‌خورده قرمز.
  `components/help/HelpSystem.tsx`: «آمارِ زندهٔ برنامه» (مخزن/مدلِ روشن/تسکِ فعال/برگهٔ باز + کلیدها) و «آمارِ همین راهنما» با برچسبِ صریح.
  `services/repo_docs.py`: پارامترِ `repo_name` در `read_text|list_dir|commits_page` (شاخهٔ پیش‌فرضِ همان مخزن، کشِ جدا، بی‌بازگشت به محلی).
  `api/routes/handbook.py`: `GET /api/handbook/repos`؛ پارامترِ `repo` روی `docs|doc|search|export`، محدود به `project_supervision.watched_repos()` (غیرِ آن 404،
  نامِ بد 400)؛ کشفِ گسترده‌ترِ اسنادِ مخزنِ دیگر (ریشه، docs، docs/<پوشه>، experiences + CHANGELOG ِ همان مخزن؛ ACTIVITY فقط مالِ این برنامه).
  `app/handbook/page.tsx`: انتخابگرِ «📁 پروژه» (`?repo=`)، همهٔ پیوندها/جست‌وجو/خروجی با همان پروژه؛ مخزنی که HANDBOOK ندارد اولین سندش باز می‌شود.
- **[VERIFY]** `tests/test_pm_ins_0010_handbook_repos.py` (۴ تست: فهرستِ مخزن‌ها، کاتالوگ/سند/جست‌وجو/خروجیِ مخزنِ دیگر با GitHub ِ ساختگی، محدودیتِ فهرستِ پایش،
  بی‌بازگشت به محلی)؛ pytest ۸۴۹ سبز، next build سبز. Chromium محلی (پاسخِ مدل‌ها شبیه‌سازی‌شده): کارت «openai ✕ · claude ✕ · gemini ✓ · deepseek ✓ · perplexity ?»،
  راهنما «۱ مخزنِ تحتِ پایش · ۴ مدلِ روشن · …» برابر با خانه، انتخابگرِ پروژه با Detective-1. خواندنِ واقعیِ Detective-1 از GitHub در این محیط سنجیده نشد
  (GitHub از سندباکس 403 می‌دهد) — روی Render با توکنِ GitHub می‌خواند.
- **[TODO]** مالک: پس از دیپلوی `/handbook?repo=mahdighandi1989/Detective-1` را باز کنید؛ اگر مخزن خصوصی است، توکنِ GitHub ِ «اتاق فرمان» باید به آن دسترسی داشته باشد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + Chromium

## 2026-11-16 (۳۷) — فوری PM-INS-0011: مدل‌ها و تنظیمات — لاگ رندر، نشانِ کلیدها، ایمیلِ بی‌SMTP، مصرفِ یکپارچه

- **[OWNER]** برگهٔ فوریِ PM-INS-0011 (X9، وارسی ۰۰:۴۵ دبی، فقط مشاهده): زیرتب‌ها باز می‌شوند ✓. ایرادها: (۱) «📋 لاگ رندر» پس از ۱۵ ثانیه هنوز «در حال بارگذاری...»
  بی‌لاگ و بی‌خطا؛ (۲) «🤖 کلیدهای AI» برای OpenAI و Claude «✓ فعال» با وجودِ «Incorrect API key / invalid x-api-key» در تستِ توانایی — نشانِ سه‌حالته؛
  (۳) «🔔 نوتیفیکیشن»: Email «فعال» ولی «⚠️ SMTP credentials کامل نیست» — خودکار خاموش یا هشدارِ قرمز؛ (۴) «📊 مصرف AI»: امروز = ۷ روز = ۳۰ روز = 85.5K / 42
  و «آخرین درخواست: ۴ ساعت پیش» در حالی که بازرس ویژه ساعت ۲۲:۵۸ حدود ۵۱هزار توکن مصرف کرد — همه را یکپارچه ثبت کنید.
- **[FINDING]** (۱) بارگذاریِ اولیه منتظرِ `services/refresh` + `logs/fetch` از **همهٔ** سرویس‌ها پشتِ‌سرِهم بود و نشستِ aiohttp ِ Render timeout نداشت (پیش‌فرض ۳۰۰ ثانیه)؛
  شکست‌ها فقط `console.error` بودند؛ و فرانت `data.saved` را می‌خواند در حالی که مسیر `total_saved` برمی‌گرداند. (۲) نشان فقط «کلید هست» بود. (۳) فقط خطِ کهربایی.
  (۴) همهٔ مسیرها (بازرس، دستیار، اتاق فرمان، تستِ توانایی) از `ai_manager.generate` می‌گذرند، ولی فراخوانیِ **شکست‌خورده** و مسیرِ OAuth (cloud_code) هرگز ثبت
  نمی‌شد و `create_task` ِ ثبت ارجاع نداشت (ممکن است پیش از اجرا جمع‌آوری شود). «۴ ساعت پیش» = اختلافِ دبی (+۴): `created_at` UTC ِ بی‌منطقه است و مرورگر محلی می‌خواند.
  برابریِ امروز/۷/۳۰ روز یعنی ردیفی قدیمی‌تر از امروز در `ai_logs` نیست — این را در production نتوانستم بسنجم.
- **[CHANGE]** `RenderLogsPanel.tsx`: لاگ‌های DB فوراً (سقفِ ۱۵ ثانیه)، گرفتنِ تازه پس‌زمینه با نوارِ «در حالِ گرفتن…»، کادرِ قرمزِ ماندگارِ علت + «دوباره»، `total_saved`.
  `render_service.py`: `ClientTimeout(total=20, connect=8)`. `render_logs.py` `/logs/fetch`: سرویس‌ها موازی (Semaphore 6، هر کدام ۲۵ ثانیه، timeout = خطای همان سرویس).
  `SettingsView.tsx`: نشانِ هر کلید از `providerKeyStates` (✓ / ✕ با خطای واقعی در title / آزموده نشده / بی‌کلید). `NotificationSettingsPanel.tsx`: کانالِ روشنِ
  بی‌تنظیمات حلقهٔ قرمز + «⛔ روشن است ولی هیچ … فرستاده نمی‌شود» با نامِ متغیرها — کلید خودکار خاموش نمی‌شود (انتخابِ ذخیره‌شدهٔ مالک؛ با تنظیمِ SMTP خودش کار می‌کند).
  `ai_manager.py`: `_schedule_usage_log` (ارجاعِ task نگه داشته می‌شود)؛ ثبتِ فراخوانیِ شکست‌خورده (status=error، متنِ خطا) و هر دو مسیرِ OAuth.
  `ai_usage.py` `/summary`: زمان‌ها با `Z` + `first_request_at`؛ `AIUsagePanel.tsx`: زمانِ بی‌منطقه = UTC، «📅 قدیمی‌ترین ثبت» و توضیحِ برابریِ بازه‌ها.
- **[VERIFY]** `tests/test_pm_ins_0011_usage_and_settings.py` (۵ تست: ثبتِ موفق، ثبتِ شکست + raise، ثبتِ OAuth، `Z` در summary، سقفِ timeout ِ نشستِ Render)؛ pytest ۸۵۴ سبز،
  next build سبز، `check_frontend_api` ۰ نامنطبق. Chromium محلی: «لاگ رندر» در ۱٫۳ ثانیه کادرِ «لاگ از Render خوانده نشد: کلید API رندر یافت نشد» (محلی کلید نیست)؛
  کانالِ ایمیلِ روشن و بی‌SMTP (پاسخِ شبیه‌سازی‌شده) کادرِ قرمز. نشانِ کلیدها همان منطقِ سنجیده‌شدهٔ PM-INS-0010 است.
- **[TODO]** مالک: پس از دیپلوی «مصرف AI» را دوباره ببینید؛ اگر «قدیمی‌ترین ثبت» امروز است، ردیف‌های قدیمی‌تر در `ai_logs` نیستند (احتمالاً پایگاه‌داده تازه شده یا ثبت تازه آغاز شده).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + Chromium

## 2026-11-16 (۳۸) — فوری PM-INS-0012 (دورِ دوم): پذیرشِ زندهٔ «عامل» — ورود درست شد، ولی عدد «۰» بود؛ صبر تا رسیدنِ داده

- **[OWNER]** برگهٔ فوریِ PM-INS-0012 (بند ۱۲ «عامل» و «ضبط»): پذیرش = کارِ فقط‌خواندنیِ «از منو به آرشیو برو و تعدادِ گفت‌وگوها را بگو» با Gemini Flash و
  DeepSeek موفق شود و عددِ درست را بگوید. دورِ قبل (کامیت 4c59a18) `partial` بود چون زنده سنجیده نشده بود.
- **[FINDING]** سنجشِ زنده روی production با نشستِ ناظر (`/api/auth/supervisor-session` ⇒ bearer، Origin = فرانت، `use_session`، میزبانِ API مجاز — همان بدنه‌ای که
  `BrowserAgentPanel` می‌فرستد): هر دو مدل **وارد شدند** («🔑 با نشستِ واردشدهٔ خودِ شما … وارد شد») و `done` شدند، ولی هر دو گفتند «۰ گفت‌وگو، ۰ مناظره».
  دادهٔ واقعی (`/api/assistant/conversations` و `/api/debate/`): **۱ گفت‌وگو، ۲ مناظره** (نه ۳ — پس از یکی‌سازیِ مناظره‌های تکراری در PM-INS-0007). عکسِ گامِ آخرِ
  همان اجرا «۱ / ۲» را نشان می‌داد: کلیکِ منو مسیرِ سمتِ کاربر (Next) است و `/archive` داده را با fetch **بعد از** `domcontentloaded` می‌گیرد؛ عامل پیش از رسیدنِ
  داده مشاهده می‌کرد و صفرهای اولیهٔ کارت‌ها را می‌خواند. `wait_for_load_state("networkidle")` هم کمکی نمی‌کند (پس از ناوبریِ سمتِ کاربر فوراً برمی‌گردد).
- **[CHANGE]** `backend/app/services/browser_agent.py`: `_NetWatch` درخواست‌های در جریانِ صفحه را می‌شمارد (مسدودشده‌ها `requestfailed`)؛ `settle()` تا ۵۰۰ms سکوتِ
  شبکه صبر می‌کند، با سقفِ `BROWSER_AGENT_SETTLE_MS` (پیش‌فرض ۶ ثانیه، برای polling/stream) — پس از شروع و پس از هر کار جز `wait`.
  `frontend/src/app/archive/page.tsx`: کارت‌های آمار تا پایانِ بارگذاری «…» نشان می‌دهند، نه «۰» ِ گمراه‌کننده (برای عامل و برای انسان).
- **[VERIFY]** `tests/test_browser_agent_settle_pm_ins_0012.py` (۲ تست، Chromium ِ واقعی: صفحه‌ای که با کلیک pushState می‌کند و داده را ۱٫۵ ثانیه بعد می‌گیرد —
  بی‌تغییر قرمز «خالی»، با تغییر «گفت‌وگو: 1»؛ و سقفِ زمانِ settle وقتی شبکه آرام نمی‌شود). pytest ۸۵۶ سبز (۶ شکستِ `PIL._imaging` محیطیِ سندباکس بود، با نصبِ
  Pillow رفع؛ بی‌ربط به این تغییر)، next build سبز. پذیرشِ زنده **پس از دیپلوی** تکرار می‌شود؛ «🎬 ضبط» به کلیکِ واقعیِ مالک در مرورگر نیاز دارد (انتخاب‌گرِ اشتراکِ
  صفحه در Chromium ِ بی‌سر سنجیدنی نیست).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + اجرای زندهٔ عامل روی production
