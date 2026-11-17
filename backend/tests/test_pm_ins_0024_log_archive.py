"""PM-INS-0024 «الف» — old render_logs / ai_logs → Drive → deleted; searchable; never deleted without Drive."""

import gzip
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.ai_log import AILog
from app.models.render_log import LogDriveArchive, RenderLog, RenderLogSettings
from app.services import gdrive
from app.services import log_archive as LA

NOW = datetime.utcnow()


@pytest.fixture()
def db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for m in (RenderLog, AILog, LogDriveArchive, RenderLogSettings):
        m.__table__.create(eng)
    s = sessionmaker(bind=eng)()
    for i in range(30):
        s.add(RenderLog(id=f"r{i}", service_id="srv-a" if i % 2 else "srv-b", service_name="x",
                        timestamp=NOW - timedelta(days=i), level="error" if i == 20 else "info", message=f"line {i}"))
        s.add(AILog(id=f"a{i}", provider="deepseek", model="deepseek-chat", created_at=NOW - timedelta(days=i * 2),
                    prompt=f"p{i}", response="r"))
    s.commit()
    store = {}
    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "folder")

    def _up(db, data, **kw):
        fid = f"f{len(store)}"
        store[fid] = data
        return {"id": fid, "link": f"https://drive/{fid}"}

    monkeypatch.setattr(gdrive, "upload_bytes", _up)
    monkeypatch.setattr(gdrive, "download_bytes", lambda db, fid: store[fid])
    s._store = store
    return s


def test_preview_changes_nothing(db):
    p = LA.preview(db, {"render_logs": NOW - timedelta(days=14), "ai_logs": NOW - timedelta(days=30)})
    assert p["render_logs"]["total"] == 30 and p["render_logs"]["to_move"] == 15
    assert p["ai_logs"]["to_move"] == 14 and db.query(RenderLog).count() == 30


def test_run_moves_then_deletes_and_indexes(db):
    cut = {"render_logs": NOW - timedelta(days=14), "ai_logs": NOW - timedelta(days=30)}
    res = LA.run(db, cut)
    assert res["ok"] and res["render_logs"]["moved"] == 15 and res["ai_logs"]["moved"] == 14
    assert db.query(RenderLog).count() == 15 and db.query(AILog).count() == 16
    rows = [json.loads(l) for l in gzip.decompress(db._store["f0"]).decode().splitlines()]
    assert len(rows) == 15 and rows[0]["message"] == "line 29"          # full rows, oldest first
    arch = LA.list_archives(db, "render_logs")
    assert arch[0]["rows"] == 15 and "srv-a" in arch[0]["services"] and arch[0]["link"]
    hit = LA.search(db, table="render_logs", q="line 20")
    assert [h["id"] for h in hit["hits"]] == ["r20"]
    assert LA.search(db, table="render_logs", level="error")["hits"][0]["id"] == "r20"


def test_nothing_is_deleted_when_drive_fails(db, monkeypatch):
    monkeypatch.setattr(gdrive, "upload_bytes", lambda db, data, **kw: {})
    res = LA.run(db, {"render_logs": NOW - timedelta(days=14), "ai_logs": None})
    assert not res["ok"] and res["render_logs"]["moved"] == 0 and db.query(RenderLog).count() == 30


def test_nothing_is_deleted_without_drive(db, monkeypatch):
    monkeypatch.setattr(gdrive, "is_connected", lambda db: False)
    assert LA.run(db)["ok"] is False and db.query(RenderLog).count() == 30


def test_default_retention_follows_the_setting(db):
    db.add(RenderLogSettings(retention_hours=48)); db.commit()
    cut = LA.default_cutoffs(db)
    assert abs((NOW - cut["render_logs"]).total_seconds() - 48 * 3600) < 120
    assert abs((NOW - cut["ai_logs"]).days - 30) <= 1


def test_routes_need_confirmation_and_the_janitor_runs_it():
    import inspect
    from app.api.routes import render_logs as RL
    from app.services import disk_janitor
    assert "if not body.confirm" in inspect.getsource(RL.log_archive_run)
    assert "log_archive.run(_d)" in inspect.getsource(disk_janitor.run_all)
