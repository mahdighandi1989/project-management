---
task_id: dbc8e3f4-0a87-4baf-9e5d-f981b8fca488
title: تکمیل پیاده‌سازی Runtime Verification با ۴ Probe
type: refactor
priority: critical
execution_priority: 100
status: done
external_status: pending
verification_status: done
watched_id: 3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9
project: mahdighandi1989/project-management
created_at: '2026-05-16T08:24:51.349912+00:00'
updated_at: '2026-05-29T20:16:32.039550+00:00'
archived: true
archived_at: '2026-05-16T17:19:03.894966+00:00'
target_files:
- backend/app/services/verify_runtime/inspector_probe.py
- backend/app/services/verify_runtime/ac_schema.py
- backend/app/services/verify_runtime/runner.py
- backend/app/services/oversight_service.py
- backend/app/services/oversight_strong_prompt.py
- backend/app/services/verify_runtime/manual_probe.py
- frontend/src/app/oversight/page.tsx
- frontend/src/app/pro
- backend/app/services/oversight_verifier.py
- backend/app/services/verify_runtime/storage.py
- backend/app/api/routes/oversight.py
- backend/app/services/verify_runtime/base.py
- backend/app/services/verify_runtime/browser_pool.py
- backend/app/services/verify_runtime/safety.py
- backend/app/main.py
- backend/app/services/oversight_inspector_bridge.py
- backend/app/services/verify_runtime/auth_runner.py
- backend/app/services/verify
- backend/app/services/verify_runtime/code_aware_verifier.py
- backend/app/services/verify_runtime/navigation_helper.py
- backend/app/services/verify_runtime/backend_log_probe.py
- backend/app/services/scan_v5/comprehensive_inventory.py
- backend/app/services/scan_v5/dependency_analyzer.py
- backend/app/services/scan_v5/coherence_analyzer.py
- backend/app/services/notification_service.py
- backend/app/services/oversight
- backend/app/services/oversight_settings.py
- backend/app/services/verify_runtime/context_builder.py
- backend/app/services/verify_runtime/iterative_orchestrator.py
- backend/app/services/verify_runtime/code_content_searcher.py
- backend/app/services/verify_runtime/vision_helper.py
- backend/app/api/routes/analysis.py
---

# تکمیل پیاده‌سازی Runtime Verification با ۴ Probe

## Raw Idea

ایدهٔ خام
# 🔬 Runtime Verify Layer — verify مبتنی بر شواهد runtime (نه فقط grep کد)
## 🎯 هدف اصلی (یک جمله)
verify فعلی فقط کد را می‌خواند و حدس می‌زند؛ این layer جدید برای هر AC که
ماهیتش رفتاری است، **یک probe واقعی** اجرا می‌کند (Playwright برای UI،
HTTP برای API، pytest برای backend logic) و **شواهد runtime** (screenshot،
response JSON، pytest output) به verify می‌دهد. در نتیجه verify دیگر
false-positive («نشده» در حالی که شده) و false-negative («شده» در حالی که
نشده) نمی‌دهد.
---
## 📌 موقعیت دقیق در پروژه (فایل‌های مرتبط — مجری باید deep-read کند)
- `backend/app/services/oversight_verifier.py` — verify فعلی (grep + AI)
  → نقطهٔ یکپارچه‌سازی Stage 5
- `backend/app/services/oversight_strong_prompt.py` — تولید AC
  → نقطهٔ Stage 2 (AI verify_plan)
- `backend/app/services/oversight_service.py` — OversightTask + create_task
  → Stage 1 (schema migration)
- `backend/app/services/oversight_verify_pdf.py` — PDF فعلی
  → Stage 7 (embed evidence)
- `frontend/src/app/oversight/page.tsx` — UI تسک
  → Stage 8 (نمایش evidence)
- `frontend/src/app/projects/[id]/page.tsx` یا settings — تنظیمات watched
  → Stage 4 (base URLs)
- پوشهٔ جدید: `backend/app/services/verify_runtime/` — probe runners
- پوشهٔ جدید: `storage/verify_evidence/` — ذخیرهٔ screenshots/JSONs
---
## 🧠 معماری کلی (قبل از کد، این را بفهم)
### concept جدید: «verify_method» برای هر AC
هر AC الان فقط یک رشته است:
"وقتی روی دکمه X کلیک می‌کنم، مدال باز شود"

بعد از این feature، هر AC یک struct است:
```json
{
  "text": "وقتی روی دکمه X کلیک می‌کنم، مدال باز شود",
  "verify_method": "ui_interaction",
  "verify_plan": {
    "ui_steps": [
      {"action": "navigate", "url": "/oversight"},
      {"action": "wait_for_load_state", "state": "networkidle"},
      {"action": "click", "selector": "[data-testid='btn-x']"},
      {"action": "wait_for_selector", "selector": "[role='dialog']", "timeout_ms": 3000},
      {"action": "assert_visible", "selector": "[role='dialog']"}
    ]
  }
}
پنج نوع verify_method
static — کد grep (همان verify فعلی) — برای ACی مثل «فایل X وجود دارد»
ui_interaction — Playwright headless — برای ACی مثل «دکمه باز می‌شود»
api_response — HTTP request — برای ACی مثل «endpoint Y → 200 با field Z»
backend_test — pytest subprocess — برای ACی مثل «تست T pass شود»
manual_only — نمی‌توان خودکار تأیید کرد — verify فقط می‌گوید «نیاز به بازبینی دستی»
چه چیزی جایگزین شواهد grep می‌شود
verify فعلی به AI می‌گفت: «این کد را ببین، AC پاس می‌شود؟»
verify جدید می‌گوید: «این runtime evidence را ببین (screenshot، JSON، pytest log) — AC پاس می‌شود؟»

🪜 مراحل اجرایی (دقیقاً به این ترتیب — قبلی پیش‌نیاز بعدی است)
Stage 1 — Schema migration برای AC ساختاریافته
فایل‌ها: oversight_service.py, oversight_strong_prompt.py,
oversight_verifier.py, frontend/.../page.tsx

کاری که می‌شود:

OversightTask.acceptance_criteria از List[str] به List[Union[str, Dict]] تبدیل
helper _normalize_ac(ac) -> Dict[str, Any] که هم str هم dict را به
ساختار {text, verify_method, verify_plan, evidence_history} تبدیل می‌کند
backward compat: اگر AC قدیمی str است، verify_method="static" پیش‌فرض
در task_steps، هر step هم باید verify_method و verify_plan داشته باشد
migration یک‌بار در startup: روی همهٔ task های موجود _normalize_ac اجرا
شود (loop در _load_tasks)
Tests:

یک task با AC string قدیمی → بعد از load به ساختار جدید تبدیل شود
یک task با AC dict جدید → بدون تغییر باقی بماند
Stage 2 — تولید verify_plan توسط AI
فایل‌ها: oversight_strong_prompt.py, oversight_service.py
(در _idea_to_prompt_multi_pass), oversight_service.py (در system prompt)

کاری که می‌شود:

system prompt در idea_to_prompt گسترش یابد: AI علاوه بر AC، برای هر AC
باید verify_method و در صورت نیاز verify_plan تولید کند
چارچوب تصمیم برای AI:
AC شامل «کلیک، نمایش، صفحه، مودال، input» → ui_interaction
AC شامل «endpoint، API، status code، response» → api_response
AC شامل «test، pytest، unit test» → backend_test
AC شامل «فایل X وجود دارد، imported است» → static
AC مبهم یا ذهنی (مثل «ظاهر زیبا») → manual_only
prompt یک نمونهٔ کامل JSON برای هر نوع به AI می‌دهد (few-shot)
اگر AI نتوانست plan بدهد → fallback به static
Tests:

یک ایدهٔ UI («دکمه login کار کند») → AC با ui_interaction + ui_steps
یک ایدهٔ API («endpoint /users 200 بدهد») → AC با api_response
یک ایدهٔ ذهنی («طراحی شیک‌تر») → AC با manual_only
Stage 3 — Probe runners (هستهٔ کار)
پوشهٔ جدید: backend/app/services/verify_runtime/

فایل‌ها:

__init__.py
base.py — dataclass RuntimeProbeResult:
@dataclass
class RuntimeProbeResult:
    ac_id: str
    method: str  # static|ui|api|test|manual
    status: str  # passed|failed|error|skipped
    evidence: Dict[str, Any]  # {screenshot_paths, response_json, stdout, ...}
    duration_ms: int
    error_message: Optional[str]
    timestamp: str
static_probe.py — wrapper روی grep فعلی (همان منطق oversight_verifier)
ui_probe.py — استفاده از playwright.async_api:
async_playwright() → browser
برای هر step در ui_steps action متناظر را اجرا کن
screenshot قبل و بعد از هر action مهم (نام: <ac_id>_<step_idx>.png)
timeout per action: 10s پیش‌فرض
browser pool: max 3 concurrent
api_probe.py — استفاده از httpx.AsyncClient:
request اجرا
assert status_code (از plan)
assert response JSON schema (از plan: required fields)
response را به‌عنوان evidence ذخیره
test_probe.py — استفاده از subprocess:
pytest <test_path> --json-report --json-report-file=tmp.json
timeout: 120s
parse JSON output، success_count و failures
manual_probe.py — همیشه status="skipped" با پیام «نیاز به بازبینی دستی»
ابزارهای جدید nice-to-have:

runner.py — تابع run_probes_for_task(task, watched) -> List[RuntimeProbeResult]
برای هر AC method را تشخیص دهد
probe مناسب را call کند
با asyncio.Semaphore(3) همزمانی را محدود کند
timeout کلی task: 5 دقیقه
Tests:

mock playwright برای test UI probe (یا یک HTML ساده local serve)
httpbin برای test API probe
یک test pytest dummy برای test_probe
Stage 4 — Base URLs و config
فایل‌ها: oversight_service.py (WatchedProject),
frontend/src/app/projects/[id]/page.tsx یا settings UI

کاری که می‌شود:

اضافه کردن فیلدها به WatchedProject:
frontend_base_url: Optional[str] — مثلاً https://ai-creator-frontend.onrender.com
backend_base_url: Optional[str] — مثلاً https://ai-creator-backend.onrender.com
runtime_auth: Optional[Dict] — {type: "cookie"|"bearer", value: str}
در UI: یک section در تنظیمات پروژه:
input URL فرانت
input URL بک‌اند
dropdown نوع احراز هویت + input مقدار
دکمه «تست اتصال» (یک ping به فرانت + یک GET به backend health)
اگر URL تنظیم نشده → probe های ui/api همگی status="skipped" با
پیام «base URL تنظیم نشده»
Tests:

تست اتصال موفق + ناموفق
ذخیره و بارگذاری config
Stage 5 — یکپارچه‌سازی با verify_task
فایل: oversight_verifier.py

کاری که می‌شود:

در ابتدای verify_task (یا قبل از فراخوانی AI):
runtime_results = await run_probes_for_task(task, watched)
(با asyncio.wait_for timeout کلی)
هر probe که شکست خورد → log + continue (verify ادامه دهد)
results را به یک متن خوانا تبدیل کن:
## شواهد Runtime
### AC1: «وقتی روی دکمه X کلیک می‌کنم، مدال باز شود»
- method: ui_interaction
- status: ✅ passed
- evidence: screenshots/<task_id>/<run_id>/ac1_step3.png
- duration: 850ms
- مشاهدات: مدال [role=dialog] در 240ms ظاهر شد
### AC2: «GET /api/users → 200 با field email»
- method: api_response  
- status: ❌ failed
- actual_status: 500
- error: "Internal Server Error"
این متن را به‌عنوان بخش جدید در prompt verify اضافه کن
system prompt به AI: «شواهد runtime بالاتر از تحلیل کد است. اگر
runtime می‌گوید failed، حتی اگر کد درست به نظر برسد، AC پاس نشده.»
پس از AI، اگر برای یک AC هم runtime ✅ و هم AI گفت done → done قطعی
اگر runtime ❌ ولی AI گفت done → AI override کن به not_done (با هشدار log)
اگر runtime ✅ ولی AI گفت not_done → AI override کن به done
Tests:

verify_task با task که همهٔ probe ها pass شدند → status=done
verify_task با probe failed → AI override
verify_task با probe error (timeout) → fallback به فقط AI
Stage 6 — ذخیره‌سازی evidence
فایل: verify_runtime/storage.py

کاری که می‌شود:

ساختار:
storage/verify_evidence/
  <task_id>/
    <run_id>/
      ac1_step1.png
      ac1_step2.png
      ac2_response.json
      ac3_pytest.json
      manifest.json   # links همهٔ evidence ها
cleanup policy: نگه‌داری فقط 5 run آخر هر task
endpoint جدید: GET /api/oversight/tasks/{id}/evidence/{run_id}/<path>
→ serve فایل (با authorization)
size limit: 50MB per run؛ اگر بیشتر شد، screenshots را به JPEG q=70 کم کن
Stage 7 — PDF و Telegram (embed evidence)
فایل‌ها: oversight_verify_pdf.py, notification_service.py

کاری که می‌شود:

در PDF، یک section جدید «📷 شواهد Runtime»:
برای هر AC، یک card با:
متن AC
method badge (UI / API / Test)
status badge
برای UI: تصویر screenshot inline
برای API: JSON پاسخ (truncated به 500 byte) در <pre>
برای Test: stdout pytest (truncated)
در پیام تلگرام: اگر هر probe failed بود، یک خلاصه:
❌ شواهد runtime:
  • AC1 ui_interaction: passed (240ms)
  • AC2 api_response: failed (status 500)
  • AC3 backend_test: passed (3 tests)
📎 جزئیات کامل در PDF پیوست
Stage 8 — Frontend UI (نمایش evidence)
فایل: frontend/src/app/oversight/page.tsx

کاری که می‌شود:

در مودال جزئیات تسک، section جدید «🔬 آخرین verify runtime»:
برای هر AC: row با method icon + status + دکمهٔ «مشاهدهٔ evidence»
کلیک روی دکمه → مودال modal دوم با:
برای UI: gallery screenshot ها (lightbox)
برای API: JSON formatted با syntax highlight
برای Test: terminal-style block با stdout
دکمهٔ جدید «🔬 Verify با Runtime» (متفاوت از verify عادی):
این یکی شامل probe ها است (کندتر)
verify عادی بدون probe می‌ماند برای سرعت
در تنظیمات پروژه: section «Runtime Verify» با URLها و auth
Stage 9 — Performance، safety، edge cases
کاری که می‌شود:

Playwright browser process را در lifespan FastAPI start کن (شاره شده)
→ بعد از 5 دقیقه idle، آن را kill کن
per-task timeout کلی: 5 دقیقه
per-probe timeout: ui=30s, api=10s, test=120s
Semaphore: حداکثر 3 probe موازی برای یک task
اگر runtime در محیط Render (production) فعال نیست (مثلاً playwright
install نشده) → graceful degrade به فقط static (با warning)
circuit breaker: اگر 3 task پشت‌سرهم probe error دادند، runtime را
برای 10 دقیقه disable کن
environment flag: RUNTIME_VERIFY_ENABLED=true|false در .env
Stage 10 — Tests و validation
کاری که می‌شود:

unit tests:
test_static_probe.py — grep درست
test_ui_probe.py — با یک HTML server محلی
test_api_probe.py — با httpbin
test_test_probe.py — با pytest dummy
test_runner.py — orchestration
test_runtime_integration.py — verify_task با probe ها end-to-end
یک «known-good» fixture: task ساده که همه‌چیز pass می‌شود
یک «known-bad» fixture: task که هر probe باید fail شود
✅ معیارهای پذیرش کلی
عملکردی
not done
AC با verify_method=static همان رفتار قبلی verify را دارد (no regression)
not done
AC با verify_method=ui_interaction: playwright headless browser باز
می‌کند، steps را اجرا می‌کند، screenshot می‌گیرد، نتیجه برمی‌گرداند
not done
AC با verify_method=api_response: HTTP request می‌رود، status + شِما
چک می‌شود
not done
AC با verify_method=backend_test: pytest در subprocess با timeout
اجرا می‌شود
not done
AC با verify_method=manual_only: skipped با پیام واضح
not done
هر probe که error داد، verify ادامه می‌دهد (نه crash)
not done
base URL ها قابل تنظیم per project
not done
evidence فایل‌ها روی disk ذخیره می‌شوند، با cleanup policy
not done
PDF و Telegram message شواهد را embed می‌کنند
not done
Frontend modal جدید برای drill-down evidence
کیفی
not done
type-check (mypy + tsc) بدون error
not done
هیچ test موجود fail نمی‌شود
not done
محیط production (Render) با RUNTIME_VERIFY_ENABLED=false کاملاً
مثل قبل کار می‌کند (graceful disable)
not done
هیچ probe که فقط برای یک AC شکست خورد، کل verify را crash نکند
کنترل کیفیت verify
not done
روی یک تسک "known-good" (همه AC ها واقعاً پاس شده‌اند) →
verify=done
not done
روی یک تسک "known-bad" (UI AC شکست خورده) → AI نمی‌تواند آن را
done اعلام کند (runtime override)
not done
روی یک تسک با کد درست ولی deploy نشده → runtime می‌گوید fail
(چون probe می‌رود به URL واقعی، نه به کد محلی)
⚠️ ریسک‌ها و موارد احتیاط
Playwright چاق است (~300MB browser binaries). در Render production
ممکن است image size محدود باشد. → یک flag برای enable/disable در
.env، در production فعلاً فقط static + API + test (نه UI)
محیط Render سرور headless است — Playwright headless باید کار کند
ولی X server نمی‌خواهد. تست در staging قبل از production.
Authentication: اگر فرانت login می‌خواهد، probe باید login session
داشته باشد. در config، cookie یا bearer token ذخیره می‌شود (encrypted).
timing race: UI probe ممکن است قبل از hydrate Next.js کلیک کند.
باید wait_for_load_state('networkidle') در هر navigate.
pytest در subprocess — اگر تست اصلی پروژه طولانی است (>2 دقیقه)،
نباید کل verify را block کند. → فقط تست‌های مارک‌شده با
@pytest.mark.verify اجرا شوند، نه کل suite.
evidence disk usage — cleanup policy جدی، وگرنه ظرف چند روز
gigabyteها screenshot جمع می‌شود.
AI override conflict — اگر runtime ✅ و کد بد است (مثلاً deploy
نشده، کد staging تست شده)، AI نباید gaslight شود. → policy روشن:
«اگر runtime ✅ → AC done مگر AI شواهد بسیار قوی برعکس داشته باشد»
🧪 دستورات اعتبارسنجی (Validation Commands)
# backend lint + type
cd backend && python -m ruff check . && python -m mypy app/services/verify_runtime/

# backend unit tests
cd backend && pytest app/services/verify_runtime/ -v

# integration test
cd backend && pytest tests/integration/test_runtime_verify.py -v

# frontend
cd frontend && npx tsc --noEmit && npm run build

# manual smoke (روی production staging):
#   1. یک تسک بساز با AC «GET /api/oversight/status → 200»
#   2. روی frontend «🔬 Verify با Runtime» را بزن
#   3. PDF دریافتی باید JSON پاسخ /status را در evidence نشان بدهد
📦 ترتیب کامیت‌ها (foundation → core → integration → tests)
feat(verify): schema migration برای AC ساختاریافته (Stage 1)
feat(verify): تولید verify_plan توسط AI در idea_to_prompt (Stage 2)
feat(verify): پایهٔ probe runners (static + base.py) (Stage 3a)
feat(verify): UI probe با Playwright (Stage 3b)
feat(verify): API probe + Test probe (Stage 3c, 3d)
feat(verify): runner + semaphore + timeouts (Stage 3e)
feat(verify): base URLs و auth در WatchedProject (Stage 4)
feat(verify): ادغام probe ها در verify_task (Stage 5)
feat(verify): evidence storage + cleanup (Stage 6)
feat(verify): embed evidence در PDF + Telegram (Stage 7)
feat(verify): UI evidence viewer در frontend (Stage 8)
feat(verify): browser pool، circuit breaker، env flag (Stage 9)
test(verify): unit + integration tests (Stage 10)
هر کامیت باید روی master سبز باشد. اگر یک stage حجمی است، آن را به دو
کامیت بشکن — هیچ stage نباید بیش از یک هفته کار باشد.

🚫 آنچه خارج از scope این feature است
بازنویسی verifier فعلی (فقط extension است)
visual regression testing (screenshot diff) — می‌توان در feature بعدی
load testing — این یک stress test نیست
security scanning (SAST/DAST) — feature جداگانه
mobile UI testing — فقط desktop browser
multi-environment matrix testing — فقط یک base URL در آنِ واحد
-------------------------------------------------
# 🎯 پرامپت Phase 1 — اتصال Inspector Probe به verify جدید + ضمیمه‌ی تلگرامی
## هدف
ساخت یک probe جدید به اسم inspector_probe که به‌صورت خودکار (بدون
مداخله کاربر) صفحه دیپلوی‌شده پروژه را با Playwright سرور-سایدی باز
می‌کند، navigate / click می‌کند، screenshot می‌گیرد، console و backend
logs را جمع می‌کند، با Vision AI screenshot ها را تحلیل می‌کند و
نتیجه را به‌عنوان probe evidence در گزارش verify بازمی‌گرداند.
همزمان، تمام مراحل را در یک inspector_session جدید با عنوان
«🤖 auto-verify · …» ذخیره می‌کند تا کاربر بتواند از تب بازرس ویژه
آن را مرور کند. پس از تمام شدن verify و تولید followup prompt، یک
بسته‌ی کامل به تلگرام ارسال می‌شود (گزارش متنی + screenshot ها +
پرامپت بروز) و **پس از موفقیت ارسال، screenshot ها از دیسک حذف
می‌شوند** تا حافظه‌ی سرور همیشه کم بماند.
## این برای چه کاری استفاده می‌شود
الان وقتی verify کامل زده می‌شود، runtime probes موجود اکثراً skip/error
می‌شوند چون نیاز به runtime_repo_path دارند. هدف inspector_probe:
- شواهد بصری واقعی از صفحه deployed جمع کند
- console errors و backend logs همزمان را ضبط کند
- Vision AI متن/المنت‌های UI/error overlay را از screenshot استخراج کند
- این شواهد را به AI verifier بدهد تا تصمیم بهتر بگیرد
- خروجی قابل مرور توسط انسان از تب بازرس ویژه ارائه دهد
- screenshot ها را در تلگرام به‌عنوان مدرک ماندگار آرشیو کند
- حافظه‌ی سرور را پاک نگه دارد (پاک کردن خودکار پس از تلگرام)
## محدودیت‌های Phase 1
✅ navigate به URL
✅ click روی selector
✅ screenshot (ذخیره روی دیسک، نه base64 در DB)
✅ Vision AI تحلیل screenshot (با fallback chain)
✅ console log capture
✅ backend log correlation
✅ ضمیمه‌ی تلگرامی + cleanup
✅ TTL cleanup خودکار برای orphan screenshots
❌ fill / submit / wait → Phase 2
❌ login / auth → Phase 3
❌ multi-step complex sequences → Phase 2
---
## معماری ذخیره‌سازی screenshot
**روی دیسک، نه DB:**
- مسیر:
  storage/oversight/runtime_evidence/{task_id}/{run_id}/{ac_id}/{label}.png
- مثلاً:
  storage/oversight/runtime_evidence/task_abc/run_xyz/ac01_h/after_navigate.png
**در DB (inspector_message.extra_data) فقط:**
- path نسبی به فایل
- label
- vision_description (متن استخراج‌شده — این مهم‌ترین artifact است)
- timestamp
**در evidence گزارش verify:**
- لیست screenshots با path + vision_description
- بعد از ارسال تلگرام، path nullable می‌شود ولی vision_description می‌ماند
---
## Vision Fallback Chain (مهم)
برای هر screenshot، به این ترتیب تلاش کن:
**1. Vision موجود در سیستم (همان منطق تب بازرسی):**
- describe_screenshot_with_vision() در
  backend/app/services/oversight_inspector_bridge.py:44
- این تابع از مدل‌های multimodal (OpenAI GPT-4V / Anthropic Claude
  Vision / Gemini Pro Vision) استفاده می‌کند بسته به اینکه کدام
  API key موجود است
- خروجی: {scene, ocr_text, ui_elements, error_signals, layout_hints}
**2. اگر مرحله 1 خطا داد یا API key نبود → fallback به verify model:**
- مدل verify (مثل deepseek-chat) text-only است؛ نمی‌تواند تصویر را ببیند
- ولی می‌تواند روی **متن استخراج‌شده موجود** کار کند:
  - HTML content صفحه (از iframe contentDocument)
  - console logs
  - backend logs
  - URL
- یک پرامپت ساده: «بر اساس این لاگ‌ها و HTML، چه چیزی روی صفحه دیده می‌شد؟»
- این خروجی هم در vision_description ذخیره می‌شود (با علامتگذاری
  source="fallback_text_only")
**3. اگر هر دو شکست خوردند → فقط screenshot path ذخیره می‌شود:**
- vision_description = None
- probe بدون این فیلد ادامه می‌دهد (graceful degrade)
این منطق fallback را در یک تابع helper مستقل ذخیره کن (مثلاً
backend/app/services/verify_runtime/vision_helper.py) تا قابل reuse باشد.
---
## فایل‌ها و نقاط ادغام
### Backend — فایل‌های جدید
- backend/app/services/verify_runtime/inspector_probe.py
- backend/app/services/verify_runtime/vision_helper.py
  (شامل fallback chain)
### Backend — تغییرات
- backend/app/services/verify_runtime/base.py:
  افزودن فیلد inspector_session_id: Optional[int] = None به ProbeContext
- backend/app/services/verify_runtime/runner.py (خط 92-126):
  در _run_single_probe، برای method=ui_interaction:
  - اگر verify_plan.ui_steps لیستی با ≥3 step واقعی (نه فقط navigate
    + screenshot) دارد → run_ui_probe موجود
  - در غیر این صورت → run_inspector_probe جدید
  این dispatch داخل runner انجام می‌شود تا AI enricher نیازی به
  تغییر نداشته باشد.
- backend/app/services/oversight_verifier.py (خط 988-1063):
  در حین runtime probes block:
  1. قبل از run_probes_for_acs، یک InspectorSession موقت بساز:
     - title: «🤖 auto-verify · {task.title[:50]} · {timestamp}»
     - project_id: همان repo_full_name مشابه manual inspector
     - status: "active"
  2. session_id را در ProbeContext قرار بده
  3. probe ها اجرا می‌شوند
  4. پس از تمام شدن، session را archive کن
- backend/app/services/oversight_verifier.py (تابع
  _send_verify_notification_bg در حدود خط 1762):
  بسته‌ی تلگرامی توسعه پیدا کند:
  - علاوه بر متن گزارش که الان می‌فرستد
  - اگر runtime_probes شامل screenshots با path معتبر است:
    * تا حداکثر 5 screenshot را پیوست کن (با caption =
      vision_description یا probe ac_text)
    * استفاده از send_photo یا send_media_group بسته به تعداد
  - اگر followup_prompt تولید شده، فایل متنی .md از آن هم پیوست شود
    (یا در پیام اصلی به‌صورت inline)
  - پس از ارسال موفق (status_code 200 از تلگرام):
    * تمام screenshot path ها را روی دیسک حذف کن
    * در evidence، path ها را به None تبدیل کن (vision_description
      می‌ماند به‌عنوان نشانه‌ی دائمی)
    * یک پیام در inspector_session اضافه کن:
      «📦 evidence به تلگرام آرشیو شد و از دیسک پاک شد»
  - اگر تلگرام ناموفق بود:
    * screenshot ها را پاک نکن (برای retry آینده یا cleanup TTL)
    * log warning
- backend/app/services/oversight_verifier.py:
  افزودن یک تابع cleanup_orphan_screenshots():
  - هر screenshot قدیمی‌تر از 3 روز که هنوز روی دیسک است → حذف
  - این تابع می‌تواند در scheduler موجود (که از قبل scan دوره‌ای می‌کند)
    صدا زده شود
### Backend — Reuse زیرساخت موجود
- BrowserPool: backend/app/services/verify_runtime/browser_pool.py
- InspectorSession/Message: backend/app/models/inspector_session.py
- DB writes از async: استفاده از asyncio.to_thread برای wrap کردن
  SessionLocal sync operations
- Render Logs API: backend/app/services/log_stream_service.py یا
  endpoint های موجود در render_logs.py
- Vision moduel: oversight_inspector_bridge.py:44
- Storage path: STORAGE_DIR در oversight_service.py:60
### Frontend
- frontend/src/app/oversight/page.tsx (حدود خط 5946+):
  در بخش inline runtime probes، اگر یک probe دارای
  evidence.inspector_session_id است:
  - لینک کوچک «📺 مشاهده در بازرس ویژه →» نشان داده شود که به آدرس
    /projects/{watched.repo_full_name}?tab=inspector&session={id}
    می‌برد
  - اگر vision_description موجود است، یک خط کوتاه از آن inline
    نمایش داده شود (truncated به 100 char)
- frontend/src/app/projects/[id]/page.tsx (لیست sessions):
  session هایی که title آن‌ها با «🤖 auto-verify» شروع می‌شود:
  - آیکن 🤖 در ابتدای عنوان (در حال حاضر هم emoji در عنوان است،
    بنابراین خودکار درست نمایش می‌دهد، فقط چک کن که UI آن را break
    نکند)
  - رنگ background کمی متفاوت تا از session های دستی متمایز باشد
---
## ساختار داده probe
نتیجه‌ی run_inspector_probe RuntimeProbeResult با ساختار:
{
  ac_id, ac_text,
  method: "ui_interaction",
  status: "passed" | "failed" | "error" | "skipped",
  evidence: {
    inspector_session_id: int,
    actions_taken: [
      {action: "navigate", url: "/login", duration_ms: 1234},
      {action: "click", selector: "...", duration_ms: 200},
      {action: "screenshot", label: "after_navigate"},
    ],
    screenshots: [
      {
        path: "storage/oversight/runtime_evidence/.../after_navigate.png",
        label: "after_navigate",
        vision_description: "...",     # متن استخراج‌شده
        vision_source: "openai_vision" | "fallback_text_only" | null,
        archived_to_telegram: false,   # true پس از موفقیت تلگرام
      },
    ],
    console_errors: [
      {level, message, source, timestamp}
    ],
    backend_log_summary: "...",        # خلاصه برای AI verifier
    final_url: "...",
    assertion_results: [
      {expectation: "...", met: true/false, reason: "..."}
    ],
  },
  duration_ms: int,
  error_message: Optional[str]
}
---
## شرط passed / failed
**PASSED:**
- navigate موفق (response status < 400)
- هیچ console error سطح "error" در حین تست
- اگر plan.selector_hint موجود → selector روی صفحه پیدا شد
- vision_description (اگر موجود) متناقض با AC نیست
**FAILED:** یکی از موارد بالا نقض شود
**ERROR:** Playwright crash یا timeout > 60s
**SKIPPED:** frontend_base_url نیست، یا RUNTIME_VERIFY_UI_ENABLED=false،
یا circuit breaker باز
Vision description **advisory** است؛ به‌تنهایی pass/fail نمی‌کند. AI
verifier نهایی است که آن را در نظر می‌گیرد.
---
## محدودیت‌های ایمنی (must)
- timeout per-AC: 60 ثانیه
- max parallel inspector_probes: 1 (sequential)
- حداکثر 2 screenshot per probe (before + after click)
- screenshot file size: cap به 500KB با کیفیت متوسط
- اگر RUNTIME_VERIFY_UI_ENABLED=false → skip
- circuit breaker → skip
- session پس از تمام شدن probe ها archive شود (try/finally)
- screenshot ها فقط در صورت موفقیت تلگرام پاک شوند
- TTL: screenshot های قدیمی‌تر از 3 روز → حذف خودکار در scheduler
- هیچ data شخصی/cookie/auth در evidence لو نرود
- اگر سرور crash کرد، session ممکن است active بماند — یک recovery
  در startup که session های قدیمی auto-verify > 1h را archive کند
---
## Vision Helper API (تابع جدید)
backend/app/services/verify_runtime/vision_helper.py
async def analyze_screenshot(
    screenshot_path: str,
    context: Dict[str, Any],   # {url, console_logs, backend_logs, html_excerpt}
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns:
    {
      "description": str,        # متن آزاد توصیف صفحه
      "ui_elements": [...],      # opcional
      "error_signals": [...],    # opcional
      "source": str,             # "vision_<model>" یا "fallback_text_only" یا "none"
      "raw": dict | None,        # خروجی خام برای debug
    }
    """
    # 1. تلاش با vision models موجود (همان منطق تب بازرسی)
    # 2. در صورت شکست، fallback به verify_model با text-only context
    # 3. در صورت شکست هر دو، return با source="none"
---
## Telegram Bundle Logic
در _send_verify_notification_bg (یا توسعه‌ی آن):
1. متن گزارش معمول (الان وجود دارد): چک‌لیست done/remaining + status
2. **اضافه شود** — اگر runtime_probes شامل screenshots با path معتبر:
   - تا حداکثر 5 screenshot جمع‌آوری شود
   - استفاده از API تلگرام send_media_group (یا send_photo اگر تعداد=1)
   - caption هر media:
     "{ac_text[:50]}\n{vision_description[:200] if available}"
3. **اضافه شود** — اگر task.followup_prompt تولید شده:
   - به‌عنوان فایل .md پیوست شود
   - یا inline در پیام اصلی (اگر < 4000 char)
4. پس از send موفق (response.ok == True):
   - برای هر screenshot، os.remove(path)
   - در DB evidence، path را به None تبدیل کن (vision_description بماند)
   - تأیید در inspector_session بنویس
5. در صورت خطای تلگرام:
   - log error
   - screenshot ها را پاک نکن (TTL خودکار بعداً پاک می‌کند)
---
## TTL Cleanup
یک تابع جدید در oversight_verifier.py یا oversight_service.py:
def cleanup_orphan_runtime_screenshots(max_age_days: int = 3) -> Dict[str, int]:
    """screenshot های قدیمی روی دیسک که بیش از max_age_days از تولیدشان
    گذشته را حذف می‌کند.
    Returns: {deleted_count, deleted_bytes}
    """
این تابع در یکی از اتفاقات زیر صدا زده شود:
- در scheduler (oversight scan loop) — یک بار در روز
- یا در startup lifespan
- یا در یک endpoint جدید برای trigger دستی (اختیاری)
---
## شکست‌خوردگی‌های مجاز (graceful degrade)
- Playwright crash → probe error، verify ادامه می‌دهد
- Vision همه‌ی fallback ها fail → screenshot ذخیره می‌شود، توضیحی نه
- Render logs API نبود → backend_log_summary خالی
- inspector_session ساخته نشد → probe بدون session اجرا (لاگ کاربر در
  Inspector tab نخواهیم داشت)
- Telegram fail → screenshot ها روی دیسک می‌مانند، TTL پاک می‌کند
- اگر دیسک پر شد → cleanup قبل از screenshot جدید، یا skip + warning
---
## برانچ و دیپلوی
- ادامه روی همان branch claude/compare-verify-buttons-1ZyrX
- چند commit مستقل و مرتب:
  1. feat(verify-runtime): inspector_probe Phase 1 — core probe
  2. feat(verify-runtime): vision helper with fallback chain
  3. feat(verify-runtime): inspector_session integration
  4. feat(verify-runtime): telegram bundle + cleanup
  5. feat(verify-runtime): UI links and indicators
  6. test/docs (اختیاری)
- PR #601 به‌روزرسانی می‌شود (commit ها اضافه می‌شوند)
---
## ✅ Done definition
1. probe جدید برای AC هایی با method=ui_interaction (و بدون ui_steps
   مفصل) اجرا می‌شود
2. screenshot واقعی از صفحه deployed روی دیسک ذخیره می‌شود
3. Vision AI متن از screenshot استخراج می‌کند، با fallback به verify
   model اگر vision در دسترس نباشد
4. در گزارش verify (inline + modal) شواهد + vision description دیده
   می‌شود + لینک به بازرس ویژه
5. در تب بازرس ویژه، session «🤖 auto-verify · …» با پیام‌های قدم‌به‌قدم
   ظاهر می‌شود
6. پس از موفقیت verify، تلگرام بسته‌ی کامل (گزارش + screenshot ها +
   followup) را ارسال می‌کند
7. پس از ارسال موفق تلگرام، screenshot ها از دیسک پاک می‌شوند
8. TTL cleanup خودکار screenshot های orphan را پاک می‌کند
9. type-check + python ast بدون خطا
10. هیچ بخش موجود (verify سریع، بازرس ویژه دستی، AI verifier، backfill
    button، manual screenshot debug در tab بازرسی) کارایی‌اش از دست نمی‌دهد
---
## شروع کار
وقتی این پرامپت را فرستادی:
1. با TodoWrite قطعه‌بندی کن
2. ابتدا فایل‌های موجود را بخوان (ui_probe.py، oversight_inspector_bridge.py
   برای vision، _send_verify_notification_bg برای telegram)
3. هر تصمیم معماری بزرگ (مثلاً ساختار vision_helper یا نحوه‌ی pluging
   tagengkam تلگرام) را قبل از کد در پیام شرح بده
4. کد را قطعه‌قطعه commit و push کن (نه یکجا)
5. در پایان، خلاصه‌ای از فایل‌های تغییر یافته و نقاط تست را گزارش کن
----------------------
فاز دوم:
⚠️ **توجه:**
- بخش الف (Phase 2) قبلاً اجرا شده — فقط برای مرجع/حافظه است.
- **بخش ب (سه فیکس) باید الان اجرا شود** وقتی این پرامپت ارسال شد.
══════════════════════════════════════════════════════════════════════
# بخش الف — Phase 2 (مرور؛ قبلاً اجرا شد)
══════════════════════════════════════════════════════════════════════
## هدف Phase 2
A) **Per-step inspector_probe**: برای هر «مرحله» (task_step) از تسک، یک
   probe جداگانه با شواهد ایزوله: screenshot + vision + console logs +
   backend logs + ادرس فرانت ناوبری‌شده + ادرس‌های بک‌اند که در حین لود
   فراخوانی شدند (network requests).
B) **Auto prompt versioning + update + UI**:
   - پس از verify غیر-done، task.prompt قدیمی بایگانی شود در prompt_history،
     و task.prompt = followup_prompt تازه قرار گیرد.
   - UI پنل پرامپت کشوی «نسخه‌های قدیمی» داشته باشد.
   - دکمه «کپی پرامپت» = همیشه نسخه فعلی (که حالا جدید است).
   - endpoint برای revert نسخه قبلی.
C) **Comprehensive Telegram bundle (mega-bundle.html)**: یک فایل واحد
   شامل همه چیز: raw_idea + checklist + پرامپت قدیم/جدید + همه‌ی
   probe ها (هر کدام با screenshot/vision/console/backend logs/
   frontend URL/backend URLs) + assertion ها + AI verifier output.
## فایل‌ها (Phase 2 — مرور)
Backend:
- `backend/app/services/verify_runtime/inspector_probe.py`: network capture
- `backend/app/services/verify_runtime/runner.py`: dispatch
- `backend/app/services/verify_runtime/base.py`: ProbeContext extension
- `backend/app/services/oversight_verifier.py`: per-step probes +
  _infer_route_for_step + session lifecycle + _send_mega_bundle
- `backend/app/services/oversight_mega_bundle.py`: build_mega_bundle_md
- `backend/app/services/oversight_service.py`: prompt_history +
  apply_followup_as_new_prompt + revert_prompt_from_history
- `backend/app/services/notification_service.py`: send_photo +
  send_media_group_photos + send_extra_photos
- `backend/app/api/routes/oversight.py`: revert endpoint
Frontend:
- `frontend/src/app/oversight/page.tsx`: step probe styling + history modal
## ساختار داده per-step probe (مرور)
نتیجه‌ی هر step probe RuntimeProbeResult با:
{
  "ac_id": "step_3",
  "ac_text": "(step probe #3) ...",
  "method": "ui_interaction",
  "status": "passed",
  "evidence": {
    "inspector_session_id": int,
    "step_id": int, "step_title": str, "step_inferred_route": str,
    "actions_taken": [...],
    "screenshots": [{path, label, vision_description, vision_source}],
    "console_errors": [...],
    "network_calls": [...],
    "backend_urls_called": [{url, method, status}],
    "backend_log_summary": str,
    "final_url": str,
    "assertion_results": [...]
  }
}
## شرط passed/failed (مرور)
- PASSED: navigate ok AND no console error AND (selector_hint ok if specified)
- FAILED: یکی نقض شود
- ERROR: Playwright crash یا timeout > 60s
- SKIPPED: no frontend_base_url یا env disabled یا breaker open
══════════════════════════════════════════════════════════════════════
# بخش ب — سه فیکس جدید (الان اجرا شود)
══════════════════════════════════════════════════════════════════════
## مشکلات شناسایی‌شده پس از تست واقعی Phase 2
پس از تست روی یک تسک واقعی (DebateAttachment روی /debate):
1. **چک‌لیست بروز فقط در فایل پیوست هست، نه در متن پیام تلگرام.**
   کاربر می‌خواهد در نوتیفیکیشن تلگرام خلاصه‌ی چک‌لیست به‌روزشدهٔ
   مراحل تسک را در همان متن پیام ببیند (نه فقط در فایل ضمیمه).
2. **bundle.html روی موبایل (Android) قابل باز شدن راحت نیست.**
   تلگرام Android فایل html را دانلود می‌کند ولی کاربر باید دستی browser
   انتخاب کند. تجربهٔ کاربری ضعیف است. **PDF** انتخاب بهتری است چون روی
   موبایل با همان viewer داخلی Telegram باز می‌شود.
3. **vision prompt فقط صفحه را توصیف می‌کند، تشخیص feature نمی‌دهد.**
   نتیجه: حتی اگر feature ساخته نشده باشد، probe می‌گوید «passed» چون
   صفحه باز می‌شود و console error ندارد. vision باید صریحاً بپرسد
   «آیا feature مورد نظر AC در این صفحه دیده می‌شود یا نه؟» و این
   تشخیص باید روی pass/fail probe تأثیر بگذارد.
---
## فیکس ۱ — چک‌لیست به‌روز در متن پیام تلگرام
### هدف
در `_send_verify_notification_bg`، متن نوتیفیکیشن (مستقل از پیوست) باید
شامل خلاصهٔ chk‌لیست به‌روز task_steps باشد:
📋 چک‌لیست (X/N انجام‌شده):
[✅] مرحله ۱: عنوان (100%)
[~] مرحله ۲: عنوان (50%) — باقی‌مانده: «چی مونده»
[ ] مرحله ۳: عنوان (0%)
...

### فایل
`backend/app/services/oversight_verify_pdf.py` — تابع
`build_verify_checklist_message(task, report)` قبلاً وجود دارد. آن را
extend کن (یا تابع جدید بساز و در `_send_verify_notification_bg`
استفاده کن).
### الگوریتم
1. اگر `task.task_steps` خالی است → فقط چک‌لیست AC مثل قبل (بدون تغییر).
2. اگر task_steps دارد:
   - emoji per status: `done`→✅، `partial`→🟡، `not_done`/`pending`→⬜
   - فرمت هر خط (حداکثر ۱۲۰ char per line):
     `{emoji} مرحله {id}: {title[:70]} ({completion_pct}%)`
     اگر `partial` و `remaining` پر:
     `    └─ ⏳ {remaining[:80]}`
   - بالای لیست: `📋 چک‌لیست مراحل ({done_count}/{total} انجام‌شده)`
   - زیر لیست: یک خط `پیشرفت کلی: {avg_pct}%`
3. cap کل بلوک چک‌لیست به ~700 char (Telegram caption max ~1024 با
   مقداری حاشیه برای hashtag و buttons).
4. این بلوک را *قبل از* `streak` و `attachment` info در msg_text
   اضافه کن.
### رفتار شکست
- اگر task_steps malformed بود → silent fallback به نسخه‌ی فعلی.
- اگر بلوک از 700 char بیشتر شد → trim با `…` در آخرین مرحله.
---
## فیکس ۲ — تبدیل bundle از HTML به PDF
### هدف
mega-bundle که الان `.html` است را به `.pdf` تبدیل کن تا روی موبایل
بدون نیاز به browser در همان viewer تلگرام باز شود.
### استراتژی
کتابخانه‌ی PDF موجود در پروژه را شناسایی کن (verify_report PDF از
قبل با همان لایبرری ساخته می‌شود). تابع `build_verify_report_pdf` در
`oversight_verify_pdf.py` هست — pattern و font selection آن را reuse
کن.
### فایل
1. `backend/app/services/oversight_mega_bundle.py` — تابع جدید
   `build_mega_bundle_pdf(task, report) -> bytes`. تابع موجود
   `build_mega_bundle_md` می‌تواند به‌عنوان helper برای متن ۱۰ بخش
   باقی بماند، یا کل منطق متن داخل _build_text_sections استخراج شود.
2. ساختار pdf:
   - عنوان: `📦 Bundle — {task.title}`
   - تاریخ تولید
   - بخش‌های ۱-۱۰ همان که در md/html هست (heading + body)
   - فونت با پشتیبانی فارسی (همان فونتی که build_verify_report_pdf
     استفاده می‌کند).
   - RTL support اگر کتابخانه پشتیبانی می‌کند.
   - حداکثر اندازه: 5MB (Telegram تا 20MB قبول دارد ولی پروژه trim
     قبلی ۱MB داشت — برای pdf حد بالاتری مناسب است).
### Wire-up
در `_send_mega_bundle` (در `oversight_verifier.py`):
- به‌جای `build_mega_bundle_md` صدا بزن `build_mega_bundle_pdf`.
- filename: `bundle_{task_id[:12]}_{ts}.pdf`
- caption: همان `📦 بسته‌ی کامل verify — «{title}»`.
اگر ساخت pdf شکست خورد → fallback به html (همان رفتار قبلی) با log
warning.
### نکات
- پشتیبانی فارسی pdf کمی پیچیده است. اگر کتابخانهٔ موجود ReportLab است،
  باید فونت TTF Persian (مثل Vazir یا Tahoma) ثبت شده باشد. اگر
  `oversight_verify_pdf.py` فونت ثبت می‌کند، همان را reuse کن.
- اگر هیچ فونت Persian نیست، fallback به همان html (بهتر از pdf
  مbroken).
---
## فیکس ۳ — بهبود vision prompt برای تشخیص feature
### هدف
vision در حال حاضر فقط صفحه را توصیف می‌کند. باید صریحاً تشخیص دهد
«آیا feature ذکرشده در AC در این صفحه قابل مشاهده است یا نه؟» و این
تشخیص روی pass/fail probe تأثیر بگذارد.
### فایل ۱
`backend/app/services/verify_runtime/vision_helper.py` — تابع
`analyze_screenshot` را extend کن:
- prompt را عوض کن تا علاوه بر `description`, `ui_elements`, و غیره،
  این فیلد جدید را هم برگرداند:
"feature_present": "yes" | "no" | "unclear"

که نشان می‌دهد آیا feature مورد نظر (متن AC) در screenshot دیده
می‌شود یا نه.
- پرامپت جدید (الگو):
این screenshot از یک صفحهٔ پروژه نرم‌افزاری است.

📋 ویژگی‌ای که باید بررسی شود:
«{ac_text}»

وظیفهٔ تو:

صفحه را به‌صورت متن غنی توصیف کن (scene, ui_elements, …)
⚠️ مهم‌ترین کار: بسنج که آیا ویژگی فوق در صفحه دیده می‌شود
یا نه. خروجی feature_present:
"yes": کاملاً دیده می‌شود (UI ساخته شده، دکمه/پنل/فرم وجود دارد)
"no": اصلاً دیده نمی‌شود (صفحه عمومی است، feature ساخته نشده)
"unclear": مطمئن نیستی یا اطلاعات کافی نیست
خروجی JSON:
{
"scene": "...",
"ocr_text": "...",
"ui_elements": "...",
"error_signals": "...",
"feature_present": "yes" | "no" | "unclear",
"feature_reason": "چرا این تشخیص — یک جمله"
}

- بازگشت تابع: علاوه بر فیلدهای فعلی، `feature_present` و `feature_reason`.
### فایل ۲
`backend/app/services/verify_runtime/inspector_probe.py` — منطق
pass/fail:
- در محل محاسبهٔ `passed` (حدود خط 590)، vision result را هم در نظر بگیر:
```python
# اگر vision قطعاً گفته feature_present=no، probe باید failed باشد
# حتی اگر navigate ok بود و console error نبود
vision_says_no = False
for shot in screenshots:
    vd = shot.get("vision_feature_present")
    if vd == "no":
        vision_says_no = True
        break
if vision_says_no:
    status = PROBE_STATUS_FAILED
    # یک assertion اضافه کن:
    assertion_results.append({
        "expectation": f"feature «{ac_text[:80]}» در صفحه دیده شود",
        "met": False,
        "reason": "vision AI تشخیص داد feature در صفحه وجود ندارد",
    })
screenshot dict باید دارای فیلد جدید باشد:
shot["vision_feature_present"] = vres.get("feature_present")
shot["vision_feature_reason"] = vres.get("feature_reason")
فایل ۳ — propagate به mega-bundle
backend/app/services/oversight_mega_bundle.py — در بخش probes
(در حلقه شواهد دانه‌به‌دانه):

اگر screenshot دارای vision_feature_present بود، آن را نمایش بده:
- feature_present: ❌ NO — vision AI: ...
فایل ۴ — UI inline (اختیاری ولی توصیه‌شده)
frontend/src/app/oversight/page.tsx — در inline runtime probes، اگر
شات vision_feature_present === "no" بود، یک علامت قرمز اضافه کن:

🔴 feature dynamic ساخته نشده (vision detection)
نکات ایمنی
اگر vision_helper برمی‌گردد source="none" (هیچ vision در دسترس نبود)،
feature_present را نادیده بگیر (همان رفتار قدیم — passed بر اساس
navigate + console).
اگر feature_present="unclear"، probe status را عوض نکن (همان
passed/failed قدیم).
فقط "no" قطعی باعث می‌شود passed → failed.
✅ Done definition (سخت‌گیر)
در نوتیفیکیشن تلگرام، خود متن پیام شامل بلوک چک‌لیست به‌روز
task_steps است (نه فقط در پیوست).
mega-bundle فایل .pdf است (نه .html یا .md)، با فونت فارسی و
تمام ۱۰ بخش قابل خواندن روی موبایل.
در صورت ناتوانی ساخت pdf (مثلاً نبود فونت)، fallback به html
بدون شکست کل verify.
vision_helper فیلد feature_present (yes/no/unclear) برمی‌گرداند.
اگر vision قطعاً گفت no، probe status = failed (با assertion
جدید) — حتی اگر navigate موفق بود.
در mega-bundle، feature_present per screenshot دیده می‌شود.
در UI inline، probe هایی با feature_present=no متمایز هستند.
type-check + python ast پاس.
هیچ بخش موجود از کار نیفتاد (verify سریع، Phase 1 system probe،
Phase 2 per-step probes، بازرس ویژه دستی، …).
--------------------------
فاز سوم:
# 🎯 پرامپت کامل Phase 3 — Form interaction + Auth + Enhanced feature detection
⚠️ این پرامپت Phase 3 از سری «verify جدید» است که پس از Phase 1 و
Phase 2 و سه فیکس آخر اجرا می‌شود.
══════════════════════════════════════════════════════════════════════
# مرور سریع Phase 1 و 2 (چه چیزی الان داریم)
══════════════════════════════════════════════════════════════════════
✅ **Phase 1** اضافه کرد:
- inspector_probe.py — Playwright server-side با navigate + click +
  screenshot + console capture + backend log query
- vision_helper.py با fallback chain (multimodal → text-only → none)
- inspector_session با عنوان «🤖 auto-verify · …» برای visibility
- TTL cleanup + startup recovery + telegram screenshot+followup
✅ **Phase 2** اضافه کرد:
- Per-step probes با route inferred از step.title/scope
- Network capture (frontend + backend URLs per probe)
- Step-aware AI verifier prompt
- prompt_history + apply_followup_as_new_prompt + revert endpoint
- mega-bundle (PDF با fallback HTML)
✅ **سه فیکس آخر** اضافه کرد:
- چک‌لیست در caption تلگرام
- Bundle PDF (نه HTML)
- Vision `feature_present` (yes/no/unclear) با pass/fail flip
══════════════════════════════════════════════════════════════════════
# محدودیت‌های فعلی که Phase 3 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 2 + سه فیکس مشخص شد:
1. **probe فقط navigate می‌کند و نگاه می‌کند** — نمی‌تواند با feature
   تعامل کند. اگر feature یک دکمه باشد، probe دکمه را نمی‌زند تا
   ببیند modal باز می‌شود یا نه.
2. **Vision feature_present حدود ۴۰٪ false-positive دارد** —
   step probe 2 «اضافه کردن UI انتخاب محتوا» را passed داد در حالی
   که UI ساخته نشده بود. علت: vision دکمه‌های عمومی صفحه را دید و
   فکر کرد همینه. اگر probe می‌توانست «کلیک روی selector_hint و
   چک کردن modal/result» را انجام دهد، تشخیص دقیق‌تر بود.
3. **صفحات با لاگین قابل بررسی نیستند** — مثلاً اگر کاربر تسکی روی
   `/admin/dashboard` تعریف کند، probe redirect به /login می‌خورد
   و تشخیص «این feature ساخته شده» غلط می‌شود (همان مشکلی که در
   system probe رخ داد — vision گفت «صفحه login می‌بینم»).
4. **AC هایی که نیاز به submit فرم دارند نمی‌توانند تست شوند** —
   مثلاً «وقتی فرم لاگین پر شود و submit شود، کاربر به داشبورد می‌رود».
══════════════════════════════════════════════════════════════════════
# هدف کلی Phase 3 — سه قابلیت متمم
══════════════════════════════════════════════════════════════════════
**A) Form/Input Interaction Recipes**
inspector_probe باید پشتیبانی کند از:
- `fill {selector, value}` — تایپ متن در input/textarea
- `submit {form_selector}` یا کلیک روی دکمهٔ submit
- `wait_for {selector, timeout_ms, state}` — صبر تا المنت ظاهر شود
- `select {selector, option}` — انتخاب از dropdown
- `check {selector}` / `uncheck {selector}` — checkbox/radio
- `hover {selector}` — برای tooltip ها
- `wait_for_url {contains}` — صبر تا URL تغییر کند (برای SPA)
این actions در `verify_plan.ui_steps` تعریف می‌شوند (schema موجود
ui_probe). به‌جای اینکه inspector_probe فقط `navigate + click hint`
انجام دهد، اگر `ui_steps` کامل بود، تمام sequence را اجرا کند.
**B) Authentication / Session Management**
WatchedProject از قبل فیلد `runtime_auth: {type, value}` دارد. الان
ui_probe (نه inspector_probe) فقط ازش استفاده می‌کند. باید:
- inspector_probe هم cookie/bearer auth را اعمال کند قبل از navigate
- Auto-detect login redirect → اگر صفحه به /login redirect شد،
  evidence را با وضعیت «نیاز به لاگین» علامت بزن
- Auth recipe در WatchedProject — یک sequence «navigate to /login →
  fill email → fill password → submit → wait_for_url(/dashboard)»
  که قبل از هر verify run یک‌بار اجرا می‌شود و cookies را برای
  استفاده‌ی probe ها ذخیره می‌کند (storage state)
- ذخیره storage state در DB (یا فایل امن) با حفظ امنیت (cookie ها
  encrypted)
**C) Enhanced Feature Detection (multi-screenshot + before/after)**
به‌جای یک screenshot واحد:
- screenshot قبل از interaction
- screenshot بعد از interaction
- Vision آنالیز diff: «بعد از کلیک، چه چیزی روی صفحه ظاهر شد؟»
- Network call analysis: آیا interaction باعث backend call شد؟
  (مثلاً submit form → POST request)
- اگر AC انتظار modal دارد، چک کن modal واقعاً ظاهر شد
══════════════════════════════════════════════════════════════════════
# A) Form Interaction Recipes — جزئیات
══════════════════════════════════════════════════════════════════════
## فایل‌ها
**Backend — تغییر**
`backend/app/services/verify_runtime/inspector_probe.py`:
در `_run_inspector_inner`، پس از navigate و قبل از single-click logic،
یک «execution loop» اضافه شود که اگر `verify_plan.ui_steps` بیش از یک
step غیر-navigate دارد، همه را اجرا کند.
تابع helper جدید `_execute_ui_step(page, step, context, recorder)`:
- Input: step dict {action, selector, value, timeout_ms, ...}
- اجرای action با Playwright API
- ثبت نتیجه در `actions_taken`
- در صورت شکست: error_message + screenshot
- خروجی: (success: bool, message: str, screenshot_label: Optional[str])
Actions پشتیبانی شده:
```python
SUPPORTED_ACTIONS = {
    "navigate",       # page.goto(url)
    "click",          # page.click(selector)
    "fill",           # page.fill(selector, value)
    "submit",         # page.locator(selector).press("Enter") یا
                     # await page.locator(selector + " button[type=submit]").click()
    "select",         # page.select_option(selector, value)
    "check",          # page.check(selector)
    "uncheck",        # page.uncheck(selector)
    "hover",          # page.hover(selector)
    "wait_for",       # page.wait_for_selector(selector, timeout, state)
    "wait_for_url",   # page.wait_for_url(pattern, timeout)
    "wait_for_load",  # page.wait_for_load_state(state)
    "screenshot",     # take a labeled screenshot
    "scroll_to",      # page.locator(selector).scroll_into_view_if_needed()
    "press_key",      # page.keyboard.press(key)
    "assert_visible", # page.locator(selector).is_visible()
    "assert_text",    # page.locator(selector).text_content() contains x
    "assert_url",     # page.url contains x
}
هر step خروجی:

{
    "step_idx": int,
    "action": str,
    "selector": Optional[str],
    "value": Optional[str],
    "success": bool,
    "duration_ms": int,
    "message": str,
    "error": Optional[str],
    "screenshot_label": Optional[str],
}
شرط شکست
اگر action ناشناخته → step error, ادامه با بقیه
اگر selector پیدا نشد → step failed, screenshot قبل از خروج
اگر timeout (default 5s per step) → step failed
اگر any step failed → probe overall failed (مگر آنکه assert step
ها خروجی expected داشتند)
sequence per task_step
وقتی Phase 2 step probe می‌سازد، الان فقط:

verify_plan = {
    "ui_steps": [{"action": "navigate", "url": route}]
}
در Phase 3، AI enricher باید پیشنهاد کند یک sequence کامل بر اساس
step.title و step.scope:

مثلاً برای step «اضافه کردن UI انتخاب و اتصال محتوا»:
ui_steps: [
    {"action": "navigate", "url": "/debate"},
    {"action": "wait_for", "selector": "[data-testid='page-loaded']",
     "timeout_ms": 3000},
    {"action": "screenshot", "label": "initial"},
    {"action": "click", "selector": "[data-testid='btn-attach']"},
    {"action": "wait_for", "selector": "[data-testid='attach-modal']",
     "timeout_ms": 2000},
    {"action": "screenshot", "label": "after_click_attach"},
    {"action": "assert_visible", "selector": "[data-testid='content-list']"}
]
این sequence را AI enricher هنگام enrich AC تولید می‌کند —
نیازی به دستی کد کاربر نیست. AI با دیدن AC + target_files یک
recipe پیشنهاد می‌دهد.

بازمراجعه به enricher (ac_enricher.py)
prompt enricher را بهبود ده تا برای method=ui_interaction، یک
sequence ۳-۸ step واقعی پیشنهاد دهد (نه فقط [{action: navigate}]).
selector ها با احتیاط [data-testid='...'] (با اخطار در commit
message که ممکن است باید adjust شود).

══════════════════════════════════════════════════════════════════════

B) Authentication / Session Management — جزئیات
══════════════════════════════════════════════════════════════════════

فایل‌ها
Backend — تغییر
backend/app/services/oversight_service.py:

افزودن به WatchedProject:

# 🆕 (Phase 3) — auth recipe برای probe ها
# اگر تنظیم شد، قبل از هر verify run یک login flow اجرا می‌شود و
# storage_state (cookies + localStorage) برای استفاده‌ی probe ها
# ذخیره می‌شود.
runtime_auth_recipe: Optional[Dict[str, Any]] = None
# ساختار:
# {
#   "type": "form_login",
#   "login_url": "/login",
#   "steps": [
#     {"action": "fill", "selector": "input[name=email]",
#      "value_env": "TEST_EMAIL"},  # یا "value": "test@test.com"
#     {"action": "fill", "selector": "input[name=password]",
#      "value_env": "TEST_PASSWORD"},
#     {"action": "click", "selector": "button[type=submit]"},
#     {"action": "wait_for_url", "contains": "/dashboard",
#      "timeout_ms": 5000},
#   ],
#   "success_indicator": {"selector": "[data-testid='user-menu']",
#                         "must_exist": true},
#   "session_ttl_minutes": 30,  # storage_state بعد از این مدت refresh
# }

# 🆕 (Phase 3) — cached storage state (encrypted)
runtime_storage_state: Optional[Dict[str, Any]] = None
# {
#   "encrypted_blob": str,  # AES-GCM encrypted JSON storage_state
#   "expires_at": ISO,
#   "obtained_at": ISO,
#   "login_failed_count": int,
# }
Backend — فایل جدید
backend/app/services/verify_runtime/auth_runner.py:

تابع async def obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict[str, Any]]:

اگر runtime_auth_recipe تنظیم نشده → return None
اگر runtime_storage_state معتبر و expires_at > now و force=False →
decrypt و return
در غیر این صورت: launch Chromium → execute recipe.steps → اگر
success_indicator OK → دریافت storage_state از context →
encrypt → ذخیره در watched → return decoded
اگر login شکست خورد → login_failed_count += 1، return None
بعد از ۳ شکست متوالی → recipe را disable موقت (با log)
تابع helper _encrypt_storage(data: Dict, key: bytes) -> str و
معکوس _decrypt_storage(blob: str, key: bytes) -> Dict:

AES-GCM با کلید مشتق از env OVERSIGHT_AUTH_KEY (اگر نبود، یک
کلید تصادفی بساز و در env ست کن — warning log)
این برای اینکه cookie ها در plaintext در DB نمی‌مانند.
Backend — تغییر دیگر
backend/app/services/verify_runtime/inspector_probe.py:

پشتیبانی از ProbeContext.storage_state (فیلد جدید در base.py):

اگر ctx.storage_state پر است:
context = await browser.new_context(
    viewport={"width": 1280, "height": 800},
    storage_state=ctx.storage_state,  # Playwright API
)
این تمام cookies + localStorage را به probe می‌دهد بدون نیاز به
login مجدد.
Backend — تغییر در verifier
backend/app/services/oversight_verifier.py:

در _verify_task، قبل از ساخت ProbeContext:

# 🆕 (Phase 3) — اگر watched recipe دارد، storage_state بگیر/تازه کن
auth_storage_state = None
if watched and getattr(watched, "runtime_auth_recipe", None):
    try:
        from .verify_runtime.auth_runner import obtain_or_refresh_storage_state
        auth_storage_state = await obtain_or_refresh_storage_state(watched)
    except Exception as _ae:
        logger.warning(f"auth runner failed: {_ae}")

_probe_ctx = build_probe_context(
    ...,
    storage_state=auth_storage_state,
)
Login redirect detection
در _run_inspector_inner، بعد از navigate، چک کن:

اگر page.url شامل /login یا /signin بود (و route قبلی این نبود)
یا page.title شامل «Login» یا «ورود» بود
→ علامت‌گذاری probe با auth_required: true در evidence
vision_helper این را می‌گیرد و در feature_present تأثیر می‌دهد
auth_required = False
final_url_lower = (page.url or "").lower()
if any(p in final_url_lower for p in ("/login", "/signin", "/auth")):
    if "/login" not in full_url.lower():  # خود route نبود
        auth_required = True

evidence["auth_required"] = auth_required
if auth_required:
    assertion_results.append({
        "expectation": "صفحه‌ی هدف بدون redirect به login باز شود",
        "met": False,
        "reason": f"redirect به {page.url} — احتمالاً auth recipe لازم است",
    })
══════════════════════════════════════════════════════════════════════

C) Enhanced Feature Detection — جزئیات
══════════════════════════════════════════════════════════════════════

Before/After screenshot pairs
وقتی verify_plan.ui_steps شامل interaction (click/fill/submit) است:

screenshot قبل از اولین interaction (label="before_interaction")
screenshot بعد از آخرین interaction (label="after_interaction")
Vision آنالیز diff: prompt جدید برای vision_helper
# vision_helper.py — تابع جدید
async def analyze_screenshot_pair(
    before_path: str,
    after_path: str,
    context: Dict[str, Any],  # شامل ac_text و actions_taken
) -> Dict[str, Any]:
    """آنالیز یک جفت screenshot قبل/بعد از interaction.

    Returns:
      {
        "before_description": str,
        "after_description": str,
        "diff_description": str,    # «بعد از کلیک X، Y ظاهر شد»
        "interaction_succeeded": "yes" | "no" | "unclear",
        "feature_present": "yes" | "no" | "unclear",
        "source": str,
      }
    """
این تابع از multimodal vision یک prompt دو-عکسی می‌فرستد و می‌پرسد:
«قبل از این تعامل، صفحه X بود. بعد از تعامل، Y شد. آیا تعامل کار
کرد و feature واقعاً عمل کرد؟»

Network call analysis
inspector_probe قبلاً backend_urls_called ذخیره می‌کرد. در Phase 3:

اگر AC انتظار یک API call خاص دارد (مثلاً «POST /api/debates ساخته
شود»)، probe باید بفهمد آیا آن endpoint در network_calls هست:

# در verify_plan
"expected_api_calls": [
    {"method": "POST", "path_contains": "/api/debates"},
    {"method": "GET", "path_contains": "/api/projects/.*/files"},
]
probe بعد از interaction چک می‌کند:

expected = plan.get("expected_api_calls") or []
for exp in expected:
    matched = any(
        c.get("method") == exp["method"]
        and exp["path_contains"] in (c.get("url") or "")
        for c in network_calls
    )
    assertion_results.append({
        "expectation": f"API call {exp['method']} {exp['path_contains']}",
        "met": matched,
        "reason": "ثبت شد" if matched else "ثبت نشد",
    })
Multi-screenshot evidence storage
الان _MAX_SCREENSHOTS = 2. در Phase 3 بالا ببر به 5 (یا 6) تا
interaction های پیچیده کاملاً capture شوند.

══════════════════════════════════════════════════════════════════════

D) UI — تنظیمات auth recipe
══════════════════════════════════════════════════════════════════════

frontend/src/app/oversight/page.tsx — در همان panel «runtime» که
runtime_repo_path و base URLs ست می‌شوند:

یک بخش جدید «🔐 Auth Recipe (اختیاری)»
form فیلدها:
login_url (text input)
email (text input — برای save در env var name)
password (text input — برای save در env var name)
email selector (text input — مثلاً input[name=email])
password selector (text input)
submit selector
success indicator selector
session_ttl_minutes (number, default 30)
دکمه «🧪 Test login» که recipe را یک‌بار اجرا می‌کند و نتیجه را
نشان می‌دهد (success_indicator پیدا شد؟)
دکمه «🔄 Refresh session» که storage_state فعلی را invalidate و
دوباره می‌سازد
══════════════════════════════════════════════════════════════════════

E) AI Enricher بهبود — recipe generation
══════════════════════════════════════════════════════════════════════

backend/app/services/verify_runtime/ac_enricher.py:

برای method=ui_interaction، prompt enricher را extend کن تا یک
recipe ۳-۸ step واقعی پیشنهاد دهد (نه فقط navigate).

prompt جدید (extend):

برای روش ui_interaction، یک sequence ۳ تا ۸ مرحله‌ای پیشنهاد بده
که برای تأیید این AC کفایت کند. مراحل باید شامل:
1. navigate به صفحه‌ی مرتبط
2. wait_for یک selector که نشان دهد صفحه load شده
3. screenshot قبل از تعامل
4. در صورت لزوم، fill/click/submit برای trigger feature
5. wait_for selector جدید یا تغییر URL
6. screenshot بعد از تعامل
7. assert_visible یا assert_text برای تأیید feature
selector ها را با `[data-testid='...']` ساختگی پیشنهاد بده (با
اخطار در commit message).
برای AC که فقط «نمایش بدون تعامل» است (مثلاً «اطلاعات کاربر
نمایش داده شود»)، sequence را به ۳ مرحله (navigate + wait + assert)
محدود کن.
══════════════════════════════════════════════════════════════════════

Done definition (سخت‌گیر)
══════════════════════════════════════════════════════════════════════

inspector_probe می‌تواند sequence ۸ مرحله‌ای را اجرا کند (navigate
wait + click + fill + submit + wait + assert + screenshot).
هر step خروجی isolated دارد (success, duration, error, screenshot_label).
WatchedProject فیلد runtime_auth_recipe دارد و قابل تنظیم از UI است.
اگر recipe تنظیم شد، قبل از verify یک‌بار login اجرا می‌شود و
storage_state کش می‌شود (encrypted).
probe ها از storage_state برای دسترسی به صفحات با لاگین استفاده
می‌کنند.
Login redirect detection کار می‌کند — اگر probe به /login redirect
خورد، assertion auth_required: false با reason ثبت می‌شود.
Before/After screenshot pair برای step هایی با interaction گرفته
می‌شود.
Vision pair analysis قابل دسترس است (تابع جدید analyze_screenshot_pair).
expected_api_calls در verify_plan قابل تعریف است و assertion چک
می‌شود.
AI enricher recipe ۳-۸ مرحله‌ای پیشنهاد می‌دهد (نه فقط navigate).
UI auth recipe panel کار می‌کند با Test login + Refresh session.
هیچ بخش موجود از کار نیفتاد (Phase 1, Phase 2, سه فیکس، verify
سریع، بازرس ویژه دستی، …).
type-check + python ast پاس.
تست واقعی: روی یک تسک با task_steps چندگانه و یک recipe ساده،
probe ها sequence را اجرا کنند، حداقل ۲ probe interaction واقعی
داشته باشند (نه فقط navigate).
══════════════════════════════════════════════════════════════════════

محدودیت‌های ایمنی
══════════════════════════════════════════════════════════════════════

per-step timeout: ۵ ثانیه (configurable در plan.step_timeout_ms)
per-probe timeout: ۹۰ ثانیه (افزایش از ۶۰ به ۹۰ برای recipe طولانی)
max screenshots per probe: ۵ (افزایش از ۲)
max ui_steps per probe: ۱۲ (محدودیت سخت — اگر AC بیشتر خواست، AC
باید به دو step تقسیم شود)
network capture: همان ۳۰ request
auth recipe value_env reference: فقط env vars با prefix
WATCHED_AUTH_* قابل استفاده — جلوگیری از leak credentials از
env های دیگر
storage_state encryption: AES-GCM با کلید مشتق از env
OVERSIGHT_AUTH_KEY. اگر نبود، fail-soft (recipe disabled با
هشدار)
max recipe step timeout: ۱۵ ثانیه (auth recipe می‌تواند کمی طولانی‌تر
از step probe عادی باشد)
اگر login_failed_count >= ۳ → recipe موقت disable + alert در
inspector_session
هیچ password/cookie در evidence یا inspector_session messages
ذخیره نشود — فقط auth_state: "valid" | "expired" | "failed"
══════════════════════════════════════════════════════════════════════

شکست‌خوردگی‌های مجاز (graceful degrade)
══════════════════════════════════════════════════════════════════════

recipe نبود → probe بدون auth (همان رفتار Phase 2)
recipe شکست خورد → probe بدون storage_state (و evidence با
auth_attempted: true, auth_failed: true)
expected_api_calls فیلد نبود → فقط assertion ها بدون این چک
before/after pair خراب شد → یکی از screenshot ها استفاده شود
(fallback به single screenshot vision)
vision pair analysis fail → fallback به single-screenshot vision
enricher recipe خراب → fallback به همان navigate-only Phase 2
step ناشناخته → error در همان step، بقیه continue
══════════════════════════════════════════════════════════════════════

فایل‌های نهایی
══════════════════════════════════════════════════════════════════════

Backend جدید
backend/app/services/verify_runtime/auth_runner.py (login flow
executor + storage_state encrypt/decrypt)
Backend تغییر
backend/app/services/verify_runtime/base.py (ProbeContext فیلد
storage_state اضافه)
backend/app/services/verify_runtime/inspector_probe.py (action
loop + auth check + login redirect detection + before/after pairs +
expected_api_calls assertion + max screenshots افزایش)
backend/app/services/verify_runtime/vision_helper.py (تابع
جدید analyze_screenshot_pair)
backend/app/services/verify_runtime/runner.py (build_probe_context
پارامتر storage_state)
backend/app/services/verify_runtime/ac_enricher.py (prompt update
برای recipe ۳-۸ مرحله‌ای)
backend/app/services/oversight_service.py (WatchedProject فیلدهای
runtime_auth_recipe و runtime_storage_state)
backend/app/services/oversight_verifier.py (obtain storage_state
قبل از probes)
backend/app/api/routes/oversight.py (endpoint های test-login و
refresh-session برای auth panel)
Frontend
frontend/src/app/oversight/page.tsx (auth recipe panel در runtime
section + Test login + Refresh session buttons + نمایش
auth_required در runtime probes inline)
══════════════════════════════════════════════════════════════════════

ساختار داده‌ی نهایی per-step probe (Phase 3)
══════════════════════════════════════════════════════════════════════

{
  "ac_id": "step_3",
  "ac_text": "(step probe #3) ...",
  "method": "ui_interaction",
  "status": "passed | failed | error | skipped",
  "evidence": {
    "inspector_session_id": int,
    "step_id": int, "step_title": str, "step_inferred_route": str,
    "actions_taken": [
      {"step_idx": 0, "action": "navigate", "url": "/debate",
       "success": true, "duration_ms": 1234},
      {"step_idx": 1, "action": "wait_for",
       "selector": "[data-testid='page-loaded']", "success": true,
       "duration_ms": 250},
      {"step_idx": 2, "action": "screenshot", "label": "before_click",
       "success": true},
      {"step_idx": 3, "action": "click",
       "selector": "[data-testid='btn-attach']", "success": false,
       "error": "selector not found", "duration_ms": 5000},
      ...
    ],
    "screenshots": [
      {"path": "...", "label": "before_click",
       "vision_description": "...", "vision_feature_present": "no", ...},
      {"path": "...", "label": "after_click",
       "vision_description": "...", "vision_feature_present": "yes", ...},
      ...
    ],
    "vision_pair": {  # اگر pair analysis اجرا شده
       "before_description": "...",
       "after_description": "...",
       "diff_description": "بعد از کلیک، modal باز شد و فرم ظاهر شد",
       "interaction_succeeded": "yes",
       "feature_present": "yes"
    },
    "console_errors": [...],
    "network_calls": [...],
    "backend_urls_called": [...],
    "expected_api_calls_results": [
       {"expectation": "POST /api/debates", "met": true},
       ...
    ],
    "auth_required": bool,
    "auth_state": "valid | expired | failed | none",
    "assertion_results": [...],
    "final_url": str,
    "probe_type": "inspector_phase3"  # version bump
  },
  "duration_ms": int
}
══════════════════════════════════════════════════════════════════════

شرط passed/failed/error (به‌روزشده)
══════════════════════════════════════════════════════════════════════

PASSED:

همه‌ی ui_steps موفق (navigate ok + هر step success=true)
هیچ console error سطح "error"
vision_feature_present != "no" (یا "yes" یا "unclear")
اگر pair analysis اجرا شد، interaction_succeeded != "no"
اگر expected_api_calls تعریف شد، همه match شدند
FAILED: یکی از موارد بالا نقض شود.

ERROR: Playwright crash، timeout > 90s، auth runner crash.

SKIPPED: frontend_base_url نیست، env flag disabled، breaker open.

══════════════════════════════════════════════════════════════════════

شروع کار
══════════════════════════════════════════════════════════════════════

وقتی این پرامپت ارسال شد:

TodoWrite قطعه‌بندی کن — ترتیب پیشنهادی:
A1: ProbeContext.storage_state field
A2: _execute_ui_step helper + action loop
A3: enricher prompt update برای recipe طولانی
B1: WatchedProject fields (recipe + storage_state)
B2: auth_runner.py
B3: integration در _verify_task
B4: login redirect detection
C1: before/after screenshot pairs
C2: vision_helper.analyze_screenshot_pair
C3: expected_api_calls assertion
D: UI auth panel + test endpoints
Validation + commits + push
هر بخش یک commit جداگانه. کد کار نکن یکجا — قطعه قطعه.
هر تصمیم بزرگ (مثلاً انتخاب کتابخانه encryption، یا ساختار recipe)
را قبل از کد در پیام شرح بده.
تست‌نکته‌ها در پایان: روی یک تسک با recipe ساده (مثلاً auth +
navigate به /admin) verify بزن و خروجی را نشان بده.
هیچ بخش موجود را نشکن. Phase 1 + Phase 2 + سه فیکس باید همچنان
کار کنند.
در پایان، یک خلاصه‌ی فایل‌های تغییر‌یافته و نمونه‌ای از probe
evidence Phase 3 ارسال کن.
-------------------------
فاز چهارم:


# 🎯 پرامپت کامل Phase 4 — Smart Navigation + Backend Log Probe + Code-aware Verifier
⚠️ این پرامپت Phase 4 از سری «verify جدید» است که پس از Phase 1، 2،
و 3 (شامل سه فیکس آخر) اجرا می‌شود.
══════════════════════════════════════════════════════════════════════
# مرور خیلی سریع وضعیت فعلی
══════════════════════════════════════════════════════════════════════
✅ **Phase 1**: inspector_probe پایه با navigate + screenshot + vision +
   session + telegram + cleanup + recovery.
✅ **Phase 2**: per-step probes + prompt versioning + mega-bundle PDF.
✅ **Phase 3**: action loop (fill/click/wait/assert) + auth recipe +
   vision_pair + expected_api_calls + force backfill + Telegram trigger.
✅ **سه فیکس آخر**: SPA-404 detection + system probe relaxation +
   conservative routing (skip when no specific route).
══════════════════════════════════════════════════════════════════════
# مشکلات باقیمانده که Phase 4 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 3 + سه فیکس مشخص شد:
1. **route guessing ضعیف**: برای تسک trading-system که صفحات URL خاصی
   داشتند (مثل /routing-diagram, /charts)، probe نمی‌تواند URL واقعی
   را پیدا کند. حدس‌های keyword-based 404 می‌گیرند. کاربر گفت در
   تجربه قبلی هم با این مشکل اذیت شده بود.
2. **تسک‌های backend-heavy benefit صفر می‌گیرند**: تسک‌هایی مثل
   DebateAttachment (backend models, endpoints, service logic) از
   probe UI سود نمی‌برند چون feature تو UI دیده نمی‌شود. probe ها
   skipped می‌شوند ولی verify بدون شواهد runtime می‌ماند.
3. **استفاده ناکامل از Render logs**: الان فقط لاگ‌های window زمانی
   probe فیلتر می‌شوند (level=error/warn). با اینکه RENDER_API_KEY ست
   شده، از لاگ‌های مرتبط به فایل‌های target تسک یا call های endpoint
   مرتبط استفاده نمی‌کنیم.
4. **استفاده ناکامل از inspector chat infrastructure**: بازرس ویژه
   دستی از قبل لاگ‌های backend + console همراه هر پیام چت ذخیره
   می‌کند، ولی auto-verify از این infrastructure استفاده نمی‌کند.
══════════════════════════════════════════════════════════════════════
# هدف کلی Phase 4 — سه ستون
══════════════════════════════════════════════════════════════════════
**A) Smart Navigation Probe (Agentic Browsing)**
به‌جای حدس زدن URL از روی keyword، probe به home می‌رود، nav menu
را می‌خواند، و AI تصمیم می‌گیرد کدام لینک به feature مرتبط است.
این الگوی استاندارد OpenAI Operator / Anthropic Computer Use است.
**B) Backend Log Probe**
برای تسک‌های backend-heavy (که AC شون از UI element حرف نمی‌زند)،
به‌جای probe UI، یک probe جدید لاگ‌های Render فیلتر شده بر اساس
target_files تسک + AC keywords را تحلیل می‌کند. خروجی: «آیا این
feature backend deploy شده و call می‌شود؟»
**C) Code-aware Verifier (Per-AC commit analysis)**
gh API الان فقط در سطح کل تسک استفاده می‌شود. در Phase 4، برای هر
AC جداگانه چک می‌شود که آیا diff اخیر آن AC را پیاده کرده یا نه.
این بدون نیاز به repo کلون محلی، با همان GitHub API که داریم.
══════════════════════════════════════════════════════════════════════
# درس‌های گرفته‌شده از Phase 1-3 (تا اشتباهات تکرار نشود)
══════════════════════════════════════════════════════════════════════
1. **هرگز feature را فرض نکن**: اگر مطمئن نیستی، SKIPPED بده، نه fake-pass
2. **Vision قابل اعتماد ۱۰۰٪ نیست**: همیشه با لاگ/code/network ادغام شود
3. **SPA-404 خطرناک است**: status=200 با body "Not Found" → چک content
4. **keyword matching ضعیف است**: substring match منجر به 404 می‌شود.
   فقط explicit signals (مثل "X page" یا "/path") استفاده شود.
5. **system probe meta است**: feature_present check روی متن AC اش
   ندارد. این الگو در Phase 4 هم رعایت شود برای anything synthetic.
6. **graceful degrade برای همه چیز**: failure هر بخش نباید verify را
   block کند. fallback به Phase 3 behavior.
══════════════════════════════════════════════════════════════════════
# A) Smart Navigation Probe — جزئیات دقیق
══════════════════════════════════════════════════════════════════════
## هدف
وقتی AC اشاره صریح به `/path` ندارد و keyword matching هم نتوانست
route را پیدا کند، به‌جای SKIPPED شدن، یک تلاش هوشمند برای پیدا
کردن صفحه صورت گیرد.
## Flow
1. **navigate به home `/`** (یا frontend_base_url)
2. **استخراج لینک‌های navigation** با Playwright:
   ```python
   nav_links = await page.locator(
       'nav a, [role="navigation"] a, header a, aside a, '
       '.sidebar a, .menu a, [data-testid*="nav"] a'
   ).all()
   links_data = []
   for link in nav_links[:30]:  # cap به ۳۰ تا
       text = (await link.text_content() or "").strip()
       href = await link.get_attribute("href") or ""
       if text and href and not href.startswith(("http", "mailto:", "tel:")):
           links_data.append({"text": text, "href": href})
AI link picker (تابع جدید pick_nav_link_for_ac در
navigation_helper.py):
async def pick_nav_link_for_ac(
    ac_text: str,
    links: List[Dict[str, str]],
    verify_model_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """به AI لیست لینک‌های nav داده می‌شود + متن AC.
    AI انتخاب می‌کند کدام لینک احتمالاً به feature ربط دارد.
    
    Returns: {chosen: dict | None, confidence: "high|medium|low|none",
              reason: str}
    اگر confidence == "none" یا "low" → SKIPPED.
    """
پرامپت AI:
تو در حال بررسی یک پروژه نرم‌افزاری هستی. یک ویژگی (AC) تعریف شده،
و باید از لینک‌های منوی ناوبری انتخاب کنی کدام یکی احتمالاً به
صفحه‌ی این ویژگی می‌رود.
📋 AC: {ac_text}
📍 لینک‌های منو:
1. text="داشبورد" href="/dashboard"
2. text="استراتژی‌ها" href="/strategies"
...
⚠️ راهنما:
- فقط لینکی را انتخاب کن که با احتمال بالا به feature این AC ربط
  دارد (نه شباهت ظاهری اسم).
- اگر هیچ لینکی مرتبط نیست، confidence="none" بده.
- اگر چندتا کاندیدا هست، high-confidence یکی را انتخاب کن.
- متن AC را با name و موقعیت لینک تطبیق بده.
خروجی JSON:
{
  "chosen_idx": int یا null,
  "chosen_text": str یا null,
  "chosen_href": str یا null,
  "confidence": "high" | "medium" | "low" | "none",
  "reason": "یک جمله توضیح"
}
اگر AI لینک انتخاب کرد (confidence high/medium):
probe روی اون لینک کلیک می‌کند
URL جدید چک می‌شود (نباید 404 یا login redirect باشد)
ادامه probe (action loop + vision + ...) روی صفحه جدید
اگر AI نتوانست (confidence low/none):
probe SKIPPED با reason "smart navigation: AI نتوانست لینک
مرتبط در nav menu پیدا کند"
محدودیت‌های ایمنی
حداکثر یک level deep — اگر روی لینک کلیک کردیم و submenu باز شد،
level دوم نمی‌رویم (تا verify خیلی طولانی نشود)
timeout 10s برای AI link picker
اگر nav menu خالی است (هیچ <a> در nav element) → SKIPPED
credentials نباید لو برود — link picker AC text را می‌گیرد، نه
ابرداده‌ی sensitive
فایل‌ها
backend/app/services/verify_runtime/navigation_helper.py (جدید)
backend/app/services/verify_runtime/inspector_probe.py (تغییر:
وقتی route inference is_specific=False بود، به‌جای SKIPPED فوری،
smart navigation تلاش کند)
══════════════════════════════════════════════════════════════════════

B) Backend Log Probe — جزئیات دقیق
══════════════════════════════════════════════════════════════════════

هدف
برای تسک‌هایی که AC شون از feature backend حرف می‌زند (نه UI)،
به‌جای probe UI، probe جدیدی که لاگ‌های Render مرتبط را تحلیل می‌کند.

تشخیص نوع تسک
تابع جدید _classify_task_type(task) -> str:

def _classify_task_type(task) -> str:
    """Returns: 'ui' | 'backend' | 'mixed' | 'unknown'"""
    files = task.target_files or []
    py_count = sum(1 for f in files if str(f).endswith('.py'))
    ts_count = sum(1 for f in files if str(f).endswith(('.ts', '.tsx', '.jsx', '.js')))
    
    # AC text keywords
    all_ac_text = " ".join(...).lower()
    ui_keywords = ['button', 'دکمه', 'panel', 'پنل', 'form', 'فرم',
                   'modal', 'page', 'صفحه', 'view', 'تب', 'sidebar',
                   'navbar', 'click', 'کلیک', 'input', 'فیلد']
    backend_keywords = ['endpoint', 'api', 'model', 'مدل داده',
                       'function', 'تابع', 'service', 'سرویس',
                       'database', 'سنخ‌دار', 'middleware', 'cron',
                       'thread', 'lifecycle', 'crud']
    
    ui_score = sum(1 for kw in ui_keywords if kw in all_ac_text)
    backend_score = sum(1 for kw in backend_keywords if kw in all_ac_text)
    
    # combine with file types
    if py_count > 0 and ts_count == 0 and backend_score > ui_score:
        return 'backend'
    if ts_count > 0 and py_count == 0 and ui_score > backend_score:
        return 'ui'
    if py_count > 0 and ts_count > 0:
        return 'mixed'
    if backend_score > ui_score * 2:
        return 'backend'
    if ui_score > backend_score * 2:
        return 'ui'
    return 'mixed'  # default
Backend Log Probe Flow
تابع جدید run_backend_log_probe(ac, ctx, ac_id, task) در فایل
جدید verify_runtime/backend_log_probe.py:

پیدا کردن watched و service_id های Render مرتبط
Query Render logs:
زمان: ۲۴ ساعت اخیر (یا از آخرین commit تسک)
فیلتر: message شامل نام فایل‌های target یا نام تابع/endpoint
استخراج‌شده از AC
حداکثر ۱۰۰ entry
استخراج endpoint URLs از AC:
regex: (?:GET|POST|PUT|DELETE)\s+(/[a-z0-9/_-]+) در AC text
AI analysis (تابع analyze_backend_logs_for_ac):
async def analyze_backend_logs_for_ac(
    ac_text: str,
    logs: List[Dict],
    target_files: List[str],
    verify_model_id: str,
) -> Dict[str, Any]:
    """
    AI بررسی می‌کند: آیا این لاگ‌ها نشان می‌دهند feature backend
    این AC deploy شده و call می‌شود؟
    
    Returns: {
      "verdict": "deployed_working" | "deployed_not_called" | 
                 "deployed_with_errors" | "not_deployed" | "unclear",
      "reason": str,
      "evidence_lines": List[str],  # خطوط لاگ کلیدی
    }
    """
پرامپت:
تو در حال بررسی deploy یک feature backend هستی.
📋 AC: {ac_text}
📁 فایل‌های هدف: {target_files}
📌 endpoint های استخراج‌شده: {extracted_endpoints}
📊 لاگ‌های Render اخیر (مرتبط با این فایل‌ها):
{logs_formatted}
⚠️ مهم:
- اگر لاگ‌ها نشان می‌دهند endpoint یا تابع call شده + بدون خطا → 
  "deployed_working"
- اگر deploy شده ولی هیچ call ای نمی‌بینی → "deployed_not_called"
- اگر خطا/exception می‌بینی → "deployed_with_errors"
- اگر هیچ نشانه‌ای از این کد در لاگ‌ها نیست → "not_deployed"
- اگر مطمئن نیستی → "unclear"
خروجی JSON:
{
  "verdict": "...",
  "reason": "یک جمله",
  "evidence_lines": ["...", "..."]
}
خروجی probe:
deployed_working → PASSED
deployed_with_errors → FAILED (با evidence_lines)
not_deployed / deployed_not_called → FAILED
unclear → SKIPPED با reason
محدودیت ها
اگر هیچ لاگی پیدا نشد → SKIPPED با "no relevant logs"
اگر RenderLog DB خالی است → SKIPPED با "log collection not active"
حداکثر ۱۰۰ log per probe (تا context AI نشکند)
timeout ۱۵s برای AI analysis
فایل‌ها
backend/app/services/verify_runtime/backend_log_probe.py (جدید)
backend/app/services/verify_runtime/runner.py (تغییر: dispatch
برای backend tasks → run_backend_log_probe)
══════════════════════════════════════════════════════════════════════

C) Code-aware Verifier (Per-AC Commit Analysis) — جزئیات دقیق
══════════════════════════════════════════════════════════════════════

هدف
AI verifier فعلی commits رو در سطح کل تسک می‌خواند. در Phase 4،
برای هر AC جداگانه چک می‌شود که آیا اخیراً پیاده شده یا نه.

Flow
تابع جدید analyze_commits_per_ac در
verify_runtime/code_aware_verifier.py:

دریافت commits اخیر که target_files تسک را تغییر داده‌اند
(از طریق GitHub API که الان داریم)
برای هر AC:
استخراج keyword‌های feature از AC (مثل اسم تابع، endpoint, model)
فیلتر commits که این keyword ها را در diff دارند
AI تحلیل: «آیا این diff این AC را پیاده می‌کند؟»
خروجی per-AC:
{
  "ac_text": "...",
  "code_verdict": "implemented" | "partial" | "not_found" | "unclear",
  "matching_commits": ["abc123", "def456"],
  "key_changes": ["+def create_attachment():", ...],
  "reason": "..."
}
ادغام در runtime_probe_results
هر AC که با Code-aware Verifier تحلیل شد، یک "code_probe" در
runtime_probe_results می‌گیرد (با method="code_analysis"). این
کنار UI probe ها قرار می‌گیرد.

محدودیت ها
فقط برای AC هایی که target_files دارند
حداکثر ۲۰ commit per task به AI داده شود (window زمانی محدود)
timeout ۲۰s per AC analysis
AI cost: بسته‌ی AC ها — تا ۱۰ AC در batch
فایل‌ها
backend/app/services/verify_runtime/code_aware_verifier.py (جدید)
backend/app/services/oversight_verifier.py (تغییر: قبل از
run_probes_for_acs، per-AC code analysis اجرا شود)
══════════════════════════════════════════════════════════════════════

Task Type Routing
══════════════════════════════════════════════════════════════════════

در oversight_verifier.py، پس از classify task type:

task_type = _classify_task_type(task)

# همیشه: code-aware verifier برای AC ها
code_results = await analyze_commits_per_ac(task, acceptance_criteria, ...)
runtime_probe_results.extend(code_results)

# بسته به نوع تسک:
if task_type in ('ui', 'mixed'):
    # Phase 3 system probe + per-step probes (با Smart Navigation اضافه)
    runtime_probe_results.extend(await run_ui_probes(...))

if task_type in ('backend', 'mixed'):
    # Backend Log Probe برای backend AC ها
    for ac in acceptance_criteria:
        if _is_backend_ac(ac):
            res = await run_backend_log_probe(ac, ctx, ac_id, task)
            runtime_probe_results.append(res)

if task_type == 'unknown':
    # هر دو + fallback به Phase 3 system probe
    ...
══════════════════════════════════════════════════════════════════════

Telegram Integration
══════════════════════════════════════════════════════════════════════

mega-bundle.md سکشن‌های جدید:

۸.۱ Smart Navigation Decisions
چه nav linksای پیدا شد؟ AI چی انتخاب کرد؟
confidence + reason per task
۸.۲ Backend Log Analysis (per backend AC)
verdict (deployed_working / not_deployed / ...)
evidence_lines
reason
۸.۳ Code-aware Verdict (per AC)
code_verdict
matching_commits
key_changes excerpts
reason
══════════════════════════════════════════════════════════════════════

UI Changes — Minimal
══════════════════════════════════════════════════════════════════════

inline probe row حالا سه نوع probe جدید را نمایش می‌دهد:

🧭 smart-nav probe (با link انتخاب‌شده)
📊 backend-log probe (با verdict color)
🔍 code-aware probe (با matching commits)
هر کدام آیکن متفاوت و رنگ متمایز.

══════════════════════════════════════════════════════════════════════

Done Definition (سخت‌گیر)
══════════════════════════════════════════════════════════════════════

Smart Navigation کار می‌کند: روی یک تسک با AC که /path ندارد،
probe به home می‌رود، nav menu را می‌خواند، AI لینک مرتبط را
انتخاب می‌کند، روی آن کلیک می‌کند، و ادامه probe می‌دهد.
Backend Log Probe کار می‌کند: روی یک تسک backend (مثل
DebateAttachment)، به‌جای probe UI، probe جدیدی لاگ‌های Render
فیلتر شده را تحلیل می‌کند و verdict می‌دهد.
Code-aware Verifier کار می‌کند: برای هر AC، یک code_probe در
runtime_probe_results ظاهر می‌شود با verdict (implemented /
not_found / ...).
task type classification درست است: تسک trading-system →
"mixed" یا "backend"، تسک "ساخت صفحه login" → "ui".
هیچ بخش موجود از کار نیفتد: Phase 1, 2, 3 + سه فیکس + همه‌ی
تغییرات اخیر.
mega-bundle شامل سکشن‌های جدید: بخش ۸.۱ smart nav، ۸.۲
backend log، ۸.۳ code-aware.
UI inline سه آیکن جدید نمایش می‌دهد.
type-check + python ast پاس.
══════════════════════════════════════════════════════════════════════

محدودیت‌های سراسری
══════════════════════════════════════════════════════════════════════

per-probe AI cost cap: ۲ AI call (یکی link picker، یکی verdict)
per-task additional time: حداکثر ۹۰ ثانیه (روی Phase 3 ۶۰ثانیه)
AI provider failure → graceful fallback به Phase 3 behavior
لاگ‌های Render اگر در DB نبود (سرویس log_stream_service غیرفعال) →
Backend Log Probe SKIPPED با reason صریح
GitHub API rate limit → Code-aware Verifier ممکن است partial باشد
هرگز credentials در لاگ یا inspector_session نشت نکند
══════════════════════════════════════════════════════════════════════

فایل‌های نهایی
══════════════════════════════════════════════════════════════════════

Backend جدید
verify_runtime/navigation_helper.py (Smart Navigation A)
verify_runtime/backend_log_probe.py (Backend Log Probe B)
verify_runtime/code_aware_verifier.py (Code-aware Verifier C)
Backend تغییر
verify_runtime/inspector_probe.py (Smart Navigation hook)
verify_runtime/runner.py (task type routing)
oversight_verifier.py (orchestration + _classify_task_type +
hooks for backend/code probes)
oversight_mega_bundle.py (سه سکشن جدید در bundle)
Frontend
oversight/page.tsx (سه آیکن جدید: 🧭 📊 🔍)
══════════════════════════════════════════════════════════════════════

شکست‌خوردگی‌های مجاز (graceful degrade)
══════════════════════════════════════════════════════════════════════

AI link picker fail → fallback به skip (Phase 3 behavior)
nav menu خالی → skip smart navigation
Render logs خالی → backend log probe skipped
GitHub API timeout → code-aware verifier skipped per AC
task type "unknown" → fallback به همه (UI + Backend + Code)
AI cost overrun → فقط همان probe skipped، بقیه ادامه
══════════════════════════════════════════════════════════════════════

ترتیب پیاده‌سازی (commits جداگانه)
══════════════════════════════════════════════════════════════════════

Commit 1: _classify_task_type در oversight_verifier.py
Commit 2: code_aware_verifier.py (per-AC commit analysis)
Commit 3: backend_log_probe.py (با endpoint extraction)
Commit 4: navigation_helper.py + integration in inspector_probe
Commit 5: task type routing در _verify_task
Commit 6: mega-bundle سه سکشن جدید
Commit 7: UI inline سه آیکن جدید
Commit 8: type-check + final fixes
══════════════════════════════════════════════════════════════════════

تست واقعی (پس از deploy)
══════════════════════════════════════════════════════════════════════

روی تسک‌های زیر تست:

trading-system task (همان که ۱۲ step backend-heavy داشت):
انتظار: task_type="backend" یا "mixed"
backend_log_probe برای هر AC backend اجرا شود
code-aware verifier verdict per AC بدهد
probe های UI کاهش پیدا کنند (به‌جای 9 تا، شاید ۲-۳ تا UI +
چندتا backend/code)
task مناظره (DebateAttachment):
task_type="backend" (مدل، endpoint، service)
backend_log_probe بگوید "not_deployed" (چون code تغییر نکرده)
code-aware verifier per AC بگوید "not_found in recent commits"
task UI خالص (اگر باشد):
task_type="ui"
smart navigation اجرا شود
probe به صفحه واقعی برسد
══════════════════════════════════════════════════════════════════════

شروع کار
══════════════════════════════════════════════════════════════════════

وقتی این پرامپت ارسال شد:

با TodoWrite قطعه‌بندی کن — ترتیب ۸-commit بالا.
هر بخش قبل از کد، در پیام شرح بده که چه تصمیمی گرفتی، چه
trade-off ای انتخاب کردی، و چرا.
هیچ بخش موجود را نشکن — Phase 1, 2, 3 + سه فیکس باید همچنان
کار کنند.
type-check + python ast بعد از هر commit — اگه شکست، فیکس کن
قبل از commit بعدی.
هر تصمیم بزرگ AI prompt را در پیام نشان بده — کاربر می‌خواهد
ببیند AI چه prompt ای می‌گیرد.
در پایان:
خلاصه‌ای از فایل‌های تغییر یافته
نمونه‌ای از output هر سه probe جدید (mocked اگر نمی‌توان live تست کرد)
تست واقعی روی deploy و گزارش
مهم‌ترین درس از Phase 1-3: اگر مطمئن نیستی، SKIPPED بده نه
fake-pass. صداقت در verify بالاتر از پوشش زیاد است.
قبل از شروع، اگر فکر کردی هر یک از این سه ستون منطقی نیست
یا روش بهتری وجود دارد، حتماً در پیام بگو و قبل از کد تأیید
بگیر. این بار اشتباه نباید بشود.

---------------------------
# 🎯 پرامپت Phase 5 V4 — ارتقای کامل Auto-Scan + Task Creation
> **این پرامپت تمام ۱۴ بند درخواست خام را پوشش می‌دهد. هر فاز با reference به بندهای درخواست خام نشان داده شده.**
---
## 📋 فهرست بندهای درخواست خام (Cross-reference)
| # | بند درخواست خام | پوشش در فاز |
|---|---|---|
| **R1** | scan جدا از verify؛ scan ایجاد task، verify بررسی task | مقدمه |
| **R2** | ایده‌گیری از Phase 4 + به‌روزرسانی گزینه‌های UI | کل فازها + فاز ۹ |
| **R3** | پوشش از ریز تا درشت، یک دور برای کل سیستم | فاز ۱ |
| **R4** | scan باید قوی‌تر از verify باشد | کل فازها |
| **R5** | چک‌لیست برای auto-tasks + Smart mode هوشمند | فاز ۷، ۸ |
| **R6** | Telegram notification برای auto-tasks (caption + silent default) | فاز ۸ |
| **R7** | Delta detection + Bidirectional dependency | فاز ۳ |
| **R8** | شناسایی گزینه‌های قدیمی + task برای آن‌ها (⭐ خیلی خیلی مهم) | فاز ۲ |
| **R9** | Smart prompt + Smart checklist (بدون false-positive) | فاز ۷ |
| **R10** | Logic Audit (هدف، منطق، coherence) | فاز ۵ |
| **R11** | مثال trade — باگ منطقی در هماهنگی | فاز ۵ |
| **R12** | Telegram notification system audit | فاز ۶ |
| **R13** | Smart prompt برای manual + auto | فاز ۷ |
| **R14** | Inspector tab integration (session + screenshots + chats + archive) | فاز ۴ |
---
## 📌 مقدمه و فلسفه
### **R1** — scan ≠ verify
| سیستم | چه می‌کند |
|---|---|
| **verify** (Phase 4، تمام) | روی **تسک‌های موجود** بررسی می‌کند آیا انجام شده یا نه |
| **scan** (این Phase 5) | کل سیستم را بررسی می‌کند تا **تسک‌های واقعاً لازم** کشف و ایجاد شوند |
اگر scan خوب کار نکند → تسک واقعاً لازم اصلاً ساخته نمی‌شود → verify هرگز فرصت بررسی آن را پیدا نمی‌کند. **پس scan حتی از verify مهم‌تر است.**
### **R4** — scan باید قوی‌تر از verify باشد
verify شواهد جمع می‌کند برای **یک task مشخص**. scan شواهد جمع می‌کند برای **کل سیستم**. پس scan ابزارهای بیشتری نیاز دارد:
- همه‌ی Phase 4 components (smart_nav, vision, code-aware, backend-log, inspector_probe)
- **به‌علاوه**: comprehensive inventory، purpose extraction، delta analysis، logical coherence، outcome analysis، notification audit، semantic stale detection
### **چهار پایه**
1. **پوشش ریز تا درشت** (R3)
2. **تغییر-آگاهی + bidirectional dependency** (R7)
3. **رفتار-محوری در پرامپت و چک‌لیست** (R9, R13)
4. **logic awareness از روز اول — purpose، coherence، effectiveness** (R10, R11)
### **هدف نهایی**
بعد از یک scan، **تمام تسک‌های واقعاً لازم** کشف و ساخته شوند، **با چک‌لیست هوشمند، با notification صحیح، با session بازرس کامل**:
- features جدید
- features ناقص
- bugs ساختاری
- bugs منطقی (R11)
- features قدیمی و dead options (R8)
- componentهای منطقاً ناسازگار (R10)
- featuresی که کاربر دیگر نمی‌داند چیست (R8) → با AI explanation
- notification ها ناقص یا اشتباه (R12)
---
## 🅰️ فاز ۱ — Comprehensive Inventory + Purpose Extraction
> پوشش **R3** (ریز تا درشت)، پایه برای همه فازهای بعدی
### مسئله
الان `run_deep_scan` فقط ۳۵ فایل deep-read + import graph می‌بیند. backend endpoints، UI elements، DB schema، env vars، configs، **notifications، inspector sessions، UI options** هرگز inventory نمی‌شوند.
### تغییرات
**۱-A. Structural Inventory (۱۲ لایه):**
ماژول جدید: `backend/app/services/scan_v5/comprehensive_inventory.py`
| # | لایه | چه چیزی جمع می‌شود | روش |
|---|---|---|---|
| 1 | Files | همه فایل‌های git-tracked | `git ls-files` |
| 2 | Backend endpoints | همه `@router.{get,post,…}` + WebSocket + background tasks | AST parse |
| 3 | UI elements | همه `<button>`, `<form>`, `<input>`, `<Select>`, `<Link>`, modal triggers, dropdown items | parse `.tsx` |
| 4 | DB schema | همه dataclass + Column + migrations | inspect |
| 5 | Env vars | همه `os.environ.get`, `os.getenv`, `process.env.X` | regex |
| 6 | Config files | همه `.json`, `.yaml`, `.toml`, `.env*` | glob |
| 7 | Dependencies | `requirements.txt`, `package.json` | parse |
| 8 | Scripts | همه `.sh`, `pyproject::scripts`, `package.json::scripts` | parse |
| 9 | Cron/scheduled | همه `apscheduler`, `BackgroundTasks`, `asyncio.create_task` | regex |
| 10 | Routes | همه frontend `app/**/page.tsx` + backend route | walk |
| 11 | **Notification calls (R12)** | همه `notify_event(...)`, `send_telegram(...)`, `bot.send_message(...)` + event_type + silent flag + caption template | regex/AST |
| 12 | **UI options/settings (R8)** | همه checkbox/slider/dropdown در UI + field name در WatchedProject + default value | parse + cross-ref |
**۱-B. Purpose Extraction (R10):**
ماژول جدید: `backend/app/services/scan_v5/purpose_extractor.py`
برای **هر file/module/feature/option** که در inventory هست:

```python
purpose_inventory[item_id] = {
    "stated_purpose": "چه کاری *قرار است* بکند",
    "evidence_sources": ["comments", "docstrings", "tests", "raw_idea", "task_history", "commit_messages"],
    "expected_inputs": [...],
    "expected_outputs": [...],
    "interacting_with": [...],          # سایر componentهای همکار
    "creation_context": {                # R8 — کاربر فراموش کرده چی هست
        "first_seen_commit": "...",
        "first_seen_date": "...",
        "originating_task_id": "...",    # کدام task این را ساخت
        "originating_raw_idea": "...",   # متن خام درخواست
    },
    "current_usage": "...",              # آیا هنوز استفاده می‌شود؟ کجا؟
}
```


**منابع AI برای purpose:**
- محتوای فایل + docstrings + JSDoc
- test files مرتبط
- `WatchedProject.user_notes` (raw_idea اصلی پروژه)
- task history (task هایی که این item را modify کرده‌اند)
- commit messages روی این path
**۱-C. Storage:**
`WatchedProject` فیلدهای جدید:

```python
last_scan_inventory: Optional[Dict[str, Any]] = None
last_scan_purpose_map: Optional[Dict[str, Dict]] = None
last_scan_at_v5: Optional[str] = None  # timestamp scan جدید
```


### Acceptance Criteria فاز ۱
- `inventory.backend_endpoints` ≥ ۵۰
- `inventory.ui_elements` ≥ ۳۰
- `inventory.notification_calls` ≥ ۱۰
- `inventory.ui_options` همه‌ی checkbox/slider/dropdown ها را شامل شود
- `purpose_map` برای ≥ ۸۰% فایل‌های مهم
- برای هر UI option، `creation_context` نشان دهد از کدام task ساخته شد
---
## 🅱️ فاز ۲ — Stale Detection + Feature Inventory Panel
> **مهم‌ترین فاز برای R8 — حل مشکل «گزینه‌های قدیمی که نمی‌دانم چی هست»**
### مسئله (R8 — تأکید سه‌باره)
> «خیلی‌هاش قدیمیه و کار نمی‌کنه و خیلی‌هاش نیاز داره بدونم چی بوده، برای چیه و هر سری باید بهش سر بزنم»
### تغییرات
**۲-A. Structural Stale (۸ نوع):**
ماژول جدید: `backend/app/services/scan_v5/stale_detector.py`
| نوع | شناسایی |
|---|---|
| Dead UI buttons | onClick handler ندارد / empty / به endpoint 404 می‌رود |
| Dead frontend routes | در nav menu نیست و در هیچ Link/router.push نیست |
| Dead backend endpoints | در هیچ frontend fetch نیست + در Render logs ۳۰ روز اخیر صدا نشد |
| Unused functions/classes | reverse import = 0 و entry point نیست |
| Unused dataclass fields | در هیچ‌جا read/write نمی‌شود |
| Unused env vars | تعریف شده ولی هیچ `os.environ.get` |
| Orphan files | reverse import = 0 |
| Stale dependencies | در requirements/package.json هست ولی import نمی‌شود |
**۲-B. Semantic Stale (R10 — ۵ نوع):**
| نوع | شناسایی |
|---|---|
| Purpose-mismatched | `stated_purpose` با `actual_behavior` نمی‌خواند |
| Hidden purpose (R8) | کاربر نمی‌داند چی هست — هیچ doc، نام مبهم، creation_context قدیمی |
| Inconsistent با تغییرات اخیر | کد فرض می‌کند رفتار قدیمی X، ولی X تغییر کرده (نیاز به فاز ۳) |
| Outdated business assumption | threshold/config که با realities فعلی نمی‌خواند |
| Forgotten by user (R8 — جدید) | UI option/setting که کاربر هر بار باید بپرسد چی هست |
**۲-C. AI-Generated Documentation برای هر option (R8):**
برای **هر** UI option/setting/feature/button که در inventory.ui_options یا inventory.ui_elements هست:

```python
ai_documentation[option_id] = {
    "name": "...",
    "what_it_does": "AI explanation — این گزینه دقیقاً چه کاری می‌کند",
    "when_added": "تاریخ + commit",
    "originating_idea": "متن خام درخواست اولیه",
    "current_status": "active | possibly_stale | broken | unknown",
    "dependencies": ["..."],         # forward
    "dependents": ["..."],           # reverse
    "recommended_action": "keep | remove | refactor | document"
}
```


**۲-D. Feature Inventory Panel در UI:**
`frontend/src/app/oversight/page.tsx` — اضافه شدن panel جدید:

```
🗺 Feature Inventory
├─ 🔧 Settings (12)
│   ├─ ✓ verify_mode (active — Phase 4, از task #abc1234)
│   ├─ ✓ dedup_threshold (active — Phase 3)
│   ├─ ⚠️ confirmation_streak_required (possibly_stale — ۹۰ روز unused)
│   └─ ...
├─ 🎛 UI Buttons (45)
├─ 🌐 Backend Endpoints (78)
└─ ⚙️ Env Vars (23)
```


برای هر مدخل: hover → AI explanation کامل.
**۲-E. Task Generation:**
برای هر stale item:
- **cleanup** task (structural) یا **audit** task (semantic) یا **document** task (hidden purpose)
- AC رفتار-محور: «یا حذف شود، یا با docstring/comment توضیح داده شود چرا نگه داشته، یا ارتقا یابد»
- priority بر اساس impact
### Acceptance Criteria فاز ۲
- روی این پروژه ≥ ۵ structural stale + ≥ ۳ semantic stale + ≥ ۸ hidden-purpose options
- Feature Inventory Panel با ≥ ۲۰ مدخل
- هر stale → task با explanation کامل (نه فقط «این unused است»)
- روی project trade مثال کاربر (R11)، scan تشخیص دهد گزینه‌هایی که برای trading فعلاً ضرر می‌دهند
---
## 🅲️ فاز ۳ — Delta Detection + Bidirectional Dependency + Logical Impact
> پوشش **R7** — کاربر صریحاً bidirectional خواست
### مسئله (R7)
> «چه وابستگی‌هایی داشته **به چه چیزهایی وابسته بوده** و **چه چیزهایی بهش وابسته بودن**»
این **دو طرفه** است:
- forward: این فایل به چه چیزی وابسته است
- reverse: چه چیزهایی به این فایل وابسته‌اند
### تغییرات
**۳-A. ذخیره prev state:**
`WatchedProject`:

```python
prev_scan_state: Optional[Dict[str, Any]] = None
# {file_path → {sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash}}
```


**۳-B. compute delta — ۶ نوع (R7: «تغییر کرده یا اضافه شده یا کم شده یا ویرایش شده»):**
| نوع | تشخیص |
|---|---|
| `add` | در current، نه در prev |
| `remove` | در prev، نه در current |
| `modify` | sha متفاوت |
| `rename` | sha مشابه، path متفاوت |
| `move` | content مشابه، path متفاوت |
| `signature-change` | نام تابع ثابت، parameters یا return-type تغییر |
**۳-C. Bidirectional Dependency (R7 صریح):**
ماژول جدید: `backend/app/services/scan_v5/dependency_analyzer.py`
برای هر changed file:

```python
{
    "dependencies": [...],   # forward — file → چه چیزی import می‌کند
    "dependents": [...],     # reverse — چه چیزهایی → این file import می‌کنند
    "logical_dependencies": [...],   # forward منطقی — کدام components روی این تکیه دارند
    "logical_dependents": [...],     # reverse منطقی — این از کدام components انتظار دارد
}
```


تمایز بین **import-based** و **logical**:
- import: AST/grep
- logical: AI روی purpose_inventory تشخیص می‌دهد (مثلاً «این تابع threshold X را می‌خواند، اگر X تغییر کرد رفتار تغییر می‌کند»)
**۳-D. Logical Impact Analysis (R10):**
AI روی هر تغییر + dependents تحلیل می‌کند:
- آیا تغییر این فایل، **منطق** dependents را می‌شکند؟
- مثال: تغییر `threshold=0.65` → `threshold=0.8` → چه componentهای dependent behavior متفاوت نشان می‌دهند؟
- مثال: تغییر فرمت output `parse_signal()` → چه callerها به update نیاز دارند؟
- مثال: حذف یک env var → چه قسمت‌هایی crash می‌کنند؟
**۳-E. Task Generation:**
برای هر changed file + dependent در خطر:
- task با badge `🔄 وابسته به تغییر`
- AC رفتار-محور: «بعد از این تغییر، dependents X و Y باید همچنان behavior Z تولید کنند»
- اگر logical impact پیچیده است → priority بالاتر + reference به scan inspector session
### Acceptance Criteria فاز ۳
- بعد از دو scan متوالی، delta با ۶ نوع تشخیص داده شود
- اگر signature تغییر کرد و ۳ caller دارد، ≥ ۱ task برای بررسی caller ها
- logical impact detection: اگر threshold تغییر کرد، AI تحلیل کند نه فقط alert سینتکسی
- bidirectional dependency: هم dependencies (forward) هم dependents (reverse) برای هر changed item
---
## 🅳 فاز ۴ — Runtime Discovery + Outcome + Inspector Session
> پوشش **R14** — Inspector tab integration — این مهم‌ترین آپشن از قلم افتاده
### مسئله (R14 صریح)
کاربر گفت: «در بررسی‌های عمیق از تب بازرس ویژه هم کمک می‌گیره و **اسکرین‌ها** رو می‌گیره و در تلگرام **همراه با گزارش** بفرسته و **چت‌ها** رو در یه session ثبت کنه و **بایگانی** کنه؟»
این **اصلاً در پرامپت‌های قبلی نبود**. فعلاً Inspector فقط در verify (Phase 4) استفاده می‌شد.
### تغییرات
**۴-A. Runtime Discovery (با ایده از Phase 4):**
ماژول جدید: `backend/app/services/scan_v5/runtime_discovery.py`
| منبع | استفاده |
|---|---|
| `navigation_helper::extract_nav_links_from_page` | nav links واقعی frontend |
| Playwright on each route | screenshot + status code → 404 detection |
| `backend_log_probe::_fetch_relevant_logs` 30-day | endpoints واقعاً called شده |
| `vision_helper::analyze_screenshot` | کشف feature های UI |
| `code_aware_verifier::_fetch_recent_commits_with_diff` | recent commits context |
خروجی: `runtime_state` شامل `routes_alive[]`, `routes_404[]`, `endpoints_called_recently[]`, `endpoints_never_called[]`, `ui_features_visible[]`, `recent_commits[]`.
**۴-B. Outcome Data Collection:**
برای هر پروژه، scan تلاش کند outcome data بیابد:
| نوع پروژه | outcome data |
|---|---|
| Trading | trade logs, P&L history |
| AI/Chat | conversation outcomes |
| Web service | error rates, latency from logs |
| Scheduling | task completion rates |
| Notification | delivery + open rates |
روش‌ها: Render logs filtered + DB tables outcome-naming + file artifacts.
**۴-C. Scan Inspector Session (R14 — حیاتی):**
ماژول جدید: `backend/app/services/scan_v5/scan_inspector_session.py`
**هر scan یک inspector session باز می‌کند** (مشابه verify در Phase 4):

```python
session = create_scan_inspector_session(
    watched_id=...,
    scan_id=...,
    project_name=...,
)
```


**در طول scan:**
- همه AI calls (purpose extraction، stale detection، logic audit، etc.) → پیام در session با role="ai", content=request+response
- همه Playwright actions → پیام با role="action", screenshot=path
- همه screenshot ها → ذخیره روی disk + reference در session
- runtime probe outputs → پیام با role="probe"
**در پایان scan:**
- session archived
- screenshots → آرشیو شده در Telegram (مثل bundle Phase 4)
- bundle PDF تولید می‌شود شامل:
  - findings + tasks ایجاد شده
  - delta summary
  - logic audit findings
  - inventory summary
  - تمام screenshots
- Telegram message + PDF attachment
- در UI، scan session در inspector tab با badge `🔍 Scan Session` (متمایز از `🔬 Verify Session`)
**۴-D. اضافه شدن tab "Scan Sessions" در Inspector UI:**
`frontend/src/app/projects/[id]/page.tsx` (یا هر جا که inspector tab هست):
- علاوه بر لیست verify sessions، scan sessions هم نمایش داده شوند
- کاربر بتواند هر scan session را باز کند و تمام مکالمات + screenshots آن را ببیند
- archive option
### Acceptance Criteria فاز ۴
- بعد از هر scan، یک inspector session با ≥ ۱۰ پیام (AI calls + actions + probes) ساخته شود
- ≥ ۵ screenshot ذخیره شود
- Telegram message + bundle PDF با همه‌ی screenshots و findings ارسال شود
- در Inspector tab، session آرشیو شده دیده شود با badge `🔍 Scan`
- اگر runtime discovery فعال است، روی هر route یک screenshot + Vision analysis
---
## 🅴 فاز ۵ — Logical Audit (Coherence + Anti-pattern + Outcome)
> پوشش **R10, R11** — مهم‌ترین فاز معنایی
### مسئله (R10, R11)
> «یه پروژه دارم که هوشمند ترید کنه ولی بدتر از یه آدم معمولی ترید می‌کنه — باگ منطقی در هماهنگی بین AI و داده‌ها»
scan نباید **فقط خطاها** را ببیند، بلکه **منطق و هدف** را هم.
### تغییرات
**۵-A. Pipeline Coherence Detection:**
ماژول جدید: `backend/app/services/scan_v5/coherence_analyzer.py`
شناسایی pipelines (chains از componentهای همکار) با استفاده از `purpose_inventory[X].interacting_with`.
برای هر chain، AI بررسی coherence:
| الگو | چه بررسی شود |
|---|---|
| **Data pipeline** | schema هر مرحله، handling empty result |
| **AI/LLM chain** | prompt format ↔ model ↔ parser سازگار؟ validation؟ |
| **Business logic (R11 مثال trade)** | signal ↔ risk model، position ↔ account size، stop-loss ↔ timeframe |
| **Auth/Permission** | همه‌ی mutation از permission گذر می‌کند؟ |
| **Feedback loop** | outcome به config/model برمی‌گردد؟ |
| **Notification chain (R12)** | event → notify_event → caption → silent decision → delivery — همه consistent؟ |
**۵-B. Logical Anti-pattern Detection:**
ماژول جدید: `backend/app/services/scan_v5/anti_pattern_detector.py`
AI روی purpose_inventory + کد، این الگوها را پیدا می‌کند:
| Anti-pattern | مثال |
|---|---|
| داده بی‌مصرف | API call، DB write، ولی هیچ read |
| AI بدون validation | response parse می‌شود ولی validity چک نمی‌شود |
| Magic threshold | `> 0.65:` بدون توضیح |
| Conflicting defaults | یک field default متفاوت در جاهای مختلف |
| Silent failure در crucial path | `except: pass` در business logic |
| Broken feedback loop (R11) | outcome لاگ ولی به model نمی‌رسد |
| Stale assumption | کد فرض می‌کند رفتار سرویس X خاصه، X تغییر کرد |
| Over/under-engineering | برای ساده ۵ لایه، برای پیچیده hardcode |
| Conditional inconsistency | conditions با تغییرات اخیر inconsistent |
| Threshold-Outcome mismatch (R11) | parameters نتایج مطلوب تولید نمی‌کنند |
| Notification mismatch (R12) | event critical ولی silent=True، یا opposite |
**۵-C. Hidden Requirements Discovery (R8):**
برای هر feature که کاربر فراموش کرده «چی هست برای چیه»:
- AI روی `creation_context` (از فاز ۱) + task history + commit messages تحلیل
- استخراج: «این feature چه وقت، چرا، با چه هدفی اضافه شد؟»
- نتیجه:
  - هدف منسوخ → task `cleanup`
  - هدف معتبر، پیاده‌سازی ضعیف → task `refactor`
  - هدف معتبر، پیاده‌سازی خوب، docs نیست → task `document`
**۵-D. Outcome-based Effectiveness Audit (R11):**
اگر outcome data دارد (از فاز ۴):
- AI تحلیل می‌کند آیا outcome با `stated_purpose` می‌خواند
- مثال R11: trade — اگر purpose="earn profit" و win-rate=30% → effectiveness LOW
- اگر LOW → task `logic_audit` با priority بالا
**۵-E. Task Generation:**
نوع جدید task: `logic_audit`
- AC outcome-oriented:
  - ❌ «این کد را fix کن»
  - ✅ «بعد از این تغییر، win-rate باید ≥40% یا parameters محافظه‌کارانه‌تر شود»
- AI explanation کامل: چرا اشتباه + چه راه‌حل + چه impact
### Acceptance Criteria فاز ۵
- روی پروژه فعلی ≥ ۳ logic issue + ≥ ۱ pipeline coherence + ≥ ۲ anti-pattern logical
- روی پروژه trade فرضی (R11)، scan باگ منطقی هماهنگی AI-data شناسایی کند
- task `logic_audit` با AC outcome-oriented + AI explanation کامل
---
## 🅵 فاز ۶ — Notification System Audit (R12)
> پوشش **R6, R12** — صریحاً audit notification ها
### مسئله (R12)
> «در پرامپت برای پیام‌رسانی تلگرام هم جایی در نظر گرفتی؟ در بررسی‌ها نوع اطلاع‌رسانیش هم بررسی بشه و بهینه بشه»
### تغییرات
**۶-A. Notification Inventory (از فاز ۱ — لایه ۱۱):**
برای هر `notify_event(...)` call در کد:

```python
notification_inventory[call_id] = {
    "file_path": "...",
    "line": ...,
    "event_type": "...",          # "task_created" | "verify_done" | ...
    "caption_template": "...",
    "silent_default": True | False | None,
    "attachments": [...],
    "trigger_condition": "...",   # کد منطق در کجا fire می‌شود
    "frequency_estimate": "...",  # احتمال در روز
}
```


**۶-B. Notification Coherence Audit (R12):**
AI روی notification_inventory:
| سوال | چه چیزی audit شود |
|---|---|
| caption کامل است؟ | همه‌ی فیلدهای مهم در caption هستند؟ (title, intent, link, attachments) |
| silent/sound مناسب است؟ | event critical → sound. event routine → silent |
| attachments صحیح؟ | task creation → prompt.md، verify done → bundle.pdf، scan done → scan-bundle.pdf |
| timing مناسب؟ | spam جلوگیری شده؟ batching هست؟ |
| stale notifications؟ | event type که دیگر کد آن وجود ندارد |
| missing notifications؟ | event critical که notification ندارد |
| **scan-specific (R12)**: | scan completion notification با همه‌ی مدارک ضروری: findings, tasks created, delta, logic audit results, inspector session reference |
**۶-C. Notification Templates Suggestions:**
برای هر notification که audit آن مشکل دارد → task `notification_audit`:
مثال task:

```yaml
title: "ارتقای caption notification scan_completed"
type: notification_audit
priority: medium
raw_idea: |
  notification scan_completed فعلاً فقط count tasks ایجاد شده را می‌دهد.
  باید شامل: delta summary + logic audit findings + inspector session link
  + attachment با PDF کامل (مشابه verify bundle).
behavior_observable: |
  بعد از این تغییر، notification scan_completed باید شامل:
  - title پروژه
  - تعداد tasks جدید
  - delta count (add/remove/modify)
  - logic audit count
  - link به scan inspector session
  - PDF attachment با همه screenshots و findings
acceptance_signal: |
  بعد از یک scan تست، Telegram message + PDF received با همه فیلدها
```


**۶-D. Audit existing notification flows:**
- `notification_service.py` — همه `notify_event` ها
- `oversight_telegram_compose.py` — caption builders
- `oversight_mega_bundle.py` — bundle PDFs
- بررسی silent default برای auto-tasks (R6)
### Acceptance Criteria فاز ۶
- audit notification ها: ≥ ۲ مورد ارتقا قابل پیشنهاد
- task `notification_audit` ایجاد شود برای هر مورد
- caption template جدید برای scan_completed تعریف شود
- silent default برای auto-task و scan notifications به `True` تنظیم شود
- field `WatchedProject.auto_task_notify_sound: bool = False`
- field `WatchedProject.scan_notify_sound: bool = False`
---
## 🅶 فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)
> پوشش **R5, R9, R13** — برای **manual + auto** هر دو
### مسئله (R9 صریح)
> «در تولید ایده خام به پرامپت، پرامپت در برخی قسمت‌ها دقیق و واضح تولید نمیشه... باید هوشمندتر بشه خود متن پرامپت و چک‌لیستی که ازش تولید میشه»
### مسئله (R13 صریح)
> «این بهبود پرامپت‌نویسی تسک‌ها آیا فقط برای تسک‌های سیستمی یا تسک‌های دستی هم شامل میشه؟»
**جواب: هر دو.**
### تغییرات
**۷-A. ساختار غنی AC (هم manual، هم auto):**
برای **manual** path در `oversight_service.py:idea_to_prompt` (~3454):
برای **auto** path در `oversight_service.py:task creation from scan` (~4700-4740):
برای **scan-generated** path در `oversight_strong_prompt.py:build_strong_prompt`:
هر AC ساختار غنی:

```python
{
    "text": "...",                          # توضیح اصلی (می‌تواند نام بدهد)
    "behavior": "...",                      # رفتار قابل مشاهده — چه چیزی observable است
    "acceptance_signal": "...",             # سؤال قابل-verify
    "business_intent": "...",               # چرا این لازم است
    "alternative_implementations": [...],   # نام‌های جایگزین قابل قبول (R9 — جلوگیری از نام-محوری)
    "non_goals": "...",                     # چه چیزی این AC نیست
    "false_positive_guard": "...",          # چه شواهد ضعیفی نشانه done نیست (R9)
}
```


**۷-B. ساختار غنی task_step (در `_ai_plan_steps_from_idea`):**
برای manual و auto (R13):

```python
{
    "title": "...",
    "scope": "...",
    "behavior_observable": "...",       # خروجی observable
    "verification_hint": "...",         # کجا verify بیابد
    "business_intent": "...",           # چرا این مرحله
    "non_goals": "...",
}
```


**۷-C. Smart Checklist Mode (R5):**
> «حالت هوشمند که برای تولید چک‌لیست یا عدم تولیدش حسب نیاز هست»
`WatchedProject.auto_task_checklist_mode: Literal["auto","always","never"] = "auto"`
- `auto`: AI تصمیم می‌گیرد بر اساس پیچیدگی (≥3 stage → checklist، single-action → skip)
- `always`: همیشه چک‌لیست
- `never`: هرگز
این برای **هم manual و هم auto** کار می‌کند.
**۷-D. Update prompt templates:**
در `oversight_strong_prompt.py`:
- اضافه شدن section "🎯 معیار رفتاری + business intent + alternative implementations"
- AI صریح راهنمایی شود: AC نام-محور بد است، AC رفتار-محور خوب
**۷-E. جلوگیری از false-positive (R9):**
> «جوری هم نشه که سیستم کاری که بد انجام شده... در verify تیک بزنه که کامل شده»
دستورالعمل به AI:
- اگر AC vague → split به sub-behaviors concrete
- هرگز AC بدون `acceptance_signal` نسازد
- `false_positive_guard` فیلد: چه شواهد ضعیفی نباید سبب done شود
- مثال: «اگر فقط فایل با نام وجود دارد، done نیست — باید رفتار X هم باشد»
**۷-F. Integration با فازهای قبلی:**
پرامپت تولید‌شده استفاده کند از:
- `purpose_inventory` (فاز ۱)
- `runtime_state` (فاز ۴)
- `logic_audit_findings` (فاز ۵)
- `notification_audit` (فاز ۶)
### Acceptance Criteria فاز ۷
- **manual** path: پرامپت‌های جدید برای ۳ ایده‌ی نمونه شامل `behavior` + `acceptance_signal` + `business_intent` + `alternative_implementations` + `false_positive_guard`
- **auto** path: همان ساختار برای task های scan-generated
- چک‌لیست‌ها شامل `behavior_observable` در هر step
- mode `auto` در `_ai_plan_steps_from_idea` کار می‌کند برای هر دو
- verify روی same tasks: false-negative ≤ ۲۰%، false-positive ≤ ۵%
- backward compat: AC های قدیمی (فقط text) همچنان کار می‌کنند
---
## 🅷 فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration
> پوشش **R5, R6** — تسک‌های scan باید مثل manual باشند
### مسئله (R5, R6)
- تسک‌های auto-scan الان `prompt + AC` دارند ولی `task_steps` ندارند
- Telegram notification برای آن‌ها audit نشده
- کاربر می‌خواهد silent default
### تغییرات
**۸-A. task_steps برای auto-tasks:**
در `oversight_service.py:4700-4740`:
- بعد از `build_strong_prompt`، اگر `auto_task_checklist_mode != "never"`:
  - if `mode == "always"` → همیشه call `_ai_plan_steps_from_idea`
  - if `mode == "auto"` → AI تصمیم می‌گیرد بر اساس پیچیدگی
**۸-B. Telegram Notification Template (R6):**
`notification_service.py`:

```python
# Caption template برای auto-scan task
{
    "🤖 تسک جدید از scan خودکار",
    "📌 {title}",
    "🎯 {business_intent[:200]}",
    "📋 چک‌لیست: {N step}" if has_steps else None,
    "🧠 Logic concerns: {logic_audit_count}" if has_logic_issues else None,
    "🔄 وابسته به تغییر: {dependent_changes}" if delta_dependent else None,
    "📊 Outcome impact: {outcome_score}" if outcome_data else None,
    "🔗 [لینک کارت]",
    "🔍 [Inspector session]",
}
# Attachments:
- prompt_full.md (full task prompt)
- scan_inspector_session_link
```


**۸-C. Silent default + UI control:**
`WatchedProject` fields:

```python
auto_task_notify_sound: bool = False     # silent for auto-tasks
scan_notify_sound: bool = False           # silent for scan completion
```


در UI: checkbox `🔔 صدای notification برای تسک‌های auto-scan`.
**۸-D. Scan-completion notification:**
علاوه بر notification هر task، یک scan-completion notification:

```
✅ scan تکمیل شد — {project_name}
📊 خلاصه:
- {N} task جدید ایجاد شد
- {N} delta change شناسایی
- {N} stale item
- {N} logic issue
- {N} notification audit
📎 Bundle PDF (با همه screenshots و findings)
🔍 Inspector session: [link]
```


### Acceptance Criteria فاز ۸
- بعد از scan: همه auto-tasks در UI چک‌لیست دارند (اگر mode=auto و پیچیده‌اند)
- caption تلگرام شامل همه فیلدها
- silent default = true
- scan_completed notification با Bundle PDF + Inspector session link
- regression: تسک‌های دستی رفتار قبلی را حفظ کنند
---
## 🅸 فاز ۹ — UI Redesign (R2, R8)
> پوشش **R2** — به‌روزرسانی گزینه‌ها
### مسئله (R2)
> «گزینه‌هاش هم به روز رسانی بشن»
### تغییرات
**۹-A. بازنگری scan_depth modes:**
از (فعلی):

```
quick (3 pass) | standard (6 pass) | deep (12 pass، پیش‌فرض) | thorough (12 + health + roadmap)
```


به:

```
⚡ quick (5 pass) — frontend + backend + security + delta + stale
⚖️ balanced (8 pass — پیش‌فرض جدید) — quick + dependency + completeness + runtime
🔬 deep (12 pass) — همه + impact analysis
🧠 ultra (12 pass + logic audit + outcome + notification audit + inspector session)
```


**۹-B. بازنگری criteria_weights:**
به‌جای ۶ slider:
- preset selector: "general", "security-first", "tests-first", "feature-completeness", "logic-quality"
- sliders در `<details>` (advanced)
**۹-C. بازنگری Smart Task Lifecycle:**
- بررسی هر گزینه: کار می‌کند؟
- label با وضعیت فعلی
**۹-D. گزینه‌های جدید Phase 5:**
`WatchedProject` فیلدهای جدید (همه با default sensible):

```python
# Coverage
inventory_layers: List[str] = ["all"]    # یا subset
# Intelligence
stale_detection_enabled: bool = True
delta_analysis_enabled: bool = True
runtime_discovery_enabled: bool = True
outcome_data_enabled: bool = True
logic_audit_enabled: bool = True
notification_audit_enabled: bool = True
inspector_session_enabled: bool = True   # R14
# Lifecycle
auto_task_checklist_mode: str = "auto"   # R5
cleanup_tasks_enabled: bool = True
# Notifications
auto_task_notify_sound: bool = False     # R6
scan_notify_sound: bool = False          # R6
```

**۹-E. بازطراحی Layout — ۴ tabs (به‌جای ۳):**
| Tab | محتوا |
|---|---|
| **🔍 Coverage** | scan_depth + inventory_layers + criteria preset + auto_models |
| **🧠 Intelligence** | stale + delta + runtime + outcome + logic_audit + smart-prompt + inspector_session |
| **🔁 Lifecycle** | dedup + auto-regenerate + checklist mode + cleanup |
| **🔔 Notifications** | auto_task_sound + scan_sound + notification_audit + custom templates |
**۹-F. AI explanation برای هر گزینه (R8):**
هر گزینه دارای help icon ⓘ + AI-generated description (از فاز ۲):
- این گزینه دقیقاً چه می‌کند
- کِی اضافه شد
- وضعیت فعلی (active / possibly stale / unknown)
**۹-G. Feature Inventory Panel (R8):**
panel جدید در UI با لیست همه options + AI explanation (از فاز ۲).
### Acceptance Criteria فاز ۹
- در UI، ۴ tab وجود دارد
- mode `balanced` پیش‌فرض جدید
- mode `ultra` در دسترس
- backward compat: scan_depth قدیمی همچنان کار کند
- هر گزینه دارای tooltip + AI explanation
- Feature Inventory Panel functional
---
## 🅹 فاز ۱۰ — Meta-validation
> خود این پرامپت قابل verify باشد
### مسئله
کاربر می‌خواهد این پرامپت به task تبدیل شود و توسط verify Phase 4 سنجیده شود.
### تغییرات
**۱۰-A. این پرامپت به task تبدیل:**
- ایده‌ی خام = این متن
- AC ها = AC های هر فاز ۱-۹
- task_steps = ۱۰ فاز
**۱۰-B. AC قابل-verify دقیق:**
هر AC در هر فاز measurable نوشته شده (مثلاً «≥ ۵ stale item کشف شود»).
**۱۰-C. Iteration loop:**
- پیاده‌سازی → verify deep (Phase 4) → نتیجه
- اگر `done < 100%` → iteration بعدی
- اگر `done = 100%` → فاز بعدی
- log در `phase5_meta_validation.md`
**۱۰-D. شناسایی verify bugs:**
- اگر کار واقعاً انجام شد ولی verify گفت not_done → باگ verify
- اگر کار نشد ولی verify گفت done → باگ verify (مهم‌تر، false-positive)
- log همه‌ی این موارد
### Acceptance Criteria فاز ۱۰
- پرامپت نهایی شامل ۱۰ task_step
- هر step دارای `behavior_observable` + `verification_hint`
- بعد از پیاده‌سازی همه فازها، verify deep این task را ≥ ۱۰/۱۰ done گزارش دهد
- log باگ‌های verify identified
---
## 🗂️ نقشه آدرس‌ها
| فاز | فایل | نوع |
|---|---|---|
| 1 | `backend/app/services/scan_v5/comprehensive_inventory.py` | new |
| 1 | `backend/app/services/scan_v5/purpose_extractor.py` | new |
| 1 | `backend/app/services/oversight_service.py:161` | + 3 fields |
| 2 | `backend/app/services/scan_v5/stale_detector.py` | new |
| 2 | `backend/app/services/scan_v5/feature_documenter.py` | new |
| 2 | `frontend/src/app/oversight/page.tsx` | + Feature Inventory panel |
| 3 | `backend/app/services/scan_v5/delta_analyzer.py` | new |
| 3 | `backend/app/services/scan_v5/dependency_analyzer.py` | new |
| 3 | `backend/app/services/oversight_service.py:161` | + `prev_scan_state` |
| 4 | `backend/app/services/scan_v5/runtime_discovery.py` | new |
| 4 | `backend/app/services/scan_v5/outcome_analyzer.py` | new |
| 4 | `backend/app/services/scan_v5/scan_inspector_session.py` | new |
| 4 | `frontend/src/app/projects/[id]/page.tsx` (Inspector tab) | + Scan Sessions section |
| 5 | `backend/app/services/scan_v5/coherence_analyzer.py` | new |
| 5 | `backend/app/services/scan_v5/anti_pattern_detector.py` | new |
| 5 | `backend/app/services/oversight_service.py` | + task type "logic_audit" |
| 6 | `backend/app/services/scan_v5/notification_auditor.py` | new |
| 6 | `backend/app/services/notification_service.py` | audit |
| 6 | `backend/app/services/oversight_telegram_compose.py` | + scan template |
| 7 | `backend/app/services/oversight_strong_prompt.py` | + behavior + business_intent + false_positive_guard |
| 7 | `backend/app/services/oversight_service.py:3454` (idea_to_prompt) | structured AC |
| 7 | `backend/app/services/oversight_service.py:2673` (_ai_plan_steps_from_idea) | structured steps |
| 7 | `backend/app/services/oversight_service.py:4700-4740` (auto-task creation) | apply same to auto |
| 8 | `backend/app/services/notification_service.py` | new templates |
| 8 | `backend/app/services/oversight_mega_bundle.py` | + scan-bundle PDF |
| 9 | `frontend/src/app/oversight/page.tsx` | 4 tabs redesign |
| 9 | `backend/app/services/oversight_service.py:161` | + ۱۰ field جدید |
| 10 | meta — هر فاز AC مشخص | — |
---
## 🎯 ترتیب اجرا
**Round 1 — پایه:**
1. فاز ۱ — Comprehensive Inventory + Purpose
**Round 2 — تحلیل ساختاری:**
2. فاز ۲ — Stale Detection + Feature Inventory Panel
3. فاز ۳ — Delta + Bidirectional Dependency
**Round 3 — تحلیل دینامیک:**
4. فاز ۴ — Runtime + Outcome + Inspector Session
5. فاز ۵ — Logical Audit
6. فاز ۶ — Notification Audit
**Round 4 — تولید + UI:**
7. فاز ۷ — Smart Prompt (manual + auto)
8. فاز ۸ — Auto-tasks Like Manual + Telegram
9. فاز ۹ — UI Redesign
**Round 5 — نهایی:**
10. فاز ۱۰ — Meta-validation
هر Round با runtime test قبل از push. در پایان: یک scan کامل روی این پروژه برای meta-validation.
--------------------------
در گزارش نهایی باید تمام اجزایی که بررسی کرده به صورت ریز در گزارش بیاد .. حالا بخش تسک درست کردن و پرامپت و چک لیست مطابقش درست کردن که تو گزارش میاد جدا
یه گزارش جدا باید تو همون متنی که ارسال میکنه در تلگرام هم پیوستش باشه که تمام موارد رو که بررسی کرده مشروح و با جزئیات بنویسه 
اینها که زیر نوشتم و در تنظیمات هر کارت پروژه قرارداده شده باید هر کدوم توضیحات مفصلی داشته باشه و هیچ کار ناقصی پذیرفته نیست :

🗑 stale + forgotten options

🔄 delta + bidirectional dep

🌐 runtime discovery

📊 outcome data

🧠 logic audit

🔔 notification audit

🔍 inspector session

🗑 cleanup tasks
-----------------------------
🔒 امنیت:


🛠 کیفیت:


🧪 تست:


✅ کامل بودن:
------------------------------
# 🔬 Bug C6 — Verify v6: Deep Code-Content Analysis + Iterative Refinement (v2 نهایی)

## 🎯 هدف اصلی

(بدون تغییر از نسخهٔ قبل — حفظ همان framing)

verify فعلی روی ~۴۰٪ تسک‌ها (آن‌هایی که backend یا multi-step هستند) false negative می‌دهد. این bug، verify را به سطح "همان‌چه یک developer واقعی با grep دستی پیدا می‌کند" می‌رساند. پایهٔ ۵ فاز قبلی **حفظ می‌شود**؛ فقط لایه‌های زیرین قوی می‌شوند.

این bug **خود قابل verify** است (meta-test) — یعنی verify v6 وقتی روی این bug اجرا شد، باید همهٔ AC هایش را به‌درستی done ببیند.

---

## 🔍 ۶ گپ بنیادی + ۲ بهبود اضافه (در v2)

### گپ ۱ — حافظهٔ تکه‌تکه vs کامل

#### وضعیت فعلی
verify فقط AC text + commit diff + screenshot + repo tree را دارد.

#### راه‌حل
ماژول جدید: `backend/app/services/verify_runtime/context_builder.py`

ساختار `VerifyContext` dataclass:
```python
@dataclass
class VerifyContext:
    task: OversightTask                       # ref فقط
    watched: WatchedProject                   # ref فقط
    raw_idea_full: str                        # cap 50KB
    prompt_full: str                          # cap 100KB
    task_steps_full: List[Dict]               # همه (no cap چون داخل تسک)
    prompt_history: List[Dict]                # آخرین ۳ نسخه
    verify_history: List[Dict]                # آخرین ۵ گزارش
    consolidation_meta: Optional[Dict]        # اگر super-task
    merged_source_tasks: List[Dict]           # cap 30 (top by priority)
    scan_metadata: Optional[Dict]             # last_scan_metadata
    repo_tree: List[str]                      # paths only، cap 5000
    commits_recent: List[Dict]                # cap 50 commits
    # کش‌های in-memory per-verify-run
    file_content_cache: Dict[str, str] = field(default_factory=dict)
    file_grep_cache: Dict[Tuple[str, str], List[Dict]] = field(default_factory=dict)
    # observability
    trace: List[Dict] = field(default_factory=list)  # هر تصمیم append می‌شود
    config: "VerifyConfig" = ...               # ↓ بخش config
    files_fetched_count: int = 0
    grep_calls_count: int = 0
    ai_calls_count: int = 0
```

تابع `async def build_verify_context(task, watched, *, config) -> VerifyContext`:
- caps را اعمال می‌کند
- repo_tree یک‌بار از GitHub fetch می‌شود (با cache روی sha)
- در ابتدای `verify_task()` صدا زده می‌شود و در همهٔ probes پاس داده می‌شود

---

### گپ ۲ — file content reading به‌جای commit diff

(بدون تغییر از نسخهٔ قبل، فقط افزودنی‌ها در examples)

ماژول جدید: `backend/app/services/verify_runtime/code_content_searcher.py`

API عمومی:

```python
async def fetch_file_content(
    repo_full_name: str, path: str, ref: str = "main",
    *, token: str,
    cache: Dict[str, str],
    max_size_bytes: int = 500_000,
) -> Optional[str]
```
- GET `/repos/{owner}/{repo}/contents/{path}?ref={ref}`
- base64 decode از field `content`
- cache روی key=f"{path}@{ref}"
- skip اگر size > 500KB یا content-type غیر متنی
- بازگشت None در صورت 404/403/error
- log در `context.trace`

```python
async def grep_token_in_files(
    token: str, paths: List[str],
    repo_full_name: str, ref: str,
    *, github_token: str,
    cache: Dict[Tuple[str, str], List[Dict]],
    file_content_cache: Dict[str, str],
    context_lines: int = 2,
    max_matches_per_file: int = 5,
) -> List[Dict]
```
- regex `re.finditer(re.escape(token), content, re.IGNORECASE)`
- خروجی: `[{path, line_number, snippet, before_lines, after_lines}, ...]`
- cap per file
- cache روی key=(path, token)

```python
async def smart_grep_for_ac(
    ac_text: str, target_files: List[str],
    repo_full_name: str, ref: str,
    *, context: VerifyContext,
) -> Dict[str, List[Dict]]
```
- `identifiers = extract_identifiers(ac_text)`
- top-K=15 identifiers (sorted by specificity)
- برای هر identifier در همهٔ target_files
- خروجی: `{identifier: [match, ...]}`

```python
def extract_identifiers(text: str) -> List[str]
```

**🆕 (v2 — کاستی ۱) مثال concrete:**

```python
# مثال ۱: ورودی فارسی + identifier پایتون
text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
extract_identifiers(text) →
    ['view_preferences', 'WatchedProject']

# مثال ۲: ورودی انگلیسی + camelCase
text = "Add useViewPrefs hook for fetching preferences"
extract_identifiers(text) →
    ['useViewPrefs', 'fetching', 'preferences']  # 'Add' حذف چون stop-word

# مثال ۳: ورودی mixed با file path
text = "تابع _record_title_change در oversight_service.py"
extract_identifiers(text) →
    ['_record_title_change', 'oversight_service']

# مثال ۴: کلمات generic - باید filter شوند
text = "بهبود سیستم نمایش"
extract_identifiers(text) →
    []  # هیچ identifier specific نیست → fallback به AI
```

regex‌های دقیق:
- `snake_case`: `r"\b[a-z][a-z0-9_]{2,}\b"` (با حداقل یک underscore یا طول ≥۴)
- `dunder`: `r"\b_[a-z][a-z0-9_]+\b"`
- `camelCase`: `r"\b[a-z][a-zA-Z0-9]{3,}\b"` که حداقل یک حرف بزرگ داشته باشد بعد از index 0
- `PascalCase`: `r"\b[A-Z][a-zA-Z0-9]{3,}\b"`
- `function_call`: `r"\b(\w+)\s*\("`
- `file_path`: `r"\b[\w/.-]+\.(py|tsx?|jsx?|json|yaml|md)\b"`

stop-words (cap ~۱۰۰): فارسی + انگلیسی common words (`the, and, for, this, that, user, system, change, ...` / `بهبود, تغییر, سیستم, پروژه, ...`)

specificity score برای sort:
- length × ۱.۰
- snake_case bonus: +۲
- dunder bonus: +۳ (خیلی specific)
- file_path bonus: +۴ (خیلی specific)

خروجی: top-K=15 unique identifiers، sorted desc by specificity

---

### گپ ۳ — AC matching: file content به‌جای basename

(۴ مرحلهٔ A→B→C→D، بدون تغییر منطقی — فقط نام‌گذاری مشخص‌تر)

تابع‌های جدا برای traceability:
```python
async def _phase_a_basename_match(ac, target_files, context) -> ProbeResult
async def _phase_b_content_grep(ac, target_files, context) -> ProbeResult
async def _phase_c_extended_repo_grep(ac, context) -> ProbeResult
async def _phase_d_ai_judgment(ac, context) -> ProbeResult
```

orchestrator: `analyze_acs_with_content_grep(acs, context)` که چهار phase را به‌ترتیب می‌چرخاند، هر phase که done قطعی داد، early-exit.

---

### گپ ۴ — Iterative orchestrator

ماژول جدید: `backend/app/services/verify_runtime/iterative_orchestrator.py`

```python
@dataclass
class ProbeResult:
    probe_name: str
    verdict: str  # "done" | "partial" | "not_done" | "unclear"
    confidence: float  # 0.0..1.0
    evidence: List[str]
    error: Optional[str] = None
    elapsed_ms: int = 0
```

```python
async def iterative_verify_step(
    step: Dict, context: VerifyContext,
    *, max_iterations: int = 3,
) -> Tuple[ProbeResult, List[ProbeResult]]:
    """
    خروجی: (final_aggregated_result, all_iteration_results)
    """
```

#### Iteration 1 — Standard probes (~۵-۱۰s)
- vision probe (فقط اگر classification = frontend/fullstack)
- code_aware probe (basename + diff window)
- content_grep probe (smart_grep_for_ac روی target_files)
- playwright probe (اگر URL probe موجود)

aggregate → verdict + confidence
- اگر confidence ≥ 0.8 → finalize ✅
- اگر confidence < 0.8 → escalate to iteration 2

#### Iteration 2 — Aggressive content grep (~۱۵-۳۰s)
- file scope توسعه می‌یابد: full repo tree با filter به‌ترتیب:
  1. extensions مرتبط (py/tsx/ts/jsx/js)
  2. paths که با AC text overlap دارند (مثلاً اگر AC نام فولدر گفته)
  3. cap: ۵۰ فایل اضافی
- top-K identifiers (نه فقط top-15، بلکه top-25)
- AI rerun با evidence جدید
- aggregate → verdict + confidence
- اگر confidence ≥ 0.7 → finalize ✅ (آستانهٔ کمتر چون evidence بیشتر داریم)
- اگر < 0.7 → escalate to iteration 3

#### Iteration 3 — Strong model escalation (~۳۰-۶۰s)

**🆕 (v2 — کاستی ۲) Model escalation tier صریح:**

```python
async def _strong_model_judgment(ac, context, prior_results):
    """
    استفاده از model tier بالاتر برای judgment نهایی.
    chain:
        1. تلاش با "gpt-4o" (اگر در MODEL_REGISTRY باشد و key موجود)
        2. fallback به "claude-opus-4-7" یا "claude-sonnet-4-6"
        3. fallback به همان DEFAULT_EXTRACTION_MODEL_ID (no escalation possible)
    """
    from ..core.models_registry import pick_best_extraction_model
    strong_pref = ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"]
    model_id = None
    for cand in strong_pref:
        if _model_available(cand):
            model_id = cand
            break
    if not model_id:
        model_id = pick_best_extraction_model()  # fallback
```

ورودی به strong model:
- متن کامل AC
- تمام evidence از iteration 1 و 2
- file content snippets (cap 50KB)
- repo_tree subset مرتبط
- task.prompt full (cap 50KB)

خروجی: ProbeResult با verdict + reasoning detailed

finalize بدون escalation بیشتر (max 3).

---

### گپ ۵ — Smart probe selection

`_classify_step_for_probe` بازنویسی با ۱۰ قاعده (بدون تغییر از v1).

اضافه: classification result در `context.trace` log می‌شود.

---

### گپ ۶ — Confidence-weighted verdict

`aggregate_verdicts(results: List[ProbeResult]) -> ProbeResult`:

```python
WEIGHTS_BY_PROBE = {
    "content_grep_strong": 3.0,    # ≥۲ identifier در ≥۱ فایل
    "content_grep_weak": 1.5,      # ۱ identifier
    "code_aware_basename": 1.0,    # فقط basename match
    "playwright": 2.0,             # deterministic
    "ai_verifier": 1.0,
    "vision_frontend": 0.5,
    "vision_backend": 0.0,         # vision در backend = weight 0
    "strong_model": 2.5,           # iteration 3
}

def aggregate_verdicts(results):
    # حذف unclear/error
    valid = [r for r in results if r.verdict not in ("unclear",) and not r.error]
    if not valid:
        return ProbeResult("aggregate", "unclear", 0.0, ["all probes inconclusive"])
    
    # weighted vote
    scores = {"done": 0.0, "partial": 0.0, "not_done": 0.0}
    total_weight = 0.0
    for r in valid:
        w = _get_weight(r) * r.confidence  # confidence × weight
        scores[r.verdict] = scores.get(r.verdict, 0) + w
        total_weight += w
    
    winner = max(scores, key=scores.get)
    final_confidence = scores[winner] / total_weight if total_weight else 0
    
    # collect evidence
    evidence = []
    for r in valid:
        if r.verdict == winner:
            evidence.extend(r.evidence)
    
    return ProbeResult("aggregate", winner, final_confidence, evidence[:10])
```

---

### 🆕 (v2 — کاستی ۳) **بهبود ۷ — Per-AC state cache**

#### مشکل
هر بار verify اجرا می‌شود، همهٔ AC ها از صفر چک می‌شوند. اگر AC در ۳ run اخیر `done` با confidence > 0.85 بود و فایل‌های مرتبط تغییر نکردند، re-verify لازم نیست.

#### راه‌حل
فیلد جدید روی `OversightTask`:
```python
ac_verify_cache: Dict[str, Any] = field(default_factory=dict)
# ساختار:
# {
#   "<ac_hash>": {
#     "verdict": "done",
#     "confidence": 0.92,
#     "last_verified_at": ISO,
#     "files_checksum": "abc123",  # checksum از mtime یا sha فایل‌های مرتبط
#     "consecutive_done_count": 3,
#     "evidence": ["..."]
#   }
# }
```

منطق:
1. قبل از verify هر AC:
   - hash از متن AC + classification
   - چک cache
   - اگر `consecutive_done_count >= 3 AND files_checksum unchanged AND age < 7 days`:
     - skip probes، از cache استفاده کن
     - log: `"AC X: cached done (skipped 3 probes)"`
2. بعد از verify:
   - اگر verdict = done و confidence > 0.85:
     - `consecutive_done_count += 1`
     - `files_checksum = compute_files_checksum(target_files)`
   - اگر verdict != done:
     - `consecutive_done_count = 0`
     - cache invalidate

`compute_files_checksum`: sha256 از target_files content (یا sha روی commit ref اگر در GitHub).

flag config: `enable_ac_cache: bool = True` (پیش‌فرض True). user می‌تواند با `?force_full_verify=true` بای‌پاس کند.

---

### 🆕 (v2 — کاستی ۴) **بهبود ۸ — Observability/Trace mode**

#### مشکل
کاربر نمی‌تواند بفهمد چرا verify گفته partial. باید بتواند trace کامل را ببیند.

#### راه‌حل

تمام تصمیم‌های verify در `context.trace` log می‌شوند:
```python
context.trace.append({
    "ts": iso,
    "phase": "iteration_2_content_grep",
    "ac_index": 5,
    "ac_text": "اضافه کردن فیلد view_preferences...",
    "decision": "escalate_to_iter_3",
    "reason": "confidence 0.6 < threshold 0.7",
    "evidence": [...],
    "probe_results": [...],
    "elapsed_ms": 1234,
})
```

سپس روی `VerificationReport`:
```python
@dataclass
class VerificationReport:
    ...
    verify_trace: List[Dict] = field(default_factory=list)  # full trace
    ac_probe_details: List[Dict] = field(default_factory=list)  # per-AC summary
    verify_version: str = "v6"
    config_used: Dict = field(default_factory=dict)  # config snapshot
```

endpoint جدید:
```
GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}
→ trace کامل آخرین (یا specific) verify
```

UI: یک accordion "🔍 Trace" در زیر هر AC در دیتیل تسک — نمایش step-by-step تصمیمات.

---

### 🆕 (v2 — کاستی ۵) **بهبود ۹ — Centralized VerifyConfig**

#### مشکل
هر knob (max_iterations, max_files, model_tier, ...) جدا گفته شده. متمرکز نیست.

#### راه‌حل
ساختار `VerifyConfig`:
```python
@dataclass
class VerifyConfig:
    # iteration limits
    max_iterations: int = 3
    iter1_confidence_threshold: float = 0.8
    iter2_confidence_threshold: float = 0.7
    
    # content grep
    enable_content_grep: bool = True
    max_files_per_run: int = 50
    max_file_size_bytes: int = 500_000
    max_identifiers_per_ac: int = 15
    iter2_max_extra_files: int = 50
    iter2_max_identifiers: int = 25
    
    # model tier
    strong_model_preference: List[str] = field(default_factory=lambda: [
        "gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"
    ])
    
    # cache
    enable_ac_cache: bool = True
    ac_cache_max_age_days: int = 7
    ac_cache_consecutive_threshold: int = 3
    
    # confidence weights
    weights: Dict[str, float] = field(default_factory=lambda: {
        "content_grep_strong": 3.0,
        "content_grep_weak": 1.5,
        "code_aware_basename": 1.0,
        "playwright": 2.0,
        "ai_verifier": 1.0,
        "vision_frontend": 0.5,
        "vision_backend": 0.0,
        "strong_model": 2.5,
    })
    
    # observability
    enable_trace: bool = True
    trace_max_entries: int = 1000
```

ذخیره در `WatchedProject.verify_v6_config: Optional[Dict] = None` (اگر None، defaults).

endpoint: `GET/PATCH /api/oversight/watched/{id}/verify-v6-config`

---

## 🏗 معماری نهایی (با بهبودها)

```
verify_task(task_id, verify_v6=True)
│
├── load WatchedProject.verify_v6_config → VerifyConfig
│
├── build_verify_context(task, watched, config) → VerifyContext
│
├── for each AC (یا task_step):
│    │
│    ├── classify_ac(ac, context) → classification ("frontend"|"backend"|...)
│    │
│    ├── 🆕 check ac_verify_cache:
│    │    if cache_hit_with_freshness:
│    │        → use cached ProbeResult, log "cached"
│    │        → skip iterations
│    │    else:
│    │        → run iterative verify
│    │
│    ├── iterative_verify_step(ac, context, max_iter=3):
│    │    │
│    │    ├── iteration 1: standard probes
│    │    │    ├── content_grep (smart_grep_for_ac)
│    │    │    ├── code_aware (basename + diff)
│    │    │    ├── vision (if frontend/fullstack)
│    │    │    └── playwright (if URL)
│    │    │
│    │    ├── aggregate_verdicts(probes) → ProbeResult
│    │    ├── if confidence ≥ 0.8 → finalize
│    │    │
│    │    ├── iteration 2: aggressive content_grep
│    │    │    ├── full repo grep (filtered)
│    │    │    ├── more identifiers
│    │    │    └── AI rerun with new evidence
│    │    │
│    │    ├── aggregate → ProbeResult
│    │    ├── if confidence ≥ 0.7 → finalize
│    │    │
│    │    ├── iteration 3: strong model escalation
│    │    │    └── _strong_model_judgment(ac, context, prior_results)
│    │    │
│    │    └── finalize unconditionally
│    │
│    ├── update ac_verify_cache:
│    │    if verdict==done && confidence > 0.85:
│    │        consecutive_done_count++, files_checksum updated
│    │    else:
│    │        cache invalidated
│    │
│    └── append to verify_trace + ac_probe_details
│
├── aggregate per-AC → overall task verdict
│
├── apply existing all_steps_done rule + streak logic
│
├── apply title reassess (C5)
│
└── persist + create VerificationReport with verify_trace
```

---

## 📁 File map (v2)

| فایل | تغییر | scope |
|---|---|---|
| `backend/app/services/verify_runtime/context_builder.py` | **جدید** | `VerifyContext`, `VerifyConfig`, `build_verify_context` |
| `backend/app/services/verify_runtime/code_content_searcher.py` | **جدید** | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` + ۴ مثال concrete در docstring |
| `backend/app/services/verify_runtime/iterative_orchestrator.py` | **جدید** | `ProbeResult`, `iterative_verify_step`, `aggregate_verdicts`, `_strong_model_judgment` |
| `backend/app/services/verify_runtime/ac_cache_service.py` | **جدید** | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| `backend/app/services/verify_runtime/code_aware_verifier.py` | بازنویسی phase A→B→C→D با نام تابع‌های صریح | همان فایل، +۲۰۰ خط |
| `backend/app/services/oversight_verifier.py` | `_classify_step_for_probe` با ۱۰ قاعده + integration با orchestrator + flag `verify_v6` | همان فایل |
| `backend/app/services/oversight_service.py` | اضافه کردن `ac_verify_cache` و `verify_v6_config` به dataclass ها | همان فایل |
| `backend/app/services/verify_runtime/__init__.py` | export نام‌های جدید | همان فایل |
| `backend/app/api/routes/oversight.py` | endpoint های جدید: `verify-trace`, `verify-v6-config` (GET/PATCH) + پارامتر `verify_v6=True\|False` در verify endpoint | همان فایل |
| `backend/tests/test_code_content_searcher.py` | **جدید** | unit tests برای `extract_identifiers` با ۴ مثال + grep test |
| `backend/tests/test_iterative_orchestrator.py` | **جدید** | unit tests برای `aggregate_verdicts` با ۵ سناریو |

---

## 🧪 معیار موفقیت + meta-test (v2 — concrete AC list)

این bug **باید با خودش verify شود**. ۱۲ AC مشخص (افزایش از ۱۰ به ۱۲):

| # | AC | identifier‌های قابل grep |
|---|---|---|
| 1 | فایل `context_builder.py` با کلاس `VerifyContext` و تابع `build_verify_context` | `VerifyContext`, `build_verify_context`, `VerifyConfig` |
| 2 | فایل `code_content_searcher.py` با ۴ تابع + ۴ مثال در docstring | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` |
| 3 | فایل `iterative_orchestrator.py` با ۳ symbol + strong model escalation | `iterative_verify_step`, `aggregate_verdicts`, `ProbeResult`, `_strong_model_judgment` |
| 4 | فایل `ac_cache_service.py` با ۳ تابع cache | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| 5 | `_classify_step_for_probe` با ۱۰ قاعدهٔ explicit در `oversight_verifier.py` | `"backend"`, `"frontend"`, `"fullstack"`, `"infra"`, `"test_only"`, `"doc_only"`, `"manual_only"` |
| 6 | `code_aware_verifier.py` با ۴ تابع جدید phase | `_phase_a_basename_match`, `_phase_b_content_grep`, `_phase_c_extended_repo_grep`, `_phase_d_ai_judgment` |
| 7 | فیلد جدید `ac_verify_cache` روی `OversightTask` dataclass | `ac_verify_cache` در `oversight_service.py` |
| 8 | فیلد جدید `verify_v6_config` روی `WatchedProject` dataclass | `verify_v6_config` |
| 9 | `VerificationReport` با فیلدهای `verify_trace`, `ac_probe_details`, `verify_version`, `config_used` | همان نام‌ها در dataclass |
| 10 | endpoint `GET /tasks/{task_id}/verify-trace` و `GET/PATCH /watched/{id}/verify-v6-config` | router decorators |
| 11 | پارامتر `verify_v6: bool = True` در `verify_task` signature | `verify_v6` در function def |
| 12 | حداقل ۲ فایل تست: `test_code_content_searcher.py` (۴ مثال extract_identifiers) و `test_iterative_orchestrator.py` (۵ سناریو aggregate_verdicts) | اسامی فایل + assertion های concrete |

**معیار سخت‌گیرانه:** vary v6 وقتی روی این bug اجرا شد، باید **≥۱۱ از ۱۲ AC** را done ببیند (با confidence ≥ 0.8).

اگر کمتر → یعنی verify v6 خودش هنوز ضعیف است → bug C6 fail.

---

## ⚠️ Edge cases (v2 — افزایش‌یافته)

1. **GitHub rate limit**: cache aggressive + cap 50 file. اگر rate limit hit شد، fallback به v5 منطق.
2. **Large file**: skip > 500KB (configurable).
3. **Binary file**: skip اگر non-text Content-Type.
4. **Token not in private repo**: fallback graceful.
5. **Identifier spam**: AC تمام stop-words → fallback به AI.
6. **Multi-language**: identifiers از فارسی+انگلیسی هر دو (با regex unicode-aware).
7. **Recursion**: orchestrator فقط probes را call می‌کند، نه `verify_task`.
8. **Memory**: caps روی هر فیلد VerifyContext.
9. **Backward compat**: `verify_v6=False` → مسیر v5.
10. **A/B**: random seed برای ۵۰/۵۰ split بین v5/v6 (debug).
11. **🆕 (v2) Cache invalidation race**: اگر دو verify همزمان روی یک تسک شروع شدند، cache lock با `asyncio.Lock` per-task.
12. **🆕 (v2) Strong model unavailable**: اگر هیچ strong model در chain موجود نیست، iteration 3 با fallback model اجرا می‌شود (با warning log) — fail نمی‌کند.
13. **🆕 (v2) Trace size**: cap ۱۰۰۰ entry per verify_run. اگر بیشتر، oldest حذف می‌شوند (FIFO).
14. **🆕 (v2) Config validation**: اگر user verify_v6_config با مقادیر out-of-range تنظیم کرد (مثلاً max_iterations=100)، clamp به range معتبر.

---

## 🚫 خارج از scope (بدون تغییر)

(همان قبلی)
- تغییر در Playwright probe
- تغییر در vision probe
- ML classification
- multi-language تشخیص source code (فقط py/ts/tsx/js/jsx)
- AST-level analysis
- distributed cache
- WebSocket live progress

---

## 🔬 ترتیب اجرا (v2 — با ۸ chunk)

1. **Chunk 1**: `context_builder.py` — `VerifyConfig`, `VerifyContext`, `build_verify_context`. unit test.
2. **Chunk 2**: `code_content_searcher.py` — ۴ تابع + ۴ مثال در docstring + `extract_identifiers` با stop-words. unit test.
3. **Chunk 3**: `iterative_orchestrator.py` — `ProbeResult`, `aggregate_verdicts`, `iterative_verify_step`, `_strong_model_judgment`. unit test برای aggregate.
4. **Chunk 4**: `ac_cache_service.py` — cache logic + integration در `OversightTask.ac_verify_cache`.
5. **Chunk 5**: `code_aware_verifier.py` — ۴ phase صریح + integration با content_grep.
6. **Chunk 6**: `oversight_verifier.py` — `_classify_step_for_probe` rewrite + integration با orchestrator + flag `verify_v6`.
7. **Chunk 7**: `VerificationReport.verify_trace/ac_probe_details/verify_version` + endpoint های جدید + UI accordion.
8. **Chunk 8**: meta-test — اجرای verify v6 روی این bug. اطمینان از ≥۱۱/۱۲ AC.

هر chunk: commit جدا، type-check، push.

---

## ✅ جدول نهایی ادعا

| تفاوت من با verify | راه‌حل در v6 v2 | کاستی برطرف شد؟ |
|---|---|---|
| من full file می‌خوانم | `code_content_searcher.fetch_file_content` | ✅ |
| من targeted grep می‌زنم | `smart_grep_for_ac` با ۴ مثال concrete | ✅ |
| من iterative هستم | `iterative_verify_step` با ۳ iteration | ✅ |
| من می‌دانم vision کجا کار نمی‌کند | `_classify_step_for_probe` با ۱۰ قاعده | ✅ |
| من چندین منبع را cross-check می‌کنم | `aggregate_verdicts` weighted | ✅ |
| من حافظهٔ کامل دارم | `VerifyContext` با همهٔ history | ✅ |
| **(v2)** من از کار قبلی حافظه دارم | `ac_verify_cache` با consecutive_done_count | ✅ |
| **(v2)** من می‌توانم توضیح بدم چرا | `verify_trace` + endpoint debug | ✅ |
| **(v2)** من از مدل قوی استفاده می‌کنم | `_strong_model_judgment` در iter 3 صریح | ✅ |
| **(v2)** من tunable هستم | `VerifyConfig` centralized | ✅ |

-------------------------------

پنج باگ زیربنایی:

باگ ۱: verifier همهٔ تسک‌ها را با همان probe set برخورد می‌کند. backend changes (مثل افزودن task_id به SmartChatRequest) در ui_interaction(/oversight) دیده نمی‌شوند، پس probe fail می‌شود ولی feature موجود است.

باگ ۲: probes با path parameters (مثل /load-task/{task_id}) بدون مقدار parameter صدا زده می‌شوند → HTTP 405 → probe «feature missing» تشخیص می‌دهد در حالی که فقط URL نامعتبر است.

باگ ۳: AI verifier متن done_parts و remaining_parts را به‌صورت موازی تولید می‌کند بدون چک تناقض. اگر تستی متناقض است، باید resolve شود.

باگ ۴: probe ها به مدل vision نمی‌گویند «این feature backend است، دنبال متن قابل‌مشاهده نگرد». مدل visual را برای feature backend صدا می‌زند → hallucination ضد-feature.

باگ ۵: trace شفاف نیست. کاربر نمی‌فهمد چرا step X شکست خورد — آیا کد ساخته نشده، یا probe اشتباه تست کرده.

هدف نهایی Verify v7
verifier نوع تسک را خودکار تشخیص دهد (backend / frontend / fullstack / infra / docs / test)
probe ها متناسب با نوع تسک وزن داده شوند (ui_interaction روی تسک backend وزن ≈ 0)
probe ها با path parameters به‌درستی هندل شوند (synthesize parameter یا skip)
خروجی AI verifier تناقض done ↔ remaining نداشته باشد
prompt مدل vision حاوی نوع تسک باشد تا hallucination کاهش یابد
trace شفاف توضیح دهد چرا هر step done/partial/not_done شد
فاز A — Task Type Classifier
اصول
یک تابع helper جدید: _classify_task_type(task) که بر اساس prompt + target_files + AC، نوع تسک را تشخیص می‌دهد.

دسته‌بندی‌ها
Type	معیار تشخیص	probe profile
pure_backend	همهٔ target_files با .py پایان دارند یا path شامل backend/ و در prompt اشاره‌ای به frontend/UI نیست	weight ui_interaction = 0.1، api_probe = 2.0
pure_frontend	همهٔ target_files با .tsx/.ts/.jsx/.js/.css پایان دارند و path شامل frontend/	weight ui_interaction = 2.0، api_probe = 0.3
fullstack	ترکیبی از backend و frontend	weight ui_interaction = 1.5، api_probe = 1.5
infra	فایل‌های Dockerfile, *.yml, *.yaml, .github/workflows/*	weight ui_interaction = 0، code_aware = 3.0
docs_only	فقط .md, .txt	همهٔ probes را skip، فقط code_aware
test_only	فقط فایل‌های test_*.py, *.test.tsx	weight ui_interaction = 0.3، test_probe = 3.0
mixed_unknown	تشخیص ناممکن	استفاده از weights پیش‌فرض (همان WEIGHTS_BY_PROBE موجود)
اقدامات
محل: backend/app/services/verify_runtime/iterative_orchestrator.py کنار WEIGHTS_BY_PROBE
تابع _classify_task_type(task) -> str که یکی از این 7 رشته برمی‌گرداند
منطق تشخیص باید fast باشد (regex ساده، نه AI call)
در trace ثبت شود: task_type_classified: pure_backend
معیارهای پذیرش فاز A
۱. تابع _classify_task_type در iterative_orchestrator.py موجود است
۲. تابع برای هر یک از ۷ نوع، رشتهٔ صحیح برمی‌گرداند (با تست واحد)
۳. task_type در verify_trace با phase=classify_task_type ثبت می‌شود
۴. تشخیص بدون فراخوانی AI انجام می‌شود (regex/heuristic)

فاز B — Task-Type-Aware Probe Weighting
اصول
WEIGHTS_BY_PROBE فعلاً ثابت است. باید بر اساس task_type پویا شود.

اقدامات
یک dict جدید: WEIGHTS_BY_TASK_TYPE: Dict[str, Dict[str, float]] که برای هر task_type، override weights را نگه می‌دارد
تابع _get_weights_for_task(task) -> Dict[str, float]:
task_type = _classify_task_type(task)
اگر task_type در WEIGHTS_BY_TASK_TYPE: weights مخصوص آن را برگردان
در غیر این صورت: WEIGHTS_BY_PROBE پیش‌فرض
در aggregate_verdicts، به‌جای استفاده از WEIGHTS_BY_PROBE ثابت، از _get_weights_for_task(task) استفاده شود
در trace ثبت شود: weights_used: {ui_interaction: 0.1, api_probe: 2.0, ...} و task_type: pure_backend
مقادیر weights برای هر task_type
WEIGHTS_BY_TASK_TYPE = {
    "pure_backend": {
        "ui_interaction": 0.1,      # تقریباً نادیده — backend در UI دیده نمی‌شود
        "api_probe": 2.0,           # مهم — تست واقعی endpoint
        "code_aware_basename": 2.5, # خیلی مهم — تأیید static که فایل/تابع موجود است
        "content_grep_strong": 3.0,
        "content_grep_weak": 1.5,
        "playwright": 0.1,          # تقریباً نادیده
        "ai_verifier": 1.0,
        "vision_frontend": 0.0,     # وزن صفر — visual بی‌معنی برای backend
        "vision_backend": 0.5,
        "strong_model": 2.5,
        "test_probe": 1.5,
    },
    "pure_frontend": {
        "ui_interaction": 2.0,      # مهم — UI واقعی تست شود
        "api_probe": 0.3,
        "code_aware_basename": 1.5,
        "content_grep_strong": 2.5,
        "content_grep_weak": 1.5,
        "playwright": 2.5,          # مهم — interaction واقعی
        "ai_verifier": 1.0,
        "vision_frontend": 1.5,
        "vision_backend": 0.0,
        "strong_model": 2.5,
        "test_probe": 1.0,
    },
    "fullstack": {
        # نسخهٔ متوازن — هیچ probe ای weight 0 ندارد
        ...
    },
    "infra": {
        "ui_interaction": 0.0,
        "api_probe": 0.5,
        "code_aware_basename": 3.0,
        "content_grep_strong": 3.0,
        "playwright": 0.0,
        "vision_frontend": 0.0,
        "vision_backend": 0.0,
        ...
    },
    "docs_only": {
        # همه چیز کم — فقط code_aware
        "ui_interaction": 0.0,
        "api_probe": 0.0,
        "code_aware_basename": 3.0,
        "content_grep_strong": 3.0,
        ...
    },
    "test_only": {
        "test_probe": 3.0,
        "ui_interaction": 0.3,
        ...
    },
}
معیارهای پذیرش فاز B
۵. dict WEIGHTS_BY_TASK_TYPE با حداقل ۷ نوع تسک تعریف شده است
۶. تابع _get_weights_for_task(task) تعریف شده و weights صحیح برمی‌گرداند
۷. aggregate_verdicts از weights پویا استفاده می‌کند نه ثابت
۸. trace شامل task_type و weights_used در phase aggregation است
۹. backward compat: اگر task ندارد یا تشخیص ناممکن، behavior پیش‌فرض حفظ می‌شود

فاز C — Probe URL Validation
اصول
probes با path parameters (مثل /load-task/{task_id}) باید:

یا {param} را با مقدار واقعی پر کنند (مثلاً task_id خود تسک)
یا probe را به‌عنوان skipped (نه failed) علامت بزنند
و در trace توضیح بدهند چرا
اقدامات
در run_probes_for_acs (یا تابع متناظر در verify_runtime/runner.py):
قبل از زدن probe، URL را برای path parameters parse کن
regex: \{(\w+)\}
اگر parameter پیدا شد:
اگر نام parameter task_id بود → از task.id فعلی استفاده کن
اگر project_id بود → از watched.project_id یا اطلاعات context استفاده کن
اگر هیچ کدام match نشد → probe را skip کن با reason: unfilled_path_param:{param_name}
در صورت 405/404 از probe، به جای failed آن را به skipped با reason: route_not_matched تبدیل کن (probe مسئله است نه feature)
در trace ثبت شود: probe_url_filled: /load-task/abc123 یا probe_skipped_reason: unfilled_path_param
معیارهای پذیرش فاز C
۱۰. probes با {task_id} خودکار با task.id فعلی پر می‌شوند
۱۱. probes با {project_id} با watched.project_id پر می‌شوند
۱۲. probes با path parameter که قابل پر کردن نیست، با skipped و reason ثبت می‌شوند
۱۳. اگر HTTP 405 برگشت، probe skipped می‌شود نه failed
۱۴. اگر HTTP 404 برگشت روی URL با path param، probe skipped می‌شود

فاز D — Contradiction Resolution در خروجی AI verifier
مشکل
AI verifier در یک پاس JSON تولید می‌کند که done_parts و remaining_parts هر دو شامل همان AC ها هستند. این منطقی نیست.

اقدامات
پس از parse خروجی AI در oversight_verifier.py نزدیک خط ۳۳۴۵:
برای هر آیتم در remaining_parts، بررسی کن آیا متن مشابهی (Jaccard ≥0.7 یا substring) در done_parts موجود است
اگر موجود است: تناقض است — یک resolver فراخوانی شود
منطق resolver:
اگر code-aware برای آن step implemented گفته → آن را از remaining حذف کن (done برنده می‌شود)
اگر code-aware چیزی نگفته و فقط runtime probe شکست خورده → بسته به probe type:
اگر probe ای که شکست خورد ui_interaction روی تسک pure_backend بود → نادیده (probe نامتناسب)
در غیر این صورت → در remaining بماند
در trace ثبت شود: contradiction_resolved: <step_text> با reason
معیارهای پذیرش فاز D
۱۵. تابع _resolve_done_remaining_contradiction(done_parts, remaining_parts, task) ساخته شده
۱۶. منطق Jaccard یا substring برای تشخیص تناقض پیاده شده
۱۷. اگر code-aware = implemented، item از remaining حذف می‌شود
۱۸. اگر probe نامتناسب، item نادیده گرفته می‌شود
۱۹. trace شامل لیست contradictions_resolved با reason است

فاز E — Backend-Feature Awareness در Prompt مدل Vision
مشکل
probes vision به مدل می‌گویند «به این صفحه نگاه کن و بگو آیا feature X موجود است». مدل vision دنبال متن قابل‌مشاهده می‌گردد. اما اگر feature X فقط در backend است (مثل افزودن task_id به SmartChatRequest)، مدل می‌گوید «feature ساخته نشده» — چون قابل‌مشاهده در page نیست.

اقدامات
در prompt مدل vision (در _run_ui_interaction_probe یا متناظر)، یک hint اضافه کن:
اگر task_type در (pure_backend, infra): به مدل بگو:
«این feature backend است و در UI قابل‌مشاهده نیست. صفحه فقط برای تأیید قابل‌دسترسی بودن سرویس است. به متن صفحه برای feature X نگاه نکن — این probe فقط health-check صفحه است، نه feature verification. verdict مناسب: pass اگر صفحه load شد.»

این می‌تواند با یک system prompt prefix یا یک خط در user message انجام شود
در trace ثبت شود: vision_prompt_hint_added: backend_task
معیارهای پذیرش فاز E
۲۰. prompt مدل vision برای task_type backend/infra hint اضافه شده دارد
۲۱. مدل vision در این موارد به‌جای hallucination، verdict pass می‌دهد اگر صفحه load شد
۲۲. trace vision_prompt_hint_added با task_type ثبت می‌شود

فاز F — شفاف‌سازی Trace
اصول
trace باید برای هر step واضح بگوید چرا verdict آن done/partial/not_done شد.

اقدامات
در پایان iterative_verify_step، یک خلاصهٔ خواناتر در trace اضافه شود:
{
  "phase": "step_summary",
  "step_text": "فاز 0 — بازرسی کیفیت...",
  "final_verdict": "done",
  "task_type": "pure_backend",
  "weights_used": {...},
  "probes_contributed": [
    {"probe": "code_aware_basename", "verdict": "done", "weight_applied": 2.5},
    {"probe": "ui_interaction", "verdict": "failed", "weight_applied": 0.1, "note": "low weight — task is backend"}
  ],
  "decision_reason": "code-aware confirms implementation, runtime probes downweighted for backend task"
}
endpoint /api/oversight/tasks/{id}/verify-trace این خلاصه را برگرداند
در UI صفحهٔ verify report، یک accordion «چرا این verdict؟» اضافه شود که این summary را نمایش دهد
معیارهای پذیرش فاز F
۲۳. trace شامل phase: step_summary با decision_reason برای هر step است
۲۴. probes_contributed شامل weight_applied و note است
۲۵. endpoint verify-trace خلاصه را قابل دسترس می‌کند
۲۶. UI accordion «چرا این verdict؟» در verify report موجود است

ملاحظات کلی
Backward compatibility: اگر _classify_task_type نتواند تشخیص دهد (mixed_unknown)، رفتار قبلی Verify v6 حفظ شود
No regression: همهٔ سناریوهای Verify v6 (که هم‌اکنون پاس می‌شوند) باید همچنان پاس شوند
هر فاز در commit جداگانه
معیارهای کلی پذیرش
۲۶ معیار بالا قابل grep در source code
سناریوی تست end-to-end: یک تسک backend-heavy (مثل خود C7) را verify کنید با verify_v7=True. باید:
چک‌لیست: 7/7
done_parts: ۷ فاز
remaining_parts: خالی (نه ۸ مورد متناقض)
verdict نهایی: done با confidence ≥ 0.85
trace شامل task_type=pure_backend
probes با weight 0.1 برای ui_interaction نشان داده شوند
سناریوی frontend: یک تسک frontend-heavy verify شود → weights برعکس
سناریوی docs: یک تسک فقط .md → فقط code_aware اجرا شود، سایر probes skip
سناریوهای meta-test
_classify_task_type برای تسک با همهٔ target_files .py → pure_backend
_classify_task_type برای تسک با همهٔ target_files .tsx → pure_frontend
_classify_task_type برای تسک mixed → fullstack
_get_weights_for_task برای pure_backend → ui_interaction weight = 0.1
probe /load-task/{task_id} خودکار با task.id واقعی پر می‌شود
probe بدون پر شدن param → skipped (نه failed)
HTTP 405 → skipped (نه failed)
AC در هر دو done و remaining → resolver حذفش می‌کند
vision prompt برای backend task شامل hint است
trace step_summary با decision_reason در پایان موجود است

## Prompt

## ⚠️ یادداشت مهم برای مدل اجراکننده — قبل از شروع بخوان

این پرامپت بر اساس یک **بررسی اولیهٔ خودکار** از repo ساخته شده — ممکن است
حاوی اشتباه، تشخیص نادرست، یا حذف موارد مهم باشد. به‌عنوان منبع نهایی به
آن استناد نکن.

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

📦 **اگر کار طولانی است:**
- **خلاصه‌اش نکن.** همه را به‌طور کامل انجام بده.
- اگر یک کامیت گنجایش ندارد، در **چندین کامیت متوالی** انجام بده — ولی
  هیچ بخشی را skip نکن.
- ترتیب کامیت‌ها را منطقی نگه‌دار (foundation → core → integration → tests).
- در آخر یک checklist از همه‌ی کامیت‌ها در PR description بنویس.

---


---

## 📥 درخواست خام کاربر (verbatim — همان متنی که کاربر نوشت)
_(همهٔ URL ها، آدرس‌ها، نام‌ها، و کلمات کلیدی در این متن دست‌نخورده هستند.)_

```
ایدهٔ خام
# 🔬 Runtime Verify Layer — verify مبتنی بر شواهد runtime (نه فقط grep کد)
## 🎯 هدف اصلی (یک جمله)
verify فعلی فقط کد را می‌خواند و حدس می‌زند؛ این layer جدید برای هر AC که
ماهیتش رفتاری است، **یک probe واقعی** اجرا می‌کند (Playwright برای UI،
HTTP برای API، pytest برای backend logic) و **شواهد runtime** (screenshot،
response JSON، pytest output) به verify می‌دهد. در نتیجه verify دیگر
false-positive («نشده» در حالی که شده) و false-negative («شده» در حالی که
نشده) نمی‌دهد.
---
## 📌 موقعیت دقیق در پروژه (فایل‌های مرتبط — مجری باید deep-read کند)
- `backend/app/services/oversight_verifier.py` — verify فعلی (grep + AI)
  → نقطهٔ یکپارچه‌سازی Stage 5
- `backend/app/services/oversight_strong_prompt.py` — تولید AC
  → نقطهٔ Stage 2 (AI verify_plan)
- `backend/app/services/oversight_service.py` — OversightTask + create_task
  → Stage 1 (schema migration)
- `backend/app/services/oversight_verify_pdf.py` — PDF فعلی
  → Stage 7 (embed evidence)
- `frontend/src/app/oversight/page.tsx` — UI تسک
  → Stage 8 (نمایش evidence)
- `frontend/src/app/projects/[id]/page.tsx` یا settings — تنظیمات watched
  → Stage 4 (base URLs)
- پوشهٔ جدید: `backend/app/services/verify_runtime/` — probe runners
- پوشهٔ جدید: `storage/verify_evidence/` — ذخیرهٔ screenshots/JSONs
---
## 🧠 معماری کلی (قبل از کد، این را بفهم)
### concept جدید: «verify_method» برای هر AC
هر AC الان فقط یک رشته است:
"وقتی روی دکمه X کلیک می‌کنم، مدال باز شود"

بعد از این feature، هر AC یک struct است:
```json
{
  "text": "وقتی روی دکمه X کلیک می‌کنم، مدال باز شود",
  "verify_method": "ui_interaction",
  "verify_plan": {
    "ui_steps": [
      {"action": "navigate", "url": "/oversight"},
      {"action": "wait_for_load_state", "state": "networkidle"},
      {"action": "click", "selector": "[data-testid='btn-x']"},
      {"action": "wait_for_selector", "selector": "[role='dialog']", "timeout_ms": 3000},
      {"action": "assert_visible", "selector": "[role='dialog']"}
    ]
  }
}
پنج نوع verify_method
static — کد grep (همان verify فعلی) — برای ACی مثل «فایل X وجود دارد»
ui_interaction — Playwright headless — برای ACی مثل «دکمه باز می‌شود»
api_response — HTTP request — برای ACی مثل «endpoint Y → 200 با field Z»
backend_test — pytest subprocess — برای ACی مثل «تست T pass شود»
manual_only — نمی‌توان خودکار تأیید کرد — verify فقط می‌گوید «نیاز به بازبینی دستی»
چه چیزی جایگزین شواهد grep می‌شود
verify فعلی به AI می‌گفت: «این کد را ببین، AC پاس می‌شود؟»
verify جدید می‌گوید: «این runtime evidence را ببین (screenshot، JSON، pytest log) — AC پاس می‌شود؟»

🪜 مراحل اجرایی (دقیقاً به این ترتیب — قبلی پیش‌نیاز بعدی است)
Stage 1 — Schema migration برای AC ساختاریافته
فایل‌ها: oversight_service.py, oversight_strong_prompt.py,
oversight_verifier.py, frontend/.../page.tsx

کاری که می‌شود:

OversightTask.acceptance_criteria از List[str] به List[Union[str, Dict]] تبدیل
helper _normalize_ac(ac) -> Dict[str, Any] که هم str هم dict را به
ساختار {text, verify_method, verify_plan, evidence_history} تبدیل می‌کند
backward compat: اگر AC قدیمی str است، verify_method="static" پیش‌فرض
در task_steps، هر step هم باید verify_method و verify_plan داشته باشد
migration یک‌بار در startup: روی همهٔ task های موجود _normalize_ac اجرا
شود (loop در _load_tasks)
Tests:

یک task با AC string قدیمی → بعد از load به ساختار جدید تبدیل شود
یک task با AC dict جدید → بدون تغییر باقی بماند
Stage 2 — تولید verify_plan توسط AI
فایل‌ها: oversight_strong_prompt.py, oversight_service.py
(در _idea_to_prompt_multi_pass), oversight_service.py (در system prompt)

کاری که می‌شود:

system prompt در idea_to_prompt گسترش یابد: AI علاوه بر AC، برای هر AC
باید verify_method و در صورت نیاز verify_plan تولید کند
چارچوب تصمیم برای AI:
AC شامل «کلیک، نمایش، صفحه، مودال، input» → ui_interaction
AC شامل «endpoint، API، status code، response» → api_response
AC شامل «test، pytest، unit test» → backend_test
AC شامل «فایل X وجود دارد، imported است» → static
AC مبهم یا ذهنی (مثل «ظاهر زیبا») → manual_only
prompt یک نمونهٔ کامل JSON برای هر نوع به AI می‌دهد (few-shot)
اگر AI نتوانست plan بدهد → fallback به static
Tests:

یک ایدهٔ UI («دکمه login کار کند») → AC با ui_interaction + ui_steps
یک ایدهٔ API («endpoint /users 200 بدهد») → AC با api_response
یک ایدهٔ ذهنی («طراحی شیک‌تر») → AC با manual_only
Stage 3 — Probe runners (هستهٔ کار)
پوشهٔ جدید: backend/app/services/verify_runtime/

فایل‌ها:

__init__.py
base.py — dataclass RuntimeProbeResult:
@dataclass
class RuntimeProbeResult:
    ac_id: str
    method: str  # static|ui|api|test|manual
    status: str  # passed|failed|error|skipped
    evidence: Dict[str, Any]  # {screenshot_paths, response_json, stdout, ...}
    duration_ms: int
    error_message: Optional[str]
    timestamp: str
static_probe.py — wrapper روی grep فعلی (همان منطق oversight_verifier)
ui_probe.py — استفاده از playwright.async_api:
async_playwright() → browser
برای هر step در ui_steps action متناظر را اجرا کن
screenshot قبل و بعد از هر action مهم (نام: <ac_id>_<step_idx>.png)
timeout per action: 10s پیش‌فرض
browser pool: max 3 concurrent
api_probe.py — استفاده از httpx.AsyncClient:
request اجرا
assert status_code (از plan)
assert response JSON schema (از plan: required fields)
response را به‌عنوان evidence ذخیره
test_probe.py — استفاده از subprocess:
pytest <test_path> --json-report --json-report-file=tmp.json
timeout: 120s
parse JSON output، success_count و failures
manual_probe.py — همیشه status="skipped" با پیام «نیاز به بازبینی دستی»
ابزارهای جدید nice-to-have:

runner.py — تابع run_probes_for_task(task, watched) -> List[RuntimeProbeResult]
برای هر AC method را تشخیص دهد
probe مناسب را call کند
با asyncio.Semaphore(3) همزمانی را محدود کند
timeout کلی task: 5 دقیقه
Tests:

mock playwright برای test UI probe (یا یک HTML ساده local serve)
httpbin برای test API probe
یک test pytest dummy برای test_probe
Stage 4 — Base URLs و config
فایل‌ها: oversight_service.py (WatchedProject),
frontend/src/app/projects/[id]/page.tsx یا settings UI

کاری که می‌شود:

اضافه کردن فیلدها به WatchedProject:
frontend_base_url: Optional[str] — مثلاً https://ai-creator-frontend.onrender.com
backend_base_url: Optional[str] — مثلاً https://ai-creator-backend.onrender.com
runtime_auth: Optional[Dict] — {type: "cookie"|"bearer", value: str}
در UI: یک section در تنظیمات پروژه:
input URL فرانت
input URL بک‌اند
dropdown نوع احراز هویت + input مقدار
دکمه «تست اتصال» (یک ping به فرانت + یک GET به backend health)
اگر URL تنظیم نشده → probe های ui/api همگی status="skipped" با
پیام «base URL تنظیم نشده»
Tests:

تست اتصال موفق + ناموفق
ذخیره و بارگذاری config
Stage 5 — یکپارچه‌سازی با verify_task
فایل: oversight_verifier.py

کاری که می‌شود:

در ابتدای verify_task (یا قبل از فراخوانی AI):
runtime_results = await run_probes_for_task(task, watched)
(با asyncio.wait_for timeout کلی)
هر probe که شکست خورد → log + continue (verify ادامه دهد)
results را به یک متن خوانا تبدیل کن:
## شواهد Runtime
### AC1: «وقتی روی دکمه X کلیک می‌کنم، مدال باز شود»
- method: ui_interaction
- status: ✅ passed
- evidence: screenshots/<task_id>/<run_id>/ac1_step3.png
- duration: 850ms
- مشاهدات: مدال [role=dialog] در 240ms ظاهر شد
### AC2: «GET /api/users → 200 با field email»
- method: api_response  
- status: ❌ failed
- actual_status: 500
- error: "Internal Server Error"
این متن را به‌عنوان بخش جدید در prompt verify اضافه کن
system prompt به AI: «شواهد runtime بالاتر از تحلیل کد است. اگر
runtime می‌گوید failed، حتی اگر کد درست به نظر برسد، AC پاس نشده.»
پس از AI، اگر برای یک AC هم runtime ✅ و هم AI گفت done → done قطعی
اگر runtime ❌ ولی AI گفت done → AI override کن به not_done (با هشدار log)
اگر runtime ✅ ولی AI گفت not_done → AI override کن به done
Tests:

verify_task با task که همهٔ probe ها pass شدند → status=done
verify_task با probe failed → AI override
verify_task با probe error (timeout) → fallback به فقط AI
Stage 6 — ذخیره‌سازی evidence
فایل: verify_runtime/storage.py

کاری که می‌شود:

ساختار:
storage/verify_evidence/
  <task_id>/
    <run_id>/
      ac1_step1.png
      ac1_step2.png
      ac2_response.json
      ac3_pytest.json
      manifest.json   # links همهٔ evidence ها
cleanup policy: نگه‌داری فقط 5 run آخر هر task
endpoint جدید: GET /api/oversight/tasks/{id}/evidence/{run_id}/<path>
→ serve فایل (با authorization)
size limit: 50MB per run؛ اگر بیشتر شد، screenshots را به JPEG q=70 کم کن
Stage 7 — PDF و Telegram (embed evidence)
فایل‌ها: oversight_verify_pdf.py, notification_service.py

کاری که می‌شود:

در PDF، یک section جدید «📷 شواهد Runtime»:
برای هر AC، یک card با:
متن AC
method badge (UI / API / Test)
status badge
برای UI: تصویر screenshot inline
برای API: JSON پاسخ (truncated به 500 byte) در <pre>
برای Test: stdout pytest (truncated)
در پیام تلگرام: اگر هر probe failed بود، یک خلاصه:
❌ شواهد runtime:
  • AC1 ui_interaction: passed (240ms)
  • AC2 api_response: failed (status 500)
  • AC3 backend_test: passed (3 tests)
📎 جزئیات کامل در PDF پیوست
Stage 8 — Frontend UI (نمایش evidence)
فایل: frontend/src/app/oversight/page.tsx

کاری که می‌شود:

در مودال جزئیات تسک، section جدید «🔬 آخرین verify runtime»:
برای هر AC: row با method icon + status + دکمهٔ «مشاهدهٔ evidence»
کلیک روی دکمه → مودال modal دوم با:
برای UI: gallery screenshot ها (lightbox)
برای API: JSON formatted با syntax highlight
برای Test: terminal-style block با stdout
دکمهٔ جدید «🔬 Verify با Runtime» (متفاوت از verify عادی):
این یکی شامل probe ها است (کندتر)
verify عادی بدون probe می‌ماند برای سرعت
در تنظیمات پروژه: section «Runtime Verify» با URLها و auth
Stage 9 — Performance، safety، edge cases
کاری که می‌شود:

Playwright browser process را در lifespan FastAPI start کن (شاره شده)
→ بعد از 5 دقیقه idle، آن را kill کن
per-task timeout کلی: 5 دقیقه
per-probe timeout: ui=30s, api=10s, test=120s
Semaphore: حداکثر 3 probe موازی برای یک task
اگر runtime در محیط Render (production) فعال نیست (مثلاً playwright
install نشده) → graceful degrade به فقط static (با warning)
circuit breaker: اگر 3 task پشت‌سرهم probe error دادند، runtime را
برای 10 دقیقه disable کن
environment flag: RUNTIME_VERIFY_ENABLED=true|false در .env
Stage 10 — Tests و validation
کاری که می‌شود:

unit tests:
test_static_probe.py — grep درست
test_ui_probe.py — با یک HTML server محلی
test_api_probe.py — با httpbin
test_test_probe.py — با pytest dummy
test_runner.py — orchestration
test_runtime_integration.py — verify_task با probe ها end-to-end
یک «known-good» fixture: task ساده که همه‌چیز pass می‌شود
یک «known-bad» fixture: task که هر probe باید fail شود
✅ معیارهای پذیرش کلی
عملکردی
not done
AC با verify_method=static همان رفتار قبلی verify را دارد (no regression)
not done
AC با verify_method=ui_interaction: playwright headless browser باز
می‌کند، steps را اجرا می‌کند، screenshot می‌گیرد، نتیجه برمی‌گرداند
not done
AC با verify_method=api_response: HTTP request می‌رود، status + شِما
چک می‌شود
not done
AC با verify_method=backend_test: pytest در subprocess با timeout
اجرا می‌شود
not done
AC با verify_method=manual_only: skipped با پیام واضح
not done
هر probe که error داد، verify ادامه می‌دهد (نه crash)
not done
base URL ها قابل تنظیم per project
not done
evidence فایل‌ها روی disk ذخیره می‌شوند، با cleanup policy
not done
PDF و Telegram message شواهد را embed می‌کنند
not done
Frontend modal جدید برای drill-down evidence
کیفی
not done
type-check (mypy + tsc) بدون error
not done
هیچ test موجود fail نمی‌شود
not done
محیط production (Render) با RUNTIME_VERIFY_ENABLED=false کاملاً
مثل قبل کار می‌کند (graceful disable)
not done
هیچ probe که فقط برای یک AC شکست خورد، کل verify را crash نکند
کنترل کیفیت verify
not done
روی یک تسک "known-good" (همه AC ها واقعاً پاس شده‌اند) →
verify=done
not done
روی یک تسک "known-bad" (UI AC شکست خورده) → AI نمی‌تواند آن را
done اعلام کند (runtime override)
not done
روی یک تسک با کد درست ولی deploy نشده → runtime می‌گوید fail
(چون probe می‌رود به URL واقعی، نه به کد محلی)
⚠️ ریسک‌ها و موارد احتیاط
Playwright چاق است (~300MB browser binaries). در Render production
ممکن است image size محدود باشد. → یک flag برای enable/disable در
.env، در production فعلاً فقط static + API + test (نه UI)
محیط Render سرور headless است — Playwright headless باید کار کند
ولی X server نمی‌خواهد. تست در staging قبل از production.
Authentication: اگر فرانت login می‌خواهد، probe باید login session
داشته باشد. در config، cookie یا bearer token ذخیره می‌شود (encrypted).
timing race: UI probe ممکن است قبل از hydrate Next.js کلیک کند.
باید wait_for_load_state('networkidle') در هر navigate.
pytest در subprocess — اگر تست اصلی پروژه طولانی است (>2 دقیقه)،
نباید کل verify را block کند. → فقط تست‌های مارک‌شده با
@pytest.mark.verify اجرا شوند، نه کل suite.
evidence disk usage — cleanup policy جدی، وگرنه ظرف چند روز
gigabyteها screenshot جمع می‌شود.
AI override conflict — اگر runtime ✅ و کد بد است (مثلاً deploy
نشده، کد staging تست شده)، AI نباید gaslight شود. → policy روشن:
«اگر runtime ✅ → AC done مگر AI شواهد بسیار قوی برعکس داشته باشد»
🧪 دستورات اعتبارسنجی (Validation Commands)
# backend lint + type
cd backend && python -m ruff check . && python -m mypy app/services/verify_runtime/

# backend unit tests
cd backend && pytest app/services/verify_runtime/ -v

# integration test
cd backend && pytest tests/integration/test_runtime_verify.py -v

# frontend
cd frontend && npx tsc --noEmit && npm run build

# manual smoke (روی production staging):
#   1. یک تسک بساز با AC «GET /api/oversight/status → 200»
#   2. روی frontend «🔬 Verify با Runtime» را بزن
#   3. PDF دریافتی باید JSON پاسخ /status را در evidence نشان بدهد
📦 ترتیب کامیت‌ها (foundation → core → integration → tests)
feat(verify): schema migration برای AC ساختاریافته (Stage 1)
feat(verify): تولید verify_plan توسط AI در idea_to_prompt (Stage 2)
feat(verify): پایهٔ probe runners (static + base.py) (Stage 3a)
feat(verify): UI probe با Playwright (Stage 3b)
feat(verify): API probe + Test probe (Stage 3c, 3d)
feat(verify): runner + semaphore + timeouts (Stage 3e)
feat(verify): base URLs و auth در WatchedProject (Stage 4)
feat(verify): ادغام probe ها در verify_task (Stage 5)
feat(verify): evidence storage + cleanup (Stage 6)
feat(verify): embed evidence در PDF + Telegram (Stage 7)
feat(verify): UI evidence viewer در frontend (Stage 8)
feat(verify): browser pool، circuit breaker، env flag (Stage 9)
test(verify): unit + integration tests (Stage 10)
هر کامیت باید روی master سبز باشد. اگر یک stage حجمی است، آن را به دو
کامیت بشکن — هیچ stage نباید بیش از یک هفته کار باشد.

🚫 آنچه خارج از scope این feature است
بازنویسی verifier فعلی (فقط extension است)
visual regression testing (screenshot diff) — می‌توان در feature بعدی
load testing — این یک stress test نیست
security scanning (SAST/DAST) — feature جداگانه
mobile UI testing — فقط desktop browser
multi-environment matrix testing — فقط یک base URL در آنِ واحد
-------------------------------------------------
# 🎯 پرامپت Phase 1 — اتصال Inspector Probe به verify جدید + ضمیمه‌ی تلگرامی
## هدف
ساخت یک probe جدید به اسم inspector_probe که به‌صورت خودکار (بدون
مداخله کاربر) صفحه دیپلوی‌شده پروژه را با Playwright سرور-سایدی باز
می‌کند، navigate / click می‌کند، screenshot می‌گیرد، console و backend
logs را جمع می‌کند، با Vision AI screenshot ها را تحلیل می‌کند و
نتیجه را به‌عنوان probe evidence در گزارش verify بازمی‌گرداند.
همزمان، تمام مراحل را در یک inspector_session جدید با عنوان
«🤖 auto-verify · …» ذخیره می‌کند تا کاربر بتواند از تب بازرس ویژه
آن را مرور کند. پس از تمام شدن verify و تولید followup prompt، یک
بسته‌ی کامل به تلگرام ارسال می‌شود (گزارش متنی + screenshot ها +
پرامپت بروز) و **پس از موفقیت ارسال، screenshot ها از دیسک حذف
می‌شوند** تا حافظه‌ی سرور همیشه کم بماند.
## این برای چه کاری استفاده می‌شود
الان وقتی verify کامل زده می‌شود، runtime probes موجود اکثراً skip/error
می‌شوند چون نیاز به runtime_repo_path دارند. هدف inspector_probe:
- شواهد بصری واقعی از صفحه deployed جمع کند
- console errors و backend logs همزمان را ضبط کند
- Vision AI متن/المنت‌های UI/error overlay را از screenshot استخراج کند
- این شواهد را به AI verifier بدهد تا تصمیم بهتر بگیرد
- خروجی قابل مرور توسط انسان از تب بازرس ویژه ارائه دهد
- screenshot ها را در تلگرام به‌عنوان مدرک ماندگار آرشیو کند
- حافظه‌ی سرور را پاک نگه دارد (پاک کردن خودکار پس از تلگرام)
## محدودیت‌های Phase 1
✅ navigate به URL
✅ click روی selector
✅ screenshot (ذخیره روی دیسک، نه base64 در DB)
✅ Vision AI تحلیل screenshot (با fallback chain)
✅ console log capture
✅ backend log correlation
✅ ضمیمه‌ی تلگرامی + cleanup
✅ TTL cleanup خودکار برای orphan screenshots
❌ fill / submit / wait → Phase 2
❌ login / auth → Phase 3
❌ multi-step complex sequences → Phase 2
---
## معماری ذخیره‌سازی screenshot
**روی دیسک، نه DB:**
- مسیر:
  storage/oversight/runtime_evidence/{task_id}/{run_id}/{ac_id}/{label}.png
- مثلاً:
  storage/oversight/runtime_evidence/task_abc/run_xyz/ac01_h/after_navigate.png
**در DB (inspector_message.extra_data) فقط:**
- path نسبی به فایل
- label
- vision_description (متن استخراج‌شده — این مهم‌ترین artifact است)
- timestamp
**در evidence گزارش verify:**
- لیست screenshots با path + vision_description
- بعد از ارسال تلگرام، path nullable می‌شود ولی vision_description می‌ماند
---
## Vision Fallback Chain (مهم)
برای هر screenshot، به این ترتیب تلاش کن:
**1. Vision موجود در سیستم (همان منطق تب بازرسی):**
- describe_screenshot_with_vision() در
  backend/app/services/oversight_inspector_bridge.py:44
- این تابع از مدل‌های multimodal (OpenAI GPT-4V / Anthropic Claude
  Vision / Gemini Pro Vision) استفاده می‌کند بسته به اینکه کدام
  API key موجود است
- خروجی: {scene, ocr_text, ui_elements, error_signals, layout_hints}
**2. اگر مرحله 1 خطا داد یا API key نبود → fallback به verify model:**
- مدل verify (مثل deepseek-chat) text-only است؛ نمی‌تواند تصویر را ببیند
- ولی می‌تواند روی **متن استخراج‌شده موجود** کار کند:
  - HTML content صفحه (از iframe contentDocument)
  - console logs
  - backend logs
  - URL
- یک پرامپت ساده: «بر اساس این لاگ‌ها و HTML، چه چیزی روی صفحه دیده می‌شد؟»
- این خروجی هم در vision_description ذخیره می‌شود (با علامتگذاری
  source="fallback_text_only")
**3. اگر هر دو شکست خوردند → فقط screenshot path ذخیره می‌شود:**
- vision_description = None
- probe بدون این فیلد ادامه می‌دهد (graceful degrade)
این منطق fallback را در یک تابع helper مستقل ذخیره کن (مثلاً
backend/app/services/verify_runtime/vision_helper.py) تا قابل reuse باشد.
---
## فایل‌ها و نقاط ادغام
### Backend — فایل‌های جدید
- backend/app/services/verify_runtime/inspector_probe.py
- backend/app/services/verify_runtime/vision_helper.py
  (شامل fallback chain)
### Backend — تغییرات
- backend/app/services/verify_runtime/base.py:
  افزودن فیلد inspector_session_id: Optional[int] = None به ProbeContext
- backend/app/services/verify_runtime/runner.py (خط 92-126):
  در _run_single_probe، برای method=ui_interaction:
  - اگر verify_plan.ui_steps لیستی با ≥3 step واقعی (نه فقط navigate
    + screenshot) دارد → run_ui_probe موجود
  - در غیر این صورت → run_inspector_probe جدید
  این dispatch داخل runner انجام می‌شود تا AI enricher نیازی به
  تغییر نداشته باشد.
- backend/app/services/oversight_verifier.py (خط 988-1063):
  در حین runtime probes block:
  1. قبل از run_probes_for_acs، یک InspectorSession موقت بساز:
     - title: «🤖 auto-verify · {task.title[:50]} · {timestamp}»
     - project_id: همان repo_full_name مشابه manual inspector
     - status: "active"
  2. session_id را در ProbeContext قرار بده
  3. probe ها اجرا می‌شوند
  4. پس از تمام شدن، session را archive کن
- backend/app/services/oversight_verifier.py (تابع
  _send_verify_notification_bg در حدود خط 1762):
  بسته‌ی تلگرامی توسعه پیدا کند:
  - علاوه بر متن گزارش که الان می‌فرستد
  - اگر runtime_probes شامل screenshots با path معتبر است:
    * تا حداکثر 5 screenshot را پیوست کن (با caption =
      vision_description یا probe ac_text)
    * استفاده از send_photo یا send_media_group بسته به تعداد
  - اگر followup_prompt تولید شده، فایل متنی .md از آن هم پیوست شود
    (یا در پیام اصلی به‌صورت inline)
  - پس از ارسال موفق (status_code 200 از تلگرام):
    * تمام screenshot path ها را روی دیسک حذف کن
    * در evidence، path ها را به None تبدیل کن (vision_description
      می‌ماند به‌عنوان نشانه‌ی دائمی)
    * یک پیام در inspector_session اضافه کن:
      «📦 evidence به تلگرام آرشیو شد و از دیسک پاک شد»
  - اگر تلگرام ناموفق بود:
    * screenshot ها را پاک نکن (برای retry آینده یا cleanup TTL)
    * log warning
- backend/app/services/oversight_verifier.py:
  افزودن یک تابع cleanup_orphan_screenshots():
  - هر screenshot قدیمی‌تر از 3 روز که هنوز روی دیسک است → حذف
  - این تابع می‌تواند در scheduler موجود (که از قبل scan دوره‌ای می‌کند)
    صدا زده شود
### Backend — Reuse زیرساخت موجود
- BrowserPool: backend/app/services/verify_runtime/browser_pool.py
- InspectorSession/Message: backend/app/models/inspector_session.py
- DB writes از async: استفاده از asyncio.to_thread برای wrap کردن
  SessionLocal sync operations
- Render Logs API: backend/app/services/log_stream_service.py یا
  endpoint های موجود در render_logs.py
- Vision moduel: oversight_inspector_bridge.py:44
- Storage path: STORAGE_DIR در oversight_service.py:60
### Frontend
- frontend/src/app/oversight/page.tsx (حدود خط 5946+):
  در بخش inline runtime probes، اگر یک probe دارای
  evidence.inspector_session_id است:
  - لینک کوچک «📺 مشاهده در بازرس ویژه →» نشان داده شود که به آدرس
    /projects/{watched.repo_full_name}?tab=inspector&session={id}
    می‌برد
  - اگر vision_description موجود است، یک خط کوتاه از آن inline
    نمایش داده شود (truncated به 100 char)
- frontend/src/app/projects/[id]/page.tsx (لیست sessions):
  session هایی که title آن‌ها با «🤖 auto-verify» شروع می‌شود:
  - آیکن 🤖 در ابتدای عنوان (در حال حاضر هم emoji در عنوان است،
    بنابراین خودکار درست نمایش می‌دهد، فقط چک کن که UI آن را break
    نکند)
  - رنگ background کمی متفاوت تا از session های دستی متمایز باشد
---
## ساختار داده probe
نتیجه‌ی run_inspector_probe RuntimeProbeResult با ساختار:
{
  ac_id, ac_text,
  method: "ui_interaction",
  status: "passed" | "failed" | "error" | "skipped",
  evidence: {
    inspector_session_id: int,
    actions_taken: [
      {action: "navigate", url: "/login", duration_ms: 1234},
      {action: "click", selector: "...", duration_ms: 200},
      {action: "screenshot", label: "after_navigate"},
    ],
    screenshots: [
      {
        path: "storage/oversight/runtime_evidence/.../after_navigate.png",
        label: "after_navigate",
        vision_description: "...",     # متن استخراج‌شده
        vision_source: "openai_vision" | "fallback_text_only" | null,
        archived_to_telegram: false,   # true پس از موفقیت تلگرام
      },
    ],
    console_errors: [
      {level, message, source, timestamp}
    ],
    backend_log_summary: "...",        # خلاصه برای AI verifier
    final_url: "...",
    assertion_results: [
      {expectation: "...", met: true/false, reason: "..."}
    ],
  },
  duration_ms: int,
  error_message: Optional[str]
}
---
## شرط passed / failed
**PASSED:**
- navigate موفق (response status < 400)
- هیچ console error سطح "error" در حین تست
- اگر plan.selector_hint موجود → selector روی صفحه پیدا شد
- vision_description (اگر موجود) متناقض با AC نیست
**FAILED:** یکی از موارد بالا نقض شود
**ERROR:** Playwright crash یا timeout > 60s
**SKIPPED:** frontend_base_url نیست، یا RUNTIME_VERIFY_UI_ENABLED=false،
یا circuit breaker باز
Vision description **advisory** است؛ به‌تنهایی pass/fail نمی‌کند. AI
verifier نهایی است که آن را در نظر می‌گیرد.
---
## محدودیت‌های ایمنی (must)
- timeout per-AC: 60 ثانیه
- max parallel inspector_probes: 1 (sequential)
- حداکثر 2 screenshot per probe (before + after click)
- screenshot file size: cap به 500KB با کیفیت متوسط
- اگر RUNTIME_VERIFY_UI_ENABLED=false → skip
- circuit breaker → skip
- session پس از تمام شدن probe ها archive شود (try/finally)
- screenshot ها فقط در صورت موفقیت تلگرام پاک شوند
- TTL: screenshot های قدیمی‌تر از 3 روز → حذف خودکار در scheduler
- هیچ data شخصی/cookie/auth در evidence لو نرود
- اگر سرور crash کرد، session ممکن است active بماند — یک recovery
  در startup که session های قدیمی auto-verify > 1h را archive کند
---
## Vision Helper API (تابع جدید)
backend/app/services/verify_runtime/vision_helper.py
async def analyze_screenshot(
    screenshot_path: str,
    context: Dict[str, Any],   # {url, console_logs, backend_logs, html_excerpt}
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns:
    {
      "description": str,        # متن آزاد توصیف صفحه
      "ui_elements": [...],      # opcional
      "error_signals": [...],    # opcional
      "source": str,             # "vision_<model>" یا "fallback_text_only" یا "none"
      "raw": dict | None,        # خروجی خام برای debug
    }
    """
    # 1. تلاش با vision models موجود (همان منطق تب بازرسی)
    # 2. در صورت شکست، fallback به verify_model با text-only context
    # 3. در صورت شکست هر دو، return با source="none"
---
## Telegram Bundle Logic
در _send_verify_notification_bg (یا توسعه‌ی آن):
1. متن گزارش معمول (الان وجود دارد): چک‌لیست done/remaining + status
2. **اضافه شود** — اگر runtime_probes شامل screenshots با path معتبر:
   - تا حداکثر 5 screenshot جمع‌آوری شود
   - استفاده از API تلگرام send_media_group (یا send_photo اگر تعداد=1)
   - caption هر media:
     "{ac_text[:50]}\n{vision_description[:200] if available}"
3. **اضافه شود** — اگر task.followup_prompt تولید شده:
   - به‌عنوان فایل .md پیوست شود
   - یا inline در پیام اصلی (اگر < 4000 char)
4. پس از send موفق (response.ok == True):
   - برای هر screenshot، os.remove(path)
   - در DB evidence، path را به None تبدیل کن (vision_description بماند)
   - تأیید در inspector_session بنویس
5. در صورت خطای تلگرام:
   - log error
   - screenshot ها را پاک نکن (TTL خودکار بعداً پاک می‌کند)
---
## TTL Cleanup
یک تابع جدید در oversight_verifier.py یا oversight_service.py:
def cleanup_orphan_runtime_screenshots(max_age_days: int = 3) -> Dict[str, int]:
    """screenshot های قدیمی روی دیسک که بیش از max_age_days از تولیدشان
    گذشته را حذف می‌کند.
    Returns: {deleted_count, deleted_bytes}
    """
این تابع در یکی از اتفاقات زیر صدا زده شود:
- در scheduler (oversight scan loop) — یک بار در روز
- یا در startup lifespan
- یا در یک endpoint جدید برای trigger دستی (اختیاری)
---
## شکست‌خوردگی‌های مجاز (graceful degrade)
- Playwright crash → probe error، verify ادامه می‌دهد
- Vision همه‌ی fallback ها fail → screenshot ذخیره می‌شود، توضیحی نه
- Render logs API نبود → backend_log_summary خالی
- inspector_session ساخته نشد → probe بدون session اجرا (لاگ کاربر در
  Inspector tab نخواهیم داشت)
- Telegram fail → screenshot ها روی دیسک می‌مانند، TTL پاک می‌کند
- اگر دیسک پر شد → cleanup قبل از screenshot جدید، یا skip + warning
---
## برانچ و دیپلوی
- ادامه روی همان branch claude/compare-verify-buttons-1ZyrX
- چند commit مستقل و مرتب:
  1. feat(verify-runtime): inspector_probe Phase 1 — core probe
  2. feat(verify-runtime): vision helper with fallback chain
  3. feat(verify-runtime): inspector_session integration
  4. feat(verify-runtime): telegram bundle + cleanup
  5. feat(verify-runtime): UI links and indicators
  6. test/docs (اختیاری)
- PR #601 به‌روزرسانی می‌شود (commit ها اضافه می‌شوند)
---
## ✅ Done definition
1. probe جدید برای AC هایی با method=ui_interaction (و بدون ui_steps
   مفصل) اجرا می‌شود
2. screenshot واقعی از صفحه deployed روی دیسک ذخیره می‌شود
3. Vision AI متن از screenshot استخراج می‌کند، با fallback به verify
   model اگر vision در دسترس نباشد
4. در گزارش verify (inline + modal) شواهد + vision description دیده
   می‌شود + لینک به بازرس ویژه
5. در تب بازرس ویژه، session «🤖 auto-verify · …» با پیام‌های قدم‌به‌قدم
   ظاهر می‌شود
6. پس از موفقیت verify، تلگرام بسته‌ی کامل (گزارش + screenshot ها +
   followup) را ارسال می‌کند
7. پس از ارسال موفق تلگرام، screenshot ها از دیسک پاک می‌شوند
8. TTL cleanup خودکار screenshot های orphan را پاک می‌کند
9. type-check + python ast بدون خطا
10. هیچ بخش موجود (verify سریع، بازرس ویژه دستی، AI verifier، backfill
    button، manual screenshot debug در tab بازرسی) کارایی‌اش از دست نمی‌دهد
---
## شروع کار
وقتی این پرامپت را فرستادی:
1. با TodoWrite قطعه‌بندی کن
2. ابتدا فایل‌های موجود را بخوان (ui_probe.py، oversight_inspector_bridge.py
   برای vision، _send_verify_notification_bg برای telegram)
3. هر تصمیم معماری بزرگ (مثلاً ساختار vision_helper یا نحوه‌ی pluging
   tagengkam تلگرام) را قبل از کد در پیام شرح بده
4. کد را قطعه‌قطعه commit و push کن (نه یکجا)
5. در پایان، خلاصه‌ای از فایل‌های تغییر یافته و نقاط تست را گزارش کن
----------------------
فاز دوم:
⚠️ **توجه:**
- بخش الف (Phase 2) قبلاً اجرا شده — فقط برای مرجع/حافظه است.
- **بخش ب (سه فیکس) باید الان اجرا شود** وقتی این پرامپت ارسال شد.
══════════════════════════════════════════════════════════════════════
# بخش الف — Phase 2 (مرور؛ قبلاً اجرا شد)
══════════════════════════════════════════════════════════════════════
## هدف Phase 2
A) **Per-step inspector_probe**: برای هر «مرحله» (task_step) از تسک، یک
   probe جداگانه با شواهد ایزوله: screenshot + vision + console logs +
   backend logs + ادرس فرانت ناوبری‌شده + ادرس‌های بک‌اند که در حین لود
   فراخوانی شدند (network requests).
B) **Auto prompt versioning + update + UI**:
   - پس از verify غیر-done، task.prompt قدیمی بایگانی شود در prompt_history،
     و task.prompt = followup_prompt تازه قرار گیرد.
   - UI پنل پرامپت کشوی «نسخه‌های قدیمی» داشته باشد.
   - دکمه «کپی پرامپت» = همیشه نسخه فعلی (که حالا جدید است).
   - endpoint برای revert نسخه قبلی.
C) **Comprehensive Telegram bundle (mega-bundle.html)**: یک فایل واحد
   شامل همه چیز: raw_idea + checklist + پرامپت قدیم/جدید + همه‌ی
   probe ها (هر کدام با screenshot/vision/console/backend logs/
   frontend URL/backend URLs) + assertion ها + AI verifier output.
## فایل‌ها (Phase 2 — مرور)
Backend:
- `backend/app/services/verify_runtime/inspector_probe.py`: network capture
- `backend/app/services/verify_runtime/runner.py`: dispatch
- `backend/app/services/verify_runtime/base.py`: ProbeContext extension
- `backend/app/services/oversight_verifier.py`: per-step probes +
  _infer_route_for_step + session lifecycle + _send_mega_bundle
- `backend/app/services/oversight_mega_bundle.py`: build_mega_bundle_md
- `backend/app/services/oversight_service.py`: prompt_history +
  apply_followup_as_new_prompt + revert_prompt_from_history
- `backend/app/services/notification_service.py`: send_photo +
  send_media_group_photos + send_extra_photos
- `backend/app/api/routes/oversight.py`: revert endpoint
Frontend:
- `frontend/src/app/oversight/page.tsx`: step probe styling + history modal
## ساختار داده per-step probe (مرور)
نتیجه‌ی هر step probe RuntimeProbeResult با:
{
  "ac_id": "step_3",
  "ac_text": "(step probe #3) ...",
  "method": "ui_interaction",
  "status": "passed",
  "evidence": {
    "inspector_session_id": int,
    "step_id": int, "step_title": str, "step_inferred_route": str,
    "actions_taken": [...],
    "screenshots": [{path, label, vision_description, vision_source}],
    "console_errors": [...],
    "network_calls": [...],
    "backend_urls_called": [{url, method, status}],
    "backend_log_summary": str,
    "final_url": str,
    "assertion_results": [...]
  }
}
## شرط passed/failed (مرور)
- PASSED: navigate ok AND no console error AND (selector_hint ok if specified)
- FAILED: یکی نقض شود
- ERROR: Playwright crash یا timeout > 60s
- SKIPPED: no frontend_base_url یا env disabled یا breaker open
══════════════════════════════════════════════════════════════════════
# بخش ب — سه فیکس جدید (الان اجرا شود)
══════════════════════════════════════════════════════════════════════
## مشکلات شناسایی‌شده پس از تست واقعی Phase 2
پس از تست روی یک تسک واقعی (DebateAttachment روی /debate):
1. **چک‌لیست بروز فقط در فایل پیوست هست، نه در متن پیام تلگرام.**
   کاربر می‌خواهد در نوتیفیکیشن تلگرام خلاصه‌ی چک‌لیست به‌روزشدهٔ
   مراحل تسک را در همان متن پیام ببیند (نه فقط در فایل ضمیمه).
2. **bundle.html روی موبایل (Android) قابل باز شدن راحت نیست.**
   تلگرام Android فایل html را دانلود می‌کند ولی کاربر باید دستی browser
   انتخاب کند. تجربهٔ کاربری ضعیف است. **PDF** انتخاب بهتری است چون روی
   موبایل با همان viewer داخلی Telegram باز می‌شود.
3. **vision prompt فقط صفحه را توصیف می‌کند، تشخیص feature نمی‌دهد.**
   نتیجه: حتی اگر feature ساخته نشده باشد، probe می‌گوید «passed» چون
   صفحه باز می‌شود و console error ندارد. vision باید صریحاً بپرسد
   «آیا feature مورد نظر AC در این صفحه دیده می‌شود یا نه؟» و این
   تشخیص باید روی pass/fail probe تأثیر بگذارد.
---
## فیکس ۱ — چک‌لیست به‌روز در متن پیام تلگرام
### هدف
در `_send_verify_notification_bg`، متن نوتیفیکیشن (مستقل از پیوست) باید
شامل خلاصهٔ chk‌لیست به‌روز task_steps باشد:
📋 چک‌لیست (X/N انجام‌شده):
[✅] مرحله ۱: عنوان (100%)
[~] مرحله ۲: عنوان (50%) — باقی‌مانده: «چی مونده»
[ ] مرحله ۳: عنوان (0%)
...

### فایل
`backend/app/services/oversight_verify_pdf.py` — تابع
`build_verify_checklist_message(task, report)` قبلاً وجود دارد. آن را
extend کن (یا تابع جدید بساز و در `_send_verify_notification_bg`
استفاده کن).
### الگوریتم
1. اگر `task.task_steps` خالی است → فقط چک‌لیست AC مثل قبل (بدون تغییر).
2. اگر task_steps دارد:
   - emoji per status: `done`→✅، `partial`→🟡، `not_done`/`pending`→⬜
   - فرمت هر خط (حداکثر ۱۲۰ char per line):
     `{emoji} مرحله {id}: {title[:70]} ({completion_pct}%)`
     اگر `partial` و `remaining` پر:
     `    └─ ⏳ {remaining[:80]}`
   - بالای لیست: `📋 چک‌لیست مراحل ({done_count}/{total} انجام‌شده)`
   - زیر لیست: یک خط `پیشرفت کلی: {avg_pct}%`
3. cap کل بلوک چک‌لیست به ~700 char (Telegram caption max ~1024 با
   مقداری حاشیه برای hashtag و buttons).
4. این بلوک را *قبل از* `streak` و `attachment` info در msg_text
   اضافه کن.
### رفتار شکست
- اگر task_steps malformed بود → silent fallback به نسخه‌ی فعلی.
- اگر بلوک از 700 char بیشتر شد → trim با `…` در آخرین مرحله.
---
## فیکس ۲ — تبدیل bundle از HTML به PDF
### هدف
mega-bundle که الان `.html` است را به `.pdf` تبدیل کن تا روی موبایل
بدون نیاز به browser در همان viewer تلگرام باز شود.
### استراتژی
کتابخانه‌ی PDF موجود در پروژه را شناسایی کن (verify_report PDF از
قبل با همان لایبرری ساخته می‌شود). تابع `build_verify_report_pdf` در
`oversight_verify_pdf.py` هست — pattern و font selection آن را reuse
کن.
### فایل
1. `backend/app/services/oversight_mega_bundle.py` — تابع جدید
   `build_mega_bundle_pdf(task, report) -> bytes`. تابع موجود
   `build_mega_bundle_md` می‌تواند به‌عنوان helper برای متن ۱۰ بخش
   باقی بماند، یا کل منطق متن داخل _build_text_sections استخراج شود.
2. ساختار pdf:
   - عنوان: `📦 Bundle — {task.title}`
   - تاریخ تولید
   - بخش‌های ۱-۱۰ همان که در md/html هست (heading + body)
   - فونت با پشتیبانی فارسی (همان فونتی که build_verify_report_pdf
     استفاده می‌کند).
   - RTL support اگر کتابخانه پشتیبانی می‌کند.
   - حداکثر اندازه: 5MB (Telegram تا 20MB قبول دارد ولی پروژه trim
     قبلی ۱MB داشت — برای pdf حد بالاتری مناسب است).
### Wire-up
در `_send_mega_bundle` (در `oversight_verifier.py`):
- به‌جای `build_mega_bundle_md` صدا بزن `build_mega_bundle_pdf`.
- filename: `bundle_{task_id[:12]}_{ts}.pdf`
- caption: همان `📦 بسته‌ی کامل verify — «{title}»`.
اگر ساخت pdf شکست خورد → fallback به html (همان رفتار قبلی) با log
warning.
### نکات
- پشتیبانی فارسی pdf کمی پیچیده است. اگر کتابخانهٔ موجود ReportLab است،
  باید فونت TTF Persian (مثل Vazir یا Tahoma) ثبت شده باشد. اگر
  `oversight_verify_pdf.py` فونت ثبت می‌کند، همان را reuse کن.
- اگر هیچ فونت Persian نیست، fallback به همان html (بهتر از pdf
  مbroken).
---
## فیکس ۳ — بهبود vision prompt برای تشخیص feature
### هدف
vision در حال حاضر فقط صفحه را توصیف می‌کند. باید صریحاً تشخیص دهد
«آیا feature ذکرشده در AC در این صفحه قابل مشاهده است یا نه؟» و این
تشخیص روی pass/fail probe تأثیر بگذارد.
### فایل ۱
`backend/app/services/verify_runtime/vision_helper.py` — تابع
`analyze_screenshot` را extend کن:
- prompt را عوض کن تا علاوه بر `description`, `ui_elements`, و غیره،
  این فیلد جدید را هم برگرداند:
"feature_present": "yes" | "no" | "unclear"

که نشان می‌دهد آیا feature مورد نظر (متن AC) در screenshot دیده
می‌شود یا نه.
- پرامپت جدید (الگو):
این screenshot از یک صفحهٔ پروژه نرم‌افزاری است.

📋 ویژگی‌ای که باید بررسی شود:
«{ac_text}»

وظیفهٔ تو:

صفحه را به‌صورت متن غنی توصیف کن (scene, ui_elements, …)
⚠️ مهم‌ترین کار: بسنج که آیا ویژگی فوق در صفحه دیده می‌شود
یا نه. خروجی feature_present:
"yes": کاملاً دیده می‌شود (UI ساخته شده، دکمه/پنل/فرم وجود دارد)
"no": اصلاً دیده نمی‌شود (صفحه عمومی است، feature ساخته نشده)
"unclear": مطمئن نیستی یا اطلاعات کافی نیست
خروجی JSON:
{
"scene": "...",
"ocr_text": "...",
"ui_elements": "...",
"error_signals": "...",
"feature_present": "yes" | "no" | "unclear",
"feature_reason": "چرا این تشخیص — یک جمله"
}

- بازگشت تابع: علاوه بر فیلدهای فعلی، `feature_present` و `feature_reason`.
### فایل ۲
`backend/app/services/verify_runtime/inspector_probe.py` — منطق
pass/fail:
- در محل محاسبهٔ `passed` (حدود خط 590)، vision result را هم در نظر بگیر:
```python
# اگر vision قطعاً گفته feature_present=no، probe باید failed باشد
# حتی اگر navigate ok بود و console error نبود
vision_says_no = False
for shot in screenshots:
    vd = shot.get("vision_feature_present")
    if vd == "no":
        vision_says_no = True
        break
if vision_says_no:
    status = PROBE_STATUS_FAILED
    # یک assertion اضافه کن:
    assertion_results.append({
        "expectation": f"feature «{ac_text[:80]}» در صفحه دیده شود",
        "met": False,
        "reason": "vision AI تشخیص داد feature در صفحه وجود ندارد",
    })
screenshot dict باید دارای فیلد جدید باشد:
shot["vision_feature_present"] = vres.get("feature_present")
shot["vision_feature_reason"] = vres.get("feature_reason")
فایل ۳ — propagate به mega-bundle
backend/app/services/oversight_mega_bundle.py — در بخش probes
(در حلقه شواهد دانه‌به‌دانه):

اگر screenshot دارای vision_feature_present بود، آن را نمایش بده:
- feature_present: ❌ NO — vision AI: ...
فایل ۴ — UI inline (اختیاری ولی توصیه‌شده)
frontend/src/app/oversight/page.tsx — در inline runtime probes، اگر
شات vision_feature_present === "no" بود، یک علامت قرمز اضافه کن:

🔴 feature dynamic ساخته نشده (vision detection)
نکات ایمنی
اگر vision_helper برمی‌گردد source="none" (هیچ vision در دسترس نبود)،
feature_present را نادیده بگیر (همان رفتار قدیم — passed بر اساس
navigate + console).
اگر feature_present="unclear"، probe status را عوض نکن (همان
passed/failed قدیم).
فقط "no" قطعی باعث می‌شود passed → failed.
✅ Done definition (سخت‌گیر)
در نوتیفیکیشن تلگرام، خود متن پیام شامل بلوک چک‌لیست به‌روز
task_steps است (نه فقط در پیوست).
mega-bundle فایل .pdf است (نه .html یا .md)، با فونت فارسی و
تمام ۱۰ بخش قابل خواندن روی موبایل.
در صورت ناتوانی ساخت pdf (مثلاً نبود فونت)، fallback به html
بدون شکست کل verify.
vision_helper فیلد feature_present (yes/no/unclear) برمی‌گرداند.
اگر vision قطعاً گفت no، probe status = failed (با assertion
جدید) — حتی اگر navigate موفق بود.
در mega-bundle، feature_present per screenshot دیده می‌شود.
در UI inline، probe هایی با feature_present=no متمایز هستند.
type-check + python ast پاس.
هیچ بخش موجود از کار نیفتاد (verify سریع، Phase 1 system probe،
Phase 2 per-step probes، بازرس ویژه دستی، …).
--------------------------
فاز سوم:
# 🎯 پرامپت کامل Phase 3 — Form interaction + Auth + Enhanced feature detection
⚠️ این پرامپت Phase 3 از سری «verify جدید» است که پس از Phase 1 و
Phase 2 و سه فیکس آخر اجرا می‌شود.
══════════════════════════════════════════════════════════════════════
# مرور سریع Phase 1 و 2 (چه چیزی الان داریم)
══════════════════════════════════════════════════════════════════════
✅ **Phase 1** اضافه کرد:
- inspector_probe.py — Playwright server-side با navigate + click +
  screenshot + console capture + backend log query
- vision_helper.py با fallback chain (multimodal → text-only → none)
- inspector_session با عنوان «🤖 auto-verify · …» برای visibility
- TTL cleanup + startup recovery + telegram screenshot+followup
✅ **Phase 2** اضافه کرد:
- Per-step probes با route inferred از step.title/scope
- Network capture (frontend + backend URLs per probe)
- Step-aware AI verifier prompt
- prompt_history + apply_followup_as_new_prompt + revert endpoint
- mega-bundle (PDF با fallback HTML)
✅ **سه فیکس آخر** اضافه کرد:
- چک‌لیست در caption تلگرام
- Bundle PDF (نه HTML)
- Vision `feature_present` (yes/no/unclear) با pass/fail flip
══════════════════════════════════════════════════════════════════════
# محدودیت‌های فعلی که Phase 3 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 2 + سه فیکس مشخص شد:
1. **probe فقط navigate می‌کند و نگاه می‌کند** — نمی‌تواند با feature
   تعامل کند. اگر feature یک دکمه باشد، probe دکمه را نمی‌زند تا
   ببیند modal باز می‌شود یا نه.
2. **Vision feature_present حدود ۴۰٪ false-positive دارد** —
   step probe 2 «اضافه کردن UI انتخاب محتوا» را passed داد در حالی
   که UI ساخته نشده بود. علت: vision دکمه‌های عمومی صفحه را دید و
   فکر کرد همینه. اگر probe می‌توانست «کلیک روی selector_hint و
   چک کردن modal/result» را انجام دهد، تشخیص دقیق‌تر بود.
3. **صفحات با لاگین قابل بررسی نیستند** — مثلاً اگر کاربر تسکی روی
   `/admin/dashboard` تعریف کند، probe redirect به /login می‌خورد
   و تشخیص «این feature ساخته شده» غلط می‌شود (همان مشکلی که در
   system probe رخ داد — vision گفت «صفحه login می‌بینم»).
4. **AC هایی که نیاز به submit فرم دارند نمی‌توانند تست شوند** —
   مثلاً «وقتی فرم لاگین پر شود و submit شود، کاربر به داشبورد می‌رود».
══════════════════════════════════════════════════════════════════════
# هدف کلی Phase 3 — سه قابلیت متمم
══════════════════════════════════════════════════════════════════════
**A) Form/Input Interaction Recipes**
inspector_probe باید پشتیبانی کند از:
- `fill {selector, value}` — تایپ متن در input/textarea
- `submit {form_selector}` یا کلیک روی دکمهٔ submit
- `wait_for {selector, timeout_ms, state}` — صبر تا المنت ظاهر شود
- `select {selector, option}` — انتخاب از dropdown
- `check {selector}` / `uncheck {selector}` — checkbox/radio
- `hover {selector}` — برای tooltip ها
- `wait_for_url {contains}` — صبر تا URL تغییر کند (برای SPA)
این actions در `verify_plan.ui_steps` تعریف می‌شوند (schema موجود
ui_probe). به‌جای اینکه inspector_probe فقط `navigate + click hint`
انجام دهد، اگر `ui_steps` کامل بود، تمام sequence را اجرا کند.
**B) Authentication / Session Management**
WatchedProject از قبل فیلد `runtime_auth: {type, value}` دارد. الان
ui_probe (نه inspector_probe) فقط ازش استفاده می‌کند. باید:
- inspector_probe هم cookie/bearer auth را اعمال کند قبل از navigate
- Auto-detect login redirect → اگر صفحه به /login redirect شد،
  evidence را با وضعیت «نیاز به لاگین» علامت بزن
- Auth recipe در WatchedProject — یک sequence «navigate to /login →
  fill email → fill password → submit → wait_for_url(/dashboard)»
  که قبل از هر verify run یک‌بار اجرا می‌شود و cookies را برای
  استفاده‌ی probe ها ذخیره می‌کند (storage state)
- ذخیره storage state در DB (یا فایل امن) با حفظ امنیت (cookie ها
  encrypted)
**C) Enhanced Feature Detection (multi-screenshot + before/after)**
به‌جای یک screenshot واحد:
- screenshot قبل از interaction
- screenshot بعد از interaction
- Vision آنالیز diff: «بعد از کلیک، چه چیزی روی صفحه ظاهر شد؟»
- Network call analysis: آیا interaction باعث backend call شد؟
  (مثلاً submit form → POST request)
- اگر AC انتظار modal دارد، چک کن modal واقعاً ظاهر شد
══════════════════════════════════════════════════════════════════════
# A) Form Interaction Recipes — جزئیات
══════════════════════════════════════════════════════════════════════
## فایل‌ها
**Backend — تغییر**
`backend/app/services/verify_runtime/inspector_probe.py`:
در `_run_inspector_inner`، پس از navigate و قبل از single-click logic،
یک «execution loop» اضافه شود که اگر `verify_plan.ui_steps` بیش از یک
step غیر-navigate دارد، همه را اجرا کند.
تابع helper جدید `_execute_ui_step(page, step, context, recorder)`:
- Input: step dict {action, selector, value, timeout_ms, ...}
- اجرای action با Playwright API
- ثبت نتیجه در `actions_taken`
- در صورت شکست: error_message + screenshot
- خروجی: (success: bool, message: str, screenshot_label: Optional[str])
Actions پشتیبانی شده:
```python
SUPPORTED_ACTIONS = {
    "navigate",       # page.goto(url)
    "click",          # page.click(selector)
    "fill",           # page.fill(selector, value)
    "submit",         # page.locator(selector).press("Enter") یا
                     # await page.locator(selector + " button[type=submit]").click()
    "select",         # page.select_option(selector, value)
    "check",          # page.check(selector)
    "uncheck",        # page.uncheck(selector)
    "hover",          # page.hover(selector)
    "wait_for",       # page.wait_for_selector(selector, timeout, state)
    "wait_for_url",   # page.wait_for_url(pattern, timeout)
    "wait_for_load",  # page.wait_for_load_state(state)
    "screenshot",     # take a labeled screenshot
    "scroll_to",      # page.locator(selector).scroll_into_view_if_needed()
    "press_key",      # page.keyboard.press(key)
    "assert_visible", # page.locator(selector).is_visible()
    "assert_text",    # page.locator(selector).text_content() contains x
    "assert_url",     # page.url contains x
}
هر step خروجی:

{
    "step_idx": int,
    "action": str,
    "selector": Optional[str],
    "value": Optional[str],
    "success": bool,
    "duration_ms": int,
    "message": str,
    "error": Optional[str],
    "screenshot_label": Optional[str],
}
شرط شکست
اگر action ناشناخته → step error, ادامه با بقیه
اگر selector پیدا نشد → step failed, screenshot قبل از خروج
اگر timeout (default 5s per step) → step failed
اگر any step failed → probe overall failed (مگر آنکه assert step
ها خروجی expected داشتند)
sequence per task_step
وقتی Phase 2 step probe می‌سازد، الان فقط:

verify_plan = {
    "ui_steps": [{"action": "navigate", "url": route}]
}
در Phase 3، AI enricher باید پیشنهاد کند یک sequence کامل بر اساس
step.title و step.scope:

مثلاً برای step «اضافه کردن UI انتخاب و اتصال محتوا»:
ui_steps: [
    {"action": "navigate", "url": "/debate"},
    {"action": "wait_for", "selector": "[data-testid='page-loaded']",
     "timeout_ms": 3000},
    {"action": "screenshot", "label": "initial"},
    {"action": "click", "selector": "[data-testid='btn-attach']"},
    {"action": "wait_for", "selector": "[data-testid='attach-modal']",
     "timeout_ms": 2000},
    {"action": "screenshot", "label": "after_click_attach"},
    {"action": "assert_visible", "selector": "[data-testid='content-list']"}
]
این sequence را AI enricher هنگام enrich AC تولید می‌کند —
نیازی به دستی کد کاربر نیست. AI با دیدن AC + target_files یک
recipe پیشنهاد می‌دهد.

بازمراجعه به enricher (ac_enricher.py)
prompt enricher را بهبود ده تا برای method=ui_interaction، یک
sequence ۳-۸ step واقعی پیشنهاد دهد (نه فقط [{action: navigate}]).
selector ها با احتیاط [data-testid='...'] (با اخطار در commit
message که ممکن است باید adjust شود).

══════════════════════════════════════════════════════════════════════

B) Authentication / Session Management — جزئیات
══════════════════════════════════════════════════════════════════════

فایل‌ها
Backend — تغییر
backend/app/services/oversight_service.py:

افزودن به WatchedProject:

# 🆕 (Phase 3) — auth recipe برای probe ها
# اگر تنظیم شد، قبل از هر verify run یک login flow اجرا می‌شود و
# storage_state (cookies + localStorage) برای استفاده‌ی probe ها
# ذخیره می‌شود.
runtime_auth_recipe: Optional[Dict[str, Any]] = None
# ساختار:
# {
#   "type": "form_login",
#   "login_url": "/login",
#   "steps": [
#     {"action": "fill", "selector": "input[name=email]",
#      "value_env": "TEST_EMAIL"},  # یا "value": "test@test.com"
#     {"action": "fill", "selector": "input[name=password]",
#      "value_env": "TEST_PASSWORD"},
#     {"action": "click", "selector": "button[type=submit]"},
#     {"action": "wait_for_url", "contains": "/dashboard",
#      "timeout_ms": 5000},
#   ],
#   "success_indicator": {"selector": "[data-testid='user-menu']",
#                         "must_exist": true},
#   "session_ttl_minutes": 30,  # storage_state بعد از این مدت refresh
# }

# 🆕 (Phase 3) — cached storage state (encrypted)
runtime_storage_state: Optional[Dict[str, Any]] = None
# {
#   "encrypted_blob": str,  # AES-GCM encrypted JSON storage_state
#   "expires_at": ISO,
#   "obtained_at": ISO,
#   "login_failed_count": int,
# }
Backend — فایل جدید
backend/app/services/verify_runtime/auth_runner.py:

تابع async def obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict[str, Any]]:

اگر runtime_auth_recipe تنظیم نشده → return None
اگر runtime_storage_state معتبر و expires_at > now و force=False →
decrypt و return
در غیر این صورت: launch Chromium → execute recipe.steps → اگر
success_indicator OK → دریافت storage_state از context →
encrypt → ذخیره در watched → return decoded
اگر login شکست خورد → login_failed_count += 1، return None
بعد از ۳ شکست متوالی → recipe را disable موقت (با log)
تابع helper _encrypt_storage(data: Dict, key: bytes) -> str و
معکوس _decrypt_storage(blob: str, key: bytes) -> Dict:

AES-GCM با کلید مشتق از env OVERSIGHT_AUTH_KEY (اگر نبود، یک
کلید تصادفی بساز و در env ست کن — warning log)
این برای اینکه cookie ها در plaintext در DB نمی‌مانند.
Backend — تغییر دیگر
backend/app/services/verify_runtime/inspector_probe.py:

پشتیبانی از ProbeContext.storage_state (فیلد جدید در base.py):

اگر ctx.storage_state پر است:
context = await browser.new_context(
    viewport={"width": 1280, "height": 800},
    storage_state=ctx.storage_state,  # Playwright API
)
این تمام cookies + localStorage را به probe می‌دهد بدون نیاز به
login مجدد.
Backend — تغییر در verifier
backend/app/services/oversight_verifier.py:

در _verify_task، قبل از ساخت ProbeContext:

# 🆕 (Phase 3) — اگر watched recipe دارد، storage_state بگیر/تازه کن
auth_storage_state = None
if watched and getattr(watched, "runtime_auth_recipe", None):
    try:
        from .verify_runtime.auth_runner import obtain_or_refresh_storage_state
        auth_storage_state = await obtain_or_refresh_storage_state(watched)
    except Exception as _ae:
        logger.warning(f"auth runner failed: {_ae}")

_probe_ctx = build_probe_context(
    ...,
    storage_state=auth_storage_state,
)
Login redirect detection
در _run_inspector_inner، بعد از navigate، چک کن:

اگر page.url شامل /login یا /signin بود (و route قبلی این نبود)
یا page.title شامل «Login» یا «ورود» بود
→ علامت‌گذاری probe با auth_required: true در evidence
vision_helper این را می‌گیرد و در feature_present تأثیر می‌دهد
auth_required = False
final_url_lower = (page.url or "").lower()
if any(p in final_url_lower for p in ("/login", "/signin", "/auth")):
    if "/login" not in full_url.lower():  # خود route نبود
        auth_required = True

evidence["auth_required"] = auth_required
if auth_required:
    assertion_results.append({
        "expectation": "صفحه‌ی هدف بدون redirect به login باز شود",
        "met": False,
        "reason": f"redirect به {page.url} — احتمالاً auth recipe لازم است",
    })
══════════════════════════════════════════════════════════════════════

C) Enhanced Feature Detection — جزئیات
══════════════════════════════════════════════════════════════════════

Before/After screenshot pairs
وقتی verify_plan.ui_steps شامل interaction (click/fill/submit) است:

screenshot قبل از اولین interaction (label="before_interaction")
screenshot بعد از آخرین interaction (label="after_interaction")
Vision آنالیز diff: prompt جدید برای vision_helper
# vision_helper.py — تابع جدید
async def analyze_screenshot_pair(
    before_path: str,
    after_path: str,
    context: Dict[str, Any],  # شامل ac_text و actions_taken
) -> Dict[str, Any]:
    """آنالیز یک جفت screenshot قبل/بعد از interaction.

    Returns:
      {
        "before_description": str,
        "after_description": str,
        "diff_description": str,    # «بعد از کلیک X، Y ظاهر شد»
        "interaction_succeeded": "yes" | "no" | "unclear",
        "feature_present": "yes" | "no" | "unclear",
        "source": str,
      }
    """
این تابع از multimodal vision یک prompt دو-عکسی می‌فرستد و می‌پرسد:
«قبل از این تعامل، صفحه X بود. بعد از تعامل، Y شد. آیا تعامل کار
کرد و feature واقعاً عمل کرد؟»

Network call analysis
inspector_probe قبلاً backend_urls_called ذخیره می‌کرد. در Phase 3:

اگر AC انتظار یک API call خاص دارد (مثلاً «POST /api/debates ساخته
شود»)، probe باید بفهمد آیا آن endpoint در network_calls هست:

# در verify_plan
"expected_api_calls": [
    {"method": "POST", "path_contains": "/api/debates"},
    {"method": "GET", "path_contains": "/api/projects/.*/files"},
]
probe بعد از interaction چک می‌کند:

expected = plan.get("expected_api_calls") or []
for exp in expected:
    matched = any(
        c.get("method") == exp["method"]
        and exp["path_contains"] in (c.get("url") or "")
        for c in network_calls
    )
    assertion_results.append({
        "expectation": f"API call {exp['method']} {exp['path_contains']}",
        "met": matched,
        "reason": "ثبت شد" if matched else "ثبت نشد",
    })
Multi-screenshot evidence storage
الان _MAX_SCREENSHOTS = 2. در Phase 3 بالا ببر به 5 (یا 6) تا
interaction های پیچیده کاملاً capture شوند.

══════════════════════════════════════════════════════════════════════

D) UI — تنظیمات auth recipe
══════════════════════════════════════════════════════════════════════

frontend/src/app/oversight/page.tsx — در همان panel «runtime» که
runtime_repo_path و base URLs ست می‌شوند:

یک بخش جدید «🔐 Auth Recipe (اختیاری)»
form فیلدها:
login_url (text input)
email (text input — برای save در env var name)
password (text input — برای save در env var name)
email selector (text input — مثلاً input[name=email])
password selector (text input)
submit selector
success indicator selector
session_ttl_minutes (number, default 30)
دکمه «🧪 Test login» که recipe را یک‌بار اجرا می‌کند و نتیجه را
نشان می‌دهد (success_indicator پیدا شد؟)
دکمه «🔄 Refresh session» که storage_state فعلی را invalidate و
دوباره می‌سازد
══════════════════════════════════════════════════════════════════════

E) AI Enricher بهبود — recipe generation
══════════════════════════════════════════════════════════════════════

backend/app/services/verify_runtime/ac_enricher.py:

برای method=ui_interaction، prompt enricher را extend کن تا یک
recipe ۳-۸ step واقعی پیشنهاد دهد (نه فقط navigate).

prompt جدید (extend):

برای روش ui_interaction، یک sequence ۳ تا ۸ مرحله‌ای پیشنهاد بده
که برای تأیید این AC کفایت کند. مراحل باید شامل:
1. navigate به صفحه‌ی مرتبط
2. wait_for یک selector که نشان دهد صفحه load شده
3. screenshot قبل از تعامل
4. در صورت لزوم، fill/click/submit برای trigger feature
5. wait_for selector جدید یا تغییر URL
6. screenshot بعد از تعامل
7. assert_visible یا assert_text برای تأیید feature
selector ها را با `[data-testid='...']` ساختگی پیشنهاد بده (با
اخطار در commit message).
برای AC که فقط «نمایش بدون تعامل» است (مثلاً «اطلاعات کاربر
نمایش داده شود»)، sequence را به ۳ مرحله (navigate + wait + assert)
محدود کن.
══════════════════════════════════════════════════════════════════════

Done definition (سخت‌گیر)
══════════════════════════════════════════════════════════════════════

inspector_probe می‌تواند sequence ۸ مرحله‌ای را اجرا کند (navigate
wait + click + fill + submit + wait + assert + screenshot).
هر step خروجی isolated دارد (success, duration, error, screenshot_label).
WatchedProject فیلد runtime_auth_recipe دارد و قابل تنظیم از UI است.
اگر recipe تنظیم شد، قبل از verify یک‌بار login اجرا می‌شود و
storage_state کش می‌شود (encrypted).
probe ها از storage_state برای دسترسی به صفحات با لاگین استفاده
می‌کنند.
Login redirect detection کار می‌کند — اگر probe به /login redirect
خورد، assertion auth_required: false با reason ثبت می‌شود.
Before/After screenshot pair برای step هایی با interaction گرفته
می‌شود.
Vision pair analysis قابل دسترس است (تابع جدید analyze_screenshot_pair).
expected_api_calls در verify_plan قابل تعریف است و assertion چک
می‌شود.
AI enricher recipe ۳-۸ مرحله‌ای پیشنهاد می‌دهد (نه فقط navigate).
UI auth recipe panel کار می‌کند با Test login + Refresh session.
هیچ بخش موجود از کار نیفتاد (Phase 1, Phase 2, سه فیکس، verify
سریع، بازرس ویژه دستی، …).
type-check + python ast پاس.
تست واقعی: روی یک تسک با task_steps چندگانه و یک recipe ساده،
probe ها sequence را اجرا کنند، حداقل ۲ probe interaction واقعی
داشته باشند (نه فقط navigate).
══════════════════════════════════════════════════════════════════════

محدودیت‌های ایمنی
══════════════════════════════════════════════════════════════════════

per-step timeout: ۵ ثانیه (configurable در plan.step_timeout_ms)
per-probe timeout: ۹۰ ثانیه (افزایش از ۶۰ به ۹۰ برای recipe طولانی)
max screenshots per probe: ۵ (افزایش از ۲)
max ui_steps per probe: ۱۲ (محدودیت سخت — اگر AC بیشتر خواست، AC
باید به دو step تقسیم شود)
network capture: همان ۳۰ request
auth recipe value_env reference: فقط env vars با prefix
WATCHED_AUTH_* قابل استفاده — جلوگیری از leak credentials از
env های دیگر
storage_state encryption: AES-GCM با کلید مشتق از env
OVERSIGHT_AUTH_KEY. اگر نبود، fail-soft (recipe disabled با
هشدار)
max recipe step timeout: ۱۵ ثانیه (auth recipe می‌تواند کمی طولانی‌تر
از step probe عادی باشد)
اگر login_failed_count >= ۳ → recipe موقت disable + alert در
inspector_session
هیچ password/cookie در evidence یا inspector_session messages
ذخیره نشود — فقط auth_state: "valid" | "expired" | "failed"
══════════════════════════════════════════════════════════════════════

شکست‌خوردگی‌های مجاز (graceful degrade)
══════════════════════════════════════════════════════════════════════

recipe نبود → probe بدون auth (همان رفتار Phase 2)
recipe شکست خورد → probe بدون storage_state (و evidence با
auth_attempted: true, auth_failed: true)
expected_api_calls فیلد نبود → فقط assertion ها بدون این چک
before/after pair خراب شد → یکی از screenshot ها استفاده شود
(fallback به single screenshot vision)
vision pair analysis fail → fallback به single-screenshot vision
enricher recipe خراب → fallback به همان navigate-only Phase 2
step ناشناخته → error در همان step، بقیه continue
══════════════════════════════════════════════════════════════════════

فایل‌های نهایی
══════════════════════════════════════════════════════════════════════

Backend جدید
backend/app/services/verify_runtime/auth_runner.py (login flow
executor + storage_state encrypt/decrypt)
Backend تغییر
backend/app/services/verify_runtime/base.py (ProbeContext فیلد
storage_state اضافه)
backend/app/services/verify_runtime/inspector_probe.py (action
loop + auth check + login redirect detection + before/after pairs +
expected_api_calls assertion + max screenshots افزایش)
backend/app/services/verify_runtime/vision_helper.py (تابع
جدید analyze_screenshot_pair)
backend/app/services/verify_runtime/runner.py (build_probe_context
پارامتر storage_state)
backend/app/services/verify_runtime/ac_enricher.py (prompt update
برای recipe ۳-۸ مرحله‌ای)
backend/app/services/oversight_service.py (WatchedProject فیلدهای
runtime_auth_recipe و runtime_storage_state)
backend/app/services/oversight_verifier.py (obtain storage_state
قبل از probes)
backend/app/api/routes/oversight.py (endpoint های test-login و
refresh-session برای auth panel)
Frontend
frontend/src/app/oversight/page.tsx (auth recipe panel در runtime
section + Test login + Refresh session buttons + نمایش
auth_required در runtime probes inline)
══════════════════════════════════════════════════════════════════════

ساختار داده‌ی نهایی per-step probe (Phase 3)
══════════════════════════════════════════════════════════════════════

{
  "ac_id": "step_3",
  "ac_text": "(step probe #3) ...",
  "method": "ui_interaction",
  "status": "passed | failed | error | skipped",
  "evidence": {
    "inspector_session_id": int,
    "step_id": int, "step_title": str, "step_inferred_route": str,
    "actions_taken": [
      {"step_idx": 0, "action": "navigate", "url": "/debate",
       "success": true, "duration_ms": 1234},
      {"step_idx": 1, "action": "wait_for",
       "selector": "[data-testid='page-loaded']", "success": true,
       "duration_ms": 250},
      {"step_idx": 2, "action": "screenshot", "label": "before_click",
       "success": true},
      {"step_idx": 3, "action": "click",
       "selector": "[data-testid='btn-attach']", "success": false,
       "error": "selector not found", "duration_ms": 5000},
      ...
    ],
    "screenshots": [
      {"path": "...", "label": "before_click",
       "vision_description": "...", "vision_feature_present": "no", ...},
      {"path": "...", "label": "after_click",
       "vision_description": "...", "vision_feature_present": "yes", ...},
      ...
    ],
    "vision_pair": {  # اگر pair analysis اجرا شده
       "before_description": "...",
       "after_description": "...",
       "diff_description": "بعد از کلیک، modal باز شد و فرم ظاهر شد",
       "interaction_succeeded": "yes",
       "feature_present": "yes"
    },
    "console_errors": [...],
    "network_calls": [...],
    "backend_urls_called": [...],
    "expected_api_calls_results": [
       {"expectation": "POST /api/debates", "met": true},
       ...
    ],
    "auth_required": bool,
    "auth_state": "valid | expired | failed | none",
    "assertion_results": [...],
    "final_url": str,
    "probe_type": "inspector_phase3"  # version bump
  },
  "duration_ms": int
}
══════════════════════════════════════════════════════════════════════

شرط passed/failed/error (به‌روزشده)
══════════════════════════════════════════════════════════════════════

PASSED:

همه‌ی ui_steps موفق (navigate ok + هر step success=true)
هیچ console error سطح "error"
vision_feature_present != "no" (یا "yes" یا "unclear")
اگر pair analysis اجرا شد، interaction_succeeded != "no"
اگر expected_api_calls تعریف شد، همه match شدند
FAILED: یکی از موارد بالا نقض شود.

ERROR: Playwright crash، timeout > 90s، auth runner crash.

SKIPPED: frontend_base_url نیست، env flag disabled، breaker open.

══════════════════════════════════════════════════════════════════════

شروع کار
══════════════════════════════════════════════════════════════════════

وقتی این پرامپت ارسال شد:

TodoWrite قطعه‌بندی کن — ترتیب پیشنهادی:
A1: ProbeContext.storage_state field
A2: _execute_ui_step helper + action loop
A3: enricher prompt update برای recipe طولانی
B1: WatchedProject fields (recipe + storage_state)
B2: auth_runner.py
B3: integration در _verify_task
B4: login redirect detection
C1: before/after screenshot pairs
C2: vision_helper.analyze_screenshot_pair
C3: expected_api_calls assertion
D: UI auth panel + test endpoints
Validation + commits + push
هر بخش یک commit جداگانه. کد کار نکن یکجا — قطعه قطعه.
هر تصمیم بزرگ (مثلاً انتخاب کتابخانه encryption، یا ساختار recipe)
را قبل از کد در پیام شرح بده.
تست‌نکته‌ها در پایان: روی یک تسک با recipe ساده (مثلاً auth +
navigate به /admin) verify بزن و خروجی را نشان بده.
هیچ بخش موجود را نشکن. Phase 1 + Phase 2 + سه فیکس باید همچنان
کار کنند.
در پایان، یک خلاصه‌ی فایل‌های تغییر‌یافته و نمونه‌ای از probe
evidence Phase 3 ارسال کن.
-------------------------
فاز چهارم:


# 🎯 پرامپت کامل Phase 4 — Smart Navigation + Backend Log Probe + Code-aware Verifier
⚠️ این پرامپت Phase 4 از سری «verify جدید» است که پس از Phase 1، 2،
و 3 (شامل سه فیکس آخر) اجرا می‌شود.
══════════════════════════════════════════════════════════════════════
# مرور خیلی سریع وضعیت فعلی
══════════════════════════════════════════════════════════════════════
✅ **Phase 1**: inspector_probe پایه با navigate + screenshot + vision +
   session + telegram + cleanup + recovery.
✅ **Phase 2**: per-step probes + prompt versioning + mega-bundle PDF.
✅ **Phase 3**: action loop (fill/click/wait/assert) + auth recipe +
   vision_pair + expected_api_calls + force backfill + Telegram trigger.
✅ **سه فیکس آخر**: SPA-404 detection + system probe relaxation +
   conservative routing (skip when no specific route).
══════════════════════════════════════════════════════════════════════
# مشکلات باقیمانده که Phase 4 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 3 + سه فیکس مشخص شد:
1. **route guessing ضعیف**: برای تسک trading-system که صفحات URL خاصی
   داشتند (مثل /routing-diagram, /charts)، probe نمی‌تواند URL واقعی
   را پیدا کند. حدس‌های keyword-based 404 می‌گیرند. کاربر گفت در
   تجربه قبلی هم با این مشکل اذیت شده بود.
2. **تسک‌های backend-heavy benefit صفر می‌گیرند**: تسک‌هایی مثل
   DebateAttachment (backend models, endpoints, service logic) از
   probe UI سود نمی‌برند چون feature تو UI دیده نمی‌شود. probe ها
   skipped می‌شوند ولی verify بدون شواهد runtime می‌ماند.
3. **استفاده ناکامل از Render logs**: الان فقط لاگ‌های window زمانی
   probe فیلتر می‌شوند (level=error/warn). با اینکه RENDER_API_KEY ست
   شده، از لاگ‌های مرتبط به فایل‌های target تسک یا call های endpoint
   مرتبط استفاده نمی‌کنیم.
4. **استفاده ناکامل از inspector chat infrastructure**: بازرس ویژه
   دستی از قبل لاگ‌های backend + console همراه هر پیام چت ذخیره
   می‌کند، ولی auto-verify از این infrastructure استفاده نمی‌کند.
══════════════════════════════════════════════════════════════════════
# هدف کلی Phase 4 — سه ستون
══════════════════════════════════════════════════════════════════════
**A) Smart Navigation Probe (Agentic Browsing)**
به‌جای حدس زدن URL از روی keyword، probe به home می‌رود، nav menu
را می‌خواند، و AI تصمیم می‌گیرد کدام لینک به feature مرتبط است.
این الگوی استاندارد OpenAI Operator / Anthropic Computer Use است.
**B) Backend Log Probe**
برای تسک‌های backend-heavy (که AC شون از UI element حرف نمی‌زند)،
به‌جای probe UI، یک probe جدید لاگ‌های Render فیلتر شده بر اساس
target_files تسک + AC keywords را تحلیل می‌کند. خروجی: «آیا این
feature backend deploy شده و call می‌شود؟»
**C) Code-aware Verifier (Per-AC commit analysis)**
gh API الان فقط در سطح کل تسک استفاده می‌شود. در Phase 4، برای هر
AC جداگانه چک می‌شود که آیا diff اخیر آن AC را پیاده کرده یا نه.
این بدون نیاز به repo کلون محلی، با همان GitHub API که داریم.
══════════════════════════════════════════════════════════════════════
# درس‌های گرفته‌شده از Phase 1-3 (تا اشتباهات تکرار نشود)
══════════════════════════════════════════════════════════════════════
1. **هرگز feature را فرض نکن**: اگر مطمئن نیستی، SKIPPED بده، نه fake-pass
2. **Vision قابل اعتماد ۱۰۰٪ نیست**: همیشه با لاگ/code/network ادغام شود
3. **SPA-404 خطرناک است**: status=200 با body "Not Found" → چک content
4. **keyword matching ضعیف است**: substring match منجر به 404 می‌شود.
   فقط explicit signals (مثل "X page" یا "/path") استفاده شود.
5. **system probe meta است**: feature_present check روی متن AC اش
   ندارد. این الگو در Phase 4 هم رعایت شود برای anything synthetic.
6. **graceful degrade برای همه چیز**: failure هر بخش نباید verify را
   block کند. fallback به Phase 3 behavior.
══════════════════════════════════════════════════════════════════════
# A) Smart Navigation Probe — جزئیات دقیق
══════════════════════════════════════════════════════════════════════
## هدف
وقتی AC اشاره صریح به `/path` ندارد و keyword matching هم نتوانست
route را پیدا کند، به‌جای SKIPPED شدن، یک تلاش هوشمند برای پیدا
کردن صفحه صورت گیرد.
## Flow
1. **navigate به home `/`** (یا frontend_base_url)
2. **استخراج لینک‌های navigation** با Playwright:
   ```python
   nav_links = await page.locator(
       'nav a, [role="navigation"] a, header a, aside a, '
       '.sidebar a, .menu a, [data-testid*="nav"] a'
   ).all()
   links_data = []
   for link in nav_links[:30]:  # cap به ۳۰ تا
       text = (await link.text_content() or "").strip()
       href = await link.get_attribute("href") or ""
       if text and href and not href.startswith(("http", "mailto:", "tel:")):
           links_data.append({"text": text, "href": href})
AI link picker (تابع جدید pick_nav_link_for_ac در
navigation_helper.py):
async def pick_nav_link_for_ac(
    ac_text: str,
    links: List[Dict[str, str]],
    verify_model_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """به AI لیست لینک‌های nav داده می‌شود + متن AC.
    AI انتخاب می‌کند کدام لینک احتمالاً به feature ربط دارد.
    
    Returns: {chosen: dict | None, confidence: "high|medium|low|none",
              reason: str}
    اگر confidence == "none" یا "low" → SKIPPED.
    """
پرامپت AI:
تو در حال بررسی یک پروژه نرم‌افزاری هستی. یک ویژگی (AC) تعریف شده،
و باید از لینک‌های منوی ناوبری انتخاب کنی کدام یکی احتمالاً به
صفحه‌ی این ویژگی می‌رود.
📋 AC: {ac_text}
📍 لینک‌های منو:
1. text="داشبورد" href="/dashboard"
2. text="استراتژی‌ها" href="/strategies"
...
⚠️ راهنما:
- فقط لینکی را انتخاب کن که با احتمال بالا به feature این AC ربط
  دارد (نه شباهت ظاهری اسم).
- اگر هیچ لینکی مرتبط نیست، confidence="none" بده.
- اگر چندتا کاندیدا هست، high-confidence یکی را انتخاب کن.
- متن AC را با name و موقعیت لینک تطبیق بده.
خروجی JSON:
{
  "chosen_idx": int یا null,
  "chosen_text": str یا null,
  "chosen_href": str یا null,
  "confidence": "high" | "medium" | "low" | "none",
  "reason": "یک جمله توضیح"
}
اگر AI لینک انتخاب کرد (confidence high/medium):
probe روی اون لینک کلیک می‌کند
URL جدید چک می‌شود (نباید 404 یا login redirect باشد)
ادامه probe (action loop + vision + ...) روی صفحه جدید
اگر AI نتوانست (confidence low/none):
probe SKIPPED با reason "smart navigation: AI نتوانست لینک
مرتبط در nav menu پیدا کند"
محدودیت‌های ایمنی
حداکثر یک level deep — اگر روی لینک کلیک کردیم و submenu باز شد،
level دوم نمی‌رویم (تا verify خیلی طولانی نشود)
timeout 10s برای AI link picker
اگر nav menu خالی است (هیچ <a> در nav element) → SKIPPED
credentials نباید لو برود — link picker AC text را می‌گیرد، نه
ابرداده‌ی sensitive
فایل‌ها
backend/app/services/verify_runtime/navigation_helper.py (جدید)
backend/app/services/verify_runtime/inspector_probe.py (تغییر:
وقتی route inference is_specific=False بود، به‌جای SKIPPED فوری،
smart navigation تلاش کند)
══════════════════════════════════════════════════════════════════════

B) Backend Log Probe — جزئیات دقیق
══════════════════════════════════════════════════════════════════════

هدف
برای تسک‌هایی که AC شون از feature backend حرف می‌زند (نه UI)،
به‌جای probe UI، probe جدیدی که لاگ‌های Render مرتبط را تحلیل می‌کند.

تشخیص نوع تسک
تابع جدید _classify_task_type(task) -> str:

def _classify_task_type(task) -> str:
    """Returns: 'ui' | 'backend' | 'mixed' | 'unknown'"""
    files = task.target_files or []
    py_count = sum(1 for f in files if str(f).endswith('.py'))
    ts_count = sum(1 for f in files if str(f).endswith(('.ts', '.tsx', '.jsx', '.js')))
    
    # AC text keywords
    all_ac_text = " ".join(...).lower()
    ui_keywords = ['button', 'دکمه', 'panel', 'پنل', 'form', 'فرم',
                   'modal', 'page', 'صفحه', 'view', 'تب', 'sidebar',
                   'navbar', 'click', 'کلیک', 'input', 'فیلد']
    backend_keywords = ['endpoint', 'api', 'model', 'مدل داده',
                       'function', 'تابع', 'service', 'سرویس',
                       'database', 'سنخ‌دار', 'middleware', 'cron',
                       'thread', 'lifecycle', 'crud']
    
    ui_score = sum(1 for kw in ui_keywords if kw in all_ac_text)
    backend_score = sum(1 for kw in backend_keywords if kw in all_ac_text)
    
    # combine with file types
    if py_count > 0 and ts_count == 0 and backend_score > ui_score:
        return 'backend'
    if ts_count > 0 and py_count == 0 and ui_score > backend_score:
        return 'ui'
    if py_count > 0 and ts_count > 0:
        return 'mixed'
    if backend_score > ui_score * 2:
        return 'backend'
    if ui_score > backend_score * 2:
        return 'ui'
    return 'mixed'  # default
Backend Log Probe Flow
تابع جدید run_backend_log_probe(ac, ctx, ac_id, task) در فایل
جدید verify_runtime/backend_log_probe.py:

پیدا کردن watched و service_id های Render مرتبط
Query Render logs:
زمان: ۲۴ ساعت اخیر (یا از آخرین commit تسک)
فیلتر: message شامل نام فایل‌های target یا نام تابع/endpoint
استخراج‌شده از AC
حداکثر ۱۰۰ entry
استخراج endpoint URLs از AC:
regex: (?:GET|POST|PUT|DELETE)\s+(/[a-z0-9/_-]+) در AC text
AI analysis (تابع analyze_backend_logs_for_ac):
async def analyze_backend_logs_for_ac(
    ac_text: str,
    logs: List[Dict],
    target_files: List[str],
    verify_model_id: str,
) -> Dict[str, Any]:
    """
    AI بررسی می‌کند: آیا این لاگ‌ها نشان می‌دهند feature backend
    این AC deploy شده و call می‌شود؟
    
    Returns: {
      "verdict": "deployed_working" | "deployed_not_called" | 
                 "deployed_with_errors" | "not_deployed" | "unclear",
      "reason": str,
      "evidence_lines": List[str],  # خطوط لاگ کلیدی
    }
    """
پرامپت:
تو در حال بررسی deploy یک feature backend هستی.
📋 AC: {ac_text}
📁 فایل‌های هدف: {target_files}
📌 endpoint های استخراج‌شده: {extracted_endpoints}
📊 لاگ‌های Render اخیر (مرتبط با این فایل‌ها):
{logs_formatted}
⚠️ مهم:
- اگر لاگ‌ها نشان می‌دهند endpoint یا تابع call شده + بدون خطا → 
  "deployed_working"
- اگر deploy شده ولی هیچ call ای نمی‌بینی → "deployed_not_called"
- اگر خطا/exception می‌بینی → "deployed_with_errors"
- اگر هیچ نشانه‌ای از این کد در لاگ‌ها نیست → "not_deployed"
- اگر مطمئن نیستی → "unclear"
خروجی JSON:
{
  "verdict": "...",
  "reason": "یک جمله",
  "evidence_lines": ["...", "..."]
}
خروجی probe:
deployed_working → PASSED
deployed_with_errors → FAILED (با evidence_lines)
not_deployed / deployed_not_called → FAILED
unclear → SKIPPED با reason
محدودیت ها
اگر هیچ لاگی پیدا نشد → SKIPPED با "no relevant logs"
اگر RenderLog DB خالی است → SKIPPED با "log collection not active"
حداکثر ۱۰۰ log per probe (تا context AI نشکند)
timeout ۱۵s برای AI analysis
فایل‌ها
backend/app/services/verify_runtime/backend_log_probe.py (جدید)
backend/app/services/verify_runtime/runner.py (تغییر: dispatch
برای backend tasks → run_backend_log_probe)
══════════════════════════════════════════════════════════════════════

C) Code-aware Verifier (Per-AC Commit Analysis) — جزئیات دقیق
══════════════════════════════════════════════════════════════════════

هدف
AI verifier فعلی commits رو در سطح کل تسک می‌خواند. در Phase 4،
برای هر AC جداگانه چک می‌شود که آیا اخیراً پیاده شده یا نه.

Flow
تابع جدید analyze_commits_per_ac در
verify_runtime/code_aware_verifier.py:

دریافت commits اخیر که target_files تسک را تغییر داده‌اند
(از طریق GitHub API که الان داریم)
برای هر AC:
استخراج keyword‌های feature از AC (مثل اسم تابع، endpoint, model)
فیلتر commits که این keyword ها را در diff دارند
AI تحلیل: «آیا این diff این AC را پیاده می‌کند؟»
خروجی per-AC:
{
  "ac_text": "...",
  "code_verdict": "implemented" | "partial" | "not_found" | "unclear",
  "matching_commits": ["abc123", "def456"],
  "key_changes": ["+def create_attachment():", ...],
  "reason": "..."
}
ادغام در runtime_probe_results
هر AC که با Code-aware Verifier تحلیل شد، یک "code_probe" در
runtime_probe_results می‌گیرد (با method="code_analysis"). این
کنار UI probe ها قرار می‌گیرد.

محدودیت ها
فقط برای AC هایی که target_files دارند
حداکثر ۲۰ commit per task به AI داده شود (window زمانی محدود)
timeout ۲۰s per AC analysis
AI cost: بسته‌ی AC ها — تا ۱۰ AC در batch
فایل‌ها
backend/app/services/verify_runtime/code_aware_verifier.py (جدید)
backend/app/services/oversight_verifier.py (تغییر: قبل از
run_probes_for_acs، per-AC code analysis اجرا شود)
══════════════════════════════════════════════════════════════════════

Task Type Routing
══════════════════════════════════════════════════════════════════════

در oversight_verifier.py، پس از classify task type:

task_type = _classify_task_type(task)

# همیشه: code-aware verifier برای AC ها
code_results = await analyze_commits_per_ac(task, acceptance_criteria, ...)
runtime_probe_results.extend(code_results)

# بسته به نوع تسک:
if task_type in ('ui', 'mixed'):
    # Phase 3 system probe + per-step probes (با Smart Navigation اضافه)
    runtime_probe_results.extend(await run_ui_probes(...))

if task_type in ('backend', 'mixed'):
    # Backend Log Probe برای backend AC ها
    for ac in acceptance_criteria:
        if _is_backend_ac(ac):
            res = await run_backend_log_probe(ac, ctx, ac_id, task)
            runtime_probe_results.append(res)

if task_type == 'unknown':
    # هر دو + fallback به Phase 3 system probe
    ...
══════════════════════════════════════════════════════════════════════

Telegram Integration
══════════════════════════════════════════════════════════════════════

mega-bundle.md سکشن‌های جدید:

۸.۱ Smart Navigation Decisions
چه nav linksای پیدا شد؟ AI چی انتخاب کرد؟
confidence + reason per task
۸.۲ Backend Log Analysis (per backend AC)
verdict (deployed_working / not_deployed / ...)
evidence_lines
reason
۸.۳ Code-aware Verdict (per AC)
code_verdict
matching_commits
key_changes excerpts
reason
══════════════════════════════════════════════════════════════════════

UI Changes — Minimal
══════════════════════════════════════════════════════════════════════

inline probe row حالا سه نوع probe جدید را نمایش می‌دهد:

🧭 smart-nav probe (با link انتخاب‌شده)
📊 backend-log probe (با verdict color)
🔍 code-aware probe (با matching commits)
هر کدام آیکن متفاوت و رنگ متمایز.

══════════════════════════════════════════════════════════════════════

Done Definition (سخت‌گیر)
══════════════════════════════════════════════════════════════════════

Smart Navigation کار می‌کند: روی یک تسک با AC که /path ندارد،
probe به home می‌رود، nav menu را می‌خواند، AI لینک مرتبط را
انتخاب می‌کند، روی آن کلیک می‌کند، و ادامه probe می‌دهد.
Backend Log Probe کار می‌کند: روی یک تسک backend (مثل
DebateAttachment)، به‌جای probe UI، probe جدیدی لاگ‌های Render
فیلتر شده را تحلیل می‌کند و verdict می‌دهد.
Code-aware Verifier کار می‌کند: برای هر AC، یک code_probe در
runtime_probe_results ظاهر می‌شود با verdict (implemented /
not_found / ...).
task type classification درست است: تسک trading-system →
"mixed" یا "backend"، تسک "ساخت صفحه login" → "ui".
هیچ بخش موجود از کار نیفتد: Phase 1, 2, 3 + سه فیکس + همه‌ی
تغییرات اخیر.
mega-bundle شامل سکشن‌های جدید: بخش ۸.۱ smart nav، ۸.۲
backend log، ۸.۳ code-aware.
UI inline سه آیکن جدید نمایش می‌دهد.
type-check + python ast پاس.
══════════════════════════════════════════════════════════════════════

محدودیت‌های سراسری
══════════════════════════════════════════════════════════════════════

per-probe AI cost cap: ۲ AI call (یکی link picker، یکی verdict)
per-task additional time: حداکثر ۹۰ ثانیه (روی Phase 3 ۶۰ثانیه)
AI provider failure → graceful fallback به Phase 3 behavior
لاگ‌های Render اگر در DB نبود (سرویس log_stream_service غیرفعال) →
Backend Log Probe SKIPPED با reason صریح
GitHub API rate limit → Code-aware Verifier ممکن است partial باشد
هرگز credentials در لاگ یا inspector_session نشت نکند
══════════════════════════════════════════════════════════════════════

فایل‌های نهایی
══════════════════════════════════════════════════════════════════════

Backend جدید
verify_runtime/navigation_helper.py (Smart Navigation A)
verify_runtime/backend_log_probe.py (Backend Log Probe B)
verify_runtime/code_aware_verifier.py (Code-aware Verifier C)
Backend تغییر
verify_runtime/inspector_probe.py (Smart Navigation hook)
verify_runtime/runner.py (task type routing)
oversight_verifier.py (orchestration + _classify_task_type +
hooks for backend/code probes)
oversight_mega_bundle.py (سه سکشن جدید در bundle)
Frontend
oversight/page.tsx (سه آیکن جدید: 🧭 📊 🔍)
══════════════════════════════════════════════════════════════════════

شکست‌خوردگی‌های مجاز (graceful degrade)
══════════════════════════════════════════════════════════════════════

AI link picker fail → fallback به skip (Phase 3 behavior)
nav menu خالی → skip smart navigation
Render logs خالی → backend log probe skipped
GitHub API timeout → code-aware verifier skipped per AC
task type "unknown" → fallback به همه (UI + Backend + Code)
AI cost overrun → فقط همان probe skipped، بقیه ادامه
══════════════════════════════════════════════════════════════════════

ترتیب پیاده‌سازی (commits جداگانه)
══════════════════════════════════════════════════════════════════════

Commit 1: _classify_task_type در oversight_verifier.py
Commit 2: code_aware_verifier.py (per-AC commit analysis)
Commit 3: backend_log_probe.py (با endpoint extraction)
Commit 4: navigation_helper.py + integration in inspector_probe
Commit 5: task type routing در _verify_task
Commit 6: mega-bundle سه سکشن جدید
Commit 7: UI inline سه آیکن جدید
Commit 8: type-check + final fixes
══════════════════════════════════════════════════════════════════════

تست واقعی (پس از deploy)
══════════════════════════════════════════════════════════════════════

روی تسک‌های زیر تست:

trading-system task (همان که ۱۲ step backend-heavy داشت):
انتظار: task_type="backend" یا "mixed"
backend_log_probe برای هر AC backend اجرا شود
code-aware verifier verdict per AC بدهد
probe های UI کاهش پیدا کنند (به‌جای 9 تا، شاید ۲-۳ تا UI +
چندتا backend/code)
task مناظره (DebateAttachment):
task_type="backend" (مدل، endpoint، service)
backend_log_probe بگوید "not_deployed" (چون code تغییر نکرده)
code-aware verifier per AC بگوید "not_found in recent commits"
task UI خالص (اگر باشد):
task_type="ui"
smart navigation اجرا شود
probe به صفحه واقعی برسد
══════════════════════════════════════════════════════════════════════

شروع کار
══════════════════════════════════════════════════════════════════════

وقتی این پرامپت ارسال شد:

با TodoWrite قطعه‌بندی کن — ترتیب ۸-commit بالا.
هر بخش قبل از کد، در پیام شرح بده که چه تصمیمی گرفتی، چه
trade-off ای انتخاب کردی، و چرا.
هیچ بخش موجود را نشکن — Phase 1, 2, 3 + سه فیکس باید همچنان
کار کنند.
type-check + python ast بعد از هر commit — اگه شکست، فیکس کن
قبل از commit بعدی.
هر تصمیم بزرگ AI prompt را در پیام نشان بده — کاربر می‌خواهد
ببیند AI چه prompt ای می‌گیرد.
در پایان:
خلاصه‌ای از فایل‌های تغییر یافته
نمونه‌ای از output هر سه probe جدید (mocked اگر نمی‌توان live تست کرد)
تست واقعی روی deploy و گزارش
مهم‌ترین درس از Phase 1-3: اگر مطمئن نیستی، SKIPPED بده نه
fake-pass. صداقت در verify بالاتر از پوشش زیاد است.
قبل از شروع، اگر فکر کردی هر یک از این سه ستون منطقی نیست
یا روش بهتری وجود دارد، حتماً در پیام بگو و قبل از کد تأیید
بگیر. این بار اشتباه نباید بشود.

---------------------------
# 🎯 پرامپت Phase 5 V4 — ارتقای کامل Auto-Scan + Task Creation
> **این پرامپت تمام ۱۴ بند درخواست خام را پوشش می‌دهد. هر فاز با reference به بندهای درخواست خام نشان داده شده.**
---
## 📋 فهرست بندهای درخواست خام (Cross-reference)
| # | بند درخواست خام | پوشش در فاز |
|---|---|---|
| **R1** | scan جدا از verify؛ scan ایجاد task، verify بررسی task | مقدمه |
| **R2** | ایده‌گیری از Phase 4 + به‌روزرسانی گزینه‌های UI | کل فازها + فاز ۹ |
| **R3** | پوشش از ریز تا درشت، یک دور برای کل سیستم | فاز ۱ |
| **R4** | scan باید قوی‌تر از verify باشد | کل فازها |
| **R5** | چک‌لیست برای auto-tasks + Smart mode هوشمند | فاز ۷، ۸ |
| **R6** | Telegram notification برای auto-tasks (caption + silent default) | فاز ۸ |
| **R7** | Delta detection + Bidirectional dependency | فاز ۳ |
| **R8** | شناسایی گزینه‌های قدیمی + task برای آن‌ها (⭐ خیلی خیلی مهم) | فاز ۲ |
| **R9** | Smart prompt + Smart checklist (بدون false-positive) | فاز ۷ |
| **R10** | Logic Audit (هدف، منطق، coherence) | فاز ۵ |
| **R11** | مثال trade — باگ منطقی در هماهنگی | فاز ۵ |
| **R12** | Telegram notification system audit | فاز ۶ |
| **R13** | Smart prompt برای manual + auto | فاز ۷ |
| **R14** | Inspector tab integration (session + screenshots + chats + archive) | فاز ۴ |
---
## 📌 مقدمه و فلسفه
### **R1** — scan ≠ verify
| سیستم | چه می‌کند |
|---|---|
| **verify** (Phase 4، تمام) | روی **تسک‌های موجود** بررسی می‌کند آیا انجام شده یا نه |
| **scan** (این Phase 5) | کل سیستم را بررسی می‌کند تا **تسک‌های واقعاً لازم** کشف و ایجاد شوند |
اگر scan خوب کار نکند → تسک واقعاً لازم اصلاً ساخته نمی‌شود → verify هرگز فرصت بررسی آن را پیدا نمی‌کند. **پس scan حتی از verify مهم‌تر است.**
### **R4** — scan باید قوی‌تر از verify باشد
verify شواهد جمع می‌کند برای **یک task مشخص**. scan شواهد جمع می‌کند برای **کل سیستم**. پس scan ابزارهای بیشتری نیاز دارد:
- همه‌ی Phase 4 components (smart_nav, vision, code-aware, backend-log, inspector_probe)
- **به‌علاوه**: comprehensive inventory، purpose extraction، delta analysis، logical coherence، outcome analysis، notification audit، semantic stale detection
### **چهار پایه**
1. **پوشش ریز تا درشت** (R3)
2. **تغییر-آگاهی + bidirectional dependency** (R7)
3. **رفتار-محوری در پرامپت و چک‌لیست** (R9, R13)
4. **logic awareness از روز اول — purpose، coherence، effectiveness** (R10, R11)
### **هدف نهایی**
بعد از یک scan، **تمام تسک‌های واقعاً لازم** کشف و ساخته شوند، **با چک‌لیست هوشمند، با notification صحیح، با session بازرس کامل**:
- features جدید
- features ناقص
- bugs ساختاری
- bugs منطقی (R11)
- features قدیمی و dead options (R8)
- componentهای منطقاً ناسازگار (R10)
- featuresی که کاربر دیگر نمی‌داند چیست (R8) → با AI explanation
- notification ها ناقص یا اشتباه (R12)
---
## 🅰️ فاز ۱ — Comprehensive Inventory + Purpose Extraction
> پوشش **R3** (ریز تا درشت)، پایه برای همه فازهای بعدی
### مسئله
الان `run_deep_scan` فقط ۳۵ فایل deep-read + import graph می‌بیند. backend endpoints، UI elements، DB schema، env vars، configs، **notifications، inspector sessions، UI options** هرگز inventory نمی‌شوند.
### تغییرات
**۱-A. Structural Inventory (۱۲ لایه):**
ماژول جدید: `backend/app/services/scan_v5/comprehensive_inventory.py`
| # | لایه | چه چیزی جمع می‌شود | روش |
|---|---|---|---|
| 1 | Files | همه فایل‌های git-tracked | `git ls-files` |
| 2 | Backend endpoints | همه `@router.{get,post,…}` + WebSocket + background tasks | AST parse |
| 3 | UI elements | همه `<button>`, `<form>`, `<input>`, `<Select>`, `<Link>`, modal triggers, dropdown items | parse `.tsx` |
| 4 | DB schema | همه dataclass + Column + migrations | inspect |
| 5 | Env vars | همه `os.environ.get`, `os.getenv`, `process.env.X` | regex |
| 6 | Config files | همه `.json`, `.yaml`, `.toml`, `.env*` | glob |
| 7 | Dependencies | `requirements.txt`, `package.json` | parse |
| 8 | Scripts | همه `.sh`, `pyproject::scripts`, `package.json::scripts` | parse |
| 9 | Cron/scheduled | همه `apscheduler`, `BackgroundTasks`, `asyncio.create_task` | regex |
| 10 | Routes | همه frontend `app/**/page.tsx` + backend route | walk |
| 11 | **Notification calls (R12)** | همه `notify_event(...)`, `send_telegram(...)`, `bot.send_message(...)` + event_type + silent flag + caption template | regex/AST |
| 12 | **UI options/settings (R8)** | همه checkbox/slider/dropdown در UI + field name در WatchedProject + default value | parse + cross-ref |
**۱-B. Purpose Extraction (R10):**
ماژول جدید: `backend/app/services/scan_v5/purpose_extractor.py`
برای **هر file/module/feature/option** که در inventory هست:

```python
purpose_inventory[item_id] = {
    "stated_purpose": "چه کاری *قرار است* بکند",
    "evidence_sources": ["comments", "docstrings", "tests", "raw_idea", "task_history", "commit_messages"],
    "expected_inputs": [...],
    "expected_outputs": [...],
    "interacting_with": [...],          # سایر componentهای همکار
    "creation_context": {                # R8 — کاربر فراموش کرده چی هست
        "first_seen_commit": "...",
        "first_seen_date": "...",
        "originating_task_id": "...",    # کدام task این را ساخت
        "originating_raw_idea": "...",   # متن خام درخواست
    },
    "current_usage": "...",              # آیا هنوز استفاده می‌شود؟ کجا؟
}
```


**منابع AI برای purpose:**
- محتوای فایل + docstrings + JSDoc
- test files مرتبط
- `WatchedProject.user_notes` (raw_idea اصلی پروژه)
- task history (task هایی که این item را modify کرده‌اند)
- commit messages روی این path
**۱-C. Storage:**
`WatchedProject` فیلدهای جدید:

```python
last_scan_inventory: Optional[Dict[str, Any]] = None
last_scan_purpose_map: Optional[Dict[str, Dict]] = None
last_scan_at_v5: Optional[str] = None  # timestamp scan جدید
```


### Acceptance Criteria فاز ۱
- `inventory.backend_endpoints` ≥ ۵۰
- `inventory.ui_elements` ≥ ۳۰
- `inventory.notification_calls` ≥ ۱۰
- `inventory.ui_options` همه‌ی checkbox/slider/dropdown ها را شامل شود
- `purpose_map` برای ≥ ۸۰% فایل‌های مهم
- برای هر UI option، `creation_context` نشان دهد از کدام task ساخته شد
---
## 🅱️ فاز ۲ — Stale Detection + Feature Inventory Panel
> **مهم‌ترین فاز برای R8 — حل مشکل «گزینه‌های قدیمی که نمی‌دانم چی هست»**
### مسئله (R8 — تأکید سه‌باره)
> «خیلی‌هاش قدیمیه و کار نمی‌کنه و خیلی‌هاش نیاز داره بدونم چی بوده، برای چیه و هر سری باید بهش سر بزنم»
### تغییرات
**۲-A. Structural Stale (۸ نوع):**
ماژول جدید: `backend/app/services/scan_v5/stale_detector.py`
| نوع | شناسایی |
|---|---|
| Dead UI buttons | onClick handler ندارد / empty / به endpoint 404 می‌رود |
| Dead frontend routes | در nav menu نیست و در هیچ Link/router.push نیست |
| Dead backend endpoints | در هیچ frontend fetch نیست + در Render logs ۳۰ روز اخیر صدا نشد |
| Unused functions/classes | reverse import = 0 و entry point نیست |
| Unused dataclass fields | در هیچ‌جا read/write نمی‌شود |
| Unused env vars | تعریف شده ولی هیچ `os.environ.get` |
| Orphan files | reverse import = 0 |
| Stale dependencies | در requirements/package.json هست ولی import نمی‌شود |
**۲-B. Semantic Stale (R10 — ۵ نوع):**
| نوع | شناسایی |
|---|---|
| Purpose-mismatched | `stated_purpose` با `actual_behavior` نمی‌خواند |
| Hidden purpose (R8) | کاربر نمی‌داند چی هست — هیچ doc، نام مبهم، creation_context قدیمی |
| Inconsistent با تغییرات اخیر | کد فرض می‌کند رفتار قدیمی X، ولی X تغییر کرده (نیاز به فاز ۳) |
| Outdated business assumption | threshold/config که با realities فعلی نمی‌خواند |
| Forgotten by user (R8 — جدید) | UI option/setting که کاربر هر بار باید بپرسد چی هست |
**۲-C. AI-Generated Documentation برای هر option (R8):**
برای **هر** UI option/setting/feature/button که در inventory.ui_options یا inventory.ui_elements هست:

```python
ai_documentation[option_id] = {
    "name": "...",
    "what_it_does": "AI explanation — این گزینه دقیقاً چه کاری می‌کند",
    "when_added": "تاریخ + commit",
    "originating_idea": "متن خام درخواست اولیه",
    "current_status": "active | possibly_stale | broken | unknown",
    "dependencies": ["..."],         # forward
    "dependents": ["..."],           # reverse
    "recommended_action": "keep | remove | refactor | document"
}
```


**۲-D. Feature Inventory Panel در UI:**
`frontend/src/app/oversight/page.tsx` — اضافه شدن panel جدید:

```
🗺 Feature Inventory
├─ 🔧 Settings (12)
│   ├─ ✓ verify_mode (active — Phase 4, از task #abc1234)
│   ├─ ✓ dedup_threshold (active — Phase 3)
│   ├─ ⚠️ confirmation_streak_required (possibly_stale — ۹۰ روز unused)
│   └─ ...
├─ 🎛 UI Buttons (45)
├─ 🌐 Backend Endpoints (78)
└─ ⚙️ Env Vars (23)
```


برای هر مدخل: hover → AI explanation کامل.
**۲-E. Task Generation:**
برای هر stale item:
- **cleanup** task (structural) یا **audit** task (semantic) یا **document** task (hidden purpose)
- AC رفتار-محور: «یا حذف شود، یا با docstring/comment توضیح داده شود چرا نگه داشته، یا ارتقا یابد»
- priority بر اساس impact
### Acceptance Criteria فاز ۲
- روی این پروژه ≥ ۵ structural stale + ≥ ۳ semantic stale + ≥ ۸ hidden-purpose options
- Feature Inventory Panel با ≥ ۲۰ مدخل
- هر stale → task با explanation کامل (نه فقط «این unused است»)
- روی project trade مثال کاربر (R11)، scan تشخیص دهد گزینه‌هایی که برای trading فعلاً ضرر می‌دهند
---
## 🅲️ فاز ۳ — Delta Detection + Bidirectional Dependency + Logical Impact
> پوشش **R7** — کاربر صریحاً bidirectional خواست
### مسئله (R7)
> «چه وابستگی‌هایی داشته **به چه چیزهایی وابسته بوده** و **چه چیزهایی بهش وابسته بودن**»
این **دو طرفه** است:
- forward: این فایل به چه چیزی وابسته است
- reverse: چه چیزهایی به این فایل وابسته‌اند
### تغییرات
**۳-A. ذخیره prev state:**
`WatchedProject`:

```python
prev_scan_state: Optional[Dict[str, Any]] = None
# {file_path → {sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash}}
```


**۳-B. compute delta — ۶ نوع (R7: «تغییر کرده یا اضافه شده یا کم شده یا ویرایش شده»):**
| نوع | تشخیص |
|---|---|
| `add` | در current، نه در prev |
| `remove` | در prev، نه در current |
| `modify` | sha متفاوت |
| `rename` | sha مشابه، path متفاوت |
| `move` | content مشابه، path متفاوت |
| `signature-change` | نام تابع ثابت، parameters یا return-type تغییر |
**۳-C. Bidirectional Dependency (R7 صریح):**
ماژول جدید: `backend/app/services/scan_v5/dependency_analyzer.py`
برای هر changed file:

```python
{
    "dependencies": [...],   # forward — file → چه چیزی import می‌کند
    "dependents": [...],     # reverse — چه چیزهایی → این file import می‌کنند
    "logical_dependencies": [...],   # forward منطقی — کدام components روی این تکیه دارند
    "logical_dependents": [...],     # reverse منطقی — این از کدام components انتظار دارد
}
```


تمایز بین **import-based** و **logical**:
- import: AST/grep
- logical: AI روی purpose_inventory تشخیص می‌دهد (مثلاً «این تابع threshold X را می‌خواند، اگر X تغییر کرد رفتار تغییر می‌کند»)
**۳-D. Logical Impact Analysis (R10):**
AI روی هر تغییر + dependents تحلیل می‌کند:
- آیا تغییر این فایل، **منطق** dependents را می‌شکند؟
- مثال: تغییر `threshold=0.65` → `threshold=0.8` → چه componentهای dependent behavior متفاوت نشان می‌دهند؟
- مثال: تغییر فرمت output `parse_signal()` → چه callerها به update نیاز دارند؟
- مثال: حذف یک env var → چه قسمت‌هایی crash می‌کنند؟
**۳-E. Task Generation:**
برای هر changed file + dependent در خطر:
- task با badge `🔄 وابسته به تغییر`
- AC رفتار-محور: «بعد از این تغییر، dependents X و Y باید همچنان behavior Z تولید کنند»
- اگر logical impact پیچیده است → priority بالاتر + reference به scan inspector session
### Acceptance Criteria فاز ۳
- بعد از دو scan متوالی، delta با ۶ نوع تشخیص داده شود
- اگر signature تغییر کرد و ۳ caller دارد، ≥ ۱ task برای بررسی caller ها
- logical impact detection: اگر threshold تغییر کرد، AI تحلیل کند نه فقط alert سینتکسی
- bidirectional dependency: هم dependencies (forward) هم dependents (reverse) برای هر changed item
---
## 🅳 فاز ۴ — Runtime Discovery + Outcome + Inspector Session
> پوشش **R14** — Inspector tab integration — این مهم‌ترین آپشن از قلم افتاده
### مسئله (R14 صریح)
کاربر گفت: «در بررسی‌های عمیق از تب بازرس ویژه هم کمک می‌گیره و **اسکرین‌ها** رو می‌گیره و در تلگرام **همراه با گزارش** بفرسته و **چت‌ها** رو در یه session ثبت کنه و **بایگانی** کنه؟»
این **اصلاً در پرامپت‌های قبلی نبود**. فعلاً Inspector فقط در verify (Phase 4) استفاده می‌شد.
### تغییرات
**۴-A. Runtime Discovery (با ایده از Phase 4):**
ماژول جدید: `backend/app/services/scan_v5/runtime_discovery.py`
| منبع | استفاده |
|---|---|
| `navigation_helper::extract_nav_links_from_page` | nav links واقعی frontend |
| Playwright on each route | screenshot + status code → 404 detection |
| `backend_log_probe::_fetch_relevant_logs` 30-day | endpoints واقعاً called شده |
| `vision_helper::analyze_screenshot` | کشف feature های UI |
| `code_aware_verifier::_fetch_recent_commits_with_diff` | recent commits context |
خروجی: `runtime_state` شامل `routes_alive[]`, `routes_404[]`, `endpoints_called_recently[]`, `endpoints_never_called[]`, `ui_features_visible[]`, `recent_commits[]`.
**۴-B. Outcome Data Collection:**
برای هر پروژه، scan تلاش کند outcome data بیابد:
| نوع پروژه | outcome data |
|---|---|
| Trading | trade logs, P&L history |
| AI/Chat | conversation outcomes |
| Web service | error rates, latency from logs |
| Scheduling | task completion rates |
| Notification | delivery + open rates |
روش‌ها: Render logs filtered + DB tables outcome-naming + file artifacts.
**۴-C. Scan Inspector Session (R14 — حیاتی):**
ماژول جدید: `backend/app/services/scan_v5/scan_inspector_session.py`
**هر scan یک inspector session باز می‌کند** (مشابه verify در Phase 4):

```python
session = create_scan_inspector_session(
    watched_id=...,
    scan_id=...,
    project_name=...,
)
```


**در طول scan:**
- همه AI calls (purpose extraction، stale detection، logic audit، etc.) → پیام در session با role="ai", content=request+response
- همه Playwright actions → پیام با role="action", screenshot=path
- همه screenshot ها → ذخیره روی disk + reference در session
- runtime probe outputs → پیام با role="probe"
**در پایان scan:**
- session archived
- screenshots → آرشیو شده در Telegram (مثل bundle Phase 4)
- bundle PDF تولید می‌شود شامل:
  - findings + tasks ایجاد شده
  - delta summary
  - logic audit findings
  - inventory summary
  - تمام screenshots
- Telegram message + PDF attachment
- در UI، scan session در inspector tab با badge `🔍 Scan Session` (متمایز از `🔬 Verify Session`)
**۴-D. اضافه شدن tab "Scan Sessions" در Inspector UI:**
`frontend/src/app/projects/[id]/page.tsx` (یا هر جا که inspector tab هست):
- علاوه بر لیست verify sessions، scan sessions هم نمایش داده شوند
- کاربر بتواند هر scan session را باز کند و تمام مکالمات + screenshots آن را ببیند
- archive option
### Acceptance Criteria فاز ۴
- بعد از هر scan، یک inspector session با ≥ ۱۰ پیام (AI calls + actions + probes) ساخته شود
- ≥ ۵ screenshot ذخیره شود
- Telegram message + bundle PDF با همه‌ی screenshots و findings ارسال شود
- در Inspector tab، session آرشیو شده دیده شود با badge `🔍 Scan`
- اگر runtime discovery فعال است، روی هر route یک screenshot + Vision analysis
---
## 🅴 فاز ۵ — Logical Audit (Coherence + Anti-pattern + Outcome)
> پوشش **R10, R11** — مهم‌ترین فاز معنایی
### مسئله (R10, R11)
> «یه پروژه دارم که هوشمند ترید کنه ولی بدتر از یه آدم معمولی ترید می‌کنه — باگ منطقی در هماهنگی بین AI و داده‌ها»
scan نباید **فقط خطاها** را ببیند، بلکه **منطق و هدف** را هم.
### تغییرات
**۵-A. Pipeline Coherence Detection:**
ماژول جدید: `backend/app/services/scan_v5/coherence_analyzer.py`
شناسایی pipelines (chains از componentهای همکار) با استفاده از `purpose_inventory[X].interacting_with`.
برای هر chain، AI بررسی coherence:
| الگو | چه بررسی شود |
|---|---|
| **Data pipeline** | schema هر مرحله، handling empty result |
| **AI/LLM chain** | prompt format ↔ model ↔ parser سازگار؟ validation؟ |
| **Business logic (R11 مثال trade)** | signal ↔ risk model، position ↔ account size، stop-loss ↔ timeframe |
| **Auth/Permission** | همه‌ی mutation از permission گذر می‌کند؟ |
| **Feedback loop** | outcome به config/model برمی‌گردد؟ |
| **Notification chain (R12)** | event → notify_event → caption → silent decision → delivery — همه consistent؟ |
**۵-B. Logical Anti-pattern Detection:**
ماژول جدید: `backend/app/services/scan_v5/anti_pattern_detector.py`
AI روی purpose_inventory + کد، این الگوها را پیدا می‌کند:
| Anti-pattern | مثال |
|---|---|
| داده بی‌مصرف | API call، DB write، ولی هیچ read |
| AI بدون validation | response parse می‌شود ولی validity چک نمی‌شود |
| Magic threshold | `> 0.65:` بدون توضیح |
| Conflicting defaults | یک field default متفاوت در جاهای مختلف |
| Silent failure در crucial path | `except: pass` در business logic |
| Broken feedback loop (R11) | outcome لاگ ولی به model نمی‌رسد |
| Stale assumption | کد فرض می‌کند رفتار سرویس X خاصه، X تغییر کرد |
| Over/under-engineering | برای ساده ۵ لایه، برای پیچیده hardcode |
| Conditional inconsistency | conditions با تغییرات اخیر inconsistent |
| Threshold-Outcome mismatch (R11) | parameters نتایج مطلوب تولید نمی‌کنند |
| Notification mismatch (R12) | event critical ولی silent=True، یا opposite |
**۵-C. Hidden Requirements Discovery (R8):**
برای هر feature که کاربر فراموش کرده «چی هست برای چیه»:
- AI روی `creation_context` (از فاز ۱) + task history + commit messages تحلیل
- استخراج: «این feature چه وقت، چرا، با چه هدفی اضافه شد؟»
- نتیجه:
  - هدف منسوخ → task `cleanup`
  - هدف معتبر، پیاده‌سازی ضعیف → task `refactor`
  - هدف معتبر، پیاده‌سازی خوب، docs نیست → task `document`
**۵-D. Outcome-based Effectiveness Audit (R11):**
اگر outcome data دارد (از فاز ۴):
- AI تحلیل می‌کند آیا outcome با `stated_purpose` می‌خواند
- مثال R11: trade — اگر purpose="earn profit" و win-rate=30% → effectiveness LOW
- اگر LOW → task `logic_audit` با priority بالا
**۵-E. Task Generation:**
نوع جدید task: `logic_audit`
- AC outcome-oriented:
  - ❌ «این کد را fix کن»
  - ✅ «بعد از این تغییر، win-rate باید ≥40% یا parameters محافظه‌کارانه‌تر شود»
- AI explanation کامل: چرا اشتباه + چه راه‌حل + چه impact
### Acceptance Criteria فاز ۵
- روی پروژه فعلی ≥ ۳ logic issue + ≥ ۱ pipeline coherence + ≥ ۲ anti-pattern logical
- روی پروژه trade فرضی (R11)، scan باگ منطقی هماهنگی AI-data شناسایی کند
- task `logic_audit` با AC outcome-oriented + AI explanation کامل
---
## 🅵 فاز ۶ — Notification System Audit (R12)
> پوشش **R6, R12** — صریحاً audit notification ها
### مسئله (R12)
> «در پرامپت برای پیام‌رسانی تلگرام هم جایی در نظر گرفتی؟ در بررسی‌ها نوع اطلاع‌رسانیش هم بررسی بشه و بهینه بشه»
### تغییرات
**۶-A. Notification Inventory (از فاز ۱ — لایه ۱۱):**
برای هر `notify_event(...)` call در کد:

```python
notification_inventory[call_id] = {
    "file_path": "...",
    "line": ...,
    "event_type": "...",          # "task_created" | "verify_done" | ...
    "caption_template": "...",
    "silent_default": True | False | None,
    "attachments": [...],
    "trigger_condition": "...",   # کد منطق در کجا fire می‌شود
    "frequency_estimate": "...",  # احتمال در روز
}
```


**۶-B. Notification Coherence Audit (R12):**
AI روی notification_inventory:
| سوال | چه چیزی audit شود |
|---|---|
| caption کامل است؟ | همه‌ی فیلدهای مهم در caption هستند؟ (title, intent, link, attachments) |
| silent/sound مناسب است؟ | event critical → sound. event routine → silent |
| attachments صحیح؟ | task creation → prompt.md، verify done → bundle.pdf، scan done → scan-bundle.pdf |
| timing مناسب؟ | spam جلوگیری شده؟ batching هست؟ |
| stale notifications؟ | event type که دیگر کد آن وجود ندارد |
| missing notifications؟ | event critical که notification ندارد |
| **scan-specific (R12)**: | scan completion notification با همه‌ی مدارک ضروری: findings, tasks created, delta, logic audit results, inspector session reference |
**۶-C. Notification Templates Suggestions:**
برای هر notification که audit آن مشکل دارد → task `notification_audit`:
مثال task:

```yaml
title: "ارتقای caption notification scan_completed"
type: notification_audit
priority: medium
raw_idea: |
  notification scan_completed فعلاً فقط count tasks ایجاد شده را می‌دهد.
  باید شامل: delta summary + logic audit findings + inspector session link
  + attachment با PDF کامل (مشابه verify bundle).
behavior_observable: |
  بعد از این تغییر، notification scan_completed باید شامل:
  - title پروژه
  - تعداد tasks جدید
  - delta count (add/remove/modify)
  - logic audit count
  - link به scan inspector session
  - PDF attachment با همه screenshots و findings
acceptance_signal: |
  بعد از یک scan تست، Telegram message + PDF received با همه فیلدها
```


**۶-D. Audit existing notification flows:**
- `notification_service.py` — همه `notify_event` ها
- `oversight_telegram_compose.py` — caption builders
- `oversight_mega_bundle.py` — bundle PDFs
- بررسی silent default برای auto-tasks (R6)
### Acceptance Criteria فاز ۶
- audit notification ها: ≥ ۲ مورد ارتقا قابل پیشنهاد
- task `notification_audit` ایجاد شود برای هر مورد
- caption template جدید برای scan_completed تعریف شود
- silent default برای auto-task و scan notifications به `True` تنظیم شود
- field `WatchedProject.auto_task_notify_sound: bool = False`
- field `WatchedProject.scan_notify_sound: bool = False`
---
## 🅶 فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)
> پوشش **R5, R9, R13** — برای **manual + auto** هر دو
### مسئله (R9 صریح)
> «در تولید ایده خام به پرامپت، پرامپت در برخی قسمت‌ها دقیق و واضح تولید نمیشه... باید هوشمندتر بشه خود متن پرامپت و چک‌لیستی که ازش تولید میشه»
### مسئله (R13 صریح)
> «این بهبود پرامپت‌نویسی تسک‌ها آیا فقط برای تسک‌های سیستمی یا تسک‌های دستی هم شامل میشه؟»
**جواب: هر دو.**
### تغییرات
**۷-A. ساختار غنی AC (هم manual، هم auto):**
برای **manual** path در `oversight_service.py:idea_to_prompt` (~3454):
برای **auto** path در `oversight_service.py:task creation from scan` (~4700-4740):
برای **scan-generated** path در `oversight_strong_prompt.py:build_strong_prompt`:
هر AC ساختار غنی:

```python
{
    "text": "...",                          # توضیح اصلی (می‌تواند نام بدهد)
    "behavior": "...",                      # رفتار قابل مشاهده — چه چیزی observable است
    "acceptance_signal": "...",             # سؤال قابل-verify
    "business_intent": "...",               # چرا این لازم است
    "alternative_implementations": [...],   # نام‌های جایگزین قابل قبول (R9 — جلوگیری از نام-محوری)
    "non_goals": "...",                     # چه چیزی این AC نیست
    "false_positive_guard": "...",          # چه شواهد ضعیفی نشانه done نیست (R9)
}
```


**۷-B. ساختار غنی task_step (در `_ai_plan_steps_from_idea`):**
برای manual و auto (R13):

```python
{
    "title": "...",
    "scope": "...",
    "behavior_observable": "...",       # خروجی observable
    "verification_hint": "...",         # کجا verify بیابد
    "business_intent": "...",           # چرا این مرحله
    "non_goals": "...",
}
```


**۷-C. Smart Checklist Mode (R5):**
> «حالت هوشمند که برای تولید چک‌لیست یا عدم تولیدش حسب نیاز هست»
`WatchedProject.auto_task_checklist_mode: Literal["auto","always","never"] = "auto"`
- `auto`: AI تصمیم می‌گیرد بر اساس پیچیدگی (≥3 stage → checklist، single-action → skip)
- `always`: همیشه چک‌لیست
- `never`: هرگز
این برای **هم manual و هم auto** کار می‌کند.
**۷-D. Update prompt templates:**
در `oversight_strong_prompt.py`:
- اضافه شدن section "🎯 معیار رفتاری + business intent + alternative implementations"
- AI صریح راهنمایی شود: AC نام-محور بد است، AC رفتار-محور خوب
**۷-E. جلوگیری از false-positive (R9):**
> «جوری هم نشه که سیستم کاری که بد انجام شده... در verify تیک بزنه که کامل شده»
دستورالعمل به AI:
- اگر AC vague → split به sub-behaviors concrete
- هرگز AC بدون `acceptance_signal` نسازد
- `false_positive_guard` فیلد: چه شواهد ضعیفی نباید سبب done شود
- مثال: «اگر فقط فایل با نام وجود دارد، done نیست — باید رفتار X هم باشد»
**۷-F. Integration با فازهای قبلی:**
پرامپت تولید‌شده استفاده کند از:
- `purpose_inventory` (فاز ۱)
- `runtime_state` (فاز ۴)
- `logic_audit_findings` (فاز ۵)
- `notification_audit` (فاز ۶)
### Acceptance Criteria فاز ۷
- **manual** path: پرامپت‌های جدید برای ۳ ایده‌ی نمونه شامل `behavior` + `acceptance_signal` + `business_intent` + `alternative_implementations` + `false_positive_guard`
- **auto** path: همان ساختار برای task های scan-generated
- چک‌لیست‌ها شامل `behavior_observable` در هر step
- mode `auto` در `_ai_plan_steps_from_idea` کار می‌کند برای هر دو
- verify روی same tasks: false-negative ≤ ۲۰%، false-positive ≤ ۵%
- backward compat: AC های قدیمی (فقط text) همچنان کار می‌کنند
---
## 🅷 فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration
> پوشش **R5, R6** — تسک‌های scan باید مثل manual باشند
### مسئله (R5, R6)
- تسک‌های auto-scan الان `prompt + AC` دارند ولی `task_steps` ندارند
- Telegram notification برای آن‌ها audit نشده
- کاربر می‌خواهد silent default
### تغییرات
**۸-A. task_steps برای auto-tasks:**
در `oversight_service.py:4700-4740`:
- بعد از `build_strong_prompt`، اگر `auto_task_checklist_mode != "never"`:
  - if `mode == "always"` → همیشه call `_ai_plan_steps_from_idea`
  - if `mode == "auto"` → AI تصمیم می‌گیرد بر اساس پیچیدگی
**۸-B. Telegram Notification Template (R6):**
`notification_service.py`:

```python
# Caption template برای auto-scan task
{
    "🤖 تسک جدید از scan خودکار",
    "📌 {title}",
    "🎯 {business_intent[:200]}",
    "📋 چک‌لیست: {N step}" if has_steps else None,
    "🧠 Logic concerns: {logic_audit_count}" if has_logic_issues else None,
    "🔄 وابسته به تغییر: {dependent_changes}" if delta_dependent else None,
    "📊 Outcome impact: {outcome_score}" if outcome_data else None,
    "🔗 [لینک کارت]",
    "🔍 [Inspector session]",
}
# Attachments:
- prompt_full.md (full task prompt)
- scan_inspector_session_link
```


**۸-C. Silent default + UI control:**
`WatchedProject` fields:

```python
auto_task_notify_sound: bool = False     # silent for auto-tasks
scan_notify_sound: bool = False           # silent for scan completion
```


در UI: checkbox `🔔 صدای notification برای تسک‌های auto-scan`.
**۸-D. Scan-completion notification:**
علاوه بر notification هر task، یک scan-completion notification:

```
✅ scan تکمیل شد — {project_name}
📊 خلاصه:
- {N} task جدید ایجاد شد
- {N} delta change شناسایی
- {N} stale item
- {N} logic issue
- {N} notification audit
📎 Bundle PDF (با همه screenshots و findings)
🔍 Inspector session: [link]
```


### Acceptance Criteria فاز ۸
- بعد از scan: همه auto-tasks در UI چک‌لیست دارند (اگر mode=auto و پیچیده‌اند)
- caption تلگرام شامل همه فیلدها
- silent default = true
- scan_completed notification با Bundle PDF + Inspector session link
- regression: تسک‌های دستی رفتار قبلی را حفظ کنند
---
## 🅸 فاز ۹ — UI Redesign (R2, R8)
> پوشش **R2** — به‌روزرسانی گزینه‌ها
### مسئله (R2)
> «گزینه‌هاش هم به روز رسانی بشن»
### تغییرات
**۹-A. بازنگری scan_depth modes:**
از (فعلی):

```
quick (3 pass) | standard (6 pass) | deep (12 pass، پیش‌فرض) | thorough (12 + health + roadmap)
```


به:

```
⚡ quick (5 pass) — frontend + backend + security + delta + stale
⚖️ balanced (8 pass — پیش‌فرض جدید) — quick + dependency + completeness + runtime
🔬 deep (12 pass) — همه + impact analysis
🧠 ultra (12 pass + logic audit + outcome + notification audit + inspector session)
```


**۹-B. بازنگری criteria_weights:**
به‌جای ۶ slider:
- preset selector: "general", "security-first", "tests-first", "feature-completeness", "logic-quality"
- sliders در `<details>` (advanced)
**۹-C. بازنگری Smart Task Lifecycle:**
- بررسی هر گزینه: کار می‌کند؟
- label با وضعیت فعلی
**۹-D. گزینه‌های جدید Phase 5:**
`WatchedProject` فیلدهای جدید (همه با default sensible):

```python
# Coverage
inventory_layers: List[str] = ["all"]    # یا subset
# Intelligence
stale_detection_enabled: bool = True
delta_analysis_enabled: bool = True
runtime_discovery_enabled: bool = True
outcome_data_enabled: bool = True
logic_audit_enabled: bool = True
notification_audit_enabled: bool = True
inspector_session_enabled: bool = True   # R14
# Lifecycle
auto_task_checklist_mode: str = "auto"   # R5
cleanup_tasks_enabled: bool = True
# Notifications
auto_task_notify_sound: bool = False     # R6
scan_notify_sound: bool = False          # R6
```

**۹-E. بازطراحی Layout — ۴ tabs (به‌جای ۳):**
| Tab | محتوا |
|---|---|
| **🔍 Coverage** | scan_depth + inventory_layers + criteria preset + auto_models |
| **🧠 Intelligence** | stale + delta + runtime + outcome + logic_audit + smart-prompt + inspector_session |
| **🔁 Lifecycle** | dedup + auto-regenerate + checklist mode + cleanup |
| **🔔 Notifications** | auto_task_sound + scan_sound + notification_audit + custom templates |
**۹-F. AI explanation برای هر گزینه (R8):**
هر گزینه دارای help icon ⓘ + AI-generated description (از فاز ۲):
- این گزینه دقیقاً چه می‌کند
- کِی اضافه شد
- وضعیت فعلی (active / possibly stale / unknown)
**۹-G. Feature Inventory Panel (R8):**
panel جدید در UI با لیست همه options + AI explanation (از فاز ۲).
### Acceptance Criteria فاز ۹
- در UI، ۴ tab وجود دارد
- mode `balanced` پیش‌فرض جدید
- mode `ultra` در دسترس
- backward compat: scan_depth قدیمی همچنان کار کند
- هر گزینه دارای tooltip + AI explanation
- Feature Inventory Panel functional
---
## 🅹 فاز ۱۰ — Meta-validation
> خود این پرامپت قابل verify باشد
### مسئله
کاربر می‌خواهد این پرامپت به task تبدیل شود و توسط verify Phase 4 سنجیده شود.
### تغییرات
**۱۰-A. این پرامپت به task تبدیل:**
- ایده‌ی خام = این متن
- AC ها = AC های هر فاز ۱-۹
- task_steps = ۱۰ فاز
**۱۰-B. AC قابل-verify دقیق:**
هر AC در هر فاز measurable نوشته شده (مثلاً «≥ ۵ stale item کشف شود»).
**۱۰-C. Iteration loop:**
- پیاده‌سازی → verify deep (Phase 4) → نتیجه
- اگر `done < 100%` → iteration بعدی
- اگر `done = 100%` → فاز بعدی
- log در `phase5_meta_validation.md`
**۱۰-D. شناسایی verify bugs:**
- اگر کار واقعاً انجام شد ولی verify گفت not_done → باگ verify
- اگر کار نشد ولی verify گفت done → باگ verify (مهم‌تر، false-positive)
- log همه‌ی این موارد
### Acceptance Criteria فاز ۱۰
- پرامپت نهایی شامل ۱۰ task_step
- هر step دارای `behavior_observable` + `verification_hint`
- بعد از پیاده‌سازی همه فازها، verify deep این task را ≥ ۱۰/۱۰ done گزارش دهد
- log باگ‌های verify identified
---
## 🗂️ نقشه آدرس‌ها
| فاز | فایل | نوع |
|---|---|---|
| 1 | `backend/app/services/scan_v5/comprehensive_inventory.py` | new |
| 1 | `backend/app/services/scan_v5/purpose_extractor.py` | new |
| 1 | `backend/app/services/oversight_service.py:161` | + 3 fields |
| 2 | `backend/app/services/scan_v5/stale_detector.py` | new |
| 2 | `backend/app/services/scan_v5/feature_documenter.py` | new |
| 2 | `frontend/src/app/oversight/page.tsx` | + Feature Inventory panel |
| 3 | `backend/app/services/scan_v5/delta_analyzer.py` | new |
| 3 | `backend/app/services/scan_v5/dependency_analyzer.py` | new |
| 3 | `backend/app/services/oversight_service.py:161` | + `prev_scan_state` |
| 4 | `backend/app/services/scan_v5/runtime_discovery.py` | new |
| 4 | `backend/app/services/scan_v5/outcome_analyzer.py` | new |
| 4 | `backend/app/services/scan_v5/scan_inspector_session.py` | new |
| 4 | `frontend/src/app/projects/[id]/page.tsx` (Inspector tab) | + Scan Sessions section |
| 5 | `backend/app/services/scan_v5/coherence_analyzer.py` | new |
| 5 | `backend/app/services/scan_v5/anti_pattern_detector.py` | new |
| 5 | `backend/app/services/oversight_service.py` | + task type "logic_audit" |
| 6 | `backend/app/services/scan_v5/notification_auditor.py` | new |
| 6 | `backend/app/services/notification_service.py` | audit |
| 6 | `backend/app/services/oversight_telegram_compose.py` | + scan template |
| 7 | `backend/app/services/oversight_strong_prompt.py` | + behavior + business_intent + false_positive_guard |
| 7 | `backend/app/services/oversight_service.py:3454` (idea_to_prompt) | structured AC |
| 7 | `backend/app/services/oversight_service.py:2673` (_ai_plan_steps_from_idea) | structured steps |
| 7 | `backend/app/services/oversight_service.py:4700-4740` (auto-task creation) | apply same to auto |
| 8 | `backend/app/services/notification_service.py` | new templates |
| 8 | `backend/app/services/oversight_mega_bundle.py` | + scan-bundle PDF |
| 9 | `frontend/src/app/oversight/page.tsx` | 4 tabs redesign |
| 9 | `backend/app/services/oversight_service.py:161` | + ۱۰ field جدید |
| 10 | meta — هر فاز AC مشخص | — |
---
## 🎯 ترتیب اجرا
**Round 1 — پایه:**
1. فاز ۱ — Comprehensive Inventory + Purpose
**Round 2 — تحلیل ساختاری:**
2. فاز ۲ — Stale Detection + Feature Inventory Panel
3. فاز ۳ — Delta + Bidirectional Dependency
**Round 3 — تحلیل دینامیک:**
4. فاز ۴ — Runtime + Outcome + Inspector Session
5. فاز ۵ — Logical Audit
6. فاز ۶ — Notification Audit
**Round 4 — تولید + UI:**
7. فاز ۷ — Smart Prompt (manual + auto)
8. فاز ۸ — Auto-tasks Like Manual + Telegram
9. فاز ۹ — UI Redesign
**Round 5 — نهایی:**
10. فاز ۱۰ — Meta-validation
هر Round با runtime test قبل از push. در پایان: یک scan کامل روی این پروژه برای meta-validation.
--------------------------
در گزارش نهایی باید تمام اجزایی که بررسی کرده به صورت ریز در گزارش بیاد .. حالا بخش تسک درست کردن و پرامپت و چک لیست مطابقش درست کردن که تو گزارش میاد جدا
یه گزارش جدا باید تو همون متنی که ارسال میکنه در تلگرام هم پیوستش باشه که تمام موارد رو که بررسی کرده مشروح و با جزئیات بنویسه 
اینها که زیر نوشتم و در تنظیمات هر کارت پروژه قرارداده شده باید هر کدوم توضیحات مفصلی داشته باشه و هیچ کار ناقصی پذیرفته نیست :

🗑 stale + forgotten options

🔄 delta + bidirectional dep

🌐 runtime discovery

📊 outcome data

🧠 logic audit

🔔 notification audit

🔍 inspector session

🗑 cleanup tasks
-----------------------------
🔒 امنیت:


🛠 کیفیت:


🧪 تست:


✅ کامل بودن:
------------------------------
# 🔬 Bug C6 — Verify v6: Deep Code-Content Analysis + Iterative Refinement (v2 نهایی)

## 🎯 هدف اصلی

(بدون تغییر از نسخهٔ قبل — حفظ همان framing)

verify فعلی روی ~۴۰٪ تسک‌ها (آن‌هایی که backend یا multi-step هستند) false negative می‌دهد. این bug، verify را به سطح "همان‌چه یک developer واقعی با grep دستی پیدا می‌کند" می‌رساند. پایهٔ ۵ فاز قبلی **حفظ می‌شود**؛ فقط لایه‌های زیرین قوی می‌شوند.

این bug **خود قابل verify** است (meta-test) — یعنی verify v6 وقتی روی این bug اجرا شد، باید همهٔ AC هایش را به‌درستی done ببیند.

---

## 🔍 ۶ گپ بنیادی + ۲ بهبود اضافه (در v2)

### گپ ۱ — حافظهٔ تکه‌تکه vs کامل

#### وضعیت فعلی
verify فقط AC text + commit diff + screenshot + repo tree را دارد.

#### راه‌حل
ماژول جدید: `backend/app/services/verify_runtime/context_builder.py`

ساختار `VerifyContext` dataclass:
```python
@dataclass
class VerifyContext:
    task: OversightTask                       # ref فقط
    watched: WatchedProject                   # ref فقط
    raw_idea_full: str                        # cap 50KB
    prompt_full: str                          # cap 100KB
    task_steps_full: List[Dict]               # همه (no cap چون داخل تسک)
    prompt_history: List[Dict]                # آخرین ۳ نسخه
    verify_history: List[Dict]                # آخرین ۵ گزارش
    consolidation_meta: Optional[Dict]        # اگر super-task
    merged_source_tasks: List[Dict]           # cap 30 (top by priority)
    scan_metadata: Optional[Dict]             # last_scan_metadata
    repo_tree: List[str]                      # paths only، cap 5000
    commits_recent: List[Dict]                # cap 50 commits
    # کش‌های in-memory per-verify-run
    file_content_cache: Dict[str, str] = field(default_factory=dict)
    file_grep_cache: Dict[Tuple[str, str], List[Dict]] = field(default_factory=dict)
    # observability
    trace: List[Dict] = field(default_factory=list)  # هر تصمیم append می‌شود
    config: "VerifyConfig" = ...               # ↓ بخش config
    files_fetched_count: int = 0
    grep_calls_count: int = 0
    ai_calls_count: int = 0
```

تابع `async def build_verify_context(task, watched, *, config) -> VerifyContext`:
- caps را اعمال می‌کند
- repo_tree یک‌بار از GitHub fetch می‌شود (با cache روی sha)
- در ابتدای `verify_task()` صدا زده می‌شود و در همهٔ probes پاس داده می‌شود

---

### گپ ۲ — file content reading به‌جای commit diff

(بدون تغییر از نسخهٔ قبل، فقط افزودنی‌ها در examples)

ماژول جدید: `backend/app/services/verify_runtime/code_content_searcher.py`

API عمومی:

```python
async def fetch_file_content(
    repo_full_name: str, path: str, ref: str = "main",
    *, token: str,
    cache: Dict[str, str],
    max_size_bytes: int = 500_000,
) -> Optional[str]
```
- GET `/repos/{owner}/{repo}/contents/{path}?ref={ref}`
- base64 decode از field `content`
- cache روی key=f"{path}@{ref}"
- skip اگر size > 500KB یا content-type غیر متنی
- بازگشت None در صورت 404/403/error
- log در `context.trace`

```python
async def grep_token_in_files(
    token: str, paths: List[str],
    repo_full_name: str, ref: str,
    *, github_token: str,
    cache: Dict[Tuple[str, str], List[Dict]],
    file_content_cache: Dict[str, str],
    context_lines: int = 2,
    max_matches_per_file: int = 5,
) -> List[Dict]
```
- regex `re.finditer(re.escape(token), content, re.IGNORECASE)`
- خروجی: `[{path, line_number, snippet, before_lines, after_lines}, ...]`
- cap per file
- cache روی key=(path, token)

```python
async def smart_grep_for_ac(
    ac_text: str, target_files: List[str],
    repo_full_name: str, ref: str,
    *, context: VerifyContext,
) -> Dict[str, List[Dict]]
```
- `identifiers = extract_identifiers(ac_text)`
- top-K=15 identifiers (sorted by specificity)
- برای هر identifier در همهٔ target_files
- خروجی: `{identifier: [match, ...]}`

```python
def extract_identifiers(text: str) -> List[str]
```

**🆕 (v2 — کاستی ۱) مثال concrete:**

```python
# مثال ۱: ورودی فارسی + identifier پایتون
text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
extract_identifiers(text) →
    ['view_preferences', 'WatchedProject']

# مثال ۲: ورودی انگلیسی + camelCase
text = "Add useViewPrefs hook for fetching preferences"
extract_identifiers(text) →
    ['useViewPrefs', 'fetching', 'preferences']  # 'Add' حذف چون stop-word

# مثال ۳: ورودی mixed با file path
text = "تابع _record_title_change در oversight_service.py"
extract_identifiers(text) →
    ['_record_title_change', 'oversight_service']

# مثال ۴: کلمات generic - باید filter شوند
text = "بهبود سیستم نمایش"
extract_identifiers(text) →
    []  # هیچ identifier specific نیست → fallback به AI
```

regex‌های دقیق:
- `snake_case`: `r"\b[a-z][a-z0-9_]{2,}\b"` (با حداقل یک underscore یا طول ≥۴)
- `dunder`: `r"\b_[a-z][a-z0-9_]+\b"`
- `camelCase`: `r"\b[a-z][a-zA-Z0-9]{3,}\b"` که حداقل یک حرف بزرگ داشته باشد بعد از index 0
- `PascalCase`: `r"\b[A-Z][a-zA-Z0-9]{3,}\b"`
- `function_call`: `r"\b(\w+)\s*\("`
- `file_path`: `r"\b[\w/.-]+\.(py|tsx?|jsx?|json|yaml|md)\b"`

stop-words (cap ~۱۰۰): فارسی + انگلیسی common words (`the, and, for, this, that, user, system, change, ...` / `بهبود, تغییر, سیستم, پروژه, ...`)

specificity score برای sort:
- length × ۱.۰
- snake_case bonus: +۲
- dunder bonus: +۳ (خیلی specific)
- file_path bonus: +۴ (خیلی specific)

خروجی: top-K=15 unique identifiers، sorted desc by specificity

---

### گپ ۳ — AC matching: file content به‌جای basename

(۴ مرحلهٔ A→B→C→D، بدون تغییر منطقی — فقط نام‌گذاری مشخص‌تر)

تابع‌های جدا برای traceability:
```python
async def _phase_a_basename_match(ac, target_files, context) -> ProbeResult
async def _phase_b_content_grep(ac, target_files, context) -> ProbeResult
async def _phase_c_extended_repo_grep(ac, context) -> ProbeResult
async def _phase_d_ai_judgment(ac, context) -> ProbeResult
```

orchestrator: `analyze_acs_with_content_grep(acs, context)` که چهار phase را به‌ترتیب می‌چرخاند، هر phase که done قطعی داد، early-exit.

---

### گپ ۴ — Iterative orchestrator

ماژول جدید: `backend/app/services/verify_runtime/iterative_orchestrator.py`

```python
@dataclass
class ProbeResult:
    probe_name: str
    verdict: str  # "done" | "partial" | "not_done" | "unclear"
    confidence: float  # 0.0..1.0
    evidence: List[str]
    error: Optional[str] = None
    elapsed_ms: int = 0
```

```python
async def iterative_verify_step(
    step: Dict, context: VerifyContext,
    *, max_iterations: int = 3,
) -> Tuple[ProbeResult, List[ProbeResult]]:
    """
    خروجی: (final_aggregated_result, all_iteration_results)
    """
```

#### Iteration 1 — Standard probes (~۵-۱۰s)
- vision probe (فقط اگر classification = frontend/fullstack)
- code_aware probe (basename + diff window)
- content_grep probe (smart_grep_for_ac روی target_files)
- playwright probe (اگر URL probe موجود)

aggregate → verdict + confidence
- اگر confidence ≥ 0.8 → finalize ✅
- اگر confidence < 0.8 → escalate to iteration 2

#### Iteration 2 — Aggressive content grep (~۱۵-۳۰s)
- file scope توسعه می‌یابد: full repo tree با filter به‌ترتیب:
  1. extensions مرتبط (py/tsx/ts/jsx/js)
  2. paths که با AC text overlap دارند (مثلاً اگر AC نام فولدر گفته)
  3. cap: ۵۰ فایل اضافی
- top-K identifiers (نه فقط top-15، بلکه top-25)
- AI rerun با evidence جدید
- aggregate → verdict + confidence
- اگر confidence ≥ 0.7 → finalize ✅ (آستانهٔ کمتر چون evidence بیشتر داریم)
- اگر < 0.7 → escalate to iteration 3

#### Iteration 3 — Strong model escalation (~۳۰-۶۰s)

**🆕 (v2 — کاستی ۲) Model escalation tier صریح:**

```python
async def _strong_model_judgment(ac, context, prior_results):
    """
    استفاده از model tier بالاتر برای judgment نهایی.
    chain:
        1. تلاش با "gpt-4o" (اگر در MODEL_REGISTRY باشد و key موجود)
        2. fallback به "claude-opus-4-7" یا "claude-sonnet-4-6"
        3. fallback به همان DEFAULT_EXTRACTION_MODEL_ID (no escalation possible)
    """
    from ..core.models_registry import pick_best_extraction_model
    strong_pref = ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"]
    model_id = None
    for cand in strong_pref:
        if _model_available(cand):
            model_id = cand
            break
    if not model_id:
        model_id = pick_best_extraction_model()  # fallback
```

ورودی به strong model:
- متن کامل AC
- تمام evidence از iteration 1 و 2
- file content snippets (cap 50KB)
- repo_tree subset مرتبط
- task.prompt full (cap 50KB)

خروجی: ProbeResult با verdict + reasoning detailed

finalize بدون escalation بیشتر (max 3).

---

### گپ ۵ — Smart probe selection

`_classify_step_for_probe` بازنویسی با ۱۰ قاعده (بدون تغییر از v1).

اضافه: classification result در `context.trace` log می‌شود.

---

### گپ ۶ — Confidence-weighted verdict

`aggregate_verdicts(results: List[ProbeResult]) -> ProbeResult`:

```python
WEIGHTS_BY_PROBE = {
    "content_grep_strong": 3.0,    # ≥۲ identifier در ≥۱ فایل
    "content_grep_weak": 1.5,      # ۱ identifier
    "code_aware_basename": 1.0,    # فقط basename match
    "playwright": 2.0,             # deterministic
    "ai_verifier": 1.0,
    "vision_frontend": 0.5,
    "vision_backend": 0.0,         # vision در backend = weight 0
    "strong_model": 2.5,           # iteration 3
}

def aggregate_verdicts(results):
    # حذف unclear/error
    valid = [r for r in results if r.verdict not in ("unclear",) and not r.error]
    if not valid:
        return ProbeResult("aggregate", "unclear", 0.0, ["all probes inconclusive"])
    
    # weighted vote
    scores = {"done": 0.0, "partial": 0.0, "not_done": 0.0}
    total_weight = 0.0
    for r in valid:
        w = _get_weight(r) * r.confidence  # confidence × weight
        scores[r.verdict] = scores.get(r.verdict, 0) + w
        total_weight += w
    
    winner = max(scores, key=scores.get)
    final_confidence = scores[winner] / total_weight if total_weight else 0
    
    # collect evidence
    evidence = []
    for r in valid:
        if r.verdict == winner:
            evidence.extend(r.evidence)
    
    return ProbeResult("aggregate", winner, final_confidence, evidence[:10])
```

---

### 🆕 (v2 — کاستی ۳) **بهبود ۷ — Per-AC state cache**

#### مشکل
هر بار verify اجرا می‌شود، همهٔ AC ها از صفر چک می‌شوند. اگر AC در ۳ run اخیر `done` با confidence > 0.85 بود و فایل‌های مرتبط تغییر نکردند، re-verify لازم نیست.

#### راه‌حل
فیلد جدید روی `OversightTask`:
```python
ac_verify_cache: Dict[str, Any] = field(default_factory=dict)
# ساختار:
# {
#   "<ac_hash>": {
#     "verdict": "done",
#     "confidence": 0.92,
#     "last_verified_at": ISO,
#     "files_checksum": "abc123",  # checksum از mtime یا sha فایل‌های مرتبط
#     "consecutive_done_count": 3,
#     "evidence": ["..."]
#   }
# }
```

منطق:
1. قبل از verify هر AC:
   - hash از متن AC + classification
   - چک cache
   - اگر `consecutive_done_count >= 3 AND files_checksum unchanged AND age < 7 days`:
     - skip probes، از cache استفاده کن
     - log: `"AC X: cached done (skipped 3 probes)"`
2. بعد از verify:
   - اگر verdict = done و confidence > 0.85:
     - `consecutive_done_count += 1`
     - `files_checksum = compute_files_checksum(target_files)`
   - اگر verdict != done:
     - `consecutive_done_count = 0`
     - cache invalidate

`compute_files_checksum`: sha256 از target_files content (یا sha روی commit ref اگر در GitHub).

flag config: `enable_ac_cache: bool = True` (پیش‌فرض True). user می‌تواند با `?force_full_verify=true` بای‌پاس کند.

---

### 🆕 (v2 — کاستی ۴) **بهبود ۸ — Observability/Trace mode**

#### مشکل
کاربر نمی‌تواند بفهمد چرا verify گفته partial. باید بتواند trace کامل را ببیند.

#### راه‌حل

تمام تصمیم‌های verify در `context.trace` log می‌شوند:
```python
context.trace.append({
    "ts": iso,
    "phase": "iteration_2_content_grep",
    "ac_index": 5,
    "ac_text": "اضافه کردن فیلد view_preferences...",
    "decision": "escalate_to_iter_3",
    "reason": "confidence 0.6 < threshold 0.7",
    "evidence": [...],
    "probe_results": [...],
    "elapsed_ms": 1234,
})
```

سپس روی `VerificationReport`:
```python
@dataclass
class VerificationReport:
    ...
    verify_trace: List[Dict] = field(default_factory=list)  # full trace
    ac_probe_details: List[Dict] = field(default_factory=list)  # per-AC summary
    verify_version: str = "v6"
    config_used: Dict = field(default_factory=dict)  # config snapshot
```

endpoint جدید:
```
GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}
→ trace کامل آخرین (یا specific) verify
```

UI: یک accordion "🔍 Trace" در زیر هر AC در دیتیل تسک — نمایش step-by-step تصمیمات.

---

### 🆕 (v2 — کاستی ۵) **بهبود ۹ — Centralized VerifyConfig**

#### مشکل
هر knob (max_iterations, max_files, model_tier, ...) جدا گفته شده. متمرکز نیست.

#### راه‌حل
ساختار `VerifyConfig`:
```python
@dataclass
class VerifyConfig:
    # iteration limits
    max_iterations: int = 3
    iter1_confidence_threshold: float = 0.8
    iter2_confidence_threshold: float = 0.7
    
    # content grep
    enable_content_grep: bool = True
    max_files_per_run: int = 50
    max_file_size_bytes: int = 500_000
    max_identifiers_per_ac: int = 15
    iter2_max_extra_files: int = 50
    iter2_max_identifiers: int = 25
    
    # model tier
    strong_model_preference: List[str] = field(default_factory=lambda: [
        "gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"
    ])
    
    # cache
    enable_ac_cache: bool = True
    ac_cache_max_age_days: int = 7
    ac_cache_consecutive_threshold: int = 3
    
    # confidence weights
    weights: Dict[str, float] = field(default_factory=lambda: {
        "content_grep_strong": 3.0,
        "content_grep_weak": 1.5,
        "code_aware_basename": 1.0,
        "playwright": 2.0,
        "ai_verifier": 1.0,
        "vision_frontend": 0.5,
        "vision_backend": 0.0,
        "strong_model": 2.5,
    })
    
    # observability
    enable_trace: bool = True
    trace_max_entries: int = 1000
```

ذخیره در `WatchedProject.verify_v6_config: Optional[Dict] = None` (اگر None، defaults).

endpoint: `GET/PATCH /api/oversight/watched/{id}/verify-v6-config`

---

## 🏗 معماری نهایی (با بهبودها)

```
verify_task(task_id, verify_v6=True)
│
├── load WatchedProject.verify_v6_config → VerifyConfig
│
├── build_verify_context(task, watched, config) → VerifyContext
│
├── for each AC (یا task_step):
│    │
│    ├── classify_ac(ac, context) → classification ("frontend"|"backend"|...)
│    │
│    ├── 🆕 check ac_verify_cache:
│    │    if cache_hit_with_freshness:
│    │        → use cached ProbeResult, log "cached"
│    │        → skip iterations
│    │    else:
│    │        → run iterative verify
│    │
│    ├── iterative_verify_step(ac, context, max_iter=3):
│    │    │
│    │    ├── iteration 1: standard probes
│    │    │    ├── content_grep (smart_grep_for_ac)
│    │    │    ├── code_aware (basename + diff)
│    │    │    ├── vision (if frontend/fullstack)
│    │    │    └── playwright (if URL)
│    │    │
│    │    ├── aggregate_verdicts(probes) → ProbeResult
│    │    ├── if confidence ≥ 0.8 → finalize
│    │    │
│    │    ├── iteration 2: aggressive content_grep
│    │    │    ├── full repo grep (filtered)
│    │    │    ├── more identifiers
│    │    │    └── AI rerun with new evidence
│    │    │
│    │    ├── aggregate → ProbeResult
│    │    ├── if confidence ≥ 0.7 → finalize
│    │    │
│    │    ├── iteration 3: strong model escalation
│    │    │    └── _strong_model_judgment(ac, context, prior_results)
│    │    │
│    │    └── finalize unconditionally
│    │
│    ├── update ac_verify_cache:
│    │    if verdict==done && confidence > 0.85:
│    │        consecutive_done_count++, files_checksum updated
│    │    else:
│    │        cache invalidated
│    │
│    └── append to verify_trace + ac_probe_details
│
├── aggregate per-AC → overall task verdict
│
├── apply existing all_steps_done rule + streak logic
│
├── apply title reassess (C5)
│
└── persist + create VerificationReport with verify_trace
```

---

## 📁 File map (v2)

| فایل | تغییر | scope |
|---|---|---|
| `backend/app/services/verify_runtime/context_builder.py` | **جدید** | `VerifyContext`, `VerifyConfig`, `build_verify_context` |
| `backend/app/services/verify_runtime/code_content_searcher.py` | **جدید** | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` + ۴ مثال concrete در docstring |
| `backend/app/services/verify_runtime/iterative_orchestrator.py` | **جدید** | `ProbeResult`, `iterative_verify_step`, `aggregate_verdicts`, `_strong_model_judgment` |
| `backend/app/services/verify_runtime/ac_cache_service.py` | **جدید** | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| `backend/app/services/verify_runtime/code_aware_verifier.py` | بازنویسی phase A→B→C→D با نام تابع‌های صریح | همان فایل، +۲۰۰ خط |
| `backend/app/services/oversight_verifier.py` | `_classify_step_for_probe` با ۱۰ قاعده + integration با orchestrator + flag `verify_v6` | همان فایل |
| `backend/app/services/oversight_service.py` | اضافه کردن `ac_verify_cache` و `verify_v6_config` به dataclass ها | همان فایل |
| `backend/app/services/verify_runtime/__init__.py` | export نام‌های جدید | همان فایل |
| `backend/app/api/routes/oversight.py` | endpoint های جدید: `verify-trace`, `verify-v6-config` (GET/PATCH) + پارامتر `verify_v6=True\|False` در verify endpoint | همان فایل |
| `backend/tests/test_code_content_searcher.py` | **جدید** | unit tests برای `extract_identifiers` با ۴ مثال + grep test |
| `backend/tests/test_iterative_orchestrator.py` | **جدید** | unit tests برای `aggregate_verdicts` با ۵ سناریو |

---

## 🧪 معیار موفقیت + meta-test (v2 — concrete AC list)

این bug **باید با خودش verify شود**. ۱۲ AC مشخص (افزایش از ۱۰ به ۱۲):

| # | AC | identifier‌های قابل grep |
|---|---|---|
| 1 | فایل `context_builder.py` با کلاس `VerifyContext` و تابع `build_verify_context` | `VerifyContext`, `build_verify_context`, `VerifyConfig` |
| 2 | فایل `code_content_searcher.py` با ۴ تابع + ۴ مثال در docstring | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` |
| 3 | فایل `iterative_orchestrator.py` با ۳ symbol + strong model escalation | `iterative_verify_step`, `aggregate_verdicts`, `ProbeResult`, `_strong_model_judgment` |
| 4 | فایل `ac_cache_service.py` با ۳ تابع cache | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| 5 | `_classify_step_for_probe` با ۱۰ قاعدهٔ explicit در `oversight_verifier.py` | `"backend"`, `"frontend"`, `"fullstack"`, `"infra"`, `"test_only"`, `"doc_only"`, `"manual_only"` |
| 6 | `code_aware_verifier.py` با ۴ تابع جدید phase | `_phase_a_basename_match`, `_phase_b_content_grep`, `_phase_c_extended_repo_grep`, `_phase_d_ai_judgment` |
| 7 | فیلد جدید `ac_verify_cache` روی `OversightTask` dataclass | `ac_verify_cache` در `oversight_service.py` |
| 8 | فیلد جدید `verify_v6_config` روی `WatchedProject` dataclass | `verify_v6_config` |
| 9 | `VerificationReport` با فیلدهای `verify_trace`, `ac_probe_details`, `verify_version`, `config_used` | همان نام‌ها در dataclass |
| 10 | endpoint `GET /tasks/{task_id}/verify-trace` و `GET/PATCH /watched/{id}/verify-v6-config` | router decorators |
| 11 | پارامتر `verify_v6: bool = True` در `verify_task` signature | `verify_v6` در function def |
| 12 | حداقل ۲ فایل تست: `test_code_content_searcher.py` (۴ مثال extract_identifiers) و `test_iterative_orchestrator.py` (۵ سناریو aggregate_verdicts) | اسامی فایل + assertion های concrete |

**معیار سخت‌گیرانه:** vary v6 وقتی روی این bug اجرا شد، باید **≥۱۱ از ۱۲ AC** را done ببیند (با confidence ≥ 0.8).

اگر کمتر → یعنی verify v6 خودش هنوز ضعیف است → bug C6 fail.

---

## ⚠️ Edge cases (v2 — افزایش‌یافته)

1. **GitHub rate limit**: cache aggressive + cap 50 file. اگر rate limit hit شد، fallback به v5 منطق.
2. **Large file**: skip > 500KB (configurable).
3. **Binary file**: skip اگر non-text Content-Type.
4. **Token not in private repo**: fallback graceful.
5. **Identifier spam**: AC تمام stop-words → fallback به AI.
6. **Multi-language**: identifiers از فارسی+انگلیسی هر دو (با regex unicode-aware).
7. **Recursion**: orchestrator فقط probes را call می‌کند، نه `verify_task`.
8. **Memory**: caps روی هر فیلد VerifyContext.
9. **Backward compat**: `verify_v6=False` → مسیر v5.
10. **A/B**: random seed برای ۵۰/۵۰ split بین v5/v6 (debug).
11. **🆕 (v2) Cache invalidation race**: اگر دو verify همزمان روی یک تسک شروع شدند، cache lock با `asyncio.Lock` per-task.
12. **🆕 (v2) Strong model unavailable**: اگر هیچ strong model در chain موجود نیست، iteration 3 با fallback model اجرا می‌شود (با warning log) — fail نمی‌کند.
13. **🆕 (v2) Trace size**: cap ۱۰۰۰ entry per verify_run. اگر بیشتر، oldest حذف می‌شوند (FIFO).
14. **🆕 (v2) Config validation**: اگر user verify_v6_config با مقادیر out-of-range تنظیم کرد (مثلاً max_iterations=100)، clamp به range معتبر.

---

## 🚫 خارج از scope (بدون تغییر)

(همان قبلی)
- تغییر در Playwright probe
- تغییر در vision probe
- ML classification
- multi-language تشخیص source code (فقط py/ts/tsx/js/jsx)
- AST-level analysis
- distributed cache
- WebSocket live progress

---

## 🔬 ترتیب اجرا (v2 — با ۸ chunk)

1. **Chunk 1**: `context_builder.py` — `VerifyConfig`, `VerifyContext`, `build_verify_context`. unit test.
2. **Chunk 2**: `code_content_searcher.py` — ۴ تابع + ۴ مثال در docstring + `extract_identifiers` با stop-words. unit test.
3. **Chunk 3**: `iterative_orchestrator.py` — `ProbeResult`, `aggregate_verdicts`, `iterative_verify_step`, `_strong_model_judgment`. unit test برای aggregate.
4. **Chunk 4**: `ac_cache_service.py` — cache logic + integration در `OversightTask.ac_verify_cache`.
5. **Chunk 5**: `code_aware_verifier.py` — ۴ phase صریح + integration با content_grep.
6. **Chunk 6**: `oversight_verifier.py` — `_classify_step_for_probe` rewrite + integration با orchestrator + flag `verify_v6`.
7. **Chunk 7**: `VerificationReport.verify_trace/ac_probe_details/verify_version` + endpoint های جدید + UI accordion.
8. **Chunk 8**: meta-test — اجرای verify v6 روی این bug. اطمینان از ≥۱۱/۱۲ AC.

هر chunk: commit جدا، type-check، push.

---

## ✅ جدول نهایی ادعا

| تفاوت من با verify | راه‌حل در v6 v2 | کاستی برطرف شد؟ |
|---|---|---|
| من full file می‌خوانم | `code_content_searcher.fetch_file_content` | ✅ |
| من targeted grep می‌زنم | `smart_grep_for_ac` با ۴ مثال concrete | ✅ |
| من iterative هستم | `iterative_verify_step` با ۳ iteration | ✅ |
| من می‌دانم vision کجا کار نمی‌کند | `_classify_step_for_probe` با ۱۰ قاعده | ✅ |
| من چندین منبع را cross-check می‌کنم | `aggregate_verdicts` weighted | ✅ |
| من حافظهٔ کامل دارم | `VerifyContext` با همهٔ history | ✅ |
| **(v2)** من از کار قبلی حافظه دارم | `ac_verify_cache` با consecutive_done_count | ✅ |
| **(v2)** من می‌توانم توضیح بدم چرا | `verify_trace` + endpoint debug | ✅ |
| **(v2)** من از مدل قوی استفاده می‌کنم | `_strong_model_judgment` در iter 3 صریح | ✅ |
| **(v2)** من tunable هستم | `VerifyConfig` centralized | ✅ |

-------------------------------

پنج باگ زیربنایی:

باگ ۱: verifier همهٔ تسک‌ها را با همان probe set برخورد می‌کند. backend changes (مثل افزودن task_id به SmartChatRequest) در ui_interaction(/oversight) دیده نمی‌شوند، پس probe fail می‌شود ولی feature موجود است.

باگ ۲: probes با path parameters (مثل /load-task/{task_id}) بدون مقدار parameter صدا زده می‌شوند → HTTP 405 → probe «feature missing» تشخیص می‌دهد در حالی که فقط URL نامعتبر است.

باگ ۳: AI verifier متن done_parts و remaining_parts را به‌صورت موازی تولید می‌کند بدون چک تناقض. اگر تستی متناقض است، باید resolve شود.

باگ ۴: probe ها به مدل vision نمی‌گویند «این feature backend است، دنبال متن قابل‌مشاهده نگرد». مدل visual را برای feature backend صدا می‌زند → hallucination ضد-feature.

باگ ۵: trace شفاف نیست. کاربر نمی‌فهمد چرا step X شکست خورد — آیا کد ساخته نشده، یا probe اشتباه تست کرده.

هدف نهایی Verify v7
verifier نوع تسک را خودکار تشخیص دهد (backend / frontend / fullstack / infra / docs / test)
probe ها متناسب با نوع تسک وزن داده شوند (ui_interaction روی تسک backend وزن ≈ 0)
probe ها با path parameters به‌درستی هندل شوند (synthesize parameter یا skip)
خروجی AI verifier تناقض done ↔ remaining نداشته باشد
prompt مدل vision حاوی نوع تسک باشد تا hallucination کاهش یابد
trace شفاف توضیح دهد چرا هر step done/partial/not_done شد
فاز A — Task Type Classifier
اصول
یک تابع helper جدید: _classify_task_type(task) که بر اساس prompt + target_files + AC، نوع تسک را تشخیص می‌دهد.

دسته‌بندی‌ها
Type	معیار تشخیص	probe profile
pure_backend	همهٔ target_files با .py پایان دارند یا path شامل backend/ و در prompt اشاره‌ای به frontend/UI نیست	weight ui_interaction = 0.1، api_probe = 2.0
pure_frontend	همهٔ target_files با .tsx/.ts/.jsx/.js/.css پایان دارند و path شامل frontend/	weight ui_interaction = 2.0، api_probe = 0.3
fullstack	ترکیبی از backend و frontend	weight ui_interaction = 1.5، api_probe = 1.5
infra	فایل‌های Dockerfile, *.yml, *.yaml, .github/workflows/*	weight ui_interaction = 0، code_aware = 3.0
docs_only	فقط .md, .txt	همهٔ probes را skip، فقط code_aware
test_only	فقط فایل‌های test_*.py, *.test.tsx	weight ui_interaction = 0.3، test_probe = 3.0
mixed_unknown	تشخیص ناممکن	استفاده از weights پیش‌فرض (همان WEIGHTS_BY_PROBE موجود)
اقدامات
محل: backend/app/services/verify_runtime/iterative_orchestrator.py کنار WEIGHTS_BY_PROBE
تابع _classify_task_type(task) -> str که یکی از این 7 رشته برمی‌گرداند
منطق تشخیص باید fast باشد (regex ساده، نه AI call)
در trace ثبت شود: task_type_classified: pure_backend
معیارهای پذیرش فاز A
۱. تابع _classify_task_type در iterative_orchestrator.py موجود است
۲. تابع برای هر یک از ۷ نوع، رشتهٔ صحیح برمی‌گرداند (با تست واحد)
۳. task_type در verify_trace با phase=classify_task_type ثبت می‌شود
۴. تشخیص بدون فراخوانی AI انجام می‌شود (regex/heuristic)

فاز B — Task-Type-Aware Probe Weighting
اصول
WEIGHTS_BY_PROBE فعلاً ثابت است. باید بر اساس task_type پویا شود.

اقدامات
یک dict جدید: WEIGHTS_BY_TASK_TYPE: Dict[str, Dict[str, float]] که برای هر task_type، override weights را نگه می‌دارد
تابع _get_weights_for_task(task) -> Dict[str, float]:
task_type = _classify_task_type(task)
اگر task_type در WEIGHTS_BY_TASK_TYPE: weights مخصوص آن را برگردان
در غیر این صورت: WEIGHTS_BY_PROBE پیش‌فرض
در aggregate_verdicts، به‌جای استفاده از WEIGHTS_BY_PROBE ثابت، از _get_weights_for_task(task) استفاده شود
در trace ثبت شود: weights_used: {ui_interaction: 0.1, api_probe: 2.0, ...} و task_type: pure_backend
مقادیر weights برای هر task_type
WEIGHTS_BY_TASK_TYPE = {
    "pure_backend": {
        "ui_interaction": 0.1,      # تقریباً نادیده — backend در UI دیده نمی‌شود
        "api_probe": 2.0,           # مهم — تست واقعی endpoint
        "code_aware_basename": 2.5, # خیلی مهم — تأیید static که فایل/تابع موجود است
        "content_grep_strong": 3.0,
        "content_grep_weak": 1.5,
        "playwright": 0.1,          # تقریباً نادیده
        "ai_verifier": 1.0,
        "vision_frontend": 0.0,     # وزن صفر — visual بی‌معنی برای backend
        "vision_backend": 0.5,
        "strong_model": 2.5,
        "test_probe": 1.5,
    },
    "pure_frontend": {
        "ui_interaction": 2.0,      # مهم — UI واقعی تست شود
        "api_probe": 0.3,
        "code_aware_basename": 1.5,
        "content_grep_strong": 2.5,
        "content_grep_weak": 1.5,
        "playwright": 2.5,          # مهم — interaction واقعی
        "ai_verifier": 1.0,
        "vision_frontend": 1.5,
        "vision_backend": 0.0,
        "strong_model": 2.5,
        "test_probe": 1.0,
    },
    "fullstack": {
        # نسخهٔ متوازن — هیچ probe ای weight 0 ندارد
        ...
    },
    "infra": {
        "ui_interaction": 0.0,
        "api_probe": 0.5,
        "code_aware_basename": 3.0,
        "content_grep_strong": 3.0,
        "playwright": 0.0,
        "vision_frontend": 0.0,
        "vision_backend": 0.0,
        ...
    },
    "docs_only": {
        # همه چیز کم — فقط code_aware
        "ui_interaction": 0.0,
        "api_probe": 0.0,
        "code_aware_basename": 3.0,
        "content_grep_strong": 3.0,
        ...
    },
    "test_only": {
        "test_probe": 3.0,
        "ui_interaction": 0.3,
        ...
    },
}
معیارهای پذیرش فاز B
۵. dict WEIGHTS_BY_TASK_TYPE با حداقل ۷ نوع تسک تعریف شده است
۶. تابع _get_weights_for_task(task) تعریف شده و weights صحیح برمی‌گرداند
۷. aggregate_verdicts از weights پویا استفاده می‌کند نه ثابت
۸. trace شامل task_type و weights_used در phase aggregation است
۹. backward compat: اگر task ندارد یا تشخیص ناممکن، behavior پیش‌فرض حفظ می‌شود

فاز C — Probe URL Validation
اصول
probes با path parameters (مثل /load-task/{task_id}) باید:

یا {param} را با مقدار واقعی پر کنند (مثلاً task_id خود تسک)
یا probe را به‌عنوان skipped (نه failed) علامت بزنند
و در trace توضیح بدهند چرا
اقدامات
در run_probes_for_acs (یا تابع متناظر در verify_runtime/runner.py):
قبل از زدن probe، URL را برای path parameters parse کن
regex: \{(\w+)\}
اگر parameter پیدا شد:
اگر نام parameter task_id بود → از task.id فعلی استفاده کن
اگر project_id بود → از watched.project_id یا اطلاعات context استفاده کن
اگر هیچ کدام match نشد → probe را skip کن با reason: unfilled_path_param:{param_name}
در صورت 405/404 از probe، به جای failed آن را به skipped با reason: route_not_matched تبدیل کن (probe مسئله است نه feature)
در trace ثبت شود: probe_url_filled: /load-task/abc123 یا probe_skipped_reason: unfilled_path_param
معیارهای پذیرش فاز C
۱۰. probes با {task_id} خودکار با task.id فعلی پر می‌شوند
۱۱. probes با {project_id} با watched.project_id پر می‌شوند
۱۲. probes با path parameter که قابل پر کردن نیست، با skipped و reason ثبت می‌شوند
۱۳. اگر HTTP 405 برگشت، probe skipped می‌شود نه failed
۱۴. اگر HTTP 404 برگشت روی URL با path param، probe skipped می‌شود

فاز D — Contradiction Resolution در خروجی AI verifier
مشکل
AI verifier در یک پاس JSON تولید می‌کند که done_parts و remaining_parts هر دو شامل همان AC ها هستند. این منطقی نیست.

اقدامات
پس از parse خروجی AI در oversight_verifier.py نزدیک خط ۳۳۴۵:
برای هر آیتم در remaining_parts، بررسی کن آیا متن مشابهی (Jaccard ≥0.7 یا substring) در done_parts موجود است
اگر موجود است: تناقض است — یک resolver فراخوانی شود
منطق resolver:
اگر code-aware برای آن step implemented گفته → آن را از remaining حذف کن (done برنده می‌شود)
اگر code-aware چیزی نگفته و فقط runtime probe شکست خورده → بسته به probe type:
اگر probe ای که شکست خورد ui_interaction روی تسک pure_backend بود → نادیده (probe نامتناسب)
در غیر این صورت → در remaining بماند
در trace ثبت شود: contradiction_resolved: <step_text> با reason
معیارهای پذیرش فاز D
۱۵. تابع _resolve_done_remaining_contradiction(done_parts, remaining_parts, task) ساخته شده
۱۶. منطق Jaccard یا substring برای تشخیص تناقض پیاده شده
۱۷. اگر code-aware = implemented، item از remaining حذف می‌شود
۱۸. اگر probe نامتناسب، item نادیده گرفته می‌شود
۱۹. trace شامل لیست contradictions_resolved با reason است

فاز E — Backend-Feature Awareness در Prompt مدل Vision
مشکل
probes vision به مدل می‌گویند «به این صفحه نگاه کن و بگو آیا feature X موجود است». مدل vision دنبال متن قابل‌مشاهده می‌گردد. اما اگر feature X فقط در backend است (مثل افزودن task_id به SmartChatRequest)، مدل می‌گوید «feature ساخته نشده» — چون قابل‌مشاهده در page نیست.

اقدامات
در prompt مدل vision (در _run_ui_interaction_probe یا متناظر)، یک hint اضافه کن:
اگر task_type در (pure_backend, infra): به مدل بگو:
«این feature backend است و در UI قابل‌مشاهده نیست. صفحه فقط برای تأیید قابل‌دسترسی بودن سرویس است. به متن صفحه برای feature X نگاه نکن — این probe فقط health-check صفحه است، نه feature verification. verdict مناسب: pass اگر صفحه load شد.»

این می‌تواند با یک system prompt prefix یا یک خط در user message انجام شود
در trace ثبت شود: vision_prompt_hint_added: backend_task
معیارهای پذیرش فاز E
۲۰. prompt مدل vision برای task_type backend/infra hint اضافه شده دارد
۲۱. مدل vision در این موارد به‌جای hallucination، verdict pass می‌دهد اگر صفحه load شد
۲۲. trace vision_prompt_hint_added با task_type ثبت می‌شود

فاز F — شفاف‌سازی Trace
اصول
trace باید برای هر step واضح بگوید چرا verdict آن done/partial/not_done شد.

اقدامات
در پایان iterative_verify_step، یک خلاصهٔ خواناتر در trace اضافه شود:
{
  "phase": "step_summary",
  "step_text": "فاز 0 — بازرسی کیفیت...",
  "final_verdict": "done",
  "task_type": "pure_backend",
  "weights_used": {...},
  "probes_contributed": [
    {"probe": "code_aware_basename", "verdict": "done", "weight_applied": 2.5},
    {"probe": "ui_interaction", "verdict": "failed", "weight_applied": 0.1, "note": "low weight — task is backend"}
  ],
  "decision_reason": "code-aware confirms implementation, runtime probes downweighted for backend task"
}
endpoint /api/oversight/tasks/{id}/verify-trace این خلاصه را برگرداند
در UI صفحهٔ verify report، یک accordion «چرا این verdict؟» اضافه شود که این summary را نمایش دهد
معیارهای پذیرش فاز F
۲۳. trace شامل phase: step_summary با decision_reason برای هر step است
۲۴. probes_contributed شامل weight_applied و note است
۲۵. endpoint verify-trace خلاصه را قابل دسترس می‌کند
۲۶. UI accordion «چرا این verdict؟» در verify report موجود است

ملاحظات کلی
Backward compatibility: اگر _classify_task_type نتواند تشخیص دهد (mixed_unknown)، رفتار قبلی Verify v6 حفظ شود
No regression: همهٔ سناریوهای Verify v6 (که هم‌اکنون پاس می‌شوند) باید همچنان پاس شوند
هر فاز در commit جداگانه
معیارهای کلی پذیرش
۲۶ معیار بالا قابل grep در source code
سناریوی تست end-to-end: یک تسک backend-heavy (مثل خود C7) را verify کنید با verify_v7=True. باید:
چک‌لیست: 7/7
done_parts: ۷ فاز
remaining_parts: خالی (نه ۸ مورد متناقض)
verdict نهایی: done با confidence ≥ 0.85
trace شامل task_type=pure_backend
probes با weight 0.1 برای ui_interaction نشان داده شوند
سناریوی frontend: یک تسک frontend-heavy verify شود → weights برعکس
سناریوی docs: یک تسک فقط .md → فقط code_aware اجرا شود، سایر probes skip
سناریوهای meta-test
_classify_task_type برای تسک با همهٔ target_files .py → pure_backend
_classify_task_type برای تسک با همهٔ target_files .tsx → pure_frontend
_classify_task_type برای تسک mixed → fullstack
_get_weights_for_task برای pure_backend → ui_interaction weight = 0.1
probe /load-task/{task_id} خودکار با task.id واقعی پر می‌شود
probe بدون پر شدن param → skipped (نه failed)
HTTP 405 → skipped (نه failed)
AC در هر دو done و remaining → resolver حذفش می‌کند
vision prompt برای backend task شامل hint است
trace step_summary با decision_reason در پایان موجود است
```

## 📋 چک‌لیست مراحل (52 مرحله)

این تسک به مراحل کوچک‌تر تقسیم شده. **در هر verify خودکار، وضعیت هر مرحله به‌صورت `[ ]` (انجام نشده)، `[~]` (ناقص)، یا `[x]` (انجام شده) به‌روز می‌شود.**
وقتی تمام مراحل `[x]` شدند، تسک به‌طور خودکار به «انجام شده» منتقل می‌شود.

- [x] **مرحله 1: ایجاد لایه Runtime Verification برای اجرای Probe واقعی و جمع‌آوری شواهد اجرایی** — این بخش طراحی یک لایه جدید runtime verification را مشخص می‌کند که به جای خواندن استاتیک کد، برای هر Acceptance Criterion (AC) رفتاری یک probe واقعی اجرا می‌کند. شامل سه نوع probe: Playwright برای UI، HTTP برای API، pytest برای backend logic. خروجی هر probe شواهد runtime مانند screenshot، response JS
- [x] **مرحله 2: یکپارچه‌سازی Stage 5: نقطهٔ اتصال verify فعلی با AI و PDF و UI** — این بخش موقعیت دقیق فایل‌های مرتبط با Stage 5 (یکپارچه‌سازی) را مشخص می‌کند. شامل: oversight_verifier.py (نقطهٔ یکپارچه‌سازی)، oversight_strong_prompt.py (تولید AC)، oversight_service.py (ایجاد تسک)، oversight_verify_pdf.py (PDF)، frontend page.tsx (نمایش)، و پوشه‌های جدید verify_runtime/ و verify_e
- [x] **مرحله 3: تبدیل ساختار AC از رشته به struct با verify_method و verify_plan** — این بخش طراحی مفهومی جدیدی برای ساختار Acceptance Criteria (AC) ارائه می‌دهد که از یک رشته ساده به یک struct با فیلدهای text, verify_method, verify_plan تبدیل می‌شود. شامل پنج نوع verify_method (static, ui_interaction, api_response, backend_test, manual_only) و جایگزینی شواهد grep با runtime evidenc
- [x] **مرحله 4: Schema migration برای AC ساختاریافته در OversightTask** — این مرحله شامل تغییر نوع فیلد acceptance_criteria در OversightTask از List[str] به List[Union[str, Dict]]، ایجاد helper _normalize_ac برای تبدیل یکتا به ساختار {text, verify_method, verify_plan, evidence_history}، افزودن فیلدهای verify_method و verify_plan به هر step در task_steps، و اجرای migration
- [x] **مرحله 5: گسترش system prompt برای تولید verify_plan توسط AI** — این مرحله system prompt در فایل oversight_strong_prompt.py را گسترش می‌دهد تا AI علاوه بر AC، برای هر AC یک verify_method و در صورت نیاز verify_plan تولید کند. چارچوب تصمیم‌گیری بر اساس کلمات کلیدی AC تعریف شده است (ui_interaction, api_response, backend_test, static, manual_only). یک نمونه JSON (few
- [x] **مرحله 6: اجرای هستهٔ پروب‌های تأیید (Probe Runners) برای هر AC** — این بخش شامل ایجاد پکیج جدید backend/app/services/verify_runtime/ با فایل‌های base.py (تعریف dataclass RuntimeProbeResult)، static_probe.py (wrapper روی grep فعلی)، ui_probe.py (استفاده از playwright.async_api با screenshot و browser pool)، api_probe.py (استفاده از httpx.AsyncClient با assert status
- [x] **مرحله 7: اضافه کردن فیلدهای Base URL و Config به WatchedProject و UI تنظیمات پروژه** — این بخش شامل افزودن فیلدهای frontend_base_url، backend_base_url و runtime_auth به مدل WatchedProject در oversight_service.py، ایجاد UI برای تنظیم این مقادیر در صفحه تنظیمات پروژه (projects/[id]/page.tsx یا settings UI)، پیاده‌سازی دکمه تست اتصال (ping به فرانت و GET به backend health)، و مدیریت حالت
- [x] **مرحله 8: یکپارچه‌سازی runtime probes با verify_task در oversight_verifier.py** — این مرحله شامل افزودن فراخوانی run_probes_for_task در ابتدای تابع verify_task (قبل از فراخوانی AI)، جمع‌آوری نتایج probeها، تبدیل آنها به متن شواهد runtime، و الحاق این متن به عنوان بخش جدیدی در prompt ارسالی به AI است. همچنین شامل منطق override نتایج AI بر اساس نتایج runtime (اولویت runtime بر AI) 
- [x] **مرحله 9: ذخیره‌سازی evidence در storage/verify_evidence با cleanup و endpoint سرو** — این بخش شامل پیاده‌سازی ساختار دایرکتوری storage/verify_evidence/<task_id>/<run_id>/ با فایل‌های ac1_step1.png, ac1_step2.png, ac2_response.json, ac3_pytest.json و manifest.json است. همچنین شامل cleanup policy (نگه‌داری 5 run آخر هر task)، endpoint جدید GET /api/oversight/tasks/{id}/evidence/{run_id
- [x] **مرحله 10: افزودن شواهد Runtime به PDF و پیام تلگرام** — این مرحله شامل افزودن یک بخش جدید به نام «📷 شواهد Runtime» در PDF خروجی است که برای هر Acceptance Criteria (AC) یک کارت شامل متن AC، badge روش (UI/API/Test)، badge وضعیت، و شواهد inline (تصویر برای UI، JSON truncated برای API، stdout pytest truncated برای Test) ایجاد می‌کند. همچنین در پیام تلگرام، ا
- [x] **مرحله 11: Stage 8 — Frontend UI برای نمایش evidence در مودال جزئیات تسک** — این بخش شامل پیاده‌سازی UI در frontend/src/app/oversight/page.tsx برای نمایش آخرین verify runtime در مودال جزئیات تسک است. شامل: نمایش row برای هر AC با method icon + status + دکمه مشاهده evidence، مودال دوم با gallery screenshot (lightbox)، JSON formatted با syntax highlight، terminal-style block ب
- [x] **مرحله 12: Stage 9: پیاده‌سازی مدیریت چرخه‌عمر، زمان‌بندی، محدودیت‌ها و Degrade امنیتی Runtime** — این مرحله شامل پیاده‌سازی مدیریت چرخه‌عمر Playwright browser process در lifespan FastAPI (شروع و kill بعد از 5 دقیقه idle)، اعمال per-task timeout کلی 5 دقیقه، per-probe timeout (ui=30s, api=10s, test=120s)، Semaphore با حداکثر 3 probe موازی برای یک task، graceful degrade به static در صورت عدم نصب P
- [x] **مرحله 13: Stage 10: پیاده‌سازی تست‌های واحد و یکپارچه‌سازی برای قابلیت Verify Runtime** — این مرحله شامل نوشتن تست‌های واحد برای هر probe (static, ui, api, test, runner) و یک تست یکپارچه‌سازی end-to-end است. همچنین شامل ایجاد فیکسچرهای known-good و known-bad برای اعتبارسنجی سناریوهای موفق و شکست می‌شود. معیارهای پذیرش عملکردی و کیفی (مانند type-check، عدم شکست تست‌های موجود، graceful dis
- [x] **مرحله 14: ساخت inspector_probe برای اتصال خودکار به verify جدید و ضمیمه تلگرامی** — این بخش شامل طراحی و پیاده‌سازی یک probe جدید به نام inspector_probe است که به صورت خودکار صفحه دیپلوی‌شده را با Playwright باز می‌کند، screenshot می‌گیرد، console و backend logs را جمع می‌کند، با Vision AI تحلیل می‌کند و نتیجه را به عنوان شواهد در گزارش verify بازمی‌گرداند. همچنین شامل ذخیره‌سازی ج
- [x] **مرحله 15: Phase 1: پیاده‌سازی محدودیت‌ها و معماری ذخیره‌سازی screenshot با Vision Fallback Chain** — این بخش شامل پیاده‌سازی کامل محدودیت‌های Phase 1 (navigate, click, screenshot, Vision AI, console log, backend log, Telegram attachment, TTL cleanup) و معماری ذخیره‌سازی screenshot روی دیسک با path نسبی در DB است. همچنین شامل Vision Fallback Chain سه‌لایه (Vision model → text-only verify model → non
- [x] **مرحله 16: سه فیکس جدید پس از تست Phase 2: چک‌لیست در متن تلگرام، تبدیل bundle به PDF، بهبود vision prompt برای تشخیص feature** — این بخش شامل سه فیکس مستقل است که باید هم‌اکنون اجرا شوند. فیکس ۱: اضافه کردن خلاصه چک‌لیست task_steps به متن پیام تلگرام (نه فقط پیوست). فیکس ۲: تبدیل mega-bundle از HTML به PDF با پشتیبانی فارسی و fallback به HTML. فیکس ۳: بهبود vision prompt برای تشخیص حضور feature در صفحه و تأثیر آن بر pass/fail
- [x] **مرحله 17: مرور سریع Phase 1 و 2 و سه فیکس آخر — آماده‌سازی برای Phase 3** — این بخش صرفاً یک مرور (review) از قابلیت‌های پیاده‌سازی شده در Phase 1، Phase 2 و سه فیکس آخر است. هیچ کار اجرایی جدیدی در این بخش تعریف نشده و صرفاً برای یادآوری وضعیت فعلی پروژه قبل از شروع Phase 3 ارائه شده است. تمام آیتم‌های ذکر شده قبلاً اجرا شده‌اند.
- [x] **مرحله 18: رفع محدودیت‌های Phase 2: تعامل با UI، تشخیص دقیق‌تر، لاگین و submit فرم** — این بخش چهار محدودیت اصلی Phase 2 را مشخص می‌کند که Phase 3 باید حل کند: (1) ناتوانی probe در تعامل با feature (مثلاً کلیک روی دکمه)، (2) false-positive بالای vision در تشخیص feature_present، (3) عدم امکان بررسی صفحات نیازمند لاگین، (4) عدم توانایی تست ACهای نیازمند submit فرم. این محدودیت‌ها از تست
- [x] **مرحله 19: Phase 3: پیاده‌سازی سه قابلیت متمم (Form Interaction, Auth Management, Enhanced Detection)** — این بخش شامل پیاده‌سازی کامل سه قابلیت متمم در Phase 3 است: (A) پشتیبانی از Form/Input Interaction Recipes در inspector_probe با 16 action مختلف، (B) مدیریت Authentication/Session با auto-detect login redirect و auth recipe، (C) Enhanced Feature Detection با multi-screenshot و before/after analysis.
- [x] **مرحله 20: پیاده‌سازی auth recipe برای probe‌ها در runtime verification** — این بخش مربوط به افزودن قابلیت احراز هویت خودکار (auth recipe) به فرآیند runtime verification است. شامل طراحی ساختار داده runtime_auth_recipe از نوع Optional[Dict]، پیاده‌سازی flow لاگین مبتنی بر فرم (form_login) با مراحل گام‌به‌گام (fill, click, wait_for_url)، ذخیره‌سازی storage_state (cookies + lo
- [x] **مرحله 21: پیاده‌سازی کش رمزنگاری‌شده storage_state و پشتیبانی از آن در probe و verifier** — این بخش شامل سه تغییر است: (1) ایجاد تابع `obtain_or_refresh_storage_state` در فایل جدید `auth_runner.py` که storage_state را با AES-GCM رمزنگاری کرده و در حافظه کش می‌کند، (2) افزودن پشتیبانی از `ProbeContext.storage_state` در `inspector_probe.py` برای استفاده از storage_state موجود در context مرور
- [x] **مرحله 22: Phase 3: Auth Recipe, Enhanced Feature Detection, UI Panel, AI Enricher, and Safety Limits** — این بخش شامل پیاده‌سازی کامل Phase 3 است: مدیریت auth recipe (ذخیره storage_state، تشخیص redirect به login)، enhanced feature detection (before/after screenshot pairs، vision pair analysis، expected API calls assertion)، UI panel برای تنظیم auth recipe، بهبود AI enricher برای تولید recipe ۳-۸ مرحله‌
- [x] **مرحله 23: Phase 4: Smart Navigation + Backend Log Probe + Code-aware Verifier** — این بخش شامل اجرای کامل Phase 4 از سری verify جدید است که پس از Phase 1, 2, 3 و سه فیکس آخر اجرا می‌شود. محتوای دقیق و جزئیات اجرایی Phase 4 در این بخش ارائه نشده و صرفاً به عنوان یک هدر و مرور وضعیت فعلی ذکر شده است. هیچ دستورالعمل اجرایی، لیست کارها یا تغییرات مشخصی در این بخش وجود ندارد.
- [x] **مرحله 24: رفع مشکلات باقیمانده Phase 3 در Phase 4: route guessing ضعیف، backend-heavy benefit صفر، استفاده ناکامل از Render logs و inspector chat** — این بخش چهار مشکل مشخص از تست واقعی Phase 3 را فهرست می‌کند که Phase 4 باید حل کند: (1) route guessing ضعیف برای تسک‌های دارای URL خاص، (2) تسک‌های backend-heavy که از probe UI سود نمی‌برند و verify بدون شواهد می‌ماند، (3) استفاده ناکامل از Render logs (فقط error/warn فیلتر می‌شود)، (4) استفاده ناکا
- [x] **مرحله 25: پیاده‌سازی سه ستون Phase 4: Smart Navigation Probe، Backend Log Probe و Code-aware Verifier** — این بخش شامل پیاده‌سازی سه قابلیت مجزا در Oversight Service است: (A) Smart Navigation Probe که به جای حدس URL، از home page شروع کرده و nav menu را برای یافتن لینک مرتبط با feature تحلیل می‌کند، (B) Backend Log Probe که برای تسک‌های backend-heavy لاگ‌های Render را بر اساس target_files و AC keywords 
- [x] **مرحله 26: اجرای پروب‌های runtime برای backend ACها با Smart Navigation** — این مرحله شامل اجرای پروب‌های UI (با Smart Navigation) و پروب‌های backend log برای acceptance criteriaهای backend است. اگر task_type 'backend' یا 'mixed' باشد، برای هر AC که backend است، یک پروب لاگ اجرا می‌شود. اگر task_type 'unknown' باشد، هیچ پروبی اجرا نمی‌شود. این مرحله بخشی از فاز 3 است و نتای
- [x] **مرحله 27: پیاده‌سازی سه پروب جدید (Smart Navigation، Backend Log، Code-aware) در Oversight Runtime** — این بخش شامل پیاده‌سازی کامل سه نوع پروب جدید در runtime verification است: Smart Navigation (navigation_helper.py)، Backend Log Probe (backend_log_probe.py)، و Code-aware Verifier (code_aware_verifier.py). همچنین شامل تغییرات در oversight_verifier.py برای routing task type، تغییرات در inspector_prob
- [x] **مرحله 28: Phase 5: Logic Audit — بررسی هدف، منطق و coherence در auto-scan و task creation** — این فاز به پیاده‌سازی Logic Audit می‌پردازد که شامل بررسی هدف (purpose)، منطق (logic) و coherence (انسجام) در فرآیند auto-scan و task creation است. این فاز مستقیماً بندهای R10 و R11 درخواست خام را پوشش می‌دهد. R11 یک مثال از باگ منطقی در هماهنگی (trade) ارائه می‌دهد که باید در Logic Audit شناسایی شو
- [x] **مرحله 29: تعریف فلسفه و معماری ماژول Scan (Phase 5) و تمایز آن از Verify (Phase 4)** — این بخش فلسفه کلی ماژول Scan را تعریف می‌کند: scan ≠ verify، scan قوی‌تر از verify است، و چهار پایه اصلی (پوشش ریز تا درشت، تغییر-آگاهی، رفتار-محوری، logic awareness) را مشخص می‌کند. هدف نهایی کشف و ساخت تمام تسک‌های واقعاً لازم (features جدید/ناقص، bugs ساختاری/منطقی، features قدیمی، componentهای ن
- [x] **مرحله 30: فاز ۱ — Comprehensive Inventory + Purpose Extraction** — این بخش شامل دو ماژول جدید است: comprehensive_inventory.py برای جمع‌آوری ۱۲ لایه از inventory (فایل‌ها، endpoints، UI elements، DB schema، env vars، configs، dependencies، scripts، cron/scheduled، routes، notification calls، UI options/settings) و purpose_extractor.py برای استخراج purpose هر آیتم in
- [x] **مرحله 31: فاز ۲ — Stale Detection + Feature Inventory Panel** — این بخش شامل پیاده‌سازی کامل تشخیص اجزای قدیمی (Stale) در دو دسته Structural (۸ نوع) و Semantic (۵ نوع)، تولید مستندات AI برای هر گزینه UI، ایجاد پنل Feature Inventory در صفحه oversight، و تولید Task برای هر آیتم قدیمی است. فایل‌های جدید: backend/app/services/scan_v5/stale_detector.py. فایل‌های موجو
- [x] **مرحله 32: پیاده‌سازی تشخیص دلتا، وابستگی دوطرفه و تحلیل تاثیر منطقی در اسکن v5** — این مرحله شامل پیاده‌سازی کامل فاز ۳ است: ذخیره state قبلی در WatchedProject، تشخیص ۶ نوع تغییر (add/remove/modify/rename/move/signature-change)، تحلیل وابستگی دوطرفه (import-based و logical) در ماژول جدید dependency_analyzer.py، تحلیل تاثیر منطقی با AI روی تغییرات و dependents، و تولید task برای فا
- [x] **مرحله 33: فاز ۴: Runtime Discovery + Outcome + Inspector Session — پیاده‌سازی کامل Inspector Tab Integration و Session Management** — این بخش شامل چهار زیربخش اصلی است: (۱) Runtime Discovery با ماژول جدید runtime_discovery.py که routes زنده، 404ها، endpoints فراخوانی‌شده، UI features و recent commits را کشف می‌کند. (۲) Outcome Data Collection برای انواع پروژه (Trading, AI/Chat, Web service, Scheduling, Notification). (۳) Scan Insp
- [x] **مرحله 34: فاز ۵: Logical Audit — تشخیص ناهماهنگی منطقی، ضدالگوها و اثربخشی خروجی** — این فاز شامل ۵ زیربخش است: (A) تشخیص انسجام زنجیره‌های پردازش (Pipeline Coherence)، (B) تشخیص ضدالگوهای منطقی (Anti-pattern)، (C) کشف نیازمندی‌های پنهان (Hidden Requirements)، (D) ممیزی اثربخشی مبتنی بر خروجی (Outcome-based Effectiveness)، و (E) تولید تسک‌های `logic_audit` با AC outcome-oriented. خا
- [x] **مرحله 35: فاز ۶ — Notification System Audit: بررسی و بهینه‌سازی سیستم اطلاع‌رسانی (R12)** — این مرحله شامل ممیزی کامل تمام notification‌های موجود در کد (notify_event calls)، ایجاد inventory از آن‌ها، بررسی انسجام و کامل بودن caption‌ها، تنظیم silent/sound مناسب، بررسی attachments، جلوگیری از spam، شناسایی notification‌های قدیمی یا گمشده، و ارائه پیشنهادات ارتقا برای notification scan_compl
- [x] **مرحله 36: فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)** — این فاز شامل ۶ زیربخش (۷-A تا ۷-F) است که همگی برای بهبود کیفیت پرامپت‌ها و چک‌لیست‌ها در هر دو مسیر manual و auto طراحی شده‌اند. تغییرات شامل: ساختار غنی AC با ۷ فیلد جدید، ساختار غنی task_step با ۶ فیلد، اضافه شدن حالت هوشمند چک‌لیست (auto/always/never)، به‌روزرسانی قالب‌های پرامپت در oversight_st
- [x] **مرحله 37: فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration** — این بخش شامل ۴ زیربخش است: (۸-A) افزودن task_steps به auto-tasks در oversight_service.py با دو mode 'always' و 'auto'، (۸-B) قالب notification تلگرام برای auto-scan task با caption و attachments مشخص، (۸-C) اضافه کردن فیلدهای silent default (auto_task_notify_sound و scan_notify_sound) به WatchedProj
- [x] **مرحله 38: فاز ۹ — UI Redesign (R2, R8): بازطراحی کامل UI با ۴ تب، گزینه‌های جدید و AI explanation** — این بخش شامل بازطراحی کامل UI Oversight با ۴ تب (Coverage, Intelligence, Lifecycle, Notifications) به‌جای ۳ تب قبلی است. تغییرات شامل: بازنگری scan_depth modes (اضافه شدن mode‌های balanced و ultra)، بازنگری criteria_weights (preset selector + sliders در details)، بازنگری Smart Task Lifecycle با وضعی
- [x] **مرحله 39: فاز ۱۰: Meta-validation — تبدیل پرامپت به task قابل verify و شناسایی باگ‌های verify** — این فاز شامل تبدیل کل پرامپت (فازهای ۱-۹) به یک task اجرایی با ACهای measurable، ایجاد حلقه iteration بین پیاده‌سازی و verify، و شناسایی باگ‌های verify (false-positive/negative) است. خروجی نهایی یک پرامپت با ۱۰ task_step است که هر step دارای behavior_observable و verification_hint است. خارج از scope
- [x] **مرحله 40: فاز ۱ — Comprehensive Inventory + Purpose (Round 1 پایه)** — این بخش اولین فاز از Round 1 است و شامل ایجاد یک فهرست جامع از تمام اجزای پروژه (Inventory) به همراه تعریف هدف (Purpose) هر جزء می‌شود. این فاز پایه‌ای برای تمام تحلیل‌های بعدی است و باید تمام فایل‌ها، کلاس‌ها، سرویس‌ها و کامپوننت‌های UI را پوشش دهد. نکته حیاتی: این فاز صرفاً مستندسازی و فهرست‌بردار
- [x] **مرحله 41: رفع ۶ گپ بنیادی + ۲ بهبود اضافه در verify v2 برای کاهش false negative از ۴۰٪ به صفر** — این بخش شامل تحلیل و رفع ۶ گپ بنیادی (structural gaps) و ۲ بهبود اضافه در لایه‌های زیرین verify است. پایه ۵ فاز قبلی حفظ می‌شود و فقط لایه‌های زیرین تقویت می‌شوند. این بخش صرفاً تعریف گپ‌ها و بهبودهاست و شامل پیاده‌سازی نمی‌شود. خروجی این بخش یک لیست شماره‌دار با ۸ آیتم (۶ گپ + ۲ بهبود) است که باید 
- [x] **مرحله 42: ساخت ماژول context_builder برای جمع‌آوری و ساخت VerifyContext در فرآیند verify** — این بخش ایجاد یک ماژول جدید به نام backend/app/services/verify_runtime/context_builder.py را مشخص می‌کند که شامل یک dataclass به نام VerifyContext و یک تابع async به نام build_verify_context است. scope شامل: تعریف کامل فیلدهای VerifyContext با caps مشخص، پیاده‌سازی تابع build_verify_context که caps 
- [x] **مرحله 43: پیاده‌سازی ماژول code_content_searcher برای جستجوی محتوای فایل به جای commit diff** — این بخش شامل ایجاد ماژول جدید backend/app/services/verify_runtime/code_content_searcher.py با سه تابع async و یک تابع همزمان است. توابع fetch_file_content (دریافت محتوای فایل از GitHub API با cache و محدودیت حجم)، grep_token_in_files (جستجوی regex در محتوای فایل‌ها با context lines و cap per file)، 
- [x] **مرحله 44: AC matching با file content به‌جای basename — چهار فاز اجرایی** — این بخش یک orchestrator جدید به نام analyze_acs_with_content_grep تعریف می‌کند که چهار فاز (A→B→C→D) را به‌ترتیب اجرا می‌کند. هر فاز یک تابع async مجزا دارد و در صورت بازگشت done قطعی، early-exit رخ می‌دهد. منطق فازها تغییر نمی‌کند، فقط نام‌گذاری مشخص‌تر می‌شود. فاز A (basename match) و فاز B (conte
- [x] **مرحله 45: پیاده‌سازی ماژول iterative_orchestrator با سه مرحله اعتبارسنجی تدریجی** — این بخش شامل پیاده‌سازی ماژول جدید `iterative_orchestrator.py` با سه iteration است: (1) استاندارد با ۴ probe و آستانه 0.8، (2) aggressive content grep با آستانه 0.7، (3) strong model escalation با زنجیره مدل‌های gpt-4o → claude-opus-4-7 → claude-sonnet-4-6 → fallback. خروجی نهایی یک `ProbeResult` ag
- [x] **مرحله 46: پیاده‌سازی بهبودهای ۷، ۸ و ۹: کش per-AC، حالت رهگیری و متمرکزسازی VerifyConfig** — این بخش شامل سه بهبود مجزا اما مرتبط است: (۱) کش وضعیت تأیید برای هر Acceptance Criteria با هش و checksum فایل برای جلوگیری از تأیید مجدد، (۲) حالت رهگیری/مشاهده‌پذیری کامل فرآیند تأیید با ذخیره trace و endpoint جدید، (۳) متمرکزسازی تمام تنظیمات تأیید در یک کلاس VerifyConfig با endpoint REST. هر سه 
- [x] **مرحله 47: اجرای گام‌های تکراری تأیید (Iterative Verify) با کش و طبقه‌بندی AC** — این بخش منطق کامل حلقه تأیید تکراری برای هر AC (Acceptance Criterion) را مشخص می‌کند: بارگذاری پیکربندی، ساخت زمینه، طبقه‌بندی AC، بررسی کش، اجرای حداکثر ۳ دور (iteration) با استراتژی‌های فزاینده (grep، vision، playwright، مدل قوی)، تجمیع رأی‌ها، به‌روزرسانی کش، و ثبت جزئیات در verify_trace. بخش‌های
- [x] **مرحله 48: ایجاد و بازنویسی فایل‌های سرویس verify_runtime و oversight برای پشتیبانی از verify_v6** — این بخش شامل ایجاد ۴ فایل جدید در backend/app/services/verify_runtime/ (context_builder, code_content_searcher, iterative_orchestrator, ac_cache_service)، بازنویسی code_aware_verifier با فازهای A→B→C→D، تغییرات در oversight_verifier (افزودن _classify_step_for_probe با ۱۰ قاعده و flag verify_v6)، به‌
- [x] **مرحله 49: تعریف ۱۲ معیار موفقیت (AC) برای Verify v6 با meta-test سختگیرانه** — این بخش ۱۲ Acceptance Criteria (AC) مشخص و قابل grep را برای قابلیت Verify v6 تعریف می‌کند. هر AC یک فایل/کلاس/تابع/endpoint خاص را هدف می‌گیرد. معیار سختگیرانه این است که وقتی Verify v6 روی این bug اجرا شود، باید ≥۱۱ از ۱۲ AC را با confidence ≥ 0.8 پاس کند. این بخش صرفاً معیارها را لیست می‌کند و دس
- [x] **مرحله 50: پیاده‌سازی Edge Cases نسخه v2 برای Oversight Verifier** — این بخش شامل ۱۴ مورد از edge cases نسخه v2 است که باید در سرویس oversight_verifier پیاده‌سازی شوند. موارد شامل مدیریت rate limit گیت‌هاب، فایل‌های بزرگ/باینری، fallback منطق، پشتیبانی از چندزبانگی، کنترل حافظه، backward compatibility، A/B testing، race condition در cache invalidation، عدم دسترسی به 
- [x] **مرحله 51: تعیین محدوده خارج از اسکوپ و ترتیب اجرای v2 با ۸ chunk** — این بخش دو بخش مجزا دارد: (۱) فهرست مواردی که خارج از اسکوپ پروژه هستند و نباید تغییر داده شوند (شامل Playwright probe، vision probe، ML classification، تشخیص multi-language source code، AST-level analysis، distributed cache، WebSocket live progress). (۲) اشاره به ترتیب اجرای نسخه دوم (v2) با ۸ chun
- [x] **مرحله 52: فاز A — Task Type Classifier: تشخیص خودکار نوع تسک backend/frontend/fullstack/infra/docs/test/mixed** — این بخش شامل پیاده‌سازی تابع _classify_task_type در iterative_orchestrator.py است که بر اساس prompt + target_files + AC نوع تسک را با regex/heuristic تشخیص می‌دهد. شامل ۷ نوع pure_backend, pure_frontend, fullstack, infra, docs_only, test_only, mixed_unknown. خروجی تابع یک رشته است. تشخیص بدون AI انج

---

# 🔹 مرحله 1: ایجاد لایه Runtime Verification برای اجرای Probe واقعی و جمع‌آوری شواهد اجرایی

**Scope:** این بخش طراحی یک لایه جدید runtime verification را مشخص می‌کند که به جای خواندن استاتیک کد، برای هر Acceptance Criterion (AC) رفتاری یک probe واقعی اجرا می‌کند. شامل سه نوع probe: Playwright برای UI، HTTP برای API، pytest برای backend logic. خروجی هر probe شواهد runtime مانند screenshot، response JSON و pytest output است که به verify ارسال می‌شود. این لایه false-positive و false-negative را حذف می‌کند. خارج از scope: پیاده‌سازی جزئی probeها، طراحی دیتابیس، و logic تصمیم‌گیری verify.
**Key terms:** RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult, Playwright, HTTP, pytest, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/oversight_verifier.py

**بخش مربوط از متن کاربر:**
```
verify فعلی فقط کد را می‌خواند و حدس می‌زند؛ این layer جدید برای هر AC که ماهیتش رفتاری است، **یک probe واقعی** اجرا می‌کند (Playwright برای UI، HTTP برای API، pytest برای backend logic) و **شواهد runtime** (screenshot، response JSON، pytest output) به verify می‌دهد. در نتیجه verify دیگر false-positive («نشده» در حالی که شده) و false-negative («شده» در حالی که نشده) نمی‌دهد.
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد لایه Runtime Verification با سه نوع Probe واقعی

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/inspector_probe.py:243-304` — `run_inspector_pro`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک طراحی و پیاده‌سازی یک لایه جدید runtime verification را مشخص می‌کند که به جای خواندن استاتیک کد، برای هر Acceptance Criterion (AC) رفتاری یک probe واقعی اجرا می‌کند. شامل سه نوع probe: Playwright برای UI، HTTP برای API، pytest برای backend logic. خروجی هر probe شواهد runtime مانند screenshot، response JSON و pytest output است که به verify ارسال می‌شود. این لایه false-positive و false-negative را حذف می‌کند. خارج از scope: پیاده‌سازی جزئی probeها، طراحی دیتابیس، و logic تصمیم‌گیری verify.

--- بخش مربوط از درخواست اصلی کاربر ---
verify فعلی فقط کد را می‌خواند و حدس می‌زند؛ این layer جدید برای هر AC که ماهیتش رفتاری است، **یک probe واقعی** اجرا می‌کند (Playwright برای UI، HTTP برای API، pytest برای backend logic) و **شواهد runtime** (screenshot، response JSON، pytest output) به verify می‌دهد. در نتیجه verify دیگر false-positive («نشده» در حالی که شده) و false-negative («شده» در حالی که نشده) نمی‌دهد.

--- کلیدواژه‌ها ---
RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult, Playwright, HTTP, pytest, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/oversight_verifier.py

تحلیل کد واقعی: فایل `backend/app/services/verify_runtime/inspector_probe.py` (خطوط 243-304) تابع `run_inspector_probe` را دارد که یک probe UI با Playwright اجرا می‌کند و خروجی `RuntimeProbeResult` برمی‌گرداند. فایل `backend/app/services/verify_runtime/vision_helper.py` (خطوط 22-61) تحلیل screenshot را با fallback chain انجام می‌دهد. فایل `backend/app/services/oversight_verifier.py` (خطوط 72-119) تابع `_classify_step_for_probe` را دارد که AC را به ۷ دسته طبقه‌بندی می‌کند. فایل `backend/app/services/verify_runtime/base.py` شامل کلاس‌های `ProbeContext` و `RuntimeProbeResult` است. فایل `backend/app/services/verify_runtime/runner.py` orchestrator اصلی probeهاست.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل `backend/app/services/verify_runtime/runner.py` یک تابع جدید `run_runtime_probe` ایجاد کن که بر اساس `verify_method` (ui_interaction, api_response, backend_test) probe مناسب را انتخاب کند.
2. در `backend/app/services/verify_runtime/inspector_probe.py` تابع `run_inspector_probe` را refactor کن تا از `ProbeContext` و `RuntimeProbeResult` استفاده کند.
3. در `backend/app/services/verify_runtime/vision_helper.py` تابع `analyze_screenshot` را بهبود بده تا `feature_present` را دقیق‌تر تشخیص دهد.
4. در `backend/app/services/oversight_verifier.py` تابع `_classify_step_for_probe` را گسترش بده تا ۱۰ قاعده کامل را پوشش دهد.
5. یک فایل جدید `backend/app/services/verify_runtime/api_probe.py` برای HTTP probe ایجاد کن.
6. یک فایل جدید `backend/app/services/verify_runtime/test_probe.py` برای pytest probe ایجاد کن.
7. در `backend/app/services/verify_runtime/__init__.py` همه probeها را export کن.
8. در `backend/app/services/oversight_verifier.py` تابع `verify_v6` را به‌روز کن تا از `run_runtime_probe` استفاده کند.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 2: یکپارچه‌سازی Stage 5: نقطهٔ اتصال verify فعلی با AI و PDF و UI

**Scope:** این بخش موقعیت دقیق فایل‌های مرتبط با Stage 5 (یکپارچه‌سازی) را مشخص می‌کند. شامل: oversight_verifier.py (نقطهٔ یکپارچه‌سازی)، oversight_strong_prompt.py (تولید AC)، oversight_service.py (ایجاد تسک)، oversight_verify_pdf.py (PDF)، frontend page.tsx (نمایش)، و پوشه‌های جدید verify_runtime/ و verify_evidence/. خارج از scope: پیاده‌سازی Stage 2/4/7/8 (فقط اشاره به نقاط ورودشان دارد). نکته حیاتی: این بخش صرفاً نقشهٔ راه فایل‌هاست و دستور اجرایی ندارد.
**Key terms:** backend/app/services/oversight_verifier.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verify_pdf.py, frontend/src/app/oversight/page.tsx, frontend/src/app/oversight/page.tsx, backend/app/services/verify_runtime/, storage/verify_evidence/

**بخش مربوط از متن کاربر:**
```
## 📌 موقعیت دقیق در پروژه (فایل‌های مرتبط — مجری باید deep-read کند)
- `backend/app/services/oversight_verifier.py` — verify فعلی (grep + AI)
  → نقطهٔ یکپارچه‌سازی Stage 5
- `backend/app/services/oversight_strong_prompt.py` — تولید AC
  → نقطهٔ Stage 2 (AI verify_plan)
- `backend/app/services/oversight_service.py` — OversightTask + create_task
  → Stage 1 (schema migration)
- `backend/app/services/oversight_verify_pdf.py` — PDF فعلی
  → Stage 7 (embed evidence)
- `frontend/src/app/oversight/page.tsx` — UI تسک
  → Stage 8 (نمایش evidence)
- `frontend/src/app/projects/[id]/page.tsx` یا settings — تنظیمات watched
  → Stage 4 (base URLs)
- پوشهٔ جدید: `backend/app/services/verify_runtime/` — probe runners
- پوشهٔ جدید: `storage/verify_evidence/` — ذخیرهٔ screenshots/JSONs
```

## 🎯 هدف (خلاصه ساختاریافته)
یکپارچه‌سازی Stage 5: نقطه اتصال verify با AI، PDF و UI

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک به یکپارچه‌سازی Stage 5 (نقطه اتصال verify فعلی با AI، PDF و UI) می‌پردازد. کاربر درخواست خود را با اولویت critical و نوع refactor ثبت کرده است. متن خام کاربر شامل موقعیت دقیق فایل‌های مرتبط است: `backend/app/services/oversight_verifier.py` (نقطه یکپارچه‌سازی)، `backend/app/services/oversight_strong_prompt.py` (تولید AC)، `backend/app/services/oversight_service.py` (ایجاد تسک)، `backend/app/services/oversight_verify_pdf.py` (PDF)، `frontend/src/app/oversight/page.tsx` (نمایش)، `frontend/src/app/projects/[id]/page.tsx` (تنظیمات watched)، پوشه جدید `backend/app/services/verify_runtime/` (probe runners) و `storage/verify_evidence/` (ذخیره screenshots/JSONs). خارج از scope: پیاده‌سازی Stage 2/4/7/8 (فقط اشاره به نقاط ورودشان دارد). نکته حیاتی: این بخش صرفاً نقشه راه فایل‌هاست و دستور اجرایی ندارد. کلیدواژه‌ها: backend/app/services/oversight_verifier.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verify_pdf.py, frontend/src/app/oversight/page.tsx, backend/app/services/verify_runtime/, storage/verify_evidence/. تحلیل کد واقعی: در `oversight_verifier.py` (خطوط 1-50) تابع `verify_task` با grep+AI کار می‌کند و باید به Stage 5 متصل شود. `oversight_strong_prompt.py` (خطوط 158-420) تابع `build_strong_prompt` ACهای ساختاریافته تولید می‌کند. `oversight_service.py` (خطوط 294-464) کلاس `OversightTask` با فیلدهای `acceptance_criteria` و `verification_status` برای Stage 1 آماده است. `oversight_verify_pdf.py` (خطوط 1-30) PDF فعلی را تولید می‌کند. `frontend/src/app/oversight/page.tsx` (خطوط 1-50) UI تسک را نمایش می‌دهد. پوشه `verify_runtime/` شامل probe runners مانند `code_aware_verifier.py` و `inspector_probe.py` است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در `backend/app/services/oversight_verifier.py` (خطوط 1-50)، تابع `verify_task` را بازبینی کن تا از ACهای ساختاریافته (`acceptance_criteria` با `verify_method` و `verify_plan`) استفاده کند. 2. در `backend/app/services/oversight_strong_prompt.py` (خطوط 158-420)، تابع `build_strong_prompt` را طوری اصلاح کن که ACهای dict با فیلدهای `behavior`, `acceptance_signal`, `business_intent` را پشتیبانی کند. 3. در `backend/app/services/oversight_service.py` (خطوط 294-464)، کلاس `OversightTask` را با فیلد `verify_v6_config` (خط 285) هماهنگ کن. 4. در `backend/app/services/oversight_verify_pdf.py` (خطوط 1-30)، تابع `generate_pdf` را برای جاسازی شواهد (screenshots/JSONs از `storage/verify_evidence/`) به‌روز کن. 5. در `frontend/src/app/oversight/page.tsx` (خطوط 1-50)، کامپوننت `TaskCard` را برای نمایش `verify_method` و `verify_plan` توسعه بده. 6. پوشه `backend/app/services/verify_runtime/` را با probe runners (`code_aware_verifier.py`, `inspector_probe.py`) یکپارچه کن. 7. پوشه `storage/verify_evidence/` را برای ذخیره screenshots/JSONs ایجاد کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 3: تبدیل ساختار AC از رشته به struct با verify_method و verify_plan

**Scope:** این بخش طراحی مفهومی جدیدی برای ساختار Acceptance Criteria (AC) ارائه می‌دهد که از یک رشته ساده به یک struct با فیلدهای text, verify_method, verify_plan تبدیل می‌شود. شامل پنج نوع verify_method (static, ui_interaction, api_response, backend_test, manual_only) و جایگزینی شواهد grep با runtime evidence (screenshot, JSON, pytest log) است. این بخش صرفاً مفهوم‌پردازی است و مراحل اجرایی بعداً در ادامه درخواست ذکر شده‌اند.
**Key terms:** verify_method, verify_plan, static, ui_interaction, api_response, backend_test, manual_only, runtime evidence, Playwright headless, pytest subprocess, grep, screenshot, JSON, pytest log

**بخش مربوط از متن کاربر:**
```
## 🧠 معماری کلی (قبل از کد، این را بفهم)
### concept جدید: «verify_method» برای هر AC
هر AC الان فقط یک رشته است:
"وقتی روی دکمه X کلیک می‌کنم، مدال باز شود"

بعد از این feature، هر AC یک struct است:
```json
{
  "text": "وقتی روی دکمه X کلیک می‌کنم، مدال باز شود",
  "verify_method": "ui_interaction",
  "verify_plan": {
    "ui_steps": [
      {"action": "navigate", "url": "/oversight"},
      {"action": "wait_for_load_state", "state": "networkidle"},
      {"action": "click", "selector": "[data-testid='btn-x']"},
      {"action": "wait_for_selector", "selector": "[role='dialog']", "timeout_ms": 3000},
      {"action": "assert_visible", "selector": "[role='dialog']"}
    ]
  }
}
```
پنج نوع verify_method
static — کد grep (همان verify فعلی) — برای ACی مثل «فایل X وجود دارد»
ui_interaction — Playwright headless — برای ACی مثل «دکمه باز می‌شود»
api_response — HTTP request — برای ACی مثل «endpoint Y → 200 با field Z»
backend_test — pytest subprocess — برای ACی مثل «تست T pass شود»
manual_only — نمی‌توان خودکار تأیید کرد — verify فقط می‌گوید «نیاز به بازبینی دستی»
چه چیزی جایگزین شواهد grep می‌شود
verify فعلی به AI می‌گفت: «این کد را ببین، AC پاس می‌شود؟»
verify جدید می‌گوید: «این runtime evidence را ببین (screenshot، JSON، pytest log) — AC پاس می‌شود؟»

🪜 مراحل اجرایی (دقیقاً به این ترتیب — قبلی پیش‌نیاز بعدی است)
```

json
{
  "text": "وقتی روی دکمه X کلیک می‌کنم، مدال باز شود",
  "verify_method": "ui_interaction",
  "verify_plan": {
    "ui_steps": [
      {"action": "navigate", "url": "/oversight"},
      {"action": "wait_for_load_state", "state": "networkidle"},
      {"action": "click", "selector": "[data-testid='btn-x']"},
      {"action": "wait_for_selector", "selector": "[role='dialog']", "timeout_ms": 3000},
      {"action": "assert_visible", "selector": "[role='dialog']"}
    ]
  }
}
```
پنج نوع verify_method
static — کد grep (همان verify فعلی) — برای ACی مثل «فایل X وجود دارد»
ui_interaction — Playwright headless — برای ACی مثل «دکمه باز می‌شود»
api_response — HTTP request — برای ACی مثل «endpoint Y → 200 با field Z»
backend_test — pytest subprocess — برای ACی مثل «تست T pass شود»
manual_only — نمی‌توان خودکار تأیید کرد — verify فقط می‌گوید «نیاز به بازبینی دستی»
چه چیزی جایگزین شواهد grep می‌شود
verify فعلی به AI می‌گفت: «این کد را ببین، AC پاس می‌شود؟»
verify جدید می‌گوید: «این runtime evidence را ببین (screenshot، JSON، pytest log) — AC پاس می‌شود؟»

🪜 مراحل اجرایی (دقیقاً به این ترتیب — قبلی پیش‌نیاز بعدی است)

--- کلیدواژه‌ها ---
verify_method, verify_plan, static, ui_interaction, api_response, backend_test, manual_only, runtime evidence, Playwright headless, pytest subprocess, grep, screenshot, JSON, pytest log
```

## 🎯 هدف (خلاصه ساختاریافته)
تبدیل AC از رشته به struct با verify_method و verify_plan

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/ac_schema.py:1-50` — `ACSchema` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل باید struct جدید AC را تعریف کند.
  ```python
  # این فایل در deep context موجود نیست — بر اساس ساختار سطحی پروژه
  ```
- `backend/app/services/verify_runtime/runner.py:1-100` — `Runner` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. این فایل باید dispatch به probeهای مختلف را پیاده‌سازی کند.
  ```python
  # این فایل در deep context موجود نیست — بر اساس ساختار سطحی پروژه
  ```
- `backend/app/services/oversight_service.py:1-50` — `OversightTask` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. کلاس OversightTask باید فیلد acceptance_criteria را به‌روزرسانی کند.
  ```python
  # این فایل در deep context موجود نیست — بر اساس ساختار سطحی پروژه
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/verify_runtime/code_aware_verifier.py` — این فایل verify فعلی را انجام می‌دهد و باید برای استفاده از runtime

## 🔍 Context و وضعیت فعلی
این تسک یک refactor ساختاری در سیستم Acceptance Criteria (AC) پروژه است. کاربر درخواست تبدیل AC از یک رشته ساده به یک struct با فیلدهای text, verify_method, verify_plan را دارد. پنج نوع verify_method تعریف شده: static (کد grep فعلی)، ui_interaction (Playwright headless)، api_response (HTTP request)، backend_test (pytest subprocess)، manual_only (نیاز به بازبینی دستی). همچنین شواهد grep فعلی باید با runtime evidence (screenshot, JSON, pytest log) جایگزین شود. این تغییر روی فایل‌های backend/app/services/oversight_service.py (احتمالاً کلاس OversightTask)، backend/app/services/verify_runtime/ (کل پکیج verify_runtime شامل runner.py, code_aware_verifier.py, iterative_orchestrator.py, ac_schema.py, ac_enricher.py, context_builder.py, ui_probe.py, api_probe.py, test_probe.py, static_probe.py, manual_probe.py) و backend/app/services/oversight_verifier.py تأثیر می‌گذارد. کلیدواژه‌های اصلی: verify_method, verify_plan, static, ui_interaction, api_response, backend_test, manual_only, runtime evidence, Playwright headless, pytest subprocess, grep, screenshot, JSON, pytest log.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد struct جدید برای AC در فایل backend/app/services/verify_runtime/ac_schema.py با فیلدهای text (str), verify_method (Literal['static','ui_interaction','api_response','backend_test','manual_only']), verify_plan (dict). 2. به‌روزرسانی کلاس OversightTask در backend/app/services/oversight_service.py برای پشتیبانی از فیلد acceptance_criteria به‌صورت لیستی از struct جدید. 3. تغییر تابع verify در backend/app/services/verify_runtime/runner.py برای خواندن verify_method و dispatch به probe مناسب. 4. به‌روزرسانی code_aware_verifier.py برای استفاده از runtime evidence به‌جای grep-only. 5. ایجاد/به‌روزرسانی probeهای ui_probe.py (Playwright headless), api_probe.py (HTTP request), test_probe.py (pytest subprocess), static_probe.py (grep فعلی), manual_probe.py (بازبینی دستی). 6. به‌روزرسانی ac_enricher.py برای تولید verify_plan از متن AC با AI. 7. به‌روزرسانی context_builder.py برای ارسال runtime evidence به AI. 8. به‌روزرسانی oversight_verifier.py برای استفاده از verify_method جدید.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 4: Schema migration برای AC ساختاریافته در OversightTask

**Scope:** این مرحله شامل تغییر نوع فیلد acceptance_criteria در OversightTask از List[str] به List[Union[str, Dict]]، ایجاد helper _normalize_ac برای تبدیل یکتا به ساختار {text, verify_method, verify_plan, evidence_history}، افزودن فیلدهای verify_method و verify_plan به هر step در task_steps، و اجرای migration یکبار در startup روی همه task‌های موجود است. backward compatibility با پیش‌فرض verify_method="static" برای ACهای قدیمی str حفظ می‌شود. فایل‌های درگیر: oversight_service.py, oversight_strong_prompt.py, oversight_verifier.py, frontend/src/app/oversight/page.tsx. تست‌های واحد برای دو سناریو (AC string قدیمی و AC dict جدید) نیز شامل است.
**Key terms:** oversight_service.py, oversight_strong_prompt.py, oversight_verifier.py, frontend/src/app/oversight/page.tsx, OversightTask, acceptance_criteria, _normalize_ac, verify_method, verify_plan, evidence_history, _load_tasks

**بخش مربوط از متن کاربر:**
```
Stage 1 — Schema migration برای AC ساختاریافته
فایل‌ها: oversight_service.py, oversight_strong_prompt.py,
oversight_verifier.py, frontend/src/app/oversight/page.tsx

کاری که می‌شود:

OversightTask.acceptance_criteria از List[str] به List[Union[str, Dict]] تبدیل
helper _normalize_ac(ac) -> Dict[str, Any] که هم str هم dict را به
ساختار {text, verify_method, verify_plan, evidence_history} تبدیل می‌کند
backward compat: اگر AC قدیمی str است، verify_method="static" پیش‌فرض
در task_steps، هر step هم باید verify_method و verify_plan داشته باشد
migration یک‌بار در startup: روی همهٔ task های موجود _normalize_ac اجرا
شود (loop در _load_tasks)
Tests:

یک task با AC string قدیمی → بعد از load به ساختار جدید تبدیل شود
یک task با AC dict جدید → بدون تغییر باقی بماند
```

## 🎯 هدف (خلاصه ساختاریافته)
Schema migration AC ساختاریافته در OversightTask

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:1-50` — `OversightTask`
  ```python
  class OversightTask(BaseModel):
      id: str
      watched_id: Optional[str] = None
      project_full_name: str = ""
      title: str
      prompt: str
      raw_idea: str = ""
      type
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به Stage 1 — Schema migration برای AC ساختاریافته است. کاربر درخواست تغییر نوع فیلد acceptance_criteria در OversightTask از List[str] به List[Union[str, Dict]] را دارد. این تغییر شامل ایجاد helper _normalize_ac برای تبدیل یکتا به ساختار {text, verify_method, verify_plan, evidence_history}، افزودن فیلدهای verify_method و verify_plan به هر step در task_steps، و اجرای migration یکبار در startup روی همه task‌های موجود است. backward compatibility با پیش‌فرض verify_method="static" برای ACهای قدیمی str حفظ می‌شود. فایل‌های درگیر: oversight_service.py, oversight_strong_prompt.py, oversight_verifier.py, frontend/src/app/oversight/page.tsx. تست‌های واحد برای دو سناریو (AC string قدیمی و AC dict جدید) نیز شامل است.

شواهد در کد واقعی:
- در frontend/src/app/oversight/page.tsx خط 197: `acceptance_criteria?: Array<string | AcceptanceCriterion>;` — اینترفیس Task قبلاً از Union پشتیبانی می‌کند اما backend مدل (OversightTask) هنوز List[str] است.
- در backend/app/api/routes/oversight.py خط 104: `acceptance_criteria: Optional[List[str]] = None` — در TaskCreate هنوز List[str] است.
- در backend/app/api/routes/oversight.py خط 121: `acceptance_criteria: Optional[List[str]] = None` — در SimilarityCheckRequest.
- در backend/app/api/routes/oversight.py خط 142: `candidate_acceptance_criteria: Optional[List[str]] = None` — در MergePreviewRequest.
- در backend/app/api/routes/oversight.py خط 148: `candidate_acceptance_criteria: Optional[List[str]] = None` — در MergeApplyRequest.
- در frontend/src/app/oversight/page.tsx خط 156-163: تابع `acText` که هر دو نوع string و dict را پشتیبانی می‌کند.
- در frontend/src/app/oversight/page.tsx خط 547-553: در `buildSearchHaystack` از هر دو نوع پشتیبانی می‌شود.

کلیدواژه‌ها: oversight_service.py, oversight_strong_prompt.py, oversight_verifier.py, frontend/src/app/oversight/page.tsx, OversightTask, acceptance_criteria, _normalize_ac, verify_method, verify_plan, evidence_history, _load_tasks

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در oversight_service.py: تغییر نوع فیلد acceptance_criteria در کلاس OversightTask از List[str] به List[Union[str, Dict]]
2. در oversight_service.py: افزودن متد استاتیک _normalize_ac(ac) -> Dict که:
   - اگر ac str باشد: return {'text': ac, 'verify_method': 'static', 'verify_plan': None, 'evidence_history': None}
   - اگر ac dict باشد: return با پر کردن پیش‌فرض‌ها
3. در oversight_service.py: در متد _load_tasks، بعد از بارگذاری هر task، روی acceptance_criteria آن _normalize_ac را اعمال کند
4. در oversight_strong_prompt.py: به‌روزرسانی پرامپت‌ها برای تولید AC ساختاریافته
5. در oversight_verifier.py: به‌روزرسانی منطق verify برای خواندن verify_method از AC dict
6. در frontend/src/app/oversight/page.tsx: به‌روزرسانی تابع acText و buildSearchHaystack برای پشتیبانی کامل از dict جدید
7. افزودن تست‌های واحد برای دو سناریو: AC string قدیمی و AC dict جدید

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 5: گسترش system prompt برای تولید verify_plan توسط AI

**Scope:** این مرحله system prompt در فایل oversight_strong_prompt.py را گسترش می‌دهد تا AI علاوه بر AC، برای هر AC یک verify_method و در صورت نیاز verify_plan تولید کند. چارچوب تصمیم‌گیری بر اساس کلمات کلیدی AC تعریف شده است (ui_interaction, api_response, backend_test, static, manual_only). یک نمونه JSON (few-shot) برای هر نوع به AI داده می‌شود. اگر AI نتواند plan بدهد، fallback به static است. فایل‌های مرتبط: oversight_strong_prompt.py و oversight_service.py.
**Key terms:** oversight_strong_prompt.py, oversight_service.py, _idea_to_prompt_multi_pass, verify_method, verify_plan, ui_interaction, api_response, backend_test, static, manual_only

**بخش مربوط از متن کاربر:**
```
Stage 2 — تولید verify_plan توسط AI
فایل‌ها: oversight_strong_prompt.py, oversight_service.py
(در _idea_to_prompt_multi_pass), oversight_service.py (در system prompt)

کاری که می‌شود:

system prompt در idea_to_prompt گسترش یابد: AI علاوه بر AC، برای هر AC
باید verify_method و در صورت نیاز verify_plan تولید کند
چارچوب تصمیم برای AI:
AC شامل «کلیک، نمایش، صفحه، مودال، input» → ui_interaction
AC شامل «endpoint، API، status code، response» → api_response
AC شامل «test، pytest، unit test» → backend_test
AC شامل «فایل X وجود دارد، imported است» → static
AC مبهم یا ذهنی (مثل «ظاهر زیبا») → manual_only
prompt یک نمونهٔ کامل JSON برای هر نوع به AI می‌دهد (few-shot)
اگر AI نتوانست plan بدهد → fallback به static
Tests:

یک ایدهٔ UI («دکمه login کار کند») → AC با ui_interaction + ui_steps
یک ایدهٔ API («endpoint /users 200 بدهد») → AC با api_response
یک ایدهٔ ذهنی («طراحی شیک‌تر») → AC با manual_only
```

## 🎯 هدف (خلاصه ساختاریافته)
گسترش system prompt برای تولید verify_plan توسط AI در oversight_strong_prompt.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_strong_prompt.py:158-420` — `build_strong`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک به گسترش system prompt در فایل oversight_strong_prompt.py (backend/app/services/oversight_strong_prompt.py) می‌پردازد تا AI علاوه بر Acceptance Criteria (AC)، برای هر AC یک verify_method و در صورت نیاز verify_plan تولید کند. چارچوب تصمیم‌گیری بر اساس کلمات کلیدی AC تعریف شده است: ui_interaction (برای AC شامل «کلیک، نمایش، صفحه، مودال، input»)، api_response (برای AC شامل «endpoint، API، status code، response»)، backend_test (برای AC شامل «test، pytest، unit test»)، static (برای AC شامل «فایل X وجود دارد، imported است»)، manual_only (برای AC مبهم یا ذهنی مثل «ظاهر زیبا»). یک نمونه JSON (few-shot) برای هر نوع به AI داده می‌شود. اگر AI نتواند plan بدهد، fallback به static است. فایل‌های مرتبط: oversight_strong_prompt.py و oversight_service.py. بخش مربوط از درخواست اصلی کاربر: Stage 2 — تولید verify_plan توسط AI. فایل‌ها: oversight_strong_prompt.py, oversight_service.py (در _idea_to_prompt_multi_pass), oversight_service.py (در system prompt). کاری که می‌شود: system prompt در idea_to_prompt گسترش یابد: AI علاوه بر AC، برای هر AC باید verify_method و در صورت نیاز verify_plan تولید کند. چارچوب تصمیم برای AI: AC شامل «کلیک، نمایش، صفحه، مودال، input» → ui_interaction. AC شامل «endpoint، API، status code، response» → api_response. AC شامل «test، pytest، unit test» → backend_test. AC شامل «فایل X وجود دارد، imported است» → static. AC مبهم یا ذهنی (مثل «ظاهر زیبا») → manual_only. prompt یک نمونهٔ کامل JSON برای هر نوع به AI می‌دهد (few-shot). اگر AI نتوانست plan بدهد → fallback به static. Tests: یک ایدهٔ UI («دکمه login کار کند») → AC با ui_interaction + ui_steps. یک ایدهٔ API («endpoint /users 200 بدهد») → AC با api_response. یک ایدهٔ ذهنی («طراحی شیک‌تر») → AC با manual_only. کلیدواژه‌ها: oversight_strong_prompt.py, oversight_service.py, _idea_to_prompt_multi_pass, verify_method, verify_plan, ui_interaction, api_response, backend_test, static, manual_only.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_strong_prompt.py، تابع build_strong_prompt (خط 158) را گسترش بده تا یک پارامتر جدید به نام `verify_plan_config` بپذیرد که شامل few-shot examples برای هر verify_method باشد. 2. در بخش تولید AC (خطوط 328-368)، بعد از هر AC یک فیلد verify_method و verify_plan اضافه کن که بر اساس کلمات کلیدی AC انتخاب شود. 3. یک تابع کمکی جدید به نام `_infer_verify_method` در همان فایل اضافه کن که متن AC را می‌گیرد و بر اساس کلمات کلیدی (ui_interaction, api_response, backend_test, static, manual_only) یک dict با verify_method و verify_plan برمی‌گرداند. 4. در فایل backend/app/services/oversight_service.py، تابع _idea_to_prompt_multi_pass (که در خطوط 800-900 قرار دارد) را اصلاح کن تا از تابع جدید _infer_verify_method استفاده کند و خروجی AC را با verify_method و verify_plan غنی کند. 5. در فایل backend/app/services/oversight_strong_prompt.py، یک بخش جدید به نام `## 🔬 راهنمای انتخاب verify_method` به system prompt اضافه کن که شامل جدول نشانه‌ها و نمونه‌های few-shot باشد. 6. تست‌های واحد در backend/tests/ برای سه سناریوی ذکر شده (UI, API, manual) اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 6: اجرای هستهٔ پروب‌های تأیید (Probe Runners) برای هر AC

**Scope:** این بخش شامل ایجاد پکیج جدید backend/app/services/verify_runtime/ با فایل‌های base.py (تعریف dataclass RuntimeProbeResult)، static_probe.py (wrapper روی grep فعلی)، ui_probe.py (استفاده از playwright.async_api با screenshot و browser pool)، api_probe.py (استفاده از httpx.AsyncClient با assert status_code و schema)، test_probe.py (استفاده از subprocess برای pytest با timeout 120s)، manual_probe.py (همیشه skipped) و runner.py (تابع run_probes_for_task با asyncio.Semaphore(3) و timeout کلی 5 دقیقه) است. همچنین شامل تست‌های mock برای UI probe، httpbin برای API probe و یک pytest dummy برای test_probe می‌شود. فایل‌های موجود در مسیرهای داده شده (مانند oversight_verifier.py) نباید تغییر کنند مگر برای import در static_probe.py.
**Key terms:** backend/app/services/verify_runtime/, RuntimeProbeResult, base.py, static_probe.py, ui_probe.py, api_probe.py, test_probe.py, manual_probe.py, runner.py, run_probes_for_task, asyncio.Semaphore(3), playwright.async_api, httpx.AsyncClient, subprocess, pytest --json-report, oversight_verifier.py

**بخش مربوط از متن کاربر:**
```
Stage 3 — Probe runners (هستهٔ کار)
پوشهٔ جدید: backend/app/services/verify_runtime/

فایل‌ها:

__init__.py
base.py — dataclass RuntimeProbeResult:
@dataclass
class RuntimeProbeResult:
    ac_id: str
    method: str  # static|ui|api|test|manual
    status: str  # passed|failed|error|skipped
    evidence: Dict[str, Any]  # {screenshot_paths, response_json, stdout, ...}
    duration_ms: int
    error_message: Optional[str]
    timestamp: str
static_probe.py — wrapper روی grep فعلی (همان منطق oversight_verifier)
ui_probe.py — استفاده از playwright.async_api:
async_playwright() → browser
برای هر step در ui_steps action متناظر را اجرا کن
screenshot قبل و بعد از هر action مهم (نام: <ac_id>_<step_idx>.png)
timeout per action: 10s پیش‌فرض
browser pool: max 3 concurrent
api_probe.py — استفاده از httpx.AsyncClient:
request اجرا
assert status_code (از plan)
assert response JSON schema (از plan: required fields)
response را به‌عنوان evidence ذخیره
test_probe.py — استفاده از subprocess:
pytest <test_path> --json-report --json-report-file=tmp.json
timeout: 120s
parse JSON output، success_count و failures
manual_probe.py — همیشه status="skipped" با پیام «نیاز به بازبینی دستی»
ابزارهای جدید nice-to-have:

runner.py — تابع run_probes_for_task(task, watched) -> List[RuntimeProbeResult]
برای هر AC method را تشخیص دهد
probe مناسب را call کند
با asyncio.Semaphore(3) همزمانی را محدود کند
timeout کلی task: 5 دقیقه
Tests:

mock playwright برای test UI probe (یا یک HTML ساده local serve)
httpbin برای test API probe
یک test pytest dummy برای test_probe
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد پکیج Probe Runners برای تأیید AC در verify_runtime

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/manual_probe.py:19-33` — `run_manual_probe`
  ```python
  def run_manual_probe(
      ac: Dict[str, Any],
      ctx: ProbeContext,
      ac_id: str,
  ) -> RuntimeProbeResult:
      plan = ac.get("verify_plan") or {}
      reason = plan.get("reason") or "این AC نیاز به بازبینی انسانی دارد و خودکار قابل تأیید نیست."
      return RuntimeProbeResult(
          ac_id=ac_id,
          ac_text=str(ac.get
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست اجرای هستهٔ پروب‌های تأیید (Probe Runners) برای هر AC را دارد. این شامل ایجاد پکیج جدید backend/app/services/verify_runtime/ با فایل‌های base.py (تعریف dataclass RuntimeProbeResult)، static_probe.py (wrapper روی grep فعلی)، ui_probe.py (استفاده از playwright.async_api با screenshot و browser pool)، api_probe.py (استفاده از httpx.AsyncClient با assert status_code و schema)، test_probe.py (استفاده از subprocess برای pytest با timeout 120s)، manual_probe.py (همیشه skipped) و runner.py (تابع run_probes_for_task با asyncio.Semaphore(3) و timeout کلی 5 دقیقه) است. همچنین شامل تست‌های mock برای UI probe، httpbin برای API probe و یک pytest dummy برای test_probe می‌شود. فایل‌های موجود در مسیرهای داده شده (مانند oversight_verifier.py) نباید تغییر کنند مگر برای import در static_probe.py. کلیدواژه‌ها: backend/app/services/verify_runtime/, RuntimeProbeResult, base.py, static_probe.py, ui_probe.py, api_probe.py, test_probe.py, manual_probe.py, runner.py, run_probes_for_task, asyncio.Semaphore(3), playwright.async_api, httpx.AsyncClient, subprocess, pytest --json-report, oversight_verifier.py. در کد فعلی، فایل‌های manual_probe.py و static_probe.py از قبل وجود دارند (manual_probe.py خط 19-33، static_probe.py خط 140-252) اما api_probe.py، ui_probe.py، test_probe.py و runner.py وجود ندارند. oversight_verifier.py (خط 1-2858) حاوی منطق grep و classification است که static_probe.py باید از آن import کند. فایل base.py نیز وجود ندارد و باید تعریف dataclass RuntimeProbeResult را شامل شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل base.py در backend/app/services/verify_runtime/ با تعریف dataclass RuntimeProbeResult شامل فیلدهای ac_id, method, status, evidence, duration_ms, error_message, timestamp. 2. ایجاد فایل ui_probe.py با تابع run_ui_probe که از playwright.async_api استفاده می‌کند، browser pool با max 3 concurrent، screenshot قبل و بعد از هر action، timeout 10s per action. 3. ایجاد فایل api_probe.py با تابع run_api_probe که از httpx.AsyncClient استفاده می‌کند، request اجرا، assert status_code و response JSON schema از plan، ذخیره response به عنوان evidence. 4. ایجاد فایل test_probe.py با تابع run_test_probe که subprocess برای pytest <test_path> --json-report --json-report-file=tmp.json با timeout 120s اجرا می‌کند و JSON output را parse می‌کند. 5. ایجاد فایل runner.py با تابع run_probes_for_task(task, watched) که برای هر AC method را تشخیص دهد، probe مناسب را call کند، با asyncio.Semaphore(3) همزمانی را محدود کند و timeout کلی task 5 دقیقه. 6. ایجاد تست‌های mock برای UI probe (یک HTML ساده local serve)، httpbin برای API probe و یک pytest dummy برای test_probe. 7. در static_probe.py، import از oversight_verifier.py برای استفاده از _build_keywords_from_acs و _extract_relevant_chunks اضافه شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 7: اضافه کردن فیلدهای Base URL و Config به WatchedProject و UI تنظیمات پروژه

**Scope:** این بخش شامل افزودن فیلدهای frontend_base_url، backend_base_url و runtime_auth به مدل WatchedProject در oversight_service.py، ایجاد UI برای تنظیم این مقادیر در صفحه تنظیمات پروژه (projects/[id]/page.tsx یا settings UI)، پیاده‌سازی دکمه تست اتصال (ping به فرانت و GET به backend health)، و مدیریت حالت skipped برای probeها در صورت تنظیم نبودن URLها است. خارج از scope: پیاده‌سازی خود probeها (فقط تست اتصال ساده)، و تغییرات در سایر فایل‌های oversight.
**Key terms:** oversight_service.py, WatchedProject, frontend_base_url, backend_base_url, runtime_auth, frontend/src/app/oversight/page.tsx, settings UI, تست اتصال, ping, backend health, skipped, base URL تنظیم نشده

**بخش مربوط از متن کاربر:**
```
Stage 4 — Base URLs و config
فایل‌ها: oversight_service.py (WatchedProject),
frontend/src/app/projects/[id]/page.tsx یا settings UI

کاری که می‌شود:

اضافه کردن فیلدها به WatchedProject:
frontend_base_url: Optional[str] — مثلاً https://ai-creator-frontend.onrender.com
backend_base_url: Optional[str] — مثلاً https://ai-creator-backend.onrender.com
runtime_auth: Optional[Dict] — {type: "cookie"|"bearer", value: str}
در UI: یک section در تنظیمات پروژه:
input URL فرانت
input URL بک‌اند
dropdown نوع احراز هویت + input مقدار
دکمه «تست اتصال» (یک ping به فرانت + یک GET به backend health)
اگر URL تنظیم نشده → probe های ui/api همگی status="skipped" با
پیام «base URL تنظیم نشده»
Tests:

تست اتصال موفق + ناموفق
ذخیره و بارگذاری config
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن فیلدهای Base URL و Config به WatchedProject و UI تنظیمات پروژه

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/oversight/page.tsx:117-141` — `interface Watched` — این فیلدها قبلاً در interface Watched تعریف شده‌اند — نیاز به UI برای ویرایش آن‌ها در صفحه تنظیمات پروژه است.
  ```tsx
  frontend_base_url?: string | null;
    backend_base_url?: string | null;
    runtime_auth?: { type?: 'bearer' | 'cookie' | null; value?: string | null } | null;
    runtime_repo_path?: string | null;
    runtime_autodetected?: boolean;
    runtime_connection_test?: {
      at?: string;
      frontend?: { ok?: boolean; status?: number; error?: string; url?: string };
      backend?: { ok?: boolean; status?: number; error?: string; url?: string };
    } | null;
  ```
- `frontend/src/app/pro`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن فیلدهای frontend_base_url، backend_base_url و runtime_auth به مدل WatchedProject در oversight_service.py و ایجاد UI برای تنظیم این مقادیر در صفحه تنظیمات پروژه (projects/[id]/page.tsx یا settings UI) را دارد. همچنین پیاده‌سازی دکمه تست اتصال (ping به فرانت و GET به backend health) و مدیریت حالت skipped برای probeها در صورت تنظیم نبودن URLها. خارج از scope: پیاده‌سازی خود probeها (فقط تست اتصال ساده)، و تغییرات در سایر فایل‌های oversight. کلیدواژه‌ها: oversight_service.py, WatchedProject, frontend_base_url, backend_base_url, runtime_auth, frontend/src/app/oversight/page.tsx, settings UI, تست اتصال, ping, backend health, skipped, base URL تنظیم نشده. در کد فعلی، فایل frontend/src/app/oversight/page.tsx از خط 117 تا 141 فیلدهای frontend_base_url، backend_base_url، runtime_auth، runtime_autodetected و runtime_connection_test را در interface Watched تعریف کرده است. همچنین فایل backend/app/services/oversight_service.py (که deep-read نشده اما در ساختار پروژه موجود است) باید مدل WatchedProject را با این فیلدها به‌روز کند. فایل frontend/src/app/projects/[id]/page.tsx از خط 1 تا 685 شامل stateهای inspector و external است اما بخشی برای تنظیم base URLها ندارد. فایل backend/app/api/routes/oversight.py (deep-read نشده) باید endpointهای GET/PATCH برای این فیلدها و endpoint تست اتصال را پیاده‌سازی کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در backend/app/services/oversight_service.py، فیلدهای frontend_base_url (Optional[str])، backend_base_url (Optional[str]) و runtime_auth (Optional[Dict]) را به مدل WatchedProject اضافه کن. 2. در backend/app/api/routes/oversight.py، یک endpoint جدید POST /api/oversight/watched/{watched_id}/test-connection ایجاد کن که به frontend_base_url یک ping (GET /) و به backend_base_url یک GET /health بزند و نتیجه را در runtime_connection_test ذخیره کند. 3. در frontend/src/app/projects/[id]/page.tsx، یک بخش UI جدید با عنوان 'تنظیمات Runtime Verify' اضافه کن شامل: input برای frontend_base_url، input برای backend_base_url، dropdown برای نوع auth (bearer/cookie) + input برای مقدار، و دکمه 'تست اتصال'. 4. در frontend/src/app/oversight/page.tsx، از خط 117 تا 141 فیلدهای موجود (frontend_base_url, backend_base_url, runtime_auth, runtime_connection_test) در interface Watched قبلاً تعریف شده‌اند — فقط UI برای ویرایش آن‌ها در صفحه تنظیمات پروژه اضافه شود. 5. اگر URL تنظیم نشده باشد، در بخش نمایش probeها (که خارج از scope است) وضعیت 'skipped' با پیام 'base URL تنظیم نشده' نمایش داده شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 8: یکپارچه‌سازی runtime probes با verify_task در oversight_verifier.py

**Scope:** این مرحله شامل افزودن فراخوانی run_probes_for_task در ابتدای تابع verify_task (قبل از فراخوانی AI)، جمع‌آوری نتایج probeها، تبدیل آنها به متن شواهد runtime، و الحاق این متن به عنوان بخش جدیدی در prompt ارسالی به AI است. همچنین شامل منطق override نتایج AI بر اساس نتایج runtime (اولویت runtime بر AI) و مدیریت خطاهای timeout با fallback به AI-only می‌باشد. فایل‌های درگیر: oversight_verifier.py (اصلی)، runner.py (برای run_probes_for_task)، و احتمالاً oversight_strong_prompt.py (برای اصلاح system prompt).
**Key terms:** oversight_verifier.py, verify_task, run_probes_for_task, asyncio.wait_for, RuntimeProbeResult, ProbeContext, runner.py, oversight_strong_prompt.py

**بخش مربوط از متن کاربر:**
```
Stage 5 — یکپارچه‌سازی با verify_task
فایل: oversight_verifier.py

کاری که می‌شود:

در ابتدای verify_task (یا قبل از فراخوانی AI):
runtime_results = await run_probes_for_task(task, watched)
(با asyncio.wait_for timeout کلی)
هر probe که شکست خورد → log + continue (verify ادامه دهد)
results را به یک متن خوانا تبدیل کن:
## شواهد Runtime
### AC1: «وقتی روی دکمه X کلیک می‌کنم، مدال باز شود»
- method: ui_interaction
- status: ✅ passed
- evidence: screenshots/<task_id>/<run_id>/ac1_step3.png
- duration: 850ms
- مشاهدات: مدال [role=dialog] در 240ms ظاهر شد
### AC2: «GET /api/users → 200 با field email»
- method: api_response  
- status: ❌ failed
- actual_status: 500
- error: "Internal Server Error"
این متن را به‌عنوان بخش جدید در prompt verify اضافه کن
system prompt به AI: «شواهد runtime بالاتر از تحلیل کد است. اگر
runtime می‌گوید failed، حتی اگر کد درست به نظر برسد، AC پاس نشده.»
پس از AI، اگر برای یک AC هم runtime ✅ و هم AI گفت done → done قطعی
اگر runtime ❌ ولی AI گفت done → AI override کن به not_done (با هشدار log)
اگر runtime ✅ ولی AI گفت not_done → AI override کن به done
Tests:

verify_task با task که همهٔ probe ها pass شدند → status=done
verify_task با probe failed → AI override
verify_task با probe error (timeout) → fallback به فقط AI
```

## 🎯 هدف (خلاصه ساختاریافته)
یکپارچه‌سازی runtime probes با verify_task در oversight_verifier.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_verifier.py:800-810` — `verify_task`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک به درخواست کاربر برای یکپارچه‌سازی runtime probes با تابع verify_task در فایل oversight_verifier.py انجام می‌شود. کاربر خواسته است که در ابتدای تابع verify_task (قبل از فراخوانی AI) یک فراخوانی به run_probes_for_task اضافه شود. این فراخوانی باید با asyncio.wait_for timeout کلی انجام شود. هر probe که شکست خورد → log + continue (verify ادامه دهد). نتایج probeها باید به یک متن خوانا تبدیل شوند با ساختار:
## شواهد Runtime
### AC1: «وقتی روی دکمه X کلیک می‌کنم، مدال باز شود»
- method: ui_interaction
- status: ✅ passed
- evidence: screenshots/<task_id>/<run_id>/ac1_step3.png
- duration: 850ms
- مشاهدات: مدال [role=dialog] در 240ms ظاهر شد
### AC2: «GET /api/users → 200 با field email»
- method: api_response  
- status: ❌ failed
- actual_status: 500
- error: "Internal Server Error"
این متن به‌عنوان بخش جدید در prompt verify اضافه شود. system prompt به AI: «شواهد runtime بالاتر از تحلیل کد است. اگر runtime می‌گوید failed، حتی اگر کد درست به نظر برسد، AC پاس نشده.» پس از AI، اگر برای یک AC هم runtime ✅ و هم AI گفت done → done قطعی. اگر runtime ❌ ولی AI گفت done → AI override کن به not_done (با هشدار log). اگر runtime ✅ ولی AI گفت not_done → AI override کن به done. فایل‌های درگیر: oversight_verifier.py (اصلی)، runner.py (برای run_probes_for_task)، و احتمالاً oversight_strong_prompt.py (برای اصلاح system prompt). کلیدواژه‌ها: oversight_verifier.py, verify_task, run_probes_for_task, asyncio.wait_for, RuntimeProbeResult, ProbeContext, runner.py, oversight_strong_prompt.py. در کد واقعی، تابع verify_task در oversight_verifier.py (خطوط 800-2858) وجود دارد که در حال حاضر مستقیماً AI را فراخوانی می‌کند. تابع run_probes_for_task در runner.py (backend/app/services/verify_runtime/runner.py) تعریف شده است. تابع build_strong_prompt در oversight_strong_prompt.py (خط 158) برای ساخت prompt استفاده می‌شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_verifier.py، در ابتدای تابع verify_task (حدود خط 800)، یک فراخوانی async به run_probes_for_task اضافه کن با asyncio.wait_for timeout کلی (مثلاً 60 ثانیه). 2. نتایج probeها (از نوع RuntimeProbeResult) را جمع‌آوری کن. 3. یک تابع کمکی جدید به نام _format_runtime_evidence بنویس که نتایج probeها را به متن خوانا با ساختار مشخص شده تبدیل کند (شامل method, status, evidence, duration, مشاهدات). 4. این متن را به عنوان بخش جدیدی با عنوان '## شواهد Runtime' به prompt ارسالی به AI اضافه کن. 5. در system prompt AI، جمله 'شواهد runtime بالاتر از تحلیل کد است. اگر runtime می‌گوید failed، حتی اگر کد درست به نظر برسد، AC پاس نشده.' را اضافه کن. 6. پس از دریافت پاسخ AI، منطق override را پیاده‌سازی کن: اگر runtime ✅ و AI گفت done → done قطعی؛ اگر runtime ❌ ولی AI گفت done → AI override به not_done با log هشدار؛ اگر runtime ✅ ولی AI گفت not_done → AI override به done. 7. خطاهای timeout را مدیریت کن: اگر asyncio.wait_for timeout خورد، به AI-only fallback کن. 8. تست‌های مشخص شده را اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 9: ذخیره‌سازی evidence در storage/verify_evidence با cleanup و endpoint سرو

**Scope:** این بخش شامل پیاده‌سازی ساختار دایرکتوری storage/verify_evidence/<task_id>/<run_id>/ با فایل‌های ac1_step1.png, ac1_step2.png, ac2_response.json, ac3_pytest.json و manifest.json است. همچنین شامل cleanup policy (نگه‌داری 5 run آخر هر task)، endpoint جدید GET /api/oversight/tasks/{id}/evidence/{run_id}/<path> با authorization، و size limit 50MB per run با fallback به JPEG q=70 برای screenshots می‌شود. خارج از scope: پیاده‌سازی خود فرآیند capture یا تولید evidence.
**Key terms:** verify_runtime/storage.py, storage/verify_evidence/, manifest.json, GET /api/oversight/tasks/{id}/evidence/{run_id}/<path>, cleanup policy, size limit 50MB, JPEG q=70

**بخش مربوط از متن کاربر:**
```
Stage 6 — ذخیره‌سازی evidence
فایل: verify_runtime/storage.py

کاری که می‌شود:

ساختار:
storage/verify_evidence/
  <task_id>/
    <run_id>/
      ac1_step1.png
      ac1_step2.png
      ac2_response.json
      ac3_pytest.json
      manifest.json   # links همهٔ evidence ها
cleanup policy: نگه‌داری فقط 5 run آخر هر task
endpoint جدید: GET /api/oversight/tasks/{id}/evidence/{run_id}/<path>
→ serve فایل (با authorization)
size limit: 50MB per run؛ اگر بیشتر شد، screenshots را به JPEG q=70 کم کن
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی ذخیره‌سازی evidence با cleanup و endpoint سرو

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/storage.py:1-150` — `کل فایل (جدید)` — این فایل در ساختار پروژه موجود است (backend/app/services/verify_runtime/storage.py) اما deep-read نشده. باید ایجاد/تکمیل شود با توابع save_evidence, generate_manifest, cleanup_old_runs, enforce_size_limit, resolve_evidence_file
- `backend/app/api/routes/oversight.py:363-395` — `get_evidence_file`
  ```python
  @router.get("/tasks/{task_id}/evidence/{run_id}/{file_path:path}")
  async def get_evidence_file(task_id: str, run_id: str, file_path: str):
      """فایل evidence (screenshot یا JSON) را با محافظت در برابر traversal serve می‌کند."""
      from pathlib import Path
      from fastapi.responses import FileResponse
      from app.services.oversight_service import STORAGE_DIR
      from app.services.verify_runtime.storage import resolve_evidence_file
      p =
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی ساختار دایرکتوری storage/verify_evidence/<task_id>/<run_id>/ با فایل‌های ac1_step1.png, ac1_step2.png, ac2_response.json, ac3_pytest.json و manifest.json را دارد. همچنین cleanup policy (نگه‌داری 5 run آخر هر task)، endpoint جدید GET /api/oversight/tasks/{id}/evidence/{run_id}/<path> با authorization، و size limit 50MB per run با fallback به JPEG q=70 برای screenshots. خارج از scope: پیاده‌سازی خود فرآیند capture یا تولید evidence.

بر اساس کد واقعی پروژه:
- فایل backend/app/services/verify_runtime/storage.py (که در ساختار پروژه موجود است اما deep-read نشده) باید ایجاد/تکمیل شود.
- فایل backend/app/api/routes/oversight.py از خط 363 تا 395 endpointهای GET /tasks/{task_id}/evidence/runs و GET /tasks/{task_id}/evidence/{run_id}/{file_path:path} را دارد که باید با endpoint جدید یکپارچه شود.
- فایل frontend/src/app/oversight/page.tsx از خط 300-318 interface Report را دارد که باید برای نمایش evidence به‌روز شود.
- کلیدواژه‌های کاربر: verify_runtime/storage.py, storage/verify_evidence/, manifest.json, GET /api/oversight/tasks/{id}/evidence/{run_id}/<path>, cleanup policy, size limit 50MB, JPEG q=70

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد/تکمیل فایل backend/app/services/verify_runtime/storage.py با توابع:
   - save_evidence(task_id, run_id, evidence_files: dict) -> ذخیره فایل‌ها در storage/verify_evidence/<task_id>/<run_id>/
   - generate_manifest(task_id, run_id) -> تولید manifest.json با لیست همه فایل‌ها
   - cleanup_old_runs(task_id, max_runs=5) -> حذف runهای قدیمی‌تر از 5 تای آخر
   - enforce_size_limit(run_dir, max_bytes=50*1024*1024) -> اگر حجم از 50MB بیشتر شد، screenshots را به JPEG q=70 تبدیل کند
   - get_evidence_file(task_id, run_id, file_path) -> مسیر فایل را با محافظت path traversal برگرداند

2. به‌روزرسانی endpoint موجود در backend/app/api/routes/oversight.py خط 375-395:
   - تابع get_evidence_file را با storage.resolve_evidence_file یکپارچه کن
   - authorization چک کند (بررسی watched_id مرتبط با task)

3. افزودن cleanup job به backend/app/services/background_scheduler.py برای اجرای دوره‌ای cleanup

4. به‌روزرسانی frontend/src/app/oversight/page.tsx برای نمایش evidence در UI

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 10: افزودن شواهد Runtime به PDF و پیام تلگرام

**Scope:** این مرحله شامل افزودن یک بخش جدید به نام «📷 شواهد Runtime» در PDF خروجی است که برای هر Acceptance Criteria (AC) یک کارت شامل متن AC، badge روش (UI/API/Test)، badge وضعیت، و شواهد inline (تصویر برای UI، JSON truncated برای API، stdout pytest truncated برای Test) ایجاد می‌کند. همچنین در پیام تلگرام، اگر هر probe failed باشد، یک خلاصه با وضعیت هر AC و لینک به PDF پیوست ارسال می‌شود. فایل‌های هدف: oversight_verify_pdf.py و notification_service.py. خارج از scope: تغییر منطق اجرای probeها یا ذخیره شواهد.
**Key terms:** oversight_verify_pdf.py, notification_service.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult

**بخش مربوط از متن کاربر:**
```
در PDF، یک section جدید «📷 شواهد Runtime»:
برای هر AC، یک card با:
متن AC
method badge (UI / API / Test)
status badge
برای UI: تصویر screenshot inline
برای API: JSON پاسخ (truncated به 500 byte) در <pre>
برای Test: stdout pytest (truncated)
در پیام تلگرام: اگر هر probe failed بود، یک خلاصه:
❌ شواهد runtime:
  • AC1 ui_interaction: passed (240ms)
  • AC2 api_response: failed (status 500)
  • AC3 backend_test: passed (3 tests)
📎 جزئیات کامل در PDF پیوست
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن بخش شواهد Runtime به PDF و پیام تلگرام

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست افزودن یک بخش جدید به نام «📷 شواهد Runtime» در PDF خروجی (فایل oversight_verify_pdf.py) و همچنین افزودن خلاصه شواهد Runtime در پیام تلگرام (فایل notification_service.py) را دارد. بر اساس تحلیل کد واقعی:

در فایل backend/app/services/oversight_verify_pdf.py، تابع `_build_verify_report_html` (خط 204) مسئول ساخت HTML برای رندر PDF است. در خطوط 369-486 یک بخش runtime_html وجود دارد که برای هر probe یک کارت با متن AC، badge روش (UI/API/Test)، badge وضعیت، و شواهد inline (تصویر برای UI، JSON truncated برای API، stdout pytest truncated برای Test) ایجاد می‌کند. اما این بخش فعلاً فقط برای runtime probes موجود است و کاربر می‌خواهد این بخش به‌صورت اختصاصی‌تر با عنوان «📷 شواهد Runtime» و با ساختار مشخص‌تر (card برای هر AC) پیاده‌سازی شود.

در فایل backend/app/services/notification_service.py، تابع `build_verify_checklist_message` (خط 81) مسئول ساخت متن چک‌لیستی برای caption پیام تلگرام است. در خطوط 177-192 یک بخش runtime probes summary وجود دارد که خلاصه‌ای از runtime probes را نشان می‌دهد (✅❌⏭⚠️). کاربر می‌خواهد اگر هر probe failed باشد، یک خلاصه با وضعیت هر AC و لینک به PDF پیوست ارسال شود.

کلیدواژه‌های کاربر: oversight_verify_pdf.py, notification_service.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult

درخواست کاربر شامل دو بخش است:
1. در PDF: یک section جدید «📷 شواهد Runtime» با card برای هر AC شامل متن AC، method badge (UI/API/Test)، status badge، و شواهد inline (تصویر برای UI، JSON truncated برای API، stdout pytest truncated برای Test)
2. در پیام تلگرام: اگر هر probe failed بود، یک خلاصه با وضعیت هر AC و لینک به PDF پیوست

خارج از scope: تغییر منطق اجرای probeها یا ذخیره شواهد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_verify_pdf.py، تابع `_build_verify_report_html` (خط 204):
   - یک بخش جدید با عنوان `<h2>📷 شواهد Runtime</h2>` بعد از بخش runtime_html فعلی (خط 485) اضافه کن.
   - برای هر AC که در evidence.runtime_probes موجود است، یک card با ساختار مشخص بساز:
     * متن AC در `<div class="probe-ac">`
     * method badge (UI/API/Test) با کلاس CSS مناسب
     * status badge (passed/failed/error/skipped) با رنگ‌های مشخص
     * برای UI: تصویر screenshot inline (base64) در `<img>`
     * برای API: JSON پاسخ (truncated به 500 byte) در `<pre class="code">`
     * برای Test: stdout pytest (truncated به 600 کاراکتر) در `<pre class="code">`
   - اطمینان حاصل کن که این بخش فقط زمانی نمایش داده شود که runtime_probes موجود باشد.

2. در فایل backend/app/services/notification_service.py، تابع `build_verify_checklist_message` (خط 81):
   - بعد از بخش runtime probes summary فعلی (خطوط 177-192)، یک بخش جدید اضافه کن که اگر هر probe failed باشد، یک خلاصه با وضعیت هر AC و لینک به PDF پیوست ارسال کند.
   - ساختار خلاصه:
     ❌ شواهد runtime:
       • AC1 ui_interaction: passed (240ms)
       • AC2 api_response: failed (status 500)
       • AC3 backend_test: passed (3 tests)
     📎 جزئیات کامل در PDF پیوست
   - از داده‌های موجود در report.evidence.runtime_probes استفاده کن.

3. اطمینان حاصل کن که لینک PDF پیوست در انتهای پیام تلگرام

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 11: Stage 8 — Frontend UI برای نمایش evidence در مودال جزئیات تسک

**Scope:** این بخش شامل پیاده‌سازی UI در frontend/src/app/oversight/page.tsx برای نمایش آخرین verify runtime در مودال جزئیات تسک است. شامل: نمایش row برای هر AC با method icon + status + دکمه مشاهده evidence، مودال دوم با gallery screenshot (lightbox)، JSON formatted با syntax highlight، terminal-style block برای stdout، و دکمه جدید «🔬 Verify با Runtime» که شامل probe ها است. verify عادی بدون probe باقی می‌ماند. همچنین بخش تنظیمات پروژه برای Runtime Verify با URLها و auth. خارج از scope: backend logic، تست‌ها، و پیاده‌سازی actual runtime verification.
**Key terms:** frontend/src/app/oversight/page.tsx, مودال جزئیات تسک, آخرین verify runtime, AC, method icon, status, مشاهدهٔ evidence, gallery screenshot, lightbox, JSON formatted, syntax highlight, terminal-style block, stdout, Verify با Runtime, probe, verify عادی, تنظیمات پروژه, Runtime Verify, URL, auth

**بخش مربوط از متن کاربر:**
```
Stage 8 — Frontend UI (نمایش evidence)
فایل: frontend/src/app/oversight/page.tsx

کاری که می‌شود:

در مودال جزئیات تسک، section جدید «🔬 آخرین verify runtime»:
برای هر AC: row با method icon + status + دکمهٔ «مشاهدهٔ evidence»
کلیک روی دکمه → مودال modal دوم با:
برای UI: gallery screenshot ها (lightbox)
برای API: JSON formatted با syntax highlight
برای Test: terminal-style block با stdout
دکمهٔ جدید «🔬 Verify با Runtime» (متفاوت از verify عادی):
این یکی شامل probe ها است (کندتر)
verify عادی بدون probe می‌ماند برای سرعت
در تنظیمات پروژه: section «Runtime Verify» با URLها و auth
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن مودال نمایش evidence runtime verify در جزئیات تسک

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/oversight/page.tsx:165-298` — `interface Task`
  ```tsx
  interface Task {
    id: string;
    watched_id?: string
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی Stage 8 — Frontend UI برای نمایش evidence در مودال جزئیات تسک در فایل frontend/src/app/oversight/page.tsx را دارد. این شامل: نمایش row برای هر AC با method icon + status + دکمه مشاهده evidence، مودال دوم با gallery screenshot (lightbox)، JSON formatted با syntax highlight، terminal-style block برای stdout، و دکمه جدید «🔬 Verify با Runtime» که شامل probe ها است. verify عادی بدون probe باقی می‌ماند. همچنین بخش تنظیمات پروژه برای Runtime Verify با URLها و auth. خارج از scope: backend logic، تست‌ها، و پیاده‌سازی actual runtime verification. کلیدواژه‌ها: frontend/src/app/oversight/page.tsx, مودال جزئیات تسک, آخرین verify runtime, AC, method icon, status, مشاهدهٔ evidence, gallery screenshot, lightbox, JSON formatted, syntax highlight, terminal-style block, stdout, Verify با Runtime, probe, verify عادی, تنظیمات پروژه, Runtime Verify, URL, auth. در کد فعلی frontend/src/app/oversight/page.tsx، مودال جزئیات تسک (احتمالاً در بخش‌های بعدی فایل که در deep context موجود نیست) باید توسعه یابد. همچنین در backend/app/api/routes/oversight.py endpoint‌های /tasks/{task_id}/evidence/runs و /tasks/{task_id}/evidence/{run_id}/{file_path:path} برای سرو کردن evidence وجود دارد (خطوط 364-395). در frontend/src/app/oversight/page.tsx، ساختار Task شامل فیلدهای verification_history (خطوط 185-191) و acceptance_criteria (خط 197) است که برای نمایش ACها استفاده می‌شود. همچنین در backend/app/api/routes/oversight.py، endpoint /tasks/{task_id}/verify-trace (خطوط 285-311) trace کامل verify v6 را برمی‌گرداند که شامل verify_trace, ac_probe_details, verify_version, config_used است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در frontend/src/app/oversight/page.tsx، در مودال جزئیات تسک (که احتمالاً در خطوط 800-3179 فایل قرار دارد)، یک section جدید با عنوان «🔬 آخرین verify runtime» اضافه کن. 2. برای هر AC در task.acceptance_criteria، یک row با method icon (بر اساس verify_method: static=📄, ui_interaction=🖱️, api_response=🌐, backend_test=🧪, manual_only=👤)، status (از ac.last_status یا 'pending')، و دکمه «مشاهدهٔ evidence» ایجاد کن. 3. با کلیک روی دکمه، یک مودال دوم باز شود که: برای UI (verify_method=ui_interaction) gallery screenshot ها با lightbox (با استفاده از state و img tag ساده)، برای API (verify_method=api_response) JSON formatted با syntax highlight (با استفاده از تابع formatJSON و <pre> با CSS)، برای Test (verify_method=backend_test) terminal-style block با stdout (با استفاده از <pre> با background تیره). 4. یک دکمه جدید «🔬 Verify با Runtime» در کنار دکمه verify عادی اضافه کن که به endpoint /api/oversight/tasks/{taskId}/run با include_runtime=true POST می‌کند. 5. در بخش تنظیمات پروژه (که احتمالاً در همان مودال یا یک panel جداگانه است)، section «Runtime Verify» با فیلدهای frontend_base_url، backend_base_url، runtime_auth (type و value)، runtime_repo_path اضافه کن که به endpoint /api/oversight/watched/{watchedId} با PATCH ارسال شوند. 6. از endpoint /api/oversight/tasks/{taskId}/evidence/runs برای دریافت لیست runها و از /api/oversight/tasks/{taskId}/evidence/{runId}/{filePath} برای دریافت فایل‌های evidence استفاده کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 12: Stage 9: پیاده‌سازی مدیریت چرخه‌عمر، زمان‌بندی، محدودیت‌ها و Degrade امنیتی Runtime

**Scope:** این مرحله شامل پیاده‌سازی مدیریت چرخه‌عمر Playwright browser process در lifespan FastAPI (شروع و kill بعد از 5 دقیقه idle)، اعمال per-task timeout کلی 5 دقیقه، per-probe timeout (ui=30s, api=10s, test=120s)، Semaphore با حداکثر 3 probe موازی برای یک task، graceful degrade به static در صورت عدم نصب Playwright (با warning)، circuit breaker با 3 خطای متوالی probe که runtime را برای 10 دقیقه disable می‌کند، و خواندن environment flag RUNTIME_VERIFY_ENABLED=true|false از .env است. خارج از scope: پیاده‌سازی خود probeها، منطق business، و frontend.
**Key terms:** Playwright browser process, lifespan FastAPI, 5 دقیقه idle, per-task timeout, per-probe timeout, ui=30s, api=10s, test=120s, Semaphore, 3 probe موازی, graceful degrade, static, warning, circuit breaker, 3 task پشت‌سرهم probe error, 10 دقیقه disable, RUNTIME_VERIFY_ENABLED, .env, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/base.py, backend/app/services/oversight_service.py

**بخش مربوط از متن کاربر:**
```
Stage 9 — Performance, safety, edge cases
کاری که می‌شود:
Playwright browser process را در lifespan FastAPI start کن (شاره شده)
→ بعد از 5 دقیقه idle، آن را kill کن
per-task timeout کلی: 5 دقیقه
per-probe timeout: ui=30s, api=10s, test=120s
Semaphore: حداکثر 3 probe موازی برای یک task
اگر runtime در محیط Render (production) فعال نیست (مثلاً playwright install نشده) → graceful degrade به فقط static (با warning)
circuit breaker: اگر 3 task پشت‌سرهم probe error دادند، runtime را برای 10 دقیقه disable کن
environment flag: RUNTIME_VERIFY_ENABLED=true|false در .env
```

## 🎯 هدف (خلاصه ساختاریافته)
مدیریت چرخه‌عمر، زمان‌بندی و Degrade امنیتی Runtime Verify

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/runner.py:1-200` — `class RuntimeVerifyRunner` — کلاس اصلی اجرای verify — اینجا باید Semaphore، per-task timeout، و بررسی RUNTIME_VERIFY_ENABLED اضافه شود
  ```python
  class RuntimeVerifyRunner:
      def __init__(self):
          self._session: Optional[aiohttp.ClientSession] = None
          self._lock = asyncio.Lock()
  ```
- `backend/app/services/verify_runtime/base.py:1-100` — `class BaseProbe` — کلاس پایه probeها — اینجا باید timeout_per_probe (ui=30s, api=10s, test=120s) با asyncio.wait_for پیاده‌سازی شود
  ```python
  class BaseProbe(ABC):
      @abstractmethod
      async def run(self, context: ProbeContext) -> ProbeResult:
          ...
  ```
- `backend/app/services/verify_runtime/browser_pool.py:1-80` — `class BrowserPool` — مدیریت Playwright browser — اینجا باید start_browser()، stop_browser()، و idle timeout 5 دقیقه‌ای اضافه شود
  ```python
  class BrowserPool:
      def __init__(self):
          self._browser: Optional[playwright.async_api.Browser] = None
          self._last_used: Optional[float] = None
  ```
- `backend/app/services/verify_runtime/safety.py:1-50` — `class CircuitBreaker` — فایل جدید یا موجود برای circuit breaker — باید state خطاهای متوالی را نگه دارد و runtime را disable کند
  ```python
  # safety.py — currently empty or minimal
  # باید circuit breaker با 3 خطای متوالی و 10 دقیقه disable پیاده‌سازی شود
  ```
- `backend/app/main.py:1-50` — `lifespan` — lifespan FastAPI — اینجا باید start_browser() در startup و stop_browser() در shutdown فراخوانی شود
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # startup
      yield
      # shutdown
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/core/config.py` — خواندن RUNTIME_VERIFY_ENABLED از .env —

## 🔍 Context و وضعیت فعلی
پیاده‌سازی Stage 9 شامل مدیریت چرخه‌عمر Playwright browser process در lifespan FastAPI (شروع و kill بعد از 5 دقیقه idle)، اعمال per-task timeout کلی 5 دقیقه، per-probe timeout (ui=30s, api=10s, test=120s)، Semaphore با حداکثر 3 probe موازی برای یک task، graceful degrade به static در صورت عدم نصب Playwright (با warning)، circuit breaker با 3 خطای متوالی probe که runtime را برای 10 دقیقه disable می‌کند، و خواندن environment flag RUNTIME_VERIFY_ENABLED=true|false از .env. این تغییرات عمدتاً در فایل‌های backend/app/services/verify_runtime/runner.py (خطوط 1-200 فعلی که مدیریت session و browser pool را انجام می‌دهد)، backend/app/services/verify_runtime/base.py (کلاس BaseProbe با timeout)، backend/app/services/verify_runtime/browser_pool.py (مدیریت Playwright browser)، backend/app/services/verify_runtime/safety.py (circuit breaker و degrade)، backend/app/services/verify_runtime/__init__.py (export کلاس‌ها)، backend/app/main.py (lifespan FastAPI)، و backend/app/core/config.py (خواندن RUNTIME_VERIFY_ENABLED از .env) اعمال می‌شوند. خارج از scope: پیاده‌سازی خود probeها، منطق business، و frontend.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در backend/app/core/config.py: افزودن فیلد RUNTIME_VERIFY_ENABLED: bool = True با خواندن از env.
2. در backend/app/services/verify_runtime/browser_pool.py: افزودن متد start_browser() که Playwright browser را با chromium.launch() راه‌اندازی کند و متد stop_browser() که browser را ببندد. افزودن تایمر idle 5 دقیقه‌ای با asyncio.create_task که اگر browser به مدت 300 ثانیه استفاده نشد، kill کند.
3. در backend/app/services/verify_runtime/base.py: افزودن timeout_per_probe به کلاس BaseProbe (ui=30, api=10, test=120) و اعمال asyncio.wait_for روی هر probe.
4. در backend/app/services/verify_runtime/runner.py: افزودن Semaphore با max 3 برای محدودیت probeهای موازی. افزودن per-task timeout کلی 5 دقیقه با asyncio.wait_for روی کل run_verify.
5. در backend/app/services/verify_runtime/safety.py: پیاده‌سازی circuit breaker با شمارش خطاهای متوالی probe (3 خطا = disable 10 دقیقه). ذخیره state در dict درون حافظه.
6. در backend/app/services/verify_runtime/__init__.py: export کلاس‌ها و توابع جدید.
7. در backend/app/main.py: در lifespan FastAPI، فراخوانی start_browser() در startup و stop_browser() در shutdown. اگر playwright نصب نبود، graceful degrade با warning.
8. در backend/app/services/verify_runtime/runner.py: بررسی RUNTIME_VERIFY_ENABLED از config — اگر false بود، فقط static probe اجرا شود.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 13: Stage 10: پیاده‌سازی تست‌های واحد و یکپارچه‌سازی برای قابلیت Verify Runtime

**Scope:** این مرحله شامل نوشتن تست‌های واحد برای هر probe (static, ui, api, test, runner) و یک تست یکپارچه‌سازی end-to-end است. همچنین شامل ایجاد فیکسچرهای known-good و known-bad برای اعتبارسنجی سناریوهای موفق و شکست می‌شود. معیارهای پذیرش عملکردی و کیفی (مانند type-check، عدم شکست تست‌های موجود، graceful disable در production) نیز بخشی از این مرحله هستند. خارج از scope این مرحله، بازنویسی verifier فعلی، visual regression testing، load testing، security scanning و mobile UI testing است.
**Key terms:** test_static_probe.py, test_ui_probe.py, test_api_probe.py, test_test_probe.py, test_runner.py, test_runtime_integration.py, known-good fixture, known-bad fixture, verify_method=static, verify_method=ui_interaction, verify_method=api_response, verify_method=backend_test, verify_method=manual_only, RUNTIME_VERIFY_ENABLED, mypy, tsc, pytest, Playwright, httpbin, Render, backend/app/services/verify_runtime/, tests/integration/test_runtime_verify.py

**بخش مربوط از متن کاربر:**
```
unit tests:
test_static_probe.py — grep درست
test_ui_probe.py — با یک HTML server محلی
test_api_probe.py — با httpbin
test_test_probe.py — با pytest dummy
test_runner.py — orchestration
test_runtime_integration.py — verify_task با probe ها end-to-end
یک «known-good» fixture: task ساده که همه‌چیز pass می‌شود
یک «known-bad» fixture: task که هر probe باید fail شود
✅ معیارهای پذیرش کلی
عملکردی
not done
AC با verify_method=static همان رفتار قبلی verify را دارد (no regression)
not done
AC با verify_method=ui_interaction: playwright headless browser باز
می‌کند، steps را اجرا می‌کند، screenshot می‌گیرد، نتیجه برمی‌گرداند
not done
AC با verify_method=api_response: HTTP request می‌رود، status + شِما
چک می‌شود
not done
AC با verify_method=backend_test: pytest در subprocess با timeout
اجرا می‌شود
not done
AC با verify_method=manual_only: skipped با پیام واضح
not done
هر probe که error داد، verify ادامه می‌دهد (نه crash)
not done
base URL ها قابل تنظیم per project
not done
evidence فایل‌ها روی disk ذخیره می‌شوند، با cleanup policy
not done
PDF و Telegram message شواهد را embed می‌کنند
not done
Frontend modal جدید برای drill-down evidence
کیفی
not done
type-check (mypy + tsc) بدون error
not done
هیچ test موجود fail نمی‌شود
not done
محیط production (Render) با RUNTIME_VERIFY_ENABLED=false کاملاً
مثل قبل کار می‌کند (graceful disable)
not done
هیچ probe که فقط برای یک AC شکست خورد، کل verify را crash نکند
کنترل کیفیت verify
not done
روی یک تسک "known-good" (همه AC ها واقعاً پاس شده‌اند) →
verify=done
not done
روی یک تسک "known-bad" (UI AC شکست خورده) → AI نمی‌تواند آن را
done اعلام کند (runtime override)
not done
روی یک تسک با کد درست ولی deploy نشده → runtime می‌گوید fail
(چون probe می‌رود به URL واقعی، نه به کد محلی)
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن تست‌های واحد و یکپارچه‌سازی برای Verify Runtime

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
Stage 10: پیاده‌سازی تست‌های واحد و یکپارچه‌سازی برای قابلیت Verify Runtime. این مرحله شامل نوشتن تست‌های واحد برای هر probe (static, ui, api, test, runner) و یک تست یکپارچه‌سازی end-to-end است. همچنین شامل ایجاد فیکسچرهای known-good و known-bad برای اعتبارسنجی سناریوهای موفق و شکست می‌شود. معیارهای پذیرش عملکردی و کیفی (مانند type-check، عدم شکست تست‌های موجود، graceful disable در production) نیز بخشی از این مرحله هستند. خارج از scope این مرحله، بازنویسی verifier فعلی، visual regression testing، load testing، security scanning و mobile UI testing است.

بخش مربوط از درخواست اصلی کاربر:
unit tests:
test_static_probe.py — grep درست
test_ui_probe.py — با یک HTML server محلی
test_api_probe.py — با httpbin
test_test_probe.py — با pytest dummy
test_runner.py — orchestration
test_runtime_integration.py — verify_task با probe ها end-to-end
یک «known-good» fixture: task ساده که همه‌چیز pass می‌شود
یک «known-bad» fixture: task که هر probe باید fail شود

✅ معیارهای پذیرش کلی
عملکردی
not done
AC با verify_method=static همان رفتار قبلی verify را دارد (no regression)
not done
AC با verify_method=ui_interaction: playwright headless browser باز می‌کند، steps را اجرا می‌کند، screenshot می‌گیرد، نتیجه برمی‌گرداند
not done
AC با verify_method=api_response: HTTP request می‌رود، status + شِما چک می‌شود
not done
AC با verify_method=backend_test: pytest در subprocess با timeout اجرا می‌شود
not done
AC با verify_method=manual_only: skipped با پیام واضح
not done
هر probe که error داد، verify ادامه می‌دهد (نه crash)
not done
base URL ها قابل تنظیم per project
not done
evidence فایل‌ها روی disk ذخیره می‌شوند، با cleanup policy
not done
PDF و Telegram message شواهد را embed می‌کنند
not done
Frontend modal جدید برای drill-down evidence
کیفی
not done
type-check (mypy + tsc) بدون error
not done
هیچ test موجود fail نمی‌شود
not done
محیط production (Render) با RUNTIME_VERIFY_ENABLED=false کاملاً مثل قبل کار می‌کند (graceful disable)
not done
هیچ probe که فقط برای یک AC شکست خورد، کل verify را crash نکند
کنترل کیفیت verify
not done
روی یک تسک "known-good" (همه AC ها واقعاً پاس شده‌اند) → verify=done
not done
روی یک تسک "known-bad" (UI AC شکست خورده) → AI نمی‌تواند آن را done اعلام کند (runtime override)
not done
روی یک تسک با کد درست ولی deploy نشده → runtime می‌گوید fail (چون probe می‌رود به URL واقعی، نه به کد محلی)

کلیدواژه‌ها:
test_static_probe.py, test_ui_probe.py, test_api_probe.py, test_test_probe.py, test_runner.py, test_runtime_integration.py, known-good fixture, known-bad fixture, verify_method=static, verify_method=ui_interaction, verify_method=api_response, verify_method=backend_test, verify_method=manual_only, RUNTIME_VERIFY_ENABLED, mypy, tsc, pytest, Playwright, httpbin, Render, backend/app/services/verify_runtime/, tests/integration/test_runtime_verify.py

شواهد در کد واقعی: فایل `backend/tests/test_runtime_verify_integration.py` (خطوط 1-180) شامل تست‌های integration فعلی است که از `build_probe_context` و `run_probes_for_acs` استفاده می‌کند. فیکسچرهای `known_good_repo` (خط 30) و

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 14: ساخت inspector_probe برای اتصال خودکار به verify جدید و ضمیمه تلگرامی

**Scope:** این بخش شامل طراحی و پیاده‌سازی یک probe جدید به نام inspector_probe است که به صورت خودکار صفحه دیپلوی‌شده را با Playwright باز می‌کند، screenshot می‌گیرد، console و backend logs را جمع می‌کند، با Vision AI تحلیل می‌کند و نتیجه را به عنوان شواهد در گزارش verify بازمی‌گرداند. همچنین شامل ذخیره‌سازی جلسه بازرسی (inspector_session)، ارسال بسته کامل به تلگرام و حذف خودکار screenshot‌ها از دیسک پس از ارسال موفق است. خارج از این بخش: پیاده‌سازی خود verify، طراحی UI تب بازرس، و مکانیزم‌های ذخیره‌سازی طولانی‌مدت.
**Key terms:** inspector_probe, Playwright, Vision AI, inspector_session, verify, followup prompt, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult

**بخش مربوط از متن کاربر:**
```
ساخت یک probe جدید به اسم inspector_probe که به‌صورت خودکار (بدون مداخله کاربر) صفحه دیپلوی‌شده پروژه را با Playwright سرور-سایدی باز می‌کند، navigate / click می‌کند، screenshot می‌گیرد، console و backend logs را جمع می‌کند، با Vision AI screenshot ها را تحلیل می‌کند و نتیجه را به‌عنوان probe evidence در گزارش verify بازمی‌گرداند. همزمان، تمام مراحل را در یک inspector_session جدید با عنوان «🤖 auto-verify · …» ذخیره می‌کند تا کاربر بتواند از تب بازرس ویژه آن را مرور کند. پس از تمام شدن verify و تولید followup prompt، یک بسته‌ی کامل به تلگرام ارسال می‌شود (گزارش متنی + screenshot ها + پرامپت بروز) و **پس از موفقیت ارسال، screenshot ها از دیسک حذف می‌شوند** تا حافظه‌ی سرور همیشه کم بماند.
```

## 🎯 هدف (خلاصه ساختاریافته)
تکمیل inspector_probe با اتصال به verify و ارسال تلگرامی

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به طراحی و پیاده‌سازی یک probe جدید به نام inspector_probe است که به صورت خودکار (بدون مداخله کاربر) صفحه دیپلوی‌شده پروژه را با Playwright سرور-سایدی باز می‌کند، navigate/click می‌کند، screenshot می‌گیرد، console و backend logs را جمع می‌کند، با Vision AI screenshot‌ها را تحلیل می‌کند و نتیجه را به‌عنوان probe evidence در گزارش verify بازمی‌گرداند. همزمان، تمام مراحل را در یک inspector_session جدید با عنوان «🤖 auto-verify · …» ذخیره می‌کند تا کاربر بتواند از تب بازرس ویژه آن را مرور کند. پس از تمام شدن verify و تولید followup prompt، یک بسته کامل به تلگرام ارسال می‌شود (گزارش متنی + screenshot‌ها + پرامپت بروز) و پس از موفقیت ارسال، screenshot‌ها از دیسک حذف می‌شوند تا حافظه سرور همیشه کم بماند. کلیدواژه‌ها: inspector_probe, Playwright, Vision AI, inspector_session, verify, followup prompt, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult. شواهد در کد: فایل inspector_probe.py (خطوط 1-20) معماری probe را توضیح می‌دهد: باز کردن آدرس با Playwright، ضبط console errors، screenshot قبل و بعد از click، خواندن backend logs از RenderLog DB، تحلیل screenshot با vision_helper، ذخیره اقدامات در inspector_session و برگرداندن RuntimeProbeResult با evidence غنی. فایل vision_helper.py (خطوط 1-10) سه مرحله تحلیل screenshot را مشخص می‌کند: 1) Vision multimodal موجود، 2) fallback متنی با verify_model، 3) خروجی source='none'. فایل scan_inspector_session.py (خطوط 1-19) نحوه ایجاد InspectorSession برای scan را نشان می‌دهد که مشابه verify در Phase 4 است. فایل runner.py (خطوط 1-30) orchestrator اصلی verify runtime را شامل می‌شود که probeها را فراخوانی می‌کند. فایل base.py (خطوط 1-40) کلاس‌های ProbeContext و RuntimeProbeResult را تعریف می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/verify_runtime/inspector_probe.py، تابع run_inspector_probe (خط 243) را بررسی و تکمیل کن تا: a) بعد از اتمام probe و جمع‌آوری evidence، یک inspector_session جدید با عنوان «🤖 auto-verify · [ac_text]» ایجاد کند (با استفاده از create_scan_session از scan_inspector_session.py خط 120). b) تمام مراحل (navigate, click, screenshot, vision analysis) را به‌عنوان پیام‌های InspectorMessage در session ذخیره کند (با استفاده از _save_inspector_message_sync خط 191). c) پس از پایان verify و تولید followup prompt، یک بسته کامل به تلگرام ارسال کند (گزارش متنی + screenshot‌ها + پرامپت بروز) با استفاده از سرویس‌های موجود در oversight_telegram_compose.py. d) پس از موفقیت ارسال تلگرام، screenshot‌ها را از دیسک حذف کند (با استفاده از Path.unlink روی فایل‌های موجود در shot_dir خط 120). 2. در فایل backend/app/services/verify_runtime/vision_helper.py، تابع analyze_screenshot (خط 22) را بررسی کن تا مطمئن شوی fallback chain به درستی کار می‌کند و feature_present را به‌درستی برمی‌گرداند. 3. در فایل backend/app/services/verify_runtime/runner.py، تابع run_verify (خط 50) را اصلاح کن تا بعد از اجرای همه probeها و تولید followup prompt، تابع ارسال تلگرام را صدا بزند. 4. در

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 15: Phase 1: پیاده‌سازی محدودیت‌ها و معماری ذخیره‌سازی screenshot با Vision Fallback Chain

**Scope:** این بخش شامل پیاده‌سازی کامل محدودیت‌های Phase 1 (navigate, click, screenshot, Vision AI, console log, backend log, Telegram attachment, TTL cleanup) و معماری ذخیره‌سازی screenshot روی دیسک با path نسبی در DB است. همچنین شامل Vision Fallback Chain سه‌لایه (Vision model → text-only verify model → none) و ساختار داده probe (RuntimeProbeResult) با شرط‌های pass/fail می‌باشد. فایل‌های جدید inspector_probe.py و vision_helper.py ایجاد می‌شوند و تغییرات در base.py, runner.py, oversight_verifier.py اعمال می‌گردد. محدودیت‌های ایمنی (timeout 60s, max 1 parallel, max 2 screenshots, 500KB cap, circuit breaker, TTL 3 روز) و graceful degrade برای همه شکست‌ها لحاظ شده است.
**Key terms:** backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, backend/app/services/oversight_verifier.py, backend/app/services/oversight_inspector_bridge.py, RuntimeProbeResult, ProbeContext, InspectorSession, describe_screenshot_with_vision, cleanup_orphan_runtime_screenshots, RUNTIME_VERIFY_UI_ENABLED, storage/oversight/runtime_evidence/

**بخش مربوط از متن کاربر:**
```
## محدودیت‌های Phase 1
✅ navigate به URL
✅ click روی selector
✅ screenshot (ذخیره روی دیسک، نه base64 در DB)
✅ Vision AI تحلیل screenshot (با fallback chain)
✅ console log capture
✅ backend log correlation
✅ ضمیمه‌ی تلگرامی + cleanup
✅ TTL cleanup خودکار برای orphan screenshots
❌ fill / submit / wait → Phase 2
❌ login / auth → Phase 3
❌ multi-step complex sequences → Phase 2
---
## معماری ذخیره‌سازی screenshot
**روی دیسک، نه DB:**
- مسیر: storage/oversight/runtime_evidence/{task_id}/{run_id}/{ac_id}/{label}.png
- مثلاً: storage/oversight/runtime_evidence/task_abc/run_xyz/ac01_h/after_navigate.png
**در DB (inspector_message.extra_data) فقط:**
- path نسبی به فایل
- label
- vision_description (متن استخراج‌شده — این مهم‌ترین artifact است)
- timestamp
---
## Vision Fallback Chain (مهم)
برای هر screenshot، به این ترتیب تلاش کن:
**1. Vision موجود در سیستم (همان منطق تب بازرسی):**
- describe_screenshot_with_vision() در backend/app/services/oversight_inspector_bridge.py:44
**2. اگر مرحله 1 خطا داد یا API key نبود → fallback به verify model:**
- مدل verify (مثل deepseek-chat) text-only است
- یک پرامپت ساده: «بر اساس این لاگ‌ها و HTML، چه چیزی روی صفحه دیده می‌شد؟»
- خروجی با source="fallback_text_only"
**3. اگر هر دو شکست خوردند → فقط screenshot path ذخیره می‌شود:**
- vision_description = None
---
## ساختار داده probe
نتیجه‌ی run_inspector_probe RuntimeProbeResult با ساختار:
{
  ac_id, ac_text, method: "ui_interaction", status: "passed" | "failed" | "error" | "skipped",
  evidence: {
    inspector_session_id: int,
    actions_taken: [{action: "navigate", url: "/login", duration_ms: 1234}, ...],
    screenshots: [{path, label, vision_description, vision_source, archived_to_telegram}],
    console_errors: [{level, message, source, timestamp}],
    backend_log_summary: "...",
    final_url: "...",
    assertion_results: [{expectation, met, reason}]
  },
  duration_ms: int,
  error_message: Optional[str]
}
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی محدودیت‌ها و معماری ذخیره‌سازی screenshot با Vision Fallback Chain

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_inspector_bridge.py:44-285` — `describe_screenshot_with_vision`
  ```python
  async def describe_screenshot_with_vision(
      base64_img: str,
      user_context: str,
      page_url: str = "",
      dom_text: str = "",
  ) -> Dict[str, Any]:
      """با vision model عکس را به متن غنی تبدیل
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک شامل پیاده‌سازی کامل محدودیت‌های Phase 1 (navigate, click, screenshot, Vision AI, console log, backend log, Telegram attachment, TTL cleanup) و معماری ذخیره‌سازی screenshot روی دیسک با path نسبی در DB است. همچنین شامل Vision Fallback Chain سه‌لایه (Vision model → text-only verify model → none) و ساختار داده probe (RuntimeProbeResult) با شرط‌های pass/fail می‌باشد. فایل‌های جدید inspector_probe.py و vision_helper.py در backend/app/services/verify_runtime/ ایجاد می‌شوند و تغییرات در base.py, runner.py, oversight_verifier.py اعمال می‌گردد. محدودیت‌های ایمنی (timeout 60s, max 1 parallel, max 2 screenshots, 500KB cap, circuit breaker, TTL 3 روز) و graceful degrade برای همه شکست‌ها لحاظ شده است. مسیر ذخیره‌سازی: storage/oversight/runtime_evidence/{task_id}/{run_id}/{ac_id}/{label}.png. در DB فقط path نسبی، label، vision_description و timestamp ذخیره می‌شود. Vision Fallback Chain: 1) describe_screenshot_with_vision() در oversight_inspector_bridge.py:44، 2) fallback به verify model text-only با پرامپت ساده، 3) فقط screenshot path. ساختار RuntimeProbeResult شامل ac_id, ac_text, method: ui_interaction, status: passed/failed/error/skipped, evidence با inspector_session_id, actions_taken, screenshots, console_errors, backend_log_summary, final_url, assertion_results, duration_ms, error_message. کلیدواژه‌ها: backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, backend/app/services/oversight_verifier.py, backend/app/services/oversight_inspector_bridge.py, RuntimeProbeResult, ProbeContext, InspectorSession, describe_screenshot_with_vision, cleanup_orphan_runtime_screenshots, RUNTIME_VERIFY_UI_ENABLED, storage/oversight/runtime_evidence/

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل جدید backend/app/services/verify_runtime/inspector_probe.py با کلاس RuntimeProbeResult و تابع run_inspector_probe که محدودیت‌های Phase 1 (navigate, click, screenshot, console log, backend log) را پیاده‌سازی می‌کند. 2. ایجاد فایل جدید backend/app/services/verify_runtime/vision_helper.py با Vision Fallback Chain سه‌لایه: اول describe_screenshot_with_vision از oversight_inspector_bridge.py:44، دوم fallback به text-only verify model، سوم ذخیره path بدون description. 3. تغییر در backend/app/services/verify_runtime/base.py برای اضافه کردن RUNTIME_VERIFY_UI_ENABLED و مسیر ذخیره‌سازی storage/oversight/runtime_evidence/. 4. تغییر در backend/app/services/verify_runtime/runner.py برای پشتیبانی از ui_interaction method و فراخوانی inspector_probe. 5. تغییر در backend/app/services/oversight_verifier.py برای اضافه کردن تابع cleanup_orphan_runtime_screenshots با TTL 3 روز. 6. پیاده‌سازی circuit breaker با max 1 parallel و timeout 60s. 7. محدودیت max 2 screenshots با 500KB cap. 8. ذخیره screenshot روی دیسک با path نسبی و فقط metadata در DB.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 16: سه فیکس جدید پس از تست Phase 2: چک‌لیست در متن تلگرام، تبدیل bundle به PDF، بهبود vision prompt برای تشخیص feature

**Scope:** این بخش شامل سه فیکس مستقل است که باید هم‌اکنون اجرا شوند. فیکس ۱: اضافه کردن خلاصه چک‌لیست task_steps به متن پیام تلگرام (نه فقط پیوست). فیکس ۲: تبدیل mega-bundle از HTML به PDF با پشتیبانی فارسی و fallback به HTML. فیکس ۳: بهبود vision prompt برای تشخیص حضور feature در صفحه و تأثیر آن بر pass/fail probe. بخش الف (Phase 2) قبلاً اجرا شده و فقط برای مرجع است — نباید دوباره اجرا شود.
**Key terms:** _send_verify_notification_bg, oversight_verify_pdf.py, build_verify_checklist_message, oversight_mega_bundle.py, build_mega_bundle_pdf, build_mega_bundle_md, oversight_verifier.py, _send_mega_bundle, vision_helper.py, analyze_screenshot, inspector_probe.py, feature_present, feature_reason, frontend/src/app/oversight/page.tsx, ReportLab, Vazir, Tahoma

**بخش مربوط از متن کاربر:**
```
## فیکس ۱ — چک‌لیست به‌روز در متن پیام تلگرام
### هدف
در `_send_verify_notification_bg`، متن نوتیفیکیشن (مستقل از پیوست) باید شامل خلاصهٔ chk‌لیست به‌روز task_steps باشد:
📋 چک‌لیست (X/N انجام‌شده):
[✅] مرحله ۱: عنوان (100%)
[~] مرحله ۲: عنوان (50%) — باقی‌مانده: «چی مونده»
[ ] مرحله ۳: عنوان (0%)
...

## فیکس ۲ — تبدیل bundle از HTML به PDF
### هدف
mega-bundle که الان `.html` است را به `.pdf` تبدیل کن تا روی موبایل بدون نیاز به browser در همان viewer تلگرام باز شود.

## فیکس ۳ — بهبود vision prompt برای تشخیص feature
### هدف
vision در حال حاضر فقط صفحه را توصیف می‌کند. باید صریحاً تشخیص دهد «آیا feature ذکرشده در AC در این صفحه قابل مشاهده است یا نه؟» و این تشخیص روی pass/fail probe تأثیر بگذارد.
```

## 🎯 هدف (خلاصه ساختاریافته)
سه فیکس Phase 2: چک‌لیست تلگرام، PDF bundle، بهبود vision prompt

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
سه فیکس مستقل پس از تست Phase 2 که باید هم‌اکنون اجرا شوند:

**فیکس ۱ — چک‌لیست به‌روز در متن پیام تلگرام**
در `_send_verify_notification_bg` (فایل `backend/app/services/oversight_verifier.py`)، متن نوتیفیکیشن (مستقل از پیوست) باید شامل خلاصهٔ چک‌لیست به‌روز task_steps باشد:
📋 چک‌لیست (X/N انجام‌شده):
[✅] مرحله ۱: عنوان (100%)
[~] مرحله ۲: عنوان (50%) — باقی‌مانده: «چی مونده»
[ ] مرحله ۳: عنوان (0%)
...

**فیکس ۲ — تبدیل bundle از HTML به PDF**
mega-bundle که الان `.html` است را به `.pdf` تبدیل کن تا روی موبایل بدون نیاز به browser در همان viewer تلگرام باز شود. فایل‌های مرتبط: `backend/app/services/oversight_mega_bundle.py` (تابع `build_mega_bundle_md` و `build_mega_bundle_pdf`)، `backend/app/services/oversight_verify_pdf.py`، `backend/app/services/oversight_verifier.py` (تابع `_send_mega_bundle`). کتابخانه‌های پیشنهادی: ReportLab با فونت فارسی Vazir یا Tahoma.

**فیکس ۳ — بهبود vision prompt برای تشخیص feature**
vision در حال حاضر فقط صفحه را توصیف می‌کند. باید صریحاً تشخیص دهد «آیا feature ذکرشده در AC در این صفحه قابل مشاهده است یا نه؟» و این تشخیص روی pass/fail probe تأثیر بگذارد. فایل‌های مرتبط: `backend/app/services/verify_runtime/vision_helper.py` (تابع `analyze_screenshot`)، `backend/app/services/verify_runtime/inspector_probe.py` (فیلدهای `feature_present` و `feature_reason`).

کلیدواژه‌های کاربر: `_send_verify_notification_bg`, `oversight_verify_pdf.py`, `build_verify_checklist_message`, `oversight_mega_bundle.py`, `build_mega_bundle_pdf`, `build_mega_bundle_md`, `oversight_verifier.py`, `_send_mega_bundle`, `vision_helper.py`, `analyze_screenshot`, `inspector_probe.py`, `feature_present`, `feature_reason`, `frontend/src/app/oversight/page.tsx`, `ReportLab`, `Vazir`, `Tahoma`

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مراحل پیاده‌سازی:

**فیکس ۱ — چک‌لیست در متن تلگرام:**
1. در `backend/app/services/oversight_verifier.py`، تابع `_send_verify_notification_bg` را پیدا کن.
2. یک تابع جدید `build_verify_checklist_message(task)` ایجاد کن که از `task.task_steps` (لیست دیکشنری‌های دارای `title`, `status`, `completion_pct`) یک متن فرمت‌شده با ایموجی‌های [✅], [~], [ ] بسازد.
3. این متن را به `notification_text` اضافه کن (قبل از بخش پیوست).
4. اگر `task_steps` خالی بود، این بخش را اضافه نکن.

**فیکس ۲ — تبدیل bundle به PDF:**
1. در `backend/app/services/oversight_mega_bundle.py`، تابع `build_mega_bundle_pdf` را اصلاح کن تا از ReportLab با فونت Vazir یا Tahoma برای تولید PDF استفاده کند.
2. فونت فارسی را در مسیر `backend/fonts/` قرار بده (اگر نیست، از فونت‌های سیستمی استفاده کن).
3. محتوای مارک‌داون را به صورت ساده (عنوان‌ها، پاراگراف‌ها، لیست‌ها) به PDF تبدیل کن.
4. fallback به HTML اگر playwright در دسترس نباشد (همان منطق فعلی

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 17: مرور سریع Phase 1 و 2 و سه فیکس آخر — آماده‌سازی برای Phase 3

**Scope:** این بخش صرفاً یک مرور (review) از قابلیت‌های پیاده‌سازی شده در Phase 1، Phase 2 و سه فیکس آخر است. هیچ کار اجرایی جدیدی در این بخش تعریف نشده و صرفاً برای یادآوری وضعیت فعلی پروژه قبل از شروع Phase 3 ارائه شده است. تمام آیتم‌های ذکر شده قبلاً اجرا شده‌اند.
**Key terms:** inspector_probe.py, vision_helper.py, inspector_session, oversight_verifier.py, oversight_strong_prompt.py, oversight_service.py, oversight_verify_pdf.py, oversight_inspector_bridge.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult

**بخش مربوط از متن کاربر:**
```
✅ **Phase 1** اضافه کرد:
- inspector_probe.py — Playwright server-side با navigate + click +
  screenshot + console capture + backend log query
- vision_helper.py با fallback chain (multimodal → text-only → none)
- inspector_session با عنوان «🤖 auto-verify · …» برای visibility
- TTL cleanup + startup recovery + telegram screenshot+followup
✅ **Phase 2** اضافه کرد:
- Per-step probes با route inferred از step.title/scope
- Network capture (frontend + backend URLs per probe)
- Step-aware AI verifier prompt
- prompt_history + apply_followup_as_new_prompt + revert endpoint
- mega-bundle (PDF با fallback HTML)
✅ **سه فیکس آخر** اضافه کرد:
- چک‌لیست در caption تلگرام
- Bundle PDF (نه HTML)
- Vision `feature_present` (yes/no/unclear) با pass/fail flip
```

## 🎯 هدف (خلاصه ساختاریافته)
مرور و مستندسازی Phase 1 و 2 و سه فیکس آخر برای آماده‌سازی Phase 3

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک یک مرور (review) از قابلیت‌های پیاده‌سازی شده در Phase 1، Phase 2 و سه فیکس آخر است. هیچ کار اجرایی جدیدی در این بخش تعریف نشده و صرفاً برای یادآوری وضعیت فعلی پروژه قبل از شروع Phase 3 ارائه شده است. تمام آیتم‌های ذکر شده قبلاً اجرا شده‌اند.

✅ **Phase 1** اضافه کرد:
- `inspector_probe.py` — Playwright server-side با navigate + click + screenshot + console capture + backend log query
- `vision_helper.py` با fallback chain (multimodal → text-only → none)
- `inspector_session` با عنوان «🤖 auto-verify · …» برای visibility
- TTL cleanup + startup recovery + telegram screenshot+followup

✅ **Phase 2** اضافه کرد:
- Per-step probes با route inferred از step.title/scope
- Network capture (frontend + backend URLs per probe)
- Step-aware AI verifier prompt
- `prompt_history` + `apply_followup_as_new_prompt` + revert endpoint
- mega-bundle (PDF با fallback HTML)

✅ **سه فیکس آخر** اضافه کرد:
- چک‌لیست در caption تلگرام
- Bundle PDF (نه HTML)
- Vision `feature_present` (yes/no/unclear) با pass/fail flip

کلیدواژه‌ها: `inspector_probe.py`, `vision_helper.py`, `inspector_session`, `oversight_verifier.py`, `oversight_strong_prompt.py`, `oversight_service.py`, `oversight_verify_pdf.py`, `oversight_inspector_bridge.py`, `backend/app/services/verify_runtime/vision_helper.py`, `backend/app/services/verify_runtime/inspector_probe.py`, `backend/app/services/verify_runtime/base.py`, `backend/app/services/verify_runtime/runner.py`, `RuntimeProbeResult`, `ProbeContext`, `InspectorSession`, `VerifyContext`, `VerifyConfig`, `ProbeResult`

شواهد در کد واقعی:
- در `backend/app/services/verify_runtime/inspector_probe.py` خطوط 1-20: توضیحات کامل Phase 1 شامل Playwright server-side، console errors، screenshot، backend logs، vision analysis و ذخیره در inspector_session.
- در `backend/app/services/verify_runtime/vision_helper.py` خطوط 1-10: fallback chain سه‌مرحله‌ای (multimodal → text-only → none).
- در `backend/app/services/oversight_inspector_bridge.py` خطوط 1-13: bridge بین Inspector و Oversight با strong prompt و vision description.
- در `backend/app/services/oversight_verify_pdf.py`: mega-bundle PDF با fallback HTML.
- در `backend/app/services/oversight_verifier.py`: step-aware AI verifier prompt و prompt_history.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک صرفاً یک مرور (review) است و نیازی به تغییر کد ندارد. اما برای آماده‌سازی Phase 3، پیشنهاد می‌شود:

1. **مستندسازی کامل**: یک فایل `docs/PHASE_1_2_REVIEW.md` ایجاد شود که شامل:
   - خلاصه قابلیت‌های Phase 1 و 2
   - لیست فایل‌های تغییر یافته با لینک به خطوط کلیدی
   - توضیح سه فیکس آخر
   - نقشه وابستگی‌ها بین ماژول‌ها

2. **بررسی یکپارچگی**: اطمینان از اینکه تمام endpointهای مرتبط (مانند `apply_followup_as_new_prompt` و `revert` در `oversight_verifier.py`) به درستی کار می‌کنند.

3. **آماده‌سازی برای Phase 3**: شناسایی نقاط ضعف فعلی:
   - محدودیت `_MAX_UI_STEPS = 12` در `inspector_probe.py` خط 56
   - عدم پشتیبانی از multi-page flows
   - نبود caching برای vision results

4. **بهبود لاگینگ**: اضافه کردن لاگ‌های بیشتر در `inspector_probe

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 18: رفع محدودیت‌های Phase 2: تعامل با UI، تشخیص دقیق‌تر، لاگین و submit فرم

**Scope:** این بخش چهار محدودیت اصلی Phase 2 را مشخص می‌کند که Phase 3 باید حل کند: (1) ناتوانی probe در تعامل با feature (مثلاً کلیک روی دکمه)، (2) false-positive بالای vision در تشخیص feature_present، (3) عدم امکان بررسی صفحات نیازمند لاگین، (4) عدم توانایی تست ACهای نیازمند submit فرم. این محدودیت‌ها از تست واقعی Phase 2 و سه فیکس استخراج شده‌اند.
**Key terms:** probe, feature_present, selector_hint, /admin/dashboard, /login, submit فرم, Phase 3

**بخش مربوط از متن کاربر:**
```
# محدودیت‌های فعلی که Phase 3 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 2 + سه فیکس مشخص شد:
1. **probe فقط navigate می‌کند و نگاه می‌کند** — نمی‌تواند با feature
   تعامل کند. اگر feature یک دکمه باشد، probe دکمه را نمی‌زند تا
   ببیند modal باز می‌شود یا نه.
2. **Vision feature_present حدود ۴۰٪ false-positive دارد** —
   step probe 2 «اضافه کردن UI انتخاب محتوا» را passed داد در حالی
   که UI ساخته نشده بود. علت: vision دکمه‌های عمومی صفحه را دید و
   فکر کرد همینه. اگر probe می‌توانست «کلیک روی selector_hint و
   چک کردن modal/result» را انجام دهد، تشخیص دقیق‌تر بود.
3. **صفحات با لاگین قابل بررسی نیستند** — مثلاً اگر کاربر تسکی روی
   `/admin/dashboard` تعریف کند، probe redirect به /login می‌خورد
   و تشخیص «این feature ساخته شده» غلط می‌شود (همان مشکلی که در
   system probe رخ داد — vision گفت «صفحه login می‌بینم»).
4. **AC هایی که نیاز به submit فرم دارند نمی‌توانند تست شوند** —
   مثلاً «وقتی فرم لاگین پر شود و submit شود، کاربر به داشبورد می‌رود».
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع محدودیت‌های Phase 2: تعامل UI، تشخیص دقیق‌تر، لاگین و submit فرم

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک چهار محدودیت اصلی Phase 2 را که از تست واقعی Phase 2 و سه فیکس استخراج شده‌اند، در لایه‌ی verify_runtime رفع می‌کند. محدودیت‌ها عبارتند از: (1) probe فقط navigate می‌کند و نگاه می‌کند — نمی‌تواند با feature تعامل کند. اگر feature یک دکمه باشد، probe دکمه را نمی‌زند تا ببیند modal باز می‌شود یا نه. (2) Vision feature_present حدود ۴۰٪ false-positive دارد — step probe 2 «اضافه کردن UI انتخاب محتوا» را passed داد در حالی که UI ساخته نشده بود. علت: vision دکمه‌های عمومی صفحه را دید و فکر کرد همینه. اگر probe می‌توانست «کلیک روی selector_hint و چک کردن modal/result» را انجام دهد، تشخیص دقیق‌تر بود. (3) صفحات با لاگین قابل بررسی نیستند — مثلاً اگر کاربر تسکی روی `/admin/dashboard` تعریف کند، probe redirect به /login می‌خورد و تشخیص «این feature ساخته شده» غلط می‌شود (همان مشکلی که در system probe رخ داد — vision گفت «صفحه login می‌بینم»). (4) AC هایی که نیاز به submit فرم دارند نمی‌توانند تست شوند — مثلاً «وقتی فرم لاگین پر شود و submit شود، کاربر به داشبورد می‌رود». کلیدواژه‌ها: probe, feature_present, selector_hint, /admin/dashboard, /login, submit فرم, Phase 3. در کد فعلی، فایل‌های `backend/app/services/verify_runtime/ui_probe.py` و `backend/app/services/verify_runtime/runner.py` و `backend/app/services/verify_runtime/iterative_orchestrator.py` و `backend/app/services/verify_runtime/code_aware_verifier.py` و `backend/app/services/verify_runtime/auth_runner.py` و `backend/app/services/verify_runtime/navigation_helper.py` و `backend/app/services/verify_runtime/ac_schema.py` و `backend/app/services/verify_runtime/ac_enricher.py` و `backend/app/services/verify_runtime/context_builder.py` و `backend/app/services/verify_runtime/base.py` و `backend/app/services/verify_runtime/browser_pool.py` و `backend/app/services/verify_runtime/safety.py` و `backend/app/services/verify_runtime/storage.py` و `backend/app/services/verify_runtime/static_probe.py` و `backend/app/services/verify_runtime/api_probe.py` و `backend/app/services/verify_runtime/manual_probe.py` و `backend/app/services/verify_runtime/test_probe.py` و `backend/app/services/verify_runtime/backend_log_probe.py` و `backend/app/services/verify_runtime/inspector_probe.py` و `backend/app/services/verify_runtime/render_autodetect.py` و `backend/app/services/verify_runtime/vision_helper.py` و `backend/app/services/verify_runtime/code_content_searcher.py` و `backend/app/services/verify_runtime/ac_cache_service.py` و `backend/app/services/verify_runtime/ac_schema.py` و `backend/app/services/verify_runtime/ac_enricher.py` و `backend/app/services/verify_runtime/context_builder.py` و `backend/app/services/verify_runtime/base.py` و `backend/app/services/verify_runtime/browser_pool.py` و `backend/app/services/verify_runtime/safety.py` و `backend/app/services/verify_runtime/storage.py` و `backend/app/services/verify_runtime/static_probe.py` و `backend/app/services/verify_runtime/api_probe.py` و `backend/app/services/verify_runtime/manual_probe.py` و `backend/app/services/verify_runtime/test_probe.py` و `backend/app/services/verify_runtime/backend_log_probe.py` و `backend/app/services/verify_runtime/inspector_probe.py` و `backend/app/services/verify_runtime/render_autodetect.py` و `backend/app/services/verify_runtime/vision_helper.py` و `backend/app/services/verify_runtime/code_content_searcher.py` و `backend/app/services/verify_runtime/ac_cache_service.py`

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 19: Phase 3: پیاده‌سازی سه قابلیت متمم (Form Interaction, Auth Management, Enhanced Detection)

**Scope:** این بخش شامل پیاده‌سازی کامل سه قابلیت متمم در Phase 3 است: (A) پشتیبانی از Form/Input Interaction Recipes در inspector_probe با 16 action مختلف، (B) مدیریت Authentication/Session با auto-detect login redirect و auth recipe، (C) Enhanced Feature Detection با multi-screenshot و before/after analysis. تمام تغییرات در فایل‌های backend متمرکز است و frontend را شامل نمی‌شود. نکته حیاتی: AI enricher باید برای method=ui_interaction یک sequence 3-8 step واقعی پیشنهاد دهد.
**Key terms:** inspector_probe, verify_plan.ui_steps, ui_probe, _execute_ui_step, SUPPORTED_ACTIONS, WatchedProject, runtime_auth, ac_enricher.py, oversight_service.py, backend/app/services/verify_runtime/inspector_probe.py

**بخش مربوط از متن کاربر:**
```
# هدف کلی Phase 3 — سه قابلیت متمم
══════════════════════════════════════════════════════════════════════
**A) Form/Input Interaction Recipes**
inspector_probe باید پشتیبانی کند از:
- `fill {selector, value}` — تایپ متن در input/textarea
- `submit {form_selector}` یا کلیک روی دکمهٔ submit
- `wait_for {selector, timeout_ms, state}` — صبر تا المنت ظاهر شود
- `select {selector, option}` — انتخاب از dropdown
- `check {selector}` / `uncheck {selector}` — checkbox/radio
- `hover {selector}` — برای tooltip ها
- `wait_for_url {contains}` — صبر تا URL تغییر کند (برای SPA)
این actions در `verify_plan.ui_steps` تعریف می‌شوند (schema موجود ui_probe).

**B) Authentication / Session Management**
WatchedProject از قبل فیلد `runtime_auth: {type, value}` دارد. الان ui_probe (نه inspector_probe) فقط ازش استفاده می‌کند. باید:
- inspector_probe هم cookie/bearer auth را اعمال کند قبل از navigate
- Auto-detect login redirect → اگر صفحه به /login redirect شد، evidence را با وضعیت «نیاز به لاگین» علامت بزن
- Auth recipe در WatchedProject — یک sequence «navigate to /login → fill email → fill password → submit → wait_for_url(/dashboard)»

**C) Enhanced Feature Detection (multi-screenshot + before/after)**
به‌جای یک screenshot واحد:
- screenshot قبل از interaction
- screenshot بعد از interaction
- Vision آنالیز diff: «بعد از کلیک، چه چیزی روی صفحه ظاهر شد؟»
- Network call analysis: آیا interaction باعث backend call شد؟
- اگر AC انتظار modal دارد، چک کن modal واقعاً ظاهر شد
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی سه قابلیت متمم Phase 3 در inspector_probe و ac_enricher

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک شامل پیاده‌سازی کامل سه قابلیت متمم در Phase 3 است: (A) پشتیبانی از Form/Input Interaction Recipes در inspector_probe با 16 action مختلف شامل fill, submit, wait_for, select, check, uncheck, hover, wait_for_url و غیره که در verify_plan.ui_steps تعریف می‌شوند. (B) مدیریت Authentication/Session با auto-detect login redirect و auth recipe — WatchedProject از قبل فیلد runtime_auth: {type, value} دارد و ui_probe (نه inspector_probe) فقط ازش استفاده می‌کند. باید inspector_probe هم cookie/bearer auth را اعمال کند قبل از navigate، auto-detect login redirect کند (اگر صفحه به /login redirect شد، evidence را با وضعیت «نیاز به لاگین» علامت بزند)، و auth recipe در WatchedProject شامل sequence «navigate to /login → fill email → fill password → submit → wait_for_url(/dashboard)» باشد. (C) Enhanced Feature Detection با multi-screenshot و before/after analysis — به‌جای یک screenshot واحد: screenshot قبل از interaction، screenshot بعد از interaction، Vision آنالیز diff، Network call analysis، و بررسی ظهور modal. تمام تغییرات در فایل‌های backend متمرکز است و frontend را شامل نمی‌شود. نکته حیاتی: AI enricher (فایل backend/app/services/verify_runtime/ac_enricher.py) باید برای method=ui_interaction یک sequence 3-8 step واقعی پیشنهاد دهد. کلیدواژه‌ها: inspector_probe, verify_plan.ui_steps, ui_probe, _execute_ui_step, SUPPORTED_ACTIONS, WatchedProject, runtime_auth, ac_enricher.py, oversight_service.py, backend/app/services/verify_runtime/inspector_probe.py. شواهد در کد: در inspector_probe.py خط 60-65 مجموعه SUPPORTED_ACTIONS شامل 13 action است (navigate, click, fill, submit, select, check, uncheck, hover, wait_for, wait_for_url, wait_for_load, screenshot, scroll_to, press_key, assert_visible, assert_text, assert_url) که 16 action را پوشش می‌دهد اما برخی مانند fill, submit, select, check, uncheck, hover, wait_for_url پیاده‌سازی کامل در _execute_ui_step ندارند. در خط 56 _MAX_UI_STEPS = 12 تعریف شده. در خط 44 _TIMEOUT_S = 90. در خط 563-614 action loop برای اجرای sequence وجود دارد اما تابع _execute_ui_step (خط 590) باید توسعه یابد. در oversight_service.py خط 165 WatchedProject فیلد verify_mode: str = "deep" دارد و خط 233 runtime_auth فیلد دارد اما inspector_probe از آن استفاده نمی‌کند. در ac_enricher.py خط 70-84 نمونه ui_steps با 3-8 مرحله پیشنهاد شده اما باید در عمل sequence واقعی تولید کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. مرحله 1: در فایل backend/app/services/verify_runtime/inspector_probe.py، تابع _execute_ui_step (خط 590) را توسعه دهید تا action های fill, submit, select, check, uncheck, hover, wait_for_url را پشتیبانی کند. برای fill از page.fill(selector, value) استفاده کنید، برای submit از page.click('button[type=submit]') یا form.submit()، برای select از page.select_option(selector, option)، برای check/uncheck از page.check()/page.uncheck()، برای hover از page.hover()، برای wait_for_url از page.wait_for_url(contains). مرحله 2: در inspector_probe.py، در تابع _run_inspector_inner (خط 307)، قبل از navigate (خط 431)، auth را از WatchedProject.runtime_auth (که از طریق ctx یا plan قابل دسترسی است) بخوانید و cookie/bearer header را به context اضافه کنید. از browser.add_cookies() یا context.set_extra_http_headers() استفاده کنید. مرحله 3: در inspector_probe.py، بعد از navigate (خط 470)، auto-detect login redirect را پیاده‌سازی کنید (خطوط 476-486 فعلاً وجود دارد اما باید کامل شود). اگر final_url به /login یا /signin redirect شد، auth_required=True ست شود

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 20: پیاده‌سازی auth recipe برای probe‌ها در runtime verification

**Scope:** این بخش مربوط به افزودن قابلیت احراز هویت خودکار (auth recipe) به فرآیند runtime verification است. شامل طراحی ساختار داده runtime_auth_recipe از نوع Optional[Dict]، پیاده‌سازی flow لاگین مبتنی بر فرم (form_login) با مراحل گام‌به‌گام (fill, click, wait_for_url)، ذخیره‌سازی storage_state (cookies + localStorage) برای استفاده probe‌ها، و مکانیزم refresh خودکار بر اساس session_ttl_minutes. خارج از scope: پیاده‌سازی خود probe‌ها، logic verification، و مدیریت خطاهای network.
**Key terms:** runtime_auth_recipe, form_login, storage_state, session_ttl_minutes, success_indicator, login_url, value_env, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/base.py, ProbeContext, VerifyConfig

**بخش مربوط از متن کاربر:**
```
# 🆕 (Phase 3) — auth recipe برای probe ها
# اگر تنظیم شد، قبل از هر verify run یک login flow اجرا می‌شود و
# storage_state (cookies + localStorage) برای استفاده‌ی probe ها
# ذخیره می‌شود.
runtime_auth_recipe: Optional[Dict[str, Any]] = None
# ساختار:
# {
#   "type": "form_login",
#   "login_url": "/login",
#   "steps": [
#     {"action": "fill", "selector": "input[name=email]",
#      "value_env": "TEST_EMAIL"},  # یا "value": "test@test.com"
#     {"action": "fill", "selector": "input[name=password]",
#      "value_env": "TEST_PASSWORD"},
#     {"action": "click", "selector": "button[type=submit]"},
#     {"action": "wait_for_url", "contains": "/dashboard",
#      "timeout_ms": 5000},
#   ],
#   "success_indicator": {"selector": "[data-testid='user-menu']",
#                         "must_exist": true},
#   "session_ttl_minutes": 30,  # storage_state بعد از این مدت refresh
# }
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن auth recipe به runtime verification runner

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی auth recipe برای probe‌ها در runtime verification. این تسک مربوط به افزودن قابلیت احراز هویت خودکار (auth recipe) به فرآیند runtime verification است. شامل طراحی ساختار داده runtime_auth_recipe از نوع Optional[Dict]، پیاده‌سازی flow لاگین مبتنی بر فرم (form_login) با مراحل گام‌به‌گام (fill, click, wait_for_url)، ذخیره‌سازی storage_state (cookies + localStorage) برای استفاده probe‌ها، و مکانیزم refresh خودکار بر اساس session_ttl_minutes. خارج از scope: پیاده‌سازی خود probe‌ها، logic verification، و مدیریت خطاهای network.

بخش مربوط از درخواست اصلی کاربر:
# 🆕 (Phase 3) — auth recipe برای probe ها
# اگر تنظیم شد، قبل از هر verify run یک login flow اجرا می‌شود و
# storage_state (cookies + localStorage) برای استفاده‌ی probe ها
# ذخیره می‌شود.
runtime_auth_recipe: Optional[Dict[str, Any]] = None
# ساختار:
# {
#   "type": "form_login",
#   "login_url": "/login",
#   "steps": [
#     {"action": "fill", "selector": "input[name=email]",
#      "value_env": "TEST_EMAIL"},  # یا "value": "test@test.com"
#     {"action": "fill", "selector": "input[name=password]",
#      "value_env": "TEST_PASSWORD"},
#     {"action": "click", "selector": "button[type=submit]"},
#     {"action": "wait_for_url", "contains": "/dashboard",
#      "timeout_ms": 5000},
#   ],
#   "success_indicator": {"selector": "[data-testid='user-menu']",
#                         "must_exist": true},
#   "session_ttl_minutes": 30,  # storage_state بعد از این مدت refresh
# }

کلیدواژه‌ها: runtime_auth_recipe, form_login, storage_state, session_ttl_minutes, success_indicator, login_url, value_env, backend/app/services/verify_runtime/runner.py, backend/app/services/verify_runtime/base.py, ProbeContext, VerifyConfig

شواهد در کد واقعی: فایل‌های backend/app/services/verify_runtime/runner.py و backend/app/services/verify_runtime/base.py در deep context موجود نیستند، اما بر اساس ساختار پروژه و import map، runner.py و base.py هستهٔ اصلی runtime verification هستند. base.py شامل کلاس‌های پایه مانند ProbeContext و VerifyConfig است که باید runtime_auth_recipe به آن‌ها اضافه شود. runner.py مسئول orchestration اجرای probe‌هاست و باید login flow را قبل از اجرای probe‌ها فراخوانی کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/verify_runtime/base.py، به کلاس VerifyConfig فیلد runtime_auth_recipe از نوع Optional[Dict[str, Any]] با مقدار پیش‌فرض None اضافه شود. همچنین به ProbeContext فیلد storage_state از نوع Optional[Dict] اضافه شود تا probe‌ها بتوانند از cookies و localStorage استفاده کنند.

2. در فایل backend/app/services/verify_runtime/runner.py، یک متد جدید به نام _execute_auth_recipe ایجاد شود که:
   - اگر runtime_auth_recipe None باشد، مستقیماً برگردد.
   - بر اساس type (form_login) flow مناسب را اجرا کند.
   - مراحل steps را به ترتیب اجرا کند: fill (پر کردن فیلد با value یا value_env)، click (کلیک روی selector)، wait_for_url (منتظر ماندن برای URL حاوی contains).
   - بعد از اتمام steps، success_indicator را بررسی کند (selector باید must_exist باشد).
   - در صورت موفقیت، storage_state (cookies + localStorage) را ذخیره کند.
   - session_ttl_minutes را برای تعیین زمان انقضای storage_state ذخیره کند.

3. در runner.py، قبل از اجرای هر probe (در حلقهٔ اجرای probe‌ها

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 21: پیاده‌سازی کش رمزنگاری‌شده storage_state و پشتیبانی از آن در probe و verifier

**Scope:** این بخش شامل سه تغییر است: (1) ایجاد تابع `obtain_or_refresh_storage_state` در فایل جدید `auth_runner.py` که storage_state را با AES-GCM رمزنگاری کرده و در حافظه کش می‌کند، (2) افزودن پشتیبانی از `ProbeContext.storage_state` در `inspector_probe.py` برای استفاده از storage_state موجود در context مرورگر، (3) تغییر در `oversight_verifier.py` برای استفاده از storage_state قبل از ساخت ProbeContext. خارج از scope: پیاده‌سازی خود recipe steps، مدیریت خطاهای غیر از login، و تست‌های یکپارچه‌سازی.
**Key terms:** auth_runner.py, obtain_or_refresh_storage_state, _encrypt_storage, _decrypt_storage, AES-GCM, OVERSIGHT_AUTH_KEY, inspector_probe.py, ProbeContext.storage_state, oversight_verifier.py, _verify_task, runtime_storage_state, runtime_auth_recipe

**بخش مربوط از متن کاربر:**
```
# 🆕 (Phase 3) — cached storage state (encrypted)
runtime_storage_state: Optional[Dict[str, Any]] = None
# {
#   "encrypted_blob": str,  # AES-GCM encrypted JSON storage_state
#   "expires_at": ISO,
#   "obtained_at": ISO,
#   "login_failed_count": int,
# }
Backend — فایل جدید
backend/app/services/verify_runtime/auth_runner.py:

تابع async def obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict[str, Any]]:

اگر runtime_auth_recipe تنظیم نشده → return None
اگر runtime_storage_state معتبر و expires_at > now و force=False →
decrypt و return
در غیر این صورت: launch Chromium → execute recipe.steps → اگر
success_indicator OK → دریافت storage_state از context →
encrypt → ذخیره در watched → return decoded
اگر login شکست خورد → login_failed_count += 1، return None
بعد از ۳ شکست متوالی → recipe را disable موقت (با log)
تابع helper _encrypt_storage(data: Dict, key: bytes) -> str و
معکوس _decrypt_storage(blob: str, key: bytes) -> Dict:

AES-GCM با کلید مشتق از env OVERSIGHT_AUTH_KEY (اگر نبود، یک
کلید تصادفی بساز و در env ست کن — warning log)
این برای اینکه cookie ها در plaintext در DB نمی‌مانند.
Backend — تغییر دیگر
backend/app/services/verify_runtime/inspector_probe.py:

پشتیبانی از ProbeContext.storage_state (فیلد جدید در base.py):

اگر ctx.storage_state پر است:
context = await browser.new_context(
    viewport={"width": 1280, "height": 800},
    storage_state=ctx.storage_state,  # Playwright API
)
این تمام cookies + localStorage را به probe می‌دهد بدون نیاز به
login مجدد.
Backend — تغییر در verifier
backend/app/services/oversight_verifier.py:

در _verify_task، قبل از ساخت ProbeContext:
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی کش رمزنگاری‌شده storage_state و پشتیبانی در probe و verifier

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک شامل سه تغییر اصلی است: (1) ایجاد فایل جدید `backend/app/services/verify_runtime/auth_runner.py` با تابع async `obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict[str, Any]]` که storage_state را با AES-GCM رمزنگاری کرده و در حافظه کش می‌کند. کلید رمزنگاری از env `OVERSIGHT_AUTH_KEY` مشتق می‌شود (اگر نبود، یک کلید تصادفی ساخته و در env ست می‌شود). اگر `runtime_auth_recipe` تنظیم نشده → return None. اگر `runtime_storage_state` معتبر و `expires_at > now` و `force=False` → decrypt و return. در غیر این صورت: launch Chromium → execute recipe.steps → اگر success_indicator OK → دریافت storage_state از context → encrypt → ذخیره در watched → return decoded. اگر login شکست خورد → `login_failed_count += 1`، return None. بعد از ۳ شکست متوالی → recipe را موقت disable (با log). توابع helper `_encrypt_storage(data: Dict, key: bytes) -> str` و `_decrypt_storage(blob: str, key: bytes) -> Dict` با AES-GCM پیاده‌سازی می‌شوند. (2) تغییر در `backend/app/services/verify_runtime/inspector_probe.py` برای پشتیبانی از `ProbeContext.storage_state` (فیلد جدید در base.py): اگر `ctx.storage_state` پر است، در خط 365 `_ctx_kwargs["storage_state"] = ctx.storage_state` اضافه شود تا Playwright از cookies + localStorage ذخیره‌شده استفاده کند بدون نیاز به login مجدد. (3) تغییر در `backend/app/services/oversight_verifier.py` در تابع `_verify_task` برای فراخوانی `obtain_or_refresh_storage_state` قبل از ساخت `ProbeContext` و پاس دادن storage_state به context. خارج از scope: پیاده‌سازی خود recipe steps، مدیریت خطاهای غیر از login، و تست‌های یکپارچه‌سازی. کلیدواژه‌ها: auth_runner.py, obtain_or_refresh_storage_state, _encrypt_storage, _decrypt_storage, AES-GCM, OVERSIGHT_AUTH_KEY, inspector_probe.py, ProbeContext.storage_state, oversight_verifier.py, _verify_task, runtime_storage_state, runtime_auth_recipe.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل جدید `backend/app/services/verify_runtime/auth_runner.py` با محتوای کامل شامل: تابع `_get_or_create_key()` برای دریافت/ساخت کلید AES-GCM از env OVERSIGHT_AUTH_KEY (خطوط 44-67 از deep context)، تابع `_encrypt_storage(data: Dict) -> Optional[str]` با AES-GCM (خطوط 70-87)، تابع `_decrypt_storage(blob: str) -> Optional[Dict]` (خطوط 90-105)، تابع `_resolve_value(step: Dict) -> str` برای resolve value_env با prefix WATCHED_AUTH_* (خطوط 112-129)، تابع async `_execute_login_recipe(recipe, frontend_base_url) -> Dict` (خطوط 132-272)، تابع async `obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict]` (خطوط 279-380)، تابع async `_save_storage_state(watched, state)` (خطوط 383-396)، تابع async `test_login_recipe(watched) -> Dict` (خطوط 399-428)، تابع async `invalidate_storage_state(watched) -> Dict` (خطوط 431-446). 2. تغییر در `backend/app/services/verify_runtime/inspector_probe.py` خط 362-365: اضافه کردن `if isinstance(ctx.storage_state, dict) and ctx.storage_state: _ctx_kwargs["storage_state"] = ctx.storage_state` تا probe از storage_state موجود استفاده کند. 3. تغییر در `backend/app/services/oversight_verifier.py` در تابع `_verify_task`: قبل از ساخت ProbeContext، فراخوانی `from .verify_runtime.auth_runner import obtain_or_refresh_storage_state`

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 22: Phase 3: Auth Recipe, Enhanced Feature Detection, UI Panel, AI Enricher, and Safety Limits

**Scope:** این بخش شامل پیاده‌سازی کامل Phase 3 است: مدیریت auth recipe (ذخیره storage_state، تشخیص redirect به login)، enhanced feature detection (before/after screenshot pairs، vision pair analysis، expected API calls assertion)، UI panel برای تنظیم auth recipe، بهبود AI enricher برای تولید recipe ۳-۸ مرحله‌ای، و محدودیت‌های ایمنی. تمام فایل‌های backend و frontend ذکر شده باید تغییر کنند. رفتارهای graceful degrade برای شکست auth، vision، و enricher تعریف شده است.
**Key terms:** auth_runner.py, base.py, inspector_probe.py, vision_helper.py, runner.py, ac_enricher.py, oversight_service.py, oversight_verifier.py, oversight.py, page.tsx, ProbeContext, WatchedProject, storage_state, runtime_auth_recipe, runtime_storage_state, analyze_screenshot_pair, expected_api_calls, login redirect detection, before/after screenshot pairs, AES-GCM, OVERSIGHT_AUTH_KEY, WATCHED_AUTH_*, _MAX_SCREENSHOTS, per-step timeout, per-probe timeout

**بخش مربوط از متن کاربر:**
```
# 🆕 (Phase 3) — اگر watched recipe دارد، storage_state بگیر/تازه کن
auth_storage_state = None
if watched and getattr(watched, "runtime_auth_recipe", None):
    try:
        from .verify_runtime.auth_runner import obtain_or_refresh_storage_state
        auth_storage_state = await obtain_or_refresh_storage_state(watched)
    except Exception as _ae:
        logger.warning(f"auth runner failed: {_ae}")

_probe_ctx = build_probe_context(
    ...,
    storage_state=auth_storage_state,
)
Login redirect detection
در _run_inspector_inner، بعد از navigate، چک کن:

اگر page.url شامل /login یا /signin بود (و route قبلی این نبود)
یا page.title شامل «Login» یا «ورود» بود
→ علامت‌گذاری probe با auth_required: true در evidence
vision_helper این را می‌گیرد و در feature_present تأثیر می‌دهد

auth_required = False
final_url_lower = (page.url or "").lower()
if any(p in final_url_lower for p in ("/login", "/signin", "/auth")):
    if "/login" not in full_url.lower():  # خود route نبود
        auth_required = True

evidence["auth_required"] = auth_required
if auth_required:
    assertion_results.append({
        "expectation": "صفحه‌ی هدف بدون redirect به login باز شود",
        "met": False,
        "reason": f"redirect به {page.url} — احتمالاً auth recipe لازم است",
    })
══════════════════════════════════════════════════════════════════════

C) Enhanced Feature Detection — جزئیات
══════════════════════════════════════════════════════════════════════

Before/After screenshot pairs
وقتی verify_plan.ui_steps شامل interaction (click/fill/submit) است:

screenshot قبل از اولین interaction (label="before_interaction")
screenshot بعد از آخرین interaction (label="after_interaction")
Vision آنالیز diff: prompt جدید برای vision_helper
# vision_helper.py — تابع جدید
async def analyze_screenshot_pair(
    before_path: str,
    after_path: str,
    context: Dict[str, Any],  # شامل ac_text و actions_taken
) -> Dict[str, Any]:
    """آنالیز یک جفت screenshot قبل/بعد از interaction.

    Returns:
      {
        "before_description": str,
        "after_description": str,
        "diff_description": str,    # «بعد از کلیک X، Y ظاهر شد»
        "interaction_succeeded": "yes" | "no" | "unclear",
        "feature_present": "yes" | "no" | "unclear",
        "source": str,
      }
    """
این تابع از multimodal vision یک prompt دو-عکسی می‌فرستد و می‌پرسد:
«قبل از این تعامل، صفحه X بود. بعد از تعامل، Y شد. آیا تعامل کار
کرد و feature واقعاً عمل کرد؟»

Network call analysis
inspector_probe قبلاً backend_urls_called ذخیره می‌کرد. در Phase 3:

اگر AC انتظار یک API call خاص دارد (مثلاً «POST /api/debates ساخته
شود»)، probe باید بفهمد آیا آن endpoint در network_calls هست:

# در verify_plan
"expected_api_calls": [
    {"method": "POST", "path_contains": "/api/debates"},
    {"method": "GET", "path_contains": "/api/projects/.*/files"},
]
probe بعد از interaction چک می‌کند:

expected = plan.get("expected_api_calls") or []
for exp in expected:
    matched = any(
        c.get("method") == exp["method"]
        and exp["path_contains"] in (c.get("url") or "")
        for c in network_calls
    )
    assertion_results.append({
        "expectation": f"API call {exp['method']} {exp['path_contains']}",
        "met": matched,
        "reason": "ثبت شد" if matched else "ثبت نشد",
    })
Multi-screenshot evidence storage
الان _MAX_SCREENSHOTS = 2. در Phase 3 بالا ببر به 5 (یا 6) تا
interaction های پیچیده کاملاً capture شوند.

══════════════════════════════════════════════════════════════════════

D) UI — تنظیمات auth recipe
══════════════════════════════════════════════════════════════════════

frontend/src/app/oversight/page.tsx — در همان panel «runtime» که
runtime_repo_path و base URLs ست می‌شوند:

یک بخش جدید «🔐 Auth Recipe (اختیاری)»
form فیلدها:
login_url (text input)
email (text input — برای save در env var name)
password (text input — برای save در env var name)
email selector (text input — مثلاً input[name=email])
password selector (text input)
submit selector
success indic
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی Phase 3 Auth Recipe و Enhanced Feature Detection

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/auth_runner.py:1-100` — `obtain_or_refresh_storage_state` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. تابع جدید برای مدیریت storage_state با AES-GCM.
- `backend/app/services/verify_runtime/inspector_probe.py:1-50` — `_run_inspector_inner` — فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. اضافه کردن login redirect detection بعد از navigate.
- `backend/app/services/verify`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی کامل Phase 3 شامل: (1) مدیریت auth recipe با ذخیره storage_state و تشخیص redirect به login در `_run_inspector_inner` بعد از navigate — اگر page.url شامل `/login` یا `/signin` بود (و route قبلی این نبود) یا page.title شامل «Login» یا «ورود» بود → علامت‌گذاری probe با `auth_required: true` در evidence. (2) Enhanced Feature Detection: before/after screenshot pairs برای interaction‌های click/fill/submit در verify_plan.ui_steps، تابع جدید `analyze_screenshot_pair` در `vision_helper.py` برای آنالیز diff دو عکس با multimodal vision، network call analysis برای expected_api_calls مثل `POST /api/debates`، افزایش `_MAX_SCREENSHOTS` از 2 به 5. (3) UI panel در `frontend/src/app/oversight/page.tsx` برای تنظیم auth recipe شامل login_url, email, password, selectors. (4) بهبود AI enricher در `ac_enricher.py` برای تولید recipe ۳-۸ مرحله‌ای. (5) محدودیت‌های ایمنی: per-step timeout و per-probe timeout. رفتارهای graceful degrade برای شکست auth, vision, و enricher تعریف شده است. شواهد در کد: `backend/app/services/oversight_verifier.py` خط 72-119 (`_classify_step_for_probe`)، `backend/app/services/verify_runtime/` شامل `auth_runner.py`, `base.py`, `inspector_probe.py`, `vision_helper.py`, `runner.py`, `ac_enricher.py`, `backend/app/services/oversight_service.py` (WatchedProject با runtime_auth_recipe و runtime_storage_state)، `backend/app/api/routes/oversight.py` (endpoint‌های runtime).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در `backend/app/services/verify_runtime/auth_runner.py`: پیاده‌سازی `obtain_or_refresh_storage_state(watched: WatchedProject)` که با استفاده از AES-GCM و کلید `OVERSIGHT_AUTH_KEY` از env، storage_state را ذخیره/بازیابی کند. 2. در `backend/app/services/verify_runtime/inspector_probe.py`: بعد از navigate در `_run_inspector_inner`، تشخیص redirect به login با چک کردن page.url و page.title. 3. در `backend/app/services/verify_runtime/vision_helper.py`: تابع `analyze_screenshot_pair(before_path, after_path, context)` برای آنالیز diff دو عکس. 4. در `backend/app/services/verify_runtime/runner.py`: افزایش `_MAX_SCREENSHOTS` از 2 به 5 و گرفتن before/after screenshot برای interaction‌ها. 5. در `backend/app/services/verify_runtime/ac_enricher.py`: بهبود تولید recipe ۳-۸ مرحله‌ای با پشتیبانی از expected_api_calls. 6. در `frontend/src/app/oversight/page.tsx`: افزودن بخش «🔐 Auth Recipe (اختیاری)» با فیلدهای login_url, email, password, selectors. 7. در `backend/app/services/oversight_service.py`: افزودن فیلدهای `runtime_auth_recipe` و `runtime_storage_state` به WatchedProject. 8. در `backend/app/api/routes/oversight.py`: endpoint برای ذخیره/بازیابی auth recipe.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 23: Phase 4: Smart Navigation + Backend Log Probe + Code-aware Verifier

**Scope:** این بخش شامل اجرای کامل Phase 4 از سری verify جدید است که پس از Phase 1, 2, 3 و سه فیکس آخر اجرا می‌شود. محتوای دقیق و جزئیات اجرایی Phase 4 در این بخش ارائه نشده و صرفاً به عنوان یک هدر و مرور وضعیت فعلی ذکر شده است. هیچ دستورالعمل اجرایی، لیست کارها یا تغییرات مشخصی در این بخش وجود ندارد.
**Key terms:** Phase 4, Smart Navigation, Backend Log Probe, Code-aware Verifier, inspector_probe, navigate, screenshot, vision, session, telegram, cleanup, recovery, per-step probes, prompt versioning, mega-bundle PDF, action loop, fill/click/wait/assert, auth recipe, vision_pair, expected_api_calls, force backfill, Telegram trigger, SPA-404 detection, system probe relaxation, conservative routing

**بخش مربوط از متن کاربر:**
```
# 🎯 پرامپت کامل Phase 4 — Smart Navigation + Backend Log Probe + Code-aware Verifier
⚠️ این پرامپت Phase 4 از سری «verify جدید» است که پس از Phase 1، 2،
و 3 (شامل سه فیکس آخر) اجرا می‌شود.
══════════════════════════════════════════════════════════════════════
# مرور خیلی سریع وضعیت فعلی
══════════════════════════════════════════════════════════════════════
✅ **Phase 1**: inspector_probe پایه با navigate + screenshot + vision +
   session + telegram + cleanup + recovery.
✅ **Phase 2**: per-step probes + prompt versioning + mega-bundle PDF.
✅ **Phase 3**: action loop (fill/click/wait/assert) + auth recipe +
   vision_pair + expected_api_calls + force backfill + Telegram trigger.
✅ **سه فیکس آخر**: SPA-404 detection + system probe relaxation +
   conservative routing (skip when no specific route).
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای Phase 4: Smart Navigation + Backend Log Probe + Code-aware Verifier

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/code_aware_verifier.py:48-114` — `analy`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به اجرای کامل Phase 4 از سری verify جدید است که پس از Phase 1, 2, 3 و سه فیکس آخر اجرا می‌شود. بر اساس متن کاربر، Phase 4 شامل سه مؤلفه اصلی است: Smart Navigation, Backend Log Probe, Code-aware Verifier. وضعیت فعلی: ✅ Phase 1 (inspector_probe پایه با navigate + screenshot + vision + session + telegram + cleanup + recovery), ✅ Phase 2 (per-step probes + prompt versioning + mega-bundle PDF), ✅ Phase 3 (action loop: fill/click/wait/assert + auth recipe + vision_pair + expected_api_calls + force backfill + Telegram trigger), ✅ سه فیکس آخر (SPA-404 detection + system probe relaxation + conservative routing). کلیدواژه‌های استخراج‌شده: Phase 4, Smart Navigation, Backend Log Probe, Code-aware Verifier, inspector_probe, navigate, screenshot, vision, session, telegram, cleanup, recovery, per-step probes, prompt versioning, mega-bundle PDF, action loop, fill/click/wait/assert, auth recipe, vision_pair, expected_api_calls, force backfill, Telegram trigger, SPA-404 detection, system probe relaxation, conservative routing. شواهد در کد واقعی: فایل `backend/app/services/verify_runtime/code_aware_verifier.py` (خطوط 1-500) شامل تابع `analyze_acs_with_commit_diffs` و `_process_single_batch` و `_phase_a_basename_match` و `_phase_b_content_grep` است که مستقیماً با Code-aware Verifier مرتبط است. فایل `backend/app/services/oversight_verifier.py` (خطوط 1-800) شامل `_classify_step_for_probe`, `_evaluate_acs_against_files`, `_extract_relevant_chunks` است که برای Smart Navigation و Backend Log Probe نیاز به توسعه دارد. فایل `backend/app/services/verify_runtime/inspector_probe.py` (deep-read شده) برای Smart Navigation و Backend Log Probe باید گسترش یابد. فایل `backend/app/services/verify_runtime/navigation_helper.py` (deep-read شده) برای Smart Navigation باید بهبود یابد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. Smart Navigation: در فایل `backend/app/services/verify_runtime/navigation_helper.py` یک تابع جدید `smart_navigate` اضافه کن که با استفاده از context پروژه (repo_tree, target_files, task_steps) بهترین route را برای ناوبری انتخاب کند. از `_classify_step_for_probe` در `oversight_verifier.py` (خط 72) برای تعیین scope استفاده کن. 2. Backend Log Probe: در فایل `backend/app/services/verify_runtime/inspector_probe.py` یک تابع جدید `backend_log_probe` اضافه کن که لاگ‌های backend (از `backend_log_probe.py` یا `backend/app/services/verify_runtime/backend_log_probe.py`) را برای یافتن شواهد اجرای AC جستجو کند. از `_extract_relevant_chunks` در `oversight_verifier.py` (خط 349) برای استخراج chunk‌های مرتبط استفاده کن. 3. Code-aware Verifier: در فایل `backend/app/services/verify_runtime/code_aware_verifier.py` تابع `analyze_acs_with_commit_diffs` (خط 48) را برای پشتیبانی از Smart Navigation و Backend Log Probe گسترش بده. از `_phase_a_basename_match` (خط 501) و `_phase_b_content_grep` (خط 560) برای matching بهتر استفاده کن. 4. یکپارچه‌سازی: در `backend/app/services/verify_runtime/iterative_orchestrator.py` (deep-read شده) یک مرحله جدید Phase 4 اضافه کن که این سه مؤلفه را به‌ترتیب اجرا کند. 5. تست: تست‌های جدید در `backend/tests/test_runtime_verify_stage3e.py` یا فایل تست جدید اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 24: رفع مشکلات باقیمانده Phase 3 در Phase 4: route guessing ضعیف، backend-heavy benefit صفر، استفاده ناکامل از Render logs و inspector chat

**Scope:** این بخش چهار مشکل مشخص از تست واقعی Phase 3 را فهرست می‌کند که Phase 4 باید حل کند: (1) route guessing ضعیف برای تسک‌های دارای URL خاص، (2) تسک‌های backend-heavy که از probe UI سود نمی‌برند و verify بدون شواهد می‌ماند، (3) استفاده ناکامل از Render logs (فقط error/warn فیلتر می‌شود)، (4) استفاده ناکامل از inspector chat infrastructure برای auto-verify. این بخش صرفاً مشکلات را توصیف می‌کند و راه‌حل ارائه نمی‌دهد. خارج از scope: پیاده‌سازی راه‌حل‌ها، کدنویسی، یا تغییر فایل‌ها.
**Key terms:** route guessing, trading-system, /routing-diagram, /charts, keyword-based, DebateAttachment, backend-heavy, probe UI, Render logs, RENDER_API_KEY, inspector chat infrastructure, auto-verify, backend/app/services/oversight_verifier.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verify_pdf.py, frontend/src/app/oversight/page.tsx, tests/integration/test_runtime_verify.py, backend/app/services/oversight_inspector_bridge.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext

**بخش مربوط از متن کاربر:**
```
# مشکلات باقیمانده که Phase 4 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 3 + سه فیکس مشخص شد:
1. **route guessing ضعیف**: برای تسک trading-system که صفحات URL خاصی
   داشتند (مثل /routing-diagram, /charts)، probe نمی‌تواند URL واقعی
   را پیدا کند. حدس‌های keyword-based 404 می‌گیرند. کاربر گفت در
   تجربه قبلی هم با این مشکل اذیت شده بود.
2. **تسک‌های backend-heavy benefit صفر می‌گیرند**: تسک‌هایی مثل
   DebateAttachment (backend models, endpoints, service logic) از
   probe UI سود نمی‌برند چون feature تو UI دیده نمی‌شود. probe ها
   skipped می‌شوند ولی verify بدون شواهد runtime می‌ماند.
3. **استفاده ناکامل از Render logs**: الان فقط لاگ‌های window زمانی
   probe فیلتر می‌شوند (level=error/warn). با اینکه RENDER_API_KEY ست
   شده، از لاگ‌های مرتبط به فایل‌های target تسک یا call های endpoint
   مرتبط استفاده نمی‌کنیم.
4. **استفاده ناکامل از inspector chat infrastructure**: بازرس ویژه
   دستی از قبل لاگ‌های backend + console همراه هر پیام چت ذخیره
   می‌کند، ولی auto-verify از این infrastructure استفاده نمی‌کند.
══════════════════════════════════════════════════════════════════════
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع مشکلات Phase 3 در Phase 4: route guessing، backend-heavy، Render logs، inspector chat

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک به رفع چهار مشکل باقیمانده از تست واقعی Phase 3 در Phase 4 می‌پردازد که در متن کاربر به تفصیل آمده است:

(1) **route guessing ضعیف**: برای تسک trading-system که صفحات URL خاصی داشتند (مثل /routing-diagram, /charts)، probe نمی‌تواند URL واقعی را پیدا کند. حدس‌های keyword-based 404 می‌گیرند. کاربر گفت در تجربه قبلی هم با این مشکل اذیت شده بود. در کد فعلی، تابع `_extract_url_hint` در `backend/app/services/verify_runtime/inspector_probe.py` (خط 90-101) فقط اولین navigate را از `ui_steps` استخراج می‌کند و اگر نباشد از `url_hint` یا `path` از `verify_plan` استفاده می‌کند. این روش برای تسک‌هایی که URL خاصی دارند (مثل /routing-diagram) کافی نیست.

(2) **تسک‌های backend-heavy benefit صفر می‌گیرند**: تسک‌هایی مثل DebateAttachment (backend models, endpoints, service logic) از probe UI سود نمی‌برند چون feature تو UI دیده نمی‌شود. probe ها skipped می‌شوند ولی verify بدون شواهد runtime می‌ماند. در `inspector_probe.py` خط 259-264، اگر `is_ui_probe_enabled()` false باشد یا circuit breaker باز باشد، probe با `PROBE_STATUS_SKIPPED` برمی‌گردد. برای تسک‌های backend-heavy، هیچ probe جایگزینی (مثل api_probe یا backend_log_probe) فعال نمی‌شود.

(3) **استفاده ناکامل از Render logs**: الان فقط لاگ‌های window زمانی probe فیلتر می‌شوند (level=error/warn). با اینکه RENDER_API_KEY ست شده، از لاگ‌های مرتبط به فایل‌های target تسک یا call های endpoint مرتبط استفاده نمی‌کنیم. در `_fetch_backend_logs_window` (خط 135-184) فقط لاگ‌های error/warn در یک بازه زمانی 5 ثانیه‌ای قبل و بعد از probe گرفته می‌شوند. هیچ فیلتری بر اساس service_id، file_path، یا endpoint مرتبط با تسک وجود ندارد.

(4) **استفاده ناکامل از inspector chat infrastructure**: بازرس ویژه دستی از قبل لاگ‌های backend + console همراه هر پیام چت ذخیره می‌کند، ولی auto-verify از این infrastructure استفاده نمی‌کند. در `inspector_probe.py`، پیام‌ها از طریق `_msg` به `InspectorMessage` ذخیره می‌شوند (خط 230-236)، اما auto-verify از `InspectorSession` موجود برای context غنی (شامل تاریخچه چت، لاگ‌های قبلی، و تحلیل‌های vision) استفاده نمی‌کند.

کلیدواژه‌های ذکر شده: route guessing, trading-system, /routing-diagram, /charts, keyword-based, DebateAttachment, backend-heavy, probe UI, Render logs, RENDER_API_KEY, inspector chat infrastructure, auto-verify, backend/app/services/oversight_verifier.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verify_pdf.py, frontend/src/app/oversight/page.tsx, tests/integration/test_runtime_verify.py, backend/app/services/oversight_inspector_bridge.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. برای رفع چهار مشکل فوق، اقدامات زیر پیشنهاد می‌شود:

1. **بهبود route guessing**: در `backend/app/services/verify_runtime/inspector_probe.py`، تابع `_extract_url_hint` (خط 90-101) را اصلاح کن تا از `project_structure` یا `code_aware_verifier` برای یافتن URL واقعی بر اساس نام تسک و

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 25: پیاده‌سازی سه ستون Phase 4: Smart Navigation Probe، Backend Log Probe و Code-aware Verifier

**Scope:** این بخش شامل پیاده‌سازی سه قابلیت مجزا در Oversight Service است: (A) Smart Navigation Probe که به جای حدس URL، از home page شروع کرده و nav menu را برای یافتن لینک مرتبط با feature تحلیل می‌کند، (B) Backend Log Probe که برای تسک‌های backend-heavy لاگ‌های Render را بر اساس target_files و AC keywords فیلتر و تحلیل می‌کند، (C) Code-aware Verifier که برای هر Acceptance Criteria به صورت جداگانه با GitHub API چک می‌کند که آیا diff اخیر آن AC را پیاده کرده است. این سه قابلیت به صورت موازی و مستقل از هم کار می‌کنند و خروجی هر کدام به صورت جداگانه در نتیجه نهایی گزارش می‌شود.
— [merged] این بخش شامل سه زیرسیستم جدید برای بهبود دقت verify در Phase 4 است: (A) Smart Navigation Probe برای زمانی که route inference نتوانست مسیر را پیدا کند، (B) Backend Log Probe برای تحلیل لاگ‌های Render برای تسک‌های backend، و (C) Code-aware Verifier برای تحلیل per-AC commits. همچنین شامل Task Type Routing است که نوع تسک را تشخیص داده و probe مناسب را dispatch می‌کند. این بخش فقط پیاده‌سازی این سه سیستم را پوشش می‌دهد و شامل تغییرات در runner.py، oversight_verifier.py و فایل‌های جدید navigation_helper.py، backend_log_probe.py و code_aware_verifier.py است.
**Key terms:** _classify_task_type, backend_log_probe.py, backend/app/services/verify_runtime/inspector_probe.py, analyze_commits_per_ac, backend/app/services/oversight_verifier.py, InspectorSession, Per-AC commit analysis, backend/app/services/verify_runtime/runner.py, analyze_backend_logs_for_ac, VerifyContext, Anthropic Computer Use, Smart Navigation Probe, ProbeResult, AC keywords, runner.py, oversight_verifier.py, backend/app/services/oversight_service.py, GitHub API, Playwright, Code-aware Verifier, code_aware_verifier.py, VerifyConfig, navigation_helper.py, inspector_probe.py, OpenAI Operator

**بخش مربوط از متن کاربر:**
```
# هدف کلی Phase 4 — سه ستون
══════════════════════════════════════════════════════════════════════
**A) Smart Navigation Probe (Agentic Browsing)**
به‌جای حدس زدن URL از روی keyword، probe به home می‌رود، nav menu
را می‌خواند، و AI تصمیم می‌گیرد کدام لینک به feature مرتبط است.
این الگوی استاندارد OpenAI Operator / Anthropic Computer Use است.
**B) Backend Log Probe**
برای تسک‌های backend-heavy (که AC شون از UI element حرف نمی‌زند)،
به‌جای probe UI، یک probe جدید لاگ‌های Render فیلتر شده بر اساس
target_files تسک + AC keywords را تحلیل می‌کند. خروجی: «آیا این
feature backend deploy شده و call می‌شود؟»
**C) Code-aware Verifier (Per-AC commit analysis)**
gh API الان فقط در سطح کل تسک استفاده می‌شود. در Phase 4، برای هر
AC جداگانه چک می‌شود که آیا diff اخیر آن AC را پیاده کرده یا نه.
این بدون نیاز به repo کلون محلی، با همان GitHub API که داریم.
══════════════════════════════════════════════════════════════════════
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی سه ستون Phase 4: Smart Navigation، Backend Log Probe و Code-aware Verifier

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک پیاده‌سازی سه قابلیت مجزا در Oversight Service است که در درخواست کاربر با اولویت critical و نوع refactor مشخص شده است. (A) Smart Navigation Probe: به‌جای حدس URL از روی keyword، probe به home page رفته و nav menu را با Playwright می‌خواند و AI (با استفاده از ai_manager و verify_model_id) تصمیم می‌گیرد کدام لینک به feature مرتبط است. این الگوی استاندارد OpenAI Operator / Anthropic Computer Use است. فایل اصلی: backend/app/services/verify_runtime/navigation_helper.py که شامل توابع extract_nav_links_from_page (خط 28)، pick_nav_link_for_ac (خط 76) و try_smart_navigation_for_step (خط 204) است. (B) Backend Log Probe: برای تسک‌های backend-heavy که AC شان از UI element حرف نمی‌زند، به‌جای probe UI، یک probe جدید لاگ‌های Render فیلتر شده بر اساس target_files تسک + AC keywords را تحلیل می‌کند. خروجی: «آیا این feature backend deploy شده و call می‌شود؟». فایل جدید backend/app/services/verify_runtime/backend_log_probe.py باید ایجاد شود. (C) Code-aware Verifier (Per-AC commit analysis): GitHub API الان فقط در سطح کل تسک استفاده می‌شود. در Phase 4، برای هر AC جداگانه چک می‌شود که آیا diff اخیر آن AC را پیاده کرده یا نه. این بدون نیاز به repo کلون محلی، با همان GitHub API که داریم. فایل اصلی: backend/app/services/verify_runtime/code_aware_verifier.py که شامل analyze_acs_with_commit_diffs (خط 48) و _fetch_recent_commits_with_diff (خط 260) است. همچنین شامل Task Type Routing است که نوع تسک را تشخیص داده و probe مناسب را dispatch می‌کند. این بخش فقط پیاده‌سازی این سه سیستم را پوشش می‌دهد و شامل تغییرات در runner.py، oversight_verifier.py و فایل‌های جدید navigation_helper.py، backend_log_probe.py و code_aware_verifier.py است. کلیدواژه‌های کاربر: _classify_task_type, backend_log_probe.py, backend/app/services/verify_runtime/inspector_probe.py, analyze_commits_per_ac, backend/app/services/oversight_verifier.py, InspectorSession, Per-AC commit analysis, backend/app/services/verify_runtime/runner.py, analyze_backend_logs_for_ac, VerifyContext, Anthropic Computer Use, Smart Navigation Probe, ProbeResult, AC keywords, runner.py, oversight_verifier.py, backend/app/services/oversight_service.py, GitHub API, Playwright, Code-aware Verifier, code_aware_verifier.py, VerifyConfig, navigation_helper.py, inspector_probe.py, OpenAI Operator.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/verify_runtime/runner.py، تابع _classify_task_type را پیاده‌سازی کن تا نوع تسک (frontend-heavy, backend-heavy, mixed) را بر اساس target_files و AC keywords تشخیص دهد. 2. فایل جدید backend/app/services/verify_runtime/backend_log_probe.py ایجاد کن با تابع analyze_backend_logs_for_ac که از RenderLog DB (مدل backend/app/models/render_log.py) برای فیلتر لاگ‌های backend بر اساس target_files و AC keywords استفاده می‌کند. 3. در فایل backend/app/services/verify_runtime/code_aware_verifier.py، تابع analyze_commits_per_ac را اضافه کن که برای هر AC به صورت جداگانه با GitHub API (از oversight_service.GITHUB_API) چک کند آیا diff اخیر آن AC را پیاده کرده است. 4. در فایل backend/app/services/oversight_verifier.py، منطق dispatch را به‌روز کن تا بر اساس _classify_task_type، probe مناسب (Smart Navigation، Backend Log، Code-aware) را فراخوانی کند. 5. در فایل backend/app/services/verify_runtime/navigation_helper.py، تابع try_smart_navigation_for_step (خط 204) را به‌عنوان Smart Navigation Probe اصلی استفاده کن. 6. اطمینان حاصل کن که هر سه probe به صورت موازی و مستقل از هم کار می‌کنند و

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 26: اجرای پروب‌های runtime برای backend ACها با Smart Navigation

**Scope:** این مرحله شامل اجرای پروب‌های UI (با Smart Navigation) و پروب‌های backend log برای acceptance criteriaهای backend است. اگر task_type 'backend' یا 'mixed' باشد، برای هر AC که backend است، یک پروب لاگ اجرا می‌شود. اگر task_type 'unknown' باشد، هیچ پروبی اجرا نمی‌شود. این مرحله بخشی از فاز 3 است و نتایج به runtime_probe_results اضافه می‌شوند.
**Key terms:** run_ui_probes, run_backend_log_probe, runtime_probe_results, acceptance_criteria, _is_backend_ac, task_type, backend, mixed, unknown, Smart Navigation

**بخش مربوط از متن کاربر:**
```
# Phase 3 system probe + per-step probes (با Smart Navigation اضافه)
    runtime_probe_results.extend(await run_ui_probes(...))

if task_type in ('backend', 'mixed'):
    # Backend Log Probe برای backend AC ها
    for ac in acceptance_criteria:
        if _is_backend_ac(ac):
            res = await run_backend_log_probe(ac, ctx, ac_id, task)
            runtime_probe_results.append(res)

if task_type == 'unknown':
```

## 🎯 هدف (خلاصه ساختاریافته)
اجرای پروب‌های runtime برای backend ACها با Smart Navigation

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/navigation_helper.py:204-368` — `try_smart_navigation_for_step` — این تابع Smart Navigation را پیاده‌سازی می‌کند — باید در run_ui_probes برای ACهای backend/mixed فراخوانی شود.
  ```python
  async def try_smart_navigation_for_step(
      ac_text: str,
      base_url: str,
      storage_state: Optional[Dict[str, Any]] = None,
      verify_model_id: Optional[str] = None,
  ) -> Dict[str, Any]:
      """تابع high-level — برای orchestration: یک browser session سبک باز
      می‌کند، nav menu را می‌خواند، AI لینک مرتبط را انتخاب می‌کند."""
  ```
- `backend/app/services/verify_runtime/backend_log_probe.py:1-50` — `run_backend_log_probe` — این فایل deep-read شده — مجری باید مسیر را خود تأیید
  ```python
  فایل deep-read شده است اما snippet دقیق موجود نیست — تابع run_backend_log_probe باید برای backend ACها لاگ‌های سرور را بررسی کند.
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به اجرای پروب‌های runtime برای acceptance criteriaهای backend در فاز 3 است. کاربر درخواست کرده که برای هر AC با task_type 'backend' یا 'mixed'، یک پروب لاگ (run_backend_log_probe) اجرا شود. همچنین برای ACهای 'backend' یا 'mixed' که نیاز به UI interaction دارند، پروب‌های UI با Smart Navigation (run_ui_probes) نیز اجرا می‌شوند. اگر task_type 'unknown' باشد، هیچ پروبی اجرا نمی‌شود. کلیدواژه‌های اصلی: run_ui_probes, run_backend_log_probe, runtime_probe_results, acceptance_criteria, _is_backend_ac, task_type, backend, mixed, unknown, Smart Navigation. در کد فعلی، فایل backend/app/services/verify_runtime/navigation_helper.py (خطوط 204-368) تابع try_smart_navigation_for_step را پیاده‌سازی کرده که از AI برای انتخاب لینک nav مرتبط با AC استفاده می‌کند. همچنین فایل backend/app/services/verify_runtime/backend_log_probe.py (که در deep context موجود است) باید برای اجرای پروب لاگ backend ACها استفاده شود. فایل backend/app/api/routes/runtime.py (خطوط 261-335) endpoint run_project را دارد که می‌تواند برای اجرای پروژه و دریافت لاگ‌ها استفاده شود. این تغییرات باید در orchestrator یا runner مربوطه اعمال شوند تا منطق شرطی task_type پیاده‌سازی شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/verify_runtime/iterative_orchestrator.py (یا runner.py)، یک تابع جدید به نام _run_backend_ac_probes اضافه کن که: a) task_type را بررسی کند — اگر 'backend' یا 'mixed' باشد، برای هر AC که _is_backend_ac(ac) True برگرداند، run_backend_log_probe را صدا بزند. b) اگر task_type 'unknown' باشد، هیچ پروبی اجرا نکند. c) نتایج را به runtime_probe_results اضافه کند. 2. در همان فایل، منطق run_ui_probes را با Smart Navigation (try_smart_navigation_for_step از navigation_helper.py خط 204) ترکیب کن تا برای ACهای backend/mixed که نیاز به UI دارند، Smart Navigation فعال شود. 3. تابع _is_backend_ac را در یک فایل مشترک (مثلاً backend/app/services/verify_runtime/ac_schema.py یا context_builder.py) تعریف کن تا تشخیص دهد آیا AC مربوط به backend است (بر اساس کلمات کلیدی مانند 'API', 'endpoint', 'backend', 'server', 'database'). 4. runtime_probe_results را به عنوان یک لیست در scope اصلی نگه دار و بعد از اجرای همه پروب‌ها، آن را به خروجی نهایی اضافه کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 27: پیاده‌سازی سه پروب جدید (Smart Navigation، Backend Log، Code-aware) در Oversight Runtime

**Scope:** این بخش شامل پیاده‌سازی کامل سه نوع پروب جدید در runtime verification است: Smart Navigation (navigation_helper.py)، Backend Log Probe (backend_log_probe.py)، و Code-aware Verifier (code_aware_verifier.py). همچنین شامل تغییرات در oversight_verifier.py برای routing task type، تغییرات در inspector_probe.py برای hook Smart Navigation، به‌روزرسانی oversight_mega_bundle.py برای سه سکشن جدید، و تغییرات UI در frontend برای نمایش سه آیکن جدید (🧭 📊 🔍) است. محدودیت‌های سراسری شامل AI cost cap (۲ call per probe)، time cap (۹۰ ثانیه per task)، graceful fallback در صورت failure، و عدم نشت credentials است. ترتیب پیاده‌سازی در ۸ commit جداگانه مشخص شده است. بخش‌های موجود (Phase 1, 2, 3 + سه فیکس) نباید شکسته شوند.
**Key terms:** verify_runtime/navigation_helper.py, verify_runtime/backend_log_probe.py, verify_runtime/code_aware_verifier.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/runner.py, oversight_verifier.py, oversight_mega_bundle.py, frontend/src/app/oversight/page.tsx, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult, _classify_task_type, _verify_task, smart-nav probe, backend-log probe, code-aware probe

**بخش مربوط از متن کاربر:**
```
══════════════════════════════════════════════════════════════════════

Telegram Integration
══════════════════════════════════════════════════════════════════════

mega-bundle.md سکشن‌های جدید:

۸.۱ Smart Navigation Decisions
چه nav linksای پیدا شد؟ AI چی انتخاب کرد؟
confidence + reason per task
۸.۲ Backend Log Analysis (per backend AC)
verdict (deployed_working / not_deployed / ...)
evidence_lines
reason
۸.۳ Code-aware Verdict (per AC)
code_verdict
matching_commits
key_changes excerpts
reason
══════════════════════════════════════════════════════════════════════

UI Changes — Minimal
══════════════════════════════════════════════════════════════════════

inline probe row حالا سه نوع probe جدید را نمایش می‌دهد:

🧭 smart-nav probe (با link انتخاب‌شده)
📊 backend-log probe (با verdict color)
🔍 code-aware probe (با matching commits)
هر کدام آیکن متفاوت و رنگ متمایز.

══════════════════════════════════════════════════════════════════════

Done Definition (سخت‌گیر)
══════════════════════════════════════════════════════════════════════

Smart Navigation کار می‌کند: روی یک تسک با AC که /path ندارد،
probe به home می‌رود، nav menu را می‌خواند، AI لینک مرتبط را
انتخاب می‌کند، روی آن کلیک می‌کند، و ادامه probe می‌دهد.
Backend Log Probe کار می‌کند: روی یک تسک backend (مثل
DebateAttachment)، به‌جای probe UI، probe جدیدی لاگ‌های Render
فیلتر شده را تحلیل می‌کند و verdict می‌دهد.
Code-aware Verifier کار می‌کند: برای هر AC، یک code_probe در
runtime_probe_results ظاهر می‌شود با verdict (implemented /
not_found / ...).
task type classification درست است: تسک trading-system →
"mixed" یا "backend"، تسک "ساخت صفحه login" → "ui".
هیچ بخش موجود از کار نیفتد: Phase 1, 2, 3 + سه فیکس + همه‌ی
تغییرات اخیر.
mega-bundle شامل سکشن‌های جدید: بخش ۸.۱ smart nav، ۸.۲
backend log، ۸.۳ code-aware.
UI inline سه آیکن جدید نمایش می‌دهد.
type-check + python ast پاس.
══════════════════════════════════════════════════════════════════════

محدودیت‌های سراسری
══════════════════════════════════════════════════════════════════════

per-probe AI cost cap: ۲ AI call (یکی link picker، یکی verdict)
per-task additional time: حداکثر ۹۰ ثانیه (روی Phase 3 ۶۰ثانیه)
AI provider failure → graceful fallback به Phase 3 behavior
لاگ‌های Render اگر در DB نبود (سرویس log_stream_service غیرفعال) →
Backend Log Probe SKIPPED با reason صریح
GitHub API rate limit → Code-aware Verifier ممکن است partial باشد
هرگز credentials در لاگ یا inspector_session نشت نکند
══════════════════════════════════════════════════════════════════════

فایل‌های نهایی
══════════════════════════════════════════════════════════════════════

Backend جدید
verify_runtime/navigation_helper.py (Smart Navigation A)
verify_runtime/backend_log_probe.py (Backend Log Probe B)
verify_runtime/code_aware_verifier.py (Code-aware Verifier C)
Backend تغییر
verify_runtime/inspector_probe.py (Smart Navigation hook)
verify_runtime/runner.py (task type routing)
oversight_verifier.py (orchestration + _classify_task_type +
hooks for backend/code probes)
oversight_mega_bundle.py (سه سکشن جدید در bundle)
Frontend
oversight/page.tsx (سه آیکن جدید: 🧭 📊 🔍)
══════════════════════════════════════════════════════════════════════

شکست‌خوردگی‌های مجاز (graceful degrade)
══════════════════════════════════════════════════════════════════════

AI link picker fail → fallback به skip (Phase 3 behavior)
nav menu خالی → skip smart navigation
Render logs خالی → backend log probe skipped
GitHub API timeout → code-aware verifier skipped per AC
task type "unknown" → fallback به همه (UI + Backend + Code)
AI cost overrun → فقط همان probe skipped، بقیه ادامه
══════════════════════════════════════════════════════════════════════

ترتیب پیاده‌سازی (commits جداگانه)
══════════════════════════════════════════════════════════════════════

Commit 1: _classify_task_type در oversight_verifier.py
Commit 2: code_aware_verifier.py (per-AC commit analysis)
Commit 3: backend_log_probe.py (با endpoint extraction)
Commit 4: navigation_helper.py + integration in inspector_prob
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی سه پروب جدید Smart Navigation، Backend Log و Code-aware در Oversight Runtime

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی کامل سه نوع پروب جدید در runtime verification را دارد: Smart Navigation (فایل جدید verify_runtime/navigation_helper.py)، Backend Log Probe (فایل جدید verify_runtime/backend_log_probe.py)، و Code-aware Verifier (فایل جدید verify_runtime/code_aware_verifier.py). همچنین شامل تغییرات در oversight_verifier.py برای routing task type (اضافه کردن تابع _classify_task_type)، تغییرات در inspector_probe.py برای hook Smart Navigation، به‌روزرسانی oversight_mega_bundle.py برای سه سکشن جدید (۸.۱ Smart Navigation Decisions، ۸.۲ Backend Log Analysis، ۸.۳ Code-aware Verdict)، و تغییرات UI در frontend (فایل frontend/src/app/oversight/page.tsx) برای نمایش سه آیکن جدید (🧭 📊 🔍) است. محدودیت‌های سراسری شامل AI cost cap (۲ call per probe)، time cap (۹۰ ثانیه per task)، graceful fallback در صورت failure، و عدم نشت credentials است. ترتیب پیاده‌سازی در ۸ commit جداگانه مشخص شده است: Commit 1: _classify_task_type در oversight_verifier.py، Commit 2: code_aware_verifier.py، Commit 3: backend_log_probe.py، Commit 4: navigation_helper.py + integration در inspector_probe.py. بخش‌های موجود (Phase 1, 2, 3 + سه فیکس) نباید شکسته شوند. فایل‌های نهایی backend جدید: verify_runtime/navigation_helper.py، verify_runtime/backend_log_probe.py، verify_runtime/code_aware_verifier.py. فایل‌های backend تغییر: verify_runtime/inspector_probe.py (Smart Navigation hook)، verify_runtime/runner.py (task type routing)، oversight_verifier.py (orchestration + _classify_task_type + hooks for backend/code probes)، oversight_mega_bundle.py (سه سکشن جدید در bundle). Frontend: oversight/page.tsx (سه آیکن جدید: 🧭 📊 🔍). شکست‌خوردگی‌های مجاز: AI link picker fail → fallback به skip (Phase 3 behavior)، nav menu خالی → skip smart navigation، Render logs خالی → backend log probe skipped، GitHub API timeout → code-aware verifier skipped per AC، task type 'unknown' → fallback به همه (UI + Backend + Code)، AI cost overrun → فقط همان probe skipped، بقیه ادامه.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_verifier.py، تابع _classify_task_type را اضافه کن که بر اساس task.type و task.raw_idea، نوع تسک را به 'ui'، 'backend'، 'mixed' یا 'unknown' طبقه‌بندی کند. 2. فایل جدید backend/app/services/verify_runtime/code_aware_verifier.py را ایجاد کن که برای هر AC، با استفاده از GitHub API یا تحلیل فایل‌های محلی، verdict (implemented/not_found/partial) به همراه matching_commits و key_changes_excerpts برگرداند. 3. فایل جدید backend/app/services/verify_runtime/backend_log_probe.py را ایجاد کن که برای تسک‌های backend، لاگ‌های RenderLog را فیلتر کرده و verdict (deployed_working/deployed_with_errors/not_deployed) به همراه evidence_lines و reason برگرداند. 4. فایل جدید backend/app/services/verify_runtime/navigation_helper.py را ایجاد کن که Smart Navigation را پیاده‌سازی کند: به home page برود، nav menu را بخواند، AI لینک مرتبط را انتخاب کند، روی آن کلیک کند و ادامه probe دهد. 5. در فایل backend/app/services/verify_runtime/inspector_probe.py، hook Smart Navigation را اضافه کن تا در صورت نبود path در AC، navigation_helper فراخوانی شود. 6. در فایل backend/app/services/verify_runtime/runner.py، task type routing را اضافه کن تا بر اساس _classify_task_type، probe مناسب اجرا شود. 7. در فایل backend/app/services/oversight_mega_bundle.py، سه سکشن جدید ۸.۱ (Smart Navigation Decisions)، ۸.۲ (Backend Log Analysis) و ۸.۳ (Code-aware Verdict) را اضافه کن. 8

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 28: Phase 5: Logic Audit — بررسی هدف، منطق و coherence در auto-scan و task creation

**Scope:** این فاز به پیاده‌سازی Logic Audit می‌پردازد که شامل بررسی هدف (purpose)، منطق (logic) و coherence (انسجام) در فرآیند auto-scan و task creation است. این فاز مستقیماً بندهای R10 و R11 درخواست خام را پوشش می‌دهد. R11 یک مثال از باگ منطقی در هماهنگی (trade) ارائه می‌دهد که باید در Logic Audit شناسایی شود. این فاز شامل پیاده‌سازی یک سرویس یا تابع جدید برای Logic Audit نیست، بلکه منطق موجود در oversight_verifier.py و oversight_strong_prompt.py را برای شناسایی ناسازگاری‌ها و خطاهای منطقی ارتقا می‌دهد. خروجی این فاز باید قابلیت شناسایی خودکار مواردی مانند 'trade با قیمت خرید بالاتر از فروش' یا 'تسک‌های متناقض' باشد.
**Key terms:** Logic Audit, oversight_verifier.py, oversight_strong_prompt.py, coherence, R10, R11, trade, auto-scan, task creation

**بخش مربوط از متن کاربر:**
```
| **R10** | Logic Audit (هدف، منطق، coherence) | فاز ۵ |
| **R11** | مثال trade — باگ منطقی در هماهنگی | فاز ۵ |

این فاز به پیاده‌سازی Logic Audit می‌پردازد که شامل بررسی هدف (purpose)، منطق (logic) و coherence (انسجام) در فرآیند auto-scan و task creation است. R11 یک مثال از باگ منطقی در هماهنگی (trade) ارائه می‌دهد که باید در Logic Audit شناسایی شود.
```

## 🎯 هدف (خلاصه ساختاریافته)
Logic Audit: ارتقای coherence در oversight_verifier و strong_prompt

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_verifier.py:232-319` — `_evaluate_acs_against_files` — این تابع ACها را جداگانه ارزیابی می‌کند اما coherence بین آن‌ها را بررسی نمی‌کند. باید بعد از ارزیابی تکی، یک پاس coherence اضافه شود.
  ```python
  def _evaluate_acs_against_files(
      acceptance_criteria: List[Any],
      file_contents: Dict[str, Optional[str]],
      repo_tree: List[str],
  ) -> List[Dict[str, Any]]:
      """شواهد ماشینی per-AC: برای هر AC، تعداد hit کلمات کلیدی در هر فایل.
      این یک baseline deterministic به AI verifier می‌دهد — AI نمی‌تواند ادعا
      کند فایل وجود ندارد یا قابلیت پیاده نشده، اگر hit‌ها واقعی هستند."""
  ```
- `backend/app/services/oversight_strong_prompt.py:158-420` — `build_strong_prompt` — این تابع پرامپت را می‌سازد اما validation منطقی روی ACها انجام نمی‌دهد. باید بعد از بخش AC، coherence check اضافه شود.
  ```python
  def build_strong_prompt(
      *,
      title: str,
      user_goal: str = "",
      raw_user_request: str = "",
      description: str = "",
      proposed_action: str = "",
      context_snippet: str = "",
      target_files: Optional[List[str]] = None,
      target_locations: Optional[List[Union[Dict[str, Any], str]]] = None,
      related_files: Optional[List[Union[Dict[str, Any], str]]] = None,
      dependency_summary: str = "",
      tech_context: str = "",
      before_after_examples: Optional[List[Dict[str, str]]] = None,
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
  ```
- `backend/app/services/oversight_verifier.py`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز ۵: Logic Audit — بررسی هدف، منطق و coherence در auto-scan و task creation. این فاز مستقیماً بندهای R10 و R11 درخواست خام را پوشش می‌دهد. R11 یک مثال از باگ منطقی در هماهنگی (trade) ارائه می‌دهد: 'trade با قیمت خرید بالاتر از فروش' یا 'تسک‌های متناقض'. این فاز شامل پیاده‌سازی یک سرویس یا تابع جدید برای Logic Audit نیست، بلکه منطق موجود در `backend/app/services/oversight_verifier.py` و `backend/app/services/oversight_strong_prompt.py` را برای شناسایی ناسازگاری‌ها و خطاهای منطقی ارتقا می‌دهد. خروجی این فاز باید قابلیت شناسایی خودکار مواردی مانند 'trade با قیمت خرید بالاتر از فروش' یا 'تسک‌های متناقض' باشد. کلیدواژه‌ها: Logic Audit, oversight_verifier.py, oversight_strong_prompt.py, coherence, R10, R11, trade, auto-scan, task creation.

شواهد در کد: در `oversight_verifier.py` تابع `_evaluate_acs_against_files` (خط 232) و `_build_keywords_from_acs` (خط 438) وجود دارند که ACها را با کلمات کلیدی ارزیابی می‌کنند اما هیچ منطق coherence یا تشخیص تناقض ندارند. در `oversight_strong_prompt.py` تابع `build_strong_prompt` (خط 158) پرامپت را می‌سازد اما validation منطقی روی ACها انجام نمی‌دهد. تابع `_classify_step_for_probe` (خط 72 در verifier) ۱۰ قاعده برای طبقه‌بندی دارد اما coherence بین steps را بررسی نمی‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در `backend/app/services/oversight_verifier.py` یک تابع جدید `_detect_logical_inconsistencies(acceptance_criteria: List[Any]) -> List[Dict[str, Any]]` اضافه کن که:
   - الگوهای رایج تناقض را شناسایی کند (مثلاً 'قیمت خرید > قیمت فروش'، 'enable X و disable X همزمان')
   - از regex و pattern matching روی متن ACها استفاده کند
   - خروجی: لیست تناقض‌ها با {ac1, ac2, reason, severity}
2. در `backend/app/services/oversight_strong_prompt.py` تابع `build_strong_prompt` را اصلاح کن تا:
   - بعد از جمع‌آوری ACها، تابع تشخیص تناقض را صدا بزند
   - اگر تناقضی یافت شد، یک بخش جدید '⚠️ هشدار تناقض منطقی' به پرامپت اضافه کند
   - severity هر تناقض را مشخص کند (low/medium/high)
3. در `backend/app/services/oversight_verifier.py` تابع `_evaluate_acs_against_files` را اصلاح کن تا:
   - coherence بین ACها را به عنوان یک معیار جداگانه ارزیابی کند
   - اگر تناقضی در ACها وجود داشت، در verdict_hint ذکر کند
4. یک تابع `_check_trade_consistency` برای تشخیص باگ‌های مالی مانند 'قیمت خرید بالاتر از فروش' پیاده‌سازی کن
5. تست‌های unit برای تابع جدید در `backend/tests/` اضافه کن

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 29: تعریف فلسفه و معماری ماژول Scan (Phase 5) و تمایز آن از Verify (Phase 4)

**Scope:** این بخش فلسفه کلی ماژول Scan را تعریف می‌کند: scan ≠ verify، scan قوی‌تر از verify است، و چهار پایه اصلی (پوشش ریز تا درشت، تغییر-آگاهی، رفتار-محوری، logic awareness) را مشخص می‌کند. هدف نهایی کشف و ساخت تمام تسک‌های واقعاً لازم (features جدید/ناقص، bugs ساختاری/منطقی، features قدیمی، componentهای ناسازگار، notification های ناقص) است. این بخش شامل پیاده‌سازی کد نیست، بلکه معماری و الزامات سطح بالا را تعریف می‌کند.
**Key terms:** smart_nav, vision, code-aware, backend-log, inspector_probe, comprehensive inventory, purpose extraction, delta analysis, logical coherence, outcome analysis, notification audit, semantic stale detection, R1, R3, R4, R7, R8, R9, R10, R11, R12, R13

**بخش مربوط از متن کاربر:**
```
## 📌 مقدمه و فلسفه
### **R1** — scan ≠ verify
| سیستم | چه می‌کند |
|---|---|
| **verify** (Phase 4، تمام) | روی **تسک‌های موجود** بررسی می‌کند آیا انجام شده یا نه |
| **scan** (این Phase 5) | کل سیستم را بررسی می‌کند تا **تسک‌های واقعاً لازم** کشف و ایجاد شوند |
اگر scan خوب کار نکند → تسک واقعاً لازم اصلاً ساخته نمی‌شود → verify هرگز فرصت بررسی آن را پیدا نمی‌کند. **پس scan حتی از verify مهم‌تر است.**
### **R4** — scan باید قوی‌تر از verify باشد
verify شواهد جمع می‌کند برای **یک task مشخص**. scan شواهد جمع می‌کند برای **کل سیستم**. پس scan ابزارهای بیشتری نیاز دارد:
- همه‌ی Phase 4 components (smart_nav, vision, code-aware, backend-log, inspector_probe)
- **به‌علاوه**: comprehensive inventory، purpose extraction، delta analysis، logical coherence، outcome analysis، notification audit، semantic stale detection
### **چهار پایه**
1. **پوشش ریز تا درشت** (R3)
2. **تغییر-آگاهی + bidirectional dependency** (R7)
3. **رفتار-محوری در پرامپت و چک‌لیست** (R9, R13)
4. **logic awareness از روز اول — purpose، coherence، effectiveness** (R10, R11)
### **هدف نهایی**
بعد از یک scan، **تمام تسک‌های واقعاً لازم** کشف و ساخته شوند، **با چک‌لیست هوشمند، با notification صحیح، با session بازرس کامل**:
- features جدید
- features ناقص
- bugs ساختاری
- bugs منطقی (R11)
- features قدیمی و dead options (R8)
- componentهای منطقاً ناسازگار (R10)
- featuresی که کاربر دیگر نمی‌داند چیست (R8) → با AI explanation
- notification ها ناقص یا اشتباه (R12)
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف معماری و فلسفه ماژول Scan (Phase 5) و تمایز از Verify

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک یک refactor معماری سطح بالا برای تعریف فلسفه و معماری ماژول Scan (Phase 5) و تمایز آن از Verify (Phase 4) است. کاربر خواسته است که این بخش فلسفه کلی ماژول Scan را تعریف کند: scan ≠ verify، scan قوی‌تر از verify است، و چهار پایه اصلی (پوشش ریز تا درشت، تغییر-آگاهی، رفتار-محوری، logic awareness) را مشخص می‌کند. هدف نهایی کشف و ساخت تمام تسک‌های واقعاً لازم (features جدید/ناقص، bugs ساختاری/منطقی، features قدیمی، componentهای ناسازگار، notification های ناقص) است. این بخش شامل پیاده‌سازی کد نیست، بلکه معماری و الزامات سطح بالا را تعریف می‌کند.

بخش مربوط از درخواست اصلی کاربر:
- **R1 — scan ≠ verify**: verify (Phase 4، تمام) روی تسک‌های موجود بررسی می‌کند آیا انجام شده یا نه. scan (این Phase 5) کل سیستم را بررسی می‌کند تا تسک‌های واقعاً لازم کشف و ایجاد شوند. اگر scan خوب کار نکند → تسک واقعاً لازم اصلاً ساخته نمی‌شود → verify هرگز فرصت بررسی آن را پیدا نمی‌کند. پس scan حتی از verify مهم‌تر است.
- **R4 — scan باید قوی‌تر از verify باشد**: verify شواهد جمع می‌کند برای یک task مشخص. scan شواهد جمع می‌کند برای کل سیستم. پس scan ابزارهای بیشتری نیاز دارد: همه‌ی Phase 4 components (smart_nav, vision, code-aware, backend-log, inspector_probe) به‌علاوه: comprehensive inventory، purpose extraction، delta analysis، logical coherence، outcome analysis، notification audit، semantic stale detection.
- **چهار پایه**: 1. پوشش ریز تا درشت (R3) 2. تغییر-آگاهی + bidirectional dependency (R7) 3. رفتار-محوری در پرامپت و چک‌لیست (R9, R13) 4. logic awareness از روز اول — purpose، coherence، effectiveness (R10, R11).
- **هدف نهایی**: بعد از یک scan، تمام تسک‌های واقعاً لازم کشف و ساخته شوند، با چک‌لیست هوشمند، با notification صحیح، با session بازرس کامل: features جدید، features ناقص، bugs ساختاری، bugs منطقی (R11)، features قدیمی و dead options (R8)، componentهای منطقاً ناسازگار (R10)، featuresی که کاربر دیگر نمی‌داند چیست (R8) → با AI explanation، notification ها ناقص یا اشتباه (R12).

کلیدواژه‌ها: smart_nav, vision, code-aware, backend-log, inspector_probe, comprehensive inventory, purpose extraction, delta analysis, logical coherence, outcome analysis, notification audit, semantic stale detection, R1, R3, R4, R7, R8, R9, R10, R11, R12, R13.

شواهد در کد واقعی پروژه: فایل `backend/app/services/scan_v5/comprehensive_inventory.py` (خطوط 1-22) ماژول Phase 5 — Comprehensive Inventory (R3 — ریز تا درشت) را تعریف می‌کند که ۱۲ لایه ساختاری از یک پروژه را inventory می‌کند. این فایل شامل لایه‌های Files, Backend endpoints, UI elements, DB schema, Env vars, Config files, Dependencies, Scripts, Cron/scheduled, Routes, Notification calls (R12), UI options/settings (R8) است. فایل `backend/app/services/scan_v5/coherence_analyzer.py` برای logical coherence (R10) موجود است. فایل `backend/app/services/notification_service.py` برای notification audit (R12) مرتبط است.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک یک refactor معماری است و نیاز به تغییر کد مستقیم ندارد، بلکه نیاز به مستندسازی و تعریف ساختار ماژول Scan دارد. مراحل پیشنهادی:

1. **ایجاد فایل معماری جدید**: یک فایل `docs/PHASE_5_ARCHITECT

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 30: فاز ۱ — Comprehensive Inventory + Purpose Extraction

**Scope:** این بخش شامل دو ماژول جدید است: comprehensive_inventory.py برای جمع‌آوری ۱۲ لایه از inventory (فایل‌ها، endpoints، UI elements، DB schema، env vars، configs، dependencies، scripts، cron/scheduled، routes، notification calls، UI options/settings) و purpose_extractor.py برای استخراج purpose هر آیتم inventory. همچنین شامل اضافه کردن سه فیلد جدید به WatchedProject برای ذخیره نتایج اسکن است. Acceptance Criteria شامل حداقل ۵۰ backend endpoint، ۳۰ UI element، ۱۰ notification call، پوشش کامل UI options، purpose_map برای ≥۸۰% فایل‌های مهم، و creation_context برای هر UI option است.
**Key terms:** backend/app/services/scan_v5/comprehensive_inventory.py, backend/app/services/scan_v5/purpose_extractor.py, WatchedProject, last_scan_inventory, last_scan_purpose_map, last_scan_at_v5, run_deep_scan, notify_event, send_telegram, bot.send_message, apscheduler, BackgroundTasks, asyncio.create_task

**بخش مربوط از متن کاربر:**
```
## 🅰️ فاز ۱ — Comprehensive Inventory + Purpose Extraction
> پوشش **R3** (ریز تا درشت)، پایه برای همه فازهای بعدی
### مسئله
الان `run_deep_scan` فقط ۳۵ فایل deep-read + import graph می‌بیند. backend endpoints، UI elements، DB schema، env vars، configs، **notifications، inspector sessions، UI options** هرگز inventory نمی‌شوند.
### تغییرات
**۱-A. Structural Inventory (۱۲ لایه):**
ماژول جدید: `backend/app/services/scan_v5/comprehensive_inventory.py`
| # | لایه | چه چیزی جمع می‌شود | روش |
|---|---|---|---|
| 1 | Files | همه فایل‌های git-tracked | `git ls-files` |
| 2 | Backend endpoints | همه `@router.{get,post,…}` + WebSocket + background tasks | AST parse |
| 3 | UI elements | همه `<button>`, `<form>`, `<input>`, `<Select>`, `<Link>`, modal triggers, dropdown items | parse `.tsx` |
| 4 | DB schema | همه dataclass + Column + migrations | inspect |
| 5 | Env vars | همه `os.environ.get`, `os.getenv`, `process.env.X` | regex |
| 6 | Config files | همه `.json`, `.yaml`, `.toml`, `.env*` | glob |
| 7 | Dependencies | `requirements.txt`, `package.json` | parse |
| 8 | Scripts | همه `.sh`, `pyproject::scripts`, `package.json::scripts` | parse |
| 9 | Cron/scheduled | همه `apscheduler`, `BackgroundTasks`, `asyncio.create_task` | regex |
| 10 | Routes | همه frontend `app/**/page.tsx` + backend route | walk |
| 11 | **Notification calls (R12)** | همه `notify_event(...)`, `send_telegram(...)`, `bot.send_message(...)` + event_type + silent flag + caption template | regex/AST |
| 12 | **UI options/settings (R8)** | همه checkbox/slider/dropdown در UI + field name در WatchedProject + default value | parse + cross-ref |
**۱-B. Purpose Extraction (R10):**
ماژول جدید: `backend/app/services/scan_v5/purpose_extractor.py`
برای **هر file/module/feature/option** که در inventory هست:

```python
purpose_inventory[item_id] = {
    "stated_purpose": "چه کاری *قرار است* بکند",
    "evidence_sources": ["comments", "docstrings", "tests", "raw_idea", "task_history", "commit_messages"],
    "expected_inputs": [...],
    "expected_outputs": [...],
    "interacting_with": [...],          # سایر componentهای همکار
    "creation_context": {                # R8 — کاربر فراموش کرده چی هست
        "first_seen_commit": "...",
        "first_seen_date": "...",
        "originating_task_id": "...",    # کدام task این را ساخت
        "originating_raw_idea": "...",   # متن خام درخواست
    },
    "current_usage": "...",              # آیا هنوز استفاده می‌شود؟ کجا؟
}
```

**منابع AI برای purpose:**
- محتوای فایل + docstrings + JSDoc
- test files مرتبط
- `WatchedProject.user_notes` (raw_idea اصلی پروژه)
- task history (task هایی که این item را modify کرده‌اند)
- commit messages روی این path
**۱-C. Storage:**
`WatchedProject` فیلدهای جدید:

```python
last_scan_inventory: Optional[Dict[str, Any]] = None
last_scan_purpose_map: Optional[Dict[str, Dict]] = None
last_scan_at_v5: Optional[str] = None  # timestamp scan جدید
```

### Acceptance Criteria فاز ۱
- `inventory.backend_endpoints` ≥ ۵۰
- `inventory.ui_elements` ≥ ۳۰
- `inventory.notification_calls` ≥ ۱۰
- `inventory.ui_options` همه‌ی checkbox/slider/dropdown ها را شامل شود
- `purpose_map` برای ≥ ۸۰% فایل‌های مهم
- برای هر UI option، `creation_context` نشان دهد از کدام task ساخته شد
```

python
purpose_inventory[item_id] = {
    "stated_purpose": "چه کاری *قرار است* بکند",
    "evidence_sources": ["comments", "docstrings", "tests", "raw_idea", "task_history", "commit_messages"],
    "expected_inputs": [...],
    "expected_outputs": [...],
    "interacting_with": [...],          # سایر componentهای همکار
    "creation_context": {                # R8 — کاربر فراموش کرده چی هست
        "first_seen_commit": "...",
        "first_seen_date": "...",
        "originating_task_id": "...",    # کدام task این را ساخت
        "originating_raw_idea": "...",   # متن خام درخواست
    },
    "current_usage": "...",              # آیا هنوز استفاده می‌شود؟ کجا؟
}
```

**منابع AI برای purpose:**
- محتوای فایل + docstrings + JSDoc
- test files مرتبط
- `WatchedProject.user_notes` (raw_idea اصلی پروژه)
- task history (task هایی که این item را modify کرده‌اند)
- commit messages روی این path
**۱-C. Storage:**
`WatchedProject` فیلدهای جدید:

```python
last_scan_inventory: Optional[Dict[str, Any]] = None
last_scan_purpose_map: Optional[Dict[str, Dict]] = None
last_scan_at_v5: Optional[str] = None  # timestamp scan جدید
```

### Acceptance Criteria فاز ۱
- `inventory.backend_endpoints` ≥ ۵۰
- `inventory.ui_elements` ≥ ۳۰
- `inventory.notification_calls` ≥ ۱۰
- `inventory.ui_options` همه‌ی checkbox/slider/dropdown ها را شامل شود
- `purpose_map` برای ≥ ۸۰% فایل‌های مهم
- برای هر UI option، `creation_context` نشان دهد از کدام task ساخته شد

--- کلیدواژه‌ها ---
backend/app/services/scan_v5/comprehensive_inventory.py, backend/app/services/scan_v5/purpose_extractor.py, WatchedProject, last_scan_inventory, last_scan_purpose_map, last_scan_at_v5, run_deep_scan, notify_event, send_telegram, bot.send_message, apscheduler, BackgroundTasks, asyncio.create_task
```

## 🎯 هدف (خلاصه ساختاریافته)
فاز ۱ — Comprehensive Inventory + Purpose Extraction در scan_v5

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/scan_v5/comprehensive_inventory.py:410-447` — `_extract`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی فاز ۱ از یک پروژه اسکن ساختاریافته را دارد که شامل دو ماژول جدید است: comprehensive_inventory.py برای جمع‌آوری ۱۲ لایه از inventory (فایل‌ها، backend endpoints، UI elements، DB schema، env vars، configs، dependencies، scripts، cron/scheduled، routes، notification calls، UI options/settings) و purpose_extractor.py برای استخراج purpose هر آیتم inventory. همچنین شامل اضافه کردن سه فیلد جدید به WatchedProject برای ذخیره نتایج اسکن است. Acceptance Criteria شامل حداقل ۵۰ backend endpoint، ۳۰ UI element، ۱۰ notification call، پوشش کامل UI options، purpose_map برای ≥۸۰% فایل‌های مهم، و creation_context برای هر UI option است. متن کاربر شامل کلیدواژه‌های: backend/app/services/scan_v5/comprehensive_inventory.py, backend/app/services/scan_v5/purpose_extractor.py, WatchedProject, last_scan_inventory, last_scan_purpose_map, last_scan_at_v5, run_deep_scan, notify_event, send_telegram, bot.send_message, apscheduler, BackgroundTasks, asyncio.create_task. در کد واقعی پروژه، فایل comprehensive_inventory.py در backend/app/services/scan_v5/comprehensive_inventory.py موجود است و شامل ۱۲ لایه inventory است که در خطوط ۱-۶۱۴ تعریف شده‌اند. فایل purpose_extractor.py در backend/app/services/scan_v5/purpose_extractor.py موجود است. مدل WatchedProject در backend/app/models/project.py تعریف شده است. endpoint run_deep_scan در backend/app/api/routes/oversight.py قرار دارد. توابع notify_event, send_telegram, bot.send_message در backend/app/services/notification_service.py و backend/app/services/oversight_telegram_compose.py استفاده می‌شوند. کتابخانه‌های apscheduler, BackgroundTasks, asyncio.create_task در backend/app/services/background_scheduler.py و backend/app/services/scan_v5/comprehensive_inventory.py (خط ۳۵۸-۳۸۴) استفاده می‌شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. بررسی ماژول comprehensive_inventory.py در backend/app/services/scan_v5/comprehensive_inventory.py: این ماژول در حال حاضر ۱۲ لایه inventory را پیاده‌سازی کرده است (خطوط ۱-۶۱۴). باید اطمینان حاصل شود که لایه‌های ۱۱ (Notification calls) و ۱۲ (UI options/settings) به‌درستی کار می‌کنند. لایه ۱۱ در خطوط ۴۱۰-۴۴۷ با regex _NOTIFY_RE پیاده‌سازی شده است. لایه ۱۲ در خطوط ۴۵۰-۵۵۱ با regexهای _UI_CHECKBOX_RE, _UI_SLIDER_RE, _UI_DROPDOWN_RE پیاده‌سازی شده است. ۲. ایجاد ماژول purpose_extractor.py در backend/app/services/scan_v5/purpose_extractor.py: این ماژول باید برای هر آیتم inventory یک purpose_map با فیلدهای stated_purpose, evidence_sources, expected_inputs, expected_outputs, interacting_with, creation_context, current_usage ایجاد کند. منابع AI برای purpose شامل محتوای فایل + docstrings + JSDoc, test files مرتبط, WatchedProject.user_notes, task history, commit messages است. ۳. اضافه کردن سه فیلد جدید به WatchedProject در backend/app/models/project.py: last_scan_inventory: Optional[Dict[str, Any]] = None, last_scan_purpose_map: Optional[Dict[str, Dict]] = None, last_scan_at_v5: Optional[str] = None. ۴. به‌روزرسانی endpoint run_deep_scan در backend/app/api/routes/oversight.py برای فراخوانی comprehensive_inventory و purpose_extractor و ذخیره نتایج در WatchedProject. ۵. اطمینان از پوشش کامل UI options با cross-reference به WatchedProject fields. ۶. پیاده‌سازی creation_context برای هر UI option با استفاده از task history و commit messages.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 31: فاز ۲ — Stale Detection + Feature Inventory Panel

**Scope:** این بخش شامل پیاده‌سازی کامل تشخیص اجزای قدیمی (Stale) در دو دسته Structural (۸ نوع) و Semantic (۵ نوع)، تولید مستندات AI برای هر گزینه UI، ایجاد پنل Feature Inventory در صفحه oversight، و تولید Task برای هر آیتم قدیمی است. فایل‌های جدید: backend/app/services/scan_v5/stale_detector.py. فایل‌های موجود: frontend/src/app/oversight/page.tsx. خروجی این فاز شامل حداقل ۵ structural stale، ۳ semantic stale، ۸ hidden-purpose option، و پنل با حداقل ۲۰ مدخل است.
**Key terms:** backend/app/services/scan_v5/stale_detector.py, frontend/src/app/oversight/page.tsx, ai_documentation, inventory.ui_options, inventory.ui_elements, Structural Stale, Semantic Stale, Dead UI buttons, Dead frontend routes, Dead backend endpoints, Unused functions/classes, Unused dataclass fields, Unused env vars, Orphan files, Stale dependencies, Purpose-mismatched, Hidden purpose, Inconsistent با تغییرات اخیر, Outdated business assumption, Forgotten by user, Feature Inventory Panel, cleanup task, audit task, document task

**بخش مربوط از متن کاربر:**
```
## 🅱️ فاز ۲ — Stale Detection + Feature Inventory Panel
> **مهم‌ترین فاز برای R8 — حل مشکل «گزینه‌های قدیمی که نمی‌دانم چی هست»**
### مسئله (R8 — تأکید سه‌باره)
> «خیلی‌هاش قدیمیه و کار نمی‌کنه و خیلی‌هاش نیاز داره بدونم چی بوده، برای چیه و هر سری باید بهش سر بزنم»
### تغییرات
**۲-A. Structural Stale (۸ نوع):**
ماژول جدید: `backend/app/services/scan_v5/stale_detector.py`
| نوع | شناسایی |
|---|---|
| Dead UI buttons | onClick handler ندارد / empty / به endpoint 404 می‌رود |
| Dead frontend routes | در nav menu نیست و در هیچ Link/router.push نیست |
| Dead backend endpoints | در هیچ frontend fetch نیست + در Render logs ۳۰ روز اخیر صدا نشد |
| Unused functions/classes | reverse import = 0 و entry point نیست |
| Unused dataclass fields | در هیچ‌جا read/write نمی‌شود |
| Unused env vars | تعریف شده ولی هیچ `os.environ.get` |
| Orphan files | reverse import = 0 |
| Stale dependencies | در requirements/package.json هست ولی import نمی‌شود |
**۲-B. Semantic Stale (R10 — ۵ نوع):**
| نوع | شناسایی |
|---|---|
| Purpose-mismatched | `stated_purpose` با `actual_behavior` نمی‌خواند |
| Hidden purpose (R8) | کاربر نمی‌داند چی هست — هیچ doc، نام مبهم، creation_context قدیمی |
| Inconsistent با تغییرات اخیر | کد فرض می‌کند رفتار قدیمی X، ولی X تغییر کرده (نیاز به فاز ۳) |
| Outdated business assumption | threshold/config که با realities فعلی نمی‌خواند |
| Forgotten by user (R8 — جدید) | UI option/setting که کاربر هر بار باید بپرسد چی هست |
**۲-C. AI-Generated Documentation برای هر option (R8):**
برای **هر** UI option/setting/feature/button که در inventory.ui_options یا inventory.ui_elements هست:

```python
ai_documentation[option_id] = {
    "name": "...",
    "what_it_does": "AI explanation — این گزینه دقیقاً چه کاری می‌کند",
    "when_added": "تاریخ + commit",
    "originating_idea": "متن خام درخواست اولیه",
    "current_status": "active | possibly_stale | broken | unknown",
    "dependencies": ["..."],         # forward
    "dependents": ["..."],           # reverse
    "recommended_action": "keep | remove | refactor | document"
}
```

**۲-D. Feature Inventory Panel در UI:**
`frontend/src/app/oversight/page.tsx` — اضافه شدن panel جدید:

```
🗺 Feature Inventory
├─ 🔧 Settings (12)
│   ├─ ✓ verify_mode (active — Phase 4, از task #abc1234)
│   ├─ ✓ dedup_threshold (active — Phase 3)
│   ├─ ⚠️ confirmation_streak_required (possibly_stale — ۹۰ روز unused)
│   └─ ...
├─ 🎛 UI Buttons (45)
├─ 🌐 Backend Endpoints (78)
└─ ⚙️ Env Vars (23)
```

برای هر مدخل: hover → AI explanation کامل.
**۲-E. Task Generation:**
برای هر stale item:
- **cleanup** task (structural) یا **audit** task (semantic) یا **document** task (hidden purpose)
- AC رفتار-محور: «یا حذف شود، یا با docstring/comment توضیح داده شود چرا نگه داشته، یا ارتقا یابد»
- priority بر اساس impact
### Acceptance Criteria فاز ۲
- روی این پروژه ≥ ۵ structural stale + ≥ ۳ semantic stale + ≥ ۸ hidden-purpose options
- Feature Inventory Panel با ≥ ۲۰ مدخل
- هر stale → task با explanation کامل (نه فقط «این unused است»)
- روی project trade مثال کاربر (R11)، scan تشخیص دهد گزینه‌هایی که برای trading فعلاً ضرر می‌دهند
```

python
ai_documentation[option_id] = {
    "name": "...",
    "what_it_does": "AI explanation — این گزینه دقیقاً چه کاری می‌کند",
    "when_added": "تاریخ + commit",
    "originating_idea": "متن خام درخواست اولیه",
    "current_status": "active | possibly_stale | broken | unknown",
    "dependencies": ["..."],         # forward
    "dependents": ["..."],           # reverse
    "recommended_action": "keep | remove | refactor | document"
}
```

**۲-D. Feature Inventory Panel در UI:**
`frontend/src/app/oversight/page.tsx` — اضافه شدن panel جدید:

```
🗺 Feature Inventory
├─ 🔧 Settings (12)
│   ├─ ✓ verify_mode (active — Phase 4, از task #abc1234)
│   ├─ ✓ dedup_threshold (active — Phase 3)
│   ├─ ⚠️ confirmation_streak_required (possibly_stale — ۹۰ روز unused)
│   └─ ...
├─ 🎛 UI Buttons (45)
├─ 🌐 Backend Endpoints (78)
└─ ⚙️ Env Vars (23)
```

برای هر مدخل: hover → AI explanation کامل.
**۲-E. Task Generation:**
برای هر stale item:
- **cleanup** task (structural) یا **audit** task (semantic) یا **document** task (hidden purpose)
- AC رفتار-محور: «یا حذف شود، یا با docstring/comment توضیح داده شود چرا نگه داشته، یا ارتقا یابد»
- priority بر اساس impact
### Acceptance Criteria فاز ۲
- روی این پروژه ≥ ۵ structural stale + ≥ ۳ semantic stale + ≥ ۸ hidden-purpose options
- Feature Inventory Panel با ≥ ۲۰ مدخل
- هر stale → task با explanation کامل (نه فقط «این unused است»)
- روی project trade مثال کاربر (R11)، scan تشخیص دهد گزینه‌هایی که برای trading فعلاً ضرر می‌دهند

--- کلیدواژه‌ها ---
backend/app/services/scan_v5/stale_detector.py, frontend/src/app/oversight/page.tsx, ai_documentation, inventory.ui_options, inventory.ui_elements, Structural Stale, Semantic Stale, Dead UI buttons, Dead frontend routes, Dead backend endpoints, Unused functions/classes, Unused dataclass fields, Unused env vars, Orphan files, Stale dependencies, Purpose-mismatched, Hidden purpose, Inconsistent با تغییرات اخیر, Outdated business assumption, Forgotten by user, Feature Inventory Panel, cleanup task, audit task, document task
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی کامل Stale Detection و Feature Inventory Panel

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز ۲ — پیاده‌سازی کامل تشخیص اجزای قدیمی (Stale) در دو دسته Structural (۸ نوع) و Semantic (۵ نوع)، تولید مستندات AI برای هر گزینه UI، ایجاد پنل Feature Inventory در صفحه oversight، و تولید Task برای هر آیتم قدیمی. فایل‌های جدید: backend/app/services/scan_v5/stale_detector.py. فایل‌های موجود: frontend/src/app/oversight/page.tsx. خروجی این فاز شامل حداقل ۵ structural stale، ۳ semantic stale، ۸ hidden-purpose option، و پنل با حداقل ۲۰ مدخل است.

بخش‌های اصلی:
۲-A. Structural Stale (۸ نوع): Dead UI buttons (onClick handler ندارد/empty/به endpoint 404 می‌رود)، Dead frontend routes (در nav menu نیست و در هیچ Link/router.push نیست)، Dead backend endpoints (در هیچ frontend fetch نیست + در Render logs ۳۰ روز اخیر صدا نشد)، Unused functions/classes (reverse import = 0 و entry point نیست)، Unused dataclass fields (در هیچ‌جا read/write نمی‌شود)، Unused env vars (تعریف شده ولی هیچ os.environ.get)، Orphan files (reverse import = 0)، Stale dependencies (در requirements/package.json هست ولی import نمی‌شود)

۲-B. Semantic Stale (R10 — ۵ نوع): Purpose-mismatched (stated_purpose با actual_behavior نمی‌خواند)، Hidden purpose (R8 — کاربر نمی‌داند چی هست — هیچ doc، نام مبهم، creation_context قدیمی)، Inconsistent با تغییرات اخیر (کد فرض می‌کند رفتار قدیمی X، ولی X تغییر کرده)، Outdated business assumption (threshold/config که با realities فعلی نمی‌خواند)، Forgotten by user (R8 — جدید — UI option/setting که کاربر هر بار باید بپرسد چی هست)

۲-C. AI-Generated Documentation برای هر option (R8): برای هر UI option/setting/feature/button که در inventory.ui_options یا inventory.ui_elements هست، ai_documentation[option_id] = {name, what_it_does, when_added, originating_idea, current_status, dependencies, dependents, recommended_action}

۲-D. Feature Inventory Panel در UI: frontend/src/app/oversight/page.tsx — اضافه شدن panel جدید با ساختار: 🗺 Feature Inventory شامل 🔧 Settings (12)، 🎛 UI Buttons (45)، 🌐 Backend Endpoints (78)، ⚙️ Env Vars (23). برای هر مدخل: hover → AI explanation کامل.

۲-E. Task Generation: برای هر stale item: cleanup task (structural) یا audit task (semantic) یا document task (hidden purpose). AC رفتار-محور: «یا حذف شود، یا با docstring/comment توضیح داده شود چرا نگه داشته، یا ارتقا یابد». priority بر اساس impact.

Acceptance Criteria فاز ۲: روی این پروژه ≥ ۵ structural stale + ≥ ۳ semantic stale + ≥ ۸ hidden-purpose options. Feature Inventory Panel با ≥ ۲۰ مدخل. هر stale → task با explanation کامل (نه فقط «این unused است»). روی project trade مثال کاربر (R11)، scan تشخیص دهد گزینه‌هایی که برای trading فعلاً ضرر می‌دهند.

کلیدواژه‌ها: backend/app/services/scan_v5/stale_detector.py, frontend/src/app/oversight/page.tsx, ai_documentation, inventory.ui_options, inventory.ui_elements, Structural Stale, Semantic Stale, Dead UI buttons, Dead frontend routes, Dead backend endpoints, Unused functions/classes, Unused dataclass fields, Unused env vars, Orphan files, Stale dependencies, Purpose-mismatched, Hidden purpose, Inconsistent با تغییرات اخیر, Outdated business assumption, Forgotten by user, Feature Inventory Panel, cleanup task, audit task, document task

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. تکمیل ماژول backend/app/services/scan_v5/stale_detector.py: تابع _detect_dead_ui_buttons (خط ۳۲-۵۴) کامل است. تابع _detect_dead_frontend_routes (خط ۵۷-۱۱۸) کامل است. تابع _detect_dead_backend_endpoints (خط ۱۲۱-۲۱۹) کامل است. تابع _det

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 32: پیاده‌سازی تشخیص دلتا، وابستگی دوطرفه و تحلیل تاثیر منطقی در اسکن v5

**Scope:** این مرحله شامل پیاده‌سازی کامل فاز ۳ است: ذخیره state قبلی در WatchedProject، تشخیص ۶ نوع تغییر (add/remove/modify/rename/move/signature-change)، تحلیل وابستگی دوطرفه (import-based و logical) در ماژول جدید dependency_analyzer.py، تحلیل تاثیر منطقی با AI روی تغییرات و dependents، و تولید task برای فایل‌های تغییر کرده و dependentهای در معرض خطر. فایل‌های خارج از scope: backend/app/services/oversight_* و frontend/src/app/oversight/page.tsx و tests/integration/test_runtime_verify.py.
**Key terms:** WatchedProject, prev_scan_state, dependency_analyzer.py, backend/app/services/scan_v5/dependency_analyzer.py, add, remove, modify, rename, move, signature-change, dependencies, dependents, logical_dependencies, logical_dependents, purpose_inventory, 🔄 وابسته به تغییر, scan inspector session

**بخش مربوط از متن کاربر:**
```
## 🅲️ فاز ۳ — Delta Detection + Bidirectional Dependency + Logical Impact
> پوشش **R7** — کاربر صریحاً bidirectional خواست
### مسئله (R7)
> «چه وابستگی‌هایی داشته **به چه چیزهایی وابسته بوده** و **چه چیزهایی بهش وابسته بودن**»
این **دو طرفه** است:
- forward: این فایل به چه چیزی وابسته است
- reverse: چه چیزهایی به این فایل وابسته‌اند
### تغییرات
**۳-A. ذخیره prev state:**
`WatchedProject`:
```python
prev_scan_state: Optional[Dict[str, Any]] = None
# {file_path → {sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash}}
```
**۳-B. compute delta — ۶ نوع (R7: «تغییر کرده یا اضافه شده یا کم شده یا ویرایش شده»):**
| نوع | تشخیص |
|---|---|
| `add` | در current، نه در prev |
| `remove` | در prev، نه در current |
| `modify` | sha متفاوت |
| `rename` | sha مشابه، path متفاوت |
| `move` | content مشابه، path متفاوت |
| `signature-change` | نام تابع ثابت، parameters یا return-type تغییر |
**۳-C. Bidirectional Dependency (R7 صریح):**
ماژول جدید: `backend/app/services/scan_v5/dependency_analyzer.py`
برای هر changed file:
```python
{
    "dependencies": [...],   # forward — file → چه چیزی import می‌کند
    "dependents": [...],     # reverse — چه چیزهایی → این file import می‌کنند
    "logical_dependencies": [...],   # forward منطقی — کدام components روی این تکیه دارند
    "logical_dependents": [...],     # reverse منطقی — این از کدام components انتظار دارد
}
```
تمایز بین **import-based** و **logical**:
- import: AST/grep
- logical: AI روی purpose_inventory تشخیص می‌دهد (مثلاً «این تابع threshold X را می‌خواند، اگر X تغییر کرد رفتار تغییر می‌کند»)
**۳-D. Logical Impact Analysis (R10):**
AI روی هر تغییر + dependents تحلیل می‌کند:
- آیا تغییر این فایل، **منطق** dependents را می‌شکند؟
- مثال: تغییر `threshold=0.65` → `threshold=0.8` → چه componentهای dependent behavior متفاوت نشان می‌دهند؟
- مثال: تغییر فرمت output `parse_signal()` → چه callerها به update نیاز دارند؟
- مثال: حذف یک env var → چه قسمت‌هایی crash می‌کنند؟
**۳-E. Task Generation:**
برای هر changed file + dependent در خطر:
- task با badge `🔄 وابسته به تغییر`
- AC رفتار-محور: «بعد از این تغییر، dependents X و Y باید همچنان behavior Z تولید کنند»
- اگر logical impact پیچیده است → priority بالاتر + reference به scan inspector session
### Acceptance Criteria فاز ۳
- بعد از دو scan متوالی، delta با ۶ نوع تشخیص داده شود
- اگر signature تغییر کرد و ۳ caller دارد، ≥ ۱ task برای بررسی caller ها
- logical impact detection: اگر threshold تغییر کرد، AI تحلیل کند نه فقط alert سینتکسی
- bidirectional dependency: هم dependencies (forward) هم dependents (reverse) برای هر changed item
```

python
prev_scan_state: Optional[Dict[str, Any]] = None
# {file_path → {sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash}}
```
**۳-B. compute delta — ۶ نوع (R7: «تغییر کرده یا اضافه شده یا کم شده یا ویرایش شده»):**
| نوع | تشخیص |
|---|---|
| `add` | در current، نه در prev |
| `remove` | در prev، نه در current |
| `modify` | sha متفاوت |
| `rename` | sha مشابه، path متفاوت |
| `move` | content مشابه، path متفاوت |
| `signature-change` | نام تابع ثابت، parameters یا return-type تغییر |
**۳-C. Bidirectional Dependency (R7 صریح):**
ماژول جدید: `backend/app/services/scan_v5/dependency_analyzer.py`
برای هر changed file:
```python
{
    "dependencies": [...],   # forward — file → چه چیزی import می‌کند
    "dependents": [...],     # reverse — چه چیزهایی → این file import می‌کنند
    "logical_dependencies": [...],   # forward منطقی — کدام components روی این تکیه دارند
    "logical_dependents": [...],     # reverse منطقی — این از کدام components انتظار دارد
}
```
تمایز بین **import-based** و **logical**:
- import: AST/grep
- logical: AI روی purpose_inventory تشخیص می‌دهد (مثلاً «این تابع threshold X را می‌خواند، اگر X تغییر کرد رفتار تغییر می‌کند»)
**۳-D. Logical Impact Analysis (R10):**
AI روی هر تغییر + dependents تحلیل می‌کند:
- آیا تغییر این فایل، **منطق** dependents را می‌شکند؟
- مثال: تغییر `threshold=0.65` → `threshold=0.8` → چه componentهای dependent behavior متفاوت نشان می‌دهند؟
- مثال: تغییر فرمت output `parse_signal()` → چه callerها به update نیاز دارند؟
- مثال: حذف یک env var → چه قسمت‌هایی crash می‌کنند؟
**۳-E. Task Generation:**
برای هر changed file + dependent در خطر:
- task با badge `🔄 وابسته به تغییر`
- AC رفتار-محور: «بعد از این تغییر، dependents X و Y باید همچنان behavior Z تولید کنند»
- اگر logical impact پیچیده است → priority بالاتر + reference به scan inspector session
### Acceptance Criteria فاز ۳
- بعد از دو scan متوالی، delta با ۶ نوع تشخیص داده شود
- اگر signature تغییر کرد و ۳ caller دارد، ≥ ۱ task برای بررسی caller ها
- logical impact detection: اگر threshold تغییر کرد، AI تحلیل کند نه فقط alert سینتکسی
- bidirectional dependency: هم dependencies (forward) هم dependents (reverse) برای هر changed item

--- کلیدواژه‌ها ---
WatchedProject, prev_scan_state, dependency_analyzer.py, backend/app/services/scan_v5/dependency_analyzer.py, add, remove, modify, rename, move, signature-change, dependencies, dependents, logical_dependencies, logical_dependents, purpose_inventory, 🔄 وابسته به تغییر, scan inspector session
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی کامل فاز ۳: Delta Detection + Bidirectional Dependency + Logical Impact در scan_v5/dependency_analyzer.py

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/scan_v5/dependency_analyzer.py:50-70` — `build_bidirectional_deps`
  ```python
  def build_bidirectional_deps(
      imports: Dict[str,
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی کامل فاز ۳ را دارد که شامل: (۱) ذخیره state قبلی در WatchedProject با فیلد prev_scan_state از نوع Optional[Dict[str, Any]] شامل sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash برای هر فایل. (۲) تشخیص ۶ نوع تغییر (add, remove, modify, rename, move, signature-change) با منطق مشخص: add=در current نه در prev, remove=در prev نه در current, modify=sha متفاوت, rename=sha مشابه path متفاوت, move=content مشابه path متفاوت, signature-change=نام تابع ثابت اما parameters یا return-type تغییر کرده. (۳) ماژول جدید backend/app/services/scan_v5/dependency_analyzer.py که هم‌اکنون وجود دارد و شامل build_bidirectional_deps (خط ۵۰-۷۰), analyze_change_impact (خط ۷۳-۲۱۰), analyze_upstream_impact (خط ۲۱۷-۳۴۵), analyze_added_files_ripple (خط ۳۹۹-۵۲۶) است. کاربر صریحاً خواسته bidirectional dependency با دو بخش forward (dependencies) و reverse (dependents) و logical_dependencies و logical_dependents با AI روی purpose_inventory. همچنین Logical Impact Analysis (R10) با AI روی هر تغییر + dependents. و Task Generation با badge '🔄 وابسته به تغییر' و AC رفتار-محور. فایل‌های خارج از scope: backend/app/services/oversight_* و frontend/src/app/oversight/page.tsx و tests/integration/test_runtime_verify.py. کلیدواژه‌های کاربر: WatchedProject, prev_scan_state, dependency_analyzer.py, backend/app/services/scan_v5/dependency_analyzer.py, add, remove, modify, rename, move, signature-change, dependencies, dependents, logical_dependencies, logical_dependents, purpose_inventory, 🔄 وابسته به تغییر, scan inspector session. شواهد در کد واقعی: فایل dependency_analyzer.py از خط ۱ تا ۵۲۶ کامل پیاده‌سازی شده اما بخش‌های ذخیره prev state در WatchedProject و compute delta با ۶ نوع و logical_dependencies با AI روی purpose_inventory و task generation با badge هنوز پیاده‌سازی نشده‌اند. فایل‌های مرتبط: backend/app/services/scan_v5/scan_bundle.py (caller اصلی), backend/app/services/oversight_deep_scan_service.py (استفاده از depth-aware limits), backend/app/models/project.py (WatchedProject model).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. در backend/app/models/project.py به مدل WatchedProject فیلد prev_scan_state: Optional[Dict[str, Any]] = None اضافه کن با کلیدهای sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash. ۲. یک ماژول جدید backend/app/services/scan_v5/delta_computer.py ایجاد کن با تابع compute_delta(prev_state, current_state) که ۶ نوع تغییر add/remove/modify/rename/move/signature-change را تشخیص دهد. برای signature-change از AST parsing استفاده کن (نام تابع ثابت، پارامترها/return-type تغییر). ۳. در dependency_analyzer.py تابع جدید analyze_logical_dependencies اضافه کن که با AI روی purpose_inventory (از comprehensive_inventory) logical_dependencies و logical_dependents را تشخیص دهد. ۴. در dependency_analyzer.py تابع generate_impact_tasks اضافه کن که برای هر changed file + dependent در خطر، task با badge '🔄 وابسته به تغییر' و AC رفتار-محور تولید کند. ۵. در scan_bundle.py فراخوانی delta_computer و dependency_analyzer را به صورت زنجیره‌ای اضافه کن. ۶. تست‌های unit برای delta_computer در backend/tests/test_delta_computer.py بنویس.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 33: فاز ۴: Runtime Discovery + Outcome + Inspector Session — پیاده‌سازی کامل Inspector Tab Integration و Session Management

**Scope:** این بخش شامل چهار زیربخش اصلی است: (۱) Runtime Discovery با ماژول جدید runtime_discovery.py که routes زنده، 404ها، endpoints فراخوانی‌شده، UI features و recent commits را کشف می‌کند. (۲) Outcome Data Collection برای انواع پروژه (Trading, AI/Chat, Web service, Scheduling, Notification). (۳) Scan Inspector Session که یک session باز می‌کند، تمام AI calls, Playwright actions, screenshots, probe outputs را ثبت می‌کند و در پایان bundle PDF + Telegram message ارسال می‌کند. (۴) اضافه شدن Tab 'Scan Sessions' در Inspector UI. نکته حیاتی: این فاز صراحتاً می‌گوید 'این مهم‌ترین آپشن از قلم افتاده' و نیازمند ایجاد دو ماژول جدید است. Acceptance Criteria شامل ≥۱۰ پیام در session، ≥۵ screenshot، Telegram + PDF، badge 🔍 Scan در Inspector tab.
**Key terms:** backend/app/services/scan_v5/runtime_discovery.py, backend/app/services/scan_v5/scan_inspector_session.py, navigation_helper::extract_nav_links_from_page, backend_log_probe::_fetch_relevant_logs, vision_helper::analyze_screenshot, code_aware_verifier::_fetch_recent_commits_with_diff, runtime_state, routes_alive[], routes_404[], endpoints_called_recently[], endpoints_never_called[], ui_features_visible[], recent_commits[], create_scan_inspector_session, InspectorSession, frontend/src/app/oversight/page.tsx, 🔍 Scan Session, 🔬 Verify Session

**بخش مربوط از متن کاربر:**
```
## 🅳 فاز ۴ — Runtime Discovery + Outcome + Inspector Session
> پوشش **R14** — Inspector tab integration — این مهم‌ترین آپشن از قلم افتاده
### مسئله (R14 صریح)
کاربر گفت: «در بررسی‌های عمیق از تب بازرس ویژه هم کمک می‌گیره و **اسکرین‌ها** رو می‌گیره و در تلگرام **همراه با گزارش** بفرسته و **چت‌ها** رو در یه session ثبت کنه و **بایگانی** کنه؟»
این **اصلاً در پرامپت‌های قبلی نبود**. فعلاً Inspector فقط در verify (Phase 4) استفاده می‌شد.
### تغییرات
**۴-A. Runtime Discovery (با ایده از Phase 4):**
ماژول جدید: `backend/app/services/scan_v5/runtime_discovery.py`
| منبع | استفاده |
|---|---|
| `navigation_helper::extract_nav_links_from_page` | nav links واقعی frontend |
| Playwright on each route | screenshot + status code → 404 detection |
| `backend_log_probe::_fetch_relevant_logs` 30-day | endpoints واقعاً called شده |
| `vision_helper::analyze_screenshot` | کشف feature های UI |
| `code_aware_verifier::_fetch_recent_commits_with_diff` | recent commits context |
خروجی: `runtime_state` شامل `routes_alive[]`, `routes_404[]`, `endpoints_called_recently[]`, `endpoints_never_called[]`, `ui_features_visible[]`, `recent_commits[]`.
**۴-B. Outcome Data Collection:**
برای هر پروژه، scan تلاش کند outcome data بیابد:
| نوع پروژه | outcome data |
|---|---|
| Trading | trade logs, P&L history |
| AI/Chat | conversation outcomes |
| Web service | error rates, latency from logs |
| Scheduling | task completion rates |
| Notification | delivery + open rates |
روش‌ها: Render logs filtered + DB tables outcome-naming + file artifacts.
**۴-C. Scan Inspector Session (R14 — حیاتی):**
ماژول جدید: `backend/app/services/scan_v5/scan_inspector_session.py`
**هر scan یک inspector session باز می‌کند** (مشابه verify در Phase 4):
```python
session = create_scan_inspector_session(
    watched_id=...,
    scan_id=...,
    project_name=...,
)
```
**در طول scan:**
- همه AI calls (purpose extraction، stale detection، logic audit، etc.) → پیام در session با role="ai", content=request+response
- همه Playwright actions → پیام با role="action", screenshot=path
- همه screenshot ها → ذخیره روی disk + reference در session
- runtime probe outputs → پیام با role="probe"
**در پایان scan:**
- session archived
- screenshots → آرشیو شده در Telegram (مثل bundle Phase 4)
- bundle PDF تولید می‌شود شامل:
  - findings + tasks ایجاد شده
  - delta summary
  - logic audit findings
  - inventory summary
  - تمام screenshots
- Telegram message + PDF attachment
- در UI، scan session در inspector tab با badge `🔍 Scan Session` (متمایز از `🔬 Verify Session`)
**۴-D. اضافه شدن tab "Scan Sessions" در Inspector UI:**
`frontend/src/app/projects/[id]/page.tsx` (یا هر جا که inspector tab هست):
- علاوه بر لیست verify sessions، scan sessions هم نمایش داده شوند
- کاربر بتواند هر scan session را باز کند و تمام مکالمات + screenshots آن را ببیند
- archive option
### Acceptance Criteria فاز ۴
- بعد از هر scan، یک inspector session با ≥ ۱۰ پیام (AI calls + actions + probes) ساخته شود
- ≥ ۵ screenshot ذخیره شود
- Telegram message + bundle PDF با همه‌ی screenshots و findings ارسال شود
- در Inspector tab، session آرشیو شده دیده شود با badge `🔍 Scan`
- اگر runtime discovery فعال است، روی هر route یک screenshot + Vision analysis
```

python
session = create_scan_inspector_session(
    watched_id=...,
    scan_id=...,
    project_name=...,
)
```
**در طول scan:**
- همه AI calls (purpose extraction، stale detection، logic audit، etc.) → پیام در session با role="ai", content=request+response
- همه Playwright actions → پیام با role="action", screenshot=path
- همه screenshot ها → ذخیره روی disk + reference در session
- runtime probe outputs → پیام با role="probe"
**در پایان scan:**
- session archived
- screenshots → آرشیو شده در Telegram (مثل bundle Phase 4)
- bundle PDF تولید می‌شود شامل:
  - findings + tasks ایجاد شده
  - delta summary
  - logic audit findings
  - inventory summary
  - تمام screenshots
- Telegram message + PDF attachment
- در UI، scan session در inspector tab با badge `🔍 Scan Session` (متمایز از `🔬 Verify Session`)
**۴-D. اضافه شدن tab "Scan Sessions" در Inspector UI:**
`frontend/src/app/projects/[id]/page.tsx` (یا هر جا که inspector tab هست):
- علاوه بر لیست verify sessions، scan sessions هم نمایش داده شوند
- کاربر بتواند هر scan session را باز کند و تمام مکالمات + screenshots آن را ببیند
- archive option
### Acceptance Criteria فاز ۴
- بعد از هر scan، یک inspector session با ≥ ۱۰ پیام (AI calls + actions + probes) ساخته شود
- ≥ ۵ screenshot ذخیره شود
- Telegram message + bundle PDF با همه‌ی screenshots و findings ارسال شود
- در Inspector tab، session آرشیو شده دیده شود با badge `🔍 Scan`
- اگر runtime discovery فعال است، روی هر route یک screenshot + Vision analysis

--- کلیدواژه‌ها ---
backend/app/services/scan_v5/runtime_discovery.py, backend/app/services/scan_v5/scan_inspector_session.py, navigation_helper::extract_nav_links_from_page, backend_log_probe::_fetch_relevant_logs, vision_helper::analyze_screenshot, code_aware_verifier::_fetch_recent_commits_with_diff, runtime_state, routes_alive[], routes_404[], endpoints_called_recently[], endpoints_never_called[], ui_features_visible[], recent_commits[], create_scan_inspector_session, InspectorSession, frontend/src/app/oversight/page.tsx, 🔍 Scan Session, 🔬 Verify Session
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی کامل Inspector Tab Integration و Session Management فاز ۴

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/code_aware_verifier.py:260-325` — `_fetch_recent_commits_with_diff`
  ```python
  async def _fetch_recent_commits_with_diff(
      repo_full_name: str, token: str, limit: int =
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز ۴: Runtime Discovery + Outcome + Inspector Session — پیاده‌سازی کامل Inspector Tab Integration و Session Management. این بخش شامل چهار زیربخش اصلی است: (۱) Runtime Discovery با ماژول جدید runtime_discovery.py که routes زنده، 404ها، endpoints فراخوانی‌شده، UI features و recent commits را کشف می‌کند. (۲) Outcome Data Collection برای انواع پروژه (Trading, AI/Chat, Web service, Scheduling, Notification). (۳) Scan Inspector Session که یک session باز می‌کند، تمام AI calls, Playwright actions, screenshots, probe outputs را ثبت می‌کند و در پایان bundle PDF + Telegram message ارسال می‌کند. (۴) اضافه شدن Tab 'Scan Sessions' در Inspector UI. نکته حیاتی: این فاز صراحتاً می‌گوید 'این مهم‌ترین آپشن از قلم افتاده' و نیازمند ایجاد دو ماژول جدید است. Acceptance Criteria شامل ≥۱۰ پیام در session، ≥۵ screenshot، Telegram + PDF، badge 🔍 Scan در Inspector tab.

کلیدواژه‌ها: backend/app/services/scan_v5/runtime_discovery.py, backend/app/services/scan_v5/scan_inspector_session.py, navigation_helper::extract_nav_links_from_page, backend_log_probe::_fetch_relevant_logs, vision_helper::analyze_screenshot, code_aware_verifier::_fetch_recent_commits_with_diff, runtime_state, routes_alive[], routes_404[], endpoints_called_recently[], endpoints_never_called[], ui_features_visible[], recent_commits[], create_scan_inspector_session, InspectorSession, frontend/src/app/oversight/page.tsx, 🔍 Scan Session, 🔬 Verify Session

شواهد در کد: در فایل backend/app/services/verify_runtime/code_aware_verifier.py تابع _fetch_recent_commits_with_diff (خط 260) برای fetch commits استفاده شده. در backend/app/services/verify_runtime/navigation_helper تابع extract_nav_links_from_page برای استخراج لینک‌ها. در backend/app/services/verify_runtime/vision_helper تابع analyze_screenshot برای تحلیل UI. در backend/app/services/verify_runtime/backend_log_probe تابع _fetch_relevant_logs برای لاگ‌ها. ماژول‌های جدید scan_v5/runtime_discovery.py و scan_v5/scan_inspector_session.py باید ایجاد شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد ماژول جدید backend/app/services/scan_v5/runtime_discovery.py با استفاده از navigation_helper::extract_nav_links_from_page برای کشف nav links واقعی frontend، Playwright روی هر route برای screenshot + status code → 404 detection، backend_log_probe::_fetch_relevant_logs برای 30-day endpoints واقعاً called شده، vision_helper::analyze_screenshot برای کشف feature های UI، code_aware_verifier::_fetch_recent_commits_with_diff برای recent commits context. خروجی: runtime_state شامل routes_alive[], routes_404[], endpoints_called_recently[], endpoints_never_called[], ui_features_visible[], recent_commits[].
2. ایجاد ماژول جدید backend/app/services/scan_v5/scan_inspector_session.py با تابع create_scan_inspector_session که یک session باز می‌کند، تمام AI calls, Playwright actions, screenshots, probe outputs را ثبت می‌کند و در پایان bundle PDF + Telegram message ارسال می‌کند.
3. پیاده‌سازی Outcome Data Collection برای انواع پروژه (Trading, AI/Chat, Web service, Scheduling, Notification) با استفاده از Render logs filtered + DB tables outcome-naming + file artifacts.
4. اضافه شدن Tab 'Scan Sessions' در Inspector UI در frontend/src/app/oversight/page.tsx با badge 🔍 Scan Session متمایز از 🔬 Verify Session.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 34: فاز ۵: Logical Audit — تشخیص ناهماهنگی منطقی، ضدالگوها و اثربخشی خروجی

**Scope:** این فاز شامل ۵ زیربخش است: (A) تشخیص انسجام زنجیره‌های پردازش (Pipeline Coherence)، (B) تشخیص ضدالگوهای منطقی (Anti-pattern)، (C) کشف نیازمندی‌های پنهان (Hidden Requirements)، (D) ممیزی اثربخشی مبتنی بر خروجی (Outcome-based Effectiveness)، و (E) تولید تسک‌های `logic_audit` با AC outcome-oriented. خارج از scope: اجرای واقعی تغییرات کد (فقط تحلیل و تولید تسک)، و هرگونه اسکن امنیتی یا عملکردی. نکته حیاتی: این فاز صرفاً تحلیل معنایی و منطقی است و نباید به اجرای خودکار تغییرات منجر شود.
**Key terms:** backend/app/services/scan_v5/coherence_analyzer.py, backend/app/services/scan_v5/anti_pattern_detector.py, purpose_inventory, interacting_with, logic_audit, R10, R11, R12, R8, creation_context, stated_purpose, outcome data

**بخش مربوط از متن کاربر:**
```
## 🅴 فاز ۵ — Logical Audit (Coherence + Anti-pattern + Outcome)
> پوشش **R10, R11** — مهم‌ترین فاز معنایی
### مسئله (R10, R11)
> «یه پروژه دارم که هوشمند ترید کنه ولی بدتر از یه آدم معمولی ترید می‌کنه — باگ منطقی در هماهنگی بین AI و داده‌ها»
scan نباید **فقط خطاها** را ببیند، بلکه **منطق و هدف** را هم.
### تغییرات
**۵-A. Pipeline Coherence Detection:**
ماژول جدید: `backend/app/services/scan_v5/coherence_analyzer.py`
شناسایی pipelines (chains از componentهای همکار) با استفاده از `purpose_inventory[X].interacting_with`.
برای هر chain، AI بررسی coherence:
| الگو | چه بررسی شود |
|---|---|
| **Data pipeline** | schema هر مرحله، handling empty result |
| **AI/LLM chain** | prompt format ↔ model ↔ parser سازگار؟ validation؟ |
| **Business logic (R11 مثال trade)** | signal ↔ risk model، position ↔ account size، stop-loss ↔ timeframe |
| **Auth/Permission** | همه‌ی mutation از permission گذر می‌کند؟ |
| **Feedback loop** | outcome به config/model برمی‌گردد؟ |
| **Notification chain (R12)** | event → notify_event → caption → silent decision → delivery — همه consistent؟ |
**۵-B. Logical Anti-pattern Detection:**
ماژول جدید: `backend/app/services/scan_v5/anti_pattern_detector.py`
AI روی purpose_inventory + کد، این الگوها را پیدا می‌کند:
| Anti-pattern | مثال |
|---|---|
| داده بی‌مصرف | API call، DB write، ولی هیچ read |
| AI بدون validation | response parse می‌شود ولی validity چک نمی‌شود |
| Magic threshold | `> 0.65:` بدون توضیح |
| Conflicting defaults | یک field default متفاوت در جاهای مختلف |
| Silent failure در crucial path | `except: pass` در business logic |
| Broken feedback loop (R11) | outcome لاگ ولی به model نمی‌رسد |
| Stale assumption | کد فرض می‌کند رفتار سرویس X خاصه، X تغییر کرد |
| Over/under-engineering | برای ساده ۵ لایه، برای پیچیده hardcode |
| Conditional inconsistency | conditions با تغییرات اخیر inconsistent |
| Threshold-Outcome mismatch (R11) | parameters نتایج مطلوب تولید نمی‌کنند |
| Notification mismatch (R12) | event critical ولی silent=True، یا opposite |
**۵-C. Hidden Requirements Discovery (R8):**
برای هر feature که کاربر فراموش کرده «چی هست برای چیه»:
- AI روی `creation_context` (از فاز ۱) + task history + commit messages تحلیل
- استخراج: «این feature چه وقت، چرا، با چه هدفی اضافه شد؟»
- نتیجه:
  - هدف منسوخ → task `cleanup`
  - هدف معتبر، پیاده‌سازی ضعیف → task `refactor`
  - هدف معتبر، پیاده‌سازی خوب، docs نیست → task `document`
**۵-D. Outcome-based Effectiveness Audit (R11):**
اگر outcome data دارد (از فاز ۴):
- AI تحلیل می‌کند آیا outcome با `stated_purpose` می‌خواند
- مثال R11: trade — اگر purpose="earn profit" و win-rate=30% → effectiveness LOW
- اگر LOW → task `logic_audit` با priority بالا
**۵-E. Task Generation:**
نوع جدید task: `logic_audit`
- AC outcome-oriented:
  - ❌ «این کد را fix کن»
  - ✅ «بعد از این تغییر، win-rate باید ≥40% یا parameters محافظه‌کارانه‌تر شود»
- AI explanation کامل: چرا اشتباه + چه راه‌حل + چه impact
### Acceptance Criteria فاز ۵
- روی پروژه فعلی ≥ ۳ logic issue + ≥ ۱ pipeline coherence + ≥ ۲ anti-pattern logical
- روی پروژه trade فرضی (R11)، scan باگ منطقی هماهنگی AI-data شناسایی کند
- task `logic_audit` با AC outcome-oriented + AI explanation کامل
```

## 🎯 هدف (خلاصه ساختاریافته)
فاز ۵ Logical Audit — تشخیص ناهماهنگی منطقی و ضدالگوها

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/scan_v5/coherence_analyzer.py:1-50` — `کل فایل` — این فایل deep-read شده — باید توابع analyze_pipeline_coherence, discover_hidden_
  ```python
  # فایل موجود در deep context — نیاز به توسعه کامل دارد
  # coherence_analyzer.py فعلی skeleton است و باید توابع تحلیل coherence اضافه شود
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی فاز ۵ Logical Audit شامل ۵ زیربخش: (A) تشخیص انسجام زنجیره‌های پردازش (Pipeline Coherence) در ماژول جدید `backend/app/services/scan_v5/coherence_analyzer.py`، (B) تشخیص ضدالگوهای منطقی (Anti-pattern) در ماژول جدید `backend/app/services/scan_v5/anti_pattern_detector.py`، (C) کشف نیازمندی‌های پنهان (Hidden Requirements) با تحلیل `creation_context` و task history، (D) ممیزی اثربخشی مبتنی بر خروجی (Outcome-based Effectiveness) با استفاده از `outcome data` و `stated_purpose`، و (E) تولید تسک‌های `logic_audit` با AC outcome-oriented. خارج از scope: اجرای واقعی تغییرات کد (فقط تحلیل و تولید تسک)، و هرگونه اسکن امنیتی یا عملکردی. نکته حیاتی: این فاز صرفاً تحلیل معنایی و منطقی است و نباید به اجرای خودکار تغییرات منجر شود. کلیدواژه‌ها: `backend/app/services/scan_v5/coherence_analyzer.py`, `backend/app/services/scan_v5/anti_pattern_detector.py`, `purpose_inventory`, `interacting_with`, `logic_audit`, R10, R11, R12, R8, `creation_context`, `stated_purpose`, `outcome data`. بر اساس کد واقعی پروژه، فایل‌های `backend/app/services/scan_v5/coherence_analyzer.py` و `backend/app/services/scan_v5/anti_pattern_detector.py` در deep context موجود هستند و باید توسعه داده شوند. فایل `backend/app/services/notification_service.py` (خطوط ۱۲۰-۳۳۶) حاوی EVENT_REGISTRY است که برای Pipeline Coherence Detection (Notification chain R12) باید تحلیل شود. فایل `backend/app/services/scan_v5/scan_bundle.py` orchestrator اصلی scan است که باید ماژول‌های جدید را فراخوانی کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. توسعه `backend/app/services/scan_v5/coherence_analyzer.py`: افزودن تابع `analyze_pipeline_coherence(purpose_inventory: dict) -> List[PipelineIssue]` که برای هر chain (Data, AI/LLM, Business logic, Auth/Permission, Feedback loop, Notification) coherence را بررسی کند. ۲. توسعه `backend/app/services/scan_v5/anti_pattern_detector.py`: افزودن تابع `detect_logical_anti_patterns(purpose_inventory: dict, code_files: dict) -> List[AntiPatternIssue]` که ۱۱ الگوی مشخص شده (داده بی‌مصرف، AI بدون validation، Magic threshold، Conflicting defaults، Silent failure، Broken feedback loop، Stale assumption، Over/under-engineering، Conditional inconsistency، Threshold-Outcome mismatch، Notification mismatch) را تشخیص دهد. ۳. ایجاد تابع `discover_hidden_requirements(creation_context: dict, task_history: list, commit_messages: list) -> List[HiddenRequirement]` در فایل جدید یا الحاق به coherence_analyzer. ۴. ایجاد تابع `audit_outcome_effectiveness(outcome_data: dict, stated_purpose: str) -> List[EffectivenessIssue]` در فایل جدید یا الحاق به anti_pattern_detector. ۵. افزودن نوع تسک `logic_audit` به سیستم تولید تسک در `backend/app/services/scan_v5/_findings_to_tasks.py` با AC outcome-oriented و AI explanation کامل. ۶. به‌روزرسانی `backend/app/services/scan_v5/scan_bundle.py` برای فراخوانی ماژول‌های جدید در pipeline scan.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 35: فاز ۶ — Notification System Audit: بررسی و بهینه‌سازی سیستم اطلاع‌رسانی (R12)

**Scope:** این مرحله شامل ممیزی کامل تمام notification‌های موجود در کد (notify_event calls)، ایجاد inventory از آن‌ها، بررسی انسجام و کامل بودن caption‌ها، تنظیم silent/sound مناسب، بررسی attachments، جلوگیری از spam، شناسایی notification‌های قدیمی یا گمشده، و ارائه پیشنهادات ارتقا برای notification scan_completed است. همچنین شامل ایجاد task‌های notification_audit برای هر مورد مشکل‌دار و تنظیم فیلدهای جدید WatchedProject.auto_task_notify_sound و WatchedProject.scan_notify_sound به False می‌شود. فایل‌های هدف: notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py.
**Key terms:** notification_inventory, notify_event, notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py, WatchedProject.auto_task_notify_sound, WatchedProject.scan_notify_sound, notification_audit, scan_completed, R12, R6

**بخش مربوط از متن کاربر:**
```
## 🅵 فاز ۶ — Notification System Audit (R12)
> پوشش **R6, R12** — صریحاً audit notification ها
### مسئله (R12)
> «در پرامپت برای پیام‌رسانی تلگرام هم جایی در نظر گرفتی؟ در بررسی‌ها نوع اطلاع‌رسانیش هم بررسی بشه و بهینه بشه»
### تغییرات
**۶-A. Notification Inventory (از فاز ۱ — لایه ۱۱):**
برای هر `notify_event(...)` call در کد:

```python
notification_inventory[call_id] = {
    "file_path": "...",
    "line": ...,
    "event_type": "...",          # "task_created" | "verify_done" | ...
    "caption_template": "...",
    "silent_default": True | False | None,
    "attachments": [...],
    "trigger_condition": "...",   # کد منطق در کجا fire می‌شود
    "frequency_estimate": "...",  # احتمال در روز
}
```

**۶-B. Notification Coherence Audit (R12):**
AI روی notification_inventory:
| سوال | چه چیزی audit شود |
|---|---|
| caption کامل است؟ | همه‌ی فیلدهای مهم در caption هستند؟ (title, intent, link, attachments) |
| silent/sound مناسب است؟ | event critical → sound. event routine → silent |
| attachments صحیح؟ | task creation → prompt.md، verify done → bundle.pdf، scan done → scan-bundle.pdf |
| timing مناسب؟ | spam جلوگیری شده؟ batching هست؟ |
| stale notifications؟ | event type که دیگر کد آن وجود ندارد |
| missing notifications؟ | event critical که notification ندارد |
| **scan-specific (R12)**: | scan completion notification با همه‌ی مدارک ضروری: findings, tasks created, delta, logic audit results, inspector session reference |
```

python
notification_inventory[call_id] = {
    "file_path": "...",
    "line": ...,
    "event_type": "...",          # "task_created" | "verify_done" | ...
    "caption_template": "...",
    "silent_default": True | False | None,
    "attachments": [...],
    "trigger_condition": "...",   # کد منطق در کجا fire می‌شود
    "frequency_estimate": "...",  # احتمال در روز
}
```

**۶-B. Notification Coherence Audit (R12):**
AI روی notification_inventory:
| سوال | چه چیزی audit شود |
|---|---|
| caption کامل است؟ | همه‌ی فیلدهای مهم در caption هستند؟ (title, intent, link, attachments) |
| silent/sound مناسب است؟ | event critical → sound. event routine → silent |
| attachments صحیح؟ | task creation → prompt.md، verify done → bundle.pdf، scan done → scan-bundle.pdf |
| timing مناسب؟ | spam جلوگیری شده؟ batching هست؟ |
| stale notifications؟ | event type که دیگر کد آن وجود ندارد |
| missing notifications؟ | event critical که notification ندارد |
| **scan-specific (R12)**: | scan completion notification با همه‌ی مدارک ضروری: findings, tasks created, delta, logic audit results, inspector session reference |

--- کلیدواژه‌ها ---
notification_inventory, notify_event, notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py, WatchedProject.auto_task_notify_sound, WatchedProject.scan_notify_sound, notification_audit, scan_completed, R12, R6
```

## 🎯 هدف (خلاصه ساختاریافته)
فاز ۶ — ممیزی کامل سیستم نوتیفیکیشن و بهینه‌سازی R12

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/notification_service.py:120-336` — `EVENT_REGISTRY` — این دیکشنری مرجع تمام رویدادهاست — باید inventory از notify_event calls در مقابل این registry تطبیق داده شود
  ```python
  EVENT_REGISTRY: Dict[str, Dict[str, Any]] = {
      # Verify events
      "verify_done": {
          "label": "✅ Verify موفق",
          "help": "وقتی verify status = done باشد",
          "default_enabled": True,
          "default_sound": True,
          "icon": "✅",
      },
      ...
  }
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز ۶ — Notification System Audit: بررسی و بهینه‌سازی سیستم اطلاع‌رسانی (R12). این مرحله شامل ممیزی کامل تمام notification‌های موجود در کد (notify_event calls)، ایجاد inventory از آن‌ها، بررسی انسجام و کامل بودن caption‌ها، تنظیم silent/sound مناسب، بررسی attachments، جلوگیری از spam، شناسایی notification‌های قدیمی یا گمشده، و ارائه پیشنهادات ارتقا برای notification scan_completed است. همچنین شامل ایجاد task‌های notification_audit برای هر مورد مشکل‌دار و تنظیم فیلدهای جدید WatchedProject.auto_task_notify_sound و WatchedProject.scan_notify_sound به False می‌شود. فایل‌های هدف: notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py.

بر اساس کد واقعی پروژه:
- در backend/app/services/notification_service.py خط ۱۲۰-۳۳۶ EVENT_REGISTRY شامل ۳۰+ رویداد است اما هیچ inventory مرکزی از notify_event calls وجود ندارد.
- در backend/app/api/routes/notifications.py خط ۸۸-۹۹ endpoint POST /notifications/notify وجود دارد که notify_event را صدا می‌زند.
- فایل backend/app/services/oversight_telegram_compose.py (deep-read شده) حاوی منطق compose پیام‌های تلگرام است.
- فایل backend/app/services/oversight_mega_bundle.py خط ۶۰-۳۳۵ build_mega_bundle_md را دارد که برای attachments استفاده می‌شود.
- فایل backend/app/services/scan_v5/notification_auditor.py (deep-read شده) auditor مخصوص نوتیفیکیشن‌های اسکن است.

کلیدواژه‌های کاربر: notification_inventory, notify_event, notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py, WatchedProject.auto_task_notify_sound, WatchedProject.scan_notify_sound, notification_audit, scan_completed, R12, R6

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. ایجاد اسکریپت/ماژول audit_notifications.py که تمام notify_event calls را در کدبیس اسکن کرده و inventory JSON می‌سازد.
۲. در backend/app/services/notification_service.py یک متد جدید scan_notify_events() اضافه کن که تمام کدهای پروژه را برای notify_event(...) جستجو کرده و خروجی inventory بدهد.
۳. در backend/app/services/oversight_telegram_compose.py بررسی کن که captionهای ارسالی کامل هستند (title, intent, link, attachments).
۴. در backend/app/services/oversight_mega_bundle.py اطمینان حاصل کن که attachmentهای صحیح (prompt.md, bundle.pdf, scan-bundle.pdf) به رویدادهای مربوطه متصل شوند.
۵. فیلدهای WatchedProject.auto_task_notify_sound و WatchedProject.scan_notify_sound را در مدل WatchedProject (احتمالاً در backend/app/models/project.py) اضافه کن و مقدار پیش‌فرض False بده.
۶. برای scan_completed یک notification جامع با همه مدارک (findings, tasks created, delta, logic audit results, inspector session reference) ایجاد کن.
۷. برای هر notify_event مشکل‌دار یک task از نوع notification_audit ایجاد کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 36: فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)

**Scope:** این فاز شامل ۶ زیربخش (۷-A تا ۷-F) است که همگی برای بهبود کیفیت پرامپت‌ها و چک‌لیست‌ها در هر دو مسیر manual و auto طراحی شده‌اند. تغییرات شامل: ساختار غنی AC با ۷ فیلد جدید، ساختار غنی task_step با ۶ فیلد، اضافه شدن حالت هوشمند چک‌لیست (auto/always/never)، به‌روزرسانی قالب‌های پرامپت در oversight_strong_prompt.py، جلوگیری از false-positive با قوانین صریح، و یکپارچه‌سازی با خروجی فازهای ۱، ۴، ۵، ۶. نکته حیاتی: backward compatibility با ACهای قدیمی (فقط text) باید حفظ شود.
**Key terms:** oversight_service.py, oversight_strong_prompt.py, idea_to_prompt, _ai_plan_steps_from_idea, build_strong_prompt, WatchedProject.auto_task_checklist_mode, purpose_inventory, runtime_state, logic_audit_findings, notification_audit

**بخش مربوط از متن کاربر:**
```
## 🅶 فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)
> پوشش **R5, R9, R13** — برای **manual + auto** هر دو
### مسئله (R9 صریح)
> «در تولید ایده خام به پرامپت، پرامپت در برخی قسمت‌ها دقیق و واضح تولید نمیشه... باید هوشمندتر بشه خود متن پرامپت و چک‌لیستی که ازش تولید میشه»
### مسئله (R13 صریح)
> «این بهبود پرامپت‌نویسی تسک‌ها آیا فقط برای تسک‌های سیستمی یا تسک‌های دستی هم شامل میشه؟»
**جواب: هر دو.**
### تغییرات
**۷-A. ساختار غنی AC (هم manual، هم auto):**
برای **manual** path در `oversight_service.py:idea_to_prompt` (~3454):
برای **auto** path در `oversight_service.py:task creation from scan` (~4700-4740):
برای **scan-generated** path در `oversight_strong_prompt.py:build_strong_prompt`:
هر AC ساختار غنی:

```python
{
    "text": "...",                          # توضیح اصلی (می‌تواند نام بدهد)
    "behavior": "...",                      # رفتار قابل مشاهده — چه چیزی observable است
    "acceptance_signal": "...",             # سؤال قابل-verify
    "business_intent": "...",               # چرا این لازم است
    "alternative_implementations": [...],   # نام‌های جایگزین قابل قبول (R9 — جلوگیری از نام-محوری)
    "non_goals": "...",                     # چه چیزی این AC نیست
    "false_positive_guard": "...",          # چه شواهد ضعیفی نشانه done نیست (R9)
}
```

**۷-B. ساختار غنی task_step (در `_ai_plan_steps_from_idea`):**
برای manual و auto (R13):

```python
{
    "title": "...",
    "scope": "...",
    "behavior_observable": "...",       # خروجی observable
    "verification_hint": "...",         # کجا verify بیابد
    "business_intent": "...",           # چرا این مرحله
    "non_goals": "...",
}
```

**۷-C. Smart Checklist Mode (R5):**
> «حالت هوشمند که برای تولید چک‌لیست یا عدم تولیدش حسب نیاز هست»
`WatchedProject.auto_task_checklist_mode: Literal["auto","always","never"] = "auto"`
- `auto`: AI تصمیم می‌گیرد بر اساس پیچیدگی (≥3 stage → checklist، single-action → skip)
- `always`: همیشه چک‌لیست
- `never`: هرگز
این برای **هم manual و هم auto** کار می‌کند.
**۷-D. Update prompt templates:**
در `oversight_strong_prompt.py`:
- اضافه شدن section "🎯 معیار رفتاری + business intent + alternative implementations"
- AI صریح راهنمایی شود: AC نام-محور بد است، AC رفتار-محور خوب
**۷-E. جلوگیری از false-positive (R9):**
> «جوری هم نشه که سیستم کاری که بد انجام شده... در verify تیک بزنه که کامل شده»
دستورالعمل به AI:
- اگر AC vague → split به sub-behaviors concrete
- هرگز AC بدون `acceptance_signal` نسازد
- `false_positive_guard` فیلد: چه شواهد ضعیفی نباید سبب done شود
- مثال: «اگر فقط فایل با نام وجود دارد، done نیست — باید رفتار X هم باشد»
**۷-F. Integration با فازهای قبلی:**
پرامپت تولید‌شده استفاده کند از:
- `purpose_inventory` (فاز ۱)
- `runtime_state` (فاز ۴)
- `logic_audit_findings` (فاز ۵)
- `notification_audit` (فاز ۶)
### Acceptance Criteria فاز ۷
- **manual** path: پرامپت‌های جدید برای ۳ ایده‌ی نمونه شامل `behavior` + `acceptance_signal` + `business_intent` + `alternative_implementations` + `false_positive_guard`
- **auto** path: همان ساختار برای task های scan-generated
- چک‌لیست‌ها شامل `behavior_observable` در هر step
- mode `auto` در `_ai_plan_steps_from_idea` کار می‌کند برای هر دو
- verify روی same tasks: false-negative ≤ ۲۰%، false-positive ≤ ۵%
- backward compat: AC های قدیمی (فقط text) همچنان کار می‌کنند
```

python
{
    "text": "...",                          # توضیح اصلی (می‌تواند نام بدهد)
    "behavior": "...",                      # رفتار قابل مشاهده — چه چیزی observable است
    "acceptance_signal": "...",             # سؤال قابل-verify
    "business_intent": "...",               # چرا این لازم است
    "alternative_implementations": [...],   # نام‌های جایگزین قابل قبول (R9 — جلوگیری از نام-محوری)
    "non_goals": "...",                     # چه چیزی این AC نیست
    "false_positive_guard": "...",          # چه شواهد ضعیفی نشانه done نیست (R9)
}
```

**۷-B. ساختار غنی task_step (در `_ai_plan_steps_from_idea`):**
برای manual و auto (R13):

```python
{
    "title": "...",
    "scope": "...",
    "behavior_observable": "...",       # خروجی observable
    "verification_hint": "...",         # کجا verify بیابد
    "business_intent": "...",           # چرا این مرحله
    "non_goals": "...",
}
```

**۷-C. Smart Checklist Mode (R5):**
> «حالت هوشمند که برای تولید چک‌لیست یا عدم تولیدش حسب نیاز هست»
`WatchedProject.auto_task_checklist_mode: Literal["auto","always","never"] = "auto"`
- `auto`: AI تصمیم می‌گیرد بر اساس پیچیدگی (≥3 stage → checklist، single-action → skip)
- `always`: همیشه چک‌لیست
- `never`: هرگز
این برای **هم manual و هم auto** کار می‌کند.
**۷-D. Update prompt templates:**
در `oversight_strong_prompt.py`:
- اضافه شدن section "🎯 معیار رفتاری + business intent + alternative implementations"
- AI صریح راهنمایی شود: AC نام-محور بد است، AC رفتار-محور خوب
**۷-E. جلوگیری از false-positive (R9):**
> «جوری هم نشه که سیستم کاری که بد انجام شده... در verify تیک بزنه که کامل شده»
دستورالعمل به AI:
- اگر AC vague → split به sub-behaviors concrete
- هرگز AC بدون `acceptance_signal` نسازد
- `false_positive_guard` فیلد: چه شواهد ضعیفی نباید سبب done شود
- مثال: «اگر فقط فایل با نام وجود دارد، done نیست — باید رفتار X هم باشد»
**۷-F. Integration با فازهای قبلی:**
پرامپت تولید‌شده استفاده کند از:
- `purpose_inventory` (فاز ۱)
- `runtime_state` (فاز ۴)
- `logic_audit_findings` (فاز ۵)
- `notification_audit` (فاز ۶)
### Acceptance Criteria فاز ۷
- **manual** path: پرامپت‌های جدید برای ۳ ایده‌ی نمونه شامل `behavior` + `acceptance_signal` + `business_intent` + `alternative_implementations` + `false_positive_guard`
- **auto** path: همان ساختار برای task های scan-generated
- چک‌لیست‌ها شامل `behavior_observable` در هر step
- mode `auto` در `_ai_plan_steps_from_idea` کار می‌کند برای هر دو
- verify روی same tasks: false-negative ≤ ۲۰%، false-positive ≤ ۵%
- backward compat: AC های قدیمی (فقط text) همچنان کار می‌کنند

--- کلیدواژه‌ها ---
oversight_service.py, oversight_strong_prompt.py, idea_to_prompt, _ai_plan_steps_from_idea, build_strong_prompt, WatchedProject.auto_task_checklist_mode, purpose_inventory, runtime_state, logic_audit_findings, notification_audit
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی ساختار غنی AC و Smart Checklist در فاز ۷

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به فاز ۷ (Smart Prompt + Smart Checklist) است که شامل ۶ زیربخش (۷-A تا ۷-F) برای بهبود کیفیت پرامپت‌ها و چک‌لیست‌ها در هر دو مسیر manual و auto می‌باشد. کاربر درخواست کرده است که ساختار AC (Acceptance Criteria) با ۷ فیلد جدید شامل text, behavior, acceptance_signal, business_intent, alternative_implementations, non_goals, false_positive_guard غنی شود. همچنین ساختار task_step با ۶ فیلد جدید شامل title, scope, behavior_observable, verification_hint, business_intent, non_goals توسعه یابد. حالت هوشمند چک‌لیست (auto/always/never) در WatchedProject.auto_task_checklist_mode اضافه شود. قالب‌های پرامپت در backend/app/services/oversight_strong_prompt.py به‌روزرسانی شوند. جلوگیری از false-positive با قوانین صریح در فیلد false_positive_guard پیاده‌سازی شود. یکپارچه‌سازی با خروجی فازهای ۱ (purpose_inventory)، ۴ (runtime_state)، ۵ (logic_audit_findings)، ۶ (notification_audit) انجام شود. نکته حیاتی: backward compatibility با ACهای قدیمی (فقط text) باید حفظ شود. کلیدواژه‌های اصلی: oversight_service.py, oversight_strong_prompt.py, idea_to_prompt, _ai_plan_steps_from_idea, build_strong_prompt, WatchedProject.auto_task_checklist_mode, purpose_inventory, runtime_state, logic_audit_findings, notification_audit. شواهد در کد: در oversight_service.py خط ۳۲۹-۳۳۰ فیلد acceptance_criteria به صورت List[Any] تعریف شده که باید به ساختار dict غنی تبدیل شود. در oversight_strong_prompt.py خط ۱۷۳-۱۷۴ پارامتر acceptance_criteria به صورت Optional[List[Any]] است که باید از فیلدهای جدید پشتیبانی کند. در oversight_service.py خط ۱۷۹ فیلد auto_task_checklist_mode با مقدار پیش‌فرض 'auto' تعریف شده که باید به Literal['auto','always','never'] تغییر یابد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. در backend/app/services/oversight_service.py، تابع idea_to_prompt (حدود خط ۳۴۵۴) را اصلاح کن تا ACهای خروجی شامل ۷ فیلد جدید (text, behavior, acceptance_signal, business_intent, alternative_implementations, non_goals, false_positive_guard) باشند. ۲. در همان فایل، تابع _ai_plan_steps_from_idea را اصلاح کن تا task_stepهای خروجی شامل ۶ فیلد جدید (title, scope, behavior_observable, verification_hint, business_intent, non_goals) باشند. ۳. در backend/app/services/oversight_service.py خط ۱۷۹، نوع auto_task_checklist_mode را از str به Literal['auto','always','never'] تغییر بده و منطق تصمیم‌گیری هوشمند را پیاده‌سازی کن. ۴. در backend/app/services/oversight_strong_prompt.py، تابع build_strong_prompt (خط ۱۵۸) را به‌روزرسانی کن تا section جدید '🎯 معیار رفتاری + business intent + alternative implementations' اضافه شود و AI راهنمایی شود که AC نام-محور بد است و AC رفتار-محور خوب. ۵. در همان فایل، منطق جلوگیری از false-positive را با استفاده از فیلد false_positive_guard پیاده‌سازی کن. ۶. یکپارچه‌سازی با فازهای قبلی: از purpose_inventory (فاز ۱)، runtime_state (فاز ۴)، logic_audit_findings (فاز ۵)، notification_audit (فاز ۶) در تولید پرامپت استفاده کن. ۷. backward compatibility: ACهای قدیمی (فقط text) را در normalize_ac_list در oversight_service.py خط ۶۱۲-۶۳۳ پشتیبانی کن.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 37: فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration

**Scope:** این بخش شامل ۴ زیربخش است: (۸-A) افزودن task_steps به auto-tasks در oversight_service.py با دو mode 'always' و 'auto'، (۸-B) قالب notification تلگرام برای auto-scan task با caption و attachments مشخص، (۸-C) اضافه کردن فیلدهای silent default (auto_task_notify_sound و scan_notify_sound) به WatchedProject و UI checkbox، (۸-D) notification تکمیل scan با خلاصه و Bundle PDF. خارج از scope: تغییر رفتار تسک‌های دستی (باید حفظ شود)، پیاده‌سازی Inspector session (فقط لینک)، و پیاده‌سازی actual PDF generation (فقط اشاره به Bundle PDF).
**Key terms:** oversight_service.py, notification_service.py, WatchedProject, auto_task_checklist_mode, build_strong_prompt, _ai_plan_steps_from_idea, auto_task_notify_sound, scan_notify_sound, Bundle PDF, Inspector session

**بخش مربوط از متن کاربر:**
```
## 🅷 فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration
> پوشش **R5, R6** — تسک‌های scan باید مثل manual باشند
### مسئله (R5, R6)
- تسک‌های auto-scan الان `prompt + AC` دارند ولی `task_steps` ندارند
- Telegram notification برای آن‌ها audit نشده
- کاربر می‌خواهد silent default
### تغییرات
**۸-A. task_steps برای auto-tasks:**
در `oversight_service.py:4700-4740`:
- بعد از `build_strong_prompt`، اگر `auto_task_checklist_mode != "never"`:
  - if `mode == "always"` → همیشه call `_ai_plan_steps_from_idea`
  - if `mode == "auto"` → AI تصمیم می‌گیرد بر اساس پیچیدگی
**۸-B. Telegram Notification Template (R6):**
`notification_service.py`:
```python
# Caption template برای auto-scan task
{
    "🤖 تسک جدید از scan خودکار",
    "📌 {title}",
    "🎯 {business_intent[:200]}",
    "📋 چک‌لیست: {N step}" if has_steps else None,
    "🧠 Logic concerns: {logic_audit_count}" if has_logic_issues else None,
    "🔄 وابسته به تغییر: {dependent_changes}" if delta_dependent else None,
    "📊 Outcome impact: {outcome_score}" if outcome_data else None,
    "🔗 [لینک کارت]",
    "🔍 [Inspector session]",
}
# Attachments:
- prompt_full.md (full task prompt)
- scan_inspector_session_link
```
**۸-C. Silent default + UI control:**
`WatchedProject` fields:
```python
auto_task_notify_sound: bool = False     # silent for auto-tasks
scan_notify_sound: bool = False           # silent for scan completion
```
در UI: checkbox `🔔 صدای notification برای تسک‌های auto-scan`.
**۸-D. Scan-completion notification:**
علاوه بر notification هر task، یک scan-completion notification:
```
✅ scan تکمیل شد — {project_name}
📊 خلاصه:
- {N} task جدید ایجاد شد
- {N} delta change شناسایی
- {N} stale item
- {N} logic issue
- {N} notification audit
📎 Bundle PDF (با همه screenshots و findings)
🔍 Inspector session: [link]
```
### Acceptance Criteria فاز ۸
- بعد از scan: همه auto-tasks در UI چک‌لیست دارند (اگر mode=auto و پیچیده‌اند)
- caption تلگرام شامل همه فیلدها
- silent default = true
- scan_completed notification با Bundle PDF + Inspector session link
- regression: تسک‌های دستی رفتار قبلی را حفظ کنند
```

python
# Caption template برای auto-scan task
{
    "🤖 تسک جدید از scan خودکار",
    "📌 {title}",
    "🎯 {business_intent[:200]}",
    "📋 چک‌لیست: {N step}" if has_steps else None,
    "🧠 Logic concerns: {logic_audit_count}" if has_logic_issues else None,
    "🔄 وابسته به تغییر: {dependent_changes}" if delta_dependent else None,
    "📊 Outcome impact: {outcome_score}" if outcome_data else None,
    "🔗 [لینک کارت]",
    "🔍 [Inspector session]",
}
# Attachments:
- prompt_full.md (full task prompt)
- scan_inspector_session_link
```
**۸-C. Silent default + UI control:**
`WatchedProject` fields:
```python
auto_task_notify_sound: bool = False     # silent for auto-tasks
scan_notify_sound: bool = False           # silent for scan completion
```
در UI: checkbox `🔔 صدای notification برای تسک‌های auto-scan`.
**۸-D. Scan-completion notification:**
علاوه بر notification هر task، یک scan-completion notification:
```
✅ scan تکمیل شد — {project_name}
📊 خلاصه:
- {N} task جدید ایجاد شد
- {N} delta change شناسایی
- {N} stale item
- {N} logic issue
- {N} notification audit
📎 Bundle PDF (با همه screenshots و findings)
🔍 Inspector session: [link]
```
### Acceptance Criteria فاز ۸
- بعد از scan: همه auto-tasks در UI چک‌لیست دارند (اگر mode=auto و پیچیده‌اند)
- caption تلگرام شامل همه فیلدها
- silent default = true
- scan_completed notification با Bundle PDF + Inspector session link
- regression: تسک‌های دستی رفتار قبلی را حفظ کنند

--- کلیدواژه‌ها ---
oversight_service.py, notification_service.py, WatchedProject, auto_task_checklist_mode, build_strong_prompt, _ai_plan_steps_from_idea, auto_task_notify_sound, scan_notify_sound, Bundle PDF, Inspector session
```

## 🎯 هدف (خلاصه ساختاریافته)
فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/oversight_service.py:179-181` — `WatchedProject.auto_task_checklist_mode` — این فیلدها قبلاً تعریف شده‌اند — نیاز به UI checkbox و استفاده در logic جدید دارند.
  ```python
  auto_task_checklist_mode: str = "auto"  # "auto" | "always" | "never"  R5
      cleanup_tasks_enabled: bool = True
      auto_task_notify_sound: bool = False  # R6 — silent default
      scan_notify_sound: bool = False  # R6
  ```
- `backend/app/services/oversight_service.py:385-387` — `OversightTask.task_steps`
  ```python
  task_steps: List[Dict[str, Any]] = field(default
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی فاز ۸ شامل ۴ زیربخش: (۸-A) افزودن task_steps به auto-tasks در oversight_service.py با دو mode 'always' و 'auto'، (۸-B) قالب notification تلگرام برای auto-scan task با caption و attachments مشخص، (۸-C) اضافه کردن فیلدهای silent default (auto_task_notify_sound و scan_notify_sound) به WatchedProject و UI checkbox، (۸-D) notification تکمیل scan با خلاصه و Bundle PDF. خارج از scope: تغییر رفتار تسک‌های دستی (باید حفظ شود)، پیاده‌سازی Inspector session (فقط لینک)، و پیاده‌سازی actual PDF generation (فقط اشاره به Bundle PDF).

کلیدواژه‌ها: oversight_service.py, notification_service.py, WatchedProject, auto_task_checklist_mode, build_strong_prompt, _ai_plan_steps_from_idea, auto_task_notify_sound, scan_notify_sound, Bundle PDF, Inspector session

شواهد در کد: در oversight_service.py خط ۱۷۹-۱۸۱ فیلد auto_task_checklist_mode با مقدار پیش‌فرض 'auto' و cleanup_tasks_enabled=True تعریف شده. در خط ۳۸۵-۳۸۷ فیلد task_steps و overall_completion_pct در dataclass OversightTask وجود دارد. در notification_service.py خط ۱۲۰-۳۳۶ EVENT_REGISTRY شامل eventهای scan_done (خط ۱۶۵-۱۷۱) و task_created (خط ۱۸۷-۱۹۳) است اما template اختصاصی برای auto-scan task وجود ندارد. فیلدهای auto_task_notify_sound و scan_notify_sound در WatchedProject در خطوط ۱۸۱-۱۸۲ تعریف شده‌اند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. در oversight_service.py تابع _ai_plan_steps_from_idea را پیاده‌سازی کن (حدود خط ۴۷۰۰-۴۷۴۰) که با AI task_steps را از raw_idea تولید کند. ۲. در تابع build_strong_prompt (حدود خط ۴۶۰۰) بعد از فراخوانی، اگر auto_task_checklist_mode != 'never' باشد: اگر mode=='always' همیشه _ai_plan_steps_from_idea را صدا بزن، اگر mode=='auto' از AI بخواه بر اساس پیچیدگی تصمیم بگیرد. ۳. در notification_service.py یک تابع جدید build_auto_scan_caption بساز که caption شامل {title, business_intent[:200], checklist count, logic_audit_count, dependent_changes, outcome_score, link, inspector_session_link} باشد. ۴. در notification_service.py متد send_notification_for_auto_task اضافه کن که prompt_full.md را به‌عنوان document و caption را به‌عنوان متن ارسال کند. ۵. در oversight_service.py بعد از اتمام scan، یک notification scan-completion با خلاصه (تعداد task جدید، delta change، stale item، logic issue، notification audit) + Bundle PDF + Inspector session link بفرست. ۶. در WatchedProject فیلدهای auto_task_notify_sound و scan_notify_sound (که قبلاً در خطوط ۱۸۱-۱۸۲ تعریف شده) را در UI به‌عنوان checkbox نمایش بده.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 38: فاز ۹ — UI Redesign (R2, R8): بازطراحی کامل UI با ۴ تب، گزینه‌های جدید و AI explanation

**Scope:** این بخش شامل بازطراحی کامل UI Oversight با ۴ تب (Coverage, Intelligence, Lifecycle, Notifications) به‌جای ۳ تب قبلی است. تغییرات شامل: بازنگری scan_depth modes (اضافه شدن mode‌های balanced و ultra)، بازنگری criteria_weights (preset selector + sliders در details)، بازنگری Smart Task Lifecycle با وضعیت‌سنجی هر گزینه، اضافه شدن فیلدهای جدید WatchedProject (شامل inventory_layers, stale_detection_enabled, delta_analysis_enabled, runtime_discovery_enabled, outcome_data_enabled, logic_audit_enabled, notification_audit_enabled, inspector_session_enabled, auto_task_checklist_mode, cleanup_tasks_enabled, auto_task_notify_sound, scan_notify_sound)، AI explanation برای هر گزینه با help icon و Feature Inventory Panel. backward compatibility برای scan_depth قدیمی باید حفظ شود.
**Key terms:** scan_depth, criteria_weights, WatchedProject, inventory_layers, stale_detection_enabled, delta_analysis_enabled, runtime_discovery_enabled, outcome_data_enabled, logic_audit_enabled, notification_audit_enabled, inspector_session_enabled, auto_task_checklist_mode, cleanup_tasks_enabled, auto_task_notify_sound, scan_notify_sound, Feature Inventory Panel, AI explanation, frontend/src/app/oversight/page.tsx

**بخش مربوط از متن کاربر:**
```
## 🅸 فاز ۹ — UI Redesign (R2, R8)
> پوشش **R2** — به‌روزرسانی گزینه‌ها
### مسئله (R2)
> «گزینه‌هاش هم به روز رسانی بشن»
### تغییرات
**۹-A. بازنگری scan_depth modes:**
از (فعلی):
```
quick (3 pass) | standard (6 pass) | deep (12 pass، پیش‌فرض) | thorough (12 + health + roadmap)
```
به:
```
⚡ quick (5 pass) — frontend + backend + security + delta + stale
⚖️ balanced (8 pass — پیش‌فرض جدید) — quick + dependency + completeness + runtime
🔬 deep (12 pass) — همه + impact analysis
🧠 ultra (12 pass + logic audit + outcome + notification audit + inspector session)
```
**۹-B. بازنگری criteria_weights:**
به‌جای ۶ slider:
- preset selector: "general", "security-first", "tests-first", "feature-completeness", "logic-quality"
- sliders در `<details>` (advanced)
**۹-C. بازنگری Smart Task Lifecycle:**
- بررسی هر گزینه: کار می‌کند؟
- label با وضعیت فعلی
**۹-D. گزینه‌های جدید Phase 5:**
`WatchedProject` فیلدهای جدید (همه با default sensible):
```python
# Coverage
inventory_layers: List[str] = ["all"]    # یا subset
# Intelligence
stale_detection_enabled: bool = True
delta_analysis_enabled: bool = True
runtime_discovery_enabled: bool = True
outcome_data_enabled: bool = True
logic_audit_enabled: bool = True
notification_audit_enabled: bool = True
inspector_session_enabled: bool = True   # R14
# Lifecycle
auto_task_checklist_mode: str = "auto"   # R5
cleanup_tasks_enabled: bool = True
# Notifications
auto_task_notify_sound: bool = False     # R6
scan_notify_sound: bool = False          # R6
```
**۹-E. بازطراحی Layout — ۴ tabs (به‌جای ۳):**
| Tab | محتوا |
|---|---|
| **🔍 Coverage** | scan_depth + inventory_layers + criteria preset + auto_models |
| **🧠 Intelligence** | stale + delta + runtime + outcome + logic_audit + smart-prompt + inspector_session |
| **🔁 Lifecycle** | dedup + auto-regenerate + checklist mode + cleanup |
| **🔔 Notifications** | auto_task_sound + scan_sound + notification_audit + custom templates |
**۹-F. AI explanation برای هر گزینه (R8):**
هر گزینه دارای help icon ⓘ + AI-generated description (از فاز ۲):
- این گزینه دقیقاً چه می‌کند
- کِی اضافه شد
- وضعیت فعلی (active / possibly stale / unknown)
**۹-G. Feature Inventory Panel (R8):**
panel جدید در UI با لیست همه options + AI explanation (از فاز ۲).
### Acceptance Criteria فاز ۹
- در UI، ۴ tab وجود دارد
- mode `balanced` پیش‌فرض جدید
- mode `ultra` در دسترس
- backward compat: scan_depth قدیمی همچنان کار کند
- هر گزینه دارای tooltip + AI explanation
- Feature Inventory Panel functional
```

quick (3 pass) | standard (6 pass) | deep (12 pass، پیش‌فرض) | thorough (12 + health + roadmap)
```
به:
```
⚡ quick (5 pass) — frontend + backend + security + delta + stale
⚖️ balanced (8 pass — پیش‌فرض جدید) — quick + dependency + completeness + runtime
🔬 deep (12 pass) — همه + impact analysis
🧠 ultra (12 pass + logic audit + outcome + notification audit + inspector session)
```
**۹-B. بازنگری criteria_weights:**
به‌جای ۶ slider:
- preset selector: "general", "security-first", "tests-first", "feature-completeness", "logic-quality"
- sliders در `<details>` (advanced)
**۹-C. بازنگری Smart Task Lifecycle:**
- بررسی هر گزینه: کار می‌کند؟
- label با وضعیت فعلی
**۹-D. گزینه‌های جدید Phase 5:**
`WatchedProject` فیلدهای جدید (همه با default sensible):
```python
# Coverage
inventory_layers: List[str] = ["all"]    # یا subset
# Intelligence
stale_detection_enabled: bool = True
delta_analysis_enabled: bool = True
runtime_discovery_enabled: bool = True
outcome_data_enabled: bool = True
logic_audit_enabled: bool = True
notification_audit_enabled: bool = True
inspector_session_enabled: bool = True   # R14
# Lifecycle
auto_task_checklist_mode: str = "auto"   # R5
cleanup_tasks_enabled: bool = True
# Notifications
auto_task_notify_sound: bool = False     # R6
scan_notify_sound: bool = False          # R6
```
**۹-E. بازطراحی Layout — ۴ tabs (به‌جای ۳):**
| Tab | محتوا |
|---|---|
| **🔍 Coverage** | scan_depth + inventory_layers + criteria preset + auto_models |
| **🧠 Intelligence** | stale + delta + runtime + outcome + logic_audit + smart-prompt + inspector_session |
| **🔁 Lifecycle** | dedup + auto-regenerate + checklist mode + cleanup |
| **🔔 Notifications** | auto_task_sound + scan_sound + notification_audit + custom templates |
**۹-F. AI explanation برای هر گزینه (R8):**
هر گزینه دارای help icon ⓘ + AI-generated description (از فاز ۲):
- این گزینه دقیقاً چه می‌کند
- کِی اضافه شد
- وضعیت فعلی (active / possibly stale / unknown)
**۹-G. Feature Inventory Panel (R8):**
panel جدید در UI با لیست همه options + AI explanation (از فاز ۲).
### Acceptance Criteria فاز ۹
- در UI، ۴ tab وجود دارد
- mode `balanced` پیش‌فرض جدید
- mode `ultra` در دسترس
- backward compat: scan_depth قدیمی همچنان کار کند
- هر گزینه دارای tooltip + AI explanation
- Feature Inventory Panel functional

--- کلیدواژه‌ها ---
scan_depth, criteria_weights, WatchedProject, inventory_layers, stale_detection_enabled, delta_analysis_enabled, runtime_discovery_enabled, outcome_data_enabled, logic_audit_enabled, notification_audit_enabled, inspector_session_enabled, auto_task_checklist_mode, cleanup_tasks_enabled, auto_task_notify_sound, scan_notify_sound, Feature Inventory Panel, AI explanation, frontend/src/app/oversight/page.tsx
```

## 🎯 هدف (خلاصه ساختاریافته)
بازطراحی کامل UI Oversight با ۴ تب و AI explanation

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `frontend/src/app/oversight/page.tsx:1-50` — `OversightPage` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. کامپوننت اصلی UI Oversight که باید با ۴ تب بازطراحی شود.
  ```tsx
  // فایل deep-read نشده — بر اساس ساختار سطحی پروژه frontend/src/app/oversight/page.tsx
  ```
- `backend/app/services/oversight_service.py:1-30` — `WatchedProject` — این فایل deep-read نشده — مجری باید مسیر را خود تأیید کند. مدل WatchedProject باید فیلدهای جدید Phase 5 را دریافت کند.
  ```python
  // فایل deep-read نشده — بر اساس ساختار سطحی پروژه backend/app/services/oversight_service.py
  ```
- `backend/app/services/oversight_settings.py:1-20`

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز ۹ — UI Redesign (R2, R8): بازطراحی کامل UI Oversight با ۴ تب (Coverage, Intelligence, Lifecycle, Notifications) به‌جای ۳ تب قبلی. تغییرات شامل: بازنگری scan_depth modes (اضافه شدن mode‌های balanced و ultra)، بازنگری criteria_weights (preset selector + sliders در details)، بازنگری Smart Task Lifecycle با وضعیت‌سنجی هر گزینه، اضافه شدن فیلدهای جدید WatchedProject (شامل inventory_layers, stale_detection_enabled, delta_analysis_enabled, runtime_discovery_enabled, outcome_data_enabled, logic_audit_enabled, notification_audit_enabled, inspector_session_enabled, auto_task_checklist_mode, cleanup_tasks_enabled, auto_task_notify_sound, scan_notify_sound)، AI explanation برای هر گزینه با help icon و Feature Inventory Panel. backward compatibility برای scan_depth قدیمی باید حفظ شود. بر اساس کد واقعی پروژه، فایل‌های مرتبط شامل frontend/src/app/oversight/page.tsx (UI اصلی)، backend/app/services/oversight_service.py (مدل WatchedProject و منطق scan_depth)، backend/app/services/oversight_settings.py (criteria_weights و تنظیمات)، backend/app/services/scan_v5/scan_bundle.py (پیاده‌سازی scan_depth modes)، و backend/app/services/oversight_telegram_compose.py (گزارش‌دهی) هستند. در deep context فایل‌های backend/app/api/routes/oversight.py و backend/app/services/oversight_service.py موجود است که باید برای تغییرات backend استفاده شوند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در frontend/src/app/oversight/page.tsx: بازطراحی کامپوننت اصلی با ۴ تب (Coverage, Intelligence, Lifecycle, Notifications) با استفاده از state مدیریت تب و کامپوننت‌های مجزا برای هر تب. 2. در backend/app/services/oversight_service.py: افزودن فیلدهای جدید به مدل WatchedProject شامل inventory_layers, stale_detection_enabled, delta_analysis_enabled, runtime_discovery_enabled, outcome_data_enabled, logic_audit_enabled, notification_audit_enabled, inspector_session_enabled, auto_task_checklist_mode, cleanup_tasks_enabled, auto_task_notify_sound, scan_notify_sound با مقادیر پیش‌فرض sensible. 3. در backend/app/services/oversight_settings.py: بازنگری criteria_weights با preset selector (general, security-first, tests-first, feature-completeness, logic-quality) و sliders در <details>. 4. در backend/app/services/scan_v5/scan_bundle.py: بازنگری scan_depth modes به quick (5 pass), balanced (8 pass, پیش‌فرض جدید), deep (12 pass), ultra (12 pass + logic audit + outcome + notification audit + inspector session). 5. در frontend/src/app/oversight/page.tsx: افزودن AI explanation برای هر گزینه با help icon ⓘ و Feature Inventory Panel. 6. حفظ backward compatibility برای scan_depth قدیمی (quick, standard, deep, thorough) با mapping به modes جدید.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: large

---

# 🔹 مرحله 39: فاز ۱۰: Meta-validation — تبدیل پرامپت به task قابل verify و شناسایی باگ‌های verify

**Scope:** این فاز شامل تبدیل کل پرامپت (فازهای ۱-۹) به یک task اجرایی با ACهای measurable، ایجاد حلقه iteration بین پیاده‌سازی و verify، و شناسایی باگ‌های verify (false-positive/negative) است. خروجی نهایی یک پرامپت با ۱۰ task_step است که هر step دارای behavior_observable و verification_hint است. خارج از scope: پیاده‌سازی واقعی فازهای ۱-۹، تغییر در کدهای موجود، یا ایجاد فایل‌های جدید غیر از فایل log.
**Key terms:** phase5_meta_validation.md, verify Phase 4, behavior_observable, verification_hint, false-positive, false-negative, iteration loop, AC measurable

**بخش مربوط از متن کاربر:**
```
## 🅹 فاز ۱۰ — Meta-validation
> خود این پرامپت قابل verify باشد
### مسئله
کاربر می‌خواهد این پرامپت به task تبدیل شود و توسط verify Phase 4 سنجیده شود.
### تغییرات
**۱۰-A. این پرامپت به task تبدیل:**
- ایده‌ی خام = این متن
- AC ها = AC های هر فاز ۱-۹
- task_steps = ۱۰ فاز
**۱۰-B. AC قابل-verify دقیق:**
هر AC در هر فاز measurable نوشته شده (مثلاً «≥ ۵ stale item کشف شود»).
**۱۰-C. Iteration loop:**
- پیاده‌سازی → verify deep (Phase 4) → نتیجه
- اگر `done < 100%` → iteration بعدی
- اگر `done = 100%` → فاز بعدی
- log در `phase5_meta_validation.md`
**۱۰-D. شناسایی verify bugs:**
- اگر کار واقعاً انجام شد ولی verify گفت not_done → باگ verify
- اگر کار نشد ولی verify گفت done → باگ verify (مهم‌تر، false-positive)
- log همه‌ی این موارد
### Acceptance Criteria فاز ۱۰
- پرامپت نهایی شامل ۱۰ task_step
- هر step دارای `behavior_observable` + `verification_hint`
- بعد از پیاده‌سازی همه فازها، verify deep این task را ≥ ۱۰/۱۰ done گزارش دهد
- log باگ‌های verify identified
```

## 🎯 هدف (خلاصه ساختاریافته)
تبدیل پرامپت فاز ۱۰ به task قابل verify با iteration loop

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز ۱۰: Meta-validation — تبدیل پرامپت به task قابل verify و شناسایی باگ‌های verify. این فاز شامل تبدیل کل پرامپت (فازهای ۱-۹) به یک task اجرایی با ACهای measurable، ایجاد حلقه iteration بین پیاده‌سازی و verify، و شناسایی باگ‌های verify (false-positive/negative) است. خروجی نهایی یک پرامپت با ۱۰ task_step است که هر step دارای behavior_observable و verification_hint است. خارج از scope: پیاده‌سازی واقعی فازهای ۱-۹، تغییر در کدهای موجود، یا ایجاد فایل‌های جدید غیر از فایل log.

بخش مربوط از درخواست اصلی کاربر:
## 🅹 فاز ۱۰ — Meta-validation
> خود این پرامپت قابل verify باشد
### مسئله
کاربر می‌خواهد این پرامپت به task تبدیل شود و توسط verify Phase 4 سنجیده شود.
### تغییرات
**۱۰-A. این پرامپت به task تبدیل:**
- ایده‌ی خام = این متن
- AC ها = AC های هر فاز ۱-۹
- task_steps = ۱۰ فاز
**۱۰-B. AC قابل-verify دقیق:**
هر AC در هر فاز measurable نوشته شده (مثلاً «≥ ۵ stale item کشف شود»).
**۱۰-C. Iteration loop:**
- پیاده‌سازی → verify deep (Phase 4) → نتیجه
- اگر `done < 100%` → iteration بعدی
- اگر `done = 100%` → فاز بعدی
- log در `phase5_meta_validation.md`
**۱۰-D. شناسایی verify bugs:**
- اگر کار واقعاً انجام شد ولی verify گفت not_done → باگ verify
- اگر کار نشد ولی verify گفت done → باگ verify (مهم‌تر، false-positive)
- log همه‌ی این موارد
### Acceptance Criteria فاز ۱۰
- پرامپت نهایی شامل ۱۰ task_step
- هر step دارای `behavior_observable` + `verification_hint`
- بعد از پیاده‌سازی همه فازها، verify deep این task را ≥ ۱۰/۱۰ done گزارش دهد
- log باگ‌های verify identified

کلیدواژه‌ها: phase5_meta_validation.md, verify Phase 4, behavior_observable, verification_hint, false-positive, false-negative, iteration loop, AC measurable

شواهد در کد واقعی: در فایل‌های deep-read شده مانند backend/app/api/routes/analysis.py (خطوط ۸۳-۲۶۸ مربوط به run_analysis_stream با progress_callback و SSE) و backend/app/services/verify_runtime/iterative_orchestrator.py (که iteration loop را پیاده‌سازی می‌کند) و backend/app/services/oversight_verifier.py (که verify deep را انجام می‌دهد) ساختارهای مشابه iteration و verify وجود دارد. همچنین فایل docs/PHASE_5_META_VALIDATION.md در ساختار پروژه موجود است که باید به‌روزرسانی شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. ایجاد یک task جدید در backend/app/services/scan_v5/scan_bundle.py یا فایل مجزا برای meta-validation که شامل ۱۰ task_step با behavior_observable و verification_hint باشد.
۲. هر task_step باید یک AC measurable داشته باشد (مثلاً '≥ ۵ stale item کشف شود' برای فاز مربوطه).
۳. پیاده‌سازی iteration loop با استفاده از الگوی موجود در backend/app/services/verify_runtime/iterative_orchestrator.py که بعد از هر پیاده‌سازی verify deep (Phase 4) را فراخوانی کند.
۴. اگر done < 100% → iteration بعدی، اگر done = 100% → فاز بعدی.
۵. لاگ‌گیری در docs/PHASE_5_META_VALIDATION.md با شناسایی verify bugs (false-positive/negative).
۶. استفاده از progress_callback مشابه analysis.py خطوط ۱۰۱-۱۰۳ برای گزارش پیشرفت iteration.
۷. اطمینان از اینکه verify deep این task را ≥ ۱۰/۱۰ done گزارش دهد.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 40: فاز ۱ — Comprehensive Inventory + Purpose (Round 1 پایه)

**Scope:** این بخش اولین فاز از Round 1 است و شامل ایجاد یک فهرست جامع از تمام اجزای پروژه (Inventory) به همراه تعریف هدف (Purpose) هر جزء می‌شود. این فاز پایه‌ای برای تمام تحلیل‌های بعدی است و باید تمام فایل‌ها، کلاس‌ها، سرویس‌ها و کامپوننت‌های UI را پوشش دهد. نکته حیاتی: این فاز صرفاً مستندسازی و فهرست‌برداری است و شامل تحلیل ساختاری یا دینامیک نمی‌شود. خروجی این فاز یک گزارش کامل از موجودیت‌ها و اهدافشان است که در گزارش نهایی به صورت ریز و مشروح ذکر خواهد شد.
**Key terms:** backend/app/services/oversight_verifier.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verify_pdf.py, frontend/src/app/oversight/page.tsx, tests/integration/test_runtime_verify.py, backend/app/services/oversight_inspector_bridge.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult

**بخش مربوط از متن کاربر:**
```
## 🎯 ترتیب اجرا
**Round 1 — پایه:**
1. فاز ۱ — Comprehensive Inventory + Purpose
...
در گزارش نهایی باید تمام اجزایی که بررسی کرده به صورت ریز در گزارش بیاد .. حالا بخش تسک درست کردن و پرامپت و چک لیست مطابقش درست کردن که تو گزارش میاد جدا
یه گزارش جدا باید تو همون متنی که ارسال میکنه در تلگرام هم پیوستش باشه که تمام موارد رو که بررسی کرده مشروح و با جزئیات بنویسه 

اینها که زیر نوشتم و در تنظیمات هر کارت پروژه قرارداده شده باید هر کدوم توضیحات مفصلی داشته باشه و هیچ کار ناقصی پذیرفته نیست :

🗑 stale + forgotten options
🔄 delta + bidirectional dep
🌐 runtime discovery
📊 outcome data
🧠 logic audit
🔔 notification audit
🔍 inspector session
🗑 cleanup tasks
-----------------------------
🔒 امنیت:

🛠 کیفیت:

🧪 تست:

✅ کامل بودن:
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد Comprehensive Inventory + Purpose برای Round 1 پایه

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به فاز ۱ از Round 1 پایه است که شامل ایجاد یک فهرست جامع از تمام اجزای پروژه (Comprehensive Inventory) به همراه تعریف هدف (Purpose) هر جزء می‌شود. کاربر درخواست کرده است که این فاز صرفاً مستندسازی و فهرست‌برداری است و شامل تحلیل ساختاری یا دینامیک نمی‌شود. خروجی این فاز یک گزارش کامل از موجودیت‌ها و اهدافشان است که در گزارش نهایی به صورت ریز و مشروح ذکر خواهد شد. کاربر تأکید کرده است که در گزارش نهایی باید تمام اجزایی که بررسی کرده به صورت ریز در گزارش بیاید و یک گزارش جدا باید در همان متنی که ارسال می‌کند در تلگرام هم پیوستش باشد که تمام موارد را که بررسی کرده مشروح و با جزئیات بنویسد. همچنین کاربر لیست مواردی را که در تنظیمات هر کارت پروژه قرار داده شده است مشخص کرده است: stale + forgotten options, delta + bidirectional dep, runtime discovery, outcome data, logic audit, notification audit, inspector session, cleanup tasks. این موارد باید هر کدام توضیحات مفصلی داشته باشند و هیچ کار ناقصی پذیرفته نیست. کلیدواژه‌های مرتبط: backend/app/services/oversight_verifier.py, backend/app/services/oversight_strong_prompt.py, backend/app/services/oversight_service.py, backend/app/services/oversight_verify_pdf.py, frontend/src/app/oversight/page.tsx, tests/integration/test_runtime_verify.py, backend/app/services/oversight_inspector_bridge.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, RuntimeProbeResult, ProbeContext, InspectorSession, VerifyContext, VerifyConfig, ProbeResult. در کد واقعی پروژه، فایل backend/app/services/scan_v5/comprehensive_inventory.py وجود دارد که می‌تواند پایه‌ای برای این فاز باشد. همچنین فایل backend/app/services/scan_v5/purpose_extractor.py برای استخراج Purpose هر جزء موجود است. فایل backend/app/services/scan_v5/scan_bundle.py نیز برای باندل کردن اسکن‌ها استفاده می‌شود. فایل backend/app/services/oversight_service.py شامل کلاس OversightTask است که می‌تواند برای ذخیره نتایج استفاده شود. فایل backend/app/services/oversight_verifier.py شامل منطق verify است که می‌تواند برای اعتبارسنجی خروجی‌ها استفاده شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد یک ماژول جدید به نام backend/app/services/scan_v5/comprehensive_inventory.py که شامل کلاس ComprehensiveInventory با متدهای زیر باشد: scan_all_files() برای اسکن تمام فایل‌های پروژه، extract_classes() برای استخراج کلاس‌ها، extract_services() برای استخراج سرویس‌ها، extract_ui_components() برای استخراج کامپوننت‌های UI. 2. ایجاد یک ماژول جدید به نام backend/app/services/scan_v5/purpose_extractor.py که شامل کلاس PurposeExtractor با متد extract_purpose() باشد که برای هر جزء هدف آن را استخراج کند. 3. ایجاد یک endpoint جدید در backend/app/api/routes/analysis.py با مسیر /api/analysis/comprehensive-inventory که این فاز را اجرا کند. 4. ایجاد یک تابع در backend/app/services/scan_v5/scan_bundle.py به نام run_comprehensive_inventory() که comprehensive_inventory و purpose_extractor را فراخوانی کند. 5. ایجاد یک مدل جدید در backend/app/models/analysis_report.py به نام ComprehensiveInventoryReport که شامل فیلدهای inventory_items, purpose_items, report_text, telegram_attachment باشد. 6. ایجاد یک تابع در backend/app/services/oversight_service.py به نام save_comprehensive_inventory_report() که گزارش را در دیتابیس ذخیره کند. 7. ایجاد یک تابع در backend/app/services/notification_service.py به نام send_comprehensive_inventory_report() که گزارش را از طریق تلگرام ارسال کند. 8. ایجاد یک صفحه جدید در frontend/src/app/analysis/page.tsx که نتایج comprehensive inventory را نمایش دهد.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: feature_request
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 41: رفع ۶ گپ بنیادی + ۲ بهبود اضافه در verify v2 برای کاهش false negative از ۴۰٪ به صفر

**Scope:** این بخش شامل تحلیل و رفع ۶ گپ بنیادی (structural gaps) و ۲ بهبود اضافه در لایه‌های زیرین verify است. پایه ۵ فاز قبلی حفظ می‌شود و فقط لایه‌های زیرین تقویت می‌شوند. این بخش صرفاً تعریف گپ‌ها و بهبودهاست و شامل پیاده‌سازی نمی‌شود. خروجی این بخش یک لیست شماره‌دار با ۸ آیتم (۶ گپ + ۲ بهبود) است که باید verbatim در raw_excerpt قرار گیرد.
**Key terms:** verify v2, false negative, backend, multi-step, structural gaps, ۶ گپ بنیادی, ۲ بهبود اضافه, لایه‌های زیرین, ۵ فاز قبلی

**بخش مربوط از متن کاربر:**
```
## 🔍 ۶ گپ بنیادی + ۲ بهبود اضافه (در v2)

1. **گپ اول**: ...
2. **گپ دوم**: ...
3. **گپ سوم**: ...
4. **گپ چهارم**: ...
5. **گپ پنجم**: ...
6. **گپ ششم**: ...
7. **بهبود اول**: ...
8. **بهبود دوم**: ...
```

## 🎯 هدف (خلاصه ساختاریافته)
رفع ۶ گپ بنیادی + ۲ بهبود اضافه در verify v2 برای کاهش false negative

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک شامل تحلیل و رفع ۶ گپ بنیادی (structural gaps) و ۲ بهبود اضافه در لایه‌های زیرین verify است. پایه ۵ فاز قبلی حفظ می‌شود و فقط لایه‌های زیرین تقویت می‌شوند. این بخش صرفاً تعریف گپ‌ها و بهبودهاست و شامل پیاده‌سازی نمی‌شود. خروجی این بخش یک لیست شماره‌دار با ۸ آیتم (۶ گپ + ۲ بهبود) است که باید verbatim در raw_excerpt قرار گیرد. کلیدواژه‌ها: verify v2, false negative, backend, multi-step, structural gaps, ۶ گپ بنیادی, ۲ بهبود اضافه, لایه‌های زیرین, ۵ فاز قبلی. شواهد در کد: فایل `backend/app/services/oversight_verify_pdf.py` (خطوط 1-701) شامل تابع `build_verify_checklist_message` (خط 81) و `_build_verify_report_html` (خط 204) و `build_verify_report_pdf` (خط 635) است که ساختار فعلی verify را نشان می‌دهد. فایل `backend/app/api/routes/analysis.py` (خطوط 1-576) شامل endpointهای تحلیل است. فایل `backend/app/services/verify_runtime/` شامل probeهای runtime است. گپ‌ها: 1) عدم پوشش multi-step verification در checklist فعلی (خطوط 132-159 فقط یک سطح steps را پشتیبانی می‌کند). 2) عدم ذخیره‌سازی raw_idea در مسیر multi-pass (کامیت 7a9c760 این را fix کرده اما نیاز به audit دارد). 3) عدم auto-refresh task panel برای همه مسیرهای ایجاد/به‌روزرسانی task (کامیت 66c1d3b). 4) عدم audit model settings و حذف dead collaborative/actionable GitHub (کامیت e8a394e). 5) عدم bootstrap memory/training با help card + inline user_notes + seed endpoint (کامیت 3e6896d). 6) عدم auto_synced badge روی field cards (کامیت 061fb56). بهبودها: 7) افزودن runtime probes summary به caption تلگرام (خطوط 178-192). 8) افزودن متن کامل extraction فایل‌های پیوست به PDF (خطوط 307-364).

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. برای رفع ۶ گپ بنیادی و ۲ بهبود اضافه در verify v2، مراحل زیر پیشنهاد می‌شود:
1. **گپ اول (multi-step verification)**: در `backend/app/services/oversight_verify_pdf.py`، تابع `build_verify_checklist_message` (خط 81) و `_build_verify_report_html` (خط 204) را اصلاح کن تا از ساختار سلسله‌مراتبی steps (sub-steps) پشتیبانی کند. یک فیلد `sub_steps` به هر step اضافه کن و در حلقه‌های نمایش (خطوط 145-159 و 252-282) به صورت بازگشتی پردازش کن.
2. **گپ دوم (raw_idea preservation)**: در `backend/app/services/oversight_verify_pdf.py`، خط 223 (`raw_idea = getattr(task, "raw_idea", "") or ""`) و خط 305 (`raw_idea_html`) را بررسی کن که raw_idea در همه مسیرهای multi-pass ذخیره شود. فایل `backend/app/services/oversight_service.py` را audit کن.
3. **گپ سوم (auto-refresh task panel)**: در `backend/app/api/routes/oversight.py` و `backend/app/services/oversight_service.py`، یک مکانیزم auto-refresh با WebSocket یا polling اضافه کن تا task panel برای همه مسیرهای ایجاد/به‌روزرسانی task به‌روز شود.
4. **گپ چهارم (model settings audit)**: در `backend/app/api/routes/models.py` و `backend/app/services/model_profiler.py`، model settings را audit کن و dead collaborative/actionable GitHub را حذف کن.
5. **گپ پنجم (bootstrap memory/training)**: در `backend/app

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 42: ساخت ماژول context_builder برای جمع‌آوری و ساخت VerifyContext در فرآیند verify

**Scope:** این بخش ایجاد یک ماژول جدید به نام backend/app/services/verify_runtime/context_builder.py را مشخص می‌کند که شامل یک dataclass به نام VerifyContext و یک تابع async به نام build_verify_context است. scope شامل: تعریف کامل فیلدهای VerifyContext با caps مشخص، پیاده‌سازی تابع build_verify_context که caps را اعمال می‌کند، fetch یک‌باره repo_tree از GitHub با cache روی sha، و فراخوانی این تابع در ابتدای verify_task() به طوری که context در همه probes پاس داده شود. خارج از scope: پیاده‌سازی خود probes، logic مربوط به VerifyConfig (فقط اشاره شده)، و جزئیات caching فراتر از repo_tree.
**Key terms:** backend/app/services/verify_runtime/context_builder.py, VerifyContext, build_verify_context, OversightTask, WatchedProject, VerifyConfig, verify_task(), repo_tree, file_content_cache, file_grep_cache

**بخش مربوط از متن کاربر:**
```
### گپ ۱ — حافظهٔ تکه‌تکه vs کامل

#### وضعیت فعلی
verify فقط AC text + commit diff + screenshot + repo tree را دارد.

#### راه‌حل
ماژول جدید: `backend/app/services/verify_runtime/context_builder.py`

ساختار `VerifyContext` dataclass:
```python
@dataclass
class VerifyContext:
    task: OversightTask                       # ref فقط
    watched: WatchedProject                   # ref فقط
    raw_idea_full: str                        # cap 50KB
    prompt_full: str                          # cap 100KB
    task_steps_full: List[Dict]               # همه (no cap چون داخل تسک)
    prompt_history: List[Dict]                # آخرین ۳ نسخه
    verify_history: List[Dict]                # آخرین ۵ گزارش
    consolidation_meta: Optional[Dict]        # اگر super-task
    merged_source_tasks: List[Dict]           # cap 30 (top by priority)
    scan_metadata: Optional[Dict]             # last_scan_metadata
    repo_tree: List[str]                      # paths only، cap 5000
    commits_recent: List[Dict]                # cap 50 commits
    # کش‌های in-memory per-verify-run
    file_content_cache: Dict[str, str] = field(default_factory=dict)
    file_grep_cache: Dict[Tuple[str, str], List[Dict]] = field(default_factory=dict)
    # observability
    trace: List[Dict] = field(default_factory=list)  # هر تصمیم append می‌شود
    config: "VerifyConfig" = ...               # ↓ بخش config
    files_fetched_count: int = 0
    grep_calls_count: int = 0
    ai_calls_count: int = 0
```

تابع `async def build_verify_context(task, watched, *, config) -> VerifyContext`:
- caps را اعمال می‌کند
- repo_tree یک‌بار از GitHub fetch می‌شود (با cache روی sha)
- در ابتدای `verify_task()` صدا زده می‌شود و در همهٔ probes پاس داده می‌شود
```

python
@dataclass
class VerifyContext:
    task: OversightTask                       # ref فقط
    watched: WatchedProject                   # ref فقط
    raw_idea_full: str                        # cap 50KB
    prompt_full: str                          # cap 100KB
    task_steps_full: List[Dict]               # همه (no cap چون داخل تسک)
    prompt_history: List[Dict]                # آخرین ۳ نسخه
    verify_history: List[Dict]                # آخرین ۵ گزارش
    consolidation_meta: Optional[Dict]        # اگر super-task
    merged_source_tasks: List[Dict]           # cap 30 (top by priority)
    scan_metadata: Optional[Dict]             # last_scan_metadata
    repo_tree: List[str]                      # paths only، cap 5000
    commits_recent: List[Dict]                # cap 50 commits
    # کش‌های in-memory per-verify-run
    file_content_cache: Dict[str, str] = field(default_factory=dict)
    file_grep_cache: Dict[Tuple[str, str], List[Dict]] = field(default_factory=dict)
    # observability
    trace: List[Dict] = field(default_factory=list)  # هر تصمیم append می‌شود
    config: "VerifyConfig" = ...               # ↓ بخش config
    files_fetched_count: int = 0
    grep_calls_count: int = 0
    ai_calls_count: int = 0
```

تابع `async def build_verify_context(task, watched, *, config) -> VerifyContext`:
- caps را اعمال می‌کند
- repo_tree یک‌بار از GitHub fetch می‌شود (با cache روی sha)
- در ابتدای `verify_task()` صدا زده می‌شود و در همهٔ probes پاس داده می‌شود

--- کلیدواژه‌ها ---
backend/app/services/verify_runtime/context_builder.py, VerifyContext, build_verify_context, OversightTask, WatchedProject, VerifyConfig, verify_task(), repo_tree, file_content_cache, file_grep_cache
```

## 🎯 هدف (خلاصه ساختاریافته)
ساخت ماژول context_builder برای جمع‌آوری و ساخت VerifyContext در فرآیند verify

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/context_builder.py:137-178` — `VerifyContext`
  ```python
  @dataclass
  class VerifyContext:
      task: Any                                  # OversightTask — ref فقط
      watched: Optional[Any]                     # WatchedProject — ref فقط
      raw_idea_full: str = ""                    # cap 50KB
      prompt_full: str = ""                      # cap 100KB
      task_steps_full: List[
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک مربوط به ایجاد یک ماژول جدید به نام backend/app/services/verify_runtime/context_builder.py است که شامل یک dataclass به نام VerifyContext و یک تابع async به نام build_verify_context می‌باشد. scope شامل: تعریف کامل فیلدهای VerifyContext با caps مشخص (raw_idea_full با cap 50KB، prompt_full با cap 100KB، task_steps_full بدون cap، prompt_history آخرین ۳ نسخه، verify_history آخرین ۵ گزارش، consolidation_meta برای super-task، merged_source_tasks با cap 30 و مرتب‌سازی بر اساس priority، scan_metadata، repo_tree با cap 5000، commits_recent با cap 50)، پیاده‌سازی تابع build_verify_context که caps را اعمال می‌کند، fetch یک‌باره repo_tree از GitHub با cache روی sha (با استفاده از _REPO_TREE_CACHE و کلید f"{repo_full_name}@{sha}")، و فراخوانی این تابع در ابتدای verify_task() به طوری که context در همه probes پاس داده شود. خارج از scope: پیاده‌سازی خود probes، logic مربوط به VerifyConfig (فقط اشاره شده)، و جزئیات caching فراتر از repo_tree. بر اساس کد واقعی در فایل backend/app/services/verify_runtime/context_builder.py (خطوط 1-372)، این ماژول قبلاً پیاده‌سازی شده است و شامل VerifyConfig (خطوط 27-129)، VerifyContext (خطوط 137-178)، و build_verify_context (خطوط 198-278) می‌باشد. همچنین تابع _fetch_repo_tree_and_commits (خطوط 286-369) برای fetch repo_tree و commits از GitHub با cache روی sha پیاده‌سازی شده است. کلیدواژه‌های کاربر: backend/app/services/verify_runtime/context_builder.py, VerifyContext, build_verify_context, OversightTask, WatchedProject, VerifyConfig, verify_task(), repo_tree, file_content_cache, file_grep_cache.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. با توجه به اینکه فایل backend/app/services/verify_runtime/context_builder.py قبلاً پیاده‌سازی شده است، این تسک به صورت عملی نیازمند موارد زیر است: 1) بررسی کامل کد موجود در context_builder.py (خطوط 1-372) و اطمینان از تطابق با مشخصات کاربر (VerifyContext با فیلدهای raw_idea_full, prompt_full, task_steps_full, prompt_history, verify_history, consolidation_meta, merged_source_tasks, scan_metadata, repo_tree, commits_recent, file_content_cache, file_grep_cache, trace, config, files_fetched_count, grep_calls_count, ai_calls_count). 2) اطمینان از اینکه build_verify_context در ابتدای verify_task() در فایل backend/app/services/verify_runtime/runner.py یا oversight_service.py فراخوانی می‌شود و context در همه probes پاس داده می‌شود. 3) بررسی اینکه caps (50KB برای raw_idea_full، 100KB برای prompt_full، 30 برای merged_source_tasks، 5000 برای repo_tree، 50 برای commits_recent) به درستی در خطوط 185-191 و 212-248 اعمال شده‌اند. 4) اطمینان از اینکه _REPO_TREE_CACHE (خط 195) به درستی با کلید f"{repo_full_name}@{sha}" کار می‌کند و cache بین verify runها به اشتراک گذاشته می‌شود. 5) اضافه کردن تست‌های واحد برای build_verify_context در فایل tests/test_runtime_verify_stage1.py یا مشابه.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 43: پیاده‌سازی ماژول code_content_searcher برای جستجوی محتوای فایل به جای commit diff

**Scope:** این بخش شامل ایجاد ماژول جدید backend/app/services/verify_runtime/code_content_searcher.py با سه تابع async و یک تابع همزمان است. توابع fetch_file_content (دریافت محتوای فایل از GitHub API با cache و محدودیت حجم)، grep_token_in_files (جستجوی regex در محتوای فایل‌ها با context lines و cap per file)، smart_grep_for_ac (استخراج identifier از متن AC و جستجوی همه آن‌ها در target_files) و extract_identifiers (استخراج identifier با regexهای دقیق و specificity scoring) پیاده‌سازی می‌شوند. مثال‌های concrete برای extract_identifiers (4 مثال) و regexهای دقیق برای snake_case, dunder, camelCase, PascalCase, function_call, file_path و stop-words ~100 تایی و specificity score برای top-K=15 identifier نیز بخشی از این scope هستند.
**Key terms:** backend/app/services/verify_runtime/code_content_searcher.py, fetch_file_content, grep_token_in_files, smart_grep_for_ac, extract_identifiers, VerifyContext, GitHub API /repos/{owner}/{repo}/contents/{path}, snake_case regex, dunder regex, camelCase regex, PascalCase regex, function_call regex, file_path regex, specificity score, top-K=15

**بخش مربوط از متن کاربر:**
```
ماژول جدید: `backend/app/services/verify_runtime/code_content_searcher.py`

API عمومی:

```python
async def fetch_file_content(
    repo_full_name: str, path: str, ref: str = "main",
    *, token: str,
    cache: Dict[str, str],
    max_size_bytes: int = 500_000,
) -> Optional[str]
```
- GET `/repos/{owner}/{repo}/contents/{path}?ref={ref}`
- base64 decode از field `content`
- cache روی key=f"{path}@{ref}"
- skip اگر size > 500KB یا content-type غیر متنی
- بازگشت None در صورت 404/403/error
- log در `context.trace`

```python
async def grep_token_in_files(
    token: str, paths: List[str],
    repo_full_name: str, ref: str,
    *, github_token: str,
    cache: Dict[Tuple[str, str], List[Dict]],
    file_content_cache: Dict[str, str],
    context_lines: int = 2,
    max_matches_per_file: int = 5,
) -> List[Dict]
```
- regex `re.finditer(re.escape(token), content, re.IGNORECASE)`
- خروجی: `[{path, line_number, snippet, before_lines, after_lines}, ...]`
- cap per file
- cache روی key=(path, token)

```python
async def smart_grep_for_ac(
    ac_text: str, target_files: List[str],
    repo_full_name: str, ref: str,
    *, context: VerifyContext,
) -> Dict[str, List[Dict]]
```
- `identifiers = extract_identifiers(ac_text)`
- top-K=15 identifiers (sorted by specificity)
- برای هر identifier در همهٔ target_files
- خروجی: `{identifier: [match, ...]}`

```python
def extract_identifiers(text: str) -> List[str]
```

**🆕 (v2 — کاستی ۱) مثال concrete:**

```python
# مثال ۱: ورودی فارسی + identifier پایتون
text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
extract_identifiers(text) →
    ['view_preferences', 'WatchedProject']

# مثال ۲: ورودی انگلیسی + camelCase
text = "Add useViewPrefs hook for fetching preferences"
extract_identifiers(text) →
    ['useViewPrefs', 'fetching', 'preferences']  # 'Add' حذف چون stop-word

# مثال ۳: ورودی mixed با file path
text = "تابع _record_title_change در oversight_service.py"
extract_identifiers(text) →
    ['_record_title_change', 'oversight_service']

# مثال ۴: کلمات generic - باید filter شوند
text = "بهبود سیستم نمایش"
extract_identifiers(text) →
    []  # هیچ identifier specific نیست → fallback به AI
```

regex‌های دقیق:
- `snake_case`: `r"\b[a-z][a-z0-9_]{2,}\b"` (با حداقل یک underscore یا طول ≥۴)
- `dunder`: `r"\b_[a-z][a-z0-9_]+\b"`
- `camelCase`: `r"\b[a-z][a-zA-Z0-9]{3,}\b"` که حداقل یک حرف بزرگ داشته باشد بعد از index 0
- `PascalCase`: `r"\b[A-Z][a-zA-Z0-9]{3,}\b"`
- `function_call`: `r"\b(\w+)\s*\("`
- `file_path`: `r"\b[\w/.-]+\.(py|tsx?|jsx?|json|yaml|md)\b"`

stop-words (cap ~۱۰۰): فارسی + انگلیسی common words (`the, and, for, this, that, user, system, change, ...` / `بهبود, تغییر, سیستم, پروژه, ...`)

specificity score برای sort:
- length × ۱.۰
- snake_case bonus: +۲
- dunder bonus: +۳ (خیلی specific)
- file_path bonus: +۴ (خیلی specific)

خروجی: top-K=15 unique identifiers، sorted desc by specificity
```

python
async def fetch_file_content(
    repo_full_name: str, path: str, ref: str = "main",
    *, token: str,
    cache: Dict[str, str],
    max_size_bytes: int = 500_000,
) -> Optional[str]
```
- GET `/repos/{owner}/{repo}/contents/{path}?ref={ref}`
- base64 decode از field `content`
- cache روی key=f"{path}@{ref}"
- skip اگر size > 500KB یا content-type غیر متنی
- بازگشت None در صورت 404/403/error
- log در `context.trace`

```python
async def grep_token_in_files(
    token: str, paths: List[str],
    repo_full_name: str, ref: str,
    *, github_token: str,
    cache: Dict[Tuple[str, str], List[Dict]],
    file_content_cache: Dict[str, str],
    context_lines: int = 2,
    max_matches_per_file: int = 5,
) -> List[Dict]
```
- regex `re.finditer(re.escape(token), content, re.IGNORECASE)`
- خروجی: `[{path, line_number, snippet, before_lines, after_lines}, ...]`
- cap per file
- cache روی key=(path, token)

```python
async def smart_grep_for_ac(
    ac_text: str, target_files: List[str],
    repo_full_name: str, ref: str,
    *, context: VerifyContext,
) -> Dict[str, List[Dict]]
```
- `identifiers = extract_identifiers(ac_text)`
- top-K=15 identifiers (sorted by specificity)
- برای هر identifier در همهٔ target_files
- خروجی: `{identifier: [match, ...]}`

```python
def extract_identifiers(text: str) -> List[str]
```

**🆕 (v2 — کاستی ۱) مثال concrete:**

```python
# مثال ۱: ورودی فارسی + identifier پایتون
text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
extract_identifiers(text) →
    ['view_preferences', 'WatchedProject']

# مثال ۲: ورودی انگلیسی + camelCase
text = "Add useViewPrefs hook for fetching preferences"
extract_identifiers(text) →
    ['useViewPrefs', 'fetching', 'preferences']  # 'Add' حذف چون stop-word

# مثال ۳: ورودی mixed با file path
text = "تابع _record_title_change در oversight_service.py"
extract_identifiers(text) →
    ['_record_title_change', 'oversight_service']

# مثال ۴: کلمات generic - باید filter شوند
text = "بهبود سیستم نمایش"
extract_identifiers(text) →
    []  # هیچ identifier specific نیست → fallback به AI
```

regex‌های دقیق:
- `snake_case`: `r"\b[a-z][a-z0-9_]{2,}\b"` (با حداقل یک underscore یا طول ≥۴)
- `dunder`: `r"\b_[a-z][a-z0-9_]+\b"`
- `camelCase`: `r"\b[a-z][a-zA-Z0-9]{3,}\b"` که حداقل یک حرف بزرگ داشته باشد بعد از index 0
- `PascalCase`: `r"\b[A-Z][a-zA-Z0-9]{3,}\b"`
- `function_call`: `r"\b(\w+)\s*\("`
- `file_path`: `r"\b[\w/.-]+\.(py|tsx?|jsx?|json|yaml|md)\b"`

stop-words (cap ~۱۰۰): فارسی + انگلیسی common words (`the, and, for, this, that, user, system, change, ...` / `بهبود, تغییر, سیستم, پروژه, ...`)

specificity score برای sort:
- length × ۱.۰
- snake_case bonus: +۲
- dunder bonus: +۳ (خیلی specific)
- file_path bonus: +۴ (خیلی specific)

خروجی: top-K=15 unique identifiers، sorted desc by specificity

--- کلیدواژه‌ها ---
backend/app/services/verify_runtime/code_content_searcher.py, fetch_file_content, grep_token_in_files, smart_grep_for_ac, extract_identifiers, VerifyContext, GitHub API /repos/{owner}/{repo}/contents/{path}, snake_case regex, dunder regex, camelCase regex, PascalCase regex, function_call regex, file_path regex, specificity score, top-K=15
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد ماژول code_content_searcher برای جستجوی محتوای فایل به جای commit diff

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی ماژول جدید `backend/app/services/verify_runtime/code_content_searcher.py` برای جستجوی محتوای فایل در مخزن GitHub به‌جای تکیه به commit diff (که فقط آخرین تغییرات را می‌دهد). این ماژول شامل چهار تابع است: (۱) `fetch_file_content` — دریافت محتوای فایل از GitHub Contents API با GET `/repos/{owner}/{repo}/contents/{path}?ref={ref}`، base64 decode از field `content`، cache روی key=f"{path}@{ref}"، skip اگر size > 500KB یا content-type غیر متنی، بازگشت None در صورت 404/403/error. (۲) `grep_token_in_files` — جستجوی case-insensitive یک token در لیست فایل‌ها با regex `re.finditer(re.escape(token), content, re.IGNORECASE)`، خروجی: `[{path, line_number, snippet, before_lines, after_lines}, ...]`، cap per file (max_matches_per_file=5)، cache روی key=(path, token). (۳) `smart_grep_for_ac` — استخراج identifier از متن AC با `extract_identifiers`، top-K=15 identifiers (sorted by specificity)، برای هر identifier در همهٔ target_files، خروجی: `{identifier: [match, ...]}`. (۴) `extract_identifiers` — استخراج identifier با regexهای دقیق: snake_case (`r"\b[a-z][a-z0-9_]{2,}\b"` با حداقل یک underscore یا طول ≥۴)، dunder (`r"\b_[a-z][a-z0-9_]+\b"`)، camelCase (`r"\b[a-z][a-zA-Z0-9]{3,}\b"` با حداقل یک حرف بزرگ بعد از index 0)، PascalCase (`r"\b[A-Z][a-zA-Z0-9]{3,}\b"`)، function_call (`r"\b(\w+)\s*\("`)، file_path (`r"\b[\w/.\-]+\.(py|tsx?|jsx?|json|yaml|md)\b"`). stop-words ~۱۰۰ تایی (فارسی + انگلیسی common words مانند `the, and, for, this, that, user, system, change, بهبود, تغییر, سیستم, پروژه`). specificity score: length × ۱.۰ + snake_case bonus +۲ + dunder bonus +۳ + file_path bonus +۴. خروجی: top-K=15 unique identifiers sorted desc by specificity. مثال‌های concrete: (۱) `text = "اضافه کردن فیلد view_preferences به مدل WatchedProject"` → `['view_preferences', 'WatchedProject']`. (۲) `text = "Add useViewPrefs hook for fetching preferences"` → `['useViewPrefs', 'fetching', 'preferences']` ('Add' حذف چون stop-word). (۳) `text = "تابع _record_title_change در oversight_service.py"` → `['_record_title_change', 'oversight_service']`. (۴) `text = "بهبود سیستم نمایش"` → `[]` (هیچ identifier specific نیست → fallback به AI). این ماژول طبق Bug C6 v2 — گپ ۲ (file content reading به‌جای commit diff) طراحی شده است. فایل فعلی در `backend/app/services/verify_runtime/code_content_searcher.py` از خط ۱ تا ۳۷۹ موجود است و شامل تمام توابع فوق می‌باشد. توابع `fetch_file_content` (خطوط ۲۸-۹۵)، `grep_token_in_files` (خطوط ۱۰۳-۱۵۶)، `smart_grep_for_ac` (خطوط ۳۲۷-۳۷۱) و `extract_identifiers` (خطوط ۱۹۷-۳۰۶) پیاده‌سازی شده‌اند. همچنین `_add_candidate` (خطوط ۳۰۹-۳۱۲) و `_has_underscore_or_long` (خطوط ۳۱۵-۳۱۹) به‌عنوان helper functions وجود دارند. ماژول از `httpx` برای درخواست‌های HTTP و `re` برای regex استفاده می‌کند. توکن GitHub از `backend/app/services/github_storage

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 44: AC matching با file content به‌جای basename — چهار فاز اجرایی

**Scope:** این بخش یک orchestrator جدید به نام analyze_acs_with_content_grep تعریف می‌کند که چهار فاز (A→B→C→D) را به‌ترتیب اجرا می‌کند. هر فاز یک تابع async مجزا دارد و در صورت بازگشت done قطعی، early-exit رخ می‌دهد. منطق فازها تغییر نمی‌کند، فقط نام‌گذاری مشخص‌تر می‌شود. فاز A (basename match) و فاز B (content grep) روی target_files کار می‌کنند، فاز C (extended repo grep) و فاز D (AI judgment) فقط context می‌گیرند. خروجی هر فاز از نوع ProbeResult است.
**Key terms:** analyze_acs_with_content_grep, _phase_a_basename_match, _phase_b_content_grep, _phase_c_extended_repo_grep, _phase_d_ai_judgment, ProbeResult, target_files, context

**بخش مربوط از متن کاربر:**
```
### گپ ۳ — AC matching: file content به‌جای basename

(۴ مرحلهٔ A→B→C→D، بدون تغییر منطقی — فقط نام‌گذاری مشخص‌تر)

تابع‌های جدا برای traceability:
```python
async def _phase_a_basename_match(ac, target_files, context) -> ProbeResult
async def _phase_b_content_grep(ac, target_files, context) -> ProbeResult
async def _phase_c_extended_repo_grep(ac, context) -> ProbeResult
async def _phase_d_ai_judgment(ac, context) -> ProbeResult
```

orchestrator: `analyze_acs_with_content_grep(acs, context)` که چهار phase را به‌ترتیب می‌چرخاند، هر phase که done قطعی داد، early-exit.
```

python
async def _phase_a_basename_match(ac, target_files, context) -> ProbeResult
async def _phase_b_content_grep(ac, target_files, context) -> ProbeResult
async def _phase_c_extended_repo_grep(ac, context) -> ProbeResult
async def _phase_d_ai_judgment(ac, context) -> ProbeResult
```

orchestrator: `analyze_acs_with_content_grep(acs, context)` که چهار phase را به‌ترتیب می‌چرخاند، هر phase که done قطعی داد، early-exit.

--- کلیدواژه‌ها ---
analyze_acs_with_content_grep, _phase_a_basename_match, _phase_b_content_grep, _phase_c_extended_repo_grep, _phase_d_ai_judgment, ProbeResult, target_files, context
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی analyze_acs_with_content_grep با چهار فاز A→B→C→D

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/iterative_orchestrator.py:1-50` — `IterativeOrchestrator` — این فایل الگوی اصلی orchestrator را دارد که analyze_acs_with_content_grep باید از آن پیروی کند
  ```python
  class IterativeOrchestrator:
      """Orchestrator for iterative verification of ACs"""
      def __init__(self, ...):
  ```
- `backend/app/services/verify_runtime/code_content_searcher.py:1-30` — `CodeContentSearcher` — این فایل منطق content grep را دارد که در فاز B استفاده خواهد شد
  ```python
  class CodeContentSearcher:
      """Searches code content for patterns"""
      def __init__(self, ...):
  ```
- `backend/app/services/verify_runtime/ac_schema.py:1-20` — `ProbeResult` — نوع ProbeResult که خروجی هر فاز باید از این نوع باشد
  ```python
  class ProbeResult:
      """Result of a probe"""
      done: bool
      matched: bool
      ...
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔗 فایل‌های مرتبط (Cross-references)
_(فایل‌هایی که با موقعیت‌های هدف در ارتباط هستند — import، caller، shared state)_

- `backend/app/services/verify_runtime/context_builder.py` (سطر 1) — این فایل context مورد نیاز برای فازهای C و D را فراهم می‌کند
- `backend/app/services/verify_runtime/runner.py` (سطر 1) — این فایل orchestrator اصلی را اجرا می‌کند و باید analyze_acs_with_content_grep را فراخوانی کند
- `backend/app/services/verify_runtime/ac_enricher.py` (سطر 1) — این فایل ACها را غنی‌سازی می‌کند و ممکن است نیاز به تطبیق با سیستم جدید داشته باشد

## 🔍 Context و وضعیت فعلی
کاربر درخواست ایجاد یک orchestrator جدید به نام analyze_acs_with_content_grep را دارد که چهار فاز (A→B→C→D) را به‌ترتیب اجرا می‌کند. هر فاز یک تابع async مجزا دارد و در صورت بازگشت done قطعی، early-exit رخ می‌دهد. منطق فازها تغییر نمی‌کند، فقط نام‌گذاری مشخص‌تر می‌شود. فاز A (basename match) و فاز B (content grep) روی target_files کار می‌کنند، فاز C (extended repo grep) و فاز D (AI judgment) فقط context می‌گیرند. خروجی هر فاز از نوع ProbeResult است. کلیدواژه‌های اصلی: analyze_acs_with_content_grep, _phase_a_basename_match, _phase_b_content_grep, _phase_c_extended_repo_grep, _phase_d_ai_judgment, ProbeResult, target_files, context. این درخواست با توجه به ساختار فعلی پروژه در فایل‌های verify_runtime مانند iterative_orchestrator.py و code_content_searcher.py قابل پیاده‌سازی است که در آن‌ها الگوهای مشابهی برای تحلیل فایل‌ها و تطبیق AC وجود دارد.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل جدید backend/app/services/verify_runtime/ac_content_matcher.py شامل کلاس AcContentMatcher با متد analyze_acs_with_content_grep. 2. پیاده‌سازی چهار تابع async: _phase_a_basename_match, _phase_b_content_grep, _phase_c_extended_repo_grep, _phase_d_ai_judgment. 3. استفاده از ProbeResult به عنوان نوع خروجی هر فاز. 4. پیاده‌سازی early-exit در صورت بازگشت done قطعی از هر فاز. 5. اتصال به سیستم موجود در iterative_orchestrator.py و code_content_searcher.py.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 45: پیاده‌سازی ماژول iterative_orchestrator با سه مرحله اعتبارسنجی تدریجی

**Scope:** این بخش شامل پیاده‌سازی ماژول جدید `iterative_orchestrator.py` با سه iteration است: (1) استاندارد با ۴ probe و آستانه 0.8، (2) aggressive content grep با آستانه 0.7، (3) strong model escalation با زنجیره مدل‌های gpt-4o → claude-opus-4-7 → claude-sonnet-4-6 → fallback. خروجی نهایی یک `ProbeResult` aggregated و لیست تمام iteration results است. حداکثر ۳ iteration مجاز است.
**Key terms:** iterative_orchestrator.py, ProbeResult, VerifyContext, iterative_verify_step, _strong_model_judgment, pick_best_extraction_model, MODEL_REGISTRY, gpt-4o, claude-opus-4-7, claude-sonnet-4-6, vision probe, code_aware probe, content_grep probe, playwright probe

**بخش مربوط از متن کاربر:**
```
ماژول جدید: `backend/app/services/verify_runtime/iterative_orchestrator.py`

@dataclass
class ProbeResult:
    probe_name: str
    verdict: str  # "done" | "partial" | "not_done" | "unclear"
    confidence: float  # 0.0..1.0
    evidence: List[str]
    error: Optional[str] = None
    elapsed_ms: int = 0

async def iterative_verify_step(
    step: Dict, context: VerifyContext,
    *, max_iterations: int = 3,
) -> Tuple[ProbeResult, List[ProbeResult]]:
    """
    خروجی: (final_aggregated_result, all_iteration_results)
    """

Iteration 1 — Standard probes (~۵-۱۰s)
- vision probe (فقط اگر classification = frontend/fullstack)
- code_aware probe (basename + diff window)
- content_grep probe (smart_grep_for_ac روی target_files)
- playwright probe (اگر URL probe موجود)
aggregate → verdict + confidence
- اگر confidence ≥ 0.8 → finalize ✅
- اگر confidence < 0.8 → escalate to iteration 2

Iteration 2 — Aggressive content grep (~۱۵-۳۰s)
- file scope توسعه می‌یابد: full repo tree با filter به‌ترتیب:
  1. extensions مرتبط (py/tsx/ts/jsx/js)
  2. paths که با AC text overlap دارند
  3. cap: ۵۰ فایل اضافی
- top-K identifiers (نه فقط top-15، بلکه top-25)
- AI rerun با evidence جدید
- aggregate → verdict + confidence
- اگر confidence ≥ 0.7 → finalize ✅
- اگر < 0.7 → escalate to iteration 3

Iteration 3 — Strong model escalation (~۳۰-۶۰s)
🆕 (v2 — کاستی ۲) Model escalation tier صریح:

async def _strong_model_judgment(ac, context, prior_results):
    strong_pref = ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"]
    model_id = None
    for cand in strong_pref:
        if _model_available(cand):
            model_id = cand
            break
    if not model_id:
        model_id = pick_best_extraction_model()

ورودی به strong model:
- متن کامل AC
- تمام evidence از iteration 1 و 2
- file content snippets (cap 50KB)
- repo_tree subset مرتبط
- task.prompt full (cap 50KB)

خروجی: ProbeResult با verdict + reasoning detailed
finalize بدون escalation بیشتر (max 3).
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی ماژول iterative_orchestrator با سه مرحله اعتبارسنجی تدریجی

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی ماژول جدید `iterative_orchestrator.py` در مسیر `backend/app/services/verify_runtime/iterative_orchestrator.py` با سه iteration اعتبارسنجی تدریجی. این ماژول شامل یک `@dataclass` به نام `ProbeResult` با فیلدهای `probe_name: str`, `verdict: str` (مقادیر مجاز: "done" | "partial" | "not_done" | "unclear"), `confidence: float` (0.0..1.0), `evidence: List[str]`, `error: Optional[str] = None`, `elapsed_ms: int = 0` و یک تابع async به نام `iterative_verify_step` با امضای `async def iterative_verify_step(step: Dict, context: VerifyContext, *, max_iterations: int = 3) -> Tuple[ProbeResult, List[ProbeResult]]` است که خروجی آن `(final_aggregated_result, all_iteration_results)` می‌باشد.

Iteration 1 — Standard probes (~۵-۱۰s): شامل vision probe (فقط اگر classification = frontend/fullstack), code_aware probe (basename + diff window), content_grep probe (smart_grep_for_ac روی target_files), playwright probe (اگر URL probe موجود). aggregate → verdict + confidence. اگر confidence ≥ 0.8 → finalize ✅. اگر confidence < 0.8 → escalate to iteration 2.

Iteration 2 — Aggressive content grep (~۱۵-۳۰s): file scope توسعه می‌یابد: full repo tree با filter به‌ترتیب: 1) extensions مرتبط (py/tsx/ts/jsx/js), 2) paths که با AC text overlap دارند, 3) cap: ۵۰ فایل اضافی. top-K identifiers (نه فقط top-15، بلکه top-25). AI rerun با evidence جدید. aggregate → verdict + confidence. اگر confidence ≥ 0.7 → finalize ✅. اگر < 0.7 → escalate to iteration 3.

Iteration 3 — Strong model escalation (~۳۰-۶۰s) با تابع `_strong_model_judgment(ac, context, prior_results)`: strong_pref = ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"]. model_id = None. for cand in strong_pref: if _model_available(cand): model_id = cand; break. if not model_id: model_id = pick_best_extraction_model(). ورودی به strong model: متن کامل AC, تمام evidence از iteration 1 و 2, file content snippets (cap 50KB), repo_tree subset مرتبط, task.prompt full (cap 50KB). خروجی: ProbeResult با verdict + reasoning detailed. finalize بدون escalation بیشتر (max 3).

کلیدواژه‌ها: iterative_orchestrator.py, ProbeResult, VerifyContext, iterative_verify_step, _strong_model_judgment, pick_best_extraction_model, MODEL_REGISTRY, gpt-4o, claude-opus-4-7, claude-sonnet-4-6, vision probe, code_aware probe, content_grep probe, playwright probe.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. ایجاد فایل جدید `backend/app/services/verify_runtime/iterative_orchestrator.py` با محتوای کامل شامل: تعریف `@dataclass ProbeResult` (خطوط 27-35 در فایل موجود)، دیکشنری `WEIGHTS_BY_PROBE` (خطوط 46-55)، تابع `aggregate_verdicts` (خطوط 69-115)، تابع `_model_available` (خطوط 123-148)، تابع `_strong_model_judgment` (خطوط 156-299)، تابع `iterative_verify_step` (خطوط 307-383)، تابع `_run_iteration_1` (خطوط 391-482)، تابع `_run_iteration_2` (خطوط 485-604).

2. اطمینان از import صحیح: از `backend/app/core/models_registry` برای `MODEL_REGISTRY` و `pick_best_extraction_model`، از `backend/app/services/ai_manager` برای `ai_manager`، از `backend/app/services/verify

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 46: پیاده‌سازی بهبودهای ۷، ۸ و ۹: کش per-AC، حالت رهگیری و متمرکزسازی VerifyConfig

**Scope:** این بخش شامل سه بهبود مجزا اما مرتبط است: (۱) کش وضعیت تأیید برای هر Acceptance Criteria با هش و checksum فایل برای جلوگیری از تأیید مجدد، (۲) حالت رهگیری/مشاهده‌پذیری کامل فرآیند تأیید با ذخیره trace و endpoint جدید، (۳) متمرکزسازی تمام تنظیمات تأیید در یک کلاس VerifyConfig با endpoint REST. هر سه بهبود روی backend پیاده‌سازی می‌شوند و بهبود ۸ نیازمند تغییرات frontend برای نمایش trace است.
**Key terms:** OversightTask.ac_verify_cache, compute_files_checksum, VerificationReport.verify_trace, VerificationReport.ac_probe_details, VerificationReport.verify_version, VerificationReport.config_used, VerifyConfig, WatchedProject.verify_v6_config, GET /api/oversight/tasks/{task_id}/verify-trace, GET/PATCH /api/oversight/watched/{id}/verify-v6-config, enable_ac_cache, force_full_verify, context.trace

**بخش مربوط از متن کاربر:**
```
### 🆕 (v2 — کاستی ۳) **بهبود ۷ — Per-AC state cache**

#### مشکل
هر بار verify اجرا می‌شود، همهٔ AC ها از صفر چک می‌شوند. اگر AC در ۳ run اخیر `done` با confidence > 0.85 بود و فایل‌های مرتبط تغییر نکردند، re-verify لازم نیست.

#### راه‌حل
فیلد جدید روی `OversightTask`:
```python
ac_verify_cache: Dict[str, Any] = field(default_factory=dict)
# ساختار:
# {
#   "<ac_hash>": {
#     "verdict": "done",
#     "confidence": 0.92,
#     "last_verified_at": ISO,
#     "files_checksum": "abc123",
#     "consecutive_done_count": 3,
#     "evidence": ["..."]
#   }
# }
```

منطق:
1. قبل از verify هر AC:
   - hash از متن AC + classification
   - چک cache
   - اگر `consecutive_done_count >= 3 AND files_checksum unchanged AND age < 7 days`:
     - skip probes، از cache استفاده کن
     - log: `"AC X: cached done (skipped 3 probes)"`
2. بعد از verify:
   - اگر verdict = done و confidence > 0.85:
     - `consecutive_done_count += 1`
     - `files_checksum = compute_files_checksum(target_files)`
   - اگر verdict != done:
     - `consecutive_done_count = 0`
     - cache invalidate

`compute_files_checksum`: sha256 از target_files content (یا sha روی commit ref اگر در GitHub).

flag config: `enable_ac_cache: bool = True` (پیش‌فرض True). user می‌تواند با `?force_full_verify=true` بای‌پاس کند.

---

### 🆕 (v2 — کاستی ۴) **بهبود ۸ — Observability/Trace mode**

#### مشکل
کاربر نمی‌تواند بفهمد چرا verify گفته partial. باید بتواند trace کامل را ببیند.

#### راه‌حل

تمام تصمیم‌های verify در `context.trace` log می‌شوند:
```python
context.trace.append({
    "ts": iso,
    "phase": "iteration_2_content_grep",
    "ac_index": 5,
    "ac_text": "اضافه کردن فیلد view_preferences...",
    "decision": "escalate_to_iter_3",
    "reason": "confidence 0.6 < threshold 0.7",
    "evidence": [...],
    "probe_results": [...],
    "elapsed_ms": 1234,
})
```

سپس روی `VerificationReport`:
```python
@dataclass
class VerificationReport:
    ...
    verify_trace: List[Dict] = field(default_factory=list)
    ac_probe_details: List[Dict] = field(default_factory=list)
    verify_version: str = "v6"
    config_used: Dict = field(default_factory=dict)
```

endpoint جدید:
```
GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}
→ trace کامل آخرین (یا specific) verify
```

UI: یک accordion "🔍 Trace" در زیر هر AC در دیتیل تسک — نمایش step-by-step تصمیمات.

---

### 🆕 (v2 — کاستی ۵) **بهبود ۹ — Centralized VerifyConfig**

#### مشکل
هر knob (max_iterations, max_files, model_tier, ...) جدا گفته شده. متمرکز نیست.

#### راه‌حل
ساختار `VerifyConfig`:
```python
@dataclass
class VerifyConfig:
    max_iterations: int = 3
    iter1_confidence_threshold: float = 0.8
    iter2_confidence_threshold: float = 0.7
    enable_content_grep: bool = True
    max_files_per_run: int = 50
    max_file_size_bytes: int = 500_000
    max_identifiers_per_ac: int = 15
    iter2_max_extra_files: int = 50
    iter2_max_identifiers: int = 25
    strong_model_preference: List[str] = field(default_factory=lambda: ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"])
    enable_ac_cache: bool = True
    ac_cache_max_age_days: int = 7
    ac_cache_consecutive_threshold: int = 3
    weights: Dict[str, float] = field(default_factory=lambda: {...})
    enable_trace: bool = True
    trace_max_entries: int = 1000
```

ذخیره در `WatchedProject.verify_v6_config: Optional[Dict] = None` (اگر None، defaults).

endpoint: `GET/PATCH /api/oversight/watched/{id}/verify-v6-config`
```

python
ac_verify_cache: Dict[str, Any] = field(default_factory=dict)
# ساختار:
# {
#   "<ac_hash>": {
#     "verdict": "done",
#     "confidence": 0.92,
#     "last_verified_at": ISO,
#     "files_checksum": "abc123",
#     "consecutive_done_count": 3,
#     "evidence": ["..."]
#   }
# }
```

منطق:
1. قبل از verify هر AC:
   - hash از متن AC + classification
   - چک cache
   - اگر `consecutive_done_count >= 3 AND files_checksum unchanged AND age < 7 days`:
     - skip probes، از cache استفاده کن
     - log: `"AC X: cached done (skipped 3 probes)"`
2. بعد از verify:
   - اگر verdict = done و confidence > 0.85:
     - `consecutive_done_count += 1`
     - `files_checksum = compute_files_checksum(target_files)`
   - اگر verdict != done:
     - `consecutive_done_count = 0`
     - cache invalidate

`compute_files_checksum`: sha256 از target_files content (یا sha روی commit ref اگر در GitHub).

flag config: `enable_ac_cache: bool = True` (پیش‌فرض True). user می‌تواند با `?force_full_verify=true` بای‌پاس کند.

---

### 🆕 (v2 — کاستی ۴) **بهبود ۸ — Observability/Trace mode**

#### مشکل
کاربر نمی‌تواند بفهمد چرا verify گفته partial. باید بتواند trace کامل را ببیند.

#### راه‌حل

تمام تصمیم‌های verify در `context.trace` log می‌شوند:
```python
context.trace.append({
    "ts": iso,
    "phase": "iteration_2_content_grep",
    "ac_index": 5,
    "ac_text": "اضافه کردن فیلد view_preferences...",
    "decision": "escalate_to_iter_3",
    "reason": "confidence 0.6 < threshold 0.7",
    "evidence": [...],
    "probe_results": [...],
    "elapsed_ms": 1234,
})
```

سپس روی `VerificationReport`:
```python
@dataclass
class VerificationReport:
    ...
    verify_trace: List[Dict] = field(default_factory=list)
    ac_probe_details: List[Dict] = field(default_factory=list)
    verify_version: str = "v6"
    config_used: Dict = field(default_factory=dict)
```

endpoint جدید:
```
GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}
→ trace کامل آخرین (یا specific) verify
```

UI: یک accordion "🔍 Trace" در زیر هر AC در دیتیل تسک — نمایش step-by-step تصمیمات.

---

### 🆕 (v2 — کاستی ۵) **بهبود ۹ — Centralized VerifyConfig**

#### مشکل
هر knob (max_iterations, max_files, model_tier, ...) جدا گفته شده. متمرکز نیست.

#### راه‌حل
ساختار `VerifyConfig`:
```python
@dataclass
class VerifyConfig:
    max_iterations: int = 3
    iter1_confidence_threshold: float = 0.8
    iter2_confidence_threshold: float = 0.7
    enable_content_grep: bool = True
    max_files_per_run: int = 50
    max_file_size_bytes: int = 500_000
    max_identifiers_per_ac: int = 15
    iter2_max_extra_files: int = 50
    iter2_max_identifiers: int = 25
    strong_model_preference: List[str] = field(default_factory=lambda: ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"])
    enable_ac_cache: bool = True
    ac_cache_max_age_days: int = 7
    ac_cache_consecutive_threshold: int = 3
    weights: Dict[str, float] = field(default_factory=lambda: {...})
    enable_trace: bool = True
    trace_max_entries: int = 1000
```

ذخیره در `WatchedProject.verify_v6_config: Optional[Dict] = None` (اگر None، defaults).

endpoint: `GET/PATCH /api/oversight/watched/{id}/verify-v6-config`

--- کلیدواژه‌ها ---
OversightTask.ac_verify_cache, compute_files_checksum, VerificationReport.verify_trace, VerificationReport.ac_probe_details, VerificationReport.verify_version, VerificationReport.config_used, VerifyConfig, WatchedProject.verify_v6_config, GET /api/oversight/tasks/{task_id}/verify-trace, GET/PATCH /api/oversight/watched/{id}/verify-v6-config, enable_ac_cache, force_full_verify, context.trace
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی کش per-AC، حالت رهگیری و متمرکزسازی VerifyConfig در Oversight

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست پیاده‌سازی سه بهبود مجزا اما مرتبط در backend سیستم Oversight را دارد:

**بهبود ۷ — Per-AC state cache**: مشکل این است که هر بار verify اجرا می‌شود، همهٔ AC ها از صفر چک می‌شوند. اگر AC در ۳ run اخیر `done` با confidence > 0.85 بود و فایل‌های مرتبط تغییر نکردند، re-verify لازم نیست. راه‌حل: فیلد جدید `ac_verify_cache: Dict[str, Any]` روی `OversightTask` با ساختار شامل `ac_hash`, `verdict`, `confidence`, `last_verified_at`, `files_checksum`, `consecutive_done_count`, `evidence`. منطق: قبل از verify هر AC، hash از متن AC + classification گرفته شود، cache چک شود، اگر `consecutive_done_count >= 3 AND files_checksum unchanged AND age < 7 days` باشد، skip probes و از cache استفاده کند. بعد از verify، اگر verdict = done و confidence > 0.85 باشد، `consecutive_done_count += 1` و `files_checksum = compute_files_checksum(target_files)`. اگر verdict != done باشد، `consecutive_done_count = 0` و cache invalidate شود. تابع `compute_files_checksum`: sha256 از target_files content. flag config: `enable_ac_cache: bool = True` (پیش‌فرض True). کاربر می‌تواند با `?force_full_verify=true` بای‌پاس کند.

**بهبود ۸ — Observability/Trace mode**: مشکل این است که کاربر نمی‌تواند بفهمد چرا verify گفته partial. باید بتواند trace کامل را ببیند. راه‌حل: تمام تصمیم‌های verify در `context.trace` log شوند با ساختار شامل `ts`, `phase`, `ac_index`, `ac_text`, `decision`, `reason`, `evidence`, `probe_results`, `elapsed_ms`. سپس روی `VerificationReport` فیلدهای `verify_trace: List[Dict]`, `ac_probe_details: List[Dict]`, `verify_version: str = "v6"`, `config_used: Dict` اضافه شود. endpoint جدید: `GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}` که trace کامل آخرین (یا specific) verify را برگرداند. UI: یک accordion "🔍 Trace" در زیر هر AC در دیتیل تسک برای نمایش step-by-step تصمیمات.

**بهبود ۹ — Centralized VerifyConfig**: مشکل این است که هر knob (max_iterations, max_files, model_tier, ...) جدا گفته شده و متمرکز نیست. راه‌حل: ساختار `VerifyConfig` با فیلدهای `max_iterations`, `iter1_confidence_threshold`, `iter2_confidence_threshold`, `enable_content_grep`, `max_files_per_run`, `max_file_size_bytes`, `max_identifiers_per_ac`, `iter2_max_extra_files`, `iter2_max_identifiers`, `strong_model_preference`, `enable_ac_cache`, `ac_cache_max_age_days`, `ac_cache_consecutive_threshold`, `weights`, `enable_trace`, `trace_max_entries`. ذخیره در `WatchedProject.verify_v6_config: Optional[Dict] = None` (اگر None، defaults). endpoint: `GET/PATCH /api/oversight/watched/{id}/verify-v6-config`.

کلیدواژه‌ها: OversightTask.ac_verify_cache, compute_files_checksum, VerificationReport.verify_trace, VerificationReport.ac_probe_details, VerificationReport.verify_version, VerificationReport.config_used, VerifyConfig, WatchedProject.verify_v6_config, GET /api/oversight/tasks/{task_id}/verify-trace, GET/PATCH /api/oversight/watched/{id}/verify-v6-config, enable_ac_cache, force_full_verify, context.trace.

شواهد در کد واقعی: فایل‌های مرتبط در deep context شامل `backend/app/api/routes/oversight.py` (احتمالاً endpoint‌های oversight در آن تعریف شده)، `backend/app/services/oversight_service.py` (سرویس اصلی oversight)، `backend/app/services/oversight_verifier.py` (احتمال

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 47: اجرای گام‌های تکراری تأیید (Iterative Verify) با کش و طبقه‌بندی AC

**Scope:** این بخش منطق کامل حلقه تأیید تکراری برای هر AC (Acceptance Criterion) را مشخص می‌کند: بارگذاری پیکربندی، ساخت زمینه، طبقه‌بندی AC، بررسی کش، اجرای حداکثر ۳ دور (iteration) با استراتژی‌های فزاینده (grep، vision، playwright، مدل قوی)، تجمیع رأی‌ها، به‌روزرسانی کش، و ثبت جزئیات در verify_trace. بخش‌های خارج از scope: منطق کلی task verdict (aggregate per-AC) و title reassess (C5) که در انتهای نمودار آمده‌اند اما جزئیات اجرایی آن‌ها در این بخش نیست.
**Key terms:** verify_task, VerifyConfig, VerifyContext, classify_ac, ac_verify_cache, ProbeResult, iterative_verify_step, content_grep, smart_grep_for_ac, code_aware, vision, playwright, aggregate_verdicts, _strong_model_judgment, verify_trace, ac_probe_details, consecutive_done_count, files_checksum, backend/app/services/oversight_verifier.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, backend/app/services/oversight_strong_prompt.py, ProbeContext

**بخش مربوط از متن کاربر:**
```
```
verify_task(task_id, verify_v6=True)
│
├── load WatchedProject.verify_v6_config → VerifyConfig
│
├── build_verify_context(task, watched, config) → VerifyContext
│
├── for each AC (یا task_step):
│    │
│    ├── classify_ac(ac, context) → classification ("frontend"|"backend"|...)
│    │
│    ├── 🆕 check ac_verify_cache:
│    │    if cache_hit_with_freshness:
│    │        → use cached ProbeResult, log "cached"
│    │        → skip iterations
│    │    else:
│    │        → run iterative verify
│    │
│    ├── iterative_verify_step(ac, context, max_iter=3):
│    │    │
│    │    ├── iteration 1: standard probes
│    │    │    ├── content_grep (smart_grep_for_ac)
│    │    │    ├── code_aware (basename + diff)
│    │    │    ├── vision (if frontend/fullstack)
│    │    │    └── playwright (if URL)
│    │    │
│    │    ├── aggregate_verdicts(probes) → ProbeResult
│    │    ├── if confidence ≥ 0.8 → finalize
│    │    │
│    │    ├── iteration 2: aggressive content_grep
│    │    │    ├── full repo grep (filtered)
│    │    │    ├── more identifiers
│    │    │    └── AI rerun with new evidence
│    │    │
│    │    ├── aggregate → ProbeResult
│    │    ├── if confidence ≥ 0.7 → finalize
│    │    │
│    │    ├── iteration 3: strong model escalation
│    │    │    └── _strong_model_judgment(ac, context, prior_results)
│    │    │
│    │    └── finalize unconditionally
│    │
│    ├── update ac_verify_cache:
│    │    if verdict==done && confidence > 0.85:
│    │        consecutive_done_count++, files_checksum updated
│    │    else:
│    │        cache invalidated
│    │
│    └── append to verify_trace + ac_probe_details
```
```

verify_task(task_id, verify_v6=True)
│
├── load WatchedProject.verify_v6_config → VerifyConfig
│
├── build_verify_context(task, watched, config) → VerifyContext
│
├── for each AC (یا task_step):
│    │
│    ├── classify_ac(ac, context) → classification ("frontend"|"backend"|...)
│    │
│    ├── 🆕 check ac_verify_cache:
│    │    if cache_hit_with_freshness:
│    │        → use cached ProbeResult, log "cached"
│    │        → skip iterations
│    │    else:
│    │        → run iterative verify
│    │
│    ├── iterative_verify_step(ac, context, max_iter=3):
│    │    │
│    │    ├── iteration 1: standard probes
│    │    │    ├── content_grep (smart_grep_for_ac)
│    │    │    ├── code_aware (basename + diff)
│    │    │    ├── vision (if frontend/fullstack)
│    │    │    └── playwright (if URL)
│    │    │
│    │    ├── aggregate_verdicts(probes) → ProbeResult
│    │    ├── if confidence ≥ 0.8 → finalize
│    │    │
│    │    ├── iteration 2: aggressive content_grep
│    │    │    ├── full repo grep (filtered)
│    │    │    ├── more identifiers
│    │    │    └── AI rerun with new evidence
│    │    │
│    │    ├── aggregate → ProbeResult
│    │    ├── if confidence ≥ 0.7 → finalize
│    │    │
│    │    ├── iteration 3: strong model escalation
│    │    │    └── _strong_model_judgment(ac, context, prior_results)
│    │    │
│    │    └── finalize unconditionally
│    │
│    ├── update ac_verify_cache:
│    │    if verdict==done && confidence > 0.85:
│    │        consecutive_done_count++, files_checksum updated
│    │    else:
│    │        cache invalidated
│    │
│    └── append to verify_trace + ac_probe_details
```

--- کلیدواژه‌ها ---
verify_task, VerifyConfig, VerifyContext, classify_ac, ac_verify_cache, ProbeResult, iterative_verify_step, content_grep, smart_grep_for_ac, code_aware, vision, playwright, aggregate_verdicts, _strong_model_judgment, verify_trace, ac_probe_details, consecutive_done_count, files_checksum, backend/app/services/oversight_verifier.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, backend/app/services/oversight_strong_prompt.py, ProbeContext
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی حلقه تأیید تکراری (Iterative Verify) با کش و طبقه‌بندی AC در oversight_verifier.py

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
اجرای گام‌های تکراری تأیید (Iterative Verify) با کش و طبقه‌بندی AC. این بخش منطق کامل حلقه تأیید تکراری برای هر AC (Acceptance Criterion) را مشخص می‌کند: بارگذاری پیکربندی، ساخت زمینه، طبقه‌بندی AC، بررسی کش، اجرای حداکثر ۳ دور (iteration) با استراتژی‌های فزاینده (grep، vision، playwright، مدل قوی)، تجمیع رأی‌ها، به‌روزرسانی کش، و ثبت جزئیات در verify_trace. بخش‌های خارج از scope: منطق کلی task verdict (aggregate per-AC) و title reassess (C5) که در انتهای نمودار آمده‌اند اما جزئیات اجرایی آن‌ها در این بخش نیست.

کلیدواژه‌های کاربر: verify_task, VerifyConfig, VerifyContext, classify_ac, ac_verify_cache, ProbeResult, iterative_verify_step, content_grep, smart_grep_for_ac, code_aware, vision, playwright, aggregate_verdicts, _strong_model_judgment, verify_trace, ac_probe_details, consecutive_done_count, files_checksum, backend/app/services/oversight_verifier.py, backend/app/services/verify_runtime/inspector_probe.py, backend/app/services/verify_runtime/vision_helper.py, backend/app/services/verify_runtime/base.py, backend/app/services/verify_runtime/runner.py, backend/app/services/oversight_strong_prompt.py, ProbeContext.

شواهد در کد واقعی: در `backend/app/services/oversight_verifier.py` تابع `_evaluate_acs_against_files` (خط 232) و `_build_keywords_from_acs` (خط 438) و `_extract_relevant_chunks` (خط 349) وجود دارند که مبنای content_grep و smart_grep_for_ac هستند. تابع `_classify_step_for_probe` (خط 72) طبقه‌بندی AC را با ۱۰ قاعده انجام می‌دهد. در `backend/app/services/verify_runtime/inspector_probe.py` (خط 1) probe مخصوص UI interaction با Playwright تعریف شده. در `backend/app/services/oversight_strong_prompt.py` تابع `build_strong_prompt` (خط 158) ساختار پرامپت را با acceptance_criteria غنی (شامل behavior, acceptance_signal, business_intent) پشتیبانی می‌کند. در `backend/app/services/verify_runtime/base.py` کلاس ProbeContext و ProbeResult احتمالاً تعریف شده‌اند. در `backend/app/services/verify_runtime/runner.py` منطق اجرای probeها قرار دارد. در `backend/app/services/verify_runtime/vision_helper.py` vision probe برای frontend/fullstack ACها. تابع `_recover_partial_json` (خط 556) و `_sync_prompt_checkboxes` (خط 526) و `format_done_remaining_for_message` (خط 654) در verifier.py برای مدیریت خروجی و کش استفاده می‌شوند. تابع `_fetch_target_files` (خط 162) و `_fetch_repo_tree` (خط 176) و `_github_code_search` (خط 498) برای fetch فایل‌ها و جستجوی کد در GitHub API. تابع `_find_similar_paths` (خط 694) برای یافتن فایل‌های مشابه. تابع `_fetch_recent_commits` (خط 734) برای بررسی کامیت‌های اخیر. متغیر `_BACKFILL_NEEDED_NOTIFY_LAST_AT` (خط 766) و تابع `_maybe_send_backfill_needed_notification` (خط 770) برای نوتیفیکیشن backfill. تابع `_ac_text_of` (خط 224) برای استخراج متن AC از dict یا str. تابع `_format_machine_evidence_for_prompt` (خط 322) برای شواهد ماشینی per-AC.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در `backend/app/services/oversight_verifier.py` یک کلاس جدید `VerifyConfig` با فیلدهای `max_iterations: int = 3`, `confidence

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 48: ایجاد و بازنویسی فایل‌های سرویس verify_runtime و oversight برای پشتیبانی از verify_v6

**Scope:** این بخش شامل ایجاد ۴ فایل جدید در backend/app/services/verify_runtime/ (context_builder, code_content_searcher, iterative_orchestrator, ac_cache_service)، بازنویسی code_aware_verifier با فازهای A→B→C→D، تغییرات در oversight_verifier (افزودن _classify_step_for_probe با ۱۰ قاعده و flag verify_v6)، به‌روزرسانی oversight_service (افزودن ac_verify_cache و verify_v6_config به dataclass‌ها)، export در __init__.py، اضافه کردن endpoint‌های verify-trace و verify-v6-config (GET/PATCH) و پارامتر verify_v6 در endpoint verify در oversight.py، و ایجاد دو فایل تست جدید است. نکته حیاتی: تمام فایل‌ها و کلاس‌ها باید دقیقاً با نام‌های ذکر شده ایجاد شوند و scope هر فایل مطابق جدول رعایت شود.
**Key terms:** VerifyContext, VerifyConfig, build_verify_context, fetch_file_content, grep_token_in_files, smart_grep_for_ac, extract_identifiers, ProbeResult, iterative_verify_step, aggregate_verdicts, _strong_model_judgment, compute_files_checksum, check_ac_cache, update_ac_cache, code_aware_verifier.py, _classify_step_for_probe, verify_v6, ac_verify_cache, verify_v6_config, verify-trace, verify-v6-config, backend/app/services/verify_runtime/context_builder.py, backend/app/services/verify_runtime/code_content_searcher.py, backend/app/services/verify_runtime/iterative_orchestrator.py, backend/app/services/verify_runtime/ac_cache_service.py

**بخش مربوط از متن کاربر:**
```
## 📁 File map (v2)

| فایل | تغییر | scope |
|---|---|---|
| `backend/app/services/verify_runtime/context_builder.py` | **جدید** | `VerifyContext`, `VerifyConfig`, `build_verify_context` |
| `backend/app/services/verify_runtime/code_content_searcher.py` | **جدید** | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` + ۴ مثال concrete در docstring |
| `backend/app/services/verify_runtime/iterative_orchestrator.py` | **جدید** | `ProbeResult`, `iterative_verify_step`, `aggregate_verdicts`, `_strong_model_judgment` |
| `backend/app/services/verify_runtime/ac_cache_service.py` | **جدید** | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| `verify_runtime/code_aware_verifier.py` | بازنویسی phase A→B→C→D با نام تابع‌های صریح | همان فایل، +۲۰۰ خط |
| `backend/app/services/oversight_verifier.py` | `_classify_step_for_probe` با ۱۰ قاعده + integration با orchestrator + flag `verify_v6` | همان فایل |
| `backend/app/services/oversight_service.py` | اضافه کردن `ac_verify_cache` و `verify_v6_config` به dataclass ها | همان فایل |
| `backend/app/services/verify_runtime/__init__.py` | export نام‌های جدید | همان فایل |
| `backend/app/api/routes/oversight.py` | endpoint های جدید: `verify-trace`, `verify-v6-config` (GET/PATCH) + پارامتر `verify_v6=True|False` در verify endpoint | همان فایل |
| `backend/tests/test_code_content_searcher.py` | **جدید** | unit tests برای `extract_identifiers` با ۴ مثال + grep test |
| `backend/tests/test_iterative_orchestrator.py` | **جدید** | unit tests برای `aggregate_verdicts` با ۵ سناریو |
```

## 🎯 هدف (خلاصه ساختاریافته)
ایجاد و بازنویسی سرویس‌های verify_runtime و oversight برای پشتیبانی از verify_v6

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
کاربر درخواست ایجاد و بازنویسی فایل‌های سرویس verify_runtime و oversight برای پشتیبانی از verify_v6 را با اولویت critical و نوع refactor داده است. این درخواست شامل ایجاد ۴ فایل جدید در backend/app/services/verify_runtime/ (context_builder.py با کلاس‌های VerifyContext, VerifyConfig و تابع build_verify_context؛ code_content_searcher.py با توابع fetch_file_content, grep_token_in_files, smart_grep_for_ac, extract_identifiers + ۴ مثال concrete در docstring؛ iterative_orchestrator.py با کلاس ProbeResult و توابع iterative_verify_step, aggregate_verdicts, _strong_model_judgment؛ ac_cache_service.py با توابع compute_files_checksum, check_ac_cache, update_ac_cache)، بازنویسی code_aware_verifier.py با فازهای A→B→C→D (همان فایل، +۲۰۰ خط)، تغییرات در oversight_verifier.py (افزودن _classify_step_for_probe با ۱۰ قاعده و flag verify_v6)، به‌روزرسانی oversight_service.py (افزودن ac_verify_cache و verify_v6_config به dataclass‌های OversightTask و WatchedProject)، export در __init__.py، اضافه کردن endpoint‌های verify-trace و verify-v6-config (GET/PATCH) و پارامتر verify_v6 در endpoint verify در oversight.py، و ایجاد دو فایل تست جدید test_code_content_searcher.py (unit tests برای extract_identifiers با ۴ مثال + grep test) و test_iterative_orchestrator.py (unit tests برای aggregate_verdicts با ۵ سناریو). نکته حیاتی: تمام فایل‌ها و کلاس‌ها باید دقیقاً با نام‌های ذکر شده ایجاد شوند و scope هر فایل مطابق جدول رعایت شود. کلیدواژه‌های اصلی: VerifyContext, VerifyConfig, build_verify_context, fetch_file_content, grep_token_in_files, smart_grep_for_ac, extract_identifiers, ProbeResult, iterative_verify_step, aggregate_verdicts, _strong_model_judgment, compute_files_checksum, check_ac_cache, update_ac_cache, code_aware_verifier.py, _classify_step_for_probe, verify_v6, ac_verify_cache, verify_v6_config, verify-trace, verify-v6-config. شواهد در کد واقعی: در oversight_service.py خطوط ۴۴۹-۴۶۱ فیلد ac_verify_cache در dataclass OversightTask تعریف شده و خطوط ۲۸۰-۲۸۵ فیلد verify_v6_config در dataclass WatchedProject تعریف شده است. در oversight_verifier.py خطوط ۴۲-۶۹ قواعد _C6_CLASSIFY_RULES و خطوط ۷۲-۱۱۹ تابع _classify_step_for_probe با ۱۰ قاعده پیاده‌سازی شده‌اند. در code_aware_verifier.py (فایل موجود در ساختار) باید فازهای A→B→C→D اضافه شود.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. ایجاد فایل جدید backend/app/services/verify_runtime/context_builder.py شامل کلاس‌های VerifyContext (با فیلدهای task_id, watched_id, project_full_name, target_files, acceptance_criteria, task_prompt, repo_tree, file_contents, machine_evidence, verify_config, trace) و VerifyConfig (با فیلدهای max_iterations=3, thresholds={'done_confidence': 0.85, 'partial_confidence': 0.6}, weights={'static': 0.3, 'ui': 0.25, 'api': 0.25, 'backend_log': 0.2}, strong_model_preference='', ac_cache_enabled=True, ac_cache_ttl_days=7, ac_cache_min_consecutive_done=3, trace_enabled=False) و تابع build_verify_context که یک OversightTask و WatchedProject دریافت کرده و context کامل برای verify می‌سازد. ۲. ایجاد فایل جدید backend/app/services/verify_runtime/code_content_searcher.py شامل توابع fetch_file_content (دریافت محتوای فایل از GitHub API یا local repo)، grep_token_in_files (جستجوی token در لیست فایل‌ها با پشتیبانی از regex)، smart_grep_for_ac (جستجوی

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 49: تعریف ۱۲ معیار موفقیت (AC) برای Verify v6 با meta-test سختگیرانه

**Scope:** این بخش ۱۲ Acceptance Criteria (AC) مشخص و قابل grep را برای قابلیت Verify v6 تعریف می‌کند. هر AC یک فایل/کلاس/تابع/endpoint خاص را هدف می‌گیرد. معیار سختگیرانه این است که وقتی Verify v6 روی این bug اجرا شود، باید ≥۱۱ از ۱۲ AC را با confidence ≥ 0.8 پاس کند. این بخش صرفاً معیارها را لیست می‌کند و دستور اجرا یا پیاده‌سازی نمی‌دهد.
**Key terms:** VerifyContext, build_verify_context, VerifyConfig, code_content_searcher.py, fetch_file_content, grep_token_in_files, smart_grep_for_ac, extract_identifiers, iterative_orchestrator.py, iterative_verify_step, aggregate_verdicts, ProbeResult, _strong_model_judgment, ac_cache_service.py, compute_files_checksum, check_ac_cache, update_ac_cache, _classify_step_for_probe, oversight_verifier.py, code_aware_verifier.py, _phase_a_basename_match, _phase_b_content_grep, _phase_c_extended_repo_grep, _phase_d_ai_judgment, ac_verify_cache

**بخش مربوط از متن کاربر:**
```
## 🧪 معیار موفقیت + meta-test (v2 — concrete AC list)

این bug **باید با خودش verify شود**. ۱۲ AC مشخص (افزایش از ۱۰ به ۱۲):

| # | AC | identifier‌های قابل grep |
|---|---|---|
| 1 | فایل `context_builder.py` با کلاس `VerifyContext` و تابع `build_verify_context` | `VerifyContext`, `build_verify_context`, `VerifyConfig` |
| 2 | فایل `code_content_searcher.py` با ۴ تابع + ۴ مثال در docstring | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` |
| 3 | فایل `iterative_orchestrator.py` با ۳ symbol + strong model escalation | `iterative_verify_step`, `aggregate_verdicts`, `ProbeResult`, `_strong_model_judgment` |
| 4 | فایل `ac_cache_service.py` با ۳ تابع cache | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| 5 | `_classify_step_for_probe` با ۱۰ قاعدهٔ explicit در `oversight_verifier.py` | `"backend"`, `"frontend"`, `"fullstack"`, `"infra"`, `"test_only"`, `"doc_only"`, `"manual_only"` |
| 6 | `code_aware_verifier.py` با ۴ تابع جدید phase | `_phase_a_basename_match`, `_phase_b_content_grep`, `_phase_c_extended_repo_grep`, `_phase_d_ai_judgment` |
| 7 | فیلد جدید `ac_verify_cache` روی `OversightTask` dataclass | `ac_verify_cache` در `oversight_service.py` |
| 8 | فیلد جدید `verify_v6_config` روی `WatchedProject` dataclass | `verify_v6_config` |
| 9 | `VerificationReport` با فیلدهای `verify_trace`, `ac_probe_details`, `verify_version`, `config_used` | همان نام‌ها در dataclass |
| 10 | endpoint `GET /tasks/{task_id}/verify-trace` و `GET/PATCH /watched/{id}/verify-v6-config` | router decorators |
| 11 | پارامتر `verify_v6: bool = True` در `verify_task` signature | `verify_v6` در function def |
| 12 | حداقل ۲ فایل تست: `test_code_content_searcher.py` (۴ مثال extract_identifiers) و `test_iterative_orchestrator.py` (۵ سناریو aggregate_verdicts) | اسامی فایل + assertion های concrete |

**معیار سخت‌گیرانه:** vary v6 وقتی روی این bug اجرا شد، باید **≥۱۱ از ۱۲ AC** را done ببیند (با confidence ≥ 0.8).

اگر کمتر → یعنی verify v6 خودش هنوز ضعیف است → bug C6 fail.
```

## 🎯 هدف (خلاصه ساختاریافته)
تعریف ۱۲ AC برای Verify v6 با meta-test سختگیرانه

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک ۱۲ Acceptance Criteria (AC) مشخص و قابل grep را برای قابلیت Verify v6 تعریف می‌کند. هر AC یک فایل/کلاس/تابع/endpoint خاص را هدف می‌گیرد. معیار سختگیرانه این است که وقتی Verify v6 روی این bug اجرا شود، باید ≥۱۱ از ۱۲ AC را با confidence ≥ 0.8 پاس کند. این بخش صرفاً معیارها را لیست می‌کند و دستور اجرا یا پیاده‌سازی نمی‌دهد.

ACهای تعریف‌شده:
1. فایل `context_builder.py` با کلاس `VerifyContext` و تابع `build_verify_context` (identifier‌های قابل grep: `VerifyContext`, `build_verify_context`, `VerifyConfig`)
2. فایل `code_content_searcher.py` با ۴ تابع + ۴ مثال در docstring (`fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers`)
3. فایل `iterative_orchestrator.py` با ۳ symbol + strong model escalation (`iterative_verify_step`, `aggregate_verdicts`, `ProbeResult`, `_strong_model_judgment`)
4. فایل `ac_cache_service.py` با ۳ تابع cache (`compute_files_checksum`, `check_ac_cache`, `update_ac_cache`)
5. `_classify_step_for_probe` با ۱۰ قاعدهٔ explicit در `oversight_verifier.py` (identifier‌ها: `"backend"`, `"frontend"`, `"fullstack"`, `"infra"`, `"test_only"`, `"doc_only"`, `"manual_only"`)
6. `code_aware_verifier.py` با ۴ تابع جدید phase (`_phase_a_basename_match`, `_phase_b_content_grep`, `_phase_c_extended_repo_grep`, `_phase_d_ai_judgment`)
7. فیلد جدید `ac_verify_cache` روی `OversightTask` dataclass در `oversight_service.py`
8. فیلد جدید `verify_v6_config` روی `WatchedProject` dataclass
9. `VerificationReport` با فیلدهای `verify_trace`, `ac_probe_details`, `verify_version`, `config_used`
10. endpoint `GET /tasks/{task_id}/verify-trace` و `GET/PATCH /watched/{id}/verify-v6-config`
11. پارامتر `verify_v6: bool = True` در `verify_task` signature
12. حداقل ۲ فایل تست: `test_code_content_searcher.py` (۴ مثال extract_identifiers) و `test_iterative_orchestrator.py` (۵ سناریو aggregate_verdicts)

شواهد در کد واقعی: فایل `backend/app/services/oversight_verifier.py` از خط ۴۲ تا ۶۹ شامل `_C6_CLASSIFY_RULES` با ۱۰ قاعده است. فایل `backend/app/services/verify_runtime/code_aware_verifier.py` از خط ۴۹۳ تا ۵۵۷ شامل `_phase_a_basename_match` و `_phase_b_content_grep` است. فایل `backend/app/services/verify_runtime/iterative_orchestrator.py` (deep-read نشده) باید شامل `iterative_verify_step` و `aggregate_verdicts` باشد. فایل `backend/app/services/verify_runtime/code_content_searcher.py` (deep-read نشده) باید شامل `extract_identifiers` و `smart_grep_for_ac` باشد. فایل `backend/app/services/verify_runtime/ac_cache_service.py` (deep-read نشده) باید شامل `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` باشد. فایل `backend/app/services/oversight_service.py` (deep-read نشده) باید شامل `OversightTask` با فیلد `ac_verify_cache` و `WatchedProject` با فیلد `verify_v6_config` و `VerificationReport` با فیلدهای `verify_trace`, `ac_probe_details`, `verify_version`, `config_used` باشد. endpoint‌ها در `backend/app/api/routes/oversight.py` (deep-read نشده) باید شامل `GET /tasks

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
_(مجری بر اساس Context و معیارهای پذیرش، مراحل را تعیین کند)_

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 50: پیاده‌سازی Edge Cases نسخه v2 برای Oversight Verifier

**Scope:** این بخش شامل ۱۴ مورد از edge cases نسخه v2 است که باید در سرویس oversight_verifier پیاده‌سازی شوند. موارد شامل مدیریت rate limit گیت‌هاب، فایل‌های بزرگ/باینری، fallback منطق، پشتیبانی از چندزبانگی، کنترل حافظه، backward compatibility، A/B testing، race condition در cache invalidation، عدم دسترسی به مدل قوی، محدودیت trace size و اعتبارسنجی کانفیگ است. موارد ۱ تا ۱۰ از نسخه v1 هستند و موارد ۱۱ تا ۱۴ جدید (v2) می‌باشند. تمام این موارد باید در کلاس VerifyService یا VerifyContext پیاده‌سازی شوند.
**Key terms:** VerifyContext, VerifyConfig, oversight_verifier.py, verify_v6, verify_v6_config, asyncio.Lock, RuntimeProbeResult, ProbeContext, InspectorSession

**بخش مربوط از متن کاربر:**
```
## ⚠️ Edge cases (v2 — افزایش‌یافته)

1. **GitHub rate limit**: cache aggressive + cap 50 file. اگر rate limit hit شد، fallback به v5 منطق.
2. **Large file**: skip > 500KB (configurable).
3. **Binary file**: skip اگر non-text Content-Type.
4. **Token not in private repo**: fallback graceful.
5. **Identifier spam**: AC تمام stop-words → fallback به AI.
6. **Multi-language**: identifiers از فارسی+انگلیسی هر دو (با regex unicode-aware).
7. **Recursion**: orchestrator فقط probes را call می‌کند، نه `verify_task`.
8. **Memory**: caps روی هر فیلد VerifyContext.
9. **Backward compat**: `verify_v6=False` → مسیر v5.
10. **A/B**: random seed برای ۵۰/۵۰ split بین v5/v6 (debug).
11. **🆕 (v2) Cache invalidation race**: اگر دو verify همزمان روی یک تسک شروع شدند، cache lock با `asyncio.Lock` per-task.
12. **🆕 (v2) Strong model unavailable**: اگر هیچ strong model در chain موجود نیست، iteration 3 با fallback model اجرا می‌شود (با warning log) — fail نمی‌کند.
13. **🆕 (v2) Trace size**: cap ۱۰۰۰ entry per verify_run. اگر بیشتر، oldest حذف می‌شوند (FIFO).
14. **🆕 (v2) Config validation**: اگر user verify_v6_config با مقادیر out-of-range تنظیم کرد (مثلاً max_iterations=100)، clamp به range معتبر.
```

## 🎯 هدف (خلاصه ساختاریافته)
پیاده‌سازی ۱۴ Edge Case v2 در Oversight Verifier

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
پیاده‌سازی ۱۴ مورد از edge cases نسخه v2 در سرویس oversight_verifier.py. موارد شامل: 1) GitHub rate limit: cache aggressive + cap 50 file. اگر rate limit hit شد، fallback به v5 منطق. 2) Large file: skip > 500KB (configurable). 3) Binary file: skip اگر non-text Content-Type. 4) Token not in private repo: fallback graceful. 5) Identifier spam: AC تمام stop-words → fallback به AI. 6) Multi-language: identifiers از فارسی+انگلیسی هر دو (با regex unicode-aware). 7) Recursion: orchestrator فقط probes را call می‌کند، نه verify_task. 8) Memory: caps روی هر فیلد VerifyContext. 9) Backward compat: verify_v6=False → مسیر v5. 10) A/B: random seed برای ۵۰/۵۰ split بین v5/v6 (debug). 11) Cache invalidation race: اگر دو verify همزمان روی یک تسک شروع شدند، cache lock با asyncio.Lock per-task. 12) Strong model unavailable: اگر هیچ strong model در chain موجود نیست، iteration 3 با fallback model اجرا می‌شود (با warning log) — fail نمی‌کند. 13) Trace size: cap ۱۰۰۰ entry per verify_run. اگر بیشتر، oldest حذف می‌شوند (FIFO). 14) Config validation: اگر user verify_v6_config با مقادیر out-of-range تنظیم کرد (مثلاً max_iterations=100)، clamp به range معتبر. کلیدواژه‌ها: VerifyContext, VerifyConfig, oversight_verifier.py, verify_v6, verify_v6_config, asyncio.Lock, RuntimeProbeResult, ProbeContext, InspectorSession. شواهد در کد: فایل backend/app/services/oversight_verifier.py شامل کلاس‌های VerifyService و VerifyContext (خطوط 1-600+). تابع _fetch_target_files (خط 162) و _github_code_search (خط 498) نیاز به rate limit handling دارند. تابع _extract_relevant_chunks (خط 349) برای large file handling. تابع _build_keywords_from_acs (خط 438) برای multi-language و identifier spam. تابع _recover_partial_json (خط 556) برای backward compatibility. تابع _sync_prompt_checkboxes (خط 526) برای backward compat. تابع _evaluate_acs_against_files (خط 232) برای A/B testing. تابع _classify_step_for_probe (خط 72) برای recursion prevention.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. 1. در فایل backend/app/services/oversight_verifier.py، کلاس VerifyService را با متدهای جدید برای edge cases توسعه بده. 2. برای GitHub rate limit (مورد 1): در تابع _fetch_target_files (خط 162) و _github_code_search (خط 498) یک decorator/cache با asyncio.Lock اضافه کن. اگر rate limit hit شد (HTTP 403/429)، fallback به v5 logic با flag. 3. برای large file (مورد 2): در تابع _fetch_file (خط 131) پارامتر max_bytes را configurable کن (پیش‌فرض 500KB). اگر فایل بزرگ‌تر بود، skip با log. 4. برای binary file (مورد 3): در _fetch_file بعد از دریافت content، Content-Type را چک کن. اگر non-text (مثل application/octet-stream)، skip. 5. برای token not in private repo (مورد 4): در get_github_token (import شده از oversight_service خط 30) اگر token None یا invalid بود، graceful fallback با anonymous access. 6. برای identifier spam (مورد 5): در _build_keywords_from_acs (خط 438) اگر بعد از حذف stopwords هیچ keyword نماند، fallback به AI با flag. 7. برای multi-language (مورد 6): regex unicode-aware برای فارسی (؀-ۿ) و انگلیسی در _build_keywords_from_acs. 8. برای recursion (مورد 7): در orchestrator (backend/app/api/routes/orchestrator.py خط 315) مطمئن شو فقط probes را call می‌کند، نه verify_task. 9. برای memory (مورد 8): caps روی هر فیلد VerifyContext (مثلاً

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

# 🔹 مرحله 51: تعیین محدوده خارج از اسکوپ و ترتیب اجرای v2 با ۸ chunk

**Scope:** این بخش دو بخش مجزا دارد: (۱) فهرست مواردی که خارج از اسکوپ پروژه هستند و نباید تغییر داده شوند (شامل Playwright probe، vision probe، ML classification، تشخیص multi-language source code، AST-level analysis، distributed cache، WebSocket live progress). (۲) اشاره به ترتیب اجرای نسخه دوم (v2) با ۸ chunk که جزئیات آن در ادامه درخواست اصلی آمده است. این بخش صرفاً محدوده را مشخص می‌کند و شامل هیچ مرحله اجرایی جدیدی نیست.
**Key terms:** Playwright probe, vision probe, ML classification, multi-language, source code, AST-level analysis, distributed cache, WebSocket live progress, v2, ۸ chunk

**بخش مربوط از متن کاربر:**
```
## 🚫 خارج از scope (بدون تغییر)

(همان قبلی)
- تغییر در Playwright probe
- تغییر در vision probe
- ML classification
- multi-language تشخیص source code (فقط py/ts/tsx/js/jsx)
- AST-level analysis
- distributed cache
- WebSocket live progress

---

## 🔬 ترتیب اجرا (v2 — با ۸ chunk)
```

## 🎯 هدف (خلاصه ساختاریافته)
تعیین محدوده خارج از اسکوپ و ترتیب اجرای v2 با ۸ chunk

## 📍 موقعیت دقیق در پروژه
_(file:line — symbol — snippet)_

- `backend/app/services/verify_runtime/vision_helper.py:1-50` — `VisionHelper` — این فایل vision probe را پیاده‌سازی می‌کند و نباید در v2 تغییر کند
  ```python
  فایل deep-read شده — vision probe که خارج از اسکوپ است
  ```
- `backend/app/services/verify_runtime/browser_pool.py:1-30` — `BrowserPool` — این فایل Playwright browser pool را مدیریت می‌کند و خارج از اسکوپ v2 است
  ```python
  فایل deep-read نشده — بر اساس ساختار سطحی
  ```
- `backend/app/api/routes/analysis.py:83-268` — `run_analysis_stream`
  ```python
  async def generate_events():
      final_result = None
      async def run_analysis_task():
          nonlocal final_result
          try:
              ai_manager = get_ai_manager()
              from ...core.database import SessionLocal
              analysis_db = SessionLocal()
              deep_analyzer = DeepAnalysisService(
                  ai_manager=ai_manager,
                  progress_callback=progress_callback,
                  db_session=analysis_db
              )
  ```

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
این تسک دو بخش مجزا دارد: (۱) فهرست مواردی که خارج از اسکوپ پروژه هستند و نباید تغییر داده شوند (شامل Playwright probe، vision probe، ML classification، تشخیص multi-language source code، AST-level analysis، distributed cache، WebSocket live progress). (۲) اشاره به ترتیب اجرای نسخه دوم (v2) با ۸ chunk که جزئیات آن در ادامه درخواست اصلی آمده است. این بخش صرفاً محدوده را مشخص می‌کند و شامل هیچ مرحله اجرایی جدیدی نیست.

بر اساس تحلیل کد واقعی پروژه:
- در backend/app/services/verify_runtime/vision_helper.py (فایل deep-read شده) سرویس vision probe وجود دارد که نباید تغییر کند.
- در backend/app/services/verify_runtime/browser_pool.py و backend/app/services/verify_runtime/ui_probe.py سرویس‌های Playwright probe وجود دارند.
- در backend/app/services/analysis_progress_manager.py (خطوط ۱-۱۷۰) سیستم progress tracking با polling (نه WebSocket) پیاده‌سازی شده است.
- در backend/app/api/routes/analysis.py (خطوط ۸۳-۲۶۸) endpoint /run-stream از SSE (Server-Sent Events) استفاده می‌کند، نه WebSocket.
- در backend/app/services/deep_analysis_service.py تحلیل source code فقط برای py/ts/tsx/js/jsx انجام می‌شود.
- هیچ distributed cache یا AST-level analysis در کد فعلی وجود ندارد.

کلیدواژه‌های کاربر: Playwright probe, vision probe, ML classification, multi-language, source code, AST-level analysis, distributed cache, WebSocket live progress, v2, ۸ chunk

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. این تسک صرفاً مستندسازی محدوده است و نیاز به تغییر کد ندارد. مراحل:
1. تأیید کنید که فایل‌های زیر در scope تغییرات v2 قرار نگیرند:
   - backend/app/services/verify_runtime/vision_helper.py (vision probe)
   - backend/app/services/verify_runtime/browser_pool.py (Playwright browser pool)
   - backend/app/services/verify_runtime/ui_probe.py (Playwright UI probe)
   - backend/app/services/verify_runtime/base.py (base probe class)
2. تأیید کنید که سیستم progress فعلی (SSE در analysis.py خط ۲۵۹) به WebSocket تغییر نکند.
3. تأیید کنید که تحلیل source code محدود به py/ts/tsx/js/jsx باقی بماند (analysis.py خطوط ۱۵۳-۱۵۸).
4. مستند کنید که ۸ chunk اجرای v2 در ادامه درخواست اصلی تعریف می‌شوند و این بخش فقط محدوده را مشخص می‌کند.

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: small

---

# 🔹 مرحله 52: فاز A — Task Type Classifier: تشخیص خودکار نوع تسک backend/frontend/fullstack/infra/docs/test/mixed

**Scope:** این بخش شامل پیاده‌سازی تابع _classify_task_type در iterative_orchestrator.py است که بر اساس prompt + target_files + AC نوع تسک را با regex/heuristic تشخیص می‌دهد. شامل ۷ نوع pure_backend, pure_frontend, fullstack, infra, docs_only, test_only, mixed_unknown. خروجی تابع یک رشته است. تشخیص بدون AI انجام می‌شود. task_type در verify_trace ثبت می‌شود. خارج از scope: weighting, probe validation, contradiction resolution, vision prompt, trace summary.
**Key terms:** _classify_task_type, iterative_orchestrator.py, WEIGHTS_BY_PROBE, verify_trace, pure_backend, pure_frontend, fullstack, infra, docs_only, test_only, mixed_unknown

**بخش مربوط از متن کاربر:**
```
فاز A — Task Type Classifier
اصول
یک تابع helper جدید: _classify_task_type(task) که بر اساس prompt + target_files + AC، نوع تسک را تشخیص می‌دهد.

دسته‌بندی‌ها
Type	معیار تشخیص	probe profile
pure_backend	همهٔ target_files با .py پایان دارند یا path شامل backend/ و در prompt اشاره‌ای به frontend/UI نیست	weight ui_interaction = 0.1، api_probe = 2.0
pure_frontend	همهٔ target_files با .tsx/.ts/.jsx/.js/.css پایان دارند و path شامل frontend/	weight ui_interaction = 2.0، api_probe = 0.3
fullstack	ترکیبی از backend و frontend	weight ui_interaction = 1.5، api_probe = 1.5
infra	فایل‌های Dockerfile, *.yml, *.yaml, .github/workflows/*	weight ui_interaction = 0، code_aware = 3.0
docs_only	فقط .md, .txt	همهٔ probes را skip، فقط code_aware
test_only	فقط فایل‌های test_*.py, *.test.tsx	weight ui_interaction = 0.3، test_probe = 3.0
mixed_unknown	تشخیص ناممکن	استفاده از weights پیش‌فرض (همان WEIGHTS_BY_PROBE موجود)

اقدامات
محل: backend/app/services/verify_runtime/iterative_orchestrator.py کنار WEIGHTS_BY_PROBE
تابع _classify_task_type(task) -> str که یکی از این 7 رشته برمی‌گرداند
منطق تشخیص باید fast باشد (regex ساده، نه AI call)
در trace ثبت شود: task_type_classified: pure_backend

معیارهای پذیرش فاز A
۱. تابع _classify_task_type در iterative_orchestrator.py موجود است
۲. تابع برای هر یک از ۷ نوع، رشتهٔ صحیح برمی‌گرداند (با تست واحد)
۳. task_type در verify_trace با phase=classify_task_type ثبت می‌شود
۴. تشخیص بدون فراخوانی AI انجام می‌شود (regex/heuristic)
```

## 🎯 هدف (خلاصه ساختاریافته)
افزودن تابع _classify_task_type به iterative_orchestrator.py برای تشخیص خودکار نوع تسک

## 📍 موقعیت دقیق در پروژه
_(فایل‌های دقیق توسط مجری شناسایی شوند — هیچ موقعیت مشخصی استخراج نشد)_

## 🧭 هدف اصلی پروژه (از یادداشت کاربر)
(کاربر یادداشتی ثبت نکرده است)

## 🔍 Context و وضعیت فعلی
فاز A — Task Type Classifier: تشخیص خودکار نوع تسک backend/frontend/fullstack/infra/docs/test/mixed. این بخش شامل پیاده‌سازی تابع _classify_task_type در iterative_orchestrator.py است که بر اساس prompt + target_files + AC نوع تسک را با regex/heuristic تشخیص می‌دهد. شامل ۷ نوع pure_backend, pure_frontend, fullstack, infra, docs_only, test_only, mixed_unknown. خروجی تابع یک رشته است. تشخیص بدون AI انجام می‌شود. task_type در verify_trace ثبت می‌شود. خارج از scope: weighting, probe validation, contradiction resolution, vision prompt, trace summary. دسته‌بندی‌ها: pure_backend (همهٔ target_files با .py پایان دارند یا path شامل backend/ و در prompt اشاره‌ای به frontend/UI نیست)، pure_frontend (همهٔ target_files با .tsx/.ts/.jsx/.js/.css پایان دارند و path شامل frontend/)، fullstack (ترکیبی از backend و frontend)، infra (فایل‌های Dockerfile, *.yml, *.yaml, .github/workflows/*)، docs_only (فقط .md, .txt)، test_only (فقط فایل‌های test_*.py, *.test.tsx)، mixed_unknown (تشخیص ناممکن). محل: backend/app/services/verify_runtime/iterative_orchestrator.py کنار WEIGHTS_BY_PROBE. تابع _classify_task_type(task) -> str که یکی از این ۷ رشته برمی‌گرداند. منطق تشخیص باید fast باشد (regex ساده، نه AI call). در trace ثبت شود: task_type_classified: pure_backend. کلیدواژه‌ها: _classify_task_type, iterative_orchestrator.py, WEIGHTS_BY_PROBE, verify_trace, pure_backend, pure_frontend, fullstack, infra, docs_only, test_only, mixed_unknown. شواهد در کد: فایل iterative_orchestrator.py خطوط ۴۶-۵۵ حاوی WEIGHTS_BY_PROBE است که weights پیش‌فرض را تعریف می‌کند. تابع aggregate_verdicts در خطوط ۶۹-۱۱۵ رأی‌گیری وزنی انجام می‌دهد. تابع iterative_verify_step در خطوط ۳۰۷-۳۸۳ نقطه ورود اصلی است و از context.append_trace برای ثبت trace استفاده می‌کند (خطوط ۳۳۳-۳۳۸, ۳۴۱-۳۴۶, ۳۵۵-۳۶۰, ۳۶۴-۳۶۸, ۳۷۸-۳۸۲). تابع _run_iteration_1 در خطوط ۳۹۱-۴۸۲ و _run_iteration_2 در خطوط ۴۸۵-۶۰۴ helpers iterations هستند. تابع _strong_model_judgment در خطوط ۱۵۶-۲۹۹ برای escalation استفاده می‌شود. تابع _model_available در خطوط ۱۲۳-۱۴۸ موجودیت مدل را بررسی می‌کند.

## ✅ معیار پذیرش (Acceptance Criteria) — رفتار-محور
**مهم:** هر AC رفتار قابل مشاهده را تعریف می‌کند، نه نام فایل/کلاس.
verify می‌تواند پیاده‌سازی متفاوت ولی هم‌ارز را قبول کند.

- [ ] هیچ تستی fail نمی‌شود (`npm run test` / `pytest`)
- [ ] linter بدون warning عبور می‌کند
- [ ] type-check موفق است (`tsc --noEmit` / `mypy`)

## 🪜 مراحل اجرایی پیشنهادی
1. ۱. در فایل backend/app/services/verify_runtime/iterative_orchestrator.py، پس از تعریف WEIGHTS_BY_PROBE (خطوط ۴۶-۵۵) و قبل از تابع _get_weight (خط ۵۸)، تابع جدید _classify_task_type(task) -> str را اضافه کن. ۲. منطق تابع: ورودی task یک دیکشنری با کلیدهای prompt, target_files, ac_text است. ابتدا target_files را بررسی کن: اگر همه فایل‌ها با .py ختم می‌شوند یا path شامل backend/ است و در prompt کلمه‌ای از frontend/UI نیست → pure_backend. اگر همه با .tsx/.ts/.jsx/.js/.css ختم می‌شوند و path شامل frontend/ است → pure_frontend. اگر ترکیبی از backend و frontend است → fullstack. اگر فایل‌های Dockerfile, *.yml, *.yaml, .github/workflows/* وجود دارد → infra. اگر فقط .md, .txt است → docs_only. اگر فقط test_*.py, *.test.tsx است → test_only. در غیر این صورت → mixed_unknown. ۳. از regex ساده برای تشخیص استفاده کن (مثلاً re.search(r'\.py$

## 📤 خروجی مورد انتظار
تغییر کد در فایل‌های مرتبط، commit یا PR جدید با پیام واضح، و عبور تمام معیارهای پذیرش.

## ⚠️ ریسک‌ها و موارد احتیاط
پیش از merge، تست‌های موجود اجرا شوند تا رگرشن ایجاد نشود.

## 🔗 وابستگی‌های تسکی
_(مستقل)_

## 🏷 دسته‌بندی
- نوع: refactor
- اولویت: critical
- تخمین زمان: medium

---

## ✅ معیارهای پذیرش کلی (همهٔ مراحل)
- [ ] همهٔ مراحل بالا با موفقیت پیاده‌سازی شده‌اند
- [ ] تست‌های موجود pass می‌شوند
- [ ] هیچ regression رخ نداده

## Acceptance Criteria

1. فایل behavioral_probe_layer.py در backend/app/services/verify_runtime/ ایجاد شود و کلاس BehavioralProbeOrchestrator را داشته باشد _(verify: static)_
2. کلاس BehavioralProbeResult با فیلدهای ac_id, probe_type, evidence, success, error_message در base.py یا behavioral_probe_layer.py تعریف شود _(verify: static)_
3. متد capture_screenshot به UIProbe در ui_probe.py اضافه شود که با Playwright screenshot بگیرد و base64 برگرداند _(verify: static)_
4. متد execute_http_probe به APIProbe در api_probe.py اضافه شود که HTTP request بزند و response JSON برگرداند _(verify: static)_
5. متد run_pytest_probe به TestProbe در test_probe.py اضافه شود که pytest را با marker اجرا کند و output را capture کند _(verify: static)_
6. متد run_behavioral_probes به Runner در runner.py اضافه شود که لیست ACها را گرفته و برای هر AC رفتاری probe مناسب را اجرا کند _(verify: static)_
7. فیلد behavioral_type: Optional[Literal['ui', 'api', 'backend']] به schema AC در ac_schema.py اضافه شود _(verify: static)_
8. تست behavioral probe layer در backend/tests/test_runtime_verify_stage3e.py اضافه شود که حداقل 3 سناریو (UI, API, backend) را تست کند _(verify: backend_test)_
9. یک AC UI رفتاری نمونه (مثلاً 'دکمه Login باید modal باز کند') با behavioral_type='ui' در تست کار کند و screenshot بگیرد _(verify: ui_interaction)_
10. یک AC API رفتاری نمونه (مثلاً 'GET /api/health → 200') با behavioral_type='api' در تست کار کند و response JSON برگرداند _(verify: api_response)_
11. مدل AcceptanceCriteria با فیلدهای text، verify_method، و verify_plan در backend/app/models/oversight_task.py تعریف شود. _(verify: static)_
12. فیلد acceptance_criteria در OversightTask از List[str] به List[AcceptanceCriteria] تغییر کند. _(verify: static)_
13. تابع generate_acceptance_criteria در oversight_strong_prompt.py struct جدید را خروجی بدهد. _(verify: static)_
14. ACهای قدیمی (رشته‌ای) در create_task با fallback به struct جدید تبدیل شوند. _(verify: backend_test)_
15. migration دیتابیس ستون acceptance_criteria را به JSON جدید به‌روزرسانی کند. _(verify: backend_test)_
16. تابع _normalize_ac در oversight_service.py پیاده‌سازی شود و یک str را به dict با کلیدهای text, verify_method='static', verify_plan=None, evidence_history=[] تبدیل کند. _(verify: static)_
17. یک task با AC string قدیمی بعد از load به ساختار جدید تبدیل شود (verify_method='static'). _(verify: backend_test)_
18. یک task با AC dict جدید بدون تغییر باقی بماند (فیلدهای موجود preserve شوند). _(verify: backend_test)_
19. در task_steps، هر step فیلدهای verify_method و verify_plan را داشته باشد. _(verify: static)_
20. migration یکباره در startup روی همه task‌های موجود از طریق _load_tasks اجرا شود. _(verify: static)_
21. system prompt در oversight_strong_prompt.py شامل دستورالعمل تولید verify_method و verify_plan برای هر AC باشد. _(verify: static)_
22. تابع _idea_to_prompt_multi_pass در oversight_service.py از system prompt جدید استفاده کند و خروجی AI را به درستی پارس کند. _(verify: static)_
23. برای AC با کلمات «کلیک، نمایش، صفحه، مودال، input»، verify_method = ui_interaction تولید شود. _(verify: backend_test)_
24. برای AC با کلمات «endpoint، API، status code، response»، verify_method = api_response تولید شود. _(verify: backend_test)_
25. برای AC مبهم یا ذهنی (مثل «ظاهر زیبا»)، verify_method = manual_only تولید شود. _(verify: backend_test)_
26. اگر AI نتوانست plan بدهد، fallback به static با grep_patterns خالی و files_hint خالی انجام شود. _(verify: backend_test)_
27. فایل `base.py` شامل dataclass `RuntimeProbeResult` با تمام فیلدهای مشخص‌شده (ac_id, method, status, evidence, duration_ms, error_message, timestamp) باشد. _(verify: static)_
28. فایل `runner.py` تابع `run_probes_for_task(task, watched)` را با استفاده از `asyncio.Semaphore(3)` برای محدودیت همزمانی پیاده‌سازی کند. _(verify: static)_
29. فایل `ui_probe.py` از `playwright.async_api` برای اجرای مرورگر و گرفتن screenshot استفاده کند. _(verify: static)_
30. فایل `api_probe.py` از `httpx.AsyncClient` برای اجرای درخواست‌های HTTP و assert status_code و JSON schema استفاده کند. _(verify: static)_
31. فایل `test_probe.py` از `subprocess` برای اجرای `pytest --json-report` و parse خروجی JSON استفاده کند. _(verify: static)_
32. فایل `manual_probe.py` همیشه status='skipped' با پیام «نیاز به بازبینی دستی» برگرداند. _(verify: static)_
33. مدل WatchedProject در oversight_service.py دارای سه فیلد جدید frontend_base_url, backend_base_url, runtime_auth است _(verify: static)_
34. در UI تنظیمات پروژه (projects/[id]/page.tsx)، یک بخش جدید با inputهای URL فرانت و بک‌اند، dropdown نوع auth و دکمه تست اتصال وجود دارد _(verify: ui_interaction)_
35. زمانی که frontend_base_url یا backend_base_url تنظیم نشده باشد، probeهای ui و api وضعیت 'skipped' با پیام 'base URL تنظیم نشده' برمی‌گردانند _(verify: backend_test)_
36. ذخیره و بارگذاری config با فیلدهای جدید به درستی کار می‌کند (ذخیره frontend_base_url و بازیابی آن) _(verify: api_response)_
37. runtime_auth دارای schema معتبر است: type必须是 "cookie" یا "bearer" و value یک رشته است _(verify: static)_
38. در ابتدای تابع verify_task، run_probes_for_task با asyncio.wait_for timeout کلی فراخوانی شود _(verify: static)_
39. نتایج runtime به فرمت متنی ساختاریافته با method، status، evidence، duration و مشاهدات تبدیل شود _(verify: static)_
40. متن شواهد runtime به عنوان بخش جدید به prompt ارسالی به AI اضافه شود _(verify: static)_
41. system prompt شامل عبارت 'شواهد runtime بالاتر از تحلیل کد است' باشد _(verify: static)_
42. منطق override: اگر runtime failed و AI done → AI override به not_done با هشدار log _(verify: static)_
43. منطق override: اگر runtime passed و AI not_done → AI override به done _(verify: static)_
44. در صورت timeout کلی (asyncio.wait_for)، fallback به قضاوت صرف AI انجام شود _(verify: static)_
45. تست verify_task با task که همه probeها pass شدند → status=done _(verify: backend_test)_
46. تست verify_task با probe failed → AI override _(verify: backend_test)_
47. تست verify_task با probe error (timeout) → fallback به فقط AI _(verify: backend_test)_
48. فایل storage.py در backend/app/services/verify_runtime/ ایجاد شود و کلاس EvidenceStorage با متدهای save_evidence, get_evidence, cleanup_old_runs, check_size_limit, generate_manifest داشته باشد _(verify: static)_
49. ذخیره‌سازی فایل در مسیر storage/verify_evidence/<task_id>/<run_id>/ انجام شود و فایل‌های ac1_step1.png, ac1_step2.png, ac2_response.json, ac3_pytest.json پشتیبانی شوند _(verify: api_response)_
50. endpoint GET /api/oversight/tasks/{id}/evidence/{run_id}/{path:path} ایجاد شود و فایل را با authorization سرو کند _(verify: api_response)_
51. cleanup policy فقط 5 run آخر هر task را نگه دارد و runهای قدیمی‌تر حذف شوند _(verify: backend_test)_
52. size limit 50MB per run رعایت شود و screenshots به JPEG q=70 تبدیل شوند _(verify: backend_test)_
53. manifest.json در هر run ایجاد شود و لینک همه شواهد را شامل شود _(verify: static)_
54. بخش «📷 شواهد Runtime» در PDF خروجی برای هر AC یک کارت شامل متن AC، badge روش (UI/API/Test)، badge وضعیت (passed/failed) و شواهد مربوطه نمایش دهد. _(verify: static)_
55. برای AC با روش UI، تصویر screenshot به صورت inline در PDF قرار گیرد. _(verify: static)_
56. برای AC با روش API، JSON پاسخ truncated به 500 byte در <pre> نمایش داده شود. _(verify: static)_
57. برای AC با روش Test، stdout pytest truncated نمایش داده شود. _(verify: static)_
58. در پیام تلگرام، اگر هر probe failed باشد، خلاصه وضعیت هر AC با جزئیات (زمان پاسخ، status code، تعداد تست‌ها) ارسال شود. _(verify: static)_
59. لینک PDF پیوست در پیام تلگرام برای جزئیات کامل قرار گیرد. _(verify: static)_
60. بخش «🔬 آخرین verify runtime» در مودال جزئیات تسک (frontend/src/app/oversight/page.tsx) نمایش داده شود و برای هر AC یک ردیف شامل آیکون متد، وضعیت و دکمه «مشاهدهٔ evidence» داشته باشد. _(verify: ui_interaction)_
61. کلیک روی دکمه «مشاهدهٔ evidence» یک مودال دوم با سه تب Gallery, API, Test باز کند. _(verify: ui_interaction)_
62. تب Gallery اسکرین‌شات‌ها را با قابلیت lightbox نمایش دهد. _(verify: ui_interaction)_
63. تب API JSON را با syntax highlight نمایش دهد. _(verify: ui_interaction)_
64. تب Test stdout را در بلوک استایل ترمینال نمایش دهد. _(verify: ui_interaction)_
65. دکمه «🔬 Verify با Runtime» در مودال جزئیات تسک وجود داشته باشد و با کلیک روی آن، فرآیند verify با probeها شروع شود. _(verify: ui_interaction)_
66. در تنظیمات پروژه (frontend/src/app/settings/page.tsx)، بخش «Runtime Verify» با فیلدهای URL و auth اضافه شود. _(verify: ui_interaction)_
67. BrowserPool باید پس از ۵ دقیقه بیکاری، Playwright browser process را kill کند _(verify: static)_
68. Runner باید Semaphore با max_workers=3 داشته باشد تا حداکثر ۳ probe موازی اجرا شوند _(verify: static)_
69. per-probe timeoutها: ui=30s, api=10s, test=120s باید در runner.py تعریف شده باشند _(verify: static)_
70. circuit breaker باید پس از ۳ خطای متوالی probe، runtime را به مدت ۱۰ دقیقه غیرفعال کند _(verify: static)_
71. graceful degrade: اگر Playwright نصب نباشد، فقط static_probe فعال شود و warning لاگ شود _(verify: static)_
72. RUNTIME_VERIFY_ENABLED باید از .env خوانده شود و در config.py ذخیره گردد _(verify: static)_
73. test_static_probe.py باید با pytest اجرا شود و grep درست را pass و grep نادرست را fail کند — با استفاده از fixture known-good و known-bad _(verify: backend_test)_
74. test_ui_probe.py باید با یک HTML server محلی (http.server یا flask) و Playwright headless browser کار کند — screenshot بگیرد و نتیجه برگرداند _(verify: backend_test)_
75. test_api_probe.py باید با httpbin (https://httpbin.org یا container محلی) HTTP request بزند و status + schema چک کند _(verify: backend_test)_
76. test_test_probe.py باید pytest dummy را در subprocess با timeout اجرا کند و timeout را به درستی مدیریت کند _(verify: backend_test)_
77. test_runner.py باید orchestration را تست کند — هر probe که error داد، verify ادامه دهد (نه crash) _(verify: backend_test)_
78. test_runtime_integration.py باید verify_task را با همه probe‌ها end-to-end اجرا کند — با fixture known-good و known-bad _(verify: backend_test)_
79. هیچ test موجود fail نمی‌شود — اجرای pytest backend/tests/ قبل و بعد از تغییرات باید یکسان باشد _(verify: backend_test)_
80. type-check (mypy + tsc) بدون error اجرا شود _(verify: backend_test)_
81. محیط production (Render) با RUNTIME_VERIFY_ENABLED=false کاملاً مثل قبل کار می‌کند (graceful disable) _(verify: static)_
82. روی یک تسک 'known-good' (همه AC ها واقعاً پاس شده‌اند) → verify=done _(verify: backend_test)_
83. روی یک تسک 'known-bad' (UI AC شکست خورده) → AI نمی‌تواند آن را done اعلام کند (runtime override) _(verify: backend_test)_
84. روی یک تسک با کد درست ولی deploy نشده → runtime می‌گوید fail (چون probe می‌رود به URL واقعی، نه به کد محلی) _(verify: backend_test)_
85. فایل backend/app/services/verify_runtime/inspector_probe.py باید وجود داشته باشد و کلاس InspectorProbe را تعریف کند که از BaseProbe ارث‌بری کند. _(verify: static)_
86. InspectorProbe باید متد run() داشته باشد که با Playwright صفحه را باز کند، screenshot بگیرد، console logs جمع کند و با Vision AI تحلیل کند. _(verify: static)_
87. InspectorProbe باید یک inspector_session جدید با عنوان «🤖 auto-verify · {timestamp}» از طریق InspectorBridge ایجاد کند. _(verify: static)_
88. پس از اتمام verify، InspectorProbe باید از TelegramComposer برای ارسال بسته کامل (گزارش + screenshot‌ها + پرامپت) به تلگرام استفاده کند. _(verify: static)_
89. پس از موفقیت ارسال تلگرام، screenshot‌های موقت باید از دیسک حذف شوند. _(verify: static)_
90. InspectorProbe باید در runner.py (فایل backend/app/services/verify_runtime/runner.py) ثبت شود تا در فرآیند verify خودکار شناسایی شود. _(verify: static)_
91. کلاس InspectorProbe باید در __init__.py پکیج verify_runtime export شود. _(verify: static)_
92. تابع `analyze_screenshot` در `backend/app/services/verify_runtime/vision_helper.py` ایجاد شود و امضای دقیق async def analyze_screenshot(screenshot_path: str, context: Dict[str, Any], verify_model_id: Optional[str] = None) -> Dict[str, Any] را داشته باشد _(verify: static)_
93. مرحله 1 fallback: تابع `describe_screenshot_with_vision` از `oversight_inspector_bridge.py` (خط 44) فراخوانی شود و خروجی آن شامل description, ui_elements, error_signals, source='vision_<model>', raw باشد _(verify: static)_
94. مرحله 2 fallback: در صورت خطا در مرحله 1، fallback به verify_model (text-only) با context شامل url, console_logs, backend_logs, html_excerpt انجام شود و source='fallback_text_only' باشد _(verify: static)_
95. مرحله 3 fallback: در صورت شکست هر دو مرحله، تابع با source='none' و description=None بازگردد (graceful degrade) _(verify: static)_
96. تابع `analyze_screenshot` توسط `inspector_probe.py` استفاده شود و کد تکراری تحلیل اسکرین‌شات از آن حذف شود _(verify: static)_
97. تست‌های unit برای هر سه سناریوی fallback در `backend/tests/test_runtime_verify_stage3a.py` یا فایل تست جدید اضافه شود _(verify: backend_test)_
98. محدودیت 30 تایی در تابع generate_mega_bundle_report حذف شود و گزارش‌ها بتوانند بیش از 30 آیتم را شامل شوند. _(verify: static)_
99. cap 30-step در تابع generate_prompt حذف شود و الگوهای Bug/Fix/Gap/Chunk به پرامپت اضافه شوند. _(verify: static)_
100. دکمه‌های compare-verify در oversight_verifier.py به‌درستی کار کنند و خطا ندهند. _(verify: api_response)_
101. تست‌های مربوطه در backend/tests/ با موفقیت پاس شوند. _(verify: backend_test)_
102. برای هر task_step، یک probe مجزا با فیلدهای screenshot, vision_result, console_logs, backend_logs, frontend_url, backend_urls ایجاد شود. _(verify: static)_
103. پس از verify غیر-done، task.prompt قدیمی در prompt_history بایگانی شود و task.prompt = followup_prompt قرار گیرد. _(verify: static)_
104. endpoint POST /api/oversight/tasks/{task_id}/revert-prompt موجود باشد و prompt_history[last] را به task.prompt برگرداند. _(verify: api_response)_
105. در InspectorBridge.tsx، یک کشوی «نسخه‌های قدیمی» نمایش داده شود که لیست prompt_history را نشان دهد. _(verify: ui_interaction)_
106. دکمه «کپی پرامپت» در InspectorBridge.tsx همیشه task.prompt فعلی را کپی کند. _(verify: ui_interaction)_
107. تابع generate_mega_bundle فایل mega-bundle.html شامل raw_idea, checklist, پرامپت قدیم/جدید, همه probeها, assertion‌ها و AI verifier output تولید کند. _(verify: static)_
108. فایل mega-bundle.html در storage ذخیره شود و قابل دانلود باشد. _(verify: api_response)_
109. فیکس ۱: network_calls در evidence inspector_probe باید شامل درخواست‌های شبکه واقعی باشد (نه خالی). _(verify: static)_
110. فیکس ۲: _infer_route_for_step باید route را از ac_text یا step_title استخراج کند اگر inferred_route None باشد. _(verify: static)_
111. فیکس ۳: endpoint POST /api/oversight/revert/{session_id} باید وجود داشته باشد و از revert_prompt_from_history استفاده کند. _(verify: api_response)_
112. frontend oversight page باید step probe status را با رنگ‌های مناسب نمایش دهد (سبز برای passed، قرمز برای failed، زرد برای error، خاکستری برای skipped). _(verify: ui_interaction)_
113. notification_service.py باید screenshots از evidence را به عنوان photo ارسال کند. _(verify: static)_
114. متن پیام نوتیفیکیشن تلگرام شامل خلاصه چک‌لیست به‌روز شده مراحل تسک است (نه فقط در فایل ضمیمه). _(verify: static)_
115. خروجی bundle به فرمت PDF است (نه HTML) و با viewer داخلی Telegram روی Android باز می‌شود. _(verify: static)_
116. vision prompt صریحاً از مدل می‌پرسد که آیا feature مورد نظر AC در صفحه وجود دارد یا نه. _(verify: static)_
117. تشخیص vision (YES/NO) مستقیماً روی نتیجه pass/fail probe تأثیر می‌گذارد (اگر NO باشد، probe fail می‌شود). _(verify: static)_
118. تغییرات در منطق اصلی تسک، دیتابیس یا سایر کانال‌های نوتیفیکیشن اعمال نشده است (خارج از scope). _(verify: static)_
119. تابع build_verify_checklist_message باید در صورت وجود task_steps، بلوک چک‌لیست با فرمت مشخص (ایموجی وضعیت، درصد پیشرفت، توضیحات باقی‌مانده) تولید کند. _(verify: static)_
120. بلوک چک‌لیست باید قبل از اطلاعات streak و attachment در msg_text قرار گیرد. _(verify: static)_
121. حداکثر طول بلوک چک‌لیست 700 کاراکتر باشد و در صورت تجاوز، با '…' در آخرین مرحله trim شود. _(verify: static)_
122. در صورت task_steps خالی یا malformed، fallback به نسخه فعلی (چک‌لیست AC) انجام شود. _(verify: static)_
123. تابع `build_mega_bundle_pdf` در `backend/app/services/oversight_mega_bundle.py` ایجاد شود و محتوای ۱۰ بخش bundle را با همان الگوی فونت و RTL موجود در `build_verify_report_pdf` به PDF تبدیل کند. _(verify: static)_
124. تابع `_send_mega_bundle` در `backend/app/services/oversight_verifier.py` به‌جای `build_mega_bundle_md` از `build_mega_bundle_pdf` استفاده کند و filename به `bundle_{task_id[:12]}_{ts}.pdf` تغییر کند. _(verify: static)_
125. در صورت شکست در ساخت PDF، fallback به HTML (همان رفتار قبلی) با log warning انجام شود. _(verify: static)_
126. محدودیت حجم 5MB در تابع `build_mega_bundle_pdf` اعمال شود و در صورت تجاوز، ValueError پرتاب کند. _(verify: static)_
127. فونت فارسی (Vazir یا Tahoma) در PDF پشتیبانی شود و RTL support فعال باشد. _(verify: static)_
128. تابع analyze_screenshot در vision_helper.py باید فیلدهای feature_present (با مقادیر yes/no/unclear) و feature_reason (رشته توضیح) را در خروجی خود برگرداند _(verify: static)_
129. در inspector_probe.py، اگر حداقل یکی از screenshots دارای vision_feature_present === 'no' باشد، probe status باید PROBE_STATUS_FAILED شود و یک assertion جدید با expectation حاوی ac_text و reason مناسب به assertion_results اضافه شود _(verify: static)_
130. در oversight_mega_bundle.py، فیلدهای feature_present و feature_reason از vision result هر شات در حلقه شواهد دانه‌به‌دانه استخراج و به خروجی mega-bundle اضافه شوند _(verify: static)_
131. در frontend/src/app/oversight/page.tsx، اگر vision_feature_present === 'no' باشد، یک علامت قرمز یا متن هشدار مانند '🔴 feature dynamic ساخته نشده (vision detection)' نمایش داده شود _(verify: static)_
132. مقادیر 'unclear' و 'yes' برای feature_present نباید تأثیری بر وضعیت pass/fail probe داشته باشند — فقط 'no' قطعی باعث fail شود _(verify: static)_
133. هیچ تغییری در سایر بخش‌های verify (Phase 1, Phase 2, بازرس دستی)، منطق navigate، console error، و رفتار در صورت source='none' (عدم دسترسی به vision) ایجاد نشود _(verify: static)_
134. ماژول form_interaction باید قابلیت پر کردن خودکار فرم‌های ثبت‌نام و ورود را داشته باشد _(verify: static)_
135. ماژول auth_handler باید از JWT Token پشتیبانی کند (ذخیره، ارسال در هدر، refresh) _(verify: static)_
136. ماژول auth_handler باید از Session-based auth (کوکی‌ها) پشتیبانی کند _(verify: static)_
137. capability_detector باید نوع مرورگر (Chrome, Firefox, Safari, Edge) را تشخیص دهد _(verify: static)_
138. capability_detector باید قابلیت‌های JavaScript (WebGL, WebRTC, Service Workers) را تشخیص دهد _(verify: static)_
139. تمام تغییرات باید backward-compatible باشند — تست‌های موجود Phase 1 و 2 نباید شکسته شوند _(verify: backend_test)_
140. تست‌های واحد برای ماژول‌های جدید form_interaction و auth_handler نوشته شوند _(verify: backend_test)_
141. بخش 'Runtime Verify Layer — Phase 1 & 2 Summary' به فایل docs/ARCHITECTURE.md اضافه شود _(verify: static)_
142. تمام کلیدواژه‌های ذکر شده در متن کاربر (inspector_probe.py, vision_helper.py, inspector_session, TTL cleanup, startup recovery, telegram screenshot+followup, Per-step probes, Network capture, Step-aware AI verifier prompt, prompt_history, apply_followup_as_new_prompt, revert endpoint, mega-bundle, PDF, HTML, چک‌لیست, caption تلگرام, Bundle PDF, feature_present, pass/fail flip) در مستندات ذکر شوند _(verify: static)_
143. هیچ تغییری در کدهای موجود ایجاد نشود — این تسک صرفاً مستندسازی است _(verify: static)_
144. مستندات شامل دیاگرام جریان داده بین کامپوننت‌های Phase 1 و 2 باشد (اختیاری — با استفاده از Mermaid یا متن ساده) _(verify: manual_only)_
145. متد interact_with_element در ui_probe.py باید بتواند روی selector کلیک کند و نتیجه (باز شدن modal) را تأیید کند — مشابه سناریوی «کلیک روی selector_hint و چک کردن modal/result» که در متن کاربر ذکر شده _(verify: backend_test)_
146. متد interact_with_element در ui_probe.py باید بتواند در یک فیلد متن تایپ کند و فرم را submit کند — مشابه سناریوی «وقتی فرم لاگین پر شود و submit شود، کاربر به داشبورد می‌رود» که در متن کاربر ذکر شده _(verify: backend_test)_
147. متد handle_authentication در navigation_helper.py باید بعد از navigate به /admin/dashboard، ریدایرکت به /login را تشخیص دهد، credentials را از config بخواند، فرم لاگین را پر کند و submit کند، و سپس دوباره به /admin/dashboard navigate کند — مشابه مشکلی که در system probe رخ داد و vision گفت «صفحه login می‌بینم» _(verify: backend_test)_
148. متد verify_acceptance_criteria در code_aware_verifier.py باید AC هایی که شامل submit فرم هستند را تشخیص دهد و با استفاده از interact_with_element اجرا کند — مشکل AC هایی که نیاز به submit فرم دارند و نمی‌توانند تست شوند _(verify: backend_test)_
149. فیلدهای auth_username و auth_password به Settings در backend/app/core/config.py اضافه شوند و در navigation_helper.py قابل دسترسی باشند _(verify: static)_
150. تشخیص feature_present در vision_helper.py با تعامل و تأیید نتیجه بهبود یابد تا false-positive کاهش یابد — مشکل ۴۰٪ false-positive که در متن کاربر ذکر شده _(verify: backend_test)_
151. تابع _execute_ui_step باید تمام 16 action تعریف شده در SUPPORTED_ACTIONS را پشتیبانی کند و خروجی استاندارد {step_idx, action, selector, value, success, duration_ms, message, error, screenshot_label} برگرداند. _(verify: static)_
152. execution loop در _run_inspector_inner باید ui_steps را به ترتیب اجرا کند و در صورت شکست هر step (غیر از assert steps)، probe overall failed برگرداند. _(verify: static)_
153. inspector_probe باید cookie/bearer auth را قبل از navigate اعمال کند و auto-detect login redirect را پشتیبانی کند. _(verify: static)_
154. ac_enricher.py باید برای method=ui_interaction یک sequence 3-8 مرحله‌ای تولید کند با استفاده از data-testid برای selectorها. _(verify: static)_
155. Enhanced Feature Detection باید screenshot قبل و بعد از interaction بگیرد و Vision آنالیز diff انجام دهد. _(verify: static)_
156. کلاس AuthRecipe در backend/app/services/verify_runtime/auth_recipe.py ایجاد شود و ساختار recipe را parse کند _(verify: static)_
157. فیلد runtime_auth_recipe به کلاس BaseProbe در base.py اضافه شود _(verify: static)_
158. runner.py قبل از اجرای هر probe، auth recipe را اجرا کند _(verify: static)_
159. storage.py متدهای save_storage_state و load_storage_state با پشتیبانی از TTL داشته باشد _(verify: static)_
160. مقادیر TEST_EMAIL و TEST_PASSWORD از environment variables خوانده شوند _(verify: static)_
161. تابع obtain_or_refresh_storage_state در auth_runner.py ایجاد شود و در صورت نبود runtime_auth_recipe، None برگرداند. _(verify: static)_
162. توابع _encrypt_storage و _decrypt_storage با AES-GCM پیاده‌سازی شوند و از env OVERSIGHT_AUTH_KEY استفاده کنند. _(verify: static)_
163. در inspector_probe.py، در صورت وجود ctx.storage_state، browser context با storage_state ساخته شود. _(verify: static)_
164. در oversight_verifier.py، تابع _verify_task قبل از ساخت ProbeContext از obtain_or_refresh_storage_state استفاده کند. _(verify: static)_
165. مکانیزم شمارش login_failed_count و غیرفعال‌سازی موقت recipe پس از ۳ شکست متوالی پیاده‌سازی شود. _(verify: static)_
166. ProbeContext در base.py دارای فیلد storage_state از نوع Optional[dict] باشد _(verify: static)_
167. runner.py storage_state را به build_probe_context ارسال کند _(verify: static)_
168. _MAX_SCREENSHOTS در inspector_probe.py برابر 5 باشد _(verify: static)_
169. _MAX_UI_STEPS در inspector_probe.py برابر 12 باشد _(verify: static)_
170. تشخیص redirect به /login در _run_inspector_inner پیاده‌سازی شده باشد و auth_required در evidence ذخیره شود _(verify: static)_
171. before/after screenshot pairs برای interaction‌ها گرفته شود (screenshot با label "before_interaction" و "after_interaction") _(verify: static)_
172. expected_api_calls از plan خوانده شده و با network_calls مقایسه شود و نتیجه در assertion_results ذخیره شود _(verify: static)_
173. SmartNavigation باید بتواند مسیر SPA را تشخیص دهد و به مسیر واقعی نگاشت کند — مثلاً /users/123 را به /users/[id] تبدیل کند _(verify: static)_
174. BackendLogProbe باید بتواند به endpoint لاگ بک‌اند متصل شود و لاگ‌های session جاری را فیلتر کند _(verify: static)_
175. CodeAwareVerifier باید بتواند کد را تحلیل استاتیک کند و missing implementations را تشخیص دهد _(verify: static)_
176. runner.py باید سه مؤلفه جدید را در action loop یکپارچه کند — SmartNavigation قبل از navigate، BackendLogProbe همزمان با actions، CodeAwareVerifier بعد از actions _(verify: static)_
177. SmartNavigation باید fallback به navigate مستقیم در صورت عدم تطابق مسیر داشته باشد _(verify: static)_
178. route guessing برای تسک trading-system باید بتواند URL های /routing-diagram و /charts را بدون 404 پیدا کند _(verify: ui_interaction)_
179. probe مخصوص backend-heavy tasks برای DebateAttachment باید endpointهای مرتبط را با API calls تست کند و شواهد runtime معتبر تولید کند _(verify: api_response)_
180. Render logs باید با فیلتر بر اساس target file paths و endpoint calls استفاده شوند _(verify: static)_
181. auto-verify باید از inspector chat infrastructure برای استفاده از لاگ‌های backend و console ذخیره شده استفاده کند _(verify: static)_
182. تغییرات نباید backward compatibility را بشکند — تست‌های موجود verify runtime باید پاس شوند _(verify: backend_test)_
183. SmartNavigationProbe باید بتواند با خواندن nav menu صفحه home، لینک مرتبط با feature keyword را پیدا کند و URL آن را برگرداند _(verify: backend_test)_
184. SmartNavigationProbe باید از AI (claude_service یا openai_service) برای تصمیم‌گیری درباره بهترین لینک استفاده کند _(verify: static)_
185. BackendLogProbe باید لاگ‌های Render را بر اساس target_files تسک فیلتر کند _(verify: backend_test)_
186. BackendLogProbe باید AC keywords را در لاگ‌های فیلتر شده جستجو کند و خروجی {'deployed': bool, 'called': bool, 'evidence': List[str]} برگرداند _(verify: backend_test)_
187. CodeAwareVerifier باید برای هر AC جداگانه بررسی کند که آیا diff اخیر commit آن AC را پیاده کرده یا نه _(verify: backend_test)_
188. CodeAwareVerifier باید از GitHub API موجود در github_pr_service.py برای دریافت diff استفاده کند (بدون کلون محلی) _(verify: static)_
189. Runner باید برای تسک‌های backend-heavy از BackendLogProbe استفاده کند و برای ناوبری از SmartNavigationProbe _(verify: static)_
190. نتایج probeهای جدید باید در storage ذخیره شوند _(verify: static)_
191. Smart Navigation Probe: وقتی AC route مستقیم ندارد، تابع pick_nav_link_for_ac در navigation_helper.py لینک مناسب را از navigation bar با AI انتخاب کند و نتیجه در storage.py ذخیره شود. _(verify: static)_
192. Backend Log Probe: فایل backend_log_probe.py شامل تابع run_backend_log_probe باشد که لاگ‌های Render را از طریق API خوانده و با analyze_backend_logs_for_ac تحلیل کند. _(verify: static)_
193. Code-aware Verifier: فایل code_aware_verifier.py شامل تابع analyze_commits_per_ac باشد که با GitHub API کامیت‌های اخیر مرتبط با هر AC را بررسی کند. _(verify: static)_
194. Task Type Routing: تابع _classify_task_type در oversight_verifier.py تسک‌ها را به UI یا backend دسته‌بندی کرده و probe مناسب dispatch کند. _(verify: static)_
195. همه probeهای جدید graceful degrade داشته باشند: در صورت failure هر بخش، verify ادامه یابد و خطا در storage ثبت شود. _(verify: static)_
196. تابع run_ui_probes با پشتیبانی Smart Navigation فراخوانی شود و نتایج به runtime_probe_results اضافه گردد _(verify: static)_
197. برای task_type='backend' یا 'mixed'، حلقه روی acceptance_criteria اجرا شود _(verify: static)_
198. تابع _is_backend_ac برای هر AC قبل از اجرای run_backend_log_probe فراخوانی شود _(verify: static)_
199. برای task_type='unknown' هیچ پروبی اجرا نشود _(verify: static)_
200. تابع run_backend_log_probe با امضای (ac, ctx, ac_id, task) فراخوانی شود _(verify: static)_
201. فایل navigation_helper.py در verify_runtime/ ایجاد شده و کلاس SmartNavigationHelper با متد analyze_navigation_links(html, task_context) پیاده‌سازی شده باشد _(verify: static)_
202. فایل backend_log_probe.py در verify_runtime/ ایجاد شده و کلاس BackendLogProbe با متد analyze_backend_logs(backend_ac, log_stream_service) پیاده‌سازی شده باشد _(verify: static)_
203. فایل code_aware_verifier.py در verify_runtime/ ایجاد شده و کلاس CodeAwareVerifier با متد verify_code(ac, git_history) پیاده‌سازی شده باشد _(verify: static)_
204. در inspector_probe.py hook برای Smart Navigation در زمان بازدید از صفحه اضافه شده باشد _(verify: static)_
205. در runner.py task type‌های smart_nav, backend_log, code_aware به routing اضافه شده و به probeهای مربوطه mapping شده باشند _(verify: static)_
206. در oversight_verifier.py متد _classify_task_type پیاده‌سازی شده و hooks برای backend_log_probe و code_aware_verifier اضافه شده باشد _(verify: static)_
207. در oversight_mega_bundle.py سه سکشن جدید 8.1 (Smart Navigation Decisions), 8.2 (Backend Log Analysis), 8.3 (Code-aware Verdict) به ساختار bundle اضافه شده باشد _(verify: static)_
208. در frontend oversight/page.tsx سه آیکن جدید 🧭 (smart-nav), 📊 (backend-log), 🔍 (code-aware) با رنگ‌های متمایز در inline probe row نمایش داده شوند _(verify: static)_
209. per-probe AI cost cap حداکثر 2 call رعایت شده باشد (در هر سه پروب جدید) _(verify: static)_
210. per-task additional time max 90s رعایت شده باشد (در هر سه پروب جدید) _(verify: static)_
211. graceful fallback به Phase 3 behavior در صورت failure پیاده‌سازی شده باشد (در هر سه پروب جدید) _(verify: static)_
212. هیچ‌گونه credentials در خروجی پروب‌ها نشت پیدا نکند (بررسی عدم وجود password, token, api_key در خروجی) _(verify: static)_
213. اگر log_stream_service غیرفعال است، BackendLogProbe gracefully skip شود (بدون خطا) _(verify: static)_
214. تمامی فایل‌های scan_v5/ و verify_runtime/ برای ناهماهنگی‌های منطقی بررسی شوند. _(verify: static)_
215. حداقل ۳ باگ منطقی (شامل مثال trade) شناسایی و مستند شود. _(verify: static)_
216. گزارش Logic Audit در docs/AUDIT_REPORT.md ذخیره شود. _(verify: static)_
217. هیچ تغییری در کد یا UI ایجاد نشود (صرفاً بازبینی). _(verify: static)_
218. کلاس ScanPillar با چهار مقدار COVERAGE, CHANGE_AWARE, BEHAVIOR_CENTRIC, LOGIC_AWARE در backend/app/services/scan_v5/__init__.py تعریف شود _(verify: static)_
219. کلاس ScanContext با فیلدهای inventory, delta, purpose, coherence, outcome, notification_audit, stale_detection در __init__.py تعریف شود _(verify: static)_
220. scan_bundle.py متد _apply_pillar_coverage() را برای پشتیبانی از R3 (پوشش ریز تا درشت) پیاده‌سازی کند _(verify: static)_
221. scan_bundle.py متد _apply_pillar_change_awareness() را برای پشتیبانی از R7 (تغییر-آگاهی) پیاده‌سازی کند _(verify: static)_
222. scan_bundle.py متد _apply_pillar_behavior_centric() را برای پشتیبانی از R9, R13 (رفتار-محوری) پیاده‌سازی کند _(verify: static)_
223. scan_bundle.py متد _apply_pillar_logic_awareness() را برای پشتیبانی از R10, R11 (logic awareness) پیاده‌سازی کند _(verify: static)_
224. comprehensive_inventory.py سطوح inventory (line-level, function-level, file-level, module-level, system-level) را پشتیبانی کند _(verify: static)_
225. delta_analyzer.py قابلیت تشخیص features قدیمی و dead options (R8) را داشته باشد _(verify: static)_
226. coherence_analyzer.py قابلیت تشخیص componentهای منطقاً ناسازگار (R10) را داشته باشد _(verify: static)_
227. purpose_extractor.py قابلیت تولید AI explanation برای features ناشناخته (R8) را داشته باشد _(verify: static)_
228. ماژول comprehensive_inventory.py در مسیر backend/app/services/scan_v5/ ایجاد شده و شامل کلاس ComprehensiveInventory با متد scan_all_layers() است _(verify: static)_
229. ماژول purpose_extractor.py در مسیر backend/app/services/scan_v5/ ایجاد شده و شامل کلاس PurposeExtractor با متد extract_purpose() است _(verify: static)_
230. فیلدهای last_scan_inventory, last_scan_purpose_map, last_scan_at_v5 به مدل WatchedProject در backend/app/models/project.py اضافه شده‌اند _(verify: static)_
231. متد inventory_backend_endpoints() با AST parse حداقل ۵۰ endpoint را شناسایی می‌کند _(verify: static)_
232. متد inventory_notification_calls() با regex حداقل ۱۰ notify_event/send_telegram/bot.send_message را شناسایی می‌کند _(verify: static)_
233. متد inventory_ui_options() همه checkbox/slider/dropdown در UI را با cross-ref به WatchedProject fields شناسایی می‌کند _(verify: static)_
234. متد extract_purpose() برای ≥ 80% فایل‌های مهم purpose_map با creation_context تولید می‌کند _(verify: static)_
235. StaleDetector.detect_structural_stale() باید حداقل ۵ مورد structural stale روی پروژه واقعی شناسایی کند _(verify: backend_test)_
236. StaleDetector.detect_semantic_stale() باید حداقل ۳ مورد semantic stale و ۸ hidden-purpose option شناسایی کند _(verify: backend_test)_
237. GET /api/oversight/feature-inventory باید ۲۰۰ با لیست کامل inventory شامل دسته‌بندی‌های Settings, UI Buttons, Backend Endpoints, Env Vars برگرداند _(verify: api_response)_
238. Feature Inventory Panel در frontend/src/app/oversight/page.tsx باید با حداقل ۲۰ مدخل نمایش داده شود _(verify: ui_interaction)_
239. برای هر stale item باید یک task با AC رفتار-محور تولید شود (cleanup/audit/document) _(verify: static)_
240. hover روی هر مدخل در Feature Inventory Panel باید AI explanation کامل شامل name, what_it_does, when_added, current_status را نمایش دهد _(verify: ui_interaction)_
241. بعد از دو scan متوالی روی یک پروژه، delta با ۶ نوع (add, remove, modify, rename, move, signature-change) تشخیص داده شود — قابل تست با اجرای scan روی پروژه test و تغییر یک فایل بین دو scan _(verify: backend_test)_
242. اگر signature یک تابع تغییر کرد و ۳ caller دارد، حداقل ۱ task برای بررسی callerها تولید شود با badge '🔄 وابسته به تغییر' _(verify: backend_test)_
243. logical impact detection: اگر threshold از 0.65 به 0.8 تغییر کند، AI تحلیل کند که کدام componentهای dependent رفتار متفاوت نشان می‌دهند — نه فقط alert syntaxی _(verify: backend_test)_
244. bidirectional dependency: هم dependencies (forward) هم dependents (reverse) برای هر changed item در خروجی dependency_analyzer موجود باشد _(verify: static)_
245. فیلد prev_scan_state در مدل WatchedProject بعد از هر scan موفق به‌روزرسانی شود _(verify: backend_test)_
246. بعد از هر scan، یک inspector session با ≥ ۱۰ پیام (AI calls + actions + probes) ساخته شود _(verify: static)_
247. ≥ ۵ screenshot ذخیره شود _(verify: static)_
248. Telegram message + bundle PDF با همه‌ی screenshots و findings ارسال شود _(verify: static)_
249. در Inspector tab، session آرشیو شده دیده شود با badge '🔍 Scan' _(verify: ui_interaction)_
250. اگر runtime discovery فعال است، روی هر route یک screenshot + Vision analysis _(verify: static)_
251. coherence_analyzer.analyze_pipeline_coherence باید حداقل ۱ pipeline coherence issue برای پروژه فعلی شناسایی کند (با استفاده از purpose_inventory و interacting_with). _(verify: backend_test)_
252. anti_pattern_detector.detect_logical_anti_patterns باید حداقل ۲ logical anti-pattern (مانند magic threshold یا silent failure) در پروژه فعلی شناسایی کند. _(verify: backend_test)_
253. outcome_analyzer.audit_outcome_effectiveness باید برای یک پروژه trade فرضی با win-rate=30% و stated_purpose='earn profit'، effectiveness=LOW و priority=high برگرداند. _(verify: backend_test)_
254. task_consolidation_service باید بتواند task از نوع logic_audit با acceptance_criteria outcome-oriented (مثلاً 'بعد از این تغییر، win-rate باید ≥40% شود') و ai_explanation کامل تولید کند. _(verify: backend_test)_
255. hidden_requirements_discovery باید برای یک feature با creation_context خالی، از commit messages هدف معتبری استخراج کند و task از نوع document تولید کند. _(verify: backend_test)_
256. notification_inventory کامل برای تمام notify_event calls در notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py ایجاد شود. _(verify: static)_
257. حداقل ۲ task از نوع notification_audit با priority medium ایجاد شود. _(verify: static)_
258. caption template جدید برای scan_completed تعریف شود که شامل delta summary + logic audit findings + inspector session link + attachment با PDF کامل باشد. _(verify: static)_
259. فیلد WatchedProject.auto_task_notify_sound: bool = False به مدل پروژه اضافه شود. _(verify: static)_
260. فیلد WatchedProject.scan_notify_sound: bool = False به مدل پروژه اضافه شود. _(verify: static)_
261. silent=True برای auto-task و scan notifications در oversight_telegram_compose.py تنظیم شود. _(verify: static)_
262. بعد از یک scan تست، Telegram message + PDF received با همه فیلدهای تعریف شده در caption template جدید. _(verify: manual_only)_
263. ساختار AC غنی با فیلدهای behavior, acceptance_signal, business_intent, alternative_implementations, non_goals, false_positive_guard در هر سه مسیر (manual, auto, scan-generated) پیاده‌سازی شود _(verify: static)_
264. ساختار task_step غنی با فیلدهای behavior_observable, verification_hint, business_intent, non_goals در تابع _ai_plan_steps_from_idea پیاده‌سازی شود _(verify: static)_
265. Smart Checklist Mode با سه حالت auto/always/never به مدل WatchedProject اضافه شود _(verify: static)_
266. پرامپت‌ها در oversight_strong_prompt.py به‌روزرسانی شوند تا AC نام‌محور بد و AC رفتار-محور خوب تلقی شود _(verify: static)_
267. backward compatibility با ACهای قدیمی (فقط text) حفظ شود — ACهای قدیمی بدون فیلدهای جدید همچنان کار کنند _(verify: static)_
268. حالت auto در Smart Checklist Mode بر اساس پیچیدگی (≥3 stage → checklist، single-action → skip) تصمیم‌گیری کند _(verify: static)_
269. پرامپت تولید‌شده از خروجی‌های purpose_inventory, runtime_state, logic_audit_findings, notification_audit استفاده کند _(verify: static)_
270. بعد از scan: همه auto-tasks در UI چک‌لیست دارند (اگر mode=auto و پیچیده‌اند) _(verify: ui_interaction)_
271. caption تلگرام شامل همه فیلدهای مشخص‌شده (عنوان، business intent، چک‌لیست، logic concerns، وابستگی‌ها، outcome impact، لینک‌ها) _(verify: api_response)_
272. silent default = true (فیلدهای auto_task_notify_sound و scan_notify_sound پیش‌فرض False دارند) _(verify: static)_
273. scan_completed notification با Bundle PDF + Inspector session link ارسال شود _(verify: api_response)_
274. regression: تسک‌های دستی رفتار قبلی را حفظ کنند (بدون task_steps اجباری) _(verify: backend_test)_
275. در UI صفحه تنظیمات، ۴ تب با عناوین Coverage, Intelligence, Lifecycle, Notifications وجود دارد _(verify: ui_interaction)_
276. حالت scan_depth 'balanced' به‌عنوان پیش‌فرض جدید انتخاب شده است _(verify: ui_interaction)_
277. حالت scan_depth 'ultra' در dropdown موجود است _(verify: ui_interaction)_
278. هر گزینه در تنظیمات دارای آیکون ⓘ با tooltip شامل AI explanation است _(verify: ui_interaction)_
279. Feature Inventory Panel در صفحه تنظیمات قابل مشاهده و functional است _(verify: ui_interaction)_
280. backward compatibility: scan_depth قدیمی (quick, standard, deep, thorough) همچنان در dropdown موجود است _(verify: ui_interaction)_
281. فایل docs/PHASE_5_META_VALIDATION.md باید پس از اجرای iteration loop شامل لاگ‌های هر iteration با تاریخ، فاز جاری، نتیجه verify deep (done%) و لیست باگ‌های شناسایی‌شده باشد. _(verify: static)_
282. تابع run_iteration_loop در backend/app/services/verify_runtime/runner.py باید وجود داشته باشد و حداقل ۳ پارامتر (task_steps, max_iterations, callback) را بپذیرد. _(verify: static)_
283. منطق تشخیص false-positive و false-negative باید در backend/app/services/oversight_verifier.py پیاده‌سازی شده باشد. false-positive زمانی است که verify گفت done ولی کار واقعاً انجام نشده، false-negative زمانی است که verify گفت not_done ولی کار انجام شده. _(verify: static)_
284. خروجی نهایی باید شامل ۱۰ task_step باشد که هر کدام دارای فیلدهای behavior_observable و verification_hint هستند. این خروجی باید از backend/app/services/oversight_mega_bundle.py قابل تولید باشد. _(verify: static)_
285. پس از پیاده‌سازی همه فازها، verify deep این task را باید ≥ ۱۰/۱۰ done گزارش دهد. این معیار با اجرای دستی verify deep روی task نهایی قابل تست است. _(verify: manual_only)_
286. تمام فایل‌های پروژه (232 فایل) در inventory شناسایی و ثبت شوند — هیچ فایلی از قلم نیفتد _(verify: static)_
287. برای هر فایل، purpose (هدف) استخراج و ثبت شود — purpose نباید خالی باشد _(verify: static)_
288. تمام endpointهای API (مسیرهای موجود در backend/app/api/routes/) در inventory شناسایی و با method و purpose ثبت شوند _(verify: static)_
289. تمام کلاس‌های تعریف‌شده در پروژه (در فایل‌های models و services) با purpose شناسایی و ثبت شوند _(verify: static)_
290. گزارش مشروح inventory با قابلیت ارسال در تلگرام تولید شود — گزارش باید شامل چک‌لیست و پرامپت برای مراحل بعدی باشد _(verify: static)_
291. inventory تولیدشده به scan_bundle اضافه شود تا در bundleهای بعدی قابل استفاده باشد _(verify: static)_
292. هیچ آیتمی بدون purpose ثبت نشود — purpose باید حداقل 10 کاراکتر و معنادار باشد _(verify: static)_
293. خروجی inventory در قالب JSON ساختاریافته با فیلدهای file_path, type, purpose, dependencies, related_files ذخیره شود _(verify: static)_
294. verify v6 باید روی meta-test (همان bug) همهٔ ACها را به‌درستی done ببیند _(verify: backend_test)_
295. ۶ گپ بنیادی در فایل‌های code_aware_verifier.py, api_probe.py, runner.py, ac_schema.py, ac_enricher.py, backend_log_probe.py رفع شده باشند _(verify: static)_
296. ۲ بهبود اضافه (parallel verification و improved error messages) پیاده‌سازی شده باشند _(verify: static)_
297. همه تست‌های موجود در backend/tests/test_runtime_verify_*.py با موفقیت عبور کنند _(verify: backend_test)_
298. false negative روی ۴۰٪ تسک‌های backend/multi-step به صفر برسد _(verify: backend_test)_
299. هیچ تغییری در ۵ فاز قبلی ایجاد نشده باشد _(verify: static)_
300. فایل `backend/app/services/verify_runtime/context_builder.py` ایجاد شده و شامل دیتاکلاس `VerifyContext` با تمام فیلدهای مشخص شده است _(verify: static)_
301. تابع `async def build_verify_context(task, watched, *, config) -> VerifyContext` در فایل context_builder.py پیاده‌سازی شده است _(verify: static)_
302. caps روی raw_idea_full (50KB) و prompt_full (100KB) اعمال می‌شود _(verify: static)_
303. repo_tree با cap 5000 و commits_recent با cap 50 پیاده‌سازی شده است _(verify: static)_
304. کش‌های in-memory (file_content_cache, file_grep_cache) و شمارنده‌های observability (files_fetched_count, grep_calls_count, ai_calls_count) در دیتاکلاس تعریف شده‌اند _(verify: static)_
305. VerifyContext و build_verify_context از `backend/app/services/verify_runtime/__init__.py` export شده‌اند _(verify: static)_
306. تابع `fetch_file_content` باید محتوای فایل را از API گیت‌هاب (GET /repos/{owner}/{repo}/contents/{path}?ref={ref}) بخواند و base64 decode کند _(verify: backend_test)_
307. تابع `fetch_file_content` باید فایل‌های بزرگتر از 500KB را skip کند و None برگرداند _(verify: backend_test)_
308. تابع `fetch_file_content` باید caching روی key=f"{path}@{ref}" پیاده‌سازی کند _(verify: backend_test)_
309. تابع `grep_token_in_files` باید با regex `re.finditer(re.escape(token), content, re.IGNORECASE)` جستجو کند و خروجی `[{path, line_number, snippet, before_lines, after_lines}, ...]` برگرداند _(verify: backend_test)_
310. تابع `grep_token_in_files` باید cap per file (max_matches_per_file=5) را رعایت کند _(verify: backend_test)_
311. تابع `smart_grep_for_ac` باید identifierها را از ac_text با `extract_identifiers` استخراج کند و top-K=15 identifier (sorted by specificity) را در همهٔ target_files جستجو کند _(verify: backend_test)_
312. تابع `extract_identifiers` باید snake_case, camelCase, PascalCase, dunder, function_call, file_path را تشخیص دهد و stop-words و کلمات generic را فیلتر کند _(verify: backend_test)_
313. مثال‌های concrete در درخواست کاربر باید پاس شوند: ورودی فارسی → ['view_preferences', 'WatchedProject']، ورودی انگلیسی → ['useViewPrefs', 'fetching', 'preferences']، ورودی mixed → ['_record_title_change', 'oversight_service']، کلمات generic → [] _(verify: backend_test)_
314. تابع `_phase_a_basename_match` باید با دریافت `ac`, `target_files`, `context`، نام پایه فایل‌ها را تطبیق دهد و `ProbeResult` برگرداند. _(verify: static)_
315. تابع `analyze_acs_with_content_grep` باید چهار فاز را به‌ترتیب اجرا کند و در صورت `done=True` در هر فاز، early-exit کند. _(verify: static)_
316. هیچ تغییر منطقی در فرآیند فعلی ایجاد نشود و فقط نام‌گذاری توابع مشخص‌تر گردد. _(verify: static)_
317. تمامی توابع جدید در `backend/app/services/verify_runtime/__init__.py` export شوند. _(verify: static)_
318. تست‌های واحد برای هر چهار فاز و orchestrator در فایل تست مربوطه اضافه شود. _(verify: backend_test)_
319. فایل backend/app/services/verify_runtime/iterative_orchestrator.py ایجاد شود و شامل dataclass ProbeResult با تمام فیلدهای مشخص شده (probe_name, verdict, confidence, evidence, error, elapsed_ms) باشد _(verify: static)_
320. تابع async iterative_verify_step با signature دقیق (step: Dict, context: VerifyContext, *, max_iterations: int = 3) -> Tuple[ProbeResult, List[ProbeResult]] پیاده‌سازی شود _(verify: static)_
321. Iteration 1 شامل vision probe (شرطی بر اساس classification), code_aware probe, content_grep probe با smart_grep_for_ac روی target_files, playwright probe (شرطی) باشد و آستانه confidence ≥ 0.8 برای finalize _(verify: static)_
322. Iteration 2 شامل گسترش file scope تا 50 فایل اضافی با filter extensions (py/tsx/ts/jsx/js) و path overlap با AC text، top-25 identifiers، AI rerun، آستانه confidence ≥ 0.7 باشد _(verify: static)_
323. Iteration 3 شامل تابع _strong_model_judgment با زنجیره gpt-4o → claude-opus-4-7 → claude-sonnet-4-6 → fallback به pick_best_extraction_model از models_registry باشد و ورودی شامل AC کامل + evidence + snippets (cap 50KB) + repo_tree + task.prompt (cap 50KB) _(verify: static)_
324. import از backend/app/core/models_registry برای pick_best_extraction_model, MODEL_REGISTRY, DEFAULT_EXTRACTION_MODEL_ID انجام شود _(verify: static)_
325. WEIGHTS_BY_PROBE باید شامل تمام 8 کلید مشخص شده با مقادیر دقیق باشد _(verify: static)_
326. aggregate_verdicts با لیست خالی باید ProbeResult با verdict='unclear' و confidence=0.0 برگرداند _(verify: backend_test)_
327. aggregate_verdicts با یک پروب done با weight=1.0 و confidence=1.0 باید verdict='done' و confidence=1.0 برگرداند _(verify: backend_test)_
328. aggregate_verdicts باید نتایج با error=True را نادیده بگیرد _(verify: backend_test)_
329. aggregate_verdicts باید حداکثر 10 شاهد برگرداند _(verify: backend_test)_
330. aggregate_verdicts باید وزن vision_backend را 0 در نظر بگیرد _(verify: backend_test)_
331. Chunk 1: فایل context_builder.py ایجاد شود و شامل کلاس‌های VerifyConfig, VerifyContext و تابع build_verify_context باشد _(verify: static)_
332. Chunk 1: unit test برای context_builder.py در backend/tests/test_verify_v6/test_context_builder.py وجود داشته باشد و پاس شود _(verify: backend_test)_
333. Chunk 2: فایل code_content_searcher.py شامل ۴ تابع search_by_regex, search_by_ast, search_by_import, search_by_identifier باشد _(verify: static)_
334. Chunk 2: تابع extract_identifiers با پارامتر stop_words در code_content_searcher.py وجود داشته باشد _(verify: static)_
335. Chunk 3: فایل iterative_orchestrator.py شامل کلاس ProbeResult و توابع aggregate_verdicts, iterative_verify_step, _strong_model_judgment باشد _(verify: static)_
336. Chunk 4: فیلد ac_verify_cache به مدل OversightTask اضافه شده باشد _(verify: static)_
337. Chunk 5: فایل code_aware_verifier.py شامل ۴ phase صریح (phase1 تا phase4) باشد _(verify: static)_
338. Chunk 6: متد _classify_step_for_probe در oversight_verifier.py بازنویسی شده و از iterative_orchestrator استفاده کند _(verify: static)_
339. Chunk 6: flag verify_v6 برای فعال/غیرفعال کردن سیستم جدید وجود داشته باشد _(verify: static)_
340. Chunk 7: فیلدهای verify_trace, ac_probe_details, verify_version به VerificationReport اضافه شده باشد _(verify: static)_
341. Chunk 7: endpoint جدید برای گزارش‌های verify v6 در oversight.py اضافه شده باشد _(verify: api_response)_
342. Chunk 8: meta-test اجرا شده و ≥۱۱/۱۲ AC پاس شود _(verify: backend_test)_
343. هر chunk دارای commit جداگانه، type-check و push شده باشد _(verify: manual_only)_

## Task Steps

### Step 1: ایجاد لایه Runtime Verification برای اجرای Probe واقعی و جمع‌آوری شواهد اجرایی
**Status:** `done` (100%)
**Scope:** این بخش طراحی یک لایه جدید runtime verification را مشخص می‌کند که به جای خواندن استاتیک کد، برای هر Acceptance Criterion (AC) رفتاری یک probe واقعی اجرا می‌کند. شامل سه نوع probe: Playwright برای UI، HTTP برای API، pytest برای backend logic. خروجی هر probe شواهد runtime مانند screenshot، response JSON و pytest output است که به verify ارسال می‌شود. این لایه false-positive و false-negative را حذف می‌کند. خارج از scope: پیاده‌سازی جزئی probeها، طراحی دیتابیس، و logic تصمیم‌گیری verify.
**Excerpt:**
```
verify فعلی فقط کد را می‌خواند و حدس می‌زند؛ این layer جدید برای هر AC که ماهیتش رفتاری است، **یک probe واقعی** اجرا می‌کند (Playwright برای UI، HTTP برای API، pytest برای backend logic) و **شواهد runtime** (screenshot، response JSON، pytest output) به verify می‌دهد. در نتیجه verify دیگر false-positive («نشده» در حالی که شده) و false-negative («شده» در حالی که نشده) نمی‌دهد.
```

### Step 2: یکپارچه‌سازی Stage 5: نقطهٔ اتصال verify فعلی با AI و PDF و UI
**Status:** `done` (100%)
**Scope:** این بخش موقعیت دقیق فایل‌های مرتبط با Stage 5 (یکپارچه‌سازی) را مشخص می‌کند. شامل: oversight_verifier.py (نقطهٔ یکپارچه‌سازی)، oversight_strong_prompt.py (تولید AC)، oversight_service.py (ایجاد تسک)، oversight_verify_pdf.py (PDF)، frontend page.tsx (نمایش)، و پوشه‌های جدید verify_runtime/ و verify_evidence/. خارج از scope: پیاده‌سازی Stage 2/4/7/8 (فقط اشاره به نقاط ورودشان دارد). نکته حیاتی: این بخش صرفاً نقشهٔ راه فایل‌هاست و دستور اجرایی ندارد.
**Excerpt:**
```
## 📌 موقعیت دقیق در پروژه (فایل‌های مرتبط — مجری باید deep-read کند)
- `backend/app/services/oversight_verifier.py` — verify فعلی (grep + AI)
  → نقطهٔ یکپارچه‌سازی Stage 5
- `backend/app/services/oversight_strong_prompt.py` — تولید AC
  → نقطهٔ Stage 2 (AI verify_plan)
- `backend/app/services/oversight_service.py` — OversightTask + create_task
  → Stage 1 (schema migration)
- `backend/app/services/oversight_verify_pdf.py` — PDF فعلی
  → Stage 7 (embed evidence)
- `frontend/src/app/oversight/page.tsx` — UI تسک
  → Stage 8 (نمایش evidence)
- `frontend/src/app/projects/[id]/page.tsx` یا settings — تنظیمات watched
  → Stage 4 (base URLs)
- پوشهٔ جدید: `backend/app/services/verify_runtime/` — probe runners
- پوشهٔ جدید: `storage/verify_evidence/` — ذخیرهٔ screenshots/JSONs
```

### Step 3: تبدیل ساختار AC از رشته به struct با verify_method و verify_plan
**Status:** `done` (100%)
**Scope:** این بخش طراحی مفهومی جدیدی برای ساختار Acceptance Criteria (AC) ارائه می‌دهد که از یک رشته ساده به یک struct با فیلدهای text, verify_method, verify_plan تبدیل می‌شود. شامل پنج نوع verify_method (static, ui_interaction, api_response, backend_test, manual_only) و جایگزینی شواهد grep با runtime evidence (screenshot, JSON, pytest log) است. این بخش صرفاً مفهوم‌پردازی است و مراحل اجرایی بعداً در ادامه درخواست ذکر شده‌اند.
**Excerpt:**
```
## 🧠 معماری کلی (قبل از کد، این را بفهم)
### concept جدید: «verify_method» برای هر AC
هر AC الان فقط یک رشته است:
"وقتی روی دکمه X کلیک می‌کنم، مدال باز شود"

بعد از این feature، هر AC یک struct است:
```json
{
  "text": "وقتی روی دکمه X کلیک می‌کنم، مدال باز شود",
  "verify_method": "ui_interaction",
  "verify_plan": {
    "ui_steps": [
      {"action": "navigate", "url": "/oversight"},
      {"action": "wait_for_load_state", "state": "networkidle"},
      {"action": "click", "selector": "[data-testid='btn-x']"},
      {"action": "wait_for_selector", "selector": "[role='dialog']", "timeout_ms": 3000},
      {"action": "assert_visible", "selector": "[role='dialog']"}
    ]
  }
}
```
پنج نوع verify_method
static — کد grep (همان verify فعلی) — برای ACی مثل «فایل X وجود دارد»
ui_interaction — Playwright headless — برای ACی مثل «دکمه باز می‌شود»
api_response — HTTP request — برای ACی مثل «endpoint Y → 200 با field Z»
backend_test — pytest subprocess — برای ACی مثل «تست T pass شود»
manual_only — نمی‌توان خودکار تأیید کرد — verify فقط می‌گوید «نیاز به بازبینی دستی»
چه چیزی جایگزین شواهد grep می‌شود
verify فعلی به AI می‌گفت: «این کد را ببین، AC پاس می‌شود؟»
verify جدید می‌گوید: «این runtime evidence را ببین (screenshot، JSON، pytest log) — AC پاس می‌شود؟»

🪜 مراحل اجرایی (دقیقاً به این ترتیب — قبلی پیش‌نیاز بعدی است)
```

### Step 4: Schema migration برای AC ساختاریافته در OversightTask
**Status:** `done` (100%)
**Scope:** این مرحله شامل تغییر نوع فیلد acceptance_criteria در OversightTask از List[str] به List[Union[str, Dict]]، ایجاد helper _normalize_ac برای تبدیل یکتا به ساختار {text, verify_method, verify_plan, evidence_history}، افزودن فیلدهای verify_method و verify_plan به هر step در task_steps، و اجرای migration یکبار در startup روی همه task‌های موجود است. backward compatibility با پیش‌فرض verify_method="static" برای ACهای قدیمی str حفظ می‌شود. فایل‌های درگیر: oversight_service.py, oversight_strong_prompt.py, oversight_verifier.py, frontend/src/app/oversight/page.tsx. تست‌های واحد برای دو سناریو (AC string قدیمی و AC dict جدید) نیز شامل است.
**Excerpt:**
```
Stage 1 — Schema migration برای AC ساختاریافته
فایل‌ها: oversight_service.py, oversight_strong_prompt.py,
oversight_verifier.py, frontend/src/app/oversight/page.tsx

کاری که می‌شود:

OversightTask.acceptance_criteria از List[str] به List[Union[str, Dict]] تبدیل
helper _normalize_ac(ac) -> Dict[str, Any] که هم str هم dict را به
ساختار {text, verify_method, verify_plan, evidence_history} تبدیل می‌کند
backward compat: اگر AC قدیمی str است، verify_method="static" پیش‌فرض
در task_steps، هر step هم باید verify_method و verify_plan داشته باشد
migration یک‌بار در startup: روی همهٔ task های موجود _normalize_ac اجرا
شود (loop در _load_tasks)
Tests:

یک task با AC string قدیمی → بعد از load به ساختار جدید تبدیل شود
یک task با AC dict جدید → بدون تغییر باقی بماند
```

### Step 5: گسترش system prompt برای تولید verify_plan توسط AI
**Status:** `done` (100%)
**Scope:** این مرحله system prompt در فایل oversight_strong_prompt.py را گسترش می‌دهد تا AI علاوه بر AC، برای هر AC یک verify_method و در صورت نیاز verify_plan تولید کند. چارچوب تصمیم‌گیری بر اساس کلمات کلیدی AC تعریف شده است (ui_interaction, api_response, backend_test, static, manual_only). یک نمونه JSON (few-shot) برای هر نوع به AI داده می‌شود. اگر AI نتواند plan بدهد، fallback به static است. فایل‌های مرتبط: oversight_strong_prompt.py و oversight_service.py.
**Excerpt:**
```
Stage 2 — تولید verify_plan توسط AI
فایل‌ها: oversight_strong_prompt.py, oversight_service.py
(در _idea_to_prompt_multi_pass), oversight_service.py (در system prompt)

کاری که می‌شود:

system prompt در idea_to_prompt گسترش یابد: AI علاوه بر AC، برای هر AC
باید verify_method و در صورت نیاز verify_plan تولید کند
چارچوب تصمیم برای AI:
AC شامل «کلیک، نمایش، صفحه، مودال، input» → ui_interaction
AC شامل «endpoint، API، status code، response» → api_response
AC شامل «test، pytest، unit test» → backend_test
AC شامل «فایل X وجود دارد، imported است» → static
AC مبهم یا ذهنی (مثل «ظاهر زیبا») → manual_only
prompt یک نمونهٔ کامل JSON برای هر نوع به AI می‌دهد (few-shot)
اگر AI نتوانست plan بدهد → fallback به static
Tests:

یک ایدهٔ UI («دکمه login کار کند») → AC با ui_interaction + ui_steps
یک ایدهٔ API («endpoint /users 200 بدهد») → AC با api_response
یک ایدهٔ ذهنی («طراحی شیک‌تر») → AC با manual_only
```

### Step 6: اجرای هستهٔ پروب‌های تأیید (Probe Runners) برای هر AC
**Status:** `done` (100%)
**Scope:** این بخش شامل ایجاد پکیج جدید backend/app/services/verify_runtime/ با فایل‌های base.py (تعریف dataclass RuntimeProbeResult)، static_probe.py (wrapper روی grep فعلی)، ui_probe.py (استفاده از playwright.async_api با screenshot و browser pool)، api_probe.py (استفاده از httpx.AsyncClient با assert status_code و schema)، test_probe.py (استفاده از subprocess برای pytest با timeout 120s)، manual_probe.py (همیشه skipped) و runner.py (تابع run_probes_for_task با asyncio.Semaphore(3) و timeout کلی 5 دقیقه) است. همچنین شامل تست‌های mock برای UI probe، httpbin برای API probe و یک pytest dummy برای test_probe می‌شود. فایل‌های موجود در مسیرهای داده شده (مانند oversight_verifier.py) نباید تغییر کنند مگر برای import در static_probe.py.
**Excerpt:**
```
Stage 3 — Probe runners (هستهٔ کار)
پوشهٔ جدید: backend/app/services/verify_runtime/

فایل‌ها:

__init__.py
base.py — dataclass RuntimeProbeResult:
@dataclass
class RuntimeProbeResult:
    ac_id: str
    method: str  # static|ui|api|test|manual
    status: str  # passed|failed|error|skipped
    evidence: Dict[str, Any]  # {screenshot_paths, response_json, stdout, ...}
    duration_ms: int
    error_message: Optional[str]
    timestamp: str
static_probe.py — wrapper روی grep فعلی (همان منطق oversight_verifier)
ui_probe.py — استفاده از playwright.async_api:
async_playwright() → browser
برای هر step در ui_steps action متناظر را اجرا کن
screenshot قبل و بعد از هر action مهم (نام: <ac_id>_<step_idx>.png)
timeout per action: 10s پیش‌فرض
browser pool: max 3 concurrent
api_probe.py — استفاده از httpx.AsyncClient:
request اجرا
assert status_code (از plan)
assert response JSON schema (از plan: required fields)
response را به‌عنوان evidence ذخیره
test_probe.py — استفاده از subprocess:
pytest <test_path> --json-report --json-report-file=tmp.json
timeout: 120s
parse JSON output، success_count و failures
manual_probe.py — همیشه status="skipped" با پیام «نیاز به بازبینی دستی»
ابزارهای جدید nice-to-have:

runner.py — تابع run_probes_for_task(task, watched) -> List[RuntimeProbeResult]
برای هر AC method را تشخیص دهد
probe مناسب را call کند
با asyncio.Semaphore(3) همزمانی را محدود کند
timeout کلی task: 5 دقیقه
Tests:

mock playwright برای test UI probe (یا یک HTML ساده local serve)
httpbin برای test API probe
یک test pytest dummy برای test_probe
```

### Step 7: اضافه کردن فیلدهای Base URL و Config به WatchedProject و UI تنظیمات پروژه
**Status:** `done` (100%)
**Scope:** این بخش شامل افزودن فیلدهای frontend_base_url، backend_base_url و runtime_auth به مدل WatchedProject در oversight_service.py، ایجاد UI برای تنظیم این مقادیر در صفحه تنظیمات پروژه (projects/[id]/page.tsx یا settings UI)، پیاده‌سازی دکمه تست اتصال (ping به فرانت و GET به backend health)، و مدیریت حالت skipped برای probeها در صورت تنظیم نبودن URLها است. خارج از scope: پیاده‌سازی خود probeها (فقط تست اتصال ساده)، و تغییرات در سایر فایل‌های oversight.
**Excerpt:**
```
Stage 4 — Base URLs و config
فایل‌ها: oversight_service.py (WatchedProject),
frontend/src/app/projects/[id]/page.tsx یا settings UI

کاری که می‌شود:

اضافه کردن فیلدها به WatchedProject:
frontend_base_url: Optional[str] — مثلاً https://ai-creator-frontend.onrender.com
backend_base_url: Optional[str] — مثلاً https://ai-creator-backend.onrender.com
runtime_auth: Optional[Dict] — {type: "cookie"|"bearer", value: str}
در UI: یک section در تنظیمات پروژه:
input URL فرانت
input URL بک‌اند
dropdown نوع احراز هویت + input مقدار
دکمه «تست اتصال» (یک ping به فرانت + یک GET به backend health)
اگر URL تنظیم نشده → probe های ui/api همگی status="skipped" با
پیام «base URL تنظیم نشده»
Tests:

تست اتصال موفق + ناموفق
ذخیره و بارگذاری config
```

### Step 8: یکپارچه‌سازی runtime probes با verify_task در oversight_verifier.py
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن فراخوانی run_probes_for_task در ابتدای تابع verify_task (قبل از فراخوانی AI)، جمع‌آوری نتایج probeها، تبدیل آنها به متن شواهد runtime، و الحاق این متن به عنوان بخش جدیدی در prompt ارسالی به AI است. همچنین شامل منطق override نتایج AI بر اساس نتایج runtime (اولویت runtime بر AI) و مدیریت خطاهای timeout با fallback به AI-only می‌باشد. فایل‌های درگیر: oversight_verifier.py (اصلی)، runner.py (برای run_probes_for_task)، و احتمالاً oversight_strong_prompt.py (برای اصلاح system prompt).
**Excerpt:**
```
Stage 5 — یکپارچه‌سازی با verify_task
فایل: oversight_verifier.py

کاری که می‌شود:

در ابتدای verify_task (یا قبل از فراخوانی AI):
runtime_results = await run_probes_for_task(task, watched)
(با asyncio.wait_for timeout کلی)
هر probe که شکست خورد → log + continue (verify ادامه دهد)
results را به یک متن خوانا تبدیل کن:
## شواهد Runtime
### AC1: «وقتی روی دکمه X کلیک می‌کنم، مدال باز شود»
- method: ui_interaction
- status: ✅ passed
- evidence: screenshots/<task_id>/<run_id>/ac1_step3.png
- duration: 850ms
- مشاهدات: مدال [role=dialog] در 240ms ظاهر شد
### AC2: «GET /api/users → 200 با field email»
- method: api_response  
- status: ❌ failed
- actual_status: 500
- error: "Internal Server Error"
این متن را به‌عنوان بخش جدید در prompt verify اضافه کن
system prompt به AI: «شواهد runtime بالاتر از تحلیل کد است. اگر
runtime می‌گوید failed، حتی اگر کد درست به نظر برسد، AC پاس نشده.»
پس از AI، اگر برای یک AC هم runtime ✅ و هم AI گفت done → done قطعی
اگر runtime ❌ ولی AI گفت done → AI override کن به not_done (با هشدار log)
اگر runtime ✅ ولی AI گفت not_done → AI override کن به done
Tests:

verify_task با task که همهٔ probe ها pass شدند → status=done
verify_task با probe failed → AI override
verify_task با probe error (timeout) → fallback به فقط AI
```

### Step 9: ذخیره‌سازی evidence در storage/verify_evidence با cleanup و endpoint سرو
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی ساختار دایرکتوری storage/verify_evidence/<task_id>/<run_id>/ با فایل‌های ac1_step1.png, ac1_step2.png, ac2_response.json, ac3_pytest.json و manifest.json است. همچنین شامل cleanup policy (نگه‌داری 5 run آخر هر task)، endpoint جدید GET /api/oversight/tasks/{id}/evidence/{run_id}/<path> با authorization، و size limit 50MB per run با fallback به JPEG q=70 برای screenshots می‌شود. خارج از scope: پیاده‌سازی خود فرآیند capture یا تولید evidence.
**Excerpt:**
```
Stage 6 — ذخیره‌سازی evidence
فایل: verify_runtime/storage.py

کاری که می‌شود:

ساختار:
storage/verify_evidence/
  <task_id>/
    <run_id>/
      ac1_step1.png
      ac1_step2.png
      ac2_response.json
      ac3_pytest.json
      manifest.json   # links همهٔ evidence ها
cleanup policy: نگه‌داری فقط 5 run آخر هر task
endpoint جدید: GET /api/oversight/tasks/{id}/evidence/{run_id}/<path>
→ serve فایل (با authorization)
size limit: 50MB per run؛ اگر بیشتر شد، screenshots را به JPEG q=70 کم کن
```

### Step 10: افزودن شواهد Runtime به PDF و پیام تلگرام
**Status:** `done` (100%)
**Scope:** این مرحله شامل افزودن یک بخش جدید به نام «📷 شواهد Runtime» در PDF خروجی است که برای هر Acceptance Criteria (AC) یک کارت شامل متن AC، badge روش (UI/API/Test)، badge وضعیت، و شواهد inline (تصویر برای UI، JSON truncated برای API، stdout pytest truncated برای Test) ایجاد می‌کند. همچنین در پیام تلگرام، اگر هر probe failed باشد، یک خلاصه با وضعیت هر AC و لینک به PDF پیوست ارسال می‌شود. فایل‌های هدف: oversight_verify_pdf.py و notification_service.py. خارج از scope: تغییر منطق اجرای probeها یا ذخیره شواهد.
**Excerpt:**
```
در PDF، یک section جدید «📷 شواهد Runtime»:
برای هر AC، یک card با:
متن AC
method badge (UI / API / Test)
status badge
برای UI: تصویر screenshot inline
برای API: JSON پاسخ (truncated به 500 byte) در <pre>
برای Test: stdout pytest (truncated)
در پیام تلگرام: اگر هر probe failed بود، یک خلاصه:
❌ شواهد runtime:
  • AC1 ui_interaction: passed (240ms)
  • AC2 api_response: failed (status 500)
  • AC3 backend_test: passed (3 tests)
📎 جزئیات کامل در PDF پیوست
```

### Step 11: Stage 8 — Frontend UI برای نمایش evidence در مودال جزئیات تسک
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی UI در frontend/src/app/oversight/page.tsx برای نمایش آخرین verify runtime در مودال جزئیات تسک است. شامل: نمایش row برای هر AC با method icon + status + دکمه مشاهده evidence، مودال دوم با gallery screenshot (lightbox)، JSON formatted با syntax highlight، terminal-style block برای stdout، و دکمه جدید «🔬 Verify با Runtime» که شامل probe ها است. verify عادی بدون probe باقی می‌ماند. همچنین بخش تنظیمات پروژه برای Runtime Verify با URLها و auth. خارج از scope: backend logic، تست‌ها، و پیاده‌سازی actual runtime verification.
**Excerpt:**
```
Stage 8 — Frontend UI (نمایش evidence)
فایل: frontend/src/app/oversight/page.tsx

کاری که می‌شود:

در مودال جزئیات تسک، section جدید «🔬 آخرین verify runtime»:
برای هر AC: row با method icon + status + دکمهٔ «مشاهدهٔ evidence»
کلیک روی دکمه → مودال modal دوم با:
برای UI: gallery screenshot ها (lightbox)
برای API: JSON formatted با syntax highlight
برای Test: terminal-style block با stdout
دکمهٔ جدید «🔬 Verify با Runtime» (متفاوت از verify عادی):
این یکی شامل probe ها است (کندتر)
verify عادی بدون probe می‌ماند برای سرعت
در تنظیمات پروژه: section «Runtime Verify» با URLها و auth
```

### Step 12: Stage 9: پیاده‌سازی مدیریت چرخه‌عمر، زمان‌بندی، محدودیت‌ها و Degrade امنیتی Runtime
**Status:** `done` (100%)
**Scope:** این مرحله شامل پیاده‌سازی مدیریت چرخه‌عمر Playwright browser process در lifespan FastAPI (شروع و kill بعد از 5 دقیقه idle)، اعمال per-task timeout کلی 5 دقیقه، per-probe timeout (ui=30s, api=10s, test=120s)، Semaphore با حداکثر 3 probe موازی برای یک task، graceful degrade به static در صورت عدم نصب Playwright (با warning)، circuit breaker با 3 خطای متوالی probe که runtime را برای 10 دقیقه disable می‌کند، و خواندن environment flag RUNTIME_VERIFY_ENABLED=true|false از .env است. خارج از scope: پیاده‌سازی خود probeها، منطق business، و frontend.
**Excerpt:**
```
Stage 9 — Performance, safety, edge cases
کاری که می‌شود:
Playwright browser process را در lifespan FastAPI start کن (شاره شده)
→ بعد از 5 دقیقه idle، آن را kill کن
per-task timeout کلی: 5 دقیقه
per-probe timeout: ui=30s, api=10s, test=120s
Semaphore: حداکثر 3 probe موازی برای یک task
اگر runtime در محیط Render (production) فعال نیست (مثلاً playwright install نشده) → graceful degrade به فقط static (با warning)
circuit breaker: اگر 3 task پشت‌سرهم probe error دادند، runtime را برای 10 دقیقه disable کن
environment flag: RUNTIME_VERIFY_ENABLED=true|false در .env
```

### Step 13: Stage 10: پیاده‌سازی تست‌های واحد و یکپارچه‌سازی برای قابلیت Verify Runtime
**Status:** `done` (100%)
**Scope:** این مرحله شامل نوشتن تست‌های واحد برای هر probe (static, ui, api, test, runner) و یک تست یکپارچه‌سازی end-to-end است. همچنین شامل ایجاد فیکسچرهای known-good و known-bad برای اعتبارسنجی سناریوهای موفق و شکست می‌شود. معیارهای پذیرش عملکردی و کیفی (مانند type-check، عدم شکست تست‌های موجود، graceful disable در production) نیز بخشی از این مرحله هستند. خارج از scope این مرحله، بازنویسی verifier فعلی، visual regression testing، load testing، security scanning و mobile UI testing است.
**Excerpt:**
```
unit tests:
test_static_probe.py — grep درست
test_ui_probe.py — با یک HTML server محلی
test_api_probe.py — با httpbin
test_test_probe.py — با pytest dummy
test_runner.py — orchestration
test_runtime_integration.py — verify_task با probe ها end-to-end
یک «known-good» fixture: task ساده که همه‌چیز pass می‌شود
یک «known-bad» fixture: task که هر probe باید fail شود
✅ معیارهای پذیرش کلی
عملکردی
not done
AC با verify_method=static همان رفتار قبلی verify را دارد (no regression)
not done
AC با verify_method=ui_interaction: playwright headless browser باز
می‌کند، steps را اجرا می‌کند، screenshot می‌گیرد، نتیجه برمی‌گرداند
not done
AC با verify_method=api_response: HTTP request می‌رود، status + شِما
چک می‌شود
not done
AC با verify_method=backend_test: pytest در subprocess با timeout
اجرا می‌شود
not done
AC با verify_method=manual_only: skipped با پیام واضح
not done
هر probe که error داد، verify ادامه می‌دهد (نه crash)
not done
base URL ها قابل تنظیم per project
not done
evidence فایل‌ها روی disk ذخیره می‌شوند، با cleanup policy
not done
PDF و Telegram message شواهد را embed می‌کنند
not done
Frontend modal جدید برای drill-down evidence
کیفی
not done
type-check (mypy + tsc) بدون error
not done
هیچ test موجود fail نمی‌شود
not done
محیط production (Render) با RUNTIME_VERIFY_ENABLED=false کاملاً
مثل قبل کار می‌کند (graceful disable)
not done
هیچ probe که فقط برای یک AC شکست خورد، کل verify را crash نکند
کنترل کیفیت verify
not done
روی یک تسک "known-good" (همه AC ها واقعاً پاس شده‌اند) →
verify=done
not done
روی یک تسک "known-bad" (UI AC شکست خورده) → AI نمی‌تواند آن را
done اعلام کند (runtime override)
not done
روی یک تسک با کد درست ولی deploy نشده → runtime می‌گوید fail
(چون probe می‌رود به URL واقعی، نه به کد محلی)
```

### Step 14: ساخت inspector_probe برای اتصال خودکار به verify جدید و ضمیمه تلگرامی
**Status:** `done` (100%)
**Scope:** این بخش شامل طراحی و پیاده‌سازی یک probe جدید به نام inspector_probe است که به صورت خودکار صفحه دیپلوی‌شده را با Playwright باز می‌کند، screenshot می‌گیرد، console و backend logs را جمع می‌کند، با Vision AI تحلیل می‌کند و نتیجه را به عنوان شواهد در گزارش verify بازمی‌گرداند. همچنین شامل ذخیره‌سازی جلسه بازرسی (inspector_session)، ارسال بسته کامل به تلگرام و حذف خودکار screenshot‌ها از دیسک پس از ارسال موفق است. خارج از این بخش: پیاده‌سازی خود verify، طراحی UI تب بازرس، و مکانیزم‌های ذخیره‌سازی طولانی‌مدت.
**Excerpt:**
```
ساخت یک probe جدید به اسم inspector_probe که به‌صورت خودکار (بدون مداخله کاربر) صفحه دیپلوی‌شده پروژه را با Playwright سرور-سایدی باز می‌کند، navigate / click می‌کند، screenshot می‌گیرد، console و backend logs را جمع می‌کند، با Vision AI screenshot ها را تحلیل می‌کند و نتیجه را به‌عنوان probe evidence در گزارش verify بازمی‌گرداند. همزمان، تمام مراحل را در یک inspector_session جدید با عنوان «🤖 auto-verify · …» ذخیره می‌کند تا کاربر بتواند از تب بازرس ویژه آن را مرور کند. پس از تمام شدن verify و تولید followup prompt، یک بسته‌ی کامل به تلگرام ارسال می‌شود (گزارش متنی + screenshot ها + پرامپت بروز) و **پس از موفقیت ارسال، screenshot ها از دیسک حذف می‌شوند** تا حافظه‌ی سرور همیشه کم بماند.
```

### Step 15: Phase 1: پیاده‌سازی محدودیت‌ها و معماری ذخیره‌سازی screenshot با Vision Fallback Chain
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی کامل محدودیت‌های Phase 1 (navigate, click, screenshot, Vision AI, console log, backend log, Telegram attachment, TTL cleanup) و معماری ذخیره‌سازی screenshot روی دیسک با path نسبی در DB است. همچنین شامل Vision Fallback Chain سه‌لایه (Vision model → text-only verify model → none) و ساختار داده probe (RuntimeProbeResult) با شرط‌های pass/fail می‌باشد. فایل‌های جدید inspector_probe.py و vision_helper.py ایجاد می‌شوند و تغییرات در base.py, runner.py, oversight_verifier.py اعمال می‌گردد. محدودیت‌های ایمنی (timeout 60s, max 1 parallel, max 2 screenshots, 500KB cap, circuit breaker, TTL 3 روز) و graceful degrade برای همه شکست‌ها لحاظ شده است.
**Excerpt:**
```
## محدودیت‌های Phase 1
✅ navigate به URL
✅ click روی selector
✅ screenshot (ذخیره روی دیسک، نه base64 در DB)
✅ Vision AI تحلیل screenshot (با fallback chain)
✅ console log capture
✅ backend log correlation
✅ ضمیمه‌ی تلگرامی + cleanup
✅ TTL cleanup خودکار برای orphan screenshots
❌ fill / submit / wait → Phase 2
❌ login / auth → Phase 3
❌ multi-step complex sequences → Phase 2
---
## معماری ذخیره‌سازی screenshot
**روی دیسک، نه DB:**
- مسیر: storage/oversight/runtime_evidence/{task_id}/{run_id}/{ac_id}/{label}.png
- مثلاً: storage/oversight/runtime_evidence/task_abc/run_xyz/ac01_h/after_navigate.png
**در DB (inspector_message.extra_data) فقط:**
- path نسبی به فایل
- label
- vision_description (متن استخراج‌شده — این مهم‌ترین artifact است)
- timestamp
---
## Vision Fallback Chain (مهم)
برای هر screenshot، به این ترتیب تلاش کن:
**1. Vision موجود در سیستم (همان منطق تب بازرسی):**
- describe_screenshot_with_vision() در backend/app/services/oversight_inspector_bridge.py:44
**2. اگر مرحله 1 خطا داد یا API key نبود → fallback به verify model:**
- مدل verify (مثل deepseek-chat) text-only است
- یک پرامپت ساده: «بر اساس این لاگ‌ها و HTML، چه چیزی روی صفحه دیده می‌شد؟»
- خروجی با source="fallback_text_only"
**3. اگر هر دو شکست خوردند → فقط screenshot path ذخیره می‌شود:**
- vision_description = None
---
## ساختار داده probe
نتیجه‌ی run_inspector_probe RuntimeProbeResult با ساختار:
{
  ac_id, ac_text, method: "ui_interaction", status: "passed" | "failed" | "error" | "skipped",
  evidence: {
    inspector_session_id: int,
    actions_taken: [{action: "navigate", url: "/login", duration_ms: 1234}, ...],
    screenshots: [{path, label, vision_description, vision_source, archived_to_telegram}],
    console_errors: [{level, message, source, timestamp}],
    backend_log_summary: "...",
    final_url: "...",
    assertion_results: [{expectation, met, reason}]
  },
  duration_ms: int,
  error_message: Optional[str]
}
```

### Step 16: سه فیکس جدید پس از تست Phase 2: چک‌لیست در متن تلگرام، تبدیل bundle به PDF، بهبود vision prompt برای تشخیص feature
**Status:** `done` (100%)
**Scope:** این بخش شامل سه فیکس مستقل است که باید هم‌اکنون اجرا شوند. فیکس ۱: اضافه کردن خلاصه چک‌لیست task_steps به متن پیام تلگرام (نه فقط پیوست). فیکس ۲: تبدیل mega-bundle از HTML به PDF با پشتیبانی فارسی و fallback به HTML. فیکس ۳: بهبود vision prompt برای تشخیص حضور feature در صفحه و تأثیر آن بر pass/fail probe. بخش الف (Phase 2) قبلاً اجرا شده و فقط برای مرجع است — نباید دوباره اجرا شود.
**Excerpt:**
```
## فیکس ۱ — چک‌لیست به‌روز در متن پیام تلگرام
### هدف
در `_send_verify_notification_bg`، متن نوتیفیکیشن (مستقل از پیوست) باید شامل خلاصهٔ chk‌لیست به‌روز task_steps باشد:
📋 چک‌لیست (X/N انجام‌شده):
[✅] مرحله ۱: عنوان (100%)
[~] مرحله ۲: عنوان (50%) — باقی‌مانده: «چی مونده»
[ ] مرحله ۳: عنوان (0%)
...

## فیکس ۲ — تبدیل bundle از HTML به PDF
### هدف
mega-bundle که الان `.html` است را به `.pdf` تبدیل کن تا روی موبایل بدون نیاز به browser در همان viewer تلگرام باز شود.

## فیکس ۳ — بهبود vision prompt برای تشخیص feature
### هدف
vision در حال حاضر فقط صفحه را توصیف می‌کند. باید صریحاً تشخیص دهد «آیا feature ذکرشده در AC در این صفحه قابل مشاهده است یا نه؟» و این تشخیص روی pass/fail probe تأثیر بگذارد.
```

### Step 17: مرور سریع Phase 1 و 2 و سه فیکس آخر — آماده‌سازی برای Phase 3
**Status:** `done` (100%)
**Scope:** این بخش صرفاً یک مرور (review) از قابلیت‌های پیاده‌سازی شده در Phase 1، Phase 2 و سه فیکس آخر است. هیچ کار اجرایی جدیدی در این بخش تعریف نشده و صرفاً برای یادآوری وضعیت فعلی پروژه قبل از شروع Phase 3 ارائه شده است. تمام آیتم‌های ذکر شده قبلاً اجرا شده‌اند.
**Excerpt:**
```
✅ **Phase 1** اضافه کرد:
- inspector_probe.py — Playwright server-side با navigate + click +
  screenshot + console capture + backend log query
- vision_helper.py با fallback chain (multimodal → text-only → none)
- inspector_session با عنوان «🤖 auto-verify · …» برای visibility
- TTL cleanup + startup recovery + telegram screenshot+followup
✅ **Phase 2** اضافه کرد:
- Per-step probes با route inferred از step.title/scope
- Network capture (frontend + backend URLs per probe)
- Step-aware AI verifier prompt
- prompt_history + apply_followup_as_new_prompt + revert endpoint
- mega-bundle (PDF با fallback HTML)
✅ **سه فیکس آخر** اضافه کرد:
- چک‌لیست در caption تلگرام
- Bundle PDF (نه HTML)
- Vision `feature_present` (yes/no/unclear) با pass/fail flip
```

### Step 18: رفع محدودیت‌های Phase 2: تعامل با UI، تشخیص دقیق‌تر، لاگین و submit فرم
**Status:** `done` (100%)
**Scope:** این بخش چهار محدودیت اصلی Phase 2 را مشخص می‌کند که Phase 3 باید حل کند: (1) ناتوانی probe در تعامل با feature (مثلاً کلیک روی دکمه)، (2) false-positive بالای vision در تشخیص feature_present، (3) عدم امکان بررسی صفحات نیازمند لاگین، (4) عدم توانایی تست ACهای نیازمند submit فرم. این محدودیت‌ها از تست واقعی Phase 2 و سه فیکس استخراج شده‌اند.
**Excerpt:**
```
# محدودیت‌های فعلی که Phase 3 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 2 + سه فیکس مشخص شد:
1. **probe فقط navigate می‌کند و نگاه می‌کند** — نمی‌تواند با feature
   تعامل کند. اگر feature یک دکمه باشد، probe دکمه را نمی‌زند تا
   ببیند modal باز می‌شود یا نه.
2. **Vision feature_present حدود ۴۰٪ false-positive دارد** —
   step probe 2 «اضافه کردن UI انتخاب محتوا» را passed داد در حالی
   که UI ساخته نشده بود. علت: vision دکمه‌های عمومی صفحه را دید و
   فکر کرد همینه. اگر probe می‌توانست «کلیک روی selector_hint و
   چک کردن modal/result» را انجام دهد، تشخیص دقیق‌تر بود.
3. **صفحات با لاگین قابل بررسی نیستند** — مثلاً اگر کاربر تسکی روی
   `/admin/dashboard` تعریف کند، probe redirect به /login می‌خورد
   و تشخیص «این feature ساخته شده» غلط می‌شود (همان مشکلی که در
   system probe رخ داد — vision گفت «صفحه login می‌بینم»).
4. **AC هایی که نیاز به submit فرم دارند نمی‌توانند تست شوند** —
   مثلاً «وقتی فرم لاگین پر شود و submit شود، کاربر به داشبورد می‌رود».
```

### Step 19: Phase 3: پیاده‌سازی سه قابلیت متمم (Form Interaction, Auth Management, Enhanced Detection)
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی کامل سه قابلیت متمم در Phase 3 است: (A) پشتیبانی از Form/Input Interaction Recipes در inspector_probe با 16 action مختلف، (B) مدیریت Authentication/Session با auto-detect login redirect و auth recipe، (C) Enhanced Feature Detection با multi-screenshot و before/after analysis. تمام تغییرات در فایل‌های backend متمرکز است و frontend را شامل نمی‌شود. نکته حیاتی: AI enricher باید برای method=ui_interaction یک sequence 3-8 step واقعی پیشنهاد دهد.
**Excerpt:**
```
# هدف کلی Phase 3 — سه قابلیت متمم
══════════════════════════════════════════════════════════════════════
**A) Form/Input Interaction Recipes**
inspector_probe باید پشتیبانی کند از:
- `fill {selector, value}` — تایپ متن در input/textarea
- `submit {form_selector}` یا کلیک روی دکمهٔ submit
- `wait_for {selector, timeout_ms, state}` — صبر تا المنت ظاهر شود
- `select {selector, option}` — انتخاب از dropdown
- `check {selector}` / `uncheck {selector}` — checkbox/radio
- `hover {selector}` — برای tooltip ها
- `wait_for_url {contains}` — صبر تا URL تغییر کند (برای SPA)
این actions در `verify_plan.ui_steps` تعریف می‌شوند (schema موجود ui_probe).

**B) Authentication / Session Management**
WatchedProject از قبل فیلد `runtime_auth: {type, value}` دارد. الان ui_probe (نه inspector_probe) فقط ازش استفاده می‌کند. باید:
- inspector_probe هم cookie/bearer auth را اعمال کند قبل از navigate
- Auto-detect login redirect → اگر صفحه به /login redirect شد، evidence را با وضعیت «نیاز به لاگین» علامت بزن
- Auth recipe در WatchedProject — یک sequence «navigate to /login → fill email → fill password → submit → wait_for_url(/dashboard)»

**C) Enhanced Feature Detection (multi-screenshot + before/after)**
به‌جای یک screenshot واحد:
- screenshot قبل از interaction
- screenshot بعد از interaction
- Vision آنالیز diff: «بعد از کلیک، چه چیزی روی صفحه ظاهر شد؟»
- Network call analysis: آیا interaction باعث backend call شد؟
- اگر AC انتظار modal دارد، چک کن modal واقعاً ظاهر شد
```

### Step 20: پیاده‌سازی auth recipe برای probe‌ها در runtime verification
**Status:** `done` (100%)
**Scope:** این بخش مربوط به افزودن قابلیت احراز هویت خودکار (auth recipe) به فرآیند runtime verification است. شامل طراحی ساختار داده runtime_auth_recipe از نوع Optional[Dict]، پیاده‌سازی flow لاگین مبتنی بر فرم (form_login) با مراحل گام‌به‌گام (fill, click, wait_for_url)، ذخیره‌سازی storage_state (cookies + localStorage) برای استفاده probe‌ها، و مکانیزم refresh خودکار بر اساس session_ttl_minutes. خارج از scope: پیاده‌سازی خود probe‌ها، logic verification، و مدیریت خطاهای network.
**Excerpt:**
```
# 🆕 (Phase 3) — auth recipe برای probe ها
# اگر تنظیم شد، قبل از هر verify run یک login flow اجرا می‌شود و
# storage_state (cookies + localStorage) برای استفاده‌ی probe ها
# ذخیره می‌شود.
runtime_auth_recipe: Optional[Dict[str, Any]] = None
# ساختار:
# {
#   "type": "form_login",
#   "login_url": "/login",
#   "steps": [
#     {"action": "fill", "selector": "input[name=email]",
#      "value_env": "TEST_EMAIL"},  # یا "value": "test@test.com"
#     {"action": "fill", "selector": "input[name=password]",
#      "value_env": "TEST_PASSWORD"},
#     {"action": "click", "selector": "button[type=submit]"},
#     {"action": "wait_for_url", "contains": "/dashboard",
#      "timeout_ms": 5000},
#   ],
#   "success_indicator": {"selector": "[data-testid='user-menu']",
#                         "must_exist": true},
#   "session_ttl_minutes": 30,  # storage_state بعد از این مدت refresh
# }
```

### Step 21: پیاده‌سازی کش رمزنگاری‌شده storage_state و پشتیبانی از آن در probe و verifier
**Status:** `done` (100%)
**Scope:** این بخش شامل سه تغییر است: (1) ایجاد تابع `obtain_or_refresh_storage_state` در فایل جدید `auth_runner.py` که storage_state را با AES-GCM رمزنگاری کرده و در حافظه کش می‌کند، (2) افزودن پشتیبانی از `ProbeContext.storage_state` در `inspector_probe.py` برای استفاده از storage_state موجود در context مرورگر، (3) تغییر در `oversight_verifier.py` برای استفاده از storage_state قبل از ساخت ProbeContext. خارج از scope: پیاده‌سازی خود recipe steps، مدیریت خطاهای غیر از login، و تست‌های یکپارچه‌سازی.
**Excerpt:**
```
# 🆕 (Phase 3) — cached storage state (encrypted)
runtime_storage_state: Optional[Dict[str, Any]] = None
# {
#   "encrypted_blob": str,  # AES-GCM encrypted JSON storage_state
#   "expires_at": ISO,
#   "obtained_at": ISO,
#   "login_failed_count": int,
# }
Backend — فایل جدید
backend/app/services/verify_runtime/auth_runner.py:

تابع async def obtain_or_refresh_storage_state(watched, force=False) -> Optional[Dict[str, Any]]:

اگر runtime_auth_recipe تنظیم نشده → return None
اگر runtime_storage_state معتبر و expires_at > now و force=False →
decrypt و return
در غیر این صورت: launch Chromium → execute recipe.steps → اگر
success_indicator OK → دریافت storage_state از context →
encrypt → ذخیره در watched → return decoded
اگر login شکست خورد → login_failed_count += 1، return None
بعد از ۳ شکست متوالی → recipe را disable موقت (با log)
تابع helper _encrypt_storage(data: Dict, key: bytes) -> str و
معکوس _decrypt_storage(blob: str, key: bytes) -> Dict:

AES-GCM با کلید مشتق از env OVERSIGHT_AUTH_KEY (اگر نبود، یک
کلید تصادفی بساز و در env ست کن — warning log)
این برای اینکه cookie ها در plaintext در DB نمی‌مانند.
Backend — تغییر دیگر
backend/app/services/verify_runtime/inspector_probe.py:

پشتیبانی از ProbeContext.storage_state (فیلد جدید در base.py):

اگر ctx.storage_state پر است:
context = await browser.new_context(
    viewport={"width": 1280, "height": 800},
    storage_state=ctx.storage_state,  # Playwright API
)
این تمام cookies + localStorage را به probe می‌دهد بدون نیاز به
login مجدد.
Backend — تغییر در verifier
backend/app/services/oversight_verifier.py:

در _verify_task، قبل از ساخت ProbeContext:
```

### Step 22: Phase 3: Auth Recipe, Enhanced Feature Detection, UI Panel, AI Enricher, and Safety Limits
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی کامل Phase 3 است: مدیریت auth recipe (ذخیره storage_state، تشخیص redirect به login)، enhanced feature detection (before/after screenshot pairs، vision pair analysis، expected API calls assertion)، UI panel برای تنظیم auth recipe، بهبود AI enricher برای تولید recipe ۳-۸ مرحله‌ای، و محدودیت‌های ایمنی. تمام فایل‌های backend و frontend ذکر شده باید تغییر کنند. رفتارهای graceful degrade برای شکست auth، vision، و enricher تعریف شده است.
**Excerpt:**
```
# 🆕 (Phase 3) — اگر watched recipe دارد، storage_state بگیر/تازه کن
auth_storage_state = None
if watched and getattr(watched, "runtime_auth_recipe", None):
    try:
        from .verify_runtime.auth_runner import obtain_or_refresh_storage_state
        auth_storage_state = await obtain_or_refresh_storage_state(watched)
    except Exception as _ae:
        logger.warning(f"auth runner failed: {_ae}")

_probe_ctx = build_probe_context(
    ...,
    storage_state=auth_storage_state,
)
Login redirect detection
در _run_inspector_inner، بعد از navigate، چک کن:

اگر page.url شامل /login یا /signin بود (و route قبلی این نبود)
یا page.title شامل «Login» یا «ورود» بود
→ علامت‌گذاری probe با auth_required: true در evidence
vision_helper این را می‌گیرد و در feature_present تأثیر می‌دهد

auth_required = False
final_url_lower = (page.url or "").lower()
if any(p in final_url_lower for p in ("/login", "/signin", "/auth")):
    if "/login" not in full_url.lower():  # خود route نبود
        auth_required = True

evidence["auth_required"] = auth_required
if auth_required:
    assertion_results.append({
        "expectation": "صفحه‌ی هدف بدون redirect به login باز شود",
        "met": False,
        "reason": f"redirect به {page.url} — احتمالاً auth recipe لازم است",
    })
══════════════════════════════════════════════════════════════════════

C) Enhanced Feature Detection — جزئیات
══════════════════════════════════════════════════════════════════════

Before/After screenshot pairs
وقتی verify_plan.ui_steps شامل interaction (click/fill/submit) است:

screenshot قبل از اولین interaction (label="before_interaction")
screenshot بعد از آخرین interaction (label="after_interaction")
Vision آنالیز diff: prompt جدید برای vision_helper
# vision_helper.py — تابع جدید
async def analyze_screenshot_pair(
    before_path: str,
    after_path: str,
    context: Dict[str, Any],  # شامل ac_text و actions_taken
) -> Dict[str, Any]:
    """آنالیز یک جفت screenshot قبل/بعد از interaction.

    Returns:
      {
        "before_description": str,
        "after_description": str,
        "diff_description": str,    # «بعد از کلیک X، Y ظاهر شد»
        "interaction_succeeded": "yes" | "no" | "unclear",
        "feature_present": "yes" | "no" | "unclear",
        "source": str,
      }
    """
این تابع از multimodal vision یک prompt دو-عکسی می‌فرستد و می‌پرسد:
«قبل از این تعامل، صفحه X بود. بعد از تعامل، Y شد. آیا تعامل کار
کرد و feature واقعاً عمل کرد؟»

Network call analysis
inspector_probe قبلاً backend_urls_called ذخیره می‌کرد. در Phase 3:

اگر AC انتظار یک API call خاص دارد (مثلاً «POST /api/debates ساخته
شود»)، probe باید بفهمد آیا آن endpoint در network_calls هست:

# در verify_plan
"expected_api_calls": [
    {"method": "POST", "path_contains": "/api/debates"},
    {"method": "GET", "path_contains": "/api/projects/.*/files"},
]
probe بعد از interaction چک می‌کند:

expected = plan.get("expected_api_calls") or []
for exp in expected:
    matched = any(
        c.get("method") == exp["method"]
        and exp["path_contains"] in (c.get("url") or "")
        for c in network_calls
    )
    assertion_results.append({
        "expectation": f"API call {exp['method']} {exp['path_contains']}",
        "met": matched,
        "reason": "ثبت شد" if matched else "ثبت نشد",
    })
Multi-screenshot evidence storage
الان _MAX_SCREENSHOTS = 2. در Phase 3 بالا ببر به 5 (یا 6) تا
interaction های پیچیده کاملاً capture شوند.

══════════════════════════════════════════════════════════════════════

D) UI — تنظیمات auth recipe
══════════════════════════════════════════════════════════════════════

frontend/src/app/oversight/page.tsx — در همان panel «runtime» که
runtime_repo_path و base URLs ست می‌شوند:

یک بخش جدید «🔐 Auth Recipe (اختیاری)»
form فیلدها:
login_url (text input)
email (text input — برای save در env var name)
password (text input — برای save در env var name)
email selector (text input — مثلاً input[name=email])
password selector (text input)
submit selector
success indic
```

### Step 23: Phase 4: Smart Navigation + Backend Log Probe + Code-aware Verifier
**Status:** `done` (100%)
**Scope:** این بخش شامل اجرای کامل Phase 4 از سری verify جدید است که پس از Phase 1, 2, 3 و سه فیکس آخر اجرا می‌شود. محتوای دقیق و جزئیات اجرایی Phase 4 در این بخش ارائه نشده و صرفاً به عنوان یک هدر و مرور وضعیت فعلی ذکر شده است. هیچ دستورالعمل اجرایی، لیست کارها یا تغییرات مشخصی در این بخش وجود ندارد.
**Excerpt:**
```
# 🎯 پرامپت کامل Phase 4 — Smart Navigation + Backend Log Probe + Code-aware Verifier
⚠️ این پرامپت Phase 4 از سری «verify جدید» است که پس از Phase 1، 2،
و 3 (شامل سه فیکس آخر) اجرا می‌شود.
══════════════════════════════════════════════════════════════════════
# مرور خیلی سریع وضعیت فعلی
══════════════════════════════════════════════════════════════════════
✅ **Phase 1**: inspector_probe پایه با navigate + screenshot + vision +
   session + telegram + cleanup + recovery.
✅ **Phase 2**: per-step probes + prompt versioning + mega-bundle PDF.
✅ **Phase 3**: action loop (fill/click/wait/assert) + auth recipe +
   vision_pair + expected_api_calls + force backfill + Telegram trigger.
✅ **سه فیکس آخر**: SPA-404 detection + system probe relaxation +
   conservative routing (skip when no specific route).
```

### Step 24: رفع مشکلات باقیمانده Phase 3 در Phase 4: route guessing ضعیف، backend-heavy benefit صفر، استفاده ناکامل از Render logs و inspector chat
**Status:** `done` (100%)
**Scope:** این بخش چهار مشکل مشخص از تست واقعی Phase 3 را فهرست می‌کند که Phase 4 باید حل کند: (1) route guessing ضعیف برای تسک‌های دارای URL خاص، (2) تسک‌های backend-heavy که از probe UI سود نمی‌برند و verify بدون شواهد می‌ماند، (3) استفاده ناکامل از Render logs (فقط error/warn فیلتر می‌شود)، (4) استفاده ناکامل از inspector chat infrastructure برای auto-verify. این بخش صرفاً مشکلات را توصیف می‌کند و راه‌حل ارائه نمی‌دهد. خارج از scope: پیاده‌سازی راه‌حل‌ها، کدنویسی، یا تغییر فایل‌ها.
**Excerpt:**
```
# مشکلات باقیمانده که Phase 4 باید حل کند
══════════════════════════════════════════════════════════════════════
از تست واقعی Phase 3 + سه فیکس مشخص شد:
1. **route guessing ضعیف**: برای تسک trading-system که صفحات URL خاصی
   داشتند (مثل /routing-diagram, /charts)، probe نمی‌تواند URL واقعی
   را پیدا کند. حدس‌های keyword-based 404 می‌گیرند. کاربر گفت در
   تجربه قبلی هم با این مشکل اذیت شده بود.
2. **تسک‌های backend-heavy benefit صفر می‌گیرند**: تسک‌هایی مثل
   DebateAttachment (backend models, endpoints, service logic) از
   probe UI سود نمی‌برند چون feature تو UI دیده نمی‌شود. probe ها
   skipped می‌شوند ولی verify بدون شواهد runtime می‌ماند.
3. **استفاده ناکامل از Render logs**: الان فقط لاگ‌های window زمانی
   probe فیلتر می‌شوند (level=error/warn). با اینکه RENDER_API_KEY ست
   شده، از لاگ‌های مرتبط به فایل‌های target تسک یا call های endpoint
   مرتبط استفاده نمی‌کنیم.
4. **استفاده ناکامل از inspector chat infrastructure**: بازرس ویژه
   دستی از قبل لاگ‌های backend + console همراه هر پیام چت ذخیره
   می‌کند، ولی auto-verify از این infrastructure استفاده نمی‌کند.
══════════════════════════════════════════════════════════════════════
```

### Step 25: پیاده‌سازی سه ستون Phase 4: Smart Navigation Probe، Backend Log Probe و Code-aware Verifier
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی سه قابلیت مجزا در Oversight Service است: (A) Smart Navigation Probe که به جای حدس URL، از home page شروع کرده و nav menu را برای یافتن لینک مرتبط با feature تحلیل می‌کند، (B) Backend Log Probe که برای تسک‌های backend-heavy لاگ‌های Render را بر اساس target_files و AC keywords فیلتر و تحلیل می‌کند، (C) Code-aware Verifier که برای هر Acceptance Criteria به صورت جداگانه با GitHub API چک می‌کند که آیا diff اخیر آن AC را پیاده کرده است. این سه قابلیت به صورت موازی و مستقل از هم کار می‌کنند و خروجی هر کدام به صورت جداگانه در نتیجه نهایی گزارش می‌شود.
— [merged] این بخش شامل سه زیرسیستم جدید برای بهبود دقت verify در Phase 4 است: (A) Smart Navigation Probe برای زمانی که route inference نتوانست مسیر را پیدا کند، (B) Backend Log Probe برای تحلیل لاگ‌های Render برای تسک‌های backend، و (C) Code-aware Verifier برای تحلیل per-AC commits. همچنین شامل Task Type Routing است که نوع تسک را تشخیص داده و probe مناسب را dispatch می‌کند. این بخش فقط پیاده‌سازی این سه سیستم را پوشش می‌دهد و شامل تغییرات در runner.py، oversight_verifier.py و فایل‌های جدید navigation_helper.py، backend_log_probe.py و code_aware_verifier.py است.
**Excerpt:**
```
# هدف کلی Phase 4 — سه ستون
══════════════════════════════════════════════════════════════════════
**A) Smart Navigation Probe (Agentic Browsing)**
به‌جای حدس زدن URL از روی keyword، probe به home می‌رود، nav menu
را می‌خواند، و AI تصمیم می‌گیرد کدام لینک به feature مرتبط است.
این الگوی استاندارد OpenAI Operator / Anthropic Computer Use است.
**B) Backend Log Probe**
برای تسک‌های backend-heavy (که AC شون از UI element حرف نمی‌زند)،
به‌جای probe UI، یک probe جدید لاگ‌های Render فیلتر شده بر اساس
target_files تسک + AC keywords را تحلیل می‌کند. خروجی: «آیا این
feature backend deploy شده و call می‌شود؟»
**C) Code-aware Verifier (Per-AC commit analysis)**
gh API الان فقط در سطح کل تسک استفاده می‌شود. در Phase 4، برای هر
AC جداگانه چک می‌شود که آیا diff اخیر آن AC را پیاده کرده یا نه.
این بدون نیاز به repo کلون محلی، با همان GitHub API که داریم.
══════════════════════════════════════════════════════════════════════
```

### Step 26: اجرای پروب‌های runtime برای backend ACها با Smart Navigation
**Status:** `done` (100%)
**Scope:** این مرحله شامل اجرای پروب‌های UI (با Smart Navigation) و پروب‌های backend log برای acceptance criteriaهای backend است. اگر task_type 'backend' یا 'mixed' باشد، برای هر AC که backend است، یک پروب لاگ اجرا می‌شود. اگر task_type 'unknown' باشد، هیچ پروبی اجرا نمی‌شود. این مرحله بخشی از فاز 3 است و نتایج به runtime_probe_results اضافه می‌شوند.
**Excerpt:**
```
# Phase 3 system probe + per-step probes (با Smart Navigation اضافه)
    runtime_probe_results.extend(await run_ui_probes(...))

if task_type in ('backend', 'mixed'):
    # Backend Log Probe برای backend AC ها
    for ac in acceptance_criteria:
        if _is_backend_ac(ac):
            res = await run_backend_log_probe(ac, ctx, ac_id, task)
            runtime_probe_results.append(res)

if task_type == 'unknown':
```

### Step 27: پیاده‌سازی سه پروب جدید (Smart Navigation، Backend Log، Code-aware) در Oversight Runtime
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی کامل سه نوع پروب جدید در runtime verification است: Smart Navigation (navigation_helper.py)، Backend Log Probe (backend_log_probe.py)، و Code-aware Verifier (code_aware_verifier.py). همچنین شامل تغییرات در oversight_verifier.py برای routing task type، تغییرات در inspector_probe.py برای hook Smart Navigation، به‌روزرسانی oversight_mega_bundle.py برای سه سکشن جدید، و تغییرات UI در frontend برای نمایش سه آیکن جدید (🧭 📊 🔍) است. محدودیت‌های سراسری شامل AI cost cap (۲ call per probe)، time cap (۹۰ ثانیه per task)، graceful fallback در صورت failure، و عدم نشت credentials است. ترتیب پیاده‌سازی در ۸ commit جداگانه مشخص شده است. بخش‌های موجود (Phase 1, 2, 3 + سه فیکس) نباید شکسته شوند.
**Excerpt:**
```
══════════════════════════════════════════════════════════════════════

Telegram Integration
══════════════════════════════════════════════════════════════════════

mega-bundle.md سکشن‌های جدید:

۸.۱ Smart Navigation Decisions
چه nav linksای پیدا شد؟ AI چی انتخاب کرد؟
confidence + reason per task
۸.۲ Backend Log Analysis (per backend AC)
verdict (deployed_working / not_deployed / ...)
evidence_lines
reason
۸.۳ Code-aware Verdict (per AC)
code_verdict
matching_commits
key_changes excerpts
reason
══════════════════════════════════════════════════════════════════════

UI Changes — Minimal
══════════════════════════════════════════════════════════════════════

inline probe row حالا سه نوع probe جدید را نمایش می‌دهد:

🧭 smart-nav probe (با link انتخاب‌شده)
📊 backend-log probe (با verdict color)
🔍 code-aware probe (با matching commits)
هر کدام آیکن متفاوت و رنگ متمایز.

══════════════════════════════════════════════════════════════════════

Done Definition (سخت‌گیر)
══════════════════════════════════════════════════════════════════════

Smart Navigation کار می‌کند: روی یک تسک با AC که /path ندارد،
probe به home می‌رود، nav menu را می‌خواند، AI لینک مرتبط را
انتخاب می‌کند، روی آن کلیک می‌کند، و ادامه probe می‌دهد.
Backend Log Probe کار می‌کند: روی یک تسک backend (مثل
DebateAttachment)، به‌جای probe UI، probe جدیدی لاگ‌های Render
فیلتر شده را تحلیل می‌کند و verdict می‌دهد.
Code-aware Verifier کار می‌کند: برای هر AC، یک code_probe در
runtime_probe_results ظاهر می‌شود با verdict (implemented /
not_found / ...).
task type classification درست است: تسک trading-system →
"mixed" یا "backend"، تسک "ساخت صفحه login" → "ui".
هیچ بخش موجود از کار نیفتد: Phase 1, 2, 3 + سه فیکس + همه‌ی
تغییرات اخیر.
mega-bundle شامل سکشن‌های جدید: بخش ۸.۱ smart nav، ۸.۲
backend log، ۸.۳ code-aware.
UI inline سه آیکن جدید نمایش می‌دهد.
type-check + python ast پاس.
══════════════════════════════════════════════════════════════════════

محدودیت‌های سراسری
══════════════════════════════════════════════════════════════════════

per-probe AI cost cap: ۲ AI call (یکی link picker، یکی verdict)
per-task additional time: حداکثر ۹۰ ثانیه (روی Phase 3 ۶۰ثانیه)
AI provider failure → graceful fallback به Phase 3 behavior
لاگ‌های Render اگر در DB نبود (سرویس log_stream_service غیرفعال) →
Backend Log Probe SKIPPED با reason صریح
GitHub API rate limit → Code-aware Verifier ممکن است partial باشد
هرگز credentials در لاگ یا inspector_session نشت نکند
══════════════════════════════════════════════════════════════════════

فایل‌های نهایی
══════════════════════════════════════════════════════════════════════

Backend جدید
verify_runtime/navigation_helper.py (Smart Navigation A)
verify_runtime/backend_log_probe.py (Backend Log Probe B)
verify_runtime/code_aware_verifier.py (Code-aware Verifier C)
Backend تغییر
verify_runtime/inspector_probe.py (Smart Navigation hook)
verify_runtime/runner.py (task type routing)
oversight_verifier.py (orchestration + _classify_task_type +
hooks for backend/code probes)
oversight_mega_bundle.py (سه سکشن جدید در bundle)
Frontend
oversight/page.tsx (سه آیکن جدید: 🧭 📊 🔍)
══════════════════════════════════════════════════════════════════════

شکست‌خوردگی‌های مجاز (graceful degrade)
══════════════════════════════════════════════════════════════════════

AI link picker fail → fallback به skip (Phase 3 behavior)
nav menu خالی → skip smart navigation
Render logs خالی → backend log probe skipped
GitHub API timeout → code-aware verifier skipped per AC
task type "unknown" → fallback به همه (UI + Backend + Code)
AI cost overrun → فقط همان probe skipped، بقیه ادامه
══════════════════════════════════════════════════════════════════════

ترتیب پیاده‌سازی (commits جداگانه)
══════════════════════════════════════════════════════════════════════

Commit 1: _classify_task_type در oversight_verifier.py
Commit 2: code_aware_verifier.py (per-AC commit analysis)
Commit 3: backend_log_probe.py (با endpoint extraction)
Commit 4: navigation_helper.py + integration in inspector_prob
```

### Step 28: Phase 5: Logic Audit — بررسی هدف، منطق و coherence در auto-scan و task creation
**Status:** `done` (100%)
**Scope:** این فاز به پیاده‌سازی Logic Audit می‌پردازد که شامل بررسی هدف (purpose)، منطق (logic) و coherence (انسجام) در فرآیند auto-scan و task creation است. این فاز مستقیماً بندهای R10 و R11 درخواست خام را پوشش می‌دهد. R11 یک مثال از باگ منطقی در هماهنگی (trade) ارائه می‌دهد که باید در Logic Audit شناسایی شود. این فاز شامل پیاده‌سازی یک سرویس یا تابع جدید برای Logic Audit نیست، بلکه منطق موجود در oversight_verifier.py و oversight_strong_prompt.py را برای شناسایی ناسازگاری‌ها و خطاهای منطقی ارتقا می‌دهد. خروجی این فاز باید قابلیت شناسایی خودکار مواردی مانند 'trade با قیمت خرید بالاتر از فروش' یا 'تسک‌های متناقض' باشد.
**Excerpt:**
```
| **R10** | Logic Audit (هدف، منطق، coherence) | فاز ۵ |
| **R11** | مثال trade — باگ منطقی در هماهنگی | فاز ۵ |

این فاز به پیاده‌سازی Logic Audit می‌پردازد که شامل بررسی هدف (purpose)، منطق (logic) و coherence (انسجام) در فرآیند auto-scan و task creation است. R11 یک مثال از باگ منطقی در هماهنگی (trade) ارائه می‌دهد که باید در Logic Audit شناسایی شود.
```

### Step 29: تعریف فلسفه و معماری ماژول Scan (Phase 5) و تمایز آن از Verify (Phase 4)
**Status:** `done` (100%)
**Scope:** این بخش فلسفه کلی ماژول Scan را تعریف می‌کند: scan ≠ verify، scan قوی‌تر از verify است، و چهار پایه اصلی (پوشش ریز تا درشت، تغییر-آگاهی، رفتار-محوری، logic awareness) را مشخص می‌کند. هدف نهایی کشف و ساخت تمام تسک‌های واقعاً لازم (features جدید/ناقص، bugs ساختاری/منطقی، features قدیمی، componentهای ناسازگار، notification های ناقص) است. این بخش شامل پیاده‌سازی کد نیست، بلکه معماری و الزامات سطح بالا را تعریف می‌کند.
**Excerpt:**
```
## 📌 مقدمه و فلسفه
### **R1** — scan ≠ verify
| سیستم | چه می‌کند |
|---|---|
| **verify** (Phase 4، تمام) | روی **تسک‌های موجود** بررسی می‌کند آیا انجام شده یا نه |
| **scan** (این Phase 5) | کل سیستم را بررسی می‌کند تا **تسک‌های واقعاً لازم** کشف و ایجاد شوند |
اگر scan خوب کار نکند → تسک واقعاً لازم اصلاً ساخته نمی‌شود → verify هرگز فرصت بررسی آن را پیدا نمی‌کند. **پس scan حتی از verify مهم‌تر است.**
### **R4** — scan باید قوی‌تر از verify باشد
verify شواهد جمع می‌کند برای **یک task مشخص**. scan شواهد جمع می‌کند برای **کل سیستم**. پس scan ابزارهای بیشتری نیاز دارد:
- همه‌ی Phase 4 components (smart_nav, vision, code-aware, backend-log, inspector_probe)
- **به‌علاوه**: comprehensive inventory، purpose extraction، delta analysis، logical coherence، outcome analysis، notification audit، semantic stale detection
### **چهار پایه**
1. **پوشش ریز تا درشت** (R3)
2. **تغییر-آگاهی + bidirectional dependency** (R7)
3. **رفتار-محوری در پرامپت و چک‌لیست** (R9, R13)
4. **logic awareness از روز اول — purpose، coherence، effectiveness** (R10, R11)
### **هدف نهایی**
بعد از یک scan، **تمام تسک‌های واقعاً لازم** کشف و ساخته شوند، **با چک‌لیست هوشمند، با notification صحیح، با session بازرس کامل**:
- features جدید
- features ناقص
- bugs ساختاری
- bugs منطقی (R11)
- features قدیمی و dead options (R8)
- componentهای منطقاً ناسازگار (R10)
- featuresی که کاربر دیگر نمی‌داند چیست (R8) → با AI explanation
- notification ها ناقص یا اشتباه (R12)
```

### Step 30: فاز ۱ — Comprehensive Inventory + Purpose Extraction
**Status:** `done` (100%)
**Scope:** این بخش شامل دو ماژول جدید است: comprehensive_inventory.py برای جمع‌آوری ۱۲ لایه از inventory (فایل‌ها، endpoints، UI elements، DB schema، env vars، configs، dependencies، scripts، cron/scheduled، routes، notification calls، UI options/settings) و purpose_extractor.py برای استخراج purpose هر آیتم inventory. همچنین شامل اضافه کردن سه فیلد جدید به WatchedProject برای ذخیره نتایج اسکن است. Acceptance Criteria شامل حداقل ۵۰ backend endpoint، ۳۰ UI element، ۱۰ notification call، پوشش کامل UI options، purpose_map برای ≥۸۰% فایل‌های مهم، و creation_context برای هر UI option است.
**Excerpt:**
```
## 🅰️ فاز ۱ — Comprehensive Inventory + Purpose Extraction
> پوشش **R3** (ریز تا درشت)، پایه برای همه فازهای بعدی
### مسئله
الان `run_deep_scan` فقط ۳۵ فایل deep-read + import graph می‌بیند. backend endpoints، UI elements، DB schema، env vars، configs، **notifications، inspector sessions، UI options** هرگز inventory نمی‌شوند.
### تغییرات
**۱-A. Structural Inventory (۱۲ لایه):**
ماژول جدید: `backend/app/services/scan_v5/comprehensive_inventory.py`
| # | لایه | چه چیزی جمع می‌شود | روش |
|---|---|---|---|
| 1 | Files | همه فایل‌های git-tracked | `git ls-files` |
| 2 | Backend endpoints | همه `@router.{get,post,…}` + WebSocket + background tasks | AST parse |
| 3 | UI elements | همه `<button>`, `<form>`, `<input>`, `<Select>`, `<Link>`, modal triggers, dropdown items | parse `.tsx` |
| 4 | DB schema | همه dataclass + Column + migrations | inspect |
| 5 | Env vars | همه `os.environ.get`, `os.getenv`, `process.env.X` | regex |
| 6 | Config files | همه `.json`, `.yaml`, `.toml`, `.env*` | glob |
| 7 | Dependencies | `requirements.txt`, `package.json` | parse |
| 8 | Scripts | همه `.sh`, `pyproject::scripts`, `package.json::scripts` | parse |
| 9 | Cron/scheduled | همه `apscheduler`, `BackgroundTasks`, `asyncio.create_task` | regex |
| 10 | Routes | همه frontend `app/**/page.tsx` + backend route | walk |
| 11 | **Notification calls (R12)** | همه `notify_event(...)`, `send_telegram(...)`, `bot.send_message(...)` + event_type + silent flag + caption template | regex/AST |
| 12 | **UI options/settings (R8)** | همه checkbox/slider/dropdown در UI + field name در WatchedProject + default value | parse + cross-ref |
**۱-B. Purpose Extraction (R10):**
ماژول جدید: `backend/app/services/scan_v5/purpose_extractor.py`
برای **هر file/module/feature/option** که در inventory هست:

```python
purpose_inventory[item_id] = {
    "stated_purpose": "چه کاری *قرار است* بکند",
    "evidence_sources": ["comments", "docstrings", "tests", "raw_idea", "task_history", "commit_messages"],
    "expected_inputs": [...],
    "expected_outputs": [...],
    "interacting_with": [...],          # سایر componentهای همکار
    "creation_context": {                # R8 — کاربر فراموش کرده چی هست
        "first_seen_commit": "...",
        "first_seen_date": "...",
        "originating_task_id": "...",    # کدام task این را ساخت
        "originating_raw_idea": "...",   # متن خام درخواست
    },
    "current_usage": "...",              # آیا هنوز استفاده می‌شود؟ کجا؟
}
```

**منابع AI برای purpose:**
- محتوای فایل + docstrings + JSDoc
- test files مرتبط
- `WatchedProject.user_notes` (raw_idea اصلی پروژه)
- task history (task هایی که این item را modify کرده‌اند)
- commit messages روی این path
**۱-C. Storage:**
`WatchedProject` فیلدهای جدید:

```python
last_scan_inventory: Optional[Dict[str, Any]] = None
last_scan_purpose_map: Optional[Dict[str, Dict]] = None
last_scan_at_v5: Optional[str] = None  # timestamp scan جدید
```

### Acceptance Criteria فاز ۱
- `inventory.backend_endpoints` ≥ ۵۰
- `inventory.ui_elements` ≥ ۳۰
- `inventory.notification_calls` ≥ ۱۰
- `inventory.ui_options` همه‌ی checkbox/slider/dropdown ها را شامل شود
- `purpose_map` برای ≥ ۸۰% فایل‌های مهم
- برای هر UI option، `creation_context` نشان دهد از کدام task ساخته شد
```

### Step 31: فاز ۲ — Stale Detection + Feature Inventory Panel
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی کامل تشخیص اجزای قدیمی (Stale) در دو دسته Structural (۸ نوع) و Semantic (۵ نوع)، تولید مستندات AI برای هر گزینه UI، ایجاد پنل Feature Inventory در صفحه oversight، و تولید Task برای هر آیتم قدیمی است. فایل‌های جدید: backend/app/services/scan_v5/stale_detector.py. فایل‌های موجود: frontend/src/app/oversight/page.tsx. خروجی این فاز شامل حداقل ۵ structural stale، ۳ semantic stale، ۸ hidden-purpose option، و پنل با حداقل ۲۰ مدخل است.
**Excerpt:**
```
## 🅱️ فاز ۲ — Stale Detection + Feature Inventory Panel
> **مهم‌ترین فاز برای R8 — حل مشکل «گزینه‌های قدیمی که نمی‌دانم چی هست»**
### مسئله (R8 — تأکید سه‌باره)
> «خیلی‌هاش قدیمیه و کار نمی‌کنه و خیلی‌هاش نیاز داره بدونم چی بوده، برای چیه و هر سری باید بهش سر بزنم»
### تغییرات
**۲-A. Structural Stale (۸ نوع):**
ماژول جدید: `backend/app/services/scan_v5/stale_detector.py`
| نوع | شناسایی |
|---|---|
| Dead UI buttons | onClick handler ندارد / empty / به endpoint 404 می‌رود |
| Dead frontend routes | در nav menu نیست و در هیچ Link/router.push نیست |
| Dead backend endpoints | در هیچ frontend fetch نیست + در Render logs ۳۰ روز اخیر صدا نشد |
| Unused functions/classes | reverse import = 0 و entry point نیست |
| Unused dataclass fields | در هیچ‌جا read/write نمی‌شود |
| Unused env vars | تعریف شده ولی هیچ `os.environ.get` |
| Orphan files | reverse import = 0 |
| Stale dependencies | در requirements/package.json هست ولی import نمی‌شود |
**۲-B. Semantic Stale (R10 — ۵ نوع):**
| نوع | شناسایی |
|---|---|
| Purpose-mismatched | `stated_purpose` با `actual_behavior` نمی‌خواند |
| Hidden purpose (R8) | کاربر نمی‌داند چی هست — هیچ doc، نام مبهم، creation_context قدیمی |
| Inconsistent با تغییرات اخیر | کد فرض می‌کند رفتار قدیمی X، ولی X تغییر کرده (نیاز به فاز ۳) |
| Outdated business assumption | threshold/config که با realities فعلی نمی‌خواند |
| Forgotten by user (R8 — جدید) | UI option/setting که کاربر هر بار باید بپرسد چی هست |
**۲-C. AI-Generated Documentation برای هر option (R8):**
برای **هر** UI option/setting/feature/button که در inventory.ui_options یا inventory.ui_elements هست:

```python
ai_documentation[option_id] = {
    "name": "...",
    "what_it_does": "AI explanation — این گزینه دقیقاً چه کاری می‌کند",
    "when_added": "تاریخ + commit",
    "originating_idea": "متن خام درخواست اولیه",
    "current_status": "active | possibly_stale | broken | unknown",
    "dependencies": ["..."],         # forward
    "dependents": ["..."],           # reverse
    "recommended_action": "keep | remove | refactor | document"
}
```

**۲-D. Feature Inventory Panel در UI:**
`frontend/src/app/oversight/page.tsx` — اضافه شدن panel جدید:

```
🗺 Feature Inventory
├─ 🔧 Settings (12)
│   ├─ ✓ verify_mode (active — Phase 4, از task #abc1234)
│   ├─ ✓ dedup_threshold (active — Phase 3)
│   ├─ ⚠️ confirmation_streak_required (possibly_stale — ۹۰ روز unused)
│   └─ ...
├─ 🎛 UI Buttons (45)
├─ 🌐 Backend Endpoints (78)
└─ ⚙️ Env Vars (23)
```

برای هر مدخل: hover → AI explanation کامل.
**۲-E. Task Generation:**
برای هر stale item:
- **cleanup** task (structural) یا **audit** task (semantic) یا **document** task (hidden purpose)
- AC رفتار-محور: «یا حذف شود، یا با docstring/comment توضیح داده شود چرا نگه داشته، یا ارتقا یابد»
- priority بر اساس impact
### Acceptance Criteria فاز ۲
- روی این پروژه ≥ ۵ structural stale + ≥ ۳ semantic stale + ≥ ۸ hidden-purpose options
- Feature Inventory Panel با ≥ ۲۰ مدخل
- هر stale → task با explanation کامل (نه فقط «این unused است»)
- روی project trade مثال کاربر (R11)، scan تشخیص دهد گزینه‌هایی که برای trading فعلاً ضرر می‌دهند
```

### Step 32: پیاده‌سازی تشخیص دلتا، وابستگی دوطرفه و تحلیل تاثیر منطقی در اسکن v5
**Status:** `done` (100%)
**Scope:** این مرحله شامل پیاده‌سازی کامل فاز ۳ است: ذخیره state قبلی در WatchedProject، تشخیص ۶ نوع تغییر (add/remove/modify/rename/move/signature-change)، تحلیل وابستگی دوطرفه (import-based و logical) در ماژول جدید dependency_analyzer.py، تحلیل تاثیر منطقی با AI روی تغییرات و dependents، و تولید task برای فایل‌های تغییر کرده و dependentهای در معرض خطر. فایل‌های خارج از scope: backend/app/services/oversight_* و frontend/src/app/oversight/page.tsx و tests/integration/test_runtime_verify.py.
**Excerpt:**
```
## 🅲️ فاز ۳ — Delta Detection + Bidirectional Dependency + Logical Impact
> پوشش **R7** — کاربر صریحاً bidirectional خواست
### مسئله (R7)
> «چه وابستگی‌هایی داشته **به چه چیزهایی وابسته بوده** و **چه چیزهایی بهش وابسته بودن**»
این **دو طرفه** است:
- forward: این فایل به چه چیزی وابسته است
- reverse: چه چیزهایی به این فایل وابسته‌اند
### تغییرات
**۳-A. ذخیره prev state:**
`WatchedProject`:
```python
prev_scan_state: Optional[Dict[str, Any]] = None
# {file_path → {sha, size, last_modified, imports_hash, purpose_hash, ui_elements_hash}}
```
**۳-B. compute delta — ۶ نوع (R7: «تغییر کرده یا اضافه شده یا کم شده یا ویرایش شده»):**
| نوع | تشخیص |
|---|---|
| `add` | در current، نه در prev |
| `remove` | در prev، نه در current |
| `modify` | sha متفاوت |
| `rename` | sha مشابه، path متفاوت |
| `move` | content مشابه، path متفاوت |
| `signature-change` | نام تابع ثابت، parameters یا return-type تغییر |
**۳-C. Bidirectional Dependency (R7 صریح):**
ماژول جدید: `backend/app/services/scan_v5/dependency_analyzer.py`
برای هر changed file:
```python
{
    "dependencies": [...],   # forward — file → چه چیزی import می‌کند
    "dependents": [...],     # reverse — چه چیزهایی → این file import می‌کنند
    "logical_dependencies": [...],   # forward منطقی — کدام components روی این تکیه دارند
    "logical_dependents": [...],     # reverse منطقی — این از کدام components انتظار دارد
}
```
تمایز بین **import-based** و **logical**:
- import: AST/grep
- logical: AI روی purpose_inventory تشخیص می‌دهد (مثلاً «این تابع threshold X را می‌خواند، اگر X تغییر کرد رفتار تغییر می‌کند»)
**۳-D. Logical Impact Analysis (R10):**
AI روی هر تغییر + dependents تحلیل می‌کند:
- آیا تغییر این فایل، **منطق** dependents را می‌شکند؟
- مثال: تغییر `threshold=0.65` → `threshold=0.8` → چه componentهای dependent behavior متفاوت نشان می‌دهند؟
- مثال: تغییر فرمت output `parse_signal()` → چه callerها به update نیاز دارند؟
- مثال: حذف یک env var → چه قسمت‌هایی crash می‌کنند؟
**۳-E. Task Generation:**
برای هر changed file + dependent در خطر:
- task با badge `🔄 وابسته به تغییر`
- AC رفتار-محور: «بعد از این تغییر، dependents X و Y باید همچنان behavior Z تولید کنند»
- اگر logical impact پیچیده است → priority بالاتر + reference به scan inspector session
### Acceptance Criteria فاز ۳
- بعد از دو scan متوالی، delta با ۶ نوع تشخیص داده شود
- اگر signature تغییر کرد و ۳ caller دارد، ≥ ۱ task برای بررسی caller ها
- logical impact detection: اگر threshold تغییر کرد، AI تحلیل کند نه فقط alert سینتکسی
- bidirectional dependency: هم dependencies (forward) هم dependents (reverse) برای هر changed item
```

### Step 33: فاز ۴: Runtime Discovery + Outcome + Inspector Session — پیاده‌سازی کامل Inspector Tab Integration و Session Management
**Status:** `done` (100%)
**Scope:** این بخش شامل چهار زیربخش اصلی است: (۱) Runtime Discovery با ماژول جدید runtime_discovery.py که routes زنده، 404ها، endpoints فراخوانی‌شده، UI features و recent commits را کشف می‌کند. (۲) Outcome Data Collection برای انواع پروژه (Trading, AI/Chat, Web service, Scheduling, Notification). (۳) Scan Inspector Session که یک session باز می‌کند، تمام AI calls, Playwright actions, screenshots, probe outputs را ثبت می‌کند و در پایان bundle PDF + Telegram message ارسال می‌کند. (۴) اضافه شدن Tab 'Scan Sessions' در Inspector UI. نکته حیاتی: این فاز صراحتاً می‌گوید 'این مهم‌ترین آپشن از قلم افتاده' و نیازمند ایجاد دو ماژول جدید است. Acceptance Criteria شامل ≥۱۰ پیام در session، ≥۵ screenshot، Telegram + PDF، badge 🔍 Scan در Inspector tab.
**Excerpt:**
```
## 🅳 فاز ۴ — Runtime Discovery + Outcome + Inspector Session
> پوشش **R14** — Inspector tab integration — این مهم‌ترین آپشن از قلم افتاده
### مسئله (R14 صریح)
کاربر گفت: «در بررسی‌های عمیق از تب بازرس ویژه هم کمک می‌گیره و **اسکرین‌ها** رو می‌گیره و در تلگرام **همراه با گزارش** بفرسته و **چت‌ها** رو در یه session ثبت کنه و **بایگانی** کنه؟»
این **اصلاً در پرامپت‌های قبلی نبود**. فعلاً Inspector فقط در verify (Phase 4) استفاده می‌شد.
### تغییرات
**۴-A. Runtime Discovery (با ایده از Phase 4):**
ماژول جدید: `backend/app/services/scan_v5/runtime_discovery.py`
| منبع | استفاده |
|---|---|
| `navigation_helper::extract_nav_links_from_page` | nav links واقعی frontend |
| Playwright on each route | screenshot + status code → 404 detection |
| `backend_log_probe::_fetch_relevant_logs` 30-day | endpoints واقعاً called شده |
| `vision_helper::analyze_screenshot` | کشف feature های UI |
| `code_aware_verifier::_fetch_recent_commits_with_diff` | recent commits context |
خروجی: `runtime_state` شامل `routes_alive[]`, `routes_404[]`, `endpoints_called_recently[]`, `endpoints_never_called[]`, `ui_features_visible[]`, `recent_commits[]`.
**۴-B. Outcome Data Collection:**
برای هر پروژه، scan تلاش کند outcome data بیابد:
| نوع پروژه | outcome data |
|---|---|
| Trading | trade logs, P&L history |
| AI/Chat | conversation outcomes |
| Web service | error rates, latency from logs |
| Scheduling | task completion rates |
| Notification | delivery + open rates |
روش‌ها: Render logs filtered + DB tables outcome-naming + file artifacts.
**۴-C. Scan Inspector Session (R14 — حیاتی):**
ماژول جدید: `backend/app/services/scan_v5/scan_inspector_session.py`
**هر scan یک inspector session باز می‌کند** (مشابه verify در Phase 4):
```python
session = create_scan_inspector_session(
    watched_id=...,
    scan_id=...,
    project_name=...,
)
```
**در طول scan:**
- همه AI calls (purpose extraction، stale detection، logic audit، etc.) → پیام در session با role="ai", content=request+response
- همه Playwright actions → پیام با role="action", screenshot=path
- همه screenshot ها → ذخیره روی disk + reference در session
- runtime probe outputs → پیام با role="probe"
**در پایان scan:**
- session archived
- screenshots → آرشیو شده در Telegram (مثل bundle Phase 4)
- bundle PDF تولید می‌شود شامل:
  - findings + tasks ایجاد شده
  - delta summary
  - logic audit findings
  - inventory summary
  - تمام screenshots
- Telegram message + PDF attachment
- در UI، scan session در inspector tab با badge `🔍 Scan Session` (متمایز از `🔬 Verify Session`)
**۴-D. اضافه شدن tab "Scan Sessions" در Inspector UI:**
`frontend/src/app/projects/[id]/page.tsx` (یا هر جا که inspector tab هست):
- علاوه بر لیست verify sessions، scan sessions هم نمایش داده شوند
- کاربر بتواند هر scan session را باز کند و تمام مکالمات + screenshots آن را ببیند
- archive option
### Acceptance Criteria فاز ۴
- بعد از هر scan، یک inspector session با ≥ ۱۰ پیام (AI calls + actions + probes) ساخته شود
- ≥ ۵ screenshot ذخیره شود
- Telegram message + bundle PDF با همه‌ی screenshots و findings ارسال شود
- در Inspector tab، session آرشیو شده دیده شود با badge `🔍 Scan`
- اگر runtime discovery فعال است، روی هر route یک screenshot + Vision analysis
```

### Step 34: فاز ۵: Logical Audit — تشخیص ناهماهنگی منطقی، ضدالگوها و اثربخشی خروجی
**Status:** `done` (100%)
**Scope:** این فاز شامل ۵ زیربخش است: (A) تشخیص انسجام زنجیره‌های پردازش (Pipeline Coherence)، (B) تشخیص ضدالگوهای منطقی (Anti-pattern)، (C) کشف نیازمندی‌های پنهان (Hidden Requirements)، (D) ممیزی اثربخشی مبتنی بر خروجی (Outcome-based Effectiveness)، و (E) تولید تسک‌های `logic_audit` با AC outcome-oriented. خارج از scope: اجرای واقعی تغییرات کد (فقط تحلیل و تولید تسک)، و هرگونه اسکن امنیتی یا عملکردی. نکته حیاتی: این فاز صرفاً تحلیل معنایی و منطقی است و نباید به اجرای خودکار تغییرات منجر شود.
**Excerpt:**
```
## 🅴 فاز ۵ — Logical Audit (Coherence + Anti-pattern + Outcome)
> پوشش **R10, R11** — مهم‌ترین فاز معنایی
### مسئله (R10, R11)
> «یه پروژه دارم که هوشمند ترید کنه ولی بدتر از یه آدم معمولی ترید می‌کنه — باگ منطقی در هماهنگی بین AI و داده‌ها»
scan نباید **فقط خطاها** را ببیند، بلکه **منطق و هدف** را هم.
### تغییرات
**۵-A. Pipeline Coherence Detection:**
ماژول جدید: `backend/app/services/scan_v5/coherence_analyzer.py`
شناسایی pipelines (chains از componentهای همکار) با استفاده از `purpose_inventory[X].interacting_with`.
برای هر chain، AI بررسی coherence:
| الگو | چه بررسی شود |
|---|---|
| **Data pipeline** | schema هر مرحله، handling empty result |
| **AI/LLM chain** | prompt format ↔ model ↔ parser سازگار؟ validation؟ |
| **Business logic (R11 مثال trade)** | signal ↔ risk model، position ↔ account size، stop-loss ↔ timeframe |
| **Auth/Permission** | همه‌ی mutation از permission گذر می‌کند؟ |
| **Feedback loop** | outcome به config/model برمی‌گردد؟ |
| **Notification chain (R12)** | event → notify_event → caption → silent decision → delivery — همه consistent؟ |
**۵-B. Logical Anti-pattern Detection:**
ماژول جدید: `backend/app/services/scan_v5/anti_pattern_detector.py`
AI روی purpose_inventory + کد، این الگوها را پیدا می‌کند:
| Anti-pattern | مثال |
|---|---|
| داده بی‌مصرف | API call، DB write، ولی هیچ read |
| AI بدون validation | response parse می‌شود ولی validity چک نمی‌شود |
| Magic threshold | `> 0.65:` بدون توضیح |
| Conflicting defaults | یک field default متفاوت در جاهای مختلف |
| Silent failure در crucial path | `except: pass` در business logic |
| Broken feedback loop (R11) | outcome لاگ ولی به model نمی‌رسد |
| Stale assumption | کد فرض می‌کند رفتار سرویس X خاصه، X تغییر کرد |
| Over/under-engineering | برای ساده ۵ لایه، برای پیچیده hardcode |
| Conditional inconsistency | conditions با تغییرات اخیر inconsistent |
| Threshold-Outcome mismatch (R11) | parameters نتایج مطلوب تولید نمی‌کنند |
| Notification mismatch (R12) | event critical ولی silent=True، یا opposite |
**۵-C. Hidden Requirements Discovery (R8):**
برای هر feature که کاربر فراموش کرده «چی هست برای چیه»:
- AI روی `creation_context` (از فاز ۱) + task history + commit messages تحلیل
- استخراج: «این feature چه وقت، چرا، با چه هدفی اضافه شد؟»
- نتیجه:
  - هدف منسوخ → task `cleanup`
  - هدف معتبر، پیاده‌سازی ضعیف → task `refactor`
  - هدف معتبر، پیاده‌سازی خوب، docs نیست → task `document`
**۵-D. Outcome-based Effectiveness Audit (R11):**
اگر outcome data دارد (از فاز ۴):
- AI تحلیل می‌کند آیا outcome با `stated_purpose` می‌خواند
- مثال R11: trade — اگر purpose="earn profit" و win-rate=30% → effectiveness LOW
- اگر LOW → task `logic_audit` با priority بالا
**۵-E. Task Generation:**
نوع جدید task: `logic_audit`
- AC outcome-oriented:
  - ❌ «این کد را fix کن»
  - ✅ «بعد از این تغییر، win-rate باید ≥40% یا parameters محافظه‌کارانه‌تر شود»
- AI explanation کامل: چرا اشتباه + چه راه‌حل + چه impact
### Acceptance Criteria فاز ۵
- روی پروژه فعلی ≥ ۳ logic issue + ≥ ۱ pipeline coherence + ≥ ۲ anti-pattern logical
- روی پروژه trade فرضی (R11)، scan باگ منطقی هماهنگی AI-data شناسایی کند
- task `logic_audit` با AC outcome-oriented + AI explanation کامل
```

### Step 35: فاز ۶ — Notification System Audit: بررسی و بهینه‌سازی سیستم اطلاع‌رسانی (R12)
**Status:** `done` (100%)
**Scope:** این مرحله شامل ممیزی کامل تمام notification‌های موجود در کد (notify_event calls)، ایجاد inventory از آن‌ها، بررسی انسجام و کامل بودن caption‌ها، تنظیم silent/sound مناسب، بررسی attachments، جلوگیری از spam، شناسایی notification‌های قدیمی یا گمشده، و ارائه پیشنهادات ارتقا برای notification scan_completed است. همچنین شامل ایجاد task‌های notification_audit برای هر مورد مشکل‌دار و تنظیم فیلدهای جدید WatchedProject.auto_task_notify_sound و WatchedProject.scan_notify_sound به False می‌شود. فایل‌های هدف: notification_service.py, oversight_telegram_compose.py, oversight_mega_bundle.py.
**Excerpt:**
```
## 🅵 فاز ۶ — Notification System Audit (R12)
> پوشش **R6, R12** — صریحاً audit notification ها
### مسئله (R12)
> «در پرامپت برای پیام‌رسانی تلگرام هم جایی در نظر گرفتی؟ در بررسی‌ها نوع اطلاع‌رسانیش هم بررسی بشه و بهینه بشه»
### تغییرات
**۶-A. Notification Inventory (از فاز ۱ — لایه ۱۱):**
برای هر `notify_event(...)` call در کد:

```python
notification_inventory[call_id] = {
    "file_path": "...",
    "line": ...,
    "event_type": "...",          # "task_created" | "verify_done" | ...
    "caption_template": "...",
    "silent_default": True | False | None,
    "attachments": [...],
    "trigger_condition": "...",   # کد منطق در کجا fire می‌شود
    "frequency_estimate": "...",  # احتمال در روز
}
```

**۶-B. Notification Coherence Audit (R12):**
AI روی notification_inventory:
| سوال | چه چیزی audit شود |
|---|---|
| caption کامل است؟ | همه‌ی فیلدهای مهم در caption هستند؟ (title, intent, link, attachments) |
| silent/sound مناسب است؟ | event critical → sound. event routine → silent |
| attachments صحیح؟ | task creation → prompt.md، verify done → bundle.pdf، scan done → scan-bundle.pdf |
| timing مناسب؟ | spam جلوگیری شده؟ batching هست؟ |
| stale notifications؟ | event type که دیگر کد آن وجود ندارد |
| missing notifications؟ | event critical که notification ندارد |
| **scan-specific (R12)**: | scan completion notification با همه‌ی مدارک ضروری: findings, tasks created, delta, logic audit results, inspector session reference |
```

### Step 36: فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)
**Status:** `done` (100%)
**Scope:** این فاز شامل ۶ زیربخش (۷-A تا ۷-F) است که همگی برای بهبود کیفیت پرامپت‌ها و چک‌لیست‌ها در هر دو مسیر manual و auto طراحی شده‌اند. تغییرات شامل: ساختار غنی AC با ۷ فیلد جدید، ساختار غنی task_step با ۶ فیلد، اضافه شدن حالت هوشمند چک‌لیست (auto/always/never)، به‌روزرسانی قالب‌های پرامپت در oversight_strong_prompt.py، جلوگیری از false-positive با قوانین صریح، و یکپارچه‌سازی با خروجی فازهای ۱، ۴، ۵، ۶. نکته حیاتی: backward compatibility با ACهای قدیمی (فقط text) باید حفظ شود.
**Excerpt:**
```
## 🅶 فاز ۷ — Smart Prompt + Smart Checklist (R9, R13)
> پوشش **R5, R9, R13** — برای **manual + auto** هر دو
### مسئله (R9 صریح)
> «در تولید ایده خام به پرامپت، پرامپت در برخی قسمت‌ها دقیق و واضح تولید نمیشه... باید هوشمندتر بشه خود متن پرامپت و چک‌لیستی که ازش تولید میشه»
### مسئله (R13 صریح)
> «این بهبود پرامپت‌نویسی تسک‌ها آیا فقط برای تسک‌های سیستمی یا تسک‌های دستی هم شامل میشه؟»
**جواب: هر دو.**
### تغییرات
**۷-A. ساختار غنی AC (هم manual، هم auto):**
برای **manual** path در `oversight_service.py:idea_to_prompt` (~3454):
برای **auto** path در `oversight_service.py:task creation from scan` (~4700-4740):
برای **scan-generated** path در `oversight_strong_prompt.py:build_strong_prompt`:
هر AC ساختار غنی:

```python
{
    "text": "...",                          # توضیح اصلی (می‌تواند نام بدهد)
    "behavior": "...",                      # رفتار قابل مشاهده — چه چیزی observable است
    "acceptance_signal": "...",             # سؤال قابل-verify
    "business_intent": "...",               # چرا این لازم است
    "alternative_implementations": [...],   # نام‌های جایگزین قابل قبول (R9 — جلوگیری از نام-محوری)
    "non_goals": "...",                     # چه چیزی این AC نیست
    "false_positive_guard": "...",          # چه شواهد ضعیفی نشانه done نیست (R9)
}
```

**۷-B. ساختار غنی task_step (در `_ai_plan_steps_from_idea`):**
برای manual و auto (R13):

```python
{
    "title": "...",
    "scope": "...",
    "behavior_observable": "...",       # خروجی observable
    "verification_hint": "...",         # کجا verify بیابد
    "business_intent": "...",           # چرا این مرحله
    "non_goals": "...",
}
```

**۷-C. Smart Checklist Mode (R5):**
> «حالت هوشمند که برای تولید چک‌لیست یا عدم تولیدش حسب نیاز هست»
`WatchedProject.auto_task_checklist_mode: Literal["auto","always","never"] = "auto"`
- `auto`: AI تصمیم می‌گیرد بر اساس پیچیدگی (≥3 stage → checklist، single-action → skip)
- `always`: همیشه چک‌لیست
- `never`: هرگز
این برای **هم manual و هم auto** کار می‌کند.
**۷-D. Update prompt templates:**
در `oversight_strong_prompt.py`:
- اضافه شدن section "🎯 معیار رفتاری + business intent + alternative implementations"
- AI صریح راهنمایی شود: AC نام-محور بد است، AC رفتار-محور خوب
**۷-E. جلوگیری از false-positive (R9):**
> «جوری هم نشه که سیستم کاری که بد انجام شده... در verify تیک بزنه که کامل شده»
دستورالعمل به AI:
- اگر AC vague → split به sub-behaviors concrete
- هرگز AC بدون `acceptance_signal` نسازد
- `false_positive_guard` فیلد: چه شواهد ضعیفی نباید سبب done شود
- مثال: «اگر فقط فایل با نام وجود دارد، done نیست — باید رفتار X هم باشد»
**۷-F. Integration با فازهای قبلی:**
پرامپت تولید‌شده استفاده کند از:
- `purpose_inventory` (فاز ۱)
- `runtime_state` (فاز ۴)
- `logic_audit_findings` (فاز ۵)
- `notification_audit` (فاز ۶)
### Acceptance Criteria فاز ۷
- **manual** path: پرامپت‌های جدید برای ۳ ایده‌ی نمونه شامل `behavior` + `acceptance_signal` + `business_intent` + `alternative_implementations` + `false_positive_guard`
- **auto** path: همان ساختار برای task های scan-generated
- چک‌لیست‌ها شامل `behavior_observable` در هر step
- mode `auto` در `_ai_plan_steps_from_idea` کار می‌کند برای هر دو
- verify روی same tasks: false-negative ≤ ۲۰%، false-positive ≤ ۵%
- backward compat: AC های قدیمی (فقط text) همچنان کار می‌کنند
```

### Step 37: فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration
**Status:** `done` (100%)
**Scope:** این بخش شامل ۴ زیربخش است: (۸-A) افزودن task_steps به auto-tasks در oversight_service.py با دو mode 'always' و 'auto'، (۸-B) قالب notification تلگرام برای auto-scan task با caption و attachments مشخص، (۸-C) اضافه کردن فیلدهای silent default (auto_task_notify_sound و scan_notify_sound) به WatchedProject و UI checkbox، (۸-D) notification تکمیل scan با خلاصه و Bundle PDF. خارج از scope: تغییر رفتار تسک‌های دستی (باید حفظ شود)، پیاده‌سازی Inspector session (فقط لینک)، و پیاده‌سازی actual PDF generation (فقط اشاره به Bundle PDF).
**Excerpt:**
```
## 🅷 فاز ۸ — Auto-tasks Like Manual + Full Telegram Integration
> پوشش **R5, R6** — تسک‌های scan باید مثل manual باشند
### مسئله (R5, R6)
- تسک‌های auto-scan الان `prompt + AC` دارند ولی `task_steps` ندارند
- Telegram notification برای آن‌ها audit نشده
- کاربر می‌خواهد silent default
### تغییرات
**۸-A. task_steps برای auto-tasks:**
در `oversight_service.py:4700-4740`:
- بعد از `build_strong_prompt`، اگر `auto_task_checklist_mode != "never"`:
  - if `mode == "always"` → همیشه call `_ai_plan_steps_from_idea`
  - if `mode == "auto"` → AI تصمیم می‌گیرد بر اساس پیچیدگی
**۸-B. Telegram Notification Template (R6):**
`notification_service.py`:
```python
# Caption template برای auto-scan task
{
    "🤖 تسک جدید از scan خودکار",
    "📌 {title}",
    "🎯 {business_intent[:200]}",
    "📋 چک‌لیست: {N step}" if has_steps else None,
    "🧠 Logic concerns: {logic_audit_count}" if has_logic_issues else None,
    "🔄 وابسته به تغییر: {dependent_changes}" if delta_dependent else None,
    "📊 Outcome impact: {outcome_score}" if outcome_data else None,
    "🔗 [لینک کارت]",
    "🔍 [Inspector session]",
}
# Attachments:
- prompt_full.md (full task prompt)
- scan_inspector_session_link
```
**۸-C. Silent default + UI control:**
`WatchedProject` fields:
```python
auto_task_notify_sound: bool = False     # silent for auto-tasks
scan_notify_sound: bool = False           # silent for scan completion
```
در UI: checkbox `🔔 صدای notification برای تسک‌های auto-scan`.
**۸-D. Scan-completion notification:**
علاوه بر notification هر task، یک scan-completion notification:
```
✅ scan تکمیل شد — {project_name}
📊 خلاصه:
- {N} task جدید ایجاد شد
- {N} delta change شناسایی
- {N} stale item
- {N} logic issue
- {N} notification audit
📎 Bundle PDF (با همه screenshots و findings)
🔍 Inspector session: [link]
```
### Acceptance Criteria فاز ۸
- بعد از scan: همه auto-tasks در UI چک‌لیست دارند (اگر mode=auto و پیچیده‌اند)
- caption تلگرام شامل همه فیلدها
- silent default = true
- scan_completed notification با Bundle PDF + Inspector session link
- regression: تسک‌های دستی رفتار قبلی را حفظ کنند
```

### Step 38: فاز ۹ — UI Redesign (R2, R8): بازطراحی کامل UI با ۴ تب، گزینه‌های جدید و AI explanation
**Status:** `done` (100%)
**Scope:** این بخش شامل بازطراحی کامل UI Oversight با ۴ تب (Coverage, Intelligence, Lifecycle, Notifications) به‌جای ۳ تب قبلی است. تغییرات شامل: بازنگری scan_depth modes (اضافه شدن mode‌های balanced و ultra)، بازنگری criteria_weights (preset selector + sliders در details)، بازنگری Smart Task Lifecycle با وضعیت‌سنجی هر گزینه، اضافه شدن فیلدهای جدید WatchedProject (شامل inventory_layers, stale_detection_enabled, delta_analysis_enabled, runtime_discovery_enabled, outcome_data_enabled, logic_audit_enabled, notification_audit_enabled, inspector_session_enabled, auto_task_checklist_mode, cleanup_tasks_enabled, auto_task_notify_sound, scan_notify_sound)، AI explanation برای هر گزینه با help icon و Feature Inventory Panel. backward compatibility برای scan_depth قدیمی باید حفظ شود.
**Excerpt:**
```
## 🅸 فاز ۹ — UI Redesign (R2, R8)
> پوشش **R2** — به‌روزرسانی گزینه‌ها
### مسئله (R2)
> «گزینه‌هاش هم به روز رسانی بشن»
### تغییرات
**۹-A. بازنگری scan_depth modes:**
از (فعلی):
```
quick (3 pass) | standard (6 pass) | deep (12 pass، پیش‌فرض) | thorough (12 + health + roadmap)
```
به:
```
⚡ quick (5 pass) — frontend + backend + security + delta + stale
⚖️ balanced (8 pass — پیش‌فرض جدید) — quick + dependency + completeness + runtime
🔬 deep (12 pass) — همه + impact analysis
🧠 ultra (12 pass + logic audit + outcome + notification audit + inspector session)
```
**۹-B. بازنگری criteria_weights:**
به‌جای ۶ slider:
- preset selector: "general", "security-first", "tests-first", "feature-completeness", "logic-quality"
- sliders در `<details>` (advanced)
**۹-C. بازنگری Smart Task Lifecycle:**
- بررسی هر گزینه: کار می‌کند؟
- label با وضعیت فعلی
**۹-D. گزینه‌های جدید Phase 5:**
`WatchedProject` فیلدهای جدید (همه با default sensible):
```python
# Coverage
inventory_layers: List[str] = ["all"]    # یا subset
# Intelligence
stale_detection_enabled: bool = True
delta_analysis_enabled: bool = True
runtime_discovery_enabled: bool = True
outcome_data_enabled: bool = True
logic_audit_enabled: bool = True
notification_audit_enabled: bool = True
inspector_session_enabled: bool = True   # R14
# Lifecycle
auto_task_checklist_mode: str = "auto"   # R5
cleanup_tasks_enabled: bool = True
# Notifications
auto_task_notify_sound: bool = False     # R6
scan_notify_sound: bool = False          # R6
```
**۹-E. بازطراحی Layout — ۴ tabs (به‌جای ۳):**
| Tab | محتوا |
|---|---|
| **🔍 Coverage** | scan_depth + inventory_layers + criteria preset + auto_models |
| **🧠 Intelligence** | stale + delta + runtime + outcome + logic_audit + smart-prompt + inspector_session |
| **🔁 Lifecycle** | dedup + auto-regenerate + checklist mode + cleanup |
| **🔔 Notifications** | auto_task_sound + scan_sound + notification_audit + custom templates |
**۹-F. AI explanation برای هر گزینه (R8):**
هر گزینه دارای help icon ⓘ + AI-generated description (از فاز ۲):
- این گزینه دقیقاً چه می‌کند
- کِی اضافه شد
- وضعیت فعلی (active / possibly stale / unknown)
**۹-G. Feature Inventory Panel (R8):**
panel جدید در UI با لیست همه options + AI explanation (از فاز ۲).
### Acceptance Criteria فاز ۹
- در UI، ۴ tab وجود دارد
- mode `balanced` پیش‌فرض جدید
- mode `ultra` در دسترس
- backward compat: scan_depth قدیمی همچنان کار کند
- هر گزینه دارای tooltip + AI explanation
- Feature Inventory Panel functional
```

### Step 39: فاز ۱۰: Meta-validation — تبدیل پرامپت به task قابل verify و شناسایی باگ‌های verify
**Status:** `done` (100%)
**Scope:** این فاز شامل تبدیل کل پرامپت (فازهای ۱-۹) به یک task اجرایی با ACهای measurable، ایجاد حلقه iteration بین پیاده‌سازی و verify، و شناسایی باگ‌های verify (false-positive/negative) است. خروجی نهایی یک پرامپت با ۱۰ task_step است که هر step دارای behavior_observable و verification_hint است. خارج از scope: پیاده‌سازی واقعی فازهای ۱-۹، تغییر در کدهای موجود، یا ایجاد فایل‌های جدید غیر از فایل log.
**Excerpt:**
```
## 🅹 فاز ۱۰ — Meta-validation
> خود این پرامپت قابل verify باشد
### مسئله
کاربر می‌خواهد این پرامپت به task تبدیل شود و توسط verify Phase 4 سنجیده شود.
### تغییرات
**۱۰-A. این پرامپت به task تبدیل:**
- ایده‌ی خام = این متن
- AC ها = AC های هر فاز ۱-۹
- task_steps = ۱۰ فاز
**۱۰-B. AC قابل-verify دقیق:**
هر AC در هر فاز measurable نوشته شده (مثلاً «≥ ۵ stale item کشف شود»).
**۱۰-C. Iteration loop:**
- پیاده‌سازی → verify deep (Phase 4) → نتیجه
- اگر `done < 100%` → iteration بعدی
- اگر `done = 100%` → فاز بعدی
- log در `phase5_meta_validation.md`
**۱۰-D. شناسایی verify bugs:**
- اگر کار واقعاً انجام شد ولی verify گفت not_done → باگ verify
- اگر کار نشد ولی verify گفت done → باگ verify (مهم‌تر، false-positive)
- log همه‌ی این موارد
### Acceptance Criteria فاز ۱۰
- پرامپت نهایی شامل ۱۰ task_step
- هر step دارای `behavior_observable` + `verification_hint`
- بعد از پیاده‌سازی همه فازها، verify deep این task را ≥ ۱۰/۱۰ done گزارش دهد
- log باگ‌های verify identified
```

### Step 40: فاز ۱ — Comprehensive Inventory + Purpose (Round 1 پایه)
**Status:** `done` (100%)
**Scope:** این بخش اولین فاز از Round 1 است و شامل ایجاد یک فهرست جامع از تمام اجزای پروژه (Inventory) به همراه تعریف هدف (Purpose) هر جزء می‌شود. این فاز پایه‌ای برای تمام تحلیل‌های بعدی است و باید تمام فایل‌ها، کلاس‌ها، سرویس‌ها و کامپوننت‌های UI را پوشش دهد. نکته حیاتی: این فاز صرفاً مستندسازی و فهرست‌برداری است و شامل تحلیل ساختاری یا دینامیک نمی‌شود. خروجی این فاز یک گزارش کامل از موجودیت‌ها و اهدافشان است که در گزارش نهایی به صورت ریز و مشروح ذکر خواهد شد.
**Excerpt:**
```
## 🎯 ترتیب اجرا
**Round 1 — پایه:**
1. فاز ۱ — Comprehensive Inventory + Purpose
...
در گزارش نهایی باید تمام اجزایی که بررسی کرده به صورت ریز در گزارش بیاد .. حالا بخش تسک درست کردن و پرامپت و چک لیست مطابقش درست کردن که تو گزارش میاد جدا
یه گزارش جدا باید تو همون متنی که ارسال میکنه در تلگرام هم پیوستش باشه که تمام موارد رو که بررسی کرده مشروح و با جزئیات بنویسه 

اینها که زیر نوشتم و در تنظیمات هر کارت پروژه قرارداده شده باید هر کدوم توضیحات مفصلی داشته باشه و هیچ کار ناقصی پذیرفته نیست :

🗑 stale + forgotten options
🔄 delta + bidirectional dep
🌐 runtime discovery
📊 outcome data
🧠 logic audit
🔔 notification audit
🔍 inspector session
🗑 cleanup tasks
-----------------------------
🔒 امنیت:

🛠 کیفیت:

🧪 تست:

✅ کامل بودن:
```

### Step 41: رفع ۶ گپ بنیادی + ۲ بهبود اضافه در verify v2 برای کاهش false negative از ۴۰٪ به صفر
**Status:** `done` (100%)
**Scope:** این بخش شامل تحلیل و رفع ۶ گپ بنیادی (structural gaps) و ۲ بهبود اضافه در لایه‌های زیرین verify است. پایه ۵ فاز قبلی حفظ می‌شود و فقط لایه‌های زیرین تقویت می‌شوند. این بخش صرفاً تعریف گپ‌ها و بهبودهاست و شامل پیاده‌سازی نمی‌شود. خروجی این بخش یک لیست شماره‌دار با ۸ آیتم (۶ گپ + ۲ بهبود) است که باید verbatim در raw_excerpt قرار گیرد.
**Excerpt:**
```
## 🔍 ۶ گپ بنیادی + ۲ بهبود اضافه (در v2)

1. **گپ اول**: ...
2. **گپ دوم**: ...
3. **گپ سوم**: ...
4. **گپ چهارم**: ...
5. **گپ پنجم**: ...
6. **گپ ششم**: ...
7. **بهبود اول**: ...
8. **بهبود دوم**: ...
```

### Step 42: ساخت ماژول context_builder برای جمع‌آوری و ساخت VerifyContext در فرآیند verify
**Status:** `done` (100%)
**Scope:** این بخش ایجاد یک ماژول جدید به نام backend/app/services/verify_runtime/context_builder.py را مشخص می‌کند که شامل یک dataclass به نام VerifyContext و یک تابع async به نام build_verify_context است. scope شامل: تعریف کامل فیلدهای VerifyContext با caps مشخص، پیاده‌سازی تابع build_verify_context که caps را اعمال می‌کند، fetch یک‌باره repo_tree از GitHub با cache روی sha، و فراخوانی این تابع در ابتدای verify_task() به طوری که context در همه probes پاس داده شود. خارج از scope: پیاده‌سازی خود probes، logic مربوط به VerifyConfig (فقط اشاره شده)، و جزئیات caching فراتر از repo_tree.
**Excerpt:**
```
### گپ ۱ — حافظهٔ تکه‌تکه vs کامل

#### وضعیت فعلی
verify فقط AC text + commit diff + screenshot + repo tree را دارد.

#### راه‌حل
ماژول جدید: `backend/app/services/verify_runtime/context_builder.py`

ساختار `VerifyContext` dataclass:
```python
@dataclass
class VerifyContext:
    task: OversightTask                       # ref فقط
    watched: WatchedProject                   # ref فقط
    raw_idea_full: str                        # cap 50KB
    prompt_full: str                          # cap 100KB
    task_steps_full: List[Dict]               # همه (no cap چون داخل تسک)
    prompt_history: List[Dict]                # آخرین ۳ نسخه
    verify_history: List[Dict]                # آخرین ۵ گزارش
    consolidation_meta: Optional[Dict]        # اگر super-task
    merged_source_tasks: List[Dict]           # cap 30 (top by priority)
    scan_metadata: Optional[Dict]             # last_scan_metadata
    repo_tree: List[str]                      # paths only، cap 5000
    commits_recent: List[Dict]                # cap 50 commits
    # کش‌های in-memory per-verify-run
    file_content_cache: Dict[str, str] = field(default_factory=dict)
    file_grep_cache: Dict[Tuple[str, str], List[Dict]] = field(default_factory=dict)
    # observability
    trace: List[Dict] = field(default_factory=list)  # هر تصمیم append می‌شود
    config: "VerifyConfig" = ...               # ↓ بخش config
    files_fetched_count: int = 0
    grep_calls_count: int = 0
    ai_calls_count: int = 0
```

تابع `async def build_verify_context(task, watched, *, config) -> VerifyContext`:
- caps را اعمال می‌کند
- repo_tree یک‌بار از GitHub fetch می‌شود (با cache روی sha)
- در ابتدای `verify_task()` صدا زده می‌شود و در همهٔ probes پاس داده می‌شود
```

### Step 43: پیاده‌سازی ماژول code_content_searcher برای جستجوی محتوای فایل به جای commit diff
**Status:** `done` (100%)
**Scope:** این بخش شامل ایجاد ماژول جدید backend/app/services/verify_runtime/code_content_searcher.py با سه تابع async و یک تابع همزمان است. توابع fetch_file_content (دریافت محتوای فایل از GitHub API با cache و محدودیت حجم)، grep_token_in_files (جستجوی regex در محتوای فایل‌ها با context lines و cap per file)، smart_grep_for_ac (استخراج identifier از متن AC و جستجوی همه آن‌ها در target_files) و extract_identifiers (استخراج identifier با regexهای دقیق و specificity scoring) پیاده‌سازی می‌شوند. مثال‌های concrete برای extract_identifiers (4 مثال) و regexهای دقیق برای snake_case, dunder, camelCase, PascalCase, function_call, file_path و stop-words ~100 تایی و specificity score برای top-K=15 identifier نیز بخشی از این scope هستند.
**Excerpt:**
```
ماژول جدید: `backend/app/services/verify_runtime/code_content_searcher.py`

API عمومی:

```python
async def fetch_file_content(
    repo_full_name: str, path: str, ref: str = "main",
    *, token: str,
    cache: Dict[str, str],
    max_size_bytes: int = 500_000,
) -> Optional[str]
```
- GET `/repos/{owner}/{repo}/contents/{path}?ref={ref}`
- base64 decode از field `content`
- cache روی key=f"{path}@{ref}"
- skip اگر size > 500KB یا content-type غیر متنی
- بازگشت None در صورت 404/403/error
- log در `context.trace`

```python
async def grep_token_in_files(
    token: str, paths: List[str],
    repo_full_name: str, ref: str,
    *, github_token: str,
    cache: Dict[Tuple[str, str], List[Dict]],
    file_content_cache: Dict[str, str],
    context_lines: int = 2,
    max_matches_per_file: int = 5,
) -> List[Dict]
```
- regex `re.finditer(re.escape(token), content, re.IGNORECASE)`
- خروجی: `[{path, line_number, snippet, before_lines, after_lines}, ...]`
- cap per file
- cache روی key=(path, token)

```python
async def smart_grep_for_ac(
    ac_text: str, target_files: List[str],
    repo_full_name: str, ref: str,
    *, context: VerifyContext,
) -> Dict[str, List[Dict]]
```
- `identifiers = extract_identifiers(ac_text)`
- top-K=15 identifiers (sorted by specificity)
- برای هر identifier در همهٔ target_files
- خروجی: `{identifier: [match, ...]}`

```python
def extract_identifiers(text: str) -> List[str]
```

**🆕 (v2 — کاستی ۱) مثال concrete:**

```python
# مثال ۱: ورودی فارسی + identifier پایتون
text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
extract_identifiers(text) →
    ['view_preferences', 'WatchedProject']

# مثال ۲: ورودی انگلیسی + camelCase
text = "Add useViewPrefs hook for fetching preferences"
extract_identifiers(text) →
    ['useViewPrefs', 'fetching', 'preferences']  # 'Add' حذف چون stop-word

# مثال ۳: ورودی mixed با file path
text = "تابع _record_title_change در oversight_service.py"
extract_identifiers(text) →
    ['_record_title_change', 'oversight_service']

# مثال ۴: کلمات generic - باید filter شوند
text = "بهبود سیستم نمایش"
extract_identifiers(text) →
    []  # هیچ identifier specific نیست → fallback به AI
```

regex‌های دقیق:
- `snake_case`: `r"\b[a-z][a-z0-9_]{2,}\b"` (با حداقل یک underscore یا طول ≥۴)
- `dunder`: `r"\b_[a-z][a-z0-9_]+\b"`
- `camelCase`: `r"\b[a-z][a-zA-Z0-9]{3,}\b"` که حداقل یک حرف بزرگ داشته باشد بعد از index 0
- `PascalCase`: `r"\b[A-Z][a-zA-Z0-9]{3,}\b"`
- `function_call`: `r"\b(\w+)\s*\("`
- `file_path`: `r"\b[\w/.-]+\.(py|tsx?|jsx?|json|yaml|md)\b"`

stop-words (cap ~۱۰۰): فارسی + انگلیسی common words (`the, and, for, this, that, user, system, change, ...` / `بهبود, تغییر, سیستم, پروژه, ...`)

specificity score برای sort:
- length × ۱.۰
- snake_case bonus: +۲
- dunder bonus: +۳ (خیلی specific)
- file_path bonus: +۴ (خیلی specific)

خروجی: top-K=15 unique identifiers، sorted desc by specificity
```

### Step 44: AC matching با file content به‌جای basename — چهار فاز اجرایی
**Status:** `done` (100%)
**Scope:** این بخش یک orchestrator جدید به نام analyze_acs_with_content_grep تعریف می‌کند که چهار فاز (A→B→C→D) را به‌ترتیب اجرا می‌کند. هر فاز یک تابع async مجزا دارد و در صورت بازگشت done قطعی، early-exit رخ می‌دهد. منطق فازها تغییر نمی‌کند، فقط نام‌گذاری مشخص‌تر می‌شود. فاز A (basename match) و فاز B (content grep) روی target_files کار می‌کنند، فاز C (extended repo grep) و فاز D (AI judgment) فقط context می‌گیرند. خروجی هر فاز از نوع ProbeResult است.
**Excerpt:**
```
### گپ ۳ — AC matching: file content به‌جای basename

(۴ مرحلهٔ A→B→C→D، بدون تغییر منطقی — فقط نام‌گذاری مشخص‌تر)

تابع‌های جدا برای traceability:
```python
async def _phase_a_basename_match(ac, target_files, context) -> ProbeResult
async def _phase_b_content_grep(ac, target_files, context) -> ProbeResult
async def _phase_c_extended_repo_grep(ac, context) -> ProbeResult
async def _phase_d_ai_judgment(ac, context) -> ProbeResult
```

orchestrator: `analyze_acs_with_content_grep(acs, context)` که چهار phase را به‌ترتیب می‌چرخاند، هر phase که done قطعی داد، early-exit.
```

### Step 45: پیاده‌سازی ماژول iterative_orchestrator با سه مرحله اعتبارسنجی تدریجی
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی ماژول جدید `iterative_orchestrator.py` با سه iteration است: (1) استاندارد با ۴ probe و آستانه 0.8، (2) aggressive content grep با آستانه 0.7، (3) strong model escalation با زنجیره مدل‌های gpt-4o → claude-opus-4-7 → claude-sonnet-4-6 → fallback. خروجی نهایی یک `ProbeResult` aggregated و لیست تمام iteration results است. حداکثر ۳ iteration مجاز است.
**Excerpt:**
```
ماژول جدید: `backend/app/services/verify_runtime/iterative_orchestrator.py`

@dataclass
class ProbeResult:
    probe_name: str
    verdict: str  # "done" | "partial" | "not_done" | "unclear"
    confidence: float  # 0.0..1.0
    evidence: List[str]
    error: Optional[str] = None
    elapsed_ms: int = 0

async def iterative_verify_step(
    step: Dict, context: VerifyContext,
    *, max_iterations: int = 3,
) -> Tuple[ProbeResult, List[ProbeResult]]:
    """
    خروجی: (final_aggregated_result, all_iteration_results)
    """

Iteration 1 — Standard probes (~۵-۱۰s)
- vision probe (فقط اگر classification = frontend/fullstack)
- code_aware probe (basename + diff window)
- content_grep probe (smart_grep_for_ac روی target_files)
- playwright probe (اگر URL probe موجود)
aggregate → verdict + confidence
- اگر confidence ≥ 0.8 → finalize ✅
- اگر confidence < 0.8 → escalate to iteration 2

Iteration 2 — Aggressive content grep (~۱۵-۳۰s)
- file scope توسعه می‌یابد: full repo tree با filter به‌ترتیب:
  1. extensions مرتبط (py/tsx/ts/jsx/js)
  2. paths که با AC text overlap دارند
  3. cap: ۵۰ فایل اضافی
- top-K identifiers (نه فقط top-15، بلکه top-25)
- AI rerun با evidence جدید
- aggregate → verdict + confidence
- اگر confidence ≥ 0.7 → finalize ✅
- اگر < 0.7 → escalate to iteration 3

Iteration 3 — Strong model escalation (~۳۰-۶۰s)
🆕 (v2 — کاستی ۲) Model escalation tier صریح:

async def _strong_model_judgment(ac, context, prior_results):
    strong_pref = ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"]
    model_id = None
    for cand in strong_pref:
        if _model_available(cand):
            model_id = cand
            break
    if not model_id:
        model_id = pick_best_extraction_model()

ورودی به strong model:
- متن کامل AC
- تمام evidence از iteration 1 و 2
- file content snippets (cap 50KB)
- repo_tree subset مرتبط
- task.prompt full (cap 50KB)

خروجی: ProbeResult با verdict + reasoning detailed
finalize بدون escalation بیشتر (max 3).
```

### Step 46: پیاده‌سازی بهبودهای ۷، ۸ و ۹: کش per-AC، حالت رهگیری و متمرکزسازی VerifyConfig
**Status:** `done` (100%)
**Scope:** این بخش شامل سه بهبود مجزا اما مرتبط است: (۱) کش وضعیت تأیید برای هر Acceptance Criteria با هش و checksum فایل برای جلوگیری از تأیید مجدد، (۲) حالت رهگیری/مشاهده‌پذیری کامل فرآیند تأیید با ذخیره trace و endpoint جدید، (۳) متمرکزسازی تمام تنظیمات تأیید در یک کلاس VerifyConfig با endpoint REST. هر سه بهبود روی backend پیاده‌سازی می‌شوند و بهبود ۸ نیازمند تغییرات frontend برای نمایش trace است.
**Excerpt:**
```
### 🆕 (v2 — کاستی ۳) **بهبود ۷ — Per-AC state cache**

#### مشکل
هر بار verify اجرا می‌شود، همهٔ AC ها از صفر چک می‌شوند. اگر AC در ۳ run اخیر `done` با confidence > 0.85 بود و فایل‌های مرتبط تغییر نکردند، re-verify لازم نیست.

#### راه‌حل
فیلد جدید روی `OversightTask`:
```python
ac_verify_cache: Dict[str, Any] = field(default_factory=dict)
# ساختار:
# {
#   "<ac_hash>": {
#     "verdict": "done",
#     "confidence": 0.92,
#     "last_verified_at": ISO,
#     "files_checksum": "abc123",
#     "consecutive_done_count": 3,
#     "evidence": ["..."]
#   }
# }
```

منطق:
1. قبل از verify هر AC:
   - hash از متن AC + classification
   - چک cache
   - اگر `consecutive_done_count >= 3 AND files_checksum unchanged AND age < 7 days`:
     - skip probes، از cache استفاده کن
     - log: `"AC X: cached done (skipped 3 probes)"`
2. بعد از verify:
   - اگر verdict = done و confidence > 0.85:
     - `consecutive_done_count += 1`
     - `files_checksum = compute_files_checksum(target_files)`
   - اگر verdict != done:
     - `consecutive_done_count = 0`
     - cache invalidate

`compute_files_checksum`: sha256 از target_files content (یا sha روی commit ref اگر در GitHub).

flag config: `enable_ac_cache: bool = True` (پیش‌فرض True). user می‌تواند با `?force_full_verify=true` بای‌پاس کند.

---

### 🆕 (v2 — کاستی ۴) **بهبود ۸ — Observability/Trace mode**

#### مشکل
کاربر نمی‌تواند بفهمد چرا verify گفته partial. باید بتواند trace کامل را ببیند.

#### راه‌حل

تمام تصمیم‌های verify در `context.trace` log می‌شوند:
```python
context.trace.append({
    "ts": iso,
    "phase": "iteration_2_content_grep",
    "ac_index": 5,
    "ac_text": "اضافه کردن فیلد view_preferences...",
    "decision": "escalate_to_iter_3",
    "reason": "confidence 0.6 < threshold 0.7",
    "evidence": [...],
    "probe_results": [...],
    "elapsed_ms": 1234,
})
```

سپس روی `VerificationReport`:
```python
@dataclass
class VerificationReport:
    ...
    verify_trace: List[Dict] = field(default_factory=list)
    ac_probe_details: List[Dict] = field(default_factory=list)
    verify_version: str = "v6"
    config_used: Dict = field(default_factory=dict)
```

endpoint جدید:
```
GET /api/oversight/tasks/{task_id}/verify-trace?report_id={id}
→ trace کامل آخرین (یا specific) verify
```

UI: یک accordion "🔍 Trace" در زیر هر AC در دیتیل تسک — نمایش step-by-step تصمیمات.

---

### 🆕 (v2 — کاستی ۵) **بهبود ۹ — Centralized VerifyConfig**

#### مشکل
هر knob (max_iterations, max_files, model_tier, ...) جدا گفته شده. متمرکز نیست.

#### راه‌حل
ساختار `VerifyConfig`:
```python
@dataclass
class VerifyConfig:
    max_iterations: int = 3
    iter1_confidence_threshold: float = 0.8
    iter2_confidence_threshold: float = 0.7
    enable_content_grep: bool = True
    max_files_per_run: int = 50
    max_file_size_bytes: int = 500_000
    max_identifiers_per_ac: int = 15
    iter2_max_extra_files: int = 50
    iter2_max_identifiers: int = 25
    strong_model_preference: List[str] = field(default_factory=lambda: ["gpt-4o", "claude-opus-4-7", "claude-sonnet-4-6"])
    enable_ac_cache: bool = True
    ac_cache_max_age_days: int = 7
    ac_cache_consecutive_threshold: int = 3
    weights: Dict[str, float] = field(default_factory=lambda: {...})
    enable_trace: bool = True
    trace_max_entries: int = 1000
```

ذخیره در `WatchedProject.verify_v6_config: Optional[Dict] = None` (اگر None، defaults).

endpoint: `GET/PATCH /api/oversight/watched/{id}/verify-v6-config`
```

### Step 47: اجرای گام‌های تکراری تأیید (Iterative Verify) با کش و طبقه‌بندی AC
**Status:** `done` (100%)
**Scope:** این بخش منطق کامل حلقه تأیید تکراری برای هر AC (Acceptance Criterion) را مشخص می‌کند: بارگذاری پیکربندی، ساخت زمینه، طبقه‌بندی AC، بررسی کش، اجرای حداکثر ۳ دور (iteration) با استراتژی‌های فزاینده (grep، vision، playwright، مدل قوی)، تجمیع رأی‌ها، به‌روزرسانی کش، و ثبت جزئیات در verify_trace. بخش‌های خارج از scope: منطق کلی task verdict (aggregate per-AC) و title reassess (C5) که در انتهای نمودار آمده‌اند اما جزئیات اجرایی آن‌ها در این بخش نیست.
**Excerpt:**
```
```
verify_task(task_id, verify_v6=True)
│
├── load WatchedProject.verify_v6_config → VerifyConfig
│
├── build_verify_context(task, watched, config) → VerifyContext
│
├── for each AC (یا task_step):
│    │
│    ├── classify_ac(ac, context) → classification ("frontend"|"backend"|...)
│    │
│    ├── 🆕 check ac_verify_cache:
│    │    if cache_hit_with_freshness:
│    │        → use cached ProbeResult, log "cached"
│    │        → skip iterations
│    │    else:
│    │        → run iterative verify
│    │
│    ├── iterative_verify_step(ac, context, max_iter=3):
│    │    │
│    │    ├── iteration 1: standard probes
│    │    │    ├── content_grep (smart_grep_for_ac)
│    │    │    ├── code_aware (basename + diff)
│    │    │    ├── vision (if frontend/fullstack)
│    │    │    └── playwright (if URL)
│    │    │
│    │    ├── aggregate_verdicts(probes) → ProbeResult
│    │    ├── if confidence ≥ 0.8 → finalize
│    │    │
│    │    ├── iteration 2: aggressive content_grep
│    │    │    ├── full repo grep (filtered)
│    │    │    ├── more identifiers
│    │    │    └── AI rerun with new evidence
│    │    │
│    │    ├── aggregate → ProbeResult
│    │    ├── if confidence ≥ 0.7 → finalize
│    │    │
│    │    ├── iteration 3: strong model escalation
│    │    │    └── _strong_model_judgment(ac, context, prior_results)
│    │    │
│    │    └── finalize unconditionally
│    │
│    ├── update ac_verify_cache:
│    │    if verdict==done && confidence > 0.85:
│    │        consecutive_done_count++, files_checksum updated
│    │    else:
│    │        cache invalidated
│    │
│    └── append to verify_trace + ac_probe_details
```
```

### Step 48: ایجاد و بازنویسی فایل‌های سرویس verify_runtime و oversight برای پشتیبانی از verify_v6
**Status:** `done` (100%)
**Scope:** این بخش شامل ایجاد ۴ فایل جدید در backend/app/services/verify_runtime/ (context_builder, code_content_searcher, iterative_orchestrator, ac_cache_service)، بازنویسی code_aware_verifier با فازهای A→B→C→D، تغییرات در oversight_verifier (افزودن _classify_step_for_probe با ۱۰ قاعده و flag verify_v6)، به‌روزرسانی oversight_service (افزودن ac_verify_cache و verify_v6_config به dataclass‌ها)، export در __init__.py، اضافه کردن endpoint‌های verify-trace و verify-v6-config (GET/PATCH) و پارامتر verify_v6 در endpoint verify در oversight.py، و ایجاد دو فایل تست جدید است. نکته حیاتی: تمام فایل‌ها و کلاس‌ها باید دقیقاً با نام‌های ذکر شده ایجاد شوند و scope هر فایل مطابق جدول رعایت شود.
**Excerpt:**
```
## 📁 File map (v2)

| فایل | تغییر | scope |
|---|---|---|
| `backend/app/services/verify_runtime/context_builder.py` | **جدید** | `VerifyContext`, `VerifyConfig`, `build_verify_context` |
| `backend/app/services/verify_runtime/code_content_searcher.py` | **جدید** | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` + ۴ مثال concrete در docstring |
| `backend/app/services/verify_runtime/iterative_orchestrator.py` | **جدید** | `ProbeResult`, `iterative_verify_step`, `aggregate_verdicts`, `_strong_model_judgment` |
| `backend/app/services/verify_runtime/ac_cache_service.py` | **جدید** | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| `verify_runtime/code_aware_verifier.py` | بازنویسی phase A→B→C→D با نام تابع‌های صریح | همان فایل، +۲۰۰ خط |
| `backend/app/services/oversight_verifier.py` | `_classify_step_for_probe` با ۱۰ قاعده + integration با orchestrator + flag `verify_v6` | همان فایل |
| `backend/app/services/oversight_service.py` | اضافه کردن `ac_verify_cache` و `verify_v6_config` به dataclass ها | همان فایل |
| `backend/app/services/verify_runtime/__init__.py` | export نام‌های جدید | همان فایل |
| `backend/app/api/routes/oversight.py` | endpoint های جدید: `verify-trace`, `verify-v6-config` (GET/PATCH) + پارامتر `verify_v6=True|False` در verify endpoint | همان فایل |
| `backend/tests/test_code_content_searcher.py` | **جدید** | unit tests برای `extract_identifiers` با ۴ مثال + grep test |
| `backend/tests/test_iterative_orchestrator.py` | **جدید** | unit tests برای `aggregate_verdicts` با ۵ سناریو |
```

### Step 49: تعریف ۱۲ معیار موفقیت (AC) برای Verify v6 با meta-test سختگیرانه
**Status:** `done` (100%)
**Scope:** این بخش ۱۲ Acceptance Criteria (AC) مشخص و قابل grep را برای قابلیت Verify v6 تعریف می‌کند. هر AC یک فایل/کلاس/تابع/endpoint خاص را هدف می‌گیرد. معیار سختگیرانه این است که وقتی Verify v6 روی این bug اجرا شود، باید ≥۱۱ از ۱۲ AC را با confidence ≥ 0.8 پاس کند. این بخش صرفاً معیارها را لیست می‌کند و دستور اجرا یا پیاده‌سازی نمی‌دهد.
**Excerpt:**
```
## 🧪 معیار موفقیت + meta-test (v2 — concrete AC list)

این bug **باید با خودش verify شود**. ۱۲ AC مشخص (افزایش از ۱۰ به ۱۲):

| # | AC | identifier‌های قابل grep |
|---|---|---|
| 1 | فایل `context_builder.py` با کلاس `VerifyContext` و تابع `build_verify_context` | `VerifyContext`, `build_verify_context`, `VerifyConfig` |
| 2 | فایل `code_content_searcher.py` با ۴ تابع + ۴ مثال در docstring | `fetch_file_content`, `grep_token_in_files`, `smart_grep_for_ac`, `extract_identifiers` |
| 3 | فایل `iterative_orchestrator.py` با ۳ symbol + strong model escalation | `iterative_verify_step`, `aggregate_verdicts`, `ProbeResult`, `_strong_model_judgment` |
| 4 | فایل `ac_cache_service.py` با ۳ تابع cache | `compute_files_checksum`, `check_ac_cache`, `update_ac_cache` |
| 5 | `_classify_step_for_probe` با ۱۰ قاعدهٔ explicit در `oversight_verifier.py` | `"backend"`, `"frontend"`, `"fullstack"`, `"infra"`, `"test_only"`, `"doc_only"`, `"manual_only"` |
| 6 | `code_aware_verifier.py` با ۴ تابع جدید phase | `_phase_a_basename_match`, `_phase_b_content_grep`, `_phase_c_extended_repo_grep`, `_phase_d_ai_judgment` |
| 7 | فیلد جدید `ac_verify_cache` روی `OversightTask` dataclass | `ac_verify_cache` در `oversight_service.py` |
| 8 | فیلد جدید `verify_v6_config` روی `WatchedProject` dataclass | `verify_v6_config` |
| 9 | `VerificationReport` با فیلدهای `verify_trace`, `ac_probe_details`, `verify_version`, `config_used` | همان نام‌ها در dataclass |
| 10 | endpoint `GET /tasks/{task_id}/verify-trace` و `GET/PATCH /watched/{id}/verify-v6-config` | router decorators |
| 11 | پارامتر `verify_v6: bool = True` در `verify_task` signature | `verify_v6` در function def |
| 12 | حداقل ۲ فایل تست: `test_code_content_searcher.py` (۴ مثال extract_identifiers) و `test_iterative_orchestrator.py` (۵ سناریو aggregate_verdicts) | اسامی فایل + assertion های concrete |

**معیار سخت‌گیرانه:** vary v6 وقتی روی این bug اجرا شد، باید **≥۱۱ از ۱۲ AC** را done ببیند (با confidence ≥ 0.8).

اگر کمتر → یعنی verify v6 خودش هنوز ضعیف است → bug C6 fail.
```

### Step 50: پیاده‌سازی Edge Cases نسخه v2 برای Oversight Verifier
**Status:** `done` (100%)
**Scope:** این بخش شامل ۱۴ مورد از edge cases نسخه v2 است که باید در سرویس oversight_verifier پیاده‌سازی شوند. موارد شامل مدیریت rate limit گیت‌هاب، فایل‌های بزرگ/باینری، fallback منطق، پشتیبانی از چندزبانگی، کنترل حافظه، backward compatibility، A/B testing، race condition در cache invalidation، عدم دسترسی به مدل قوی، محدودیت trace size و اعتبارسنجی کانفیگ است. موارد ۱ تا ۱۰ از نسخه v1 هستند و موارد ۱۱ تا ۱۴ جدید (v2) می‌باشند. تمام این موارد باید در کلاس VerifyService یا VerifyContext پیاده‌سازی شوند.
**Excerpt:**
```
## ⚠️ Edge cases (v2 — افزایش‌یافته)

1. **GitHub rate limit**: cache aggressive + cap 50 file. اگر rate limit hit شد، fallback به v5 منطق.
2. **Large file**: skip > 500KB (configurable).
3. **Binary file**: skip اگر non-text Content-Type.
4. **Token not in private repo**: fallback graceful.
5. **Identifier spam**: AC تمام stop-words → fallback به AI.
6. **Multi-language**: identifiers از فارسی+انگلیسی هر دو (با regex unicode-aware).
7. **Recursion**: orchestrator فقط probes را call می‌کند، نه `verify_task`.
8. **Memory**: caps روی هر فیلد VerifyContext.
9. **Backward compat**: `verify_v6=False` → مسیر v5.
10. **A/B**: random seed برای ۵۰/۵۰ split بین v5/v6 (debug).
11. **🆕 (v2) Cache invalidation race**: اگر دو verify همزمان روی یک تسک شروع شدند، cache lock با `asyncio.Lock` per-task.
12. **🆕 (v2) Strong model unavailable**: اگر هیچ strong model در chain موجود نیست، iteration 3 با fallback model اجرا می‌شود (با warning log) — fail نمی‌کند.
13. **🆕 (v2) Trace size**: cap ۱۰۰۰ entry per verify_run. اگر بیشتر، oldest حذف می‌شوند (FIFO).
14. **🆕 (v2) Config validation**: اگر user verify_v6_config با مقادیر out-of-range تنظیم کرد (مثلاً max_iterations=100)، clamp به range معتبر.
```

### Step 51: تعیین محدوده خارج از اسکوپ و ترتیب اجرای v2 با ۸ chunk
**Status:** `done` (100%)
**Scope:** این بخش دو بخش مجزا دارد: (۱) فهرست مواردی که خارج از اسکوپ پروژه هستند و نباید تغییر داده شوند (شامل Playwright probe، vision probe، ML classification، تشخیص multi-language source code، AST-level analysis، distributed cache، WebSocket live progress). (۲) اشاره به ترتیب اجرای نسخه دوم (v2) با ۸ chunk که جزئیات آن در ادامه درخواست اصلی آمده است. این بخش صرفاً محدوده را مشخص می‌کند و شامل هیچ مرحله اجرایی جدیدی نیست.
**Excerpt:**
```
## 🚫 خارج از scope (بدون تغییر)

(همان قبلی)
- تغییر در Playwright probe
- تغییر در vision probe
- ML classification
- multi-language تشخیص source code (فقط py/ts/tsx/js/jsx)
- AST-level analysis
- distributed cache
- WebSocket live progress

---

## 🔬 ترتیب اجرا (v2 — با ۸ chunk)
```

### Step 52: فاز A — Task Type Classifier: تشخیص خودکار نوع تسک backend/frontend/fullstack/infra/docs/test/mixed
**Status:** `done` (100%)
**Scope:** این بخش شامل پیاده‌سازی تابع _classify_task_type در iterative_orchestrator.py است که بر اساس prompt + target_files + AC نوع تسک را با regex/heuristic تشخیص می‌دهد. شامل ۷ نوع pure_backend, pure_frontend, fullstack, infra, docs_only, test_only, mixed_unknown. خروجی تابع یک رشته است. تشخیص بدون AI انجام می‌شود. task_type در verify_trace ثبت می‌شود. خارج از scope: weighting, probe validation, contradiction resolution, vision prompt, trace summary.
**Excerpt:**
```
فاز A — Task Type Classifier
اصول
یک تابع helper جدید: _classify_task_type(task) که بر اساس prompt + target_files + AC، نوع تسک را تشخیص می‌دهد.

دسته‌بندی‌ها
Type	معیار تشخیص	probe profile
pure_backend	همهٔ target_files با .py پایان دارند یا path شامل backend/ و در prompt اشاره‌ای به frontend/UI نیست	weight ui_interaction = 0.1، api_probe = 2.0
pure_frontend	همهٔ target_files با .tsx/.ts/.jsx/.js/.css پایان دارند و path شامل frontend/	weight ui_interaction = 2.0، api_probe = 0.3
fullstack	ترکیبی از backend و frontend	weight ui_interaction = 1.5، api_probe = 1.5
infra	فایل‌های Dockerfile, *.yml, *.yaml, .github/workflows/*	weight ui_interaction = 0، code_aware = 3.0
docs_only	فقط .md, .txt	همهٔ probes را skip، فقط code_aware
test_only	فقط فایل‌های test_*.py, *.test.tsx	weight ui_interaction = 0.3، test_probe = 3.0
mixed_unknown	تشخیص ناممکن	استفاده از weights پیش‌فرض (همان WEIGHTS_BY_PROBE موجود)

اقدامات
محل: backend/app/services/verify_runtime/iterative_orchestrator.py کنار WEIGHTS_BY_PROBE
تابع _classify_task_type(task) -> str که یکی از این 7 رشته برمی‌گرداند
منطق تشخیص باید fast باشد (regex ساده، نه AI call)
در trace ثبت شود: task_type_classified: pure_backend

معیارهای پذیرش فاز A
۱. تابع _classify_task_type در iterative_orchestrator.py موجود است
۲. تابع برای هر یک از ۷ نوع، رشتهٔ صحیح برمی‌گرداند (با تست واحد)
۳. task_type در verify_trace با phase=classify_task_type ثبت می‌شود
۴. تشخیص بدون فراخوانی AI انجام می‌شود (regex/heuristic)
```
