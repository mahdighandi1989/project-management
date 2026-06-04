# -*- coding: utf-8 -*-
"""
🤖 External Prompts API
endpoints برای ابزارهای خارجی (Cloud Code و …) که پرامپت‌ها را به ترتیب
اولویت پیک‌آپ و اجرا می‌کنند.

Auth: header `X-External-Token` که با env var `EXTERNAL_TOOL_TOKEN` چک می‌شود.
نقش EXTERNAL_TOOL اجازه ندارد: archive، delete، تغییر title/prompt.
"""
from __future__ import annotations

import asyncio
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


# 🆕 (External Runner Notifications) — Telegram feedback برای هر مرحله از
# اجرای Claude Auto-Runner. کاربر بدون باز کردن GitHub Actions می‌فهمد:
#   1) workflow چه تسکی را برداشت (🏃 شروع)
#   2) چه تسکی موفق شد (✅ پایان)
#   3) چه تسکی شکست خورد (❌ خطا)
# همه best-effort + fire-and-forget — اگر notification شکست خورد، API
# response تحت تأثیر قرار نمی‌گیرد.
def _emit_runner_notification(
    *,
    event: str,
    task: Any,
    agent_id: str,
    extra: str = "",
) -> None:
    """ارسال غیربلاکینگ نوتیفیکیشن. اگر agent_id با Claude Auto-Runner
    مطابقت نداشته باشد (مثلاً ابزار خارجی دیگر)، رد می‌شود."""
    if (agent_id or "").lower() not in (
        "claude-code-action", "claude-runner", "claude-auto-task",
        "claude-manual-trigger", "claude-telegram-trigger",
        "claude-runner-sweeper", "claude-runner-recovery",
    ):
        return
    try:
        from ...services.notification_service import notification_service
        title = (getattr(task, "title", "") or "")[:120]
        repo = (getattr(task, "project_full_name", "") or "—")
        task_id_short = (getattr(task, "id", "") or "")[:8]
        if event == "external_runner_claimed":
            emoji, head = "🏃", "Claude شروع کرد"
        elif event == "external_runner_completed":
            emoji, head = "✅", "Claude تسک را تکمیل کرد"
        elif event == "external_runner_failed":
            emoji, head = "❌", "Claude شکست خورد"
        else:
            emoji, head = "ℹ️", "Claude runner update"
        lines = [
            f"{emoji} *{head}*",
            "",
            f"📁 پروژه: `{repo}`",
            f"📌 تسک: «{title}»",
            f"🆔 `{task_id_short}`",
        ]
        if extra:
            lines.extend(["", extra.strip()[:600]])
        msg = "\n".join(lines)
        asyncio.create_task(
            notification_service.notify_event(
                event,
                msg,
                subject=head,
                priority="low",
                project_name=repo,
                watched_id=getattr(task, "watched_id", None),
            )
        )
    except Exception as _e:
        logger.debug(f"_emit_runner_notification skipped: {_e}")

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
    # 🆕 Telegram feedback: 🏃 شروع
    _emit_runner_notification(
        event="external_runner_claimed", task=t, agent_id=payload.agent_id,
    )
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
    # 🆕 Telegram feedback: ✅ تکمیل
    _emit_runner_notification(
        event="external_runner_completed",
        task=t,
        agent_id=payload.agent_id,
        extra=(payload.summary or "")[:500],
    )
    # 🤖🔬 (Claude Auto-Runner — verify-then-chain) — به‌جای chain-next مستقیم،
    # **اول verify می‌زنیم** روی همین تسک. تا تمام شدن verify، lock فعال
    # می‌شود تا هیچ workflow دیگری برای این watched trigger نشود (حتی اگر
    # فولدر prompt/ تغییر کند). بعد از verify، بسته به نتیجه:
    #   - done → auto-archive (در خود verifier) + chain-next
    #   - partial و retries مانده → re-trigger همان تسک (auto-loop)
    #   - max retries → TODO file + chain-next
    if (
        (payload.agent_id or "").lower() in (
            "claude-code-action", "claude-runner", "claude-auto-task"
        )
        and getattr(t, "watched_id", None)
    ):
        try:
            watched = service._find_watched(t.watched_id)
            # 🆕 (manual single-task) — verify بعد از complete باید بدون توجه به
            # claude_runner_enabled اجرا شود (تنها شرط: workflow نصب شده باشد).
            # اگر کاربر manual single-task trigger زده، انتظار دارد همان موقع
            # verify شود و در صورت partial، Claude دوباره روی همان تسک کار کند.
            if (
                watched is not None
                and getattr(watched, "claude_runner_workflow_path", None)
            ):
                # acquire verify lock — تا تمام شدن verify، تسک بعدی شروع نشود
                if service._acquire_verify_lock(watched.id, t.id):
                    service._save_watched()
                    logger.info(
                        f"verify-after-complete: locked watched={watched.id} "
                        f"on task={t.id} — scheduling verify"
                    )
                    asyncio.create_task(
                        _verify_then_chain(
                            task_id=t.id,
                            watched_id=watched.id,
                            agent_id=payload.agent_id,
                        )
                    )
                else:
                    logger.warning(
                        f"verify-after-complete: could not acquire lock for "
                        f"watched={watched.id} task={t.id} (already locked)"
                    )
        except Exception as _vfy_e:
            logger.warning(
                f"verify-after-complete scheduling failed for task {t.id}: "
                f"{_vfy_e}"
            )
    return {"success": True, "task": _task_summary(t)}


