"""🛡 Telegram webhook self-heal supervisor.

Background: the user reported "every button I press, nothing happens"
multiple times across separate weeks. Each occurrence had the same root
cause: the webhook Telegram had registered for our bot pointed at a
stale URL (after a Render redeploy, env var change, or after Telegram
paused delivery due to past errors). Manually calling
/telegram/set-webhook fixed it each time — until it broke again.

This file pins the self-heal supervisor so the regression can't return:

  1. Heal cycle is a no-op when bot token / public URL is unset (don't
     crash a deployment that doesn't use Telegram).
  2. When the webhook URL Telegram has differs from BACKEND_PUBLIC_URL,
     the supervisor re-sets it (the core fix).
  3. When pending_update_count is huge, supervisor re-sets WITH
     drop_pending_updates=True (Telegram paused us — clear the queue so
     a backlog doesn't keep us paused).
  4. When everything is healthy, supervisor returns {"healthy": true}
     with NO setWebhook call (idempotent / cheap).
  5. The supervisor loop respects stop_event for clean shutdown.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_mock_session(get_response: dict | None = None, post_response: dict | None = None):
    """Build a fake aiohttp.ClientSession that returns scripted JSON."""
    class _R:
        def __init__(self, data, status=200):
            self._data = data
            self.status = status
        async def json(self):
            return self._data
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    class _Sess:
        def __init__(self):
            self.get_calls = []
            self.post_calls = []
        def get(self, url, *a, **kw):
            self.get_calls.append(url)
            return _R(get_response or {"result": {}})
        def post(self, url, *a, **kw):
            self.post_calls.append({"url": url, "json": kw.get("json")})
            return _R(post_response or {"ok": True})
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    sess = _Sess()
    return sess


# ---------------------------------------------------------------------------
# 1. No bot token / no public URL → skipped (don't crash on dev/CI)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heal_skipped_without_bot_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://example.com")
    from app.services.notification_service import _telegram_webhook_heal_once
    result = await _telegram_webhook_heal_once()
    assert result == {"skipped": "no_bot_token"}


@pytest.mark.asyncio
async def test_heal_skipped_without_public_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "BOT123")
    monkeypatch.delenv("BACKEND_PUBLIC_URL", raising=False)
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("PUBLIC_URL", raising=False)
    from app.services.notification_service import _telegram_webhook_heal_once
    result = await _telegram_webhook_heal_once()
    assert result == {"skipped": "no_public_url"}


# ---------------------------------------------------------------------------
# 2. URL mismatch → re-set webhook (THE FIX for "buttons don't respond")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heal_resets_when_telegram_has_stale_url(monkeypatch):
    """Render redeployed → BACKEND_PUBLIC_URL changed → Telegram still has
    old URL. Supervisor must detect mismatch and re-set."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "BOT123")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://new-deploy.onrender.com")

    sess = _make_mock_session(
        get_response={"result": {
            "url": "https://old-deploy.onrender.com/api/notifications/telegram/webhook",
            "pending_update_count": 3,
        }},
        post_response={"ok": True},
    )

    def _session_factory(*a, **kw):
        return sess

    with patch("app.services.notification_service.aiohttp.ClientSession", _session_factory):
        from app.services.notification_service import _telegram_webhook_heal_once
        result = await _telegram_webhook_heal_once()

    assert result.get("reset") is True, (
        "URL mismatch must trigger a re-set so buttons start working again"
    )
    assert "url mismatch" in " ".join(result["reasons"])
    assert result["new_url"] == (
        "https://new-deploy.onrender.com/api/notifications/telegram/webhook"
    )
    # With small queue, don't drop pending updates — we want to process them
    assert result["dropped_pending"] is False
    # Confirm setWebhook was POSTed with the right URL
    assert any("setWebhook" in c["url"] for c in sess.post_calls)
    set_call = next(c for c in sess.post_calls if "setWebhook" in c["url"])
    assert set_call["json"]["url"] == (
        "https://new-deploy.onrender.com/api/notifications/telegram/webhook"
    )
    assert "callback_query" in set_call["json"]["allowed_updates"], (
        "callback_query is critical — without it, inline buttons silently dropped"
    )


