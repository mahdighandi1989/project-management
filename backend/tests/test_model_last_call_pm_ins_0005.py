# -*- coding: utf-8 -*-
"""PM-INS-0005 (2026-11-15): a capability-test 0 that is really a failed call says so (errors, all_failed) and the
last REAL call is remembered per model (advanced_settings["last_call"]) so «API ✓» means a real success; the owner's
explicit enable clears the temporary flag; toggling a model without a DB row flips the registry default."""
import asyncio
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base  # noqa: E402
from app.models.ai_profile import ModelSettings  # noqa: E402
from app.services import model_capability_tester as mct  # noqa: E402


@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng, tables=[ModelSettings.__table__])
    Sess = sessionmaker(bind=eng)
    monkeypatch.setattr("app.core.database.SessionLocal", Sess)

    def _get_db():
        db = Sess()
        try:
            yield db
        finally:
            db.close()
    monkeypatch.setattr("app.core.database.get_db", _get_db)
    return Sess


class _FailingManager:
    async def generate(self, **kw):
        raise RuntimeError("401 invalid x-api-key")


class _OkManager:
    async def generate(self, **kw):
        return '{"score": 80, "strengths": ["a"]}'


def test_all_failed_reports_real_error_and_records_last_call(mem_db):
    res = asyncio.run(mct.ModelCapabilityTester(_FailingManager()).test_model("gpt-4o-mini"))
    assert res["all_failed"] is True and res["calls_ok"] == 0 and res["calls_total"] > 0
    assert any("invalid x-api-key" in e for e in res["errors"])
    row = mem_db().query(ModelSettings).filter_by(model_id="gpt-4o-mini").first()
    lc = row.advanced_settings["last_call"]
    assert lc["ok"] is False and "invalid x-api-key" in lc["error"] and lc["source"] == "capability_test"


def test_success_records_ok(mem_db):
    res = asyncio.run(mct.ModelCapabilityTester(_OkManager()).test_model("gpt-4o-mini"))
    assert res["all_failed"] is False and res["errors"] == []
    row = mem_db().query(ModelSettings).filter_by(model_id="gpt-4o-mini").first()
    assert row.advanced_settings["last_call"]["ok"] is True and row.advanced_settings["last_call"]["error"] is None


def test_record_last_call_never_raises(monkeypatch):
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr("app.core.database.SessionLocal", boom)
    mct.record_last_call("x", ok=False, error="e")  # must not raise


def test_owner_enable_clears_temporary_flag_and_toggle_flips_registry_default():
    src = (Path(__file__).resolve().parents[1] / "app/api/routes/models.py").read_text(encoding="utf-8")
    assert src.count("setting.temporary_enabled = 0") >= 3
    assert "enabled=0 if _reg_on else 1" in src
    assert "last_call=((db_setting.advanced_settings or {}).get(\"last_call\")" in src
