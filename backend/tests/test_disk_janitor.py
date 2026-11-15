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