# ─────────────────────────────────────────────────────────────────────────────
# 🔬 (verify-then-chain) — background flow بعد از /complete توسط Claude
# ─────────────────────────────────────────────────────────────────────────────


def _normalize_remaining(items: List[Any]) -> List[str]:
    """نرمال‌سازی برای مقایسهٔ remaining_parts بین دو verify run."""
    out: List[str] = []
    for it in items or []:
        s = str(it or "").strip().lower()
        if s:
            out.append(s)
    return sorted(out)


def _remaining_unchanged(current: List[Any], task: Any, service: Any = None) -> bool:
    """🚨 (no-progress guard) — آیا remaining_parts این بار با remaining_parts
    دور قبل تقریباً یکسان است؟ اگر بله، Claude در دور قبل نتوانست هیچ
    آیتمی را تمام کند و ادامهٔ retry بی‌ثمر است.

    منبع snapshot: اول `task._last_remaining_snapshot` (lazy attr داخل
    process). اگر نبود (مثلاً پس از restart که این attr lost می‌شود)،
    از آخرین گزارش این تسک در `service.reports` می‌خوانیم — این persistent
    است. این تضمین می‌کند guard پس از restart هم کار کند.
    """
    cur = _normalize_remaining(current)
    prev = _normalize_remaining(
        getattr(task, "_last_remaining_snapshot", []) or []
    )
    if not prev and service is not None:
        # 🆕 (persistence fix) — از reports تاریخچه بخوان
        try:
            task_reports = [
                r for r in (getattr(service, "reports", None) or [])
                if getattr(r, "task_id", None) == getattr(task, "id", None)
            ]
            # آخرین گزارش (به ترتیب زمانی)
            task_reports.sort(
                key=lambda r: getattr(r, "generated_at", "") or "",
                reverse=True,
            )
            for r in task_reports[:5]:  # 5 گزارش اخیر را اسکن کن
                prev_candidate = getattr(r, "remaining_parts", None) or []
                if prev_candidate:
                    prev = _normalize_remaining(prev_candidate)
                    break
        except Exception:
            pass
    if not prev:
        return False  # دور اول — معیار مقایسه نداریم
    if not cur:
        return False  # حالا remaining خالی است → پیشرفت کرد
    # Jaccard ≥ 0.85 یعنی عملاً همان مجموعهٔ آیتم‌ها
    set_cur = set(cur)
    set_prev = set(prev)
    inter = len(set_cur & set_prev)
    union = len(set_cur | set_prev)
    if union == 0:
        return False
    jaccard = inter / union
    return jaccard >= 0.85


