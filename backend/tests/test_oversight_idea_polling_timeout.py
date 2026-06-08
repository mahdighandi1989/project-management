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


def test_timeout_scales_with_attachment_count():
    """A bare idea-to-prompt call finishes in seconds; one with 13
    images + multi-pass takes minutes. The cap must scale per attachment
    so users with many images don't see a spurious timeout."""
    src = _read_oversight_page()
    # base 5 min, +1 min per attachment, capped at 15 min
    assert "baseSec = 300" in src, "5-minute base must be preserved"
    assert "perAttachmentSec = 60" in src, (
        "must add 60s per attachment so multi-image processing fits"
    )
    assert "15 * 60" in src, (
        "must cap at 15 min so a true backend hang still surfaces"
    )
    # And the loop count derives from the dynamic cap, not the old 150
    assert "const maxAttempts = Math.ceil(maxSec / 2)" in src, (
        "maxAttempts must derive from the dynamic cap, not be hardcoded"
    )


def test_no_progress_guard_bails_after_90s_without_track():
    """If the backend never registers the track (e.g., crashed before
    logging anything), polling for 5+ min on `found: false` is useless.
    Bail after 90s of no-progress so the user can retry promptly."""
    src = _read_oversight_page()
    assert "no-progress guard" in src
    assert "lastFoundAt" in src, (
        "must track the last time poll saw found:true to detect "
        "complete silence from the backend"
    )
    assert "Date.now() - lastFoundAt > 90 * 1000" in src, (
        "90s no-progress threshold must be enforced inside the polling loop"
    )
    assert "هیچ پیشرفتی از سرور دریافت نشد" in src


def test_timeout_message_mentions_attachment_count():
    """The final timeout error must tell the user WHY (number of
    attachments, elapsed minutes) so they can decide whether to retry
    or split the request — instead of a generic 'try again' that just
    repeats the same failure."""
    src = _read_oversight_page()
    # The message includes both ${minutes} and ${attachmentCount}
    assert "${minutes} دقیقه" in src or "${minutes} دقیقه" in src
    assert "${attachmentCount} پیوست" in src
    assert "تعداد پیوست‌ها را کاهش دهید" in src
