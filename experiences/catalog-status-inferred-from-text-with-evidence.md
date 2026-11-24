---
title: "A catalog field that only an optional metadata key can fill ends up «unknown» for almost everything — infer it from the text, and keep the evidence"
tags: ["catalog", "metadata", "classification", "frontmatter", "backfill", "evidence", "filters", "knowledge-base"]
topic_canonical: "catalog-status-inferred-from-text-with-evidence"
source:
  type: "claude-code-task"
  origin: "claude-code"
  imported_at: "2026-11-24T22:00:00Z"
created_at: "2026-11-24T22:00:00Z"
updated_at: "2026-11-24T22:00:00Z"
merged_from: []
resolution_status: "solved"
---

# A catalog status that nobody fills in

## 🎯 چالش / Challenge

یک کاتالوگ از سندهای markdown (از چند مخزن) فیلترِ «وضعیت» داشت: حل‌شده / نیمه‌حل / باز. حدودِ ۸۷٪ ِ ورودی‌ها «نامشخص» بودند، پس فیلتر عملاً بی‌فایده بود و مصرف‌کنندهٔ پایین‌دستی (یک دستیارِ LLM) نمی‌توانست
درسِ حل‌شده را از ناتمام جدا کند.

### علت

وضعیت فقط از یک کلیدِ **اختیاری** در سرآیندِ فایل خوانده می‌شد. نویسنده‌های خودکار آن کلید را نمی‌نوشتند (قالبِ راهنمایشان هم آن را نخواسته بود). «نامشخص» یعنی «کسی نپرسید»، نه «معلوم نیست» — و چون مقدارِ پیش‌فرض
خطا نیست، هیچ‌جا دیده نشد.

## 💡 راه‌حل / Solution

۱. **مقدار را از خودِ متن استنتاج کن**، با ترتیبِ اعتماد: گفتهٔ صریحِ نویسنده (سرآیند) ⇒ بلوکِ ساختاریِ «Status: …» ⇒ وجودِ بخشِ راه‌حلِ واقعی (نه جای‌خالی، نه داخلِ بلوکِ کد) ⇒ جملهٔ صریحِ «هنوز حل نشده».
۲. **هر حکم یک جملهٔ شاهد نگه دارد** («بخشِ راه‌حل دارد، ۵۴۸ نویسه، هیچ نشانهٔ ناتمامی نیست») و منبعِ حکم (`frontmatter|text|model|none`) — برچسبِ غلط تا جمله‌ای که باعثش شد ردگیری می‌شود.
۳. **مدل فقط برای موردِ دوپهلو** (هم راه‌حل، هم نشانهٔ ناتمامی)، با سقف و با بازگشتِ محتاط (`partial`) وقتی مدل نیست یا بی‌قالب جواب داد. قاعدهٔ قطعی برای بقیه: بی‌هزینه و تکرارپذیر.
۴. **«نامشخص» را نگه دار ولی کمیاب کن:** فقط وقتی هیچ شاهدی نیست؛ در شاهدش بنویس چه دیدی (فهرستِ سرفصل‌ها) تا قاعدهٔ جاافتاده پیدا شود.
۵. **پرکردنِ قدیمی‌ها بدونِ مهاجرت:** کنارِ هر ورودی «هشِ محتوایی که حکم برایش داده شد» را نگه دار؛ همگام‌سازیِ عادی هر ورودیِ بی‌آن را یک‌بار دوباره می‌خواند. نه اسکریپتِ یک‌بارمصرف، نه بازنویسیِ داده.

## 🧪 نمونه کد (Anonymized)

```python
def infer_status(meta, body) -> tuple[str, str, str]:      # (status, source, evidence)
    if meta.get("status") in DECIDED:
        return meta["status"], "frontmatter", "author wrote it"
    solution, open_signals = scan_sections(body)            # headings + explicit sentences, code fences removed
    if solution and open_signals: return "partial", "ambiguous", f"solution + {open_signals[0]}"
    if solution:                  return "solved", "text", f"solution section ({len(solution)} chars)"
    if open_signals:              return "open", "text", open_signals[0]
    return "unknown", "none", "no evidence in the text"

# sync: skip an unchanged file only once it has been classified
if entry.blob_sha == remote_sha and entry.status_checked_hash == entry.content_hash:
    continue
```

## ⚠️ نکات حیاتی / Pitfalls

- واژهٔ «حل نشد» در روایتِ **تلاش‌های شکست‌خوردهٔ قبلی** فراوان است؛ اگر هر رخدادش را نشانهٔ ناتمامی بگیری، سندهای حل‌شده «نیمه‌حل» می‌شوند. فقط سرفصلِ «کارِ مانده/Open questions» و جمله‌های صریحِ زمانِ حال را بشمار.
- سرفصلِ نمونه داخلِ بلوکِ کد (` ```## Solution``` `) شاهد نیست — پیش از تحلیل بلوک‌های کد را کنار بگذار.
- واکشیِ ناموفق (متنِ خالی) را «فایلِ خالی» حساب نکن؛ ورودیِ قبلی را نگه دار و بعداً دوباره تلاش کن.
- پرکردنِ قدیمی‌ها نباید `updated_at` یا هشِ «آخرین پردازش» را عوض کند، وگرنه مرتب‌سازی به‌هم می‌ریزد و پردازشِ گران دوباره برای همه راه می‌افتد.

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere

- برای هر فیلترِ کاتالوگ توزیعِ مقدارها را نگاه کن: اگر یک مقدارِ پیش‌فرض بیش از نیمی را گرفته، فیلتر کار نمی‌کند — منبعِ آن فیلد را پیدا کن.
- فیلدی که به کلیدِ اختیاری تکیه دارد، یک استنتاج‌گرِ پشتیبان می‌خواهد؛ و قالبِ راهنمای نویسنده‌ها باید آن کلید را بخواهد.
- حکمِ استنتاجی را همیشه با منبع و شاهد ذخیره کن و در UI نشان بده.

### Applies when
- فهرست/کاتالوگی از سندهای نیمه‌ساختاریافته با نویسنده‌های گوناگون (انسان و agent).

### Does NOT apply when (anti-pattern)
- وضعیت یک واقعیتِ بیرونی است (مثلاً «PR ادغام شد») و منبعِ معتبرِ ماشینی دارد — همان را بخوان، حدس نزن.

## 🔗 References
- مرتبط: `review-reads-every-format-in-full`، `browser-agent-unseen-is-not-absent` («نسنجیدم» ≠ «نیست»)
