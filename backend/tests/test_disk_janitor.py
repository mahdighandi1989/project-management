# -*- coding: utf-8 -*-
"""Disk janitor (owner decision 2026-11-15): archive old artifacts to Google Drive, THEN free the 1 GB disk; never
delete without an archive copy; a failed data write is reported, not swallowed."""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import disk_janitor as J  # noqa: E402


def _tree(root: Path):
    (root / "scan_v5_bundles").mkdir(parents=True)
    (root / "scan_v5_screenshots" / "w1").mkdir(parents=True)
    old = root / "scan_v5_bundles" / "old.pdf"
    new = root / "scan_v5_bundles" / "new.pdf"
    shots = root / "scan_v5_screenshots" / "w1" / "a.png"
    for f in (old, new, shots):
        f.write_bytes(b"x" * 1000)
    t = time.time() - 30 * 86400
    for f in (old, shots, shots.parent):
        os.utime(f, (t, t))
    return old, new, shots


def test_without_drive_nothing_is_deleted(tmp_path, monkeypatch):
    from app.services import gdrive

    old, new, shots = _tree(tmp_path)
    monkeypatch.setattr(gdrive, "is_connected", lambda db: False)
    r = J.run(db=object(), root=tmp_path)
    assert r["drive"] is False and r["archived"] == 0 and r["kept_without_drive"] == 2
    assert old.exists() and new.exists() and shots.exists()


def test_with_drive_old_items_are_archived_then_removed(tmp_path, monkeypatch):
    from app.services import gdrive

    old, new, shots = _tree(tmp_path)
    uploaded = []
    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "/".join(parts))
    monkeypatch.setattr(gdrive, "upload", lambda db, fh, **k: uploaded.append(k["name"]) or {"id": "f1"})
    monkeypatch.setattr(gdrive, "upload_bytes", lambda db, data, **k: uploaded.append(k["name"]) or {"id": "f2"})
    r = J.run(db=object(), root=tmp_path)
    assert sorted(uploaded) == ["old.pdf", "w1.tar.gz"]
    assert not old.exists() and not shots.parent.exists() and new.exists()  # the recent one stays
    assert r["archived"] == 2 and r["freed"] >= 2000


def test_a_failed_upload_keeps_the_file(tmp_path, monkeypatch):
    from app.services import gdrive

    old, _, _ = _tree(tmp_path)
    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "p")

    def boom(*a, **k):
        raise RuntimeError("quota")
    monkeypatch.setattr(gdrive, "upload", boom)
    monkeypatch.setattr(gdrive, "upload_bytes", boom)
    r = J.run(db=object(), root=tmp_path)
    assert old.exists() and r["errors"]


def test_write_errors_are_reported(tmp_path):
    from app.services import oversight_service as S

    S._write_json(tmp_path / "missing-dir" / "x.json", {"a": 1})
    assert "x.json" in (S.last_write_error() or "")
    assert J.needs_alert({"percent": 10, "last_write_error": S.last_write_error()})
    S._write_json(tmp_path / "ok.json", {"a": 1})
    assert S.last_write_error() is None
    assert J.needs_alert({"percent": 91, "last_run": {"drive": False}}).endswith("بایگانی ممکن نیست")


# --- PM-INS-0024 (2026-11-17): «چه چیزی جا گرفته» + safe cleanup with preview/confirm + Telegram past 85% -------------

def test_breakdown_names_the_biggest_dirs_files_and_tables(tmp_path):
    import sqlite3

    (tmp_path / "oversight").mkdir()
    (tmp_path / "oversight" / "tasks.json").write_bytes(b"x" * 5000)
    (tmp_path / "small.txt").write_bytes(b"x" * 10)
    db = tmp_path / "database.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE t (a TEXT)")
    con.executemany("INSERT INTO t VALUES (?)", [("y" * 100,)] * 50)
    con.commit()
    con.close()
    b = J.breakdown(tmp_path)
    assert b["top_dirs"][0] == {"path": "oversight", "bytes": 5000}
    assert b["top_files"][0]["path"] in ("oversight/tasks.json", "database.db")
    assert {f["path"] for f in b["top_files"]} >= {"oversight/tasks.json", "small.txt"}
    t = J.db_tables(db)
    assert t and t[0]["table"] == "t"


def test_cleanup_preview_never_lists_the_database_or_stores_and_apply_only_acts_on_listed(tmp_path, monkeypatch):
    from app.services import gdrive

    old, new, shots = _tree(tmp_path)
    (tmp_path / "oversight").mkdir()
    store = tmp_path / "oversight" / "tasks.json"
    store.write_bytes(b"{}")
    (tmp_path / "database.db").write_bytes(b"x")
    cache = tmp_path / "x" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "m.pyc").write_bytes(b"x" * 300)
    log = tmp_path / "logs" / "a.log"
    log.parent.mkdir()
    log.write_bytes(b"x" * 200)
    t = time.time() - 30 * 86400
    os.utime(log, (t, t))
    os.utime(store, (t, t))
    p = J.cleanup_preview(tmp_path)
    paths = {i["path"]: i for i in p["items"]}
    assert "oversight/tasks.json" not in paths and "database.db" not in paths and "scan_v5_bundles/new.pdf" not in paths
    assert paths["x/__pycache__"]["action"] == "delete"
    assert paths["logs/a.log"]["action"] == "archive"
    assert paths["scan_v5_bundles/old.pdf"]["kind"] == "old_artifact"

    # Drive NOT connected: caches go, archive-items stay, an unlisted path is refused
    monkeypatch.setattr(gdrive, "is_connected", lambda db: False)
    r = J.cleanup_apply(["x/__pycache__", "logs/a.log", "oversight/tasks.json", "../etc"], db=object(), root=tmp_path)
    assert not cache.exists() and log.exists() and store.exists()
    assert r["removed"] == 1 and "logs/a.log" in r["kept"] and set(r["skipped"]) == {"oversight/tasks.json", "../etc"}

    # Drive connected: the log is archived first, then removed
    up = []
    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "p")
    monkeypatch.setattr(gdrive, "upload", lambda db, fh, **k: up.append(k["name"]) or {"id": "1"})
    r = J.cleanup_apply(["logs/a.log"], db=object(), root=tmp_path)
    assert up == ["a.log"] and not log.exists() and r["removed"] == 1


def test_telegram_alert_only_past_85_percent_and_names_the_biggest():
    rep = {"percent": 84.9, "free": 100, "breakdown": {"top_files": [{"path": "oversight/tasks.json", "bytes": 127 << 20}]}}
    assert J.telegram_alert(rep) is None
    assert J.needs_alert({**rep, "last_run": {"drive": True}})  # the home banner still warns from 80%
    msg = J.telegram_alert({**rep, "percent": 86.0})
    assert "86.0%" in msg and "oversight/tasks.json 127.0MB" in msg
