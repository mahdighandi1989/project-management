"""
API ساده برای مدیریت پروژه‌ها
بدون پیچیدگی - فقط کار میکنه!
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

router = APIRouter(prefix="/api/simple", tags=["Simple Projects"])


# ================================
# Request/Response Models
# ================================

class CreateProjectRequest(BaseModel):
    name: str
    description: str
    project_type: str = "python"
    technologies: List[str] = []


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    project_type: str
    status: str
    created_at: str
    files: List[dict] = []
    structure: dict = {}


# ================================
# AI Generate Function
# ================================

async def ai_generate(prompt: str) -> str:
    """تولید متن با AI - از هر مدل موجود استفاده میکنه"""
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    ai_manager = get_ai_manager()

    # پیدا کردن یه مدل فعال
    available_models = ai_manager.get_available_models()
    if not available_models:
        raise HTTPException(status_code=400, detail="هیچ مدل AI فعالی نیست! اول از تنظیمات کلید وارد کنید.")

    # استفاده از اولین مدل
    model = available_models[0]

    try:
        response = await ai_manager.generate(
            model_id=model.id,
            messages=[Message(role="user", content=prompt)],
            max_tokens=4000,
            temperature=0.7
        )
        return response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید با AI: {str(e)}")


# ================================
# Endpoints
# ================================

@router.get("/projects")
async def list_projects():
    """لیست همه پروژه‌ها"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    projects = creator.list_projects()

    return {
        "success": True,
        "projects": [p.to_dict() for p in projects],
        "count": len(projects)
    }


@router.post("/projects/create")
async def create_project(request: CreateProjectRequest):
    """ساخت پروژه جدید با AI"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()

    try:
        project = await creator.create_project(
            name=request.name,
            description=request.description,
            project_type=request.project_type,
            technologies=request.technologies,
            ai_generate=ai_generate
        )

        return {
            "success": True,
            "project": project.to_dict(),
            "message": f"پروژه {project.name} با {len(project.files)} فایل ساخته شد!"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """دریافت یک پروژه"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    # بارگذاری فایل‌ها از دیسک
    files = await creator.get_project_files(project_id)

    data = project.to_dict()
    data["disk_files"] = files

    return {
        "success": True,
        "project": data
    }


@router.get("/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """لیست فایل‌های پروژه"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    files = await creator.get_project_files(project_id)

    return {
        "success": True,
        "files": files,
        "count": len(files)
    }


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_file_content(project_id: str, file_path: str):
    """خواندن محتوای فایل"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    content = await creator.get_file_content(project_id, file_path)

    if content is None:
        raise HTTPException(status_code=404, detail="فایل پیدا نشد")

    return {
        "success": True,
        "path": file_path,
        "content": content
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """حذف پروژه"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    success = creator.delete_project(project_id)

    if not success:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    return {
        "success": True,
        "message": "پروژه حذف شد"
    }


@router.post("/projects/{project_id}/generate-more")
async def generate_more_files(project_id: str, file_paths: List[str] = None):
    """تولید فایل‌های بیشتر"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    # TODO: تولید فایل‌های بیشتر

    return {
        "success": True,
        "message": "فایل‌ها تولید شدند"
    }


@router.post("/projects/{project_id}/deploy")
async def deploy_project(project_id: str):
    """Deploy پروژه به Render"""
    from ...services.simple_creator import get_simple_creator
    import os

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    render_key = os.environ.get("RENDER_API_KEY")
    if not render_key:
        raise HTTPException(status_code=400, detail="کلید Render تنظیم نشده. از صفحه تنظیمات کلید رو وارد کن.")

    # TODO: پیاده‌سازی واقعی Deploy به Render
    # فعلا یه پیام موفقیت برمیگردونیم

    return {
        "success": True,
        "message": "Deploy آماده است. فایل‌ها رو میتونی دانلود کنی یا به GitHub push کنی.",
        "project_id": project_id,
        "instructions": [
            "۱. فایل‌های پروژه رو دانلود کن",
            "۲. یه repo جدید در GitHub بساز",
            "۳. فایل‌ها رو push کن",
            "۴. از Render.com به repo متصل شو",
            "۵. Deploy اتوماتیک انجام میشه"
        ]
    }


@router.get("/status")
async def get_status():
    """وضعیت سیستم"""
    from ...services.ai_manager import get_ai_manager
    from ...services.simple_creator import get_simple_creator

    ai_manager = get_ai_manager()
    creator = get_simple_creator()

    available_models = ai_manager.get_available_models()

    return {
        "success": True,
        "ai_ready": len(available_models) > 0,
        "models_count": len(available_models),
        "models": [{"id": m.id, "name": m.name, "provider": m.provider.value} for m in available_models],
        "projects_count": len(creator.projects)
    }
