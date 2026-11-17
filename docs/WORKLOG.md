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

## 2026-11-16 (۳۹) — فوری PM-INS-0014: سینکِ خودکارِ همهٔ پروژه‌های GitHub، بی‌سقفِ ۱۰۰ فایل، برچسبِ خصوصی از خودِ GitHub

- **[OWNER]** برگهٔ فوریِ PM-INS-0014 (G4/G6 «هاب همهٔ پروژه‌ها»): (۱) سینک خودکار نیست — قرآن پیش از کلیکِ دستی ۷ فایل داشت، بعد «99 فایل بروزرسانی شد · 102 فایل»؛
  برای هر ۹ مخزن سینک با هر کامیتِ main + «آخرین سینک: …» روی کارت + هشدارِ عقب‌افتادگی؛ (۲) برچسب پس از سینک از «🔒 خصوصی» به «🌐 عمومی» رفت؛ (۳) ۱۰۲ فایل
  مشکوک به سقف — «N از M» با دلیل؛ (۴) همین را برای بقیهٔ ۸ مخزن بسنجید. پذیرش: کامیتِ تازه بی‌کلیک ظرفِ چند دقیقه دیده شود؛ برچسب درست؛ تعداد برابر یا با توضیح.
- **[FINDING]** (۱) «سینک خودکار» فقط تیکی در `extra_data.sync_settings` بود؛ **هیچ کدی آن را اجرا نمی‌کرد**. (۳) `import_repository` سقفِ ثابتِ ۱۰۰ فایل (۳۳ بک‌اند/۳۳
  فرانت/۳۳ بقیه) داشت و بی‌صدا بقیه را دور می‌ریخت؛ فایلِ حذف‌شده در GitHub هم هرگز این‌جا حذف نمی‌شد. `save_imported_project` کلِ `extra_data` را بازنویسی می‌کرد
  (تنظیماتِ سینک و `cached_structure` پاک می‌شدند). (۲) برچسب همان `private` ِ پاسخِ `GET /repos/{o}/{r}` ِ GitHub است: پس از سینکِ ساعتِ ۱۴:۳۴ برای
  `quran-web-app-v1` (و `Detective-1`) مقدارِ `false` ذخیره شد — یعنی **خودِ GitHub این دو مخزن را عمومی گزارش کرده**؛ برچسبِ قبلی «خصوصی» از سینکِ قدیمی‌تر بود.
  (۴) سنجشِ production (فقط‌خواندنی، نشستِ ناظر) — فایل در AI Creator / فایل‌های فیلترشدهٔ درختِ ذخیره‌شده / آخرین سینک: detective_1 ۹۹/۱۱۹ (۶ ژوئن)،
  quran ۱۰۲/۳۸۸ (امروز)، lifemanager ۵۳/۵۳ (۲۰ مه)، detective ۱۰۰/۲۲۱ (۹ مه)، video_processor ۷/۷ (۳۰ مارس)، project_management ۱۱۳/۱۴۴ (۱۸ مه؛ مخزنِ واقعی
  ~۸۳۰ فایلِ متنی)، trading_system ۹۶/۱۴۴ (۲۱ مارس)، language ۱۶/۱۶ (۵ فوریه)، allin1 ۱۴۴/۱۵۵ (۲۰ فوریه، ۱۲ فایلِ دیگر دیگر در درخت نیستند).
- **[CHANGE]** `services/github_autosync.py` (تازه): حلقه هر ۳ دقیقه برای هر `github_import` آخرین کامیتِ شاخهٔ پیش‌فرض (`get_branch_head`) و `private` را از GitHub
  می‌خواند؛ کامیتِ تازه ⇒ سینکِ افزایشی (sha ِ بی‌تغییر ⇒ بی‌دانلود). `main.py` حلقه را بالا می‌آورد/می‌بندد. `services/github_import.py`: سقف ⇒ `GITHUB_IMPORT_MAX_FILES`
  (۱۵۰۰) + `GITHUB_IMPORT_MAX_BYTES` (۴۰ مگ)، فایل‌های مهم و کد اول؛ `sync_report` با شمارِ هر دلیلِ رد؛ درخت از همان sha ِ کامیت؛ حذف‌ها اعمال (فقط درختِ کامل و
  بی‌برش) و در `github_sync.history` با کامیت و فهرستِ افزوده/تغییر/حذف ثبت؛ `extra_data` ادغام می‌شود نه بازنویسی. `routes/github_import.py`: «🔄 سینک از GitHub» همان
  مسیر (`force`) و خروجیِ +/~/−، «N از M»؛ `POST /api/github/imported-sync-all` (پشتِ دیوارِ ورود). فرانت: `components/GithubSyncBadge.tsx` روی کارتِ `/projects` و
  سرِ `/projects/[id]` («آخرین سینک: … · N از M فایل (نیامده: …)»، قرمز اگر عقب/خطا)؛ کارتِ «فایل» «N از M» و «دسترسی (طبقِ GitHub)» با زمانِ بررسی.
- **[VERIFY]** `tests/test_github_autosync_pm_ins_0014.py` (۲ تست، GitHub ِ ساختگی): ۱۵۱ فایل بی‌سقف، `.png` با دلیل، بی‌کامیت ⇒ صفر دانلود، کامیتِ تازه ⇒ فقط ۲ فایلِ
  عوض‌شده دانلود + ۱ حذف + تاریخچه، `sync_settings` می‌ماند، `private` از GitHub؛ سقفِ تنظیم‌شده صریح گزارش می‌شود. pytest ۸۵۸ سبز، next build سبز.
  پذیرشِ زنده («کامیتِ تازه ظرفِ چند دقیقه») پس از دیپلوی سنجیدنی است — اولین دورِ حلقه ۶۰ ثانیه پس از بالا آمدن.
- **[TODO]** مالک: GitHub مخزن‌های `quran-web-app-v1` و `Detective-1` را **عمومی** گزارش می‌کند؛ اگر باید خصوصی باشند، در تنظیماتِ GitHub ِ همان مخزن عوضش کنید —
  برچسب این‌جا دورِ بعد خودش درست می‌شود. اولین سینکِ کاملِ ۹ مخزن پس از دیپلوی چند دقیقه طول می‌کشد (حدود ۲٬۰۰۰ فایل، یک‌بار).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + سنجشِ فقط‌خواندنیِ production

## 2026-11-16 (۴۰) — فوری PM-INS-0015 (امنیت): پیش‌نمایشِ «بازرس ویژه» دیگر هم‌origin ِ AI Creator نیست

- **[OWNER]** برگهٔ فوریِ PM-INS-0015: پیش‌نمایش از `/api/render/inspector/proxy/<id>/` روی همان origin ِ `ai-creator-frontend` اجرا می‌شود؛ در localStorage کلیدهای
  quran.* کنارِ `pm.auth.token` ⇒ هر JS ِ پروژهٔ پیش‌نمایش توکنِ مالک را می‌خواند. خواسته: origin ِ جدا (یا sandbox بی‌allow-same-origin)، توکن به کوکیِ HttpOnly، پاک‌کردنِ
  فقط quran.*. پذیرش: localStorage ِ AI Creator فقط کلیدهای خودش؛ از داخلِ iframe `window.parent.localStorage` در دسترس نباشد.
- **[FINDING]** درست است: Next همهٔ `/api/*` را به بک‌اند rewrite می‌کند، پس سندِ پروکسی هم‌origin ِ برنامه بود و iframe `sandbox="… allow-same-origin …"` داشت.
  آزمایشِ Chromium (سرورِ کوچکِ محلی): با CSP `sandbox` بی‌allow-same-origin، `window.parent.localStorage` ⇒ SecurityError ✓، ولی localStorage ِ خودِ سند هم
  SecurityError می‌دهد و فایل‌های JS ِ سند کوکیِ Strict/Lax را **نمی‌فرستند** (فقط `SameSite=None; Secure`) — پس بلیتِ پیش‌نمایش باید None شود و storage shim لازم است.
- **[CHANGE]** `routes/render_logs.py`: `PROXY_SANDBOX_CSP` روی همهٔ پاسخ‌های پروکسی (HTML، فایل‌ها، صفحهٔ خطا)؛ `_inject_storage_shim` اولین چیزِ `<head>`.
  `routes/auth.py` preview-ticket ⇒ `samesite: none`؛ `lib/previewTicket.ts` کوکی `samesite=none; secure` روی https. iframe در `projects/[id]/page.tsx` بی‌allow-same-origin
  (+ modals/downloads). `lib/auth.tsx`: `purgeForeignPreviewKeys` فقط `quran.*`. خواندن‌های مستقیمِ iframe (`contentDocument`) همه در try/catch بودند و نشانیِ صفحه با
  postMessage ِ اسکریپتِ پروکسی می‌آید — آن‌ها کار می‌کنند؛ تشخیصِ «صفحهٔ سفید» و عکسِ DOM ِ iframe دیگر ممکن نیست (عکس از مسیرِ سرور می‌رود).
- **[VERIFY]** `tests/test_preview_sandbox_pm_ins_0015.py` (۴ تست: CSP بی‌allow-same-origin روی HTML و فایل، shim پیش از اسکریپتِ صفحه، iframe/کوکی/پاک‌سازی)؛ آزمایشِ
  Chromium ِ محلی برای parent-LS=SecurityError، shim=ok و رسیدنِ کوکیِ None. pytest سبز، next build سبز.
- **[TODO]** انتقالِ `pm.auth.token` به کوکیِ HttpOnly انجام **نشد**: فرانت API را مستقیم روی origin ِ بک‌اند (`NEXT_PUBLIC_API_URL`) صدا می‌زند؛ کوکی آن‌جا شخصِ ثالث است و
  Chrome/Safari مسدودش می‌کنند. شرط: همهٔ فراخوانی‌ها از مسیرِ نسبیِ `/api` (rewrite ِ Next) بروند، بعد کوکیِ HttpOnly + محافظتِ CSRF. با sandbox، مسیرِ حمله‌ای که برگه گفت بسته است.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + آزمایشِ Chromium

## 2026-11-16 (۴۱) — فوری PM-INS-0016 (تکمیلِ ۱۴ با شاهد): file_count ِ ۰ و هشدارِ «بیش از ۱ روز»

- **[OWNER]** برگهٔ PM-INS-0016: «آخرین سینکِ» ۸ مخزن ۵ تا ۹ ماه پیش بود؛ `files/file_count` در `/api/github/imported` برای همه ۰؛ سینکِ خودکار برای هر ۹ مخزن + «آخرین سینک»
  روی کارت + هشدارِ قرمز اگر بیش از ۱ روز عقب است. مالک عمداً سینکِ دستی نزد تا کارِ خودکار سنجیده شود.
- **[FINDING]** سینکِ خودکار همان کارِ (۳۹) است و روی production کار می‌کند — بی‌هیچ کلیکی پس از دیپلوی: project_management ۸۳۵ از ۸۴۶، allin1 ۱۱۲۱ از ۱۱۴۸،
  trading_system ۱۱۰۳ از ۱۲۰۹، language ۴۸۵ از ۵۰۶، detective ۷۱۳ از ۷۴۳، video_processor ۲۶۹ از ۲۹۰ (سه مخزنِ دیگر در همان دورِ اول). `file_count` ِ فهرست از
  `Project.to_dict()` می‌آمد که فایل‌ها را نمی‌شمارد.
- **[CHANGE]** `routes/github_import.py` `GET /imported`: `file_count` با یک group-by روی `project_files`. `GithubSyncBadge.tsx`: قرمز «⚠️ بیش از ۱ روز بی‌بررسی» اگر
  `last_checked_at` کهنه‌تر از ۲۴ ساعت است (حلقه هر ۳ دقیقه بررسی می‌کند؛ کهنه‌بودن یعنی حلقه یا GitHub از کار افتاده).
- **[VERIFY]** تستِ `test_list_reports_real_file_count`؛ pytest و next build سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + سنجشِ زندهٔ production

## 2026-11-16 (۴۲) — PM-INS-0016 (ادامه): rate limit ِ GitHub در اولین سینکِ کامل؛ فایلِ دانلودنشده دیگر گم نمی‌شود

- **[FINDING]** اولین دورِ سینکِ کامل حدود ۴٬۵۰۰ فایل را یک‌جا گرفت و سقفِ ۵٬۰۰۰ درخواست در ساعتِ توکنِ GitHub پر شد (۱۶:۰۰ UTC: همه «دسترسی ممنوع - Rate limit»).
  quran، Detective-1 و Lifemanager پس از بازشدنِ سقف (کمتر از یک ساعت) سینک می‌شوند. ایرادِ واقعیِ پنهان: فایلی که دانلودش شکست می‌خورد sha ِ تازه را در درخت
  می‌گرفت و کامیت «سینک‌شده» ثبت می‌شد ⇒ آن فایل **هرگز** دوباره گرفته نمی‌شد.
