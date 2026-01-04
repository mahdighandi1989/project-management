"""
سیستم مدیریت پروژه پایدار
Persistent Project Management System
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

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
        self._ensure_storage()
        self._load_projects()

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
        """ذخیره پروژه در دیسک"""
        try:
            path = os.path.join(self.storage_path, f"{project.project_id}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(project.dict(), f, ensure_ascii=False, indent=2)
            self._update_registry()
        except Exception as e:
            print(f"Error saving project: {e}")

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
        self._save_project(project)

        return {
            "success": True,
            "project_id": project_id,
            "name": name,
            "phases_count": len(phases),
            "created_at": now
        }

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
            return {"success": True, "message": "پروژه حذف شد"}
        return {"success": False, "error": "پروژه یافت نشد"}


# سرویس سینگلتون
_project_service: Optional[ProjectService] = None

def get_project_service() -> ProjectService:
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
