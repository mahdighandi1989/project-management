"""Owner: «موارد اختیاری را هم انجام بده» (2026-11-15) — recording resume after a restart, old reports to Drive,
tasks.json/reports.json written off the event loop."""

import asyncio
import gzip
import json
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services import inspector_recording_service as IRS
from app.services import oversight_service as OS
from app.services import reports_archive as RA


# ── recording resume ────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def rec(tmp_path, monkeypatch):
    monkeypatch.setattr(IRS, "RECORDINGS_ROOT", tmp_path)
    return IRS.InspectorRecordingService()


def test_resume_recreates_lost_session_under_same_id(rec):
    sid = str(uuid.uuid4())

    async def go():
        s, resumed = await rec.resume_session(sid, started_ago_sec=120, project_id="p", project_full_name=None, mode="B")
        assert resumed and s.session_id == sid and s.phase == "recording"
        assert 115 < s.duration_sec() < 130  # the recording's real length survives the restart
        # chunks re-sent by the browser are counted once per seq
        await rec.append_video_chunk(sid, 0, b"a")
        await rec.append_video_chunk(sid, 0, b"a")
        await rec.append_video_chunk(sid, 1, b"b")
        assert s.video_chunks_count == 2
        again, resumed2 = await rec.resume_session(sid, project_id="p", project_full_name=None, mode="B")
        assert again is s and not resumed2  # an existing session is never replaced

    asyncio.run(go())


def test_resume_rejects_non_uuid_ids(rec):
    with pytest.raises(ValueError):
        asyncio.run(rec.resume_session("../../etc", project_id="p", project_full_name=None, mode="A"))


def test_resume_route_is_wired():
    from app.api.routes import inspector_recording as R

    paths = {(r.path, tuple(sorted(r.methods))) for r in R.router.routes}
    assert any(p.endswith("/{session_id}/resume") and "POST" in m for p, m in paths)


# ── reports → Drive ─────────────────────────────────────────────────────────────────────────────────────────────────
def _rep(i, task, days_ago, **kw):
    run_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return OS.OversightReport(id=f"r{i}", task_id=task, watched_id="w", project_full_name="o/r", run_at=run_at,
                              status="partial", raw_response="X" * 100, evidence={"e": 1}, **kw)


def test_candidates_keep_latest_per_task_and_recent_ones():
    reps = [_rep(1, "t1", 1), _rep(2, "t1", 50), _rep(3, "t1", 60), _rep(4, "t2", 70), _rep(5, "t3", 90)]
    reps[4].archived_to = {"drive_id": "x"}  # already archived
    got = {r.id for r in RA.candidates(reps, min_age_days=30)}
    # r1 recent; r4 is t2's latest; r5 done already
    assert got == {"r2", "r3"}


def test_run_uploads_full_copies_then_slims(monkeypatch, tmp_path):
    from app.services import gdrive

    svc = SimpleNamespace(_lock=asyncio.Lock(), reports=[_rep(1, "t1", 1), _rep(2, "t1", 50)], saved=0)
    svc._save_reports = lambda: setattr(svc, "saved", svc.saved + 1)
    big = tmp_path / "reports.json"
    big.write_bytes(b"0" * 2000)
    uploaded = {}
    monkeypatch.setattr(OS, "REPORTS_FILE", big)
    monkeypatch.setattr(OS, "get_oversight_service", lambda: svc)
    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "folder")

    def _up(db, data, **kw):
        uploaded["items"] = json.loads(gzip.decompress(data))
        return {"id": "drv1", "link": "https://drive/x"}

    monkeypatch.setattr(gdrive, "upload_bytes", _up)
    res = asyncio.run(RA.run(db=object(), min_bytes=1000, min_age_days=30))
    assert res["archived"] == 1 and svc.saved == 1
    assert [d["id"] for d in uploaded["items"]] == ["r2"] and uploaded["items"][0]["raw_response"] == "X" * 100
    old = svc.reports[1]
    assert old.raw_response == "" and old.evidence == {} and old.archived_to["drive_id"] == "drv1"
    assert old.status == "partial" and svc.reports[0].raw_response  # summary kept; the latest untouched

    # opening it brings the full copy back
    monkeypatch.setattr(gdrive, "download_bytes", lambda db, fid: gzip.compress(json.dumps(uploaded["items"]).encode()))
    import app.core.database as D

    monkeypatch.setattr(D, "SessionLocal", lambda: SimpleNamespace(close=lambda: None))
    full = asyncio.run(RA.full_report(old.to_dict()))
    assert full["raw_response"] == "X" * 100 and full["restored_from_archive"]


def test_run_does_nothing_without_drive(monkeypatch, tmp_path):
    from app.services import gdrive

    big = tmp_path / "reports.json"
    big.write_bytes(b"0" * 2000)
    monkeypatch.setattr(OS, "REPORTS_FILE", big)
    monkeypatch.setattr(gdrive, "is_connected", lambda db: False)
    res = asyncio.run(RA.run(db=object(), min_bytes=1000))
    assert res["archived"] == 0 and "drive" in res["skipped"]


# ── background JSON writes ──────────────────────────────────────────────────────────────────────────────────────────
def test_background_writes_land_in_order_and_flush(tmp_path):
    p = tmp_path / "tasks.json"

    async def go():
        for i in range(50):
            OS._write_json_soon(p, [{"n": i}])
        assert OS.flush_pending_writes(10)

    asyncio.run(go())
    assert json.loads(p.read_text()) == [{"n": 49}]
    # a synchronous (no loop) write after queued ones is never overwritten by an older snapshot
    OS._write_json_soon(p, [{"n": "sync"}])
    assert OS.flush_pending_writes(5)
    assert json.loads(p.read_text()) == [{"n": "sync"}]


def test_save_tasks_does_not_block_the_loop(tmp_path, monkeypatch):
    p = tmp_path / "slow.json"
    real = OS._write_json

    def slow(path, data):
        time.sleep(0.3)
        real(path, data)

    monkeypatch.setattr(OS, "_write_json", slow)

    async def go():
        t0 = time.monotonic()
        OS._write_json_soon(p, [1])
        assert time.monotonic() - t0 < 0.1
        await asyncio.to_thread(OS.flush_pending_writes, 5)

    asyncio.run(go())
    assert json.loads(p.read_text()) == [1]
