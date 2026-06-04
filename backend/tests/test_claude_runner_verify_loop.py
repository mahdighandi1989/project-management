"""Contract tests for the Claude Auto-Runner verify-after-complete pipeline.

The user repeatedly asked for these invariants to hold for both the
"اجرای خودکار" (auto-runner mode) and per-task "اجرا از طریق کلاد" button:

  1. Every time Claude calls /complete with agent_id=claude-code-action,
     the backend MUST acquire the verify lock and schedule
     _verify_then_chain. The post-complete hook fires regardless of
     whether the workflow was originally dispatched by the push hook
     (auto mode) or by the per-task button (manual mode), because the
     workflow itself always calls /complete with the same agent_id.

  2. While the lock is held, no other task can be auto-triggered
     (is_watched_verify_locked returns True, trigger_workflow_dispatch
     skips).

  3. _verify_then_chain's branching matches the user's requirement:
       verified=done                -> chain_next, release lock
       partial, retries < max       -> retry_same, push task back to pending
       partial, retries >= max      -> TODO file, release lock, chain_next
       regressed                    -> TODO file, release lock, chain_next

  4. retry_same re-dispatches the SAME task (target_task_id) with force,
     so a partial verify guarantees Claude works on that task again
     before any other.

The body of _verify_then_chain calls real services; we exercise the
decision tree directly via a thin harness that supplies fake tasks +
watched + verifier.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _AsyncLock:
    """Proper async context manager — `async with svc._lock:` returns immediately."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


# ---------------------------------------------------------------------------
# Hook trigger: every complete from claude-code-action acquires the verify lock
# ---------------------------------------------------------------------------


def test_post_complete_hook_fires_for_claude_code_action_agent_ids():
    """The hook in external_prompts.complete_prompt is gated on the agent_id
    set. The set must include the agent_id the workflow uses, otherwise
    the loop never runs."""
    import inspect

    from app.api.routes import external_prompts

    src = inspect.getsource(external_prompts.complete_prompt)
    # The workflow master prompt hard-codes agent_id="claude-code-action"
    # in /claim and /complete calls — that exact value MUST be matched.
    assert '"claude-code-action"' in src or "'claude-code-action'" in src


def test_workflow_master_prompt_uses_claude_code_action_agent_id():
    """The /complete call inside the workflow uses claude-code-action so the
    backend hook can recognise it."""
    from app.services.claude_runner_bootstrap import MASTER_PROMPT
    assert '"agent_id":"claude-code-action"' in MASTER_PROMPT


# ---------------------------------------------------------------------------
# Verify-lock blocks dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_workflow_dispatch_is_skipped_while_verify_lock_held():
    """While backend is verifying the just-completed task, no new dispatch
    should fly — even if a push happens or the user clicks "اجرا از طریق
    کلاد" on another task."""
    from app.services import claude_runner_bootstrap as crb

    watched = SimpleNamespace(
        id="w1",
        repo_full_name="owner/repo",
        github_repo="owner/repo",
        claude_runner_enabled=True,
        claude_runner_workflow_path=".github/workflows/claude-auto-task-runner.yml",
        claude_runner_verifying_task_id="task-being-verified",
    )

    fake_ovs = SimpleNamespace(
        is_watched_verify_locked=lambda _id: _id == "w1",
    )

    with patch("app.services.oversight_service.get_oversight_service", return_value=fake_ovs):
        result = await crb.trigger_workflow_dispatch(
            watched,
            gh_token="ghp_x",
            target_task_id="some-other-task",
        )
    assert result["success"] is True
    assert result["skipped"] is True
    assert result["reason"] == "verify_in_progress"
    assert result["locked_task_id"] == "task-being-verified"


