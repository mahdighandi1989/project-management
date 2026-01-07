"""
🔗 Unified API Routes - مسیرهای یکپارچه
API های جدید برای Creator Engine یکپارچه
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import os

from ...services.unified_storage import (
    get_unified_storage,
    configure_unified_storage,
    ProjectConfig
)
from ...services.deploy_service import (
    get_deploy_manager,
    configure_deploy_manager,
    DeployProvider,
    DeployStatus
)
from ...services.dynamic_diagram_service import (
    get_diagram_service,
    DiagramInfo
)

router = APIRouter(prefix="/api/unified", tags=["unified"])


# =====================================
# 📦 پروژه‌ها
# =====================================

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    project_type: str = "python"
    technologies: List[str] = []


class SaveFileRequest(BaseModel):
    file_path: str
    content: str
    folder: str = "src"


@router.post("/projects/create")
async def create_project(request: CreateProjectRequest):
    """ایجاد پروژه جدید"""
    storage = get_unified_storage()

    config = await storage.create_project(
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        technologies=request.technologies
    )

    return {
        "success": True,
        "project": {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "project_type": config.project_type,
            "path": str(storage.projects_path / config.id),
            "created_at": config.created_at
        }
    }


@router.get("/projects")
async def list_projects():
    """لیست همه پروژه‌ها"""
    storage = get_unified_storage()
    projects = await storage.list_projects()

    return {
        "success": True,
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "project_type": p.project_type,
                "technologies": p.technologies,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "github_synced": p.github_synced,
                "render_deployed": p.render_deployed,
                "render_url": p.render_url
            }
            for p in projects
        ],
        "total": len(projects)
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """دریافت اطلاعات پروژه"""
    storage = get_unified_storage()
    config = await storage.get_project_config(project_id)

    if not config:
        raise HTTPException(status_code=404, detail="Project not found")

    # تشخیص نوع پروژه
    detected_type = await storage.detect_project_type(project_id)

    return {
        "success": True,
        "project": {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "project_type": config.project_type,
            "detected_type": detected_type,
            "technologies": config.technologies,
            "entry_point": config.entry_point,
            "build_command": config.build_command,
            "start_command": config.start_command,
            "port": config.port,
            "env_vars": config.env_vars,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
            "github_synced": config.github_synced,
            "render_deployed": config.render_deployed,
            "render_service_id": config.render_service_id,
            "render_url": config.render_url
        }
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """حذف پروژه"""
    storage = get_unified_storage()
    result = await storage.delete_project(project_id)

    return {
        "success": result,
        "message": "Project deleted" if result else "Project not found"
    }


# =====================================
# 📄 فایل‌ها
# =====================================

@router.post("/projects/{project_id}/files")
async def save_file(project_id: str, request: SaveFileRequest):
    """ذخیره فایل در پروژه"""
    storage = get_unified_storage()

    file_info = await storage.save_file(
        project_id=project_id,
        file_path=request.file_path,
        content=request.content,
        folder=request.folder
    )

    return {
        "success": True,
        "file": {
            "path": file_info.path,
            "name": file_info.name,
            "size": file_info.size,
            "language": file_info.language
        }
    }


@router.get("/projects/{project_id}/files")
async def list_files(project_id: str, folder: str = None, recursive: bool = True):
    """لیست فایل‌های پروژه"""
    storage = get_unified_storage()
    files = await storage.list_files(project_id, folder, recursive)

    return {
        "success": True,
        "files": [
            {
                "path": f.path,
                "name": f.name,
                "size": f.size,
                "language": f.language,
                "last_modified": f.last_modified
            }
            for f in files
        ],
        "total": len(files)
    }


@router.get("/projects/{project_id}/files/{file_path:path}")
async def read_file(project_id: str, file_path: str, folder: str = "src"):
    """خواندن محتوای فایل"""
    storage = get_unified_storage()
    content = await storage.read_file(project_id, file_path, folder)

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "success": True,
        "content": content,
        "path": file_path
    }


@router.delete("/projects/{project_id}/files/{file_path:path}")
async def delete_file(project_id: str, file_path: str, folder: str = "src"):
    """حذف فایل"""
    storage = get_unified_storage()
    result = await storage.delete_file(project_id, file_path, folder)

    return {
        "success": result,
        "message": "File deleted" if result else "File not found"
    }


@router.post("/projects/{project_id}/upload")
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    folder: str = Form("src")
):
    """آپلود فایل"""
    storage = get_unified_storage()

    content = await file.read()
    file_info = await storage.save_file(
        project_id=project_id,
        file_path=file.filename,
        content=content,
        folder=folder
    )

    return {
        "success": True,
        "file": {
            "path": file_info.path,
            "name": file_info.name,
            "size": file_info.size
        }
    }


# =====================================
# 🔄 سینک GitHub
# =====================================

@router.post("/projects/{project_id}/sync/github")
async def sync_to_github(project_id: str):
    """سینک پروژه با GitHub"""
    storage = get_unified_storage()
    result = await storage.sync_project_to_github(project_id)

    return result


# =====================================
# 🚀 Deploy
# =====================================

class DeployRequest(BaseModel):
    project_name: Optional[str] = None
    env_vars: Dict[str, str] = {}
    auto_deploy: bool = True


class ConfigureRenderRequest(BaseModel):
    api_key: str


@router.post("/deploy/configure/render")
async def configure_render(request: ConfigureRenderRequest):
    """تنظیم API key رندر"""
    manager = configure_deploy_manager(render_api_key=request.api_key)

    # ذخیره در env یا config
    os.environ["RENDER_API_KEY"] = request.api_key

    return {
        "success": True,
        "message": "Render API key configured",
        "is_configured": manager.render.is_configured()
    }


@router.get("/deploy/render/status")
async def get_render_status():
    """وضعیت اتصال به Render"""
    manager = get_deploy_manager()

    if not manager.render.is_configured():
        return {
            "success": True,
            "configured": False,
            "message": "Render API key not configured"
        }

    # تست اتصال
    services = await manager.render.list_services()

    return {
        "success": True,
        "configured": True,
        "services_count": len(services) if isinstance(services, list) else 0
    }


@router.get("/deploy/render/services")
async def list_render_services():
    """لیست سرویس‌های Render"""
    manager = get_deploy_manager()

    if not manager.render.is_configured():
        raise HTTPException(status_code=400, detail="Render not configured")

    services = await manager.render.list_services()
    return {
        "success": True,
        "services": services
    }


@router.post("/projects/{project_id}/deploy/prepare")
async def prepare_for_deploy(project_id: str):
    """آماده‌سازی پروژه برای Deploy"""
    storage = get_unified_storage()
    result = await storage.prepare_for_render(project_id)

    return result


@router.post("/projects/{project_id}/deploy/render")
async def deploy_to_render(project_id: str, request: DeployRequest):
    """Deploy یک‌کلیکه به Render"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    if not manager.render.is_configured():
        raise HTTPException(status_code=400, detail="Render API key not configured")

    # دریافت اطلاعات پروژه
    config = await storage.get_project_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Project not found")

    # آماده‌سازی فایل‌ها
    await storage.prepare_for_render(project_id)

    # سینک با GitHub (اجباری برای Render)
    if not config.github_synced:
        sync_result = await storage.sync_project_to_github(project_id)
        if not sync_result.get("success"):
            return {
                "success": False,
                "error": "Failed to sync to GitHub. Render requires GitHub repo."
            }

    # تشخیص نوع پروژه
    project_type = await storage.detect_project_type(project_id)

    # GitHub URL
    github_url = f"https://github.com/{storage.github_owner}/{storage.github_repo}"

    # Deploy
    deployment = await manager.quick_deploy(
        project_id=project_id,
        project_name=request.project_name or config.name,
        project_type=project_type,
        github_repo_url=github_url,
        github_branch=storage.github_branch,
        root_dir=f"projects/{project_id}",
        env_vars=request.env_vars
    )

    # بروزرسانی config
    if deployment.service_id:
        config.render_deployed = True
        config.render_service_id = deployment.service_id
        config.render_url = deployment.url
        await storage._save_project_config(project_id, config)

    return {
        "success": deployment.status != DeployStatus.FAILED,
        "deployment": {
            "id": deployment.id,
            "service_id": deployment.service_id,
            "status": deployment.status.value,
            "url": deployment.url,
            "error": deployment.error
        }
    }


