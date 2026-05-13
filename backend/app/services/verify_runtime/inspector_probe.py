"""Inspector probe — Phase 1 of auto-verify ↔ Inspector integration.

این probe برای AC هایی با method=ui_interaction (و verify_plan ضعیف یا
خالی) فراخوانی می‌شود. به‌جای اجرای ui_steps ساختاریافته، یک رفتار سبک
exploratory دارد:

  1. آدرس را با Playwright سرور-سایدی باز کند (با base_url مربوطه)
  2. console errors را در طول مدت تست ضبط کند
  3. screenshot قبل و (در صورت click) بعد از click بگیرد
  4. اگر selector_hint از verify_plan داده شده، اول click می‌کند
  5. backend logs در پنجره‌ی زمانی probe را از RenderLog DB بخواند
  6. screenshot ها را با vision_helper تحلیل کند (multimodal → fallback متنی)
  7. اقدامات قدم‌به‌قدم را در inspector_session مربوطه ذخیره کند تا کاربر
     بتواند از تب «بازرس ویژه» مشاهده کند
  8. RuntimeProbeResult با evidence غنی برگرداند

تمام مراحل graceful degrade دارند — هیچ exception ای بیرون نمی‌اندازد.
screenshot ها روی دیسک ذخیره می‌شوند (نه base64 در DB) و توسط
notification بعدی به تلگرام آرشیو می‌شوند، سپس از دیسک پاک می‌شوند.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
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

# محدودیت Phase 1
_TIMEOUT_S = 60
_MAX_SCREENSHOTS = 2
_MAX_SCREENSHOT_BYTES = 500_000  # ~500KB
_MAX_CONSOLE_LOGS = 50
# 🆕 (Phase 2) محدودیت ضبط network requests
_MAX_NETWORK_CALLS = 30
_STATIC_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".otf",
    ".css", ".js", ".mjs", ".map", ".ico",
)


# ---------------------------------------------------------------------------
# سمافور: فقط یک inspector_probe در هر لحظه اجرا شود (session-bound)
# ---------------------------------------------------------------------------
_INSPECTOR_SEMAPHORE = asyncio.Semaphore(1)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _select_base_url(plan: Dict[str, Any], ctx: ProbeContext) -> Optional[str]:
    """انتخاب base_url بر اساس verify_plan.base."""
    base_pref = str(plan.get("base") or "frontend").lower()
    if base_pref == "backend":
        return ctx.backend_base_url
    return ctx.frontend_base_url


def _extract_url_hint(plan: Dict[str, Any]) -> str:
    """URL relative از verify_plan استخراج کن (اولین navigate در ui_steps یا /)."""
    steps = plan.get("ui_steps") or []
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, dict) and s.get("action") == "navigate":
                u = str(s.get("url") or "").strip()
                if u:
                    return u
    # gefore explicit hint
    hint = plan.get("url_hint") or plan.get("path") or "/"
    return str(hint or "/")


def _extract_selector_hint(plan: Dict[str, Any]) -> Optional[str]:
    """selector_hint از verify_plan — اولین click یا selector_hint صریح."""
    if "selector_hint" in plan:
        s = plan.get("selector_hint")
        if isinstance(s, str) and s.strip():
            return s.strip()
    steps = plan.get("ui_steps") or []
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, dict) and s.get("action") == "click":
                sel = s.get("selector")
                if isinstance(sel, str) and sel.strip():
                    return sel.strip()
    return None


def _ensure_screenshot_dir(ctx: ProbeContext, ac_id: str) -> Optional[Path]:
    """مسیر storage/oversight/runtime_evidence/{task_id}/{run_id}/{ac_id}/ را بساز."""
    try:
        from ..oversight_service import STORAGE_DIR
    except Exception:
        return None
    base = Path(STORAGE_DIR) / "runtime_evidence" / str(ctx.task_id) / str(ctx.run_id) / str(ac_id)
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception as e:
        logger.warning(f"inspector_probe: cannot create screenshot dir: {e}")
        return None


async def _fetch_backend_logs_window(
    ctx: ProbeContext, started_at: datetime, finished_at: datetime,
) -> Tuple[str, List[Dict[str, Any]]]:
    """لاگ‌های backend در پنجره‌ی زمانی probe — query مستقیم به RenderLog.

    خروجی: (summary_str, raw_list)
    summary فقط شامل error و warn است.
    """
    try:
        from ...core.database import SessionLocal
        from ...models.render_log import RenderLog
    except Exception as e:
        logger.debug(f"inspector_probe: render_log import failed: {e}")
        return ("", [])

    def _q() -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            rows = (
                db.query(RenderLog)
                .filter(RenderLog.timestamp >= started_at - timedelta(seconds=5))
                .filter(RenderLog.timestamp <= finished_at + timedelta(seconds=5))
                .filter(RenderLog.level.in_(["error", "warn", "warning"]))
                .order_by(RenderLog.timestamp.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "level": r.level,
                    "message": (r.message or "")[:500],
                    "service_id": r.service_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.debug(f"inspector_probe: render_log query failed: {e}")
            return []
        finally:
            db.close()

    rows = await asyncio.to_thread(_q)
    if not rows:
        return ("بدون خطای backend در پنجره‌ی زمانی", [])
    err_count = sum(1 for r in rows if r["level"] == "error")
    warn_count = len(rows) - err_count
    sample = " | ".join((r["message"] or "")[:80] for r in rows[:3])
    summary = f"{err_count} error + {warn_count} warn — نمونه: {sample}"
    return (summary[:600], rows)


# ---------------------------------------------------------------------------
# inspector_session writers (sync, wrapped via to_thread)
# ---------------------------------------------------------------------------

def _save_inspector_message_sync(
    session_id: int,
    role: str,
    content: str,
    *,
    action_type: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """ذخیره یک پیام در InspectorMessage. شکست‌خوردگی silent."""
    try:
        from ...core.database import SessionLocal
        from ...models.inspector_session import InspectorMessage
    except Exception as e:
        logger.debug(f"inspector_probe: model import failed: {e}")
        return
    db = SessionLocal()
    try:
        msg = InspectorMessage(
            session_id=session_id,
            role=role,
            content=content[:5000],
            action_type=action_type,
            extra_data=json.dumps(extra_data, ensure_ascii=False)[:8000] if extra_data else None,
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        logger.debug(f"inspector_probe: save msg failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass


async def _msg(session_id: Optional[int], role: str, content: str, **kwargs: Any) -> None:
    """wrapper async برای _save_inspector_message_sync."""
    if session_id is None:
        return
    await asyncio.to_thread(
        _save_inspector_message_sync, session_id, role, content, **kwargs
    )


# ---------------------------------------------------------------------------
# main probe
# ---------------------------------------------------------------------------

async def run_inspector_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
) -> RuntimeProbeResult:
    """اجرای inspector_probe برای یک AC.

    این تابع هیچ exception ای بیرون نمی‌اندازد — هر خطا → ProbeError در evidence.
    """
    start_mono = time.monotonic()
    started_at_dt = datetime.now(timezone.utc)
    ac_text = str(ac.get("text") or "")
    plan = ac.get("verify_plan") or {}

    # ------- pre-checks -------
    from .safety import is_runtime_enabled, is_ui_probe_enabled, get_breaker
    if not is_runtime_enabled():
        return _skipped(ac_id, ac_text, "RUNTIME_VERIFY_ENABLED=false", start_mono)
    if not is_ui_probe_enabled():
        return _skipped(ac_id, ac_text, "RUNTIME_VERIFY_UI_ENABLED=false", start_mono)
    if get_breaker().is_open("ui_interaction"):
        return _skipped(ac_id, ac_text, "circuit breaker open for ui_interaction", start_mono)

    base_url = _select_base_url(plan, ctx)
    if not base_url:
        return _skipped(ac_id, ac_text, "frontend_base_url تنظیم نشده", start_mono)

    # ------- semaphore: sequential -------
    async with _INSPECTOR_SEMAPHORE:
        try:
            return await asyncio.wait_for(
                _run_inspector_inner(
                    ac, ctx, ac_id, ac_text, plan, base_url,
                    start_mono, started_at_dt,
                ),
                timeout=_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            await _msg(
                ctx.inspector_session_id, "system",
                f"⌛ probe timeout ({_TIMEOUT_S}s) — ac «{ac_text[:80]}»",
            )
            return RuntimeProbeResult(
                ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
                status=PROBE_STATUS_ERROR,
                evidence={"reason": f"timeout > {_TIMEOUT_S}s", "inspector_session_id": ctx.inspector_session_id},
                duration_ms=int((time.monotonic() - start_mono) * 1000),
                error_message="probe timeout",
            )
        except Exception as e:
            logger.warning(f"inspector_probe crashed: {e}", exc_info=False)
            await _msg(
                ctx.inspector_session_id, "system",
                f"💥 probe crashed: {str(e)[:200]}",
            )
            return RuntimeProbeResult(
                ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
                status=PROBE_STATUS_ERROR,
                evidence={"reason": f"crashed: {e}", "inspector_session_id": ctx.inspector_session_id},
                duration_ms=int((time.monotonic() - start_mono) * 1000),
                error_message=str(e)[:300],
            )


async def _run_inspector_inner(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
    ac_text: str,
    plan: Dict[str, Any],
    base_url: str,
    start_mono: float,
    started_at_dt: datetime,
) -> RuntimeProbeResult:
    """منطق اصلی probe — جدا تا timeout بتواند آن را لغو کند."""
    from .browser_pool import get_browser_pool

    url_hint = _extract_url_hint(plan)
    selector_hint = _extract_selector_hint(plan)

    # absolute URL
    if url_hint.startswith("http"):
        full_url = url_hint
    else:
        if not url_hint.startswith("/"):
            url_hint = "/" + url_hint
        full_url = base_url.rstrip("/") + url_hint

    # screenshot dir
    shot_dir = _ensure_screenshot_dir(ctx, ac_id)

    # log to session
    await _msg(
        ctx.inspector_session_id, "system",
        f"🚀 شروع auto-verify probe برای AC: «{ac_text[:100]}»",
        extra_data={"ac_id": ac_id, "full_url": full_url, "selector_hint": selector_hint},
    )

    pool = get_browser_pool()
    browser = await pool.get_browser()
    if browser is None:
        await _msg(
            ctx.inspector_session_id, "system",
            "⏭ Playwright/Chromium در دسترس نیست — probe skip شد",
        )
        return _skipped(ac_id, ac_text, "browser pool unavailable", start_mono)

    actions_taken: List[Dict[str, Any]] = []
    screenshots: List[Dict[str, Any]] = []
    console_errors: List[Dict[str, Any]] = []
    final_url: str = full_url
    html_excerpt: str = ""
    context = None
    page = None

    try:
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            page.set_default_timeout(ctx.ui_timeout_ms)

            # console listener
            def _on_console(m: Any) -> None:
                try:
                    if len(console_errors) >= _MAX_CONSOLE_LOGS:
                        return
                    lvl = (m.type or "log").lower()
                    if lvl not in ("error", "warning", "warn"):
                        return
                    console_errors.append({
                        "level": "error" if lvl == "error" else "warning",
                        "message": (m.text or "")[:400],
                        "source": "console",
                        "timestamp": _now_iso(),
                    })
                except Exception:
                    pass

            page.on("console", _on_console)

            # 🆕 (Phase 2) — network capture: همه‌ی درخواست‌های API را ضبط کن
            # تا «ادرس‌های بک‌اند که فرانت در حین لود زده» در evidence باشد.
            # استاتیک‌ها (image/font/css/js) filter می‌شوند.
            network_calls: List[Dict[str, Any]] = []

            def _on_request(req: Any) -> None:
                try:
                    if len(network_calls) >= _MAX_NETWORK_CALLS:
                        return
                    url = (getattr(req, "url", "") or "")
                    if not url or url.startswith(("data:", "blob:")):
                        return
                    low = url.lower().split("?", 1)[0]
                    if any(low.endswith(ext) for ext in _STATIC_EXTENSIONS):
                        return
                    network_calls.append({
                        "url": url[:500],
                        "method": (getattr(req, "method", None) or "GET")[:10],
                        "resource_type": (getattr(req, "resource_type", None) or "")[:30],
                        "status": None,
                        "timestamp": _now_iso(),
                    })
                except Exception:
                    pass

            def _on_response(resp: Any) -> None:
                try:
                    url = (getattr(resp, "url", "") or "")
                    status = getattr(resp, "status", None)
                    # status فقط برای request اولی که هنوز status ندارد ست شود
                    for item in network_calls:
                        if item.get("url") == url and item.get("status") is None:
                            item["status"] = status
                            break
                except Exception:
                    pass

            page.on("request", _on_request)
            page.on("response", _on_response)

            # ---- navigate ----
            nav_start = time.monotonic()
            try:
                resp = await page.goto(full_url, wait_until="domcontentloaded")
                nav_status = getattr(resp, "status", 0) if resp else 0
                nav_ok = bool(resp) and (nav_status == 0 or nav_status < 400)
            except Exception as e:
                nav_ok = False
                nav_status = 0
                await _msg(
                    ctx.inspector_session_id, "action",
                    f"❌ navigate به {full_url} fail: {str(e)[:200]}",
                    action_type="navigate",
                )
                actions_taken.append({
                    "action": "navigate", "url": full_url,
                    "duration_ms": int((time.monotonic() - nav_start) * 1000),
                    "success": False, "error": str(e)[:200],
                })
                return _build_result_after_failure(
                    ac_id, ac_text, ctx, start_mono, actions_taken, screenshots,
                    console_errors, "navigate failed", html_excerpt, final_url,
                    network_calls=network_calls,
                )

            actions_taken.append({
                "action": "navigate", "url": full_url,
                "duration_ms": int((time.monotonic() - nav_start) * 1000),
                "success": nav_ok, "status": nav_status,
            })
            await _msg(
                ctx.inspector_session_id, "action",
                f"📍 navigate به {full_url} (status={nav_status})",
                action_type="navigate",
            )

            # کمی صبر برای SPA render (در حد امن)
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            final_url = page.url or full_url

            # screenshot 1 (after_navigate)
            shot1 = await _take_and_record_screenshot(
                page, shot_dir, "after_navigate", screenshots, actions_taken, ctx,
            )

            # capture HTML excerpt (for vision fallback)
            try:
                html_excerpt = (await page.content())[:5000]
            except Exception:
                html_excerpt = ""

            # ---- click (در صورت وجود selector_hint) ----
            selector_found = True  # default if no hint
            if selector_hint:
                click_start = time.monotonic()
                try:
                    el = await page.wait_for_selector(selector_hint, timeout=5000, state="visible")
                    selector_found = el is not None
                    if selector_found and len(screenshots) < _MAX_SCREENSHOTS:
                        await el.click()
                        actions_taken.append({
                            "action": "click", "selector": selector_hint,
                            "duration_ms": int((time.monotonic() - click_start) * 1000),
                            "success": True,
                        })
                        await _msg(
                            ctx.inspector_session_id, "action",
                            f"👆 click روی {selector_hint}",
                            action_type="click",
                        )
                        # کمی صبر برای واکنش
                        try:
                            await page.wait_for_load_state("networkidle", timeout=3000)
                        except Exception:
                            pass
                        final_url = page.url or final_url
                        # screenshot 2 (after_click)
                        await _take_and_record_screenshot(
                            page, shot_dir, "after_click",
                            screenshots, actions_taken, ctx,
                        )
                    elif not selector_found:
                        actions_taken.append({
                            "action": "click", "selector": selector_hint,
                            "duration_ms": int((time.monotonic() - click_start) * 1000),
                            "success": False, "error": "selector not visible",
                        })
                        await _msg(
                            ctx.inspector_session_id, "system",
                            f"⚠️ selector «{selector_hint}» روی صفحه پیدا نشد",
                        )
                except Exception as e:
                    selector_found = False
                    actions_taken.append({
                        "action": "click", "selector": selector_hint,
                        "duration_ms": int((time.monotonic() - click_start) * 1000),
                        "success": False, "error": str(e)[:200],
                    })
                    await _msg(
                        ctx.inspector_session_id, "system",
                        f"⚠️ click روی «{selector_hint}» fail: {str(e)[:150]}",
                    )

        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass
            pool.touch()

        finished_at_dt = datetime.now(timezone.utc)

        # ---- backend logs ----
        backend_summary, _backend_raw = await _fetch_backend_logs_window(
            ctx, started_at_dt, finished_at_dt,
        )
        if backend_summary and ctx.inspector_session_id:
            await _msg(
                ctx.inspector_session_id, "system",
                f"📋 backend logs: {backend_summary}",
            )

        # ---- vision analysis (سکمنت سکمنت) ----
        for shot in screenshots:
            if not shot.get("path"):
                continue
            try:
                from .vision_helper import analyze_screenshot
                vctx = {
                    "url": final_url,
                    "ac_text": ac_text,
                    "console_logs": console_errors,
                    "backend_logs": [{"level": "info", "message": backend_summary}] if backend_summary else [],
                    "html_excerpt": html_excerpt,
                }
                vres = await analyze_screenshot(
                    shot["path"], vctx, verify_model_id=ctx.verify_model_id,
                )
                shot["vision_description"] = (vres.get("description") or "")[:2000]
                shot["vision_source"] = vres.get("source") or "none"
                # 🆕 (Phase 2 fix 3) — feature_present تشخیص بصری
                shot["vision_feature_present"] = (vres.get("feature_present") or "unclear")
                shot["vision_feature_reason"] = (vres.get("feature_reason") or "")[:600]
                # خلاصه‌ای در session
                if shot["vision_description"]:
                    fp = shot["vision_feature_present"]
                    fp_emoji = {"yes": "✅", "no": "❌", "unclear": "❓"}.get(fp, "❓")
                    fp_line = (
                        f" — feature_present: {fp_emoji} {fp}"
                        if fp != "unclear" else ""
                    )
                    await _msg(
                        ctx.inspector_session_id, "system",
                        f"🔍 vision ({shot['label']}){fp_line}: "
                        f"{shot['vision_description'][:300]}",
                    )
            except Exception as e:
                logger.debug(f"inspector_probe vision failed: {e}")
                shot["vision_description"] = ""
                shot["vision_source"] = "none"
                shot["vision_feature_present"] = "unclear"
                shot["vision_feature_reason"] = ""

        # ---- pass/fail decision ----
        has_console_error = any(c.get("level") == "error" for c in console_errors)
        nav_ok = bool(actions_taken) and actions_taken[0].get("success", False)
        # if there's a selector_hint, it must be found
        selector_ok = (selector_hint is None) or selector_found

        # 🆕 (Phase 2 fix 3) — اگر vision قطعاً گفت feature_present="no"،
        # probe باید FAILED شود (حتی اگر navigate ok بود + console error
        # نبود). این مهم‌ترین سیگنال برای تشخیص feature که هنوز ساخته
        # نشده است.
        vision_says_feature_missing = False
        vision_missing_reason = ""
        for _shot in screenshots:
            if (_shot.get("vision_feature_present") or "").lower() == "no":
                vision_says_feature_missing = True
                vision_missing_reason = _shot.get("vision_feature_reason") or "vision AI: feature not visible"
                break

        passed = (
            nav_ok
            and (not has_console_error)
            and selector_ok
            and (not vision_says_feature_missing)
        )
        status = PROBE_STATUS_PASSED if passed else PROBE_STATUS_FAILED
        emoji = "✅" if passed else "❌"
        await _msg(
            ctx.inspector_session_id, "system",
            f"{emoji} probe {status}"
            + (f" — feature missing: {vision_missing_reason[:200]}"
               if vision_says_feature_missing else ""),
        )

        assertion_results: List[Dict[str, Any]] = [
            {"expectation": "navigate successful", "met": nav_ok,
             "reason": f"status={actions_taken[0].get('status') if actions_taken else 'n/a'}"},
            {"expectation": "no console errors", "met": (not has_console_error),
             "reason": f"{sum(1 for c in console_errors if c.get('level') == 'error')} errors"},
        ]
        # 🆕 (Phase 2 fix 3) — assertion vision feature_present
        if vision_says_feature_missing:
            assertion_results.append({
                "expectation": f"feature «{ac_text[:80]}» در صفحه دیده شود",
                "met": False,
                "reason": vision_missing_reason[:300],
            })
        if selector_hint:
            assertion_results.append({
                "expectation": f"selector «{selector_hint}» found",
                "met": selector_ok,
                "reason": "" if selector_ok else "selector not visible",
            })

        # 🆕 (Phase 2) — جدا کردن URL های بک‌اند که فرانت در حین لود زد
        backend_root = (ctx.backend_base_url or "").rstrip("/")
        backend_urls_called: List[Dict[str, Any]] = [
            {"url": n.get("url"), "method": n.get("method"),
             "status": n.get("status")}
            for n in network_calls
            if backend_root and (n.get("url") or "").startswith(backend_root)
        ]
        if backend_urls_called and ctx.inspector_session_id:
            _be_count = len(backend_urls_called)
            _be_sample = ", ".join(
                f"{b.get('method')} {(b.get('url') or '').split(backend_root, 1)[-1][:40]}→{b.get('status')}"
                for b in backend_urls_called[:3]
            )
            try:
                await _msg(
                    ctx.inspector_session_id, "system",
                    f"🌐 {_be_count} درخواست backend ثبت شد — نمونه: {_be_sample}",
                )
            except Exception:
                pass

        return RuntimeProbeResult(
            ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
            status=status,
            evidence={
                "inspector_session_id": ctx.inspector_session_id,
                "actions_taken": actions_taken,
                "screenshots": screenshots,
                "console_errors": console_errors,
                "network_calls": network_calls,
                "backend_urls_called": backend_urls_called,
                "backend_log_summary": backend_summary,
                "final_url": final_url,
                "assertion_results": assertion_results,
                "probe_type": "inspector_phase1",
            },
            duration_ms=int((time.monotonic() - start_mono) * 1000),
        )

    except Exception as e:
        logger.warning(f"inspector_probe inner crashed: {e}", exc_info=False)
        await _msg(
            ctx.inspector_session_id, "system",
            f"💥 probe inner crash: {str(e)[:200]}",
        )
        _nc = locals().get("network_calls") or []
        return RuntimeProbeResult(
            ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
            status=PROBE_STATUS_ERROR,
            evidence={
                "reason": f"playwright crash: {e}",
                "inspector_session_id": ctx.inspector_session_id,
                "actions_taken": actions_taken,
                "screenshots": screenshots,
                "console_errors": console_errors,
                "network_calls": _nc,
            },
            duration_ms=int((time.monotonic() - start_mono) * 1000),
            error_message=str(e)[:300],
        )


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

async def _take_and_record_screenshot(
    page: Any,
    shot_dir: Optional[Path],
    label: str,
    screenshots: List[Dict[str, Any]],
    actions_taken: List[Dict[str, Any]],
    ctx: ProbeContext,
) -> Optional[str]:
    if not shot_dir or len(screenshots) >= _MAX_SCREENSHOTS:
        return None
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
    fname = f"{safe_label}_{int(time.time() * 1000)}.png"
    fpath = shot_dir / fname
    try:
        await page.screenshot(
            path=str(fpath), full_page=False, type="png",
        )
        # cap size
        try:
            sz = fpath.stat().st_size
        except Exception:
            sz = 0
        if sz > _MAX_SCREENSHOT_BYTES:
            # دوباره با کیفیت کمتر
            try:
                fpath.unlink(missing_ok=True)
                fpath = shot_dir / (safe_label + "_" + str(int(time.time() * 1000)) + ".jpg")
                await page.screenshot(
                    path=str(fpath), full_page=False, type="jpeg", quality=70,
                )
            except Exception:
                pass
        screenshots.append({
            "path": str(fpath),
            "label": label,
            "vision_description": "",
            "vision_source": None,
            "vision_feature_present": "unclear",
            "vision_feature_reason": "",
            "archived_to_telegram": False,
        })
        actions_taken.append({
            "action": "screenshot", "label": label,
            "duration_ms": 0, "success": True,
        })
        if ctx.inspector_session_id:
            try:
                await _msg(
                    ctx.inspector_session_id, "system",
                    f"📸 screenshot گرفته شد: {label}",
                    extra_data={"screenshot_path": str(fpath), "label": label},
                )
            except Exception:
                pass
        return str(fpath)
    except Exception as e:
        logger.debug(f"inspector_probe screenshot failed: {e}")
        return None


def _skipped(ac_id: str, ac_text: str, reason: str, start_mono: float) -> RuntimeProbeResult:
    return RuntimeProbeResult(
        ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
        status=PROBE_STATUS_SKIPPED,
        evidence={"reason": reason, "probe_type": "inspector_phase1"},
        duration_ms=int((time.monotonic() - start_mono) * 1000),
    )


def _build_result_after_failure(
    ac_id: str, ac_text: str, ctx: ProbeContext, start_mono: float,
    actions: List[Dict[str, Any]], screenshots: List[Dict[str, Any]],
    console_errors: List[Dict[str, Any]], reason: str,
    html_excerpt: str, final_url: str,
    network_calls: Optional[List[Dict[str, Any]]] = None,
) -> RuntimeProbeResult:
    evid: Dict[str, Any] = {
        "inspector_session_id": ctx.inspector_session_id,
        "actions_taken": actions,
        "screenshots": screenshots,
        "console_errors": console_errors,
        "final_url": final_url,
        "reason": reason,
        "probe_type": "inspector_phase1",
    }
    if network_calls is not None:
        evid["network_calls"] = network_calls
        backend_root = (ctx.backend_base_url or "").rstrip("/")
        evid["backend_urls_called"] = [
            {"url": n.get("url"), "method": n.get("method"),
             "status": n.get("status")}
            for n in network_calls
            if backend_root and (n.get("url") or "").startswith(backend_root)
        ]
    return RuntimeProbeResult(
        ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
        status=PROBE_STATUS_FAILED,
        evidence=evid,
        duration_ms=int((time.monotonic() - start_mono) * 1000),
        error_message=reason,
    )
