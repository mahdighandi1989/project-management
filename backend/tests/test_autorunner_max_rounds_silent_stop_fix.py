"""🐛 Auto-runner silent-stop fix v2 — threshold + max-rounds cleanup.

User reports (in chronological order):

  v1 report (silent stop): task ran ~9 auto-rounds via Claude Code action,
    then stopped silently for hours — no archive, no TODO file, no Telegram
    notification — even though the checklist showed 0/6 done.

  v2 refinement: "archiving should NOT happen just because we hit max_rounds
    with an incomplete checklist. First check after every verify if the
    checklist crossed a threshold (e.g., 90%) — if yes, archive + write
    remaining items to TODO. ONLY if 6 attempts pass without crossing the
    threshold, force-archive (same as clicking the archive button on the
    card) and write remaining to TODO."

Two trigger conditions for cleanup:

  1. ratio_threshold — `done_parts / (done_parts + remaining_parts) >= 0.90`
     fires on ANY verify (even round 2). Verifier hard-guard only archives
     when remaining=0 (100%). This layer sits above it and accepts 90% as
     "good enough", routing the remaining 10% to the TO-DO/ folder.

  2. max_rounds — `followup_round >= max_auto_loop_rounds (6)`. Force-archive
     mirroring the archive button on the card. Distinct archived_reason so
     the panel can distinguish the two failure modes.

In BOTH cases:
  - TODO file written to repo (`TO-DO/todo-task-<id>.md`)
  - Task archived with `archived_reason` tagging the cause
  - Verify-lock released on the watched project
  - Telegram notification with reason-specific message
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _slice_apply_followup_body() -> str:
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def apply_followup_after_verify")
    assert idx != -1, "apply_followup_after_verify not found"
    rest = src[idx + 1:]
    nxt = rest.find("\n    async def ")
    return rest if nxt == -1 else rest[:nxt]


def test_cleanup_flag_present():
    """The function must set a generic cleanup flag (no longer only
    triggered by max-rounds)."""
    body = _slice_apply_followup_body()
    assert "_trigger_cleanup" in body, (
        "apply_followup_after_verify must set _trigger_cleanup flag "
        "for the post-lock block to archive + write TODO + notify"
    )


def test_two_distinct_cleanup_reasons():
    """Cleanup must distinguish ratio_threshold vs max_rounds so panel/
    reports can show why the task was abandoned."""
    body = _slice_apply_followup_body()
    assert 'ratio_threshold' in body, (
        "cleanup must support a ratio_threshold reason (≥90% done → archive)"
    )
    assert '"max_rounds"' in body or "'max_rounds'" in body, (
        "cleanup must support a max_rounds reason (6 attempts → force-archive)"
    )
    assert '"auto_loop_ratio_met"' in body, (
        "archived_reason `auto_loop_ratio_met` must be used for threshold case"
    )
    assert '"auto_loop_max_rounds"' in body, (
        "archived_reason `auto_loop_max_rounds` must be used for force case"
    )


def test_ratio_uses_done_over_total():
    """The threshold must be computed as done / (done + remaining) so it
    reflects actual progress, not absolute counts."""
    body = _slice_apply_followup_body()
    assert "_done_n" in body and "_rem_n" in body
    assert "_total = _done_n + _rem_n" in body
    assert "_done_n / _total" in body


def test_ratio_threshold_default_is_90_percent():
    """User specified 90%. Pin both the Watched field default and the local
    fallback in apply_followup_after_verify."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    ).read_text(encoding="utf-8")
    assert "auto_archive_done_ratio: float = 0.90" in src, (
        "Watched.auto_archive_done_ratio must default to 0.90 (90%)"
    )
    body = _slice_apply_followup_body()
    assert "0.90" in body, "fallback threshold must be 0.90"


