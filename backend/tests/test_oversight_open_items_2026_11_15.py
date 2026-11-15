"""«موارد باز» of the project-card audit (2026-11-15)."""

import inspect

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.routes import external_prompts as EP
from app.api.routes import oversight as R
from app.core import auth
from app.services import oversight_service as OS


def test_bulk_verify_state_is_per_project():
    assert not hasattr(R, "_BULK_VERIFY_STATE")
    R._BULK_STATES.clear()
    R._BULK_STATES["A"] = {**R._new_bulk_state(), "running": True}
    assert R._bulk_running_other("B") == "A" and R._bulk_running_other("A") is None
    R._BULK_STATES.clear()


def test_report_counts_are_per_project():
    svc = OS.get_oversight_service()
    keep = list(svc.reports)
    try:
        svc.reports = [OS.OversightReport(id=f"r{i}", task_id="t", watched_id=w, project_full_name="o/r",
                                          run_at="2026-11-15", status="partial") for i, w in enumerate("AAB")]
        assert svc._report_counts_by_watched() == {"A": 2, "B": 1}
    finally:
        svc.reports = keep


def test_scheduled_runs_leave_the_tick():
    tick = inspect.getsource(OS.OversightService._scheduler_tick_inner)
    assert "self._scheduled_run(" in tick and "await self.run_task(" not in tick
    assert "_RUNNING_RUNS.discard" in inspect.getsource(OS.OversightService._scheduled_run)


def _req(path_params=None, query=b""):
    return Request({"type": "http", "path_params": path_params or {}, "query_string": query, "headers": []})


def test_runner_token_only_opens_its_own_project(monkeypatch):
    monkeypatch.setenv("EXTERNAL_TOOL_TOKEN", "master")
    tok = auth.runner_token_for("W1")
    EP.require_external_token(_req(query=b"watched_id=W1"), tok)  # its own /next: ok
    with pytest.raises(HTTPException) as e:
        EP.require_external_token(_req(query=b"watched_id=W2"), tok)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException):
        EP.require_external_token(_req(), tok)  # /next without watched_id
    svc = OS.get_oversight_service()
    keep = list(svc.tasks)
    try:
        svc.tasks = [OS.OversightTask(id="T2", watched_id="W2", title="x", project_full_name="o/r", prompt="x")]
        with pytest.raises(HTTPException):
            EP.require_external_token(_req({"task_id": "T2"}), tok)  # another project's task
    finally:
        svc.tasks = keep
    EP.require_external_token(_req({"task_id": "T2"}), "master")  # the master token is not restricted


def test_first_runner_sync_skips_finished_and_archived_tasks():
    src = inspect.getsource(OS.OversightService._sync_dirty_tasks_to_github)
    assert 'not getattr(t, "github_prompt_synced_at", None)' in src and '"suggested"' in src
