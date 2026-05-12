"""Stage 9 — safety, flags, circuit breaker.

این ماژول گاردهای جلوگیری از crash و overuse را فراهم می‌کند:

1. RUNTIME_VERIFY_ENABLED env flag — اگر "false"، کل runtime layer
   خاموش است.
2. RUNTIME_VERIFY_UI_ENABLED env flag — اگر "false"، UI probe ها
   skip می‌شوند (مفید برای production که Playwright nصب نیست).
3. Circuit breaker per-probe-method: اگر 3 بار پشت‌سرهم error داد،
   آن method برای 10 دقیقه disable می‌شود (هر AC از آن method
   → skipped).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# env flags
# ---------------------------------------------------------------------------

def is_runtime_enabled() -> bool:
    """flag سراسری برای کل runtime layer."""
    return os.environ.get("RUNTIME_VERIFY_ENABLED", "true").lower() != "false"


def is_ui_probe_enabled() -> bool:
    """flag مستقل برای UI probe (Playwright). در Render production
    معمولاً false است چون image size محدود است."""
    if not is_runtime_enabled():
        return False
    return os.environ.get("RUNTIME_VERIFY_UI_ENABLED", "true").lower() != "false"


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

_CIRCUIT_ERROR_THRESHOLD = 3      # هر چند error متوالی → open کن
_CIRCUIT_OPEN_SECONDS = 600       # ۱۰ دقیقه


class CircuitBreaker:
    """per-method circuit breaker.

    State machine ساده:
    - closed: probe اجازه دارد
    - open: probe skip می‌شود تا CIRCUIT_OPEN_SECONDS بگذرد
    - half_open: یک probe دیگر اجازه دارد — اگر pass شد closed،
      اگر error دوباره open

    Thread/async safe نیست — فقط در event loop اصلی استفاده می‌شود.
    """

    def __init__(self) -> None:
        self._error_counts: Dict[str, int] = {}
        self._open_until: Dict[str, float] = {}

    def is_open(self, method: str) -> bool:
        until = self._open_until.get(method)
        if until is None:
            return False
        if time.monotonic() < until:
            return True
        # expired → close
        self._open_until.pop(method, None)
        self._error_counts[method] = 0
        return False

    def record_result(self, method: str, status: str) -> None:
        """نتیجهٔ یک probe را ثبت کن. status: passed/failed/error/skipped."""
        if status == "error":
            n = self._error_counts.get(method, 0) + 1
            self._error_counts[method] = n
            if n >= _CIRCUIT_ERROR_THRESHOLD:
                self._open_until[method] = time.monotonic() + _CIRCUIT_OPEN_SECONDS
                logger.warning(
                    f"circuit OPEN for probe method={method} "
                    f"after {n} consecutive errors — will retry in "
                    f"{_CIRCUIT_OPEN_SECONDS}s"
                )
        elif status in ("passed", "failed"):
            # یک probe که تا انتها رفته (passed/failed) error نیست —
            # error counter را ریست کن
            if self._error_counts.get(method):
                self._error_counts[method] = 0
        # skipped را نه ثبت می‌کنیم نه ریست — neutral

    def snapshot(self) -> Dict[str, Any]:
        now = time.monotonic()
        return {
            "errors": dict(self._error_counts),
            "open_methods": {
                m: int(t - now)
                for m, t in self._open_until.items()
                if t > now
            },
        }

    def reset(self) -> None:
        self._error_counts.clear()
        self._open_until.clear()


# singleton
_breaker = CircuitBreaker()


def get_breaker() -> CircuitBreaker:
    return _breaker
