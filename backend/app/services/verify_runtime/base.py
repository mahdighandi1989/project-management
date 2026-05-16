"""Stage 3a — types مشترک برای probe ها.

هر probe یک `RuntimeProbeResult` برمی‌گرداند که شامل:
- ac_id: شناسهٔ یکتا برای AC (index یا hash text)
- method: روش probe
- status: passed | failed | error | skipped
- evidence: dict دلخواه (screenshot_paths, response_json, stdout, ...)
- duration_ms: زمان اجرا
- error_message: در صورت خطا
- timestamp: ISO datetime
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


PROBE_STATUS_PASSED = "passed"
PROBE_STATUS_FAILED = "failed"
PROBE_STATUS_ERROR = "error"      # probe خودش crash کرد، نه AC شکست
PROBE_STATUS_SKIPPED = "skipped"  # base URL نبود، method نامرتبط، disable، ...

PROBE_STATUSES = (
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_ERROR,
    PROBE_STATUS_SKIPPED,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeProbeResult:
    """نتیجهٔ یک probe برای یک AC."""
    ac_id: str
    ac_text: str
    method: str  # static | ui_interaction | api_response | backend_test | manual_only
    status: str  # PROBE_STATUS_*
    evidence: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        """خلاصهٔ یک‌خطی برای نمایش به AI verify یا کاربر."""
        emoji = {
            PROBE_STATUS_PASSED: "✅",
            PROBE_STATUS_FAILED: "❌",
            PROBE_STATUS_ERROR: "⚠️",
            PROBE_STATUS_SKIPPED: "⏭",
        }.get(self.status, "❓")
        line = f"{emoji} {self.method}: {self.status}"
        if self.duration_ms:
            line += f" ({self.duration_ms}ms)"
        if self.error_message:
            line += f" — {self.error_message[:200]}"
        return line


class ProbeError(Exception):
    """خطای داخلی probe — به PROBE_STATUS_ERROR تبدیل می‌شود."""
    pass


# ---------------------------------------------------------------------------
# Probe context: اطلاعات لازم برای اجرای probe ها
# ---------------------------------------------------------------------------

@dataclass
class ProbeContext:
    """context مشترک که runner به probe ها می‌دهد.

    حاوی اطلاعات runtime که هر probe ممکن است نیاز داشته باشد:
    - base_url ها (frontend/backend)
    - auth (cookie/bearer)
    - repo path برای static probe + test probe
    - evidence_dir برای ذخیرهٔ screenshot/JSON
    - inspector_session_id برای ثبت اقدامات auto-verify در تب بازرس ویژه
    """
    task_id: str
    run_id: str
    repo_path: Optional[str] = None
    frontend_base_url: Optional[str] = None
    backend_base_url: Optional[str] = None
    auth_type: Optional[str] = None   # "cookie" | "bearer" | None
    auth_value: Optional[str] = None
    evidence_dir: Optional[str] = None  # مسیر absolute برای ذخیرهٔ شواهد
    # محدودیت‌های زمانی
    ui_timeout_ms: int = 30000
    api_timeout_s: int = 10
    # 🆕 (Phase 5 V4 — bug B2) — افزایش از ۱۲۰s به ۲۴۰s. تست‌های backend
    # اغلب شامل import های سنگین (fastapi، sqlalchemy، playwright) هستند
    # که خود ۲۰-۴۰s startup می‌خواهند. plan می‌تواند با timeout_seconds
    # override کند.
    test_timeout_s: int = 240
    # 🔬 (inspector_probe Phase 1) — اگر set باشد، inspector_probe پیام‌ها/شواهد
    # خود را در این session ذخیره می‌کند تا کاربر بتواند از تب بازرس ویژه ببیند.
    inspector_session_id: Optional[int] = None
    # 🔬 verify_model_id برای fallback Vision (text-only تحلیل) و auto-verify pipeline
    verify_model_id: Optional[str] = None
    # 🔬 watched_id برای جستجوی RenderLog مرتبط با سرویس
    watched_id: Optional[str] = None
    # 🔐 (Phase 3) — storage_state از Playwright (cookies + localStorage) که
    # اگر تنظیم شد، inspector_probe در new_context آن را اعمال می‌کند تا
    # probe به صفحات با لاگین دسترسی داشته باشد. dict مستقیماً قابل پاس
    # به browser.new_context(storage_state=...).
    storage_state: Optional[Dict[str, Any]] = None