# ---------------------------------------------------------------------------
# _verify_then_chain decision tree
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_then_chain_done_releases_lock_and_chains_next():
    from app.api.routes import external_prompts

    class _Task(SimpleNamespace):
        def __init__(self, **kw):
            super().__init__(**kw)

    task = _Task(
        id="t1", watched_id="w1", title="x", raw_idea="", prompt="x",
        verification_status="done", followup_round=0,
        external_status="done", status="done",
        external_locked_by=None, external_lease_until=None,
    )

    released = {"flag": False}
    dispatched = {"args": None}

    class _Svc:
        def __init__(self):
            self.tasks = [task]
            self._lock = _AsyncLock()  # asynccontext stub

        def _find_watched(self, _id):
            return SimpleNamespace(
                id="w1", repo_full_name="owner/repo",
                claude_runner_max_retries_per_task=3,
            )

        def _release_verify_lock(self, _id):
            released["flag"] = True

        def _save_watched(self):
            pass

        def _save_tasks(self):
            pass

        def _recompute_execution_priorities(self, _t):
            pass

    fake_svc = _Svc()

    async def fake_verify(task_id, **kw):
        return {
            "task": {"verification_status": "done"},
            "report": {"status": "done"},
        }

    async def fake_dispatch(watched, *, gh_token, target_task_id, force, claude_model):
        dispatched["args"] = {
            "target_task_id": target_task_id,
            "force": force,
            "claude_model": claude_model,
        }
        return {"success": True}

    with patch("app.api.routes.external_prompts.get_oversight_service", return_value=fake_svc), \
         patch("app.services.oversight_verifier.verify_task", side_effect=fake_verify), \
         patch("app.services.oversight_service.get_github_token", return_value="ghp_x"), \
         patch(
             "app.services.claude_runner_bootstrap.trigger_workflow_dispatch",
             side_effect=fake_dispatch,
         ), \
         patch(
             "app.services.claude_runner_bootstrap.pick_model_for_task",
             AsyncMock(return_value="claude-sonnet-x"),
         ), \
         patch(
             "app.api.routes.external_prompts._emit_runner_notification",
             new=lambda **kw: None,
         ):
        await external_prompts._verify_then_chain(
            task_id="t1", watched_id="w1", agent_id="claude-code-action",
        )

    assert released["flag"] is True
    # done → chain_next means target_task_id is None and force is False
    assert dispatched["args"] is not None
    assert dispatched["args"]["target_task_id"] is None
    assert dispatched["args"]["force"] is False


@pytest.mark.asyncio
async def test_verify_then_chain_partial_under_max_retries_re_runs_same_task():
    from app.api.routes import external_prompts

    task = SimpleNamespace(
        id="t1", watched_id="w1", title="x", raw_idea="", prompt="x",
        verification_status="partial", followup_round=1,
        external_status="done", status="awaiting_review",
        external_locked_by="claude-code-action",
        external_lease_until="2030-01-01T00:00:00Z",
        updated_at="",
    )

    dispatched = {"args": None}

    class _Svc:
        def __init__(self):
            self.tasks = [task]
            self._lock = _AsyncLock()

        def _find_watched(self, _id):
            return SimpleNamespace(
                id="w1", repo_full_name="owner/repo",
                claude_runner_max_retries_per_task=3,
            )

        def _release_verify_lock(self, _id):
            pass

        def _save_watched(self):
            pass

        def _save_tasks(self):
            pass

        def _recompute_execution_priorities(self, _t):
            pass

    fake_svc = _Svc()

    async def fake_verify(task_id, **kw):
        return {
            "task": {"verification_status": "partial"},
            "report": {"status": "partial"},
        }

    async def fake_dispatch(watched, *, gh_token, target_task_id, force, claude_model):
        dispatched["args"] = {
            "target_task_id": target_task_id,
            "force": force,
            "claude_model": claude_model,
        }
        return {"success": True}

    with patch("app.api.routes.external_prompts.get_oversight_service", return_value=fake_svc), \
         patch("app.services.oversight_verifier.verify_task", side_effect=fake_verify), \
         patch("app.services.oversight_service.get_github_token", return_value="ghp_x"), \
         patch(
             "app.services.claude_runner_bootstrap.trigger_workflow_dispatch",
             side_effect=fake_dispatch,
         ), \
         patch(
             "app.services.claude_runner_bootstrap.pick_model_for_task",
             AsyncMock(return_value="claude-opus-x"),
         ), \
         patch(
             "app.api.routes.external_prompts._emit_runner_notification",
             new=lambda **kw: None,
         ):
        await external_prompts._verify_then_chain(
            task_id="t1", watched_id="w1", agent_id="claude-code-action",
        )

    # The whole point of ping-pong: same task must be re-dispatched with force
    assert dispatched["args"] is not None
    assert dispatched["args"]["target_task_id"] == "t1"
    assert dispatched["args"]["force"] is True
    # Task must be returned to pending so Claude picks it up again
    assert task.external_status == "pending"
    assert task.status == "pending"
    assert task.external_locked_by is None


