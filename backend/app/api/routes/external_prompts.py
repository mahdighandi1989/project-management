# -*- coding: utf-8 -*-
"""
🤖 External Prompts API
endpoints برای ابزارهای خارجی (Cloud Code و …) که پرامپت‌ها را به ترتیب
اولویت پیک‌آپ و اجرا می‌کنند.

Auth: header `X-External-Token` که با env var `EXTERNAL_TOOL_TOKEN` چک می‌شود.
نقش EXTERNAL_TOOL اجازه ندارد: archive، delete، تغییر title/prompt.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.oversight_service import get_oversight_service, now_iso
from ...services.prompt_github_sync import (
    PICKABLE_STATUSES,
    PICKABLE_EXTERNAL_STATUSES,
)

logger = logging.getLogger(__name__)

DEFAULT_LEASE_MINUTES = 30


def _check_external_token(provided: Optional[str]) -> None:
    expected = os.environ.get("EXTERNAL_TOOL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="EXTERNAL_TOOL_TOKEN env var تنظیم نشده — endpoint غیرفعال است.",
        )
    if not provided or provided.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid X-External-Token")


def require_external_token(
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
) -> None:
    """FastAPI dependency برای endpoint های ابزار خارجی."""
    _check_external_token(x_external_token)


def require_admin_token(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """FastAPI dependency برای endpoint های مدیریتی (backfill و …)."""
    expected = os.environ.get("ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_TOKEN env var تنظیم نشده — endpoint غیرفعال است.",
        )
    if not x_admin_token or x_admin_token.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token")


router = APIRouter(prefix="/external/prompts", tags=["External Prompts"])


def _is_lease_expired(task: Any) -> bool:
    lease = getattr(task, "external_lease_until", None)
    if not lease:
        return True
    try:
        exp = datetime.fromisoformat(lease.replace("Z", "+00:00"))
        return exp <= datetime.now(timezone.utc)
    except Exception:
        return True


def _task_summary(task: Any) -> Dict[str, Any]:
    return {
        "task_id": task.id,
        "watched_id": task.watched_id,
        "project": task.project_full_name,
        "title": task.title,
        "type": task.type,
        "priority": task.priority,
        "execution_priority": getattr(task, "execution_priority", 100),
        "status": task.status,
        "external_status": getattr(task, "external_status", "pending"),
        "verification_status": task.verification_status,
        "github_prompt_path": getattr(task, "github_prompt_path", None),
        "external_attempts": getattr(task, "external_attempts", 0),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────


class ClaimRequest(BaseModel):
    agent_id: str = Field(..., description="شناسه ابزار/agent (e.g., 'cloud-code-1')")
    lease_minutes: int = Field(default=DEFAULT_LEASE_MINUTES, ge=1, le=240)


class CompleteRequest(BaseModel):
    agent_id: str
    summary: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)


class FailRequest(BaseModel):
    agent_id: str
    error: str
    retry: bool = True


class ProgressRequest(BaseModel):
    agent_id: str
    progress_pct: int = Field(default=0, ge=0, le=100)
    note: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/next", dependencies=[Depends(require_external_token)])
async def list_next_prompts(
    limit: int = Query(default=10, ge=1, le=100),
    watched_id: Optional[str] = Query(default=None),
):
    """لیست تسک‌های pickable به ترتیب اولویت اجرا (کوچک‌تر = اولویت بالاتر).

    شامل فقط تسک‌هایی که:
      - archived=False
      - status ∈ PICKABLE_STATUSES
      - external_status ∈ PICKABLE_EXTERNAL_STATUSES (یا claimed با lease منقضی)
    """
    service = get_oversight_service()
    candidates: List[Any] = []
    for t in service.tasks:
        if getattr(t, "archived", False):
            continue
        if watched_id and t.watched_id != watched_id:
            continue
        if t.status not in PICKABLE_STATUSES:
            continue
        ext = getattr(t, "external_status", "pending") or "pending"
        if ext == "claimed" and not _is_lease_expired(t):
            continue
        if ext == "in_progress" and not _is_lease_expired(t):
            continue
        if ext == "done":
            continue
        candidates.append(t)
    candidates.sort(
        key=lambda x: (
            getattr(x, "execution_priority", 100),
            getattr(x, "created_at", ""),
        )
    )
    return {
        "total": len(candidates),
        "returned": min(len(candidates), limit),
        "tasks": [_task_summary(t) for t in candidates[:limit]],
    }


@router.get("/{task_id}", dependencies=[Depends(require_external_token)])
async def get_prompt(task_id: str):
    """محتوای کامل تسک — شامل prompt و acceptance_criteria و task_steps."""
    service = get_oversight_service()
    t = next((x for x in service.tasks if x.id == task_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        **_task_summary(t),
        "prompt": t.prompt,
        "raw_idea": t.raw_idea,
        "acceptance_criteria": t.acceptance_criteria,
        "task_steps": t.task_steps,
        "target_files": t.target_files,
        "followup_prompt": t.followup_prompt,
        "tags": t.tags,
        "deadline": t.deadline,
        "external_locked_by": t.external_locked_by,
        "external_lease_until": t.external_lease_until,
    }


@router.post("/{task_id}/claim", dependencies=[Depends(require_external_token)])
async def claim_prompt(task_id: str, payload: ClaimRequest):
    """قفل گرفتن یک تسک برای اجرا (با lease).

    اگر تسک قبلاً claim شده و lease معتبر دارد، 409 برمی‌گرداند مگر اینکه
    همان agent_id باشد (renewal).
    """
    service = get_oversight_service()
    async with service._lock:
        t = next((x for x in service.tasks if x.id == task_id), None)
        if not t:
            raise HTTPException(status_code=404, detail="task not found")
        if t.archived:
            raise HTTPException(status_code=409, detail="task archived")
        if t.status not in PICKABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"task status '{t.status}' not pickable",
            )
        cur_status = getattr(t, "external_status", "pending") or "pending"
        cur_lock = getattr(t, "external_locked_by", None)
        if (
            cur_status in ("claimed", "in_progress")
            and not _is_lease_expired(t)
            and cur_lock != payload.agent_id
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_claimed",
                    "locked_by": cur_lock,
                    "lease_until": t.external_lease_until,
                },
            )
        lease_until = (
            datetime.now(timezone.utc) + timedelta(minutes=payload.lease_minutes)
        ).isoformat()
        t.external_status = "claimed"
        t.external_locked_by = payload.agent_id
        t.external_locked_at = now_iso()
        t.external_lease_until = lease_until
        t.external_attempts = int(getattr(t, "external_attempts", 0) or 0) + 1
        t.updated_at = now_iso()
        service._save_tasks()
        service._recompute_execution_priorities(t)
        service._schedule_prompt_sync(t, rebuild_index=True)
    return {"success": True, "task": _task_summary(t), "lease_until": lease_until}


@router.post("/{task_id}/progress", dependencies=[Depends(require_external_token)])
async def report_progress(task_id: str, payload: ProgressRequest):
    """گزارش پیشرفت اختیاری از ابزار خارجی + تمدید lease.

    اگر lease قبلاً منقضی شده، 410 برمی‌گرداند — agent نمی‌تواند خاموش-روشن
    سرقت lease کند، باید claim مجدد بزند.
    """
    service = get_oversight_service()
    async with service._lock:
        t = next((x for x in service.tasks if x.id == task_id), None)
        if not t:
            raise HTTPException(status_code=404, detail="task not found")
        if t.external_locked_by != payload.agent_id:
            raise HTTPException(
                status_code=403,
                detail="agent_id mismatch — only the claimant can report progress",
            )
        if _is_lease_expired(t):
            raise HTTPException(
                status_code=410,
                detail="lease expired — please re-claim before reporting progress",
            )
        t.external_status = "in_progress"
        t.external_lease_until = (
            datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_LEASE_MINUTES)
        ).isoformat()
        t.updated_at = now_iso()
        service._save_tasks()
        # /progress هم باید فایل GitHub را sync کند (external_status: in_progress
        # در front-matter دیده شود) — هم‌سو با claim/complete/fail.
        service._schedule_prompt_sync(t, rebuild_index=False)
    return {"success": True, "task": _task_summary(t)}


@router.post("/{task_id}/complete", dependencies=[Depends(require_external_token)])
async def complete_prompt(task_id: str, payload: CompleteRequest):
    """گزارش تکمیل توسط ابزار خارجی.

    این endpoint تسک را به‌صورت "applied_externally_pending_verify" علامت می‌زند.
    تأیید نهایی فقط با verify انجام می‌شود (نقش EXTERNAL_TOOL نمی‌تواند آرشیو کند).
    """
    service = get_oversight_service()
    async with service._lock:
        t = next((x for x in service.tasks if x.id == task_id), None)
        if not t:
            raise HTTPException(status_code=404, detail="task not found")
        if t.external_locked_by != payload.agent_id:
            raise HTTPException(
                status_code=403,
                detail="agent_id mismatch — only the claimant can complete",
            )
        t.external_status = "done"
        t.external_locked_by = None
        t.external_lease_until = None
        t.external_last_error = None
        # علامت applied — برای ورود به جریان verify
        t.verification_status = "applied_externally_pending_verify"
        t.manually_marked_applied_at = now_iso()
        if payload.summary:
            t.last_summary = payload.summary[:5000]
        if payload.evidence:
            try:
                t.applied_evidence = {
                    **(t.applied_evidence or {}),
                    "external_tool": payload.evidence,
                    "agent_id": payload.agent_id,
                    "completed_at": now_iso(),
                }
            except Exception:
                pass
        t.updated_at = now_iso()
        service._save_tasks()
        service._recompute_execution_priorities(t)
        service._schedule_prompt_sync(t, rebuild_index=True)
    return {"success": True, "task": _task_summary(t)}


@router.post("/{task_id}/fail", dependencies=[Depends(require_external_token)])
async def fail_prompt(task_id: str, payload: FailRequest):
    """گزارش شکست از ابزار خارجی. اگر retry=True، تسک به pending برمی‌گردد."""
    service = get_oversight_service()
    async with service._lock:
        t = next((x for x in service.tasks if x.id == task_id), None)
        if not t:
            raise HTTPException(status_code=404, detail="task not found")
        if t.external_locked_by != payload.agent_id:
            raise HTTPException(
                status_code=403,
                detail="agent_id mismatch",
            )
        t.external_last_error = payload.error[:1000]
        t.external_locked_by = None
        t.external_lease_until = None
        t.external_status = "failed" if not payload.retry else "pending"
        t.updated_at = now_iso()
        service._save_tasks()
        service._recompute_execution_priorities(t)
        service._schedule_prompt_sync(t, rebuild_index=True)
    return {"success": True, "task": _task_summary(t)}


# ─────────────────────────────────────────────────────────────────────────────
# Backfill / Maintenance — برای راه‌اندازی اولیه و trigger دستی
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/_admin/backfill", dependencies=[Depends(require_admin_token)])
async def backfill_all(watched_id: Optional[str] = Query(default=None)):
    """sync همهٔ تسک‌های موجود به ریپوهای مربوطه + ساخت index.

    اگر watched_id داده شد فقط همان پروژه. وگرنه همه‌ی پروژه‌های با
    prompt_sync_enabled=True. این endpoint از service.force_sync_and_rebuild_all
    استفاده می‌کند که semaphore=5، _index.json صریح، و persistence نهایی
    را تضمین می‌کند.
    """
    service = get_oversight_service()
    result = await service.force_sync_and_rebuild_all(watched_id=watched_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error", "force_sync failed"),
        )
    return result


@router.post("/_admin/rebuild-index", dependencies=[Depends(require_admin_token)])
async def rebuild_index_only(watched_id: Optional[str] = Query(default=None)):
    """فقط _index.json پروژه‌ها را بازسازی می‌کند — بدون re-sync تسک‌ها.

    کاربرد: اگر در runtime به دلیل debounce-race یا restart، _index.json
    یک پروژه ساخته نشد، این endpoint سریع بازسازی می‌کند بدون اینکه
    تمام تسک‌ها دوباره به GitHub push شوند (که rate-limit مصرف می‌کند).
    """
    from ...services.prompt_github_sync import rebuild_project_index
    from ...services.oversight_service import get_github_token
    token = get_github_token()
    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured")

    service = get_oversight_service()
    targets = [
        w for w in service.watched
        if getattr(w, "prompt_sync_enabled", True)
        and (watched_id is None or w.id == watched_id)
    ]
    results: List[Dict[str, Any]] = []
    for w in targets:
        try:
            res = await rebuild_project_index(list(service.tasks), w, token=token)
            ok = bool(res.get("success"))
            results.append({
                "watched_id": w.id,
                "repo": w.repo_full_name,
                "rebuilt": ok,
                "error": res.get("error") if not ok else None,
            })
            if ok:
                logger.info(
                    f"rebuild-index: ✓ {w.repo_full_name} (manual trigger)"
                )
            else:
                logger.warning(
                    f"rebuild-index: ✗ {w.repo_full_name}: {res.get('error')}"
                )
        except Exception as e:
            results.append({
                "watched_id": w.id,
                "repo": w.repo_full_name,
                "rebuilt": False,
                "error": str(e),
            })
    return {
        "success": True,
        "projects": len(targets),
        "rebuilt": sum(1 for r in results if r["rebuilt"]),
        "results": results,
    }


@router.get("/_admin/diagnose/{task_id}", dependencies=[Depends(require_admin_token)])
async def diagnose_task_sync(task_id: str):
    """تشخیص دلیل عدم همگام‌سازی یک تسک به GitHub.

    خروجی شامل تمام شواهد لازم برای فهم اینکه چرا/چگونه sync انجام
    می‌شود (یا نمی‌شود):
      - وضعیت dirty (updated vs synced timestamps)
      - وجود token
      - وضعیت watched project (enabled, repo, branch)
      - exclude list
      - last_error قبلی
      - مسیر مورد انتظار در GitHub
    """
    import os as _os
    from ...services.oversight_service import get_github_token
    from ...services.prompt_github_sync import (
        _resolve_repo_and_branch, _excluded_repos, _file_path,
        compute_execution_priority,
    )

    service = get_oversight_service()
    t = next((x for x in service.tasks if x.id == task_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")

    token = get_github_token()
    watched = service._find_watched(t.watched_id) if t.watched_id else None

    # detect why dirty (یا نه)
    synced_at = getattr(t, "github_prompt_synced_at", None)
    is_dirty = service._is_task_dirty(t)
    dirty_reason = (
        "never synced" if not synced_at
        else (f"updated_at({t.updated_at}) > synced_at({synced_at})" if is_dirty
              else "in sync (updated_at <= synced_at)")
    )

    # resolve repo info
    repo_info = None
    if watched:
        resolved = _resolve_repo_and_branch(watched)
        if resolved:
            owner, repo, branch = resolved
            repo_info = {
                "owner": owner, "repo": repo, "branch": branch,
                "expected_path": _file_path(t.id, archived=getattr(t, "archived", False)),
            }
        else:
            repo_info = {"error": "_resolve_repo_and_branch returned None"}

    excluded = _excluded_repos()
    is_excluded = bool(watched) and getattr(
        watched, "repo_full_name", ""
    ).strip().lower() in excluded

    return {
        "task_id": t.id,
        "title": t.title,
        "is_dirty": is_dirty,
        "dirty_reason": dirty_reason,
        "github_state": {
            "github_prompt_path": getattr(t, "github_prompt_path", None),
            "github_prompt_sha": getattr(t, "github_prompt_sha", None),
            "github_prompt_synced_at": synced_at,
            "github_prompt_last_error": getattr(t, "github_prompt_last_error", None),
            "github_prompt_archived": getattr(t, "github_prompt_archived", False),
            "updated_at": t.updated_at,
            "execution_priority": getattr(t, "execution_priority", None),
        },
        "watched": {
            "found": watched is not None,
            "watched_id": t.watched_id,
            "repo_full_name": getattr(watched, "repo_full_name", None) if watched else None,
            "prompt_sync_enabled": (
                getattr(watched, "prompt_sync_enabled", None)
                if watched else None
            ),
            "default_branch": (
                getattr(watched, "default_branch", None)
                if watched else None
            ),
            "is_excluded_by_env": is_excluded,
        },
        "config": {
            "github_token_set": bool(token),
            "excluded_repos": sorted(excluded),
            "external_tool_token_set": bool(
                _os.environ.get("EXTERNAL_TOOL_TOKEN", "").strip()
            ),
            "admin_token_set": bool(
                _os.environ.get("ADMIN_TOKEN", "").strip()
            ),
        },
        "diagnosis": _diagnose_summary(t, watched, token, is_dirty, is_excluded, repo_info),
        "repo_info": repo_info,
    }


def _diagnose_summary(task, watched, token, is_dirty, is_excluded, repo_info) -> str:
    """تشخیص محتمل‌ترین دلیل عدم sync — به فارسی برای کاربر."""
    if not token:
        return "❌ GITHUB_TOKEN روی backend ست نیست — sync کاملاً غیرفعال."
    if not watched:
        return f"❌ watched project با id={task.watched_id} پیدا نشد."
    if not getattr(watched, "prompt_sync_enabled", True):
        return "❌ prompt_sync_enabled=False روی این watched. در config پروژه فعالش کن."
    if is_excluded:
        return (
            f"❌ ریپو {watched.repo_full_name} در PROMPT_SYNC_EXCLUDE_REPOS هست. "
            f"اگر می‌خوای sync بشه، اسمش رو از env var حذف کن."
        )
    if not repo_info or repo_info.get("error"):
        return f"❌ _resolve_repo_and_branch fail شد: {repo_info.get('error', '?')}"
    if not is_dirty:
        return (
            "✓ تسک in-sync است (updated_at <= synced_at). "
            "اگر می‌خوای force sync بشه، یک update فیک بزن (مثلاً regenerate) "
            "یا /admin/backfill رو با watched_id این پروژه صدا بزن."
        )
    last_err = getattr(task, "github_prompt_last_error", None)
    if last_err:
        return (
            f"⚠️ تسک dirty هست و sync trigger می‌شه ولی آخرین تلاش fail شده: "
            f"{last_err}. logs Render رو چک کن برای 'prompt-sync ✗' marker."
        )
    return (
        "✓ همه شرایط fulfilled. تسک باید sync بشه. اگه نمی‌بینی فایل رو در "
        f"{repo_info['owner']}/{repo_info['repo']}@{repo_info['branch']}:"
        f"{repo_info['expected_path']}، logs Render رو دنبال 'prompt-sync ✓' "
        "یا 'prompt-sync ✗' برای task_id="
        f"{task.id[:8]} بگرد."
    )
