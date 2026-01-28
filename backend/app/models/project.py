"""
Project Model - مدل پروژه
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import json

from ..core.database import Base


class ProjectStatus(enum.Enum):
    """وضعیت پروژه"""
    CREATED = "created"
    GENERATING = "generating"
    COMPLETED = "completed"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ARCHIVED = "archived"
    IMPORTED = "imported"


class ProjectType(enum.Enum):
    """نوع پروژه"""
    WEB_APP = "web_app"
    API = "api"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    SCRIPT = "script"
    LIBRARY = "library"
    TRADING = "trading"
    CUSTOM = "custom"
    GITHUB_IMPORT = "github_import"


class Project(Base):
    """جدول پروژه‌ها"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    project_type = Column(String(50), default="custom")
    status = Column(String(50), default="created", index=True)

    # تنظیمات
    technologies = Column(Text)  # JSON string: ["python", "fastapi", ...]
    features = Column(Text)  # JSON string: ["authentication", ...]
    structure = Column(Text)  # JSON string: ساختار پوشه‌ها
    extra_data = Column(Text)  # JSON string: اطلاعات اضافی (GitHub info, etc.)

    # باکس حافظه و دستورات برای AI
    memory_instructions = Column(Text)  # JSON: {"content": "...", "target_models": ["all"]}
    dynamic_fields = Column(Text)  # JSON: [{"id": "...", "name": "...", "value": "...", "target_models": [...]}]

    # مسیرها
    local_path = Column(String(500))  # مسیر محلی فایل‌ها
    github_path = Column(String(500))  # مسیر در GitHub
    deploy_url = Column(String(500))  # آدرس deploy شده

    # متادیتا
    file_count = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # بایت
    ai_model_used = Column(String(100))
    tokens_used = Column(Integer, default=0)

    # ====================================
    # 🆕 تنظیمات و نتایج تحلیل سلامت پروژه
    # ====================================

    # تنظیمات تحلیل (prompts قوی قابل ویرایش، مدل‌های منتخب، زمان‌بندی)
    analysis_settings = Column(Text)  # JSON: {"instruction": "...", "target_models": [...], "trigger_interval": 60, ...}

    # نمرات سلامت (هر بار از صفر محاسبه می‌شود)
    health_scores = Column(Text)  # JSON: {"overall": 85, "code_quality": 90, ...}

    # رنگ‌بندی فایل‌ها برای دیاگرام
    file_health_map = Column(Text)  # JSON: {"file_path": {"score": 85, "color": "#22c55e", "models": [...], "date": "..."}}

    # آخرین تحلیل
    last_analysis_id = Column(String(50))  # شناسه آخرین تحلیل
    last_analysis_at = Column(DateTime)  # زمان آخرین تحلیل
    last_analysis_models = Column(Text)  # JSON: لیست مدل‌های استفاده شده

    # ====================================
    # 🆕 وضعیت تحلیل در حال اجرا (برای pause/resume)
    # ====================================
    analysis_progress = Column(Text)  # JSON: {
    #   "status": "running|paused|completed|failed",
    #   "analysis_id": "...",
    #   "phase": "micro|macro|structural",
    #   "total_files": 50,
    #   "analyzed_files": 25,
    #   "completed_files": ["file1.py", "file2.py", ...],
    #   "current_file": "file3.py",
    #   "current_model": "gpt-4",
    #   "model_statuses": {"gpt-4": "working", ...},
    #   "started_at": "...",
    #   "last_update": "...",
    #   "elapsed_time": 120.5,
    #   "issues_found": 15,
    #   "partial_results": {...},  # نتایج تا این لحظه
    #   "error": null
    # }

    # محتوای Roadmap و README (ایجاد/به‌روزرسانی شده توسط AI)
    roadmap_content = Column(Text)  # محتوای فایل ROADMAP.md
    readme_content = Column(Text)  # محتوای فایل README.md
    ideal_state = Column(Text)  # توضیح حالت ایده‌آل پروژه
    issues_found = Column(Text)  # JSON: لیست ایرادات شناسایی شده

    # زمان‌ها
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    deployed_at = Column(DateTime)

    # روابط
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self):
        """تبدیل به dictionary"""
        # پارس JSON fields
        technologies = []
        features = []
        structure = {}
        metadata = {}
        memory_instructions = {"content": "", "target_models": ["all"]}
        dynamic_fields = []

        try:
            if self.technologies:
                technologies = json.loads(self.technologies) if isinstance(self.technologies, str) else self.technologies
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.features:
                features = json.loads(self.features) if isinstance(self.features, str) else self.features
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.structure:
                structure = json.loads(self.structure) if isinstance(self.structure, str) else self.structure
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.extra_data:
                metadata = json.loads(self.extra_data) if isinstance(self.extra_data, str) else self.extra_data
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.memory_instructions:
                memory_instructions = json.loads(self.memory_instructions) if isinstance(self.memory_instructions, str) else self.memory_instructions
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.dynamic_fields:
                dynamic_fields = json.loads(self.dynamic_fields) if isinstance(self.dynamic_fields, str) else self.dynamic_fields
        except (json.JSONDecodeError, TypeError):
            pass

        # Parse new analysis fields
        analysis_settings = {}
        health_scores = {}
        file_health_map = {}
        issues_found = []
        last_analysis_models = []

        try:
            if self.analysis_settings:
                analysis_settings = json.loads(self.analysis_settings) if isinstance(self.analysis_settings, str) else self.analysis_settings
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.health_scores:
                health_scores = json.loads(self.health_scores) if isinstance(self.health_scores, str) else self.health_scores
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.file_health_map:
                file_health_map = json.loads(self.file_health_map) if isinstance(self.file_health_map, str) else self.file_health_map
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.issues_found:
                issues_found = json.loads(self.issues_found) if isinstance(self.issues_found, str) else self.issues_found
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if self.last_analysis_models:
                last_analysis_models = json.loads(self.last_analysis_models) if isinstance(self.last_analysis_models, str) else self.last_analysis_models
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "status": self.status,
            "technologies": technologies,
            "features": features,
            "structure": structure,
            "metadata": metadata,
            "memory_instructions": memory_instructions,
            "dynamic_fields": dynamic_fields,
            "local_path": self.local_path,
            "github_path": self.github_path,
            "deploy_url": self.deploy_url,
            "file_count": self.file_count,
            "total_size": self.total_size,
            "ai_model_used": self.ai_model_used,
            "tokens_used": self.tokens_used,
            # 🆕 Analysis fields
            "analysis_settings": analysis_settings,
            "health_scores": health_scores,
            "file_health_map": file_health_map,
            "last_analysis_id": self.last_analysis_id,
            "last_analysis_at": self.last_analysis_at.isoformat() if self.last_analysis_at else None,
            "last_analysis_models": last_analysis_models,
            "roadmap_content": self.roadmap_content,
            "readme_content": self.readme_content,
            "ideal_state": self.ideal_state,
            "issues_found": issues_found,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
        }


class ProjectFile(Base):
    """جدول فایل‌های پروژه"""
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # اطلاعات فایل
    file_path = Column(String(500), nullable=False)  # مسیر نسبی فایل
    content = Column(Text)  # محتوای فایل
    file_type = Column(String(50))  # نوع فایل (python, javascript, etc.)
    size = Column(Integer, default=0)  # سایز به بایت
    checksum = Column(String(64))  # SHA256 hash

    # محل ذخیره
    storage_type = Column(String(20), default="local")  # local, github
    storage_path = Column(String(500))  # مسیر واقعی در storage
    github_url = Column(String(500))  # لینک مستقیم به GitHub

    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # روابط
    project = relationship("Project", back_populates="files")

    def to_dict(self):
        """تبدیل به dictionary"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "content": self.content[:500] + "..." if self.content and len(self.content) > 500 else self.content,
            "file_type": self.file_type,
            "size": self.size,
            "checksum": self.checksum,
            "storage_type": self.storage_type,
            "storage_path": self.storage_path,
            "github_url": self.github_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
