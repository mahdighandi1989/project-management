"""
سیستم مدیریت پروژه پایدار
Persistent Project Management System
با پشتیبانی از SQLite + GitHub ترکیبی
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

# =====================================
# مدل‌های داده
# =====================================

class PhaseStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    ROLLBACK = "rollback"

class ProjectType(str, Enum):
    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    API_SERVICE = "api_service"
    DATA_PIPELINE = "data_pipeline"
    ML_PROJECT = "ml_project"
    CUSTOM = "custom"

class Phase(BaseModel):
    id: str
    name: str
    description: str = ""
    status: PhaseStatus = PhaseStatus.PENDING
    progress: int = 0
    steps: List[str] = []
    completed_steps: List[str] = []
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: str = ""

class ProjectContext(BaseModel):
    project_id: str
    name: str
    description: str = ""
    project_type: ProjectType = ProjectType.CUSTOM
    goal: str = ""
    complexity: str = "medium"
    created_at: str
    updated_at: str
    phases: List[Phase] = []
    current_phase_index: int = 0
    conversations: List[Dict] = []
    files: List[Dict] = []
    model_scores: Dict[str, Dict] = {}
    knowledge_base: List[Dict] = []
    status: str = "active"

# =====================================
# قالب‌های فاز بر اساس نوع پروژه
# =====================================

PHASE_TEMPLATES = {
    ProjectType.WEB_APP: [
        Phase(id="p1", name="تحلیل و طراحی", description="تحلیل نیازمندی‌ها و طراحی معماری",
              steps=["جمع‌آوری نیازمندی‌ها", "طراحی wireframe", "طراحی معماری", "انتخاب تکنولوژی"]),
        Phase(id="p2", name="توسعه Backend", description="پیاده‌سازی سرور و API",
              steps=["راه‌اندازی پروژه", "طراحی دیتابیس", "پیاده‌سازی API", "تست واحد"]),
        Phase(id="p3", name="توسعه Frontend", description="پیاده‌سازی رابط کاربری",
              steps=["راه‌اندازی پروژه", "کامپوننت‌ها", "اتصال به API", "استایل و تم"]),
        Phase(id="p4", name="تست و QA", description="تست کامل سیستم",
              steps=["تست یکپارچگی", "تست E2E", "تست کارایی", "رفع باگ"]),
        Phase(id="p5", name="استقرار", description="استقرار در محیط تولید",
              steps=["آماده‌سازی سرور", "CI/CD", "استقرار", "مانیتورینگ"]),
    ],
    ProjectType.API_SERVICE: [
        Phase(id="p1", name="طراحی API", description="طراحی endpoints و مستندات",
              steps=["OpenAPI spec", "طراحی endpoints", "مدل‌های داده", "احراز هویت"]),
        Phase(id="p2", name="پیاده‌سازی", description="کدنویسی API",
              steps=["ساختار پروژه", "routes", "controllers", "middleware"]),
        Phase(id="p3", name="دیتابیس", description="طراحی و پیاده‌سازی دیتابیس",
              steps=["طراحی schema", "migrations", "seeding", "بهینه‌سازی"]),
        Phase(id="p4", name="تست", description="تست API",
              steps=["unit tests", "integration tests", "load tests", "security tests"]),
        Phase(id="p5", name="مستندات و استقرار", description="مستندسازی و deploy",
              steps=["API docs", "Docker", "CI/CD", "monitoring"]),
    ],
    ProjectType.ML_PROJECT: [
        Phase(id="p1", name="جمع‌آوری داده", description="جمع‌آوری و آماده‌سازی داده",
              steps=["شناسایی منابع", "جمع‌آوری", "پاکسازی", "برچسب‌گذاری"]),
        Phase(id="p2", name="تحلیل اکتشافی", description="EDA و feature engineering",
              steps=["آمار توصیفی", "تصویرسازی", "feature engineering", "انتخاب ویژگی"]),
        Phase(id="p3", name="مدل‌سازی", description="آموزش و ارزیابی مدل",
              steps=["انتخاب مدل", "آموزش", "hyperparameter tuning", "ارزیابی"]),
        Phase(id="p4", name="بهینه‌سازی", description="بهینه‌سازی و تست",
              steps=["بهینه‌سازی", "cross-validation", "تست نهایی", "مستندات"]),
        Phase(id="p5", name="استقرار", description="استقرار مدل",
              steps=["API wrapper", "containerization", "deploy", "monitoring"]),
    ],
    ProjectType.CUSTOM: [
        Phase(id="p1", name="تحلیل", description="تحلیل اولیه", steps=["بررسی نیازها", "تحقیق"]),
        Phase(id="p2", name="طراحی", description="طراحی راه‌حل", steps=["طراحی معماری", "برنامه‌ریزی"]),
        Phase(id="p3", name="پیاده‌سازی", description="اجرا", steps=["کدنویسی", "تست"]),
        Phase(id="p4", name="تکمیل", description="نهایی‌سازی", steps=["مستندات", "تحویل"]),
    ],
}

# =====================================
# سرویس مدیریت پروژه
# =====================================

class ProjectService:
    def __init__(self, storage_path: str = "./data/projects"):
        self.storage_path = storage_path
        self.projects: Dict[str, ProjectContext] = {}
        self.github_storage = None
        self._db_service = None
        self._use_sqlite = True  # فعال‌سازی SQLite
        self._ensure_storage()
        self._load_projects()
        # بارگذاری از GitHub به صورت async در startup انجام میشه

    def _get_db_service(self):
        """دریافت سرویس پایگاه داده"""
        if self._db_service is None:
            try:
                from .db_service import get_db_service
                self._db_service = get_db_service()
            except ImportError:
                logger.warning("Database service not available")
                self._use_sqlite = False
        return self._db_service

    def _get_db_session(self):
        """دریافت session پایگاه داده"""
        try:
            from ..core.database import SessionLocal
            return SessionLocal()
        except ImportError:
            return None

    def initialize_github(self, github_storage):
        """Initialize با GitHub storage"""
        self.github_storage = github_storage
        # بارگذاری پروژه‌ها از GitHub
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._load_from_github())
            else:
                loop.run_until_complete(self._load_from_github())
        except Exception as e:
            logger.error(f"Could not load from GitHub: {e}")

    def _ensure_storage(self):
        """ایجاد پوشه ذخیره‌سازی"""
        os.makedirs(self.storage_path, exist_ok=True)

    def _load_projects(self):
        """بارگذاری پروژه‌ها از دیسک"""
        try:
            registry_path = os.path.join(self.storage_path, "registry.json")
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                    for project_id in registry:
                        self._load_project(project_id)
        except Exception as e:
            print(f"Error loading projects: {e}")

    async def _load_from_github(self):
        """بارگذاری پروژه‌ها از GitHub"""
        if not self.github_storage:
            return

        try:
            # لیست پوشه projects
            files = await self.github_storage.list_folder("projects")
            for folder in files:
                if folder.type == "dir":
                    project_id = folder.name
                    if project_id not in self.projects:
                        # دریافت metadata.json
                        await self._load_project_from_github(project_id)
        except Exception as e:
            print(f"Error loading from GitHub: {e}")

    async def _load_project_from_github(self, project_id: str):
        """بارگذاری یک پروژه از GitHub"""
        if not self.github_storage:
            return

        try:
            # دریافت فایل metadata
            result = await self.github_storage.get_file(f"projects/{project_id}/metadata.json")
            if result.get("success") and result.get("content"):
                import base64
                content = base64.b64decode(result["content"]).decode('utf-8')
                data = json.loads(content)
                project = ProjectContext(**data)
                self.projects[project_id] = project
                # ذخیره لوکال هم
                self._save_project_local(project)
                print(f"Loaded project {project_id} from GitHub")
        except Exception as e:
            print(f"Error loading project {project_id} from GitHub: {e}")

    def _load_project(self, project_id: str) -> Optional[ProjectContext]:
        """بارگذاری یک پروژه"""
        try:
            path = os.path.join(self.storage_path, f"{project_id}.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    project = ProjectContext(**data)
                    self.projects[project_id] = project
                    return project
        except Exception as e:
            print(f"Error loading project {project_id}: {e}")
        return None

    def _save_project(self, project: ProjectContext):
        """ذخیره پروژه در دیسک، SQLite و GitHub"""
        # ذخیره لوکال
        self._save_project_local(project)

        # 🆕 ذخیره در SQLite
        self._save_to_sqlite(project)

        # ذخیره در GitHub (async)
        if self.github_storage:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._save_project_to_github(project))
                else:
                    loop.run_until_complete(self._save_project_to_github(project))
            except Exception as e:
                logger.error(f"Could not save to GitHub: {e}")

    def _save_project_local(self, project: ProjectContext):
        """ذخیره پروژه فقط در دیسک لوکال"""
        try:
            path = os.path.join(self.storage_path, f"{project.project_id}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(project.dict(), f, ensure_ascii=False, indent=2)
            self._update_registry()
        except Exception as e:
            print(f"Error saving project locally: {e}")

    async def _save_project_to_github(self, project: ProjectContext):
        """ذخیره پروژه در GitHub"""
        if not self.github_storage:
            return

        try:
            # ذخیره metadata.json در هر دو محل (برای سازگاری)
            content = json.dumps(project.dict(), ensure_ascii=False, indent=2)

            # ذخیره در source/metadata.json
            await self.github_storage.save_project_file(
                project.project_id,
                content.encode('utf-8'),
                "metadata.json",
                "source"
            )

            # ذخیره در root هم برای دسترسی راحت‌تر
            await self.github_storage.upload_file(
                content.encode('utf-8'),
                f"projects/{project.project_id}/metadata.json",
                f"Update project metadata for {project.project_id}"
            )

            print(f"Project {project.project_id} saved to GitHub")
        except Exception as e:
            print(f"Error saving project {project.project_id} to GitHub: {e}")

    def _update_registry(self):
        """بروزرسانی فهرست پروژه‌ها"""
        registry_path = os.path.join(self.storage_path, "registry.json")
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(list(self.projects.keys()), f)

    # =====================================
    # API های اصلی
    # =====================================

    def create_project(
        self,
        name: str,
        description: str = "",
        project_type: ProjectType = ProjectType.CUSTOM,
        goal: str = "",
        complexity: str = "medium",
        custom_phases: Optional[List[Dict]] = None
    ) -> Dict:
        """ایجاد پروژه جدید"""
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        # انتخاب فازها
        if custom_phases:
            # اضافه کردن id اتوماتیک اگر وجود نداره
            phases = []
            for i, p in enumerate(custom_phases):
                if 'id' not in p:
                    p['id'] = f"phase_{i+1}_{uuid.uuid4().hex[:8]}"
                phases.append(Phase(**p))
        else:
            template = PHASE_TEMPLATES.get(project_type, PHASE_TEMPLATES[ProjectType.CUSTOM])
            phases = [Phase(**p.dict()) for p in template]

        project = ProjectContext(
            project_id=project_id,
            name=name,
            description=description,
            project_type=project_type,
            goal=goal,
            complexity=complexity,
            created_at=now,
            updated_at=now,
            phases=phases
        )

        self.projects[project_id] = project
        self._save_project(project)  # این متد خودش به SQLite هم ذخیره می‌کند

        return {
            "success": True,
            "project_id": project_id,
            "name": name,
            "phases_count": len(phases),
            "created_at": now
        }

    def _save_to_sqlite(self, project: ProjectContext):
        """ذخیره پروژه در SQLite"""
        if not self._use_sqlite:
            return

        try:
            db_service = self._get_db_service()
            db = self._get_db_session()
            if not db_service or not db:
                return

            try:
                # تبدیل ProjectContext به فرمت مناسب SQLite
                from ..models.project import Project as DBProject

                # چک کن آیا وجود دارد
                existing = db.query(DBProject).filter(DBProject.id == project.project_id).first()

                # آماده‌سازی داده‌ها
                technologies = []
                features = []
                structure = {"phases": [p.dict() for p in project.phases]}
                metadata = {
                    "goal": project.goal,
                    "complexity": project.complexity,
                    "model_scores": project.model_scores,
                    "conversations_count": len(project.conversations),
                    "knowledge_entries": len(project.knowledge_base),
                }

                if existing:
                    # بروزرسانی
                    existing.name = project.name
                    existing.description = project.description
                    existing.project_type = project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type)
                    existing.status = project.status
                    existing.technologies = json.dumps(technologies, ensure_ascii=False)
                    existing.features = json.dumps(features, ensure_ascii=False)
                    existing.structure = json.dumps(structure, ensure_ascii=False)
                    existing.metadata = json.dumps(metadata, ensure_ascii=False)
                else:
                    # ایجاد جدید
                    db_project = DBProject(
                        id=project.project_id,
                        name=project.name,
                        description=project.description,
                        project_type=project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
                        status=project.status,
                        technologies=json.dumps(technologies, ensure_ascii=False),
                        features=json.dumps(features, ensure_ascii=False),
                        structure=json.dumps(structure, ensure_ascii=False),
                        metadata=json.dumps(metadata, ensure_ascii=False),
                    )
                    db.add(db_project)

                db.commit()
                logger.debug(f"Project {project.project_id} saved to SQLite")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error saving project to SQLite: {e}")

    def get_project(self, project_id: str) -> Optional[Dict]:
        """دریافت اطلاعات پروژه"""
        project = self.projects.get(project_id)
        if not project:
            project = self._load_project(project_id)

        if project:
            return {
                "success": True,
                "project": project.dict(),
                "current_phase": project.phases[project.current_phase_index].dict() if project.phases else None,
                "progress": self._calculate_progress(project)
            }
        return {"success": False, "error": "پروژه یافت نشد"}

    def list_projects(self) -> Dict:
        """لیست همه پروژه‌ها"""
        projects = []
        for project in self.projects.values():
            projects.append({
                "project_id": project.project_id,
                "name": project.name,
                "type": project.project_type,
                "status": project.status,
                "progress": self._calculate_progress(project),
                "created_at": project.created_at,
                "updated_at": project.updated_at
            })
        return {"success": True, "projects": projects, "count": len(projects)}

    def start_next_phase(self, project_id: str) -> Dict:
        """شروع فاز بعدی"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        # تکمیل فاز فعلی
        if project.current_phase_index < len(project.phases):
            current = project.phases[project.current_phase_index]
            current.status = PhaseStatus.COMPLETED
            current.completed_at = datetime.now().isoformat()
            current.progress = 100

        # شروع فاز بعدی
        if project.current_phase_index + 1 < len(project.phases):
            project.current_phase_index += 1
            next_phase = project.phases[project.current_phase_index]
            next_phase.status = PhaseStatus.IN_PROGRESS
            next_phase.started_at = datetime.now().isoformat()

            project.updated_at = datetime.now().isoformat()
            self._save_project(project)

            return {
                "success": True,
                "message": f"فاز '{next_phase.name}' شروع شد",
                "phase": next_phase.dict()
            }
        else:
            project.status = "completed"
            self._save_project(project)
            return {"success": True, "message": "پروژه تکمیل شد!", "completed": True}

    def update_phase_progress(
        self,
        project_id: str,
        progress: int,
        step_completed: Optional[str] = None
    ) -> Dict:
        """بروزرسانی پیشرفت فاز"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        current = project.phases[project.current_phase_index]
        current.progress = min(100, max(0, progress))

        if step_completed and step_completed not in current.completed_steps:
            current.completed_steps.append(step_completed)

        project.updated_at = datetime.now().isoformat()
        self._save_project(project)

        return {"success": True, "progress": current.progress, "completed_steps": current.completed_steps}

    def add_conversation(
        self,
        project_id: str,
        user_message: str,
        ai_responses: List[Dict]
    ) -> Dict:
        """افزودن مکالمه به پروژه"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        conversation = {
            "id": f"conv_{len(project.conversations) + 1}",
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "responses": ai_responses,
            "phase_id": project.phases[project.current_phase_index].id if project.phases else None
        }

        project.conversations.append(conversation)

        # بروزرسانی امتیاز مدل‌ها
        for response in ai_responses:
            model_id = response.get("model")
            score = response.get("score", 75)
            if model_id:
                if model_id not in project.model_scores:
                    project.model_scores[model_id] = {"total": 0, "count": 0, "average": 0}
                project.model_scores[model_id]["total"] += score
                project.model_scores[model_id]["count"] += 1
                project.model_scores[model_id]["average"] = round(
                    project.model_scores[model_id]["total"] / project.model_scores[model_id]["count"]
                )

        project.updated_at = datetime.now().isoformat()
        self._save_project(project)

        return {"success": True, "conversation_id": conversation["id"]}

    def add_to_knowledge_base(
        self,
        project_id: str,
        knowledge_type: str,
        content: str,
        tags: List[str] = []
    ) -> Dict:
        """افزودن به پایگاه دانش"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        entry = {
            "id": f"kb_{len(project.knowledge_base) + 1}",
            "type": knowledge_type,  # pattern, anti_pattern, lesson, reference
            "content": content,
            "tags": tags,
            "added_at": datetime.now().isoformat()
        }

        project.knowledge_base.append(entry)
        self._save_project(project)

        return {"success": True, "entry_id": entry["id"]}

    def get_project_summary(self, project_id: str) -> Dict:
        """خلاصه پروژه"""
        project = self.projects.get(project_id)
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        completed_phases = sum(1 for p in project.phases if p.status == PhaseStatus.COMPLETED)

        return {
            "success": True,
            "summary": {
                "name": project.name,
                "type": project.project_type,
                "status": project.status,
                "progress": self._calculate_progress(project),
                "phases": {
                    "total": len(project.phases),
                    "completed": completed_phases,
                    "current": project.phases[project.current_phase_index].name if project.phases else None
                },
                "conversations": len(project.conversations),
                "files": len(project.files),
                "knowledge_entries": len(project.knowledge_base),
                "best_model": self._get_best_model(project),
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
        }

    def _calculate_progress(self, project: ProjectContext) -> int:
        """محاسبه پیشرفت کلی"""
        if not project.phases:
            return 0

        total = 0
        for phase in project.phases:
            total += phase.progress
        return round(total / len(project.phases))

    def _get_best_model(self, project: ProjectContext) -> Optional[str]:
        """بهترین مدل بر اساس امتیازات"""
        if not project.model_scores:
            return None

        best = max(project.model_scores.items(), key=lambda x: x[1].get("average", 0))
        return best[0]

    def delete_project(self, project_id: str) -> Dict:
        """حذف پروژه"""
        if project_id in self.projects:
            del self.projects[project_id]
            path = os.path.join(self.storage_path, f"{project_id}.json")
            if os.path.exists(path):
                os.remove(path)
            self._update_registry()

            # 🆕 حذف از SQLite
            self._delete_from_sqlite(project_id)

            return {"success": True, "message": "پروژه حذف شد"}
        return {"success": False, "error": "پروژه یافت نشد"}

    def _delete_from_sqlite(self, project_id: str):
        """حذف پروژه از SQLite"""
        if not self._use_sqlite:
            return

        try:
            db = self._get_db_session()
            if not db:
                return

            try:
                from ..models.project import Project as DBProject, ProjectFile as DBProjectFile

                # حذف فایل‌های مرتبط
                db.query(DBProjectFile).filter(DBProjectFile.project_id == project_id).delete()

                # حذف پروژه
                db.query(DBProject).filter(DBProject.id == project_id).delete()
                db.commit()
                logger.debug(f"Project {project_id} deleted from SQLite")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error deleting project from SQLite: {e}")

    def sync_all_to_sqlite(self) -> Dict:
        """
        سینک همه پروژه‌های موجود به SQLite
        برای مایگریشن از سیستم قبلی
        """
        if not self._use_sqlite:
            return {"success": False, "error": "SQLite disabled"}

        synced = 0
        errors = []

        for project_id, project in self.projects.items():
            try:
                self._save_to_sqlite(project)
                synced += 1
            except Exception as e:
                errors.append({"id": project_id, "error": str(e)})

        return {
            "success": True,
            "synced": synced,
            "errors": errors,
            "total": len(self.projects)
        }

    def load_from_sqlite(self) -> Dict:
        """
        بارگذاری پروژه‌ها از SQLite
        """
        if not self._use_sqlite:
            return {"success": False, "error": "SQLite disabled"}

        try:
            db = self._get_db_session()
            if not db:
                return {"success": False, "error": "Database not available"}

            try:
                from ..models.project import Project as DBProject

                db_projects = db.query(DBProject).all()
                loaded = 0

                for db_proj in db_projects:
                    if db_proj.id not in self.projects:
                        # تبدیل به ProjectContext
                        try:
                            structure = json.loads(db_proj.structure) if db_proj.structure else {}
                            metadata = json.loads(db_proj.metadata) if db_proj.metadata else {}

                            phases = []
                            if structure.get("phases"):
                                for p in structure["phases"]:
                                    phases.append(Phase(**p))

                            project = ProjectContext(
                                project_id=db_proj.id,
                                name=db_proj.name,
                                description=db_proj.description or "",
                                project_type=ProjectType(db_proj.project_type) if db_proj.project_type else ProjectType.CUSTOM,
                                goal=metadata.get("goal", ""),
                                complexity=metadata.get("complexity", "medium"),
                                created_at=db_proj.created_at.isoformat() if db_proj.created_at else datetime.now().isoformat(),
                                updated_at=db_proj.updated_at.isoformat() if db_proj.updated_at else datetime.now().isoformat(),
                                phases=phases,
                                status=db_proj.status or "active",
                                model_scores=metadata.get("model_scores", {}),
                            )
                            self.projects[db_proj.id] = project
                            loaded += 1

                        except Exception as e:
                            logger.warning(f"Could not load project {db_proj.id} from SQLite: {e}")

                return {"success": True, "loaded": loaded, "total": len(db_projects)}

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error loading from SQLite: {e}")
            return {"success": False, "error": str(e)}

    # =====================================
    # 🔄 سینک هوشمند و مدیریت پروژه‌ها
    # =====================================

    async def smart_sync_from_github(self) -> Dict:
        """
        سینک هوشمند از GitHub
        - بارگذاری پروژه‌های جدید
        - تشخیص پروژه‌های تکراری
        - ادغام پروژه‌های مشابه
        """
        if not self.github_storage:
            return {"success": False, "error": "GitHub storage متصل نیست"}

        results = {
            "loaded": [],
            "skipped": [],
            "duplicates": [],
            "merged": [],
            "errors": []
        }

        try:
            # لیست پوشه‌های projects
            folders = await self.github_storage.list_folder("projects")

            for folder in folders:
                if folder.type != "dir":
                    continue

                project_id = folder.name

                # اگر قبلاً وجود دارد
                if project_id in self.projects:
                    results["skipped"].append({
                        "id": project_id,
                        "reason": "already_exists"
                    })
                    continue

                # دریافت metadata
                try:
                    meta_result = await self.github_storage.get_file(
                        f"projects/{project_id}/metadata.json"
                    )

                    if meta_result.get("success") and meta_result.get("content"):
                        import base64
                        content = base64.b64decode(meta_result["content"]).decode('utf-8')
                        data = json.loads(content)

                        # چک تکراری بودن بر اساس نام
                        duplicate = self._find_duplicate_project(data.get("name", ""))
                        if duplicate:
                            results["duplicates"].append({
                                "new_id": project_id,
                                "existing_id": duplicate.project_id,
                                "name": data.get("name")
                            })
                            continue

                        # بارگذاری
                        project = ProjectContext(**data)
                        self.projects[project_id] = project
                        self._save_project_local(project)
                        results["loaded"].append({
                            "id": project_id,
                            "name": project.name
                        })
                except Exception as e:
                    results["errors"].append({
                        "id": project_id,
                        "error": str(e)
                    })

            self._update_registry()

        except Exception as e:
            return {"success": False, "error": str(e), "results": results}

        return {
            "success": True,
            "results": results,
            "total_projects": len(self.projects)
        }

    def _find_duplicate_project(self, name: str) -> Optional[ProjectContext]:
        """پیدا کردن پروژه تکراری بر اساس نام"""
        if not name:
            return None

        name_lower = name.lower().strip()

        for project in self.projects.values():
            if project.name.lower().strip() == name_lower:
                return project

        return None

    def detect_duplicates(self) -> Dict:
        """
        شناسایی پروژه‌های تکراری/مشابه
        """
        duplicates = []
        checked = set()

        projects_list = list(self.projects.values())

        for i, p1 in enumerate(projects_list):
            if p1.project_id in checked:
                continue

            for p2 in projects_list[i+1:]:
                if p2.project_id in checked:
                    continue

                similarity = self._calculate_similarity(p1, p2)
                if similarity > 0.7:  # بیش از 70% مشابه
                    duplicates.append({
                        "project1": {
                            "id": p1.project_id,
                            "name": p1.name,
                            "created_at": p1.created_at
                        },
                        "project2": {
                            "id": p2.project_id,
                            "name": p2.name,
                            "created_at": p2.created_at
                        },
                        "similarity": round(similarity * 100)
                    })
                    checked.add(p2.project_id)

        return {
            "success": True,
            "duplicates": duplicates,
            "count": len(duplicates)
        }

    def _calculate_similarity(self, p1: ProjectContext, p2: ProjectContext) -> float:
        """محاسبه شباهت دو پروژه"""
        score = 0.0
        weights = {
            "name": 0.4,
            "description": 0.2,
            "type": 0.2,
            "goal": 0.2
        }

        # مقایسه نام
        if p1.name.lower() == p2.name.lower():
            score += weights["name"]
        elif p1.name.lower() in p2.name.lower() or p2.name.lower() in p1.name.lower():
            score += weights["name"] * 0.7

        # مقایسه نوع
        if p1.project_type == p2.project_type:
            score += weights["type"]

        # مقایسه توضیحات
        if p1.description and p2.description:
            common_words = set(p1.description.lower().split()) & set(p2.description.lower().split())
            if len(common_words) > 5:
                score += weights["description"]

        # مقایسه هدف
        if p1.goal and p2.goal:
            if p1.goal.lower() == p2.goal.lower():
                score += weights["goal"]

        return score

    def merge_projects(self, keep_id: str, delete_id: str) -> Dict:
        """
        ادغام دو پروژه - نگه‌داشتن یکی و حذف دیگری

        Args:
            keep_id: پروژه‌ای که نگه داشته میشود
            delete_id: پروژه‌ای که حذف میشود (فایل‌هایش به پروژه اول منتقل میشن)
        """
        keep_project = self.projects.get(keep_id)
        delete_project = self.projects.get(delete_id)

        if not keep_project:
            return {"success": False, "error": f"پروژه {keep_id} یافت نشد"}
        if not delete_project:
            return {"success": False, "error": f"پروژه {delete_id} یافت نشد"}

        # انتقال فایل‌ها
        existing_paths = {f.get("path") for f in keep_project.files}
        for file in delete_project.files:
            if file.get("path") not in existing_paths:
                keep_project.files.append(file)

        # انتقال مکالمات
        keep_project.conversations.extend(delete_project.conversations)

        # انتقال knowledge base
        keep_project.knowledge_base.extend(delete_project.knowledge_base)

        # ادغام امتیازات مدل‌ها
        for model_id, scores in delete_project.model_scores.items():
            if model_id not in keep_project.model_scores:
                keep_project.model_scores[model_id] = scores
            else:
                keep_project.model_scores[model_id]["total"] += scores.get("total", 0)
                keep_project.model_scores[model_id]["count"] += scores.get("count", 0)
                if keep_project.model_scores[model_id]["count"] > 0:
                    keep_project.model_scores[model_id]["average"] = round(
                        keep_project.model_scores[model_id]["total"] /
                        keep_project.model_scores[model_id]["count"]
                    )

        # بروزرسانی توضیحات اگه لازمه
        if delete_project.description and not keep_project.description:
            keep_project.description = delete_project.description

        keep_project.updated_at = datetime.now().isoformat()

        # ذخیره و حذف
        self._save_project(keep_project)
        self.delete_project(delete_id)

        return {
            "success": True,
            "message": f"پروژه {delete_id} با {keep_id} ادغام شد",
            "merged_files": len(delete_project.files),
            "merged_conversations": len(delete_project.conversations)
        }

    def get_active_project(self) -> Dict:
        """
        تشخیص پروژه فعال (آخرین پروژه بروزرسانی شده)
        """
        if not self.projects:
            return {"success": False, "error": "هیچ پروژه‌ای وجود ندارد"}

        # مرتب‌سازی بر اساس updated_at
        sorted_projects = sorted(
            self.projects.values(),
            key=lambda p: p.updated_at,
            reverse=True
        )

        active = sorted_projects[0]

        return {
            "success": True,
            "active_project": {
                "id": active.project_id,
                "name": active.name,
                "status": active.status,
                "progress": self._calculate_progress(active),
                "updated_at": active.updated_at
            }
        }


# سرویس سینگلتون
_project_service: Optional[ProjectService] = None

def get_project_service() -> ProjectService:
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
