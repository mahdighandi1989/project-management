"""🐛 Auto-runner silent-stop fix — apply_followup_after_verify max-rounds.

User report (verbatim, Persian):
  > یه تسک ایجاد کردم، و از اونجایی که قبلا دکمه اجرای خودکار روشن بود،
  > بعد از دقایقی شروع کرد به کار شدن روش از طریق توکن کلاد از اکشن
  > متوجه شدم چند دور روش کار شد ولی بعدش تا الایگه کاری روش انجام نشده
  > یعنی چند ساعته که گویا پرونده ش رو بسته دون اینکه کارش تموم شده باشه
  > یا ارشیو شده باشه یا تو فولدر تودو بخواد اپدیت کنه ...

Translation: a task ran ~9 auto-rounds via Claude Code action, then stopped
silently for hours — no archive, no TODO file, no Telegram notification —
even though the checklist showed 0/6 done and lots of work left.

Root cause — `apply_followup_after_verify` else-branch when
`max_auto_loop_rounds` is reached only did `logger.info(...)`. No mutation,
no cleanup. Task stayed in whatever status it was (commonly
`applied_externally_pending_verify` or `awaiting_review`), held the verify
lock, and the user had no signal anything was wrong.

Reference for the correct cleanup is `external_prompts._verify_then_chain`
action=`max_retries_todo` (lines ~674-708): write TODO + archive task +
release lock + emit notification.

The fix mirrors that cleanup inside `apply_followup_after_verify`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Source-level pins — the fix is a code-shape change inside a single block.
# Behavioral tests would require mocking GitHub API + notification service;
# source pins are cheaper and catch regressions just as well.
# ---------------------------------------------------------------------------


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


def test_max_rounds_branch_no_longer_only_logs():
    """The else-branch when `max_auto_loop_rounds` is reached must NOT be a
    silent log-and-continue. It must trigger cleanup (archive + TODO +
    notification). We pin the presence of the cleanup trigger flag."""
    body = _slice_apply_followup_body()

    assert "_trigger_max_rounds_cleanup" in body, (
        "apply_followup_after_verify must set a max-rounds cleanup flag "
        "so the post-lock block can archive + write TODO + notify. "
        "Without this flag the function silently stops the task in limbo "
        "(reported by user: 9 rounds ran, then no archive / no TODO / "
        "no Telegram for hours)."
    )

    # The flag must be set in the max-rounds branch
    assert "_trigger_max_rounds_cleanup = True" in body


def test_max_rounds_cleanup_archives_with_correct_reason():
    """When max-rounds cleanup fires, the task must be archived with reason
    `auto_loop_max_rounds` (distinct from `max_retries` used by the other
    cleanup path in external_prompts) so the panel/reports can distinguish
    the two failure modes."""
    body = _slice_apply_followup_body()

    assert 'task.archived_reason = "auto_loop_max_rounds"' in body, (
        "max-rounds cleanup must archive with reason `auto_loop_max_rounds` "
        "so it's distinct from `max_retries` and `regressed`"
    )
    assert 'task.archived = True' in body
    assert 'task.status = "abandoned"' in body
    assert 'task.external_status = "abandoned"' in body


def test_max_rounds_cleanup_writes_todo_file():
    """User specifically called out the TODO folder not being updated. The
    cleanup must invoke `_write_todo_for_task` with the verify report so
    the user has a self-contained handoff document."""
    body = _slice_apply_followup_body()

    assert "_write_todo_for_task" in body, (
        "max-rounds cleanup must call _write_todo_for_task so the repo's "
        "TO-DO/ folder gets the partial-progress record"
    )
    # The verify_result shape passed in must include report fields the
    # TODO writer needs (done_parts, remaining_parts, next_actions,
    # confidence_score, evidence) — pin a couple to lock the shape.
    assert "remaining_parts" in body
    assert "done_parts" in body
    assert "next_actions" in body


def test_max_rounds_cleanup_releases_verify_lock():
    """Without releasing the verify-lock, subsequent auto-runner dispatches
    on the same watched project are blocked by `verify_in_progress`."""
    body = _slice_apply_followup_body()

    assert "_release_verify_lock" in body, (
        "max-rounds cleanup must release the watched verify-lock — "
        "otherwise the project is permanently stuck in 'verify in progress'"
    )


def test_max_rounds_cleanup_emits_notification():
    """User must be told via Telegram that the auto-loop hit its cap and
    that manual intervention is required. Use the same notification helper
    as external_prompts._verify_then_chain for consistent UX."""
    body = _slice_apply_followup_body()

    assert "_emit_runner_notification" in body, (
        "max-rounds cleanup must emit a runner notification so the user "
        "knows the auto-loop stopped (user explicitly reported no "
        "Telegram message arrived for hours after silent stop)"
    )
    # The notification event must match the one used for max-retries in
    # external_prompts — the notification_service treats them the same.
    assert "external_runner_max_retries_or_regressed" in body


def test_max_rounds_cleanup_runs_outside_main_lock():
    """`_write_todo_for_task` calls the GitHub API (3-10s). Holding the
    service lock during a long network call would block every other
    operation (UI list, status, other verifies). The cleanup must run
    AFTER the main `self._save_tasks()` and release the outer lock first."""
    body = _slice_apply_followup_body()

    # The cleanup block must be after the outer `self._save_tasks()` and at
    # function-body indentation (8 spaces — outside the `async with`).
    cleanup_marker = "if _trigger_max_rounds_cleanup"
    assert cleanup_marker in body
    line = next(
        ln for ln in body.splitlines()
        if cleanup_marker in ln and "=" not in ln.split(cleanup_marker)[0]
    )
    # Leading whitespace count
    indent = len(line) - len(line.lstrip())
    assert indent == 8, (
        f"max-rounds cleanup must be at method-body indent (8 spaces) "
        f"so it runs outside the outer `async with self._lock:` block. "
        f"Got indent={indent}. Holding the lock during the GitHub API "
        f"call would serialize the whole service."
    )


def test_max_rounds_cleanup_returns_to_skip_followup_apply():
    """After cleanup, the function should return — calling
    apply_followup_as_new_prompt on an abandoned/archived task would
    overwrite task.prompt with a followup that the user will never run.
    """
    body = _slice_apply_followup_body()

    # Find the cleanup block and check there's a `return` inside it before
    # the apply_followup_as_new_prompt call at the bottom.
    cleanup_idx = body.find("if _trigger_max_rounds_cleanup")
    apply_idx = body.find("apply_followup_as_new_prompt", cleanup_idx)
    assert cleanup_idx != -1 and apply_idx != -1
    between = body[cleanup_idx:apply_idx]
    assert "return" in between, (
        "max-rounds cleanup block must `return` so the function does NOT "
        "fall through to apply_followup_as_new_prompt — that would "
        "overwrite task.prompt with a stale followup for an already-"
        "abandoned task"
    )


def test_initial_flag_value_is_false():
    """`_trigger_max_rounds_cleanup` must be initialized to False BEFORE
    the try-block so that if the try raises before assignment, the
    post-lock `if` doesn't blow up with NameError."""
    body = _slice_apply_followup_body()
    assert "_trigger_max_rounds_cleanup = False" in body, (
        "flag must be pre-initialized to False so an exception inside "
        "the auto-loop try-block doesn't leave it unbound"
    )


def test_pending_branch_still_works():
    """Regression guard: the existing happy path (round < max_rounds →
    status=pending → next_run_at=now) must still be intact."""
    body = _slice_apply_followup_body()
    assert 'task.status = "pending"' in body
    assert "task.next_run_at = now_iso()" in body
    assert "max_rounds = int(getattr(watched" in body
