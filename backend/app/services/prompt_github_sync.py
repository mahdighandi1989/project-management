# -*- coding: utf-8 -*-
"""
🔄 Prompt ↔ GitHub Sync
سرویس همگام‌سازی پرامپت تسک‌ها به ریپوی هر پروژه‌ی تحت نظارت.

ساختار در ریپوی هدف:
  prompt/
    task-{id}.md          ← فایل اصلی تسک
    archive/
      task-{id}.md        ← تسک‌های آرشیوشده
    _index.json           ← لیست مرتب بر اساس execution_priority (برای ابزار خارجی)

این ماژول stateless است — همهٔ متادیتا روی خود تسک نگهداری می‌شود
(github_prompt_path, github_prompt_sha, …).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .github_pr_service import get_github_pr_service

logger = logging.getLogger(__name__)


PROMPT_DIR = "prompt"
ARCHIVE_DIR = "prompt/archive"
INDEX_PATH = "prompt/_index.json"

# نگاشت priority متنی → عدد پایه (کوچک‌تر = اولویت بالاتر)
PRIORITY_BASE = {
    "critical": 1000,
    "high": 2000,
    "medium": 3000,
    "low": 4000,
}

# ابزار خارجی نباید تسک‌های done/cancelled/archived رو ببینه
PICKABLE_STATUSES = {"pending", "awaiting_review"}
PICKABLE_EXTERNAL_STATUSES = {"pending", "failed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_path(task_id: str, archived: bool = False) -> str:
    folder = ARCHIVE_DIR if archived else PROMPT_DIR
    return f"{folder}/task-{task_id}.md"


def _parse_repo(repo_full_name: str) -> Tuple[str, str]:
    if not repo_full_name or "/" not in repo_full_name:
        return ("", "")
    owner, _, repo = repo_full_name.partition("/")
    return (owner.strip(), repo.strip())


def compute_execution_priority(task: Any) -> int:
    """محاسبهٔ اولویت اجرا برای یک تسک.

    پایه = PRIORITY_BASE[priority]
    تعدیل:
      - pinned          → −500
      - critical+blocker → −200
      - failed قبلی     → +50 × external_attempts (تسک‌های repeatedly-fail عقب می‌افتند)
      - awaiting_review → +300 (manual gating)
    """
    base = PRIORITY_BASE.get(getattr(task, "priority", "medium"), 3000)
    if getattr(task, "pinned", False):
        base -= 500
    if getattr(task, "status", "") == "awaiting_review":
        base += 300
    attempts = int(getattr(task, "external_attempts", 0) or 0)
    if attempts > 0:
        base += min(attempts * 50, 500)
    # tie-breaker با created_at به‌صورت صعودی
    try:
        ts = datetime.fromisoformat(
            (getattr(task, "created_at", "") or "").replace("Z", "+00:00")
        ).timestamp()
        # اضافه‌کردن secs/1000 → کم‌اهمیت ولی deterministic
        base += int(ts / 1000) % 1000
    except Exception:
        pass
    return int(base)


def format_prompt_markdown(task: Any) -> str:
    """رندر فایل markdown نهایی برای یک تسک.

    شامل front-matter YAML + بدنهٔ markdown با کامل‌ترین جزئیات (بدون summarization).
    """
    def _yaml_escape(s: str) -> str:
        if s is None:
            return ""
        s = str(s).replace('"', '\\"').replace("\n", " ")
        return s

    ac_list = getattr(task, "acceptance_criteria", []) or []
    ac_lines: List[str] = []
    for i, ac in enumerate(ac_list, 1):
        if isinstance(ac, dict):
            text = ac.get("text") or ac.get("description") or ""
            method = ac.get("verify_method", "")
            ac_lines.append(f"{i}. {text}" + (f" _(verify: {method})_" if method else ""))
        elif isinstance(ac, str):
            ac_lines.append(f"{i}. {ac}")

    steps = getattr(task, "task_steps", []) or []
    step_lines: List[str] = []
    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict):
            continue
        title = st.get("title", "")
        scope = st.get("scope", "")
        status = st.get("status", "pending")
        completion = st.get("completion_pct", 0)
        step_lines.append(f"### Step {i}: {title}")
        step_lines.append(f"**Status:** `{status}` ({completion}%)")
        if scope:
            step_lines.append(f"**Scope:** {scope}")
        raw_excerpt = st.get("raw_excerpt", "")
        if raw_excerpt:
            step_lines.append("**Excerpt:**")
            step_lines.append("```")
            step_lines.append(raw_excerpt)
            step_lines.append("```")
        step_lines.append("")

    target_files = getattr(task, "target_files", []) or []
    tags = getattr(task, "tags", []) or []

    fm: List[str] = [
        "---",
        f"task_id: \"{task.id}\"",
        f"title: \"{_yaml_escape(task.title)}\"",
        f"type: \"{task.type}\"",
        f"priority: \"{task.priority}\"",
        f"execution_priority: {compute_execution_priority(task)}",
        f"status: \"{task.status}\"",
        f"external_status: \"{getattr(task, 'external_status', 'pending')}\"",
        f"verification_status: \"{task.verification_status}\"",
        f"watched_id: \"{task.watched_id or ''}\"",
        f"project: \"{task.project_full_name}\"",
        f"created_at: \"{task.created_at}\"",
        f"updated_at: \"{task.updated_at}\"",
    ]
    if getattr(task, "archived", False):
        fm.append(f"archived: true")
        if task.archived_at:
            fm.append(f"archived_at: \"{task.archived_at}\"")
    if getattr(task, "deadline", None):
        fm.append(f"deadline: \"{task.deadline}\"")
    if tags:
        fm.append("tags: [" + ", ".join(f"\"{_yaml_escape(t)}\"" for t in tags) + "]")
    if target_files:
        fm.append("target_files:")
        for tf in target_files[:50]:
            fm.append(f"  - \"{_yaml_escape(tf)}\"")
    fm.append("---")
    fm.append("")
    fm.append(f"# {task.title}")
    fm.append("")
    if task.raw_idea:
        fm.append("## Raw Idea")
        fm.append("")
        fm.append(task.raw_idea)
        fm.append("")
    fm.append("## Prompt")
    fm.append("")
    fm.append(task.prompt or "")
    fm.append("")
    if ac_lines:
        fm.append("## Acceptance Criteria")
        fm.append("")
        fm.extend(ac_lines)
        fm.append("")
    if step_lines:
        fm.append("## Task Steps")
        fm.append("")
        fm.extend(step_lines)
    followup = getattr(task, "followup_prompt", "")
    if followup:
        fm.append("## Followup Prompt")
        fm.append("")
        fm.append(followup)
        fm.append("")

    return "\n".join(fm).rstrip() + "\n"


def _resolve_repo_and_branch(watched: Any) -> Optional[Tuple[str, str, str]]:
    """از watched project: (owner, repo, branch). None اگر فاقد config باشد."""
    if watched is None:
        return None
    if not getattr(watched, "prompt_sync_enabled", True):
        return None
    repo_full = getattr(watched, "repo_full_name", "") or ""
    owner, repo = _parse_repo(repo_full)
    if not owner or not repo:
        return None
    branch = (
        getattr(watched, "prompt_sync_branch", None)
        or getattr(watched, "default_branch", None)
        or "main"
    )
    return (owner, repo, branch)


async def sync_task_to_github(task: Any, watched: Any, *, token: str) -> Dict[str, Any]:
    """ساخت یا آپدیت فایل پرامپت تسک در ریپوی پروژه.

    اگر `task.archived` باشد، فایل به فولدر archive/ منتقل می‌شود.
    این تابع state تسک را در محل تغییر می‌دهد:
      github_prompt_path, github_prompt_sha, github_prompt_synced_at,
      github_prompt_archived, github_prompt_last_error
    Returns: {"success": bool, "path": str, "error": str?}
    """
    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {"success": False, "error": "sync_disabled_or_no_repo", "skipped": True}
    if not token:
        return {"success": False, "error": "no_github_token", "skipped": True}
    owner, repo, branch = resolved

    archived = bool(getattr(task, "archived", False))
    desired_path = _file_path(task.id, archived=archived)
    prior_path = getattr(task, "github_prompt_path", None)

    pr = get_github_pr_service()

    # اگر مسیر قبلی موجود است و با مسیر فعلی فرق دارد (آرشیو/آن‌آرشیو شد) →
    # اول فایل قبلی را حذف کن
    if prior_path and prior_path != desired_path:
        del_res = await pr.delete_file(
            owner=owner,
            repo=repo,
            path=prior_path,
            message=f"chore(prompt): move task {task.id} ({'archive' if archived else 'unarchive'})",
            branch=branch,
            token=token,
            sha=getattr(task, "github_prompt_sha", None),
        )
        if not del_res.get("success") and not del_res.get("not_found"):
            # خطای حذف فقط لاگ می‌شود — فایل جدید را به هر حال می‌نویسیم
            logger.warning(
                f"prompt-sync: delete old path failed task={task.id} "
                f"path={prior_path} err={del_res.get('error')}"
            )

    body = format_prompt_markdown(task)
    upsert = await pr.create_or_update_file(
        owner=owner,
        repo=repo,
        path=desired_path,
        content=body,
        message=f"chore(prompt): sync task {task.id} — {task.title[:80]}",
        branch=branch,
        token=token,
    )
    if upsert.get("success"):
        task.github_prompt_path = desired_path
        task.github_prompt_sha = upsert.get("sha")
        task.github_prompt_synced_at = _now_iso()
        task.github_prompt_archived = archived
        task.github_prompt_last_error = None
        return {"success": True, "path": desired_path}
    err = upsert.get("error", "unknown")
    task.github_prompt_last_error = err[:500]
    return {"success": False, "error": err, "path": desired_path}


async def delete_task_from_github(task: Any, watched: Any, *, token: str) -> Dict[str, Any]:
    """حذف کامل فایل پرامپت از ریپو (هنگام delete_task)."""
    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {"success": False, "skipped": True}
    if not token:
        return {"success": False, "skipped": True}
    owner, repo, branch = resolved
    path = getattr(task, "github_prompt_path", None)
    if not path:
        return {"success": True, "skipped": True}
    pr = get_github_pr_service()
    res = await pr.delete_file(
        owner=owner,
        repo=repo,
        path=path,
        message=f"chore(prompt): delete task {task.id}",
        branch=branch,
        token=token,
        sha=getattr(task, "github_prompt_sha", None),
    )
    if res.get("success") or res.get("not_found"):
        task.github_prompt_path = None
        task.github_prompt_sha = None
        task.github_prompt_synced_at = None
    return res


async def rebuild_project_index(
    tasks: List[Any], watched: Any, *, token: str
) -> Dict[str, Any]:
    """بازسازی prompt/_index.json با لیست مرتب بر اساس execution_priority.

    این فایل توسط ابزار خارجی (Cloud Code) خوانده می‌شود تا بداند به ترتیب چه
    کارهایی را برداشت کند. فقط تسک‌های pickable را شامل می‌شود.
    """
    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {"success": False, "skipped": True}
    if not token:
        return {"success": False, "skipped": True}
    owner, repo, branch = resolved

    pickable: List[Dict[str, Any]] = []
    for t in tasks:
        if getattr(t, "watched_id", None) != watched.id:
            continue
        if getattr(t, "archived", False):
            continue
        status = getattr(t, "status", "")
        if status not in PICKABLE_STATUSES:
            continue
        ext_status = getattr(t, "external_status", "pending") or "pending"
        if ext_status not in PICKABLE_EXTERNAL_STATUSES:
            continue
        pickable.append({
            "task_id": t.id,
            "title": t.title,
            "priority": t.priority,
            "execution_priority": compute_execution_priority(t),
            "status": status,
            "external_status": ext_status,
            "path": getattr(t, "github_prompt_path", _file_path(t.id)),
            "external_attempts": getattr(t, "external_attempts", 0),
            "created_at": getattr(t, "created_at", ""),
            "updated_at": getattr(t, "updated_at", ""),
        })

    pickable.sort(key=lambda x: (x["execution_priority"], x["created_at"]))
    index_body = {
        "version": 1,
        "generated_at": _now_iso(),
        "project": getattr(watched, "repo_full_name", ""),
        "watched_id": watched.id,
        "total": len(pickable),
        "tasks": pickable,
    }
    content = json.dumps(index_body, ensure_ascii=False, indent=2)
    pr = get_github_pr_service()
    upsert = await pr.create_or_update_file(
        owner=owner,
        repo=repo,
        path=INDEX_PATH,
        content=content,
        message=f"chore(prompt): rebuild index ({len(pickable)} tasks)",
        branch=branch,
        token=token,
    )
    return upsert


async def safe_sync_task(task: Any, watched: Any, *, token: str) -> None:
    """wrapper امن — هیچ‌گاه exception نمی‌اندازد. برای fire-and-forget."""
    try:
        await sync_task_to_github(task, watched, token=token)
    except Exception as e:
        logger.warning(f"prompt-sync: safe_sync_task failed task={task.id}: {e}")
        try:
            task.github_prompt_last_error = str(e)[:500]
        except Exception:
            pass


async def safe_rebuild_index(
    tasks: List[Any], watched: Any, *, token: str
) -> None:
    try:
        await rebuild_project_index(tasks, watched, token=token)
    except Exception as e:
        logger.warning(
            f"prompt-sync: safe_rebuild_index failed watched={watched.id}: {e}"
        )


async def safe_delete_task(task: Any, watched: Any, *, token: str) -> None:
    try:
        await delete_task_from_github(task, watched, token=token)
    except Exception as e:
        logger.warning(f"prompt-sync: safe_delete_task failed task={task.id}: {e}")
