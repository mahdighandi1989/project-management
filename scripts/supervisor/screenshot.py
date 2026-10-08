#!/usr/bin/env python3
"""Take the «after» picture the way the owner sees the page — in a real browser,
on production (or any frontend you point it at).

    python3 scripts/supervisor/screenshot.py /projects --out /tmp/after.png
    python3 scripts/supervisor/screenshot.py /projects/12 --selector "main > div:nth-of-type(2)" --out /tmp/a.png
    python3 scripts/supervisor/screenshot.py /project/7 --tab "حافظه" --selector "…" --out /tmp/a.png
    python3 scripts/supervisor/screenshot.py /inspection --frontend http://localhost:3000 --out /tmp/x.png

`fixed` on a sheet needs an after-picture that shows THE PLACE THE OWNER BOXED.
Use the sheet's own anchor selector (QUEUE.md «گره») with --selector, and its
tab (QUEUE.md «زبانه») with --tab, so the picture is of that spot.

Ported from Detective-1 (`scripts/supervisor/screenshot.py`). This app has no
login, so no session is planted; the inspection overlays are switched off so
the picture is of the page itself.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import launch, open_page  # noqa: E402
from client import SupervisorError, frontend_url  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="عکسِ «بعد» از صفحه")
    ap.add_argument("path", help="مسیرِ صفحه، مثلاً /projects")
    ap.add_argument("--out", required=True)
    ap.add_argument("--selector", default="", help="فقط همین عنصر (گرهِ برگه)")
    ap.add_argument("--tab", default="", help="اول روی دکمهٔ زبانه‌ای با این متن کلیک کن")
    ap.add_argument("--frontend", default="", help="آدرسِ فرانت‌اند؛ پیش‌فرض: سرویسِ Render")
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--wait", type=int, default=2500)
    ap.add_argument("--full", action="store_true", help="کلِ صفحه (نه فقط پنجره)")
    args = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"error": "playwright نصب نیست: pip install playwright"}, ensure_ascii=False), file=sys.stderr)
        return 3
    try:
        base = (args.frontend or frontend_url()).rstrip("/")
    except SupervisorError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 3
    url = base + args.path
    with sync_playwright() as p:
        browser = launch(p)
        try:
            page, errors = open_page(browser, url, width=args.width, height=args.height, wait_ms=args.wait)
        except Exception as e:  # noqa: BLE001 - «could not look» is exit 3
            print(json.dumps({"error": f"صفحه باز نشد: {e}"[:400]}, ensure_ascii=False), file=sys.stderr)
            browser.close()
            return 3
        if args.tab:
            btn = page.get_by_role("button", name=args.tab).first
            try:
                btn.click(timeout=10_000)
                page.wait_for_timeout(1500)
            except Exception:  # noqa: BLE001
                print(json.dumps({"error": f"زبانهٔ «{args.tab}» پیدا نشد"}, ensure_ascii=False), file=sys.stderr)
                browser.close()
                return 2
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if args.selector:
            el = page.query_selector(args.selector)
            if el is None:
                print(json.dumps({"error": f"عنصرِ «{args.selector}» روی صفحه پیدا نشد"}, ensure_ascii=False), file=sys.stderr)
                browser.close()
                return 2
            el.scroll_into_view_if_needed()
            el.screenshot(path=str(out))
        else:
            page.screenshot(path=str(out), full_page=args.full)
        browser.close()
    print(json.dumps({"ok": True, "out": str(out), "url": url, "page_errors": errors}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
