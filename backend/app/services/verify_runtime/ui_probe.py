"""Stage 3b — UI probe با Playwright (headless browser).

برای AC هایی با method=ui_interaction، یک headless Chromium باز می‌کند
و steps را اجرا می‌کند.

verify_plan schema:
{
  "base": "frontend",   # یا "backend" — کدام base_url
  "ui_steps": [
    {"action": "navigate", "url": "/path"},
    {"action": "wait_for_load_state", "state": "networkidle"|"domcontentloaded"|"load"},
    {"action": "click", "selector": "..."},
    {"action": "fill", "selector": "...", "value": "..."},
    {"action": "wait_for_selector", "selector": "...", "timeout_ms": 3000},
    {"action": "assert_visible", "selector": "..."},
    {"action": "assert_text", "selector": "...", "contains": "..."},
    {"action": "assert_url", "contains": "..."},
    {"action": "screenshot", "label": "..."}
  ]
}

Playwright در محیط Render شاید نصب نباشد — اگر import شکست خورد،
graceful degrade به PROBE_STATUS_SKIPPED.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import (
    PROBE_STATUS_ERROR,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_SKIPPED,
    ProbeContext,
    RuntimeProbeResult,
)

logger = logging.getLogger(__name__)

# global flag — اگر playwright در دسترس نباشد، تمام UI probe ها skipped
_PLAYWRIGHT_AVAILABLE: Optional[bool] = None


def _check_playwright_available() -> bool:
    """one-shot import check (cached)."""
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is not None:
        return _PLAYWRIGHT_AVAILABLE
    try:
        import playwright.async_api  # noqa: F401
        _PLAYWRIGHT_AVAILABLE = True
    except ImportError:
        _PLAYWRIGHT_AVAILABLE = False
    return _PLAYWRIGHT_AVAILABLE


def _select_base_url(base_pref: str, ctx: ProbeContext) -> Optional[str]:
    """انتخاب base_url بر اساس verify_plan.base ('frontend'|'backend')."""
    if base_pref == "backend":
        return ctx.backend_base_url
    return ctx.frontend_base_url  # default frontend


def _ensure_evidence_dir(ctx: ProbeContext, ac_id: str) -> Optional[Path]:
    """مسیر ذخیرهٔ screenshot ها را آماده کن."""
    if not ctx.evidence_dir:
        return None
    p = Path(ctx.evidence_dir) / ac_id
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"ui_probe evidence_dir create failed: {e}")
        return None
    return p


async def _apply_auth(context: Any, ctx: ProbeContext, base_url: str) -> None:
    """احراز هویت را روی Playwright context اعمال کن."""
    auth_type = (ctx.auth_type or "").lower()
    if not ctx.auth_value:
        return
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        domain = parsed.netloc
        if auth_type == "cookie":
            # auth_value به شکل "name1=val1; name2=val2"
            cookies = []
            for pair in ctx.auth_value.split(";"):
                if "=" not in pair:
                    continue
                k, v = pair.split("=", 1)
                cookies.append({
                    "name": k.strip(),
                    "value": v.strip(),
                    "domain": domain,
                    "path": "/",
                })
            if cookies:
                await context.add_cookies(cookies)
        elif auth_type == "bearer":
            await context.set_extra_http_headers({
                "Authorization": f"Bearer {ctx.auth_value}",
            })
    except Exception as e:
        logger.debug(f"ui_probe auth apply failed: {e}")


async def _take_screenshot(
    page: Any, evidence_path: Optional[Path], label: str,
) -> Optional[str]:
    """screenshot بگیر و path نسبی برگردان (یا None اگر fail)."""
    if not evidence_path:
        return None
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
    fname = f"{safe_label}_{int(time.time() * 1000)}.png"
    fpath = evidence_path / fname
    try:
        await page.screenshot(path=str(fpath), full_page=False)
        return fname
    except Exception as e:
        logger.debug(f"screenshot failed: {e}")
        return None


async def _run_step(
    page: Any,
    step: Dict[str, Any],
    evidence_path: Optional[Path],
    step_idx: int,
) -> Tuple[bool, str, Optional[str]]:
    """یک step را اجرا کن. خروجی: (success, message, screenshot_filename)
    در صورت assert failure، success=False ولی exception نمی‌اندازد.
    """
    action = str(step.get("action") or "").strip()
    if not action:
        return False, "step بدون action", None
    try:
        if action == "navigate":
            url = step.get("url") or "/"
            await page.goto(url, wait_until="domcontentloaded")
            return True, f"navigated to {url}", None
        if action == "wait_for_load_state":
            state = step.get("state") or "networkidle"
            await page.wait_for_load_state(state)
            return True, f"load state: {state}", None
        if action == "click":
            sel = step.get("selector") or ""
            if not sel:
                return False, "click بدون selector", None
            await page.click(sel)
            shot = await _take_screenshot(page, evidence_path, f"step{step_idx}_click")
            return True, f"clicked {sel}", shot
        if action == "fill":
            sel = step.get("selector") or ""
            val = step.get("value") or ""
            if not sel:
                return False, "fill بدون selector", None
            await page.fill(sel, val)
            return True, f"filled {sel}", None
        if action == "wait_for_selector":
            sel = step.get("selector") or ""
            timeout_ms = int(step.get("timeout_ms") or 3000)
            await page.wait_for_selector(sel, timeout=timeout_ms)
            return True, f"selector visible: {sel}", None
        if action == "assert_visible":
            sel = step.get("selector") or ""
            if not sel:
                return False, "assert_visible بدون selector", None
            try:
                el = await page.wait_for_selector(sel, timeout=3000, state="visible")
                visible = el is not None
            except Exception as e:
                shot = await _take_screenshot(page, evidence_path, f"step{step_idx}_visiblefail")
                return False, f"not visible: {sel} ({e})", shot
            shot = await _take_screenshot(page, evidence_path, f"step{step_idx}_visible")
            return visible, f"visible: {sel}", shot
        if action == "assert_text":
            sel = step.get("selector") or ""
            contains = step.get("contains") or ""
            try:
                el = await page.wait_for_selector(sel, timeout=3000)
                if not el:
                    return False, f"selector نبود: {sel}", None
                text = await el.inner_text()
            except Exception as e:
                return False, f"selector وافی نبود: {e}", None
            if contains and contains in text:
                return True, f"text contains '{contains[:50]}'", None
            return False, f"text mismatch (got '{text[:80]}')", None
        if action == "assert_url":
            contains = step.get("contains") or ""
            url = page.url
            if contains in url:
                return True, f"url contains '{contains}'", None
            return False, f"url mismatch ({url})", None
        if action == "screenshot":
            label = step.get("label") or "screenshot"
            shot = await _take_screenshot(page, evidence_path, f"step{step_idx}_{label}")
            return True, f"screenshot: {label}", shot
        return False, f"action ناشناخته: {action}", None
    except Exception as e:
        # هر خطای ناشی از Playwright (مثل locator failed) → step fail
        shot = await _take_screenshot(page, evidence_path, f"step{step_idx}_error")
        return False, f"خطا: {str(e)[:200]}", shot


async def run_ui_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
) -> RuntimeProbeResult:
    """UI probe را با Playwright اجرا می‌کند."""
    start = time.monotonic()
    ac_text = str(ac.get("text") or "")
    plan = ac.get("verify_plan") or {}
    ui_steps = plan.get("ui_steps") or []

    if not _check_playwright_available():
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="ui_interaction",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "playwright در دسترس نیست — install: pip install playwright && playwright install chromium"},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    if not ui_steps:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="ui_interaction",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "ui_steps خالی است"},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    base_pref = str(plan.get("base") or "frontend").lower()
    base_url = _select_base_url(base_pref, ctx)
    if not base_url:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="ui_interaction",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": f"{base_pref}_base_url تنظیم نشده"},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    evidence_path = _ensure_evidence_dir(ctx, ac_id)

    # اولین navigate باید absolute باشد (Playwright نسبی را قبول نمی‌کند مگر page.goto)
    # ما اولین step را اگر navigate است با base_url کامل می‌کنیم.
    normalized_steps: List[Dict[str, Any]] = []
    for s in ui_steps:
        ns = dict(s)
        if ns.get("action") == "navigate":
            url = ns.get("url") or "/"
            if not url.startswith("http"):
                if not url.startswith("/"):
                    url = "/" + url
                ns["url"] = base_url.rstrip("/") + url
        normalized_steps.append(ns)

    step_results: List[Dict[str, Any]] = []
    screenshots: List[str] = []
    all_passed = True

    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="ui_interaction",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": "playwright import failed"},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e),
        )

    try:
        async with async_playwright() as pw:
            try:
                browser = await pw.chromium.launch(headless=True)
            except Exception as e:
                return RuntimeProbeResult(
                    ac_id=ac_id,
                    ac_text=ac_text,
                    method="ui_interaction",
                    status=PROBE_STATUS_ERROR,
                    evidence={"reason": f"chromium launch failed: {e}"},
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error_message=str(e),
                )
            try:
                context = await browser.new_context()
                await _apply_auth(context, ctx, base_url)
                page = await context.new_page()
                page.set_default_timeout(ctx.ui_timeout_ms)

                for idx, step in enumerate(normalized_steps, start=1):
                    success, msg, shot = await _run_step(
                        page, step, evidence_path, idx,
                    )
                    step_results.append({
                        "step": idx,
                        "action": step.get("action"),
                        "success": success,
                        "message": msg,
                        "screenshot": shot,
                    })
                    if shot:
                        screenshots.append(shot)
                    if not success:
                        all_passed = False
                        break  # توقف پس از اولین failure

                # یک screenshot نهایی برای evidence
                final_shot = await _take_screenshot(page, evidence_path, "final")
                if final_shot:
                    screenshots.append(final_shot)
            finally:
                try:
                    await browser.close()
                except Exception:
                    pass
    except Exception as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="ui_interaction",
            status=PROBE_STATUS_ERROR,
            evidence={
                "reason": f"playwright crashed: {e}",
                "step_results": step_results,
                "screenshots": screenshots,
            },
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e)[:300],
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    evidence = {
        "base_url": base_url,
        "step_count": len(normalized_steps),
        "step_results": step_results,
        "screenshots": screenshots,
    }

    if all_passed:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="ui_interaction",
            status=PROBE_STATUS_PASSED,
            evidence=evidence,
            duration_ms=duration_ms,
        )
    # یک step شکست خورد → failed
    failed_step = next((s for s in step_results if not s["success"]), {})
    return RuntimeProbeResult(
        ac_id=ac_id,
        ac_text=ac_text,
        method="ui_interaction",
        status=PROBE_STATUS_FAILED,
        evidence=evidence,
        duration_ms=duration_ms,
        error_message=f"step {failed_step.get('step', '?')}: {failed_step.get('message', '')[:200]}",
    )
