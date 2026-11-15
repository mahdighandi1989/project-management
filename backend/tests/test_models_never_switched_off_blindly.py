"""«مدل‌ها همه رفتند» (2026-11-15): a temp-activation revert with no record, or the boot cleanup, must never switch
off a model the owner switched on."""

import asyncio

from app.core.database import SessionLocal, init_db
from app.models.ai_profile import ModelSettings
from app.services import oversight_model_temp_activate as TA


def _row(mid, enabled, temp):
    init_db()
    db = SessionLocal()
    r = db.query(ModelSettings).filter(ModelSettings.model_id == mid).first()
    if r is None:
        r = ModelSettings(model_id=mid)
        db.add(r)
    r.enabled, r.temporary_enabled = enabled, temp
    db.commit()
    db.close()


def _get(mid):
    db = SessionLocal()
    try:
        r = db.query(ModelSettings).filter(ModelSettings.model_id == mid).first()
        return int(r.enabled or 0), int(r.temporary_enabled or 0)
    finally:
        db.close()


def test_revert_without_record_leaves_the_model_alone():
    mid = "deepseek-chat"
    _row(mid, 1, 0)
    TA._active.pop(mid, None)
    res = asyncio.run(TA.temp_revert_model(mid, trigger="test"))
    assert res["reverted"] is False
    assert _get(mid)[0] == 1


def test_boot_cleanup_only_clears_the_flag():
    mid = "deepseek-chat"
    _row(mid, 1, 1)  # legacy row: owner-enabled model carrying the old flag
    asyncio.run(TA.cleanup_stale_temp_activations_on_boot())
    assert _get(mid) == (1, 0)


def test_activate_then_revert_restores_exactly():
    mid = "deepseek-chat"
    _row(mid, 0, 0)
    asyncio.run(TA.temp_activate_model(mid, trigger="t"))
    assert _get(mid) == (1, 1)
    asyncio.run(TA.temp_revert_model(mid, trigger="t"))
    assert _get(mid) == (0, 0)
    _row(mid, 1, 0)
    asyncio.run(TA.temp_activate_model(mid, trigger="t"))
    asyncio.run(TA.temp_revert_model(mid, trigger="t"))
    asyncio.run(TA.temp_revert_model(mid, trigger="t"))  # a second revert must not switch it off
    assert _get(mid)[0] == 1
