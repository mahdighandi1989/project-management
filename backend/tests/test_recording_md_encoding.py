"""UTF-8 / RTL safety of the .md prompt file sent to Telegram.

The recording feature emits a Persian-heavy markdown alongside the video.
Without an explicit BOM, some Windows / Android viewers (and Telegram's
own preview on certain platforms) misdetected the encoding as
Windows-1252 and rendered the Persian text as gibberish. These tests
lock down the two contracts that prevent that:

  1. The bytes returned by `_build_full_prompt_markdown` start with the
     UTF-8 BOM (EF BB BF) so any consumer that sniffs the prefix
     locks onto UTF-8 immediately.
  2. The Telegram document upload announces the right charset in
     content-type for every text format (md/txt/html/json) so HTTP
     middleboxes and Telegram's preview agree with the BOM.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Markdown bytes start with UTF-8 BOM and round-trip cleanly
# ---------------------------------------------------------------------------


def _fake_session(**overrides):
    """Minimal session stub that exercises every Persian-bearing branch."""
    s = MagicMock()
    defaults = dict(
        session_id="abc12345-rest",
        project_full_name="owner/repo",
        project_id="p1",
        mode="A",
        prompt_model="claude-sonnet-4-5",
        transcript_model="gemini-2.5-flash",
        prompt="پرامپت سنتزشده به فارسی.\nخط دوم.",
        transcript="سلام، این متن صداست.",
        visual_summary=[],
        location_timeline=[],
        interactions=[],
        console_logs=[],
        backend_logs=[],
    )
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    s.duration_sec.return_value = 65
    return s


def test_markdown_bytes_start_with_utf8_bom():
    from app.services.inspector_recording_finalize import _build_full_prompt_markdown

    out = _build_full_prompt_markdown(
        _fake_session(),
        user_note="یادداشت اولیه فارسی",
        task_id="t1",
    )
    assert out[:3] == b"\xef\xbb\xbf", (
        "Persian markdown must start with the UTF-8 BOM so Windows Notepad "
        "and Telegram previews lock onto UTF-8 instead of falling back to "
        "Windows-1252 (which shows the text as gibberish)."
    )


def test_markdown_persian_roundtrips_after_decoding():
    from app.services.inspector_recording_finalize import _build_full_prompt_markdown

    out = _build_full_prompt_markdown(
        _fake_session(),
        user_note="یادداشت اولیه فارسی",
        task_id="t1",
    )
    # `utf-8-sig` strips the BOM transparently, like every modern viewer.
    decoded = out.decode("utf-8-sig")
    for needle in ("پرامپت", "یادداشت", "transcript", "صداست"):
        assert needle in decoded, f"missing Persian fragment after roundtrip: {needle!r}"


def test_markdown_renders_every_section_for_mode_b():
    from app.services.inspector_recording_finalize import _build_full_prompt_markdown

    s = _fake_session(
        mode="B",
        visual_summary=[
            {
                "timestamp_ms": 5000,
                "scene": "صفحه ورود کاربر",
                "ocr_text": "ثبت‌نام",
                "ui_elements": "form, button",
                "error_signals": "",
                "user_voice_at_this_moment": "اینجا ثبت نام کن",
            }
        ],
        location_timeline=[
            {
                "ts_ms": 10000,
                "category": "chrome_tab",
                "url_or_app_name": "https://example.com/login",
                "related_to_project": True,
                "activity_description": "صفحه لاگین",
            }
        ],
        interactions=[
            MagicMock(ts_ms=2000, type="click", details={"x": 10})
        ],
        console_logs=[{"level": "warn", "message": "هشدار فرانت‌اند"}],
        backend_logs=[{"level": "error", "message": "خطای بک‌اند"}],
    )
    out = _build_full_prompt_markdown(s, user_note="نکته", task_id="t9")
    decoded = out.decode("utf-8-sig")
    # All Persian section headers + content must be present and intact
    for needle in (
        "## 🎙 transcript کامل صدا",
        "## 👁 خلاصه‌های بصری keyframes",
        "## 🗺 نقشهٔ زمانی فعالیت (mode B)",
        "## 🖱 تعاملات کاربر",
        "## 🌐 Console logs frontend",
        "## ⚙️ Backend logs",
        "صفحه ورود کاربر",
        "هشدار فرانت‌اند",
        "خطای بک‌اند",
    ):
        assert needle in decoded, f"missing section/content: {needle!r}"


# ---------------------------------------------------------------------------
# Telegram content-type announces charset=utf-8 for every text variant
# ---------------------------------------------------------------------------


def test_telegram_document_content_type_announces_utf8_for_text_formats():
    """The notification channel must hand the right Content-Type to the
    Telegram API for each text extension. Without an explicit
    `charset=utf-8`, certain Telegram clients sniff the bytes and may
    pick a legacy single-byte encoding for the preview, breaking
    Persian content even when the BOM is present."""
    import inspect

    from app.services import notification_service as ns

    src = inspect.getsource(ns.TelegramChannel.send_document)

    # Each branch must declare charset=utf-8.
    for ext, ctype_fragment in (
        (".md",   "text/markdown; charset=utf-8"),
        (".txt",  "text/plain; charset=utf-8"),
        (".html", "text/html; charset=utf-8"),
        (".json", "application/json; charset=utf-8"),
    ):
        assert ctype_fragment in src, (
            f"send_document must use {ctype_fragment!r} for {ext} files; "
            f"missing — Persian content will render as gibberish without it."
        )