@pytest.mark.asyncio
async def test_verify_then_chain_partial_at_max_retries_writes_todo_and_chains():
    from app.api.routes import external_prompts

    task = SimpleNamespace(
        id="t1", watched_id="w1", title="x", raw_idea="", prompt="x",
        verification_status="partial",
        followup_round=3,  # already at max
        external_status="done", status="awaiting_review",
        external_locked_by="claude", external_lease_until="2030-01-01",
        archived=False, archived_at=None, archived_reason=None,
        updated_at="",
    )

    todo_written = {"flag": False}
    dispatched = {"args": None}

    class _Svc:
        def __init__(self):
            self.tasks = [task]
            self._lock = _AsyncLock()

        def _find_watched(self, _id):
            return SimpleNamespace(
                id="w1", repo_full_name="owner/repo",
                claude_runner_max_retries_per_task=3,
            )

        def _release_verify_lock(self, _id):
            pass

        def _save_watched(self):
            pass

        def _save_tasks(self):
            pass

    fake_svc = _Svc()

    async def fake_verify(task_id, **kw):
        return {"task": {"verification_status": "partial"}, "report": {"status": "partial"}}

    async def fake_dispatch(watched, *, gh_token, target_task_id, force, claude_model):
        dispatched["args"] = {
            "target_task_id": target_task_id,
            "force": force,
        }
        return {"success": True}

    async def fake_todo(*, task, watched, verify_result):
        todo_written["flag"] = True

    with patch("app.api.routes.external_prompts.get_oversight_service", return_value=fake_svc), \
         patch("app.services.oversight_verifier.verify_task", side_effect=fake_verify), \
         patch("app.services.oversight_service.get_github_token", return_value="ghp_x"), \
         patch(
             "app.services.claude_runner_bootstrap.trigger_workflow_dispatch",
             side_effect=fake_dispatch,
         ), \
         patch(
             "app.services.claude_runner_bootstrap.pick_model_for_task",
             AsyncMock(return_value=None),
         ), \
         patch(
             "app.api.routes.external_prompts._write_todo_for_task",
             side_effect=fake_todo,
         ), \
         patch(
             "app.api.routes.external_prompts._emit_runner_notification",
             new=lambda **kw: None,
         ):
        await external_prompts._verify_then_chain(
            task_id="t1", watched_id="w1", agent_id="claude-code-action",
        )

    assert todo_written["flag"] is True
    # At max retries we move on rather than spinning on the same task
    assert dispatched["args"]["target_task_id"] is None
    assert dispatched["args"]["force"] is False
    # 🚨 (loop-bug fix) — the task MUST be archived with reason so /next
    # never picks it up again. Before this fix, the task stayed at
    # status=awaiting_review (which is in PICKABLE_STATUSES), so the next
    # workflow dispatch grabbed it again and an infinite loop ensued.
    assert task.archived is True
    assert task.archived_reason == "max_retries"
    assert task.status == "abandoned"
    assert task.external_status == "abandoned"
    assert task.external_locked_by is None


