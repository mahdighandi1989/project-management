# -*- coding: utf-8 -*-
"""Fixes from the «اتاق فرمان» audit (owner plan item 8, 2026-11-15) — each guards a bug that was confirmed in code."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_interrupted_scans_are_marked_after_a_restart(tmp_path, monkeypatch):
    from app.services import oversight_deep_scan_service as ds

    monkeypatch.setattr(ds, "PROGRESS_DIR", tmp_path)
    (tmp_path / "a.json").write_text(json.dumps({"status": "starting", "phase": "phase3_x", "stop_requested": True}))
    (tmp_path / "b.json").write_text(json.dumps({"status": "completed"}))
    assert ds.mark_interrupted_scans() == 1
    a = json.loads((tmp_path / "a.json").read_text())
    assert a["status"] == "interrupted" and a["stop_requested"] is False
    assert json.loads((tmp_path / "b.json").read_text())["status"] == "completed"


def test_deep_scan_start_clears_an_old_stop_request():
    src = (Path(__file__).resolve().parents[1] / "app/services/oversight_deep_scan_service.py").read_text(encoding="utf-8")
    start = src[src.index('status="starting"') - 200: src.index('status="starting"') + 900]
    assert "stop_requested=False" in start and "pause_requested=False" in start
    assert "passes_total=len(enabled)" in start
    # the «scan started» message comes after the token check
    assert src.index("token = get_github_token()\n    if not token:") < src.index("# 🔔 notification (scan_started)")


def test_scheduler_ticks_never_overlap():
    from app.services.oversight_service import OversightService

    svc = OversightService.__new__(OversightService)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_inner():
        started.set()
        await release.wait()
        return {"ran": True}

    svc._scheduler_tick_inner = slow_inner

    async def run():
        first = asyncio.create_task(svc.scheduler_tick())
        await started.wait()
        second = await svc.scheduler_tick()
        release.set()
        return await first, second

    first, second = asyncio.run(run())
    assert first == {"ran": True}
    assert second.get("skipped") is True


def test_no_progress_guard_ignores_the_report_of_the_verify_that_just_ran():
    from app.api.routes.external_prompts import _remaining_unchanged

    task = SimpleNamespace(id="t")
    older = SimpleNamespace(id="r1", task_id="t", run_at="2026-06-01T00:00:00Z", remaining_parts=["a", "b", "c", "d"])
    current = SimpleNamespace(id="r2", task_id="t", run_at="2026-06-02T00:00:00Z", remaining_parts=["a", "b"])
    svc = SimpleNamespace(reports=[current, older])
    # real progress (4 → 2 items): without excluding r2 it compared r2 with itself and said «no progress»
    assert _remaining_unchanged(["a", "b"], task, svc, exclude_report_id="r2") is False
    assert _remaining_unchanged(["a", "b", "c", "d"], task, svc, exclude_report_id="r2") is True


def test_repo_suffix_is_removed_not_stripped():
    for p in ("app/services/inspector_scan_bridge.py", "app/services/inspector_proposal_executor.py"):
        src = (Path(__file__).resolve().parents[1] / p).read_text(encoding="utf-8")
        assert '.rstrip(".git")' not in src, p


def test_one_deep_scan_per_project_and_a_time_limit(monkeypatch):
    from app.services import oversight_deep_scan_service as ds

    started = asyncio.Event()

    async def slow(watched_id, **kw):
        started.set()
        await asyncio.sleep(5)

    monkeypatch.setattr(ds, "_run_deep_scan_impl", slow)
    monkeypatch.setattr(ds, "SCAN_TIMEOUT_MIN", 0.5 / 60)  # 0.5 s
    monkeypatch.setattr(ds, "write_progress", lambda *a, **k: None)

    async def run():
        first = asyncio.create_task(ds.run_deep_scan("w1"))
        await started.wait()
        try:
            await ds.run_deep_scan("w1")
            second = "ran"
        except ds.ScanAlreadyRunning:
            second = "refused"
        try:
            await first
            outcome = "finished"
        except asyncio.TimeoutError:
            outcome = "timed out"
        return second, outcome, set(ds._RUNNING_SCANS)

    second, outcome, left = asyncio.run(run())
    assert second == "refused" and outcome == "timed out" and "w1" not in left


def test_scan_dedup_keeps_distinct_bugs_and_respects_rejections():
    from types import SimpleNamespace as NS

    from app.services.oversight_deep_scan_service import _find_existing_active_task

    def task(tid, title, status="suggested", archived=False):
        return NS(id=tid, watched_id="w", title=title, status=status, archived=archived, verification_status="pending",
                  type="bug", target_files=["app/x.py"], created_by_scan_metadata={}, raw_idea="")

    svc = NS(tasks=[task("a", "Login form loses the password field"),
                    task("c", "Race condition in the payment webhook retry", status="cancelled", archived=True)])
    other_bug = {"title": "Pagination of reports returns duplicates", "type": "bug", "target_files": ["app/x.py"]}
    assert _find_existing_active_task(svc, "w", other_bug) is None          # same file, different bug ⇒ new task
    same = {"title": "Login form loses the password field value", "type": "bug", "target_files": ["app/x.py"]}
    assert _find_existing_active_task(svc, "w", same).id == "a"
    rejected = {"title": "Race condition in the payment webhook retry", "type": "bug", "target_files": ["app/x.py"]}
    assert _find_existing_active_task(svc, "w", rejected).id == "c"         # owner cancelled it ⇒ not re-suggested
