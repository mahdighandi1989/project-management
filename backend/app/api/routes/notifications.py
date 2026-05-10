"""API endpoints برای مدیریت notifications.

GET  /api/notifications/status              وضعیت + events_registry
PUT  /api/notifications/prefs               به‌روزرسانی toggleها/sound/min_priority/app_url
POST /api/notifications/test                ارسال تست (channel اختیاری)
POST /api/notifications/notify              ارسال دستی یک event (برای testing)
POST /api/notifications/telegram/webhook    دریافت updates از Telegram (commands)
POST /api/notifications/telegram/set-webhook  ست webhook URL با Telegram API
POST /api/notifications/telegram/delete-webhook
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PrefsUpdate(BaseModel):
    events: Optional[Dict[str, bool]] = None
    sound: Optional[Dict[str, bool]] = None
    channels: Optional[Dict[str, Dict[str, Any]]] = None
    min_priority: Optional[str] = None
    include_hashtags: Optional[bool] = None
    include_inline_buttons: Optional[bool] = None
    app_base_url: Optional[str] = None


class TestRequest(BaseModel):
    channel: Optional[str] = None  # 'telegram' | 'email' | None (= همه)


class NotifyRequest(BaseModel):
    event: str
    message: str
    subject: Optional[str] = None
    priority: str = "low"
    project_name: Optional[str] = None
    watched_id: Optional[str] = None


class WebhookRequest(BaseModel):
    webhook_url: str


@router.get("/status")
async def get_status():
    return notification_service.get_status()


@router.put("/prefs")
async def update_prefs(payload: PrefsUpdate):
    partial: Dict[str, Any] = {}
    if payload.events is not None:
        partial["events"] = payload.events
    if payload.sound is not None:
        partial["sound"] = payload.sound
    if payload.channels is not None:
        partial["channels"] = payload.channels
    if payload.min_priority is not None:
        if payload.min_priority not in ("low", "medium", "high", "critical"):
            raise HTTPException(status_code=400, detail="min_priority نامعتبر")
        partial["min_priority"] = payload.min_priority
    if payload.include_hashtags is not None:
        partial["include_hashtags"] = payload.include_hashtags
    if payload.include_inline_buttons is not None:
        partial["include_inline_buttons"] = payload.include_inline_buttons
    if payload.app_base_url is not None:
        partial["app_base_url"] = payload.app_base_url.strip()
    updated = notification_service.update_prefs(partial)
    return {"ok": True, "prefs": updated}


@router.post("/test")
async def test_send(payload: TestRequest):
    results = await notification_service.test_send(channel=payload.channel)
    any_ok = any(r.get("ok") for r in results)
    return {"ok": any_ok, "results": results}


@router.post("/notify")
async def notify_now(payload: NotifyRequest):
    """ارسال دستی یک event — برای testing مسیرهای مختلف از پنل."""
    results = await notification_service.notify_event(
        payload.event,
        payload.message,
        subject=payload.subject,
        priority=payload.priority,
        project_name=payload.project_name,
        watched_id=payload.watched_id,
    )
    return {"ok": any(r.get("ok") for r in results), "results": results}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """endpoint که Telegram update‌ها را به آن می‌فرستد.

    باید با /telegram/set-webhook ست شود تا Telegram به این URL POST کند.
    """
    try:
        body = await request.json()
    except Exception:
        return {"ok": True}
    return await notification_service.handle_telegram_update(body)


@router.post("/telegram/set-webhook")
async def set_webhook(payload: WebhookRequest):
    """ست‌کردن webhook URL با Telegram. مثلاً:
    {"webhook_url": "https://your-backend.onrender.com/api/notifications/telegram/webhook"}
    """
    tg = notification_service._telegram()
    return await tg.set_webhook(payload.webhook_url)


@router.post("/telegram/delete-webhook")
async def delete_webhook():
    tg = notification_service._telegram()
    return await tg.delete_webhook()
