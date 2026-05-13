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
    # 🆕 (commit 2.3) عمق scan + وزن‌های معیار — مهاجرت از Health
    scan_depth: Optional[str] = None  # quick | standard | deep | thorough
    scan_criteria_weights: Optional[Dict[str, float]] = None
    # 🆕 (audit fix) فیلدهایی که در UI و backend model بودند ولی در schema جا افتاده بودند
    default_execution_mode: Optional[str] = None  # manual | auto_via_projects_page | auto_via_pr
    verify_only_mode: Optional[bool] = None
    verify_interval_hours: Optional[float] = None
    # 🆕 (auto-loop) ping-pong مداوم تا verify=done
    auto_continue_until_done: Optional[bool] = None
    max_auto_loop_rounds: Optional[int] = None
    # 🆕 (P1) مدل‌های auto-scan — لیست ID مدل‌ها (مثل deepseek-coder)
    selected_models: Optional[List[str]] = None
    # 🆕 (Smart Task Lifecycle)
    auto_regenerate_old_prompts: Optional[bool] = None
    prompt_quality_threshold: Optional[int] = None  # 0..100
    dedup_in_manual_create: Optional[bool] = None
    dedup_score_threshold: Optional[float] = None  # 0..1
    # 🔬 (Runtime Verify Stage 4) — base URLs + auth + repo_path برای probe ها
    frontend_base_url: Optional[str] = None
    backend_base_url: Optional[str] = None
    runtime_auth: Optional[Dict[str, Any]] = None   # {type, value}
    runtime_repo_path: Optional[str] = None


class IdeaToPromptRequest(BaseModel):
    idea: str = ""
    watched_id: Optional[str] = None
    type: str = "other"
    priority: str = "medium"
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None
    # 🆕 multi_pass_mode: "auto" | "always" | "never"
    # auto = heuristic، always = همیشه تقسیم مرحله‌ای، never = single-pass
    multi_pass_mode: str = "auto"
    # 🆕 (Stage 7 — File Attachment) — sessionهای آپلودشده برای پیوست
    upload_session_ids: Optional[List[str]] = None
    # 🆕 (Stage 6 — Progress tracker) — اگر داده شد، progress updates روی این track_id
    # ثبت می‌شود تا frontend با /progress/{track_id} poll کند
    progress_track_id: Optional[str] = None


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
    # 🆕 (Smart Task Lifecycle) Dedup Gate parameters
    force_create: bool = False
    merge_into_task_id: Optional[str] = None
    target_files: Optional[List[str]] = None
    acceptance_criteria: Optional[List[str]] = None
    # 🆕 (Multi-pass Checklist) — وقتی تسک از طریق idea_to_prompt با multi-pass
    # ساخته می‌شود، مراحل از پیش‌نمایش پرامپت برای ذخیره به همراه می‌آیند.
    task_steps: Optional[List[Dict[str, Any]]] = None
    overall_completion_pct: Optional[int] = None
    # 🆕 (Stage 7 — File Attachment) — sessionهای آپلودشده برای ربط به این تسک
    upload_session_ids: Optional[List[str]] = None
    # 🔔 Reminder feature — وقتی type="reminder"، این فیلدها استفاده می‌شوند
    reminder_at: Optional[str] = None   # ISO datetime زمان firing بعدی
    reminder_repeat_rule: Optional[str] = None  # daily|weekly|None


class SimilarityCheckRequest(BaseModel):
    """درخواست پیش‌نمایش similarity پیش از ایجاد تسک (frontend debounce)."""
    watched_id: Optional[str] = None
    title: str
    raw_idea: str = ""
    acceptance_criteria: Optional[List[str]] = None
    score_threshold: Optional[float] = None  # override پیش‌فرض watched


class MergePreviewRequest(BaseModel):
    existing_task_id: str
    candidate_title: str
    candidate_raw_idea: str = ""
    candidate_prompt: str = ""
    candidate_acceptance_criteria: Optional[List[str]] = None
    candidate_target_files: Optional[List[str]] = None
    similarity_score: float = 0.0
    use_ai: bool = False
    model_id: Optional[str] = None


class MergeApplyRequest(BaseModel):
    existing_task_id: str
    candidate_title: str
    candidate_raw_idea: str = ""
    candidate_prompt: str = ""
    candidate_acceptance_criteria: Optional[List[str]] = None
    candidate_target_files: Optional[List[str]] = None
    chosen_fields: Optional[Dict[str, str]] = None  # field -> existing|candidate|ai_merged
    source: str = "manual"
    similarity_score: float = 0.0
    # 🆕 مقادیر AI-merged که در preview محاسبه شده (frontend از field_diffs می‌گیرد)
    ai_merged_values: Optional[Dict[str, Any]] = None


class FromInspectorRequest(BaseModel):
    """درخواست ساخت تسک از ویجت «بازرس ویژه»."""
    project_id: str
    project_full_name: Optional[str] = None  # hint از frontend
    mode: str  # "chat" | "visual_debug"
    user_request: str
    enhanced_prompt: Optional[str] = None
    # context
    screenshots: Optional[List[Dict[str, Any]]] = None  # [{base64, page_url, timestamp}]
    console_logs: Optional[List[Dict[str, Any]]] = None
    backend_logs: Optional[List[Dict[str, Any]]] = None
    related_urls: Optional[List[str]] = None
    api_paths: Optional[List[str]] = None
    frontend_url: Optional[str] = None
    backend_url: Optional[str] = None
    page_url: Optional[str] = None
    # metadata
    priority: str = "medium"
    type: str = "bug"
    inspector_session_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    raw_idea: Optional[str] = None  # 🆕 (P4) برای regenerate prompt
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[str] = None
    last_summary: Optional[str] = None
    next_run_at: Optional[str] = None
    archived: Optional[bool] = None  # 🆕 (P3)


class RunTaskRequest(BaseModel):
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None
    # 🔬 (Runtime Verify Stage 8) — controls runtime probes in verify-now
    # default True (همان رفتار قبلی + probe ها)؛ False = verify سریع بدون probe
    include_runtime: bool = True


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


# 🔬 (Runtime Verify Stage 6) — لیست runهای evidence یک task
@router.get("/tasks/{task_id}/evidence/runs")
async def list_evidence_runs(task_id: str):
    """فهرست همهٔ run های verify که evidence ذخیره کرده‌اند، newest first."""
    from pathlib import Path
    from app.services.oversight_service import STORAGE_DIR
    from app.services.verify_runtime.storage import list_runs_for_task
    runs = list_runs_for_task(Path(STORAGE_DIR), task_id)
    return {"task_id": task_id, "runs": runs}