async def _verify_then_chain(
    *, task_id: str, watched_id: str, agent_id: str,
) -> None:
    """جریان کامل پس از تکمیل تسک توسط Claude Auto-Runner.

    1) verify_task() را اجرا می‌کند (deep verify در پس‌زمینه)
    2) بر اساس verification_status تسک:
       - done: lock آزاد + workflow بعدی trigger (chain-next)
       - partial/needs_clarification + retries < max:
         تسک به pending برگردانده می‌شود (با followup_prompt),
         lock آزاد + workflow trigger (که این تسک را دوباره می‌گیرد)
       - regressed یا max retries: TODO file + lock آزاد + chain-next
    """
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        logger.warning(f"_verify_then_chain: watched {watched_id} not found")
        return

    # 1) verify
    verify_result: Dict[str, Any] = {}
    try:
        from ...services.oversight_verifier import verify_task
        # include_runtime=True یعنی verify عمیق (با probe و Playwright)
        verify_result = await verify_task(
            task_id,
            triggered_by="claude_auto_runner_post_complete",
            include_runtime=True,
            verify_v6=True,
        )
        # verify_task return shape: {"task": <dict>, "report": ..., "final": ..., ...}
        _vs = (verify_result.get("task") or {}).get("verification_status", "?")
        logger.info(
            f"_verify_then_chain: verify done for task={task_id} → status={_vs}"
        )
    except Exception as _e:
        logger.exception(f"_verify_then_chain: verify_task crashed: {_e}")
        # هرچند verify crash کرد، باید lock را آزاد کنیم و chain-next بزنیم
        verify_result = {"verification_status": "error", "_crash": str(_e)}

    # 2) decide next action — تسک ممکن است در verifier mutate شده باشد
    task = next((x for x in service.tasks if x.id == task_id), None)
    if task is None:
        logger.warning(f"_verify_then_chain: task {task_id} not found post-verify")
        # release lock
        async with service._lock:
            service._release_verify_lock(watched_id)
            service._save_watched()
        return

    vstatus = getattr(task, "verification_status", None)
    # 🚨 (auto-runner loop fix) — raw verdict verifier در این run. اگر
    # status_val=done باشد ولی vstatus به streak guard خورده و "partial"
    # شده، retry فقط token هدر می‌دهد (Claude همه کارها را درست انجام
    # داده، فقط streak یک واحد کم است). با bypass جدید برای trigger های
    # claude_auto_runner_*، این مسیر هم تأیید می‌گیرد ولی به‌عنوان defense-
    # in-depth، اگر verifier از قبل گفته done این بار هم retry نمی‌کنیم.
    status_val_this_run = str(verify_result.get("status_val") or "").lower()
    max_retries = int(
        getattr(watched, "claude_runner_max_retries_per_task", 3) or 3
    )
    retries_done = int(getattr(task, "followup_round", 0) or 0)

    action = "chain_next"  # default
    if vstatus == "done" or status_val_this_run == "done":
        action = "chain_next"
    elif vstatus in ("partial", "needs_clarification"):
        # 🚨 (no-progress guard) — اگر این verify در مقایسه با verify
        # قبلی همان تسک هیچ پیشرفت معناداری نشان نداده، یعنی Claude در
        # دور قبل نتوانست remaining_parts را کم کند (احتمالاً نیازمند
        # credential، فعل دستی، یا اطلاعاتی است که در دسترسش نیست).
        # ادامهٔ retry فقط token می‌سوزاند و کاربر همان checklist را در
        # Telegram دوباره می‌بیند ("هی داره تسک تکراری انجام میده").
        # حالا مستقیماً TODO می‌نویسیم و archive می‌کنیم.
        cur_remaining = list(
            (verify_result.get("report") or {}).get("remaining_parts") or []
        )
        no_progress = (
            retries_done >= 1
            and _remaining_unchanged(cur_remaining, task, service)
        )
        if no_progress:
            logger.info(
                f"_verify_then_chain: no-progress detected for task={task_id} "
                f"(retries_done={retries_done}, remaining={len(cur_remaining)}). "
                f"Skipping retry — going straight to TODO."
            )
            action = "max_retries_todo"
        elif retries_done < max_retries:
            action = "retry_same"
        else:
            action = "max_retries_todo"
    elif vstatus == "regressed":
        action = "regressed_todo"
    elif vstatus == "error" or "_crash" in verify_result:
        # 🚨 (sweeper loop fix) — verify خراب شد (AI fail, balance، یا crash).
        # status را force به "error" کن تا sweeper این تسک را در
        # applied_externally_pending_verify ندیده و دوباره پیک نکند.
        try:
            async with service._lock:
                if task.verification_status != "error":
                    task.verification_status = "error"
                    task.updated_at = now_iso()
                    service._save_tasks()
        except Exception:
            pass
        action = "chain_next"  # verify crash → keep going (manual review)
    elif vstatus == "applied_externally_pending_verify":
        # 🚨 (sweeper loop fix CRITICAL) — این حالت یعنی verify_task اجرا
        # شد ولی نتوانست به یک verdict برسد (احتمالاً AI fail). اگر اینجا
        # status را عوض نکنیم، sweeper این تسک را در همان حالت می‌بیند و
        # برای همیشه دوباره verify-then-chain trigger می‌کند (loop).
        # کاربر این loop را گزارش داد: workflow های Cancelled به دلیل
        # chain_next های مکرر روی همان تسک.
        # status را force به "error" کن — این تسک باید توسط کاربر دستی
        # مرور و verify شود.
        logger.warning(
            f"_verify_then_chain: task={task_id} still in "
            f"applied_externally_pending_verify after verify run — "
            f"verify likely failed silently. Forcing status to 'error' "
            f"to prevent sweeper loop."
        )
        try:
            async with service._lock:
                task.verification_status = "error"
                task.updated_at = now_iso()
                service._save_tasks()
            vstatus = "error"
        except Exception:
            pass
        action = "chain_next"

    logger.info(
        f"_verify_then_chain: task={task_id} vstatus={vstatus} "
        f"retries={retries_done}/{max_retries} → action={action}"
    )

    # 3) apply action
    if action == "retry_same":
        # تسک را به pending برگردان تا workflow بعدی همین را بگیرد
        # 🚨 (no-progress guard) — snapshot remaining_parts روی task ذخیره
        # کن تا دور بعد بتوانیم تشخیص بدهیم پیشرفتی هست یا نه.
        _cur_remaining_for_snapshot = list(
            (verify_result.get("report") or {}).get("remaining_parts") or []
        )
        async with service._lock:
            task.external_status = "pending"
            task.status = "pending"
            task.external_locked_by = None
            task.external_lease_until = None
            # 🚨 (loop fix v2) — followup_round حالا در همین نقطه increment
            # می‌شود — یعنی فقط وقتی auto-runner واقعاً تسک را به pending
            # برمی‌گرداند برای retry. قبلاً در apply_followup_after_verify
            # increment می‌شد که از scheduler/manual/sweeper هم صدا زده
            # می‌شود — counter اشتباه بالا می‌رفت و workflow های جاری
            # cancel می‌شدند. حالا semantics درست: followup_round = تعداد
            # retry های واقعی auto-runner.
            task.followup_round = (task.followup_round or 0) + 1
            task.updated_at = now_iso()
            try:
                setattr(task, "_last_remaining_snapshot", _cur_remaining_for_snapshot)
            except Exception:
                pass
            service._save_tasks()
            service._recompute_execution_priorities(task)
            # release lock
            service._release_verify_lock(watched_id)
            service._save_watched()
        _emit_runner_notification(
            event="external_runner_retry_after_partial_verify",
            task=task,
            agent_id=agent_id,
            extra=f"verify={vstatus}. retry {retries_done + 1}/{max_retries}.",
        )
    elif action in ("max_retries_todo", "regressed_todo"):
        # TODO file + chain-next
        await _write_todo_for_task(
            task=task, watched=watched, verify_result=verify_result,
        )
        # 🚨 (loop-bug fix) — قبلاً فقط TODO نوشته می‌شد ولی task همچنان
        # pickable می‌ماند (status=awaiting_review در PICKABLE_STATUSES است).
        # پس chain_next با /next همان task را دوباره برمی‌داشت و بی‌نهایت
        # loop می‌شد. حالا task را archive می‌کنیم تا از /next حذف شود،
        # ولی با archived_reason جدا از success تا UI/گزارش‌ها بفهمند.
        from ...services.oversight_service import now_iso as _now_iso_abnd
        async with service._lock:
            task.archived = True
            task.archived_at = _now_iso_abnd()
            task.archived_reason = (
                "regressed" if action == "regressed_todo" else "max_retries"
            )
            task.status = "abandoned"  # نه done — به‌وضوح متمایز
            task.external_status = "abandoned"
            task.external_locked_by = None
            task.external_lease_until = None
            task.updated_at = _now_iso_abnd()
            service._save_tasks()
            service._release_verify_lock(watched_id)
            service._save_watched()
        _emit_runner_notification(
            event="external_runner_max_retries_or_regressed",
            task=task,
            agent_id=agent_id,
            extra=(
                f"verify={vstatus}, retries={retries_done}/{max_retries}.\n"
                f"تسک با علت `{task.archived_reason}` آرشیو شد و در TO-DO/ ثبت گردید.\n"
                f"سراغ تسک بعدی می‌رویم."
            ),
        )
    else:
        # chain_next (default + done)
        async with service._lock:
            service._release_verify_lock(watched_id)
            service._save_watched()

    # 4) trigger workflow بعدی
    #    - retry_same: target_task_id=task_id → Claude همین تسک را اجرا کند
    #    - chain_next/max_retries_todo/regressed_todo: target_task_id=None →
    #      Claude /next می‌زند و اولین تسک pickable را برمی‌دارد
    target_for_dispatch = task_id if action == "retry_same" else None
    # 🆕 (manual single-task) — برای retry روی همان تسک، force=True بزنیم تا
    # حتی اگر claude_runner_enabled=False باشد (سناریوی manual single-task
    # trigger)، بتوانیم همان تسک را دوباره اجرا کنیم. برای chain-next این کار
    # را نمی‌کنیم — اگر کاربر auto-runner را روشن نکرده، نباید تسک‌های دیگر را
    # خودبه‌خود اجرا کنیم.
    force_dispatch = action == "retry_same"
    try:
        from ...services.oversight_service import get_github_token
        from ...services.claude_runner_bootstrap import (
            pick_model_for_task,
            trigger_workflow_dispatch,
        )
        gh_token = get_github_token()
        if gh_token:
            # 🤖 (dynamic model) — برای retry روی همان تسک، tier بر اساس
            # محتوای آن تسک. برای chain-next که target_task_id خالی است،
            # tier بر اساس همان تسک فعلی (که verify شد) — منطق این است
            # که تسک بعدی در صف معمولاً مشابه است؛ اگر متفاوت بود، Claude
            # CLI همچنان alias `sonnet` را به آخرین Sonnet route می‌کند.
            _picked_model = await pick_model_for_task(
                task, consumer_key="claude_auto_runner",
            ) if task else None
            disp = await trigger_workflow_dispatch(
                watched,
                gh_token=gh_token,
                target_task_id=target_for_dispatch,
                force=force_dispatch,
                claude_model=_picked_model,
            )
            logger.info(
                f"_verify_then_chain: dispatched workflow after action={action}, "
                f"target={target_for_dispatch or 'next'} force={force_dispatch} → {disp}"
            )
    except Exception as _disp_e:
        logger.warning(f"_verify_then_chain: dispatch failed: {_disp_e}")


