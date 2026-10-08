---
title: "Owner Inspection Board with Off-Site File Storage — boxes on screens, an honest supervisor, bytes that never stay on the server"
tags: ["inspection", "supervisor", "routine", "google-drive", "uploads", "spool", "screenshots", "coordinates", "nextjs", "fastapi"]
topic_canonical: "owner-inspection-board-with-offsite-file-storage"
source:
  type: "claude-code-task"
  origin: "claude-code"
  imported_at: "2026-10-08T08:30:00Z"
created_at: "2026-10-08T08:30:00Z"
updated_at: "2026-10-08T08:30:00Z"
merged_from: []
---

# Owner Inspection Board with Off-Site File Storage

## 🎯 چالش / Challenge

صاحبِ یک وب‌اپ می‌خواهد خودش در برنامه بگردد، دورِ هر ایراد کادر بکشد، توضیح و فایل (هر نوع، حجیم)
بدهد، و یک «ناظرِ خودکار» (یک agent ِ زمان‌بندی‌شده) زیرِ همان برگه جواب بنویسد — بی‌آنکه:
۱) رنگِ «انجام شد» دروغ بگوید، ۲) ناظر فایل‌ها را نخوانده جواب بدهد، ۳) فایل‌های حجیم دیسکِ کوچکِ
سرور را پر کنند، ۴) جای کادر با تغییرِ اندازهٔ پنجره بی‌معنا شود.

## 💡 راه‌حل / Solution

1. **وضعیت ≠ نتیجه.** `status` (نوبتِ کیست: open/answered/approved/filed) رنگِ کارت و هایلایت
   است؛ `outcome` (fixed/partial/not-done/needs-owner) فقط نشان. `fixed` بدونِ تصویرِ «بعد» در API رد می‌شود.
2. **مالک تیک می‌زند، ناظر هرگز.** هویتِ ناظر با توکن؛ endpointهای تأیید/حذف/فوری توکنِ ناظر را ۴۰۳ می‌کنند.
3. **خواندنِ فایل قابلِ اندازه‌گیری است.** متن هنگامِ آپلود استخراج و تکه‌تکه سرو می‌شود؛ سرور فقط
   خواندنِ **پیوسته** را می‌شمارد و جوابِ ناظر را تا بدهیِ خواندن صفر نشده رد می‌کند (۴۲۲ با نامِ فایل).
4. **بایت‌ها فقط «در راه» روی سرورند.** آپلودِ تکه‌ای (octet-stream، قابلِ ادامه با offset) ←
   فایلِ موقت ← استخراج ← انتقال به ذخیره‌سازِ بیرونی (مثلاً Drive با scope ِ حداقلی) ← **تطبیقِ MD5**
   ← حذفِ نسخهٔ محلی. ردیف فقط رفرنسِ انسانی (`PREFIX-0007-F01`) و لینک نگه می‌دارد. تا ذخیره‌ساز
   وصل نیست، وضعیت `pending` با دلیل؛ یک worker هر چند دقیقه دوباره تلاش می‌کند؛ سقفِ فضای موقت.
5. **مختصاتِ ماندگار.** کادر به چهار شکل ذخیره می‌شود: سلکتورِ round-trip‌شدهٔ عنصرِ زیرِ کادر + کسرهای
   کادر نسبت به همان عنصر (با reflow هم درست است) + مختصاتِ سند + پنجره/اسکرول/dpr، و زبانهٔ فعال.
   بازگذاری اول از عنصر، وگرنه از مختصاتِ سند **و می‌گوید «تقریبی»**.
6. **نقشهٔ خودکارِ سطحِ برنامه.** هر صفحه هنگامِ آرام‌شدن عنوان‌ها/زبانه‌ها/بخش‌ها/دکمه‌ها/ورودی‌ها را با
   سلکتور و مختصات گزارش می‌دهد؛ اسکنِ headless ِ ناظر **همان تابعِ خودِ صفحه** را صدا می‌زند؛ فهرستِ
   کد صفحه‌های دیده‌نشده را علامت می‌زند. صفحهٔ فردا بی‌ویرایشِ دستی ظاهر می‌شود.
7. **پرامپتِ روتین کوتاه و ثابت؛ دستور در ریپو با نسخه.** روتین فقط «این فایل را بخوان و اجرا کن» +
   مجوزهایی که باید از زبانِ مالک باشد؛ نسخهٔ قبلی در `archive/PROMPT-v{N}-{date}.md`.

## 🧪 نمونه کد (Anonymized)

```python
def push(row):                       # verified, then freed
    placed = storage.upload(open(row.spool_path, "rb"), name=f"{row.ref} — {row.filename}")
    if placed["md5"] != row.md5:
        row.store = "failed"; return  # keep the local copy, retry later
    row.store, row.link = "remote", placed["link"]
    os.remove(row.spool_path); row.spool_path = ""
```

```ts
// hover tooltips WITHOUT stealing clicks: overlay is pointer-events:none,
// hover is a document-level mousemove hit-test against the placed rects
window.addEventListener('mousemove', (e) => setHover(hitTest(placed, e.pageX, e.pageY)))
```

## ⚠️ نکات حیاتی / Pitfalls

- «نتوانستم نگاه کنم» و «نگاه کردم، چیزی نبود» نباید یک کدِ خروج داشته باشند (۳ در برابرِ ۰).
- یک callback ِ inline در deps ِ یک `useCallback` ِ بارگذاری = حلقهٔ بی‌پایانِ fetch؛ در ref نگه دار.
- رویدادِ «برگه‌ها عوض شد» را از خودِ بارگذاریِ بورد نفرست اگر بورد به همان گوش می‌دهد (حلقه).
- تب‌های ساخته‌شده از دکمه‌های ساده: ردیفِ دکمه‌های **اقدام** (ثبت/ذخیره/+) را تب حساب نکن — اسکنِ
  خودکار رویشان کلیک می‌کند.
- Playwright ِ pip ممکن است نسخهٔ کرومیومِ دیگری بخواهد؛ به کرومیومِ نصب‌شدهٔ محیط برگرد.

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere

- [ ] مدل: Report(status, outcome-in-notes, geometry, notes[], deps[], urgent_at/claimed/done, binder)
      + Shot + File(store, ref, link, spool_path, extract_status, read_chars) + Binder + Surface.
- [ ] API: create / note / edit / status(owner-only) / urgent(+claim with TTL) / file(archive) /
      intake start-append-finish / files text(slices, contiguous) / raw / surfaces / inventory.
- [ ] Worker: spool → remote → MD5 → delete; pending با دلیل؛ سقفِ فضای موقت.
- [ ] Client: provider (کادر، تصویرِ خودکار + Ctrl+V، «گزارشِ جدید» یا «ذیلِ برگهٔ باز»، فایل، ⚡)،
      highlights (رنگ = نوبت)، surface recorder، board.
- [ ] دو روتین: کامل (هفته‌ای دو بار) و فوری (هر چند ساعت)؛ هر دو اول «آبی‌ها را بایگانی کن».

## 🔗 References

- الگو: سامانهٔ «نظارت و سرکشی» ِ دو پروژهٔ همسایه (فقط خوانده شدند).
- مرتبط: `cloudflare-403-on-chunked-cross-origin-post`
