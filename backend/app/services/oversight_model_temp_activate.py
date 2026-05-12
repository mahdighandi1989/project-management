"""
Oversight — Temporary Model Activation
=======================================
وقتی کاربر فایلی پیوست می‌کند ولی هیچ مدل بصری enabled نیست، می‌توانیم
یک مدل را **موقتاً** فعال کنیم → کار را انجام دهیم → دوباره disable کنیم.

این service آن flow را مدیریت می‌کند، با اطلاع‌رسانی به کاربر در هر دو
نقطه (activation + revert) از طریق Telegram (و سایر کانال‌های پیکربندی‌شده).

ویژگی‌ها:
- in-memory tracker برای مدل‌هایی که موقتاً فعال شده‌اند
- detection: اگر backend restart کرد، در startup hook بررسی می‌کنیم
  که آیا temporary_enabled=1 در DB مانده ولی trigger مرتبط (extraction)
  ناتمام مانده → revert خودکار
- atomic — هر model_id فقط یک temp_activation فعال
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.models_registry import (
    MODEL_REGISTRY, get_model, list_extraction_model_candidates,
)
from ..models.ai_profile import ModelSettings

logger = logging.getLogger(__name__)

# in-memory tracker: model_id → {trigger, activated_at, original_enabled}
_active: Dict[str, Dict[str, Any]] = {}
_lock = asyncio.Lock()


def _db_setting(db: Session, model_id: str) -> ModelSettings:
    s = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
    if s is None:
        s = ModelSettings(model_id=model_id, enabled=0, temporary_enabled=0)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


async def _notify(message: str) -> None:
    """ارسال notification (best-effort) — اگر کانال‌ها پیکربندی نشده، silent."""
    try:
        from .notification_service import notification_service
        await notification_service.notify_event(
            "verify_partial",  # event با default_enabled=True که caption متن دلخواه را قبول می‌کند
            message,
            subject="فعال‌سازی موقت مدل",
            priority="medium",
        )
    except Exception as e:
        logger.debug(f"temp_activate notify failed (non-fatal): {e}")


async def temp_activate_model(model_id: str, trigger: str = "") -> Dict[str, Any]:
    """فعال‌سازی موقت یک مدل. اگر قبلاً enabled بود، حالت اصلی ثبت می‌شود
    تا revert به همان حالت برگردد.

    در DB: enabled هم به 1 ست می‌شود (چون ai_manager فعلاً فقط enabled را
    نگاه می‌کند، نه temporary_enabled). temporary_enabled=1 هم ست می‌شود
    تا revert بداند که این auto-activation بوده.

    خروجی: {model_id, name, was_originally_enabled, message}
    """
    m = get_model(model_id)
    if m is None:
        raise ValueError(f"مدل {model_id} ناشناخته است")

    async with _lock:
        if model_id in _active:
            return {
                "model_id": model_id,
                "name": m.name,
                "was_originally_enabled": _active[model_id].get("original_enabled", False),
                "message": f"مدل {m.name} از قبل موقتاً فعال است",
                "already_active": True,
            }
        db = SessionLocal()
        try:
            s = _db_setting(db, model_id)
            was_enabled = bool(s.enabled)
            s.enabled = 1
            s.temporary_enabled = 1
            db.commit()
            # registry هم به‌روز کن (in-memory) — تا pick_best_extraction_model
            # بلافاصله ببیند
            try:
                MODEL_REGISTRY[model_id].enabled = True
            except Exception:
                pass
            _active[model_id] = {
                "trigger": trigger,
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "original_enabled": was_enabled,
            }
        finally:
            db.close()

    await _notify(
        f"🔓 *مدل {m.name} موقتاً فعال شد*\n"
        f"📌 برای: `{trigger or '-'}`\n"
        f"⏳ پس از اتمام کار، خودکار به وضعیت قبل برمی‌گردد."
    )
    return {
        "model_id": model_id,
        "name": m.name,
        "was_originally_enabled": was_enabled,
        "message": f"مدل {m.name} موقتاً فعال شد",
    }


async def temp_revert_model(model_id: str, trigger: str = "") -> Dict[str, Any]:
    """برگرداندن مدل به حالت اصلی پس از پایان کار.

    اگر original_enabled=True → فقط temporary_enabled=0 (enabled همان True)
    اگر original_enabled=False → enabled=0 + temporary_enabled=0
    """
    m = get_model(model_id)
    if m is None:
        return {"model_id": model_id, "reverted": False, "reason": "model not found"}

    async with _lock:
        info = _active.pop(model_id, None)
        original_enabled = info.get("original_enabled", False) if info else False
        db = SessionLocal()
        try:
            s = _db_setting(db, model_id)
            s.temporary_enabled = 0
            if not original_enabled:
                s.enabled = 0
                try:
                    MODEL_REGISTRY[model_id].enabled = False
                except Exception:
                    pass
            else:
                s.enabled = 1
                try:
                    MODEL_REGISTRY[model_id].enabled = True
                except Exception:
                    pass
            db.commit()
        finally:
            db.close()

    if info is None:
        # هیچ‌گاه فعال نشده بود از طریق این service — silent
        return {"model_id": model_id, "reverted": False, "reason": "not in active list"}

    await _notify(
        f"🔒 *مدل {m.name} غیرفعال شد*\n"
        f"📌 trigger: `{trigger or info.get('trigger', '-')}`\n"
        f"✅ کار خاتمه یافت — مدل به حالت قبل ({'enabled' if original_enabled else 'disabled'}) برگشت."
    )
    return {
        "model_id": model_id,
        "name": m.name,
        "reverted": True,
        "restored_to_enabled": original_enabled,
    }


def get_active_temp_activations() -> Dict[str, Dict[str, Any]]:
    """snapshot از فعال‌سازی‌های موقت فعلی (برای /status endpoint)."""
    return {k: dict(v) for k, v in _active.items()}


async def cleanup_stale_temp_activations_on_boot() -> int:
    """هنگام boot، اگر temporary_enabled=1 در DB مانده ولی _active خالی است
    (یعنی restart بدون revert)، آن‌ها را revert کن تا state پاک شود.
    """
    n = 0
    db = SessionLocal()
    try:
        items = db.query(ModelSettings).filter(ModelSettings.temporary_enabled == 1).all()
        for s in items:
            # ما نمی‌دانیم original_enabled چه بوده — محافظه‌کارانه: کاربر
            # بهتر است خودش دوباره enable کند، پس فعلاً temporary_enabled=0
            # می‌کنیم ولی enabled را دست نمی‌زنیم (محافظت در برابر حذف ناخواسته).
            s.temporary_enabled = 0
            n += 1
        if n:
            db.commit()
            logger.info(f"temp_activate boot cleanup: cleared temporary_enabled for {n} models")
    except Exception as e:
        logger.warning(f"temp_activate boot cleanup failed: {e}")
    finally:
        db.close()
    return n


def check_extraction_model_availability(
    mime_type: str,
    *,
    preferred_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """بررسی: آیا برای این mime یک مدل enabled مناسب وجود دارد؟

    خروجی:
      {available: True, model_id, name} اگر موجود
      {available: False, candidates: [{id, name, provider}]} اگر نیست
    """
    from ..core.models_registry import pick_best_extraction_model
    # ابتدا سعی کن مدل enabled پیدا کنی
    m = pick_best_extraction_model(mime_type, preferred_model_id=preferred_model_id)
    if m is not None:
        return {"available": True, "model_id": m.id, "name": m.name}
    # هیچ enabled نبود → کاندیداهای disabled را برگردان
    cands = list_extraction_model_candidates(mime_type, include_disabled=True)
    return {
        "available": False,
        "candidates": [
            {"id": c.id, "name": c.name, "provider": c.provider.value, "priority": c.priority}
            for c in cands[:5]
        ],
    }
