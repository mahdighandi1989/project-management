"""Stage 3b — UI probe tests (با graceful skip اگر Playwright نباشد).

تست‌های واقعی Playwright فقط در صورت نصب شدن آن اجرا می‌شوند.
بقیه (graceful skip / select_base_url / etc) همیشه اجرا می‌شوند.
"""

import pytest

from app.services.verify_runtime.base import (
    PROBE_STATUS_SKIPPED,
    PROBE_STATUS_ERROR,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    ProbeContext,
)
from app.services.verify_runtime.ui_probe import (
    _check_playwright_available,
    _select_base_url,
    run_ui_probe,
)


class TestSelectBaseUrl:
    def test_frontend_default(self):
        ctx = ProbeContext(
            task_id="t", run_id="r",
            frontend_base_url="http://fe.test",
            backend_base_url="http://be.test",
        )
        assert _select_base_url("frontend", ctx) == "http://fe.test"

    def test_backend_explicit(self):
        ctx = ProbeContext(
            task_id="t", run_id="r",
            frontend_base_url="http://fe.test",
            backend_base_url="http://be.test",
        )
        assert _select_base_url("backend", ctx) == "http://be.test"

    def test_missing_returns_none(self):
        ctx = ProbeContext(task_id="t", run_id="r")
        assert _select_base_url("frontend", ctx) is None


class TestUiProbeWithoutPlaywright:
    """اگر playwright نباشد، probe باید graceful skip شود."""

    @pytest.mark.asyncio
    async def test_skip_when_playwright_missing(self, monkeypatch):
        # شبیه‌سازی فقدان playwright
        monkeypatch.setattr(
            "app.services.verify_runtime.ui_probe._PLAYWRIGHT_AVAILABLE", False,
        )
        ctx = ProbeContext(task_id="t", run_id="r", frontend_base_url="http://x")
        ac = {"text": "X", "verify_method": "ui_interaction",
              "verify_plan": {"ui_steps": [{"action": "navigate", "url": "/"}]}}
        r = await run_ui_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_SKIPPED
        assert "playwright" in r.evidence["reason"].lower()

    @pytest.mark.asyncio
    async def test_skip_when_no_ui_steps(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.verify_runtime.ui_probe._PLAYWRIGHT_AVAILABLE", True,
        )
        ctx = ProbeContext(task_id="t", run_id="r", frontend_base_url="http://x")
        ac = {"text": "X", "verify_method": "ui_interaction", "verify_plan": {"ui_steps": []}}
        r = await run_ui_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_SKIPPED

    @pytest.mark.asyncio
    async def test_skip_when_no_base_url(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.verify_runtime.ui_probe._PLAYWRIGHT_AVAILABLE", True,
        )
        ctx = ProbeContext(task_id="t", run_id="r")  # no base URLs
        ac = {"text": "X", "verify_method": "ui_interaction",
              "verify_plan": {"ui_steps": [{"action": "navigate", "url": "/"}]}}
        r = await run_ui_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_SKIPPED
        assert "base_url" in r.evidence["reason"]


# نکته: تست‌های واقعی Playwright (open browser) در stage 10 با
# yet-another HTML server کوچک خواهد بود. اینجا فقط mock-able path ها
# را تست می‌کنیم.
