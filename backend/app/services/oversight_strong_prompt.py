"""
Strong Prompt Builder
=====================
سازندهٔ template پرامپت اجرایی فوق‌العاده دقیق برای تسک‌های oversight.
این template در همهٔ مسیرها (scan، idea_to_prompt، deep scan، ...) استفاده می‌شود.

ساختار خروجی:
  🎯 هدف
  📍 موقعیت دقیق در پروژه (با file:line و snippet)
  🧭 هدف اصلی پروژه (یادداشت کاربر)
  🧱 پشتهٔ فناوری و معماری
  🔗 فایل‌های مرتبط (cross-references)
  🌐 نقشهٔ وابستگی‌ها
  🔍 Context و وضعیت فعلی
  ✅ معیار پذیرش (Acceptance Criteria)
  🪜 مراحل اجرایی پیشنهادی
  💡 نمونه‌های قبل/بعد (اختیاری)
  📤 خروجی مورد انتظار
  🧪 دستورات اعتبارسنجی
  ⚠️ ریسک‌ها و موارد احتیاط
  🔗 وابستگی‌های تسکی
  🏷 دسته‌بندی
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Union


# ─────────────────────────────────────────────────────────────────────────────
# DISCLAIMER — همیشه ابتدای هر پرامپت تولیدشده درج می‌شود.
# هدف: مدل اجراکنندهٔ خارجی (Cursor, ChatGPT, Claude Code, ...) متوجه باشد که:
#   1. این پرامپت بر اساس بررسی اولیه است — قطعی نیست
#   2. مسئولیت بررسی مستقل با خود مدل است
#   3. اگر کار طولانی است، چند کامیت متوالی مجاز است (skip ممنوع)
# ─────────────────────────────────────────────────────────────────────────────

EXECUTOR_DISCLAIMER = """## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

📖 **خواندن کامل + اجرای مو-به-مو (بسیار مهم):**

این پرامپت — از این یادداشت تا انتها — یک سند واحد است که هر بخشش
حاوی الزام یا context منحصربه‌فرد است. خواندن سطحی یا skim کردن **ممنوع**
است.

- پرامپت را **سطر به سطر** بخوان، نه head/tail/فقط-بخش-اصلی.
- اگر بخشی به‌نظر طولانی یا تکراری آمد، **حتماً** بخوان — تفاوت‌های
  ریز ممکن است در آن جا اساسی باشند.
- هر جمله، URL، نام فایل، نام تابع، یا مقدار عددی که در پرامپت آمده،
  دقیقاً همان است که کاربر می‌خواهد — تغییرش نده، رندش نکن، خلاصه‌اش
  نکن.
- اگر پرامپت چندین درخواست/مرحله/زیرتسک دارد، **همه** را پیاده کن. حتی
  یکی را نه به‌عنوان "خارج از scope" حذف کن.

❌ ممنوعات صریح:
- خلاصه‌سازی متن کاربر در commit message یا response
- "این بخش اصلی نیست، رد می‌کنم"
- "کاربر احتمالاً منظورش این بود..." — منظورش همان است که نوشته
- "این URL/نام به نظر قدیمی است، آپدیتش کردم" — تغییر بدون درخواست ممنوع
- پیاده‌سازی فقط بخشی از پرامپت و تظاهر به کامل بودن
- "همه آیتم‌های لیست A را بررسی کردم، B و C مشابه بودند" — نه؛
  هرکدام را جداگانه

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

🔗 **وابستگی‌ها و همگام‌سازی (بسیار حیاتی — هرگز skip نکن):**

این بخش از همهٔ بخش‌های دیگرِ این یادداشت **مهم‌تر** است. اگر نقض شود،
نتیجهٔ کار ممکن است مشروع به‌نظر برسد ولی در عمل بخش‌های دیگر سیستم را عقب
بیندازد، broken reference تولید کند، یا منجر به data corruption شود.

پیش از و حین تغییر، تمام وابستگی‌ها را در **چهار جهت** به‌طور **کامل و
بدون هیچ خلاصه‌سازی** شناسایی و همگام کن:

**۱. وابستگی‌های upstream (این تسک به چه چیزهایی متکی است):**
- چه فایل‌ها، توابع، کلاس‌ها، API endpoint ها، schema های دیتابیس،
  env vars، یا config هایی که این تسک نیاز دارد؟
- آیا قرار است چیزی را ویرایش/حذف کنی که جای دیگر (signature، رفتار،
  return type، side effect) از آن انتظار خاصی می‌رود؟
- اگر dependency جدیدی اضافه می‌کنی، آیا با dependencyهای موجود تداخل
  دارد (نسخه، compat، lock file)؟

**۲. وابستگی‌های downstream (چه چیزهایی به این تسک متکی‌اند):**
- چه فایل‌ها، توابع، تست‌ها، migrations، docs، یا UI component هایی از
  کدی که داری ویرایش/اضافه/حذف می‌کنی **استفاده می‌کنند**؟
- با grep و reference search **همه‌ی** call sites، importها، subclassها،
  reference های مستقیم و غیرمستقیم را پیدا کن — نه فقط چند مورد اصلی.
- خصوصاً برای حذف یا rename: هیچ broken reference نباید باقی بماند.

**۳. وابستگی‌های cross-tier (بسیار مهم — هرگز فقط یک لایه را نبین):**

