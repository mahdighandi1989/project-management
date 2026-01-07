"""
🔗 External Projects API - مسیرهای API پروژه‌های خارجی
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import logging

from ...services.external_project_connector import get_external_project_connector, ExternalProjectConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external-projects", tags=["external-projects"])


# =====================================
# مدل‌های درخواست
# =====================================

class ConnectGitHubRequest(BaseModel):
    """درخواست اتصال به GitHub"""
    repo_url: str
    token: Optional[str] = None
    branch: str = "main"


class ConnectRenderRequest(BaseModel):
    """درخواست اتصال به Render"""
    service_url: str
    api_key: Optional[str] = None
    service_id: Optional[str] = None


class AnalyzeProjectRequest(BaseModel):
    """درخواست تحلیل پروژه"""
    analysis_type: str = "overview"  # overview, issues, suggestions


# =====================================
# دریافت connector
# =====================================

def get_connector() -> ExternalProjectConnector:
    """دریافت نمونه connector"""
    return get_external_project_connector()


# =====================================
# مسیرهای API
# =====================================

@router.get("/")
async def list_external_projects(
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """لیست همه پروژه‌های خارجی متصل شده"""
    return connector.list_projects()


@router.post("/connect/github")
async def connect_github_repo(
    request: ConnectGitHubRequest,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """
    اتصال به ریپوی GitHub

    - **repo_url**: آدرس ریپو (مثال: https://github.com/owner/repo)
    - **token**: Personal Access Token (برای ریپوهای خصوصی)
    - **branch**: شاخه مورد نظر (پیش‌فرض: main)
    """
    result = await connector.connect_github_repo(
        repo_url=request.repo_url,
        token=request.token,
        branch=request.branch
    )

    if not result.get("success"):
        if result.get("needs_auth"):
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Authentication required")
            )
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Connection failed")
        )

    return result


@router.post("/connect/render")
async def connect_render_app(
    request: ConnectRenderRequest,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """
    اتصال به اپلیکیشن Render

    - **service_url**: آدرس اپلیکیشن
    - **api_key**: API Key رندر (اختیاری)
    - **service_id**: شناسه سرویس (اختیاری)
    """
    result = await connector.connect_render_app(
        service_url=request.service_url,
        api_key=request.api_key,
        service_id=request.service_id
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/{project_id}")
async def get_external_project(
    project_id: str,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """دریافت اطلاعات یک پروژه خارجی"""
    result = connector.get_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.delete("/{project_id}")
async def disconnect_external_project(
    project_id: str,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """قطع اتصال از پروژه خارجی"""
    result = connector.disconnect_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/{project_id}/sync")
async def sync_external_project(
    project_id: str,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """بروزرسانی اطلاعات پروژه از منبع"""
    result = await connector.sync_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: str,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """لیست فایل‌های پروژه"""
    project_result = connector.get_project(project_id)
    if not project_result.get("success"):
        raise HTTPException(status_code=404, detail=project_result.get("error"))

    project = project_result.get("project", {})
    return {
        "success": True,
        "files": project.get("files_cache", []),
        "structure": project.get("structure_cache", {}),
        "total": len(project.get("files_cache", []))
    }


@router.get("/{project_id}/file/{file_path:path}")
async def get_file_content(
    project_id: str,
    file_path: str,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """دریافت محتوای یک فایل"""
    result = await connector.get_file_content(project_id, file_path)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/{project_id}/analyze")
async def analyze_external_project(
    project_id: str,
    request: AnalyzeProjectRequest,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """
    تحلیل پروژه با هوش مصنوعی

    analysis_type:
    - **overview**: بررسی کلی پروژه
    - **issues**: شناسایی مشکلات
    - **suggestions**: پیشنهادات بهبود
    """
    result = await connector.analyze_project(
        project_id=project_id,
        analysis_type=request.analysis_type
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/{project_id}/readme")
async def get_project_readme(
    project_id: str,
    connector: ExternalProjectConnector = Depends(get_connector)
):
    """دریافت README پروژه"""
    project_result = connector.get_project(project_id)
    if not project_result.get("success"):
        raise HTTPException(status_code=404, detail=project_result.get("error"))

    project = project_result.get("project", {})
    readme = project.get("readme_content")

    if not readme:
        raise HTTPException(status_code=404, detail="README یافت نشد")

    return {
        "success": True,
        "content": readme,
        "project_name": project.get("name")
    }
