"""
Oversight Settings Helpers
===========================
نگاشت‌های قابل تنظیم کاربر برای feature extraction. در جدول `settings` ذخیره
می‌شوند با کلیدهای زیر:

- `oversight.extraction.default_model_id`  → str
- `oversight.extraction.candidate_model_ids` → list[str] (آماده برای آینده)

استفاده ساده بدون نیاز به session-management:
    from .oversight_settings import get_default_extraction_model_id_from_db
    mid = get_default_extraction_model_id_from_db()  # None اگر تنظیم نشده
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

KEY_DEFAULT_EXTRACTION_MODEL = "oversight.extraction.default_model_id"


def get_default_extraction_model_id_from_db() -> Optional[str]:
    """مدل پیش‌فرض extraction از DB — اگر کاربر در /models تنظیم کرده باشد.

    خروجی None اگر تنظیم نشده، یا اگر DB در دسترس نباشد (silent fail).
    """
    try:
        from ..core.database import SessionLocal
        from ..models.setting import Setting
        db = SessionLocal()
        try:
            val = Setting.get_value(db, KEY_DEFAULT_EXTRACTION_MODEL, default=None)
            if isinstance(val, str) and val.strip():
                return val.strip()
            return None
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"get_default_extraction_model_id_from_db failed (non-fatal): {e}")
        return None


def set_default_extraction_model_id_in_db(model_id: Optional[str]) -> bool:
    """تنظیم مدل پیش‌فرض extraction. اگر model_id خالی یا None، تنظیم پاک می‌شود.

    خروجی True در صورت موفقیت.
    """
    try:
        from ..core.database import SessionLocal
        from ..models.setting import Setting
        db = SessionLocal()
        try:
            Setting.set_value(
                db,
                KEY_DEFAULT_EXTRACTION_MODEL,
                value=(model_id or "").strip(),
                value_type="string",
                category="oversight_extraction",
            )
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"set_default_extraction_model_id_in_db failed: {e}")
        return False