- **[CHANGE]** `services/github_import.py`: `failed_paths`؛ sha ِ آن‌ها در درخت `None`؛ با هر دانلودِ شکست‌خورده `last_synced_sha` جلو نمی‌رود، `behind=true` و خطای
  «N فایل دانلود نشد — دورِ بعد دوباره» (نشانِ قرمز). دورِ بعد فقط همان‌ها گرفته می‌شوند.
- **[VERIFY]** `test_failed_downloads_are_retried_next_round` (۵۱ شکست ⇒ دورِ بعد دقیقاً ۵۱ دانلود ⇒ ۱۵۱ فایل، کامیت ثبت)؛ pytest و next build سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + سنجشِ زندهٔ production

## 2026-11-16 (۴۳) — فوری PM-INS-0017: تست Deploy با نتیجه، سربرگِ Detective-1، طبقه‌بندیِ سؤالِ ساده

- **[OWNER]** برگهٔ PM-INS-0017 (وارسیِ ۲۱:۰۰ دبی، `/projects/gh_mahdighandi1989_detective_1`): ✓ نمودارِ معماری، ✓ هشِ آخرین کامیت، ✓ Duplicates. ایرادها:
  (۱) «🧪 تست Deploy» هیچ پنجره/پیام/نتیجه‌ای نشان نمی‌دهد — باید نتیجهٔ تستِ اتصالِ Render (سرویس‌های پروژه، آخرین دیپلوی، خطا) را نشان دهد. (۲) سربرگ متنِ خامِ
  یک پرامپتِ بلند با علامت‌های markdown را نشان می‌دهد و در ۹۷۴px دکمه‌ها را له و یکی را بیرون می‌برد — خلاصه/یک‌خطی + «بیشتر». (۳) «هش آخرین commit چیست» باز
  «درخواست اقدام» شد و deepseek-chat (عامل) با ۱۸ هزار توکن جواب داد.
- **[FINDING]** (۱) دکمه `POST /deploy/test` را صدا می‌زد که در واقع `trigger_render_deploy` است — یعنی «تست» دیپلویِ واقعی راه می‌انداخت و نتیجه فقط یک toast ِ ۵ ثانیه‌ای بود.
  (۲) `project.description` خام در `<p>` و ردیفِ دکمه‌ها `flex` ِ بی‌wrap. (۳) پیش‌طبقه‌بندِ PM-INS-0007 درست کار می‌کند (`is_simple_info_question("هش آخرین commit چیست")`
  = True) ولی «ساختارمندسازیِ پرامپت» ِ فرانت پیش از ارسال متن را به یک پرامپتِ بلندِ چندخطی تبدیل می‌کند، پس سرور هرگز سؤالِ خام را نمی‌دید.
- **[CHANGE]** (۱) `routes/project_memory.py`: `GET /{id}/deploy/diagnose` (فقط‌خواندنی؛ کلید، سرویس‌های ذخیره‌شده یا هم‌نام/هم‌مخزن، آخرین دیپلوی/کامیت/خطای هر کدام).
  `projects/[id]/page.tsx`: دکمه پنجرهٔ «نتیجهٔ تست اتصالِ Render» را باز می‌کند؛ دیپلویِ واقعی (`testRenderDeploy`، بی‌تغییر) دکمهٔ «🚀 اجرای Deploy واقعی» در همان پنجره —
  چیزی حذف نشد. (۲) `summarizeDescription`: اولین خطِ معنادار (تیترها و «یادداشت برای مدل» رد)، بی‌markdown، ≤۱۶۰ نویسه؛ متنِ کامل در `<details>` «بیشتر»؛ سربرگ و دکمه‌ها
  `flex-wrap`. (۳) فرانت `original_message` (متنِ خام) را کنارِ پیامِ ساختارمند می‌فرستد؛ `render_logs._apply_quick_question_override` اگر خام سؤالِ ساده باشد (و ریپلای نباشد)
  همان را جایگزین می‌کند ⇒ QUESTION بی‌فراخوانیِ طبقه‌بند و بی‌سوئیچ به عامل.
- **[VERIFY]** `tests/test_pm_ins_0017_deploy_diag_and_quick_question.py` (۵ تست: سرویس‌ها + آخرین دیپلوی + خطا و **هیچ trigger_deploy**، بی‌کلید، سرویس‌های ذخیره‌شده، جایگزینیِ
  خام، دست‌نخوردنِ درخواستِ واقعی/ریپلای). pytest ۸۶۹ سبز، next build سبز. Playwright روی build ِ محلی در ۹۷۴px با API ِ ساختگی: `scrollWidth`=۹۷۴ (بی‌سرریز)، سربرگِ یک‌خطی +
  «بیشتر»، پنجرهٔ نتیجه با دو سرویس. روی production پس از دیپلوی سنجیده نشده.
- **[REVERT]** همین کامیت را revert کنید؛ endpoint ِ قدیمیِ `/deploy/test` دست‌نخورده است.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build + Playwright محلی

## 2026-11-16 (۴۴) — فوری PM-INS-0018 (بخشی): «🔍 تشخیص» از نشانیِ واقعیِ پیش‌نمایش؛ دکمه‌های تحلیل همیشه

- **[OWNER]** برگهٔ PM-INS-0018 (وارسیِ ۲۱:۳۰ دبی، بازرس ویژهٔ quran-web-app-v1): (۱) پیش‌نمایش روی `quran-web-app-8rwy.onrender.com` بالاست ولی «🔍 تشخیص» می‌گوید «URL
  پیش‌نمایش پروژه تنظیم نشده». (۲) خوداصلاحی خودکار نیست — حالتِ «🩹 خوداصلاح» (روشن/خاموش) که با هر خطای تازهٔ پیش‌نمایش خودکار تحلیل + پیشنهادِ diff بدهد و در چت
  ثبت کند؛ دکمه‌های «تحلیل خطاها / بررسی امنیت / یافتن باگ» پس از شروعِ چت پنهان‌اند. (۳) پیامی قدیمی در تاریخچه «مدل Claude: Claude 3.5 Sonnet» می‌گوید — نامِ مدلِ
  واقعی را از پیکربندی بخوانید.
- **[FINDING]** (۱) `GET /inspector/debug-bridge` فقط `project.deploy_url/preview_url` را می‌خواند که برای پروژه‌های GitHub خالی است؛ اسکرین نشانی را از
  `/api/render/services/by-project` می‌گیرد. (۲) دکمه‌های سریع داخلِ `inspectorChatMessages.length === 0` بودند. (۳) برچسبِ مدلِ پیام‌ها در UI از `model_id` ِ ذخیره‌شدهٔ
  همان پیام است (نه متن)؛ «Claude 3.5 Sonnet» درونِ **متنِ** پیامِ قدیمی است (خودمعرفیِ اشتباهِ مدل که پیش‌تر با system prompt مهار شد).
- **[CHANGE]** (۱) `render_logs._resolve_bridge_preview_url` + پارامترِ `preview_url` در debug-bridge؛ فرانت نشانیِ همان پیش‌نمایش را می‌فرستد. (۲) ردیفِ دکمه‌های سریع
  همیشه نمایان (sticky بالای چت). (۳) تاریخچهٔ تولیدی بازنویسی نشد (خطِ قرمز).
- **[VERIFY]** `tests/test_pm_ins_0018_bridge_preview_url.py` (۳ تست)؛ pytest و next build سبز.
- **[TODO]** حالتِ «🩹 خوداصلاح» (تشخیصِ خودکارِ خطای تازهٔ کنسول/لایهٔ خطا ⇒ تحلیل ⇒ پیشنهادِ diff ⇒ تأییدِ مالک) — کارِ بزرگ‌تری است و در این دور انجام **نشد**.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-16 · pytest + next build

## 2026-11-17 (۴۵) — فوری PM-INS-0018 (تکمیل): حالتِ «🩹 خوداصلاح» ِ بازرس ویژه

- **[OWNER]** همان برگهٔ PM-INS-0018، بندِ (۲) که در (۴۴) باز ماند: «خوداصلاحیِ دائمی» — حالتِ «🩹 خوداصلاح» (روشن/خاموش) که با هر خطای تازه در پیش‌نمایش
  خودکار تحلیل و پیشنهادِ اصلاح (diff) بدهد و در چت ثبت کند؛ اعمال با تأییدِ مالک یا برگهٔ فوری در «نظارت و سرکشی».
- **[FINDING]** زنجیرهٔ لازم تکه‌تکه بود: رویدادهای `error`/`console-error`/`error-overlay` در `handleBridgeEvent` به چت می‌رسیدند؛ تحلیل فقط دستی
  (`/inspector/investigate` با انتخابِ مدل) و `/inspector/analyze-error` diff نمی‌داد؛ اعمال از مسیرِ `/inspector/fix` (شاخه + PR) با پنجرهٔ انتخابِ مدل.
- **[CHANGE]** بک‌اند: `services/self_heal.py` (امضای پایدارِ خطا، پیدا کردنِ owner/repo، انتخابِ فایل‌ها از stack/نامِ فایل — نامِ ساخته‌شدهٔ هش‌دار هم —،
  پرامپت، خواندنِ تحمل‌پذیرِ JSON/بلوکِ diff) + `POST /api/render/inspector/self-heal/propose` در `render_logs.py` (فقط پیشنهاد؛ مدل = انتخابِ چت یا اولین مدلِ
  فعالِ فهرستِ بررسی). فرانت `projects/[id]/page.tsx`: کلیدِ «🩹 خوداصلاح» در ردیفِ دکمه‌های سریع (localStorage برای هر پروژه)؛ خطای تازه ⇒ `runSelfHeal`
  (یکی‌یکی، همان خطا ۱۰ دقیقه دوباره نه، ۱۵ لاگِ آخرِ کنسول + نشانیِ پیش‌نمایش) ⇒ پیامِ «پیشنهادِ اصلاح» با diff در چت و تاریخچهٔ سشن؛ دکمهٔ «✅ اعمال با تأیید»
  همان پنجرهٔ «🔧 اصلاح» را با گزارش و فایل‌ها پر می‌کند (تأیید ⇒ شاخه + PR، بی‌تأیید هیچ کامیتی)؛ «⚡ برگهٔ فوری» برگهٔ فوری روی بُردِ «نظارت و سرکشیِ» همین
  برنامه با `page=/projects/<id>` می‌سازد (بُردِ سرورِ خودِ پروژه‌های دیگر از این‌جا فقط‌خواندنی است و توکنِ نوشتن ندارد). چیزی حذف نشد.
- **[VERIFY]** `tests/test_pm_ins_0018_self_heal.py` (۶ تست: امضا، owner/repo، انتخابِ فایل از stack، پارسِ JSON و diff ِ خام، propose ِ بی‌شبکه بی‌اعمال، سیم‌کشیِ
  endpoint و فرانت). pytest ۸۷۸ سبز، `check_frontend_api` ۰ بی‌مسیر، next build سبز. روی production و با خطای واقعیِ پیش‌نمایش پس از دیپلوی سنجیده **نشده**.
- **[REVERT]** همین کامیت را revert کنید؛ مسیرهای قبلیِ بررسی/اصلاح دست‌نخورده‌اند.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + next build


## 2026-11-17 (۴۶) — ناظرِ خودکار، اجرای ۱۱: سنجشِ زندهٔ PM-INS-0018 + هشدارِ دیسک

- **[FINDING]** برگهٔ PM-INS-0018 پس از دیپلوی ِ 104b998 روی production سنجیده شد: «🔍 تشخیص» با `preview_url` واقعی ⇒ `deployed_has_bridge: true`؛ کلیدِ «🩹 خوداصلاح» و
  دکمه‌های سریع بالای چتِ پُر دیده شد؛ `self-heal/propose` با خطای آزمایشی فایل‌ها را از GitHub خواند و بی‌شاهد diff نساخت (`confidence: low`).
