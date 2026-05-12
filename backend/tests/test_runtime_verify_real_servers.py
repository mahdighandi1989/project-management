"""Stage 10+ — تست‌های real-server.

- API probe در برابر یک aiohttp server محلی واقعی
- UI probe در برابر یک HTML page محلی (اگر Playwright نصب باشد)

این تست‌ها graceful skip می‌شوند اگر dep ها نباشند.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from app.services.verify_runtime.base import (
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_SKIPPED,
    ProbeContext,
)
from app.services.verify_runtime.api_probe import run_api_probe
from app.services.verify_runtime.ui_probe import run_ui_probe, _check_playwright_available


def _can_actually_launch_chromium() -> bool:
    """تست واقعی — آیا playwright می‌تواند chromium را launch کند؟
    این یک نسخه‌ٔ stricter از _check_playwright_available است که برای skip تست‌های
    real-Playwright استفاده می‌شود.
    """
    if not _check_playwright_available():
        return False
    try:
        import asyncio
        from playwright.async_api import async_playwright

        async def _try():
            async with async_playwright() as p:
                b = await p.chromium.launch(headless=True)
                await b.close()
            return True

        return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_try())
    except Exception:
        return False


_PLAYWRIGHT_RUNNABLE = _can_actually_launch_chromium()


# ---------------------------------------------------------------------------
# Real HTTP server (aiohttp) for API probe
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def local_http_server():
    """یک HTTP server محلی واقعی با چند endpoint برای تست."""
    try:
        from aiohttp import web
    except ImportError:
        pytest.skip("aiohttp not installed")

    async def health(req):
        return web.json_response({"ok": True, "version": "1.2", "user": {"email": "x@y"}})

    async def server_error(req):
        return web.json_response({"error": "internal"}, status=500)

    async def echo_post(req):
        body = await req.json()
        return web.json_response({"received": body, "ok": True})

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/error", server_error)
    app.router.add_post("/echo", echo_post)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)  # port 0 → OS picks free port
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    await runner.cleanup()


class TestApiProbeRealServer:
    @pytest.mark.asyncio
    async def test_health_passes(self, local_http_server):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url=local_http_server)
        ac = {"text": "GET /health 200", "verify_method": "api_response",
              "verify_plan": {"method": "GET", "path": "/health",
                              "expected_status": 200,
                              "required_fields": ["ok", "version"]}}
        r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED
        assert r.evidence["actual_status"] == 200

    @pytest.mark.asyncio
    async def test_dot_path_field(self, local_http_server):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url=local_http_server)
        ac = {"text": "GET /health user.email", "verify_method": "api_response",
              "verify_plan": {"path": "/health", "expected_status": 200,
                              "required_fields": ["user.email"]}}
        r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED

    @pytest.mark.asyncio
    async def test_500_fails(self, local_http_server):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url=local_http_server)
        ac = {"text": "X", "verify_method": "api_response",
              "verify_plan": {"path": "/error", "expected_status": 200}}
        r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_FAILED
        assert r.evidence["actual_status"] == 500

    @pytest.mark.asyncio
    async def test_post_with_body(self, local_http_server):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url=local_http_server)
        ac = {"text": "POST /echo", "verify_method": "api_response",
              "verify_plan": {"method": "POST", "path": "/echo",
                              "json_body": {"name": "Ali"},
                              "expected_status": 200,
                              "required_fields": ["received", "ok"]}}
        r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED

    @pytest.mark.asyncio
    async def test_unreachable_url_errors(self):
        ctx = ProbeContext(task_id="t", run_id="r",
                           backend_base_url="http://127.0.0.1:1")  # closed port
        ac = {"text": "X", "verify_method": "api_response",
              "verify_plan": {"path": "/", "expected_status": 200}}
        r = await run_api_probe(ac, ctx, "ac1")
        assert r.status in ("error", "failed")


# ---------------------------------------------------------------------------
# Real Playwright UI probe (skip if not installed)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def local_html_server():
    """یک static HTML server محلی برای تست UI probe."""
    try:
        from aiohttp import web
    except ImportError:
        pytest.skip("aiohttp not installed")

    with tempfile.TemporaryDirectory() as td:
        idx = Path(td) / "index.html"
        idx.write_text(
            "<!doctype html><html><body>"
            "<h1 id='hello' data-testid='hello'>Hello World</h1>"
            "<button id='btn' data-testid='btn-x' "
            "onclick=\"document.getElementById('modal').style.display='block'\">"
            "Open</button>"
            "<div id='modal' role='dialog' style='display:none' data-testid='modal'>"
            "<p>Modal Content</p></div>"
            "</body></html>",
            encoding="utf-8",
        )
        app = web.Application()
        app.router.add_get("/", lambda r: web.FileResponse(idx))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        yield f"http://127.0.0.1:{port}"
        await runner.cleanup()


@pytest.mark.skipif(
    not _PLAYWRIGHT_RUNNABLE,
    reason="playwright chromium not launchable in this env",
)
class TestUiProbeReal:
    @pytest.mark.asyncio
    async def test_navigate_and_assert_visible(self, local_html_server, tmp_path):
        ctx = ProbeContext(
            task_id="t", run_id="r",
            frontend_base_url=local_html_server,
            evidence_dir=str(tmp_path),
        )
        ac = {"text": "h1 hello نمایش داده شود", "verify_method": "ui_interaction",
              "verify_plan": {
                  "base": "frontend",
                  "ui_steps": [
                      {"action": "navigate", "url": "/"},
                      {"action": "wait_for_load_state", "state": "domcontentloaded"},
                      {"action": "assert_visible", "selector": "#hello"},
                      {"action": "assert_text", "selector": "#hello",
                       "contains": "Hello"},
                  ],
              }}
        r = await run_ui_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED, r.evidence

    @pytest.mark.asyncio
    async def test_click_opens_modal(self, local_html_server, tmp_path):
        ctx = ProbeContext(
            task_id="t", run_id="r",
            frontend_base_url=local_html_server,
            evidence_dir=str(tmp_path),
        )
        ac = {"text": "کلیک روی دکمه مدال باز شود",
              "verify_method": "ui_interaction",
              "verify_plan": {
                  "base": "frontend",
                  "ui_steps": [
                      {"action": "navigate", "url": "/"},
                      {"action": "click", "selector": "[data-testid='btn-x']"},
                      {"action": "wait_for_selector",
                       "selector": "[role='dialog']", "timeout_ms": 3000},
                      {"action": "assert_visible",
                       "selector": "[data-testid='modal']"},
                  ],
              }}
        r = await run_ui_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED, r.evidence
        # screenshot ها در evidence_dir ایجاد شده باشند
        shots = list(Path(tmp_path).rglob("*.png"))
        assert len(shots) >= 1

    @pytest.mark.asyncio
    async def test_missing_selector_fails(self, local_html_server, tmp_path):
        ctx = ProbeContext(
            task_id="t", run_id="r",
            frontend_base_url=local_html_server,
            evidence_dir=str(tmp_path),
        )
        ac = {"text": "X", "verify_method": "ui_interaction",
              "verify_plan": {
                  "base": "frontend",
                  "ui_steps": [
                      {"action": "navigate", "url": "/"},
                      {"action": "assert_visible", "selector": "#never-exists"},
                  ],
              }}
        r = await run_ui_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_FAILED
