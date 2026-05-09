"""
Oversight API
=============
API routes برای مرکز نظارت و مدیریت پروژه‌های گیت‌هاب.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ...services.oversight_service import get_oversight_service
from ...core.database import get_db

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
async def list_user_repos(
    max_pages: int = Query(default=5, ge=1, le=20),
    refresh: bool = Query(default=False),
):
    """لیست تمام مخازن گیت‌هاب کاربر (با cache 6 ساعته). refresh=true → بازخوانی از GitHub."""
    service = get_oversight_service()
    return await service.list_user_repos(max_pages=max_pages, force_refresh=refresh)


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


@router.get("/summary/by-project/{project_full_name:path}")
async def oversight_summary_by_project(project_full_name: str):
    """خلاصهٔ سبک تسک‌ها برای استفاده در /projects (count به تفکیک وضعیت)."""
    service = get_oversight_service()
    items = await service.list_tasks_by_project(project_full_name)
    counts: Dict[str, int] = {}
    for t in items:
        s = t.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    return {
        "project_full_name": project_full_name,
        "total": len(items),
        "by_status": counts,
        "pending": counts.get("pending", 0) + counts.get("suggested", 0),
        "in_review": counts.get("awaiting_review", 0),
        "done": counts.get("done", 0),
    }


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


@router.post("/tasks/{task_id}/verify-now")
async def verify_task_now(task_id: str, payload: Optional[RunTaskRequest] = None):
    """اجرای فوری verifier روی یک تسک — مستقل از execution."""
    from ...services.oversight_verifier import verify_task as _verify_task

    try:
        return await _verify_task(
            task_id,
            model_id=payload.model_id if payload else None,
            triggered_by="manual",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/mark-applied-externally")
async def mark_applied_externally(task_id: str):
    """کاربر صریحاً می‌گوید این تسک را بیرون از سیستم اعمال کردم."""
    service = get_oversight_service()
    async with service._lock:
        for t in service.tasks:
            if t.id == task_id:
                t.manually_marked_applied_at = (
                    __import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    ).isoformat()
                )
                t.verification_status = "applied_externally_pending_verify"
                t.updated_at = t.manually_marked_applied_at
                service._save_tasks()
                return t.to_dict()
    raise HTTPException(status_code=404, detail="تسک یافت نشد")


@router.get("/tasks/{task_id}/full-prompt")
async def get_full_prompt(task_id: str):
    """برمی‌گرداند پرامپت کامل تسک — برای کپی به ابزار خارجی."""
    service = get_oversight_service()
    for t in service.tasks:
        if t.id == task_id:
            return {
                "task_id": t.id,
                "title": t.title,
                "prompt": t.prompt,
                "target_files": t.target_files,
                "acceptance_criteria": t.acceptance_criteria,
                "type": t.type,
                "priority": t.priority,
                "execution_mode": t.execution_mode,
                "project_full_name": t.project_full_name,
            }
    raise HTTPException(status_code=404, detail="تسک یافت نشد")


@router.get("/tasks/{task_id}/verification-history")
async def get_verification_history(task_id: str):
    """تاریخچهٔ verification یک تسک."""
    service = get_oversight_service()
    for t in service.tasks:
        if t.id == task_id:
            return {
                "task_id": t.id,
                "verification_status": t.verification_status,
                "confirmation_streak": t.confirmation_streak,
                "manually_marked_applied_at": t.manually_marked_applied_at,
                "last_verified_at": t.last_verified_at,
                "history": t.verification_history,
            }
    raise HTTPException(status_code=404, detail="تسک یافت نشد")


# ============================================================
# 🚀 Inspector apply-action bridge — حلقهٔ اتصال OversightTask به مسیر
# اجرای واقعی روی پروژهٔ محلی
# ============================================================

class RecordExecutionRequest(BaseModel):
    pr_url: str
    pr_branch: Optional[str] = ""
    files_committed: Optional[List[str]] = []
    model_ids: Optional[List[str]] = []
    action_plan_summary: Optional[str] = ""
    executed_via: Optional[str] = "inspector_apply_action"


@router.get("/tasks/{task_id}/resolve-project")
async def resolve_project_for_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
):
    """نگاشت OversightTask → Project محلی (DB) برای فاز preflight اجرا.

    قبل از فراخوانی smart-chat / apply-action (که project_id محلی می‌خواهند)،
    UI این endpoint را call می‌کند تا از تطابق مطمئن شود و در صورت نبود،
    راهنمایی فارسی به کاربر بدهد.
    """
    service = get_oversight_service()
    # check task existence ابتدا (resolve خودش هم چک می‌کند ولی برای 404 صریح‌تر)
    task = next((t for t in service.tasks if t.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return service.resolve_project_for_task(db, task_id)


@router.post("/tasks/{task_id}/record-execution")
async def record_task_execution_endpoint(
    task_id: str,
    payload: RecordExecutionRequest,
):
    """ثبت اجرای موفق یک تسک از طریق Inspector apply-action.

    این endpoint بعد از موفقیت apply-action (که PR ساخته شد) از فرانت‌اند
    صدا زده می‌شود تا applied_evidence و verification_history به‌روز شوند.
    """
    service = get_oversight_service()
    if not payload.pr_url and not payload.pr_branch:
        raise HTTPException(
            status_code=400,
            detail="حداقل یکی از pr_url یا pr_branch باید پر باشد",
        )
    result = await service.record_task_execution(
        task_id,
        pr_url=payload.pr_url or "",
        pr_branch=payload.pr_branch or "",
        files_committed=payload.files_committed or [],
        model_ids=payload.model_ids or [],
        action_plan_summary=payload.action_plan_summary or "",
        executed_via=payload.executed_via or "inspector_apply_action",
    )
    if result is None:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return result


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
    """اسکن سریع پروژه برای یافتن نیازها/ایرادات (حالت سادهٔ قبلی)."""
    service = get_oversight_service()
    try:
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


class DeepScanRequest(BaseModel):
    model_id: Optional[str] = None
    enabled_passes: Optional[List[str]] = None
    deep_read_count: int = 35


@router.post("/scan/{watched_id}/deep")
async def deep_scan_project(watched_id: str, payload: Optional[DeepScanRequest] = None):
    """اجرای deep scan در پس‌زمینه. progress قابل polling از /scan/{id}/progress است."""
    import asyncio as _aio
    from ...services.oversight_deep_scan_service import run_deep_scan, write_progress

    payload = payload or DeepScanRequest()

    # ست کردن وضعیت اولیه
    write_progress(watched_id, status="queued", phase="queued", message="در انتظار شروع")

    async def _bg():
        try:
            await run_deep_scan(
                watched_id,
                model_id=payload.model_id,
                enabled_passes=payload.enabled_passes,
                deep_read_count=payload.deep_read_count,
            )
        except Exception as e:
            from ...services.oversight_deep_scan_service import write_progress as _wp
            _wp(watched_id, status="error", message=str(e))

    _aio.create_task(_bg())
    return {"success": True, "status": "queued", "watched_id": watched_id}


@router.get("/scan/{watched_id}/progress")
async def scan_progress(watched_id: str):
    """خواندن progress جاری deep scan (برای polling از UI)."""
    from ...services.oversight_deep_scan_service import read_progress

    return read_progress(watched_id)


@router.get("/scan/{watched_id}/summaries")
async def scan_summaries(watched_id: str):
    """خواندن خلاصه‌های ساختاریافته از آخرین deep scan.

    شامل: security_summary (از Pass I) + coverage_summary (از Pass J — بعداً)
    + هر summary ساختاریافته دیگری که passes تخصصی تولید کرده‌اند.

    این endpoint برای UI تب «🏥 سلامت پروژه» در /oversight استفاده می‌شود
    تا metrics را بدون reparse کردن کل findings نمایش دهد.
    """
    from ...services.oversight_deep_scan_service import SCAN_RESULTS_DIR
    from ...services.oversight_service import _read_json

    data = _read_json(SCAN_RESULTS_DIR / f"{watched_id}.json", {}) or {}
    return {
        "watched_id": watched_id,
        "ran_at": data.get("ran_at", ""),
        "passes_run": data.get("passes_run", 0),
        "pass_summaries": data.get("pass_summaries", {}),
        "findings_count": len(data.get("findings") or []),
        "tasks_created_count": len(data.get("tasks_created") or []),
    }


# ============================================================
# Codex
# ============================================================

class CodexRefreshRequest(BaseModel):
    model_id: Optional[str] = None
    max_files: int = 40
    only_changed: bool = True


@router.get("/codex/{watched_id}")
async def get_codex(watched_id: str):
    """خواندن Codex (شناسنامهٔ خودکار) یک پروژه."""
    from ...services.oversight_codex_service import read_codex

    return read_codex(watched_id)


@router.post("/codex/{watched_id}/refresh")
async def refresh_codex(watched_id: str, payload: Optional[CodexRefreshRequest] = None):
    """به‌روزرسانی Codex (delta-based)."""
    from ...services.oversight_codex_service import refresh_codex as _refresh_codex

    payload = payload or CodexRefreshRequest()
    try:
        return await _refresh_codex(
            watched_id,
            model_id=payload.model_id,
            max_files=payload.max_files,
            only_changed=payload.only_changed,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🆕 Roadmap & README management (مهاجرت از Health analysis)
# ============================================================

class GenerateRoadmapRequest(BaseModel):
    model_id: Optional[str] = None
    tone: str = "professional"


class GenerateReadmeRequest(BaseModel):
    model_id: Optional[str] = None
    sections: Optional[List[str]] = None


class UpdateRoadmapRequest(BaseModel):
    """ویرایش دستی روadmap — فقط markdown یا کل ساختار."""
    roadmap_markdown: Optional[str] = None
    ideal_state: Optional[str] = None
    phases: Optional[List[Dict[str, Any]]] = None


class UpdateReadmeRequest(BaseModel):
    readme_markdown: str


@router.get("/codex/{watched_id}/roadmap")
async def get_roadmap(watched_id: str):
    """خواندن روadmap ذخیره شده. اگر تولید نشده، dict خالی."""
    from ...services.oversight_codex_service import read_roadmap
    return read_roadmap(watched_id)


@router.post("/codex/{watched_id}/generate-roadmap")
async def generate_roadmap_endpoint(watched_id: str, payload: Optional[GenerateRoadmapRequest] = None):
    """تولید روadmap با AI از structure + scan findings + user_notes."""
    from ...services.oversight_codex_service import generate_roadmap_for_watched
    payload = payload or GenerateRoadmapRequest()
    try:
        return await generate_roadmap_for_watched(
            watched_id, model_id=payload.model_id, tone=payload.tone,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/codex/{watched_id}/roadmap")
async def update_roadmap_endpoint(watched_id: str, payload: UpdateRoadmapRequest):
    """ویرایش دستی روadmap (markdown یا phases)."""
    from ...services.oversight_codex_service import read_roadmap, write_roadmap, now_iso
    data = read_roadmap(watched_id) or {"watched_id": watched_id}
    if payload.roadmap_markdown is not None:
        data["roadmap_markdown"] = payload.roadmap_markdown
    if payload.ideal_state is not None:
        data["ideal_state"] = payload.ideal_state
    if payload.phases is not None:
        data["phases"] = payload.phases
    data["updated_at"] = now_iso()
    if not data.get("generated_at"):
        data["generated_at"] = data["updated_at"]
    write_roadmap(watched_id, data)
    return data


@router.patch("/codex/{watched_id}/roadmap/items/{item_id}")
async def toggle_roadmap_item_endpoint(watched_id: str, item_id: str):
    """تاگل completed یک item. item_id فرمت 'phase_idx:item_idx'."""
    from ...services.oversight_codex_service import toggle_roadmap_item
    result = toggle_roadmap_item(watched_id, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="item یا روadmap یافت نشد")
    return result


@router.get("/codex/{watched_id}/readme")
async def get_readme(watched_id: str):
    """خواندن README ذخیره شده."""
    from ...services.oversight_codex_service import read_readme_doc
    return read_readme_doc(watched_id)


@router.post("/codex/{watched_id}/generate-readme")
async def generate_readme_endpoint(watched_id: str, payload: Optional[GenerateReadmeRequest] = None):
    """تولید README با AI."""
    from ...services.oversight_codex_service import generate_readme_for_watched
    payload = payload or GenerateReadmeRequest()
    try:
        return await generate_readme_for_watched(
            watched_id, model_id=payload.model_id, sections=payload.sections,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/codex/{watched_id}/readme")
async def update_readme_endpoint(watched_id: str, payload: UpdateReadmeRequest):
    """ویرایش دستی README."""
    from ...services.oversight_codex_service import read_readme_doc, write_readme_doc, now_iso
    data = read_readme_doc(watched_id) or {"watched_id": watched_id}
    data["readme_markdown"] = payload.readme_markdown
    data["updated_at"] = now_iso()
    if not data.get("generated_at"):
        data["generated_at"] = data["updated_at"]
    write_readme_doc(watched_id, data)
    return data


# ============================================================
# 🆕 General Archive (مهاجرت از Health analysis general_archive)
# ============================================================

@router.get("/archive")
async def list_general_archive(
    item_type: Optional[str] = Query(default=None, description="task | report"),
    project_full_name: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """آرشیو سراسری: تسک‌های done/archived + گزارش‌های قدیمی.

    این endpoint جایگزین Health analysis /general-archive است.
    به‌صورت paginated و قابل فیلتر بر اساس type و پروژه.
    """
    service = get_oversight_service()
    items: List[Dict[str, Any]] = []
    type_breakdown: Dict[str, int] = {}
    status_breakdown: Dict[str, int] = {}

    # tasks: status ∈ {done, archived, cancelled}
    if item_type in (None, "task"):
        for t in service.tasks:
            if t.status not in ("done", "archived", "cancelled"):
                continue
            if project_full_name and t.project_full_name != project_full_name:
                continue
            items.append({
                "item_type": "task",
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "type": t.type,
                "priority": t.priority,
                "project_full_name": t.project_full_name,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "merged_findings_count": len(t.merged_findings or []),
                "preview": (t.raw_idea or "")[:200],
            })
            status_breakdown[t.status] = status_breakdown.get(t.status, 0) + 1
            type_breakdown[t.type] = type_breakdown.get(t.type, 0) + 1

    # reports
    if item_type in (None, "report"):
        for r in service.reports:
            if project_full_name and r.project_full_name != project_full_name:
                continue
            items.append({
                "item_type": "report",
                "id": r.id,
                "task_id": r.task_id,
                "status": r.status,
                "project_full_name": r.project_full_name,
                "run_at": r.run_at,
                "model_id": r.model_id,
                "preview": (r.raw_response or "")[:200],
            })
            status_breakdown[r.status] = status_breakdown.get(r.status, 0) + 1
            type_breakdown["report"] = type_breakdown.get("report", 0) + 1

    # sort by date desc
    items.sort(key=lambda x: x.get("updated_at") or x.get("run_at") or "", reverse=True)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = items[start:end]

    return {
        "items": paginated,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if page_size else 1,
        "type_breakdown": type_breakdown,
        "status_breakdown": status_breakdown,
    }


@router.delete("/archive/{item_type}/{item_id}")
async def delete_archive_item(item_type: str, item_id: str):
    """حذف یک item از archive (task یا report)."""
    service = get_oversight_service()
    if item_type == "task":
        async with service._lock:
            before = len(service.tasks)
            service.tasks = [t for t in service.tasks if t.id != item_id]
            if len(service.tasks) == before:
                raise HTTPException(status_code=404, detail="task یافت نشد")
            service._save_tasks()
        return {"success": True, "deleted": "task", "id": item_id}
    elif item_type == "report":
        async with service._lock:
            before = len(service.reports)
            service.reports = [r for r in service.reports if r.id != item_id]
            if len(service.reports) == before:
                raise HTTPException(status_code=404, detail="report یافت نشد")
            service._save_reports()
        return {"success": True, "deleted": "report", "id": item_id}
    else:
        raise HTTPException(status_code=400, detail="item_type باید 'task' یا 'report' باشد")


# ============================================================
# 🔗 External Project Tasks Bridge — wiring /projects ↔ /oversight
# ============================================================
# هدف: dynamic_fields از پروژه‌های local که action_type='github_commit' دارند
# را در /oversight به‌عنوان «تسک قابل verify» نمایش دهیم — بدون ذخیرهٔ
# duplicate. این API فقط READ + verify-now است.

@router.get("/external-tasks")
async def list_external_project_tasks(
    project_id: Optional[str] = Query(default=None, description="فیلتر بر اساس project_id خاص"),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """لیست dynamic_fields از پروژه‌های local که قابلیت اجرا/verify دارند.

    این endpoint برای نمایش در تب جدید «تسک‌های پروژه‌ها» در صفحهٔ /oversight
    استفاده می‌شود.
    """
    service = get_oversight_service()
    items = service.list_external_project_tasks(
        db_session=db,
        project_id_filter=project_id,
        include_archived=include_archived,
    )
    return {"items": items, "total": len(items)}


@router.get("/external-tasks/summary")
async def external_project_tasks_summary(
    db: Session = Depends(get_db),
):
    """خلاصهٔ تعداد تسک‌های external به تفکیک پروژه — برای indicator سراسری."""
    service = get_oversight_service()
    items = service.list_external_project_tasks(db_session=db)
    by_project: Dict[str, Dict[str, Any]] = {}
    for it in items:
        pid = it.get("origin_project_id", "")
        if pid not in by_project:
            by_project[pid] = {
                "project_id": pid,
                "project_name": it.get("origin_project_name", ""),
                "total": 0,
                "pending": 0,
                "archived": 0,
            }
        by_project[pid]["total"] += 1
        if it.get("status") == "archived":
            by_project[pid]["archived"] += 1
        else:
            by_project[pid]["pending"] += 1
    return {
        "total": len(items),
        "by_project": list(by_project.values()),
    }


@router.post("/external-tasks/{project_id}/{field_id}/verify-now")
async def verify_external_project_field(
    project_id: str,
    field_id: str,
    payload: Optional[RunTaskRequest] = None,
    db: Session = Depends(get_db),
):
    """verify فوری یک dynamic_field از /projects با همان موتور verifier.

    بدون اهمیت دادن به اینکه چه کسی فیلد را اعمال کرده (AI، کاربر، ابزار خارجی)،
    وضعیت فعلی repo را با acceptance criteria مقایسه می‌کند.
    """
    service = get_oversight_service()
    try:
        return await service.verify_external_project_field(
            db_session=db,
            project_id=project_id,
            field_id=field_id,
            model_id=payload.model_id if payload else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Manual scheduler tick (for testing)
# ============================================================

@router.post("/scheduler/tick")
async def manual_tick():
    """اجرای دستی یک نوبت scheduler (مفید برای تست)."""
    service = get_oversight_service()
    return await service.scheduler_tick()


# ============================================================
# Bridge router → /api/projects/{project_id}/...
# اتصال صفحهٔ /projects به سیستم Oversight (بخش ۷.۳ و ۱۱.۳ اسپک)
# ============================================================

projects_bridge_router = APIRouter(prefix="/projects", tags=["Oversight Bridge"])


class ApplyOversightTaskRequest(BaseModel):
    task_id: str
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None


def _resolve_project_full_name(project_id: str) -> str:
    """project_id از /projects page ممکن است full_name (owner/repo) یا UUID محلی باشد.
    اگر '/' داشته باشد، همان full_name است. در غیر این صورت تلاش می‌کنیم از simple_creator
    آن را پیدا کنیم؛ و اگر نشد، خود project_id را برمی‌گردانیم تا lookup در tasks fallback شود.
    """
    if "/" in project_id:
        return project_id
    try:
        from ...services.simple_creator import SimpleProjectCreator  # type: ignore
        # best-effort lookup; if not available, just return as-is
        creator = SimpleProjectCreator()
        proj = creator.get_project(project_id)
        if proj and getattr(proj, "name", None):
            # simple projects don't store full_name, fall back to id
            return project_id
    except Exception:
        pass
    return project_id


@projects_bridge_router.get("/{project_id:path}/oversight-summary")
async def project_oversight_summary(project_id: str):
    """خلاصهٔ تسک‌های نظارت برای پروژه‌ای که در صفحهٔ /projects نمایش داده می‌شود.

    project_id می‌تواند full_name (مثل owner/repo) یا id محلی باشد.
    در صورت full_name، مستقیماً tasks مرتبط برمی‌گردند؛ در غیر این صورت لیست خالی.
    """
    service = get_oversight_service()
    full_name = _resolve_project_full_name(project_id)
    items = await service.list_tasks_by_project(full_name)
    counts: Dict[str, int] = {}
    for t in items:
        s = t.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    return {
        "project_id": project_id,
        "project_full_name": full_name,
        "total": len(items),
        "by_status": counts,
        "pending": counts.get("pending", 0) + counts.get("suggested", 0),
        "in_review": counts.get("awaiting_review", 0),
        "done": counts.get("done", 0),
        "items": items,
    }


@projects_bridge_router.post("/{project_id:path}/apply-oversight-task")
async def apply_oversight_task(project_id: str, payload: ApplyOversightTaskRequest):
    """اعمال یک تسک نظارت روی یک پروژه (مسیر A — متصل).

    این endpoint thin-wrapper روی `service.run_task` است؛ پرامپت را به مدل کدنویس می‌دهد
    و طبق `auto_create_pr_instead_of_commit` و `allow_push` تصمیم می‌گیرد PR بسازد یا commit مستقیم.
    """
    service = get_oversight_service()
    # validate task exists and (if possible) belongs to this project
    target_full_name = _resolve_project_full_name(project_id)
    found = None
    for t in service.tasks:
        if t.id == payload.task_id:
            found = t
            break
    if not found:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    # soft-validate project association (don't hard-fail if simple-project id is opaque)
    if "/" in target_full_name and found.project_full_name and found.project_full_name != target_full_name:
        raise HTTPException(
            status_code=400,
            detail=f"این تسک به پروژهٔ '{found.project_full_name}' تعلق دارد، نه '{target_full_name}'",
        )
    try:
        result = await service.run_task(
            payload.task_id,
            model_id=payload.model_id,
            model_ids=payload.model_ids,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@projects_bridge_router.post("/{project_id:path}/verify-task/{task_id}")
async def verify_project_task(project_id: str, task_id: str, payload: Optional[RunTaskRequest] = None):
    """verify فوری یک تسک از طریق مسیر /projects — مستقل از execution path."""
    from ...services.oversight_verifier import verify_task as _verify_task

    service = get_oversight_service()
    target_full_name = _resolve_project_full_name(project_id)
    found = None
    for t in service.tasks:
        if t.id == task_id:
            found = t
            break
    if not found:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    if "/" in target_full_name and found.project_full_name and found.project_full_name != target_full_name:
        raise HTTPException(
            status_code=400,
            detail=f"این تسک به پروژهٔ '{found.project_full_name}' تعلق دارد، نه '{target_full_name}'",
        )
    try:
        return await _verify_task(
            task_id,
            model_id=payload.model_id if payload else None,
            triggered_by="projects_page",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
