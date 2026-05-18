# -*- coding: utf-8 -*-
"""
مدل دیتابیس برای فیلدهای دستورات، حافظه و آموزش مدل‌ها در بازرس ویژه
هر فیلد یک واحد مستقل از دستور، حافظه یا آموزش است که توسط کاربر مدیریت می‌شود
"""

import json
import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Float
from sqlalchemy.sql import func
from ..core.database import Base


class InspectorPromptField(Base):
    """فیلدهای دستورات و حافظه و آموزش بازرس ویژه"""
    __tablename__ = "inspector_prompt_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(100), nullable=False, index=True)

    # نوع فیلد: instruction (دستور), memory (حافظه), training (آموزش)
    category = Column(String(50), nullable=False, index=True)

    # عنوان و محتوا
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)

    # اولویت (عدد بزرگتر = اولویت بالاتر)
    priority = Column(Integer, default=0, index=True)

    # فعال/غیرفعال
    is_active = Column(Boolean, default=True)

    # آمار استفاده واقعی
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # آخرین تست زنده
    last_tested_at = Column(DateTime, nullable=True)
    last_test_passed = Column(Boolean, nullable=True)
    last_test_result = Column(Text, nullable=True)  # JSON result

    # 🆕 (C7v2) فیلدهای جدید برای archive، auto-sync و چرخهٔ تقویت/آرشیو
    archived = Column(Boolean, default=False, index=True)
    source = Column(String(50), nullable=True)  # "manual" | "oversight_auto_sync" | "migrate"
    auto_synced = Column(Boolean, default=False, index=True)
    evidence_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime, nullable=True)
    previous_content = Column(Text, nullable=True)  # نسخهٔ قبلی content پس از تقویت

    # زمان‌ها
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "last_test_passed": self.last_test_passed,
            "last_test_result": json.loads(self.last_test_result) if self.last_test_result else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # 🆕 (C7v2)
            "archived": bool(self.archived) if self.archived is not None else False,
            "source": self.source or "manual",
            "auto_synced": bool(self.auto_synced) if self.auto_synced is not None else False,
            "evidence_count": int(self.evidence_count or 0),
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "previous_content": self.previous_content,
        }
