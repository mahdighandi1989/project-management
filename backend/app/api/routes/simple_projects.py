"""
API ساده برای مدیریت پروژه‌ها
بدون پیچیدگی - فقط کار میکنه!
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import os

from ...core.database import get_db

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
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """حذف پروژه"""
    from ...services.simple_creator import get_simple_creator
    from ...models.project import Project, ProjectFile

    creator = get_simple_creator()

    # حذف از memory و فایل‌سیستم
    memory_deleted = creator.delete_project(project_id)

    # حذف از دیتابیس هم
    try:
        # حذف داده‌های مرتبط با ژورنال
        try:
            from .project_journal import ActivityLog, Report, ReportTrigger
            db.query(ActivityLog).filter(ActivityLog.project_id == project_id).delete()
            db.query(Report).filter(Report.project_id == project_id).delete()
            db.query(ReportTrigger).filter(ReportTrigger.project_id == project_id).delete()
        except Exception:
            pass

        # حذف فایل‌ها و پروژه از دیتابیس
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).delete()
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            db.delete(project)
            db.commit()
    except Exception as e:
        db.rollback()
        # ادامه بده حتی اگه از دیتابیس نتونست حذف کنه

    if not memory_deleted and not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    return {
        "success": True,
        "message": "پروژه حذف شد"
    }


class GenerateMoreRequest(BaseModel):
    """درخواست تولید فایل‌های بیشتر"""
    file_paths: List[str] = []
    descriptions: dict = {}  # path -> description


@router.post("/projects/{project_id}/generate-more")
async def generate_more_files(project_id: str, request: GenerateMoreRequest = None):
    """تولید فایل‌های بیشتر برای پروژه"""
    from ...services.simple_creator import get_simple_creator
    import aiofiles
    from pathlib import Path

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    file_paths = request.file_paths if request else []
    descriptions = request.descriptions if request else {}

    if not file_paths:
        raise HTTPException(status_code=400, detail="لیست فایل‌ها خالی است")

    generated_files = []
    errors = []
    project_path = creator.workspace / project_id

    for file_path in file_paths:
        try:
            # توضیح فایل
            file_desc = descriptions.get(file_path, f"فایل {file_path} برای پروژه")

            # تولید محتوای فایل با AI
            content = await creator._generate_file(
                project_name=project.name,
                project_desc=project.description,
                project_type=project.project_type,
                file_path=file_path,
                file_desc=file_desc,
                ai_generate=ai_generate
            )

            # ذخیره فایل در دیسک
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)

            # اضافه کردن به لیست فایل‌های پروژه
            from ...services.simple_creator import ProjectFile
            new_file = ProjectFile(
                path=file_path,
                content=content,
                language=creator._detect_language(file_path)
            )
            project.files.append(new_file)

            generated_files.append({
                "path": file_path,
                "size": len(content),
                "language": new_file.language
            })

        except HTTPException:
            raise
        except Exception as e:
            errors.append({"path": file_path, "error": str(e)})

    # ذخیره metadata پروژه
    await creator._save_project_meta(project)

    return {
        "success": len(errors) == 0,
        "project_id": project_id,
        "generated": generated_files,
        "errors": errors,
        "message": f"{len(generated_files)} فایل تولید شد" + (f" ({len(errors)} خطا)" if errors else "")
    }


class DeployRequest(BaseModel):
    """درخواست Deploy"""
    github_repo_url: Optional[str] = None
    github_branch: str = "main"
    env_vars: dict = {}


@router.post("/projects/{project_id}/deploy")
async def deploy_project(project_id: str, request: DeployRequest = None):
    """Deploy پروژه به Render"""
    from ...services.simple_creator import get_simple_creator
    from ...services.deploy_service import get_deploy_manager
    from ...services.github_storage import get_github_storage
    import os

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    render_key = os.environ.get("RENDER_API_KEY")
    if not render_key:
        raise HTTPException(status_code=400, detail="کلید Render تنظیم نشده. از صفحه تنظیمات کلید رو وارد کن.")

    # دریافت deploy manager
    deploy_manager = get_deploy_manager()
    deploy_manager.configure_render(render_key)

    # بررسی GitHub repo
    github_repo_url = None
    if request and request.github_repo_url:
        github_repo_url = request.github_repo_url
    else:
        # سعی کن از GitHub storage اطلاعات رو بگیر
        github_storage = get_github_storage()
        if github_storage.token and github_storage.owner and github_storage.repo:
            github_repo_url = f"https://github.com/{github_storage.owner}/{github_storage.repo}"

    if not github_repo_url:
        # اگر GitHub repo نداریم، راهنمای دستی بده
        return {
            "success": True,
            "deployed": False,
            "message": "برای Deploy خودکار، اول پروژه رو به GitHub push کن.",
            "project_id": project_id,
            "instructions": [
                "۱. فایل‌های پروژه رو دانلود کن",
                "۲. یه repo جدید در GitHub بساز",
                "۳. فایل‌ها رو push کن",
                "۴. برگرد و دوباره Deploy رو بزن با آدرس repo"
            ]
        }

    try:
        # Deploy به Render
        deployment = await deploy_manager.quick_deploy(
            project_id=project_id,
            project_name=project.name,
            project_type=project.project_type,
            github_repo_url=github_repo_url,
            github_branch=request.github_branch if request else "main",
            root_dir=f"ai-workspace/projects/{project_id}/generated",
            env_vars=request.env_vars if request else {}
        )

        if deployment.error:
            return {
                "success": False,
                "error": deployment.error,
                "project_id": project_id
            }

        return {
            "success": True,
            "deployed": True,
            "message": f"پروژه در حال Deploy شدن به Render است!",
            "project_id": project_id,
            "deployment_id": deployment.id,
            "service_id": deployment.service_id,
            "status": deployment.status.value,
            "url": deployment.url,
            "dashboard_url": f"https://dashboard.render.com/web/{deployment.service_id}" if deployment.service_id else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در Deploy: {str(e)}")


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
