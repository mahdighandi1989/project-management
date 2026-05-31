---
task_id: c230e259-b06d-4a4e-9c1d-ae260e4faffd
title: 'امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه '
type: other
priority: medium
execution_priority: 3000
status: pending
external_status: pending
verification_status: pending
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-11T04:42:02.468113+00:00'
updated_at: '2026-05-31T09:11:44.768807+00:00'
target_files:
- frontend/next.config.js
- frontend/src/app/login/page.tsx
- backend/app/main.py
- backend/app/core/config.py
- frontend/src/app/model-profiles/page.tsx
- backend/app/api/routes/analysis.py
- backend/app/api/routes/external_prompts.py
---

# امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه 

## Raw Idea

امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده و وابستگی ها را ریز به ریز کشف کن و شناسایی کن و زیر ساخت و سایر موارد لازم را پیاده سازی کن

## Prompt

## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

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


---

## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)
_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند.)_

```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده و وابستگی ها را ریز به ریز کشف کن و شناسایی کن و زیر ساخت و سایر موارد لازم را پیاده سازی کن
```

## 📋 چک‌لیست مراحل (7 مرحله)

این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**
وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.

- [ ] **مرحله 1: تحلیل وابستگی‌ها و شناسایی نقاط ورود برنامه برای اعمال احراز هویت** — این مرحله شامل بررسی کامل ساختار پروژه، شناسایی تمامی routeها، صفحات، API endpoints، middlewareها و کامپوننت‌هایی است که نیاز به محافظت دارند. باید مشخص شود کدام بخش‌ها عمومی (مثل صفحه لاگین) و کدام بخش‌ها خصوصی هستند. همچنین وابستگی‌های کتابخانه‌ای (مثل next-auth، firebase، supabase) و نحوه مدیریت 
- [ ] **مرحله 2: نصب و پیکربندی کتابخانه احراز هویت (مثلاً NextAuth.js) برای پشتیبانی از Google OAuth** — این مرحله شامل نصب کتابخانه NextAuth.js (یا معادل) و پیکربندی اولیه آن برای استفاده از Google OAuth provider است. باید فایل پیکربندی (مثلاً [...nextauth].ts) ایجاد شود و کلیدهای API از Google Cloud Console تنظیم شوند. همچنین باید endpointهای callback و sign-in/sign-out تعریف شوند. خارج از این مرحله:
- [ ] **مرحله 3: ایجاد صفحه لاگین سفارشی با دکمه ورود با گوگل** — این مرحله شامل ایجاد یک صفحه لاگین جدید (مثلاً /login) است که شامل یک دکمه 'ورود با گوگل' می‌باشد. این صفحه باید با استفاده از کامپوننت signIn از NextAuth.js کار کند. طراحی باید ساده و مینیمال باشد و با تم فعلی برنامه هماهنگ شود. خارج از این مرحله: تغییر در صفحه اصلی یا سایر صفحات، اعمال middleware.
- [ ] **مرحله 4: ایجاد middleware برای محافظت از تمام صفحات و APIهای خصوصی** — این مرحله شامل ایجاد یک فایل middleware.ts (یا middleware.js) در ریشه پروژه است که تمام درخواست‌ها به صفحات و APIهای خصوصی را بررسی می‌کند. اگر کاربر لاگین نکرده باشد، به صفحه لاگین هدایت می‌شود. باید مسیرهای عمومی (مثل /login، /api/auth/*، فایل‌های استاتیک) از این بررسی مستثنی شوند. خارج از این مرح
- [ ] **مرحله 5: اعمال محدودیت دسترسی بر اساس ایمیل‌های مجاز (لیست سفید)** — این مرحله شامل ایجاد یک مکانیزم برای محدود کردن دسترسی به برنامه بر اساس ایمیل کاربر است. باید یک لیست سفید از ایمیل‌های مجاز (مثلاً در فایل env یا دیتابیس) تعریف شود. در middleware یا در session callback، ایمیل کاربر لاگین‌شده با این لیست مقایسه می‌شود. اگر ایمیل در لیست نباشد، دسترسی رد می‌شود و ک
- [ ] **مرحله 6: به‌روزرسانی کامپوننت‌های UI برای نمایش وضعیت لاگین (header/navbar)** — این مرحله شامل به‌روزرسانی کامپوننت‌های عمومی UI (مثل header، navbar، sidebar) برای نمایش وضعیت لاگین کاربر است. اگر کاربر لاگین کرده باشد، نام و تصویر پروفایل او نمایش داده شود و دکمه خروج ظاهر شود. اگر لاگین نکرده باشد، دکمه ورود نمایش داده شود. باید از session از NextAuth.js استفاده شود. خارج از 
- [ ] **مرحله 7: تست جامع سناریوهای لاگین و دسترسی (بدون آسیب به منطق موجود)** — این مرحله شامل اجرای تست‌های دستی و خودکار برای اطمینان از عملکرد صحیح احراز هویت است. سناریوهای زیر تست می‌شوند: لاگین با ایمیل مجاز، لاگین با ایمیل غیرمجاز، دسترسی به صفحات خصوصی بدون لاگین، دسترسی به صفحات عمومی، خروج از برنامه، و بازگشت به صفحه لاگین. همچنین باید تست شود که منطق موجود برنامه (مث

---

# 🔹 مرحله 1: تحلیل وابستگی‌ها و شناسایی نقاط ورود برنامه برای اعمال احراز هویت

**Scope:** این مرحله شامل بررسی کامل ساختار پروژه، شناسایی تمامی routeها، صفحات، API endpoints، middlewareها و کامپوننت‌هایی است که نیاز به محافظت دارند. باید مشخص شود کدام بخش‌ها عمومی (مثل صفحه لاگین) و کدام بخش‌ها خصوصی هستند. همچنین وابستگی‌های کتابخانه‌ای (مثل next-auth، firebase، supabase) و نحوه مدیریت session فعلی بررسی می‌شود. خارج از این مرحله: پیاده‌سازی کد، تغییر منطق موجود، نصب کتابخانه. نکته حیاتی: این تحلیل باید مستند شود تا در مراحل بعدی دقیقاً مشخص باشد چه چیزی باید تغییر کند.
**Key terms:** routes, pages, API endpoints, middleware, session management, next-auth, firebase, supabase, login page, private pages

**بخش مربوط از متن کاربر:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده و وابستگی ها را ریز به ریز کشف کن و شناسایی کن
```

## 🎯 هدف (خلاصه ساختاریافته)
تحلیل وابستگی‌ها و نقاط ورود برای احراز هویت

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
تحلیل وابستگی‌ها و شناسایی نقاط ورود برنامه برای اعمال احراز هویت. این مرحله شامل بررسی کامل ساختار پروژه، شناسایی تمامی routeها، صفحات، API endpoints، middlewareها و کامپوننت‌هایی است که نیاز به محافظت دارند. باید مشخص شود کدام بخش‌ها عمومی (مثل صفحه لاگین) و کدام بخش‌ها خصوصی هستند. همچنین وابستگی‌های کتابخانه‌ای (مثل next-auth، firebase، supabase) و نحوه مدیریت session فعلی بررسی می‌شود. خارج از این مرحله: پیاده‌سازی کد، تغییر منطق موجود، نصب کتابخانه. نکته حیاتی: این تحلیل باید مستند شود تا در مراحل بعدی دقیقاً مشخص باشد چه چیزی باید تغییر کند.

--- بخش مربوط از درخواست اصلی کاربر ---
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده و وابستگی ها را ریز به ریز کشف کن و شناسایی کن

--- کلیدواژه‌ها ---
routes, pages, API endpoints, middleware, session management, next-auth, firebase, supabase, login page, private pages

شواهد در کد واقعی پروژه:
- backend/app/api/routes/analysis.py: تمامی endpointهای این فایل (POST /run، POST /run-stream، GET /reports، GET /reports/{report_id}، DELETE /reports/{report_id}، GET /reports/{report_id}/download، GET /profiles، GET /profiles/top، GET /profiles/{model_id}، GET /profiles/{model_id}/history، POST /profiles/compare، POST /profiles/refresh-rankings، POST /profiles/initialize، GET /schedule/{project_id}، PUT /schedule، DELETE /schedule/{project_id}، GET /stats) همگی بدون هیچ middleware احراز هویت هستند.
- backend/app/api/routes/external_prompts.py: از token-based auth (X-External-Token و X-Admin-Token) استفاده می‌کند اما این یک مکانیزم اختصاصی است نه احراز هویت کاربر.
- backend/app/api/routes/github_import.py: endpointهای POST /check و POST /import بدون احراز هویت هستند.
- backend/app/main.py: فایل اصلی FastAPI که routerها را mount می‌کند. هیچ middleware سراسری برای احراز هویت در آن دیده نمی‌شود.
- frontend/src/app/analysis/page.tsx, frontend/src/app/archive/page.tsx, frontend/src/app/creator/page.tsx, frontend/src/app/debate/page.tsx, frontend/src/app/diagrams/page.tsx: صفحات فرانت‌اند که همگی بدون محافظت هستند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. **مستندسازی تمامی routeهای بک‌اند**: در فایل backend/app/api/routes/analysis.py (خطوط 46-268 برای endpointهای تحلیل)، backend/app/api/routes/external_prompts.py (خطوط 129-340 برای endpointهای external)، backend/app/api/routes/github_import.py (خطوط 55-175 برای endpointهای GitHub)، backend/app/api/routes/model_profiles.py، backend/app/api/routes/models.py، backend/app/api/routes/orchestrator.py، backend/app/api/routes/oversight.py، backend/app/api/routes/project_health.py، backend/app/api/routes/project_journal.py، backend/app/api/routes/project_memory.py، backend/app/api/routes/render_logs.py، backend/app/api/routes/security_analysis.py، backend/app/api/routes/settings.py، backend/app/api/routes/simple_projects.py، backend/app/api/routes/system_prompts.py، backend/app/api/routes/unified_api.py — همه باید لیست شوند و مشخص شود عمومی یا خصوصی.
2. **مستندسازی تمامی صفحات فرانت‌اند**: frontend/src/app/analysis/page.tsx، frontend/src/app/archive/page.tsx، frontend/src/app

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: other
- اولویت: medium
- تخمین زمان: medium

---

# 🔹 مرحله 2: نصب و پیکربندی کتابخانه احراز هویت (مثلاً NextAuth.js) برای پشتیبانی از Google OAuth

**Scope:** این مرحله شامل نصب کتابخانه NextAuth.js (یا معادل) و پیکربندی اولیه آن برای استفاده از Google OAuth provider است. باید فایل پیکربندی (مثلاً [...nextauth].ts) ایجاد شود و کلیدهای API از Google Cloud Console تنظیم شوند. همچنین باید endpointهای callback و sign-in/sign-out تعریف شوند. خارج از این مرحله: تغییر در صفحات موجود، اعمال middleware، ذخیره session در دیتابیس. نکته حیاتی: باید از متغیرهای محیطی برای ذخیره کلیدها استفاده شود و هیچ کلیدی در کد hardcode نشود.
**Key terms:** NextAuth.js, Google OAuth, provider, [...nextauth].ts, callback, sign-in, sign-out, Google Cloud Console, environment variables

**بخش مربوط از متن کاربر:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند
```

## 🎯 هدف (خلاصه ساختاریافته)
نصب و پیکربندی NextAuth.js برای Google OAuth در فرانت‌اند

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/next.config.js:8-14` — `rewrites` — این rewrite تمام مسیرهای `/api/*` را به بک‌اند هدایت می‌کند. مسیر `/api
  ```jsx
  async rewrites() {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      return [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
        },
      ];
    },
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست نصب و پیکربندی کتابخانه احراز هویت (مثلاً NextAuth.js) برای پشتیبانی از Google OAuth را دارد. این مرحله شامل نصب کتابخانه NextAuth.js (یا معادل) و پیکربندی اولیه آن برای استفاده از Google OAuth provider است. باید فایل پیکربندی (مثلاً [...nextauth].ts) ایجاد شود و کلیدهای API از Google Cloud Console تنظیم شوند. همچنین باید endpointهای callback و sign-in/sign-out تعریف شوند. خارج از این مرحله: تغییر در صفحات موجود، اعمال middleware، ذخیره session در دیتابیس. نکته حیاتی: باید از متغیرهای محیطی برای ذخیره کلیدها استفاده شود و هیچ کلیدی در کد hardcode نشود. کاربر تأکید کرده: 'امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند'. کلیدواژه‌ها: NextAuth.js, Google OAuth, provider, [...nextauth].ts, callback, sign-in, sign-out, Google Cloud Console, environment variables. پروژه از Next.js 14 با ساختار `frontend/src/app` استفاده می‌کند (طبق `frontend/tsconfig.json` و `frontend/next.config.js`). فایل `frontend/next.config.js` در خط ۸-۱۴ یک `rewrite` برای `/api/:path*` به `http://localhost:8000/api/:path*` دارد که باید با endpointهای NextAuth.js هماهنگ شود. فایل `frontend/package.json` و `frontend/package-lock.json` نشان می‌دهند که NextAuth.js هنوز نصب نشده است. فایل `frontend/Dockerfile` از `node:20-alpine` استفاده می‌کند و نیاز به نصب وابستگی جدید دارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. نصب NextAuth.js در فرانت‌اند: `cd frontend && npm install next-auth@4`. 2. ایجاد فایل پیکربندی در `frontend/src/app/api/auth/[...nextauth]/route.ts` (طبق App Router Next.js 14). 3. در این فایل، provider Google OAuth را با clientId و clientSecret از متغیرهای محیطی `GOOGLE_CLIENT_ID` و `GOOGLE_CLIENT_SECRET` پیکربندی کن. 4. متغیر `NEXTAUTH_SECRET` را برای رمزنگاری session تنظیم کن. 5. متغیر `NEXTAUTH_URL` را به آدرس فرانت‌اند (مثلاً `http://localhost:3000`) تنظیم کن. 6. endpointهای callback به صورت خودکار توسط NextAuth.js در `/api/auth/callback/google` تعریف می‌شوند. 7. sign-in و sign-out از طریق `signIn('google')` و `signOut()` از کتابخانه `next-auth/react` انجام می‌شود. 8. در `frontend/.env.local` (که باید به `.gitignore` اضافه شود) کلیدها را ذخیره کن. 9. هیچ middleware یا تغییر در صفحات موجود در این مرحله انجام نشود. 10. اطمینان حاصل شود که `frontend/next.config.js` با مسیر `/api/auth/*` تداخل نداشته باشد (rewrite فعلی فقط `/api/:path*` را به backend می‌فرستد، اما `/api/auth/*` باید به NextAuth.js برسد).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: medium
- تخمین زمان: medium

---

# 🔹 مرحله 3: ایجاد صفحه لاگین سفارشی با دکمه ورود با گوگل

**Scope:** این مرحله شامل ایجاد یک صفحه لاگین جدید (مثلاً /login) است که شامل یک دکمه 'ورود با گوگل' می‌باشد. این صفحه باید با استفاده از کامپوننت signIn از NextAuth.js کار کند. طراحی باید ساده و مینیمال باشد و با تم فعلی برنامه هماهنگ شود. خارج از این مرحله: تغییر در صفحه اصلی یا سایر صفحات، اعمال middleware. نکته حیاتی: این صفحه باید تنها صفحه عمومی برنامه باشد و بقیه صفحات نیاز به احراز هویت داشته باشند.
**Key terms:** /login, signIn, Google button, NextAuth.js, custom login page

**بخش مربوط از متن کاربر:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد صفحه لاگین سفارشی با دکمه ورود با گوگل

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/login/page.tsx:1-50` — `LoginPage`
  ```tsx
  // فایل جدید - صفحه لاگین سفارشی
  import { signIn } from 'next-auth/react';
  
  export default function LoginPage() {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100">
        <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
          <h1 className="mb-6 text-center text-2xl font-bold text-gray-800">
            ورود به سامانه
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست ایجاد یک صفحه لاگین جدید (مثلاً /login) کرده است که شامل یک دکمه 'ورود با گوگل' می‌باشد. این صفحه باید با استفاده از کامپوننت signIn از NextAuth.js کار کند. طراحی باید ساده و مینیمال باشد و با تم فعلی برنامه هماهنگ شود. خارج از این مرحله: تغییر در صفحه اصلی یا سایر صفحات، اعمال middleware. نکته حیاتی: این صفحه باید تنها صفحه عمومی برنامه باشد و بقیه صفحات نیاز به احراز هویت داشته باشند.

بخش مربوط از درخواست اصلی کاربر: 'امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد'

کلیدواژه‌ها: /login, signIn, Google button, NextAuth.js, custom login page

شواهد در کد: پروژه از Next.js (frontend) و FastAPI (backend) استفاده می‌کند. فایل frontend/next.config.js (خط 1-15) و frontend/package.json (خط 1-30) نشان‌دهنده استفاده از Next.js 14 است. در frontend/package.json، هیچ وابستگی به next-auth وجود ندارد، بنابراین باید اضافه شود. backend/app/api/routes/external_prompts.py (خط 1-50) نشان‌دهنده وجود سیستم احراز هویت مبتنی بر توکن (X-External-Token) در بک‌اند است، اما این برای ابزارهای خارجی است و با لاگین کاربر نهایی تفاوت دارد. backend/app/core/config.py و backend/.env.example (خط 1-50) حاوی تنظیمات امنیتی (SECRET_KEY) و CORS هستند که برای پیکربندی NextAuth.js ضروری است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. نصب پکیج next-auth در فرانت‌اند: `npm install next-auth`
2. ایجاد فایل `frontend/src/app/api/auth/[...nextauth]/route.ts` برای پیکربندی NextAuth.js با provider گوگل. از متغیرهای محیطی `GOOGLE_CLIENT_ID` و `GOOGLE_CLIENT_SECRET` استفاده شود.
3. ایجاد فایل `frontend/src/app/login/page.tsx` به عنوان صفحه لاگین سفارشی. این صفحه شامل یک دکمه 'ورود با گوگل' است که با استفاده از کامپوننت `signIn('google')` از next-auth/react کار می‌کند. طراحی ساده و مینیمال با Tailwind CSS.
4. ایجاد یک SessionProvider در `frontend/src/app/layout.tsx` برای در دسترس قرار دادن سشن در کل برنامه.
5. ایجاد یک middleware در `frontend/src/middleware.ts` که مسیر `/login` را عمومی و بقیه مسیرها را نیازمند احراز هویت کند. از `getToken` از `next-auth/jwt` استفاده شود.
6. تنظیم متغیرهای محیطی `NEXTAUTH_SECRET` و `NEXTAUTH_URL` در فایل `.env.local` فرانت‌اند.
7. (اختیاری) در بک‌اند، یک endpoint جدید برای تایید توکن گوگل و ایجاد/به‌روزرسانی کاربر در دیتابیس ایجاد شود. این endpoint می‌تواند در `backend/app/api/routes/auth.py` (فایل جدید) قرار گیرد.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 4: ایجاد middleware برای محافظت از تمام صفحات و APIهای خصوصی

**Scope:** این مرحله شامل ایجاد یک فایل middleware.ts (یا middleware.js) در ریشه پروژه است که تمام درخواست‌ها به صفحات و APIهای خصوصی را بررسی می‌کند. اگر کاربر لاگین نکرده باشد، به صفحه لاگین هدایت می‌شود. باید مسیرهای عمومی (مثل /login، /api/auth/*، فایل‌های استاتیک) از این بررسی مستثنی شوند. خارج از این مرحله: تغییر در منطق صفحات یا APIها. نکته حیاتی: middleware باید با دقت پیاده‌سازی شود تا هیچ مسیر خصوصی بدون محافظت باقی نماند و همچنین مسیرهای عمومی به درستی مجاز شوند.
**Key terms:** middleware.ts, matcher, public routes, private routes, /login, /api/auth/*, static files

**بخش مربوط از متن کاربر:**
```
برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد middleware محافظت از صفحات و APIهای خصوصی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/next.config.js:1-15` — `nextConfig`
  ```jsx
  /** @type {import('next').NextConfig} */
  const nextConfig = {
    output: 'standalone',
    reactStrictMode: true,
    async rewrites() {
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست ایجاد یک middleware برای محافظت از تمام صفحات و APIهای خصوصی پروژه را دارد. این middleware باید در ریشه پروژه (فایل middleware.ts یا middleware.js) قرار گیرد و تمام درخواست‌ها به صفحات و APIهای خصوصی را بررسی کند. اگر کاربر لاگین نکرده باشد، به صفحه لاگین هدایت می‌شود. مسیرهای عمومی مثل /login، /api/auth/* و فایل‌های استاتیک باید از این بررسی مستثنی شوند. کاربر تأکید کرده که خارج از این مرحله، تغییری در منطق صفحات یا APIها نباید ایجاد شود. نکته حیاتی: middleware باید با دقت پیاده‌سازی شود تا هیچ مسیر خصوصی بدون محافظت باقی نماند و همچنین مسیرهای عمومی به درستی مجاز شوند. بخش مربوط از درخواست اصلی کاربر: «برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد». کلیدواژه‌ها: middleware.ts, matcher, public routes, private routes, /login, /api/auth/*, static files. در کد فعلی پروژه، فایل frontend/next.config.js (خط ۱-۱۵) وجود دارد که از rewrites برای پروکسی API به backend استفاده می‌کند. فایل frontend/tsconfig.json (خط ۱-۳۰) مسیرهای TypeScript را مشخص کرده است. فایل frontend/package.json (خط ۱-۳۰) وابستگی‌ها از جمله next@14.1.0 را نشان می‌دهد. فایل backend/app/api/routes/external_prompts.py (خط ۳۱-۴۶) مکانیزم احراز هویت با X-External-Token را نشان می‌دهد که می‌تواند الگویی برای middleware باشد. فایل backend/app/api/routes/github_import.py (خط ۴۵-۵۲) تابع get_effective_token را برای مدیریت توکن‌ها نشان می‌دهد. فایل backend/app/core/config.py (خط ۱-۲۰) تنظیمات امنیتی مانند SECRET_KEY را مدیریت می‌کند. فایل backend/.env.example (خط ۱-۵۰) متغیرهای محیطی از جمله SECRET_KEY و ACCESS_TOKEN_EXPIRE_MINUTES را مشخص کرده است. فایل backend/app/main.py (خط ۱-۳۰) نقطه ورود برنامه FastAPI است که می‌توان middleware در آن اضافه کرد. فایل frontend/Dockerfile (خط ۱-۴۰) نحوه build فرانت‌اند را نشان می‌دهد. فایل docker-compose.yml (خط ۱-۵۰) سرویس‌های backend و frontend را مشخص کرده است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل middleware.ts در ریشه پروژه frontend (frontend/middleware.ts) با استفاده از قابلیت Next.js Middleware. 2. تعریف matcher برای اعمال middleware روی تمام مسیرها به جز مسیرهای عمومی: /login, /api/auth/*, /_next/static/*, /favicon.ico, /public/*. 3. در middleware، بررسی وجود توکن احراز هویت در کوکی یا هدر درخواست. اگر توکن معتبر نبود، redirect به /login. 4. استفاده از NextResponse.redirect برای هدایت و NextResponse.next برای ادامه مسیر. 5. اطمینان از اینکه مسیر /login خودش از redirect محافظت نشود (لوپ بی‌نهایت). 6. اضافه کردن مسیرهای عمومی دیگر در صورت نیاز (مثلاً /api/public/*). 7. تست با شبیه‌سازی درخواست‌های بدون توکن و با توکن. 8. مستندسازی در README یا فایل جداگانه.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: small

---

# 🔹 مرحله 5: اعمال محدودیت دسترسی بر اساس ایمیل‌های مجاز (لیست سفید)

**Scope:** این مرحله شامل ایجاد یک مکانیزم برای محدود کردن دسترسی به برنامه بر اساس ایمیل کاربر است. باید یک لیست سفید از ایمیل‌های مجاز (مثلاً در فایل env یا دیتابیس) تعریف شود. در middleware یا در session callback، ایمیل کاربر لاگین‌شده با این لیست مقایسه می‌شود. اگر ایمیل در لیست نباشد، دسترسی رد می‌شود و کاربر به صفحه خطا یا لاگین هدایت می‌شود. خارج از این مرحله: مدیریت داینامیک لیست سفید (اضافه/حذف از طریق UI). نکته حیاتی: این مرحله باید با middleware هماهنگ شود تا دسترسی غیرمجاز در همان ابتدا مسدود شود.
**Key terms:** whitelist, allowed emails, session callback, middleware, access control, env, database

**بخش مربوط از متن کاربر:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

## 🎯 هدف (خلاصه ساختاریافته)
اعمال محدودیت دسترسی بر اساس لیست سفید ایمیل‌های مجاز

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/main.py:1-50` — `app (FastAPI instance)` — ورودی اصلی FastAPI — middleware جدید باید اینجا اضافه شود تا قبل از رسیدن به routeها اجرا شود.
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  
  app = FastAPI(title="AI Creator Engine", version="2.0.0")
  
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- `backend/app/core/config.py:1-30` — `Settings class`
  ```python
  from pydantic_settings import BaseSettings
  
  class Settings(BaseSettings):
      APP_NAME: str = "AI Creator Engine"
      DEBUG: bool = True
      ENVIRONMENT: str = "development"
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست اعمال محدودیت دسترسی به برنامه بر اساس ایمیل‌های مجاز (لیست سفید) را دارد. این مرحله شامل ایجاد یک مکانیزم برای محدود کردن دسترسی به برنامه بر اساس ایمیل کاربر است. باید یک لیست سفید از ایمیل‌های مجاز (مثلاً در فایل env یا دیتابیس) تعریف شود. در middleware یا در session callback، ایمیل کاربر لاگین‌شده با این لیست مقایسه می‌شود. اگر ایمیل در لیست نباشد، دسترسی رد می‌شود و کاربر به صفحه خطا یا لاگین هدایت می‌شود. خارج از این مرحله: مدیریت داینامیک لیست سفید (اضافه/حذف از طریق UI). نکته حیاتی: این مرحله باید با middleware هماهنگ شود تا دسترسی غیرمجاز در همان ابتدا مسدود شود. بخش مربوط از درخواست اصلی کاربر: "امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد". کلیدواژه‌ها: whitelist, allowed emails, session callback, middleware, access control, env, database. در کد فعلی پروژه، فایل backend/app/main.py (ورودی اصلی FastAPI) و backend/app/core/config.py (تنظیمات) و backend/app/api/routes/external_prompts.py (که از middleware توکن خارجی استفاده می‌کند) مرتبط هستند. همچنین frontend/src/app/... صفحات مختلفی دارند که نیاز به محافظت دارند. backend/app/core/database.py برای ذخیره لیست سفید در دیتابیس قابل استفاده است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در backend/app/core/config.py یک متغیر محیطی جدید به نام ALLOWED_EMAILS (رشته‌ای از ایمیل‌های مجاز جدا شده با کاما) اضافه کن. 2. یک middleware جدید در backend/app/main.py ایجاد کن که در هر درخواست، هدر Authorization یا session کاربر را بررسی کند. 3. در middleware، ایمیل کاربر استخراج‌شده از توکن JWT یا session با لیست ALLOWED_EMAILS مقایسه شود. 4. اگر ایمیل در لیست نبود، پاسخ 403 Forbidden با پیام "دسترسی غیرمجاز" برگردانده شود. 5. برای مسیرهای عمومی (مثل /login, /health) middleware نادیده گرفته شود. 6. در صورت نیاز به ذخیره داینامیک، یک مدل دیتابیس AllowedEmail در backend/app/models/ ایجاد و از backend/app/core/database.py استفاده شود. 7. در frontend، یک صفحه خطا (مثلاً /unauthorized) برای نمایش پیام دسترسی غیرمجاز اضافه شود. 8. session callback در backend/app/api/routes/external_prompts.py (که از X-External-Token استفاده می‌کند) به‌عنوان الگو برای استخراج ایمیل از session استفاده شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 6: به‌روزرسانی کامپوننت‌های UI برای نمایش وضعیت لاگین (header/navbar)

**Scope:** این مرحله شامل به‌روزرسانی کامپوننت‌های عمومی UI (مثل header، navbar، sidebar) برای نمایش وضعیت لاگین کاربر است. اگر کاربر لاگین کرده باشد، نام و تصویر پروفایل او نمایش داده شود و دکمه خروج ظاهر شود. اگر لاگین نکرده باشد، دکمه ورود نمایش داده شود. باید از session از NextAuth.js استفاده شود. خارج از این مرحله: تغییر در منطق صفحات اصلی. نکته حیاتی: این تغییرات باید در تمام صفحاتی که این کامپوننت‌ها استفاده می‌شوند، اعمال شود.
**Key terms:** header, navbar, sidebar, useSession, signOut, profile image, user name

**بخش مربوط از متن کاربر:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن وضعیت لاگین به هدر/نوار ناوبری عمومی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/model-profiles/page.tsx:1-6` — `imports and component definition` — این فایل از 'use client' استفاده می‌کند و باید useSession از next-auth/react به imports اضافه شود. هدر فعلی (خط 295-315) باید با AuthHeader جایگزین شود.
  ```tsx
  import { useState, useEffect } from 'react';
  import Link from 'next/link';
  
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  ```
- `frontend/src/app/model-profiles/page.tsx:295-315` — `header section`
  ```tsx
  <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
    <div className="max-w-7xl mx-auto px-4 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
به‌روزرسانی کامپوننت‌های UI عمومی (header، navbar، sidebar) برای نمایش وضعیت لاگین کاربر با استفاده از NextAuth.js. اگر کاربر لاگین کرده باشد، نام و تصویر پروفایل او نمایش داده شود و دکمه خروج (signOut) ظاهر شود. اگر لاگین نکرده باشد، دکمه ورود نمایش داده شود. این تغییرات باید در تمام صفحاتی که این کامپوننت‌ها استفاده می‌شوند، اعمال شود. خارج از این مرحله: تغییر در منطق صفحات اصلی. بخش مربوط از درخواست اصلی کاربر: 'امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد'. کلیدواژه‌ها: header, navbar, sidebar, useSession, signOut, profile image, user name. در کد فعلی، فایل frontend/src/app/model-profiles/page.tsx (خط 1-6) از 'use client' و useState/useEffect استفاده می‌کند اما هیچ اشاره‌ای به NextAuth یا useSession ندارد. فایل frontend/src/app/analysis/page.tsx و frontend/src/app/archive/page.tsx نیز وضعیت مشابهی دارند. فایل backend/app/main.py (خط 1-50) شامل middleware یا endpoint لاگین نیست. فایل backend/app/api/routes/settings.py و backend/app/api/routes/security_analysis.py نیز مرتبط با احراز هویت نیستند. فایل backend/app/services/oversight_upload_session.py و backend/app/services/scan_v5/scan_inspector_session.py نیز session مدیریت می‌کنند اما برای oversight هستند نه لاگین کاربر.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. نصب و پیکربندی NextAuth.js در frontend: ایجاد فایل frontend/src/app/api/auth/[...nextauth]/route.ts با provider جیمیل. 2. ایجاد SessionProvider در frontend/src/app/layout.tsx برای wrapping کل برنامه. 3. ایجاد کامپوننت AuthHeader در frontend/src/components/AuthHeader.tsx که از useSession استفاده کند: اگر session دارد، نام کاربر و تصویر پروفایل و دکمه signOut نمایش دهد، در غیر این صورت دکمه signIn نمایش دهد. 4. جایگزینی header/navbar/sidebar موجود در frontend/src/app/model-profiles/page.tsx (خط 295-315) و frontend/src/app/analysis/page.tsx و frontend/src/app/archive/page.tsx با AuthHeader. 5. افزودن middleware در frontend/src/middleware.ts برای redirect به صفحه لاگین در صورت عدم احراز هویت (برای حفاظت از صفحات برنامه). 6. تنظیم متغیرهای محیطی در frontend/.env.local: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, NEXTAUTH_SECRET, NEXTAUTH_URL. 7. به‌روزرسانی backend/app/main.py برای پذیرش token از frontend (اختیاری برای مرحله اول).

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: high
- تخمین زمان: medium

---

# 🔹 مرحله 7: تست جامع سناریوهای لاگین و دسترسی (بدون آسیب به منطق موجود)

**Scope:** این مرحله شامل اجرای تست‌های دستی و خودکار برای اطمینان از عملکرد صحیح احراز هویت است. سناریوهای زیر تست می‌شوند: لاگین با ایمیل مجاز، لاگین با ایمیل غیرمجاز، دسترسی به صفحات خصوصی بدون لاگین، دسترسی به صفحات عمومی، خروج از برنامه، و بازگشت به صفحه لاگین. همچنین باید تست شود که منطق موجود برنامه (مثل APIها، دیتابیس، محاسبات) تحت تأثیر قرار نگرفته است. خارج از این مرحله: رفع باگ‌های کشف‌شده (در مرحله بعدی انجام می‌شود). نکته حیاتی: تمام سناریوهای edge case باید پوشش داده شود.
**Key terms:** test scenarios, login, access control, edge cases, regression testing, API, database

**بخش مربوط از متن کاربر:**
```
فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده
```

## 🎯 هدف (خلاصه ساختاریافته)
تست جامع سناریوهای لاگین و دسترسی بدون آسیب به منطق موجود

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/api/routes/analysis.py:46-80` — `run_analysis` — این endpoint بدون احراز هویت است و به دیتابیس و سرویس‌های حساس دسترسی دارد. باید با middleware یا dependency محافظت شود.
  ```python
  @router.post("/run", response_model=AnalysisResponse)
  async def run_analysis(
      request: AnalysisRequest,
      background_tasks: BackgroundTasks
  ):
      """
      اجرای تحلیل جدید
      تحلیل کامل پروژه توسط مدل‌های انتخابی
      """
      try:
          analyzer = get_project_analyzer()
          analyzer.initialize()
  ```
- `backend/app/api/routes/external_prompts.py:129-`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک شامل اجرای تست‌های دستی و خودکار برای اطمینان از عملکرد صحیح احراز هویت است. سناریوهای زیر تست می‌شوند: لاگین با ایمیل مجاز، لاگین با ایمیل غیرمجاز، دسترسی به صفحات خصوصی بدون لاگین، دسترسی به صفحات عمومی، خروج از برنامه، و بازگشت به صفحه لاگین. همچنین باید تست شود که منطق موجود برنامه (مثل APIها، دیتابیس، محاسبات) تحت تأثیر قرار نگرفته است. خارج از این مرحله: رفع باگ‌های کشف‌شده (در مرحله بعدی انجام می‌شود). نکته حیاتی: تمام سناریوهای edge case باید پوشش داده شود. بخش مربوط از درخواست اصلی کاربر: 'فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده'. کلیدواژه‌ها: test scenarios, login, access control, edge cases, regression testing, API, database. شواهد در کد: در فایل backend/app/api/routes/analysis.py خطوط 46-80 endpoint POST /analysis/run وجود دارد که بدون احراز هویت اجرا می‌شود و به دیتابیس دسترسی دارد. همچنین در backend/app/api/routes/external_prompts.py خطوط 129-168 endpoint GET /external/prompts/next وجود دارد که با X-External-Token محافظت می‌شود. در backend/app/api/routes/github_import.py خطوط 55-91 endpoint POST /github/check وجود دارد که بدون لاگین قابل دسترسی است. در backend/app/main.py احتمالاً middleware احراز هویت وجود ندارد. در frontend/src/app/analysis/page.tsx و frontend/src/app/oversight/page.tsx صفحات خصوصی وجود دارند که باید با لاگین محافظت شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. بررسی فایل backend/app/main.py برای وجود middleware احراز هویت (مانند dependency injection برای توکن). 2. افزودن middleware یا decorator برای بررسی ایمیل مجاز در تمام endpointهای حساس مانند POST /analysis/run (analysis.py خط 46)، POST /github/check (github_import.py خط 55)، GET /external/prompts/next (external_prompts.py خط 129). 3. ایجاد یک سرویس احراز هویت ساده (مثلاً backend/app/services/auth_service.py) که ایمیل مجاز را از env var یا دیتابیس چک کند. 4. افزودن صفحه لاگین در frontend (مثلاً frontend/src/app/login/page.tsx) که ایمیل را گرفته و توکن ذخیره کند. 5. محافظت از صفحات خصوصی frontend مانند analysis/page.tsx و oversight/page.tsx با redirect به لاگین در صورت نبود توکن. 6. تست regression روی APIهای موجود (analysis, external_prompts, github_import) برای اطمینان از عدم تأثیر. 7. پوشش edge cases: لاگین با ایمیل خالی، ایمیل با فرمت نادرست، توکن منقضی، دسترسی همزمان چند کاربر.

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

---

## ✅ معیارهای پذیرش کلی (همهٔ مراحل)
- [ ] همهٔ مراحل بالا با موفقیت پیاده‌سازی شده‌اند
- [ ] تست‌های موجود pass می‌شوند
- [ ] هیچ regression رخ نداده

## Task Steps

### Step 1: تحلیل وابستگی‌ها و شناسایی نقاط ورود برنامه برای اعمال احراز هویت
**Status:** `pending` (0%)
**Scope:** این مرحله شامل بررسی کامل ساختار پروژه، شناسایی تمامی routeها، صفحات، API endpoints، middlewareها و کامپوننت‌هایی است که نیاز به محافظت دارند. باید مشخص شود کدام بخش‌ها عمومی (مثل صفحه لاگین) و کدام بخش‌ها خصوصی هستند. همچنین وابستگی‌های کتابخانه‌ای (مثل next-auth، firebase، supabase) و نحوه مدیریت session فعلی بررسی می‌شود. خارج از این مرحله: پیاده‌سازی کد، تغییر منطق موجود، نصب کتابخانه. نکته حیاتی: این تحلیل باید مستند شود تا در مراحل بعدی دقیقاً مشخص باشد چه چیزی باید تغییر کند.
**Excerpt:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده و وابستگی ها را ریز به ریز کشف کن و شناسایی کن
```

### Step 2: نصب و پیکربندی کتابخانه احراز هویت (مثلاً NextAuth.js) برای پشتیبانی از Google OAuth
**Status:** `pending` (0%)
**Scope:** این مرحله شامل نصب کتابخانه NextAuth.js (یا معادل) و پیکربندی اولیه آن برای استفاده از Google OAuth provider است. باید فایل پیکربندی (مثلاً [...nextauth].ts) ایجاد شود و کلیدهای API از Google Cloud Console تنظیم شوند. همچنین باید endpointهای callback و sign-in/sign-out تعریف شوند. خارج از این مرحله: تغییر در صفحات موجود، اعمال middleware، ذخیره session در دیتابیس. نکته حیاتی: باید از متغیرهای محیطی برای ذخیره کلیدها استفاده شود و هیچ کلیدی در کد hardcode نشود.
**Excerpt:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند
```

### Step 3: ایجاد صفحه لاگین سفارشی با دکمه ورود با گوگل
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک صفحه لاگین جدید (مثلاً /login) است که شامل یک دکمه 'ورود با گوگل' می‌باشد. این صفحه باید با استفاده از کامپوننت signIn از NextAuth.js کار کند. طراحی باید ساده و مینیمال باشد و با تم فعلی برنامه هماهنگ شود. خارج از این مرحله: تغییر در صفحه اصلی یا سایر صفحات، اعمال middleware. نکته حیاتی: این صفحه باید تنها صفحه عمومی برنامه باشد و بقیه صفحات نیاز به احراز هویت داشته باشند.
**Excerpt:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

### Step 4: ایجاد middleware برای محافظت از تمام صفحات و APIهای خصوصی
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک فایل middleware.ts (یا middleware.js) در ریشه پروژه است که تمام درخواست‌ها به صفحات و APIهای خصوصی را بررسی می‌کند. اگر کاربر لاگین نکرده باشد، به صفحه لاگین هدایت می‌شود. باید مسیرهای عمومی (مثل /login، /api/auth/*، فایل‌های استاتیک) از این بررسی مستثنی شوند. خارج از این مرحله: تغییر در منطق صفحات یا APIها. نکته حیاتی: middleware باید با دقت پیاده‌سازی شود تا هیچ مسیر خصوصی بدون محافظت باقی نماند و همچنین مسیرهای عمومی به درستی مجاز شوند.
**Excerpt:**
```
برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

### Step 5: اعمال محدودیت دسترسی بر اساس ایمیل‌های مجاز (لیست سفید)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل ایجاد یک مکانیزم برای محدود کردن دسترسی به برنامه بر اساس ایمیل کاربر است. باید یک لیست سفید از ایمیل‌های مجاز (مثلاً در فایل env یا دیتابیس) تعریف شود. در middleware یا در session callback، ایمیل کاربر لاگین‌شده با این لیست مقایسه می‌شود. اگر ایمیل در لیست نباشد، دسترسی رد می‌شود و کاربر به صفحه خطا یا لاگین هدایت می‌شود. خارج از این مرحله: مدیریت داینامیک لیست سفید (اضافه/حذف از طریق UI). نکته حیاتی: این مرحله باید با middleware هماهنگ شود تا دسترسی غیرمجاز در همان ابتدا مسدود شود.
**Excerpt:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

### Step 6: به‌روزرسانی کامپوننت‌های UI برای نمایش وضعیت لاگین (header/navbar)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل به‌روزرسانی کامپوننت‌های عمومی UI (مثل header، navbar، sidebar) برای نمایش وضعیت لاگین کاربر است. اگر کاربر لاگین کرده باشد، نام و تصویر پروفایل او نمایش داده شود و دکمه خروج ظاهر شود. اگر لاگین نکرده باشد، دکمه ورود نمایش داده شود. باید از session از NextAuth.js استفاده شود. خارج از این مرحله: تغییر در منطق صفحات اصلی. نکته حیاتی: این تغییرات باید در تمام صفحاتی که این کامپوننت‌ها استفاده می‌شوند، اعمال شود.
**Excerpt:**
```
امکان لاگین کردن توسط جیمیل برای حفاظت از عدم دسترسی افراد دیگر به صفحات برنامه ... صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد
```

### Step 7: تست جامع سناریوهای لاگین و دسترسی (بدون آسیب به منطق موجود)
**Status:** `pending` (0%)
**Scope:** این مرحله شامل اجرای تست‌های دستی و خودکار برای اطمینان از عملکرد صحیح احراز هویت است. سناریوهای زیر تست می‌شوند: لاگین با ایمیل مجاز، لاگین با ایمیل غیرمجاز، دسترسی به صفحات خصوصی بدون لاگین، دسترسی به صفحات عمومی، خروج از برنامه، و بازگشت به صفحه لاگین. همچنین باید تست شود که منطق موجود برنامه (مثل APIها، دیتابیس، محاسبات) تحت تأثیر قرار نگرفته است. خارج از این مرحله: رفع باگ‌های کشف‌شده (در مرحله بعدی انجام می‌شود). نکته حیاتی: تمام سناریوهای edge case باید پوشش داده شود.
**Excerpt:**
```
فقط بسیار دقت شود که این لاگین هیچ اسیبی به منطق و قسمت های دیگر نزند و صرفا عملکرد و ورد به برنامه منوط به لاگین شدن از طریق ایمیل مجاز باشد... بسیار با دقت بررسی های لازم را انجام بده
```
