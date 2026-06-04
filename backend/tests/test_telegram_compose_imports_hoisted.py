"""🚨 Regression test: get_compose_service / ComposeItem must always
resolve at module level in notification_service.

User reported `/reminder` button in Telegram returned:
   ⚠️ خطای داخلی در پردازش دستور:
   name 'get_compose_service' is not defined

Root cause: `_start_reminder_flow` (added in commit dde6ea3) called
`get_compose_service()` but forgot the local `from .oversight_telegram_compose
import get_compose_service` that every other handler had. Python only
catches such missing-name bugs at runtime, so it shipped for weeks
unnoticed — every other handler had the local import as a convention,
but conventions don't compile-check.

Permanent fix: hoist `get_compose_service` and `ComposeItem` to the
top of `notification_service.py` so they're always in scope. These
tests pin the fix:

1. The two names must be importable directly from notification_service
   module top-level (catches any future "let me move this back to local
   imports" refactor that would silently re-introduce the bug).
2. `_start_reminder_flow` must execute end-to-end without NameError,
   even with mocked compose_service and tg — this is the exact path
   the user hit.
3. (Source-level) the canonical hoist line must be present so a partial
   refactor that deletes only the hoist (leaving a function still
   referencing `get_compose_service`) is caught.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_get_compose_service_is_hoisted_to_module_level():
    """Importing the symbol from the parent module must succeed.

    If a future refactor moves this back to a function-local import, the
    `from app.services.notification_service import get_compose_service`
    fails with ImportError — caught at test time, not in production."""
    from app.services.notification_service import get_compose_service
    assert callable(get_compose_service)


def test_compose_item_is_hoisted_to_module_level():
    """Same guarantee for ComposeItem — used by 2 handlers
    (_start_codex_flow / _start_telegram_creator paths)."""
    from app.services.notification_service import ComposeItem
    assert ComposeItem is not None


def test_hoist_marker_present_in_source():
    """Source check — the hoist line must remain. Without this,
    deleting it would re-expose every handler to NameError."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/notification_service.py"
    ).read_text(encoding="utf-8")
    # The exact hoist marker — both names must be hoisted together.
    assert (
        "from .oversight_telegram_compose import get_compose_service, ComposeItem"
        in src
    ), (
        "the module-level import of get_compose_service / ComposeItem must "
        "remain — otherwise handlers that don't add their own local import "
        "will crash with NameError (user reported /reminder broken this way)"
    )


@pytest.mark.asyncio
async def test_start_reminder_flow_does_not_NameError():
    """The exact failure path: user taps /reminder, _start_reminder_flow
    runs, must NOT raise NameError. Before the hoist, this test would
    fail with `name 'get_compose_service' is not defined`."""
    from app.services.notification_service import notification_service

    fake_compose = SimpleNamespace(
        start=AsyncMock(return_value=None),
    )

    with patch(
        "app.services.notification_service.get_compose_service",
        return_value=fake_compose,
    ), patch.object(
        notification_service, "_telegram",
        return_value=SimpleNamespace(send=AsyncMock(return_value={"ok": True})),
    ):
        # Should NOT raise NameError
        result = await notification_service._start_reminder_flow("12345")

    assert result.get("ok") is True
    assert result.get("handled") == "reminder_compose_started"
    fake_compose.start.assert_called_once()


@pytest.mark.asyncio
async def test_start_reminder_flow_passes_correct_compose_args():
    """Beyond NameError-safety: the reminder flow must start compose with
    force_type='reminder' so the buffer routes to the reminder pipeline
    on submit. Catches a future refactor that breaks the routing."""
    from app.services.notification_service import notification_service

    fake_compose = SimpleNamespace(
        start=AsyncMock(return_value=None),
    )

    with patch(
        "app.services.notification_service.get_compose_service",
        return_value=fake_compose,
    ), patch.object(
        notification_service, "_telegram",
        return_value=SimpleNamespace(send=AsyncMock(return_value={"ok": True})),
    ):
        await notification_service._start_reminder_flow("12345")

    call_kwargs = fake_compose.start.call_args.kwargs
    assert call_kwargs.get("force_type") == "reminder", (
        "must pass force_type='reminder' so submit routes to reminder pipeline"
    )
    assert call_kwargs.get("watched_id") is None, (
        "reminders are repo-agnostic — watched_id must be None"
    )
    assert call_kwargs.get("replace") is True, (
        "reminder flow must replace any active compose to avoid mixing buffers"
    )
