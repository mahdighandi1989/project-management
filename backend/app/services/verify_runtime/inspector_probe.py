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

# محدودیت Phase 3
_TIMEOUT_S = 90  # افزایش از ۶۰ به ۹۰ برای recipe طولانی
_MAX_SCREENSHOTS = 5  # افزایش از ۲ — interaction های پیچیده
_MAX_SCREENSHOT_BYTES = 500_000  # ~500KB
_MAX_CONSOLE_LOGS = 50
# 🆕 (Phase 2) محدودیت ضبط network requests
_MAX_NETWORK_CALLS = 30
_STATIC_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".otf",
    ".css", ".js", ".mjs", ".map", ".ico",
)
# 🆕 (Phase 3) — action loop
_MAX_UI_STEPS = 12  # حداکثر step در هر probe
_DEFAULT_STEP_TIMEOUT_MS = 5000

# action های مجاز در ui_steps
_SUPPORTED_ACTIONS = frozenset({
    "navigate", "click", "fill", "submit", "select",
    "check", "uncheck", "hover", "wait_for", "wait_for_url",
    "wait_for_load", "screenshot", "scroll_to", "press_key",
    "assert_visible", "assert_text", "assert_url",
})


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
            # 🆕 (Phase 3) — اگر ctx.storage_state داریم، در new_context اعمال
            # کن تا probe به صفحات با لاگین دسترسی داشته باشد.
            _ctx_kwargs: Dict[str, Any] = {"viewport": {"width": 1280, "height": 800}}
            if isinstance(ctx.storage_state, dict) and ctx.storage_state:
                _ctx_kwargs["storage_state"] = ctx.storage_state
            context = await browser.new_context(**_ctx_kwargs)
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

            # 🔐 (Phase 3) — Login redirect detection
            # اگر صفحه به /login redirect خورد (و هدف تسک خود login نبود)،
            # علامت‌گذاری کن. اگر storage_state داشتیم ولی auth منقضی شده، این
            # هم گرفته می‌شود.
            auth_required = False
            try:
                _final_lower = (final_url or "").lower()
                _orig_lower = (full_url or "").lower()
                _login_paths = ("/login", "/signin", "/sign-in", "/auth/login", "/auth/signin")
                if any(p in _final_lower for p in _login_paths) and not any(
                    p in _orig_lower for p in _login_paths
                ):
                    auth_required = True
            except Exception:
                pass

            # screenshot 1 (after_navigate)
            shot1 = await _take_and_record_screenshot(
                page, shot_dir, "after_navigate", screenshots, actions_taken, ctx,
            )

            # capture HTML excerpt (for vision fallback)
            try:
                html_excerpt = (await page.content())[:5000]
            except Exception:
                html_excerpt = ""

            # 🆕 (Phase 3 fix) — تشخیص SPA-404 از محتوای صفحه (status=200 ولی
            # محتوا "Not Found"). نشانه‌های 404:
            #  - متن "Not Found" یا "404" در body
            #  - متن کوتاه (<500 char) با hint اخطار
            spa_404_detected = False
            try:
                _body_low = (html_excerpt or "").lower()
                _markers_404 = (
                    "not found", "404 ", " 404\b", "page not found",
                    "صفحه پیدا نشد", "صفحه یافت نشد", "یافت نشد",
                )
                # اگر body شامل یکی از markers ـه و کوتاه‌ـه (نشان از 404 page minimal)
                if any(m in _body_low for m in _markers_404):
                    # double-check: محتوای main page باید معمولاً > 2000 char باشد
                    _stripped_len = len(_body_low.strip())
                    if _stripped_len < 3000:
                        spa_404_detected = True
            except Exception:
                pass

            # 🆕 (Phase 4 fix) — HTTP 4xx/5xx response هم باید vision را
            # skip کند. Vision روی صفحه‌ی واقعی 404/500 محتوای ساختگی
            # می‌سازد که کلمات AC را در آن fake می‌کند.
            http_error_detected = False
            try:
                if isinstance(nav_status, int) and nav_status >= 400:
                    http_error_detected = True
            except Exception:
                pass

            # یک flag مشترک برای skip شدن vision در هر دو حالت
            page_unusable = spa_404_detected or http_error_detected

            if http_error_detected and not spa_404_detected:
                # nav_ok را false کن (احتمالاً قبلاً false بود ولی تأکید)
                nav_ok = False
                if ctx.inspector_session_id:
                    try:
                        await _msg(
                            ctx.inspector_session_id, "system",
                            f"⚠️ HTTP error detected: status={nav_status} "
                            f"— probe FAIL، vision skip می‌شود ({full_url[:120]})",
                        )
                    except Exception:
                        pass

            if spa_404_detected:
                # nav_ok را به false تنظیم کن تا probe failed باشد
                nav_ok = False
                # یک پیام در session
                if ctx.inspector_session_id:
                    try:
                        await _msg(
                            ctx.inspector_session_id, "system",
                            f"⚠️ SPA-404 detected: page returned 200 but body indicates 'Not Found' "
                            f"({full_url[:120]})",
                        )
                    except Exception:
                        pass

            # 🆕 (Phase 3) — action loop: اگر verify_plan.ui_steps شامل بیش از
            # یک step غیر-navigate است، sequence را اجرا کن (interaction واقعی).
            # navigate قبلاً انجام شده، پس step های navigate در sequence skip
            # می‌شوند مگر URL متفاوت داشته باشند.
            extra_steps_executed = False
            backend_root_for_probe = (ctx.backend_base_url or "").rstrip("/")
            plan_steps_raw = plan.get("ui_steps") or []
            # تنها step های non-navigate یا step های navigate با URL متفاوت
            executable_steps: List[Dict[str, Any]] = []
            if isinstance(plan_steps_raw, list):
                for _s in plan_steps_raw[:_MAX_UI_STEPS]:
                    if not isinstance(_s, dict):
                        continue
                    _act = str(_s.get("action") or "").lower()
                    if _act == "navigate":
                        # اولین navigate قبلاً انجام شده — skip تا navigate دوگانه نداشته باشیم
                        continue
                    if _act:
                        executable_steps.append(_s)

            if executable_steps:
                extra_steps_executed = True
                if ctx.inspector_session_id:
                    try:
                        await _msg(
                            ctx.inspector_session_id, "system",
                            f"🎬 اجرای sequence ({len(executable_steps)} مرحله)",
                        )
                    except Exception:
                        pass
                for _step_idx, _step in enumerate(executable_steps, start=1):
                    _step_result = await _execute_ui_step(
                        page, _step, _step_idx, shot_dir,
                        screenshots, ctx, backend_root_for_probe,
                    )
                    actions_taken.append(_step_result)
                    # log به session
                    if ctx.inspector_session_id:
                        _emoji = "✅" if _step_result.get("success") else "❌"
                        try:
                            await _msg(
                                ctx.inspector_session_id, "action",
                                f"{_emoji} step {_step_idx}: {_step_result.get('message', '')}",
                                action_type=_step_result.get("action"),
                            )
                        except Exception:
                            pass
                    # اگر step ای fail شد، sequence را متوقف کن (مگر assert_*)
                    if (not _step_result.get("success")
                            and not _step_result["action"].startswith("assert_")):
                        break
                # update final_url پس از sequence
                try:
                    final_url = page.url or final_url
                except Exception:
                    pass

            # ---- click (در صورت وجود selector_hint و در صورت نبود extra_steps) ----
            selector_found = True  # default if no hint
            # اگر sequence اجرا شد، single-click قدیمی را skip کن
            if selector_hint and not extra_steps_executed:
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
            # 🆕 (Phase 4 fix) — اگر صفحه قابل استفاده نیست (SPA-404 یا
            # HTTP 4xx/5xx)، vision را اصلاً صدا نزن — vision معمولاً
            # از روی URL/title hallucinate می‌کند و feature_present=yes
            # برمی‌گرداند با محتوای ساختگی که حتی کلمات AC را در OCR
            # fake می‌کند. به‌جای آن، مستقیماً feature_present=no با
            # reason صریح ست می‌کنیم.
            if page_unusable:
                _err_label = (
                    f"HTTP {nav_status}" if http_error_detected else "SPA-404"
                )
                shot["vision_description"] = (
                    f"(صفحه قابل استفاده نیست — {_err_label}؛ "
                    "Vision صدا زده نشد تا hallucination رخ ندهد)"
                )
                shot["vision_source"] = (
                    "skipped_http_error" if http_error_detected else "skipped_spa_404"
                )
                shot["vision_feature_present"] = "no"
                shot["vision_feature_reason"] = (
                    f"page returned {_err_label} — feature can't be present"
                )
                try:
                    await _msg(
                        ctx.inspector_session_id, "system",
                        f"🚫 vision ({shot['label']}) skipped — {_err_label}",
                    )
                except Exception:
                    pass
                continue
            try:
                from .vision_helper import analyze_screenshot
                # 🆕 (Phase 4 fix) — prefix `(step probe #N)` و
                # `(auto-verify system probe)` فقط برای logging هستند —
                # حذفشان قبل از پاس به vision تا AI روی scope واقعی AC
                # تمرکز کند، نه روی تگ‌های داخلی engine.
                import re as _re_clean
                _clean_ac = _re_clean.sub(
                    r"^\(\s*(step probe #\d+|auto-verify system probe)\s*\)\s*",
                    "",
                    ac_text or "",
                ).strip()
                vctx = {
                    "url": final_url,
                    "ac_text": _clean_ac,
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
        # 🆕 (Phase 3 fix) — system probe (ac_id="system_home") AC متادیتایی
        # دارد، نه چیزی که روی صفحه دیده شود ("صفحه اصلی deployed قابل
        # دسترسی است"). vision نباید آن متن را روی UI جست‌وجو کند. برای
        # system probe، feature_present check را skip می‌کنیم — فقط
        # nav_ok و console errors ملاک هستند.
        is_system_probe_local = (ac_id == "system_home")
        vision_says_feature_missing = False
        vision_missing_reason = ""
        # 🆕 (Phase 4 fix) — fail-safe: اگر vision نتوانست feature_present
        # تشخیص دهد (parse failure → ست به "" یا "unclear")، probe باید
        # احتیاط کند و pass نگیرد. از این flag در passed_initial استفاده
        # می‌کنیم تا نسبت به سکوت Vision امن باشیم.
        vision_inconclusive = False
        if not is_system_probe_local:
            _has_any_vision_yes = False
            _all_inconclusive = True if screenshots else False
            for _shot in screenshots:
                if not _shot.get("path"):
                    continue
                _fp = (_shot.get("vision_feature_present") or "").lower()
                if _fp == "no":
                    vision_says_feature_missing = True
                    vision_missing_reason = (
                        _shot.get("vision_feature_reason")
                        or "vision AI: feature not visible"
                    )
                    break
                if _fp == "yes":
                    _has_any_vision_yes = True
                    _all_inconclusive = False
                elif _fp in ("", "unclear"):
                    # هیچ اطلاع قطعی نیست — ادامه می‌دهیم ولی flag فعال
                    pass
                else:
                    _all_inconclusive = False
            # اگر هیچ shot ای yes نگفت و همگی فقط empty/unclear هستند،
            # vision را "بی‌نتیجه" در نظر بگیر — probe باید fail-safe بدهد
            if (not vision_says_feature_missing
                    and not _has_any_vision_yes
                    and _all_inconclusive
                    and screenshots):
                vision_inconclusive = True
                vision_missing_reason = (
                    "vision AI: feature_present تشخیص داده نشد "
                    "(parse failure یا response ناقص) — fail-safe به FAIL"
                )

        # 🔢 (Phase 3) — passed نهایی بعد از vision_pair و expected_api_calls
        # محاسبه می‌شود (پایین‌تر در کد). فعلاً initial passed برای assertion ها.
        passed_initial = (
            nav_ok
            and (not has_console_error)
            and selector_ok
            and (not vision_says_feature_missing)
            and (not vision_inconclusive)
            and (not auth_required)
        )

        assertion_results: List[Dict[str, Any]] = [
            {"expectation": "navigate successful", "met": nav_ok,
             "reason": f"status={actions_taken[0].get('status') if actions_taken else 'n/a'}"},
            {"expectation": "no console errors", "met": (not has_console_error),
             "reason": f"{sum(1 for c in console_errors if c.get('level') == 'error')} errors"},
        ]
        # 🆕 (Phase 3) — vision pair analysis اگر ≥۲ screenshot داریم
        # و sequence اجرا شده (یعنی interaction واقعی بود)
        vision_pair_result: Optional[Dict[str, Any]] = None
        try:
            if extra_steps_executed and len(screenshots) >= 2:
                # اولین و آخرین screenshot معتبر را به‌عنوان before/after بگیر
                _valid_shots = [s for s in screenshots if s.get("path")]
                if len(_valid_shots) >= 2:
                    _before = _valid_shots[0]
                    _after = _valid_shots[-1]
                    from .vision_helper import analyze_screenshot_pair
                    # 🆕 (Phase 4 fix) — همان sanitize برای vision pair
                    import re as _re_clean2
                    _clean_ac_pair = _re_clean2.sub(
                        r"^\(\s*(step probe #\d+|auto-verify system probe)\s*\)\s*",
                        "",
                        ac_text or "",
                    ).strip()
                    vision_pair_result = await analyze_screenshot_pair(
                        _before["path"], _after["path"],
                        {
                            "ac_text": _clean_ac_pair,
                            "actions_taken": actions_taken,
                        },
                    )
                    if vision_pair_result and ctx.inspector_session_id:
                        try:
                            _diff = vision_pair_result.get("diff_description") or ""
                            _suc = vision_pair_result.get("interaction_succeeded") or "unclear"
                            _fp = vision_pair_result.get("feature_present") or "unclear"
                            await _msg(
                                ctx.inspector_session_id, "system",
                                f"🔬 vision pair: interaction={_suc}, "
                                f"feature_present={_fp} — {_diff[:200]}",
                            )
                        except Exception:
                            pass
        except Exception as _vpe:
            logger.debug(f"inspector_probe vision pair failed: {_vpe}")

        # 🆕 (Phase 3) — expected_api_calls assertion
        expected_api_calls_results: List[Dict[str, Any]] = []
        try:
            expected = plan.get("expected_api_calls") or []
            if isinstance(expected, list) and expected:
                for exp in expected:
                    if not isinstance(exp, dict):
                        continue
                    exp_method = str(exp.get("method") or "GET").upper()
                    exp_path = str(exp.get("path_contains") or "").strip()
                    if not exp_path:
                        continue
                    matched = any(
                        str(c.get("method") or "").upper() == exp_method
                        and exp_path in str(c.get("url") or "")
                        for c in network_calls
                    )
                    expected_api_calls_results.append({
                        "expectation": f"API call {exp_method} {exp_path}",
                        "met": matched,
                        "reason": "ثبت شد" if matched else "ثبت نشد",
                    })
        except Exception as _eae:
            logger.debug(f"inspector_probe expected_api_calls failed: {_eae}")

        # اگر expected_api_calls فیلد داشت و حداقل یکی نشد → احتمالاً feature
        # واقعی کار نکرده — این علاوه بر vision یک signal دیگر است
        api_calls_failed = bool(expected_api_calls_results) and any(
            not r.get("met") for r in expected_api_calls_results
        )

        # vision_pair interaction signal
        vision_pair_interaction_failed = bool(
            vision_pair_result
            and vision_pair_result.get("interaction_succeeded") == "no"
        )

        # assertion ها از vision_pair و expected_api_calls
        if vision_pair_result and vision_pair_result.get("interaction_succeeded") != "unclear":
            _ok = vision_pair_result.get("interaction_succeeded") == "yes"
            assertion_results.append({
                "expectation": "interaction قابل مشاهده‌ای انجام شد",
                "met": _ok,
                "reason": vision_pair_result.get("diff_description", "")[:300],
            })
        assertion_results.extend(expected_api_calls_results)

        # 🆕 passed نهایی Phase 3
        passed = (
            passed_initial
            and not vision_pair_interaction_failed
            and not api_calls_failed
        )
        status = PROBE_STATUS_PASSED if passed else PROBE_STATUS_FAILED
        emoji = "✅" if passed else "❌"
        # علت اولویت‌دار برای پیام session
        _why_failed = ""
        if vision_says_feature_missing:
            _why_failed = f" — feature missing: {vision_missing_reason[:200]}"
        elif auth_required:
            _why_failed = " — redirect به login (auth recipe لازم است)"
        elif vision_pair_interaction_failed:
            _why_failed = f" — interaction انجام نشد: {(vision_pair_result or {}).get('diff_description', '')[:200]}"
        elif api_calls_failed:
            _missed = [r for r in expected_api_calls_results if not r.get('met')]
            _why_failed = f" — {len(_missed)} API call مورد انتظار ثبت نشد"
        await _msg(
            ctx.inspector_session_id, "system",
            f"{emoji} probe {status}{_why_failed}",
        )

        # 🆕 (Phase 2 fix 3) — assertion vision feature_present
        if vision_says_feature_missing:
            assertion_results.append({
                "expectation": f"feature «{ac_text[:80]}» در صفحه دیده شود",
                "met": False,
                "reason": vision_missing_reason[:300],
            })
        # 🔐 (Phase 3) — login redirect assertion
        if auth_required:
            _auth_state_label = (
                "valid" if ctx.storage_state else
                ("none" if not getattr(ctx, "storage_state", None) else "expired")
            )
            assertion_results.append({
                "expectation": "صفحه‌ی هدف بدون redirect به login باز شود",
                "met": False,
                "reason": (
                    f"redirect به {final_url[:120]} — auth_state={_auth_state_label}"
                    f"؛ احتمالاً runtime_auth_recipe لازم است"
                ),
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
                # 🆕 (Phase 3) — vision pair + expected_api_calls
                "vision_pair": vision_pair_result,
                "expected_api_calls_results": expected_api_calls_results,
                # 🔐 (Phase 3) — auth state
                "auth_required": auth_required,
                "auth_state": (
                    "valid" if (ctx.storage_state and not auth_required) else
                    ("expired" if (ctx.storage_state and auth_required) else
                     ("failed" if auth_required else "none"))
                ),
                "probe_type": "inspector_phase3",
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


# ---------------------------------------------------------------------------
# 🆕 (Phase 3) — action loop helper
# ---------------------------------------------------------------------------

async def _execute_ui_step(
    page: Any,
    step: Dict[str, Any],
    step_idx: int,
    shot_dir: Optional[Path],
    screenshots: List[Dict[str, Any]],
    ctx: ProbeContext,
    backend_root: str,
) -> Dict[str, Any]:
    """اجرای یک ui_step و برگرداندن نتیجه ساختاریافته.

    Returns:
      {
        step_idx, action, selector, value,
        success, duration_ms, message, error, screenshot_label
      }
    """
    start = time.monotonic()
    action = str(step.get("action") or "").strip().lower()
    selector = step.get("selector")
    value = step.get("value")
    timeout_ms = int(step.get("timeout_ms") or _DEFAULT_STEP_TIMEOUT_MS)

    result: Dict[str, Any] = {
        "step_idx": step_idx,
        "action": action,
        "selector": selector,
        "value": value if action != "fill" else "***",  # mask values
        "success": False,
        "duration_ms": 0,
        "message": "",
        "error": None,
        "screenshot_label": None,
    }

    if action not in _SUPPORTED_ACTIONS:
        result["error"] = f"unknown action: {action}"
        result["message"] = "action skipped"
        return result

    try:
        if action == "navigate":
            url = step.get("url") or "/"
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"navigated to {url}"
        elif action == "click":
            if not selector:
                result["error"] = "selector required"
                return result
            await page.locator(selector).first.click(timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"clicked {selector}"
        elif action == "fill":
            if not selector:
                result["error"] = "selector required"
                return result
            await page.locator(selector).first.fill(str(value or ""), timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"filled {selector}"
        elif action == "submit":
            # selector می‌تواند یک form یا یک button[type=submit] باشد
            if selector:
                try:
                    await page.locator(selector).first.click(timeout=timeout_ms)
                except Exception:
                    await page.locator(selector).first.press("Enter", timeout=timeout_ms)
                result["success"] = True
                result["message"] = f"submitted via {selector}"
            else:
                result["error"] = "selector required"
                return result
        elif action == "select":
            if not selector:
                result["error"] = "selector required"
                return result
            await page.select_option(selector, str(value or ""), timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"selected {value} in {selector}"
        elif action == "check":
            await page.check(selector, timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"checked {selector}"
        elif action == "uncheck":
            await page.uncheck(selector, timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"unchecked {selector}"
        elif action == "hover":
            await page.hover(selector, timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"hovered {selector}"
        elif action == "wait_for":
            state = step.get("state", "visible")
            await page.wait_for_selector(selector, timeout=timeout_ms, state=state)
            result["success"] = True
            result["message"] = f"wait_for {selector} ({state})"
        elif action == "wait_for_url":
            contains = step.get("contains") or step.get("pattern") or ""
            # Playwright wait_for_url می‌خواهد یا callable یا regex یا exact url
            try:
                await page.wait_for_url(f"**{contains}**", timeout=timeout_ms)
            except Exception:
                # fallback: poll page.url
                deadline = time.monotonic() + (timeout_ms / 1000.0)
                while time.monotonic() < deadline:
                    if contains in (page.url or ""):
                        break
                    await asyncio.sleep(0.2)
                if contains not in (page.url or ""):
                    raise
            result["success"] = True
            result["message"] = f"url now contains '{contains}'"
        elif action == "wait_for_load":
            state = step.get("state", "networkidle")
            await page.wait_for_load_state(state, timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"wait_for_load_state({state})"
        elif action == "screenshot":
            label = str(step.get("label") or f"step_{step_idx}")
            path = await _take_and_record_screenshot(
                page, shot_dir, label, screenshots, [], ctx,
            )
            result["success"] = path is not None
            result["screenshot_label"] = label
            result["message"] = f"screenshot {label}"
        elif action == "scroll_to":
            await page.locator(selector).first.scroll_into_view_if_needed(timeout=timeout_ms)
            result["success"] = True
            result["message"] = f"scrolled to {selector}"
        elif action == "press_key":
            key = str(step.get("key") or "Enter")
            await page.keyboard.press(key)
            result["success"] = True
            result["message"] = f"pressed {key}"
        elif action == "assert_visible":
            visible = await page.locator(selector).first.is_visible(timeout=timeout_ms)
            result["success"] = bool(visible)
            result["message"] = f"assert_visible {selector} = {visible}"
            if not visible:
                result["error"] = "not visible"
        elif action == "assert_text":
            text = await page.locator(selector).first.text_content(timeout=timeout_ms)
            contains = str(step.get("contains") or "")
            ok = bool(text and contains and contains in text)
            result["success"] = ok
            result["message"] = f"assert_text {selector} contains '{contains}' = {ok}"
            if not ok:
                result["error"] = f"text mismatch (got: {(text or '')[:80]})"
        elif action == "assert_url":
            contains = str(step.get("contains") or "")
            current = page.url or ""
            ok = contains in current
            result["success"] = ok
            result["message"] = f"assert_url contains '{contains}' = {ok}"
            if not ok:
                result["error"] = f"url mismatch ({current})"
    except Exception as e:
        result["error"] = str(e)[:300]
        result["message"] = f"{action} failed: {result['error']}"
        # screenshot on failure (best-effort)
        try:
            fail_label = f"step_{step_idx}_fail_{action}"
            await _take_and_record_screenshot(
                page, shot_dir, fail_label, screenshots, [], ctx,
            )
            result["screenshot_label"] = fail_label
        except Exception:
            pass

    result["duration_ms"] = int((time.monotonic() - start) * 1000)
    return result


def _skipped(ac_id: str, ac_text: str, reason: str, start_mono: float) -> RuntimeProbeResult:
    return RuntimeProbeResult(
        ac_id=ac_id, ac_text=ac_text, method="ui_interaction",
        status=PROBE_STATUS_SKIPPED,
        evidence={"reason": reason, "probe_type": "inspector_phase3"},
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
        "probe_type": "inspector_phase3",
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