- **[FINDING]** دیسکِ بک‌اند ۸۰٫۴٪ پر (۱۸۳ مگابایت آزاد؛ DB ۴۸۱ مگابایت، `tasks.json` ۱۲۷ مگابایت) ⇒ `docs/supervisor/OPEN_ITEMS.md` #۶.
- **[FINDING]** کاهشِ منو (۱۱⇒۹) و دکمه‌های صفحه (۴۶۷⇒۴۳۴) در `inventory.py` از ادغامِ صفحه‌ها (ViewHub) است، نه حذفِ قابلیت؛ هیچ مسیرِ API کم نشده.
- **[DECISION]** دادهٔ production حذف یا بایگانی نشد (خطِ قرمز)؛ تصمیمِ دیسک با مالک.
- **[CHANGE]** فقط مستندات: RUNLOG (اجرای ۱۱)، OPEN_ITEMS (#۶)، runs.jsonl، INVENTORY؛ جوابِ برگهٔ ۱۸ (`fixed` با عکس). کدِ محصول دست نخورد.
- **[VERIFY]** pytest ۸۷۸ قبول / ۴ skip؛ next build سبز.
- **[REVERT]** همین کامیت را revert کنید (فقط مستندات).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + next build


## 2026-11-17 (۴۷) — فوری PM-INS-0019: Bridge ِ پیش‌نمایش، دکمه‌های گیج‌کننده، طوفانِ درخواست، هویتِ مدل

- **[OWNER]** برگهٔ فوریِ PM-INS-0019 (بند ۱۲، پروژهٔ quran-web-app-v1)، هشت بند: ۱) Bridge هرگز وصل نمی‌شود؛ ۲) «نسخه قدیمی v1.0» در حالی که پروکسی v2.4 دارد؛
  ۳) برچسب‌های وضعیت که کارِ معکوس می‌کنند + تأییدِ پیش از commit در ریپوی پروژه + راهنما؛ ۴) ورود در پیش‌نمایش (sandbox بی‌allow-same-origin) و اندازهٔ کوچک؛
  ۵) ۸۸ درخواستِ `executions/active` در ۲۰ ثانیه؛ ۶) مدل خودش را «Claude 3.5 Sonnet» می‌نامد؛ ۷) مثبتِ کاذبِ تأیید و پاسخِ انگلیسیِ عامل؛ ۸) ضبط پس از رفعِ ۱.
- **[FINDING]** ۱) `str.replace("__BRIDGE_WS_URL__", url)` همهٔ رخدادها را عوض می‌کند، از جمله نگهبانِ `WS_URL === '__BRIDGE_WS_URL__'` ⇒ `WS_URL === '<url>'` همیشه
  درست ⇒ `return` پیش از `new WebSocket` در هر سه قالب (HTML، JS، کامپوننتِ Next). جدا از آن، بازرسی که بعد از Bridge وصل شود `peer_connected` نمی‌گرفت.
  ۲) regex ِ نسخه فقط `// Version:` را می‌خواند؛ قالبِ HTML `<!-- Version: 2.4 -->` دارد ⇒ «1.0» ⇒ و «آپدیتِ خودکار» در هر بررسیِ وضعیت بی‌خبر commit می‌کرد.
  ۵) در `ExecutingPromptsPanel` تابعِ fetch به `previousExecutions` وابسته بود که هر fetch عوضش می‌کرد ⇒ effect دوباره ⇒ fetch ِ فوری (حلقه به سرعتِ شبکه).
  ۷) `<button>` ِ بی‌type خارج از فرم هم `type==='submit'` گزارش می‌شود ⇒ تبِ ناوبری «ارسال» شمرده می‌شد.
- **[CHANGE]** بک‌اند `render_logs.py`: نگهبانِ قالب‌ها `!/^wss?:[/][/]/.test(WS_URL)`، `INSPECTOR_BRIDGE_VERSION` ۲٫۵، regex ِ نسخه `(?://|<!--)`، دلیلِ تازهٔ
  needs_update برای نگهبانِ خراب، `_heal_bridge_self_guard` در پاسخِ HTML و JS ِ پروکسی (فقط literal ِ مقایسه را `__unset__` می‌کند)، `peers` در پیامِ `registered`.
  `cloud_code_service._build_system_blocks(…, model)` یک بلوکِ «هویتِ مدل» با شناسهٔ واقعی (پس از پرامپتِ کاربر). `browser_agent.py`: `submits` فقط با فرمِ واقعی؛
  قاعدهٔ زبانِ فارسی در SYSTEM. فرانت `projects/[id]/page.tsx`: `peers>0` ⇒ متصل؛ «آپدیتِ خودکار» قرنطینه (پرچمِ `BRIDGE_AUTO_UPDATE_QUARANTINED`، کدِ قبلی سرِ جا،
  فقط پیام)؛ `confirm` با نامِ فایل برای نصب/حذف/آپدیت؛ برچسبِ وضعیت جدا از دکمهٔ عمل برای «رصد لاگ» و «Bridge» + `<details>` راهنما؛ ⛶ تمام‌صفحه (Esc) و ↗ پنجرهٔ جدا.
  `ExecutingPromptsPanel`: ref + یک تایمرِ خودزمان‌بند (≥۵ ثانیه، backoff ۱۰/۳۰، توقف در تبِ پنهان)؛ `PromptManager` ۳⇒۶ ثانیه و توقف در تبِ پنهان. چیزی حذف نشد.
- **[DECISION]** بند ۴: پیش‌نمایشِ داخلی sandbox ِ بی‌allow-same-origin می‌ماند (امنیتِ PM-INS-0015)؛ راهِ امنِ ورود = پنجرهٔ جدا روی origin ِ خودِ سایت (Bridge ِ ترمیم‌شده
  از آن‌جا هم به چت وصل می‌شود). زیردامنهٔ جدا برای پیش‌نمایش نیازمندِ DNS/سرویسِ تازه است ⇒ با مالک.
- **[VERIFY]** `tests/test_pm_ins_0019_bridge.py` (۵ تست). pytest ۸۸۳ سبز / ۴ skip؛ next build سبز. روی production با مرورگرِ واقعی (پشتِ ورودِ گوگل) سنجیده **نشده**؛
  بندِ ۸ (ضبط) و شمارشِ درخواست‌ها پس از دیپلوی باید زنده سنجیده شود. Bridge ِ ریپوی quran-web-app-v1 هنوز ۲٫۴ است: پروکسی ترمیمش می‌کند، ولی پنجرهٔ جدا تا آپدیت (با دکمه و تأییدِ مالک) وصل نمی‌شود.
- **[TODO]** پس از دیپلوی: «WS: متصل» در پیش‌نمایش، شمارِ `executions/active` در ۲۰ ثانیه (انتظار ≤۴)، و یک ضبطِ کوتاه با لاگِ کلیک.
- **[REVERT]** همین کامیت را revert کنید.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + next build

## 2026-11-17 (۴۸) — فوری PM-INS-0021: Bridge ِ قرآن در بیلدِ production خاموش بود — پیش‌نمایش روشنش می‌کند

- **[OWNER]** (هماهنگ‌کننده، ۱۰:۴۰ دبی) پس از a1e02e5 هنوز «WS: منتظر Bridge»؛ ریشهٔ دوم: اسکریپتِ ۲٫۴ ِ قرآن با `if ('%VITE_ENABLE_INSPECTOR_BRIDGE%' !== 'true') return;`
  شروع می‌شود و WS_URL فقط از `window.__INSPECTOR_WS_URL__` می‌آید. خواسته: پروکسی نگهبان را خنثی و نشانی را پیش از اسکریپت ست کند (بی‌کامیت در ریپوی قرآن)، «🔍 تشخیص» همین را بگوید، بررسیِ هر ۹ پروژه.
- **[FINDING]** HTML ِ واقعیِ https://quran-web-app-8rwy.onrender.com (۳۷٬۵۲۸ بایت) خطِ ۱۸۶ همان نگهبان را دارد (توکنِ Vite جایگزین نشده) و خطِ ۲۰۷ `WS_URL = window.__INSPECTOR_WS_URL__ || ''`.
  بررسیِ ۹ پروژه (HTML ِ زندهٔ فرانتِ هر کدام): Bridge دارند ۳ — quran v2.4 (خاموش در بیلد، نشانی از window)، video-processor v2.4 و trading-system v2.2 (نشانیِ ثابتِ wss)؛ بی Bridge ۶ —
  project-management، language، detective، ALLIN1، Lifemanager (نشانیِ فرانت در اتاق فرمان ثبت نیست؛ با نشانیِ Render سنجیده شد)، Detective-1.
- **[CHANGE]** `render_logs.py`: `analyze_bridge_html` (حضور، نسخه، خاموشی در بیلد، منبعِ نشانیِ WS)؛ `_enable_project_bridge` در پروکسیِ پیش‌نمایش (فقط نمای مالک؛ سایتِ عمومی و ریپو دست نمی‌خورند):
  `'%VITE_ENABLE_INSPECTOR_BRIDGE%'` ⇐ `'true'` و `window.__INSPECTOR_WS_URL__` اولِ `<head>`؛ «🔍 تشخیص» (`debug-bridge`) حالا «⚠️ Bridge در بیلدِ production خاموش است (VITE_ENABLE_INSPECTOR_BRIDGE)…» می‌گوید
  نه «✅ اسکریپت موجود است»؛ `GET /api/render/inspector/bridge-survey` (همین بررسی برای همهٔ پروژه‌های تحتِ پایش).
- **[VERIFY]** `tests/test_pm_ins_0021_bridge_build_guard.py` (۴ تست روی HTML ِ واقعیِ قرآن به‌عنوانِ fixture). سنجشِ زنده پس از دیپلوی در همین برگه.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + HTML ِ زندهٔ ۹ پروژه

## 2026-11-17 (۴۹) — PM-INS-0021 (ادامه): برنامهٔ قرآن در پیش‌نمایش سفید بود — ماژول‌ها بی‌کوکی ۴۰۱ می‌گرفتند؛ + PM-INS-0020 بندِ ۲ (دستیار)

- **[VERIFY]** سنجشِ زندهٔ (۴۸) روی production (مرورگرِ ناظر، bc21f80d): «WS: متصل» پس از ۵٫۱ و بارِ دوم ۱٫۰ ثانیه؛ زنجیرهٔ کنسول: Bridge اجرا ⇐ WebSocket connected ⇐ registered as bridge ⇐ peer connected؛
  کلیکِ داخلِ پیش‌نمایش در چت: «کلیک کردی روی html (pointerdown)».
- **[FINDING]** خودِ برنامهٔ قرآن در پیش‌نمایش سفید است (متنِ body ۰): `assets/index-CjLBx5Le.js` ⇐ **۴۰۱**. پیش‌نمایش از PM-INS-0015 در sandbox (مبدأِ opaque) است و اسکریپتِ ماژول
  (`type="module" crossorigin`، همهٔ اپ‌های Vite) بی‌کوکی درخواست می‌شود، پس بلیتِ پیش‌نمایش نمی‌رسید.
- **[CHANGE]** `core/auth.preview_allowed`: بلیتِ امضاشده و محدود به همان پروژه در مسیر هم پذیرفته می‌شود (`/proxy/<پروژه>/~pt~<بلیت>/…`)؛ پروکسی بلیت را از مسیر برمی‌دارد، نشانی‌های
  دارایی‌های صفحه را با آن بازنویسی می‌کند (importهای نسبی آن را نگه می‌دارند) و به پاسخِ دارایی‌ها `Access-Control-Allow-Origin: *` می‌دهد (فایل‌های عمومیِ فرانتِ پروژه، بی‌اعتبارنامه).
- **[CHANGE]** PM-INS-0020 بندِ ۲: `assistant._live_counts` — «برگه‌ها» (نظارت و سرکشی) و «تسک‌ها» (اتاق فرمان) با برچسبِ جدا؛ کل و شمارش به همان برچسب‌های صفحه («در انتظارِ ناظر»…)؛
  ۵ برگهٔ آخر با شماره و زمانِ دبی؛ در دستورِ سیستمی: عددِ یکی را برای دیگری نگو، «آخرین برگه» = بزرگ‌ترین شماره.
- **[VERIFY]** +۲ تست (بلیت در مسیر فقط همان پروژه/GET؛ پروکسی)؛ pytest ۸۸۹ سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۵۰) — فوری PM-INS-0020: کلیدها از نتیجهٔ واقعی، ✅ ِ درست، زمانِ محلی، و خلاصهٔ یک‌صفحه‌ایِ اتاق فرمان

- **[OWNER]** (هماهنگ‌کننده، ۰۹:۴۸ دبی) بندِ ۶: (الف) پنجرهٔ نتیجهٔ Gemini Pro پس از ۴۵ ثانیه باز نشد، (ب) «کلید ✓ · آزموده نشده» با وجودِ تستِ موفق، (ج) GPT-4o با ✅ با کلیدِ خراب،
  (د) زمان‌ها UTC؛ بندِ ۱۳: خلاصهٔ یک‌صفحه‌ای + پاک‌سازیِ امنِ تکراری/کهنه با پیش‌نمایش و تأیید، بی حذفِ خودکار.
- **[FINDING]** دادهٔ production درست بود (DeepSeek/Gemini Pro/Flash/Cloud Code ⇐ `last_call.ok=True` ِ امروز)؛ تبِ «کلیدهای AI» فقط هنگامِ باز شدنِ صفحه می‌خواند و پس از تست تازه نمی‌شد؛
  مصرفِ واقعی (عامل، چت) هم ثبت نمی‌شد. فهرستِ «مدل پیش‌فرض برای استخراج فایل» ✅ را از رجیستری می‌داد، نه از تنظیمات و کلید. `tested_at`/`last_call.at` بی‌منطقهٔ زمانی ذخیره می‌شد.
