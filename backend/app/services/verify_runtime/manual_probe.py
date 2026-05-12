"""Stage 3a — Manual probe (no-op با پیام).

AC هایی که method=manual_only هستند نیاز به بازبینی انسانی دارند —
probe فقط یک نتیجهٔ skipped با پیام واضح برمی‌گرداند.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from .base import (
    PROBE_STATUS_SKIPPED,
    ProbeContext,
    RuntimeProbeResult,
)


def run_manual_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
) -> RuntimeProbeResult:
    plan = ac.get("verify_plan") or {}
    reason = plan.get("reason") or "این AC نیاز به بازبینی انسانی دارد و خودکار قابل تأیید نیست."
    return RuntimeProbeResult(
        ac_id=ac_id,
        ac_text=str(ac.get("text") or ""),
        method="manual_only",
        status=PROBE_STATUS_SKIPPED,
        evidence={"reason": reason},
        duration_ms=0,
    )