# 🔬 (Runtime Verify Stage 6) — یک فایل evidence (screenshot/JSON) را serve می‌کند
@router.get("/tasks/{task_id}/evidence/{run_id}/{file_path:path}")
async def get_evidence_file(task_id: str, run_id: str, file_path: str):
    """فایل evidence (screenshot یا JSON) را با محافظت در برابر traversal serve می‌کند."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.services.oversight_service import STORAGE_DIR
    from app.services.verify_runtime.storage import resolve_evidence_file
    p = resolve_evidence_file(Path(STORAGE_DIR), task_id, run_id, file_path)
    if p is None:
        raise HTTPException(status_code=404, detail="فایل evidence یافت نشد")
    # تشخیص media type ساده
    suffix = p.suffix.lower()
    media = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".json": "application/json",
        ".txt": "text/plain; charset=utf-8",
    }.get(suffix, "application/octet-stream")
    return FileResponse(str(p), media_type=media)


# 🔬 (Runtime Verify Stage 4) — تست اتصال probe
@router.post("/watched/{watched_id}/runtime/test-connection")
async def runtime_test_connection(watched_id: str):
    """ping به frontend و backend base URL — نتیجه ذخیره می‌شود.

    خروجی: {frontend: {ok, status, error?}, backend: {...}, at: ISO}
    """
    service = get_oversight_service()
    w = next((x for x in service.watched if x.id == watched_id), None)
    if not w:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")
    result = await service._test_runtime_connection_inner(w)
    # ذخیره برای نمایش بعدی در UI
    from app.services.oversight_service import now_iso
    async with service._lock:
        w.runtime_connection_test = result
        w.updated_at = now_iso()
        service._save_watched()
    return result


# 🔬 (Runtime Verify auto-detect) — discover URLs از Render
@router.post("/watched/{watched_id}/runtime/autodetect")
async def runtime_autodetect(watched_id: str):
    """auto-detect frontend/backend URL از Render API + تست اتصال + ذخیره.

    اگر RENDER_API_KEY نباشد، URL ها تغییر نمی‌کنند ولی تست اتصال روی
    URL های موجود اجرا می‌شود.
    """
    service = get_oversight_service()
    w = next((x for x in service.watched if x.id == watched_id), None)
    if not w:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")
    await service._autodetect_and_test_runtime(watched_id)
    # تسک به‌روزشده را برگردان
    w = next((x for x in service.watched if x.id == watched_id), None)
    return {
        "watched": w.to_dict() if w else None,
        "runtime_autodetected": getattr(w, "runtime_autodetected", False) if w else False,
        "runtime_connection_test": getattr(w, "runtime_connection_test", None) if w else None,
    }


# 🔬 (Runtime Verify diagnostics) — چرا probe ها کار می‌کنند یا نمی‌کنند
@router.get("/runtime/diagnostics")
async def runtime_diagnostics():
    """تشخیص وضعیت runtime probes — کجا تنظیم نشده و چرا probe ها skip می‌شوند.

    خروجی شامل:
    - env: وضعیت RUNTIME_VERIFY_ENABLED/UI و حضور توکن‌ها (فقط بود/نبود)
    - watched: برای هر watched، URL ها، repo_path، نتیجه آخرین تست اتصال
    - tasks: شمارش AC ها بر اساس verify_method (چقدر AI کلاسیفای کرده)
    - recent_reports: خلاصه runtime_status در ۵۰ گزارش اخیر
    - issues: لیست مشکلات شناسایی‌شده، human-readable
    """
    import os as _os
    from app.services.oversight_service import get_render_token, get_github_token

    service = get_oversight_service()

    # ---- env flags ----
    runtime_enabled_raw = _os.environ.get("RUNTIME_VERIFY_ENABLED", "true").lower()
    ui_enabled_raw = _os.environ.get("RUNTIME_VERIFY_UI_ENABLED", "true").lower()
    env_info = {
        "RUNTIME_VERIFY_ENABLED": runtime_enabled_raw != "false",
        "RUNTIME_VERIFY_UI_ENABLED": ui_enabled_raw != "false",
        "RENDER_API_KEY_present": bool(get_render_token()),
        "GITHUB_TOKEN_present": bool(get_github_token()),
    }

    # ---- watched ----
    watched_info: List[Dict[str, Any]] = []
    for w in service.watched:
        watched_info.append({
            "id": w.id,
            "repo_full_name": w.repo_full_name,
            "frontend_base_url": w.frontend_base_url,
            "backend_base_url": w.backend_base_url,
            "runtime_repo_path": w.runtime_repo_path,
            "runtime_autodetected": w.runtime_autodetected,
            "runtime_connection_test": w.runtime_connection_test,
            "has_base_url": bool(w.frontend_base_url or w.backend_base_url),
            "has_repo_path": bool(w.runtime_repo_path),
        })

    # ---- tasks AC classification ----
    method_counts: Dict[str, int] = {
        "static": 0, "ui_interaction": 0, "api_response": 0,
        "backend_test": 0, "manual_only": 0, "unknown": 0,
    }
    tasks_without_acs = 0
    total_tasks = 0
    for t in service.tasks:
        total_tasks += 1
        acs = t.acceptance_criteria or []
        if not acs:
            tasks_without_acs += 1
            continue
        for ac in acs:
            if isinstance(ac, dict):
                m = str(ac.get("verify_method") or "static").lower()
            else:
                m = "static"
            method_counts[m] = method_counts.get(m, 0) + 1

    # ---- recent reports runtime_status ----
    recent = service.reports[:50]
    status_breakdown: Dict[str, int] = {}
    for r in recent:
        ev = r.evidence if isinstance(r.evidence, dict) else {}
        rs = str(ev.get("runtime_status") or "missing")
        if rs.startswith("ran"):
            bucket = "ran"
        elif rs.startswith("did_not_run"):
            bucket = "did_not_run"
        elif rs.startswith("skipped"):
            bucket = "skipped_by_user_choice"
        elif rs.startswith("disabled"):
            bucket = "disabled_by_env"
        elif rs.startswith("no acceptance"):
            bucket = "no_acceptance_criteria"
        else:
            bucket = rs[:40] or "missing"
        status_breakdown[bucket] = status_breakdown.get(bucket, 0) + 1

    # ---- issues (human-readable verdict) ----
    issues: List[str] = []
    if not env_info["RUNTIME_VERIFY_ENABLED"]:
        issues.append(
            "RUNTIME_VERIFY_ENABLED=false در env — کل لایه runtime probe غیرفعال است."
        )
    if not env_info["RENDER_API_KEY_present"]:
        issues.append(
            "RENDER_API_KEY ست نشده — autodetect URL از Render کار نمی‌کند."
        )
    no_url = [w["repo_full_name"] for w in watched_info if not w["has_base_url"]]
    if no_url:
        issues.append(
            f"این watched ها frontend/backend base_url ندارند: {no_url} — "
            f"AI enricher صدا زده نمی‌شود و ui_interaction/api_response probe ها skip می‌شوند."
        )
    no_repo = [w["repo_full_name"] for w in watched_info if not w["has_repo_path"]]
    if no_repo:
        issues.append(
            f"این watched ها runtime_repo_path ندارند: {no_repo} — "
            f"static/backend_test probe ها با reason 'repo_path تنظیم نشده' skip می‌شوند."
        )
    non_static = (
        method_counts["ui_interaction"]
        + method_counts["api_response"]
        + method_counts["backend_test"]
    )
    if method_counts["static"] > 0 and non_static == 0:
        issues.append(
            f"همه {method_counts['static']} AC هنوز verify_method=static دارند — "
            f"AI enricher یا اجرا نشده، یا base_url نبوده، یا AI همه را static برگردانده. "
            f"تسک‌های قدیمی (قبل از Stage 2) backfill نیاز دارند."
        )
    if (
        status_breakdown.get("ran", 0) == 0
        and (status_breakdown.get("did_not_run", 0) + status_breakdown.get("missing", 0)) > 0
    ):
        issues.append(
            "هیچ‌کدام از ۵۰ گزارش اخیر runtime_status='ran' ندارند — یعنی در عمل "
            "هیچ probe ای اجرا نشده است (همان رفتار verify سریع و verify کامل)."
        )
    if not issues:
        issues.append("هیچ مشکل آشکاری پیدا نشد — runtime probes باید فعال باشند.")

    return {
        "env": env_info,
        "watched": watched_info,
        "tasks": {
            "total": total_tasks,
            "without_acs": tasks_without_acs,
            "ac_by_method": method_counts,
        },
        "recent_reports": {
            "count_inspected": len(recent),
            "runtime_status_breakdown": status_breakdown,
        },
        "issues": issues,
    }


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
    archived: Optional[str] = None,  # 🆕 (P3) "active" | "archived" | "all" (default: active)
):
    service = get_oversight_service()
    items = await service.list_tasks(
        watched_id=watched_id, status=status, priority=priority
    )
    # filter by archived state — default: hide archived
    archived_filter = (archived or "active").lower()
    if archived_filter == "active":
        items = [t for t in items if not t.get("archived")]
    elif archived_filter == "archived":
        items = [t for t in items if t.get("archived")]
    # archived_filter == "all" → no filter
    return {"items": items}


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
    """ایجاد تسک با dedup gate.

    خروجی همیشه dict با فیلد status:
      - "created": تسک ساخته شد (task پر است)
      - "duplicate_detected": مشابه پیدا شد و تسک ساخته نشد (similar_matches پر است)
      - "merged": با تسک هدف merge شد (task پر است)

    HTTP status همیشه 200 است — duplicate_detected حالت خطا نیست.
    """
    service = get_oversight_service()
    try:
        return await service.create_task(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/from-idea")
async def task_from_idea(payload: IdeaToPromptRequest):
    """تبدیل ایدهٔ خام به پرامپت قدرتمند (پیش‌نمایش، ذخیره نمی‌شود).

    🆕 (Stage 7) — اگر `upload_session_ids` داده شده، فایل‌های پیوست
    قبل از تولید پرامپت استخراج می‌شوند و متن کامل به idea append می‌شود.
    """
    service = get_oversight_service()
    try:
        return await service.idea_to_prompt(
            idea=payload.idea,
            watched_id=payload.watched_id,
            type_=payload.type,
            priority=payload.priority,
            model_id=payload.model_id,
            model_ids=payload.model_ids,
            multi_pass_mode=payload.multi_pass_mode,
            upload_session_ids=payload.upload_session_ids,
            progress_track_id=payload.progress_track_id,
        )
    except ValueError as e:
        # 🛡 (audit fix CRITICAL) — اگر blocked_no_vision_model است،
        # ساختار کامل (candidates، missing_files) را در detail برگردان
        # تا frontend modal toggle نشان دهد.
        blocked = getattr(e, "blocked_payload", None)
        if blocked:
            raise HTTPException(status_code=409, detail=blocked)
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


# 🆕 (P3) archive/unarchive endpoints
@router.post("/tasks/{task_id}/archive")
async def archive_task(task_id: str):
    service = get_oversight_service()
    res = await service.update_task(task_id, {"archived": True})
    if not res:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return {"success": True, "task": res}


@router.post("/tasks/{task_id}/unarchive")
async def unarchive_task(task_id: str):
    service = get_oversight_service()
    res = await service.update_task(task_id, {"archived": False})
    if not res:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return {"success": True, "task": res}


# 🔔 Reminder endpoints
class ReminderSnoozeRequest(BaseModel):
    until: Optional[str] = None        # ISO datetime — مقصد دقیق
    delta_seconds: Optional[int] = None  # یا delta از الان


class ReminderStepToggleRequest(BaseModel):
    done: bool


@router.post("/tasks/{task_id}/reminder/snooze")
async def reminder_snooze(task_id: str, payload: ReminderSnoozeRequest):
    from datetime import datetime, timedelta, timezone
    service = get_oversight_service()
    task = next((t for t in service.tasks if t.id == task_id), None)
    if not task or task.type != "reminder":
        raise HTTPException(status_code=404, detail="یادآوری یافت نشد")
    if payload.until:
        try:
            new_at = datetime.fromisoformat(payload.until.replace("Z", "+00:00"))
            if new_at.tzinfo is None:
                new_at = new_at.replace(tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="فرمت زمان نامعتبر")
    elif payload.delta_seconds is not None:
        new_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload.delta_seconds))
    else:
        raise HTTPException(status_code=400, detail="until یا delta_seconds لازم است")
    from app.services.oversight_service import now_iso
    async with service._lock:
        task.reminder_at = new_at.isoformat()
        task.reminder_state = "snoozed"
        task.reminder_history.append({
            "ts": now_iso(), "action": "snoozed", "new_at": new_at.isoformat(),
        })
        task.updated_at = now_iso()
        service._save_tasks()
    return {"success": True, "task": task.to_dict()}


@router.post("/tasks/{task_id}/reminder/done")
async def reminder_done(task_id: str):
    service = get_oversight_service()
    task = next((t for t in service.tasks if t.id == task_id), None)
    if not task or task.type != "reminder":
        raise HTTPException(status_code=404, detail="یادآوری یافت نشد")
    from app.services.oversight_service import now_iso
    async with service._lock:
        for s in task.task_steps or []:
            s["done"] = True
            s["status"] = "done"
            s["completion_pct"] = 100
        task.reminder_state = "done"
        task.archived = True
        task.archived_at = now_iso()
        task.reminder_history.append({
            "ts": now_iso(), "action": "done", "via": "frontend_button",
        })
        task.updated_at = now_iso()
        service._save_tasks()
    return {"success": True, "task": task.to_dict()}


@router.patch("/tasks/{task_id}/reminder/step/{step_id}")
async def reminder_step_toggle(
    task_id: str, step_id: int, payload: ReminderStepToggleRequest,
):
    service = get_oversight_service()
    task = next((t for t in service.tasks if t.id == task_id), None)
    if not task or task.type != "reminder":
        raise HTTPException(status_code=404, detail="یادآوری یافت نشد")
    from app.services.oversight_service import now_iso
    found = False
    async with service._lock:
        for s in task.task_steps or []:
            if s.get("id") == step_id:
                s["done"] = bool(payload.done)
                s["status"] = "done" if payload.done else "pending"
                s["completion_pct"] = 100 if payload.done else 0
                if payload.done:
                    s["completed_at"] = now_iso()
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail="مرحله یافت نشد")
        task.reminder_history.append({
            "ts": now_iso(), "action": "step_ticked" if payload.done else "step_unticked",
            "step_id": step_id,
        })
        # اگر همه done شدند، خودکار done
        if all(s.get("done") for s in (task.task_steps or [])):
            task.reminder_state = "done"
            task.archived = True
            task.archived_at = now_iso()
            task.reminder_history.append({
                "ts": now_iso(), "action": "done", "via": "all_steps_ticked",
            })
        task.updated_at = now_iso()
        service._save_tasks()
    return {"success": True, "task": task.to_dict()}


# 🆕 (P4) regenerate prompt — بازتولید پرامپت بدون ساخت تسک جدید
class RegenPromptRequest(BaseModel):
    raw_idea: Optional[str] = None  # اگر None، از task.raw_idea فعلی استفاده می‌شود
    model_id: Optional[str] = None
    model_ids: Optional[List[str]] = None


# 🆕 endpoint سبک برای prepend DISCLAIMER به تسک‌های قدیمی (بدون AI call)
@router.post("/tasks/prepend-disclaimer-to-old")
async def prepend_disclaimer_to_old_tasks():
    """تسک‌های موجود که DISCLAIMER ندارند را با prepend به‌روز می‌کند.
    سریع و رایگان — هیچ AI call نمی‌کند.
    """
    from ...services.oversight_strong_prompt import EXECUTOR_DISCLAIMER
    from ...services.oversight_service import get_oversight_service, now_iso
    service = get_oversight_service()
    updated_count = 0
    skipped_count = 0
    async with service._lock:
        for t in service.tasks:
            if not t.prompt:
                skipped_count += 1
                continue
            if "یادداشت مهم برای مدل اجراکننده" in t.prompt[:500]:
                skipped_count += 1
                continue
            # archive قدیمی به history
            history_entry = {
                "prompt": t.prompt,
                "raw_idea": t.raw_idea or "",
                "model_id": (t.models_used[0] if t.models_used else "") or "",
                "generated_at": t.updated_at or t.created_at,
                "source": "before_disclaimer_migration",
            }
            t.prompt_history.insert(0, history_entry)
            t.prompt_history = t.prompt_history[:10]
            # prepend DISCLAIMER
            t.prompt = EXECUTOR_DISCLAIMER + "\n" + t.prompt
            t.updated_at = now_iso()
            updated_count += 1
        service._save_tasks()
    return {
        "ok": True,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "total_tasks": len(service.tasks),
    }

# 🆕 (Inspector → Oversight Bridge) ساخت تسک از بازرس ویژه
@router.post("/tasks/from-inspector")
async def create_task_from_inspector(payload: FromInspectorRequest):
    """ساخت تسک از ویجت بازرس ویژه با پرامپت غنی و context کامل.

    - mode='chat': درخواست متنی + لاگ‌ها → پرامپت غنی
    - mode='visual_debug': درخواست + screenshots → vision describe → پرامپت
      خودکفا که حتی برای مدل غیر بصری قابل درک است
    - بدون محدودیت طول prompt
    - inspector_context ذخیره می‌شود برای دسترسی بعدی به screenshots اصلی
    """
    if payload.mode not in ("chat", "visual_debug"):
        raise HTTPException(status_code=400, detail="mode باید 'chat' یا 'visual_debug' باشد")
    if not (payload.user_request or "").strip():
        raise HTTPException(status_code=400, detail="user_request خالی است")

    from ...services.oversight_inspector_bridge import process_from_inspector
    try:
        result = await process_from_inspector(
            project_id=payload.project_id,
            project_full_name=payload.project_full_name,
            mode=payload.mode,
            user_request=payload.user_request,
            enhanced_prompt=payload.enhanced_prompt,
            screenshots=payload.screenshots,
            console_logs=payload.console_logs,
            backend_logs=payload.backend_logs,
            related_urls=payload.related_urls,
            api_paths=payload.api_paths,
            frontend_url=payload.frontend_url,
            backend_url=payload.backend_url,
            page_url=payload.page_url,
            priority=payload.priority,
            task_type=payload.type,
            inspector_session_id=payload.inspector_session_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا: {str(e)[:300]}")


@router.get("/tasks/{task_id}/inspector-context")
async def get_inspector_context(task_id: str):
    """خواندن inspector_context کامل (شامل screenshots base64) برای یک تسک.

    استفاده: نمایش جزئیات در UI مرکز نظارت یا fetch توسط مدل اجراکننده.
    """
    from ...services.oversight_inspector_bridge import read_inspector_context
    data = read_inspector_context(task_id)
    if not data:
        raise HTTPException(
            status_code=404,
            detail="inspector_context برای این تسک یافت نشد (این تسک از inspector نیست یا context پاک شده)",
        )
    return data


# 🆕 (Smart Task Lifecycle) Dedup + Merge + Auto-Regenerate endpoints
@router.post("/tasks/check-similarity")
async def check_similarity(payload: SimilarityCheckRequest):
    """پیش‌نمایش similarity برای debounce در frontend پیش از submit نهایی فرم."""
    service = get_oversight_service()
    threshold = payload.score_threshold
    if threshold is None:
        # از watched گرفته شود
        if payload.watched_id:
            w = next((x for x in service.watched if x.id == payload.watched_id), None)
            threshold = float(getattr(w, "dedup_score_threshold", 0.65) if w else 0.65)
        else:
            threshold = 0.65
    matches = service.find_similar_active_tasks(
        project_id=payload.watched_id,
        candidate_title=payload.title,
        candidate_raw_idea=payload.raw_idea,
        candidate_acceptance_criteria=payload.acceptance_criteria,
        score_threshold=threshold,
    )
    return {
        "matches": [m.to_dict() for m in matches],
        "count": len(matches),
        "score_threshold": threshold,
    }


@router.post("/tasks/merge-preview")
async def merge_preview(payload: MergePreviewRequest):
    """تولید پیش‌نمایش side-by-side ادغام (بدون اعمال تغییر)."""
    from ...services.task_merge_service import get_task_merge_service
    service = get_oversight_service()
    existing = next((t for t in service.tasks if t.id == payload.existing_task_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="تسک هدف یافت نشد")
    merge_service = get_task_merge_service()
    preview = await merge_service.preview_merge(
        existing=existing,
        candidate_title=payload.candidate_title,
        candidate_raw_idea=payload.candidate_raw_idea,
        candidate_prompt=payload.candidate_prompt,
        candidate_acceptance_criteria=payload.candidate_acceptance_criteria,
        candidate_target_files=payload.candidate_target_files,
        similarity_score=payload.similarity_score,
        use_ai=payload.use_ai,
        model_id=payload.model_id,
    )
    return preview.to_dict()


@router.post("/tasks/merge-apply")
async def merge_apply(payload: MergeApplyRequest):
    """اعمال انتخاب کاربر و ادغام تسک."""
    from ...services.task_merge_service import get_task_merge_service
    merge_service = get_task_merge_service()
    try:
        res = await merge_service.apply_merge(
            existing_task_id=payload.existing_task_id,
            candidate_title=payload.candidate_title,
            candidate_raw_idea=payload.candidate_raw_idea,
            candidate_prompt=payload.candidate_prompt,
            candidate_acceptance_criteria=payload.candidate_acceptance_criteria,
            candidate_target_files=payload.candidate_target_files,
            chosen_fields=payload.chosen_fields,
            source=payload.source,
            similarity_score=payload.similarity_score,
            ai_merged_values=payload.ai_merged_values,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not res:
        raise HTTPException(status_code=404, detail="تسک هدف یافت نشد")
    return {"success": True, "task": res}


@router.post("/watched/{watched_id}/audit-prompt-quality")
async def watched_audit_prompt_quality(watched_id: str):
    """امتیاز کیفیت پرامپت تسک‌های active پروژه را به‌روز می‌کند (بدون AI call)."""
    service = get_oversight_service()
    if not next((w for w in service.watched if w.id == watched_id), None):
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")
    return await service.audit_prompt_quality(watched_id)


class RegenerateLowQualityRequest(BaseModel):
    max_count: int = 5
    reason: str = "manual_override"


@router.post("/watched/{watched_id}/regenerate-low-quality-prompts")
async def watched_regenerate_low_quality(
    watched_id: str, payload: RegenerateLowQualityRequest = None,
):
    """پرامپت‌های با کیفیت پایین این پروژه را بازتولید می‌کند (rate-limit max_count)."""
    service = get_oversight_service()
    if not next((w for w in service.watched if w.id == watched_id), None):
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")
    payload = payload or RegenerateLowQualityRequest()
    return await service.regenerate_low_quality_prompts(
        watched_id,
        max_count=int(payload.max_count or 5),
        reason=payload.reason or "manual_override",
    )


@router.post("/tasks/{task_id}/regenerate-prompt")
async def regenerate_prompt(task_id: str, payload: RegenPromptRequest):
    service = get_oversight_service()
    try:
        res = await service.regenerate_prompt_for_task(
            task_id,
            new_raw_idea=payload.raw_idea,
            model_id=payload.model_id,
            model_ids=payload.model_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if not res:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    return {"success": True, "task": res}


# 🆕 (P4) rollback prompt — برگرداندن نسخهٔ قبلی از history
@router.post("/tasks/{task_id}/rollback-prompt/{history_idx}")
async def rollback_prompt(task_id: str, history_idx: int):
    service = get_oversight_service()
    async with service._lock:
        task = next((t for t in service.tasks if t.id == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="تسک یافت نشد")
        history = list(task.prompt_history or [])
        if history_idx < 0 or history_idx >= len(history):
            raise HTTPException(status_code=400, detail="history_idx نامعتبر")
        # نسخهٔ فعلی را به history منتقل کن
        from datetime import datetime, timezone
        now_iso_local = datetime.now(timezone.utc).isoformat()
        current_entry = {
            "prompt": task.prompt,
            "raw_idea": task.raw_idea or "",
            "model_id": (task.models_used[0] if task.models_used else "") or "",
            "generated_at": task.updated_at or task.created_at,
        }
        # نسخهٔ هدف را restore کن
        target = history[history_idx]
        task.prompt = target.get("prompt") or task.prompt
        task.raw_idea = target.get("raw_idea") or task.raw_idea
        # current را push و target را pop
        new_history = [current_entry] + [h for i, h in enumerate(history) if i != history_idx]
        task.prompt_history = new_history[:10]
        task.updated_at = now_iso_local
        service._save_tasks()
        return {"success": True, "task": task.to_dict()}


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
            include_runtime=payload.include_runtime if payload else True,
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


# 🆕 Pause / Resume / Stop scan (مهاجرت از Health analysis)
# state در progress JSON ذخیره می‌شود تا run_deep_scan در شروع چک کند

@router.post("/scan/{watched_id}/pause")
async def pause_scan(watched_id: str):
    """درخواست pause یک scan در حال اجرا.

    state در progress JSON ست می‌شود. scan در iteration بعدی چک می‌کند
    و متوقف می‌شود (graceful, not abort).
    """
    from ...services.oversight_deep_scan_service import write_progress, read_progress
    progress = read_progress(watched_id)
    if not progress:
        raise HTTPException(status_code=404, detail="هیچ scan فعالی برای این پروژه نیست")
    write_progress(
        watched_id,
        pause_requested=True,
        paused_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )
    return {"success": True, "status": "pause_requested"}


@router.post("/scan/{watched_id}/resume")
async def resume_scan(watched_id: str):
    """clear pause flag — scan در iteration بعدی ادامه می‌دهد."""
    from ...services.oversight_deep_scan_service import write_progress, read_progress
    progress = read_progress(watched_id)
    if not progress:
        raise HTTPException(status_code=404, detail="هیچ scan در حال اجرا نیست")
    write_progress(
        watched_id,
        pause_requested=False,
        resumed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )
    return {"success": True, "status": "resumed"}


@router.post("/scan/{watched_id}/stop")
async def stop_scan(watched_id: str):
    """درخواست توقف کامل scan (cancel).

    scan در iteration بعدی چک می‌کند و خارج می‌شود.
    """
    from ...services.oversight_deep_scan_service import write_progress, read_progress
    progress = read_progress(watched_id)
    if not progress:
        raise HTTPException(status_code=404, detail="هیچ scan فعالی برای این پروژه نیست")
    write_progress(
        watched_id,
        stop_requested=True,
        status="stopping",
        stopped_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )
    return {"success": True, "status": "stop_requested"}


# 🆕 Validation chain status (مهاجرت از Health chain-status)

@router.get("/watched/{watched_id}/chain-status")
async def get_chain_status(watched_id: str):
    """وضعیت کامل chain یک watched project: scan → verify → roadmap → tasks.

    این endpoint جایگزین Health analysis chain-status است.
    """
    from ...services.oversight_deep_scan_service import (
        STRUCTURE_DIR, SCAN_RESULTS_DIR
    )
    from ...services.oversight_codex_service import read_codex, read_roadmap
    from ...services.oversight_service import _read_json

    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise HTTPException(status_code=404, detail="watched project یافت نشد")

    structure = _read_json(STRUCTURE_DIR / f"{watched_id}.json", {}) or {}
    scan_results = _read_json(SCAN_RESULTS_DIR / f"{watched_id}.json", {}) or {}
    codex = read_codex(watched_id)
    roadmap = read_roadmap(watched_id)

    # تسک‌های مرتبط
    related_tasks = [t for t in service.tasks if t.watched_id == watched_id]
    pending_count = sum(1 for t in related_tasks if t.status in ("pending", "suggested"))
    done_count = sum(1 for t in related_tasks if t.status == "done")
    rejected_count = sum(1 for t in related_tasks if t.status in ("cancelled", "archived"))
    verified_count = sum(1 for t in related_tasks if t.verification_status == "done")
    partial_count = sum(1 for t in related_tasks if t.verification_status == "partial")

    return {
        "watched_id": watched_id,
        "repo": watched.repo_full_name,
        # Phase 1: Scan
        "scan": {
            "status": "done" if scan_results.get("ran_at") else "never",
            "last_at": scan_results.get("ran_at"),
            "passes_run": scan_results.get("passes_run", 0),
            "findings_count": len(scan_results.get("findings") or []),
        },
        # Phase 2: Codex
        "codex": {
            "status": "done" if codex.get("updated_at") else "never",
            "last_at": codex.get("updated_at"),
            "files_documented": codex.get("files_count", 0),
        },
        # Phase 3: Roadmap & Ideal State
        "roadmap": {
            "status": "done" if roadmap.get("generated_at") else "never",
            "last_at": roadmap.get("generated_at") or roadmap.get("updated_at"),
            "ideal_state_set": bool(roadmap.get("ideal_state", "").strip()),
            "phases_count": len(roadmap.get("phases") or []),
        },
        # Phase 4: Tasks
        "tasks": {
            "total": len(related_tasks),
            "pending": pending_count,
            "done": done_count,
            "rejected": rejected_count,
        },
        # Phase 5: Verification
        "verification": {
            "verified_count": verified_count,
            "partial_count": partial_count,
        },
        # Last full chain run timestamp (most recent of scan_results)
        "last_full_chain_at": scan_results.get("ran_at"),
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


@router.post("/migration/import-from-project/{project_id}")
async def import_from_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    """مهاجرت data یک پروژهٔ Health → Oversight (دستی، per-project).

    معادل صدا زدن migrate_one_project از script CLI ولی از طریق API.
    این endpoint قبل از حذف نهایی Health به کاربران اجازه می‌دهد
    داده‌های پروژه را به Oversight منتقل کنند.
    """
    from ...models.project import Project
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # delegate به script (که async است)
    try:
        from ...scripts_migration_helper import migrate_one_project_async
    except Exception:
        # fallback: import مستقیم از scripts
        import importlib.util
        from pathlib import Path
        script_path = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "migrate_health_to_oversight.py"
        if not script_path.exists():
            raise HTTPException(status_code=500, detail="migration script یافت نشد")
        spec = importlib.util.spec_from_file_location("migrate_h2o", str(script_path))
        if spec is None or spec.loader is None:
            raise HTTPException(status_code=500, detail="بارگذاری migration script ناموفق")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migrate_one_project_async = module.migrate_one_project

    result = await migrate_one_project_async(proj, dry_run=False)
    return result


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
# 🆕 (Stage 2 — File Attachment) — chunked resumable upload sessions
# ============================================================

from fastapi import Request as _FastAPIRequest


class StartUploadRequest(BaseModel):
    task_draft_id: str = Field(..., description="گروه برای ربط چند فایل به یک تسک (client-generated)")
    original_filename: str
    mime_type: str
    total_size: int = Field(..., ge=1)
    file_order: Optional[int] = None  # اگر None، خودکار بر اساس آخرین + 1


@router.post("/uploads/start")
async def upload_start(payload: StartUploadRequest):
    """شروع یک سشن آپلود chunked. خروجی شامل session_id و chunk_size پیشنهادی."""
    from ...services.oversight_upload_session import (
        get_upload_session_service, CLIENT_CHUNK_SIZE, DEFAULT_MAX_FILE_BYTES,
    )
    svc = get_upload_session_service()
    try:
        s = await svc.start_session(
            task_draft_id=payload.task_draft_id,
            original_filename=payload.original_filename,
            mime_type=payload.mime_type,
            total_size=payload.total_size,
            file_order=payload.file_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"start session failed: {e}")
    return {
        "session_id": s.id,
        "chunk_size": CLIENT_CHUNK_SIZE,
        "max_file_bytes": DEFAULT_MAX_FILE_BYTES,
        "file_order": s.file_order,
        "session": s.to_dict(),
    }


@router.post("/uploads/{session_id}/chunk")
async def upload_chunk(
    session_id: str,
    request: _FastAPIRequest,
    offset: int = Query(..., ge=0, description="بایت شروع این chunk از ابتدای فایل"),
):
    """دریافت یک chunk از فایل (raw body). به‌صورت streaming به temp_path append می‌شود.

    ⚠ Client باید Content-Type = `application/octet-stream` بفرستد و `offset`
    دقیقاً همان `bytes_received` فعلی session باشد (در غیر این صورت 400 با
    expected_offset برمی‌گردد و client باید resume کند).
    """
    from ...services.oversight_upload_session import get_upload_session_service
    svc = get_upload_session_service()
    s = svc.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="session یافت نشد")
    if s.is_terminal():
        raise HTTPException(
            status_code=400,
            detail=f"session در وضعیت {s.status} است — chunk پذیرفته نمی‌شود",
        )

    # خواندن body با streaming — جلوگیری از load در RAM (هر iter ~64KB یا کمتر)
    # FastAPI/Starlette با request.stream() این را native می‌دهد، اما append_chunk
    # یک bytes واحد می‌خواهد. برای سادگی و امنیت RAM، chunk را به‌صورت یکجا اما
    # محدود به یک iteration می‌خوانیم. client هر بار حداکثر CLIENT_CHUNK_SIZE
    # (5MB) می‌فرستد — RAM peak ~5MB OK است.
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="body خالی است")
    try:
        s2 = await svc.append_chunk(session_id, offset, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="session یافت نشد")
    except ValueError as e:
        # offset mismatch یا overrun → client باید با expected_offset resume کند
        raise HTTPException(status_code=400, detail={
            "error": str(e),
            "expected_offset": s.bytes_received,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chunk append failed: {e}")
    return {
        "session_id": s2.id,
        "bytes_received": s2.bytes_received,
        "total_size": s2.total_size,
        "status": s2.status,
        "next_offset": s2.bytes_received,
        "completed": s2.status in ("completed", "extracting", "extracted"),
    }


@router.post("/uploads/{session_id}/complete")
async def upload_complete(session_id: str):
    """علامت‌گذاری پایان upload. اگر bytes_received != total_size خطا می‌دهد."""
    from ...services.oversight_upload_session import get_upload_session_service
    svc = get_upload_session_service()
    try:
        s = await svc.mark_completed(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session یافت نشد")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return s.to_dict()


@router.get("/uploads/{session_id}")
async def upload_status(session_id: str):
    """وضعیت یک session — برای resume."""
    from ...services.oversight_upload_session import get_upload_session_service
    svc = get_upload_session_service()
    s = svc.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="session یافت نشد")
    return s.to_dict()


@router.get("/uploads")
async def upload_list_by_draft(task_draft_id: Optional[str] = Query(None), task_id: Optional[str] = Query(None)):
    """لیست sessionها بر اساس task_draft_id (قبل از create_task) یا task_id (بعد از آن)."""
    from ...services.oversight_upload_session import get_upload_session_service
    svc = get_upload_session_service()
    if task_draft_id:
        return [s.to_dict() for s in svc.list_by_draft(task_draft_id)]
    if task_id:
        return [s.to_dict() for s in svc.list_by_task(task_id)]
    raise HTTPException(status_code=400, detail="task_draft_id یا task_id لازم است")


@router.delete("/uploads/{session_id}")
async def upload_cancel(session_id: str):
    """لغو session و حذف temp."""
    from ...services.oversight_upload_session import get_upload_session_service
    svc = get_upload_session_service()
    s = await svc.cancel(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="session یافت نشد")
    return {"success": True, "session": s.to_dict()}


@router.post("/uploads/cleanup-orphans")
async def upload_cleanup_orphans(ttl_hours: int = Query(24, ge=1, le=720)):
    """حذف temp file هایی که >ttl_hours بدون activity مانده‌اند. (best-effort)"""
    from ...services.oversight_upload_session import get_upload_session_service
    svc = get_upload_session_service()
    removed = await svc.cleanup_orphans(ttl_hours=ttl_hours)
    return {"removed": removed}


# 🆕 (Telegram Compose Stage 6) — progress tracker endpoint
@router.get("/progress/{track_id}")
async def progress_get(track_id: str):
    """snapshot از progress یک operation طولانی — frontend هر چند ثانیه poll می‌کند.

    خروجی: {track_id, stage, current, total, percent, detail, completed, error?, result?}
    اگر track_id ناشناخته → {found: False}.
    """
    from ...services.oversight_progress import get_progress_tracker
    snap = get_progress_tracker().get(track_id)
    if snap is None:
        return {"found": False, "track_id": track_id}
    return {"found": True, **snap.to_dict()}


@router.get("/progress")
async def progress_list_active():
    """لیست عملیات‌های فعال (برای debug/monitoring)."""
    from ...services.oversight_progress import get_progress_tracker
    return {
        "active": [s.to_dict() for s in get_progress_tracker().list_active()],
    }


# ============================================================
# 🆕 (Stage 4+5 — Extraction) — استخراج متن از فایل پیوست
# ============================================================

class ExtractSessionRequest(BaseModel):
    user_idea: str = Field("", description="متن ایدهٔ کاربر — برای plan headings داینامیک")
    preferred_model_id: Optional[str] = None  # override default (gemini-2.5-flash)
    auto_temp_activate: bool = Field(
        False,
        description="اگر True و هیچ مدل enabled نبود، اولین candidate را موقتاً فعال کن",
    )


@router.post("/uploads/{session_id}/check-model")
async def upload_check_model(session_id: str, preferred_model_id: Optional[str] = Query(None)):
    """بررسی: آیا برای mime این session مدل enabled داریم؟
    اگر نه، لیست کاندیداها (disabled) برمی‌گردد تا UI prompt activate نشان دهد.
    """
    from ...services.oversight_upload_session import get_upload_session_service
    from ...services.oversight_model_temp_activate import check_extraction_model_availability
    s = get_upload_session_service().get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="session یافت نشد")
    return {
        "session_id": session_id,
        "mime_type": s.mime_type,
        **check_extraction_model_availability(s.mime_type, preferred_model_id=preferred_model_id),
    }


@router.post("/uploads/{session_id}/extract")
async def upload_extract(session_id: str, payload: ExtractSessionRequest):
    """شروع استخراج متن از یک upload session.

    Flow:
      1. اگر هیچ مدل enabled برای این mime نیست:
         - اگر auto_temp_activate=False → 409 + candidates (UI prompt می‌دهد)
         - اگر auto_temp_activate=True → اولین candidate را موقتاً فعال کن
      2. extraction را اجرا کن
      3. اگر در گام 1 فعال‌سازی موقت داشتیم → پس از اتمام revert کن
         (در try/finally — حتی اگر extraction fail کند).

    خروجی: FileExtraction + segments.
    """
    from ...services.oversight_extraction import (
        extract_session, get_extraction_repo,
    )
    from ...services.oversight_upload_session import get_upload_session_service
    from ...services.oversight_model_temp_activate import (
        check_extraction_model_availability, temp_activate_model, temp_revert_model,
    )

    upload_svc = get_upload_session_service()
    s = upload_svc.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="session یافت نشد")

    # check availability
    avail = check_extraction_model_availability(
        s.mime_type, preferred_model_id=payload.preferred_model_id
    )
    temp_activated_id: Optional[str] = None
    if not avail.get("available"):
        cands = avail.get("candidates") or []
        if not cands:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "هیچ مدلی با قابلیت لازم پیدا نشد (نه enabled نه disabled)",
                    "mime_type": s.mime_type,
                },
            )
        if not payload.auto_temp_activate:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "blocked_no_vision_model",
                    "message": f"هیچ مدل بصری enabled برای mime {s.mime_type} نیست",
                    "candidates": cands,
                    "session_id": session_id,
                    "hint": (
                        "از /api/oversight/uploads/{id}/extract با auto_temp_activate=true "
                        "صدا بزن یا قبل از آن /api/models/settings/{model_id}/temp-activate"
                    ),
                },
            )
        # auto-activate اولین candidate
        chosen = cands[0]["id"]
        try:
            await temp_activate_model(chosen, trigger=f"extract:session={session_id}")
            temp_activated_id = chosen
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"temp activation failed: {e}")

    try:
        fe = await extract_session(
            session_id,
            user_idea=payload.user_idea,
            preferred_model_id=payload.preferred_model_id or temp_activated_id,
        )
    except Exception as e:
        # حتی اگر extraction fail کرد، باید revert کنیم
        if temp_activated_id:
            try:
                await temp_revert_model(temp_activated_id, trigger=f"extract:failed:session={session_id}")
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))

    # success → revert (اگر temp بوده)
    if temp_activated_id:
        try:
            await temp_revert_model(temp_activated_id, trigger=f"extract:done:session={session_id}")
        except Exception as e:
            logger.warning(f"temp revert failed (non-fatal): {e}") if False else None  # safe no-op

    repo = get_extraction_repo()
    return {
        "extraction": fe.to_dict(),
        "segments": [s.to_dict() for s in repo.get_segments(fe.id)],
        "temp_activated_model": temp_activated_id,
    }


# ── Model temp-activate endpoints (manual user-driven flow) ──

@router.post("/models/{model_id}/temp-activate")
async def model_temp_activate(model_id: str, trigger: Optional[str] = Query(None)):
    """فعال‌سازی دستی موقتی یک مدل (در پاسخ به prompt UI).
    کاربر بعد از pickup فایل، اگر مدل disabled بود، این endpoint را صدا می‌زند.
    """
    from ...services.oversight_model_temp_activate import temp_activate_model
    try:
        res = await temp_activate_model(model_id, trigger=trigger or "manual")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return res


@router.post("/models/{model_id}/temp-revert")
async def model_temp_revert(model_id: str, trigger: Optional[str] = Query(None)):
    """برگرداندن مدل به حالت قبل از temp-activate (در صورت لزوم دستی)."""
    from ...services.oversight_model_temp_activate import temp_revert_model
    return await temp_revert_model(model_id, trigger=trigger or "manual")


@router.get("/models/temp-activations")
async def models_temp_activations():
    """فهرست مدل‌هایی که در حال حاضر موقتاً فعال‌اند."""
    from ...services.oversight_model_temp_activate import get_active_temp_activations
    return {"active": get_active_temp_activations()}


# 🆕 (Stage 10 audit fix #4) — تنظیم/خواندن «مدل پیش‌فرض extraction»
# کاربر در /models می‌تواند این را عوض کند، بدون نیاز به deploy.

class SetDefaultExtractionModelRequest(BaseModel):
    model_id: Optional[str] = Field(None, description="model_id جدید — None یا خالی = استفاده از hard-coded default")


@router.get("/models/extraction-default")
async def get_extraction_default():
    """مدل پیش‌فرض extraction فعلی — کاربر در /models می‌بیند و عوض می‌کند.

    اولویت: DB > hard-coded default (gemini-2.5-flash)
    """
    from ...services.oversight_settings import get_default_extraction_model_id_from_db
    from ...core.models_registry import (
        DEFAULT_EXTRACTION_MODEL_ID, list_extraction_model_candidates,
        get_model,
    )
    user_pick = get_default_extraction_model_id_from_db()
    effective_id = user_pick or DEFAULT_EXTRACTION_MODEL_ID
    eff_model = get_model(effective_id)
    # کاندیداهای ممکن: همهٔ مدل‌های multimodal capable
    cands = list_extraction_model_candidates("application/pdf", include_disabled=True)
    return {
        "user_pick": user_pick,
        "effective_id": effective_id,
        "effective_name": eff_model.name if eff_model else effective_id,
        "hard_coded_default": DEFAULT_EXTRACTION_MODEL_ID,
        "candidates": [
            {
                "id": c.id, "name": c.name, "provider": c.provider.value,
                "priority": c.priority, "enabled": c.enabled,
                "capabilities": [str(cap) for cap in c.capabilities],
            }
            for c in cands
        ],
    }


@router.post("/models/extraction-default")
async def set_extraction_default(payload: SetDefaultExtractionModelRequest):
    """تنظیم مدل پیش‌فرض extraction (در DB ذخیره می‌شود — restart-safe)."""
    from ...services.oversight_settings import set_default_extraction_model_id_in_db
    from ...core.models_registry import (
        DEFAULT_EXTRACTION_MODEL_ID, get_model, list_extraction_model_candidates,
    )
    mid = (payload.model_id or "").strip() or None
    # اعتبارسنجی — اگر داده شد، باید در registry موجود و capable multimodal باشد
    if mid:
        m = get_model(mid)
        if m is None:
            raise HTTPException(status_code=404, detail=f"model_id ناشناخته: {mid}")
        capable_ids = {
            c.id for c in list_extraction_model_candidates("application/pdf", include_disabled=True)
        }
        if mid not in capable_ids:
            raise HTTPException(
                status_code=400,
                detail=f"مدل {mid} توان extraction (multimodal) ندارد",
            )
    ok = set_default_extraction_model_id_in_db(mid)
    if not ok:
        raise HTTPException(status_code=500, detail="ذخیره تنظیمات ناموفق")
    return {
        "success": True,
        "user_pick": mid,
        "effective_id": mid or DEFAULT_EXTRACTION_MODEL_ID,
    }


@router.get("/tasks/{task_id}/extractions")
async def task_extractions(task_id: str):
    """لیست همهٔ فایل‌های استخراج‌شدهٔ یک تسک."""
    from ...services.oversight_extraction import get_extraction_repo
    repo = get_extraction_repo()
    items = repo.list_by_task(task_id)
    return {
        "task_id": task_id,
        "count": len(items),
        "extractions": [e.to_dict() for e in items],
    }


@router.get("/extractions/{extraction_id}/segments")
async def extraction_segments(extraction_id: str):
    """segmentهای استخراج‌شدهٔ یک فایل، به ترتیب segment_index."""
    from ...services.oversight_extraction import get_extraction_repo
    repo = get_extraction_repo()
    fe = repo.get(extraction_id)
    if fe is None:
        raise HTTPException(status_code=404, detail="extraction یافت نشد")
    segs = sorted(repo.get_segments(extraction_id), key=lambda s: s.segment_index)
    return {
        "extraction": fe.to_dict(),
        "segments": [s.to_dict() for s in segs],
    }


@router.get("/extractions/{extraction_id}/full-text")
async def extraction_full_text(extraction_id: str):
    """متن کامل ادغام‌شدهٔ یک extraction."""
    from ...services.oversight_extraction import get_extraction_repo
    repo = get_extraction_repo()
    fe = repo.get(extraction_id)
    if fe is None:
        raise HTTPException(status_code=404, detail="extraction یافت نشد")
    return {
        "extraction_id": extraction_id,
        "filename": fe.original_filename,
        "mime_type": fe.mime_type,
        "status": fe.status,
        "full_text": repo.full_text(extraction_id),
    }


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
