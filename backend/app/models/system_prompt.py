"""
SystemPrompt Model - مدل پرامپت‌های سیستم
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum as SQLEnum
from datetime import datetime
import enum
import json
import uuid

from ..core.database import Base


class PromptCategory(enum.Enum):
    """دسته‌بندی پرامپت‌ها"""
    HEALTH_ANALYSIS = "health_analysis"  # تحلیل سلامت
    ENGINEERING_REPORT = "engineering_report"  # گزارش مهندسی
    AUTO_SETUP = "auto_setup"  # راه‌اندازی خودکار
    DEEP_ANALYSIS = "deep_analysis"  # تحلیل عمیق
    CUSTOM = "custom"  # سفارشی


class PromptType(enum.Enum):
    """نوع پرامپت"""
    SYSTEM = "system"  # سیستمی (دستورات کلی)
    USER = "user"  # کاربری (دستورات خاص)
    CONTEXT = "context"  # زمینه‌ای (اطلاعات پروژه)
    INSTRUCTION = "instruction"  # دستورالعمل (وظایف)


class SystemPrompt(Base):
    """جدول پرامپت‌های سیستم

    این جدول شامل تمام پرامپت‌های قابل ویرایش سیستم است که در:
    - تحلیل سلامت (health_analysis)
    - گزارش مهندسی (engineering_report)
    - راه‌اندازی خودکار (auto_setup)

    استفاده می‌شوند.
    """
    __tablename__ = "system_prompts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # اطلاعات اصلی
    name = Column(String(200), nullable=False, index=True)  # نام نمایشی پرامپت
    description = Column(Text)  # توضیحات

    # دسته‌بندی
    category = Column(String(50), nullable=False, index=True)  # health_analysis, engineering_report, auto_setup
    prompt_type = Column(String(30), default="instruction")  # system, user, context, instruction

    # محتوا
    content = Column(Text, nullable=False)  # محتوای پرامپت
    variables = Column(Text)  # JSON: لیست متغیرهای قابل استفاده {"project_name": "نام پروژه", ...}

    # ترتیب و اولویت اجرا
    execution_order = Column(Integer, default=1)  # ترتیب اجرا در زمان پردازش
    is_required = Column(Boolean, default=True)  # آیا اجباری است؟

    # وضعیت
    is_active = Column(Boolean, default=True, index=True)  # فعال/غیرفعال
    is_default = Column(Boolean, default=False)  # پرامپت پیش‌فرض سیستم؟
    is_locked = Column(Boolean, default=False)  # قفل شده (غیرقابل حذف)

    # وابستگی‌ها
    depends_on = Column(Text)  # JSON: لیست id پرامپت‌های وابسته ["prompt_id_1", "prompt_id_2"]
    parent_id = Column(String(36))  # اگر زیرمجموعه پرامپت دیگری باشد

    # متادیتا
    metadata_json = Column(Text)  # JSON: اطلاعات اضافی {
        # "min_tokens": 500,
        # "max_tokens": 4000,
        # "recommended_models": ["claude", "openai"],
        # "output_format": "json",
        # "tags": ["analysis", "security"]
    # }

    # آمار
    usage_count = Column(Integer, default=0)  # تعداد استفاده
    success_count = Column(Integer, default=0)  # تعداد موفقیت
    last_used_at = Column(DateTime)  # آخرین استفاده
    last_error = Column(Text)  # آخرین خطا

    # زمان‌ها
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """تبدیل به dictionary"""
        variables = {}
        depends_on = []
        metadata = {}

        try:
            if self.variables:
                variables = json.loads(self.variables)
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.depends_on:
                depends_on = json.loads(self.depends_on)
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.metadata_json:
                metadata = json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "prompt_type": self.prompt_type,
            "content": self.content,
            "variables": variables,
            "execution_order": self.execution_order,
            "is_required": self.is_required,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "is_locked": self.is_locked,
            "depends_on": depends_on,
            "parent_id": self.parent_id,
            "metadata": metadata,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_active_prompts(db, category: str, include_defaults: bool = True):
        """دریافت پرامپت‌های فعال یک دسته"""
        query = db.query(SystemPrompt).filter(
            SystemPrompt.category == category,
            SystemPrompt.is_active == True
        )
        if not include_defaults:
            query = query.filter(SystemPrompt.is_default == False)
        return query.order_by(SystemPrompt.execution_order).all()

    @staticmethod
    def get_prompt_by_name(db, category: str, name: str):
        """دریافت پرامپت با نام و دسته"""
        return db.query(SystemPrompt).filter(
            SystemPrompt.category == category,
            SystemPrompt.name == name,
            SystemPrompt.is_active == True
        ).first()

    @staticmethod
    def build_combined_prompt(db, category: str, context: dict = None) -> str:
        """ساخت پرامپت ترکیبی از تمام پرامپت‌های فعال یک دسته"""
        prompts = SystemPrompt.get_active_prompts(db, category)
        if not prompts:
            return ""

        combined = []
        for prompt in prompts:
            content = prompt.content

            # جایگزینی متغیرها با مقادیر context
            if context:
                for key, value in context.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in content:
                        content = content.replace(placeholder, str(value))

            combined.append(f"## {prompt.name}\n{content}")

        return "\n\n".join(combined)

    @staticmethod
    def record_usage(db, prompt_id: str, success: bool = True, error: str = None):
        """ثبت استفاده از پرامپت"""
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()
        if prompt:
            prompt.usage_count = (prompt.usage_count or 0) + 1
            if success:
                prompt.success_count = (prompt.success_count or 0) + 1
            prompt.last_used_at = datetime.utcnow()
            if error:
                prompt.last_error = error
            db.commit()


class PromptExecution(Base):
    """جدول اجرای پرامپت‌ها - برای نمایش وضعیت real-time"""
    __tablename__ = "prompt_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # ارتباط با پرامپت و پروژه
    prompt_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), index=True)

    # وضعیت اجرا
    status = Column(String(30), default="pending", index=True)  # pending, running, completed, failed, cancelled

    # اطلاعات اجرا
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)  # مدت اجرا به ثانیه

    # نتیجه
    result_summary = Column(Text)  # خلاصه نتیجه
    error_message = Column(Text)  # پیام خطا در صورت وجود

    # متادیتا
    model_used = Column(String(50))  # مدل AI استفاده شده
    tokens_used = Column(Integer)

    # زمان‌ها
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "project_id": self.project_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