تسک شما ممکن است از backend، frontend، database، worker، یا هر tier
دیگری شروع شده باشد. ولی تغییرات تقریباً همیشه روی tier های دیگر هم
اثر می‌گذارند. **مستقل از اینکه تسک از کدام tier است**، این چک‌های دو
طرفه را همیشه انجام بده:

🔁 **اگر backend را تغییر دادی** (API، service، model، route):
  → frontend: کدام component/page/hook این endpoint یا data shape را
    مصرف می‌کند؟ type definition، state shape، error handling، loading
    state، form validation، URL routing همگی باید همگام شوند.
  → mobile/SDK/client library (اگر پروژه دارد): همان داستان frontend.
  → database: آیا migration لازم است؟ آیا rollback امن است؟
  → background workers: آیا event producer/consumer ها تحت تأثیرند؟
  → rate limit، auth، CORS، CSP: آیا رفتار جدید پشتیبانی می‌شود؟

🔁 **اگر frontend را تغییر دادی** (component، form، state، route):
  → backend: آیا endpoint جدید/تغییریافته لازم است؟ آیا data shape ای
    که ارسال می‌شود با schema سرور سازگار است؟
  → backend validation: آیا برای ورودی‌های جدید UI کافی است؟
  → permissions/RBAC: آیا feature جدید نیاز به role check جدید دارد؟
  → analytics/tracking: آیا event های جدید باید در backend log شوند؟
  → SEO/SSR: آیا تغییر route نیاز به sitemap/meta tags جدید دارد؟

🔁 **اگر database/migration را تغییر دادی**:
  → backend models (ORM، Pydantic، dataclasses) همگی به‌روزند؟
  → query های raw SQL یا ORM queries با schema جدید سازگارند؟
  → seed data، fixtures، factory functions تست‌ها به‌روزند؟
  → frontend: آیا data shape جدید در UI به‌درستی render می‌شود؟
  → rollback migration نوشته شده و امن است؟

🔁 **اگر API contract یا event schema را تغییر دادی** (REST، GraphQL،
   WebSocket، gRPC، Kafka، …):
  → OpenAPI/GraphQL schema/proto file آپدیت شد؟
  → همه‌ی consumer ها (client، subscriber، webhook، external API
    user) با version جدید سازگارند؟
  → backward compatibility حفظ شده یا migration path روشن است؟
  → versioning header/path اگر breaking change است؟

🔁 **اگر infrastructure یا config را تغییر دادی** (Dockerfile، CI، Render
   config، env، secrets):
  → README setup/installation section به‌روزه؟
  → `.env.example` با env vars جدید آپدیت شد؟
  → deploy script یا CI workflow هم تغییر کرد؟
  → docs/architecture یا diagram های infrastructure به‌روزند؟

⚠️ **هرگز فقط یک tier را تغییر نده و فرض کنی بقیه خودکار همگام می‌شوند.**
   حتی برای تغییرات به‌ظاهر «کوچک»، چک کن.

**۴. وابستگی‌های جانبی (artifacts که همیشه چک شوند):**

تغییرات کد همیشه روی این artifact ها اثر دارند. **همه را** بررسی و
به‌روز کن — مستندات اولویت **بالا** دارد چون فراموش‌شدنی‌ترین است.

  📝 **مستندات** (همیشه چک کن — حتی برای تغییر کوچک کد):
    - README.md (شرح، setup، نمونه‌های استفاده، badge ها)
    - CHANGELOG.md / RELEASE_NOTES.md
    - docs/ folder (architecture، API reference، user guides، runbooks)
    - inline docstrings/کامنت‌های توابع و کلاس‌های تغییریافته
    - OpenAPI/Swagger annotations، JSDoc/TSDoc
    - architecture diagrams (اگر component اضافه/حذف شد)
    - migration guides (اگر breaking change است)

  🌍 **مستندات کاربر**:
    - i18n files و translation keys
    - UI labels، tooltip ها، help text، error messages
    - in-app onboarding (اگر flow جدید است)

  🧪 **تست‌ها**:
    - unit tests (همه‌ی فایل‌های مرتبط — حتی اگر «بی‌ربط» به‌نظر می‌رسد)
    - integration tests
    - e2e tests (Playwright/Cypress/Selenium)
    - snapshot tests (اگر UI تغییر کرد)
    - contract tests (Pact یا مشابه)
    - performance benchmarks (اگر behavior performance-sensitive تغییر کرد)

  🧬 **type definitions و contracts**:
    - .d.ts files
    - Pydantic models، dataclasses
    - Protobuf/Avro/Thrift schemas
    - GraphQL schema definitions
    - JSON Schemas

  🏗 **infrastructure و config**:
    - Dockerfile، docker-compose.yml
    - Kubernetes manifests
    - Render/Vercel/Netlify config
    - GitHub Actions / GitLab CI workflows
    - environment templates (.env.example، .env.sample)
    - feature flags (LaunchDarkly، GrowthBook، config)

  📊 **monitoring و observability**:
    - logging keys (اگر اضافه/حذف شد، log parser ها هم به‌روز شوند)
    - metric names (Prometheus، Datadog)
    - tracing spans
    - alert rules و dashboards
    - error tracking (Sentry rules، groupings)

  🔐 **security**:
    - auth rules (rate limit، CORS، CSP، HSTS)
    - permissions/RBAC config
    - secrets rotation policies
    - audit log events (اگر action جدید اضافه شد)

  💾 **caches و serialization**:
    - cache keys و TTL (اگر data shape یا lifecycle تغییر کرد)
    - serializer formats (Redis، session storage)
    - browser storage (localStorage، IndexedDB schemas)

