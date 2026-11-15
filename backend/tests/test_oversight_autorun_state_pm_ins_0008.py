"""PM-INS-0008 — the card must say WHY auto-run does not run, flag an overdue run, and «اجرای الان» must respect
«فقط verify» while running eligible auto-mode tasks otherwise."""
import asyncio

from app.services import oversight_service as OS


def _w(**kw):
    w = OS.WatchedProject(id="W-autorun", repo_full_name="o/r", repo_url="https://github.com/o/r")
    w.autonomy_level = "auto"
    w.schedule_enabled = True
    w.interval_hours = 96
    w.next_run_at = "2026-06-07T07:05:20+00:00"
    for k, v in kw.items():
        setattr(w, k, v)
    return w


def _svc(w, tasks=()):
    svc = OS.get_oversight_service()
    keep = (svc.watched, svc.tasks, svc._save_watched, svc._spawn_bg)
    svc.watched, svc.tasks = [w], list(tasks)
    svc._save_watched = lambda *a, **k: None
    spawned = []
    svc._spawn_bg = lambda coro: (spawned.append(coro), coro.close())
    return svc, keep, spawned


def _restore(svc, keep):
    svc.watched, svc.tasks, svc._save_watched, svc._spawn_bg = keep


def _task(tid, mode):
    t = OS.OversightTask(id=tid, watched_id="W-autorun", project_full_name="o/r", title=tid, prompt="p")
    t.status = "pending"
    t.execution_mode = mode
    return t


def test_verify_only_is_named_and_not_run():
    svc, keep, spawned = _svc(_w(verify_only_mode=True))
    try:
        st = svc.autorun_state(svc.watched[0])
        assert st["state"] == "verify_only"
        r = asyncio.run(svc.autorun_now("W-autorun"))
        assert r["success"] is False and r["ran_count"] == 0 and "فقط verify" in r["message"]
        assert not spawned
    finally:
        _restore(svc, keep)


def test_overdue_then_run_now_runs_only_auto_mode_tasks():
    tasks = [_task("a", "auto_via_pr"), _task("m", "manual")]
    svc, keep, spawned = _svc(_w(verify_only_mode=False), tasks)
    try:
        st = svc.autorun_state(svc.watched[0])
        assert st["state"] == "overdue" and st["eligible_count"] == 1 and st["pending_count"] == 2
        r = asyncio.run(svc.autorun_now("W-autorun"))
        assert r["success"] and r["task_ids"] == ["a"] and len(spawned) == 1
        assert svc.watched[0].last_run_at and svc.watched[0].next_run_at > "2026-11"
    finally:
        OS._RUNNING_RUNS.discard("W-autorun")
        _restore(svc, keep)


def test_list_watched_carries_autorun_and_effective_models():
    svc, keep, _ = _svc(_w(verify_only_mode=True))
    try:
        d = asyncio.run(svc.list_watched())[0]
        assert d["autorun"]["state"] == "verify_only"
        assert "effective_models" in d
    finally:
        _restore(svc, keep)
