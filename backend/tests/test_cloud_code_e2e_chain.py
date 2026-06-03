"""End-to-end chain test: prove the 4-stage Cloud Code centralization
behaves correctly across the full chain (registry → helper → consumer).

This file is the "did everything work?" test. After implementing each
stage individually and writing unit tests, run this file to verify
the seams hold together when the pieces actually meet.

If anything in this file fails, the centralization is broken end-to-end
even if every unit test passes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Scenario A — user never touches the models page
# ---------------------------------------------------------------------------


def test_e2e_default_state_preserves_legacy_behavior(monkeypatch):
    """No DB row → every consumer behaves as if Cloud Code is on (assuming
    the token is set). This is the critical "nothing breaks for existing
    users" guarantee."""
    from app.services import cloud_code_service as ccs
    from app.models.ai_profile import CLOUD_CODE_PREFERRED_FOR_KEYS

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")

    # Stub DB to return no row.
    class _Q:
        def filter(self, *a, **k): return self
        def first(self): return None
    class _DB:
        def query(self, *a, **k): return _Q()
        def close(self): pass
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _DB())

    for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
        assert ccs.cloud_code_setting_is_enabled_for(key) is True, (
            f"default state must enable consumer={key} — legacy behavior"
        )


# ---------------------------------------------------------------------------
# Scenario B — user toggles cloud_code OFF
# ---------------------------------------------------------------------------


def test_e2e_user_toggles_cloud_code_off(monkeypatch):
    """Row exists with enabled=0. Every consumer must report off, even
    though the env token is still set."""
    from app.services import cloud_code_service as ccs
    from app.models.ai_profile import CLOUD_CODE_PREFERRED_FOR_KEYS

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")

    row = MagicMock(enabled=0, preferred_for=[])
    class _Q:
        def filter(self, *a, **k): return self
        def first(self): return row
    class _DB:
        def query(self, *a, **k): return _Q()
        def close(self): pass
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _DB())

    for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
        assert ccs.cloud_code_setting_is_enabled_for(key) is False


# ---------------------------------------------------------------------------
# Scenario C — user enables but only for inspector
# ---------------------------------------------------------------------------


def test_e2e_user_restricts_to_inspector_only(monkeypatch):
    """The 4 consumer keys must independently honor preferred_for. The
    user picks ONE; the other 3 must fall back to default behavior."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")

    row = MagicMock(enabled=1, preferred_for=["inspector_cloud_code"])
    class _Q:
        def filter(self, *a, **k): return self
        def first(self): return row
    class _DB:
        def query(self, *a, **k): return _Q()
        def close(self): pass
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _DB())

    assert ccs.cloud_code_setting_is_enabled_for("inspector_cloud_code") is True
    assert ccs.cloud_code_setting_is_enabled_for("claude_auto_runner") is False
    assert ccs.cloud_code_setting_is_enabled_for("claude_single_task") is False
    assert ccs.cloud_code_setting_is_enabled_for("creator_engine") is False


# ---------------------------------------------------------------------------
# Scenario D — pick_model_for_task respects the helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_pick_model_for_task_returns_none_when_consumer_off(monkeypatch):
    """The actual decision the auto-runner makes: if the helper says off,
    the model picker returns None, the workflow falls back to its default
    sonnet alias. The runner still works — it just picks a default model."""
    from app.services import claude_runner_bootstrap as crb

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_setting_is_enabled_for",
        lambda key: False,
    )
    task = MagicMock(title="hello", raw_idea="world", prompt="x")
    assert await crb.pick_model_for_task(task, consumer_key="claude_auto_runner") is None
    assert await crb.pick_model_for_task(task, consumer_key="claude_single_task") is None


# ---------------------------------------------------------------------------
# Scenario E — inspector availability + 503 chain
# ---------------------------------------------------------------------------


def test_e2e_inspector_available_returns_helper_decision(monkeypatch):
    """The inspector chat endpoints (both /oversight/ and /render/ aliases)
    call InspectorAgentService.cloud_code_available() to decide whether
    to throw 503. That call now routes through the helper, so disabling
    the inspector consumer in the models page actually closes the chat."""
    from app.services import inspector_agent_service as ias

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")

    # Pretend helper says off
    monkeypatch.setattr(ias, "cloud_code_setting_is_enabled_for", lambda key: False)
    assert ias.InspectorAgentService.cloud_code_available() is False

    # Pretend helper says on
    monkeypatch.setattr(ias, "cloud_code_setting_is_enabled_for", lambda key: True)
    assert ias.InspectorAgentService.cloud_code_available() is True


# ---------------------------------------------------------------------------
# Scenario F — token absent gates everything
# ---------------------------------------------------------------------------


def test_e2e_no_token_disables_everything(monkeypatch):
    """If the OAuth token isn't set in env, no DB toggle can save the
    consumers — they all report off regardless of the row state."""
    from app.services import cloud_code_service as ccs
    from app.models.ai_profile import CLOUD_CODE_PREFERRED_FOR_KEYS

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

    # Even an enabled row with full prefs:
    row = MagicMock(enabled=1, preferred_for=["all"])
    class _Q:
        def filter(self, *a, **k): return self
        def first(self): return row
    class _DB:
        def query(self, *a, **k): return _Q()
        def close(self): pass
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _DB())

    for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
        assert ccs.cloud_code_setting_is_enabled_for(key) is False


# ---------------------------------------------------------------------------
# Scenario G — registry entry surface check
# ---------------------------------------------------------------------------


def test_e2e_registry_entry_is_complete():
    """The Cloud Code row in the models page is driven entirely by the
    MODEL_REGISTRY entry + the ModelSettings DB. Verify the entry has
    all fields the frontend needs."""
    from app.core.models_registry import MODEL_REGISTRY, get_model

    entry = get_model("cloud_code")
    assert entry is not None
    assert entry.name == "Cloud Code (Claude OAuth)"
    assert entry.cost_per_1k_tokens == 0.0
    assert entry.enabled is True
    # Capabilities must be picked up by the frontend filter chips.
    cap_values = [c.value if hasattr(c, "value") else str(c) for c in entry.capabilities]
    assert "code" in cap_values
    assert "reasoning" in cap_values
