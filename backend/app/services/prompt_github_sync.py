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

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .github_pr_service import get_github_pr_service
from .oversight_service import now_iso

logger = logging.getLogger(__name__)


PROMPT_DIR = "prompt"
ARCHIVE_DIR = "prompt/archive"
INDEX_PATH = "prompt/_index.json"

# 🆕 (deploy-loop prevention) marker — به‌صورت conditional اعمال می‌شود.
# - `[skip render]` همیشه (روی ریپوهای غیر-backend هم harmless است)
# - `[skip ci]` فقط روی ریپوی self-backend (که در PROMPT_SYNC_EXCLUDE_REPOS است)
# علت: روی ریپوهای دیگر **می‌خواهیم** GitHub Actions trigger شود (به‌خصوص
# workflow «Claude Auto-Runner» که هدفش دقیقاً اجرا روی push تسک‌های جدید
# به prompt/ است). اگر `[skip ci]` همه‌جا اعمال می‌شد، آن workflow هرگز
# trigger نمی‌گرفت.
SKIP_RENDER_MARKER = "[skip render]"
SKIP_CI_MARKER = "[skip render][skip ci]"


def _commit_message(verb: str, *, details: str = "", target_repo: str = "") -> str:
    """commit message یکپارچه با marker مناسب.

    اگر `target_repo` در PROMPT_SYNC_EXCLUDE_REPOS باشد (یعنی ریپوی خودِ
    backend)، marker کامل `[skip render][skip ci]` گذاشته می‌شود تا
    deploy loop نشود. در غیر این صورت فقط `[skip render]` گذاشته می‌شود
    تا Claude Auto-Runner workflow بتواند trigger شود.
    """
    base = f"chore(prompt): {verb}"
    if details:
        base = f"{base} — {details}"
    repo_lc = (target_repo or "").strip().lower()
    is_self = bool(repo_lc and repo_lc in _excluded_repos())
    marker = SKIP_CI_MARKER if is_self else SKIP_RENDER_MARKER
    return f"{base}\n\n{marker}"


# repo های مستثنی (مثلاً backend خودش) — از env var
# PROMPT_SYNC_EXCLUDE_REPOS خوانده می‌شود (comma-separated).
def _excluded_repos() -> set:
    raw = os.environ.get("PROMPT_SYNC_EXCLUDE_REPOS", "").strip()
    if not raw:
        return set()
    return {r.strip().lower() for r in raw.split(",") if r.strip()}

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


def _file_path(task_id: str, archived: bool = False) -> str:
    folder = ARCHIVE_DIR if archived else PROMPT_DIR
    return f"{folder}/task-{task_id}.md"


def _parse_repo(repo_full_name: str) -> Tuple[str, str]:
    """تجزیه `owner/repo` — حذف `.git` در انتها (سازگار با _parse_repo_url)."""
    if not repo_full_name:
        return ("", "")
    s = repo_full_name.replace(".git", "").strip("/")
    if "/" not in s:
        return ("", "")
    owner, _, repo = s.partition("/")
    return (owner.strip(), repo.strip())


# ────────────────────────────────────────────────────────────────────────
# Per-repo write-serialization + index-debounce
# ────────────────────────────────────────────────────────────────────────
# GitHub Contents API ضد concurrent writes روی یک branch است (409 sha
# mismatch). برای جلوگیری از write-storm، نوشتن روی هر repo را با یک
# asyncio.Lock مخصوص همان repo سریالیزه می‌کنیم.
_repo_locks: Dict[str, asyncio.Lock] = {}
_index_debounce_tasks: Dict[str, asyncio.Task] = {}
INDEX_DEBOUNCE_SECONDS = 60.0  # 🛡 (workflow trigger leak fix) — افزایش از 2 به 60
# بدون این، هر تغییر کوچک تسک یک commit/push روی _index.json تولید می‌کرد
# و چون workflow Claude Auto-Runner روی همین trigger می‌شود، در یک روز
# 2000 دقیقهٔ سهمیهٔ ماهانهٔ GitHub Actions تمام می‌شد (بدون اینکه حتی یک
# تسک واقعاً اجرا شود — هر run توسط run بعدی cancel می‌شد).


