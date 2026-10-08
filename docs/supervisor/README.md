# ناظرِ خودکار و «نظارت و سرکشی» — project-management

دو **Routine** (زمان‌بندِ Claude Code) که خودشان برگه‌های «نظارت و سرکشی» را می‌خوانند، کار را
انجام می‌دهند، زیرِ برگه جواب می‌نویسند، تأییدشده‌ها را بایگانی می‌کنند و سامانه را بازرسی
می‌کنند. مالک کاری نمی‌کند جز ثبتِ برگه (کادر روی صفحه، یا «درخواستِ عمومی») و تیکِ تأیید.

الگو: سامانهٔ نظارتِ دو پروژهٔ همسایه — `mahdighandi1989/ALLIN1` و `mahdighandi1989/Detective-1`
(فقط خوانده شدند؛ هیچ تغییری در آن‌ها داده نشد).

## روتین‌ها

| مورد | دورِ کامل | صفِ فوری |
|---|---|---|
| نام | ناظرِ خودکارِ سامانه — project-management (نشستِ مستقل) | صفِ فوریِ «نظارت و سرکشی» — project-management (نشستِ مستقل) |
| شناسه | `trig_0185k7gpGZBvVs9JY9pZHiHJ` | `trig_01SmGK1H3EyJoWpeSBVcqj8F` |
| زمان‌بندی (UTC) | `37 0 * * 2,5` — سه‌شنبه و جمعه ۰۰:۳۷ (۰۴:۰۷ تهران) | `11 */3 * * *` — هر ۳ ساعت، دقیقهٔ ۱۱ |
| دستور (تنها مرجع) | [`PROMPT.md`](PROMPT.md) | [`URGENT_PROMPT.md`](URGENT_PROMPT.md) |
| اعلان | push + ایمیل | push (صفِ خالی = بی‌صدا) |
| نشست | هر اجرا یک نشستِ تازه | هر اجرا یک نشستِ تازه |
| وضعیت | ✅ فعال | ✅ فعال |

زمان‌ها عمداً با روتین‌های پروژه‌های دیگرِ همین حساب هم‌پوشانی ندارند (ALLIN1 دقیقهٔ ۲۳،
Detective-1 دقیقهٔ ۴۱، Lifemanager دقیقهٔ ۵۳ — همه هر ۳ ساعت؛ دورهای کامل در روزها/ساعت‌های دیگر).

پرامپتِ داخلِ باکسِ هر Routine **عمداً کوتاه و ثابت** است: مخزن را پیدا کن، `main` را بگیر،
این فایل را بخوان و مو‌به‌مو اجرا کن — به‌اضافهٔ **مجوزِ صریحِ پوش روی `main`** از طرفِ مالک
(چون نگهبانِ مجوز، متنِ فایل‌های ریپو را «داده» می‌خواند نه «حرفِ مالک» — درسِ ALLIN1). همهٔ
رفتار در گیت است و تاریخچه دارد.

اگر زمان‌بندی را عوض کردی، روی سرویسِ بک‌اند در Render این‌ها را هم هم‌خوان کن (برای شمارش‌گرِ
«دورِ بعدیِ ناظر» تا اولین دورِ مشاهده‌شده؛ بعد از آن زمانِ واقعیِ دورها **اندازه‌گیری** می‌شود):
`SUPERVISOR_URGENT_MINUTE` (پیش‌فرض ۱۱)، `SUPERVISOR_URGENT_EVERY_H` (۳)، `SUPERVISOR_URGENT_CRON`،
`SUPERVISOR_FULL_CRON`.

## چطور دستورِ ناظر را عوض کنم؟

**فایل را ویرایش کن، نه پرامپتِ Routine را.** روال (برای `PROMPT.md` و `URGENT_PROMPT.md` یکسان):

1. نسخهٔ فعلی را بایگانی کن:
   `cp docs/supervisor/PROMPT.md docs/supervisor/archive/PROMPT-v{N}-{YYYY-MM-DD}.md`
   (`N` = نسخهٔ فعلی در frontmatter؛ برای صفِ فوری `URGENT_PROMPT-v{N}-…`).
2. فایل را ویرایش کن؛ در frontmatter `version` را یک واحد جلو ببر، `updated` را امروز بگذار،
   `supersedes` را مسیرِ فایلِ بایگانی‌شده بگذار، و عنوانِ «نسخهٔ N» را هم عوض کن.
3. کامیت و پوش روی `main`. اجرای بعدیِ روتین نسخهٔ تازه را می‌خواند.

نسخه‌های قبلی هرگز پاک نمی‌شوند ([`archive/`](archive/)).

## هویتِ ناظر — بدونِ هیچ رازی در ریپو

- برنامه پشتِ «ورود با گوگل» است؛ «ناظر» حسابِ گوگل ندارد و با یک توکن شناخته می‌شود (مرورگرِ headless اش با
  `POST /api/auth/supervisor-session` یک نشستِ `supervisor` می‌گیرد که هرگز تیک/حذف/فوری نمی‌تواند): هدرِ `X-Supervisor-Token`
  باید با `SUPERVISOR_TOKEN` روی سرویسِ بک‌اند (Render) یکی باشد — اگر آن نبود، با
  `EXTERNAL_TOOL_TOKEN` که از قبل روی Render هست.
