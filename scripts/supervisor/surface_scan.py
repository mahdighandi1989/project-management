#!/usr/bin/env python3
"""Walk EVERY page (and every tab inside it) of the live app and record its map —
headings, tabs, sections, buttons, inputs and links with verified selectors and
document coordinates — into «نظارت و سرکشی › نقشهٔ سامانه».

    python3 scripts/supervisor/surface_scan.py              # production
    python3 scripts/supervisor/surface_scan.py --frontend http://localhost:3000
    python3 scripts/supervisor/surface_scan.py --only /projects /inspection

The measuring code is the APP'S OWN (`window.__pmSurfaceSnapshot`, from
frontend/src/lib/inspection/surface.tsx), so the owner's browser and this scan
can never disagree about how a screen is measured. The snapshot is posted with
the supervisor token (seen_by = supervisor-scan).

Pages come from the code inventory (docs/supervisor/inventory.json — run
inventory.py first); dynamic routes (`/projects/[id]`) use a sample URL the
owner's browser already registered, or are reported as «no sample yet».

Clicks ONLY tab buttons (to reach sub-pages). Never anything else: a scan that
presses «حذف» on production is not a scan.
Exit codes: 0 ok · 2 some pages failed · 3 could not run at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import launch, open_page  # noqa: E402
from client import Client, SupervisorError, frontend_url  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INV = ROOT / "docs" / "supervisor" / "inventory.json"
OUT = ROOT / "docs" / "supervisor" / "last_surface_scan.json"

#: tab buttons only — the same rule the app uses (role=tab, or a bar of buttons
#: with exactly one styled «active»); returns their labels in order
TABS_JS = """() => {
  const out = [];
  const seen = new Set();
  const push = (b) => { const t = (b.innerText || b.textContent || '').trim().replace(/\\s+/g,' ');
    if (t && !seen.has(t) && !/حذف|delete|remove|پاک|ارسال|send|deploy|اجرا|run|خروج|ثبت|ذخیره|افزودن|ایجاد|روشن|خاموش|import|sync|save|create|add|new|＋|\+|📝|⚡/i.test(t)) { seen.add(t); out.push(t); } };
  document.querySelectorAll('[data-report-surface] [role="tab"]').forEach(push);
  const ACTIVE = /(^|\\s)(border-b-2|bg-white shadow|bg-primary-|bg-blue-600|bg-gray-900|bg-indigo-600|bg-purple-600)/;
  document.querySelectorAll('[data-report-surface] div, [data-report-surface] nav').forEach((bar) => {
    const bs = Array.from(bar.children).filter((c) => c.tagName === 'BUTTON');
    if (bs.length < 2 || bs.length > 14 || bs.length < bar.children.length * 0.6) return;
    if (bs.filter((b) => ACTIVE.test(b.className || '')).length !== 1) return;
    bs.forEach(push);
  });
  return out.slice(0, 16);
}"""


def main() -> int:
    ap = argparse.ArgumentParser(description="نقشهٔ همهٔ صفحه‌ها و زبانه‌ها")
    ap.add_argument("--frontend", default="")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--no-tabs", action="store_true")
    args = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"error": "playwright نصب نیست"}, ensure_ascii=False), file=sys.stderr)
        return 3
    try:
        c = Client()
        c.whoami()
        base = (args.frontend or frontend_url()).rstrip("/")
        known = {s["route"]: s for s in c.api("/api/inspection/surfaces").get("surfaces", [])}
    except SupervisorError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 3
    routes: list[str] = args.only or []
    if not routes:
        try:
            routes = [p["route"] for p in json.loads(INV.read_text(encoding="utf-8"))["pages"]]
        except Exception:  # noqa: BLE001
            print(json.dumps({"error": "inventory.json نیست — اول inventory.py را اجرا کن"}, ensure_ascii=False),
                  file=sys.stderr)
            return 3
    report: dict = {"base": base, "pages": [], "failed": [], "no_sample": []}
    with sync_playwright() as p:
        browser = launch(p)
        for route in routes:
            path = route
            if "[id]" in route:
                sample = (known.get(route) or {}).get("sample_path")
                if not sample:
                    report["no_sample"].append(route)
                    continue
                path = sample
            try:
                page, errors = open_page(browser, base + path)
                snaps = [page.evaluate("() => window.__pmSurfaceSnapshot && window.__pmSurfaceSnapshot()")]
                tabs = [] if args.no_tabs else page.evaluate(TABS_JS)
                for label in tabs:
                    try:
                        page.get_by_role("button", name=label, exact=True).first.click(timeout=8000)
                    except Exception:  # noqa: BLE001
                        try:
                            page.get_by_role("tab", name=label, exact=True).first.click(timeout=8000)
                        except Exception:  # noqa: BLE001
                            continue
                    page.wait_for_timeout(1200)
                    snaps.append(page.evaluate("() => window.__pmSurfaceSnapshot && window.__pmSurfaceSnapshot()"))
                posted = 0
                for snap in snaps:
                    if not snap:
                        continue
                    snap["route"] = route
                    c.api("/api/inspection/surfaces", body=snap)
                    posted += 1
                report["pages"].append({"route": route, "path": path, "snapshots": posted,
                                        "tabs": tabs, "page_errors": errors[:5]})
                page.context.close()
                if not snaps or not snaps[0]:
                    report["failed"].append({"route": route, "error": "تابعِ اندازه‌گیری روی صفحه نبود (نسخهٔ قدیمیِ فرانت؟)"})
            except Exception as e:  # noqa: BLE001 - record and continue with the next page
                report["failed"].append({"route": route, "error": str(e)[:300]})
        browser.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"pages": len(report["pages"]), "snapshots": sum(x["snapshots"] for x in report["pages"]),
                      "failed": len(report["failed"]), "no_sample": report["no_sample"]}, ensure_ascii=False))
    return 2 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
