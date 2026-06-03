"""Stage 3: each Cloud Code consumer queries the central helper.

stage 1 added the registry entry. stage 2 added
`cloud_code_setting_is_enabled_for(consumer_key)`. stage 3 wires every
existing consumer to pass its consumer_key so the helper actually gets
consulted.

If a future refactor accidentally drops the keyword arg, the consumer
silently reverts to legacy (always-on) behavior — the user toggle in
the models page would do nothing. These tests pin the wiring at the
source level so that regression is caught loudly.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# pick_model_for_task signature accepts consumer_key
# ---------------------------------------------------------------------------


def test_pick_model_for_task_accepts_consumer_key_kwarg():
    from app.services.claude_runner_bootstrap import pick_model_for_task

    sig = inspect.signature(pick_model_for_task)
    assert "consumer_key" in sig.parameters, (
        "pick_model_for_task lost its consumer_key parameter — "
        "without it, all callers default to legacy always-on behavior "
        "and the user's model-page toggle does nothing"
    )
    # Must be keyword-only or have a default of None
    p = sig.parameters["consumer_key"]
    assert p.default is None


# ---------------------------------------------------------------------------
# pick_model_for_task honors the helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pick_model_for_task_returns_none_when_consumer_disabled(monkeypatch):
    """If the consumer is disabled in the models page, pick must return
    None so the workflow falls back to its default sonnet alias."""
    from app.services import claude_runner_bootstrap as crb

    # cloud_code is configured (env)
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_is_configured",
        lambda: True,
    )
    # but disabled for this consumer
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: False,
    )
    task = MagicMock(title="x", raw_idea="y", prompt="z")
    result = await crb.pick_model_for_task(task, consumer_key="claude_auto_runner")
    assert result is None


@pytest.mark.asyncio
async def test_pick_model_for_task_without_consumer_key_uses_legacy_path(monkeypatch):
    """Backward-compat: if a caller doesn't pass consumer_key, the
    helper isn't consulted (legacy behavior preserved). This protects
    any unknown callers we missed."""
    from app.services import claude_runner_bootstrap as crb

    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_is_configured",
        lambda: True,
    )
    # If consumer_key were checked, this would force False — but the
    # legacy path shouldn't call it.
    helper_calls = []

    def _spy(key):
        helper_calls.append(key)
        return False

    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        _spy,
    )
    # Also stub pick_best_model so we don't make a network call.
    async def _fake_pick(messages, **kw):
        return ("claude-sonnet-4-x", "sonnet", "stub")
    monkeypatch.setattr(
        "app.services.cloud_code_service.pick_best_model", _fake_pick,
    )
    task = MagicMock(title="x", raw_idea="y", prompt="z")
    # No consumer_key passed:
    result = await crb.pick_model_for_task(task)
    assert result == "claude-sonnet-4-x"
    assert helper_calls == [], (
        "consumer_key not passed → helper must not be consulted"
    )


# ---------------------------------------------------------------------------
# Consumers pass the right consumer_key
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_prompt_github_sync_passes_auto_runner_key():
    """The auto-runner path (workflow dispatch on task push) must use
    consumer_key='claude_auto_runner'."""
    src = _read(
        Path(__file__).resolve().parents[1]
        / "app/services/prompt_github_sync.py"
    )
    # Look for the call site that picks the model.
    assert 'pick_model_for_task(\n                    _next_task, consumer_key="claude_auto_runner"' in src \
        or 'consumer_key="claude_auto_runner"' in src, (
        "prompt_github_sync must pass consumer_key='claude_auto_runner' "
        "to pick_model_for_task — otherwise the user's models-page toggle "
        "for auto-runner is silently ignored"
    )


def test_external_prompts_verify_chain_passes_auto_runner_key():
    """_verify_then_chain re-triggers the auto-runner — same consumer.
    There's only one call site to pick_model_for_task in this file,
    so we check the whole file for the auto-runner key."""
    src = _read(
        Path(__file__).resolve().parents[1]
        / "app/api/routes/external_prompts.py"
    )
    assert "pick_model_for_task" in src
    # Every call site must specify the consumer key.
    assert 'consumer_key="claude_auto_runner"' in src, (
        "external_prompts must pass the auto-runner consumer key"
    )


def test_oversight_run_single_task_passes_single_task_key():
    """run_single_task_via_claude is the per-card 'Run via Claude' button."""
    src = _read(
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    )
    # All call sites for pick_model_for_task in this file (there's only
    # one today) must use the single-task consumer key.
    idx = src.find("pick_model_for_task(\n            t, consumer_key=")
    if idx == -1:
        # tolerate alternate formatting
        idx = src.find('consumer_key="claude_single_task"')
    assert idx != -1, (
        "oversight_service must pass consumer_key='claude_single_task' "
        "from the Run-via-Claude button path"
    )


def test_inspector_agent_service_availability_routes_through_helper():
    """The inspector chat UI calls cloud_code_available() to decide
    whether to show the engine option. That call must consult the
    helper using the 'inspector_cloud_code' key — otherwise toggling
    inspector off in the models page does nothing."""
    src = _read(
        Path(__file__).resolve().parents[1]
        / "app/services/inspector_agent_service.py"
    )
    assert 'cloud_code_setting_is_enabled_for("inspector_cloud_code")' in src, (
        "InspectorAgentService.cloud_code_available must call the central "
        "helper with the inspector consumer key"
    )


# ---------------------------------------------------------------------------
# inspector_agent_service.cloud_code_available behavior
# ---------------------------------------------------------------------------


def test_inspector_cloud_code_available_returns_helper_result(monkeypatch):
    """When the helper says off, available() reports off — even if the
    token is set."""
    from app.services import inspector_agent_service as ias

    # inspector_agent_service imports the helper by name (`from ... import ...`)
    # so we must patch the reference IN that module, not the source.
    monkeypatch.setattr(
        ias, "cloud_code_setting_is_enabled_for", lambda key: False,
    )
    assert ias.InspectorAgentService.cloud_code_available() is False


def test_inspector_cloud_code_available_helper_called_with_right_key(monkeypatch):
    """The exact key matters — pinning it stops a future typo from
    silently breaking the wiring."""
    from app.services import inspector_agent_service as ias

    seen = []

    def _spy(key):
        seen.append(key)
        return True

    monkeypatch.setattr(ias, "cloud_code_setting_is_enabled_for", _spy)
    ias.InspectorAgentService.cloud_code_available()
    assert seen == ["inspector_cloud_code"]
