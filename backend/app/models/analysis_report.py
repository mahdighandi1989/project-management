"""
مدل گزارش تحلیل پروژه
Analysis Report Model
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AnalysisReport(Base):
    """جدول گزارش‌های تحلیل"""
    __tablename__ = "analysis_reports"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True, nullable=False)

    # زمان و وضعیت
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed

    # مدل‌های استفاده‌شده
    models_used = Column(JSON, default=[])

    # نمرات کلی
    overall_score = Column(Float, default=0.0)  # 0-100
    overall_color = Column(String, default="red")  # green, yellow, orange, red

    # نمرات جزئی
    code_quality_score = Column(Float, default=0.0)
    documentation_score = Column(Float, default=0.0)
    security_score = Column(Float, default=0.0)
    structure_score = Column(Float, default=0.0)
    roadmap_compliance_score = Column(Float, default=0.0)

    # تحلیل‌های جزئی
    file_analyses = Column(JSON, default=[])  # لیست تحلیل هر فایل
    structure_analysis = Column(JSON, default={})  # تحلیل ساختار
    roadmap_comparison = Column(JSON, default={})  # مقایسه با نقشه راه

    # پیشنهادات و نتایج
    issues_found = Column(JSON, default=[])  # مشکلات یافت‌شده
    recommendations = Column(JSON, default=[])  # پیشنهادات بهبود
    summary = Column(Text, nullable=True)  # خلاصه گزارش

    # اعتبارسنجی مدل‌ها
    model_validations = Column(JSON, default={})  # نمرات مدل‌ها در این تحلیل


class FileAnalysis(Base):
    """جدول تحلیل هر فایل"""
    __tablename__ = "file_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("analysis_reports.id"), index=True)
    file_path = Column(String, nullable=False)

    # نمرات
    score = Column(Float, default=0.0)
    color = Column(String, default="red")

    # نمرات جزئی
    code_quality = Column(Float, default=0.0)
    documentation = Column(Float, default=0.0)
    security = Column(Float, default=0.0)
    best_practices = Column(Float, default=0.0)

    # جزئیات
    issues = Column(JSON, default=[])
    suggestions = Column(JSON, default=[])
    analysis_by_model = Column(JSON, default={})  # تحلیل هر مدل جداگانه

    created_at = Column(DateTime, default=func.now())


class AnalysisSchedule(Base):
    """جدول زمان‌بندی تحلیل‌های خودکار"""
    __tablename__ = "analysis_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, index=True, nullable=False)

    # تنظیمات زمان‌بندی
    enabled = Column(Integer, default=1)  # 0 = غیرفعال, 1 = فعال
    interval = Column(String, default="daily")  # hourly, daily, weekly, manual
    time = Column(String, default="02:00")  # ساعت اجرا (برای daily)
    day_of_week = Column(Integer, default=0)  # روز هفته (برای weekly)

    # تنظیمات تحلیل
    models = Column(JSON, default=[])  # مدل‌های منتخب
    criteria_weights = Column(JSON, default={
        "code_quality": 0.25,
        "documentation": 0.15,
        "security": 0.20,
        "structure": 0.20,
        "roadmap_compliance": 0.20
    })
    thresholds = Column(JSON, default={
        "critical": 50,
        "warning": 70,
        "good": 85
    })

    # آمار
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    total_runs = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# =====================
# Pydantic Schemas
# =====================

class FileAnalysisSchema(BaseModel):
    """اسکیما تحلیل فایل"""
    file_path: str
    score: float = 0.0
    color: str = "red"
    code_quality: float = 0.0
    documentation: float = 0.0
    security: float = 0.0
    best_practices: float = 0.0
    issues: List[Dict[str, Any]] = []
    suggestions: List[str] = []
    analysis_by_model: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class AnalysisReportSchema(BaseModel):
    """اسکیما گزارش تحلیل"""
    id: str
    project_id: str
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    models_used: List[str] = []
    overall_score: float = 0.0
    overall_color: str = "red"

    code_quality_score: float = 0.0
    documentation_score: float = 0.0
    security_score: float = 0.0
    structure_score: float = 0.0
    roadmap_compliance_score: float = 0.0

    file_analyses: List[FileAnalysisSchema] = []
    issues_found: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    summary: Optional[str] = None

    model_validations: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class AnalysisScheduleSchema(BaseModel):
    """اسکیما زمان‌بندی"""
    project_id: str
    enabled: bool = True
    interval: str = "daily"
    time: str = "02:00"
    day_of_week: int = 0
    models: List[str] = []
    criteria_weights: Dict[str, float] = {}
    thresholds: Dict[str, int] = {}

    class Config:
        from_attributes = True


class AnalysisRequestSchema(BaseModel):
    """اسکیما درخواست تحلیل"""
    project_id: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    analyze_files: bool = True
    analyze_structure: bool = True
    compare_roadmap: bool = True
    full_analysis: bool = True  # بدون خلاصه‌سازی
