"""🚨 Sweeper loop fix — verify_task failures left task status stuck.

User screenshot showed 466+ workflow runs all "Cancelled" in GitHub
Actions for the language repo. The Render log explained why:

  10:09:18  verify ai_generate failed: [deepseek] Insufficient Balance
  10:09:22  _verify_then_chain: vstatus=applied_externally_pending_verify
            retries=0/3 → action=chain_next
  10:09:23  dispatched workflow (next task)

  10:10:01  sweeper: triggering verify-then-chain for SAME task (recovery)
  10:15:03  sweeper: triggering verify-then-chain for SAME task AGAIN

Two cascading bugs:

1. **Verifier early-return on AI failure didn't update task state.**
   When the verify AI call raised (DeepSeek balance, rate limit, etc.),
   verify_task at oversight_verifier.py:3468-3489 wrote an error
   OversightReport but never touched `task.verification_status`. The
   field stayed at `applied_externally_pending_verify` (the initial
   value set when Claude /complete fired). The sweeper polls for
   exactly that status and tries to recover.

2. **_verify_then_chain didn't handle `applied_externally_pending_verify`
   either.** The action mapping covered done/partial/regressed/error
   but not the leftover-initial-state case. Default was chain_next,
   which fired without touching the stuck status. So:

     verify AI fails →
       task.verification_status stays as applied_externally_pending_verify →
         chain_next fires (new workflow) →
           grace period elapses →
             sweeper sees stuck status →
               re-triggers _verify_then_chain →
                 LOOP

   The cancelled workflows were the in-flight Claude runs killed
   when chain_next dispatched a new run on top of them.

Both fixes land here:
  - Verifier's error path now sets task.verification_status="error"
    AND saves tasks. Sweeper no longer picks it up.
  - Verifier's error path now returns the full schema expected by
    `_verify_then_chain` (status_val, final, streak, etc.) so the
    caller doesn't crash on missing keys.
  - `_verify_then_chain` adds a defensive branch: if vstatus is still
    `applied_externally_pending_verify` after verify_task returned,
    that's a sure sign verify failed silently. Force status to "error"
    and chain_next. Belt-and-suspenders with fix #1.
  - The existing "error" branch now ALSO forces the status update,
    so any future path that leaves it stuck gets cleaned up.

This restores the auto-runner to a working state. With DeepSeek balance
empty (the user's actual condition), verify will keep falling through
the AI failure path, but tasks will be marked "error" and not loop.
The user gets a clean retry once they top up the AI budget or after
they manually re-verify.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _read(rel: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / rel
    ).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Verifier error path now sets task state and returns full schema
# ---------------------------------------------------------------------------


def test_verifier_error_path_sets_task_verification_status():
    """🚨 The critical fix. When the verify AI call fails, the early-
    return path must set task.verification_status to 'error' so the
    sweeper doesn't pick up the still-pending status and loop."""
    src = _read("app/services/oversight_verifier.py")
    idx = src.find('logger.exception("verify ai_generate failed")')
    assert idx != -1, "verify ai_generate failure block not found"
    # Slice forward to the return statement
    rest = src[idx:idx + 2000]
    assert 'task.verification_status = "error"' in rest, (
        "verify ai_generate failure must set task.verification_status = "
        "'error' before returning, or the sweeper will keep re-triggering "
        "verify on the stuck task"
    )
    assert "service._save_tasks()" in rest, (
        "fix must persist the status change to disk so sweeper actually "
        "sees the updated status on next tick"
    )


def test_verifier_error_path_returns_full_schema():
    """The error-path return value must include the keys that
    `_verify_then_chain` reads (`status_val`, `final`, etc.). If they're
    missing, the caller defaults to wrong values or crashes."""
    src = _read("app/services/oversight_verifier.py")
    idx = src.find('logger.exception("verify ai_generate failed")')
    assert idx != -1
    rest = src[idx:idx + 2500]
    for required_key in ('"status_val"', '"final"', '"streak"', '"followup_round"'):
        assert required_key in rest, (
            f"verifier error path must include {required_key} in the "
            f"return dict (consumed by _verify_then_chain)"
        )


# ---------------------------------------------------------------------------
# _verify_then_chain handles the leftover applied_externally_pending_verify
# ---------------------------------------------------------------------------


def test_verify_then_chain_handles_stuck_applied_externally_status():
    """🚨 Belt-and-suspenders. If vstatus is still
    `applied_externally_pending_verify` after verify_task returned,
    treat it as a verify failure: force status to 'error' and chain_next.
    Otherwise the sweeper loops."""
    src = _read("app/api/routes/external_prompts.py")
    # Find the action-mapping block in _verify_then_chain
    idx = src.find('action = "chain_next"  # default')
    assert idx != -1
    rest = src[idx:idx + 3000]
    assert 'vstatus == "applied_externally_pending_verify"' in rest, (
        "_verify_then_chain must handle applied_externally_pending_verify "
        "explicitly — otherwise it defaults to chain_next without clearing "
        "the stuck status and the sweeper loops"
    )
    # Must force the status update
    assert 'task.verification_status = "error"' in rest, (
        "the applied_externally_pending_verify branch must overwrite the "
        "stuck status so the sweeper doesn't re-trigger"
    )


def test_verify_then_chain_error_branch_also_persists_status():
    """The existing error branch is similarly defensive: when vstatus is
    already 'error' or verify_result contains _crash, persist the status
    update so any other path that left it inconsistent gets cleaned up."""
    src = _read("app/api/routes/external_prompts.py")
    idx = src.find('elif vstatus == "error" or "_crash" in verify_result:')
    assert idx != -1
    rest = src[idx:idx + 1000]
    assert 'task.verification_status = "error"' in rest


# ---------------------------------------------------------------------------
# Source-level: applied_externally_pending_verify must NOT silently default
# to chain_next anymore
# ---------------------------------------------------------------------------


def test_default_chain_next_no_longer_catches_stuck_status():
    """The default-chain_next was the silent failure. With the explicit
    branch in place, applied_externally_pending_verify cannot fall
    through to the default anymore."""
    src = _read("app/api/routes/external_prompts.py")
    # Find the action mapping and confirm there's an explicit branch
    # before the implicit default kicks in.
    idx = src.find('action = "chain_next"  # default')
    branch_idx = src.find('vstatus == "applied_externally_pending_verify"', idx)
    assert branch_idx != -1 and branch_idx > idx, (
        "explicit applied_externally_pending_verify branch must exist "
        "after the default declaration"
    )
