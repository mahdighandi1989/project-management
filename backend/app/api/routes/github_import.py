"""
API routes برای import پروژه از GitHub
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.github_import import get_github_import_service
from ...models.project import Project, ProjectFile
from ...core.logging_utils import StructuredLogger

router = APIRouter(prefix="/github", tags=["GitHub Import"])
slog = StructuredLogger("github_import")


# ===========================================
# Request/Response Models
# ===========================================

class CheckRepoRequest(BaseModel):
    """درخواست بررسی دسترسی به repo"""
    url: str
    token: Optional[str] = None
    use_global_token: bool = False  # استفاده از توکن ذخیره شده


class ImportRepoRequest(BaseModel):
    """درخواست import یک repository"""
    url: str
    token: Optional[str] = None
    use_global_token: bool = False  # استفاده از توکن ذخیره شده
    include_files: bool = True
    max_file_size: int = 500000  # 500KB
    excluded_dirs: Optional[List[str]] = None
    excluded_extensions: Optional[List[str]] = None


# ===========================================
# Endpoints
# ===========================================

def get_effective_token(provided_token: str = None, use_global: bool = False) -> str:
    """دریافت توکن مناسب - سراسری یا ارسال شده"""
    import os
    if provided_token:
        return provided_token
    if use_global:
        return os.environ.get("GITHUB_TOKEN", "")
    return ""


@router.post("/check")
async def check_repository(request: CheckRepoRequest):
    """
    بررسی دسترسی به یک repository
    برای چک کردن قبل از import
    """
    service = get_github_import_service()

    # پارس URL
    parsed = service.parse_github_url(request.url)
    if not parsed.get("owner") or not parsed.get("repo"):
        return {
            "success": False,
            "error": "URL نامعتبر است",
            "hint": "فرمت صحیح: https://github.com/owner/repo یا owner/repo"
        }

    # دریافت توکن مناسب
    token = get_effective_token(request.token, request.use_global_token)

    # بررسی دسترسی
    result = await service.check_repo_access(
        parsed["owner"],
        parsed["repo"],
        token if token else None
    )

    # اگر موفق بود، زبان‌ها رو هم بگیر
    if result.get("success"):
        languages = await service.get_repo_languages(
            parsed["owner"],
            parsed["repo"],
            token if token else None
        )
        result["languages"] = languages

    return result


@router.post("/import")
async def import_repository(request: ImportRepoRequest):
    """
    Import کامل یک repository از GitHub

    - پشتیبانی از repo های public و private
    - برای private repos، توکن GitHub لازم است
    - فایل‌های بزرگ و باینری فیلتر می‌شوند
    """
    service = get_github_import_service()

    # دریافت توکن مناسب
    token = get_effective_token(request.token, request.use_global_token)

    # انجام import
    result = await service.import_repository(
        url_or_path=request.url,
        token=token if token else None,
        include_files=request.include_files,
        max_file_size=request.max_file_size,
        excluded_dirs=request.excluded_dirs,
        excluded_extensions=request.excluded_extensions,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "خطا در import"))

    # ذخیره در دیتابیس
    save_result = await service.save_imported_project(result)

    if not save_result.get("success"):
        # حتی اگه ذخیره نشد، نتیجه import رو برگردون
        result["save_error"] = save_result.get("error")
        result["saved"] = False
    else:
        result["saved"] = True
        result["db_project_id"] = save_result.get("project_id")

        # 🆕 راه‌اندازی خودکار حافظه و فیلدهای پویا
        try:
            from ...services.project_auto_setup import auto_setup_project_memory
            from ...core.database import SessionLocal

            db_session = SessionLocal()
            try:
                auto_result = await auto_setup_project_memory(
                    project_id=save_result["project_id"],
                    project_name=result.get("name", "پروژه"),
                    project_description=result.get("description", ""),
                    project_type="github_import",
                    files=result.get("files", []),
                    use_ai=True,
                    db_session=db_session
                )
                result["auto_setup"] = {
                    "success": auto_result.get("success", False),
                    "detected_type": auto_result.get("detected_type"),
                    "ai_insights": auto_result.get("ai_insights"),
                    "fields_created": len(auto_result.get("dynamic_fields", []))
                }
            finally:
                db_session.close()
        except Exception as e:
            result["auto_setup"] = {"success": False, "error": str(e)}

    return result


@router.get("/imported")
async def list_imported_projects(db: Session = Depends(get_db)):
    """
    لیست پروژه‌های import شده از GitHub
    """
    slog.api_request("GET", "/github/imported")
    try:
        projects = db.query(Project).filter(
            Project.project_type == "github_import"
        ).order_by(Project.created_at.desc()).all()

        slog.info("Listed imported projects", count=len(projects))
        return {
            "success": True,
            "projects": [p.to_dict() for p in projects],
            "count": len(projects)
        }
    except Exception as e:
        slog.error("Failed to list imported projects", exception=e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/imported/{project_id}")
async def get_imported_project(project_id: str, db: Session = Depends(get_db)):
    """
    دریافت جزئیات یک پروژه import شده
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        # دریافت فایل‌ها
        files = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id
        ).all()

        result = project.to_dict()
        result["files"] = [
            {
                "path": f.file_path,
                "type": f.file_type,
                "size": f.size,
                "github_url": f.github_url,
            }
            for f in files
        ]
        result["file_count"] = len(files)

        return {"success": True, "project": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/imported/{project_id}/file")
async def get_project_file(
    project_id: str,
    path: str,
    db: Session = Depends(get_db)
):
    """
    دریافت محتوای یک فایل از پروژه import شده
    """
    try:
        file = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_path == path
        ).first()

        if not file:
            raise HTTPException(status_code=404, detail="فایل یافت نشد")

        return {
            "success": True,
            "path": file.file_path,
            "content": file.content,
            "size": file.size,
            "type": file.file_type,
            "github_url": file.github_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imported/{project_id}/refresh")
async def refresh_imported_project(
    project_id: str,
    token: Optional[str] = None,
    use_global_token: bool = True,
    db: Session = Depends(get_db)
):
    """
    بروزرسانی پروژه از GitHub
    آخرین تغییرات را دریافت می‌کند
    """
    import os

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        import json
        metadata = json.loads(project.extra_data) if project.extra_data else {}

        if metadata.get("source") != "github":
            raise HTTPException(status_code=400, detail="این پروژه از GitHub نیست")

        owner = metadata.get("owner")
        repo = metadata.get("repo")

        if not owner or not repo:
            raise HTTPException(status_code=400, detail="اطلاعات GitHub ناقص است")

        # دریافت توکن مناسب
        effective_token = token
        if not effective_token and use_global_token:
            effective_token = os.environ.get("GITHUB_TOKEN", "")

        # Re-import
        service = get_github_import_service()
        result = await service.import_repository(
            url_or_path=f"{owner}/{repo}",
            token=effective_token if effective_token else None,
            include_files=True,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        # ذخیره
        save_result = await service.save_imported_project(result)

        return {
            "success": True,
            "message": "پروژه بروزرسانی شد",
            "files_updated": len(result.get("files", [])),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/imported/{project_id}")
async def delete_imported_project(project_id: str, db: Session = Depends(get_db)):
    """
    حذف پروژه import شده
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        # حذف داده‌های مرتبط با ژورنال
        try:
            from .project_journal import ActivityLog, Report, ReportTrigger
            db.query(ActivityLog).filter(ActivityLog.project_id == project_id).delete()
            db.query(Report).filter(Report.project_id == project_id).delete()
            db.query(ReportTrigger).filter(ReportTrigger.project_id == project_id).delete()
        except Exception:
            pass  # جداول ممکنه هنوز وجود نداشته باشند

        # حذف فایل‌ها
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).delete()

        # حذف پروژه
        db.delete(project)
        db.commit()

        return {"success": True, "message": "پروژه حذف شد"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-url")
async def parse_github_url(url: str):
    """
    پارس URL گیت‌هاب و استخراج owner/repo
    """
    service = get_github_import_service()
    parsed = service.parse_github_url(url)

    if not parsed.get("owner") or not parsed.get("repo"):
        return {
            "success": False,
            "error": "URL نامعتبر",
            "supported_formats": [
                "https://github.com/owner/repo",
                "https://github.com/owner/repo.git",
                "git@github.com:owner/repo.git",
                "owner/repo"
            ]
        }

    return {
        "success": True,
        "owner": parsed["owner"],
        "repo": parsed["repo"],
        "full_name": f"{parsed['owner']}/{parsed['repo']}",
        "url": f"https://github.com/{parsed['owner']}/{parsed['repo']}"
    }
