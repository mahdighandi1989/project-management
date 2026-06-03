"""Stage 2 of the Cloud Code centralization: helper that consumers query.

Pre-existing consumers each checked `cloud_code_is_configured()` directly
to decide whether to use Cloud Code. There was no way for the user to
say "use Cloud Code for inspector chat but NOT for auto-runner" — it
was all-or-nothing based on the env var.

The helper `cloud_code_setting_is_enabled_for(consumer_key)` answers the
per-consumer question by combining:
  - the env-based availability (must stay, else 503)
  - the ModelSettings DB row for `cloud_code` (enabled + preferred_for)

Behavior rules (locked by these tests):
  - no token in env       → False unconditionally
  - no DB row             → True (legacy behavior — sane default)
  - row exists, enabled=0 → False
  - enabled, prefs empty  → True for every consumer
  - enabled, prefs=["x"]  → only "x" gets True
  - enabled, prefs=["all"]→ wildcard: every consumer gets True
  - DB error              → True (legacy fallback so this can't regress)

No consumer is wired to the helper yet — that's stage 3. This stage
only adds the helper and its tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Pre-condition: env-driven availability
# ---------------------------------------------------------------------------


def test_helper_returns_false_when_no_token(monkeypatch):
    """If CLAUDE_CODE_OAUTH_TOKEN is unset, no consumer can use it
    regardless of DB state."""
    from app.services import cloud_code_service as ccs

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    assert ccs.cloud_code_setting_is_enabled_for("claude_auto_runner") is False


# ---------------------------------------------------------------------------
# DB-driven gating
# ---------------------------------------------------------------------------


def _patch_db_returning_row(monkeypatch, row):
    """Helper that swaps SessionLocal so the query returns `row`."""
    from app.services import cloud_code_service as ccs

    class _FakeQ:
        def __init__(self, r): self._r = r
        def filter(self, *a, **k): return self
        def first(self): return self._r

    class _FakeDB:
        def query(self, *a, **k): return _FakeQ(row)
        def close(self): pass

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")
    monkeypatch.setattr(
        "app.core.database.SessionLocal",
        lambda: _FakeDB(),
    )


def test_no_db_row_defaults_to_true_for_every_consumer(monkeypatch):
    """No row in ModelSettings = user hasn't customized = legacy
    behavior preserved. Every consumer reports enabled."""
    from app.services import cloud_code_service as ccs
    from app.models.ai_profile import CLOUD_CODE_PREFERRED_FOR_KEYS

    _patch_db_returning_row(monkeypatch, None)
    for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
        assert ccs.cloud_code_setting_is_enabled_for(key) is True, (
            f"consumer {key} should default to True when DB row absent"
        )


def test_db_row_enabled_false_disables_all_consumers(monkeypatch):
    """User explicitly toggled the row off → no consumer uses Cloud Code,
    even if preferred_for is non-empty."""
    from app.services import cloud_code_service as ccs

    row = MagicMock(enabled=0, preferred_for=["claude_auto_runner"])
    _patch_db_returning_row(monkeypatch, row)
    assert ccs.cloud_code_setting_is_enabled_for("claude_auto_runner") is False
    assert ccs.cloud_code_setting_is_enabled_for("inspector_cloud_code") is False


def test_db_row_enabled_no_prefs_means_all_consumers_on(monkeypatch):
    """Enabled with empty preferred_for = 'on for all' (matches the UX
    where the user enables Cloud Code without restricting it)."""
    from app.services import cloud_code_service as ccs
    from app.models.ai_profile import CLOUD_CODE_PREFERRED_FOR_KEYS

    row = MagicMock(enabled=1, preferred_for=[])
    _patch_db_returning_row(monkeypatch, row)
    for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
        assert ccs.cloud_code_setting_is_enabled_for(key) is True


def test_db_row_with_specific_prefs_only_enables_listed(monkeypatch):
    """Restricted prefs = only listed keys get True."""
    from app.services import cloud_code_service as ccs

    row = MagicMock(
        enabled=1,
        preferred_for=["claude_auto_runner", "inspector_cloud_code"],
    )
    _patch_db_returning_row(monkeypatch, row)
    assert ccs.cloud_code_setting_is_enabled_for("claude_auto_runner") is True
    assert ccs.cloud_code_setting_is_enabled_for("inspector_cloud_code") is True
    assert ccs.cloud_code_setting_is_enabled_for("claude_single_task") is False
    assert ccs.cloud_code_setting_is_enabled_for("creator_engine") is False


def test_db_row_with_all_wildcard_enables_every_consumer(monkeypatch):
    """`all` in preferred_for is the wildcard the UI uses for 'whole app'."""
    from app.services import cloud_code_service as ccs
    from app.models.ai_profile import CLOUD_CODE_PREFERRED_FOR_KEYS

    row = MagicMock(enabled=1, preferred_for=["all"])
    _patch_db_returning_row(monkeypatch, row)
    for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
        assert ccs.cloud_code_setting_is_enabled_for(key) is True


# ---------------------------------------------------------------------------
# DB error → fallback to legacy behavior (True)
# ---------------------------------------------------------------------------


def test_db_error_falls_back_to_true(monkeypatch):
    """A broken DB connection must not break the consumers. Legacy
    behavior (Cloud Code on if token set) must be preserved."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "dummy")

    def _broken():
        raise RuntimeError("DB down")

    monkeypatch.setattr("app.core.database.SessionLocal", _broken)
    # Must not raise; must return True.
    assert ccs.cloud_code_setting_is_enabled_for("claude_auto_runner") is True


# ---------------------------------------------------------------------------
# snapshot helper (diagnostics)
# ---------------------------------------------------------------------------


def test_snapshot_reports_token_state(monkeypatch):
    from app.services import cloud_code_service as ccs

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    snap = ccs.cloud_code_settings_snapshot()
    assert snap["token_configured"] is False


def test_snapshot_includes_per_consumer_decisions(monkeypatch):
    from app.services import cloud_code_service as ccs

    row = MagicMock(enabled=1, preferred_for=["claude_auto_runner"])
    _patch_db_returning_row(monkeypatch, row)
    snap = ccs.cloud_code_settings_snapshot()
    assert snap["token_configured"] is True
    assert snap["db_row_present"] is True
    assert snap["db_enabled"] is True
    assert snap["preferred_for"] == ["claude_auto_runner"]
    assert snap["consumers"]["claude_auto_runner"] is True
    assert snap["consumers"]["inspector_cloud_code"] is False
