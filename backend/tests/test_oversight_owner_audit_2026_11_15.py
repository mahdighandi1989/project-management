"""Deep audit of the «اتاق فرمان» project card (owner request 2026-11-15) — the behaviour fixes."""

import inspect
import os

from app.api.routes import oversight as R
from app.core import auth
from app.services import claude_runner_bootstrap as CRB
from app.services import oversight_deep_scan_service as DS
from app.services import oversight_service as OS
from app.services import prompt_github_sync as PGS


def test_a_scan_where_no_model_answered_is_a_failure_not_a_success():
    src = inspect.getsource(DS._run_deep_scan_impl)
    assert "ai_passes_ok == 0" in src and "raise ScanNoModel" in src
    assert src.index("raise ScanNoModel") < src.index("watched.last_scan_at = now_iso()")
    assert '"passes_total": len(PASSES)' not in src


def test_scheduled_scan_backs_off_and_never_switches_models_on():
    src = inspect.getsource(OS.OversightService._scheduled_scan)
    assert "pick_scan_model" in src and "revert_temp_enables(revert)" in src
    assert "{1: 1.0, 2: 6.0, 3: 24.0}" in src and '"scan_failed"' in src


def test_scheduler_verify_rules():
    src = inspect.getsource(OS.OversightService._scheduler_tick_inner)
    assert 'w.schedule_enabled and w.id not in _RUNNING_VERIFIES' in src  # paused project ⇒ no periodic verify
    assert 't.status != "suggested"' in src                               # unapproved suggestions are not verified
    assert '"error",' in src                                                # failed verifies are retried
    assert "self._scheduled_verify(" in src                                 # background, not blocking the tick


def test_interval_zero_means_off_for_scan_and_verify():
    b = R.WatchedUpdate(scan_interval_hours=0, verify_interval_hours=0, interval_hours=0)
    R._clamp_intervals(b)
    assert (b.scan_interval_hours, b.verify_interval_hours, b.interval_hours) == (0, 0, R._MIN_INTERVAL_HOURS)


def test_enum_fields_are_validated():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        R.WatchedUpdate(autonomy_level="bogus")
    with pytest.raises(ValidationError):
        R.WatchedUpdate(max_auto_loop_rounds=0)
    R.WatchedUpdate(autonomy_level="assist", scan_depth="ultra", default_execution_mode="auto_via_pr")


def test_runner_token_is_scoped_and_per_project(monkeypatch):
    monkeypatch.setenv("EXTERNAL_TOOL_TOKEN", "master-secret")
    t = auth.runner_token_for("w-1")
    assert t.startswith("rt_w-1_") and "master-secret" not in t
    assert auth.runner_token_watched(t) == "w-1"
    assert auth.runner_token_watched(t[:-1] + "x") is None
    assert auth.runner_token_watched("master-secret") is None
    assert "runner_token_for(watched.id)" in inspect.getsource(CRB.install_runner)


def test_backend_own_repo_is_never_a_runner_target(monkeypatch):
    monkeypatch.delenv("PROMPT_SYNC_EXCLUDE_REPOS", raising=False)
    assert "mahdighandi1989/project-management" in PGS._excluded_repos()

    class W:
        repo_full_name = "mahdighandi1989/project-management"
        claude_runner_enabled = True
        prompt_sync_enabled = True

    assert PGS._resolve_repo_and_branch(W(), explicit=True) is None
    assert PGS._resolve_repo_and_branch(W(), explicit=True, allow_excluded=True) is not None  # uninstall only


def test_runner_pushes_to_a_branch_unless_the_owner_allowed_direct_push():
    y = CRB.build_workflow_yaml(watched_id="w", repo_full_name="o/r")
    assert 'OVERSIGHT_PUSH_MODE: "branch"' in y and "oversight/task-" in y and "gh pr create" in y
    assert "مستقیم به main commit و push" not in CRB.MASTER_PROMPT
    assert "prompt/task-<task_id>.md" in CRB.MASTER_PROMPT


def test_todo_file_obeys_the_automatic_gate():
    from app.api.routes import external_prompts as EP

    src = inspect.getsource(EP._write_todo_for_task)
    assert "_resolve_repo_and_branch(watched, explicit=False)" in src and "return True" in src
