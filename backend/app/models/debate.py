"""
Debate Model - مدل مناظره
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class Debate(Base):
    """جدول مناظره‌ها"""
    __tablename__ = "debates"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), index=True)
    topic = Column(Text, nullable=False)  # موضوع مناظره
    status = Column(String(50), default="active", index=True)  # active, completed, archived

    # تنظیمات
    models = Column(JSON, default=list)  # لیست مدل‌های شرکت‌کننده
    work_mode = Column(String(50), default="debate")  # debate, collaborate, analyze
    max_rounds = Column(Integer, default=5)
    current_round = Column(Integer, default=0)

    # نتیجه
    conclusion = Column(Text)  # نتیجه‌گیری نهایی
    winner_model = Column(String(100))  # مدل برنده (اگر مناظره بود)

    # آمار
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    duration_seconds = Column(Integer)

    # زمان‌ها
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # روابط
    messages = relationship("DebateMessage", back_populates="debate", cascade="all, delete-orphan")

    def to_dict(self):
        """تبدیل به dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "status": self.status,
            "models": self.models or [],
            "work_mode": self.work_mode,
            "max_rounds": self.max_rounds,
            "current_round": self.current_round,
            "conclusion": self.conclusion,
            "winner_model": self.winner_model,
            "total_messages": self.total_messages,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DebateMessage(Base):
    """جدول پیام‌های مناظره"""
    __tablename__ = "debate_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    debate_id = Column(String(36), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False, index=True)

    # محتوا
    role = Column(String(20), nullable=False)  # user, assistant, system
    model_id = Column(String(100))  # مدل AI که پاسخ داده
    content = Column(Text, nullable=False)
    round_number = Column(Integer, default=1)

    # متادیتا
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer)  # زمان پاسخ
    cost = Column(Float, default=0.0)

    # زمان
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # روابط
    debate = relationship("Debate", back_populates="messages")

    def to_dict(self):
        """تبدیل به dictionary"""
        return {
            "id": self.id,
            "debate_id": self.debate_id,
            "role": self.role,
            "model_id": self.model_id,
            "content": self.content,
            "round_number": self.round_number,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