- اسکریپت‌ها (`scripts/supervisor/client.py`) آدرس و توکن را **در زمانِ اجرا** از Render API
  می‌خوانند — پروکسیِ محیطِ Claude Code میزبانِ `api.render.com` را احراز می‌کند. توکن نه چاپ
  می‌شود نه روی دیسک می‌رود. برای اجرای محلی: `PM_SUPERVISOR_API_BASE`، `PM_SUPERVISOR_TOKEN`،
  `PM_FRONTEND_URL`.
- **نگهبان‌ها در خودِ API:** فقط ناظر «نتیجه» ثبت می‌کند و صفِ فوری را برمی‌دارد؛ ناظر هرگز
  نمی‌تواند تأیید، حذف یا «فوری» کند؛ `fixed` بدونِ عکسِ بعد و جوابِ با فایلِ نخوانده رد می‌شوند.

## فایل‌ها کجا می‌روند — گوگل درایو، نه سرور

خواستهٔ مالک: «در بک‌اند چیزی رو نگه ندار». هر فایل/اسکرین‌شات فقط تا وقتی در راه است روی دیسکِ
موقتِ سرور است (`<DATABASE_DIR>/inspection_spool`)، بعد:

```
My Drive / project-management / نظارت و سرکشی / گزارش-0007 / PM-INS-0007-F01 — نمونه.docx
                                                          / PM-INS-0007-F01 — نمونه.docx.متن.txt
                                                          / تصویرها / PM-INS-0007-S01-before.jpg
                              / سطلِ حذف‌شده /    ← «حذف» فقط جابه‌جا می‌کند، هرگز پاک نمی‌کند
```

پس از تطبیقِ MD5 نسخهٔ سرور پاک می‌شود و در سامانه فقط رفرنس و لینک می‌ماند. تا درایو وصل
نشده، فایل‌ها با برچسبِ «⏳ هنوز در درایو نیست» منتظر می‌مانند (سقفِ فضای موقت:
`INSPECTION_SPOOL_MAX_MB`، پیش‌فرض ۵۰۰) و به‌محضِ اتصال خودکار منتقل می‌شوند.

**اتصال (یک بار، روی Render — هیچ‌کدام در کد نیست):**
`GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` (یک OAuth client در Google Cloud Console) و سپس یکی از:
`GOOGLE_DRIVE_REFRESH_TOKEN` (scope ‏`drive.file`)، یا دکمهٔ «اتصال به گوگل درایو» در
«نظارت و سرکشی › فضای ذخیره‌سازی» (نشانیِ فرانت‌اند باید در Authorized JavaScript origins همان
کلاینت باشد). اختیاری: `GOOGLE_DRIVE_ROOT_FOLDER` (پیش‌فرض `project-management`).

## اسکریپت‌ها

```bash
python3 scripts/supervisor/inspection.py whoami   # آیا سرور این ناظر را می‌شناسد؟
python3 scripts/supervisor/inspection.py file     # تیک‌خورده‌ها (آبی) → زونکن (هر دور)
python3 scripts/supervisor/inspection.py pull     # QUEUE.md + shots/ + files/  (خروجِ ۴ = بدهی)
python3 scripts/supervisor/inspection.py urgent   # یک برگهٔ فوری (۰ خالی · ۵ برداشته شد · ۳ خطا)
python3 scripts/supervisor/inspection.py answer N --outcome … --after … --dep … [--place …]
python3 scripts/supervisor/inventory.py --post    # فهرستِ کد → INVENTORY.md + «نقشهٔ سامانه»
python3 scripts/supervisor/surface_scan.py        # هر صفحه و زبانه روی production → مختصاتِ همهٔ عنصرها
python3 scripts/supervisor/screenshot.py /projects --tab "…" --selector "…" --out after.png   # عکسِ «بعد»
```

## در برنامه

منوی کناری › **نظارت و سرکشی** (`/inspection`) با زبانه‌های: برگه‌ها · درخواست‌های عمومی ·
نقشهٔ سامانه · بایگانی · فضای ذخیره‌سازی · روتین‌ها. کلیدِ «📝 ثبتِ گزارش» پایینِ منو حالتِ کادرکشی
را روی همهٔ صفحه‌ها روشن می‌کند (یا کلیدِ Alt). کدها: `backend/app/api/routes/inspection.py`،
`backend/app/models/inspection.py`، `backend/app/services/{gdrive,inspection_files,supervisor_rounds}.py`،
`frontend/src/lib/inspection/*`، `frontend/src/components/inspection/*`، `frontend/src/app/inspection/page.tsx`.

## فایل‌های این پوشه

| فایل | نقش |
|---|---|
| `PROMPT.md` / `URGENT_PROMPT.md` | دستورِ روتین‌ها — تنها مرجع |
| `archive/` | نسخه‌های قبلیِ دستورها |
| `RUNLOG.md` | گزارشِ هر اجرا، جدیدترین در انتها |
| `OPEN_ITEMS.md` | کارهای بازِ انتقالی بینِ اجراها |
| `runs.jsonl` | سنجه‌های هر اجرا (یک خط JSON) |
| `INVENTORY.md` / `inventory.json` | فهرستِ خودکارِ صفحه‌ها/دکمه‌ها/مسیرها (خودکار) |
| `inspection/README.md` | پوشهٔ کاریِ کارتابل (QUEUE/URGENT/shots/files — در git نیستند) |