**قانون مطلق همگام‌سازی:**
- هر چیزی که در (۱)، (۲)، (۳)، یا (۴) شناسایی شد، در **همان workflow
  این تسک** همگام و به‌روز شود. هرگز برای بعد رها نکن.
- اگر یک فایل/تست/docs نسبت به تغییر شما عقب بماند، در بهترین حالت bug،
  در بدترین حالت مشکل امنیتی یا data corruption تولید می‌کند.
- تغییرات همگام‌سازی می‌توانند در commit جداگانه باشند (در همان task)،
  ولی نباید skip شوند یا به «refactor آینده» سپرده شوند.

**هرگز این جمله‌ها قابل قبول نیست:**
- ❌ «بعداً پیداش می‌کنم»
- ❌ «احتمالاً جای دیگه‌ای استفاده نمی‌شه»
- ❌ «این یه refactor جداگانه‌ست — out of scope»
- ❌ «فقط فایل‌های اصلی رو بررسی کردم»
- ❌ «حدس می‌زنم چیزی بهش وابسته نیست»
- ❌ «دامنه‌ی وابستگی‌ها رو خلاصه کردم» — هرگز خلاصه نکن
- ❌ «این task فقط backend است؛ frontend مشکل خودش» — هرگز
- ❌ «این task فقط frontend است؛ backend از قبل کار می‌کند» — هرگز ثابت نکرده
- ❌ «مستندات بعداً به‌روز می‌شن» — همیشه same-task همگام شوند
- ❌ «testها رو نگاه نکردم چون فقط یه تغییر کوچیک بود»

**در commit message یا PR description**، دامنهٔ وابستگی‌های شناسایی‌شده و
همگام‌شده را به‌طور explicit و **per-tier** بنویس. مثال:
```
Dependencies synced:
- upstream: User model schema, auth middleware
- downstream: 3 API endpoints, 5 frontend components, 12 tests
- cross-tier (backend → frontend): UserProfile.tsx, useUser.ts hook,
  api-types.ts (TS definitions)
- cross-tier (backend → infra): .env.example added NEW_AUTH_SCOPES
- side artifacts: OpenAPI spec, README API section, i18n keys for
  new errors, Sentry alert rule for new error code
```
اگر هیچ وابستگی پیدا نکردی در هر کدام از چهار جهت، صریحاً بنویس:
«بررسی شد — هیچ وابستگی upstream / downstream / cross-tier (backend↔
frontend↔db↔infra) / side شناسایی نشد» تا مشخص باشد بررسی **انجام شده**
نه اینکه فراموش شده.

📋 **مدیریت TO-DO برای اقدامات دستی کاربر (همیشه چک کن):**

⚠️ **هشدار بحرانی — قاعدهٔ ضد-فرار:** TO-DO فقط برای کارهایی است که
**واقعاً غیرممکن** برای agent است (نیاز به انسان مطلق)، نه برای کارهایی
که «بزرگ‌اند»، «وقت می‌برند»، یا «نیازمند fixture/setup» هستند. اگر یک
agent در یک سشن بیش از **۲۰٪ از تسک‌ها** را با TO-DO ببندد، یعنی از کار
فرار می‌کند — این الگو در سشن‌های قبلی **مشاهده** شده و الان ممنوع است.

✅ **فقط برای این موارد TO-DO بساز** (لیست بسته — هرچه خارج این لیست
ممنوع است):

  ۱. **Credential/secret که فقط کاربر دارد**:
     - تنظیم API key واقعی در پنل ادمین خارجی (Render، AWS، Stripe، …)
     - تأیید OAuth client روی console آن سرویس
     - paste کردن webhook secret که فقط بعد از ساخت در dashboard ظاهر می‌شود

  ۲. **Account/billing روی سرویس خارجی که کاربر باید عضو شود**:
     - ساخت account جدید روی Stripe/SendGrid/Twilio/Google Cloud
     - تأیید verification شماره یا ID
     - فعال‌سازی subscription پولی

  ۳. **داده/asset خصوصی که فقط کاربر دارد**:
     - آپلود لوگو/تصویر/فونت برند
     - paste کردن داده‌ای که در محل کار کاربر است
     - import داده‌ای که فقط روی device کاربر است

  ۴. **تصمیم سلیقه‌ای/حقوقی/کسب‌وکار**:
     - انتخاب رنگ‌بندی نهایی یا تم
     - متن دقیق Terms of Service / Privacy Policy
     - تعرفهٔ قیمت‌گذاری
     - نام نهایی برند یا دامنه

