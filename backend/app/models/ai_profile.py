"""
مدل پروفایل و اعتبارسنجی مدل‌های AI
AI Profile & Validation Model

نمرات تجمعی هستند و هیچوقت صفر نمی‌شوند!
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text
from sqlalchemy.sql import func
from ..core.database import Base
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AIProfile(Base):
    """پروفایل هر مدل AI - نمرات تجمعی و دائمی"""
    __tablename__ = "ai_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, unique=True, index=True, nullable=False)
    provider = Column(String, nullable=False)
    display_name = Column(String, nullable=True)

    # =====================
    # آمار کلی
    # =====================
    total_analyses = Column(Integer, default=0)  # تعداد کل تحلیل‌ها
    total_tasks = Column(Integer, default=0)  # تعداد کل وظایف
    total_debates = Column(Integer, default=0)  # تعداد شرکت در مناظره
    total_correct_findings = Column(Integer, default=0)  # یافته‌های صحیح
    total_missed_issues = Column(Integer, default=0)  # مشکلات از دست رفته
    total_false_positives = Column(Integer, default=0)  # هشدارهای اشتباه

    # =====================
    # نمرات تجمعی (0-100)
    # این نمرات هیچوقت صفر نمی‌شوند!
    # هر بررسی جدید میانگین متحرک محاسبه می‌شود
    # =====================

    # دقت کلی
    accuracy_score = Column(Float, default=100.0)  # Precision

    # کامل بودن
    completeness_score = Column(Float, default=100.0)  # Recall

    # سرعت پاسخ‌دهی
    speed_score = Column(Float, default=100.0)

    # قابلیت اعتماد (عدم خطا)
    reliability_score = Column(Float, default=100.0)

    # کیفیت کد تولیدی (برای code generation)
    code_quality_score = Column(Float, default=100.0)

    # کیفیت استدلال
    reasoning_score = Column(Float, default=100.0)

    # نمره کلی (میانگین وزن‌دار)
    overall_score = Column(Float, default=100.0)

    # =====================
    # رتبه‌بندی
    # =====================
    rank = Column(Integer, default=0)  # رتبه در بین همه مدل‌ها
    tier = Column(String, default="unranked")  # S, A, B, C, D, F

    # =====================
    # تاریخچه نمرات
    # =====================
    score_history = Column(JSON, default=[])  # [{timestamp, scores, task_type}]

    # آخرین نمرات هر نوع کار
    last_scores_by_task = Column(JSON, default={})  # {task_type: {scores}}

    # =====================
    # آمار عملکرد
    # =====================
    avg_response_time = Column(Float, default=0.0)  # میانگین زمان پاسخ (ثانیه)
    total_tokens_used = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)  # هزینه کل

    # =====================
    # قابلیت‌های اثبات‌شده
    # =====================
    proven_strengths = Column(JSON, default=[])  # قابلیت‌های اثبات‌شده
    proven_weaknesses = Column(JSON, default=[])  # ضعف‌های اثبات‌شده

    # =====================
    # متادیتا
    # =====================
    notes = Column(Text, nullable=True)  # یادداشت‌ها
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime, nullable=True)


class ModelValidationRecord(Base):
    """رکورد هر اعتبارسنجی مدل"""
    __tablename__ = "model_validation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, index=True, nullable=False)
    analysis_report_id = Column(String, index=True, nullable=True)

    # نوع کار
    task_type = Column(String, default="analysis")  # analysis, code_gen, debate, etc

    # نمرات این سنجش
    precision = Column(Float, default=0.0)  # درصد یافته‌های صحیح
    recall = Column(Float, default=0.0)  # درصد مشکلات شناسایی‌شده
    f1_score = Column(Float, default=0.0)  # میانگین هارمونیک

    # جزئیات
    correct_findings = Column(Integer, default=0)
    missed_issues = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)

    # متا
    response_time = Column(Float, default=0.0)  # ثانیه
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    # گزارش کامل
    details = Column(JSON, default={})

    created_at = Column(DateTime, default=func.now())


# =====================
# Pydantic Schemas
# =====================

class AIProfileSchema(BaseModel):
    """اسکیما پروفایل AI"""
    model_id: str
    provider: str
    display_name: Optional[str] = None

    total_analyses: int = 0
    total_tasks: int = 0

    accuracy_score: float = 100.0
    completeness_score: float = 100.0
    speed_score: float = 100.0
    reliability_score: float = 100.0
    code_quality_score: float = 100.0
    reasoning_score: float = 100.0
    overall_score: float = 100.0

    rank: int = 0
    tier: str = "unranked"

    avg_response_time: float = 0.0
    total_tokens_used: int = 0
    total_cost: float = 0.0

    proven_strengths: List[str] = []
    proven_weaknesses: List[str] = []

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIProfileSummarySchema(BaseModel):
    """خلاصه پروفایل برای نمایش"""
    model_id: str
    provider: str
    display_name: Optional[str] = None
    overall_score: float
    tier: str
    rank: int
    total_analyses: int

    class Config:
        from_attributes = True


class ModelValidationSchema(BaseModel):
    """اسکیما اعتبارسنجی"""
    model_id: str
    task_type: str
    precision: float
    recall: float
    f1_score: float
    correct_findings: int
    missed_issues: int
    false_positives: int
    response_time: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScoreHistoryEntry(BaseModel):
    """یک ورودی در تاریخچه نمرات"""
    timestamp: datetime
    task_type: str
    scores: Dict[str, float]
    details: Optional[Dict[str, Any]] = None


class ProfileUpdateRequest(BaseModel):
    """درخواست به‌روزرسانی پروفایل"""
    model_id: str
    task_type: str = "analysis"

    # نتایج اعتبارسنجی
    correct_findings: int = 0
    total_expected: int = 0  # تعداد کل مشکلات واقعی
    false_positives: int = 0  # هشدارهای اشتباه

    # متا
    response_time: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0

    # جزئیات اضافی
    details: Dict[str, Any] = {}
