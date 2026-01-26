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
    metadata = Column(Text)  # JSON string: اطلاعات اضافی (GitHub info, etc.)

    # مسیرها
    local_path = Column(String(500))  # مسیر محلی فایل‌ها
    github_path = Column(String(500))  # مسیر در GitHub
    deploy_url = Column(String(500))  # آدرس deploy شده

    # متادیتا
    file_count = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # بایت
    ai_model_used = Column(String(100))
    tokens_used = Column(Integer, default=0)

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
            if self.metadata:
                metadata = json.loads(self.metadata) if isinstance(self.metadata, str) else self.metadata
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
            "local_path": self.local_path,
            "github_path": self.github_path,
            "deploy_url": self.deploy_url,
            "file_count": self.file_count,
            "total_size": self.total_size,
            "ai_model_used": self.ai_model_used,
            "tokens_used": self.tokens_used,
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