- **[CHANGE]** `ModelsView`: نوارِ «⏳ در حالِ تستِ …» در طولِ تست؛ پنجرهٔ نتیجه همیشه باز می‌شود؛ پاسخِ نرسیده ⇒ پیامِ روشن و تازه‌سازیِ خودکار پس از ۲۰ ثانیه؛ رویدادِ `models:tested`.
  `SettingsView`: با آن رویداد و با بازگشت به تب دوباره می‌خواند. `ai_manager._schedule_usage_log`: هر فراخوانیِ موفقِ واقعی `last_call` (source=real_use، حداکثر ۱ بار در ۱۰ دقیقه برای هر مدل).
  `GET /oversight/models/extraction-default`: `enabled` از تنظیمات + `key_state` (ok/failed/untested/no_key) از تازه‌ترین فراخوانیِ واقعیِ همان provider؛ ✅ فقط روشن + کلیدِ سالم (⚠️/🔑✕/❔ در غیرِ این صورت).
  زمان‌ها: ذخیره با `+00:00`؛ `lib/time.ts` (`localTime`) مقدارِ بی‌منطقه را UTC می‌خواند و به ساعتِ مرورگر (دبی) نشان می‌دهد.
- **[CHANGE]** بندِ ۱۳: `services/oversight_summary.py` + `GET /oversight/summary`، `GET /summary/cleanup-preview`، `POST /summary/cleanup` (فقط با `confirm=true`؛ بایگانی با `owner_cleanup_duplicate`
  + `merged_into` / `owner_cleanup_stale` — هیچ حذفی)؛ `components/OversightSummary.tsx` بالای /oversight: خودکار/خاموش و چرا برای هر پروژه، ۱۰ تسکِ مهم، پیش‌نمایشِ تیک‌دار و تأیید.
- **[VERIFY]** `tests/test_pm_ins_0020_summary.py` (۴)؛ pytest و build در ship؛ سنجشِ زنده در همان برگه.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + next build

## 2026-11-17 (۵۱) — سنجشِ زندهٔ PM-INS-0020 و PM-INS-0021 روی production و جواب در برگه‌ها

- **[VERIFY]** PM-INS-0021 (مرورگرِ ناظر، c0d9b16): «WS: متصل» quran ۴٫۶ ث (اجراهای دیگر ۱٫۰ و ۵٫۱)، video-processor ۵٫۶، trading-system ۴٫۶؛ اپِ قرآن در پیش‌نمایش رندر شد (۵۲۱ نویسه، پیش‌تر ۰ و ۴۰۱ روی
  `assets/index-CjLBx5Le.js`)؛ کلیک در چت: «کلیک کردی روی دکمه "تمرین" (pointerdown)»؛ «🔍 تشخیص»: «⚠️ Bridge در بیلدِ production ِ پروژه خاموش است (VITE_ENABLE_INSPECTOR_BRIDGE…)»؛
  `bridge-survey` روی production: ۳ با Bridge، ۵ بی Bridge، Lifemanager بی نشانیِ فرانت. جواب: fixed + تصویر.
- **[VERIFY]** PM-INS-0020 (9a26974): دستیار با همان پرسش ⇐ «PM-INS-0021 … ۱۰:۳۳ دبی؛ در انتظارِ ناظر ۱» (واقعی: بیشینه ۲۱، open=1)؛ تبِ کلیدها: OpenAI ✕، Claude ✕، Gemini ✓، DeepSeek ✓،
  Perplexity آزموده‌نشده (درست)؛ استخراج: GPT-4o off/failed؛ تستِ Gemini Pro: نوارِ «در حالِ تست» و پنجرهٔ نتیجه پس از ۱۰۹ ثانیه؛ `last_call.at` با `+00:00`؛
  خلاصه: ۹ مخزن، ۱٬۳۷۹ باز (۱٬۲۲۱ پیشنهاد، ۱۱۴ در انتظار، ۴۴ منتظرِ بازبینی)، ۶۱۵ بایگانی، ۳٬۰۵۸ گزارش، ۴ مدلِ روشن؛ پاک‌سازی: ۸ تکراری در ۴ گروه، ۸۴۳ کهنه — پیش‌نمایش باز شد، تأیید نزدم.
  جواب: fixed + تصویر.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی + API روی production

## 2026-11-17 (۵۲) — فوری PM-INS-0022: Bridge برای همهٔ پروژه‌ها در پیش‌نمایش

- **[OWNER]** (هماهنگ‌کننده، ۱۳:۵۸ دبی) PM-INS-0020 و 0021 تأیید شد. حالا: Bridge و لاگ در چت برای همهٔ پروژه‌ها — در پاسخِ پروکسیِ پیش‌نمایشِ detective_1، language، allin1، lifemanager، project_management
  هیچ Bridge ای نیست؛ Detective-1 ۴۶ ثانیه «منتظر Bridge». پروکسی Bridge ِ ۲٫۵ را فقط در پاسخِ پیش‌نمایش تزریق کند (بی‌کامیت)؛ «🔍 تشخیص» منبع را بگوید؛ اپ‌های فرانت/بک‌اندِ جدا کامل باز شوند.
- **[CHANGE]** `render_logs._inject_preview_bridge`: صفحه‌ای که Bridge ندارد (`analyze_bridge_html`) قالبِ فعلیِ `INSPECTOR_BRIDGE_SCRIPT` را با نشانیِ هابِ همان پروژه پیش از `</body>` می‌گیرد، با نشانهٔ
  «injected by the preview proxy»؛ صفحه‌ای که خودش Bridge دارد دست نمی‌خورد. `debug-bridge`: `bridge_source` (repo / preview_injection) و پیامِ «ℹ️ Bridge در ریپوی این پروژه نیست — پیش‌نمایش … تزریق می‌کند».
- **[VERIFY]** `tests/test_pm_ins_0022_preview_bridge.py` (۳). سنجشِ زنده در برگه.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest

## 2026-11-17 (۵۳) — PM-INS-0022 (ادامه): اپ‌های Next.js در پیش‌نمایش، کلیک روی SVG، fetch ِ صفحه با بلیت

- **[VERIFY]** پس از e48848a: پاسخِ پروکسیِ ۵ پروژه (detective_1، language، allin1، lifemanager، project_management) همه Bridge ِ تزریق‌شده دارند؛ «WS: متصل»: Detective-1 ۶٫۱ ث، language ۶٫۶، ALLIN1 ۵٫۶.
- **[FINDING]** (۱) Detective-1 و ALLIN1 (Next.js) سیاه/خالی: chunk ها و CSS از مسیرِ مطلقِ `/_next/static/…` ⇐ `/_next` ِ خودِ AI Creator (اپِ اشتباه) ⇒ ChunkLoadError و ERR_BLOCKED_BY_ORB.
  (۲) language: کلیک روی آیکنِ SVG ⇐ `TypeError: el.className.split is not a function` در قالبِ Bridge ⇒ کلیک به چت نمی‌رسید. (۳) fetch/XHR ِ مطلقِ خودِ صفحه از پروکسی بی بلیت ⇒ ۴۰۱.
- **[CHANGE]** `render_logs._rewrite_next_paths` (HTML و پاسخ‌های JS/CSS ِ پروکسی: `"/_next/`، `'/_next/`، `\"/_next/`، `url(/_next/` ⇐ مسیرِ پروکسیِ همان پروژه با بلیت)؛ قالبِ Bridge: className ِ غیرِرشته‌ای (SVG)؛
  اسکریپتِ رصدِ پروکسی fetch/XHR ِ مطلق را به مسیرِ بلیت‌دار می‌برد. محدودیتِ آگاهانه: پروکسی فقط GET است (نوشتن روی بک‌اندِ پروژه‌ها از پیش‌نمایش نه)؛ ورودِ گوگلِ خودِ اپ‌ها در پیش‌نمایش ممکن نیست.
- **[VERIFY]** +۳ تست؛ pytest ۸۹۹ سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۵۴) — PM-INS-0022 (ادامه): ناوبریِ سمتِ کاربرِ Next.js داخلِ پیش‌نمایش می‌ماند

- **[VERIFY]** پس از af2170f: Detective-1 و ALLIN1 بالا می‌آیند (متن ۰ ⇐ ۱۰۰ نویسه)؛ language کلیک روی SVG را ثبت کرد («کلیک کردی روی path»)؛ WS: ۶٫۶ / ۵٫۶ / ۵٫۱ ث.
- **[FINDING]** نگهبانِ ورودِ خودِ Detective-1 و ALLIN1 به `/login` می‌رود: درخواستِ RSC ِ Next با شیءِ URL ِ مطلق ساخته می‌شود (رهگیر فقط رشتهٔ «/…» را می‌گرفت) و پروکسی هدرهای RSC را نمی‌فرستاد
  ⇒ بازگشتِ Next به ناوبریِ کامل ⇒ خروج از پیش‌نمایش به `/login` ِ خودِ AI Creator (۴۰۴/۴۰۱).
- **[CHANGE]** اسکریپتِ رصدِ پروکسی: `_px` برای رشته‌های مطلق/نسبی، `URL` و `Request` ِ هم‌مبدأ؛ `history.pushState/replaceState` زیرِ مسیرِ پروکسی؛ پروکسی هدرهای `RSC`، `Next-Router-State-Tree`،
  `Next-Router-Prefetch`، `Next-Url` را می‌فرستد و پاسخِ `text/x-component` هم بازنویسیِ `/_next/` می‌گیرد.
- **[VERIFY]** +۱ تست؛ pytest سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۵۵) — PM-INS-0022 (ادامه): بارِ RSC ِ خروجیِ ایستای Next (text/plain)

- **[VERIFY]** پس از 196f71f: قابِ Detective-1 و ALLIN1 داخلِ مسیرِ پروکسی می‌ماند (پیش‌تر به `/login` ِ AI Creator می‌پرید)؛ Detective-1 بی‌خطا.
- **[FINDING]** ALLIN1 خروجیِ ایستای Next است و بارِ RSC را به‌صورتِ `…/index.txt` با `text/plain` می‌دهد ⇒ ارجاعِ `/_next/static/css/…` در آن بازنویسی نمی‌شد ⇒ یک CSS از `/_next` ِ AI Creator.
- **[CHANGE]** بازنویسیِ `/_next/` برای پاسخ‌های `text/plain` و `json` هم.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۵۶) — PM-INS-0022 (ادامه): حلقهٔ ورودِ Detective-1 در پیش‌نمایش

- **[VERIFY]** پس از d28a0a7 پذیرش برقرار شد: «WS: متصل» Detective-1 ۶٫۲ ث، language ۵٫۱، ALLIN1 ۵٫۵؛ کلیک در چت ۰٫۳ ثانیه پس از کلیک برای هر سه («Sent message … click» از خودِ Bridge)؛
  language صفحهٔ ورودِ خودش («لهجه لبنانی … ورود با گوگل») و ALLIN1 داشبورد/ورودِ خودش («Banking Ops | Dashboard | Customers …») را کامل نشان دادند.
- **[FINDING]** Detective-1 سیاه می‌ماند: روترِ Next مسیر را `/api/render/inspector/proxy/…/login` می‌بیند، هیچ مسیری نمی‌خورد و نگهبانِ ورود دوباره به `login?next=<مسیرِ پروکسی>` می‌برد — حلقه.
- **[CHANGE]** اسکریپتِ رصد برای صفحه‌های Next (`__STRIP__`): پیش از اسکریپت‌های اپ، نشانیِ دیدنی به مسیرِ خودِ اپ برمی‌گردد (`replaceState`)؛ درخواست‌ها همچنان از پروکسی؛ history برای Next پیشوند نمی‌گیرد.
- **[VERIFY]** +۱ تست؛ pytest سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۵۷) — سنجشِ نهاییِ PM-INS-0022 روی production و جواب در برگه

- **[VERIFY]** روی 5ad6d72، مرورگرِ ناظر: «WS: متصل» Detective-1 ۶٫۲ ث، language ۶٫۴، ALLIN1 ۵٫۷؛ کلیک تا ثبت در چت ۰٫۳ ث برای هر سه؛ Detective-1 صفحهٔ ورودِ خودش را پایدار نشان داد
  (حلقه رفع شد)؛ «🔍 تشخیص»: Detective-1 ⇐ `preview_injection`، quran ⇐ `repo`. جواب در برگه: fixed + تصویر.