def test_max_rounds_default_is_six():
    """User specified 6. Pin both Watched field and local fallback."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    ).read_text(encoding="utf-8")
    assert "max_auto_loop_rounds: int = 6" in src, (
        "Watched.max_auto_loop_rounds default must be 6 (user requested)"
    )
    body = _slice_apply_followup_body()
    assert 'getattr(watched, "max_auto_loop_rounds", 5)' not in body, (
        "stale fallback to 5 must be updated to 6"
    )


def test_ratio_check_runs_before_max_rounds_check():
    """Critical ordering: ratio_threshold must be checked FIRST so that a
    task hitting 90% in round 3 is archived cleanly via ratio_threshold,
    not silently kept running until round 6 and then force-archived."""
    body = _slice_apply_followup_body()
    ratio_idx = body.find('_cleanup_reason = "ratio_threshold"')
    rounds_idx = body.find('_cleanup_reason = "max_rounds"')
    assert ratio_idx != -1 and rounds_idx != -1
    assert ratio_idx < rounds_idx, (
        "ratio_threshold must be checked BEFORE max_rounds — otherwise a "
        "task at 95% done in round 3 keeps running until round 6"
    )


def test_pending_branch_still_works_when_below_threshold_and_under_limit():
    """The middle case (ratio < 90% AND round < 6) must still send the task
    back to pending so the next auto-runner tick picks it up."""
    body = _slice_apply_followup_body()
    assert 'task.status = "pending"' in body
    assert "task.next_run_at = now_iso()" in body
    assert "elif (task.followup_round or 0) < max_rounds" in body


def test_cleanup_calls_write_todo():
    """User explicitly demanded remaining items → TO-DO/ folder."""
    body = _slice_apply_followup_body()
    assert "_write_todo_for_task" in body
    assert "remaining_parts" in body and "done_parts" in body
    assert "next_actions" in body


def test_cleanup_archives_and_abandons_task():
    """User said force-archive mirrors the card archive button."""
    body = _slice_apply_followup_body()
    assert "task.archived = True" in body
    assert 'task.status = "abandoned"' in body
    assert 'task.external_status = "abandoned"' in body


def test_cleanup_releases_verify_lock():
    body = _slice_apply_followup_body()
    assert "_release_verify_lock" in body, (
        "must release verify-lock so other dispatches aren't blocked"
    )


def test_cleanup_emits_notification_with_reason_specific_message():
    body = _slice_apply_followup_body()
    assert "_emit_runner_notification" in body
    assert "external_runner_max_retries_or_regressed" in body
    assert "حد نصاب ۹۰٪" in body, (
        "Telegram message for ratio_threshold path must mention threshold"
    )
    assert "سقف ۶ تلاش" in body, (
        "Telegram message for max_rounds path must mention attempts cap"
    )


def test_cleanup_runs_outside_main_lock():
    """`_write_todo_for_task` is a 3-10s GitHub API call. Holding the
    service lock during that serializes the whole oversight service."""
    body = _slice_apply_followup_body()
    cleanup_marker = "if _trigger_cleanup and watched is not None:"
    assert cleanup_marker in body
    line = next(
        ln for ln in body.splitlines()
        if cleanup_marker in ln
    )
    indent = len(line) - len(line.lstrip())
    assert indent == 8, (
        f"cleanup must be at method-body indent (8 spaces), got {indent}. "
        f"Holding self._lock during GitHub API call serializes the service."
    )


def test_cleanup_returns_to_skip_followup_apply():
    """After cleanup, function must return — calling
    apply_followup_as_new_prompt on an abandoned task overwrites task.prompt
    with a followup the user will never run."""
    body = _slice_apply_followup_body()
    cleanup_idx = body.find("if _trigger_cleanup")
    apply_idx = body.find("apply_followup_as_new_prompt", cleanup_idx)
    assert cleanup_idx != -1 and apply_idx != -1
    between = body[cleanup_idx:apply_idx]
    assert "return" in between, (
        "cleanup block must return — otherwise the function falls through "
        "to apply_followup_as_new_prompt on an already-abandoned task"
    )


def test_cleanup_flags_initialized_before_try():
    """Flags must be pre-initialized so an exception inside the try-block
    doesn't leave them unbound."""
    body = _slice_apply_followup_body()
    assert "_trigger_cleanup = False" in body
    assert '_cleanup_reason = ""' in body
    assert "_cleanup_ratio = 0.0" in body


def test_ratio_zero_total_does_not_trigger_archive():
    """If total = 0 (verifier returned empty done AND empty remaining), the
    ratio is undefined. We must NOT trigger ratio_threshold cleanup — fall
    through to max_rounds check or pending."""
    body = _slice_apply_followup_body()
    assert "_total > 0 and _cleanup_ratio >= ratio_threshold" in body, (
        "must guard ratio check with _total > 0 — otherwise a verify with "
        "no parts at all would archive on ratio=0.0 >= 0 spuriously"
    )
