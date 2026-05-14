"""Phase 5 — Runtime Discovery (R14 + ایده از Phase 4).

با استفاده از Phase 4 components، state واقعی دیپلوی‌شده را کشف می‌کند:
  - Playwright + navigation_helper → nav links واقعی
  - Playwright screenshot on each route → 404 detection
  - backend_log_probe → endpoints called recently
  - vision_helper → کشف feature های UI

خروجی → runtime_state که در فاز ۲ (stale) و ۵ (logic audit) استفاده می‌شود.

API:
    discover_runtime_state(frontend_base_url, backend_base_url,
                          inventory, storage_state, scan_session_id,
                          verify_model_id) -> runtime_state dict
"""

from __future__ import annotations

import asyncio
import logging
import time as _time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_MAX_ROUTES_TO_VISIT = 8  # محدودیت — زمان scan افزایش می‌دهد
_PER_ROUTE_TIMEOUT_S = 15


async def discover_runtime_state(
    frontend_base_url: Optional[str],
    backend_base_url: Optional[str],
    inventory: Dict[str, Any],
    storage_state: Optional[Dict[str, Any]] = None,
    scan_session_id: Optional[int] = None,
    screenshot_dir: Optional[str] = None,
    verify_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """جمع‌آوری runtime_state از Playwright + Render logs.

    Returns:
        {
            "routes_alive": [...],
            "routes_404": [...],
            "endpoints_called_recently": [...],
            "endpoints_never_called": [...],
            "ui_features_visible": [...],
            "screenshots": [...],
            "duration_ms": int,
        }
    """
    start = _time.monotonic()
    runtime_state: Dict[str, Any] = {
        "routes_alive": [],
        "routes_404": [],
        "endpoints_called_recently": [],
        "endpoints_never_called": [],
        "ui_features_visible": [],
        "screenshots": [],
        "duration_ms": 0,
        "_meta": {"frontend_visited": False, "logs_fetched": False},
    }

    # log to scan session
    def _log_session(role: str, content: str):
        if scan_session_id:
            try:
                from .scan_inspector_session import log_scan_message
                log_scan_message(scan_session_id, role=role, content=content)
            except Exception:
                pass

    # ── 1) Frontend route discovery via Playwright ──
    if frontend_base_url:
        try:
            _log_session(
                "system",
                f"🧭 شروع runtime_discovery روی {frontend_base_url}",
            )
            from ..verify_runtime.browser_pool import get_browser_pool
            from ..verify_runtime.navigation_helper import extract_nav_links_from_page
            pool = get_browser_pool()
            browser = await pool.get_browser()
            if browser is None:
                _log_session("system", "⚠️ browser pool unavailable")
            else:
                _ctx_kwargs: Dict[str, Any] = {"viewport": {"width": 1280, "height": 800}}
                if isinstance(storage_state, dict) and storage_state:
                    _ctx_kwargs["storage_state"] = storage_state
                context = await browser.new_context(**_ctx_kwargs)
                page = await context.new_page()
                page.set_default_timeout(_PER_ROUTE_TIMEOUT_S * 1000)

                # کاندیداهای route — از inventory + nav
                candidate_routes: List[str] = []
                inv_routes = (inventory.get("routes") or {}).get("frontend") or []
                candidate_routes.extend([r for r in inv_routes if not r.startswith(":")][:_MAX_ROUTES_TO_VISIT])
                # محدود به MAX
                candidate_routes = list(dict.fromkeys(candidate_routes))[:_MAX_ROUTES_TO_VISIT]

                # ابتدا home برای nav menu
                try:
                    await asyncio.wait_for(
                        page.goto(frontend_base_url, wait_until="domcontentloaded"),
                        timeout=_PER_ROUTE_TIMEOUT_S,
                    )
                    nav_links = await extract_nav_links_from_page(page)
                    _log_session(
                        "system",
                        f"🧭 nav menu: {len(nav_links)} link پیدا شد",
                    )
                    # add nav links به candidates
                    for link in nav_links:
                        href = (link.get("href") or "").split("?")[0].rstrip("/")
                        if href and href not in candidate_routes:
                            candidate_routes.append(href)
                    candidate_routes = candidate_routes[:_MAX_ROUTES_TO_VISIT]
                except Exception as e:
                    _log_session("system", f"⚠️ home navigation failed: {e}")

                # visit each route + screenshot
                shot_idx = 0
                base_clean = frontend_base_url.rstrip("/")
                for route in candidate_routes:
                    if not route:
                        continue
                    full_url = (
                        route if route.startswith("http")
                        else base_clean + (route if route.startswith("/") else "/" + route)
                    )
                    try:
                        resp = await asyncio.wait_for(
                            page.goto(full_url, wait_until="domcontentloaded"),
                            timeout=_PER_ROUTE_TIMEOUT_S,
                        )
                        status = getattr(resp, "status", 0) if resp else 0
                        # SPA-404 check
                        body = (await page.content())[:3000].lower()
                        is_404 = (
                            status >= 400
                            or ("not found" in body and len(body) < 3000)
                        )
                        # screenshot
                        shot_path = None
                        if screenshot_dir:
                            try:
                                shot_idx += 1
                                shot_p = Path(screenshot_dir) / f"runtime_{shot_idx}_{route.strip('/').replace('/', '_') or 'root'}.png"
                                shot_p.parent.mkdir(parents=True, exist_ok=True)
                                await page.screenshot(path=str(shot_p), full_page=False)
                                shot_path = str(shot_p)
                                runtime_state["screenshots"].append({
                                    "route": route, "status": status,
                                    "path": shot_path, "is_404": is_404,
                                })
                            except Exception as _se:
                                logger.debug(f"screenshot fail: {_se}")
                        if is_404:
                            runtime_state["routes_404"].append({
                                "route": route, "url": full_url, "status": status,
                            })
                            _log_session(
                                "action",
                                f"❌ {route} → {status} (404 detected)",
                            )
                        else:
                            runtime_state["routes_alive"].append({
                                "route": route, "url": full_url, "status": status,
                            })
                            _log_session(
                                "action",
                                f"✅ {route} → {status} alive",
                            )
                    except Exception as e:
                        _log_session(
                            "action",
                            f"⚠️ {route} → navigation error: {str(e)[:120]}",
                        )

                try:
                    await context.close()
                except Exception:
                    pass
                pool.touch()
                runtime_state["_meta"]["frontend_visited"] = True
        except Exception as e:
            logger.warning(f"runtime_discovery: frontend visit failed: {e}")
            _log_session("system", f"⚠️ frontend discovery error: {e}")

    # ── 2) Backend endpoints called recently — از Render logs ──
    try:
        from ..verify_runtime.backend_log_probe import _fetch_relevant_logs
        # برای جمع‌آوری endpoints called، logs کلی (نه فیلتر شده) را scan کن
        # سپس path-ها را با endpoints inventory match کن
        recent_logs = await _fetch_relevant_logs(
            target_files=[],  # همه
            endpoints=[],
            symbols=[],
            window_hours=720,  # 30 روز
        )
        runtime_state["_meta"]["logs_fetched"] = True
        # match endpoints
        endpoints = inventory.get("backend_endpoints") or []
        seen: Set[str] = set()
        for log in (recent_logs or [])[:200]:
            msg = (log.get("message") or "").lower()
            for ep in endpoints:
                ep_path = (ep.get("path") or "").lower()
                if ep_path and ep_path in msg:
                    seen.add(ep_path)
        runtime_state["endpoints_called_recently"] = sorted(seen)
        # never_called
        runtime_state["endpoints_never_called"] = [
            ep.get("path") for ep in endpoints
            if ep.get("path") and (ep.get("path") or "").lower() not in seen
        ][:50]
        _log_session(
            "system",
            f"📊 backend logs: {len(seen)} endpoint called, "
            f"{len(runtime_state['endpoints_never_called'])} silent (30d)",
        )
    except Exception as e:
        logger.warning(f"runtime_discovery: log fetch failed: {e}")
        _log_session("system", f"⚠️ log fetch error: {e}")

    runtime_state["duration_ms"] = int((_time.monotonic() - start) * 1000)
    _log_session(
        "system",
        f"🏁 runtime_discovery تمام شد — alive={len(runtime_state['routes_alive'])}, "
        f"404={len(runtime_state['routes_404'])}, "
        f"called={len(runtime_state['endpoints_called_recently'])}",
    )
    return runtime_state
