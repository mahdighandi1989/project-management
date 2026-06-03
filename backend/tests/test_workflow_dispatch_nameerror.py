"""🚨 NameError regression: rebuild_project_index's workflow_dispatch hook
crashed silently for weeks.

What the user observed
======================
Render backend logs showed this warning EVERY time a task got pushed:

    workflow_dispatch hook crashed: name 'task' is not defined

Effect: the Claude Auto-Runner workflow was effectively NEVER triggered
through the normal path (task added / index rebuilt). The only paths that
still fired Claude were:
  1. The recovery sweeper (`_sweep_pending_external_verifies`) — which
     retriggers verify-then-chain for tasks where verify-after-complete
     was lost. This is why the user saw the SAME task repeatedly: the
     sweeper kept resurrecting it.
  2. Manual disable→enable cycles, which re-fire the dispatch through
     a different code path.

Tasks could never make forward progress through the auto-runner because
new tasks never got their initial workflow trigger.

Root cause
==========
In `rebuild_project_index(tasks, watched, *, token)`, the parameter is
`tasks` (a list). The workflow_dispatch hook at line 486 called
`pick_model_for_task(task)` — singular `task` — which doesn't exist
in this scope. Python raised NameError, caught by the surrounding
try/except, which only logged a warning. workflow_dispatch never ran.

Fix
===
Pull the next task from the sorted `pickable` index — that's the same
task Claude /next will pick — and pass that to `pick_model_for_task`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_rebuild_project_index_does_not_reference_undefined_task():
    """🚨 The exact regression. The body of `rebuild_project_index` must
    not contain `pick_model_for_task(task)` with a bare `task` name —
    that's the typo that broke auto-runner."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/prompt_github_sync.py"
    )
    src = src_path.read_text(encoding="utf-8")
    # Find the function body.
    idx = src.find("async def rebuild_project_index(")
    assert idx != -1, "rebuild_project_index not found — test stale"
    # Slice to the next top-level function.
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    if nxt == -1:
        nxt = rest.find("\ndef ")
    body = rest if nxt == -1 else rest[:nxt]
    # Direct check: no NON-COMMENT line should call pick_model_for_task(task).
    # The fix's explanatory comment quotes the bad form to document the
    # bug — that's fine. We only care about actual code lines.
    code_lines = [
        ln for ln in body.splitlines()
        if "pick_model_for_task(task)" in ln
        and not ln.strip().startswith("#")
        and "`" not in ln  # markdown-quoted in comments
    ]
    assert code_lines == [], (
        "rebuild_project_index has an executable call to "
        "pick_model_for_task(task) — `task` is undefined in that scope. "
        f"Bad lines: {code_lines}"
    )
    # And the fix must call pick_model_for_task with a derived task.
    assert "pick_model_for_task" in body, (
        "the call to pick_model_for_task must remain — only the argument fixed"
    )


def test_rebuild_project_index_picks_first_pickable_for_model():
    """The fix derives the next task from the sorted `pickable` index.
    Lock the wiring so future refactors don't accidentally drop it back
    to passing a bare list / undefined name."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/prompt_github_sync.py"
    )
    src = src_path.read_text(encoding="utf-8")
    idx = src.find("async def rebuild_project_index(")
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    # Must derive next_task_id from pickable.
    assert 'pickable[0]["task_id"]' in body, (
        "fix must derive next_task_id from pickable[0]"
    )
    # And must look up the task object in the tasks list (not blind cast).
    assert "for t in tasks" in body or "next(" in body, (
        "fix must walk the tasks parameter to find the actual task object"
    )


def test_rebuild_project_index_handles_empty_pickable():
    """If no tasks are pickable, model picking must short-circuit to
    None instead of crashing on pickable[0]."""
    src_path = (
        Path(__file__).resolve().parents[1]
        / "app/services/prompt_github_sync.py"
    )
    src = src_path.read_text(encoding="utf-8")
    idx = src.find("async def rebuild_project_index(")
    rest = src[idx + 1:]
    nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    # The pickable-empty guard must exist.
    assert "if pickable" in body, (
        "fix must guard against empty pickable before indexing pickable[0]"
    )
