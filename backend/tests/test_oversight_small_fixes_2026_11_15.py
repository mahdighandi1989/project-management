"""Last batch of confirmed reviewer findings (2026-11-15): intervals, bulk-verify double start, per-project logs,
evidence path ids."""

import asyncio
import inspect
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import oversight as R
from app.services.verify_runtime import backend_log_probe as P
from app.services.verify_runtime.storage import resolve_evidence_file


def test_zero_or_negative_interval_is_clamped():
    body = R.WatchedUpdate(interval_hours=0, verify_interval_hours=-3, scan_interval_hours=float("nan"))
    R._clamp_intervals(body)
    assert body.interval_hours == body.verify_interval_hours == body.scan_interval_hours == R._MIN_INTERVAL_HOURS
    assert "interval_hours" in body.model_dump(exclude_unset=True)
    ok = R.WatchedUpdate(interval_hours=6)
    R._clamp_intervals(ok)
    assert ok.interval_hours == 6
    s = R.SettingsUpdate(scan_interval_hours=0)
    R._clamp_intervals(s)
    assert s.scan_interval_hours == R._MIN_INTERVAL_HOURS


def test_bulk_verify_claims_slot_before_spawning():
    src = inspect.getsource(R.start_bulk_verify)
    assert src.index('_BULK_VERIFY_STATE["running"] = True') < src.index("_aio.create_task(")


def test_evidence_ids_cannot_traverse(tmp_path: Path):
    d = tmp_path / "verify_evidence" / "t1" / "r1"
    d.mkdir(parents=True)
    (d / "a.png").write_bytes(b"x")
    assert resolve_evidence_file(tmp_path, "t1", "r1", "a.png") is not None
    assert resolve_evidence_file(tmp_path, "..", "r1", "a.png") is None
    assert resolve_evidence_file(tmp_path, "t1", "../../x", "a.png") is None
    assert resolve_evidence_file(tmp_path, "t1", "r1", "../../../etc/passwd") is None


@pytest.fixture()
def logs_db(monkeypatch):
    from app.core import database
    from app.models.render_log import RenderLog, RenderService

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    RenderService.__table__.create(eng)
    RenderLog.__table__.create(eng)
    S = sessionmaker(bind=eng)
    db = S()
    now = datetime.utcnow()
    db.add_all([
        RenderService(id="srv-a", name="proj-a-backend", service_url="https://proj-a-backend.onrender.com"),
        RenderService(id="srv-b", name="proj-b-backend", service_url=None),
        RenderLog(id="1", service_id="srv-a", service_name="proj-a-backend", timestamp=now, level="info", message="A ok"),
        RenderLog(id="2", service_id="srv-b", service_name="proj-b-backend", timestamp=now - timedelta(minutes=1),
                  level="error", message="B boom"),
    ])
    db.commit()
    db.close()
    monkeypatch.setattr(database, "SessionLocal", S)
    return S


def _fetch(urls):
    return asyncio.run(P._fetch_relevant_logs([], [], [], window_hours=24, project_urls=urls))


def test_logs_are_scoped_to_the_project(logs_db):
    assert {r["service_id"] for r in _fetch(["https://proj-a-backend.onrender.com"])} == {"srv-a"}
    # no service_url stored → the onrender.com subdomain is the service name
    assert {r["service_id"] for r in _fetch(["https://proj-b-backend.onrender.com/api"])} == {"srv-b"}
    # known URL that maps to nothing → nothing, never another project's logs
    assert _fetch(["https://elsewhere.example.com"]) == []
    # unknown project → old account-wide behaviour
    assert {r["service_id"] for r in _fetch([None])} == {"srv-a", "srv-b"}
