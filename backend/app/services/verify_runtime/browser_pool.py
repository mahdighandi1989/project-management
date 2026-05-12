"""Browser pool — share یک Playwright instance بین probe ها.

به جای launch/close هر بار Chromium (که هر بار ~2s طول می‌کشد)، یک
browser pool را در FastAPI lifespan زنده نگه می‌داریم.

- get_browser(): اگر Playwright در دسترس است، یک browser باز برمی‌گرداند.
- shutdown_browser(): در shutdown FastAPI کلیه browser و playwright instance
  را می‌بندد.
- ۵ دقیقه idle → خودکار kill (در background task).

Thread-safe نیست؛ فقط در event loop اصلی استفاده می‌شود.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# پس از این مدت idle، browser kill می‌شود
_IDLE_TIMEOUT_S = 5 * 60


class BrowserPool:
    """singleton browser pool."""

    def __init__(self) -> None:
        self._pw: Optional[Any] = None       # AsyncPlaywright
        self._browser: Optional[Any] = None  # Browser
        self._lock = asyncio.Lock()
        self._last_used_at: float = 0.0
        self._idle_task: Optional[asyncio.Task] = None
        self._shutting_down: bool = False

    async def get_browser(self) -> Optional[Any]:
        """browser شده را برمی‌گرداند (lazy launch).

        اگر playwright در دسترس نباشد → None.
        """
        if self._shutting_down:
            return None
        try:
            from playwright.async_api import async_playwright  # noqa: F401
        except ImportError:
            return None
        async with self._lock:
            if self._browser is not None:
                # تست سلامت ساده: aware از crashed browser
                try:
                    is_connected = self._browser.is_connected()
                except Exception:
                    is_connected = False
                if not is_connected:
                    logger.warning("browser pool: lost connection, relaunching")
                    self._browser = None
                    self._pw = None
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                    self._pw = await async_playwright().start()
                    self._browser = await self._pw.chromium.launch(headless=True)
                    logger.info("browser pool: launched headless chromium")
                except Exception as e:
                    logger.warning(f"browser pool: chromium launch failed: {e}")
                    self._browser = None
                    self._pw = None
                    return None
            self._last_used_at = time.monotonic()
            # idle reaper را اگر نیست start کن
            if self._idle_task is None or self._idle_task.done():
                try:
                    self._idle_task = asyncio.create_task(self._idle_reaper())
                except RuntimeError:
                    # ممکن است در tests بدون loop باشد
                    pass
            return self._browser

    def touch(self) -> None:
        """نشانه‌گذاری کن که browser در حال استفاده است."""
        self._last_used_at = time.monotonic()

    async def _idle_reaper(self) -> None:
        """هر دقیقه چک کن — اگر >5 دقیقه idle، browser را ببند."""
        while not self._shutting_down:
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            if self._browser is None:
                continue
            idle = time.monotonic() - self._last_used_at
            if idle >= _IDLE_TIMEOUT_S:
                logger.info(f"browser pool: idle {int(idle)}s — closing")
                await self._close_inner()
                # پس از close idle reaper هم می‌تواند تمام شود
                return

    async def _close_inner(self) -> None:
        async with self._lock:
            br = self._browser
            pw = self._pw
            self._browser = None
            self._pw = None
        if br is not None:
            try:
                await br.close()
            except Exception as e:
                logger.debug(f"browser close error: {e}")
        if pw is not None:
            try:
                await pw.stop()
            except Exception as e:
                logger.debug(f"playwright stop error: {e}")

    async def shutdown(self) -> None:
        """در shutdown FastAPI صدا زده شود."""
        self._shutting_down = True
        if self._idle_task is not None and not self._idle_task.done():
            self._idle_task.cancel()
            try:
                await self._idle_task
            except (asyncio.CancelledError, Exception):
                pass
        await self._close_inner()
        logger.info("browser pool: shutdown complete")


# singleton
_pool: Optional[BrowserPool] = None


def get_browser_pool() -> BrowserPool:
    global _pool
    if _pool is None:
        _pool = BrowserPool()
    return _pool


async def shutdown_browser_pool() -> None:
    """در lifespan FastAPI صدا زده می‌شود."""
    global _pool
    if _pool is not None:
        await _pool.shutdown()
        _pool = None
