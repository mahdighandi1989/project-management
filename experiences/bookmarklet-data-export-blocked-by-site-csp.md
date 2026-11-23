---
title: "Bookmarklet data export blocked by the host site's CSP — open a receiver window and postMessage"
tags: ["bookmarklet", "csp", "form-action", "connect-src", "postmessage", "window-open", "coop", "testing"]
topic_canonical: "bookmarklet-data-export-blocked-by-site-csp"
source:
  type: "claude-code-task"
  origin: "claude-code"
  imported_at: "2026-11-23T09:30:00Z"
created_at: "2026-11-23T09:30:00Z"
updated_at: "2026-11-23T09:30:00Z"
merged_from: []
---

# Bookmarklet data export blocked by the host site's CSP

## 🎯 چالش / Challenge

یک بوک‌مارکلت روی سایتِ A اجرا می‌شود و باید داده‌ای را به سرورِ B برساند. با `<form method=POST target=_blank>` نوشته
شده بود. روی سایتِ واقعی کاربر فقط یک زبانهٔ تازه با `405 Method Not Allowed` می‌دید و هیچ POST ای به سرور نمی‌رسید.

### علت

بوک‌مارکلت در **صفحهٔ A** اجرا می‌شود و تابعِ CSP ِ همان صفحه است. `form-action 'self'` فرم به مبدأِ دیگر را می‌بندد و
`connect-src 'self'` هم `fetch`/XHR/`sendBeacon` را. کروم زبانهٔ `_blank` را باز می‌گذارد ولی POST نمی‌کند.

## 💡 راه‌حل / Solution

CSP ناوبری و `postMessage` را محدود نمی‌کند:

1. بوک‌مارکلت **اول و هم‌زمان با کلیک** `w = window.open(<صفحهٔ گیرنده روی B>)` می‌زند (پیش از هر `await`، تا user activation نسوزد).
2. صفحهٔ گیرنده هر ۳۰۰ms به `window.opener` پیامِ `ready` می‌دهد؛ بوک‌مارکلت پس از آماده‌شدنِ داده با `w.postMessage(data, <مبدأِ B>)` جواب می‌دهد (targetOrigin ِ دقیق، نه `*`).
3. گیرنده فقط از `event.source === window.opener` می‌پذیرد، **`event.origin` را به‌جای مبدأِ ادعاشده در داده** می‌گذارد و هم‌مبدأ POST می‌کند.

شرط‌ها: صفحهٔ گیرنده نباید `Cross-Origin-Opener-Policy` بدهد (opener قطع می‌شود)؛ `COOP: same-origin-allow-popups` روی سایتِ A مانعی نیست.

## ⚠️ نکات حیاتی / Pitfalls

کدی که داخلِ صفحهٔ یک سایتِ دیگر اجرا می‌شود را با **سربرگ‌های واقعیِ همان سایت** بسنج: `curl -sI <site>` و یک صفحهٔ محلی با همان
`Content-Security-Policy` و `Cross-Origin-Opener-Policy`. آزمون با پاسخ‌های ساختگیِ بی‌سربرگ این دسته خطا را نمی‌بیند.

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere

- هر جا اسکریپتی در صفحهٔ شخصِ ثالث باید داده بیرون بدهد (بوک‌مارکلت، اسنیپتِ کنسول): اول CSP ِ آن صفحه را بخوان.
- `form-action` / `connect-src` محدود ⇒ پنجرهٔ گیرنده + `postMessage`؛ هویتِ فرستنده را از `event.origin` بگیر.

## 🔗 References
- مرتبط: cloudflare-403-on-chunked-cross-origin-post