@pytest.mark.asyncio
async def test_verify_then_chain_regressed_archives_with_regressed_reason():
    """Same guarantee for the regressed branch: the task is removed from
    the pickable set with archived_reason='regressed' so /next does not
    grab it again."""
    from app.api.routes import external_prompts

    task = SimpleNamespace(
        id="t1", watched_id="w1", title="x", raw_idea="", prompt="x",
        verification_status="regressed",
        followup_round=1,
        external_status="done", status="awaiting_review",
        external_locked_by=None, external_lease_until=None,
        archived=False, archived_at=None, archived_reason=None,
        updated_at="",
    )

    class _Svc:
        def __init__(self):
            self.tasks = [task]
            self._lock = _AsyncLock()
        def _find_watched(self, _id):
            return SimpleNamespace(
                id="w1", repo_full_name="owner/repo",
                claude_runner_max_retries_per_task=3,
            )
        def _release_verify_lock(self, _id): pass
        def _save_watched(self): pass
        def _save_tasks(self): pass

    fake_svc = _Svc()

    async def fake_verify(task_id, **kw):
        return {"task": {"verification_status": "regressed"}, "report": {"status": "regressed"}}

    dispatched = {"args": None}

    async def fake_dispatch(watched, *, gh_token, target_task_id, force, claude_model):
        dispatched["args"] = {"target_task_id": target_task_id, "force": force}
        return {"success": True}

    with patch("app.api.routes.external_prompts.get_oversight_service", return_value=fake_svc), \
         patch("app.services.oversight_verifier.verify_task", side_effect=fake_verify), \
         patch("app.services.oversight_service.get_github_token", return_value="ghp_x"), \
         patch("app.services.claude_runner_bootstrap.trigger_workflow_dispatch",
               side_effect=fake_dispatch), \
         patch("app.services.claude_runner_bootstrap.pick_model_for_task",
               AsyncMock(return_value=None)), \
         patch("app.api.routes.external_prompts._write_todo_for_task",
               new=AsyncMock(return_value=None)), \
         patch("app.api.routes.external_prompts._emit_runner_notification",
               new=lambda **kw: None):
        await external_prompts._verify_then_chain(
            task_id="t1", watched_id="w1", agent_id="claude-code-action",
        )

    assert task.archived is True
    assert task.archived_reason == "regressed"
    assert task.status == "abandoned"
    # chain_next, not retry
    assert dispatched["args"]["target_task_id"] is None


# ---------------------------------------------------------------------------
# 🚨 TODO file content richness — the user explicitly asked for "what
# remains" to be enumerated in the file itself, not just a generic
# placeholder. These tests render `_write_todo_for_task` against a
# realistic verify_result and assert the markdown contains the actual
# remaining_parts, done_parts, next_actions, AC list, etc. — so the user
# can read the TODO file standalone and know what to do.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_todo_includes_remaining_and_done_parts():
    """When verify_result has rich report data, the TODO must surface:
    - remaining_parts as a checkable list (the user's main question)
    - done_parts so the user knows where Claude got to
    - next_actions as concrete next steps
    - confidence / verifier model / report id

    Generic placeholder text is NOT enough."""
    from app.api.routes import external_prompts

    captured = {}

    async def fake_create_or_update_file(*, owner, repo, path, content, **kw):
        captured["path"] = path
        captured["content"] = content
        return {"ok": True}

    fake_pr = SimpleNamespace(create_or_update_file=fake_create_or_update_file)

    task = SimpleNamespace(
        id="task_abcdef1234",
        watched_id="w1",
        title="Add /metrics endpoint",
        raw_idea="کاربر می‌خواهد روی /metrics آمار ببیند",
        prompt="Add a /metrics endpoint that returns json…",
        verification_status="partial",
        followup_round=3,
        archived_reason="max_retries",
        last_summary="",
        acceptance_criteria=[
            "/metrics endpoint exists and returns 200",
            {"text": "metrics endpoint exposes p50/p95 latency"},
            "GET /metrics is documented in README",
        ],
        followup_prompt="Continue: implement p95 calculation in MetricsAggregator…",
        last_verification_report_id="rep_123",
    )

    watched = SimpleNamespace(
        id="w1", repo_full_name="acme/api",
    )

    verify_result = {
        "report": {
            "id": "rep_999",
            "done_parts": [
                "FastAPI route /metrics registered",
                "Returns 200 OK with json body",
            ],
            "remaining_parts": [
                "p95 latency calculation missing — only p50 implemented",
                "README docs not updated with the new endpoint",
            ],
            "next_actions": [
                "Wire p95 into MetricsAggregator.compute()",
                "Add `## /metrics` section to README.md",
            ],
            "confidence_score": 0.62,
            "model_id": "gemini-2.5-flash",
            "evidence": {
                "commits": ["abc1234", "def5678"],
                "files": ["app/api/routes/metrics.py", "tests/test_metrics.py"],
                "issues": [],
            },
            "raw_response": (
                '{"summary": "Endpoint exists but p95 missing and README '
                'untouched.", "done_parts": [], "remaining_parts": []}'
            ),
        },
    }

    with patch(
        "app.services.github_pr_service.get_github_pr_service",
        return_value=fake_pr,
    ), patch(
        "app.services.prompt_github_sync._resolve_repo_and_branch",
        return_value=("acme", "api", "main"),
    ), patch(
        "app.services.prompt_github_sync._commit_message",
        return_value="todo: …",
    ), patch(
        "app.services.oversight_service.get_github_token",
        return_value="ghp_x",
    ):
        await external_prompts._write_todo_for_task(
            task=task, watched=watched, verify_result=verify_result,
        )

    assert "content" in captured, "TODO file was not written"
    body = captured["content"]

    # Headline section: remaining_parts must appear verbatim as checklist
    assert "p95 latency calculation missing" in body, (
        "remaining_parts text must appear in TODO file so the user can read "
        "what's left without opening the panel"
    )
    assert "README docs not updated" in body
    assert "- [ ] p95 latency" in body, (
        "remaining items must be formatted as unchecked checklist items"
    )

    # Done parts shown so user knows the starting point
    assert "FastAPI route /metrics registered" in body
    assert "- [x] " in body, "done_parts must be formatted as checked items"

    # Next actions enumerated
    assert "Wire p95 into MetricsAggregator" in body
    assert "Add `## /metrics` section to README.md" in body

    # Acceptance criteria reference — including dict form
    assert "/metrics endpoint exists and returns 200" in body
    assert "metrics endpoint exposes p50/p95 latency" in body

    # Verifier metadata
    assert "0.62" in body, "confidence score must surface"
    assert "gemini-2.5-flash" in body, "verifier model must be visible"
    assert "rep_999" in body or "rep_123" in body, "report id must be visible"

    # Evidence section
    assert "abc1234" in body, "commits must be listed"
    assert "app/api/routes/metrics.py" in body, "touched files must be listed"

    # Verifier summary extracted from raw_response
    assert "Endpoint exists but p95 missing" in body

    # Original task context
    assert "Add /metrics endpoint" in body, "title must appear"
    assert "کاربر می‌خواهد روی /metrics آمار ببیند" in body, (
        "raw_idea must be carried over so the file is self-contained"
    )

    # Followup prompt for copy/paste
    assert "MetricsAggregator" in body, "followup prompt must be included"

    # Archive reason must be explained in Persian
    assert "max_retries" in body
    assert "سقف retry" in body or "retry" in body.lower()


