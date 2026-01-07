"""
API routes for Project Management
مسیرهای API برای مدیریت پروژه
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...services.project_service import (
    get_project_service,
    ProjectType,
    PhaseStatus
)
from ...services.diagram_service import get_diagram_service

router = APIRouter(prefix="/projects", tags=["Projects"])


# =====================================
# مدل‌های درخواست
# =====================================

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    project_type: str = "custom"
    goal: str = ""
    complexity: str = "medium"
    custom_phases: Optional[List[Dict]] = None


class UpdateProgressRequest(BaseModel):
    progress: int
    step_completed: Optional[str] = None


class AddConversationRequest(BaseModel):
    user_message: str
    ai_responses: List[Dict]


class AddKnowledgeRequest(BaseModel):
    knowledge_type: str  # pattern, anti_pattern, lesson, reference
    content: str
    tags: List[str] = []


# =====================================
# پروژه‌ها
# =====================================

@router.get("")
async def list_projects():
    """لیست همه پروژه‌ها"""
    service = get_project_service()
    return service.list_projects()


@router.post("")
async def create_project(request: CreateProjectRequest):
    """ایجاد پروژه جدید"""
    service = get_project_service()

    # تبدیل نوع پروژه
    try:
        project_type = ProjectType(request.project_type)
    except ValueError:
        project_type = ProjectType.CUSTOM

    return service.create_project(
        name=request.name,
        description=request.description,
        project_type=project_type,
        goal=request.goal,
        complexity=request.complexity,
        custom_phases=request.custom_phases
    )


@router.get("/{project_id}")
async def get_project(project_id: str):
    """دریافت اطلاعات پروژه"""
    service = get_project_service()
    result = service.get_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/{project_id}/summary")
async def get_project_summary(project_id: str):
    """خلاصه پروژه"""
    service = get_project_service()
    result = service.get_project_summary(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """حذف پروژه"""
    service = get_project_service()
    return service.delete_project(project_id)


# =====================================
# فازها
# =====================================

@router.post("/{project_id}/next-phase")
async def start_next_phase(project_id: str):
    """شروع فاز بعدی"""
    service = get_project_service()
    result = service.start_next_phase(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.put("/{project_id}/progress")
async def update_progress(project_id: str, request: UpdateProgressRequest):
    """بروزرسانی پیشرفت"""
    service = get_project_service()
    return service.update_phase_progress(
        project_id=project_id,
        progress=request.progress,
        step_completed=request.step_completed
    )


# =====================================
# مکالمات
# =====================================

@router.post("/{project_id}/conversations")
async def add_conversation(project_id: str, request: AddConversationRequest):
    """افزودن مکالمه"""
    service = get_project_service()
    return service.add_conversation(
        project_id=project_id,
        user_message=request.user_message,
        ai_responses=request.ai_responses
    )


# =====================================
# پایگاه دانش
# =====================================

@router.post("/{project_id}/knowledge")
async def add_knowledge(project_id: str, request: AddKnowledgeRequest):
    """افزودن به پایگاه دانش"""
    service = get_project_service()
    return service.add_to_knowledge_base(
        project_id=project_id,
        knowledge_type=request.knowledge_type,
        content=request.content,
        tags=request.tags
    )


# =====================================
# نمودارها
# =====================================

@router.get("/{project_id}/diagram")
async def get_project_diagram(project_id: str, diagram_type: str = "flowchart"):
    """دریافت نمودار پروژه"""
    project_service = get_project_service()
    diagram_service = get_diagram_service()

    project_result = project_service.get_project(project_id)
    if not project_result.get("success"):
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    project = project_result["project"]

    if diagram_type == "flowchart":
        diagram = diagram_service.generate_project_flowchart(project)
    elif diagram_type == "gantt":
        # تبدیل فازها به تسک‌های Gantt
        tasks = []
        for i, phase in enumerate(project.get("phases", [])):
            tasks.append({
                "section": "فازها",
                "name": phase.get("name", f"فاز {i+1}"),
                "id": phase.get("id", f"p{i}"),
                "duration": "1w",
                "status": "done" if phase.get("status") == "completed" else "active" if phase.get("status") == "in_progress" else ""
            })
        diagram = diagram_service.generate_gantt_chart(project.get("name", "پروژه"), tasks)
    else:
        diagram = diagram_service.generate_project_flowchart(project)

    return {
        "success": True,
        "diagram_type": diagram_type,
        "mermaid": diagram,
        "project_id": project_id
    }


# =====================================
# قالب‌ها
# =====================================

# =====================================
# 🔄 سینک هوشمند
# =====================================

@router.post("/sync/github")
async def smart_sync_from_github():
    """سینک هوشمند از GitHub - بارگذاری پروژه‌های جدید و تشخیص تکراری‌ها"""
    service = get_project_service()
    return await service.smart_sync_from_github()


@router.get("/duplicates")
async def detect_duplicate_projects():
    """شناسایی پروژه‌های تکراری/مشابه"""
    service = get_project_service()
    return service.detect_duplicates()


@router.post("/merge")
async def merge_projects(keep_id: str, delete_id: str):
    """
    ادغام دو پروژه
    - keep_id: پروژه‌ای که نگه داشته میشه
    - delete_id: پروژه‌ای که حذف میشه (داده‌هاش منتقل میشه)
    """
    service = get_project_service()
    result = service.merge_projects(keep_id, delete_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/active")
async def get_active_project():
    """تشخیص پروژه فعال (آخرین پروژه بروزرسانی شده)"""
    service = get_project_service()
    return service.get_active_project()


# =====================================
# قالب‌ها
# =====================================

@router.get("/templates/types")
async def get_project_types():
    """لیست انواع پروژه"""
    return {
        "success": True,
        "types": [
            {"id": "web_app", "name": "اپلیکیشن وب", "icon": "🌐"},
            {"id": "mobile_app", "name": "اپلیکیشن موبایل", "icon": "📱"},
            {"id": "api_service", "name": "سرویس API", "icon": "⚙️"},
            {"id": "data_pipeline", "name": "پایپلاین داده", "icon": "📊"},
            {"id": "ml_project", "name": "پروژه ML", "icon": "🤖"},
            {"id": "custom", "name": "سفارشی", "icon": "📦"},
        ]
    }
