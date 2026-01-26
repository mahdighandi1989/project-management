"""
Project Model - مدل پروژه
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..core.database import Base


class ProjectStatus(enum.Enum):
    """وضعیت پروژه"""
    CREATED = "created"
    GENERATING = "generating"
    COMPLETED = "completed"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ARCHIVED = "archived"


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


class Project(Base):
    """جدول پروژه‌ها"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    project_type = Column(String(50), default="custom")
    status = Column(String(50), default="created", index=True)

    # تنظیمات
    technologies = Column(JSON, default=list)  # ["python", "fastapi", ...]
    features = Column(JSON, default=list)  # ["authentication", ...]
    structure = Column(JSON, default=dict)  # ساختار پوشه‌ها

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
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "status": self.status,
            "technologies": self.technologies or [],
            "features": self.features or [],
            "structure": self.structure or {},
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
            "files": [f.to_dict() for f in self.files] if self.files else []
        }


class ProjectFile(Base):
    """جدول فایل‌های پروژه"""
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False)  # مسیر نسبی فایل
    language = Column(String(50))  # زبان برنامه‌نویسی
    size = Column(Integer, default=0)  # سایز به بایت
    checksum = Column(String(64))  # SHA256 hash

    # محل ذخیره
    storage_type = Column(String(20), default="local")  # local, github
    storage_path = Column(String(500))  # مسیر واقعی در storage

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
            "path": self.path,
            "language": self.language,
            "size": self.size,
            "checksum": self.checksum,
            "storage_type": self.storage_type,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
