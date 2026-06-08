"""🛡 (oversight idea-to-prompt timeout) — کاربر گزارش داد که با ۱۳ تصویر پیوست،
frontend timeout می‌خورد قبل از کامل شدن backend.

از logs کاربر:
  - backend POST anthropic چندین بار (multi-pass mode)
  - frontend polling progress endpoint
  - بعد از ~۹۰ ثانیه error «زمان پردازش بیش از حد طول کشید» نمایش
  - عجیب: timeout مشخص شده بود ۵ دقیقه (150 * 2s) ولی polling زودتر stop شد

علل احتمالی:
  ۱) `pollOnce` throw می‌کرد روی Render edge transient 502/503 → loop abort
  ۲) با ۱۳ تصویر، multi-pass واقعاً > ۵ دقیقه طول می‌کشد
  ۳) هیچ guard برای «track id اصلاً نیامد» نبود (backend silent crash)

این فایل تست‌های source-level برای fix هر سه می‌نویسد.
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


def test_pollonce_swallows_transient_errors():
    """pollOnce must NOT throw on transient 502/503 from Render edge —
    those happen routinely mid-Anthropic-call and used to abort the
    polling loop, surfacing a misleading 'timeout' error after a single
    failed poll instead of retrying."""
    src = _read_oversight_page()
    # The fix wraps the fetch in try/catch and returns null on 502/503
    # instead of throwing. Pin both halves.
    assert "// network blip → swallow, try again" in src, (
        "pollOnce must swallow network blips so the polling loop "
        "doesn't abort on a single transient Render edge failure"
    )
    assert "poll-resilience" in src


def test_polling_loop_uses_progress_based_guards_not_fixed_cap():
    """🛡 v2 — User reported the 15-min hard cap killed a perfectly-
    healthy multi-image run at 15:00 while backend was still climbing.
    Replaced by progress-based guards: as long as the snapshot's stage
    or percent is changing, keep polling. Only abort if (a) NO progress
    for 4 minutes, (b) track never registered for 90s, or (c) absolute
    60-min runaway cap is hit."""
    src = _read_oversight_page()
    # Stuck threshold (4 min of no progress)
    assert "STUCK_THRESHOLD_SEC = 4 * 60" in src, (
        "must define a stuck-progress threshold so legitimately slow "
        "but advancing processes aren't killed"
    )
    # Absolute runaway cap, much higher than the previous 15-min limit
    assert "ABSOLUTE_MAX_SEC = 60 * 60" in src, (
        "absolute cap must be 60 min so big batches finish naturally"
    )
    # Track-register guard (replaces the 90s no-found guard)
    assert "TRACK_REGISTER_THRESHOLD_SEC = 90" in src
    # Progress signature compares stage + percent + detail so we detect
    # genuine forward movement, not just any non-empty snapshot
    assert "progressKey" in src and "lastProgressAt" in src, (
        "must compute a progress signature so we know whether the "
        "snapshot is actually advancing or just being re-emitted"
    )
    # No fixed maxAttempts loop — while(true) with the three guards
    assert "while (true)" in src, (
        "polling loop must run open-ended; guards decide when to break"
    )


def test_no_progress_guard_bails_when_track_never_registers():
    """If the backend never registers the track (e.g., crashed before
    logging anything), polling for many minutes on `found: false` is
    useless. Bail after 90s so the user can retry promptly."""
    src = _read_oversight_page()
    assert "TRACK_REGISTER_THRESHOLD_SEC" in src
    assert "sawTrack" in src, (
        "must track whether poll EVER saw found:true to distinguish "
        "'track never registered' from 'track active but slow'"
    )
    assert "هیچ پیشرفتی از سرور دریافت نشد" in src


def test_stuck_progress_guard_fires_only_after_4min_silence():
    """If the backend's progress signature hasn't changed in 4 minutes,
    something is genuinely stuck. Bail with a clear error so the user
    can retry instead of waiting on a hung process."""
    src = _read_oversight_page()
    assert "lastProgressAt" in src
    assert "STUCK_THRESHOLD_SEC * 1000" in src
    assert "پردازش بیش از" in src and "بدون تغییر مانده" in src, (
        "stuck-progress error message must clearly distinguish 'stuck' "
        "from 'long but advancing' so the user knows to retry"
    )


def test_absolute_cap_error_mentions_attachment_count():
    """If the absolute 60-min cap is hit (genuine runaway), the message
    must tell the user how many attachments + minutes so they can
    decide whether to split the request."""
    src = _read_oversight_page()
    # The runaway message includes both ${minutes} and ${attachmentCount}
    assert "${minutes} دقیقه" in src
    assert "${attachmentCount} پیوست" in src
    assert "تعداد پیوست‌ها را کاهش دهید" in src
