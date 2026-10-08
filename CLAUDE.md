# CLAUDE.md — قواعدِ کار روی این ریپو (برای Claude و هر هوش مصنوعیِ دیگر)

> **اول [`AGENTS.md`](AGENTS.md) را بخوان** — قواعدِ مشترکِ همهٔ agentها و پروتکلِ امضا.
> اگر این دو در یک قاعده اختلاف داشتند، AGENTS.md برنده است و ناهماهنگی باگی است که در همان کامیت رفع می‌شود.

project-management (AI Creator Engine): FastAPI + Next.js روی Render. **`main` خودکار روی Render دیپلوی می‌شود**
(بک‌اند `ai-creator-backend` و فرانت‌اند `ai-creator-frontend`) — هر تغییر روی `main`، تغییرِ production است.
الگوی این قواعد: دو پروژهٔ دیگرِ مالک، Detective-1 و ALLIN1.

## دستورهای ثابتِ مالک (همهٔ سشن‌ها، بدونِ استثنا)

1. **ارسالِ خودکار پس از هر کار.** وقتی کاری تمام شد: `scripts/ship.sh "type(scope): summary"` — تست‌های بک‌اند،
   بیلدِ فرانت‌اند و دروازهٔ مستندات را اجرا می‌کند، کامیت می‌کند، شاخهٔ کاری را push و در `main` ادغام و push می‌کند
   (= دیپلوی). از مالک نخواه دستی در GitHub کامیت/پوش/مرج کند. PR باز نکن مگر مالک بخواهد. تست/بیلدِ قرمز را
   اصلاح کن؛ هرگز تست را برای سبز شدن غیرفعال نکن. hook ِ `Stop` در `.claude/settings.json` پایانِ سشن با کارِ
   ارسال‌نشده را متوقف می‌کند.
2. **ثبتِ کامل و جزئی.** پس از هر کار یک بخشِ تازه به انتهای [`docs/WORKLOG.md`](docs/WORKLOG.md) (قالب در سرِ همان
   فایل: FINDING/DECISION/CHANGE/VERIFY/REVERT/OWNER/TODO) با خطِ امضا. درخواست‌ها و تصمیم‌های مالک در گفت‌وگو هم با
   `[OWNER]` ثبت شوند. هیچ ورودیِ قبلی پاک نمی‌شود. درسِ قابلِ استفادهٔ مجدد ⇒ `experiences/` (قالب در README همان پوشه —
   merge، نه replace).
3. **هیچ قابلیتی حذف نمی‌شود** (endpoint، صفحه، دکمه، داده). قرنطینه کن و در WORKLOG ثبت کن؛ حذف فقط با اجازهٔ صریحِ مالک.
4. **امنیت و ورود.** همهٔ برنامه پشتِ «ورود با گوگل» است (`backend/app/core/auth.py`). هر endpoint ِ تازه خودکار پشتِ
   دیوار است؛ اگر فراخوانندهٔ ماشینی دارد، باید با هدرِ رازِ خودش بیاید (`X-External-Token`، `X-Supervisor-Token`) —
   مسیرِ عمومی فقط با ثبت در `PUBLIC` و دلیل در WORKLOG. کلید/رمز/ایمیلِ مالک هرگز در کد یا مستندات نوشته نمی‌شود
   (فقط متغیرهای محیطیِ Render). مرزِ واقعیِ دسترسی سمتِ سرور است؛ UI فقط پنهان می‌کند.
5. **نظارت و سرکشی.** برگه‌های مالک (`/inspection`) را جدی بگیر؛ قواعدِ ناظر در [`docs/supervisor/PROMPT.md`](docs/supervisor/PROMPT.md).
6. **فایل‌های حجیم روی سرور نمی‌مانند** — به گوگل درایوِ پروژه می‌روند (`backend/app/services/gdrive.py`)؛ دیسکِ Render
   فقط ۱ گیگ است و پایگاه‌داده هم روی آن است.
7. `prompt/` مالِ ابزارِ بیرونیِ مالک است — **دست نزن**.

## ساختار
| بخش | مسیر |
|---|---|
| قواعدِ مشترکِ همهٔ agentها (اول این) | `AGENTS.md` (+ اشاره‌گرها: `GEMINI.md`، `.github/copilot-instructions.md`) |
| ارسالِ خودکار + دروازهٔ مستندات | `scripts/ship.sh`، `scripts/docs_gate.py`، `.claude/settings.json`، `.claude/hooks/ensure-shipped.sh` |
| دفترِ کار (ثبتِ همهٔ تغییرات) | `docs/WORKLOG.md` |
| API (FastAPI) | `backend/app/main.py`، `backend/app/api/routes/`، `backend/app/services/` |
| ورود با گوگل و دیوارِ API | `backend/app/core/auth.py`، `backend/app/api/routes/auth.py`، `backend/app/models/app_user.py`، فرانت: `frontend/src/lib/auth.tsx`، `frontend/src/app/users/page.tsx` |
| نظارت و سرکشی (API، فایل‌ها، درایو، زمانِ دورها) | `backend/app/api/routes/inspection.py`، `backend/app/models/inspection.py`، `backend/app/services/inspection_files.py`، `backend/app/services/gdrive.py`، `backend/app/services/supervisor_rounds.py` |
| نظارت و سرکشی (فرانت) | `frontend/src/lib/inspection/`، `frontend/src/components/inspection/`، `frontend/src/app/inspection/page.tsx` |
| ناظرِ خودکار (روتین‌ها، پرامپت‌های نسخه‌دار، بایگانی، اسکریپت‌ها) | `docs/supervisor/`، `scripts/supervisor/` |
| تست‌ها | `backend/tests/` |
| فرانت‌اند (Next.js) | `frontend/src/app/`، `frontend/src/components/Layout.tsx` |
| درس‌ها | `experiences/` |
| تسک‌های ابزارِ بیرونیِ مالک | `prompt/` (دست نزن) |

## اجرا و راستی‌آزمایی
```bash
cd backend && pip install -r requirements.txt && python -m pytest -q          # تست‌ها
ENVIRONMENT=production DATABASE_DIR=/tmp/pmdb uvicorn app.main:app --port 8000  # بک‌اند محلی
cd frontend && npm ci && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
scripts/ship.sh "type(scope): summary"                                          # ارسال = دیپلوی
```
قراردادِ کامیت: `type(scope): summary` — کوچک، یک موضوع، برگشت‌پذیر. متنِ UI فارسی و `dir="rtl"`.