- **[TODO]** (آگاهانه) ورودِ گوگلِ خودِ اپ‌ها داخلِ sandbox ِ پیش‌نمایش ممکن نیست؛ پروکسی فقط GET.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production

## 2026-11-17 (۵۸) — فوری PM-INS-0023: هویتِ مدل، یک رویداد = یک خط، ضبطِ بی‌پنجرهٔ اشتراک

- **[OWNER]** (هماهنگ‌کننده، ۱۶:۲۴ دبی) برگهٔ ۲۲ و «عامل» تأیید شد. مانده‌ها: (۱) برچسبِ deepseek-chat ولی متن «Claude 3.5 Sonnet از API ِ Anthropic»، ۱۲٬۷۸۸ توکن برای یک خط؛ (۲) در
  پیش‌نمایشِ language هر کلیک دو بار در چت؛ (۳) راهی برای آزمودنِ «ضبط» بی‌پنجرهٔ انتخابِ اشتراکِ صفحه.
- **[CHANGE]** (۱) `services/model_identity.py`: یادداشتِ «هویتِ تو (واقعیت — سرور تعیین کرده)» با نام، شناسه، provider و مسیر (کلیدِ API / اشتراکِ OAuth) + «فقط همین را بگو»؛ در همهٔ
  پرامپت‌های چتِ بازرس (`general_instructions_text`) و برای پرسشِ فقط‌هویتی مسیرِ سبک (بی‌بافتِ مخزن، ۴۰۰ توکن خروجی)؛ اگر مدلِ جایگزین جواب داد، هویتِ همان را سرور می‌گوید.
  (۲) پنجرهٔ حذفِ تکراری از ۲ به ۶۰ ثانیه: رویدادی که هنگامِ وصل‌شدنِ WS هم با postMessage رفت و هم در صفِ سوکت ماند، با تأخیرِ چندثانیه‌ای دوباره ثبت می‌شد (کلید همان مُهرِ زمانیِ میلی‌ثانیه‌ای است).
  (۳) «🖥 ضبطِ سمتِ سرور» در پنجرهٔ ضبط: بی getDisplayMedia و بی میکروفون؛ Chromium ِ سرور صفحهٔ واقعیِ پروژه را عکس‌برداری می‌کند (`start-screencast`) و کلیک/تایپ از Bridge ثبت می‌شود؛
  `start-screencast` نشانیِ پیش‌نمایش/خالی را به فرانتِ واقعیِ پروژه برمی‌گرداند (`resolve_preview_frontend_url`، مشترک با پروکسی).
- **[VERIFY]** `tests/test_pm_ins_0023_identity_recording.py` (۵)؛ pytest ۹۰۶ سبز. سنجشِ زنده در برگه.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest

## 2026-11-17 (۵۹) — سنجشِ زندهٔ PM-INS-0023 روی production و جواب در برگه

- **[VERIFY]** (۱) همان پرسشِ هویتی در چتِ بازرسِ quran: deepseek-chat ⇐ «DeepSeek Chat … API دیپ‌سیک با کلید API» (۲۳۸ توکن، پیش‌تر ۱۲٬۷۸۸)؛ gemini-2.5-flash ⇐ «Gemini 2.5 Flash … API ِ Google»
  (۲۴۴)؛ cloud_code ⇐ «claude-sonnet-5-5 … اشتراک Claude (توکن OAuth)، نه کلید API». (۲) کلیک در language پیش از «WS: متصل» ⇐ Bridge ۱ کلیک فرستاد، چت دقیقاً ۱ خط؛ نسخهٔ صف‌شده
  در «duplicate dropped» شمرده شد. (۳) «🖥 ضبطِ سمتِ سرور» روی quran: start ⇐ start-screencast ۲۰۰ ⇐ ۲ کلیک ⇐ پایان ⇐ پیش‌نمایشِ ضبط پس از ۶۵٫۶ ث (۱ keyframe، ۴ تعامل، پرامپتِ درست).
  جواب: fixed + تصویر.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی + API روی production


## 2026-11-17 (۶۰) — فوری PM-INS-0024: عددهای «تسک‌های فعال» ِ خانه = خلاصهٔ اتاق فرمان؛ ریزِ مصرفِ دیسک و پاک‌سازیِ امن

- **[OWNER]** (هماهنگ‌کننده، ۱۸:۲۴ دبی، بند ۹ «خانه همیشه سینک») (۱) کارتِ «تسک‌های فعال» در خانه «در انتظارِ بازبینی 267 · در حالِ اجرا 0» و خلاصهٔ یک‌صفحه‌ایِ اتاق فرمان
  «۱٬۳۷۹ تسکِ باز: پیشنهادِ اسکن ۱٬۲۲۱، در انتظار ۱۱۴، منتظرِ بازبینی ۴۴» — خانه همان تعریف و همان API را بخواند. (۲) دیسک ۷۸٫۶٪ و «آخرین پاک‌سازی 0MB» — چه جا گرفته
  (ده پوشه/جدولِ بزرگ)، پاک‌سازیِ امن با پیش‌نمایش و تأیید، هشدارِ تلگرام بالای ۸۵٪.
- **[FINDING]** (۱) خانه `tasks_by_status` ِ `/api/oversight/status` را می‌خواند که **تسک‌های بایگانی‌شده را هم** می‌شمارد (۲۶۷ منتظرِ بازبینی = ۴۴ باز + ۲۲۳ بایگانی)؛ خلاصه از
  `/api/oversight/summary` (باز = بایگانی‌نشده و نه done/cancelled). (۲) گزارشِ زندهٔ `/api/oversight/disk`: `tasks.json` به‌تنهایی ۱۲۷MB، `reports.json` ۱۷MB، `extractions.json` ۴MB؛
  فایل‌های قابلِ بایگانیِ janitor فقط ~۲MB و همه کمتر از ۷ روز ⇒ «0MB آزاد» درست بود (درایو وصل است). بقیهٔ ۸۰۲MB در گزارش دیده نمی‌شد. ضبط‌های بازرس در `/tmp` اند، نه دیسک.
- **[CHANGE]** فرانت: `lib/liveStats.ts` ⇐ `summary` از `/api/oversight/summary`؛ کارتِ خانه عدد = `totals.tasks_open` و زیرنویس = همان برچسب‌ها و ترتیبِ `open_by_status` ِ خلاصه.
  `components/DiskPanel.tsx` در خلاصهٔ یک‌صفحه‌ای (`/oversight#disk`): درصد، ۱۰ پوشه و ۱۰ فایلِ بزرگ، جدول‌های بزرگِ پایگاه‌داده، پیش‌نمایش ⇐ تیک ⇐ تأیید. کارتِ دیسکِ خانه بزرگ‌ترین فایل
  را می‌گوید و به `/oversight#disk` می‌رود. بک‌اند `services/disk_janitor.py`: `breakdown()` (در `report()`)، `db_tables()` (`dbstat`، وگرنه شمارِ سطر)، `cleanup_preview()` (کش/موقت ⇐ حذف؛
  لاگِ بیش از ۱۴ روز و فایلِ کهنهٔ اسکن/آپلود ⇐ اول درایو بعد حذف؛ پایگاه‌داده و JSONها هرگز)، `cleanup_apply()` (فقط مسیرهای همان پیش‌نمایش، بی درایو چیزی بایگانی‌کردنی برداشته نمی‌شود)،
  `telegram_alert()` (فقط ≥۸۵٪ یا خطای نوشتن، با ۵ فایلِ بزرگ). مسیرها: `GET /api/oversight/disk/cleanup-preview`، `POST /api/oversight/disk/cleanup` (`confirm: true`). زمان‌بندِ ۶ساعته
  حالا تلگرام را از `telegram_alert` می‌فرستد؛ بنرِ خانه همچنان از ۸۰٪.
- **[VERIFY]** `tests/test_disk_janitor.py` +۳ (ریزِ مصرف، پیش‌نمایش/اعمالِ امن، آستانهٔ ۸۵٪)؛ pytest ۹۰۹ سبز؛ `npm run build` سبز؛ `check_frontend_api.py` ۰ ناهم‌خوان.
- **[TODO]** `tasks.json` ِ ۱۲۷MB بزرگ‌ترین مصرف‌کنندهٔ شناخته‌شده است — پیشنهاد: بردنِ تسک‌های بایگانی‌شده (۶۱۵) به درایو با نسخهٔ سبک، مثلِ `reports_archive` (تصمیمِ مالک).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + build + گزارشِ زندهٔ دیسک

## 2026-11-17 (۶۱) — سنجشِ زندهٔ PM-INS-0024 روی production و جواب در برگه

- **[VERIFY]** روی 02f9c21: کارتِ خانه «۱٬۳۷۹ — پیشنهادِ اسکن ۱٬۲۲۱ · در انتظار ۱۱۴ · منتظرِ بازبینی ۴۴» = خلاصهٔ اتاق فرمان. پنلِ دیسک: ۷۸٫۶٪، `database.db` ۴۸۵MB
  (project_files ۱۳۱MB، render_logs ۹۷MB + ایندکس‌ها حدودِ ۷۲MB، ai_logs ۹۶MB، inspector_messages ۴۶MB)، `tasks.json` ۱۲۲MB، `oversight/verify_evidence` ۹۲MB. پیش‌نمایشِ پاک‌سازیِ فایلی خالی است
  (هیچ کش/لاگِ فایلی/فایلِ کهنه‌ای نیست). جواب: partial — هر دو تصویر گرفته شد.
- **[TODO]** تصمیمِ مالک: (الف) render_logs/ai_logs ِ قدیمی ⇐ درایو ⇐ حذفِ ردیف (VACUUM ۴۸۵MB جای موقت می‌خواهد، فقط ۱۹۲MB آزاد است)؛ (ب) تسک‌های بایگانی‌شده از `tasks.json` به درایو.
  نکته: `RenderLogSettings.retention_hours` = ۴۸ ولی ۹۷MB لاگ مانده ⇒ باید بررسی شود که آیا پاک‌سازیِ دوره‌ایِ render_logs اجرا می‌شود.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API و اسکرین‌شات روی production

## 2026-11-17 (۶۰) — PM-INS-0024 «الف»: لاگ‌های قدیمی به درایو و بیرون از پایگاه‌داده؛ نگه‌داریِ ۴۸ ساعته واقعاً اجرا می‌شود

- **[OWNER]** (هماهنگ‌کننده، شبِ ۱۷ نوامبر) فقط «الف»: ردیف‌های render_logs ِ بیش از ۱۴ روز و ai_logs ِ بیش از ۳۰ روز اول به‌صورتِ فایلِ فشرده به درایو (دیدنی/جست‌وجوپذیر از «لاگ رندر › آرشیو»)
  و بعد از جدول حذف؛ «ب» انجام نشود؛ نگه‌داریِ ۴۸ ساعته‌ای که اجرا نمی‌شد درست شود؛ پیش‌نمایش و عددِ قبل/بعد روی production.
- **[FINDING]** `render_service.cleanup_old_logs` (نگه‌داریِ ۴۸ ساعته) هیچ‌جا زمان‌بندی نشده بود (فقط endpoint ِ دستی) و «آرشیو» را دوباره **داخلِ همان پایگاه‌داده** (`render_log_archives`) می‌نوشت.
- **[CHANGE]** `services/log_archive.py` + جدولِ `log_drive_archives`: پیش‌نمایش؛ انتقالِ دسته‌ایِ (۲۰٬۰۰۰) قدیمی‌ترین‌ها به‌صورتِ JSONL ِ gzip به درایو («بایگانیِ سرور/<جدول>»)، حذفِ دقیقاً همان ردیف‌ها فقط پس از
  تأییدِ درایو، فهرست و جست‌وجو (دانلودِ فایل‌های هم‌پوشان، کش)؛ `/api/render/log-archive/{preview,run,status,list,search}` (run فقط با confirm، در پس‌زمینه)؛ پاک‌سازِ ۶ ساعته آن را با
  `retention_hours` (۴۸ ساعت) و ۳۰ روزِ ai_logs اجرا می‌کند؛ `components/LogDriveArchive.tsx` در «لاگ رندر › آرشیو». درایو وصل نباشد ⇒ هیچ حذفی. «ب» دست نخورد.
- **[DECISION]** بخشِ دومِ پیام (commit ِ واقعی با مدلِ ضعیف در project-management): مسیرِ «اعمال» ِ بازرس ویژه همیشه شاخهٔ تازهٔ `inspector/smart-fix-…` + PR می‌سازد و هرگز روی main
  نمی‌نویسد؛ به «فقط پایش» ربطی ندارد — هیچ تنظیمی لازم نیست. خطر فقط در **ادغامِ** آن PR است (= دیپلوی، بی‌تست/بی‌دروازهٔ ship.sh). «اجرای خودکار» برای این مخزن قفل است (`_SELF_REPOS`). چیزی روشن نکردم.
