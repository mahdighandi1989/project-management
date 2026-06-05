"""🚨 prompt-sync backlog drain caused backend OOM/timeout

After the streak-bypass fix deployed (8547436), the auto-runner started
correctly archiving many tasks that had been stuck in "partial" status.
Each archive set updated_at=now, marking the task dirty for GitHub
prompt-sync. Result: a backlog of ~hundreds of archived tasks flooding
the prompt-sync dispatcher.

Render logs showed:
  prompt-sync: dispatched 1 task(s) to 1 project(s)
  prompt-sync ✓ task=... repo=.../archive/...
…every 2-5 seconds for 5+ minutes, until `Shutting down` at 17:33:42
(the instance couldn't keep up with /health within 10s window).

Two fixes:

1. Stop re-syncing archived tasks that are already in archive/.
   Once archived → first sync sets github_prompt_archived=True. After
   that, future updated_at bumps (verifier housekeeping, state
   reconciliation) should NOT re-push the same content to the same
   path. They will if some genuine state changes that matters — but
   we trust the caller to clear github_prompt_synced_at then.

2. Cap dispatches per save event. Even with the archive skip, if 100+
   tasks become dirty in a single save (e.g., bulk import), firing
   100 parallel GitHub API calls saturates the free-tier instance and
   triggers the same OOM/timeout pattern. Sort by execution_priority
   and dispatch only the top N (5) per cycle. The rest drain on the
   next save event.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Archive-already-synced is not dirty
# ---------------------------------------------------------------------------


def _make_service():
    from app.services.oversight_service import OversightService

    svc = OversightService.__new__(OversightService)
    svc._inflight_sync_tasks = set()
    return svc


def test_archived_and_synced_task_is_not_dirty():
    """Once a task is archived AND first-synced to archive/, future
    updated_at bumps must NOT re-trigger sync. The backlog drain caused
    backend overload — we don't want that recurring."""
    svc = _make_service()
    task = SimpleNamespace(
        id="t1",
        archived=True,
        github_prompt_archived=True,
        github_prompt_synced_at="2026-06-03T16:00:00Z",
        updated_at="2026-06-03T17:00:00Z",  # newer than synced — would normally be dirty
    )
    assert svc._is_task_dirty(task) is False


def test_archived_but_not_yet_archive_synced_is_dirty():
    """A task that was JUST archived (status flipped, but not yet pushed
    to archive/ folder) must still be dirty for that first push."""
    svc = _make_service()
    task = SimpleNamespace(
        id="t2",
        archived=True,
        github_prompt_archived=False,  # not yet moved to archive/
        github_prompt_synced_at="2026-06-03T16:00:00Z",
        updated_at="2026-06-03T17:00:00Z",
    )
    assert svc._is_task_dirty(task) is True


def test_archived_never_synced_is_dirty():
    """Edge case: task archived but never synced at all — must be dirty
    so we push it."""
    svc = _make_service()
    task = SimpleNamespace(
        id="t3",
        archived=True,
        github_prompt_archived=False,
        github_prompt_synced_at=None,
        updated_at="2026-06-03T17:00:00Z",
    )
    assert svc._is_task_dirty(task) is True


def test_active_task_with_newer_updated_is_dirty():
    """Active tasks (not archived) follow the normal updated_at > synced_at rule."""
    svc = _make_service()
    task = SimpleNamespace(
        id="t4",
        archived=False,
        github_prompt_archived=False,
        github_prompt_synced_at="2026-06-03T16:00:00Z",
        updated_at="2026-06-03T17:00:00Z",
    )
    assert svc._is_task_dirty(task) is True


def test_active_task_in_flight_is_not_dirty():
    """Inflight prevention still works for active tasks."""
    svc = _make_service()
    svc._inflight_sync_tasks.add("t5")
    task = SimpleNamespace(
        id="t5",
        archived=False,
        github_prompt_archived=False,
        github_prompt_synced_at=None,
        updated_at="2026-06-03T17:00:00Z",
    )
    assert svc._is_task_dirty(task) is False


# ---------------------------------------------------------------------------
# Throttle: max dispatches per tick
# ---------------------------------------------------------------------------


def test_throttle_marker_present_in_source():
    """Static source check — the dispatcher must cap per-tick dispatches.
    Without the cap, 100+ dirty tasks all fire parallel GitHub API calls
    and saturate the free-tier instance.

    We pin the cap value (5) so a refactor doesn't accidentally lift it
    to 50 or 100."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    )
    src = src_path.read_text(encoding="utf-8")
    assert "_MAX_DISPATCH_PER_TICK" in src, (
        "dispatcher must have a per-tick cap (was missing → OOM)"
    )
    assert "_MAX_DISPATCH_PER_TICK = 5" in src, (
        "cap value must stay at 5 — higher saturates Render free tier"
    )
    # The cap must actually be applied (syncable list trimmed). The
    # variable was renamed from `dirty` to `syncable` when the
    # eligibility filter was hoisted above the throttle.
    assert (
        "syncable[:_MAX_DISPATCH_PER_TICK]" in src
        or "dirty[:_MAX_DISPATCH_PER_TICK]" in src
    ), (
        "cap must trim the dispatch list, not just be defined"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🚨 Throttle-eligibility regression: user-reported bug
# ─────────────────────────────────────────────────────────────────────────────


def test_throttle_picks_only_from_syncable_tasks():
    """🚨 User reported: 'چند تا تسک رو باز تولید زدم و همینطور بوک
    وریفای تلفیق کردم، ولی تو فولدر گیتهاب آپدیت نشده.'

    Root cause: previous dispatcher sorted ALL dirty tasks by
    execution_priority and took top N. If the top N happened to have
    missing watched or prompt_sync_enabled=False, the cycle
    dispatched ZERO tasks even when there were perfectly-syncable
    tasks waiting (just at lower priority).

    The fix partitions dirty into syncable+skipped BEFORE the throttle,
    so the throttle window always contains real candidates.

    Source-level guard: the eligibility filter (watched + sync_enabled
    check) must happen BEFORE the throttle (dispatch cap)."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    )
    src = src_path.read_text(encoding="utf-8")
    idx_dirty = src.find("dirty: List[\"OversightTask\"] = []")
    assert idx_dirty != -1, "dirty list construction must exist"
    # Locate the throttle and the eligibility check
    idx_throttle = src.find("_MAX_DISPATCH_PER_TICK", idx_dirty)
    idx_eligibility = src.find('"prompt_sync_enabled", True', idx_dirty)
    assert idx_throttle != -1 and idx_eligibility != -1
    assert idx_eligibility < idx_throttle, (
        "eligibility check (watched + prompt_sync_enabled) must happen "
        "BEFORE the per-tick throttle so the throttle window is always "
        "filled with real candidates. Otherwise top-priority tasks with "
        "missing watched silently consume the dispatch budget and lower-"
        "priority syncable tasks never get a turn."
    )


def test_throttle_logs_breakdown_of_skipped_reasons():
    """The diagnostic log when ALL dirty tasks are skipped must
    distinguish 'no watched' from 'sync_disabled' so the user can tell
    whether their problem is orphaned tasks vs disabled projects."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    )
    src = src_path.read_text(encoding="utf-8")
    assert "no_watched=" in src, (
        "diagnostic log must break out 'no_watched=N' so the user can "
        "distinguish orphaned tasks from disabled projects"
    )
    assert "sync_disabled=" in src
