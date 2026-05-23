# -*- coding: utf-8 -*-
"""
مدل دیتابیس برای ذخیره سشن‌ها و پیام‌های بازرس هوشمند
"""

import json
from datetime import timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


def _utc_iso(dt):
    """تبدیل datetime ذخیره‌شده در DB (که naive ولی UTC است) به ISO string با
    «Z» نهایی — برای جلوگیری از misparse در JavaScript به‌عنوان local time.

    اگر datetime tz-aware باشد، آن را به UTC تبدیل و سپس «Z» می‌گذارد.
    """
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            # naive — فرض می‌کنیم UTC است (سرور Render UTC اجرا می‌شود)
            return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        # tz-aware — به UTC تبدیل کن
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


class InspectorSession(Base):
    """سشن‌های بازرس هوشمند"""
    __tablename__ = "inspector_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), nullable=False, index=True)
    status = Column(String(20), default="active")  # active, archived
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)

    messages = relationship("InspectorMessage", back_populates="session", cascade="all, delete-orphan",
                            order_by="InspectorMessage.timestamp")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "title": self.title,
            # 🆕 timezone-fix: created_at در DB naive ذخیره می‌شود ولی محتوایش
            # UTC است (سرور Render UTC اجرا می‌شود). برای جلوگیری از misparse در
            # JavaScript به‌عنوان local time، صریحاً «Z» اضافه می‌کنیم.
            "created_at": _utc_iso(self.created_at),
            "closed_at": _utc_iso(self.closed_at),
            "message_count": len(self.messages) if self.messages else 0,
        }


class InspectorMessage(Base):
    """پیام‌های بازرس هوشمند"""
    __tablename__ = "inspector_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("inspector_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system, action
    content = Column(Text, nullable=False)
    action_type = Column(String(50), nullable=True)  # click, scroll, input, navigate, focus, hover
    model_id = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    backend_verified = Column(Boolean, nullable=True)  # null=pending, True=ok, False=error
    backend_log_summary = Column(Text, nullable=True)  # خلاصه بررسی لاگ بک‌اند
    verified_by_model = Column(String(100), nullable=True)  # مدلی که تأیید رو انجام داده
    logs_checked = Column(Integer, nullable=True)  # تعداد لاگ‌های بررسی شده
    error_logs_count = Column(Integer, nullable=True)  # تعداد لاگ‌های خطا
    checked_logs_data = Column(Text, nullable=True)  # JSON array of checked log entries
    extra_data = Column(Text, nullable=True)  # JSON: visual_debug_packs, action_plan, is_visual_debug_report, enhanced_prompt, ...
    timestamp = Column(DateTime, server_default=func.now())

    session = relationship("InspectorSession", back_populates="messages")

    def to_dict(self):
        _extra = {}
        if self.extra_data:
            try:
                _extra = json.loads(self.extra_data)
            except Exception:
                _extra = {}
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "action_type": self.action_type,
            "model_id": self.model_id,
            "tokens_used": self.tokens_used,
            "backend_verified": self.backend_verified,
            "backend_log_summary": self.backend_log_summary,
            "verified_by_model": self.verified_by_model,
            "logs_checked": self.logs_checked,
            "error_logs_count": self.error_logs_count,
            "checked_logs": json.loads(self.checked_logs_data) if self.checked_logs_data else [],
            # 🆕 timezone-fix (به دلیل بالا): timestamp را به‌عنوان UTC explicit
            # serialize می‌کنیم تا frontend (JavaScript) آن را local تفسیر نکند.
            "timestamp": _utc_iso(self.timestamp),
            **_extra,
        }
