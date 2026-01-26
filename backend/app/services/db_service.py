"""
Database Service - سرویس مدیریت پایگاه داده
ترکیب SQLite برای metadata و GitHub برای فایل‌ها
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from ..core.database import get_db_session, SessionLocal
from ..models.project import Project, ProjectFile
from ..models.debate import Debate, DebateMessage
from ..models.setting import Setting
from ..models.ai_log import AILog

logger = logging.getLogger(__name__)


class DatabaseService:
    """سرویس یکپارچه پایگاه داده"""

    # ==================== Project Operations ====================

    def create_project(
        self,
        db: Session,
        name: str,
        description: str = "",
        project_type: str = "web",
        technologies: List[str] = None,
        features: List[str] = None,
        structure: dict = None,
        metadata: dict = None,
    ) -> Project:
        """ایجاد پروژه جدید"""
        project = Project(
            name=name,
            description=description,
            project_type=project_type,
            technologies=json.dumps(technologies or [], ensure_ascii=False),
            features=json.dumps(features or [], ensure_ascii=False),
            structure=json.dumps(structure or {}, ensure_ascii=False),
            metadata=json.dumps(metadata or {}, ensure_ascii=False),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created project: {project.id} - {name}")
        return project

    def get_project(self, db: Session, project_id: str) -> Optional[Project]:
        """دریافت پروژه با ID"""
        return db.query(Project).filter(Project.id == project_id).first()

    def get_project_by_name(self, db: Session, name: str) -> Optional[Project]:
        """دریافت پروژه با نام"""
        return db.query(Project).filter(Project.name == name).first()

    def list_projects(
        self,
        db: Session,
        status: str = None,
        project_type: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Project]:
        """لیست پروژه‌ها"""
        query = db.query(Project)

        if status:
            query = query.filter(Project.status == status)
        if project_type:
            query = query.filter(Project.project_type == project_type)

        return query.order_by(desc(Project.created_at)).offset(offset).limit(limit).all()

    def update_project(
        self,
        db: Session,
        project_id: str,
        **kwargs
    ) -> Optional[Project]:
        """بروزرسانی پروژه"""
        project = self.get_project(db, project_id)
        if not project:
            return None

        # فیلدهای JSON باید serialize شوند
        json_fields = ['technologies', 'features', 'structure', 'metadata']
        for key, value in kwargs.items():
            if hasattr(project, key):
                if key in json_fields and not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                setattr(project, key, value)

        db.commit()
        db.refresh(project)
        return project

    def delete_project(self, db: Session, project_id: str) -> bool:
        """حذف پروژه"""
        project = self.get_project(db, project_id)
        if not project:
            return False

        # حذف فایل‌های مرتبط
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).delete()
        db.delete(project)
        db.commit()
        logger.info(f"Deleted project: {project_id}")
        return True

    def search_projects(self, db: Session, query: str) -> List[Project]:
        """جستجو در پروژه‌ها"""
        search_term = f"%{query}%"
        return db.query(Project).filter(
            or_(
                Project.name.ilike(search_term),
                Project.description.ilike(search_term),
            )
        ).order_by(desc(Project.created_at)).all()

    # ==================== Project File Operations ====================

    def add_project_file(
        self,
        db: Session,
        project_id: str,
        file_path: str,
        content: str = None,
        file_type: str = None,
        size: int = None,
        github_url: str = None,
    ) -> Optional[ProjectFile]:
        """افزودن فایل به پروژه"""
        project = self.get_project(db, project_id)
        if not project:
            return None

        # چک کن فایل قبلاً وجود نداشته باشه
        existing = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_path == file_path
        ).first()

        if existing:
            # بروزرسانی فایل موجود
            existing.content = content
            existing.file_type = file_type or existing.file_type
            existing.size = size or len(content) if content else existing.size
            existing.github_url = github_url or existing.github_url
            db.commit()
            return existing

        # ایجاد فایل جدید
        project_file = ProjectFile(
            project_id=project_id,
            file_path=file_path,
            content=content,
            file_type=file_type or self._detect_file_type(file_path),
            size=size or (len(content) if content else 0),
            github_url=github_url,
        )
        db.add(project_file)
        db.commit()
        return project_file

    def get_project_files(self, db: Session, project_id: str) -> List[ProjectFile]:
        """دریافت فایل‌های پروژه"""
        return db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id
        ).order_by(ProjectFile.file_path).all()

    def get_project_file(
        self, db: Session, project_id: str, file_path: str
    ) -> Optional[ProjectFile]:
        """دریافت یک فایل خاص"""
        return db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_path == file_path
        ).first()

    def delete_project_file(
        self, db: Session, project_id: str, file_path: str
    ) -> bool:
        """حذف فایل از پروژه"""
        file = self.get_project_file(db, project_id, file_path)
        if not file:
            return False
        db.delete(file)
        db.commit()
        return True

    def _detect_file_type(self, file_path: str) -> str:
        """تشخیص نوع فایل از پسوند"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.sql': 'sql',
            '.sh': 'shell',
            '.env': 'env',
            '.txt': 'text',
        }
        for ext, ftype in ext_map.items():
            if file_path.endswith(ext):
                return ftype
        return 'text'

    # ==================== Debate Operations ====================

    def create_debate(
        self,
        db: Session,
        title: str,
        topic: str,
        models: List[str],
        work_mode: str = "sequential",
        total_rounds: int = 3,
        metadata: dict = None,
    ) -> Debate:
        """ایجاد debate جدید"""
        debate = Debate(
            title=title,
            topic=topic,
            models=json.dumps(models, ensure_ascii=False),
            work_mode=work_mode,
            total_rounds=total_rounds,
            metadata=json.dumps(metadata or {}, ensure_ascii=False),
        )
        db.add(debate)
        db.commit()
        db.refresh(debate)
        logger.info(f"Created debate: {debate.id} - {title}")
        return debate

    def get_debate(self, db: Session, debate_id: str) -> Optional[Debate]:
        """دریافت debate"""
        return db.query(Debate).filter(Debate.id == debate_id).first()

    def list_debates(
        self, db: Session, status: str = None, limit: int = 50
    ) -> List[Debate]:
        """لیست debates"""
        query = db.query(Debate)
        if status:
            query = query.filter(Debate.status == status)
        return query.order_by(desc(Debate.created_at)).limit(limit).all()

    def update_debate(
        self, db: Session, debate_id: str, **kwargs
    ) -> Optional[Debate]:
        """بروزرسانی debate"""
        debate = self.get_debate(db, debate_id)
        if not debate:
            return None

        json_fields = ['models', 'metadata']
        for key, value in kwargs.items():
            if hasattr(debate, key):
                if key in json_fields and not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                setattr(debate, key, value)

        db.commit()
        db.refresh(debate)
        return debate

    def add_debate_message(
        self,
        db: Session,
        debate_id: str,
        role: str,
        content: str,
        model: str = None,
        round_number: int = 1,
        tokens_used: int = 0,
    ) -> Optional[DebateMessage]:
        """افزودن پیام به debate"""
        debate = self.get_debate(db, debate_id)
        if not debate:
            return None

        message = DebateMessage(
            debate_id=debate_id,
            role=role,
            content=content,
            model=model,
            round_number=round_number,
            tokens_used=tokens_used,
        )
        db.add(message)
        db.commit()
        return message

    def get_debate_messages(
        self, db: Session, debate_id: str
    ) -> List[DebateMessage]:
        """دریافت پیام‌های debate"""
        return db.query(DebateMessage).filter(
            DebateMessage.debate_id == debate_id
        ).order_by(DebateMessage.created_at).all()

    # ==================== Settings Operations ====================

    def get_setting(self, db: Session, key: str, default=None):
        """دریافت تنظیم"""
        return Setting.get_value(db, key, default)

    def set_setting(
        self,
        db: Session,
        key: str,
        value,
        value_type: str = "string",
        category: str = "general",
        description: str = None,
        is_secret: bool = False,
    ) -> Setting:
        """تنظیم مقدار"""
        return Setting.set_value(
            db, key, value, value_type, category, description, is_secret
        )

    def get_settings_by_category(self, db: Session, category: str) -> List[Setting]:
        """دریافت تنظیمات یک دسته"""
        return db.query(Setting).filter(Setting.category == category).all()

    def get_all_settings(self, db: Session) -> Dict[str, Any]:
        """دریافت همه تنظیمات به صورت dictionary"""
        settings = db.query(Setting).all()
        result = {}
        for s in settings:
            result[s.key] = Setting.get_value(db, s.key)
        return result

    # ==================== AI Log Operations ====================

    def log_ai_request(
        self,
        db: Session,
        provider: str,
        model: str,
        request_type: str,
        prompt: str,
        response: str = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        latency_ms: int = 0,
        project_id: str = None,
        debate_id: str = None,
        status: str = "success",
        error_message: str = None,
    ) -> AILog:
        """ثبت لاگ درخواست AI"""
        return AILog.log_request(
            db, provider, model, request_type, prompt, response,
            input_tokens, output_tokens, cost, latency_ms,
            project_id, debate_id, status, error_message
        )

    def get_ai_stats(self, db: Session, days: int = 30) -> List[Dict]:
        """آمار مصرف AI"""
        return AILog.get_stats(db, days)

    def get_recent_ai_logs(
        self, db: Session, limit: int = 100, provider: str = None
    ) -> List[AILog]:
        """لاگ‌های اخیر AI"""
        query = db.query(AILog)
        if provider:
            query = query.filter(AILog.provider == provider)
        return query.order_by(desc(AILog.created_at)).limit(limit).all()


# Singleton instance
_db_service = None


def get_db_service() -> DatabaseService:
    """دریافت instance سرویس"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
