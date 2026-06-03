"""🚨 Two regression tests pinned together because the user reported them
together: the auto-backfill button "stuck" forever, and the auto-runner
verify-loop.

Bug 1 — Stuck Phase 3 button
============================
The dashboard ran `/runtime/diagnostics` over ALL tasks (including
archived). It would happily report "2 تسک نیاز به Phase 3" — for tasks
that were already archived weeks ago. Meanwhile `_maybe_auto_backfill_ac`
(the scheduler-driven auto-trigger) correctly skipped archived tasks,
so its counter saw 0 and never fired. Net effect: the purple button
sat on the dashboard for "مدت‌هاست" while the scheduler stayed silent.

Fix: align the diagnostics counter with the trigger — both skip archived.

Bug 2 — Auto-runner retries even when verify says DONE
======================================================
The verifier requires `confirmation_streak >= streak_required` (default 2)
before flipping a task to `done` and archiving. On the first successful
verify, streak goes 0→1, condition fails, and the verifier writes
`verification_status = "partial"` — even though THIS run's raw verdict
was DONE. `_verify_then_chain` reads "partial" and calls `retry_same`,
which sends the task back to `pending` and triggers a new Claude run.
Claude redoes work that was already done. Second verify also DONE,
streak=2, archive. Net: one wasted Claude run per task + the user sees
the same checklist in Telegram twice.

Fix (two layers, defense-in-depth):
  1. Verifier: bypass the streak guard when `triggered_by` starts with
     "claude_auto_runner". Auto-runner already does the deepest verify
     possible (runtime probes + iterative orchestrator) — one pass is
     authoritative.
  2. _verify_then_chain: also short-circuit `retry_same` whenever the
     verifier's RAW verdict for this run was DONE, regardless of the
     mutated task.verification_status. This covers any path that
     might still hit the streak guard.

verify_task now also returns `status_val` so callers can distinguish
the raw verdict from the mutated task state.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Bug 1: diagnostics skips archived tasks
# ---------------------------------------------------------------------------


def test_diagnostics_excludes_archived_from_phase3_counter():
    """🚨 Regression. The Phase-3 counter on the dashboard must NOT
    include archived tasks. The auto-trigger excludes them; the
    counter that drives the button must match — otherwise the button
    is stuck on a positive number forever while the scheduler does
    nothing."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/oversight.py"
    )
    src = src_path.read_text(encoding="utf-8")
    # Locate the diagnostics counter loop.
    idx = src.find("ac_needing_phase3_upgrade = 0")
    assert idx != -1, "diagnostics counter not found — test stale"
    # The `for t in service.tasks:` block that immediately follows must
    # have an archived skip. We search the window after idx.
    window = src[idx:idx + 800]
    assert "for t in service.tasks:" in window
    assert 'if getattr(t, "archived", False):' in window, (
        "diagnostics phase3 counter must skip archived tasks — otherwise "
        "the purple button shows phantom work indefinitely"
    )
    # The skip must come BEFORE total_tasks += 1 to keep total accurate too.
    skip_pos = window.find('if getattr(t, "archived", False):')
    total_pos = window.find("total_tasks += 1")
    assert 0 < skip_pos < total_pos, (
        "archived skip must be before total_tasks counter"
    )


# ---------------------------------------------------------------------------
# Bug 2: verifier bypasses streak guard for auto-runner triggers
# ---------------------------------------------------------------------------


def test_verifier_source_bypasses_streak_for_auto_runner():
    """Static source check — when `triggered_by` starts with
    'claude_auto_runner', the streak-guard branch must be bypassed.

    We use a source-level check rather than a unit test because
    `verify_task` is 2000+ lines and depends on the full oversight
    service stack — too brittle to mock comprehensively."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_verifier.py"
    )
    src = src_path.read_text(encoding="utf-8")
    assert 'startswith("claude_auto_runner")' in src, (
        "verifier must check triggered_by.startswith('claude_auto_runner') "
        "to bypass streak guard"
    )
    assert "bypass_for_auto_runner" in src, (
        "bypass flag must be wired into the streak condition"
    )
    # The flag must appear in the OR chain that decides archive.
    # Find the streak check and verify the OR chain contains all three signals.
    streak_idx = src.find("task.confirmation_streak >= streak_required")
    assert streak_idx != -1
    window = src[streak_idx:streak_idx + 400]
    assert "bypass_streak" in window
    assert "bypass_for_auto_runner" in window, (
        "auto-runner bypass must be in the same OR chain as the streak check"
    )


def test_verify_task_returns_status_val():
    """The new field lets `_verify_then_chain` distinguish a verifier
    verdict of DONE from a task state mutated to partial by the streak
    guard. Without it, the chain can't tell the two apart."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_verifier.py"
    )
    src = src_path.read_text(encoding="utf-8")
    # Find the verify_task return block and assert status_val is in it.
    # Use the unique 'followup_round' key as an anchor.
    anchor = '"followup_round": task.followup_round,'
    idx = src.find(anchor)
    assert idx != -1, "return block anchor not found"
    window = src[idx:idx + 600]
    assert '"status_val":' in window, (
        "verify_task return must include status_val so callers can see "
        "the raw verdict separate from mutated task state"
    )


def test_verify_then_chain_short_circuits_on_raw_done():
    """🚨 The actual fix. `_verify_then_chain` must treat a raw verdict
    of DONE the same as task.verification_status=done — both lead to
    chain_next, neither leads to retry_same. Otherwise auto-runner
    burns a Claude run re-doing work that was already done."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/external_prompts.py"
    )
    src = src_path.read_text(encoding="utf-8")
    # Find the action decision block.
    idx = src.find("action = \"chain_next\"  # default")
    assert idx != -1, "decision block not found — test stale"
    window = src[idx:idx + 800]
    # The done-branch must check BOTH vstatus and status_val.
    assert "status_val" in window, (
        "_verify_then_chain must read status_val from verify_result"
    )
    assert 'status_val_this_run == "done"' in window or '"done"' in window
    # The retry_same branch must STILL exist for genuine partials.
    assert "retry_same" in window
