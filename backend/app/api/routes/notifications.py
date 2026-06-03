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
    # 🆕 (Daily Report) — تنظیمات گزارش دوره‌ای
    daily_report: Optional[Dict[str, Any]] = None


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
    if payload.daily_report is not None:
        partial["daily_report"] = payload.daily_report
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

    🛡 (safety net) — هر چیزی در handler به استثنا برسد، باز هم {"ok": True}
    برگردانیم تا Telegram retry نکند (که باعث flood می‌شود). loggerبا
    exception کامل وضعیت را روی Render قابل دیدن می‌کند.
    """
    import logging as _logging_wh
    _wh_logger = _logging_wh.getLogger(__name__)
    try:
        body = await request.json()
    except Exception as _je:
        _wh_logger.warning(f"telegram webhook: invalid JSON body: {_je}")
        return {"ok": True}
    try:
        result = await notification_service.handle_telegram_update(body)
        # diagnostic log اگر handler ای ignored برگرداند ولی پیام دستوری بود
        if result.get("ignored") and (body.get("message") or {}).get("text"):
            _wh_logger.info(
                f"telegram webhook: ignored text='{(body.get('message') or {}).get('text', '')[:60]}' "
                f"reason='{result.get('error') or 'configured_id_mismatch'}'"
            )
        return result
    except Exception as _e:
        _wh_logger.exception(f"telegram webhook handler crashed: {_e}")
        # تلاش برای پاسخ‌دهی به کاربر — حداقل بداند backend در دسترس است
        try:
            chat_id = (body.get("message") or {}).get("chat", {}).get("id") \
                or (body.get("callback_query") or {}).get("message", {}).get("chat", {}).get("id")
            if chat_id:
                await notification_service._telegram().send(
                    f"⚠️ خطای داخلی در پردازش دستور:\n`{str(_e)[:200]}`\n\n"
                    f"می‌توانی /kb بزنی تا منو برگردد یا /ping برای تست.",
                    silent=True,
                )
        except Exception:
            pass
        # Always return 200 — تا Telegram retry نکند
        return {"ok": True, "handler_error": str(_e)[:200]}


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


# ──────────────────────────────────────────────────────────────────────────
# 🆕 (Daily Report) endpoints برای preview + send-now
# ──────────────────────────────────────────────────────────────────────────

@router.get("/daily-report/preview")
async def preview_daily_report():
    """preview بدون ارسال — برای دیدن متن خروجی + summary در UI."""
    from ...services.oversight_service import get_oversight_service
    from ...services.notification_service import format_health_report_message
    service = get_oversight_service()
    summary = await service.compute_global_health_summary()
    prefs = notification_service.get_prefs()
    text, reply_markup = format_health_report_message(
        summary, app_base_url=prefs.get("app_base_url", "")
    )
    return {
        "summary": summary,
        "preview_text": text,
        "reply_markup": reply_markup,
        "char_count": len(text),
    }


@router.post("/daily-report/send-now")
async def send_daily_report_now():
    """ارسال فوری گزارش — برای تست manual."""
    from ...services.oversight_service import get_oversight_service
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        prefs = notification_service.get_prefs()
        tz_name = (prefs.get("daily_report", {}) or {}).get("timezone", "Asia/Tehran")
        local_now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        local_now = datetime.now()

    service = get_oversight_service()
    summary = await service.compute_global_health_summary()
    results = await notification_service.send_daily_report(summary)
    ok = any(r.get("ok") for r in results) if results else False
    notification_service.update_prefs({
        "daily_report": {
            "last_sent_at": local_now.isoformat(),
            "last_sent_status": "ok" if ok else ("no_channel_ready" if not results else "failed"),
        }
    })
    return {"ok": ok, "results": results, "channels_count": len(results)}
