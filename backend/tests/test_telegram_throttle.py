"""Tests for TelegramChannel flood-protection and the /kb quick-restore.

The user reported that the persistent menu disappears on Telegram Web /
desktop after bursts of notifications (verify ping-pong + scan + recording
finalize all firing within seconds), and that the per-message URL buttons
under those notifications appear stuck. Both symptoms point to Telegram
flood-protection 429s dropping our subsequent sends — including the
re-attach of the persistent reply keyboard.

This file guards the two countermeasures:

  1. Per-chat token bucket (~1 msg/1.1s) inside TelegramChannel.send.
  2. 429-aware behaviour: when Telegram returns a parameters.retry_after,
     a global pause is set so the next sends naturally space out instead
     of being rejected too.

  3. The new /kb command (and Persian aliases) is a minimum-surface
     restore path — one send, with a 1-shot retry — so the user can
     always recover the menu even if every other code path got rate-
     limited.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from app.services.notification_service import (  # noqa: E402
    PERSISTENT_REPLY_KEYBOARD,
    TelegramChannel,
)


# ---------------------------------------------------------------------------
# Per-chat throttle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_chat_throttle_spaces_out_back_to_back_sends(monkeypatch):
    """Two send()s to the same chat back-to-back must observe at least
    the configured _MIN_INTERVAL_PER_CHAT_SEC gap."""
    # Reset class state
    TelegramChannel._last_send_at.clear()
    TelegramChannel._global_pause_until = 0.0
    # Speed up the test — use a small interval
    monkeypatch.setattr(TelegramChannel, "_MIN_INTERVAL_PER_CHAT_SEC", 0.15)

    ch = TelegramChannel(bot_token="x", chat_id="123")
    starts: List[float] = []

    class _OkResp:
        status = 200

        async def text(self):
            return ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _SessionStub:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, json=None):
            starts.append(time.monotonic())
            return _OkResp()

    monkeypatch.setattr(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: _SessionStub(),
    )

    await ch.send("first")
    await ch.send("second")
    await ch.send("third")

    # Three calls → gaps between them should both be >= the configured min
    assert len(starts) == 3
    gap_1 = starts[1] - starts[0]
    gap_2 = starts[2] - starts[1]
    assert gap_1 >= 0.14, f"gap1={gap_1}"
    assert gap_2 >= 0.14, f"gap2={gap_2}"


# ---------------------------------------------------------------------------
# 429 absorbs the retry_after into the global pause
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_with_retry_after_sets_global_pause_and_retries(monkeypatch):
    """When Telegram returns 429 + parameters.retry_after, the channel
    must:
      1. Absorb the retry_after into the class-level _global_pause_until.
      2. Wait for that pause to elapse.
      3. Retry the same request once.
    """
    TelegramChannel._last_send_at.clear()
    TelegramChannel._global_pause_until = 0.0
    monkeypatch.setattr(TelegramChannel, "_MIN_INTERVAL_PER_CHAT_SEC", 0.01)

    ch = TelegramChannel(bot_token="x", chat_id="42")
    call_count = {"n": 0}

    class _Resp:
        def __init__(self, status, body):
            self.status = status
            self._body = body

        async def text(self):
            return self._body

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _SessionStub:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, json=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First call → 429 with retry_after=1
                return _Resp(429, json_module.dumps({
                    "ok": False,
                    "error_code": 429,
                    "description": "Too Many Requests: retry after 1",
                    "parameters": {"retry_after": 1},
                }))
            return _Resp(200, "")

    import json as json_module
    monkeypatch.setattr(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: _SessionStub(),
    )

    t0 = time.monotonic()
    res = await ch.send("hello")
    elapsed = time.monotonic() - t0

    assert res.get("ok") is True
    assert res.get("retried_after_429") is True
    assert call_count["n"] == 2
    # Should have actually waited at least ~1s
    assert elapsed >= 0.9, f"elapsed={elapsed}"
    # Class-level pause persists for the buffer beyond the wait
    assert TelegramChannel._global_pause_until > 0


@pytest.mark.asyncio
async def test_global_pause_blocks_other_chats_too(monkeypatch):
    """A 429 from one chat must slow subsequent sends to *any* chat —
    the limit is account-wide on Telegram."""
    TelegramChannel._last_send_at.clear()
    # Set a small global pause manually
    TelegramChannel._global_pause_until = time.monotonic() + 0.3
    monkeypatch.setattr(TelegramChannel, "_MIN_INTERVAL_PER_CHAT_SEC", 0.0)

    # Use a different chat_id — must still wait
    ch = TelegramChannel(bot_token="x", chat_id="other-chat")

    class _OkResp:
        status = 200

        async def text(self):
            return ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _SessionStub:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, json=None):
            return _OkResp()

    monkeypatch.setattr(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: _SessionStub(),
    )

    t0 = time.monotonic()
    await ch.send("hi")
    waited = time.monotonic() - t0
    assert waited >= 0.25, f"waited={waited}"
    # Clean up
    TelegramChannel._global_pause_until = 0.0


# ---------------------------------------------------------------------------
# /kb command — minimum-surface restore
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kb_command_sends_persistent_reply_keyboard(monkeypatch):
    """/kb is the lifeline when /menu got rate-limited away. It must send
    exactly one short message whose reply_markup is the persistent
    keyboard, with no inline_keyboard or other heavy payload."""
    from app.services.notification_service import notification_service

    captured: List[Dict[str, Any]] = []

    class _FakeTG:
        bot_token = "x"
        chat_id = "config-chat"

        async def send(self, message, *, silent=False, reply_markup=None, subject=None):
            captured.append({"message": message, "reply_markup": reply_markup, "silent": silent})
            return {"ok": True}

    monkeypatch.setattr(notification_service, "_telegram", lambda: _FakeTG())
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "config-chat")

    res = await notification_service.handle_telegram_update({
        "message": {
            "text": "/kb",
            "chat": {"id": "config-chat"},
        },
    })
    assert res.get("handled") == "kb_restore"
    assert len(captured) >= 1
    assert captured[0]["reply_markup"] == PERSISTENT_REPLY_KEYBOARD


@pytest.mark.asyncio
async def test_ping_command_responds_with_pong_minimal_overhead(monkeypatch):
    """The /ping diagnostic must always succeed — single send, no markup,
    no DB, no external call. It is the lifeline when everything else
    seems broken."""
    from app.services.notification_service import notification_service

    captured: List[Dict[str, Any]] = []

    class _FakeTG:
        bot_token = "x"
        chat_id = "config-chat"

        async def send(self, message, *, silent=False, reply_markup=None, subject=None):
            captured.append({"message": message, "reply_markup": reply_markup, "silent": silent})
            return {"ok": True}

    monkeypatch.setattr(notification_service, "_telegram", lambda: _FakeTG())
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "config-chat")

    res = await notification_service.handle_telegram_update({
        "message": {"text": "/ping", "chat": {"id": "config-chat"}},
    })
    assert res.get("handled") == "ping"
    assert len(captured) == 1
    assert "pong" in captured[0]["message"].lower()
    # No reply_markup — keep it minimum surface so it can't be blocked by
    # markup parse errors or rate-limit cascades.
    assert captured[0]["reply_markup"] is None


@pytest.mark.asyncio
async def test_handle_update_keeps_running_when_cleanup_state_crashes(monkeypatch):
    """If _cleanup_expired_state throws, the user's command must still be
    processed — regression against the original report where the bot
    silently stopped responding."""
    from app.services import notification_service as ns_module
    from app.services.notification_service import notification_service

    captured: List[Dict[str, Any]] = []

    class _FakeTG:
        bot_token = "x"
        chat_id = "config-chat"

        async def send(self, message, *, silent=False, reply_markup=None, subject=None):
            captured.append({"message": message})
            return {"ok": True}

    monkeypatch.setattr(notification_service, "_telegram", lambda: _FakeTG())
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "config-chat")

    # Simulate cleanup crashing
    def _boom():
        raise RuntimeError("cleanup crash")
    monkeypatch.setattr(ns_module, "_cleanup_expired_state", _boom)

    res = await notification_service.handle_telegram_update({
        "message": {"text": "/ping", "chat": {"id": "config-chat"}},
    })
    # /ping still succeeded despite the cleanup crash
    assert res.get("handled") == "ping"
    assert any("pong" in (c["message"].lower()) for c in captured)


@pytest.mark.asyncio
async def test_kb_command_retries_when_first_send_fails(monkeypatch):
    """If the first send fails (rate-limit just kicked in), /kb should
    retry once with an even smaller payload — so the user always gets
    the keyboard back."""
    from app.services.notification_service import notification_service

    captured: List[Dict[str, Any]] = []

    class _FakeTG:
        bot_token = "x"
        chat_id = "config-chat"
        _calls = 0

        async def send(self, message, *, silent=False, reply_markup=None, subject=None):
            type(self)._calls += 1
            captured.append({"message": message, "reply_markup": reply_markup})
            if type(self)._calls == 1:
                return {"ok": False, "error": "HTTP 429"}
            return {"ok": True}

    monkeypatch.setattr(notification_service, "_telegram", lambda: _FakeTG())
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "config-chat")

    res = await notification_service.handle_telegram_update({
        "message": {
            "text": "/kb",
            "chat": {"id": "config-chat"},
        },
    })
    assert res.get("handled") == "kb_restore"
    # First call full-text, second is a single emoji — both with keyboard
    assert len(captured) == 2
    assert all(c["reply_markup"] == PERSISTENT_REPLY_KEYBOARD for c in captured)