@router.get("/projects/{project_id}/deploy/status")
async def get_deploy_status(project_id: str):
    """وضعیت Deploy پروژه"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    config = await storage.get_project_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Project not found")

    if not config.render_service_id:
        return {
            "success": True,
            "deployed": False,
            "message": "Project not deployed"
        }

    status = await manager.render.get_deploy_status(config.render_service_id)

    return {
        "success": True,
        "deployed": True,
        "service_id": config.render_service_id,
        "url": config.render_url,
        "status": status
    }


@router.post("/projects/{project_id}/deploy/redeploy")
async def redeploy_project(project_id: str):
    """Redeploy پروژه"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    config = await storage.get_project_config(project_id)
    if not config or not config.render_service_id:
        raise HTTPException(status_code=400, detail="Project not deployed")

    result = await manager.render.trigger_deploy(config.render_service_id)
    return result


@router.post("/projects/{project_id}/deploy/stop")
async def stop_deployment(project_id: str):
    """متوقف کردن سرویس"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    config = await storage.get_project_config(project_id)
    if not config or not config.render_service_id:
        raise HTTPException(status_code=400, detail="Project not deployed")

    result = await manager.render.suspend_service(config.render_service_id)
    return result


@router.post("/projects/{project_id}/deploy/start")
async def start_deployment(project_id: str):
    """راه‌اندازی مجدد سرویس"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    config = await storage.get_project_config(project_id)
    if not config or not config.render_service_id:
        raise HTTPException(status_code=400, detail="Project not deployed")

    result = await manager.render.resume_service(config.render_service_id)
    return result


