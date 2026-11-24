---
title: "Controlled form inputs: the box shows the new value, the request sends the old one"
tags: ["react", "forms", "controlled-input", "stale-state", "autofill", "browser-agent", "llm-pipeline", "self-check"]
topic_canonical: "controlled-input-stale-state-sends-previous-value"
source:
  type: "claude-code-task"
  origin: "claude-code"
  imported_at: "2026-11-24T10:30:00Z"
created_at: "2026-11-24T10:30:00Z"
updated_at: "2026-11-24T10:30:00Z"
merged_from: []
---

# Controlled form inputs: the box shows the new value, the request sends the old one

## 🎯 چالش / Challenge

فرمی با دو کادرِ کنترل‌شده (نام و شرح) ورودی را به یک خطِ تولیدِ LLM می‌فرستد. کاربر شرحِ «الف» را در کادر می‌بیند ولی خروجی هر بار دربارهٔ «ب» (ورودیِ دفعهٔ قبل) است — با پاسخِ ۲۰۰، بی هیچ خطا.
اولین گمان «کشِ سرور» یا «پیش‌نویسِ ذخیره‌شده» است؛ هیچ‌کدام نبود.

### علت

مقدارِ کادر بی‌رویدادِ فریم‌ورک عوض شده بود (پرکنندهٔ خودکار، افزونه، یا عاملِ مرورگری که `element.value = …` می‌نویسد). DOM مقدارِ تازه را نشان می‌دهد، state همان قبلی می‌ماند، و handler از state
می‌فرستد. با اولین رندرِ بعدی کادر هم به مقدارِ قدیمی برمی‌گردد — ولی کاربر دیگر به آن نگاه نمی‌کند.

## 💡 راه‌حل / Solution

۱. **اول سرور را جدا بسنج:** همان ورودی را مستقیم به endpoint بده. خروجیِ درست ⇒ مشکل در درخواست است، نه در تولید.
۲. **بازتولید در مرورگرِ واقعی:** متنِ قدیمی را عادی تایپ کن، متنِ تازه را با `el.value = …` بگذار، کلیک کن و **بدنهٔ درخواست** را بخوان (route interception).
۳. **هنگامِ ارسال، خودِ کادر را بخوان** (ref) و state را با آن هم‌گام کن — «آنچه دیده می‌شود همان فرستاده می‌شود».
۴. **ورودیِ هر خروجی را کنارِ خودش نشان بده** (پژواکِ سرور، نه حدسِ کلاینت) و اگر فرم بعداً عوض شد، خروجی را «کهنه» علامت بزن و عملِ بعدی را قفل کن.
۵. **خودسنجیِ ارزان پیش از عملِ برگشت‌ناپذیر/پرهزینه:** کلیدواژه‌های متمایزِ ورودی باید در خروجی باشند؛ مرز را سمتِ سرور هم بگذار (۴۰۹)، با راهِ عبورِ صریح برای خطای سنجش.

## 🧪 نمونه کد (Anonymized)

```tsx
const descRef = useRef<HTMLTextAreaElement>(null);
const readForm = () => {
  const d = descRef.current?.value ?? description;
  if (d !== description) setDescription(d);   // state follows what is on screen
  return { idea: d.trim() };
};
const submit = async () => {
  const form = readForm();                      // never the closure's state alone
  setResult(null);                              // a failed call must not leave the previous result on screen
  const data = await post({ idea: form.idea });
  setResult(data); setResultSource(data.source_idea ?? form.idea);
};
const stale = result && resultSource !== description.trim();   // ⇒ disable «confirm»
```

## ⚠️ نکات حیاتی / Pitfalls

- تطبیقِ کلیدواژه با زیررشته دروغ می‌گوید («تاریخ» در «تاریخچه»)؛ واژه‌ای تطبیق بده و واژه‌های عمومیِ حوزه («صفحه»، «وب»، «تست»، نامِ زبان‌ها) را کنار بگذار.
- خروجی‌ای که ورودی را عیناً پژواک می‌کند خودسنجی را بی‌اثر می‌کند — فقط بخش‌هایی را بسنج که **مدل** نوشته.
- زبانِ ورودی و خروجی که فرق دارد، «نشد بسنجم» بگو، نه «سالم» و نه «خراب».
- نتیجهٔ قبلی را پیش از درخواستِ تازه پاک کن؛ وگرنه شکستِ درخواست = نمایشِ نتیجهٔ کهنه به‌جای تازه.
- تابعی که هم state را عوض می‌کند و هم بلافاصله درخواست می‌فرستد، مقدارِ تازه را باید آرگومان بگیرد (closure هنوز مقدارِ قبلی را دارد).

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere

- هر فرمِ کنترل‌شده‌ای که ورودی‌اش به عملِ پرهزینه/برگشت‌ناپذیر می‌رسد (تولیدِ کد، ارسالِ پیام، پرداخت).
- هر جا کاربرِ فرم ممکن است ماشین باشد (تستِ خودکار، عاملِ مرورگر، مدیرِ رمز).
- هر خطِ «ورودی ⇒ LLM ⇒ ساخت»: پژواکِ ورودی + سنجشِ هم‌موضوعی پیش از مرحلهٔ ساخت.

## 🔗 References
- مرتبط: browser-agent-unseen-is-not-absent
