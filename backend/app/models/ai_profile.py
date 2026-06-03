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


# =====================
# تنظیمات مدل‌ها (قابل ذخیره در دیتابیس)
# =====================

class ModelSettings(Base):
    """تنظیمات هر مدل AI - قابل مدیریت توسط کاربر"""
    __tablename__ = "model_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, unique=True, index=True, nullable=False)

    # وضعیت فعال بودن
    enabled = Column(Integer, default=1)  # 1=فعال، 0=غیرفعال
    temporary_enabled = Column(Integer, default=0)  # 1=موقتاً فعال برای یک task خاص

    # بخش‌های مجاز برای استفاده (JSON array)
    # مثال: ["chat", "analysis", "code_generation", "all"]
    allowed_tasks = Column(JSON, default=["all"])

    # اولویت (1 = بالاترین)
    priority = Column(Integer, default=5)

    # محدودیت‌ها
    max_tokens_override = Column(Integer, nullable=True)  # override برای max_tokens
    max_daily_requests = Column(Integer, default=0)  # 0 = نامحدود
    current_daily_requests = Column(Integer, default=0)
    last_request_date = Column(String, nullable=True)  # YYYY-MM-DD

    # ترجیحات
    preferred_for = Column(JSON, default=[])  # ["code", "reasoning", ...]
    fallback_model_id = Column(String, nullable=True)  # مدل جایگزین

    # هزینه و بودجه
    max_daily_cost = Column(Float, default=0.0)  # 0 = نامحدود
    current_daily_cost = Column(Float, default=0.0)

    # یادداشت کاربر
    notes = Column(Text, nullable=True)

    # تنظیمات پیشرفته (JSON)
    advanced_settings = Column(JSON, default={})
    # شامل: temperature, top_p, custom_system_prompt, etc.

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ModelSettingsSchema(BaseModel):
    """اسکیما تنظیمات مدل"""
    model_id: str
    enabled: bool = True
    allowed_tasks: List[str] = ["all"]
    priority: int = 5
    max_tokens_override: Optional[int] = None
    max_daily_requests: int = 0
    preferred_for: List[str] = []
    fallback_model_id: Optional[str] = None
    max_daily_cost: float = 0.0
    notes: Optional[str] = None
    advanced_settings: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class ModelSettingsUpdateRequest(BaseModel):
    """درخواست بروزرسانی تنظیمات مدل"""
    enabled: Optional[bool] = None
    allowed_tasks: Optional[List[str]] = None
    priority: Optional[int] = None
    max_tokens_override: Optional[int] = None
    max_daily_requests: Optional[int] = None
    preferred_for: Optional[List[str]] = None
    fallback_model_id: Optional[str] = None
    max_daily_cost: Optional[float] = None
    notes: Optional[str] = None
    advanced_settings: Optional[Dict[str, Any]] = None


# Task types that can be assigned to models
AVAILABLE_TASK_TYPES = [
    {"id": "all", "name": "همه کارها", "description": "استفاده در تمام بخش‌های برنامه"},
    {"id": "chat", "name": "چت", "description": "پرسش و پاسخ با AI در پروژه‌ها"},
    {"id": "analysis", "name": "تحلیل سلامت", "description": "تحلیل و بررسی سلامت کد"},
    {"id": "code_generation", "name": "تولید کد", "description": "تولید و نوشتن کد جدید"},
    {"id": "code_review", "name": "بررسی کد", "description": "بررسی و نقد کد موجود"},
    {"id": "documentation", "name": "مستندسازی", "description": "تولید README و مستندات"},
    {"id": "debugging", "name": "دیباگ", "description": "یافتن و رفع باگ‌ها"},
    {"id": "refactoring", "name": "ریفکتور", "description": "بهبود ساختار کد"},
    {"id": "testing", "name": "تست", "description": "نوشتن و اجرای تست‌ها"},
    {"id": "image_analysis", "name": "تحلیل تصویر", "description": "بررسی و تحلیل تصاویر"},
    {"id": "research", "name": "تحقیق", "description": "جستجو و تحقیق (Perplexity)"},
    # 🆕 (Cloud Code centralization) — 4 task type جدید که فقط برای entry
    # Cloud Code معنا دارند. هر کدام یک مصرف‌کنندهٔ مرکزی است: اگر کاربر
    # یکی را در ستون «ترجیحی برای» تیک نزند، آن مصرف‌کننده از Cloud Code
    # استفاده نمی‌کند و به‌رفتار پیش‌فرض خود بازمی‌گردد (alias `sonnet`
    # در workflow، local AI در inspector chat).
    {
        "id": "claude_auto_runner",
        "name": "اجرای خودکار",
        "description": "تسک‌ها در حالت اجرای خودکار (auto-runner) از Cloud Code استفاده کنند",
    },
    {
        "id": "claude_single_task",
        "name": "اجرای تکی از طریق کلاد",
        "description": "دکمهٔ «اجرا از طریق کلاد» روی هر کارت تسک",
    },
    {
        "id": "inspector_cloud_code",
        "name": "چت بازرس ویژه (Cloud Code)",
        "description": "engine انتخابی در inspector chat هنگام انتخاب Cloud Code",
    },
    {
        "id": "creator_engine",
        "name": "موتور خالق",
        "description": "ساخت/بازبینی پروژه در موتور خالق با Cloud Code",
    },
    # 🆕 (extraction routing) — Claude vision via OAuth برای استخراج
    # تصویر/PDF (بدون کسر از API key Gemini). برای صوت/ویدیو ساپورت ندارد
    # و خودکار به Gemini fallback می‌شود.
    {
        "id": "file_extraction",
        "name": "استخراج فایل‌های پیوست (تصویر/PDF)",
        "description": "استفاده از Cloud Code OAuth به‌جای کلید Gemini برای استخراج تصویر و PDF — بدون هزینهٔ کلید. صوت و ویدیو همیشه با Gemini.",
    },
]

# 🆕 (Cloud Code centralization) — لیست id های preferred_for که فقط مربوط
# به entry Cloud Code هستند. هر consumer با یکی از این key ها از helper
# مرکزی می‌پرسد «آیا برای این کار از Cloud Code استفاده کنم؟».
CLOUD_CODE_PREFERRED_FOR_KEYS = [
    "claude_auto_runner",
    "claude_single_task",
    "inspector_cloud_code",
    "creator_engine",
    "file_extraction",
]
