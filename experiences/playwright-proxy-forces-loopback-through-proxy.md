---
title: "Playwright behind an egress proxy sends localhost through the proxy — local pages all «fail»"
tags: ["playwright", "chromium", "proxy", "localhost", "loopback", "testing", "ci"]
topic_canonical: "playwright-proxy-forces-loopback-through-proxy"
source:
  type: "claude-code-task"
  origin: "claude-code"
  imported_at: "2026-11-24T01:30:00Z"
created_at: "2026-11-24T01:30:00Z"
updated_at: "2026-11-24T01:30:00Z"
merged_from: []
---

# Playwright behind an egress proxy sends localhost through the proxy

## 🎯 چالش / Challenge

یک اسکنِ مرورگری (Playwright + Chromium) هم باید سایتِ بیرونی را از راهِ پراکسیِ محیط ببیند و هم برنامهٔ محلی
(`http://localhost:3000`) را. با `proxy={"server": …, "bypass": "localhost,127.0.0.1"}` همهٔ صفحه‌های محلی «شکست» خوردند
(«تابعِ اندازه‌گیری روی صفحه نبود») در حالی که `curl` همان نشانی را ۲۰۰ می‌گرفت. ابزار «محیط نرسید» را به شکلِ «محصول خراب است»
گزارش می‌کرد.

### علت

Playwright وقتی پراکسی دارد، به‌طورِ پیش‌فرض `<-loopback>` را به فهرستِ bypass ِ Chromium اضافه می‌کند: یعنی **loopback هم از
پراکسی رد می‌شود** و قاعدهٔ `bypass: "localhost"` بی‌اثر می‌ماند. پراکسی‌ای که فقط تونلِ HTTPS می‌پذیرد برای `http://localhost`
صفحهٔ خطای خودش را برمی‌گرداند — مرورگر «۲۰۰ با محتوای اشتباه» می‌بیند، نه خطای شبکه.

## 💡 راه‌حل / Solution

متغیرِ محیطیِ `PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK=1` را **پیش از شروعِ درایورِ Playwright** بگذار (در سطحِ
ماژول، قبل از `sync_playwright()`؛ گذاشتنش درست پیش از `chromium.launch()` دیر است چون درایور قبلاً بالا آمده):

```python
import os
os.environ.setdefault("PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK", "1")
```

اگر تغییرِ محیط ممکن نیست: `context.route("http://127.0.0.1:PORT/**", handler)` و در handler خودت بی‌پراکسی بگیر و `fulfill` کن.

## ⚠️ نکات حیاتی / Pitfalls

- نشانه: متنِ صفحه پیامِ خودِ پراکسی است («only accepts HTTPS CONNECT tunnels»)، نه برنامهٔ تو. اول `inner_text('body')` را چاپ کن.
- «نرسیدم» را هرگز «خراب است» گزارش نکن؛ ابزارِ سنجش باید این دو را جدا بگوید.

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere

- هر CI/کانتینری که `HTTPS_PROXY` دارد و با Playwright هم سایتِ بیرونی و هم سرورِ محلی را می‌بیند.

## 🔗 References
- مرتبط: bookmarklet-data-export-blocked-by-site-csp
