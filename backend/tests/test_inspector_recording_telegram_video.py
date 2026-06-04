"""🎬 Inspector recording → Telegram delivery (iframe mode A).

User-reported bug: after iframe-mode recording finished, Telegram showed
a single screenshot as a "sticker" instead of playing the actual video.
The prompt .md was delivered fine, but the video itself appeared as a
static image and couldn't be played.

Root cause: the previous implementation built an animated WebP and
called Telegram's `sendAnimation` API. But sendAnimation only supports
GIF / MP4 / PNG — when given WebP it extracts the first frame and
treats it as a sticker. So users got a screenshot.

Fix (3 layers):
  1. _build_mp4_from_frames — uses ffmpeg to build a real MP4 (preferred,
     plays inline on every Telegram client, smallest file).
  2. _build_animated_gif_from_frames — Pillow-only fallback for hosts
     without ffmpeg. Telegram plays GIF inline via sendAnimation.
  3. _build_video_for_telegram — picks MP4 first, falls back to GIF.
     Never returns WebP. Never returns None when frames exist + Pillow is
     installed (Render guarantees both).

send_video() in notification_service now:
  - routes .gif → sendAnimation (works)
  - routes .webp → sendDocument (safety net for old code paths; user
    at least gets the file rather than a static sticker)

These tests pin all three layers + the routing rule.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _seed_frames_dir(n: int = 12, size=(320, 240)) -> Path:
    """Create a temp dir with n PNG frames so the builders have input."""
    from PIL import Image, ImageDraw
    d = Path(tempfile.mkdtemp(prefix="frames_"))
    for i in range(n):
        img = Image.new("RGB", size, (255 - i * 10 % 255, 100, 50 + i * 5 % 200))
        # Draw frame number so each frame is distinguishable
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"frame {i}", fill=(255, 255, 255))
        img.save(d / f"frame_{i:04d}.png", format="PNG")
    return d


# ---------------------------------------------------------------------------
# 1. GIF fallback (always works — Pillow always available)
# ---------------------------------------------------------------------------


def test_gif_fallback_produces_animated_gif():
    """Without ffmpeg, _build_animated_gif_from_frames must produce a
    valid multi-frame GIF that Telegram's sendAnimation can play."""
    from app.services.inspector_recording_finalize import (
        _build_animated_gif_from_frames,
    )
    fd = _seed_frames_dir(n=8)
    try:
        result = _build_animated_gif_from_frames(fd, max_frames=8, fps=2)
        assert result is not None, "GIF builder must succeed with valid frames"
        data, mime = result
        assert mime == "image/gif"
        assert len(data) > 100, "GIF bytes must be non-trivial"
        # Validate it's an actual multi-frame GIF
        from PIL import Image
        gif = Image.open(io.BytesIO(data))
        gif.seek(1)  # raises EOFError if only 1 frame
        assert gif.format == "GIF"
    finally:
        shutil.rmtree(fd, ignore_errors=True)