- **[VERIFY]** `tests/test_pm_ins_0024_log_archive.py` (۶). سنجشِ production در همان برگه.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest

## 2026-11-17 (۶۱) — PM-INS-0024 «الف»: اجرا روی production + کوتاه‌کردنِ WAL

- **[VERIFY]** پس از a55a6ca، پاک‌سازِ ۶ ساعته در نخستین تیک اجرا شد: render_logs ۳۹۴٬۹۳۲ ⇐ ۴٬۴۹۰ ردیف (۳۹۰٬۴۴۲ در ۲۰ فایلِ درایو)، ai_logs ۲۸٬۴۹۰ ⇐ ۵۸۹ (۲۷٬۹۰۱ در ۲ فایل)؛
  جدول‌ها: render_logs ≈۱٫۳MB و ai_logs ≈۲MB (پیش‌تر ≈۱۷۰ و ۹۶MB).
- **[FINDING]** دیسک ۸۰٫۱٪ ⇐ ۸۵٫۲٪: حذف‌های بزرگ اول در WAL نوشته شد (`database.db-wal` ۷ ⇐ ۷۴MB) و WAL خودبه‌خود کوچک نمی‌شود؛ `database.db` (۵۰۸MB) حالا ~۲۵۰MB صفحهٔ آزاد دارد که دوباره
  استفاده می‌شود. VACUUM ِ کامل ~۲۶۰MB جای موقت می‌خواهد و فقط ~۱۳۰MB آزاد است — انجام نشد.
- **[CHANGE]** `log_archive.run`: پس از جابه‌جایی `PRAGMA wal_checkpoint(TRUNCATE)`؛ `database.py`: `journal_size_limit=32MB`.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API و لاگ‌های production

## 2026-11-17 (۶۲) — PM-INS-0024 «الف»: سنجشِ نهایی و جواب در برگه

- **[VERIFY]** پس از 8a86d8b و اجرای دستی (confirm): `wal_checkpoint(TRUNCATE)` ⇐ WAL ۷۴٫۴ ⇐ ۰MB، دیسک ۸۵٫۱٪ ⇐ ۷۷٫۹٪ (۲۰۹MB آزاد)؛ جست‌وجوی «Traceback» در بایگانیِ render_logs ۱٫۷ ث / ۲۰۰ نتیجه،
  «deepseek» در ai_logs نتیجه داد؛ تبِ «لاگ رندر › آرشیو › ☁️ بایگانیِ درایو» بی‌خطای صفحه. جواب در برگه: fixed + تصویر، همراه با پاسخِ «commit با مدلِ ضعیف» (هیچ تنظیمی لازم نیست؛ شاخه + PR؛ خطر فقط در ادغام).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی + API روی production

## 2026-11-17 (۶۳) — PM-INS-0025: موتور خالق — رعایتِ قیدها، خودسنجی (تست + مرورگر) و اصلاح تا سبز، پیش‌نمایشِ زنده و zip

- **[OWNER]** (هماهنگ‌کننده، ۰۰:۰۶؛ مالک: «موتور خالق خیلی بی‌کیفیت است») پروژهٔ «test-calculator-coordinator» با DeepSeek: منطقِ calculator.js درست، ولی در مرورگر کار نمی‌کند
  (اسکریپت‌ها بی type="module" با export، js/app.js اصلاً بار نمی‌شود)، package.json «type: commonjs» + jest ⇒ تست خطا، با «بدونِ بک‌اند» باز main.py/FastAPI/requirements.txt،
  یادداشتِ «بررسیِ repo» در پرامپتِ مرحلهٔ ۱، و هیچ خودسنجی‌ای پیش از «ساخته شد». پذیرش: همان پروژه دوباره با DeepSeek؛ «2+3=» ⇒ 5 در مرورگر و `npm test` سبز.
- **[FINDING]** `simple_creator._generate_structure` نمونهٔ JSON‌اش عیناً `src/main.py` و `requirements.txt` بود (مدلِ ضعیف کپی می‌کرد)؛ `_generate_file` هر فایل را **بی‌خبر از بقیه** می‌نوشت
  (ریشهٔ ناهماهنگیِ HTML/JS)؛ قیدِ کاربر هیچ‌جا اعمال نمی‌شد؛ هیچ اجرایی پس از ساخت نبود؛ ایمیجِ بک‌اند Node نداشت؛ یادداشتِ repo از `EXECUTOR_DISCLAIMER` ِ مشترک می‌آمد.
- **[CHANGE]** `services/creator_selfcheck.py` (تازه): `detect_constraints` (فقط عبارت‌های صریحِ خودِ کاربر — متنِ قالبِ پرامپت را نمی‌خواند)، قواعدِ ساختار و شکلِ ثابتِ اپِ مرورگری،
  `filter_planned_files`، `order_for_generation` + `context_for_file`، `static_problems` + `deterministic_fixes` (type="module"، بارگذاریِ ورودیِ جامانده، package.json)، `run_tests` (اسکریپتِ تستِ
  package.json با Node، بی‌نصب)، `run_browser` (Chromium روی سرورِ محلیِ ۱۲۷.۰.۰.۱: pageerror، 404، سناریوی کلیک/انتظار، عکس)، `plan_browser_steps`، `fix_loop` (تا ۳ دور؛ قالبِ
  `=== FILE: … ===`). «اجرا نشد» ِ زیرساخت (`blocked`) سبز حساب نمی‌شود و به مدل هم داده نمی‌شود.
  `simple_creator`: فیلدهای `constraints`/`selfcheck`، `run_selfcheck`، عکس‌ها در `_selfcheck/<id>` (پروژه فایلِ اضافه نمی‌گیرد). `simple_projects`: قیدها از `description` ِ خامِ کاربر
  + `structured_prompt.constraints`، `selfcheck: true` (پیش‌فرض)، `POST /projects/{id}/selfcheck`، `GET …/selfcheck/screenshot`، `POST …/preview-url`، `GET /preview/{id}/~pt~…/…` (CSP sandbox،
  nosniff، ACAO *)، `GET …/zip`. `core/auth`: `CREATOR_PREVIEW_PREFIX` با بلیتِ `creator:<id>`. `oversight_strong_prompt`: `NEW_PROJECT_NOTE` و `new_project=True`؛
  `creator_idea_to_prompt`: فیلدِ `constraints`، حذفِ فناوری/endpoint ِ سرور با «بدونِ بک‌اند». `Dockerfile`: `nodejs`. فرانت: `components/CreatorSelfcheckPanel.tsx` در `/project/[id]`.
- **[DECISION]** «npm test» بی npm: Debian ‏`npm` صدها بسته می‌کشد؛ اسکریپتِ تستِ package.json فقط وقتی `node …` است اجرا می‌شود (هیچ نصبی روی سرور) — برای همین اپِ مرورگری `node --test` می‌گیرد.
- **[VERIFY]** `tests/test_creator_selfcheck.py` (۹، شاملِ مرورگرِ واقعی: ماشین‌حسابِ خراب ⇒ دورِ ۰ تست ۰/۱ و سناریو ۴/۵ ⇒ دورِ ۱ سبز ۵/۵). کلِ تست‌ها ۹۲۳ قبول. سنجشِ production در ورودیِ بعد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + Chromium ِ محلی

## 2026-11-17 (۶۴) — PM-INS-0025: سنجشِ production + سناریوی کامل‌تر و جلوگیری از «سبز با حذفِ تست»

- **[VERIFY]** پس از d7f304fc، همان درخواستِ هماهنگ‌کننده با DeepSeek روی production: مرحلهٔ ۱ ‏۹ ث، پرامپت ۴٬۶۹۹ نویسه (پیش‌تر ۲۱٬۳۱۶)، بی یادداشتِ repo، `constraints` شاملِ «بدونِ بک‌اند»، ۰ endpoint؛
  ساخت ۱۱۶ ث، ۱۱ فایل (هیچ .py/requirements/Dockerfile)، `static-web`. خودسنجی: دورِ ۰ تست ۴۰/۴۲ و سناریو ۱/۵ ⇒ دورِ ۱ سناریو ۵/۵ ⇒ دورِ ۲ **سبز** (تست ۳۲/۳۲، سناریو ۵/۵، ۰ خطای صفحه).
  مستقل: zip ‏(۱۷٬۳۸۸ بایت) ⇒ `node --test` ‏۳۲/۳۲؛ Chromium: کلیکِ 2+3= ⇒ 5، کیبورد 0.1+0.2=0.3، 7/2=3.5، 123⌫=12، بی خطا.
- **[FINDING]** (۱) 10/0 فقط «خطا» نشان می‌دهد با این‌که پیامِ فارسی در calculator.js هست — سناریو فقط کارِ اصلی را می‌سنجید. (۲) دورِ ۲ تست‌ها را هم بازنویسی کرد (۴۲ ⇒ ۳۲):
  «سبز با کم‌کردنِ تست» ممکن بود. (Node فایلِ بی‌تست را هم یک «test» می‌شمارد.)
- **[CHANGE]** سناریوی مرورگر حالا «هر ویژگیِ دیدنیِ خواسته‌شده» با متنِ موردِ انتظارِ کاربر (۵ تا ۴۰ قدم)؛ شمارشِ «مورد»های نام‌دار (`cases`)؛ کم شدنِ موردها نسبت به دورِ ۰ ⇒ ایراد و سبز نیست؛
  پرامپتِ اصلاح «تست را حذف/ضعیف نکن»؛ `POST …/selfcheck` با `replan` (دکمهٔ «اجرا و اصلاح تا سبز» سناریو را از نو می‌نویسد)؛ ساخت با `max_tokens=8000` (دورهای اصلاح فایلِ کامل می‌نویسند).
- **[VERIFY]** ‏`tests/test_creator_selfcheck.py` ‏۱۰ (تستِ تازه: «اصلاح» با خالی‌کردنِ فایلِ تست سبز نمی‌شود).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API + Chromium روی خروجیِ production

## 2026-11-17 (۶۵) — PM-INS-0025: «اجرا و اصلاح» یک پروژهٔ سبز را بدتر کرد ⇒ اول سناریو، بهترین دور می‌ماند، برگرداندن

- **[FINDING]** آزمونِ `POST …/selfcheck` (replan) روی همان ماشین‌حسابِ سبز (proj_7d391e88) با DeepSeek: سناریوی تازهٔ ۳۹ قدمی انتخابگرهای ناموجود داشت (`data-digit`، `.key-num:nth-child(1)`،
  `html[data-theme]` به‌صورتِ متن) و حلقه **برنامه را به‌خاطرِ سناریوی غلط بازنویسی کرد**: ۳ دور، تست‌ها ۳۲ ⇒ ۲۵ مورد، سناریو ۳۶/۳۹، سبز ⇒ ناسبز. برنامه هنوز کار می‌کند (۲۵/۲۵، 2+3=5)
  ولی ضعیف‌تر شد؛ نسخهٔ سبزِ پیشین را من از zip دارم ولی سرور راهی برای بازگرداندن نداشت. **تقصیرِ آزمونِ من است** و در جواب گفته می‌شود.
- **[CHANGE]** `creator_selfcheck`: قدمی که المان/انتخابگرش در صفحه نیست = ایرادِ **سناریو** (`scenario_error`) ⇒ تا ۲ بار فقط سناریو با HTML ِ واقعی اصلاح می‌شود، به مدلِ اصلاحِ برنامه داده
  نمی‌شود و سبز هم حساب نمی‌شود (`blocked`)؛ `el[attr]` attribute را می‌خواند؛ مقایسه فاصله/سطر را نادیده می‌گیرد (عددها دقیق)؛ هر دور امتیاز می‌گیرد و در پایان **بهترین دور** برمی‌گردد
  (`restored_round`) — اصلاح هرگز پروژه را بدتر از اول رها نمی‌کند؛ پرامپتِ اصلاح «id/class/data-* ِ موجود را عوض نکن». `simple_creator`: پیش از هر «اجرا و اصلاح» نسخهٔ پشتیبان
  (۵ تا، در `_selfcheck/<id>/`)، `undo_last_fix`؛ `POST /projects/{id}/selfcheck/undo`؛ دکمهٔ «↩ برگرداندن به پیش از آخرین اصلاح» در پنل.
- **[VERIFY]** `tests/test_creator_selfcheck.py` ‏۱۴ (تازه: انتخابگرِ غلط فقط سناریو را عوض می‌کند و برنامه دست‌نخورده سبز می‌شود؛ اصلاحِ بدتر برگردانده می‌شود؛ مقایسه؛ undo).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API ِ production + pytest

## 2026-11-17 (۶۶) — PM-INS-0025: ساختِ تازه روی production + قاعدهٔ دقیق‌ترِ «حذفِ تست»

