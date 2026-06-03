"""Tests for the auto-backfill-AC scheduler trigger.

The user reported a workflow gap: the yellow "⚠️ backfill AC ها" and the
purple "🔬 Force re-enrich (Phase 3)" buttons appeared periodically on the
dashboard, the user kept clicking them manually, and didn't know what
they did. This file locks down the new auto-trigger that makes the
scheduler handle them itself and notify on Telegram.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Helpers — build a fake oversight service with the bare minimum surface
# the new _maybe_auto_backfill_ac touches.
# ---------------------------------------------------------------------------


def _make_service(
    *,
    tasks: List[Any],
    enabled: bool = True,
    min_hours: float = 6.0,
    last_at: str | None = None,
):
    from app.services.oversight_service import OversightService

    svc = OversightService.__new__(OversightService)
    svc.tasks = tasks
    svc.settings = {
        "auto_backfill_ac_enabled": enabled,
        "auto_backfill_ac_min_hours": min_hours,
        "last_auto_backfill_ac_at": last_at,
    }
    svc._save_settings = MagicMock()
    return svc


def _ac_unclassified():
    return {"text": "Login button works", "verify_method": ""}


def _ac_classified_with_phase2_plan():
    return {
        "text": "Form submits",
        "verify_method": "ui_interaction",
        "verify_plan": {"steps": [{"action": "navigate"}]},
    }


def _ac_classified_with_rich_plan():
    return {
        "text": "Form submits",
        "verify_method": "ui_interaction",
        "verify_plan": {"steps": [
            {"action": "navigate"},
            {"action": "click"},
            {"action": "type"},
            {"action": "assert"},
        ]},
    }


def _make_task(acs, archived=False):
    return SimpleNamespace(
        acceptance_criteria=acs,
        archived=archived,
    )


# ---------------------------------------------------------------------------
# Gating conditions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_backfill_skipped_when_disabled(monkeypatch):
    """settings.auto_backfill_ac_enabled=False → never triggers."""
    svc = _make_service(
        tasks=[_make_task([_ac_unclassified()])],
        enabled=False,
    )
    fake_state = {"running": False}
    fake_runner = AsyncMock()

    with patch.dict(
        "sys.modules",
        {"app.api.routes.oversight": SimpleNamespace(
            _BACKFILL_STATE=fake_state,
            _run_backfill_ac_classification=fake_runner,
        )},
    ):
        await svc._maybe_auto_backfill_ac()
    fake_runner.assert_not_called()


@pytest.mark.asyncio
async def test_auto_backfill_skipped_during_cooldown():
    """Within min_hours of the last run, don't fire again."""
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    svc = _make_service(
        tasks=[_make_task([_ac_unclassified()])],
        min_hours=6.0,
        last_at=recent,
    )
    fake_state = {"running": False}
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()
    fake_runner.assert_not_called()


@pytest.mark.asyncio
async def test_auto_backfill_skipped_when_already_running():
    """If a manual or previous auto run is in flight, don't double-trigger."""
    svc = _make_service(tasks=[_make_task([_ac_unclassified()])])
    fake_state = {"running": True}  # already busy
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()
    fake_runner.assert_not_called()


@pytest.mark.asyncio
async def test_auto_backfill_skipped_when_nothing_needs_attention():
    """All AC classified with rich plans → nothing to do."""
    svc = _make_service(tasks=[_make_task([
        _ac_classified_with_rich_plan(),
        _ac_classified_with_rich_plan(),
    ])])
    fake_state = {"running": False}
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()
    fake_runner.assert_not_called()


# ---------------------------------------------------------------------------
# Trigger paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_backfill_triggers_regular_when_unclassified_ac_exist():
    """The cheaper path (force=False) wins when there are unclassified ACs."""
    svc = _make_service(tasks=[_make_task([_ac_unclassified(), _ac_unclassified()])])
    fake_state = {"running": False}
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()

    # await the create_task coroutine so the assertion sees the call
    import asyncio
    await asyncio.sleep(0)

    fake_runner.assert_called_once()
    call = fake_runner.call_args
    assert call.kwargs.get("force") is False
    assert fake_state["running"] is True
    assert fake_state["force"] is False
    assert fake_state["triggered_by"] == "auto_scheduler"
    # cooldown timestamp written so the next tick honours it
    assert svc.settings["last_auto_backfill_ac_at"] is not None
    svc._save_settings.assert_called_once()


@pytest.mark.asyncio
async def test_auto_backfill_triggers_force_when_only_phase2_plans_remain():
    """No unclassified ACs but some have Phase-2 plans → force=True."""
    svc = _make_service(tasks=[
        _make_task([_ac_classified_with_phase2_plan()]),
        _make_task([_ac_classified_with_rich_plan()]),  # already rich
    ])
    fake_state = {"running": False}
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()
    import asyncio
    await asyncio.sleep(0)

    fake_runner.assert_called_once()
    assert fake_runner.call_args.kwargs.get("force") is True
    assert fake_state["force"] is True
    assert fake_state["triggered_by"] == "auto_scheduler"


@pytest.mark.asyncio
async def test_auto_backfill_prefers_regular_when_both_conditions_hold():
    """If both unclassified ACs and Phase-2 plans exist, regular path
    (cheaper, only enriches the unclassified set) fires first. On the
    next eligible tick — when only Phase-2 plans remain — force will fire."""
    svc = _make_service(tasks=[
        _make_task([_ac_unclassified()]),
        _make_task([_ac_classified_with_phase2_plan()]),
    ])
    fake_state = {"running": False}
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()
    import asyncio
    await asyncio.sleep(0)

    fake_runner.assert_called_once()
    assert fake_runner.call_args.kwargs.get("force") is False


@pytest.mark.asyncio
async def test_auto_backfill_ignores_archived_tasks():
    """Archived tasks don't count toward 'work needed'."""
    svc = _make_service(tasks=[
        _make_task([_ac_unclassified()], archived=True),
    ])
    fake_state = {"running": False}
    fake_runner = AsyncMock()
    with patch.dict("sys.modules", {"app.api.routes.oversight": SimpleNamespace(
        _BACKFILL_STATE=fake_state,
        _run_backfill_ac_classification=fake_runner,
    )}):
        await svc._maybe_auto_backfill_ac()
    fake_runner.assert_not_called()
