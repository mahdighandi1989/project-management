# -*- coding: utf-8 -*-
"""PM-INS-0032 (2026-11-22) «دیسک دوباره دارد پر می‌شود»: free pages inside database.db, the owner's consumer groups,
growth snapshots, the compact status for the coordinator, the VACUUM guard, and verify_evidence going to Drive."""
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import disk_janitor as J  # noqa: E402


def _db_with_free_pages(path: Path) -> None:
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (x BLOB)")
    con.executemany("INSERT INTO t VALUES (?)", [(b"x" * 4000,) for _ in range(500)])
    con.commit()
    con.execute("DELETE FROM t")
    con.commit()
    con.close()


def test_db_space_reports_free_pages(tmp_path):
    db = tmp_path / "database.db"
    _db_with_free_pages(db)
    ds = J.db_space(db)
    assert ds["free_pages"] > 400 and ds["free_bytes"] == ds["free_pages"] * ds["page_size"]
    assert ds["used_bytes"] + ds["free_bytes"] == ds["page_count"] * ds["page_size"]


def test_consumers_groups_and_other(tmp_path):
    (tmp_path / "oversight" / "verify_evidence" / "t1").mkdir(parents=True)
    (tmp_path / "oversight" / "tasks.json").write_bytes(b"x" * 5000)
    (tmp_path / "oversight" / "verify_evidence" / "t1" / "a.png").write_bytes(b"x" * 3000)
    (tmp_path / "database.db").write_bytes(b"x" * 8000)
    (tmp_path / "misc.bin").write_bytes(b"x" * 700)
    rep = {"db_space": {"free_bytes": 6000}, "breakdown": J.breakdown(tmp_path)}
    rows = J.consumers(rep, tmp_path)
    by = {r["label"]: r for r in rows}
    assert by["پایگاه‌داده (database.db)"]["bytes"] == 8000 and by["پایگاه‌داده (database.db)"]["free_inside"] == 6000
    assert by["tasks.json (تسک‌های اتاق فرمان)"]["bytes"] == 5000
    assert by["شواهدِ راستی‌آزمایی (verify_evidence)"]["bytes"] == 3000
    assert by["سایر"]["bytes"] == 700
    assert rows[0]["bytes"] >= rows[-1]["bytes"]


def test_snapshots_every_6h_and_growth(tmp_path, monkeypatch):
    rep = {"percent": 70.0, "free": 100, "consumers": [{"label": "a", "bytes": 10}, {"label": "b", "bytes": 5}]}
    h1 = J.record_snapshot(rep, tmp_path)
    h2 = J.record_snapshot(rep, tmp_path)  # same 6 h window ⇒ no new snapshot
    assert len(h1) == 1 and len(h2) == 1
    assert J.growth(h2)["groups"] == []
    t = time.time() + 7 * 3600
    monkeypatch.setattr(J.time, "time", lambda: t)
    rep2 = {"percent": 75.0, "free": 80, "consumers": [{"label": "a", "bytes": 30}, {"label": "b", "bytes": 4}]}
    h3 = J.record_snapshot(rep2, tmp_path)
    assert len(h3) == 2
    g = J.growth(h3)
    assert g["groups"][0] == {"label": "a", "before": 10, "after": 30, "delta": 20}
    assert g["percent_before"] == 70.0 and g["percent_after"] == 75.0


def test_vacuum_guard_refuses_without_room(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "STORAGE_ROOT", tmp_path)
    ds = {"file_bytes": 500, "used_bytes": 200 * 1048576, "free_bytes": 300 * 1048576}
    p = J.vacuum_plan({"db_space": ds, "free": 100 * 1048576})
    assert p["possible"] is False and "لازم است" in p["reason"]
    p = J.vacuum_plan({"db_space": ds, "free": 10_000 * 1048576})
    assert p["possible"] is True and p["reclaimable"] == 300 * 1048576
    small = {"file_bytes": 500, "used_bytes": 1048576, "free_bytes": 1048576}
    assert J.vacuum_plan({"db_space": small, "free": 10_000 * 1048576})["possible"] is False


def test_vacuum_start_needs_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "vacuum_plan", lambda rep=None: {"possible": True})
    r = J.vacuum_start(False)
    assert r["started"] is False and "confirm" in r["reason"]


def test_status_levels(monkeypatch):
    monkeypatch.setattr(J, "vacuum_plan", lambda rep=None: {"possible": False})
    assert J.status({"percent": 50.0})["level"] == "ok"
    assert J.status({"percent": 81.0})["level"] == "warn"
    s = J.status({"percent": 90.0, "consumers": [{"label": "x", "bytes": 1}]})
    assert s["level"] == "critical" and s["top"][0]["label"] == "x" and s["alert"]


def test_old_verify_evidence_goes_to_drive_then_off_disk(tmp_path, monkeypatch):
    from app.services import gdrive

    old = tmp_path / "oversight" / "verify_evidence" / "task-old"
    new = tmp_path / "oversight" / "verify_evidence" / "task-new"
    for d in (old / "run1", new / "run1"):
        d.mkdir(parents=True)
        (d / "a.png").write_bytes(b"x" * 1000)
    t = time.time() - 30 * 86400
    for p in (old / "run1" / "a.png", old / "run1", old):
        os.utime(p, (t, t))
    sent = []
    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(J, "_archive_item", lambda db, kind, item: sent.append((kind, item.name)) or True)
    r = J.run(db=object(), root=tmp_path)
    assert ("verify_evidence", "task-old") in sent and not old.exists() and new.exists()
    assert r["archived"] == 1


def test_report_carries_the_new_parts(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "db_space", lambda db_path=None: {"free_bytes": 1, "used_bytes": 1, "file_bytes": 2})
    monkeypatch.setattr(J, "db_tables", lambda db_path=None, n=10: [])
    (tmp_path / "oversight").mkdir()
    rep = J.report(tmp_path)
    assert "consumers" in rep and "history" in rep and "growth" in rep and rep["db_space"]["free_bytes"] == 1
    assert (tmp_path / J.HISTORY_FILE).is_file()
