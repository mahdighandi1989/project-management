"""Sync-guard: every event in EVENT_REGISTRY must be reachable from the
NotificationSettingsPanel UI.

The user reported that Claude Auto-Runner notifications (start, complete,
fail, retry) and the new auto-backfill notification arrived in Telegram
but had no row in the settings UI — making them impossible to silence or
toggle sound for. Root cause: events were registered in backend
EVENT_REGISTRY but never added to the frontend `EVENT_GROUPS` array,
which is what the panel iterates over.

This test parses the frontend file and asserts every backend event ID is
either:
  • listed inside one of the EVENT_GROUPS arrays, OR
  • visible via the panel's "auto-detected orphans" fallback (currently
    always present in the rendered JSX).

The auto-orphan fallback is a runtime safety net, but having this test
catches the omission at PR-review time so we don't ship UI gaps.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_every_backend_event_is_either_grouped_or_caught_by_orphan_fallback():
    from app.services.notification_service import EVENT_REGISTRY

    panel_path = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/components/NotificationSettingsPanel.tsx"
    )
    assert panel_path.exists(), f"settings panel not found at {panel_path}"
    src = panel_path.read_text(encoding="utf-8")

    # Extract every key listed under any `keys: [...]` array inside
    # EVENT_GROUPS. We don't try to be clever — just pull `'foo'` quoted
    # strings from anywhere inside the file that appears between
    # `EVENT_GROUPS = [` and the matching `];`.
    m = re.search(
        r"EVENT_GROUPS\s*:\s*Array<[^>]*>\s*=\s*\[(.*?)\];",
        src,
        re.DOTALL,
    )
    assert m, "could not locate EVENT_GROUPS definition"
    groups_body = m.group(1)
    grouped = set(re.findall(r"'([a-z_]+)'", groups_body))

    backend_events = set(EVENT_REGISTRY.keys())

    # Orphan fallback presence is the other branch — confirm it exists
    # in the file (so unmapped events still render).
    has_orphan_fallback = "auto-detected" in src and "orphans" in src

    missing = backend_events - grouped
    if missing and not has_orphan_fallback:
        raise AssertionError(
            f"backend events not in any EVENT_GROUPS and no orphan fallback: "
            f"{sorted(missing)}"
        )

    # Even with the fallback, surface a soft warning list — useful so
    # devs know which events fell through to the catch-all and might
    # deserve their own labeled group.
    if missing:
        print(
            "\n[notice] events relying on auto-orphan fallback "
            "(consider adding to EVENT_GROUPS for clarity):\n  - "
            + "\n  - ".join(sorted(missing))
        )


def test_critical_events_are_grouped_explicitly():
    """Soft contract: the Claude Auto-Runner and backfill events the user
    flagged should live in their own dedicated groups, NOT just the
    orphan fallback. Locks the fix from regressing if someone refactors
    EVENT_GROUPS."""
    panel_path = (
        Path(__file__).resolve().parents[2]
        / "frontend/src/components/NotificationSettingsPanel.tsx"
    )
    src = panel_path.read_text(encoding="utf-8")
    m = re.search(
        r"EVENT_GROUPS\s*:\s*Array<[^>]*>\s*=\s*\[(.*?)\];",
        src,
        re.DOTALL,
    )
    grouped = set(re.findall(r"'([a-z_]+)'", m.group(1)))

    must_be_explicit = {
        # The original report
        "external_runner_claimed",
        "external_runner_completed",
        "external_runner_failed",
        "external_runner_retry_after_partial_verify",
        "external_runner_max_retries_or_regressed",
        "claude_runner_enable_attempt",
        "claude_runner_disabled",
        # Auto backfill we just added
        "backfill_ac_needed",
        "backfill_ac_completed",
    }
    missing = must_be_explicit - grouped
    assert not missing, (
        f"these critical events must be in EVENT_GROUPS explicitly so the "
        f"user can find them: {sorted(missing)}"
    )