def test_gif_fallback_returns_none_on_empty_dir():
    """No frames → return None so caller can record a warning."""
    from app.services.inspector_recording_finalize import (
        _build_animated_gif_from_frames,
    )
    empty = Path(tempfile.mkdtemp(prefix="empty_"))
    try:
        assert _build_animated_gif_from_frames(empty) is None
    finally:
        shutil.rmtree(empty, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2. MP4 builder behavior (skip when ffmpeg unavailable)
# ---------------------------------------------------------------------------


def test_mp4_builder_returns_none_without_ffmpeg():
    """When ffmpeg is missing, the MP4 builder must short-circuit so the
    caller can fall through to GIF — must NOT raise or hang."""
    from app.services.inspector_recording_finalize import _build_mp4_from_frames
    with patch(
        "app.services.inspector_recording_finalize._ffmpeg_available",
        return_value=False,
    ):
        fd = _seed_frames_dir(n=4)
        try:
            assert _build_mp4_from_frames(fd) is None
        finally:
            shutil.rmtree(fd, ignore_errors=True)


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg not installed in this test environment",
)
def test_mp4_builder_produces_playable_mp4_when_ffmpeg_present():
    """On hosts with ffmpeg (Render production), MP4 must be produced
    with H.264 + yuv420p + faststart so Telegram plays it inline."""
    from app.services.inspector_recording_finalize import _build_mp4_from_frames
    fd = _seed_frames_dir(n=8)
    try:
        result = _build_mp4_from_frames(fd)
        assert result is not None
        data, mime = result
        assert mime == "video/mp4"
        # MP4 magic: ftyp box appears near start
        assert b"ftyp" in data[:32], "must be a valid MP4 file"
    finally:
        shutil.rmtree(fd, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. Top-level dispatcher prefers MP4, falls back to GIF, NEVER WebP
# ---------------------------------------------------------------------------


def test_build_video_for_telegram_prefers_mp4_when_available():
    """If both MP4 and GIF builders would succeed, MP4 wins (Telegram
    plays it inline, smaller file)."""
    from app.services.inspector_recording_finalize import _build_video_for_telegram

    with patch(
        "app.services.inspector_recording_finalize._build_mp4_from_frames",
        return_value=(b"fake-mp4-bytes", "video/mp4"),
    ), patch(
        "app.services.inspector_recording_finalize._build_animated_gif_from_frames",
        return_value=(b"fake-gif-bytes", "image/gif"),
    ):
        fd = _seed_frames_dir(n=4)
        try:
            result = _build_video_for_telegram(fd)
        finally:
            shutil.rmtree(fd, ignore_errors=True)

    assert result is not None
    data, name, mime = result
    assert data == b"fake-mp4-bytes"
    assert name.endswith(".mp4")
    assert mime == "video/mp4"


def test_build_video_for_telegram_falls_back_to_gif_without_ffmpeg():
    """No ffmpeg → use GIF. Filename ends with .gif so the Telegram
    sender routes to sendAnimation correctly."""
    from app.services.inspector_recording_finalize import _build_video_for_telegram

    with patch(
        "app.services.inspector_recording_finalize._build_mp4_from_frames",
        return_value=None,
    ):
        fd = _seed_frames_dir(n=4)
        try:
            result = _build_video_for_telegram(fd)
        finally:
            shutil.rmtree(fd, ignore_errors=True)

    assert result is not None
    data, name, mime = result
    assert name.endswith(".gif")
    assert mime == "image/gif"
    assert len(data) > 100


def test_build_video_for_telegram_never_returns_webp():
    """🚨 Regression guard: even with WebP in the codebase, the dispatcher
    must NEVER return .webp — Telegram renders it as a sticker."""
    from app.services.inspector_recording_finalize import _build_video_for_telegram

    fd = _seed_frames_dir(n=4)
    try:
        result = _build_video_for_telegram(fd)
    finally:
        shutil.rmtree(fd, ignore_errors=True)

    if result is None:
        return  # both builders failed — fine for this guard
    _, name, mime = result
    assert not name.endswith(".webp"), (
        "WebP must not be sent to Telegram — it renders as a static sticker"
    )
    assert mime != "image/webp"


# ---------------------------------------------------------------------------
# 4. Telegram sender routes .gif → sendAnimation, .webp → sendDocument
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_video_routes_gif_to_send_animation():
    """A .gif filename must hit sendAnimation, not sendVideo."""
    from app.services.notification_service import TelegramChannel

    tc = TelegramChannel(bot_token="BOT123", chat_id="42")

    captured = {}

    class _R:
        def __init__(self):
            self.status = 200
        async def text(self):
            return '{"ok": true, "result": {"message_id": 1}}'
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    class _Sess:
        def post(self, url, data=None, **kw):
            captured["url"] = url
            return _R()
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with patch(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: _Sess(),
    ):
        await tc.send_video(b"GIF89a-fake-bytes", "recording.gif", caption="x")

    assert "sendAnimation" in captured["url"], (
        "GIF must route to sendAnimation so Telegram plays it inline"
    )


@pytest.mark.asyncio
async def test_send_video_routes_webp_to_send_document():
    """🚨 Safety net: if old code somehow produces .webp, it must NOT go
    to sendAnimation (which renders it as a sticker). Must go to
    sendDocument so the user at least gets the file."""
    from app.services.notification_service import TelegramChannel

    tc = TelegramChannel(bot_token="BOT123", chat_id="42")

    called = {"send_document": False, "send_video_url": None}

    async def fake_doc(file_bytes, filename, *, caption=None, silent=False):
        called["send_document"] = True
        called["doc_filename"] = filename
        return {"ok": True, "channel": "telegram", "filename": filename}

    with patch.object(tc, "send_document", side_effect=fake_doc):
        result = await tc.send_video(b"RIFF-webp-bytes", "rec.webp", caption="x")

    assert called["send_document"] is True, (
        "WebP must be routed to sendDocument, not sendAnimation/sendVideo — "
        "Telegram treats WebP as a sticker on the animation endpoint"
    )
    assert called["doc_filename"] == "rec.webp"
    assert result.get("ok") is True


@pytest.mark.asyncio
async def test_send_video_routes_mp4_to_send_video():
    """MP4 must hit sendVideo (not sendAnimation) so Telegram shows it
    with playback controls and preview."""
    from app.services.notification_service import TelegramChannel

    tc = TelegramChannel(bot_token="BOT123", chat_id="42")
    captured = {}

    class _R:
        def __init__(self):
            self.status = 200
        async def text(self):
            return '{"ok": true, "result": {"message_id": 1}}'
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    class _Sess:
        def post(self, url, data=None, **kw):
            captured["url"] = url
            return _R()
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with patch(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: _Sess(),
    ):
        await tc.send_video(b"\x00\x00\x00\x20ftypmp42", "recording.mp4", caption="x")

    assert "sendVideo" in captured["url"]
    assert "sendAnimation" not in captured["url"]