def _get_repo_lock(owner: str, repo: str, branch: str) -> asyncio.Lock:
    key = f"{owner}/{repo}@{branch}"
    lock = _repo_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _repo_locks[key] = lock
    return lock


def compute_execution_priority(task: Any) -> int:
    """محاسبهٔ اولویت اجرا برای یک تسک (کوچک‌تر = اولویت بالاتر).

    پایه = PRIORITY_BASE[priority]
    تعدیل:
      - pinned          → −500
      - awaiting_review → +300 (نیاز به گیت دستی)
      - failed قبلی     → +50 × external_attempts (تسک‌های repeatedly-fail عقب می‌افتند)

    Tie-breaker بر اساس created_at توسط callerها (به‌صورت secondary sort key)
    اعمال می‌شود — اینجا فقط priority پایه برمی‌گردد.
    """
    base = PRIORITY_BASE.get(getattr(task, "priority", "medium"), 3000)
    if getattr(task, "pinned", False):
        base -= 500
    if getattr(task, "status", "") == "awaiting_review":
        base += 300
    attempts = int(getattr(task, "external_attempts", 0) or 0)
    if attempts > 0:
        base += min(attempts * 50, 500)
    return int(base)


def format_prompt_markdown(task: Any) -> str:
    """رندر فایل markdown نهایی برای یک تسک.

    شامل front-matter YAML (با yaml.safe_dump برای امن بودن در برابر
    backslash/CRLF/unicode/multiline) + بدنهٔ markdown با کامل‌ترین جزئیات
    (بدون summarization).
    """
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

    fm_data: Dict[str, Any] = {
        "task_id": task.id,
        "title": task.title or "",
        "type": task.type,
        "priority": task.priority,
        "execution_priority": (
            getattr(task, "execution_priority", None)
            or compute_execution_priority(task)
        ),
        "status": task.status,
        "external_status": getattr(task, "external_status", "pending"),
        "verification_status": task.verification_status,
        "watched_id": task.watched_id or "",
        "project": task.project_full_name,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
    if getattr(task, "archived", False):
        fm_data["archived"] = True
        if task.archived_at:
            fm_data["archived_at"] = task.archived_at
    if getattr(task, "deadline", None):
        fm_data["deadline"] = task.deadline
    if tags:
        fm_data["tags"] = list(tags)
    if target_files:
        fm_data["target_files"] = list(target_files[:50])

    fm_yaml = yaml.safe_dump(
        fm_data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10_000,
    )

    body_parts: List[str] = ["---", fm_yaml.rstrip(), "---", "", f"# {task.title}", ""]
    if task.raw_idea:
        body_parts += ["## Raw Idea", "", task.raw_idea, ""]
    body_parts += ["## Prompt", "", task.prompt or "", ""]
    if ac_lines:
        body_parts += ["## Acceptance Criteria", ""] + ac_lines + [""]
    if step_lines:
        body_parts += ["## Task Steps", ""] + step_lines
    followup = getattr(task, "followup_prompt", "")
    if followup:
        body_parts += ["## Followup Prompt", "", followup, ""]

    return "\n".join(body_parts).rstrip() + "\n"


def _resolve_repo_and_branch(watched: Any) -> Optional[Tuple[str, str, str]]:
    """از watched project: (owner, repo, branch). None اگر فاقد config باشد.

    اگر repo در PROMPT_SYNC_EXCLUDE_REPOS باشد، None برمی‌گرداند تا از
    deploy loop (backend writing to its own repo) جلوگیری شود.
    """
    if watched is None:
        return None
    if not getattr(watched, "prompt_sync_enabled", True):
        return None
    repo_full = getattr(watched, "repo_full_name", "") or ""
    if repo_full.strip().lower() in _excluded_repos():
        return None
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

    Writes روی همان repo با asyncio.Lock سریالیزه می‌شوند تا از 409 های
    concurrent جلوگیری شود.
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

    async with _get_repo_lock(owner, repo, branch):
        # اگر مسیر قبلی موجود است و با مسیر فعلی فرق دارد (آرشیو/آن‌آرشیو شد) →
        # اول فایل قبلی را حذف کن
        if prior_path and prior_path != desired_path:
            del_res = await pr.delete_file(
                owner=owner,
                repo=repo,
                path=prior_path,
                message=_commit_message(
                    f"move task {task.id}",
                    details=("archive" if archived else "unarchive"),
                    target_repo=watched.repo_full_name,
                ),
                branch=branch,
                token=token,
                sha=getattr(task, "github_prompt_sha", None),
            )
            if not del_res.get("success") and not del_res.get("not_found"):
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
            message=_commit_message(
                f"sync task {task.id}", details=task.title[:80],
                target_repo=watched.repo_full_name,
            ),
            branch=branch,
            token=token,
        )

    if upsert.get("success"):
        task.github_prompt_path = desired_path
        task.github_prompt_sha = upsert.get("sha")
        task.github_prompt_synced_at = now_iso()
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
    async with _get_repo_lock(owner, repo, branch):
        res = await pr.delete_file(
            owner=owner,
            repo=repo,
            path=path,
            message=_commit_message(
                f"delete task {task.id}",
                target_repo=watched.repo_full_name,
            ),
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
        # priority cached را ترجیح بده تا compute مجدد نکنیم
        eprio = getattr(t, "execution_priority", None) or compute_execution_priority(t)
        pickable.append({
            "task_id": t.id,
            "title": t.title,
            "priority": t.priority,
            "execution_priority": eprio,
            "status": status,
            "external_status": ext_status,
            "path": getattr(t, "github_prompt_path", _file_path(t.id)),
            "external_attempts": getattr(t, "external_attempts", 0),
            # 🛡 (workflow trigger leak fix) — `created_at` و `updated_at`
            # از index حذف شدند چون با هر تغییر کوچک تسک (verifier،
            # AC enrichment، …) عوض می‌شدند و content-hash فایل را
            # متفاوت می‌کردند → commit جدید → workflow trigger هدررو.
        })

    pickable.sort(key=lambda x: (x["execution_priority"], x["task_id"]))
    index_body = {
        "version": 1,
        # 🛡 `generated_at` حذف شد — قبلاً each rebuild یک timestamp
        # جدید می‌گرفت، حتی اگر هیچ تسکی واقعاً تغییر نکرده بود. این
        # باعث می‌شد content فایل همیشه متفاوت باشد → commit جدید →
        # workflow trigger بی‌جا.
        "project": getattr(watched, "repo_full_name", ""),
        "watched_id": watched.id,
        "total": len(pickable),
        "tasks": pickable,
    }
    content = json.dumps(index_body, ensure_ascii=False, indent=2)
    pr = get_github_pr_service()
    async with _get_repo_lock(owner, repo, branch):
        # 🛡 (workflow trigger leak fix) — قبل از push، محتوای فعلی فایل
        # را بخوان و فقط در صورت تغییر واقعی push کن. این جلوی هر
        # commit بی‌فایده (و در نتیجه workflow trigger بی‌فایده) را می‌گیرد.
        try:
            current = await pr.get_file_content(
                owner=owner, repo=repo, path=INDEX_PATH,
                branch=branch, token=token,
            )
            if current.get("success") and current.get("content") == content:
                logger.debug(
                    f"rebuild_project_index: skip push for {owner}/{repo} — "
                    f"content unchanged ({len(pickable)} tasks)"
                )
                return {"success": True, "skipped": True, "reason": "no_change"}
        except Exception as _diff_e:
            # اگر چک diff fail شد، ادامه بده و push کن — بهتر از crash
            logger.debug(f"rebuild_project_index: diff check failed: {_diff_e}")

        upsert = await pr.create_or_update_file(
            owner=owner,
            repo=repo,
            path=INDEX_PATH,
            content=content,
            message=_commit_message(
                "rebuild index", details=f"{len(pickable)} tasks",
                target_repo=watched.repo_full_name,
            ),
            branch=branch,
            token=token,
        )
    return upsert


async def safe_sync_task(
    task: Any, watched: Any, *, token: str, on_done: Optional[callable] = None,
) -> None:
    """wrapper امن — هیچ‌گاه exception نمی‌اندازد. برای fire-and-forget.

    on_done: اختیاری — پس از موفقیت (یا شکست) صدا زده می‌شود تا state تسک
    (که در همان task object تغییر کرده) را در دیسک ذخیره کنیم.
    """
    repo = getattr(watched, "repo_full_name", "?")
    task_id_short = (getattr(task, "id", "?") or "?")[:8]
    try:
        result = await sync_task_to_github(task, watched, token=token)
        if result.get("success"):
            logger.info(
                f"prompt-sync ✓ task={task_id_short} repo={repo} "
                f"path={result.get('path')} ({len(task.prompt or '')} chars)"
            )
        elif result.get("skipped"):
            logger.debug(
                f"prompt-sync ⊘ task={task_id_short} repo={repo} "
                f"skipped: {result.get('error')}"
            )
        else:
            logger.warning(
                f"prompt-sync ✗ task={task_id_short} repo={repo} "
                f"FAILED: {result.get('error')}"
            )
    except Exception as e:
        logger.warning(
            f"prompt-sync ✗ task={task_id_short} repo={repo} "
            f"exception: {e}"
        )
        try:
            task.github_prompt_last_error = str(e)[:500]
        except Exception:
            pass
    finally:
        if on_done is not None:
            try:
                on_done()
            except Exception as e:
                logger.debug(f"prompt-sync: on_done callback failed: {e}")


def schedule_index_rebuild(
    tasks_getter: callable,
    watched: Any,
    *,
    token: str,
    debounce_seconds: float = INDEX_DEBOUNCE_SECONDS,
) -> None:
    """rebuild_index را debounce می‌کند — اگر در فاصلهٔ debounce چندبار صدا
    زده شود، فقط یک بار رخ می‌دهد (آخرین snapshot).

    tasks_getter: callable که هنگام flush، snapshot تازه از لیست تسک‌ها را
    برمی‌گرداند (مثلاً `lambda: list(service.tasks)`).
    """
    resolved = _resolve_repo_and_branch(watched)
    if not resolved or not token:
        return
    watched_id = watched.id

    async def _flush():
        try:
            await asyncio.sleep(debounce_seconds)
            snapshot = tasks_getter()
            await rebuild_project_index(snapshot, watched, token=token)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning(
                f"prompt-sync: debounced rebuild_index failed "
                f"watched={watched_id}: {e}"
            )
        finally:
            _index_debounce_tasks.pop(watched_id, None)

    existing = _index_debounce_tasks.get(watched_id)
    if existing and not existing.done():
        existing.cancel()
    _index_debounce_tasks[watched_id] = asyncio.create_task(_flush())


async def safe_delete_task(
    task: Any, watched: Any, *, token: str, on_done: Optional[callable] = None,
) -> None:
    try:
        await delete_task_from_github(task, watched, token=token)
    except Exception as e:
        logger.warning(f"prompt-sync: safe_delete_task failed task={task.id}: {e}")
    finally:
        if on_done is not None:
            try:
                on_done()
            except Exception as e:
                logger.debug(f"prompt-sync: on_done callback failed: {e}")