⛔ **هرگز TO-DO نکن برای** (لیست سیاه — هر چیزی که در این لیست است
**قابل اجرا** توسط agent است، حتی اگر بزرگ یا چندبخشی باشد):

  ❌ UI component / page / dashboard (هر فریم‌ورک: React, Vue, Angular,
     Svelte، حتی اگر معماری بزرگ دارد) — می‌توانی stub اولیه + state
     management + layout + استایل بسازی
  ❌ "نیازمند Google Drive / Stripe / Twilio API" — می‌توانی **client
     stub** با abstraction layer بسازی که با env var واقعی plug-in شود؛
     کد integration یعنی پیاده‌سازی، نه TO-DO
  ❌ "feature بزرگ، چند روز کار می‌برد" — اندازه دلیل defer نیست؛ کوچک
     شروع کن، iterate کن، در همین سشن کامل کن
  ❌ Celery / background worker / scheduler — یک task ساده + register
     می‌توانی بسازی
  ❌ Migration / model / schema — حتی اگر فیلد جدید نیاز دارد، اضافه کن
  ❌ REST endpoint / GraphQL resolver / WebSocket route — هرگز TO-DO
  ❌ test (unit/integration/e2e) — همیشه قابل نوشتن
  ❌ Documentation / README / API docs — همیشه قابل نوشتن
  ❌ Config file / .env.example / Dockerfile / CI workflow — همیشه قابل
     نوشتن
  ❌ "می‌توانستی .tsx ولی repo .jsx است" — از .jsx استفاده کن، TO-DO نکن
  ❌ "نیازمند فیلد X در مدل دیگر" — اضافه کن فیلد را، TO-DO نکن
  ❌ "تصمیم admin-vs-user-scoped" — پرامپت اولیه scope را معلوم کرده،
     یا با محتاطانه‌ترین تفسیر پیش برو
  ❌ "credential در production هنوز ست نیست" — این TO-DO ساده برای
     تنظیم env var است (مورد ۱ بالا)، نه دلیل برای defer کردن کد
  ❌ "نیازمند verification از کاربر" — اگر اقدام واقعی غیرممکن نیست،
     پیش برو
  ❌ هر چیزی که در یک کامنت `# TODO` معمولی نوشته می‌شد — این فایل
     TO-DO نیست، کامنت inline است

🔬 **قاعدهٔ «حداقل تلاش» قبل از TO-DO**: قبل از TO-DO کردن یک AC، **اثبات
کن** که قابل انجام نیست:

  ۱. آیا می‌توانم یک stub/placeholder بسازم که با env واقعی plug-in شود؟
     → اگر بله، بساز و TO-DO نکن
  ۲. آیا می‌توانم برای این بخش یک test (حتی mock-based) بنویسم؟
     → اگر بله، بنویس و TO-DO نکن
  ۳. آیا می‌توانم abstraction/interface را تعریف کنم، حتی اگر backend
     واقعی نیست؟ → اگر بله، تعریف کن و TO-DO نکن
  ۴. آیا فقط یک حالت سلیقه‌ای/decision کاربر در میان است؟
     → فقط آن یک decision را TO-DO کن، نه کل feature را

اگر یکی از این چهار راه‌حل ممکن بود ولی به TO-DO رفتی، **اعتبار شما از
بین می‌رود**.

📊 **آستانهٔ TO-DO per session**: در یک حلقهٔ اجرای N تسک، اگر بیشتر از
**۲۰٪** تسک‌ها فایل TO-DO ساختی، خودت در گزارش پایانی صریحاً اعلام کن:

  "⚠️ نسبت TO-DO من {K}/{N} = {%} است که از آستانهٔ ۲۰٪ بالاتر است.
   احتمالاً برخی از این TO-DO ها قابل اجرا بودند ولی من فرار کردم.
   لیست TO-DO ها را کاربر باید بازبینی کند که آیا واقعاً Manual-required
   بودند یا agent ضعیف کار کرده."

**یادآوری همیشگی:** اگر در آینده قابلیت‌های شما گسترش پیدا کرد و توانستید
یکی از موارد لیست سفید را خودکار انجام دهید (مثلاً managed credential
injection، یا integration پولی automate شود)، انجام دهید و TO-DO نسازید.
لیست سفید بسته است ولی **بسته از پایین** (می‌تواند کوچک‌تر شود اگر
قابلیت‌ها رشد کنند، ولی هرگز بزرگ‌تر نشود برای فرار).

**اگر هیچ بخش Manual-required نبود (تمام تسک Auto-capable است)**:
  → فایل TO-DO **نساز**. فولدر TO-DO/ باید پاک و معنادار بماند.
  → اگر برای این task از قبل `TO-DO/todo-task-{task_id_first_8}.md` بود
     (یعنی در run قبلی نیاز به دخالت کاربر بود ولی الان نه): فایل قدیمی
     را پاک کن و entry را از `TO-DO/_index.json` حذف کن.

**اگر بخش Manual-required دارد** (همه‌جانبه یا hybrid):
  1. فولدر TO-DO/ را در ریشه ریپو ایجاد کن اگر نیست
  2. فایل `TO-DO/todo-task-{task_id_first_8}.md` بساز با front-matter
     شامل: task_id, task_title, execution_priority, created_at,
     updated_at, status: "pending"
     و در بدنه: «چرا این فایل ساخته شد»، «وضعیت بخش‌های خودکار»
     (commit ها reference)، «کارهایی که باید انجام دهی» با اولویت
     بالا/متوسط/پایین به ترتیب، «وقتی این کارها را تمام کردی»
  3. `TO-DO/_index.json` را با **merge** آپدیت کن (نه overwrite):
     - فایل موجود را بخوان
     - entry های orphan (فایلشان پاک شده) را حذف کن
     - entry این task را اضافه/replace کن
     - بر اساس execution_priority صعودی مرتب کن
     - ساختار: `{"version":1, "generated_at": ISO, "total": N, "items": [...]}`
  4. این تغییرات TO-DO را در **همان commit کد** شامل کن (نه commit جداگانه)