- **[VERIFY]** پس از a182ea09، ساختِ تازهٔ همان درخواست با DeepSeek (proj_18cc2a74): ۲۲۹ ث، ۱۲ فایل، بی فایلِ سرور؛ دورِ ۰ تست ۴۷/۶۸ و سناریو ۳۰/۳۵ (۲ قدمِ «انتخابگر در صفحه نیست» ⇒ ایرادِ سناریو)،
  دورِ ۲: سناریوی ۳۵ قدمی **۳۵/۳۵** (2+3=5، «تقسیم بر صفر مجاز نیست»، ⌫، ٪، 9×7=63، تاریخچه، حالتِ تاریک) و تست ۴۷/۴۷؛ دورِ ۳ بدتر (۵۲/۵۵، ۳۴/۳۵) ⇒ **دورِ ۲ برگردانده شد**
  (`restored_round=2`؛ zip ⇒ `node --test` ‏۴۷/۴۷). سبز اعلام نشد چون موردها ۶۸ ⇒ ۴۷.
- **[DECISION]** «کم شدنِ تعداد» قاعدهٔ کندی بود: ۲۱ تا از ۶۸ از اول رد می‌شدند (تستِ غلط). قاعدهٔ تازه: هر تستی که در اجرای اول **قبول** بود باید با همان نام بماند و قبول شود؛ بازنویسی/حذفِ تستِ
  ردشده مجاز است و گزارش می‌شود (`tests_removed_failing`). نوع با «بدونِ بک‌اند» همیشه `static-web` (این بار `node` آمده بود).
- **[VERIFY]** `tests/test_creator_selfcheck.py` ‏۱۵.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API ِ production + node --test روی zip

## 2026-11-17 (۶۷) — PM-INS-0025: ساختِ سوم + فهرستِ دقیقِ تست‌های ردشده برای مدل

- **[VERIFY]** پس از d114d0b4 ساختِ سوم (proj_f29027be، ۱۳ فایل، static-web): DeepSeek ‏۱۱۷ تست نوشت که ۳۳ تا رد می‌شد؛ سناریوی مرورگر ۳۰/۳۲ ⇒ در دورهای ۱–۳ ‏۳۲/۳۲ ولی هر دور تست‌های
  قبول‌شده را از دست داد (۲۳، ۰، ۳۴ قبول) ⇒ حلقه درست دورِ ۰ را نگه داشت؛ سبز نشد. از سه ساختِ تازه، یکی سبز (proj_7d391e88، پیش از آن‌که آزمونِ replan ِ من ضعیفش کند)،
  یکی ۳۵/۳۵ + ۴۷/۴۷ اما «۲۱ تستِ ردشده حذف شد» (proj_18cc2a74)، یکی این.
- **[FINDING]** مدل از نتیجهٔ تست فقط ۲٬۵۰۰ نویسهٔ **آخرِ** خروجیِ TAP را می‌دید — با ۱۱۷ تست یعنی فقط تست‌های قبول‌شده.
- **[CHANGE]** `failing_tests`: از بلوک‌های `not ok` فهرستِ «نام (فایل:خط): انتظار X بود، Y آمد — خطا» (تا ۱۵) ساخته و به‌جای دمِ خروجی به مدل داده می‌شود؛ پرامپتِ اصلاح:
  «اگر تست با خواستهٔ کاربر می‌خواند کد را درست کن؛ اگر خودِ تست غلط است همان تست را با همان نام اصلاح کن؛ تستِ قبول را دست نزن».
- **[VERIFY]** `tests/test_creator_selfcheck.py` ‏۱۶.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API ِ production + pytest

## 2026-11-17 (۶۸) — PM-INS-0026: بازرس ویژه (مکث هنگامِ قطعی، گزارشِ صادق، دکمه‌های سریع، ژورنال، حافظهٔ کهنه، راه‌اندازیِ سرور) + خطِ «آخرین اجرای واقعی»

- **[OWNER]** (هماهنگ‌کننده، ۰۰:۴۵ دبی ۱۸ نوامبر؛ مالک: «همهٔ زیرقسمت‌ها و دکمه‌ها بررسی شود») الف ۱–۵ و ب — متنِ کامل در برگهٔ PM-INS-0026.
- **[FINDING]** (۱) اجرای مرحله‌ای پس از «Failed to fetch» فقط ۲ و ۴ ثانیه صبر می‌کرد (دیپلوی ~۳ دقیقه)، خروجیِ خالی «نتیجه» حساب می‌شد، تیترِ گزارش همیشه «N مرحله کامل شد» بود و
  بلوکِ «AI اقدام نکرد / مدل ضعیف است» برای هر گزارشِ بی‌فایل می‌آمد. (۲) دکمه‌های سریع فقط `setInspectorChatInput`. (۳) بازرس، عامل و اجرای مرحله‌ای در `inspector_messages`
  می‌نویسند و ژورنال فقط `activity_logs` را می‌خواند. (۴) `project_auto_setup` هر وابستگیِ `react` را «React/Next.js» برچسب می‌زد ⇒ حافظهٔ quran (Vite + React) «React و Next.js» و
  ۳ فیلد (App Router، getStaticProps/next.config، axios + NEXT_PUBLIC_API_BASE_URL). (۵) `GlobalAnalysisProgress` در Layout هر ۳ ثانیه `GET /api/projects` (و چون `project.id` می‌خواند
  ولی فهرست `project_id` دارد، هرگز پیشرفتی هم نمی‌دید)؛ شکستِ شبکه در صفحهٔ پروژه = «پروژه پیدا نشد». (ب) `auto_via_projects_page` فقط تسک را به چتِ بازرس می‌فرستد (کدی اعمال نمی‌کند)؛
  «اعمال» ِ بازرس همیشه شاخهٔ تازه + PR؛ Claude runner برای project-management قفل است (`_SELF_REPOS`).
- **[CHANGE]** فرانت `projects/[id]`: شکستِ شبکه ⇒ «⏸ مکث تا برگشتِ سرور» (`waitForBackend` تا ۱۲۰ ث) و بعد همان مرحله؛ پاسخِ خالی ⇒ «⚪ خالی» و تکرار (۳ بار)؛ `stepOutcome` و تیترِ
  «X از N مرحله کامل شد» + «🔌 K مرحله به‌خاطرِ قطعیِ سرور اجرا نشد — تقصیرِ مدل نیست»؛ گزارشِ تحلیلیِ بی‌فایل دیگر «AI اقدام نکرد» نمی‌گیرد؛ یافته‌ها ۵۰۰ نویسه با شمارهٔ واقعیِ مرحله.
  `quickSendInspector`: دکمه‌های سریع می‌فرستند (در حینِ اجرای دیگر، متن در کادر + راهنما). صفحهٔ پروژه: «سرور در حال راه‌اندازی… تلاشِ دوباره» و تلاشِ خودکار پس از `/health`؛
  `ProjectsView`: همان به‌جای «پروژه‌ای نیست». `GlobalAnalysisProgress`: ۳۰ ث (۳ ث فقط وقتی تحلیلی در جریان است)، در تبِ پنهان هیچ، `project_id`.
  بک‌اند: `project_journal.sync_inspector_activity` (پاسخ‌های بازرس ⇒ ژورنال، `act_insp_<id>`، تکرارناپذیر، ۳۰ روزِ گذشته را هم پر می‌کند) در `/journal` و `/journal/stats` و گزارش‌ها؛
  `services/memory_stack_review.py` + `POST /api/projects/{id}/memory/review-stack` و پس از هر سینکِ GitHub ِ دارای فایلِ تازه: فیلدِ فریم‌ورکِ ناموجود ⇒ بایگانی با `stale_stack:<fw>`
  (حذف نه)، یک پاراگرافِ «⚠️ اصلاحِ خودکارِ حافظه» بالای دستورات (متنِ اصلی می‌ماند)؛ `project_auto_setup`: Next.js / React / Vite جدا. `oversight_summary.last_real_runs` + کارتِ
  «⏱ آخرین اجرای واقعیِ یک تسک … ؛ هیچ پروژه‌ای اجرای خودکارِ کد ندارد» + «خودمختاری auto ولی فقط verify» + مسیرِ امن.
- **[DECISION]** «ب»: برای آزمونِ یک‌خطی روی project-management **هیچ تنظیمِ اتاق فرمان لازم نیست و نباید عوض شود** — مسیرِ امن «بازرس ویژه» ِ همان پروژه ⇒ «اعمال» ⇒ شاخه + PR. روشن‌کردنِ
  Claude runner برای این مخزن کاری نمی‌کند (قفل) و `allow_push` یعنی commit ِ مستقیم روی main = دیپلوی بی‌تست. چیزی روشن نکردم.
- **[VERIFY]** `tests/test_pm_ins_0026.py` ‏(۴)؛ کلِ تست‌ها ۹۳۲.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + tsc

## 2026-11-17 (۶۹) — PM-INS-0025/0026: سنجشِ production پس از 1e9a8546 + حکمِ سه‌حالته

- **[VERIFY]** «۰۰۲۶»: `POST …/memory/review-stack` روی quran ⇒ پشته React + Vite، ۳ فیلدِ Next.js بایگانی (`stale_stack:Next.js`)، پاراگرافِ اصلاح بالای دستورات. ژورنال پس از سینک ۱ فعالیت
  (پاسخ‌های بازرس در DB کم‌اند: فرانت فقط پیام‌های سشنِ فعال را ذخیره می‌کند — سشنِ ۱۸۳۰). «بررسی امنیت» با DeepSeek Chat (مرورگرِ واقعی، انتخابِ دستیِ مدل): اسکنِ موردیِ عمیق
  ۲۱:۰۰:۳۲ ⇒ ۲۱:۰۵:۲۰ «✅ ۲۶ پیشنهاد از ۴۴ finding»؛ کلیکِ دوم در حینِ اسکن «منتظر بمانید» گرفت. در ۶۰ ثانیهٔ اولِ اجرا ۲ بار `GET /api/projects` (پیش‌تر ~۷ در ۲۰ ث).
  خلاصهٔ اتاق فرمان: هیچ تسکی `last_run_at` ندارد ⇒ خط «هرگز» می‌گفت؛ حالا به اجرای پروژه برمی‌گردد («آخرین اجرای خودکارِ تسک‌ها: ۲۰۲۶-۰۶-۰۷ …»)؛ هر ۹ مخزن «auto ولی فقط verify».
  مکثِ «⏸ تا برگشتِ سرور» روی production زنده آزموده نشد (به یک دیپلویِ هم‌زمان با اجرای مرحله‌ای نیاز دارد) — فقط tsc/بیلد.
- **[VERIFY]** «۰۰۲۵»: «اجرا و اصلاح» (۵ دور، فهرستِ تست‌های ردشده) روی proj_f29027be: دورِ ۲ = تست ۷۴/۷۴ و سناریو ۳۲/۳۲ ⇒ نگه داشته شد؛ مستقل: zip ⇒ `node --test` ‏۷۴/۷۴، Chromium:
  2+3 ⇒ «۵»، 10/0 ⇒ «تقسیم بر صفر مجاز نیست»، 0.1+0.2 ⇒ «۰٫۳»، 7/2 ⇒ «۳٫۵». سبز اعلام نشد: ۸۴ تستِ قبول‌شدهٔ اول به ۷۴ با نام‌های دیگر رسید.
- **[CHANGE]** حکمِ سه‌حالته `verdict`: green / `works_tests_rewritten` (همهٔ تست‌های فعلی + سناریو قبول، ولی تست‌های قبول‌شده بازنویسی شد — 🟡 «نگاه کنید») / not_green؛ پیامِ ساخت و پنل.
  `last_real_runs`: بازگشت به اجرای پروژه وقتی تسک‌ها مهر ندارند (`source`).
- **[VERIFY]** `tests/test_creator_selfcheck.py` ‏۱۷، `tests/test_pm_ins_0026.py` ‏۵.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API + مرورگرِ واقعی روی production
## 2026-11-17 (۷۰) — PM-INS-0025: آزمونِ پذیرش با ساختِ تازهٔ DeepSeek + مبنای «تستِ قبول نباید برود» از همهٔ دورها

