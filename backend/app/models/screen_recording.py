# -*- coding: utf-8 -*-
"""
مدل دیتابیس برای ذخیره metadata ضبط‌های صفحه (Screen Recording).

هر رکورد یک جلسهٔ ضبط ویدئو/صدا از «بازرس ویژه» را نگه می‌دارد:
فایل ویدئو، فایل صدا (میکروفون/سیستم)، transcript صوت، لاگ‌های
console/backend که حین ضبط جمع شده، و رویدادهای تعامل کاربر
(کلیک/ناوبری/scroll). این داده‌ها ورودی ساخت «پرامپت قوی» هستند.
"""

import json
from datetime import timezone
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.sql import func

from ..core.database import Base


def _utc_iso(dt):
    """تبدیل datetime ذخیره‌شده در DB (naive ولی UTC) به ISO با «Z» نهایی."""
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


class ScreenRecording(Base):
    """متادیتای یک جلسهٔ ضبط صفحه از بازرس ویژه."""
    __tablename__ = "screen_recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), nullable=False, index=True)
    inspector_session_id = Column(String(100), nullable=True, index=True)

    # فایل‌های ذخیره‌شده (file_id از storage_service)
    video_file_id = Column(String(100), nullable=True)
    audio_file_id = Column(String(100), nullable=True)

    # تنظیمات صوت هنگام ضبط: mic | system | both | none
    audio_source = Column(String(20), default="mic")
    # حالت هندزفری (echoCancellation/noiseSuppression خاموش) — صرفاً metadata
    handsfree = Column(String(10), default="false")

    duration_ms = Column(Integer, nullable=True)

    # transcript حاصل از تبدیل گفتار به متن
    transcript = Column(Text, nullable=True)

    # JSON arrays
    console_logs = Column(Text, nullable=True)       # [{level,message,timestamp,source}]
    backend_logs = Column(Text, nullable=True)       # [{level,message,timestamp,service_id}]
    user_interactions = Column(Text, nullable=True)  # [{type,target,page_url,timestamp,...}]

    status = Column(String(20), default="recording")  # recording, ready, transcribed, error
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ---- helpers ----
    @staticmethod
    def _loads(val):
        if not val:
            return []
        try:
            data = json.loads(val)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "inspector_session_id": self.inspector_session_id,
            "video_file_id": self.video_file_id,
            "audio_file_id": self.audio_file_id,
            "audio_source": self.audio_source,
            "handsfree": (str(self.handsfree).lower() == "true"),
            "duration_ms": self.duration_ms,
            "transcript": self.transcript,
            "console_logs": self._loads(self.console_logs),
            "backend_logs": self._loads(self.backend_logs),
            "user_interactions": self._loads(self.user_interactions),
            "status": self.status,
            "created_at": _utc_iso(self.created_at),
            "updated_at": _utc_iso(self.updated_at),
        }
