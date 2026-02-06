# -*- coding: utf-8 -*-
"""
مدل دیتابیس برای ذخیره سشن‌ها و پیام‌های بازرس هوشمند
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
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
    timestamp = Column(DateTime, server_default=func.now())

    session = relationship("InspectorSession", back_populates="messages")

    def to_dict(self):
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
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
