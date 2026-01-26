"""
AI Log Model - مدل لاگ‌های AI
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from datetime import datetime
import uuid

from ..core.database import Base


class AILog(Base):
    """جدول لاگ درخواست‌های AI"""
    __tablename__ = "ai_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # اطلاعات درخواست
    provider = Column(String(50), index=True)  # openai, claude, gemini, deepseek, groq
    model = Column(String(100), index=True)  # gpt-4, claude-3, etc.
    request_type = Column(String(50), index=True)  # chat, completion, embedding, image

    # محتوای درخواست و پاسخ
    prompt = Column(Text)  # prompt یا messages
    response = Column(Text)  # پاسخ AI

    # متادیتا
    project_id = Column(String(36), index=True, nullable=True)  # اگر مربوط به پروژه باشد
    debate_id = Column(String(36), index=True, nullable=True)  # اگر مربوط به debate باشد

    # آمار مصرف
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)  # هزینه به دلار

    # زمان‌ها
    latency_ms = Column(Integer, default=0)  # زمان پاسخ به میلی‌ثانیه
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # وضعیت
    status = Column(String(20), default="success")  # success, error, timeout
    error_message = Column(Text, nullable=True)

    # اطلاعات اضافی
    extra_data = Column(JSON, nullable=True)  # داده‌های اضافی به صورت JSON

    def to_dict(self):
        """تبدیل به dictionary"""
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "request_type": self.request_type,
            "prompt": self.prompt[:500] + "..." if self.prompt and len(self.prompt) > 500 else self.prompt,
            "response": self.response[:500] + "..." if self.response and len(self.response) > 500 else self.response,
            "project_id": self.project_id,
            "debate_id": self.debate_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def log_request(db, provider: str, model: str, request_type: str,
                    prompt: str, response: str = None,
                    input_tokens: int = 0, output_tokens: int = 0,
                    cost: float = 0.0, latency_ms: int = 0,
                    project_id: str = None, debate_id: str = None,
                    status: str = "success", error_message: str = None,
                    extra_data: dict = None):
        """ثبت یک درخواست AI"""
        log = AILog(
            provider=provider,
            model=model,
            request_type=request_type,
            prompt=prompt,
            response=response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            project_id=project_id,
            debate_id=debate_id,
            status=status,
            error_message=error_message,
            extra_data=extra_data,
        )
        db.add(log)
        db.commit()
        return log

    @staticmethod
    def get_stats(db, days: int = 30):
        """آمار مصرف AI در روزهای اخیر"""
        from sqlalchemy import func
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)

        stats = db.query(
            AILog.provider,
            func.count(AILog.id).label('request_count'),
            func.sum(AILog.total_tokens).label('total_tokens'),
            func.sum(AILog.cost).label('total_cost'),
            func.avg(AILog.latency_ms).label('avg_latency')
        ).filter(
            AILog.created_at >= since
        ).group_by(AILog.provider).all()

        return [
            {
                "provider": s.provider,
                "request_count": s.request_count,
                "total_tokens": s.total_tokens or 0,
                "total_cost": round(s.total_cost or 0, 4),
                "avg_latency": round(s.avg_latency or 0, 2)
            }
            for s in stats
        ]
