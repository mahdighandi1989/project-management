"""API endpoints برای مدیریت notifications.

GET  /api/notifications/status         وضعیت env + prefs
PUT  /api/notifications/prefs          به‌روزرسانی toggleها/min_priority
POST /api/notifications/test           ارسال تست (channel اختیاری)
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PrefsUpdate(BaseModel):
    events: Optional[Dict[str, bool]] = None
    channels: Optional[Dict[str, Dict[str, Any]]] = None
    min_priority: Optional[str] = None


class TestRequest(BaseModel):
    channel: Optional[str] = None  # 'telegram' | 'email' | None (= همه)


@router.get("/status")
async def get_status():
    return notification_service.get_status()


@router.put("/prefs")
async def update_prefs(payload: PrefsUpdate):
    partial: Dict[str, Any] = {}
    if payload.events is not None:
        partial["events"] = payload.events
    if payload.channels is not None:
        partial["channels"] = payload.channels
    if payload.min_priority is not None:
        if payload.min_priority not in ("low", "medium", "high", "critical"):
            raise HTTPException(status_code=400, detail="min_priority نامعتبر")
        partial["min_priority"] = payload.min_priority
    updated = notification_service.update_prefs(partial)
    return {"ok": True, "prefs": updated}


@router.post("/test")
async def test_send(payload: TestRequest):
    results = await notification_service.test_send(channel=payload.channel)
    any_ok = any(r.get("ok") for r in results)
    return {"ok": any_ok, "results": results}