@pytest.mark.asyncio
async def test_write_todo_handles_missing_report_gracefully():
    """If verify crashed and there's no rich report, the TODO must still
    be written but tell the user clearly that the verifier didn't return
    a verdict — pointing them to the AC list as the manual checklist."""
    from app.api.routes import external_prompts

    captured = {}

    async def fake_create_or_update_file(*, owner, repo, path, content, **kw):
        captured["content"] = content
        return {"ok": True}

    fake_pr = SimpleNamespace(create_or_update_file=fake_create_or_update_file)

    task = SimpleNamespace(
        id="task_xxxxx", watched_id="w1", title="Fix login bug",
        raw_idea="", prompt="",
        verification_status="error", followup_round=1,
        archived_reason="max_retries", last_summary="",
        acceptance_criteria=["Login form submits without 500"],
        followup_prompt="",
        last_verification_report_id=None,
    )
    watched = SimpleNamespace(id="w1", repo_full_name="acme/api")

    # Verify crashed → no report
    verify_result = {"verification_status": "error", "_crash": "boom"}

    with patch(
        "app.services.github_pr_service.get_github_pr_service",
        return_value=fake_pr,
    ), patch(
        "app.services.prompt_github_sync._resolve_repo_and_branch",
        return_value=("acme", "api", "main"),
    ), patch(
        "app.services.prompt_github_sync._commit_message",
        return_value="todo: …",
    ), patch(
        "app.services.oversight_service.get_github_token",
        return_value="ghp_x",
    ):
        await external_prompts._write_todo_for_task(
            task=task, watched=watched, verify_result=verify_result,
        )

    body = captured["content"]
    # Even with no report, AC list must be present as the fallback checklist
    assert "Login form submits without 500" in body
    # And the user must see a clear "no remaining returned" note
    assert "remaining_part" in body or "AC" in body or "Acceptance" in body
