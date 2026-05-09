"""
Oversight API
=============
API routes برای مرکز نظارت و مدیریت پروژه‌های گیت‌هاب.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from ...services.oversight_service import get_oversight_service

router = APIRouter(prefix="/oversight", tags=["Oversight"])


# ============================================================
# Pydantic models
# ============================================================

class WatchedCreate(BaseModel):
    repo_full_name: str
    repo_url: Optional[str] = None
    private: bool = False
    default_branch: str = "main"
    language: str = ""
    user_notes: str = ""
    tags: List[str] = Field(default_factory=list)
    schedule_enabled: bool = False
    interval_hours: float = 24.0
    autonomy_level: str = "manual"
    allow_push: bool = False


class WatchedUpdate(BaseModel):
    user_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    schedule_enabled: Optional[bool] = None
    interval_hours: Optional[float] = None
    autonomy_level: Optional[str] = None
    allow_push: Optional[bool] = None
    allow_create_issue: Optional[bool] = None
    scan_interval_hours: Optional[float] = None


class IdeaToPromptRequest(BaseModel):
    idea: str
    watched_id: Optional[str] = None
    type: str = "other"
    priority: str = "medium"
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None


class TaskCreate(BaseModel):
    watched_id: Optional[str] = None
    project_full_name: Optional[str] = ""
    title: str
    prompt: str
    raw_idea: str = ""
    type: str = "other"
    priority: str = "medium"
    status: str = "pending"
    deadline: Optional[str] = None
    source: str = "user"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[str] = None
    last_summary: Optional[str] = None
    next_run_at: Optional[str] = None


class RunTaskRequest(BaseModel):
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None


class ScanRequest(BaseModel):
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None


class WatchedUpdateExtra(BaseModel):
    """فقط برای پشتیبانی از فیلدهای جدید (allow_create_issue, scan_interval_hours)"""
    pass


class SettingsUpdate(BaseModel):
    default_models: Optional[List[str]] = None
    allow_auto_push_global: Optional[bool] = None
    max_parallel_runs: Optional[int] = None
    scan_interval_hours: Optional[float] = None


# ============================================================
# Status & Settings
# ============================================================

@router.get("/status")
async def get_status():
    """خلاصه وضعیت سیستم نظارت."""
    service = get_oversight_service()
    return await service.status_summary()


@router.get("/settings")
async def get_settings():
    service = get_oversight_service()
    return await service.get_settings()


@router.put("/settings")
async def update_settings(payload: SettingsUpdate):
    service = get_oversight_service()
    updates = payload.model_dump(exclude_none=True)
    return await service.update_settings(updates)


# ============================================================
# GitHub Repos
# ============================================================

@router.get("/repos")
async def list_user_repos(max_pages: int = Query(default=5, ge=1, le=20)):
    """لیست تمام مخازن گیت‌هاب کاربر (با paging)."""
    service = get_oversight_service()
    return await service.list_user_repos(max_pages=max_pages)


# ============================================================
# Watched Projects
# ============================================================

@router.get("/watched")
async def list_watched():
    service = get_oversight_service()
    return {"items": await service.list_watched()}


@router.post("/watched")
async def add_watched(payload: WatchedCreate):
    service = get_oversight_service()
    try:
        result = await service.add_watched(payload.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/watched/{watched_id}")
async def update_watched(watched_id: str, payload: WatchedUpdate):
    service = get_oversight_service()
    updates = payload.model_dump(exclude_none=True)
    result = await service.update_watched(watched_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")
    return result


@router.delete("/watched/{watched_id}")
async def delete_watched(watched_id: str):
    service = get_oversight_service()
    ok = await service.delete_watched(watched_id)
    if not ok:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")
    return {"success": True}


# ============================================================
# Tasks
# ============================================================

@router.get("/tasks")
async def list_tasks(
    watched_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
):
    service = get_oversight_service()
    return {
        "items": await service.list_tasks(
            watched_id=watched_id, status=status, priority=priority
        )
    }


@router.get("/tasks/by-project/{project_full_name:path}")
async def list_tasks_by_project(project_full_name: str):
    """لیست تسک‌های یک پروژه بر اساس full_name (برای اتصال به سایر صفحات)."""
    service = get_oversight_service()
    return {"items": await service.list_tasks_by_project(project_full_name)}


@router.post("/tasks")
async def create_task(payload: TaskCreate):
    service = get_oversight_service()
    try:
        return await service.create_task(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/from-idea")
async def task_from_idea(payload: IdeaToPromptRequest):
    """تبدیل ایدهٔ خام به پرامپت قدرتمند (پیش‌نمایش، ذخیره نمی‌شود)."""
    service = get_oversight_service()
    try:
        return await service.idea_to_prompt(
            idea=payload.idea,
            watched_id=payload.watched_id,
            type_=payload.type,
            priority=payload.priority,
            model_id=payload.model_id,
            model_ids=payload.model_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate):
    service = get_oversight_service()
    updates = payload.model_dump(exclude_none=True)
    result = await service.update_task(task_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return result


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    service = get_oversight_service()
    ok = await service.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return {"success": True}


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str, payload: Optional[RunTaskRequest] = None):
    """اجرای فوری یک تسک."""
    service = get_oversight_service()
    try:
        result = await service.run_task(
            task_id,
            model_id=payload.model_id if payload else None,
            model_ids=payload.model_ids if payload else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watched/{watched_id}/run-now")
async def run_all_pending(watched_id: str, payload: Optional[RunTaskRequest] = None):
    """اجرای فوری همه‌ی تسک‌های pending یک پروژه (برای دکمهٔ «بررسی فوری»)."""
    service = get_oversight_service()
    try:
        return await service.run_all_pending_for_watched(
            watched_id, model_id=payload.model_id if payload else None
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BulkApproveRequest(BaseModel):
    task_ids: List[str]


@router.post("/tasks/bulk-approve")
async def bulk_approve(payload: BulkApproveRequest):
    """تأیید گروهی تسک‌های suggested (تبدیل به pending)."""
    service = get_oversight_service()
    updated = []
    for tid in payload.task_ids:
        result = await service.update_task(tid, {"status": "pending"})
        if result:
            updated.append(result)
    return {"success": True, "updated_count": len(updated), "tasks": updated}


# ============================================================
# Reports
# ============================================================

@router.get("/reports")
async def list_reports(
    task_id: Optional[str] = None,
    watched_id: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    flagged: Optional[bool] = None,
    read: Optional[bool] = None,
    limit: int = Query(default=100, le=500),
):
    service = get_oversight_service()
    items = await service.list_reports(
        task_id=task_id, watched_id=watched_id, limit=500
    )

    # فیلترهای پیشرفته
    def _ok(r: dict) -> bool:
        if status and r.get("status") != status:
            return False
        if flagged is not None and bool(r.get("flagged")) != flagged:
            return False
        if read is not None and bool(r.get("read")) != read:
            return False
        run_at = r.get("run_at") or ""
        if since and run_at < since:
            return False
        if until and run_at > until:
            return False
        return True

    items = [r for r in items if _ok(r)]
    return {"items": items[:limit], "total": len(items)}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """جزئیات یک گزارش."""
    service = get_oversight_service()
    r = await service.get_report(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    return r


@router.patch("/reports/{report_id}/mark")
async def mark_report(
    report_id: str, read: Optional[bool] = None, flagged: Optional[bool] = None
):
    service = get_oversight_service()
    result = await service.mark_report(report_id, read=read, flagged=flagged)
    if not result:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    return result


# ============================================================
# Auto-scan
# ============================================================

@router.post("/scan/{watched_id}")
async def scan_project(watched_id: str, payload: Optional[ScanRequest] = None):
    """اسکن خودکار پروژه برای یافتن نیازها/ایرادات."""
    service = get_oversight_service()
    try:
        # اگر model_ids ارائه شده فقط model_id اول را به scan می‌فرستیم (scan فعلاً single-model است)
        chosen_model = None
        if payload:
            chosen_model = payload.model_id or (
                payload.model_ids[0] if payload.model_ids else None
            )
        return await service.scan_project(watched_id, model_id=chosen_model)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Manual scheduler tick (for testing)
# ============================================================

@router.post("/scheduler/tick")
async def manual_tick():
    """اجرای دستی یک نوبت scheduler (مفید برای تست)."""
    service = get_oversight_service()
    return await service.scheduler_tick()
