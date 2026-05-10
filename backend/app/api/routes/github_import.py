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

        # 🆕 (Creator) auto-register به watched
        try:
            from ...services.oversight_service import get_oversight_service
            oversight = get_oversight_service()
            repo_full_name = result.get("full_name") or result.get("repo_full_name")
            if not repo_full_name:
                owner = result.get("owner") or ""
                name = result.get("name") or ""
                if owner and name:
                    repo_full_name = f"{owner}/{name}"
            if repo_full_name and "/" in repo_full_name:
                auto_w = await oversight.auto_register_watched(
                    repo_full_name,
                    source="github_import",
                    repo_url=result.get("url") or result.get("html_url", ""),
                    default_branch=result.get("default_branch", "main"),
                    language=result.get("language", ""),
                    private=bool(result.get("private", False)),
                    user_notes=(result.get("description") or "")[:300],
                )
                result["auto_watched"] = auto_w
        except Exception as e:
            result["auto_watched"] = {"success": False, "error": str(e)}

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


# ===========================================
# Pull Request Endpoints
# ===========================================

class CreatePRRequest(BaseModel):
    """درخواست ایجاد Pull Request"""
    github_path: str  # owner/repo یا full URL
    branch_name: str
    title: str
    description: str
    files: List[dict]  # [{path: str, content: str}]
    token: Optional[str] = None
    use_global_token: bool = True


class PushIssuesRequest(BaseModel):
    """درخواست push ایرادات به GitHub Issues"""
    github_path: str
    issues: List[dict]  # لیست ایرادات
    token: Optional[str] = None
    use_global_token: bool = True


@router.post("/pr/create")
async def create_pull_request(request: CreatePRRequest):
    """
    ایجاد Pull Request با تغییرات

    1. ایجاد branch جدید
    2. Commit فایل‌ها
    3. ایجاد PR
    """
    from ...services.github_pr_service import get_github_pr_service

    slog.api_request("POST", "/github/pr/create", branch=request.branch_name)

    token = get_effective_token(request.token, request.use_global_token)
    if not token:
        return {
            "success": False,
            "error": "توکن GitHub مورد نیاز است"
        }

    service = get_github_pr_service()
    result = await service.create_pr_with_changes(
        github_path=request.github_path,
        branch_name=request.branch_name,
        title=request.title,
        description=request.description,
        files=request.files,
        token=token
    )

    return result


@router.post("/issues/push")
async def push_issues_to_github(request: PushIssuesRequest):
    """
    Push ایرادات محلی به GitHub Issues

    هر ایراد یک Issue جدید در GitHub ایجاد می‌کند
    """
    from ...services.github_pr_service import get_github_pr_service

    slog.api_request("POST", "/github/issues/push",
        issues_count=len(request.issues)
    )

    token = get_effective_token(request.token, request.use_global_token)
    if not token:
        return {
            "success": False,
            "error": "توکن GitHub مورد نیاز است"
        }

    service = get_github_pr_service()
    result = await service.push_issues_to_github(
        github_path=request.github_path,
        issues=request.issues,
        token=token
    )

    return result


@router.get("/issues/{owner}/{repo}")
async def get_github_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: Optional[str] = None,
    use_global_token: bool = True
):
    """
    دریافت Issues یک repository
    """
    from ...services.github_pr_service import get_github_pr_service

    token = get_effective_token(None, use_global_token)

    service = get_github_pr_service()
    result = await service.get_repo_issues(
        owner=owner,
        repo=repo,
        state=state,
        labels=labels,
        token=token if token else None
    )

    return result


@router.post("/pr/from-project/{project_id}")
async def create_pr_from_project(
    project_id: str,
    branch_name: str,
    title: str,
    description: str,
    file_paths: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    ایجاد PR از فایل‌های پروژه

    اگر file_paths مشخص نشده، همه فایل‌های پروژه را شامل می‌شود
    """
    from ...services.github_pr_service import get_github_pr_service

    slog.api_request("POST", f"/github/pr/from-project/{project_id}")

    # دریافت پروژه
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    if not project.github_path:
        return {"success": False, "error": "پروژه GitHub path ندارد"}

    # دریافت فایل‌ها
    query = db.query(ProjectFile).filter(ProjectFile.project_id == project_id)
    if file_paths:
        query = query.filter(ProjectFile.file_path.in_(file_paths))

    files = query.all()
    if not files:
        return {"success": False, "error": "فایلی یافت نشد"}

    # آماده‌سازی فایل‌ها
    files_data = [
        {"path": f.file_path, "content": f.content or ""}
        for f in files
        if f.content
    ]

    token = get_effective_token(None, True)
    if not token:
        return {"success": False, "error": "توکن GitHub تنظیم نشده"}

    service = get_github_pr_service()
    result = await service.create_pr_with_changes(
        github_path=project.github_path,
        branch_name=branch_name,
        title=title,
        description=description,
        files=files_data,
        token=token
    )

    return result


@router.post("/issues/from-project/{project_id}")
async def push_project_issues_to_github(
    project_id: str,
    issue_ids: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    Push ایرادات پروژه به GitHub Issues

    اگر issue_ids مشخص نشده، همه ایرادات را push می‌کند
    """
    from ...services.github_pr_service import get_github_pr_service
    import json

    slog.api_request("POST", f"/github/issues/from-project/{project_id}")

    # دریافت پروژه
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"success": False, "error": "پروژه یافت نشد"}

    if not project.github_path:
        return {"success": False, "error": "پروژه GitHub path ندارد"}

    # دریافت ایرادات
    issues = []
    if project.issues_found:
        try:
            all_issues = json.loads(project.issues_found)
            if issue_ids:
                issues = [i for i in all_issues if i.get("id") in issue_ids]
            else:
                issues = all_issues
        except json.JSONDecodeError:
            return {"success": False, "error": "فرمت ایرادات نامعتبر"}

    if not issues:
        return {"success": False, "error": "ایرادی یافت نشد"}

    token = get_effective_token(None, True)
    if not token:
        return {"success": False, "error": "توکن GitHub تنظیم نشده"}

    service = get_github_pr_service()
    result = await service.push_issues_to_github(
        github_path=project.github_path,
        issues=issues,
        token=token
    )

    # به‌روزرسانی ایرادات با شناسه GitHub
    if result.get("success") and result.get("issues"):
        try:
            all_issues = json.loads(project.issues_found)
            github_map = {i["local_id"]: i for i in result.get("issues", [])}

            for issue in all_issues:
                if issue.get("id") in github_map:
                    issue["github_issue_number"] = github_map[issue["id"]].get("github_issue")
                    issue["github_issue_url"] = github_map[issue["id"]].get("url")
                    issue["pushed_to_github"] = True
                    issue["pushed_at"] = datetime.utcnow().isoformat()

            project.issues_found = json.dumps(all_issues, ensure_ascii=False)
            db.commit()
        except Exception as e:
            slog.warning("Failed to update issues with GitHub info", exception=e)

    return result


from datetime import datetime