# ---------------------------------------------------------------------------
# 3. Huge pending queue → re-set with drop_pending_updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heal_drops_pending_when_queue_huge(monkeypatch):
    """When pending_update_count is over the threshold, Telegram has paused
    delivery to us. A simple re-set without drop_pending_updates would
    keep the backlog and Telegram would just pause us again. Must drop."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "BOT123")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://deploy.onrender.com")

    expected_url = "https://deploy.onrender.com/api/notifications/telegram/webhook"
    sess = _make_mock_session(
        get_response={"result": {
            "url": expected_url,  # url matches — only trigger is the queue
            "pending_update_count": 250,
        }},
        post_response={"ok": True},
    )

    with patch(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: sess,
    ):
        from app.services.notification_service import _telegram_webhook_heal_once
        result = await _telegram_webhook_heal_once()

    assert result.get("reset") is True
    assert any("pending_update_count=250" in r for r in result["reasons"])
    set_call = next(c for c in sess.post_calls if "setWebhook" in c["url"])
    assert set_call["json"]["drop_pending_updates"] is True, (
        "huge queue means Telegram already paused us — must drop or we just "
        "re-pause immediately"
    )


# ---------------------------------------------------------------------------
# 4. Healthy webhook → no-op
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heal_noop_when_healthy(monkeypatch):
    """Idempotency: when the webhook matches and queue is small, supervisor
    must NOT make a setWebhook call. Otherwise every 5 min we'd thrash."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "BOT123")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://deploy.onrender.com")

    expected_url = "https://deploy.onrender.com/api/notifications/telegram/webhook"
    sess = _make_mock_session(
        get_response={"result": {
            "url": expected_url,
            "pending_update_count": 2,
        }},
        post_response={"ok": True},
    )

    with patch(
        "app.services.notification_service.aiohttp.ClientSession",
        lambda *a, **kw: sess,
    ):
        from app.services.notification_service import _telegram_webhook_heal_once
        result = await _telegram_webhook_heal_once()

    assert result.get("healthy") is True
    assert result["url"] == expected_url
    # Critical: zero setWebhook calls when healthy
    assert not any("setWebhook" in c["url"] for c in sess.post_calls), (
        "supervisor must be idempotent — no thrashing on healthy state"
    )


# ---------------------------------------------------------------------------
# 5. Public URL resolution priority
# ---------------------------------------------------------------------------


def test_public_url_resolution_priority(monkeypatch):
    """BACKEND_PUBLIC_URL wins, then RENDER_EXTERNAL_URL, then PUBLIC_URL.
    Trailing slash is stripped so the resulting webhook URL is clean."""
    from app.services.notification_service import _resolve_public_url

    monkeypatch.delenv("BACKEND_PUBLIC_URL", raising=False)
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("PUBLIC_URL", raising=False)
    assert _resolve_public_url() == ""

    monkeypatch.setenv("PUBLIC_URL", "https://c.com/")
    assert _resolve_public_url() == "https://c.com"

    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://b.com")
    assert _resolve_public_url() == "https://b.com"

    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://a.com//")
    assert _resolve_public_url() == "https://a.com"


# ---------------------------------------------------------------------------
# 6. Supervisor loop respects stop_event (clean shutdown)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_loop_stops_on_event():
    """Lifespan shutdown calls stop_event.set() — loop must exit promptly,
    not hang the worker."""
    from app.services.notification_service import telegram_webhook_supervisor_loop
    stop = asyncio.Event()
    # set stop immediately so the loop exits during initial delay
    stop.set()
    # should return within a couple seconds at most
    await asyncio.wait_for(telegram_webhook_supervisor_loop(stop), timeout=3.0)
