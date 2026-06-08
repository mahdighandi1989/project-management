"""🛡 v3 (no-fixed-timeout) — کاربر گزارش داد که هر threshold زمانی خودسرانه
در سناریوی واقعی غلط فعال می‌شود:

  v1: 5 min hard cap → multi-image fail
  v2: 15 min scaled cap → still fail (20+ min legitimate)
  v3: stuck-after-4min → fail در آخرین merge step (1 ساعت progress واقعی)

تصمیم نهایی: حذف **همه** thresholdهای زمانی. فقط ۴ راه برای قطع polling:
  1) backend می‌گوید completed=true
  2) backend می‌گوید error
  3) کاربر دکمهٔ لغو می‌زند (cancelGenRef.current=true)
  4) چندین poll پشت سر هم 404 → track wipe

UI زمان سپری شده را نشان می‌دهد + دکمهٔ لغو دارد تا کاربر آگاهانه تصمیم بگیرد.
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _read_oversight_page() -> str:
    p = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/app/oversight/page.tsx"
    )
    return p.read_text(encoding="utf-8")


def test_v3_removes_all_fixed_time_thresholds():
    """🛡 v3 — هیچ threshold زمانی hardcoded نباید باقی مانده باشد.
    تشخیص آنها بر اساس متغیرهای _SEC نام‌گذاری شدهٔ قبلی."""
    src = _read_oversight_page()
    for legacy_threshold in (
        "ABSOLUTE_MAX_SEC",
        "STUCK_THRESHOLD_SEC",
        "TRACK_REGISTER_THRESHOLD_SEC",
    ):
        # OK to mention in code comments documenting history, but the
        # variable itself must not be in active polling logic
        active = src.replace("// ", "\n").split("\n")
        active_lines = [
            ln for ln in active
            if legacy_threshold in ln
            and not ln.strip().startswith("//")
            and "no-fixed-timeout" not in ln
            and "v3" not in ln
        ]
        assert not active_lines, (
            f"{legacy_threshold} must not be used in the polling loop — "
            f"v3 removed all time-based aborts. Found: {active_lines}"
        )


def test_polling_loop_only_breaks_on_completed_error_cancel_or_404():
    """polling loop must exit only on these 4 conditions:
      1) snap.completed=true
      2) snap.completed + snap.error
      3) cancelGenRef.current=true
      4) consecutiveGone >= 5 (404)
    No time-based abort."""
    src = _read_oversight_page()
    # Cancel ref must be checked inside the loop
    assert "cancelGenRef.current" in src, (
        "must use a ref for cancellation so the polling closure sees "
        "live updates (state would capture initial false value)"
    )
    assert "userCancelled = true" in src
    # 404-based track-wipe detection
    assert "consecutiveGone" in src
    assert "consecutiveGone >= 5" in src, (
        "must require 5 consecutive 404s before giving up — a single "
        "404 could be a Render edge blip"
    )
    # completed path
    assert "snap.completed" in src
    # No-fixed-timeout comment marker
    assert "no-fixed-timeout v3" in src


def test_ui_shows_elapsed_time_and_cancel_button():
    """User said: «من باید بفهمم داره کار میشه». UI must surface:
      - elapsed time (minutes + seconds) so user gauges progress
      - a manual cancel button so they're in control"""
    src = _read_oversight_page()
    assert "genElapsedSec" in src, (
        "must track and display elapsed seconds so user knows how long "
        "they've been waiting"
    )
    assert "setInterval" in src and "Date.now() - startedAt" in src, (
        "elapsed timer must update every second based on real wall-clock"
    )
    # Persian UI strings
    assert "سپری شده" in src
    assert "لغو پردازش" in src
    # Cancel button updates BOTH the ref (sync, for the polling loop) and
    # the state (for re-rendering the button label)
    assert "cancelGenRef.current = true" in src
    assert "setCancelGen(true)" in src


def test_no_fixed_timeout_error_messages_removed():
    """The old timeout error messages were misleading — user got
    «زمان پردازش بیش از حد طول کشید» while backend was still working.
    Those exact messages must be gone."""
    src = _read_oversight_page()
    # The old runaway/stuck-cap messages tied to time thresholds
    forbidden = [
        # v1 message
        "زمان پردازش بیش از حد طول کشید — لطفاً دوباره تلاش کنید",
        # v2 stuck message
        "بدون تغییر مانده — احتمالاً سرور stuck شده",
    ]
    for bad in forbidden:
        assert bad not in src, (
            f"v1/v2 timeout message must be removed: {bad!r}"
        )


def test_user_cancel_message_includes_elapsed_minutes():
    """When user clicks cancel, the error toast must tell them how long
    they waited so they have a record."""
    src = _read_oversight_page()
    assert "پردازش توسط کاربر لغو شد" in src
    assert "${elapsedMin} دقیقه" in src