async def _write_todo_for_task(
    *, task: Any, watched: Any, verify_result: Dict[str, Any],
) -> None:
    """نوشتن فایل TO-DO/todo-task-{id}.md به ریپوی watched.

    این مسیر فقط برای تسک‌هایی است که Claude نتوانست در سقف retry تمام کند.
    فایل باید *self-contained* باشد — کاربر با خواندن همین فایل بفهمد دقیقاً
    چه چیزی مانده و چه قدم‌هایی باید بردارد، بدون نیاز به مراجعه به پنل.
    """
    try:
        from ...services.github_pr_service import get_github_pr_service
        from ...services.prompt_github_sync import (
            _resolve_repo_and_branch, _commit_message,
        )
        from ...services.oversight_service import get_github_token
        from ...services.oversight_verifier import _ac_text_of
        resolved = _resolve_repo_and_branch(watched)
        if not resolved:
            return
        owner, repo, branch = resolved
        token = get_github_token()
        if not token:
            return
        short_id = (task.id or "")[:8]
        path = f"TO-DO/todo-task-{short_id}.md"

        # ------------------------------------------------------------------
        # Pull rich data from verify_result
        # ------------------------------------------------------------------
        vstatus = getattr(task, "verification_status", "?")
        retries = getattr(task, "followup_round", 0) or 0
        archived_reason = getattr(task, "archived_reason", None) or "max_retries"

        report = verify_result.get("report") or {}
        done_parts: List[str] = list(report.get("done_parts") or [])
        remaining_parts: List[str] = list(report.get("remaining_parts") or [])
        next_actions: List[str] = list(report.get("next_actions") or [])
        confidence = float(report.get("confidence_score") or 0.0)
        evidence = report.get("evidence") or {}
        report_id = report.get("id") or getattr(
            task, "last_verification_report_id", None
        )
        verifier_model = report.get("model_id") or "—"

        # Extract summary text from raw_response (verifier's narrative).
        # OversightReport doesn't have a `summary` field directly, but the
        # JSON inside raw_response has one — pull it for human context.
        summary_text = ""
        try:
            import re as _re
            raw = str(report.get("raw_response") or "")
            m = _re.search(
                r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', raw
            )
            if m:
                summary_text = m.group(1).replace('\\n', '\n').replace('\\"', '"')
        except Exception:
            summary_text = ""
        if not summary_text:
            summary_text = (getattr(task, "last_summary", "") or "").strip()

        # Original task context
        title = (getattr(task, "title", "") or "").strip()
        raw_idea = (getattr(task, "raw_idea", "") or "").strip()
        original_prompt = (getattr(task, "prompt", "") or "").strip()
        acs = list(getattr(task, "acceptance_criteria", []) or [])
        ac_texts = [t for t in (_ac_text_of(a) for a in acs) if t]
        followup_prompt = (getattr(task, "followup_prompt", "") or "").strip()

        # Evidence breakdown
        ev_commits = list(evidence.get("commits") or []) if isinstance(evidence, dict) else []
        ev_files = list(evidence.get("files") or []) if isinstance(evidence, dict) else []
        ev_issues = list(evidence.get("issues") or []) if isinstance(evidence, dict) else []

        # ------------------------------------------------------------------
        # Build markdown
        # ------------------------------------------------------------------
        reason_fa = {
            "max_retries": "Claude به سقف retry رسید بدون اینکه verify=done شود",
            "regressed":   "verify تشخیص داد تسک نسبت به وضعیت قبلی regress کرده",
        }.get(archived_reason, f"archived_reason={archived_reason}")

        lines: List[str] = [
            f"# TODO — Task {short_id} (نیاز به تکمیل دستی)",
            "",
            f"> **{title}**",
            "",
            "## 🔎 خلاصه وضعیت",
            "",
            f"- **task_id**: `{task.id}`",
            f"- **repo**: `{watched.repo_full_name}`",
            f"- **verification_status**: `{vstatus}`",
            f"- **archived_reason**: `{archived_reason}` — {reason_fa}",
            f"- **retries_done**: {retries}",
            f"- **verifier confidence**: {confidence:.2f}",
            f"- **verifier model**: `{verifier_model}`",
            f"- **report_id**: `{report_id or '—'}`",
            f"- **created_at**: {now_iso()}",
            "",
        ]

        # --- Headline section: what remains (the user's main question) ---
        lines += [
            "## 🚧 چه چیزی باقی مانده (مهم‌ترین بخش)",
            "",
        ]
        if remaining_parts:
            lines += [f"- [ ] {item}" for item in remaining_parts]
        else:
            lines += [
                "_verifier هیچ remaining_part صریحی برنگرداند._ "
                "احتمالاً verify نتوانست clear verdict بدهد — به Acceptance "
                "Criteria پایین مراجعه و دستی چک کنید کدام AC هنوز satisfy نیست.",
            ]
        lines.append("")

        # --- Concrete next actions (verifier's suggestions) ---
        if next_actions:
            lines += [
                "## 👉 قدم‌های بعدی پیشنهادی (از verifier)",
                "",
            ]
            lines += [f"{i+1}. {a}" for i, a in enumerate(next_actions)]
            lines.append("")

        # --- What Claude DID finish (so user knows where to start) ---
        if done_parts:
            lines += [
                "## ✅ چه چیزی Claude انجام داد",
                "",
            ]
            lines += [f"- [x] {item}" for item in done_parts]
            lines.append("")

        # --- Verifier narrative ---
        if summary_text:
            lines += [
                "## 📝 خلاصهٔ verifier",
                "",
                summary_text.strip()[:2000],
                "",
            ]

        # --- Full acceptance criteria for reference ---
        if ac_texts:
            lines += [
                "## 📋 Acceptance Criteria (مرجع کامل)",
                "",
                "این لیست معیار done شدن تسک است — هر آیتمی که هنوز satisfy نیست",
                "باید توسط انسان تکمیل شود.",
                "",
            ]
            lines += [f"- {t}" for t in ac_texts]
            lines.append("")

        # --- Evidence: what the verifier saw ---
        if ev_commits or ev_files or ev_issues:
            lines += ["## 🔬 Evidence که verifier پیدا کرد", ""]
            if ev_commits:
                lines.append("**Commits:**")
                lines += [f"- `{c}`" for c in ev_commits[:20]]
                lines.append("")
            if ev_files:
                lines.append("**Files lams شده:**")
                lines += [f"- `{f}`" for f in ev_files[:30]]
                lines.append("")
            if ev_issues:
                lines.append("**Issues:**")
                lines += [f"- {i}" for i in ev_issues[:20]]
                lines.append("")

        # --- Original task description (so file is self-contained) ---
        if raw_idea:
            lines += [
                "## 💡 ایدهٔ اصلی تسک",
                "",
                raw_idea[:1500],
                "",
            ]
        if original_prompt and original_prompt != raw_idea:
            excerpt = original_prompt[:2000]
            if len(original_prompt) > 2000:
                excerpt += "\n\n_[truncated — full prompt در پنل]_"
            lines += [
                "## 📜 پرامپت اصلی (excerpt)",
                "",
                "```",
                excerpt,
                "```",
                "",
            ]

        # --- Last regenerated follow-up prompt (ready to copy/paste) ---
        if followup_prompt:
            lines += [
                "## 🔁 آخرین followup prompt تولیدشده",
                "",
                "_می‌توانید این را در یک agent جدید paste کنید تا کار را ادامه دهد._",
                "",
                "```",
                followup_prompt[:3000],
                "```",
                "",
            ]

        # --- Footer ---
        lines += [
            "---",
            "",
            f"_این فایل توسط Claude Auto-Runner تولید شده است. تسک با حالت_ "
            f"`{archived_reason}` _آرشیو شده و دیگر به‌صورت خودکار pickup نمی‌شود._",
        ]

        content = "\n".join(lines)
        pr = get_github_pr_service()
        await pr.create_or_update_file(
            owner=owner,
            repo=repo,
            path=path,
            content=content,
            message=_commit_message(
                f"todo: task {short_id} needs manual completion",
                target_repo=watched.repo_full_name,
            ),
            branch=branch,
            token=token,
        )
        logger.info(f"_write_todo_for_task: wrote {path} for task {task.id}")
    except Exception as _e:
        logger.warning(f"_write_todo_for_task failed: {_e}")


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
    # 🆕 Telegram feedback: ❌ شکست
    _emit_runner_notification(
        event="external_runner_failed",
        task=t,
        agent_id=payload.agent_id,
        extra=f"خطا: {(payload.error or '')[:500]}\n"
              f"retry: {'بله' if payload.retry else 'خیر'}",
    )
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