⛔ **ممنوعات مطلق TO-DO**:
  ❌ ساختن TO-DO برای کاری که می‌توانستی خودت انجام دهی (شلوغی فولدر)
  ❌ overwrite کردن `TO-DO/_index.json` بدون merge (data loss)
  ❌ نگه‌داشتن entry هایی که فایل‌شان پاک شده (broken reference)
  ❌ فراموش کردن نوشتن «خروجی مورد انتظار» در هر آیتم TO-DO

این بخش الزامی است. حتی اگر فکر می‌کنی "این تسک کاملاً auto است و نیازی
به TO-DO نیست"، صریحاً در commit message یا report بنویس:
"بررسی شد — این تسک هیچ بخش Manual-required ندارد، TO-DO ساخته نشد."

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی
  هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.

🔁 **Commit + Push فوری per-task (بسیار مهم برای جریان کار صحیح):**

پس از اتمام پیاده‌سازی این تسک، **بلافاصله** commit کن و **همان موقع**
به default branch (main/master) push کن. سپس به تسک بعدی برو.

✓ چرا این قانون حیاتی است:
  - تسک‌های بعدی ممکن است به فایل‌ها/تغییراتی که این تسک ایجاد کرده
    نیاز داشته باشند. اگر push نکنی، `git pull` بعدی آن‌ها را نمی‌بیند.
  - جمع‌کردن تغییرات چند تسک منجر به conflict های بزرگ می‌شود.
  - اگر در میانه fail کنی، task های push شده ضایع نمی‌شوند.

⛔ ممنوع: "همه task ها را تمام می‌کنم بعد یک‌جا push می‌زنم"
⛔ ممنوع: branch جدا برای task — مستقیم به default branch
⛔ ممنوع: task بعدی بدون push کامل task قبلی

