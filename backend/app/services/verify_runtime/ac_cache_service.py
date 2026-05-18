"""Verify v6 — ac_cache_service

Per-AC state cache برای جلوگیری از re-verify غیرضروری AC هایی که
چندین run متوالی done شده‌اند و فایل‌های مرتبط تغییر نکرده‌اند.

طبق Bug C6 v2 — بهبود ۷ (Per-AC state cache).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context_builder import VerifyContext
    from .iterative_orchestrator import ProbeResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# asyncio.Lock per-task (edge case v2: cache invalidation race)
# ---------------------------------------------------------------------------


_TASK_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_task_lock(task_id: str) -> asyncio.Lock:
    """دریافت/ساخت asyncio.Lock اختصاصی هر task برای جلوگیری از race condition
    در بروزرسانی cache هنگام دو verify همزمان."""
    if task_id not in _TASK_LOCKS:
        _TASK_LOCKS[task_id] = asyncio.Lock()
    return _TASK_LOCKS[task_id]


# ---------------------------------------------------------------------------
# compute_files_checksum
# ---------------------------------------------------------------------------


def compute_files_checksum(
    target_files: List[str],
    *,
    file_content_cache: Optional[Dict[str, str]] = None,
    commit_sha: str = "",
) -> str:
    """sha256 از target_files content (یا sha روی commit ref اگر GitHub).

    منطق: اگر file_content_cache داریم، روی محتوای کش شده hash می‌زنیم
    (دقیق‌ترین signal). اگر فقط commit_sha داریم، آن را hash می‌کنیم
    (سریع‌تر ولی کمتر دقیق — هر تغییر commit باعث invalidate می‌شود).
    اگر هیچکدام نبود، رشتهٔ خالی برمی‌گردانیم (cache غیرفعال).
    """
    if not target_files:
        return ""
    h = hashlib.sha256()
    if file_content_cache:
        # روی محتوای کش شده — اگر فایل در cache نباشد، فقط path هش می‌شود
        for path in sorted(set(target_files)):
            h.update(path.encode("utf-8"))
            h.update(b"\x00")
            content = file_content_cache.get(path)
            if content is not None:
                h.update(content.encode("utf-8", errors="replace"))
            h.update(b"\x01")
        return h.hexdigest()
    if commit_sha:
        h.update(commit_sha.encode("utf-8"))
        for path in sorted(set(target_files)):
            h.update(path.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()
    return ""


# ---------------------------------------------------------------------------
# ac_hash — کلید cache برای یک AC
# ---------------------------------------------------------------------------


def _ac_hash(ac: Any, classification: str = "") -> str:
    """hash پایدار از متن AC + classification — کلید cache."""
    if isinstance(ac, dict):
        text = str(ac.get("text", "")).strip()
    else:
        text = str(ac).strip()
    if not text:
        return ""
    raw = f"{text}\n@@{classification}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# check_ac_cache
# ---------------------------------------------------------------------------


def check_ac_cache(
    ac: Any,
    context: "VerifyContext",
    *,
    classification: str = "",
    target_files: Optional[List[str]] = None,
    force_full_verify: bool = False,
) -> Optional["ProbeResult"]:
    """بررسی cache برای یک AC. اگر cache hit با freshness باشد،
    ProbeResult مربوطه را برمی‌گرداند. در غیر این صورت None.

    شرایط cache hit:
    - enable_ac_cache=True در config
    - force_full_verify=False
    - consecutive_done_count >= ac_cache_consecutive_threshold (default 3)
    - files_checksum unchanged
    - age < ac_cache_max_age_days (default 7 days)
    """
    cfg = context.config
    if force_full_verify or not (cfg and cfg.enable_ac_cache):
        return None

    task = context.task
    cache_dict = getattr(task, "ac_verify_cache", None)
    if not isinstance(cache_dict, dict):
        return None

    key = _ac_hash(ac, classification)
    if not key or key not in cache_dict:
        return None

    entry = cache_dict.get(key)
    if not isinstance(entry, dict):
        return None

    cons = int(entry.get("consecutive_done_count", 0) or 0)
    threshold = cfg.ac_cache_consecutive_threshold if cfg else 3
    if cons < threshold:
        return None

    # age check
    from datetime import datetime, timezone, timedelta
    last_iso = entry.get("last_verified_at", "")
    if last_iso:
        try:
            last_dt = datetime.fromisoformat(str(last_iso).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            max_age_days = cfg.ac_cache_max_age_days if cfg else 7
            if now - last_dt > timedelta(days=max_age_days):
                return None
        except Exception:
            return None

    # checksum check
    files = target_files or list(getattr(task, "target_files", None) or [])
    repo_full_name = ""
    if context.watched is not None:
        repo_full_name = getattr(context.watched, "repo_full_name", "") or ""
    commit_sha = ""
    if context.commits_recent:
        first = context.commits_recent[0] if context.commits_recent else {}
        if isinstance(first, dict):
            commit_sha = str(first.get("sha", "") or first.get("commit_sha", ""))

    current_checksum = compute_files_checksum(
        files,
        file_content_cache=context.file_content_cache,
        commit_sha=commit_sha,
    )
    cached_checksum = str(entry.get("files_checksum", ""))
    if not current_checksum or current_checksum != cached_checksum:
        return None

    # cache hit — return ProbeResult
    from .iterative_orchestrator import ProbeResult
    return ProbeResult(
        probe_name="ac_cache",
        verdict=str(entry.get("verdict", "unclear")),
        confidence=float(entry.get("confidence", 0.0) or 0.0),
        evidence=list(entry.get("evidence", []) or []) + [
            f"cache hit (consecutive_done={cons}, age_ok)",
        ],
    )


# ---------------------------------------------------------------------------
# update_ac_cache
# ---------------------------------------------------------------------------


async def update_ac_cache(
    ac: Any,
    result: "ProbeResult",
    context: "VerifyContext",
    *,
    classification: str = "",
    target_files: Optional[List[str]] = None,
) -> None:
    """به‌روزرسانی cache پس از یک verify run.

    - اگر verdict=done و confidence > 0.85 → consecutive_done_count++,
      files_checksum updated
    - اگر verdict != done → consecutive_done_count = 0, cache invalidate
      (entry حذف می‌شود)

    استفاده از asyncio.Lock per-task برای race-safety.
    """
    cfg = context.config
    if not (cfg and cfg.enable_ac_cache):
        return

    task = context.task
    task_id = getattr(task, "id", "") or ""
    if not task_id:
        return

    lock = _get_task_lock(task_id)
    async with lock:
        cache_dict = getattr(task, "ac_verify_cache", None)
        if not isinstance(cache_dict, dict):
            # init field on task
            try:
                setattr(task, "ac_verify_cache", {})
                cache_dict = task.ac_verify_cache  # type: ignore[attr-defined]
            except Exception:
                return

        key = _ac_hash(ac, classification)
        if not key:
            return

        verdict = (result.verdict or "").lower() if result else "unclear"
        confidence = float(result.confidence or 0.0) if result else 0.0

        if verdict == "done" and confidence > 0.85:
            prev_entry = cache_dict.get(key) if isinstance(cache_dict.get(key), dict) else {}
            prev_count = int(prev_entry.get("consecutive_done_count", 0) or 0)
            files = target_files or list(getattr(task, "target_files", None) or [])
            commit_sha = ""
            if context.commits_recent:
                first = context.commits_recent[0] if context.commits_recent else {}
                if isinstance(first, dict):
                    commit_sha = str(first.get("sha", "") or first.get("commit_sha", ""))
            checksum = compute_files_checksum(
                files,
                file_content_cache=context.file_content_cache,
                commit_sha=commit_sha,
            )
            from datetime import datetime, timezone
            cache_dict[key] = {
                "verdict": "done",
                "confidence": confidence,
                "last_verified_at": datetime.now(timezone.utc).isoformat(),
                "files_checksum": checksum,
                "consecutive_done_count": prev_count + 1,
                "evidence": list(result.evidence or [])[:5],
            }
        else:
            # invalidate
            if key in cache_dict:
                del cache_dict[key]


__all__ = [
    "compute_files_checksum",
    "check_ac_cache",
    "update_ac_cache",
]