- **[OWNER]** (روتینِ صفِ فوری) برگهٔ ۲۵ هنوز بی‌جواب بود؛ پذیرش: «همین پروژه را دوباره با DeepSeek بساز؛ در مرورگر 2+3= ⇒ 5 و npm test سبز، با عدد و عکس».
- **[VERIFY]** روی production (پس از 1e9a854): همان خواسته، `deepseek-chat`، نام «test-calculator-urgent-run» ⇒ مرحلهٔ ۱ ‏۱۳ ث، پرامپت ۴٬۹۱۴ نویسه، **بی** یادداشتِ repo، ۱۳ قید (شاملِ «بدونِ بک‌اند»)؛
  ساخت ۱۵۴ ث، `proj_aea848f1`، `static-web`، ۱۰ فایل (هیچ .py/requirements/Dockerfile). خودسنجی: دورِ ۰ SyntaxError در calculator.js (‏`</calculator.js>` در فایل) ⇒ تست ۰، سناریو ۳۰/۳۸؛
  دورِ ۱ تست ۵۱/۸۱، سناریو ۳۷/۳۸؛ دورِ ۲ تست ۷۹/۸۱، سناریو ۳۸/۳۸؛ دورِ ۳ **سبز**: تست ۷۰/۷۰، سناریو ۳۸/۳۸، ۰ خطای صفحه.
  مستقل روی zip ‏(۱۷٬۸۲۸ بایت): `npm test` ⇒ ۷۰/۷۰؛ Chromium (۳۹۰×۸۴۴): کلیکِ 2+3= ⇒ **5**، 10÷0 ⇒ «تقسیم بر صفر مجاز نیست»، 7÷2=3.5، 123⌫=12، کیبورد 0.1+0.2=0.3،
  تاریخچه ۴ مورد، حالتِ تاریک، `lang=fa dir=rtl`، ۰ خطا. 200×50%= ⇒ 20000 (رفتارِ ویندوز: ٪ = ۵۰٪ ِ ۲۰۰)، نه ۱۰۰ ِ مالک — گزارش شد.
- **[FINDING]** موردهای تست ۸۱ ⇒ ۷۰ در دورِ ۳ و هیچ هشداری: مبنای «تستِ قبول نباید برود» فقط دورِ ۰ بود و دورِ ۰ اصلاً اجرا نشده بود (SyntaxError) ⇒ نگهبان بی‌اثر.
- **[CHANGE]** `creator_selfcheck.fix_loop`: `base_passing` و `base_cases` پس از هر دور بزرگ می‌شوند (اجتماعِ نام‌های قبول‌شده، بیشینهٔ موردها)؛ همهٔ دورها نگه داشته و بهترین با مبنای نهایی انتخاب می‌شود.
- **[VERIFY]** `tests/test_creator_selfcheck.py::test_a_test_that_passed_in_a_later_round_may_not_be_dropped` (روی کدِ قبلی رد، روی کدِ تازه قبول)؛ کلِ تست‌ها ۹۳۳ قبول؛ `npm run build` سبز.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · API ِ production + node --test + Chromium روی zip

## 2026-11-17 (۷۰) — PM-INS-0027: «این فایل را بساز و یک خط بنویس» مستقیم به action_plan؛ لغوِ اسکن دیده می‌شود

- **[OWNER]** (هماهنگ‌کننده، ۰۱:۴۰ دبی ۱۸ نوامبر؛ مالک: «با مدلِ ضعیف مثلِ Claude Code برنامه‌نویسی کند») در بازرس ویژهٔ project-management با Local AI/DeepSeek: «در docs/COORDINATOR_TEST.md
  (اگر نیست بساز) دقیقاً این یک خط را بنویس… اعمال کن (شاخه + PR، بدونِ ادغام)» ⇒ اسکنِ موردیِ عمیق (explicit_keyword ۹۰٪) ⇒ `scan_aborted` («scope با هیچ فایلی نمی‌خورد» — فایل هنوز نیست)
  که هرگز در چت نیامد؛ ۱۰ دقیقه «پیشنهادها چند دقیقه دیگر…». پذیرش: همین درخواست با DeepSeek و جدا با Gemini Flash ظرفِ ۳ دقیقه یک PR (فقط همان فایل/خط، بدونِ ادغام). تنها تغییرِ مجازِ مالک در ریپو.
- **[FINDING]** (۱) دروازهٔ «عملیاتِ سادهٔ فایل» (`_is_simple_file_op`) روی **پرامپتِ ساختارمندشده** اجرا می‌شد که پر از «بررسی/review» است ⇒ ساده شناخته نمی‌شد؛ روی متنِ خودِ کاربر درست
  `True` است. (۲) پیامِ `scan_aborted` در DB بود ولی با مرتب‌سازی بر اساسِ db_id **بالای** پیام‌های محلیِ «در حال اسکن…» (که بعداً با id ِ بزرگ‌تر ذخیره می‌شوند) می‌نشست.
- **[CHANGE]** smart-chat: پیش از تشخیصِ اسکن، `_is_simple_file_op(original_message)` ⇒ بی‌اسکن، مستقیم به action_plan؛ «بنویس/write» هم فعلِ عملیاتِ فایل شد. فرانت: پایانِ اسکن با
  `result.aborted` ⇒ پیامِ «🚫 اسکنِ موردی لغو شد — دلیل» در **پایینِ** چت و همان درخواست یک بار بی‌اسکن (`enable_selective_scan: false`) دوباره فرستاده می‌شود.
- **[VERIFY]** `tests/test_pm_ins_0027.py` ‏(۲). سنجشِ production در ورودیِ بعد.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · pytest + tsc

## 2026-11-17 (۷۱) — PM-INS-0027: «اعمال» هیچ فایلی commit نکرد ⇒ ادغامِ مراحل و فایلِ خالی

- **[VERIFY]** پس از 80f5b9fc در مرورگرِ واقعی، بازرس ویژهٔ project-management، DeepSeek Chat: **بی‌اسکنِ عمیق**، action_plan در ۳۳ ث — فقط `docs/COORDINATOR_TEST.md` (create).
- **[FINDING]** «اعمال» ⇒ شاخهٔ `inspector/smart-fix-1794952526` ساخته شد و بعد «❌ هیچ فایلی commit نشد»، بی‌دلیل. درخواست به ۳ مرحله تجزیه شده بود (بررسی / نوشتن / شاخه+PR)؛ مرحلهٔ ۳ همان
  فایل را **بی‌محتوا** دوباره آورد و در ادغامِ فرانت جای نسخهٔ مرحلهٔ ۲ را گرفت؛ سرور فایلِ بی‌محتوا را بی‌صدا رد می‌کرد و شاخهٔ خالی می‌ماند.
- **[CHANGE]** enhance-prompt: عملیاتِ سادهٔ فایل (متنِ خودِ کاربر) مرحله‌بندی نمی‌شود؛ فرانت: در ادغامِ مراحل نسخهٔ بی‌محتوا جای نسخهٔ دارای محتوا را نمی‌گیرد؛ apply-action: فایلِ بی‌محتوا
  با پیامِ صریح، و اگر هیچ چیز commit نشد شاخهٔ `inspector/…` ِ خالی پاک می‌شود (`GitHubPRService.delete_branch` فقط برای `inspector/…`).
- **[TODO]** شاخهٔ خالیِ `inspector/smart-fix-1794952526` (از همین آزمون) روی project-management مانده — پاک‌کردنش با مالک.
- **[VERIFY]** `tests/test_pm_ins_0027.py` ‏(۴).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۷۲) — PM-INS-0027: پاک‌کنِ محتوا هر .md/.txt ِ فارسی را خالی می‌کرد

- **[VERIFY]** پس از 003ed542: DeepSeek بی‌مرحله‌بندی، action_plan در **۱۵ ث**، «✅ اعمال تغییرات» ⇒ حالا پیامِ صریح «⚠️ docs/COORDINATOR_TEST.md: محتوای فایل در action_plan خالی است».
- **[FINDING]** محتوا را مدل داده بود؛ `content_sanitizer.sanitize_file_content` آن را خالی کرد: مرحلهٔ ۲ و ۴ («حذفِ خط‌های فارسی/markdown ِ غیرکد از ابتدا و انتها») برای همهٔ `CODE_EXTENSIONS`
  اجرا می‌شد که **md و txt** را هم دارد ⇒ «آزمونِ … PM-INS-0027» ⇒ `""`، «# Title\n\nسلام» ⇒ «# Title». یعنی هر سندِ فارسی‌ای که بازرس/موتور خالق با هر مدلی می‌نوشت ناقص یا خالی commit
  می‌شد (یا اصلاً نمی‌شد) — ریشهٔ واقعیِ «هیچ فایلی commit نشد».
- **[CHANGE]** `PROSE_EXTENSIONS` (md/markdown/mdx/txt/rst) از مراحلِ ۲ و ۴ معاف؛ کد مثلِ قبل محافظت می‌شود.
- **[VERIFY]** `tests/test_pm_ins_0027.py` ‏(۵)؛ کلِ تست‌ها ۹۴۰.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۷۳) — PM-INS-0027: PR با DeepSeek ساخته شد؛ Gemini Flash به نگهبانِ «فایل خوانده نشد» خورد

- **[VERIFY]** پس از 4c5e8a9d، مرورگرِ واقعی، بازرس ویژهٔ project-management، DeepSeek Chat: ارسال ۲۳:۰۴:۴۴ ⇒ action_plan ‏۲۳:۰۴:۵۳ ⇒ «✅ اعمال تغییرات» ⇒ commit ‏۲۳:۰۴:۵۸ ⇒ **PR ‏۲۳:۰۵:۰۰ (~۱۶ ث)**:
  https://github.com/mahdighandi1989/project-management/pull/930 — شاخهٔ `inspector/smart-fix-1794956696`، فقط `docs/COORDINATOR_TEST.md` با یک خط («آزمونِ برنامه‌نویسی با مدلِ ضعیف —
  PM-INS-0027 — deepseek»)، ادغام‌نشده.
- **[FINDING]** Gemini 2.5 Flash: action_plan در ۸ ث، ولی «🚫 اعمال لغو شد: فایل‌های پروژه خوانده نشده بودند» — نگهبانِ فرانت هر plan ِ «بی‌خواندن» را رد می‌کرد، حتی ساختِ فایلِ تازه. و در
  سرور «create» وجودِ فایل را نمی‌سنجید (یعنی می‌توانست فایلِ موجود را بازنویسی کند).
- **[CHANGE]** فرانت: plan ِ فقط-create بی‌خواندن هم اعمال می‌شود؛ سرور: «create» روی فایلِ موجود رد می‌شود («باید modify باشد») — هیچ بازنویسیِ کورکورانه‌ای.
- **[VERIFY]** `tests/test_pm_ins_0027.py` ‏(۶).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + GitHub

## 2026-11-17 (۷۴) — PM-INS-0027: Gemini Flash برای یک خط ۵۰۰ فایل را خواند

- **[VERIFY]** پس از 5c591056، Gemini 2.5 Flash: حلقهٔ عامل این بار رسیدگی نکرد و مسیرِ قدیمی «دامنه: کل پروژه» را برگزید ⇒ ۵۰۰ فایل در ۱۷ دسته، بیش از ۷ دقیقه، بی action_plan در زمانِ آزمون.
- **[FINDING]** `_detect_request_scope` روی پرامپتِ ساختارمند (پر از «پروژه») اجرا می‌شد؛ DeepSeek در همان درخواست «هدفمند» گرفته بود.
- **[CHANGE]** عملیاتِ سادهٔ فایل (متنِ خودِ کاربر) ⇒ همیشه `TARGETED`.
- **[VERIFY]** `tests/test_pm_ins_0027.py` ‏(۷).

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + pytest

## 2026-11-17 (۷۵) — PM-INS-0027: پذیرش — دو PR با مدلِ ضعیف، هر کدام فقط یک فایل/یک خط

- **[VERIFY]** مرورگرِ واقعی، بازرس ویژهٔ project-management، موتور Local AI، انتخابِ دستیِ مدل، همان درخواستِ هماهنگ‌کننده:
  - DeepSeek Chat (پس از 4c5e8a9d): ارسال ۲۳:۰۴:۴۴ ⇒ PR ‏۲۳:۰۵:۰۰ (~۱۶ ث) — https://github.com/mahdighandi1989/project-management/pull/930
  - Gemini 2.5 Flash (پس از c4f238d3): ارسال ۲۳:۳۳:۵۱ ⇒ PR ‏۲۳:۳۴:۳۷ (~۴۶ ث؛ دامنهٔ هدفمند، ۲۵ فایل خوانده شد) — https://github.com/mahdighandi1989/project-management/pull/931
  - diff ِ هر دو: فقط `docs/COORDINATOR_TEST.md` (new file، یک خط)؛ هیچ‌کدام ادغام نشده‌اند. بی‌اسکنِ عمیق، بی‌مرحله‌بندی.
- **[TODO]** مالک: دو PR ِ آزمونی ادغام نشوند (یا بسته شوند)؛ شاخهٔ خالیِ `inspector/smart-fix-1794952526` از نخستین تلاش (پیش از پاک‌کنِ خودکارِ شاخهٔ خالی) هنوز هست.

> **امضا:** `Claude Code (Anthropic CLI)` · 2026-11-17 · مرورگرِ واقعی روی production + GitHub