---
"""


def _normalize_locations(
    target_locations: Optional[List[Union[Dict[str, Any], str]]],
    legacy_target_files: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """ادغام target_locations جدید (dict) و target_files قدیمی (str) به ساختار یکسان."""
    out: List[Dict[str, Any]] = []
    if target_locations:
        for item in target_locations:
            if isinstance(item, str):
                out.append({"path": item})
            elif isinstance(item, dict) and item.get("path"):
                out.append({k: v for k, v in item.items() if v not in (None, "")})
    if legacy_target_files:
        existing = {o.get("path") for o in out}
        for p in legacy_target_files:
            if p and p not in existing:
                out.append({"path": p})
    return out


def _format_location(loc: Dict[str, Any]) -> str:
    """فرمت یک ردیف موقعیت با مسیر:خط، نام تابع/کلاس، و snippet کد."""
    path = (loc.get("path") or "").strip()
    if not path:
        return ""
    lines = (loc.get("lines") or loc.get("line_range") or "").strip()
    line_start = loc.get("line_start")
    line_end = loc.get("line_end")
    if not lines and line_start:
        lines = str(line_start) + (f"-{line_end}" if line_end and line_end != line_start else "")
    symbol = (loc.get("symbol") or loc.get("function") or loc.get("class") or "").strip()
    snippet = (loc.get("snippet") or loc.get("code_snippet") or "").strip()
    note = (loc.get("note") or loc.get("reason") or "").strip()

    label = f"`{path}"
    if lines:
        label += f":{lines}"
    label += "`"
    if symbol:
        label += f" — `{symbol}`"
    if note:
        label += f" — {note}"

    out = f"- {label}"
    if snippet:
        # detect language for fence
        lang = ""
        low = path.lower()
        if low.endswith((".ts", ".tsx")):
            lang = "tsx"
        elif low.endswith(".js") or low.endswith(".jsx"):
            lang = "jsx"
        elif low.endswith(".py"):
            lang = "python"
        elif low.endswith((".json",)):
            lang = "json"
        elif low.endswith((".sql",)):
            lang = "sql"
        elif low.endswith((".md",)):
            lang = "markdown"
        out += f"\n  ```{lang}\n  " + snippet.replace("\n", "\n  ") + "\n  ```"
    return out


def _format_related_files(related: List[Dict[str, Any]]) -> str:
    """فرمت لیست فایل‌های مرتبط با ذکر دلیل (imports / imported_by / calls / shares_state)."""
    lines: List[str] = []
    for r in related:
        if isinstance(r, str):
            lines.append(f"- `{r}`")
            continue
        path = (r.get("path") or "").strip()
        if not path:
            continue
        reason = (r.get("reason") or r.get("relation") or "").strip()
        ref_line = (r.get("at_line") or r.get("line") or "").strip() if isinstance(r.get("at_line") or r.get("line"), str) else r.get("at_line") or r.get("line")
        suffix = ""
        if ref_line:
            suffix += f" (سطر {ref_line})"
        if reason:
            lines.append(f"- `{path}`{suffix} — {reason}")
        else:
            lines.append(f"- `{path}`{suffix}")
    return "\n".join(lines)


def build_strong_prompt(
    *,
    title: str,
    user_goal: str = "",
    raw_user_request: str = "",  # 🆕 متن خام کاربر (verbatim) — هرگز خلاصه نشود
    description: str = "",
    proposed_action: str = "",
    context_snippet: str = "",
    target_files: Optional[List[str]] = None,
    target_locations: Optional[List[Union[Dict[str, Any], str]]] = None,
    related_files: Optional[List[Union[Dict[str, Any], str]]] = None,
    dependency_summary: str = "",
    tech_context: str = "",
    before_after_examples: Optional[List[Dict[str, str]]] = None,
    # 🔬 (Runtime Verify Stage 1) — AC می‌تواند str (قدیمی) یا dict (جدید) باشد
    acceptance_criteria: Optional[List[Any]] = None,
    steps: Optional[List[str]] = None,
    validation_commands: Optional[List[str]] = None,
    expected_output: str = "",
    risks: str = "",
    dependencies: Optional[List[str]] = None,
    type_: str = "other",
    priority: str = "medium",
    estimate: str = "medium",
) -> str:
    """ساخت پرامپت اجرایی با ساختار استاندارد و عمق بالا برای ابزارهای کدنویس خارجی.

    🆕 پارامتر raw_user_request (مهم):
      متن خام کاربر — اگر داده شود، **به‌صورت verbatim** در ابتدای پرامپت
      قرار می‌گیرد (هرگز خلاصه/تغییر نمی‌کند). این تضمین می‌کند URLs،
      آدرس‌ها، نام‌ها، کلمات کلیدی هرگز گم نشوند، حتی اگر AI ضعیف باشد.

    پارامترهای کلیدی:
    - target_locations: لیست dictهای {"path","lines","line_start","line_end","symbol","snippet","note"}
      جایگزین قوی‌تر برای target_files (که فقط مسیر می‌گیرد).
    - related_files: لیست dictهای {"path","reason","at_line"} — برای راهنمایی به فایل‌های اطراف
      که این تسک با آنها در ارتباط است (importها، callerها، state share).
    - dependency_summary: متن کوتاه دربارهٔ نقش این بخش در نقشهٔ وابستگی‌های پروژه.
    - tech_context: پشتهٔ فناوری/معماری مرتبط (مثل "Next.js 14 App Router + FastAPI + SQLAlchemy").
    - before_after_examples: لیست {"label","before","after"} — نمونه قبل/بعد کد.
    - validation_commands: دستورات shell که برای verify باید موفق اجرا شوند.
    """
    target_files = target_files or []
    acceptance_criteria = acceptance_criteria or []
    steps = steps or []
    dependencies = dependencies or []
    validation_commands = validation_commands or []
    before_after_examples = before_after_examples or []

    locations = _normalize_locations(target_locations, target_files)

    parts: List[str] = []

    # 🔔 (Reminder feature) — اگر type_=="reminder"، یک پرامپت کاملاً متفاوت
    # با لحن شخصی/یادآوری برمی‌گردانیم. این یادآوری برای انجام کاری توسط
    # خود کاربر است، نه دستورالعملی برای مدل کدنویس. ساختار:
    #   - بدون EXECUTOR_DISCLAIMER (آن متن برای مدل اجرایی است)
    #   - بدون target_locations / risks / validation_commands
    #   - چک‌لیست action items قابل تیک — هر AC به یک ردیف [ ] تبدیل می‌شود
    if (type_ or "").lower().strip() == "reminder":
        rem_parts: List[str] = []
        rem_parts.append(f"# 🔔 یادداشت یادآوری: {title.strip()}")
        rem_parts.append("")
        if raw_user_request and raw_user_request.strip():
            rem_parts.append("## 📝 متن کاربر (verbatim)")
            rem_parts.append(f"> {raw_user_request.strip()}")
            rem_parts.append("")
        if description and description.strip() and description.strip() != raw_user_request.strip():
            rem_parts.append("## 📌 شرح کوتاه")
            rem_parts.append(description.strip())
            rem_parts.append("")
        if acceptance_criteria:
            rem_parts.append("## ✅ چک‌لیست (قابل تیک)")
            rem_parts.append(
                "_هر آیتم را با تیک علامت بزن وقتی انجام شد. "
                "وقتی از تلگرام دکمهٔ آیتم را بزنی، در فرانت هم تیک می‌خورد و "
                "در یادآوری بعدی نمایش داده نمی‌شود._"
            )
            rem_parts.append("")
            for a in acceptance_criteria:
                # 🔬 (Runtime Verify Stage 1) — AC می‌تواند str یا dict باشد
                txt = (a.get("text") if isinstance(a, dict) else a) or ""
                txt = str(txt).strip()
                if txt:
                    rem_parts.append(f"- [ ] {txt}")
            rem_parts.append("")
        if user_goal and user_goal.strip():
            rem_parts.append("## 🎯 چرا این یادآوری مهم است")
            rem_parts.append(user_goal.strip())
            rem_parts.append("")
        rem_parts.append("---")
        rem_parts.append(
            "_این یک یادآوری شخصی است؛ از طریق تلگرام در زمان موعد "
            "به‌صورت inline checklist ارسال می‌شود._"
        )
        return "\n".join(rem_parts)

    # === ⚠️ DISCLAIMER (همیشه ابتدای پرامپت — قبل از هر چیز دیگر) ===
    parts.append(EXECUTOR_DISCLAIMER)

    # === 📥 درخواست خام کاربر (verbatim — هرگز خلاصه نشود) ===
    # این بخش حیاتی است: تضمین می‌کند URL ها، آدرس‌ها، نام‌ها، context کامل
    # کاربر در پرامپت نهایی می‌مانند، حتی اگر AI در ساختاردهی ضعیف باشد.
    if raw_user_request and raw_user_request.strip():
        parts.append(
            "## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)\n"
            "_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند. "
            "بخش‌های بعدی توسط AI ساختار داده شده‌اند و ممکن است ناقص باشند — این متن مرجع اصلی است.)_\n\n"
            "```\n"
            f"{raw_user_request.strip()}\n"
            "```"
        )

    parts.append(f"## 🎯 هدف (خلاصه ساختاریافته)\n{title.strip()}")

    # === موقعیت دقیق ===
    if locations:
        loc_lines = "\n".join(_format_location(l) for l in locations if l.get("path"))
        parts.append(
            "## 📍 موقعیت دقیق در پروژه\n"
            "_(file:line — symbol — snippet)_\n\n"
            f"{loc_lines}"
        )
    else:
        parts.append(
            "## 📍 موقعیت دقیق در پروژه\n"
            "_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_"
        )

    parts.append(
        f"## 🧭 هدف اصلی پروژه (از یادداشت کاربر)\n"
        f"{(user_goal or '(کاربر یادداشتی ثبت نکرده است)').strip()}"
    )

    if tech_context:
        parts.append(f"## 🧱 پشتهٔ فناوری و معماری\n{tech_context.strip()}")

    # === فایل‌های مرتبط (cross-references) ===
    related_norm: List[Dict[str, Any]] = []
    if related_files:
        for r in related_files:
            if isinstance(r, str):
                related_norm.append({"path": r})
            elif isinstance(r, dict):
                related_norm.append(r)
    if related_norm:
        parts.append(
            "## 🔗 فایل‌های مرتبط (Cross-references)\n"
            "_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_\n\n"
            f"{_format_related_files(related_norm)}"
        )

    if dependency_summary:
        parts.append(f"## 🌐 نقشهٔ وابستگی‌ها\n{dependency_summary.strip()}")

    # === Context ===
    ctx_block = description.strip()
    if context_snippet:
        ctx_block = f"{ctx_block}\n\n```\n{context_snippet.strip()}\n```"
    parts.append(
        f"## 🔍 Context و وضعیت فعلی\n{ctx_block or '_(وضعیت فعلی توسط مجری بررسی شود)_'}"
    )

    # === Acceptance criteria ===
    # 🔬 (Runtime Verify Stage 1) — AC می‌تواند str یا dict باشد
    # 🆕 (Phase 5 — فاز ۷) — AC ساختار غنی: behavior + acceptance_signal +
    # business_intent + alternative_implementations + non_goals +
    # false_positive_guard. هر AC اگر این فیلدها را داشته باشد، در پرامپت
    # به‌صورت block جداگانه render می‌شود تا verify بتواند رفتار-محور
    # judge کند نه نام-محور.
    ac_lines: List[str] = []
    for c in acceptance_criteria:
        if isinstance(c, dict):
            c_text = str(c.get("text") or "").strip()
            if not c_text:
                continue
            extras_parts: List[str] = []
            if c.get("behavior"):
                extras_parts.append(f"  📐 رفتار: {str(c['behavior'])[:300]}")
            if c.get("acceptance_signal"):
                extras_parts.append(f"  🎯 معیار قابل-verify: {str(c['acceptance_signal'])[:300]}")
            if c.get("business_intent"):
                extras_parts.append(f"  💼 چرا (intent): {str(c['business_intent'])[:200]}")
            if c.get("alternative_implementations"):
                alts = ", ".join(str(a)[:80] for a in c["alternative_implementations"][:5])
                extras_parts.append(f"  🔀 پیاده‌سازی‌های جایگزین قابل قبول: {alts}")
            if c.get("non_goals"):
                extras_parts.append(f"  ⛔ این AC شامل نیست: {str(c['non_goals'])[:200]}")
            if c.get("false_positive_guard"):
                extras_parts.append(f"  ⚠️ شواهد ضعیف (NOT done): {str(c['false_positive_guard'])[:200]}")
            ac_lines.append(f"- [ ] {c_text}")
            if extras_parts:
                ac_lines.extend(extras_parts)
        else:
            c_text = str(c).strip()
            if c_text:
                ac_lines.append(f"- [ ] {c_text}")
    standard_ac = [
        "- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)",
        "- [ ] linter بدون warning عبور می‌کند",
        "- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)",
    ]
    for s in standard_ac:
        if s not in ac_lines:
            ac_lines.append(s)
    parts.append(
        "## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور\n"
        "**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.\n"
        "verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.\n\n"
        + "\n".join(ac_lines)
    )

    # === Steps ===
    if not steps and proposed_action:
        steps = [proposed_action]
    if steps:
        step_lines = "\n".join(f"{i + 1}. {s.strip()}" for i, s in enumerate(steps) if s)
        parts.append(f"## 🪜 مراحل اجرایی پیشنهادی\n{step_lines}")
    else:
        parts.append(
            "## 🪜 مراحل اجرایی پیشنهادی\n_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_"
        )

    # === Before/after examples ===
    if before_after_examples:
        ex_chunks: List[str] = []
        for i, ex in enumerate(before_after_examples, 1):
            label = (ex.get("label") or f"نمونه {i}").strip()
            before = (ex.get("before") or "").strip()
            after = (ex.get("after") or "").strip()
            block = f"**{label}**"
            if before:
                block += f"\n\n_قبل:_\n```\n{before}\n```"
            if after:
                block += f"\n\n_بعد:_\n```\n{after}\n```"
            ex_chunks.append(block)
        parts.append("## 💡 نمونه‌های قبل/بعد\n" + "\n\n".join(ex_chunks))

    parts.append(
        f"## 📤 خروجی مورد انتظار\n{(expected_output or 'تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.').strip()}"
    )

    # === Validation commands ===
    if validation_commands:
        cmd_lines = "\n".join(f"- `{c.strip()}`" for c in validation_commands if c.strip())
        parts.append(f"## 🧪 دستورات اعتبارسنجی\n{cmd_lines}")

    parts.append(
        f"## ⚠️ ریسک‌ها و موارد احتیاط\n"
        f"{(risks or 'پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.').strip()}"
    )

    if dependencies:
        dep_lines = "\n".join(f"- {d}" for d in dependencies if d)
        parts.append(f"## 🔗 وابستگی‌های تسکی\n{dep_lines}")
    else:
        parts.append("## 🔗 وابستگی‌های تسکی\n_(مستقل)_")

    parts.append(
        f"## 🏷 دسته‌بندی\n- نوع: {type_}\n- اولویت: {priority}\n- تخمین زمان: {estimate}"
    )

    return "\n\n".join(parts)


def extract_target_files(prompt: str) -> List[str]:
    """استخراج فایل‌های موقعیت از یک پرامپت قوی (فقط path، حتی اگر `path:line` باشد).

    سازگار با هر دو فرمت:
      ## 📍 موقعیت دقیق در پروژه       (نسخهٔ جدید)
      ## 📍 موقعیت در پروژه               (نسخهٔ قدیمی)
    """
    import re

    files: List[str] = []
    match = re.search(
        r"##\s*\S*\s*موقعیت(?:\s+دقیق)?\s+در پروژه[^\n]*\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return files
    block = match.group(1)
    # فقط خط‌های اصلی (نه snippetهای داخل code-fence)
    in_fence = False
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = line.lstrip("-").strip()
        # اولین قطعه‌ای که داخل backtick است معمولاً path یا path:line است
        m = re.search(r"`([^`]+)`", line)
        if m:
            tok = m.group(1).strip()
        else:
            tok = line
        if not tok or tok.startswith("_") or tok.startswith("("):
            continue
        # تفکیک path:line — فقط path را نگه می‌داریم
        if ":" in tok:
            head, tail = tok.split(":", 1)
            # اگر دم رشته شامل "/" نیست → احتمالاً line range است → فقط head
            if "/" not in tail:
                tok = head
        # حذف symbol بعد از path (مثل `path` — `func`)
        tok = tok.split(" ")[0].strip("`").strip()
        if "/" in tok or "." in tok:
            files.append(tok)
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def extract_target_locations(prompt: str) -> List[Dict[str, Any]]:
    """استخراج موقعیت‌های دقیق (path + line range + symbol) از پرامپت — برای استفادهٔ verifier."""
    import re

    locations: List[Dict[str, Any]] = []
    match = re.search(
        r"##\s*\S*\s*موقعیت(?:\s+دقیق)?\s+در پروژه[^\n]*\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return locations
    block = match.group(1)
    in_fence = False
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.startswith("-"):
            continue
        rest = line.lstrip("-").strip()
        # اول backtick: path[:line]
        m = re.search(r"`([^`]+)`", rest)
        if not m:
            continue
        tok = m.group(1).strip()
        path = tok
        lines_str = ""
        if ":" in tok:
            head, tail = tok.split(":", 1)
            if "/" not in tail:
                path = head
                lines_str = tail
        # دوم backtick (اگر بود): symbol
        rest_after = rest[m.end():]
        sym = ""
        m2 = re.search(r"`([^`]+)`", rest_after)
        if m2:
            sym = m2.group(1).strip()
        if "/" in path or "." in path:
            loc = {"path": path}
            if lines_str:
                loc["lines"] = lines_str
            if sym:
                loc["symbol"] = sym
            locations.append(loc)
    # dedup
    seen = set()
    out: List[Dict[str, Any]] = []
    for l in locations:
        key = (l.get("path"), l.get("lines"), l.get("symbol"))
        if key not in seen:
            seen.add(key)
            out.append(l)
    return out


def extract_acceptance_criteria(prompt: str) -> List[str]:
    """استخراج معیارهای پذیرش از یک پرامپت قوی."""
    import re

    match = re.search(
        r"##\s*\S*\s*معیار پذیرش.*?\n(.+?)(?=\n##|\Z)",
        prompt,
        re.DOTALL,
    )
    if not match:
        return []
    block = match.group(1)
    items: List[str] = []
    for line in block.splitlines():
        s = line.strip()
        m = re.match(r"^-\s*\[[ xX]\]\s*(.+)$", s)
        if m:
            items.append(m.group(1).strip())
            continue
        m = re.match(r"^-\s+(.+)$", s)
        if m and not s.startswith("-_"):
            items.append(m.group(1).strip())
    return items
