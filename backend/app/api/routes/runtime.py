"""
Runtime API Routes
اندپوینت‌های اجرای پروژه

Features:
- اجرای پروژه در Docker
- بررسی قابلیت‌های سیستم
- مدیریت پروژه‌های در حال اجرا
- لاگ‌ها و monitoring
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["Project Runtime"])


# =====================================
# Request/Response Models
# =====================================

class RunProjectRequest(BaseModel):
    """درخواست اجرای پروژه"""
    project_id: str
    custom_port: Optional[int] = None
    force_rebuild: bool = False


class StopProjectRequest(BaseModel):
    """درخواست توقف پروژه"""
    project_id: str


# =====================================
# Helper Functions
# =====================================

def get_runtime_executor():
    """دریافت سرویس اجرا"""
    from ...services.runtime_executor import get_runtime_executor
    executor = get_runtime_executor()
    if not executor._initialized:
        from ...services.github_storage import get_github_storage
        github = get_github_storage()
        executor.initialize(github)
    return executor


def get_capability_detector():
    """دریافت سرویس تشخیص قابلیت"""
    from ...services.capability_detector import get_capability_detector
    detector = get_capability_detector()
    if not detector._initialized:
        from ...services.github_storage import get_github_storage
        github = get_github_storage()
        detector.initialize(github)
    return detector


def get_github_storage():
    """دریافت GitHub storage"""
    from ...services.github_storage import get_github_storage as _get_github
    return _get_github()


async def get_project_files(project_id: str) -> List[Dict]:
    """دریافت فایل‌های پروژه از GitHub"""
    github = get_github_storage()
    if not github or not github.token:
        return []

    files = []
    try:
        project_files = await github.get_project_files(project_id)
        for folder_type, folder_files in project_files.get("files", {}).items():
            for f in folder_files:
                if f.get("name") and f["name"] != ".gitkeep":
                    # خواندن محتوای فایل
                    import base64
                    file_path = f"projects/{project_id}/{folder_type}/{f['name']}"
                    result = await github.get_file(file_path)
                    content = ""
                    if result.get("success") and result.get("content"):
                        content = base64.b64decode(result["content"]).decode('utf-8', errors='replace')

                    files.append({
                        "name": f["name"],
                        "folder": folder_type,
                        "content": content,
                        "size": f.get("size", 0)
                    })
    except Exception as e:
        logger.error(f"Error getting project files: {e}")

    return files


# =====================================
# System Capabilities Endpoints
# =====================================

@router.get("/capabilities")
async def get_system_capabilities():
    """
    دریافت قابلیت‌های سیستم

    Returns:
        - اطلاعات سیستم عامل
        - وضعیت Docker
        - runtime های موجود
        - انواع پروژه‌های قابل اجرا
    """
    try:
        detector = get_capability_detector()
        return {
            "success": True,
            **detector.get_capability_summary()
        }
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/can-run/{project_id}")
async def check_can_run_project(project_id: str):
    """
    بررسی اینکه آیا پروژه قابل اجرا است

    Returns:
        - can_run: آیا مستقیم قابل اجرا است
        - can_run_with_docker: آیا با Docker قابل اجرا است
        - missing_capabilities: قابلیت‌های missing
        - upgrade_needed: آیا نیاز به ارتقا دارد
    """
    try:
        # دریافت اطلاعات پروژه
        from ...services.project_service import get_project_service
        project_service = get_project_service()
        project_data = project_service.get_project(project_id)

        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        project = project_data["project"]
        project_type = project.get("type", "custom")

        # دریافت فایل‌های پروژه
        files = await get_project_files(project_id)

        # تحلیل نیازمندی‌ها
        detector = get_capability_detector()
        requirements = await detector.analyze_project_requirements(
            project_id, project_type, files
        )

        return {
            "success": True,
            "project_id": project_id,
            "project_type": project_type,
            "can_run": requirements.can_run,
            "can_run_with_docker": requirements.can_run_with_docker,
            "upgrade_needed": requirements.upgrade_needed,
            "required_capabilities": [
                {
                    "name": cap.name,
                    "type": cap.type.value,
                    "status": cap.status.value,
                    "docker_image": cap.docker_image
                }
                for cap in requirements.required_capabilities
            ],
            "missing_capabilities": [
                {
                    "name": cap.name,
                    "type": cap.type.value,
                    "docker_image": cap.docker_image,
                    "install_command": cap.install_command
                }
                for cap in requirements.missing_capabilities
            ],
            "notes": requirements.notes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request-upgrade/{project_id}")
async def request_system_upgrade(project_id: str):
    """
    درخواست ارتقای سیستم برای اجرای یک پروژه

    این درخواست را در GitHub ذخیره می‌کند تا در deployment بعدی
    قابلیت‌های لازم نصب شوند.
    """
    try:
        # دریافت اطلاعات پروژه
        from ...services.project_service import get_project_service
        project_service = get_project_service()
        project_data = project_service.get_project(project_id)

        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        project = project_data["project"]
        project_type = project.get("type", "custom")

        # دریافت فایل‌ها
        files = await get_project_files(project_id)

        # تحلیل نیازمندی‌ها
        detector = get_capability_detector()
        requirements = await detector.analyze_project_requirements(
            project_id, project_type, files
        )

        if not requirements.missing_capabilities:
            return {
                "success": True,
                "message": "نیازی به ارتقا نیست - همه قابلیت‌ها موجود است",
                "can_run": True
            }

        # ذخیره درخواست ارتقا
        saved = await detector.save_upgrade_requirements(project_id, requirements)

        return {
            "success": saved,
            "message": "درخواست ارتقا ثبت شد - در deployment بعدی اعمال می‌شود" if saved else "خطا در ثبت درخواست",
            "missing_capabilities": [cap.name for cap in requirements.missing_capabilities],
            "will_install": [
                cap.docker_image for cap in requirements.missing_capabilities
                if cap.docker_image
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting upgrade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Project Execution Endpoints
# =====================================

@router.post("/run")
async def run_project(request: RunProjectRequest):
    """
    اجرای پروژه در Docker container

    Args:
        project_id: شناسه پروژه
        custom_port: پورت سفارشی (اختیاری)
        force_rebuild: بازسازی اجباری

    Returns:
        - status: وضعیت اجرا
        - url: آدرس دسترسی
        - port: پورت
        - logs: لاگ‌ها
    """
    try:
        executor = get_runtime_executor()

        if not executor.is_docker_available():
            raise HTTPException(
                status_code=400,
                detail="Docker در دسترس نیست. برای اجرای پروژه‌ها نیاز به Docker دارید."
            )

        # بررسی پروژه در حال اجرا
        existing = executor.get_running_project(request.project_id)
        if existing and existing.status.value == "running" and not request.force_rebuild:
            return {
                "success": True,
                "status": existing.status.value,
                "url": existing.url,
                "port": existing.port,
                "container_id": existing.container_id,
                "logs": existing.logs[-20:],
                "message": "پروژه قبلاً در حال اجراست"
            }

        # توقف نسخه قبلی اگر force_rebuild
        if existing and request.force_rebuild:
            await executor.stop_project(request.project_id)

        # دریافت فایل‌های پروژه
        files = await get_project_files(request.project_id)

        if not files:
            raise HTTPException(
                status_code=400,
                detail="فایلی برای اجرا یافت نشد. ابتدا پروژه را بسازید."
            )

        # اجرای پروژه
        running = await executor.start_project(
            request.project_id,
            files,
            custom_port=request.custom_port
        )

        return {
            "success": running.status.value not in ["error"],
            "status": running.status.value,
            "url": running.url,
            "port": running.port,
            "container_id": running.container_id,
            "runtime_type": running.runtime_type.value,
            "started_at": running.started_at.isoformat() if running.started_at else None,
            "logs": running.logs[-20:],
            "error": running.error
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_project(request: StopProjectRequest):
    """
    توقف پروژه در حال اجرا
    """
    try:
        executor = get_runtime_executor()
        stopped = await executor.stop_project(request.project_id)

        return {
            "success": stopped,
            "message": "پروژه متوقف شد" if stopped else "پروژه در حال اجرا نبود"
        }

    except Exception as e:
        logger.error(f"Error stopping project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}")
async def get_project_runtime_status(project_id: str):
    """
    دریافت وضعیت اجرای پروژه
    """
    try:
        executor = get_runtime_executor()
        running = executor.get_running_project(project_id)

        if not running:
            return {
                "success": True,
                "status": "not_running",
                "message": "پروژه در حال اجرا نیست"
            }

        return {
            "success": True,
            "status": running.status.value,
            "url": running.url,
            "port": running.port,
            "container_id": running.container_id,
            "runtime_type": running.runtime_type.value,
            "started_at": running.started_at.isoformat() if running.started_at else None,
            "error": running.error
        }

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{project_id}")
async def get_project_logs(
    project_id: str,
    lines: int = Query(default=100, ge=1, le=1000)
):
    """
    دریافت لاگ‌های پروژه در حال اجرا
    """
    try:
        executor = get_runtime_executor()
        logs = await executor.get_project_logs(project_id, lines)

        return {
            "success": True,
            "project_id": project_id,
            "logs": logs
        }

    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/running")
async def get_all_running_projects():
    """
    لیست همه پروژه‌های در حال اجرا
    """
    try:
        executor = get_runtime_executor()
        running = executor.get_all_running_projects()

        return {
            "success": True,
            "count": len(running),
            "projects": [
                {
                    "project_id": proj_id,
                    "status": proj.status.value,
                    "url": proj.url,
                    "port": proj.port,
                    "runtime_type": proj.runtime_type.value,
                    "started_at": proj.started_at.isoformat() if proj.started_at else None
                }
                for proj_id, proj in running.items()
            ]
        }

    except Exception as e:
        logger.error(f"Error getting running projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-all")
async def stop_all_projects():
    """
    توقف همه پروژه‌های در حال اجرا
    """
    try:
        executor = get_runtime_executor()
        await executor.cleanup_all()

        return {
            "success": True,
            "message": "همه پروژه‌ها متوقف شدند"
        }

    except Exception as e:
        logger.error(f"Error stopping all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Upgrade Management Endpoints
# =====================================

@router.post("/apply-upgrades")
async def apply_pending_upgrades():
    """
    اعمال ارتقاهای pending
    این endpoint معمولاً در startup فراخوانی می‌شود
    """
    try:
        detector = get_capability_detector()
        results = await detector.check_and_apply_upgrades()

        return {
            "success": True,
            **results
        }

    except Exception as e:
        logger.error(f"Error applying upgrades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docker-status")
async def get_docker_status():
    """
    وضعیت Docker
    """
    try:
        executor = get_runtime_executor()
        detector = get_capability_detector()

        caps = detector.get_capability_summary()

        return {
            "success": True,
            "docker_available": executor.is_docker_available(),
            "docker_version": caps.get("docker", {}).get("version"),
            "can_run_projects": executor.is_docker_available()
        }

    except Exception as e:
        logger.error(f"Error checking docker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
