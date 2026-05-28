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

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.oversight_service import get_oversight_service, now_iso
from ...services.prompt_github_sync import (
    compute_execution_priority,
    PICKABLE_STATUSES,
    PICKABLE_EXTERNAL_STATUSES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external/prompts", tags=["External Prompts"])

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


@router.get("/next")
async def list_next_prompts(
    limit: int = Query(default=10, ge=1, le=100),
    watched_id: Optional[str] = Query(default=None),
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
):
    """لیست تسک‌های pickable به ترتیب اولویت اجرا (کوچک‌تر = اولویت بالاتر).

    شامل فقط تسک‌هایی که:
      - archived=False
      - status ∈ PICKABLE_STATUSES
      - external_status ∈ PICKABLE_EXTERNAL_STATUSES (یا claimed با lease منقضی)
    """
    _check_external_token(x_external_token)
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


@router.get("/{task_id}")
async def get_prompt(
    task_id: str,
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
):
    """محتوای کامل تسک — شامل prompt و acceptance_criteria و task_steps."""
    _check_external_token(x_external_token)
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


@router.post("/{task_id}/claim")
async def claim_prompt(
    task_id: str,
    payload: ClaimRequest,
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
):
    """قفل گرفتن یک تسک برای اجرا (با lease).

    اگر تسک قبلاً claim شده و lease معتبر دارد، 409 برمی‌گرداند مگر اینکه
    همان agent_id باشد (renewal).
    """
    _check_external_token(x_external_token)
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
        service._recompute_execution_priorities()
        service._schedule_prompt_sync(t, rebuild_index=True)
    return {"success": True, "task": _task_summary(t), "lease_until": lease_until}


@router.post("/{task_id}/progress")
async def report_progress(
    task_id: str,
    payload: ProgressRequest,
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
):
    """گزارش پیشرفت اختیاری از ابزار خارجی + تمدید lease."""
    _check_external_token(x_external_token)
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
        t.external_status = "in_progress"
        t.external_lease_until = (
            datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_LEASE_MINUTES)
        ).isoformat()
        t.updated_at = now_iso()
        service._save_tasks()
    return {"success": True, "task": _task_summary(t)}


@router.post("/{task_id}/complete")
async def complete_prompt(
    task_id: str,
    payload: CompleteRequest,
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
):
    """گزارش تکمیل توسط ابزار خارجی.

    این endpoint تسک را به‌صورت "applied_externally_pending_verify" علامت می‌زند.
    تأیید نهایی فقط با verify انجام می‌شود (نقش EXTERNAL_TOOL نمی‌تواند آرشیو کند).
    """
    _check_external_token(x_external_token)
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
        service._recompute_execution_priorities()
        service._schedule_prompt_sync(t, rebuild_index=True)
    return {"success": True, "task": _task_summary(t)}


@router.post("/{task_id}/fail")
async def fail_prompt(
    task_id: str,
    payload: FailRequest,
    x_external_token: Optional[str] = Header(default=None, alias="X-External-Token"),
):
    """گزارش شکست از ابزار خارجی. اگر retry=True، تسک به pending برمی‌گردد."""
    _check_external_token(x_external_token)
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
        service._recompute_execution_priorities()
        service._schedule_prompt_sync(t, rebuild_index=True)
    return {"success": True, "task": _task_summary(t)}


# ─────────────────────────────────────────────────────────────────────────────
# Backfill / Maintenance — برای راه‌اندازی اولیه و trigger دستی
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/_admin/backfill")
async def backfill_all(
    watched_id: Optional[str] = Query(default=None),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """sync همهٔ تسک‌های موجود به ریپوهای مربوطه + ساخت index.

    اگر watched_id داده شد فقط همان پروژه. وگرنه همه‌ی پروژه‌های با
    prompt_sync_enabled=True.
    """
    expected = os.environ.get("ADMIN_TOKEN", "").strip()
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token")

    from ...services.prompt_github_sync import (
        safe_sync_task, safe_rebuild_index,
    )
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
    if not targets:
        return {"success": True, "synced_tasks": 0, "projects": 0}

    service._recompute_execution_priorities()
    synced = 0
    for w in targets:
        for t in service.tasks:
            if t.watched_id != w.id:
                continue
            await safe_sync_task(t, w, token=token)
            synced += 1
        await safe_rebuild_index(list(service.tasks), w, token=token)
    service._save_tasks()
    return {
        "success": True,
        "projects": len(targets),
        "synced_tasks": synced,
    }