@router.get("/projects/{project_id}/deploy/logs")
async def get_deploy_logs(project_id: str, lines: int = 100):
    """لاگ‌های Deploy"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    config = await storage.get_project_config(project_id)
    if not config or not config.render_service_id:
        raise HTTPException(status_code=400, detail="Project not deployed")

    result = await manager.render.get_logs(config.render_service_id, lines)
    return result


# =====================================
# 📊 نمودارها
# =====================================

class CustomDiagramRequest(BaseModel):
    diagram_type: str
    data: Dict[str, Any]


@router.get("/projects/{project_id}/diagrams")
async def get_project_diagrams(project_id: str, regenerate: bool = False):
    """دریافت نمودارهای پروژه"""
    storage = get_unified_storage()
    diagram_service = get_diagram_service()

    config = await storage.get_project_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Project not found")

    project_path = storage.projects_path / project_id

    # بررسی کش
    cached = diagram_service.get_cached_diagrams(project_id)

    if not cached or regenerate:
        diagrams = await diagram_service.generate_all_diagrams(
            project_id=project_id,
            project_path=project_path,
            project_name=config.name
        )
    else:
        diagrams = cached

    return {
        "success": True,
        "project_id": project_id,
        "project_name": config.name,
        "diagrams": [
            {
                "id": d.id,
                "name": d.name,
                "type": d.type,
                "content": d.content,
                "source_files": d.source_files,
                "created_at": d.created_at,
                "auto_generated": d.auto_generated
            }
            for d in diagrams
        ],
        "total": len(diagrams)
    }


@router.get("/projects/{project_id}/diagrams/{diagram_type}")
async def get_specific_diagram(project_id: str, diagram_type: str, regenerate: bool = False):
    """دریافت یک نمودار خاص"""
    storage = get_unified_storage()
    diagram_service = get_diagram_service()

    config = await storage.get_project_config(project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Project not found")

    project_path = storage.projects_path / project_id

    if regenerate:
        diagram = await diagram_service.update_diagram(
            project_id=project_id,
            diagram_type=diagram_type,
            project_path=project_path,
            project_name=config.name
        )
    else:
        cached = diagram_service.get_cached_diagrams(project_id)
        diagram = next((d for d in cached if d.type == diagram_type), None)

        if not diagram:
            diagram = await diagram_service.update_diagram(
                project_id=project_id,
                diagram_type=diagram_type,
                project_path=project_path,
                project_name=config.name
            )

    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")

    return {
        "success": True,
        "diagram": {
            "id": diagram.id,
            "name": diagram.name,
            "type": diagram.type,
            "content": diagram.content,
            "source_files": diagram.source_files
        }
    }


@router.post("/projects/{project_id}/diagrams/custom")
async def create_custom_diagram(project_id: str, request: CustomDiagramRequest):
    """ایجاد نمودار سفارشی"""
    diagram_service = get_diagram_service()

    content = diagram_service.generate_custom_diagram(
        diagram_type=request.diagram_type,
        data=request.data
    )

    return {
        "success": True,
        "diagram": {
            "type": request.diagram_type,
            "content": content
        }
    }


@router.post("/projects/{project_id}/diagrams/save")
async def save_diagram(
    project_id: str,
    diagram_type: str = Form(...),
    content: str = Form(...),
    name: str = Form(None)
):
    """ذخیره نمودار در پروژه"""
    storage = get_unified_storage()

    file_path = await storage.save_diagram(
        project_id=project_id,
        diagram_type=diagram_type,
        content=content,
        name=name
    )

    return {
        "success": True,
        "file_path": file_path
    }


# =====================================
# 📦 Export/Import
# =====================================

@router.get("/projects/{project_id}/export")
async def export_project(project_id: str):
    """Export پروژه به ZIP"""
    storage = get_unified_storage()
    config = await storage.get_project_config(project_id)

    if not config:
        raise HTTPException(status_code=404, detail="Project not found")

    zip_content = await storage.export_project(project_id)

    if not zip_content:
        raise HTTPException(status_code=500, detail="Export failed")

    from fastapi.responses import Response
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{config.name}.zip"'
        }
    )


@router.post("/projects/import")
async def import_project(
    file: UploadFile = File(...),
    name: str = Form(...)
):
    """Import پروژه از ZIP"""
    storage = get_unified_storage()

    content = await file.read()
    config = await storage.import_project(content, name)

    if not config:
        raise HTTPException(status_code=500, detail="Import failed")

    return {
        "success": True,
        "project": {
            "id": config.id,
            "name": config.name,
            "project_type": config.project_type
        }
    }


# =====================================
# ⚙️ تنظیمات
# =====================================

class ConfigureStorageRequest(BaseModel):
    github_token: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    render_api_key: Optional[str] = None
    auto_sync: bool = False


@router.post("/configure")
async def configure_storage(request: ConfigureStorageRequest):
    """پیکربندی سرویس‌ها"""
    # تنظیم storage
    if any([request.github_token, request.github_owner, request.github_repo]):
        configure_unified_storage(
            github_token=request.github_token,
            github_owner=request.github_owner,
            github_repo=request.github_repo,
            auto_sync=request.auto_sync
        )

    # تنظیم Render
    if request.render_api_key:
        configure_deploy_manager(render_api_key=request.render_api_key)
        os.environ["RENDER_API_KEY"] = request.render_api_key

    # ذخیره در env
    if request.github_token:
        os.environ["GITHUB_TOKEN"] = request.github_token
    if request.github_owner:
        os.environ["GITHUB_OWNER"] = request.github_owner
    if request.github_repo:
        os.environ["GITHUB_REPO"] = request.github_repo

    return {
        "success": True,
        "message": "Configuration updated"
    }


@router.get("/status")
async def get_system_status():
    """وضعیت سیستم"""
    storage = get_unified_storage()
    manager = get_deploy_manager()

    return {
        "success": True,
        "storage": {
            "workspace_path": str(storage.workspace_path),
            "github_configured": bool(storage.github_token and storage.github_owner),
            "auto_sync": storage.auto_sync
        },
        "deploy": {
            "render_configured": manager.render.is_configured()
        }
    }
