"""🚨 Auto-runner infinite loop fix — followup_round increment was conditional.

User reported in Telegram screenshots:
  > verify=partial. retry 1/3.
  > verify=partial. retry 1/3.
  > verify=partial. retry 1/3.
  ...for the SAME task, over and over. The counter never advanced
  past 1/3 even though Claude was completing the task and getting
  partial verifies multiple times.

Net effect:
  - max_retries (default 3) never reached
  - max_retries_todo never triggered
  - TODO file never written
  - task never archived as "abandoned"
  - same checklist appeared in Telegram every cycle
  - Gemini key budget burning, Claude OAuth subscription wasting calls

Root cause — `apply_followup_after_verify` at oversight_service.py:9197+:

  try:
      new_prompt = await self.generate_followup_prompt_for_task(...)
  except Exception:
      new_prompt = None

  if not new_prompt:
      return        # ⚠️ EARLY EXIT — followup_round NEVER incremented

  # ... lots of work ...

  task.followup_round = (task.followup_round or 0) + 1  # only reached if new_prompt

When generate_followup_prompt_for_task fails (timeout, AI cap, ratelimit),
or returns empty, the function returns BEFORE incrementing
followup_round. Subsequent verifies see followup_round=0 →
retries_done=0 → notification says "retry 1/3" forever.

The fix: always increment followup_round on partial, even when the
prompt regeneration fails. This guarantees max_retries is honored
and the task eventually archives with a TODO file.

Secondary fix: the no-progress guard's `_last_remaining_snapshot`
was stored via setattr (lazy attr, not a dataclass field), so it
didn't persist across restarts. Now it also reads from
service.reports as a fallback so the guard works after a backend
restart.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Source-level pins
# ---------------------------------------------------------------------------


def test_apply_followup_increments_round_even_on_prompt_failure():
    """🚨 The critical fix. apply_followup_after_verify must increment
    followup_round on partial even when generate_followup_prompt fails.
    Otherwise retries_done stays at 0 forever and the runner loops."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/services/oversight_service.py"
    ).read_text(encoding="utf-8")
    idx = src.find("async def apply_followup_after_verify")
    assert idx != -1
    # Slice to next async def
    rest = src[idx + 1:]
    nxt = rest.find("\n    async def ")
    body = rest if nxt == -1 else rest[:nxt]

    # The early-return branch must include the increment.
    assert "if not new_prompt:" in body
    # Look for the increment near the early return.
    early_return_idx = body.find("if not new_prompt:")
    assert early_return_idx != -1
    early_return_window = body[early_return_idx:early_return_idx + 1500]
    assert "task.followup_round = (task.followup_round or 0) + 1" in early_return_window, (
        "the early-return branch (when new_prompt generation fails) must "
        "increment followup_round; otherwise the retry counter loops at 0"
    )
    assert "prevents infinite retry loop" in early_return_window, (
        "fix must include the comment explaining why — easy for the next "
        "reader to understand the intent"
    )


def test_remaining_unchanged_reads_service_reports_when_snapshot_missing():
    """The no-progress guard's `_last_remaining_snapshot` is a lazy
    attr that doesn't persist across restarts. The function must also
    consult service.reports so the guard survives a restart."""
    src = (
        Path(__file__).resolve().parents[1]
        / "app/api/routes/external_prompts.py"
    ).read_text(encoding="utf-8")
    idx = src.find("def _remaining_unchanged(")
    assert idx != -1
    # Slice to next top-level def
    rest = src[idx + 1:]
    nxt = rest.find("\ndef ")
    if nxt == -1:
        nxt = rest.find("\nasync def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert "service.reports" in body or "service, 'reports'" in body \
        or "getattr(service, \"reports\"" in body, (
        "_remaining_unchanged must read from service.reports when the "
        "in-memory snapshot is absent — otherwise the no-progress guard "
        "breaks after a backend restart"
    )


def test_remaining_unchanged_signature_accepts_service():
    """The helper must accept a `service` parameter so the caller can
    pass the oversight service for the reports lookup."""
    from app.api.routes.external_prompts import _remaining_unchanged
    import inspect

    sig = inspect.signature(_remaining_unchanged)
    assert "service" in sig.parameters
    # Backward-compat: default None so older callers don't break
    assert sig.parameters["service"].default is None


# ---------------------------------------------------------------------------
# Behavioral pins
# ---------------------------------------------------------------------------


def test_remaining_unchanged_with_persistent_report(monkeypatch):
    """Snapshot is missing on the task (e.g., post-restart). But the
    service.reports has the previous remaining_parts. _remaining_unchanged
    must use the report's remaining_parts as the comparison baseline."""
    from app.api.routes.external_prompts import _remaining_unchanged

    task = SimpleNamespace(id="task_x")  # no _last_remaining_snapshot
    # Service has a previous report with the same remaining items
    prev_report = SimpleNamespace(
        task_id="task_x",
        generated_at="2026-06-04T10:00:00Z",
        remaining_parts=["item a", "item b", "item c"],
    )
    service = SimpleNamespace(reports=[prev_report])

    # Current verify finds the same 3 items → no progress
    result = _remaining_unchanged(
        ["item a", "item b", "item c"], task, service,
    )
    assert result is True, (
        "guard must detect no-progress using the persisted report when "
        "the in-memory snapshot is missing"
    )


def test_remaining_unchanged_no_service_no_snapshot_returns_false():
    """If neither snapshot nor reports are available, we can't compare —
    must return False (don't block legitimate retries)."""
    from app.api.routes.external_prompts import _remaining_unchanged

    task = SimpleNamespace(id="t1")
    result = _remaining_unchanged(["a", "b"], task, None)
    assert result is False


def test_remaining_unchanged_detects_progress_via_reports(monkeypatch):
    """If the service has a previous report with 5 items and current has
    3 (real progress), the guard must NOT mark it as no-progress."""
    from app.api.routes.external_prompts import _remaining_unchanged

    task = SimpleNamespace(id="task_y")
    prev_report = SimpleNamespace(
        task_id="task_y",
        generated_at="2026-06-04T10:00:00Z",
        remaining_parts=["a", "b", "c", "d", "e"],
    )
    service = SimpleNamespace(reports=[prev_report])

    # Now only 3 of the original 5 remain → Jaccard = 3/5 = 0.6 < 0.85
    result = _remaining_unchanged(["a", "b", "c"], task, service)
    assert result is False, (
        "real progress (5 → 3 items) must NOT be flagged as no-progress"
    )
